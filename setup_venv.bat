@ECHO off

pushd "%~dp0"

where /q python
IF ERRORLEVEL 1 (
	
	SET /P gumpf=You do not seem to have python installed. Please check the 'running from source' help.
	
	popd
	
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
IF "%install_type%" == "d" goto :create
goto :parse_fail

:question_qt

ECHO:
ECHO If you are on Windows ^<=8.1, choose 5.
SET /P qt=Do you want Qt(5), Qt(6), or (t)est? 

IF "%qt%" == "5" goto :question_mpv
IF "%qt%" == "6" goto :question_mpv
IF "%qt%" == "t" goto :question_mpv
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

IF ERRORLEVEL 1 (
	
	SET /P gumpf=The venv failed to activate, stopping now!
	
	popd
	
	EXIT /B 1
	
)

python -m pip install --upgrade pip

python -m pip install --upgrade wheel

IF "%install_type%" == "s" (
	
	python -m pip install -r requirements.txt
	
)

IF "%install_type%" == "d" (

	python -m pip install -r static\requirements\advanced\requirements_core.txt
	
	python -m pip install -r static\requirements\advanced\requirements_qt6_test.txt
	python -m pip install pyside2
	python -m pip install PyQtChart PyQt5
	python -m pip install PyQt6-Charts PyQt6
	python -m pip install -r static\requirements\advanced\requirements_new_mpv.txt
	python -m pip install -r static\requirements\advanced\requirements_new_opencv.txt
	python -m pip install -r static\requirements\hydev\requirements_windows_build.txt
	
)

IF "%install_type%" == "a" (
	
	python -m pip install -r static\requirements\advanced\requirements_core.txt
	
	IF "%qt%" == "5" python -m pip install -r static\requirements\advanced\requirements_qt5.txt
	IF "%qt%" == "6" python -m pip install -r static\requirements\advanced\requirements_qt6.txt
	IF "%qt%" == "t" python -m pip install -r static\requirements\advanced\requirements_qt6_test.txt
	
	IF "%mpv%" == "o" python -m pip install -r static\requirements\advanced\requirements_old_mpv.txt
	IF "%mpv%" == "n" python -m pip install -r static\requirements\advanced\requirements_new_mpv.txt
	
	IF "%opencv%" == "o" python -m pip install -r static\requirements\advanced\requirements_old_opencv.txt
	IF "%opencv%" == "n" python -m pip install -r static\requirements\advanced\requirements_new_opencv.txt
	
)

CALL venv\Scripts\deactivate.bat

SET /P done=Done!

popd

EXIT /B 0

:parse_fail

SET /P done=Sorry, did not understand that input!

popd

EXIT /B 1
