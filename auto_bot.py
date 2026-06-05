import sys
import os
import json
import logging
import datetime
from strategies.market_scanner import MarketScanner
from utils.telegram import send_telegram_message

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

CONFIG_FILE = "telegram_config.json"

def main():
    logger.info("Bắt đầu chạy Auto Bot quét thị trường...")
    
    # Ép kiểu terminal về utf-8 trên Windows
    if sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
    
    if not os.path.exists(CONFIG_FILE):
        logger.error(f"Không tìm thấy file {CONFIG_FILE}. Vui lòng mở App, vào Tab 2 và lưu cấu hình Telegram trước!")
        return
        
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        config = json.load(f)
        
    token = config.get('tg_token', '')
    chat_id = config.get('tg_chat_id', '')
    
    if not token or not chat_id:
        logger.error("Token hoặc Chat ID bị trống.")
        return
        
    # Quét toàn bộ VN30
    scanner = MarketScanner()
    logger.info("Đang tải dữ liệu VNINDEX và quét VN30...")
    scan_results = scanner.scan_market()
    
    vn_status = scanner.vnindex_status
    logger.info(f"Trạng thái VN-INDEX: {vn_status}")
    
    if scan_results.empty:
        logger.info("Thị trường bình yên, không có mã nào có tín hiệu hôm nay.")
        return
        
    logger.info(f"Tìm thấy {len(scan_results)} mã có tín hiệu. Đang gửi Telegram...")
    
    msg = "🔥 <b>BÁO CÁO QUÉT THỊ TRƯỜNG VSA (AUTO)</b> 🔥\n"
    msg += f"🚦 <b>VN-INDEX:</b> {vn_status}\n\n"
    for _, row in scan_results.iterrows():
        msg += f"<b>{row['Mã']}</b> | <b>{row['Tín hiệu']}</b>\n"
        msg += f"💵 Giá: {row['Giá đóng cửa']} | Trend: {row['Xu hướng (MA50)']}\n"
        rs_val = row.get('Sức mạnh (RS)', 'N/A')
        msg += f"💪 Sức mạnh: {rs_val}\n"
        news_val = row.get('Tin tức mới nhất', 'Không có')
        msg += f"📰 Tin: <i>{news_val}</i>\n"
        msg += "--------------------------------------\n"
        
    success, info = send_telegram_message(token, chat_id, msg)
    if success:
        logger.info("Đã gửi tin nhắn Telegram thành công!")
    else:
        logger.error(f"Lỗi gửi Telegram: {info}")

if __name__ == "__main__":
    main()
