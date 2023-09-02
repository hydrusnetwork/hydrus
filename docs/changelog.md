---
title: Changelog
---

# changelog

!!! note
    This is the new changelog, only the most recent builds. For all versions, see the [old changelog](old_changelog.html).

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

## [Version 540](https://github.com/hydrusnetwork/hydrus/releases/tag/v540)

### misc

* the system predicate parser can now handle 'system:filetype is xxx' for more of the general human-friendly filetype strings like 'video' and 'mkv'. it can also handle 'static gif' and any other types with spaces but now enforces commas between each filetype. I think all system:filetype predicate strings the client produces now parse correctly if you paste them back
* fixed many bitmap imports, most typically in the 'system:similar files' system, which was not generating pixel hashes correctly. most/all bitmaps coming in with alpha channels, or, I also believe, with a null channel (RGB32), were being handled wrong and coming out BGR. perceptual hashes are greyscale and were not affected, but pixel hashes were wrong. this was a real pain to figure out, and it may be that it is still broken for users on big-endian systems or something, so let me know how you get on
* added links to https://github.com/abtalerico/wd-hydrus-tagger (danbooru-trained model tagging) and https://github.com/Garbevoir/wd-e621-hydrus-tagger (which adds more models) to the client api help. reports are that they work well, even on 'normal' pictures
* the bad darkmode tooltip text colour in the new Qt 6.5.2 on Windows appears to be a bug, here: https://bugreports.qt.io/browse/QTBUG-116021 . there's not a great answer here, so let me know your thoughts. if you like, you can edit a custom stylesheet with a different `QToolTip` `background-color`, or I can spam some alternate fixed QSS files for everyone, or we can wait for a fix on Qt's end
* on update, all existing PSD and static gif files will be scheduled for pixel hash regen, perceptual hash regen, and entry into the similar files system (I forgot to do this last week)
* on update, all existing PNGs will be scheduled for pixel duplicate data regen. we have a legacy alpha channel issue here that has reared its head several times (searchting for 'must not be pixel dupes', but getting pixel dupes), so I am just going to bosh it on the head for everyone

### file maintenance

* if a file has multiple jobs pending, the file maintenance manager now processes all those jobs at once, saving significant disk I/O. also, a couple things like the 'do all work' button's popup now shows the total number of jobs to do, rather than that of each job type in turn
* the 'manage scheduled jobs' file maintenance panel now shows the count for jobs that exist but are not yet due. previously, these were hidden, which was part of the mkv/webm duplicate difficulties last week.
* when the program needs to rename a file because it has a new mime, it now first tests if the file is still in use (normally this means some file parsing component like ffmpeg or opencv is still cleaning up OS file handles or whatever), and, if so, waits just a little bit before trying
* relatedly, the 'try and delete the rename-dupe again' job now tries again in one hour, rather than one week in the future, and if that after-one-hour job fails again (this would usually be because you were actually viewing the original file in the media viewer at the time of its reparse), then that job will retry again in a week, and the week after if that fails, and again after that, etc... for about a year
* fixed an issue with the thumbnail resizing maintenance job on PSD files and probably some other weird types too
* fixed some scheduling issues in how the mainloop of the file maintenance system tests its current rate of work and when it should cancel a current batch of work

### boring stuff

* simplified and cleaned up some of the duplicate system king-fetching code. I _may_ have also fixed one instance of pair representatives being fetched wrong for the filter when 'at least one file has to match the one search'
* when editing the duplicate action merge options, a new label at the top says which dupe action you are editing for, and if it isn't "this is better", it notes that the available merge actions are limited
* improved four things with the recovery code that handles missing master hash definitions--first, the substitute hashes are now the correct length; second, they are now saved back to the database, which should stop issues like the "trying to delete a thing that doesn't exist and has an ever-changing name in a loop forever" bug; third, the popup tells the user what to do next, and more information is written to the log; and fourth, the client checks the local hash cache so see if it can automatically recover the missing data

### client api

* the `file_metadata` call now has two new fields, `filetype_human`, which looks like 'jpeg' or 'webm', and `filetype_enum`, which uses internal hydrus filetype numbers
* the help and unit tests are updated for this
* client api version is now 50

## [Version 539](https://github.com/hydrusnetwork/hydrus/releases/tag/v539)

### another new library today

* **if you run from source, I recommend you rebuild your venv today. we've got another library to add full PSD support**

