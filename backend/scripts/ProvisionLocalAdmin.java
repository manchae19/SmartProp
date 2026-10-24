import java.sql.*;
import java.nio.charset.StandardCharsets;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
/** Explicit local operator command. Reads secrets from process environment, never seeds on startup. */
class ProvisionLocalAdmin {
 public static void main(String[] args)throws Exception{
  String url=System.getenv("DB_URL"), email=System.getenv("LOCAL_ADMIN_EMAIL"), password=System.getenv("LOCAL_ADMIN_PASSWORD");
  if(url==null||!url.matches("^jdbc:mysql://(?:localhost|127\\.0\\.0\\.1):3306/smartprop(?:\\?.*)?$"))throw new IllegalArgumentException("Only the explicitly configured local smartprop database is supported");
  if(email==null||!email.matches("[^\\s@]+@[^\\s@]+\\.[^\\s@]+")||password==null||password.length()<8||password.getBytes(StandardCharsets.UTF_8).length>72)throw new IllegalArgumentException("Supply a valid LOCAL_ADMIN_EMAIL and an 8-character/72-byte password through environment variables");
  email=email.strip().toLowerCase(java.util.Locale.ROOT);var encoder=new BCryptPasswordEncoder(12);
  try(Connection c=DriverManager.getConnection(url,System.getenv("DB_USER"),System.getenv("DB_PASSWORD"))){
   c.setAutoCommit(false);
   try{
    try(PreparedStatement p=c.prepareStatement("SELECT role,status,deleted_at,password_hash FROM users WHERE email=? FOR UPDATE")){
     p.setString(1,email);try(ResultSet r=p.executeQuery()){if(r.next()){
      if(!"ADMIN".equals(r.getString(1))||!"ACTIVE".equals(r.getString(2))||r.getTimestamp(3)!=null||!encoder.matches(password,r.getString(4)))throw new IllegalStateException("Account exists; refusing to promote, unlock or reset any existing account");
      c.rollback();System.out.println("ADMIN_ACCOUNT_ALREADY_READY; no changes");return;
     }}
    }
    long id;
    try(PreparedStatement p=c.prepareStatement("INSERT INTO users(email,password_hash,full_name,role,status,created_at,updated_at) VALUES(?,?,?,'ADMIN','ACTIVE',UTC_TIMESTAMP(6),UTC_TIMESTAMP(6))",Statement.RETURN_GENERATED_KEYS)){
     p.setString(1,email);p.setString(2,encoder.encode(password));p.setString(3,"Admin");p.executeUpdate();try(ResultSet r=p.getGeneratedKeys()){if(!r.next())throw new IllegalStateException("No generated user ID");id=r.getLong(1);}
    }
    try(PreparedStatement p=c.prepareStatement("SELECT COUNT(*) FROM user_roles WHERE user_id=? AND role_code='ADMIN'")){p.setLong(1,id);try(ResultSet r=p.executeQuery()){r.next();if(r.getInt(1)!=1)throw new IllegalStateException("ADMIN role bridge missing; transaction rolled back");}}
    try(PreparedStatement p=c.prepareStatement("INSERT INTO audit_logs(id,actor_type,action,entity_type,entity_numeric_id,new_values,created_at) VALUES(UUID(),'SYSTEM','LOCAL_ADMIN_PROVISIONED','USER',?,JSON_OBJECT('role','ADMIN','status','ACTIVE'),UTC_TIMESTAMP(6))")){p.setLong(1,id);p.executeUpdate();}
    c.commit();System.out.println("ADMIN_ACCOUNT_CREATED; role=ADMIN; status=ACTIVE; bcrypt=12; role bridge and audit verified");
   }catch(Exception e){c.rollback();if(e instanceof SQLException sql)throw new IllegalStateException("Provisioning rolled back; SQLState="+sql.getSQLState()+", code="+sql.getErrorCode());throw e;}
  }
 }
}