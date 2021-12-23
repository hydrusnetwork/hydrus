# Changelog

!!! note
    This is the new changelog. For versions prior to 466 see the [old changelog](old_changelog.html).

## [Version 467](https://github.com/hydrusnetwork/hydrus/releases/tag/v467)

### new scanbar cleanup
* the media container's scanbar and volume control are now combined on the same widget, meaning they now show/hide in sync and faster. their layout calculation is also more sensible. the new controls bar also has a thin border to make it pop better against a background video
* improved the way some auto-hide anti-flicker tech on the scanbar now works. it all hides a frame faster sometimes
* figured out some new anti-flicker tech to reduce/eliminate a frame of stretch when flicking from a static image to an mpv video, particularly for the first or second time in a session
* fixed a bug where clicking the global mute/unmute on an mpv player meant that certain shortcut keys (usually those with arrow keys) would not work on that player again. (it was a focus issue on the button, which then captured some form navigation keys but they had nowhere to go)
* brushed up some mouse coordinate testing logic across the program. some linux clients had trouble with the new animation scanbar popping up over mpv, I think I improved it!
* fixed another type problem with newer python/PyQt5 on Arch, also in scanbar coordinate testing
* fixed some dodgy colours in the scanbar initialisation and volume control border
* macOS users: I undid a long-time paint hack on the media container and the static image canvas. Qt is responsible for clearing the background again, which allows me to remove some jank anti-flicker tech. HOWEVER, the original reason for this hack was because without it, old macOS went to 100% CPU whenever the media viewer was showing something. therefore, to be safe, this option is still on for macOS users for now. you'll get a little flicker when browsing. please try hitting _help->debug->gui actions->macOS anti-flicker test_ and do some mixed video/image browsing. does your whole damn client lock up?

