package vn.smartprop.recommendation;

import org.springframework.stereotype.Service;
import java.math.*;
import java.util.*;
import static vn.smartprop.recommendation.RecommendationDtos.*;

@Service
public class AreaScoringService {
    public List<AreaResult> top(List<Scored> candidates) {
        Map<String,List<Scored>> grouped=new TreeMap<>();
        for(var s:candidates) {
            if(s.candidate().district()==null || s.candidate().district().isBlank())continue;
            String key=HybridRecommendationService.normalize(s.candidate().district())+"|"+HybridRecommendationService.normalize(s.candidate().ward());
            grouped.computeIfAbsent(key,k->new ArrayList<>()).add(s);
        }
        var result=new ArrayList<AreaResult>();
        grouped.values().forEach(group->{
            var first=group.getFirst().candidate();
            int unverified=(int)group.stream().filter(s->"UNVERIFIED".equals(s.candidate().verification())).count();
            int review=(int)group.stream().filter(s->"NEEDS_REVIEW".equals(s.candidate().quality())).count();
            var sum=group.stream().map(s->s.candidate().price()).reduce(BigDecimal.ZERO,BigDecimal::add);
            result.add(new AreaResult(first.district(),first.ward(),group.size(),
                PropertyScoringService.round(group.stream().mapToDouble(Scored::score).average().orElse(0)),
                sum.divide(BigDecimal.valueOf(group.size()),2,RoundingMode.HALF_UP),
                group.stream().map(s->s.candidate().source().name()).distinct().sorted().toList(),unverified,review,
                List.of("Điểm trung bình của "+group.size()+" ứng viên sau lọc và khử nhóm trùng; địa bàn theo nguồn.",
                    "Trung bình giá rao của mẫu, không phải giá thị trường hay dự báo tăng giá."),
                unverified>0||review>0?List.of("Mẫu demo nội bộ chứa tin chưa xác minh/cần rà soát; không coi là nguồn cung đã xác minh."):List.of()));
        });
        return result.stream().sorted(Comparator.comparingDouble(AreaResult::score).reversed()
            .thenComparing(AreaResult::district).thenComparing(a->a.ward()==null?"":a.ward())).limit(5).toList();
    }
}
