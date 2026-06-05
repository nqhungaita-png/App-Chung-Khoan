import sys
import logging
from data_feed.vnstock_feed import VNStockDataFeed

# Cấu hình UTF-8 cho console để in log tiếng Việt không bị lỗi trên Windows
sys.stdout.reconfigure(encoding='utf-8')
from indicators.vsa import VSAIndicator

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    logger.info("Khởi động Hệ thống phân tích chứng khoán VN (VSA/Wyckoff)")
    
    # 1. Khởi tạo Data Feed
    data_feed = VNStockDataFeed(retries=3, backoff_factor=2)
    
    # Cấu hình lấy dữ liệu (Ví dụ HPG)
    symbol = 'HPG'
    start_date = '2023-01-01'
    end_date = '2024-01-01'
    
    logger.info(f"Yêu cầu dữ liệu cho mã {symbol} từ {start_date} đến {end_date}...")
    
    df = data_feed.fetch_historical_data(symbol, start_date, end_date, resolution='1D')
    
    if df.empty:
        logger.error("Không thể lấy dữ liệu. Dừng chương trình.")
        return
        
    # 2. Phân tích VSA
    logger.info("Đang chạy module tính toán VSA...")
    vsa_engine = VSAIndicator(df)
    vsa_result = vsa_engine.run_all()
    
    # In ra mẫu 10 ngày cuối cùng để kiểm tra các chỉ báo
    columns_to_show = ['Date', 'Close', 'Volume', 'Rel_Vol', 'Spread', 'Stopping_Volume', 'Effort_vs_Result_Bearish', 'Spring']
    print("\n--- KẾT QUẢ PHÂN TÍCH VSA (10 NGÀY CUỐI) ---")
    print(vsa_result[columns_to_show].tail(10).to_string(index=False))
    
if __name__ == "__main__":
    main()
