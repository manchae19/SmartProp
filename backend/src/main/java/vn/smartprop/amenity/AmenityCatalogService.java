package vn.smartprop.amenity;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Service;

import java.io.InputStream;
import java.text.Normalizer;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import static vn.smartprop.amenity.AmenityDtos.*;

@Service
public class AmenityCatalogService {
    private final ObjectMapper mapper;
    private final Map<String, AmenityProfile> byId = new LinkedHashMap<>();
    private final Map<String, AmenityProfile> byDistrictWard = new ConcurrentHashMap<>();
    private final Map<String, AmenityProfile> byDistrictOnly = new ConcurrentHashMap<>();
    private final Map<String, AmenityProfile> byCorridor = new ConcurrentHashMap<>();
    private CatalogSummary summary;

    public AmenityCatalogService(ObjectMapper mapper) {
        this.mapper = mapper;
        loadCatalog();
    }

    private void loadCatalog() {
        try {
            ClassPathResource res = new ClassPathResource("amenity/danang_amenity_catalog_v1.json");
            if (!res.exists()) {
                throw new IllegalStateException("danang_amenity_catalog_v1.json not found on classpath");
            }
            try (InputStream in = res.getInputStream()) {
                JsonNode root = mapper.readTree(in);
                String version = root.path("catalogVersion").asText("UNKNOWN");
                String jurisdiction = root.path("jurisdiction").asText("Thành phố Đà Nẵng");
                int totalPois = root.path("totalEffectivePois").asInt(1323);
                int totalAreas = root.path("totalAreasAnalyzed").asInt(82);

                Map<String, Integer> countsByLevel = new LinkedHashMap<>();
                JsonNode countsNode = root.path("countsByLevel");
                if (countsNode.isObject()) {
                    countsNode.fields().forEachRemaining(e -> countsByLevel.put(e.getKey(), e.getValue().asInt()));
                }

                Map<String, Double> weights = new LinkedHashMap<>();
                JsonNode weightsNode = root.path("livingPurposeWeights");
                if (weightsNode.isObject()) {
                    weightsNode.fields().forEachRemaining(e -> weights.put(e.getKey(), e.getValue().asDouble()));
                }

                this.summary = new CatalogSummary(version, jurisdiction, totalPois, totalAreas, countsByLevel, weights);

                JsonNode areasNode = root.path("areas");
                if (areasNode.isArray()) {
                    for (JsonNode a : areasNode) {
                        AmenityProfile p = parseProfile(a);
                        byId.put(p.areaId(), p);

                        if ("DISTRICT".equals(p.areaLevel())) {
                            byDistrictOnly.put(normalize(p.areaName()), p);
                        } else if ("WARD".equals(p.areaLevel())) {
                            // areaName is "Ward, District"
                            String[] parts = p.areaName().split(",");
                            if (parts.length >= 2) {
                                String w = normalize(parts[0].trim());
                                String d = normalize(parts[1].trim());
                                byDistrictWard.put(d + "|" + w, p);
                            }
                        } else if ("CORRIDOR".equals(p.areaLevel())) {
                            // areaName is "Đường Street, District"
                            String raw = p.areaName().replaceFirst("(?i)^Đường\\s+", "");
                            String[] parts = raw.split(",");
                            String s = normalize(parts[0].trim());
                            byCorridor.put(s, p);
                            if (parts.length >= 2) {
                                String d = normalize(parts[1].trim());
                                byCorridor.put(d + "|" + s, p);
                            }
                        }
                    }
                }
            }
        } catch (Exception e) {
            throw new IllegalStateException("Failed to initialize AmenityCatalogService: " + e.getMessage(), e);
        }
    }

