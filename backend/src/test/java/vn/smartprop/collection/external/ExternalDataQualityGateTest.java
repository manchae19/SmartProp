package vn.smartprop.collection.external;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class ExternalDataQualityGateTest {

    private ExternalDataQualityGate gate;

    @BeforeEach
    void setUp() {
        gate = new ExternalDataQualityGate();
    }

    @Test
    @DisplayName("Should detect 404 or invalid title")
    void shouldDetect404OrInvalidTitle() {
        ExternalListingDraft d1 = new ExternalListingDraft();
        d1.title = "Trang không tìm thấy";
        d1.detailUrl = "https://example.com/item/1";
        d1.category = "Nhà ở";
        d1.priceMillion = new BigDecimal("1500");
        d1.areaSqm = new BigDecimal("80");
        d1.district = "Hải Châu";

        gate.evaluateSingleRecord(d1);
        assertTrue(d1.qualityIssues.contains(ExternalDataQualityGate.ISSUE_TITLE_ERROR_OR_404));

        ExternalListingDraft d2 = new ExternalListingDraft();
        d2.title = "cần bán"; // length < 10
        d2.detailUrl = "https://example.com/item/2";
        d2.category = "Nhà ở";
        d2.priceMillion = new BigDecimal("1500");
        d2.areaSqm = new BigDecimal("80");
        d2.district = "Hải Châu";

        gate.evaluateSingleRecord(d2);
        assertTrue(d2.qualityIssues.contains(ExternalDataQualityGate.ISSUE_TITLE_ERROR_OR_404));

        gate.clusterDuplicates(List.of(d1, d2));
        assertEquals(ExternalDataQualityGate.STATUS_REJECTED, d1.qualityStatus);
        assertEquals(ExternalDataQualityGate.STATUS_REJECTED, d2.qualityStatus);
    }

    @Test
    @DisplayName("Should detect multi-property listings")
    void shouldDetectMultiProperty() {
        ExternalListingDraft d = new ExternalListingDraft();
        d.title = "Bán 2 căn liền kề mặt tiền Nguyễn Tri Phương";
        d.detailUrl = "https://example.com/item/3";
        d.category = "Nhà ở";
        d.priceMillion = new BigDecimal("8500");
        d.areaSqm = new BigDecimal("150");
        d.district = "Thanh Khê";

        gate.evaluateSingleRecord(d);
        assertTrue(d.qualityIssues.contains(ExternalDataQualityGate.ISSUE_MULTI_PROPERTY));

        gate.clusterDuplicates(List.of(d));
        assertEquals(ExternalDataQualityGate.STATUS_NEEDS_REVIEW, d.qualityStatus);
    }

    @Test
    @DisplayName("Should detect category and URL mismatch")
    void shouldDetectCategoryMismatch() {
        ExternalListingDraft d = new ExternalListingDraft();
        d.title = "Bán lô đất đẹp kiệt ô tô Hòa Minh";
        d.detailUrl = "https://example.com/ban-nha-quan-lien-chieu/123";
        d.category = "Đất nền"; // URL has ban-nha
        d.priceMillion = new BigDecimal("2500");
        d.areaSqm = new BigDecimal("100");
        d.district = "Liên Chiểu";

        gate.evaluateSingleRecord(d);
        assertTrue(d.qualityIssues.contains(ExternalDataQualityGate.ISSUE_CATEGORY_MISMATCH));

        gate.clusterDuplicates(List.of(d));
        assertEquals(ExternalDataQualityGate.STATUS_NEEDS_REVIEW, d.qualityStatus);
    }

    @Test
    @DisplayName("Should detect missing details like district")
    void shouldDetectMissingDetails() {
        ExternalListingDraft d = new ExternalListingDraft();
        d.title = "Bán đất Hòa Xuân view sông";
        d.detailUrl = "https://example.com/ban-dat/123";
        d.category = "Đất nền";
        d.priceMillion = new BigDecimal("3200");
        d.areaSqm = new BigDecimal("100");
        d.district = null; // missing district

        gate.evaluateSingleRecord(d);
        assertTrue(d.qualityIssues.contains(ExternalDataQualityGate.ISSUE_MISSING_DISTRICT));

        gate.clusterDuplicates(List.of(d));
        assertEquals(ExternalDataQualityGate.STATUS_NEEDS_REVIEW, d.qualityStatus);
    }

    @Test
    @DisplayName("Should normalize Homedy SALE from URL /ban-")
    void shouldNormalizeHomedySale() {
        ExternalListingDraft d = new ExternalListingDraft();
        d.source = "homedy";
        d.detailUrl = "https://homedy.com/ban-nha-rieng-quan-cam-le-da-nang/item-123";
        d.title = "Bán nhà kiệt đường Nguyễn Hữu Thọ Cẩm Lệ";
        d.category = "Nhà ở";
        d.priceMillion = new BigDecimal("3500");
        d.areaSqm = new BigDecimal("100");
        d.district = "Cẩm Lệ";

        gate.evaluateSingleRecord(d);
        assertEquals("SALE", d.transactionType);
        assertEquals("INFERRED_FROM_URL", d.transactionBasis);
        assertEquals(ExternalDataQualityGate.STATUS_UNVERIFIED, d.verificationStatus);
    }

    @Test
    @DisplayName("Should cluster Truong Chinh near-duplicate group correctly")
    void shouldClusterTruongChinhGroup() {
        // Truong Chinh listings: homedy:2247057, homedy:2346049, homedy:2615601
        ExternalListingDraft tc1 = new ExternalListingDraft();
        tc1.recordKey = "homedy:2247057";
        tc1.source = "homedy";
        tc1.title = "Bán nhà cấp 4 kiệt Trường Chinh 118m2 giá rẻ 1,7 tỷ";
        tc1.category = "Nhà ở";
        tc1.price = new BigDecimal("1700000000");
        tc1.priceMillion = new BigDecimal("1700.0");
        tc1.areaSqm = new BigDecimal("118.0");
        tc1.district = "Cẩm Lệ";
        tc1.addressRaw = "Bán Nhà riêng Đường Trường Chinh - Phường Hòa Thọ Tây, Quận Cẩm Lệ, Đà Nẵng";
        tc1.detailUrl = "https://homedy.com/ban-nha-rieng-quan-cam-le-da-nang/tc1";

        ExternalListingDraft tc2 = new ExternalListingDraft();
        tc2.recordKey = "homedy:2346049";
        tc2.source = "homedy";
        tc2.title = "Bán nhà cấp 4 kiệt Trường Chinh quận Cẩm Lệ 118,5m2 giá rẻ 1,65 tỷ";
        tc2.category = "Nhà ở";
        tc2.price = new BigDecimal("1650000000");
        tc2.priceMillion = new BigDecimal("1650.0");
        tc2.areaSqm = new BigDecimal("118.0");
        tc2.district = "Cẩm Lệ";
        tc2.addressRaw = "Bán Nhà riêng Đường Trường Chinh - Phường Hòa Thọ Tây, Quận Cẩm Lệ, Đà Nẵng";
        tc2.detailUrl = "https://homedy.com/ban-nha-rieng-quan-cam-le-da-nang/tc2";

        ExternalListingDraft tc3 = new ExternalListingDraft();
        tc3.recordKey = "homedy:2615601";
        tc3.source = "homedy";
        tc3.title = "Bán nhà kiệt Trường Chinh gần cầu vượt Hoà Cầm, 120m2, giá rẻ 1,55 tỷ";
        tc3.category = "Nhà ở";
        tc3.price = new BigDecimal("1550000000");
        tc3.priceMillion = new BigDecimal("1550.0");
        tc3.areaSqm = new BigDecimal("120.0");
        tc3.district = "Cẩm Lệ";
        tc3.addressRaw = "Bán Nhà riêng Đường Trường Chinh - Phường Hòa Thọ Tây, Quận Cẩm Lệ, Đà Nẵng";
        tc3.detailUrl = "https://homedy.com/ban-nha-rieng-quan-cam-le-da-nang/tc3";

        // Unrelated distinct listing
        ExternalListingDraft other = new ExternalListingDraft();
        other.recordKey = "cafeland:9999999";
        other.source = "cafeland";
        other.title = "Bán biệt thự biển Sơn Trà view triệu đô";
        other.category = "Nhà ở";
        other.price = new BigDecimal("25000000000");
        other.priceMillion = new BigDecimal("25000.0");
        other.areaSqm = new BigDecimal("300.0");
        other.district = "Sơn Trà";
        other.addressRaw = "Đường Hoàng Sa, Phường Thọ Quang, Quận Sơn Trà, Đà Nẵng";
        other.detailUrl = "https://cafeland.vn/ban-nha-son-tra/item-999";

        List<ExternalListingDraft> all = List.of(tc1, tc2, tc3, other);
        for (ExternalListingDraft d : all) {
            gate.evaluateSingleRecord(d);
        }

        List<ExternalDataQualityGate.DuplicateGroupSummary> summaries = gate.clusterDuplicates(all);

        // Verification
        assertEquals(1, summaries.size(), "Should produce exactly 1 duplicate group");
        ExternalDataQualityGate.DuplicateGroupSummary group = summaries.get(0);
        assertEquals("group_dup_truong_chinh_cam_le", group.groupId());
        assertEquals(3, group.listingCount());

        assertTrue(tc1.isDuplicate);
        assertTrue(tc2.isDuplicate);
        assertTrue(tc3.isDuplicate);
        assertFalse(other.isDuplicate);

        assertEquals("group_dup_truong_chinh_cam_le", tc1.duplicateGroup);
        assertEquals("group_dup_truong_chinh_cam_le", tc2.duplicateGroup);
        assertEquals("group_dup_truong_chinh_cam_le", tc3.duplicateGroup);
        assertNull(other.duplicateGroup);

        assertTrue(tc1.qualityIssues.contains(ExternalDataQualityGate.ISSUE_NEAR_DUPLICATE));
        assertTrue(tc2.qualityIssues.contains(ExternalDataQualityGate.ISSUE_NEAR_DUPLICATE));
        assertTrue(tc3.qualityIssues.contains(ExternalDataQualityGate.ISSUE_NEAR_DUPLICATE));

        assertEquals(ExternalDataQualityGate.STATUS_NEEDS_REVIEW, tc1.qualityStatus);
        assertEquals(ExternalDataQualityGate.STATUS_NEEDS_REVIEW, tc2.qualityStatus);
        assertEquals(ExternalDataQualityGate.STATUS_NEEDS_REVIEW, tc3.qualityStatus);
        assertEquals(ExternalDataQualityGate.STATUS_VALID, other.qualityStatus);

        assertEquals(ExternalDataQualityGate.STATUS_UNVERIFIED, tc1.verificationStatus);
        assertEquals(ExternalDataQualityGate.STATUS_UNVERIFIED, tc2.verificationStatus);
        assertEquals(ExternalDataQualityGate.STATUS_UNVERIFIED, tc3.verificationStatus);
        assertEquals(ExternalDataQualityGate.STATUS_UNVERIFIED, other.verificationStatus);
    }
}
