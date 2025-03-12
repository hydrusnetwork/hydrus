---
title: Changelog
---

# changelog

!!! note
    This is the new changelog, only the most recent builds. For all versions, see the [old changelog](old_changelog.html).

## [Version 613](https://github.com/hydrusnetwork/hydrus/releases/tag/v613)

### misc

* I think I have fixed the crazy flickering dialog resize bug where if you resize certain dialogs shorter or thinner than their parents, they might flicker throughout your resize motion between the size you are moving to and the height/width of the parent. there's still some occasional flicker due to some other legacy fuzzy padding hacks, but things are better
* fixed some bad grammar for the namespace hide/show options in `options->tag presentation`, and split the non-namespace rendering settings out to their own box
* when files are imported, any existing 'media result' object for the file is now properly updated with the new file modified time. you usually wouldn't notice this, because the media result typically isn't loaded until after import when we need to show it on screen, but in advanced cases where you were re-importing previously deleted files you are looking at or doing Client API work where you did a URL lookup before deciding to import, and the media result object from the URL lookup was still in memory, the 'media result' was not getting the timestamp and subsequent inspections or edits of the modified timestamp were failing as a result until the media result had a chance to decay out of its cache and be reloaded from disk
* made some ratings update and sort code more safe against ratings service deletions
* url classes now allow 'keep extra parameters for server' if you have an API/Redirect URL Converter. I _think_ the reasons for this originally being prohibited were only a fear, not anything grounded, but let's see how it goes

### system predicate for advanced tag search

* _after talking about it with people recently and having some good ideas, I decided to just push and try to knock this out. it is pretty clever and may have bugs, so let me know how it goes_
* added a new `system:tag (advanced)` predicate, which does sophisticated tag searches. you enter a tag as raw text and can then--  
    * specify which tag service it should search on, if different to the current tag context
    * specify if it should include siblings or just be the raw tag on the 'storage' domain
    * specify whether you should search current, deleted, pending, or petitioned mappings
    * specify if the file _should_ or _should not_ have the tag mapping
* I ran out of time to implement system predicate parsing, but I planned the pred's label to support this and will try to get it done next week
* searches that include unified or deleted file domains or any other crazy stuff may take a very long time to return, but the underlying tag search code in hydrus is pretty robust, and extending it to the newer domains all just came together, so I think everything works. it should respond quickly to the cancel search button if it takes too long

### duplicates auto-resolution

* I had more success than expected with the new preview panel and I think we are now about two weeks away from the initial user test of this system
* the edit duplicates auto-resolution rule dialog now has a live preview panel. it loads the pairs of a rule's search and then does the comparator/selector test to determine which pairs pass or fail, showing you the counts at each stage
* the panel also shows the pass/fail thumbnail pairs with some new 'thumbnail table' widgets I wrote. these load thumbnails asynchronously and should scale up to thousands of pairs no prob. I am really happy with how it worked out, as this was the thing I was dreading would take weeks of rewrites, but I figured something out. it is ugly, as always, but it works
* every time you show the panel page, it checks if the rule has changed. if search has changed, it re-runs the whole search, and if only the selector has changed, it just does a re-test
* next week I'll add the ability to launch a particular pair into a standard Media Viewer so you can 'look closer' on the preview, and then I'll be doing final integration and testing. we are on the home stretch now!
* _if you are an advanced user and you've poked around the duplicates auto-resolution UI previously, you might like to check out the preview panel this week on the default jpg vs png rule--does it all seem to load up sensible results, even though you can't zoom in yet? any errors? I'm guessing that loading thousands of pairs is going to be super slow, so what would be a good number to sample--256?_

### boring cleanup

* reworked the client thumbnail cache to work on the simpler and lower-lever `MediaResult` rather than the UI-level `Media`
* fixed a couple areas where file maintenance jobs were being scheduled using the `Media` object
* fixed some old areas within file maintenance where media objects had the wrong name
* reworked and cleaned the main GetThumbnailPath RegenThumbnail file routines to similarly only work and talk about `MediaResult`
* fixed a dumb typo in the as-yet-enabled `MetadataConditional` edit-panel
* updated the faq with answers for why I work alone, do weekly releases, and use weird versioning
* fixed a couple places where I had accidental `/n` in some label text lol, thanks to the user who pointed this out

## [Version 612](https://github.com/hydrusnetwork/hydrus/releases/tag/v612)

### misc

