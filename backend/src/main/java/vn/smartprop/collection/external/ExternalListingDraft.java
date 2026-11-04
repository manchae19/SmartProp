package vn.smartprop.collection.external;

import com.fasterxml.jackson.databind.JsonNode;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;

public class ExternalListingDraft {
    public String recordKey;
    public String source;
    public String sourceListingId;
    public String title;
    public String detailUrl;
    public String category;
    public String transactionType = "SALE";
    public String transactionBasis;
    public BigDecimal price;
    public BigDecimal priceMillion;
    public BigDecimal areaSqm;
    public BigDecimal pricePerSqmMillion;
    public String district;
    public String addressRaw;
    public String qualityStatus = "VALID";
    public List<String> qualityIssues = new ArrayList<>();
    public String verificationStatus = "UNVERIFIED";
    public String duplicateGroup;
    public boolean isDuplicate = false;
    public boolean isProtectedHoldout = false;
    public Instant collectedAt;
    public JsonNode rawMetadata;

    // Helper fields for quality gate
    public String cleanAddress;
    public List<String> titleTokens = new ArrayList<>();
}
