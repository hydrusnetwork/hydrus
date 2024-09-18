---
title: Changelog
---

# changelog

!!! note
    This is the new changelog, only the most recent builds. For all versions, see the [old changelog](old_changelog.html).

## [Version 590](https://github.com/hydrusnetwork/hydrus/releases/tag/v590)

### misc

* the 'check now' button in manage subscriptions is generally more intelligent and now offers questions around paused status: if _all_ the selected queries are DEAD, it now asks you if you want to resurrect them with a yes/no variant of the DEAD/ALIVE question (previously it just did it); if you are in _edit subscriptions_ and any of the selected subs are paused, it now asks you if you want to include them (and unpause) in the check now, and if not it reduces the queries examined for the DEAD/ALIVE question appropriately (previously it just did their queries, and did not unpause); in either _edit subscriptions_ or _edit subscription_, if any queries in the selection after any 'paused subs' or 'DEAD/ALIVE' filtering are paused, it asks you if you want to include (and unpause) them in the check now (previously it just did and unpaused them all)
* if you shrink the search page's preview window down to 0 size (which it will suddenly snap to, and which is a silghtly different hide state to the one caused by double-left-clicking the splitter sash), the preview canvas will now recognise it is hidden and no longer load media as you click on thumbs. previously this thing was loading noisy videos in the background etc..
* the `StringMatch` 'character set' match type now has 'hexadecimal characters' (`^[\da-fA-F]+$`) and 'base-64 characters' (`^[a-zA-Z\d+/]+={0,2}$`) in its dropdown choice
* the 'gui pages' options panel now has 'when closing tabs, move focus (left/right)', so if you'd rather move left when middle-clicking tabs etc.., you can now set it, and if your style's default behaviour is whack and never moved to the right before despite you wanting it, now you can force it; it is now explicit either way. let me know if any crazy edge-case focus logic happens in this mode with nested page of pages or whatever
* when you right-click a file, in the _share-&gt;copy hash_ menu, the md5, sha1, and sha512 hashes are now loaded from the database, usually in the milliseconds after the menu is opened, and shown in the menu labels for quick human reference. if your client does not have these hashes for the file, it says so
* the 'share' thumbnail menu is now visible on non-local files. it is severely truncated, basically just shows copy hash/file_id stuff
* wrote a 'Current Deleted Pending Petitioned' section for the Developer API to discuss how the states in the content storage system overlap and change in relation to various commands in the content update pipeline https://hydrusnetwork.github.io/hydrus/developer_api.html#CDPP It may be of interest to non-API-devs who are generally interested in what exactly the 'pending' state etc.. is
* if the file import options in a hard drive import page currently imports to an empty location context (e.g. you deleted the local file service it wanted to import to), the import page now pauses and presents an appropriate error text. the URL importers already did this, so this is the hdd import joining them
* this 'check we are good to do file work' test in the importer pages now in all cases pursues a 'default' file import options to the actual real one that will be used, so if your importer file import options are borked, this is now detected too and the importer will pause rather than fail everything in its file log
* thanks to a user, fixed a typo bug in the new multi-column list work that was causing problems when looking at gallery logs that included mis-linked log entries. in general, the main 'turn this integer into something human' function will now handle errors better

### default downloaders

* _advanced/technical, tl;dr: x.com URLs save better now._ since a better fix will take more work, the 'x post' URL class is for now set to associate URLs. this fixes the association of x.com URLs when those are explicitly referred to as source URLs in a booru post. previously, some hydrus network engine magic related to how x URLs are converted to twitter URLs (and then fx/vxtwitter URLs) to get parsed by the twitter parser was causing some problems. a full 'render this URL as this URL' system will roll out in future to better handle this situation where two non-API URLs can mean the same thing. this will result in some twitter/x post URL duplication--we'll figure out a nice merge later!

### duplicate auto-resolution tech

* I have written the first skeleton of the `MetadataConditional` object. it has a rule based on a system predicate (like 'width &gt; 400px') and returns True/False when you give it a media object. this lego-brick will plug into a variety of different systems in future, including the duplicate auto-resolution system, with a unified UI
* system predicates cannot yet do this arbitrarily, so it will be future work to fill out this code. to start with, I've just got system:filetype working to ultimately effect the first duplicate auto-resolution job of 'if pixel duplicates and one is jpeg, one png, then keep the jpeg'
* add some unit tests to test this capability

### boring search object code decoupling

* refactored the main `Predicate` object and friends to the new `ClientSearchPredicate`
* refactored the main `NumberTest` object and friends to the new `ClientNumberTest`
* refactored the main `TagContext` object and friends to the new `ClientTagContext`
* refactored the main `FileSearchContext` object and friends to the new `ClientSearchFileSearchContext`
* moved some other `ClientSearch` stuff to other places and renamed the original file to `ClientSearchFavourites`; it now just contains the favourite searches manager
* some misc cleanup around here. some enums had bad names, that sort of thing

## [Version 589](https://github.com/hydrusnetwork/hydrus/releases/tag/v589)

### misc

