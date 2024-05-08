---
title: Changelog
---

# changelog

!!! note
    This is the new changelog, only the most recent builds. For all versions, see the [old changelog](old_changelog.html).

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

## [Version 569](https://github.com/hydrusnetwork/hydrus/releases/tag/v569)

### user contributions

* thanks to a user, fixed a problem with the recent URL changes that caused downloaders examining multi-file posts to only grab the first file
* thanks to a user, all the menubar commands that launch a modal dialog are now suffix'd by an ellipsis
* thanks to a user, fixed an issue regarding KDE 6 quitting the program as soon as the pre-boot 'your database is missing a location, let's find it' repair dialog was ok'd
* thanks to a user, the application icon is fixed in KDE Plasma Wayland (and anything else that pulls icon from .desktop file). if you have been using a hydrus.desktop file and don't see a program icon, you should rename it to `/usr/share/applications/io.github.hydrusnetwork.hydrus.desktop` . more importantly, if you manage a package for hydrus--please output to this file path instead of `hydrus.desktop` if you make one
* thanks to a user, updated the `hydrus_client.sh` file to include `"$@"`, which passes parameters given to the .sh file to the .py call

### more on last week's URL work

* fixed the 'show the Request URL under "additional urls" submenu' thing on the file log list menu. I screwed up the logic and was effectively testing for when `1 != 1`
* the converter that generates a Referral URL now operates on the API/redirect conversion principle too--it normalises the Source URL to its 'Request URL' state--keeping defined ephemeral params and filling in defaults but dropping any extra gubbins not asked for--before applying the conversion
* fixed the 'manage url class' dialog to correctly display an example API/redirect-converted URL based on the new _request url_, not the _normalised url_ (so the api/redirect example will now show the new ephemeral params properly). this was working in requests correctly behind the scenes, it was just the example text box in the dialog that was showing wrong
* improved the 'is this query text pre-encoded?' test to check for `%hh`, where `h` is a hexadecimal character, instead of the hackier 'is % in it while not followed by whitespace or end of string?'
* improved/simplified/optimised the overall procedure that figures out if an entered URL is pre-encoded or not. this routine now only runs at the stage where a URL is ingested and it obeys the `%hh` rule. these ingestion points are currently: the text boxes in a urls downloader/simple downloader page; the 'import new sources' function of file log menus; a URL `ContentParser` in the parsing system; the test box in `manage url classes`; and the main gui's 'import url' landing pad, which is used by the drag and drop system, the clipboard watcher, and the client api's 'import url' command. note that this does not occur on 'manage known urls' editing, where you can do what you want with whatever, and I won't coerce it to anything

### misc

* fixed a variety of logical cases around &gt;0, =0, !=0, &lt;0 for the `NumberTest` objects I recently applied to system:duration and elsewhere. when it comes to file searching, files that have 'None' duration are now considered equivalent to files that have an explicit 0 duration in all cases. previously, I was trying to thread a needle where '=0' would find null results but &lt;x would not, and it was a mess. now it all works the same way. if you want to search for 'duration &lt; x' and want to exclude still images, either add a filetype pred or slap on 'has duration'
* improved the stability of the manual file exporter process. it was consulting an object in a thread that it shouldn't have
* improved the ability of the manual file exporter process to report errors on a very large export that encounters errors after the dialog has closed
* fixed the 'remember last used default tag service in manage tag dialogs' and its accompanying dropdown not saving their current value on options dialog ok. sorry for the trouble!
* fixed the system that truncates very long filenames (for export folders and drag and drop exports) on Linux when the exporter is also outputting a sidecar that has a long extra suffix
* the 'find potential duplicate pairs' routine that runs in idle time now properly obeys the work/rest times in `options->maintenance and processing`. previously, it was just the 'run now' routine that was resting in that way, and the idle thing was just doing a hardcoded 'work for 60 seconds every 10 mins or so'. thanks to the reporting user who cleverly noticed this
* the `options->connection` page now mentions your proxy needs to be `http://`

### boring stuff

