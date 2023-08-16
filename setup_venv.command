#!/bin/bash

pushd "$(dirname "$0")" || exit 1

py_command=python3

if ! type -P $py_command >/dev/null 2>&1; then
	echo "No python3 found, using python."
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

echo "If your macOS is slightly old, do the advanced install. Let hydev know what works for you."
echo
echo "Your Python version is:"
$py_command --version
echo
echo "Do you want the (s)imple or (a)dvanced install? "

read -r install_type

if [ "$install_type" = "s" ]; then
	:
elif [ "$install_type" = "a" ]; then
	echo
	echo "Qt is the User Interface library. We are now on Qt6."
	echo "If you are <= 10.13 (High Sierra), choose 5. If you are <=10.15 (Catalina), choose o."
	echo "Do you want Qt(5), Qt(6), Qt6 (o)lder, or (t)est? "
	read -r qt
	if [ "$qt" = "5" ]; then
		:
	elif [ "$qt" = "6" ]; then
		:
	elif [ "$qt" = "o" ]; then
		:
	elif [ "$qt" = "t" ]; then
		:
	else
		echo "Sorry, did not understand that input!"
		popd || exit 1
		exit 1
	fi
	
	echo
	echo "mpv is broken on macOS. As a safe default, choose n."
	echo "Do you want (o)ld mpv or (n)ew mpv? "
	read -r mpv
	if [ "$mpv" = "o" ]; then
		:
	elif [ "$mpv" = "n" ]; then
		:
	else
		echo "Sorry, did not understand that input!"
		popd || exit 1
		exit 1
	fi
	
	echo
	echo "OpenCV is the main image processing library."
	echo "Try the n first. If it doesn't work, fall back to o. Very new python versions might need t."
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
	python -m pip install -r static/requirements/advanced/requirements_core.txt
	
	if [ "$qt" = "5" ]; then
		python -m pip install -r static/requirements/advanced/requirements_qt5.txt
	elif [ "$qt" = "6" ]; then
		python -m pip install -r static/requirements/advanced/requirements_qt6.txt
	elif [ "$qt" = "o" ]; then
		python -m pip install -r static/requirements/advanced/requirements_qt6_older.txt
	elif [ "$qt" = "t" ]; then
		python -m pip install -r static/requirements/advanced/requirements_qt6_test.txt
	fi
	
	if [ "$mpv" = "o" ]; then
		python -m pip install -r static/requirements/advanced/requirements_mpv_old.txt
	elif [ "$mpv" = "n" ]; then
		python -m pip install -r static/requirements/advanced/requirements_mpv_new.txt
	fi
	
	if [ "$opencv" = "o" ]; then
		python -m pip install -r static/requirements/advanced/requirements_opencv_old.txt
	elif [ "$opencv" = "n" ]; then
		python -m pip install -r static/requirements/advanced/requirements_opencv_new.txt
	elif [ "$opencv" = "t" ]; then
		python -m pip install -r static/requirements/advanced/requirements_opencv_test.txt
	fi
fi

deactivate

echo "Done!"

read -r

popd || exit