* the similar-files search maintenance code has an important update that corrects tree rebalancing for a variety of clients that initialised with an unlucky first import file. in the database update, I will check if you were affected here and immediately optimise your tree if so. it might take a couple minutes if you have millions of files
* tag parent and sibling changes now calculate faster at the database level. a cache that maintains the structure of which pairs need to be synced is now adjusted with every parent/sibling content change, rather than regenerated. for the PTR, I believe this will save about a second of deferred CPU time on an arbitrary parent/sibling change for the price of about 2MB of memory, hooray. fingers crossed, looking at the _tags-&gt;sibling/parent sync-&gt;review_ panel while repository processing is going on will now be a smooth-updating affair, rather than repeated 'refreshing...' wait-flicker
* the 'the pairs you mean to add seem to connect to some loops' auto-loop-resolution popup in the manage siblings/parents dialogs will now only show when it is relevent to pairs to be added. previously, this thing was spamming during the pre-check of the process of the user actually breaking up loops by removing pairs
* added an item, 'sync now', to the _tags-&gt;sibling/parent sync_ menu. this is a nice easy way to force 'work hard' on all services that need work. it tells you if there was no work to do
* reworked the 'new page chooser' mini-dialog and better fixed-in-place the intended static 3x3 button layout
* showing 'all my files' and 'local files' in the 'new page chooser' mini-dialog is now configurable in _options-&gt;pages_. previously 'local files' was hidden behind advanced mode. 'all my files' will only ever show if you have more than one local files domain
* when a login script fails with 401 or 403, or indeed any other network error, it now presents a simpler error in UI (previously it could spam the raw html of the response up to UI)
* generally speaking, the network job status widget will now only show the first line of any status text it is given. if some crazy html document or other long error ends up spammed to this thing, it should now show a better summary
* the 'filename' and 'first/second/etc.. directory' checkbox-and-text-input controls in the filename tagging panel now auto-check when you type something in
* the 'review sibling/parent sync' and 'manage where tag siblings and parents apply' dialogs are now plugged into the 'default tag service' system. they open to this tab, and if you are set to update it to the last seen, they save over the value on changes

### default downloaders

* fixed the default safebooru file page parser to stop reading undesired '?' tags for every namespace (they changed their html recently I think)
* catbox 'collection' pages are now parseable by default

### boring list stuff

* fixed an issue with showing the 'manage export folders' dialog. sorry for the trouble--in my list rewrite, I didn't account for one thing that is special for this list and it somehow slipped through testing. as a side benefit, we are better prepped for a future update that will support column hiding and rearranging
* optimised about half of the new multi-column lists, as discussed last week. particularly included are file log, gallery log, watcher page, gallery page, and filename tagging panel, which all see a bunch of regular display/sort updates. the calls to get display data or sort data for a row are now separate, so if the display code is CPU expensive, it won't slow a sort
* in a couple places, url type column is now sorted by actual text, i.e. file url-gallery url-post url-watchable url, rather than the previous conveniently ordered enum. not sure if this is going to be annoying, so we'll see
* the filename tagging list no longer sorts the tag column by tag contents, instead it just does '#''. this makes this list sort superfast, so let's see if it is super annoying, but since this guy often has 10,000+ items, we may prefer the fast sort/updates for now

### client api

* the `/add_files/add_file` command now has a `delete_after_successful_import` parameter, default false, that does the same as the manual file import's similar checkbox. it only works on commands with a `path` parameter, obviously
* updated client api help and unit tests to test this
* client api version is now 70

### more boring cleanup

* I cleaned up a mash of ancient shortcut-processing jank in the tag autocomplete input and fixed some logic. everything is now processed through one event filter, the result flags are no longer topsy-turvy, and the question of which key events are passed from the text input to the results list is now a simple strict whitelist--basically now only up/down/page up/page down/home/end/enter (sometimes)/escape (sometimes) and ctrl+p/n (for legacy reasons) are passed to the results list. this fixes some unhelpful behaviour where you couldn't select text and ctrl+c it _unless_ the results list was empty (since the list was jumping in, after recent updates, and saying 'hey, I can do ctrl+c, bro' and copying the currently selected results)
* the key event processing in multi-column lists is also cleaned up from the old wx bridge to native Qt handling
* and some crazy delete handling in the manage urls dialog is cleaned up too
* the old `EVT_KEY_DOWN` wx bridge is finally cleared out of the program. I also cleared out some other old wx event definitions that have long been replaced. mostly we just have some mouse handling and window state changes to deal with now
* replaced many of my ancient static inheritance references with python's `super()` gubbins. I disentangled all the program's multiple inheritance into super() and did I think about half of the rest. still like 360 `__init__` lines to do in future
* a couple of the 'noneable text' widgets that I recently set to have a default text, in the subscription dialogs, now use that text as placeholder rather than actual default. having 'my subscription' or whatever is ok as a guide, but when the user actually wants to edit, having it be real text is IRL a pain
* refactored the repair file locations dialog and manage options dialog and new page picker mini-dialog to their own python files

## [Version 588](https://github.com/hydrusnetwork/hydrus/releases/tag/v588)

### fast new lists

