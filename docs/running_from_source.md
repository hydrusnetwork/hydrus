---
title: running from source  
---

I write the client and server entirely in [python](https://python.org), which can run straight from source. It is not simple to get hydrus running this way, but if none of the built packages work for you (for instance you use a non-Ubuntu-compatible flavour of Linux), it may be the only way you can get the program to run. Also, if you have a general interest in exploring the code or wish to otherwise modify the program, you will obviously need to do this.

## a quick note about Linux flavours { id="linux_flavours" }

I often point people here when they are running non-Ubuntu flavours of Linux and cannot run the build. One Debian user mentioned that he had an error like this:

```
_ImportError: /home/user/hydrus/libX11.so.6: undefined symbol: xcb\_poll\_for_reply64_
```

But that by simply deleting the _libX11.so.6_ file in the hydrus install directory, he was able to boot. I presume this meant the build was then relying on his local libX11.so, which happened to have better API compatibility. If you receive a similar error, you might like to try the same sort of thing. Let me know if you discover anything!

## building packages on windows { id="windows_build" }

Installing some packages on windows with pip may need Visual Studio's C++ Build Tools for your version of python. Although these tools are free, it can be a pain to get them through the official (and often huge) downloader installer from Microsoft. Instead, install [Chocolatey](https://chocolatey.org/) and use this one simple line:

```
choco install -y vcbuildtools visualstudio2017buildtools
```

Trust me, just do this, it will save a ton of headaches!

This can also be helpful for Windows 10 python work generally:

```
choco install -y windows-sdk-10.0
```


## what you will need { id="what_you_need" }

You will need basic python experience, python 3.x and a number of python modules, all through pip.

First of all, get the actual program. The github repo is [https://github.com/hydrusnetwork/hydrus](https://github.com/hydrusnetwork/hydrus). If you are familiar with git, you can just clone the repo to the location you want, but if not, then just go to the [latest release](https://github.com/hydrusnetwork/hydrus/releases/latest) and download and extract the source code .zip or .tar.gz somewhere. The same database location rules apply for the source release as the builds, so if you are not planning to redirect the database with the -d launch parameter, make sure the directory has write permissions (e.g. in Windows, don't put it in "Program Files")

Inside the extract should be client.py, client.pyw, and server.py. You will be treating these basically the same as the 'client' and 'server' executables--you should be able to launch them the same way and they take the same launch parameters as the exes. On Windows, using client.pyw allows you to neatly launch the program without a command terminal appearing behind it, but both the .py and .pyw work fundamentally the same--feel free to play with them both.

Hydrus needs a whole bunch of libraries, so let's now set your python up. If you are on Linux or macOS, or if you are on Windows and have an existing python you do not want to stomp all over with new modules, I recommend you create a virtual environment:

_Note, if you are on Linux, it may be easier to use your package manager instead of messing around with venv. A user has written a great summary with all needed packages [here](running_from_source_linux_packages.txt)._

To create a new venv environment:

*   (navigate to your hydrus extract folder in a terminal)
*   ```pip3 install virtualenv``` (if you need it)
*   `pip3 install wheel` (if you need it)
*   `mkdir venv`
*   `virtualenv --python=python3 venv`
*   `. venv/bin/activate`

That `. venv/bin/activate` line turns your venv on, which is an isolated copy of python that you can install modules to without worrying about breaking something system-wide, and will be needed every time you run the `client.pyw`/`server.py` files. You should see your terminal note you are now in the venv. You can easily tuck this venv activation into a launch script.

On Windows Powershell, the command is `.\venv\Scripts\activate`, but you may find the whole deal is done much easier in cmd than Powershell. When in Powershell, just type `cmd` to get an old fashioned command line. In cmd, the launch command is just `venv\scripts\activate`, no leading period.

After that, you can use pip to install everything you need from the appropriate requirements.txt in the base install directory. For instance, for Windows, you would go:

```
pip3 install -r requirements_windows.txt
```

If you prefer to do things manually, inspect the document and install the modules yourself.

## PyQt5 support { id="pyqt5" }

For Qt, either PySide2 (default) or PyQt5 are supported, through qtpy. For PyQt5, go:

```
pip3 install qtpy PyQtChart PyQt5
```

## FFMPEG { id="ffmpeg" }

If you don't have FFMPEG in your PATH and you want to import anything more fun than jpegs, you will need to put a static [FFMPEG](https://ffmpeg.org/) executable in your PATH or the `install_dir/bin` directory. If you can't find a static exe on Windows, you can copy the exe from one of my extractable releases.

## mpv support { id="mpv" }

MPV is optional and complicated, but it is great, so it is worth the time to figure out!

As well as the python wrapper, 'python-mpv' as in the requirements.txt, you also need the underlying library. This is _not_ mpv the program, but 'libmpv', often called 'libmpv1'.

For Windows, the dll builds are [here](https://sourceforge.net/projects/mpv-player-windows/files/libmpv/), although getting the right version for the current wrapper can be difficult (you will get errors when you try to load video if it is not correct). Just put it in your hydrus base install directory. You can also just grab the 'mpv-1.dll' I bundle in my release. In my experience, [this](https://sourceforge.net/projects/mpv-player-windows/files/libmpv/mpv-dev-x86_64-20210228-git-d1be8bb.7z/download) works with python-mpv 0.5.2.

If you are on Linux/macOS, you can usually get 'libmpv1' with _apt_. You might have to adjust your python-mpv version (e.g. `pip3 install python-mpv==0.4.5`) to get it to work.

## SQLite { id="sqlite" }

If you can, update python's SQLite--it'll improve performance.

On Windows, get the 64-bit sqlite3.dll [here](https://www.sqlite.org/download.html), and just drop it in `C:\Python37\DLLs` or wherever you have python installed. You'll be overwriting the old file, so make a backup if you want to (I have never had trouble updating like this, however).

I don't know how to do it for Linux or macOS, so if you do, please let me know!

## additional windows info { id="additional_windows" }

This may not matter any more, but in the old days, Windows pip could have problems building modules like lz4 and lxml. [This page](http://www.lfd.uci.edu/~gohlke/pythonlibs/) has a lot of prebuilt binaries--I have found it very helpful many times.

I have a fair bit of experience with Windows python, so send me a mail if you need help.

## running it { id="running_it" }

Once you have everything set up, client.pyw and server.py should look for and run off client.db and server.db just like the executables. They will look in the 'db' directory by default, or anywhere you point them with the "-d" parameter, again just like the executables. Explictly, you will be entering something like this in the terminal:

```
. venv/bin/activate
./client.py -d="/path/to/database"
```

Again, you may want to set up a shortcut to a script to make it easy.

I develop hydrus on and am most experienced with Windows, so the program is more stable and reasonable on that. I do not have as much experience with Linux or macOS, but I still appreciate and will work on your Linux/macOS bug reports.

## Building the docs

When running from source you will also need to [build the hydrus help docs](about_docs.md) yourself.

## my code { id="my_code" }

My coding style is unusual and unprofessional. Everything is pretty much hacked together. If you are interested in how things work, please do look through the source and ask me if you don't understand something.

I'm constantly throwing new code together and then cleaning and overhauling it down the line. I work strictly alone, however, so while I am very interested in detailed bug reports or suggestions for good libraries to use, I am not looking for pull requests or suggestions on style. I know a lot of things are a mess. Everything I do is [WTFPL](https://github.com/sirkris/WTFPL/blob/master/WTFPL.md), so feel free to fork and play around with things on your end as much as you like.