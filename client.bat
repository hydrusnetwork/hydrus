@ECHO off

IF NOT EXIST "venv\" goto :missing_venv

CALL venv\Scripts\activate.bat

start "" "pythonw" client.pyw

goto :done

:missing_venv

SET /P ready=You need to set up a venv! Check the running from source help for more info!

:done
