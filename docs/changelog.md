---
title: Changelog
---

# changelog

!!! note
    This is the new changelog, only the most recent builds. For all versions, see the [old changelog](old_changelog.html).

## [Version 550](https://github.com/hydrusnetwork/hydrus/releases/tag/v550)

### misc

* if you enter invalid URLs (i.e. non-parsing) into 'manage URLs', the dialog now lets you know they were not apparently good and asks if you want to enter them anyway. previously, it errored-out and disallowed anything that wasn't parsing ok (issue #1444)
* when physically deleting files (i.e. deleting from trash or picking 'permanently delete' from the advanced delete dialog), the relevant files are now immediately removed from view. there were some situations where, when physically deleting a lot of files (causing the job to clear in batches), you could subsequently click on a soon-to-be-deleted file, loading it in mpv, and then, if you started a big UI-lag job like loading 'manage siblings', it could cause a crash if the file was deleted during the UI hang (issue #1447)
* the client now explicitly closes and clears its network connections after five minutes of inactivity. it turns out that the behind the scenes tools were not doing this exactly as I had thought, clogging up connection slots (issue #1458)
* thanks to a user, the rendering of palettized PNGs with ICC profiles is fixed!
* fixed the github build script to include the new-as-of-a-couple-of-weeks-ago 'auto_update_installer.bat' file in the Windows builds. sorry for the confusion here, I forgot I had to do this!
* optimised deselection of a large number of files when you already have a lot of thumbnails selected (a tricky example of this is clicking on an unselected file when you have a lot of files selected, thus deselecting all that old stuff). should be a little faster to work on big lists now
* further optimised reduction recalculation of the taglist in general

### thumbnail fill

* after vacillating and talking about it for months, I finally reworked how ''scale to fill' thumbnails work. as sometimes happens, I only had to change about six critical lines of code to get the core functionality changed and nothing seems to have exploded
* the main change here is KISS--'fill' thumbnail image files on disk are no longer clipped to just the viewable area, but the whole image scaled to fill the thumbnail space (with exceptions for extreme cases). this change gives us some simplicity and flexibility behind the scenes, saves some regeneration work when the user only changes one thumbnail dimension setting, improves maintenance tasks based off the thumbnail (like blurhash), and means that the Client API can fetch your thumbs and still have something useful to display
* if you have 'scale to fit' set, hydrus will regenerate your thumbnails naturally as you browse the client. fingers crossed, you won't notice any visual difference through the transition
* 'open externally' button panels now display their thumbnails with more reasonable maximum dimensions, and when things are gonk for whatever reason, they should nonetheless be centered correctly
* as a side thing, this change allowed me to finally purge all the clipping tech from the thumbnail pipeline, where it had obtusely sunk in to every possible filetype thumbgen

### eager login system

* I fixed a problem where some sorts of login script could allow a network job supposedly waiting on them to start before they had completed. it was due to a complicated 'am I logged in?' cookie testing issue while the login process was still working. all network jobs that hypothetically need a login now test if there is a login process currently working on their domain and will properly wait for that process to finish before they move on
* fixed a 'cannot log in' reporting bug in the login system
* some misc login code cleanup

### smarter orphan file record and repository update handling

* _this is advanced stuff, most users can ignore_
* _database->db maintenance->clear orphan file records_ is now able to recover file records where A) the file is in a service component but not the master, B) the file exists on disk. it copies the import timestamp from the specific to the umbrella domain and spams all the repaired files to a new page for user review. this maintenance routine isn't used all that much, but when you have a damaged database, it is nice to recover as much as possible rather than having to export (with clear orphan file records+clear orphan files) and then reimport and lose archive/inbox status and import timestamps
* repository update files now have a 'delete from repository updates' entry in their right-click menu
* this area of the code appears to be related to the PTR 404 issue some users have had (it seems to be repository update records not beeing added/deleted/updated correctly), so I am likely to revisit this
* deleting a file from 'all local files' (which happens for repository update files) now correctly updates the UI-level media object to recognise that the file is fully deleted from all local file domains beneath the umbrella, removing the 'delete from x' commands from their menu, and in the right view contexts removing them from view completely

## [Version 549](https://github.com/hydrusnetwork/hydrus/releases/tag/v549)

### misc

* optimised taglist sorting code, which is really groaning when it gets to 50k+ unique tags. the counting is more efficient now, but more work can be done
* optimised taglist internal update recalc by updating existing items in place instead of remove/replace and skipping cleanup-sort when no new items are added and/or the sort is not count-based. it should also preserve selection and focus stuff a bit better now
* thanks to a user, we have some new url classes to handle the recent change in sankaku URL format. your sank subscriptions are likely to go slightly crazy for a week as they figure out where they are caught up to, sorry!
* if a file copy into your temp directory fails due to 'Errno 28 No space left on device', the client now pops up more information about this specific problem, which is often a symptom of trying to import a 4GB drive into a ramdisk-hosted tempdir and similar. many Linux flavours relatedly have special rules about the max filesize in the tempdir!

