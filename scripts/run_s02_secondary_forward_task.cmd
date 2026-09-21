@echo off
setlocal

cd /d "%~dp0.."
set "PY=%CD%\.venv\Scripts\python.exe"
set "LOGDIR=%CD%\data\forward-task-logs"
set "LOG=%LOGDIR%\s02_secondary_forward.log"

if not exist "%PY%" (
  echo Python venv executable not found: %PY%
  exit /b 10
)

if not exist "%LOGDIR%" mkdir "%LOGDIR%"

echo ===== S02 secondary forward task start %DATE% %TIME% =====>> "%LOG%"

"%PY%" "scripts\scan_s02_forward.py" --database "data\forward_ustec.sqlite" --entity "S02-v0.1:USTEC:SECONDARY" >> "%LOG%" 2>&1
set "USTEC_SCAN=%ERRORLEVEL%"
"%PY%" "scripts\verify_forward_ledger.py" --database "data\forward_ustec.sqlite" >> "%LOG%" 2>&1
set "USTEC_VERIFY=%ERRORLEVEL%"

"%PY%" "scripts\scan_s02_forward.py" --database "data\forward_us30.sqlite" --entity "S02-v0.1:US30:SECONDARY" >> "%LOG%" 2>&1
set "US30_SCAN=%ERRORLEVEL%"
"%PY%" "scripts\verify_forward_ledger.py" --database "data\forward_us30.sqlite" >> "%LOG%" 2>&1
set "US30_VERIFY=%ERRORLEVEL%"

echo ustec_scan=%USTEC_SCAN% ustec_verify=%USTEC_VERIFY% us30_scan=%US30_SCAN% us30_verify=%US30_VERIFY%>> "%LOG%"
echo.>> "%LOG%"

if not "%USTEC_SCAN%"=="0" exit /b %USTEC_SCAN%
if not "%USTEC_VERIFY%"=="0" exit /b %USTEC_VERIFY%
if not "%US30_SCAN%"=="0" exit /b %US30_SCAN%
if not "%US30_VERIFY%"=="0" exit /b %US30_VERIFY%

exit /b 0
