---
title: Changelog
---

# changelog

!!! note
    This is the new changelog, only the most recent builds. For all versions, see the [old changelog](old_changelog.html).

## [Version 682](https://github.com/hydrusnetwork/hydrus/releases/tag/v682)

### more file metadata

* the client can now inspect an image file and tell if it has (EXIF-like) XMP or IPTC metadata! the data will also show in the media viewer, in the extra info dialog
* renamed the new 'source' metadata line to 'software/source'. sometimes it is 'photoshop'; sometimes it is a camera model; sometimes it is both
* the client now tracks and generates 'has software/source', 'has xmp', and 'has iptc' flags, just like 'has exif' and friends. all _new_ files will get these flags and it is all saved to db and so on
* there are new 'system:file property' predicates to search for these flags; they are also parseable
* the file maintenance system has new jobs to regen these flags for existing files
* these flags appear in the duplicate filter comparison statements and in some file flyout menu summaries and so on, similarly
* 'has embedded metadata' and 'has non-EXIF metadata' and similar terms are now renamed (back) to 'has human-readable metadata'. this flag is now absolutely intended to be Artist, Title, Comment, and AI prompts kind of stuff. 'some dude probably typed this in once metadata'
* I am, again, not yet triggering the big (optional) 'regen who has human-readable metadata' job for all existing files, but I think we are just about ready, so if no one has any issues with today's work, it'll be next week. we'll do all four xmp, iptc, software/source, and human-readable flags in one go and make something more useful out of all this. if you are an advanced user, give these new flags a spin and let me know what you think

### Client API

* file_metadata call now says `has_xmp`, `has_iptc`, and `has_software_source`, reflecting the above changes
* Client API version is now 95

### misc

* the right-hand notes hover window in the media viewer now copies the name/note_text on a middle-click. it also has a tooltip that says what different clicks do (is this obscuring/annoying?)
* the 'edit file notes' dialog has a little cog icon to alter how the copy button works; you can say whether you want all notes or just the current one in view, and you can say whether to copy as JSON, which the paste button accepts, or something more human
* fixed the new GraphicsView thumbnail widget test to accept drag and drops
* the options dialog now hides the Qt audio device fetch and list initialisation behind a button click. this has been a source of dialog crashing and other hassle in the past, so, like for mpv, the dialog now needs you to click a thing to go ask your lower level OS dlls whats up with audio device availability right now
* I fixed an issue in the duplicates system that was sometimes causing non-accessible potential duplicate pairs to be registered. it was when a serf (a non-king member) of a multi-file duplicate group was queued up for potential duplicate discovery and found a pair while the king had since been physically deleted (this typically requires some non-deleting duplicate-setting and then a king delete and then a re-search potentials action, but a big client can have a few warts like this). on update, all clients will run the 'resync potnential duplicate pairs to storage' maintenance job to clean up any location-orphaned pairs
* thanks to a user, fixed another instance of certain downloaders adding tags parsed in a gallery page fetch passing on their tags to a 'next page' gallery url

### executables manager plan

* I have planned out the basic shape of the executable manager, which is my big project for the second half of this year that will allow hydrus to call external exes and servers in a more flexible way. basically a reverse API that will add tech like 'please download this complicated URL' and 'generate clever tag suggestions for this file' without needing me to write the exe hooks. now I have sunken my teeth into it, I feel fairly good and hope to have richer 'open file/url externally' options page as the first step quite soon
* in closer detail, I had a think, made a plan, and sketched out some early enums and objects
* also wrote out a new serialisable tracker object for objects that have an immutable id and a string name label; something nicer than the hackery I have previously deployed in the downloader system

### boring stuff

* added `distortion` and `date:timestamp` to the ignored fields for human-readable metadata
* since we now track seven boolean flags for stuff like 'has exif' and 'has transparency', I cleaned up _some_ of the db storage code here. I considered folding it all into one table, but in my experience, this particular shape of data doesn't benefit from such a thing. I kept it separate and spammy but KISS and collapsed the code to more shared calls. the search code however is now pretty spammy so I will revisit this
* cleaned up some code in the master main gui drag and drop catcher and improved how it handles some drag mouse events. there's a small chance some odd drop bugs may be fixed in weirder OSes
* added some unit tests for the new file metadata flag tech
* fixed up some unit tests in the duplicates auto-resolution system that were skating on thin ice and needed tighter logic for my new 'only add potential duplicate pairs when they satisfy x and y' filter
* removed some old defunct Linux help regarding ffmpeg on the frozen builds. you got it now, bro
* fixed some 'waiting for a work slot' labelling in the downloaders UI
* a bunch of misc linting and some voodoo linting

## [Version 681](https://github.com/hydrusnetwork/hydrus/releases/tag/v681)

### misc

* status bar 'busy' indicator is simpler, and the tooltip now says the number of threads working
* wrote a catch to stop QSS stylesheets from specifying a hydrus property colour with transparency. these were drawing crazy, with noclip garbage left on bitmaps used for transparenty images and animations in the media viewer. also fixed the `e621_redux` stylesheet, where this issue was discovered, to simply set a background colour for the media viewer

### more human-readable embedded metadata filtering

