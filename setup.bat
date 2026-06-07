@echo off
:: ============================================================
::  setup.bat — Run once after cloning to a new machine
::  Registers the 07:30 AM daily scheduled task automatically
:: ============================================================
set ROOT=%~dp0
set PYTHON=C:\Users\%USERNAME%\.code-puppy-venv\Scripts\python.exe
set TASK=367A MetricRank Refresh

echo.
echo  367-A MetricRank — First-Time Setup
echo  =====================================
echo.

:: Check Python exists
if not exist "%PYTHON%" (
    echo  [ERROR] Code Puppy not found at %PYTHON%
    echo  Install Code Puppy first: https://puppy.walmart.com
    pause
    exit /b 1
)
echo  [OK] Python found: %PYTHON%

:: Create output folder
if not exist "%ROOT%output" mkdir "%ROOT%output"
echo  [OK] output\ folder ready

:: Register scheduled task (daily 07:30 AM)
schtasks /create /tn "%TASK%" /tr "\"%ROOT%REFRESH.bat\"" /sc DAILY /st 07:30 /f >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo  [OK] Scheduled task registered: "%TASK%" at 07:30 AM daily
) else (
    echo  [WARN] Could not register scheduled task (may need admin rights)
    echo         Run Task Scheduler manually and point it to REFRESH.bat
)

:: Do an initial build from existing data/metrics_raw.txt
echo.
echo  Running initial build from data\metrics_raw.txt...
"%PYTHON%" "%ROOT%parse.py"
"%PYTHON%" "%ROOT%build.py"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo  [OK] Setup complete!
    echo  - Dashboard: %ROOT%output\367A_Metrics_Final.html
    echo  - To refresh manually: double-click REFRESH.bat
    echo  - Auto-refresh: every morning at 07:30 AM
    echo.
    start "" "%ROOT%output\367A_Metrics_Final.html"
) else (
    echo.
    echo  [ERROR] Build failed — check output\refresh.log
    pause
)
