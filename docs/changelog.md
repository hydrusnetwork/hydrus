---
title: Changelog
---

# changelog

!!! note
    This is the new changelog, only the most recent builds. For all versions, see the [old changelog](old_changelog.html).

## [Version 697](https://github.com/hydrusnetwork/hydrus/releases/tag/v697)

### misc

* radically improved repository definition re-processing time. after the PTR definitions reprocess last week, I noticed it wasn't running as fast as I expected. content re-process uses some optimisations to handle the exact same situation, and after looking at it, I saw that definitions was not doing the same thing. I've now implemented this, and in my test situation, re-processing definitions went from 50k/s to 400k/s! I am sorry for those who sat through an hour or more slog with the PTR work--should be much nicer in future
* fixed system predicate parsing for 'system:has url' in regex and url class modes when the incoming regex or url class name includes uppercase letters. for regex, we'll read any `(?P<name>...)` stuff correctly, and url classes should match regardless of capitalisation (I think url classes actually did work before, but they didn't remember their capitalisation through the parse, so that's more of a display fix). this fixes such predicates sent through the Client API. also added some unit tests for this (issue #2122)
* fixed a harmless but not great error popup when you launch the media viewer with a file focused in a particular position (a bunch of categories like 'the first file in the thumbgrid when the n first files in the thumbgrid are selected', I think), delete that file in the media viewer such that it is removed from the original thumbgridview, and then close the media viewer and make a navigation step that relies on the 'previous focus' media. the 'slide this to a new valid position' logic for the 'previous focus' guy was simply bad and not clearing correctly in all cases. fixed now, and there's a guard to nullify similar errors in future (issue #2118)
* added a link in the Client API help to `https://github.com/micnorian14/wd-e621-hydrus-tagger`, which is a new and currently maintained fork of this AI tagging project for hydrus. if you use the old branch of this tech, check out this repo and review the updates
* same guy has forked and optimised the Hydrus Video Deduplicator, so this is added to the Client API help too: `https://github.com/micnorian14/hydrus-video-deduplicator`. it might get pulled back into the original project, and another user is working hard merging more improvements, so if you use this tool, watch this space

### sessions and session cookies

* building on the recent session cookie clearing timer, network sessions are now only 'touched' to reset the cookie expiry when we actually do network work on them or change cookies. previously, any object lookup, including to consult for the 'review cookies' UI or stuff like login checks, was doing a touch, leading to this stuff to take longer to time out the more you checked to see if it had timed out yet
* the 'review session' UI now says when a session was last used/modified
* fixed editing cookies in the 'review cookies' panel when you edit the domain, path, or name (it was not deleting the old cookie correctly)
* I renamed 'review session cookies' and similar to 'review cookies'. the word 'session' refers to both the umbrella that holds all the gubbins for a network connection and it is a specific type of ephemeral cookie. it is valid to say a session's session cookies, but that's not helpful, so I'll try and phase out the former term when it is ambiguous

### executable manager

* the 'send single file' and 'get metadata for a single file' executable types now support md5, sha1, and sha512 hashes as input parameters. if a file is missing this data on a call but is nonetheless local, the error handling schedules an 'other hash' regen and the message to the user says 'try again in a bit'
* the executable manager now only sends the required input parameters to a call. previously it would provide all possible params, but it is now more judicious. this saves a file system hit for a path check on file calls that only need the hash, and it allows calls on non-local files when only, say, a hash is needed
* missing file paths or file URIs on non-local files have some nicer handling, although I think you'd have to pull a rabbit out of your hat to trigger one of these
* fixed the 'file_id' parameter for 'send single file' commands IRL, outside of the options window test environment
* fixed an issue where edited local process calls that were not expecting a response were nonetheless defaulting to saving (and then doing nothing with) stdout to a temp file

### dupe search

* the pair search optimisation that says 'do the rest of the search in one step', often seen in UI as something like '4,000/1,234,567' for a while before the result comes back, now considers how big the '1,234,567' side is. while the old optimisation is still faster than a block-based search, it seems to take about 1 second for each 100k pairs to set up. if the remaining search is larger than 200K and 10% of your total pair count, I now just use the master potential pair table and filter to the in-memory pair set. this will still take a couple seconds, and it may have bad performance in certain situations, but let's see how it goes IRL

### boring stuff

* cleaned up some lazy job status logging for stuff like db table analyze work summaries
* cleaned up some of the 'upload pending' job to be cleaner and report nicer
* cleaned up some of the executable manager code with tighter type hinting
* cleaned up some duplicated code in 'review cookies'
* updated mkdocs-material to from `9.7.7` to `9.8.2` for standard security patches
* removed the old macOS app build files from static dir and the 'running from app' checks during program init

## [Version 696](https://github.com/hydrusnetwork/hydrus/releases/tag/v696)

### PTR definition problem

