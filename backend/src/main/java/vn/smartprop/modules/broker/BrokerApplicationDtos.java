package vn.smartprop.modules.broker;

import jakarta.validation.constraints.*;
import java.time.Instant;

public final class BrokerApplicationDtos {
    private BrokerApplicationDtos() {}
    public enum ApplicantType { OWNER, AGENT }
    public enum Status { PENDING, APPROVED, REJECTED, NEEDS_INFORMATION, SUSPENDED }
    public enum Action { APPROVE, REJECT, REQUEST_INFORMATION, SUSPEND }
    public record Submit(@NotNull ApplicantType applicantType,
        @NotBlank @Size(max=150) String displayName,
        @NotBlank @Size(min=8,max=30) @Pattern(regexp="\\+?[0-9][0-9 ()-]{6,28}[0-9]") String contactPhone,
        @NotBlank @Size(max=200) String operatingArea,
        @NotBlank @Size(max=2000) String requestMessage,
        @NotNull @AssertTrue Boolean responsibilityAccepted,
        @Positive Integer expectedVersion) {
        @Override public String toString() { return "BrokerApplicationSubmit[redacted]"; }
    }
    public record Review(@NotNull Action action,@NotNull @Positive Integer expectedVersion,
                         @NotBlank @Size(max=2000) String reason) {
        @Override public String toString() { return "BrokerApplicationReview[redacted]"; }
    }
    public record View(String id,Long userId,ApplicantType applicantType,String displayName,String contactPhone,
        String operatingArea,String requestMessage,boolean responsibilityAccepted,Instant consentedAt,
        Status status,int contentVersion,Long reviewedBy,Action reviewAction,String reviewReason,
        Instant reviewedAt,Instant createdAt,Instant updatedAt) {}
    public record Mine(String status,boolean canPublish,boolean legacyPublisher,View application) {}
}
