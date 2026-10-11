@echo off
setlocal EnableDelayedExpansion

REM DORMANT review-only successor. Never install without separate owner approval.
REM Python requires VOWSIG_GUARDED_PUBLISH_ENABLED=1, absent by default.

cd /d "%~dp0.."
REM Fail closed BEFORE any logs, notifications, network or filesystem writes.
if not "%VOWSIG_GUARDED_PUBLISH_ENABLED%"=="1" exit /b 31
set "PY=%CD%\.venv\Scripts\python.exe"
set "LOGDIR=%CD%\data\forward-task-logs"
set "LOG=%LOGDIR%\product_publish_guarded_v0_1.log"

if not exist "%PY%" exit /b 10
if not exist "%LOGDIR%" mkdir "%LOGDIR%"

echo ===== Guarded publisher start %DATE% %TIME% =====>> "%LOG%"

REM Keep independent core/expansion alerts even when crypto publication is HELD.
"%PY%" -B "scripts\notify_forward_events.py" >> "%LOG%" 2>&1
set "ALERT_EXIT=!ERRORLEVEL!"
echo alert_exit=!ALERT_EXIT!>> "%LOG%"
if not "!ALERT_EXIT!"=="0" exit /b !ALERT_EXIT!

"%PY%" -B "scripts\guarded_product_publish_v0_1.py" --confirm RUN-GUARDED-PUBLISH-V0.1 >> "%LOG%" 2>&1
set "RESULT=!ERRORLEVEL!"
echo guarded_exit=!RESULT!>> "%LOG%"
echo.>> "%LOG%"
exit /b !RESULT!
