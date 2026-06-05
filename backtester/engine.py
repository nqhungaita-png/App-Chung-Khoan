import pandas as pd
import numpy as np

class BacktestEngine:
    def __init__(self, analyzed_df, max_holding_days=20, risk_reward_ratio=2.0, stop_loss_buffer=3.0, trend_filter=False, buy_signal_type="Spring", use_atr_trailing=False):
        """
        Khởi tạo Backtester.
        :param analyzed_df: DataFrame đã chạy qua VSAIndicator.
        :param max_holding_days: Số ngày cầm tối đa (T+20).
        :param risk_reward_ratio: Tỷ lệ Chốt lời / Cắt lỗ (RR).
        :param stop_loss_buffer: Biên độ đệm cắt lỗ (%).
        :param trend_filter: Chỉ mua khi Giá > MA50.
        :param buy_signal_type: Chiến thuật ("Spring", "SOS", "LPS (No Supply)").
        :param use_atr_trailing: Bật chế độ chốt lời động 2x ATR.
        """
        self.df = analyzed_df.copy().reset_index(drop=True)
        # Tính ATR (Average True Range) 14 phiên nếu df không rỗng
        if not self.df.empty and 'High' in self.df.columns:
            self.df['TR'] = np.maximum(
                self.df['High'] - self.df['Low'],
                np.maximum(
                    abs(self.df['High'] - self.df['Close'].shift(1)),
                    abs(self.df['Low'] - self.df['Close'].shift(1))
                )
            )
            self.df['ATR'] = self.df['TR'].rolling(window=14).mean().fillna(0)
        else:
            self.df['ATR'] = 0
        
        self.max_holding_days = max_holding_days
        self.rr_ratio = risk_reward_ratio
        self.sl_buffer = stop_loss_buffer / 100.0
        self.trend_filter = trend_filter
        self.buy_signal_type = buy_signal_type
        self.use_atr_trailing = use_atr_trailing
        
    def run_backtest(self):
        trades = []
        n = len(self.df)
        
        for i in range(n - 1):
            # Tuỳ chọn tín hiệu mua theo trường phái Wyckoff
            signal = False
            if self.buy_signal_type == "Spring":
                signal = self.df.loc[i, 'Spring']
            elif self.buy_signal_type == "SOS":
                signal = self.df.loc[i, 'SOS']
            elif self.buy_signal_type == "mSOS":
                signal = self.df.loc[i, 'mSOS']
            elif self.buy_signal_type == "JAC":
                signal = self.df.loc[i, 'JAC']
            elif self.buy_signal_type == "UTAD":
                signal = self.df.loc[i, 'UTAD']
            elif self.buy_signal_type == "LPS (No Supply)":
                signal = self.df.loc[i, 'No_Supply']
            elif self.buy_signal_type == "No Demand (Test Cầu)":
                signal = self.df.loc[i, 'No_Demand']
            elif self.buy_signal_type == "Squat Bar (Đỡ giá)":
                signal = self.df.loc[i, 'Squat_Bar']
            elif self.buy_signal_type == "POE (Vào lệnh tại Vùng Cầu - SMC)":
                signal = self.df.loc[i, 'POE']
            elif self.buy_signal_type == "ChoCH":
                signal = self.df.loc[i, 'ChoCH']
                
            if signal:
                
                # Áp dụng bộ lọc xu hướng: Smart Filter (Long vs Short)
                if self.trend_filter:
                    is_short_strategy = self.buy_signal_type in ["UTAD (Phân phối đỉnh - Đánh Short)", "No Demand (Test Cầu ở đỉnh - Đánh Short)", "UTAD", "No Demand (Test Cầu)"]
                    if is_short_strategy:
                        # Đánh Short: Bắt buộc giá phải nằm DƯỚI MA50 (Downtrend)
                        if self.df.loc[i, 'Close'] >= self.df.loc[i, 'MA_50']:
                            continue
                    else:
                        # Đánh Long: Bắt buộc giá phải nằm TRÊN MA50 (Uptrend)
                        if self.df.loc[i, 'Close'] <= self.df.loc[i, 'MA_50']:
                            continue
                            
                entry_idx = i + 1  # Mua ở phiên mở cửa ngày hôm sau
                if entry_idx >= n:
                    break
                    
                entry_date = self.df.loc[entry_idx, 'Date']
                entry_price = self.df.loc[entry_idx, 'Open']
                
                is_short = (self.buy_signal_type in ["UTAD", "No Demand (Test Cầu)"])
                
                if not is_short:
                    # Lệnh MUA (Long)
                    stop_loss_price = self.df.loc[i, 'Low'] * (1 - self.sl_buffer)
                    if entry_price <= stop_loss_price:
                        continue
                    risk_per_share = entry_price - stop_loss_price
                    take_profit_price = entry_price + (risk_per_share * self.rr_ratio)
                else:
                    # Lệnh BÁN KHỐNG (Short)
                    stop_loss_price = self.df.loc[i, 'High'] * (1 + self.sl_buffer)
                    if entry_price >= stop_loss_price:
                        continue
                    risk_per_share = stop_loss_price - entry_price
                    take_profit_price = entry_price - (risk_per_share * self.rr_ratio)
                
                # Biến theo dõi lệnh
                sell_date = None
                sell_price = 0
                exit_reason = ""
                
                # Biến cho ATR Trailing Stop
                if self.use_atr_trailing and not is_short:
                    current_trailing_stop = entry_price - 2 * self.df.loc[i, 'ATR']
                    highest_price_since_entry = entry_price
                else:
                    current_trailing_stop = None
                    highest_price_since_entry = None
                
                # Mô phỏng các ngày tiếp theo
                for j in range(entry_idx, min(entry_idx + self.max_holding_days, n)):
                    current_low = self.df.loc[j, 'Low']
                    current_high = self.df.loc[j, 'High']
                    current_close = self.df.loc[j, 'Close']
                    current_date = self.df.loc[j, 'Date']
                    
                    # Kiểm tra cắt lỗ và chốt lời theo loại lệnh
                    if not is_short:
                        if self.use_atr_trailing:
                            # 1. Kiểm tra xem giá Low hôm nay có chạm ngưỡng Trailing Stop của ngày hôm trước không
                            if current_low <= current_trailing_stop:
                                sell_date = current_date
                                sell_price = current_trailing_stop
                                exit_reason = "ATR Trailing Stop"
                                break
                            
                            # 2. Nếu không bị chạm, cập nhật Trailing Stop mới cho ngày mai dựa trên giá High hôm nay
                            highest_price_since_entry = max(highest_price_since_entry, current_high)
                            new_trailing_stop = highest_price_since_entry - 2 * self.df.loc[j, 'ATR']
                            current_trailing_stop = max(current_trailing_stop, new_trailing_stop)
                        else:
                            if current_low <= stop_loss_price:
                                sell_date = current_date
                                sell_price = stop_loss_price
                                exit_reason = "Stop-loss"
                                break
                            if current_high >= take_profit_price:
                                sell_date = current_date
                                sell_price = take_profit_price
                                exit_reason = "Take-profit"
                                break
                    else:
                        if current_high >= stop_loss_price:
                            sell_date = current_date
                            sell_price = stop_loss_price
                            exit_reason = "Stop-loss (Short)"
                            break
                        if current_low <= take_profit_price:
                            sell_date = current_date
                            sell_price = take_profit_price
                            exit_reason = "Take-profit (Short)"
                            break
                        
                    # Nếu giữ đến ngày cuối cùng của max_holding_days
                    if j == entry_idx + self.max_holding_days - 1:
                        sell_date = current_date
                        sell_price = current_close
                        exit_reason = "Time-stop (T+20)"
                        break
                        
                # Nếu lệnh chưa được đóng nhưng hết dữ liệu (đang gồng lãi/lỗ ở hiện tại)
                if sell_date is None:
                    sell_date = self.df.loc[n-1, 'Date']
                    sell_price = self.df.loc[n-1, 'Close']
                    exit_reason = "Đang giữ (Unrealized)"
                    
                # Tính PnL
                if not is_short:
                    pnl_pct = ((sell_price - entry_price) / entry_price) * 100
                else:
                    pnl_pct = ((entry_price - sell_price) / entry_price) * 100
                
                trades.append({
                    'Ngày Tín Hiệu': self.df.loc[i, 'Date'].strftime('%Y-%m-%d'),
                    'Ngày Mua': entry_date.strftime('%Y-%m-%d'),
                    'Giá Mua': round(entry_price, 2),
                    'Giá Cắt Lỗ': round(stop_loss_price, 2),
                    'Giá Chốt Lời': round(take_profit_price, 2),
                    'Ngày Bán': sell_date.strftime('%Y-%m-%d'),
                    'Giá Bán': round(sell_price, 2),
                    'Lý do Bán': exit_reason,
                    'Lợi nhuận (%)': round(pnl_pct, 2)
                })
                
        return pd.DataFrame(trades)
        
    def get_summary(self, trades_df):
        if trades_df.empty:
            return None
            
        completed_trades = trades_df[trades_df['Lý do Bán'] != 'Đang giữ (Unrealized)']
        if completed_trades.empty:
            return None
            
        total_trades = len(completed_trades)
        winning_trades = len(completed_trades[completed_trades['Lợi nhuận (%)'] > 0])
        win_rate = (winning_trades / total_trades) * 100
        
        avg_pnl = completed_trades['Lợi nhuận (%)'].mean()
        total_return = completed_trades['Lợi nhuận (%)'].sum()
        
        return {
            'Tổng số lệnh': total_trades,
            'Số lệnh thắng': winning_trades,
            'Tỷ lệ thắng (Win Rate)': f"{win_rate:.1f}%",
            'Tổng lợi nhuận (Cộng dồn)': f"{total_return:.2f}%",
            'Lợi nhuận trung bình / lệnh': f"{avg_pnl:.2f}%"
        }
