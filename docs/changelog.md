---
title: Changelog
---

# changelog

!!! note
    This is the new changelog, only the most recent builds. For all versions, see the [old changelog](old_changelog.html).

## [Version 668](https://github.com/hydrusnetwork/hydrus/releases/tag/v668)

### mistakes

* HOTFIX: I made a v667a last week to fix a regression where subscription queries with outstanding file queues were downloading those files even if the individual query was paused. The 'finish jobs even if you are DEAD' check change was too lenient first time around. Sorry for the trouble!
* HOTFIX 2: I then made a v667b since the first one didn't get everything. individually paused queries that had a due-to-work 'do gallery search' check were 100% CPUing the subscription daemon. I fixed it in the same way as the file check and added additional guards for other 'cannot work' error states and calls. the run logic in individual subscription queries was not clean, and a little change revealed the faults. I regret it and apologise to those hit with inconvenience and frustration here
* I have added unit tests for query pause, DEAD, 'has outstanding file work', 'has a due sync', 'is checking now', and 'is expecting to work in the future' states. this specific error will not happen again

### new media viewer shortcuts

* thanks to a user, we have some more window and media viewer options, including some clever debug stuff for those who get annoying 'rescued from offscreen' behaviour--
* you can now map 'always on top: on, off, flip on/off' in the media viewer's shortcuts set
* you can now map 'frameless: flip on/off' in the media viewer's shortcuts set
* in `options->gui`, you can now control whether an offscreen-rescued window gets the (default 40, 40) top-left safety padding
* you can also only remove the safety padding only when doing the 'resize to media' job for the media viewer
* and you can set the fuzzy 40px amount to something else

### misc

* renamed a handful of shortcuts action labels from 'verb thing' to 'thing: verb' for better sorting
* ADVANCED: added settings to `options->importing` to expose the until-now hardcoded bottlenecks on how many particular import queues can run at once (e.g. 'gallery files'). this is the thing that handles a 'pending' vs 'working' state in import page UI. it has an 'ADVANCED' warning label

### client api

* I chickened out of removing/default-off-ing some deprecated calls in the Client API as I had planned. it is not the season for causing fresh headaches, and nothing will break today
* since we'll indefinitely live with some mess, I decided to make a quick update to `The Services Object`. I hate that I made the `service_key` the key of the Objects involved here since in some JSON libraries it is a real pain to navigate. thus, anywhere I add the old Services Object under `services`, I also now add `services_v2`, which has the services as a list. same format except they now have a `service_key` field. I will not remove `services` any time soon, so no need to change anything you already have
* the Client API docs now refer to the `services_v2` structure so that new guys and projects are steered towards something non-weird
* I concede this is spammy and inelegant, but it resolves and KISSes an early mistake. the cruft is intensifying to the point where we may not be able to contain it, but why contain it? let it spill over into the add-ons and the MCPs, let the scripts pile up in the streets. in the end, they will beg us for a Rust conversion
* Client API version is now 90

### db dir build stuff

* I reworked how the 'help my db is broke.txt' help files (and for Windows, 'sqlite3.exe') end up in a db dir. these files now primarily live in `static/db_files`. any .txt files in there are mirrored into a new database folder on db creation. I strongly considered updating these files on any update, but I went back on it, preferring not to auto-fiddle with the db dir overmuch--I'll make a manual command for it
* a `CONTENT_DB_PATH` variable that had caused some hassle for patched source installs like the AUR release is now gone
* I will be removing the 'db' dir from the main repo in the future. I'll do more planning and testing around .gitignore just to be certain doing that will be smooth. we obviously want this to be absolutely failsafe
* I also expect to eventually migrate these .txt files to proper .md help files, with formatting and everything, at which point this will scale back significantly, probably just to a single .txt that says 'if everything is busted, go here in the help'
* I am finally ready to plan moving the default location of the db outside of the install dir. we'll have a first-start wizard to select/find location and a small file in your user folder to track available profiles or whatever if the client is run without `-d`, or something along those lines. this transition will take careful planning, so your general thoughts are appreciated

### boring import options overhaul

