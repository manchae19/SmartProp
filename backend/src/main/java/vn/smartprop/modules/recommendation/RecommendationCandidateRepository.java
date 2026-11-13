package vn.smartprop.modules.recommendation;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;
import java.util.*;
import static vn.smartprop.modules.recommendation.RecommendationDtos.*;

/** Read-only projection. No persistence entity, import or schema mutation. */
@Repository
public class RecommendationCandidateRepository {
    static final int CAP=10001;
    private final JdbcTemplate jdbc;
    private final ObjectMapper mapper;
    public RecommendationCandidateRepository(JdbcTemplate jdbc,ObjectMapper mapper) { this.jdbc=jdbc;this.mapper=mapper; }
    public List<Candidate> find(Request request,boolean demo) {
        var result=new ArrayList<Candidate>();
        var minimum=request.minAreaSqm()==null?java.math.BigDecimal.ZERO:request.minAreaSqm();
        var maximum=request.maxAreaSqm()==null?new java.math.BigDecimal("1000000"):request.maxAreaSqm();
        String minOperator=request.minAreaExclusive()?">":">=";
        String maxOperator=request.maxAreaExclusive()?"<":"<=";
        String propertyQuery = "SELECT id,title,property_type,price,area_sqm,district,ward FROM properties "
            + "WHERE status='PUBLISHED' AND deleted_at IS NULL AND (expires_at IS NULL OR expires_at>UTC_TIMESTAMP(6)) "
            + "AND transaction_type='SALE' AND currency='VND' AND price_unit='TOTAL' "
            + "AND price>0 AND price<=? AND area_sqm>0 AND area_sqm" + minOperator + "? "
            + "AND area_sqm" + maxOperator + "? ORDER BY id LIMIT 10001";
        result.addAll(jdbc.query(propertyQuery,(rs,n)->new Candidate("property:"+rs.getString("id"),rs.getString("title"),
                PropertyType.valueOf(rs.getString("property_type")),rs.getBigDecimal("price"),rs.getBigDecimal("area_sqm"),
                rs.getString("district"),rs.getString("ward"),new Source("PROPERTY","SmartProp",rs.getString("id"),"/api/v1/properties/"+rs.getString("id")),
                "PLATFORM_PUBLISHED","PLATFORM_PUBLISHED",null,false,false,List.of(),false),request.budgetVnd(),minimum,maximum));
        String policy=demo?"l.quality_status IN ('VALID','NEEDS_REVIEW') AND l.verification_status IN ('VERIFIED','UNVERIFIED')"
            :"l.quality_status='VALID' AND l.verification_status='VERIFIED'";
        String externalQuery = "SELECT l.* FROM external_listings l WHERE l.is_protected_holdout=0 "
            + "AND l.transaction_type='SALE' AND l.price>0 AND l.price<=? AND l.area_sqm>0 "
            + "AND l.area_sqm" + minOperator + "? AND l.area_sqm" + maxOperator + "? "
            + "AND (l.duplicate_group IS NULL OR NOT EXISTS "
            + "(SELECT 1 FROM external_listings h WHERE h.duplicate_group=l.duplicate_group AND h.is_protected_holdout=1)) "
            + "AND " + policy + " ORDER BY l.record_key LIMIT 10001";
        result.addAll(jdbc.query(externalQuery,(rs,n)->new Candidate("external:"+rs.getLong("id"),rs.getString("title"),
                category(rs.getString("category")),rs.getBigDecimal("price"),rs.getBigDecimal("area_sqm"),rs.getString("district"),null,
                new Source("EXTERNAL",rs.getString("source"),rs.getString("record_key"),rs.getString("detail_url")),
                rs.getString("quality_status"),rs.getString("verification_status"),rs.getString("duplicate_group"),
                rs.getBoolean("is_duplicate"),rs.getBoolean("is_protected_holdout"),issues(rs.getString("quality_issues")),false),request.budgetVnd(),minimum,maximum));
        return result;
    }
    private List<String> issues(String json) {
        try {
            var node=mapper.readTree(json);
            if(!node.isArray())return List.of("INVALID_QUALITY_METADATA");
            var values=new ArrayList<String>();
            for(var item:node) { if(!item.isTextual())return List.of("INVALID_QUALITY_METADATA");values.add(item.asText()); }
            return List.copyOf(values);
        } catch(Exception e) { return List.of("INVALID_QUALITY_METADATA"); }
    }
    private PropertyType category(String value) {
        return switch(value) { case "Nhà ở"->PropertyType.HOUSE;case "Căn hộ chung cư"->PropertyType.APARTMENT;
            case "Đất nền"->PropertyType.LAND;default->null; };
    }
}
