package vn.smartprop.common;
import java.util.*;
import org.springframework.data.domain.*;
public final class ApiInputs {
    private ApiInputs() {}
    public static ApiException bad(String message) { return new ApiException(400,"VALIDATION_ERROR",message); }
    public static ApiException missing() { return new ApiException(404,"NOT_FOUND","Không tìm thấy tài nguyên"); }
    public static ApiException forbidden() { return new ApiException(403,"FORBIDDEN","Bạn không có quyền thực hiện thao tác này"); }
    public static ApiException conflict(String message) { return new ApiException(409,"CONFLICT",message); }
    public static String uuid(String value) {
        try { String id=UUID.fromString(value).toString(); if(!id.equalsIgnoreCase(value)) throw bad("UUID không hợp lệ"); return id; }
        catch(IllegalArgumentException | NullPointerException e) { throw bad("UUID không hợp lệ"); }
    }
    public static Pageable page(int page,int size,Sort sort) {
        if(page<0 || page>10000 || size<1 || size>100) throw bad("page phải từ 0–10000; size từ 1–100");
        return PageRequest.of(page,size,sort);
    }
    public static Pageable newest(int page,int size) { return page(page,size,Sort.by(Sort.Order.desc("createdAt"),Sort.Order.desc("id"))); }
    public static String like(String value) { return "%"+value.replace("\\","\\\\").replace("%","\\%").replace("_","\\_")+"%"; }
}