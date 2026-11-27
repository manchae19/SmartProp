package vn.smartprop.comparable;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import vn.smartprop.common.ApiException;
import vn.smartprop.modules.property.Property;
import vn.smartprop.modules.property.PropertyRepository;

import static org.assertj.core.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;
import static vn.smartprop.comparable.ComparableDtos.*;

class ComparablePhaseBTest {
    private static final String SUBJECT = "10000000-0000-4000-8000-000000000000";
    private static final String DISTRICT = "Hải Châu";
    private final ComparableCandidateRepository repository = mock(ComparableCandidateRepository.class);
    private final PropertyRepository properties = mock(PropertyRepository.class);
    private final ComparableRankingService service = new ComparableRankingService(repository, new ComparableEligibilityService(), properties, true);

    @Test
    void valuationIgnoresFreeFormAndLoadedTargetPriceForPoolOrderScoresAndResponse() {
        when(repository.propertyCandidates(any(), eq(200))).thenReturn(List.of(
            property(SUBJECT, "HOUSE", DISTRICT, null, 80, "1700000000"),
            property("a", "HOUSE", DISTRICT, null, 83, "6500000000"),
            property("b", "HOUSE", DISTRICT, null, 80, "5000000000"),
            property("c", "HOUSE", DISTRICT, null, 98, "1200000000")));
        var captures = ArgumentCaptor.forClass(ComparableCandidateRepository.Search.class);
        var standaloneA = service.rank(request(null, null, "1000000000", Purpose.VALUATION_SUPPORT, null, null));
        var standaloneB = service.rank(request(null, null, "9000000000", Purpose.VALUATION_SUPPORT, null, null));
        assertThat(standaloneA).isEqualTo(standaloneB);
        assertThat(ids(standaloneA)).contains("property:b", "property:c", "property:a");
        assertThat(standaloneA.reference().priceVnd()).isNull();
        assertThat(standaloneA.comparables()).allSatisfy(c -> {
            assertThat(c.scoreBreakdown()).doesNotContainKey("price");
            assertThat(c.priceDifferencePct()).isNull();
        });

        var subject = new Property();
        subject.id = SUBJECT;
        subject.status = Property.Status.PUBLISHED;
        subject.transactionType = Property.Transaction.SALE;
        subject.priceUnit = Property.PriceUnit.TOTAL;
        subject.currency = "VND";
        subject.propertyType = Property.Type.HOUSE;
        subject.district = DISTRICT;
        subject.areaSqm = bd("80");
        when(properties.findByIdAndDeletedAtIsNull(SUBJECT)).thenReturn(Optional.of(subject));
        subject.price = bd("1800000000");
        var storedA = service.rank(request(SUBJECT, null, "1", Purpose.VALUATION_SUPPORT, null, null));
        subject.price = bd("18000000000");
        var storedB = service.rank(request(SUBJECT, null, "9999999999999", Purpose.VALUATION_SUPPORT, null, null));
        assertThat(storedA).isEqualTo(storedB);
        assertThat(ids(storedA)).containsExactly("property:b", "property:a", "property:c");
        verify(repository, times(4)).propertyCandidates(captures.capture(), eq(200));
        assertThat(captures.getAllValues().get(0)).isEqualTo(captures.getAllValues().get(1));
        assertThat(captures.getAllValues().get(2)).isEqualTo(captures.getAllValues().get(3));
        assertThat(captures.getAllValues()).allSatisfy(search -> {
            assertThat(search.minPrice()).isEqualByComparingTo("200000000");
            assertThat(search.maxPrice()).isEqualByComparingTo("1000000000000");
        });

        subject.expiresAt = Instant.now().minusSeconds(1);
        assertThatExceptionOfType(ApiException.class)
            .isThrownBy(() -> service.rank(request(SUBJECT, null, null, Purpose.VALUATION_SUPPORT, null, null)));
    }

    @Test
    void buyerBudgetIsAnAbsoluteCapWhileLegacyAskingPriceIsStillAvailableForSimilarListings() {
        when(repository.propertyCandidates(any(), anyInt())).thenReturn(List.of(
            property("over", "HOUSE", DISTRICT, null, 80, "3200000000"),
            property("equal", "HOUSE", DISTRICT, null, 90, "3000000000"),
            property("under", "HOUSE", DISTRICT, null, 85, "450000000")));
        var buyer = service.rank(request(null, null, "8000000000", Purpose.BUYER_BUDGET_SEARCH, "3000000000", null));
        assertThat(ids(buyer)).containsExactly("property:under", "property:equal");
        var query = ArgumentCaptor.forClass(ComparableCandidateRepository.Search.class);
        verify(repository).propertyCandidates(query.capture(), eq(200));
        assertThat(query.getValue().maxPrice()).isEqualByComparingTo("3000000000");
        var similar = service.rank(request(null, null, "3000000000", null, null, null));
        assertThat(similar.reference().priceVnd()).isEqualByComparingTo("3000000000");
        assertThat(similar.comparables()).anySatisfy(c -> assertThat(c.scoreBreakdown()).containsKey("price"));
    }