* every single importer across the program now converts the legacy file, tag, and note import options to the new 'import options container' before passing it to the main file import object. the whole file import object pipeline below the importer level is now converted to the new options structure!
* cleared 'file import options' out of some of the parsing pipeline where it wasn't used any more. this seems to have cleared all import options out of the gallery pipeline
* wrote out a modern 'set up a default set of options' call following the existing loud/quiet dichotomy and 'post urls get tags; watchers don't' ruleset
* my in-testing 'import options' panel gets a 'reset to defaults' button that will reset the main defaults, all the custom url classes, or the favourites/templates
* fiddled with some of the wording in this UI. defaulting the defaults back to 'use defaults' etc.. can make for unclear tooltips
* fleshed out the container object to offer up different import options in a more convenient and nicely typed way in the real pipelines
* in the file import, the 'should fetch metadata even if url/hash recognised...' advanced setting is now strictly _any_ metadata. previously this checkbox would only kick in if you actually had some tags set up to parse and import somewhere. after the migration, these checkboxes will be moving to an independant 'prefetch import options' guy, away from tags completely
* certain non-already-in-db imports that have no tags or notes are now one db hit cheaper
* certain already-in-db imports are now one db hit cheaper

### other boring stuff

* fixed a possible count bug in the thread slot system where in certain late-initialisation systems it could undercount the number of active jobs in a slot
* the 'prefer system ffmpeg' setting no longer needs a client restart. the call that discerns the ffmpeg path to use is also a little more sensible and failsafe, and cycling the options dialog now resets some state so you can put an ffmpeg in your hydrus 'bin' folder, ok the options, and it'll redo the 'is there one there?' test
* updated `crash.log` to `/db/hydrus_crash.log` in `.gitignore` file

## [Version 667](https://github.com/hydrusnetwork/hydrus/releases/tag/v667)

### misc

* fixed an issue with subs where a sub with all DEAD queries was considered 'no work remaining', and thus subs in that situation with nonetheless outstanding file downloads would not clear those outstanding file downloads if the work spilled over to future sub runs
* all thumbnail pair lists (which are in the duplicates auto-resolution UI) now have a menu that says 'show x rows in a new page' so can you can review things in more detail. let me know if this swallows deleted thumbnails anywhere
* the file storage granularisation system can now handle cross-filesystem granularisation. this can happen on 3-to-2 when some of the 3-granular subfolders have been migrated to a second location and need to be collected in a central source that might be on a different partition. it seems to also occur in 2-to-3 when the filesystem has overlapping subfolder orphans from a previous borked migration or similar and things are tidied as part of the regranularisation. the previous very fast atomic 'file rename' was raising an error here; now I do some efficient device checking of subfolders and move to a 'copy2+unlink' combo instead when the device differs
* the granularisation panel now warns those with weird symlinked storage to stay away
* the routine that counts up the durations of a gif's frames and the hydrus native renderer now fall back to best-guess defaults if A) the file changes resolution mid-parse or B) any frame appears to have a width or height bigger than 16k pixels. we encountered a malformed gif this week that went from 640x480 to a fake 28579x93263 and caused a memory explosion. should handle this situation better now
* continuing the 'clean up PIL Images better' work, native animation renders that error out are now explicitly closed before reinitialisation
* thanks to a user, the 'Paper_Dark' QSS files have fixed, visible `▲/▼` button labels. relatedly, the objectNames I added for this guy last week are renamed to `HydrusCollapseArrowUp/Down`. they were `Expanded/Collapsed`, but since the arrows reverse depending on an upwards or downwards expand, we realised we'd want something more specific to the actual label being shown if we ever wanted custom icons/labels

### sidecars

* sidecars gets an easy one-click template that covers simple stuff. the 'edit metadata migration routers' dialog, which the main guy in sidecar editing, now has a star button. when exporting to sidecars, it offers an 'easy one-click JSON that covers the basics' template that spams out definitions for a single 'filename.jpg.json' JSON sidecar that gets your notes, urls, tags for each tag service by storage (no siblings/parents) and display (with siblings/parents), and timestamps for archived time, main import time, and media/preview viewer 'last viewed time'. when importing from sidecars, the buton offers the same 'easy one-click' option to eat from a JSON using the same format and will line up any tag services that have the same service name
* if you try to export notes to a .txt sidecar using `\n` as the separator, or conversely import notes from a `\n` .txt sidecar, the 'edit sidecar stuff' dialog now moans at you on ok, asking if you are totally sure that is correct. since notes often _include_ newlines, something like `||||` is more appropriate
* when dragging and dropping individual files onto the client, it can now give a pretty 'sidecar' result when you drop individual files. this only worked if you dropped directories previously, with individual file drops giving 'PROBLEM: filetype unsupported' for the sidecars. this is an aesthetic change only; it doesn't matter that sidecars are not parsed ok at this step, but it is nice to have the correct 'won't try to import' label
* in the 'add metadata before we import' sub-dialog of the manual file import, the 'sidecars' list now shows better metadata context around the sidecar content preview. the 'notes' now compresses multiple notes better, with a total count and elided preview; the 'tags' now says to which tag service they are going; the 'URLs' now says how many URLs and elides better; the 'timestamp' now converts to a nice datestring and says what the destination is for that time (previously it just said the UNIX timestamp flat wew)

