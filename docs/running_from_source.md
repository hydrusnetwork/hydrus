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

    ??? info "Git for Windows"
        Git is an excellent tool for synchronising code across platforms. Instead of downloading and extracting the whole .zip every time you want to update, it allows you to just run one line and all the code updates are applied in about three seconds. You can also run special versions of the program, or test out changes I committed two minutes ago without having to wait for me to make a whole build. You don't have to, but I recommend you get it.
        
        Installing it is simple, but it can be intimidating. These are a bunch of very clever tools coming over from Linux-land, and the installer has a 10+ page wizard with several technical questions. Luckily, the 'default' is broadly fine, but I'll write everything out so you can follow along. I can't promise this list will stay perfectly up to date, so let me know if there is something complex and new you don't understand. <span class="spoiler">This is also a record that I can refer to when I set up a new machine.</span>
        
        - First off, get it [here](https://gitforwindows.org/). Run the installer.
        - On the first page, with checkboxes, I recommend you uncheck 'Windows Explorer Integration', with its 'Open Git xxx here' sub-checkboxes. This stuff will just be annoying for our purposes.
        - Then set your text editor. Select the one you use, and if you don't recognise anything, set 'notepad'.
        - Now we enter the meat of the wizard pages. Everything except the default console window is best left as default:
            - `Let Git decide` on using "master" as the default main branch name
            - `Git from the command line and also from 3rd-party software`
            - `Use bundled OpenSSH`
            - `Use the OpenSSL library`
            - `Checkout Windows-style, commit Unix-style line endings`
            - **(NOT DEFAULT)** `Use Windows' default console window`. Let's keep things simple, but it isn't a big deal.
            - `Fast-forward or merge`
            - `Git Credential Manager`
            - Do `Enable file system caching`/Do not `Enable symbolic links`
            - Do not enable experimental stuff
        
        Git should now be installed on your system. Any new terminal window (shift+right-click on any folder and hit 'Open in terminal') now has the `git` command!
        
    
    First of all, you will need to install Python. Get 3.10 or 3.11 [here](https://www.python.org/downloads/windows/). During the install process, make sure it has something like 'Add Python to PATH' checked. This makes Python available everywhere in Windows.  
    

=== "Linux"

    You should already have a fairly new python. Ideally, you want at least 3.9.

=== "macOS"

    You should already have python of about the correct version.

If you are already on a very new python, like 3.12+, that's ok--you might need to select the 'advanced' setup later on and choose the '(t)est' options. If you are stuck on a much older version of python, try the same thing, but with the '(o)lder' options (but I can't promise it will work!).

Then, get the hydrus source. It is best to get it with Git: make a new folder somewhere, open a terminal in it, and then enter:

    git clone https://github.com/hydrusnetwork/hydrus

The whole repository will be copied to that location. If Git is not available, then just go to the [latest release](https://github.com/hydrusnetwork/hydrus/releases/latest) and download and extract the source code .zip somewhere.

!!! warning "Read-only install locations"
    Make sure the install directory has convenient write permissions (e.g. on Windows, don't put it in "Program Files"). Extracting straight to a spare drive, something like "D:\Hydrus Network", is ideal.

We will call the base extract directory, the one with 'hydrus_client.py' in it, `install_dir`.

!!! info "Mixed Builds"
    Don't mix and match build extracts and source extracts. The process that runs the code gets confused if there are unexpected extra .dlls in the directory. **If you need to convert between built and source releases, perform a [clean install](getting_started_installing.md#clean_installs).**  
    
    If you are converting from one install type to another, make a backup before you start. Then, if it all goes wrong, you'll always have a safe backup to rollback to.

#### Built Programs

There are three special external libraries. You just have to get them and put them in the correct place:

=== "Windows"

    1. mpv  
        
        1. If you are on Windows 8.1 or older, [this](https://sourceforge.net/projects/mpv-player-windows/files/libmpv/mpv-dev-x86_64-20210228-git-d1be8bb.7z) is known safe.
        2. If you are on Windows 10 or newer and want the simple answer, try [this](https://sourceforge.net/projects/mpv-player-windows/files/libmpv/mpv-dev-x86_64-20220501-git-9ffaa6b.7z).
        3. Ideally, go for [this](https://sourceforge.net/projects/mpv-player-windows/files/libmpv/mpv-dev-x86_64-20230212-git-a40958c.7z), but you have to rename `libmpv-2.dll` to `mpv-2.dll`.
        4. I have been testing [this newer version](https://sourceforge.net/projects/mpv-player-windows/files/libmpv/mpv-dev-x86_64-20230820-git-19384e0.7z) and [this very new version](https://sourceforge.net/projects/mpv-player-windows/files/libmpv/mpv-dev-x86_64-20231231-git-abc2a74.7z) and things seem to be fine too, at least on updated Windows. If you use the '(t)est' python-mpv, 1.0.5, you do not have to rename `libmpv-2.dll` to `mpv-2.dll`.
        
        Then open that archive and place the 'mpv-1.dll' or 'mpv-2.dll' into `install_dir`.
        
        ??? info "mpv on older Windows"
            I have word that that newer mpv, the API version 2.1 that you have to rename to mpv-2.dll, will work on Qt5 and Windows 7. If this applies to you, have a play around with different versions here. You'll need the newer mpv choice in the setup-venv script however, which, depending on your situation, may not be possible.
        
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
        
    ??? "Qt compatibility note"
        
        If you run into trouble running newer versions of Qt6, which you will be setting up later, some users have fixed it by installing the packages `libicu-dev` and `libxcb-cursor-dev`. With `apt` that will be:
        
        * `sudo apt-get install libicu-dev`
        * `sudo apt-get install libxcb-cursor-dev`
        

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
    
    You may need to experiment with the advanced choices, especially if your macOS is a litle old.
    

The setup will ask you some questions. Just type the letters it asks for and hit enter. Most users are looking at the (s)imple setup, but if your situation is unusual, try the (a)dvanced, which will walk you through the main decisions. Once ready, it should take a minute to download its packages and a couple minutes to install them. Do not close it until it is finished installing everything and says 'Done!'. If it seems like it hung, just give it time to finish.

If something messes up, or you want to make a different decision, just run the setup script again and it will reinstall everything. Everything these scripts do ends up in the 'venv' directory, so you can also just delete that folder to 'uninstall' the venv. It should _just work_ on most normal computers, but let me know if you have any trouble.

Then run the 'setup_help' script to build the help. This isn't necessary, but it is nice to have it built locally. You can run this again at any time to rebuild the current help.

#### Running it

=== "Windows"

    Run 'hydrus_client.bat' to start the client.

=== "Linux"

    Run 'hydrus_client.sh' to start the client. Don't forget to set `chmod +x hydrus_client.sh` if you need it.

=== "macOS"

    Run 'hydrus_client.command' to start the client. Don't forget to set `chmod +x hydrus_client.command` if you need it.

The first start will take a little longer (it has to compile all the code into something your computer understands). Once up, it will operate just like a normal build with the same folder structure and so on.

!!! warning "Missing a Library"
    If the client fails to boot, it should place a 'hydrus_crash.log' in your 'db' directory or your desktop, or, if it got far enough, it may write the error straight to the 'client - date.log' file in your db directory.  

    If that error talks about a missing library, try reinstalling your venv. Are you sure it finished correctly? Do you need to run the advanced setup and select a different version of Qt?

=== "Windows"

    If you want to redirect your database or use any other launch arguments, then copy 'hydrus_client.bat' to 'hydrus_client-user.bat' and edit it, inserting your desired db path. Run this instead of 'hydrus_client.bat'. New `git pull` commands will not affect 'hydrus_client-user.bat'.
    
    You probably can't pin your .bat file to your Taskbar or Start (and if you try and pin the running program to your taskbar, its icon may revert to Python), but you can make a shortcut to the .bat file, pin that to Start, and in its properties set a custom icon. There's a nice hydrus one in `install_dir/static`.
    
    However, some versions of Windows won't let you pin a shortcut to a bat to the start menu. In this case, make a shortcut like this:
    
    `C:\Windows\System32\cmd.exe /c "C:\hydrus\Hydrus Source\hydrus_client-user.bat"`
    
    This is a shortcut to tell the terminal to run the bat; it should be pinnable to start. You can give it a nice name and the hydrus icon and you should be good!

=== "Linux"

    If you want to redirect your database or use any other launch arguments, then copy 'hydrus_client.sh' to 'hydrus_client-user.sh' and edit it, inserting your desired db path. Run this instead of 'hydrus_client.sh'. New `git pull` commands will not affect 'hydrus_client-user.sh'.

=== "macOS"

    If you want to redirect your database or use any other launch arguments, then copy 'hydrus_client.command' to 'hydrus_client-user.command' and edit it, inserting your desired db path. Run this instead of 'hydrus_client.command'. New `git pull` commands will not affect 'hydrus_client-user.command'.

### Simple Updating Guide

To update, you do the same thing as for the extract builds.

1. If you installed by extracting the source zip, then download the [latest release](https://github.com/hydrusnetwork/hydrus/releases/latest) source zip and extract it over the top of the folder you have, overwriting the existing source files.
2. If you installed with git, then just run `git pull` as normal. I have added easy 'git_pull' scripts to the install directory for your convenience (on Windows, just double-click 'git_pull.bat').

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

You can also set up the environment yourself. Inside the extract should be hydrus_client.py and hydrus_server.py. You will be treating these basically the same as the 'client' and 'server' executables--with the right environment, you should be able to launch them the same way and they take the same launch parameters as the exes.

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
    
    This activate line will be needed every time you alter your venv or run the `hydrus_client.py`/`hydrus_server.py` files. You can easily tuck this into a launch script--check the easy setup files for examples.  
    
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

??? "Qt compatibility notes"
    
    If you run into trouble running newer versions of Qt6 on Linux, some users have fixed it by installing the packages `libicu-dev` and `libxcb-cursor-dev`. With `apt` that will be:
    
    * `sudo apt-get install libicu-dev`
    * `sudo apt-get install libxcb-cursor-dev`
    
    If you still have trouble with the default Qt6 version, or you rebuilt your venv and the newer version of Qt6 gives you problems, check out the setup_venv script language and the advanced requirements.txts files it relies on in `install_dir/static/requirements/advanced`. There should be several older version examples you can try out.
    
    To install a specific version of a library with pip, activate your venv and then type something like `pip install PySide6==6.3.1`.
    

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
    If you want to update SQLite for your Windows system python install, you can also drop it into `C:\Program Files\Python310\DLLs` or wherever you have python installed, and it'll update for all your python projects. You'll be overwriting the old file, so make a backup of the old one (I have never had trouble updating like this, however).
    
    A user who made a Windows venv with Anaconda reported they had to replace the sqlite3.dll in their conda env at `~/.conda/envs/<envname>/Library/bin/sqlite3.dll`.

### FFMPEG { id="ffmpeg" }

If you don't have FFMPEG in your PATH and you want to import anything more fun than jpegs, you will need to put a static [FFMPEG](https://ffmpeg.org/) executable in your PATH or the `install_dir/bin` directory. [This](https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-full.7z) should always point to a new build for Windows. Alternately, you can just copy the exe from one of my extractable Windows releases.

### Running It { id="running_it" }

Once you have everything set up, hydrus_client.py and hydrus_server.py should look for and run off client.db and server.db just like the executables. You can use the 'hydrus_client.bat/sh/command' scripts in the install dir or use them as inspiration for your own. In any case, you are looking at entering something like this into the terminal:

```
source venv/bin/activate
python hydrus_client.py
```

This will use the 'db' directory for your database by default, but you can use the [launch arguments](launch_arguments.md) just like for the executables. For example, this could be your client-user.sh file:

```
#!/bin/bash

source venv/bin/activate
python hydrus_client.py -d="/path/to/database"
```

### Building these Docs

When running from source you may want to [build the hydrus help docs](about_docs.md) yourself. You can also check the `setup_help` scripts in the install directory. 

### Building Packages on Windows { id="windows_build" }

Almost everything you get through pip is provided as pre-compiled 'wheels' these days, but if you get an error about Visual Studio C++ when you try to pip something, you have two choices:

- Get Visual Studio 14/whatever build tools
- Pick a different library version

Option B is always simpler. If opencv-headless as the requirements.txt specifies won't compile in your python, then try a newer version--there will probably be one of these new highly compatible wheels and it'll just work in seconds. Check my build scripts and various requirements.txts for ideas on what versions to try for your python etc...

If you are confident you need Visual Studio tools, then prepare for headaches. Although the tools are free from Microsoft, it can be a pain to get them through the official (and often huge) downloader installer from Microsoft. Expect a 5GB+ install with an eye-watering number of checkboxes that probably needs some stackexchange searches to figure out.

On Windows 10, [Chocolatey](https://chocolatey.org/) has been the easy answer. These can be useful:

```
choco install -y vcredist-all
choco install -y vcbuildtools (this is Visual Studio 2015)
choco install -y visualstudio2017buildtools
choco install -y visualstudio2022buildtools
choco install -y windows-sdk-10.0
```

_Update:_ On Windows 11, I have had some trouble with the above. The VS2015 seems not to install any more. A basic stock Win 11 install with Python 3.10 or 3.11 is fine getting everything on our requirements, but freezing with PyInstaller may have trouble finding certain 'api-***.dll' files. I am now trying to figure this out with my latest dev machine as of 2024-01. If you try this, let me know what you find out! 

### Additional Windows Info { id="additional_windows" }

This does not matter much any more, but in the old days, building modules like lz4 and lxml was a complete nightmare, and hooking up Visual Studio was even more difficult. [This page](http://www.lfd.uci.edu/~gohlke/pythonlibs/) has a lot of prebuilt binaries--I have found it very helpful many times.

I have a fair bit of experience with Windows python, so send me a mail if you need help.

## My Code { id="my_code" }

I develop hydrus on and am most experienced with Windows, so the program is more stable and reasonable on that. I do not have as much experience with Linux or macOS, but I still appreciate and will work on your Linux/macOS bug reports.

My coding style is unusual and unprofessional. Everything is pretty much hacked together. If you are interested in how things work, please do look through the source and ask me if you don't understand something.

I'm constantly throwing new code together and then cleaning and overhauling it down the line. I work strictly alone. While I am very interested in detailed bug reports or suggestions for good libraries to use, I am not looking for pull requests or suggestions on style. I know a lot of things are a mess. Everything I do is [WTFPL](https://github.com/sirkris/WTFPL/blob/master/WTFPL.md), so feel free to fork and play around with things on your end as much as you like.
