---
title: Changelog
---

# changelog

!!! note
    This is the new changelog, only the most recent builds. For all versions, see the [old changelog](old_changelog.html).

## [Version 661](https://github.com/hydrusnetwork/hydrus/releases/tag/v661)

### qt media player

* the QtMediaPlayer test is complete, and I am making it the default fallback if mpv is unavailable! thanks to everyone who helped with it
* this player is a video and audio player just like mpv, but it uses simpler native Qt tech and works more reliably than mpv. it has lower performance, but for macOS and Wayland users, there is now a viable way to play noise in hydrus
* if you start up a new client and mpv is not available, video and audio is now set to use the QtMediaPlayer
* users who are currently set to view some video/audio with the native viewer or an open externally button will get a special popup after updating explaining there is a new player and how to check it out
* the old 'video widget (Test 1)' QtMediaPlayer is retired and the successful 'Graphics View (Test 2)' player is now just `QtMediaPlayer` in UI and code. anyone who has a view setting for the old test will be switched to the new on update
* the 'use the same QtMediaPlayer through media transitions' test setting now defaults to False, is renamed to a DEBUG setting, and all users will be set to False on update. I fixed the bugs, but it has some flicker and doesn't appear to improve performance over just creating a new one every time

### openraster support

* thanks to a user, we now have OpenRaster (.ora) support! not dissimilar to Krita, this is an open 'image project' format (like PSD) that is supported by some programs like Gimp
* we show the image like Krita or PSD in the normal media viewer

### more granularisation work

* thank you to those who tested the granularisation migrations! we found the migration speed was about as expected, except that the clever BTRFS filesysttem worked at 10x speed. no failures, just a bit slow for big clients
* I wrote some more migration tech and have added a 'I want to return from 3 back to 2' button to the panel, so this is now completely undoable at the db level, and a couple pain-in-the-neck failure or backup recovery states are now easier to navigate
* the granularisation routine also has some folder optimisations to reduce worst-time performance on some very slow storage devices
* in an effort to buffer against high latency file storage, I tested out some worker pools to rename files in parallel. there may be a world where this improves performance radically for general use, but across my test platforms I would rarely get better than 20% improvement in speed, and best-case performance generally nosedived because of overhead. in my ongoing KISS push, I thus unwound the clever answer that didn't help all that much. this overall suggests that renaming isn't something you can cheat--depending on the device, it is either already well buffered or a rename is so primitive that the OS forces atomicity
* updated the unit tests to test more file moves, prefix canonisation, and a subfolder creation failure error state
* gave the help in 'database migration' a soft pass and added a screen of the panel

### hydrus MCP

* a user has been working on an MCP server for the hydrus API! this is basically an instruction set that teaches an AI model you are running (e.g. with LM Studio) how to talk to hydrus, so you can ask your model questions in natural language like 'how much did I import in the past 24 hours', and it goes and fetches the data it needs, thinks about it, and reports back. I added it to the Client API help list, and you can find it here: https://github.com/TheElo/HydrusMCPServer
* as a side thing, I played with plugging some AI models into my IDE (PyCharm) this week. I haven't got much real experience with this stuff yet so I wanted to poke around. as many others say, I think it is really cool for certain things, but you need a high-performance model. I'm passionate about running models locally, and my underpowered NUCs can't run the bigger models that produce better-quality work, so I turned most of the tech off again and hardening my plan to get an AI box to sit under my desk (probably my new vidya machine when I have dosh saved up and can snipe a good price). I will thus be contributing my part to the tightening ram/GPU market, hooray

### future build with new install structure

* _only for advanced users. we'll test how this goes and then roll it out to everyone next week assuming no problems_
* thanks to the work of another user, I am making another future build this week. This is a special build with new libraries that I would like advanced users to test out so I know they are safe to fold into the normal release.
* in the release post, I will link to this alternate build. if you are experienced and would like to help me, please check it out
* special notes for this time: new cleaner one-directory build, and some version updates. clean install needed. I'd like to know if you have any path problems and how mpv goes on Windows
* the specific changes this week are--
* the builds now tuck all the .dlls and other library files and folders into a single `lib` subfolder, so the program is now structured `hydrus_client` and `hydrus_server` executables and a `lib` dir. if you boot like normal, you then get a second `db` directory. all much simpler and cleaner
* if you use the Windows installer, you do not have to do anything; just install like normal and your old install will be cleaned up and the new one put in place. if you use the Windows or Linux extracts, **you will have to do a 'clean install'**, help here: https://hydrusnetwork.github.io/hydrus/getting_started_installing.html#clean_installs. this is the last time you'll have to do such a messy clean install like this. if you haven't done a 'clean install' before, basically you delete everything except the 'db' dir and its contents before extracting like normal, to clear out old dlls and such
* futhermore--
* the Docker packages are updated to Alpine 3.23
* SQLite on Windows is updated to 3.51.2
* mpv on Windows is updated to 2026-02-01
* thanks to the clean install, the Windows mpv dll is no longer renamed, but now `libmpv-2.dll`
* and for the build scripts, the client and server specs are now merged into one, the gubbins in the spec is pushed to the new content_dir 'lib', Docker builds are cached better, and everything is cleaner

### boring build path stuff

* **if you patch how hydrus sets up its paths, watch out for changes to `HydrusConstants` and friends this week**
* with the changes in the future build, hydrus is now a bit smarter about how it figures out paths--
* it now differentiates between the base install dir and contents dir. it uses `__file__` tech more than before. in a source install, the base and contents dir are the same, but in a one-dir pyinstaller deployment, like we are testing, stuff like `static` is now in `base_dir/lib/static`

### misc boring stuff

