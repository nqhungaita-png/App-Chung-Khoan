import pandas as pd
from datetime import datetime, timedelta
import logging
import time
import vnstock
import sys

# Bắt buộc xuất log tiếng Việt bằng UTF-8 để vnstock in dấu tick không bị lỗi
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# Cấu hình API Key (Gói Community - 60 request/phút)
vnstock.change_api_key('vnstock_9ccd41fbaa83da86f5d5b985841012f5')

from data_feed.vnstock_feed import VNStockDataFeed
from indicators.vsa import VSAIndicator

logger = logging.getLogger(__name__)

# Danh sách VN30 giả định (có thể lấy động từ API vnstock nhưng fix cứng để tối ưu tốc độ)
VN30_SYMBOLS = [
    'ACB', 'BCM', 'BID', 'BVH', 'CTG', 'FPT', 'GAS', 'GVR', 'HDB', 'HPG', 
    'MBB', 'MSN', 'MWG', 'PLX', 'POW', 'SAB', 'SHB', 'SSB', 'SSI', 'STB', 
    'TCB', 'TPB', 'VCB', 'VHM', 'VIB', 'VIC', 'VJC', 'VNM', 'VPB', 'VRE'
]

SECTORS_MAP = {
    "Ngân hàng": ["VCB", "BID", "CTG", "TCB", "MBB", "VPB", "ACB", "STB", "SHB", "HDB", "TPB", "VIB", "LPB", "MSB", "OCB", "SSB", "EIB"],
    "Chứng khoán": ["SSI", "VND", "VCI", "HCM", "SHS", "VIX", "MBS", "FTS", "BSI", "CTS"],
    "Bất động sản": ["VHM", "VIC", "VRE", "NVL", "PDR", "DIG", "DXG", "KDH", "NLG", "CEO", "HDC"],
    "Thép": ["HPG", "HSG", "NKG", "SMC", "POM", "VGS"],
    "Bán lẻ": ["MWG", "PNJ", "FRT", "DGW", "PET"],
    "Dầu khí": ["GAS", "PVD", "PVS", "BSR", "PLX", "OIL", "PVC"],
    "Xây dựng & Đầu tư công": ["VCG", "HHV", "KSB", "LCG", "FCN", "C4G", "HUT"],
    "Khu Công nghiệp": ["BCM", "IDC", "KBC", "VGC", "SZC", "PHR"],
    "Thủy sản": ["VHC", "ANV", "IDI", "FMC", "ASM"],
    "Hóa chất & Phân bón": ["DGC", "DPM", "DCM", "CSV", "LAS"],
    "Cảng biển & Vận tải": ["GMD", "HAH", "VOS", "PVT", "VIP"],
    "Công nghệ & Viễn thông": ["FPT", "CMG", "ELC", "CTR", "VGI", "FOX"],
    "UPCOM Chọn Lọc (Thanh khoản cao)": ["BSR", "VEA", "VGI", "ACV", "MCH", "QNS", "FOX", "VTP", "LTG", "DDV", "C4G", "SBS", "AAS"]
}

