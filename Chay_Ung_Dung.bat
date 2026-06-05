@echo off
set PYTHONUTF8=1
echo ===================================================
echo   DANG KHOI DONG HE THONG PHAN TICH CHUNG KHOAN 
echo ===================================================
echo.
echo He thong se tu dong mo tren trinh duyet web cua ban...
echo Vui long KHONG tat cua so mau den nay trong qua trinh su dung!
echo.

cd /d "%~dp0"
python -m streamlit run app.py

pause
