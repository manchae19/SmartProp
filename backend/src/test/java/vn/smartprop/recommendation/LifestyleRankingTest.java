package vn.smartprop.modules.recommendation;

import java.math.BigDecimal;
import java.util.*;
import org.junit.jupiter.api.Test;
import vn.smartprop.modules.amenity.AmenityDtos.*;
import vn.smartprop.modules.recommendation.PropertyLocationResolver.Resolution;
import static vn.smartprop.modules.recommendation.RecommendationDtos.*;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class LifestyleRankingTest {
    AmenityProfile profile(String name,double school,double shop) {
        return new AmenityProfile(name,"DISTRICT",name,name,50,
            new CategoryScores(shop,school,50,50,50),.8,.5,0,
            new PoiCounts(8,1,1,1,1,1,1,1,1),null,null,"FULL","false",List.of(),"",List.of(),List.of());
    }
    Candidate candidate(String id,String district, String price) {
        return new Candidate(id,id,PropertyType.APARTMENT,new BigDecimal(price),new BigDecimal("80"),district,null,
            new Source("PROPERTY","SmartProp",id,"/listing/"+id),"PLATFORM_PUBLISHED","PLATFORM_PUBLISHED",null,false,false,List.of(),false);
    }
    Request request(List<AmenityPriority> priorities) {
        return new Request(new BigDecimal("2000000000"),Purpose.LIVING,PropertyType.APARTMENT,null,null,null,1,priorities);
    }
    HybridRecommendationService service() {
        var repo=mock(RecommendationCandidateRepository.class);
        when(repo.find(any(),anyBoolean())).thenReturn(List.of(candidate("school-area","A","1600000000"),
            candidate("shop-area","B","1600000000"),candidate("over-budget","A","2100000000")));
        var resolver=mock(PropertyLocationResolver.class);
        when(resolver.resolve("A",null)).thenReturn(new Resolution(profile("A",95,10),"DISTRICT_SHARED_AMENITY",.8,false));
        when(resolver.resolve("B",null)).thenReturn(new Resolution(profile("B",10,95),"DISTRICT_SHARED_AMENITY",.8,false));
        var score=new PropertyScoringV11Service(resolver,.38,.17,.20,.25,.45,.25,.20,.10,.40,.20,.25,.15);
        var evidence=new AmenityEvidenceService();
        return new HybridRecommendationService(repo,new PropertyScoringService(),new AreaScoringService(),false,
            score,new AreaScoringV11Service(resolver,evidence),evidence,resolver,true);
    }
    @Test void primaryPreferenceChangesWinnerBeforeLimitWithoutRelaxingBudget() {
        var service=service();
        var schools=service.recommend(request(List.of(AmenityPriority.SCHOOL,AmenityPriority.SUPERMARKET)));
        var shops=service.recommend(request(List.of(AmenityPriority.SUPERMARKET,AmenityPriority.SCHOOL)));
        assertEquals("school-area",schools.topProperties().getFirst().id());
        assertEquals("shop-area",shops.topProperties().getFirst().id());
        assertEquals(1,schools.topProperties().size());
        assertEquals(2,schools.eligibleCandidateCount());
        assertTrue(schools.topProperties().getFirst().explanations().stream().anyMatch(s->s.contains("chưa xác nhận trường tiểu học")));
    }
    @Test void absentPreferencesPreserveOriginalAmenityScoreAndMissingDataIsNotZero() {
        assertEquals(50.0,PropertyScoringV11Service.amenityFit(profile("A",95,10),request(List.of())));
        assertNull(PropertyScoringV11Service.amenityFit(null,request(List.of(AmenityPriority.SCHOOL))));
        var missing=new AmenityProfile("x","DISTRICT","x","x",50,new CategoryScores(10,95,10,10,10),.8,.5,0,
            new PoiCounts(0,0,0,0,0,0,0,0,0),null,null,"UNKNOWN","true",List.of(),"",List.of(),List.of());
        assertNull(PropertyScoringV11Service.amenityFit(missing,request(List.of(AmenityPriority.SCHOOL))));
    }
    @Test void oldJsonAndConstructorRemainCompatible() throws Exception {
        var mapper=new com.fasterxml.jackson.databind.ObjectMapper();
        var old=mapper.readValue("{\"budgetVnd\":2000000000,\"purpose\":\"LIVING\",\"propertyType\":\"APARTMENT\",\"limit\":1}",Request.class);
        assertTrue(old.amenityPriorities().isEmpty());
        assertTrue(new Request(new BigDecimal("1"),Purpose.LIVING,PropertyType.ALL,null,null,null,1).amenityPriorities().isEmpty());
    }
    @Test void preferencesCannotBeSilentlyIgnoredWhenV11IsOff() {
        var repo=mock(RecommendationCandidateRepository.class);
        var service=new HybridRecommendationService(repo,new PropertyScoringService(),new AreaScoringService(),false);
        assertThrows(org.springframework.web.server.ResponseStatusException.class,()->service.recommend(request(List.of(AmenityPriority.SCHOOL))));
        verifyNoInteractions(repo);
    }
}