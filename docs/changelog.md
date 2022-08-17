# changelog

!!! note
    This is the new changelog, only the most recent builds. For all versions, see the [old changelog](old_changelog.html).

## [Version 496](https://github.com/hydrusnetwork/hydrus/releases/tag/v496)

### note import options
* the client now has a system to set default note import options. it works exactly the same as default tag import options and shares the same UI, now named _network->downloaders->manage default import options_. you now set tag and/or note import options for a particular domain. I don't think you'll have to touch the note defaults until this system is really going and we learn more about what we want. I have made the initial defaults get all notes with some simple conflict resolution that won't discard any data
* all url pages, watchers, watcher pages, gallery queries, gallery downloader pages, and subscriptions now have a note import options. by default, they are 'default'
* the edit subscription dialog now has a button to set note import options _en masse_
* all the behind the scenes stuff that connects and powers these systems is done. note parsing now works! advanced users, especially downloader makers, are encouraged to play around with this for real. the remaining hurdle is still multiline parsing support
* notes now have a cleaning system before they are saved. to start with this week, they are now trimmed of leading or trailing whitespace or newlines

### Qt6
* the media viewer now draws correctly on UI scaled displays. If you are at >100% UI scale, it will now render images beautifully, using all available pixels, and state the correct zoom percentage. you look at a 4k image on a 4k screen, you now see 4k, no matter the UI scale. previously it was rendering at 100% UI scale coordinates and being nearest-neighbour scaled up
* after several sad hours banging my head against font metrics, I finally discovered the magic flag needed and have improved the font quality of the thumbnail banners when you boot the client with only 100% UI scale monitors. should be anti-aliased now, although if you have a semi-transparent banner colour it may look slightly jank for reasons I still need to investigate.
* I fixed the 'don't process the click that activates a media viewer into the shortcuts system' hook for Qt6 (and still working on Qt5). it is a little smarter now, too

### misc
* the new import options button is now an arrow-menu button. the secret right-click menu is no longer hidden. I also did some behind the scenes stuff to make it so all these arrow buttons spawn their menus on your cursor when you click, rather than hanging off the bottom-left corner of the button proper
* rating stars of all shapes are now anti-aliased
* greatly improved the shape of the 'star' rating star
* moved the 'checker options' button on watcher highlight panels down a bit. maybe it'll get integrated into other import options one day--I am still thinking about it
* archive/delete filters will not present 'delete from hard disk' as a final choice if the current domain is 'all local files'. I thought I fixed this a couple weeks ago, but there was a legacy issue
* fixed some real jank logic when setting the tag domain in autocomplete dropdown widgets. this got messed up a little with recent updates to file and tag domain searching. I reworked the signal path and fixed some weird update bugs and situations where you could seemingly set 'all known files'/'all known tags'

### boring code cleanup
* refactored all zoom code from the media viewer canvas to the media viewer container. the canvas no longer manages zoom numbers or container size
* refactored all container-position-tracking code from the media viewer canvas to the media viewer container and cleaned it
* updated the media viewer container to recognise UI scaling and adapt the stated zoom to reflect the raw pixels on screen, not the device independent coordinate system
* updated the native animation widget to recognise UI scaling, adapt its underlying renderer resolution appropriately, and draw that super-resolution frame to the canvas
* updated the static image widget to recognise UI scaling, adapt its tile coordinate system and resolution appropriately, and scatter the ethereal powder of the cleansed ancients across the QPainter in order to stitch the arbitrarily zoomed super-resolution tiles together on a sub-pixel canvas with no visible seams
* the animation and static image widgets also recognise changes in the current UI scale--if the current monitor changes or you move across monitors with differing UI scale
* updated some old pubsub update calls in the canvas code to Qt signals
* cleaned up some old const definitions in canvas code
* refactored and simplified some test methods related to the canvas container and media show actions
* cleaned up some old painter code and hacks to simpler alternatives
* cleaned a tangle of file/tag domain update code in the autocomplete dropdowns
* cleaned up some options getting/setting methods in the downloaders

## [Version 495](https://github.com/hydrusnetwork/hydrus/releases/tag/v495)

### Qt6
* if available, Qt6 is now the default. specifically, if the QT_API environment variable is not set, the default is now PySide6, and if that is not available, then PySide2 (Qt5). previously, the opposite was true
* fixed a bug in last week's File Import Options default update with the new 'default' FIOs always showing 'new' files on a gallery/watcher highlight. the Presentation Import Options and the check to see if the pending local file domains actually exist now correctly look up the 'default' FIOs
* Qt6 has much better UI scaling support than Qt5 for zooms other than 100%/200%. many Windows users are at 125%/150%, which revealed some pretty ugly thumbnails and thumb banner text in Qt6. thank you for the reports. I did my homework and read up on how this is _supposed_ to work and I have hacked pretty thumbnails at unusual UI scales. it also redraws itself correctly when I move from a 100% screen to a different one at 125%; let me know how you get on. I'm quite pleased
* the media viewer is still slightly borked at >100%. the fix will be slightly different, but I have a plan and hope to have it sorted for next week.
* fixed setting a mouse scroll wheel shortcut in shortcut options in Qt6
* as a reminder, as far as I know, Windows 7 cannot run Qt6. I will be dropping the Qt5 build in a few weeks, so if you are a Windows 7 user, have a think on what you want to do--either stop updating, move hydrus to a newer OS, or run from source on Win 7/Qt5

