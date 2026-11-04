package vn.smartprop.modules.broker;

import java.sql.*;
import java.time.Instant;
import java.util.*;
import org.springframework.jdbc.core.*;
import org.springframework.stereotype.Repository;
import vn.smartprop.common.*;
import static vn.smartprop.modules.broker.BrokerApplicationDtos.*;

/** JDBC mapping keeps the disabled feature independent of V13 at application startup. */
@Repository
public class BrokerApplicationRepository {
    private final JdbcTemplate jdbc;
    public BrokerApplicationRepository(JdbcTemplate jdbc) { this.jdbc=jdbc; }
    private static Instant instant(ResultSet r,String name) throws SQLException { var value=r.getTimestamp(name);return value==null?null:value.toInstant(); }
    private final RowMapper<View> mapper=(r,n)->new View(r.getString("id"),r.getLong("user_id"),
        ApplicantType.valueOf(r.getString("applicant_type")),r.getString("display_name"),r.getString("contact_phone"),
        r.getString("operating_area"),r.getString("request_message"),r.getBoolean("responsibility_accepted"),instant(r,"consented_at"),
        Status.valueOf(r.getString("status")),r.getInt("content_version"),(Long)r.getObject("reviewed_by"),
        r.getString("review_action")==null?null:Action.valueOf(r.getString("review_action")),r.getString("review_reason"),
        instant(r,"reviewed_at"),instant(r,"created_at"),instant(r,"updated_at"));
    public Optional<View> byUser(Long user) { return jdbc.query("SELECT * FROM broker_applications WHERE user_id=?",mapper,user).stream().findFirst(); }
    public Optional<View> byUserForUpdate(Long user) { return jdbc.query("SELECT * FROM broker_applications WHERE user_id=? FOR UPDATE",mapper,user).stream().findFirst(); }
    public View byId(String id) { return jdbc.query("SELECT * FROM broker_applications WHERE id=?",mapper,id).stream().findFirst().orElseThrow(ApiInputs::missing); }
    public PageResponse<View> queue(Status status,int page,int size) {
        ApiInputs.newest(page,size);
        String where=status==null?"":" WHERE status=?";
        Object[] countArgs=status==null?new Object[]{}:new Object[]{status.name()};
        Long count=jdbc.queryForObject("SELECT COUNT(*) FROM broker_applications"+where,Long.class,countArgs);
        Object[] args=status==null?new Object[]{size,(long)page*size}:new Object[]{status.name(),size,(long)page*size};
        var items=jdbc.query("SELECT * FROM broker_applications"+where+" ORDER BY updated_at DESC,id DESC LIMIT ? OFFSET ?",mapper,args);
        long total=count==null?0:count;return new PageResponse<>(items,page,size,total,(int)((total+size-1)/size));
    }
    public View submit(Long user,Submit input,View previous) {
        Instant now=Instant.now();String id=previous==null?UUID.randomUUID().toString():previous.id();
        if(previous==null)jdbc.update("INSERT INTO broker_applications(id,user_id,applicant_type,display_name,contact_phone,operating_area,request_message,responsibility_accepted,consented_at,status,content_version,created_at,updated_at) VALUES(?,?,?,?,?,?,?,TRUE,?,'PENDING',1,?,?)",
            id,user,input.applicantType().name(),input.displayName().strip(),input.contactPhone().strip(),input.operatingArea().strip(),input.requestMessage().strip(),Timestamp.from(now),Timestamp.from(now),Timestamp.from(now));
        else if(jdbc.update("UPDATE broker_applications SET applicant_type=?,display_name=?,contact_phone=?,operating_area=?,request_message=?,responsibility_accepted=TRUE,consented_at=?,status='PENDING',content_version=content_version+1,reviewed_by=NULL,review_action=NULL,review_reason=NULL,reviewed_at=NULL,updated_at=? WHERE id=? AND content_version=?",
            input.applicantType().name(),input.displayName().strip(),input.contactPhone().strip(),input.operatingArea().strip(),input.requestMessage().strip(),Timestamp.from(now),Timestamp.from(now),id,previous.contentVersion())!=1)throw ApiInputs.conflict("Hồ sơ đã thay đổi; hãy tải lại");
        return byId(id);
    }
    public View review(View previous,Long actor,Review input,Status after) {
        if(jdbc.update("UPDATE broker_applications SET status=?,content_version=content_version+1,reviewed_by=?,review_action=?,review_reason=?,reviewed_at=UTC_TIMESTAMP(6),updated_at=UTC_TIMESTAMP(6) WHERE id=? AND content_version=?",
            after.name(),actor,input.action().name(),input.reason().strip(),previous.id(),previous.contentVersion())!=1)throw ApiInputs.conflict("Hồ sơ đã thay đổi; hãy tải lại");
        return byId(previous.id());
    }
}
