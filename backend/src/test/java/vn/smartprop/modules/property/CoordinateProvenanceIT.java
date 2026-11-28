package vn.smartprop.modules.property;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.nullValue;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.util.List;
import java.util.Map;
import java.util.UUID;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.request.RequestPostProcessor;

import vn.smartprop.modules.user.User;
import vn.smartprop.modules.user.UserRepository;

/**
 * Coordinate Provenance V1 — HTTP contract test với Spring Security thật, controller
 * thật, MySQL thật.
 *
 * <p>Chạy trên DB cô lập (biến {@code DB_URL}). Bỏ qua khi thiếu cấu hình để clone
 * vẫn build được.
 *
 * <p>Kiểm chứng bảy blocker của review:
 * <ul>
 *   <li>Transaction verify không ném {@code IllegalTransactionStateException}.</li>
 *   <li>{@code expectedRevision} cũ trả 409, không xác minh nhầm bản mới.</li>
 *   <li>Public detail trả audit thật, không phải {@code absent()}.</li>
 *   <li>Provenance là {@code UNKNOWN}, không tự khai {@code USER_PINNED}.</li>
 *   <li>Audit là bắt buộc — không có nhánh bỏ qua âm thầm.</li>
 *   <li>Eligibility cấp thửa không vượt quá bằng chứng.</li>
 * </ul>
 */
@SpringBootTest
@AutoConfigureMockMvc
@EnabledIfEnvironmentVariable(named = "DB_URL", matches = ".+")
class CoordinateProvenanceIT {

    @Autowired MockMvc mvc;
    @Autowired UserRepository users;
    @Autowired JdbcTemplate jdbc;

    private Long brokerId;
    private Long adminId;
    private Long activeNonOwnerId;
    private final List<String> createdProperties = new java.util.ArrayList<>();

    @BeforeEach
    void setUp() {
        List<User> staff = users.findAll().stream()
            .filter(u -> u.deletedAt == null && u.status == User.Status.ACTIVE)
            .toList();
        brokerId = staff.stream()
            .filter(u -> u.role == User.Role.BROKER || u.role == User.Role.ADMIN)
            .map(u -> u.id).findFirst()
            .orElseThrow(() -> new IllegalStateException("cần một BROKER/ADMIN đang hoạt động"));
        adminId = staff.stream()
            .filter(u -> u.role == User.Role.ADMIN)
            .map(u -> u.id).findFirst()
            .orElseThrow(() -> new IllegalStateException("cần một ADMIN đang hoạt động"));
        activeNonOwnerId = staff.stream()
            .filter(u -> u.role == User.Role.BUYER && u.status == User.Status.ACTIVE)
            .map(u -> u.id).findFirst()
            .orElseThrow(() -> new IllegalStateException("cần một subject active khác chủ tin"));
    }

    @AfterEach
    void cleanUp() {
        for (String id : createdProperties) {
            jdbc.update("DELETE FROM property_coordinate_audit WHERE property_id = ?", id);
            jdbc.update("DELETE FROM property_listing_code_allocations WHERE property_id = ?", id);
            jdbc.update("DELETE FROM properties WHERE id = ?", id);
        }
        createdProperties.clear();
    }

    /** BROKER: cần ROLE_BROKER cho POST/PATCH /api/v1/properties. */
    private RequestPostProcessor as(Long userId) {
        return jwt().jwt(j -> j.subject(String.valueOf(userId)))
                    .authorities(new org.springframework.security.core.authority.SimpleGrantedAuthority("ROLE_BROKER"));
    }

    /** ADMIN cần authority ROLE_ADMIN cho các endpoint /api/v1/admin/**. */
    private RequestPostProcessor asAdmin(Long userId) {
        return jwt().jwt(j -> j.subject(String.valueOf(userId)))
                    .authorities(new org.springframework.security.core.authority.SimpleGrantedAuthority("ROLE_ADMIN"));
    }

    private String createProperty(double lat, double lon, String address, String district, String ward)
            throws Exception {
        String body = """
            {"title":"Coordinate IT fixture","propertyType":"HOUSE","transactionType":"SALE",
             "price":1000000000,"priceUnit":"TOTAL","areaSqm":50.0,
             "address":"%s","city":"Da Nang","district":"%s","ward":"%s",
             "latitude":%s,"longitude":%s}
            """.formatted(address, district, ward, lat, lon);
        String response = mvc.perform(post("/api/v1/properties").with(as(brokerId))
                .contentType(MediaType.APPLICATION_JSON).content(body))
            .andExpect(status().isCreated())
            .andReturn().getResponse().getContentAsString();
        String id = com.jayway.jsonpath.JsonPath.read(response, "$.property.id");
        createdProperties.add(id);
        return id;
    }

    // ---------- A. Create ----------

    @Test
    void createWritesAuditWithUnknownProvenance() throws Exception {
        String id = createProperty(16.0430, 108.1840, "Đường Tôn Đản, Hòa An", "Cẩm Lệ", "Hòa An");

        Map<String, Object> row = jdbc.queryForMap("""
            SELECT coordinate_source, accuracy_level, accuracy_meters, verification_status,
                   revision, geographic_validation_status
            FROM property_coordinate_audit WHERE property_id = ? AND superseded_at IS NULL
            """, id);

        // Blocker 4: request chỉ mang lat/lon, không chứng minh thao tác ghim bản đồ.
        assertThat(row.get("coordinate_source")).isEqualTo("UNKNOWN");
        assertThat(row.get("accuracy_level")).isEqualTo("UNKNOWN");
        assertThat(row.get("accuracy_meters")).isNull();
        assertThat(row.get("verification_status")).isEqualTo("UNVERIFIED");
        assertThat(row.get("revision")).isEqualTo(1);
        assertThat(row.get("geographic_validation_status")).isNotNull();
    }

