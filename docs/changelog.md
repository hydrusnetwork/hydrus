---
title: Changelog
---

# changelog

!!! note
    This is the new changelog, only the most recent builds. For all versions, see the [old changelog](old_changelog.html).

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

* filename parsing: 
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

## [Version 638](https://github.com/hydrusnetwork/hydrus/releases/tag/v638)

### misc

* thanks to a user, epubs with svg or IBook image cover pages will now get nice thumbnails. epubs with html covers will no longer spam error info to the log
* the default pixiv URL Classes are tweaked a little so they now want to keep their `www.`. when I did the multi-domain url class update the other week, which unified domain parsing and normalisation, some `www*.` removal loopholes were fixed and suddenly the pixiv downloader had a bunch of redirects going on behind the scenes because they are still firmly a `www.`-preferred site. no great harm done or subscription inefficiency or anything precisely because these URLs are considered the same now, but it was ugly in places so I've cleaned it up on my end. what to do about `www.` in future is perhaps something to talk about, and in context of an eventual _en masse_ URL normaliser/converter--maybe URL Classes will get an option regarding `www.` so we can handle various legacy issues like this. also for some reason the 'pixiv file api' url class was saving associated urls, which I've turned off
* the media viewer's prefetch system has better error handling for images with unknown resolution
* when exporting files, if the export filename produced by the pattern is the empty string, it now (again) falls back to the file hash. in a recent round of rewrites, it was falling back to the string 'empty', so you'd get a scatter of annoying 'empty (7).jpg' filenames
* when viewing an animation with the native viewer, hitting the shortcut for 'seek media: negative time delta' repeatedly near the beginning of the video, either on a slow video or a paused one, will no longer let the viewer move from the 1st frame to the undefined 0th frame (issue #1793)
* updated the first/previous/next/last media viewer navigation arrows to .svg icons and renamed them behind the scenes to position_x so they line up better alphabetically
* brushed up my newer .svg icons with some nicer gradients and drop shadows

### duplicates

* several duplicates auto-resolution thumbnail lists now spawn full-fledged duplicate filters instead of media viewers. these will navigate the full list, not just the one pair, starting with the most recent pair you have selected. the lists that have this tech are: in the 'edit rule' panel, the 'preview' tab's 'passed the test' and 'failed the test' lists; and in the 'review' panel, the 'pending actions' tab's main list
* the duplicate filter here has the normal actions. I'd like to add 'approve/deny' buttons for the 'pending actions' panel in future
* the 'send pair to duplicates media page for later processing' button in this case now sends the pair to a new/existing page called 'duplicate pairs'
* the 'send pair to duplicates media page for later processing' button on the duplicate right-hand hover no longer has the 'fullscreen' icon, which was changed last week and doesn't work there any more. I gave it the 'copy' icon for now
* the iterative duplicate search routines that generate grouped or mixed pairs for the filter and the one that generates the count of the current search for a duplicate search context panel are now auto-throttled. they'll start at 4096 items and speed up (reducing overhead) or slow down (reducing system latency) based on live timings, aiming for about 0.5s per work packet, which for almost all users will mean a prompt acceleration. if you have been staring at a lot of '2,000,000/4,100,000 ... 0 found' duplicate progress texts recently, let me know if this changes things at all (issue #1778)

### referral url logic cleanup and policy change

* the downloader is now stricter about which url it will prime child objects to use as their referral url (i.e. the file result from a gallery hit, one of multiple file objects created by a multi-file post, or a 'next gallery page'). the referral url given to the child object is now, strictly, the same URL that was actually hit at the parent stage, _including_ redirects. if you use an API redirect, that is now the referral URL. if the server 3XX redirects you, that is now the referral URL
* previously, it was mostly the 'pretty', pre-API redirect URL used, unless it was for some reason set otherwise, and unless there was a 3XX, in which case it was always that(?). it was a mess. rather than trying to be cute, I'm going for clear and accurate KISS. if hydrus hits an URL, that's the referral for the child, unless the URL Class of the child overrides it, and if it overrides it, it overrides _it_
* advanced downloader creators will recall that URL Classes can override, nullify, or modify the given referral URL. if you have a delicate URL Class here that uses both an API Redirect and a referral URL regex transformation that presumably eats the pre-API URL as a base, I am afraid I may have broken your downloader. I hate to do this, but I need to clean up the logic here and I think my decision causes the least damage and makes for the most reliable new rule going forward
* when you right-click a file object and look at 'additional urls', it will now state if there is an API/Redirect, and what URL that will be
* when you right-click a file object and look at 'additional urls', it will now state if the referral URL is due to be modified by URL Class rules. the URL Class is of course that for the expected URL to fetch, i.e. after API/Redirect conversion
* when you right-click a gallery object in a gallery/check log, you now see an 'additional urls' submenu with the above API/Redirect and Referral URL stuff, and you'll see any fixed http headers
* note in this subject that as part of moving from `requests` to `httpx`, I'm strongly considering handling redirects myself, and that will appear in the logs here as a child object with the new URL. I'd like the logs here to be better logs of what happened, in full, with less voodoo
* issue #1789 is related here, but I don't think I have it actually fixed

### boring stuff

* moved the duplicates filter canvas (60KB now) to its own `ClientGUICanvasDuplicates.py` file
* overhauled the duplicates filter canvas to be agnostic about the source of its list of pairs to action. it now takes a new pair factory, and all async work to initialise the search space and do grouping and fetching and sorting is now handled on the side of the factory
* cleaned up some of the not-great async logic around here during the decoupling, which clarified some things, and committed some fresh sins too
* wrote a pair factory for the thumbnail lists
* misc URL handling code cleanup and variable normallisation
* added a couple notes regarding mpv and ffmpeg in macOS to the 'running from source' help; thanks to the feedback from users who recently made the migration

## [Version 637](https://github.com/hydrusnetwork/hydrus/releases/tag/v637)

### duplicates auto-resolution

* 'test A or B' comparators now support 'system:time', for the four main time system predicates (import time, modified time, last viewed time, archived time)
* 'test A against B using file info' comparators now support the same 'system:time' stuff, so you can now mandate, say, that "A has system:import time earlier than B". I also wangled a time delta in there, so you can say 'A was imported more than three months earlier than B' if you like
* I brushed up the comparator UI for time; instead of `<` and `=`, you'll see a vertical stack of 'earlier than', 'roughly the same time as' and so on. also, the deltas for `+/-` and the B delta are full time widgets, so you set the time you mean and don't have to care about converting to milliseconds. this all percolates to the comparator summary string too.
* same deal for `system:duration` in that panel--it now has a time delta for the absolute `+/-` test and the B delta, and has a time-aware summary string
* I added 'only earlier imports' variants for the 'visually similar pairs' suggested duplicates auto-resolution rules. I am sure there are many edge cases, but I feel that these are pretty good 'near-zero false positive' rules to try out
* the 'edit duplicate auto-resolution rules' panel now has export/import/duplicate buttons
* the 'comparison' tab of 'edit duplicate auto-resolution rule', where you edit comparators, now has export/import/duplicate buttons

### duplicates

* in the duplicate filter, jpeg subsampling and quality info is cached in a nicer, more thread-safe way. certain laggy calculation situations should be more stable. I am not sure if this was the source of the crashes some people have had, so if you still get them, please let me know

### misc

* for the new `/db/static` overwrite tech, a .png icon in the db dir now overrides an .svg in the install dir. if you chose to add it, I'll prefer it
* the star.png used for favourites buttons is now an svg
* the fullscreen_switch.png used in the media viewer is now an svg, and more like the typical icon for this
* I forgot to do some metadata regen on epubs last week, so any existing epubs probably got stretched thumbnails. soon after v637 boots, your epubs should double-check their resolution ratios and regen any busted thumbs (issue #1788)
* I overhauled one of the ways that threads can give Qt work to do, making it more Qt safe. there were about 80 calls that used this system, mostly stuff like initialising a label or focusing a button in the event loop immediately after a panel appears. fingers crossed, these will be much more stable in edge cases when, say, a dialog insta-closes before an initialising job can fire

### big brain subscription logic improvement

* when subscription queries compact themselves down to the (typically 250) newest URLs, they now recognise that child URLs ("Found 2 new URLs in 2 sub-posts.") should not be counted. in sites where the gallery pages have potentially high count and each gallery-parsed post URL can also each produce many files (e.g. Pixiv manga), 250 file import objects could only be, say, 21 top-level Post URLs, significantly less than the gallery page provides, and the safety checks here, which are tuned to recognise 100 contiguous Post URLs 'already in cache', were overflowing every n checks and causing some post re-downloads. hydrus should be better about recognising this situation
* the compaction routine does this by grouping file import objects into parents, including nesting parents, and only culling on the top level. when things are confusing, it tries to fail safely in complicated situations, on the side of reducing compaction aggressision
* if you have manga subs, they may well grow to be like 4,000 files. let me know how it all goes
* a similar bit of logic that tests the number of items found versus the pre-gallery-sync size of the file log now uses this tech to estimate that size (previously it did some hacky referral url checking stuff)
* thanks to the user who worked with me to figure this one out
* this is more evidence that I should write a layer on the database level URL storage for 'subscription x saw this URL', and then we wouldn't have such a problem

### base64URL

* String Converters can now encode/decode with Base64URL, which is a variant of Base64 that uses `-_` instead of `+/` and where '=' padding is encoder-optional (and not added here) to make inclusion in an URL parameter simpler
* when I _decode_ (convert from base64 to normal text) by base64 of either sort now, I add any extra `=` padding that is needed, no worries
* String Matches can now have a 'character set' of Base64URL (`^[a-zA-Z\d\-_]+={0,2}$`) or 'Base64 (url encoded)'' (`^([a-zA-Z\d]|%2B|%2F)+(%3D){0,2}$`)

### boring stuff

* removed the macOS build script and such. I left the macOS build files in place and copied my various .yml workflow scripts to `static/build_files/macos`
* fixed up some bad layout flags in the duplicates auto-resolution comparator edit panels
* swapped the trash and retry buttons in the gallery downloader page sidebar
* similarly moved the trash button to the end in the watcher downloader page sidebar
* wrote unit tests for predicate value testing (i.e. for Metadata Conditionals) for import time, modified time, last viewed time, archived time
* wrote unit tests for predicate value extracting (i.e. for relative file info comparators) for import time, modified time, last viewed time, archived time
* wrote unit tests for the new Base64URL encode/decode and added some clever stuff to check for the `+/-_` stuff
* wrote unit tests for the new Base64 character set filters
* fleshed out some of my Base64 unit tests to catch a couple extra situations
* wrote unit tests for my new query compaction parent-grouping tech and 'master url' counting routine
* moved the 'CallAfter' thread-to-qt calling system to a new file `ClientGUICallAfter.py`, and made it safer
* moved an overhead-heavy alternate Qt-safe CallAfter to this leaner pipeline
* renamed `PREDICATE_TYPE_SYSTEM_AGE` to `PREDICATE_TYPE_SYSTEM_IMPORT_TIME`
* the `NumberTest` init no longer flips from `+/-%` to `=` if the inherent 'value' is 0--this was not helping in duplicates auto-resolution, where the value is not used and in some cases initialises to 0
* updated the predicate object so null/stub preds (which until comparators generally only appeared in memory as autocomplete dropdown system preds) can always serialise
* if a menu item label is longer than 128 characters and thus...elides, the tooltip will no longer have doubled ampersands (generally affects urls in menus)
* added a catch to the `help->about` error reporting; if you have "sio_flush" in an mpv import error, I now say to try running from source

## [Version 636](https://github.com/hydrusnetwork/hydrus/releases/tag/v636)

### multi-domain URL Classes

* URL Classes now support multiple domains! you can set multiple fixed domains like `example.com`/`example.net` and multiple regex rules like `example\.[^\.]+`. if a given URL matches any of the patterns, the URL Class can now match
* in the URL Class edit panel, there's now a 'domain' box panel for it all. by default, you'll start in a simple mode with a single text input for a single domain, but you can flip to an advanced mode that shows two add/edit/delete lists for the underlying fixed and regex rules
* the 'match subdomains' and 'keep matched subdomains' checkboxes are also moved into this panel
* two new 'test'/'normalised' text boxes let you enter a test domain to see if your current rules match it, and what it will normalise to (think subdomains) according to everything set
* if you are a downloader creator, please play with this, but I'll say don't go crazy yet. I feel good about it all, but this is new ground so I don't know if there's something we haven't thought of. also obviously be careful with the regex stuff. learn the difference between `.` and `\.` or you might end up matching more than you think!
* I believe this tech is fundamentally cool though, and if you know a new site uses a particular content engine you already have support for (e.g. some specific booru), then just adding its domain to the list for the file and gallery page URL Classes should essentially activate the downloader for that whole site. only thing you'd need for a full downloader would be a new GUG. no new parser example urls or any of that stuff needed. as a little test on my dev machine, I was able to merge the e621, e6ai, and e926 URL Classes with minimum fuss in about two minutes and nothing broke!!
* in terms of layout and bells and whistles, I think we might want some import/export copy/paste stuff here, let me know how it works for you IRL. the lists were already huge, so I didn't wrap them in nice labels saying 'these are the raw domains' and 'these are the regex rules', but I think I may need to pretty it up. I also added collapse/expand arrows to the three main static boxes in the edit URL Class panel, so I hope that helps if you are dealing with twenty domains or something
* if you have an URL in the media viewer top-right menu that matches a URL Class more complicated than just one fixed domain, it now says the domain of the URL after the name of the URL Class. e.g. 'coolbooru post (somecoolbooru.com)', so you know what's going on

### unfortunate macOS App news

* this is the last macOS App I will be putting out, and there will not be a Silicon App from me. I am sorry!
* Github are retiring the old macos-13 runner (intel) that we have been using, and for the past few weeks I've been trying to build both Intel and Silicon builds on the macos-14 runner. unfortunately, I could not get the retroactive Intel one to build, and Silicon Apps have special signing requirements. I bashed my head at the signing problem, and I was very hopeful I'd have a 'future build' test this week, but unfortunately I ran up against a hard technical barrier and I do not have the time and macOS expertise to properly overcome it. I also suspect the self-signed hole we had hoped to fit through will be closed in the not so distant future. we've been coasting on a very hacky App structure for a long time, and it would need a couple full passes to work in the new system, so I simply had to call it. even if that overhaul worked out, we'd still be locked to older Python 3.10 due to pyoxidizer and looking at asking users to override Gatekeeper quarantine
* thus, I now recommend that all macOS users run from source going forward. although it is a small one-time headache to set up, it'll run much better than the old Intel App, which was likely being Rosetta'd to your newer machines. I have brushed up the 'running from source' help and written a small specific section for you here: https://hydrusnetwork.github.io/hydrus/running_from_source.html#migrating_from_an_existing_install
* all the help is updated to talk about there being no App build now; let me know if I missed anything
* let me know how you get on and if you have any trouble getting a source release going. I regret the sudden halt here, and while I understand there are still a few weeks of Github macos-13 brownout if we are desperate to get an App out, the writing is on the wall, so best to start on migrations now. I'll put reminder banners on the release posts for the next four weeks
* it is possible that another user will figure out their own an App solution in future, perhaps with PyInstaller instead of pyoxidizer, but it shalln't be me!

### B is not better

* a subtle bug caused auto-resolution rules with the action "B is better" to swap the AB to BA when pairs were in the 'pending a decision' queue in semi-automatic mode. I believe they were fine in automatic mode
* I have decided the maintenance debt for this command not justified, and it mostly just serves to confuse everyone, so it is removed from duplicates auto-resolution. I also removed it from the API docs (it'll still work there, and it seems to work well, but it isn't documented any more and I recommend anyone using it migrate carefully to use 'A is better' instead)
* in future I will add a 'swap A and B' button to the auto-resolution comparators tab so if you did set everything up wrong, it is still recoverable without frustrating the overall pipeline
* on update, all auto-resolution rules set to 'B is better' will pause and reset to 'A is better', and you'll get a popup about the situation
* thank you very much to the user who tested and reported this. it was unwise of me to throw this action in the mix, and another good example of KISS

### greyscale jpeg duplicate info

* in the duplicate filter, I now detect when jpegs are truly greyscale (i.e. actually 8 bits per pixel), and report that in the subsampling label. previously, greyscale were registering as 'unknown'. if either file is greyscale, the subsampling score is now 0
* the jpeg quality value is also adjusted for a greyscale image. they were reporting as slightly higher quality than they should have been when compared to an RGB equivalent. let me know how this works out IRL, though. I may need to tune it more
* the jpeg subsampling and quality comparison lines now have nicer tooltips explaining what they are

### epub covers

* thanks to a user who waded through some ugly xml, we can now produce thumbnails for EPUB files! should work for any EPUB 3 file that actually has a thumb
* I extended this to support EPUB 2 and some other broken files. I'll be interested in any examples that you think do have a cover but still don't have one in hydrus
* all existing EPUB files will be scheduled for a thumb regen on update

### client api

* fixed a 500-causing typo in `/add_files/generate_hashes/` for filetypes with a perceptual hash (issue #1783)
* added unit tests for both the path and bytes versions of this call so this won't happen again

### boring stuff

* the new retry svg icon has a brighter green arrow that stands out better in darkmode--thanks for letting me know
* after a user mentioned it, I optimised my new svg icons' filesize (with `scour`), and will continue to do so
* I rejigged the buttons in the duplicates page sidebar 'preparation' tab. my new rule is generally that cog buttons go on the right, as part of the thing they modify
* I may have fixed the alignment of the gallery downloader sidebar cog icon button in crazier stylesheets. if you still get the problem, let me know
* if a user runs into the 'It seems an entire batch of pairs were unable to be displayed.' duplicate filter error, all the pertinent rows are now printed to the log
* improved a little keyboard focus stuff on some small dialogs
* fixed an unstable list menu call that could cause trouble if the list was closed and deleted before the menu could show
* moved the 80KB-odd of URL Class UI code to a new `ClientGUIURLClass` file
* wrote some code to better handle and report critical hash definition errors during forced file maintenance
* network jobs that are expecting HTML/JSON no longer error out if they exceed 100MB. such jobs now spool to a temp file after 10MB. good luck to the guy with the larger-than 100MB JSON files
* when hydrus tries to import an expected HTML/JSON that doesn't seem to parse correct (just in case it is actually some raw file redirect), the copy from the network job to the import file temp location source is a smarter, low-memory stream. other work is still going to stay stuck in memory, however, so we'll see how it shakes out

## [Version 635](https://github.com/hydrusnetwork/hydrus/releases/tag/v635)

### misc

* with help from a user, the manual `file->import files` dialog has a new 'search subdirectories' checkbox, default on, that, if off, allows you to just search the files in the base dir
* import folders now also have a checkbox for 'search subdirectories', for the same thing
* the importer 'file log' menu now offers to remove everything except unknown (i.e. unstarted) items from the queue
* the `network->data->review current network jobs` window now has auto-refresh, with custom time delta
* if the client files manager runs into a critical drive error and subs, paged importers, and import folders are paused, the `file->import and export folders->pause` menu is now correctly updated immediately to reflect this

### cog icons

* after various discussions about 'advanced mode', I've decided to push more on cog icon buttons to tuck away advanced settings and commands. I hope to slowly slowly migrate most 'advanced mode' stuff to cog icons and similar
* I fired up Inkscape and made a new .svg cog icon. it will draw with nice antialiasing and scale up nicely as we move to UI-scale-scaling buttons in future. please bear with my artistic skill, but I think it is ok in both light and dark modes. the recent cool thing is, if it isn't to your taste, you can now replace/edit the file yourself and put a copy in `/db/static` and hydrus will use that instead
* the file sort widget, when set to namespaces mode, now tucks the tag service selector button and tag display type selector button (previously also only visible in advanced mode), into a cog icon button
* the file collect widget now always has a cog icon. it handles tag service and tag display type selection
* the file sort widget in 'num tags' sort now has a cog icon allowing tag service selection. the current tag service of the search page no longer controls the tag service in these sorts--you set what you want

### retry icon

* the 'retry failed' and 'retry ignored' buttons in gallery pages, watcher pages, edit subscriptions, and edit subscription panels are now collapsed into one new menu icon button. this liberates a row of space in the downloader pages
* lists across the program will update their button 'enabled' status instantly after various advanced commands now. if you see the list text change, the buttons should update

### boring stuff

* wrote a nicer menu templating system (old system was all horrible tuple hardcoding)
* the scrollable menu choice buttons now all use the new templating system
* the menu icon buttons now all use the new templating system
* the menu buttons now all use the new templating system
* wrote a 'cog icon' class just to keep track of it nicely across the program
* fixed up alignment and position (cog icons will now generally always go far right) of buttons in network job widget
* secondary file sort now applies within collections
* I did some prep work for allowing customisable secondary sort on any file page, but we aren't quite there yet
* replace my ancient 'buffered window icon' widget with a simple QLabel with a pixmap, affecting: the trash and inbox icons in the media viewer top-right hover, Mr Bones, Lain, and the 'open externally' thumb-and-button widget in the media viewer
* brushed up the grammar of the various 'text-and-gauge' stuff that I moved to always be zero-indexed the other week, particularly in the subscription popups

### boring url stuff

* updated `URLClass` to now hold a static one-domain `URLDomainMask` and use it for all internal `netloc` tests and subdomain clipping
* added raw domain rules to the new `URLDomainMask`
* added more `URLDomainMask` unit tests for this
* added a unit test to better check discarding subdomains at the url class level
* fixed 'www'-stripping alternate-url searching for urls with more components like `www.subdomain.something.something`
* the network engine is now more tolerant of non-urls, only checking strictly when you input into downloaders. previously, any normalise call on something that didn't parse would raise an error--now it is a no-op. the client api will respond to invalid `get_url_x` and `associate_url` URL params as best it can rather than responding with 400 (while still erroring out on `add_url`), and when you export urls with a sidecar, invalid urls should be outputted ok
