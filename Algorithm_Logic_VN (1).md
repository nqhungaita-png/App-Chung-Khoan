# Tài liệu Logic Thuật toán (Algorithm Logic)

## 1. Xử lý dữ liệu VN
* **ATC Exclusion:** Khi tính toán tín hiệu kỹ thuật trong ngày, lọc bỏ hoặc gắn nhãn riêng cho dữ liệu phiên ATC để tránh tín hiệu giả.
* **Relative Volume:** `Rel_Vol = Volume_today / Average(Volume, 20)`.

## 2. Logic VSA
* **Stopping Volume:** (Close < Open) & (Volume > 2.0 * TB_20) & (Râu dưới >= 2*Thân nến).
* **Effort vs Result:** Nếu nến tăng với khối lượng lớn nhưng biên độ giá hẹp (Spread nhỏ) -> Dấu hiệu đảo chiều (Buying Climax).

## 3. Logic Wyckoff
* **Spring Detection:** Giá phá đáy hỗ trợ cũ sau đó hồi phục trong phiên với khối lượng tăng đột biến.
