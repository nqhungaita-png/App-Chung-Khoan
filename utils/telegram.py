import requests
import logging

logger = logging.getLogger(__name__)

def send_telegram_message(token, chat_id, text):
    """
    Gửi tin nhắn qua Telegram Bot.
    """
    if not token or not chat_id:
        return False, "Thiếu Token hoặc Chat ID"
        
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            return True, "Gửi thành công!"
        else:
            logger.error(f"Telegram error: {response.text}")
            return False, f"Lỗi: {response.text}"
    except Exception as e:
        logger.error(f"Telegram exception: {e}")
        return False, str(e)
