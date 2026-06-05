@echo off
chcp 65001 >nul
echo ==============================================================
echo CAI DAT BOT QUET CHUNG KHOAN TU DONG (14:40 Hang Ngay)
echo ==============================================================
echo.

set "SCRIPT_PATH=%~dp0auto_bot.py"

echo Tao lich trinh chay ngam vao luc 14:40 moi ngay...
schtasks /create /tn "VSA_Quant_Bot" /tr "python \"%SCRIPT_PATH%\"" /sc daily /st 14:40 /f

echo.
echo ==============================================================
echo [THANH CONG] Bot da duoc cai dat thanh cong!
echo Cu den 14:40 chieu moi ngay, Bot se tu dong quet va gui Telegram.
echo De huy bot, hay chay lenh: schtasks /delete /tn "VSA_Quant_Bot" /f
echo ==============================================================
pause