* several users reported their PTR processing suddenly encountered a critical definition error! if you got it too, or get it, please do not panic. the server burped because of a rare race condition and delivered insufficient data last saturday. I am figuring out a serverside fix with the hope that in a few days a client will be able to step over the gap and never notice there was an issue. please bear with me and expect to unpause any halted repo sync in a few days
* the actual problem is there was a very rare race condition in how updates are generated. it required a user to upload tags at the same time as updates for the last update period were being generated at the same time as a very slow maintenance job was running, and then it needed an unlucky dice roll. this has not happened in the 15-odd years the PTR has been running, and the respective code here is so old there isn't even a git record. I have now fixed the issue so it will not happen again
* we still have the problem on the PTR that did happen. the update built on 2026-11-14 was missing one or more ids. I am doing an investigation now to figure out exactly which ids we are talking about so we can roll out a manual fix to the database. hold on for a bit please, and in a couple days I hope to say 'ok unpause now' and it'll all just work again no worries

### misc

* you can now import/export/duplicate import folders. a little label on the panel says be careful doing this for a couple reasons (privacy leak when sharing and some service migration pains)
* you can now import/export/duplicate export folders. there's a new warning label here too
* fixed a regression in v695 where the video seekbar text disappeared
* fixed a regression introduced in v695 mainloop refactor when downloading more than one file at once from a hydrus file repository
* loading up the pending count of file maintenance jobs is now twice as fast in CPU terms (I/O on initial fetch can still be a little slow)

### user submissions on image resizing and close pages api

* thanks to a user, we have fixes for several (stupid) image resizing typo-bugs I had made that mostly meant optimisations were not kicking in or the incorrect interpolation algorithm was being selected when interpolating (scaling up) images in many non-media-viewer contexts like 'get me a bigger version of this thumb right away'
* also added is a query param to the render API endpoint to allow setting the resizing interpolation algorithm
* also adds safety clamp to the render quality param when using animated WebP so Pillow doesn't error
* Changes the wording for ZOOM_CUBIC to "bicubic interpolation" rather than "4x4 bilinear interpolation" which is incorrect.
* the Client API gets a new `/manage_pages/close_page` call! it takes a page_key and closes the page immediately, skipping user-interaction for any potential 'are you sure?' stuff
* Client API version is now 97

### network stuff

* hydrus now clears "session" cookies (i.e. those with no fixed expiry) after thirty-six hours of domain inactivity. for a long long time, hydrus has not aggressively cleared session cookies, since it is useful sometimes to hang on to them, but it has been causing issues on some sites with them piling up, so I'm instituting a pragmatic and KISS answer. if you'd like something different than thirty-six hours, check the new setting under `options->connection`. I may revisit this with a more aggressive system, or per-cookie timeouts, and likely an option to purge on every client restart, so let me know how you get on
* with thanks to several users' contributions, we have some curl_cffi improvements--
* a number of connection timeout (error 28) errors are now caught correctly and converted to something hydrus understands
* two new checkboxes under `options->connection` now handle whether jobs under curl_cffi should strip the User-Agent header set by hydrus--you can select to do it generally, or only when the hydrus-side header comes from the default global context. default settings here are to strip in all situations, preserving old behaviour. I expect to migrate this, like curl_cffi in general, to a simpler per-domain yes/no in future

### duplicate pair search CPU optimisations

* duplicate pair search caches now remember their sort status, whether sorted for fast search or rich estimates, and do not repeat sorts. they pass on their sort state to child caches they spawn
* duplicate pair search caches now defer deletes in many cases, saving much CPU time when we run into millions of rows
* duplicate pair search caches are better about cleaning up their internal mapping indices during a particular sort of destructive pop-iteration

### boring stuff

* I removed a couple old requirements.txts from the build folders. we use the pyproject.toml now, and these old files were not being updated and just giving dependabot warnings
* added dynamic typedefs to the multi-column list model and panel code, so they know what they are supposed to hold
* went through all 60-odd lists in the program and added typing decorators to their init and row presentation/sort code so they better know what's flying around. good news is there were no problems, but now we know
* also cleared out some stub methods that weren't doing anything and allowed my custom serialisable list/dict objects to figure out their types better too. lots of inferred type hinting now just werks
* misc linting and type hinting

## [Version 695](https://github.com/hydrusnetwork/hydrus/releases/tag/v695)

### seekbar

* to relieve the 'oh my click did something else because I didn't notice the tiny gap below the seekbar in fullscreen mode' issue, if the current media has a seekbar and it is wide but not quite tall enough for the window--think a vid like 1920x1078 in fullscreen--hydrus now drops that media the couple pixels down so the seekbar is flush with the bottom edge whenever 'centering' that media. you can change the pixel gap threshold for this (default 20) or turn it off entirely, under `options->media playback`
* this 'move down' mode should work well in UI scales larger than 100%, but you will still sometimes get videos with a little gap at the bottom when the height of the media matches the height of the window; there are no easy and excellent technical solutions for this right now, but if you want me to add an option to always drop it a virtual pixel and thus always leave a little gap at the _top_, I can do it
* fixed an issue where in fullscreen borderless in some UI scales, the seekbar does not pop up to full size if the mouse is at the bottom of the screen
* UI scales greater than 100% should draw the border around the scanbar a little better. not perfect yet

### more memory-efficient duplicate work

