---
title: Changelog
---

# changelog

!!! note
    This is the new changelog, only the most recent builds. For all versions, see the [old changelog](old_changelog.html).

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

## [Version 580](https://github.com/hydrusnetwork/hydrus/releases/tag/v580)

### misc

* I _may_, and a very hesitant _may_, have fixed the program hanging after minimising to system tray from the close button. thanks to the user who pinned down that it was the close button doing this rather than the other ways to minimise to system tray. if you have had trouble with minimising to the system tray, please try again when it is convenient and let me know how you get on. please also note which exact command, whether it was the file menu, system tray icon menu, minimise button, or close button, that you hit to trigger the minimise event that ultimately would not restore correctly
* the taglist right-click menu now has a _maintenance-&gt;regenerate tag display_ command, which is basically the 'regenerate mappings storage cache' command in the database menu, but limited just to your selection. this _should_, with luck, fix incorrect autocomplete counts or sibling/parent presentation for any tags you see that are weird. I've wanted this for years, since the whole-cache regen is so large that it is essentially impossible to run on the PTR, but now we can debug individual tag presentation problems a lot easier!
* fixed an issue where read-only import files would not delete from the temp dir after import, despite, if desired, successfully deleting from their original locations. it turns out the read-only property was being copied to the temp path for import, and the 'I'm done with the temp file, delete it' routine, unlike the normal file delete, wasn't checking for and undoing read-only status. note this was also screwing with the 'delete the hydrus temp dir on shutdown' routine, so if you do a lot of unusual/misc hard drive imports, feel free to shut your client down, check your temp folder (hit _help->about_ to find it), and delete anything called hydrusXXXXXXXX
* the new 'eye' icon in the media viewer now has 'apply image ICC Profile colour adjustments', which will flip on/off the fairly newish checkbox added to _options->media playback_. it updates the image live!
* added a shortcut for the 'flip apply image ICC Profile colour adjustments' to the 'media viewer' set! if you are big into this stuff and also do duplicate filtering, set it up and let me know how it goes
* important but subtle file import options fix: when you set a file to import to a specific destination in file import options, or you say to archive all imports, this is supposed to work even when the file is 'already in db'. this was not working when 'already in db' was caused by a 'url/hash recognised' result in the downloader system. I have fixed this; it now works for 'already in db' for url/hash/file recognised states. thank you to the user who noticed this and did the debug legwork to figure out what was going on
* import _file logs_ now have a menu item 'search for URLs', which does the same as the recent 'urls' media right-click menu command, opening a search page for any files that share these URLs
* added a shortcut command 'reload the current qss stylesheet' to the 'main gui' shortcut set. moreover, the 'reload current ui session' entry in the debug menu, which was just above this before, is renamed to 'close and reload current ui session' because of common misclicks
* the options panel uses less CPU on ok/cancel to set/reset style as needed. same deal with the old hack that makes the colour-picker work--it'll now be more efficient about setting/resetting style
* fixed a stupid list/tuple type error when trying to edit the 'frame locations' in options->gui. this was from an accident during the selection/scroll rewrites last week
* generally improved the reliability of the multi-column list against the above bug in its various forms
* added a simple click-through login script to fix recent changes to the 8chan.moe TOS filter, which broke the respective watcher. all users get this and it should just work out of the box
* thanks to a user, the default danbooru parsers are fixed to fetch md5 hash correctly
* some misc tooltip and description fixes
* improved some media result testing stuff

### client api

* the `/add_tags/add_tags` command has two new parameters, `override_previously_deleted_mappings`, and `create_new_deleted_mappings`, both True by default (which was also previous behaviour). turning either off allows you to, respectively, not force-add a tag mapping when it has been previously deleted (like how the gallery downloader works) and not force-delete (and thus make a 'delete' record) when deleting a tag mapping unless it already exists
* updated the Client API help to talk about these
* added some unit tests to test these
* the client api is now version 65

