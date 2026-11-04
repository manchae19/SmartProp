package vn.smartprop.modules.recommendation;

import com.fasterxml.jackson.databind.*;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import java.math.BigDecimal;
import java.nio.file.*;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
import static vn.smartprop.modules.recommendation.RecommendationDtos.*;

/** Real recovery CSV projection + actual Hybrid V1 code; mocked repository only.
 * No Spring server, MySQL, synthetic property rows or import execution. */
@EnabledIfEnvironmentVariable(named="SMARTPROP_RECOVERY_OFFLINE_TEST",matches="true")
class RecoveryOfflineHybridTest {
    final ObjectMapper mapper=new ObjectMapper();
    JsonNode data() throws Exception {
        Path root=Path.of(System.getenv("SMARTPROP_RECOVERY_FIXTURE")).toAbsolutePath().normalize();
        assertTrue(root.endsWith(Path.of("step18-4-1","offline_candidates.json")));
        JsonNode rows=mapper.readTree(root.toFile());assertEquals(275,rows.size());return rows;
    }
    Candidate candidate(JsonNode row) {
        var issues=new ArrayList<String>();row.path("qualityIssues").forEach(i->issues.add(i.asText()));
        PropertyType type=switch(row.path("category").asText()) {case "Nhà ở"->PropertyType.HOUSE;case "Đất nền"->PropertyType.LAND;case "Căn hộ chung cư"->PropertyType.APARTMENT;default->throw new AssertionError("Unknown fixture category");};
        String key=row.path("recordKey").asText(),group=row.path("duplicateGroup").isNull()?null:row.path("duplicateGroup").asText();
        return new Candidate(key,key,type,new BigDecimal(row.path("priceVnd").asText()),new BigDecimal(row.path("areaSqm").asText()),row.path("district").asText(),null,
            new Source("EXTERNAL",row.path("source").asText(),key,null),row.path("qualityStatus").asText(),"UNVERIFIED",group,group!=null,row.path("holdoutRisk").asBoolean(),issues,false);
    }
    HybridRecommendationService service(boolean demo,List<Candidate> values) {
        var repository=mock(RecommendationCandidateRepository.class);
        when(repository.find(any(),eq(demo))).thenReturn(values);
        return new HybridRecommendationService(repository,new PropertyScoringService(),new AreaScoringService(),demo);
    }
    @Test void actualRecoveryCandidatesUseAllBudgetsPurposesAndSafePolicyOffline() throws Exception {
        JsonNode rows=data();var candidates=new ArrayList<Candidate>();Set<String> admitted=new HashSet<>(),forbidden=new HashSet<>();
        for(var row:rows) {
            assertTrue(row.path("latitude").isNull());assertTrue(row.path("longitude").isNull());
            String key=row.path("recordKey").asText();
            if(row.path("admitted").asBoolean()) {
                assertTrue(Set.of("PREVIOUS_READY_UNCHANGED","AUTO_RECOVERED_READY").contains(row.path("decision").asText()));
                assertFalse(row.path("holdoutRisk").asBoolean());admitted.add(key);candidates.add(candidate(row));
            }else forbidden.add(key);
        }
        assertEquals(24,admitted.size());assertEquals(251,forbidden.size());assertTrue(Collections.disjoint(admitted,forbidden));
        var cases=new ArrayList<Response>();
        for(long budget:new long[]{750000000L,1250000000L,2350000000L,3780000000L,4650000000L,8900000000L,15500000000L}) {
            for(var purpose:Purpose.values()) {
                var request=new Request(BigDecimal.valueOf(budget),purpose,PropertyType.ALL,null,null,null,10);
                var safe=service(false,candidates).recommend(request);
                assertTrue(safe.topProperties().isEmpty());assertTrue(safe.topAreas().isEmpty());
                var demo=service(true,candidates).recommend(request);cases.add(demo);
                assertEquals(BigDecimal.valueOf(budget),demo.criteria().budgetVnd());
                assertTrue(demo.topProperties().size()<=10);assertTrue(demo.topAreas().size()<=5);
                Set<String> groups=new HashSet<>(),keys=new HashSet<>();double previous=101;
                for(var p:demo.topProperties()) {
                    assertTrue(admitted.contains(p.id()));assertFalse(forbidden.contains(p.id()));assertTrue(keys.add(p.id()));
                    assertTrue(p.priceVnd().compareTo(request.budgetVnd())<=0);assertEquals("UNVERIFIED",p.verificationStatus());
                    assertTrue(p.score()>=0&&p.score()<=100&&p.score()<=previous);previous=p.score();
                    assertFalse(p.explanations().isEmpty());assertTrue(p.warnings().stream().anyMatch(w->w.contains("UNVERIFIED")));
                    if(p.duplicateGroup()!=null)assertTrue(groups.add(p.duplicateGroup()));
                }
                assertEquals(demo.eligibleCandidateCount(),demo.topAreas().stream().mapToInt(AreaResult::candidateCount).sum());
            }
        }
        Path output=Path.of(System.getenv("SMARTPROP_RECOVERY_FIXTURE")).getParent().resolve("hybrid-java-offline-results.json");
        mapper.writerWithDefaultPrettyPrinter().writeValue(output.toFile(),Map.of("engine","actual Java Hybrid V1; CSV offline; repository mock; no HTTP/MySQL","cases",cases,"safeAllUnverifiedResults",0,"noFakeCoordinates",true));
    }
    @Test void recoveredLabelsRemainExactAndFiltersDoNotInferMissingWards() throws Exception {
        var values=new ArrayList<Candidate>();for(var row:data())if(row.path("admitted").asBoolean())values.add(candidate(row));
        for(var c:values) {
            var exact=new Request(c.price(),Purpose.LIVING,c.type(),c.area(),c.district(),null,10);
            assertEquals(1,service(true,List.of(c)).recommend(exact).topProperties().size());
            var below=new Request(c.price().subtract(BigDecimal.ONE),Purpose.LIVING,c.type(),null,null,null,10);
            assertTrue(service(true,List.of(c)).recommend(below).topProperties().isEmpty());
            var ward=new Request(c.price(),Purpose.RENTAL,c.type(),null,null,"missing-ward-must-not-be-inferred",10);
            assertTrue(service(true,List.of(c)).recommend(ward).topProperties().isEmpty());
        }
    }
}