* tl;dr: big lists faster now. you do not need to do anything
* every multi-column list in the program (there's about 75 of them) now works on a more sophisticated model (specifically, we are updating from QTreeWidget to QTreeView). instead of the list storing and regenerating display labels for every single row of a table, only the rows that are currently in view are generally consulted. sort events are similarly extremely fast, with off-screen updates virtualised and deferred
* in my tests, a list with 170,000 rows now sorts in about four seconds. my code is still connected to a non-optimised part of the old system, so I hope to improve gains with background cleanup work in coming months. I believe I can make it work at least twice as fast in places, particularly in initialisation
* multi-column lists are much better about initialising/migrating the selection 'focus' (the little, usually dotted-line-border box that says where keyboard focus is) through programmatic insertions and deletes and sorts
* column headers now show the up/down 'sort' arrows using native style. everything is a bit more Qt-native and closer to C++ instead of my old custom garbage
* none of this changes anything to do with single-column lists across the program, which are still using somewhat jank old code. my taglist in particular is an entirely custom object that is neat in some ways but stuck in place by my brittle design. the above rewrite was tricky in a couple of annoying ways but overall very worth doing, so I expect to replicate it elsewhere. another open choice is rewriting the similarly entirely custom thumbnail canvas to a proper Qt widget with a QLayout and such. we'll see how future work goes

### misc

* fixed the 'show' part of 'pages-&gt;sidebar and preview panels-&gt;show/hide sidebar and preview panel', which was busted last week in the page relayout cleanup
* I think I fixed the frame of flicker (usually a moment of page-wide autocomplete input) you would sometimes get when clicking a 'show these files' popup message files button
* fixed the new shimmie parser (by adding a simpler dupe and wangling the example urls around) to correctly parse r34h tags
* I think I may have fixed some deadlocks and/or mega-pauses in the manage tag parents/siblings dialogs when entering pairs causes a dialog (a yes/no confirmation, or the 'enter a reason' input) to pop up
* I think I have fixed the 'switch between fullscreen borderless and regular framed window' command when set to the 'media_viewer' shortcut set. some command-processing stuff wasn't wired up fully after I cleared out some old hacks a while ago
* the manage tag parents dialog has some less janky layout as it is expanded/shrunk
* if similar files search tree maintenance fails to regenerate a branch, the user is now told to try running the full regen
* the full similar files search tree regen now filters out nodes with invalid phashes (i.e. due to database damage), deleting those nodes fully and printing all pertinent info to the log, and tells the user what to do next
* you can now regen the similar files search tree on an empty database without error, lol
* while I was poking around lists, I fixed a bit of bad error handling when you try to import a broken serialised data png to a multi-column list

### client api

* the `/get_files/search_files` command now supports `include_current_tags` and `include_pending_tags`, mirroring the buttons on the normal search interface (issue #1577)
* updated the help and unit tests to check these new params
* client api version is now 69

## [Version 587](https://github.com/hydrusnetwork/hydrus/releases/tag/v587)

### all misc this week

* I made a second stupid typo last week. it raised an error when trying to open the 'manage tag display and search' dialog! it was fixed thanks to a user
* the current local file domains of a file (e.g. 'my files') are now simply listed in the top-right hover window, above any remote locations or URLs. I think I'm going to make these checkboxes or something in future so we can have one-click file migrations
* if you set up a _share-&gt;export files_ job and one of the internal files is actually missing, the error message now tells you to go check for missing files using the database file maintenance stuff
* if an export files job that is set to delete internal files breaks half way through, the routine now makes sure only to delete what was actually successful
* subscriptions now catch program shutdown signals better. previously, this was being handled as an unknown error and delay times and error texts were being set. it now just closes cleanly, no worries
* the command palette should now match case-insensitively
* I _may_ have fixed a false-positive delete-lock report ('could not delete files xyz because of delete lock') that can happen in the duplicate filter. also, the 'unable to delete file' popup that happens in this case now quietly prints the current stack to log, which I would be interested in seeing
* I believe I have fixed several of the false-positive 'hey it looks like you edited this parser, are you sure you want to cancel?' confirmations in the edit parser dialog
* the automatic datestring parsing routine should now be more resilient against english datestrings when the locale differs significantly (it seems if the locale requires a 24-hour clock, it may be a problem for AM/PM time strings)
* cleaned up some ancient-and-terrible sash-sizing code that manages the three resizable panels of each media results page. hopefully I fixed an issue in Docker and other places where the media page could spawn with a 0-pixel-wide thumbnail panel
* fixed a weird/stupid bug with the new scanbar that would sometimes start giving errors on media transitions because it couldn't find its media parent
* improved how a core UI job waits on the database to be free. it now uses just a little less CPU/fewer thread switches
* improved how that same UI job waits on the pubsub system to be free, same deal
* since they reversed the API click-through requirement, removed the 8chan TOS click-through login script from the defaults. existing users will see it set to non-active. 8chan thread watching should work out the box again

### new list stuff

* I worked on a new multi-column list class that uses a more intelligent data model. I basically finished it, but I will not launch it yet--it needs a bunch more testing and debugging
* as a side thing, a variety of list display update calls, even on the old list, are now a little faster

## [Version 586](https://github.com/hydrusnetwork/hydrus/releases/tag/v586)

### faster sibling/parent fetching

* for a while, some users have had extremely slow selective sibling/parent fetching, usually manifesting in sibling/parent display calculation or autocomplete results decoration. with last week's new sibling/parent async dialogs, the problem was suddenly exposed further. thankfully, this situation was a useful testbed, and I have made multiple updates that I believe should remove much if not all of the unreasonable megalag. if you saw 30 second delays in the new sibling/parent dialogs, let me know how this all works for you. the ideal is that simple stuff takes 50ms, and something that behind the scenes might have 14,000 rows (stuff like 'gender:female' in parents can sprawl like this), should be no more than a couple of seconds on first fetch, and much faster thereafter
* fixed up a bad preload routine in the new sibling/parents dialogs that was doing busy wait and eating up bunch of extra CPU
* simplified the main sibling/parent chain-following search
* removed all the UNION queries from the sibling and parent modules; maybe I'll reintroduce it one day, but it doesn't really save much time and can limit search cleverness by making the query planner go bananas
* further optimised the recursive loop of this search, particularly for parents which has to do some additional sibling ideal lookup stuff to join chains coupled by sibling relations
* overhauled the tag parents/siblings storage tables from the old two-table combined format to dynamic sub-tables separated by both service_id and status. this makes parent and sibling storage a little more spammy but also significantly smaller and more simple, and it ensures search code is always working on clean, efficient, and fast indices, which means no more crazy search variability no matter how we work with these things. as a side benefit, I relaxed the logic so the siblings storage is now capable of storing more 'conflicting' pairs, no longer enforcing an old overly optimistic 1-&gt;n rule (which was probably the cause of some 'I see a different loop to you, how do we debug this?' frustration amongst PTR users comparing siblings). **if you sync with the PTR, the database update to v586 will take a few seconds this week**
* there may still be a single slow-the-first-time query for parents in a PTR-syncing client, simply because certain joiner tags like 'gender:female' merge many groups together. I am considering what to do here, so let's see how it goes
* plugged a hole in the 'fetch relevant sibling/parent pairs' routine where if you triggered two searches at the same time with overlapping tags (e.g. let's say things were working super slow), the second routine was not waiting correctly for the results and the main EnterPairs method was raising a 'hey, this should not have happened' message

### misc

* fixed an issue in the media scanbar where if you had it set to hide completely when the mouse is not over it, then if the media was paused while the scanbar was hidden, the scanbar would unhide in a blank state until you clicked it. further, the anti-show/hide-flicker tech is improved here
* when you open up a tag search page from the media viewer's tag list (e.g. by middle-clicking a tag), the original context's file domain is now preserved. if you open a media viewer on 'my files', then new search pages from the taglist will now be in 'my files' (it was previously defaulting to the safe backstop of 'all my files')
* the client now forces a full tag presentation refresh when deleting a service or resetting a tag respository's processing. this should clear up some ghost tags we were seeing here without having to restart
* the master decoding call used by the parsing system (which does 'convert this raw I/O input to nice unicode text') will now implicitly trust encoding provided by the network engine if that encoding is exlpcitly set in the response (previously it would defer to `chardet` if that was more confident), and if the given document is encoded incorrectly, it will replace bad characters with special question marks
* when an import options button handles only one options type (e.g. the tag import options button in edit subscription query panel, where it also only does 'additional tags' stuff, or the file import buttons in _options-&gt;importing_), the button now previews what it does in its label. the way these summary statements is produced (and, more generally, used in the button's tooltips) is also tightened up--there is less newline spam, and smaller changes will collect into a single line
* because of some remaining display bugs, if your Qt's default style would be the new 'windows11' (which is true for Win Qt 6.7.x), I am saying 'no' and switching it back to 'windowsvista'
* I removed a 'do not allow an import folder to run for more than an hour' timer. this was an undocumented backstop hack and was messing with 'do not run regularly' import folders that operate on 100,000+ file mega folders. if you want a gigantic import job, you got it
* silenced some spammy network reporting--the main file and gallery import objects were printing tracebacks to the log on many failure states, which in some unusual SSL/Connection errors was resulting in a whole lot of html garbage being dumped to the log
* improved the error message when an audio file's duration cannot be determined
* tweaked the 'help my db is broke.txt' document
* fixed up some weird tag application logic: the client db and the tags manager object now agree that you can, through programmatic means, petition content that does not yet exist (e.g. to insert deleted rows from an external source), and thus if you wish to _pend_ content, we need to check for conflicting pre-existing _petitioned_ content, and _vice versa_. the manage tags dialog similarly understands this, but it won't offer the 'petition' action when things do not yet exist because this is a bit technical and best left to programmatic editing like the Client API or migrate tags window. it was previously possible to create a situation where a file had both pending and petitioned data that did not yet exist (`tag (+1) (-1)`, lol)--this should no longer be possible. if you got into this situation and want to clean it up, try doing a search for 'system:has tags' on just 'include pending tags', and then ctrl+a-&gt;F3 your results and then ctrl+a the taglist and hit enter on it--you should be given an option to 'undo petition on x tags' and clear it all up in one go

### noneable defaults

* all of the 'noneable' (nullable) integer widgets (where you have an editable number with a 'no limit' checkbox beside it) now initialise with an appropriate default value in the integer box, even if they otherwise initialise in the 'None' state. previously, these would usually sit at '1' on the number side, when starting at None, meaning you'd have to guess an appropriate number when switching from None to something concrete. all the noneable integers in the options dialog now initialise with their respective options default
* similarly, most of the noneable text input boxes now initialise with a suggested value in the text box even if the initial value for that dialog or whatever is the 'None' checkbox ticked
* and all of the nullable bytes widgets (a number-of-bytes value and then 'no limit' checkbox) similarly now initialise with a default value. they kind of already did, but it is better formalised now
* dejanked some nullable int widget code design. the ones that have two dimensions are now their own class

### client api

* thanks to a user, `/get_files/render` has new parameters that let you now ask for a png/jpeg/webp rather than just png, at a certain quality, and a certain resolution
* added the 'sort by pixel hash hex and blurhash' sort_type definitions to the help for `/get_files/search_files` and noted that you can asc/desc these too
* `/add_files/add_file` now accepts a 'file domain' to set a custom import destination (just like in file import options). obviously you can only set local file domains here
* `/add_urls/add_url` also now accepts a 'file domain', same deal. it will select/create a new url downloader page with non-default file import options set with that import destination
* updated the help and unit tests to reflect the above
* added `/add_urls/migrate_files` to copy files to new local file domains (essentially doing _files-&gt;add to_ from the thumbnail menu)
* with (I think) all multiple local file service capabilities added to the Client API, issue #251 is finally ticked off
* client api version is now 68

## [Version 585](https://github.com/hydrusnetwork/hydrus/releases/tag/v585)

### the new asynchronous siblings and parent dialogs

* the `tags->manage tag siblings/parents` dialogs now load quickly. rather than fetching all known pairs on every open, they now only load pertinent pairs as they are needed. if you type in tag A in the left or right side, all the pairs that involve A directly or point to a pair that involves A directly or indirectly are loaded in the background (usually so fast it seems instant). the dialog can still do 'ah, that would cause a conflict, what do you want to do?' logic, but it only fetches what it needs
* the main edit operations in this dialog are now 'asynchronous', which means there is actually a short delay between the action firing and the UI updating. most of the time it is so fast it isn't noticeable, and in general because of other cleanup it tends to be faster about everything it does
* the dialogs now have a sticky workspace 'memory'. when you type tags in, the dialog still shows the related rows as normal, but now it does not clear those rows away once you actually enter those new pairs. the 'workspace' shows anything related to anything you have typed until you hit the new 'wipe workspace' button, which will reset back to a blank view. I hope this makes it less frustrating to work on a large group--it now stays in view the whole time, rather than the 'current' stuff jumping in and out of view vs the pending/petitioned as you type and submit stuff. the 'wipe workspace' button also has the current workspace tags in its tooltip
* the 'show all pairs' checkbox remains. it may well take twenty seconds to load up the hundreds of thousands of pairs from the PTR, but you can do it
* also added is a 'show pending and petitioned groups', which will load up anything waiting to be uploaded to a tag repository, and all related pairs
* when a user with 'modify siblings/parents' adds a pair, the auto-assigned 'reason' is now "Entered by a janitor.' (previously it was the enigmatic "admin")
* some misc layout improvements aross the board. the green/red text at the top is compressed; the 'num pairs' now shows the current number of pairs count; there are more rows for the pairs list, fewer for the input list; and the pairs list eats up all new expand space
* a great amount of misc code cleanup in all these panels and systems, and most of the logic is shared between both sibling and parent dialogs. a lot of janky old stuff is cleared up!
* these dialogs are better about showing invalid, duplicated, or loop-causing pairs. the idea is to show you everything as-is in storage so you can better directly edit problems out (previously, I am pretty sure it was sometimes collapsing stuff and obscuring problems)
* the 'manage tag parents' dialog now auto-petitions new loops when entering pairs (it was just siblings before)
* this tech now works on multiple potential loops, rather than just the first
* the 'manage tag parents' dialog now detects pre-existing loops in the database record and warns about this when trying to enter pairs that join the loop (it was just siblings before)
* this tech works better and now detects multiple loops, including completely invalid records that nonetheless exist (e.g. `a->b, a->c` siblings that point to more than one locations), and when it reports them, it now reports them all in one dialog, and it shows the actual `a->b->c->d` route that forms the loop
* a bad final 'do not allow loop-inputs' backstop check in the main pair-add routine is removed--it was not helping

### misc

* hitting escape on any taglist will now deselect all tags
* added 'Do not allow mouse media drag-panning when the media has duration' to the _options->media viewer_ page. if you often misclick and pan when scrubbing through videos, try it out!
* the media viewer's top hover window no longer shows every 'added-to' time for all the local file services; it was spammy, so it now just says 'imported: (time)'. the related 'hide uninteresting import time' option is retired. I also removed the 'archived: (time)' label, so this is now pretty much just 'imported, modified'. if I bring detailed times back to the file summary, it'll be part of a more flexible system. note that all these timestamps are still available in the media top-row flyout menu
* the file log and gallery log now copy their urls/sources on a ctrl+c hit. also, the 'copy' right-click commands here also no longer unhelpfully double-newline-separates rows
* a `StringConverter` edit panel now throws up a yes/no confirmation if you try to ok on a regex substitution that seems to match a group in the pattern but has an empty string in the 'replacement' box
* updated the 'test' versions of OpenCV (4.10.0.84), Pyside6 (6.7.2), and python-mpv (1.0.7). I'll be testing these myself, and devving with them, mostly to iron out some Qt 6.7.x stuff we've seen, and then put out a future release with them
* added a note to the default_mpv.conf to say 'try commenting out the audio normalisation line if you get mpv problems and are on Arch'
* added different example launch paths to the 'external programs' options panel depending on the current OS
* added a note about running with `QT_QPA_PLATFORM=xcb` on Wayland to the install help
* refactored the `ClientGUIFileSeedCache` and `ClientGUIGallerySeedLog` files, which do the file and gallery log panels, up to the 'gui.importing' module
* thanks to a user, added a new darkmode 'Nord' stylesheet

### fixes

* fixed 'scrub invalidity' in the manage logins dialog--sorry, it was a stupid typo from the recent multiple-column list rework. also, this button is now only enabled if the login script is active
* fixed a bug opening the 'migrate files' dialog when you have no files!
* I force-added `Accept-Language: en-US,en;q=0.5` to the client's default http headers for pixiv.net. this appears to get the API to give us English tags again. let me know if this completely screws anything up
* updated the 'do we have enough disk space to do this transaction?' test to check for double the destination disk amount. thanks to the user who helped navigate this--regardless of temp dir work, when you do a vacuum or other gigantic single transaction, there is a very brief period as the transaction commits when either the stuffed WAL journal or (for a vacuum) cloned db file exists at the same time in the same folder as the original db file. I also updated the text in the 'review vacuum data' window to talk about this a bit. good luck vacuuming your client.mappings.db file bros
* improved the error handling when a sidecar import fails--it now says the original file path in the report
* improved failure-recovery of unicode decoding (usually used in webpage parsing) when the given text includes errors and the encoding is `ISO-8859-1` (or the encoding is unparseable and `requests` falls back to it) and/or if `chardet` is not available
* I hacked the menubar padding back to something sensible on the new 'windows11' style int Qt 6.7.x. for whatever reason, this new style adds about 15px of padding/margin to each menubar menu button. I am aware the collect-by combobox is still busted in this style--let me know if you spot anything else! btw switching from 'windows11' to 'windowsvista' seems to make all the menubar menus transparent, let's go
* improved the layout of the 'edit client api access key permissions' panel. it wasn't vertically expanding before
* fixed up some keypress handling in taglists. some stuff that was being swallowed or promoted unintentionally is fixed
* thanks to a user, fixed a weird bug in the 'repair missing file storage locations' boot repair dialog where it would always say you only had missing thumbs
* also thanks to that user, the 'repair missing file storage locations' dialog now checks `client_files` and `thumbnails` subdirectories when trying to auto-discover with the 'add a possibly correct location' action

### some hash-sorting stuff

* _you can probably ignore this section, don't worry about it_
* you can now sort by blurhash. this works at the database level too, when mixed with system:limit
* when sorting by pixel hash, a file search with system:limit now pre-sorts by pixel hash before the limit clips the resultset
* when sorting by pixel hash or blurhash, the files with no such hash (e.g. audio files) are now always put at the end
* searching many tens of thousands of files and sorting by hash, pixel hash, or blurhash is now just a tiny bit faster

### client api

* the new `/manage_services/get_pending_counts` command now includes the 'Services Object' in its response
* the client api version is now 67

## [Version 584](https://github.com/hydrusnetwork/hydrus/releases/tag/v584)

### misc

* fixed a logical hole in the recent 'is this URL that is saying (deleted/already in db) trustworthy, or does it have weird mappings to other files?' pre-download check that was causing Pixiv, Kemono, and Twitter and any other multiple-URL Post URL Class to, on re-encountering the URL in a downloader, classify the underlying file URL as untrustworthy and re-download the files(l!!)
* the 'copy all' and paste buttons in the manage known urls dialog are replaced with icon buttons, and the copy button now copies the current selection if there is one
* the newish Regex input widget (the one that goes green/red based on current text validity) now propagates an Enter key into a dialog ok event when appropriate
* when you ctrl+double-click a taglist, the program now ensures the item under the mouse is selected before firing off the double-click nega-activation event. this is slightly awkward, but I hope it smoothes out the awkward moment where you want to invert a selection of tags but doing a normal ctrl+double-click on them causes the one of them to be deselected and then messes up the selection
* regex URL searches are now always the last job to run in a file query. if you mix in any other predicate like filesize or just some tag, your regex URL searches should run massively massively faster
* improved some boot error handling when Qt fails to import
* fixed the whack alignment of the 'filename'/'first directory'/etc.. checkbox-and-text-edit widgets in the filename tagging panel, and set 'namespace' placeholder text
* force-selecting a null value in a 'select one from this list of things' dialog should no longer raise errors
* thanks to a user, the new shimmie parser gets tags in a simpler, more reliable way

### client api

* added a new permission, `Commit Pending` (12), which allows you to see and commit pending content for each service
* added `/manage_services/get_pending_counts`, which basically returns the content of the client's 'pending' menu
* added `/manage_services/commit_pending`, which fires those commands off
* added `/manage_services/forget_pending`, which does the same 'forget' command on that menu
* added `/manage_file_relationships/remove_potentials`, which clears any known potential pairs off the given files
* the `/manage_pages/get_pages` and `/manage_pages/get_page_info` commands now return `is_media_page` boolean, which is a simple shorthand for 'not a page of pages'
* added the above to the Client API help
* wrote unit tests covering the above
* the client api version is now 66

### boring cleanup

* fixed up how some lists deliver their underlying data to various methods
* `CallBlockingToQt` no longer spams encountered errors to the log--proper error handling should (and does now) occur elsewhere
* the way the initial focus is set on system predicate flesh-out panels (when you double-click on like 'system:dimensions' and get a bunch of sub-panels) is more sane. should be, fairly reliably, on the first editable panel's ok button. I want it to be on an editable widget in the panel in future, I think, but I need to do some behind the scenes stuff to make this work in a nicer way
* pulled some stuff out of `HydrusData`, mostly to `HydrusNumbers`, `HydrusLists`, and the new `HydrusProcess`, mostly for decoupling purposes
* renamed some `ConvertXToY` stuff to just `XToY`

## [Version 583](https://github.com/hydrusnetwork/hydrus/releases/tag/v583)

### new

* added a 'command palette' options page. the ability to show menubar and media actions is now set here with a couple of checkboxes (previously these were hidden behind advanced mode)
* you can also now search for 'page of pages' with the command palette. this is turned on in the same new options page
* the new sidecar test panel now only shows its notebook tabs if there is more than one source. the tab labels, when shown, are now '1st' ... '2nd' ordinal strings respective to the source list on the left
* added some explanation text, a button to the help docs, and a bit of better layout to the sidecars UI
* the file import report mode now writes the 'nice human description' for the file import to the log. this will expose the source URL or local file path for better context than just the random temp path
* in the 'manage times' dialog, you can now set the same timestamp (including cascading timestamps) to multiple domains or file services at once. the logic is a little delicate where some files are in one domain in your selection and others are only in another, but I think I got it working ok. if you have a complicated setup, let me know how you get on!
* the 'Dark Blue' stylesheets and the new 'Purple' stylesheet have updated custom colours

### fixes

* fixed a typo in the 'fetch a mappings petition' server code
* when the client is called to render an image that was just this moment removed from the file store, the image renderer should now give you a nicer error image with an appropriate messare rather than throwing an error popup
* hydrus no longer applies EXIF Orientation (rotation) to PNG files, which it recently started doing automatically when we started scanning PNGs for EXIF. EXIF is not well-defined and supported for PNG, and if an Orientation row exists, it is likely a false positive mistake of some encoder. hydrus will show this data but it will not apply it, and the metadata review UI now also notes this
* fixed the 'has exif?' file maintenance job, which I think was false-negativing!

### code and help

* the `psutil` library is now technically optional. it is still needed for a bunch of normal operations like 'is the client currently running?' and 'how much free space is there on this drive?', but if it is missing the client will now boot and try to muddle through anyway
* did more multi-column list 'select, sort, and scroll' tech for: the url class parameters list; the url class links list; the external launch paths list; the tag suggestion related tags namespace lists; import folder filename tagging options; manage custom network context headers; the string to string match widget list; the string match to string match widget list; the edit subscription queries list; and more of the edit subscriptions subscription list, including the merge and separate actions
* updated the QuickSync help a little, clarifying it is only useful for _new, empty_ clients

## [Version 582](https://github.com/hydrusnetwork/hydrus/releases/tag/v582)

### fixes

* fixed an issue where setting a file 'collect' was not automatically sorting the collected objects internally properly. normally when you collect, each collected object is supposed to be sorted internally by filesize or namespace or whatever--this is working again
* fixed a weird internal error state in the import folders manager where it could get confused about and throw an error regarding the import folders' next work times if an internal update notification occured during an import folder working
* fixed a typo error with the shortcut set 'special duplicate' button
* fixed pasting new query texts into the manage subscriptions dialog when one of the pasted texts resurrects a DEAD query. my new summary generation text was handling the DEAD report wrong!

### misc

* the advanced 'all deleted files' service, which is mostly just used for behind the scenes caching calculations, is renamed to 'deleted from anywhere'. the related 'regen-&gt;all deleted files' database command is also moved to 'check and repair-&gt;sync combined deleted files'
* the edit tag filter panel's 'load' button now shows all the current tag repositories' tag filters
* when you hit ctrl-enter on some tags (or otherwise trigger a linked remove+add action) in an active search list (e.g. top-left on a search page), which causes those tags to invert and thus sometimes sorted to a different position, the current selection now propagates through the inversion, with the keyboard focus moved to the post-topmost item. so, you can now basically hit ctrl+enter twice for a no-op
* fixed the paste button in the new 'purge tags' dialog
* thanks to a user, we have a new 'Purple' stylesheet
* I tweaked the some default stylesheet colours and think I fixed the display of the 'valid/invalid' controls you sometimes see (for instance in the new regex input, which goes green/red) for dark mode stylesheets that don't define colours for these. previously, the dark mode text, usually a light grey, was being washed out by the default green

### custom colours in QSS

* you can now set the _options-&gt;colours_ colours in a QSS stylesheet! if you are a stylesheet maker, check the default_hydrus.qss file to see how it works--it is the same deal as the animation scanbar previously
* the options in _options-&gt;colours_ remain, but they are now wrapped in a 'overwrite your stylesheet with these colours' checkbox _for now_. existing users are going to be set to 'yes overwrite', so nothing will suddenly change, but new users are going to default to using whatever the current QSS says. in future, I may collapse the light/darkmode distinction into one option set; I may morph it into a "colour highly rated files' thumbnail borders gold" dynamic options system; I may simply delete the whole thing and replace it with in-client QSS editing or something. not sure, so let's see how it goes and how Qt 7's darkmode stuff turns out.
* I have pasted the hydrus default darkmode colours into all the other stylesheets that come with the program, so new users selecting a darkmode style are going to get something reasonable out of the box rather than the previous ugly clash. the users who made the original stylesheets are welcome to figure out better colours and send them in
* if you are not set to override with the custom colours in _options-&gt;colours_, then hitting _help-&gt;darkmode_ now gives you a popup telling you what is going on

### sidecar UI

* the four 'edit sidecars' panels (under manual imports, import folders, manual exports, and export folders), which use paths and media as sources respectively, now have test panels to review the current sidecar route you have set up. they use up to 25 rows of example file paths/media from the actual thing you are working on. it provides a live update of what the sources you set up will load, so you know you have the json parse or .txt separator set up correct
* for the export folders case, there is a button in the panel 'edit export folders' panel to populate the text context, under your control, since this involves a potentially slow file search
* there is more to do here. I would like better test panels in the sub-dialogs and I'd like to collapse the related 'eight-nested-dialogs-deep' problem, and in the string processing and parsing UI more generally, but I'm happy with this step forward. let me know where it goes wrong!

### advanced autocomplete logic fixes

* when you enter a wildcard into a Read tag autocomplete, it no longer always delivers the 'always autocompleting' version. so, if you enter `sa*s`, it will suggest `sa*s (wildcard search)` and perhaps `sa*s (any namespace)`, but it will no longer suggest the `sa*s*` variants until you, obviously, actually type that trailing asterisk yourself. I intermittently had no idea what the hell I was doing when I originally developed this stuff
* the 'unnamespaced input gives `(any namespace)` wildcard results' tag display option is now correctly negatively enforced when entering unnamespaced wildcards. previously it was always adding them, and sometimes inserting them at the top of the list. the `(any namespace)` variant is now always below the unnamespaced when both are present
* fixed up a bunch of jank unit tests that were testing this badly

## [Version 581](https://github.com/hydrusnetwork/hydrus/releases/tag/v581)

### misc

* thanks to a user, we have a much improved shimmie parser, for both file and gallery urls, that fetches md5 better, improves gallery navigation, stops grabbing bad urls and related tags by accident, and can handle namespaces for those shimmies that use them. for our purposes, this improves r34h and r34@paheal downloaders by default
* thanks to a user, we have a new 'Dark Blue 1.1' styesheet with some improvements. the recommendation is: check the different scrollbar styling to see if you prefer the old version
* timedelta widgets now enforce their minimum time on focus-out rather than value change. if it wants at least 20 minutes, you can now type in '5...' in the minutes column without it going nuts. let me know if you discover a way to out-fox the focus-out detection!
* added a checkbox to file import options to govern whether 'import destinations' and 'archive all imports' apply to 'already in db' files. this turns on/off the logic that I made more reliable last week. default is that they do
* added 'do sleep check' to _options-&gt;system_ to try some things out on systems that often false-positive this check
* the 'review current network jobs' multi-column list has a new right-click menu to show a bit more debug info about each job: each of its network contexts, how the bandwidth is on each context, if the domain is ok, if it is waiting on a connection error, if it is waiting on serverside bandwidth, if it obey bandwidth, and if its tokens are ok. if you have been working with me on gallery jobs that just sit on 'starting soon', please check it out and let me know what you see. also, 'review current network jobs' is duplicated to the help-&gt;debug menu. I forgot where it was, so let's have it in both places
* on the filename-import tagging panel, the filename and directory checkbox-and-text-edit widgets no longer emit a (sometimes laggy) update signal when typing when the checkbox is unchecked

### janitor stuff

* if you are a repository janitor, right-clicking on any tag shows a new 'admin' menu
* if you have 'change options' permission, you will see 'block x'/'re-allow x' to let you quickly see if tags are blocked and then edit the repository tag filter respectively
* if you have 'mappings petition resolution' permission, you can 'purge' the selected tags, which will deleted them from the service entirely. this launches a review window that previews the job and allows adding of more tags using the standard autocomplete interface. when 'fired off', it launches a tag migration job to queue up the full petition/delete upload
* this new 'purge' window is also available from the normal 'administrate services' menu in the main gui
* also under the 'administrate services' is a new 'purge tag filter' command, which applies the existing repository tag filter to its own mappings store, retroactively syncing you to it

### tag filters and migration

* I wrote a database routine that quickly converts a hydrus tag filter into the list of tags within a file and tag search context. this tech will have a variety of uses in the genre of 'hey please delete/fetch/check all these tags'
* to start with, it is now plugged into the tag migration system, so when you set up, say, an 'all known files' tag migration that only looks for a namespace or a bunch of single tags, the 'setup' phase is now massively, massively faster (previously, with something like the PTR, this would be scanning through tens of millions of files for minutes; now it just targets the 50k or whatever using existing tag search tech usually within less than a second)
* cleaned (KISSed) and reworked the tag filter logic a bit--it can now, underlyingly, handle 'no namespaced tags, except for creator:anything, but still allowing creator:blah'
* optimised how tag filters do 'apply unnamespaced rules to namespaced tags' (which happens in some blacklists that want to be expansive)
* improved how the tag filter describes itself in many cases. it should make more grammatical sense and repeat itself less now (e.g. no more 'all tags and namespaced tags and unnamespaced tags' rubbish)
* improved how some tag filter rules are handled across the program, including fixing some edge-case false-positive namespace-rule detection
* deleted some ancient and no longer used tag filtering code

### boring multi-column list stuff

* did more 'select, sort, and scroll' code cleanup in my multi-column lists, specifically: manage import folders; manage export folders; the string-to-string dict list; edit ngug; edit downloader display (both gugs and url classes, and with a one-shot show/hide choice on a multi-selection rather than asking for each in turn); the special 'duplicate' command of edit shortcut set; and the string converter conversions list (including better select logic on move up/down)
* in keeping with the new general policy of 'when you edit a multi-column list, you just edit one row', the various 'edit' buttons under these lists across the program are now generally only enabled when you have one row selected
* the new 'select, sort, and scroll to new item when a human adds it' tech now _deselects_ the previous selection. let me know if this screws up anywhere (maybe in a hacky multi-add somewhere it'll only select the last added?)
* the aggravating 'clear the focus of the list on most changes bro' jank seems to be fixed--it was a dumb legacy thing
* whenever the multi-column list does its new 'scroll-to' action, it now takes focus to better highlight where we are (rather than stay, for instance, leaving focus on the 'add' button you just clicked)

### other boring stuff

* worked a little more on a routine that collapses an arbitrary list of strings to a human-presentable summary and replaced the hardcoded hacky version that presents the 'paste queries' result in the 'edit subscription' panel with it
* wrote a similar new routine to collapse an arbitrary list of strings to a single-line summary, appropriate for menu labels and such
* fixed a layout issue in the 'manage downloader display' dialog that caused the 'edit' button on the 'media viewer urls' side to not show, lmaooooooo
* ephemeral 'watcher' and 'gallery' network contexts now describe themselves with a nicer string
* decoupled how some service admin stuff works behind the scenes to make it easier to launch this stuff from different UI widgets
* refactored `ToHumanInt` and the `ToPrettyOrdinalString` guys to a new `HydrusNumbers.py` file
* fixed some bad Client API documentation for the params in `/get_files/search_files`
