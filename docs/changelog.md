---
title: Changelog
---

# changelog

!!! note
    This is the new changelog, only the most recent builds. For all versions, see the [old changelog](old_changelog.html).

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

## [Version 576](https://github.com/hydrusnetwork/hydrus/releases/tag/v576)

### file access latency

* the mpv player no longer hangs the UI thread on file load if the file manager is busy. it now just shows a black square until things are freed up. sorry this took so long to fix!
* the client file storage system has a new two-layer locking mechanism that allows for massively more parallel access, even when files are importing. file imports should lag out file/thumbnail load significantly less
* the 'check for file orphans' maintenance job is now a significantly less-blocking process. it'll lock each of the 512 subfolders in turn, which will delay some file/thumb access, but it won't need an exclusive write lock on the whole client files manager for the entire job any more
* also, the 'check for file orphans' job now saves thumbnails, sticking them in a subdirectory of the export location you designate. some users wanted to try using saucenao-type services to try and recover when they had a thumb but no file, so let's see how this works out

### import options in watchers and gallery downloaders

* instead of the mysterious 'set options to queries' button, there is now a button beside the 'import options' one that is only visible when the current selection of downloaders has differing file limit or import options than the main page. although this is still a complicated idea, I hope this will make it a little more obvious what is going on
* I did the same deal for the watchers page, for checker options or the import options
* it may be that some import options appear to differ after a client restart despite having the same settings. if you get this, let me know the details and I'll fix it!
* the 'set options to watchers' command now updates note import options
* fixed gallery imports not always saving changes to their note/tag import options in the main gui session, particularly if they are paused and the client is closed soon after options change
* improved the import options button's handling of certain options objects when editing, I suspect this fixed some weird edge-case situations of 'I thought I did not set that there' kind of thing, particularly when doing multiple sets of editing to a page and then sub-queries within it
* the import options button also has a stricter 'set default' command, clearing out old data more thoroughly to help with inter-widget comparisons here

### misc

* thanks to a user, we now have support for legacy Microsoft Office documents (.doc, .ppt, .xls), and a framework for other OLE based documents in future
* this new feature requires the `olefile` library. this is optional, and everyone who runs the normal built release now gets it, but if you run from source you might like to re-run the `setup_venv` script this week so you get it
* thanks to a user, the danbooru parsers now grab a danbooru post time accurate and precise to the second (previously they were getting 24-hour resolution, I think UTC midnight)
* uploading large files to the file repository should now use significantly less memory and be far less error prone. due to an in-elegant network request, it was previously timing out the connection if files took too long to upload. the code now streams the upload more cleverly. thanks to the users who helped with this one
* (tl;dr: if you have a darkmode stylesheet, the colour picker dialog is now fast) it looks like Qt fixed the weird bug that meant certain stylesheets broke the colour picker, so my test that says 'if the user is on Qt 6 and they have a hover-includiig stylesheet, then force a fake stylesheet without that tech before they open the colour-picker dialog and then restore the old one after they close, adding multiple seconds of entry and exit lag to this dialog argh' now no longer applies if you are on Qt 6.6 or later, which is anyone on the built release. let me know if you still have any problems!
* URLs are now tested against URL Classes by descending order of domain length. this ensures that if you have a URL class for 'api.example.com' and another for 'example.com', and this latter one is set to also apply to subdomains, the specific 'api.example.com' URL Class will be tested first! this was frequently working as desired before, but only for accidental reasons; it is now explicit in all cases

### boring stuff

* cleaned up the the regex list in the filename tagging panel, which had some ancient bad code from the wx days that stored the data in the string labels
* similarly significantly dejanked the 'ListBook' widget used in the options dialog
* overhauled my four(!!) separate radiobox classes, merging the best of all into one unified class and getting rid of some similar ancient and horrible 'select by label' tech. about twenty or thirty radioboxes across the program, particularly the stuff you see in system predicate panels, now operate on slightly saner principles
* fixed up the 'default gui session' combobox in the options, which was also inexplicably using ancient tech
* updated some misc UI typos and unhelpful tooltips
* refactored some of the client files manager to work with a 'prefix chunk', which will represent an umbrella prefix in the future system that supports overlapping folders and folders with differing prefix lengths'
* deleted some old client files manager code
* thanks to a user, the macOS setup_venv is fixed to point at the correct Cocoa/Quartz requirements.txt file

## [Version 575](https://github.com/hydrusnetwork/hydrus/releases/tag/v575)

### misc

