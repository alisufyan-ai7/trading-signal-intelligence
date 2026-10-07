@echo off
setlocal EnableDelayedExpansion

cd /d "%~dp0.."
set "PY=%CD%\.venv\Scripts\python.exe"
set "LOGDIR=%CD%\data\forward-task-logs"
set "LOG=%LOGDIR%\ai_v1_2_1_expansion_shadow.log"

if not exist "%PY%" (
  echo Python venv executable not found: %PY%
  exit /b 10
)

if not exist "%LOGDIR%" mkdir "%LOGDIR%"

echo ===== VowSig AI-v1.2.1 expansion shadow task start %DATE% %TIME% =====>> "%LOG%"

"%PY%" "scripts\run_ai_v1_2_1_live.py" >> "%LOG%" 2>&1
set "RUN_EXIT=!ERRORLEVEL!"

"%PY%" "scripts\verify_ai_v1_2_1_runtime.py" --include-scheduler >> "%LOG%" 2>&1
set "VERIFY_EXIT=!ERRORLEVEL!"

echo run_exit=!RUN_EXIT! verify_exit=!VERIFY_EXIT!>> "%LOG%"
echo.>> "%LOG%"

if not "!RUN_EXIT!"=="0" exit /b !RUN_EXIT!
if not "!VERIFY_EXIT!"=="0" exit /b !VERIFY_EXIT!

exit /b 0
