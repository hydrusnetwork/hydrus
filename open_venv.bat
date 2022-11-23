@ECHO off

pushd "%~dp0"

IF NOT EXIST "venv\" (

	SET /P gumpf=Sorry, you do not seem to have a venv!
	
	popd
	
	EXIT /B 1
	
)

ECHO Type 'deactivate' to return.

CALL venv\Scripts\activate.bat
