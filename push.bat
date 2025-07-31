@echo off
cd /d "%~dp0"

REM Get current timestamp
for /f "tokens=1-5 delims=/: " %%d in ("%date% %time%") do (
    set "stamp=%%d-%%e-%%f_%%g%%h"
)

git add .
git commit -m "Update on %stamp%"
git push

pause
