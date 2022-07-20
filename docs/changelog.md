# changelog

!!! note
    This is the new changelog, only the most recent builds. For all versions, see the [old changelog](old_changelog.html).

## [Version 492](https://github.com/hydrusnetwork/hydrus/releases/tag/v492)

### sort and collect updates
* for big brain users, the collect control now has a tag domain button. it only shows if you are in advanced mode (issue #572)
* the sort control also has a tag domain button hidden behind advanced mode. it applies to system:num tags and namespace sorting
* the collect control now appears on all import pages

### archived file delete lock
* the duplicate processing action code now no longer archives files that are due for deletion right before that deletion. this was hitting the archive delete lock
* if archive delete lock is on and the 'other' file in the duplicate filter is archived, the option to 'this is better, delete the other' is now disabled
* if you attempt to delete a delete-locked file during normal browsing, or if an automatic system like export folders wants to but fails on some, a popup is now made with a button to show the files that were filtered out so you can review the situation and fix it if you want
* I am considering adding a dialog to say 'hey, this is locked, want to send back to inbox?' to fix these situations in a nice way, but I think this is probably a bad idea in terms of workflow, design, and my sanity given all the edge cases and potential future expansions of lock rules. maybe I'll add a simple 'delete and override lock checks' option, but a lock is a lock tbh. for now, I will focus on this better UI feedback of currently delete-locked files and make it simpler for humans to remove any locks

### misc
* using black magic, I have made it so the shortcuts for 'move left/right one page' 'and 'move home/end' do not dip down to the lowest level of a neighbouring page of pages for the next command. it now stays on the current tab level for three seconds after the most recent move command. this works in testing but may be jank in some IRL situations, so if this matters to you, let me know how it works out
* fixed a bug in 'do a full metadata resync' that meant unprocessed row orphans were not being deleted, which lead to lingering 1950/2000-style processed gauges that didn't actually cause any work to be done on 'process now'
* the duplicate filter now shows if one or both files have an icc profile. for now the score for this is always 0, neutral
* I think I have reduced general lag on some busy clients

### code cleaning and minor fixes
* refactored file viewing stats management to a new database module
* refactored file physical storage management to a new database module
* cleaned up an ugly bridge that made inbox/archive work and moved it all to a clean new separate database module
* improved some client file physical storage repair code, both in how it repairs and how it recovers in the current boot
* updated the yes/no dialog texts when you apply 'not related' or 'alternates' to a selection
* added a bunch of tooltips to the 'speed and memory' options panel. also clarified the example image sizes in number of pixels
* improved how my grid layout propagates tooltips from the widget to the text when the widget is compound and in its own layout
* consolidated where the delete lock test occurs to just one location for db, gui
* added infrastructure to filter and report delete-locked files. callers no longer care about specific lock rules, opening this up to future expansion
* cleaned and simplified some duplicate action processing code
* cleaned up some file collect code, optimised it a bit too
* the sort control now only changes sort type on mouse wheel events if the mouse is over that button
* renamed 'tag search context' to 'tag context' across the program, mirroring a recent change with the location context, and gave it some bells and whistles. in future, the tag context will hold multiple tag services
* wrote a new button to edit tag contexts

## [Version 491](https://github.com/hydrusnetwork/hydrus/releases/tag/v491)

### system predicates
* the advanced OR input, where you can type tags in complicated logical expressions, now supports system predicates! most system predicates are supported using their typical display strings. it uses the same engine as the client api, so check the examples here https://hydrusnetwork.github.io/hydrus/developer_api.html#get_files_search_files sorry for the delay here
* the advanced input also runs tags better through the hydrus tag 'cleaning' process, so things like whitespace between the namespace colon and the subtag are cleaned up correctly, and invalid tags should be excluded
* it also starts with the keyboard focus in the text input
* and I think I fixed an issue with '!'', 'not', or '-' negation prefixes not parsing
* highlighted the example parseable system predicate texts in the Client API help, and added 'last viewed' to it

### misc
* altering your services in _manage services_ no longer causes a full page refresh for all currently open search pages
* in a related thing, if you click the file or tag domain of a file search page to be the same as it just was, you no longer get a page refresh
* the rating widgets now show their current rating value on their tooltips
* when setting a numerical rating by a drag, it no longer matters if your mouse strays above or below the widget--it will still set
* the String Processing system has a new 'String Tag Filter' processing step. this applies the normal tag filtering object to your list of strings and also performs the hydrus 'tag cleaning' process on them, making them all lowercase and trimming whitespace and so on
* the sibling/parent sync is now even more polite when told to do work in 'normal' time. this has been hitting a lot of new users really hard, so it should now really trickle work during normal time, throttling down when it hits a bump to avoid stunlocking you but also responding quickly to recent changes if you are fully synced
* the database repair code is now better at healing damaged fast-text-search (FTS) tables. previously, in cases of partial damage to the virtual table, the repair code would error out
* fixed a bug where certain search predicate calendar dates that are acceptable in Linux but not in Windows caused Windows to fail to load the session. if you put in 1965 as a search date, it should now revert to the current time one next load etc...
* the test to see if a directory is writeable-to is improved and now handles Windows's Program Files directory correctly
* improved how the boot scripts handle incorrect/bad database directory paths. the error handling works better, and it figures out a fallback location for crash.log better
* a new button on 'review services' now lets advanced users copy the service key to the clipboard
* the migrate tags dialog now lists file repositories, ipfs services, and 'all my files' as potential file filter domains
* when checking it has space for a large transaction like a vacuum, hydrus now tries to check if you are running on a ramdisk or other severely space-limited temp dir and offers more text if this is true
* updated the '4chan style thread api parser' to handle posts with multiple files, which fixes tvchan.moe and probably anything else running NPFchan
* some logic testing around showing 'return to inbox' and the actual operation is fixed so it only applies to local files. in some weird advanced situations, you could previously send deleted files to inbox

### new import/export framework
* started a new modular metadata import/export pipeline. this thing starts out today by doing the work of newline-separated tags in a .txt sidecar file and will expand to do all sorts of metadata in other formats like JSON and XML. it will also, eventually, support arbitrary cross-type conversions like tags to urls or ratings to tags
* export folders now support '.txt' sidecar tag exporting!
* the '.txt' sidecar tag importing in import folders or manual imports is now handled by the new pipeline
* the '.txt' sidecar exporting in the manual export dialog is now handled by the new pipeline
* please expect the UI around '.txt' sidecar importing and exporting to change significantly in future. you'll be selecting different metadata types to import or export, make string processing steps to alter or filter what you get, and of course be able to compile it all into more complicated filetypes

### cleanup and refactoring
* mr bones gets two new columns to line up the numbers better
* a bunch of export code got moved around. created a new module 'exporting', and moved ClientExporting.py to it, renaming to ClientExportingFiles.py
* removed an old prototype for sidecar exporting and related plans for UI
* the 'missing file folders on boot' dialog now points users to 'help my media files are broke.txt'
* brushed up the 'help my x is broke.txt' documents in the database directory a little
* fixed some surplus double backslashes in the help
* a secret tiny label change/fix, let's see if anyone notices
* cleaned up how the rating widgets manage and update rating state. it was ancient bad code
* updated how different rating values are converted to UI text
* misc cleanup of some free space checking code
* fixed some bad quote characters in client api help JSON examples
* improved some error handling for uploading pending content and sped up file uploads a little

## [Version 490](https://github.com/hydrusnetwork/hydrus/releases/tag/v490)

### misc
* fixed a stupid bug that meant the image caches were initialising with default values (as under _speed and memory_) until you opened and OKed the options dialog (or did some other options-refresh events). sorry for the trouble, please enjoy some smoother image browsing.
* mr bones now shows more numbers, and in a neater table. it should be clearer what the percentages are for now, too
* the _manage->regenerate_ thumbnail menu has additional quick maintenance commands for presence and integrity checks and regenerating data in the similar files system
* wrote a new 'special duplicate' button for the edit shortcut set dialog. the list on this dialog doesn't allow duplicates (which meant the old 'duplicate' button was doing nothing), so this duplicates the current actions with 'incremented' shortcut keys. 'a' becomes 'b', 'ctrl+5' becomes 'ctrl+6', and so on. it doesn't always work, but if you want to make ten shortcuts for setting rating 1-10, this should help
* fixed an issue where the thumbnail banner text and the media viewer background text was not changing size or font according to QSS stylesheet rules (issue #1173)
* SIGTERM should now cause a clean program exit (previously it killed the GUI App but left some daemon threads alive for thirty seconds or more). unlike SIGINT, it will not ask you if you are sure you want to exit or if you would like to do shutdown maintenance--it just closes the client promptly
* fixed a bug in last week's importer page status improvements--the hard drive import page wasn't showing all the updates it should have
* brushed up some backup help

### file services
* fixed a bug where advanced users could set 'all known files'/'all known tags' on a search dropdown. this search domain is not supported
* in the archive/delete filter, if the current location is 'all my files' and the files being deleted are only in one local file domain, the surplus 'all my files' will no longer appear at the top of the filter's commit dialog
* the file services in the thumbnail select/remove menu are now sorted in the same order as the file domain button in search dropdowns
* the thumbnail select/remove menus now exclude 'all my files' and 'all local files' if those choices are redundant (e.g. if you only have files in 'my files', 'all my files' will be hidden)
* fixed some incorrect 'delete from x' actions appearing in thumbnail right-click menus

### orphan files
* there's a persistent processing bug some users have where some update files are missing but they won't redownload correctly. I think I fix that this week naturally so existing maintenance routines will now be able to fix it themselves after another round
* fixed some issues related to deleting files from the repository updates file domain.
* the 'clear orphan file records' maintenance command now fixes the 'all my files' umbrella services as well as the 'all local files' one. it also has nicer description, does some additional file-removal cleanup, and triggers a file recount if problems are found
* moved 'clear orphan files' to the 'files' maintenance menu

## [Version 489](https://github.com/hydrusnetwork/hydrus/releases/tag/v489)

### downloader pages
* greatly improved the status reporting for downloader pages. the way the little text updates on your file and gallery progress are generated and presented is overhauled, and tests are unified across the different downloader pages. you now get specific texts on all possible reasons the queue cannot currently process, such as the emergency pause states under the _network_ menu or specific info like hitting the file limit, and all the code involved here is much cleaner
* the 'working/pending' status, when you have a whole bunch of galleries or watchers wanting to run at the same time, is now calculated more reliably, and the UI will report 'waiting for a work slot' on pending jobs. no more blank pending!
* when you pause mid-job, the 'pausing - status' text is generated is a little neater too
* with luck, we'll also have fewer examples of 64KB of 503 error html spamming the UI
* any critical unhandled errors during importing proper now stop that queue until a client restart and make an appropriate status text and popup (in some situations, they previously could spam every thirty seconds)
* the simple downloader and urls downloader now support the 'delay work until later' error system. actual UI for status reporting on these downloaders remains limited, however
* a bunch of misc downloader page cleanup

### archive/delete
* the final 'commit/forget/back' confirmation dialog on the archive/delete filter now lists all the possible local file domains you could delete from with separate file counts and 'commit' buttons, including 'all my files' if there are multiple, defaulting to the parent page's location at the top of the list. this let's you do a 'yes, purge all these from everywhere' delete or a 'no, just from here' delete as needed and generally makes what is going on more visible
* fixed archive/delete commit for users with the 'archived file delete lock' turned on

### misc
* fixed a bug in the parsing sanity check that makes sure bad 'last modified' timestamps are not added. some ~1970-01-01 results were slipping through. on update, all modified dates within a week of this epoch will be retroactively removed
* the 'connection' panel in the options now lets you configure how many times a network request can retry connections and requests. the logic behind these values is improved, too--network jobs now count connection and request errors separately
* optimised the master tag update routine when you petition tags
* the Client API help for /add_tags/add_tags now clarifies that deleting a tag that does not exist _will_ make a change--it makes a deletion record
* thanks to a user, the 'getting started with files' help has had a pass
* I looked into memory bloat some users are seeing after media viewer use, but I couldn't reproduce it locally. I am now making a plan to finally integrate a memory profiler and add some memory debug UI so we can better see what is going on when a couple gigs suddenly appear

### important repository processing fixes
* I've been trying to chase down a persistent processing bug some users got, where no matter what resyncs or checks they do, a content update seems to be cast as a definition update. fingers crossed, I have finally fixed it this week. it turns out there was a bug near my 'is this a definition or a content update?' check that is used for auto-repair maintenance here (long story short, ffmpeg was false-positive discovering mpegs in json). whatever the case, I have scheduled all users for a repository update file metadata check, so with luck anyone with a bad record will be fixed automatically in the background within a few hours of background work. anyone who encounters this problem in future should be fixed by the automatic repair too. thank you very much to the patient users who sent in reports about this and worked with me to figure this out. please try processing again, and let me know if you still have any issues
* I also cleaned some of the maintenance code, and made it more aggressive, so 'do a full metadata resync' is now be even more uncompromising
* also, the repository updates file service gets a bit of cleanup. it seems some ghost files have snuck in there over time, and today their records are corrected. the bug that let this happen in the first place is also fixed
* there remains an issue where some users' clients have tried to hit the PTR with 404ing update file hashes. I am still investigating this

## [Version 488](https://github.com/hydrusnetwork/hydrus/releases/tag/v488)

### all misc this week
* the client now supports 'wavpack' files. these are basically a kind of compressed wav. mpv seems to play them fine too!
* added a new file maintenance action, 'if file is missing, note it in log', which records the metadata about missing files to the database directory but makes no other action
* the 'file is missing/incorrect' file maintenance jobs now also export the files' tags to the database directory, to further help identify them
* simplified the logic behind the 'remove files if they are trashed' option. it should fire off more reliably now, even if you have a weird multiple-domain location for the current page, and still not fire if you are actually looking at the trash
* if you paste an URL into the normal 'urls' downloader page, and it already has that URL and the URL has status 'failed', that existing URL will now be tried again. let's see how this works IRL, maybe it needs an option, maybe this feels natural when it comes up
* the default bandwidth rules are boosted. the client is more efficient these days and doesn't need so many forced breaks on big import lists, and the internet has generally moved on. thanks to the users who helped talk out what the new limits should aim at. if you are an existing user, you can change your current defaults under _network->data->review bandwidth usage and edit rules_--there's even a button to revert your defaults 'back' to these new rules
* now like all its neighbours, the cog icon on the duplicate right-side hover no longer annoyingly steals keyboard focus on a click.
* did some code and logic cleanup around 'delete files', particularly to improve repository update deletes now we have multiple local file services, and in planning for future maintenance in this area
* all the 'yes yes no' dialogs--the ones with multiple yes options--are moved to the newer panel system and will render their size and layout a bit more uniformly
* may have fixed an issue with a very slow to boot client trying to politely wait on the thumbnail cache before it instantiates
* misc UI text rewording and layout flag fixes
* fixed some jank formatting on database migration help

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
