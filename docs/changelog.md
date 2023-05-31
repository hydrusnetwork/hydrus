---
title: Changelog
---

# changelog

!!! note
    This is the new changelog, only the most recent builds. For all versions, see the [old changelog](old_changelog.html).

## [Version 530](https://github.com/hydrusnetwork/hydrus/releases/tag/v530)

### autocomplete and system predicates

* the normal autocomplete text input in file search pages now parses system tags if you type them! For a long time, this cool system has only been awkwardly available, but now it should work straight out of the box. not every predicate is supported, and sometimes what parses is slightly different to what you see, but I am improving things regularly, so let me know what doesn't work
* the normal autocomplete text input in file search pages now has a paste button! it takes tags in the normal newline-separated hydrus format and is plugged into the system predicate parser too. it should obey the same rules as if you were typing, so if you put in a negated tag, or a wildcard or namespace wildcard, and that's allowed with your current settings, it'll propagate. anything that isn't allowed or won't parse correctly is skipped silently for now
* the system predicate parser now supports the new 'similar to data' similar files search added last week. there isn't an easy way to generate the pixel and perceptual hashes yet (this will come soon to the Client API), but if you have the hashes, the thing should now parse. same format as the existing 'similar to( files)', but just say 'similar to data' and mix and match the 64- and 16-character hashes and it'll figure it out
* fixed system predicate parsing for 'system:has note with name xxx', which was parsing as a borked 'system:has note(s)', and the same deal for 'has no note'
* also made the 'system:has/no notes' and 'system:has a note named xxx' more flexible. they can take more english variants of the phrase, and if you give a note name in "quotes" (e.g. if you copy the system predicate string and paste it back in), it'll strip them

### misc