* the new 'children' tab now sorts its results by count, and it only shows the top n (default 40) results. you can edit the n under _options-&gt;tags_. let me know how this works IRL, as this new count-sorting needs a bit of extra CPU
* when you ask subscriptions to 'check now', either in the 'edit subscription' or 'edit subscriptions' dialogs, if there is a mix of DEAD and ALIVE subs, it now pops up a quick question dialog asking whether you want to check now for all/alive/dead
* fixed the (do not) 'alphabetise GET query parameters' URL Class checkbox, which I broke in v569. sorry for the trouble--the new URL encoding handling was accidentally alphabetising all URLs on ingestion. a new unit test will catch this in future, so it shouldn't happen again (issue #1551)
* thanks to a user, I think we have fixed ICC profile processing when your system ICC Profile is non-sRGB
* fixed a logical test that was disallowing thumbnail regen on files with no resolution (certain svg, for instance). all un-resolutioned files will now (re)render a thumb to the max bounding thumbnail resolution setting. fingers crossed we'll be able to figure out a ratio solution in future
* added a _debug-&gt;help-&gt;gui actions-&gt;reload current stylesheet_ menu action. it unloads and reloads the current QSS
* added a _debug-&gt;help-&gt;gui actions-&gt;reload current gui session_ menu action. it saves the current session and reloads it
* fixed the rendering of some 16-bit pngs that seem to be getting a slightly different image mode on the new version of PIL
* the debug 'gui report mode' now reports extensive info about virtual taglist heights. if I have been working with you on taglists, mostly on the manage tags dialog, that spawn without a scrollbar even though they should, please run this mode and then try to capture the error. hit me up and we'll see if the numbers explain what's going on. I may have also simply fixed the bug
* I think I sped up adding tags to a local tag service that has a lot of siblings/parents
* updated the default danbooru parsers to get the original and/or translated artist notes. I don't know if a user did this or I did, but my dev machine somehow already had the tech while the defaults did not--if you did this, thinks!
* added more tweet URL Classes for the default downloader. you should now be able to drag and drop a vxtwitter or fxtwitter URL on the client and it'll work

### auto-duplicate resolution

* I have nothing real to show today, but I have a skeleton of code and a good plan on how to get the client resolving easy duplicate pairs by itself. so far, it looks easier than I feared, but, as always, there will be a lot to do. I will keep chipping away at this and will release features in tentative waves for advanced users to play with
* with this system, I will be launching the very first version of the 'Metadata Conditional' object I have been talking about for a few years. fingers crossed, we'll be able to spam it to all sorts of other places to do 'if the file has x property, then do y' in a standardised way

### boring stuff

* refactored the new tag children autocomplete tab to its own class so it can handle its new predicate gubbins and sorted/culled search separately. it is also now aware of the current file location context to give file-domain-sensitive suggestions (falling back to 'all known files' for fast search if things are complicated)
* fixed a layout issue on file import options panel when a sister page caused it to be taller than it wanted; the help button ended up being the expanding widget jej
* non-menubar menus and submenus across the program now remove a hanging final separator item, making the logic of forming menu groups a little easier in future
* the core 'Load image in PIL' method has some better error reporting, and many calls now explicitly tell it a human-readable source description so we can avoid repeats of `DamagedOrUnusualFileException: Could not load the image at "&lt;_io.BytesIO object at 0x000001F60CE45620&gt;"--it was likely malformed!`
* cleaned up some dict instantiations in `ClientOptions`
* moved `ClientDuplicates` up to a new `duplicates` module and migrated some duplicate enums over to it from `ClientConstants`
* removed an old method-wrapper hack that applied the 'load images with PIL' option. I just moved to a global that I set on init and update on options change
* cleaned some duplicate checking code

## [Version 574](https://github.com/hydrusnetwork/hydrus/releases/tag/v574)

### local hashes cache

* we finally figured out the 'update 404' issue that some PTR-syncing users were getting, where PTR processing would halt with an error about an update file not being available on the server. long story short, SQLite was sometimes crossing a wire in the database on a crash, and this week I add some new maintenance code to fix this and catch it in future
* the local hash cache has a bunch of new resync/recovery code. it can now efficiently recover from missing hash_ids, excess hash_ids, desynced hash_ids, and even repopulate the master hash table if that guy has missing hash_ids (which can happen after severe db damage due to hard drive failure). it records all recovery info to the log
* the normal _database-&gt;regenerate-&gt;local hashes cache_ function now works entirely in this new resync code, making it significantly faster (previously it just deleted and re-added everything). this job also gets a nicer popup with a summary of any problems found
* when the client recovers from a bad shutdown, it now runs a quick sync on the latest hash_ids added to the local hashes cache to ensure that desync did not occur. fingers crossed, this will work super fast and ensure that we don't get the 404 problem (or related hash_id cross-wire problems) again
* on repository processing failure and a scheduling of update file maintenance, we now resync the update files in the local hash cache, meaning the 404 problem, if it does happen again, will now fix itself in the normal recovery code
* on update, everyone is going to get a full local hash cache resync, just to catch any lingering issues here. it should now work super fast!
* fixed an issue where the local hash and tags caches would not fully reset desynced results on a 'regenerate' call until a client restart

### misc