### maintenance and processing

* _advanced users only, don't worry about it too much_
* the _options->maintenance and processing_ page has several advanced new settings. these are all separately hardcoded systems that I have merged into more of the same logic this week. the UI is a tower of spam, but it will serve us useful when we want to test and fine tune clients that are having various sorts of maintenance trouble
* a new section for potential duplicate search now duplicates the 'do search in idle time' setting you see in the duplicates page and has new 'work packet time' and 'rest time percentage' settings
* a new section for repository processing now exposes the similar 'work/rest' timings for 'normal', 'idle', and 'very idle' (after an hour of idle mode). **if I have been working with you on freezes or memory explosions during PTR processing, increase the rest percentages here to 50-2,000, let's see if that gives your client time to breathe and clean up old work**
* a new section for sibling/parent sync does the same, for 'idle', 'normal', and 'work hard' modes **same deal here probably**
* a new section for the deferred database table delete system does the same, for 'idle', 'normal', and 'work hard' modes
* I duplicated the 'do sibling/parent sync in idle/normal time' _tags_ menu settings to this options page. they are synced, so altering one updates the other
* if you change the 'run file maintenance jobs in idle/normal time' settings in the dialog, the _database_ menu now properly updates to reflect any changes
* the way these various systems calculate their rest time now smoothes out extreme bumps. sibling/parent display, in particular, should wait for a good amount of time after a big bump, but won't allow itself to wait for a crazy amount of time

### all deleted files

* fixed the various 'clear deletion record' commands to also remove from the 'all deleted files' service cache, which stores all your deleted files for all known specific file services and is used for various search tech on deleted file domains
* also wrote a command to completely regen this cache from original deletion records. it can be fired under _database->regenerate->all deleted files_. this will happen on update, to fix the above retroactively
* removed the foolish 'deleted from all deleted files' typo-entry from the advanced multiple file domain selector list. the value and use of a deletion record from a virtual combined deletion record is a complicated idea, and the entities that lurk in the shadows of the inverse sphere would strongly prefer that we not consider the matter any more

### running from source stuff

