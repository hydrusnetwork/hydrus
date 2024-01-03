---
title: Changelog
---

# changelog

!!! note
    This is the new changelog, only the most recent builds. For all versions, see the [old changelog](old_changelog.html).

## [Version 557](https://github.com/hydrusnetwork/hydrus/releases/tag/v557)

### misc

* optimised large tag filter edit UI. you can now paste 5,000 items into an empty tag filter blacklist in less than a second, and if you have a big tag filter, removing or adding one thing is now instant (previously, this stuff would lag 4 seconds or more, sometimes multiple minutes!!)
* the ugoira 'num frames' counting method now discludes files ending in .js/.json, to catch future bundling of frame timings
* the cbz scanning tech should now recognise cbzs with four or fewer pages
* a legacy 'is this image all good?' check that happens on PIL-loading is now gone. this improves rendering for a variety of truncated files and clarifies some error messages (previously, this thing was just failing silently)
* fixed the delete file pre-flight logic so users on the non-advanced delete dialog can now delete repository updates. previously, they saw the menu entry, but hitting it was a no-op

### better hash predicate parsing

* `system:hash` labels are a little different now. they'll say `system:hash (md5) is abcd...`, with the algorithm after the "hash". hash is omitted for sha256 (the hydrus default). this eases parsing
* `system:similar to data` labels are a little different. they'll say 'distance' instead of 'max hamming', and the number and type of hashes they hold, and if they hold only pixel hashes, the distance is not stated
* `system:hash` predicate parsing is now more flexible. you can put the hash type pretty much anywhere now.
* `system:similar to` and `system:similar to data` predicate parsing is now more flexible. more combinations are allowed, and you can not include distance and it'll be fine
* these three hash predicates now copy to clipboard with all their hashes explicitly enumerated, making strings that are fully parsable! this is a big step forward in a completely sealed import-export predicate parsing loop; now I have the tech set up to export a different phrase to clipboard than what you see in the label, I just need the examples of where it goes wrong. if there is a system predicate that copies to clipboard in a way that won't parse back, let me know and I'll see if I can fix it.
* added more unit tests for this parsing

### documentation and cleanup

* wrote a guide on how to install 'Git for Windows' for the 'running from source' help. although most of the settings in its marathon 12-page install wizard can be left as default, the technical questions can be intimidating, so I've written them all out for a nice simple install. also brushed up some of the surrounding help here
* added a warning to the regular 'installing and updating' help regarding the danger of test-running extract releases before updating (you can overwrite your database by accident)
* thanks to a user, the filetypes help document is updated with Ugoira and CBZ info
* all the 'HydrusFiletypeHandling' files are refactored to a new 'files' module. there's a bunch of them these days!
* the hydrus.core.images module is moved beneath this 'files' module too
* the file log list panel right-click menu now says 'open URLs'/'open files' locations' depending on whether you are looking at a URL import log or local HDD import log

### client api

* the `file_metadata` call now returns `filetype_forced` and, if so, also `original_mime` to talk about the new forced filetype system
* the client api help and unit tests are updated to test this is working ok
* fixed a typo that was causing too much work in the updated file info manager call (and was often returning 'null' results for half-cached `file_metadata` requests with `only_return_basic_information=true`)
* thanks to a user, the `/add_urls/get_url_info` Client API call now has a cache timeout of ten minutes, and the `/add_urls/get_url_files` call now has a timeout of 30 seconds if all the files are 'already in db'. this should automatically reduce some overhead for several programs that talk to the Client API a lot about URLs
* the client api version is now 58

## [Version 556](https://github.com/hydrusnetwork/hydrus/releases/tag/v556)

### misc

* fixed, on a file drag and drop, the new export path eliding code from raising an error when the default export phrase would give an empty filename. e.g. if you set the export phrase as `[title]` and the file has no title. this no longer raises an error, and the fallback export phrase `{hash}` is again used instead. broadly speaking, most errors here are now handled better
* also, export folders will now fallback to using `{hash}` if their normal export filename raises an error
* holding down ctrl+shift+ while selecting thumbnails now does the same thing as a bare shift+ select. previously, it was unhelpfully interpreting this as a bare ctrl+ click
* I may have improved the stability of 'minimise to system tray'. this thing still hangs the UI for some users on a delayed restore, I do not for certain know why
* thanks to a user who figured out the new build script, the Docker package is now on Alpine 3.19, with more and newer python library support along with it

