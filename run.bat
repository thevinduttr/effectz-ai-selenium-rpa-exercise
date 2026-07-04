@echo off
setlocal

title botrunner

echo ==========================
echo        botrunner
echo ==========================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo Python virtual environment not found.
    echo Creating .venv...
    python -m venv .venv
    if errorlevel 1 goto setup_failed
)

echo Installing requirements...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto setup_failed

echo 1. Run Task A only
echo 2. Run Task A and Task B
echo.
set /p choice=Enter option (1/2 or A/BOTH): 

if /I "%choice%"=="1" goto task_a
if /I "%choice%"=="A" goto task_a
if /I "%choice%"=="2" goto both
if /I "%choice%"=="BOTH" goto both

echo.
echo Invalid option. Please run botrunner again and choose 1, 2, A, or BOTH.
pause
exit /b 1

:task_a
echo.
echo Running Task A...
".venv\Scripts\python.exe" run.py --task A
goto done

:both
echo.
echo Running Task A and Task B...
".venv\Scripts\python.exe" run.py --task BOTH
goto done

:setup_failed
echo.
echo Setup failed. Please check Python is installed and try again.
pause
exit /b 1

:done
set "exit_code=%ERRORLEVEL%"
echo.
pause
exit /b %exit_code%
