---
title: Changelog
---

# changelog

!!! note
    This is the new changelog, only the most recent builds. For all versions, see the [old changelog](old_changelog.html).

## [Version 533](https://github.com/hydrusnetwork/hydrus/releases/tag/v533)

### macOS App crashes

* unfortunately, last week's eventFilter work did not fix the macOS build's crashing--however, thanks to user help, we figured out that it was some half-hidden auxiliary Qt library that updated in the background starting v530 (the excellently named `PyQt6-Qt6` package). the build script is updated to roll back this version and it seems like things are fixed. this particular issue shouldn't happen again. sorry for the trouble, and let me know if there are any new issues! (issue #1379)

### misc

* the download panels in subscription popup windows are now significantly more responsive. ever since the popup manager was embedded into the gui, popup messages were not doing the 'should I update myself?' test correctly, and their network UI was not being updated without other events like surrounding widgets resizing. I was wondering what was going on here for ages--turns out it was regular stupidity
* if an image has width or height > 1024, the 'share->copy' menu now shows a second, 'source lookup' bitmap, with the resolution clipped to 1024x1024
* 'sort files by hash' can now be sorted asc or desc. this also fixes a bug where it was secretly either sorting asc or desc based on the previous selection. well done to the user who noticed and tested this
* if system:limit=0 is in a search, the search is no longer run--it comes back immediately empty. also, the system:limit edit panel now has a minimum value of 1 to dissuade this state
* the experimental QtMediaPlayer now initialises with the correct volume/mute and updates on volume/mute events. the scanbar and volume control UI are still hidden behind the OpenGL frame for now, but one step forward
* the system that caches media results now hangs on to the most recent 2048 files aggressively for two minutes after initial load. previously, if you refreshed a page of unique files, or did some repeated client api work on files that were not loaded somewhere as thumbs, in the interim periods those media objects were not strictly in non-weak memory anywhere in the client and could have been eligible for clearing out of the cache. now they are a bit more sticky
* added some info on editing predicates and the various undocumented click shortcuts the taglist supports (e.g. ctrl+double-left-click) to the 'getting started with searching and sorting' help page
* added a link to the Client API help for 'Hydrus Video Deduplicator' (https://github.com/appleappleapplenanner/hydrus-video-deduplicator), which neatly discovers duplicate videos in your client and queues them up in the duplicate filter by marking them as 'potential dupes'

### sub-gallery url network parsing gubbins

* sub-gallery import objects now get the tags and custom headers that are parsed with them. if the sub-gallery urls are parsed in 'posts' using a subsidiary parser, they only inherit the metadata within their post
* sub-gallery import objects now use their parent gallery urls as referral header
* sub-gallery import objects now inherit the 'can generate more pages' state of their parents (previously it was always 'yes')
* 'next page' gallery urls do not get the tags they are parsed with. this behaviour makes a little less sense, and I suspect it _could_ cause various troubles, so I'll wait for more input, bug reports, and a larger cleanup and overhaul of how metadata is managed and passed down from one item to the next in the downloader system
* generally speaking, when file and gallery import objects have the opportunity to acquire tags or headers, they'll now add to the existing store rather than replace it. this should mean if they both inherit and parse stuff, it won't all overwrite each other. this is all a giant mess so I have a cleanup overhaul planned

### boring stuff

* if a critical drive error occurs (e.g. running out of space on a storage drive), the popup message saying 'hey everything just got mega-paused' is now a little clearer about what has happened and how to fix it
* similarly, the specific 'all watchers are paused'-style messages now specifically state 'network->pause to resume!' to point users to this menu to fix this tricky issue. this has frustrated a couple of newer users before
* to reduce confusion, the 'clear orphan files' pre-job now only presents the user one combined dialog
* improved how pages test and recognise that they have changes and thus should be saved--it works faster, and a bunch of false negatives should be removed
* improved the safety routine that ensures multiple-column list data is read-only
* fixed .txt sidecar importers' description labels, which were missing extra text munging
* to relieve some latency stress on session load, pages that are loading their initial files in the background now do so in batches of 64 rather than 256
* fixed some bad error handling in the master client db update routine
* fixed a scatter of linting problems a user found
* last week's pixiv parser hotfix is reinforced this week for anyone who got the early 532 release
* made some primitive interfaces for the main controller and schedulable job classes and ensured the main hydrusglobals has type hinting for these--now everything that talks to the controller has a _bit_ of an idea what it is actually doing, and as I continue to work on this, we'll get better linting
* moved the client DataCache object and its friends to a new 'caches' module and cleaned some of the code

## [Version 532](https://github.com/hydrusnetwork/hydrus/releases/tag/v532)

### misc

* whenever you say 'show these files in a new page', the new page now has a search interface. it starts with a 'system:hash' pre-populated with the files' hashes, so you can now easily narrow down or return to the stuff you are playing with! original file sort order is preserved until you alter or refresh the search
* tags' `right-click->search` menu now has a 'open in a new duplicate filter' for quick spawning of duplicate filters for specific searches
* the duplicate filter no longer flicks to the 'preparation' tab if there is work to do on the first numbers fetch. this thing has been driving me nuts, I don't know why I wrote it that way to begin with
* improved the reliability of certain session object saving--I believe some situations where the 'searching immediately' and 'this search was completed' status where not being saved for some page queries. this _may_ solve a long time bug where some pages would refresh on load
* all search pages that load with files now explicitly reaffirm internally that they are starting with a completed search, which should reduce some related edge case buggy behaviour here
* the 'string to string' edit control now tries to compensate if it is incorrectly given non-string data. somewhere in the html parsing formula UI this happened, an integer sneaking in the key/value of the tag rule, maybe by manual human JSON editing, but I'm not really sure. should be handled correctly now though. let me know if you are into this and discover anything
* every 'eventFilter' in the program now catches Exceptions ruthlessly. it turns out Qt can't handle an Exception escaping one of these, and this _may_ be the cause of some >=v530 crashing on macOS related to multi-column list interaction under issue #1379. it is probably the cause of some other crashes that I haven't been able to figure out--these will now give normal popup errors, so let me know if you see anything. if you have had crazy crashes in macOS recently and these changes don't fix you, reverting back to v529 is apparently ok! there have been no big database updates in that time, so you should be able to just install v529 on your existing install and be off
* the routine that purges files from the trash now uses fewer database queries to find eligable files. some Linux guys have been working with me on memory explosions possibly in this area--let me know if you notice any difference
* the 'clear trash' command in review services is politer to your database, breaking up a large amount of trash into smaller groups
* the program no longer moans to the log when it physically deletes a file and files no accompanying thumbnail to delete--this is true for several situations, and not worth the logspam
* fixed a typo error in the `url class links` 'try to fill in the gaps' command

### pixiv downloader

* I reworked the pixiv parser changes from a couple weeks ago. as background, what happened is pixiv said if you aren't logged in, you can't get the 'original' quality of the file any more. my first fix was to say 'ok, if the user is not logged in, get the lower quality', but this was the wrong decision. the parser now vetoes, causing an 'ignored' result and telling you the problem in the import note. if you _do_ want to get the lower quality image and not log in, this is now selectable as an alternate parser under _network->downloader components->manage url class links_
* also, a variety of old pixiv objects and other experiments are deleted and merged today. the parsers that worked on the old html format, `pixiv manga page parser`, `pixiv manga_big page parser`, `pixiv single file page parser - new layout`, and `pixiv tag search gallery page parser` will be deleted from your client, and the old gallery url class, `pixiv tag search gallery page` meets a similar fate. `pixiv manga_big page` and `pixiv manga page` are removed and their urls merged into a more accomodating `pixiv file page`, which stays to hold all the legacy pixiv URLs, which on the site are automatically redirected to the new format. thanks to a user for helping me with what here was cruft (issue #947)

### mpv logging and emergency halt

* a user sent me a cool truncated twitter video download that, when loaded into mpv, would crash the program after a click or two around the player. this sent me on an odyssey into the mpv logging system and event loop and some really bizarre behaviour under the hood, and, long story short, mpv will notice this particular problem class in future and immediately unload the file and present the user with a dialog explaining the issue. it also won't let you load that file again that boot
* to recognise this error class, I broaden what is logged and scan the lines as they come in. I've been careful in how I filter, but it may produce some false positives. let me know if this thing triggers for any files that seem fine in an external player
* errors of unknown severity are now printed silently to the log with a little intro text saying which file it was and so on. there are a bunch of these with the sorts of files we deal with, stuff like missing chapter marks or borked header data. I expect I'll work on silencing the ones we confirm are no big deal, but if you encounter a ton of them, particularly if you know some cause crashes, please now check your log and let me know what you see
* if you have two mpv players playing media at the same time, this reporting system will report the info for both files--sorry, I had to hack this gubbins! future versions of mpv or python-mpv may open some doors here

### client api

* the `/get_files/file` command now has a `download=true` parameter which converts the `Content-Disposition` from `inline` (show the file) to `attachment` (auto-download or open save-as dialog) (issue #1375)
* added help and a unit test for the above
* client api version is now 47

## [Version 531](https://github.com/hydrusnetwork/hydrus/releases/tag/v531)

### misc

* fixed editing favourite searches, which I accidentally broke last week with the collect-by updates
* when you right-click a tag and get the siblings/parents menus, the list of copyable siblings, parents, and children is now truncated to 10 items each per service. stuff like pokemon has hundreds of children and for a very long time has been spamming giganto 11-column menus that cover the entire screen
* same menu truncation for the open/copy URLs menu. if there's a file that has 600 URLs for interesting technical reasons, it won't nuke you any more (issue #1037)
* updated the default pixiv file page parser, which recently broke for users who were not logged in. they seem to hide original size behind the login now, so if you do a lot of pixiv work, get Hydrus Companion or figure out a cookies.txt solution and get yourself logged in
* the downloader progress panels have a couple of status text improvements: first, they will stop saying 'waiting for a work slot' when the actual error is something unusual such as the gallery search hitting the file limit. second, when there is an unusual status and the downloader is in the paused state, it can now properly differentiate between 'paused' and 'pausing'
* some invalid URL strings now raise the correct error in the downloader system, causing them to be properly filtered away instead of sticking around and being unhelpful
* if there is a connection error because of an SSL issue, the network job is now retried like any other connection error. I originally thought these were all non-retryable like cert validation errors, but it seems some of them are just write timeouts etc.. during the negotiation, so let's see how it goes
* I believe I have fixed an error when selecting a tag in a list when that list had been previously shift-selected and then cleared and repopulated
* manage siblings and parents should be better about focusing the correct text input after they boot and load
* in future, if a taglist tries to deselect something it no longer has, it'll do an emergency 'deselect all' to exorcise the ghosts fully
* reworded the text around 'reset potential duplicates' action in the duplicates page to be more clear on what it does
* I tinkered with some of the shutdown code hoping to catch an odd issue of the exit 'last session' not saving correctly, but I don't think I figured the issue out. if you have noticed you boot up and get a session that missed up to the last 15 minutes of changes before you last shut down, please let me know you your details
* added a link to `tagrank`, a new Client API project at https://github.com/matjojo/tagrank, to the Client API help. it shows you pairs of comparison images over and over and uses `trueskill` ranking algorithm to figure out which tags are your favourite
* added a link to 'Send to Hydrus', a Client API project at https://github.com/Wyrrrd/send-to-hydrus, to the Client API help. it sends URLs from an Android device to your client

### client api

* as part of a plan to migrate to service_key indexing everywhere and reduce file_metadata bloat, the client api has a new `services` structure, a service information Object where `service_key` is the key. this is now in the `/get_services` call and `/get_files/file_metadata`, under `services` under the root. the old type-based structure in `/get_services` and the in-file embedding of service info in `/get_files/file_metadata` are still in place, so nothing breaks today, but I am officially declaring them deprecated, to be deleted in 2024, and recommend all Client API devs move to the new system before the new year
* the new service object also includes info on the local rating services. I'd like to add ratings to file_metadata fairly soon
* if you don't want the services object in `/get_files/file_metadata`, there's a new `include_services_object` param you can set to false to hide it
* updated the unit tests and client api help to reflect all this. main new section: https://hydrusnetwork.github.io/hydrus/developer_api.html#services_object
* the client api version is now 46

### update woes

* I somewhat successfully pounded my head against an issue where the first tab (usually 'my tags') was disappearing in the _manage tags/siblings/parents_ dialogs for some users. this bug, for real, seems to be the combination of (Python 3.11 + PyQt6 6.5.x + two tabs + total tab text characters > ~12 + tab selection is set to 1 during init event). Change any of those things and it doesn't happen. This is so weird a problem to otherwise normal code that I won't pivot all my 50-odd instances of tab selection to handle it and instead have hacked an answer for the three tag dialogs and filename tagging. Sorry for the trouble if you got this! Let me know if you see any more
* in a similar-but-different thing, PySide6 6.5.1 has a bug related to certain Signal connections. don't use it with hydrus, it messes up all my menus! their dev notes suggest they are going to have a fix/revert for 6.5.1.1

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
