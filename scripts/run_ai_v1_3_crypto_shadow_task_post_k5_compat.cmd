@echo off
setlocal EnableDelayedExpansion

REM Additive K5 successor: follow the proven AI-v1.2.1 registry-compat task pattern.
REM The frozen K3 AI-v1.3 runner is preserved unchanged.
REM Check scheduler health externally AFTER Task Scheduler completes this run.

cd /d "%~dp0.."
set "PY=%CD%\.venv\Scripts\python.exe"
set "LOGDIR=%CD%\data\forward-task-logs"
set "LOG=%LOGDIR%\ai_v1_3_crypto_shadow.log"

if not exist "%PY%" (
  echo Python venv executable not found: %PY%
  exit /b 10
)

if not exist "%LOGDIR%" mkdir "%LOGDIR%"

echo ===== VowSig AI-v1.3 crypto shadow task start %DATE% %TIME% =====>> "%LOG%"

"%PY%" "scripts\run_ai_v1_3_crypto_live.py" >> "%LOG%" 2>&1
set "RUN_EXIT=!ERRORLEVEL!"

if not "!RUN_EXIT!"=="0" (
  echo run_exit=!RUN_EXIT! verify_exit=SKIPPED>> "%LOG%"
  echo.>> "%LOG%"
  exit /b !RUN_EXIT!
)

REM The normal full runtime verifier checks all three append-only ledgers,
REM K3 frozen artifacts/anchor, parallel runtime, broker/public boundaries.
REM NEVER use --include-scheduler inside the task being evaluated.
"%PY%" "scripts\verify_ai_v1_3_crypto_runtime.py" >> "%LOG%" 2>&1
set "VERIFY_EXIT=!ERRORLEVEL!"

echo run_exit=!RUN_EXIT! verify_exit=!VERIFY_EXIT!>> "%LOG%"
echo.>> "%LOG%"

if not "!VERIFY_EXIT!"=="0" exit /b !VERIFY_EXIT!

exit /b 0
