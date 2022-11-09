@ECHO off

IF NOT EXIST "venv\" (

	SET /P gumpf=Sorry, you do not seem to have a venv!
	EXIT /B 1
	
)

start venv\Scripts\activate.bat
