---
title: Changelog
---

# changelog

!!! note
    This is the new changelog, only the most recent builds. For all versions, see the [old changelog](old_changelog.html).

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

## [Version 572](https://github.com/hydrusnetwork/hydrus/releases/tag/v572)

### misc

* added a new checkbox to _options-&gt;files and trash_ to say 'include skipped files when you remove files after archive/delete'
* thanks to a user, we now have an 'e621' stylsheet in _options-&gt;style_. this is the first default stylesheet that uses assets (some checkbox etc.. svgs), which means some users--I think just those who run from source--will need to be careful that their CWD is the hydrus install dir when they boot, or this won't load properly! if you try it and get errors in your log as it tries to load the svgs, let me know!

### share menu

* like the 'open' menu a couple weeks ago, the 'share' menu off of thumbnails or the media viewer is rewritten to nicer code. no major differences, but it has a clearer, universal layout, provides more options for 'the currently focused file' vs 'all selected files', is more careful about only providing commands it can deliver on (e.g. no file copy for remote files), and now everything it does is mappable in the shortcut system under the 'media' shortcut set
* you can now copy a file's thumbnail as a bitmap from this menu!
* the canvas now supports 'export files'. the 'export files' window just pops on top of it with the one file
* 'copy file id' is no longer hidden by advanced mode--go nuts!
* the share menu no longer has 'share on local booru'. the local booru service was an interesting experiment, but I could never find time to properly dev it and there are better answers with the Client API or simple third-party image hosting services that you can drag and drop to. thus, I am finally sunsetting it. I'll strip away its features over the coming weeks until it is completely removed

### shortcut updates

* the 'copy file hash' shortcut actions, which used to be four separate things, have been collapsed to one action that has a 'hash type' dropdown (and a 'target' dropdown to select either all selected files or just the currently focused file, which will default to 'all selected' on update, which was the previous behaviour). you can also now set 'pixel_hash' or 'blurhash' as the hash type
* the 'copy file bitmap' shortcuts have similarly been collapsed down to one action with a dropdown, also with the new 'copy thumbnail' command
* the 'copy files', 'copy file paths', and 'copy file id' shortcuts now have a dropdown for whether you want all selected files or just the currently focused file. updated commands will default to 'all selected', which was the previous behaviour
* added a 'copy ipfs multihash' shortcut action, which has this new 'focused vs all selected' parameter and the ipfs service to copy from as its options

### boring code cleanup

* wrote a new command for copying arbitrary file hashes, with a new 'file command target'
* simplified the media hash copying code
* wrote a new command for copying arbitrary bitmap types
* combined the bitmap copying code into one shared function call and simplified the surrounding code
* combined the file and path copying code into shared functions, simplified the code, and added tech for focused vs all selected targeting
* and the same thing for copying ipfs multihashes
* wrote a routine to copy a file's thumbnail in the normal clipboard copying pubsub
* with the recent rounds of simplication, the core thumbnail menu call is now but a mere 600 lines of spaghetti code
* misc renaming of some enums here so they are more in agreement ('xxx files' instead of 'xxx file', etc...)
* renamed the various simple commands I have replaced in the past few weeks as 'legacy', so we don't accidentally refer to them again in real code
* the unit test for 'dateparser decode' is no longer run if dateparser is not in the environment
* fixed the file metadata parsing unit tests to account for newer ffmpeg, which sees a -10ms different duration on one of the test files, and made the various tests +/-20% lenient to handle this stuff if it comes up again in future

## [Version 571](https://github.com/hydrusnetwork/hydrus/releases/tag/v571)

### clean install

* the recent 'future build' test went well, so I am rolling these updates into the normal release for everyone. on Windows and Linux, the built program is now running Python 3.11, and, on all platforms, updated versions of Qt (UI) and OpenCV (image-processing). there's nothing earth-shattering about these changes, but some things will work better and faster
* **because of the jump, v570 and v571 have dll conflicts! if you are on Windows or Linux and use the .zip or .tar.zst "Extract" release, you will need to a clean install as here**: https://hydrusnetwork.github.io/hydrus/getting_started_installing.html#clean_installs
* **if you are a Windows installer/macOS App/source user, you do not need to do a clean install, just update as normal**

### misc

* when you finish an archive/delete filter and there are several domains you could delete from, the 'commit' buttons are now disabled for 1.2 seconds. this catches you from accidentally spamming enter through a surprise complicated decision
* under _options-&gt;files and trash_, you can now say 'when finishing filtering, always delete from all possible domains', which makes the above decision always single domain. hit this if you do want to spam through this and are fine always deleting from everywhere
* the client will now, by default, attempt to load truncated images. this was previously off until you set it per-session-on in a debug menu, but is now a checkbox under _options-&gt;media_. some weird damaged jpegs and pngs should now load, fingers crossed
* the 'load images with PIL' setting is now default on for new users and no longer IN TESTING
* every normal single column text list across the program now copies text better if you explicitly hit ctrl+c/ctrl+insert. they now copy all selected rows (rather than just one), and when the display text differs from the underlying data/sort text, you'll now get the sort text (e.g. on manage urls launched on multiple files, you might see 'site.com/123456 (2)', but now, when it copies, that ' (1)' display cruft is omitted). I spammed this to 22 locations and tested 2 so there are definitely no weird string copy bugs anywhere
* fixed an issue opening/closing manage parsers, url classes, or url class links if you have url classes with invalid example urls or critically missing default values in your storage
* the server has a new 'restart_services' command, only triggerable by an admin with service modification ability, which tells all the services on all ports to stop and restart. if there's a new ssl cert, they load the new one

### client api

* the 'associate urls' command has a new 'normalise_urls' parameter (default true, which was the behaviour before) to let you force-add un-normalised URLs or URIs or whatever
* added some unit tests to test this new param
* client api version is now 64

