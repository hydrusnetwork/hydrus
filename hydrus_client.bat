@ECHO off

pushd "%~dp0"

IF NOT EXIST "venv\" (

	SET /P gumpf="You need to set up a venv! Check the running from source help for more info!"
	
	popd
	
	EXIT /B 1
	
)

CALL venv\Scripts\activate.bat

IF ERRORLEVEL 1 (
	
	SET /P gumpf="The venv failed to activate, stopping now!"
	
	popd
	
	EXIT /B 1
	
)

REM You can copy this file to 'hydrus_client-user.bat' and add in your own launch parameters here if you like, and a git pull won't overwrite the file.
REM Just tack new params on like this:
REM start "" "pythonw" hydrus_client.pyw -d="E:\hydrus"

start "" "pythonw" hydrus_client.pyw

REM Here is an alternate line that will keep the console open and show live log updates. Useful for boot/live debugging:
REM python hydrus_client.py

CALL venv\Scripts\deactivate.bat

popd