* I finally finally caught up with a github repository job that was sitting on my desktop and now `https://hydrusnetwork.github.io/` redirects to the normal help at `https://hydrusnetwork.github.io/hydrus`
* added the uv-specific `uv.lock` to the `.gitignore`. one is supposed to commit this, but there are still wrinkles to be ironed out before we buy in, and adding it to the ignore list stops some branch confusion for users who do use `uv`
* added `.python-version` to the base dir, which certain environment managers pick up on as the suggested version to deploy. I have selected `3.13` as the current recommended source python. if you are otherwise, it isn't a big deal
* the `pyproject.toml` now explicitly says `>=3.10,<3.15` as the supported pythons for hydrus (this adds a new 'not ready for 3.15.x' bound)
* the `setup_venv.py` now moans at you especially if you start it up with python `>=3.15`
* I am not totally happy with the recent changes to `pyproject.toml`, which had to be emergency-patched last week. I will be revisiting it in the near future with a big KISS brush. most of the overly-complicated groups are going to disappear such that normal package managers will just work out of the box with it, and `setup_venv.py` will be the canonical place to install test library versions. no big changes yet, but since I was already planning to sunset some group stuff for v373, expect that to be the new date for this to get much simpler. I'll try and push on this next week
* because of a surprise unicode issue that broke the Windows github build last week, `mkdocs-material` is now pinned to `9.7.1`
* if you create a new non-default-location database using the --db_dir (or the new build structure creates a new db in the new clean basedir), I now copy the .txt help files and the sqlite3.exe on Windows over to the new dir
* misc help cleanup regarding the install structure
* updated the help here and there to talk about QtMediaPlayer versus mpv
* misc `HydrusConstants` cleanup
* deleted the ancient UPnP dialog. I have no idea if any of it still worked, and I don't bundle the exe it relies on any more. I'll be clearing the optional upnp tech out from the servers similarly--this stuff is not my job and I'm not keeping up with the technical debt
* fixed an issue with the location storage update code last week when the client being updated has two ideal storage locations set that are actually the same location. same deal for updating the locations in the 'move media files' dialog

## [Version 660](https://github.com/hydrusnetwork/hydrus/releases/tag/v660)

### misc

* I cleaned up some internal layout logic in my new QtMediaPlayer. transitioning from certain landscape to portrait videos should no longer reposition the video to the right when you have 'use the same QtMediaPlayer' checkbox ticked. thank you for the reports. let's try one more time: if you are happy with this, I'll make it real
* the new 'help: random 403 errors' menu items on every retry button were driving me nuts, so I moved them to the 'retry ignored' button selection dialog
* fixed several issues when loading an Ugoira (or several other animation types) that has a faulty (0 or null) number of frames
* the 'check database integrity' job is completely removed. this thing is only useful for detecting SQLite-level corruption, which we often see as a 'malformed' error, and really should be run from the command line interface, on one file at a time, when working through the 'help my db is broke.txt' document. several users have wasted time with this thing over the years hoping it would fix other bugs--unfortunately, it does not
* added `database->db maintenance->clear orphan URL mappings`, a new job that helps resolve some 'system:num_urls' stuff if your client.master.db has been damaged

### cleaner venv setup

* _this only matters for users who run from source_
* thanks to a user, the setup_venv scripts and general venv setup are simplified and improved. years of behind-the-scenes cruft is cleared
* for a while, I've maintained both a scatter of old requirement.txts to handle the different choices you make in `setup_venv.blah` and a more modern `pyproject.toml` file that bundles everything in a nicer way and can be used by tools like `uv`. the setup_venv script routine is now updated to talk to that pyproject.toml, so all the old .txts are gone. this cleans up how your venv is installed, making it one atomic call and allowing easier editing of package choices in future (also removes the duplicate maintenance situation)
* further, the three setup_venv scripts are converted into stubs that call one single multiplat `setup_venv.py` file. you can just run that `setup_venv.py` file on its own and it works, so that is now the recommendation for all platforms. this script now talks about how to launch the program after its 'Done!' message, too
* I've updated the 'running from source' help to talk about this. also, anyone who manually pip-installs their venv is using a different command to hit the single `pyproject.toml` rather than the requirements.txts, and I added some stuff about the venv `activate` script, and I talked a bit about python vs pythonw in Windows
* as I recently did with the setup_venv, I have decided to rename some of the groups in the `pyproject.toml`. the three groups `mpv-new`, `opencv-new`, and `qt6-new` are being renamed to `xxxx-normal`. I am achieving this today simply by duplicating the groups with new names, so using the old `xxxx-new` name will still work for now. I will be deleting the old group names in three months, v673, so if you have an automatic script that installs hydrus, please update it. since these are the default selections, I presume no one uses them and this doesn't really matter
* I will also delete the old `setup_venv.bat/sh/command` stubs and the basedir `requirements.txt` in three months, in v673, to be clean. if you use them in an automated script, please switch over to the .py
* I ran out of time, but I'll do the same for setup_help and git pull--it can all be multiplat .py soon

### file storage granularity test

* _for advanced users now, everyone else soon_
* after much planning, I am rolling out a test for advanced users with fewer than 1 million files
* that improves latency on file access and other maintenance operations for clients with many files
* essentially, instead of storing files in just 256 "fxx" folders, the client can now use 4096 "fxx/x" folders. same for the "txx" thumbnails. this means 16x fewer files per subfolder, where big clients are pushing 10,000+, making for snappier folder scans and file access in the client and when you do something like 'open video externally' and the video player does a brief folder scan for subtitle files and such
* this is all accessed through `database->move media files...` in a new panel. your client now reports if it is currently granularity 2 or 3 and offers to migrate you to 3. this process involves moving all your files, so it can take a while. my tests suggest about 5,000 files/s on an NVME, so thumbs will zip by, but the actual files on HDD may be a good bit slower, especially on funky USB or NAS connections where there's odd buffering. it is cancellable if it is taking too long
* some first-draft help here too https://hydrusnetwork.github.io/hydrus/database_migration.html#granularity
* one additional issue is that this storage rejigger makes a backup look completely different! we don't want to do a 100% backup run just to mirror file moves, so this panel offers a similar migration for a backup. the text and dialogs guide you through it all
* if you are an advanced user with fewer than 1 million files and you definitely absolutely have a backup, I invite you to try this operation out. obviously let me know if there are any problems, but please also note the final dialog, which will say how long the migration took, and report to me something like, "500,000 files, thumbs on NVME, files on sata HDD, 21 minutes", which I hope to compile into nicer 'expect about x files/s on an HDD' estimates for the normal users
* if you have 8 million files and really want to do this, you can, but bear in mind it might be a three hour migration

