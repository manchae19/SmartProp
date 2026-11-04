package vn.smartprop.modules.prediction;
import jakarta.validation.constraints.*;
import java.math.BigDecimal;
import vn.smartprop.modules.property.Property;
public record ValuationRequest(
    @NotNull Property.Type propertyType, @NotNull Property.Transaction transactionType,
    @NotNull @DecimalMin("0.01") @DecimalMax("9999999999") BigDecimal areaSqm,
    @NotBlank @Size(max=100) String locationFeature,
    @Size(max=100) String ward, @Min(0) @Max(32767) Integer bedrooms,
    @Size(max=255) String title, @Size(max=20000) String description) {
    @Override public String toString(){return "ValuationRequest[redacted]";}
}
