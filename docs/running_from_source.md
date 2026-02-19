---
title: Running From Source  
---

# running from source

I write the client and server entirely in [python](https://python.org), which can run straight from source. It is getting simpler and simpler to run python programs like this, so don't be afraid of it. The program generally works better (better UI compatibility and mpv support) from source than from a built release. If none of the builds work for you (for instance if you use Windows 8.1 or 18.04 Ubuntu or a newer but more distant flavour of Linux, and since 2025-09 any macOS situation), it may be the only way you can get the program to run. Also, if you want to explore or modify the code, you will obviously need to do this.

I generally recommend running from source if you can, especially on Linux.

## Simple Setup Guide

There are now setup scripts that make this easy. You do not need any python experience.

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

    **First of all, you will need git.** If you are just a normal Windows user, you will not have it. Get it:
    
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
        
        Git should now be installed on your system. Any _new_ terminal/command line/powershell window (right-click on any folder and hit something like 'Open in terminal') now has the `git` command!
        
    
    ??? warning "Windows 7"
        For a long time, I supported Windows 7 via running from source. Unfortunately, as libraries and code inevitably updated, this finally seems to no longer be feasible. Python 3.8 will no longer run the program. I understand v582 is one of the last versions of the program to work.
        
        First, you will have to install the older [Python 3.8](https://www.python.org/downloads/release/python-3810/), since that is the latest version that you can run.
        
        Then, later, when you do the `git clone https://github.com/hydrusnetwork/hydrus` line, you will need to run `git checkout tags/v578`, which will rewind you to that point in time.
        
        I can't promise anything though. You may like to think about moving to Linux.
        
    
    If you do not know if you have Python, you probably do not. Let's check--right-click on any folder and select 'open in terminal' and copy/paste the following:
    
    `python --version`
    
    If you get some nice python version information, you have python. Hydrus should be fine with Python 3.10-3.13. If you are on 3.14+, that may be ok, but select the 'advanced' setup later on and choose the '(t)est' options. If you are stuck on something older, try the same thing, but with the '(o)lder' options (but I can't promise it will work!).
    
    If you don't have python, we need to get it. Try 3.12 [here](https://www.python.org/downloads/windows/). During the install process, make sure it has something like 'Add Python to PATH' checked. This makes Python available everywhere in Windows.  
    
    Once it is installed, then, _after installation is totally complete_, open up a new terminal (It needs to be a new terminal to catch your now-updated PATH) and copy/paste the following:
    
    `python --version`  
    `python -m pip --version`  
    `python -m venv --help`
    
    If all these produce good output (no errors), you are good to go!

=== "Linux"

    You probably have git, but let's check by opening a new terminal and going:
    
    `git --version`
    
    If you do not get a nice answer, you will want to install it. If you are on Debian/Ubuntu/Mint, you'll most likely be using `apt`, like this:
    
    `sudo apt install git`
    
    If you are in the Arch family, you may be on `pacman`. In this case, where I might say in this help to do `sudo apt install package`, you are probably looking at `sudo pacman -S package`, so:
    
    `sudo pacman -S git`
    
    You should already have a fairly new python. Hydrus is fine with Python 3.10-3.13. If you are on 3.14+, that may be ok, but select the 'advanced' setup later on and choose the '(t)est' options. If you are stuck on something older, try the same thing, but with the '(o)lder' options (but I can't promise it will work!). You can find out what version you have just by opening a new terminal and typing `python3` or `python`.
    
    You are going to need `pip` and `venv`. These are often bundled with a python install, but not always with a system python. Open a terminal and try these two lines:
    
    `python3 -m pip --version`  
    `python3 -m venv --help`
    
    If it complains about either, you will need to install them. Try this:
    
    `sudo apt install python3-pip`  
    `sudo apt install python3-venv`

=== "macOS"

    _If you are currently on the old App and need to migrate to a source install, get a test situation running and then scroll down to the [migrating from an existing install](#migrating_from_an_existing_install) section._
    
    You may not have git already, so open a new terminal and check with:
    
    `git --version`
    
    If you do not get a nice version back, you will want to install it, most likely with:
    
    `brew install git`
    
    You should already have a fairly new python. Hydrus should be fine with Python 3.10-3.13. If you are on 3.14+, that may be ok, but select the 'advanced' setup later on and choose the '(t)est' options. If you are stuck on something older, try the same thing, but with the '(o)lder' options (but I can't promise it will work!). You can find out what version you have just by opening a new terminal and typing `python3` or `python`.
    
    You are going to need `pip` and `venv`. These are often bundled with a python install, but not always with a system python. Open a terminal and try these two lines:
    
    `python3 -m pip --version`  
    `python3 -m venv --help`
    
    If it complains about either, you will need to install them. You do not want to fight with your system python, so you should investigate `brew install python` to install a separate python just for your username.

**Then, get the hydrus source.** It is best to get it with Git: make a new folder somewhere, open a terminal in it, and then paste:

    git clone https://github.com/hydrusnetwork/hydrus

The whole repository will be copied to that location--this is now your install dir. You can move it if you like.

If Git is not available, then just go to the [latest release](https://github.com/hydrusnetwork/hydrus/releases/latest) and download and extract the source code .zip somewhere.

!!! warning "Read-only install locations"
    Make sure the install directory has convenient write permissions (e.g. on Windows, don't put it in "Program Files"). Extracting straight to a spare drive, something like "D:\Hydrus Network", is ideal.

We will call the base extract directory, the one with 'hydrus_client.py' in it, `install_dir`.

!!! warning "Mixed Builds"
    Don't mix and match build extracts and source extracts. The process that runs the code gets confused if there are unexpected extra .dlls in the directory. You will want to set up an entirely new install situation and then move your database dir from the old to the new. [More here](#migrating_from_an_existing_install).  
    
    **If you are converting from one install type to another, make a backup before you start.** Then, if it all goes wrong, you'll always have a safe backup to rollback to.

#### Built Programs

There are three special external libraries. You just have to get them and put them in the correct place:

=== "Windows"

    1. mpv  
        
        1. If you are on Windows 8.1 or older, [2021-02-28](https://sourceforge.net/projects/mpv-player-windows/files/libmpv/mpv-dev-x86_64-20210228-git-d1be8bb.7z) is known safe.
        2. If you are on Windows 10 or need the safe answer (e.g. your Windows is under-updated), try [2023-08-20](https://sourceforge.net/projects/mpv-player-windows/files/libmpv/mpv-dev-x86_64-20230820-git-19384e0.7z).
        3. Otherwise, if you are just normal Win 11, use [2024-10-20](https://sourceforge.net/projects/mpv-player-windows/files/libmpv/mpv-dev-x86_64-20241020-git-37159a8.7z).
        
        Then open that archive and place the 'mpv-1.dll'/'mpv-2.dll'/'libmpv-2.dll' into `install_dir`.
        
    2. SQLite3  
        
        _This is optional and might feel scary, so feel free to ignore. It updates your python install to newer, faster database tech. You can always come back and do it later._
        
        Open your python install location and find the DLLs folder. Likely something like `C:\Program Files\Python311\DLLs` or `C:\Python311\DLLs`. There should be a sqlite3.dll there. Rename it to sqlite3.dll.old, and then open `install_dir/static/build_files/windows` and copy that 'sqlite3.dll' into the python `DLLs` folder.
        
        The absolute newest sqlite3.dll is always available [here](https://sqlite.org/download.html). You want the x64 dll.
        
    3. FFMPEG  
        
        If you already have FFMPEG on your PATH, you are good to go.
        
        If not, get a Windows build of FFMPEG [here](https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-full.7z).
        
        If you know how to put it on your PATH, do so. Otherwise, extract the ffmpeg.exe into `install_dir/bin`.
        

=== "Linux"

    1. mpv  
        
        Linux can provide what we need in a couple of different ways. It is important that we get `libmpv`, rather than just the `mpv` player. Some Linux installs of mpv do also bring libmpv, but others do not. If your package manager provides mpv and it says it comes with libmpv, you are probably good just to get that.
        
        Otherwise, try just running `sudo apt install libmpv1` or `sudo apt install libmpv2` in a new terminal. You can also try `apt show libmpv2` to see any current version. Or, if you use a different package manager, try searching `libmpv`, `libmpv1`, `libmpv2`, or again, just `mpv` on that.
        
        1. If you have earlier than 0.34.1, you will be looking at running the 'advanced' setup in the next section and selecting the 'old' mpv.
        2. If you have 0.34.1 or later, you can run the normal setup script.
        
    2. SQLite3  
        
        No action needed.
        
    3. FFMPEG  
        
        You should already have ffmpeg, but we should double-check: just type `ffmpeg` into a new terminal, and it should give a basic version response. If you don't have it, check your package manager.
        

=== "macOS"

    1. mpv  
        
        Unfortunately, mpv is not well supported in macOS yet. You may be able to install `libmpv` in brew, but it seems to freeze the client as soon as it is loaded. If `help->about` seems to suggest mpv loaded ok, I still recommend you set your `options->media playback` settings to 'show with native viewer' and not mpv. There may be macOS mpv support in future.
        
    2. SQLite3  
        
        No action needed.
        
    3. FFMPEG  
        
        You should already have ffmpeg, but we should double-check: just type `ffmpeg` into a new terminal, and it should give a basic version response. If you don't have it, you are probably looking at:
        
        `brew install ffmpeg`
        

#### Environment setup

=== "Windows"

    
    Double-click `setup_venv.py`. You can also run `python setup_venv.py` from the command line.
    

=== "Linux"

    
    _You do not need to run the setup script as sudo, and doing so may cause some things not to work. Just regular you in a normal terminal._
    
    The file is `setup_venv.py`. You may be able to double-click it. If not, open a terminal in the folder and type:  
    
    `./setup_venv.py`
    
    -or, explicitly-
    
    `python setup_venv.py`
    
    If you do not have permission to execute the file, do this before trying again:  
    
    `chmod +x setup_venv.py`
    
    You will likely have to do the same on the other .sh or .py files.
    
    !!! info "Desktop File"
        If you like, you can later run the `setup_desktop.sh` file to install an io.github.hydrusnetwork.hydrus.desktop file to your applications folder. (Or check the template in `install_dir/static/io.github.hydrusnetwork.hydrus.desktop` and do it yourself!)
    

=== "macOS"

    
    _You do not need to run the setup script as sudo, and doing so may cause some things not to work. Just regular you._
    
    The file is `setup_venv.py`. You may be able to double-click it. If not, open a terminal in the folder and type:  
    
    `./setup_venv.py`
    
    -or, explicitly-
    
    `python setup_venv.py`
    
    If you do not have permission to run the .command file, open a terminal on the folder and enter:
    
    If you do not have permission to execute the file, do this before trying again:  
    
    `chmod +x setup_venv.py`
    
    We used to do this via a .command file. If you want to run one of the other .command files, you likely also need this to tell Gatekeeper you are ok running it:
    
    `sudo xattr -rd com.apple.quarantine the_script.command`
    
    You will likely have to do the same on the other .command files.
    

The setup will ask you some questions. Just type the letters it asks for and hit enter. Most users are looking at the (s)imple setup, but if your situation is unusual (e.g. very old/new python), try the (a)dvanced, which will walk you through the main decisions. Once ready, it should take a minute to download its packages and a couple minutes to install them. Do not close it until it is finished installing everything and says 'Done!'. If it seems like it hung, just give it time to finish.

This setup creates a copy of your system python in a folder called 'venv'. Is it completely non-destructive and undoable. If something messes up, or you want to make a different decision, just run the setup script again and it will clear out and reinstall everything. You can also just delete that folder to 'uninstall' the venv.

The setup should _just work_ on most normal computers, but very old or new systems or unusual architectures may run into trouble. Let me know if you have any problems.

Then run the 'setup_help' script to build the help. This isn't necessary, but it is nice to have it built locally. You can run this again at any time to update to the current help.

#### Running it

!!! note "Run the launch script, not the .py"
    Do not run `hydrus_client.py` on its own by, say double-clicking it, because you will get errors about missing libraries (probably `yaml`/`qtpy`). You will be running `hydrus_client.bat/.sh/.command` instead, or setting up a shortcut to the new python exe we just made in the venv dir.
    
    We have just set up a "venv", which is not the same as your system python, and so in order to run `hydrus_client.py`, we need to "activate" the venv first to load all the libraries we just installed with the `setup_venv` script. Feel free to check the contents of the launch scripts--they are very simple--to see how it works.

=== "Windows"

    Run `hydrus_client.bat` to start the client.
    
    Alternately, if you want a very simple shortcut, you can call the venv directly with the python executable we just installed. The setup venv script may have given you an example. It will look something like this:
    
    `C:\Hydrus\venv\Scripts\pythonw.exe C:\Hydrus\hydrus_client.py`

=== "Linux"

    !!! warning "Wayland (and MPV)"
        Unfortunately, hydrus has several bad bugs in Wayland. The mpv window will often not embed properly into the media viewer, menus and windows may position on the wrong screen, and the taskbar icon may not work at all. Newer versions are less buggy, but some of these issues, particularly mpv embedding, seem to be intractable.
        
        User testing suggests that the best solution for now is just to launch the program in X11, and I now encourage this for all Wayland users. Launching with the environment variable `QT_QPA_PLATFORM=xcb` (e.g. by putting `export QT_QPA_PLATFORM=xcb` in a boot script that launches `hydrus_client`) should do it. The 'xcb' should force X11.
        
        It does not work for everyone, though. If it fails, another user says setting `WAYLAND_DISPLAY=` (as in setting it to nothing) or unsetting it entirely with `unset WAYLAND_DISPLAY`, which forces hydrus (and its embedded mpv windows) to use Xwayland, is another solution. You might need to do `sudo apt install xwayland` first.
        
        You should be able to see which window manager hydrus thinks it is running under in `help->about`, on the "Qt" row.
        
        I expect to revisit this question in future versions of Qt and Wayland, and I plan to try a different mpv embedding technique that I know Wayland should support--we'll see if the situation stabilises.
    
    !!! note "Qt compatibility"
        
        If the program fails to run, and from terminal it says something like this:
        
        `qt.qpa.plugin: From 6.5.0, xcb-cursor0 or libxcb-cursor0 is needed to load the Qt xcb platform plugin`
        
        Then Qt6 may need a couple additional packages:
        
        * `libicu-dev`
        * `libxcb-cursor-dev`
        
        With `apt`, that will be:
        
        * `sudo apt install libicu-dev`
        * `sudo apt install libxcb-cursor-dev`
        
        Or check your OS's package manager.
        
        One user reports that Fedora might need `libxkbcommon` too.
        
        If you still have trouble with the default Qt6 version, try running setup_venv again and choose a different version. There are several to choose from, including (w)riting a custom version. If you are having a lot of trouble, this list can be worth exploring: [PySide6](https://pypi.org/project/PySide6/#history)
        
    
    Run `hydrus_client.sh` to start the client. Don't forget to `chmod +x hydrus_client.sh` if you need it.
    
    Alternately, if you want a very simple shortcut, you can call the venv directly with the python executable we just installed. The setup venv script may have given you an example. It will look something like this:
    
    `/path/to/your/Hydrus/venv/bin/python /path/to/your/Hydrus/hydrus_client.py`

=== "macOS"
    
    Run `hydrus_client.command` to start the client. Don't forget to `chmod +x hydrus_client.command` and `sudo xattr -rd com.apple.quarantine hydrus_client.command` if you need it.
    
    Alternately, if you want a very simple shortcut, you can call the venv directly with the python executable we just installed. The setup venv script may have given you an example. It will look something like this:
    
    `/path/to/your/Hydrus/venv/bin/python /path/to/your/Hydrus/hydrus_client.py`
    
The first start will take a little longer (it has to compile all the code into something your computer understands). Once up, it will operate just like a normal build with the same folder structure and so on.

!!! warning "Missing a Library"
    If the client fails to boot, it should place a 'hydrus_crash.log' in your 'db' directory or your desktop, or, if it got far enough, it may write the error straight to the 'client - date.log' file in your db directory.  
    
    If that error talks about a missing library, particularly 'yaml', try reinstalling your venv. Scroll through the output--are you sure it installed everything correctly? Do you need to run the advanced setup and select a different version of Qt?

=== "Windows"

    If you want to redirect your database or use any other launch arguments, then copy 'hydrus_client.bat' to 'hydrus_client-user.bat' and edit it, inserting your desired db path. Run this instead of 'hydrus_client.bat'. New `git pull` commands will not affect 'hydrus_client-user.bat'.
    
    You probably can't pin your .bat file to your Taskbar or Start (and if you try and pin the running program to your taskbar, its icon may revert to Python), but you can make a shortcut to the .bat file, pin that to Start, and in its properties set a custom icon. There's a nice hydrus one in `install_dir/static`.
    
    However, some versions of Windows won't let you pin a shortcut to a bat to the start menu. In this case, make a shortcut like this:
    
    `C:\Windows\System32\cmd.exe /c "C:\hydrus\Hydrus Source\hydrus_client-user.bat"`
    
    This is a shortcut to tell the terminal to run the bat; it should be pinnable to start. You can give it a nice name and the hydrus icon and you should be good!
    
    Or you can make a shortcut with the direct python executable that we saw before, something like:
    
    `C:\Hydrus\venv\Scripts\pythonw.exe C:\Hydrus\hydrus_client.py`

=== "Linux"

    If you want to redirect your database or use any other launch arguments, then copy 'hydrus_client.sh' to 'hydrus_client-user.sh' and edit it, inserting your desired db path. Run this instead of 'hydrus_client.sh'. New `git pull` commands will not affect 'hydrus_client-user.sh'.

=== "macOS"

    If you want to redirect your database or use any other launch arguments, then copy 'hydrus_client.command' to 'hydrus_client-user.command' and edit it, inserting your desired db path. Run this instead of 'hydrus_client.command'. New `git pull` commands will not affect 'hydrus_client-user.command'.

### Have Fun

If everything boots ok, great! Have a play around with the client and make sure file imports work ok and, if you are not macOS, that mpv is all correct. Hitting `help->about` will show if the optional libraries are all available and will give you error popups detailing any problems.

Don't forget to create a nice shortcut to your `hydrus_client` or `hydrus_client-user` launch script. If you can, set a custom icon--there are several `hydrus...` files in `install_dir/static` that are suitable.

??? note "System Qt styles"
    
    If you have a system Qt with several styles but do not see them under `options->style`, it is probably that your venv cannot "see" your system Qt.
    
    I am working on a cleverer answer for this, but a user (who knew he had PySide6 installed to his system python) discovered that if he manually set up his own venv, as in the guide below, with `python -m venv venv --system-site-packages`, and then removed `PySide6` and `shiboken` from his venv, it would load his system python and he could see all his styles.
    
    If you have this problem and put time into it, let me know how it goes.

### Simple Updating Guide

Updating is simple. If you installed with `git`, it takes about three seconds: just close the client, open the base install directory in a terminal, and type `git pull`. I have added easy 'git_pull' scripts to the install directory for your convenience (on Windows, just double-click 'git_pull.bat'). 

If you installed by extracting the source zip, update just as you would with the built extract: download the [latest release](https://github.com/hydrusnetwork/hydrus/releases/latest) source zip and extract it over the top of the folder you have, overwriting the existing source files.

If you get a library version error when you try to boot, run the venv setup again. It is worth doing this every 3-6 months, just to stay up to date. I mention in the release posts when there are important changes, usually right after a 'future build' test.

### Migrating from an Existing Install

Many users start out using one of the official built releases and decide to move to source. There is a full document [here](database_migration.md) about how to migrate a database, but for your purposes, the simple method is:

**If you never moved your database to another place and do not use -d/--db_dir launch parameter**

1. Follow the above guide to get the "running from source" install working in a new folder on a fresh database
2. **MAKE A BACKUP OF EVERYTHING**
3. Delete any test database you made from the "running from source" install's `db` directory.
4. Move your built release's entire `db` directory to the now-clear "running from source" install's `db` directory.
5. Run your "running from source" install again--it should load your old db no problem!
6. Update your backup routine to point to the new "running from source" install location.

**If you moved your database to another location and use the -d/--db_dir launch parameter**

1. Follow the above guide to get the "running from source" install working in a new folder on a fresh database (without --db_dir)
2. **MAKE A BACKUP OF EVERYTHING**
3. Just to be neat, delete any test database you made from the "running from source" install's `db` directory.
4. Run the "running from source" install with --db_dir just as you would the built executable--it should load your old db no problem!

**If you are currently on the macOS App.**

_Your App's database should be in `~/Library/Hydrus` (i.e `/Users/[You]/Library/Hydrus`. You can also hit up `file->open->database directory` in the client to make sure.)._

1. Follow the above guide to get the "running from source" install working in a new folder on a fresh database.
2. **MAKE A BACKUP OF EVERYTHING**
3. Delete any test database you made from the "running from source" install's `db` directory.
4. Move the contents of `~/Library/Hydrus` to your "running from source" install's `db` directory.
5. Run your "running from source" install again--it should load your old db no problem!
6. Update your backup routine to point to the new "running from source" install location.

_Note that these jobs are essentially the same as making a [clean install](getting_started_installing.md#clean_installs) in a new location._

### Moving Your Install Directory

The venv directory holds a private copy of python, and it contains absolute path references to itself. If you move your source install directory somewhere, trying to launch hydrus will give you an error about 'python' being missing.

**If you move your install directory, you have to build a new venv.** Just double-click the setup_venv script again, and you'll be back in a couple minutes.

If you want to run from source via a USB stick you will move between different computers, my setup_venv script will not be enough (a normal venv symlinks to your system python, and you have the absolute path issue); you will either have to rebuild your venv from the local python every time you move the stick or manually set up your own environment with a special embeddable version of python or self-contained environment creator like Conda's `constructor`.

## Doing it Yourself { id="what_you_need" }

_This is for advanced users only._

_If you have never used python before, do not try this. If the easy setup scripts failed for you and you don't know what happened, please contact hydev before trying this, as the thing that went wrong there will probably go much more wrong here._

You can also set up the environment yourself. Inside the extract should be hydrus_client.py and hydrus_server.py. You will be treating these basically the same as the 'client' and 'server' executables--with the right environment, you should be able to launch them the same way and they take the same launch parameters as the exes.

Hydrus needs a whole bunch of libraries, so let's now set your python up. I **strongly** recommend you create a virtual environment. It is easy and doesn't mess up your system python.

**You have to do this in the correct order! Do not switch things up. If you make a mistake, delete your venv folder and start over from the beginning.**

First get the hydrus source cloned with git:

`git clone https://github.com/hydrusnetwork/hydrus`

Then, to create a new venv:

* Open a terminal at your hydrus folder. If `python3` doesn't work, use `python`.
* `python3 -m pip install virtualenv` (if you need it)
* `python3 -m venv venv`
* `source venv/bin/activate` (`CALL venv\Scripts\activate.bat` in Windows cmd)
* `python -m pip install --upgrade pip`
* `python -m pip install --upgrade wheel`

!!! info "venvs"
    That `source venv/bin/activate` line turns on your venv. You should see your terminal prompt note you are now in it. A venv is an isolated environment of python that you can install modules to without worrying about breaking something system-wide. **Ideally, you do not want to install python modules to your system python.**  
    
    When you run the "activate" script, your environment is updated so that any time you type `python`, it runs the python copy we made in the venv directory and loads those libraries we have installed to it.
    
    This activate line will be needed every time you alter your venv or run the `hydrus_client.py`/`hydrus_server.py` files. You can easily tuck this into a launch script--check the easy setup files for examples.  
    
    If you would prefer not to run the "activate" script, you can just invoke the actual python binary instead. Perhaps this is easier for a shortcut or script you want to set up. In this case, rather than entering `python` on its own, you are doing calls like this:
    
    `/path/to/my/hydrus/venv/bin/python -m pip install .`
    
    -or-
    
    `C:\Hydrus Network\venv\Scripts\python -m pip install .`
    

**After you have activated the venv**, you can use pip to install everything you need to it from the `pyproject.toml` in the install_dir:

```
python -m pip install . --group qt6-normal --group opencv-normal --group mpv-normal --group other-normal
```

If you need different versions of libraries, check the `pyproject.toml` file itself. For instance, for the newer OpenCV and Qt, you'd do this:

```
python -m pip install . --group qt6-test --group opencv-test --group mpv-normal --group other-normal
```

### Qt { id="qt" }

Qt is the UI library. I used to support Qt5, but no longer. You can run PySide6 or PyQt6--a wrapper library called `qtpy` allows this. The default is PySide6, but if it is missing, qtpy will fall back to an available alternative. You can choose PyQt6 like this:

```
python -m pip install . --group qt6-new-pyqt6 --group opencv-normal --group mpv-normal --group other-normal
```

If you have multiple Qts installed, then select which one you want to use by setting the `QT_API` environment variable to 'pyside6' or 'pyqt6'. Check _help->about_ to make sure it loaded the right one.

!!! note "Qt compatibility"
    
    If the program fails to run, and from terminal it says something like this:
    
    `qt.qpa.plugin: From 6.5.0, xcb-cursor0 or libxcb-cursor0 is needed to load the Qt xcb platform plugin`
    
    Then Qt6 may need a couple additional packages:
    
    * `libicu-dev`
    * `libxcb-cursor-dev`
    
    With `apt`, that will be:
    
    * `sudo apt install libicu-dev`
    * `sudo apt install libxcb-cursor-dev`
    
    Or check your OS's package manager.
    
    If you still have trouble with the default Qt6 version, try running setup_venv again and choose a different version. There are several to choose from, including (w)riting a custom version. If you are having a lot of trouble, this list can be worth exploring: [PySide6](https://pypi.org/project/PySide6/#history)
    

### mpv { id="mpv" }

MPV is optional and complicated, but it is great, so it is worth the time to figure out!

As well as the python wrapper that we installed in the venv, you also need the underlying dev library, which means a .dll or .so file. This is _not_ mpv the program, but `libmpv`, often called `libmpv1` or `libmpv2`.

For Windows, the dll builds are [here](https://sourceforge.net/projects/mpv-player-windows/files/libmpv/), although selecting a stable version can be difficult on older machines. Just put it in your hydrus base install directory. Check the links in the easy-setup guide above for good versions. You can also just grab the 'mpv-1.dll'/'mpv-2.dll' I bundle in my extractable Windows release.

If you are on Linux, you can usually get `libmpv` like so:

`sudo apt install libmpv1`  
-or-  
`sudo apt install libmpv2`

On macOS, you should be able to get it with `brew install mpv`, but you are likely to find mpv crashes the program when it tries to load. Hydev is working on this, but it will probably need a completely different render API.

Hit _help->about_ to see your mpv status. If you don't have it, it will present an error popup box with more info.

### SQLite { id="sqlite" }

If you can, update python's SQLite--it'll improve performance. The SQLite that comes with stock python is usually quite old, so you'll get a significant boost in speed. In some python deployments, the built-in SQLite not compiled with neat features like Fast Text Search (FTS) that hydrus needs.

On Windows, get the 64-bit sqlite3.dll [here](https://www.sqlite.org/download.html), and just drop it in your ~~base install directory~~ python install location's DLLs folder, likely something like `C:\Program Files\Python311\DLLs` or `C:\Python311\DLLs`. There should be a sqlite3.dll there. Rename it to sqlite3.dll.old and add your newer one in.

You _may_ be able to update your SQLite on Linux or macOS with:

* `sudo apt install libsqlite3-dev`
* (activate your venv)
* `python -m pip install pysqlite3`

But as long as the program launches, it usually isn't a big deal.

!!! note "Anaconda"
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

## My Code { id="my_code" }

I use Windows and Linux, but I have more experience with Windows, and the program is generally most stable and clean there. I have very little experience with macOS, but I appreciate bug reports for any platform.

My coding style is unusual and unprofessional. Everything is pretty much hacked together. I'm constantly throwing new code together and then cleaning and overhauling it down the line. If you are interested in how things work, look through the source and please do ask me if you don't understand something.

I work strictly alone, however. While I am very interested in bug reports or suggestions for good libraries to use, I am not looking for pull requests or suggestions on refactoring. I know a lot of things are a mess. Everything I do is [WTFPL](https://github.com/sirkris/WTFPL/blob/master/WTFPL.md), so you can fork and play around with things on your end as much as you like.

[This DeepWiki AI Crawl](https://deepwiki.com/hydrusnetwork/hydrus) of the Hydrus Github repository is not totally comprehensive, but I was impressed with how generally accurate it is. It attributes more thought on my part than actually happened, hahaha, but you might like to check it if you want to poke around.