### viewable PSD files

* thanks to a user, hydrus can now view PSD files in the main viewer, just like any other file. it can be a bit slow to load, and you can't show/hide away layers or anything, but for simply showing the image as-is, it works great
* because this needs more CPU than for normal images, we're starting out with conservative view settings. while PSD files will show as normal in the media viewer, they'll only show the 'open externally' button in the preview viewer. see how it works for you, and remember you can change it under _options->media_. if there isn't any real problem IRL with showing even big PSDs everywhere, I'll change the defaults, so let's see how it goes
* and of course if you have a borked PSD--say one that shows up in all the wrong colours, or has bad transparency--please send it in and I'll have a look. there is apparently a rare class of PSD files that simply won't render at all with our new system, and hydrus is pretty bad at handling that situation, so that'd also be useful if at the very least to get me to write some better error handling code
* just like last week, if you run from source, please rebuild your venv again today--there's a PSD-handling library that supports all this
* all PSD files will be scheduled for a thumbnail regen on update

### static vs animated gif

* the program now treats still and animated gifs as separate file types for the purpose of searching and selecting display options (previously, static gifs were just animated gifs with no duration). most people won't have many static gifs, so this doesn't matter too much, but it cleans up our image/animation filetype group distinction and makes a bunch of behind the scenes stuff simpler. all your gifs will be set to either camp on update
* if you have an existing file import options or system:filetype that looked for gifs specifically, it will now search for 'animated gifs' only, so watch out if you need 'static gif' too/instead

### parseable rating predicates

* the system predicate parser (including the Client API) now accepts system:rating predicates. type 'system:has rating (service name)' or 'system:rating for (service name) > 4/5' or other reasonable variants and it should pre-fill
* in the UI, the system 'has/no rating' predicate strings are now in the format 'has a rating for (service name)' and 'does not have a rating for (service name)'. (previously it was 'has/no (service name) rating', which is out of step with our usual syntax and generally unhelpfully parsing-ambiguous)
* added a bunch of unit tests for this

### misc

* fixed the 'network timeout' setting under _options->connection_, which was not saving changes
* the media viewer top hover window now enables/disables the 'show file metadata' button--rather than shows/hides--in order to stop the buttons on the left jumping around so much when you scroll through media
* the duplicate filter's always-on-top right-hand window is fixed in place again. the buttons won't jump around any more. if the notes hover grows to overlap it, it won't show over it as long as your mouse is over the duplicate hover. this should make clicking those duplicate buttons on note-heavy files far less frustrating. sorry for the late fix here!
* the duplicate filter now always presents a statement on the pair's filetypes, even if they are the same (it'll say like 'both are pngs'). this is to help catch the upcoming PSD matches (where you probably do not want to delete either) and other weirdness as we add new filetypes
* just a small thing, but the 'management panel' labels are renamed broadly to 'sidebar' under the _pages_ menu. the panel on the left of pages is now called 'sidebar', and the wx-era 'sash' wording is gone
* there's an issue with the file metadata reparse system right now where, on a filetype change, it will often fail to cleanly rename bigger files (e.g. from x.mkv to x.webm). the result is the file copies and the old one is never deleted, leaving a duplicate that is not properly cleared up later. on update this week, I am scheduling a fresh cleanup for these dupes. if, like me, you have a lot of large AV1-encoded vidya capture mkvs, you may have noticed your hydrus folders suddenly bloated in size this past week--this should be 99% fixed soon. I will fix the underlying issue here next week
* touched up the 'running from source' help and 'setup_venv' texts in general and specifically regarding some new version info stuff. it looks like macOS <= 10.15 can't handle last week's new Qt6 version, and some versions of Linux need `libicu-dev` and `libxcb-cursor-dev` installed via apt or otherwise
* fixed the file query sort-and-clip method when you are set to sort by file hash and also have system:limit, and fixed it for asc/desc too
* for the second time, fixed the 'import QtSVG' error on hydrus server install when the client requirements.txt had not been run. turns out I messed up the 'proper' fix I did for the first time

### boring cleanup

