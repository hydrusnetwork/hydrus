---
title: Changelog
---

# changelog

!!! note
    This is the new changelog, only the most recent builds. For all versions, see the [old changelog](old_changelog.html).

## [Version 633](https://github.com/hydrusnetwork/hydrus/releases/tag/v633)

### duplicates group mode

* the duplicate filter now has a 'group mode', which will cause it to load one group of files that are all potentially related at a time. you'll process the entire group until there are no potential pairs left, and then a new group will be selected. if new potential pairs are added as a result of the first pass of dupe merges, you'll be given those to process, over and over, until there is nothing left, but for the most part, I think you will be able to process a whole group in one pass. it'll be interesting to see how it shakes out IRL
* if you manually skip all the pairs in a group, you will be asked if you want to change group
* if you know the duplicate filter, please give this a go. I think it might be annoyingly 'bitty' with groups of size 1, so I may bundle smaller groups together to make it all smoother, but if I do that I may want a slightly different x/y label presentation. I really like this when it works well, so once we are happy, I may make this the default behaviour for new dupe pages
* as a side thing, I believe I deserve an award for 'density of ugly UI' here for the checkbox, which has a right-border misaligned with the buttons above and below, the text, which isn't properly vertically centered on the checkbox, and the whole widget overall, which refused to center align how I wanted in the first place. this is another reminder to clean up some of my ancient layout tools, which often fail when I mix different widgets and layouts together. and maybe I should just make the thing a scrolling button like I do for file and tag sort stuff

### duplicates

* the duplicate filter comparison statements now include jpeg subsampling (444, 422, 420), with a little score weighting too. if you don't know, subsampling is a sort of 'data density' in how the image is drawn with light and colour. much like with jpeg quality, you can usually assume that bigger numbers are better, with 444 the gold standard
* the jpeg quality comparison line in the duplicate filter now considers subsampling. it is a little complicated since this is all hacky and there's a curve going on behind the scenes, but a `4:2:0` jpeg will get 0.85 the 'arithmetic power', and a `4:2:2` will get 0.92, of a `4:4:4`'s, which works out to dropping one or two 'high quality' to 'medium quality' qualitative bands, but I may have been too aggressive. thanks to a user who pointed out that quantization tables do not change with different subsampling levels
* several duplicate filter comparison statements are no longer hidden if there is no difference. for instance, if both files have the same jpeg quality, you now get a blue (0 score) line saying 'both are medium high quality'. having dynamic hiding here to maximise useful data was a decent idea, but, rather than streamlining the experience, it usually just increased cognitive load by bouncing the lines around and made successive similar pairs more difficult to track. similarly affected are: resolution, num_tags, and import timestamp; and has_audio, has_transparency, has_exif, and has icc profile (if either does)
* when two files are set duplicate and their metadata merged using the duplicate merge options, the url timestamps are now synced when both files have an url from the same domain, that being the destination gets the reasonable earlier timestamp of itself and the source. previously, the timestamp was only synced if the destination did not have an url in that domain already

### window positioning

* absent a saved record, media viewers now declare an ideal initial size of 1280x720. previously, this was alternately 240x180 or 0x0, and so when your media viewers were set not to remember their previous size, they were making some crazy small or completely hidden windows (issue #1768)
* media viewers are now correctly hooked up to the main gui when they do topleft/center parent initial positioning and gravity based parent sizing

### misc

* all subscription popups have an additional progress gauge for the queries. this should stabilise the width of sub popups, also
* all datetime widgets (e.g. under 'manage times') now have a 'now' button, beside the 'paste', to set the time to now
* the 'retry ignored' file log buttons now offer to retry 403s
* `help->about` now has boot time in relative and absolute terms
* added an ADVANCED checkbox to `options->media viewer` that lets you focus the main gui only when you exit a media viewer with a page/thumb 'focusing' action. useful if you use multiple viewers and are thinking about the focus stack
* fixed the default export path in `options->exporting` from saving incorrectly if the dialog was saved with it on a blank value. it was saving as the path of the db directory; now it should stay blank, and the export files dialog will default to `~/hydrus_export`
* wrote a section on loading your system Qt styles in the `running from source` help. a user seems to have figured out how to do it. if you have python experience and also have this problem, have a look and let me know how it goes. I'm going to _see_ if I can adapt my 'setup_venv' script to auto-detect the situation and optionally install the venv differently (issue #1767)

### boring stuff

* deleted a bunch of old and no-longer-hooked-up nitter url classes from the defaults
* reduced some unbalanced lag in the 'deny auto-resolution pairs' command in semi-automatic rules, with more than 4 pairs being denied at once
* refactored much of my old list chunking to a richer progress-tracking call
* refactored my hacky old inter-thread progress-gauge tracking to nicer calls on the shared status object
* fixed a GUG unit test that failed after the recent %20 thing. I think I last-minute changed the default value for that setting, after doing my main testing
* wrote a 'URLDomainMask' object to handle the future multi-domain URL Class update. lots to do up and down the pipeline to get this guy inserted, but the whole system will eventually support multiple regex domains per URL CLass. also wrote some unit tests for it

## [Version 632](https://github.com/hydrusnetwork/hydrus/releases/tag/v632)

### hotfix last week

* I did a v631a hotfix last week that fixed a looping network job(!!) under the particular conditions where a Post URL A1) used subsidiary parsers and failed to parse any URLs or, A2) did not parse anything generally, and B) had a certain environment, I think most probably ffmpeg version, that judged the respective html/json to _not_ be potentially importable. I am very sorry for this problem and I thank the users who reported it and helped me test
* I added additional safety checks to the file and gallery import objects to stop this type of error happening again. if an import job works and produces no status change, it will now auto-veto with an appropriate note

### misc

* the 'show the top-right hover window in the preview viewer' option has worked out well, and I like it a lot, so it is now default 'on' for all new users. also, all existing users will get it flipped to 'on' on update. if you tried it and decided you didn't like it already, sorry! hit up `options->media viewer hovers` to hide it again
* the 'page lock' system now correctly removes files when you remove them from _inside_ a collection (hitting 'remove' from a child media viewer looking inside the collection)
* the 'manage url classes' dialog's test text box is now much faster. it only needs to do CPU work on the first character you type, rather than being sluggish every time
* the 'manage url classes' dialog's test text box no longer steals focus from the text box on a match. you can now easily keep typing to discover a more specific url class
* added a DEBUG checkbox to `options->downloading` to turn off the legacy `%20` replacement in GUG generation (pasting `skirt%20blue_eyes` is interpreted as `skirt blue_eyes` when pasting query texts). all existing users will get this set on; all new users will get it set off. it isn't a huge deal, but if you need this off, try it out and let me know how it goes. like with the double-slash option beside it, I might quietly flip everyone to off in a year

### move-merge files

* the file 'locations' submenu now summarises which locations your files are currently in in the top row, in a flyout submenu
* the file 'locations' submenu now lists 'move (merge)' and 'move (strict)' actions separately. the 'strict' was the previous behaviour, and it only moves if the file is not already in the destination
* the shortcut command that handles local file domain add/move stuff allows this new move-merge action. existing shortcuts will have the 'if not already in destination', but perhaps you'll want the other, 'even if already in destination'
* this 'locations' menu stuff now shows the number of files to be added/move-merged/strict-moved
* this went through multiple reworks and namings. I'm still not totally happy with the verbiage and workflow, but it is powerful and clearly allows the various commands we want. I tried having a yes/no dialog that asked you whether you wanted a strict move or a move-merge, but it wasn't nice in its own way. I tried merging the two menus, but it make the eyes glaze over. I thought about removing the strict move entirely, but I'm not ready for that. in the end I went with a clear verb-first approach with separate submenus. let me know what you think with IRL situations and if you can think of something better than 'strict'/'merge' that isn't too long so it fits nicely in a menu

### duplicates

