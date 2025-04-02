---
title: Changelog
---

# changelog

!!! note
    This is the new changelog, only the most recent builds. For all versions, see the [old changelog](old_changelog.html).

## [Version 616](https://github.com/hydrusnetwork/hydrus/releases/tag/v616)

### more media viewer stuff from a user

* thanks to a user, we have some more media viewer updates--
* first, if you use multiple media viewers from different tabs (especially complicated nested tabs), you can now set a 'close-media-viewer' shortcut action that does 'close-media-viewer-and-return-to-the-tab-that-opened-it'. a new checkbox under `options->media viewer` allows you to mandate this all the time
* second, the media viewer 'eye' menu button has two new settings for setting 'always on top' and removing the window frame. these options are a little experimental and don't save just yet. have a play with them and let us know how it goes, especially on more unusual OSes

### misc

* you can now mix and match as many `system:hash` predicates in a query as you like. the UI will no longer consider them mutually exclusive when editing, and in the Client API, where you can force two at once, it no longer pseudorandomly chooses one to actually use
* fixed export folders that have multiple sidecar routers that have the same file destination. previously only one of the sidecars was adding data and the others were doing nothing. (my recent 'genius' 'optimisation' code was going 'oh, that sidecar already exists, do not update it')
* the export folder UI has a label on the sidecar section saying 'hey, export folders will not update pre-existing sidecar files, if you change them make sure to delete the existing sidecars and they will regenerate on next run'
* when subscriptions hit their periodic file limit, they now compare the url classes of the new fetch with the oldest url class in the file log; if they differ, it no longer shows the 'subscription found x new URLs without running into any it had seen before' popup that offers the gap downloader! since in this case, the site/downloader has changed URL format, and the recommendation is to ignore the messages, I now no longer show the messages. we are doing this this week, so let me know how it goes
* the 'search enabled' system, which on very old subscription presentation pages would allow for a search page that just presented files and had no search panel in the sidebar, is completely removed. the echoes of this thing have caused several typo problems over the years, was anti-KISS, and I intend to completely replace it with a nicer dynamic search freeze/sync system that will sync the page's current files to a fresh system:hash pred
* the duplicate metadata merge options panel now has separate buttons on the tag service list for 'edit action' and 'edit filter'
* the duplicate metadata merge options panel has a new label to clarify how ratings merge
* the core Exception-handling routine can now handle an Exception with an empty string in its value
* Errors that end up in a popup use the nicer log-printing routine to form their traceback, and they print to the log using this system too
* errors with no trace no longer spam the stack twice

### e621 and more

* _tl;dr: today e621 is fixed to get tags again and I add e926 and e6ai. your subs will do some extra CPU work to catch up but it isn't a big deal_
* the e621 sites have been changing their html recently, and it broke our parser--suddenly it wouldn't get tags any more. the good news is that someone let me know their API is excellent, so I am rolling out a fixed e621 downloader, and downloaders for e926 (their sfw alternative) and e6ai (their ai containment booru), and pool URL support too. since the API is so good, the downloader now runs extremely efficiently--all the normal 'post' data is provided at the gallery step, so e621 downloaders will hereafter only need to hit the gallery page and then they'll be downloading raw files directly. the only drawback here is the gallery parsing step eats a whack of CPU all at once, which you'll notice if you go bananas (issue #1698)
* your e621 subscriptions will see the new direct file URLs and not be able to knit that together with the old Post URLs they already have. there is no nice technical way to get around this while keeping the nice new efficient downloader. we would normally be blitzed by the 'subscription found x new URLs without running into any it had seen before' popups that offer to open up the gap downloader, but I hate offloading that problem to user and have written in some new logic this week to detect the 'oh it is basically ok, the url format just changed' situation and silence the report in this case. luckily, your temporarily bloated e621 subs will process the 100-odd 'new' URLs they see very fast because there will be an md5 and raw file URL and e621 Post URL and tags to help it realise 'already in db'/'previously deleted'/'tag-blacklisted' without having to make any more network requests. serendipitously, this will actually help to fill in the gap of missing tags users have had over the past week or two. all users will get a popup about this on update. **if you changed your e621 subs to have a very high "normal checks" file limit, edit them before you update! 100 is proper**
* several users were quicker than me, and I appreciate the suggestions and submissions. I made heavy use of an API parser one user made, fixing a couple tiny things and making it work for more domains, and that's what's rolling out today. you do not have to do anything--it should all just work. if you have added or played around with your own e621 parsers and today's update seems not to have worked, check out what's going on under `network->downloader components->url class links` and the other dialogs under there--worst case, if things aren't lining up, just delete everything 'e621' related and add back from the defaults

### duplicates auto-resolution

* thank you to the users who tried out the new system. although it works technically well, the common consensus is that it is _too_ automatic and needs A) the ability to pump the brakes and let humans better review what it is about to do and B) remember the pairs it actioned so humans can review what it just did. I am launching these features today for more testing and delaying the all-user launch of the system.
* unfortunately, the changes I am making to the database are not compatible with the jpeg/png test rule from last week. on update, if you have the rule, you will get a popup saying 'hey, sorry, have to delete the rule now'. you can recreate it just as you did before, but the count it had of how many pairs it had processed has to be reset back to 0
* you now choose if rules are going to be 'paused', where they do nothing, 'semi-automatic', where they will search and test but not action until the human approves, or 'fully automatic', where they will search, test, and then action entirely on their own (as before). new auto-resolution rules now start semi-automatic by default
* beside the 'edit rules' button, there's now a 'review actions' button. double-clicking a row in the list now launches this. it opens up a panel for the selected rule with new thumbnail lists that show any semi-automatic pending pairs and the actioned pairs. they both allow multiple selection. the 'pending actions' page has approve/deny buttons, and the 'actions taken' has a powerful undo button that's wrapped in a scary yes/no confirmation. these panels are non-modal, meaning you can still use the program while they are open. the actioned audit log will often have fully deleted files so will present a blurhash or the hydrus default thumb, and any deleted files obviously won't launch in the media viewer
* the thumbnail pair lists that show a pending action, which used to just show 'it will be this AB' vs 'could be either way around', now also says the duplicate action to be applied and an experimental summary of all content updates about to occur to both A and B. you'll see the tags, notes, urls, ratings, and archive actions--let me know how this works IRL, since I think we'll need some better sizing tech to make it all fit nice
* a 'duplicate metadata merge options' that is set to 'always archive both' will now perform 'if one is archived, archive the other' if ran through the auto-resolution system. the auto-resolution edit UI says this explicitly. KISS answer to this sticky problem.
* in the preview panel of the edit UI, the 'pairs that will be actioned' and 'pairs that will be skipped' lists are now collapsible
* the cog icon on the duplicates auto-resolution sidebar now has 'reset test' and 'reset declined' to re-test all current pending/fail test results and undo all user-declined pairs
* the main auto-resolution rule dialog now has some WOAH LAD red text at the top
* updated the help with new screenshots and stuff for the new semi-automatic and fully automatic modes

### boring duplicates auto-resolution stuff