## [Version 579](https://github.com/hydrusnetwork/hydrus/releases/tag/v579)

### some url-checking logic

* the 'during URL check, check for neighbour-spam?' checkbox in _file import options_ has some sophisticated new logic. check the issue for a longer explanation, but long story short is if you have two different booru URLs that share the same source URL (with one or both simply being incorrect e.g. both point to the same 'clean' source, even though one is 'messy'), then that bad source URL will no longer cause the second booru import job to get 'already in db'. it now recognises this is an untrustworthy mapping and goes ahead with the download, just as you actually want. once the file is imported, it is still able, as normal, to quickly recognise the true positive 'already in db' result, so I believe have successfully plugged a logical hole here without affecting normal good operation! (issue #1563)
* the 'associate source urls' option in file import options is more careful about the above logic. source urls are now definitely not included in the pre-import file url checks if this option is off

### some regex quality of life

* regex input text boxes have been given a pass. the regex 'help' links are folded into the button, the links are updated to something newer (one of the older ones seems to have died), the button is now put aside the input and labelled `.*`, the menu is a little neater, and the input has placeholder text and now shows green/red (valid/invalid in the stylesheet) depending on whether the current regex text compiles ok. just a nicer widget overall
* this widget is now in filename tagging, the String Match panel regex match, the String Converter panel regex step, and the 'regex favourites' options panel, which I was surprised to learn the existence of
* the regex menu for the String Converter regex step also now shows how to do grouping in python regex. I hadn't experimented with this properly in python, but I learned this past week that this thing can handle `(...) -> \1` group-replace fine and can do named groups with `(?P<name>...) -> \g<name>` too!
* for convenience, when editing a String Match, if you flick from 'any' to 'fixed' or 'regex', it now puts whatever was in your example text beforehand as the new value for the fixed text or regex

### list selecting and scrolling

* I added some new scroll-to tech to my multi-column lists
* pasting a URL into the 'edit URL Classes' dialog's test input now selects and scrolls to the matching URL Class
* the following lists should all have better list sort/select preservation, and will now scroll to and maintain visibility, on various edit/add events: edit url classes, edit gugs, edit parsers, edit shortcut sets, edit shortcut set, the options dialog frame locations, the options dialog media viewer options, manage services, manage account types, manage logins, manage login scripts, edit login script, and some weird legacy stuff. lots more to do in future
* when you 'add from defaults' for many lists, it will now try and scroll to what was just added. may not be perfect!
* same deal with 'import' buttons. it will now try and scroll to what you import!
* I am also moving to 'when you edit, you only edit one row at a time'. in general, when I have written list edit functions, I write them to edit each row of a multi-selection in turn with a new dialog, but: this is not used very much, can be confusing/annoying to the user, and increases code complexity, so I am undoing it. as I continue to work here, if you have a multi-selection, an edit call will increasingly just edit the top selected row. maybe in this case I'll reduce the selection, maybe I'll add some different way to do multi-edit again, let me know what you think

### misc

* import folders now work in a far more efficient way. previously, the client loaded import folders every three minutes to see which were ready to run; now, it loads them once on startup or change and then consults each folder to determine how long to wait until loading it again. it isn't perfect yet, but this ancient, terrible code from back when 100 files was a lot is now far more efficient. users with large import folders may notice less background lag, let me know how you get on. thanks to the users who spotted this--there's doubtless more out there
* to help muscle memory, the 'undo' menu is now disabled when there is nothing for it to hold, not invisible. same deal for the 'pending' menu, although this will still hide if you have no services to pend to (ipfs, hydrus repositories). see how this feels, maybe I'll add options for it
* the new 'is this webp animated?' check is now a little faster
* if your similar file search tree is missing a branch (this can happen after db damage or crash desync during a file import) and a new file import (wanting to add a new leaf) runs into this gap, the database now imports the file successfully and the user gets a popup message telling them to regen their similar files search tree when convenient (rather than raising an error and failing the import)
* added a FAQ question 'I just imported files from my hard drive collection. How can I get their tags from the boorus?', to talk about my feelings on this technical question and to link to the user guide here: https://wiki.hydrus.network/books/hydrus-manual/page/file-look-up
* the default bandwidth rules for a hydrus repository are boosted from 512MB a day to 2GB. my worries about a database syncing 'too fast' for maintenance timers to kick in are less critical these days

### build and cleanup

* since the recent test 'future build' went without any problems, I am folding its library updates into the normal build. Qt (PySide6) goes from 6.6.0 to 6.6.3.1 for Linux and Windows, there's a newer SQLite dll on Windows, and there's a newer mpv dll on Windows
* updated all the requirements.txts to specify to not use the brand new numpy 2.0.0, which it seems just released this week and breaks anything that was compiled to work with 1.x.x. if you tried to set up a new venv in the past few days and got weird numpy errors, please rebuild your venv in v579, it should work again
* thanks to a user, the Docker build's `requests` 'no_proxy' patch is fixed for python &gt;3.10
* cleaned up a ton of `SyntaxWarnings` boot logspam on python &gt;=3.12 due to un-`r`-texted escape sequences like `\s`. thanks to the user who submitted all this, let me know if I missed any
* cleaned up some regex ui code
* cleaned up some garbage in the string panel ui code
* fixed some weird vertical stretch in some single-control dialogs

## [Version 578](https://github.com/hydrusnetwork/hydrus/releases/tag/v578)

### animated webp

* we now have animated webp support! despite many libraries having trouble with this, it turns out that modern PIL can decode and render them. I have figured out a solution using my old native gif renderer, so webps will now play in the program
* I'm going the same route as gifs and (a)pngs--the program now tracks 'webp' vs 'animated webp' as different filetypes. all your image webps will be queued for a scan on update, and any with animation will become the new type, with num frames and duration, and will be fully viewable in the media viewer
* I don't know when PIL added this tech, so if you are a source user and haven't rebuilt your venv in a while, this is probably a good time!

### misc

* the five new 'draw hover-window text in the background of media viewer' options are now copied to the media viewer itself, under a new 'eye' icon menu button. I'll be hanging more stuff off here, like 'always on top' in future!
* the 'known urls' media submenu is now just 'urls', and it now has A) the 'manage' command, moved from the manage menu and B) 'open in a new page' for the focused file's specific URLs or 'any of them' (i.e. it opens a new search page with 'system:known url=blah', so if you need to find which files share a URL, it is now just one click
* fixed the gelbooru 0.2.5 post parser's fetching of multiple source urls. it was not splitting them correctly due to a (recent?) change on gelbooru's end and adding unhelpful `https://gelbooru.com/%7C` gumpf as an additional source url
* added a 'network report mode (silent)' to the `help-&gt;debug` menu, which does everything the network report mode does but with silent logging rather than a million popups. should help with longer-term debugging
* fixed an issue with fetching gif variable framerate timings in the native renderer
* added variable framerate tech to the native renderer for all animation types PIL can figure out except apng (previously it could only do it for gif)
* tightened up some of the file metadata checks. apng is now scanned for exif data, the HEIF types are now scanned for transparency. these jobs are also queued up on update
* the media viewer's top hover's center buttons (usually inbox/delete stuff) are finally centered correctly, aligned with the text below. apologies for the delay; it took several years of under-waterfall mediation to gather enough chi, but I finally have a beginner's understanding of `QSizePolicy.Expanding`