    private AmenityProfile parseProfile(JsonNode node) {
        JsonNode cs = node.path("categoryScores");
        CategoryScores categoryScores = new CategoryScores(
            cs.path("essentials").asDouble(0.0),
            cs.path("education").asDouble(0.0),
            cs.path("healthcare").asDouble(0.0),
            cs.path("transit").asDouble(0.0),
            cs.path("recreation").asDouble(0.0)
        );

        JsonNode pc = node.path("poiCounts");
        PoiCounts poiCounts = new PoiCounts(
            pc.path("total").asInt(0),
            pc.path("school").asInt(0),
            pc.path("hospital").asInt(0),
            pc.path("pharmacy").asInt(0),
            pc.path("market").asInt(0),
            pc.path("supermarket").asInt(0),
            pc.path("park").asInt(0),
            pc.path("beach").asInt(0),
            pc.path("transit").asInt(0)
        );

        List<PoiEvidenceItem> evidence = new ArrayList<>();
        JsonNode evNode = node.path("poiEvidence");
        if (evNode.isArray()) {
            for (JsonNode ev : evNode) {
                evidence.add(new PoiEvidenceItem(
                    ev.path("name").asText(""),
                    ev.path("category").asText(""),
                    ev.path("attributionBasis").asText("")
                ));
            }
        }

        List<String> sources = new ArrayList<>();
        JsonNode srcNode = node.path("sources");
        if (srcNode.isArray()) {
            for (JsonNode s : srcNode) sources.add(s.asText());
        }

        List<String> limitations = new ArrayList<>();
        JsonNode limNode = node.path("dataLimitations");
        if (limNode.isArray()) {
            for (JsonNode l : limNode) limitations.add(l.asText());
        }

        Double areaKm2 = node.path("areaKm2").isNull() ? null : node.path("areaKm2").asDouble();
        Double density = node.path("densityPerKm2").isNull() ? null : node.path("densityPerKm2").asDouble();

        return new AmenityProfile(
            node.path("areaId").asText(""),
            node.path("areaLevel").asText(""),
            node.path("areaName").asText(""),
            node.path("parentDistrict").asText(""),
            node.path("livingScore").asDouble(0.0),
            categoryScores,
            node.path("confidence").asDouble(0.5),
            node.path("diversityIndex").asDouble(0.5),
            node.path("sampleListingCount").asInt(0),
            poiCounts,
            areaKm2,
            density,
            node.path("completenessTier").asText("MEDIUM"),
            node.path("hasCriticalGaps").asText("NO"),
            evidence,
            node.path("amenitySummary").asText(""),
            sources,
            limitations
        );
    }

    public Optional<AmenityProfile> getById(String areaId) {
        if (areaId == null || areaId.isBlank()) return Optional.empty();
        return Optional.ofNullable(byId.get(areaId.strip()));
    }

    public Optional<AmenityProfile> lookup(String district, String ward, String street) {
        String nd = blank(district) != null ? normalize(district) : null;
        String nw = blank(ward) != null ? normalize(ward) : null;
        String ns = blank(street) != null ? normalize(street) : null;

        // 1. Try corridor first if street is provided and has an exact corridor profile
        if (ns != null) {
            if (nd != null && byCorridor.containsKey(nd + "|" + ns)) {
                return Optional.of(byCorridor.get(nd + "|" + ns));
            }
            if (byCorridor.containsKey(ns)) {
                return Optional.of(byCorridor.get(ns));
            }
        }

        // 2. Try ward-level profile
        if (nw != null) {
            if (nd != null) {
                String key = nd + "|" + nw;
                if (byDistrictWard.containsKey(key)) {
                    return Optional.of(byDistrictWard.get(key));
                }
            }
            // Fallback: check if any ward key ends with |nw
            for (Map.Entry<String, AmenityProfile> entry : byDistrictWard.entrySet()) {
                if (entry.getKey().endsWith("|" + nw)) {
                    return Optional.of(entry.getValue());
                }
            }
        }

        // 3. Fallback to district-level profile
        if (nd != null && byDistrictOnly.containsKey(nd)) {
            return Optional.of(byDistrictOnly.get(nd));
        }

        return Optional.empty();
    }

    public List<AreaSummary> listAreas(String level, String district) {
        String normLevel = blank(level) != null ? level.strip().toUpperCase(Locale.ROOT) : null;
        String normDist = blank(district) != null ? normalize(district) : null;

        return byId.values().stream()
            .filter(p -> normLevel == null || p.areaLevel().equalsIgnoreCase(normLevel))
            .filter(p -> normDist == null || normalize(p.parentDistrict()).equals(normDist))
            .map(p -> new AreaSummary(
                p.areaId(),
                p.areaLevel(),
                p.areaName(),
                p.parentDistrict(),
                p.livingScore(),
                p.confidence(),
                p.sampleListingCount(),
                p.completenessTier()
            ))
            .toList();
    }

    public CatalogSummary getSummary() {
        return summary;
    }

    public static String normalize(String s) {
        if (s == null) return "";
        String clean = s.strip().toLowerCase(Locale.ROOT).replace('đ', 'd').replace('Đ', 'd');
        String nfd = Normalizer.normalize(clean, Normalizer.Form.NFD);
        String alpha = nfd.replaceAll("\\p{M}", "").replaceAll("[^a-z0-9]", "");
        return alpha.replaceFirst("^(thanhpho|tp|quan|huyen|phuong|xa|duong)", "");
    }

    private static String blank(String s) {
        return s == null || s.isBlank() ? null : s.strip();
    }
}
