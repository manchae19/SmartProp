package vn.smartprop.database;

import java.util.*;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.env.EnvironmentPostProcessor;
import org.springframework.core.Ordered;
import org.springframework.core.env.ConfigurableEnvironment;
import org.springframework.core.env.Environment;

/** Reject ambiguous profiles/auto-DDL before datasource or Flyway initialization. */
public class MigrationProfileEnvironmentGuard implements EnvironmentPostProcessor, Ordered {
    public static final String LOCAL="hybrid-local-existing-v13", STANDARD="standard-migrations";
    public static final String LOCAL_URL="jdbc:mysql://127.0.0.1:3306/smartprop?connectionTimeZone=UTC";
    /** Staging is the same lineage on the isolated instance; the URL is a literal, never a variable. */
    public static final String STAGING="hybrid-local-existing-v13-staging";
    public static final String STAGING_URL="jdbc:mysql://127.0.0.1:3307/smartprop?connectionTimeZone=UTC";
    public static final String STAGING_DATADIR_SUFFIX="/mysql-isolated/data/";
    @Override public int getOrder(){return Ordered.HIGHEST_PRECEDENCE+11;}
    @Override public void postProcessEnvironment(ConfigurableEnvironment env,SpringApplication app){check(env);}
    public static boolean staging(Environment env){return List.of(env.getActiveProfiles()).contains(STAGING);}
    public static boolean isLocal(Environment env){return List.of(env.getActiveProfiles()).contains(LOCAL)||staging(env);}
    public static String expectedLocalUrl(Environment env){return staging(env)?STAGING_URL:LOCAL_URL;}
    public static void check(ConfigurableEnvironment env){
        Set<String> profiles=new HashSet<>(List.of(env.getActiveProfiles()));
        boolean local=isLocal(env),standard=profiles.contains(STANDARD);
        if(!local&&!standard)return;
        if(profiles.size()!=1)throw new IllegalStateException("Select exactly one explicit migration profile; do not combine it with dev or another lineage.");
        String location="classpath:database/"+(local?"legacy-hybrid-local":"migrations")+",classpath:database/research-migrations"+(local?"":"/poi");
        if(!location.equals(env.getProperty("spring.flyway.locations")))throw new IllegalStateException("Unexpected migration location for selected lineage.");
        if(env.getProperty("spring.flyway.enabled",Boolean.class,false))throw new IllegalStateException("Runtime auto-migrate is forbidden. Use the separately reviewed CLI.");
        if(!"validate".equals(env.getProperty("spring.jpa.hibernate.ddl-auto"))||!"never".equals(env.getProperty("spring.sql.init.mode")))throw new IllegalStateException("Runtime DDL/init must remain disabled.");
        if(local&&!expectedLocalUrl(env).equals(env.getProperty("spring.datasource.url")))throw new IllegalStateException("Local lineage only permits "+expectedLocalUrl(env)+".");
        if(local&&!env.getProperty("app.local-lineage.require-complete",Boolean.class,true)){
            if(staging(env))throw new IllegalStateException("Staging requires the completed Local lineage; the read-only pending-schema mode is not allowed.");
            if(!env.getProperty("spring.datasource.hikari.read-only",Boolean.class,false)
                ||!"SET SESSION TRANSACTION READ ONLY".equals(env.getProperty("spring.datasource.hikari.connection-init-sql"))
                ||env.getProperty("app.broker-applications.enabled",Boolean.class,false)
                ||env.getProperty("app.profile.avatar-enabled",Boolean.class,false)
                ||env.getProperty("app.google.enabled",Boolean.class,false))throw new IllegalStateException("Pending schema is allowed only for explicit read-only Advisor with Broker/Avatar/Google disabled.");
        }
    }
}
