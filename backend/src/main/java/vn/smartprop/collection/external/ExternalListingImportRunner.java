package vn.smartprop.collection.external;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.stereotype.Component;

import java.io.File;

@Component
public class ExternalListingImportRunner implements ApplicationRunner {

    private static final Logger log = LoggerFactory.getLogger(ExternalListingImportRunner.class);

    private final ExternalListingImportService importService;

    @Value("${app.import.external-listings:}")
    private String importFilePath;

    public ExternalListingImportRunner(ExternalListingImportService importService) {
        this.importService = importService;
    }

    @Override
    public void run(ApplicationArguments args) throws Exception {
        String path = importFilePath;
        if (args.containsOption("app.import.external-listings")) {
            var vals = args.getOptionValues("app.import.external-listings");
            if (vals != null && !vals.isEmpty()) {
                path = vals.get(0);
            }
        }

        if (path != null && !path.isBlank()) {
            File csvFile = new File(path);
            if (!csvFile.exists()) {
                log.error("CSV import file does not exist: {}", path);
                return;
            }

            log.info("Starting external listings import from: {}", path);
            ExternalListingImportService.ImportSummary summary = importService.importCandidates(csvFile);
            log.info("Import finished successfully: processed={}, valid={}, needsReview={}, rejected={}, duplicateGroups={}",
                    summary.totalProcessed(), summary.validCount(), summary.needsReviewCount(),
                    summary.rejectedCount(), summary.duplicateGroupCount());
        }
    }
}
