@ECHO off

REM Minimal setup script for Windows - finds Python and delegates to tools/setup_venv.py

pushd "%~dp0"

set python_bin=python

where /q %python_bin%
if errorlevel 1 (
    echo ERROR: Could not find python!
    popd
    exit /b 1
)

REM Delegate to Python setup script
%python_bin% tools\setup_venv.py

popd
exit /b %errorlevel%