### boring file storage work

* the tables that track physical file storage have been updated to better handle 4096 rows rather than 256. all the tables now use a shared `location_id` table, with the same single read/write calls, ensuring all items here agree on portable vs absolute path storage and so on
* the database now stores how 'granular' its file storage is, with default being 2 (2 hex chars, or 256 subfolders). if the stored file locations do not match this, it raises a serious error
* the folder relocation code (when you do a 'move files now' run, and which will be replaced this year I hope by multi-location support and background migration) is more KISS and foolproof
* the folder repair code (when you boot with a missing location) is similarly more KISS and foolproof
* fixed a storage weight initialisation issue that could occur if the 'ideal thumbnail location' was specifically set and also in the media file storage locations list
* all prefix-generating methods now always take an explicit prefix length/granularity. there is no longer a nebulous default anywhere
* reworked my folder granularisation to be safer, to work both up and down, and added status reporting for an UI panel
* wrote a routine that looks at an existing base storage location and guesses its current granularisation for job pre-checks
* wrote a database granularisation routine and added 'aieeeee, it broke half way through, try and undo' code
* the client files manager now only performs rigorous checks of all existing subfolder locations on startup. any migration or other re-init reason now just repopulates the subfolder store
* when file subdirs of granularity 3 or more are migrated, if the intervening parent directory, for instance `f83` in a `f83/d` prefix, is empty afterwards, it is now deleted
* the percentage usages in 'move media files' are now 2 sig figs since we are distributing 4096 things now and you'd get 0.0% sometimes
* the mysterious 'empty_client_files' archive is updated regarding all this
* wrote a 'help my db is the wrong granularity.txt' help document in the db dir for help recovering from big problems here
* wrote unit tests for 2to3 and 3to2 granularisation and cancel tech
* wrote unit tests for estimate folder granularity tech

### boring cleanup

* I deleted a bunch of very old 'running from source' help from the pre-everything-is-a-wheel days that is no longer pertinent
* deleted some ancient unused client service UI code

## [Version 659](https://github.com/hydrusnetwork/hydrus/releases/tag/v659)

### misc

* certain PNGs that would load very slowly now load about ten times faster! specifically, any PNG with gamma/chromaticity information in its header now has that converted to a bespoke ICC Profile, and the normal ICC Profile translation code is applied to convert to sRGB. my hacky (and possibly unstable) manual conversion is no longer used. typically, a big ~50 megapixel PNG (7,000x8,000) would render in about ten seconds with lots of memory churn; now it renders in one, with far less. this fix brought to you by ChatGPT, which understands ICC Profile header construction, `r/g/bTRC` gamma curves, and D50/D65 `wtpt` and `chad` applicability across ICC Profile engine versions far better than it did last year. thanks for your patience, those who submitted weird big PNGs in. if you have any PNGs (or any other file of course) that suddenly render with the wrong colour, I'm interested to see them
* the `network->downloaders` menu has new 'user-run downloader repository' and 'help: random 403 errors' items. the former links to https://github.com/CuddleBear92/Hydrus-Presets-and-Scripts, the latter opens a little help window that talks about the infrastructure changes that are slowly breaking some of the original default downloaders. this help window is now linked off any downloader 'retry' icon button that has 'ignored' stuff to retry, and I replicated it in the 'getting started with downloaders' help, so I hope anyone who gets perplexed by a 403 will now see what's going on. there is no excellent solution here, but I am thinking about it (issue #1963)

### fixes