* I further cleaned up what hydrus considers 'human-readable embedded metadata'. many more technical fields are now hidden from the little text panel, meaning when this guy does pop up, or you search 'has non-EXIF embedded metadata', you'll now tend to see something nice and human like 'Artist' or 'Title', or otherwise rich like an AI prompt or Character card
* I now invite advanced users to do some 'determine if the file has non-EXIF embedded metadata' maintenance regenning on some 'has non-EXIF embedded metadata' files and tell me what technical/inhuman text remains in their collections. I'm getting pretty happy here and I expect to (optionally) schedule a big regen for all users pretty soon
* the newly excluded fields are: 'software', 'transparency', 'bit_depth', 'duration', 'primary', 'default_image', 'Creation Time', 'create-date', 'modify-date', 'date:create', 'date:modify', 'chroma', 'loop', 'timestamp = 0', 'extension', 'photoshop', 'bbox', 'blend', 'mpoffset', 'disposal', 'interlace', 'aspect', 'sizes', a ton of 'Thumb::' garbage, 'iptc', 'Raw profile type exif', 'Raw profile type iptc' (ye olde XMP), 'xmp', 'XML:com.adobe.xmp', 'adobe', and 'adobe_transform'. a bunch of these are format specific DPI data and such and not useful to elevate to the user. the IPTC and XMP stuff will come back when I expand EXIF parsing
* excluded 'comment' or 'Comment' from human-readable metadata fields if it matches a handful of 'Created with X' style regexes; this is now parsed as a 'software' field
* the 'Creator' and 'Source' fields are now appended to the 'software' field
* excluded any human-readable metadata fields that have null value or empty list/dict
* I realised while doing this that maybe going for a whitelist of what we do want would be saner, but I think I prefer, for completeness and fun, to get everything and actually deal with the sore thumbs
* put 'software' metadata field in the 'extra info' panel below, as 'source' ('source' rather than 'software' because sometimes stuff like Kodak blah blah comes through here). there's an argument to include this in human-readable fields, if we are keeping artist/title, but I'm falling on the side of extracting it. I like this field a lot as human-valuable and it'll be high priority to be its own thing when we add richer metadata storage/search
* similarly, the 'create-date' and friends are cool and I'll figure out some way to pipe that to a 'file metadata' modified time 'domain'. you can't generally get any better than the file metadata for this
* if a file has a 'chroma' field talking about '420' subsampling, this is now converted to a subsampling field in the 'extra info' panel, like for jpeg
* optimised 'has human-readable metadata' test for a fast yes in many cases

### new graphicsview thumbnail grid test

* the new 'thumbnail rendering tech' TEST under `options->thumbnails` is fixed up a bit and ready for advanced users to tentatively try out. I think I have it doing pretty much everything the existing code does without complaint, but I would like to confirm that with a broader test. it only applies to new pages, so I recommend first opening a new page and do some of your normal stuff before you test your whole session with a full client restart
* fixed 'collect-by' transitions, removing the ghost singles that hung around
* fixed a late waterfall thumb keyerror when transitioning through collect-by states
* fixed collections not redrawing for a new first media on sort-by changes
* fixed updating the status bar on any collect-by change, in either old or new thumbgrid code. it now flips between '200 files' and '200 files in 12 collections' when you change the collections
* fixed drawing of thumbs at higher than 100% UI scale (the bitmaps were cropped due to DPR fun)
* fixed a blurhash thumb fallback route in the new test
* shaved the test animation time down for snappier feel. I'm pretty sure the old animation is accidentally heavily curved so despite ostensibly being 0.5s it was visually done faster. new guy is now ~13 frames at 60Hz
* did some KISS refactoring of this code

### more de-laggification work

* I hacked in a test last week to try a different way of scheduling jobs in the background. it worked very well and I seem to have found the cause of the 'I have a fat client and when it does heavy work like archive/delete filter commit, everything slows down a lot' issue. basically, when certain sorts of heavy work was going on, threads waiting on new work to do or database jobs to come back were getting into a kind of traffic jam and wasting lots of time figuring out who had to go first rather than letting the guy who was actually doing the work go ahead and do it. I have now replicated and cleaned my work to several places and big clients that do a lot should be a good bit less laggy when big things are going on
* cleaned up the successful CallToThread anti-CPU-thrashing test, taking out older code and cleaning the loop of it
* added anti-CPU-thrash tech to db mainloop
* added anti-CPU-thrash tech to threads waiting on the db to finish current work
* added anti-CPU-thrash tech to database jobs; when many threads are competing for the db, they'll wake less
* added anti-CPU-thrash tech to network job waits; when many threads are competing for network resources, they'll wake less
* added anti-CPU-thrash tech to pubsub, both in the managing daemon and any threads waiting on 'background work to free up'
* added anti-CPU thrash tech to 'are we currently rendering any thumbnails?' wait, which a bunch of threads wait on before going ahead with their own work
* added anti-CPU-thrash tech to the core read-write lock used in the filesystem. I was very careful here as this is not my fortÃ©, and tests are good. this should improve latency, particularly thumb and file loading latency, when many file imports are going on and the locks are churning, which is another place we've seen inexplicable lag during certain busy periods
* retired the debug 'db ui-hang relief mode'. this was an interesting experiment but the incorrect solution to the problem of GUI threads waiting on the db

### boring de-laggification stuff

* wrote a new thread worker pool object to look after calltothreads
* primary controller and test controller now use this same object to manage threads (test guy had its own hacky code before)
* tightened up db mainloop shutdown--to assure that db jobs can wait forever safely, we now guarantee that every job posted will get explicitly woken with a result through db shutdown
* network engine now guarantees every network job it gets will be done'd so waiting threads shall all be woken up on program shutdown
* rejiggered some 'is it time to commit?' in db idle time stuff given the changes
* cleaned up some thread status-checking locking, mostly in debug code
* KISSed some network job status stuff, and removed some confusing shutdown detection from the core 'isdone' calls
* removed defunct db I/O-locking error-handling code
* pubsub takes work breaks more often
* pubsub system now has a shutdown signal to tidy up waiters properly on shutdown
* thumbnail caches now have an explicit shutdown signal and clean up after themselves better on shutdown
* cleaned up some misc thumb cache code
* misc shutdown code cleanup
* reordered some controller shutdown code
* misc cleanup of controller wait code
* removal of spurious event flags in db and pubsub

### future build committed

* This release commits the changes tested with the recent future test build, which went well
* the summary for this update is: loads of stuff
* there are no special instructions for the update. update as normal
* since library versions have been bumped, users who run from source will be encouraged to rebuild their venv on update this week.
* the library changes are--
   - `PySide6` (Qt) from `6.9.3` to `6.10.3`
   - OpenCV (`opencv-python-headless`) from `4.12.0.88` to `4.13.0.92`
   - `beatifulsoup4` `4.14.3` to `4.15.0`
   - `cbor2` `6.1.1` to `6.1.3`
   - `cryptography` `48.0.0` to `49.0.0`
   - `Pillow` `12.2.0` to `12.3.0`
   - `pillow-heif` `1.3.0` to `1.4.0`
   - `pillow-jxl-plugin` `1.3.7` to `1.3.8`
   - `pyopenssl` `26.2.0` to `26.3.0`
   - `service-identity` `24.2.0` to `26.1.0`
   - `numpy` `2.3.1` to `2.4.6` (this jump was a bit of a juggle, and now possible with OpenCV 4.13)
   - `requests` `2.33.1` to `2.34.2`
   - SQLite dll and sqlite3 terminal updated on Windows from `3.51.2` to `3.53.3`
   - SQLite terminal executable `3.53.3` now added to Linux and added to new db folders just like the Windows extract