* I added 'you can scan for this' flags for JXL for rotation EXIF, has EXIF, has non-EXIF, has transparency, and has ICC Profile, which we forgot to add when first rolling out JXL support. all existing JXL files will be scheduled for rescan of these properties on update, so if you have any wrongly rotated JXL, they should fix themselves soon after update (issue #1684)
* the 'duration' duplicates filter comparison statement now says the +/-% difference in duration. if it is only +1%, it is now clearer
* if a server gives a 429 (Too Many Requests) with a 'Retry-After' response header, hydrus now obeys this rather than its default server retry time as set in `options->connection` (issue #734)
* added `help->debug->debug modes->macOS window position fix test` to test a fix for macOS windows always getting delta y position on init

### drag-cancelling tech

* the new drag-cancelling tech was false-positive cancelling fast drags where you moved the mouse outside of the window 200ms after the initial click press. this is fixed
* the new drag-cancelling tech no longer occurs on macOS, since it was raising an error. it seems due to system policy you can't programatically cancel a drag on macOS in Qt (issue #1685)

### sidecars in export folders

* an export folder with sidecars will now fill in any sidecar gaps on every run. if a file should have a sidecar but currently does not, the sidecar will be generated (issue #1682)
* an export folder set to 'synchronise' (which deletes files from the export destination if they are no longer in the export folder's search) will now be more careful not to delete sidecars

### some running from source stuff

* for users who run from source, the 'test' `PySide6` is updated from `6.8.1.1` to `6.8.2.1`, and the `qtpy` from `2.4.2` to `2.4.3`
* added a `open_venv.ps1` script to easily activate the venv in powershell

### duplicates auto-resolution

* _my work this upcoming system grinds on. I successfully did the thing I stalled on a couple weeks ago, and now the only big thing I still have to do before advanced users can try it is a preview panel and a billion unit tests_
* the database modules are live! they boot and will initialise their (as-yet empty) tables on update to v612
* the daemon is now live! it runs its full mainloop and consults the database modules for work
* rewrote some daemon-db interaction, mostly for KISS and deduplication of responsibility
* figured out some tech to reset duplicates rule search progress on edits and user command
* simplified the daemon workflow so that rules hold on to cached search counts and report their own search status
* fixed some stuff in rule-setting and status fetching
* the auto-resolution rule object is now serialisable and _could_ be saved to disk if I enabled the edit UI
* rules now report their correct search status, no longer a placeholder
* the daemon now reports the correct running status, no longer a placeholder

## [Version 611](https://github.com/hydrusnetwork/hydrus/releases/tag/v611)

### misc

* I am pretty sure I fixed the long-time 'hey why did the scrollbar on this page of thumbs reset to the start position sometime while the page was hidden?' issue. an importer that adds new rows of thumbs in the background should now retain its scroll position. a window resize or a mass file removal event will cause the scrollbar to stay at the same relative num_rows vertical position, which we may ultimately want to be more sophisticated, but this is a good step for now. let me know if any specific situation still resets the vertical position
* fixed an interesting bug with two of the Drag and Drops in the program, when you DnD a page tab or a selection of thumbnaills, where if you released your left-click at just the right moment (about 100ms after click press), you could get a DnD state that persisted despite no mouse button being down. a subsequent click would clear it. it seems that the DnD was spawning while the click release was already behind it in the event queue. the program now recognises this state and cancels the DnD
* I believe I fixed an issue with the `apply image ICC Profile colour adjustments` entry on the media viewer's 'eye' menu button, precisely when you were looking at a file. the static image's private tile cache was not clearing itself correctly, and not calling for an update after the clear, so old yes/no ICC-profile-adjusted tiles were hanging around and sometimes poisoning future calls. the whole system clears itself properly now and seems to flip good every time
* I believe I have fixed a macOS issue (and I think X11, too, if you have a taskbar on the top of the screen) where the hydrus window position-recording system would move your windows down a little way on every save/load cycle
* all the 'write/edit' tag autocomplete inputs that have a list above them now send a copy shortcut to that top list when there is nothing selected in the text box and there are no results in the list below. so, if you open the 'manage tags' dialog, and the first thing you do is hit ctrl+c, you'll copy everything in the big list of existing tags. hit ctrl+shift+c, and you'll get the parents too
* all the hardcoded 'copy' shortcut detection now happens through the same location and counts ctrl+c or ctrl/insert
* if the 'is user ok to ok/cancel' dialog pre-close checks raise an error, I now have a catch for it. it says 'hey user, these checks threw an exception, please contact hydev, the data was probably broken so here is what to do next depending on whether you were oking or cancelling'. previously, you could be stuck with an unclosable dialog and have to quit the whole process
* same deal but for the dialog 'is the data in the panel valid?' check--there is now a special catch and it tells you what happened and what to do
* fixed a regression from last week's "make sure the new note is focused when the current tab changes" call, which was throwing a spurious error when you deleted the last note (issue #1679)
* fixed an issue with my mpv rewind-spam catching code when you force it to load a file without any duration

### file sort

* if you change the file sort on a search with an explicit system:limit, and the sort is one that can operate at the database level, the search will now refresh
* added a checkbox to `options->file search` to turn this off if you prefer
* the file sort widget now has a tooltip saying whether the current sort type is simple enough to work with system:limit

### stopping accidental page close

* if you try to close a downloader that has any items in it, you'll now be asked if you are sure. this doesn't apply to session exit, just manual user close events
* you can turn this confirmation off under `options->gui pages`
* another checkbox under `gui pages`, this time default off, allows you to confirm all page closes. this mostly catches middle-clicking single page tabs, be that file search pages or 'page of pages'
* the routines that delete multiple pages in one step 'close other pages' etc..., now do the 'is user ok to close these' in one combined step for all closees before closing anything. previously it tested and closed each in turn, and a cancel event broke out of the loop
* various 'close these pages?' messages now correctly add up the number of sub-pages in 'page of pages' to be closed

### long-time bug with non-updating media viewer is fixed

* for ages we've had a weird issue where the media viewer, on some random file, will suddenly update when you click on ratings and things. the content signals are going through, and you can watch the file's respective thumbnail in the main gui getting archived or whatever, but the media viewer will not show it. this is finally fixed! it was basically a rare maintenance update issue, where if, for instance, a 'regen file metadata' job occured on a file in a media viewer's list after the media viewer was spawned, the media object in the viewer list was falling out of sync; able to send content updates but no longer hooked into the update pipeline so it never received them back again
* this is fixed for the 'force filetype' action. this job now propagates to the UI much faster than before, no longer needing a full media result load
* this is fixed for the file maintenance jobs that regen file metadata, check for 'has icc profile' etc.., and regen pixel/blurhash. all these jobs now propagate in the same way much faster to the UI
* this is fixed for the file maintenance job that refetches the file's modified time from disk. same deal it now updates in UI faster
* also fixed in the case where a previously known-of file is imported and we discover our old file info was incorrect, and also this file was in view so we need to sync the media result. sounds like a crazy situation but that's exactly when you need this to work

### tag context in media

* the thumbnail grid is now aware of the current tag context of the search (where you set 'all known tags' or 'my tags' or whatever in the autocomplete dropdown). `system:number of tags` now follows the current tag context

### shortcuts

* in an experiment, you can now set the modifier keys as their own shortcuts, with no accompanying 'real' key. it'll mark it as 'ctrl+nothing', 'shift+alt+nothing', etc.. seems to work, but I can't promise it won't go crazy in the wrong place
* the keyboard shortcut widget, where you enter a shortcut, now uses a shortcut catching routine that is one level higher than before, which matches the actual shortcut processing system that's in use. there's a chance that if your Qt hardcode maps some shortcut, not allowing it in a text edit box, it'll work now (issue #1674)
* the keyboard shortcut widget no longer shows its caret. it also takes keyboard focus more reliably when the edit shortcut dialog boots. I kind of like this but also don't, let me know if it is jarring
* the 'shortcut report mode' will now say some information about unmappable key presses
* I have prepped some render code to show shortcuts on macOS in the form ⌘Z, but I have not enabled it yet because I don't know enough about macOS. if you want your shortcut labels to look like this everywhere, let me know. but if shortcuts should only look like that in menus, and it isn't appropriate for the shortcuts dialog and debug labels and stuff, I'll put it off until we actually have menu shortcut labels lol

### parsing

* I added a 'STATIC' formula type. it just spits out the same static text, every time, and repeated n times if you need it
* added a little help documentation for the new STATIC formula type; the edit panel links to it like for the other formulae
* if your parsing test panel gets something that doesn't seem to be html or json, it no longer puts the goofy quote marks around it

### boring code cleanup

* did some misc refactoring in the page close testing code because the method names were whack
* cleaned some sidebar and autocomplete interactions to work with 'tag context' instead of 'tag service key', which means these guys are now sending a richer object with more tag display info in it
* cleaned up some duplicate variable handling all through the sidebar stuff
* a bunch of redundant location context emit spam from the sidebar is deleted. I don't think this will break any weird thumbnail grid or previuw canvas location stuff , but we'll see in the edge cases
* cleaned up how query autocomplete dropdowns and sidebar panels were communicating search state changes
* ratings that fail to draw for whatever reason now do so more safely
* removed code that did the old and canvas-desyncing media object update routine

## [Version 610](https://github.com/hydrusnetwork/hydrus/releases/tag/v610)

### misc

* files with an average colour with less than 3% saturation in the HSL colour space (i.e. completely greyscale, or otherwise averaging to grey) are now propagated to the end of the Hue sort, whether red or purple first
* hitting ctrl+c on a taglist with no selected items now copies all items
* updated the system predicate parser so it can read 'number of pixels'. previously, it could only handle 'num pixels'. this means you can copy/paste a 'system:number of pixels' pred back into the autocomplete and it should all work
* fixed a problem with `system:num file relationships - (test) "not related/false positive"`, which was only every returning the results of one not-related alternates group, rather than all that matched the test
* made some 'click below to copy to clipboard' menu labels bold
* the client now says 'tag mappings' explicitly, rather than 'mappings', in a bunch of UI labels like shortcut action descriptions

### notes

* the 'start editing notes with the text cursor at the end' setting under `options->notes` now applies to all notes in an 'edit notes' panel with multiple notes
* clicking a new note tab in 'edit notes' now immediately focuses the underlying note so you can start typing
* if you have made changes, the 'edit notes' panel now confirms if you want to cancel. let me know if this produces false positives--there's some 'note cleaning' stuff I don't account for

### file viewing statistics

* the new 'client api' views are now integrated into the UI for search, sort, and view
* the way file viewing stats are presented in the media right-click menu is simplified. the stuff under `options->file viewing statistics` is down from five different options to two (show the views summed with a stack of the components in a submenu, or just show the stack of separate count types up front), and there's a new checkbox list with media, preview, and client api views so you can select what you want to see
* sorting files by media views now obeys the above 'what you want to see' setting, summing the respective values. previously it just did media views
* `system:file viewing statistics` now allows for selection of 'client api views'
* `system:file viewing statistics` now renders itself in the form `system:views/viewtime in (domains) (operator) (value)`, where 'domains' is a comma-separated combination of `media`, `preview` and `client api`. previously they were `system:media/preview/all views/viewtime (operator) (value)`
* if domains is left blank, I substitute the above 'what you want to see' option, so you can now just type `system:views > 5` and you'll get something reasonable
* the old forms still parse but are unchanged and won't support client api
* added some new unit tests for this
* as a side thing, I did the same pixel-perfect-height update that I did for multi-column lists to most of my checkbox lists across the program, including for canvas view selection around here. they just fit better now
* I overhauled some file viewing stats db search code. the predicate still holds some stupid variables that I'll want to rework one day, but the meat of the db search code is now ok

### advanced parsing logic and overhaul

* subsidiary page parsers have a new 'sort posts by source time' checkbox, default off, which sorts what this subsidiary parser chops up according to any parsed source time, newest first. use this if you are, obviously, parsing things that each have a source time you'd like to sort by but which come in some other order, e.g. you have two individually sorted pages of results in one document and you'd like to interleave them
* wrote up proper objects to hold 'parsable content description', 'parsed content', and 'parsed post'. previously this was a big mess of tuples upon tuples and 'all parse results' vs 'whole page parse results' semantic sludge
* refactored `ClientParsing` to a new `parsing` module, added `ClientParsingResults` to handle the new objects, and split off old file lookup stuff to `ClientParsingLegacy`
* all parsers now use the new objects to report what content they can parse
* all parsers now use the new objects all along the parsing pipeline! the whole thing is done and much nicer
* deleted a ton of old bad code that was navigating this before
* deleted some old bytes/str error-handling back from the python 2 days
* when a gallery url is worked, it now reports fully, in the gallery log note column, how many sub-gallery urls were parsed, and how many were previously hit this run, and how many next gallery page urls were parsed, and how many were previously hit this run, and whether a url class extrapolated next gallery page url was generated, and, the same deal, if it was previously hit this run. previously, this guy mostly just reported the latest interesting thing to happen--now it is comprehensive
* fixed an odd bug where the gallery worker could add a sub-gallery urls that pointed to the API redirected URL that created it
* fixed an odd bug where the gallery worker could skip the 'seen this url before in this parsing run?' check for an auto-generated 'next page' gallery url fallback step
* cleaned up the gallery url 'work' code significantly
* fixed a note parsing issue in the downloader where note texts were not always being cleaned on parse
* overhauled the subsidiary parser test panel to use the actual code as-in the subsidiary parser, rather than a facsimile
* got the page parser and subsidiary page parser test panels to recognise empty input rather than outputting errors on failed conversions of the empty string lol
* all the 'raw data'/'post conversion'/'post separation' tabs in the parser test UI now show up to 64KB of data. previously, the latter two were still capped to 1KBs
* fixed some bad layout in the edit subsidiary page parser panel
* cleaned up some lazy variable names in the subsidiary page parser code
* cleaned up how subsidiary page parsers initialise their edit panel
* fixed a layout issue in the 'edit login step' panel where there were now two nested 'content parsers' static boxes

### some subscription logic and UI

* cleaned some of the subscription gallery search logic, especially the 'have we caught up to where we were despite the (large) gallery page not being finished yet?' test, which has a couple of false positive edge cases solved
* cleaned some duplicate code out of here
* subscription queries now have an editable 'compaction number', which governs how small they should trim themselves to. this was previously fixed at 250 items, but is now changeable for advanced debugging purposes under the edit subscription query panel
* if you have a very large periodic file limit or the site produces a huge gallery page, the compaction number will now increase dynamically to ensure the subscription maintains a healthy cache of urls to consult for the size of our job
* the edit subscription query panel gets a layout overhaul. the stack of widgets is now grouped into boxes
* the `options->downloading` page now specifies that the two checker options buttons are for the subscription/watcher _defaults_
* as a side thing, watcher check logs now record up to 500 entries before removing old items. used to be 100

### weird thing

* the tag autocomplete searches across the program that manage a `read/search` context (as opposed to a `write/edit` one), will now pass a keyboard copy event to their top list if there is no selected text in the text input and there are no results in the search list below. actually getting into this situation is tricky, but this is really prep for a future overhaul of the write context, where no results is the default situation on an empty input but which cannot actually talk to its top list yet

## [Version 609](https://github.com/hydrusnetwork/hydrus/releases/tag/v609)

### macOS app now comes in a zip

* the macos-13 runner that we recently moved to has been taking way too long to build the App DMG. under ideal conditions it will take ~6 minutes, but sometimes it will be 45+. this is an unfortunate and widespread issue without an excellent fix
* thus, the macOS App is now distributed in a zip (that takes about 30 seconds to build and is the same size as the DMG lol)
* unfortunately this means we can't have the Applications shortcut or the ReadMe; you'll be double-clicking the zip to extract the App, and then dragging it to your Applications yourself
* I have updated the 'getting started - installing' guide with the 'allow unsigned apps' stuff from the ReadMe
* I am increasingly of the mind that macOS users should consider running from source. the App is built for intel chipsets, so if you are on Silicon, you definitely should: https://hydrusnetwork.github.io/hydrus/running_from_source.html

### misc

* INFO: reducing the 'too many events' mpv error-handling hook worked well. if you saw a bunch of these in the past few weeks, these were almost certainly false-positives. the files were likely not broken, they were just taxing your computer for a bit and the error was firing accidentally. if you set up a special workflow to isolate or deal with these files, please undo it
* the new 'group by namespace (user)' list widget under `options->sort/collect` now accepts `:` to represent 'all other namespaced tags' if you would like to put them somewhere specific
* fixed a typo in the new duplicate files 'has duration' comparison strings. it said 'the other has duration, the other does not' when the current file had no duration
* the score for duration now scales from 1 to 50 depending on how much longer a vid is than the other on millisecond longer = 1, twice as long = 50 (cap). this is all still just hardcoded stuff I'm playing around with, and I expect it to formalise to something completely user-customisable as the tools from duplicates auto-resolution firm up
* added a little section to 'help my db is broke.txt' talking about the sqlite3 terminal and how to get it on non-Windows

### colour sorting

* after talking with some users, and learning that our blurhash provides the average colour of image thumbnails, I went bananas and added five new 'average colour' file sorts--
* `lightness` - sorts light-to-dark in the Lab colourspace
* `hue` - sorts the standard red-orange-yellow-green-cyan-blue-purple colourwheel/rainbow in the HSL colourspace
* `balance - blue-yellow` - sorts blue-yellow chromaticity in the Lab colourspace
* `balance - green-red` - sorts green-red chromaticity in the Lab colourspace
* `chromatic magnitude` - sorts the combined chroma value, which is basically 'is it grey or colourful' in the Lab colourspace
* this works on any file with a thumbnail!
* they all work with system:limit, also!
* and the Client API--new `file_sort_type` definitions are in the Client API reference
* I am extremely pleased with how this all worked out. there are some weird results because it is average colour, rather, say, than a carefully selected 'primary colour', and I think it could do with some more work, to perhaps, for instance, push remarkably grey images to the bottom of Hue sorts, but this really works and it simply looks cool to do and then scroll through. it is a good base and proof of concept for my original plan to make colour histograms for files and distinguish between images that are muddy all over versus white and red. let me know where this succeeds and fails, and we'll see what improvements we can think of

### janitor stuff

* in the petition processing page, when you process a petition, either the normal way or via the mass approve/deny buttons, the 'currently highlighted petition' moves to _after_ the current one (or the next available one if you process multiple at once). previously this was resetting to the 0 position on every mass approve/deny. it should ripple down a bit more naturally now
* when you set to apply multiple petitions at once, the pertinent list rows now instantly to show 'uploading...' status
* I wrote a whack of test code that loads up and processes fake petitions for the petition page, so I can test these workflows much easier now
* I fixed the 'modify account that uploaded this tag' for tags that include the '+' character. sorry for the long-time trouble--it was a stupid GET args parsing issue I missed in early code

### boring code cleanup

* broke up the 'ManagementPanels' monolith, refactoring it to a bunch of smaller files more under the 'Sidebar' name
* renamed the ambiguous 'management type' to 'page type', and 'management panel' to 'sidebar', and 'management controller' to 'page manager' across the program
* cleaned up some old static superclass calls in here to `super()`
* brushed up the code generally around here, ditching some bad ideas and scope design
* fixed a small instability trigger in the main file query routine
* cleaned up some more inartful controller scope code in page and downloader UI
* cleaned some ugly `QLineEdit` initialisations across the program
* updated the server requirements.txt, which isn't used for anything but a reference, to use the newer OpenCV; I just forgot to update it a while ago

### pyproject.toml

* a user made a 'pyproject.toml' file. this is basically a cleverer requirements.txt that allows for better dependency options. I learned a bit about these files this week and I quite like them. pip can handle them too, so this would be one way to simplify my setup_venv scripts to a single call and allow users to set up simple custom automated situations
* so, just for now, there's a pyproject.toml in the base directory. if you use `uv`, feel free to play around with it. I will manually keep it updated and version-synced to our requirements txts, and I wouldn't be surprised if I switch to it as the master soon. I'm going to do some other work and research and testing first though

### duplicates auto-resolution

* I did a little work on the daemon, but I didn't feel great about it tbh. I know roughly the various things it needs to do, but I'm not firm on what should be the correct orientation of everything. I'll keep at it, and I may do more UI so I have better feedback while I am doing final integration here

## [Version 608](https://github.com/hydrusnetwork/hydrus/releases/tag/v608)

### mpv

* my ill-fated mpv-choking error hook, which tries to catch when MPV is having a 100% CPU event and unloads the file in a big fuss, and which has unfortunately caused a whole bunch of false positives, is now flipped on its head. instead of catching all instances of the log output and trying to exclude 'oh that's fine' cases, the hook now precisely targets files that go irrevocably 100% CPU on loop, specifically by recognising files that reload too frequently in one second for their duration (e.g. a normal vid looping twenty times in one second). mpv will be back to being juddery sometimes, but whatever, that's better than what I was doing
* the new 'DEBUG CAREFUL: Allow "too many events queued" files' checkbox no longer does anything and is removed
* also, the mpv emergency dump-out code is back to being per mpv player. previously it would unload all players the client was managing
* my mpv player now uses a little less CPU when mouse-drag-seeking

### misc

* I am changing the tag sort logic such that if you group by namespace, the namespace order stays as it is, no matter the underling asc/desc order of the actual sort. in simple english, this means that creator tags stay at the top whether you say 'most first' or 'fewest first'. we had success with the 'namespace (user)' just recently, and after talking about it with some guys, I think I agree that doing a full reverse of the whole list is not useful, and it isn't, fundamentally, what grouping is. let's try it like this, see how we like it
* the various multi-column lists across the program, which generally set their minimum and initial height by a 'num rows' suggestion, now do so pixel-perfect in most cases, no matter the style (it was previously ok on windowsvista, with a bit of fuzzy padding, but on Fusion it was either too tall or short due to font height estimate stuff). the downloader and watcher lists, which dynamically size according to contents, also do so unerringly. I find this very slightly eerie tbh so I might add a couple pixels of whitespace on the end so your brain knows there isn't more to scroll. let's try it like this for a few weeks and see how it feels
* added `--pause_network_traffic` launch parameter to the client, which hits `network->pause->all new network traffic` before the network engine initialises, to help debug when pending subscriptions or initial-session downloaders go crazy
* in 'manage tag siblings/parents', if you import from a clipboard/txt that includes a `a->a` loop-pair, the dialog now yells at you
* as a little hack, I added ctrl+shift+c to the taglist to say 'copy tags with parents' the default ctrl+c does not include the parents
* removed a duplicate and blank entry for 'EXPERIMENTAL: Image path for thumbnail panel...' in `options->thumbnails`, whoops
* I added a little safety code to the import folder, trying to catch a possible infinite loop we have seen. import folders now also take regular short breaks to give other threads like garbage collection a guaranteed moment to step in
* fixed a bad buffer truncation calculation in the native video viewer

### build/jpeg-xl stuff

* in `help->about`, moved the Jpeg-XL and HEIF(/AVIF) support lines to the second tab, and together
* if your client does not have Jpeg-XL support, the import error is now stated when you hit `help->about`. **if you are on macOS, you probably do not have Jpeg-XL support yet**, and the solution, whether on App or from source, is to run `brew install jpeg-xl` in the terminal, which is now also said in this message (issue #1670)
* added a small note to the installing help docs to say Apple Silicon users should consider running from source. the App is Intel for the time being, and running from source will give you a much more pleasant experience all around

### boring code cleanup

* refactored the `ProcessContentUpdates` megacall and its friends to a new 'content updates' database module
* refactored the duplicates file search stuff down to a new database module
* and refactored the 'set duplicates' call down to a new database module
* about 110KB of code is thus cleared out of the `ClientDB` monolith, which is down to 500KB, and we are ready to plug the duplicates auto-resolution module in as it now has scope on the various calls it needs
* fleshed out the duplicates db module's master id definitions
* cleaned up how I refer to file duration across the program. all the convenient-to-change duration or frame durations have a unified nomenclature and always say if they are in seconds or milliseconds

### duplicates auto-resolution

* the final difficult duplicates auto-resolution database problem (fast incremental duplicate pairs search) is solved. outside of at-scale testing and final integration, the database side of this is now complete. now just need to to figure out a daemon and a preview panel

## [Version 607](https://github.com/hydrusnetwork/hydrus/releases/tag/v607)

### misc

* jpeg-xl images are now fully supported! jpeg-xl is one of the contenders for 'what format do we use next?', and I think a pretty good one. it is basically jpeg but it can handle more colour depth/HDR, transparency, and optional lossless encoding, all while saving about 40% equivalent filesize to a jpeg/png. I understand it can also do animation (although we don't add that today), making it a potential 'capabilities superset' of gif as well. jpeg-xl is not well supported yet, but I hope that as more programs add support we'll see that change, and hydrus does its part today. thanks to the users who navigated this
* added some boxes to `options->thumbnails` to give it some better layout and grouping
* the 'show the media viewer top hover text in the status bar when one thumb is selected' option now defaults to True. it was a mistake to turn this off by default, and all users will be switched to True on update. the checkbox remains in `options->thumbnails` if you want to turn it off
* added 'Give thumbnail ratings a flat background' to `options->thumbnails` to turn off if you prefer to just have the ratings without the rectangle backing I added last week
* the new 'namespace grouping sort' sorted text list in `options->sort/collect` now has a paste button if you need to enter a ton of them
* a new checkbox under `options->importing` let's you stop the program switching to the destination download page whenever you drag and drop a URL on the program. this was personally driving me nuts
* when you right-click a selection of predicates that includes OR preds, the 'copy' submenu now includes an option to copy texts with collapse ORs, which renders them like "a OR b OR c" in one line, rather than the separate rows
* the duplicate filter's "comparison statements" in the mid-right hover now show if one or both files have duration. I hacked this in simply for guys who are using external tools to get videos into the potential duplicate pairs queue, and I still want to completely rewrite this thing to a fully user-editable system once I have the tools matured in the duplicates auto-resolution work
* a safety limit that would force the status bar to stick to 'x files' instead of the more interesting and cpu-intensive 'x images/collections/whatever' is raised from 1,000 files to 100,000. let's see how it goes
* fixed a sometimes-error when showing different file presentations of watchers/gallery downloaders (when you right-click some and say `show files->blah`)
* the complicated pre-download file status logic that determines if a URL-mapping has untrustworthy neighbours now prints a little log message of what it discovered when it hits a positive. this thing runs a little quiet and I want to see if it is firing too often or is not quite checking what we want in difficult cases
* fixed a weird typo when unsetting the EXPERIMENTAL media viewer background bitmap thing in `options->thumbnails`

### MPV

* I did some work trying to handle the 'too many events queued' problems we've seen with mpv recently. I cleaned some code and reduced the overhead of my custom event handling, but I am generally convinced that some of the problems we've seen are due to 100% CPU bugs in various libmpv versions, particularly because I can set the 'loglevel' of mpv to 'no', for 'nothing at all', but the error still happens, suggesting there is probably no log-processing speed I can do on my end to fix this. I am leaving the emergency-dump-out code in place, but for this specific 'too many events queued' error it no longer adds that file to the 'never load again this boot' list--you can deselect the file and then reselect to try again (although it seems like the mpv player's event loop can be poisoned by the situation and lags a bit on next load). I have also seen the error occur at I believe the start of playback, but then I could load the file fine another time with the same dll, which suggests the log stuff can pile up due to a brief busy period in thread scheduling or whatever. so, there is more to do here--perhaps a 'if we get the error persisting for more than two seconds' or something
* I did discover a different loop flag I could set for mpv that fixes one of the reliable problems--setting 'loop-playlist' rather than 'loop-file', which seems to force the file to reload and avoids the EOF rewind bug that mpv is running into. if you get the error on the first loop of a file, try hitting the new checkbox under `options->media playback` and we'll see how it all goes
* I also just bit the bullet and added a DEBUG option, also to `options->media playback`, to disable the new 'too many events queued' dump-out hook. if you hit many false-positives and are feeling brave, try turning it off, but you may have to deal with some 100% CPU situations

### viewtimes are now in ms

* the filetime viewing stats system now records total viewtime in ms (previously it only had 'second' resolution). this doesn't matter all that much, but all the little deltas it adds are now 'viewed file for 3.2 seconds' rather than always rounding to the nearest integer
* the settings under `options->file viewing statistics` are now full 'time delta' widgets that support ms, so you can say 'viewing a file for at least 2.5 seconds counts as a view' rather, again, than having to deal with full integers all the time
* system:viewtime now supports milliseconds input for viewtime ranges
* mr bones now reports a ms-precise (float) total viewtime (e.g. 3.456s) for the current search

### client api

* the client api can now see and edit file viewtime statistics!
* `/get_files/file_metadata` now states the file viewtime statistics (last viewed time, total views, total viewtime for the different viewer types) for each file
* file viewtime statistics has a new 'client api viewer' enum, separate from the existing 'media viewer' and 'preview viewer' record, if you'd like to do your own thing. I've hacked this a bit, and it doesn't show in the normal Client UI yet, nor can you search on it via `system:file viewing statistics`. the current options on how to show viewtime (`options->file viewing statistics`) are frankly crazy, so I think probably we'll want to go to a list of simpler checkboxes or something and stop trying to be clever
* the new `/edit_times/increment_file_viewtime`, which needs the existing 'edit times' permission, lets you add views and viewtime and set the latest view timestamp
* the new `/edit_times/set_file_viewtime`, which needs the existing 'edit times' permission, lets you set fixed values (i.e. if you are migrating from one client to another)
* I have not added a delete/clear call here yet. if you would like to do this, let me know what you would like. the client only has 'clear everything for this file' and 'clear all records completely', but I expect we'd want the ability to clear by view type?
* wrote help for this
* wrote unit tests for this
* client api version is now 78
* the rich version of `/get_files/file_metadata` is now providing a lot of personal user metadata like inbox, ratings, local tags, and now viewtime statistics, making the 'just share some files with a friend' scenario less attractive. I was considering adding a new 'edit file viewtimes' permission today that would allow the edit and also dynamically show/hide the new viewtimes, but I think it would be better if I make a _read_ permission in the _ouvre_ of 'can see user file metadata', which, if absent, will mean callers can only ask for the basic file information. this permission may apply in other places, and the whole client api permissions system could do with a pass and likely some KISS. let me know what you think!

### boring cleanup

* cleaned up how some thumbnail-focus-delegation happens on new file focuses
* cleaned some viewtime pipeline code generally
* fixed the API help json example requests for `set_time`, which didn't have `file_id` stuff
* replaced all my 'convert ms time to s time, but a float, oh except I guess when it is null, don't forget bro' code with a single and safer unified call across the program
* cleaned up some agnostic 's or ms' duration calls, but there's plenty more to do

### build updates

* last week's 'future build' went well, so I am folding the changes into the normal build. users who run from source may like to run their `setup_venv` script again today, and users who would like to run from source but only have python 3.13 now have a route to run hydrus
* details--
* PySide6 (Qt) is updated from `6.6.3.1` to `6.7.3` (test version is now `6.8.1.1`, which source users on Python 3.13 can run)
* on macOS, PyQt6 (Qt) is updated from `6.6.0` to `6.7.1`
* OpenCV (image stuff) is updated from `4.8.1.78` to `4.10.0.84`, which lets us update numpy (test version is now `4.11.0.86`)
* numpy is switched from `<2.0.0` to `>=2.0.0`. this adds Python 3.13 support to hydrus for source users
* pillow-jxl-plugin is added, and thereby we have Jpeg-XL support (thanks to some users for navigating this!)
* the python mpv package is updated from `1.0.6` to `1.0.7` (test verison stays at `1.0.7`; there is nothing new)
* twisted (the networking engine that runs the hydrus server and client api) now includes better TLS and http2 support
* some import hacks that helped old PyInstaller navigate numpy and OpenCV bundling are removed

## [Version 606](https://github.com/hydrusnetwork/hydrus/releases/tag/v606)

### tag sort

* when you group sorted tags by namespace, you can now force the order of the namespaces! this means you can have all the creator tags first, then the series, then the character, etc..., in any order you want. specifically, tag sorts in 'tag' or 'count' mode have a new 'group by namespace (user)' option that applies the sort override. you can set the namespaces you prefer under a new list in `options->sort/collect`, and the default is `[ creator, series, character, species, unnamespaced, meta ]`. any namespaces that do not fit will be grouped (a-z) underneath, just as before
* sorry for taking so long to get to this. thankfully it worked out well, enough that I have set 'group by namespace (user)' the default for new clients; I recommend everyone who is familiar with normal booru namespace sort set this too under their `sort/collect` page
* tag sort will handle some unusual unicode character comparisons (e.g. 'ß' vs 'ss') better
* tag sort will now reliably sort non-ascii namespaces above unnamespaced tags when grouping by namespace

### misc

* the `database->view file history` chart now has checkboxes for all four lines. its code is cleaner and it now updates itself faster and nicer, and charts from old searches are now deleted promptly
* fixed the position of the 'collection' thumbnail icon when you have the new 'show ratings on thumbs' set. also, the backing colour on the collection count now covers the icon; the colour of the backing panel and texts now feed off your current stylesheet; and I generally cleaned up how the icon and text position themselves
* after last week's not-excellent background highlighting for ratings on thumbnails, I bit the bullet and just did a flat background with your normal qss window panel colour. inc/decs get a background too. it looks _fine_ and thumbnail ratings are now clear in all situations--it basically looks like the top-right hover now
* the file right-click menu's top row flyout metadata submenu, which shows details like file modified time, now includes the exact file size in bytes
* the top hover window's 'EXIF and other stuff' button is moved to the center button row, has a new 'page with text' icon, and is always available since it now will always show the contents of the flyout metadata submenu. you can thus now see the data in this menu from the archive/delete or duplicate filters

### boring code cleanup

* in bad-idea-cleanup twelve years in the making, refactored the 'listening media list' out of the navigable canvas subclasses. the underlying list is now handled inside the object rather than being the UI panel itself
* the duplicate filter also gets some 'listening media list' cleanup. it handles its own content updates and the handling of what to do after deleting a file in the pair is now more safely wrapped inside the same atomic event
* updated up an old 'remove media' pubsub, from the browser media viewer to the underlying thumbnail grid, to be a nicer Qt signal
* updated the same thing from the archive/delete filter's commit, which can have special remove logic when the filter is complete, and replaced a hacky second-remove, which tries to catch users who hit F5 very quickly after an archive/delete is complete, with a popup that appears after two seconds to show slow commits actually happening--we'll see how it does IRL
* fixed some recent 'woah that text-and-thing went to the right' bad layout in the 'edit shortcuts set' and 'edit subscription' panel--thank you for the reports
* optimised some media result load
* cleaned up some media result caching sync around the database repair code
* deleted some static old colour defs that I missed in previous sweeps. now I updated the colours in the thumbnail collection stuff, none of them are used any more
* reworked more garbage thumbnail ratings layout code
* did some tag sorting KISS refactoring

### duplicates auto-resolution

* broke the new database module into two--one for the clever search side, the other for the simple storage side. the main (duplicates) db module will now see the storage and keep it updated on new/dissolved potential duplicate pairs
* merged the rule-setting gubbins together into one 'set rules' command and added search-resetting code on search updates
* wrote a status-count cache for quick review of rule progress
* brushed up maintenance code for orphan rules and pairs
* fleshed out the 'let's see if these unsearched pairs match our search' tech and the 'let's see if these search-matching pairs pass our auto-dupe rules, and if so, set the action' tech
* refactored the media results generation and caching code from the monolithic `ClientDB` to a new module. the duplicates auto-resolution search module now talks to this guy
* I still have to refactor a couple more things so I can wire this all up, but this should be simple work. all the difficult parts of the duplicates auto-resolution db stuff, except for one bit of incremental search I need to figure out, feel like they are fixed. only one big difficult hurdle (the rule preview UI) remaining!

### future build

* I am making a 'future' test build today--it should be in a post beside the normal build. it is the same as the normal build except it has jpeg-xl support and a number of libraries are updated to new versions. I would like advanced users to try it out and give me feedback on any boot problems. instructions are in the release post
* build details--
* PySide6 (Qt) is updated from `6.6.3.1` to `6.7.3` (test version is now `6.8.1.1`, which source users on Python 3.13 can run)
* on macOS, PyQt6 (Qt) is updated from `6.6.0` to `6.7.1`
* OpenCV (image stuff) is updated from `4.8.1.78` to `4.10.0.84`, which lets us update numpy (test version is now `4.11.0.86`)
* numpy is switched from `<2.0.0` to `>=2.0.0`. this adds Python 3.13 support to hydrus for source users
* pillow-jxl-plugin is added, and thereby we have Jpeg-XL support (thanks to some users for navigating this!)
* the python mpv package is updated from `1.0.6` to `1.0.7` (test verison stays at `1.0.7`; there is nothing new)
* twisted (the networking engine that runs the hydrus server and client api) now includes better TLS and http2 support
* some import hacks that helped old PyInstaller navigate numpy and OpenCV bundling are removed

## [Version 605](https://github.com/hydrusnetwork/hydrus/releases/tag/v605)

### ratings on thumbnails

* thanks to a user, ratings are now displayable in thumbnails! hit the new 'show in thumbnails' service checkbox in _services->manage services_ and that service's ratings will show
* I updated this a bit and added a second option for 'show even when there is no rating value'
* I played around with different backing colours to make these new ratings stand out more. in the end, my best solution was very hacky and isn't amazing--the stars in particular can get washed by a banner or busy thumb underneath. I tried a block of backing colour but it all looked worse. we may be approaching a 'just do it with svgs' moment for ratings rather than my decade-old painter primitives and coordinate lists. have a play with it and let me know what you think
* I improved some rating drawing positioning, too--some stuff was off by half a pixel etc..
* thumbnails now refresh when after a _manage services_ ok

### misc

* did a hotfix a couple hours after v604 release, v604a, to fix an issue with double/middle-clicking collection thumbnails to launch the media viewer
* I deleted the Endchan /hydrus/ board and removed the links from the client and help. the board was intended as a bunker and never got much traffic, but the whole site being spammed this week reminded me that I don't want to own a board any more. if we ever need a bunker again, I'll revisit the issue
* fixed some file-picker dialogs' name filters, which were not filtering to PNG or JSON correctly. all file dialogs that filter files this way now also offer `Any files (*)` as a second option
* the Lain import downloaders dialog now filters the file-picker to .png files
* I reworked the 'top hover file summary' settings under `options->media viewer` to their own box with a bit of extra text, and I renamed the complementary setting under `options->thumbnails` to the clearer "Show the media viewer's top hover file text in the status bar when a single thumbnail is selected"
* I did a bunch of layout work this week, cleaning up how things position and expand to fill available screen space. there were several hundred things impacted and I did not have time to check everything that might have been changed. please let me know if some dialog has a help button that's weirdly aligned etc.., thank you!
* cleaned up the reason-initialisation of the advanced file deletion dialog. the list of reasons is now much more item-position-stable and will not create duplicates when intersecting options clash. the selection rules are now simple: if all the file(s) have existing deletion reasons, this reason is listed, marked as the existing reason, and selected; otherwise, if the dialog is set to remember the previous deletion reason, this is listed and selected; otherwise, the "default" reason the dialog launches with is listed and selected. items have a more stable position as the list now always follows an order of (optional unique default shared reason, list of pre-defined reasons, optional unique shared existing reason, optional do-not-alter existing reason, custom reason), and items are marked in-place if they are interesting (issue #1653)
* fixed 'do not verify https' network jobs for clients with a CA bundle set in their envs

### duplicates

* in a terminology change that matters in other places, the duplicate filter, for the current file index, no longer says 'A' or 'B': but now 'File One/File Two'
* the comparison scores list in the mid-right duplicates hover window now says the total score difference as an actual number. let's see if the IRL scores are helpful as we move into making these rules more user-customisable

### default downloaders

* the e621 site has 'contributor' tags now, to distinguish VA talent or model makers from the primary artist. I was going to fold this into the normal default e621 parser as just another 'creator' tag, but the examples I found were pretty spammy so I'm not sure it is so useful, at least out of the box for normal users. if you are super interested in this, you might like to check out the new 'e621 file page parser with contributor tags' under `network->downloader components->manage url class links` for the `e621 file page` url class. the tags all seem to have `_(va)` kind of thing after them, so they wouldn't _confuse_ our existing creator tags, but it does seem like a lot of incidental spam and maybe it muddies things and should indeed be its own namespace in hydrus or just be ignored, idk, let me know what you think

### style

* thanks to a user, the e621 stylesheet gets some tweaks and better darkmode colours. check the new 'e621_redux' QSS. there's some some interesting new transparency tech on taglists

### client api

* fixed an issue with the `/manage_file_relationships/set_file_relationships` call and the 'set B as better' duplicate action (seen at times in other areas of the client, very rarely, as "set as worse" or "this is a worse duplicate") with `do_default_content_merge`--it was doing nothing, since there is no default for this action. now it fetches the normal 'set A as better' default options (also making sure to apply them the correct way around ha ha)
* client api version is now 77

### boring code cleanup

* across the duplicates system, I've reworked a tangle of references to 'first' and 'second' or '1' and '2' to a unified 'A' and 'B' for our pair processing. in code and duplicates action settings, the A is the first file in the pair being actioned and B is the second. in a few places where we have yet determined AB, I now specifically use 1/2. it is arbitrary, but at least it is now clear
* refactored the 'edit duplicate content merge options' panel to its own file and converted it to a non-scrolling widget so I can embed it in panels easier. it can also take SetValue calls after init and will reconfigure itself for different duplicate action types
* did some more Qt Enum updates since my linter found a bunch more: `QPainter.RenderHint`, `QPainter.CompositionMode`, `QPalette.ColorRole`, `QColor.NameFormat`, `QFont.Weight`, `QFont.StyleHint`, `QFont.StyleStrategy`, `QImage.Format`, `QTextCursor.MoveOperation`, `QColorSpace.NamedColorSpace`, `QTextOption.WrapMode`

* boring layout cleanup
* I did some Qt research and fixed a jank expanding layout technique I use in ~90 different places. a bunch of panels should eat up extra pixels a little more reliably, with fewer cases of the invididual widgets all experiencing cosmological redshift or mysterious magical growing lower buffer space if the dialog grows
* also fixed a bunch of bad sizer flags and stretch stuff used on my text&widget gridsizer that I use in ~190 places
* fixed some crazy flags and layout used inside my text&widget gridsizer
* fixed up some crazy layout in manage siblings
* fixed some crazy popup toaster layout
* fixed crazy layout in the login credentials edit panel
* fixed some crazy layout in the shortcut action editing UI
* fixed some crazy layout in the new duplicate pairs search context panel. it now expands to fill available space properly
* fixed several options pages that didn't know what to do with extra space
* the system:hash panel list now expands vertically
* reworked the view options dialog under the `options->media playback` file list into one clean and lined-up gridbox

### duplicates auto-resolution

* finished the 'action' tab, which governs the duplicate type to apply to the pair, whether to delete A or B, and any custom duplicate content merge options
* gave the rule dialog workflow a slight pass, particularly making the 'comparator' step define 'A' and 'B' rather than 'better' and 'worse'. my head was too into setting better/worse duplicates, which made things things awkward for same quality, alternates, or false positive actions. similarly, the 'action' step is now orienting towards position-specific 'A is better' verbs rather than 'yeah I guess set the better as better bro'. also, as before, as soon as this panel was finished, I immediately disabled it for the first test, ha ha
* the one-file comparator can now do 'either A or B has property x' tests
* added some safety code to the rule dialog
* work still to do is: the master database search and caching code, the preview panel, which will load up some example pairs and show them in a nice way (⊙ _ ⊙ ), tying all the objects finally together and saving them to db, and then the daemon that'll work rules on demand and in the background. I feel ok about most of it, but the db stuff may be a nightmare, and the preview code, which will need thumbnails and media viewer tech from a dialog to be worth something, will definitely be one. it'll be great to finally have 'thumbs anywhere' tech though, so lfg

## [Version 604](https://github.com/hydrusnetwork/hydrus/releases/tag/v604)

### misc

* fixed an odd and fairly recent bug where if you had an mpv window loaded in the preview panel--but it was paused--and then you changed pages back and forth, the mpv would not re-initialise itself with the previously paused media (nor really any media) unless you did some weird stuff where you clicked on another media and then changed pages again
* system:filetype now supports exclusion (i.e. `system:filetype is not video`). also, the search system now allows multiple system:filetype predicates--it figures out the correct intersection (previously it just pseudorandomly selected one of them). the system predicate text parser can handle the new 'is not' operator, and I added a unit test to make sure it sticks
* if you paste hashes with hash_type prefixes (e.g. `md5:775858135a6006db32f8ef0e5fa3102c`) into 'system:hash', it now auto-strips the prefix and sets the choice for you
* the new 'fix missing file archived times' dialog pre-job now counts up and says the number of missing timestamps of each type it discovers. this thing seems to run at 100,000s of rows per second, so it turns out no worries
* export folders should run a little bit faster now, especially to disks with higher latency (HDD or NAS, rather than a local SSD)
* export folders now only do their sidecar exports if the respective file was actually copied this run (previously it looks like they were updating to the latest data on every run, aieeeeee!)
* I've reworked the routine that draws the hover window into the background of the media viewer to more natively emulate out its layout and margin/spacer/etc.. sizes. the notes position still has some trouble, especially with difficult unicode, but it is better and now has justified text that properly expands to fill all the available space. this is now generally pixel perfect on my dev machine. while I am confident _some_ of it will survive janked QSS styles, some may not, so let me know what you see
* the tags list in the background is now also pixel-perfect-positioned with its hover!
* fixed the 'incdec' rating widget looking fuzzy in some places
* the Edit Tag Filter Panel text inputs (and their paste buttons) are now add-only. previously, it would silently do add/remove logic on each item depending on whether it was already in the list, which is not helpful now we have big lists here. so, you can paste a big list of a hundred things and now it won't remove any stuff that was already in there
* added `show file trash times/reason in top hover summary` checkboxes to `options->media viewer`, which expands the recent top hover summary stuff (issue #1652)
* rejiggered some layout in the duplicates filter page sidebar panel. the search is its own box now, as is the options

### sidecars

* the import folder system now moves all possible sidecars when you have it set to 'move the source file'. it was previously still on the old system of just supporting a single 'filename.txt' sidecar format--now it does anything you have set up, live
* the import folder UI has a couple new tooltips saying 'hey bro, delete and move actions will delete/move sidecars too, so if you have one sidecar for multiple files, make sure not to set the action to delete or move, or the next file will not have a sidecar to see'
* hooked up/improved the edit sidecar panel test UI: the string processor button on the main sidecar 'metadata router' panel now loads up example strings from your actual importers and file paths; the string processor button on the edit single sidecar importer panel now loads up example strings from your actual file paths; the process that loads up expected result strings for the multi-column test panel is more tolerant to failure; the process that provides example test data to the sidecar importer panel is more tolerant to failure; and the importer panel's test no longer spams JSON garbage into the test context, what was I thinking. I also just cleaned some of this code

### downloaders and network

* thanks to a user, the e621 login script is fixed! if you have had errors with this recently, then the update _should_ just reset any error state and allow it to try again immediately, but if not, check `network->logins->manage logins` and make sure the `active` is set and hit `scrub invalidity/delays` if you need to (issue #1655)
* updated the simple-tag shimmie file page parser to not grab 'popular tags' when those appear
* I am removing the old deviant art file page parsers from the defaults. we removed the search a while ago, but there was limited drag and drop support until seemingly just recently. it looks like the whole site got a revamp. I had a very quick look at their new format, and while it may be possible to write a new parser, I will leave this to the user-run repo to handle if they wish. I understand the whole site is mostly wrapped up in OAuth stuff now, so I think imgbrd-grabber is probably a much better solution here going forward
* the 'review bandwidth' panel gets a pass: its multi-column list ctrl is now wrapped in a nicer panel that has live buttons for edit/delete; the 'edit defailt rules' button now lists the 'global' rules; there's a little help label; and the 'search distance' column now shows your all-time total bandwidth use if you have 'show all' set. the individual network context bandwidth review panel (the one with the bar chart) also now shows your all-time usage. let's see what our all-time globals are lol
* brushed up the 'getting started with downloaders/subscriptions' help a little bit
* also expanded the 'bandwidth' section of this help and added a couple screenshots

### old mpv dll

* I am rolling back the Windows build's recent mpv update, back to the 2023-08 mpv dll. the 2024-10 dll caused stutter and slowdown with several users in the wider test, particularly Windows 10 guys. we'll revisit the topic in a future update round and see if we can select a better test candidate
* for those source users who are still on the new dll (myself included), if your client does run into an APNG or webm/mkv that trips 100% CPU (it is some bananas silent logspam outputting too fast to process), this is now recognised after a couple seconds in the hydrus error handling and the file should unload itself with the "Sorry, this media appears to have a serious problem!" error dump-out

### boring technical stuff

* the archived-file delete-lock now plays with normal trash maintenance better. the 'do we have any trash files to delete?' method now works more flexibly and it can find stuff to delete even if the oldest 256 items are locked (previously it couldn't!)
* on db update, everyone is going to get a file maintenance job queued up to check their images are all in the similar files system as desired. a recent bug caused some files not to re-register with the similar files system if they were re-imports. this job isn't super heavy on CPU or anything, so no worries, it'll just do its thing in the background and maybe fix up some holes
* under `file->shortcuts`, the custom shortcuts list now forces unique names on adds and edits
* the 'network report mode' in the `help->debug` menu now spams the Request and Response headers of each job. I also clarified, made error-safe, and added newlines to some of the other popups here to make things clearer when URLs are being transformed and so on
* the `setup_desktop.sh` script now wraps the Exec line value in quotes, so this should now work if your hydrus install folder includes whitespace

### boring code cleanup

* harmonised my various daemons more into the parent `ManagerWithMainLoop` class, which now takes responsibility for the mainloop status tracking and pre-loop startup wait. the way these guys now do their pre-work wait is a little smarter and will react to early program shutdown and so on more cleanly and in the same reliable way
* moved more old multi-column list calls to the newer methods that do cleaner post-edit select, scroll, and sort. this includes some stuff in parsing UI and manage services, so hopefully these lists will be just nicer to work with
* made the newer multi-column list code even simpler when just adding one item
* fixed up some more static superclass calls to `super()` in the autocomplete code
* merged `CanvasWithDetails` and `CanvasWithHovers` so I'd be able to interrogate the hovers when figuring out the details layout gubbins
* moved the 'open the media viewer from the preview panel' action from my old pubsub to a nicer Qt signal
* fixed some crazy sizing in my 'select stuff from a list' quick dialog

### duplicates auto-resolution

* updated the Metadata Conditional objects to work on full file search contexts instead of single predicates
* added inbox and archive support to the Metadata Conditional system
* wrote edit UI for my 'pair selector/comparator' objects
* refactored and decoupled my autocomplete dropdown classes in a couple little ways and wrote a new stripped-down autocomplete dropdown for the metadata conditional edit UI
* wrote that first 'Edit Metadata Conditional' panel
* the first version of the 'comparison' tab of the new duplicates auto-resolution UI is thus complete, and with that, I immediately disabled it like the 'search' tab, hahaha
