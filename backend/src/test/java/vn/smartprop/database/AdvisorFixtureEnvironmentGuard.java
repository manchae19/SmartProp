package vn.smartprop.database;

import java.nio.file.*;
import java.util.List;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.env.EnvironmentPostProcessor;
import org.springframework.core.Ordered;
import org.springframework.core.env.*;
/** Test classpath only; runs after ConfigData/native profile guards, before any datasource bean. */
public final class AdvisorFixtureEnvironmentGuard implements EnvironmentPostProcessor,Ordered {
    public int getOrder(){return Ordered.HIGHEST_PRECEDENCE+12;}
    public void postProcessEnvironment(ConfigurableEnvironment env,SpringApplication app) {
        boolean advisorRuntime="true".equals(System.getenv("PR41_ADVISOR_RUNTIME_TEST"));
        boolean localFixture="true".equals(System.getenv("PR41_LOCAL_V28_TEST"));
        if(!advisorRuntime&&!localFixture)return;
        if(localFixture&&!advisorRuntime){
            AdvisorFixtureBoundary.check(List.of(env.getActiveProfiles()).equals(List.of(Pr41TestFixture.PROFILE)),
                "PR41 Local fixture profile must be explicit and exclusive");
            AdvisorFixtureBoundary.check(Pr41TestFixture.PROFILE.equals(env.getProperty("smartprop.test.fixture-profile")),
                "Test-only PR41 fixture profile marker is missing");
        }
        String file=env.getProperty("smartprop.test.fixture-manifest",System.getenv("SMARTPROP_TEST_FIXTURE_MANIFEST"));
        AdvisorFixtureBoundary.check(file!=null&&!file.isBlank(),"No allocated fixture manifest");
        if(env.getProperty("smartprop.test.fixture-manifest")==null)
            env.getPropertySources().addFirst(new MapPropertySource("independent-fixture-manifest",java.util.Map.of("smartprop.test.fixture-manifest",file)));
        var fixture=new AdvisorFixtureBoundary(Path.of(file),System.getenv("SMARTPROP_TEST_FIXTURE_AUTHORIZATION"));
        fixture.verify(env.getProperty("spring.datasource.url"));
        for(String name:new String[]{"spring.datasource.hikari.jdbc-url","spring.flyway.url"}) {
            String candidate=env.getProperty(name);if(candidate!=null&&!candidate.isBlank())fixture.verify(candidate);
        }
        for(String name:new String[]{"spring.datasource.jndi-name","spring.datasource.hikari.data-source-class-name","spring.datasource.hikari.data-source-j-n-d-i","spring.datasource.hikari.data-source-properties.url","spring.datasource.hikari.data-source-properties.serverName"})
            AdvisorFixtureBoundary.check(env.getProperty(name)==null,"Alternate datasource mechanism forbidden: "+name);
        AdvisorFixtureBoundary.check(AdvisorGuardedDriver.class.getName().equals(env.getProperty("spring.datasource.driver-class-name")),"Physical connection guard must be explicit");
        AdvisorFixtureBoundary.check(!env.getProperty("spring.flyway.enabled",Boolean.class,false)&&"validate".equals(env.getProperty("spring.jpa.hibernate.ddl-auto"))&&"never".equals(env.getProperty("spring.sql.init.mode")),"No auto-migrate/DDL/init in fixture runtime");
        AdvisorFixtureBoundary.check(!env.getProperty("app.news.ingestion-enabled",Boolean.class,false),"Live News ingestion must remain disabled");
        String nativeProfile=env.getProperty("smartprop.test.native-profile");
        if(nativeProfile!=null){
            // Validate the real native policy using the actual runtime flags. Only the endpoint literal
            // is translated for this policy check; it is never bound to a datasource or connected.
            var policy=new StandardEnvironment();policy.setActiveProfiles(nativeProfile);
            policy.getPropertySources().addFirst(new org.springframework.core.env.MapPropertySource("native-policy-literal",java.util.Map.of("spring.datasource.url",MigrationProfileEnvironmentGuard.STAGING.equals(nativeProfile)?MigrationProfileEnvironmentGuard.STAGING_URL:MigrationProfileEnvironmentGuard.LOCAL_URL)));
            for(PropertySource<?> source:env.getPropertySources())policy.getPropertySources().addLast(source);
            MigrationProfileEnvironmentGuard.check(policy);
        }
        AdvisorFixtureBoundary.AUTHORIZED.put(fixture.url,fixture);
        System.out.println("FIXTURE_PRE_CONNECTION_PASS jdbc="+fixture.url+" source="+(env.getPropertySources().contains("commandLineArgs")?"commandLineArgs":"resolved-environment")+" nativeSimulation="+nativeProfile);
    }
}