* refactored a bunch of HydrusImageHandling code to HydrusAnimationHandling
* cleaned up several of our enums and enum testing, and cleared out several hardcoded hooks to deal with different kinds of gif
* did some similar enum cleaning and `gif`->`PILAnimation` renaming to encompass the new HEIF sequences
* streamlined the image and animation metadata parsing methods significantly
* a bunch of simple `image`->`animation` renames, like IMAGE_APNG is now ANIMATION_APNG
* cleaned up some other confusing code handles for 'image' vs 'static image', to handle whether we are talking about strictly images or viewable raster image-likes (for now including PSD files) but I think it'll need more work
* deleted some ancient and no longer used imageboard profile code

## [Version 538](https://github.com/hydrusnetwork/hydrus/releases/tag/v538)

### important note on index regeneration

* **if you get a note on update about missing indices that need to be regenerated, don't panic! everything is fine, nothing to worry about, let it do its work**

### new libraries today

* **if you run from source, I recommend you rebuild your venv today. the setup script points at new versions of Qt, OpenCV, and a HEIF module that adds new filetype support**

### new Qt and OpenCV

* all release builds and normal source installations move up to PySide6 (Qt) 6.5.2 today. we've done a good bit of testing in different situations, and it seems to be a good and reliable upgrade from 6.4.1, which has given us a mix of annoying trouble at times, like mismatched UI scaling and mpv-related flickering
* let me know if you have any trouble with the overall feel of the program, particularly if you are running on an older or un-updated version of your OS
* the last version of Qt that was generally without caveats was 6.3.1. if you do have trouble with today's release (I suspect old and un-updated OSes, or source users on older Python), one option is to move to running from source and using this older version, which I have updated my setup_venv scripts to offer as a stable 'Qt6 (o)lder' option
* similarly, we are moving from OpenCV (an image library) 4.5.5.64 to 4.7.0.72. we've tested this in several rounds of future-builds and had no reports of trouble, and this also improves some build compatibility with FFMPEG 5.0 (issue #1419)
* the 'test' version of Qt stays at 6.5.2 for now, since this is the latest version
* the 'old' OpenCV compatability version remains at 4.5.3.56, the new 'test' version is now 4.8.0.74

### deferred delete system

* the first full version of the deferred delete system is complete. your no-longer-needed tables lying around after a big operation like a PTR delete/reset will now be shrunk in the background until they are small enough to delete in trivial time
* the menu entry under _database->database maintenance_ has a new submenu for the job and 'work in idle/normal' time checkboxes just like file maintenance
* the new review window UI is now fleshed out. it can refresh itself, and automitically does so on changes, and the 'work hard' button functions
* I discovered a bug in last week's code that stopped some indices from being recreated in certain regeneration jobs. if you did a 'regenerate tag text search cache' or similar operation last week, you'll encounter the above 'need to regen some indices' note. no worries, it'll all fix itself, and, if you noticed any slowdown, the affected system should work at the proper speed again

### user contributions