* all resolution rules and associated data will be deleted on update. sorry!
* auto-resolution rules ditch the paused bool and now have a tri-state operation mode--paused, semi-automatic, and fully automatic. the semi-automatic does all the search and test work but queues 'ready to action' pairs for human approval. when a rule switches to fully automatic, all 'ready to action' pending pairs are sent back to be re-tested in the normal queue for KISS
* added a new status for 'passes search, passes test, ready for actioning', with a custom pair storage table, to handle the semi-automatic mode where it prepares pairs and the human approves them
* same deal but for 'user declined to action', for when the user does not approve
* figured out the pipeline for this
* added a table to log AB file pairs actioned. it records the duplicate action and the timestamp also. the 'pairs resolved' count is now generated from this live and stored in the normal count cache table
* figured out the pipeline for this record
* I vacillated and wrote some code to make the history try to 'live sync' to current data, but in the end I decided to go full non-changing audit log. if you dissolve a duplicate group and re-action the files with the same rule, the log will have two entries
* if a rule's selector changes after editing, all pairs in the 'failed test' or 'ready to action' queues are now reset to 'passes search, ready to test'. relatedly, pair selectors can now equality-compare themselves to each other
* the thumbnail pair lists that list duplicate merge summary data now calculate that third column in an async thread. previously this happened in one big block before the list was populated, but in future selector work will be high CPU (think comparing image similarity live), so it now happens on each list row as it comes into view. there's still a little more work to do here in the preview panel
* refactored the new thumbnail list classes out to their own file and renamed some things to be more generic (for use in the new 'review actions' panel too)
* if a user tries to edit the auto-resolution rules while any of the new preview windows is open, the preview windows are closed
* the thumbnail lists now check if media it wants to open in the media viewer is local lol
* cleaned up the 'reset search' and 'reset test' maintenance calls and improved efficiency
* refactored how I move pairs from one database queue to another and cleaned it up a bit. a lot of maintenance and other reset stuff now all goes through this one location
* a bunch of misc refactoring and cleanup of the auto-resolution db module

### unit tests

* added unit tests for the semi-automatic auto-resolution rule queueing, queue-fetching, and approval and denial processes
* added unit tests for the audit log after all other unit tests commit actions
* added a unit test to ensure changing the search resets searched pairs back to 'not searched'
* added a unit test to ensure changing the selector resets tested pairs back to 'match search but not tested'
* added a unit test to ensure changing from semi- to fully automatic resets 'ready to action' pairs back to 'not tested'

### misc boring stuff

* added a convenience function to the media results database module to fetch pairs of media results
* made my static box change its size policy to fixed when it is collapsed--it now tucks itself away where before it was expanding to any available space
* fixed the new auto-resolution unit tests for python 3.12+. thanks to a user for reporting--I was using the deprecated `assertNotEquals` instead of `assertNotEqual`
* fixed some Mr Bones crazy text alignment and he now tells you in the duplicates panel to set to "all files every imported or deleted" to get better "all-time" numbers
* Mr Bones now gives more accurate 'total files in alternate groups' numbers and also says the total number of alternate groups. previously, he was basically adding a bunch of duplicate files in there that were standing on their own and hadn't actually been set alternate to anything
* updated my 'install help' Linux tab Wayland section to say 'yeah, best solution is X11 for now' with the two ways we know of getting that to work within Wayland. that's my Wayland policy going forward

### client api

* the Mr Bones call on the Client API now has a 'total_alternate_groups' key, reflecting the new number in the window
* Client API version is now 79

## [Version 615](https://github.com/hydrusnetwork/hydrus/releases/tag/v615)

### duplicates auto-resolution brief

* the system is ready for advanced users to try! there is one simple static rule available. check out the help https://hydrusnetwork.github.io/hydrus/advanced_duplicates_auto_resolution.html , go into the UI, and try out the suggested pixel-perfect jpg & png rule. I want to know if--
   - it all makes sense to you
   - where it runs smooth
   - where it runs garbage
   - any errors?
   - out of interest, what do you get? Of ~800k potential pairs, I had ~6,000 jpg/png pixel pairs, resulting in ~4,700 total actual processed pairs (numbers shrink because multiple good files can share the same bad file). speed was bleh in the preview viewer (about 30 seconds to load the preview numbers) but nice when doing work: only a second or two to save the rule and then ~20k files/s in the search stage and 10 files/s in the processing stage. about 7 mins to ditch 7.5GB of Clipboard.png, hooray

### duplicates auto-resolution

* fleshed out the help page here: https://hydrusnetwork.github.io/hydrus/advanced_duplicates_auto_resolution.html it is linked in the main help directory, too, under 'advanced'
* made it so you can double-click or enter/return any pass/fail test row in the auto-resolution preview panel to open that pair in a normal media viewer
* added `work on these rules during idle/normal time` to the cog button on the auto-resolution sidebar tab
* wrote up 'work hard' functionality and wired up the button--however I think I might remove this, since the system works well enough on its own. let me know what you think
* reworked the preview panel to have a two-stage search. it spends a whack of CPU time fetching the total count of the search, and then the sample part works faster afterwards and can be hit over and over. it still sucks and I have another idea to speed things up, we'll see
* updated the main duplicates auto-resolution maintenance routine to do the search step in blocks of 8192 rather than trying to do everything at once as soon as a rule is added. I hesitated doing this earlier, since the large one-time init search is more efficient, but we are going to be doing incremental searches in normal operation, so making small search chunks work well is not optional. I think the biggest potential weakness of this whole system is going to be incremental searches on new potential pairs when the potential duplicate pairs search of the auto-resolution rule has significant per-search overhead, but which searches will those be? sounds like we'll find out in the coming weeks. thankfully, jpg/png pixel dupes seems to scale excellently, so we are good for today

### misc auto-resolution stuff

* reduced flicker on the main 'auto-resolution' review panel as it works a real rule
* fixed a 'hey I guess the auto-resolution preview panel is 1200px wide now' bug on certain rule-fetch validation errors
* renamed 'A will pass' comparison UI labels to 'A will match'
* the preview panel lists now scroll one row per scroll (it was doing 3 before, lol, and the default height is ~2 rows)
* the auto-resolution preview panel (particularly the 'will be actioned' list, with its third column) should size itself better if you have large thumbnails
* if the auto-resolution preview panel had results but the search changes and now we have no resullts, the test result lists will now appropriaterly clear themselves
* the preview result lists now generally clear nicely before a new search is started, so if something actually goes wrong, you don't have old test results hanging around
* fixed incremental potential duplicates search on non-pixel-duplicate searches

### unit tests

* wrote unit tests for the `MetadataConditional`
* wrote unit tests for all the predicate types that can work in the `MetadataConditional`
* wrote unit tests for the `Selector`
* wrote unit tests for the one-file `Comparator`
* wrote unit tests for auto-resolution rules: for editing at the db level; for syncing to existing, new, dissolved, and resolved potential duplicate pairs; performing search; performing resolution

### misc

