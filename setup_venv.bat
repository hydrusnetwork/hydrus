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

echo This setup_venv.bat file is going to be deleted in v673. Please move to setup_venv.py.

REM Delegate to Python setup script
%python_bin% setup_venv.py

popd
exit /b %errorlevel%
