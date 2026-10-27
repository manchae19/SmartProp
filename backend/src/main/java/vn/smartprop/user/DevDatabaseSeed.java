package vn.smartprop.user;

import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import javax.sql.DataSource;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Profile;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.core.io.ClassPathResource;
import org.springframework.jdbc.datasource.init.ResourceDatabasePopulator;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

/** Explicitly opt-in, development-only fixtures; no production or admin account creation. */
@Component @Profile("dev")
@ConditionalOnProperty(name="app.database-seed.enabled",havingValue="true")
public class DevDatabaseSeed implements ApplicationRunner {
    private final UserRepository users;
    private final PasswordEncoder passwords;
    private final DataSource dataSource;
    private final String password;
    private final Path fixture;
    public DevDatabaseSeed(UserRepository users, PasswordEncoder passwords, DataSource dataSource,
        @Value("${DEV_DATABASE_SEED_PASSWORD:}") String password,
        @Value("${DEV_DATABASE_SEED_FIXTURE:dev-fixtures/sample-property.svg}") String fixture) {
        this.users=users; this.passwords=passwords; this.dataSource=dataSource;
        this.password=password; this.fixture=Path.of(fixture);
    }
    @Override @Transactional
    public void run(ApplicationArguments args) throws Exception {
        if(password.length()<12 || password.getBytes(StandardCharsets.UTF_8).length>72)
            throw new IllegalStateException("Development fixture password must be 12+ characters and at most 72 UTF-8 bytes");
        if(!Files.isRegularFile(fixture))
            throw new IllegalStateException("Development fixture file is missing; set DEV_DATABASE_SEED_FIXTURE");
        account("buyer@smartprop.example.test", "Development Buyer", User.Role.BUYER);
        account("broker@smartprop.example.test", "Development Broker", User.Role.BROKER);
        users.flush();
        ResourceDatabasePopulator populator=new ResourceDatabasePopulator();
        populator.setSqlScriptEncoding("UTF-8");
        populator.addScript(new ByteArrayResource(("SET @fixture_bytes="+Files.size(fixture)+";").getBytes(StandardCharsets.UTF_8)));
        populator.addScript(new ClassPathResource("database/seeds/development.sql"));
        populator.execute(dataSource);
    }
    private void account(String email,String name,User.Role role) {
        User existing=users.findByEmail(email).orElse(null);
        if(existing!=null) {
            if(existing.role!=role) throw new IllegalStateException("Development seed refuses to alter an existing role");
            return;
        }
        User u=new User();u.email=email;u.fullName=name;u.role=role;u.status=User.Status.ACTIVE;
        u.passwordHash=passwords.encode(password);users.save(u);
    }
}
