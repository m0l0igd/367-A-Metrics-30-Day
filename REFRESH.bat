@echo off
:: ============================================================
::  REFRESH.bat — Manual or scheduled daily refresh
::  Double-click anytime to pull latest MetricRank data
:: ============================================================
set ROOT=%~dp0
set PYTHON=C:\Users\%USERNAME%\.code-puppy-venv\Scripts\python.exe

echo.
echo  367-A MetricRank Refresh — %DATE% %TIME%
echo  ==========================================
echo.

"%PYTHON%" "%ROOT%refresh.py"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  [ERROR] Refresh failed. Check: %ROOT%output\refresh.log
    pause
    exit /b 1
)

echo.
echo  Opening dashboard...
start "" "%ROOT%output\367A_Metrics_Final.html"
