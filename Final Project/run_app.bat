@echo off
setlocal
cd /d "%~dp0"

echo Starting AI Career Coach...
python -m streamlit run app.py

echo.
echo Streamlit has stopped. Press any key to close this window.
pause >nul
