---
title: Changelog
---

# changelog

!!! note
    This is the new changelog, only the most recent builds. For all versions, see the [old changelog](old_changelog.html).

## [Version 648](https://github.com/hydrusnetwork/hydrus/releases/tag/v648)

### misc

* I have disabled animated jxl parsing. some/many jxls are causing ffmpeg to go into an infinite loop when I ask it to see if the file is animated. I will harden the ffmpeg calling system and fix this for next week
* the 'update selected with current options' buttons that appear in the gallery and watcher download pages now pop in below the import options rather than squashing in beside. before, just clicking the 'file limit' checkbox with some of the list selected would often cause the sidebar width to overflow and make a horizontal scrollbar etc..
* system:duration now allows 'equal' and 'not equal'
* system:framerate no longer allows 'less/greater than or equal to' in its edit panel, and there is a label mentioning how fuzzy framerate is. the hardcoded quick-select framerate system preds in the 'system:duration' panel are now +/-1. I used to have a hack in the db search code to handle the fuzziness, but that was removed when I moved to the new number test system. I have not yet decided, but I may change all framerate calculations to be to the nearest integer, since that's pretty much what we display in UI
* fixed an error-raising typo when the database is trying to do a large db job based on a tag filter that has a namespace blacklisted. an example of this would be a `tags->migrate tags` for 'all tags except title: tags'
* if a user loads up a thumbnail grid that wants to have a virtual height greater than the Qt max (~16.7 million pixels, 2^24-1), I now pop up a one-time warning about it. these pages 'work' for ctrl+a type stuff, but you can't scroll below the magic line, and I suspect they are unstable
* fixed an instabality bug in the regular file right-click menu, when non-sha2356 hashes are async-populated in the menu after a db fetch (issue #1908)

### duplicates auto-resolution

* 'test A or B' comparators now support the spectrum of normal tag predicates: tags, namespace:anything, and wildcards. all their negated versions are also supported (-creator:anything, etc..). the search domain here is fixed at 'combined local file domains'/'all known tags'
* 'test A or B' comparators now support 'system:number of tags'. it works on 'all known tags'
* 'test A or B' comparators now support 'system:duration', 'system:framerate', and 'system:num frames', all under the 'system:duration' stub in the edit panel
* 'test A or B' comparators now support 'has audio', 'has forced filetype', and 'has transparency', and 'has duration', and all the 'has/has no' guys are now collapsed to the regular 'system:file properties' like in a normal search
* 'system:known url' and 'system:num urls' are collapsed in the edit panel down to 'system:urls'
* 'test A against B' comparators now support 'system:framerate'. a note in the edit panel reminds that these numbers are blurry, so you need padding
* the various 'test A against B' tests that are non-time based now accept a null value for a property and treat it as zero for comparisons. for instance, an image with null duration will now have less duration than a video with duration 3s. previously, if either file had a null value for the system pred in question, the comparator would fail, which is not how the rest of the search tech works in the program

### boring stuff

* fixed an instability bug in the new async defaulterrback handling when the main window has died
* if the user is running from source, the 'ffmpeg failed to render' exception now recommends that users try updating ffmpeg before doing anything else
* I cleaned up some autocomplete dropdown behind the scenes stuff. these guys have been rewritten and reworked so many times, they aren't beautiful
* all framerate calculations on media results now happen in one central location

### boring duplicates auto-resolution stuff

* the duplicates manager is now stricter about the order it clears work. it now clears the search work and then immediately the resolution work for each rule in clever-alphabetical turn. no more interleaved work
* the duplicates manager can now pack more search work into each work slot, and it reports the 'searching' state for a rule more reliably
* my mainloop daemons now have two sleep modes and differentiated wake signals to ensure they take forced breaks more reliably. I'm hoping to finally quash the problem of some workers (like duplicates auto-resolution) waking up too early and thus working far too hard when there are lots of other things (e.g. import queues) telling them there are various updates
* similarly, the potential pair discovery manager now uses this nicer wake system and will not hammer potential discovery work while file imports are going on. it previously had a system that said 'if caught up, ok to hammer'. now it keeps pace with its maintenance work time preferences, waking immediately if idle but otherwise smoothing out a rush of new work over a few seconds rather than going bananas
* duplicate auto-resolution rules now render themselves to a nice string with name and id when in various debugging modes
* when you open a one-file comparator edit dialog, the focus now starts on the tag text input box
* added unit tests for the normal tag metadata conditional file tests
* added unit tests for the num_tags metadata conditional file tests
* added unit tests for duration, framerate, num_frames metadata conditional file tests
* added unit tests for framerate media result value extraction

## [Version 647](https://github.com/hydrusnetwork/hydrus/releases/tag/v647)

### misc

* if the selected subtags have any whitespace, all taglist menus now offer 'copy (selected subtags with underscores)'!
* all existing users will see 'all local files' renamed to 'hydrus local file storage'. I did this for new users a couple weeks ago and we had no obvious problems, so now everyone gets it
* the similarly not-excellently-named 'all my files' is renamed for new users to 'combined local file domains'. I'll do everyone else in a couple weeks if no problems
* a file import options now has two 'do this if file is already in db' checkboxes--one for the auto-archive option, which now disables in the panel if you aren't auto-archiving, and the other to specifically say whether 'already in db' files should be re-sent to the stated import destinations, which matters for clients with multiple local file domains. this latter question is typically more annoying than helpful, so it is now default off **and will move to off, on update, for all file import options you have**. if you use multiple local file domains and want your 'already in db' files to be re-sent to a particular domain somewhere (I'm guessing we'd be talking a special import folder, rather than always), please go into that import context and edit the file import options back
* thanks to a user, 'system:ratio' and 'system:rating' predicates can now produce inverted copies of themself, so they can invert on a ctrl+double-click (also available in the predicate menu under `search->require`) and can auto-exclude clearly mutually exclusive predicates (you may not have noticed, but see what happens when you add system:inbox to a query with system:archive. this happens with a bunch of stuff). when you have something like 'system:ratio is 16:9', you'll now be able to replace it with 'system:ratio is not 16:9'. for ratings, you'll similarly get 'rated' and 'not rated' and like/dislike flips. they will also do taller/wider and 'less than/greater than' numerical or inc/dec ratings, but since these predicates do not yet support `>=` or `<=`, the inversion is imperfect. this will be fixed in future when I eventually migrate these guys to the newer object that, for instance, 'system:number of frames' uses (issue #1777)
* the default pixiv downloaders now say a more clear 'no support for pixiv ugoiras yet' when they veto an ugoira URL
* the 'notes' and 'zoom - index' in a navigable media viewer window are now background-drawn in the 'media viewer text' colour, matching the top file info text and the top-right stuff
* the command palette now displays and searches long page names without 'eliding...'
* the 'edit gallery url generator' panel now shows separate text boxes for the raw url generated and the post-normalised url if there is a matching url class

### duplicates

* duplicate auto-resolution rules now have a separate paused status and operation mode. it was not ultimately helpful to go for paused/semi/automatic; now it is paused/unpaused, semi/automatic. any rule that was previously paused is now paused and semi-automatic
* you can now pause/play rules from the normal duplicates page list with a button. you don't have to go into the edit dialog to pause or resume a rule
* I wrote a new hardcoded comparator for 'A has a clearly higher jpeg quality than B'. just a simple thing for now, no testing of specific value or anything, but maybe that'll come in future
* the rule edit UI now explictly says 'hey these work in name order so name them "1 - ", "2 - ", if you want to force one to have precedence'
* the sort order here is now my clever human sort (so '3 - ' is earlier than '10 - '), and the list in the edit and review panels sort the name column that way too
* deleted the 'pixel-perfect pairs - keep EXIF or ICC data' suggested rule--this is generally now covered by the 'pixel-perfect pairs' rule
* after a user suggestion, added 'near-perfect jpegs vs pngs' suggested rule. this guy uses a 'visual duplicates' comparator in 'near perfect' mode to check for what is for practical purposes a pixel-perfect jpeg/png pair, but with a couple extra caveats in the rule to ensure we don't throw out a useful png. it has comparators to select the jpeg that is of same or higher resolution (obvious), of smaller filesize (so we don't select a wastefully high quality jpeg of a vector or flat screenshot that is better as png), where the png doesn't uniquely have EXIF data (to err on the side of originality). also added a note about this guy in the help
* tweaked my visual duplicates algorthim, the edge detection part in particular, to better filter out heavy jpeg artifacts
* the cog icon beside a potential duplicate pair search context panel's count now has `allow single slow search optimisation when seeing low hit-rate`, which turns off my new optimisation. it looks like it performs very badly in some complicated edge cases, so now you can turn it off. I will gather more information and revisit this
* just to be a little more human, some arbitrary user-facing numbers around here are moved from 4,096/512/256/128 to 4,000/500/250/100
* to stay sane with the file search logic here, potential duplicate pair searches will no longer let you select a 'multiple locations' domain. just a single local file domain or the 'all my files'/'combined local file domains' umbrella
* fixed up a number of update-signals that bounce around the duplicates auto-resolution system. some maintenance tasks now correctly update all duplicate pages lists, not just for the page that started the job, and different jobs are careful to emit the correct 'rules changed' vs 'state changed' so various things update more efficiently
* duplicate auto-resolution sub-pages now only update their rules or rule number display when they are in view (or switched to)

### client api

* thanks to a user, the `/manage_pages/get_page_info` call now returns file selection data: `num_files_selected`, `hash_ids_selected`, and in non-simple mode, `hashes_selected`
* clarified in the help (and checked in code) that sending a client api file delete call to 'hydrus local file storage' will work on any local file, anywhere, as a 'permanent delete now' command. I wasn't sure if it would only work on currently trashed files, but we are good
* client api version is now 82

### blocking ui calls and a memory leak

* I discovered a long-time memory leak for busy clients at the last minute last week. I patched it just before release, and this week I have polished my patch. any time that an asynchronous 'thread to ui' job that waits on the ui to do something fails due to the attached ui widget dying early (think closing a dialog before an update routine finishes) now handles this situation appropriately to the caller and yields back the thread, in all cases (previously it could get stuck in a loop waiting forever for the dead window to respond, tying up that thread worker until program exit, and, in critical situations, when there were more than 200 current ongoing jobs, block other work indefinitely). there's about sixty of these calls across the code, including a bunch in the Client API when asking about pages, and some were not coping with all error situations nicely--they now do
* many of these calls also now navigate to a last-ditch ui widget anchor correctly (e.g. when they are doing something during boot/shutdown, when the main gui isn't available)
* reporting to a custom async errback is also now handled more gracefully. if the ui panel dies before a custom errback can be called, we now fallback to the default errback
* also did some smart typing here so an IDE can figure out what is supposed to be coming back from one of these

### boring stuff

* mpv file load error reporting is nicer, and simple missing file errors have their own hook
* fixed a logical issue in the new potential duplicates debug report mode, where it'd error out if you started the mode while a long job was still working
* fixed some bad newlines and old text in the running from source help
* cleaned up the default auto-resolution rule definitions, which was turning into a monolith
* I think/hope I have fixed an issue with loading the client when URL Domain Masks have bad data
* did some misc type linting, particularly around some non-beautiful clientside service juggling

## [Version 646](https://github.com/hydrusnetwork/hydrus/releases/tag/v646)

### misc

* I made mpv safer, both in the existing recycle system and the create/destruction test. if you tried the mpv test last week and got hangs when flicking quickly or when leaving certain media viewers on an mpv window, please give it another go
* when pages load themselves initially, the individual file load jobs are split into different work packets for the worker pool, so a handful of big pages will no longer monopolise the queue. also, if a page is closed, the initial load pauses--if it is undo-reopened, initial load resumes
* in the duplicate filter, when the difference in import time is less than 30 days, the 'imported at similar time (unhelpful average timestamp)' label is replaced with '_a little_ newer/older than' (issue #1898)
* if you have a very large database, it now requires up to 5GB of free disk space on the db partition to boot (the cap was previously 512MB)
* the db disk space check now occurs on shutdown too. if you have less space than it thinks is safe, it warns you that shutdown may not save correctlly and you should immediately free up some space. you have the choice of backing out or going ahead (issue #1895)

### low hitrate potential duplicate pairs search

* when potential duplicate pairs are counted or searched with just one small creator tag or a system:hash or something, and the final result is tiny, like 5 out of 750,000, it now won't iterate through your whole pair store but instead do a few blocks and then immediately come up with the answer in one step (issue #1778)
* this works by examining the running sample, and if we are confident the hit-rate is lower than 1%, the search strategy now inverts, and rather than iterating through 750,000 pairs to find 5 that match the search context, it runs the underlying (typically very small and fast) file search and runs those n files against the 750,000 rows, getting the 5 hits
* it should all just work, but let me know how it goes. does it kick in too late, too infrequently? are there search types it lags out at?
* I've added a 'potential duplicates report mode' to `help->debug->report modes` that spits a bunch of search data to log. if you are into all this, please run it on a variety of searches in IRL situations and copy/paste to me
* this was the last difficult job for duplicates auto-resolution. I've now got about a dozen small jobs for comparator tweaks and stuff, and maybe some smarter count update tech so we aren't resetting search spaces so much, and then this system is v1.0 done. I still feel good about hitting this by the end of the year

### boring duplicates stuff

* the routine that performs the 'search duplicate pairs in small increments' iteration now has a unified object to govern the search. it handles search space initialisation/reset, search progress, reset, block-popping, block-throttling, hitrate tracking, estimate confidence intervals, desired total hits, status reports, and now search strategy
* put this new fragmentary search into the potential duplicate search context panel count call and the Client API version
* put it in group/mixed filtering pairs fetch, the 'fetch some random', and the Client API version
* put it in the auto-resolution preview panel thumbnail pair fetch
* added another wilson interval confidence test to the fragmentary test to do 'are we 95% sure the hitrate is below x%?'
* added some logic to figure out if a one-time file search or the remaining iterative search is going to be faster, including if the caller only wants n hits, and I profiled stuff a bit so I could establish a magic coefficient
* the search space randomisation strategy is now based on whether the searcher is looking to stop/switch early or always wants to do the whole job
* deleted some old pair-fetch code that is no longer used by the Client API since the pairfactory overhaul
* updated my Client API unit tests for potential pair fetch to use nicer db mocking to handle some cleverer fragmentary update stuff properly
* wrote some neater db routines for navigating these questions
* cleaned up some search optimisations in here. not that significant, just edge cases

### boring mpv stuff

* all media viewers will now defer any media transition if they are currently looking at an mpv window that is still initialising. once the mpv window is ok, they'll recall the most recent set-media request and move on. this seems to fix the 'spawn errors/hang the client when scrolling through many mpv windows fast' issue in the mpv destruction test, and some related jank
* all media viewer top level windows (i.e. not the preview) now immediately ignore window close events if the current mpv player is not yet initialised
* in the new mpv destruction test, mpv windows are put in a holding queue and the mpv handle explicitly terminated before Qt widget deletion. previously this was handled by the python garbage collector, which is not ideal
* when any top level media window (i.e. not the previews) gets a close signal, if there are any mpv windows awaiting destruction, the window hides itself and waits until mpv is clear before allowing Qt to destroy it
* in both the 'is initialised?' and 'is cleaned up?' checks, we just go ahead if it has been 180 seconds
* fixed an mpv options-setting bug that could sometimes print an error to log on shutdown

### other boring stuff

* I think I fixed an issue where some thread jobs could not terminate correctly if the UI window they were attached to died before the job was done. this may be related to some hanging clients that have extremely busy sessions
* all multi-column temp integer tables in the db are now row-unique
* fixed an issue where a couple of shutdown-late CallAfter guys could try to do a CallAfter after Qt was down and the log was closed out, which would spam some error to the terminal
* cleaned up some media viewer close logic
* the thumbnail-preview focus-media logic is now more cleverly idempotent and stops spamming some excess update signals
* all async updaters have names that now render nice in the 'review threads' debug panel (we're chasing down a guy that seems to be stuck on one client)

## [Version 645](https://github.com/hydrusnetwork/hydrus/releases/tag/v645)

### mpv samsara

* background: after use, mpv players are not destroyed but released to a hidden pool and reused when another media viewer needs them. this is because, in my original implementation, attempting to destroy an mpv window caused an instacrash. many users have long-time struggled with situations where one of their persistent mpv players would get a fault due to an audio or video driver issue, such as a bug in restoring from system sleep, and thereafter their hydrus client would have one player good/one player bad, interlaced, as the media player swapped between them. there's a lame 'seal away bad mpv windows and create more' debug routine that ameliorates this, but the overall solution was just to restart the client
* this hopefully changes today. I have added `TEST: Destroy/recreate mpv widgets instead of recycling them` to `options->media playback`. if you are an advanced user ready to risk a crash, or in particular if you are someone who gets the 'every other mpv window is broken' issue, please try it. load up one video hesitantly, then try unloading it. try browsing between video and images, video and video. then, if you like, go bananas. do you get any crashes? I cannot get it to crash, but if I scroll as fast as I can through videos, I'll get some warnings in the log, and if I scroll through a loop of like ten audio files it will hang
* I am not sure why it does not crash any more. most likely I have simply cleaned up some really garbage code around here in the past couple of years and the problem is gone. it could also be a fix in mpv, mpv-python, or Qt in the same time period, or a mix of several of these things. it doesn't even crash with the legacy mpv interface I just moved from. in any case, I feel fairly good about this, and with a little more polish, if we have no big problems, I expect to make this mpv destruction/recreation the default behaviour going forward, with the recycling being another legacy mode people with problems can switch to. the only drawback of the new mode is a couple extra frames of delay to boot a video since we are initialising from nothing every time. I can address that in future in various ways, or users who care can just switch back to the legacy system
* in a related thing, I'm trying to chase down a long-time layout flicker bug where after a media viewer sees a single mpv window, image-to-image transitions in some clients get a flicker where the next image is at the top-left position of the previous for one frame before moving to the correct position. I get this on my IRL machine but only sometimes on my dev machine, and I'd like to see if this layout-poisoning still happens if the associated mpv window is fully destroyed (I figure the media viewer converts to some sort of hardware-accelerated compositing mode or something for the mpv window, and that introduces some delay or voids double-buffering-something in future layout calcs. maybe that can be unwound, maybe not, but keeping the window alive but hidden with a new parent is definitely not doing it)

### misc

* for new users, 'all local files' is renamed to 'hydrus local file storage'. this is to address confusion with the other umbrella local file service, "all my files", which I am also thinking of renaming. if nothing blows up, most likely r.e. some commonly used Client API script that happens to access services in a funny way, I will rename all existing users in a couple weeks, for v647
* the 'review services' panels now have a micro-FAQ description blurb for each service type
* the 'review bandwidth' window now sorts 'web domain' network contexts with subdomains below their parents, so you'll get site.com and then media.site.com right after. it was previously raw alphabetical on domain
* the four `network->pause->paged importer x` entries now wake all importers when they change, so all your import pages should update their UI and start allowed work immediately after you hit them (previously it would take up to thirty seconds to unpause)
* you can now select the strictness of the 'has transparency' test under `options->media playback`. the default is still the 'human perceptible' test I added last week, but if you like you can change it to 'not totally transparent/opaque' (what it was before) or 'has any alpha channel at all'. this affects rendering and the "has transparency" property for new files and future file maintenance jobs
* with help from a user, running a hydrus server or the client api in https mode with a proper cert now loads the full cert chain with issuers, letting a browser verify it properly. the old method was a very basic stub that was only sending the first leaf in the cert, and thus only appropriate for self-signed certs

### duplicates auto-resolution

* if an auto-resolution approve/deny action from the rule review panel takes longer than 4 seconds, it now boots a popup window with progress. if you like to fire off 1,000 approves and then close the window, you'll now see them finish up

### duplicates search tech

* there's a legacy situation in the duplicate system where potential duplicate pairs were not being delisted when one or both files in the pair were physically deleted. this is fixed today
* when a single file or a king of a duplicate group is physically deleted, all potential duplicate pairs it is part of are now removed
* added a new maintenance task under the duplicates page 'preparation' tab cog icon button to resync pairs to the currently local kings. this job will run in the update this week to fix us all
* your various duplicate pair counts will now line up better in edge cases such as 'system:everything' searches or when the count of actionable pairs nears zero. there won't be a bunch of spare unmatching pairs you can't get at
* there's still an issue here in that duplicate pair search operates in 'all my files', but the delisting happens when files leave hydrus local file storage, so if you manually delete a pair, it will stay in the master count until it is physically deleted. I considered making pairs delist when leaving 'all my files', but this would mean a delete/undelete cycle would re-queue the file for similar files search and it would make a 'set duplicate' action with a file delete component slightly logically frustrating, so I'm leaving it as-is now. let me know if your numbers are still so out of whack that it is distracting

### boring stuff

* fixed an intermittent Qt warning related to creating/showing menus with non-top-level-window parents
* fixed a source of mpv/Qt instability with the mpv event processing during window destruction
* fixed the mpv crash restart loop crash handler, which missed some recent rewrites
* across the codebase, all the 'all local files' and 'combined local file' nomenclature is now unified to 'hydrus local file storage'
* thanks to a user, added a note about `sudo xattr -rd com.apple.quarantine setup_venv.command` to the macOS 'running from source' help
* all the macOS .command scripts now start with `#!/bin/bash -l` with the `-l`, which forces a login terminal that has more env stuff like homebrow on your PATH. finding ffmpeg and such should be easier hereon--sorry for any trouble!
* the 7,000 line, 444KB main options dialog py is refactored into 38 sub files; all the panels now separated
* added a tl;dr section to the duplicates auto-resolution help
* updated some duplicates help to talk about trying too hard to saving disk space
* added a note about https://github.com/hydrusvideodeduplicator/hydrus-video-deduplicator to the normal duplicates help
* couple of misc linting fixes

## [Version 644](https://github.com/hydrusnetwork/hydrus/releases/tag/v644)

### new libraries

* the 'future build' test last week went well with the exception that some Linux flavours were unable to load mpv. I am folding these updates into the normal builds--
* Linux built runner from Ubuntu 22.04 to Ubuntu 24.04
* Linux built mpv from libmpv1 to libmpv2
* Windows built sqlite from 3.50.1 to 3.50.4
* opencv-python-headless from 4.10.0.84 to 4.11.0.86
* PySide6 (Qt) from 6.8.2.1 to 6.8.3
* if you are a Linux user and cannot load mpv in today's build, please move to running from source (I recommend all Linux users do this these days!): https://hydrusnetwork.github.io/hydrus/running_from_source.html

### docker package

* thanks to a user, the Docker package is updated from Alpine `3.19` to `3.22`. `x11vnc` is replaced with the more unicode-capable `tigervnc`, and several other issues, including some permission stuff and the `lxml` import bug on the server, are fixed (issue #1785)
* if you have any trouble, let me know and I'll pass it on to the guy who manages this

### misc

* the new 'show deleted mappings' eye icon stuff in manage tags now properly syncs across the different service pages of all manage tags dialogs that are open. if you click it somewhere, it now updates everywhere
* added `all paged importer work` to `network->pause` and clarified the three more specific pause-paged-work options. I noticed at the last minute that these guys don't wake the downloaders when unpaused (if you don't want to wait like ten minutes, atm you have to jog each downloader awake by manually poking them with their own pause/resume etc..), I'll fix this next week
* when a large page is loading during session initialisation and it says 'initialising' in the page tab, the status bar text where it says 'Loading initial files... x/y' is now preserved through a page hide/show cycle. when you switch to a still-initialising page, the status bar should now say something sensible (previously it was resetting to 'no search done yet' kind of thing on every page show until the next batch of ~~64 files~~ now 100 files came in)
* fixed a crash when a thumbnail suffers a certain critical load-processing failure. it now shows the hydrus fallback thumb and gives you popups

### ui optimisation

* the session weight in the 'pages' menu is now only recalculated on menu open or while the menu is open (it now has a dirty flag). this guy can really add up when a lot of stuff is going on
* same deal with the page history submenu. I KISSed some stuff here too
* when a file search is loading, the media results are now loaded in batches of 100 rather than 256. I also fetch them in file_id order, which I'm testing to see if it saves a little time (close ids _should_ share index branches, reducing cache I/O)
* on many types of page status update, the GUI is now only hit with a 'update the status bar' call if this is the current page. this was hitting a busy session load a bunch

### filename parsing

* I completely overhauled the background worker and data objects that kick in when you drop files on the program and the window appears to parse them all
* all paths that fail (zero size, missing, currently in use, bad filetype, Thumbs.db, seems to be a sidecar) are now listed with their failure reason
* the cog button to set whether paths within folders be added in the 'human-sorted' way (ordering 'page 3' before 'page 11') is removed. paths are now always added this way
* the paths sent to import or tag are now all sorted according to the #, which is just the order they were parsed. this way preserves some nice folder structure. previously I think it was sending whatever the current list sort was, which sounds good but it wasn't obvious that was happening
* paths are now processed in more granular, faster blocks
* remaining issues: although sidecars are now listed, they are now sorted at the top of the directory structure they parse from. also, we don't have a nice 'retry' menu action, which would be nice to retry currently-in-use or missing results. let me know if you notice anything else IRL

### file operations

* many file operations are now a lot more efficient, with fewer disk hits per job. I hope that export folders and other 'lots of fast individual file work' jobs will now be a good bit quicker
* file-merge operations now bundle their various file property checks into far fewer disk hits
* same for file-mirror operations
* same for dir-merge operations
* same for dir-mirror operations
* the 'same size/modified time' check in all file mirror/merge operations now re-uses a previous disk hit and is essentially instant
* all the 'ensure file is writable' checks are faster. there's still a slow 'file is writable?'' check however
* the 'ensure file is writable' checks on files before delete or overwrite now only occur on Windows. it doesn't matter elsewhere. I think there may be a problem now when doing stuff from Linux on read-only files a Windows network share, but the problem of read-only files appearing in the first place is mostly a legacy issue, so whatever. if you have a weird setup, let me know if you run into any trouble
* fixed an issue where on Windows a file-merge operation would fail if the destination differed from the source but was read-only
* when mirroring a directory, the 'delete surplus files from dest' work now happens failsafely at the end, after all other copies went ok, rather than interleaved
* the delete and recycle file calls now check for symlinks properly and delete only the symlink, not the resolved target. this was true previously in almost all cases by accident, but now it is explicit

### image transparency

* **on update, you will get a popup saying 'hey you have 12,345 files with transparency, want me to recheck them?'. I recommend saying yes**
* in hydrus, if a file being loaded has completely opaque or completely transparent alpha channel, I discard that alpha channel, deeming it useless. this also determines the 'has transparency' metadata on files. I had an opportunity to closely examine a bunch of real-world transparency-having pngs while doing the visual duplicates work this week, and I decided to soften my 'this transparency is useless' test to cover more situations. Where a value of 255 is 'completely opaque', I encountered one IRL file that had 560k pixels at 255, 442k at 254, 20k at 253, 243 at 252, and 22 at 251. another had a spackling of 1 or 2 pixels of alpha 208, 209, 222, 224, 225, 227, 235, 236, 238, 247, 249, 250, 251, 252, 253, and 254, and many similar situations. we've also long had many images with just one fully transparent pixel in a corner. this data is essentially invisible unless you are looking for it, and it is not useful to carry forward and tell the user about. thus, the rule going forward is now that an alpha channel needs a mix of values, specifically at least `2 * ( width + height )` or `0.5% num_pixels, rounding up to 1` pixels, whichever amount is smaller, not in the `>=251` top band and, in a separate test, not in the `<=4` bottom band. the minimum interesting state is now something like a one-pixel border of visible transparency or opacity around the file, and anything less than that is discarded as an artifact of an anti-aliasing algorithm or a funny brush setting
* the 'eye' icon in the media viewer top hover now lets you flip the 'transparency as checkerboard' options for the normal and duplicate filter media viewers on and off
* the 'eye' icon also lets you draw a neon greenscreen instead of checkerboard. this setting is available otherwise under `options->media playback`
* these three actions are also now available under the 'media viewers - all' and 'media viewers - duplicate filter' shortcut sets

### duplicates

* setting duplicate relationships via the buttons in the normal duplicates page, or by a normal thumbnail menu/shortcut action, or by Client API, will now trigger a 'refresh count' call in the duplicates page
* I think this might be painful IRL with lots of new 'initialising' loading time, so let me know how it feels. I strongly suspect I'll want to revisit how smart the refresh/update calls are here

### duplicates search math

* the new 'n pairs; ~x match' count estimate uses richer statistical math (Wilson Intervals) to now be better than ~2.5% imprecise 95% of the time. it adapts to hitrate and total population size. previously, it just stopped when `x>=1000` on a not-totally-random sample, which was apparently giving 95% confidence of better than 6.2% imprecision at high hitrates and much worse at low
* when the new incremental duplicate pair search works, there are now two sampling strategies. if we are doing a full, non-estimate count, the sample is sorted (to keep db index access at high throughput) and then randomised in large blocks to smooth out count-rate. in the other cases, being estimated count, duplicate filter fetch, 'get random pairs', and the auto-resolution rule preview panel, which can all end early, I now randomise far more granularily, ignoring sort entirely, emphasising a reliable hit-rate and early exit

### duplicates auto-resolution

* added 'pixel-perfect gifs vs pngs' as a static-gif complement to the jpegs vs pngs rule. I noticed a bunch of these in my IRL client. before you ask, yes ladies, I am single and available
* I updated my visual duplicates testing suite to do some alpha tests and profiled a number of transparent files against it
* the visual duplicates algorithm will now accept and test pairs where both files have transparency. the test is intended to be fairly forgiving and just makes sure the respective alpha channels match up closely. if you encounter false negatives here with `(transparency does not match)` reason in the duplicate filter, I'd be very interested in seeing them (issue #1798)
* if only one file has an interesting alpha channel, then those files are still counted as not visual duplicates
* the 'visual duplicates' suggested auto-resolution rule no longer excludes transparent files
* the 'visual duplicates - only earlier imports' suggested auto-resolution rule is now `A has "system:import time" earlier than B + 7 days`. just a little safety padding that ensures that files that _were_ all imported at the same time don't fail a test due to your subscription for the nice version hitting five hours after the worse
* I do not plan to make any more changes to the suggested rules. maybe we'll add something like the +7 days padding somewhere, or maybe the transparency test has some issue, but if you have been testing this system for me, I think the suggested rules are pretty good now
* I _thiiink_ the 'rescan transparency' job is going to reset affected files' status in potential duplicates. fingers crossed, when a file is determined to not actually be transparent after all, it'll get searched against similar looking files again and the auto-resolution rules will give it a re-go without the user having to touch anything. let's see how it goes

### ugoiras

* ugoiras with external duration (from a note text or simulated) now have the 'duration' icon in their thumbnails. this is also true of a collection that contains external duration ugoiras
* the way this stuff is handled and calculated behind the scenes is cleaned up a bit
* ugoiras with only one frame no longer get any external duration checks

### boring stuff

* added the Wayland env info to the Linux 'running from source' help
* added some stuff about `pacman` to the Linux 'running from source' help and reworked the 'which python you need' stuff into the three guides better
* sudo'd all my `apt install` lines in the help
* added some stuff about environment variables to `hydrus_client.sh`
* after a user suggestion, reordered the 'making a downloader' help to be URL Class, Parser, GUG (previously GUG was at the start, but it isn't the best initial stepping stone)
* gave the 'making a downloader' help a very light pass in some places
* fixed some dialog yes/no stuff in the database update code which was failing to fire with recent stricter UI validity rules
* I deleted the `speedcopy` test code and removed its entry from `help->about`. it didn't do quite what we wanted and there hasn't been any action on it
* reworked the old thread loop that used to spawn for local file parsing to the newer async updater-worker I've been using in a bunch of places

## [Version 643](https://github.com/hydrusnetwork/hydrus/releases/tag/v643)

### future build

* I am making another future build this week. This is a special build with new libraries that I would like advanced users to test out so I know they are safe to fold into the normal release.
* in the release post, I will link to this alternate build. if you are experienced and would like to help me, please check it out
* In my tests, _neither_ of these required a clean install. Linux users might like to do one anyway, since this week is a big shift for them, particularly if it has been a while or you are on an odd flavour
* the specific changes this week are--
* Linux built runner from `Ubuntu 22.04` to `Ubuntu 24.04`
* Linux built mpv from `libmpv1` to `libmpv2`
* Windows built sqlite from `3.50.1` to `3.50.4`
* `opencv-python-headless` from `4.10.0.84` to `4.11.0.86`
* `PySide6` from `6.8.2.1` to `6.8.3`
* I was going to do dateparser `1.2.1` to `1.2.2`, but there was a pyinstaller problem. we'll try again another time

### misc

* animated jxl is now supported! as previously, hydrus handles this with a new 'animated jxl' filetype. mpv wasn't super happy with the jxl files I was playing with, so I'm only enabling this for the hydrus ffmpeg-powered native viewer for now, like animated webp. all existing jxls will be queued for a rescan on update, so you don't have to do anything. performance is not amazing, and there's no variable frame rate support, and I'm afraid the tests here add yet more time to the jxl import process, but it does work. I'll keep checking in future for nicer (native Pillow etc..) solutions here. I looked at parsing jxls manually, like we do for quick png/apng differentiation and parsing num_frames etc..., but jxl appears to be pretty wewmode internally (issue #1881)
* in the 'edit times' dialog, when editing an individual time, the 'paste' button now eats milliseconds correctly whether you post a raw timestamp like `1738783297.299` or a datestring like `2025-10-10T12:00:00.123+02:00` (issue #1884)
* the manage tags dialog has a new "deleted mappings" text-and-icon that appears below the paste/cog icons if there are deleted mappings. it'll say "3 deleted mappings" and show you an eye icon. click the eye to show/hide deleted mappings. this display setting is now remembered through dialog open/close and is no longer accessible through the cog menu. this is an experiment, and I am open to doing more display options here to finally get on top of some finicky workflows
* hitting 'show deleted' in the manage tags dialog now redraws the list immediately; previously, it wouldn't actually show until the list incidentally repainted itself otherwise, e.g. after a click
* 403 (forbidden), and 509, 529, 502, and 522 network errors (bandwidth and gateway problems) no longer spam the log with so much server response text
* fixed some Qt crashes related to PDF import
* fixed some Qt crashes related to SVG import
* updated the 'eye' icon to svg. I'm actually happy with it; I even added a caruncle
* added an 'eye_closed' svg icon
* I think I figured out the 'list of tags in the media viewer background has a different line height than the hover window' bug that hit some Linux flavours

### duplicates

* by default, the client now searches for potential duplicates in normal time. this code now has such low per-file overhead that it isn't a bother
* 'potential duplicate pairs search' panels, such as in the duplicate page or the auto-resolution rule edit panel, now, by default, state an _estimate_ of the matching count once they have found 1,000 matches. for instance, it might say "513,547 pairs; ~210,000 match". it makes the estimate once it has found 1,000 matches and obviously stops working a lot faster this way. a new cog button let's you switch back to the old 'always precise' behaviour. let me know how this feels with IRL data!
* I examined making 'apply alternates/false positive to many files at once' work in a sane way (atm it applies to all internal pair combinations, so millions of relationships when you reach a single group of thousands of files), and it is not possible with the current file relationship storage. one solution I had discussed with users as a mid-way stopgap might have legs, but I think it is still insufficient. I have made a plan to improve this but will not do it in the push to finish auto-resolution. sounds like 2026

### duplicates auto-resolution

* added a 'AND' comparator type. this works like the OR one and allows you to clause a bunch of different comparator types together within a OR collection. I know some users have wanted to try something like `(A filesize > B AND A imported earlier B) OR (A filesize > 1.2x B AND A imported after B)` within the same expensive 'visual duplicates' rule. I think it is a little awkward, but have a think and see how it goes
* some more small tweaks for the suggested rules--
    - the 'visually similar pairs' rule now has `A filesize > B` rather than `>=` because the dialog won't ok without a definitive way to arrange A and B, hahaha. since a non-pixel-dupe visually similar pair of exactly the same size is unlikely, I'm fine not catching them here
    - the 'pixel-perfect pairs' rule now has `( A filesize > B ) OR ( A filesize = B AND A imported earlier B )`. previously, it just had `A filesize > B`. I have discovered that pixel perfect duplicates of exactly equal filesize are not uncommon (I particularly encountered it with some imagemagick resizes of the same original files done several years apart on different OSes, where I assume the only difference is some version enum in the file header), so I wanted a tie-breaker clause for them
* the auto-resolution help is now updated to talk about this
* an empty OR or AND comparator now gives an appropriate summary string
* I explored making resolution rules work on their queues in a more random order, but I backed off when I couldn't make it fast. there's a way to make this happen, but not a simple one, so I'll back burner it for now. the rules pull pairs in an order according to SQLite's whim, which often produces pairs featuring the same file in a row, which you may have seen in the pending action log. this is fine in some ways but it wasn't intentional and does give some minor headaches. unfortunately the most important thing about this guy is he runs with very low per-file overhead, so I'll leave things as they are for now

### mpv

* the new mpv interface is now turned on for all users. thanks to those who tested different situations for me. you should notice that mpv is slightly less laggy and generally more stable
* if you have a very old version of mpv and video suddenly throws a bunch of errors about `command_async`, please check `options->media playback->LEGACY DEBUG: Use legacy mpv communication method`
* I also updated this new code to be more polite about seek-scrubbing. if a new seek command comes in while a previous seek command is still working, it now waits until mpv is done and and then sends the most recent seek command received. it is now quite difficult to produce the 'too many events queued' error by scrubbing
* as the 'too many events queued' error is rare and no longer big deal, it'll no longer spam to the log
* I experimented with 'do a faster keyframe seek while dragging, and only an exact seek when mouse down/up', but it felt pretty bad with the low-latency keyframe seek caret bouncing around as you dragged, sometimes to the start of the video. I'd rather spend the CPU and have a nice experience
* added 'allow crashy files in mpv' to `help->debug->debug modes`. this disables the handler that would catch problems here and allows loading of files previously put on the blacklist. I notice that with the new async interface, I can't really get mpv to crash any more and while even totally whack files will spam the log, visually they'll just flitter between the first two frames or whatever. maybe we'll make this guy less strict in future

### boring stuff

* tweaked some database migration help
* clarified in the options that the 'idle mouse' setting is global, not just mouse over the hydrus window
* cleaned up some canvas painter handling to do nicer save/restore within draw methods

## [Version 642](https://github.com/hydrusnetwork/hydrus/releases/tag/v642)

### misc

* pushed a hotfix to source master to fix an issue with users running from source in python 3.10 or earlier. the deprecated `datetime` calls I updated are still needed in older python!
* fixed an issue with 'send all pages down from here and to the right', and a couple of similar commands, which were failing with 'PagesNotebook already deleted' errors when the pages being moved had been previously moved from another place that was now deleted (a parent reference wasn't being updated correctly) (issue #1880)
* the 'edit subscription' dialog list now lists the name/query column as 'display_name (query_text)' for any queries with a display name
* when you paste queries into a sub, if any existing conflicting queries have a 'display name' different to their query text, you'll now see them reported in the dialogs as this same 'display name (query text)''. also, the part that asks about reviving DEAD queries now sorts the list it shows you
* fixed an issue where a drag and drop export (in fact any file DnD initiated from within hydrus) would fail if you had the 'copy files to temp folder...' option set and you had a DnD export filename pattern that produced a path separator (e.g. a slash or backslash from `{tags}`). now the subfolders will be created within your temp dir just like how an Export Folder or manual export does it. I won't include that folder in the DnD yet--it just won't error and you'll get the same final filenames as before. maybe we can revisit this one day and DnD the whole subfolder(s)(?), so let me know how it goes
* the `locations->add to` menu no longer appears for files that are in the trash. in fact, you'll probably not see a `locations` menu at all for trashed files
* similarly, the central code that mediates all 'move/duplicate file to new local file location' actions now silently ignores files that are not in 'all my files' (i.e. stuff in the trash)
* removed some 'if there was a big bump of work, take a big break' logic from my tag display and duplicate file daemons. it was a nice idea, but it misfired a lot and there was no feedback. I'm pretty sure this thing was causing auto-resolution to take inexplicable breaks, so let's see how it feels now
* fixed some update signals in the auto-resolution review panel; if you have done some actions, switching to 'actions taken' tab will now correctly trigger an update; if you undo some actions, switching to 'pending actions' will trigger an update; undoing actions taken no longer triggers a no-op update of the 'actions taken' list (the log remains, even if undone); undoing actions taken triggers a numbers reset notification and wakes the potential duplicate discovery daemon, so the UI will quickly reflect the new 99.9% search status, and, if everything is caught up and good to work, trigger a very quick re-search and re-auto-resolution queueing-up of the undone file
* added `help->debug->report modes->idle report mode`, which talks about various 'idle mode' checks, like "IDLE MODE - Blocked: Last mouse move was 41 seconds ago.". it gets pretty spammy, so hover your mouse over the popup toaster 'dismiss all' button and click without moving or launch the program from terminal and watch stdout

### crash reporting

* last week, I tried to roll out an on-by-default crash reporting mode. unfortunately, I discovered late that it wouldn't play nice with mpv. I couldn't fix the issue fully, so this mode is now available but default off. you turn it on via `help->debug->debug modes`
* if you have regular crashes, please give it a go and we'll see what we learn. the only proviso is you absolutely cannot load up mpv and scrub through its seekbar while it is on or you'll just get a crash within seconds. a popup moans about this whenever you turn the mode on

### mpv updates

* _tl;dr: I wrote a thing for mpv and would like some advanced users to test it_
* last week's failed crash-handling exposed some ways I am being rude to mpv. I'm interrogating its properties and giving it commands from the Qt thread, and the mpv mainloop appears to be occasionally bugging out as a result. `faulthandler` was seeing the serious exception inside the mpv dll and thinking it was a crash and pre-empting the dll's exception handling. so, I wrote a new interface that, instead of interrogating mpv for its pause and video position sixty times a second for the seekbar, now asks mpv to notify us when those things change when it is happy to do so. the transfer of data to Qt is also all thread safe
* I do not know how well this new interface works with different mpv api versions, so it isn't on by default yet. if you are an advanced user, please hit up `options->media playback` and _uncheck_ the new `LEGACY DEBUG: Use legacy mpv communication method` checkbox. restart the client if you have instantiated any mpv windows. if pause and seek clicks all work and the seekbar updates to follow what you do, that's great. if it errors out or the seekbar stays at the 0 position, let me know please, and if you know it, let me know your mpv version. if this guy works out for anything but the weirdest and oldest mpv, I'll switch that option around to off for everyone and the old legacy interface will be the debug for odd situations
* unfortunately while this new polite communication method reduces the crashes with the new crash reporting tool, it doesn't stop them completely particularly when the seekbar is spammed with a drag. it seems some part of the wrapper library's event loop still causes the heavy exception inside the dll, I think probably because of overlapping events before an interrupt completes. oh well. hopefully I can revisit this in future
* I fixed a multi-player issue with the mpv crash handler that dealt with certain serious mpv loadfile errors (when the program pops up a 'MPV-crasher' dialog and button). it was not properly halting and reporting when you were looking at the problem file with an mpv window other than the first one created (mpv windows are re-used, and so typically meant this reporter had a 50% or 67% chance of continuing to play the problem file)

### visual duplicates tuning

* _tl;dr: visual duplicates works a little better. I still trust and recommend it at "almost certainly" confidence_
* I completed my visual duplicates tuning suite. this is something I have tucked away in the debug menu that lets me load up some files, programmatically generate 'good' and 'bad' duplicates of various sizes and qualities and with fake watermarks and so on, and then test them against each other with the algorithm so I can get a results at a wider range and faster than me doing it manually with print statements and my IDE's debugger
* the results were fairly successful, and I have retuned my algorithm to produce fewer false negatives while, I think, not introducing new false positives--
    - the simple quick scan is now more forgiving. more true duplicates will be allowed into the slower, more accurate test
    - I made the edge map test more forgiving, allowing more true duplicates to hit the tile tests. almost all true negatives are being caught at this stage
    - the tile tests are tuned to allow more 'probably duplicates' results. the 'almost certainly' tests were all good
* I am not sure if I want to pursue this work further to get a confidence level between 'probably' and 'almost certainly'. I will have a think about this
* I still plan to add transparency capability to this algorithm in future
* the algorithm is particularly vulnerable to severe resizes. images of similar size but different quality or subsampling are pretty doable, but anything that resizes to lower than 75% original dimensions has a pretty high false negative ratio
* I was not sucessful at re-weighting my algorithm to consider 444 vs 420 subsampling differences. there appears to be no easy linear translation
* I was able to produce a couple of false positives if I pushed it. these were generally a pair of ~60% resizes, at 60 jpeg quality, of a busy image, where one had a 25% alpha watermark. I am ok with failure at this level
* there are more mathematical options here, but I believe the next significant version of this would be an AI model. a lot of this is fuzzy and organic and involves many weighting coefficients derived through observing real world data, so I believe we would be looking at a simple model that eats the edge maps and tile data and learns with a not dissimilar tuning suite generating synthetic data. I probably do not have time for this, but if we ever end up getting TensorFlow or a similar library into hydrus, and perhaps if we want to categorise different types of alternates, I may have a serious think. alternately, we may end up farming this job out to an exe call or similar, and then it can be anything by anyone
* as always, if you come across any false positives (files that are not duplicates that show up as dupes, which at this stage likely means very subtle watermarks or alternates), I'd love to see them
* also, I triaged my remaining auto-resolution work in prep for a 1.0 release for all users. we're looking at four medium size jobs--removing potential pairs from rules when at least one file is manually deleted; some tag-based comparators; faster search when the hit rate is very low; and transparency in the visual duplicates test--and then about a dozen small jobs like a jpeg quality comparator, nicer pause for auto-resolution rules, and some metadata merge option tweaks

### advanced test stuff
* updated the 'test' versions for users who run from source--
* `opencv` is updated from `4.11.0.86` to `4.12.0.88`
* `PySide6` is updated from `6.9.1` to `6.9.3`
* I expect to do a 'future test' build next week

### boring stuff

* after the new event queueing code proved fine, merged the 110-odd `CallAfter` and `CallAfterQtSafe` calls together and ditched the old job-label system
* removed 50-odd now-redundant `IsValid` checks in the callafter callables
* fixed a potential crash in the login script test UI-reporting system
* cleaned up some of the 'move pages' code and deleted old stuff I no longer use
* added a couple of notes about 'potential duplicates' and similar looking files to the help and 'system:similar to' edit panel. also wrote some tooltips for the 'search distance' spin widgets and made them step 2
* the UI test now boots the review services panel. this guy has a bunch of stuff going on, including bandwidth calendar reports, and would have caught the datetime hotfix

## [Version 641](https://github.com/hydrusnetwork/hydrus/releases/tag/v641)

### Client API projects

* this past week, a user launched Hydrui, a new web portal for the Client API. it looks nice! repo: https://github.com/hydrui/hydrui / main site: https://hydrui.dev/
* a couple months ago, another user created 'hydrus-automate', a system that automatically applies metadata according to customisable rules like "all files with tag x should be sent to local file service y". repo: https://github.com/Zspaghetti/hydrus-automate
* I added both of these to the Client API help landing page and brushed up the links and descriptions there. also linked Hybooru, https://github.com/funmaker/Hybooru , a booru style read-only web wrapper for the client, which was until now only in the Docker readme

### important crash reporting update

* **EDIT: In further testing, this mode conflicted with mpv and _causes_ crashes within seconds of normal playback. this mode is disabled for now, I will work on it more next week**
* in a stroke of luck, I discovered a nice way to gather data during a crash (i.e. when the entire program halts immediately, no error popup etc..). if your boot gets as far as creating your client/server .log file, then any full on crash will now write the current stack for all open threads to the log file. hooray!
* so, if you suffer from regular crashes, please check your log files--there will now be a bunch of stuff in there. I am very interested in seeing it as it will help me to figure out what I did wrong
* the new crash handler code (using `faulthandler`) may interfere with other OS-level crash reporting or dumping, so if you happen to want to use WER or Linux Dumps to catch a particular crash, you can turn this guy off under `help->debug->tests do not touch->turn off faulthandler crash logging`

### merging clients

* I have written some help for how to merge a client into another. this has always been a patchwork process that I would talk about in an ad-hoc way, so now we have somewhere to point people that I can keep hanging things off as various problems are solved: https://hydrusnetwork.github.io/hydrus/database_merging.html
* I recall seeing some user(s) posting scripts that would do Client API timestamp migration or sidecar generations or similar. if you know of this, please link me to them or post them or whatever, and I'll integrate them into this document

### duplicates auto-resolution

* important fix: the duplicate-filter-like media viewers that launch from the duplicates auto-resolution preview and preview thumbnail pair lists now order their files same as the list does!! previously, the duplicate filter tech that tries to put the higher scoring file as 'File One' was still kicking in and, for some rules, presenting some pairs in the opposite order. sorry for the trouble, and thank you for the reports. also, the 'File One/Two' labels here are now, correctly, 'A/B' for these filters
* the duplicate-filter-like media viewer that launches from the 'review' auto-resolution panel's thumbnail pair list now has 'approve/deny' buttons on the right-hand duplicate hover window. these plug into the actual rule, and there's a couple neat things where the filter is clever enough to perform the filter's cleverer 'ok that file in the upcoming pair was deleted/merged in a previous decision; let's auto-skip it' tech on the batch
* added `duplicate filter: approve/deny auto-resolution pair` to the 'duplicate filter' shortcut set
* after saying "I don't expect to change the suggested rules again much" last week, I am changing the 'pixel-perfect pairs' rule to select for `A > B filesize`. previously it was `A < B filesize`. after looking at my and users' IRL test feedback, I think going for the larger file will tend to select for the original more frequently (CDNs tend to strip rather than add extraneous file header info, which is the only difference with pixel-perfect pairs) and that's what we should focus on. going for the smaller file only tends to save a handful of KB on average. although saving space is nice, we are already saving ~50% filesize in duplicate processing, so let's spend a few KB to hit the original version of files more often
* I also removed the `A filesize > B OR A num_pixels > B` comparator from the 'visually similar pairs' suggested rule. I was trying to be too clever--the three `>=` filesize, width, height rules cover the same question in a logically better and more KISS way
* brand new duplicates auto-resolution rules (when you click 'add') now start with `[ system:filetype is image, system:width > 128, system:height>128 ]`, and max search distance of 0
* if an auto-resolution rule is not semi-automatic, loading up the 'review' window defaults to the 'actions taken' page
* if an auto-resolution visual duplicates comparator test results in a rendering error, it no longer interrupts the user with a popup
* I gave the duplicates auto-resolution help another full pass: https://hydrusnetwork.github.io/hydrus/advanced_duplicates_auto_resolution.html
* I am close to launching this whole system for all users and the next few weeks will aggressively triage the remaining todo so we can hone in on a v1.0

### misc

* when you use a shortcut to apply a tag, like/dislike, numerical, or inc/dec rating to many thumbnails using a shortcut, this job is now split into smaller batches (e.g. of 64 files). if it takes more than three seconds, a popup with a progress gauge will appear (issue #1807)
* when an image fails to render, the error text is a little better and there's a special catch for 'seems like our rotation understanding changed' situations
* the 'test parsing' panels in the edit parsing UI now do nothing if you enter a blank URL after clicking the 'fetch data from an url' 'link' button
* the upper 'fetch test data from url' panel that appears in the 'edit page parser' version of this test panel, if the URL input is blank, will fetch the current example urls and put the top one in, just like how the dialog initialises
* added a link to the DeepWiki AI crawl of the Hydrus Repo https://deepwiki.com/hydrusnetwork/hydrus to the help, just as a reference. I ran into this by accident this week and was quite impressed. it isn't comprehensive and attributes more thought on my part than actually happened, but pretty much everything it says is correct
* improved error handling when a file recycle fails and added a briefer catch for 'filename too long' errors (happens for me in Linux when a tweet screenshot with a full filename is deleted after import, and Linux tries to add a .trashinfo suffix)
* under `options->files and trash`, you can now set an 'ADVANCED: do not use chmod' mode. if you have an ACL-backed storage system, you may be getting errors or audit logspam from when hydrus copies the permission bits to newly imported files. set this mode and you'll use different copy paths that only copy file contents and try to copy access/modified time over

### boring stuff

* I have added a couple ways to induce a crash to `help->debug->tests do not touch->induce a program crash`. one just calls `os.abort`, the other spams an immediate GUI repaint from a worker thread
* updated some deprecated twisted 404 Resources in the hydrus client api server setup
* when potential duplicate search contexts give a summary string, the '(not) pixel duplicates' part is now at the front, before file search info
* when potential duplicate search contexts give a summary string, they now say their max hamming search distance if not set to require pixel duplicates
* wrote a new class to handle the 'I have made a decision in the duplicate filter' action and associated pipelines. previously it was a hacky and ugly tuple doing four different jobs
* this new pipeline has a bunch of action and commit logic to handle a new 'approve/deny' decision as related to auto-resolution review panel, which now produces a rule-aware pair factory
* general cleanup for the duplicate filter now we don't have so many crazy tuples
* updated the duplicate filter commit pipeline to use the new decision object in many more places, simplifying it significantly
* also renamed a lot of the gubbins around here to use the new 'duplicate pair decision' nomenclature. it was all a mess before
* removed a 'I'm done with work after exiting' signal from the duplicates filter that was firing at the wrong time; replaced it with a pubsub from the actual thread that does the work. it still seems like the 'review' auto-resolution panel is not reacting to this signal correctly, nor 'undo approved action', so there's a bit more to do here
* cleaned up some deprecated datetime utc calls and a subprocess connections call
* the umask fetch when we try to give a file nice permission bits is now thread safe
* the duplicate 'preparation' tab cog icon now lists 'idle time/normal time' like everything else, not 'normal time/idle time'
* fixed a one-in-a-hundred chance of a duplicate file test unit test failing because of unlucky random number selection

## [Version 640](https://github.com/hydrusnetwork/hydrus/releases/tag/v640)

### new navigation features

* thanks to a user, we have some neat new UI tech--
* in a normal 'previous/next' media viewer, there is now a 'show random' button in the top-right hover. this jumps to a random position in the list. you can right-click this button to walk back, too! the 'media navigation:random/undo random' shortcut actions are settable under the 'media viewer - normal browser' shortcut set. note this is true random, not shuffle
* the Main GUI's `pages` menu now has a 'history' submenu that shows which pages you were last navigated to! if you have a giganto session, see how it feels to work with. I think I'd like to have some page navigation shortcuts tied to this
* a new shortcut action, `focus the tab the media came from, if possible, and focus the media`, which appears in the 'all' media viewes, 'normal browser', and 'media viewers' shortcut sets, now lets you focus the spawning page of this media viewer and the media you are currently looking at. this is in complement to recent 'show page/media' settings recently added on media viewer close for users who regularly use multiple simultaneous media viewers; this does the same, but it leaves the media viewer open and does not switch focus away. in a secret feature, right-clicking the 'drag media' button triggers this command

### duplicates

* added a 'auto-commit completed batches of this size or smaller' setting to `options->duplicates`, for the filter. if you finish the current batch without any manual skips, and the number of actions you made is equal to or less than this, it'll just confirm and load the next batch. the default value here is 1--let's see if that makes going through 1/1 batches in group mode a little nicer
* 'show some random potential pairs' is now an asynchronous job. it won't block the UI any more. while it is working, the button will be disabled
* after last week's 'potential duplicates discovery search' overhaul did not bring the house down, I have made it so any new file import will wake the daemon instantly if it can A) work now, and B) there are fewer than 50 files remaining in the search queue. thus, if you are synced on potential dupe discovery, you are going to see new imports searched for potentials and then actioned by auto-resolution rules within moments. again, let's see how this feels IRL. it feels like we need better discoverability of when files are deleted, but I'm of two minds about how to do it
* the visual duplicates detector is slightly better at determining RGB hue-shifts as alternates

### duplicates auto-resolution

* the duplicates auto-resolution daemon now has customisable work/rest settings like the other daemons under `options->maintenance and processing`. this was all hardcoded before
* the 'test A or B' comparator's edit panel now has nice OR UI. the autocomplete dropdown responds to shft+enter, has explicit OR/cancel-OR/rewind-OR buttons, and any 'edit OR' sub-dialog will have similarly limited system predicate support
* added two new hardcoded comparators: `A and B have the same "has exif" value` and `A and B have the same "has icc profile" value`. these match if A and B are both True or both False--useful if you don't want to accidentally promote a 'bare' file over one with extra metadata
* added a new 'OR Comparator' type. it holds a list of comparators and returns True if any are True
* I have overhauled the suggested rules--
    - the `A >= 1.1x B blah` is now `A > 1.0x B` in all cases. IRL feedback suggests this padding was neither helpful nor needed
    - the `visually similar pairs - eliminate smaller resolution` and `visually similar pairs - eliminate smaller filesize` suggested rules are merged into `visually similar pairs` that tests `A > 1.0x B num_pixels OR A > 1.0x B filesize` (while still checking A has bigger or equal filesize, width, and height to be careful)
    - the `pixel-perfect pairs - eliminate bloat` suggested rule is renamed to `pixel-perfect pairs`
    - `pixel-perfect pairs` and `visually similar pairs` no longer exclude files with exif or icc data either in search or from B--instead they have comparators that say `both A and B have the same "has exif/icc profile" value OR B does not have exif/icc profile` (i.e. Yes/Yes, Yes/No, No/No, but not No/Yes). users who care deeply about EXIF or ICC Profiles may wish to edit, but this is a reasonably safe compromise that will work for most
* if you have already deployed the suggested rules, have a think about if you want to change to the new defaults. if you do, although it is finicky, I recommend editing your rule in-place to reflect the suggested one, and then you'll keep your rule history (to do this, load up the suggested rule, check its new search and update the old rule to look like that, then export/import the comparators via clipboard, then delete the suggested rule again). note of course that if you change file search and comparators, your rules will reset their search and test status, which for the 'visually similar' rules could mean a lot of reset work! I don't think I'll adjust the logic of the suggested rules much more--although I guess I'll drop the 'no transparency' predicate when visual dupes can handle it better--but I do expect to tweak the 'visual duplicates' algorithm further, so I expect to encourage one more beta-tester test reset in the coming months

### downloader stuff

* fixed an issue with url class matching priority; domains were all being sorted with equal value after the recent URLDomainMask work. the correct behaviour is longer domains are matched first
* subscriptions are better about cancelling pending file work. if there are multiple queries with pending file downloads but the system has to stop before they are all done (this happens a lot when the sub is bandwidth choked), the overseer subscription call is new more aware of the stop reason and will skip checking (and loading/saving!!) the remaining queries for their (instantly failing) thoughts
* the routine that says 'hey record bandwidth for the original spawning domain if that differs from the file URL's domain' now works on file import objects that create multiple child import objects, such as pixiv multi-file posts. this tech ensures that bandwidth wait logic lines up across domains when a site stores files on an external CDN
* when a gallery url gets a 400 response from the server, the result is now 'ignored', with note '400', just like 403/404 handling. previously, this counted as a full error and was registered as a domain network error, which was causing trouble for those sites that give 400 for the overflow gallery page
* if the downloader grabs and tries to import an HTML file, the error note is more helpful. also, it catches JSON with the same hook now too

### misc

* when you delete lots of thumbs at once, the job now works in batches of 16 files (was 64 previously), and a popup with a progress gauge now appears after three seconds
* in the manage tags dialog, the 'file lookup' tag suggestion box's link button now shows any 3XX redirected GET URL the script ran across (e.g. if the MD5 gallery lookup was redirected to a Post URL), and you can now choose to open or copy (previously it just did open)
* export folders have two new checkboxes--'overwrite all sidecars on next run' and 'always overwrite all sidecars' to help control sidecar regen. some text scares you away from setting 'always do it' on a short period export folder  (issue #1801)
* the default period for an export folder is now 24 hours (previously 1 hour, which seems a little keen compared to how we ended up generally using these guys)
* all the close-page confirmation yes/no dialogs use the grammar 'Close "name"?'. previously they were a patchwork of different language that generally didn't say the name of the page

### client api

* `/manage_file_relationships/get_potential_pairs` has a new parameter, `group_mode`, a bool, optional, default `false`, that switches to group mode. in this mode, `max_num_pairs` is ignored; you get the whole thing
* `/manage_file_relationships/get_potential_pairs` has two more new parameters, `duplicate_pair_sort_type` and `duplicate_pair_sort_asc`, both optional, defaulting to 'filesize of larger file--largest first', to handle the new pair sort. they are an int enum and a bool
* updated the help to talk about these
* wrote unit tests for these
* the Client API is now version 81

### boring stuff

* I did the first half of a debug-level testing suite that will programatically tune the visual duplicates system. it eats a bunch of example files, generates various jpeg quality subsampling, and resize duplicates, and also makes some fake alternates with watermarks, artist corrections, and colour swaps. the second half will run these files against each other and profile how the internal variables of visual duplicates respond to the wider and more precisely defined range of differences, allowing us to choose better tuning coefficients and automating what I was previously doing manually fingers crossed, this will improve the confidence of visual duplicates, including across subsampling differences (it is bad at this atm), and make future tweaks or 'now we can handle an alpha channel' tech easier to pull off
* updated/added unit tests for client api potential pair searching when: there are no special params; there is a search space; there is a min number of rows set; there is a specific sort set; group mode is on
* wrote up unit tests for the new exif, icc profile, and OR auto-resolution comparators
* fixed up some imperfect regexes in the unit tests
* wrote a widget for editing a list of comparators; the selector and comparator OR panels now use this
* broke the duplicate filtering page into nicer panel classes. there's still a bit of Qt Signal mess under the hood, but the preparation and filtering tabs are no longer all mixed into the same place
* if a dupe filter page does not find pairs to show in the 'show some random pairs' button, the page state (used mostly in client api reporting atm) is now correctly reset from 'loading' to 'normal'
* renamed a bunch of patchwork 'work_time'/'time_it_took' variables in my different daemons to 'actual/expected_work_period'
* the mixed duplicate pair factory now takes its 'no more than' value during init, decoupling it from the options

## [Version 639](https://github.com/hydrusnetwork/hydrus/releases/tag/v639)

### misc

* `system:number of tags` and `system:tag as number` have a nicer new namespace selection widget
* fixed the duplicate filter group mode finding a new group after the previous group was resolved. I messed this up in last week's rewrite and it slipped through testing
* huge multi-column lists handle large selections much more efficiently, particularly when they have lots of buttons. all the various logic that handles 'should this accompanying button be enabled?' and so on now uses calls that work much faster when there are thousands of items selected. in my tests, a sublist with 5,000 test items now updates to a new selection in under 30ms--previously it was about a second. similarly, pasting all those items to a new list now takes about six seconds, whereas previously it was locking up for ages and ages, perhaps forever (issue #1737)
* fixed an issue where the 'move media files' dialog was saying all files were in their ideal location if the thumbnail location override was not set. this was happening because an error was being quashed over-eagerly. if this dialog has a similar problem in future, you might get some spammy reports, but it'll show. also a side thing, the 'set' button of the thumbnail location override no longer disables if you have a path set--feel free to move it to a new location in one step mate
* the system that positions windows off the topLeft corner of their parent is now more forgiving of unusual window manager frame geometry. if you kept getting 'hey I just rescued a window from ( 24, -14 )'-style popups every time you open the options off a maximised main GUI, let me know what happens now--are your dialogs appearing offscreen, auto-repositioning to (0, 0), or is everything good now?
* if you are feeling clever and can get an OR predicate into the duplicates auto-resolution 'test A or B' comparator, it now works! I'll brush up the UI in future to make it easy to enter an OR here (issue #1790)

### potential duplicates discovery

* I have overhauled the daemon that looks for new potential duplicate pairs. this guy no longer searches for pairs during shutdown maintenance (I'm generally trying to retire shutdown work), but you can now tell it to run in idle and/or normal time, with separate work/rest settings under `options->maintenance and processing`
* your settings here will mostly reset to defaults this week, sorry! default is to run in idle time but not active time, with some conservative work/rest ratios
* a critical section of database code that finds outstanding eligible files to perform the similar files search on is now optimised for clients with larger numbers of files. there will be a one-time CPU cost for each search distance you run at, and thereafter this thing should run like greased lightning even if you have millions of files, reducing per-job overhead for all similar files search
* when you force work through the duplicate page 'preparation' tab, it now works through a pause/play button and there is no separate work popup; it now just updates the bar in front of you
* I'm interested to know how 'run in normal time' feels for clients that have a lot of imports going on. I haven't gone for instant reaction to new files yet, but if it is idling with all other work done it'll get to any new files within about ten seconds, and the auto-resolution system _will_ react instantly to new potential duplicate pairs. might be laggy, might be cool, might be confusing as files in downloader pages are deleted before your eyes. the super ideal here would be to collapse the whole operation into the single import job and return something like 'file was duplicate' instead of 'already in db' as the import status, but we'll see how this does
* the 'reset potential search' cog-button task now resets the search for all eligible files. previously, I was trying to be cute and only reset search for files that previously found a potential pair, but the, say, ~37% filled progress bar after reset was confusing and not actually what the maintenance task wanted. KISS

### profile mode

* `help->debug->profiling->profile mode` now works on Python 3.12+. newer version of python are more strict about how profiling operates in a multi-threaded environment, and hydrus's profiling now obeys these rules. it turns out hydrus was always getting some _slightly_ gonk numbers here in busy multi-threaded situations, or at least many jobs were being truncated, which explains some inexplicable results I've seen over the years
* profile mode is now split into four exclusive types--client api, db, threads, and ui. the menu and html help are updated to talk about these. most users will want 'db'
* 'threads' and 'client api' profiles will sometimes include a bunch of truncated 'EXCLUSIVE: (job) ran in 17ms'. this is me salvaging a difficult situation with a still-useful number. don't worry about it!
* Python 3.12+ adds some cool tools here, and I expect to expand to some 'profile everything going on mate' modes in future to capture deep Qt things my specific modes do not
* there's an ancient shortcut for 'turn profile mode on'. this now does 'db' profile mode; it'll probably do something else later, or I'll retire it

### boring stuff

* if you boot the client or server in a python environment that does not have the requirements.txt stuff installed, the client now recognises this and gives a nicer error saying 'hey, I think you need to reinstall/activate your venv', rather than the old 'hey you don't have yaml' error
* tweaked the client's critical boot error handling so that it shows a nicer english error message first and then the full traceback in a second dialog
* added some unit tests for OR predicates within Metadata Conditionals
* fixed a deprecated unit test call. thanks to the user who pointed this out. this is not the first time this specific thing happened, so I'm switching up my testing regime to catch this in future

### boring overhauls and refactoring

* wrote a new MainLoop Manager for the potential duplicates search and some maintenance and numbers caching
* overhauled the potential duplicates search tree maintenance call to have less overhead and be happier working in tiny chunks. it is now continually maintained throughout search work
* wrote a count cache for the shape search store for the new daemon (previously it counted manually); it is updated as the underlying store changes
* hooked up new notification paths for new shape search counts or brance rebalancing work. these paths are simple and comprehensive, so the new guy should be a bit more reliable for unusual file maintenance jobs and so on that may alter the search space a little
* added some safety code to the new similar files search daemon to stop an infinite loop if the search record store has non-searchable items for some reason
* cleaned up the Duplicates Page Sidebar maintenance page a bunch. there was just a ton of cruft to go through
* to untangle some imports, moved duplicate score and visual duplicates gubbins out of `ClientDuplicates.py` to a new `ClientDuplicatesComparisonStatements.py`
* collected pretty much all the profiling and query planner gubbins like start time and job count and printing tech from `HydrusController.py` and `HydrusGlobals.py` to `HydrusProfiling.py`. I cleaned a bunch of it up along the way
* brushed up some of the database migration help r.e. missing locations and the pre-boot repair dialog
* the core `CallAfter` method used by many thread-to-Qt comms is a tiny bit more stable/thread-safe
* misc linting work, including clearing out some legacy unresolved references