### Client API and setting archived time

* for sidecars and the Client API, if you push an archived time on a file in the inbox, the file is now auto-archived! the UI and Client API docs now mention this
* previously, the data was (buggily) recorded but generally swallowed and not reported anywhere
* the Client API 'file metadata' call now gives a `time_archived` if the file is not in the inbox and there is a known timestamp
* sidecar routers, when harvesting timestamps to send to a sidecar file, will no longer suck an orphaned archive timestamp from a file that is in the inbox
* Client API version is now 89

### QtMediaPlayer transparency

* the QtMediaPlayer should now support transparency properly! previously, if you put up an animated gif with transparency, the transparent areas would be black with ugly fuzzy edges. now it does a checkerboard or greenscreen using the same settings as a static image. on some files there is still fuzz, but most of the time it looks great
* the QtMediaPlayer should also show the normal background colour while it waits for a non-transparent media to load. it probably flashed black before, so should cut down on some load flicker
* the normal static image checkerboard and greenscreen transparency uses the same, updated tech here. rather than drawing a bunch of boxes, we now have a textured pixmap brush, and in fact in all cases we just set a brush and do an eraseRect, nice and clean. Qt is great
* the 'show transparency and checkerboard in duplicate filter' setting in `duplicates` is now its own thing and applies independently to the one in `media playback`. previously it had some whack 'only applies if the media playback guy is unchecked', which is the kind of thing you can convince yourself is useful and technically correct but violates KISS

### ingesting serialised objects

* the 'import downloaders' panel now accepts drag-and-drop or pasted JSON files
* added a `help->debug->what is this object?` debug review panel to figure out mysterious bits of json or png or whatever

### boring stuff

* improved error handling for setting QtMediaPlayer null audio device on media load
* improved how 'show menu' events are handled, Qt-side, for the: colour picker widget; preview viewer; navigable media viewer; taglist
* cleaned up some ugly menu generation/show for the main thumbnail grid
* decoupled the 'import downloaders' serialised object ingestion routine and brushed it up a bit with nicer error reporting and so on
* all serialisable objects can now describe themselves with regards to the serialisation system, with special hooks for named objects and the special list, dict, and bytes dict
* fixed up several places that do a fast 'is it a jpeg/png' mime check, which was accidentally skipping the png side and doing the slower check
* fixed a bad layout flag in the 'select from a list of checkboxes now mate' dialog
* fixed some close-curly-brace typos in the example Client API Services Object JSON

## [☠⛤ Version 666 ⛤☠](https://github.com/hydrusnetwork/hydrus/releases/tag/v666)

### misc

* when you create a new subscription with 'add' button, it now asks you for the downloader up-front. this was easy to forget to set, previously; now you can't miss it
* the problem where media could sometimes not receive any content updates (rating changes, new tags, archive state, whatever) after a backup, lock, vacuum, or certain database transaction error recovery until a page was refreshed is fixed. a cache that the in-session pages refer to was held by a database module being reinitialised through these processes and thus, after cache reset, the connection to send the update signal on media changes wasn't getting through to UI
* added `^(?!...$).+$` to the regex input menu's quick selections for 'anything except this exact phrase'. I have to search stackexchange to figure this out every time I need it; now it is just there. also fixed a formatting typo in this menu for the 'any of these' entry

### media players

* improved the guard around the QtMultimedia module for those Qts where it is not available or otherwise fails to import
* if your options say to show something with QtMediaPlayer but the module isn't available, it now falls back to an 'open externally' button and does a little popup; the same handling for missing mpv
* improved the popup text when you boot `help->about` with an unusual module load error to report
* rejiggered the `help->about` 'Optional Libraries' list a little and moved mpv over there
* added another mpv 'null' audio error text, 'Could not open device', to our new cascade of 'calm down, but set the null audio device now' error handling
* added a `KDE and QtMediaPlayer` note to the 'installing - linux' help. installing `mit-krb5` may help

### qss

* the e621, e621_redux, and Paper_Dark qss stylesheets get 'built_release' alternates to handle the new 'lib' directory structure of the built release
* updated the guidance on external asset paths in `options->style`

### import options test panel

