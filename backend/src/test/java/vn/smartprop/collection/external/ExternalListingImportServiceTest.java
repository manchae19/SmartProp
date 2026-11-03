package vn.smartprop.collection.external;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

import java.io.BufferedReader;
import java.io.StringReader;
import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

class ExternalListingImportServiceTest {

    private ExternalListingRepository listingRepository;
    private ExternalDuplicateGroupRepository duplicateGroupRepository;
    private ExternalDataQualityGate qualityGate;
    private ObjectMapper objectMapper;
    private ExternalListingImportService service;

    @BeforeEach
    void setUp() {
        listingRepository = mock(ExternalListingRepository.class);
        duplicateGroupRepository = mock(ExternalDuplicateGroupRepository.class);
        qualityGate = new ExternalDataQualityGate();
        objectMapper = new ObjectMapper();
        service = new ExternalListingImportService(listingRepository, duplicateGroupRepository, qualityGate, objectMapper);
    }

    @Test
    @DisplayName("Should parse CSV with quoted commas and multiline correctly")
    void shouldParseCsvCorrectly() throws Exception {
        String csvContent = """
                record_key,source,source_listing_id,detail_url,title,category,district,address_raw,price_million,area_sqm,price_per_sqm_million,collected_at,protected_holdout,assigned_split,training_allowed,transaction_basis
                homedy:1001,homedy,1001,https://homedy.com/ban-nha/1,"Nhà đẹp, kiệt ô tô",Nhà ở,Hải Châu,"Hải Châu, Đà Nẵng",3500.0,100.0,35.0,2026-10-10T13:26:47.808526+00:00,False,train,True,source_sale_url_and_detail_snapshot
                cafeland:2002,cafeland,2002,https://cafeland.vn/dat/2,"Đất nền
                view sông",Đất nền,Cẩm Lệ,"Cẩm Lệ, Đà Nẵng",2200.0,90.0,24.44,2026-10-10T13:28:08.550370+00:00,True,reserved_holdout,False,explicit_source_field
                """;

        BufferedReader reader = new BufferedReader(new StringReader(csvContent));
        List<ExternalListingDraft> drafts = service.parseCsv(reader);

        assertEquals(2, drafts.size());

        ExternalListingDraft d1 = drafts.get(0);
        assertEquals("homedy:1001", d1.recordKey);
        assertEquals("Nhà đẹp, kiệt ô tô", d1.title);
        assertEquals(new BigDecimal("3500.0"), d1.priceMillion);
        assertEquals(new BigDecimal("3500000000.0"), d1.price);
        assertFalse(d1.isProtectedHoldout);
        assertEquals("train", d1.rawMetadata.get("assigned_split").asText());

        ExternalListingDraft d2 = drafts.get(1);
        assertEquals("cafeland:2002", d2.recordKey);
        assertTrue(d2.title.contains("view sông"));
        assertTrue(d2.isProtectedHoldout);
        assertEquals("reserved_holdout", d2.rawMetadata.get("assigned_split").asText());
    }

