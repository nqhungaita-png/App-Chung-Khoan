import pandas as pd
import numpy as np

class VSAIndicator:
    def __init__(self, data: pd.DataFrame):
        """
        Khởi tạo VSA Indicator với dữ liệu OHLCV.
        :param data: pandas DataFrame chứa ['Open', 'High', 'Low', 'Close', 'Volume']
        """
        self.data = data.copy()
        
    def calculate_base_metrics(self):
        """
        Tính toán các metrics cơ bản cho VSA như Spread, Average Volume, và Relative Volume.
        """
        # Tính toán Spread (Biên độ nến)
        self.data['Spread'] = self.data['High'] - self.data['Low']
        self.data['Body'] = abs(self.data['Close'] - self.data['Open'])
        self.data['Lower_Tail'] = np.where(self.data['Close'] > self.data['Open'], 
                                           self.data['Open'] - self.data['Low'], 
                                           self.data['Close'] - self.data['Low'])
        self.data['Upper_Tail'] = np.where(self.data['Close'] > self.data['Open'], 
                                           self.data['High'] - self.data['Close'], 
                                           self.data['High'] - self.data['Open'])
        
        # Relative Volume (So với TB 20 phiên)
        self.data['Avg_Vol_20'] = self.data['Volume'].rolling(window=20).mean()
        self.data['Rel_Vol'] = self.data['Volume'] / self.data['Avg_Vol_20']
        
        # Đường MA20 và MA50 dùng làm bộ lọc xu hướng
        self.data['MA_20'] = self.data['Close'].rolling(window=20).mean()
        self.data['MA_50'] = self.data['Close'].rolling(window=50).mean()
        
        # Điền NaN cho các giá trị ban đầu nếu cần
        self.data['Rel_Vol'].fillna(0, inplace=True)
        return self.data
    
    def detect_stopping_volume(self):
        """
        Phát hiện Stopping Volume:
        (Close < Open) & (Volume > 2.0 * TB_20) & (Râu dưới >= 2*Thân nến)
        """
        condition = (
            (self.data['Close'] < self.data['Open']) & 
            (self.data['Rel_Vol'] > 2.0) & 
            (self.data['Lower_Tail'] >= 2 * self.data['Body'])
        )
        self.data['Stopping_Volume'] = condition
        return self.data

    def detect_effort_vs_result(self, small_spread_threshold=0.015):
        """
        Phát hiện Effort vs Result Bearish (Dấu hiệu Buying Climax):
        Nến tăng với khối lượng lớn nhưng biên độ giá hẹp.
        """
        condition = (
            (self.data['Close'] > self.data['Open']) & 
            (self.data['Rel_Vol'] > 2.0) & 
            ((self.data['Spread'] / self.data['Close']) < small_spread_threshold)
        )
        self.data['Effort_vs_Result_Bearish'] = condition
        return self.data
        
    def detect_squat_bar(self, small_spread_threshold=0.015):
        """
        Phát hiện Squat Bar / Effort vs Result Bullish:
        Nến giảm (Close < Open) với khối lượng lớn nhưng biên độ giá hẹp (Lực bán bị hấp thụ).
        """
        condition = (
            (self.data['Close'] < self.data['Open']) & 
            (self.data['Rel_Vol'] > 1.5) & 
            ((self.data['Spread'] / self.data['Close']) < 0.02)
        )
        self.data['Squat_Bar'] = condition
        return self.data

    def detect_spring(self, lookback=20):
        """
        Spring Detection: Giá phá đáy hỗ trợ cũ sau đó hồi phục trong phiên với khối lượng lớn.
        (Minh họa cơ bản: Giá Low xuyên thủng Min Low(20) nhưng Close lại kéo lên trên Min Low đó)
        """
        self.data['Min_Low_20'] = self.data['Low'].shift(1).rolling(window=lookback).min()
        condition = (
            (self.data['Low'] < self.data['Min_Low_20']) & 
            (self.data['Close'] > self.data['Min_Low_20']) & 
            (self.data['Rel_Vol'] > 1.5) # Khối lượng tăng đột biến
        )
        self.data['Spring'] = condition
        return self.data

    def detect_sos(self):
        """
        Sign of Strength (SOS) - Tách biệt mSOS và JAC:
        - mSOS (Minor SOS): Vượt đỉnh 20 ngày, Vol > 1.5, Close >= 0.6
        - JAC (Major SOS / Jump Across Creek): Vượt đỉnh 60 ngày, Vol > 2.0, Close >= 0.6
        """
        highest_high_20 = self.data['High'].shift(1).rolling(window=20).max()
        highest_high_60 = self.data['High'].shift(1).rolling(window=60).max()
        
        # Tính tỷ lệ vị trí giá Đóng cửa so với toàn bộ biên độ nến
        candle_range = self.data['High'] - self.data['Low'] + 1e-6
        close_position = (self.data['Close'] - self.data['Low']) / candle_range
        
        condition_msos = (
            (self.data['Close'] > self.data['Open']) &
            (self.data['Close'] > highest_high_20) &
            (self.data['Close'] <= highest_high_60) & # Chỉ là mSOS nếu chưa vượt đỉnh 60 ngày
            (self.data['Volume'] > 1.5 * self.data['Avg_Vol_20']) &
            (close_position >= 0.6)
        )
        
        condition_jac = (
            (self.data['Close'] > self.data['Open']) &
            (self.data['Close'] > highest_high_60) &
            (self.data['Volume'] > 2.0 * self.data['Avg_Vol_20']) &
            (close_position >= 0.6)
        )
        
        self.data['mSOS'] = condition_msos
        self.data['JAC'] = condition_jac
        
        # Giữ lại biến SOS (bằng JAC hoặc mSOS) để tương thích lùi nếu cần
        self.data['SOS'] = condition_msos | condition_jac
        return self.data

    def detect_utad(self):
        """
        Upthrust After Distribution (UTAD):
        - Giá High vượt đỉnh 20 ngày (Breakout ảo)
        - Đóng cửa bị ép xuống 40% phần dưới của thân nến (Close position <= 0.4)
        - Khối lượng bán mạnh (Volume > 1.5 * Avg_Vol_20)
        """
        highest_high_20 = self.data['High'].shift(1).rolling(window=20).max()
        
        candle_range = self.data['High'] - self.data['Low'] + 1e-6
        close_position = (self.data['Close'] - self.data['Low']) / candle_range
        
        condition = (
            (self.data['High'] > highest_high_20) &
            (self.data['Volume'] > 1.5 * self.data['Avg_Vol_20']) &
            (close_position <= 0.4)
        )
        self.data['UTAD'] = condition
        return self.data

    def detect_choch(self):
        """
        ChoCH (Change of Character) - Tín hiệu Pha D (Wyckoff):
        - Giá phá vỡ đỉnh gần nhất (highest_high_20) với khối lượng lớn (>1.5 lần trung bình).
        - Trước đó cổ phiếu phải có thời gian tích lũy hoặc giảm (Tối thiểu 10/20 phiên trước đó nằm dưới MA50).
        - Đánh dấu sự thay đổi thuộc tính từ Downtrend/Sideways sang Uptrend.
        """
        highest_high_20 = self.data['High'].shift(1).rolling(window=20).max()
        
        # Đếm số phiên nằm dưới MA50 trong 20 phiên trước đó
        below_ma50_count = (self.data['Close'] < self.data['MA_50']).rolling(window=20).sum().shift(1)
        
        condition = (
            (self.data['Close'] > self.data['Open']) &
            (self.data['Close'] > highest_high_20) &
            (self.data['Volume'] > 1.5 * self.data['Avg_Vol_20']) &
            (below_ma50_count >= 10)
        )
        self.data['ChoCH'] = condition
        return self.data

    def detect_no_supply(self):
        """
        No Supply (LPS) - Pha D/E:
        - Xảy ra trong xu hướng tăng (Close > MA_20 và Close > MA_50)
        - Phải là nến Đỏ (Close <= Open) thể hiện nhịp kéo ngược.
        - Râu nến dưới (Low) phải quét sát về dải hỗ trợ MA20 (Biên độ 2%)
        - Khối lượng cạn kiệt (Volume < 0.8 * Avg_Vol_20)
        """
        condition = (
            (self.data['Close'] > self.data['MA_20']) &
            (self.data['Close'] > self.data['MA_50']) &
            (self.data['Close'] <= self.data['Open']) &
            (self.data['Low'] <= self.data['MA_20'] * 1.02) &
            (self.data['Volume'] < 0.8 * self.data['Avg_Vol_20']) &
            (self.data['Spread'] < self.data['Spread'].rolling(20).mean())
        )
        self.data['No_Supply'] = condition
        return self.data

    def detect_no_demand(self):
        """
        No Demand (Test Cầu) - Pha Xả:
        - Đang trong xu hướng giảm (Close < MA_20)
        - Nến Tăng (Close > Open)
        - Giá cao nhất chạm/gần dải kháng cự MA20 (High >= MA_20 * 0.98)
        - Khối lượng cạn kiệt (Volume < 0.8 * Avg_Vol_20)
        """
        condition = (
            (self.data['Close'] < self.data['MA_20']) &
            (self.data['Close'] > self.data['Open']) &
            (self.data['High'] >= self.data['MA_20'] * 0.98) &
            (self.data['Volume'] < 0.8 * self.data['Avg_Vol_20']) &
            (self.data['Spread'] < self.data['Spread'].rolling(20).mean())
        )
        self.data['No_Demand'] = condition
        return self.data

    def detect_order_block_and_poe(self):
        """
        Nhận diện Vùng Cầu (Demand Zone / Order Block) và Điểm Vào Lệnh (POE).
        - Order Block: Cây nến giảm cuối cùng trước tín hiệu JAC (BOS).
        - POE: Giá hồi về chạm Order Block và có xác nhận VSA (Spring, Squat, Stopping Vol, No Supply).
        """
        dz_highs = [np.nan]
        dz_lows = [np.nan]
        
        last_dz_high = np.nan
        last_dz_low = np.nan
        
        for i in range(1, len(self.data)):
            # Cập nhật Order block khi có JAC
            if self.data['JAC'].iloc[i]:
                for j in range(i-1, max(-1, i-20), -1):
                    if self.data['Close'].iloc[j] < self.data['Open'].iloc[j]:
                        last_dz_high = self.data['High'].iloc[j]
                        last_dz_low = self.data['Low'].iloc[j]
                        break
            
            # Xóa Order block nếu giá đóng cửa thủng vùng này (Mitigated/Failed)
            if pd.notna(last_dz_low) and self.data['Close'].iloc[i] < last_dz_low:
                last_dz_high = np.nan
                last_dz_low = np.nan
                
            dz_highs.append(last_dz_high)
            dz_lows.append(last_dz_low)
            
        self.data['Demand_Zone_High'] = dz_highs
        self.data['Demand_Zone_Low'] = dz_lows
        
        has_vsa_confirmation = (
            self.data['Spring'] | 
            self.data['Squat_Bar'] | 
            self.data['Stopping_Volume'] | 
            self.data['No_Supply']
        )
        
        touch_demand_zone = (self.data['Low'] <= self.data['Demand_Zone_High']) & (self.data['High'] >= self.data['Demand_Zone_Low'])
        
        self.data['POE'] = touch_demand_zone & has_vsa_confirmation
        return self.data

    def calculate_macd(self):
        # MACD: 12-period EMA - 26-period EMA
        ema12 = self.data['Close'].ewm(span=12, adjust=False).mean()
        ema26 = self.data['Close'].ewm(span=26, adjust=False).mean()
        self.data['MACD'] = ema12 - ema26
        # Signal line: 9-period EMA of MACD
        self.data['MACD_Signal'] = self.data['MACD'].ewm(span=9, adjust=False).mean()
        self.data['MACD_Hist'] = self.data['MACD'] - self.data['MACD_Signal']

    def calculate_rsi(self, window=14):
        delta = self.data['Close'].diff()
        # Tính theo công thức trung bình di chuyển đơn giản (SMA) của gain/loss
        gain = delta.clip(lower=0).rolling(window=window).mean()
        loss = -delta.clip(upper=0).rolling(window=window).mean()
        # Để tránh chia cho 0
        rs = gain / loss
        self.data['RSI'] = 100 - (100 / (1 + rs))

    def calculate_ichimoku(self):
        # Tenkan-sen (Conversion Line): (9-period high + 9-period low)/2
        high_9 = self.data['High'].rolling(window=9).max()
        low_9 = self.data['Low'].rolling(window=9).min()
        self.data['Tenkan'] = (high_9 + low_9) / 2

        # Kijun-sen (Base Line): (26-period high + 26-period low)/2
        high_26 = self.data['High'].rolling(window=26).max()
        low_26 = self.data['Low'].rolling(window=26).min()
        self.data['Kijun'] = (high_26 + low_26) / 2

        # Senkou Span A (Leading Span A): (Tenkan + Kijun)/2 (Dịch về tương lai 26 phiên)
        self.data['Senkou_A'] = ((self.data['Tenkan'] + self.data['Kijun']) / 2).shift(26)

        # Senkou Span B (Leading Span B): (52-period high + 52-period low)/2 (Dịch về tương lai 26 phiên)
        high_52 = self.data['High'].rolling(window=52).max()
        low_52 = self.data['Low'].rolling(window=52).min()
        self.data['Senkou_B'] = ((high_52 + low_52) / 2).shift(26)

    def run_all(self):
        self.calculate_base_metrics()
        self.detect_stopping_volume()
        self.detect_effort_vs_result()
        self.detect_squat_bar()
        self.detect_spring()
        self.detect_sos()
        self.detect_choch()
        self.detect_utad()
        self.detect_no_supply()
        self.detect_no_demand()
        self.detect_order_block_and_poe()
        # Thêm các chỉ báo Kỹ thuật truyền thống
        self.calculate_macd()
        self.calculate_rsi()
        self.calculate_ichimoku()
        return self.data