* booting the options dialog in 'advanced mode' now adds a 'PREVIEW: import options' panel. this is the new central place that we'll be customising import options after my rewrite here is done
* this panel saves nothing; it is only for playing around with. it takes your current settings and migrates them to the new system as the expected pending migration will
* I am happy with the technical side of things here, but this thing is complicated and I would like to throw advanced users in the deep end and get feedback on where the roughest parts are. I'll sand down the roughest corners with better UI and consider it all as I revise the help docs
* april fools this year is yet more hellish UI from hydev

### removing the default downloaders

* a fresh hydrus client database no longer starts with any downloader definitions! I am cleaning some legacy things and making the program more neutral from the start. users will now add whichever downloaders they want from third-party sources like the user-run downloader repo. not an april fools--sorry for the trouble!
* existing users keep what they have; this only affects new installs
* this also frees me from the maintenance burden, which I was failing at. several of the defaults were breaking and I was not keeping up with the issues
* so, the defaults are removed from the `static` dir and there are no 'add from defaults' buttons in the edit panels. the UI now supports and starts with a 'null' state of 'no downloader selected' everywhere
* users without any downloaders are pointed to the `network->downloaders` menu and the user-run repository
* I updated the help documentation all over regarding this change. it may need a revisit to make new-user onboarding smoother

### import options boring work

* added a 'paste-fill' paste type to the options panel, for filling in gaps without overwriting
* wrote paste buttons for individual options panels and the import options container panel
* wrote copy buttons for the container panel
* fleshed out the valueChanged signals for all the new options panels: prefetch; file filtering; tag filtering; locations; tags; notes; presentation
* wrote a favourites button and adjusted the UI to handle it in the appropriate locations
* wrote some basic default favourites
* polished the UI, swapping to icon buttons, bunch of stuff
* fixed some little logic and label bugs in the new import options stuff

### little stuff and cleanup

* the little `▲/▼` button you see across the program on static boxes and the popup toaster now uses a special shared class that uses nicer Qt tech to signal things and sets two new object names for QSS devs to hook into: `HydrusCollapseArrowCollapsed` and `HydrusCollapseArrowExpanded`. note that these guys use reversed labels depending on whether they expand up or down (I just realised this, working on it now), so if you want to put a new label or icon in, I think we might want to do some more here. let me know how it goes
* I think I fixed an issue where the 'hey your page is super mega tall, careful' message was showing more than once if the session includes multiple pages in this state
* updated some new async ui code, the stuff that does new unified callBack/errBack panel restoration after job reset, so that it better handles the error of its parent window being closed early, and a program shutdown call. this was causing some harmless error spam in some things like a delayed subscription popup files button press/dismiss
* fixed a stupid error in the updated Linux .desktop file deployment script that broke the Icon with quotes around the path
* made the various widgets, options, and importers ok with having no downloaders available. the first time a GUG comes in via the drag and drop system, it is set as the default
* amidst the downloader work, cleaned up how subscriptions do some edit panel `Set` stuff, removing some legacy jank
* fixed up an old hardcoded 'downloader updated' callable with a nicer Qt Signal
* improved the error messages around invalid/missing/null GUGs at different stages
* I also removed some legacy downloader db update code that would have fallen to bitrot here
* fixed a couple `finally/return` syntax issues
* 'manage login scripts' now has some red text up top warning that it is an ancient system that does not work well
* updated the 'adding new downloaders' help to be more clear about what is going on with the png files. it now has an example png for artbooru.com
* updated a bunch of ancient screenshots in the help, particularly the parsing system
* fixed duplicated 'index to fetch' label in html parsing formula panel
* replaced some whackadoodle ListBook fixed sizing with a proper `sizeHint` and some live rowheight checking and framewidth correction
* cleaned up some subscription unit tests
* the media result cache is now a singleton instance that persists through a database restart, and the unit tests now do some careful clearing on test database resetting here
* fixed a missing definition typo in the filetype labels

## [Version 665](https://github.com/hydrusnetwork/hydrus/releases/tag/v665)

### misc

