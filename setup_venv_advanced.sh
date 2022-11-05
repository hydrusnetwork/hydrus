#!/bin/bash

if [ -d "venv" ]; then
	echo "Virtual environment will be reinstalled. Hit Enter to start."
	read
	echo "Deleting old venv..."
	rm -rf venv
else
	echo "If you do not know what this is, check the 'running from source' help. Hit Enter to start."
	read
fi

echo "Do you want Qt(5) or Qt(6)? "
read qt
if [ $qt = "5" ]; then
	:
elif [ $qt = "6" ]; then
	:
else
	echo "Sorry, did not understand that input!"
	exit 1
fi

echo "Do you want (o)ld mpv or (n)ew mpv? "
read mpv
if [ $mpv = "o" ]; then
	:
elif [ $mpv = "n" ]; then
	:
else
	echo "Sorry, did not understand that input!"
	exit 1
fi

echo "Do you want (o)ld OpenCV or (n)ew OpenCV? "
read opencv
if [ $opencv = "o" ]; then
	:
elif [ $opencv = "n" ]; then
	:
else
	echo "Sorry, did not understand that input!"
	exit 1
fi

echo "Creating new venv..."
python -m venv venv

source venv/bin/activate

python -m pip install --upgrade pip

pip3 install --upgrade wheel

pip3 install -r requirements_core.txt

if [ $qt = "5" ]; then
	pip3 install -r requirements_qt5.txt
elif [ $qt = "6" ]; then
	pip3 install -r requirements_qt6.txt
fi

if [ $mpv = "o" ]; then
	pip3 install -r requirements_old_mpv.txt
elif [ $mpv = "n" ]; then
	pip3 install -r requirements_new_mpv.txt
fi

if [ $opencv = "o" ]; then
	pip3 install -r requirements_old_opencv.txt
elif [ $opencv = "n" ]; then
	pip3 install -r requirements_new_opencv.txt
fi

deactivate

echo "Done!"

read
