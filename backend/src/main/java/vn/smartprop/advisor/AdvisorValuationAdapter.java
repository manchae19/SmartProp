package vn.smartprop.advisor;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.ByteArrayOutputStream;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.ByteBuffer;
import java.time.Duration;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CompletionStage;
import java.util.concurrent.Flow;
import java.util.concurrent.TimeUnit;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import vn.smartprop.advisor.AdvisorDtos.ShapFactorItem;
import vn.smartprop.advisor.AdvisorDtos.ShapSummary;
import vn.smartprop.advisor.AdvisorDtos.ValuationEvidence;
import vn.smartprop.modules.property.Property;
import vn.smartprop.modules.property.PropertyRepository;
import vn.smartprop.modules.recommendation.RecommendationDtos.PropertyType;

/**
 * Safe loopback adapter to FastAPI XGBoost V6 + TreeSHAP for the AI Advisor.
 *
 * <p>Enforces strict pre-call feature validation:
 * <ul>
 *   <li>Never invokes XGBoost when mandatory features ({@code category}, {@code area_sqm} in 20..1000,
 *       supported {@code location_feature}) are missing or out of range.</li>
 *   <li>Never fabricates fallback prices or SHAP explanations when the AI service is offline.</li>
 *   <li>Pins {@code model_version="v6"} and {@code model_run="b4b1339d3f35857e"}.</li>
 *   <li>Never transmits or returns PII (phone, email, owner identity, raw street address).</li>
 * </ul>
 */
@Component
public class AdvisorValuationAdapter {
    public static final String EXPECTED_VERSION = "v6";
    public static final String EXPECTED_RUN = "b4b1339d3f35857e";
    public static final String PRICE_BASIS =
        "Giá rao ước tính độc lập từ mô hình XGBoost V6 (dữ liệu tin đăng); không phải giá giao dịch thực tế và không dùng để tự chứng minh độ chính xác.";

    private static final BigDecimal MIN_AREA = new BigDecimal("20");
    private static final BigDecimal MAX_AREA = new BigDecimal("1000");
    private static final int MAX_RESPONSE_BYTES = 131_072;

    private final ObjectMapper json;
    private final PropertyRepository properties;
    private final URI base;
    private final boolean enabled;
    private final HttpClient client;

    public AdvisorValuationAdapter(
            ObjectMapper json,
            PropertyRepository properties,
            @Value("${app.advisor.valuation-enabled:true}") boolean enabled,
            @Value("${app.advisor.valuation-base-url:http://127.0.0.1:8000}") String baseUrl) {
        this.json = json;
        this.properties = properties;
        this.enabled = enabled;
        this.base = URI.create(baseUrl);
        if (!"http".equals(base.getScheme())
                || !"127.0.0.1".equals(base.getHost())
                || base.getUserInfo() != null
                || base.getQuery() != null
                || base.getFragment() != null
                || !(base.getPath().isEmpty() || "/".equals(base.getPath()))
                || base.getPort() < 1) {
            throw new IllegalArgumentException(
                "Advisor valuation peer must be a fixed IPv4 loopback HTTP origin with an explicit port");
        }
        this.client = HttpClient.newBuilder()
            .connectTimeout(Duration.ofMillis(1200))
            .followRedirects(HttpClient.Redirect.NEVER)
            .build();
    }

    public boolean isEnabled() {
        return enabled;
    }

    /**
     * Fast per-consultation readiness probe that returns supported locations by V6 category,
     * or {@code null} if disabled or FastAPI is offline/unhealthy.
     */
    public Map<String, Set<String>> probeSupportedLocations() {
        if (!enabled) return null;
        JsonNode options = exchange("/model/options", null, 1800);
        if (options == null || !validPin(options) || !options.path("categories").isArray()) {
            return null;
        }
        Map<String, Set<String>> byCategory = new LinkedHashMap<>();
        for (JsonNode catNode : options.path("categories")) {
            String cat = catNode.path("category").asText("");
            JsonNode locs = catNode.path("locations");
            if (cat.isBlank() || !locs.isArray()) continue;
            java.util.LinkedHashSet<String> set = new java.util.LinkedHashSet<>();
            for (JsonNode loc : locs) {
                if (loc.isTextual() && !loc.asText().isBlank()) {
                    set.add(loc.asText().strip());
                }
            }
            if (!set.isEmpty()) {
                byCategory.put(cat, Set.copyOf(set));
            }
        }
        return byCategory.isEmpty() ? null : Map.copyOf(byCategory);
    }

