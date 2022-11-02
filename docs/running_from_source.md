---
title: Running From Source  
---

# running from source

I write the client and server entirely in [python](https://python.org), which can run straight from source. It is getting simpler and simpler to run python programs like this, so don't be afraid of it. If none of the built packages work for you (for instance if you use Windows 7 or 18.04 Ubuntu (or equivalent)), it may be the only way you can get the program to run. Also, if you have a general interest in exploring the code or wish to otherwise modify the program, you will obviously need to do this.

## Simple Setup Guide

There are now setup scripts that make this easy on Windows and Linux. You do not need any python experience.

### Summary:

1. Get Python.
2. Get Hydrus source.
3. Get mpv/SQLite/FFMPEG.
4. Run setup_venv script.
5. Run setup_help script.
6. Run client script.

### Walkthrough

#### Core

!!! warning ".sh and .command are in testing"
    Hey, the .sh and .command setup files for Linux/macOS are new. I cannot promise they are bug free, so please only test them if you are brave and/or know a little about this, and let me know how it goes.

=== "Windows"

    First of all, you will need to install Python. Get 3.8.x or 3.9.x [here](https://www.python.org/downloads/windows/). During the install process, make sure it has something like 'Add Python to PATH' checked. This makes Python available to your Windows.

=== "Linux"

    You should already have a fairly new python. Ideally, you want 3.8.x or 3.9.x. If you are on 3.10.x, run the 'advanced' setup script later on and choose the newer OpenCV.

=== "macOS"

    You should already have python of about the correct version.

Then, get the hydrus source. The github repo is [https://github.com/hydrusnetwork/hydrus](https://github.com/hydrusnetwork/hydrus). If you are familiar with git, you can just clone the repo to the location you want with `git clone https://github.com/hydrusnetwork/hydrus`, but if not, then just go to the [latest release](https://github.com/hydrusnetwork/hydrus/releases/latest) and download and extract the source code .zip somewhere. Make sure the directory has write permissions (e.g. don't put it in "Program Files"). Extracting straight to a spare drive, something like "D:\Hydrus Network", is ideal.

We will call the base extract directory, the one with 'client.py' in it, `install_dir`.

!!! info "Mixed Builds"
    Don't mix and match build extracts and source extracts. The process that runs the code gets confused if there are unexpected extra .dlls in the directory. If you need to convert between built and source releases, perform a [clean install](getting_started_installing.md#clean_installs).

#### Built Programs

There are three external libraries. You just have to get them and put them in the correct place:

=== "Windows"

    1. mpv  
        
        1. If you are on Windows 7, get [this](https://sourceforge.net/projects/mpv-player-windows/files/libmpv/mpv-dev-x86_64-20210228-git-d1be8bb.7z).
        2. If you are on Windows 8 or newer, get [this](https://sourceforge.net/projects/mpv-player-windows/files/libmpv/mpv-dev-x86_64-20220501-git-9ffaa6b.7z).
        
        Then open that archive and place the 'mpv-1.dll' or 'mpv-2.dll' into `install_dir`.
        
    2. SQLite3  
        
        Go to `install_dir/static/build_files/windows` and copy 'sqlite3.dll' into `install_dir`.
        
    3. FFMPEG  
        
        Get a Windows build of FFMPEG [here](https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-full.7z).
        
        Extract the ffmpeg.exe into `install_dir/bin`.
        

=== "Linux"

    1. mpv  
        
        Try running `apt-get install libmpv1` in a new terminal. You can type `apt show libmpv1` to see your current version. Or, if you use a different package manager, try searching `libmpv` or `libmpv1` on that.
        
        1. If you have earlier than 0.34.1, you will be looking at running the 'advanced' setup script in the next section and selecting the 'old' mpv.
        2. If you have 0.34.1 or later, you can run the normal setup script.
        
    2. SQLite3  
        
        No action needed.
        
    3. FFMPEG  
        
        You should already have ffmpeg. Just type `ffmpeg` into a new terminal, and it should give a basic version response. If you somehow don't have ffmpeg, check your package manager.
        

=== "macOS"

    1. mpv  
        
        Unfortunately, mpv is not well supported in macOS yet. You may be able to install it in brew, but it seems to freeze the client as soon as it is loaded. Hydev is thinking about fixes here.
        
    2. SQLite3  
        
        No action needed.
        
    3. FFMPEG  
        
        You should already have ffmpeg.
        

#### Environment setup

=== "Windows"

    1. If you are on Windows 7, you want 'setup_venv_advanced.bat'.
    2. Everyone else go for 'setup_venv.bat'.
    
    Just double-click the file.

=== "Linux"

    1. If you are on or below Ubuntu 20.04 or equivalent, or are otherwise stuck with an older mpv version, you want 'setup_venv_advanced.sh'.
    2. Everyone else go for 'setup_venv.sh'.
    
    You might be able to double-click the file. Otherwise, open a terminal in the folder and type:  
    `. setup_venv.sh`

=== "macOS"

    I do not know which versions of macOS are unable to run Qt6, so you probably want to try setup_venv.command, and if that fails, experiment with setup_venv_advanced.command. Try Qt5 and the other older libraries first, then test the newer ones later.
    
    Please let me know what you discover.

The setup should take a minute to download its packages and a couple minutes to install them. Do not close it until it is finished installing everything and says 'Done!'. If it seems like it hung, just give it time to finish.

!!! info "Advanced Setup"
    The advanced setup script allows you to choose between old or newer versions of several libraries:  
    
    1. Qt: Win 7 and Ubuntu 18.04 equivalents should go for Qt5, everyone else Qt6.
    2. mpv: Win 7 and Ubuntu 20.04 equivalents should go for the old one, everyone else the new.
    3. OpenCV: Does not matter much, but Python 3.10 users may need the new.

If something messes up, or you want to switch between Qt5/Qt6, just run the setup script again and it will reinstall everything. Everything these scripts do ends up in the 'venv' directory, so you can also just delete that folder to 'uninstall'. It should _just work_ on most normal computers, but let me know if you have any trouble.

Then run the 'setup_help' script to build the help. This isn't necessary, but it is nice to have it built locally. You can run this again at any time to rebuild the current help.

#### Running it

=== "Windows"

    Run 'client.bat' to start the client.

=== "Linux"

    Run 'client.sh' to start the client.

=== "macOS"

    Run 'client.command' to start the client.

The first start will take a little longer. It will operate just like a normal build, putting your database in the 'db' directory.

!!! warning "Missing a Library"
    If the client fails to boot, it should place a 'hydrus_crash.log' in your 'db' directory or your desktop, or, if it got far enough, it may write the error straight to the 'client - date.log' file in your db directory.  

    If that error talks about a missing library, then try reinstalling your venv. Are you sure it finished correctly? Are you sure you have the correct Qt version?

=== "Windows"

    If you want to redirect your database or use any other launch arguments, then copy 'client.bat' to 'client-user.bat' and edit it, inserting your desired db path. Run this instead of 'client.bat'. New `git pull` commands will not affect 'client-user.bat'.
    
    You probably can't pin your .bat file to your Taskbar or Start (and if you try and pin the running program to your taskbar, its icon may revert to Python), but you can make a shortcut to the .bat file, pin that to Start, and in its properties set a custom icon. There's a nice hydrus one in `install_dir/static`.

=== "Linux"

    If you want to redirect your database or use any other launch arguments, then copy 'client.sh' to 'client-user.sh' and edit it, inserting your desired db path. Run this instead of 'client.sh'. New `git pull` commands will not affect 'client-user.sh'.

=== "macOS"

    If you want to redirect your database or use any other launch arguments, then copy 'client.command' to 'client-user.command' and edit it, inserting your desired db path. Run this instead of 'client.command'. New `git pull` commands will not affect 'client-user.command'.

## Simple Updating Guide

To update, you do the same thing as for the extract builds.

1. If you installed by extracting the source zip, then download the [latest release](https://github.com/hydrusnetwork/hydrus/releases/latest) source zip and extract it over the top of the folder you have, overwriting the existing source files.
2. If you installed with git, then just run `git pull` as normal.

If you get a library version error when you try to boot, run the venv setup again. It is worth doing this anyway, every now and then, just to stay up to date.

## doing it manually { id="what_you_need" }

_This is for advanced users only._

Inside the extract should be client.py and server.py. You will be treating these basically the same as the 'client' and 'server' executables--you should be able to launch them the same way and they take the same launch parameters as the exes.

Hydrus needs a whole bunch of libraries, so let's now set your python up. I **strongly** recommend you create a virtual environment. It is easy and doesn't mess up your system python.

_Note, if you are on Linux and you have trouble with venv, it may be easier to use your package manager instead. A user has written a great summary with all needed packages [here](running_from_source_linux_packages.txt)._

To create a new venv environment:

* Open a terminal at your hydrus extract folder.
* `pip3 install virtualenv` (if you need it)
* `python3 -m venv venv`
* `source venv/bin/activate`
* `python -m pip install --upgrade pip`
* `pip3 install --upgrade wheel`

That `source venv/bin/activate` line turns on your venv, which is an isolated copy of python that you can install modules to without worrying about breaking something system-wide. This line will be needed every time you run the `client.py`/`server.py` files. You should see your terminal note you are now in the venv. You can easily tuck this venv activation line into a launch script--check the easy setup files for examples.

On Windows Powershell, the command is `.\venv\Scripts\activate`, but you may find the whole deal is done much easier in cmd than Powershell. When in Powershell, just type `cmd` to get an old fashioned command line. In cmd, the launch command is just `venv\scripts\activate.bat`, no leading period.

After you have activated the venv, you can use pip to install everything you need to it from the requirements.txt in the install_dir:

```
pip install -r requirements.txt
```

You can also pick and choose from the other advanced requirements. Check and compare their contents to the main requirements.txt to see what is going on.

## Qt { id="qt" }

Qt is the UI library. You can run PySide2, PySide6, PyQt5, or PyQt6. A wrapper library called `qtpy` allows this. The default is PySide6, but it is missing and any others are available, it will fall back to them. For PyQt5 or PyQt6, you need an extra Chart module, so go:

```
pip3 install qtpy PyQtChart PyQt5
-or-
pip3 install qtpy PyQt6-Charts PyQt6
```

If you have multiple Qts installed, then select which one you want to use by setting the `QT_API` environment variable to 'pyside2', 'pyside6', 'pyqt5', or 'pyqt6'. Check _help->about_ to make sure it loaded the right one.

If you want to set QT_API in a batch file, do this:

`set QT_API=pyqt6`

If you run Windows 7 or Ubuntu 18.04, you cannot run Qt6. Please try PySide2 or PyQt5.

## mpv support { id="mpv" }

MPV is optional and complicated, but it is great, so it is worth the time to figure out!

As well as the python wrapper, 'python-mpv' (which is in the requirements.txt), you also need the underlying library. This is _not_ mpv the program, but 'libmpv', often called 'libmpv1'.

For Windows, the dll builds are [here](https://sourceforge.net/projects/mpv-player-windows/files/libmpv/), although getting a stable version can be difficult. Just put it in your hydrus base install directory. Check the links in the easy-setup guide above for good versions.

You can also just grab the 'mpv-1.dll'/'mpv-2.dll' I bundle in my extractable Windows release.

If you are on Linux, you can usually get 'libmpv1' like so:

`apt-get install libmpv1`

On macOS, you should be able to get it with `brew install mpv`, but you are likely to find mpv crashes the program when it tries to load. Hydev is working on this, but it will probably need a completely different render API.

Hit _help->about_ to see your mpv status. If you don't have it, it will present an error popup box with more info.

## SQLite { id="sqlite" }

If you can, update python's SQLite--it'll improve performance.

On Windows, get the 64-bit sqlite3.dll [here](https://www.sqlite.org/download.html), and just drop it in your base install directory.

You can also just grab the 'sqlite3.dll' I bundle in my extractable Windows release.

I don't know how to do this for Linux or macOS, so if you do, please let me know!

!!! warning "Extremely safe no way it can go wrong"
    If you want to update sqlite for your system python install, you can also drop it into `C:\Python38\DLLs` or wherever you have python installed. You'll be overwriting the old file, so make a backup if you want to (I have never had trouble updating like this, however).

## FFMPEG { id="ffmpeg" }

If you don't have FFMPEG in your PATH and you want to import anything more fun than jpegs, you will need to put a static [FFMPEG](https://ffmpeg.org/) executable in your PATH or the `install_dir/bin` directory. [This](https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-full.7z) should always point to a new build.

Alternately, you can just copy the exe from one of my extractable Windows releases.

## building packages on windows { id="windows_build" }

Almost everything is provided as pre-compiled 'wheels' these days, but if you get an error about Visual Studio C++ when you try to pip something, it may be you need that compiler tech.

You also need this if you want to build a frozen release locally.

Although these tools are free, it can be a pain to get them through the official (and often huge) downloader installer from Microsoft. Instead, install [Chocolatey](https://chocolatey.org/) and use this one simple line:

```
choco install -y vcbuildtools visualstudio2017buildtools
```

Trust me, just do this, it will save a ton of headaches!

This can also be helpful for Windows 10 python work generally:

```
choco install -y windows-sdk-10.0
```

## additional windows info { id="additional_windows" }

This does not matter much any more, but in the old days, Windows pip could have problems building modules like lz4 and lxml, and Visual Studio was tricky to get working. [This page](http://www.lfd.uci.edu/~gohlke/pythonlibs/) has a lot of prebuilt binaries--I have found it very helpful many times.

I have a fair bit of experience with Windows python, so send me a mail if you need help.

## running it { id="running_it" }

Once you have everything set up, client.py and server.py should look for and run off client.db and server.db just like the executables. They will look in the 'db' directory by default, or anywhere you point them with the "-d" parameter, again just like the executables. Explictly, you will be entering something like this in the terminal:

```
source venv/bin/activate
python client.py -d="/path/to/database"
```

Again, you may want to set up a shortcut to a script to make it easy.

I develop hydrus on and am most experienced with Windows, so the program is more stable and reasonable on that. I do not have as much experience with Linux or macOS, but I still appreciate and will work on your Linux/macOS bug reports.

## Building the docs

When running from source you will also need to [build the hydrus help docs](about_docs.md) yourself.

## my code { id="my_code" }

My coding style is unusual and unprofessional. Everything is pretty much hacked together. If you are interested in how things work, please do look through the source and ask me if you don't understand something.

I'm constantly throwing new code together and then cleaning and overhauling it down the line. I work strictly alone, however, so while I am very interested in detailed bug reports or suggestions for good libraries to use, I am not looking for pull requests or suggestions on style. I know a lot of things are a mess. Everything I do is [WTFPL](https://github.com/sirkris/WTFPL/blob/master/WTFPL.md), so feel free to fork and play around with things on your end as much as you like.
