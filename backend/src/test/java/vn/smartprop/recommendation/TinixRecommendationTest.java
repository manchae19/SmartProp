package vn.smartprop.recommendation;
import java.math.BigDecimal;
import java.util.*;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
import static vn.smartprop.recommendation.RecommendationDtos.*;

class TinixRecommendationTest {
    Candidate row(String id,String group,boolean held,String status,BigDecimal price) {
        return new Candidate(id,"Dataset fixture",PropertyType.HOUSE,price,new BigDecimal("80.125"),"Hải Châu",null,
            new Source("TINIX_AI","TiniX AI",id,null),status,"UNVERIFIED",group,true,held,List.of(),false);
    }
    Request request(long price) { return new Request(BigDecimal.valueOf(price),Purpose.LIVING,PropertyType.ALL,null,null,null,10); }
    @Test void safeModeNeverQueriesOrReturnsTinix() {
        var repo=mock(RecommendationCandidateRepository.class);var tinix=mock(TinixCandidateRepository.class);
        when(repo.find(any(),eq(false))).thenReturn(List.of(row("t","g",false,"HYBRID_ELIGIBLE_RESEARCH",BigDecimal.ONE)));
        var s=new HybridRecommendationService(repo,new PropertyScoringService(),new AreaScoringService(),false);s.configureTinix(tinix,true);
        assertTrue(s.recommend(request(2000000000L)).topProperties().isEmpty());verifyNoInteractions(tinix);
    }
    @Test void internalGateBudgetHoldsReviewDedupAndAreaLimits() {
        var repo=mock(RecommendationCandidateRepository.class);when(repo.find(any(),eq(false))).thenReturn(List.of());
        var tinix=mock(TinixCandidateRepository.class);
        var rows=new ArrayList<Candidate>();
        for(int i=0;i<20;i++)rows.add(row("tinix:"+i,"g"+i,false,"HYBRID_ELIGIBLE_RESEARCH",new BigDecimal("1750000000")));
        rows.add(row("held","held",true,"HYBRID_ELIGIBLE_RESEARCH",BigDecimal.ONE));
        rows.add(row("review","review",false,"NEEDS_REVIEW",BigDecimal.ONE));
        rows.add(row("over","over",false,"HYBRID_ELIGIBLE_RESEARCH",new BigDecimal("1750000001")));
        rows.add(row("duplicate","g0",false,"HYBRID_ELIGIBLE_RESEARCH",new BigDecimal("1750000000")));
        when(tinix.find(any())).thenReturn(rows);
        var s=new HybridRecommendationService(repo,new PropertyScoringService(),new AreaScoringService(),false);s.configureTinix(tinix,true);
        var result=s.recommendResearch(request(1750000000L));
        assertEquals("INTERNAL_DEMO",result.mode());assertEquals(20,result.eligibleCandidateCount());assertEquals(10,result.topProperties().size());assertTrue(result.topAreas().size()<=5);
        assertTrue(result.topProperties().stream().allMatch(p->p.source().kind().equals("TINIX_AI")&&p.warnings().stream().anyMatch(w->w.contains("TiniX AI"))));
        s.configureTinix(tinix,false);assertThrows(RuntimeException.class,()->s.recommendResearch(request(1750000000L)));
    }
}
