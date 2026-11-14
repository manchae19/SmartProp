package vn.smartprop.modules.prediction;
import com.fasterxml.jackson.databind.JsonNode;
import java.math.BigDecimal;
import java.util.*;
import org.springframework.stereotype.Service;
import vn.smartprop.modules.auth.AccountAccess;
import vn.smartprop.modules.property.Property;
@Service
public class ValuationService {
    public static final String RUN="b4b1339d3f35857e";
    private static final Set<String> DISTRICTS=Set.of("Hải Châu","Thanh Khê","Sơn Trà","Ngũ Hành Sơn","Cẩm Lệ","Liên Chiểu","Hòa Vang","Hoà Vang");
    private static final Set<String> CATEGORIES=Set.of("Nhà ở","Đất nền","Căn hộ chung cư");
    private final AccountAccess access;private final ValuationClient client;
    public ValuationService(AccountAccess access,ValuationClient client){this.access=access;this.client=client;}
    public record Category(String category,List<String> locations){}
    public record Options(String modelVersion,String modelRun,List<Category> categories){}
    public record Preview(boolean available,String reason,String modelVersion,String modelRun,String predictedAskingPriceVnd,
        String currency,String priceBasis,Map<String,Object> featuresUsed,List<String> missingFeatures,List<String> warnings){}
    private static void pin(JsonNode n){if(!"v6".equals(n.path("model_version").asText())||!RUN.equals(n.path("model_run").asText()))throw ValuationClient.unavailable();}
    private Options loadOptions(){
        var n=client.exchange("/model/options",null);pin(n);
        if(!n.path("categories").isArray())throw ValuationClient.unavailable();
        List<Category> groups=new ArrayList<>();Set<String> seen=new HashSet<>();
        for(var c:n.path("categories")){
            String category=c.path("category").asText();if(!CATEGORIES.contains(category)||!seen.add(category)||!c.path("locations").isArray())throw ValuationClient.unavailable();
            List<String> locations=new ArrayList<>();for(var l:c.path("locations"))if(l.isTextual()&&DISTRICTS.contains(l.asText())&&!locations.contains(l.asText()))locations.add(l.asText());
            if(locations.isEmpty())throw ValuationClient.unavailable();groups.add(new Category(category,List.copyOf(locations)));
        }
        if(!seen.equals(CATEGORIES))throw ValuationClient.unavailable();return new Options("v6",RUN,List.copyOf(groups));
    }
    public Options options(Long actor){access.publisher(actor);return loadOptions();}
    private Preview unsupported(String reason){return new Preview(false,reason,"v6",RUN,null,"VND",null,Map.of(),List.of(),List.of());}
    public Preview preview(Long actor,ValuationRequest r){
        access.publisher(actor);
        String category=switch(r.propertyType()){case HOUSE,VILLA->"Nhà ở";case LAND->"Đất nền";case APARTMENT->"Căn hộ chung cư";default->null;};
        if(r.transactionType()!=Property.Transaction.SALE)return unsupported("Model hiện chỉ hỗ trợ tin bán.");
        if(category==null)return unsupported("Loại bất động sản này chưa được model hỗ trợ.");
        if(r.areaSqm().compareTo(new BigDecimal("20"))<0||r.areaSqm().compareTo(new BigDecimal("1000"))>0)return unsupported("Model hỗ trợ diện tích từ 20 đến 1000 m².");
        if(!"Đất nền".equals(category)&&r.bedrooms()!=null&&r.bedrooms()>30)return unsupported("Số phòng ngủ vượt phạm vi model (1–30).");
        if("Căn hộ chung cư".equals(category)&&(r.roadWidthM()!=null||r.frontageWidthM()!=null))return unsupported("Chiều rộng đường/mặt tiền không áp dụng cho căn hộ.");
        var options=loadOptions();String location=r.locationFeature().strip();
        if(options.categories().stream().noneMatch(c->c.category().equals(category)&&c.locations().contains(location)))return unsupported("Khu vực chưa được hỗ trợ cho loại bất động sản này.");
        Map<String,Object> input=new LinkedHashMap<>();input.put("category",category);input.put("area_sqm",r.areaSqm().doubleValue());input.put("location_feature",location);
        if(r.ward()!=null&&!r.ward().isBlank())input.put("ward",r.ward().strip());
        if(!"Đất nền".equals(category)&&r.bedrooms()!=null&&r.bedrooms()>0)input.put("rooms",r.bedrooms());
        if(r.propertyType()==Property.Type.VILLA)input.put("house_subtype","villa");
        // Optional real measurements; omitted fields remain absent, never defaulted.
        if(r.roadWidthM()!=null)input.put("road_width_m",r.roadWidthM());
        if(r.frontageWidthM()!=null)input.put("frontage_width_m",r.frontageWidthM());
        if(r.streetName()!=null&&!r.streetName().isBlank())input.put("street_name",r.streetName().strip());
        if(r.projectName()!=null&&!r.projectName().isBlank())input.put("project_name",r.projectName().strip());
        if(r.bathrooms()!=null)input.put("bathrooms",r.bathrooms());
        if(r.houseDirection()!=null&&!r.houseDirection().isBlank())input.put("house_direction",r.houseDirection().strip());
        if(r.balconyDirection()!=null&&!r.balconyDirection().isBlank())input.put("balcony_direction",r.balconyDirection().strip());
        input.put("title",r.title()==null?"":r.title());String description=r.description()==null?"":r.description();
        boolean shortened=description.length()>8000;input.put("description",shortened?description.substring(0,8000):description);
        var n=client.exchange("/predict",input);pin(n);
        var price=n.path("predicted_asking_price_vnd");
        if(!"all".equals(n.path("configuration").asText())||!"VND".equals(n.path("currency").asText())||!category.equals(n.path("category").asText())||
            !price.isIntegralNumber()||price.bigIntegerValue().signum()<=0||price.bigIntegerValue().bitLength()>63)throw ValuationClient.unavailable();
        var f=n.path("features_used");if(!f.isObject()||!location.equals(f.path("location_feature").asText())||!f.path("area_sqm").isNumber()||
            Math.abs(f.path("area_sqm").asDouble()-r.areaSqm().doubleValue())>0.00001)throw ValuationClient.unavailable();
        Map<String,Object> features=new LinkedHashMap<>();features.put("areaSqm",r.areaSqm());features.put("locationFeature",location);
        // Only numeric/enum model features; no arbitrary upstream JSON or extracted address is exposed.
        for(String key:List.of("rooms","floors"))if(f.path(key).isNumber())features.put(key,f.path(key).numberValue());
        for(String key:List.of("access_type","house_subtype"))if(f.path(key).isTextual())features.put(key,f.path(key).asText());
        List<String> warnings=strings(n.path("warnings"));if(shortened)warnings.add("Model chỉ dùng 8000 ký tự đầu của mô tả; mô tả tin đăng được giữ nguyên.");
        return new Preview(true,null,"v6",RUN,price.bigIntegerValue().toString(),"VND","Giá rao ước tính từ dữ liệu tin đăng.",features,strings(n.path("missing_features")),warnings);
    }
    private static List<String> strings(JsonNode n){if(!n.isArray()||n.size()>30)throw ValuationClient.unavailable();List<String> out=new ArrayList<>();for(var v:n){if(!v.isTextual()||v.asText().length()>1000)throw ValuationClient.unavailable();out.add(v.asText());}return out;}
}