* fixed the new unified directory picker to always return a path with backslashes on Windows. it was producing one with forward slashes, which in certain listdir operations (like 'add folder' in the import files dialog) was generating paths with mixed slashes and backslashes(!!). python handles this situation well and it didn't break anything, but it is ugly, unwise, and caused some path duplicates since you could add the same path to certain lists with both slashes and backslashes. the various 'add filename(s)' dialogs were already normalising correctly, so I believe we are fully covered here now. thank you to the users who reported this
* fixed a stupid bug that meant if you renamed an import folder, it would always be renamed as a non-duplicate 'import folder name (1)' alternate
* I think I have fixed the issue where the new QtMediaPlayer could sometimes 'scroll inside' the viewport of the player on a mouse wheel event. this seemed to be aggravated by the aspect ratio changes caused by having the `TEST: Use the same QtMediaPlayer through media transitions` checkbox on. I was going to force everyone out of this test mode (it is currently default), but I think I fixed it correct so I won't yet. let me know how things are now--if we are good, then I think it is time to formalise this test into a real thing
* fixed some bad reset code in the duplicate potential pair search when you have the 'try to state a final estimate' setting on. it was possible for it to do some confidence math on a hitrate of over 100% and it got into trouble when generating the count. the reset code is nicer and the math now checks for and handles non-sensible input (issue #1960)

### client api

* fixed the 'fetch SVG file for rating service' routine when the SVG file is a user override in their `db/static` dir
* fixed the 'this service doesn't use an SVG rating' 404 when fetching SVG files for rating services--it was 500ing previously. added a unit test for this too
* fixed the error handling in this SVG fetch routine to handle certain other error cases better
* client api version is now 88

## [Version 658](https://github.com/hydrusnetwork/hydrus/releases/tag/v658)

### misc

* fixed an exclusive-to-inclusive system predicate parsing regression, for instance the input `system:filetype is not x` was parsing as `system:filetype is x`, which was because of a logical hole in a recent rewrite
* added 'Active Search Predicates list height' to `options->file search`. this is the list _above_ the tag autocomplete input on normal search boxes. defaults to 6 (was previously 8 due to weirdness)
* tag lists no longer default to min height 8 rows but 1. let me know if anything sizes crazy now
* fixed the `help->about` db transaction period, which was typoed and calculating off the wrong number
* the 'don't use important accounts with hydrus' warning is clarified and unified in the downloader help, login dialog, and now session cookies dialog
* the media viewer right-click menu now has a 'player' sub-menu at the end that says what player (mpv, QtMediaPlayer, Hydrus Native stuff) is currently in view. might be worth tucking this into a deeper advanced/maintenance/debug menu somewhere in a future reshuffle, but for now it is there

### QtMediaPlayer (and an mpv thing)

* fixed a 'C++ object already deleted' instability error with the new GraphicsView QtMediaPlayer. I had this a couple of times in devving but needed to tighten up how some mouse event hacks were owned and destroyed
* fixed an UI hang that could sometimes occur in PySide6 when opening a new media viewer when the preview viewer already has a QtMediaPlayer loaded
* added `TEST: Use the same mpv player through media transitions` and `TEST: Use the same QtMediaPlayer through media transitions` options to `options->media playback`. previously, I would always create or swap to a different player when navigating from video to video, because re-using the same guy was super flickery or crash city. things are better now and I'm open to testing it more
* added `TEST: Use OpenGL Window in QtMediaPlayer` to `options->media playback`. maybe it improves performance for big vids? I noticed it can cause some initial window-level flickering in Windows, but it is worth trying in different situations

### boring QtMediaPlayer cleanup

* the new GraphicsView test now loops natively and tracks 'num plays' through some fudgy maths (previously it hooked into the video 'end; stop' statechange and manually did 'seek 0; play'). I've had some reports about the program hanging on video end-loop, so let's see if this helps that
* made the mouse-move event hack a little safer
* rewrote some media destruction signals and moved QtMediaPlayer destruction responsibility from the GUI to the MediaContainer itself. there's no more weird reparenting
* QtMediaPlayers are now cleaned up more aggressively. generally a 500ms timer instead of 5s

### boring cleanup

* broke `options->media playback` into sections and fixed some layout issues
* fixed a bit of foolishness that was causing the `hydrus_test_boot.py` unit test script to always exit( 1 ) even when everything was OK
* relatedly, replaced all lazy `except:` handling with `except Exception as e:`
* if the duplicates filter fails to generate a visual duplicate comparison, the error now only makes one popup per program boot. it still spams some basic 'hash x failed' stuff to log so we can debug the issue
* cleaned up a little 'menu last click' global out of HG
* added a 'Run the launch script, not the .py' note to the 'running from source' help

### boring import options overhaul

* broke the 'file filtering import options' (stuff like allowed filetypes and min/max filesize) out of 'file import options (legacy)' just like I did presentation and prefetch import options the other week. the legacy object now holds a 'file filtering import options' sub-object in prep for the conversion to the new options structure
* did the same for the 'location import options' (stuff like where to put the file and auto-archive/url options)
* wrote an edit panel for 'file filtering import options'
* did the same for 'location import options'
* fixed the red warning text about an invalid, empty import destination context to now appear properly and instantly on dialog load, if it boots with an invalid destination context
* 'associate primary/source urls' checkboxes are no longer hidden behind advanced mode
* the prefetch import options are now in their own edit panel
* the presentation and notes import options panels are now QWidgets not ScrollingEditPanels, which will fix some jank layout we've seen here
* fixed some layout expanding issues in the file import options panel
* network job and file import statuses now work with a file filtering import options object for their filtering decisions, not a file import options
* importers now consult a location import options for pre-work destination validity checks
* updated the unit tests for the new 'file filtering import options' object
* updated the unit tests for the 'location import options' object
* wrote some very basic prefitch import options unit tests

## [Version 657](https://github.com/hydrusnetwork/hydrus/releases/tag/v657)

### misc

* the 'edit header' dialog panel, where you configure custom http headers, is given a usability pass. this thing never got out of debug-tier and none of the widgets were labelled lol. it has a grid with labels and some nicer strings for the enigmatic 'approved' status
* added some safety code for the new `tldextract` test I added last week. one of the calls I make is newer than I expected (issue #1953)

### QtMediaPlayer

* I revisited the QtMediaPlayer, which is an experimental alternate to the mpv embed that I haven't touched in ages. I may have strongly succeeded
* I am rolling out a new type of QtMediaPlayer. the old one is called (Test 1 - VideoWidget); this new one is (Test 2 - GraphicsView). both are listed in the `options->media playback` settings for audio/video/animation. this new GraphicsView solution does not have the 'always on top' rendering problem the old one had, meaning the seek bar is shown and behaves properly!! this guy basically looks just like mpv, although it is less customisable and your performance and interpolation quality etc.. may be a little worse (issue #1883)
* if you have had trouble with mpv, please try this new GraphicsView player out. I don't know how crashy it is, so brace yourself. I'm interested in performance, errors, what filetypes it cannot handle, which mouse interactions fail to register, anything you think pertinent. if we can nail it down, I can polish all this as the new mpv fallback for macOS and Wayland and anyone else with mpv trouble
* one thing I did notice btw is that it spams some debug-warning stuff to your log when it loads files with unusual metadata. I silenced a bunch of it with Qt logging options, but there's more to do
* all users can now see the experimental QtMediaPlayer options. previously it was blocked behind source users in advanced mode
* the volume button now appears for QtMediaPlayers (although obviously still hidden by the 'on top' behaviour of the old one)
* fixed volume application for the experimental QtMediaPlayer--because of a type problem, it was either doing mute at 0 or 100% everywhere else
* fixed an unload media bug in the QtMediaPlayer for PyQt6

### new hydrus API web-based browser

* another user has created a web portal for your hydrus install! check it out here: https://hyaway.com/ | documentation https://docs.hyaway.com/ | github https://github.com/hyaway/hyaway
* I don't know much about it, but it looks cool and is open source. you can use the hosted version at that site or set up your own instance. if you want to browse your client from your phone, check it out
* I added this to the collection of other Client API tools on the landing page here https://hydrusnetwork.github.io/hydrus/client_api.html

### Client API rating colours

* the `Services Object` in the Client API now provides the pen and brush colours for different rating service states, in #ffffff format, and bools for `show_in_thumbnail` and `show_in_thumbnail_even_if_null`, and for numerical ratings, a convenience `allows_zero`.
* updated the unit tests to check for this and the help to talk about it
* the Client API version is now 87

### python 3.14 and opencv

* tl;dr: you can now get setup with hydrus on the (new) python 3.14 easily--just do `setup_venv` as normal and select `(a)dvanced` and then `(t)est` for everything
* it has been previously tricky to run hydrus on python 3.14 because of some funny library stuff. you could fudge things manually, but it wasn't nice, there were image rendering bugs, and the `setup_venv` script didn't have a path for it. this situation improved in just the last week, which is good because some users on bleeding edge OSes are getting rollouts of 3.14 right now (issue #1950)
* the 'test' version of `opencv-python-headless` is bumped from `4.12.0.88` to `4.13.0.90`, which is the first version of OpenCV that is ok with the newer numpy
* the 'normal' vs 'test' OpenCV requirement bundles now include `numpy`, with respective versions of `~2.3.1` and `2.4.1`
* as a side thing, the new 'test' Qt, `PySide6 6.10.1`, seems to be the first version that installs nicely on 3.14
* all the `setup_venv` scripts now ask if you want the `(n)ormal` rather than the `(n)ew` version of things. 'new' was originally to contrast to the 'old' version, but these days it is more confusing vs 'test'
* all the `setup_venv` scripts now direct users on Py 3.14 to go in (a)dvanced mode. get the (t)est versions of things and you should be good, but I'll be interested to hear where not
* all the `setup_venv` scripts now temporarily ask a fourth question in (a)dvanced mode, for the new domain-parsing `tldextract` library, which I added test code for last week
* as a side thing, in the `setup_venv.bat` script, the secret (d)ev mode that adds some unit test and build gubbins now allows you (me) to make the (a)dvanced choices
* I also maintain a 3.14 test environment here in my IDE. I can do 3.10-3.14 and PyQt6 and regularly do simple tests in all of them, so I hope we'll catch bigger version-specific issues, and we'll know when 3.10 is no longer supportable

### network domain management overhaul, mostly boring

* a push on better per-domain settings and status tracking went well. like with other recent rewrites, I've mostly just done behind the scenes prep work, with no large changes yet, but I'm feeling good about it. in the end of this, I hope to have domain-specific settings for most of the stuff in the 'general' panel of `options->connection`. again, like with other settings overhauls, I'm planning to have a global default which you then override with custom settings for a particular domain if you wish. ideally we'll have favourites/templates and the ability to bundle these settings with a downloader, like you can headers and bandwidth rules
* the 'halt new jobs as long as this many network infrastructure errors on their domain' setting now applies to all levels of the domain. if `site.com` gets a bunch of connection errors, a request to `subdomain.site.com` will now also wait on that option. the domain vs second-level domain logic here was previously spotty, and some subdomain stuff wasn't waiting when it was supposed to
* sketched out `DomainSettings` and `DomainStatus` objects to track the settings and basic event history on a per-domain basis in an easily future-extendable way. they don't work yet, but I'm prepping for it
* wrote some unit tests for the new objects
* domain errors are now reported with an event type, in prep for the new objects

### boring code cleanup

* retired my older directory picker dialog in favour of my newer 'quick' select, replacing use in the file import window; move media files; repair file locations; clear orphan files; review services manual export update files; manual import update files; select backup location; restore backup location
* updated my 'quick' directory select call to remember the last directory selected this session (defaulting to install dir for now), and if the caller doesn't have a specific location in mind, to use that last selection as the starting dir of the next dialog open. it also handles cancel results a little nicer
* removed one or two 'is the user in Qt5?' checks with the QtMediaPlayer work. I'm not sure when, but I think I'll purge the rest of these completely in the next month or so, probably at the next 'future build' commit. it is basically time to move on

## [Version 656](https://github.com/hydrusnetwork/hydrus/releases/tag/v656)

### misc

* when you edit an ongoing tag autocomplete input to have or not have a leading hyphen, the results should now switch more reliably between `skirt` and `-skirt`. the logic was patchy here, previously, updating itself on certain unnamespaced text but not namespaced, and I believe in some cases in-construction OR predicates could be negated, but it should now, on all updates, work on all the correct predicates
* all file and directory pickers across the program now no longer realise any symlinks you select. I never knew this was default behaviour, but now, if you tell 'move media files...' or similar to use a symlink, it will result in that dir you select, not the realised endpoint
* if a file storage location involves a symlink, the 'move media files' dialog and related log entries will now say `/some/path (Real path: /other/path)`. if there is a problem determining the path, it will say `/some/path (Real path: Could not determine real path--check log!)`
* the example urls list in the 'edit page parser' dialog now has copy/paste buttons for quicker in and out when you just need to grab some urls to test with etc.. . I will brush up this list object more in future and do duplicate removal and right-click menus and stuff
* when hydrus does a free space check on your temp dir before a big db job, it now recognises the `SQLITE_TMPDIR` environment variable, which overrides and tells SQLite to use a different path, and it will check and talk about this guy instead. if SQLite is indeed redirected with `SQLITE_TMPDIR`, this is now stated in `help->about`
* if duplicates auto-resolution fails to generate visual data for a file, it now prints a message to the log about the bad file hash, considers the file pair not duplicate, and no longer halts the whole system (issue #1950)

### import options overhaul

* I have planned out the overhaul to import options. we will migrate to a system that is similar to the current url-type-based  tag/note import options customisation but for all ways of importing and all import options types. the edit panels will get a strong usability and clarity pass, all gathered in one panel, with favourites/templates for quick load of preferred options, and the import options will be split into more granular types so you can, say, easily set up a specific tag blacklist while keeping default tag parsing rules. the current expected default categories will be global, local import, gallery, subscription, watcher, specific url classes, and the new import options will be: prefetch logic, file filtering, tag filtering, locations, tags, notes, presentation. should be easier to add a 'ratings options' to this sort of thing, too, in future
* I did a load of boring behind the scenes cleanup this week to move this forward. nothing works different, but the shape of things is altering--
* I wrote a new import options container object that will dynamically hold a swiss-cheese template of various options for a particular layer of the options context, and a manager to hold the defaults and serve the appropriate specific import options based on who is asking
* the 'file import options' across the program is converted to 'file import options (legacy)'
* same deal for 'tag import options'
* wrote a 'prefetch import options'
* the hash-check, url-check, and url-neighbour logic is migrated inside a file import options to this new prefetch import options, and all importers and options now interact with the prefetch import options, care-of the file import options. same thing will happen in future for the file filter stuff ('don't allow x filetype' etc...) and the locations stuff ('put it here and archive it'); and on the tag side for blacklist vs tag destination options; before I migrate all those newly decoupled lego blocks up one level to the new container class with, fingers crossed, minimum fuss
* the edit file import options now breaks the prefetch logic out to a new UI box. these options are no longer hidden behind advanced mode, but for this transition period I will now start the box collapsed and have a scary warning label
* now I have thought about this and planned it, I feel fairly good. I think I am 20% done and believe I can keep chipping away like this for a smooth migration, no gigantic changes at any stage

### client api

* the `/add_tags/search_tags` Client API request now delivers a very simple `autocomplete_text` Object that says what actual text the user entered and whether it was inclusive (i.e. started with a hyphen or not). I considered adding some other A/C logic like 'is explicit wildcard' and 'what automatic autocomplete wildcars are being added' to this structure, but that stuff is a little messy so I'll KISS for now
* the unit tests now check this
* Client API version is now 86

### other boring cleanup

* moved file and directory picker buttons out of `QtPorting` and harmonised the 'quick, select an existing dir' routine to `DialogsQuick`
* moved the richer file and directory dialogs out of `QtPorting`

### new domain logic prep

* if the client has access to the library `tldextract`, it now defers to this for generating the 'second level domain' of an URL (or, more strictly, detecting the 'public suffix domain'). this is the `blah.com` style of domain, with no subdomains. at the moment, hydrus naively collapses a `blah.co.uk` to the unhelpful `co.uk` for various domain-management purposes (you may see this under _review session cookies_), which doesn't cause any errors but is ugly and does cause bloated sessions that collect all cookies under this TLD into one bucket and forces everything under the domain to share bandwidth tokens on this false second-level umbrella. this new library navigates this and produces the `blah.co.uk` result as desired
* `help->about` now lists `tldextract` under the 'optional libraries' section
* this code does nothing yet for almost all users. in the near future I will roll the library into the requirements for source users and the future build so we can test for issues. I have written a failsafe to try to not break any logins (anyone who has login cookies in a 'co.uk' style session entry will keep using that bucket after the planned transition), but we'll see if anything else pops up

### future build committed

* This release commits the changes tested with the recent future build. The test went well, and there are no special instructions for the update. Source users are encouraged to rebuild their venvs this week. Update as normal, and you will get--
* - `requests` (networking library) `2.32.4` to `2.32.5`
* - `mpv` (the python wrapper that talks to the dll) `1.0.7` to `1.0.8`
* - `PySide6` (Qt) normal `6.8.3` to `6.9.3`
* - `PySide6` (Qt) test, for source users, `6.9.3` to `6.10.1`

## [Version 655](https://github.com/hydrusnetwork/hydrus/releases/tag/v655)

### misc

* for all the normal page sidebars, the sections above the taglist (e.g. 'search' on a search page, or 'gallery downloader' and 'highlighted query' on a gallery download page) are now collapsible (there's a little up/down arrow button in the corner). if you want to do some taglist work, you can now make it really big. this is just a hacky test though, so let me know how it feels
* the 'eye' icon in the media viewer now has 'always start new media viewers always on top' (which works nice generally) and 'always start new media viewers without titlebar/frame' (which is a little flickery since I schedule it to happen 100ms after window init because of technical gubbins). neither plays very well with start-fullscreen mode. I also reworded the titlebar option logical grammar from 'show titlebar (default on)' to 'hide titlebar/frame (default off)'
* the 'pause network/subs' menu items in the system tray icon are now checkbox items. the ugly 'unpause x' grammar is gone!
* if you do not have a file, the file info lines that appear in the thumbnail flyout menu and the main gui status, which normally say stuff like 'imported 3 days ago' now explicitly say "you do not have this file, (but you did once|but your client has heard a bit about it|and you have never had it)". I hope this will forestall some confusion these advanced media results cause (usually under a 'all known files' search)
* the unhelpful and incorrect 'archived: unknown time' statement no longer appears for non-local files
* if a site delivers `451: Unavailable For Legal Reasons`, the file and gallery download objects now catch this and assign an 'ignored' state with an appropriate note. previously this was counting as an ugly uncaught error and causing subs to break and so on (this caused my 'do not use NGUGs here' 'edit subscription' warning label last week). if you have been hit by this (seems like danbooru is doing it?), I don't know if it is because of your region or certain queries (e.g. 'do not post' artists); let me know how the workflow is with these results now being ignored--maybe we want this to be an outright errorthat will auto-pause subs and such, just with the now-nicer error description? I've been thinking about making subs cleverer about region-based captcha blocks, recognising that this is a temporary block that should cause hydrus to stop talking to the domain entirely, but not considering it an error _per se_ and backing out of the current job non-destructively so it can try resuming where it left off again later, so if this is part of that, we'll want to throw it in the mix

### Client API

* with thanks to a user for the skeleton, I fleshed out and added `/manage_pages/get_media_viewers` to the Client API. this thing fetches all the current open media viewers, tells you an id and type for each, and says what media is currently in view. this also clears issue #1583
* wrote a (bad) unit test for this and some documentation
* Client API version is now 84

### Client API deprecation

* I am formalising my Client API deprecation schedule since I have been procrastinating on this cleanup yet don't want to suddenly delete something mysteriously two years after the fact
* if you send `hide_service_keys_tags=false` to a `file_metadata` Client API call, the user now gets a `FutureWarning` deprecation log entry. the behaviour this parameter supports will be deleted on v668 (three months from now)
* same for the `set_user_agent` command. you'll get a `FutureWarning` if a script calls it, and it will be deleted in v668
* `hide_x=true` is ugly logic, so we'll go with `use_deprecated_x=false` default going forward
* I am going to add a `use_deprecated_services_structure=false` default to the `services` call in v668, to hide the old service structure. it will similarly get a warning and a three month timeout, to be deleted in v681

### boring file storage cleanup

* an early 'umbrella' experiment for dynamic file storage prefix-length is removed and some validity checking is simplified
* in prep for the move to a storage system with three-character prefix (4096 folders), moved a bunch of prefix-handling to a central location and made it length-agnostic
* KISSed some of this code. it is still a bit of a mess though tbh
* wrote a method to 'granularise' a file storage structure, moving a base location from subfolders in the form '/f83' to '/f83/0' - '/f83/f', with file migration and handling weird files and stuff. when we move to three-character storage, we'll not only be granularising our main storage, but we'll want to do this one-time manually on our backups as well

### other boring stuff

* the 'edit default duplicate metadata merge options' button in the duplicates page is shuffled down to the 'duplicate filter' box
* fixed a quiet layout sizing warning in the petition processing page when the checkboxlists have no content
* added a note to 'help my db is broke.txt' about a clone crashing

### future build

* I am making another future build this week. This is a special build with new libraries that I would like advanced users to test out so I know they are safe to fold into the normal release.
* in the release post, I will link to this alternate build. if you are experienced and would like to help me, please check it out
* special notes for this time: nothing crazy, we'll see if the new Qt kicks up a fuss anywhere strange
* the specific changes this week are--
* `requests` `2.32.4` to `2.32.5`
* `mpv` (the python wrapper that talks to the dll) `1.0.7` to `1.0.8`
* `PySide6` (Qt) normal `6.8.3` to `6.9.3`
* `PySide6` (Qt) test `6.9.3` to `6.10.1`

## [Version 654](https://github.com/hydrusnetwork/hydrus/releases/tag/v654)

### command palette

* reorganised the command palette options panel and updated how the character search threshold works. you can now say 'show all my x initially' for a particular search result type and then set a character limit for the general searches. the default and min value for the character search threshold is now 1

### slideshow

* the slideshow menu in the media viewer has been shuffled a bit to tuck everything together
* the slideshow menu now also appears in the top hover of the normal 'browser' media viewer, in a new icon button beside the 'move randomly' button
* the sildeshow menu now has a 'slideshows move randomly' option. this thing is a global setting, mostly a test. let me know how it works out

### misc

* the manage subscription dialog now nags you with red text if you set a downloader that appears to fetch from multiple sites (i.e. it is an NGUG that has multiple domains in its example urls). although it sounds temptingly convenient to set up a sub with a multi-site NGUG, they don't work so great like this, so the panel now says so and tells you what to do instead
* added a `When finishing archive/delete filtering, delay activation of multiple deletion choice buttons` checkbox, default True, to `options->files and trash`, so you can now disable the 1.2 second delay on the delete/commit buttons when there are multiple deletion choices
* made new svg icons for 'image', (which turns up when hydrus can't find a thumb for an image file), 'images' which turns up in the command palette as a 'media' proxy for media menu results, and the new 'slideshow' icon button. I like how these look at high res, but the smaller ones look bleh tbh. we'll have a review of all my new svgs when I finally add icon button sizing options and boost the default up a bit
* `options->media viewer` now has split up mouse and seek bar settings. the seek bar panel has a new `Seek bar full-height pop-in requires window focus` checkbox, which is now default **True**
* fixed svg resolution fetching (and probably all sorts of related svg gubbins) in PyQt6 (this is an alternate version of Qt some source users may be running)

### boring and cleanup

* overhauled how the command palette does some search string handling and cleaned up a couple of logic things like whitespace no longer counts as a new char, etc..
* the code behind the slideshow is all cleaner and decoupled application command stuff
* I went through and renamed some 'scanbar' labels to the more canonical 'seek bar'
* the 'eye' icon button in the media viewer top hover is recollected into window/hovers/rendering submenu categories
* fixed the vacuum command to no longer check the temp dir for free space in the lower-db call--the newer 'vacuum into' command we use no longer needs a temp copy
* might have fixed a bad 'Go!' confirmation dialog string generation in `migrate tags` that hits users for whom Mercury is in retrograde
* improved the error handling for when my new async subprocess reader tries to read from a process that terminates early
* fixed some unit test 'call after' job scheduling stuff with the same anti-deadlock handling I added to the main client a while ago

### admin and docs

* created a hydrus_dev@proton.me email address and added it to all my contact lists. please feel free to email me there if you prefer--I'll check it as often as my gmail
* to stop new users missing it, the 'Wayland' warning box in the Linux install and source help now starts uncollapsed
* added a note about `libxkbcommon` for X11 support on Fedora too
* wrote a 'help I had a file identifier missing error.txt' document for the db dir to handle the 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa34bf0b9abf7683e3955781212d0d1899' emergency hash-recovery situation

## [Version 653](https://github.com/hydrusnetwork/hydrus/releases/tag/v653)

### misc

* I hacked a simple date range (x axis) into the file history chart. it is clunky, but if you want to zoom in on one year, it'll work. this persists through search changes, and there's a 'refit x axis' button to recalc for the current data in view
* reworked the naming and layout of the checkbox list in `options->media viewer hovers`
* `options->media viewer hovers` and the top hover eye icon get a new `Hover-window pop-in requires window focus`, default on
* `options->media viewer hovers` and the top hover eye icon get a new `Pop-in notes (right) hover window on mouseover`, default on, to handle the notes hover window
* also added the new 'pin the duplicates filter hover window' checkbox to these guys (it is also still in the cog menu of the hover itself)
* the `When finishing filtering, always delete from all possible domains` option is now simpler and more reliable. it had some old logic from the days when archive/delete allowed trashed files and sometimes not activate if there _were_ multiple domains (#1926)
* the archive/delete commit dialog when the above option is _off_ is simplified and, if there _are_ multiple domains to delete from, always puts 'combined local file domains', which now has a clearer label, at the top
* `system:duration` parsing now supports hours and minutes, and some funky stuff like '26000ms' works better (#1924)
* the hydrus network engine has two new global http headers: `Accept: image/jpeg,image/png,image/*;q=0.9,*/*;q=0.8`, which preferences jpegs and pngs over webp, and `Cache-Control: no-transform`, which asks CDNs not to deliver "optimised" versions of files (often not honoured, though). all users who don't have a global header with those names already in place will get them on update. if you prefer something else, hit `network->data->manage http headers` to edit!
* fixed the 'refresh all pages on current page of pages' shortcut action, which was accidentally nullified by a recent rewrite
* fixed an issue with clientside services not deleting properly when editing services on a server and deleting more than one service at once

### boring cleanup

* the file history chart can now take new data and will regen its internal series and axes and stuff. previously I swapped in a whole new chart widget on every new search. also cleaned up the layout of the wider panel here
* all `Typing.Optional` across the program (~300 instances I think) are replaced with `x | None`, which is python 3.10+ only. turns out we already had some of these, so no big worries, I hope, about lingering 3.9 users
* all `Typing.Union` across the program (~50 instances) is similarly replaced
* clarified some 'this message only shows one time per program boot' messages

## [Version 652](https://github.com/hydrusnetwork/hydrus/releases/tag/v652)

### misc

* the advanced rating system predicate (the new one that lets you do all/any/only) is now fully parsable, so you can type `system:any rating rated`, and it should work. if you need to stack up multiple specific rating services, split them by commas for something like `system:only rating service 1, rating service 2 (amongst like/dislike ratings) rated`. against all probability, I think I support everything here
* `options->command palette` now lets you set a number of characters to type before any results come in. default is 0
* fixed some selection issues with the command palette. I just cleaned up the select logic a bunch and fixed things like: if you select something with arrow keys and then click on the text box and start selecting again, the old selected guy is now properly deselected; scrolling to the topmost item via a wraparound or home now ensures any non-selectable title is in view; page up from text input now jumps up a page from bottom rather than just selecting the bottommost item; page up/down events that land on a title now spill over to the next selectable item and are a bit faster if you have like 500 results in the background
* I cleared up some initial UI lag when when you highlight a very large downloader or watcher (say 5,000+ files) with presentation options that care about inbox status (requiring a db hit). the db hit now happens on the worker thread, not the Qt setup phase. the popup window showing progress now appears if this job takes longer than two seconds for the whole thing (previously three seconds for the results building step). let me know how it feels
* when hydrus calls other programs and wants text back, it now forgives invalid utf-8 with the replacement character �. previously it strictly raised an error, and this broke imports of mp4s and so on that had damaged utf-8 in their metadata description (which ffmpeg faithfully passes along) etc..

### default downloaders

* updated the danbooru gallery parser to not get a load of gumpf links if you have 'show scores' set on in your account/cookies and sync that to hydrus

### boring cleanup

* all my custom `paintEvents` across the program now have completely safe exception handling and unified reporting in all cases. if there is an exception, the user is notified once per boot about what is happening, why it is important (unhandled exceptions in paint events are crash-city), and to please send the trace on to me
* some 'media result' tag access is now a touch more thread-safe. this effects the client api `add_tags` and `file_metadata` calls. I'm not sure if this will solve some `add_tags` crashes we've seen, but it is the only candidate I can see
* I've cleaned up the system predicate parsing system a bit. this thing started out as a clever neat routine, and I and others have hacked at it so many times for new preds that it is a mess. I've worked on making the pipeline less brittle, with a common workspace shared by all methods rather than fiddly params. much of the old stuff is still in there, but I've been able to undo some hacks and feel overall good about the direction. I've slowly been moving my basic system preds to a new unified 'numbertest' object, and the next step here is to integrate this into the parsing so we can finally specify absolute and percentage uncertainty, which atm is locked at +/-15%
* the hacks cleaned up are: an uppercase/lowercase thing for url class and regex parsing; a non-consuming operator thing to make non-sha256 system:hash preds parse correct; and some value/operator juggling to handle the conversion to `taller than|=|wider than 1:1` for 'ratio is portrait/square/landscape'
* fixed an issue with the newer ffmpeg error handling when your ffmpeg gives no stderr on a file parse
* cleaned up some ffmpeg error exception handling to be nicer to linters
* removed some ancient python 3.6 and 3.7 compatibility code in the subprocess stuff
* when the initial url parser fails to figure out what is going on with an incoming URL, the exception now states the URL text that caused the failure
* fixed up some client api unit tests that were doing dodgy media result prep
* fixed a checker options unit test that I accidentally broke last week with a last-minute change
* updated the versions of the github actions in the runner workflows to be ready for Node24. I think that migration triggers on Github around April 2026, so we are way early. it looks like some of the docker stuff isn't 24 compat yet, so there may be another round of this early next year
* deleted an old duplicate of the docker.yml workflow in 'build_files' that had fallen behind the master
