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
            external(1, "A", "42", "g1", "https://a.example/Detail?listing=1", 80),
            external(2, "A", "42", "g2", null, 82),
            external(3, "A", "other", "g2", null, 81),
            external(4, "B", "42", "g1", "https://b.example/path", 80),
            external(5, "C", null, null, "HTTPS://A.EXAMPLE:443/Detail?listing=1&utm_medium=x", 81),
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

        var subject = new SubjectIdentity(1L, "A", "42", null, "https://a.example/Detail?listing=1");
        var excluded = service.rank(request(null, null, null, Purpose.VALUATION_SUPPORT, null, subject));
        assertThat(ids(excluded)).containsExactly("external:4", "external:6", "external:7", "external:8");
    }

    @Test
    void keepsCanonicalUrlIdentityConservative() {
        assertThat(ComparableIdentity.canonicalUrl(" HTTPS://Homes.EXAMPLE:443/Detail?listingId=12&id=7&utm_medium=x#photo "))
            .isEqualTo("https://homes.example/Detail?listingId=12&id=7#photo");
        assertThat(ComparableIdentity.canonicalUrl("https://homes.example/Detail?listing=13"))
            .isNotEqualTo(ComparableIdentity.canonicalUrl("https://homes.example/detail?listing=13"));
        assertThat(ComparableIdentity.canonicalUrl("https://homes.example/#/listing/13"))
            .isNotEqualTo(ComparableIdentity.canonicalUrl("https://homes.example/#/listing/14"));
        for (String url : List.of("", " ", "https:///bad", "javascript:alert(0)", "https://user@homes.example/",
                "https://homes.example/", "https://homes.example/listings", "https://homes.example/category?id=123",
                "https://homes.example/landing?utm_source=123#map", "https://homes.example/category?listingId=42")) {
            assertThat(ComparableIdentity.canonicalUrl(url)).isNull();
        }
    }

    @Test
    void sharedGenericLinksCannotMergeDistinctRecordsAcrossProviders() {
        when(repository.externalCandidates(any(), anyString(), anyInt())).thenReturn(List.of(
            external(1, "A", "42", null, "https://homes.example/", 80),
            external(2, "B", "42", null, "https://homes.example/", 80),
            external(3, "A", "43", null, "https://homes.example/category?id=42", 80),
            external(4, "B", "43", null, "https://homes.example/category?id=42", 80),
            external(5, "B", "44", null, "https://homes.example/landing", 80)));
        var result = service.rank(request(null, null, null, Purpose.VALUATION_SUPPORT, null, null));
        assertThat(ids(result)).containsExactly("external:1", "external:2", "external:3", "external:4", "external:5");
    }

    @Test
    void canonicalSelfMatchFillingTheHardLimitIsReportedAsIncomplete() {
        var duplicates = java.util.stream.LongStream.rangeClosed(1, 1201)
            .mapToObj(id -> external(id, "A", null, null, "https://homes.example/listings/77", 80)).toList();
        when(repository.externalCandidates(any(), anyString(), anyInt()))
            .thenAnswer(call -> duplicates.subList(0, call.getArgument(2)));
        var subject = new SubjectIdentity(null, null, null, null, "https://homes.example/listings/77");
        var result = service.rank(request(null, null, null, Purpose.VALUATION_SUPPORT, null, subject));
        assertThat(ids(result)).isEmpty();
        assertThat(result.warnings()).anyMatch(w -> w.startsWith("SCAN_LIMIT_REACHED"));
        assertThat(result.evidence().scanComplete()).isFalse();
        assertThat(result.evidence().status()).isEqualTo(EvidenceStatus.INSUFFICIENT_EVIDENCE);
        assertThat(result.evidence().dedupe().exactSelfExcluded()).isEqualTo(1200);
        verify(repository, times(2)).externalCandidates(any(), anyString(), anyInt());
    }

    @Test
    void cohortStatisticsUseEligibleUniqueRowsOutsideTheReturnedSample() {
        when(repository.propertyCandidates(any(), anyInt())).thenReturn(List.of(
            property("1", "HOUSE", DISTRICT, null, 80, "2000000000"),
            property("2", "HOUSE", DISTRICT, null, 80, "4000000000"),
            property("3", "HOUSE", DISTRICT, null, 80, "6000000000"),
            property("4", "HOUSE", DISTRICT, null, 100, "8000000000"),
            property("5", "HOUSE", DISTRICT, null, 100, "10000000000"),
            property("6", "HOUSE", DISTRICT, null, 100, "12000000000"),
            property("6", "HOUSE", DISTRICT, null, 100, "12000000000"),
            property("outside", "HOUSE", "Thanh Khê", null, 80, "19000000000")));
        var request = new Request(null, "HOUSE", DISTRICT, null, bd("80"), null, null, null, 2,
            false, Purpose.VALUATION_SUPPORT, null, null);
        var result = service.rank(request);
        Evidence evidence = result.evidence();
        assertThat(ids(result)).containsExactly("property:1", "property:2");
        assertThat(evidence.purpose()).isEqualTo(Purpose.VALUATION_SUPPORT);
        assertThat(evidence.retrievedCandidateCount()).isEqualTo(7);
        assertThat(evidence.uniqueEligibleCandidateCount()).isEqualTo(6);
        assertThat(evidence.returnedSampleCount()).isEqualTo(2);
        assertThat(evidence.status()).isEqualTo(EvidenceStatus.AVAILABLE);
        assertThat(evidence.scannedCohortAskingPrice().medianPriceVnd()).isEqualByComparingTo("7000000000");
        assertThat(evidence.scannedCohortAskingPrice().medianPricePerSqmVnd()).isEqualByComparingTo("77500000");
        assertThat(evidence.provenance()).doesNotContainKey(SourceKind.TINIX_RESEARCH);
    }

    @Test
    void smallCohortReturnsRowsAndSuppressesBothMedians() {
        when(repository.propertyCandidates(any(), anyInt())).thenReturn(List.of(
            property("one", "HOUSE", DISTRICT, null, 80, "2000000000")));
        var result = service.rank(request(null, null, null, Purpose.VALUATION_SUPPORT, null, null));
        assertThat(ids(result)).containsExactly("property:one");
        assertThat(result.evidence().status()).isEqualTo(EvidenceStatus.INSUFFICIENT_EVIDENCE);
        assertThat(result.evidence().scannedCohortAskingPrice().observations()).isEqualTo(1);
        assertThat(result.evidence().scannedCohortAskingPrice().medianPriceVnd()).isNull();
        assertThat(result.evidence().scannedCohortAskingPrice().medianPricePerSqmVnd()).isNull();
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
