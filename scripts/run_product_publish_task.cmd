@echo off
setlocal

cd /d "%~dp0.."
set "PY=%CD%\.venv\Scripts\python.exe"
set "LOGDIR=%CD%\data\forward-task-logs"
set "LOG=%LOGDIR%\product_publish.log"

if not exist "%PY%" exit /b 10
if not exist "%LOGDIR%" mkdir "%LOGDIR%"

echo ===== TradingTop product publish %DATE% %TIME% =====>> "%LOG%"

"%PY%" "scripts\export_public_snapshot.py" >> "%LOG%" 2>&1
set "EXPORT_EXIT=%ERRORLEVEL%"

"%PY%" "scripts\notify_forward_events.py" >> "%LOG%" 2>&1
set "ALERT_EXIT=%ERRORLEVEL%"

"%PY%" "scripts\push_public_snapshot.py" --optional >> "%LOG%" 2>&1
set "PUSH_EXIT=%ERRORLEVEL%"

echo export_exit=%EXPORT_EXIT% alert_exit=%ALERT_EXIT% push_exit=%PUSH_EXIT%>> "%LOG%"
echo.>> "%LOG%"

if not "%EXPORT_EXIT%"=="0" exit /b %EXPORT_EXIT%
if not "%ALERT_EXIT%"=="0" exit /b %ALERT_EXIT%
if not "%PUSH_EXIT%"=="0" exit /b %PUSH_EXIT%

exit /b 0
