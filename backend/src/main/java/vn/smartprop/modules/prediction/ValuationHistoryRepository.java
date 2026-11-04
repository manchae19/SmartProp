package vn.smartprop.modules.prediction;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.*;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.util.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;
import vn.smartprop.common.PageResponse;

@Repository
public class ValuationHistoryRepository {
    public record Entry(String id, Instant createdAt, JsonNode input, JsonNode prediction) {}
    public record Stored(Entry entry, String fingerprint) {}
    private static final String COLUMNS = "id,created_at,input_snapshot,prediction_snapshot,request_sha256";
    private final JdbcTemplate jdbc;
    private final ObjectMapper json;

    public ValuationHistoryRepository(JdbcTemplate jdbc, ObjectMapper json) { this.jdbc=jdbc; this.json=json; }

    private Stored row(java.sql.ResultSet row, int index) throws java.sql.SQLException {
        try {
            return new Stored(new Entry(row.getString("id"), row.getObject("created_at",LocalDateTime.class).toInstant(ZoneOffset.UTC),
                json.readTree(row.getString("input_snapshot")), json.readTree(row.getString("prediction_snapshot"))),
                row.getString("request_sha256"));
        } catch (JsonProcessingException error) { throw new java.sql.SQLException("Invalid history snapshot", error); }
    }

    public Optional<Stored> byKey(Long user, String key) {
        return jdbc.query("SELECT "+COLUMNS+" FROM valuation_history WHERE user_id=? AND request_key=?", this::row, user, key).stream().findFirst();
    }
    public Optional<Stored> byId(Long user, String id) {
        return jdbc.query("SELECT "+COLUMNS+" FROM valuation_history WHERE user_id=? AND id=?", this::row, user, id).stream().findFirst();
    }
    public void insert(Long user, String key, String fingerprint, JsonNode input, JsonNode prediction) {
        jdbc.update("INSERT INTO valuation_history (id,user_id,request_key,request_sha256,input_snapshot,prediction_snapshot,created_at) " +
            "VALUES (?,?,?,?,CAST(? AS JSON),CAST(? AS JSON),?) ON DUPLICATE KEY UPDATE id=id",
            UUID.randomUUID().toString(), user, key, fingerprint, input.toString(), prediction.toString(), LocalDateTime.now(ZoneOffset.UTC));
    }
    public PageResponse<Entry> list(Long user, int page, int size) {
        Long total = jdbc.queryForObject("SELECT COUNT(*) FROM valuation_history WHERE user_id=?", Long.class, user);
        List<Entry> items = jdbc.query("SELECT "+COLUMNS+" FROM valuation_history WHERE user_id=? ORDER BY created_at DESC,id DESC LIMIT ? OFFSET ?",
            this::row, user, size, (long) page*size).stream().map(Stored::entry).toList();
        long count = total == null ? 0 : total;
        return new PageResponse<>(items,page,size,count,(int)((count+size-1)/size));
    }
    public boolean delete(Long user, String id) {
        return jdbc.update("DELETE FROM valuation_history WHERE user_id=? AND id=?", user,id)==1;
    }
}
