package vn.smartprop.modules.news;

import java.time.Instant;
import java.util.*;
import java.util.concurrent.*;
import org.junit.jupiter.api.*;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.autoconfigure.orm.jpa.HibernatePropertiesCustomizer;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;
import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest
@org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc
@Import(NewsAdminConcurrentIT.SqlCapture.class)
@EnabledIfEnvironmentVariable(named="DB_URL",matches=".+")
class NewsAdminConcurrentIT {
    static final Queue<String> SQL = new ConcurrentLinkedQueue<>();
    @TestConfiguration static class SqlCapture {
        @Bean HibernatePropertiesCustomizer captureAdminSql() {
            return properties -> properties.put("hibernate.session_factory.statement_inspector",
                (org.hibernate.resource.jdbc.spi.StatementInspector) sql -> { SQL.add(sql); return sql; });
        }
    }
    @Autowired org.springframework.test.web.servlet.MockMvc mvc;
    @Autowired NewsAdminService admin;
    @Autowired NewsArticleRepository articles;
    @Autowired JdbcTemplate jdbc;
    @Autowired PlatformTransactionManager manager;
    String source, article;
    @BeforeEach void fixture() {
        vn.smartprop.testing.Pr41DatabaseTestSafety.require(jdbc);
        source=UUID.randomUUID().toString();article=UUID.randomUUID().toString();
        jdbc.update("INSERT INTO news_sources(id,source_code,name,publisher,website_url,feed_url,rights_review_status,rights_reference,enabled) VALUES(?,?,'SYNTHETIC CONCURRENCY','SYNTHETIC OWNER','https://example.invalid',?,'APPROVED','SYNTHETIC FIXTURE ONLY',1)",source,source,"https://example.invalid/"+source);
        jdbc.update("INSERT INTO news_articles(id,source_id,canonical_url,canonical_url_hash,title,category,region,fetched_at,first_seen_at,last_seen_at,publication_status,featured) VALUES(?,?,?,?,'SYNTHETIC CONCURRENCY','MARKET','DA_NANG',UTC_TIMESTAMP(6),UTC_TIMESTAMP(6),UTC_TIMESTAMP(6),'VISIBLE',0)",article,source,"https://example.invalid/"+article,NewsText.sha256(article));
        SQL.clear();
    }
    @AfterEach void cleanup() {
        if(source!=null)jdbc.update("DELETE FROM news_sources WHERE id=?",source);
    }
    static void await(CountDownLatch latch) {
        try { assertTrue(latch.await(20,TimeUnit.SECONDS),"transaction barrier timeout"); }
        catch(InterruptedException e){Thread.currentThread().interrupt();throw new AssertionError(e);}
    }
    void mutate(boolean featured, boolean identity) {
        if(featured)admin.setFeatured(article,true);
        else if(identity)admin.update(source,new NewsDtos.UpdateSource(null,"SYNTHETIC NEW OWNER",null,null,null,null,null,null,null,null,null,null,null));
        else admin.setVisibility(article,NewsArticle.PublicationStatus.HIDDEN);
    }
    @ParameterizedTest(name="featured commits first={0}, source identity hide={1}")
    @CsvSource({"true,false","false,false","true,true","false,true"})
    void overlappingTransactionsPreserveBothAdminDecisions(boolean featuredFirst,boolean identity) throws Exception {
        CountDownLatch bothRead=new CountDownLatch(2), firstCommitted=new CountDownLatch(1);
        ExecutorService pool=Executors.newFixedThreadPool(2);
        try {
            Future<?> first=pool.submit(()->{
                new TransactionTemplate(manager).executeWithoutResult(tx->{
                    assertNotNull(articles.findById(article).orElseThrow());bothRead.countDown();await(bothRead);
                    mutate(featuredFirst,identity);
                });firstCommitted.countDown();
            });
            Future<NewsDtos.AdminArticle> second=pool.submit(()->new TransactionTemplate(manager).execute(tx->{
                // Hold a real stale persistence-context snapshot while the other transaction commits.
                var old=articles.findById(article).orElseThrow();assertFalse(old.featured);
                assertEquals(NewsArticle.PublicationStatus.VISIBLE,old.publicationStatus);
                bothRead.countDown();await(firstCommitted);
                if(featuredFirst){
                    if(identity){mutate(false,true);return null;}
                    return admin.setVisibility(article,NewsArticle.PublicationStatus.HIDDEN);
                }
                return admin.setFeatured(article,true);
            }));
            first.get(25,TimeUnit.SECONDS);var response=second.get(25,TimeUnit.SECONDS);
            if(response!=null){assertEquals("HIDDEN",response.publicationStatus());assertTrue(response.featured());}
            assertEquals("HIDDEN",jdbc.queryForObject("SELECT publication_status FROM news_articles WHERE id=?",String.class,article));
            assertEquals(1,jdbc.queryForObject("SELECT featured FROM news_articles WHERE id=?",Integer.class,article));
            assertEquals(0,articles.findPublic(null,null,null,null,org.springframework.data.domain.PageRequest.of(0,20)).getTotalElements());
            assertEquals(0,articles.findFeatured(org.springframework.data.domain.PageRequest.of(0,20)).getTotalElements());
            for(String path:new String[]{"/api/v1/news","/api/v1/news/featured"})
                mvc.perform(org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get(path))
                    .andExpect(org.springframework.test.web.servlet.result.MockMvcResultMatchers.status().isOk())
                    .andExpect(org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath("$.totalElements").value(0));
            List<String> updates=SQL.stream().map(String::toLowerCase).filter(sql->sql.startsWith("update news_articles ")).toList();
            assertFalse(updates.isEmpty());
            for(String sql:updates){
                String columns=sql.substring(sql.indexOf(" set ")+5,sql.indexOf(" where "));
                assertFalse(columns.contains("source_id")||columns.contains("title=")||columns.contains("summary="),sql);
                assertFalse(columns.contains("featured=")&&columns.contains("publication_status="),sql);
            }
            System.out.println("ADMIN_CONCURRENCY_SQL featuredFirst="+featuredFirst+" identity="+identity+" "+updates);
        } finally {firstCommitted.countDown();bothRead.countDown();bothRead.countDown();pool.shutdownNow();assertTrue(pool.awaitTermination(5,TimeUnit.SECONDS));}
    }
    @Test void missingArticlePreserves404Contract() {
        for(boolean featured:new boolean[]{true,false}){
            var error=assertThrows(vn.smartprop.common.ApiException.class,()->{
                if(featured)admin.setFeatured("missing-synthetic",true);
                else admin.setVisibility("missing-synthetic",NewsArticle.PublicationStatus.HIDDEN);
            });assertEquals(404,error.status);
        }
    }
}
