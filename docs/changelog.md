---
title: Changelog
---

# changelog

!!! note
    This is the new changelog, only the most recent builds. For all versions, see the [old changelog](old_changelog.html).

## [Version 639](https://github.com/hydrusnetwork/hydrus/releases/tag/v639)

### misc

* `system:number of tags` and `system:tag as number` have a nicer new namespace selection widget
* fixed the duplicate filter group mode finding a new group after the previous group was resolved. I messed this up in last week's rewrite and it slipped through testing
* huge multi-column lists handle large selections much more efficiently, particularly when they have lots of buttons. all the various logic that handles 'should this accompanying button be enabled?' and so on now uses calls that work much faster when there are thousands of items selected. in my tests, a sublist with 5,000 test items now updates to a new selection in under 30ms--previously it was about a second. similarly, pasting all those items to a new list now takes about six seconds, whereas previously it was locking up for ages and ages, perhaps forever (issue #1737)
* fixed an issue where the 'move media files' dialog was saying all files were in their ideal location if the thumbnail location override was not set. this was happening because an error was being quashed over-eagerly. if this dialog has a similar problem in future, you might get some spammy reports, but it'll show. also a side thing, the 'set' button of the thumbnail location override no longer disables if you have a path set--feel free to move it to a new location in one step mate
* the system that positions windows off the topLeft corner of their parent is now more forgiving of unusual window manager frame geometry. if you kept getting 'hey I just rescued a window from ( 24, -14 )'-style popups every time you open the options off a maximised main GUI, let me know what happens now--are your dialogs appearing offscreen, auto-repositioning to (0, 0), or is everything good now?
* if you are feeling clever and can get an OR predicate into the duplicates auto-resolution 'test A or B' comparator, it now works! I'll brush up the UI in future to make it easy to enter an OR here (issue #1790)

### potential duplicates discovery

* I have overhauled the daemon that looks for new potential duplicate pairs. this guy no longer searches for pairs during shutdown maintenance (I'm generally trying to retire shutdown work), but you can now tell it to run in idle and/or normal time, with separate work/rest settings under `options->maintenance and processing`
* your settings here will mostly reset to defaults this week, sorry! default is to run in idle time but not active time, with some conservative work/rest ratios
* a critical section of database code that finds outstanding eligible files to perform the similar files search on is now optimised for clients with larger numbers of files. there will be a one-time CPU cost for each search distance you run at, and thereafter this thing should run like greased lightning even if you have millions of files, reducing per-job overhead for all similar files search
* when you force work through the duplicate page 'preparation' tab, it now works through a pause/play button and there is no separate work popup; it now just updates the bar in front of you
* I'm interested to know how 'run in normal time' feels for clients that have a lot of imports going on. I haven't gone for instant reaction to new files yet, but if it is idling with all other work done it'll get to any new files within about ten seconds, and the auto-resolution system _will_ react instantly to new potential duplicate pairs. might be laggy, might be cool, might be confusing as files in downloader pages are deleted before your eyes. the super ideal here would be to collapse the whole operation into the single import job and return something like 'file was duplicate' instead of 'already in db' as the import status, but we'll see how this does
* the 'reset potential search' cog-button task now resets the search for all eligible files. previously, I was trying to be cute and only reset search for files that previously found a potential pair, but the, say, ~37% filled progress bar after reset was confusing and not actually what the maintenance task wanted. KISS

### profile mode

* `help->debug->profiling->profile mode` now works on Python 3.12+. newer version of python are more strict about how profiling operates in a multi-threaded environment, and hydrus's profiling now obeys these rules. it turns out hydrus was always getting some _slightly_ gonk numbers here in busy multi-threaded situations, or at least many jobs were being truncated, which explains some inexplicable results I've seen over the years
* profile mode is now split into four exclusive types--client api, db, threads, and ui. the menu and html help are updated to talk about these. most users will want 'db'
* 'threads' and 'client api' profiles will sometimes include a bunch of truncated 'EXCLUSIVE: (job) ran in 17ms'. this is me salvaging a difficult situation with a still-useful number. don't worry about it!
* Python 3.12+ adds some cool tools here, and I expect to expand to some 'profile everything going on mate' modes in future to capture deep Qt things my specific modes do not
* there's an ancient shortcut for 'turn profile mode on'. this now does 'db' profile mode; it'll probably do something else later, or I'll retire it

### boring stuff

* if you boot the client or server in a python environment that does not have the requirements.txt stuff installed, the client now recognises this and gives a nicer error saying 'hey, I think you need to reinstall/activate your venv', rather than the old 'hey you don't have yaml' error
* tweaked the client's critical boot error handling so that it shows a nicer english error message first and then the full traceback in a second dialog
* added some unit tests for OR predicates within Metadata Conditionals
* fixed a deprecated unit test call. thanks to the user who pointed this out. this is not the first time this specific thing happened, so I'm switching up my testing regime to catch this in future

### boring overhauls and refactoring

* wrote a new MainLoop Manager for the potential duplicates search and some maintenance and numbers caching
* overhauled the potential duplicates search tree maintenance call to have less overhead and be happier working in tiny chunks. it is now continually maintained throughout search work
* wrote a count cache for the shape search store for the new daemon (previously it counted manually); it is updated as the underlying store changes
* hooked up new notification paths for new shape search counts or brance rebalancing work. these paths are simple and comprehensive, so the new guy should be a bit more reliable for unusual file maintenance jobs and so on that may alter the search space a little
* added some safety code to the new similar files search daemon to stop an infinite loop if the search record store has non-searchable items for some reason
* cleaned up the Duplicates Page Sidebar maintenance page a bunch. there was just a ton of cruft to go through
* to untangle some imports, moved duplicate score and visual duplicates gubbins out of `ClientDuplicates.py` to a new `ClientDuplicatesComparisonStatements.py`
* collected pretty much all the profiling and query planner gubbins like start time and job count and printing tech from `HydrusController.py` and `HydrusGlobals.py` to `HydrusProfiling.py`. I cleaned a bunch of it up along the way
* brushed up some of the database migration help r.e. missing locations and the pre-boot repair dialog
* the core `CallAfter` method used by many thread-to-Qt comms is a tiny bit more stable/thread-safe
* misc linting work, including clearing out some legacy unresolved references

## [Version 638](https://github.com/hydrusnetwork/hydrus/releases/tag/v638)

### misc

* thanks to a user, epubs with svg or IBook image cover pages will now get nice thumbnails. epubs with html covers will no longer spam error info to the log
* the default pixiv URL Classes are tweaked a little so they now want to keep their `www.`. when I did the multi-domain url class update the other week, which unified domain parsing and normalisation, some `www*.` removal loopholes were fixed and suddenly the pixiv downloader had a bunch of redirects going on behind the scenes because they are still firmly a `www.`-preferred site. no great harm done or subscription inefficiency or anything precisely because these URLs are considered the same now, but it was ugly in places so I've cleaned it up on my end. what to do about `www.` in future is perhaps something to talk about, and in context of an eventual _en masse_ URL normaliser/converter--maybe URL Classes will get an option regarding `www.` so we can handle various legacy issues like this. also for some reason the 'pixiv file api' url class was saving associated urls, which I've turned off
* the media viewer's prefetch system has better error handling for images with unknown resolution
* when exporting files, if the export filename produced by the pattern is the empty string, it now (again) falls back to the file hash. in a recent round of rewrites, it was falling back to the string 'empty', so you'd get a scatter of annoying 'empty (7).jpg' filenames
* when viewing an animation with the native viewer, hitting the shortcut for 'seek media: negative time delta' repeatedly near the beginning of the video, either on a slow video or a paused one, will no longer let the viewer move from the 1st frame to the undefined 0th frame (issue #1793)
* updated the first/previous/next/last media viewer navigation arrows to .svg icons and renamed them behind the scenes to position_x so they line up better alphabetically
* brushed up my newer .svg icons with some nicer gradients and drop shadows

### duplicates

* several duplicates auto-resolution thumbnail lists now spawn full-fledged duplicate filters instead of media viewers. these will navigate the full list, not just the one pair, starting with the most recent pair you have selected. the lists that have this tech are: in the 'edit rule' panel, the 'preview' tab's 'passed the test' and 'failed the test' lists; and in the 'review' panel, the 'pending actions' tab's main list
* the duplicate filter here has the normal actions. I'd like to add 'approve/deny' buttons for the 'pending actions' panel in future
* the 'send pair to duplicates media page for later processing' button in this case now sends the pair to a new/existing page called 'duplicate pairs'
* the 'send pair to duplicates media page for later processing' button on the duplicate right-hand hover no longer has the 'fullscreen' icon, which was changed last week and doesn't work there any more. I gave it the 'copy' icon for now
* the iterative duplicate search routines that generate grouped or mixed pairs for the filter and the one that generates the count of the current search for a duplicate search context panel are now auto-throttled. they'll start at 4096 items and speed up (reducing overhead) or slow down (reducing system latency) based on live timings, aiming for about 0.5s per work packet, which for almost all users will mean a prompt acceleration. if you have been staring at a lot of '2,000,000/4,100,000 ... 0 found' duplicate progress texts recently, let me know if this changes things at all (issue #1778)

### referral url logic cleanup and policy change

* the downloader is now stricter about which url it will prime child objects to use as their referral url (i.e. the file result from a gallery hit, one of multiple file objects created by a multi-file post, or a 'next gallery page'). the referral url given to the child object is now, strictly, the same URL that was actually hit at the parent stage, _including_ redirects. if you use an API redirect, that is now the referral URL. if the server 3XX redirects you, that is now the referral URL
* previously, it was mostly the 'pretty', pre-API redirect URL used, unless it was for some reason set otherwise, and unless there was a 3XX, in which case it was always that(?). it was a mess. rather than trying to be cute, I'm going for clear and accurate KISS. if hydrus hits an URL, that's the referral for the child, unless the URL Class of the child overrides it, and if it overrides it, it overrides _it_
* advanced downloader creators will recall that URL Classes can override, nullify, or modify the given referral URL. if you have a delicate URL Class here that uses both an API Redirect and a referral URL regex transformation that presumably eats the pre-API URL as a base, I am afraid I may have broken your downloader. I hate to do this, but I need to clean up the logic here and I think my decision causes the least damage and makes for the most reliable new rule going forward
* when you right-click a file object and look at 'additional urls', it will now state if there is an API/Redirect, and what URL that will be
* when you right-click a file object and look at 'additional urls', it will now state if the referral URL is due to be modified by URL Class rules. the URL Class is of course that for the expected URL to fetch, i.e. after API/Redirect conversion
* when you right-click a gallery object in a gallery/check log, you now see an 'additional urls' submenu with the above API/Redirect and Referral URL stuff, and you'll see any fixed http headers
* note in this subject that as part of moving from `requests` to `httpx`, I'm strongly considering handling redirects myself, and that will appear in the logs here as a child object with the new URL. I'd like the logs here to be better logs of what happened, in full, with less voodoo
* issue #1789 is related here, but I don't think I have it actually fixed

### boring stuff

* moved the duplicates filter canvas (60KB now) to its own `ClientGUICanvasDuplicates.py` file
* overhauled the duplicates filter canvas to be agnostic about the source of its list of pairs to action. it now takes a new pair factory, and all async work to initialise the search space and do grouping and fetching and sorting is now handled on the side of the factory
* cleaned up some of the not-great async logic around here during the decoupling, which clarified some things, and committed some fresh sins too
* wrote a pair factory for the thumbnail lists
* misc URL handling code cleanup and variable normallisation
* added a couple notes regarding mpv and ffmpeg in macOS to the 'running from source' help; thanks to the feedback from users who recently made the migration

## [Version 637](https://github.com/hydrusnetwork/hydrus/releases/tag/v637)

### duplicates auto-resolution

* 'test A or B' comparators now support 'system:time', for the four main time system predicates (import time, modified time, last viewed time, archived time)
* 'test A against B using file info' comparators now support the same 'system:time' stuff, so you can now mandate, say, that "A has system:import time earlier than B". I also wangled a time delta in there, so you can say 'A was imported more than three months earlier than B' if you like
* I brushed up the comparator UI for time; instead of `<` and `=`, you'll see a vertical stack of 'earlier than', 'roughly the same time as' and so on. also, the deltas for `+/-` and the B delta are full time widgets, so you set the time you mean and don't have to care about converting to milliseconds. this all percolates to the comparator summary string too.
* same deal for `system:duration` in that panel--it now has a time delta for the absolute `+/-` test and the B delta, and has a time-aware summary string
* I added 'only earlier imports' variants for the 'visually similar pairs' suggested duplicates auto-resolution rules. I am sure there are many edge cases, but I feel that these are pretty good 'near-zero false positive' rules to try out
* the 'edit duplicate auto-resolution rules' panel now has export/import/duplicate buttons
* the 'comparison' tab of 'edit duplicate auto-resolution rule', where you edit comparators, now has export/import/duplicate buttons

### duplicates

* in the duplicate filter, jpeg subsampling and quality info is cached in a nicer, more thread-safe way. certain laggy calculation situations should be more stable. I am not sure if this was the source of the crashes some people have had, so if you still get them, please let me know

### misc

* for the new `/db/static` overwrite tech, a .png icon in the db dir now overrides an .svg in the install dir. if you chose to add it, I'll prefer it
* the star.png used for favourites buttons is now an svg
* the fullscreen_switch.png used in the media viewer is now an svg, and more like the typical icon for this
* I forgot to do some metadata regen on epubs last week, so any existing epubs probably got stretched thumbnails. soon after v637 boots, your epubs should double-check their resolution ratios and regen any busted thumbs (issue #1788)
* I overhauled one of the ways that threads can give Qt work to do, making it more Qt safe. there were about 80 calls that used this system, mostly stuff like initialising a label or focusing a button in the event loop immediately after a panel appears. fingers crossed, these will be much more stable in edge cases when, say, a dialog insta-closes before an initialising job can fire

### big brain subscription logic improvement

* when subscription queries compact themselves down to the (typically 250) newest URLs, they now recognise that child URLs ("Found 2 new URLs in 2 sub-posts.") should not be counted. in sites where the gallery pages have potentially high count and each gallery-parsed post URL can also each produce many files (e.g. Pixiv manga), 250 file import objects could only be, say, 21 top-level Post URLs, significantly less than the gallery page provides, and the safety checks here, which are tuned to recognise 100 contiguous Post URLs 'already in cache', were overflowing every n checks and causing some post re-downloads. hydrus should be better about recognising this situation
* the compaction routine does this by grouping file import objects into parents, including nesting parents, and only culling on the top level. when things are confusing, it tries to fail safely in complicated situations, on the side of reducing compaction aggressision
* if you have manga subs, they may well grow to be like 4,000 files. let me know how it all goes
* a similar bit of logic that tests the number of items found versus the pre-gallery-sync size of the file log now uses this tech to estimate that size (previously it did some hacky referral url checking stuff)
* thanks to the user who worked with me to figure this one out
* this is more evidence that I should write a layer on the database level URL storage for 'subscription x saw this URL', and then we wouldn't have such a problem

### base64URL

* String Converters can now encode/decode with Base64URL, which is a variant of Base64 that uses `-_` instead of `+/` and where '=' padding is encoder-optional (and not added here) to make inclusion in an URL parameter simpler
* when I _decode_ (convert from base64 to normal text) by base64 of either sort now, I add any extra `=` padding that is needed, no worries
* String Matches can now have a 'character set' of Base64URL (`^[a-zA-Z\d\-_]+={0,2}$`) or 'Base64 (url encoded)'' (`^([a-zA-Z\d]|%2B|%2F)+(%3D){0,2}$`)

### boring stuff

* removed the macOS build script and such. I left the macOS build files in place and copied my various .yml workflow scripts to `static/build_files/macos`
* fixed up some bad layout flags in the duplicates auto-resolution comparator edit panels
* swapped the trash and retry buttons in the gallery downloader page sidebar
* similarly moved the trash button to the end in the watcher downloader page sidebar
* wrote unit tests for predicate value testing (i.e. for Metadata Conditionals) for import time, modified time, last viewed time, archived time
* wrote unit tests for predicate value extracting (i.e. for relative file info comparators) for import time, modified time, last viewed time, archived time
* wrote unit tests for the new Base64URL encode/decode and added some clever stuff to check for the `+/-_` stuff
* wrote unit tests for the new Base64 character set filters
* fleshed out some of my Base64 unit tests to catch a couple extra situations
* wrote unit tests for my new query compaction parent-grouping tech and 'master url' counting routine
* moved the 'CallAfter' thread-to-qt calling system to a new file `ClientGUICallAfter.py`, and made it safer
* moved an overhead-heavy alternate Qt-safe CallAfter to this leaner pipeline
* renamed `PREDICATE_TYPE_SYSTEM_AGE` to `PREDICATE_TYPE_SYSTEM_IMPORT_TIME`
* the `NumberTest` init no longer flips from `+/-%` to `=` if the inherent 'value' is 0--this was not helping in duplicates auto-resolution, where the value is not used and in some cases initialises to 0
* updated the predicate object so null/stub preds (which until comparators generally only appeared in memory as autocomplete dropdown system preds) can always serialise
* if a menu item label is longer than 128 characters and thus...elides, the tooltip will no longer have doubled ampersands (generally affects urls in menus)
* added a catch to the `help->about` error reporting; if you have "sio_flush" in an mpv import error, I now say to try running from source

## [Version 636](https://github.com/hydrusnetwork/hydrus/releases/tag/v636)

### multi-domain URL Classes

* URL Classes now support multiple domains! you can set multiple fixed domains like `example.com`/`example.net` and multiple regex rules like `example\.[^\.]+`. if a given URL matches any of the patterns, the URL Class can now match
* in the URL Class edit panel, there's now a 'domain' box panel for it all. by default, you'll start in a simple mode with a single text input for a single domain, but you can flip to an advanced mode that shows two add/edit/delete lists for the underlying fixed and regex rules
* the 'match subdomains' and 'keep matched subdomains' checkboxes are also moved into this panel
* two new 'test'/'normalised' text boxes let you enter a test domain to see if your current rules match it, and what it will normalise to (think subdomains) according to everything set
* if you are a downloader creator, please play with this, but I'll say don't go crazy yet. I feel good about it all, but this is new ground so I don't know if there's something we haven't thought of. also obviously be careful with the regex stuff. learn the difference between `.` and `\.` or you might end up matching more than you think!
* I believe this tech is fundamentally cool though, and if you know a new site uses a particular content engine you already have support for (e.g. some specific booru), then just adding its domain to the list for the file and gallery page URL Classes should essentially activate the downloader for that whole site. only thing you'd need for a full downloader would be a new GUG. no new parser example urls or any of that stuff needed. as a little test on my dev machine, I was able to merge the e621, e6ai, and e926 URL Classes with minimum fuss in about two minutes and nothing broke!!
* in terms of layout and bells and whistles, I think we might want some import/export copy/paste stuff here, let me know how it works for you IRL. the lists were already huge, so I didn't wrap them in nice labels saying 'these are the raw domains' and 'these are the regex rules', but I think I may need to pretty it up. I also added collapse/expand arrows to the three main static boxes in the edit URL Class panel, so I hope that helps if you are dealing with twenty domains or something
* if you have an URL in the media viewer top-right menu that matches a URL Class more complicated than just one fixed domain, it now says the domain of the URL after the name of the URL Class. e.g. 'coolbooru post (somecoolbooru.com)', so you know what's going on

### unfortunate macOS App news

* this is the last macOS App I will be putting out, and there will not be a Silicon App from me. I am sorry!
* Github are retiring the old macos-13 runner (intel) that we have been using, and for the past few weeks I've been trying to build both Intel and Silicon builds on the macos-14 runner. unfortunately, I could not get the retroactive Intel one to build, and Silicon Apps have special signing requirements. I bashed my head at the signing problem, and I was very hopeful I'd have a 'future build' test this week, but unfortunately I ran up against a hard technical barrier and I do not have the time and macOS expertise to properly overcome it. I also suspect the self-signed hole we had hoped to fit through will be closed in the not so distant future. we've been coasting on a very hacky App structure for a long time, and it would need a couple full passes to work in the new system, so I simply had to call it. even if that overhaul worked out, we'd still be locked to older Python 3.10 due to pyoxidizer and looking at asking users to override Gatekeeper quarantine
* thus, I now recommend that all macOS users run from source going forward. although it is a small one-time headache to set up, it'll run much better than the old Intel App, which was likely being Rosetta'd to your newer machines. I have brushed up the 'running from source' help and written a small specific section for you here: https://hydrusnetwork.github.io/hydrus/running_from_source.html#migrating_from_an_existing_install
* all the help is updated to talk about there being no App build now; let me know if I missed anything
* let me know how you get on and if you have any trouble getting a source release going. I regret the sudden halt here, and while I understand there are still a few weeks of Github macos-13 brownout if we are desperate to get an App out, the writing is on the wall, so best to start on migrations now. I'll put reminder banners on the release posts for the next four weeks
* it is possible that another user will figure out their own an App solution in future, perhaps with PyInstaller instead of pyoxidizer, but it shalln't be me!

### B is not better

* a subtle bug caused auto-resolution rules with the action "B is better" to swap the AB to BA when pairs were in the 'pending a decision' queue in semi-automatic mode. I believe they were fine in automatic mode
* I have decided the maintenance debt for this command not justified, and it mostly just serves to confuse everyone, so it is removed from duplicates auto-resolution. I also removed it from the API docs (it'll still work there, and it seems to work well, but it isn't documented any more and I recommend anyone using it migrate carefully to use 'A is better' instead)
* in future I will add a 'swap A and B' button to the auto-resolution comparators tab so if you did set everything up wrong, it is still recoverable without frustrating the overall pipeline
* on update, all auto-resolution rules set to 'B is better' will pause and reset to 'A is better', and you'll get a popup about the situation
* thank you very much to the user who tested and reported this. it was unwise of me to throw this action in the mix, and another good example of KISS

### greyscale jpeg duplicate info

* in the duplicate filter, I now detect when jpegs are truly greyscale (i.e. actually 8 bits per pixel), and report that in the subsampling label. previously, greyscale were registering as 'unknown'. if either file is greyscale, the subsampling score is now 0
* the jpeg quality value is also adjusted for a greyscale image. they were reporting as slightly higher quality than they should have been when compared to an RGB equivalent. let me know how this works out IRL, though. I may need to tune it more
* the jpeg subsampling and quality comparison lines now have nicer tooltips explaining what they are

### epub covers

* thanks to a user who waded through some ugly xml, we can now produce thumbnails for EPUB files! should work for any EPUB 3 file that actually has a thumb
* I extended this to support EPUB 2 and some other broken files. I'll be interested in any examples that you think do have a cover but still don't have one in hydrus
* all existing EPUB files will be scheduled for a thumb regen on update

### client api

* fixed a 500-causing typo in `/add_files/generate_hashes/` for filetypes with a perceptual hash (issue #1783)
* added unit tests for both the path and bytes versions of this call so this won't happen again

### boring stuff

* the new retry svg icon has a brighter green arrow that stands out better in darkmode--thanks for letting me know
* after a user mentioned it, I optimised my new svg icons' filesize (with `scour`), and will continue to do so
* I rejigged the buttons in the duplicates page sidebar 'preparation' tab. my new rule is generally that cog buttons go on the right, as part of the thing they modify
* I may have fixed the alignment of the gallery downloader sidebar cog icon button in crazier stylesheets. if you still get the problem, let me know
* if a user runs into the 'It seems an entire batch of pairs were unable to be displayed.' duplicate filter error, all the pertinent rows are now printed to the log
* improved a little keyboard focus stuff on some small dialogs
* fixed an unstable list menu call that could cause trouble if the list was closed and deleted before the menu could show
* moved the 80KB-odd of URL Class UI code to a new `ClientGUIURLClass` file
* wrote some code to better handle and report critical hash definition errors during forced file maintenance
* network jobs that are expecting HTML/JSON no longer error out if they exceed 100MB. such jobs now spool to a temp file after 10MB. good luck to the guy with the larger-than 100MB JSON files
* when hydrus tries to import an expected HTML/JSON that doesn't seem to parse correct (just in case it is actually some raw file redirect), the copy from the network job to the import file temp location source is a smarter, low-memory stream. other work is still going to stay stuck in memory, however, so we'll see how it shakes out

## [Version 635](https://github.com/hydrusnetwork/hydrus/releases/tag/v635)

### misc

* with help from a user, the manual `file->import files` dialog has a new 'search subdirectories' checkbox, default on, that, if off, allows you to just search the files in the base dir
* import folders now also have a checkbox for 'search subdirectories', for the same thing
* the importer 'file log' menu now offers to remove everything except unknown (i.e. unstarted) items from the queue
* the `network->data->review current network jobs` window now has auto-refresh, with custom time delta
* if the client files manager runs into a critical drive error and subs, paged importers, and import folders are paused, the `file->import and export folders->pause` menu is now correctly updated immediately to reflect this

### cog icons

* after various discussions about 'advanced mode', I've decided to push more on cog icon buttons to tuck away advanced settings and commands. I hope to slowly slowly migrate most 'advanced mode' stuff to cog icons and similar
* I fired up Inkscape and made a new .svg cog icon. it will draw with nice antialiasing and scale up nicely as we move to UI-scale-scaling buttons in future. please bear with my artistic skill, but I think it is ok in both light and dark modes. the recent cool thing is, if it isn't to your taste, you can now replace/edit the file yourself and put a copy in `/db/static` and hydrus will use that instead
* the file sort widget, when set to namespaces mode, now tucks the tag service selector button and tag display type selector button (previously also only visible in advanced mode), into a cog icon button
* the file collect widget now always has a cog icon. it handles tag service and tag display type selection
* the file sort widget in 'num tags' sort now has a cog icon allowing tag service selection. the current tag service of the search page no longer controls the tag service in these sorts--you set what you want

### retry icon

* the 'retry failed' and 'retry ignored' buttons in gallery pages, watcher pages, edit subscriptions, and edit subscription panels are now collapsed into one new menu icon button. this liberates a row of space in the downloader pages
* lists across the program will update their button 'enabled' status instantly after various advanced commands now. if you see the list text change, the buttons should update

### boring stuff

* wrote a nicer menu templating system (old system was all horrible tuple hardcoding)
* the scrollable menu choice buttons now all use the new templating system
* the menu icon buttons now all use the new templating system
* the menu buttons now all use the new templating system
* wrote a 'cog icon' class just to keep track of it nicely across the program
* fixed up alignment and position (cog icons will now generally always go far right) of buttons in network job widget
* secondary file sort now applies within collections
* I did some prep work for allowing customisable secondary sort on any file page, but we aren't quite there yet
* replace my ancient 'buffered window icon' widget with a simple QLabel with a pixmap, affecting: the trash and inbox icons in the media viewer top-right hover, Mr Bones, Lain, and the 'open externally' thumb-and-button widget in the media viewer
* brushed up the grammar of the various 'text-and-gauge' stuff that I moved to always be zero-indexed the other week, particularly in the subscription popups

### boring url stuff

* updated `URLClass` to now hold a static one-domain `URLDomainMask` and use it for all internal `netloc` tests and subdomain clipping
* added raw domain rules to the new `URLDomainMask`
* added more `URLDomainMask` unit tests for this
* added a unit test to better check discarding subdomains at the url class level
* fixed 'www'-stripping alternate-url searching for urls with more components like `www.subdomain.something.something`
* the network engine is now more tolerant of non-urls, only checking strictly when you input into downloaders. previously, any normalise call on something that didn't parse would raise an error--now it is a no-op. the client api will respond to invalid `get_url_x` and `associate_url` URL params as best it can rather than responding with 400 (while still erroring out on `add_url`), and when you export urls with a sidecar, invalid urls should be outputted ok

## [Version 634](https://github.com/hydrusnetwork/hydrus/releases/tag/v634)

### hotfix

* I screwed up with a couple of bad typos in v633, and a couple bad bits of logic in the previous two weeks, so I ended up fixing it on Saturday and putting out a v633a hotfix. the full problems were--
* export folders doing work (issue #1775)
* setting forced filetypes
* the 'repair missing locations' pre-boot dialog
* the migrate files dialog when a path did not exist
* some weird webms
* sorry for the trouble and hassle--it looks like I just had some bad weeks recently and this just slipped through linting and my tests. I particularly regret export folders, since that isn't some super rare system, and I have written some a nicer unit tests to ensure they don't get hit by another stupid mistake like this

### inc/dec ratings

* thanks to a user, inc/dec ratings now grow to be as wide as they need to! this affects numbers over 999. their size options are now based on height rather than width (issue #1759)

### duplicates

* if the two 'jpeg quality' statements have the same label, e.g. 'high quality vs high quality', the score is now 0. previously, if the behind the scenes quality scores were 728 vs 731, it'd colour green and give points, which was confusing and over-confident
* last week's ugly 'group mode' checkbox in the duplicates sidebar is now a scrollable menu button

### duplicates auto-resolution

* the deny list is now available in a new tab in the 'review rule' panel, beside the 'actions taken' tab. it'll show the n most recent denied pairs, and you can undo specific pairs, which puts them back in the search queue
* tracking denied timestamps is new tech, so all existing denied pairs will get fake timestamps of 'now minus a few ms' on update
* the review panel now auto-updates the 'actioned' or 'denied' lists after you do actions or denies in the queue panel and then switch tabs

### ui

* I cleaned up some hacky sizing flags and minimum width calculations and several UI areas can now compress to a smaller space. this particularly affects the normal page sidebar--you should be able to make most quite a bit thinner, although for something with a multi-column list you'll need to manually shrink the columns yourself to get it to go down (issue #1769)
* almost all of the icons across the program (atm basically everything except what is drawn to thumbnails and the top-right hover) are now loaded `name.svg` first, `name.png` second. I do not use any svgs yet, but I am planning a migration, and this 'try to load an svg if it exists' is a base for testing. users who have been playing around with custom icons using the new `db/static` system are invited to put some svg icons in there and see what happens. as I do this migration, we are going to have to figure out a new sizing system based on visual units like current font size character height, rather than the fixed old (16x16) raster stuff
* a new `debug->gui actions->reload icon cache` forces the pixmap and icon caches to reload from disk, including your static dir stuff. it'll only affect _new_ widgets though

### boring stuff

* harmonised mismatched status text vs progress gauge display across the program. when you have a popup or similar that says 'working jobs: 3/5', this now means that three jobs are complete and it is working on the fourth. the progress gauge underneath will, similarly, now be at 60%. I accidentally showed 100% progress on the last job with the subscription query progress bar last week and noticed how off it looked, and when I looked at how I did it across the program, I noticed I was ad-hoc all over the place. I tried making it so '3/5' meant the third job was being worked on and having the gauge still be 40%, but I wasn't totally happy. everything now runs on the same system of 'report num_done' when there is both text and a gauge. I am open to revisiting it, perhaps just in certain places where the grammar is now odd; let me know how you find it
* progress labels no longer say x/y when x is greater than y--they'll now cap at y/y. a couple of odd situations, like uploading pending content while new content is coming in, could cause this--now it'll just cap at 100% for a little extra bit
* made the 'get free disk space for this path' checks safe for all possible disk errors
* wrote some unit tests for the new auto-resolution deny timestamp and rescind stuff
* reworded some 'declined' text in auto-resolution to all be a clear singular 'denied'
* replaced my old `mock` calls and dev requirements.txt stuff with `unittest.mock`--this stuff has been built into python for ages now
* as a test, migrated one of my unit tests to use `mock` instead of some hacky db wrapper stuff I do; strong success

### macos news

* the Github 'runner' that we use to make the macOS build is being retired soon. I played around with the newer 'macos-14' runner, which finally leaps us from Intel to Apple Silicon, and had some but not total success. the main App is going to be moving to Apple Silicon, but I think we'll be able to offer an Intel compatibility version too. there's still stuff to figure out, but I hope for a public test soon

## [Version 633](https://github.com/hydrusnetwork/hydrus/releases/tag/v633)

### duplicates group mode

* the duplicate filter now has a 'group mode', which will cause it to load one group of files that are all potentially related at a time. you'll process the entire group until there are no potential pairs left, and then a new group will be selected. if new potential pairs are added as a result of the first pass of dupe merges, you'll be given those to process, over and over, until there is nothing left, but for the most part, I think you will be able to process a whole group in one pass. it'll be interesting to see how it shakes out IRL
* if you manually skip all the pairs in a group, you will be asked if you want to change group
* if you know the duplicate filter, please give this a go. I think it might be annoyingly 'bitty' with groups of size 1, so I may bundle smaller groups together to make it all smoother, but if I do that I may want a slightly different x/y label presentation. I really like this when it works well, so once we are happy, I may make this the default behaviour for new dupe pages
* as a side thing, I believe I deserve an award for 'density of ugly UI' here for the checkbox, which has a right-border misaligned with the buttons above and below, the text, which isn't properly vertically centered on the checkbox, and the whole widget overall, which refused to center align how I wanted in the first place. this is another reminder to clean up some of my ancient layout tools, which often fail when I mix different widgets and layouts together. and maybe I should just make the thing a scrolling button like I do for file and tag sort stuff

### duplicates

* the duplicate filter comparison statements now include jpeg subsampling (444, 422, 420), with a little score weighting too. if you don't know, subsampling is a sort of 'data density' in how the image is drawn with light and colour. much like with jpeg quality, you can usually assume that bigger numbers are better, with 444 the gold standard
* the jpeg quality comparison line in the duplicate filter now considers subsampling. it is a little complicated since this is all hacky and there's a curve going on behind the scenes, but a `4:2:0` jpeg will get 0.85 the 'arithmetic power', and a `4:2:2` will get 0.92, of a `4:4:4`'s, which works out to dropping one or two 'high quality' to 'medium quality' qualitative bands, but I may have been too aggressive. thanks to a user who pointed out that quantization tables do not change with different subsampling levels
* several duplicate filter comparison statements are no longer hidden if there is no difference. for instance, if both files have the same jpeg quality, you now get a blue (0 score) line saying 'both are medium high quality'. having dynamic hiding here to maximise useful data was a decent idea, but, rather than streamlining the experience, it usually just increased cognitive load by bouncing the lines around and made successive similar pairs more difficult to track. similarly affected are: resolution, num_tags, and import timestamp; and has_audio, has_transparency, has_exif, and has icc profile (if either does)
* when two files are set duplicate and their metadata merged using the duplicate merge options, the url timestamps are now synced when both files have an url from the same domain, that being the destination gets the reasonable earlier timestamp of itself and the source. previously, the timestamp was only synced if the destination did not have an url in that domain already

### window positioning

* absent a saved record, media viewers now declare an ideal initial size of 1280x720. previously, this was alternately 240x180 or 0x0, and so when your media viewers were set not to remember their previous size, they were making some crazy small or completely hidden windows (issue #1768)
* media viewers are now correctly hooked up to the main gui when they do topleft/center parent initial positioning and gravity based parent sizing

### misc

* all subscription popups have an additional progress gauge for the queries. this should stabilise the width of sub popups, also
* all datetime widgets (e.g. under 'manage times') now have a 'now' button, beside the 'paste', to set the time to now
* the 'retry ignored' file log buttons now offer to retry 403s
* `help->about` now has boot time in relative and absolute terms
* added an ADVANCED checkbox to `options->media viewer` that lets you focus the main gui only when you exit a media viewer with a page/thumb 'focusing' action. useful if you use multiple viewers and are thinking about the focus stack
* fixed the default export path in `options->exporting` from saving incorrectly if the dialog was saved with it on a blank value. it was saving as the path of the db directory; now it should stay blank, and the export files dialog will default to `~/hydrus_export`
* wrote a section on loading your system Qt styles in the `running from source` help. a user seems to have figured out how to do it. if you have python experience and also have this problem, have a look and let me know how it goes. I'm going to _see_ if I can adapt my 'setup_venv' script to auto-detect the situation and optionally install the venv differently (issue #1767)

### boring stuff

* deleted a bunch of old and no-longer-hooked-up nitter url classes from the defaults
* reduced some unbalanced lag in the 'deny auto-resolution pairs' command in semi-automatic rules, with more than 4 pairs being denied at once
* refactored much of my old list chunking to a richer progress-tracking call
* refactored my hacky old inter-thread progress-gauge tracking to nicer calls on the shared status object
* fixed a GUG unit test that failed after the recent %20 thing. I think I last-minute changed the default value for that setting, after doing my main testing
* wrote a 'URLDomainMask' object to handle the future multi-domain URL Class update. lots to do up and down the pipeline to get this guy inserted, but the whole system will eventually support multiple regex domains per URL CLass. also wrote some unit tests for it

## [Version 632](https://github.com/hydrusnetwork/hydrus/releases/tag/v632)

### hotfix last week

* I did a v631a hotfix last week that fixed a looping network job(!!) under the particular conditions where a Post URL A1) used subsidiary parsers and failed to parse any URLs or, A2) did not parse anything generally, and B) had a certain environment, I think most probably ffmpeg version, that judged the respective html/json to _not_ be potentially importable. I am very sorry for this problem and I thank the users who reported it and helped me test
* I added additional safety checks to the file and gallery import objects to stop this type of error happening again. if an import job works and produces no status change, it will now auto-veto with an appropriate note

### misc

* the 'show the top-right hover window in the preview viewer' option has worked out well, and I like it a lot, so it is now default 'on' for all new users. also, all existing users will get it flipped to 'on' on update. if you tried it and decided you didn't like it already, sorry! hit up `options->media viewer hovers` to hide it again
* the 'page lock' system now correctly removes files when you remove them from _inside_ a collection (hitting 'remove' from a child media viewer looking inside the collection)
* the 'manage url classes' dialog's test text box is now much faster. it only needs to do CPU work on the first character you type, rather than being sluggish every time
* the 'manage url classes' dialog's test text box no longer steals focus from the text box on a match. you can now easily keep typing to discover a more specific url class
* added a DEBUG checkbox to `options->downloading` to turn off the legacy `%20` replacement in GUG generation (pasting `skirt%20blue_eyes` is interpreted as `skirt blue_eyes` when pasting query texts). all existing users will get this set on; all new users will get it set off. it isn't a huge deal, but if you need this off, try it out and let me know how it goes. like with the double-slash option beside it, I might quietly flip everyone to off in a year

### move-merge files

* the file 'locations' submenu now summarises which locations your files are currently in in the top row, in a flyout submenu
* the file 'locations' submenu now lists 'move (merge)' and 'move (strict)' actions separately. the 'strict' was the previous behaviour, and it only moves if the file is not already in the destination
* the shortcut command that handles local file domain add/move stuff allows this new move-merge action. existing shortcuts will have the 'if not already in destination', but perhaps you'll want the other, 'even if already in destination'
* this 'locations' menu stuff now shows the number of files to be added/move-merged/strict-moved
* this went through multiple reworks and namings. I'm still not totally happy with the verbiage and workflow, but it is powerful and clearly allows the various commands we want. I tried having a yes/no dialog that asked you whether you wanted a strict move or a move-merge, but it wasn't nice in its own way. I tried merging the two menus, but it make the eyes glaze over. I thought about removing the strict move entirely, but I'm not ready for that. in the end I went with a clear verb-first approach with separate submenus. let me know what you think with IRL situations and if you can think of something better than 'strict'/'merge' that isn't too long so it fits nicely in a menu

### duplicates

* you can now set the pair sort for the manual duplicate filter! I've got 'filesize of larger file', 'filesize of smaller file', 'similarity (distance/filesize ratio)', and 'random' to start. have a play with them, let me know what you think, and what others you'd like
* in the duplicate filter, if either file is an image project file (e.g. PSD), or somehow an application/archive, the 'psd vs jpg' line now has a score of -100, either way around. should pop out a bit more now
* the 'show some random potential duplicates' button now works on the fast fetch system. it builds its results far quicker than before in all typical situations, and in general worst-case performance is very much improved
* the 'show some random potential duplicates' button now delivers what I will be calling an entire 'group' of potential pairs. previously, it selected a master file and showed you every file potential to it; now we chase down everything that those potentials are potential to, and so on, until we have everything that is transitively potential in one blob. should let you see more fuzzy (alternate) groups in one go. there's a little voodoo going on here, so let me know if you get any interesting results
* the 'show some random potential duplicates' button now sorts the returned group according to a normal file sort widget, which is embedded just above the button. this guy works like a normal sort widget and will save and re-sort whatever is in the current page on changes; it is just in a different location. not sure I like it, but we'll see how it goes
* the 'x potential pairs searched' part of the new duplicate pair iterative fast-fetch system is now pre-filtered to the current file domain. pairs that are in deleted domains and stuff are no longer confusing things, and a search of 'system:everything' should now always come back with a 100% count. also, if you search in a small local file domain, let's say it only has 3,000 pairs of your total of 500,000, any duplicate search now only has to iterate over that 3,000 every time. a little extra CPU is required to figure this out in the pre-search phase, but I think it pays off. let me know how it is IRL
* the comparison statements and scores in the duplicate hover window on the right are now split into fast and slow loading and are loaded and displayed in two separate jobs, so a laggy visual dupes test won't hold the rest up. for now, slow means the jpeg quality comparison and visual dupes test
* 'they are visual duplicates' results now deliver -10 score if they are not duplicates on the simple scan and -5 if they are not duplicate on the detailed scan (and thus get red instead of blue text). I can't deliver a positive score here since this test does not reveal which of A or B is better, but on a negative we can bias the score to say they aren't dupes

### duplicates auto-resolution

* 'test A or B' comparators now support `system:tag (advanced)`, so you can test for the presence/absence of a tag on a specific domain. I hacked this in a little and 'current domain' will be 'all known tags' for now; It'd be nice to show that better in UI
* 'test A vs B' comparators now support `system:number of tags`. no namespace support yet, and it is locked to 'all known tags' and 'including parents and siblings', but you can do a basic 'A has more tags than B'

### duplicates boring/cleanup

* pair sorting now happens outside of the database and thus doesn't lag things in edge cases
* pair sorting now works wholly over the entire batch fetched in the duplicate filter (previously, each separate search block was sorted, so in sparse results you'd get a sawtooth sort)
* wrote a 'media result pairs and distances' object to hold the results of a rich potential duplicate pairs fetch. this complements the recent 'id pairs and distances' object from a couple weeks ago. this thing holds all the data needed to sort pairs and handles that all internally
* the 'show some random potential pairs' routine was completely rewritten to use the new tech. it is KISS now, and the old ad-hoc garbage with its multiple layers of king hash filtering and  'comparison_preferred_hash_ids' hackery dackery doo is deleted
* wrote some _fairly fast and good worst time performance_ file-domain pair-filtering code and expanded the pair-ids-and-distances cache to offer different answers for specific location contexts and rewangled the potential duplicate search context panel and the auto-resolution preview panel to re-initialise their base pair cache any time the location context changes
* added unit tests for the new tag-based auto-resolution comparators

### boring/cleanup

* thanks to a user, the way `system:limit` randomly samples with complicated sorts is made more clear in https://hydrusnetwork.github.io/hydrus/getting_started_searching.html
* brushed up the `server.html` help, clearing out some old things and adding a note about the update period from the FAQ
* `options->media viewer hovers` now has a label at the top saying what a hover is lol
* moved some list code from `HydrusData` to `HydrusLists`
* to reduce confusion, the 'verify https traffic' DEBUG checkbox in `options->connection` is inverted to be 'do not verify'

## [Version 631](https://github.com/hydrusnetwork/hydrus/releases/tag/v631)

### custom static assets

* you can now override any of the files in `install_dir/static` by creating a replacement in `db_dir/static`! it works like a lot of vidya modding folders do, where the program consults your user folder before falling back to the install's default whenever it loads an asset. If you want a custom splash image (`static/hydrus_splash.png`), go for it!
* routines like 'what QSS stylesheets are available?' and 'what rating SVGs are available?' and (less significant) the various 'what should our default downloaders be?' check both possible locations to create their lists, preferring (if there are filename conflicts) what it finds in your user dir
* I now explicitly recommend that custom QSS or SVGs go in this directory rather than editing the install dir. it lets you have a completely read-only install and means you don't have to worry about overwrites or clears if you update or git resync or whatever. this puts us one step closer to not having a crazy install environment, hooray
* a new `--no_user_static_dir` launch parameter disables this mode, if you need to do quick debug
* I wrote some simple help for this here: https://hydrusnetwork.github.io/hydrus/custom_assets.html

### misc

* I fixed some issues with the 'hover windows show/hide better' """improvements""" from last week. the child window testing logic was slightly dodgy and hover windows were not showing at all when there were two media viewers open. I simplified it and cleared out the unhelpful behaviour. the mouse hide/show should interact with dialogs a bit better now too
* search pages that start with 'include current/pending tags' turned off will now initialise correctly in this state. previously, the buttons were displaying 'off', as intended, but the internal search object was starting True/True always, so a bare F5 refresh was giving the wrong results and hitting the buttons the first time was not triggering a 'new search state, need to refresh' call since the button was just aligning on that first click with what the internal object already thought
* hydrus has _better_ duration/framerate parsing on videos that ffmpeg cannot report a good duration on. if, say, ffmpeg thinks the video is 40ms long but we just manually counted 400 frames, it now trusts its fps number more than the duration (previously it always trusted the duration)
* added a new shortcut command that does 'close media viewer and focus the tab the media came from, if possible, and focus the media'. same as the related command, but it forces the media focus if you have that not set under `options->media viewer`
* the 'review session cookies' and sub-panel now have 'export to clipboard' and 'import from clipboard' buttons. there's some domain filtering here that ensures cookies only go in the slot they are supposed to
* the 'expires' section in the edit cookie dialog works better--it now boots with the existing value, and the max settable time is 200 years

### duplicates

* the duplicates filter page sidebar now only disables 'launch the filter' and 'show some random potential pairs' if the search is A) complete and B) found nothing. previously, it was disabling until it found at least one pair, which is technically great but annoying in practice
* if you have 'After duplicate filter, ensure deletees are inboxed before delete' on, this now also applies to manual file deletes within the filter

### complicated url-spawning metadata propagation issue

* there are two ways an url file import job can create child jobs--one, by parsing multiple 'posts' with separate metadata using a subsidiary page parser, as in a watcher; the other, by parsing multiple urls within one post with a normal page parser. until now, these routines created their child objects with different, ad-hoc code. most of the 'my downloader that works like this doesn't get the tags/parent url/whatever assocated to this child down the chain' bugs were due to this
* this situation is now remedied. both routines now use the same shared call to create children. referral urls are set up correct; the parent url is added as an associable url; parsed http headers are passed along correctly; source time is passed down; and tags, notes and parsed primary/source urls, which were all working correct before, are still passed down (issue #1763)
* I've done the same for gallery objects creating child gallery or file imports. they had similar but lesser issues
* there are still a couple of issues in the pipeline regarding gallery urls that use multiple tiers of subsidiary page parsers. I am thinking about how to sort it out

### boring stuff

* renamed the 'confirm when closing a non-empty downloader page' in the options to _importer_ page. this applies to all importers, including hard drive import pages (issue #1764)
* the 'regen total pending count' database maintenance job now asks you to choose a repo or ipfs service. previously it was asking you to choose from every service
* if a database is missing critical tables and thus non-functional, it now reports the specific table names
* rejiggered my 'eliding label' sizeHint code to talk to Qt layouts better
* the top hover window now has fixed width and will no longer overflow. at very small sizes, the buttons will shrink and overflowing text will behave better
* the 'delay reason' label on the edit subscription panel now has proper wrap and eliding, so if that guy gets a gigantic error text, it'll now fit better
* forced subscription popups a little wider by default
* added another note from a user about mpv in the Linux install help, this time about MangoHUD. I think we might want a separate page regarding Linux environment tweaks and fixes

## [Version 630](https://github.com/hydrusnetwork/hydrus/releases/tag/v630)

### Linux laggy mpv issue

* I've been chasing down a Linux specific problem recently where mpv would lag out for a second when trying to transition media when it was near to the end of the media. it seemed to be some re-loop buffering issue but I couldn't figure it out. the recent failed 'TEST: stop mpv before transition' was a shot at this
* I figured out that it was caused by the audio normalisation pass triggered by the `af=lavfi=[loudnorm=I=-16:TP=-3:LRA=4]` line in the default mpv.conf. audio stuff like this has caused Linux other problems before. it is now commented out for all new users
* If you are a Linux user, please go to your db dir and check your mpv.conf. edit that line out if it exists.
* I am going to play with `af=dynaudnorm`, which is supposedly far less CPU intensive. feel free to try your own things too and let me know what works, and we'll figure out better defaults!

### misc

* if you have wanted to map shift+tab to a shortcut and it hasn't worked, please try it again! hydrus now recognises 'backtab', which it seems some/many situations produce on a shift+tab input. it'll likely say 'shift+backtab', but whatever--it'll catch _something_ stable now
* fixed some weird logic with the 're-focus original search page' and 'tell original search page to select exit media' options that trigger on media viewer close under `options->media viewer->window`. they now work independently
* when you upload tag data to a tag repository, the prepare routine now checks that the tags are valid (no crazy/broken characters, etc..). if not, it abandons the job and tells you how to fix invalid tags
* fixed some mouse autohide behaviour in the media viewer when various dialogs are open. child windows are detected more reliably and various 'I should unhide now' events fire properly
* added a note to `options->media playback` about the mpv.conf in the db dir--this basically wasn't documented anywhere, previously--adding that this file is reloaded on every options dialog ok
* I confidently attempted to rework the 'add folder' button in the 'import files' window to be an 'add folders' button, allowing directory multi-select, and I was stunned to discover this is simply not doable in a multiplat way using stock path-picker dialogs. I feel like I am going crazy and will revisit this
* wrote a guide and to-do list for migrating from one OS to another under https://hydrusnetwork.github.io/hydrus/database_migration.html#to_new_OS

### default downloaders

* thanks to a user, the pixiv downloader now fetches a 'series' and 'chapter' tag for those paged manga works that have that data set. I wonder if the 'series' here is more akin to what we'd call 'title', but I'm not familiar enough with pixiv to know what is more common, so let me know how it shakes out IRL

### more export filename rules

* if you are on non-Windows but an export directory filesystem is "ntfs", "exfat", "vfat", "msdos", "fat", "fat32", "cifs" (almost always ntfs underlying), "smbfs", "fuseblk" or any of those but prepended with "fuse.", ntfs naming rules (no colons, shorter filename limits etc...) are now applied (was formerly just "ntfs" or "exfat")
* a checkbox under `options->exporting` now allows you to always apply ntfs naming rules. use if you have an NFS share that is NTFS underlying, or you are subdir-translating from an export dir that is non-ntfs to a mountpoint that is
* when an export filename pattern includes subdirectory generation, the subdirs' max length is now determined by the max path characters allowed for this system and the pre-existing prefix directory length, while leaving a reasonable numbers of characters for the actual filename. they'll squeeze down to fit all normal situations (previously windows subdirs were hacked to a 64 char limit)
* filenames and dirnames are now sanitised as they are elided. everything is done through one clean combined call, so there are fewer chances for surprises here
* some eliding and sanitising rules are more failsafe in edge cases. instead of raising an exception, you'll get 'empty' or 'truncated'
* two new optional integer values are added to `options->exporting`, for overriding max path length and clipping max dirname length. check the tooltips for more info, but this is basically to test ntfs-extended modes that have their own limits. _caveat emptor_
* I updated the unit tests here to cover the changes

### duplicates

* the manual duplicate filter's pair fetch routine has been rewritten using the new low-latency fast-cancel tech I developed for auto-resolution. it should be able to fetch pairs to work on a good bit faster in all cases, and the worst case for difficult searches is much better. when it is loading new pairs, you get a running status update on the background of the filter media viewer
* the pairs it loads follow a smarter decision logic, showing you more from the same group while saving you more time
* the pairs are now sorted, hopefully with bigger files first, and the same file over and over. let me know what you think of it! I'll be adding options here, but it is tricky!
* when the duplicate filter commits work, it now does so more asynchronously. if working a mid-filter commit, the UI no longer locks and the background now updates with status text showing progress of the commit; if happening when you close out the filter, it now happens in the background but will make a popup with status if it takes longer than a second to complete. the timing of the 'refresh dupe numbers' call that hits the sidebar is better aligned to refresh once all this work is flushed
* the default duplicate filter batch size is reduced from 250 to 100
* auto-resolution rules that have pending approve/deny items now say their status is 'queued' (previously 'done'). maybe 'ready' or another word is better--let me know if you can think of one. 'awaiting approval' feels too long

### duplicate filter boring/advanced stuff

* the manual duplicate filter's pair fetch database routine no longer does any shaping of the pair queue. it previously tried to auto-filter certain pairs that would be implicated by previous decisions and tried to first give you pairs with certain properties, but the implementation was never too clean and it was often simply confusing on the front end. the UI level now takes full responsibility for this
* the manual duplicate filter is more careful about which pairs it will auto-skip, and in many cases this will let you process an entire group--alternates and all--in one run, rather than that situation where you get lots of bitty '1/2', '1/1' micro-batches at the end of a particular search. now, rather than insisting that every batch commit only include pairs of unique files, it now tracks which files are mergees by the current batch decisions and auto-skips those. so, it might present to you (A, B), and if you say A is a better duplicate than B (causing B to be merged into A), it can still present you with (A, C), but if (B, D) or (E, B) is pending, you still won't see them (since B is no longer a king, and the proper pair, which will be recalculated after the commit, is (A, D) or (A, E). in reality though, (A, D) and (A, E) are probably already in the queue due to transitive similarity, so if we can sort them together, we'll probably clear everything in one batch)
* I played around with different types of pair sort for the manual filter. this gets complicated in a couple of ways and what I thought would be useful often had a clear downside in my test data. for now, duplicate filter pairs will explicitly come by largest max filesize first, with largest min filesize as secondary sort. you'll see a lot more of the same big file matched up against other files, in descending order, and fewer low quality files matched against other low quality. let me know how it goes with IRL data, and I will add explicit options here so we can test more stuff. I tried a 'show me the most/least similar first' approach, but what that actually means beyond sorting by the discovered search distance is unclear--I can try for ~1.0 pair filesize ratio, but this seems to flood me with alternates first, which is not ideal for decision logic. if we want clear duplicates first, maybe we want to have the highest file ratio first? this max filesize first seems like a 'least worst' for now at least
* I am planning a checkbox that will let you focus on entire potential groups one at a time (seeing the same basic files over and over until there are no potentials that 'look like that' any more), which may itself benefit from an exact sort
* there's a third sort question about whether you want the same reliable order of pairs on every launch, continuing where you left off, or if you want to jump about a bit. today's low-latency fetch tech will fetch the same stuff over and over unless the numbers get big and/or refreshed. this question will be more important when I do the grouping, so I think this'll be another checkbox
* I updated the Client API help to talk about kings and `/manage_file_relationships/get_potential_pairs` given the modern tech that has been rolling out this year and this week. all my duplicates stuff now always returns kings, so you don't have to bother about that so much any more, and the filter now presents you with a raw batch that is simpler and cleaner but you may want to institute your own auto-skip tests as I have. it isn't a big deal, and you may already have something similar, but I've figured out, I think, simple and optimal rules, so please check it out yourself
* I wrote a class to handle the 'potential duplicate pairs and their distances' list that is thrown around in all the new dupe fetch code, both up and down the pipeline and in the fragmentary fetch slices. this class now handles the iterating, randomising, block popping, distance sorting, and now potential-group-mapping-and-filtering jobs internally and in one location

### other boring stuff

* now we know the new `11.3.0` version of Pillow adds native AVIF support in all the builds and source situations we work on, `pillow-avif-plugin` is removed from all requirements.txts and the pyproject.toml
* if the network request for an expected html/json file is over 100MB, the error message now says more about what went wrong (probably URL Class crossed-wires)
* fixed a client api test that could sometimes fail due to a thread taking too long to work
* `help->about` now says the system architecture (e.g. x86_64, arm64, aarch64)
* `help->about` has better wordwrap (we noticed it gets super wide if your install dir is long etc..)
