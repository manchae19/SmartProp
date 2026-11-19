package vn.smartprop.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.annotation.EnableAsync;
import org.springframework.scheduling.annotation.EnableScheduling;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;

@Configuration @EnableAsync @EnableScheduling
public class ImageScanAsyncConfig {
    @Bean(name = "imageScanExecutor")
    public ThreadPoolTaskExecutor imageScanExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(1);
        executor.setMaxPoolSize(2);
        executor.setQueueCapacity(100);
        executor.setThreadNamePrefix("image-scan-");
        executor.setWaitForTasksToCompleteOnShutdown(false);
        executor.initialize();
        return executor;
    }

    /**
     * Separate pool for YOLOv8 analysis.
     *
     * <p>Deliberately its own executor: a slow inference must never occupy the
     * thread that duplicate scanning needs, and a vision outage must not fill
     * the scan queue. One worker keeps CPU contention with Ollama predictable.
     */
    @Bean(name = "imageAnalysisExecutor")
    public ThreadPoolTaskExecutor imageAnalysisExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(1);
        executor.setMaxPoolSize(1);
        executor.setQueueCapacity(50);
        executor.setThreadNamePrefix("image-analysis-");
        executor.setWaitForTasksToCompleteOnShutdown(false);
        executor.initialize();
        return executor;
    }
}
