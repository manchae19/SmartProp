package vn.smartprop.modules.avatar;

import java.sql.Timestamp;
import java.time.*;
import java.util.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.http.*;
import org.springframework.web.multipart.MultipartFile;
import vn.smartprop.modules.auth.AccountAccess;
import vn.smartprop.common.*;
import vn.smartprop.config.*;
import vn.smartprop.modules.user.*;

@Service
public class AvatarService {
    public record View(boolean enabled,boolean available,String url,String revision,int maxBytes) {}
    private record Stored(String key,String revision) {}
    private final JdbcTemplate jdbc;private final AccountAccess access;private final AvatarFiles files;private final boolean enabled;private final UserRepository users;
    public AvatarService(JdbcTemplate jdbc,AccountAccess access,AvatarFiles files,UserRepository users,@Value("${app.profile.avatar-enabled:false}") boolean enabled){this.jdbc=jdbc;this.access=access;this.files=files;this.users=users;this.enabled=enabled;}
    private void ready(){if(!enabled)throw new ApiException(503,"FEATURE_DISABLED","Ảnh đại diện chưa được bật.");}
    private Optional<Stored> stored(Long actor){return jdbc.query("SELECT storage_key,revision FROM user_avatars WHERE user_id=?",(r,n)->new Stored(r.getString(1),r.getString(2)),actor).stream().findFirst();}
    private View view(Stored value){return new View(enabled,value!=null,value==null?null:"/api/v1/users/me/avatar/content?v="+value.revision(),value==null?null:value.revision(),AvatarFiles.MAX_BYTES);}
    @Transactional(readOnly=true) public View get(Long actor){access.active(actor);return !enabled?view(null):view(stored(actor).orElse(null));}
    @Transactional public View upload(Long actor,MultipartFile input){
        ready();lock(actor);var validated=files.validate(input);var old=stored(actor);var created=files.store(validated);String revision=UUID.randomUUID().toString();
        jdbc.update("INSERT INTO user_avatars(user_id,revision,storage_key,mime_type,sha256,width,height,updated_at) VALUES(?,?,?,?,?,?,?,?) ON DUPLICATE KEY UPDATE revision=VALUES(revision),storage_key=VALUES(storage_key),mime_type=VALUES(mime_type),sha256=VALUES(sha256),width=VALUES(width),height=VALUES(height),updated_at=VALUES(updated_at)",actor,revision,created.key(),validated.mimeType(),validated.sha256(),validated.width(),validated.height(),Timestamp.from(Instant.now()));
        old.ifPresent(value->files.removeAfterCommit(value.key()));return view(new Stored(created.key(),revision));
    }
    private void lock(Long actor){var user=users.lockById(actor).orElseThrow(ApiInputs::forbidden);if(user.status!=User.Status.ACTIVE||user.deletedAt!=null)throw ApiInputs.forbidden();}
    @Transactional public void remove(Long actor){ready();lock(actor);var old=stored(actor);jdbc.update("DELETE FROM user_avatars WHERE user_id=?",actor);old.ifPresent(value->files.removeAfterCommit(value.key()));}
    @Transactional(readOnly=true) public ResponseEntity<byte[]> content(Long actor){ready();access.active(actor);var value=stored(actor).orElseThrow(ApiInputs::missing);byte[] bytes=files.read(value.key());return ResponseEntity.ok().contentType(MediaType.IMAGE_PNG).contentLength(bytes.length).header("Cache-Control","private, no-store").header("X-Content-Type-Options","nosniff").header("Content-Disposition","inline; filename=\"avatar.png\"").body(bytes);}
}