* updated the windows setup_venv.bat to allow for custom python or venv locations using parameters. this was so I could set up a multi-python testing situation easier
* added some unit tests for the new URL encoding gubbins
* improved un-encoded URL parsing in the downloader when the URL is relative and needs to be joined to the source url
* improved some URL parsing and ingestion to better handle urls with non-ascii characters in the domain
* replaced several 'does it start with "http"?' areas with a better and unified scheme/netloc test
* wrote a routine to split URL paths into path components, and spammed it everywhere so this code is now unified. I expect we'll get a `PathComponent` class at some point, too. there will be a future question about what to do with double slashes, `//` in paths--it turns out the logic has been mixed here, and I think I will probably collapse them to `/` in all cases
* rewrote an unhealthy call that indirectly caused the above multi-file post parsing problem
* fixed some None/0 `NumberTest` stuff if you manage to enter '&lt;0' or &gt;-5 and similar
* I figured out the problems with PyInstaller 6.x and some other stuff, there should be a 'Future Build' alongside this release in github for advanced users to test with

## [Version 568](https://github.com/hydrusnetwork/hydrus/releases/tag/v568)

### user contributions

* thanks to a user, the new docx, pptx, and xlsx support is improved, with better thumbnails (better ratio, better icon itself, and sometimes an actual preview thumbnail for pptx), better file detection (fewer false positives with stuff like ppt templates), and word count for docx and pptx. I am queueing everyone's existing docx and pptx files for a metadata rescan and thumbnail regen on update
* thanks to a user, the cbz scanner now ignores the `__MACOSX` folder
* thanks to a user, setting the Qt style in *options->style* should be more reliable (fixing some name case sensitivity issues)
* thanks to a user, there's a new 'default' dark mode QSS stylesheet that has nicer valid/invalid colours. we'll build on this and try to detect dark mode better in future and auto-switch to this as the base when the application is in dark mode.

### misc improvements

* added a 'tag in reverse' checkbox to the new incremental tagger panel. this simply applies the given iterator to the last file first and then works backwards, e.g. 5, 4, 3, 2, 1 for start=1, step=1 on five files
* all _new_ system:url predicates will have slightly different (standardised) labels, and all these labels should parse correctly in the system predicate parser if you copy/paste
* the file log's right-click menu, the part where it says 'additional urls', is now more compact and will show the 'request url', if that differs from the main url, either because of the new ephemeral parameters or an api/redirect. it is now much easier to debug the various 'what was actually sent to the server?' problems!
* you should now be able to enter 'system:has url matching regex (regex with upper case)' and 'system:has url (url with upper case)' and it'll propagate through parsing. this definitely has not™ broken any other predicate parsing. you can enter url class names with upper case if you want, but url class names should now match regardless of letter case
* if you have added, edited, or deleted any url classes and try to cancel the 'manage url classes' dialog, it will now ask if that is correct
* added a new EXPERIMENTAL checkbox to _options->tag presentation_ that will replace emojis and other unicode symbol garbage with □. if you have crazy rendering for emoji stuff, try it out
* the tag summary generators that make thumbnail banners now wash their tags through the 'render tag for user' system, which will apply this new emoji rule and 'replace underscores with spaces'
* added the 'rating' parser from the default gelbooru 0.2.5 parser to the 0.2.0 parser; this should add for more 'rating' parsing from a variety of boorus

### misc fixes

* fixed a typo bug when deleting domain-based timestamps in the edit times dialog
* fixed the 'system:has url matching class (blah)' predicate edit panel's initialisation. it was always initialising to the top of the list, not remembering the 'default' or 'I want to edit this' value it was initialising with
* 'manage urls' now asks if it is ok to ok if you have any text still in the input
* you can now open the 'extra info' button (up top of a media viewer) on a jpeg if that jpeg has no exif or other human-readable metadata (to see just the progressive and subsampling info)
* updated the QuickSync link to its new home at https://breadthread.duckdns.org/

### append random text

* the String Converter has a new step type: 'append random text'. you supply the population (e.g. '0123456789abcdef') and the number of characters (e.g. 16), and it will append 'b2f96e8eda457a1e', and then the next time you check, '1fa591ad9786ea3b', etc... useful if you want to, say, make up a new token

