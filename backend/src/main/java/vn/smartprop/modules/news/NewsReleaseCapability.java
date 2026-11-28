package vn.smartprop.modules.news;

/**
 * Release capability của News Backend V1.
 *
 * <p><b>V1 là READ-ONLY RELEASE.</b> Network ingestion bị khóa bằng hằng số biên dịch,
 * không phải bằng cấu hình. Không có property, biến môi trường, profile, admin request
 * hay allowlist nào mở được nó.
 *
 * <p>Lý do: DNS rebinding chưa được xử lý đầy đủ (kiểm tra DNS và kết nối thực tế là
 * hai thời điểm khác nhau). Mở live ingestion khi chưa có resolver pinning hoặc egress
 * control là rủi ro SSRF không chấp nhận được.
 *
 * <p>Mở lại trong V1.1 yêu cầu <b>thay đổi code</b> ở lớp này, kèm security review và
 * transport đã được kiểm chứng — không phải đổi một biến cấu hình.
 */
public final class NewsReleaseCapability {
    private NewsReleaseCapability() {}

    /**
     * Live network ingestion có được phép trong bản phát hành này không.
     *
     * <p>Đây là hằng số {@code static final} — trình biên dịch có thể inline, và không
     * có cơ chế reflection/configuration nào trong ứng dụng thay đổi được giá trị này
     * ở runtime. Đổi giá trị = sửa source + review + build lại.
     */
    private static final boolean LIVE_INGESTION_PERMITTED = false;

    /** Lý do khóa, dùng cho log và response. */
    public static final String LOCK_REASON =
        "News V1 là read-only release: live network ingestion bị khóa (DNS rebinding chưa xử lý)";

    /** Mã lỗi trả về cho caller khi ingestion bị khóa. */
    public static final String LOCK_CODE = "LIVE_INGESTION_LOCKED";

    /**
     * Kiểm tra quyền thực hiện network ingestion.
     *
     * @return {@code true} chỉ khi bản phát hành này cho phép — hiện luôn {@code false}
     */
    public static boolean liveIngestionPermitted() {
        return LIVE_INGESTION_PERMITTED;
    }
}
