# changelog

!!! note
    This is the new changelog, only the most recent builds. For all versions, see the [old changelog](old_changelog.html).

## [Version 487](https://github.com/hydrusnetwork/hydrus/releases/tag/v487)

### misc
* updated the duplicate filter 'show next pair' logic again, mostly simplification and merging of decision making. it _should_ be even more resistant to weird problems at the end of batches, particularly if you have deleted files manually
* a new button on the duplicate filter right hover window now appends the current pair to the parent duplicate media page (for if you want to do more processing to them later)
* if you manually delete a file in the duplicate filter, if that file appears again in the current batch of pairs, those will be auto-skipped
* if you manually delete a file in the duplicate filter, the actual delete is now deferred to when you commit the batch! it also undoes if you go back!
* fixed a bug when editing the external program launch paths in the options
* fixed an annoying delay-and-error-popup when clearing the separator field when editing a String Splitter. now the field just turns red and vetoes an OK with a nicer error text
* also improved how string splitters report actual split errors
* if you are in advanced mode, the _review services_ panels now have an 'id' button that lets you fetch the database service id
* wrote a new database maintenance routine under _database->check and repair->resync tag mappings cache files_, which is a lightweight way of fixing ghost files or situations where files with a tag are neither counted nor appear in file results. this fixes these problems in a couple minutes, so for this it is much better than a full regen of the cache