* fixed an issue where a duplicates page would not re-enable the 'launch the filter' button sometimes when it previously had a count of 0 but got a pair-discovery update in the background that added new pairs (issue #1988)
* the 'help: random 403 errors' entry is now moved down in the 'retry' buttonlist. it will disappear in a few weeks, leaving just the `network->downloaders` menu item, once people hitting this menu have had more chance to see it
* fixed an issue where if you selected some files with a subset of trash and then said 'move/copy n files to blah local file domain', it would try and move the trashed files and throw an error. it now filters those files out of the actual operation as you'd expect
* fixed an issue in numerical rating rendering after deleting a numerical rating service (bad error handling on the missing service)
* added a section to the 'contact' help page about how to send broken files to hydev (zipping them up explanation etc..)
* updated the `io.github.hydrusnetwork.hydrus.desktop` file with easy mode help comments on how to edit things and added `StartupWMClass` to help taskbar grouping

### more audio device stuff

* applying the options dialog now updates all open mpv players to use the specified audio device
* applying the options dialog now updates all open QtMediaPlayers to use the specified audio device
* the `ao/xxxxxx: There are no playback devices available` mpv error, which until now has sparked the 'hey things are looking unstable with this file, so unloading it' response, now triggers a new 'hey, set all mpv windows to `null` audio device'. if you get this stuff when you unplug your headphones or something, let me know how it goes
* when a new QtMediaPlayer initialises, if the desired audio device is invalid, it falls back to auto. if the auto device is invalid, it resets to null
* new DEBUG checkboxes in `options->media playback` allow you to auto-set mpv or the QtMediaPlayer to 'null' audio device when playing silent media like animated gifs. I know we've had some issues around this over the years with mpv on Linux in particular, so let's see how it goes. this used to be default behaviour for the QtMediaPlayer btw; now it isn't

### some boring cleanup

* improved how media objects determine if they are in 'combined local file domains'
* a database routine used in repository sync and 'are we mostly caught up to this repo?' that fetches missing update hashes is now significantly faster
* the QtMediaPlayer no longer leaves the video output disconnected until the first non-audio file is loaded. things are more KISS
* the mpv and QtMediaPlayers recognise better their current audio device and can trigger update calls only on changes
* cleaned up some more QtMediaPlayer output setting generally
* updated some critical error text when trying to boot into a database that was created--and failed to initialise--on the last program boot
* removed some OpenRaster debug statements

### removed Qt5 gubbins

* Qt5 (which for us means PySide2 or PyQt5) is well behind us now, so any lingering support is just getting in the way. I removed it all this week. if you are struggling on a hyperpatched Win7 machine, forgive me but it is time to move to Linux
* removed Qt5 initialisation code
* removed debug code that tests for Qt5 support
* removed old thumbnail UI scaling Qt5 hack
* removed Qt5 stylesheet hacks
* removed Qt5 media panel swap hacks
* removed About Window Qt5 stuff
* removed an old Qt5 qtpy init hack
* removed Qt5 patches for mouse and drop events
* removed Qt5 QPDF check
* removed Qt5 QKeySequence conversion

### nicer PIL memory cleanup

* PIL images are now closed promptly (freeing up memory better and faster) in more locations: the visual tuning suite; jpeg quality estimation; icc profile inspection; embedded metadata inspection; exif inspection; decompression bomb testing; 'show file metadata' window; import metadata gen; icc profile inspection on load; on forced PIL loads that error out on conversion to numpy; on another standard method to load images; variable frame duration fetching, 'get number of times to play animation'; 'animation has valid duration'; serialisable object import; ugoira rendering; ugoira API rendering; ugoira property fetch; ugoira json property fetch; Ugoira thumb gen; PSD rendering; PSD thumb gen; the native PIL animation renderer; on EXIF rotation conversion; some weird dequantization; resolution fetch; when some thumbnail stuff errors out; some animation property fetch; OpenXML thumbnail gen; Paint.NET thumb gen; Krita thumb gen; Krita rendering; openraster thumb gen; openraster rendering
* I went overkill here and yet there are still some gaps. I got all the file loads though, I think, which is the main stuff here that I think was lagging. some of it is also a little ugly. we'll see if this improves some lazy memory cleanup during heavy import. if it helps, I may revisit to clean up

### import options overhaul

* wrote migration code that takes the old file/tag/note import options and produces a new populated `ImportOptionsContainer`
* updated the prefetch import options to track the 'fetch metadata even...' checkboxes, although they will do nothing until migration
* updated 'note import options' to a legacy object that can deliver a trivially shucked 'note import options' that has no 'is default' properly and works in the new system. the edit notes dialog, Client API add-notes call, duplicate content merge options, notes sidecar exporter, and unit tests now use the new object
* wrote an edit panel for the new note import options
* the legacy note import options now holds its shucked version inside it, now only taking responsibility for the 'is default' property otherwise, and all import contexts now consult the new object for work
* juggled around my options stack preference again for simplicity and added 'import folder' and 'client api' options import contexts
* brushed up the UI significantly with new labels, better options summaries, better help, a KISSer workflow that filters out overengineered options by default, a little description label for each import type, and another for each options type
* made the stack description and display clearer and added it to the url class section
* fixed some default options display
* brushed up all the import options summary statements and rearranged them all into single-line
* updated some tag filter label grammar. in some cases it was saying 'tags taken: allowing all tags', which comes from internal permissions language, when just a 'tags taken: all tags' was a better fit

## [Version 664](https://github.com/hydrusnetwork/hydrus/releases/tag/v664)

### misc

* the media 'delete' menu is no longer a flyout if there is only one deletion option (you should see 'delete from my files' more often)
* the preview viewer now has the same style of delete menu as the canvas and thumbnail
* the system tray options are no longer disabled on non-advanced non-Windows. this stuff works better these days

### audio devices and tracks

* you can now select the output audio device for QtMediaPlayers under `options->media playback`. default is 'default' (issue #1985)
* there's also a "DEBUG: null" choice to say 'never load any audio output device to QtMediaPlayer'. I know we've had some users who have had trouble with this
* I then did the same for mpv. it works a little different, so you hit a button to fetch the available options and then select from there, or type in manually if you know otherwise. similarly, you can select a 'DEBUG: null' option
* QtMediaPlayers now show their audio tracks in the player right-click menu. it says title, language, and codec, depending on what is available. you can select another track and it changes instantly!
* QtMediaPlayers also now show their video track(s)! I added the same 'switch video track' call as the audio stuff. if anyone has a multi-video-track example vid, I'd love to see it for my testing purposes, but the audio side was a dream so I assume it just werkz
* some this stuff is very slightly hacky, so let me know how this works for you

### file import object inheritance cleanup

* _tl;dr: some downloaders save modified time better_
* when a gallery parse or a file post parse creates multiple child file import objects, I have cleaned up how the parent gives the children data--
* source time is now only propagated if the parent source time is A) sensible and B) the child doesn't already have an older timestamp. all instances of file import object source-time-setting now follow this rule, which is how modified times are generally updated elsewhere in hydrus. 'older is generally more useful and trustworthy, unless it is new year's day 1970 etc..' also, file import objects now clip to thirty seconds ago when given a timestamp from the future (happens with timezone fun sometimes). thanks, particularly, to the user who identified and chased this down (issue #1984)
* referral url is similarly now propagated more softly; only inherited if it isn't set beforehand (was previously a forced overwrite in all cases. not sure it actually matters, but it might in future)

### some boring cleanup

* some critical image rendering sections now clean up their memory quickly and explicitly rather than waiting for the garbage collector to handle it later. more to come here in future
* cleaned up how `AsyncQtJob`s do UI restoration after an error, harmonising how the callback and errback restore the UI
* decoupled how some exception stuff is caught and processed and rendered for the user, and fixed some error-reporting pathways that were not rendering nicely

### boring import options overhaul

* I juggled some more pending import options stuff around, giving the wilder stuff a KISS pass
* wrote a panel to handle editing the new defaults. I simplified things a good bit and moved it all to the options dialog. it is hidden for now but I feel fairly good about it all
* filled in a bunch of holes and fixed some display bugs as I stitched it all together
* improved how import options and their containers present for network vs local imports
* got the import options editing dialog to remember the last selected options type
* I've now got to write some favourites UI, polish this all, write some migration tech, and then update the import pipeline to handle it all. feels doable

## [Version 663](https://github.com/hydrusnetwork/hydrus/releases/tag/v663)

### misc

* the `hide and anchor mouse cursor during media viewer drags` setting under `options->media viewer` is now split into the 'hide' and 'anchor' parts, to add flexibility for trickier situations. some window managers aren't happy about mouse warping. the hide logic also now kicks in faster and sticks better
* added checkboxes to `options->files and trash` to control whether trash maintenance and then deferred file delete can happen in 'normal' time
* when you ok the 'manage tags' dialog, the commit to db now occurs in a thread and will no longer block the UI. if the job looks big or otherwise takes longer than a second, you'll get a progress popup, which is now cancellable. let me know how this feels on something big like the PTR (issue #1980)
* a variety of videos that have silent audio channels were registered incorrectly in the database as 'unknown silence' and were not returning with `system:no audio` searches. the typo in the file parsing code that caused this is fixed, and all affected videos will be queued for a rescan on update to v663 (issue #1977)
* fixed a recent typo that was causing the 'retry 403/404/blacklisted' choices to instead retry all ignored. sorry!

### client api

* added a link to `HydrusTools` at https://github.com/GiovanH/HydrusTools to the Client API help page. this is a toolset for a variety of metadata management and organisation tasks, actively being worked on

### chardet build issue

* changed `chardet>=3.0.4` to `chardet>=3.0.4,<6` in the pyproject.toml and requests.txts to rewind us to `5.2.0`, as we were a few weeks ago. this handles a `requests` version issue and I think also a PyInstaller incompatibility that was causing chardet to not load in the recent builds. this thing is 'character detection' and helps with website decoding

### boring cleanup

* fixed a harmless but spammy log error when the client booted with a session that included an OR predicate with certain service-based system predicates
* used the same 'commit content updates and make a popup if it takes a while' routine I wrote for manage tags for media viewer delete files. I don't think this guy is going to spawn ten super slow popups any time, but if it does, they'll now be more visible if the user closes the viewer immediately after a delete during busy times etc..
* when telling a 'file log' to 'retry these previously deleted entries, and yes clear the deleted record', the database clear action is now asynchronous. the panel disables while it works
* archive/delete async commit block size is now 10 files, down from 64, to reduce latency as it works
* all the multi-column lists in the program now have the ability to change height to exactly contain their contents (like the gallery downloader does), and almost all of them now have a defined range for this tech. most are in the 6-12 or 12-24 range, depending on the type of panel or dialog they sit in. almost all of them are happy to be a smaller minimum size, and the minimum size math here is less crazy. lists should just size vertically a bit better now
* started a nicer and cleaner core layout call in the new `ClientGUILayout`. a years-old hack from the wx days is being replaced with nicer Qt code. the core idea is finished, and one real place uses it and nothing blew up, so the next few months will have more pushes on this and a bunch of long-term layout issues will be incrementally fixed
* brushed up the error handling around stylesheet loading
* brushed up the 'you don't need the server' help document
* brushed up the 'running from source' help regarding venvs and different versions of python
* updated some help/readmes about custom assets under your `db/static` folder. I now mean to recommend this in all cases--don't edit the install dir, make a custom folder under your db

### boring import options work

* moved some import options panel code around. the existing dialog and button are moved to `Legacy` files and will be deleted after the transition
* fleshed out some of the options here to differentiate between subs, downloader pages, and all 'post file' work
* reworked the options so specific url class options trigger at the correct layer in our stack of swiss cheese
* added some tools to the main manager so he can give nice human descriptions on his inner workings during editing
* 'full' import options containers can now describe where they got each import options (e.g. 'from subscriptions default')
* wrote out failsafe url class type and name labelling into this
* wrote most of a panel to edit a new `ImportOptionsContainer` object. I'm generally happy with it so far. it'll be a vertical listbook with the list of options types above switching edit panels below, and each line in the options list saying 'tag import options: does x' or 'tag import options: uses file posts default'. this is a complicated thing that I want to end up being clear and user-friendly, albeit sophisticated. I think we are getting there
* next will be a dialog to handle the defaults, and some favourites management UI, and then updating the workflow. lots still to do

## [Version 662](https://github.com/hydrusnetwork/hydrus/releases/tag/v662)

### future build committed, clean install needed

* This release commits the changes tested with the recent future build. The test went well but for the new mpv dll, which we will try again later.
* **Windows and Linux users who extract must perform a 'clean install' this week!** https://hydrusnetwork.github.io/hydrus/getting_started_installing.html#clean_installs
* Windows users who use the installer can update as normal
* In this new build, we have--
* build folder structure now tucks dlls and such into a 'lib' dir
* the Docker packages are updated to Alpine 3.23
* SQLite on Windows is updated to 3.51.2
* thanks to the clean install, the Windows mpv dll is no longer renamed, but now `libmpv-2.dll`
* and for the build scripts, the client and server specs are now merged into one, the gubbins in the spec is pushed to the new content_dir 'lib', Docker builds are cached better, and everything is cleaner

### duplicates auto-resolution

* I wrote a new Comparator type that does weird hardcoded jobs on just one file, debuting 'A/B/either is a progressive jpeg/is a non-progressive jpeg'
* wrote an edit panel for these
* added some unit tests for this new type

### tag menu and inversion

* the tag/active predicates list 'search' menu is now split into 'open' and 'search'
* the 'invert' item in 'search' is updated for clarity--previously, it was trying to tapdance over some 'require/exclude' verbiage, but it wasn't clean. now it just says 'invert'
* after talking with some people and looking at the code, I'm making `system:(like rating) is x` no longer invertible (this is a special state that acts as a perfect 'not' and feeds into some UI actions and menu labels, for instance system:inbox/archive are inverts of each other). previously it did a 'like/dislike' flip, but that doesn't include files not rated. 'has rating' and 'no rating' still flip as before
* `system:rating less/greater than x` is now only invertible for inc/dec services, and it now does precise `>3/<4` switching
* 'system:all/any x y z ratings rated' now invert correctly (they were previously just flipping the rated part, not the all/any too. the 'only' version is no longer invertible--I think we just don't support this with existing logic??

### misc

* the 'edit subscriptions' dialog now has an 'overwrite downloader' button to mass-set a new downloader for a selection of subs
* if the media viewer has not had a slideshow yet, the 'pause/play slideshow' shortcut will now start a new slideshow at the first defined custom time (default 1.0 seconds)
* if you stop a slideshow, the slideshow menu now provides 'resume at x seconds', firing off the 'pause/play' action
* the `resize window to fit media at specified zoom and recenter it in the viewer` shortcut action now says that specified zoom in its text where it is set (e.g. in the edit shortcuts UI)

### setup_venv.py updates

* _only important to advanced source users_
* after talking about it with several users, we are doing a bit more `pyproject.toml` and `setup_venv.py` work.
* the `groups` stuff in `pyproject.toml` is not really working out nice. it breaks a simple `pip install .` and other managers' install lines that many users are going to default to. trying to maintain the `setup_venv.py` choices in a `pyproject.toml` file was a nice idea but is not proving a good fit
* THEREFORE: I am planning to make the `pyproject.toml` nice and KISS so it works out the box, with only the `dev` group surviving. `setup_venv.py` will be the place to do weird/test venv setup
* this will happen on v673, a little under three months from now. I was previously planning just some `new` to `normal` renaming, but instead we'll do a bigger clearout. if you use the groups in the current `pyproject.toml` in any way, migrate away before then, likely to `setup_venv.py`
* I did the `setup_venv.py` stuff for today though; it now hardcodes all its decisions, entirely within the .py. no more relying on some other requirements definition standard; I just hack it with code for whatever I need, pipe it all to a pip install call, and it all installs in one clean step
* also brushed up the `setup_venv.py` code and prompts and all that a bit
* I wrote a `setup_help.py` for building the help and a `git_pull.py` convenience script to multiplat-replace the other .bat/.command/.sh stuff in the base dir. all the old scripts will be deleted on v673

### boring stuff

* fixed an issue hitting 'cancel' on note import options via the subscription or duplicate merge import options dialogs
* all temp files that hydrus makes in its tempdir now have a job-respective prefix rather than always `hydrus`, for instance `file_download_`
* updated the Linux install help regarding Wayland/X11 environment variables. both `unset WAYLAND_DISPLAY` and `export QT_QPA_PLATFORM=xcb` seem to be the trick to run in X11
* misc 'running from source' help brush-up
* updated some stuff in the 'installing' help about clean installs

### boring import options overhaul progress

* rewrote my new container and manager to have a stricter swiss-cheese/full dichotomy. rather than navigating layers of swiss cheese over and over, for every request, the manager now compresses the slices into a 'full' import options container that can answer any questions further down the file import chain
* moved `FilenameTaggingOptions` out of the legacy `TagImportOptions` stuff to its own file
* moved `ServiceTagImportOptions` out of the legacy `TagImportOptions` stuff to a new file that holds the new `TagImportOptions` object
* updated the legacy `TagImportOptions` to now hold the new `TagFilteringImportOptions` and`TagImportOptions` in prep for the big migration, just like I've done for `FileImportOptions`. the whole import pipeline is updated to talk to these two guys as appropriate
* wrote specific edit panels for the new objects
* also updated the unit tests for all this
* all the options objects are now ready to migrate. next I need to write a bunch of UI to handle the new edit panels I've written and manage my 'swiss cheese' defaults model in a user-friendly way. all the defaults setup and the 'import options' buttons in all downloaders need a rework. then I need to rejigger the file import path to pass around one container object rather than the current scatter. I feel pretty good about it. two more pushes on this, I think, and I can flip the switch

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
* I am not totally happy with the recent changes to `pyproject.toml`, which had to be emergency-patched last week. I will be revisiting it in the near future with a big KISS brush. most of the overly-complicated groups are going to disappear such that normal package managers will just work out of the box with it, and `setup_venv.py` will be the canonical place to install test library versions. no big changes yet, but since I was already planning to sunset some group stuff for v673, expect that to be the new date for this to get much simpler. I'll try and push on this next week
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
