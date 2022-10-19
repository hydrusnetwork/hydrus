---
title: Running From Source  
---

# running from source

I write the client and server entirely in [python](https://python.org), which can run straight from source. It is getting simpler and simpler to run python programs like this, so don't be afraid of it. If none of the built packages work for you (for instance if you use Windows 7 or a non-Ubuntu-compatible flavour of Linux), it may be the only way you can get the program to run. Also, if you have a general interest in exploring the code or wish to otherwise modify the program, you will obviously need to do this.

## Simple Windows Guide

There are now batch files that make setup easy. You do not need any python experience.

### Summary:

1. Get Python.
2. Get Hydrus source.
3. Get FFMPEG/mpv/sqlite.
4. Run 'setup_venv.bat'.
5. Run 'setup_help.bat'.
6. Run 'client.bat'.

### Walkthrough

#### Core

First of all, if you do not have python installed, get 3.8.x or 3.9.x [here](https://www.python.org/downloads/windows/). During the install process, make sure it has something like 'Add Python to PATH' checked. This makes Python available to your Windows.

Then, get the hydrus source. The github repo is [https://github.com/hydrusnetwork/hydrus](https://github.com/hydrusnetwork/hydrus). If you are familiar with git, you can just clone the repo to the location you want with `git clone https://github.com/hydrusnetwork/hydrus`, but if not, then just go to the [latest release](https://github.com/hydrusnetwork/hydrus/releases/latest) and download and extract the source code .zip somewhere. Make sure the directory has write permissions (e.g. don't put it in "Program Files"). Extracting straight to a spare drive, something like "D:\Hydrus Network", is ideal.

We will call the base extract directory, the one with 'client.py' in it, `install_dir`.

!!! info "Notes"
    Don't mix and match build extracts and source extracts. The process that runs the code gets confused if there are extra .dlls in the directory. If you need to convert between built and source releases, perform a [clean install](getting_started_installing.md#clean_installs).

#### Built Programs

There are three external libraries. You just have to get them and put them in the correct place:

1. mpv
    
    1. If you are on Windows 7, get [this](https://sourceforge.net/projects/mpv-player-windows/files/libmpv/mpv-dev-x86_64-20210228-git-d1be8bb.7z).
    2. If you are on Windows 8 or newer, get [this](https://sourceforge.net/projects/mpv-player-windows/files/libmpv/mpv-dev-x86_64-20220501-git-9ffaa6b.7z).
    
    Then open that archive and place the 'mpv-1.dll' or 'mpv-2.dll' into `install_dir`.
    
2. sqlite3
    
    Go to `install_dir/static/build_files/windows` and copy 'sqlite3.dll' into `install_dir`.
    
3. ffmpeg
    
    Get a Windows build of FFMPEG [here](https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-full.7z).
    
    Extract the ffmpeg.exe into `install_dir/bin`.
    

#### Environment setup

1. If you are on Windows 7, you cannot run Qt6, so you want 'setup_venv_qt5.bat'.
2. If you are on Windows 8 or newer, go for 'setup_venv.bat'.

Just double-click the batch file, and it will take you through the setup. It should take a minute to download and a couple minutes to install. If it seems like it hung, just give it time to finish. It'll say 'Done!' when it is done.

If something messes up, or you want to switch between Qt5/Qt6, just run the batch again and you will have an option to reinstall everything. Everything these scripts do ends up in the 'venv' directory, so you can also just delete that folder to 'uninstall'. It should just 'work' on most normal computers, but let me know if you have any trouble.

Then run 'setup_help.bat' to build the help. This isn't necessary, but it is nice to have it built locally. You can run this again at any time to rebuild the current help.

#### Running it

Then run 'client.bat' to start the client. The first start will take a little longer. It will operate just like a normal build, putting your database in the 'db' directory.

If you want to redirect your database or use any other launch arguments, then copy 'client.bat' to 'client-user.bat' and edit it, inserting your desired db path. Run this instead of 'client.bat'. New `git pull` commands will not affect 'client-user.bat'.

## Simple Windows Updating Guide

To update, you do the same thing as for the extract builds.

1. If you installed by extracting the source zip, then download the [latest release](https://github.com/hydrusnetwork/hydrus/releases/latest) source zip and extract it over the top of the folder you have, overwriting the existing source files.
2. If you installed with git, then just run `git pull` as normal. I added a 'git_pull.bat' file to do it with a couple clicks.

It is worth running 'setup_venv.bat' or 'setup_venv_qt5.bat' again every now and then just to stay up to date with any version changes. It will give you an option to update, which typically only takes a couple of seconds.

## doing it manually { id="what_you_need" }

_This is for advanced users only._

I hope to have similar easy-setup scripts for Linux and macOS soon. For now, if this is you, you will have to do it manually. If you are comfortable, check out the 'setup_venv' scripts to see what is going on under the hood.

Inside the extract should be client.py and server.py. You will be treating these basically the same as the 'client' and 'server' executables--you should be able to launch them the same way and they take the same launch parameters as the exes.

Hydrus needs a whole bunch of libraries, so let's now set your python up. I strongly recommend you create a virtual environment.

_Note, if you are on Linux and you have trouble with venv, it may be easier to use your package manager instead. A user has written a great summary with all needed packages [here](running_from_source_linux_packages.txt)._

To create a new venv environment:

*   (navigate to your hydrus extract folder in a terminal)
*   ```pip3 install virtualenv``` (if you need it)
*   `pip3 install wheel` (if you need it)
*   `python3 -m venv venv`
*   `. venv/bin/activate`

That `. venv/bin/activate` line turns on your venv, which is an isolated copy of python that you can install modules to without worrying about breaking something system-wide, and will be needed every time you run the `client.py`/`server.py` files. You should see your terminal note you are now in the venv. You can easily tuck this venv activation line into a launch script.

On Windows Powershell, the command is `.\venv\Scripts\activate`, but you may find the whole deal is done much easier in cmd than Powershell. When in Powershell, just type `cmd` to get an old fashioned command line. In cmd, the launch command is just `venv\scripts\activate.bat`, no leading period.

After you have activated the venv, you can use pip to install everything you need to it from the appropriate requirements.txt in the base install directory. If you are on an older OS that cannot run Qt6, use the 'qt5' version. Otherwise:

```
pip install -r requirements.txt
```

If you prefer to do things manually, inspect the document and install the modules yourself.

There are some '_build' variants of the requirements.txts. You can ignore these unless you intend to make your own frozen build like the official releases.

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

If you run Windows 7, you cannot run Qt6. Please try PySide2 or PyQt5.

## FFMPEG { id="ffmpeg" }

If you don't have FFMPEG in your PATH and you want to import anything more fun than jpegs, you will need to put a static [FFMPEG](https://ffmpeg.org/) executable in your PATH or the `install_dir/bin` directory. [This](https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-full.7z) should always point to a new build.

Alternately, you can just copy the exe from one of my extractable Windows releases.

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

!!! info "Extremely safe no way it can go wrong"
    If you want to update sqlite for your system python install, you can also drop it into `C:\Python38\DLLs` or wherever you have python installed. You'll be overwriting the old file, so make a backup if you want to (I have never had trouble updating like this, however).

## additional windows info { id="additional_windows" }

This does not matter much any more, but in the old days, Windows pip could have problems building modules like lz4 and lxml, and Visual Studio was tricky to get working. [This page](http://www.lfd.uci.edu/~gohlke/pythonlibs/) has a lot of prebuilt binaries--I have found it very helpful many times.

I have a fair bit of experience with Windows python, so send me a mail if you need help.

## running it { id="running_it" }

Once you have everything set up, client.py and server.py should look for and run off client.db and server.db just like the executables. They will look in the 'db' directory by default, or anywhere you point them with the "-d" parameter, again just like the executables. Explictly, you will be entering something like this in the terminal:

```
. venv/bin/activate
python client.py -d="/path/to/database"
```

Again, you may want to set up a shortcut to a script to make it easy.

I develop hydrus on and am most experienced with Windows, so the program is more stable and reasonable on that. I do not have as much experience with Linux or macOS, but I still appreciate and will work on your Linux/macOS bug reports.

## Building the docs

When running from source you will also need to [build the hydrus help docs](about_docs.md) yourself.

## my code { id="my_code" }

My coding style is unusual and unprofessional. Everything is pretty much hacked together. If you are interested in how things work, please do look through the source and ask me if you don't understand something.

I'm constantly throwing new code together and then cleaning and overhauling it down the line. I work strictly alone, however, so while I am very interested in detailed bug reports or suggestions for good libraries to use, I am not looking for pull requests or suggestions on style. I know a lot of things are a mess. Everything I do is [WTFPL](https://github.com/sirkris/WTFPL/blob/master/WTFPL.md), so feel free to fork and play around with things on your end as much as you like.
