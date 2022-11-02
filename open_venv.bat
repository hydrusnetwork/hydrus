@ECHO off

IF EXIST "venv\" goto :venv_exists

goto :venv_missing

:venv_exists

start venv\Scripts\activate.bat

goto :done

:venv_missing

SET /P done=Sorry, you do not seem to have a venv!

:done
