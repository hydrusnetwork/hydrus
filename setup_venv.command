#!/bin/bash

pushd "$(dirname "$0")" || exit 1

echo "   r::::::::::::::::::::::::::::::::::r"
echo "   :                                  :"
echo "   :               :PP.               :"
echo "   :               vBBr               :"
echo "   :               7BB:               :"
echo "   :               rBB:               :"
echo "   :      :DQRE:   rBB:   :gMBb:      :"
echo "   :       :BBBi   rBB:   7BBB.       :"
echo "   :        KBB:   rBB:   rBBI        :"
echo "   :        qBB:   rBB:   rQBU        :"
echo "   :        qBB:   rBB:   iBBS        :"
echo "   :        qBB:   iBB:   7BBj        :"
echo "   :        iBBY   iBB.   2BB.        :"
echo "   :         SBQq  iBQ:  EBBY         :"
echo "   :          :MQBZMBBDRBBP.          :"
echo "   :              .YBB7               :"
echo "   :               :BB.               :"
echo "   :               7BBi               :"
echo "   :               rBB:               :"
echo "   :                                  :"
echo "   r::::::::::::::::::::::::::::::::::r"
echo
echo "                  hydrus"
echo

py_command=python3

if ! type -P $py_command >/dev/null 2>&1; then
    echo "No \"python3\" found, using \"python\"."
    py_command=python
fi

if [ -d "venv" ]; then
    echo "Virtual environment will be reinstalled. Hit Enter to start."
    read -r
    echo "Deleting old venv..."
    rm -rf venv
else
    echo "If you do not know what this is, check the 'running from source' help. Hit Enter to start."
    read -r
fi

if [ -d "venv" ]; then
    echo "It looks like the venv directory did not delete correctly. Do you have it activated in a terminal or IDE anywhere? Please close that and try this again!"
    exit 1
fi

echo "--------"
echo "If your macOS is old, or you are on >=Python 3.11, do the advanced install. Let hydev know what works for you."
echo
echo "Your Python version is:"
$py_command --version
echo
echo "Do you want the (s)imple or (a)dvanced install? "

read -r install_type

if [ "$install_type" = "s" ]; then
    :
elif [ "$install_type" = "a" ]; then
    echo "--------"
    echo "We are now going to choose which versions of some larger libraries we are going to use. If something doesn't install, or hydrus won't boot, just run this script again and it will delete everything and start over."
    echo
    echo "Qt - User Interface"
    echo "Most people want \"6\"."
    echo "If you are <= 10.13 (High Sierra), choose \"5\". If you want a specific version, choose \"a\"."
    echo "Do you want Qt(5), Qt(6), or (a)dvanced? "
    read -r qt
    if [ "$qt" = "5" ]; then
        :
    elif [ "$qt" = "6" ]; then
        :
    elif [ "$qt" = "a" ]; then
        :
    else
        echo "Sorry, did not understand that input!"
        exit 1
    fi

    if [ "$qt" = "a" ]; then
        echo
        echo "If you are <=10.15 (Catalina) or otherwise have trouble with the normal Qt6, try \"o\" on Python <=3.10 or \"m\" on Python >=3.11."
        echo "Do you want Qt6 (o)lder, Qt6 (m)iddle, Qt6 (t)est, or (w)rite your own? "
        read -r qt
        if [ "$qt" = "o" ]; then
            :
        elif [ "$qt" = "m" ]; then
            :
        elif [ "$qt" = "t" ]; then
            :
        elif [ "$qt" = "w" ]; then
            :
        else
            echo "Sorry, did not understand that input!"
            exit 1
        fi
    fi

    if [ "$qt" = "w" ]; then
        echo
        echo "Enter the exact PySide6 version you want, e.g. '6.6.0': "
        read -r qt_custom_pyside6
        echo "Enter the exact qtpy version you want (probably '2.4.1'): "
        read -r qt_custom_qtpy
    fi

    echo "--------"
    echo "mpv - audio and video playback"
    echo
    echo "mpv is broken on macOS. As a safe default, choose \"n\"."
    echo "Do you want (o)ld mpv, (n)ew mpv, or (t)est mpv? "
    read -r mpv
    if [ "$mpv" = "o" ]; then
        :
    elif [ "$mpv" = "n" ]; then
        :
    elif [ "$mpv" = "t" ]; then
        :
    else
        echo "Sorry, did not understand that input!"
        popd || exit 1
        exit 1
    fi

    echo "--------"
    echo "Pillow - Images"
    echo
    echo "Most people want \"n\"."
    echo "If you are Python 3.7 or earlier, choose \"o\""
    echo "Do you want (o)ld pillow or (n)ew pillow? "
    read -r pillow
    if [ "$pillow" = "o" ]; then
        :
    elif [ "$pillow" = "n" ]; then
        :
    else
        echo "Sorry, did not understand that input!"
        popd || exit 1
        exit 1
    fi

    echo "--------"
    echo "OpenCV - Images"
    echo
    echo "Most people want \"n\"."
    echo "If it doesn't work, fall back to \"o\". Python >=3.11 might need \"t\"."
    echo "Do you want (o)ld OpenCV, (n)ew OpenCV, or (t)est OpenCV? "
    read -r opencv
    if [ "$opencv" = "o" ]; then
        :
    elif [ "$opencv" = "n" ]; then
        :
    elif [ "$opencv" = "t" ]; then
        :
    else
        echo "Sorry, did not understand that input!"
        popd || exit 1
        exit 1
    fi