    @Test
    @DisplayName("Should be idempotent: inserting new records on first run, updating on second run")
    void shouldBeIdempotentOnSubsequentRuns() {
        ExternalListingDraft draft = new ExternalListingDraft();
        draft.recordKey = "homedy:1001";
        draft.source = "homedy";
        draft.title = "Nhà đẹp đường Bạch Đằng";
        draft.detailUrl = "https://homedy.com/ban-nha/1";
        draft.category = "Nhà ở";
        draft.priceMillion = new BigDecimal("5000");
        draft.price = new BigDecimal("5000000000");
        draft.areaSqm = new BigDecimal("100");
        draft.district = "Hải Châu";
        draft.addressRaw = "Đường Bạch Đằng, Hải Châu, Đà Nẵng";
        draft.rawMetadata = objectMapper.createObjectNode();

        // 1st run: record does not exist
        when(listingRepository.findByRecordKey("homedy:1001")).thenReturn(Optional.empty());

        ExternalListing savedEntity = new ExternalListing();
        savedEntity.id = 1L;
        savedEntity.recordKey = "homedy:1001";
        when(listingRepository.save(any(ExternalListing.class))).thenReturn(savedEntity);

        ExternalListingImportService.ImportSummary summary1 = service.processAndSave(new ArrayList<>(List.of(draft)));
        assertEquals(1, summary1.insertedCount());
        assertEquals(0, summary1.updatedCount());
        assertEquals(1, summary1.totalProcessed());

        // 2nd run: record exists
        when(listingRepository.findByRecordKey("homedy:1001")).thenReturn(Optional.of(savedEntity));

        ExternalListingImportService.ImportSummary summary2 = service.processAndSave(new ArrayList<>(List.of(draft)));
        assertEquals(0, summary2.insertedCount());
        assertEquals(1, summary2.updatedCount());
        assertEquals(1, summary2.totalProcessed());

        verify(listingRepository, times(2)).save(any(ExternalListing.class));
    }

    @Test
    @DisplayName("Should successfully parse and evaluate the real eligible.csv dataset (3,204 rows)")
    void shouldParseAndEvaluateRealDataset() throws Exception {
        java.io.File realCsv = new java.io.File("..\\ai-services\\app\\data\\processed\\remaining_diversity_review\\runs\\518bbc989587326c\\eligible.csv");
        org.junit.jupiter.api.Assumptions.assumeTrue(realCsv.exists(), "real eligible.csv exists");

        List<ExternalListingDraft> drafts = service.parseCsv(realCsv);
        assertEquals(3204, drafts.size(), "Should parse exactly 3,204 rows");

        for (ExternalListingDraft draft : drafts) {
            qualityGate.evaluateSingleRecord(draft);
        }

        List<ExternalDataQualityGate.DuplicateGroupSummary> duplicateGroups = qualityGate.clusterDuplicates(drafts);
        System.out.println("Java duplicateGroups size: " + duplicateGroups.size());

        long valid = drafts.stream().filter(d -> "VALID".equals(d.qualityStatus)).count();
        long needsReview = drafts.stream().filter(d -> "NEEDS_REVIEW".equals(d.qualityStatus)).count();
        long rejected = drafts.stream().filter(d -> "REJECTED".equals(d.qualityStatus)).count();
        long duplicates = drafts.stream().filter(d -> d.isDuplicate).count();

        System.out.println("Java valid: " + valid + ", needsReview: " + needsReview + ", rejected: " + rejected + ", duplicates: " + duplicates);

        assertEquals(333, duplicateGroups.size());
        assertEquals(1721, valid);
        assertEquals(1421, needsReview);
        assertEquals(62, rejected);
        assertEquals(1026, duplicates);

        // Check Truong Chinh listings
        ExternalListingDraft tc1 = drafts.stream().filter(d -> "homedy:2247057".equals(d.recordKey)).findFirst().orElseThrow();
        ExternalListingDraft tc2 = drafts.stream().filter(d -> "homedy:2346049".equals(d.recordKey)).findFirst().orElseThrow();
        ExternalListingDraft tc3 = drafts.stream().filter(d -> "homedy:2615601".equals(d.recordKey)).findFirst().orElseThrow();

        assertEquals("group_dup_truong_chinh_cam_le", tc1.duplicateGroup);
        assertEquals("group_dup_truong_chinh_cam_le", tc2.duplicateGroup);
        assertEquals("group_dup_truong_chinh_cam_le", tc3.duplicateGroup);

        assertTrue(tc1.isDuplicate);
        assertTrue(tc2.isDuplicate);
        assertTrue(tc3.isDuplicate);

        assertEquals("NEEDS_REVIEW", tc1.qualityStatus);
        assertEquals("UNVERIFIED", tc1.verificationStatus);
        assertEquals("SALE", tc1.transactionType);
        assertEquals("INFERRED_FROM_URL", tc1.transactionBasis);
    }
}
