package vn.smartprop.modules.property;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import java.math.BigDecimal;
import java.nio.file.Path;
import java.util.*;
import org.flywaydb.core.Flyway;
import org.hibernate.SessionFactory;
import org.hibernate.cfg.Configuration;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.locationtech.jts.geom.*;
import static org.junit.jupiter.api.Assertions.*;

@EnabledIfEnvironmentVariable(named="SMARTPROP_LISTING_TEST_URL",
    matches="jdbc:mysql://127\\.0\\.0\\.1:[0-9]+/smartprop_listing_test_[a-f0-9]+\\?.*")
class ListingCodeIntegrationTest {
    static SessionFactory sessions;
    static Flyway flyway;
    @BeforeAll static void setup() {
        String url=System.getenv("SMARTPROP_LISTING_TEST_URL");
        if(url==null||url.contains(":3306/"))throw new IllegalStateException("An isolated database is required");
        flyway=Flyway.configure().dataSource(url,"root","")
            .locations("filesystem:"+Path.of("../database/migrations").toAbsolutePath().normalize())
            .baselineOnMigrate(true).baselineVersion("15").target("16").cleanDisabled(true).load();
        assertEquals(1,flyway.migrate().migrationsExecuted);
        var config=new Configuration().addAnnotatedClass(Property.class);
        config.setProperty("hibernate.connection.url",url);
        config.setProperty("hibernate.connection.username","root");
        config.setProperty("hibernate.connection.password","");
        config.setProperty("hibernate.hbm2ddl.auto","validate");
        config.setProperty("hibernate.show_sql","false");
        sessions=config.buildSessionFactory();
    }
    @AfterAll static void close(){if(sessions!=null)sessions.close();}
    static Property fixture(){
        var p=new Property();p.id=UUID.randomUUID().toString();p.ownerId=1L;p.title="Isolated listing-code test";
        p.propertyType=Property.Type.APARTMENT;p.transactionType=Property.Transaction.SALE;p.price=new BigDecimal("2000000000");
        p.currency="VND";p.priceUnit=Property.PriceUnit.TOTAL;p.areaSqm=new BigDecimal("60");p.city="Da Nang";
        p.location=new GeometryFactory(new PrecisionModel(),4326).createPoint(new Coordinate(108.23,16.06));
        p.declaredAmenities=JsonNodeFactory.instance.arrayNode();p.status=Property.Status.DRAFT;p.contentVersion=1;
        return p;
    }
    @Test void generatedCodeIsFetchedImmediatelyAndIncludedInApi()throws Exception{
        var p=fixture();
        try(var session=sessions.openSession()){
            var tx=session.beginTransaction();session.persist(p);session.flush();
            assertNotNull(p.getListingCode());assertTrue(p.getListingCode().matches("SP[0-9]{3,}"));tx.commit();
        }
        var dto=PropertyService.view(p,List.of());
        var body=new ObjectMapper().findAndRegisterModules().readTree(new ObjectMapper().findAndRegisterModules().writeValueAsString(dto));
        assertEquals(p.getListingCode(),body.path("listingCode").asText());assertEquals(p.id,body.path("id").asText());
    }
    @Test void ordinaryUpdateKeepsTheSameCode(){
        var p=fixture();
        try(var session=sessions.openSession()){var tx=session.beginTransaction();session.persist(p);tx.commit();}
        String code=p.getListingCode();
        try(var session=sessions.openSession()){var tx=session.beginTransaction();var loaded=session.find(Property.class,p.id);loaded.title="Updated title";tx.commit();}
        try(var session=sessions.openSession()){assertEquals(code,session.find(Property.class,p.id).getListingCode());}
    }
    @Test void appliedMigrationHasNoPendingWork(){assertEquals(0,flyway.migrate().migrationsExecuted);}
}