else
    echo "Sorry, did not understand that input!"
    popd || exit 1
    exit 1
fi

echo "--------"
echo "Creating new venv..."
$py_command -m venv venv

source venv/bin/activate

if ! source venv/bin/activate; then
    echo "The venv failed to activate, stopping now!"
    popd || exit 1
    exit 1
fi

python -m pip install --upgrade pip

python -m pip install --upgrade wheel

if [ "$install_type" = "s" ]; then

    python -m pip install -r requirements.txt

elif [ "$install_type" = "a" ]; then

    if [ "$qt" = "w" ]; then

        python -m pip install qtpy=="$qt_custom_qtpy"

        if [ $? -ne 0 ]; then
            echo "It looks like we could not find that qtpy version!"
            popd || exit 1
            exit 1
        fi

        python -m pip install PySide6=="$qt_custom_pyside6"

        if [ $? -ne 0 ]; then
            echo "It looks like we could not find that PySide6 version!"
            popd || exit 1
            exit 1
        fi
    fi

    python -m pip install -r static/requirements/advanced/requirements_core.txt

    if [ "$qt" = "5" ]; then
        python -m pip install -r static/requirements/advanced/requirements_qt5.txt
    elif [ "$qt" = "6" ]; then
        python -m pip install -r static/requirements/advanced/requirements_qt6.txt
    elif [ "$qt" = "o" ]; then
        python -m pip install -r static/requirements/advanced/requirements_qt6_older.txt
    elif [ "$qt" = "m" ]; then
        python -m pip install -r static/requirements/advanced/requirements_qt6_middle.txt
    elif [ "$qt" = "t" ]; then
        python -m pip install -r static/requirements/advanced/requirements_qt6_test.txt
    fi

    if [ "$mpv" = "o" ]; then
        python -m pip install -r static/requirements/advanced/requirements_mpv_old.txt
    elif [ "$mpv" = "n" ]; then
        python -m pip install -r static/requirements/advanced/requirements_mpv_new.txt
    elif [ "$mpv" = "t" ]; then
        python -m pip install -r static/requirements/advanced/requirements_mpv_test.txt
    fi

    if [ "$pillow" = "o" ]; then
        python -m pip install -r static/requirements/advanced/requirements_pillow_old.txt
    elif [ "$pillow" = "n" ]; then
        python -m pip install -r static/requirements/advanced/requirements_pillow_new.txt
    fi

    if [ "$opencv" = "o" ]; then
        python -m pip install -r static/requirements/advanced/requirements_opencv_old.txt
    elif [ "$opencv" = "n" ]; then
        python -m pip install -r static/requirements/advanced/requirements_opencv_new.txt
    elif [ "$opencv" = "t" ]; then
        python -m pip install -r static/requirements/advanced/requirements_opencv_test.txt
    fi
fi

python -m pip install -r static/requirements/advanced/requirements/requirements_macos.txt

deactivate

echo "--------"
echo "Done!"

read -r

popd || exit