    /**
     * Evaluates a single candidate property against V6 + TreeSHAP if and only if mandatory
     * features are valid and the model service is online.
     */
    public ValuationEvidence evaluate(
            String sourceKind,
            String recordKey,
            PropertyType propertyType,
            BigDecimal areaSqm,
            String district,
            String ward,
            BigDecimal askingPriceVnd,
            Map<String, Set<String>> supportedLocations) {

        String category = mapCategory(propertyType);
        if (category == null) {
            return skipped("SKIPPED_UNSUPPORTED_TYPE",
                "Loại bất động sản (" + propertyType + ") chưa nằm trong phạm vi hỗ trợ của mô hình XGBoost V6.");
        }
        if (areaSqm == null) {
            return skipped("SKIPPED_MISSING_FEATURES",
                "Thiếu diện tích bắt buộc nên không gọi mô hình XGBoost V6.");
        }
        if (areaSqm.compareTo(MIN_AREA) < 0 || areaSqm.compareTo(MAX_AREA) > 0) {
            return skipped("SKIPPED_OUT_OF_RANGE_AREA",
                "Diện tích " + areaSqm.stripTrailingZeros().toPlainString()
                + " m² nằm ngoài miền huấn luyện 20–1.000 m² của mô hình XGBoost V6.");
        }
        String normalizedDistrict = normalizeDistrict(district);
        if (normalizedDistrict == null) {
            return skipped("SKIPPED_MISSING_FEATURES",
                "Thiếu quận/huyện chuẩn hóa bắt buộc nên không gọi mô hình XGBoost V6.");
        }
        if (supportedLocations == null) {
            return skipped("SERVICE_UNAVAILABLE",
                "Dịch vụ định giá AI (XGBoost V6) hiện không khả dụng; hệ thống giữ nguyên kết quả tư vấn còn lại.");
        }
        Set<String> catLocations = supportedLocations.get(category);
        if (catLocations == null || !catLocations.contains(normalizedDistrict)) {
            return skipped("SKIPPED_UNSUPPORTED_LOCATION",
                "Địa bàn '" + normalizedDistrict + "' chưa thuộc từ điển khu vực được mô hình V6 hỗ trợ cho phân khúc " + category + ".");
        }

        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("category", category);
        payload.put("area_sqm", areaSqm.doubleValue());
        payload.put("location_feature", normalizedDistrict);
        if (ward != null && !ward.isBlank() && ward.strip().length() <= 100) {
            payload.put("ward", ward.strip());
        }
        if (propertyType == PropertyType.VILLA) {
            payload.put("house_subtype", "villa");
        }

        // Enrich with structured non-PII attributes for published platform listings only.
        if ("PROPERTY".equals(sourceKind) && recordKey != null && !recordKey.isBlank()) {
            Property prop = properties.findByIdAndDeletedAtIsNull(recordKey).orElse(null);
            if (prop != null && prop.status == Property.Status.PUBLISHED) {
                if (!"Đất nền".equals(category) && prop.bedrooms != null && prop.bedrooms >= 1 && prop.bedrooms <= 30) {
                    payload.put("rooms", (int) prop.bedrooms);
                }
                if (prop.title != null && !prop.title.isBlank()) {
                    payload.put("title", truncate(prop.title.strip(), 500));
                }
                if (prop.description != null && !prop.description.isBlank()) {
                    payload.put("description", truncate(prop.description.strip(), 8000));
                }
            }
        }

        JsonNode res = exchange("/predict", payload, 4000);
        if (res == null || !validPin(res)) {
            return skipped("SERVICE_UNAVAILABLE",
                "Không nhận được phản hồi hợp lệ từ mô hình XGBoost V6.");
        }
        JsonNode priceNode = res.path("predicted_asking_price_vnd");
        if (!priceNode.isIntegralNumber() || priceNode.bigIntegerValue().signum() <= 0) {
            return skipped("SERVICE_UNAVAILABLE", "Giá dự đoán từ mô hình V6 không hợp lệ.");
        }
        BigDecimal predictedVnd = new BigDecimal(priceNode.bigIntegerValue());
        BigDecimal deltaPct = null;
        if (askingPriceVnd != null && askingPriceVnd.signum() > 0 && predictedVnd.signum() > 0) {
            deltaPct = askingPriceVnd.subtract(predictedVnd)
                .multiply(new BigDecimal("100"))
                .divide(predictedVnd, 1, RoundingMode.HALF_UP);
        }

        Map<String, Object> featuresUsed = parseFeaturesUsed(res.path("features_used"));
        List<String> missingFeatures = parseStringList(res.path("missing_features"), 20);
        List<String> warnings = new ArrayList<>(parseStringList(res.path("warnings"), 20));
        warnings.add("Giá V6 là ước tính giá rao bán độc lập từ mô hình học máy, không phải kết luận thẩm định giá.");
        ShapSummary shap = parseShap(res.path("shap_explanation"));

        return new ValuationEvidence(
            "AVAILABLE",
            true,
            null,
            EXPECTED_VERSION,
            EXPECTED_RUN,
            predictedVnd,
            deltaPct,
            PRICE_BASIS,
            featuresUsed,
            missingFeatures,
            shap,
            List.copyOf(warnings)
        );
    }