### boring cleanup

* fixed some more long tooltips to wrap into nice newlines
* converted the 'manage urls' dialog to the decoupled 'edit' paradigm
* refactored most of the 'scrolling panel' code to a new `gui.panels` module
* broke up some of the bloated scrolling panel code into smaller files, moved Migrate Tags and Edit Timestamps to new files in `gui.metadata`, and replaced/deleted some old code
* refactored `ClientGUITime` to `gui.metadata`, `ClientGUILogin` to `gui.networking`

## [Version 577](https://github.com/hydrusnetwork/hydrus/releases/tag/v577)

### explorer integration

* thanks to a user, we have some new OS-file-explorer integration
* two additional options are added to the "open" menu for Windows users, "in another program" opens the Windows dialog to select which program to use and "properties" opens the Windows file properties dialog for the file
* the 'media' shortcut set gets the new 'open file properties' and 'open with...' commands to plug into these new features
* the "open in file browser" media menu command now more reliably selects the file in Windows and is now available for most Linux file managers--full list [here](https://github.com/damonlynch/showinfilemanager#supported-file-managers).
* the "open files' locations" file import log menu command is similarly more reliable, and can sometimes select multiple files when launched on a selection
* this requires a new external library, so users who run from source will want to rebuild their venvs this week to get this functionality

### misc

* the manage times single-time edit dialog's paste button can now eat any datstring you can think of. try pasting 'yesterday 3am' into it, it'll work!
* split the increasingly cluttered 'media' options panel into 'media playback' (options governing how media is rendered) and 'media viewer' (options governing the viewer itself like drags and slideshows)
* added to the new 'media viewer' panel are five checkboxes to turn off the background text in the full media viewer--for the taglist, the top hover, the top-right hover, the notes hover, and the bottom-right index string. if you want, you can have a completely blank background now
* gave the _help-&gt;about_ window a pass. I broke the cluttered first tab into two, and the layout all over is a bit clearer
* the _help-&gt;advanced mode_ option is now available under a new _options-&gt;advanced_ tab. this thing covers several dozen things across the program, all insufficiently documented, so the plan is to blow it out into all its granular constituent components on this page!
* fixed it so an invalid `ApplicationCommand` will still render a string. if you got some jank `ToString()` errors in a shortcuts dialog recently, please try again and let me know what you get. you'll probably want to go into the actual shortcut with the error string and try and see if you can fix what it has set--again, let me know the details please!
* updated the 'installing and updating' help page to talk clearly about the different versions that have special update instructions, and generally gave the language a pass

### some url encoding

* fixed an issue in url encoding-normalisation where urls were not retaining their parameters if their names had certain decoded characters (particularly, this was stuff like the decoded square brackets in `fields[post]=123`). a new unit test will catch this in future
* url classes and parsers are now careful to encode their example urls any time they are asked for (outside of their respective edit dialogs' "example url(s)" fields, so if you want to work with a human-looking URL in UI, that's fine). this ensures the automatic url-parser linking system works if the parser and url classes have a mish-mash of encoded and non-encoded example URLs. it also fixes some stuff like the multi-column list in the manage url classes dialog when the url class has a decoded example url. this was basically just an ingestion point that I missed in the previous work
* the edit parser dialog makes sure to properly encode the URL when you do a test pull

### orphan table tech

* the _database-&gt;db maintenance-&gt;clear orphan tables_ command, which could previously only clear out the repository update/processing-tracking tables, can now nuke: the core file list tables in client.db; the core mappings tables in client.mappings.db; the display and storage mappings caches in client.caches.db; the display and storage autocomplete count caches; the ideal and actual tag parent lookup tables in client.caches.db; the ideal and actual tag sibling lookup tables in client.caches.db; and the various tag search tables (except the fts4 stuff) in client.caches.db
* when this job fires, it now sends orphan tables to the deferred delete system (previously it dropped them immediately, which for a big mappings table is a no-go)

### boring cleanup

* cleaned a bunch of db table code for the new orphan table stuff
* deleted the old 'yaml_dumps' table and all associated methods, which are all now unused
* added a couple help labels to the "colours" and "style" pages to better explain what is actually going on here
