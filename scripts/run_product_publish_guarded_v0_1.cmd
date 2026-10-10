@echo off
setlocal EnableDelayedExpansion

REM DORMANT review-only successor. Never install without separate owner approval.
REM Python requires VOWSIG_GUARDED_PUBLISH_ENABLED=1, absent by default.

cd /d "%~dp0.."
set "PY=%CD%\.venv\Scripts\python.exe"
set "LOGDIR=%CD%\data\forward-task-logs"
set "LOG=%LOGDIR%\product_publish_guarded_v0_1.log"

if not exist "%PY%" exit /b 10
if not exist "%LOGDIR%" mkdir "%LOGDIR%"

echo ===== Guarded publisher start %DATE% %TIME% =====>> "%LOG%"
"%PY%" -B "scripts\guarded_product_publish_v0_1.py" --confirm RUN-GUARDED-PUBLISH-V0.1 >> "%LOG%" 2>&1
set "RESULT=!ERRORLEVEL!"
echo guarded_exit=!RESULT!>> "%LOG%"
echo.>> "%LOG%"
exit /b !RESULT!
