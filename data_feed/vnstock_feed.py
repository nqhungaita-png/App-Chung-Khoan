import pandas as pd
from vnstock.api.quote import Quote
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Bộ nhớ đệm (Cache) tạm thời trong phiên chạy để chống Rate Limit
_GLOBAL_CACHE = {}

class VNStockDataFeed:
    def __init__(self, retries=3, backoff_factor=15):
        """
        Khởi tạo Data Feed với cơ chế retry để đảm bảo tính ổn định.
        :param retries: Số lần thử lại tối đa nếu gọi API thất bại.
        :param backoff_factor: Hệ số thời gian chờ giữa các lần thử.
        """
        self.retries = retries
        self.backoff_factor = backoff_factor

    def fetch_historical_data(self, symbol, start_date, end_date, resolution='1D', type='stock'):
        """
        Lấy dữ liệu lịch sử với cơ chế retry, làm sạch cơ bản và Cache.
        """
        cache_key = f"{symbol}_{start_date}_{end_date}_{resolution}"
        if cache_key in _GLOBAL_CACHE:
            return _GLOBAL_CACHE[cache_key].copy()
            
        attempt = 0
        while attempt < self.retries:
            try:
                logger.info(f"Đang tải dữ liệu {symbol} (Độ phân giải: {resolution}) - Lần thử {attempt + 1}")
                # Sử dụng API mới của vnstock v4
                q = Quote(symbol=symbol, source='VCI')
                df = q.history(start=start_date, end=end_date, resolution=resolution)
                
                if df is not None and not df.empty:
                    df = self._clean_data(df)
                    
                    # Xử lý ATC nếu là dữ liệu intraday
                    if resolution != '1D':
                        df = self._tag_atc_session(df)
                        
                    logger.info(f"Tải dữ liệu {symbol} thành công. Kích thước: {df.shape}")
                    _GLOBAL_CACHE[cache_key] = df.copy()
                    return df
                else:
                    logger.warning(f"Dữ liệu trả về rỗng cho {symbol}.")
            except Exception as e:
                logger.error(f"Lỗi khi tải dữ liệu {symbol}: {e}")
            
            attempt += 1
            time.sleep(self.backoff_factor * attempt)
            
        logger.error(f"Không thể tải dữ liệu {symbol} sau {self.retries} lần thử.")
        return pd.DataFrame()

    def _clean_data(self, df):
        """
        Làm sạch dữ liệu cơ bản để đảm bảo chất lượng cho phân tích Wyckoff/VSA.
        """
        # Đảm bảo các cột tên chuẩn
        df.rename(columns={'time': 'Date', 'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}, inplace=True)
        
        # Chuyển đổi kiểu dữ liệu
        df['Date'] = pd.to_datetime(df['Date'])
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                
        # Loại bỏ các dòng có giá trị NaN (hoặc forward fill tuỳ chiến lược)
        df.dropna(subset=['Open', 'High', 'Low', 'Close', 'Volume'], inplace=True)
        
        # Sắp xếp lại theo thời gian
        df.sort_values('Date', inplace=True)
        df.reset_index(drop=True, inplace=True)
        return df

    def _tag_atc_session(self, df):
        """
        Gắn nhãn (tag) phiên ATC để loại trừ hoặc xử lý riêng biệt.
        Phiên ATC diễn ra từ 14:30 đến 14:45.
        """
        # Kiểm tra nếu Date có chứa giờ (intraday)
        if df['Date'].dt.time.nunique() > 1:
            df['Is_ATC'] = (df['Date'].dt.hour == 14) & (df['Date'].dt.minute >= 30)
            logger.info("Đã gắn nhãn dữ liệu phiên ATC cho intraday.")
        else:
            df['Is_ATC'] = False
            
        return df