### URL storage/display changes

* today I correct a foolish decision I made when I first implemented the hydrus downloader engine--handling and storing URLs internally as 'pretty' decoded text, rather than with the proper ugly '%20" stuff you sometimes see. I now store urls as the 'encoded' variant all the time, and only convert to the pretty version when the user sees it. this improves support for weird URLs and simplifies some behind the scenes. you do not need to do anything, and everything should work pretty much as before, but there is a chance some particularly funky URLs will redownload one more time if your subscription runs into them again (this change breaks some 'known url' checking logic, since what is stored is now slightly different, but this 99% doesn't affect Post URLs, so no big worries)
* so, while URLs still show pretty in a file/search log, if you copy them to clipboard, you now get the encoded version--pretty much how your web browser address bar works. I have made it show 'pretty' in the file log and search log lists, 'copy url' menu labels, and hyperlink tooltips, but in the more technical 'manage url classes' and 'manage GUGs' and so on where you are actually editing a URL, it shows the encoded version. let me know if I have forgotten to display them pretty anywhere!
* **IF YOU ARE AN ADVANCED USER WHO MAKES CRAZY URL CLASSES:** since URLs are now stored as the %-encoded version in all cases, component and parameter tests now apply to %-encoding (e.g. you are now testing for `post%5Bid%5D`, not `post[id]`). when your URL Classes update this week, I convert existing path component defaults, parameter names and defaults, and `fixed_text` String Matches for path component names and parameter values to their %-encoded value. I hope this will provide for a clean transition where it matters. unfortunately, if the String Matches were a regex or you were pulling a rabbit out of your hat with edge-case pre-%-encoded default values, I just can't auto-convert that, so please scroll down your crazier URL Classes and see if any say they don't match their example URLs!
* there's also some GUG work. when you enter a query text like `male/female` or `blonde_hair%20blue_eyes`, some new logic tries to infer whether what you entered is pre-encoded or not. it should handle pretty much everything well unless you have a single-tag query with a legit percent character in the middle (in which case you'll have to enter `%25` instead, but we'll see if it ever happens)
* these changes simplify the url parsing routine, eliminating plenty of nonsense hackery I've inserted over the years to make things like `6+girls blonde_hair`/`6%2Bgirls+blonde_hair` work with a merged system. this has mostly been a delicate cleanup job; long planned, finally triggered

### allow all ephemeral parameters

* URL Classes have a new checkbox, 'keep extra parameters for server', which will determine whether URLs should hang on to undefined parameters in the first stage of normalisation, which governs what is sent to the server. this is now default True on all new URL Classes! existing URL Classes will default True only if the URL Class is a Gallery/Watchable URL without an API/redirect converter (which was essentially the previous hardcoded behaviour). you cannot set this value if the URL has an API/redirect converter

### allow specific ephemeral parameters

* alternately, you can now specify single 'ephemeral token' parameters in the new parameter edit dialog. it is just a check box that says 'use this for the request, but don't save it'. these _are_ kept for the API/redirect URL
* if you are feeling extremely big brain, there is now a String Processor for the default value, if both 'is ephemeral?' is checked and 'default value' is not 'None'. this lets you append/replace your fixed default value with the current time, or, now, just some random hex or something! hence we can now define our own basic one-time token generators for telling caches to give us original quality etc...

### manage url classes dialog

* there's a new read-only text field with the 'example url' and 'normalised url' section called 'request url'. this shows either the example URL with its extra, ephemeral parameters, or it will show the API/redirect URL. it shows what will be sent to the server
* URL Class parameters now have their own edit panel, with everything available in one place, rather than the three-dialogs-in-a-row mess of before. also, the name and value widgets have locked normal/%-encoded text inputs that will live update each other, so you can paste whatever is convenient for you and see a preview either way
* URL Class path components also have their own edit panel. same deal as for parameters, but a little simpler

### client api

