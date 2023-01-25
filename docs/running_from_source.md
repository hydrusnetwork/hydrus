---
title: Running From Source  
---

# running from source

I write the client and server entirely in [python](https://python.org), which can run straight from source. It is getting simpler and simpler to run python programs like this, so don't be afraid of it. If none of the built packages work for you (for instance if you use Windows 8.1 or 18.04 Ubuntu (or equivalent)), it may be the only way you can get the program to run. Also, if you have a general interest in exploring the code or wish to otherwise modify the program, you will obviously need to do this.

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

=== "Windows"

    First of all, you will need to install Python. Get 3.8.x or 3.9.x [here](https://www.python.org/downloads/windows/). During the install process, make sure it has something like 'Add Python to PATH' checked. This makes Python available to your Windows.  
    
    If you are on 3.10.x, that's ok--run the 'advanced' setup later on and choose the newer OpenCV.

=== "Linux"

    You should already have a fairly new python. Ideally, you want 3.8.x or 3.9.x. If you are on 3.10.x, run the 'advanced' setup later on and choose the newer OpenCV.

=== "macOS"

    You should already have python of about the correct version.

Then, get the hydrus source. The github repo is [https://github.com/hydrusnetwork/hydrus](https://github.com/hydrusnetwork/hydrus). If you are familiar with git, you can just clone the repo to the location you want with `git clone https://github.com/hydrusnetwork/hydrus`, but if not, then just go to the [latest release](https://github.com/hydrusnetwork/hydrus/releases/latest) and download and extract the source code .zip somewhere. Make sure the directory has write permissions (e.g. don't put it in "Program Files"). Extracting straight to a spare drive, something like "D:\Hydrus Network", is ideal.

We will call the base extract directory, the one with 'client.py' in it, `install_dir`.

!!! info "Mixed Builds"
    Don't mix and match build extracts and source extracts. The process that runs the code gets confused if there are unexpected extra .dlls in the directory. **If you need to convert between built and source releases, perform a [clean install](getting_started_installing.md#clean_installs).**  
    
    If you are converting from one install type to another, make a backup before you start. Then, if it all goes wrong, you'll have a safe backup to rollback to.

#### Built Programs

There are three external libraries. You just have to get them and put them in the correct place:

=== "Windows"

    1. mpv  
        
        1. If you are on Windows 8.1 or older, get [this](https://sourceforge.net/projects/mpv-player-windows/files/libmpv/mpv-dev-x86_64-20210228-git-d1be8bb.7z).
        2. If you are on Windows 10 or newer, get [this](https://sourceforge.net/projects/mpv-player-windows/files/libmpv/mpv-dev-x86_64-20220501-git-9ffaa6b.7z).
        
        Then open that archive and place the 'mpv-1.dll' or 'mpv-2.dll' into `install_dir`.
        
    2. SQLite3  
        
        Go to `install_dir/static/build_files/windows` and copy 'sqlite3.dll' into `install_dir`.
        
    3. FFMPEG  
        
        Get a Windows build of FFMPEG [here](https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-full.7z).
        
        Extract the ffmpeg.exe into `install_dir/bin`.
        

=== "Linux"

    1. mpv  
        
        Try running `apt-get install libmpv1` in a new terminal. You can type `apt show libmpv1` to see your current version. Or, if you use a different package manager, try searching `libmpv` or `libmpv1` on that.
        
        1. If you have earlier than 0.34.1, you will be looking at running the 'advanced' setup in the next section and selecting the 'old' mpv.
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

    
    Double-click `setup_venv.bat`.
    

=== "Linux"

    
    The file is `setup_venv.sh`. You may be able to double-click it. If not, open a terminal in the folder and type:  
    
    `./setup_venv.sh`
    
    If you do not have permission to execute the file, do this before trying again:  
    
    `chmod +x setup_venv.sh`
    
    You will likely have to do the same on the other .sh files.
    
    If you get an error about the venv failing to activate during `setup_venv.sh`, you may need to install venv especially for your system. The specific error message should help you out, but you'll be looking at something along the lines of `apt install python3.10-venv`. 
    
    If you like, you can run the `setup_desktop.sh` file to install a hydrus.desktop file to your applications folder. (Or check the template in `install_dir/static/hydrus.desktop` and do it yourself!)
    

=== "macOS"

    
    Double-click `setup_venv.command`.
    
    If you do not have permission to run the .command file, then open a terminal on the folder and enter:
    
    `chmod +x setup_venv.command`
    
    You will likely have to do the same on the other .command files.
    
    I do not know which versions of macOS are unable to run Qt6, so you may need to experiment with the advanced options. Try Qt5 and the other older libraries first, then test the newer ones later.
    
    Let me know what you discover.
    

The setup will ask you some questions. Just type the letters it asks for and hit enter. Most users are looking at the (s)imple setup, but if your situation is unusual, you may need the (a)dvanced. Once ready, it should take a minute to download its packages and a couple minutes to install them. Do not close it until it is finished installing everything and says 'Done!'. If it seems like it hung, just give it time to finish.

If something messes up, or you want to switch between Qt5/Qt6, or you need to try a different version of a library, just run the setup script again and it will reinstall everything. Everything these scripts do ends up in the 'venv' directory, so you can also just delete that folder to 'uninstall'. It should _just work_ on most normal computers, but let me know if you have any trouble.

Then run the 'setup_help' script to build the help. This isn't necessary, but it is nice to have it built locally. You can run this again at any time to rebuild the current help.

#### Running it

=== "Windows"

    Run 'client.bat' to start the client.

=== "Linux"

    Run 'client.sh' to start the client. Don't forget to set `chmod +x client.sh` if you need it.

=== "macOS"

    Run 'client.command' to start the client. Don't forget to set `chmod +x client.command` if you need it.

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

### Simple Updating Guide

To update, you do the same thing as for the extract builds.

1. If you installed by extracting the source zip, then download the [latest release](https://github.com/hydrusnetwork/hydrus/releases/latest) source zip and extract it over the top of the folder you have, overwriting the existing source files.
2. If you installed with git, then just run `git pull` as normal.

If you get a library version error when you try to boot, run the venv setup again. It is worth doing this anyway, every now and then, just to stay up to date.

### Migrating from an Existing Install

Many users start out using one of the official built releases and decide to move to source. There is lots of information [here](database_migration.md) about how to migrate the database, but for your purposes, the simple method is this:

**If you never moved your database to another place and do not use -d/--db_dir launch parameter**

1. Follow the above guide to get the source install working in a new folder on a fresh database
2. **MAKE A BACKUP OF EVERYTHING**
3. Delete everything from the source install's `db` directory.
4. Move your built release's entire `db` directory to the source.
5. Run your source release again--it should load your old db no problem!
6. Update your backup routine to point to the new source install location.

**If you moved your database to another location and use the -d/--db_dir launch parameter**

1. Follow the above guide to get the source install working in a new folder on a fresh database (without -db_dir)
2. **MAKE A BACKUP OF EVERYTHING**
3. Just to be neat, delete the .db files, .log files, and client_files folder from the source install's `db` directory.
4. Run the source install with --db_dir just as you would the built executable--it should load your old db no problem!

## Doing it Yourself { id="what_you_need" }

_This is for advanced users only._

_If you have never used python before, do not try this. If the easy setup scripts failed for you and you don't know what happened, please contact hydev before trying this, as the thing that went wrong there will probably go much more wrong here._

You can also set up the environment yourself. Inside the extract should be client.py and server.py. You will be treating these basically the same as the 'client' and 'server' executables--with the right environment, you should be able to launch them the same way and they take the same launch parameters as the exes.

Hydrus needs a whole bunch of libraries, so let's now set your python up. I **strongly** recommend you create a virtual environment. It is easy and doesn't mess up your system python.

**You have to do this in the correct order! Do not switch things up. If you make a mistake, delete your venv folder and start over from the beginning.**

To create a new venv environment:

* Open a terminal at your hydrus extract folder. If `python3` doesn't work, use `python`.
* `python3 -m pip install virtualenv` (if you need it)
* `python3 -m venv venv`
* `source venv/bin/activate` (`CALL venv\Scripts\activate.bat` in Windows cmd)
* `python -m pip install --upgrade pip`
* `python -m pip install --upgrade wheel`

!!! info "venvs"
    That `source venv/bin/activate` line turns on your venv. You should see your terminal prompt note you are now in it. A venv is an isolated environment of python that you can install modules to without worrying about breaking something system-wide. **Ideally, you do not want to install python modules to your system python.**  
    
    This activate line will be needed every time you alter your venv or run the `client.py`/`server.py` files. You can easily tuck this into a launch script--check the easy setup files for examples.  
    
    On Windows Powershell, the command is `.\venv\Scripts\activate`, but you may find the whole deal is done much easier in cmd than Powershell. When in Powershell, just type `cmd` to get an old fashioned command line. In cmd, the launch command is just `venv\scripts\activate.bat`, no leading period.

**After you have activated the venv**, you can use pip to install everything you need to it from the requirements.txt in the install_dir:

```
python -m pip install -r requirements.txt
```

If you need different versions of libraries, check the cut-up requirements.txts the 'advanced' easy-setup uses in `install_dir/static/requirements/advanced`. Check and compare their contents to the main requirements.txt to see what is going on. You'll likely need the newer OpenCV on Python 3.10, for instance.

### Qt { id="qt" }

Qt is the UI library. You can run PySide2, PySide6, PyQt5, or PyQt6. A wrapper library called `qtpy` allows this. The default is PySide6, but if it is missing, qtpy will fall back to an available alternative. For PyQt5 or PyQt6, you need an extra Chart module, so go:

```
python -m pip install qtpy PyQtChart PyQt5
-or-
python -m pip install qtpy PyQt6-Charts PyQt6
```

If you have multiple Qts installed, then select which one you want to use by setting the `QT_API` environment variable to 'pyside2', 'pyside6', 'pyqt5', or 'pyqt6'. Check _help->about_ to make sure it loaded the right one.

If you want to set QT_API in a batch file, do this:

`set QT_API=pyqt6`

If you run <= Windows 8.1 or Ubuntu 18.04, you cannot run Qt6. Try PySide2 or PyQt5.

### mpv { id="mpv" }

MPV is optional and complicated, but it is great, so it is worth the time to figure out!

As well as the python wrapper, 'python-mpv' (which is in the requirements.txt), you also need the underlying dev library. This is _not_ mpv the program, but 'libmpv', often called 'libmpv1'.

For Windows, the dll builds are [here](https://sourceforge.net/projects/mpv-player-windows/files/libmpv/), although getting a stable version can be difficult. Just put it in your hydrus base install directory. Check the links in the easy-setup guide above for good versions. You can also just grab the 'mpv-1.dll'/'mpv-2.dll' I bundle in my extractable Windows release.

If you are on Linux, you can usually get 'libmpv1' like so:

`apt-get install libmpv1`

On macOS, you should be able to get it with `brew install mpv`, but you are likely to find mpv crashes the program when it tries to load. Hydev is working on this, but it will probably need a completely different render API.

Hit _help->about_ to see your mpv status. If you don't have it, it will present an error popup box with more info.

### SQLite { id="sqlite" }

If you can, update python's SQLite--it'll improve performance. The SQLite that comes with stock python is usually quite old, so you'll get a significant boost in speed. In some python deployments, the built-in SQLite not compiled with neat features like Fast Text Search (FTS) that hydrus needs.

On Windows, get the 64-bit sqlite3.dll [here](https://www.sqlite.org/download.html), and just drop it in your base install directory. You can also just grab the 'sqlite3.dll' I bundle in my extractable Windows release.

You _may_ be able to update your SQLite on Linux or macOS with:

* `apt-get install libsqlite3-dev`
* (activate your venv)
* `python -m pip install pysqlite3`

But as long as the program launches, it usually isn't a big deal.

!!! warning "Extremely safe no way it can go wrong"
    If you want to update sqlite for your system python install, you can also drop it into `C:\Python38\DLLs` or wherever you have python installed. You'll be overwriting the old file, so make a backup if you want to (I have never had trouble updating like this, however).
    
    A user who made a Windows venv with Anaconda reported they had to replace the sqlite3.dll in their conda env at `~/.conda/envs/<envname>/Library/bin/sqlite3.dll`.

### FFMPEG { id="ffmpeg" }

If you don't have FFMPEG in your PATH and you want to import anything more fun than jpegs, you will need to put a static [FFMPEG](https://ffmpeg.org/) executable in your PATH or the `install_dir/bin` directory. [This](https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-full.7z) should always point to a new build for Windows. Alternately, you can just copy the exe from one of my extractable Windows releases.

### Running It { id="running_it" }

Once you have everything set up, client.py and server.py should look for and run off client.db and server.db just like the executables. You can use the 'client.bat/sh/command' scripts in the install dir or use them as inspiration for your own. In any case, you are looking at entering something like this into the terminal:

```
source venv/bin/activate
python client.py
```

This will use the 'db' directory for your database by default, but you can use the [launch arguments](launch_arguments.md) just like for the executables. For example, this could be your client-user.sh file:

```
#!/bin/bash

source venv/bin/activate
python client.py -d="/path/to/database"
```

### Building these Docs

When running from source you may want to [build the hydrus help docs](about_docs.md) yourself. You can also check the `setup_help` scripts in the install directory. 

### Building Packages on Windows { id="windows_build" }

Almost everything you get through pip is provided as pre-compiled 'wheels' these days, but if you get an error about Visual Studio C++ when you try to pip something, you have two choices:

- Get Visual Studio 14/whatever build tools
- Pick a different library version

Option B is always the simpler. If opencv-headless as the requirements.txt specifies won't compile in Python 3.10, then try a newer version--there will probably be one of these new highly compatible wheels and it'll just work in seconds. Check my build scripts and various requirements.txts for ideas on what versions to try for your python etc...

If you are confident you need Visual Studio tools, then prepare for headaches. Although the tools are free from Microsoft, it can be a pain to get them through the official (and often huge) downloader installer from Microsoft. Expect a 5GB+ install with an eye-watering number of checkboxes that probably needs some stackexchange searches to figure out.

On Windows 10, [Chocolatey](https://chocolatey.org/) has been the easy answer. Get it installed and and use this one simple line:

```
choco install -y vcbuildtools visualstudio2017buildtools windows-sdk-10.0
```

Trust me, just do this, it will save a ton of headaches!

_Update:_ On Windows 11, in 2023-01, I had trouble with the above. There's a couple '11' SDKs that installed ok, but the vcbuildtools stuff had unusual errors. I hadn't done this in years, so maybe they are broken for Windows 10 too! The good news is that a basic stock Win 11 install with Python 3.10 is fine getting everything on our requirements and even making a build without any extra compiler tech. 

### Additional Windows Info { id="additional_windows" }

This does not matter much any more, but in the old days, building modules like lz4 and lxml was a complete nightmare, and hooking up Visual Studio was even more difficult. [This page](http://www.lfd.uci.edu/~gohlke/pythonlibs/) has a lot of prebuilt binaries--I have found it very helpful many times.

I have a fair bit of experience with Windows python, so send me a mail if you need help.

## My Code { id="my_code" }

I develop hydrus on and am most experienced with Windows, so the program is more stable and reasonable on that. I do not have as much experience with Linux or macOS, but I still appreciate and will work on your Linux/macOS bug reports.

My coding style is unusual and unprofessional. Everything is pretty much hacked together. If you are interested in how things work, please do look through the source and ask me if you don't understand something.

I'm constantly throwing new code together and then cleaning and overhauling it down the line. I work strictly alone. While I am very interested in detailed bug reports or suggestions for good libraries to use, I am not looking for pull requests or suggestions on style. I know a lot of things are a mess. Everything I do is [WTFPL](https://github.com/sirkris/WTFPL/blob/master/WTFPL.md), so feel free to fork and play around with things on your end as much as you like.
