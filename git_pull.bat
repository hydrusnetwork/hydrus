@ECHO off

pushd "%~dp0"

where /q git
IF ERRORLEVEL 1 (

	SET /P gumpf=You do not seem to have git installed!
	
	popd
	
	EXIT /B 1
	
)

git pull

popd

SET /P done=Done!