### note import options and note parsing
* note parsing is ready in parts. I am rolling them out for feedback from advanced users and hope to link it all up into a working system next week!
* the different 'x import options', previously file and tag import options, and this week adding 'note import options', are now edited through one combined button and dialog. this 'import options' button dynamically adjusts to deal with how many types of import options the importer has and will relabel and tooltip and right-click-menu itself appropriately
* this new button and multi-edit-panel show '(is default)' status in menus and tabs for quick referral
* if you want to play with note import options, check out the new EXPERIMENTAL menu option under _network->downloader components_. read the help and tooltips and let me know if I have missed anything simple, obvious, and important
* I have no default system for Note Import Options set up yet, so I have not added it for real. I will do something domain-based, similar to Tag Import Options.
* I did however write simple note parsing support. any Content Parser can now have a 'note' parsing type, with a note name. downloader creators, please feel free to play with this, although it isn't complicated and isn't plugged in yet. I think we should review what sites have parseable notes and plan for that rather than start implementing for real just yet. the main limitation is that the parsing system can't do multi-line results yet
* I'd like to see if I can get NIO defaults going next week, and this should suddenly all lock into place. multi-line parsing may be easy or a massive pain, I'm not sure yet

### misc
* added two new checkboxes to _options->files and trash_ to turn off the yes/no confirmation when you copy/move file across multiple local file services
* the 'overwrite this session?' confirmation dialog now says the session name you are overwriting
* fixed a bug where thumbnails were not immediately updating their banner text on changes to the summary generator objects in _options->tag presentation_
* moved the 'focus thumbnail in preview window' checkboxes from 'gui pages' options page to 'thumbnails'
* updated the text and enabled status of the 'BUGFIX: discord DnD' stuff in _options->gui_
* updated the job description texts in the file maintenance dialog, improving formatting and clarifying what happens in each missing/incorrect job, and what 'remove record' means precisely (it leaves no deletion record)
* fixed a bug from last week when trying to edit your default tag import options

### boring note import options cleanup and refactoring
* moved ClientGUIImport code up to a new hydrus.client.gui.importing module, refactored it into multiple files, and merged in some other edit panels for various import gui
* merged the file/tag import options buttons into one cleverer and cleaner class. changed its update callables into nicer Qt signals. wrote a new tabbed edit panel for it to work with, and replaced all old import option buttons across the program with the new system
* fixed an issue where the 'import options' buttons (now merged) would allow you to set them as 'default' through the right-click menu even when the button was set to not allow defaults (this state occurs in the options dialog, when you _set_ what the defaults are)
* fixed the same when you try to paste default options into the button
* brushed up and completed the note import options object
* wrote a 'edit note import options' panel
* fixed a small thing where the 'string-to-string' list widget wasn't setting the custom 'value' column header name correctly

## [Version 494](https://github.com/hydrusnetwork/hydrus/releases/tag/v494)

### QT6
* thanks to a user's help, we are rolling out a Qt6 test build this week. we've been running Qt5 for a few years now. 6 is mostly a very large bugfix patch, and I am hopeful this update will relieve several legacy issues related to UI scale, colour support, draw flickering, and other unusual stuff. so far, it is working for me great. I'll be putting out joint 5 and 6 builds for 4-8 weeks, to iron out any big problems, and then I'll switch over to 6 releases exclusively. if you are an advanced user, please give it a go this or next week and let me know if you run into any traceback errors about deprecated method names or completely jank layout in the less used parts of the program
* the actual changes you'll see are mostly style, just slightly different font spacing, things like that. if you have a system-baked Qt5 style that hydrus magically inherits, this will no longer work, you need to get a Qt6 version of the style (although I understand this is happening already for the popular styles, so you may already have them)
* users on Windows 7 and similarly old OS versions are unable to run Qt6 programs, sorry!
* I intend to keep the code 5-compatible, and users who run from source can choose whichever version of Qt they prefer, as here in the help: https://hydrusnetwork.github.io/hydrus/running_from_source.html#qt
* the linux Qt6 build also goes up from ubuntu 18.04 to 20.04. let me know if you have any trouble, but it feels like it is time to update this too

### file import options overhaul
* I wanted to do note parsing this week, but when I reviewed the whole job, there wasn't enough time to do it properly. so, in prep for a cleaner introduction of 'note import options' next week, I am overhauling how the other import options do some stuff
* all file import options now support filetype filtering! it uses the same control as system:filetype or in import folders, but with some improved logic. on update, existing import folder filetype settings will be copied down to the file import options
* file import options now work on a similar 'default' system as tag import options. existing file import options will stay as-is, but new ones will begin in a 'use the default settings at time of import' state. those defaults are editable under _options->importing_. for now I am not adding a 'use this file import options default for this web domain' system, but it might happen in future. let's see how this all shakes out first
* the file import options button now has a right-click menu like the tag import options button
* the manage subscriptions panel now has a 'overwrite file import options' button to mass-set FIO
* cleaned up a bunch of old file import and import options code

