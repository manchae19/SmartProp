package vn.smartprop.modules.news;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

/** V1 never fetches live RSS, even when explicitly configured to do so. */
class NewsLiveIngestionIT {
    @Test void liveIngestionIsLockedBeforeAnyRepositoryOrNetworkCall() {
        var sources = mock(NewsSourceRepository.class);
        var runs = mock(NewsIngestionRunRepository.class);
        var fetcher = mock(NewsFeedFetcher.class);
        var persistence = mock(NewsIngestionPersistenceService.class);
        var properties = new NewsProperties();
        properties.setIngestionEnabled(true);
        var service = new NewsIngestionService(sources, runs, fetcher, persistence, properties);
        assertFalse(NewsReleaseCapability.liveIngestionPermitted());
        assertEquals(NewsReleaseCapability.LOCK_CODE, service.ingest("synthetic").errorCode());
        assertTrue(service.ingestDue().isEmpty());
        verifyNoInteractions(sources, runs, fetcher, persistence);
    }
}