### forced filetypes

* you can now force files' filetypes. hit _right-click->manage->force filetype_ on thumbnails or the media viewer, and you'll get a new dialog that lets you force-reassign those files to be considered something else. changes take place immediately, and files are renamed on disk with their new file extensions, making 'open externally' work nicely. the original filetype is remembered, so this can be undone easily through the same dialog
* this is happening because of the cbz/zip/Ugoira work, where the distinction between one format and another is not always perfect. the tech will also be useful for 'arbitrary file import' support. in any case, if there is something you want to force one way or another, it should now be easy
* searching for system:filetype will recognise the forced filetypes, but there may be other, more advanced areas of the program that should but do not. please let me know how you get on!
* there is a new system predicate, `system:has/no forced filetype`, that lets you further filter for the files that have this set or not. it is under `system:file properties`. it is also parsable if you ever need to type it
* if a file gets a metadata rescan and becomes a different filetype, this affects the original filetype and not the forced. if they are now both the same, no big problem
* as a side thing, I cleaned up how file metadata is put together in the database during file search. we were in a limbo state a little while ago, with an api call that just needed limited data, but I was never comfortable with it. now everything goes through the same routine, and every 'file info manager' is fully fleshed out, no matter the caller
* _yes, if you set a zip as a jpeg, you are going to get weird errors when you click on them. I'll iron these things out a bit--and have already added several quick safety checks for apparent image files without resolution and so on--and I am interested in reports, but for the most part, don't be stupid here and you won't end up in a bad place_

### filetypes

* **you will be asked on update if you would like to regenerate all your animated GIF and APNG thumbnails. The new x%-in and transparency tech seems to be working well, so I'm rolling out the full regen to everyone**
* before verifying a zip is an Ugoira or a cbz, the client now test-reads the cover page it will use as a thumbnail just to make sure it isn't passworded or corrupt or whatever
* thanks to a user, the test for whether a a zip is encrypted is much faster and neater now
* if there is an obvious video in a zip file, this is now dispositive to it not being considered a cbz
* all cbz and Ugoira are going to get a metadata scan again to account for these stricter rules

### Mr. Bones/file history chart

* **if you have had some dodgy inbox/archive numbers in your file history chart, please check again and let me know what you see. if the numbers are still bad, try changing the search from the 'all my files'/'system:everything' default--any better?**
* fixed Mr. Bones undercounting deleted files on some very old clients (i.e. mine)
* improved accuracy of some archive/inbox time calculations for the file history chart by adjusting archive times to the file service removal time of that file, if it is earlier
* included some additional de-inbox events that were being missed in the file history chart by recognising that files in the inbox but removed from a domain are nonetheless a decrement to the inbox count
* on update, some old invalid archive records will be deleted, which will also help the file history chart

### boot error handling

* if you start the program with client.db/server.db but missing any of the auxiliary databases, the program now stops you before the new file creation starts with a blocking message saying what has happened. it advises whether you should quit the process now to diagnose the hard drive fault or attempt to continue with reconstruction
* if you start the program with client.db/server.db but the 'version' table is missing, you now get a special blocking message before the main db creation routine starts saying what has happened. it advises whether you should quit the process now to diagnose the hard drive fault or attempt to continue with initial creation
* the server gets a bit of 'safe blocking show message' tech this week, which prints this info to the console and asks for the user to hit enter to continue

## [Version 555](https://github.com/hydrusnetwork/hydrus/releases/tag/v555)

### Ugoira/CBZ/Zip

* the Ugoira/CBZ conversion last week went ok! we found too many false-positive Ugoiras, however, so I have decided to make that test stricter. Ugoiras now have to have zero-indexed filesnames, and always zero-filled to six digits. all your Ugoiras will get scanned again to see if they should better be CBZ
* all zip files that are not openable (passworded, corrupt) are now detected early and just set as 'zip'

