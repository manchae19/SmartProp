package vn.smartprop.modules.email;
import org.springframework.context.annotation.Configuration;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.scheduling.annotation.*;
@Configuration @EnableScheduling
@ConditionalOnProperty(name="app.email.worker-enabled",havingValue="true")
public class MailWorker {
    private final MailOutbox outbox;public MailWorker(MailOutbox outbox){this.outbox=outbox;}
    @Scheduled(fixedDelayString="${app.email.worker-delay-ms:30000}") public void run(){try{outbox.deliverBatch();}catch(Exception e){org.slf4j.LoggerFactory.getLogger(MailWorker.class).warn("Mail worker unavailable");}}
}
