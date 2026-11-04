package vn.smartprop.modules.user;
import com.fasterxml.jackson.databind.node.*;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import vn.smartprop.common.*;
@Service
public class PreferencesService {
    public record Preferences(boolean matchingListings,boolean brokerMessages,boolean statusUpdates) {}
    public record Patch(Boolean matchingListings,Boolean brokerMessages,Boolean statusUpdates) {}
    private final UserRepository users;
    public PreferencesService(UserRepository users) { this.users=users; }
    private User active(Long id,boolean lock) {
        User u=(lock?users.lockById(id):users.findById(id)).orElseThrow(ApiInputs::missing);
        if(u.deletedAt!=null || u.status!=User.Status.ACTIVE) throw new ApiException(401,"UNAUTHENTICATED","Tài khoản không hoạt động");
        return u;
    }
    private Preferences view(User u) {
        var n=u.notificationPreferences;
        return new Preferences(n!=null && n.path("matchingListings").asBoolean(false),n!=null && n.path("brokerMessages").asBoolean(false),n!=null && n.path("statusUpdates").asBoolean(false));
    }
    @Transactional(readOnly=true) public Preferences get(Long id) { return view(active(id,false)); }
    @Transactional public Preferences patch(Long id,Patch patch) {
        User u=active(id,true);
        ObjectNode n=u.notificationPreferences!=null && u.notificationPreferences.isObject()?(ObjectNode)u.notificationPreferences.deepCopy():JsonNodeFactory.instance.objectNode();
        if(patch.matchingListings()!=null) n.put("matchingListings",patch.matchingListings());
        if(patch.brokerMessages()!=null) n.put("brokerMessages",patch.brokerMessages());
        if(patch.statusUpdates()!=null) n.put("statusUpdates",patch.statusUpdates());
        u.notificationPreferences=n;users.saveAndFlush(u);return view(u);
    }
}