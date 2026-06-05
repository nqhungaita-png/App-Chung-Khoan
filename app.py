import sys
import os
import json
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import time
from datetime import datetime, timedelta

from data_feed.vnstock_feed import VNStockDataFeed
from indicators.vsa import VSAIndicator
from strategies.market_scanner import MarketScanner, VN30_SYMBOLS, SECTORS_MAP
from backtester.engine import BacktestEngine

# Bắt buộc xuất log tiếng Việt bằng UTF-8
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

st.set_page_config(page_title="Hệ Thống Phân Tích Chứng Khoán", layout="wide")
st.title("📈 Hệ Thống Phân Tích Chứng Khoán VSA")

WATCHLIST_FILE = "watchlist.json"

def load_watchlist():
    if os.path.exists(WATCHLIST_FILE):
        with open(WATCHLIST_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_watchlist(data):
    with open(WATCHLIST_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

PORTFOLIO_FILE = "portfolio.json"

def load_portfolio():
    if os.path.exists(PORTFOLIO_FILE):
        with open(PORTFOLIO_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_portfolio(data):
    with open(PORTFOLIO_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# Tạo 5 Tabs (Thêm Tab 5 cho Phái sinh)
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🔍 Phân Tích Cơ Sở", "🚀 Quét Thị Trường (VN30)", "🧪 Backtest", "💼 Quản Lý Danh Mục (Portfolio)", "⚡ Phái Sinh VN30F1M"])

with tab1:
    st.markdown("Hệ thống tự động lọc và đánh dấu các tín hiệu VSA trên biểu đồ giá.")
    
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        symbol = st.text_input("Mã chứng khoán:", "HPG").upper()
    with col2:
        end_default = datetime.today()
        start_default = end_default - timedelta(days=365)
        start_date = st.date_input("Từ ngày", start_default)
    with col3:
        end_date = st.date_input("Đến ngày", end_default)

    st.markdown("---")
    st.markdown("**Bật/Tắt các chỉ báo xác nhận (Tùy chọn):**")
    col_ind1, col_ind2, col_ind3 = st.columns(3)
    with col_ind1:
        show_ichimoku = st.checkbox("Mây Ichimoku", value=False)
    with col_ind2:
        show_macd = st.checkbox("MACD", value=False)
    with col_ind3:
        show_rsi = st.checkbox("RSI (14)", value=False)

    if st.button("Phân tích mã này"):
        with st.spinner(f'Đang lấy dữ liệu {symbol}...'):
            feed = VNStockDataFeed()
            df = feed.fetch_historical_data(
                symbol, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'), resolution='1D'
            )
            
            if df.empty:
                st.error("Không tìm thấy dữ liệu.")
            else:
                vsa_engine = VSAIndicator(df)
                result = vsa_engine.run_all()
                
                st.subheader(f"Biểu đồ giá {symbol}")
                
                # Tính số lượng subplot (số hàng)
                num_rows = 1
                row_heights = [0.6] if (show_macd or show_rsi) else [1.0]
                
                if show_macd:
                    num_rows += 1
                    row_heights.append(0.2 if show_rsi else 0.4)
                if show_rsi:
                    num_rows += 1
                    row_heights.append(0.2 if show_macd else 0.4)
                    
                # Khởi tạo Figure đa khung hình
                fig = make_subplots(rows=num_rows, cols=1, shared_xaxes=True, 
                                    vertical_spacing=0.03, row_heights=row_heights)
                
                # === Hàng 1: Đồ thị Giá ===
                fig.add_trace(go.Candlestick(x=result['Date'], open=result['Open'], high=result['High'], low=result['Low'], close=result['Close'], name="Giá"), row=1, col=1)
                
                # Vẽ MA20, MA50
                fig.add_trace(go.Scatter(x=result['Date'], y=result['MA_20'], mode='lines', line=dict(color='orange', width=1), name='MA20'), row=1, col=1)
                fig.add_trace(go.Scatter(x=result['Date'], y=result['MA_50'], mode='lines', line=dict(color='purple', width=1.5), name='MA50'), row=1, col=1)

                # Vẽ Ichimoku
                if show_ichimoku:
                    fig.add_trace(go.Scatter(x=result['Date'], y=result['Tenkan'], mode='lines', line=dict(color='#0496ff', width=1), name='Tenkan (9)'), row=1, col=1)
                    fig.add_trace(go.Scatter(x=result['Date'], y=result['Kijun'], mode='lines', line=dict(color='#99154e', width=1), name='Kijun (26)'), row=1, col=1)
                    fig.add_trace(go.Scatter(x=result['Date'], y=result['Senkou_A'], mode='lines', line=dict(width=0), showlegend=False, name='Senkou A'), row=1, col=1)
                    fig.add_trace(go.Scatter(x=result['Date'], y=result['Senkou_B'], mode='lines', line=dict(width=0), fill='tonexty', fillcolor='rgba(128, 128, 128, 0.2)', name='Kumo (Mây)'), row=1, col=1)

                # Vẽ các điểm nổ VSA
                springs = result[result['Spring'] == True]
                stopping_vols = result[result['Stopping_Volume'] == True]
                efforts = result[result['Effort_vs_Result_Bearish'] == True]
                msos_signals = result[result['mSOS'] == True]
                jac_signals = result[result['JAC'] == True]
                utad_signals = result[result['UTAD'] == True]
                lps_signals = result[result['No_Supply'] == True]
                no_demand_signals = result[result['No_Demand'] == True]
                squat_signals = result[result['Squat_Bar'] == True]
                poe_signals = result[result['POE'] == True]
                choch_signals = result[result['ChoCH'] == True]
                
                if not springs.empty:
                    fig.add_trace(go.Scatter(x=springs['Date'], y=springs['Low']*0.98, mode='markers', marker=dict(symbol='triangle-up', size=15, color='green'), name='VSA Spring (Pha C)'), row=1, col=1)
                if not stopping_vols.empty:
                    fig.add_trace(go.Scatter(x=stopping_vols['Date'], y=stopping_vols['Low']*0.97, mode='markers', marker=dict(symbol='triangle-up', size=15, color='blue'), name='Stopping Volume'), row=1, col=1)
                if not squat_signals.empty:
                    fig.add_trace(go.Scatter(x=squat_signals['Date'], y=squat_signals['Low']*0.98, mode='markers', marker=dict(symbol='triangle-up', size=12, color='cyan'), name='Squat Bar (Đỡ giá)'), row=1, col=1)
                if not efforts.empty:
                    fig.add_trace(go.Scatter(x=efforts['Date'], y=efforts['High']*1.02, mode='markers', marker=dict(symbol='triangle-down', size=15, color='red'), name='Effort vs Result (Bán)'), row=1, col=1)
                if not msos_signals.empty:
                    fig.add_trace(go.Scatter(x=msos_signals['Date'], y=msos_signals['Low']*0.98, mode='markers', marker=dict(symbol='star', size=10, color='pink'), name='mSOS (Vượt đỉnh phụ)'), row=1, col=1)
                if not jac_signals.empty:
                    fig.add_trace(go.Scatter(x=jac_signals['Date'], y=jac_signals['Low']*0.98, mode='markers', marker=dict(symbol='star', size=20, color='gold'), name='JAC (Major SOS - Vượt lạch)'), row=1, col=1)
                if not utad_signals.empty:
                    fig.add_trace(go.Scatter(x=utad_signals['Date'], y=utad_signals['High']*1.02, mode='markers', marker=dict(symbol='triangle-down', size=20, color='darkred'), name='UTAD (Bẫy Tăng Giá)'), row=1, col=1)
                if not lps_signals.empty:
                    fig.add_trace(go.Scatter(x=lps_signals['Date'], y=lps_signals['Low']*0.98, mode='markers', marker=dict(symbol='circle', size=10, color='orange'), name='LPS / No Supply (Pha E)'), row=1, col=1)
                if not no_demand_signals.empty:
                    fig.add_trace(go.Scatter(x=no_demand_signals['Date'], y=no_demand_signals['High']*1.02, mode='markers', marker=dict(symbol='circle', size=10, color='purple'), name='No Demand (Test Cầu)'), row=1, col=1)
                if not choch_signals.empty:
                    fig.add_trace(go.Scatter(x=choch_signals['Date'], y=choch_signals['Low']*0.98, mode='markers', marker=dict(symbol='hexagram', size=20, color='yellow'), name='ChoCH (Đảo chiều xu hướng)'), row=1, col=1)
                if not poe_signals.empty:
                    fig.add_trace(go.Scatter(x=poe_signals['Date'], y=poe_signals['Low']*0.96, mode='markers', marker=dict(symbol='diamond', size=25, color='mintcream', line=dict(color='black', width=2)), name='POE (Vào lệnh Vùng Cầu)'), row=1, col=1)

                # === Hàng phụ: MACD & RSI ===
                current_row = 2
                if show_macd:
                    colors = ['green' if val >= 0 else 'red' for val in result['MACD_Hist']]
                    fig.add_trace(go.Bar(x=result['Date'], y=result['MACD_Hist'], marker_color=colors, name='MACD Hist'), row=current_row, col=1)
                    fig.add_trace(go.Scatter(x=result['Date'], y=result['MACD'], mode='lines', line=dict(color='#2962FF', width=1.5), name='MACD'), row=current_row, col=1)
                    fig.add_trace(go.Scatter(x=result['Date'], y=result['MACD_Signal'], mode='lines', line=dict(color='#FF6D00', width=1.5), name='Signal'), row=current_row, col=1)
                    current_row += 1

                if show_rsi:
                    fig.add_trace(go.Scatter(x=result['Date'], y=result['RSI'], mode='lines', line=dict(color='purple', width=1.5), name='RSI'), row=current_row, col=1)
                    fig.add_hline(y=70, line_dash="dot", line_color="red", row=current_row, col=1)
                    fig.add_hline(y=30, line_dash="dot", line_color="green", row=current_row, col=1)
                    fig.update_yaxes(range=[0, 100], row=current_row, col=1)
                    current_row += 1

                fig.update_layout(xaxis_rangeslider_visible=False, height=800 if num_rows > 1 else 600, template='plotly_dark')
                st.plotly_chart(fig, use_container_width=True)
                
                # --- AI EXPERT ANALYSIS ---
                st.markdown("---")
                st.subheader("🤖 Trợ Lý AI Phân Tích (Tự Động)")
                last_row = result.iloc[-1]
                close_p = last_row['Close']
                ma20_v = last_row['MA_20']
                ma50_v = last_row['MA_50']
                rsi_v = last_row.get('RSI', 50)
                
                trend_status = "TĂNG" if close_p > ma50_v else "GIẢM"
                short_trend = "tích cực" if close_p > ma20_v else "tiêu cực"
                
                analysis = f"**1. Xu Hướng:** Cổ phiếu **{symbol}** đang trong xu hướng trung hạn **{trend_status}** (Giá {close_p:.2f} so với MA50 là {ma50_v:.2f}). Trong ngắn hạn, đồ thị đang **{short_trend}** do giá giao dịch quanh MA20 ({ma20_v:.2f}).\n\n"
                
                if rsi_v > 70:
                    analysis += f"**2. Động Lượng (RSI):** Đạt mức {rsi_v:.1f} (Quá Mua). Lực kéo đang rất nóng, rủi ro điều chỉnh cao, **không nên mua đuổi**.\n\n"
                elif rsi_v < 30:
                    analysis += f"**2. Động Lượng (RSI):** Đạt mức {rsi_v:.1f} (Quá Bán). Lực bán đã cạn kiệt, cổ phiếu đang ở vùng đáy ngắn hạn, có thể **canh bắt đáy**.\n\n"
                else:
                    analysis += f"**2. Động Lượng (RSI):** Mức {rsi_v:.1f} (Trung tính). Lực cung cầu đang cân bằng.\n\n"
                
                # Tìm VSA
                signals_today = []
                for col in ['Spring', 'Squat_Bar', 'mSOS', 'JAC', 'UTAD', 'No_Supply', 'No_Demand', 'POE', 'ChoCH']:
                    if col in result.columns and last_row[col]:
                        signals_today.append(col)
                        
                if signals_today:
                    analysis += f"**3. Dấu Chân Cá Mập (VSA):** 🔥 CẢNH BÁO MẠNH! Phiên hiện tại xuất hiện tín hiệu **{', '.join(signals_today)}**. Đây là dấu vết gom/xả hàng của dòng tiền lớn.\n\n"
                else:
                    recent_signals = []
                    for i in range(2, 6):
                        if i <= len(result):
                            row_i = result.iloc[-i]
                            for col in ['Spring', 'Squat_Bar', 'mSOS', 'JAC', 'UTAD', 'No_Supply', 'No_Demand', 'POE', 'ChoCH']:
                                if col in result.columns and row_i[col]:
                                    recent_signals.append(col)
                    if recent_signals:
                        analysis += f"**3. Dấu Chân Cá Mập (VSA):** Trong 5 phiên gần nhất có sự xuất hiện của dòng tiền lớn (**{', '.join(set(recent_signals))}**). Hãy đưa mã này vào danh sách theo dõi sát sao!\n\n"
                    else:
                        analysis += f"**3. Dấu Chân Cá Mập (VSA):** Chưa có dấu hiệu thu gom hay phân phối rõ ràng từ dòng tiền lớn trong các phiên gần đây.\n\n"
                
                st.info(analysis)
                
                st.subheader("Bảng dữ liệu chi tiết")
                cols_to_show = ['Date', 'Close', 'Volume', 'Rel_Vol', 'Spread', 'Spring', 'Stopping_Volume']
                st.dataframe(result[cols_to_show].sort_values('Date', ascending=False).head(50))
                
                # --- POSITION SIZING CALCULATOR ---
                st.markdown("---")
                st.subheader("⚖️ Máy tính Đi Lệnh & Quản trị Rủi Ro")
                col_ps1, col_ps2, col_ps3 = st.columns(3)
                with col_ps1:
                    capital = st.number_input("Tổng vốn giao dịch (VNĐ):", min_value=10_000_000, value=100_000_000, step=10_000_000)
                with col_ps2:
                    risk_pct = st.number_input("Rủi ro tối đa / Lệnh (%):", min_value=0.5, max_value=10.0, value=2.0, step=0.5)
                with col_ps3:
                    entry_p = st.number_input("Giá Mua (x1000):", min_value=1.0, value=float(result.iloc[-1]['Close']), step=0.1)
                    stop_p = st.number_input("Giá Cắt Lỗ (x1000):", min_value=0.1, value=float(result.iloc[-1]['Low']*0.95), step=0.1)
                
                if entry_p > stop_p:
                    risk_per_share = (entry_p - stop_p) * 1000
                    max_loss = capital * (risk_pct / 100.0)
                    shares_to_buy = int(max_loss / risk_per_share) if risk_per_share > 0 else 0
                    total_value = shares_to_buy * entry_p * 1000
                    st.info(f"💡 **Khuyến nghị đi lệnh:**\n- Số lượng mua an toàn: **{shares_to_buy:,} cổ phiếu**.\n- Tổng tiền đầu tư: **{total_value:,.0f} VNĐ**.\n- Nếu chạm cắt lỗ, bạn sẽ mất tối đa: **{max_loss:,.0f} VNĐ** (Chính xác {risk_pct}% tổng vốn).")
                else:
                    st.warning("⚠️ Giá Cắt Lỗ phải nhỏ hơn Giá Mua (Đối với lệnh Long)!")

with tab2:
    st.markdown("Tự động quét các mã cổ phiếu để tìm tín hiệu VSA bùng nổ trong phiên giao dịch gần nhất.")
    
    scan_mode = st.radio("Chọn danh mục quét:", ["VN30 (Mặc định)", "Theo Nhóm Ngành", "Danh mục tự chọn (Nhập tay)"], horizontal=True)
    custom_symbols_scan = []
    
    if scan_mode == "Theo Nhóm Ngành":
        selected_sector = st.selectbox("Chọn Ngành:", list(SECTORS_MAP.keys()))
        custom_symbols_scan = SECTORS_MAP[selected_sector]
        st.info(f"Các mã sẽ được quét ({len(custom_symbols_scan)} mã): {', '.join(custom_symbols_scan)}")
        
    elif scan_mode == "Danh mục tự chọn (Nhập tay)":
        custom_input_scan = st.text_input("Nhập các mã cổ phiếu cách nhau bởi dấu phẩy (VD: VND, DIG, PDR, HAG):", "VND, DIG, SSI, PDR")
        if custom_input_scan:
            custom_symbols_scan = [s.strip().upper() for s in custom_input_scan.split(',') if s.strip()]
            
    if st.button("Bắt đầu quét ngay"):
        if scan_mode == "VN30 (Mặc định)":
            symbols_to_scan = VN30_SYMBOLS
        else:
            symbols_to_scan = custom_symbols_scan
        
        if not symbols_to_scan:
            st.error("Vui lòng nhập ít nhất 1 mã cổ phiếu!")
        else:
            scanner = MarketScanner(symbols=symbols_to_scan)
            
            # Giao diện thanh tiến trình
        progress_text = "Đang khởi tạo trình quét..."
        my_bar = st.progress(0, text=progress_text)
        
        # Hàm callback để cập nhật thanh tiến trình từ bên trong MarketScanner
        def update_progress(current, total, symbol_name):
            percent = int((current / total) * 100)
            my_bar.progress(percent, text=f"Đang phân tích {symbol_name}... ({current}/{total})")
            
        st.info("Quá trình quét có thể mất khoảng 15-30 giây tuỳ thuộc vào tốc độ mạng, vui lòng không tắt tab.")
        
        # Chạy quét
        scan_results = scanner.scan_market(progress_callback=update_progress)
        st.session_state['scan_results'] = scan_results
        st.session_state['vnindex_status'] = scanner.vnindex_status
        
        my_bar.empty() # Xoá thanh tiến trình khi hoàn thành
        
    if 'scan_results' in st.session_state:
        scan_results = st.session_state['scan_results']
        vn_status = st.session_state.get('vnindex_status', 'Chưa rõ')
        
        # Hiển thị Vĩ mô
        if "Tốt" in vn_status:
            st.success(f"🚦 Trạng thái Vĩ mô (VN-INDEX): **{vn_status}** - Tín hiệu đáng tin cậy!")
        elif "Rủi ro" in vn_status:
            st.error(f"🚦 Trạng thái Vĩ mô (VN-INDEX): **{vn_status}** - Hạn chế mua mới, tỷ lệ xịt cao!")
        else:
            st.warning(f"🚦 Trạng thái Vĩ mô (VN-INDEX): **{vn_status}** - Thị trường đi ngang, mua tỷ trọng thấp.")

        if not scan_results.empty:
            st.success("🎉 Đã tìm thấy các mã có tín hiệu đáng chú ý hôm nay!")
            st.dataframe(scan_results, use_container_width=True)
            
            # --- TÍCH HỢP TELEGRAM BOT ---
            st.markdown("---")
            st.markdown("### 🚀 Bot Telegram - Cảnh Báo Real-Time")
            with st.expander("⚙️ Cấu hình Bot Telegram"):
                st.markdown("""
                **Hướng dẫn nhanh:**
                1. Lên Telegram tìm `@BotFather` và gõ `/newbot` để tạo Bot. Copy đoạn `HTTP API Token` (Dài lằng nhằng).
                2. Gõ `/start` vào con Bot vừa tạo.
                3. Tìm `@userinfobot` để lấy `Chat ID` (Là một dãy số, ví dụ `123456789`).
                4. Nhập Token và Chat ID vào dưới đây.
                """)
                tg_token = st.text_input("Nhập Telegram Bot Token:", value=st.session_state.get('tg_token', ''), type="password")
                tg_chat_id = st.text_input("Nhập Chat ID:", value=st.session_state.get('tg_chat_id', ''))
                
                if st.button("Lưu cấu hình Telegram"):
                    st.session_state['tg_token'] = tg_token
                    st.session_state['tg_chat_id'] = tg_chat_id
                    try:
                        with open("telegram_config.json", "w", encoding='utf-8') as f:
                            json.dump({"tg_token": tg_token, "tg_chat_id": tg_chat_id}, f)
                    except Exception:
                        pass
                    st.success("Đã lưu cấu hình vĩnh viễn (Hỗ trợ Bot chạy ngầm)!")
                    
            if st.button("Bắn tín hiệu vào Telegram 🚀", type="primary"):
                from utils.telegram import send_telegram_message
                token = st.session_state.get('tg_token', '')
                chat_id = st.session_state.get('tg_chat_id', '')
                if not token or not chat_id:
                    st.error("Vui lòng cấu hình Bot Token và Chat ID ở bên trên trước!")
                else:
                    # Format message
                    vn_status = st.session_state.get('vnindex_status', 'Chưa rõ')
                    msg = "🔥 <b>BÁO CÁO QUÉT THỊ TRƯỜNG VSA</b> 🔥\n"
                    msg += f"🚦 <b>VN-INDEX:</b> {vn_status}\n\n"
                    for _, row in scan_results.iterrows():
                        msg += f"<b>{row['Mã']}</b> | <b>{row['Tín hiệu']}</b>\n"
                        msg += f"💵 Giá: {row['Giá đóng cửa']} | Trend: {row['Xu hướng (MA50)']}\n"
                        rs_val = row.get('Sức mạnh (RS)', 'N/A')
                        msg += f"💪 Sức mạnh: {rs_val}\n"
                        news_val = row.get('Tin tức mới nhất', 'Không có')
                        msg += f"📰 Tin: <i>{news_val}</i>\n"
                        msg += "--------------------------------------\n"
                        
                    with st.spinner("Đang gửi qua Telegram..."):
                        success, info = send_telegram_message(token, chat_id, msg)
                        if success:
                            st.success(info)
                        else:
                            st.error(info)
            st.markdown("---")
            
            if st.button("Lưu các mã này vào Watchlist"):
                wl = load_watchlist()
                added = 0
                for idx, row in scan_results.iterrows():
                    symbol = row['Mã']
                    # Nếu chưa có trong danh sách thì thêm vào
                    if not any(item['Symbol'] == symbol for item in wl):
                        wl.append({
                            'Symbol': symbol,
                            'Date_Scanned': datetime.today().strftime('%Y-%m-%d'),
                            'Price_Scanned': float(row['Giá đóng cửa']),
                            'Low_Scanned': float(row['Giá thấp nhất']),
                            'Trend': row.get('Xu hướng (MA50)', 'Chưa rõ'),
                            'Signal': row['Tín hiệu']
                        })
                        added += 1
                save_watchlist(wl)
                st.success(f"Đã lưu thành công {added} mã mới vào danh sách theo dõi (Tab 4)!")
        else:
            st.warning("Hôm nay thị trường bình yên, không có mã VN30 nào xuất hiện tín hiệu VSA bùng nổ.")
            
        # --- BẢN ĐỒ LUÂN CHUYỂN DÒNG TIỀN (HEATMAP) ---
        st.markdown("---")
        st.markdown("### 🗺️ Bản Đồ Luân Chuyển Dòng Tiền (Sector Rotation)")
        if st.button("Tải Bản Đồ Dòng Tiền (Heatmap)"):
            hm_bar = st.progress(0, text="Khởi tạo dữ liệu...")
            def update_hm_progress(current, total, symbol_name):
                percent = int((current / total) * 100)
                hm_bar.progress(percent, text=f"Đang phân tích {symbol_name}... ({current}/{total})")
                
            with st.spinner("Đang phân tích sức mạnh các nhóm ngành... (Có thể mất 30s - 1 phút nếu mạng chậm)"):
                hm_scanner = MarketScanner(symbols=VN30_SYMBOLS)
                sector_df = hm_scanner.scan_sector_rotation(progress_callback=update_hm_progress)
                hm_bar.empty()
                if not sector_df.empty:
                    # Lọc bỏ các mã không có dữ liệu
                    sector_df = sector_df.dropna(subset=['PctChange', 'RS'])
                    # Vẽ Treemap
                    fig_tree = px.treemap(
                        sector_df, 
                        path=[px.Constant("Thị trường (VN30)"), 'Sector', 'Symbol'], 
                        values='Volume',
                        color='PctChange',
                        color_continuous_scale='RdYlGn',
                        color_continuous_midpoint=0,
                        hover_data=['RS', 'Close'],
                        title="Bản Đồ Dòng Tiền (Kích thước: Khối lượng | Màu sắc: % Tăng/Giảm)"
                    )
                    fig_tree.update_traces(textinfo="label+text+value")
                    fig_tree.update_layout(height=600, template='plotly_dark', margin=dict(t=50, l=25, r=25, b=25))
                    st.plotly_chart(fig_tree, use_container_width=True)
                else:
                    st.warning("Không thể tải dữ liệu bản đồ.")

with tab3:
    st.markdown("Kiểm tra hiệu quả của các **điểm mua Spring** trong quá khứ đối với một mã cổ phiếu cụ thể.")
    
    col_bt1, col_bt2, col_bt3, col_bt4 = st.columns(4)
    with col_bt1:
        bt_mode = st.radio("Danh mục Backtest:", ["VN30", "Nhập tay"], horizontal=True)
        if bt_mode == "VN30":
            bt_symbols_selected = st.multiselect(
                "Mã VN30:", 
                options=VN30_SYMBOLS, 
                default=VN30_SYMBOLS, 
                key="bt_symbols_select"
            )
        else:
            custom_input_bt = st.text_input("Nhập mã (cách nhau dấu phẩy):", "DIG, PDR, DXG, NVL")
            bt_symbols_selected = [s.strip().upper() for s in custom_input_bt.split(',') if s.strip()]
            
    with col_bt2:
        bt_rr = st.number_input("Tỷ lệ Chốt lời/Cắt lỗ (R:R)", min_value=1.0, max_value=10.0, value=2.0, step=0.5)
    with col_bt3:
        bt_buffer = st.number_input("Biên độ đệm Cắt lỗ (%)", min_value=0.0, max_value=10.0, value=3.0, step=0.5)
    with col_bt4:
        bt_hold = st.number_input("Số ngày gồng tối đa", min_value=5, max_value=100, value=20)
        
    bt_strategy = st.selectbox("Chiến thuật Giao dịch (Tín hiệu Mua/Bán Khống):", 
                               options=["Spring (Pha C - Bắt đáy hoảng loạn)", 
                                        "Squat Bar (Đỡ giá sớm)",
                                        "mSOS (Điểm mạnh thứ cấp - Đánh ngắn)", 
                                        "JAC (Major SOS - Vượt con lạch)", 
                                        "ChoCH (Thay đổi thuộc tính - Đảo chiều)",
                                        "POE (Vào lệnh tại Vùng Cầu - SMC)",
                                        "UTAD (Phân phối đỉnh - Đánh Short)",
                                        "No Demand (Test Cầu ở đỉnh - Đánh Short)",
                                        "LPS (Pha D/E - Chờ test cạn cung)"])
                                        
    bt_trend = st.checkbox("Bật Bộ Lọc Xu Hướng Thông Minh (Tự động chặn Mua khi giá nằm dưới MA50, chặn Short khi giá nằm trên MA50)", value=True)
    bt_atr_trailing = st.checkbox("🛡️ Sử dụng Chốt lời động (Trailing Stop) 2x ATR thay cho R:R cố định", value=False)
        
    if st.button("Chạy Backtest Lịch Sử"):
        symbols = bt_symbols_selected
        if not symbols:
            st.error("Vui lòng chọn ít nhất một mã chứng khoán.")
        else:
            with st.spinner(f'Đang tải dữ liệu và backtest {len(symbols)} mã cổ phiếu...'):
                bt_end = datetime.today()
                bt_start = bt_end - timedelta(days=730)
                feed = VNStockDataFeed()
                
                all_trades = []
                bt_bar = st.progress(0, text="Bắt đầu tải dữ liệu...")
                
                for idx, sym in enumerate(symbols):
                    bt_bar.progress(int(idx / len(symbols) * 100), text=f"Đang phân tích và backtest mã {sym}...")
                    
                    df = feed.fetch_historical_data(
                        sym, bt_start.strftime('%Y-%m-%d'), bt_end.strftime('%Y-%m-%d'), resolution='1D'
                    )
                    
                    # Nghỉ 0.1 giây (Dựa vào cơ chế tự động chờ 15s nếu vượt limit)
                    time.sleep(0.1)
                    
                    if not df.empty and len(df) >= 50:
                        vsa_engine = VSAIndicator(df)
                        analyzed_df = vsa_engine.run_all()
                        
                        strategy_map = {
                            "Spring (Pha C - Bắt đáy hoảng loạn)": "Spring",
                            "Squat Bar (Đỡ giá sớm)": "Squat Bar (Đỡ giá)",
                            "mSOS (Điểm mạnh thứ cấp - Đánh ngắn)": "mSOS",
                            "JAC (Major SOS - Vượt con lạch)": "JAC",
                            "ChoCH (Thay đổi thuộc tính - Đảo chiều)": "ChoCH",
                            "POE (Vào lệnh tại Vùng Cầu - SMC)": "POE (Vào lệnh tại Vùng Cầu - SMC)",
                            "UTAD (Phân phối đỉnh - Đánh Short)": "UTAD",
                            "No Demand (Test Cầu ở đỉnh - Đánh Short)": "No Demand (Test Cầu)",
                            "LPS (Pha D/E - Chờ test cạn cung)": "LPS (No Supply)"
                        }
                        mapped_strategy = strategy_map[bt_strategy]
                        
                        bt_engine = BacktestEngine(analyzed_df, max_holding_days=int(bt_hold), risk_reward_ratio=bt_rr, stop_loss_buffer=bt_buffer, trend_filter=bt_trend, buy_signal_type=mapped_strategy, use_atr_trailing=bt_atr_trailing)
                        trades_df = bt_engine.run_backtest()
                        
                        if not trades_df.empty:
                            trades_df.insert(0, 'Mã CK', sym) # Thêm cột Mã CK
                            all_trades.append(trades_df)
                            
                bt_bar.empty()
                
                if all_trades:
                    final_trades_df = pd.concat(all_trades, ignore_index=True)
                    # Khởi tạo engine rỗng chỉ để gọi hàm get_summary
                    dummy_engine = BacktestEngine(pd.DataFrame())
                    summary = dummy_engine.get_summary(final_trades_df)
                    
                    if summary:
                        st.subheader(f"📊 Kết quả Backtest Danh Mục ({len(symbols)} mã)")
                        s_col1, s_col2, s_col3, s_col4 = st.columns(4)
                        s_col1.metric("Tổng số lệnh", summary['Tổng số lệnh'])
                        s_col2.metric("Tỷ lệ thắng", summary['Tỷ lệ thắng (Win Rate)'])
                        s_col3.metric("Tổng Lãi/Lỗ (%)", summary['Tổng lợi nhuận (Cộng dồn)'])
                        s_col4.metric("Lãi trung bình / Lệnh", summary['Lợi nhuận trung bình / lệnh'])
                        
                        st.subheader("Bảng Lịch Sử Khớp Lệnh Tổng Hợp")
                        
                        def color_pnl(val):
                            color = '#1f77b4'
                            if isinstance(val, (int, float)):
                                color = 'green' if val > 0 else 'red' if val < 0 else 'gray'
                            return f'color: {color}'
                        
                        styled_trades = final_trades_df.style.applymap(color_pnl, subset=['Lợi nhuận (%)'])
                        styled_trades = styled_trades.format({
                            'Giá Mua': "{:.2f}",
                            'Giá Cắt Lỗ': "{:.2f}",
                            'Giá Chốt Lời': "{:.2f}",
                            'Giá Bán': "{:.2f}",
                            'Lợi nhuận (%)': "{:.2f}%"
                        })
                        st.dataframe(styled_trades, use_container_width=True)
                    else:
                        st.warning("Tất cả các lệnh đều đang cầm chưa bán (Unrealized).")
                else:
                    st.warning("Trong 2 năm qua, hệ thống không tìm thấy lệnh mua nào thỏa mãn với bộ lọc và chiến thuật bạn vừa chọn trên toàn bộ các mã này.")

with tab4:
    st.markdown("Theo dõi biến động giá thực tế và **Khuyến nghị giao dịch** cho các siêu cổ phiếu của bạn.")
    wl = load_watchlist()
    
    if not wl:
        st.info("Danh sách theo dõi đang trống. Hãy qua Tab 2 quét thị trường và bấm Lưu mã vào đây nhé.")
    else:
        # Bổ sung UI thiết lập R:R và Biên độ
        col_wl1, col_wl2, col_wl3 = st.columns([1, 1, 2])
        with col_wl1:
            wl_rr = st.number_input("Tỷ lệ Chốt lời (R:R) mong muốn", min_value=1.0, max_value=10.0, value=2.0, step=0.5, key="wl_rr")
        with col_wl2:
            wl_buffer = st.number_input("Biên độ đệm Cắt lỗ (%)", min_value=0.0, max_value=10.0, value=3.0, step=0.5, key="wl_buffer")
        with col_wl3:
            st.markdown("<br>", unsafe_allow_html=True) # Tạo khoảng trống cho nút thẳng hàng
            if st.button("🗑️ Xóa toàn bộ Danh sách"):
                save_watchlist([])
                st.rerun()
                
        with st.spinner('Đang lấy giá mới nhất từ sàn giao dịch...'):
            feed = VNStockDataFeed()
            end_d = datetime.today()
            start_d = end_d - timedelta(days=10) # Lùi 10 ngày để đề phòng lễ/T7 CN
            
            bullish_data = []
            bearish_data = []
            
            for item in wl:
                sym = item['Symbol']
                df_recent = feed.fetch_historical_data(sym, start_d.strftime('%Y-%m-%d'), end_d.strftime('%Y-%m-%d'), resolution='1D')
                
                # Nghỉ 0.1 giây 
                time.sleep(0.1)
                
                entry_price = item['Price_Scanned']
                # Xử lý tương thích ngược cho dữ liệu cũ chưa có Low_Scanned
                low_scanned = item.get('Low_Scanned', entry_price * 0.95)
                
                if not df_recent.empty:
                    current_price = df_recent.iloc[-1]['Close']
                    pnl_pct = ((current_price - entry_price) / entry_price) * 100
                else:
                    current_price = entry_price
                    pnl_pct = 0.0
                    
                # Thuật toán tính Stop-loss và Target
                stop_loss = low_scanned * (1 - wl_buffer / 100.0)
                if stop_loss >= entry_price:
                    stop_loss = entry_price * 0.98 # Safety check
                    
                risk_per_share = entry_price - stop_loss
                take_profit = entry_price + (risk_per_share * wl_rr)
                    
                # Phân loại tín hiệu (Phe Bò / Phe Gấu)
                is_bearish = any(s in item['Signal'] for s in ["UTAD", "No Demand", "Climax", "Bearish", "Báo Bão"])
                
                if is_bearish:
                    bearish_data.append({
                        'Mã CK': sym,
                        'Xu hướng': item.get('Trend', 'Chưa rõ'),
                        'Tín hiệu gốc': "🔴 " + item['Signal'],
                        'Ngày Quét': item['Date_Scanned'],
                        'Khuyến nghị Cơ sở': "🛑 CANH BÁN / KHÔNG MUA",
                        'Giá Cắt Lỗ (Stop-loss)': "N/A",
                        'Target Chốt Lời': "N/A",
                        'Giá Hiện Tại': f"{current_price:.2f}",
                        'Lãi/Lỗ tạm tính (%)': "N/A"
                    })
                else:
                    bullish_data.append({
                        'Mã CK': sym,
                        'Xu hướng': item.get('Trend', 'Chưa rõ'),
                        'Tín hiệu gốc': "🟢 " + item['Signal'],
                        'Ngày Quét': item['Date_Scanned'],
                        'Khuyến nghị Cơ sở': f"✅ MUA QUANH: {entry_price:.2f}",
                        'Giá Cắt Lỗ (Stop-loss)': f"{stop_loss:.2f}",
                        'Target Chốt Lời': f"{take_profit:.2f}",
                        'Giá Hiện Tại': f"{current_price:.2f}",
                        'Lãi/Lỗ tạm tính (%)': round(pnl_pct, 2)
                    })
                
            if bullish_data or bearish_data:
                tab_bull, tab_bear = st.tabs(["✅ Tín Hiệu Cơ Sở (Canh Mua)", "🔻 Cảnh Báo Phái Sinh (Canh Bán)"])
                
                def color_wl_pnl(val):
                    if val == "N/A": return 'color: gray'
                    color = '#1f77b4'
                    if isinstance(val, (int, float)):
                        color = 'green' if val > 0 else 'red' if val < 0 else 'gray'
                    return f'color: {color}'
                    
                def format_pct(x):
                    if isinstance(x, (int, float)): return f"{x:.2f}%"
                    return x
                    
                with tab_bull:
                    if bullish_data:
                        df_bull = pd.DataFrame(bullish_data)
                        styled_bull = df_bull.style.applymap(color_wl_pnl, subset=['Lãi/Lỗ tạm tính (%)']).format({'Lãi/Lỗ tạm tính (%)': format_pct})
                        st.dataframe(styled_bull, use_container_width=True)
                    else:
                        st.info("Chưa có mã chứng khoán Cơ sở nào báo tín hiệu MUA.")
                        
                with tab_bear:
                    if bearish_data:
                        df_bear = pd.DataFrame(bearish_data)
                        styled_bear = df_bear.style.applymap(color_wl_pnl, subset=['Lãi/Lỗ tạm tính (%)']).format({'Lãi/Lỗ tạm tính (%)': format_pct})
                        st.dataframe(styled_bear, use_container_width=True)
                    else:
                        st.info("Không có cảnh báo BÁN rủi ro nào.")

        # --- PORTFOLIO MANAGER ---
        st.markdown("---")
        st.markdown("### 📦 Trình Quản Lý Danh Mục Đầu Tư (Portfolio)")
        
        portfolio = load_portfolio()
        
        col_p1, col_p2, col_p3, col_p4 = st.columns([2, 2, 2, 1])
        with col_p1:
            p_symbol = st.text_input("Mã Cổ Phiếu (VD: HPG)", "").upper()
        with col_p2:
            p_price = st.number_input("Giá Vốn (x1000 VNĐ)", min_value=1.0, value=20.0, step=0.1)
        with col_p3:
            p_qty = st.number_input("Khối lượng (Cổ phiếu)", min_value=100, value=1000, step=100)
        with col_p4:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("➕ Thêm vào Danh mục"):
                if p_symbol:
                    portfolio.append({
                        "Symbol": p_symbol,
                        "Buy_Price": p_price,
                        "Quantity": p_qty,
                        "Date_Added": datetime.today().strftime('%Y-%m-%d')
                    })
                    save_portfolio(portfolio)
                    st.success(f"Đã thêm {p_symbol} vào danh mục!")
                    st.rerun()
                    
        if portfolio:
            st.markdown("#### Tình trạng Danh mục Hiện tại")
            pf_data = []
            total_invested = 0
            total_current = 0
            
            with st.spinner("Đang cập nhật giá thị trường cho danh mục..."):
                feed = VNStockDataFeed()
                end_d = datetime.today()
                start_d = end_d - timedelta(days=5)
                
                for idx, item in enumerate(portfolio):
                    sym = item['Symbol']
                    buy_price = item['Buy_Price']
                    qty = item['Quantity']
                    
                    df_recent = feed.fetch_historical_data(sym, start_d.strftime('%Y-%m-%d'), end_d.strftime('%Y-%m-%d'), resolution='1D')
                    time.sleep(0.1)
                    
                    if not df_recent.empty:
                        curr_price = df_recent.iloc[-1]['Close']
                    else:
                        curr_price = buy_price
                        
                    invested_val = buy_price * qty * 1000
                    current_val = curr_price * qty * 1000
                    pnl_val = current_val - invested_val
                    pnl_pct = (curr_price - buy_price) / buy_price * 100
                    
                    total_invested += invested_val
                    total_current += current_val
                    
                    # Cảnh báo
                    alert = "✅ An toàn"
                    if pnl_pct <= -5:
                        alert = "🚨 VI PHẠM CẮT LỖ (<-5%)"
                    elif pnl_pct >= 10:
                        alert = "🎯 ĐẠT TARGET (>10%)"
                        
                    pf_data.append({
                        "Mã CK": sym,
                        "Khối lượng": f"{qty:,}",
                        "Giá Vốn": f"{buy_price:.2f}",
                        "Giá Hiện Tại": f"{curr_price:.2f}",
                        "Tổng Vốn (VNĐ)": f"{invested_val:,.0f}",
                        "Lãi/Lỗ (VNĐ)": pnl_val,
                        "Lãi/Lỗ (%)": pnl_pct,
                        "Trạng thái": alert
                    })
                    
            df_pf = pd.DataFrame(pf_data)
            
            # Styling
            def color_pnl_val(val):
                if isinstance(val, (int, float)):
                    color = 'green' if val > 0 else 'red' if val < 0 else 'gray'
                    return f'color: {color}'
                return ''
                
            def format_pnl_pct(val):
                return f"{val:.2f}%"
                
            styled_pf = df_pf.style.applymap(color_pnl_val, subset=['Lãi/Lỗ (VNĐ)', 'Lãi/Lỗ (%)'])\
                .format({'Lãi/Lỗ (VNĐ)': "{:,.0f}", 'Lãi/Lỗ (%)': format_pnl_pct})
                
            st.dataframe(styled_pf, use_container_width=True)
            
            # Summary
            total_pnl = total_current - total_invested
            total_pnl_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0
            
            col_s1, col_s2, col_s3 = st.columns(3)
            col_s1.metric("Tổng Vốn Đầu Tư", f"{total_invested:,.0f} đ")
            col_s2.metric("Giá Trị Hiện Tại", f"{total_current:,.0f} đ")
            col_s3.metric("Tổng Lãi/Lỗ", f"{total_pnl:,.0f} đ", f"{total_pnl_pct:.2f}%")
            
            if st.button("🗑️ Xoá toàn bộ Danh mục"):
                save_portfolio([])
                st.rerun()

with tab5:
    st.markdown("### ⚡ Bảng Chỉ Huy Phái Sinh (VN30F1M)")
    st.markdown("Hệ thống tự động phân tích đồ thị Phái sinh khung thời gian **15 Phút (Intraday)**.")
    
    if st.button("Tải dữ liệu Phái sinh 15M Mới nhất"):
        with st.spinner("Đang tải dữ liệu Phái sinh Real-time..."):
            feed = VNStockDataFeed()
            end_d = datetime.today()
            start_d = end_d - timedelta(days=15)
            
            try:
                df_ps = feed.fetch_historical_data('VN30F1M', start_d.strftime('%Y-%m-%d'), end_d.strftime('%Y-%m-%d'), resolution='15')
                if not df_ps.empty:
                    vsa_ps = VSAIndicator(df_ps)
                    res_ps = vsa_ps.run_all()
                    
                    st.success("Tải dữ liệu thành công! (Lưu ý: Nến cuối cùng có thể chưa đóng cửa)")
                    
                    # Vẽ đồ thị
                    fig_ps = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3], figure=go.Figure())
                    
                    # Nến
                    fig_ps.add_trace(go.Candlestick(x=res_ps['Date'], open=res_ps['Open'], high=res_ps['High'], low=res_ps['Low'], close=res_ps['Close'], name='VN30F1M'), row=1, col=1)
                    
                    # MA
                    fig_ps.add_trace(go.Scatter(x=res_ps['Date'], y=res_ps['MA_20'], mode='lines', line=dict(color='yellow', width=1), name='MA20'), row=1, col=1)
                    fig_ps.add_trace(go.Scatter(x=res_ps['Date'], y=res_ps['MA_50'], mode='lines', line=dict(color='orange', width=1.5), name='MA50'), row=1, col=1)
                    
                    # Volume
                    colors_vol = ['green' if row['Close'] >= row['Open'] else 'red' for idx, row in res_ps.iterrows()]
                    fig_ps.add_trace(go.Bar(x=res_ps['Date'], y=res_ps['Volume'], marker_color=colors_vol, name='Volume'), row=2, col=1)
                    
                    # Đánh dấu tín hiệu
                    signals = [
                        ('Spring', 'Spring', 'green', 'bottom'),
                        ('Stopping_Volume', 'StopVol', 'lightgreen', 'bottom'),
                        ('Squat_Bar', 'Squat', 'blue', 'bottom'),
                        ('mSOS', 'mSOS', 'cyan', 'top'),
                        ('JAC', 'JAC', 'purple', 'top'),
                        ('ChoCH', 'ChoCH', 'yellow', 'top'),
                        ('UTAD', 'UTAD', 'red', 'top'),
                        ('No_Supply', 'TestCung', 'white', 'bottom'),
                        ('No_Demand', 'TestCau', 'pink', 'top'),
                        ('POE', 'POE', 'gold', 'bottom')
                    ]
                    
                    for col_name, label, color, position in signals:
                        if col_name in res_ps.columns:
                            signal_points = res_ps[res_ps[col_name] == True]
                            if not signal_points.empty:
                                y_pos = signal_points['Low'] * 0.999 if position == 'bottom' else signal_points['High'] * 1.001
                                fig_ps.add_trace(go.Scatter(
                                    x=signal_points['Date'], y=y_pos, mode='markers+text',
                                    marker=dict(symbol='triangle-up' if position=='bottom' else 'triangle-down', size=10, color=color),
                                    text=label, textposition="bottom center" if position=='bottom' else "top center",
                                    name=label
                                ), row=1, col=1)
                    
                    fig_ps.update_layout(height=800, template='plotly_dark', xaxis_rangeslider_visible=False)
                    st.plotly_chart(fig_ps, use_container_width=True)
                    
                    st.markdown("### Dữ liệu các nến gần nhất")
                    st.dataframe(res_ps.tail(10).sort_values('Date', ascending=False), use_container_width=True)
                else:
                    st.error("Lỗi: Không tải được dữ liệu Phái sinh. Có thể do ngoài giờ giao dịch hoặc API lỗi.")
            except Exception as e:
                st.error(f"Lỗi hệ thống: {e}")

