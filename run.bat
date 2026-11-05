@echo off
cd /d "%~dp0"
where py >nul 2>&1 && (py -3 run.py %* & goto :end)
python run.py %*
:end
if errorlevel 1 pause