* a user did some great memory and CPU profiling on larger potential duplicate pair filtering and found bloat due to massed primitive object duplication. I have worked on this and potential duplicate filtering should now use at least 67% less memory, and in complicated situations 90%+
* specifically, the core search atom of this system is now completely deduplicated in all cases, so any new search is pointing to the same memory store, and only containers need be recreated
* further, I reworked a rich index used to search these guys at the object level to now use these new objects, compressing used data a bit more, particularly in search spaces of millions of rows
* when you do hit large search spaces, I _think_ this compressed tech will also save a bunch of CPU when updating and re-initialising searches. let me know how it goes
* also fixed a bug in 'group mode' potential duplicate pair search that wasted a little CPU and in very very rare cases might deliver a pair with a file outside the group
* also, the 'clear search context' signal, which happens when a user purges all potential dupes from the db, is better about clearing out data here

### exe manager

* the new and still-under-testing 'get metadata for a single file' job type under `options->external programs` now shows a 'result parsing' box with the same basic UI as in 'manage parsers'. write up a json or html parser for whatever you are getting back on stdout or stderr, and the newly updated test panel will show your raw and parsed output!
* next step here is to migrate the legacy 'file lookup scripts' tag suggestions box to be a 'go ask external thing for tag suggestions' guy, and then you'll be able to pipe whatever ai model or script you can think of that eats a file reference and generates tags right into 'manage tags'

### misc

* fixed some crazy, probably truncated animated gifs that were raising errors when Pillow tried to iterate through their num_frames

### patreon

* nothing bad is happening, but my personal situation is changing a little and I will be closing my Patreon page later this month. the links and pages in the help are removed today to prep for this
* I expect to keep working on hydrus just like normal, with regular schedule
* thank you to everyone who supported over the years. I really appreciate it!

### environment stuff

* for advanced source users, the setup_venv.py now tentatively supports python 3.15, with the proviso that you need to select advanced/test on everything and you will not get lz4 (some memory savings) or jxl (the filetype) support yet
* removed the 'openssl' version line from `help->about`. this wraps the system version, not anything the python venv actually controls, and isn't particularly helpful. the old-date-despite-being-updated is sometimes confusing/worrying for users, too. EDIT: ironically, we ended up looking at openssl versions despite it being non-python this week when we went through some dll fun. I'll bring this back, and other versions we can see, in a new about tab

### boring stuff

* fixed a double-layout-set on the main gui that was raising a warning in PyQt6
* a routine that streams blocks of data from external executable calls (for ffmpeg video rendering and silent audio checks) now does a CPU-efficient sleep (this continues some CPU-thrashing code cleanup work I started a few months ago)
* the fast event processor 'job schedulers' are optimised a little and have less per-loop overhead
* when thread slots are saturated (this happens in the downloader system when there are lots of downloaders waiting to work) downloader jobs now back off on reattempts, slowly moving from 10 second to 180 second waits
* I wrenched the parser edit ui's edit and test panels apart--very ugly decoupling, and there is more to do--so I could embed the edit UI in the executable callable panel
* the edit parser panel now has a nicer Qt update signal on any changes
* a bunch of list handling tools (mass unions, iterator reshapers, some auto-throttling chunkers) have nice type hints, so all callers know the shape of what they are getting back based on what they are giving
* bit of misc linting

### boring mainloop refactoring

* I did a KISS and merge pass on my manager daemons, such as the things that run file maintenance, sibling/parent calc, and subscriptions. a bunch of timing/waiting code is more solid, but I may need to revisit this to check on some edge cases, particularly around a remaining ugly knot of when new jobs come in while a daemon is cleaning up what it thinks is the final job. I'll keep pushing on this
* the parent class of mainloops now handles the pausing between loops; every subclass now receives desired work period and returns 'still work to do' status, and the parent makes waiting decisions based on this, in a unified way
* forced wait times are also now handled by the parent class
* the separate idle/work waits are merged and wakes are handled instead by current work state logic
* the top mainloop now handles most 'check if shutting down' calls
* all nine mainloop managers now do CPU-efficient sleeps when not working, which should reduce some thrashing in busy clients

## [Version 694](https://github.com/hydrusnetwork/hydrus/releases/tag/v694)

### misc

* added 'confirm add-undelete tags' to the cog icon on 'manage tags'. if you have been annoyed at the 'confirm your action' popups in the new manage tags dialog when you type in a tag that was previously deleted, please uncheck this and let me know how it feels
* added 'allowed actions for taglist double-click:' to this menu too. if you don't ever want to see a 'clear deletion record' option, or whatever, you can now turn things on and off here too
* fixed the 'clear trash' routine to delete more than one old file per run. this was the lagging logic patched last week, now improved back to what it was originally intended to do
* also made the clear 'trash routine' wait on 'a file was recently deleted' safety delay more intelligently (it doesn't work if a file was deleted in the past sixty seconds, as a grace period for undeletes of accidental giant deletes), and, lmao, it no longer sends this signal itself when it works (blocking itself a bunch when there's a lot of work to do)
* when you drag-and-drop URLs on the client, and the application source bundles non-URL data in the 'urls' metadata slot (we have evidence of one less-used browser putting the browser tab text in with the url), the hydrus drag-and-drop catcher now filters the urls from the non-urls nicely. if any urls were in there, it silently prints info to the log; if nothing was an url, it puts it in a popup for you to see
* fixed some login cookie handling when using the `curl_cffi` test. there is more work to do with the curl_cffi test, so please bear with me
* I fixed some issues with the 'children' tab of tag autocomplete, which looks up children of tag parents in the associated taglist, when the file domain is set to multiple file domains or 'all known files'

