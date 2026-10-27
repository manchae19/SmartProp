package vn.smartprop.collection;

import java.math.*;
import java.sql.Timestamp;
import java.time.Instant;
import java.util.*;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import vn.smartprop.auth.AccountAccess;
import vn.smartprop.common.ApiInputs;
import vn.smartprop.property.Property;

/** Read-only aggregates over existing tables. No tracking, forecasts, or private contact fields. */
@Service
@Transactional(readOnly=true)
public class CollectionSummaryService {
    private final NamedParameterJdbcTemplate jdbc;
    private final AccountAccess access;
    public CollectionSummaryService(NamedParameterJdbcTemplate jdbc,AccountAccess access){this.jdbc=jdbc;this.access=access;}
    private static final String VISIBLE="p.deleted_at IS NULL AND p.status='PUBLISHED' AND (p.expires_at IS NULL OR p.expires_at>:now)";
    private static final String NUMBERS="COUNT(*) AS count, SUM(p.price) AS price_sum, SUM(p.area_sqm) AS area_sum, MIN(p.price) AS min_price, MAX(p.price) AS max_price";
    public record Amounts(long count,BigDecimal totalAskingPrice,BigDecimal averageAskingPrice,BigDecimal minimumAskingPrice,BigDecimal maximumAskingPrice,BigDecimal weightedAskingPricePerSqm) {}
    public record Group(String key,Amounts amounts) {}
    public record PriceGroup(String transactionType,String currency,String priceUnit,Amounts amounts) {}
    public record Market(Instant asOf,String source,boolean historyAvailable,Property.Transaction transactionType,String currency,Property.PriceUnit priceUnit,Amounts overall,List<Group> byPropertyType,List<Group> byDistrict,boolean districtsTruncated) {}
    public record Owned(Instant asOf,long totalListings,Map<String,Long> byStatus,long savedRecords,long recordedViews,boolean viewRecordingEnabled) {}
    public record Favorites(Instant asOf,long totalVisible,Map<String,Long> byPropertyType,Instant firstSavedAt,Instant lastSavedAt,List<PriceGroup> priceGroups) {}
    public record Reports(Instant asOf,long totalReports,Map<String,Long> byStatus) {}
    private static BigDecimal decimal(Object value){return value==null?null:new BigDecimal(value.toString());}
    private static long number(Object value){return value==null?0:((Number)value).longValue();}
    private static Instant instant(Object value){if(value==null)return null;if(value instanceof Timestamp timestamp)return timestamp.toInstant();if(value instanceof java.time.LocalDateTime date)return date.toInstant(java.time.ZoneOffset.UTC);if(value instanceof Instant time)return time;throw new IllegalStateException("Unsupported database timestamp type");}
    public static Amounts amounts(Map<String,Object> row){
        long count=number(row.get("count"));BigDecimal sum=decimal(row.get("price_sum")),area=decimal(row.get("area_sum"));
        return new Amounts(count,sum,count==0?null:sum.divide(BigDecimal.valueOf(count),2,RoundingMode.HALF_UP),decimal(row.get("min_price")),decimal(row.get("max_price")),area==null||area.signum()==0||sum==null?null:sum.divide(area,2,RoundingMode.HALF_UP));
    }
    private static String text(String input){if(input!=null&&input.length()>100)throw ApiInputs.bad("Bộ lọc chuỗi tối đa 100 ký tự");return input==null||input.isBlank()?null:input.strip();}
    public Market market(String city,String district,Property.Type type,Property.Transaction transaction,Property.PriceUnit unit){
        city=text(city);district=text(district);
        if(transaction==null||unit==null||transaction==Property.Transaction.SALE&&unit!=Property.PriceUnit.TOTAL)throw ApiInputs.bad("transactionType/priceUnit không hợp lệ");
        Instant now=Instant.now();Map<String,Object> params=new HashMap<>();params.put("now",Timestamp.from(now));params.put("transaction",transaction.name());params.put("unit",unit.name());
        String filter=VISIBLE+" AND p.transaction_type=:transaction AND p.price_unit=:unit AND p.currency='VND'";
        if(city!=null){params.put("city",city);filter+=" AND p.city=:city";}if(district!=null){params.put("district",district);filter+=" AND p.district=:district";}if(type!=null){params.put("type",type.name());filter+=" AND p.property_type=:type";}
        var overall=amounts(jdbc.queryForMap("SELECT "+NUMBERS+" FROM properties p WHERE "+filter,params));
        var types=jdbc.queryForList("SELECT p.property_type AS group_key,"+NUMBERS+" FROM properties p WHERE "+filter+" GROUP BY p.property_type ORDER BY p.property_type",params).stream().map(row->new Group((String)row.get("group_key"),amounts(row))).toList();
        var districts=jdbc.queryForList("SELECT p.district AS group_key,"+NUMBERS+" FROM properties p WHERE "+filter+" GROUP BY p.district ORDER BY p.district LIMIT 201",params);
        var groups=districts.stream().limit(200).map(row->new Group((String)row.get("group_key"),amounts(row))).toList();
        return new Market(now,"CURRENT_PUBLISHED_ASKING_PRICES",false,transaction,"VND",unit,overall,types,groups,districts.size()>200);
    }
    public Owned owned(Long actor){
        access.active(actor);Instant now=Instant.now();Map<String,Object> params=Map.of("actor",actor,"now",Timestamp.from(now));
        Map<String,Long> counts=new LinkedHashMap<>();for(var status:Property.Status.values())counts.put(status.name(),0L);
        String status="CASE WHEN p.status='PUBLISHED' AND p.expires_at<=:now THEN 'EXPIRED' ELSE p.status END";
        for(var row:jdbc.queryForList("SELECT "+status+" AS state,COUNT(*) AS count FROM properties p WHERE p.owner_id=:actor AND p.deleted_at IS NULL GROUP BY "+status,params))counts.put((String)row.get("state"),number(row.get("count")));
        long saved=jdbc.queryForObject("SELECT COUNT(*) FROM saved_properties s JOIN properties p ON p.id=s.property_id WHERE p.owner_id=:actor AND p.deleted_at IS NULL",params,Long.class);
        long views=jdbc.queryForObject("SELECT COALESCE(SUM(s.view_count),0) FROM property_daily_stats s JOIN properties p ON p.id=s.property_id WHERE p.owner_id=:actor AND p.deleted_at IS NULL",params,Long.class);
        return new Owned(now,counts.values().stream().mapToLong(Long::longValue).sum(),Map.copyOf(counts),saved,views,false);
    }
    public Favorites favorites(Long actor){
        access.active(actor);Instant now=Instant.now();var params=Map.<String,Object>of("actor",actor,"now",Timestamp.from(now));
        String from=" FROM saved_properties s JOIN properties p ON p.id=s.property_id WHERE s.user_id=:actor AND "+VISIBLE;
        var overview=jdbc.queryForMap("SELECT COUNT(*) AS count,MIN(s.saved_at) AS first_saved,MAX(s.saved_at) AS last_saved"+from,params);
        Map<String,Long> types=new LinkedHashMap<>();for(var row:jdbc.queryForList("SELECT p.property_type,COUNT(*) AS count"+from+" GROUP BY p.property_type ORDER BY p.property_type",params))types.put((String)row.get("property_type"),number(row.get("count")));
        var prices=jdbc.queryForList("SELECT p.transaction_type,p.currency,p.price_unit,"+NUMBERS+from+" GROUP BY p.transaction_type,p.currency,p.price_unit ORDER BY p.transaction_type,p.currency,p.price_unit",params).stream().map(row->new PriceGroup((String)row.get("transaction_type"),(String)row.get("currency"),(String)row.get("price_unit"),amounts(row))).toList();
        return new Favorites(now,number(overview.get("count")),Map.copyOf(types),instant(overview.get("first_saved")),instant(overview.get("last_saved")),prices);
    }
    public Reports reports(Long actor){
        access.active(actor);Map<String,Long> counts=new LinkedHashMap<>();for(var status:vn.smartprop.report.Report.Status.values())counts.put(status.name(),0L);
        for(var row:jdbc.queryForList("SELECT status,COUNT(*) AS count FROM reports WHERE reporter_id=:actor GROUP BY status",Map.of("actor",actor)))counts.put((String)row.get("status"),number(row.get("count")));
        return new Reports(Instant.now(),counts.values().stream().mapToLong(Long::longValue).sum(),Map.copyOf(counts));
    }
}