### cleanup and other boring stuff
* the archive/delete filter now says which file domain it will be deleting from
* if an archive/delete filter is launched on a 'multiple locations' file domain, it is now careful to only make delete records for the deleted files for the file services each one is actually in
* renamed the 'default local file search location' option to 'fallback' and updated its tooltip a bit. this was really a hacky thing I needed to fill some gaps while rewriting from 'my files' to multiple local file services. the whole thing needs more attention to become more useful. I also fixed an issue where it could become invalid 'nothing' if you deleted a file service it was referring to (issue #1155)
* I think I fixed a rare 'did not find info for that file' style problem when highlighting some watchers/downloaders
* I think I have silenced some unhelpful BeautifulSoup (html parser) warnings that were spamming to the log in some situations
* updated last week's big update to work with TRUNCATE journalling mode. I will be doing this for other big updates going forwards, since multi-GB WAL transactions cause problems for some users
* last week's update also gives a time estimate in its pre-popup, based on 60k files per minute
* removed some old database cache data that wasn't cleared in a previous update
* a variety of misc UI text fixes and cleanup

## [Version 486](https://github.com/hydrusnetwork/hydrus/releases/tag/v486)

* **This week's release is for advanced users only! I make a big change, and I want to make sure the update is fast and there are no unusual problems before rolling it out to all users.**
### all my files
* the client adds a new virtual file service this week, 'all my files', which is an umbrella covering all your local file domains. if you do not engage the multiple local file services system, you won't see it much, but if you do, you'll now have a convenient tool for saying 'all my stuff' without including trash and repository updates
* **it will take a minute or two to generate this new service on update. if you have a client with millions of files, it may take a while**
* 'all my files' now appears in the file domain selector button on your tag entry box if you have more than one local file domain. selecting this searches the union of all your local file domains with fast and precise count (as opposed to 'multiple locations' of the full union, which will have imprecise counts and be slower). it also does duplicate file work laser-fast (again, unlike 'multiple locations', which is often slow due to UNION complexity)
* 'all my files' also appears in review and manage services, very similarly to 'all local files'
* a heap of hacks I instituted when getting multiple local file services ready are now replaced with this clean 'yeah this file is valued and worth looking at' domain. for instance, downloader pages now view files in this way.
* mr bones and the file history chart also use 'all my files', and are significantly faster to calculate. the chart also excludes repo update files and trash now
* calls to delete or undelete on 'all my files' (this is mostly Client API and some 'default' situations) will be converted to a blanket 'force send to trash' and 'force undelete all deleted records'
* the 'undelete files?' dialog is now a button selection dialog. it also now has an 'all the above' option when more than one local service may apply, which tells the client to undelete to all services the files have been deleted from
* updated multiple local file services help to talk a little about the new domain
* rearranged the sort in a couple of places where the different local file services appear. they should now be: local file domains, all my files, trash, repo updates, all local files
* ADVANCED: the 'presentation import options' under 'file import options' now allows a full-fledged location context using the new multiple local file services system rather than the previous 'in your files(and trash too)' choice. it defaults to the new 'all my files' domain

### misc
* thanks to a user, the 'getting started with downloading' help has had a full pass. if you have had trouble with downloaders, particularly if you are unsure about what file import options are for, or what subscriptions are, please check it out!
* the 'media viewers' shortcut set gets three new zoom actions: 'switch between 100% and max', 'switch between canvas and max', and 'zoom to max' (issue #1141)
* if a media type is set to do 'exact zooms', it will now not exceed the otherwise specified max zoom
* the file sort widget will now preserve ascending/descending status on sort type changes (rather than resetting to default) if the asc/desc strings do not change. so, if you are on 'import time'/'oldest first', and switch to 'archive time', it will now stay on 'oldest' rather than resetting to 'newest'
* the manage tag siblings dialog now tries to automatically break loops for you, just like it will automatically break A->B, A->C conflicts. this works on manual entry or mass import
* the manage tag siblings dialog now shows the stated 'reason' for any pair change (e.g. "AUTO-PETITION TO BREAK LOOP") in the 'note' column
* the 'short' animation scanbar--when your mouse is away--now keeps a short disabled volume button beside it. I found it very annoying how the scan nub would jump a few pixels left/right as this popped up and down, so now it is the same width big and small
* right-clicking on files when in pages with 'multiple locations' file domains is now much much faster
* the filename tagging dialog now starts with the 'tags for all' focused, and the 'press up/down on empty input' shortcuts are now plugged in, so pressing up/down will change service
* I believe I may have completely eliminated the additional superlag that sometimes occurs when adding or deleting a service. it was a database maintenance routine getting carried away with other outstanding work
* move/add actions in the new multiple local file system now operate asynchronously and politely, spreading their work time out when the client is busy, and for large jobs they will also make a cancellable progress popup
* cleaned up how the autocomplete entry sends some of its signals to other parts of the program
* did some misc help and code edits/refactoring, including brushing up the Windows install section with more advanced options
* removed the 'hydrus zooms big bad' warning from the 'media' options page. hydrus zooms big good now!

### some database stuff
* tl;dr: database cleans up after itself better now
* some users have had trouble with database journal files (the 'wal' files in your db directory) on certain clients getting huge after lots of work, multiple GB, and causing the OS a headache if the journal is doing work through a computer sleep. these journals are 'supposed' to checkpoint and clean themselves up naturally, but I think a busy database chokes them. therefore, I have improved the hydrus maintenance this week: 1) the 'journal size limit' PRAGMA, which applies softly after every 30 seconds or so, is now 128MB down from 1GB. 2) databases in PERSIST (rare) mode will now specifically zero out their journal fifteen minutes. 3) databases in WAL mode (the default), in addition to regular PASSIVE checkpointing now every five minutes, will force an additional TRUNCATE checkpoint every fifteen. this should force a regular full flush and maybe help some other problems like gigantic memory bloat the same users sometimes saw. if you are a very advanced user and do active debug on the database while hydrus is using it, please note this new TRUNCATE command is aggressive and may block itself or you inconveniently. let me know how you get on!
* moved the recent 'be careful of usb drives' section in 'installing' help to 'help my db is broke.txt'. it is very likely this problem was related to the above WAL stuff, and it was not just usb drives, I rewrote it as generalised help for anyone who gets 'delayed write failed' errors at the OS level
* massively optimised several critical duplicate files filtering methods if the current location context has more than one file domain, and I think I cleared out the basic 'get duplicate info for this file' call of all slow calls in complex location contexts
* the repair routine that regenerates mapping caches if any tables are missing on boot is now more reliable and covers the entirety of the mappings cache system using the new modules system. it also now regenerates just for the tag services with missing tables, not the whole cache
* if multiple types of mapping cache tables are missing on boot, and multiple waves of regenerations covering different areas are planned, duplicate regenerations will now be skipped

## [Version 485](https://github.com/hydrusnetwork/hydrus/releases/tag/v485)

### multiple local file services
* multiple local file services are now available for everyone! you no longer need to be in advanced mode to create them. all are welcome, but in terms of skill level, I most recommend it for users who are comfortable with tag siblings and parents
* the tl;dr: you can now have more than one 'my files', which lets you put things in isolated locations
* I wrote a proper help document on multiple local file services--what they are, how they work, my recommendations, and a bit of extra info about hydrus file search in general, right here: https://hydrusnetwork.github.io/hydrus/advanced_multiple_local_file_services.html
* file searches in 'multiple locations' on large clients are now massively faster in almost all situations. the only place multiple location searches are still slow is whenever the duplicates system (system:file relationships) comes into play

### misc
* in the page tab menu, you can now sort pages by total file size
* the 'force system:limit for all searches' option is moved from the 'speed and memory' to 'search' panel
* when files download from sites, if the raw file is served by cloudflare and has a timestamp radically different to a parsed source time, that CF timestamp is saved under a different domain rather than overwriting the original domain timestamp. this seemed to affect danbooru on about 1 in 10-20 files. note this does not change much at the moment, but when you can see and sort on individual domain modified dates, this should improve the sort
* updated the 'installing' help to talk about bad install locations for the database. network locations are bad, and thanks to user reports, we now know USB drives can be bad if the database is busy when the OS goes to sleep
* if a 'database is malformed' error occurs on boot, the client now recognises it and points the user to 'install_dir/db/help my db is broke.txt' for the next steps

