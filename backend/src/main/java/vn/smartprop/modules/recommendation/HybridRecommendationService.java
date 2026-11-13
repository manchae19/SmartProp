package vn.smartprop.modules.recommendation;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.text.Normalizer;
import java.util.*;
import static vn.smartprop.modules.recommendation.RecommendationDtos.*;

@Service
public class HybridRecommendationService {
    private final RecommendationCandidateRepository repository;
    private final PropertyScoringService propertyScoring;
    private final AreaScoringService areaScoring;
    private final boolean demo;

    /* Hybrid V1.1 is additive: V1 stays the default and both paths share the same
       candidate selection, holdout rules and deduplication. */
    private final PropertyScoringV11Service propertyScoringV11;
    private final AreaScoringV11Service areaScoringV11;
    private final AmenityEvidenceService amenityEvidence;
    private final PropertyLocationResolver propertyLocationResolver;
    private final boolean v11Enabled;
    private TinixCandidateRepository tinix;
    private boolean tinixEnabled;
    @org.springframework.beans.factory.annotation.Autowired
    void configureTinix(TinixCandidateRepository tinix,@Value("${app.recommendation.tinix-enabled:false}") boolean enabled) {
        this.tinix=tinix;this.tinixEnabled=enabled;
    }
    public boolean tinixEnabled() { return tinixEnabled; }
    static final Set<String> DEMO_REVIEW_ISSUES=Set.of("NEAR_DUPLICATE","MISSING_DISTRICT");
    @org.springframework.beans.factory.annotation.Autowired
    public HybridRecommendationService(RecommendationCandidateRepository repository,PropertyScoringService propertyScoring,
            AreaScoringService areaScoring,@Value("${app.recommendation.allow-unverified-external:false}") boolean demo,
            org.springframework.beans.factory.ObjectProvider<PropertyScoringV11Service> propertyScoringV11,
            org.springframework.beans.factory.ObjectProvider<AreaScoringV11Service> areaScoringV11,
            org.springframework.beans.factory.ObjectProvider<AmenityEvidenceService> amenityEvidence,
            org.springframework.beans.factory.ObjectProvider<PropertyLocationResolver> propertyLocationResolver,
            @Value("${app.recommendation.v11-enabled:false}") boolean v11Enabled) {
        this(repository,propertyScoring,areaScoring,demo,propertyScoringV11.getIfAvailable(),
            areaScoringV11.getIfAvailable(),amenityEvidence.getIfAvailable(),propertyLocationResolver.getIfAvailable(),v11Enabled);
    }
    public HybridRecommendationService(RecommendationCandidateRepository repository,PropertyScoringService propertyScoring,
            AreaScoringService areaScoring,@Value("${app.recommendation.allow-unverified-external:false}") boolean demo) {
        this(repository,propertyScoring,areaScoring,demo,(PropertyScoringV11Service)null,(AreaScoringV11Service)null,
            (AmenityEvidenceService)null,(PropertyLocationResolver)null,false);
    }
    HybridRecommendationService(RecommendationCandidateRepository repository,PropertyScoringService propertyScoring,
            AreaScoringService areaScoring,boolean demo,PropertyScoringV11Service propertyScoringV11,
            AreaScoringV11Service areaScoringV11,AmenityEvidenceService amenityEvidence,
            PropertyLocationResolver propertyLocationResolver,boolean v11Enabled) {
        this.repository=repository;this.propertyScoring=propertyScoring;this.areaScoring=areaScoring;this.demo=demo;
        this.propertyScoringV11=propertyScoringV11;this.areaScoringV11=areaScoringV11;
        this.amenityEvidence=amenityEvidence;this.propertyLocationResolver=propertyLocationResolver;
        this.v11Enabled=v11Enabled&&propertyScoringV11!=null&&areaScoringV11!=null&&propertyLocationResolver!=null;
    }
    public boolean internalDemo() { return demo; }
    public boolean v11Enabled() { return v11Enabled; }
    @Transactional(readOnly=true)
    public Response recommend(Request request) {
        return recommend(request,false);
    }
    @Transactional(readOnly=true)
    public Response recommendResearch(Request request) {
        if(!tinixEnabled||tinix==null)throw vn.smartprop.common.ApiInputs.forbidden();
        return recommend(request,true);
    }
    private Response recommend(Request request,boolean research) {
        if(!request.amenityPriorities().isEmpty()&&!v11Enabled)
            throw new org.springframework.web.server.ResponseStatusException(org.springframework.http.HttpStatus.SERVICE_UNAVAILABLE,"Personalized ranking requires APP_RECOMMENDATION_V11_ENABLED=true and V1.1 services");
        boolean demo=this.demo||research;
        var raw=new ArrayList<>(repository.find(request,this.demo));
        if(research)raw.addAll(tinix.find(request));
        var warnings=new ArrayList<String>();
        warnings.add("HEURISTIC_V1: điểm quy tắc tham khảo, không phải AI cá nhân hóa đã huấn luyện hoặc dự báo lợi nhuận.");
        warnings.add("RENTAL là mua để khai thác cho thuê; ngân sách là tổng giá mua, không phải tiền thuê. Không dự đoán lợi suất thuê.");
        if(demo)warnings.add("INTERNAL_DEMO: chứa dữ liệu UNVERIFIED/NEEDS_REVIEW có điều kiện; không công khai như tin đã xác minh.");
        if(research)warnings.add("TiniX AI / tinixai/vietnam-real-estates, CC BY-NC 4.0: dữ liệu lịch sử 2025–2026 chỉ nghiên cứu phi thương mại, đã lọc bằng quy tắc; chưa xác minh còn bán. Không dự báo lợi suất hay mức tăng giá.");
        if(request.ward()!=null&&!request.ward().isBlank())warnings.add("External chưa có ward chuẩn hóa; không suy ra phường/xã từ địa chỉ thô.");
        if(raw.stream().filter(c->"EXTERNAL".equals(c.source().kind())).count()>=RecommendationCandidateRepository.CAP
            ||raw.stream().filter(c->"PROPERTY".equals(c.source().kind())).count()>=RecommendationCandidateRepository.CAP)
            warnings.add("Nguồn vượt giới hạn10001 ứng viên mỗi loại; kết quả chỉ xếp hạng trong tập đã đọc theo ID.");
        if (v11Enabled) return rankV11(raw,request,research,demo,warnings);
        var ranked=raw.stream().filter(c->eligible(c,request,research)).map(c->propertyScoring.score(c,request))
            .sorted(Comparator.comparingDouble(Scored::score).reversed().thenComparing(s->s.candidate().id())).toList();
        Map<String,Scored> unique=new LinkedHashMap<>();
        for(var s:ranked) {
            var c=s.candidate();
            String key=Set.of("EXTERNAL","TINIX_AI").contains(c.source().kind())&&c.duplicateGroup()!=null?"group:"+c.duplicateGroup():c.id();
            unique.putIfAbsent(key,s);
        }
        var candidates=List.copyOf(unique.values());
        var top=candidates.stream().limit(request.limit()==null?10:request.limit()).map(s->{
            var c=s.candidate();var itemWarnings=new ArrayList<String>();
            if("TINIX_AI".equals(c.source().kind()))itemWarnings.add("Dữ liệu nghiên cứu TiniX AI — chưa xác minh. Lịch sử, trạng thái còn bán UNKNOWN; không có URL tin gốc, liên hệ hoặc tọa độ từng căn. Nguồn: https://huggingface.co/datasets/tinixai/vietnam-real-estates (CC BY-NC 4.0).");
            else if("UNVERIFIED".equals(c.verification()))itemWarnings.add("UNVERIFIED: dữ liệu crawler chưa xác minh, chỉ dùng demo nội bộ; chưa kiểm tra tin còn bán.");
            if("NEEDS_REVIEW".equals(c.quality()))itemWarnings.add("NEEDS_REVIEW: chỉ chấp nhận cờ "+c.issues()+" trong demo; không phải tin đủ tin cậy.");
            if(c.duplicateGroup()!=null)itemWarnings.add("Một đại diện nhóm nghi trùng "+c.duplicateGroup()+"; chưa chứng minh là một tài sản đã xác minh.");
            return new PropertyResult(c.id(),c.title(),c.type(),c.price(),c.area(),c.district(),c.ward(),s.score(),s.parts(),s.explanations(),
                c.source(),c.quality(),c.verification(),c.duplicateGroup(),List.copyOf(itemWarnings),null);
        }).toList();
        return new Response("HEURISTIC_V1",demo?"INTERNAL_DEMO":"SAFE","ASKING_SALE_VND_TOTAL",request,
            candidates.size(),areaScoring.top(candidates),top,List.copyOf(warnings),null);
    }

