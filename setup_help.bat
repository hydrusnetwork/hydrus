@ECHO off

IF NOT EXIST "venv\" goto :missing_venv

IF EXIST "help\" goto :delete

goto :create

:delete

echo Deleting old help...

rmdir /s /q help

:create

echo Creating new help...

CALL venv\Scripts\activate.bat

pip install mkdocs-material

mkdocs build -d help

CALL venv\Scripts\deactivate.bat

SET /P done=Done!

goto :done

:missing_venv

SET /P ready=You need to set up a venv! Check the running from source help for more info!

:done
