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
    @JsonProperty("house_subtype") @Pattern(regexp="villa|house_c4") String houseSubtype,
    @JsonProperty("road_width_m") @DecimalMin("0.1") @DecimalMax("100") BigDecimal roadWidthM,
    @JsonProperty("frontage_width_m") @DecimalMin("0.1") @DecimalMax("500") BigDecimal frontageWidthM,
    @JsonProperty("street_name") @Size(max=200) String streetName,
    @JsonProperty("project_name") @Size(max=200) String projectName,
    @Min(1) @Max(30) Integer bathrooms,
    @JsonProperty("house_direction") @Size(max=50) String houseDirection,
    @JsonProperty("balcony_direction") @Size(max=50) String balconyDirection) {

    public Map<String,Object> modelInput() {
        if (("Đất nền".equals(category) && rooms != null) ||
            (!"Nhà ở".equals(category) && (floors != null || houseSubtype != null)) ||
            ("Căn hộ chung cư".equals(category) && (accessType != null || roadWidthM != null || frontageWidthM != null)))
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
        if (roadWidthM != null) value.put("road_width_m", roadWidthM.stripTrailingZeros());
        if (frontageWidthM != null) value.put("frontage_width_m", frontageWidthM.stripTrailingZeros());
        if (streetName != null && !streetName.isBlank()) value.put("street_name", streetName.strip());
        if (projectName != null && !projectName.isBlank()) value.put("project_name", projectName.strip());
        if (bathrooms != null) value.put("bathrooms", bathrooms);
        if (houseDirection != null && !houseDirection.isBlank()) value.put("house_direction", houseDirection.strip());
        if (balconyDirection != null && !balconyDirection.isBlank()) value.put("balcony_direction", balconyDirection.strip());
        return value;
    }

    @Override public String toString() { return "HistoryInput[redacted]"; }
}
