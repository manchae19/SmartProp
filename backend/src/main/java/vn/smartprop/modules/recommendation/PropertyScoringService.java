package vn.smartprop.modules.recommendation;

import org.springframework.stereotype.Service;
import java.util.*;
import static vn.smartprop.modules.recommendation.RecommendationDtos.*;

@Service
public class PropertyScoringService {
    public Scored score(Candidate c,Request r) {
        double ratio=c.price().divide(r.budgetVnd(),12,java.math.RoundingMode.HALF_UP).doubleValue();
        double budget=100*Math.max(0,1-Math.abs(ratio-.8)/.8);
        double areaTarget=r.minAreaSqm()==null?100:r.minAreaSqm().doubleValue()*1.5;
        double area=100*Math.min(1,c.area().doubleValue()/areaTarget);
        double budgetWeight=switch(r.purpose()) {case LIVING->.6;case INVESTMENT->.8;case RENTAL->.7;};
        double penalty=("UNVERIFIED".equals(c.verification())?10:0)+("NEEDS_REVIEW".equals(c.quality())?15:0);
        double score=round(Math.max(0,Math.min(100,budgetWeight*budget+(1-budgetWeight)*area-penalty)));
        return new Scored(c,score,Map.of("budgetFit",round(budget),"areaFit",round(area),"reviewPenalty",penalty),
            List.of("Giá rao "+c.price().toPlainString()+" VND nằm trong ngân sách "+r.budgetVnd().toPlainString()+" VND.",
                "Diện tích theo nguồn: "+c.area().toPlainString()+" m².",
                "Heuristic "+r.purpose()+": trọng số ngân sách "+round(budgetWeight*100)+"%, diện tích "+round((1-budgetWeight)*100)+"%; trừ cờ rà soát "+penalty+" điểm."));
    }
    static double round(double n) { return Math.round(n*100d)/100d; }
}