### OpenCV

* after discussing it with users, I have made the decision to slowly remove the image library OpenCV from the program. it has served us well, but it has always been a difficult-to-install bloat, and the super-compatible PIL actually does the job better these days. we'll simplify our rendering pipeline while also, with luck, improving HDR format support in future
* thanks to a user, a critical OpenCV call involved in generating similar-files search metadata (perceptual hashes DCT) is now replaced with non-OpenCV tech
* PIL can now load images in int32 or float32 greyscale, with or without ICC Profiles, and it shouldn't look too crazy (OpenCV was handling these before)
* deleted all the old OpenCV gif rendering and metadata scanning tech
* **if you would like to help test, please turn on `options->media->IN TESTING: Load images with PIL`. this used to be just a BUGFIX thing, but now it emulates where we actually want to end up. please send me any image files that render weird**

### better boot error handling

* if an error happens very early during boot, before the main Application event loop and splash screen are started, hydrus will now try and spin up a very small App and text dialog to show you the error visually! of course, if the error is Qt-related, then this won't work, ha ha ha, but you'll still always get the crash log
* the client will now boot if the 'already-running' file exists but is incomprehensible--it'll just log that it was. also, if any other problem occurs during the 'already-running' check, hydrus assumes it is not already running and prints the error to the log
* improved the 'can we write to the database folder?' test a little more. previously, if the db directory on boot was both missing and its parent was read-only, it would raise an error. now we correctly recognise that state as 'not writeable'
* also, the fallback to the userpath db directory now only happens if you do not set a `-d/--db_dir` launch parameter. if you specifically set a launch path and that place is missing or read only, the program will not boot! I am more comfortable doing this now that we have the dialog to better display what happened
* unified the 'what db dir are we using?' tests to one place
* also cleaned up some of the boot failure code, which was spamming things haphazardly

### string splitting and joining