* thanks to a user, the default twitter downloader I added last week now gets full-size images. if you spammed a bunch of URLs last week, I apologise: please do a search for 'imported within the last 7 days/has a twitter url/height=1200px' and then copy/paste the results' tweet URLs into a new urls downloader. because of some special twitter settings, you shouldn't have to set 'download the file even if known url match' in the file import options; the downloader will discover the larger versions and download the full size files with no special settings needed. once done, assuming the file count is the same on both pages, go back to your first page and delete the 1200px tall files. then repeat for width=1200px!
* the filetype selector in system:filetype now expands to eat extra vertical space if the dialog is resized
* the filetype selector in file import options is moved a bit and also now expands to eat extra vertical space
* thanks to a user, the Microsoft document recognition now has fewer false negatives (it was detecting some docs as zips)
* when setting up an import folder, the dialog will now refuse to OK if you set a path that is 1) above the install dir or db dir or 2) above or below any of your file storage locations. shouldn't be possible to set up an import from your own file storage folder by accident any more
* added a new 'apply image ICC Profile colour adjustments' checkbox to _options-&gt;media_. this simply turns off ICC profile loading and application, for debug purposes

### boring cleanup

* the default SQLite page size is now 4096 bytes on Linux, the SQLite default. it was 1024 previously, but SQLite now recommend 4096 for all platforms. the next time Linux users vacuum any of their databases, they will get fixed. I do not think this is a big deal, so don't rush to force this
* fixed the last couple dozen missing layout flags across the program, which were ancient artifacts from the wx-&gt;Qt conversion
* fixed the WTFPL licence to be my copyright, lol
* deleted the local booru service management/UI code
* deleted the local booru service db/init code
* deleted the local booru service network code
* on update, the local booru service will be deleted from the database

## [Version 573](https://github.com/hydrusnetwork/hydrus/releases/tag/v573)

### new autocomplete tab, children

* **this is an experiment. it is jank in form and workflow and may be buggy**
* the search/edit tag autocomplete dropdowns now have a third tab, 'children', which shows the tag children of the current tag context, whether that is the current search tags or what you are editing
* the idea is you type 'series:evangelion' but can't remember the character names; now you have a nice list of a bunch of stuff related to what was already entered
* note you can select this tab real quick just by hitting 'left arrow' on an empty text input
* this is a first draft, and I would like feedback and ideas, mostly around workflow improvement ideas. it seems to work ok if you have one or two tags with interesting children, but against a big list of stuff, it just becomes another multi-hundred list of spam blah that is difficult to navigate. maybe I could filter it to (and sort by?) the top n most count-heavy results?
* I wonder if it could also show children on the same level, so if you have 'shinji', it'll also show 'rei' and 'asuka'. I would call this relationship 'siblings', but then we'd be in an even bigger semantic mess
* also obviously please let me know if this fails anywhere. I think I have it hooked up correct, but some of the code around here is a bit old/messy so some scenario may not update properly
* don't worry about background lag if you regularly manage lots of tags--it only actually fetches the list of children when you switch to the tab, so you're only spending CPU if you actively engage with it

### misc

* a user and I figured out a new twitter tweet downloader using the excellent fxtwitter mirror service. it doesn't do search, but dropping a tweet URL on the client should work again. should handle quoted media and works for multi/mixed-image/video posts, too. note it will nest-pursue quoted tweets, so if there's like fifty in the nested chain, it'll get them all--let me know if this is a big pain and I'll figure out a different solution. I learned that there is another twitter downloader made by a different user on the discord; I have made the update code check for this and not replace it with this if you have it already, and I expect I'll integrate what that can do into these defaults next week
* the archive/delete and duplicate filters now yes/no confirm when you say to 'forget' at the end of a filtering run
* the duplicate filter page now only allows you to set the search location to local file domains--so it'll only ever try to search and show pairs for files you actually have
* fixed the system predicate parsing of `system:duration: has duration` and `system:duration: no duration` when entered by hand, and added a unit test to catch it in future
* the manage siblings/parents dialogs now have a little shorter minimum height
* updated some text around the PTR processing in the help--it is only the database proper, the .db files normally in `install_dir/db`, that needs to be on an SSD, and temporary processing slowdowns to 1 row/s are normal
* touched up some of the 'installing' and 'running from source' help, particularly for some Linux vagaries

### some build stuff

* all the builds and the setup_venv scripts are moved from 'python-mpv' to 'mpv', the new name for this library, and the version is updated to 1.0.6, which supports libmpv version &gt;=0.38.x. if you are a windows user and want to live on the edge, feel free to try out this very new libmpv2.dll here, which I have been testing and seems to work well: https://sourceforge.net/projects/mpv-player-windows/files/libmpv/mpv-dev-x86_64-20240421-git-b364e4a.7z/download
* updated the setup_venv scripts' Qt step to better talk about which Qt version to use for which Python version. it turns out Python 3.12 cannot run something I was recommending for &gt;=3.11, so the whole thing is a lot clearer now

### boring stuff

* refactored some question/button dialog stuff
* fixed up some file domain filtering code in the autocomplete filter and variable names to better specify what is being filtered where

### local booru deconstruction

* _reminder: I am removing the local booru, an ancient, mostly undocumented experiment._ if you used it, please check out https://github.com/floogulinc/hyshare for a replacement!
* the local booru service no longer boots as a server
* deleted the local booru share cache
* the local booru review services panel no longer shows nor allows management of its shares
* deleted the local booru unit tests
* deleted the local booru help and ancient screenshots