    public static ValuationEvidence skipped(String status, String reason) {
        return new ValuationEvidence(status, false, reason, null, null, null, null, null, Map.of(), List.of(), null, List.of());
    }

    static String mapCategory(PropertyType type) {
        if (type == null) return null;
        return switch (type) {
            case HOUSE, VILLA -> "Nhà ở";
            case LAND -> "Đất nền";
            case APARTMENT -> "Căn hộ chung cư";
            default -> null;
        };
    }

    static String normalizeDistrict(String district) {
        if (district == null || district.isBlank()) return null;
        String clean = district.strip();
        if ("Hoà Vang".equalsIgnoreCase(clean) || "Hòa Vang".equalsIgnoreCase(clean)) return "Hòa Vang";
        if ("Hải Châu".equalsIgnoreCase(clean)) return "Hải Châu";
        if ("Thanh Khê".equalsIgnoreCase(clean)) return "Thanh Khê";
        if ("Sơn Trà".equalsIgnoreCase(clean)) return "Sơn Trà";
        if ("Ngũ Hành Sơn".equalsIgnoreCase(clean)) return "Ngũ Hành Sơn";
        if ("Cẩm Lệ".equalsIgnoreCase(clean)) return "Cẩm Lệ";
        if ("Liên Chiểu".equalsIgnoreCase(clean)) return "Liên Chiểu";
        return clean;
    }

    private static boolean validPin(JsonNode node) {
        return EXPECTED_VERSION.equals(node.path("model_version").asText())
            && EXPECTED_RUN.equals(node.path("model_run").asText());
    }

    private static Map<String, Object> parseFeaturesUsed(JsonNode f) {
        if (!f.isObject()) return Map.of();
        Map<String, Object> out = new LinkedHashMap<>();
        if (f.path("area_sqm").isNumber()) out.put("areaSqm", f.path("area_sqm").doubleValue());
        if (f.path("location_feature").isTextual()) out.put("locationFeature", f.path("location_feature").asText());
        if (f.path("ward_source").isTextual()) out.put("wardSource", f.path("ward_source").asText());
        if (f.path("rooms").isNumber()) out.put("rooms", f.path("rooms").intValue());
        if (f.path("floors").isNumber()) out.put("floors", f.path("floors").doubleValue());
        if (f.path("access_type").isTextual()) out.put("accessType", f.path("access_type").asText());
        if (f.path("house_subtype").isTextual()) out.put("houseSubtype", f.path("house_subtype").asText());
        return Map.copyOf(out);
    }