### misc
* system:filetype now remembers meta filetypes better. if you select 'all video', it will now still select all video even if hydev adds support for a new video type in future. also if you select 'video + animations', it'll say that rather than listing out every possible specific-type
* fixed an issue where loading a favourite search wasn't always setting 'include current/pending' values on the buttons correct
* fixed up a status display in the gallery downloader and watcher pages--if you pause an importer while it is doing work, it now says 'pausing...' as its status until any current jobs are finished. it was giving empty text before, as if it were finished already
* fixed some unusual behaviour with downloader highlighting where the first query pended to an empty page was secretly highlighted for the next session load, and fixed the 'subscription gap downloader' also doing this and not obeying the normal 'highlight new downloaders if nothing already highlighted' option
* improved the error when the 'make sure this directory exists' function runs into a file with that pathname
* fixed a rare selection position error, maybe Qt6 only, when clicking in the thumbnail grid as it is loading

### boring Qt6 code cleanup
* as a side thing, I set up quick-launch environments for QtPy5, QtPy6, PySide2, and PySide6 in my IDE this week, so I can now test all these situations and jump back in time no problem in future
* integrated a user's patch to bring us up to Qt6 compatibility and did a little more work to get it backwards compatible with older qtpy and Qt5
* refactored the critical Qt boot setup and monkeypatching from QtPorting to a new QtInit module
* migrated the hydrus code for keyboardModifiers, event-pos, and globalPos all to the Qt6 equivalents so the monkeypatching is always going to be on older versions looking forward
* fiddled with QPoint and QPointF conversions a little so I _think_ Qt5 and Qt6 is always talking about the same type
* updated build scripts and requirements.txts for the new situation
* updated the help a bit for the new situation

## [Version 493](https://github.com/hydrusnetwork/hydrus/releases/tag/v493)

### EXIF
* in the first step of 'official' EXIF support, the media viewer now has a 'cog' button on the top hover, enabled when looking at a jpeg, that will check the file for EXIF data. if found, it will throw it up on a simple new window that shows EXIF id, label, and value. this is a hacked-together prototype, not super user-friendly, but it works. let me know what you think, and please send me any files that have weird EXIF that doesn't parse right but you think should. I already discovered a file with a null character that wouldn't display in UI, that sort of thing
* GPS EXIF values are also parsed and extracted
* made it so you can double-click a row in this new window to copy an EXIF value to clipboard
* in the duplicate filter, if one or both files have exif data, this is now noted in the comparison statements, just like ICC profile! (issue #469)
* obvious future extensions here will be storing 'has exif' in the database and allowing its presence to be searchable and enabling the cog button (or a nicer 'exif' button) only when there is known data to see. a subsequent step would be actually caching the data in the database for full EXIF search
* as a side thing, we're now set up on the hydrus end to pull TIFF EXIF, but PIL doesn't seem to offer it, so we'll have to wait for a different solution there

### fixes and misc
* fixed a problem that made saved page file sorts reset their sort order one time on update to v492. thank you to a user for noticing this and discovering the fix, and I'm very sorry for the inconvenience of changing your session and favourite search sorts. unfortunately there is no easy fix other than rolling back to a backup and jumping forward to this version
* fixed a v492 message display error when setting various duplicate relationships to three or more thumbnails at once. it was a stupid typo, sorry for the trouble! (issue #1199)
* if a page tab name elides to a 'shorter...' length, it now has its full name as the tooltip
* fixed a typo in update code error handling (issue #1192)
* the duplicate filter page now remembers if you are 'searching immediately'/'search paused' (issue #1193)
* if you are on non-Windows and export files manually or with an export folder to an NTFS or exFAT partition, this is now detected, and NTFS-invalid characters in the pattern-generated folders or filename are now replaced with underscores (issue #1194)
* 'fixed' a system predicate bug in the 'OR*' advanced predicate parser--entering a logical expression that results in a negated system tag now causes an error. previously, it would strip the 'system:' and just enter the given text as an unnamespaced tag. furthermore, that dialog now reports specific error reasons when it fails to parse. I hope to improve support for negated system tags in future--some stuff, like archive/inbox, should be easy.
* I think I fixed an instance where the archive/delete filter's confirmation dialog could present 'delete from hard disk' as an option when it wasn't appropriate
* in an attempt to reduce the media-change flickering we've recently seen in the media viewer, I untangled a bunch of the canvas size/position code this week. I'm preparing a complete overhaul and neat Qt layout integration, which this starts. I _think_ I've made some things less flickery on occasion, but we'll see IRL. much more to do
* added a '--profile_mode' launch argument, which allows you to capture the performance of boot and also try out profile mode on the server (although support there is very limited atm)

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