class MarketScanner:
    def __init__(self, symbols=VN30_SYMBOLS):
        self.symbols = symbols
        self.feed = VNStockDataFeed(retries=2, backoff_factor=1)
        self.vnindex_status = "Chưa rõ"
        self.vnindex_data = None

    def scan_market(self, lookback_days=40, progress_callback=None):
        """
        Quét danh sách các mã để tìm tín hiệu VSA trong ngày giao dịch gần nhất.
        :param lookback_days: Số ngày lịch sử cần tải (đủ để tính MA20)
        :param progress_callback: Hàm callback để cập nhật thanh tiến trình trên Streamlit
        """
        end_date = datetime.today().strftime('%Y-%m-%d')
        start_date = (datetime.today() - timedelta(days=lookback_days)).strftime('%Y-%m-%d')
        
        # --- Lấy dữ liệu VNINDEX để đo lường Vĩ mô ---
        if progress_callback: progress_callback(0, len(self.symbols), "VNINDEX (Tính toán Vĩ mô)")
        try:
            df_vni = self.feed.fetch_historical_data('VNINDEX', start_date, end_date, resolution='1D')
            if not df_vni.empty and len(df_vni) > 20:
                df_vni['MA20'] = df_vni['Close'].rolling(window=20).mean()
                df_vni['MA50'] = df_vni['Close'].rolling(window=50).mean()
                last_vni = df_vni.iloc[-1]
                if last_vni['Close'] > last_vni['MA20'] and last_vni['Close'] > last_vni['MA50']:
                    self.vnindex_status = "🟢 Tốt (Uptrend)"
                elif last_vni['Close'] < last_vni['MA20'] and last_vni['Close'] < last_vni['MA50']:
                    self.vnindex_status = "🔴 Rủi ro (Downtrend)"
                else:
                    self.vnindex_status = "🟡 Trung tính (Sideway)"
                self.vnindex_data = df_vni
        except Exception as e:
            logger.error(f"Lỗi tải VNINDEX: {e}")

        results = []
        total = len(self.symbols)
        
        for idx, symbol in enumerate(self.symbols):
            try:
                # Tải dữ liệu
                df = self.feed.fetch_historical_data(symbol, start_date, end_date, resolution='1D')
                if not df.empty and len(df) >= 20: # Cần ít nhất 20 phiên để tính Rel_Vol
                    # Chạy VSA
                    vsa = VSAIndicator(df)
                    analyzed_df = vsa.run_all()
                    
                    # Lấy ngày cuối cùng (ngày giao dịch mới nhất)
                    last_day = analyzed_df.iloc[-1]
                    
                    has_signal = (
                        last_day.get('Spring', False) or 
                        last_day.get('Stopping_Volume', False) or 
                        last_day.get('Effort_vs_Result_Bearish', False) or
                        last_day.get('Effort_vs_Result_Bullish', False) or
                        last_day.get('Squat_Bar', False) or
                        last_day.get('mSOS', False) or
                        last_day.get('JAC', False) or
                        last_day.get('ChoCH', False) or
                        last_day.get('UTAD', False) or
                        last_day.get('No_Supply', False) or
                        last_day.get('No_Demand', False) or
                        last_day.get('POE', False)
                    )
                    
                    if has_signal:
                        signals_found = []
                        if last_day.get('Spring', False): signals_found.append("Spring (Pha C)")
                        if last_day.get('Stopping_Volume', False): signals_found.append("Stopping Vol")
                        if last_day.get('Squat_Bar', False): signals_found.append("Squat Bar (Đỡ giá)")
                        if last_day.get('Effort_vs_Result_Bearish', False): signals_found.append("Buying Climax")
                        if last_day.get('Effort_vs_Result_Bullish', False): signals_found.append("Selling Climax")
                        if last_day.get('mSOS', False): signals_found.append("mSOS (Vượt đỉnh phụ)")
                        if last_day.get('JAC', False): signals_found.append("JAC (Major SOS - Vượt con lạch)")
                        if last_day.get('ChoCH', False): signals_found.append("ChoCH (Đảo chiều xu hướng)")
                        if last_day.get('UTAD', False): signals_found.append("UTAD (Bẫy Tăng Giá - Báo Bão)")
                        if last_day.get('No_Supply', False): signals_found.append("LPS / No Supply (Test Cung)")
                        if last_day.get('No_Demand', False): signals_found.append("No Demand (Test Cầu - Báo Bão)")
                        if last_day.get('POE', False): signals_found.append("POE (Điểm vào lệnh tại Vùng Cầu)")
                        
                        # Xác định xu hướng
                        trend_status = "🟢 Uptrend" if last_day['Close'] > last_day.get('MA_50', 0) else "🔴 Downtrend"
                        
                        # Lấy tin tức nổi bật nếu có tín hiệu để lọc nhiễu
                        news_summary = "Không có"
                        try:
                            from vnstock.api.company import Company
                            df_news = Company(source='VCI', symbol=symbol).news()
                            if df_news is not None and not df_news.empty and 'news_title' in df_news.columns:
                                top_news = df_news['news_title'].head(3).tolist()
                                news_summary = " | ".join(top_news)
                        except Exception as e:
                            safe_err = str(e).encode('ascii', 'ignore').decode('ascii')
                            logger.error(f"Loi tai tin tuc {symbol}: {safe_err}")

                        # Tính điểm RS (Relative Strength) so với VNINDEX
                        rs_score = "N/A"
                        if self.vnindex_data is not None and not self.vnindex_data.empty:
                            vni_start = self.vnindex_data['Close'].iloc[0]
                            vni_end = self.vnindex_data['Close'].iloc[-1]
                            vni_ret = (vni_end - vni_start) / vni_start
                            
                            sym_start = df['Close'].iloc[0]
                            sym_end = df['Close'].iloc[-1]
                            sym_ret = (sym_end - sym_start) / sym_start
                            
                            rs_val = (sym_ret - vni_ret) * 100
                            if rs_val > 0:
                                rs_score = f"🟢 Khỏe (+{rs_val:.1f}%)"
                            else:
                                rs_score = f"🔴 Yếu ({rs_val:.1f}%)"

                        results.append({
                            'Mã': symbol,
                            'Ngày': last_day['Date'].strftime('%Y-%m-%d'),
                            'Giá đóng cửa': last_day['Close'],
                            'Giá thấp nhất': last_day['Low'],
                            'Xu hướng (MA50)': trend_status,
                            'Tín hiệu': ', '.join(signals_found),
                            'Sức mạnh (RS)': rs_score,
                            'Khối lượng': f"{int(last_day['Volume']):,}",
                            'Đột biến Vol': f"{last_day['Rel_Vol']:.2f}x",
                            'Tin tức mới nhất': news_summary
                        })
            except Exception as e:
                # Ép kiểu lỗi về string ascii để tránh lỗi charmap trên Windows
                safe_error = str(e).encode('ascii', 'ignore').decode('ascii')
                logger.error(f"Loi khi tai du lieu {symbol}: {safe_error}")
                
            # Cập nhật thanh tiến trình trên giao diện
            if progress_callback:
                progress_callback(idx + 1, total, symbol)
                
            # Tăng tốc độ bằng cách chỉ nghỉ 0.1s. Nếu chạm Rate Limit, hệ thống sẽ tự chờ 15s.
            time.sleep(0.1)
                
        return pd.DataFrame(results)

    def scan_sector_rotation(self, progress_callback=None):
        """Quét tất cả các mã để tính % Thay đổi và Sức mạnh tương đối (RS) cho Heatmap."""
        results = []
        end_date = datetime.now()
        start_date = end_date - timedelta(days=60)
        
        # Tải VNINDEX để tính RS
        vnindex_data = None
        try:
            vnindex_data = self.feed.fetch_historical_data('VNINDEX', start_date, end_date, resolution='1D', type='index')
        except Exception as e:
            logger.error(f"Lỗi tải VNINDEX trong scan_sector_rotation: {e}")

        total = len(self.symbols)
        for idx, symbol in enumerate(self.symbols):
            try:
                df = self.feed.fetch_historical_data(symbol, start_date, end_date, resolution='1D')
                if not df.empty and len(df) >= 20:
                    sym_start = df['Close'].iloc[0]
                    sym_end = df['Close'].iloc[-1]
                    sym_ret = ((sym_end - sym_start) / sym_start) * 100
                    
                    rs_val = 0
                    if vnindex_data is not None and not vnindex_data.empty:
                        vni_start = vnindex_data['Close'].iloc[0]
                        vni_end = vnindex_data['Close'].iloc[-1]
                        vni_ret = ((vni_end - vni_start) / vni_start) * 100
                        rs_val = sym_ret - vni_ret
                        
                    # Tìm sector
                    sector = "Khác"
                    for s_name, s_symbols in SECTORS_MAP.items():
                        if symbol in s_symbols:
                            sector = s_name
                            break
                            
                    results.append({
                        'Symbol': symbol,
                        'Sector': sector,
                        'PctChange': sym_ret,
                        'RS': rs_val,
                        'Close': sym_end,
                        'Volume': df['Volume'].iloc[-1]
                    })
            except Exception as e:
                pass
                
            if progress_callback:
                progress_callback(idx + 1, total, symbol)
            time.sleep(0.1)
            
        return pd.DataFrame(results)
