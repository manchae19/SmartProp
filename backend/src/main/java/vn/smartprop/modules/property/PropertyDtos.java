package vn.smartprop.modules.property;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import jakarta.validation.constraints.*;
public final class PropertyDtos {
    public record Write(
        @Size(max=255) @Pattern(regexp="(?s).*\\S.*") String title,@Size(max=20000) String description,
        Property.Type propertyType,Property.Transaction transactionType,
        @DecimalMin("0") @Digits(integer=16,fraction=2) BigDecimal price,@Pattern(regexp="VND") String currency,
        Property.PriceUnit priceUnit,@DecimalMin(value="0",inclusive=false) @Digits(integer=10,fraction=2) BigDecimal areaSqm,
        @Min(0) Short bedrooms,@Min(0) Short bathrooms,@Size(max=30) String floor,@Size(max=50) String block,
        @Size(max=30) String direction,@Size(max=4000) String address,@Size(max=100) @Pattern(regexp="(?s).*\\S.*") String city,
        @Size(max=100) String district,@Size(max=100) String ward,
        @DecimalMin("-90") @DecimalMax("90") Double latitude,
        @DecimalMin(value="-180",inclusive=false) @DecimalMax("180") Double longitude,
        String projectId,@Size(max=150) String contactName,
        @Size(max=30) @Pattern(regexp="[+0-9 ()-]*") String contactPhone,@Email @Size(max=254) String contactEmail,
        @Size(max=50) List<@NotBlank @Size(max=80) String> declaredAmenities) {}
    public record Version(@NotNull @Positive Integer expectedVersion) {}
    public record Image(String id,String url,int sortOrder,boolean cover) {}
    public record View(String id,String projectId,String title,String description,Property.Type propertyType,
        Property.Transaction transactionType,BigDecimal price,String currency,Property.PriceUnit priceUnit,
        BigDecimal areaSqm,Short bedrooms,Short bathrooms,String floor,String block,String direction,
        String address,String city,String district,String ward,double latitude,double longitude,
        List<String> declaredAmenities,Property.Status status,int contentVersion,Instant publishedAt,
        Instant expiresAt,Instant createdAt,Instant updatedAt,List<Image> images,String listingCode) {
        @com.fasterxml.jackson.annotation.JsonProperty("priceExact")
        public String priceExact() { return price == null ? null : price.toPlainString(); }
        @com.fasterxml.jackson.annotation.JsonProperty("areaSqmExact")
        public String areaSqmExact() { return areaSqm == null ? null : areaSqm.toPlainString(); }
    }
    public record Managed(View property,Long ownerId,String contactName,String contactPhone,String contactEmail) {}
}