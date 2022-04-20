# changelog

!!! note
    This is the new changelog, only the most recent builds. For all versions, see the [old changelog](old_changelog.html).

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

## [Version 476](https://github.com/hydrusnetwork/hydrus/releases/tag/v476)

### domain modified times
* the downloader now saves the 'source time' (or, if none was parsed, 'creation time') for each file import object to the database when a file import is completed. separate timestamps are tracked for every domain you download from, and a file's number can update to an earlier time if a new one comes in for that domain
* I overhauled how hydrus stores timestamps in each media object and added these domain timestamps to it. now, when you see 'modified time', it is the minimum of the file modified time and all recorded domain modified times. this aggregated modfified time works for sort in UI and when sorting before applying system:limit, and it also works for system:modified time search. the search may be slow in some situations--let me know
* I also added the very recent 'archived' timestamps into this new object and added sort for archived time too. 'archived 3 minutes ago' style text will appear in thumbnail right-click menus and the media viewer top status text
* in future, I will add search for archive time; more display, search, and sort for modified time (for specific domains); and also figure out a dialog so you can manually edit these timestamps in case of problems
* I also expect to write an optional 'fill in dummy data' routine for the archived timestamps for files archived before I started tracking these timestamps. something like 'for all archived files, put in an archive time 20% between import time and now', but maybe there is a better way of doing it, let me know if you have any ideas. we'll only get one shot at this, so maybe we can do a better estimate with closer analysis
* in the longer future, I expect import/export support for this data and maintenance routines to retroactively populate the domain data based on hitting up known urls again, so all us long-time users can backfill in nicer post times for all our downloaded files

### searching tags on client api
* a user has helped me out by writing autocomplete tag search for the client api, under /add_tags/search_tags. I normally do not accept pull requests like this, but the guy did a great job and I have not been able to fit this in myself despite wanting it a lot
* I added some bells and whistles--py 3.8 support, tag sorting, filtering results according to any api permissions, and some unit tests
* at the moment, it searches the 'storage' domain that you see in a manage tags dialog, i.e. without siblings collapsed. I can and will expand it to support more options in future. please give it a go and let me know what you think
* client api version is now 26

### misc
* when you edit something in a multi-column list, I think I have updated every single one so the selection is preserved through the edit. annoyingly and confusingly on most of the old lists, for instance subscriptions, the 'ghost' of the selection focus would bump up one position after an edit. now it should stay the same even if you rename etc... and if you have multiple selected/edited
* I _think_ I fixed a bug in the selected files taglist where, in some combination of changing the tag service of the page and then loading up a favourite search, the taglist could get stuck on the previous tag domain. typically this would look as if the page's taglist had nothing in it no matter what files were selected
* if you set some files as 'alternates' when they are already 'duplicates', this now works (previously it did nothing). the non-kings of the group will be extracted from the duplicate group and applied as new alts
* added a 'BUGFIX' checkbox to 'gui pages' options page that forces a 'hide page' signal to the current page when creating a new page. we'll see if this patches a weird error or if more work is needed
* added some protections against viewing files when the image/video file has (incorrectly) 0 width or height
* added support for viewing non-image/video files in the duplicate filter. there are advanced ways to get unusual files in here, and until now a pdf or something would throw an error about having 0 width

## [Version 475](https://github.com/hydrusnetwork/hydrus/releases/tag/v475)

### new help docs
* the hydrus help is now built from markup using MkDocs! it now looks nicer and has search and automatically generated tables of contents and so on. please check it out. a user converted _all_ my old handwritten html to markup and figured out a migration process. thank you very much to this user.
* the help has pretty much the same structure, but online it has moved up a directory from https://hydrusnetwork.github.io/hydrus/help to https://hydrusnetwork.github.io/hydrus. all the old links should redirect in any case, so it isn't a big deal, but I have updated the various places in the program and my social media that have direct links. let me know if you have any trouble
* if you run from source and want a local copy of the help, you can build your own as here: https://hydrusnetwork.github.io/hydrus/about_docs.html . it is super simple, it just takes one extra step. Or just download and extract one of the archive builds
* if you run from source, hit _help->open help_, and don't have help built, the client now gives you a dialog to open the online help or see the guide to build your help
* the help got another round of updates in the second week, some fixed URLs and things and the start of the integration of the 'simple help' written by a user
* I added a screenshot and a bit more text to the 'backing up' help to show how to set up FreeFileSync for a good simple backup
* I added a list of some quick links back in to the main index page of the help
* I wrote an unlinked 'after_distaster' page for the help that collects my 'ok we finished recovering your broken database, now use your pain to maintain a backup in future' spiel, which I will point people to in future

