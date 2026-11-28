package vn.smartprop.modules.news;

/** One rights decision for reads, persistence and ingestion. No network access. */
public final class NewsRightsPolicy {
    private NewsRightsPolicy() {}
    public static boolean hasReference(String reference) {
        return reference != null && reference.codePoints().anyMatch(c -> !Character.isWhitespace(c) && !Character.isSpaceChar(c));
    }
    public static boolean approved(NewsSource source) {
        return source != null && source.rightsReviewStatus == NewsSource.RightsStatus.APPROVED
            && hasReference(source.rightsReference);
    }
    public static boolean summary(NewsSource source) {
        return approved(source) && source.enabled && source.allowSummary;
    }
    public static void validate(NewsSource source) {
        if (source.rightsReviewStatus == NewsSource.RightsStatus.APPROVED && !approved(source))
            throw new IllegalStateException("APPROVED requires a nonblank rightsReference");
        if (source.enabled && !approved(source))
            throw new IllegalStateException("Only a reviewed source can be enabled");
    }
}