* you can now set the pair sort for the manual duplicate filter! I've got 'filesize of larger file', 'filesize of smaller file', 'similarity (distance/filesize ratio)', and 'random' to start. have a play with them, let me know what you think, and what others you'd like
* in the duplicate filter, if either file is an image project file (e.g. PSD), or somehow an application/archive, the 'psd vs jpg' line now has a score of -100, either way around. should pop out a bit more now
* the 'show some random potential duplicates' button now works on the fast fetch system. it builds its results far quicker than before in all typical situations, and in general worst-case performance is very much improved
* the 'show some random potential duplicates' button now delivers what I will be calling an entire 'group' of potential pairs. previously, it selected a master file and showed you every file potential to it; now we chase down everything that those potentials are potential to, and so on, until we have everything that is transitively potential in one blob. should let you see more fuzzy (alternate) groups in one go. there's a little voodoo going on here, so let me know if you get any interesting results
* the 'show some random potential duplicates' button now sorts the returned group according to a normal file sort widget, which is embedded just above the button. this guy works like a normal sort widget and will save and re-sort whatever is in the current page on changes; it is just in a different location. not sure I like it, but we'll see how it goes
* the 'x potential pairs searched' part of the new duplicate pair iterative fast-fetch system is now pre-filtered to the current file domain. pairs that are in deleted domains and stuff are no longer confusing things, and a search of 'system:everything' should now always come back with a 100% count. also, if you search in a small local file domain, let's say it only has 3,000 pairs of your total of 500,000, any duplicate search now only has to iterate over that 3,000 every time. a little extra CPU is required to figure this out in the pre-search phase, but I think it pays off. let me know how it is IRL
* the comparison statements and scores in the duplicate hover window on the right are now split into fast and slow loading and are loaded and displayed in two separate jobs, so a laggy visual dupes test won't hold the rest up. for now, slow means the jpeg quality comparison and visual dupes test
* 'they are visual duplicates' results now deliver -10 score if they are not duplicates on the simple scan and -5 if they are not duplicate on the detailed scan (and thus get red instead of blue text). I can't deliver a positive score here since this test does not reveal which of A or B is better, but on a negative we can bias the score to say they aren't dupes

### duplicates auto-resolution

* 'test A or B' comparators now support `system:tag (advanced)`, so you can test for the presence/absence of a tag on a specific domain. I hacked this in a little and 'current domain' will be 'all known tags' for now; It'd be nice to show that better in UI
* 'test A vs B' comparators now support `system:number of tags`. no namespace support yet, and it is locked to 'all known tags' and 'including parents and siblings', but you can do a basic 'A has more tags than B'

### duplicates boring/cleanup

* pair sorting now happens outside of the database and thus doesn't lag things in edge cases
* pair sorting now works wholly over the entire batch fetched in the duplicate filter (previously, each separate search block was sorted, so in sparse results you'd get a sawtooth sort)
* wrote a 'media result pairs and distances' object to hold the results of a rich potential duplicate pairs fetch. this complements the recent 'id pairs and distances' object from a couple weeks ago. this thing holds all the data needed to sort pairs and handles that all internally
* the 'show some random potential pairs' routine was completely rewritten to use the new tech. it is KISS now, and the old ad-hoc garbage with its multiple layers of king hash filtering and  'comparison_preferred_hash_ids' hackery dackery doo is deleted
* wrote some _fairly fast and good worst time performance_ file-domain pair-filtering code and expanded the pair-ids-and-distances cache to offer different answers for specific location contexts and rewangled the potential duplicate search context panel and the auto-resolution preview panel to re-initialise their base pair cache any time the location context changes
* added unit tests for the new tag-based auto-resolution comparators

### boring/cleanup

* thanks to a user, the way `system:limit` randomly samples with complicated sorts is made more clear in https://hydrusnetwork.github.io/hydrus/getting_started_searching.html
* brushed up the `server.html` help, clearing out some old things and adding a note about the update period from the FAQ
* `options->media viewer hovers` now has a label at the top saying what a hover is lol
* moved some list code from `HydrusData` to `HydrusLists`
* to reduce confusion, the 'verify https traffic' DEBUG checkbox in `options->connection` is inverted to be 'do not verify'

## [Version 631](https://github.com/hydrusnetwork/hydrus/releases/tag/v631)

### custom static assets

* you can now override any of the files in `install_dir/static` by creating a replacement in `db_dir/static`! it works like a lot of vidya modding folders do, where the program consults your user folder before falling back to the install's default whenever it loads an asset. If you want a custom splash image (`static/hydrus_splash.png`), go for it!
* routines like 'what QSS stylesheets are available?' and 'what rating SVGs are available?' and (less significant) the various 'what should our default downloaders be?' check both possible locations to create their lists, preferring (if there are filename conflicts) what it finds in your user dir
* I now explicitly recommend that custom QSS or SVGs go in this directory rather than editing the install dir. it lets you have a completely read-only install and means you don't have to worry about overwrites or clears if you update or git resync or whatever. this puts us one step closer to not having a crazy install environment, hooray
* a new `--no_user_static_dir` launch parameter disables this mode, if you need to do quick debug
* I wrote some simple help for this here: https://hydrusnetwork.github.io/hydrus/custom_assets.html

### misc

* I fixed some issues with the 'hover windows show/hide better' """improvements""" from last week. the child window testing logic was slightly dodgy and hover windows were not showing at all when there were two media viewers open. I simplified it and cleared out the unhelpful behaviour. the mouse hide/show should interact with dialogs a bit better now too
* search pages that start with 'include current/pending tags' turned off will now initialise correctly in this state. previously, the buttons were displaying 'off', as intended, but the internal search object was starting True/True always, so a bare F5 refresh was giving the wrong results and hitting the buttons the first time was not triggering a 'new search state, need to refresh' call since the button was just aligning on that first click with what the internal object already thought
* hydrus has _better_ duration/framerate parsing on videos that ffmpeg cannot report a good duration on. if, say, ffmpeg thinks the video is 40ms long but we just manually counted 400 frames, it now trusts its fps number more than the duration (previously it always trusted the duration)
* added a new shortcut command that does 'close media viewer and focus the tab the media came from, if possible, and focus the media'. same as the related command, but it forces the media focus if you have that not set under `options->media viewer`
* the 'review session cookies' and sub-panel now have 'export to clipboard' and 'import from clipboard' buttons. there's some domain filtering here that ensures cookies only go in the slot they are supposed to
* the 'expires' section in the edit cookie dialog works better--it now boots with the existing value, and the max settable time is 200 years

### duplicates

* the duplicates filter page sidebar now only disables 'launch the filter' and 'show some random potential pairs' if the search is A) complete and B) found nothing. previously, it was disabling until it found at least one pair, which is technically great but annoying in practice
* if you have 'After duplicate filter, ensure deletees are inboxed before delete' on, this now also applies to manual file deletes within the filter

### complicated url-spawning metadata propagation issue

