---
title: Changelog
---

# changelog

!!! note
    This is the new changelog, only the most recent builds. For all versions, see the [old changelog](old_changelog.html).

## [Version 553](https://github.com/hydrusnetwork/hydrus/releases/tag/v553)

### animated gif fixes

* fixed the **false positive** "serious I/O Error! This is a significant hard drive problem" problems saw in last week's animated gif 'has transparency' rescanning. it turns out the PIL animated gif renderer we rarely use was raising overly serious errors on a truncated frame (i.e. some borked file, not a borked OS hard drive access), and this was escalating up to the overall maintenance system, which was shutting down in panic. truncated gifs in the PIL renderer should now just either render the last frame over and over or rewind as soon as they hit a super problem
* as well as rendering, the duration and frame-counter code also handles these borked frames better, so animated gifs that have a single borked frame should now A) import without an error and B) get more accurate frame counts
* you may have seen this sort of error before where an mpv window seems to keep rendering the gif despite the scanbar hitting its right end. if you see a file like that, try right-clicking and hitting _manage->maintenance->regenerate file metadata_. might just fix it up!
* if mpv encounters one of these busted gifs, a selection of quiet-but-spammy "I don't know what happened, but MPV just reported a weird error, here it is" logging no longer happens. we basically know what happened, and mpv seems good at recovering
* fixed some PIL alpha gif rendering on backwards seek and loop

### slideshow tech

* _options->media_ has a new 'slideshow' section with five new options regarding slideshows and media with duration (video, audio). if you don't care too much, just leave them alone--they make slideshows transition better!
* first, there's a checkbox to say 'always play duration-having media completely once through before moving on'. this was the previous behaviour, now default off
* then there are two options, for a percentage of the current slideshow period and a flat seconds value, to say 'if the duration-having media is shorter than this amount of time, then move the slideshow on early'. this allows short gif loops to play a bit, but not for 15 minutes
* then there is an option, for a percentage of the current slideshow period, to say 'if the duration-having media has a duration between this amount and 100% of the slideshow period, then move on once it has played once through'. this allows for clean slideshow transitions for media that is just a bit shorter than the slideshow period
* then there is an option, again for a percentage of the slideshow period, to say 'if the duration-having media is _longer_ than the slideshow period plus this amount of time, then delay moving on until it is played once through'. this allows 35 second videos to complete fully in a 30 second slideshow while stopping a ten minute vid hogging its turn
* completely rewrote the slideshow timer tech
* did a little work bringing the experimental Qt media player up to proper slideshow capability, and neatened the associated code
* yes, hydev did write all these options for his repurposed slideshow computer because he was annoyed about his vidya captures and 500ms loops playing jank on a 30m slideshow period

### misc

* the file-info-summary lines that appear in the top row thumbnail menu submenu now show if a file has audio/transparency/exif/other metadata/icc profile
* the file-info-summary lines that appear in the top row thumbnail menu submenu and the top-center of the media viewer no longer list 'removed from x 5 days ago' for files that were moved internally between local file services. these statements were spammy and not helpful! if you really need them, are available in the 'manage times' dialog. sorry for the annoyance here
* trying to move a file from local file service x to y no longer triggers the archive delete lock, if you have that enabled (this was prohibiting the delete from x after the copy to y is done)
* the 'import options' button now labels itself with 'all default', 'all set', or 'some set' to quick-review what it is holding
* the stupidly named advanced users' `OR*` button is now just `advanced`
* the 'manage->regenerate' thumbnail menu is now called 'maintenance', and it always contains the whole file maintenance job list just as it appears in the main file maintenance panel. tooltips are the longer descriptions
* if you reduce a static check time in a checker options (watchers or subscriptions), the next check time should now recalculate correctly immediately. previously, the new check period wasn't kicking in until the next, delayed cycle. I have preserved the logic that tries to keep a static check time regular (which was the core problem here), where if you check every 7 days on saturday night, then delaying one time and running it on sunday night won't delay the check time phase along to next sunday--the next week it will be due on saturday again
* the system:rating edit panel has some tooltips that say 'Set "is" and leave rating null to search for "unrated".'. maybe this is annoying, maybe I should just add redundant 'unrated' checkboxes, let me know what you think
* when the file maintenance routine runs into a serious error (like we had with the false positive transparent gifs), the popup messages now include a file button for the problem file for easy referral
* if a file breaks MPV in a crashy-looking way, hydrus now makes a popup with a file button to it for easy referral
* fixed a typo issue with the recent temp folder recovery code that broke the temp folder for file imports on the hydrus file repository. sorry for the trouble, this slipped through unit testing because that too has a hacky temp folder solution!

