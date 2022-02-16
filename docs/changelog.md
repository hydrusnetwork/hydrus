# Changelog

!!! note
    This is the new changelog. For versions prior to 466 see the [old changelog](old_changelog.html).

## [Version 474](https://github.com/hydrusnetwork/hydrus/releases/tag/v474)

## command palette
* the guy who put the command pallete together has fixed a 'show palette' bug some people encountered (issue #1060)
* he also added mouse support!
* he added support to show checkable menu items too, and I integrated this for the menubar (lightning bolt icon) items
* I added a line to the default QSS that I think fixes the odd icon/text background colours some users saw in the command palette

## misc
* file archive times are now recorded in the background. there's no load/search/sort yet, but this will be added in future
* under 'manage shortcuts', there is a new checkbox to rename left- and right-click to primary- and secondary- in the shortcuts UI. if you have a flipped mouse or any other odd situation, try it out
* if a file storage location does not have enough free disk space for a file, or if it just has <100MB generally, the client now throws up a popup to say what happened specifically with instructions to shut down and fix now and automatically pauses subscriptions, paged file import queues, and import folders. this test occurs before the attempt to copy the file into place. free space isn't actually checked over and over, it is cached for up to an hour depending on the last free space amount
* this 'paused all regular imports' mode is also now fired any time any simple file-add action fails to copy. at this stage, we are talking 'device disconnected' and 'device failed' style errors, so might as well pause everything just to be careful
* when the downloader hits a post url that spawns several subsidiary downloads (for instance on pixiv and artstation when you have a multi-file post), the status of that parent post is now 'completed', a new status to represent 'good, but not direct file'. new download queues will then present '3N' and '3 successful' summary counts that actually correspond to number of files rather than number of successful items
* pages now give a concise 'summary name' of 'name - num_files - import progress' (it also eli...des for longer names) for menus and the new command palette, which unlike the older status-bar-based strings are always available and will stop clients with many pages becoming multi-wide-column-menu-hell
* improved apng parsing. hydrus can now detect that pngs are actually apngs for (hopefully) all types of valid apng. it turns out some weird apngs have some additional header data, but I wrote a new chunk parser that should figure it all out
* with luck, users who have window focus issues when closing a child window (e.g. close review services, the main gui does not get focus back), should now see that happen (issue #1063). this may need some more work, so let me know
* the session weight count in the 'pages' menu now updates on any add thumbs, remove thumbs, or thumbnail panel swap. this _should_ be fast all the time, and buffer nicely if it is ever overwhelmed, but let me know if you have a madlad session and get significant new lag when you watch a downloader bring in new files
* a user came up with a clever idea to efficiently target regenerations for the recent fix to pixel duplicate calculations for images with opaque alpha channels, so this week I will queue up some pixel hash regeneration. it does not fix every file with an opaque alpha channel, but it should help out. it also shouldn't take _all_ that long to clear this queue out. lastly, I renamed that file maintenance job from 'calculate file pixel hash' to 'regenerate pixel duplicate data'
* the various duplicate system actions on thumbnails now specify the number of files being acted on in the yes/no dialog
* fixed a bug when searching in complicated multi-file-service domains on a client that has been on for a long time (some data used here was being reset in regular db maintenance)
* fixed a bug where for very unlucky byte sizes, for instance 188213746, the client was flipping between two different output values (e.g. 179MB/180MB) on subsequent calls (issue #1068)
* after some user profiles and experimental testing, rebalanced some optimisations in sibling and parent calculation. fingers crossed, some larger sibling groups with worst-case numbers should calculate more efficiently
* if sibling/parent calculation hits a heavy bump and takes a really long time to do a job during 'normal' time, the whole system now takes a much longer break (half an hour) before continuing

## boring stuff
* the delete dialog has basic multiple local file service support ready for that expansion. it no longer refers to the old static 'my files' service identifier. I think it will need some user-friendly more polish once that feature is in
* the 'migrate tags' dialog's file service filtering now supports n local file services, and 'all local files'
* updated the build scripts to force windows server 2019 (and macos-11). github is rolling out windows 2022 as the new latest, and there's a couple of things to iron out first on our end. this is probably going to happen this year though, along with Qt6 and python 3.9, which will all mean end of life for windows 7 in our built hydrus release
* removed the spare platform-specific github workflow scripts from the static folder--I wanted these as a sort of backup, but they never proved useful and needed to be synced on all changes

## [Version 473](https://github.com/hydrusnetwork/hydrus/releases/tag/v473)

### misc
* fixed the recent problem with drag and dropping thumbnails to a level below the top row of pages. sorry for the trouble!
* fixed a bug where the client would not load results sorting by 'import time' when the search file domain was a single deleted file domain
* fixed a list display bug in the edit page parser dialog when a subsidiary page parser has two complicated string-match based content parsers
* collections now sort by modified time, using the largest known modified time in their collection
* added sqlite3.exe console back into the windows build--sorry, it was missing since the github build changeover!
* added a note to the help about backing up when tight on space, which I will repeat here: the sqlite database files are very compressible (70GB->17GB on default 7zip settings!), so if you need more space on your backup drive, this is a good way to reclaim it

### command palette
* a user has written a cool 'command palette' for the program! it brings up a type-and-search interface to navigate to pages or menu entries.
* I have integrated his first version and set the default shortcut to Ctrl+P. users who update will get this shortcut if they have nothing else on Ctrl+P on 'main window' set. if you prefer Ctrl+K or anything else, you can change it under _file->shortcuts->the main window_
* regular users will get a page list they can search and select, advanced users will also get the (potentially dangerous) full scan of the menubar and current thumbnail right-click menu. I will be polishing this latter feature in future to filter out big maintenance jobs and show checkbox status and similar, so if you are advanced, please be careful for now
* try it out, and let me know how it goes. the underlying widget is neat, and I can change its behaviour and extend it significantly

### (mostly advanced) deleted file improvements
* files that have been deleted from a local file domain are now aware of their file deletion reason. this is visible in the right-click menu of thumb or media canvas
* the advanced file deletion dialog now initialises using this stored reason. if all pending deletees have the same existing reason stored, it will display it, and if they are all set but differ, this will be noted and an option to not alter them is also available. this will come up later in niche advanced situations with mutiple file services
* reversing a recent change, local file deletion reasons are no longer cleared on undelete or (re)import. they'll now hang around invisibly and initialise any future advanced file deletion dialog
* updated the thumbnail and canvas undelete mechanism to handle multiple services. now, if the files are deleted in more than one domain, you will be asked to multiple-select which you wish to undelete for. if there is only one eligible undelete service, the process remains unchanged--you'll just get a yes/no confirmation if the 'confirm trash' option is set
* misc multiple local file services code conversion work

## [Version 472](https://github.com/hydrusnetwork/hydrus/releases/tag/v472b)

### highlights
* the file domain button of every autocomplete input now has a 'multiple locations' entry. this launches a checkboxlist of all possible search locations and allows you to search more than one domain at once. it works, too! in future, when we can have multiple 'my files' services, you'll be able to choose here unions of what to search. users in advanced mode will see repository updates, all local files, all known files, and the new deleted file domains on this list. I removed the deleted file domains from the front menu because I expect them to be rarely used
* in _options->thumbnails_, there is now a 'thumbnail scaling' dropdown. you can set it so thumbs only ever scale down (which remains the default), scale to fit (i.e. very small images are also scaled up), or scale to fill. the 'animation' as thumbnails refit and delayed-regen themselves to 'scale to fill' is accidentally one of the coolest things I have done
* removed the old 'EXPERIMENTAL: thumbnail fill' option. the new mode works essentially the same, but faster and higher quality
* in the page tab menu, there is a new submenu 'pages', which shows all the pages at or below the current level. if you right-click on a page of pages tab, it will just show for that page of pages. click any of the entries, you will select that page. it is a web browser-like quick navigation menu, let me know what you think!
* rejiggered the page tab menu a little, reordering groups a bit with nicer separators and putting 'select' navigation on the menu even if you click in greyspace
* fixed a problem in page tab menu logic where if you right-clicked on greyspace, it would render the menu for the bottommost page of pages row rather than the one actually clicked
* last week's update where a mouse release event will no longer fire in the shortcuts system if the mouse moved a decent distance between press and release should now work in the media viewer canvas when dragging is set to anchor the mouse in place. some advanced users may wish to try setting archive/delete to work on mouse release and use left click to drag

### bug fixes
* fixed pages force-refreshing file queries on session load. this has never been intentional, but it slipped through again and was happening for a month or two now. I have added an explicit test to my routine to make sure this doesn't happen again, sorry for the trouble!
* fixed a problem in the recent fast shutdown code that was accidentally also shutting down some maintenance work like repository processing as soon as it started, even if 'exit and force work' was chosen
* all images with a completely opaque alpha channel will now have that alpha channel dropped for the new pixel hash calculation, meaning they will now match with regular non-alpha images with the same colour pixel data. in fact, all images with an opaque alpha now have that channel dropped on load, which will save a little memory and CPU any time they are handled (issue #770)
* if the 'durable' temporary database exists on boot, it is now deleted and a fresh one created rather than trying to re-use the old one (which would not have any useful information anyway), and a note is made to log. one user recently had a problem where an existing corrupt temp dir was stopping boot, which this fixes

### misc
* updated the windows build to use a newer version of mpv, moving from roughly 2021-02 to 2022-01. this replaces mpv-1.dll with mpv-2.dll, and I set the installer to delete the old '1'. if you extract, you can delete the old '1' yourself, but things seems fine with both. in any case, let me know if you have any trouble!
* updated the windows build to use sqlite 3.37.2, the sqlite3 in the db dir is also updated
* the deleted files system now neatly cleans up old file deletion reasons on file import and file undelete
* cleared out some old thumbnail generation code, including deleting an old and now obselete optimisation where too-large thumbs were scaled down to make new thumbs rather than revisiting source. since our thumb situation is more complicated now, this is gone in favour of nicer quality thumbs and simpler code
* fixed up some upcoming database maintenance code in my new modules
* updated and cleaned the code in the old wx-converted checkboxlist and replaced some awkward old access routines
* cleared out some old HTA archive code

## [Version 471](https://github.com/hydrusnetwork/hydrus/releases/tag/v471)

### times
* if you have file viewing stats turned on (by default it is), the client will now track the 'last viewed time' of your files, both in preview and media viewers. a record is only made assuming they pass the viewtime checks under _options->file viewing statistics_ (so if you scroll through really quick but have it set to only record after five seconds of viewing, it will not save that as the last viewed time). this last viewed time is shown on the right-click menu with the normal file viewing statistics
* sorting by 'import time' and 'modified time' are moved to a new 'time' subgroup in the sort button menu
* also added to 'time' is 'last viewed time'. note that this has not been tracked until now, so you will have to look at a bunch of things for a few seconds each to get some data to sort with
* to go with 'x time' pattern, 'time imported' is renamed to 'import time' across the program. both should work for system predicate parsing
* system:'import time' and 'modified time' are now bundled into a new 'system:time' stub in the system predicates list. the window launched from here is an experimental new paged panel. I am not sure I really like it, but let's see how it works IRL
* 'system:last view time' is added to search the new field! give it a go once you have some data
* also note that the search and sort of last viewed time works on the 'media viewer' number. those users who use preview or combined numbers for stuff, let me know if and how you would like that to work here--sort/search for both media and preview, try to combine based on the logic in the options, or something else?

### loading serialised pngs
* the client can now load serialised downloader-pngs if they are a perfect RGB conversion of an original greyscale export.
* the pngs don't technically have to be pngs anymore! if you drag and drop an image from firefox, the temporary bitmap exported and attached to the DnD _should_ work!
* the lain easy downloader import now has a clipboard paste button. it can take regular json text, and now, bitmap data!
* the 'import->from clipboard' button action in many multiple column lists across the program (e.g. manage parsers) (but not every list, a couple are working on older code) also now accepts bitmap data on the clipboard
* the various load errors here are also improved

### custom widget colors
* (advanced users only for now)
* after banging my head against it, I finally figured out an ok way to send colors from a QSS style file to python code. this means I can convert my custom widgets to inherit colours from the current QSS. I expect to migrate pretty much everything currently fixed over to this, except tag colours and maybe some thumbnail border stuff, and retire the old darkmode
* if you are a QSS lad, please check out the new entries at the bottom of default_hydrus.qss and play around with them in your own QSSes. please do not send me any updates to be folded in to the install yet as I still have a bunch of other colours to add. this week is just a test--please let me know how it works for you

### misc
* mouse release events no longer trigger a command in the shortcuts system if the release happens more than about 20 pixels from the original mouse down. this is tricky, so if you are into clever shortcuts, let me know how it works for you
* the file maintenance manager (which has been getting a lot of work recently with icc profiles, pixel dupes, some thumb regen, and new audio channel checks), now saves its work and publishes updates faster to the UI, at least once every ten seconds
* the sort entries in the page sort control are now always sorted according to their full (type, name) string, and the mouse-wheel-to-navigate is now fixed to always mirror this
* improved some 'delete file reason' handling. currently, a file deletion reason should only be applied when a file is entering trash. there was a bug that force-physical-deleting files from trash would overwrite their original deletion reason. this is now fixed. the advanced delete files dialog now disables the whole reason panel better when needed, never sends a file reason down to the database when there should be no reason, disables the panel if all the files are in the trash, and at the database level when file deletion reasons are being set, all files are filtered for status beforehand to ensure none are accidentally set by other means. I am about to make trash more intelligent as part of multiple local file services, so I expect to revisit this soon
* the new ICC Profile conversion no longer occurs on I or F mode files. there are weird 32/64 bit monochrome files, and mode/ICC conversion goes whack with current PIL code
* replaced the critical hamming test in the duplicate files system with a different bit-counting strategy that works about 9% faster. hamming test is used in all duplicate file searching, so this should help out a tiny bit in a lot of places

### boring cleanup
* cleaned up how media viewer canvas type is stored and tested in many places
* all across the program, file viewing statistics are now tracked by type rather than a hardcoded double of preview & media viewer. it will take a moment to update the database to reflect this this week
* cleaned up a ton of file viewing stats code
* cleared out the last twenty or so uses of the old 'execute many select' database access routine in favour of the new lower-overhead and more query-optimisable temporary integer tables method

## [Version 470](https://github.com/hydrusnetwork/hydrus/releases/tag/v470b)

### multiple file services
* I finished the conversion of all UI search to the new multiple location object. everything from back- to frontend now supports cleverer search. since searching deleted files is simple to add, users in advanced mode will now see 'deleted from...' in a new list in the tag autocomplete dropdown file domain button
* the next step is writing a widget that allows multiple selection, and then all this should work right out of the box, and we'll be an important step closer to allowing multiple local file services

### misc
* the video parsing routine is better at detecting when a present audio track is actually silent (and hence when it should mark a video as 'no audio'). all video with audio will be requeued for a metadata reparse in the files maintenance system on update
* fixed an error from last week when trying to create a new page from the tags (e.g. middle-clicking them) in the active search list
* added 'audio mkv' format to the client, to represent mkvs without a video track. I think most of the time this is going to be audio track webms from youtube-dl and similar
* added 'file relationships: set files as potential duplicates' command to the 'media actions' shortcut set
* I expanded the 'backing up' section in 'installing and updating' help
* I wrote an 'anti-virus' section for 'installing and updating' help, since I kept writing the same basic spiel about false positives. please feel free to point people there in future to relieve their concerns
* improved some shutdown tests, the client and server should exit faster in some cases (e.g. when a hydrus repository network job is hanging on reconnection attempts, holding up the 'synchronise_repository' daemon shutdown)
* the 'file was xxx at (y timestamp), which was (z time units) before this check' line in file import notes now always puts 'z time units' as that, ignoring the 'always show ISO time' setting, which was just substituting it with 'y timestamp' again. let me know if you spot other bad grammar with this setting on, I'll fix it!
* fingers crossed, images in the LAB colourspace _should_ now normalise to sRGB with the correct whitepoint. thanks to the user who provided example test tiff images here. this now uses the new PIL-based colourspace conversion I used to make ICC profiles work, just on LAB->sRGB. as far as I understand, OpenCV uses a fixed whitepoint of D65, resulting in yellow/warm conversions for some formats, but PIL may be able to figure out if D50 is needed??? if you have some crazy LUV or YPbPr or YIQ image that shows up wrong, please send it in and I'll see what I can do!

### boring rewrites and cleanup while doing file service work
* many more UI objects now store and do file service logic using a more complicated 'location context', which can store a mix of multiple services and 'deleted from service' data. all the search code that works on this can now propagate to display:
* the management objects behind every page now store a multiple location object, not a single file service id
* all media panels (the thumbnail grid on a page) are now instantiated by a multiple location object, and when they serve a highlighted downloader, they now inherit that from the file import options, which in future will dictate import destinations
* all canvases are now the same, inheriting their new location context from their parents
* all tag lists are the same. mostly they don't care much about file domain, but when you middle-click to create new pages from the autocomplete dropdown list or active search list, it can matter, so they now propagate it along
* the underlying medialist objects are now the same, and various delete logic (e.g. 'should we remove this thumb we just deleted?') is updated to work on complex domains
* some duplicate lookup code now works on location context
* renamed 'location search context' object to 'location context' since it is used all over now and put it in its own file. also wrote it some neater initialisation and meta object code
* mr bones now gives duplicate data based on the union of all non-trash local services sans update files (another case of now supporting n services but n is fixed for the moment at 1, 'my files')
* a bunch of places across the program that used to default to 'my files' or 'all local files' (which is everything on disk, including trash and repository update files) now default to this new union of all non-trash local media services
* when doing page-to-page file drag and drops, the location context is now preserved (previously, the new page would always be 'my files')
* whole heap of other cleanup in these systems
* when a thumbnail cannot be provided (for deleted files or many 'all known files' situations), the thumbnail cache now provides the hydrus icon stand-in instantly, no delayed waterfall
* fixed an unusual situation where the file search could not provide a file in a tagless search when that file had no detailed file info row in the database. this seems to effect a legacy borked row or two in the new deleted file domain searches
* removed some ancient dumper status code from thumbnail objects

## [Version 469](https://github.com/hydrusnetwork/hydrus/releases/tag/v469)

### misc
* the 'search log' button and the window panel now let you delete log entries. you can delete by completion status from the menu or specifically by row in the panel (just like the file log)
* fixed the new 'file is writable' checks for Linux/macOS, which were testing permissions overbroadly and messing with users with user-only permissions set. the code now hands off specific user/group negotiation to the OS. thanks to the maintainer of the AUR package for helping me out here (issue #1042)
* the various places where a file's permission bits are set are also cleaned up--hydrus now makes a distinction between double-checking a file is set user-writable before deleting/overwriting vs making a file's permission bits (which were potentially messed up in the past) 'nice' for human use after export. in the latter case, which still defaults to 644 on linux/macOS, the user's umask is now applied, so it should be 600 if you prefer that
* fixed a bug where the media viewer could have trouble initialising video when the player window instantiation was delayed (e.g. with embed button)

### client api
* added 'return_hashes' boolean parameter to GET /get_files/search_files, which makes the command return hashes instead of file ids. this is documented in the help and has a new unit test
* client api version is now 25

### multiple local file services work
* I rewrote a lot of code this week, but it proved more complex than I expected. I also discovered I'll have to switch the pages and canvases over too before I can nicely switch the top level UI over to allow multiple search. rather than release a borked feature, I decided not to rush the final phase, so this remains boring for now! the good news is that it works well when I hack it in, so I just need to keep pushing
* rewrote the caller side of tag autocomplete lookup to work on the new multiple file search domain
* rewrote the main database level tag lookup code to work on the new multiple file search domain
* certain types of complicated tag autocomplete lookup, particularly on all known tags and any client with lots of siblings, will be faster now
* an unusual and complicated too-expansive sibling lookup on autocomplete lookups on 'all known tags' is now fixed

### boring cleanup and refactoring
* predicate counts are now managed by a new object. predicates also support 0 minimum count for x-y count ranges, which is now possible when fetching count results from non-cross-referenced file domains (for now this means searching deleted files)
* cleaned up a ton of predicate instantiation code
* updated autocomplete, predicate, and pred count unit tests to handle the new objects and bug fixes
* wrote new classess to cover convenient multiple file search domain at the database level and updated a bunch of tag autocomplete search code to use it
* misc cleanup and refactoring for file domain search code
* purged more single file service inspection code from file search systems
* refactored most duplicate files storage code (about 70KB) to a new client db module

## [Version 468](https://github.com/hydrusnetwork/hydrus/releases/tag/v468)

### misc
* fixed an issue where the one pixel border on the new 'control bar' on the media viewer was annoyingly catching mouse events at the bottom of the screen when in borderless fullscreen mode (and hence dragging the video, not scanning video position). the animation scanbar now owns its own border and processes mouse events on it properly
* fixed a typo bug in the new pixel hash system that meant new imports were not being added to the system correctly. on update, all files affected will be fixed of bad data and scheduled for a pixel hash regen. sorry for the trouble, and thank you for the quick reports here
* added a 'fixed font size example' qss file to the install. I have passed this file to others as an example of a quick way to make the font (and essentially ui scale) larger. it has some help comments inside and is now always available. the default example font size is lmao
* fixed another type checking problem for (mostly Arch/AUR) PyQt5 users (issue #1033)
* wrote a new display mappings maintenance routine for the database menu that repopulates the display mappings cache for missing rows. this task will be radically faster than a full regen for some problems, but it only solves those problems
* on boot, the program now explicitly checks if any of the database files are set as read-only and if so will dump out with an appropriate error
* rewrote my various 'file size problem' exception hierarchy to clearly split 'the file import options disallow this big gif' vs 'this file is zero size/this file is malformed'. we've had several problems here recently, but file import options rule-breaking should set 'ignore' again, and import objects should be better about ignore vs fail state from now on
* added more error handling for broken image files. some will report cleaner errors, some will now import
* the new parsing system that discards source urls if they share a domain with a primary import url is now stricter--now discarding only if they share the same url class. the domain check was messing up saving post urls when they were parsed from an api url (issue #1036)
* the network engine no longer sends a Range header if it is expecting to pull html/json, just files. this fixes fetching pages from nijie.info (and several other server engines, it seems), which has some unusual access rules regarding Range and Accept-Encoding
* fixed a problem with no_daemons and the docker package server scripts (issue #1039)
* if the server engine (serverside or client api) is running a request during program shutdown, it now politely says 'Application is shutting down!' with a 503 rather than going bananas and dumping to log with an uncaught 500
* fixed some bad client db update error handling code

### multiple local file services (system predicate edition)
* system:file service now supports 'deleted' and 'petitioned' status
* advanced 'all known files' search pages now show more system predicates
* when inbox and archive are hidden because one has 0 count, and the search space is simple, system everything now says what they are, e.g. "system:everything (24) (all in inbox)"
* file repos' 'system:local/not local' now sort at the top of the system predicate list, like inbox/archive

### client api
* the GET /get_files/file_metadata call now returns the file modified date and imported/deleted timestamps for each file service the file is currently in or deleted from. check the help for an example!
* fixed client api file search with random sort (file_sort_type = 4)
* client api version is now 24

### boring multiple local file services work
* the system predicates listed in a search page dropdown now support the new 'multiple location search context' object, which means in future I will be able to switch over to 'file domain is union of (A, deleted from B, and C)' and all the numbers will add up appropriately with ranged 'x-y' counts and deal with combinations of file repo and local service and current/deleted neatly
* when fetching system preds in 'all known files', the system:everything 'num files' count will be stated if available in the cache
* for the new system:file service search, refactored db level file filtering to support all status types
* cleaned up how system preds are generated

### boring refactoring work
* moved GUGs from network domain code to their own file
* moved URL Class from network domain code to its own file
* moved the pure functions from network domain code to their own file
* cleared up some file maintenance enum variable names
* sped up random file sort for large result sets
* misc client network code cleanup and type hints, and rejiggered cleaner imports after the refactoring

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