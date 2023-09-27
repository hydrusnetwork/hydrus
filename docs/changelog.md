---
title: Changelog
---

# changelog

!!! note
    This is the new changelog, only the most recent builds. For all versions, see the [old changelog](old_changelog.html).

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
