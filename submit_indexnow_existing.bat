@echo off
setlocal
cd /d "%~dp0"
set "CONFIG_FILE=site_configs\site-1.json"

if not exist "%CONFIG_FILE%" (
  echo Config file not found: %CONFIG_FILE%
  pause
  exit /b 1
)

python programmatic_html_generator.py --config-file "%CONFIG_FILE%" --indexnow-submit-existing
echo.
echo IndexNow submit attempt finished.
pause
