# Business Requirements Document (BRD): Ứng dụng Theo dõi & Khuyến nghị Chứng khoán Việt Nam

## 1. Mục tiêu
Xây dựng nền tảng hỗ trợ nhà đầu tư cá nhân trên các sàn chứng khoán Việt Nam (HOSE, HNX, UPCoM) dựa trên phương pháp Wyckoff, VSA và dòng tiền.

## 2. Các yêu cầu kỹ thuật đặc thù (VN Market)
* **API Integration:** Sử dụng thư viện `vnstock` hoặc API từ FireAnt/FiinTrade.
* **Thời gian giao dịch:** Xử lý logic dữ liệu theo phiên (09:00-11:30, 13:00-15:00) và tách biệt dữ liệu phiên ATC để tránh nhiễu.
* **Biên độ giá:** Thiết lập hệ số tự động (±7%, ±10%, ±15%) tùy theo sàn (HOSE, HNX, UPCoM).

## 3. Module Phân tích (Core Engine)
* **Wyckoff Phase Identification:** Nhận diện tích lũy/phân phối.
* **VSA Indicator Suite:** Tự động phát hiện Stopping Volume, No Demand, Effort vs Result với bộ lọc Relative Volume (> 2.0x TB 20 phiên).

## 4. Module Quản trị rủi ro
* Thiết lập Stop-loss tự động theo cấu trúc kỹ thuật.
* Cảnh báo vi phạm quy tắc quản trị vốn.
