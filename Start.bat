@echo off
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
py -3.13 -c "import sys,struct;sys.exit(struct.calcsize('P')!=8)" >nul 2>nul
if not errorlevel 1 (
    py -3.13 bootstrap.py
    goto finish
)
py -3.12 -c "import sys,struct;sys.exit(struct.calcsize('P')!=8)" >nul 2>nul
if not errorlevel 1 (
    py -3.12 bootstrap.py
    goto finish
)
py -3.11 -c "import sys,struct;sys.exit(struct.calcsize('P')!=8)" >nul 2>nul
if not errorlevel 1 (
    py -3.11 bootstrap.py
    goto finish
)
python -c "import sys,struct;sys.exit(not((3,11)<=sys.version_info[:2]<=(3,13) and struct.calcsize('P')==8))" >nul 2>nul
if not errorlevel 1 (
    python bootstrap.py
    goto finish
)
echo Please install 64-bit Python 3.13, 3.12 or 3.11 from python.org.
echo Enable 'Add python.exe to PATH' and keep Tcl/Tk selected during installation.
echo Then double-click Start.bat again. See the included usage guide.
echo https://www.python.org/downloads/windows/
pause
exit /b 1
:finish
if errorlevel 1 (
    echo Startup failed. Please read the error above and the included usage guide.
    pause
)
