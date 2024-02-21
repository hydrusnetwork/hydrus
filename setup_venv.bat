@ECHO off

pushd "%~dp0"

ECHO   r::::::::::::::::::::::::::::::::::r
ECHO   :                                  :
ECHO   :               :PP.               :
ECHO   :               vBBr               :
ECHO   :               7BB:               :
ECHO   :               rBB:               :
ECHO   :      :DQRE:   rBB:   :gMBb:      :
ECHO   :       :BBBi   rBB:   7BBB.       :
ECHO   :        KBB:   rBB:   rBBI        :
ECHO   :        qBB:   rBB:   rQBU        :
ECHO   :        qBB:   rBB:   iBBS        :
ECHO   :        qBB:   iBB:   7BBj        :
ECHO   :        iBBY   iBB.   2BB.        :
ECHO   :         SBQq  iBQ:  EBBY         :
ECHO   :          :MQBZMBBDRBBP.          :
ECHO   :              .YBB7               :
ECHO   :               :BB.               :
ECHO   :               7BBi               :
ECHO   :               rBB:               :
ECHO   :                                  :
ECHO   r::::::::::::::::::::::::::::::::::r
ECHO:
ECHO                  hydrus
ECHO:

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

IF EXIST "venv\" (

    SET /P gumpf="It looks like the venv directory did not delete correctly. Do you have it activated in a terminal or IDE anywhere? Please close that and try this again!"

    popd

    EXIT /B 1

)

:questions

ECHO --------
ECHO Users on older Windows or Python ^>=3.11 need the advanced install.
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

ECHO --------
ECHO We are now going to choose which versions of some larger libraries we are going to use. If something doesn't install, or hydrus won't boot, just run this script again and it will delete everything and start over.
ECHO:

ECHO Qt - User Interface
ECHO:
ECHO Most people want "6".
ECHO If you are on Windows ^<=8.1, choose "5". If you want a specific version, choose "a".
SET /P qt="Do you want Qt(5), Qt(6), or (a)dvanced? "

IF "%qt%" == "5" goto :question_mpv
IF "%qt%" == "6" goto :question_mpv
IF "%qt%" == "a" goto :question_qt_advanced
goto :parse_fail

:question_qt_advanced

ECHO:
ECHO If you have multi-monitor menu position bugs with the normal Qt6, try "o" on Python ^<=3.10 or "m" on Python ^>=3.11.
SET /P qt="Do you want Qt6 (o)lder, Qt6 (m)iddle, Qt6 (t)est, or (w)rite your own? "

IF "%qt%" == "o" goto :question_mpv
IF "%qt%" == "m" goto :question_mpv
IF "%qt%" == "t" goto :question_mpv
IF "%qt%" == "w" goto :question_qt_custom
goto :parse_fail

:question_qt_custom

ECHO:
SET /P qt_custom_pyside6="Enter the exact PySide6 version you want, e.g. '6.6.0': "
SET /P qt_custom_qtpy="Enter the exact qtpy version you want (probably '2.4.1'): "

goto :question_mpv

:question_mpv

ECHO --------
ECHO mpv - audio and video playback
ECHO:
ECHO We need to tell hydrus how to talk to your mpv dll.
ECHO Most people want "n".
ECHO If it doesn't work, fall back to "o".
SET /P mpv="Do you want (o)ld mpv, (n)ew mpv, or (t)est mpv? "

IF "%mpv%" == "o" goto :question_pillow
IF "%mpv%" == "n" goto :question_pillow
IF "%mpv%" == "t" goto :question_pillow
goto :parse_fail

:question_pillow

ECHO --------
ECHO Pillow - Images
ECHO:
ECHO Most people want "n".
ECHO If you are Python 3.7 or earlier, choose "o".
SET /P pillow="Do you want (o)ld pillow or (n)ew pillow? "

IF "%pillow%" == "o" goto :question_opencv
IF "%pillow%" == "n" goto :question_opencv
goto :parse_fail

:question_opencv

ECHO --------
ECHO OpenCV - Images
ECHO:
ECHO Most people want "n".
ECHO If it doesn't work, fall back to "o". Python ^>=3.11 might need "t".
SET /P opencv="Do you want (o)ld OpenCV, (n)ew OpenCV, or (t)est OpenCV? "

IF "%opencv%" == "o" goto :create
IF "%opencv%" == "n" goto :create
IF "%opencv%" == "t" goto :create
goto :parse_fail

:create

ECHO --------
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
    python -m pip install -r static\requirements\advanced\requirements_pillow_new.txt
    python -m pip install -r static\requirements\advanced\requirements_mpv_test.txt
    python -m pip install -r static\requirements\advanced\requirements_opencv_test.txt
    python -m pip install -r static\requirements\hydev\requirements_windows_build.txt

)

IF "%install_type%" == "a" (

    IF "%qt%" == "w" (

        python -m pip install QtPy==%qt_custom_qtpy%

        IF ERRORLEVEL 1 (

            SET /P gumpf="It looks like we could not find that qtpy version!"

            popd

            EXIT /B 1

        )

        python -m pip install PySide6==%qt_custom_pyside6%

        IF ERRORLEVEL 1 (

            SET /P gumpf="It looks like we could not find that PySide6 version!"

            popd

            EXIT /B 1

        )
    )

    python -m pip install -r static\requirements\advanced\requirements_core.txt
    python -m pip install -r static\requirements\advanced\requirements_windows.txt

    IF "%qt%" == "5" python -m pip install -r static\requirements\advanced\requirements_qt5.txt
    IF "%qt%" == "6" python -m pip install -r static\requirements\advanced\requirements_qt6.txt
    IF "%qt%" == "o" python -m pip install -r static\requirements\advanced\requirements_qt6_older.txt
    IF "%qt%" == "m" python -m pip install -r static\requirements\advanced\requirements_qt6_middle.txt
    IF "%qt%" == "t" python -m pip install -r static\requirements\advanced\requirements_qt6_test.txt

    IF "%pillow%" == "o" python -m pip install -r static\requirements\advanced\requirements_pillow_old.txt
    IF "%pillow%" == "n" python -m pip install -r static\requirements\advanced\requirements_pillow_new.txt

    IF "%mpv%" == "o" python -m pip install -r static\requirements\advanced\requirements_mpv_old.txt
    IF "%mpv%" == "n" python -m pip install -r static\requirements\advanced\requirements_mpv_new.txt
    IF "%mpv%" == "t" python -m pip install -r static\requirements\advanced\requirements_mpv_test.txt

    IF "%opencv%" == "o" python -m pip install -r static\requirements\advanced\requirements_opencv_old.txt
    IF "%opencv%" == "n" python -m pip install -r static\requirements\advanced\requirements_opencv_new.txt
    IF "%opencv%" == "t" python -m pip install -r static\requirements\advanced\requirements_opencv_test.txt

)

CALL venv\Scripts\deactivate.bat

ECHO --------
SET /P done="Done!"

popd

EXIT /B 0

:parse_fail

ECHO --------
SET /P done="Sorry, did not understand that input!"

popd

EXIT /B 1
