SMARTPROP — CRAWLER CAFELAND (ĐÀ NẴNG)

1. Thư mục crawler: F:\SmartProp\ai-services\app\data\crawler_cafeland
2. Mở PowerShell và chạy:

cd F:\SmartProp
.\ai-services\app\data\crawler_cafeland\RUN_CAFELAND.ps1

Chạy lại đúng câu lệnh trên để tiếp tục. --max-new là số tin MỚI tối đa
trong mỗi lần chạy; 200 trang không bảo đảm có đủ 1.000 tin trong phạm vi.
Sau khi đã tới cuối phân trang, dùng thư mục output mới để chạy đợt mới.
Không chạy hai tiến trình cùng thư mục output.

Dữ liệu và checkpoint: ai-services/app/data/data_raw/cafeland_batch
Ctrl+C dừng có chủ đích; chạy lại để tiếp tục và bỏ qua ID đã lưu.

KẾT QUẢ
- cafeland_listings.csv: tin bán được xác minh địa bàn từ trang chi tiết.
- cafeland_scope_review.csv: địa danh chưa xác minh hoặc ngoài phạm vi;
  chỉ lưu thẻ danh sách, không đưa vào dữ liệu huấn luyện.
- checkpoint.json: trang tiếp tục. Không xóa khi muốn tiếp tục cùng đợt.
- sample/: kết quả chạy thử trực tiếp; không tự động gộp vào batch mới.

PHẠM VI VÀ CHẤT LƯỢNG
Bảy quận/huyện cũ: Hải Châu, Thanh Khê, Sơn Trà, Ngũ Hành Sơn,
Liên Chiểu, Cẩm Lệ, Hòa Vang. Địa danh mới không được tự suy ra quận cũ.
Một tin phải khớp ID/URL JSON-LD, tiêu đề và địa bàn giữa danh sách/chi tiết.
Giá là triệu đồng cho toàn bộ bất động sản; diện tích là m². Giá thỏa thuận,
giá theo m² và số không đọc được để trống và đánh dấu cần kiểm tra.
category lấy từ loại tin trên URL vị trí, không chỉ từ tiêu đề; loại chưa
biết để Chưa xác định. Tin có category_needs_review, price_needs_review,
area_needs_review hoặc review_reason cần kiểm tra trước khi huấn luyện.
Không suy số phòng từ lời quảng cáo. Không thu số điện thoại/tên người bán.
Không suy ngày đăng từ "Hôm nay"; posted_at để trống. Ngày hiển thị,
ngày thuộc tính và priceValidUntil giữ riêng dạng thô, không dùng làm ngày đăng.
Chống trùng ID trong cùng thư mục output; chưa chống trùng bất động sản
đăng nhiều ID hoặc trùng giữa các nguồn.

TRUY CẬP
Đọc robots.txt trước mỗi lượt, chỉ dùng trang công khai và nghỉ ít nhất 2 giây
mỗi request (mặc định 3). Dừng khi lỗi HTTP/timeout, challenge hoặc cấu trúc
không khớp. Không có cơ chế vượt CAPTCHA/đăng nhập/chặn truy cập.
Khi parser lỗi, debug_listing.html hoặc debug_detail.html giúp kiểm tra;
checkpoint và CSV đã ghi giữ nguyên. Không tự động bỏ qua lỗi để tiếp tục.
Các trường nguồn có thể thay đổi; đây là dữ liệu thô cần làm sạch.
