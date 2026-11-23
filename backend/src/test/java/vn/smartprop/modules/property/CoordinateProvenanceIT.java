package vn.smartprop.modules.property;

import static org.assertj.core.api.Assertions.assertThat;
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
}
