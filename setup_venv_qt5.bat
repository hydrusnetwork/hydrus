@ECHO off

IF EXIST "venv\" goto :venv_exists

SET /P ready=If you do not have Python 3 installed yet, check the 'running from source' help. Hit Enter to start.

goto :create

:venv_exists

SET /P install_type=venv folder already exists. Do you want to: (r)einstall, (u)pdate? 
IF "%install_type%" == "r" goto :delete
IF "%install_type%" == "u" goto :update

goto :done

:delete

echo Deleting old venv...

rmdir /s /q venv

:create

echo Creating new venv...

python -m venv venv

:update

CALL venv\Scripts\activate.bat

python -m pip install --upgrade pip

pip3 install --upgrade wheel

pip3 install -r requirements_qt5.txt

CALL venv\Scripts\deactivate.bat

SET /P done=Done!

:done