### boring code cleanup
* another 60KB or so of code pulled out of ClientDB.py:
* created a new database module for url mappings and refactored various fetch and update routines to it
* created a new database module for some rich file metadata and refactored some file filtering, history, and status testing code to it
* created new database module for file searching and moved all tag-based file searching code to it
* moved several other misc methods down to database modules

## [Version 484](https://github.com/hydrusnetwork/hydrus/releases/tag/v484)

### misc
* fixed the simple delete files dialog for trashed files. due to a logical oversight, the simple version was not testing 'trashed' status and so didn't see anything to permanently delete and would immediately dump out. now it shows the option for trashed files again, and if the selection includes trash and non-trash, it shows multiple options
* fixed an error in the 'show next pair' logic of the new duplicate filter queue where if it needed to auto-skip through the end of the current batch and load up the next batch (issues #1139, #1143)
* a new setting on _options->media_ now lets you set the scanbar to be small and simple instead of hidden when the mouse is moved away. I liked this so much personally it is now the default for new users. try it out!
* the media viewer's taglist hover window will now never send a mouse wheel event up to the media viewer canvas (so scrolling the tags won't accidentally do previous/next if you hit the end of the list scrollbar)
* I think I have fixed the bug where going on the media viewer from borderless fullscreen to a regular window would not trigger a media container resize if the media perfectly fitted the ratio of the fullscreen monitor!
* the system tray icon now has minimise/restore entries
* to reduce confusion, when a content parser vetoes, it now prepends the file import 'note' with 'veto: '
* the 'clear service info cache' job under _database->regenerate_ is renamed to 'service info numbers' and now has a service selector so you can, let's say, regen your miscounted 'number of files in trash' count without triggering a complete recount of every single mapping on the PTR the next time you open review services
* hydrus now recognises most (and maybe all) windows executables so it can discard them from imports confidently. a user discovered an interesting exe with embedded audio that ffmpeg was seeing as an mp3--this no longer occurs
* the 'edit string conversion step' dialog now saves a new default (which is used on 'add' events) every time you ok it. 'append extra text' is no longer the universal default!
* the 'edit tag rule' dialog in the parsing system now starts with the tag name field focused
* updated 'getting started/installing' help to talk more about mpv on Linux. the 'libgmodule' problem _seems_ to have a solid fix now, which is properly written out there. thanks to the users who figured all this out and provided feedback

### multiple local file services
* the media viewer menu now offers add/move actions just like the thumb grid
* added a new shortcut action that lets you specify add/move jobs. it is available in the media shortcut set and will work in the thumbnail grid and the media viewer
* add/move is now nicer in edge cases. files are filtered better to ensure only local media files end up in a job (e.g. if you were to try to move files out of the repository update domain using a shortcut), and 'add' commands from trashed files are naturally and silently converted to a pure undelete

### boring code cleanup
* refactored the UI side of multiple local file services add/move commands. various functions to select, filter, and question the user on actions are now pulled to a separate simple module where other parts of the UI can also access them, and there is now just one isolated pipeline for file service add/move content updates.
* if a 'move' job is started without a source service and multiple services could apply, the main routine will now ask the user which to use using a selector that shows how many files each choice will affect
* also rewrote the add/move menu population code, fixed a couple little issues, and refactored it to a module the media viewer canvas can use
* wrote a new menu builder that can place a list of items either as a single item (if the list is length 1), or make a submenu if there are more. it drives the new add/move commands and now the behind the scenes of all other service-based menu population

## [Version 483](https://github.com/hydrusnetwork/hydrus/releases/tag/v483)