* **the setup_venv script has slightly different Qt questions this week, so if you have your own custom script that types the letters in for you, double-check what it is going to do before updating this week!**
* there's a new version of PySide6, 6.6.0. the `(t)est` Qt version in the 'setup_venv' now points to this. it seems fine to me on a fairly normal Win 11 machine, but if recent history is any guide, there's going to be a niggle somewhere. if you have been waiting for a fix on the menu position issue or anything else, give it a go! if things go well, I'll roll this into a larger 'future' test release and then we'll integrate it into main
* also, since Qt is the most test-heavy library we have, the 'setup_venv' scripts for all platforms now have an option to `(w)rite` your own version in!
* the program no longer needs `distutils`, and thus should now be compatible (or less incompatible, let's see, ha ha) with python 3.12. thanks for the user report and assistance here

### boring stuff

* rejiggered a couple of maintenance flows to spend less time aggressively chilling out doing nothing
* the hydrus timedelta widget can now handle milliseconds
* misc code cleaning
* fixed a typo in the thumbnail 'select->local/not local' descriptions/tooltips

## [Version 548](https://github.com/hydrusnetwork/hydrus/releases/tag/v548)

### user contributions

* thanks to a user, krita files are now renderable! we've got the defaults set like psds for now, where the preview viewer will show 'open externally', but the media viewer tries to load the full thing. let's see how it goes, and as always, if you have one that doesn't work, please send it in! note that krita are now eligible for the similar files system, so I've queued them up to get entered into it
* thanks to a user, setting an IPFS 'nocopy' path including your home directory (~) should now expand correctly (issue #1320)
* thanks to a user, newly-IPFS-pinned files are properly aware of their multihashes now (previously you needed a client restart or media reload after a delay) (issue #1328)
* thanks to a user, the url and hdd downloaders now have 'stop/abort' buttons, which will stop current work and cancel the rest of the queue. I added a yes/no dialog where you can choose to skip or delete the remainder of the queue and a couple of bells and whistles like disabling the button when the current queue has no remaining work

### misc

* fixed an issue with successive drag and drop file exports that gave different files the same filename. previously, the successive files were being replaced with the first instance with the shared name (basically the original files were not being 'overwritten'), but it should be fixed now!
* various places that were sorting services pseudorandomly now do so alphabetically (the F9 new page selector was doing this with local file domains (the first buttons in 'file search'), if you had multiple set up. sorry if I mess with your muscle memory here, but things should be more reliable here going forward!)
* added a first version of an auto-update script, `auto_update_installer.bat`, to the main install directory. it will download the latest Windows exe installer using winget and install it to the current location. if you use the installer, you might want to experiment with it (make a backup first!) as an easy hands-free update solution. let me know how it goes, and if there are no problems in a couple of weeks, I'll add it to the help
* added some more mpv error handling. if the mainloop behind your mpv window halts (which happens on various internal problems), we now detect it and more gracefully disable the viewer and its commands (previously it would escalate to error popups and try to keep working)
* fixed an issue in the newer 'missing file storage recovery' code if there is more than one base location missing

### thumbnail shortcuts

* I converted all the old hardcoded thumbnail keyboard shortcuts (thumbnail focus movement, open-media-viewer, and select-files) to the newer user-editable system under _file->shortcuts_, under a new set called 'thumbnails'. there are some new file-filters too, so you can set up 'select inbox' and similar beyond the default ctrl+a to 'select all' and escape to 'select none'
* I don't expect many people will want to even touch the giganto list of (shift+)(numpad)left/right/up/down/page up/page down/home/end selection combinations, but if you want to, you can!
* the thumbnails set also now allows 'launch the archive/delete filter', which had an odd home in 'media' before. new users now start with F12 set up in 'thumbnails', not 'media'
* I removed the jank semi-secret 'ctrl+space' hardcoded 'deselect current focused thumbnail' shortcut. that tech will probably return when I figure out more sensible logic and user settings around shift+ and ctrl+ behaviour
* this cleanup reduces three different shortcut handling routines down to one, and it particularly clears the last place where I was using ancient grandfathered wx-based 'accelerator table' tech. it should be easier to update the thumbnail shortcuts in future, and I hope to plug the mouse into it also, so you can edit middle-click to launch media etc..

### client api

* after much discussion and personal vacillating, I have decided to include the `version` and `hydrus_version` in every JSON Client API response. CBOR responses are not affected. if you need to hook into these numbers for a completely stateless interface, it is now super convenient. I'm not delighted with the spamminess of this, but it is just a handful of characters and it adds value for several situations, so I'm willing to try it out
* updated the documentation and unit tests regarding this
* the client api version is now 54

### boring stuff

* file filter objects are now serialisable
* application commands can now hold serialisable objects in their 'simple data' slot
* I made a new 'slightly more than simple' application command to hold a 'thumbnail move' that has both a direction and a selection status. I expect it will be expanded in future to handle ctrl+ selection and other logic preferences
* I made a new application command to hold the file filter. I just pre-populate the UI with a dropdown with commond choices for now, but in future it could hold a customisable file filter, once, ha ha, I have some UI to actually edit one!
* cleaned up various shortcut code
* misc linting cleanup

## [Version 547](https://github.com/hydrusnetwork/hydrus/releases/tag/v547)

### mpv crash fixes

* tl;dr: mpv less crashy now
* if mpv fails to load a file but not in an outright 'error' manner (this appears to mean a file using a rare format that a submodule of mpv can't handle), the client now recognises this has happened, either right after the first load, or, if the error takes longer to occur, a subsequent status interrogation, and makes several new steps to restore program stability: disconnecting the mpv window from all commands, freezing the scanbar, loading the default hydrus.png as emergency backstop, and making a popup to let the user know what just happened. previously, Qt would get rapidly unhappy as it asked things to draw on screen over the null-state player, particularly if you show/hid the scanbar several times, and it would, if not removed promptly from screen, typically lead to a program crash
* furthermore, the scanbar now never interrogates the mpv window during its paint event. a mysterious interaction of C++ level objects during error state was causing the underlying instability here, and now I cannot reproduce this even if I try
* I also hardened the mpv window's 'no-media' state. now, rather than showing 'nothing' when media is unloaded, each mpv player now actually idles on a black png lol
* this tech will kick in for more extreme file failures, too, which have a different handler but seem to give the same detectable dump-out state
* fixed a silent-but-for-debug-mode error while destroying damaged mpv windows right when the program is terminating

### misc

* thanks to a user, we now have import support for 'djvu' files. basically an open source PDF style format
* fixed pasting an image into 'system:similar files', which I missed updating in last week's code cleanup!
* a light but spammy legacy job that refreshed every search page's empty autocomplete every five minutes (to get updated system predicates/numbers) now only occurs to autocompletes on the current page. relatedly, when you switch to a search page you haven't looked at in five minutes, it triggers the same update immediately. this should save a tiny bit of idle CPU time and, more importantly, clear out the background job queue on larger-session clients
* I _think_ I fixed some instances of the media viewer notes window initialising with a gigantic width on some OSes. if you often get a super wide notes window when you first open the media viewer, with it fixing itself when you cycle to a different file and back, let me know if things are any better
* when you have a popup message that has a 'show x files' button, usually from a subscription, that routine now excludes files that have been deleted since the button was created. it updates its existing file count on a click, also, to how many files it actually will generate. if you click one of these buttons, delete some files, and then click it again, it should no longer produce ghost files in the new search page. I'm going to add some more tech to optionally handle the system:hash predicate in a page in similar ways, 'locking' it to the current page content and preserving file sort so it works nice with 'remove files' etc..
* fixed a stupid typo that was swapping the 'allow non-local connections' server setting when making the interface for IPv6 hosts. there is a secondary check of all client IPs on every request, so I am confident this was not enabling non-local connections when undesired on IPv6, but it was disabling them by deploying the loopback interface when they should have been allowed! sorry for the trouble, and well done to the person who noticed this
* while pursing an odd and rare problem where a download job can start even though it should be waiting on a login process, I cleaned some of the login code and logic, lowering the timeout for session cookie expiring from 60 to 45 minutes and smoothing out some confusing status-checking in the pre-login stage. I could never reproduce the problem, though, so if you have had this issue, please let me know more and I'll see if I can reproduce this reliably

### simple cleanup

* cleaned up some filetype parsing code that was getting a little messy, also reduced some overhead
* unified the thumbnail/file filetype parsing a little, with better fallback states when a hydrus thumbnail happens for some reason not to be a jpeg or png
* fixed an out of date menu reference in the 'help my media files are broke.txt' document. 'clear orphan files' is under 'file maintenance' now, not 'db maintenance'

## [Version 546](https://github.com/hydrusnetwork/hydrus/releases/tag/v546)

### misc

* fixed the recent messed up colours in PSD thumbnail generation. I enthusiastically 'fixed' a problem with greyscale PSD thumbs at the last minute last week and accidentally swapped the RGB colour channels on coloured ones. I changed the badly named method that caused this mixup, and all existing PSD thumbs will be regenerated (issue #1448)
* fixed up some borked button-enabling and status-displaying logic in the file history chart. the cancel process should work properly on repeat now
* made two logical fixes to the archive count in the new file history chart when you have a specific search--archive times for files you deleted are now included properly, and files that are not eligible for archiving are discluded from the initial count. this _should_ make the inbox and archive lines, which were often way too high during specific searches, a little better behaved. let me know what you see!
* added a checkbox to _options->thumbnails_ to turn off the new blurhash thumbnail fallback
* 'this has exif data, the other does not' statements are now calculated from cached knowledge--loading pairs in the duplicate filter should be faster now
* some larger image files with clever metadata should import just a little faster now
* if the process isn't explicitly frozen into an executable or a macOS App, it is now considered 'running from source'. various unusual 'running from source' modes (e.g. booting from various scripts that mess with argv) should now be recognised better

### boring code cleanup

* moved 'recent tags' code to a new client db module
* moved ratings code to a new client db module
* moved some db integrity checking code to the db maintenance module
* moved the orphan table checking code to the db maintenance module
* fixed the orphan table checking code, which was under-detecting orphan tables
* moved some final references to sibling/parent tables from main db method to sibling and parent modules
* moved most of the image metadata functions (exif, icc profile, human-readable, subsampling, quantization quality estimate) to a new `HydrusImageMetadata` file
* moved the new blurhash methods to a new `HydrusBlurhash` file
* moved various normalisation routines to a new `HydrusImageNormalisation` file
* moved various channel scanning and adjusting code to a new `HydrusImageColours` file
* moved the hydrus image files to the new 'hydrus.core.images' module
* cleaned up some image loading code
* deleted ancient and no-longer-used client db code regarding imageboard definitions, status texts, and more
* removed the ancient `OPENCV_OK` fallback code, which was only used, superfluously, in a couple of final places. OpenCV is not optional to run hydrus, server or client

## [Version 545](https://github.com/hydrusnetwork/hydrus/releases/tag/v545)

### blurhash

* thanks to a user's work, hydrus now calculates the [blurhash](https://blurha.sh/) of files with a thumbnail! (issue #394)
* if a file has no thumbnail but does have a blurhash (e.g. missing files, or files you previously deleted and are looking at in a clever view), it now presents a thumbnail generated from that blurhash
* all existing thumbnail-having files are scheduled for a blurhash calculation (this is a new job in the file maintenance system). if you have hundreds of thousands of files, expect it to take a couple of weeks/months to clear. if you need to hurry this along, the queue is under _database->file maintenance_
* any time a file's thumbnail changes, the blurhash is scheduled for a regen
* for this first version, the blurhash is very small and simple, either 15 or 16 cells for ~34 bytes. if we end up using it a lot somewhere, I'd be open to making a size setting so you can set 8x8 or higher grids for actually decent blur-thumbs
* a new _help->debug_ report mode switches to blurhashes instead of normal thumbs

### file history search

* I did to the file history chart (_help->view file history_) what I did to mr bones a couple weeks ago. you can now search your history of imports, archives, and deletes for creator x, filetype y, or any other search you can think of
* I hacked this all together right at the end of my week, so please bear with me if there are bugs or dumb permitted domains/results. the default action when you first open it up should all work the same way as before, no worries™, but let me know how you get on and I'll fix it!
* there's more to do here. we'll want a hideable search panel, a widget to control the resolution of the chart (currently fixed at 7680 to look good blown up on a 4k), and it'd be nice to have a selectable date range
* in the longer term future, it'd be nice to have more lines of data and that chart tech you see on financial sites where it shows you the current value where your mouse is

### client api

* the `file_metadata` call now says the new blurhash. if you pipe it into a blurhash library and blow it up to an appopriate ratio canvas, it _should_ just work. the typical use is as a placeholder while you wait for thumbs/files to download
* a new `include_blurhash` parameter will include the blurhash when `only_return_basic_information` is true
* `file_metadata` also shows the file's `pixel_hash` now. the algorithm here is proprietary to hydrus, but you can throw it into 'system:similar files' to find pixel dupes. I expect to add perceptual hashes too
* the help is updated to talk about this
* I updated the unit tests to deal with this
* the error when the api fails to parse the client api header is now a properly handled 400 (previously it was falling to the 500 backstop)
* the client api version is now 53

### misc

* I'm sorry to say I'm removing the Deviant Art artist search and login script for all new users, since they are both broken. DA have been killing their nice old API in pieces, and they finally took down the old artist gallery fetch. :(. there may be a way to finagle-parse their new phone-friendly, live-loading, cloud-deployed engine, but when I look at it, it seems like a much bigger mess than hydrus's parsing system can happily handle atm. the 'correct' way to programatically parse DA is through their new OAuth API, which we simply do not support. individual page URLs seem to still work, but I expect them to go soon too. Sorry folks, try gallery-dl for now--they have a robust OAuth solution
* thanks to a user, we now have 'epub' ebook support! no 'num_words' support yet, but it looks like epubs are really just zips with some weird metadata files and a bunch of html inside, so I think this'll be doable with a future hacky parser. all your existing zip files wil be scheduled for a metadata rescan to see if they are actually epubs (this'll capture any secret kritas and procreates, too, I think)
* the main UI-level media object is now aware of a file's pixel hash. this is now used in the duplicate filter's 'these are pixel duplicates' statements to save CPU. the jank old on-the-fly calculation code is all removed now, and if these values are missing from the media object, a message will now be shown saying the pixel dupe status could not be determined. we have had multiple rounds of regen over the past year and thus almost all clients have full database data here, so fingers crossed we won't see this error state much if at all, but let me know if you do and I'll figure out a button to accelerate the fix
* the thumbnail _right-click->open->similar files_ menu now has an entry for 'open the selection in a new duplicate filter page', letting you quickly resolve the duplicates that involve the selected files
* pixel hash and blurhash are now listed, with the actual hash value, in the _share->copy->hash_ thumbnail right-click menu
* thanks to a user, 'MPO' jpegs (some weird multi-picture jpeg that we can't page through yet) now parse their EXIF correctly and should rotate on a metadata-reparse. since these are rare, I'm not going to schedule a rescan over everyone's jpegs, but if you see a jpeg that is rotated wrong, try hitting _manage->regenerate->file metadata_ on its thumbnail menu
* I may have fixed a rare hang when highlighting a downloader/watcher during very busy network time that involves that includes that importer
* added a warning to the 'getting started with installing' and 'database migration' help about running the SQLite database off a compressed filesystem--don't do it!
* fixed thumbnail generation for greyspace PSDs (and perhaps some others)

### boring cleanup

* I cleaned some code and added some tests around the new blurhash tech and thumbs in general
* a variety of metadata changes such as 'has exif', 'has icc profile' now trigger a live update on thumbnails currently loaded into the UI
* cleaned up some old file metadata loading code
* re-sorted the job list dropdown in the file maintenance dialog
* some file maintenance database work should be a bit faster
* fixed some behind the scenes stuff when the file history chart has no file info to show

## [Version 544](https://github.com/hydrusnetwork/hydrus/releases/tag/v544)

### webp vulnerability

* the main webp library (libwebp) that many programs use for webp support had a remote execution (very bad) vulnerability. you probably noticed your chrome/firefox updated this week, which was fixing this. we use the same thing via the `Pillow` library, which also rolled out a fix. I'm not sure how vulnerable hydrus ever was, since we are usually jank about how we do anything, but best to be safe about these things. there were apparently exploits for this floating around
* the builds today have the fix, so if you use them, update as normal and you are good
* if you run from source, **rebuild your venv at your earliest convenience**, and you'll get the new version of Pillow and be good. note, if you use the advanced setup, that there is a new question about `Pillow`
* unfortunately, Windows 7 users (or anyone else running from source on Python 3.7) cannot get the fix! it needs Pillow 10.0.1, which is >=Python 3.8. it seems many large programs are dropping support for Win 7 this year, so while I will continue to support it for a reasonable while longer, I think the train may be running out of track bros

### max size in file storage system

* the `migrate database` dialog now allows you to set a 'max size' for all but one of your media locations. if you have a 500GB drive you want to store some stuff on, you no longer have to balance the weights in your head--just set a max size of 450GB and hydrus will figure it out for you. it is not super precise (and it isn't healthy to fill drives up to 98% anyway), so make sure you leave some padding
* also, please note that this will not automatically rebalance _yet_. right now, the only way files move between locations is through the 'move files now' button on the dialog, so if you have a location that is full up according to its max size rule and then spend a month importing many files, it will go over its limit until and unless you revisit 'migrate database' and move files again. I hope to have automatic background rebalancing in the near future
* updated the 'database migration' help to talk about this and added a new migration example
* the 'edit num bytes' widget now supports terabytes (TB)
* I fleshed out the logic and fixed several bugs in the migration code, mostly to do with the new max size stuff and distributing weights appropriately in various situations

### misc

* when an image file fails to render in the media viewer, it now draws a bordered box with a brief 'failed to render' note. previously, it janked with a second of lag, made some popups, and left the display on eternal blank hang. now it finishes its job cleanly and returns a 'nah m8' 'image' result
* I reworked the Mr Bones layout a bit. the search is now on the left, and the rows of the main count table are separated for readability
* it turns out that bitmap (.bmp) files can support ICC Profiles, so I've told hydrus to look for them in new bitmaps and retroactively scan all your existing ones
* fixed an issue with the recent PSD code updates that was breaking boot for clients running from source without the psd-tools library (this affected the Docker build)
* updated all the 'setup_venv' scripts. all the formatting and text has had a pass, and there is now a question on (n)ew or (old) Pillow
* to stop FFMPEG's false positives where it can think a txt file is an mpeg, the main hydrus filetype scanning routine will no longer send files with common text extensions to ffmpeg. if you do have an mp3 called music.txt, rename it before import!
* thanks to a user, the inkbunny file page parser fetches the correct source time again (#1431)
* thanks to a user, the old sankaku gallery parser can find the 'next page' again
* removed the broken sankaku login script for new users. I recommend people move to Hydrus Companion for all tricky login situations (#1435)
* thanks to a user, procreate file parsing, which had the width/height flipped, is fixed. all existing procreate files will regen their metadata and thumbs

### client api

* thanks to a user, the Client API now has a `/get_files/render` command, which gives you a 100% zoom png render of the given file. useful if you want to display a PSD on a web page!
* I screwed up Mr Bones's Client API request last week. this is now fixed
* Mr Bones now supports a full file search context on the Client API, just like the main UI now. same parameters as `/get_files/search_files`, the help talks about it. He also cancels his work early if the request is terminated
* Mr Bones gets several new unit tests to guarantee long-term ride reliability
* the Client API (and all hydrus servers) now return proper JSON on an error. there's the error summary, specific exception name, and http status code. the big bad 500-error-of-last-resort still tacks on the large serverside traceback to the summary, so we'll see if that is still annoying and split it off if needed
* the new `/add_tags/get_siblings_and_parents` now properly cleans the tags you give it, trimming whitespace and lowercasing letters and so on
* the client api version is now 52

## [Version 543](https://github.com/hydrusnetwork/hydrus/releases/tag/v543)

### misc

* a new string converter rule now allows for extremely easy date parsing, thanks to the `dateparser` library. all old 'datestring to timestamp' rules remain as they are, but are now called '(advanced)'. a new option, 'datestring to timestamp (easy)', which has exactly zero variables to fiddle with, just eats up pretty much any date string you can think of, including timezone conversions, and even stuff like '2 hours ago'. you need the dateparser library for this to work, so **if you run from source, you might like to rebuild your venv this week**. your `dateparser` import status is in _help->about_
* thanks to the user who added it recently, PSD rendering is now much faster and uses less memory. if you do a lot of PSD work, let me know how this goes. if PSDs now load pretty much like large pngs, I think we'll set them, by default, to show as normal in the preview viewer
* thanks to a user, we now have description note parsing for the default e621 downloader
* the program now supports bitmap files as-is. until now, I automatically converted them to png on import, but this was a mistake--despite this file format being a waste 99.7% of the time, hydrus's philosophy is not to alter files on import, and this long-time exception resulted in several awkward bumps in the code that I'm happy to be rid of now
* fixed a couple desync bugs in the migrate database dialog where you could change a location's weight (particularly between 0 and 1) and not get the correct flip of the 'files need to be moved'/'files are all good' state until you re-opened the dialog

### PDFs

* I screwed something up with the PDF thumbnail generation at the last minute last week, fixing it on non-PySide6, but introducing some logspam and--for at least one user--adding instability. the logspam is now gone and I _believe_ the instability is fixed. now it is basically the same as the SVG thumbnail code, which hasn't given us any trouble. if we still see some crashes, I'm going to have to overhaul these two thumbnail generation methods
* when PDFs fail to generate thumbs, a little text about the error is now printed to the log
* _help->about_ now has lines for QtCharts and QtPdf, and if there is a PDF problem, it puts the import trace in a popup

### mr bones

* mr bones can now take any file search. if you want to see the average filesize of your pngs, or the archive/inbox ratio of creator x's webms, just set that search on the new panel and the numbers will update for that subset
* this turned, characteristically, into a bottomless rabbit hole, and I culled the more complicated features lest the ride consume me. searching a multiple file domain means deleted numbers cannot be calculated, nor can the 'earliest import' time, and searching deleted domains will generally give you some gonk numbers (and likely reveal some interesting legacy bugs, like inbox count amongst deleted files)
* the old search was highly optimised, but this has few guard rails. if you give this thing a super difficult query, it'll take a long time. there is now a cancel button that should interrupt all but the weirdest operations fairly promptly, however, just in case it is really lagging. note that hitting 'searching immediately' will pause updates as normal, if you need to set up something complex
* assuming deleted numbers are available, the stats now include total views/viewtime for deleted files too
* potential dupe counts are basically a search of 'at least one of the files matches the file list, can be pixel dupes, max distance 8'

### more boring work, file storage and misc

* wrote a new object to handle the base storage location for file/thumbnail subfolders. it can do over/underweight calculations and handles the pending max_num_bytes setting for database migration locations
* all the new subfolder objects now track their base location using this new object, and all related load/save/display/edit code is now throwing this thing around instead of raw paths
* the underlying migration determination code is now ready to redistribute according to a max_num_bytes option. I've just got to update the UI, and, fingers crossed, I'll be able to add it next week
* added a bunch of unit tests for the new base storage location object. it separately reports whether it needs to shrink, wants to shrink, is able to expand, or is eager to expand
* improved how updated objects are substituted into all multi-column lists, it fixes a couple of odd storage/display sync bugs here and there
* a core image data loading/conversion tool inside the program is now a bit simpler and faster, and I think it also saves memory. it should speed up various sorts of unusual file loading

## [Version 542](https://github.com/hydrusnetwork/hydrus/releases/tag/v542)

### pdfs

* thanks to a user, we now have pdf thumbnails! there is surprisingly little jank!
* I hacked together a newer and better word count for PDFs. I can't promise it is perfect, but it does actually inspect the raw text. I'm expect we'll add a separate 'num_pages' row in future to handle comics (and other stuff like cbr/cbz)
* I also hacked in 'human-readable file metadata' for PDFs. any PDF with author, title, subject, or keywords metadata is now viewable at the top of the media viewer
* on update all your existing pdfs will be scheduled to get new thumbs, count their words, and learn if they have human-readable file metadata
* this tech relies on Qt, so users running from source on old OSes (and thus Qt5) may not have very good support, sorry!

### predicate parsing

* the system predicate parser can now deal with numbers with commas, like in `system:width = 1,920`
* `system:filetype is gif` works again in the predicate parser, now resolving to `system:filetype is animated gif, static gif`
* fixed some weird parsing for 'system:tag as number' and added more operators like 'less than' and support for 'unnamespaced' and 'any namespace'
* `system:tag as number` now labels itself in the client in the style `system:tag as number: page less than 20`, which is parseable by the system
* the predicates for 'has exif/icc profile/human-readable embedded metadata' now label themselves in the format `system:has x`, not `system:image has x`. this harmonises with our other `has x` predicates, recognises that we pull metadata from non-images these days, and is the text that they were parsing with anyway

### misc

* the 'exporting' sidecar system's 'tag' source (i.e. pulling tags from your local tag services) now has a button to select 'storage' (no siblings or parents, what you see in manage tags dialog) or 'display' (has sibling and parent calculations, what you see in normal views) tags. all existing tag source sidecars will stay 'storage', but the default for new ones is now 'display'
* renamed the dumb 'x metadata migrations' button label in export files to 'x sidecar actions'
* wrote a new FAQ answer about why tags don't disappear when you delete files: https://hydrusnetwork.github.io/hydrus/faq.html#service_isolation
* also wrote just a little FAQ about running hydrus off an encrypted partition--yes you can, and this is good tech to learn
* moved the builds up to python 3.10. I thought we had already done this, but there we go. no special install instructions, it should just update as normal
* for users who run from source: added a '(m)iddle Qt6' selection to the advanced setup venv script, for those who cannot run 6.5.2, with some explanation about it (it is the recently used 6.4.1, since Python 3.11 can't run the '(o)lder' 6.3.1), and added a '(t)est mpv' option for the newer python-mpv 1.0.4

### boring file storage work

* I decided that the planned granular folders will nest in groups of 2 hex characters. when you move to three-character storage, the files starting 'ab1' will be stored in '/fab/1' directory (rather than '/fab1'). we don't want to solve the overhead of a folder with 30,000 files by creating a folder with 4096 or 65536 folders. all the code was shifted over to this
* all the migrate and repair code now uses subfolders
* replaced various hardcoded folder determination code with subfolders, ensuring we are all calculating locations using the same single method
* a variety of other responsibilities like 'does this subfolder exist on disk?' and 'make sure it does exist' are similarly now all collected in one place, in the subfolder code
* added a little suite of unit tests for the new subfolders class
* did a bunch of renaming to clear up various different concepts and names in all this code
* the 'clear' custom thumbnail location button in migrate database is now wrapped in a yes/no confirmation dialog

### other boring stuff

* wrote some new exception classes to handle several 'limited support for this particular file' states and refactored a bunch of the resolution and thumbnail producing code to use it instead of None hacks or 'this file is completely busted' exceptions
* improved some misc file format handling, particularly when they are damaged. stuff like clip database inspection and general thumbnail generation fail states
* refactored many of my hardcoded special unicode characters to constants in HC. not sure I really like all the spammed `{HC.UNICODE_ELLIPSIS}` though, so might revisit
* fixed an issue with last week's update code that was affecting users with a history of certain database damage
* I may have improved import support for some damaged or generally very strange image files by falling back to OpenCV for resolution parsing when Pillow fails

## [Version 541](https://github.com/hydrusnetwork/hydrus/releases/tag/v541)

### misc

* fixed the gallery downloader and thread watcher loading with the 'clear highlight' button enabled despite there being nothing currently highlighted
* to fix the darkmode tooltips on the new Qt 6.5.2 on Windows (the text is stuck on a dark grey, which is unreadable in darkmodes), all the default darkmode styles now have an 'alternate-tooltip-colour' variant, which swaps out the tooltip background colour for the much brighter normal widget text colour
* rewrote the apng parser to work much faster on large files. someone encountered a 200MB giga apng that locked up the client for minutes. now it takes a second or two (unfortunately it looks like that huge apng breaks mpv, but there we go)
* the 'media' options page has two new checkboxes--'hide uninteresting import/modified times'--which allow you to turn off the media viewer behaivour where import and modified times similar to the 'added to my files xxx days ago' are hidden
* reworked the layout of the 'media' options page. everything is in sections now and re-ordered a bit
* the 'other file is a pixel-for-pixel duplicate png!' statements will now only show if the complement is a jpeg, gif, or webp. this statement isn't so appropriate for formats like PSD
* a variety of tricky tags like `:>=` are now searchable in normal autocomplete lookup. a test that determined whether to use a slower but more capable search was misfiring
* the client api key editing window has a new 'check all permissions' button
* fixed the updates I made last week to the missing-master-file-id recovery system. I made a stupid typo and didn't test it properly, fixed now. sorry for the trouble!
* thanks to a user, the help has a bunch of updated screenshots and fixed references to old concepts
* did a little more reformatting and cleanup of 'getting started with downloading' help document and added a short section on note import options
* cleaned up some of the syntax in our various batch files. fingers crossed, the setup_venv.bat script will absolutely retain the trailing space after its questions now, no matter what whitespace my IDE and github want to trim

### string joiner

* the parsing system has a new String Processor object--the 'String Joiner'. this is a simple concatenator that takes the list of strings and joins them together. it has two variables: what joining text to use, e.g. ', ', or '-', or empty string '' for simple concatenation; and an optional 'group size', which lets you join every two or three or n strings in 1-2-3, 1-2-3, 1-2-3 style patterns

### new file types

* thanks to a user; we now have support for QOI (a png-like lossless image type) and procreate (Apple image project file) files. the former has full support; the latter has thumbnails
* QOI needs Pillow 9.5 at least, so if you are on a super old 'running from source' version, try rebuilding your venv; or cope with you QOI-lessness

### client api

* thanks to a user, we now have `/add_tags/get_siblings_and_parents`, which, given a set of tags, shows their sibling and parent display rules for each service
* I wrote some help and unit tests for this
* client api version is now 51

### file storage (mostly boring)

* the file storage system is creaky and ugly to use. I have prepped some longer-term upgrades, mostly by writing new tools and cleaning and reworking existing code. I am nowhere near to done, but I'd like us to have four new features in the nearish future: 
  - dynamic-length subfolders (where instead of a fixed set of 256 x00-xff folders, we can bump up to 4096 x000-xfff, and beyond, based on total number of files)
  - setting fixed space limits on particular database locations (e.g. 'no more than 200GB of files here') to complement the current weight system
  - permitting multiple valid locations for a particular subfolder prefix
  - slow per-file background migration between valid subfolders, rather than the giganto folder-atomic program-blocking 'move files now' button in database maintenance
* so, it is pretty boring so far, but I did the following: 
* wrote a new class to handle a specific file storage subfolder and spammed it everywhere, replacing previous location and prefix juggling
* wrote some new tools to scan and check the coverage of multiple locations and dynamic-length subfolders
* rewrote the file location database initialisation, storage, testing, updating, and repair to support multiple valid locations
* updated the database to hold 'max num bytes' per file storage location
* the feature to migrate the SQLite database files and then restart is removed from the 'migrate database' dialog. it was always ultrajank in a place that really shouldn't be, and it was completely user-unfriendly. just move things manually, while the client is closed
* the old 'recover and merge surplus database locations into the correct position' side feature in 'move files now' is removed. it was always a little jank, was very rarely actually helpful, and had zero reporting. it will return in the new system as a better one-shot maintenance job
* touched up the migrated database help a little
