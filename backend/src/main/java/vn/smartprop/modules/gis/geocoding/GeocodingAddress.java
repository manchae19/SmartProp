package vn.smartprop.modules.gis.geocoding;

import java.text.Normalizer;
import java.util.*;
import vn.smartprop.common.ApiInputs;
import static vn.smartprop.modules.gis.geocoding.GeocodingDtos.*;

/** Compare spelling/prefix variants, never rewrite administrative boundaries or the original address. */
final class GeocodingAddress {
    private GeocodingAddress() {}
    static String key(String value) {
        if(value==null)return "";
        String text=Normalizer.normalize(value,Normalizer.Form.NFD).replaceAll("\\p{M}+","")
            .toLowerCase(Locale.ROOT).replace('đ','d').replace('.',' ').strip().replaceAll("\\s+"," ");
        return text.replaceFirst("^(?:thanh pho|thi xa|tp|tx|quan|q|huyen|phuong|p|xa|city|province|district|ward)\\s+","");
    }
    static String normalize(Search request) {
        request=effective(request);
        var parts=new LinkedHashMap<String,String>();
        String[] values={request.address(),request.ward(),request.district(),request.city(),"Việt Nam"};
        String[] kinds={"","ward","district","city","country"};
        for(int index=0;index<values.length;index++) {
            String value=values[index];
            if(value==null)continue;
            for(String raw:Normalizer.normalize(value,Normalizer.Form.NFC).split(",")) {
                if(raw.chars().anyMatch(c->Character.isISOControl(c)&&!Character.isWhitespace(c)))throw ApiInputs.bad("Địa chỉ tìm kiếm chứa ký tự không hợp lệ.");
                String text=raw.strip().replaceAll("\\s+"," ");
                if(!text.isBlank())parts.putIfAbsent(identity(text,kinds[index],request),text);
            }
        }
        String query=String.join(", ",parts.values());
        if(request.address()==null||request.address().isBlank()||request.city()==null||request.city().isBlank()||query.length()>600)
            throw ApiInputs.bad("Nhập địa chỉ và thành phố; chuỗi tìm kiếm tối đa 600 ký tự.");
        return query;
    }
    private static String identity(String text,String assumed,Search request) {
        String plain=Normalizer.normalize(text,Normalizer.Form.NFD).replaceAll("\\p{M}+","").toLowerCase(Locale.ROOT).replace('đ','d').replace('.',' ').strip().replaceAll("\\s+"," ");
        String kind=plain.matches("^(?:phuong|p|xa|ward)\\s+.*")?"ward":plain.matches("^(?:quan|q|huyen|district)\\s+.*")?"district":plain.matches("^(?:thanh pho|tp|city|province)\\s+.*")?"city":assumed;
        String canonical=key(text);
        if(Set.of("viet nam","vietnam","vn").contains(canonical)){kind="country";canonical="viet nam";}
        if(kind.isBlank()) {
            var matching=new ArrayList<String>();
            if(!key(request.ward()).isBlank()&&canonical.equals(key(request.ward())))matching.add("ward");
            if(!key(request.district()).isBlank()&&canonical.equals(key(request.district())))matching.add("district");
            if(!key(request.city()).isBlank()&&canonical.equals(key(request.city())))matching.add("city");
            if(matching.size()==1)kind=matching.getFirst();
        }
        return kind+":"+canonical;
    }
    static boolean matches(List<String> values,String expected) {
        String wanted=key(expected);return values!=null&&values.stream().anyMatch(v->!key(v).isBlank()&&key(v).equals(wanted));
    }
    private static List<String> explicit(String address,String prefix) {
        var values=new LinkedHashMap<String,String>();
        for(String part:String.valueOf(address).split(",")){
            String text=part.strip();var matcher=java.util.regex.Pattern.compile("^(?:"+prefix+")\\s+(.+)$",java.util.regex.Pattern.CASE_INSENSITIVE|java.util.regex.Pattern.UNICODE_CASE).matcher(text);
            if(matcher.matches())values.putIfAbsent(key(matcher.group(1)),matcher.group(1));
        }
        return List.copyOf(values.values());
    }
    static Search effective(Search request) {
        var wards=explicit(request.address(),"phường|p\\.?|xã|ward");
        var districts=explicit(request.address(),"quận|q\\.?|huyện|district");
        String ward=wards.isEmpty()?(districts.isEmpty()?request.ward():null):wards.size()==1?wards.getFirst():null;
        String district=districts.isEmpty()?(wards.isEmpty()?request.district():null):districts.size()==1?districts.getFirst():null;
        return new Search(request.address(),request.city(),district,ward,request.shareAddress(),request.districtOnly());
    }
    static Optional<Candidate> review(Candidate candidate,Search request) {
        request=effective(request);
        Context source=candidate.context();
        if(source==null)return Optional.of(candidate.reviewed(new Context("",List.of(),List.of(),List.of(),"unknown",Precision.UNKNOWN,false,"Nguồn chưa cung cấp đủ thông tin địa bàn; cần đặt lại ghim thủ công.","")));
        if(!source.countryCode().isBlank()&&!source.countryCode().equalsIgnoreCase("vn"))return Optional.empty();
        if(!source.localities().isEmpty()&&!matches(source.localities(),request.city()))return Optional.empty();
        boolean locality=source.countryCode().equalsIgnoreCase("vn")&&matches(source.localities(),request.city());
        String warning=locality?"":"Chưa đối chiếu được quốc gia/thành phố; không xác nhận trực tiếp gợi ý này.";
        var districts=request.district()!=null&&!request.district().isBlank()?List.of(request.district()):explicit(request.address(),"quận|q\\.?|huyện");
        var wards=request.ward()!=null&&!request.ward().isBlank()?List.of(request.ward()):explicit(request.address(),"phường|p\\.?|xã");
        if(locality&&(districts.size()>1||wards.size()>1)){locality=false;warning="Địa chỉ nhắc nhiều địa bàn; cần làm rõ vị trí trước khi xác nhận.";}
        if(locality&&districts.size()==1&&!source.districts().isEmpty()&&!matches(source.districts(),districts.getFirst())){
            locality=false;warning="Tên khu vực nguồn trả về khác khu vực đã nhập; kiểm tra tên cũ/mới và đặt lại ghim nếu cần.";
        }
        if(locality&&wards.size()==1&&!source.wards().isEmpty()&&!matches(source.wards(),wards.getFirst())){
            locality=false;warning="Phường/xã nguồn trả về khác địa chỉ đã nhập; chưa xác minh địa giới cũ/mới.";
        }
        return Optional.of(candidate.reviewed(new Context(source.countryCode(),source.localities(),source.districts(),source.wards(),source.resultType(),source.precision(),locality,warning,source.street())));
    }
}