* fixed a typo bug that broke the maintenance job that resets all potential duplicate pair search. it was related to the recent auto-resolution integration
* fixed a typo bug that was stopping the 'review accounts' repository admin panel from opening
* added an FAQ about the extensionless files that appear in your file storage if you sync with a repository
* added `LINUX DEBUG: Do not allow combined setGeometry on mpv window` to `options->media playback`. if you have crashes on X11 in v614 when zooming mpv windows, give it a go and let me know what happens
* thanks to a user, added a note to the install help that if you are on Linux & Wayland, adding the `WAYLAND_DISPLAY` environment variable, which forces the program to run in XWayland, seems to relieve many UI bugs (issue #1695)

### boring cleanup

* cleared out a surplus entry in db init related to duplicates auto-resolution
* tweaked the 'don't show hovers/hide cursor if a dialog is open' tests in the media viewer, ignoring them if we are the child of one lol

## [Version 614](https://github.com/hydrusnetwork/hydrus/releases/tag/v614)

### misc

* the new `system:tag (advanced)` edit panel now has a 'write/edit' tag autocomplete to help you quickly enter what you want to search
* the `system:tag (advanced)` predicate now works in the system predicate parser. everything it produces should be pastable back into the tag autocomplete and it'll all just work (I believe even crazy situations, but let me know how you get on). it is somewhat error tolerant, so you can type just 'pending' instead of 'status is pending' etc.., but it is best if you get the colons, commas and quotes correct
* reworded the labels in `system:tag (advanced)` to say 'ignoring siblings/parents' rather than just 'siblings'. I was thinking about this the wrong way when I first implemented it and forgot to realise and mention that when searching in the 'storage' domain, you are missing tag mappings that would be implicated by parent relationships too
* thanks to a user, we have two new QSS styles--'catmocchin blue' and 'catmocchin lavender'. there are additional style and colour suggestions inside the QSS files themselves
* the default image cache size under `options->speed and memory` is raised from 384MB to 1GB, which means by default the cache will hold on to a ~12,600x7,000px image and prefetch a ~9,700x5,500px one. it was previously tuned for 4k, but we are going to push a little further
* `speed and memory` also lets you raise the prefetch cache percentage up to 25% (from 20%) (issue #1693)
* I discovered that the bug in the media viewer where a static image will do a flickery resize--where on zoom it will move to position and then scale in two discrete frames--is triggered by loading the mpv window in that media viewer! it seems like mpv sets some deep 'immediate render' flag on the window. I hacked around a bit and believe I have fixed this bug. a rewrite of the entire media viewer layout system remains pending, but I think we fixed this very annoying thing!
* I may have also fixed some other change-media flicker too, let me know how you get on
* the 'macOS window position fix test' debug mode is now default behaviour. if you noticed your dialog windows were moving down like 26 pixels on every open in macOS, it should be better now! (issues #1681, #1673)
* fixed a bug when searching files with 0 width or height (this is mostly a legacy issue) with a file-sort set to image ratio
* if you try to run `profile mode` on python 3.12+, you now get a popup saying it is broke atm and hydev will fix

### new media viewer tech

* thanks to a user, we have some great new media viewer zoom and display options
* there's a new zoom icon button in the top hover that lets you set some new zoom types: default for filetype, 100% zoom, canvas fit, fit horizontally, fit vertically, and canvas fill
* also, we now have 'lock current zoom type'! so, you can switch to 'view this image as 100%', and that will stick for the next file as you browse back and forth
* also, there's 'lock current pan'! useful for comparing duplicates at high zoom
* _and_ there's 'try to lock current size', which copies my duplicate filter's 'lock zoom amount' tech for the normal media viewer
* these three 'lock' options are saved, not per-media-viewer-session
* you can say in `options->media playback` what zoom type you would like the viewer to default to. the default is 'default for filetype', lol, which I generally recommend, but you can set to always override all filetypes with 'canvas fill' or something if you like, particularly, say, on the preview viewer
* also, under the 'eye' icon, or `options->media viewer`, you can now set the tags hover and/or top-right hover to not appear on mouseover!
* the 'media viewer' shortcut set gets actions for the new zoom types, a new three-way zoom switch, and a new 'recenter media' action
* I fixed a couple things with this for weird stuff like excepting audio and open externally panels. I also span out the duplicate filter zoom maintenance into its own thing and added it to the new menu as the 'lock current size' choice, reworked the options stuff a little to fit in with the existing per-filetype zoom settings, added some checkboxes to the menu for feedback, added the 'recenter-pan' action, and since graphics design is my passion I made a new icon for the advanced zoom settings icon button, yes it is a cog icon placed expertly over a magnifying glass
* I think I fixed some zoom bugs in the duplicate filter with 'open externally' and audio panels

### duplicates auto-resolution

* _everything went great. should be launching the initial test for advanced users next week_
* extended the new preview panel a bit--added a 'only sample this many' number widget, defaulting to 256, so you only start looking at a fast preview of the potentially tens of thousands of results; made sure the results always sort the same way (pseudorandom, but fixed); and added a third column to the 'pairs that will be actioned' list to show if the AB pair is fixed as you see or could be either way around
* wired the potential duplicates storage module up to the auto-resolution storage module. when a potential pair is added or removed, the auto-resolution rules are now synced in the same transaction
* buffed the 'add pairs' tech here to ensure even if the two modules get desynced somehow, the auto-resolution guy won't add dupes by accident
* hooked the 'delete orphan rules' and 'fix orphan potential pairs' auto-resolution maintenance jobs up to the cog icon menu button in the auto-resolution sidebar panel
* wrote some async code to handle waiting for any current work to finish before launching the edit dialog, and only allowing one edit dialog at a time
* added a refresh button to the review panel
* fixed up and finished the main 'set rules' pipeline, including generation and propagation of rule_id and counts cache
* reworded the rule status summary text to put pertinent info at the front
* hooked up the main search and resolution worker db calls
* fixed a ton of stupid typos in the auto-resolution db code
* enabled the UI, tried it out; the whole system works!
* the UI is enabled for today, but the edit rules dialog will not save anything. non-advanced-mode users can also see the new tab now. I will take another week to write up some unit tests and help and do a more complicated IRL test. I also didn't have time to add the media viewer so I'll make sure that gets done. otherwise, we appear to be basically ready here. I'm feeling good about it, but I still want to be quite careful

### boring cleanup

* I cleared out some bad old and duplicated canvas zoom code, and I migrated some variable handling to use the smarter stuff in the new commit
* replaced some laborious resolution validity-testing code with a single call in media result
* cleaned up how potential duplicate pairs are deleted in the main duplicate files db module. it now happens through a handful of central locations rather than spammed all over the place, so the signalling to the auto-resolution module is a good bit simpler
* fixed the permalink id in the client api help for `/get_files/thumbnail_path`. also fixed the example requests, which were also a sloppy copy/paste job from the 'thumbnail' command haha
* fixed some `None` to `null` in the client api help response examples

## [Version 613](https://github.com/hydrusnetwork/hydrus/releases/tag/v613)

### misc

* I think I have fixed the crazy flickering dialog resize bug where if you resize certain dialogs shorter or thinner than their parents, they might flicker throughout your resize motion between the size you are moving to and the height/width of the parent. there's still some occasional flicker due to some other legacy fuzzy padding hacks, but things are better
* fixed some bad grammar for the namespace hide/show options in `options->tag presentation`, and split the non-namespace rendering settings out to their own box
* when files are imported, any existing 'media result' object for the file is now properly updated with the new file modified time. you usually wouldn't notice this, because the media result typically isn't loaded until after import when we need to show it on screen, but in advanced cases where you were re-importing previously deleted files you are looking at or doing Client API work where you did a URL lookup before deciding to import, and the media result object from the URL lookup was still in memory, the 'media result' was not getting the timestamp and subsequent inspections or edits of the modified timestamp were failing as a result until the media result had a chance to decay out of its cache and be reloaded from disk
* made some ratings update and sort code more safe against ratings service deletions
* url classes now allow 'keep extra parameters for server' if you have an API/Redirect URL Converter. I _think_ the reasons for this originally being prohibited were only a fear, not anything grounded, but let's see how it goes

### system predicate for advanced tag search

* _after talking about it with people recently and having some good ideas, I decided to just push and try to knock this out. it is pretty clever and may have bugs, so let me know how it goes_
* added a new `system:tag (advanced)` predicate, which does sophisticated tag searches. you enter a tag as raw text and can then--  
    * specify which tag service it should search on, if different to the current tag context
    * specify if it should include siblings or just be the raw tag on the 'storage' domain
    * specify whether you should search current, deleted, pending, or petitioned mappings
    * specify if the file _should_ or _should not_ have the tag mapping
* I ran out of time to implement system predicate parsing, but I planned the pred's label to support this and will try to get it done next week
* searches that include unified or deleted file domains or any other crazy stuff may take a very long time to return, but the underlying tag search code in hydrus is pretty robust, and extending it to the newer domains all just came together, so I think everything works. it should respond quickly to the cancel search button if it takes too long

### duplicates auto-resolution

* I had more success than expected with the new preview panel and I think we are now about two weeks away from the initial user test of this system
* the edit duplicates auto-resolution rule dialog now has a live preview panel. it loads the pairs of a rule's search and then does the comparator/selector test to determine which pairs pass or fail, showing you the counts at each stage
* the panel also shows the pass/fail thumbnail pairs with some new 'thumbnail table' widgets I wrote. these load thumbnails asynchronously and should scale up to thousands of pairs no prob. I am really happy with how it worked out, as this was the thing I was dreading would take weeks of rewrites, but I figured something out. it is ugly, as always, but it works
* every time you show the panel page, it checks if the rule has changed. if search has changed, it re-runs the whole search, and if only the selector has changed, it just does a re-test
* next week I'll add the ability to launch a particular pair into a standard Media Viewer so you can 'look closer' on the preview, and then I'll be doing final integration and testing. we are on the home stretch now!
* _if you are an advanced user and you've poked around the duplicates auto-resolution UI previously, you might like to check out the preview panel this week on the default jpg vs png rule--does it all seem to load up sensible results, even though you can't zoom in yet? any errors? I'm guessing that loading thousands of pairs is going to be super slow, so what would be a good number to sample--256?_

### boring cleanup

* reworked the client thumbnail cache to work on the simpler and lower-lever `MediaResult` rather than the UI-level `Media`
* fixed a couple areas where file maintenance jobs were being scheduled using the `Media` object
* fixed some old areas within file maintenance where media objects had the wrong name
* reworked and cleaned the main GetThumbnailPath RegenThumbnail file routines to similarly only work and talk about `MediaResult`
* fixed a dumb typo in the as-yet-enabled `MetadataConditional` edit-panel
* updated the faq with answers for why I work alone, do weekly releases, and use weird versioning
* fixed a couple places where I had accidental `/n` in some label text lol, thanks to the user who pointed this out

## [Version 612](https://github.com/hydrusnetwork/hydrus/releases/tag/v612)

### misc

* I added 'you can scan for this' flags for JXL for rotation EXIF, has EXIF, has non-EXIF, has transparency, and has ICC Profile, which we forgot to add when first rolling out JXL support. all existing JXL files will be scheduled for rescan of these properties on update, so if you have any wrongly rotated JXL, they should fix themselves soon after update (issue #1684)
* the 'duration' duplicates filter comparison statement now says the +/-% difference in duration. if it is only +1%, it is now clearer
* if a server gives a 429 (Too Many Requests) with a 'Retry-After' response header, hydrus now obeys this rather than its default server retry time as set in `options->connection` (issue #734)
* added `help->debug->debug modes->macOS window position fix test` to test a fix for macOS windows always getting delta y position on init

### drag-cancelling tech

* the new drag-cancelling tech was false-positive cancelling fast drags where you moved the mouse outside of the window 200ms after the initial click press. this is fixed
* the new drag-cancelling tech no longer occurs on macOS, since it was raising an error. it seems due to system policy you can't programatically cancel a drag on macOS in Qt (issue #1685)

### sidecars in export folders

* an export folder with sidecars will now fill in any sidecar gaps on every run. if a file should have a sidecar but currently does not, the sidecar will be generated (issue #1682)
* an export folder set to 'synchronise' (which deletes files from the export destination if they are no longer in the export folder's search) will now be more careful not to delete sidecars

### some running from source stuff

* for users who run from source, the 'test' `PySide6` is updated from `6.8.1.1` to `6.8.2.1`, and the `qtpy` from `2.4.2` to `2.4.3`
* added a `open_venv.ps1` script to easily activate the venv in powershell

### duplicates auto-resolution

* _my work this upcoming system grinds on. I successfully did the thing I stalled on a couple weeks ago, and now the only big thing I still have to do before advanced users can try it is a preview panel and a billion unit tests_
* the database modules are live! they boot and will initialise their (as-yet empty) tables on update to v612
* the daemon is now live! it runs its full mainloop and consults the database modules for work
* rewrote some daemon-db interaction, mostly for KISS and deduplication of responsibility
* figured out some tech to reset duplicates rule search progress on edits and user command
* simplified the daemon workflow so that rules hold on to cached search counts and report their own search status
* fixed some stuff in rule-setting and status fetching
* the auto-resolution rule object is now serialisable and _could_ be saved to disk if I enabled the edit UI
* rules now report their correct search status, no longer a placeholder
* the daemon now reports the correct running status, no longer a placeholder

## [Version 611](https://github.com/hydrusnetwork/hydrus/releases/tag/v611)

### misc

* I am pretty sure I fixed the long-time 'hey why did the scrollbar on this page of thumbs reset to the start position sometime while the page was hidden?' issue. an importer that adds new rows of thumbs in the background should now retain its scroll position. a window resize or a mass file removal event will cause the scrollbar to stay at the same relative num_rows vertical position, which we may ultimately want to be more sophisticated, but this is a good step for now. let me know if any specific situation still resets the vertical position
* fixed an interesting bug with two of the Drag and Drops in the program, when you DnD a page tab or a selection of thumbnaills, where if you released your left-click at just the right moment (about 100ms after click press), you could get a DnD state that persisted despite no mouse button being down. a subsequent click would clear it. it seems that the DnD was spawning while the click release was already behind it in the event queue. the program now recognises this state and cancels the DnD
* I believe I fixed an issue with the `apply image ICC Profile colour adjustments` entry on the media viewer's 'eye' menu button, precisely when you were looking at a file. the static image's private tile cache was not clearing itself correctly, and not calling for an update after the clear, so old yes/no ICC-profile-adjusted tiles were hanging around and sometimes poisoning future calls. the whole system clears itself properly now and seems to flip good every time
* I believe I have fixed a macOS issue (and I think X11, too, if you have a taskbar on the top of the screen) where the hydrus window position-recording system would move your windows down a little way on every save/load cycle
* all the 'write/edit' tag autocomplete inputs that have a list above them now send a copy shortcut to that top list when there is nothing selected in the text box and there are no results in the list below. so, if you open the 'manage tags' dialog, and the first thing you do is hit ctrl+c, you'll copy everything in the big list of existing tags. hit ctrl+shift+c, and you'll get the parents too
* all the hardcoded 'copy' shortcut detection now happens through the same location and counts ctrl+c or ctrl/insert
* if the 'is user ok to ok/cancel' dialog pre-close checks raise an error, I now have a catch for it. it says 'hey user, these checks threw an exception, please contact hydev, the data was probably broken so here is what to do next depending on whether you were oking or cancelling'. previously, you could be stuck with an unclosable dialog and have to quit the whole process
* same deal but for the dialog 'is the data in the panel valid?' check--there is now a special catch and it tells you what happened and what to do
* fixed a regression from last week's "make sure the new note is focused when the current tab changes" call, which was throwing a spurious error when you deleted the last note (issue #1679)
* fixed an issue with my mpv rewind-spam catching code when you force it to load a file without any duration

### file sort

* if you change the file sort on a search with an explicit system:limit, and the sort is one that can operate at the database level, the search will now refresh
* added a checkbox to `options->file search` to turn this off if you prefer
* the file sort widget now has a tooltip saying whether the current sort type is simple enough to work with system:limit

### stopping accidental page close

* if you try to close a downloader that has any items in it, you'll now be asked if you are sure. this doesn't apply to session exit, just manual user close events
* you can turn this confirmation off under `options->gui pages`
* another checkbox under `gui pages`, this time default off, allows you to confirm all page closes. this mostly catches middle-clicking single page tabs, be that file search pages or 'page of pages'
* the routines that delete multiple pages in one step 'close other pages' etc..., now do the 'is user ok to close these' in one combined step for all closees before closing anything. previously it tested and closed each in turn, and a cancel event broke out of the loop
* various 'close these pages?' messages now correctly add up the number of sub-pages in 'page of pages' to be closed

### long-time bug with non-updating media viewer is fixed

* for ages we've had a weird issue where the media viewer, on some random file, will suddenly update when you click on ratings and things. the content signals are going through, and you can watch the file's respective thumbnail in the main gui getting archived or whatever, but the media viewer will not show it. this is finally fixed! it was basically a rare maintenance update issue, where if, for instance, a 'regen file metadata' job occured on a file in a media viewer's list after the media viewer was spawned, the media object in the viewer list was falling out of sync; able to send content updates but no longer hooked into the update pipeline so it never received them back again
* this is fixed for the 'force filetype' action. this job now propagates to the UI much faster than before, no longer needing a full media result load
* this is fixed for the file maintenance jobs that regen file metadata, check for 'has icc profile' etc.., and regen pixel/blurhash. all these jobs now propagate in the same way much faster to the UI
* this is fixed for the file maintenance job that refetches the file's modified time from disk. same deal it now updates in UI faster
* also fixed in the case where a previously known-of file is imported and we discover our old file info was incorrect, and also this file was in view so we need to sync the media result. sounds like a crazy situation but that's exactly when you need this to work

### tag context in media

* the thumbnail grid is now aware of the current tag context of the search (where you set 'all known tags' or 'my tags' or whatever in the autocomplete dropdown). `system:number of tags` now follows the current tag context

### shortcuts

* in an experiment, you can now set the modifier keys as their own shortcuts, with no accompanying 'real' key. it'll mark it as 'ctrl+nothing', 'shift+alt+nothing', etc.. seems to work, but I can't promise it won't go crazy in the wrong place
* the keyboard shortcut widget, where you enter a shortcut, now uses a shortcut catching routine that is one level higher than before, which matches the actual shortcut processing system that's in use. there's a chance that if your Qt hardcode maps some shortcut, not allowing it in a text edit box, it'll work now (issue #1674)
* the keyboard shortcut widget no longer shows its caret. it also takes keyboard focus more reliably when the edit shortcut dialog boots. I kind of like this but also don't, let me know if it is jarring
* the 'shortcut report mode' will now say some information about unmappable key presses
* I have prepped some render code to show shortcuts on macOS in the form ⌘Z, but I have not enabled it yet because I don't know enough about macOS. if you want your shortcut labels to look like this everywhere, let me know. but if shortcuts should only look like that in menus, and it isn't appropriate for the shortcuts dialog and debug labels and stuff, I'll put it off until we actually have menu shortcut labels lol

### parsing

* I added a 'STATIC' formula type. it just spits out the same static text, every time, and repeated n times if you need it
* added a little help documentation for the new STATIC formula type; the edit panel links to it like for the other formulae
* if your parsing test panel gets something that doesn't seem to be html or json, it no longer puts the goofy quote marks around it

### boring code cleanup

* did some misc refactoring in the page close testing code because the method names were whack
* cleaned some sidebar and autocomplete interactions to work with 'tag context' instead of 'tag service key', which means these guys are now sending a richer object with more tag display info in it
* cleaned up some duplicate variable handling all through the sidebar stuff
* a bunch of redundant location context emit spam from the sidebar is deleted. I don't think this will break any weird thumbnail grid or previuw canvas location stuff , but we'll see in the edge cases
* cleaned up how query autocomplete dropdowns and sidebar panels were communicating search state changes
* ratings that fail to draw for whatever reason now do so more safely
* removed code that did the old and canvas-desyncing media object update routine

## [Version 610](https://github.com/hydrusnetwork/hydrus/releases/tag/v610)

### misc

* files with an average colour with less than 3% saturation in the HSL colour space (i.e. completely greyscale, or otherwise averaging to grey) are now propagated to the end of the Hue sort, whether red or purple first
* hitting ctrl+c on a taglist with no selected items now copies all items
* updated the system predicate parser so it can read 'number of pixels'. previously, it could only handle 'num pixels'. this means you can copy/paste a 'system:number of pixels' pred back into the autocomplete and it should all work
* fixed a problem with `system:num file relationships - (test) "not related/false positive"`, which was only every returning the results of one not-related alternates group, rather than all that matched the test
* made some 'click below to copy to clipboard' menu labels bold
* the client now says 'tag mappings' explicitly, rather than 'mappings', in a bunch of UI labels like shortcut action descriptions

### notes

* the 'start editing notes with the text cursor at the end' setting under `options->notes` now applies to all notes in an 'edit notes' panel with multiple notes
* clicking a new note tab in 'edit notes' now immediately focuses the underlying note so you can start typing
* if you have made changes, the 'edit notes' panel now confirms if you want to cancel. let me know if this produces false positives--there's some 'note cleaning' stuff I don't account for

### file viewing statistics

* the new 'client api' views are now integrated into the UI for search, sort, and view
* the way file viewing stats are presented in the media right-click menu is simplified. the stuff under `options->file viewing statistics` is down from five different options to two (show the views summed with a stack of the components in a submenu, or just show the stack of separate count types up front), and there's a new checkbox list with media, preview, and client api views so you can select what you want to see
* sorting files by media views now obeys the above 'what you want to see' setting, summing the respective values. previously it just did media views
* `system:file viewing statistics` now allows for selection of 'client api views'
* `system:file viewing statistics` now renders itself in the form `system:views/viewtime in (domains) (operator) (value)`, where 'domains' is a comma-separated combination of `media`, `preview` and `client api`. previously they were `system:media/preview/all views/viewtime (operator) (value)`
* if domains is left blank, I substitute the above 'what you want to see' option, so you can now just type `system:views > 5` and you'll get something reasonable
* the old forms still parse but are unchanged and won't support client api
* added some new unit tests for this
* as a side thing, I did the same pixel-perfect-height update that I did for multi-column lists to most of my checkbox lists across the program, including for canvas view selection around here. they just fit better now
* I overhauled some file viewing stats db search code. the predicate still holds some stupid variables that I'll want to rework one day, but the meat of the db search code is now ok

### advanced parsing logic and overhaul

* subsidiary page parsers have a new 'sort posts by source time' checkbox, default off, which sorts what this subsidiary parser chops up according to any parsed source time, newest first. use this if you are, obviously, parsing things that each have a source time you'd like to sort by but which come in some other order, e.g. you have two individually sorted pages of results in one document and you'd like to interleave them
* wrote up proper objects to hold 'parsable content description', 'parsed content', and 'parsed post'. previously this was a big mess of tuples upon tuples and 'all parse results' vs 'whole page parse results' semantic sludge
* refactored `ClientParsing` to a new `parsing` module, added `ClientParsingResults` to handle the new objects, and split off old file lookup stuff to `ClientParsingLegacy`
* all parsers now use the new objects to report what content they can parse
* all parsers now use the new objects all along the parsing pipeline! the whole thing is done and much nicer
* deleted a ton of old bad code that was navigating this before
* deleted some old bytes/str error-handling back from the python 2 days
* when a gallery url is worked, it now reports fully, in the gallery log note column, how many sub-gallery urls were parsed, and how many were previously hit this run, and how many next gallery page urls were parsed, and how many were previously hit this run, and whether a url class extrapolated next gallery page url was generated, and, the same deal, if it was previously hit this run. previously, this guy mostly just reported the latest interesting thing to happen--now it is comprehensive
* fixed an odd bug where the gallery worker could add a sub-gallery urls that pointed to the API redirected URL that created it
* fixed an odd bug where the gallery worker could skip the 'seen this url before in this parsing run?' check for an auto-generated 'next page' gallery url fallback step
* cleaned up the gallery url 'work' code significantly
* fixed a note parsing issue in the downloader where note texts were not always being cleaned on parse
* overhauled the subsidiary parser test panel to use the actual code as-in the subsidiary parser, rather than a facsimile
* got the page parser and subsidiary page parser test panels to recognise empty input rather than outputting errors on failed conversions of the empty string lol
* all the 'raw data'/'post conversion'/'post separation' tabs in the parser test UI now show up to 64KB of data. previously, the latter two were still capped to 1KBs
* fixed some bad layout in the edit subsidiary page parser panel
* cleaned up some lazy variable names in the subsidiary page parser code
* cleaned up how subsidiary page parsers initialise their edit panel
* fixed a layout issue in the 'edit login step' panel where there were now two nested 'content parsers' static boxes

### some subscription logic and UI

* cleaned some of the subscription gallery search logic, especially the 'have we caught up to where we were despite the (large) gallery page not being finished yet?' test, which has a couple of false positive edge cases solved
* cleaned some duplicate code out of here
* subscription queries now have an editable 'compaction number', which governs how small they should trim themselves to. this was previously fixed at 250 items, but is now changeable for advanced debugging purposes under the edit subscription query panel
* if you have a very large periodic file limit or the site produces a huge gallery page, the compaction number will now increase dynamically to ensure the subscription maintains a healthy cache of urls to consult for the size of our job
* the edit subscription query panel gets a layout overhaul. the stack of widgets is now grouped into boxes
* the `options->downloading` page now specifies that the two checker options buttons are for the subscription/watcher _defaults_
* as a side thing, watcher check logs now record up to 500 entries before removing old items. used to be 100

### weird thing

* the tag autocomplete searches across the program that manage a `read/search` context (as opposed to a `write/edit` one), will now pass a keyboard copy event to their top list if there is no selected text in the text input and there are no results in the search list below. actually getting into this situation is tricky, but this is really prep for a future overhaul of the write context, where no results is the default situation on an empty input but which cannot actually talk to its top list yet

## [Version 609](https://github.com/hydrusnetwork/hydrus/releases/tag/v609)

### macOS app now comes in a zip

* the macos-13 runner that we recently moved to has been taking way too long to build the App DMG. under ideal conditions it will take ~6 minutes, but sometimes it will be 45+. this is an unfortunate and widespread issue without an excellent fix
* thus, the macOS App is now distributed in a zip (that takes about 30 seconds to build and is the same size as the DMG lol)
* unfortunately this means we can't have the Applications shortcut or the ReadMe; you'll be double-clicking the zip to extract the App, and then dragging it to your Applications yourself
* I have updated the 'getting started - installing' guide with the 'allow unsigned apps' stuff from the ReadMe
* I am increasingly of the mind that macOS users should consider running from source. the App is built for intel chipsets, so if you are on Silicon, you definitely should: https://hydrusnetwork.github.io/hydrus/running_from_source.html

### misc

* INFO: reducing the 'too many events' mpv error-handling hook worked well. if you saw a bunch of these in the past few weeks, these were almost certainly false-positives. the files were likely not broken, they were just taxing your computer for a bit and the error was firing accidentally. if you set up a special workflow to isolate or deal with these files, please undo it
* the new 'group by namespace (user)' list widget under `options->sort/collect` now accepts `:` to represent 'all other namespaced tags' if you would like to put them somewhere specific
* fixed a typo in the new duplicate files 'has duration' comparison strings. it said 'the other has duration, the other does not' when the current file had no duration
* the score for duration now scales from 1 to 50 depending on how much longer a vid is than the other on millisecond longer = 1, twice as long = 50 (cap). this is all still just hardcoded stuff I'm playing around with, and I expect it to formalise to something completely user-customisable as the tools from duplicates auto-resolution firm up
* added a little section to 'help my db is broke.txt' talking about the sqlite3 terminal and how to get it on non-Windows

### colour sorting

* after talking with some users, and learning that our blurhash provides the average colour of image thumbnails, I went bananas and added five new 'average colour' file sorts--
* `lightness` - sorts light-to-dark in the Lab colourspace
* `hue` - sorts the standard red-orange-yellow-green-cyan-blue-purple colourwheel/rainbow in the HSL colourspace
* `balance - blue-yellow` - sorts blue-yellow chromaticity in the Lab colourspace
* `balance - green-red` - sorts green-red chromaticity in the Lab colourspace
* `chromatic magnitude` - sorts the combined chroma value, which is basically 'is it grey or colourful' in the Lab colourspace
* this works on any file with a thumbnail!
* they all work with system:limit, also!
* and the Client API--new `file_sort_type` definitions are in the Client API reference
* I am extremely pleased with how this all worked out. there are some weird results because it is average colour, rather, say, than a carefully selected 'primary colour', and I think it could do with some more work, to perhaps, for instance, push remarkably grey images to the bottom of Hue sorts, but this really works and it simply looks cool to do and then scroll through. it is a good base and proof of concept for my original plan to make colour histograms for files and distinguish between images that are muddy all over versus white and red. let me know where this succeeds and fails, and we'll see what improvements we can think of

### janitor stuff

* in the petition processing page, when you process a petition, either the normal way or via the mass approve/deny buttons, the 'currently highlighted petition' moves to _after_ the current one (or the next available one if you process multiple at once). previously this was resetting to the 0 position on every mass approve/deny. it should ripple down a bit more naturally now
* when you set to apply multiple petitions at once, the pertinent list rows now instantly to show 'uploading...' status
* I wrote a whack of test code that loads up and processes fake petitions for the petition page, so I can test these workflows much easier now
* I fixed the 'modify account that uploaded this tag' for tags that include the '+' character. sorry for the long-time trouble--it was a stupid GET args parsing issue I missed in early code

### boring code cleanup

* broke up the 'ManagementPanels' monolith, refactoring it to a bunch of smaller files more under the 'Sidebar' name
* renamed the ambiguous 'management type' to 'page type', and 'management panel' to 'sidebar', and 'management controller' to 'page manager' across the program
* cleaned up some old static superclass calls in here to `super()`
* brushed up the code generally around here, ditching some bad ideas and scope design
* fixed a small instability trigger in the main file query routine
* cleaned up some more inartful controller scope code in page and downloader UI
* cleaned some ugly `QLineEdit` initialisations across the program
* updated the server requirements.txt, which isn't used for anything but a reference, to use the newer OpenCV; I just forgot to update it a while ago

### pyproject.toml

* a user made a 'pyproject.toml' file. this is basically a cleverer requirements.txt that allows for better dependency options. I learned a bit about these files this week and I quite like them. pip can handle them too, so this would be one way to simplify my setup_venv scripts to a single call and allow users to set up simple custom automated situations
* so, just for now, there's a pyproject.toml in the base directory. if you use `uv`, feel free to play around with it. I will manually keep it updated and version-synced to our requirements txts, and I wouldn't be surprised if I switch to it as the master soon. I'm going to do some other work and research and testing first though

### duplicates auto-resolution

* I did a little work on the daemon, but I didn't feel great about it tbh. I know roughly the various things it needs to do, but I'm not firm on what should be the correct orientation of everything. I'll keep at it, and I may do more UI so I have better feedback while I am doing final integration here

## [Version 608](https://github.com/hydrusnetwork/hydrus/releases/tag/v608)

### mpv

* my ill-fated mpv-choking error hook, which tries to catch when MPV is having a 100% CPU event and unloads the file in a big fuss, and which has unfortunately caused a whole bunch of false positives, is now flipped on its head. instead of catching all instances of the log output and trying to exclude 'oh that's fine' cases, the hook now precisely targets files that go irrevocably 100% CPU on loop, specifically by recognising files that reload too frequently in one second for their duration (e.g. a normal vid looping twenty times in one second). mpv will be back to being juddery sometimes, but whatever, that's better than what I was doing
* the new 'DEBUG CAREFUL: Allow "too many events queued" files' checkbox no longer does anything and is removed
* also, the mpv emergency dump-out code is back to being per mpv player. previously it would unload all players the client was managing
* my mpv player now uses a little less CPU when mouse-drag-seeking

### misc

* I am changing the tag sort logic such that if you group by namespace, the namespace order stays as it is, no matter the underling asc/desc order of the actual sort. in simple english, this means that creator tags stay at the top whether you say 'most first' or 'fewest first'. we had success with the 'namespace (user)' just recently, and after talking about it with some guys, I think I agree that doing a full reverse of the whole list is not useful, and it isn't, fundamentally, what grouping is. let's try it like this, see how we like it
* the various multi-column lists across the program, which generally set their minimum and initial height by a 'num rows' suggestion, now do so pixel-perfect in most cases, no matter the style (it was previously ok on windowsvista, with a bit of fuzzy padding, but on Fusion it was either too tall or short due to font height estimate stuff). the downloader and watcher lists, which dynamically size according to contents, also do so unerringly. I find this very slightly eerie tbh so I might add a couple pixels of whitespace on the end so your brain knows there isn't more to scroll. let's try it like this for a few weeks and see how it feels
* added `--pause_network_traffic` launch parameter to the client, which hits `network->pause->all new network traffic` before the network engine initialises, to help debug when pending subscriptions or initial-session downloaders go crazy
* in 'manage tag siblings/parents', if you import from a clipboard/txt that includes a `a->a` loop-pair, the dialog now yells at you
* as a little hack, I added ctrl+shift+c to the taglist to say 'copy tags with parents' the default ctrl+c does not include the parents
* removed a duplicate and blank entry for 'EXPERIMENTAL: Image path for thumbnail panel...' in `options->thumbnails`, whoops
* I added a little safety code to the import folder, trying to catch a possible infinite loop we have seen. import folders now also take regular short breaks to give other threads like garbage collection a guaranteed moment to step in
* fixed a bad buffer truncation calculation in the native video viewer

### build/jpeg-xl stuff

* in `help->about`, moved the Jpeg-XL and HEIF(/AVIF) support lines to the second tab, and together
* if your client does not have Jpeg-XL support, the import error is now stated when you hit `help->about`. **if you are on macOS, you probably do not have Jpeg-XL support yet**, and the solution, whether on App or from source, is to run `brew install jpeg-xl` in the terminal, which is now also said in this message (issue #1670)
* added a small note to the installing help docs to say Apple Silicon users should consider running from source. the App is Intel for the time being, and running from source will give you a much more pleasant experience all around

### boring code cleanup

* refactored the `ProcessContentUpdates` megacall and its friends to a new 'content updates' database module
* refactored the duplicates file search stuff down to a new database module
* and refactored the 'set duplicates' call down to a new database module
* about 110KB of code is thus cleared out of the `ClientDB` monolith, which is down to 500KB, and we are ready to plug the duplicates auto-resolution module in as it now has scope on the various calls it needs
* fleshed out the duplicates db module's master id definitions
* cleaned up how I refer to file duration across the program. all the convenient-to-change duration or frame durations have a unified nomenclature and always say if they are in seconds or milliseconds

### duplicates auto-resolution

* the final difficult duplicates auto-resolution database problem (fast incremental duplicate pairs search) is solved. outside of at-scale testing and final integration, the database side of this is now complete. now just need to to figure out a daemon and a preview panel

## [Version 607](https://github.com/hydrusnetwork/hydrus/releases/tag/v607)

### misc

* jpeg-xl images are now fully supported! jpeg-xl is one of the contenders for 'what format do we use next?', and I think a pretty good one. it is basically jpeg but it can handle more colour depth/HDR, transparency, and optional lossless encoding, all while saving about 40% equivalent filesize to a jpeg/png. I understand it can also do animation (although we don't add that today), making it a potential 'capabilities superset' of gif as well. jpeg-xl is not well supported yet, but I hope that as more programs add support we'll see that change, and hydrus does its part today. thanks to the users who navigated this
* added some boxes to `options->thumbnails` to give it some better layout and grouping
* the 'show the media viewer top hover text in the status bar when one thumb is selected' option now defaults to True. it was a mistake to turn this off by default, and all users will be switched to True on update. the checkbox remains in `options->thumbnails` if you want to turn it off
* added 'Give thumbnail ratings a flat background' to `options->thumbnails` to turn off if you prefer to just have the ratings without the rectangle backing I added last week
* the new 'namespace grouping sort' sorted text list in `options->sort/collect` now has a paste button if you need to enter a ton of them
* a new checkbox under `options->importing` let's you stop the program switching to the destination download page whenever you drag and drop a URL on the program. this was personally driving me nuts
* when you right-click a selection of predicates that includes OR preds, the 'copy' submenu now includes an option to copy texts with collapse ORs, which renders them like "a OR b OR c" in one line, rather than the separate rows
* the duplicate filter's "comparison statements" in the mid-right hover now show if one or both files have duration. I hacked this in simply for guys who are using external tools to get videos into the potential duplicate pairs queue, and I still want to completely rewrite this thing to a fully user-editable system once I have the tools matured in the duplicates auto-resolution work
* a safety limit that would force the status bar to stick to 'x files' instead of the more interesting and cpu-intensive 'x images/collections/whatever' is raised from 1,000 files to 100,000. let's see how it goes
* fixed a sometimes-error when showing different file presentations of watchers/gallery downloaders (when you right-click some and say `show files->blah`)
* the complicated pre-download file status logic that determines if a URL-mapping has untrustworthy neighbours now prints a little log message of what it discovered when it hits a positive. this thing runs a little quiet and I want to see if it is firing too often or is not quite checking what we want in difficult cases
* fixed a weird typo when unsetting the EXPERIMENTAL media viewer background bitmap thing in `options->thumbnails`

### MPV

* I did some work trying to handle the 'too many events queued' problems we've seen with mpv recently. I cleaned some code and reduced the overhead of my custom event handling, but I am generally convinced that some of the problems we've seen are due to 100% CPU bugs in various libmpv versions, particularly because I can set the 'loglevel' of mpv to 'no', for 'nothing at all', but the error still happens, suggesting there is probably no log-processing speed I can do on my end to fix this. I am leaving the emergency-dump-out code in place, but for this specific 'too many events queued' error it no longer adds that file to the 'never load again this boot' list--you can deselect the file and then reselect to try again (although it seems like the mpv player's event loop can be poisoned by the situation and lags a bit on next load). I have also seen the error occur at I believe the start of playback, but then I could load the file fine another time with the same dll, which suggests the log stuff can pile up due to a brief busy period in thread scheduling or whatever. so, there is more to do here--perhaps a 'if we get the error persisting for more than two seconds' or something
* I did discover a different loop flag I could set for mpv that fixes one of the reliable problems--setting 'loop-playlist' rather than 'loop-file', which seems to force the file to reload and avoids the EOF rewind bug that mpv is running into. if you get the error on the first loop of a file, try hitting the new checkbox under `options->media playback` and we'll see how it all goes
* I also just bit the bullet and added a DEBUG option, also to `options->media playback`, to disable the new 'too many events queued' dump-out hook. if you hit many false-positives and are feeling brave, try turning it off, but you may have to deal with some 100% CPU situations

### viewtimes are now in ms

* the filetime viewing stats system now records total viewtime in ms (previously it only had 'second' resolution). this doesn't matter all that much, but all the little deltas it adds are now 'viewed file for 3.2 seconds' rather than always rounding to the nearest integer
* the settings under `options->file viewing statistics` are now full 'time delta' widgets that support ms, so you can say 'viewing a file for at least 2.5 seconds counts as a view' rather, again, than having to deal with full integers all the time
* system:viewtime now supports milliseconds input for viewtime ranges
* mr bones now reports a ms-precise (float) total viewtime (e.g. 3.456s) for the current search

### client api

* the client api can now see and edit file viewtime statistics!
* `/get_files/file_metadata` now states the file viewtime statistics (last viewed time, total views, total viewtime for the different viewer types) for each file
* file viewtime statistics has a new 'client api viewer' enum, separate from the existing 'media viewer' and 'preview viewer' record, if you'd like to do your own thing. I've hacked this a bit, and it doesn't show in the normal Client UI yet, nor can you search on it via `system:file viewing statistics`. the current options on how to show viewtime (`options->file viewing statistics`) are frankly crazy, so I think probably we'll want to go to a list of simpler checkboxes or something and stop trying to be clever
* the new `/edit_times/increment_file_viewtime`, which needs the existing 'edit times' permission, lets you add views and viewtime and set the latest view timestamp
* the new `/edit_times/set_file_viewtime`, which needs the existing 'edit times' permission, lets you set fixed values (i.e. if you are migrating from one client to another)
* I have not added a delete/clear call here yet. if you would like to do this, let me know what you would like. the client only has 'clear everything for this file' and 'clear all records completely', but I expect we'd want the ability to clear by view type?
* wrote help for this
* wrote unit tests for this
* client api version is now 78
* the rich version of `/get_files/file_metadata` is now providing a lot of personal user metadata like inbox, ratings, local tags, and now viewtime statistics, making the 'just share some files with a friend' scenario less attractive. I was considering adding a new 'edit file viewtimes' permission today that would allow the edit and also dynamically show/hide the new viewtimes, but I think it would be better if I make a _read_ permission in the _ouvre_ of 'can see user file metadata', which, if absent, will mean callers can only ask for the basic file information. this permission may apply in other places, and the whole client api permissions system could do with a pass and likely some KISS. let me know what you think!

### boring cleanup

* cleaned up how some thumbnail-focus-delegation happens on new file focuses
* cleaned some viewtime pipeline code generally
* fixed the API help json example requests for `set_time`, which didn't have `file_id` stuff
* replaced all my 'convert ms time to s time, but a float, oh except I guess when it is null, don't forget bro' code with a single and safer unified call across the program
* cleaned up some agnostic 's or ms' duration calls, but there's plenty more to do

### build updates

* last week's 'future build' went well, so I am folding the changes into the normal build. users who run from source may like to run their `setup_venv` script again today, and users who would like to run from source but only have python 3.13 now have a route to run hydrus
* details--
* PySide6 (Qt) is updated from `6.6.3.1` to `6.7.3` (test version is now `6.8.1.1`, which source users on Python 3.13 can run)
* on macOS, PyQt6 (Qt) is updated from `6.6.0` to `6.7.1`
* OpenCV (image stuff) is updated from `4.8.1.78` to `4.10.0.84`, which lets us update numpy (test version is now `4.11.0.86`)
* numpy is switched from `<2.0.0` to `>=2.0.0`. this adds Python 3.13 support to hydrus for source users
* pillow-jxl-plugin is added, and thereby we have Jpeg-XL support (thanks to some users for navigating this!)
* the python mpv package is updated from `1.0.6` to `1.0.7` (test verison stays at `1.0.7`; there is nothing new)
* twisted (the networking engine that runs the hydrus server and client api) now includes better TLS and http2 support
* some import hacks that helped old PyInstaller navigate numpy and OpenCV bundling are removed
