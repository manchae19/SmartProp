package vn.smartprop.modules.prediction;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.*;
import java.math.BigDecimal;
import java.util.LinkedHashMap;
import java.util.Map;
import vn.smartprop.common.ApiInputs;

/** Structured inputs only: a caller cannot submit a price or a saved model response. */
public record HistoryInput(
    @NotBlank @Pattern(regexp="Nhà ở|Đất nền|Căn hộ chung cư") String category,
    @JsonProperty("area_sqm") @NotNull @DecimalMin("20") @DecimalMax("1000") BigDecimal area,
    @JsonProperty("location_feature") @NotBlank @Size(max=200) String location,
    @Size(max=100) String ward,
    @Min(1) @Max(30) Integer rooms,
    @DecimalMin("1") @DecimalMax("20") BigDecimal floors,
    @JsonProperty("access_type") @Pattern(regexp="alley|frontage") String accessType,
    @JsonProperty("house_subtype") @Pattern(regexp="villa|house_c4") String houseSubtype) {

    public Map<String,Object> modelInput() {
        if (("Đất nền".equals(category) && rooms != null) ||
            (!"Nhà ở".equals(category) && (floors != null || houseSubtype != null)) ||
            ("Căn hộ chung cư".equals(category) && accessType != null))
            throw ApiInputs.bad("Thông tin bổ sung không áp dụng cho loại bất động sản này.");
        Map<String,Object> value = new LinkedHashMap<>();
        value.put("category", category);
        value.put("area_sqm", area.stripTrailingZeros());
        value.put("location_feature", location.strip());
        if (ward != null && !ward.isBlank()) value.put("ward", ward.strip());
        if (rooms != null) value.put("rooms", rooms);
        if (floors != null) value.put("floors", floors.stripTrailingZeros());
        if (accessType != null) value.put("access_type", accessType);
        if (houseSubtype != null) value.put("house_subtype", houseSubtype);
        return value;
    }

    @Override public String toString() { return "HistoryInput[redacted]"; }
}
