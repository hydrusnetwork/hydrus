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

echo "Users on Ubuntu <=20.04 equivalents or python >=3.10 need the advanced install."
echo
echo "Your Python version is:"
python --version
echo
echo "Do you want the (s)imple or (a)dvanced install? "

read install_type

if [ $install_type = "s" ]; then
	:
elif [ $install_type = "a" ]; then
	echo
	echo "If you are <=Ubuntu 18.04 or equivalent, choose 5."
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
	
	echo
	echo "If you are <=Ubuntu 20.04 or equivalent, you probably do not have libmpv1 0.34.1, so choose o."
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
		exit 1
	fi
else
	echo "Sorry, did not understand that input!"
	exit 1
fi

echo "Creating new venv..."
python -m venv venv

source venv/bin/activate

python -m pip install --upgrade pip

pip3 install --upgrade wheel

if [ $install_type = "s" ]; then
	pip3 install -r requirements.txt
elif [ $install_type = "a" ]; then
	pip3 install -r static/requirements/advanced/requirements_core.txt
	
	if [ $qt = "5" ]; then
		pip3 install -r static/requirements/advanced/requirements_qt5.txt
	elif [ $qt = "6" ]; then
		pip3 install -r static/requirements/advanced/requirements_qt6.txt
	fi
	
	if [ $mpv = "o" ]; then
		pip3 install -r static/requirements/advanced/requirements_old_mpv.txt
	elif [ $mpv = "n" ]; then
		pip3 install -r static/requirements/advanced/requirements_new_mpv.txt
	fi
	
	if [ $opencv = "o" ]; then
		pip3 install -r static/requirements/advanced/requirements_old_opencv.txt
	elif [ $opencv = "n" ]; then
		pip3 install -r static/requirements/advanced/requirements_new_opencv.txt
	fi
fi

deactivate

echo "Done!"