* the String Splitter and Joiner now interpret `\n` in their splitter/joiner text as newline (and other replacements like `\t` for tab; anything python supports). in order to not break existing parsers, the old splitter and joiner strings will be encoded on update (any `\` will become `\\`)
* added some unit tests to test this behaviour for both String Processor types

### misc

* the system predicate parser is now plugged into the excellent `dateparser` library that we already use in downloader parsing. this thing can eat pretty much any date string you can throw at it, so if you type "system:archived time: since 01/05/2011" or "system:archived time: before 30 hours ago", it'll all work for almost any combination you can think of. it'll probably even work in your native language! the one big caveat is if you give a longer duration timestamp in the form 'x time units( ago)', rather than a specific date, it'll convert it to days/hours, ignoring years and months. since this stuff causes a ton of headaches, I am likely going to switch all the time-delta time predicates here to work on days/hours/seconds, and if you want to put 60 or 365 days, knowing what inaccuracy that implies means, then you can, rather than have me continually fret over and fail to deliver various leap year calculation problems. _calendarium delenda est_
* fixed some thumbnail rendering for another class of damaged gif--this time, gifs that are so garbagified that they change their resolution from one frame to the next and/or produce a sizeless, shapeless frame of a handful of bytes. this is now detected and the bad data discarded!
* if a video seems to have 0/None duration, the main native ffmpeg renderer (which is also used for thumbnail generation) can now handle it. the 'start x% in' value will be crazy, but it'll work
* fixed an error with mpv trying to inspect the duration of null media during various states of media viewer transition

### boring cleanup

* gave a quick pass over the ~250 small 'just show some text and a system icon' dialogs work across the program. unified all calls through one location, improved some strings and string formatting, added more exception logging, unified the dialog titles, differentiated information/warning/critical flags better, made 'critical' messages log their titles and text, and made it all thread safe in a nice invisible way to callers
* fixed some borked page/popup permission checks in the client api
* if a file transitions from 'no transparency' to 'has transparency', the client will now queue a thumbnail regen, just in case that tech has been recently added
* improved the formatting of what the main error-logging method actually prints to the log
* slimmed down some of the watcher/subscription fixed-checking-time code
* misc formatting cleanup and surplus import clearout
* fixed the discord link in the PTR help document

## [Version 554](https://github.com/hydrusnetwork/hydrus/releases/tag/v554)

### checker options fixes

* **sorry for any jank 'static check interval' watcher or subscription timings you saw last week! I screwed something up and it slipped through testing**
* the 'static check interval' logic is much much simpler. rather than try to always keep to the same check period, even if the actual check is delayed, it just works off 'last check time + period', every time. the clever stuff was generally confusing and failing in a variety of ways
* fixed a bug in the new static check time code that was stopping certain in-limbo watchers from calculating their correct next check time on program load
* fixed a bug in the new static check time code that was causing too many checks in long-paused-and-now-unpaused downloaders
* some new unit tests will make sure these errors do not happen again
* in the checker options UI, if you uncheck 'just check at a static, regular interval', and leave the faster/slower values as the same when you OK, then the dialog now asks you if that is what you want
* in the checker options UI, the 'slower than' value will now automatically update itself to be no smaller than the 'faster than' value

### job status fixes and cleanup (mostly boring)

* **sorry for any 'Cancel/IsCancellable' related errors you saw last week! I screwed something else up**
* fixed a dumb infinite recursion error in the new job status cancellable 'safety' checks that was happening when it was time to auto-dismiss a cancellable job due to program/thread shutdown or a maintenance mode change. this also fixes some non-dismissing popup messages (usually subscriptions) that weren't setting their cancel status correctly
* this happened because the code here was ancient and ugly. I have renamed, simplified, and reworked the logical dangerzone variables and methods in the job status object so we don't run into this problem again. 'Cancel' and 'Finish' no longer take a seconds parameter, 'Delete' is now 'FinishAndDismiss', 'IsDeleted' is now 'IsDismissed', 'IsDeletable' is now merged into a cleaner 'IsDone', 'IsWorking' is removed, 'SetCancellable' and 'SetPausable' are removed (these will always be in the init, and will determine what type of job we have), and the various new Client API calls and help are updated for this
* also, the job status methods now check their backstop 'cancel' tests far less often, and there's a throttle to make sure they can only run once a second anyway
* also ditched the needless threading events for simple bools
* also cleared up about 40 pointless Finish/FinishAndDismiss duplicate calls across the program
* also fixed up the job status object to do its various yield pauses more sanely

### cbz and ugoira detection and thumbnails

* CBZ files are now detected! there is no very strict standard of what is or isn't a CBZ (it is basically just a zip of images and maybe some metadata files), but I threw together a 'yeah that looks like a cbz' test that now runs on every zip. there will probably be several false positives, but with luck fewer false negatives, which I think is the way we want to lean here. if you have just some zip of similarly named images, it'll now be counted as a CBZ, but I think we'll nonetheless want to give those all the upcoming CBZ tech anyway, even if they aren't technically intended to be 'CBZ', whatever that actually means here other than the different file extension
* the client looks for the cover image in your CBZ and uses that for the thumbnail! it also uses this file's resolution as the CBZ resolution
* Ugoira files are now detected! there is a firmer standard of what an Ugoira is, but it is still tricky as we are just talking about a different list of zipped image files here. I expect zero false negatives and some false positives (unfortunately, it'll be CBZs with zero-padded numerical-only filenames). as all ugoiras are valid CBZs but few CBZs are valid ugoiras, the Ugoira test runs first
* the client now gets a thumbnail for Ugoiras. It'll also use the x%-in setting that other animations and videos use! it also fetches resolution and 'num frames'. duration can't be inferred just yet, but we hope to have some options (and actual rendering) happening in the medium-term future
* this is all an experiment. let me know how it goes, and send in any examples of it failing awfully. there is lots more to do. if things don't explode with this much, I'll see about .cbr and cb7, which seems totally doable, and then I can seriously plan out UI for actual view and internal navigation. I can't promise proper reader features like bookmarks or anything, but I'll keep on pushing
* all your existing zips will be scheduled for a filetype re-scan on update

### animations

* the native FFMPEG renderer pipeline is now capable of transparency. APNGs rendered in the native viewer now have correct transparency and can pass 'has transparency' checks
* all your apngs will be scheduled for the 'has transparency' check, just like pngs and gifs and stuff a couple weeks ago. thanks to the user who submitted some transparency-having apngs to test with!
* the thumbnails for animated gifs are now taken using the FFMPEG renderer, which puts them x% in, just like APNG and other video. transparency in these thumbnails also seems to be good!  am not going to regen everyone's animated gif thumbs yet--I'll do some more IRL testing--but this will probably come in a few weeks. let me know if you see a bevy of newly imported gifs with crazy thumbs
* I also overhauled the native GIF renderer. what used to be a cobbled-together RGB OpenCV solution with a fallback to bad PIL code is now a proper only-PIL RGBA solution, and the transparency seems to be great now (the OpenCV code had no transparency, and the PIL fallback tried but generally drew the last frame on top of the previous, giving a noclip effect). the new renderer also skips to an unrendered area faster
* given the file maintenance I/O Error problems we had the past couple weeks, I also made this cleaner GIF renderer much more robust; it will generally just rewind itself or give a black frame if it runs into truncation problems, no worries, and for gifs that just have one weird frame that doesn't break seek, it should be able to skip past those now, repeating the last good frame until it hits something valid
* as a side thing, the FFMPEG GIF renderer seems capable of doing almost everything the PIL renderer can now. I can flip the code to using the FFMPEG pipeline and gifs come through fine, transparency included. I prefer the PIL for now, but depending on how things go, I may add options to use the FFMPEG bridge as a testbed/fallback in future
* added some PIL animated gif rendering tech to handle a gif that out of nowhere produces a giga 85171x53524 frame, eating up multiple GB of memory and taking twenty seconds to failrender
* fixed yet another potential source of the false positive I/O Errors caused by the recent 'has transparency' checking, this time not just in malformed animated gif frames, but some busted static images too
* improved the PIL loading code a little more, converting more possible I/O Errors and other weird damaged file states to the correct hydrus-internal exception types with nicer error texts
* the 'disable CV for gifs' option is removed

### file pre-import checks

* the 'is this file free to work on' test that runs before files are added to the manual or import folder file list now has an additional file-open check. this improves reliability over NAS connections, where the file may be used by a remote process, and also improves detection for files where the current user only has read permissions
* import folders now have a 'recent modified time skip period' setting, defaulting to 60 seconds. any file that has a modified date newer than that many seconds ago will not be imported on the current check. this helps to avoid importing files that are currently being downloaded/copied into the folder when the import folder runs (when that folder/download process is otherwise immune to the existing 'already in use' checks)
* import folders now repeat-check folders that have many previously-seen files much faster

### misc

* the 'max gif size' setting in the quiet and loud file import options now defaults to 'no limit'. it used to be 32MB, to catch various trash webm re-encodes, but these days it catches more false positives than it is worth, and 32MB is less of a deal these days too
* the test on boot to see if the given database location is writeable-to should now give an error when that location is on a non--existing location (e.g. a removable usb drive that is not currently plugged in). previously, it could, depending on the situation, either proceed and go crazy later or wait indefinitely on a CPU-heavy busy-wait for the drive to be plugged back in. unfortunately, because at this stage there is no logfile location and no UI, if your custom db dir does not and cannot exist, the program terminates instantly and silently writes a crash log to your desktop. I have made a plan to improve this in future
* also cleaned up all the db_dir boot code generally. the various validity tests should now only happen once per potential location
* the function that converts an export phrase into a filename will now elide long unicode filenames correctly. filenames with complex unicode characters will take more than one byte per character (and most OSes have ~255 byte filename limit), which requires a trickier check. also, on Windows, where there is a 260-character total path limit, the combined directory+filename length is checked better, and just checked on Windows. all errors raised here are better
* added some unit tests to check the new path eliding tech
* brushed up the 'getting started with ratings' help a little

### client api

* thanks to a user, the Client API now has the ability to see and interact with the current popup messages in the popup toaster!
* fixed a stupid typo that I made in the new Client API options call. added a unit test to catch this in future, too
* the client api version is now 57

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