### weird/specific stuff

* I've spaced out many of the initial library loads across the core boot init routine. fingers crossed, the splash screen will open earlier and report more as things each import, rather than taking ages to appear and then suddenly initialising everything real quick (on slow computers). also, a monolithic UI init job is broken up into pieces, which should let the splash update itself a little smoother as your client loads its style and stuff
* the file and database maintenance managers are now initialised in a better stage, and, like the subscription manager, they now do not start any work until the first session is fully loaded
* while pouring over the server code trying to find a petition miscount bug and/or a petition summary fetch bug (which I was entirely unsuccessful at), I stopped it 404ing when there are unexpectedly no petitions to fetch--it should now just give an empty list and reset the count serverside, which is an old behaviour that wasn't working quite right in the modern system. this will cost less CPU than commanding the full service service_info number reset. I will have to investigate the core problem of miscounts more closely to figure out the base problem here
* if two subscription jobs publish files to the same popup label (which merges the popup button to include both sets of files), this file list is now properly deduplicated (so if both subs picked up the same file(s), it now won't try to publish the same file twice). the basic popup button instantiation also clears out dupes
* the 'additional tags'-only tag import options in a subscription query can now no longer be set 'default'. this choice was unintended and has no current meaning if set
* building on last week, there are even fewer duplicate menu tooltips
* updated and clarified the text in _options->external programs_. also, if you try to put a command that does not include "%path%", it'll moan at you with a yes/no dialog
* when 'confirm sending files to trash' is off but 'use advanced file delete dialog' is also on, the advanced file delete dialog will now not pop up if there is only one normal local file service to delete from (it was always popping up before, since it exposes the physical file delete options and the dialog thought it wasn't a 'one-choice' delete)
* the forced-wait throttle that happens on several exception catches is reduced from 1s to 200ms
* I made the new job status queue properly thread-safe with a lock. I forgot to do it last week, whoops!
* fixed the build script to construct a file named .tar.zst for the Ubuntu release, not .tar.gz

## [Version 552](https://github.com/hydrusnetwork/hydrus/releases/tag/v552)

### misc

* 'system:has audio' and 'system:embedded metadata' are now combined under a new meta-system predicate 'system:file properties'. if you can't find your yes/no predicate, try looking there!
* menu commands will no longer have their unadjusted label as their tooltip. all tooltips are either the full status bar description or the full label if it was long enough to be elided
* the 'open externally' panel now shows the default filetype thumbnail for formats like zip and epub
* 'system:number of character tags > 4' now parses correct when you type it (previously it wouldn't work with a namespace), including special handling for 'unnamespaced'
* the various 'number of x' system predicates will now parse if you type 'num x', 'number x', or 'num of x'
* to match the other entries, the '4k' resolution swap-in label is now '2160p'
* added a little extra info on the manage tags dialog to 'getting started with tags'
* if you have 'confirm sending files to trash' turned off, the delete dialog will now show on physical deletes (i.e. deletes from the trash)
* updated the derpibooru parser to pull the new AI-based 'generator' and 'prompter' namespaces (converting both to the hydrus-appropriate 'creator')
* thanks to a user, the Linux build is now archived with zstd instead of gzip. should be about the same size but faster to decompress

### fixes

* fixed a stupid typo in the folder copy/move tech last week that was not allowing some move/copies to start (as always, the thing that is so simple that you don't think to test it is the very thing that blows up). sorry for the trouble!
* cleaned up the file/folder move/copy error statements a little more
* fixed the 'default search page tag service' dropdown in _options->search_ not saving correctly
* fixed the 'open externally' panel having out of position thumbnails when your thumbnail supersampling is set to other than 100%
* fixed the import and display of images in signed 16-bit format (weird TIFFs, seems like).
* any image with an unusual channel data type beyond uint16 and int16 is going to be, as the default thing to do, normalised to unsigned 8-bit. it may blow out the colour range, but it should show something!
* the client handles files with (0x0) resolution better. they should now always import, and it'll _attempt_ to render them to a normal full size thumb. if it works (e.g. this is some misconfigured SVG), great, and if it doesn't, we'll get a nicely sized filetype.png or hydrus.png fallback
* files with (0x0) resolution will now never show in the preview or media viewers. previously, the preview viewer would bail out half-way through setting the media, causing it to fall into an invalid state where it still showed the previous valid media but wouldn't 'click-off' it easily, and the media viewer would generally panic to its 'no media to show' state and lose navigation functionality. now, files that are 0x0 are included in the general 'can we show this?' pre-launch sanity checks

### has_transparency

* the database can now remember if a file has transparency. you can search this with the new 'system:has transparency' predicate, which is under the new 'system:file properties' and will also parse if you type 'system:has/no transparency/alpha'
* note that my version of 'has transparency' discludes files that have an all-opaque alpha channel (i.e. one that lets no light through). RGBA is insufficient--I want an alpha channel with some actual translucency somewhere!
* although many application image project types like PSD and XCF can have transparency, the various ways we render or thumbnail them are hacky and probably lock to RGB or RGBA always, so I'm going to start simple. this week, we test transparency for all the images that support it (basically anything but jpeg), and animated gif. the animated gif tech is new and actually looks through every frame of an RGBA gif until it hits interesting alpha to catch cases where it starts opaque and fades away
* just like we had with 'has exif' and similar, 'has transparency' knowledge will be calculated instantly for all new files, but for the files you already have, we'll have to do some slow file maintenance in the background for a while to retroactively calculate it all. you don't have to do anything; the data will just populate over time
* the duplicate filter now shows 'has transparency, the other is opaque' statements
* while working on this, I encountered a number of files that seemed to be false positives--apparently normal, fully opaque images of anime girls that were somehow showing up as 'has interesting alpha'. upon inspecting them closely, I discovered the border pixels had a slight fade, or one pixel out of all of them was 98% opaque, or the single bottom right pixel was completely transparent. perhaps some of these are secret artist markers, but I imagine many are just an accidental drawing tablet smudge or dodgy crop tool calculations. I'm leaving them as 'has_transparency' for now, but maybe we'll want to tune this more in future, perhaps saying you have to be at least 0.3% transparent to count. anyway, as always, while I am interested in seeing files that seem to get a false positive/negative with this new 'has transparency' test, if you have the technical know-how, please check if they actually have no alpha yourself first. once you play around with this system, let me know what sort of pseudo-'false positive' rate you are getting, and we can talk about an appropriate threshold

### client api

* the 'file_metadata' call now includes a 'has_transparency' boolean! remember that it will be overly `false` for a while, until the file maintenance catches up
* forgot to mention it last week, but thanks to a user there is a new `/manage_database/get_client_options` call that fetches a heap of different client options. this exposes a mess that may change with any update, but there may be something neat you can hook into. this week we fixed a thing that was breaking this call for probably all old clients
* the client api version is now 56

### boring cleanup

* renamed JobKey to JobStatus across the program
* in prep for Client API calls to interact with the popup system, the queue of JobStatuses waiting to be displayed in the popup toaster is now encapsulated in a separate class, outside of the Qt object dangerzone
* sped up how the popup manager system inspects and cleans the JobStatus queue in general. should have better performance when you get hundreds or thousands of messages
* cleaned up some awkward popup manager dismiss code
* fixed a timing issue that meant popup messages were auto-dismissed from the popup toaster up to a second after they were being 'deleted' by their parent functiions. subscription flow felt more laggy because of this
* fixed the file info manager's duplicate call to duplicate unusual metadata like has_exif and blurhash
* removed some old code that isn't used any more

## [Version 551](https://github.com/hydrusnetwork/hydrus/releases/tag/v551)

### misc

* thanks to a user, we have a new checkbox under _options->thumbnails_ that disables thumbnail fading. they'll just blink into place in one frame as soon as ready
* after looking at this code myself, I gave it a full clean. the actual thumbnail fade animation is now handled with some proper objects rather than a scatter of variables passed around
* I also doubled the default fade time to 500ms. I expect I'll add an option for it, especially if we rework all this into the proper Qt animation engine and get it performing better
* fixed the crashes users on PyQt were seeing! I made one tiny change (1->1.0) last week, and PyQt didn't like it, so any view of Mr Bones or 'open externally' panels, or the media viewer top-right ratings hover was leading to program instability
* the system predicates for 'has/no duration', 'has/no frames', 'has/no notes', 'has/no words' (i.e. the respective 'num x' system pred, but either = 0 or >0) are now aware that they are each others' inverse, so if you ctrl+double-click or do similar edit actions, they'll flip
* updated the 'PTR for dummies' page to link to a new QuickSync source, kindly maintained and hosted by a user

### code cleanup and misc bug fixes

* sped up some random iteration across the program (e.g. when deciding which order to waterfall thumbnails in, which can suffer from overhead if you do a fast giganto-scroll)
* cleaned up the code that does image alpha channel (transparency) detection, comparison, and stripping
* unified how the variety of image loads and conversions perform the 'strip this image of useless transparency data' normalisation step. thumbnails from krita, svg, and pdf are now stripped of useless alpha. also, all 'import this serialised object png' avenues now handle pngs with spurious alpha
* I think I fixed the alpha channel stripping code to handle 'LA' (greyscale with transparency) files. if you try to import a hydrus serialised object png file that is for some crazy reason now LA, I think it'll work!
* when a files popup message filters its current files and the count goes to 0 (happens if you re-click the button after deleting everything it has to show), the message now auto-dismisses itself (previously it was nuking the button but staying as a thin strip of null panel space)
* fixed a bug where `system:date` predicates were displaying labels an hour off (usually midnight -> 11pm, thus cycling back to the previous day) thanks to the clocks changed (in the USA) last weekend. I suspect there is more of this, here and there, so let me know what you see
* fixed a counting typo error with the delete files code when you delete the last file in a domain but the domain thinks it already has 0 files
* fixed up similar code across the database to forestall future typos on SQLite SUMs
* improved and unified the 'hydrus temp dir' management code. if the specific per-process hydrus temp dir is cleared out by an external factor (I'm guessing just the OS cleaning up during a long running client session), hydrus should just simply make a new folder as needed. with luck, this will fix a problem with drag and drop export that ran into this

### many file move/copy error handling improvements

* _tl;dr: if hydrus can't put a file somewhere, it deals with that better now_
* improved how file move/merge function reports its errors, and how all its callers handle them
* the 'rename a file's file extension when its filetype changes' job now correctly recognises when it fails to rename a file due to a reason other than the file being currently in use
* import folders now correctly detect when they fail to 'move' action a file out after processing
* the check file integrity routine now correctly detects when it fails to move a damaged file from file storage to a landing zone in the main db directory. this failure now cancels the job properly and prints a nicer error to the log
* improved how the file copy/mirror function reports its errors, and how all its callers handle them
* saving a serialised object png now properly catches a 'transfer from temp dir to dest location' move error
* the internal database backup and restore routines now detect file copy errors better
* a drag and drop export operation that wants to put the files in the temp dir and also fails to collect its files nicely now correctly raises an error
* failing to set the mpv file on options save (and the subsequent mpv-load action) now reports its error correctly
* exporting update files now handles a missing update file more gracefully
* mergedirectory and mirrordirectory now fail instantly after any single error, rather than several
* added some more file/directory pre-checks to all the merge/mirror functions
* deleted some old unused code here

### client api

* thanks to a user, the Client API now has a 'generate_hashes' endpoint that returns the sha256 hash (and pixel hash and perceptual hashes of any appropriate image file) of any file you give it
* the client api version is now 55

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
* if you have 'scale to fill' set, hydrus will regenerate your thumbnails naturally as you browse the client. fingers crossed, you won't notice any visual difference through the transition
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
