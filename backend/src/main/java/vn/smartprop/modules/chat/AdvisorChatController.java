package vn.smartprop.modules.chat;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.CacheControl;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.*;
import vn.smartprop.common.ApiException;

/** Auth is validated by the existing live JWT/session policy. Owner always comes from JWT. */
@RestController
@RequestMapping("/api/v1/users/me/advisor-chats")
public class AdvisorChatController {
    private final AdvisorChatStore store;
    private final String serviceKey;
    public AdvisorChatController(AdvisorChatStore store,
        @Value("${app.chat-checkpoint-key:}") String serviceKey) {
        this.store=store; this.serviceKey=serviceKey;
    }
    public record Commit(@Min(0) long revision, @NotBlank @Size(max=2000) String question,
                         @NotNull JsonNode response, @NotNull JsonNode checkpoint) {}
    private void internal(String key) {
        if(serviceKey.length()<32) throw new ApiException(503,"CHECKPOINT_UNAVAILABLE","Chưa cấu hình lưu lịch sử chat.");
        if(key==null || !MessageDigest.isEqual(serviceKey.getBytes(StandardCharsets.UTF_8), key.getBytes(StandardCharsets.UTF_8)))
            throw new ApiException(403,"FORBIDDEN","Không có quyền ghi checkpoint.");
    }
    private static <T> ResponseEntity<T> body(T value) {
        return ResponseEntity.ok().cacheControl(CacheControl.noStore()).body(value);
    }
    @GetMapping public ResponseEntity<?> recent(@AuthenticationPrincipal Jwt jwt) {
        return body(store.recent(Long.valueOf(jwt.getSubject())));
    }
    @GetMapping("/{id}") public ResponseEntity<?> history(@AuthenticationPrincipal Jwt jwt,@PathVariable String id) {
        return body(store.history(Long.valueOf(jwt.getSubject()),id));
    }
    @DeleteMapping("/{id}") public ResponseEntity<?> delete(@AuthenticationPrincipal Jwt jwt,@PathVariable String id) {
        store.delete(Long.valueOf(jwt.getSubject()),id);return body(Map.of("deleted",true));
    }
    @GetMapping("/{id}/checkpoint") public ResponseEntity<?> checkpoint(@AuthenticationPrincipal Jwt jwt,@PathVariable String id,
        @RequestHeader(value="X-Chat-Checkpoint-Key",required=false) String key) {
        internal(key);return body(store.checkpoint(Long.valueOf(jwt.getSubject()),id));
    }
    @PutMapping("/{id}/checkpoint") public ResponseEntity<?> commit(@AuthenticationPrincipal Jwt jwt,@PathVariable String id,
        @RequestHeader(value="X-Chat-Checkpoint-Key",required=false) String key,@Valid @RequestBody Commit value) {
        internal(key);return body(store.commit(Long.valueOf(jwt.getSubject()),id,value));
    }
}

@Service
class AdvisorChatStore {
    private final JdbcTemplate jdbc; private final ObjectMapper mapper;
    AdvisorChatStore(JdbcTemplate jdbc,ObjectMapper mapper){this.jdbc=jdbc;this.mapper=mapper;}
    private static ApiException missing(){return new ApiException(404,"CHAT_NOT_FOUND","Không tìm thấy hội thoại.");}
    private static void id(String id){if(id==null||!id.matches("[a-f0-9]{32}"))throw missing();}
    private JsonNode json(String value){try{return mapper.readTree(value);}catch(Exception e){throw new IllegalStateException("Invalid saved checkpoint");}}
    private Map<String,Object> owned(long actor,String id){
        id(id);var rows=jdbc.queryForList("SELECT revision,checkpoint FROM advisor_chat_conversations WHERE id=? AND user_id=?",id,actor);
        if(rows.isEmpty())throw missing();return rows.getFirst();
    }
    @Transactional(readOnly=true)
    public List<Map<String,Object>> recent(long actor){
        return jdbc.queryForList("SELECT id,title,revision,updated_at AS updatedAt FROM advisor_chat_conversations WHERE user_id=? ORDER BY updated_at DESC,id LIMIT 10",actor);
    }
    @Transactional(readOnly=true)
    public Map<String,Object> history(long actor,String id){
        var row=owned(actor,id);
        // Bounded viewport; all turns remain durable in DB. Checkpoint resumes full search intent.
        var turns=jdbc.query("SELECT turn_number,question,response FROM advisor_chat_turns WHERE conversation_id=? ORDER BY turn_number DESC LIMIT 12",
            (rs,n)->Map.<String,Object>of("number",rs.getLong(1),"question",rs.getString(2),"response",json(rs.getString(3))),id);
        Collections.reverse(turns);
        return Map.of("id",id,"revision",row.get("revision"),"turns",turns,"trimmed",((Number)row.get("revision")).longValue()>12);
    }
    @Transactional(readOnly=true)
    public Map<String,Object> checkpoint(long actor,String id){
        var row=owned(actor,id);return Map.of("revision",row.get("revision"),"checkpoint",json((String)row.get("checkpoint")));
    }
    @Transactional
    public void delete(long actor,String id){
        id(id);
        int deleted=jdbc.update("DELETE FROM advisor_chat_conversations WHERE id=? AND user_id=?",id,actor);
        if(deleted!=1)throw missing();
    }
    @Transactional
    public Map<String,Object> commit(long actor,String id,AdvisorChatController.Commit value){
        id(id);
        String response=value.response().toString(), checkpoint=value.checkpoint().toString();
        if(!value.response().isObject() || !"SAFE".equals(value.response().path("mode").asText()) ||
            !value.checkpoint().isObject() || response.length()>1500000 || checkpoint.length()>100000)
            throw new ApiException(400,"INVALID_CHECKPOINT","Checkpoint không hợp lệ.");
        long next=value.revision()+1;
        if(value.revision()==0){
            // INSERT IGNORE only resolves duplicate ids; ownership is never changed by an upsert.
            int created=jdbc.update("INSERT IGNORE INTO advisor_chat_conversations(id,user_id,title,revision,checkpoint) VALUES(?,?,?,?,?)",
                id,actor,value.question().strip().substring(0,Math.min(120,value.question().strip().length())),next,checkpoint);
            if(created!=1)throw new ApiException(409,"CHAT_CONFLICT","Hội thoại đã thay đổi. Hãy tải lại.");
        }else{
            owned(actor,id);
            int changed=jdbc.update("UPDATE advisor_chat_conversations SET checkpoint=?,revision=?,updated_at=UTC_TIMESTAMP(6) WHERE id=? AND user_id=? AND revision=?",
                checkpoint,next,id,actor,value.revision());
            if(changed!=1)throw new ApiException(409,"CHAT_CONFLICT","Hội thoại đã thay đổi. Hãy tải lại.");
        }
        jdbc.update("INSERT INTO advisor_chat_turns(conversation_id,turn_number,question,response) VALUES(?,?,?,?)",id,next,value.question(),response);
        return Map.of("id",id,"revision",next);
    }
}