    @Test
    void createResponseCarriesCoordinateBlock() throws Exception {
        String body = """
            {"title":"Coord block fixture","propertyType":"HOUSE","transactionType":"SALE",
             "price":1000000000,"priceUnit":"TOTAL","areaSqm":50.0,
             "address":"Đường Tôn Đản, Hòa An","city":"Da Nang","district":"Cẩm Lệ","ward":"Hòa An",
             "latitude":16.0430,"longitude":108.1840}
            """;
        String response = mvc.perform(post("/api/v1/properties").with(as(brokerId))
                .contentType(MediaType.APPLICATION_JSON).content(body))
            .andExpect(status().isCreated())
            .andExpect(jsonPath("$.property.coordinate.coordinateSource").value("UNKNOWN"))
            .andExpect(jsonPath("$.property.coordinate.verificationStatus").value("UNVERIFIED"))
            .andExpect(jsonPath("$.property.coordinate.parcelAnalysisEligible").value(false))
            .andReturn().getResponse().getContentAsString();
        createdProperties.add(com.jayway.jsonpath.JsonPath.read(response, "$.property.id"));
    }

    // ---------- B. Patch ----------

    @Test
    void patchTitleOnlyDoesNotCreateNewRevision() throws Exception {
        String id = createProperty(16.0430, 108.1840, "Đường Tôn Đản, Hòa An", "Cẩm Lệ", "Hòa An");

        mvc.perform(patch("/api/v1/properties/" + id).param("expectedVersion", "1").with(as(brokerId))
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {"title":"Coordinate IT fixture renamed","propertyType":"HOUSE",
                     "transactionType":"SALE","price":1000000000,"priceUnit":"TOTAL","areaSqm":50.0,
                     "address":"Đường Tôn Đản, Hòa An","city":"Da Nang","district":"Cẩm Lệ",
                     "ward":"Hòa An","latitude":16.0430,"longitude":108.1840}
                    """))
            .andExpect(status().isOk());

        Integer revisions = jdbc.queryForObject(
            "SELECT COUNT(*) FROM property_coordinate_audit WHERE property_id = ?",
            Integer.class, id);
        assertThat(revisions).as("không đổi vị trí thì không tạo revision mới").isEqualTo(1);
    }

    @Test
    void patchCoordinateCreatesNewRevisionAndSupersedesOld() throws Exception {
        String id = createProperty(16.0430, 108.1840, "Đường Tôn Đản, Hòa An", "Cẩm Lệ", "Hòa An");

        mvc.perform(patch("/api/v1/properties/" + id).param("expectedVersion", "1").with(as(brokerId))
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {"title":"Coordinate IT fixture","propertyType":"HOUSE",
                     "transactionType":"SALE","price":1000000000,"priceUnit":"TOTAL","areaSqm":50.0,
                     "address":"Đường Tôn Đản, Hòa An","city":"Da Nang","district":"Cẩm Lệ",
                     "ward":"Hòa An","latitude":16.0500,"longitude":108.1900}
                    """))
            .andExpect(status().isOk());

