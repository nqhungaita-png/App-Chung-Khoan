import sys
import logging
import pandas as pd
from data_feed.vnstock_feed import VNStockDataFeed
from indicators.vsa import VSAIndicator

# Cấu hình UTF-8 để không lỗi font
sys.stdout.reconfigure(encoding='utf-8')
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def test_vsa_signals():
    print("--- BẮT ĐẦU TEST TÍN HIỆU VSA ---")
    print("Đang tải dữ liệu HPG giai đoạn 2022 (giai đoạn thị trường biến động mạnh)...")
    
    feed = VNStockDataFeed()
    # Lấy dữ liệu năm 2022, thời điểm HPG tạo đáy với khối lượng khủng
    df = feed.fetch_historical_data('HPG', '2022-10-01', '2022-12-31', resolution='1D')
    
    if df.empty:
        print("Lỗi: Không lấy được dữ liệu test.")
        return
        
    vsa = VSAIndicator(df)
    result = vsa.run_all()
    
    # Lọc ra những ngày có ĐÚNG 1 trong các tín hiệu VSA
    signals = result[(result['Stopping_Volume'] == True) | 
                     (result['Effort_vs_Result_Bearish'] == True) | 
                     (result['Spring'] == True)]
                     
    columns_to_show = ['Date', 'Close', 'Volume', 'Rel_Vol', 'Spread', 'Stopping_Volume', 'Effort_vs_Result_Bearish', 'Spring']
    
    print(f"\nĐã quét {len(df)} ngày giao dịch. Tìm thấy {len(signals)} ngày có tín hiệu VSA bùng nổ:\n")
    if not signals.empty:
        print(signals[columns_to_show].to_string(index=False))
    else:
        print("Không tìm thấy tín hiệu nào trong khoảng thời gian này.")

if __name__ == "__main__":
    test_vsa_signals()