* the `/add_urls/get_url_info` command now returns `request_url` value, which is either the 'for server' normalised URL, which may include ephemeral tokens, or the API/redirect URL, just as in the new 'manage url classes' dialog
* the `/add_files/undelete_files` command now filters the files you give it to make sure that they are actually in your file storage. no more undeleting files you don't have!
* added a new `/add_files/clear_file_deletion_record` command, which erases deletion records for physically deleted files
* updated api help docs and unit tests for the above
* client api version is now 63

### boring stuff

* the client is now much more robust if any of its URL Classes do not match their own example URLs. it will boot, to start with (lol), and you can now open the 'manage url classes' dialog without UI error popups. manage url classes now notes which URL Classes do not match their own example URLs, for easy skimming
* the 'URL Class' class has a new buddy 'Parameter' class to handle param testing
* simplified some of the guts of URL normalisation, from path/param clipping to how API URL generation is navigated
* rewrote how the query string of a URL is deconstructed and scanned against your parameters. less chance of edge-case errors/merges and easier to expand in future
* when you paste a URL, some new normalisation tech tries to figure out if it is pre-encoded or not
* brushed up the URL Class unit tests to account for the above changes and added new tests for encoding, 'is ephemeral', 'keep extra params for server', default parameter string processors, and simple default parameter values (which must have been missed a long time ago)
* also broke the monolithic url class unit test into eight smaller (albeit ugly for now) pieces
* added a unit test for the new 'append random text' converter
* cleaned up some misc URL Class code

## Version 567 was cancelled, its changes folded into 568.

## [Version 566](https://github.com/hydrusnetwork/hydrus/releases/tag/v566)

### incremental tagging

* when you boot a 'manage tags' dialog on multiple files, a new `±` button now lets you do 'incremental tagging'. this is where you, let's say for twenty files, tag them from page:1->page:20. this has been a long time in the works, but now we have thumbnail reorganisation tech, it is now sensible to do.
* the dialog lets you set a namespace (or none), start point (e.g. you can start tagging at page:19 if you are doing the second chapter etc...), the step (you can count by +2 every file, instead of +1, or even -1 to decrement), the subtag prefix (so you can say 'page:insert-4' or something), and the subtag suffix (for, say, 'page:2 (wip)')
* the last namespace is remembered between dialog opens, and if the first file in the selection has a number tag in that namespace, that is the number the 'start' will initialise with. a bit of overlap/prep may save time here!
* the prefix and suffix are remembered between dialog opens
* a status text gives you a live preview of what you will be adding and says whether any of the files already have exactly those tags or have different tags under the same namespace (which would be possible conflicts, suggesting you are not lined up correct)

### misc

* added import support for .docx, .xlsx, and .pptx files (the Microsoft Open XML Formats). they get icons, not much else. they are secretly zips, so **on update, you will be asked if you want to scan your existing zips for these formats**
* when you move a window to another screen in a maximised state (e.g. on Windows you can do this with win+shift+arrow), the system that remembers window coordinates will now register and save this. the 'restore' window size is preserved from whatever it was on the previous screen while the 'restore' position will try to stay the same on the new monitor (e.g. if it was at (200, 400) on the old monitor, it will try to do the same on the new) as long as the window fits, otherwise it is moved to (20,20) on the new screen
* the 'edit string converter' panel no longer requires you to enter an example text that can be converted. you can see the error on the dialog, so if you don't want to fix it, or you just need to nip in and out testing things, it is now up to you
* if the database takes a long time to update, the 'just woke up from sleep' state should no longer trigger. the system thought the long weird early delay was the computer going to sleep
* the system that gives a popup and then a dialog when you have 165+ (and then 500+ or so) pages open is now removed. this was always a wx thing primarily, and Qt is much happier about having a whole load of UI elements. the main problem here is now memory blot and UI-update lag. this is now in the user's hands alone, no more bothering from me (unless it becomes a new problem, and I'll figure out a better warning test/system)

### boring code cleanup

* neatened how some manage tags ui is initialised. there's a hair of a chance this fixes the 'the manage tags dialog taglist is cut off sometimes' bug
* neatened how some pending content updates are held in manage tags
* manage tags dialogs now receive their media list in the same order as the underlying thumbnail selection, ha ha ha
* untangled some of the presentation import options. stuff like 'is new or in inbox' gets slightly better description labels and cleaner actual logic code
* fixed some type issues, some typo'd pubsubs, and other misc linting
* tried last week's aborted github build update again. the build is now Node 20 compatible