    /** Hybrid V1.1 ranking. Same eligibility and dedup rules as V1; new scoring and amenity evidence. */
    private Response rankV11(List<Candidate> raw,Request request,boolean research,boolean demo,List<String> warnings) {
        warnings.add("HEURISTIC_V1_1: điểm quy tắc có trọng số, không phải AI đã huấn luyện và không dự báo lợi nhuận.");
        if(!request.purpose().name().equals("LIVING"))warnings.add("PURPOSE_WEIGHTS: trọng số tiện ích được giảm cho "+request.purpose()+"; tiện ích không được coi là tiêu chí chính.");
        var ranked=raw.stream().filter(c->eligible(c,request,research))
            .map(c->propertyScoringV11.scoreForRanking(c,request,propertyLocationResolver.resolve(c.district(),c.ward())))
            .sorted(Comparator.comparingDouble(PropertyScoringV11Service.Scored11::score).reversed()
                .thenComparing(s->s.candidate().id())).toList();
        Map<String,PropertyScoringV11Service.Scored11> unique=new LinkedHashMap<>();
        for(var s:ranked) {
            var c=s.candidate();
            String key=Set.of("EXTERNAL","TINIX_AI").contains(c.source().kind())&&c.duplicateGroup()!=null?"group:"+c.duplicateGroup():c.id();
            unique.putIfAbsent(key,s);
        }
        var candidates=List.copyOf(unique.values());
        var top=candidates.stream().limit(request.limit()==null?10:request.limit()).map(s->{
            var c=s.candidate();var itemWarnings=new ArrayList<>(baseWarnings(c));
            var evidence=s.resolution()!=null&&s.resolution().available()
                ? amenityEvidence.build(s.resolution().profile(),s.resolution(),s.amenityFit())
                : amenityEvidence.unavailable(s.resolution());
            if(!s.resolution().available())itemWarnings.add("NO_AMENITY_EVIDENCE: chưa có hồ sơ tiện ích cho địa bàn; điểm không cộng thành phần tiện ích.");
            else if(!s.resolution().wardLevel())itemWarnings.add("AMENITY_IS_DISTRICT_SHARED: tiện ích là đặc điểm chung của quận/huyện, không phải khoảng cách từ căn nhà.");
            else if(evidence!=null&&evidence.coverage()!=null&&evidence.coverage().contains("WITH_GAPS"))itemWarnings.add("AMENITY_COVERAGE_GAPS: hồ sơ tiện ích còn thiếu trụ cột; không suy ra chất lượng sống thấp hơn thực tế.");
            return new PropertyResult(c.id(),c.title(),c.type(),c.price(),c.area(),c.district(),c.ward(),s.score(),s.parts(),
                propertyScoringV11.explain(c,request,s),
                c.source(),c.quality(),c.verification(),c.duplicateGroup(),List.copyOf(itemWarnings),evidence);
        }).toList();
        return new Response("HEURISTIC_V1_1",demo?"INTERNAL_DEMO":"SAFE","ASKING_SALE_VND_TOTAL",request,
            candidates.size(),areaScoringV11.top(candidates),top,List.copyOf(warnings),
            propertyScoringV11.weights().asMap(request.purpose()));
    }

