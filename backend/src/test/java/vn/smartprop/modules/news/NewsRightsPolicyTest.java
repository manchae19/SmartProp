package vn.smartprop.modules.news;

import java.util.Optional;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class NewsRightsPolicyTest {
    NewsSource approved() {
        var s = new NewsSource(); s.id="synthetic"; s.name="Synthetic fixture";
        s.publisher="Synthetic Publisher"; s.websiteUrl="https://example.invalid";
        s.feedUrl="https://example.invalid/feed"; s.rightsReviewStatus=NewsSource.RightsStatus.APPROVED;
        s.rightsReference="synthetic-fixture-permission"; s.enabled=true; s.allowSummary=true;
        return s;
    }
    NewsDtos.UpdateSource patch(String publisher, String website, NewsSource.RightsStatus status, String reference, Boolean enabled) {
        return new NewsDtos.UpdateSource(null,publisher,website,null,null,null,status,reference,null,null,null,enabled,null);
    }
    void update(NewsSource source, NewsDtos.UpdateSource patch, NewsArticleRepository articles) {
        var sources=mock(NewsSourceRepository.class);
        when(sources.lockById(source.id)).thenReturn(Optional.of(source));
        new NewsAdminService(sources,articles,mock(NewsIngestionService.class),mock(NewsService.class)).update(source.id,patch);
    }
    @Test void refusesNullEmptyAndWhitespaceApprovalAtPersistenceBoundary() {
        for(String ref : new String[]{null,""," ","\t\r\n"}) {
            var s=approved();s.rightsReference=ref;
            assertFalse(s.ingestible()); assertFalse(NewsRightsPolicy.summary(s));
            assertThrows(IllegalStateException.class,s::validateRights);
        }
    }
    @Test void websiteChangeInvalidatesApprovalAndHidesHistoryWithoutDeletingIt() {
        var s=approved();var articles=mock(NewsArticleRepository.class);
        update(s,patch(null,"https://other.example.invalid",null,null,null),articles);
        assertEquals(NewsSource.RightsStatus.PENDING_REVIEW,s.rightsReviewStatus);
        assertNull(s.rightsReference);assertFalse(s.enabled);assertFalse(s.allowSummary);assertFalse(s.allowImages);
        verify(articles).hideBySource(eq(s.id),any());verifyNoMoreInteractions(articles);
    }
    @Test void publisherChangeCannotReuseOldReferenceInLaterApproval() {
        var s=approved();var articles=mock(NewsArticleRepository.class);
        update(s,patch("New synthetic publisher",null,null,null,null),articles);
        assertThrows(vn.smartprop.common.ApiException.class,()->update(s,patch(null,null,NewsSource.RightsStatus.APPROVED,null,null),articles));
    }
    @Test void replacingApprovedReferenceRequiresSeparateReview() {
        var s=approved();update(s,patch(null,null,null,"replacement-fixture-permission",null),mock(NewsArticleRepository.class));
        assertEquals(NewsSource.RightsStatus.PENDING_REVIEW,s.rightsReviewStatus);assertFalse(s.enabled);
        assertThrows(vn.smartprop.common.ApiException.class,()->update(approved(),patch(null,null,NewsSource.RightsStatus.APPROVED,"replacement",true),mock(NewsArticleRepository.class)));
    }
    @Test void pendingAndRejectedBothDisableIngestion() {
        for(var status : new NewsSource.RightsStatus[]{NewsSource.RightsStatus.PENDING_REVIEW,NewsSource.RightsStatus.REJECTED}) {
            var s=approved();update(s,patch(null,null,status,null,null),mock(NewsArticleRepository.class));
            assertFalse(s.enabled);assertFalse(s.ingestible());assertFalse(NewsRightsPolicy.summary(s));
        }
    }
}