    private static List<String> parseStringList(JsonNode arr, int cap) {
        if (!arr.isArray()) return List.of();
        List<String> out = new ArrayList<>();
        for (JsonNode item : arr) {
            if (out.size() >= cap) break;
            if (item.isTextual() && item.asText().length() <= 1000) {
                out.add(item.asText());
            }
        }
        return List.copyOf(out);
    }

    private static ShapSummary parseShap(JsonNode s) {
        if (s == null || !s.isObject() || !s.path("base_value_log").isNumber()) return null;
        List<ShapFactorItem> factors = new ArrayList<>();
        JsonNode top = s.path("top_factors");
        if (top.isArray()) {
            for (JsonNode item : top) {
                if (factors.size() >= 6) break;
                if (!item.path("feature_name").isTextual() || !item.path("shap_value").isNumber()) continue;
                String dir = "decrease".equals(item.path("direction").asText()) ? "decrease" : "increase";
                factors.add(new ShapFactorItem(
                    item.path("feature_name").asText(),
                    item.path("label").asText(item.path("feature_name").asText()),
                    item.path("shap_value").asDouble(),
                    item.path("impact_pct").asDouble(0.0),
                    dir,
                    item.path("context_note").asText("")
                ));
            }
        }
        return new ShapSummary(
            s.path("method").asText("TreeSHAP (Native Additive Contribution)"),
            s.path("scale").asText("log_asking_price"),
            s.path("base_value_log").asDouble(),
            s.path("base_price_vnd").asLong(0L),
            s.path("summary_vi").asText(""),
            List.copyOf(factors)
        );
    }

    private static String truncate(String s, int max) {
        return s.length() <= max ? s : s.substring(0, max);
    }

    protected JsonNode exchange(String path, Object payload, long timeoutMs) {
        CompletableFuture<HttpResponse<byte[]>> pending = null;
        try {
            HttpRequest.Builder req = HttpRequest.newBuilder(base.resolve(path))
                .timeout(Duration.ofMillis(timeoutMs))
                .header("Accept", "application/json");
            if (payload == null) {
                req.GET();
            } else {
                req.header("Content-Type", "application/json")
                   .POST(HttpRequest.BodyPublishers.ofByteArray(json.writeValueAsBytes(payload)));
            }
            pending = client.sendAsync(req.build(), info -> new BoundedSubscriber());
            HttpResponse<byte[]> res = pending.get(timeoutMs + 300, TimeUnit.MILLISECONDS);
            if (res.statusCode() != 200) return null;
            JsonNode body = json.readTree(res.body());
            return body != null && body.isObject() ? body : null;
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            return null;
        } catch (Exception e) {
            return null;
        } finally {
            if (pending != null && !pending.isDone()) {
                pending.cancel(true);
            }
        }
    }

    private static final class BoundedSubscriber implements HttpResponse.BodySubscriber<byte[]> {
        private final CompletableFuture<byte[]> body = new CompletableFuture<>();
        private final ByteArrayOutputStream out = new ByteArrayOutputStream();
        private Flow.Subscription subscription;

        @Override
        public CompletionStage<byte[]> getBody() { return body; }

        @Override
        public void onSubscribe(Flow.Subscription s) {
            this.subscription = s;
            s.request(1);
            body.whenComplete((v, e) -> { if (e != null) s.cancel(); });
        }

        @Override
        public void onNext(List<ByteBuffer> buffers) {
            for (ByteBuffer b : buffers) {
                if (out.size() + b.remaining() > MAX_RESPONSE_BYTES) {
                    subscription.cancel();
                    body.completeExceptionally(new IllegalStateException("AI valuation response exceeded bound"));
                    return;
                }
                byte[] chunk = new byte[b.remaining()];
                b.get(chunk);
                out.writeBytes(chunk);
            }
            subscription.request(1);
        }

        @Override
        public void onError(Throwable throwable) { body.completeExceptionally(throwable); }

        @Override
        public void onComplete() { body.complete(out.toByteArray()); }
    }
}
