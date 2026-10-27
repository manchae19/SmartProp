package vn.smartprop.geocoding;

import jakarta.validation.constraints.*;
import java.util.List;

public final class GeocodingDtos {
    private GeocodingDtos() {}
    public enum Provider { GEOAPIFY, GOOGLE }
    public enum Accuracy { EXACT, INTERPOLATED, APPROXIMATE, UNKNOWN }
    public enum Level { EXACT_PROPERTY, BUILDING_ONLY, APPROXIMATE, UNKNOWN }
    public record Search(@NotBlank @Size(max=4000) String address,
                         @NotBlank @Size(max=100) String city,
                         @Size(max=100) String district, @Size(max=100) String ward,
                         @AssertTrue(message="Cần đồng ý gửi địa chỉ tới dịch vụ tìm vị trí") boolean shareAddress) {}
    public record Candidate(String id, String formattedAddress, double latitude, double longitude,
                            Provider provider, Accuracy accuracy, Level locationLevel,
                            Double confidence, boolean addressMatched, boolean storageAllowed,
                            String mapProvider, String attribution) {}
    public record Result(String status, Provider provider, List<Candidate> candidates) {}
}