### exe manager

* the new Windows 'hide terminal' tech test is now default ON for all users. the test appeared to go fine, so I am making it real. you shouldn't notice any difference, but if you are a Windows user and you suddenly get command line popups every time you import a file or do 'open externally', hit up `options->external programs` to switch it off, and let me know!

### v693a hotfix

* I did a hotfix on Saturday to address some update stuff--
* in the 'future build' integration, the pyproject.toml accidentally did not get the intended `pyopenssl`, `numpy`, or `pyside6` updates, meaning the builds missed out. it was just a copy/paste transcription failure by me. this is fixed and I'll make a script to do this automatically in future
* fixed a bitrot issue with the v687-to-v688 update code
* fixed a typo in deserialisation when updating older metadata routers from v2 to v3 (would hit old import/export folders with sidecars that hadn't been edited in about 18 months)
* as a side thing here, I now have a nicer test in my weekly build workflow that tests my older db updates better. I'm going to keep an older db and test current code to catch bitrot issues like the above. unfortunately, my best rich test db is currently v693, so I'm going to pin it at that version and let it get older every week until it is 50 weeks old and we have full coverage of all the updates I try to support. so, going forward I guarantee I will test anything after v693 every week
* I've made a plan for a serialisable update manager too and will be working on that in the future. we'll fix these legacy objects sitting around on the db for years without a resave

### security

* I continued the recent security work. my deserialisation pipeline now has a single clean deserialisation context to hold the various trust information. it is easier to pass this through each stage, and this thing will be easier to extend in future
* in doing this, I was able to remove a hack that was suppressing some trusted whitelist warning logging, so whitelist warning logging is now true positive in a couple of places it was false negative before. I already fixed a couple small instances of this, although tbh I was surprised that we had so little report of legacy cruft in the local store; it was mostly just a couple of legacy 'current file service is this' on older page objects
* also generically cleaned some deserialisation unit tests and special deserialisation situations
* there's more I want to do here, including what I hope will be a big deserialisation typedef solution, so I'll keep pushing

### boring stuff

* added `help->debug->threads and processes->wake mainloops` for various debug testing
* cleared out the 12 or so 'calling non-callable' linting issues with nicer typedefs and some stub callable juggling
* cleaned up all Callable type definitions across the program and updated some old deprecated typing stuff
* fixed some error handling for malformed objects in page session load--it was not recovering properly and raising a new error
* added unit tests for the new cookie serialisation and deserialisation for requests
* added unit tests for the new cookie serialisation and deserialisation for curl_cffi
* fixed an issue with the 'networking' unit test suite when it was run on its own; `tldextract` was not initialised properly in this case, and when it tried to load its suffix list from disk to init its cache inside the first test, the mock http wrapper gonked the load

## [Version 693](https://github.com/hydrusnetwork/hydrus/releases/tag/v693)

### security

* if you missed it, AI discovered an important security flaw in hydrus last week. if you are running v691 or earlier you should update to v692 or later, such as today's release. check here for more details: https://github.com/hydrusnetwork/hydrus/releases/tag/v692
* I am now starting a project of improving the rigour of hydrus I/O security to shrink the attack surface and reduce the potential severity of future discoveries like this. today's release brings a top-to-bottom overhaul of deserialisation security with a whitelist applied to all untrusted ingresses
* when the hydrus server takes a POST request, it now applies a whitelist of which serialisable objects it is willing to load, based on the request type. if there is extra stuff, it does 400 Bad Request
* conversely, when a client receives responses from the hydrus server, it now equally whitelists the serialised response and throws an error if anything doesn't match the whitelist
* in the client UI, when you paste a bitmap or drop a png onto a list that knows how to import/export, it now applies a similar whitelist before loading; if it is expecting URL Classes, it will recognise anything that _isn't_ an URL class before it tries to load anything and cancel out
* if an object load _is_ from a trusted source (e.g. you are loading your options object from the database), the whitelist does not apply strictly but the log will write about anything that violates it. we'll see how much cruft we have hanging around from old forgotten things. if you get some messages like `An object of type 26 ("Serialisable List") loaded when the expected serialisable types are: {127}! You can probably ignore this, but if there are a bunch of these, hydev would like to know.`, please pass them on
* the hydrus serialisation system will no longer deserialise an object that comes from a future version of the client, under any circumstances. we had a hacky path here previously to permit some 'run the client on old software and see if it muddles through the errors' situations, but I would rather be KISS on this question going forward

### misc

* fixed an issue introduced in v689 that was causing increments of 0.5s of wasted CPU work when the trash was cleared for old files. some users have reported unusual freezes that come and go; please let me know how things feel now. thanks to the reporting user who found this with AI
* hydrus services now take longer breaks (about four hours) when there are connection problems, and similarly when there is any generic problem. previously, a couple of request paths would not generate a delay and they'd try again ~fifteen minutes later. I've also made hydrus requests cancel earlier in all situations--a couple of slow maintenance paths would run the normal cancel/retry system, but this stuff is mostly hidden from UI and it wasn't helping to have quick retry
* removed some ancient two year old server update code that would no longer be fired anyway because of the bitrot guard
* improved shutdown code to more promptly cancel ongoing network jobs. if a manager (e.g. 'synchronise repositories' manager) is waiting on a network job to clear but there's a connection retry etc... holding things up, this is now insta-cancelled and shutdown no longer waits
* the url class parameter edit panel now makes the default-value string processor available when the 'ephemeral token' checkbox is not set on. there is also a textbox to show the output of the string processing on the current example text

### boring security worklist

* added an object type whitelist to all deserialisation code and a trusted/untrusted environment bool; if untrusted (e.g. pasting from clipboard, receiving from a server, POST request to server), the whitelist is adhered to strictly and exceptions raised on violations; if trusted (e.g. loading from local database store), we load whatever comes and accept-but-log legacy cruft that exceeds the whitelist
* converted default object loading to use the whitelist in all cases (just a couple calls)
* converted 'noneable' object loading to use the whitelist in all cases (just three calls)
* converted 'networkbytes' object loading to use the whitelist in all cases (15 calls)
* converted 'fromstring' object loading to use the whitelist in all cases (48 calls)
* converted the core 'serialisabletuple' object loading to use the whitelist in all cases (~295 calls aieeeee)
* propagated the trusted/untrusted environment to the serialisable update routines too
* updated serverside POST request processing to obey whitelists particular to each command
* updated client 'Service' request response parsing to obey a similar per-command whitelist
* the 'what is this?' debug panel now separates the payload ingestion from actual deserialisation, showing a preview of the json content before you parse it. there are also two buttons, for trusted and untrusted parse
* added unit tests for the new deserialisation whitelisting
* added a unit test for the new future-object deserialisation error
* added unit tests for the serverside whitelisting
* misc cleanup all around here

### more boring cleanup

* removed the legacy subscription object and migration code and import support in the subs dialog. the transition was years ago, so we can drop it
* similarly removed the legacy bandwidth manager object and migration code
* amongst the type filtering work this week, discovered that legacy url classes could (harmlessly) insert the incorrect sort of string conversion tool in their parameter definitions, and fixed it
* Lain now skips erroneous import object reports more efficiently. previously she would give an error window for each unexpected object; now only simple page parsing formulae are even parsed and she'll just give one error and silently skip over them after that
* the checkbox list that Lain provides, and the same list used across the program, now makes a better expandable layout when it has more than 20 items in it. previously it janked out and wouldn't grow vertically properly
* extended some lists that accept import/export of hydrus serialisable objects to forgive objects in the same class and give a nicer error. 'import url class' list will eat gugs, ngugs, and such, and say 'hey, not them m8' rather than going nuts. you can drop a bunch of mixed downloader objects on one of these sub-dialogs and it'll pull what it can
* fixed some thumbnail error handling and 'file report mode' reporting, which missed something in the transition from hashes to media_results

### future build

* This release commits the changes tested with the recent future test build that I did after making v691 last week, which went well
* the summary for this update is: most python libraries are brought up to latest, and ffmpeg, and the builder, pyinstaller, too
* there are no special instructions for the update. update as normal
* since library versions have been bumped, users who run from source will be encouraged to rebuild their venv on update this week. this is particularly important in the current rapid-update climate
* The changes are--
* python updates--
* `PySide6` moved from `6.10.3` to `6.11.2`
* `opencv-python-headless` moved from `4.13.0.92` to `4.14.0.94`
* `pillow-heif` moved from `1.4.0` to `1.8.1`
* `cbor` moved from `6.1.3` to `6.1.5`
* `chardet` moved from `7.4.3` to `7.7.0`
* `cryptography` moved from `49.0.0` to `50.0.2`
* `lxml` from `6.1.1` to `6.1.3`
* `numpy` moved from `2.4.6` to `2.5.4`
* `pyopenssl` moved from `26.3.0` to `26.4.0`
* new library--
* `curl_cffi` is now included by default, to help testing in built environments, at `0.16.3`
* build--
* `pyinstaller` moved from `6.18` to `6.22.3`
* test versions--
* `PySide6` moved from `6.11.1` to `6.12.0`
* misc--
* ffmpeg updated from `8.1.2` to `9.0.2` on Windows
* ffmpeg updated from `2026-06-30` to `2026-10-21` on Linux
* updated the tldextract domain list from `2026-07-15` to `2026-10-20`
* updated github actions in workflow scripts to latest stable versions

## [Version 692](https://github.com/hydrusnetwork/hydrus/releases/tag/v692)

### security hotfix

* An AI scanner has found a remote code execution bug in the hydrus client. This release fixes the issue. All users should update
* the risk occurred when importing a user-made object like a downloader or when talking to a hydrus server like the PTR
* _EDIT: I originally thought the Client API was vulnerable, but additional testing has shown it was not._
* The hydrus server was not vulnerable
* After investigating the 5,000+ publicly shared downloaders on the user-run repo and 27,000+ PTR update files, I did not find any use of the exploit and am confident that there was no widespread use of the flaw. This is the time to update, in case the problem becomes real in the near future.
* to help propagate the notice and make a hard split with unpatched clients, the hydrus network version has been bumped (to 21). Any client that tries to communicate with an updated server (which includes the PTR, which has just been updated) will get a message that they need to update.
* The Client API also has a version bump, up to 96

## [Version 691](https://github.com/hydrusnetwork/hydrus/releases/tag/v691)

### exe manager

* the 'this can live for a very long time' checkbox is renamed and now detaches the process better on Windows and POSIX. the long-time child process should no longer pipe stdout/stderr to our terminal
* the `text` checkbox is removed from 'local process call' edit panels; this will now be inferred from any parsable result settings, and with a specific encoding
* the `hide terminal` checkbox is removed from 'local process call' edit panels. this was only affecting Windows and has few debug uses, so the behaviour is now always on
* if you are a Windows user, the 'external programs' options panel has a new 'TEST' checkbox to try out some cleaner 'hide terminal' tech. if you are an advanced user, please check out its tooltip and let me know how you get on
* in the first step of getting arbitrary 'tag suggestions' working, you can now set an executable call type of 'get metadata for a single file' type. this exposes a new setting at the bottom of the 'local process call' panel where you can specify whether the metadata arrives on `stdout` or `stderr`, and in which encoding, if not `utf-8`. there's no parsing yet (it'll use the same UI as the downloader system), so it will always say it parsed nothing, but the test panel is hooked up and we are now reading basic responses from external tag calls. if you are interested in this stuff, feel free to wire up a test situation