## [Version 565](https://github.com/hydrusnetwork/hydrus/releases/tag/v565)

### tag sorting bonanza

* _options->sort/collect_ now offers four places to customise default tag sort. instead of having one default sort for everything, there's now sort for search pages, media viewers, and the manage tags dialogs launched off of them

### tag filter

* when you copy namespaces from the tag filter list, it now copies the actual underlying data text like `character:`, which you can paste in elsewhere, rather than the pretty `"character" tags` display text
* brushed up some of the UI and help text on the tag filter UI
* fixed a couple places where the tag copy menus were trying to let you copy an empty string, which ended up with `-invalid label-`
* fixed some extremely janked-out logic in the tag filter that was sending `(un)namespaced tags` to the 'except for these' advanced whitelist in many cases. it was technically ok, but not ideal and overall inhuman

### concatenated source urls

* on rule34.xxx and probably some other places, when the file has multiple source urls, the gelbooru-style parsers were pulling the urls in the format [ A, B, C, 'A B C' ], adding this weird extra string concatenation that is obviously invalid. I fixed the parsers so it won't happen again
* **on update, you are going to get a couple of yes/no dialogs asking if you want to scan for and delete existing instances of these URLs**. if you have a big client, it will take some time to do this scan. the yes/no dialogs will auto-yes after ten minutes, so if you are doing a headless update via docker or something, please be patient--it will go through

### note sidecars

* the note->media sidecar exporter module now has a 'forced name' input. if you want to parse a single note from a .txt or .json that doesn't have a name, you can now force it
* the sidecard txt separator dropdown in the .txt importer module now has a 'four pipes (||||)' entry in the dropdown as a quick-select beside 'newline'. four pipes is a useful separator of multi-line notes content since it almost certainly won't come up in a normal note
* some tooltips and stuff are updated around here to better explain what the hell is going on
* added a unit test to test the forced name

### misc