### multiple local file services
* the multiple local file services feature is ready for advanced users to test out! it lets you have more than one 'my files' service to store things, which will give us some neat privacy and management tools in future. there is no nice help for this feature yet, and the UI is still a little non-user-friendly, so please do not try it out unless you have been following it. and, while this has worked great in all testing, I generally do not recommend it for heavy use on a real client either, just in case something does go wrong. with those caveats, hit up _manage services_ in advanced mode, and you can now add new 'local file domain' services. it is possible to search, import to, and migrate files between these and everything basically works. I need to do more UI work to make it clear what is going on (for instance, I think we'll figure out custom icons or similar to show where files are), and some more search tech, and write up proper help, and figure out easy client merging so users can combine legacy clients, but please feel free to experiment wildly on a fresh client or carefully on your existing one
* if you have more than one local file service, a new 'files' or 'local services' menu on thumbnail right-click handles duplicating and moving across local services. these actions will preserve original import times (e.g. if you move from A to B and then back to A), so they should be generally non-destructive, but we may want to add some advanced tools in future. let me know how this part goes--I think we'll probably want a different status than 'deleted from A' when you just move A->B, so as not to interfere with some advanced queries, but only IRL testing will show it
* if you have a 'file import options' that imports files to multiple local services but the file import is 'already in db', the file import job will now examine if and where the file is still needed and send content update calls to fill in the gaps
* the advanced delete files dialog now gives a new 'delete from all and send to trash' option if the file is in multiple local file domains
* the advanced delete files dialog now fully supports file repositories
* cleaned up some logic on the 'remember action' option of the advanced file deletion dialog. it also supports remembering specific file domains, not just the clever commands like 'delete and leave no record'. also this dialog no longer places the 'suggested' file service at the top of the radio button list--instead it selects that 'suggested' if there is no 'remember action' initial selection applicable. the suggested file service is now also set by the underlying thumbnail grid or media canvas if it has a simple one-service location context
* the normal 'non-advanced' delete files dialog now supports files that are in multiple local file services. it will show a part of the advanced dialog to let you choose where to delete from

### misc
* thanks to user submissions, there is a bit more help docs work--for file search, and for some neat new 'mermaid' svg diagrams in siblings/parents, which are automatically generated from a markup and easy to edit
* with the new easy-to-edit mermaid diagrams, I updated the unhelpful and honestly cringe examples in the siblings and parents help to reflect real world PTR data and brushed up all the text in the top sections
* just a small thing--the 'pages' menu and the page picker dialog now both say 'file search' to refer to a page that searches files. previously, 'search' or 'files' was used in different places
* completely rewrote the queue code behind the duplicate filter. an ancient bad idea is now replaced with something that will be easier to work with in future
* you can now go 'back' in the duplicate filter even when you have only done skips so far
* the 'index string' of duplicate filters, where it says 53/100, now also says the number of decisions made
* fixed some small edge case bugs in duplicate filter forward/backward move logic, and fixed the recent problem with going back after certain decisions
* updated the default nijie.info parser to grab video (issue #1113)
* added in a user fix to the deviant art parser
* added user-made Mega URL Classes. hydrus won't support Mega for a long while, but it can recognise and categorise these URLs now, presenting them in the media viewer if you want to open them externally
* fixed Exif image rotation for images that also have ICC Profiles. thanks to the user who provided great test images here (issue #1124)
* hitting F5 or otherwise saying 'refresh' explicitly will now turn a search page that is currently in 'searching paused' to 'searching immediately'. previously it silently did nothing
* the 'current file info' in the media window's top hover and the status bar of the main window now ignores Deletion reason, and also file modified date if it is not substantially different from another timestamp already stated. this data can still be seen on the file's right-click menu's expanded info lines off the top entry. also, as a small cleanup, it now says 'modified' and 'archived' instead of 'file modified/archived', just to save some more space
* like the above 'show if interesting' check for modified date, that list of file info texts now includes the actual import time if it is different than other timestamps. (for instance, if you migrate it from one service to another some time after import)
* fixed a sort error notification in the edit parser dialog when you have two duplicate subsidiary parsers that both have vetoes
* fixed the new media viewer note display for PyQt5
* fixed a rare frame-duration-lookup problem when loading certain gifs into the media viewer

### boring code cleanup
* cleaned up search signalling UI code, a couple of minor bugs with 'searching immediately' sometimes not saving right should be fixed
* the 'repository updates' domain now has a different service type. it is now a 'local update file domain' rather than a 'local file domain', which is just an enum change but marks it as different to the regular media domains. some code is cleaned up as a result
* renamed the terms in some old media filtering code to make it more compatible with multiple local file services
* brushed up some delete code to handle multiple local file services better
* cleaned up more behind the scenes of the delete files dialog
* refactored ClientGUIApplicationCommand to the widgets module
* wrote a new ApplicationCommandProcessor Mixin class for all UI elements that process commands. it is now used across the program and will grow in responsibility in future to unify some things here
* the media viewer hover windows now send their application commands through Qt signals rather than the old pubsub system
* in a bunch of places across the program, renamed 'remote' to 'not local' in file status contexts--this tends to make more sense to people at out the gate
* misc little syntax cleanup

## [Version 482](https://github.com/hydrusnetwork/hydrus/releases/tag/v482)

### misc
* fixed the stupid taglist scrolled-click position problem--sorry! I have a new specific weekly test for this, so it shouldn't happen again (issue #1120)
* I made it so middle-clicking on a tag list does a select event again
* the duplicate action options now let you say to archive both files regardless of their current archive status (issue #472)
* the duplicate filter is now hooked into the media prefetch system. as soon as 'A' is displayed, the 'B' file will now be queued to be loaded, so with luck you will see very little flicker on the first transition from A->B.
* I updated the duplicate filter's queue to store more information and added the next pair to the new prefetch queue, so when you action a pair, the A of the next pair should also load up quickly
* boosted the default sizes of the thumbnail and image caches up to 32MB and 384MB (from 25/150)  and gave them nicer 'bytes quantity' widgets in the options panel
* when popup windows show network jobs, they now have delayed hide. with luck, this will make subscriptions more stable in height, less flickering as jobs are loaded and unloaded
* reduced the extremes of the new auto-throttled pending upload. it will now change speed slower, on less strict of a schedule, and won't go as fast or slow max
* the text colour of hyperlinks across the program, most significantly in the top-right media hover window, can now be customised in QSS. I have set some ok defaults for all the QSS styles that come with the client, if you have a custom QSS, check out my default to see what you need to do. also hyperlinks are no longer underlined and you can't 'select' their text with the mouse any more (this was a weird rich-text flag)
* the client api and local booru now have a checkbox in their manage services panel for 'normie-friendly welcome page', which switches the default ascii art for an alternate
* fixed an issue with the hydrus server not explicitly saying it is utf-8 when rendering html
* may have fixed some issues with autocomplete dropdowns getting hung up in the wrong position and not fixing themselves until parent resize event or similar

### code cleanup
* about 80KB of code moved out of the main ClientDB.py file:
* refactored all combined files display mappings cache code from the code database to a new database module
* refactored all combined files storage mappings cache code from the code database to a new database module
* refactored all specific storage mappings cache code from the code database to a new database module
* more misc refactoring of tag count estimate, tag search, and other code down to modules
* hooked up specific display mappings cache to the repair system correctly--it had been left unregistered by accident
* some misc duplicate action options code cleanup
* migrated some ancient pause states--repository, subscriptions, import&export folders--to the newer options structure
* migrated the image and thumbnail cache sizes to the newer options structure
* removed some ancient db and dialog code from the retired dumper system

## [Version 481](https://github.com/hydrusnetwork/hydrus/releases/tag/v481)

### fixes and improvements after last week's hover and note work
* fixed the text colour behind the top middle hover window
* stopped clicks on the taglist and hover greyspace being duplicated up to the main canvas (this affected the archive/delete and duplicate filter shortcuts)
* fixed the background colour of the hover windows when using non-default stylesheets
* fixed the notes hover window--after having shown some notes--could then lurk in the top-left corner when it should have been hidden completely
* cleaned up some old focus test logic that weas used when hovers were separate windows
* rewrote how each note panel in the new hover is stored. a bunch of sizing and event handling code is less hacked
* significantly improved the accuracy of the 'how high should the note window be?' calculation, so notes shouldn't spill over so much or have a bunch of greyspace below
* right- or middle-clicking a note now hides its text. repeat on its name to restore. this should persist through an edit, although it won't be reflected in the background atm. let's see how it works as a simple way to quickly browse a whole stack of big notes
* a new 'notes' option panel lets you choose if you want the text caret to start at the beginning or end of the document when editing
* you can now double-click a note tab in 'edit notes' to rename the note. some styles may let you double-click in note greyspace to create a new note, but not all will handle this (yet)
* as an experiment, all the buttons on the media viewer hover windows now do not take focus when you click them. this should let you, for instance, click a duplicate filter processing button and then use the arrow keys and space to continue to navigate. previously, clicking a button would focus it, and navigation keys would be intercepted to navigate the 'form' of the buttons on the hover window. you can still focus buttons with tab. if this affects you, let me know how this goes!

### misc
* added checkboxes to _options->gui pages_ to control whether ctrl- and shift- selects will highlight media in the preview viewer. you can choose to only do it for files with no duration if you prefer
* the 'advanced mode' tag autocomplete dropdown now has 'OR' and 'OR*' buttons. the former opens a new empty OR search predicate in the edit dialog, the latter opens the advanced text parser as before
* the edit OR predicate panel now starts wider and with the text box having focus
* hydrus is now more careful about deciding whether to make a png or a jpeg thumbnail. now, only thumbnails that have an alpha channel with interesting data in it are saved to png. everything else is jpeg
* when uploading to a repository, the client will now slow down or speed up depending on how fast things are going. previously it would work on 100 mappings at a time with a forced 0.1s wait, now it can vary between 1-1,000 weight
* just to be clean, the current files line on the file history chart now initialises at 0 on your first file import time
* fixed a bug in 'if file is missing, remove record' file maintenance job. if none of the files yet scanned had any urls, it could error out since the 'missing and invalid files' directory was yet to be created
* linux users who seem to have mpv support yet are set to use the native viewer will get a one-time popup note on update this week just to let them know that mpv is stable on linux now and how to give it a go
* the macOS App now spits out any mpv import errors when you hit _help->about_, albeit with some different text around it
* I maybe fixed the 'hold shift to not follow a dragged page' tech for some users for whom it did not work, but maybe not
* thanks to a user, the new website now has a darkmode-compatible hydrus favicon
* all file import options now expose their new 'destination locations' object in a new button in the UI. you can only set one destination for now ('my files', obviously), but when we have multiple local file services, you will be able to set other/multiple destinations here. if you set 'nothing', the dialog will moan at you and stop you from ok-ing it.
* I have updated all import queues and other importing objects in the program to pause their file work with appropriate error messages if their file import options ever has a 'nothing' destination (this could potentially happen if future after a service deletion). there are multiple layers of checks here, including at the final database level
* misc code cleanup

### client api
* added 'create_new_file_ids' parameter to the 'file_metadata' call. this governs whether the client should make a new database entry and file_id when you ask about hashes it has never seen before. it defaults to **false**, which is a change on previous behaviour
* added help talking about this
* added a unit test to test this
* added archive timestamp and hash hex sort enum definitions to the 'search_files' client api help
* client api version is now 31

## [Version 480](https://github.com/hydrusnetwork/hydrus/releases/tag/v480)

### file notes and media viewer hover windows
* file notes are now shown on the media viewer! this is a first version, pretty ugly, and may have font layout bugs for some systems, but it works. they hang just below the top-right hover, both in the canvas background and with their own hover if you mouseover. clicking on any note will open 'edit notes' on that note
* the duplicate filter's always-on hover _should_ slide out of the way when there are many notes
* furthermore, I rewrote the backend of hover windows. they are now embedded into the media viewer rather than being separate frameless toolbar windows. this should relieve several problems different users had--for instance, if you click a hover, you now no longer lose focus on the main media viewer window. I hacked some of this to get it to work, but along the way I undid three other hacks, so overall it should be better. please let me know how this works for you!
* fixed a long time hover window positioning bug where the top-right window would sometimes pop in for a frame the first time you moved the mouse to the top middle before repositioning and hiding itself again
* removed the 'notes' icon from the top right hover window
* refactored a bunch of canvas background code

### client api
* search_files/get_thumbnail now returns image/jpeg or image/png Content-Type. it _should_ be super fast, but let me know if it lags after 3k thumbs or something
* you can now ask for CBOR or JSON specifically by using the 'Accept' request header, regardless of your own request Content-Type (issue #1110)
* if you send or ask for CBOR but it is not available for that client, you now get a new 'Not Acceptable' 406 response (previously it would 500 or 200 but in JSON)
* updated the help regarding the above and wrote some unit tests to check CBOR/JSON requests and responses
* client api version is now 30

### misc
* added a link to 'Hyshare', at https://github.com/floogulinc/hyshare, to the Client API help. it is a neat way to share galleries with friends, just like the the old 'local booru'
* building on last week's shift-select improvement, I tweaked it and shift-select and ctrl-select are back to not setting the preview focus. you can ctrl-click a bunch of vids in quick silence again
* the menu on the 'file log' button is now attached to the downloader page lists and the menu when you right-click on the file log panel. you can now access these actions without having to highlight a big query
* the same is also true of the search/check log!
* when you select a new downloader in the gallery download page, the keyboard focus now moves immediately to the query text input box
* tweaked the zoom locking code in the duplicate filter again. the 'don't lock that way if there is spillover' test, which is meant to stop garbage site banners from being hidden just offscreen, is much more strict. it now only cares about 10% or so spillover, assuming that with a large 'B' the spillover will be obvious. this should improve some odd zoom locking situations where the first pair change was ok and the rest were weird
* if you exit the client before the first session loads (either it is really huge or a problem breaks/delays your boot) the client will not save any 'last/exit session' (previously, it was saving empty here, requiring inconvenient load from a backup)
* if you have a really really huge session, the client is now more careful about not booting delayed background tasks like subscriptions until the session is in place
* on 'migrate database', the thumbnail size estimate now has a min-max range and a tooltip to clarify that it is an estimate
* fixed a bug in the new 'sort by file hash' pre-sort when applying system:limit

## [Version 479](https://github.com/hydrusnetwork/hydrus/releases/tag/v479)

### misc
* when shift-selecting some thumbnails, you can now reverse the direction of the select and what you just selected will be deselected, basically a full undo (issue #1105)
* when ctrl-selecting thumbnails, if you add to the selection, the file you click is now focused and always previewed (previously this only happened if there was no focused file already). this is related to the shift-select logic above, but it may be annoying when making a big ctrl-selection of videos etc.. so let me know and I can make this more clever if needed
* added file sort 'file->hash', which sorts pseudorandomly but repeatably. it sounds not super clever, but it will be useful for certain comparison operations across clients
* when you hit 'copy->hash' on a file right-click, it now shows the sha256 hash for quick review
* in the duplicate filter, the zoom locking tech now works better™ when one of the pair is portrait and the other landscape. it now tries to select either width or height to lock both when going AB and BA. it also chooses the 'better' of width or height by choosing the zoom that'll change the size less radically. previously, it could do width on AB and height on BA, which lead to a variety of odd situations. there are probably still some issues here, most likely when one of the files almost exactly fills the whole canvas, so let me know how you get on
* webps with transparency should now load correct! previously they were going crazy in the transparent area. all webps are scheduled a thumbnail regen this week
* when import folders run, the count on their progress bar now ignores previous failed and ignored entries. it should always start 0, like 0/100, rather than 20/120 etc...
* when import folders run, any imports where the status type is set to 'leave the file alone' is now still scanned at the end of a job. if the path does not exist any more, it is removed from the import list
* fixed a typo bug in the recent delete code cleanup that meant 'delete files after export' after a manual export was only working on the last file in the selection. sorry for the trouble!
* the delete files dialog now starts with keyboard focus on the action radiobox (it was defaulting to ok button since I added the recent panel disable tech)
* if a network job has a connection error or serverside bandwidth block and then waits before retrying, it now checks if all network jobs have just been paused and will not reattempt the connection if so (issue #1095)
* fixed a bug in thumbnail fallback rendering
* fixed another problem with cloudscraper's new method names. it should work for users still on an old version
* wrote a little 'extract version' sql and bat file for the db folder that simply pull the version from the client.db file in the same directory. I removed the extract options/subscriptions sql scripts since they are super old and out of date, but this general system may return in future

### file history chart
* added 'archive' line to the file history chart. this isn't exactly (current_count - inbox_count), but it pretty much is
* added a 'show deleted' checkbox to the file history chart. it will recalculate the y axis range on click, so if you have loads of deleted files, you can now hide them to see current better
* improved the way data is aggregated in the file history chart. diagonal lines should be reduced during any periods of client import-inactivity, and spikes should show better
* also bumped the number of steps up to 8,000, so it should look nice maximised on a 4k
* the file history chart now remembers its last size and position--it has an entry under options->gui

### client api
* thanks to a user, the Client API now accepts any file_id, file_ids, hash, or hashes as arguments in any place where you need to specify a file or files
* like 'return_hashes', the 'search_files' command in the Client API now takes an optional 'return_file_ids' parameter, default true, to turn off the file ids if you only want hashes
* added 'only_return_basic_information' parameter, default false, to 'get_metadata' call, which is fast for first-time requests (it is slim but not well cached) and just delivers the basics like resolution and file size
* added unit tests and updated the help to reflect the above
* client api version is now 29

### help
* split up the 'more files' help section into 'powerful searching' and 'exporting files', both still under the 'next steps' section
* moved the semi-advanced 'OR' section from 'tags' to 'searching'
* brushed up misc help
* a couple of users added some misc help updates too, thank you!

### misc boring cleanup
* cleaned up an old wx label patch
* cleaned up an old wx system colour patch
* cleaned up some misc initialisation code

## [Version 478](https://github.com/hydrusnetwork/hydrus/releases/tag/v478)

### misc
* if a file note text is crazy and can't be displayed, this is now handled and the best visual approximation is displayed (and saved back on ok) instead
* fixed an error in the cloudflare problem detection calls for the newer versions of cloudscraper (>=1.2.60) while maintaining support for the older versions. fingers crossed, we also shouldn't repeat this specific error if they refactor again

### file history chart updates
* fixed the 'inbox' line in file history, which has to be calculated in an odd way and was not counting on file imports adding to the inbox
* the file history chart now expands its y axis range to show all data even if deleted_files is huge. we'll see how nice this actually is IRL
* bumped the file history resolution up from 1,000 to 2,000 steps
* the y axis _should_ now show localised numbers, 5,000 instead of 5000, but the method by which this occurs involves fox tongues and the breath of a slighted widow, so it may just not work for some machines

### cleanup, mostly file location stuff
* I believe I have replaced all the remaining surplus static 'my files' references with code compatible with multiple local file services. when I add the capability to create new local file services, there now won't be a problem trying to display thumbnails or generate menu actions etc... if they aren't in 'my files'
* pulled the autocomplete dropdown file domain button code out to its own class and refactored it and the multiple location context panel to their own file
* added a 'default file location' option to 'files and trash' page, and a bunch of dialogs (e.g. the search panel when you make a new export folder) and similar now pull it to initialise. for most users this will stay 'my files' forever, but when we hit multiple local file services, it may want to change
* the file domain override options in 'manage tag display and search' now work on the new location system and support multple file services
* in downloaders, when highlighting, a database job that does the 'show files' filter (e.g. to include those in trash or not) now works on the new location context system and will handle files that will be imported to places other than my files
* refactored client api file service parsing
* refactored client api hashes parsing
* cleaned a whole heap of misc location code
* cleaned misc basic code across hydrus and client constant files
* gave 'you don't want the server' help page a very quick pass

### client api
* in prep for multiple local file services, delete_files now takes an optional file_service_key or file_service_name. by default, it now deletes from all appropriate local services, so behaviour is unchanged from before without the parameter if you just want to delete m8
* undelete files is the same. when we have multiple local file services, an undelete without a file service will undelete to all locations that have a delete record
* delete_files also now takes an optional 'reason' parameter
* the 'set_notes' command now checks the type of the notes Object. it obviously has to be string-to-string
* the 'get_thumbnail' command should now never 404. if you ask for a pdf thumb, it gives the pdf default thumb, and if there is no thumb for whatever reason, you get the hydrus fallback thumbnail. just like in the client itself
* updated client api help to talk about these
* updated the unit tests to handle them too
* did a pass over the client api help to unify indent style and fix other small formatting issues
* client api version is now 28

## [Version 477](https://github.com/hydrusnetwork/hydrus/releases/tag/v477)

### misc
* the network engine now parses the 'last-modified' response header for raw files. if this time is earlier than any parsed source time, it is used as the source time and saved to the new 'domain modified time' system. this provides decent post time parsing for a bunch of sites by default, which will also help for subscription timing and similar
* to get better apng duration, updated the apng parser to count up every frame duration separately. previously, if ffmpeg couldn't figure it out, I was just defaulting to 24 fps and estimating. now it is calculated properly, and for variable framerate apngs too. all apngs are scheduled for a metadata regen this week. thanks to the user who submitted some long apngs where this problem was apparent
* fixed a bug in the network engine filter that figures out url class precedence. url classes with more parameters were being accidentally sorted above those with more path components, which was messing with some url class matching and automatic parser linking
* improved the message when an url class fails to match because the given url has too few path components
* fixed a time delta display bug where it could say '2 years, 12 months' and similar, which was due to a rounding issue on 30 day months and the, for example, 362nd day of the year
* fixed a little bug where if you forced an archive action on an already archived file, that file would appear to get a fake newer archived timestamp in UI until you restarted
* updated the default nitter parsers to pull a creator tag. this seemed to not have been actually done when previously thought
* the image renderer now handles certain broken files better, including files truncated to 0 size by disk problem. a proper error popup is made, and file integrity and rescan jobs are scheduled

### file history chart
* for a long time, a user has been generating some cool charts on file history (how many files you've had in your db over time, how many were deleted, etc...) in matplotlib. you may have run his script before on your own database. we've been talking a while about integrating it into the client, and this week I finally got around to it and implemented it in QtCharts. please check out the new 'view file history' underneath Mr Bones's entry in the help menu. I would like to do more in this area, and now I have learned a little more about QtCharts I'd like to revisit and polish up my old bandwidth charts and think more about drawing some normal curves and so on of other interesting data. let me know what you think!
* I did brush up a couple things with the bandwidth bar chart already, improving date display and the y axis label format

### client api
* a user has written several expansions for the client api. I really appreciate the work
* the client api now has note support! there is a new 'add notes' permission, 'include_notes' parameter in 'file_metadata' to fetch notes, and 'set_notes' and 'delete_notes' POST commands
* the system predicate parser now supports note system preds
* hydrus now supports bigger GET requests, up to 2 megabytes total length (which will help if you are sending a big json search object via GET)
* and the client api now supports CBOR as an alternate to JSON, if requested (via content-type header for POST, 'cbor' arg for GET). CBOR is basically a compressed byte-friendly version of JSON that works a bit faster and is more accessible in some lower level languages
* cbor2 is now in the requirements.txt(s), and about->help shows it too
* I added a little api help on CBOR
* I integrated the guy's unit tests for the new notes support into the main hydrus test suite
* the client api version is now 27
* I added links to the client api help to this new list of hydrus-related projects on github, which was helpfully compiled by another user: https://github.com/stars/hydrusnetwork/lists/hydrus-related-projects