### misc
* the 'file log' and 'search log' buttons are now a new widget class that puts an arrow on the side that opens a menu. the secret right-click menus of these buttons is now exposed for all
* fixed a bug affecting some greyscale pngs with ICC profiles--they were coming out pure white due to a colourspace conversion problem
* fixed an import problem when PIL could not load a file (due to file malformation) but OpenCV could. this was causing a failed import from the new ICC profile detection code
* when the downloader hits a broken image file that cannot be imported due to malformation, the status is now 'error' instead of the incorrect 'ignored'
* fixed the duplicate file filesize comparison statement sometimes showing > in one direction and ≈ in the other. it happened when the larger file was between 20/19 and 21/20 times the size of the smaller, just a logic typo (issue #1028)
* the trash maintenance daemon is moved from the old threaded daemon system to the new repeating job worker pool. this is the last daemon cleaned up, so I am retiring the old and mostly defunct 'no_daemons' launch argument. a variety of other daemon infrastructure for things like shutdown checks is similarly removed. the program also now waits for the newer daemon jobs to finish working on shutdown
* moved most client daemon jobs like repository sync and dirty object save down so they start after the first session is loaded rather than right after boot
* if a file is called to regen its thumbnail but currently has no dimension, this is now a no-op rather than an error. in the situation where users force thumb regen before metadata regen and encounter this, it is sorted out later when the metadata regen recognises new dimensions and reschedules the thumb regen
* added an extensive user-written guide to the --db_synchronous_override launch argument to the launch arguments help page. it is possible and safe to run the program with synchronous=0 as long as certain caveats are obeyed. thanks to the user who figured this out and wrote it up
* the downloader engine now discards source urls in an import job if they have the same domain as any existing primary url. this will ensure that if a booru has a link back to itself as a source url, when the 'source' is really an alternate rather than a dupe, it won't be added in hydrus as a known url for that imported file
* misc cleanup in downloader system and file/search log UI
* fixed a type bug in the file and search log 'import from png' action. if you have existing pngs previously exported from here, they will import ok now
* refactored the various hydrus compression code to a new HydrusCompression file
* exported serialisable data pngs such as from file or search log that hold simple Strings now always compress the data before embedding it in the png. existing pngs that hold uncompressed strings should still load ok
* the payload in an exported png is now always compressed, and the payload description always states the uncompressed size
* sped up client shutdown when network traffic has been paused the whole time and a repo sync job might have wanted to run. these jobs also do not hang on a thread worker if network traffic is paused, but they should wake immediately when it is unpaused
* the hydrus login system is now resistant to connection failures; previously it was getting hung up and jamming the whole hydrus sync system when a server was down

### client api
* added GET /manage_database/mr_bones to the Client API. it returns a JSON Object with the same numbers used in the _help->how boned am I?_ dialog
* incremented Client API version to 23

## [Version 466](https://github.com/hydrusnetwork/hydrus/releases/tag/v466)

### video scanbar autohide
* the scanbar that shows below audio and video is now embedded inside the video frame, and it show/hides based on how close your mouse is to it
* I've wanted to do this for a long time, since it will allow you to watch 16:9 videos at true 100% in borderless fullscreen, but the hackery of how the media viewer works behind the scenes means this took more work than you'd think and is still a little jank. there's a small amount of flicker when it pops in and out, which I will work on in future. in any case, please have a play with it and let me know what you think. I expect to add some more options, like for the activation padding area around it, and I will be tidying up more layout stuff throughout the media viewer
* if you are a mostly keyboard user, please check out the new 'global' shortcut to flip on/off a 'force the animation scanbar to show' mode
* I don't really want to bring back the always-on hanging-below scanbar that just takes up space, but if you try this new embedded scanbar and really hate it, we'll see what we can do

### more duplicate filter search options
* the duplicates page now has a dropdown on the search for 'must be/can be/excludes pixel dupes'!
* the duplicates page now has a number control on the search for what distance the pair was found at! I am not sure how accurate this thing is in all cases, but it seems I started tracking this data some time ago and forgot I even had it
* these new options are remembered in your session and _should_ remain fast in most normal cases. I put time into some complicated database work this week to get this going, please let me know if you have any trouble with it

### misc
* when the export filename pattern in the export files dialog means many of the files share the same base and hence need to do 'filename (5)'-style suffixes to be unique, the number here is now calculated much more efficiently. opening this dialog on 10,000 files with an oft-duplicate pattern should now be a jolt of lag but not many minutes
* when you choose to 'separate' a subscription with more than 100 queries, you are no longer forced to break it into half
* when you do break a subscription in half, it now makes sure to sort the query texts before separating
* if you are in advanced mode, the 'selection tags' list on the left of every page can now switch its tag display type between 'multiple media views', 'display', and 'storage'. this is experimental and a bunch of stuff like 'select files with this tag' won't work yet
* janitors' petition pages now start with their tag list in 'storage' mode, so you can see the actual tags being changed rather than with siblings and parents calculated
* rebalanced some janitor mapping petition weights. jannies _should_ see a smoother balance of 'lots of small petitions' vs 'a few larger petitions' amongst petitions all with the same reason and creator

### boring cleanup and little fixes
* when you set the checker options in the edit subscription dialog, the queries now recalculate their file velocity better. previously, they would just set 'unknown' and recalc on the next run, but now they will actually recalculate if the query container is loaded into memory or otherwise put a status that says 'will calculate on next run'
* removed the 'should be namespaced' reason from the manage tags quick petition reasons. this is now all handled by siblings, tidying up storage tags manually is busywork
* when you click 'copy traceback' on an error popup, it also copies the software version, your platform, and if you are on a frozen build or running from source
* the logger now prints version number for every block, just before the timestamp
* cleaned up a variety of media viewer UI code while working on the scanbar, fixing some misc display bugs
* moved pixel hash storage responsibility from 'file metadata' to 'similar files' module
* the similar files system now searches pixel hashes when it is called to do any similar files search. they count as 'exact match' distance
* when a file gets a new pixel hash, it now sees if any other files have that same hash. if so, it now gets queued up again in the similar files search system, ensuring this match is not missed
* misc nomenclature cleanup--since we now have both 'pixel hashes' and 'phashes', phashes are now referred to as 'perceptual hashes' everywhere
* massively refactored the primary table join that drives potential duplicates search. it should work a bit faster now and it is much easier to work with
* I added pixel dupe and distance search to the standard search results version of the join and the 'system:everything' version, which has several optimisations
* silenced some shutdown handling in file maintenance that was being printed to log as an error
* fixed some 'broken object load' error handling to print the timestamp of the specific bad object, not whatever timestamp was requested. this error handling now also prints the full dump name and version to the log, and version to the exported filename. I was working with a user who had broken subs this week, and lacking this full info made things just a little trickier to put back together
* fixed some drag and drop handling where it was possible to drop thumbnails on a certain location of a page of pages that held an empty page of pages but it would not create a new child media page to hold them
* misc serverside db code cleanup
* fixed python 3.10 type bugs in window coordinate saving and Qt image generation from buffer (issue #1027)