### misc
* fixed a bug where changes to the search space in a duplicate filter page were not sticking after the first time they were changed. this was related to a recent 'does page have changes?' optimisation--it was giving a false negative for this page type (issue #1079)
* fixed a bug when searching for both 'media' and 'preview' view count/viewtime simultaneously (issue #1089, issue #1090)
* added support for audio-only mp4 files. these would previously generally fail, sometimes be read as m4a. all m4as are scheduled for a metadata regen scan
* improved some mpeg-4 container parsing to better differentiate these types
* now we have great apng detection, all pngs with apparent 'bitrate' over 0.85 bits/pixel will be scheduled for an 'is this actually an apng?' scan. this 0.85 isn't a perfect number and won't find extremely well-compressed pixel apngs, but it covers a good amount without causing a metadata regen for every png we own
* system:hash now supports 'is' and 'is not', if you want to, say, exclude a list of hashes from a search
* fixed some 'is not' parsing in the system predicate parser
* when you drag and drop a thumbnail to export it from the program, the preview media viewer now pauses that file (just as the full media viewer does) rather than clears it
* when you change the page away while previewing media with duration, the client now remembers if you were paused or playing and restores that state when you return to that page
* folded in a new and improved Deviant Art page parser written by a user. it should be better about getting the highest quality image in unusual situations
* running a search with a large file pool and multiple negated tags, negated namespaces, and/or negated wildcards should be significantly faster. an optimisation that was previously repeated for each negated tag search is now performed for all of them as a group with a little inter-job overhead added. should make '(big) system:inbox -character x, -character y, -character z' like lightning compared to before
* added a 'unless namespace is a number' to 'tag presentation' options, which will show the full tag for tags like '16:9' when you have 'show namespaces' unticked
* altered a path normalisation check when you add a file or thumbnail location in 'migrate database'--if it fails to normalise symlinks, it now just gives a warning and lets you continue. fingers crossed, this permits rclone mounts for file storage (issue #1084)
* when a 'check for missing/invalid file' maintenance job runs, it now prints all the hashes of missing or invalid files to a nice simple newline-separated list .txt in the error directory. this is an easy to work with hash record, useful for later recovery
* fixed numerous instances where logs and texts I was writing could create too many newline characters on Windows. it was confusing some reader software and showing as double-spaced taglists and similar for exported sidecar files and profile logs
* I think I fixed a bug, when crawling for file paths, where on Windows some network file paths were being detected incorrectly as directories and causing parse errors
* fixed a broken command in the release build so the windows installer executable should correctly get 'v475' as its version metadata (previously this was blank), which should help some software managers that use this info to decide to do updates (issue #1071)

### some cleanup
* replaced last instances of EVT_CLOSE wx wrapper with proper Qt code
* did a heap of very minor code cleanup jobs all across the program, mostly just to get into pycharm
* clarified the help text in _options->external programs_ regarding %path% variable

### pycharm
* as a side note, I finally moved from my jank old WingIDE IDE to PyCharm in this release. I am overall happy with it--it is clearly very powerful and customisable--but adjusting after about ten or twelve years of Wing was a bit awkward. I am very much a person of habit, and it will take me a little while to get fully used to the new shortcuts and UI and so on, but PyCharm does everything that is critical for me, supports many modern coding concepts, and will work well as we move to python 3.9 and beyond

## [Version 474](https://github.com/hydrusnetwork/hydrus/releases/tag/v474)

### command palette
* the guy who put the command pallete together has fixed a 'show palette' bug some people encountered (issue #1060)
* he also added mouse support!
* he added support to show checkable menu items too, and I integrated this for the menubar (lightning bolt icon) items
* I added a line to the default QSS that I think fixes the odd icon/text background colours some users saw in the command palette

### misc
* file archive times are now recorded in the background. there's no load/search/sort yet, but this will be added in future
* under 'manage shortcuts', there is a new checkbox to rename left- and right-click to primary- and secondary- in the shortcuts UI. if you have a flipped mouse or any other odd situation, try it out
* if a file storage location does not have enough free disk space for a file, or if it just has <100MB generally, the client now throws up a popup to say what happened specifically with instructions to shut down and fix now and automatically pauses subscriptions, paged file import queues, and import folders. this test occurs before the attempt to copy the file into place. free space isn't actually checked over and over, it is cached for up to an hour depending on the last free space amount
* this 'paused all regular imports' mode is also now fired any time any simple file-add action fails to copy. at this stage, we are talking 'device disconnected' and 'device failed' style errors, so might as well pause everything just to be careful
* when the downloader hits a post url that spawns several subsidiary downloads (for instance on pixiv and artstation when you have a multi-file post), the status of that parent post is now 'completed', a new status to represent 'good, but not direct file'. new download queues will then present '3N' and '3 successful' summary counts that actually correspond to number of files rather than number of successful items
* pages now give a concise 'summary name' of 'name - num_files - import progress' (it also eli...des for longer names) for menus and the new command palette, which unlike the older status-bar-based strings are always available and will stop clients with many pages becoming multi-wide-column-menu-hell
* improved apng parsing. hydrus can now detect that pngs are actually apngs for (hopefully) all types of valid apng. it turns out some weird apngs have some additional header data, but I wrote a new chunk parser that should figure it all out
* with luck, users who have window focus issues when closing a child window (e.g. close review services, the main gui does not get focus back), should now see that happen (issue #1063). this may need some more work, so let me know
* the session weight count in the 'pages' menu now updates on any add thumbs, remove thumbs, or thumbnail panel swap. this _should_ be fast all the time, and buffer nicely if it is ever overwhelmed, but let me know if you have a madlad session and get significant new lag when you watch a downloader bring in new files
* a user came up with a clever idea to efficiently target regenerations for the recent fix to pixel duplicate calculations for images with opaque alpha channels, so this week I will queue up some pixel hash regeneration. it does not fix every file with an opaque alpha channel, but it should help out. it also shouldn't take _all_ that long to clear this queue out. lastly, I renamed that file maintenance job from 'calculate file pixel hash' to 'regenerate pixel duplicate data'
* the various duplicate system actions on thumbnails now specify the number of files being acted on in the yes/no dialog
* fixed a bug when searching in complicated multi-file-service domains on a client that has been on for a long time (some data used here was being reset in regular db maintenance)
* fixed a bug where for very unlucky byte sizes, for instance 188213746, the client was flipping between two different output values (e.g. 179MB/180MB) on subsequent calls (issue #1068)
* after some user profiles and experimental testing, rebalanced some optimisations in sibling and parent calculation. fingers crossed, some larger sibling groups with worst-case numbers should calculate more efficiently
* if sibling/parent calculation hits a heavy bump and takes a really long time to do a job during 'normal' time, the whole system now takes a much longer break (half an hour) before continuing

### boring stuff
* the delete dialog has basic multiple local file service support ready for that expansion. it no longer refers to the old static 'my files' service identifier. I think it will need some user-friendly more polish once that feature is in
* the 'migrate tags' dialog's file service filtering now supports n local file services, and 'all local files'
* updated the build scripts to force windows server 2019 (and macos-11). github is rolling out windows 2022 as the new latest, and there's a couple of things to iron out first on our end. this is probably going to happen this year though, along with Qt6 and python 3.9, which will all mean end of life for windows 7 in our built hydrus release
* removed the spare platform-specific github workflow scripts from the static folder--I wanted these as a sort of backup, but they never proved useful and needed to be synced on all changes

## [Version 473](https://github.com/hydrusnetwork/hydrus/releases/tag/v473)

### misc
* fixed the recent problem with drag and dropping thumbnails to a level below the top row of pages. sorry for the trouble!
* fixed a bug where the client would not load results sorting by 'import time' when the search file domain was a single deleted file domain
* fixed a list display bug in the edit page parser dialog when a subsidiary page parser has two complicated string-match based content parsers
* collections now sort by modified time, using the largest known modified time in their collection
* added sqlite3.exe console back into the windows build--sorry, it was missing since the github build changeover!
* added a note to the help about backing up when tight on space, which I will repeat here: the sqlite database files are very compressible (70GB->17GB on default 7zip settings!), so if you need more space on your backup drive, this is a good way to reclaim it

### command palette
* a user has written a cool 'command palette' for the program! it brings up a type-and-search interface to navigate to pages or menu entries.
* I have integrated his first version and set the default shortcut to Ctrl+P. users who update will get this shortcut if they have nothing else on Ctrl+P on 'main window' set. if you prefer Ctrl+K or anything else, you can change it under _file->shortcuts->the main window_
* regular users will get a page list they can search and select, advanced users will also get the (potentially dangerous) full scan of the menubar and current thumbnail right-click menu. I will be polishing this latter feature in future to filter out big maintenance jobs and show checkbox status and similar, so if you are advanced, please be careful for now
* try it out, and let me know how it goes. the underlying widget is neat, and I can change its behaviour and extend it significantly

### (mostly advanced) deleted file improvements
* files that have been deleted from a local file domain are now aware of their file deletion reason. this is visible in the right-click menu of thumb or media canvas
* the advanced file deletion dialog now initialises using this stored reason. if all pending deletees have the same existing reason stored, it will display it, and if they are all set but differ, this will be noted and an option to not alter them is also available. this will come up later in niche advanced situations with mutiple file services
* reversing a recent change, local file deletion reasons are no longer cleared on undelete or (re)import. they'll now hang around invisibly and initialise any future advanced file deletion dialog
* updated the thumbnail and canvas undelete mechanism to handle multiple services. now, if the files are deleted in more than one domain, you will be asked to multiple-select which you wish to undelete for. if there is only one eligible undelete service, the process remains unchanged--you'll just get a yes/no confirmation if the 'confirm trash' option is set
* misc multiple local file services code conversion work

## [Version 472](https://github.com/hydrusnetwork/hydrus/releases/tag/v472b)

### highlights
* the file domain button of every autocomplete input now has a 'multiple locations' entry. this launches a checkboxlist of all possible search locations and allows you to search more than one domain at once. it works, too! in future, when we can have multiple 'my files' services, you'll be able to choose here unions of what to search. users in advanced mode will see repository updates, all local files, all known files, and the new deleted file domains on this list. I removed the deleted file domains from the front menu because I expect them to be rarely used
* in _options->thumbnails_, there is now a 'thumbnail scaling' dropdown. you can set it so thumbs only ever scale down (which remains the default), scale to fit (i.e. very small images are also scaled up), or scale to fill. the 'animation' as thumbnails refit and delayed-regen themselves to 'scale to fill' is accidentally one of the coolest things I have done
* removed the old 'EXPERIMENTAL: thumbnail fill' option. the new mode works essentially the same, but faster and higher quality
* in the page tab menu, there is a new submenu 'pages', which shows all the pages at or below the current level. if you right-click on a page of pages tab, it will just show for that page of pages. click any of the entries, you will select that page. it is a web browser-like quick navigation menu, let me know what you think!
* rejiggered the page tab menu a little, reordering groups a bit with nicer separators and putting 'select' navigation on the menu even if you click in greyspace
* fixed a problem in page tab menu logic where if you right-clicked on greyspace, it would render the menu for the bottommost page of pages row rather than the one actually clicked
* last week's update where a mouse release event will no longer fire in the shortcuts system if the mouse moved a decent distance between press and release should now work in the media viewer canvas when dragging is set to anchor the mouse in place. some advanced users may wish to try setting archive/delete to work on mouse release and use left click to drag

### bug fixes
* fixed pages force-refreshing file queries on session load. this has never been intentional, but it slipped through again and was happening for a month or two now. I have added an explicit test to my routine to make sure this doesn't happen again, sorry for the trouble!
* fixed a problem in the recent fast shutdown code that was accidentally also shutting down some maintenance work like repository processing as soon as it started, even if 'exit and force work' was chosen
* all images with a completely opaque alpha channel will now have that alpha channel dropped for the new pixel hash calculation, meaning they will now match with regular non-alpha images with the same colour pixel data. in fact, all images with an opaque alpha now have that channel dropped on load, which will save a little memory and CPU any time they are handled (issue #770)
* if the 'durable' temporary database exists on boot, it is now deleted and a fresh one created rather than trying to re-use the old one (which would not have any useful information anyway), and a note is made to log. one user recently had a problem where an existing corrupt temp dir was stopping boot, which this fixes

### misc
* updated the windows build to use a newer version of mpv, moving from roughly 2021-02 to 2022-01. this replaces mpv-1.dll with mpv-2.dll, and I set the installer to delete the old '1'. if you extract, you can delete the old '1' yourself, but things seems fine with both. in any case, let me know if you have any trouble!
* updated the windows build to use sqlite 3.37.2, the sqlite3 in the db dir is also updated
* the deleted files system now neatly cleans up old file deletion reasons on file import and file undelete
* cleared out some old thumbnail generation code, including deleting an old and now obselete optimisation where too-large thumbs were scaled down to make new thumbs rather than revisiting source. since our thumb situation is more complicated now, this is gone in favour of nicer quality thumbs and simpler code
* fixed up some upcoming database maintenance code in my new modules
* updated and cleaned the code in the old wx-converted checkboxlist and replaced some awkward old access routines
* cleared out some old HTA archive code