* highlighting a gallery downloader or thread watcher is now asynchronous! this means if you load up a meaty uncached 3,000-strong downloader, the client will no longer lock up for a few seconds--it'll load the files in the background, in 256-file chunks like a normal search page, and then present them when ready. while in the loading state, the to-be-highlighted downloader will be prepended with `> ` instead of `* `, and its loading is completely cancellable--you can unhighlight it or highlight something else and the ongoing job will promptly cancel and let the new one start. if a loading job takes more than three seconds, it will make a popup window with its ongoing progress, which also has a cancel button
* when you say to 'open files in a new page', the current file sort and collect is copied to the new page, and if you have a collect set, the new page will collect
* when parsing URLs and attempting to match relative URLs (''/post/123456') to the original domain ('example.com'), if that join fails, it now just adds the parsed text. this should stop borked errors from halting the whole parse (e.g. mysterious 'Invalid IPv6 URL' error, which was probably an errantly parsed open square bracket) while also helping debugging
* improved URL-repairing in parsing. it trims gumpf before a recognisable URL (`title - https://example.com/123456`) is now more precise, and instances of weird scheme-spam (`https://http://example.com/123456`) are now fixed for mixes of schemes and replaced with the final scheme
* the thumbnail duplicate files menu now tries to recognise if the king of a group has been deleted and will say so rather than 'show the best quality file of this file\'s group'
* if you open some duplicate files from the right-click menu (e.g. show 'king') and the search can't find them, it now searches "all known files" as a backup and tells you in a popup if the backup worked or if it just couldn't find anything

### some boring cleanup

* refactored the media controller (which drives every page in the client) and the media controller panel (the actual UI) code into separate files; now the various other guys that look at the controller have proper typing and inheritance, and all the thumbnail grids are now explicitly told their respective media controllers and have better access to stuff like the current sort
* the sort widget no longer hangs onto the media controller--it just communicates changes through Qt signals
* same doubly so for the collect widget, which no longer has a mickey-mouse pubsub chain and just Qt signals its stuff now
* misc page code and sort/collect code cleanup, multiple orphaned pubsubs removed
* moved ClientSearch and ClientSearchParseSystemPredicates to a new 'search' module
* spun off the autocomplete parsing and result caching code into a new ClientSearchAutocomplete
* added a heap of note system predicates to the system pred parsing unit tests, and some for the new 'similar to data' too
* updated the `requests` in the requirements.txts up from 2.28.1 to 2.31.0 due to some security vulnerability related to `Proxy-Authorization` headers and in-url user/pass authentication when redirecting to an https destination. I don't think we used that stuff (unless the proxy settings cause it to happen under the hood), but let's update anyway. if you run from source, you might like to run setup_venv again

## [Version 529](https://github.com/hydrusnetwork/hydrus/releases/tag/v529)

### similar files search

* hydrus now supports a 'SauceNAO'-style workflow on its own files, quickly looking up if you have something that looks like the given file, without having to import it, using a new variant of the 'system:similar to' search predicate. just open up the new 'system:similar files' entry, which now has two tabs, and on the first just paste image data or a file path from your clipboard and it'll calculate the data for you
* similar files also gets a search cache this week. this makes all repeat searches massively faster, helps out successive searches (e.g. the same file at 0, 4, then 8 distance), and should accelerate all maintenance search by a good bit depending on the size and shape of your database (on my test database of only ~10k files, it sped things up 3-4x)
* 'system:similar to' search predicates are no longer mutually exclusive in the same search--you can now have multiple
* cleaned up a bunch of the similar files code generally. the main search function is split into pieces and common calls are spun off into their own thing

### misc

* added a new shortcut action, 'open file in file explorer', which opens the file in your file Explorer. if you haven't used this before, it only works on Windows and macOS and can be buggy. on Windows, if the explorer takes too long to open, it won't select the file correctly, so hit it again
* thanks to a user, the html parsing formula can now search in a sideways direction, either finding the previous or following sibling html tags (as opposed to just search descendants/ancestors)
* if an export folder is set to 'synchronise' and also needs to delete some symlinks (either it regularly makes symlinks, or it is clearing symlinks from an old run), _and_ those symlinks now point to since-deleted files, the dead symlinks should now delete correctly! thanks for an interesting report here
* the docker build now has pympler support for memory profiling. note that this does not work very well--it is unfathomably laggy atm for any client of real size, so bear with me
* the new Qt Media Player experiment is now more careful about how it deletes old windows. old players are handed off to the main gui, which takes ownership and explicitly waits for them to finish current work, then asks them to unload their media, and then, only when they are all clear sends the window delete signal. this should stop some READY/NULL errors people were seeing on unload, and hopefully without causing new stability problems (I've had crash trouble with explicitly unloading media before destroy before, but I'm doing it super safe here, so we'll see)
* I added some more error reporting to the related area in the mpv player--if it fails to unload a media, it now prints the details to log--let's see if we can improve this too
* when files fail to import for reasons other than veto or unsupported file, they now say the actual exception type in their first line summary

### client api

* when the api sends a file to be imported and it fails, the response 'note' now just has this human-readable top level line (it used to have the full error trace), and a new entry 'traceback' has the trace
* the client api version is now 45

### future build

* to improve library update testing, I have set up a second, 'future' build that is the same as a normal release but uses newer library versions, for instance Python 3.10 from 3.9 and Qt 6.5.0 rather than 6.4.1. I am not sure how often I will be making this build--I don't want to spam, so I'm thinking once per month, but maybe we'll ultimately end up incorporating it into the main build and just kick it out every week--but please feel free to test them out as they do happen and let me know if you encounter any problems booting or with anything else. the idea here is to get more user situations, particularly older OSes, testing pending library updates so I can be more confident about pulling the trigger on moving up in the master build (the recent jump to Qt 6.4.1 caused several Win 10 users to have an annoying 2-second delay on opening any new search page, but 6.5.0 doesn't have this, so if you encountered this error, please try this build and let me know how it goes). the build is in the normal github releases stream, marked as a pre-release. v528-future is here: https://github.com/hydrusnetwork/hydrus/releases/tag/v528-future-1

## [Version 528](https://github.com/hydrusnetwork/hydrus/releases/tag/v528)

### faster file search cancelling

* if you start a large file search and then update or otherwise cancel it, the existing ongoing search should stop a little faster now
* all timestamp-based searches now cancel very quickly. if you do a bare 'all files imported in the last six months' search and then amend it with 'system:inbox', it should now update super fast
* all note-based searches now cancel quickly, either num_notes or note_names
* all rating-based searches now cancel quickly
* all OR searches cancel faster
* and, in all cases, the cancel tech works a little faster by skipping any remaining search more efficiently
* relatedly, I upgraded how I do the query cancel tech here to be a bit easier to integrate, and I switched the 20-odd existing cancels over to it. I'd like to add more in future, so let me know what cancels slow!

### system predicate parsing

* the parser is more forgiving of colons after the basename, e.g. 'system:import time: since 2023-01-01' now parses ok
* added 'since', 'before', 'around', and 'day'/month' variants to system datetime predicate parsing as more human analogues of the '>' etc... operators
* you can now say 'imported', 'modified', 'last viewed', and 'archived' without the 'time' part ('system:modified before 2020-01-01')
* also, 'system:archived' with a 'd' will now parse as 'system:archive'
* you now can stick 'ago' ('system:imported 7 days ago') on the end of a timedelta time system pred and it should parse ok! this should fix the text that is copied to clipboard from timedelta system preds
* the system predicate parser now handles 'file service' system preds when your given name doesn't match due to upper/lowercase, and more broadly when the service has upper case characters. some stages of parsing convert everything to lowercase, making this tricky, but in general it now does a sweep of what you entered and then a sweep that ignores case entirely. related pro-tip: do not give two services the same name but with different case

### misc

* you can now edit the default slideshow durations that show up in the media viewer right-click menu, under _options->media_. it is a bit hacky, but it works just like the custom zoom steps, with comma-separated floats
* fixed 'system:num notes < x', which was not including noteless files (i.e. num_notes = 0) in the result
* fixed a bug in _manage services_ when adding a local file service and then deleting it in the same dialog open. a test that checks if the thing is empty of files before the delete wasn't recognising it didn't exist yet
* improved type checking when pasting timestamps in the datetime widget, I think it was breaking some (older?) versions of python

### some more build stuff

* fixed the macOS App, which was showing a 'no' symbol rather than launching due to one more thing that needed to be redirected from 'client' to 'hydrus_client' last week (issue #1367)
* fixed a second problem with the macOS app (unlike PyInstaller, PyOxidizer needed the 'hydrus' source directory, so that change is reverted)
* I believe I've also fixed the client launching for some versions of Python/PyQt6, which had trouble with the QMediaPlayer imports
* cleaned up the PyInstall spec files a little more, removing some 'hidden-import' stuff from the pyinstaller spec files that was no longer used and pushing the server executables to the binaries section
* added a short section to the Windows 'running from source' help regarding pinning a shortcut to a bat to Start--there's a neat way to do it, if Windows won't let you
* updated a couple little more areas in the help for client->hydrus_client

## [Version 527](https://github.com/hydrusnetwork/hydrus/releases/tag/v527)

### important updates

* There are important technical updates this week that will require most users to update differently!
* first, OpenCV is updated to a new version, and this causes a dll conflict on at least one platform, necessitating a clean install
* second, the program executables are renamed from 'client' and 'server' to 'hydrus_client' and 'hydrus_server', necessitating shortcut updates
* as always, but doubly so this week, I strongly recommend you make a backup before updating. the instructions are simple, but if there is a problem, you'll always be able to roll back
* so, in summary, for each install type--
* - if you use the windows installer, install as normal. your start menu 'hydrus client' shortcut should be overwritten with one to the new executable, so you don't have to do anything there, but if you use a custom shortcut, you will need to update that too
* - if you use one of the normal extract builds, you will have to do a 'clean install', as here https://hydrusnetwork.github.io/hydrus/getting_started_installing.html#clean_installs . you also need to update your program shortcuts
* - macOS users have no special instructions. update as normal
* - source users, git pull as normal. if you haven't already, feel free to run setup_venv again to get the new OpenCV. update your launch scripts to point at the new 'hydrus_client.py' scripts
* - if you have patched my code, particularly the boot code, obviously update your patches! the 'hydrus_client.py' scripts just under 'hydrus' module all got renamed to '\_boot' too!
* also, some related stuff like firewall rules (if you run the Client API) may need updating!

### boring related update stuff

* the Windows build's sqlite3.dll and exe command line interface are updated to the latest, 3.41.2
* the 'updating' help now has a short section for the 526->527 update step, reiterating the above
* the builds no longer include the hydrus source in the 'hydrus' subdirectory. this was an old failed test in dual-booting that was mostly forgotten about and now cleaned up. if you want to run from source, get the source
* the windows hydrus_client and hydrus_server executables now have proper version info if you right-click->properties and look at the details tab

### Qt Media Player

* THIS IS VERY BUGGY AND SOMETIMES CRASHY; DISABLED FOR MOST USERS; NOT FOR NORMAL USE YET
* I have integrated Qt's Media Player into hydrus. it is selectable in _options->media_ (if you are an advanced user and running from source) and it works like my native viewer or mpv. it has good pixels-on-screen performance and audio support, but it is buggy and my implementation is experimental. for some reason, it crashes instantly when running from a frozen executable, so it is only available for source users atm. I would like feedback from advanced source users who have had trouble with mpv--does it work? how well? any crashes?
* this widget appears to be under active development by the Qt guys. the differences between 6.4.1 vs 6.5.0 are significant. I hope the improvements continue!
* current limitations are:
* - It is only available on Qt6, sorry legacy Qt5 source users
* - this thing crashed the program like hell during development. I tightened it up and can't get it to crash any more with my test files on source, but be careful
* - the video renderer is OpenGL and in Qt world that seems to mean it is ALWAYS ON TOP at all times. although it doesn't interfere with click events if you aim for the scanbar (so Qt's z-indexing logic is still correct), its pixels nonetheless cover the scanbar and my media viewer hover windows (I will have to figure out a different scanbar layout with this thing)
* - longer audio-only files often stutter intolerably
* - many videos can't scan beyond the start
* - some videos turn into pixel wash mess
* - some videos seem to be cropped wrong with green bars in the spare space
* - it spams a couple lines of file parsing error/warning info to the log for many videos. sometimes it spams a lot continuously. no idea how to turn it off!
* anyway, despite the bugs and crashing, I found this thing impressive and I hope it can be a better fallback than my rubbish native viewer in future. it is a shame it crashes when built, but I'll see what I can do. maybe it'll be ready for our purposes by Qt7

### misc

* if twisted fails to load, its exact error is saved, and if you try to launch a server, that error is printed to the log along with the notification popup

## [Version 526](https://github.com/hydrusnetwork/hydrus/releases/tag/v526)

### there will be an important update next week

* next week's release will have two important program changes--I will integrate an OpenCV update, which will require 'extract' users to perform a clean install, and the executables are finally changing from 'client' and 'server' to 'hydrus_client' and 'hydrus_server'! be prepared to update your shortcuts and launch scripts

### time

* fixed a stupid logical bug in my new date code, which was throwing errors on system:time predicates that had a month value equal to the current month (e.g. 'x years, 5 months' during May)--sorry! (issue #1362)
* when a subscription dies, the popup note about it says the death velocity period in the neat '180 days', as you set in UI, rather than converting to a date and stating the number of months and days using the recent calendar calculation updates
* I unified some more 'xxxified date' UI labels to be 'xxxified time'. we're generally moving to the latter format as the ideal while still accepting various combinations for system parsing input

### shortcuts

* added 'media play-pause/previous/next' and 'volume up/down/mute' key recognition to the shortcut system. if your keyboard/headphones have media keys, they _should_ be mappable now. note, however, that, at least on Windows, while these capture in the hydrus UI, they seem to have global OS-level hooks, and as far as I can tell Qt can't stop that event propagating, so these may have limited effectiveness if you also have an mp3 player open, since Windows will also send the 'next' call to that etc... it may be there is a nice way to properly register a Qt app as a media thing for Windows to global-hook these events to, but I'm not sure!
* also added 'mouse task button' to the mappable buttons. this is apparently a common Mouse6 mapping, so if you have it, knock yourself out
* the code in the shortcut system that tries to detect and merge many small scroll wheel events (such as the emulated scroll that a trackpad may generate) now applies to all mouse devices, not just synthesised events. with luck, this will mean that mice that generate like 15 smoothscroll events of one degree instead of one of fifteen degrees for every wheel tick will no longer spam-navigate the media viewer wew

### misc

* to save you typing/pasting time, the 'enter your reason' prompts in manage tags, tag siblings, and tag parents now remember the last five custom reasons you enter! you can change the number saved using the new option under _options->tags_, including setting it to 0 to disable the system
* fixed pasting tags in the manage tags dialog when the number of tags you are pasting is larger than the number of allowed 'recent tags'. previously it was saying 'did not understand what was in the clipboard', so hooray for the new error reporting
* every multi-column list in the program now has a 'reset column widths' item in its header right-click menu! when these reset events happen, the respective lists also resize themselves immediately, no restart required
* when you set 'try again' on an import object, it now clears all saved hashes from the import object (including the SHA256 which may have been linked from the database in an 'already in db'/'previously deleted' result). this will ensure the next attempt is not poisoned by these hashes (which can happen for various reasons) in the subsequent attempt. basically 'try again' resets better now (issue #1353)

### some build stuff

* the main build script now only uses Node16 sub-Actions (Node12 support is deprecated and being dropped in June)
* the main build script no longer uses set-output commands (these are deprecated and being dropped later in the year I think, in favour of some ENV stuff)
* tidied some cruft from the main build script
* I moved the 'new' python-mpv in the requirements.txts from 1.0.1 to 1.0.3. source users might like to rebuild their venvs again, particularly Windows users who updated to the new mpv dll recently

## [Version 525](https://github.com/hydrusnetwork/hydrus/releases/tag/v525)

### library updates

* after successful testing amongst source users, I am finally updating the official builds and the respective requirements.txts for Qt, from 6.3.1 to 6.4.1 (with 'test' now 6.5.0), opencv-python-headless from 4.5.3.56 to 4.5.5.64 (with a new 'test' of 4.7.0.72), and in the Windows build, the mpv dll from 2022-05-01 to 2023-02-12 (API 2.0 to 2.1). if you use my normal builds, you don't have to do anything special in the update, and with luck you'll get slightly faster images, video, and UI, and with fewer bugs. if you run from source, you might want to re-run your setup_venv script--it'll update you automatically--and if you are a modern Windows source user and haven't yet, grab the new dll here and rename it to mpv-2.dll https://sourceforge.net/projects/mpv-player-windows/files/libmpv/mpv-dev-x86_64-20230212-git-a40958c.7z . there is a chance that some older OSes will not be able to boot this new build, but I think these people were already migrated to being source users when Win 7-level was no longer supported. in any case, let me know how you get on, and if you are on an older OS, be prepared to rollback if this version doesn't boot
* setup_venv.bat (Windows source) now adds PyWin32, just like the builds (the new version of pympler, a memory management module, moans on boot if it doesn't have it)

### timestamps

* a couple places where fixed calendar time-deltas are converted to absolute datestrings now work better over longer times. going back (5 years, 3 months) should now work out the actual calendar dates (previously they used a rough total_num_seconds estimation) and go back to the same day of the destination month, also accounting for if that has fewer days than the starting month and handling leap years. it also handles >'12 months' better now
* in system:time predicates that use since/before a delta, it now allows much larger values in the UI, like '72 months', and it won't merge those into the larger values in the label. so if you set a gap of 100 days, it'll say that, not 3 months 10 days or whatever
* the main copy button on 'manage file times' is now a menu button letting you choose to copy all timestamps or just those for the file services. as a hacky experiment, you can also copy the file service timestamps plus one second (in case you want to try finick-ily going through a handful of files to force a certain import sort order)
* the system predicate time parsing is now more flexible. for archived, modified, last viewed, and imported time, you can now generally say all variants in the form 'import' or 'imported' and 'time' or 'date' and 'time imported' or 'imported time'.
* fixed an issue that meant editing existing delta 'system:archived time' predicates was launching the 'date' edit panel

### misc

* in the 'exif and other embedded metadata' review window, which is launched from a button on the the media viewer's top hover, jpegs now state their subsampling and whether they are progressive
* every simple place where the client eats clipboard data and tries to import something now has a unified error-reporting process. before, it would make a popup with something like 'I could not understandwhat was in the clipboard!'. Now it makes a popup with info on what was pasted, what was expected, and actual exception info. Longer info is printed to the log
* many places across the program say the specific exception type when they report errors now, not just the string summary
* the sankaku downloader is updated with a new url class for their new md5 links. also, the file parser is updated to associate the old id URL, and the gallery parser is updated to skip the 'get sank pro' thumbnail links if you are not logged in. if you have sank subscriptions, they are going to go crazy this week due to the URL format changing--sorry, there's no nice way around it!--just ignore their popups about hitting file limits and wait them out. unfortunately, due to an unusual 404-based redirect, the id-based URLs will not work in hydrus any more
* the 'API URL' system for url classes now supports File URLs--this may help you figure out some CDN redirects and similar. in a special rule for these File URLs, both URLs will be associated with the imported file (normally, Post API URLs are not saved as Known URLs). relatedly, I have renamed this system broadly to 'api/redirect url', since we use it for a bunch of non-API stuff now
* fixed a problem where deleting one of the new inc/dec rating services was not clearing the actual number ratings for that service from the database, causing service-id error hell on loading files with those orphaned rating records. sorry for the trouble, this slipped through testing! any users who were affected by this will also be fixed (orphan records cleared out) on update (issue #1357)
* the client cleans up the temporary paths used by file imports more carefully now: it tries more times to delete 'sticky' temp files; it tries to clear them again immediately on shutdown; and it stores them all in the hydrus temp subdirectory where they are less loose and will be captured by the final directory clear on shutdown (issue #1356)

## [Version 524](https://github.com/hydrusnetwork/hydrus/releases/tag/v524)

### timestamp sidecars

* the sidecars system now supports timestamps. it just uses the unix timestamp number, but if you need it, you can use string conversion to create a full datestring. each sidecar node only selects/sets that one timestamp, so this may get spammy if you want to migrate everything, but you can now migrate archived/imported/whatever time from one client to another! the content updates from sidecar imports apply immediately _after_ the file is fully imported, so it is safe and good to sidecar-import 'my files imported time' etc.. for new files, and it should all get set correctly, but obviously let me know otherwise. if you set 'archived time', the files have to be in an archived state immediately after import, which means importing and archiving them previously, or hitting 'archive all imports' on the respective file import options
* sidecars are getting complex, so I expect I will soon add a button that sets up a 'full' JSON sidecar import/export in one click, basically just spamming/sucking everything the sidecar system can do, pretty soon, so it is easier to set up larger migrations

### timestamp merge

* the duplicate merge options now have an action for 'sync file modified date?'. you can set so both files get their earliest (the new default for 'they are the same'), or that the earlier worse can be applied to the later better (the new default for 'this is better') (issue #1203)
* in the duplicate system, when URLs are merged, their respective domain-based timestamps are also merged according to the earliest, as above

### more timestamps

* hydrus now supports timestamps before 1970. should be good now, lol, back to 1AD (and my tests show BC dates seem to be working too?). it is probably a meme to apply a modified date of 1505 to some painting, but when I add timestamps to the API maybe we can have some fun. btw calendar calculations and timezones are hell on earth at times, and there's a decent chance that your pre-1970 dates may show up on hour out of phase in labels (a daylight savings time thing) of what you enter in some other area of UI. in either case, my code is not clever enough to apply DST schedules retroactively to older dates, so your search ranges may simply be an hour out back in 1953. it sounds stupid, but it may matter if we are talking midnight boundaries, so let me know how you find it
* when you set a new file modified date, the file on disk's modified date will only be updated if the date set is after 1980-01-01 (Windows) or 1970-01-01 (Linux) due to system limitations
* fixed a typo bug in last week's work that meant file service timestamp editing was not updating the media object (i.e. changes were not visible until a restart)
* fixed a bug where collections that contained files with delete timestamps were throwing errors on display. (they were calculating aggregate timestamp data wrong)
* I rejiggered how the 'is this timestamp sensible?' test applies. this test essentially discounts any timestamp before 1970-01-08 to catch any weird mis-parses and stop them nuking your aggregate modified timestamp values. it now won't apply to internal duplicate merge and so on, but it still applies when you parse timestamps in the downloader system, so you still can't parse anything pre-1970 for now
* one thing I noticed is my '5 years 1 months ago' calculation, which uses a fixed 30 day month and doesn't count the extra day of leap years, is showing obviously increasingly inaccurate numbers here. I'll fix it up

### export folders

* export folders can now show a popup while they work. there's a new checkbox for it in their edit UI. default is ON, so you'll start seeing popups for export folders that run in the background. this popup is cancellable, too, so you can now stop in-progress export runs if things seem wrong
* both import and export folders will force-show working popups whenever you trigger them manually
* export folders no longer have the weird and confusing 'paused' and 'run regularly?' duality. this was a legacy error handling thing, now cleaned up and merged into 'run regularly?'
* when 'run regularly?' is unchecked, the run period and new 'show popup while working regularly?' checkboxes are now disabled

### misc

* added 'system:ratio is square/portrait/landscape' nicer label aliases for =/taller/wider 1:1 ratio. I added them to the quick-select list on the edit panel, too. they also parse in the system predicate parser!
* I added a bit to the 'getting started with downloading' help page about getting access to difficult sites. I refer to Hydrus Companion as a good internal login solution, and link to yt-dlp, gallery-dl, and imgbrd-grabber with a little discussion on setting up external import workflows. I tried gallery-dl on twitter this week and it was excellent. it can also take your login credentials as either user/pass or cookies.txt (or pull cookies straight from firefox/safari) and give access to nsfw. since twitter has rapidly become a pain for us recently, I will be pointing people to gallery-dl for now
* fixed my Qt subclass definitions for PySide6 6.5.0, which strictly requires the Qt object to be the rightmost base class in multiple inheritance subclasses, wew. this his AUR users last week, I understand!

### client api (and local booru lol)

* if you set the Client API to not allow non-local connections, it now binds to 127.0.0.1 and ::1 specifically, which tell your OS we only want the loopback interface. this increases security, and on Windows _should_ mean it only does that first-time firewall dialog popup when 'allow non-local connections' is unchecked
* I brushed up the manage services UI for the Client API. the widgets all line up better now, and turning the service on and off isn't the awkward '[] do not run the service' any more
* fixed the 'disable idle mode if the client api does stuff' check, which was wired up wrong! also, the reset here now fires as a request starts, not when it is complete, meaning if you are already in idle mode, a client api request will now quickly cancel idle mode and hopefully free up any locked database situation promptly

### boring cleanup and stuff

* reworked all timestamp-datetime conversion to be happier with pre-1970 dates regardless of system/python support. it is broadly improved all around
* refactored all of the HydrusData time functions and much of ClientTime to a new HydrusTime module
* refactored the ClientData time stuff to ClientTime
* refactored some thread/process functions from HydrusData to HydrusThreading
* refactored some list splitting/throttling functions from HydrusData to a new HydrusLists module
* refactored the file filter out of ClientMedia and into the new ClientMediaFileFilter, and reworked things so the medialist filter jobs now happen at the filter level. this was probably done the wrong way around, but oh well
* expanded the new TimestampData object a bit, it can now give a nice descriptive string of itself
* wrote a new widget to edit TimestampData stubs
* wrote some unit tests for the new timestamp sidecar importer and exporter
* updated my multi-column list system to handle the deprecation of a column definition (today it was the 'paused' column in manage export folders list)
* it should also be able to handle new column definitions appearing
* fixed an error popup that still said 'run repair invalid tags' instead of 'run fix invalid tags'
* the FILE_SERVICES constant now holds the 'all deleted files' virtual domain. this domain keeps slipping my logic, so fingers crossed this helps. also means you can select it in 'system:file service' and stuff now
* misc cleaning and linting work

## [Version 523](https://github.com/hydrusnetwork/hydrus/releases/tag/v523)

### timestamp editing

* you can now _right-click->manage->times_ on any file to edit its archived, imported, deleted, previously imported (for undelete), file modified, domain modified, and last viewed times. there's a whole new dialog with new datetime buttons and everything. it only works on single files atm, so it is currently only appropriate for little fixes, and there's a couple advanced things like setting a currently missing deletion time that it can't do yet, but I expect to expand it in future (also ideally with some kind of 'cascade' option for multi-files so you can set a timestamp iteratively (e.g. +1 second per file) over a series of thumbs to force a certain import order sort etc...)
* I added a new shortcut action 'manage file times', for this dialog. like the other media 'manage' shortcuts, you can hit it on the dialog to ok it, too
* when you edit a saved file modified date, I have made it to update the actual file modified date on your disk too. a statement is printed to the log with old/new timestamps, just in case you ever need to recover this
* added system:archived time search predicate! it is under the system:time stub like the other time-based search preds. it works in the system predicate parser too

### misc

* fixed a stupid logical typo from 521's overhaul that was causing the advanced file deletion dialog to always set the default file deletion reason! sorry for the trouble, this one slipped through due to a tricky test situation (this data is actually calculated twice on dialog ok, and on the first run it was correct -\_-)
* in the edit system predicate dialogs, when you have a list of 'recent' preds and static useful preds, if one of the recent is supposed to also appear in the statics, it now won't be duped
* fixed a bug in the media object's file locations manager's deletion routine, which wasn't adding and removing the special 'all deleted files' domain at the UI level--not that this shows up in UI much, but the new timestamps UI revealed this
* in the janitorial 'petitions processing' page, the add and delete checkbox lists now no longer have horizontal scrollbars in any situation. previously, either list, but particularly the 'delete', at height 1, could be deceptively obscured by a pop-in scrollbar
* when you change your internal backup location, the dialog now states your current location beforehand. this information was previously not viewable! also, if you select the same location again, the process notes this and exits with no changes made
* all multi-column lists across the program now show a ▲ or ▼ on the column they are currently sorted on! this is one of those things I meant to do for ages; now it is done.
* also, you can now right-click any multi-column list's header for a stub menu. for now it just says the thing's identifier name, but I'll start hanging things off here like individual section-size reset and, in time, finally play around with 'select columns' tech
* all menus across the program now send their longer description text to the main window status bar. until now (at least in Qt, I forget wx), this has only been true for the menubar menus
* all menus across the program now have tooltips turned on. any command with description text, which is I think pretty much all of them, will present its full written description on hover. this may end up being annoying, so let me know what you think

### client api

* fixed an issue in the client api where it wasn't returning `file_metadata` results in the same file order you asked for. sorry for the trouble--this was softly intended, previously, but I forgot to make sure it stayed true. it also now folds in 'missing' hashes with null ids in the same position you asked for
* a new suite of unit tests check this explicitly for all the typical parameter/response types, and the new missing-hash insertion order--it shouldn't happen again!
* just to be safe, since this is a new feature, client api version is now 44

### boring code updates/cleanup

* wrote a new serialisable 'timestamp data' object to hold the various hydrus timestamps: archived, imported, deleted, previously imported, file modified, domain modified, aggregate modified, and last viewed time
* rewrote the timestamp content update pipeline to use 'timestamp data' object
* wrote a new database module for timestamp management off the file metadata module and migrated the domain-based modified timestamp code to it
* migrated the 'archive time' timestamp-handling from the inbox module to the new timestamp module
* migrated the media result timestamp-manager construction routine all down to the new timestamp module
* migrated the aggregate modified time file search code to the new timestamp module and added archived time search too
* wrote some UI for timestamp editing, whacked some copy/paste buttons on it too
* moved all current/deleted timestamp handling down from the locations manager to the timestamp manager and split off 'previously imported' time, which is used to preserve import timestamp for undelete events, into its own thing rather than a tacked-on hack for deleted timestamps
* moved all the location manager location timestamp tracking down to the timestamp manager
* the media result is now initialised with and handles an explicit copy of the timestamp manager, which is now shared to both location manager and file viewing stats manager, with duplication and merging code updated to handle this shared situation
* moved all the media/preview 'last view time' tracking down from the file viewing stats manager to the timestamp manager, which FVS now received on initialisation
* all media-based timestamp inspection now goes through the timestamp manager
* collections now track some aggregate timestamps a bit better, and they now calculate a archived time--not sure if it is useful, but they know it now
* updated all parts of the timestamp system to use the same shared enums
* cleaned the timestamp code generally
* cleaned some file service update code generally
* moved the main file viewing stats fetching routine for MediaResult building down to the file viewing stats module
* updated the old custom gridbox layout to handle multiple-column-spanning controls
* went through all the bash scripts and fixed some issues my IDE linter was moaning about. -r on reads, quotes around variable names, 4-space indenting, and neater testing of program return states

## [Version 522](https://github.com/hydrusnetwork/hydrus/releases/tag/v522)

### notes in sidecars

* the sidecars system now supports notes!
* my sidecars only support univariate rows atm (a list of strings, rather than, say, a list of pairs of strings), so I had to make a decision how to handle note names. if I reworked the pipeline to handle multivariate data, it would take weeks; if I incorporated explicit names into the sidecar object, it would have made 'get/export all my notes' awkward or impossible and not solved the storage problem; so I have compromised in this first version by choosing to import/export everything and merging the name and text into the same row. it expects/says 'name: text' for input and output. let me know what you think. I may revisit this, depending on how it goes
* I added a note to the sidecars help about this special 'name: text' rule along with a couple ideas for tricky situations

### misc

* added 'system:framerate' and 'system:number of frames' to the system predicate parser!
* I am undoing two changes to tag logic from last week: you can now have as many colons at the start of a tag as you like, and the content parser no longer tries to stop double-stacked namespaces. both of these were more trouble than they were worth. in related news, '::' is now a valid tag again, displaying as ':', and you can create ':blush:'-style tags by typing '::blush:'. I'm pretty sure these tags will autocomplete search awfully, so if you end up using something like this legit, let me know how it goes
* if you change the 'media/preview viewer uses its own volume' setting, the client now updates the UI sliders for this immediately, it doesn't need a client restart. the actual volume on the video also changes immediately
* when an mpv window is called to play media that has 'no audio', the mpv window is now explicitly muted. we'll see if this fixes an interesting issue where on one system, videos that have an audio channel with no sound, which hydrus detects as 'no audio', were causing cracks and pops and bursts of hellnoise in mpv (we suspect some sort of normalisation gain error)

### file safety with duplicate symlinked directory entries

* the main hydrus function that merges/mirrors files and directories now checks if the source and destination are the same location but with two different representations (e.g. a mapped drive and its network location). if so, to act as a final safety backstop, the mirror skips work and the merge throws an error. previously, if you wangled two entries for the same location into 'migrate database' and started a migration, it could cause file deletions!
* I've also updated my database migration routines to recognise and handle this situation explicitly. it now skips all file operations and just updates the location record instantly. it is now safe to have the same location twice in the dialog using different names, and to migrate from one to the other. the only bizzaro thing is if you look in the directory, it of course has boths' contents. as always though, I'll say make backups regularly, and sync them before you do any big changes like a migration--then if something goes wrong, you always have an up-to-date backup to roll back to
* the 'migrate database' dialog no longer chases the real path of what you give it. if you want to give it the mapped drive Z:, it'll take and remember it
* some related 'this is in the wrong place' recovery code handles these symlink situations better as well

### advanced new parsing tricks

* thanks to a clever user doing the heavy lifting, there are two neat but advanced additions to the downloader system
* first, the parsing system has a new content parser type, 'http headers', which lets you parse http headers to be used on subsequent downloads created by the parsing downloader object (e.g. next gallery page urls, file downloads from post pages, multi-file posts that split off to single post page urls). should be possible to wangle tokenized gallery searches and file downloads and some hacky login systems
* second, the string converter system now lets you calculate the normal hydrus hashes--md5, sha1, sha256, sha512--of any string (decoding it by utf-8), outputting hexadecimal

### http headers on the client api

* the client api now lets you see and edit the http headers (as under _network->data->review http headers_) for the global network context and specific domains. the commands are `/manage_headers/get_headers` and `/manage_headers/set_headers`
* if you have the 'Make a short-lived popup on cookie updates through the Client API' option set (under 'popups' options page), this now applies to these header changes too
* also debuting on the side is a 'network context' object in the `get_headers` response, confirming the domain you set for. this is an internal object that does domain location stuff all over. it isn't important here, but as we do more network domain setting editing, I expect we'll see more of this guy
* I added some some documentation for all this, as normal, to the client api help
* the labels and help around 'manage cookies' permission are now 'manage cookies and headers'
* the client api version is now 43
* the old `/manage_headers/set_user_agent` still works. ideally, please move to `set_headers`, since it isn't that complex, but no rush. I've made a job to delete it in a year
* while I was doing this, I realised get/set_cookies is pretty bad. I hate their old 'just spam tuples' approach. I've slowly been replacing this stuff with nicer named JSON Objects as is more typical in APIs and is easier to update, so I expect I'll overhaul them at some point

### boring cleanup

* gave the about window a pass. it now runs on the newer scrolling panel system using my hydrus UI objects (so e.g. the hyperlink now opens on a custom browser command, if you need it), says what platform you are on and whether you are source/build/app, and the version info lines are cleaned a little
* fixed/cleaned some bad code all around http header management
* wrote some unit tests for http headers in the client api
* wrote some unit tests for notes in sidecars

## [Version 521](https://github.com/hydrusnetwork/hydrus/releases/tag/v521)

### some tag presentation

* building on last week's custom sibling connector, if you don't like the fade you can now override the 'namespace' colour of the sibling connector if you like
* you can also set the ' OR ' connector text
* and you can set the OR connector's 'namespace' colour. it was 'system' before
* also turned off the new namespace colour fading for OR predicates, where it was unintentionally kicking in and looking horrible lol

### misc

* added a checkbox to 'file viewing statistcs' to turn off tracking for the archive/delete filter, if you don't like that
* file viewing statistics now maxes out at five times a duration-having media's duration, if that is more than your max view time
* the simple version of the file delete dialog will now never overwrite a file deletion reason if all of the to-be-deleted files already have deletion reasons (e.g. when physically deleting trash)	
* the advanced version of the dialog now always selects 'keep existing reason' or 'do not alter existing reasons' when they exist, regardless of your 'remember previous reason' action. also, the 'remember previous reason' saved reason no longer updates if 'keep existing reason' or 'do not alter existing reasons' is set--it will stick on whatever it was before
* I might have fixed a height-layout bug in the petition management page

### advanced change to unnamespaced tags and their parsing

* the rule that allows ':p' as a tag (by secretly storing it as '::p') has been expanded--now any unnamespaced tag can include a colon as long as it starts with an explicit colon, which in hydrus rendering contexts is usually hidden. you can now type these in simply by beginning your tag with ':'--the secret character will be quickly swallowed
* for the parsing system, content parsers that get tags can now decide whether to set an explicit namespace or not. from now on, content parsers that are set to get unnamespaced tags will force all tags they get to be unnamespaced! this stops some site that has incidental colons in their 'subtags' from spamming twenty different new namespaces to hydrus. to preserve old parser behaviour, all existing content parsers that were left blank (no namespace) will be updated to not set an explicit namespace. if you are a parser maker, please consider whether you want to go with 'unnamespaced' or 'any namespace' going forward in your parsers--since most places don't use the hydrus 'namespace:subtag' format, I suspect when we want to make the decision, we'll want 'unnamespaced'
* I updated the pixiv parser to specifically ask for unnamespaced tags when parsing regular user tags, since it has some of these colon-having tags
* as a side thing, extra colons are now collapsed at the start of a tag--anything that starts with four colons will be collapsed down to two, with one displaying to humans
* also, during parsing, if a content parser gets a tag and the subtag already starts with its namespace, it will no longer double the namespace. parse 'character:dave' with namespace set to 'character', it will no longer produce 'character:character:dave'

### advanced file domain and file import options stuff

* all import pages that need to consult their file domain now do so on a 'realised' version of 'default file import options', so if you are set to import to 'my imports', and you open a new page from a tag or some thumbs on that import page, the new file page will be set to 'my imports', not some weird 'my files' stub value (in clients that deleted 'my files', this would be 'initialising...' forever)
* more stages of the file import process 'realise' default file import options stubs, just in case more of these problems slip through in future (e.g. in my file import unit tests, which I just discovered were all broken)
* the 'default' file import options stub is now initialised with your first local file domain rather than 'my files', so if this thing is ever still consulted anywhere, it should serve as a better last resort
* also fixed the file domain button getting stuck on 'initialising' if it starts with an empty file domain
* when you open the edit file import options dialog on a 'default' FIO and switch to a non-default, it now fills in all the details with the current LOUD FIO

### boring cleanup

* extracted the master file search method (~1800 lines of code) from the monolithic database object and into its own module. then broke several sub-pieces like rating or note searching code out into that module and cleaned misc stuff along the way. not done by any means, but this was a big db-cleanup hump
* reshuffled all the page management objects so they no longer keep an explicit copy of their current file domain--now they always consult their respective sub-objects, whether that is a file search or an importer or what. any time a page needs to consult its file domain, it'll always get the live and sensible version. as above, they also 'realise' default file import options stubs
* broke the 'getting started with tags' help page into two and straddled the 'getting started with searching' page with them. the intention is to get users typing a few tags into their first import pages, just that, and then playing around with them in search, before moving on to more complicated tag subjects
* split the 'autocomplete' section of the 'search' options into two, for read/write a/c contexts, and the default file and tag domain options have been moved there from 'files and trash' and 'tags'
