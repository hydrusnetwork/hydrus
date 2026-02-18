@ECHO off

pushd "%~dp0"

IF NOT EXIST "venv\" (

    SET /P gumpf="You need to set up a venv! Check the running from source help for more info!"

    popd

    EXIT /B 1

)

:delete

IF EXIST "help\" (

    echo Deleting old help...

    rmdir /s /q help

)

:create

echo Creating new help...

CALL venv\Scripts\activate.bat

pip install mkdocs-material==9.7.1

mkdocs build -d help

CALL venv\Scripts\deactivate.bat

SET /P done="Done!"

popd
