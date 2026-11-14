package vn.smartprop.modules.property;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import vn.smartprop.modules.auth.AccountAccess;
import vn.smartprop.common.ApiInputs;
import vn.smartprop.modules.user.User;
import vn.smartprop.modules.user.UserRepository;

@Service
public class PropertyContactService {
    private final AccountAccess access;
    private final PropertyService properties;
    private final UserRepository users;
    private final ContactRateLimit limit;
    public PropertyContactService(AccountAccess access,PropertyService properties,UserRepository users,ContactRateLimit limit) {
        this.access=access;this.properties=properties;this.users=users;this.limit=limit;
    }
    @Transactional(readOnly=true)
    public PropertyContactDtos.Contact contact(Long actor,String id,String ip) {
        access.active(actor);
        // Count unsuccessful authenticated lookups too, to limit enumeration.
        limit.check(actor,ip);
        Property property=properties.publicProperty(id);
        User owner=users.findById(property.ownerId).orElseThrow(ApiInputs::missing);
        if(owner.deletedAt!=null || owner.status!=User.Status.ACTIVE) throw ApiInputs.missing();
        String phone=clean(property.contactPhone), email=clean(property.contactEmail);
        if(phone==null && email==null) return new PropertyContactDtos.Contact(false,null,null,null);
        return new PropertyContactDtos.Contact(true,clean(property.contactName),phone,email);
    }
    private static String clean(String value) {return value==null || value.isBlank()?null:value.strip();}
}
