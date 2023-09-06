@ECHO off

pushd "%~dp0"

where /q python
IF ERRORLEVEL 1 (

    SET /P gumpf="You do not seem to have python installed. Please check the 'running from source' help."

    popd

    EXIT /B 1

)

IF EXIST "venv\" (

    SET /P ready="Virtual environment will be reinstalled. Hit Enter to start."

    echo Deleting old venv...

    rmdir /s /q venv

) ELSE (

    SET /P ready="If you do not know what this is, check the 'running from source' help. Hit Enter to start."

)

:questions

ECHO:
ECHO Users on older Windows need the advanced install.
ECHO:
ECHO Your Python version is:
python --version
ECHO:
SET /P install_type="Do you want the (s)imple or (a)dvanced install? "

IF "%install_type%" == "s" goto :create
IF "%install_type%" == "a" goto :question_qt
IF "%install_type%" == "d" goto :create
goto :parse_fail

:question_qt

ECHO:
ECHO Qt is the User Interface library. We are now on Qt6.
ECHO If you are on Windows ^<=8.1, choose 5.
ECHO If you have multi-monitor menu position bugs with the normal Qt6, try the (o)lder build on Python ^<=3.10 or (m)iddle on Python ^>=3.11.
SET /P qt="Do you want Qt(5), Qt(6), Qt6 (o)lder, Qt6 (m)iddle or (t)est? "

IF "%qt%" == "5" goto :question_mpv
IF "%qt%" == "6" goto :question_mpv
IF "%qt%" == "o" goto :question_mpv
IF "%qt%" == "m" goto :question_mpv
IF "%qt%" == "t" goto :question_mpv
goto :parse_fail

:question_mpv

ECHO:
ECHO mpv is the main way to play audio and video. We need to tell hydrus how to talk to your mpv dll.
ECHO Try the n first. If it doesn't work, fall back to o.
SET /P mpv="Do you want (o)ld mpv, (n)ew mpv, or (t)est mpv? "

IF "%mpv%" == "o" goto :question_opencv
IF "%mpv%" == "n" goto :question_opencv
IF "%mpv%" == "t" goto :question_opencv
goto :parse_fail

:question_opencv

ECHO:
ECHO OpenCV is the main image processing library.
ECHO Try the n first. If it doesn't work, fall back to o. Very new python versions might need t.
SET /P opencv="Do you want (o)ld OpenCV, (n)ew OpenCV, or (t)est OpenCV? "

IF "%opencv%" == "o" goto :create
IF "%opencv%" == "n" goto :create
IF "%opencv%" == "t" goto :create
goto :parse_fail

:create

echo Creating new venv...

python -m venv venv

CALL venv\Scripts\activate.bat

IF ERRORLEVEL 1 (

    SET /P gumpf="The venv failed to activate, stopping now!"

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
    python -m pip install -r static\requirements\advanced\requirements_windows.txt

    python -m pip install -r static\requirements\advanced\requirements_qt6_test.txt
    python -m pip install pyside2
    python -m pip install PyQtChart PyQt5
    python -m pip install PyQt6-Charts PyQt6
    python -m pip install -r static\requirements\advanced\requirements_mpv_test.txt
    python -m pip install -r static\requirements\advanced\requirements_opencv_test.txt
    python -m pip install -r static\requirements\hydev\requirements_windows_build.txt

)

IF "%install_type%" == "a" (

    python -m pip install -r static\requirements\advanced\requirements_core.txt
    python -m pip install -r static\requirements\advanced\requirements_windows.txt

    IF "%qt%" == "5" python -m pip install -r static\requirements\advanced\requirements_qt5.txt
    IF "%qt%" == "6" python -m pip install -r static\requirements\advanced\requirements_qt6.txt
    IF "%qt%" == "o" python -m pip install -r static\requirements\advanced\requirements_qt6_older.txt
    IF "%qt%" == "m" python -m pip install -r static\requirements\advanced\requirements_qt6_middle.txt
    IF "%qt%" == "t" python -m pip install -r static\requirements\advanced\requirements_qt6_test.txt

    IF "%mpv%" == "o" python -m pip install -r static\requirements\advanced\requirements_mpv_old.txt
    IF "%mpv%" == "n" python -m pip install -r static\requirements\advanced\requirements_mpv_new.txt
    IF "%mpv%" == "t" python -m pip install -r static\requirements\advanced\requirements_mpv_test.txt

    IF "%opencv%" == "o" python -m pip install -r static\requirements\advanced\requirements_opencv_old.txt
    IF "%opencv%" == "n" python -m pip install -r static\requirements\advanced\requirements_opencv_new.txt
    IF "%opencv%" == "t" python -m pip install -r static\requirements\advanced\requirements_opencv_test.txt

)

CALL venv\Scripts\deactivate.bat

SET /P done="Done!"

popd

EXIT /B 0

:parse_fail

SET /P done="Sorry, did not understand that input!"

popd

EXIT /B 1
