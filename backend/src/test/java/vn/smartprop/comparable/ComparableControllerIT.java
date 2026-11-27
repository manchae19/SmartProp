package vn.smartprop.comparable;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.math.BigDecimal;
import java.util.List;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.request.RequestPostProcessor;

import vn.smartprop.modules.user.User;
import vn.smartprop.modules.user.UserRepository;

/**
 * HTTP-layer contract test: real Spring Security chain, real controller, real
 * MySQL. The JWT is supplied by Spring Security Test rather than minted from a
 * live session, so no real account's session is touched and nothing is written
 * to the database.
 *
 * Skipped when the DB credentials are absent, so a plain clone still builds.
 */
@SpringBootTest
@AutoConfigureMockMvc
@EnabledIfEnvironmentVariable(named = "DB_URL", matches = ".+")
class ComparableControllerIT {

    @Autowired MockMvc mvc;
    @Autowired UserRepository users;
    @Autowired JdbcTemplate jdbc;

    /** An existing broker/admin row, read-only: the controller re-checks the role in the DB. */
    private RequestPostProcessor broker() {
        List<User> staff = users.findAll().stream()
            .filter(u -> u.deletedAt == null && u.status == User.Status.ACTIVE
                      && (u.role == User.Role.BROKER || u.role == User.Role.ADMIN))
            .toList();
        assertThat(staff).as("an active broker/admin must exist to authorise the call").isNotEmpty();
        User actor = staff.get(0);
        return jwt().jwt(j -> j.subject(String.valueOf(actor.id)).claim("ver", actor.tokenVersion))
            .authorities(new SimpleGrantedAuthority("ROLE_" + actor.role.name()));
    }

    private static final String VALID = """
        {"propertyType":"HOUSE","district":"Hải Châu","areaSqm":80,"priceVnd":6000000000}
        """;

    @Test
    void unauthenticatedRequestIsRejected() throws Exception {
        mvc.perform(post("/api/v1/properties/comparables")
                .contentType(MediaType.APPLICATION_JSON).content(VALID))
            .andExpect(status().isUnauthorized());
    }

    @Test
    void buyerRoleIsForbidden() throws Exception {
        mvc.perform(post("/api/v1/properties/comparables")
                .with(jwt().jwt(j -> j.subject("999999")).authorities(new SimpleGrantedAuthority("ROLE_BUYER")))
                .contentType(MediaType.APPLICATION_JSON).content(VALID))
            .andExpect(status().isForbidden());
    }

    @Test
    void validBrokerRequestReturnsPublicComparablesWithoutTinixExposure() throws Exception {
        var body = mvc.perform(post("/api/v1/properties/comparables")
                .with(broker())
                .contentType(MediaType.APPLICATION_JSON).content(VALID))
            .andExpect(status().isOk())
            .andExpect(header().string("Cache-Control", "private, no-store"))
            .andExpect(jsonPath("$.candidateCount").value(org.hamcrest.Matchers.lessThanOrEqualTo(5)))
            .andExpect(jsonPath("$.reference.district").value("Hải Châu"))
            .andExpect(jsonPath("$.eligibleCountsBySource.TINIX_RESEARCH").doesNotExist())
            .andReturn().getResponse().getContentAsString(java.nio.charset.StandardCharsets.UTF_8);

        assertThat(body).contains("\"comparables\"");
        assertThat(body).doesNotContain("\"TINIX_RESEARCH\"", "CC BY-NC 4.0");
    }

    @Test
    void brokerRequestingResearchIsForbidden() throws Exception {
        mvc.perform(post("/api/v1/properties/comparables?includeResearch=true")
                .with(broker())
                .contentType(MediaType.APPLICATION_JSON).content(VALID))
            .andExpect(status().isForbidden());
    }

    @Test
    void invalidInputIsA400NotA500() throws Exception {
        mvc.perform(post("/api/v1/properties/comparables").with(broker())
                .contentType(MediaType.APPLICATION_JSON).content("{\"propertyType\":\"HOUSE\",\"areaSqm\":80}"))
            .andExpect(status().isBadRequest());
        mvc.perform(post("/api/v1/properties/comparables").with(broker())
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"propertyType\":\"ROOM\",\"district\":\"Hải Châu\",\"areaSqm\":80}"))
            .andExpect(status().isBadRequest());
        mvc.perform(post("/api/v1/properties/comparables").with(broker())
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"propertyType\":\"HOUSE\",\"district\":\"Hải Châu\",\"areaSqm\":2}"))
            .andExpect(status().isBadRequest());
        mvc.perform(post("/api/v1/properties/comparables").with(broker())
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"propertyType\":\"HOUSE\",\"district\":\"Hải Châu\",\"areaSqm\":80,\"limit\":9}"))
            .andExpect(status().isBadRequest());
    }

    @Test
    void emptyDistrictReturnsAnExplainedEmptyResult() throws Exception {
        mvc.perform(post("/api/v1/properties/comparables").with(broker())
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"propertyType\":\"HOUSE\",\"district\":\"Quận Không Tồn Tại\",\"areaSqm\":80}"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.candidateCount").value(0))
            .andExpect(jsonPath("$.searchStage").value("NONE"));
    }

    @Test
    void unknownPropertyIdIs404() throws Exception {
        mvc.perform(post("/api/v1/properties/comparables").with(broker())
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"propertyId\":\"00000000-0000-4000-8000-000000000000\"}"))
            .andExpect(status().isNotFound());
    }

    @Test
    void explicitResearchRequestFailsClosedWhenComparableResearchDisabled() throws Exception {
        List<User> admins = users.findAll().stream()
            .filter(u -> u.deletedAt == null && u.status == User.Status.ACTIVE && u.role == User.Role.ADMIN)
            .toList();
        assertThat(admins).isNotEmpty();
        User admin = admins.get(0);
        RequestPostProcessor adminJwt = jwt().jwt(j -> j.subject(String.valueOf(admin.id)).claim("ver", admin.tokenVersion))
            .authorities(new SimpleGrantedAuthority("ROLE_ADMIN"));

        mvc.perform(post("/api/v1/properties/comparables?includeResearch=true")
                .with(adminJwt)
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"propertyType\":\"LAND\",\"district\":\"Hòa Vang\",\"areaSqm\":300,\"priceVnd\":2000000000}"))
            .andExpect(status().isForbidden());
    }

    /** Minimal id extraction; the JSON shape is asserted above. */
    private static List<String> idsIn(String json) {
        var out = new java.util.ArrayList<String>();
        var m = java.util.regex.Pattern.compile("\"candidateId\":\"(tnx-[^\"]+)\"").matcher(json);
        while (m.find()) out.add(m.group(1));
        return out;
    }
}
