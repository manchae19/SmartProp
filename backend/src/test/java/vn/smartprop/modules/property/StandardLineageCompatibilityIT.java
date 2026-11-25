package vn.smartprop.modules.property;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.util.UUID;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;
import vn.smartprop.database.MigrationProfileEnvironmentGuard;
import vn.smartprop.modules.user.User;
import vn.smartprop.modules.user.UserRepository;

/** Runtime compatibility test for standard V1..V23, which intentionally has no V26 audit table. */
@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles(MigrationProfileEnvironmentGuard.STANDARD)
@EnabledIfEnvironmentVariable(named = "PR38_STANDARD_V23_TEST", matches = "true")
class StandardLineageCompatibilityIT {
    @Autowired MockMvc mvc;
    @Autowired UserRepository users;
    @Autowired JdbcTemplate jdbc;
    @Autowired PropertyCoordinateAuditService coordinateAudit;

    private Long ownerId;
    private String propertyId;

    @AfterEach
    void cleanup() {
        if (propertyId != null) {
            jdbc.update("DELETE FROM property_listing_code_allocations WHERE property_id=?", propertyId);
            jdbc.update("DELETE FROM properties WHERE id=?", propertyId);
        }
        if (ownerId != null) {
            jdbc.update("DELETE FROM user_roles WHERE user_id=?", ownerId);
            users.deleteById(ownerId);
        }
    }

    @Test
    void v23StartsAndKeepsPropertyCreateDetailSearchAvailableWhileCoordinateFeaturesFailClosed() throws Exception {
        assertThat(coordinateAudit.available()).isFalse();

        User owner = new User();
        owner.email = "pr38-v23-" + UUID.randomUUID() + "@example.invalid";
        owner.passwordHash = "test-only-hash-not-used-for-mock-jwt";
        owner.fullName = "PR38 standard lineage fixture";
        owner.role = User.Role.BROKER;
        owner.status = User.Status.ACTIVE;
        owner.tokenVersion = 0;
        owner.notificationPreferences = com.fasterxml.jackson.databind.node.JsonNodeFactory.instance.objectNode();
        owner = users.saveAndFlush(owner);
        ownerId = owner.id;

        String title = "PR38 standard v23 " + UUID.randomUUID();
        String response = mvc.perform(post("/api/v1/properties").with(broker(ownerId))
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {"title":"%s","propertyType":"HOUSE","transactionType":"SALE",
                     "price":1000000000,"priceUnit":"TOTAL","areaSqm":50.0,
                     "address":"Test street","city":"Da Nang","district":"Cẩm Lệ",
                     "ward":"Hòa An","latitude":16.0430,"longitude":108.1840}
                    """.formatted(title)))
            .andExpect(status().isCreated())
            .andExpect(jsonPath("$.property.coordinate.coordinateSource").value("UNKNOWN"))
            .andExpect(jsonPath("$.property.coordinate.distanceAnalysisEligible").value(false))
            .andReturn().getResponse().getContentAsString();
        propertyId = com.jayway.jsonpath.JsonPath.read(response, "$.property.id");

        mvc.perform(get("/api/v1/users/me/properties/" + propertyId).with(broker(ownerId)))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.property.coordinate.parcelAnalysisEligible").value(false));

        jdbc.update("UPDATE properties SET status='PUBLISHED',published_at=UTC_TIMESTAMP(6) WHERE id=?", propertyId);
        mvc.perform(get("/api/v1/properties/" + propertyId))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.coordinate.distanceAnalysisEligible").value(false));
        mvc.perform(get("/api/v1/properties").param("keyword", title))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.items[0].coordinate.distanceAnalysisEligible").value(false));

        mvc.perform(get("/api/v1/properties/" + propertyId + "/coordinate"))
            .andExpect(status().isServiceUnavailable());
        mvc.perform(get("/actuator/health/readiness"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.status").value("UP"));
    }

    private static org.springframework.test.web.servlet.request.RequestPostProcessor broker(Long id) {
        return jwt().jwt(token -> token.subject(String.valueOf(id)))
            .authorities(new SimpleGrantedAuthority("ROLE_BROKER"));
    }
}
