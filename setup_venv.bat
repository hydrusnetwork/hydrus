@ECHO off

IF EXIST "venv\" goto :venv_exists

SET /P ready=If you do not have Python 3 installed yet, check the 'running from source' help. Hit Enter to start.

goto :create

:venv_exists

SET /P Virtual environment will be reinstalled. Hit Enter to start.

echo Deleting old venv...

rmdir /s /q venv

:create

echo Creating new venv...

python -m venv venv

CALL venv\Scripts\activate.bat

python -m pip install --upgrade pip

pip3 install --upgrade wheel

pip3 install -r requirements.txt

CALL venv\Scripts\deactivate.bat

goto :done

:done

SET /P done=Done!

