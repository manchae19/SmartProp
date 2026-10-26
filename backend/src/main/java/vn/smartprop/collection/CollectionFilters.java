package vn.smartprop.collection;

import java.util.*;
import jakarta.persistence.criteria.*;
import org.springframework.data.domain.Sort;
import vn.smartprop.common.ApiInputs;

/** Shared validation for optional collection filters; never accepts a client user ID. */
public final class CollectionFilters {
    private CollectionFilters() {}
    public static String keyword(String value) {
        if(value!=null && value.length()>100) throw ApiInputs.bad("keyword tối đa 100 ký tự");
        return value==null?"":value.strip().toLowerCase(Locale.ROOT);
    }
    @SafeVarargs
    public static Predicate text(CriteriaBuilder cb,String keyword,Expression<String>... fields) {
        if(keyword.isEmpty()) return cb.conjunction();
        var term=ApiInputs.like(keyword);
        return cb.or(Arrays.stream(fields).map(f->cb.like(cb.lower(f),term,'\\')).toArray(Predicate[]::new));
    }
    public static Sort sort(String value,boolean prices) {
        value=value==null||value.isBlank()?"newest":value;
        Sort sort=switch(value) {
            case "newest" -> Sort.by(Sort.Order.desc("createdAt"));
            case "oldest" -> Sort.by("createdAt");
            case "priceAsc" -> {if(!prices)throw ApiInputs.bad("sort không được hỗ trợ");yield Sort.by("price");}
            case "priceDesc" -> {if(!prices)throw ApiInputs.bad("sort không được hỗ trợ");yield Sort.by(Sort.Order.desc("price"));}
            case "areaDesc" -> {if(!prices)throw ApiInputs.bad("sort không được hỗ trợ");yield Sort.by(Sort.Order.desc("areaSqm"));}
            default -> throw ApiInputs.bad("sort không được hỗ trợ");
        };
        return sort.and(Sort.by(Sort.Order.desc("id")));
    }
}