### session log-off detection

* I wrote a nicer hook for the signal that your OS sends to programs when the user is about to log off. hydrus has never been great about catching these events and sometimes has a non-clean exit when the computer shuts down. I am not 100% confident in my implementation yet, so it is hidden behind a new `TEST: Try new log-off detection for clean exit` under `options>gui`.
* added `help->debug->tests->do session sign-off (fake)` to simulate this event firing
* if the test is on and it happens, your log will especially state "doing fast session shutdown" when it triggers. the program hides and saves without showing the splash
* I'm worried about whether some users session managers fire the event at a time other than logoff, e.g. every fifteen minutes for some extraneous checkpointing that is misfiring, so if you are interested in cleaner program exit on log-off, please switch this test on and let me know how it goes. does it save nicely when you log off, and does the program ever now close randomly?

### misc

* fixed an issue where the QtMediaPlayer would render flag-rotated videos in a too-small area
* the command palette no longer gives 'label' results (menu items with text but no function) when searching the main menu or media menu
* I juggled some of `help->debug` around, including adding a 'threads and subprocesses' submenu
* added a 'review subprocesses' window to this new submenu. it shows the current subprocess snapshot with basic launch command, pid, and running/return code, and buttons to do reaping maintenance, and terminate (+kill on POSIX). as we do more executable manager stuff, we're running into needing a better window on this stuff, so this is a first draft. I think we'll want some more stuff like start time and timeout

