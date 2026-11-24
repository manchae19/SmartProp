package vn.smartprop.modules.news;

import java.util.List;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

/**
 * Scheduler thu thập tin tức.
 *
 * <p>Chỉ chạy khi {@code app.news.ingestion-enabled=true}. Mặc định TẮT — không tự
 * động gọi mạng ra ngoài khi chưa được cấu hình.
 *
 * <p>Mỗi nguồn có {@code fetchIntervalMinutes} riêng; scheduler chỉ chọn nguồn đã
 * đến hạn. Không giữ transaction trong lúc chờ network.
 */
@Component
@ConditionalOnProperty(name = "app.news.ingestion-enabled", havingValue = "true")
public class NewsScheduler {
    private static final Logger log = LoggerFactory.getLogger(NewsScheduler.class);

    private final NewsIngestionService ingestion;

    public NewsScheduler(NewsIngestionService ingestion) { this.ingestion = ingestion; }

    /**
     * Chạy mỗi 5 phút. Việc chọn nguồn nào đến hạn do {@code fetchIntervalMinutes}
     * của từng nguồn quyết định, nên nhịp này chỉ là tần suất kiểm tra.
     */
    @Scheduled(fixedDelayString = "${app.news.scheduler-delay-ms:300000}",
               initialDelayString = "${app.news.scheduler-initial-delay-ms:60000}")
    public void run() {
        List<NewsIngestionService.Outcome> outcomes;
        try {
            outcomes = ingestion.ingestDue();
        } catch (RuntimeException e) {
            // Không để scheduler chết vì một lỗi bất ngờ.
            log.error("news.scheduler failed: {}", e.getClass().getSimpleName());
            return;
        }
        if (outcomes.isEmpty()) return;

        long failed = outcomes.stream()
            .filter(o -> o.status() == NewsIngestionRun.Status.FAILED).count();
        log.info("news.scheduler done sources={} failed={}", outcomes.size(), failed);
    }
}
