@echo off
setlocal

cd /d "%~dp0.."
set "PY=%CD%\.venv\Scripts\python.exe"
set "LOGDIR=%CD%\data\forward-task-logs"

if not exist "%PY%" (
  echo Python venv executable not found: %PY%
  exit /b 10
)

if not exist "%LOGDIR%" mkdir "%LOGDIR%"

for /f %%I in ('powershell -NoProfile -Command "(Get-Date).ToUniversalTime().ToString(''yyyyMMddTHHmmssZ'')"') do set "STAMP=%%I"
set "LOG=%LOGDIR%\s02_xau_forward_%STAMP%.log"

echo ===== S02 XAU forward task start %STAMP% =====>> "%LOG%"

"%PY%" "scripts\scan_s02_forward.py" >> "%LOG%" 2>&1
set "SCAN_EXIT=%ERRORLEVEL%"

"%PY%" "scripts\verify_forward_ledger.py" >> "%LOG%" 2>&1
set "VERIFY_EXIT=%ERRORLEVEL%"

echo scan_exit=%SCAN_EXIT% verify_exit=%VERIFY_EXIT%>> "%LOG%"

if not "%SCAN_EXIT%"=="0" exit /b %SCAN_EXIT%
if not "%VERIFY_EXIT%"=="0" exit /b %VERIFY_EXIT%

exit /b 0