### boring stuff

* I did a bunch of boring cleanup and infrastructure expansion in the exe manager to prep for fetching tags. there's new enums, a nicer response object to handle responses, and the test panel is ready to talk about file/metadata responses
* local process calls now have 'parsable' and 'importable' sourcing data so they can pull a metadata document (with an encoding) or (in future) a raw importable file from a pipe or (in future) a temp_path input parameter
* executable definitions now have a page parser to parse metadata documents in prep for tag suggestions, but there's no UI for it yet
* moved `Switch to main window when creating new file search page from media viewer` from `options->gui` to `options->media viewer`
* brought `Pillow` from `12.3.0` to `13.0.0` for a security update

## [Version 690](https://github.com/hydrusnetwork/hydrus/releases/tag/v690)

### more treeview improvements

* the user who has been working on the treeview experiment (under `options->gui pages` if you want to try it out!) has sent in more improvements (#2101)--
* shift-double-click on a page entry in the treeview now does a page rename
* the treeview page entries can now catch file drag and drops!
* the cog icon has a new 'style/display' submenu with the alternate-row-colour setting and a new hide/show focus rectangle option
* some bottom-label/page-name desync issues are fixed
* fix when a page is first activated inside a notebook after selection moves from a different parent notebook, the parent notebook node would be highlighted instead of the activated page
* fix the 'expand all' isnt enabled when i have a pages of pages inside another, and collapse the inner one (and the inverse situation)
* fix some other small selection/activation bugs, clean up and consolidate some redundant code

### no more shutdown maintenance

* I have completely removed the 'do maintenance on shutdown' system. this system was old, creaky, inefficient, occasionally confusing, and had to jump through several unusual hoops to still work. it used to do a bunch of stuff, but I had whittled it down, over years, to just database analysis and repo processing work. removing it completely satisfies a long-term KISS plan
* going forward, I will continue to push on maintenance work working in small increments in convenient invisible ways. ideally, most users should never care or have to bother with maintenance. I may add a 'yeah go nuts do work now' button for a convenient 'just do idle work now' mode in future, but for now, the plumbing behind shutdown is a bit simpler and a shutdown should now always be as prompt as possible
* the related settings under `options->maintenance and processing` are removed, and the shortcut that did 'shutdown and force maintenance' now just does a normal shutdown

### manage tags

* _the manage tags dialog has more options on what happens when you enter tags. delete confirmations only take one 'yes' click, but it also interrupts you more when you are about to do something with no easy undo_
* the 'confirm remove/petition tags on explicit delete actions' cog icon setting, which used to only apply on hitting the delete key on the taglist or the 'remove tags' button is now 'confirm remove/petition tags' and applies to all potential removes. instead of making a second yes/no dialog, it forces the action choice dialog to show even if there is only one available action (the delete/petition)
* the action confirmation now appears even if there is only one action to do if that action is an undelete, clear deletion record, rescind pend, or rescind petitioned call
* by default, the autocomplete paste button now only does add/pend actions (so if you paste tags that are already in the list, it will not offer to delete them or rescind pends or whatever), but you can allow it to do delete/petition, resind pend/petition, and clear deletion record if you like under a new cog icon submenu
* by default, autocomplete tag entry can trigger any action except clear deletion record (add, delete, pend, petition, rescind pend, rescind petition), but you can configure it under a similar submenu
* double-clicking the list to 'activate' it can now trigger any action (add, delete. clear deletion record, pend, petition, rescind pend, rescind petition). adding a tag from the tag suggestion boxes is the same (sans 'clear deletion record'), but since those lists filter themselves by tags already in the list, It'd be tricky to pull off one of the 'removes'
* hitting the delete key on a list selection or hitting 'remove tags' button can now trigger delete, petition, rescind pend, or clear delete record outcomes
* this retires the old 'allow remove/petition result on tag input for already existing tag', which was always a muddy fudge that I could never remember the precise meaning of
* when you enter tags, there are more dialog labels to cover different situations. previously it would erroneously say 'of the 1 files being managed, some have that tag, but not all of them do' when showing the new add/clear deleted record choice, but now it handles stuff like that properly. further, it mentions if an 'add' action involves an undelete

### related tags

* _related tags works better in some clever ways; you don't have to do anything_
* you can now customise whether 'related tags' starts with "just for my files" and "siblings and parents" on/off when the manage tags dialog boots. there's a cog icon on the related tags panel, and complementary checkboxes added to `options->tag suggestions->related tags`
* the related tags search system does some smarter sibling lookups when it weights search and result tags, now weighting by the _ideal_ tag even when you search not in the sibling/parent space. if you don't want to receive any 'series' tags in your results, it will now stop giving you unnamespaced suggestions that sibling to a series tag. same deal for its searching tech
* I have made significant improvements in how the 'related tags' list is filtered of tags that already exist in the list, so that it should be better about not suggesting a storage tag when a tag already in the list shares the same ideal tag or already includes the suggested via a parent implication. there are still a couple small holes here, but the improvement was enough that I have removed all the ugly and annoying filtering at the db level, saving some lookup time and making it so if you repeal an already-pending (tag repos) or already-current (local tags) tag, the 'related tags' list is probably going to spontaneously list it, since it already found that guy, knows it is important, and was actually hiding it already. it just makes for a more reactive list that you don't need to refresh so much if you remove something by mistake

### import options

* the 'import options' button-with-menu-arrow widget you see on every importer now allows you to edit the default import options (essentially just opening the `options->import options` panel on its own) from the menu. you can also open it from the edit panel itself with a new 'edit defaults' button. if you change the defaults, the panel should update on ok to show any new actual options inheritance
* fixed the 'favourites' list in import options panel not sorting on init
* fixed an error when trying to delete one favourite

### couple of mpv things

* updated the default_mpv.conf with formatting, some opening explanation blurb, and consolidated the info in the experimental confs into it as examples for the advanced user to check out. updated the label in the options help too; ask a chatbot works well for navigating the excellent-but-monstrous docs here: https://mpv.io/manual/master/
* mpv `[error]`s of `Your platform doesn't support hardware accelerated X` are now ignored; previously they'd spam to log but the file would render fine

### boring cleanup and little fixes

* fixed `database->db maintenance->get tables using definitions`, which was failing due to a missing subclass method definition in one of the duplicate-file db modules
* added a safety catch for file import or gallery download jobs so they always always get a status set, even if an error handler is supposed to but then fails; if nothing is set by an error handler, the job is set as error. we had one instance of this recently that had a looping file import job that was failing to set some sort of skip/ignore/error status because a backing daemon had shut down early
* split the existing 'shutdown' exceptions into 'daemon' vs 'program' shutdown, so catchers can better handle the two situations
* moved the client thumbnail cache to its own file, `ClientCacheThumbnails`, and wrote some new thumbnail sizing intention infrastructure
* moved all the hydrus core thumbnail code to its own file `HydrusImageThumbnails`
* moved the filetype determination code out to its own file `HydrusFileTypeDetermination`

## [Version 689](https://github.com/hydrusnetwork/hydrus/releases/tag/v689)

### all misc this week

* with the tests complete, everyone is moved to the new 'GraphicsView' thumbnail rendering system. the old thumbnail grid rendering code and related thumb cache and other objects are deleted
* for local file services, you can now delete a deleted tag record in manage tags. if you are looking at a deleted tags (i.e. one with an X count, like `skirt (X1)`), then actioning it (double-click etc..) now gives you the option to either undelete it or clear its deletion record. the 'remove? yes/no' dialog that you may have set to appear when you hit the delete key will now say whether you are about to remove or purge your selection
* the daemon that deletes overflowing/old files from the trash (when you give the trash a max size or age under `options->files and trash`) is migrated from the old daemon type to the newer. it uses fewer database queries to work, has smarter and lower-latency work/sleep timings that cap out after a half-second of dynamically flexible work, no longer fights with the user if they happen to undelete the oldest trashed files while it is working, avoids work for the sixty seconds after you delete a file from anywhere, and deletes up to the satisfaction of the rules and no further (previously, it would work in batches and cut the trash down to way under the size/age the rules asked for)
* a 'is this file in use by another process?' test on to-be-imported files no longer attempts the 'rename file to itself' method in non-Windows. this test was false-positive failing on some POSIX systems with advanced permission setups and had no true-positive outcome
* the 'is this file in use by another process?' test now checks in with `flock` in non-Windows systems. it'll try to open a read on the file and grab an exclusive lock; if either fail, it says no. if this flock test causes permission issues in your storage setup, it _should_ still work while spitting info to log; you can turn it off completely with a new checkbox in `options->files and trash`
* fixed disappearing system tray icons on 'hide to system tray' on OSes with a Window Manager that needs a full QWidget for the system tray icon. thanks to the reporting user for figuring this out! (issue #2091)
* fixed the 'move left/right one tab/service page' and 'move to previous/next media' shortcut actions not being listed as choosable action types in the autocomplete shortcut set! (issue #2087)

## [Version 688](https://github.com/hydrusnetwork/hydrus/releases/tag/v688)

### run external program on import

* when importing files, there is a new 'external programs import options'. it allows you to run a 'send single file' call every time a file imports with a result of 'successful (and new)', 'successful (already in db)', or both. if you are building a secondary database of your hydrus files, let's say some special duplicate or search data, you can now auto-populate this guy with your new imports
* when the import options panels are in simple mode, this new options type appears in global, local hard drive import, import folders, and specific import options. I expect most people who use this will want it for either a specific import folder or for everything

### exe manager misc

* I added a first draft of an 'executable manager' help page to https://hydrusnetwork.github.io/hydrus/external_programs.html . the options page now links to this
* the 'open externally (single file)' and 'open URL (single URL)' executable types are renamed to 'send single file' and 'send single URL'
* the 'default programs' options page is renamed back to 'open externally'
* if you import an local process call with any of: exe path longer than 256 characters; more than 16 parameters; or more than 1024 characters of parameters, then the import routine tells you about the weirdness, showing what is weird, and asks if you are yes/no ok to add it

### import options

* the `options->import options` panel now shows your favourites/presets in a new list. this is the stuff normally tucked into the 'star' button, just exposed better. it is all synced with the star button, so changes show up immediately
* the box-panels holding the three lists are now also collapsible, if you need more space
* added some simple texts to the boxes and tweaked some labels here. 'favourites' are now generally called 'favourites/presets'
* fixed the default/url class 'paste custom' menu option to actually boot the customise panel, rather than just doing a paste-merge
* the 'Pasted!' micro-notifications in the options panel no longer appear when the paste action is cancelled

### misc

* added `--non_interactive_update` launch switch, which makes the client auto-choose the recommended default choice if the update routine wants to ask the user a yes/no question. if you do headless/absent updates, let me know if this is sufficient
* the splash screen now prefers to use an svg, and I have drawn an svg for it to use. it looks like the old png. feel free to create your own `db_dir/static/hydrus_splash.svg`  (or .png) file and that will be used instead. it renders at 144x196, the size of the old png, but maybe we can adjust a little now we have the tech
* fixed a small blank box that was appearing in some stylesheets in the 'external call' box of the new exe manager UI
* fixed thumbnail redraw in the new thumbnail rendering tech when you change stylesheets or flip darkmode or change blurhash rendering
* fixed thumbnail redraw in the new thumbnail rendering tech when you change thumb border or margin
* yes/no dialogs (and some other 'quick' dialogs) now max out at ~48 lines of text height. they get a scrolling panel and everything, but if these guys want to dump a gigantic list or error traceback or something, they'll stop being a giant column
* all file imports will now assign 'ignored' status to a file that is 'already in db' but for which the file filtering options would deny (let's say you have an import folder set up to not get any pngs). previously, these files were set as 'already in db', before the file filtering checks had a chance to make a judgment, and since the file was therefore considered 'successful', additional metadata like tags could be applied even though the file would have been ignored otherwise. it will now be set as 'ignored' and no metadata added
* if you have multiple since/before time predicates of a particular type in a search (e.g. 'imported since two weeks ago' and 'imported since one week ago'), the search is now careful to select the most restrictive of those, satisfying both. previously it pseudorandomly selected one to use (issue #2089)
* fixed the 'x files were not in client' error label when you try to copy some non-sha256 hashes and not all of them can be found. it was counting wrong before and just saying the total selection size
* fixed right-clicking on files with unknown filetype (the new open-with executable stuff wasn't handling it correct)
* if the deferred physical delete system encounters a file with seemingly no file info, the system now stops deferred physical delete for that boot and gives the user a note that they should regen their local hashes cache. this symptom seems to be a knock-on from a desynced hash cache

### boring stuff

* refactored some 'manage options' stuff so it is less coupled to the dialog
* the favourite tags list is now only refreshed across your autocomplete dropdowns if it actually changes on an options ok
* some custom-colour widgets now only redraw themselves if darkmode actually flips on options ok
* fixed a mermaid chart in the 'virtual memory in linux' help
