#!/bin/bash

pushd "$(dirname "$0")"

py_command=python3

type -P $py_command

if [ $? -ne 0 ]; then
	echo "No python3 found, using python."
	py_command=python
fi

if [ -d "venv" ]; then
	echo "Virtual environment will be reinstalled. Hit Enter to start."
	read
	echo "Deleting old venv..."
	rm -rf venv
else
	echo "If you do not know what this is, check the 'running from source' help. Hit Enter to start."
	read
fi

echo "The precise version limits for macOS are not yet fully known. Please try the advanced install and let hydev know what works for you."
echo
echo "Your Python version is:"
$py_command --version
echo
echo "Do you want the (s)imple or (a)dvanced install? "

read install_type

if [ $install_type = "s" ]; then
	:
elif [ $install_type = "a" ]; then
	echo
	echo "If you are <= 10.13 (High Sierra), choose 5."
	echo "Do you want Qt(5) or Qt(6)? "
	read qt
	if [ $qt = "5" ]; then
		:
	elif [ $qt = "6" ]; then
		:
	else
		echo "Sorry, did not understand that input!"
		popd
		exit 1
	fi
	
	echo
	echo "mpv is broken on macOS. As a safe default, choose n."
	echo "Do you want (o)ld mpv or (n)ew mpv? "
	read mpv
	if [ $mpv = "o" ]; then
		:
	elif [ $mpv = "n" ]; then
		:
	else
		echo "Sorry, did not understand that input!"
		popd
		exit 1
	fi
	
	echo
	echo "If you are >=Python 3.10, choose n."
	echo "Do you want (o)ld OpenCV or (n)ew OpenCV? "
	read opencv
	if [ $opencv = "o" ]; then
		:
	elif [ $opencv = "n" ]; then
		:
	else
		echo "Sorry, did not understand that input!"
		popd
		exit 1
	fi
else
	echo "Sorry, did not understand that input!"
	popd
	exit 1
fi

echo "Creating new venv..."
$py_command -m venv venv

source venv/bin/activate

if [ $? -ne 0 ]; then
    echo "The venv failed to activate, stopping now!"
	popd
	exit 1
fi

python -m pip install --upgrade pip

python -m pip install --upgrade wheel

if [ $install_type = "s" ]; then
	python -m pip install -r requirements.txt
elif [ $install_type = "a" ]; then
	python -m pip install -r static/requirements/advanced/requirements_core.txt
	
	if [ $qt = "5" ]; then
		python -m pip install -r static/requirements/advanced/requirements_qt5.txt
	elif [ $qt = "6" ]; then
		python -m pip install -r static/requirements/advanced/requirements_qt6.txt
	fi
	
	if [ $mpv = "o" ]; then
		python -m pip install -r static/requirements/advanced/requirements_old_mpv.txt
	elif [ $mpv = "n" ]; then
		python -m pip install -r static/requirements/advanced/requirements_new_mpv.txt
	fi
	
	if [ $opencv = "o" ]; then
		python -m pip install -r static/requirements/advanced/requirements_old_opencv.txt
	elif [ $opencv = "n" ]; then
		python -m pip install -r static/requirements/advanced/requirements_new_opencv.txt
	fi
fi

deactivate

echo "Done!"

read

popd
