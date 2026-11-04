package vn.smartprop.collection.external;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.io.*;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.*;

@Service
public class ExternalListingImportService {

    private static final Logger log = LoggerFactory.getLogger(ExternalListingImportService.class);

    private final ExternalListingRepository listingRepository;
    private final ExternalDuplicateGroupRepository duplicateGroupRepository;
    private final ExternalDataQualityGate qualityGate;
    private final ObjectMapper objectMapper;

    public ExternalListingImportService(
            ExternalListingRepository listingRepository,
            ExternalDuplicateGroupRepository duplicateGroupRepository,
            ExternalDataQualityGate qualityGate,
            ObjectMapper objectMapper
    ) {
        this.listingRepository = listingRepository;
        this.duplicateGroupRepository = duplicateGroupRepository;
        this.qualityGate = qualityGate;
        this.objectMapper = objectMapper;
    }

    public record ImportSummary(
            int totalProcessed,
            int insertedCount,
            int updatedCount,
            int validCount,
            int needsReviewCount,
            int rejectedCount,
            int duplicateGroupCount,
            int duplicateListingCount,
            boolean truongChinhGroupFound,
            String truongChinhGroupId,
            List<String> truongChinhMembers
    ) {}

    public List<ExternalListingDraft> parseCsv(File csvFile) throws IOException {
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(new FileInputStream(csvFile), StandardCharsets.UTF_8))) {
            return parseCsv(reader);
        }
    }

    public List<ExternalListingDraft> parseCsv(BufferedReader in) throws IOException {
        List<List<String>> rows = readCsvRows(in);
        if (rows.isEmpty()) {
            return Collections.emptyList();
        }

        List<String> headers = rows.get(0);
        Map<String, Integer> colMap = new HashMap<>();
        for (int i = 0; i < headers.size(); i++) {
            String colName = headers.get(i).replace("\uFEFF", "").trim();
            colMap.put(colName, i);
        }

        List<ExternalListingDraft> drafts = new ArrayList<>(rows.size() - 1);
        for (int r = 1; r < rows.size(); r++) {
            List<String> row = rows.get(r);
            if (row.size() < headers.size() && row.stream().allMatch(String::isBlank)) {
                continue;
            }

            ExternalListingDraft draft = new ExternalListingDraft();
            draft.recordKey = getCol(row, colMap, "record_key");
            draft.source = getCol(row, colMap, "source");
            draft.sourceListingId = getCol(row, colMap, "source_listing_id");
            draft.title = getCol(row, colMap, "title");
            draft.detailUrl = getCol(row, colMap, "detail_url");
            draft.category = getCol(row, colMap, "category");
            draft.district = getCol(row, colMap, "district");
            draft.addressRaw = getCol(row, colMap, "address_raw");
            draft.transactionBasis = getCol(row, colMap, "transaction_basis");

            String priceMilStr = getCol(row, colMap, "price_million");
            if (priceMilStr != null && !priceMilStr.isBlank()) {
                try {
                    draft.priceMillion = new BigDecimal(priceMilStr);
                    draft.price = draft.priceMillion.multiply(new BigDecimal("1000000"));
                } catch (NumberFormatException ignored) {}
            }

            String areaStr = getCol(row, colMap, "area_sqm");
            if (areaStr != null && !areaStr.isBlank()) {
                try {
                    draft.areaSqm = new BigDecimal(areaStr);
                } catch (NumberFormatException ignored) {}
            }

            String pricePerSqmStr = getCol(row, colMap, "price_per_sqm_million");
            if (pricePerSqmStr != null && !pricePerSqmStr.isBlank()) {
                try {
                    draft.pricePerSqmMillion = new BigDecimal(pricePerSqmStr);
                } catch (NumberFormatException ignored) {}
            }

            String collectedAtStr = getCol(row, colMap, "collected_at");
            if (collectedAtStr != null && !collectedAtStr.isBlank()) {
                try {
                    draft.collectedAt = Instant.parse(collectedAtStr);
                } catch (Exception ignored) {}
            }

            String holdoutStr = getCol(row, colMap, "protected_holdout");
            draft.isProtectedHoldout = Boolean.parseBoolean(holdoutStr);

            // Raw metadata
            ObjectNode meta = objectMapper.createObjectNode();
            putMeta(meta, "assigned_split", getCol(row, colMap, "assigned_split"));
            putMeta(meta, "training_allowed", getCol(row, colMap, "training_allowed"));
            putMeta(meta, "original_price_million", getCol(row, colMap, "original_price_million"));
            putMeta(meta, "original_area_sqm", getCol(row, colMap, "original_area_sqm"));
            putMeta(meta, "original_category", getCol(row, colMap, "original_category"));
            putMeta(meta, "review_codes", getCol(row, colMap, "review_codes"));
            putMeta(meta, "displayed_date", getCol(row, colMap, "displayed_date"));
            putMeta(meta, "age_days", getCol(row, colMap, "age_days"));
            putMeta(meta, "transaction_raw", getCol(row, colMap, "transaction_raw"));
            putMeta(meta, "status_crawler", getCol(row, colMap, "status"));
            putMeta(meta, "duplicate_candidate_group_crawler", getCol(row, colMap, "duplicate_candidate_group"));
            draft.rawMetadata = meta;

            drafts.add(draft);
        }
        return drafts;
    }

    @Transactional
    public ImportSummary importCandidates(File csvFile) throws IOException {
        List<ExternalListingDraft> drafts = parseCsv(csvFile);
        return processAndSave(drafts);
    }

    @Transactional
    public ImportSummary processAndSave(List<ExternalListingDraft> drafts) {
        log.info("Processing {} external listing drafts through Data Quality Gate...", drafts.size());

        for (ExternalListingDraft draft : drafts) {
            qualityGate.evaluateSingleRecord(draft);
        }

        List<ExternalDataQualityGate.DuplicateGroupSummary> groupSummaries = qualityGate.clusterDuplicates(drafts);

        // Save duplicate groups
        for (ExternalDataQualityGate.DuplicateGroupSummary gs : groupSummaries) {
            ExternalDuplicateGroup g = duplicateGroupRepository.findById(gs.groupId())
                    .orElseGet(ExternalDuplicateGroup::new);
            g.groupId = gs.groupId();
            g.name = gs.name();
            g.category = gs.category();
            g.district = gs.district();
            g.listingCount = gs.listingCount();
            g.minPrice = gs.minPrice();
            g.maxPrice = gs.maxPrice();
            g.minArea = gs.minArea();
            g.maxArea = gs.maxArea();
            duplicateGroupRepository.save(g);
        }

        int inserted = 0;
        int updated = 0;
        int valid = 0;
        int needsReview = 0;
        int rejected = 0;
        int duplicateListings = 0;

        String tcGroupId = null;
        List<String> tcMembers = new ArrayList<>();
        Set<String> targetTcKeys = Set.of("homedy:2615601", "homedy:2346049", "homedy:2247057");

        for (ExternalListingDraft draft : drafts) {
            if (ExternalDataQualityGate.STATUS_VALID.equals(draft.qualityStatus)) valid++;
            else if (ExternalDataQualityGate.STATUS_NEEDS_REVIEW.equals(draft.qualityStatus)) needsReview++;
            else if (ExternalDataQualityGate.STATUS_REJECTED.equals(draft.qualityStatus)) rejected++;

            if (draft.isDuplicate) duplicateListings++;

            if (targetTcKeys.contains(draft.recordKey)) {
                tcGroupId = draft.duplicateGroup;
                tcMembers.add(draft.recordKey);
            }

            Optional<ExternalListing> existingOpt = listingRepository.findByRecordKey(draft.recordKey);
            ExternalListing entity;
            if (existingOpt.isPresent()) {
                entity = existingOpt.get();
                updated++;
            } else {
                entity = new ExternalListing();
                inserted++;
            }

            entity.recordKey = draft.recordKey;
            entity.source = draft.source;
            entity.sourceListingId = draft.sourceListingId;
            entity.title = draft.title;
            entity.detailUrl = draft.detailUrl;
            entity.category = draft.category;
            entity.transactionType = draft.transactionType;
            entity.transactionBasis = draft.transactionBasis;
            entity.price = draft.price != null ? draft.price : BigDecimal.ZERO;
            entity.priceMillion = draft.priceMillion != null ? draft.priceMillion : BigDecimal.ZERO;
            entity.areaSqm = draft.areaSqm != null ? draft.areaSqm : BigDecimal.ZERO;
            entity.pricePerSqmMillion = draft.pricePerSqmMillion;
            entity.district = draft.district;
            entity.addressRaw = draft.addressRaw;
            entity.qualityStatus = draft.qualityStatus;

            ArrayNode issuesArray = objectMapper.createArrayNode();
            for (String issue : draft.qualityIssues) {
                issuesArray.add(issue);
            }
            entity.qualityIssues = issuesArray;

            entity.verificationStatus = draft.verificationStatus;
            entity.duplicateGroup = draft.duplicateGroup;
            entity.isDuplicate = draft.isDuplicate;
            entity.isProtectedHoldout = draft.isProtectedHoldout;
            entity.collectedAt = draft.collectedAt;
            entity.rawMetadata = draft.rawMetadata != null ? draft.rawMetadata : objectMapper.createObjectNode();

            listingRepository.save(entity);
        }

        boolean tcFound = tcMembers.containsAll(targetTcKeys);

        log.info("Import completed: total={}, inserted={}, updated={}, valid={}, needsReview={}, rejected={}, duplicateGroups={}",
                drafts.size(), inserted, updated, valid, needsReview, rejected, groupSummaries.size());

        return new ImportSummary(
                drafts.size(),
                inserted,
                updated,
                valid,
                needsReview,
                rejected,
                groupSummaries.size(),
                duplicateListings,
                tcFound,
                tcGroupId,
                tcMembers
        );
    }

    private static String getCol(List<String> row, Map<String, Integer> colMap, String colName) {
        Integer idx = colMap.get(colName);
        if (idx == null || idx >= row.size()) return null;
        String val = row.get(idx);
        return (val == null || val.isBlank() || "NaN".equals(val) || "nan".equals(val)) ? null : val.trim();
    }

    private static void putMeta(ObjectNode node, String key, String val) {
        if (val != null) {
            node.put(key, val);
        }
    }

    public static List<List<String>> readCsvRows(BufferedReader in) throws IOException {
        List<List<String>> rows = new ArrayList<>();
        List<String> currentRow = new ArrayList<>();
        StringBuilder curVal = new StringBuilder();
        boolean inQuotes = false;
        int ch;
        while ((ch = in.read()) != -1) {
            char c = (char) ch;
            if (inQuotes) {
                if (c == '"') {
                    in.mark(1);
                    int next = in.read();
                    if (next == '"') {
                        curVal.append('"');
                    } else {
                        inQuotes = false;
                        if (next != -1) in.reset();
                    }
                } else {
                    curVal.append(c);
                }
            } else {
                if (c == '"') {
                    inQuotes = true;
                } else if (c == ',') {
                    currentRow.add(curVal.toString());
                    curVal.setLength(0);
                } else if (c == '\r') {
                    // Ignore carriage return
                } else if (c == '\n') {
                    currentRow.add(curVal.toString());
                    curVal.setLength(0);
                    rows.add(currentRow);
                    currentRow = new ArrayList<>();
                } else {
                    curVal.append(c);
                }
            }
        }
        if (curVal.length() > 0 || !currentRow.isEmpty()) {
            currentRow.add(curVal.toString());
            rows.add(currentRow);
        }
        return rows;
    }
}
