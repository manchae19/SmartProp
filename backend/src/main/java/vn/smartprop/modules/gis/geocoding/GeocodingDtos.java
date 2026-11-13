package vn.smartprop.modules.gis.geocoding;

import jakarta.validation.constraints.*;
import java.util.List;

public final class GeocodingDtos {
    private GeocodingDtos() {}
    public enum Provider { GEOAPIFY, GOOGLE }
    public enum Accuracy { EXACT, INTERPOLATED, APPROXIMATE, UNKNOWN }
    public enum Level { EXACT_PROPERTY, BUILDING_ONLY, APPROXIMATE, UNKNOWN }
    public enum Precision { EXACT, APPROXIMATE_STREET, APPROXIMATE_AREA, PROJECT, MANUAL_UNVERIFIED, UNKNOWN }
    public record Availability(boolean available, Provider provider, String reason, String mapProvider, boolean storageAllowed) {}
    /** Provider metadata and verification are transient; never silently promoted to a property accuracy field. */
    public record Context(String countryCode, List<String> localities, List<String> districts, List<String> wards,
                          String resultType, Precision precision, boolean localityMatched, String warning, String street) {}
    public record Search(@NotBlank @Size(max=4000) String address,
                         @NotBlank @Size(max=100) String city,
                         @Size(max=100) String district, @Size(max=100) String ward,
                         @AssertTrue(message="Cần đồng ý gửi địa chỉ tới dịch vụ tìm vị trí") boolean shareAddress, boolean districtOnly) {
        public Search(String address,String city,String district,String ward,boolean shareAddress){this(address,city,district,ward,shareAddress,false);}
    }
    public record Candidate(String id, String formattedAddress, double latitude, double longitude,
                            Provider provider, Accuracy accuracy, Level locationLevel,
                            Double confidence, boolean addressMatched, boolean storageAllowed,
                            String mapProvider, String attribution, Context context) {
        Candidate reviewed(Context value) {
            return new Candidate(id,formattedAddress,latitude,longitude,provider,accuracy,locationLevel,confidence,
                addressMatched&&value.localityMatched(),storageAllowed,mapProvider,attribution,value);
        }
    }
    public record Result(String status, Provider provider, List<Candidate> candidates) {}
}
