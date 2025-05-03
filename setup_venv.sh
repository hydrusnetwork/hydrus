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
echo "Users on older OSes need the advanced install. Python 3.13 will need the advanced install for newer '(t)est' Qt."
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
    echo "Most people want \"n\"."
    echo "If you cannot boot with the normal Qt, try \"o\" or \"w\"."
    echo "Do you want the (o)lder Qt, (n)ew Qt, (t)est Qt, (q) for PyQt6, or (w)rite your own? "
    read -r qt
    if [ "$qt" = "o" ]; then
        :
    elif [ "$qt" = "n" ]; then
        :
    elif [ "$qt" = "q" ]; then
        :
    elif [ "$qt" = "t" ]; then
        :
    elif [ "$qt" = "w" ]; then
        :
    else
        echo "Sorry, did not understand that input!"
        exit 1
    fi

    if [ "$qt" = "w" ]; then
        echo
        echo "Enter the exact PySide6 version you want, e.g. '6.6.0':"
        echo "- For Python 3.10, your earliest available version is 6.2.0"
        echo "- For Python 3.11, your earliest available version is 6.4.0.1"
        echo "- For Python 3.12, your earliest available version is 6.6.0"
        echo "- For Python 3.13, your earliest available version is 6.8.0.2"
        echo "Version: "
        read -r qt_custom_pyside6
        echo "Enter the exact qtpy version you want (probably '2.4.1'; if older try '2.3.1'): "
        read -r qt_custom_qtpy
    fi

    echo "--------"
    echo "mpv - audio and video playback"
    echo
    echo "We need to tell hydrus how to talk to your existing mpv install."
    echo "Most people want \"n\"."
    echo "If it doesn't work, fall back to \"o\"."
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
    echo "OpenCV - Images"
    echo
    echo "Most people want \"n\"."
    echo "Python >=3.11 might need \"t\"."
    echo "Do you want (n)ew OpenCV or (t)est OpenCV? "
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

    future=n

    # comment this guy out if no special stuff going on
    echo "--------"
    echo "Future Libraries"
    echo
    echo "There is a test for a new AVIF library. Want to try it?"
    echo "(y)es/(n)o? "
    read -r future
    if [ "$future" = "y" ]; then
        :
    elif [ "$future" = "n" ]; then
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

    if [ "$qt" = "n" ]; then
        python -m pip install -r static/requirements/advanced/requirements_qt6_new.txt
    elif [ "$qt" = "o" ]; then
        python -m pip install -r static/requirements/advanced/requirements_qt6_older.txt
    elif [ "$qt" = "q" ]; then
        python -m pip install -r static/requirements/advanced/requirements_qt6_new_pyqt6.txt
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

    if [ "$opencv" = "o" ]; then
        python -m pip install -r static/requirements/advanced/requirements_opencv_old.txt
    elif [ "$opencv" = "n" ]; then
        python -m pip install -r static/requirements/advanced/requirements_opencv_new.txt
    elif [ "$opencv" = "t" ]; then
        python -m pip install -r static/requirements/advanced/requirements_opencv_test.txt
    fi

    if [ "$future" = "n" ]; then
        python -m pip install -r static/requirements/advanced/requirements_other_normal.txt
    elif [ "$future" = "y" ]; then
        python -m pip install -r static/requirements/advanced/requirements_other_future.txt
    fi

fi

deactivate

echo "--------"
echo "Done!"

popd || exit