    @Test
    void matchesStrictSameWardAndTypeWithoutRegionalFallbackOrResearch() {
        when(repository.propertyCandidates(any(), anyInt())).thenReturn(List.of(
            property("wrong-type", "VILLA", DISTRICT, "Hòa Cường Bắc", 80, "2000000000"),
            property("bad-ward", "HOUSE", DISTRICT, "Hòa Cường Nam", 80, "2000000000"),
            property("adjacent", "HOUSE", "Thanh Khê", "Hòa Cường Bắc", 80, "2000000000"),
            property("unknown", "HOUSE", DISTRICT, null, 80, "2000000000"),
            property("correct", "HOUSE", DISTRICT, "Hòa Cường Bắc", 80, "2000000000")));
        var result = service.rank(request(null, "Hòa Cường Bắc", null, Purpose.VALUATION_SUPPORT, null, null));
        assertThat(ids(result)).containsExactly("property:correct");
        assertThat(result.searchStage()).isEqualTo("WARD");
        verify(repository, never()).externalCandidates(any(), anyString(), anyInt());
        verify(repository, never()).tinixCandidates(any(), anyInt());
        verify(repository, never()).eligibleCounts();
    }

    @Test
    void mergesOnlyTrustedAliasesAndFlagsAreaPriceTwinsWithoutDroppingThem() {
        var rows = new ArrayList<>(List.of(
            external(1, "A", "42", "g1", "https://a.example/Case?listing=1", 80),
            external(2, "A", "42", "g2", null, 82),
            external(3, "A", "other", "g2", null, 81),
            external(4, "B", "42", "g1", "https://b.example/path", 80),
            external(5, "C", null, null, "HTTPS://A.EXAMPLE:443/Case?listing=1&utm_medium=x#photo", 81),
            external(6, "A", "", " ", null, 80),
            external(7, "A", " ", "", "", 80),
            external(8, "A", "only-repost", null, "https://a.example/Case?listing=8", 80)));
        when(repository.externalCandidates(any(), eq("Nhà ở"), eq(400))).thenAnswer(call -> List.copyOf(rows));
        var query = request(null, null, null, Purpose.VALUATION_SUPPORT, null, null);
        var first = service.rank(query);
        assertThat(ids(first)).containsExactly("external:1", "external:4", "external:6", "external:7", "external:8");
        assertThat(first.warnings()).anyMatch(w -> w.contains("POSSIBLE_SAME_ENTITY: external:1 / external:4"));
        Collections.reverse(rows);
        assertThat(service.rank(query)).isEqualTo(first);

        var subject = new SubjectIdentity(1L, "A", "42", null, "https://a.example/Case?listing=1");
        var excluded = service.rank(request(null, null, null, Purpose.VALUATION_SUPPORT, null, subject));
        assertThat(ids(excluded)).containsExactly("external:4", "external:6", "external:7", "external:8");
    }

    @Test
    void keepsCanonicalUrlIdentityConservative() {
        assertThat(ComparableIdentity.canonicalUrl(" HTTPS://Homes.EXAMPLE:443/Case?id=12&utm_medium=x#photo "))
            .isEqualTo("https://homes.example/Case?id=12");
        assertThat(ComparableIdentity.canonicalUrl("https://homes.example/Case?id=13"))
            .isNotEqualTo(ComparableIdentity.canonicalUrl("https://homes.example/case?id=13"));
        for (String url : List.of("", " ", "https:///bad", "javascript:alert(0)", "https://user@homes.example/")) {
            assertThat(ComparableIdentity.canonicalUrl(url)).isNull();
        }
    }

    private static Request request(String id, String ward, String price, Purpose purpose, String budget, SubjectIdentity subject) {
        return new Request(id, "HOUSE", DISTRICT, ward, bd("80"), bd(price), null, null, 5, false,
            purpose, bd(budget), subject);
    }

    private static ComparableCandidateRepository.PropertyRow property(String id, String type, String district, String ward,
                                                                         int area, String price) {
        return new ComparableCandidateRepository.PropertyRow(id, type, district, ward,
            BigDecimal.valueOf(area), bd(price), null);
    }

    private static ComparableCandidateRepository.ExternalRow external(long id, String source, String key,
                                                                         String group, String url, int area) {
        return new ComparableCandidateRepository.ExternalRow(id, source, "Nhà ở", DISTRICT, BigDecimal.valueOf(area),
            bd("2500000000"), "VALID", url, key, group);
    }

    private static List<String> ids(Response result) {
        return result.comparables().stream().map(Candidate::candidateId).toList();
    }

    private static BigDecimal bd(String value) {
        return value == null ? null : new BigDecimal(value);
    }
}
