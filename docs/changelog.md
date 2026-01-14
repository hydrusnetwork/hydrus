---
title: Changelog
---

# changelog

!!! note
    This is the new changelog, only the most recent builds. For all versions, see the [old changelog](old_changelog.html).

## [Version 655](https://github.com/hydrusnetwork/hydrus/releases/tag/v655)

### misc

* for all the normal page sidebars, the sections above the taglist (e.g. 'search' on a search page, or 'gallery downloader' and 'highlighted query' on a gallery download page) are now collapsible (there's a little up/down arrow button in the corner). if you want to do some taglist work, you can now make it really big. this is just a hacky test though, so let me know how it feels
* the 'eye' icon in the media viewer now has 'always start new media viewers always on top' (which works nice generally) and 'always start new media viewers without titlebar/frame' (which is a little flickery since I schedule it to happen 100ms after window init because of technical gubbins). neither plays very well with start-fullscreen mode. I also reworded the titlebar option logical grammar from 'show titlebar (default on)' to 'hide titlebar/frame (default off)'
* the 'pause network/subs' menu items in the system tray icon are now checkbox items. the ugly 'unpause x' grammar is gone!
* if you do not have a file, the file info lines that appear in the thumbnail flyout menu and the main gui status, which normally say stuff like 'imported 3 days ago' now explicitly say "you do not have this file, (but you did once|but your client has heard a bit about it|and you have never had it)". I hope this will forestall some confusion these advanced media results cause (usually under a 'all known files' search)
* the unhelpful and incorrect 'archived: unknown time' statement no longer appears for non-local files
* if a site delivers `451: Unavailable For Legal Reasons`, the file and gallery download objects now catch this and assign an 'ignored' state with an appropriate note. previously this was counting as an ugly uncaught error and causing subs to break and so on (this caused my 'do not use NGUGs here' 'edit subscription' warning label last week). if you have been hit by this (seems like danbooru is doing it?), I don't know if it is because of your region or certain queries (e.g. 'do not post' artists); let me know how the workflow is with these results now being ignored--maybe we want this to be an outright errorthat will auto-pause subs and such, just with the now-nicer error description? I've been thinking about making subs cleverer about region-based captcha blocks, recognising that this is a temporary block that should cause hydrus to stop talking to the domain entirely, but not considering it an error _per se_ and backing out of the current job non-destructively so it can try resuming where it left off again later, so if this is part of that, we'll want to throw it in the mix

### Client API

* with thanks to a user for the skeleton, I fleshed out and added `/manage_pages/get_media_viewers` to the Client API. this thing fetches all the current open media viewers, tells you an id and type for each, and says what media is currently in view. this also clears issue #1583
* wrote a (bad) unit test for this and some documentation
* Client API version is now 84

### Client API deprecation

* I am formalising my Client API deprecation schedule since I have been procrastinating on this cleanup yet don't want to suddenly delete something mysteriously two years after the fact
* if you send `hide_service_keys_tags=false` to a `file_metadata` Client API call, the user now gets a `FutureWarning` deprecation log entry. the behaviour this parameter supports will be deleted on v668 (three months from now)
* same for the `set_user_agent` command. you'll get a `FutureWarning` if a script calls it, and it will be deleted in v668
* `hide_x=true` is ugly logic, so we'll go with `use_deprecated_x=false` default going forward
* I am going to add a `use_deprecated_services_structure=false` default to the `services` call in v668, to hide the old service structure. it will similarly get a warning and a three month timeout, to be deleted in v681

### boring file storage cleanup

* an early 'umbrella' experiment for dynamic file storage prefix-length is removed and some validity checking is simplified
* in prep for the move to a storage system with three-character prefix (4096 folders), moved a bunch of prefix-handling to a central location and made it length-agnostic
* KISSed some of this code. it is still a bit of a mess though tbh
* wrote a method to 'granularise' a file storage structure, moving a base location from subfolders in the form '/f83' to '/f83/0' - '/f83/f', with file migration and handling weird files and stuff. when we move to three-character storage, we'll not only be granularising our main storage, but we'll want to do this one-time manually on our backups as well

### other boring stuff

* the 'edit default duplicate metadata merge options' button in the duplicates page is shuffled down to the 'duplicate filter' box
* fixed a quiet layout sizing warning in the petition processing page when the checkboxlists have no content
* added a note to 'help my db is broke.txt' about a clone crashing

### future build

* I am making another future build this week. This is a special build with new libraries that I would like advanced users to test out so I know they are safe to fold into the normal release.
* in the release post, I will link to this alternate build. if you are experienced and would like to help me, please check it out
* special notes for this time: nothing crazy, we'll see if the new Qt kicks up a fuss anywhere strange
* the specific changes this week are--
* `requests` `2.32.4` to `2.32.5`
* `mpv` (the python wrapper that talks to the dll) `1.0.7` to `1.0.8`
* `PySide6` (Qt) normal `6.8.3` to `6.9.3`
* `PySide6` (Qt) test `6.9.3` to `6.10.1`

## [Version 654](https://github.com/hydrusnetwork/hydrus/releases/tag/v654)

### command palette

* reorganised the command palette options panel and updated how the character search threshold works. you can now say 'show all my x initially' for a particular search result type and then set a character limit for the general searches. the default and min value for the character search threshold is now 1

### slideshow

* the slideshow menu in the media viewer has been shuffled a bit to tuck everything together
* the slideshow menu now also appears in the top hover of the normal 'browser' media viewer, in a new icon button beside the 'move randomly' button
* the sildeshow menu now has a 'slideshows move randomly' option. this thing is a global setting, mostly a test. let me know how it works out

### misc

* the manage subscription dialog now nags you with red text if you set a downloader that appears to fetch from multiple sites (i.e. it is an NGUG that has multiple domains in its example urls). although it sounds temptingly convenient to set up a sub with a multi-site NGUG, they don't work so great like this, so the panel now says so and tells you what to do instead
* added a `When finishing archive/delete filtering, delay activation of multiple deletion choice buttons` checkbox, default True, to `options->files and trash`, so you can now disable the 1.2 second delay on the delete/commit buttons when there are multiple deletion choices
* made new svg icons for 'image', (which turns up when hydrus can't find a thumb for an image file), 'images' which turns up in the command palette as a 'media' proxy for media menu results, and the new 'slideshow' icon button. I like how these look at high res, but the smaller ones look bleh tbh. we'll have a review of all my new svgs when I finally add icon button sizing options and boost the default up a bit
* `options->media viewer` now has split up mouse and seek bar settings. the seek bar panel has a new `Seek bar full-height pop-in requires window focus` checkbox, which is now default **True**
* fixed svg resolution fetching (and probably all sorts of related svg gubbins) in PyQt6 (this is an alternate version of Qt some source users may be running)

### boring and cleanup

* overhauled how the command palette does some search string handling and cleaned up a couple of logic things like whitespace no longer counts as a new char, etc..
* the code behind the slideshow is all cleaner and decoupled application command stuff
* I went through and renamed some 'scanbar' labels to the more canonical 'seek bar'
* the 'eye' icon button in the media viewer top hover is recollected into window/hovers/rendering submenu categories
* fixed the vacuum command to no longer check the temp dir for free space in the lower-db call--the newer 'vacuum into' command we use no longer needs a temp copy
* might have fixed a bad 'Go!' confirmation dialog string generation in `migrate tags` that hits users for whom Mercury is in retrograde
* improved the error handling for when my new async subprocess reader tries to read from a process that terminates early
* fixed some unit test 'call after' job scheduling stuff with the same anti-deadlock handling I added to the main client a while ago

### admin and docs

* created a hydrus_dev@proton.me email address and added it to all my contact lists. please feel free to email me there if you prefer--I'll check it as often as my gmail
* to stop new users missing it, the 'Wayland' warning box in the Linux install and source help now starts uncollapsed
* added a note about `libxkbcommon` for X11 support on Fedora too
* wrote a 'help I had a file identifier missing error.txt' document for the db dir to handle the 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa34bf0b9abf7683e3955781212d0d1899' emergency hash-recovery situation

## [Version 653](https://github.com/hydrusnetwork/hydrus/releases/tag/v653)

### misc

* I hacked a simple date range (x axis) into the file history chart. it is clunky, but if you want to zoom in on one year, it'll work. this persists through search changes, and there's a 'refit x axis' button to recalc for the current data in view
* reworked the naming and layout of the checkbox list in `options->media viewer hovers`
* `options->media viewer hovers` and the top hover eye icon get a new `Hover-window pop-in requires window focus`, default on
* `options->media viewer hovers` and the top hover eye icon get a new `Pop-in notes (right) hover window on mouseover`, default on, to handle the notes hover window
* also added the new 'pin the duplicates filter hover window' checkbox to these guys (it is also still in the cog menu of the hover itself)
* the `When finishing filtering, always delete from all possible domains` option is now simpler and more reliable. it had some old logic from the days when archive/delete allowed trashed files and sometimes not activate if there _were_ multiple domains (#1926)
* the archive/delete commit dialog when the above option is _off_ is simplified and, if there _are_ multiple domains to delete from, always puts 'combined local file domains', which now has a clearer label, at the top
* `system:duration` parsing now supports hours and minutes, and some funky stuff like '26000ms' works better (#1924)
* the hydrus network engine has two new global http headers: `Accept: image/jpeg,image/png,image/*;q=0.9,*/*;q=0.8`, which preferences jpegs and pngs over webp, and `Cache-Control: no-transform`, which asks CDNs not to deliver "optimised" versions of files (often not honoured, though). all users who don't have a global header with those names already in place will get them on update. if you prefer something else, hit `network->data->manage http headers` to edit!
* fixed the 'refresh all pages on current page of pages' shortcut action, which was accidentally nullified by a recent rewrite
* fixed an issue with clientside services not deleting properly when editing services on a server and deleting more than one service at once

### boring cleanup

* the file history chart can now take new data and will regen its internal series and axes and stuff. previously I swapped in a whole new chart widget on every new search. also cleaned up the layout of the wider panel here
* all `Typing.Optional` across the program (~300 instances I think) are replaced with `x | None`, which is python 3.10+ only. turns out we already had some of these, so no big worries, I hope, about lingering 3.9 users
* all `Typing.Union` across the program (~50 instances) is similarly replaced
* clarified some 'this message only shows one time per program boot' messages

## [Version 652](https://github.com/hydrusnetwork/hydrus/releases/tag/v652)

### misc

* the advanced rating system predicate (the new one that lets you do all/any/only) is now fully parsable, so you can type `system:any rating rated`, and it should work. if you need to stack up multiple specific rating services, split them by commas for something like `system:only rating service 1, rating service 2 (amongst like/dislike ratings) rated`. against all probability, I think I support everything here
* `options->command palette` now lets you set a number of characters to type before any results come in. default is 0
* fixed some selection issues with the command palette. I just cleaned up the select logic a bunch and fixed things like: if you select something with arrow keys and then click on the text box and start selecting again, the old selected guy is now properly deselected; scrolling to the topmost item via a wraparound or home now ensures any non-selectable title is in view; page up from text input now jumps up a page from bottom rather than just selecting the bottommost item; page up/down events that land on a title now spill over to the next selectable item and are a bit faster if you have like 500 results in the background
* I cleared up some initial UI lag when when you highlight a very large downloader or watcher (say 5,000+ files) with presentation options that care about inbox status (requiring a db hit). the db hit now happens on the worker thread, not the Qt setup phase. the popup window showing progress now appears if this job takes longer than two seconds for the whole thing (previously three seconds for the results building step). let me know how it feels
* when hydrus calls other programs and wants text back, it now forgives invalid utf-8 with the replacement character �. previously it strictly raised an error, and this broke imports of mp4s and so on that had damaged utf-8 in their metadata description (which ffmpeg faithfully passes along) etc..

### default downloaders

* updated the danbooru gallery parser to not get a load of gumpf links if you have 'show scores' set on in your account/cookies and sync that to hydrus

### boring cleanup

* all my custom `paintEvents` across the program now have completely safe exception handling and unified reporting in all cases. if there is an exception, the user is notified once per boot about what is happening, why it is important (unhandled exceptions in paint events are crash-city), and to please send the trace on to me
* some 'media result' tag access is now a touch more thread-safe. this effects the client api `add_tags` and `file_metadata` calls. I'm not sure if this will solve some `add_tags` crashes we've seen, but it is the only candidate I can see
* I've cleaned up the system predicate parsing system a bit. this thing started out as a clever neat routine, and I and others have hacked at it so many times for new preds that it is a mess. I've worked on making the pipeline less brittle, with a common workspace shared by all methods rather than fiddly params. much of the old stuff is still in there, but I've been able to undo some hacks and feel overall good about the direction. I've slowly been moving my basic system preds to a new unified 'numbertest' object, and the next step here is to integrate this into the parsing so we can finally specify absolute and percentage uncertainty, which atm is locked at +/-15%
* the hacks cleaned up are: an uppercase/lowercase thing for url class and regex parsing; a non-consuming operator thing to make non-sha256 system:hash preds parse correct; and some value/operator juggling to handle the conversion to `taller than|=|wider than 1:1` for 'ratio is portrait/square/landscape'
* fixed an issue with the newer ffmpeg error handling when your ffmpeg gives no stderr on a file parse
* cleaned up some ffmpeg error exception handling to be nicer to linters
* removed some ancient python 3.6 and 3.7 compatibility code in the subprocess stuff
* when the initial url parser fails to figure out what is going on with an incoming URL, the exception now states the URL text that caused the failure
* fixed up some client api unit tests that were doing dodgy media result prep
* fixed a checker options unit test that I accidentally broke last week with a last-minute change
* updated the versions of the github actions in the runner workflows to be ready for Node24. I think that migration triggers on Github around April 2026, so we are way early. it looks like some of the docker stuff isn't 24 compat yet, so there may be another round of this early next year
* deleted an old duplicate of the docker.yml workflow in 'build_files' that had fallen behind the master

## [Version 651](https://github.com/hydrusnetwork/hydrus/releases/tag/v651)

### user submission

* the user who has been sending in UI features has some more--
* the options dialog now has a search bar!! you type something in, and it'll present any text strings in the whole options dialog that match. you select one and it'll take you to the associated page and highlight the text. it is still experimental and because the underlying strings are a little jank, sometimes the results are weird too, but it is pretty cool and a clever way to get this functionality without a whole dialog rewrite, as I was expecting to do
* the regular command palette now supports smart wraparound so you can press 'up' after typing something to get to the bottom of the list
* it also supports page up/down/home/end for fast results navigation! I fixed a couple things with page up/down and made home/page up terminate on the top result, rather than the text entry--let me know if anything feels/renders wrong
* a new checkbox in `options->command palette`, default on, makes favourite search selections in the command palette open a new page rather than populating the current
* the command palette now highlights favourite search 'folder' name
* bug fixes for some recent menu search stuff and undo/redo search stuff

### duplicates auto-resolution launch

* this system is now v1.0 and ready for all users to use. I invite everyone who has done some duplicates work but has yet to touch auto-resolution to check out the updated help here https://hydrusnetwork.github.io/hydrus/advanced_duplicates_auto_resolution.html
* if you are interested but don't want to get into the details, there's a 'tl;dr:' section that tells you how to get set up in about a minute
* if you have yet to do any duplicates work at all in hydrus, I also updated the core dupes help here: https://hydrusnetwork.github.io/hydrus/duplicates.html

### misc

* the duplicates filter's right-hand hover window now has a 'this window is always visible' checkbox under the cog menu. turn it off, and it will only appear when your mouse is over it, like the other hover windows
* all 'checker options' in subscriptions and watchers now support sub-integer 'intended files per check' values. the spinner widget now changes in increments of 0.05 and can go as low as 0.25 (previously '1')
* videos that are rotated with file metadata 90 or -90 degrees in the ffmpeg metadata report now get the correct resolution in hydrus and will get the correct shape of video canvas (non-letterboxed) with mpv or the native renderer. I have not scheduled all videos for a metadata regen since these seem to be very rare, but if you see a video with a whack thumbnail and it renders in, say, a small landscape cutout within a portrait black box, while being fine in an external player, try hitting `manage->maintenance->regen file metadata` on it. it is still doesn't fix, send it to me please!
* an error of 'There are no playback devices available' in an 'ao/xxxxx' component from mpv now counts as 'crashy' in the emergency dump-out mpv error handler
* all `fatal` mpv errors are now caught by the emergency dump-out mpv error handler and assumed to be 'crashy'
* fixed a bug related to the new search history stuff that could raise an error if a search page were edited in some early initialisation states

### boring stuff

* added a new call to create new file search pages that uses the richer 'file search context' object. this allows the new 'load a favourite search from command palette' job to load the correct tag context. we still don't set the 'searching immediately' state correctly here, but it'd be nice to have one day
* when file maintenance changes a file's filetype or resolution, details are now printed to the log
* a safety throttle that stopped checker options checking too fast is relaxed to 'no faster than _one quarter_ of the time since the last hit'
* tweaked some layout stuff in the options dialog

### duplicates auto-resolution misc work, mostly boring

* gave the duplicates and duplicates auto-resolution help a full pass
* in the auto-resolution review actions window, the approve, deny, select-all, and both undo buttons will now enable/disable as their respective lists' selection status changes
* for clarity and unity, replaced some final instances of 'declined' with 'denied' in the auto-resolution system
* renamed 'both files match different searches' to 'the two files match different searches'
* the pause icon button is now a clear text button with 'pause/play'. when I figure out a nice icon or dynamic icon-switching button for pause/play, I'll put this back
* removed the 'this is being built' warning labels from the UI
* fixed some bad tooltips in duplicate hover window
* I put off a couple of features I had planned for launch, like having more modified time merge in duplicate metadata merge options, and a column in the preview's failed-test thumbnail pair list to say which comparator failed. I didn't want to rush these out; I can add thm later in normal work

## [Version 650](https://github.com/hydrusnetwork/hydrus/releases/tag/v650)

### misc

* I forgot to mention last week that the user who added a bunch of nice UI stuff also added file search page predicate changes to the main undo menu. if you accidentally remove some clever predicate, it _should_ be possible to bring it back now. undo is a tricky subject, but we're experimenting with some stuff
* fixed a logical typo in last week's better prefetching code where the media viewer was prefetching no further than the smaller of the prev/next directions. e.g. if you were set to prefetch 3 back and 5 forward, it would only fetch 3 back and 3 forward. well done to the user with no backwards prefetching who noticed this
* when subscriptions are set to process in alphabetical order, this is now smart/human alphabetical, such that, for instance, 'my sub 3' is now earlier than 'my sub 11'
* turned off some 0.5/2x size clamping in the `options->ratings` dialog for incdec ratings. it was a little confusing and sometimes made it seem that the dialog was not saving values correctly
* fixed a bad dialog title and some non-expanding UI layout in the new 'edit service specifier panel' (the thing I added for the clever new rating pred last week)
* I believe I have fixed a handful of file storage initialisation and/or migration issues that all stemmed from a file location storage path being stored in a Windows system with forward instead of back slashes (mostly a legacy issue). thanks to the user who worked with me on this
* install_dir/static has a new 'empty_client_files.7z' that just has an empty 'client_files' structure, 512 subfolders in fxx and txx format, to help ease some database maintenance jobs
* wrote 'help my media folders are broke.txt' for the db directory to directly talk about missing subfolders

### duplicates smart counting updates

* tl;dr: the duplicates system is less laggy and some annoying stuff is fixed
* in the panel that sets up a search for potential duplicate pairs (e.g. on duplicates page 'filtering' tab), the little 'x pairs searched; y match' text label now updates very fast to pair changes. previously, any time a new pair was added (e.g. right after an image is imported) or an existing pair removed (e.g. you confirm a pair are duplicates), the count was invalidated and it had to be redone; now, that widget receives clever specific info of '_this_ pair was added/deleted', and it sees if it cares about that and updates its counts or decides to search that new pair as needed. you can now leave the client open looking at a 'filtering' page while a bunch of imports are going on and it is no longer a refresh-fest
* this is universal to any pair change, no matter the cause (previously there were a couple of maintenance edge cases I'd missed)
* in a separate set of signals, any time a file moves in and out of any local file domain or 'combined local file domains', these update signals _also_ happen. so moving or deleting a file will cauise an instant count update where appropriate. the problems we had with 'if I delete one file of a pair manually, that count doesn't show up quickly' are solved
* the underlying search cache this tech relies on uses the same update-optimisations, so the slow 'initialising' step you'd see all around here now only happens on the first access

### duplicates auto-resolution smart counting updates

* tl;dr: you shouldn't see trashed stuff in auto-resolution any more and some annoying stuff is fixed
* auto-resolution rules are also hooked into this smarter signalling system. they also now only track the pairs that are in their search domain, so if you send one file of a pair to trash, the pair now disappears from the rule (if, for instance, it was sitting in the 'pending actions' queue, it now disappears). and, if you _vice versa_ import or migrate a file to a rule's file domain, any potential pairs that it comes with will be added to the rule, so rules that are set up to only work in one specific local file domain now operate more sensibly
* there's a new maintenance job under the auto-resolution cog icon button that resyncs all rules to their correct file domains. this routine will run on db update, so you'll likely see some deleted cruft cleared out of your 'denied' queues and so on
* when you change the location of an auto-resolution rule's search but nothing else, it no longer needs to re-search everything. it just adds new pairs for search and discards an excess it now has. just works a bit faster on this particular change
* when you do some semi-automatic auto-resolution 'pending actions' work in the duplicate filter, the pending/actioned/declined lists now refresh properly when you exit the filter after work done. because of the location filtering, deleting a file from a pair now correctly removes it from the pending actions queue!
* same deal for the preview panel, when editing a rule--if you open the list up in the filter and do work, the list will refresh on exiting the filter

### boring duplicates tech that makes this all work

* when potential duplicate pairs are added, deleted, deleted-by-group-dissolve, or completely cleared, the duplicates database module now broadcasts specific pubsubs for each change. its cache of initialised potential duplicate pair search spaces are also updated directly rather than being cleared for regen
* the potential duplicate id pair and distance object now stores a smarter internal mapping allowing for more types of search and filtering, and obviously now supports the above update routines, including delete stuff, which it couldn't do before. the merge routine of this guy, which is used in some clever multi-domain searches, now also correctly eliminates duplicate rows
* the internal mapping of this object now also updates on these changes, rather than needing regen every time
* the fragmentary potential duplicate pair search object can now eat these pubsubs and update its search space and 'remaining to search' stores
* the fragmentary search now tracks actual rows that hit, not just a count. when a potential pairs update comes through, the hit store is also updated!
* the potential pairs search panel listens for the pubsubs and updates its fragmentary search live
* the fragmentary search is now aware of being in a '1700 out of 1703 rows searched' situation, where there is just a little bit more to do. in this case, it'll run those last three nice and quick rather than lazily settling for an estimate. this obviously happens all the time with these new incremental updates
* deleted the old and blunter 'potential counts have changed' pubsub
* I plugged the file add/delete routines into this system and wrote a bunch of domain filtering code to quickly figure out pair-updates based on file migration, and I wrote some location context consideration logic to make sure every guy who cares about this stuff gets told at the appropriate point
* I overhauled the auto-resolution update signals to fit into this smarter system
* the db module that manages duplicate file info is now split into a 'storage' unit, which does filtering and id management, and an 'update' side, which does verbs and update signals. auto-resolution now has access to the storage to do its filtering gubbins
* cleaned up a bunch of code here
* fixed a logical error when a duplicate pairs count search is asked to estimate the final count before any searching has happened

## [Version 649](https://github.com/hydrusnetwork/hydrus/releases/tag/v649)

### big user submission

* a user has sent in a large set of command palette, page navigation, and rating updates--
* when you edit a rating service in `services->manage services`, there is now a live and interactable rating widget that updates to show your chosen shapes and colours!
* when you edit the rating sizes in `options->ratings`, there are similar live rating widgets that will dynamically resize to the widths and heights you choose!
* under `options->command palette`, you can now add your 'page history' to the initial results
* under `options->command palette`, you can now add your 'favourite searches' to the initial results! I love how this works
* you can also limit the number of search results, which appears to reduce command palette lag significantly on clients with many hundreds of pages
* and you can also re-order the results by their type
* under `pages->history`, you can now clear the history
* `options->gui pages` now allows you to limit the number of pages kept in the history
* the media viewer's zoom options menu has even more granular control over remembering zoom options with a new setting to allow updating the default settings by clicking the menu (rather than it being transient to that media viewer instance)
* there's also a "do not recenter media on window resize" option (allowing you to now turn this behaviour off), and in `options->media playback` too
* 'page of pages' now automatically put a ` ↓` suffix at the end of their name label. you can change the suffix or turn it off under `options->pages`,

### user client api

* the user also added `/get_service_rating_svg` to the Client API, which lets you pull the svg used for a rating. there is help for this
* I wrote a unit test for this
* Client API version is now 83

### misc

* every ffmpeg call we make now flags ffmpeg to fail on the first error. we encountered a not-fun issue a week ago when certain JpegXLs were putting ffmpeg into an infinite error loop on a 'is animated' pre-import test. this loop is now broken instantly, but if a similar issue comes up, all external process calls also now cancel out if they take longer than (usually) fifteen seconds. I am not sure how prevalent errors are in normal videos, so let me know if many new videos suddenly get no thumbnails or something. this might be something we eventually want to tune (issue #1912)
* the animated jxl test is re-activated
* I renamed the confusing 'all my files' to 'combined local file domains' for new users a couple weeks ago. nothing exploded, so all existing users are being renamed today
* across the program, the places where you locally store files and tags are now called 'local file/tag _domain_'. there was a mix of 'service' and 'domain' before, and I am trying to harmonise
* fixed some traceback errors related to middle-clicking stub system predicates (like 'system:rating' in the initial file auto-complete dropdown), where it wasn't checking for the stub status and couldn't navigate what to do next
* fixed importing pdfs (or any other file format) if the thumbnail creation fails silently with a null result
* the archive/delete and duplicate filters, which have a 'want to commit all this?' interstitial dialog on close, no longer tell the parent media window to focus the current media before the interstitial is finished. previously, if you started this process while looking at a video, you'd suddenly get that video playing in the background while thinking about hitting 'commit', and if you decided to cancel out and go back to filtering, the underlying thumbnail page would still have that video highlighted. since the archive/delete job often clears out processed thumbnails right after, this would IRL be a small blip of noise and CPU as the video was loaded and then unloaded. I'm pretty sure this was the cause of the odd mpv lock-up we had a few weeks ago when testing out the new mpv async interface, because of a quick mpv swish before I had code to handle early unload. anyway, this annoyance should be fixed now--the 'play this mediia' signal is sent only on a confirmed media viewer close signal. I brushed up the specific logic about which media to send from an archive/delete, too--depending on which files are set to hide after processing, it'll try and send a different appropriave focus media, often none at all
* `options->tag presentation` has a pair of advanced new options that set the default 'tag display type' of the normal page sidebar taglist and the media viewer taglist. I also fixed a rendering bug with this experimental system; changing the tag display type of a taglist now corrects the 'render for user' state for things like whether to display namespaces or custom namespace separators no matter what the starting state of the list was

### clever rating search

* in system:rating, if you have more than one rating service, there is now a powerful compound 'advanced rating' predicate. it lets you do 'system:all of x are rated' and 'system:any of x are rated', where x is a new widget that lets you select all rating services, just like/dislike, numerical, and/or inc/dec, or individual services in a checkbox list. there is also 'system:only x (amongst y) are rated', where y is a different set of rating services where all of x need to be rated but none of the remainder of y can be rated, with the classical example being x being one rating service and y being all of them, for finding files that are only rated on that service
* all these support 'not rated' too, so you can now find files that have no rating anywhere, somewhere, or within a specific selection (e.g. system:'only favourites not rated out of all my like/dislike ratings')
* I assembled this system through sheer force of will and there may be bugs. let me know how it goes
* if you enter 'only x amongst x rated', i.e. with an uninteresting y, it swaps in 'all x rated'. there are probably some more optimisations if you enter certain one-service edge cases
* I may be convinced to add an 'only-or' variant, but only if there is a real scenario for it and we can come up with clean nomenclature

### duplicates

* the auto-resolution rules review list (in a normal duplicates page) now grows and shrinks depending on the number of rules
* on the first load of a page's auto-resolution rules, the list panel now starts disabled and there's a little 'initialising...' text

### subprocess improvements

* all subprocess calls (when hydrus opens another program, like ffmpeg, or asks your system to open a file externally) now happen in one place with cleaner code and better error handling
* subprocess calls that launch a potentially long-lived program that we don't care much to talk to again, like an external music player run from 'open externally', now hand the process handles to a maintenance list to be polled every few minutes in normal memory maintenance. should be cleaner reaping and fewer zombies in non-Windows environments
* all subprocess calls that we do care for an answer from now have a timeout. if they exceed that time, they are terminated, killed, reaped, and stdout and stderr reported nicely
* all ffmpeg file metadata calls now have special handling for timeout problems, generally raising the 'damaged or unusual file' exception, which lets thumbnail gen and so on know to use a default thumb. timeout is usually 15 seconds
* wrote a separate wrapper for subprocess calls that stream data over a longer time (video, PCM rendering). these use a context manager to ensure the process is terminated and reaped cleanly and also support timeout errors on each individual pipe chunk read
* the calls that create streaming ffmpeg renderers for some more unusual thumbnail gen jobs now properly close the underlying process cleanly
* all subprocess debug reporting mode stuff now happens in all cases

### better image prefetching

* a different user sent in some ideas for smarter image prefetching/pinning, particularly to deal with very-full-cache situations (like when you scroll through ten 12,000x14,000 images), and I worked on it a bit. I ended up not using the pinning for now, but I've improved prefetch intelligence significantly
* when canvases do a neighbour prefetch, they now only perform one prefetch render at a time, alternating with next/previous/next/previous. if any of the prior prefetches are still rendering, we wait until they are done before we start another one. this saves time and memory, improves nearest-next availability when files are slow to load, and improves stability in extreme cases
* the prefetch medias are now submitted and weighed together in order every time, and if doing the next prefetch load would cause the total prefetch size to exceed the percentage allowed in 'speed and memory', we stop prefetching at that point. this stops excessive cache churn when we have lots of extremely-large-file prefetch going on. this saves time, memory, and improves stability in extreme cases
* the 'how much cache size to prefetch' option in 'speed and memory' is altered as a result. it is no longer per file, but for the whole prefetch and the allowed settable range is expanded. the default value is increased from 15% to 25%, and any user who has an existing value less than 25% will be bumped up. with the default options (25% of 1GB image cache), this means about 10x 4k images
* the 'are your prefetch numbers good?' bit in the next section now gives warnings for explicit 1080p/4k counts, so, if you are set to prefetch 4 total files, and they and the current file at 4k would exceed the prefetch threshold, it'll tell you
* the main image prefetch routine also now explicitly asks the cache if it can free up easy space to fit a new prefetch in before firing the prefetch request. images that are currently rendering are counted as 'not easy to free'. this will stop the cache churning when there's big stuff already hitting the CPU
* cache logic is generally improved a little bit
* there are still issues when scrolling through a selection of very large images quickly. the next step here is going to be a 'max number of images rendering at once' setting and render slots and, finally, nicer 'rendering...' loading status in the media viewer on the image you are currently looking at for when things are taking a while
* the old 'delay neighbour prefetching by this base millisecond delay' option no longer does anything and is retired
* fixed an issue where in rare maintenance/cache reset commands, hydrus data caches could be maintaining a fifo record for an item that was already specifically deleted

### boring stuff

* broke the master file search query in the database into constituent parts (the top level was 1,100 lines, now 250)
* wrote a simple search-state object to better track some bool flags throughout a file search
* lots of general cleanup around here
* shuffled some things around to make certain complicated and exclusive searches work faster
* a new safety hook now catches when a search fails to initialise its file domain correctly. the search now returns 0 results and you get a popup about it once per boot
* wrote a new 'service specifier' object to handle some 'here's a bunch of services' storage stuff in a nice-to-serialise way, and wrote an edit panel and button for it
* some db jobs that line many cancellable things up one after another (e.g. file search) will now cancel a bit faster
* all image prefetch code is now done in the same location
* shufled some subprocess stuff around to a new HydrusSubprocessing file
* refactored my process, subprocess, and threading code to a new 'processes' module

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
