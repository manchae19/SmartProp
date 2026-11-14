package vn.smartprop.modules.prediction;

import com.fasterxml.jackson.databind.*;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.*;
import java.util.function.Supplier;
import org.springframework.dao.DataAccessException;
import org.springframework.stereotype.Service;
import vn.smartprop.modules.auth.AccountAccess;
import vn.smartprop.common.*;
import vn.smartprop.config.*;

@Service
public class ValuationHistoryService {
    private final AccountAccess access;
    private final ValuationClient client;
    private final ValuationHistoryRepository history;
    private final ObjectMapper json;
    private static final Set<String> FEATURES=Set.of("area_sqm","location_feature","ward_source","rooms","floors","access_type","house_subtype");
    public ValuationHistoryService(AccountAccess access,ValuationClient client,ValuationHistoryRepository history,ObjectMapper json) {
        this.access=access;this.client=client;this.history=history;this.json=json;
    }
    private <T> T database(Supplier<T> operation) {
        try { return operation.get(); }
        catch (DataAccessException error) { throw new ApiException(503,"HISTORY_UNAVAILABLE","Lịch sử chưa sẵn sàng. Vui lòng kiểm tra cấu hình cơ sở dữ liệu."); }
    }
    public ValuationHistoryRepository.Entry save(Long user, HistoryInput request, String key) {
        access.active(user);
        String validKey=ApiInputs.uuid(key);
        JsonNode input=json.valueToTree(request.modelInput());
        String fingerprint;
        try { fingerprint=HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(input.toString().getBytes(StandardCharsets.UTF_8))); }
        catch (java.security.NoSuchAlgorithmException error) { throw new IllegalStateException(error); }
        var previous=database(()->history.byKey(user,validKey));
        if (previous.isPresent()) return replay(previous.get(),fingerprint);
        // Validate category-specific location against the same curated API used by the form.
        JsonNode options=client.exchange("/model/options",null);
        pin(options);
        boolean supported=false;
        if (options.path("categories").isArray()) for (var category:options.path("categories")) {
            if (request.category().equals(category.path("category").asText()) && category.path("locations").isArray())
                for (var location:category.path("locations")) if (input.path("location_feature").asText().equals(location.asText())) supported=true;
        }
        if (!supported) throw ApiInputs.bad("Địa bàn chưa được model hỗ trợ cho loại bất động sản này.");
        JsonNode prediction=snapshot(client.exchange("/predict",input),input);
        database(()->{history.insert(user,validKey,fingerprint,input,prediction);return true;});
        return replay(database(()->history.byKey(user,validKey)).orElseThrow(()->new ApiException(503,"HISTORY_UNAVAILABLE","Chưa xác nhận được kết quả đã lưu.")),fingerprint);
    }
    private ValuationHistoryRepository.Entry replay(ValuationHistoryRepository.Stored stored,String fingerprint) {
        if (!stored.fingerprint().equals(fingerprint)) throw ApiInputs.conflict("Mã lưu này đã dùng cho thông tin khác. Vui lòng tạo kết quả mới.");
        return stored.entry();
    }
    private static void pin(JsonNode value) {
        if (!"v6".equals(value.path("model_version").asText()) || !ValuationService.RUN.equals(value.path("model_run").asText())) throw ValuationClient.unavailable();
    }
    private JsonNode snapshot(JsonNode value,JsonNode input) {
        pin(value);
        var price=value.path("predicted_asking_price_vnd");var features=value.path("features_used");
        if (!"all".equals(value.path("configuration").asText()) || !"VND".equals(value.path("currency").asText()) ||
            !input.path("category").equals(value.path("category")) || !price.isIntegralNumber() || price.bigIntegerValue().signum()<=0 || price.bigIntegerValue().bitLength()>63 ||
            !value.path("predicted_asking_price_million").isNumber() || !Double.isFinite(value.path("predicted_asking_price_million").asDouble()) ||
            !features.isObject() || !features.path("area_sqm").isNumber() || features.path("area_sqm").decimalValue().compareTo(input.path("area_sqm").decimalValue())!=0 ||
            !input.path("location_feature").equals(features.path("location_feature")) || !value.path("price_basis").isTextual() || value.path("price_basis").asText().length()>200)
            throw ValuationClient.unavailable();
        ObjectNode clean=json.createObjectNode(), cleanFeatures=json.createObjectNode();
        for (String key:FEATURES) {
            var feature=features.path(key);
            if (feature.isMissingNode() || feature.isContainerNode() || (feature.isTextual() && feature.asText().length()>200)) throw ValuationClient.unavailable();
            cleanFeatures.set(key,feature);
        }
        for (String key:List.of("missing_features","warnings")) {
            var list=value.path(key);
            if (!list.isArray() || list.size()>30) throw ValuationClient.unavailable();
            for (var item:list) if (!item.isTextual() || item.asText().length()>1000 || (key.equals("missing_features") && !FEATURES.contains(item.asText()))) throw ValuationClient.unavailable();
        }
        for (String key:List.of("model_version","model_run","configuration","category","predicted_asking_price_vnd","predicted_asking_price_million","currency","price_basis","missing_features","warnings")) clean.set(key,value.get(key));
        clean.set("features_used",cleanFeatures);
        return clean;
    }
    public PageResponse<ValuationHistoryRepository.Entry> list(Long user,int page,int size) {
        access.active(user);ApiInputs.newest(page,size);return database(()->history.list(user,page,size));
    }
    public ValuationHistoryRepository.Entry get(Long user,String id) {
        access.active(user);String valid=ApiInputs.uuid(id);return database(()->history.byId(user,valid)).orElseThrow(ApiInputs::missing).entry();
    }
    public void delete(Long user,String id) {
        access.active(user);String valid=ApiInputs.uuid(id);if (!database(()->history.delete(user,valid))) throw ApiInputs.missing();
    }
}