        Integer current = jdbc.queryForObject("""
            SELECT COUNT(*) FROM property_coordinate_audit
            WHERE property_id = ? AND superseded_at IS NULL
            """, Integer.class, id);
        Integer total = jdbc.queryForObject(
            "SELECT COUNT(*) FROM property_coordinate_audit WHERE property_id = ?",
            Integer.class, id);
        assertThat(current).as("chỉ một audit hiện hành").isEqualTo(1);
        assertThat(total).as("lịch sử giữ cả bản cũ").isEqualTo(2);
    }

    @Test
    void patchAddressOnlyCreatesNewRevision() throws Exception {
        String id = createProperty(16.0430, 108.1840, "Đường Tôn Đản, Hòa An", "Cẩm Lệ", "Hòa An");

        mvc.perform(patch("/api/v1/properties/" + id).param("expectedVersion", "1").with(as(brokerId))
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {"title":"Coordinate IT fixture","propertyType":"HOUSE",
                     "transactionType":"SALE","price":1000000000,"priceUnit":"TOTAL","areaSqm":50.0,
                     "address":"Đường Tôn Đản, Hòa Phát","city":"Da Nang","district":"Cẩm Lệ",
                     "ward":"Hòa Phát","latitude":16.0430,"longitude":108.1840}
                    """))
            .andExpect(status().isOk());

        Integer total = jdbc.queryForObject(
            "SELECT COUNT(*) FROM property_coordinate_audit WHERE property_id = ?",
            Integer.class, id);
        assertThat(total).as("đổi địa chỉ phải tạo revision mới").isEqualTo(2);
    }

    // ---------- C. Verify ----------

    @Test
    void adminVerifySucceedsWithoutTransactionException() throws Exception {
        String id = createProperty(16.0430, 108.1840, "Đường Tôn Đản, Hòa An", "Cẩm Lệ", "Hòa An");

        mvc.perform(post("/api/v1/properties/" + id + "/coordinate/verify").with(asAdmin(adminId))
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {"expectedRevision":1,"verificationStatus":"VERIFIED",
                     "verificationMethod":"CADASTRAL_RECORD","evidenceReference":"IT-EVIDENCE-1",
                     "accuracyLevel":"STREET","accuracyMeters":15.0,
                     "accuracyMethod":"CADASTRAL_COMPARISON"}
                    """))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.verificationStatus").value("VERIFIED"))
            .andExpect(jsonPath("$.parcelAnalysisEligible").value(false));
    }

    @Test
    void streetWithNullMetersIsAcceptedOverHttpButCannotEnableDistanceAnalysis() throws Exception {
        String id = createProperty(16.0430, 108.1840, "Đường Tôn Đản, Hòa An", "Cẩm Lệ", "Hòa An");

        mvc.perform(post("/api/v1/properties/" + id + "/coordinate/verify").with(asAdmin(adminId))
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {"expectedRevision":1,"verificationStatus":"VERIFIED",
                     "verificationMethod":"CADASTRAL_RECORD","evidenceReference":"STREET-NULL-EVIDENCE",
                     "accuracyLevel":"STREET","accuracyMeters":null}
                    """))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.accuracyLevel").value("STREET"))
            .andExpect(jsonPath("$.accuracyMeters").value(nullValue()))
            .andExpect(jsonPath("$.referenceMapEligible").value(true))
            .andExpect(jsonPath("$.distanceAnalysisEligible").value(false))
            .andExpect(jsonPath("$.parcelAnalysisEligible").value(false));
    }

    @Test
    void httpAccuracyPolicyRejectsUnknownMetersInvalidStreetAndInvalidParcel() throws Exception {
        String id = createProperty(16.0430, 108.1840, "Đường Tôn Đản, Hòa An", "Cẩm Lệ", "Hòa An");
        for (String accuracy : List.of(
                "\"accuracyLevel\":\"UNKNOWN\",\"accuracyMeters\":1.0",
                "\"accuracyLevel\":\"STREET\",\"accuracyMeters\":0",
                "\"accuracyLevel\":\"STREET\",\"accuracyMeters\":-1",
                "\"accuracyLevel\":\"STREET\",\"accuracyMeters\":1e309",
                "\"accuracyLevel\":\"PARCEL\",\"accuracyMeters\":null",
                "\"accuracyLevel\":\"PARCEL\",\"accuracyMeters\":0",
                "\"accuracyLevel\":\"PARCEL\",\"accuracyMeters\":-1")) {
            mvc.perform(post("/api/v1/properties/" + id + "/coordinate/verify").with(asAdmin(adminId))
                    .contentType(MediaType.APPLICATION_JSON)
                    .content("""
                        {"expectedRevision":1,"verificationStatus":"VERIFIED",
                         "verificationMethod":"FIELD_SURVEY","evidenceReference":"HTTP-EVIDENCE",
                         %s}
                        """.formatted(accuracy)))
                .andExpect(status().isBadRequest());
        }
    }

    @Test
    void parcelWithPositiveMetersAndEvidenceIsAcceptedOverHttp() throws Exception {
        String id = createProperty(16.0430, 108.1840, "Đường Tôn Đản, Hòa An", "Cẩm Lệ", "Hòa An");
        // Test-only provenance evidence: this fixture models an actual user pin.
        assertThat(jdbc.update("""
            UPDATE property_coordinate_audit
            SET coordinate_source='USER_PINNED', source_reference='IT_USER_PINNED_FIXTURE'
            WHERE property_id=? AND superseded_at IS NULL AND coordinate_source='UNKNOWN'
            """, id)).isEqualTo(1);

        mvc.perform(post("/api/v1/properties/" + id + "/coordinate/verify").with(asAdmin(adminId))
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {"expectedRevision":1,"verificationStatus":"VERIFIED",
                     "verificationMethod":"FIELD_SURVEY","evidenceReference":"PARCEL-EVIDENCE",
                     "accuracyLevel":"PARCEL","accuracyMeters":1.0}
                    """))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.parcelAnalysisEligible").value(true));
    }

    @Test
    void nonAdminCannotVerify() throws Exception {
        String id = createProperty(16.0430, 108.1840, "Đường Tôn Đản, Hòa An", "Cẩm Lệ", "Hòa An");

        mvc.perform(post("/api/v1/properties/" + id + "/coordinate/verify").with(as(brokerId))
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {"expectedRevision":1,"verificationStatus":"VERIFIED",
                     "verificationMethod":"CADASTRAL_RECORD","evidenceReference":"X",
                     "accuracyLevel":"STREET"}
                    """))
            .andExpect(status().isForbidden());
    }

    @Test
    void staleExpectedRevisionReturns409() throws Exception {
        String id = createProperty(16.0430, 108.1840, "Đường Tôn Đản, Hòa An", "Cẩm Lệ", "Hòa An");

        // Người đăng sửa tọa độ → revision 2.
        mvc.perform(patch("/api/v1/properties/" + id).param("expectedVersion", "1").with(as(brokerId))
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {"title":"Coordinate IT fixture","propertyType":"HOUSE",
                     "transactionType":"SALE","price":1000000000,"priceUnit":"TOTAL","areaSqm":50.0,
                     "address":"Đường Tôn Đản, Hòa An","city":"Da Nang","district":"Cẩm Lệ",
                     "ward":"Hòa An","latitude":16.0600,"longitude":108.2000}
                    """))
            .andExpect(status().isOk());

        // Admin vẫn gửi revision 1 → 409, không xác minh nhầm revision 2.
        mvc.perform(post("/api/v1/properties/" + id + "/coordinate/verify").with(asAdmin(adminId))
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {"expectedRevision":1,"verificationStatus":"VERIFIED",
                     "verificationMethod":"CADASTRAL_RECORD","evidenceReference":"IT-EVIDENCE-1",
                     "accuracyLevel":"STREET"}
                    """))
            .andExpect(status().isConflict());

        String status = jdbc.queryForObject("""
            SELECT verification_status FROM property_coordinate_audit
            WHERE property_id = ? AND superseded_at IS NULL
            """, String.class, id);
        assertThat(status).as("revision mới không bị xác minh nhầm").isEqualTo("UNVERIFIED");
    }

    @Test
    void verifyWithoutEvidenceIsRejected() throws Exception {
        String id = createProperty(16.0430, 108.1840, "Đường Tôn Đản, Hòa An", "Cẩm Lệ", "Hòa An");

        mvc.perform(post("/api/v1/properties/" + id + "/coordinate/verify").with(asAdmin(adminId))
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {"expectedRevision":1,"verificationStatus":"VERIFIED",
                     "accuracyLevel":"STREET"}
                    """))
            .andExpect(status().isBadRequest());
    }

    @Test
    void parcelAccuracyWithoutVerificationIsRejected() throws Exception {
        String id = createProperty(16.0430, 108.1840, "Đường Tôn Đản, Hòa An", "Cẩm Lệ", "Hòa An");

        mvc.perform(post("/api/v1/properties/" + id + "/coordinate/verify").with(asAdmin(adminId))
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {"expectedRevision":1,"verificationStatus":"UNVERIFIED",
                     "accuracyLevel":"PARCEL","accuracyMeters":3.0}
                    """))
            .andExpect(status().isBadRequest());
    }

    // ---------- D. Public detail ----------

    @Test
    void publicDetailReturnsRealAuditNotAbsent() throws Exception {
        String id = createProperty(16.0430, 108.1840, "Đường Tôn Đản, Hòa An", "Cẩm Lệ", "Hòa An");

        // Publish để public detail trả được.
        jdbc.update("UPDATE properties SET status='PUBLISHED', published_at=UTC_TIMESTAMP(6) WHERE id=?", id);

        mvc.perform(get("/api/v1/properties/" + id))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.coordinate.coordinateSource").value("UNKNOWN"))
            .andExpect(jsonPath("$.coordinate.revision").value(1))
            .andExpect(jsonPath("$.coordinate.parcelAnalysisEligible").value(false));
    }

    @Test
    void v26RuntimeReadinessIsUpAfterHibernateAndFlywayValidation() throws Exception {
        mvc.perform(get("/actuator/health/readiness"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.status").value("UP"));
    }

    @Test
    void publicDetailDoesNotLeakVerifierIdentity() throws Exception {
        String id = createProperty(16.0430, 108.1840, "Đường Tôn Đản, Hòa An", "Cẩm Lệ", "Hòa An");
        jdbc.update("UPDATE properties SET status='PUBLISHED', published_at=UTC_TIMESTAMP(6) WHERE id=?", id);

        String body = mvc.perform(get("/api/v1/properties/" + id))
            .andExpect(status().isOk())
            .andReturn().getResponse().getContentAsString();

        assertThat(body).as("không lộ verified_by").doesNotContain("verifiedBy");
        assertThat(body).as("không lộ evidence").doesNotContain("evidenceReference");
    }

    @Test
    void draftPropertyIsNotPubliclyReadable() throws Exception {
        String id = createProperty(16.0430, 108.1840, "Đường Tôn Đản, Hòa An", "Cẩm Lệ", "Hòa An");

        mvc.perform(get("/api/v1/properties/" + id))
            .andExpect(status().isNotFound());
    }

    // ---------- E. Eligibility ----------

    @Test
    void parcelEligibilityRequiresAllConditions() throws Exception {
        String id = createProperty(16.0430, 108.1840, "Đường Tôn Đản, Hòa An", "Cẩm Lệ", "Hòa An");

        // PARCEL + VERIFIED nhưng provenance UNKNOWN → không đủ điều kiện cấp thửa.
        mvc.perform(post("/api/v1/properties/" + id + "/coordinate/verify").with(asAdmin(adminId))
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {"expectedRevision":1,"verificationStatus":"VERIFIED",
                     "verificationMethod":"CADASTRAL_RECORD","evidenceReference":"IT-EVIDENCE-2",
                     "accuracyLevel":"PARCEL","accuracyMeters":3.0,
                     "accuracyMethod":"CADASTRAL_COMPARISON"}
                    """))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.parcelAnalysisEligible").value(false));
    }

    @Test
    void adminReviewDetailReturnsSharedParcelEligibilityPolicy() throws Exception {
        String id = createProperty(16.0430, 108.1840, "Đường Tôn Đản, Hòa An", "Cẩm Lệ", "Hòa An");
        jdbc.update("""
            UPDATE property_coordinate_audit
            SET coordinate_source='USER_PINNED', accuracy_level='PARCEL', accuracy_meters=3.0,
                accuracy_method='CADASTRAL_COMPARISON', verification_status='VERIFIED',
                verification_method='CADASTRAL_RECORD', verified_at=UTC_TIMESTAMP(6),
                verified_by=?, evidence_reference='IT-SYNTHETIC-EVIDENCE',
                geographic_validation_status='VERIFIED_EXACT'
            WHERE property_id=? AND superseded_at IS NULL
            """, adminId, id);

        mvc.perform(get("/api/v1/admin/coordinates/" + id).with(asAdmin(adminId)))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.parcelAnalysisEligible").value(true));

        // Keep one policy source: provenance, accuracy, geographic validity and a
        // completed verification are all required for the detail headline.
        jdbc.update("UPDATE property_coordinate_audit SET coordinate_source='UNKNOWN' WHERE property_id=?", id);
        assertReviewEligibility(id, false);
        jdbc.update("UPDATE property_coordinate_audit SET coordinate_source='USER_PINNED', accuracy_level='STREET' WHERE property_id=?", id);
        assertReviewEligibility(id, false);
        jdbc.update("UPDATE property_coordinate_audit SET accuracy_level='DISTRICT' WHERE property_id=?", id);
        assertReviewEligibility(id, false);
        jdbc.update("UPDATE property_coordinate_audit SET accuracy_level='WARD' WHERE property_id=?", id);
        assertReviewEligibility(id, false);
        jdbc.update("UPDATE property_coordinate_audit SET accuracy_level='UNKNOWN', accuracy_meters=NULL WHERE property_id=?", id);
        assertReviewEligibility(id, false);
        jdbc.update("UPDATE property_coordinate_audit SET accuracy_level='PARCEL', accuracy_meters=3.0, geographic_validation_status='INVALID_DISTRICT_MISMATCH' WHERE property_id=?", id);
        assertReviewEligibility(id, false);
        jdbc.update("UPDATE property_coordinate_audit SET geographic_validation_status='VERIFIED_EXACT' WHERE property_id=?", id);
        jdbc.update("""
            UPDATE property_coordinate_audit
            SET accuracy_level='STREET', accuracy_meters=3.0, verification_status='UNVERIFIED',
                verification_method=NULL, verified_at=NULL, verified_by=NULL
            WHERE property_id=?
            """, id);
        assertReviewEligibility(id, false);
        jdbc.update("""
            UPDATE property_coordinate_audit
            SET verification_status='STALE', verification_method=NULL, verified_at=NULL, verified_by=NULL
            WHERE property_id=?
            """, id);
        assertReviewEligibility(id, false);
    }

    private void assertReviewEligibility(String propertyId, boolean expected) throws Exception {
        mvc.perform(get("/api/v1/admin/coordinates/" + propertyId).with(asAdmin(adminId)))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.parcelAnalysisEligible").value(expected));
    }

    @Test
    void pendingPaginationIsStableWhenCreatedAtTiesAcrossPages() throws Exception {
        String marker = "Coordinate tie " + UUID.randomUUID();
        List<String> ids = new java.util.ArrayList<>();
        for (int index = 0; index < 4; index++) {
            String id = createProperty(16.0430, 108.1840, "Đường Tôn Đản, Hòa An", "Cẩm Lệ", "Hòa An");
            ids.add(id);
            jdbc.update("UPDATE properties SET title=? WHERE id=?", marker, id);
        }
        jdbc.update("""
            UPDATE property_coordinate_audit
            SET created_at='2026-11-25 12:00:00.000000'
            WHERE property_id IN (?, ?, ?, ?)
            """, ids.toArray());
        List<String> expected = jdbc.queryForList("""
            SELECT a.property_id FROM property_coordinate_audit a
            JOIN properties p ON p.id=a.property_id
            WHERE a.superseded_at IS NULL AND p.deleted_at IS NULL AND p.title=?
            ORDER BY a.created_at DESC, a.id DESC
            """, String.class, marker);

        List<String> first = pendingIds(marker, 2, 0, 4);
        List<String> second = pendingIds(marker, 2, 2, 4);
        List<String> firstAgain = pendingIds(marker, 2, 0, 4);
        List<String> empty = pendingIds(marker, 2, 4, 4);
        assertThat(first).containsExactlyElementsOf(expected.subList(0, 2));
        assertThat(second).containsExactlyElementsOf(expected.subList(2, 4));
        assertThat(firstAgain).isEqualTo(first);
        assertThat(java.util.stream.Stream.concat(first.stream(), second.stream()).distinct().count()).isEqualTo(4);
        assertThat(empty).isEmpty();
    }

    private List<String> pendingIds(String marker, int limit, int offset, int expectedTotal) throws Exception {
        String body = mvc.perform(get("/api/v1/admin/coordinates/pending")
                .param("limit", String.valueOf(limit)).param("offset", String.valueOf(offset))
                .param("q", marker).with(asAdmin(adminId)))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.total").value(expectedTotal))
            .andReturn().getResponse().getContentAsString();
        return com.jayway.jsonpath.JsonPath.read(body, "$.items[*].propertyId");
    }

    // ---------- F. Backfill identity (blocker A) ----------

    @Test
    void backfillFingerprintMatchesRuntimeSoTitleEditKeepsRevision() throws Exception {
        String id = createProperty(16.0430, 108.1840, "Đường Tôn Đản, Hòa An", "Cẩm Lệ", "Hòa An");

        // Mô phỏng bản ghi backfill: fingerprint tính bằng công thức SQL (không có scope).
        jdbc.update("DELETE FROM property_coordinate_audit WHERE property_id = ?", id);
        jdbc.update("""
            INSERT INTO property_coordinate_audit (
              id, property_id, revision, audited_latitude, audited_longitude, srid,
              coordinate_fingerprint, fingerprint_version,
              address_snapshot, district_snapshot, ward_snapshot,
              coordinate_source, accuracy_level, verification_status,
              validator_scope_version, validated_at)
            SELECT UUID(), p.id, 1,
              CAST(ROUND(ST_Latitude(p.location), 7) AS DECIMAL(10,7)),
              CAST(ROUND(ST_Longitude(p.location), 7) AS DECIMAL(10,7)),
              4326,
              SHA2(CONCAT(
                CAST(CAST(ROUND(ST_Latitude(p.location), 7) AS DECIMAL(10,7)) AS CHAR), '|',
                CAST(CAST(ROUND(ST_Longitude(p.location), 7) AS DECIMAL(10,7)) AS CHAR), '|',
                COALESCE(TRIM(p.address), ''), '|',
                COALESCE(TRIM(p.district), ''), '|',
                COALESCE(TRIM(p.ward), '')), 256),
              1, p.address, p.district, p.ward,
              'UNKNOWN', 'UNKNOWN', 'UNVERIFIED', 'BACKFILL_V1', UTC_TIMESTAMP(6)
            FROM properties p WHERE p.id = ?
            """, id);

        // Sửa tiêu đề, không đổi vị trí → fingerprint backfill phải khớp runtime,
        // nên KHÔNG tạo revision mới.
        mvc.perform(patch("/api/v1/properties/" + id).param("expectedVersion", "1").with(as(brokerId))
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {"title":"Coordinate IT fixture renamed","propertyType":"HOUSE",
                     "transactionType":"SALE","price":1000000000,"priceUnit":"TOTAL","areaSqm":50.0,
                     "address":"Đường Tôn Đản, Hòa An","city":"Da Nang","district":"Cẩm Lệ",
                     "ward":"Hòa An","latitude":16.0430,"longitude":108.1840}
                    """))
            .andExpect(status().isOk());

        Integer revisions = jdbc.queryForObject(
            "SELECT COUNT(*) FROM property_coordinate_audit WHERE property_id = ?",
            Integer.class, id);
        assertThat(revisions)
            .as("fingerprint backfill phải khớp runtime — sửa tiêu đề không tạo revision")
            .isEqualTo(1);
    }

    @Test
    void backfillVerificationSurvivesTitleEdit() throws Exception {
        String id = createProperty(16.0430, 108.1840, "Đường Tôn Đản, Hòa An", "Cẩm Lệ", "Hòa An");

        // Admin xác minh revision 1.
        mvc.perform(post("/api/v1/properties/" + id + "/coordinate/verify").with(asAdmin(adminId))
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {"expectedRevision":1,"verificationStatus":"VERIFIED",
                     "verificationMethod":"CADASTRAL_RECORD","evidenceReference":"IT-EVIDENCE-3",
                     "accuracyLevel":"STREET","accuracyMeters":15.0}
                    """))
            .andExpect(status().isOk());

        // Sửa tiêu đề, không đổi vị trí → xác minh vẫn còn hiệu lực.
        mvc.perform(patch("/api/v1/properties/" + id).param("expectedVersion", "1").with(as(brokerId))
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {"title":"Coordinate IT fixture renamed","propertyType":"HOUSE",
                     "transactionType":"SALE","price":1000000000,"priceUnit":"TOTAL","areaSqm":50.0,
                     "address":"Đường Tôn Đản, Hòa An","city":"Da Nang","district":"Cẩm Lệ",
                     "ward":"Hòa An","latitude":16.0430,"longitude":108.1840}
                    """))
            .andExpect(status().isOk());

        String status = jdbc.queryForObject("""
            SELECT verification_status FROM property_coordinate_audit
            WHERE property_id = ? AND superseded_at IS NULL
            """, String.class, id);
        assertThat(status)
            .as("sửa tiêu đề không được làm mất xác minh")
            .isEqualTo("VERIFIED");
    }

    @Test
    void coordinateChangeResetsVerificationToUnverified() throws Exception {
        String id = createProperty(16.0430, 108.1840, "Đường Tôn Đản, Hòa An", "Cẩm Lệ", "Hòa An");

        mvc.perform(post("/api/v1/properties/" + id + "/coordinate/verify").with(asAdmin(adminId))
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {"expectedRevision":1,"verificationStatus":"VERIFIED",
                     "verificationMethod":"CADASTRAL_RECORD","evidenceReference":"IT-EVIDENCE-4",
                     "accuracyLevel":"STREET","accuracyMeters":15.0}
                    """))
            .andExpect(status().isOk());

        // Đổi tọa độ → revision mới, verification về UNVERIFIED.
        mvc.perform(patch("/api/v1/properties/" + id).param("expectedVersion", "1").with(as(brokerId))
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {"title":"Coordinate IT fixture","propertyType":"HOUSE",
                     "transactionType":"SALE","price":1000000000,"priceUnit":"TOTAL","areaSqm":50.0,
                     "address":"Đường Tôn Đản, Hòa An","city":"Da Nang","district":"Cẩm Lệ",
                     "ward":"Hòa An","latitude":16.0700,"longitude":108.2100}
                    """))
            .andExpect(status().isOk());

        String status = jdbc.queryForObject("""
            SELECT verification_status FROM property_coordinate_audit
            WHERE property_id = ? AND superseded_at IS NULL
            """, String.class, id);
        assertThat(status)
            .as("đổi tọa độ phải reset verification — không kế thừa xác minh vị trí cũ")
            .isEqualTo("UNVERIFIED");
    }

    // ---------- G. History endpoint security (blocker B) ----------

    @Test
    void anonymousCannotReadCoordinateHistory() throws Exception {
        String id = createProperty(16.0430, 108.1840, "Đường Tôn Đản, Hòa An", "Cẩm Lệ", "Hòa An");

        mvc.perform(get("/api/v1/properties/" + id + "/coordinate/history"))
            .andExpect(status().isUnauthorized());
    }

    @Test
    void ownerCanReadCoordinateHistory() throws Exception {
        String id = createProperty(16.0430, 108.1840, "Đường Tôn Đản, Hòa An", "Cẩm Lệ", "Hòa An");

        mvc.perform(get("/api/v1/properties/" + id + "/coordinate/history").with(as(brokerId)))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$[0].revision").value(1));
    }

    @Test
    void nonOwnerBrokerCannotReadCoordinateHistory() throws Exception {
        String id = createProperty(16.0430, 108.1840, "Đường Tôn Đản, Hòa An", "Cẩm Lệ", "Hòa An");

        // JWT principal có ROLE_BROKER và active subject khác chủ tin.
        mvc.perform(get("/api/v1/properties/" + id + "/coordinate/history").with(as(activeNonOwnerId)))
            .andExpect(status().isForbidden());
    }

    @Test
    void adminCanReadCoordinateHistory() throws Exception {
        String id = createProperty(16.0430, 108.1840, "Đường Tôn Đản, Hòa An", "Cẩm Lệ", "Hòa An");

        mvc.perform(get("/api/v1/properties/" + id + "/coordinate/history").with(asAdmin(adminId)))
            .andExpect(status().isOk());
    }

    @Test
    void anonymousCanReadPublishedCoordinateButNotDraft() throws Exception {
        String published = createProperty(16.0430, 108.1840, "Đường Tôn Đản, Hòa An", "Cẩm Lệ", "Hòa An");
        jdbc.update("UPDATE properties SET status='PUBLISHED', published_at=UTC_TIMESTAMP(6) WHERE id=?",
            published);
        mvc.perform(get("/api/v1/properties/" + published + "/coordinate"))
            .andExpect(status().isOk());

        String draft = createProperty(16.0430, 108.1840, "Đường Tôn Đản, Hòa An", "Cẩm Lệ", "Hòa An");
        mvc.perform(get("/api/v1/properties/" + draft + "/coordinate"))
            .andExpect(status().isNotFound());
    }

    // ---------- H. Concurrent verification (blocker C) ----------

    @Test
    void secondVerificationOnSameRevisionIsRejected() throws Exception {
        String id = createProperty(16.0430, 108.1840, "Đường Tôn Đản, Hòa An", "Cẩm Lệ", "Hòa An");

        // Admin A xác minh VERIFIED.
        mvc.perform(post("/api/v1/properties/" + id + "/coordinate/verify").with(asAdmin(adminId))
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {"expectedRevision":1,"verificationStatus":"VERIFIED",
                     "verificationMethod":"CADASTRAL_RECORD","evidenceReference":"IT-EVIDENCE-A",
                     "accuracyLevel":"STREET","accuracyMeters":15.0}
                    """))
            .andExpect(status().isOk());

        // Admin B gửi REJECTED trên cùng revision → 409, không ghi đè quyết định của A.
        mvc.perform(post("/api/v1/properties/" + id + "/coordinate/verify").with(asAdmin(adminId))
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {"expectedRevision":1,"verificationStatus":"REJECTED",
                     "verificationMethod":"ADMIN_REVIEW","evidenceReference":"IT-EVIDENCE-B",
                     "accuracyLevel":"UNKNOWN"}
                    """))
            .andExpect(status().isConflict());

        String status = jdbc.queryForObject("""
            SELECT verification_status FROM property_coordinate_audit
            WHERE property_id = ? AND superseded_at IS NULL
            """, String.class, id);
        assertThat(status)
            .as("quyết định của admin A không bị ghi đè âm thầm")
            .isEqualTo("VERIFIED");
    }

    @Test
    void concurrentVerificationAllowsExactlyOneWinner() throws Exception {
        String id = createProperty(16.0430, 108.1840, "Đường Tôn Đản, Hòa An", "Cẩm Lệ", "Hòa An");

        int threads = 4;
        java.util.concurrent.CyclicBarrier barrier = new java.util.concurrent.CyclicBarrier(threads);
        java.util.concurrent.ExecutorService pool =
            java.util.concurrent.Executors.newFixedThreadPool(threads);
        java.util.List<java.util.concurrent.Future<Integer>> futures = new java.util.ArrayList<>();
        java.util.concurrent.atomic.AtomicInteger ok =
            new java.util.concurrent.atomic.AtomicInteger();

        for (int i = 0; i < threads; i++) {
            final int index = i;
            futures.add(pool.submit(() -> {
                barrier.await();
                var result = mvc.perform(
                        post("/api/v1/properties/" + id + "/coordinate/verify")
                            .with(asAdmin(adminId))
                            .contentType(MediaType.APPLICATION_JSON)
                            .content("""
                                {"expectedRevision":1,"verificationStatus":"VERIFIED",
                                 "verificationMethod":"CADASTRAL_RECORD",
                                 "evidenceReference":"IT-CONCURRENT-%d",
                                 "accuracyLevel":"STREET","accuracyMeters":15.0}
                                """.formatted(index)))
                    .andReturn();
                int code = result.getResponse().getStatus();
                if (code == 200) ok.incrementAndGet();
                return code;
            }));
        }

        java.util.List<Integer> codes = new java.util.ArrayList<>();
        for (var future : futures) codes.add(future.get());
        pool.shutdown();

        assertThat(ok.get())
            .as("chỉ một quyết định xác minh được ghi: %s", codes)
            .isEqualTo(1);
        assertThat(codes).as("các request còn lại phải nhận 409").containsOnly(200, 409);

        Integer currentCount = jdbc.queryForObject("""
            SELECT COUNT(*) FROM property_coordinate_audit
            WHERE property_id = ? AND superseded_at IS NULL
            """, Integer.class, id);
        assertThat(currentCount).as("không có partial update").isEqualTo(1);
    }

    // ---------- I. Admin review endpoints ----------

    @Test
    void adminStatsCountsWholeTableNotOnePage() throws Exception {
        String id = createProperty(16.0430, 108.1840, "Đường Tôn Đản, Hòa An", "Cẩm Lệ", "Hòa An");

        mvc.perform(get("/api/v1/admin/coordinates/stats").with(asAdmin(adminId)))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.total").isNumber())
            .andExpect(jsonPath("$.unverified").isNumber())
            .andExpect(jsonPath("$.verified").isNumber())
            .andExpect(jsonPath("$.districtMismatch").isNumber());

        // Tin vừa tạo phải nằm trong tổng, không phụ thuộc phân trang.
        Long total = jdbc.queryForObject("""
            SELECT COUNT(*) FROM property_coordinate_audit a
            JOIN properties p ON p.id = a.property_id
            WHERE a.superseded_at IS NULL AND p.deleted_at IS NULL
            """, Long.class);
        String body = mvc.perform(get("/api/v1/admin/coordinates/stats").with(asAdmin(adminId)))
            .andReturn().getResponse().getContentAsString();
        Number reported = com.jayway.jsonpath.JsonPath.read(body, "$.total");
        assertThat(reported.longValue()).as("stats phải đếm toàn bộ bảng").isEqualTo(total);
    }

    @Test
    void nonAdminCannotReadStats() throws Exception {
        mvc.perform(get("/api/v1/admin/coordinates/stats").with(as(brokerId)))
            .andExpect(status().isForbidden());
    }

    @Test
    void anonymousCannotReadStats() throws Exception {
        mvc.perform(get("/api/v1/admin/coordinates/stats"))
            .andExpect(status().isUnauthorized());
    }

    @Test
    void adminReviewDetailReturnsCoordinatesAndEvidence() throws Exception {
        String id = createProperty(16.0430, 108.1840, "Đường Tôn Đản, Hòa An", "Cẩm Lệ", "Hòa An");

        mvc.perform(get("/api/v1/admin/coordinates/" + id).with(asAdmin(adminId)))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.propertyId").value(id))
            .andExpect(jsonPath("$.latitude").isNumber())
            .andExpect(jsonPath("$.longitude").isNumber())
            .andExpect(jsonPath("$.revision").value(1))
            .andExpect(jsonPath("$.coordinateSource").value("UNKNOWN"))
            .andExpect(jsonPath("$.verificationStatus").value("UNVERIFIED"))
            .andExpect(jsonPath("$.geographicValidationStatus").isNotEmpty());
    }

    @Test
    void adminDetailFailsClosedForLegacyParcelAuditsWithoutEvidence() throws Exception {
        String id = createProperty(16.0430, 108.1840, "Legacy parcel fixture", "Cẩm Lệ", "Hòa An");
        record LegacyCase(String name, String accuracy, String verification, String method,
                          boolean verifiedAt, String evidence, Double meters, boolean expected) {}
        List<LegacyCase> cases = List.of(
            new LegacyCase("complete legacy record", "PARCEL", "VERIFIED", "FIELD_SURVEY", true, "legacy-evidence", 1.0, true),
            new LegacyCase("null evidence", "PARCEL", "VERIFIED", "FIELD_SURVEY", true, null, 1.0, false),
            new LegacyCase("empty evidence", "PARCEL", "VERIFIED", "FIELD_SURVEY", true, "", 1.0, false),
            new LegacyCase("blank evidence", "PARCEL", "VERIFIED", "FIELD_SURVEY", true, "   ", 1.0, false),
            new LegacyCase("invalid accuracy", "PARCEL", "VERIFIED", "FIELD_SURVEY", true, "legacy-evidence", null, false),
            new LegacyCase("street accuracy", "STREET", "VERIFIED", "FIELD_SURVEY", true, "legacy-evidence", 1.0, false),
            new LegacyCase("unknown accuracy", "UNKNOWN", "VERIFIED", "FIELD_SURVEY", true, "legacy-evidence", null, false),
            new LegacyCase("unverified status", "STREET", "UNVERIFIED", null, false, null, 1.0, false),
            new LegacyCase("stale status", "STREET", "STALE", "FIELD_SURVEY", true, "legacy-evidence", 1.0, false)
        );

        // V26 CHECK ck_coord_audit_verified_fields disallows persisted VERIFIED rows
        // without method/time. Those legacy metadata combinations are covered by the
        // centralized policy unit tests; this endpoint test uses only schema-permitted rows.
        for (LegacyCase item : cases) {
            jdbc.update("""
                UPDATE property_coordinate_audit
                SET coordinate_source='USER_PINNED', accuracy_level=?, accuracy_meters=?,
                    verification_status=?, verification_method=?,
                    verified_at=CASE WHEN ? THEN UTC_TIMESTAMP(6) ELSE NULL END,
                    evidence_reference=?, geographic_validation_status='VERIFIED_EXACT'
                WHERE property_id=? AND superseded_at IS NULL
                """, item.accuracy(), item.meters(), item.verification(), item.method(),
                item.verifiedAt(), item.evidence(), id);

            mvc.perform(get("/api/v1/admin/coordinates/" + id).with(asAdmin(adminId)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.parcelAnalysisEligible").value(item.expected()))
                .andDo(result -> assertThat(result.getResponse().getContentAsString())
                    .as("legacy fixture case %s", item.name()).isNotBlank());
        }
    }

    @Test
    void nonAdminCannotReadReviewDetail() throws Exception {
        String id = createProperty(16.0430, 108.1840, "Đường Tôn Đản, Hòa An", "Cẩm Lệ", "Hòa An");

        mvc.perform(get("/api/v1/admin/coordinates/" + id).with(as(brokerId)))
            .andExpect(status().isForbidden());
    }

    @Test
    void reviewDetailForPropertyWithoutAuditIs404() throws Exception {
        mvc.perform(get("/api/v1/admin/coordinates/" + java.util.UUID.randomUUID())
                .with(asAdmin(adminId)))
            .andExpect(status().isNotFound());
    }

    @Test
    void pendingQueueFiltersByStatusAndQuery() throws Exception {
        String id = createProperty(16.0430, 108.1840, "Đường Tôn Đản, Hòa An", "Cẩm Lệ", "Hòa An");

        // Lọc theo trạng thái: tin mới tạo là UNVERIFIED nên phải xuất hiện.
        String unverified = mvc.perform(get("/api/v1/admin/coordinates/pending")
                .param("verificationStatus", "UNVERIFIED")
                .with(asAdmin(adminId)))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.items[0].propertyId").value(id))
            .andExpect(jsonPath("$.total").isNumber())
            .andExpect(jsonPath("$.offset").value(0))
            .andReturn().getResponse().getContentAsString();
        assertThat(unverified).contains(id);

        // Lọc theo trạng thái khác: không được chứa tin này.
        String verified = mvc.perform(get("/api/v1/admin/coordinates/pending")
                .param("verificationStatus", "VERIFIED")
                .with(asAdmin(adminId)))
            .andExpect(status().isOk())
            .andReturn().getResponse().getContentAsString();
        assertThat(verified).doesNotContain(id);

        // Tìm theo mã tin.
        String code = jdbc.queryForObject(
            "SELECT listing_code FROM properties WHERE id = ?", String.class, id);
        String searched = mvc.perform(get("/api/v1/admin/coordinates/pending")
                .param("q", code)
                .with(asAdmin(adminId)))
            .andExpect(status().isOk())
            .andReturn().getResponse().getContentAsString();
        assertThat(searched).contains(id);

        mvc.perform(get("/api/v1/admin/coordinates/pending")
                .param("q", code).param("offset", "1").with(asAdmin(adminId)))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.total").value(1))
            .andExpect(jsonPath("$.items").isEmpty());
    }

    @Test
    void pendingQueueDoesNotLeakToNonAdmin() throws Exception {
        mvc.perform(get("/api/v1/admin/coordinates/pending").with(as(brokerId)))
            .andExpect(status().isForbidden());
    }
}
