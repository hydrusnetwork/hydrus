@ECHO off

IF EXIST "venv\" goto :venv_exists

SET /P ready=If you do not have Python 3 installed yet, check the 'running from source' help. Hit Enter to start.

goto :questions

:venv_exists

SET /P install_type=Virtual environment will be reinstalled. Hit Enter to start.

echo Deleting old venv...

rmdir /s /q venv

:questions

SET /P qt=Do you want Qt(5) or Qt(6)? 

IF "%qt%" == "5" goto :qt_ok
IF "%qt%" == "6" goto :qt_ok
goto :parse_fail

:qt_ok

SET /P mpv=Do you want (o)ld mpv or (n)ew mpv? 

IF "%mpv%" == "o" goto :mpv_ok
IF "%mpv%" == "n" goto :mpv_ok
goto :parse_fail

:mpv_ok

SET /P opencv=Do you want (o)ld OpenCV or (n)ew OpenCV? 

IF "%opencv%" == "o" goto :opencv_ok
IF "%opencv%" == "n" goto :opencv_ok
goto :parse_fail

:opencv_ok

:create

echo Creating new venv...

python -m venv venv

CALL venv\Scripts\activate.bat

python -m pip install --upgrade pip

pip3 install --upgrade wheel

pip3 install -r requirements_core.txt

IF "%qt%" == "5" pip3 install -r requirements_qt5.txt
IF "%qt%" == "6" pip3 install -r requirements_qt6.txt

IF "%mpv%" == "o" pip3 install -r requirements_old_mpv.txt
IF "%mpv%" == "n" pip3 install -r requirements_new_mpv.txt

IF "%opencv%" == "o" pip3 install -r requirements_old_opencv.txt
IF "%opencv%" == "n" pip3 install -r requirements_new_opencv.txt

CALL venv\Scripts\deactivate.bat

goto :done

:parse_fail

echo Sorry, did not understand that input!

:done

SET /P done=Done!