* the 'test' library changes are--
   - `PySide6` (Qt) from `6.10.3` to `6.11.1`
   - OpenCV (`opencv-python-headless`) from `4.13.0.92` to `5.0.0.93`. I did some research, and this upcoming jump doesn't seem to be a super significant change for our purposes. mostly C++ cleanup and finally dropping python 2 support.
* other stuff--
   - db folder is now completely masked in gitignore
* build environment--
   - updated the workflow actions versions across the board
   - Windows and Linux builds are moved from python 3.12 to 3.13
   - `pyinstaller` `6.16.0` to `6.18.0`
   - the builds now share the core pyproject.toml rather than using their own requirements.txt files
   - `pywin32` in Windows build env from `311` to `312`
   - Windows ffmpeg (GyanD) `8.1.1` to `8.1.2`
   - Linux build now comes with ffmpeg (BtbN) `2026-06-30`, which I think covers `8.1.2`

## [Version 680](https://github.com/hydrusnetwork/hydrus/releases/tag/v680)

### misc

* updated the newish `tldextract` stuff (which helps navigate two-part domain suffixes like .co.uk in URL parsing) to no longer fetch a fresh suffix definition file on first ever use from `publicsuffix.org` and not to make a cache in `~/.cache/python-tldextract`. hydrus now ships with a copy of `public_suffix_list.dat` in the static dir for this library to use, and it doesn't make a cachedir entry any more. I regret not reading the docs closer! I also optimised this code so it should be a bit quicker now, too. thank you to the user who noticed this! (issue #2067)
* I _think_ I may have fixed some of the heavy CPU thrashing we have seen during heavy work like archive/delete commit and such. if you have had bad UI lag, I would like to know if some of it suddenly leaps forward today
* made file add/delete calls a tiny bit faster when they have many tags
* some thumbnail generation scheduling is a little smarter, with expensive filetypes generated more reliably at the end of the queue
* fixed thumbnail generation for cbz. sorry for the trouble--I messed something up with a recent refactor! all cbzs imported since july 5th will get a thumbnail regen call (issue #2069)
* setup_venv.py now warns the user that the path will be deleted if they specify a non-standard venv path that already exists
* added a little safety warning to the Client API page. I don't make any of those plugins and cannot guarantee anything about them--use your common sense!

### system tray

* you no longer need to be in advanced mode to see the system tray icon in Linux (old safety check I forgot about)
* added two BUGFIX checkboxes to `options->system tray` for those who have odd minimise-to-system-tray behaviour. if you had trouble, try these out and let me know what works

### number locale

* added `TEST: Use your locale for integer rendering` to `options->gui`. try it out, let me know where it works well and badly. I noticed in a fake `fr_FR` locale that the space-separator somehow messed up some taglist rendering and made system predicates no longer parse correct (I guess I hardcode commas out of numbers)--anything else?
* `system:filesize`, `system:ratio`, and `system:num pixels` now render with separators when the number exceeds 999

### file permissions

* there were some file import paths that did not set the standard hydrus file storage 'you can read and write this guy' permission bits (read+write on Windows, 644 otherwise), which I have fixed. this was affecting some downloads and some local file imports for some time in hydrus's past
* if we try to move a file during larger 'move this directory here' type operations and get a permission error, hydrus now attempts to assign the hydrus-normal read/write permission bits before trying once more (issue #2064)
* we are dealing with some legacy read-only guys here. I have a file maintenance job that tries to fix this retroactively, which I am considering firing off, sometime, to address this

### embedded metadata

* the test for the presence of file metadata is now more reliable and reflects what you see in the media viewer. previously, the file may not have been loaded the whole way during file import or file maintenance, and sometimes text was being missed, particularly in the new system where I filter out some stuff like DPI. it wasn't being missed in the media viewer since by happenstance it would generally check for EXIF beforehand, which triggers a full load. now, the thing that fetches embedded metadata now checks the file is loaded fully before grabbing the available text
* when importing files, the embedded metadata test now saves an image load (it re-uses an earlier EXIF load, if one happened) to save a bit of time

### future build

* I am making another future build this week. This is a special build with new libraries that I would like advanced users to test out so I know they are safe to fold into the normal release.
* in the release post, I will link to this alternate build. if you are experienced and would like to help me, please check it out

## [Version 679](https://github.com/hydrusnetwork/hydrus/releases/tag/v679)

### misc

* added a checkbox to `options->importing` to disable .cbz scanning. switch this off, and .cbzs will import or metadata-rescan as .zips
* fixed a recent issue where the mouse could become perma-hidden in the media viewer when transitioning to an mpv window with the mouse clicked down (e.g. in archive/delete)
* on Linux, I no longer set an application-associated desktop file on boot if you do not have a `io.github.hydrusnetwork.hydrus.desktop` file in your Applications dir(s). this fixes a warning many LInux users were seeing on boot

### system tray

* I gave the system tray hide/show tech a KISS pass. the main controls are now: 'left-click' the system tray will either (restore and) bring the program to the front, or, if it is already the front, minimise it. 'middle-click' the system tray does the full hide/show that disappears the gui from the taskbar. the 'system tray' options panel now says this specifically
* when windows go through the hide/show cycle, they remember their state better. if a media viewer is minimised before the hide, it now remembers that
* the system tray now has the 'minimise/close to system tray' and 'start in system tray' options in a new submenu. if there is a problem restoring from hide state (and thus you can't get to the options), there is now an escape hatch
* restoring from minimise is also more reliable; if the main gui was maximised before the minimise, it remembers this better
* some loop-de-doop systray icon double-click handling was removed. just middle-click it bro
* the "doesn't work half the time" 'restore/minimise' menu option is removed from system-tray right-click. just left-click it bro

### file embedded text clarity

* the 'embedded metadata' text that many images have, and which you can review using the little document button up top of the media viewer, has never been great. it grabs everything our image decoder can see and spits it into something human-readable. today I clip out many common file metadata rows so that when you see this property, you'll actually see something rich and not the ten-thousandth instance of 'this is a jfif'
* specifically, the keys of `jfif, jfif_unit, jfif_density, jfif_version, dpi, compression, resolution, srgb, gamma, and chromaticity` are no longer included in the metadata text. these are file property strings that PIL munged on load, not true embedded textual metadata. if a file has these tags (and if it has ICC profile data too), this is now presented in nice hardcoded lines below the embedded text box, same place it currently says 'progressive' and 'subsampling' for jpegs. less noise in the complex bit, more signal in the hardcoded bit!
* I am NOT scheduling a 'has embedded text?' rescan on existing files just yet. there are more rows out there, like 'Software' and a bunch of 'adobe' stuff. I'll keep working here, and advanced users please give me your feedback, and when we've culled things to our satisfaction, I'll trigger a regen on all old files and we'll wipe out a whole bunch of false-positive 'has embedded text' flags and make this thing interesting and useful

### custom temp dir

* the `temp_dir` launch argument can now be relative to your userdir, like `~/blah/hydrus_temp`, or simply relative, `db/temp`, which will be treated as relative to the base install dir, and it'll now resolve properly
* if you specify a dir that does not exist, hydrus will try to create it
* if you specify a dir that does not have write permission, hydrus now raises an exception and boot is cancelled

### faster manage tags

* if you have the 'related tags' tag suggestions panel set up, the manage tags dialog is now much more careful about how it asks that guy to go fetch tags. previously, too many pages' of related tags could be searched for on init, and they were scheduled too aggressively, and on legit refresh calls we could get overlapping refreshes, all leading to wasted CPU work. I cleaned it up a bunch
* if you have the 'file lookup scripts' tag suggestions panel set up, the manage tags dialog is now a frame or two faster to boot after first boot. the scripts are now cached rather than loaded for each service panel on each dialog load
* on my fairly dense but session-light test client, this got manage tags on one file from 160ms down to 120ms load time

### file maintenance updates

* when files get metadata updates during file maintenance, e.g. it realises it has an ICC Profile when previously it did not think so, the file is now re-queued for search in all duplicates auto-resolution rules it is in with a pertinent status (i.e. did not match search, ready to test, failed test, passed test ready to action)
* a bunch of 'ok this file has new metadata, reload the metadata object and redraw them thumb' signals are now more careful to only do that when the pertinent metadata actually changed
* re-setting pixel hashes and perceptual hashes now skips the remove/set work if the desired hashes are already set

### new client api projects

* added a couple links to the client api help: first, one to 'hydit', which is a lightweight, feature-rich hydrus client for Android (https://github.com/BashCooler/hydit)
* second, 'kaimen', which shows hydrus searches in your file explorer using virtual FUSE mounts (https://github.com/Dry-Leaf/kaimen)

### some mostly boring duplicates cleanup/optimisation

* added an index to optimise some duplicate-files setting code that would particularly slow down a client with many alternates
* optimised a particular 'reset potential dupe search' update call that is used in various file relationship dissolve and 'remove alternate member' operations (and I think some triggered by normal but complicated duplicate-setting operations too as certain groups are merged)
* optimised a number of sqlite delete calls, particularly in the duplicate files system, and particularly for clients with many dupes or alts, that were performing inefficiently on non-bleeding-edge versions of SQLite due to a particular dual-index OR clause
* fixed a file domain filtering issue with the 'maintenance: fix orphan potential pairs' job in duplicates auto-resolution; in some cases it was adding pairs that were outside of the rule's location context

* boring UI cleanup
* did a big cleanup and decoupling refactor on the new TreeView test. all my code here needs a good cleanup as we integrate the new tech, because it is groaning under the weight of five rewrites, including a transition through UI engines from years ago, and there is weird stuff all over
* decoupled the history panel from the new view, added some cleaner signals for close/reposition
* decoupled the filter panel too, same deal
* fixed filter panel focus-on-show
* removed the Application-wide eventfilter hook, which was eating a ton of CPU, and redirected to an object focus hook and a new main gui geometry/window state change signal
* removed some erroneous copy/paste spam from new code
* did some method reordering and other linting cleanup
* Main GUI no longer eventFilters itself just for minimise tracking

## [Version 678](https://github.com/hydrusnetwork/hydrus/releases/tag/v678)

### misc

* audio files that have embedded images will now get thumbnails! all your existing audio files will be scheduled for a thumb regen on update
* fixed the core ffmpeg video metadata info call to use the 'ffmpeg timeout' option, which by accident it wasn't. thank you for the reports here; this was what was stuck on 15 seconds timeout despite the new option
* the file import object right-click menu now differentiates parsed tags from inherited tags, and the gallery import object right-click menu now shows inherited tags (issue #2056)
* pdf documents that have empty human-readable file metadata text (this happens when they have no Title, Author, Subject, or Keywords) are now considered to have no such text. all pdfs are scheduled for a 'has human-readable text' regen on update

### some more UI

* thanks to a user, we have some more UI updates.
* the options search system reveals some tucked-away widgets better and excludes some other things appropriately
* there are new shortcut commands for the new per-player mute/unmute/flip-mute (issue #2050)
* I fixed some issues with the per-player mute (issue #2049)
* there's an `EXPERIMENTAL: Show tab tree view` setting under `options->gui pages` that has some neat new tech, with a tree to replace the existing tab-bar and some interesting flags to move the main page sidebar to the right. this needs a bit more work but is another thing we are playing with and will bring us a few steps towards a more modular 'place it where you like' UI layout

### boring mute cleanup

* tore out and rewrote the new per-player mute/unmute pipeline, fixing several issues related to mute check logic and subsequent state setting, also cleaned up some bad enum names and non-hooked-up signals (issue #2054)
* for KISS, the Qt and mpv players no longer track mute options; they just handle the doing of it. the parent container now tracks and reacts to options changes and the new per-player state
* the volume menu now offers a way to stop forcing mute/unmute

### boring ffmpeg cleanup

* added audio and image ffmpeg stream parsing
* added image stream rendering for audio thumbnail gen
* refactored the monolith thumbgen call, made it more reliable for weird failure cases
* refactored ffmpeg rendering calls to their own file
* misc ffmpeg calling and parsing refactoring and cleanup
* removed defunct 'only render first second' frame-counting hack
* deleted some redundant old psd ffmpeg code
* added a note to the install help about FFMPEG on Linux (issue #2052)

### other boring code cleanup

* fixed and cleaned up the layout code and some options juggling in the new treeview experiment, cleaned up some misc splitter/sizes stuff along the way

## [Version 677](https://github.com/hydrusnetwork/hydrus/releases/tag/v677)

### misc

* fixed an issue with last week's downloader metadata overhaul that broke some downloaders. specifically, when downloaders had a post with one file url and that file url was changed through normalisation (typically through a URL Class), metadata application was not working. if you had a twitter-type downloader that seemed not to add tags in v676 when there was only one file in the post, please queue up those downloads again in a new urls downloader page and they will get their tags and so on
* the 'min time to view a file in x' settings in `options->file viewing statistics` are now minimum 50ms (previously 1s)
* when doing 'special duplicate' on a shortcut with F12 as the key, it now jumps to F13 (issue #2042)
* reduced the overhead on two important 'wait a moment' checks that many of the thread workers consult. previously, when checking if the pubsub or db were busy, threads would wake too frequently in busy periods and thrash as they competed for 'is busy' locks. now the pubsub and db themselves maintain a single 'I am idle' signal the waiters can wait nicely on without needing extra checks
* the code that terminates and then kills a timed out subprocess (ffmpeg, typically) now catches permission errors better (issue #2046)
* fixed a stupid typo from the non-interactive `setup_venv.py` mode that broke the 'advanced' manual, interactive install. I was so focused on the new thing, I didn't test the old thing to see it still worked

### client api

* fixed the new `/manage_pages/new_page` command for a 'page of pages' type and updated the unit test to catch this (issue #2044)
* client api version is now 94

### human-readable metadata fix and improvements

* a user noticed my recent 'chara' file metadata parsing was causing issues for files with metadata that included non-text datatypes and spotted where it was happening. just a stupid logical typo that was causing a bunch of filres with human-readable metadata to parse as not having any at all. I have fixed this issue so these files will show up with metadata again, and it will render correctly
* any image imported after june 2nd (v674) will get a 'has human-readable metadata?' rescan
* I have hidden the 'progression/progressive' keys from human-readable metadata presentation; we scan this elsewhere and show it as 'progressive? yes/no' on the same panel. I think I'd like to do the same for some other stuff like the 'jfif' and 'dpi' gubbins you often see

### modern animations and ffmpeg

* tl;dr: fixed some video parsing bugs with the new ffmpeg 8.x.x. avifs and heifs with num_frames=1 should be fixed, you do not have to do anything
* many users, including all windows built users, have been on ffmpeg 8.x.x for a while now, and my video metadata parser recently broke for the animated 'sequence' variants of AVIF, HEIC, and HEIF. these files were being parsed with a num_frames of 1 and rendering as just a still image or throwing an error depending on the renderer
* hydrus now recognises when any video file has multiple tracks, and if one track seems to be just a still image file, it selects the true animation stream for fps calculations and so on
* also, the native renderer will now recognise this situation; if there seems to be no second frame during a render run, it will inspect the file closer to see if there is a different video track to select
* also, I updated the deprecated `vsync` ffmpeg call to be `fps_mode`. this was another source of errors for various native rendering with modern ffmpeg
* also updatedk the old `-s` to a combined `-vf` line with optional crop
* also updated the overcomplicated `-f image2pipe` to `-f rawvideo`. works the same, but it is semantically better and may fix some frame timings
* also updated the core metadata parse routine to no longer render the first second of the vid at small scale since this is an old hack that burns CPU but isn't used for anything any more and crops resolution parsing to 120 height for certain formats in ffmpeg 8.x.x (old mpegs at least, by my test)
* all animated AVIF, HEIF, and HEIC files are scheduled for a metadata reparse (issue #2041, #1891)

### new thumbgrid drawing tech

* I found some time to work on the new thumbgrid test. it is better integrated and I fixed some bugs, but there's still some stuff not working so I'll hold off on the wider test
* so, just as a record, I did--
   - fixing up some type hints
   - misc refactoring
   - undoing thumbnail movable/selectable flags to stop some inherent Qt behaviour stepping in on mouse events (this fixes ctrl+click selection, which was being pseudo-randomly undone I think in the QGraphicsScene event handling)
   - thumbs now have their own selection bool
   - moving click-event/selection responsibility to the GraphicsView since thumbs don't do anything but call the parent atm anyway
   - fixed thumb resolution stuff for non-resolution-having media when cache entry is invalidated
   - made thumbnail 'media' (and the new 'is_selected') bools public
   - tiny bit of thumb gen optimisation

## [Version 676](https://github.com/hydrusnetwork/hydrus/releases/tag/v676)

### more UI updates

* thanks to a user, we have a slew of additional UI improvements: (#2037)
* per-viewer mute under media viewer right-click menu!
* slideshows can now shuffle and 'play media once through' on a per-viewer basis
* the 'stop' slideshow menu entry now shows the current slideshow period
* a new type of 'interactive' shortcut action, for the media shortcut set. you set a tag or rating service but nothing else. when you hit the shortcut, it asks you which tag or rating you want to set!
* new options to choose which types of zoom 'zoom switch' switches between and configure how collapsed the 'eye menu' is under `options->media viewer hovers`, in the new `top hover button/menu controls` panel
* persistent 'be silent on crashy stuff' mpv option unher `help->debug->debug modes`

### misc

* the `-d` launch parameter for the program now expands a userpath db path correctly. `-d=~/hydrus` now resolves to your user dir properly
* in the parsing UI, the 'test' panel's preview area, where it shows what you downloaded/pasted, will now show up to 500,000 characters before clipping (up from 65536 chars), and the upper description is now clear when this happens
* added `TEST: import local files directly from source, do not copy to temp dir beforehand` option to let some advanced users try out direct import. we needed to copy to tempdir in the old days so that some media scanning libraries would not have to deal with cyrillic or other uncode characters in paths, but this situation seems to be resolved these days, so let's try without. if it works ok IRL, I'll keep this for those who do still need a temp dir interim but flip the default behaviour

### stylesheet paths

* me and the guys who make qss stylesheets have been fighting an issue for a while regarding loading external assets, like a little .svg for a button. I solve this today, and it will make loading up stylesheets with assets from your db dir or in the built release much more reliable
* anyone who was on the `_built_release` versions of the stylesheets will be migrated to the normal ones on update. the `_built_release` versions are deleted from the defults qss dir as the problem they addressed is solved in a better way
* for the specific change, the new 'absolute path qss test mode' proved successful, so it is now the norm. stylesheets now have to specify their paths in one particular way and I handle the path juggling on my end, on load. the readme.txt in the qss dir is now explicit about this, so if you make qss stylesheets and haven't seen it yet, check it out

### opening new pages with the client api

* thanks to a user who did a really comprehensive job, the Client API gets a new `/manage_pages/new_page` command. it covers pretty much everything, including, say, a new local import page with a list of files. check out the new documentation here: https://hydrusnetwork.github.io/hydrus/developer_api.html#manage_pages_new_page
* the user also fixed Client API file sorts not defaulting to asc=true and a focus issue when pages are closed
* the Client API version is now 93

### parsing logic fixes

* _this is for advanced users who make downloaders_
* with the help of a couple users who poked around my tangle of gallery parsing code, I think we've fixed some stupid parent-child inheritance stuff where a gallery object would take too manytagsfromcertainpostparsesandthenpassthatontoa'nextpage'galleryurl,particularly,say,ifthatnextpageurlwasauto-generatedbtwmyspacebarbrokewhenwritingthis (issue #2035)
* keyboard fixed. so, I KISSed how gallery objects create child file import objects and sub-gallery urls and next-page gallery urls. there is less overlap of responsibility between an object passing metadata down and a post parse passing metadata down (this latter system is much better these days, and old hacks in the former pipeline were causing the main issues here). gallery import objects will now not update themselves with parsed tags and referral urls after the fact; only their children will get the metadata from their parses
* relatedly, I cleaned up how file objects create child file download objects. previously, there were separate pathways for file parses that uses subsidiary parsers vs those that simply had a flat content parser that produced multiple urls and then another for a single url that turned out to match a post url class. this has all been collapsed into a single KISS route that says 'if one file url, eat up the metadata from the parsed post and then download it; else create n child objects'. some bespoke error states like 'hey I grabbed one url, it was a post url, but there's no parser for that url' are now deferred and will just get processed as a normal child file import object
* also cleaned up some crazy python module inheritance happening here
* overall, things should be more reliable, and the inheritance of metadata from one import object to the next should be clearer. let me know how it all goes for you

### source setup

* `setup_venv.py` now takes an optional `-i` parameter for non-interative (i.e. automated) installs. `-i=s` will do the simple mode, `-i=a` will do the advanced mode with all test/yes choices
* `setup_venv.py` now expands a userpath venv path correctly. `-v=~/hydrusvenvs/venv313` now resolves to your user dir properly

### safer builds

* thanks to a user, our github build scripts, including Docker, now freeze the various github actions we use (e.g. a thing that says 'ok grab that build zip you just made and upload it to the release') to known good sha256 hashes, rather than getting the latest, say, 'v6'. this insulates against a supply attack, like we've seen recently, ensuring we won't use an action that was updated two hours ago by a bad guy to do bad things
* there's a script also that updates the hashes. I'll be running this regularly to keep up and verifying every time it does. dependbot apparently interrupts whenever it is a big deal, too

### startup/shutdown

* the `twisted` library, which we use to host the client api and server services, is now started and stopped in a nicer way. previously, it was hacked into the boot scripts. now the main hydrus controller handles it and delivers some additional hydrus shutdown signals
* `twisted` now only spins up on the client if you actually start up the Client API
* when 'shutdown report mode' is on, the final client exit moment now prints all alive threads with their name and daemon status. if you have been working with me on the 'program is down but process is still alive', let's see if this catches it

### some help docs work

* rearranged and brushed up the Linux section in 'getting started - installing' and added more notes/links to 'hey running from source is over here'
* removed the old Win 7 support comments and updated the Win 10 bits to be 'time to move to Linux m8'
* updated the 'running from source' help to talk about `pyenv`, which makes it easy to install and use a different version of python with hydrus
* updated the 'running Windows version in Wine' help document for the newest version and added info about Bottles: https://hydrusnetwork.github.io/hydrus/wine.html . I managed to get v675 up with a minimum of fuss and not too much weirdness (even ffmpeg and mpv worked!?!), so I now have a basic Windows test environment, hooray. doing it manually with winetricks on my system wine-9.0 did not work, it needed Bottles's newer wine-11.0
* added easy copy buttons to the command quotes in 'running from source' help

## [Version 675](https://github.com/hydrusnetwork/hydrus/releases/tag/v675)

### misc

* the command palette will now _not_ highlight an item if the initial results list opens underneath the mouse. I'm trying to resolve a common annoyance here, but I don't use this much IRL, so let me know how this feels to you
* the new 'recognise an unmounted NAS as similar to a missing path on boot' error catching now detects a locked bitlocker drive on Windows. updated the UI text in the dialogs around this, too
* fixed an unhelpful old status check that said 'if all network traffic is paused, repository sync maintenance daemon will not work', which was blocking local-only repo processing
* added a link to 'Hydrus Slideshow Frame', a user-made KDE Plasma Widget for a hydrus photo/slideshow frame, to the Client API help (https://github.com/apampurin/hydrus-slideshow)

### custom stylesheets

* A hydrus user created a bunch of great 'Nereid' stylesheets right here: https://github.com/6788-00/nereid-theme-hydrus . these are now rolled into hydrus by default
* for stylesheet creators, I had an idea how to fix the external asset relative/absolute path problems we've had. I have written a test and would love to have some feedback on Windows and macOS. To do the test--
    * create/copy a new stylesheet into your `db/static/qss` folder. change any 'url' paths from any existing `url("path/to/my/db/static/qss/blah/my_image.svg")`, to `url("static/qss/blah/my_image.svg)`, as if it were loading from and relative to the install dir. if you are copying from the install qss dir, maybe the paths are already in this format
    * hit up `help->debug->debug modes->qss absolute path test mode`
    * load your QSS file in the `options->style` section. ok the dialog if you need to hunt around for an asset. did the assets load ok?
* let me know how it went. in that test mode, I detect paths in the normalised format and swap them with the absolutes on load. if things worked multiplat, I'll make this normal behaviour and this problem is fixed

### new thumbnail GraphicsView test

* a user has rewritten my ancient old thumbnail grid to a new Qt-nice rendering system. I really appreciate his work. I have integrated his code as a new test, and early results are very promising
* it is not ready for normal use yet and still has bugs/jank. it is under `options->thumbnails` as an EXPERIMENTAL TEST, DO NOT CLICK checkbox
* I'll keep working on this, but as it matures, we should have masonry layouts, vertical grids, more dynamic thumbnail sizes, and all sorts, all in a nicer drawing system with more animation options and so on. some bad old design ideas are being swept away at the same time

### boring cleanup

* if `twisted` (the networking library we use to host a server) fails to un-set the current hosting services on program close, the error is now printed to log. previously it was silenced. I'm narrowing down on a 'the program seemed to shut down but the process is still alive' issue, and I think it might be an overloaded/deadlocked Client API doing it
* updated the 'help my db is broke' file a little regarding clone vs repair
* fixed a note in the example .desktop file
* did some misc linting
* fixed missing executable permissions on the scripts in the main repo. sorry for the long-time problem here

### new dev machine

* just as a side thing, over my vacation I moved to a new dev machine. I'm finally on Linux to dev. I took the opportunity to rework my very messy dev environment and personal workflow and note-taking. my situation is far less stupid now, with a sensible and pleasant IDE connection to the github repo, a browser not overflowing with tabs, and a zeroed-out desktop and daily todo and such. I've got dozens of pages of overflowing note mess to still slowly work through, but I'm going to devote some specific sunday work time to project management and try to stay on top of it going forward!

## [Version 674](https://github.com/hydrusnetwork/hydrus/releases/tag/v674)

### misc

* you can now customise how mouse wheel events propagate out of the hover taglist in the media viewer. this has had a variety of hacky/patchy behaviour before; now you can hit up `options->media viewer hovers` and tell it to: never propagate; propagate only if no vertical scrollbar; propagate only if vertical scrollbar hasn't been used recently (the new default behaviour); and propagate immediately after scrollbar hits an end (which is what Qt _wants_ to do). this new 'has been used recently' tech locks you in the outer or outer context and uses a little voodoo, but I quite like it (issue #2024)
* thanks to a user, the human-readable embedded text section in the media viewer little button up top will now decode and show an embedded `Character Card V2` spec. previously, it would just dump the json string under 'chara', but now it looks a good bit better
* the help docs built into the Windows and Linux builds and the one built by the 'build_help.py' script by users running from source are now built in a more strict offline mode that caches the javascript for search tech locally. a user noticed they were previously fetching something from unpkg.com. now they should work properly even on a completely offline machine (iissue #2023)
* a variety of file existence checks and merge functions now check for 'hey this seems to be a remote storage that is disconnected/timing out' error states. previously these guys were just doing 'file does not exist' catching. this means booting the client with your NAS defined in some way but not mounted has nicer error handling. you'll get the repair locations dialog with an updated message rather than 'oh god unhandled boot I/O error aieeeee'
* added 'shutdown report mode' to the `help->debug->report modes` menu. this will report the shutdown calls, shutdown exception catches, and actual mainloop shutdown of all the program's thread workers and other mainloop daemons, with the intention of helping figure out some situations where the client will exit seemingly fine but with a silent low-resource process lingering (we think it is a thread orphaned from the signalling system or otherwise stuck in some deadlock)

### cookies.txt and expiration fixes

* when importing cookies.txt, 'session' cookies (i.e. those with no expiry) are now imported correctly. previously, they were being parsed as 'discard immediately' and were not being preserved
* fixed issues with sessions not saving new cookies after import via cookies.txt or clipboard if the user closed the client before that session was actually used in a request
* I hadn't realised, but hydrus was not being very aggressive about clearing 'session' cookies. after thinking about it, this is now intentional policy. I will add some buttons/options around this in future

### some repository account refresh cleanup

* the way repositories sync their accounts is a little cleaned up. clicking 'refresh account' is nicer and more reliable now
* the awkward and confusing 'network'/'hydrus account' panels in 'review services' for a repo are now merged into one expand/collapse box called 'hydrus service'. service status/errors usually appear on the top box while most people need the bottom; now you always see both at once. hope this makes some 'oh, everything is paused' situations a bit clearer
* the 'message' status text line in the 'account' panel now hides if there is no server message to show. this guy was just a weird UI gap for pretty much everyone
* 'refresh account' no longer disables itself when a repo is non-functional. this was another 'technically true, but not helpful' UI thing. if you click it, any blocker now gives a richer reason, with several generic 'account cannot sync right now' reasons replaced with the actual part of bandwidth tracking or whatever that is complaining
* if you try to hit 'refresh account', it now recognises if all network traffic is currently paused and breaks out early. previously, it would grey out and wait indefinitely until network traffic was unpaused
* a 'refresh account' call no longer sets a temporary 'unknown/unsynced' account to the service. if the fetch job fails, you keep the old account info
* errors from 'refresh account' are no longer put into toaster popups
* the 'tag filter' button for tag repositories is moved from 'network sync' to the new 'account' panel, beside the permissions button

### curl_cffi

* the recent test of `curl_cffi`, which adds http 2 and 3 support to hydrus, has proven successful. I am maturing the test and allowing a permanent on setting
* you now set the browser name under `options->connection`. http version selection is removed from the test--it seems it is doable and simpler to just let `curl_cffi` figure that out
* the setup_venv.py script now asks if you want `curl_cffi`
* `curl_cffi` is disabled for hydrus servers for now; we had some chunking issue when downloading from the PTR

### domain manager background work

* I moved forward my plans to launch a nicer unified 'here are the current statuses and settings for each network domain' UI and options system. this thing will eventually manage per-domain error timeouts, custom headers, perhaps some proxy settings, curl_cffi, and have some UI for recent errors. we'll migrate the stuff in `options->connection` to a 'global' entry and then allow more specific network context settings for particular domains; the usual deal
* I was thinking I'd launch a stub of this system to allow for a per-domain `curl_cffi` test, but I didn't want to rush it out, so I just kept to prep work and there's nothing launching here yet. I rounded out the objects I already had and verified the direction I'm going; I feel overall good about it

### boring stuff

* refactored some of the 'render human-readable data' method for KISS
* fixed some multi-line indenting in the human-readable rendering routine
* KISSed some inelegant 'clear expired cookies' calls and code
* added `help->debug->scan file storage folders`, which is just a test for a folder precache thing that I removed at the last minute last week when it performed terribly on an IRL spinning HDD. I rewrote it and will do some more testing
* cleaned up some error handling in 'server busy, try again later' parsing

## [Version 673](https://github.com/hydrusnetwork/hydrus/releases/tag/v673)

### misc

* the file history chart now has a custom y axis range. also, the chart now remembers if you have set either axis custom and new searches will auto-refit or maintain current dimensions as appropriate. hide/showing the lines will only recalculate the non-user-customised Y axis; let's see how that goes
* added a sanity check to the new fast 'give me the average character width' calculation, which is used for some scaling-agnostic UI sizing. one user (on a monospaced font, no less) had extremely wide average character width; I guess the font has funny kerning or extended characters or something. if the average character width is more than twice the reported height (which appears to be more reliable), I now fall back to a slower but more accurate calculation
* you can now edit the Access Key of a Client API permissions entry (a user mentioned they were migrating to a new client and updating every existing script to use new random keys was a pain). since you don't want to do this casually, it works through a button that gives a little spiel and tests the new key for validity and such, and the final ok will bail out if you paste something already in the system
* updated some system predicate parsing to support `<=` and `>=` operators, along with some variants like 'less than or equal to'. the types now supporting this are: width, height, duration, number of frames, number of words (issue #2019)

### new help docs for the recovery.txts

* added a 'Recovery' headline section to the help and migrated the .txt recovery docs to basic markdown
* the basedir 'help my client will not boot' is migrated to here
* all the .txts in the db dir like 'help my db is broke.txt' are migrated to here
* as planned, the `static/db_files` dir is removed. you no longer get a bunch of .txts in any new db folder. feel free to delete any old ones you have, but it isn't a big deal

### local file parsing optimisation

* when you drop a folder on the program, the main scan of that folder is a good bit faster than before and will scale a bit better
* when you drop a folder on the program, symlink loops are now recognised and broken out of
* when parsing import files from a folder, the main parse object now uses several fewer drive hits
* checking for 'file is in use' requires one less drive hit

### faster folder checking on startup

* when hydrus boots, it checks for the presence of all file storage folders. on a normal client, this is 512 directory presence checks; on an advanced granularity 3 system, this is 8192. this time adds up on boot, particularly on a cold HDD. I have improved the regular test here to do just one hard drive hit per folder instead of two. also, especially for the bootup phase, these locations are now scanned for _en masse_ with a carefully efficient/failsafe top-level scan on the main storage locations, massively reducing the number of hard drive hits required here

### optimised caching tech

* a user identified that a hacky id-to-value lookup cache used in tag and hash database modules was not working great. under certain types of strain, it would churn, leading to memory bloat and fragmentation
* I have tried several solutions and figured out a fairly decent replacement (LRU cache, nothing crazy) that will not churn so much and has less overhead. there's some additional long-term work that needs to be done to solve the bloat problem fully (full weakref tracking of tags/hashes), but I'm overall happy. tag and hash fetching when you load media or do various other heavy database jobs is now a little more optimised in several ways, and in most cases causes less memory duplication and fragmentation
* while I was poking around here, I also overhauled the general LRU cache used by a bunch of UI-level guys. thumbnail refetch and image zooming back and forth may be a shave faster

### source environment cleanup

* as planned a few months ago, v673 cleans up the 'running from source' setup significantly. you shouldn't have to do anything unless you run from source and use a custom script to automatically recreate your venv. I delete some old redundant scripts today, so if you happened to set an executable permission on something a long time ago, git may moan at you about being unable to pull because of your pending changes. deleting the files and then pulling again should work
* the pyproject.toml file no longer has any groups. there's one setup, nice and simple. the venue to test alternate library versions is now `setup_venv.py` exclusively
* the old basedir requirements.txt is now removed
* the manual 'running from source' help is updated. you now do just `pip install .` for a manual, pyproject.toml based pip install, with no groups needed
* the .bat/.command/.sh versions of `setup_help` and `setup_venv` and `git_pull` are removed--use the multiplat .py files from now on
* the `open_venv.bat/.ps1` scripts and `auto_update_installer.bat`, which were just fun experiments, are deleted. if you need some rinky-dink scripts to pull off a very custom thing like this, I recommend talking to an AI to get exactly what you need for your setup
* to improve hydrus package security, all dependency versions in the pyproject.toml and setup_venv.py and the build requirement.txts are now pinned/capped to recent latest versions. anything that was `>=` is now `<=` for the version as of the 672 build. all library version updates will now be considered manually by human eyes in future builds
* relatedly, the windows ffmpeg version is no longer latest but pinned at `8.1.1`
* deduped the basedir license files and renamed to `LICENSE`
* wrote a very basic `CONTRIBUTING.md` to mention that public pulls are closed right now
* for KISS, I'll switch the builds from their requirements.txts over to the pyproject.toml in the next future build test

### boring cleanup

* moved some file parsing code out of `ClientGUILocalFileimports` to `ClientImportFileParse`
* jiggled some 'make this panel x characters wide' numbers after last week's character-width update. this generally meant clearing out old +2 padding hacks and shaving some 64 to 60, that sort of thing, and I fixed a couple of things that were a little out of whack or sizing the wrong widget
