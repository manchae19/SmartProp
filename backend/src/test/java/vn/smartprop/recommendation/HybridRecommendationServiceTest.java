package vn.smartprop.modules.recommendation;

import org.junit.jupiter.api.Test;
import java.math.BigDecimal;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
import static vn.smartprop.modules.recommendation.RecommendationDtos.*;

class HybridRecommendationServiceTest {
    @Test void blockedQualityNeverAppearsEvenInPrivateDemo() {
        assertTrue(service(true,List.of(external("blocked","BLOCKED","UNVERIFIED",null,false,List.of())))
            .recommend(request(2350000000L,Purpose.LIVING,PropertyType.ALL)).topProperties().isEmpty());
    }
    @Test void arbitraryBudgetsFilterExactlyToOneDongForEveryPurpose() {
        for (long amount : new long[]{750000000L,1250000000L,2350000000L,3780000000L,4650000000L,8900000000L,15500000000L,999999999999999L}) {
            var base=external("at-budget","VALID","VERIFIED",null,false,List.of());
            var exact=new Candidate(base.id(),base.title(),base.type(),BigDecimal.valueOf(amount),base.area(),base.district(),null,base.source(),base.quality(),base.verification(),null,false,false,List.of(),false);
            var over=new Candidate("one-dong-over",base.title(),base.type(),BigDecimal.valueOf(amount).add(BigDecimal.ONE),base.area(),base.district(),null,base.source(),base.quality(),base.verification(),null,false,false,List.of(),false);
            for(var purpose:Purpose.values()) {
                var response=service(false,List.of(exact,over)).recommend(request(amount,purpose,PropertyType.ALL));
                assertEquals(List.of("at-budget"),response.topProperties().stream().map(PropertyResult::id).toList());
                assertEquals(BigDecimal.valueOf(amount),response.criteria().budgetVnd());
            }
        }
    }
    Request request(long budget,Purpose purpose,PropertyType type) { return new Request(BigDecimal.valueOf(budget),purpose,type,null,null,null,10); }
    Candidate external(String id,String quality,String verification,String group,boolean holdout,List<String> issues) {
        return new Candidate(id,id,PropertyType.HOUSE,new BigDecimal("1600000000"),new BigDecimal("80"),"Hải Châu",null,
            new Source("EXTERNAL","fixture",id,"https://example.invalid/"+id),quality,verification,group,group!=null,holdout,issues,false);
    }
    HybridRecommendationService service(boolean demo,List<Candidate> candidates) {
        var repo=mock(RecommendationCandidateRepository.class);
        when(repo.find(any(),eq(demo))).thenReturn(candidates);
        return new HybridRecommendationService(repo,new PropertyScoringService(),new AreaScoringService(),demo);
    }
    @Test void safeModeExcludesUnverifiedRejectedReviewAndHoldout() {
        var values=List.of(external("ok","VALID","VERIFIED",null,false,List.of()),
            external("raw","VALID","UNVERIFIED",null,false,List.of()),external("reject","REJECTED","VERIFIED",null,false,List.of()),
            external("held","VALID","VERIFIED",null,true,List.of()),external("review","NEEDS_REVIEW","VERIFIED",null,false,List.of("NEAR_DUPLICATE")));
        var result=service(false,values).recommend(request(2_000_000_000L,Purpose.LIVING,PropertyType.ALL));
        assertEquals(List.of("ok"),result.topProperties().stream().map(PropertyResult::id).toList());
        assertEquals("SAFE",result.mode());
    }
    @Test void demoAllowsOnlyDocumentedReviewIssuesAndWarns() {
        var values=List.of(external("valid","VALID","UNVERIFIED",null,false,List.of()),
            external("review","NEEDS_REVIEW","UNVERIFIED","g",false,List.of("NEAR_DUPLICATE")),
            external("mismatch","NEEDS_REVIEW","UNVERIFIED",null,false,List.of("CATEGORY_MISMATCH")),
            external("multi","NEEDS_REVIEW","UNVERIFIED",null,false,List.of("MULTI_PROPERTY")),
            external("rejected","REJECTED","UNVERIFIED",null,false,List.of()),
            external("holdout","VALID","UNVERIFIED",null,true,List.of()));
        var result=service(true,values).recommend(request(2_000_000_000L,Purpose.LIVING,PropertyType.ALL));
        assertEquals(Set.of("valid","review"),new HashSet<>(result.topProperties().stream().map(PropertyResult::id).toList()));
        assertTrue(result.topProperties().stream().allMatch(p->p.warnings().stream().anyMatch(w->w.contains("UNVERIFIED"))));
        var review=result.topProperties().stream().filter(p->p.id().equals("review")).findFirst().orElseThrow();
        assertTrue(review.warnings().stream().anyMatch(w->w.contains("NEEDS_REVIEW")));
        assertTrue(result.topProperties().getFirst().score()>review.score());
    }
    @Test void duplicateGroupsHaveOneDeterministicRepresentativeAndOneAreaVote() {
        var values=List.of(external("b","VALID","UNVERIFIED","g",false,List.of()),external("a","VALID","UNVERIFIED","g",false,List.of()));
        var result=service(true,values).recommend(request(2_000_000_000L,Purpose.LIVING,PropertyType.ALL));
        assertEquals(1,result.eligibleCandidateCount());assertEquals("a",result.topProperties().getFirst().id());
        assertEquals(1,result.topAreas().getFirst().candidateCount());
    }
    @Test void priceTypeDistrictAreaAndWardFiltersDoNotInferMissingData() {
        var c=external("c","VALID","UNVERIFIED",null,false,List.of());
        var service=service(true,List.of(c));
        assertTrue(service.recommend(request(1_000_000_000L,Purpose.LIVING,PropertyType.ALL)).topProperties().isEmpty());
        assertTrue(service.recommend(request(2_000_000_000L,Purpose.RENTAL,PropertyType.APARTMENT)).topProperties().isEmpty());
        var matching=new Request(new BigDecimal("2000000000"),Purpose.LIVING,PropertyType.HOUSE,new BigDecimal("70"),"hai chau",null,10);
        assertEquals(1,service.recommend(matching).topProperties().size());
        var ward=new Request(matching.budgetVnd(),matching.purpose(),matching.propertyType(),null,null,"Hải Châu I",10);
        assertTrue(service.recommend(ward).topProperties().isEmpty());
    }
    @Test void publishedPlatformAndExternalAutomaticallyMix() {
        var published=new Candidate("p","Platform",PropertyType.HOUSE,new BigDecimal("1500000000"),new BigDecimal("80"),"Hải Châu","Hải Châu I",
            new Source("PROPERTY","SmartProp","p","/api/v1/properties/p"),"PLATFORM_PUBLISHED","PLATFORM_PUBLISHED",null,false,false,List.of(),false);
        var result=service(false,List.of(published,external("e","VALID","VERIFIED",null,false,List.of())))
            .recommend(request(2_000_000_000L,Purpose.LIVING,PropertyType.ALL));
        assertEquals(Set.of("PROPERTY","EXTERNAL"),new HashSet<>(result.topProperties().stream().map(p->p.source().kind()).toList()));
    }
    @Test void emptySafeModeIsValidAndCannotInventAreas() {
        var result=service(false,List.of()).recommend(request(2_000_000_000L,Purpose.LIVING,PropertyType.ALL));
        assertTrue(result.topAreas().isEmpty());assertTrue(result.topProperties().isEmpty());
    }
    @Test void scoringIsBoundedAndPurposeUsesDocumentedWeights() {
        var c=external("c","VALID","UNVERIFIED",null,false,List.of());var scorer=new PropertyScoringService();
        var living=scorer.score(c,request(2_000_000_000L,Purpose.LIVING,PropertyType.ALL));
        var investment=scorer.score(c,request(2_000_000_000L,Purpose.INVESTMENT,PropertyType.ALL));
        assertNotEquals(living.score(),investment.score());
        for(var purpose:Purpose.values())assertTrue(scorer.score(c,request(2_000_000_000L,purpose,PropertyType.ALL)).score()>=0);
    }
    @Test void groupHoldoutOrInconsistentValidMetadataFailsClosed() {
        var c=external("bad","VALID","UNVERIFIED",null,false,List.of("CATEGORY_MISMATCH"));
        var held=new Candidate("sibling","Sibling",c.type(),c.price(),c.area(),c.district(),null,c.source(),"VALID","UNVERIFIED","holdout-group",true,false,List.of(),true);
        assertTrue(service(true,List.of(c,held)).recommend(request(2_000_000_000L,Purpose.LIVING,PropertyType.ALL)).topProperties().isEmpty());
    }
}