    private static List<String> baseWarnings(Candidate c) {
        var itemWarnings=new ArrayList<String>();
        if("TINIX_AI".equals(c.source().kind()))itemWarnings.add("Dữ liệu nghiên cứu TiniX AI — chưa xác minh. Lịch sử, trạng thái còn bán UNKNOWN; không có URL tin gốc, liên hệ hoặc tọa độ từng căn. Nguồn: https://huggingface.co/datasets/tinixai/vietnam-real-estates (CC BY-NC 4.0).");
        else if("UNVERIFIED".equals(c.verification()))itemWarnings.add("UNVERIFIED: dữ liệu crawler chưa xác minh, chỉ dùng demo nội bộ; chưa kiểm tra tin còn bán.");
        if("NEEDS_REVIEW".equals(c.quality()))itemWarnings.add("NEEDS_REVIEW: chỉ chấp nhận cờ "+c.issues()+" trong demo; không phải tin đủ tin cậy.");
        if(c.duplicateGroup()!=null)itemWarnings.add("Một đại diện nhóm nghi trùng "+c.duplicateGroup()+"; chưa chứng minh là một tài sản đã xác minh.");
        return itemWarnings;
    }

    boolean eligible(Candidate c,Request r) {
        return eligible(c,r,false);
    }
    private boolean eligible(Candidate c,Request r,boolean research) {
        if(c.holdout()||c.groupHasHoldout()||c.type()==null||c.price()==null||c.area()==null||c.price().signum()<=0||c.area().signum()<=0)return false;
        if(r.minPriceVnd()!=null&&c.price().compareTo(r.minPriceVnd())<0)return false;
        if(c.price().compareTo(r.budgetVnd())>0 || (r.minAreaSqm()!=null&&c.area().compareTo(r.minAreaSqm())<0))return false;
        if(r.propertyType()!=PropertyType.ALL&&r.propertyType()!=c.type())return false;
        if(!matches(r.district(),c.district())||!matches(r.ward(),c.ward()))return false;
        if("TINIX_AI".equals(c.source().kind()))return research&&tinixEnabled&&"HYBRID_ELIGIBLE_RESEARCH".equals(c.quality())
            &&"UNVERIFIED".equals(c.verification())&&c.issues().isEmpty()&&c.duplicateGroup()!=null&&!c.duplicateGroup().isBlank();
        if("EXTERNAL".equals(c.source().kind())) {
            if(!Set.of("VERIFIED","UNVERIFIED").contains(c.verification())||(!demo&&!"VERIFIED".equals(c.verification())))return false;
            if(c.duplicate()&&(c.duplicateGroup()==null||c.duplicateGroup().isBlank()))return false;
            if("VALID".equals(c.quality()))return c.issues().isEmpty();
            return demo&&"NEEDS_REVIEW".equals(c.quality())&&!c.issues().isEmpty()&&DEMO_REVIEW_ISSUES.containsAll(c.issues());
        }
        return "PROPERTY".equals(c.source().kind())&&"PLATFORM_PUBLISHED".equals(c.quality());
    }
    private static boolean matches(String wanted,String actual) { return wanted==null||wanted.isBlank()||normalize(wanted).equals(normalize(actual)); }
    static String normalize(String value) {
        if(value==null)return "";
        return Normalizer.normalize(value,Normalizer.Form.NFD).replaceAll("\\p{M}+","").toLowerCase(Locale.ROOT)
            .replace('đ','d').strip().replaceAll("\\s+"," ");
    }
}