* there are two ways an url file import job can create child jobs--one, by parsing multiple 'posts' with separate metadata using a subsidiary page parser, as in a watcher; the other, by parsing multiple urls within one post with a normal page parser. until now, these routines created their child objects with different, ad-hoc code. most of the 'my downloader that works like this doesn't get the tags/parent url/whatever assocated to this child down the chain' bugs were due to this
* this situation is now remedied. both routines now use the same shared call to create children. referral urls are set up correct; the parent url is added as an associable url; parsed http headers are passed along correctly; source time is passed down; and tags, notes and parsed primary/source urls, which were all working correct before, are still passed down (issue #1763)
* I've done the same for gallery objects creating child gallery or file imports. they had similar but lesser issues
* there are still a couple of issues in the pipeline regarding gallery urls that use multiple tiers of subsidiary page parsers. I am thinking about how to sort it out

### boring stuff

* renamed the 'confirm when closing a non-empty downloader page' in the options to _importer_ page. this applies to all importers, including hard drive import pages (issue #1764)
* the 'regen total pending count' database maintenance job now asks you to choose a repo or ipfs service. previously it was asking you to choose from every service
* if a database is missing critical tables and thus non-functional, it now reports the specific table names
* rejiggered my 'eliding label' sizeHint code to talk to Qt layouts better
* the top hover window now has fixed width and will no longer overflow. at very small sizes, the buttons will shrink and overflowing text will behave better
* the 'delay reason' label on the edit subscription panel now has proper wrap and eliding, so if that guy gets a gigantic error text, it'll now fit better
* forced subscription popups a little wider by default
* added another note from a user about mpv in the Linux install help, this time about MangoHUD. I think we might want a separate page regarding Linux environment tweaks and fixes

## [Version 630](https://github.com/hydrusnetwork/hydrus/releases/tag/v630)

### Linux laggy mpv issue

* I've been chasing down a Linux specific problem recently where mpv would lag out for a second when trying to transition media when it was near to the end of the media. it seemed to be some re-loop buffering issue but I couldn't figure it out. the recent failed 'TEST: stop mpv before transition' was a shot at this
* I figured out that it was caused by the audio normalisation pass triggered by the `af=lavfi=[loudnorm=I=-16:TP=-3:LRA=4]` line in the default mpv.conf. audio stuff like this has caused Linux other problems before. it is now commented out for all new users
* If you are a Linux user, please go to your db dir and check your mpv.conf. edit that line out if it exists.
* I am going to play with `af=dynaudnorm`, which is supposedly far less CPU intensive. feel free to try your own things too and let me know what works, and we'll figure out better defaults!

### misc

* if you have wanted to map shift+tab to a shortcut and it hasn't worked, please try it again! hydrus now recognises 'backtab', which it seems some/many situations produce on a shift+tab input. it'll likely say 'shift+backtab', but whatever--it'll catch _something_ stable now
* fixed some weird logic with the 're-focus original search page' and 'tell original search page to select exit media' options that trigger on media viewer close under `options->media viewer->window`. they now work independently
* when you upload tag data to a tag repository, the prepare routine now checks that the tags are valid (no crazy/broken characters, etc..). if not, it abandons the job and tells you how to fix invalid tags
* fixed some mouse autohide behaviour in the media viewer when various dialogs are open. child windows are detected more reliably and various 'I should unhide now' events fire properly
* added a note to `options->media playback` about the mpv.conf in the db dir--this basically wasn't documented anywhere, previously--adding that this file is reloaded on every options dialog ok
* I confidently attempted to rework the 'add folder' button in the 'import files' window to be an 'add folders' button, allowing directory multi-select, and I was stunned to discover this is simply not doable in a multiplat way using stock path-picker dialogs. I feel like I am going crazy and will revisit this
* wrote a guide and to-do list for migrating from one OS to another under https://hydrusnetwork.github.io/hydrus/database_migration.html#to_new_OS

### default downloaders

* thanks to a user, the pixiv downloader now fetches a 'series' and 'chapter' tag for those paged manga works that have that data set. I wonder if the 'series' here is more akin to what we'd call 'title', but I'm not familiar enough with pixiv to know what is more common, so let me know how it shakes out IRL

### more export filename rules

* if you are on non-Windows but an export directory filesystem is "ntfs", "exfat", "vfat", "msdos", "fat", "fat32", "cifs" (almost always ntfs underlying), "smbfs", "fuseblk" or any of those but prepended with "fuse.", ntfs naming rules (no colons, shorter filename limits etc...) are now applied (was formerly just "ntfs" or "exfat")
* a checkbox under `options->exporting` now allows you to always apply ntfs naming rules. use if you have an NFS share that is NTFS underlying, or you are subdir-translating from an export dir that is non-ntfs to a mountpoint that is
* when an export filename pattern includes subdirectory generation, the subdirs' max length is now determined by the max path characters allowed for this system and the pre-existing prefix directory length, while leaving a reasonable numbers of characters for the actual filename. they'll squeeze down to fit all normal situations (previously windows subdirs were hacked to a 64 char limit)
* filenames and dirnames are now sanitised as they are elided. everything is done through one clean combined call, so there are fewer chances for surprises here
* some eliding and sanitising rules are more failsafe in edge cases. instead of raising an exception, you'll get 'empty' or 'truncated'
* two new optional integer values are added to `options->exporting`, for overriding max path length and clipping max dirname length. check the tooltips for more info, but this is basically to test ntfs-extended modes that have their own limits. _caveat emptor_
* I updated the unit tests here to cover the changes

### duplicates

* the manual duplicate filter's pair fetch routine has been rewritten using the new low-latency fast-cancel tech I developed for auto-resolution. it should be able to fetch pairs to work on a good bit faster in all cases, and the worst case for difficult searches is much better. when it is loading new pairs, you get a running status update on the background of the filter media viewer
* the pairs it loads follow a smarter decision logic, showing you more from the same group while saving you more time
* the pairs are now sorted, hopefully with bigger files first, and the same file over and over. let me know what you think of it! I'll be adding options here, but it is tricky!
* when the duplicate filter commits work, it now does so more asynchronously. if working a mid-filter commit, the UI no longer locks and the background now updates with status text showing progress of the commit; if happening when you close out the filter, it now happens in the background but will make a popup with status if it takes longer than a second to complete. the timing of the 'refresh dupe numbers' call that hits the sidebar is better aligned to refresh once all this work is flushed
* the default duplicate filter batch size is reduced from 250 to 100
* auto-resolution rules that have pending approve/deny items now say their status is 'queued' (previously 'done'). maybe 'ready' or another word is better--let me know if you can think of one. 'awaiting approval' feels too long

### duplicate filter boring/advanced stuff

* the manual duplicate filter's pair fetch database routine no longer does any shaping of the pair queue. it previously tried to auto-filter certain pairs that would be implicated by previous decisions and tried to first give you pairs with certain properties, but the implementation was never too clean and it was often simply confusing on the front end. the UI level now takes full responsibility for this
* the manual duplicate filter is more careful about which pairs it will auto-skip, and in many cases this will let you process an entire group--alternates and all--in one run, rather than that situation where you get lots of bitty '1/2', '1/1' micro-batches at the end of a particular search. now, rather than insisting that every batch commit only include pairs of unique files, it now tracks which files are mergees by the current batch decisions and auto-skips those. so, it might present to you (A, B), and if you say A is a better duplicate than B (causing B to be merged into A), it can still present you with (A, C), but if (B, D) or (E, B) is pending, you still won't see them (since B is no longer a king, and the proper pair, which will be recalculated after the commit, is (A, D) or (A, E). in reality though, (A, D) and (A, E) are probably already in the queue due to transitive similarity, so if we can sort them together, we'll probably clear everything in one batch)
* I played around with different types of pair sort for the manual filter. this gets complicated in a couple of ways and what I thought would be useful often had a clear downside in my test data. for now, duplicate filter pairs will explicitly come by largest max filesize first, with largest min filesize as secondary sort. you'll see a lot more of the same big file matched up against other files, in descending order, and fewer low quality files matched against other low quality. let me know how it goes with IRL data, and I will add explicit options here so we can test more stuff. I tried a 'show me the most/least similar first' approach, but what that actually means beyond sorting by the discovered search distance is unclear--I can try for ~1.0 pair filesize ratio, but this seems to flood me with alternates first, which is not ideal for decision logic. if we want clear duplicates first, maybe we want to have the highest file ratio first? this max filesize first seems like a 'least worst' for now at least
* I am planning a checkbox that will let you focus on entire potential groups one at a time (seeing the same basic files over and over until there are no potentials that 'look like that' any more), which may itself benefit from an exact sort
* there's a third sort question about whether you want the same reliable order of pairs on every launch, continuing where you left off, or if you want to jump about a bit. today's low-latency fetch tech will fetch the same stuff over and over unless the numbers get big and/or refreshed. this question will be more important when I do the grouping, so I think this'll be another checkbox
* I updated the Client API help to talk about kings and `/manage_file_relationships/get_potential_pairs` given the modern tech that has been rolling out this year and this week. all my duplicates stuff now always returns kings, so you don't have to bother about that so much any more, and the filter now presents you with a raw batch that is simpler and cleaner but you may want to institute your own auto-skip tests as I have. it isn't a big deal, and you may already have something similar, but I've figured out, I think, simple and optimal rules, so please check it out yourself
* I wrote a class to handle the 'potential duplicate pairs and their distances' list that is thrown around in all the new dupe fetch code, both up and down the pipeline and in the fragmentary fetch slices. this class now handles the iterating, randomising, block popping, distance sorting, and now potential-group-mapping-and-filtering jobs internally and in one location

### other boring stuff

* now we know the new `11.3.0` version of Pillow adds native AVIF support in all the builds and source situations we work on, `pillow-avif-plugin` is removed from all requirements.txts and the pyproject.toml
* if the network request for an expected html/json file is over 100MB, the error message now says more about what went wrong (probably URL Class crossed-wires)
* fixed a client api test that could sometimes fail due to a thread taking too long to work
* `help->about` now says the system architecture (e.g. x86_64, arm64, aarch64)
* `help->about` has better wordwrap (we noticed it gets super wide if your install dir is long etc..)

## [Version 629](https://github.com/hydrusnetwork/hydrus/releases/tag/v629)

### misc

* fixed the regression where the top-right hover window was not showing in the archive/delete or duplicate filters (issue #1755)
* fixed some volume/rating rendering stuff in the filters, too
* the new '3/5' numerical ratings texts are now drawn in the normal text colour for your stylesheet, not from the rating colours
* you can now select the 'aggregate modified time' as the source timestamp when setting up a sidecar export. this is the reasonable minimum of all known modified times and what you generally see in the UI when it only shows one modified time
* if you try to import a Canon RAW CR3, it is no longer recognised in the initial path scanning routine as an mp4. many still images that ffmpeg can somewhat parse but isn't sure on should be fixed here--I was reading back the ffmpeg output badly and falling to a 'generic mp4?' assumption (issue #1756)
* the optional library lines in `help->about` now say a little more than just True/False, and the process by which this dialog says 'hey, mpv failed to import for this reason' on window launch is now generalised, recognises the difference between a module not being available and an actual error during import, and covers mpv, QtCharts, QtPDF, dateparser, dateutil, and psutil
* fixed 'collapse pages to the right' page tab actions, which were typo-broken in recent refactoring

### duplicates

* fixed an issue where the duplicates auto-resolution system would work way too hard and not take long enough breaks in many cases. it was notifying itself there was new work due _while_ doing work, leading it to keep waking itself up as soon as it went to sleep. it now ignores these signals while it is doing work. you will generally see the system working much slower from now on. let me know how this goes--now the clock behind all this isn't busted, it needs a re-tuning and/or options regarding how hard it wants to work, and we may want to bring back 'work hard' mode
* the 'A and B are visual duplicates' test has a more sophisticated edge-detection routine. it can now detect paler watermarks or other artist edits by tiling the images' average edge differences and calculating a skew metric to notice unusual regional shifts
* the duplicates auto-resolution system (and the database maintenance manager) now force breaks of at least 250ms between each job when things are busy
* the duplicates auto-resolution system now runs with significantly less overhead any time it needs to consult rules
* the list on the main duplicates filter 'auto-resolution' tab updates itself significantly faster now, only needing to hit the database on rule edits or the refresh button
* rules are now better at reporting if they are doing work in this list. they'll say 'waiting' (want to work but settings say no working right now) and 'working' (taking available work slots right now) a lot more now. also instead of 'idle', they now say 'done'
* the 'test' phase of a duplicates auto-resolution rule, which is CPU expensive for 'A and B are visual duplicates', now occurs outside the database transaction
* fixed the 'work on these rules during idle time' cog menu, which was wired up to the 'do search for potential duplicates in idle time' options boolean due to a typo
* the 'edit rules' dialog is now much more aggressive at interrupting and pausing ongoing work so it can launch

### more invalid export path fixes

* the new routine that elides subdirectory names generated by a export filename pattern is now careful to trim the directory name of leading/trailing whitespace. previously, when you were unlucky enough to get elided to `tag, tag, tag, `, the export operation would fail in Windows and simply be ugly everywhere else. the base filename is stripped of whitespace too, so you won't get `tag, tag, tag .jpeg` any more (issue #1751 again)
* it now also removes periods from the end of windows file/dirnames, which it turns out are also not allowed
* it now also excludes some windows reserved names like 'AUX' and 'COM1'

### AVIF

* the Pillow guys released the 11.3 that adds nice native AVIF support. all builds will fold this in and it should all just work. users who run from source might like to rebuild their venvs this week. this fixes some bugs we had with the interim plugin library, including one with unusual rotation (issue #1728)
* in the v629 update, all AVIFs are scheduled for: a metadata rescan, the 'has exif/icc profile/other human-readable embedded metadata?' checks, and forced thumb, pixel hash, and phash regen (there are several legacy issues from this saga to catch up on)
* the code that imports the heif, avif, and jpegxl plugin libraries now asks Pillow if it can do the respective thing (turns out it has a nice call for this) before importing the plugin, making for a much more natural and foolproof update process as we go forward here
* the `help->about` window now shows if you have heif, avif, or jpegxl support natively in Pillow or via a plugin

### dateparser fixes

* dateparser, which we use to do the 'easy date parse' solution, updated to `1.2.2` and suddenly wouldn't import correct in the Linux and Windows builds (maybe macOS too, not sure, but it seems to have been a PyInstaller issue), breaking a bunch of cool date parsing
* I have rolled back dateparser to `1.2.1` in all requirements files and it should import again ok in v629 builds. to check, you can see it under `help->about`
* it looks like the new version had additional locale issues, too, or it aggravated an older known one. computers that are in locales where the local time is strictly 24-hour, such as Polish or Russian, were having trouble parsing any date with AM/PM info, even when I told dateparser 'hey, if that failed, just do it in EN mate'. the program now initialises dateparser right at the very start of the program, before other imports sink their teeth into app locale, and this appears to fix dateparser's timezone cache initialisation. thanks to the user who figured this out!
* the 'easy date parse' system now has a fallback to dateutil's very good parser if dateparser fails
* all the above addresses issue #1754

### cleanup/boring stuff

* fixed a deprecated Pillow fromarray mode param
* think I fixed an issue with Arch running the Ubuntu-built release relating to a bad 'wakeUp' call in some event dispatching code
* added some painter save/restore stuff to ensure 'draw rating here' calls are non-destructive to painter state
* auto-resolution rules' counts are now updated at the object on any change and do not have to be reloaded when a daemon wants to consult them. also made it more thread-safe
* added some sidecar modified timestamp unit tests
* added unit tests for the new export path stuff, and improved my path unit tests to better work on any OS
* deleted the old integrated 'do duplicates auto-resolution work' db code
* removed the 'TEST: stop mpv on media transitions' option. this test failed and caused other bugs, but I have some other ideas I'm going to play with

## [Version 628](https://github.com/hydrusnetwork/hydrus/releases/tag/v628)

### ratings

* thanks to a user, we have another round of new ratings UI features--
* under `options->media viewer` you can now have the ratings hover window and background appear, just like in the normal media viewer! quick ratings setting from the preview!
* under the new `options->ratings`, you can now customise the size of ratings in the manage ratings dialog and the preview viewer. you can also set a different width for inc/dec ratings
* also under `options->ratings`, you can now set numerical ratings to only show the `3/5` fraction and a single star on the thumbnail view
* under the `services->manage services` panel of a 'numerical' rating service, you can now set to have the `3/5` fraction written to the left/right of the stars display
* a bunch of misc code cleanup. we are slowly tearing out some of my bad old code to make a more decoupled renderer here, and ideally to eventually figure out a proper 'what this rating will look like' preview widget alongside these options
* thanks to another user, we have a bunch of new rating svgs available by default: `architecture`, `art-palette`, `cinema-reel`, `eye`, `heart-cute`, `inspiration`, `scenery`, `smile`, and `wallpaper`. I think they look great!

### misc

* the new 'export filename' generation routine now parses any subdirs your pattern makes and forces a 64 character limit on Windows and a ~250 byte limit otherwise. you can now put `{character}\{hash}` as the pattern and it will create stable and reliable folder names. this is a hardcoded hack waiting for a richer path generation system (issue #1751)
* fixed a bug when loading an OR predicate that held a rating predicate during database initialisation (which could happen during a db update or, it seems, when loading the core options structure after the user had done some OR/ratings work that populated the 'recently used predicates' structure)
* fixed a bug when rendering any rating predicate to text during database initialisation
* since it is a clever routine and it has caused us trouble before, predicates now never fail to render themselves. if there's an error, they print it to log and return `error:cannot render this predicate`
* fixed a bug in the 'present this list of texts to the user' renderer that was causing the last line not to render when there were more than 4 items to show. this made for a completely empty output if you pasted five really short texts into 'paste queries'. it was also undercounting the 'and x others' line by one, when there were more than 24 lines of content
* the 'stop removing double slashes at the start of an URL' test went well, so all users are now flipped to working this way by default. the 'TEST' checkbox under `options->downloading` is now a 'DEBUG' one, if you need to go back to the old way
* the program no longer logs the full error when FFMPEG cannot render a PSD
* the program no longer logs the full error when Qt cannot render a PDF for a thumbnail

### potential duplicate pairs count is smoother

* the widget that edits a potential duplicate pairs search context (which you see in the duplicate filter page sidebar and the duplicates auto-resolution search panel) now has an integrated duplicate pairs count. this count calculates in an iterative/incremental way, doing a bit of counting over and over rather than one big job, just like the duplicates auto-resolution preview page, and thus opening a duplicates filter page is no longer an instant db lag. updating the search context or getting a signal of new potential pairs will quickly cancel any ongoing search and restart the count. it also pauses an ongoing count while you are not looking at it. the count also only disables the 'launch the filter' and 'show some random potential pairs' buttons until it finds at least one pair. this should all just work better!
* note that I did a bit more assumptive 'things haven't changed in the past five minutes' logic with this work, so while it should still update itself on big changes, I made it lazier on the small stuff. let me know if and when it undercounts. I also stopped it refreshing after every 'random potential pairs' action, too. the refresh button should fix any undercounting or other desync, so let's see how it does IRL

### duplicates auto-resolution

* the approve/deny actions in the review rule panel now work in chunks, which gives other jobs time to get at the database (no more freezing up), and they report '16/55' status on the button you clicked, so you can see how it is doing
* this panel also gets a 'select all' button
* I tweaked the suggested 'A and B are visual dupes' rule to queue up 128 files and broke it into two rules--one that requires `A has filesize > 1.1x B` and the other doing `A has width/height > 1.1x B`, mostly to increase confidence on the 'better' action. I didn't have time to add times to the comparator system, but that's next. I want 'A modified date earlier than B' on both rules as an extra safety guard rail for what I suggest as a default
* added a new 'archived file delete lock' exception under `options->files and trash`, for any auto-resolution action
* I've hidden the 'work hard' button. I don't really like it and it wasn't working pleasantly. maybe I'll bring it back, but if I do it'll be with some nicer UI

### boring duplicate cleanup

* the initial work that goes into setting up the new iterative potential duplicate pair fetch is now cached and shared amongst all callers, so a variety of refresh calls and duplicate filter or rule edit panel loads will now be that bit faster off the mark. this is important if you have like 700k potential pairs
* the new iterative potential duplicate pair fetch now pre-filters to any simple local file domain, so when it runs on a single local file domain with a small relative file count, it is now much much faster
* the new iterative potential duplicate pair fetch is now faster with `system:everything` searches
* the new iterative potential duplicate pair fetch tech now grabs in blocks of 4096 pairs, up from 1024. the core auto-resolution rule searcher is now 4096, too, down from 8192
* the old monolithic potential duplicate pairs counter, which now only occurs in unit tests and an API call, uses the new tech (just by iterating over the whole search space in one transaction), and is thus a good bit faster and cleaner etc.. in various situations. I was able to delete a bunch of semi-duplicated code after this!
* all duplicate pair searches that are both `system:everything` and a union of multiple local file domains now run at good speed (they were previously extremely unoptimised in many situations)

### boring cleanup

* when editing favourite regexes, the 'add' call now shows a rich regex edit box, and both add and edit calls' regex boxes are a little wider and no longer offer a recursive 'manage favourites' command from their menu lol
* moved the edit regex favourites panel to its own class
* moved the autocomplete dropdown resize code from old wx hacks to Qt Events
* moved the frame size and position saving code from old wx hacks to Qt Events and Timers and a nicer eventFilter, and reduced some save spam
* since they are no longer used anywhere, cleared out these old wx move and maximise event catching hacks
* when you enter a password through the database menu, it now asks for it a second time to confirm you typed it all ok, and if you clear it, it gives a yes/no to confirm that
* the slideshow custom period input now defaults to `15.0` so the user knows they can do sub-second input, and it now presents a graphical message if the time was unparseable
* the various 'separate' subscription choices should be better about sorting the to-be-split queries with human sort rather than just ascii
* my 'select from a list' and 'select from a checkbox list' mini-dialogs now sort their contents with richer human sort
* in the edit duplicates auto-resolution rule panel, the 'max pairs in pending queue' widget now disables more carefully based on the starting operation mode. btw I think I was crazy defining the pause state via a third operation mode choice and will most likely rework this to a separate checkbox
* updated the example response in the Client API `/manage_pages/get_page_info` documentation to include `hash_ids`
* cleaned some misc client db job-to-command mapping stuff
* bunch of little logical improvements for various text entry dialog feel, mostly making some 'edit this if you want' cancel outcomes in sub merge/separate no longer mean a cancel of the larger multi-step workflow
* `help->about` now says your numpy version
* broke `ClientGUITags`, which was ~230KB, into smaller files for Manage Tags, Manage Tag Siblings, Manage Tag Parents, Incremental Tagging, Tag Filters, Sync Maintenance EditReview, Tag Display Options, Edit Namespace Sort, and Tag Summary Generators in `hydrus.client.gui.metadata`

### text entry dialog overhaul

* migrated the ancient 'enter single line of text' dialog to my newer edit panel system. migrated all the old dialog calls over to the new class, being: sort-by namespace custom entry; password setup entry; password boot entry; debug fetch an url entry; janitor file repo file info lookup hash entry; janitor account lookup account key entry; file lookup script custom input; gui session name input; string-to-string widget add and edit key/value inputs; string-to-string-match widget add and edit key inputs; sub merge name input; select subs by name input; non-half subscription separate name input; tag filter favourite import name input and save name input; manage tags reason input; tag summary generator namespace/prefix/separator edit inputs; slideshow custom period input; some tag petition reason input; note import options whitelist add/edit name input; add domain modified timestamp domain entry; json object exporter name input; tag sibling/parent pend and petition reason entry; export downloader domain input; parser example url input; login management domain and access description entry; login script example domain and access description entry; parsing test panel url fetch input; petition files reason input; ipfs directory naming input; new page of pages naming-on-creation and naming-on-send-down option input; page renaming; registration token entry; ipfs share note input; simple downloader formulae naming input; external program launch path input; advanced file deletion reasons edit; namespace colour namespace input; namespace sort options panel editing input; tag suggestion slice weight; edit notes name input; regex favourites regex and description input
* aaaiiiieeeeeeeee

### library updates

* the 'future build' last week went without any problems, so I am folding its updates in to this build. we have--
* On All--
    - `requests` moved from `2.32.3` to `2.32.4` (security fix)
* On Linux and Windows--
    - `PyInstaller` moved from `6.7` to `6.14.1` (handles new numpy)
    - `setuptools` moved from `70.3.0` to `78.1.1` (security fix)
    - `numpy` moved from `2.2.6` to `2.3.1` (lots of improvements, py 3.11+)
* On Windows--
    - `sqlite` dll moved from `3.45.3` to `3.50.1`
* Source venvs--
    - `numpy` moved from `>=2.0.0` to `<=2.3.1`
* the pyinstaller bump is the most important, I think, and it should fix a bunch of dll load and OS API issues. there are no special install instructions, but let me know if you run into any trouble

## [Version 627](https://github.com/hydrusnetwork/hydrus/releases/tag/v627)

### misc

* windows that remember position are better about saving that position on a window move. some window managers (particularly on Linux) were not recognising the previous 'window move has ended' tech, nor non-mouse moves, so I wrote something that will work more generally. let me know if any windows start positioning crazy this week during drags!
* fixed variable framerate render timing in the native viewer for animated webp files. I messed up some logic when I first rolled this out in v620; should be working correct now (issue #1749)
* fixed an issue where import sidecars were losing their texts' order (they were being pseudorandomly re-sorted) in the outer layer of string processing where multiple sidecar texts are combined. the sidecar pipeline now preserves original sort throughout the pipeline (issue #1746)
* added a `TEST: Stop mpv before media transition` in an attempt to early-cancel laggy mpv when transitioning media when the current (looping and pre-buffering) media is near the end. may also help some situations with laggy storage, but we'll see. I think this mode might have some load bugs

### visual duplicate detection is ready

* the 'A and B are visual duplicates' system now compares spatial edge data and is better able to recognise mosaic/blur patches, minor alterations or repositions, and subtle alternates in busy areas like eye pupils. all the remaining difficult false positives I have are fixed, and the test easily catches several pairs that were previously tricky, allowing me to remove a hacky test on the colour testing side of things that was producing some false negatives
* this test is now available as a comparator in duplicates auto-resolution rules! you can choose it to be at least 'very probably', 'almost certainly', or 'near-perfect'. I default to and recommend 'almost certainly' for now. I am still interested in seeing any new false positives you encounter
* note that this tool is CPU heavy--expect about a second per pair tested! the UI seems to be holding up well with the delay, but I've added a new label to the preview panel to show when it is running slow and there are pairs still to be tested
* added a new and generally cautious 'visually similar pairs - eliminate smaller' suggested rule. it does an 'A and B are almost certainly visual duplicates' test on similar filetypes, preferring an A that is larger in size and larger or equal in resolution, and is semi-automatic. if you have been following all this, please give it a go and let me know what you think
* assuming this tech holds up, this was the last big difficult thing in my auto-resolution superjob. there is still a lot I want to do, but it'll mostly be cleaner UI, some more comparator types, a way to interact with the denied pairs log, smoother counting and pair load in more places, a way to load up a duplicate rule's pending decisions in the normal filter, richer duplicate-aware pair preview/review, that sort of thing

### cleanup/docs/boring

* added some notes to the 'migrate' and 'source' help regarding needing to rebuild your venv every time you move the install folder
* added some 'better software for x' links to 'getting started with files' to ComicRackCE, Lanaragi, and Calibre
* added a little about 'A and B are visual duplicates' to the duplicates auto-resolution help
* the 'LabHistogram' stuff that does the new 'A and B are visual duplicates' is now renamed generally to 'VisualData', and the LabHistogram stuff is rejiggered into a subclass
* fixed a small warning bug when the thumbnail pair list in the auto-resolution preview panel is updated to have a new rule while it is empty
* fixed a duplicate file system bug where it wasn't able to negotiate the correct `media id` for a file when the duplicate group had an identity definition but somehow was desynced and did not list the king as a member
* added a new 'pixel-perlfect jpegs vs pngs - except when png is smaller' alternate suggested rule that does pixel perfect jpegs and pngs but only actions when the jpeg is smaller than the png
* wrote some unit tests for 'A and B are visual duplicates'
* I think I silenced OpenCV's warning logspam. if you ever saw `[ WARN:44@43420.823] global grfmt_png.cpp:695 read_chunk chunk data is too large` kind of thing in your log, you shouldn't any more

### future build

* I am making another future build this week. This is a special build with new libraries that I would like advanced users to test out so I know they are safe to fold into the normal release.
* in the release post, I will link to this alternate build. if you are experienced and would like to help me, please check it out
* the new numpy version that caused trouble for Arch users also broke our build right afterwards, so this is an attempt to fix that while rolling in some security updates. updating PyInstaller more than a year to the same numpy fix they rolled out two weeks ago did not, I was surprised to discover, appear to break anything, so the builds may be significantly more stable and OS-compatible. as usual, I will be interested to know if anyone on Win 10 or any other older OS has trouble running this. as far as I can tell, a clean install is _not_ required
* the specific changes this week are--
* On All--
    - `requests` moved from `2.32.3` to `2.32.4` (security fix)
* On Linux and Windows--
    - `PyInstaller` moved from `6.7` to `6.14.1` (handles new numpy)
    - `setuptools` moved from `70.3.0` to `78.1.1` (security fix)
    - `numpy` moved from `2.2.6` to `2.3.1` (lots of improvements, py 3.11+)
* On Windows--
    - `sqlite` dll moved from `3.45.3` to `3.50.1`
* Source venvs--
    - `numpy` moved from `>=2.0.0` to `<=2.3.1`

## [Version 626](https://github.com/hydrusnetwork/hydrus/releases/tag/v626)

### AUR numpy problem

* there was a problem with the AUR (Arch Linux) hydrus package while I was on vacation. the python package `numpy` updated and a couple deprecated lines I had missed now threw errors. for those who auto-update to the newest of things (eg. as on AUR), this broke video view and file import. sorry for the trouble! by luck I had fixed half of this by accident a few weeks ago, but I also missed a few more lines. a user kindly figured out the fix and I was able to merge it into master early for those who could pull. rolling back numpy to `<2.3.0` was another temporary solution. the fix is now properly in this v626, so when AUR v626 rolls out, everyone should be good again. if you are an AUR guy and really want to avoid this in future, I recommend moving to your own source install, as here: https://hydrusnetwork.github.io/hydrus/running_from_source.html it takes a couple minutes to set up, but with our own venv that we control, we can fix the library versions to stuff that we know will work in perpetuity.(issue #1744)

### Paint.NET

* Paint.NET files are now importable (or at least anything since ~2006). the client pulls resolution and should be able to do thumbnail, but cannot render them fully. they count as an 'image project file'. let me know if you have any v3 .pdn files that don't work!

### default downloaders

* the derpibooru file page parser is updated to get tags again. I think I updated everything correct, but let me know if anything is parsing different to how it was before

### duplicates auto-resolution

* improved my 'A and B are visual duplicates' algorithm with a new pre-histogram gaussian filter to better tune out jpeg artifacts and a more careful later 'absolute skew pull' inspection
* many previously 'definitely visual duplicates' false positives are now detected as various states of 'not visual duplicates' or 'very probably visual duplicates'
* many previously false negatives are now correctly detected as 'definitely' or 'near-perfect' visual duplicates
* many previously true positive duplicates are now detected as higher levels of confidence of duplicate
* thank you all for submitting your false positives and false negatives. I now have one pair that still false positives as 'definitely visual duplicates', and a couple that still go 'very problably', which I would like to fix. the remaining problem to solve is file-to-file edge difference comparison, which I feel pretty good about attempting at this stage. I also feel better about finally turning this system on for the duplicates auto-resolution rules soon, with the caveat that I'll probably recommend users only go 'near-perfect' to start
* after thinking about it, I renamed the 'definitely' to 'almost certainly'. with an even more confident tier in 'near-perfect', 'definite' is the wrong word
* I am still interested in any false positives or false negatives you encounter hereon. the main problem I now have to beat in image terms is where the alternate is an artist correction that moves a small object of interest a few pixels amidst a sea of similarly coloured pixels, for instance moving an anime nose a few pixels right. eyes that have slight differences (tear-drops, heart-shapes) are also proving a problem, but the main one is a small thing moving without changing average colours anywhere. also, obviously, if today's algorithm is actually worse anywhere, let me know!

### better export filenames

* the call that generates export filenames for manual exports, export folders, and drag and drops with export filenames is improved in several ways--
* - you can now set your own 'max filename length' under `options->exporting`. defaults to 220 (most OSes are 256, although Linux eCryptFS is ~140)
* - on Windows it now tests filename and total path length against characters rather than encoded bytes
* - the test against max total path length (260 characters on Windows, which we shave to 250 for extra safety) is more reliable
* - on Linux it now tests against a max total path length of 4096 bytes, and on macOS 1024 bytes. we shave by another 20 bytes for safety
* - the test against total filename length now recognises when a filename pattern produces subdirectories and will not include them for the filename length test
* - there is less padding fudge in the system, around 54 characters! if you were clipped before, you will likely see longer filenames immediately
* if you have an export folder that uses frequently elided filenames, it is going to be busy as it generates new filenames on next run. let me know how you get on!
* added a bunch of unit tests to test filename eliding, for: null, filename, path, filename and long path cases, for ascii and unicode, for character limits (windows) and byte limits (linux)

### url slash test

* when I first made the network engine, I had the URL normalisation routine collapse multiple leading slashes on a URL path down to one. for instance, `https://site.com//images/123456.jpg` becomes `https://site.com/images/123456.jpg`. this is actually incorrect handling on my part, and there's a site or two where it matters. unfortunately, I cannot make the switch without breaking URL Classes that already relied on the collapse, and I do not know how many of these there are out there
* so, I have added a checkbox to `options->downloading` where you can participate in a TEST to change the normalisation behaviour. I would like advanced users who use unusual downloaders to turn on the test and run their subs and stuff as normal. let me know if anything suddenly doesn't work. I suspect 99.8% of everything will be fine, but I don't know so let's test it
* as a side thing, I have adjusted my master URL lookup tool, which checks for duplicates in the file log and does 'already in db'/'previously deleted' url status lookups, to consider the leading single slash as matching the two slashes. I can't do the same for URL Classes though!

### enter vs add tags

* the manage tag parents and siblings dialogs are now 'add_only' from the 'add' button. previously, this was really an 'enter' command that would add new but petition pre-existing, but this workflow was never very intuitive and now we are reguarly dealing with hundreds of rows it is only ever confusing and annoying. similarly, the 'import' button now only offers a way to add new rows. sorry for the inconvenience here--I regret this took so long to figure out. if you want to do very large clever deletes, select the rows you do not want with ctrl/shift+click and hit the 'delete' button. if you want programmatic ways to remove rows (maybe a return of the 'import' conflict-remove, or a full-on only_delete mode), let me know how you would like it to look
* the 'CONFLICT: Will be deleted on add.' list notes as you enter siblings are now more varied and precise
* similarly, in manage tags, the 'allow remove/petition result on tag input for already existing tag' cog-menu option now defaults for new users to False, and all updating users will be set to False in v626. I don't like to force option changes on update, but most people are surprised to learn this option even exists, so I'm flicking us all, one-time, to the less confusing mode

### duplicates

* auto-resolution rules are now processed in alphabetical order. the preferred order in which rules and pairs are processed is a complicated topic and I am not sure on what is generally ideal, but if you have an opinion you can now force it
* I think I fixed some layout squish with the duplicates hover window. the window sometimes won't grow to be a little taller, particularly if a comparison statement goes from single line to multiple, which was causing the buttons to squish to make everything fit, until the user jiggled a window resize
* I think I fixed some transitional layout flicker with the duplicates hover window, particularly when some of the comparison statements are multiple line. also the previous pair's score line now properly blanks out while the new comparison statements are being loaded
* if a duplicate metadata merge options panel no longer allows you to set 'move from worse to better' tag action when you hit 'edit action' on a tag repository. this choice was accidentally being included here.
* if a duplicate metadata merge options does have 'move from worse to better' tag action set for a tag repository, through whatever grandfathered legacy reason, this is now treated as a copy action. previously it was hitting a 'you should not have been able to select this' safety check and doing nothing! if you have a hole because of this, don't panic--it is just another hole we'll want to fill in with retroactive duplicate merge, when we get around to that

### misc

* when the client adds or edits services, it now forces case-insensitive unique names. you can use whatever upper case you like, but you won't be able to make two services called 'score' and 'Score' any more. this helps out some parsing stuff
* same deal for subscriptions, duplicates auto-resolution rules, and import/export folders. not because we parse these names, but just to better differentiate big objects we want to be careful about
* fixed name deduplication when editing an import folder
* thanks to a user who submitted a PNG with 'srgb' colourspace metadata, I have fixed PNG colours for these files. this is related to the recent gamma/chromaticity work. a bunch of PNGs that previously rendered slow will now do so fast and with correct colours
* I've added `system:inbox/archive` to the list of selectable system predicates for all search file domains (previously they were hidden when your search domain had no 'real' and 'current' file domain). inbox/archive doesn't really have meaning outside of your local files, but advanced searches that switch file domain do sometimes carry these preds over to something like 'deleted from my files', so we might as well support them officially and fix the exposed nails. I think the logic will be crazy sometimes, and any counts too, so if you do clever searches and use them, let me know if and when they fail
* the routine that bundles many items into a single UI presentation text (for instance, when you paste a whole bunch of query texts into a sub and it talks to you about them) now deals with very long lists better. it'll now max out at 25 lines, each line about 64 characters, with the last being some form of 'and 741 others' overflow. we think that pasting many thousands of queries into a sub may have been causing out of memory crashes when a dialog &gt;32k pixels tall was being created. this obviously also generally fixes crazy tall dialogs in these cases
* when the file migration system chooses locations to pull from and push to, it no longer selects candidates of equal urgency pseudorandomly, but now pulls from the disk with the least free disk space and pushes to the one with the most
* fixed some 'repair missing file location' handling when the incorrect path is stored in the database in an invalid portable/absolute format. this may be related to some flatpak path magic
* a related problem where in rare cases a normal file migration would abandon the job early because it could not delist the old location is fixed

### help and env stuff

* updated help regarding running the db on BTRFS and NTFS filesystem compression. thanks to the users who let me know that BTRFS is ok and faster these days, particularly on WAL journalling, which we use by default
* added 'how to test and get `git`' to the Linux and macOS 'running from source' help
* clarified some 1/2, A/B stuff in the duplicates auto-resolution dialog text
* fixed some bad newline .md formatting in 'running from source' help
* updated the 'test' `mpv` version to `1.0.8` and `PySide6` to `6.9.1`

## [Version 625](https://github.com/hydrusnetwork/hydrus/releases/tag/v625)

### more ratings work and some QoL

* thanks to a user, we have several new items--
* in `services->manage services`, all numerical rating services have a new 'icon padding' value, which allows you to squeeze the stars together or push them apart. set to 0 to restore the old 'loading bar' way of presenting (square) numerical ratings
* the `manage ratings` dialog has better layout
* also, two new checkboxes in `options->gui pages` allow you to have the client ask you to auto-name new 'page of pages' on either creation or 'send pages to a new page of pages' events

### options

* `file->shortcuts` is gone! the same panel is now under `file->options->shortcuts`. I still hate how this guy works and want to merge all the sub-panels into one big user-friendly list with a filter and stuff
* the 'custom shortcuts' panel is now viewable in non-advanced-mode
* `options->sort/collect` is now split into `tag sort` and `file sort/collect`. the 'namespace grouping sort' is now in the correct location under the tag box whoops
* `options->media viewer` has all hover/background related options sent to the new `options->media viewer hovers`
* `options->gui pages` has had a reshuffle and the session stuff is pulled out to a new `options->gui sessions`
* all the stuff in `options->speed and memory` now starts collapsed
* the options dialog should be a little shorter by default now
* rewangled how the 'replace left/right with primary/secondary' and 'numpad non-number keys are normal' options in `shortcuts` work in the sub-dialogs--they still appear to apply instantly in the dialogs, but they now reset correctly if you cancel out of the main dialog
* the edit shortcuts panel now only writes to disk on ok if you actually edited something

### file relationships

* added a new 'media' file relationships shortcut command, `file relationships: delete false positives within selection`, and an equivalent menu command when you have multiple thumbs selected, `delete all false-positive relationships these files' alternate groups have between each other`, which removes false positives only between pairs of files in the selection, rather than the other 'remove false positives' command, which removes all known false positives. if you accidentally set a false positive on a pair, this is now specifically undoable by selecting the pair and hitting this
* when you do the various 'delete false positives' actions, you now get a popup saying how many were deleted
* gave the 'file relationships' file menu a quick pass. it stacks better and now says when a file has no relationships. the reset/remove submenus are also split apart to clarify action importance. this horrible thing should nonetheless absolutely be replaced, wholesale, with a nice review and/or edit panel
* cleaned up some of the various duplicate merge logic, replacing hacky stuff with unified calls etc.. I think some redundant potentials are now removed more smartly when you merge certain alternate group members together, and I think the 'confirmed alternates' list is properly cleared of B entries when you merge B into A now. some 'merge alternate groups when two files are set dupe' stuff is clearer and works more thoroughly too. I expect to add a 'clear orphans' maintenance command here in future to handle these legacy issues and cleverly fix any db damage
* when you explicitly set files as alternate, any previous false positive relationship between the two is now repealed rather than the job silently failing

### duplicates

* the 'A and B are visual duplicates' test now gives a negative result if either file has transparency, confidently if only one does and not if both do--it isn't smart enough to handle this yet
* the approve/deny buttons in semi-automatic auto-resolution rule review now do their work off the main thread and no longer block the UI on big jobs
* the 'preview' panel of an auto-resolution rule now fetches each block of pairs in a random order it figures out every dialog boot. if you open up a rule that has worked a bunch already, you can sit there watching it climb up to 500,000/700,000 and find nothing since it already did that front work. now it fetches randomly and will start population more swiftly. of course the results will now be in a roughly different order every time you boot the dialog, so that's not amazing--let me know how you find it. I think I may be adding a lot more random access like this, and that means where we will want unified pair sorting settings (much like we want in the manual duplicate filter, which still produces a garbage hardcoded fixed order of pairs!)

### subs and downloads

* a core multi-column list update routine is optimised significantly. when many new items come to a list after an edit event (usually mass add or some mass edits), it now selects all items at once. previously it was doing so one at a time, which was triggering a billion button update calls. doing a mass paste into a subscription, or doing a 'separate sub of 1000 queries into 1000 separate subs of one query' now takes about three seconds, instead of many minutes
* when you paste queries into a subscription, if some already exist in the sub but are DEAD, you are now yes/no asked if you want to revive them
* if a subscription has a gallery page that decides searching should stop, which for this purpose typically means it has 'caught up' to a previous sync, all additional pending gallery url jobs of the same url class in the gallery log will now be set to 'skipped' with a reason of 'previous blah url said: (original stop reason)'. this ensures that downloaders that produce multiple gallery pages in one step are now processed efficiently and obey the catch-up mechanic rather than overspilling the cull limit and adding old files back in--as soon as one page is 'caught up', the rest are skipped. I made this only skip of the same url class so as not to break NGUG subscriptions. if an NGUG produces multiple gallery pages of the same class, they may be thrown off by this since they will no longer check every outstanding gallery url unless the previous produced something useful--if you are clever enough to know what this means, let me know how you get on
* when a network job downloads a file from a Post URL, it now registers the bandwidth use to the Post URL's domains as well, if they differ. this should soon fix the issue where a site that produces files on completely different domain was not pausing when the file domain hits its bandwidth rules (file urls override bandwidth rules within three seconds in order to keep post/file url hits close together, which helps some token stuff, but if the post url never becomes aware of how much bandwidth it is eating, it just keeps on chugging. now it won't!)
* added a checkbox to stop the 'override bandwidth in 3 seconds' rule under `options->downloading`, but I'm hoping the above overall fixes the issue

### misc

* the page tab menu gets a new 'collapse pages' submenu. depending on where you click, it'll say 'this page', 'pages from here to the right', and 'pages to the right'. it will suck up all the files from the given pages and place them in a new locked search page, closing the old pages in the same step. use this for when you have eight small import pages in a row you want to collapse into a single processing page. it isn wrapped in a yes/no. it works on 'page of pages' too. this action is cool to do, so try it out
* the 'send down to a new page of pages' gets the same 'pages from here to the right' option too, so you can do both operations from the very left-hand side if that's what you want
* fixed a benign error popup when you hold the 'next image' shortcut while closing out on the last pair in a duplicates filter
* if attempting to send a file to the OS recycle bin results in a `0x80270021` error (many causes for this, but it seems it can also be an unluckily-timed sharing violation or a recycle bin with 100k+ items in it and being mega laggy), it is now re-attempted twice, with short breaks in between
* when, under `services->manage services`, you open an edit panel for a rating service that has stars, the client now repopulates the cache it stores of all your current custom svgs. no need to reboot now, just reload the dialog and it'll show what is current
* I _may_ have solved some indirect threading deadlocks. all threaded jobs also initialise just a tiny bit faster now
* blurhash generation, which can be a whack of CPU per import, is now a tiny bit more efficient

### boring stuff

* removed `setuptools` from the requirements.txts that don't have `pyinstaller`. we freeze the `setuptools` version to ensure a stable frozen build structure, so this isn't explicitly needed anywhere else
* refactored some of my advanced dev requirements.txts
* brushed up the 'running from source' help doc and added some info about testing/installing `pip` and `venv`, which aren't always available by default in Linux
* replaced all the `typing.Collection` style typedefs across the program with the `collections.abc` equivalents. this stuff was deprecated starting Python 3.9 lol. also, I'm pretty sure this was already true, but hydrus will now definitely not run in Python 3.8
* replaced all the basic `typing.List` style typedefs across the program with the standard `list` equivalents. same deal as above
* overhauled the 'db duplicates' unit tests, breaking up the previous monolith rollercoaster into something a bit more atomic. it is still a huge mess, but much better than before
* added some unit tests for the new 'remove false positives within selection'

## [Version 624](https://github.com/hydrusnetwork/hydrus/releases/tag/v624)

### locked pages

* the search page state where it could hold files but have no active search is back with some bells and whistles. it is now much easier to manage a 'scratchpad' file page that won't suddenly get messed up if you hit F5 (issue #1602, and likely others in different ways)
* all normal file search pages now have a padlock icon beside the autocomplete text input. clicking this collapses the current search to a single system:hash of the current media in view and swaps the search panel for an 'unlock' button. this page will not refresh its query until unlocked, at which point you are given the system:hash back
* if you add files to or remove files from the page, the underlying system:hash will update to the new contents of the page
* lock status is saved in the session, so it persists through restart etc..
* any time you create a page with files, which typically means, 'open files in a new page' and subscription file-popups, they now start in the locked state. since the system:hash updates for new files, you can drag and drop new files onto the page, or add more subscription files from a later sync, and the underlying system:hash now stays updated. play around with it--you'll see how it works
* if you are big brain and wish in some cases _not_ to sync the underlying system:hash on add/remove file events, a cog icon beside the unlock button lets you set this
* if you have a bunch of existing subscription landing pages and other 'I'll process this later' pages, please go through them after update and lock them. it'll say 'hey, you already have a system:hash but it differs to what is currently in view, do you want to overwrite this old one with one for the current files?' and you do, so click yes
* next step here is to finally figure out some sort of 'sort files by system:hash/downloader' sort type so these sorts of pages can restore original sort

### duplicates

* the 'preview' panel of an auto-resolution rule has had a complete pipeline overhaul. after a much, much, briefer one-time initialisation, it now loads results in fast small batches and streams pass/fail pairs to the lists one by one. it shows search progress and presents ongoing count of pairs. it no longer gets the total count of the search every time--unless you let it run all the way and get everything. the refresh buttons are more efficient, the 'only sample this many' widget updates the dialog live as you edit it, and there are pause buttons for both search and testing. it also cancels work faster if the dialog is closed amidst work. this dialog is now ready for the relatively CPU-expensive 'A and B are visual duplicates' integration
* when the core duplicate file searches they rely on are CPU-expensive, the duplicates filter batch pair fetch, duplicates filter count fetch, duplicates 'show some random pairs', and duplicates auto-resolution rule preview now load up faster, particularly when you have few potential pairs remaining
* auto-resolution rules that are in semi-automatic mode now only queue up a max of 512 files in the 'pending' queue. it can take some CPU to run these tests, so it is good to keep the queue short and snappy in case you need to change anything (thus resetting the queue) in future. you can alter the 512 limit, including removing it completely, in the edit rule panel
* auto-resolution rules now categorise their comparators into a cross-reference of fast + order-possibly-important. the main testing routine and 'can this pair fit either way' test now cascades through some logic to get a dispositive true negative result faster
* the program now recognises and gracefully handles the situation where the duplicate filter is closed and program shut down initiated before a slow-loading visual duplicate pair can finish (it was outputting some mysterious error lines to the log)

### a and b are visual duplicates

* if the images are very simple, e.g. just one or two flat colours, they are now considered 'too simple to compare' and not visual duplicates. these edge cases are often deceptively tricky
* if the images have a perfectly matching interesting tile, the presence of any non-matching tile now results in 'probably not visual duplicates/(small difference?)'
* I experimented with many new techniques: pre-decimation histogram population, histogram absolute difference comparison, tile phashes, longer tile phashes, gaussian edge detection histograms, gaussian edge map average block 2d wasserstein scoring, and even gaussian edge map phashes, but unfortunately these all pretty much failed. the algorithm as-is is good, but there are still a couple of false positive situations it cannot catch. the delicate edge detection is the main thing--a difference with a subtle shade (e.g. a soft line, or a transparent water droplet) that is clear to the human eye can still be missed. please keep sending in any false positives, and I'll keep thinking about all this
* cleaned and polished a bunch of this code

### misc

* thanks to a user, the new resizable ratings have improved visuals! the little padding clipping bugs are fixed and everything lines up nice
* 'less than or equal to' and 'greater than or equal to' are added to all the modernised places you can set a number comparison, such as `system:height` or duplicates auto-resolution comparison statements
* fixed the broken `Ctrl+C = copy selected files` default 'media' shortcut for newer users--if it is broken for you (it'll say 'Unknown Application Command' in the shortcut UI), it will fix itself on update

### updated Linux and Windows builds

* the 'future build' last week went without any reports of problems, so I am folding the changes into today's normal build. both Windows and Linux are updating several core components and will gain a host of small and large bug fixes and performance improvements. It does not seem that a clean install is needed this week, but if you use the zip or tar.zst extracts, you might like to take this opportunity to do one anyway: https://hydrusnetwork.github.io/hydrus/getting_started_installing.html#clean_installs
* the WIndows installer basically does a clean install every week, so no special instructions there
* the changes are--
* Windows and Linux: moved from python 3.11 to python 3.12
* Windows and Linux: moved from PySide6 (Qt) 6.7.3 to 6.8.2.1
* Windows: moved from windows-2019 runner to windows-2022 (2019 runner is being retired next month)
* if you use a particularly old, un-updated version of Windows 10, it is possible the new Windows builds will not run for you. try running from source and choosing an older Qt version: https://hydrusnetwork.github.io/hydrus/running_from_source.html
* if you already run from source, you might like to rebuild your venv this week to get the new Qt. users on Python 3.13 no longer have to choose the (a)dvanced mode for the (t)est Qt version-- on a typical OS, all pythons from 3.10-13 should now work with (s) out of the box!

### weird/boring stuff

* I fixed some encoding in my png gamma/chromaticity ICC Profile generator. it still isn't there, but I know where to look. also wangled the `wtpt` and `chad` to handle non-D65 source whitepoints
* I may have fixed an issue where the thumbnail banners could be drawn with bold text
* my asynchronous updater object can now deal with several mid-job cancel events
* my thumbnail pair list can now handle streaming appends
* deleted the monolith 'get potential pairs that match this duplicate context' routine the preview panel was relying on. I'll migrate more duplicates stuff to incremental fetches like this, and I feel good we can make the duplicate filter and so on initialise much quicker
* updated the client api help's Hydrus Video Deduplicator link to https://github.com/hydrusvideodeduplicator/hydrus-video-deduplicator