* thanks to a user, we now have full support for HEIF, HEIC, and AVIF image files. they will import and render just like any other image. furthermore, we have support for HEIF, HEIC, and AVIF 'sequences', which are basically like an animated gif or apng and are under the 'animations' filetype category (and they seem to play in mpv great! although I don't have an example HEIC sequence to test with, lol). all users who use the normal build will get this on update--anyone running from source will want to rebuild their venv this week to get the functionality. you can double-check _help->about_ to see if you have the required 'pillow-heif' library
* thanks to a user, the various help links in the program now redirect to the online help (and/or direct to a guide to build the local help) if the local help is missing (fixes #1360)
* thanks to a user, an addititonal final network transfer size check is now in place. if a server says it will deliver x bytes and actually delivers y, the job now raises an error. this can happen with various twitter solutions, where vid downloads will sometimes stealth-stop-working, leaving a valid but truncated mp4. fingers crossed this will now catch that situation and trigger a re-attempt
* thanks to a user, fixed TIFF files not showing EXIF correctly. just to be safe, all tiffs will be scheduled for a 'has EXIF?' rescan on update, and I silenced another bit of tiff-related PIL warning-logspam
* mkv files with AV1 video (and no/worbis/opus audio) are now correctly identified as webms. all mkvs will be scheduled for a metadata rescan on update

### misc

* when transferring mappings, _tags->migrate tags_ now supports a full location context file filter (like the file domain button you see in an autocomplete). previously it was just a list of single locations to pick from, but now, if you want to grab tags for all files deleted from x, or all files in either y or z, it is simple to set up. relatedly, the 'multiple/deleted' dialog picker launched from that menu now sizes itself to try and fit all its stuff in, rather than always being scrolled
* fixed a bug that meant you could ok the 'edit predicate' dialog despite the regex string being invalid when editing an existing 'system:known url=(regex)' predicate. the 'check valid' test is now caught correctly and cancels dialog ok, rather than escalating to the popup message catcher
* fixed a bug in table analyze code that was causing empty tables to be unintentionally re-analysed over good existing data
* a file_system_type-checking call that is used in file-export is now cached. previously it was hit for every pending file path to be calculated, and on systems with a 50ms response time to this call (I presume because of NAS/RAID-style gubbins), it meant opening the file export window could take minutes (issue #1413)
* APNG metadata parsing no longer requires FFMPEG, greatly accelerating their import
* I think I fixed the root cause of a weird bug we encountered and hacked around a couple weeks ago, where if a certain sort of downloaded page produced nothing via its parser, and it was detected initially as actually a valid file to import, but then that file import failed (e.g. ffmpeg went full bananas and thought a json file was an mp4), the import attempt would loop. the error handling now catches the unusual import failure gracefully, and the import object should be set to 'skipped' appropriately
* fixed a harmless but annoying desync error popup that sometimes occurs when deleting a repository service

### misc boring notes

* to deal with the deferred delete system clashing with SQLite not allowing index renames, I moved the database index testing and creation system to a dynamic name format. it works but is a little hacky, so maybe we'll move to direct sqlite_master interrogation in future
* unfortunately, the table shrink method I had planned to employ was not feasible (I wanted to do 'delete n rows', but it turns out that isn't compiled by default in all normal SQLite releases wew). I then experimented with several other strategies and settled on the KISS of 'select n, delete these n' in two queries, which worked out far better than my cleverer attempts anyway. the thing doesn't use much CPU time, and it cautiously autothrottles itself, and I've tested it in a bunch of situations, and I'm super happy with the performance, but if you do happen to get noticeable bumps of lag, most likely in PTR removal when the current_mappings giga-table is shrunk, turn off all database maintenance under the menu, for both idle and normal time, and let me know, and we'll figure it out
* refactored APNG parsing code to the new 'HydrusAnimationHandling.py' and took out the ffmpeg code. now OpenCV/PIL figures out the resolution

## [Version 537](https://github.com/hydrusnetwork/hydrus/releases/tag/v537)

### new filetype selector

* I rewrote the expanding checkbox list that selects filetypes in 'system:filetype' and File Import Options into a more normal tree view with checkboxes. it is more compact and scrolls neatly, letting us stack it with all these new filetypes we've been adding and more in future. the 'clicking a category selects all children' logic is preserved
* I re-ordered the actual filetypes in each sublist here. I tried to put the most common filetypes at the top and listed the rest in alphabetical order below, going for the best of both worlds. you don't want to scroll down to find webm, but you don't want to hunt through a giant hydev-written 'popularity' list to find realmedia either. let's see how it works out
* I split all the archive types away from 'applications' into a new 'archives' group
* and I did the same for the 'image project files' like krita and xcf. svg and psd may be significantly more renderable soon, so this category may get further shake-up
* this leaves 'applications' as just flash and pdf for now
* it isn't a big deal, but these new groups are reflected in _options->media_ too
* all file import options and filetype system predicates that previously said 'all applications' _should_ now say 'all applications, image project files, or archives'

### fast database delete

* I have long planned a fix for 'the PTR takes ages to delete' problem. today marks the first step in this
* deleting a huge service like the PTR and deleting/resetting/regeneratting a variety of other large data stores are now essentially instant. the old tables are not deleted instantly, but renamed and moved to a deferred delete zone
* the maintenance task that actually does the deferred background delete is not yet ready, so for now these jobs sit in the landing zone taking up their original hard disk space. I expect to have it done for next week, so bear with me if you need to delete a lot this week
* as this system gets fleshed out, the new UI under _database>db maintenance->review deferred delete table data_ will finish up too

### misc

* fixed a bitrot issue in the v534 update code related to the file maintenance manager not existing at the time of db update. if you got the 'some exif scanning failed to schedule!' popup on update, don't worry about it. everything actually worked ok, it was just a final unimportant reporting step that failed (issue #1414)
* fixed the grid layout on 'migrate tags', which at some point in the recent past went completely bananas
* tightened up some of the code that calculates and schedules deferred physical file delete. it now catches a couple of cases it wasn't and skips some work it should've
* reduced some overhead in the hover window show/hide logic. in very-heavy-session clients, this was causing significant (7ms multiple times a second) lag
* when you ok the 'manage login scripts' dialog, it no longer re-links new entries for all those scripts into the 'manage logins' system. this now only happens once on database initialisation
* the manage login scripts test routine no longer spams test errors to popup dialogs. they are still written to log if you need more data
* silenced a bit of PIL warning logspam when a file with unusual or broken EXIF data is loaded
* silenced the long time logspam that oftens happens when generating flash thumbnails
* fixed a stupid typo error in the routine that schedules downloading files from file repositories
* `nose`, `six`, and `zope` are no longer in any of the requirements.txts. I think these were needed a million years ago as PyInstaller hacks, but the situation is much better these days

## [Version 536](https://github.com/hydrusnetwork/hydrus/releases/tag/v536)

### more new filetypes

* thanks to a user, we have XCF and gzip filetype support!
* I rejiggered the new SVG support so there is a firmer server/client split. the new tech needs Qt, which broke the headless Docker server last week at the last minute--now the server has some sensible stubs that safely revert to the default svg thumb and give unknown resolution, and the client patches in full support dynamically
* the new SVG code now supports the 'scale to fill' thumbnail option

### misc

* I fixed the issue that was causing tags to stay in the tag autocomplete lookup despite going to 0 count. it should not happen for new cases, and **on update, a database routine will run to remove all your existing orphans. if you have ever synced with the PTR, it will take several minutes to run!**
* sending the command to set a file as the best in its duplicate group now presents a yes/no dialog to confirm
* hitting the shortcut for 'set the focused file as better than the other(s)' when you only have one file now asks if you just want to set that file as the best of its group
* fixed an erroneous 'cannot show the best quality file of this file's group here' label in the file relationships menu--a count was off
* fixed the 'set up a hydrus.desktop file' setup script to point to the new hydrus_client.sh startup script name
* thanks to a user, a situation where certain unhandled URLs that deliver JSON were parsing as mpegs by ffmpeg and causing a weird loop is now caught and stopped. more investigation is needed to fix it properly

### boring stuff

* when a problem or file maintenance job causes a new file maintenance job to be queued (e.g. if the client in a metadata scan discovers the resolution of a file was not as expected, let's say it now recognises EXIF rotation, and starts a secondary thumbnail regen job), it now wakes the file maintenance manager immediately, which should help clear out and update for these jobs quickly when you are looking at the problem thumbnails
* if you have an image type set to show as an 'open externally' button in the media viewer, then it is now no longer prefetched in the rendering system!
* I added a very simple .editorconfig file for the project. since we have a variety of weird files in the directory tree, I've made it cautious and python-specific to start with. we'll expand as needed
* I moved the similar files search tree and maintenance tracker from client.caches.db to client.db. while the former table is regeneratable, it isn't a cache or precomputation store, _per se_, so I finally agreed to move it to the main db. if you have a giganto database, it may take an extra minute to update
* added a 'requirements_server.txt' to the advanced requirements.txts directory, just for future reference, and trimmed the Server Dockerfile down to reflect it

### client api

* thanks to a user, fixed a really stupid typo in the Client API when sending the 'file_id' parameter to set the file
* wrote unit tests for file_id and file_ids parameters to stop this sort mistake in future
* if you attempt to delete a file over the Client API when one of the given files is delete-locked (this is an advanced option that stops deletion of any archived file), the request now returns a 409 Conflict response, saying which hashes were bad, and does not delete anything
* wrote a unit test to catch the new delete lock test
* deleted the old-and-deprecated-in-one-week 'pair_rows' parameter-handling code in the set_file_relationships command
* the client api version is now 49

## [Version 535](https://github.com/hydrusnetwork/hydrus/releases/tag/v535)

### misc

* thanks to a user, we now have Krita (.kra, .krz) support! it even pulls thumbnails!
* thanks to another user, we now have SVG (.svg) support! it even generates thumbnails!
* I think I fixed a comparison statement calculator divide-by-zero error in the duplicate filter when you compare a file with a resolution with a file without one

### petitions overview

* _this is a workflow/usability update only for server janitors_
* tl;dr: the petitions page now fetches many petitions at once. update your servers and clients for it all to work right
* so, the petitions page now fetches lots of petitions with each 'fetch' button click. you can set how many it will fetch with a new number control
* the petitions are shown in a new multi-column list that shows action, account id, reason, and total weight. the actual data for the petitions will load in quickly, reflected in the list. as soon as the first is loaded, it is highlighted, but double-click any to highlight it in the old petition UI as normal
* when you process petitions, the client moves instantly to the next, all fitting into the existing workflow, without having to wait for the server to fetch a new one after you commit
* you can also mass approve/deny from here! if one account is doing great or terrible stuff, you can now blang it all in one go

### petitions details

* the 'fetch x petition' buttons now show `(*)` in their label if they are the active petition type being worked on
* petition pages now remember: the last petition type they were looking at; the number of petitions to fetch; and the number of files to show
* the petition page will pause any ongoing petition fetches if you close it, and resume if you unclose it
* a system where multi-mapping petitions would be broken up and delivered in tags with weight-similar chunks (e.g. if would say 'aaa for 11 files' and 'bbb in 15 files' in the same fetch, but not 'ccc in 542,154 files') is abandoned. this was not well explained and was causing confusion and code complexity. these petitions now appear clientside in full
* another system, where multi-mapping petitions would be delivered in same-namespace chunks, is also abandoned, for similar reasons. it was causing more confusion, especially when compared to the newer petition counting tech I've added. perhaps it will come back in as a clientside filter option
* the list of petitions you are given _should_ also be neatly grouped by account id, so rather than randomly sampling from all petitions, you'll get batches by user x, y, or z, and in most cases you'll be looking at everything by user x, and y, and then z up to the limit of num petitions you chose to fetch
* drawback: since petitions' content can overlap in complicated ways, and janitors can work on the same list at the same time, in edge cases the list you see can be slightly out of sync with what the server actually has. this isn't a big deal, and the worst case is wasted work as you approve the same thing twice. I tried to implement 'refresh list if count drops more than expected' tech, but the situation is complicated and it was spamming too much. I will let you refresh the list with a button click yourself for now, as you like, and please let me know where it works and fails
* drawback: I added some new objects, so you have to update both server and client for this to work. older/newer combinations will give you some harmless errors
* also, if your list starts running low, but there are plenty more petitions to work on, it will auto-refresh. again, it won't interrupt your current work, but it will fetch more. let me know how it works out
* drawback: while the new petition summary list is intentionally lightweight, I do spend some extra CPU figuring it out. with a high 'num petitions to fetch', it may take several seconds for a very busy server like the PTR just to fetch the initial list, so please play around with different fetch sizes and let me know what works well and what is way too slow
* there are still some things I want to do to this page, which I want to slip in the near future. I want to hide/show the sort and 'num files to show' widgets as appropriate, figure out a right-click menu for the new list to retry failures, and get some shortcut support going

### boring code cleanup

* wrote a new petition header object to hold content type, petition status, account id, and reason for petitions
* serverside petition fetching is now split into 'get petition headers' and 'get petition data'. the 'headers' section supports filtering by account id and in future reason
* the clientside petition management UI code pretty much got a full pass
* cleaned a bunch of ancient server db code
* cleaned a bunch of the clientside petition code. it was a real tangle
* improved the resilience of the hydrus server when it is given unacceptable tags in a content update
* all fetches of multiple rows of data from multi-column lists now happen sorted. this is just a little thing, but it'll probably dejank a few operations where you edit several things at once or get some errors and are trying to figure out which of five things caused it
* the hydrus official mimetype for psd files is now 'image/vnd.adobe.photoshop' (instead of 'application/x-photoshop')
* with krita file (which are actually just zip files) support, we now have the very barebones of archive tech started. I'll expand it a bit more and we should be able to improve support for other archive-like formats in the future

## [Version 534](https://github.com/hydrusnetwork/hydrus/releases/tag/v534)

### user submissions

* thanks to a user, we now have SAI2 (.sai2) file support!
* thanks to a user, the duplicate filter now says if one file has audio. this complements the recent Hydrus Video Deduplicator (https://github.com/appleappleapplenanner/hydrus-video-deduplicator), which can queue videos up in your dupe filter
* thanks to a user, we now have some nice svg images in the help->links(?) menu instead of gritty bitmaps
* thanks to a user, some help documentation for recent client vs hydrus_client changes got fixed

### quality of life/new stuff

* the media viewer's top-area 'removed from x' lines for files deleted from a local file service no longer appear--unless that file is currently in the trash. on clients with busy multiple local file services, they were mostly just annoying and spammy. if you need this data, hit up the right-click menu of the file--it is still listed there
* the 'loading' media page now draws a background in the same colour as the thumbnail grid, so new searches or refreshes will no longer flash to a default grey colour--it should just be a smooth thumbs gone/thumbs back now
* added a new shortcut action, 'copy small bmp of image for quick source lookups', for last week's new bitmap copy action
* it turns out PNG and WEBP files can have EXIF data, and our existing scanner works with them, so the EXIF scanner now looks at PNGs and WEBPs too. PNGs appear to be rare, about 1-in-200. I will retroactively scan your existing WEBPs, since they have EXIF more commonly, maybe as high as 1-in-5, and are less common as a filetype anyway so the scan will be less work, but when you update you will get a yes/no dialog asking if you want to do PNGs too. it isn't a big deal and you can always queue it up later if you want

### fixes

* I banged my head against the notes layout code and actually had great success--a variety of borked note-spilling-over-into-nothing and note-stretching-itself-crazy and note-has-fifty-pixels-of-margin issues are fixed. let me know if you still have crazy notes anywhere
* the duplicate filter right-hand hover is now more aggressive about getting out of the way of the notes hover, especially when the notes hover jitter-resizes itself a few extra pixels of height. the notes hover should no longer ever overlap the duplicate filter hover's top buttons--very sorry this took so long
* when you drag and drop thumbnails out of the program while using an automatic pattern to rename them (_options->gui_), all the filenames are now unique, adding '(x)' after their name as needed for dedupe. previously, on duplicates, it was basically doing a weird spam-merge
* fixed an issue when sanitizing export filenames when the destination directory's file system type cannot be determined
* fixed a bug when doing a search in a deleted file domain with 'file import time' as the file sort
* fixed a bug when hitting the shortcut for 'open file in media viewer' on a non-local file
* fixed a bug when the client wants to figure out view options for a file that has mime 'application/unknown'
* I may have improved the 'woah the db caches are unsynced' error handling in the 'what siblings and parents does this have?' check when you right-click tags

### weird bitmap pastes

* fixed the new 'paste image' button under `system:similar files` for a certain category of unusual clipboard bitmaps, including several that hydrus itself generates, where it turns out the QImage storage system stores extra padding bytes on each line of pixels
* fixed the new 'paste image' button when the incoming bitmap has a useless alpha channel (e.g. 100% transparent). this was not being stripped like it is for imported images, and so some similar files data was not lining up
* many bitmaps copied from other programs like Firefox remain slightly different to what hydrus generates (even though both are at 100% scale). my best guess here is that there is some differing ICC-profile-like colour adjustment happening somewhere, probably either a global browser setting, the browser obeying a global GPU setting, a simply better application of such image metadata on the browser's side, or maybe a stripping of such data, since it seems a 'copy image' event in Firefox also generates and attaches to your clipboard a temporary png file in your temp folder, so maybe the bitmap that we pull from the clipboard is actually generated during some conversion process amidst all that, and it loses some jpeg colour data. whatever the case here, it changes the pixel hash and subtly alters the perceptual hash in many cases. I'm bumping the default distance on this search predicate up to 8 now, to catch the weirder instances

### misc

* the 'does the db partition have 500MB free?' check that runs on database boot now occurs after some initial database cleanup, and it will use half the total database size instead, if that is smaller than 500MB, down to 64MB (issue #1373)
* added a note to the 'running from source' help that the newer mpv dll seems to work on Qt5 and Windows 7 (issue #1338)
* the twitter parsers and gugs are removed from the defaults for new users. a shame, but we'll see what happens in future
* more misc linting cleanup

### ratings on the client api

* the services object now shows `star_shape` and `min_stars` and `max_stars` for like/dislike and numerical rating services
* the file metadata object now has a 'ratings' key, which lists `rating_service_key->rating` for all the client's rating services. this thing is simple and uses human-friendly values, but it can hold several different data types, so check the help for details and examples
* a new permission, 'edit ratings', is added.
* a new command, `/edit_ratings/set_rating`, is added. Guess what it does! (issue #343)
* the help is updated for these
* the unit tests are updated for these
* the client api version is now 48

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
