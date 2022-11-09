@ECHO off

where /q python
IF ERRORLEVEL 1 (
	
	SET /P gumpf=You do not seem to have python installed. Please check the 'running from source' help.
	EXIT /B 1
	
)

IF EXIST "venv\" (
	
	SET /P ready=Virtual environment will be reinstalled. Hit Enter to start.
	
	echo Deleting old venv...
	
	rmdir /s /q venv
	
) ELSE (
	
	SET /P ready=If you do not know what this is, check the 'running from source' help. Hit Enter to start.
	
)

:questions

ECHO:
ECHO Users on Windows ^<=8.1 or python ^>=3.10 need the advanced install.
ECHO:
ECHO Your Python version is:
python --version
ECHO:
SET /P install_type=Do you want the (s)imple or (a)dvanced install? 

IF "%install_type%" == "s" goto :create
IF "%install_type%" == "a" goto :question_qt
goto :parse_fail

:question_qt

ECHO:
ECHO If you are on Windows 7, choose 5.
SET /P qt=Do you want Qt(5) or Qt(6)? 

IF "%qt%" == "5" goto :question_mpv
IF "%qt%" == "6" goto :question_mpv
goto :parse_fail

:question_mpv

ECHO:
ECHO If you have mpv-2.dll, choose n.
SET /P mpv=Do you want (o)ld mpv or (n)ew mpv? 

IF "%mpv%" == "o" goto :question_opencv
IF "%mpv%" == "n" goto :question_opencv
goto :parse_fail

:question_opencv

ECHO:
ECHO If you are ^>=Python 3.10, choose n.
SET /P opencv=Do you want (o)ld OpenCV or (n)ew OpenCV? 

IF "%opencv%" == "o" goto :create
IF "%opencv%" == "n" goto :create
goto :parse_fail

:create

echo Creating new venv...

python -m venv venv

CALL venv\Scripts\activate.bat

python -m pip install --upgrade pip

pip3 install --upgrade wheel

IF "%install_type%" == "s" (
	
	pip3 install -r requirements.txt
	
) ELSE (
	
	pip3 install -r static\requirements\advanced\requirements_core.txt
	
	IF "%qt%" == "5" pip3 install -r static\requirements\advanced\requirements_qt5.txt
	IF "%qt%" == "6" pip3 install -r static\requirements\advanced\requirements_qt6.txt
	
	IF "%mpv%" == "o" pip3 install -r static\requirements\advanced\requirements_old_mpv.txt
	IF "%mpv%" == "n" pip3 install -r static\requirements\advanced\requirements_new_mpv.txt
	
	IF "%opencv%" == "o" pip3 install -r static\requirements\advanced\requirements_old_opencv.txt
	IF "%opencv%" == "n" pip3 install -r static\requirements\advanced\requirements_new_opencv.txt
	
)

CALL venv\Scripts\deactivate.bat

SET /P done=Done!
EXIT /B 0

:parse_fail

SET /P done=Sorry, did not understand that input!
EXIT /B 1
