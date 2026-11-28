package vn.smartprop.modules.chat;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.*;
import org.junit.jupiter.api.*;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
import static org.mockito.ArgumentMatchers.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.oauth2.jwt.Jwt;
import vn.smartprop.common.ApiException;

class AdvisorChatTest {
    final JdbcTemplate jdbc=mock(JdbcTemplate.class);
    final ObjectMapper mapper=new ObjectMapper();
    final AdvisorChatStore store=new AdvisorChatStore(jdbc,mapper);
    final String id="a".repeat(32);
    AdvisorChatController.Commit value(long revision) throws Exception {
        return new AdvisorChatController.Commit(revision,"Question",mapper.readTree("{\"mode\":\"SAFE\",\"answer\":\"hello\"}"),mapper.readTree("{}"));
    }
    @Test void historyAndCheckpointRequireOwnership() {
        when(jdbc.queryForList(anyString(),eq(id),eq(2L))).thenReturn(List.of());
        assertEquals(404,assertThrows(ApiException.class,()->store.history(2,id)).status);
        assertEquals(404,assertThrows(ApiException.class,()->store.checkpoint(2,id)).status);
        verify(jdbc,times(2)).queryForList(contains("c.id=? AND c.user_id=?"),eq(id),eq(2L));
        verifyNoMoreInteractions(jdbc);
    }
    @Test void activityListIsBoundedAndOwnerFiltered() {
        store.recent(4);
        verify(jdbc).queryForList(contains("WHERE c.user_id=?"),eq(4L));
        var sql=org.mockito.ArgumentCaptor.forClass(String.class);
        verify(jdbc).queryForList(sql.capture(),eq(4L));
        assertTrue(sql.getValue().contains("ORDER BY c.updated_at DESC,c.id LIMIT 10"));
        // Demo land conversations stay invisible to account history at the persistence boundary.
        assertTrue(sql.getValue().contains("JSON_SEARCH")&&sql.getValue().contains("LAND_DATA"));
    }
    @Test void staleRevisionCannotAppendTurn() throws Exception {
        when(jdbc.queryForList(anyString(),eq(id),eq(1L))).thenReturn(List.of(Map.of("revision",2L,"checkpoint","{}")));
        when(jdbc.update(anyString(),any(Object[].class))).thenReturn(0);
        assertEquals(409,assertThrows(ApiException.class,()->store.commit(1,id,value(1))).status);
        verify(jdbc,never()).update(startsWith("INSERT INTO advisor_chat_turns"),any(Object[].class));
    }
    @Test void foreignOwnerCannotUpdateEvenWithServiceKey() throws Exception {
        when(jdbc.queryForList(anyString(),eq(id),eq(2L))).thenReturn(List.of());
        assertEquals(404,assertThrows(ApiException.class,()->store.commit(2,id,value(1))).status);
        verify(jdbc,never()).update(anyString(),any(Object[].class));
    }
    @Test void newIdCollisionCannotOverwriteAnotherOwner() throws Exception {
        when(jdbc.update(anyString(),any(Object[].class))).thenReturn(0);
        assertEquals(409,assertThrows(ApiException.class,()->store.commit(2,id,value(0))).status);
        verify(jdbc,never()).update(startsWith("UPDATE"),any(Object[].class));
    }
    @Test void checkpointWritesRequireServerKeyBeforeAnyDbAccess() throws Exception {
        var controller=new AdvisorChatController(store,"k".repeat(32));
        assertEquals(403,assertThrows(ApiException.class,()->controller.commit(null,id,null,value(0))).status);
        assertEquals(403,assertThrows(ApiException.class,()->controller.checkpoint(null,id,"wrong")).status);
        verifyNoInteractions(jdbc);
    }
    @Test void deleteRequiresOwnerAndDoesNotDeleteOtherAccounts(){
        when(jdbc.update(anyString(),eq(id),eq(1L))).thenReturn(1);
        store.delete(1,id);
        verify(jdbc).update(contains("WHERE id=? AND user_id=?"),eq(id),eq(1L));
        assertEquals(404,assertThrows(ApiException.class,()->store.delete(2,id)).status);
    }
    @Test void missingConfigurationFailsClosed() throws Exception {
        var controller=new AdvisorChatController(store,"");
        assertEquals(503,assertThrows(ApiException.class,()->controller.commit(null,id,null,value(0))).status);
        verifyNoInteractions(jdbc);
    }
}
