package vn.smartprop.modules.prepurchase;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.io.InputStream;
import java.text.Normalizer;
import java.util.HashMap;
import java.util.Map;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Service;

/**
 * Old ward and district names mapped to the current ward/commune, per Nghị quyết
 * 1659/NQ-UBTVQH15 (two-tier model from 01/07/2025).
 *
 * <p>Listings still store the pre-2025 ward name ("Hòa Khánh"), while flood records carry
 * the current unit ("Phường Hòa Khánh"). Comparing the two directly would attach a record
 * to the wrong listing, so both sides are folded to the same key first.
 */
@Service
public class AdminAreaMapping {
    private final Map<String, String> unitByBareName = new HashMap<>();
    private final Map<String, String> unitByOldWard = new HashMap<>();

    public AdminAreaMapping(ObjectMapper mapper) {
        try (InputStream in = new ClassPathResource("flood/danang_admin_mapping_v1.json").getInputStream()) {
            JsonNode root = mapper.readTree(in);
            JsonNode units = root.path("post2025CoreUnits");
            for (var it = units.fieldNames(); it.hasNext(); ) {
                String unit = it.next();
                unitByBareName.put(bare(unit), unit);
            }
            for (JsonNode ward : root.path("historicalWards")) {
                String unit = ward.path("nq1659Unit").asText(null);
                if (unit == null || unit.isBlank()) continue;
                unitByOldWard.put(fold(ward.path("ward").asText()), unit);
                for (JsonNode alias : ward.path("aliases")) {
                    unitByOldWard.putIfAbsent(fold(alias.asText()), unit);
                }
            }
        } catch (IOException e) {
            throw new IllegalStateException("Cannot read the administrative mapping", e);
        }
    }

    /**
     * The current ward/commune for a name a listing or a record carries.
     *
     * <p>Accepts either the current name ("Phường Hòa Khánh") or the pre-2025 ward name
     * ("Hòa Khánh"). Returns null when the name is unknown, so the caller can decide
     * whether an unknown name is a match or a gap.
     */
    public String currentUnit(String name) {
        if (name == null || name.isBlank()) return null;
        String folded = fold(name);
        String direct = unitByBareName.get(bare(folded));
        if (direct != null) return direct;
        return unitByOldWard.get(folded);
    }

    /** "Phường Hòa Khánh" -> "hoa khanh", so a bare name can be looked up. */
    private static String bare(String unit) {
        String folded = fold(unit);
        for (String prefix : new String[]{"phuong ", "xa ", "dac khu "}) {
            if (folded.startsWith(prefix)) return folded.substring(prefix.length());
        }
        return folded;
    }

    static String fold(String text) {
        String ascii = Normalizer.normalize(text.toLowerCase().replace("đ", "d"), Normalizer.Form.NFD)
            .replaceAll("\\p{M}", "");
        return String.join(" ", ascii.trim().split("\\s+"));
    }
}
