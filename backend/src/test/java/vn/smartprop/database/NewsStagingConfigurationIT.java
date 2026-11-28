package vn.smartprop.database;
import org.springframework.boot.test.context.SpringBootTest;
/** Real staging configuration, using the approved strict PR41 identity on3311, never3307. */
@SpringBootTest(properties={
    "spring.config.import=classpath:application-hybrid-local-existing-v13-staging.yml",
    "spring.datasource.url=jdbc:mysql://127.0.0.1:3311/pr41_local?connectionTimeZone=UTC"
})
class NewsStagingConfigurationIT extends NewsLocalLineageIT {}