* to help the recent shortcuts change that merged `numpad` variants of + and left arrow and so on into being seen as the `unmodified` variants, if you have a saved shortcut that _is_ still the `numpad` variant, it will now match the `unmodified` input when the merge mode is on. just means you don't have to remap everything with this mode on--everything merged matches everything
* added 'copy file known urls' to the 'media' shortcut set
* I forgot to mention last week that we figured out more native global menubar tech (where the top menubar of the program will embed into your OS's top system menubar) in last week's release, for non-macOS (some versions of Linux) users. the new checkbox is under _gui->Use Native MenuBar_. it defaults to on for macOS and off for everyone else, but feel free to try it. there was a related 'my menubar is now messed up, why?' bug that hit some people in v564 that is fixed today. sorry if you got boshed by this, since it was tricky to manually fix. in future, note you can hit ctrl+p in a default client to bring up the command palette, and then you can type 'options' and can open the options that way, if your menubar isn't working!
* fixed the `ideal usage` calculation in _database->move media files_ when there are three or more competing storage locations with two or more having a max size that is exceeded by their weight, and one or more having a max size that is only exceeded by their weight a little bit. due to a mistake in how total remaining weight was calculated in the little behind the scenes elimination game here, a location in this situation was exceeding its max size amount by a multiple of `1/(1-total_normalised_weight_of_restricted_locations)`, typically +10-30%. thank you for the report here, it was interesting to figure out!
* I removed a hack that made the repositories (like the PTR) work for users running super old versions of the client. the hack has now been in place for more than a year. if you run into repository syncing problems, please update to after v511!
* fixed a dumb status line in the 'check for missing/invalid files' checker thah was double-counting bad files in the popup
* fixed some media duration 'second' components being rendered with extraneous .0, like '30.0 seconds'
* fixed a db routine that fetches a huge table in pieces to not repeat a few rows when the ids it is fetching are non-contiguous, and to report the correct quantity of work done as a result (it was saying like 17,563/17,562)
* the new _help->about_ Qt platformName addition will now say if the actual platformName differs from the running platformName (e.g. if it was set otherwise with a Qt launch parameter)

### client api

* just a small thing, but the under-documented `/manage_database/get_client_options` call now says the four types of default tag sort. I left the old key, `default_tag_sort`, in so as not to break stuff, but it is just a copy of the `search_page` variant in the new `default_tag_sort_xxx` foursome
* client api version is now 62

## [Version 564](https://github.com/hydrusnetwork/hydrus/releases/tag/v564)

### more macOS work

* thanks to a user, we have more macOS features:
* macOS users get a new shortcut action, default Space, that uses Quick Look to preview a thumbnail like you can in Finder. **all existing users will get the new shortcut!**
* the hydrus .app now has the version number in Get Info
* **macOS users who run from source should rebuild their venvs this week!** if you don't, then trying this new Quick Look feature will just give you an error notification

### new fuzzy operator math in system predicates

* the system predicates for width, height, num_notes, num_words, num_urls, num_frames, duration, and framerate now support two different kinds of approximate equals, ≈: absolute (±x), and percentage (±x%). previously, the ≈ secretly just did ±15% in all cases (issue #1468)
* all `system:framerate=x` searches are now converted to `±5%`, which is what they were behind the scenes. `!=` framerate stuff is no longer supported, so if you happened to use it, it is now converted to `<` just as a valid fallback
* `system:duration` gets the same thing, `±5%`. it wasn't doing this behind the scenes before, but it should have been!
* `system:duration` also now allows hours and minutes input, if you need longer!
* for now, the parsing system is not updated to specify the % or absolute ± values. it will remain the same as the old system, with ±15% as the default for a `~=` input
* there's still a little borked logic in these combined types. if you search `< 3 URLs`, that will return files with 0 URLs, and same for `num_notes`, but if you search `< 200px width` or any of the others I changed this week, that won't return a PDF that has no width (although it will return a damaged file that reports 0 width specifically). I am going to think about this, since there isn't an easy one-size-fits-all-solution to marry what is technically correct with what is actually convenient. I'll probably add a checkbox that says whether to include 'Null' values or not and default that True/False depending on the situation; let me know what you think!

### misc

* I have taken out Space as the default for archive/delete filter 'keep' and duplicate filter 'this is better, delete other'. Space is now exclusively, by default, media pause/play. **I am going to set this to existing users too, deleting/overwriting what Space does for you, if you are still set to the defaults**
* integer percentages are now rendered without the trailing `.0`. `15%`, not `15.0%`
* when you 'open externally', 'open in web browser', or 'open path' from a thumbnail, the preview viewer now pauses rather than clears completely
* fixed the edit shortcut panel ALWAYS showing the new (home/end/left/right/to focus) dropdown for thumbnail dropdown, arrgh
* I fixed a stupid typo that was breaking file repository file deletes
* `help->about` now shows the Qt platformName
* added a note about bad Wayland support to the Linux 'installing' help document
* the guy who wrote the `Fixing_Hydrus_Random_Crashes_Under_Linux` document has updated it with new information, particularly related to running hydrus fast using virtual memory on small, underpowered computers

### client api

* thanks to a user, the undocumented API call that returns info on importer pages now includes the sha256 file hash in each import object Object
* although it is a tiny change, let's nonetheless update the Client API version to 61

### boring predicate overhaul work

* updated the `NumberTest` object to hold specific percentage and absolute ± values
* updated the `NumberTest` object to render itself to any number format, for instance pixels vs kilobytes vs a time delta
* updated the `Predicate` object for system preds width, height, num_notes, num_words, num_urls, num_frames, duration, and framerate to store their operator and value as a `NumberTest`, and updated predicate string rendering, parsing, editing, database-level predicate handling
* wrote new widgets to edit `NumberTest`s of various sorts and spammed them to these (operator, value) system predicate UI panels. we are finally clearing out some 8+-year-old jank here
* rewrote the `num_notes` database search logic to use `NumberTest`s
* the system preds for height, width, and framerate now say 'has x' and 'no x' when set to `>0` or `=0`, although what these really mean is not perfectly defined
