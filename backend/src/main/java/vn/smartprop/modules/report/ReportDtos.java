package vn.smartprop.modules.report;
import java.time.Instant;
import java.util.List;
import jakarta.validation.constraints.*;
public final class ReportDtos {
    public enum Reason { FAKE_IMAGES, INACCURATE_INFORMATION, SUSPECTED_SCAM, DUPLICATE, UNAVAILABLE, OTHER }
    public record Create(@NotNull Reason reasonCode,@NotBlank @Size(max=10000) String description,@Email @Size(max=254) String contactEmail) {}
    public record StatusPatch(@NotNull Report.Status status,@Positive Long assignedTo,@NotBlank @Size(max=4000) String note) {}
    public record Attachment(String id,String mimeType,long byteSize,String url,Instant createdAt) {}
    public record View(String id,Long reporterId,String propertyId,String reasonCode,String description,String contactEmail,Report.Status status,
        Long assignedTo,Long resolvedBy,String resolutionNote,Instant resolvedAt,Instant createdAt,Instant updatedAt,List<Attachment> attachments) {}
}