### help docs

* wrote a new help document, 'help my db disappeared.txt' for the db directory that tells you what to do if you boot one day and suddenly get the 'this looks like the first time you ran this program' popup
* clarified the Windows 'running from source' help a little around 'git' and added a 'here is the Python version you want' link for Win 7 users
* gave the install help a very light pass, just fixing and updating a few things here and there. I also warn Linux users that the AUR package may throw errors if Arch updates a Qt library or something before we have had a chance to test it (as we have seen a couple times recently), and I generally suggest AUR people run from source manually if they can

## [Version 570](https://github.com/hydrusnetwork/hydrus/releases/tag/v570)

### UI stuff

* wrote a thing to wrap tooltips and applied it everywhere. every tooltip in the program should now wrap to 80 characters
* the thumbnail view is now better about pausing the current video if you open it externally in various ways
* the 'open' submenu you get off of a file right-click is now exactly the same for the thumbnail menu and the media viewer menu, with all commands working in either place, the labels are also brushed up a little
* added a shortcut action for 'open file in web browser' to the media shortcut set
* added a shortcut action for 'open files in a new duplicates filter page' to the media shortcut set
* added/updated the shortcut action for 'open similar looking files in a new page' in the media shortcut set. this is now one job that lets you set any distance, and it now works from the media viewer too. all existing `show similar files: 0 (exact)` fixed-distance simple actions will be converted to the new action when you update
* I removed 'open externally' and 'open in file explorer' shortcuts from the media viewer/preview viewer/thumbnails sets. these sets are technically awkward and were really meant for a different thing, like pause/play or 'close media viewer', and having the media command code duplicated here was getting spammy. if you have any of these now-defunct commands set, please move them up to the general 'media' set, where it'll work everywhere. sorry if this breaks a very complicated set you have, but let's KISS!
* the 'files' submenu off thumbnails or the media viewer is flattened one level. the 'upload to' remote services stuff still isn't available for the media viewer, but I'll do the same as I did above for that in the near future

### misc

* fixed an issue with the 'manage tag siblings/parents' dialogs where the mass-import button was, in 'add or delete' mode, not doing any deletes/rescinds if there were any new pairs in what was being imported. this was probably applying to large regular adds in the UI, also
* this mass-import button of 'manage tag siblings/parents' also dedupes the pairs coming in. it now shouldn't do anything like 'add, then ask to remove' if you have the same pair twice!
* the nitter downloaders are removed from the defaults. I can't keep up with whatever the situation is there
* the style and stylesheet names in the options are now sorted
* sidecar importers will now work on sidecars that have uppercase .TXT or .JSON extensions

### more URL stuff (advanced, can be ignored by most)

* fixed up the recent URL encoding tech to properly follow the encoding exceptions as under RFC 3986. an '@' in an URL shouldn't get messed up now. thanks to the user(s) who helped here
* incoming URLs can now have a mix of encoded and non-encoded characters and the 'ensure URL is encoded' process will accept it and encode the non-encoded parts, idempotently. it only fails on ingesting a legit decoded percent character that happens to be followed by two hex chars, but that's rare enough we don't really have to worry
* you can similarly now enter multiple tags in a query text that are a mix of encoded and non-encoded, a mix of %20 and spaces, and it should figure it out
* the 'ensure URL is encoded' process now applies to GUG-generated URLs, and in the edit GUG UI, you now see the normalised 'for server' URL, with any additional tokens or whatever the URL class has
* GUGs also try to recognise if their replacement phrase is going into the path or the parameters now, and only force-encodes everything if it looks like our tags are going into a query param
* ensured that what you paste into an 'edit URL Class' panel's 'example url' section gets encoded before normalisation just as it would in engine
* the file log right-click now shows both the normalised and request urls under the 'additional urls' section, if they differ from the pretty human URL in the list
* right-clicking a single item in the downloader search log now previews the specific request URL to be copied

### boring stuff

* all instances of URL path or parameter encoding now go through one location that obeys RFC 3986
* replaced my various uses of the unusual `ParseResult` with `urllib.parse.urlunparse`
* added a couple unit tests for the improved URL encoding tech
* added some unit tests for the GUGs' new encoding tech
* harmonised how a file is opened in the OS file explorer in the media results and media canvas pages. what was previously random hardcode, duplicated internal method calls, and ancient pubsub redirects now all goes thorugh the application command system to a singular isolated media-actioning method
* did the same harmonisation for opening files externally
* and for opening files in your web browser, which gets additional new infrastructure so it can plug into the shortcuts system
* and to a lesser degree the 'open in a new page' and 'open in a new duplicates filter page' commands
* moved the various gui-side media python files to a new 'gui.media' module. renamed `ClientGUIMedia` to `ClientGUISimpleActions` and `ClientGUIMediaActions` to `ClientGUIModalActions` and shuffled their methods back and forth a bit
* cleaned up `ClientGUIFunctions` and `ClientGUICommon` and their imports a little with some similar shuffle-refactoring
* broke up `ClientGUIControls` into a bunch of smaller, defined files, mostly to untangle imports
* cleaned up how some text and exceptions are split by newlines to handle different sorts of newline, and cleaned up how I fetch the first 'summary' line of text in all cases across the program
* replaced `os.linesep` with `\n` across the program. Qt only wants `\n` anyway, most logging wants `\n` (and sometimes converts on the fly behind the scenes), and this helps KISS otherwise. I might bring back `os.linesep` for sidecars and stuff if it proves a problem, but most text editors and scripting languages are very happy with `\n`, so we'll see
* multi-column lists now show multiline tooltips if the underlying text in the cell was originally multiline (although tbh this is rare)
