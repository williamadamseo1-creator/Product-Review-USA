@echo off
setlocal
cd /d "%~dp0"
set "CONFIG_FILE=site_configs\site-1.json"

if not exist "%CONFIG_FILE%" (
  echo Config file not found. Generating template...
  python programmatic_html_generator.py --write-config-template "%CONFIG_FILE%"
  echo Template created: %CONFIG_FILE%
  echo Edit this file and run again.
  pause
  exit /b
)

python programmatic_html_generator.py --config-file "%CONFIG_FILE%"
echo.
echo Generation complete.
pause
