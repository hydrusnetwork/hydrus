@ECHO off

where /q git
IF ERRORLEVEL 1 (

	SET /P gumpf=You do not seem to git installed!
	EXIT /B 1
	
)

git pull

SET /P done=Done!
