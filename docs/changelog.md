---
title: Changelog
---

# changelog

!!! note
    This is the new changelog, only the most recent builds. For all versions, see the [old changelog](old_changelog.html).

## [Version 503](https://github.com/hydrusnetwork/hydrus/releases/tag/v503)

### misc
* fixed show/hiding the main gui splitters after a regression in v502. also, keyboard focus after these events should now be less jank
* thanks to a user, the Deviant Art parser we rolled back to recently now gets video support. I also added artist tag parsing like the api parser used to do
* if you use the internal client database backup system, it now says in the menu when it was last run. this menu doesn't update often, so I put a bit of buffer in where it says 'did one recently'. let me know if the numbers here are ever confusing
* fixed a bug where the database menu was not immediately updating the first time you set a backup location
* if an apng has sub-millisecond frame durations (seems to be jitter-apngs that were created oddly), these are now each rounded up to 1ms. any apngs that previously appeared to have 0 duration now have borked-tiny but valid duration and will now import ok
* the client now catches 529 error responses from servers (service is overloaded) and treats them like a 429/509 bandwidth problem, waiting for a bit before retrying. more work may be needed here
* the new popup toaster should restore from minimised better
* fixed a subtle bug where trashing and untrashing a file when searching the special 'all my files' domain would temporarily sort that file at the front/end of sorting by 'import time'
* added 'dateutil present' to _help->about_ and reordered all the entries for readability
* brushed up the network job response-bytes-size counting logic a little more
* cleaned up the EVT_ICONIZE event processing wx/Qt patch

### running from source is now easy on Windows
* as I expect to drop Qt5 support in the builds next week, we need an easy way for Windows 7 and other older-OS users to run from source. I am by no means an expert at this, but I have written some easy-setup scripts that can get you running the client in Windows from nothing in a few minutes with no python experience
* the help is updated to reflect this, with more pointers to 'running from source', and that page now has a new guide that takes you through it all in simple steps
* there's a client-user.bat you can edit to add your own launch parameters, and a setup_help.bat to build the help too
* all the requirements.txts across the program have had a full pass. all are now similarly formatted for easy future editing. it is now simple to select whether you want Qt5 or Qt6, and seeing the various differences between the documents is now obvious
* the .gitignore has been updated to not stomp over your venv, mpv/ffmpeg/sqlite, or client-user.bat
* feedback on how this works and how to make it better would be appreciated, and once we are happy with the workflow, I will invite Linux and macOS users to generate equivalent .sh and .command scripts so we are multiplatform-easy

### build stuff
* _this is all wizard nonsense, so you can ignore it. I am mostly just noting it here for my records. tl;dr: I fixed more boot problems, now and in the future_
* just when I was getting on top of the latest boot problems, we had another one last week, caused by yet another external library that updated unusually, this time just a day after the normal release. it struck some users who run from source (such as AUR), and the macOS hotfix I put out on saturday. it turns out PySide6 6.4.0 is not yet supported by qtpy. since these big libraries' bleeding edge versions are common problems, I have updated all the requirements.txts across the program to set specific versions for qtpy, PySide2/PySide6, opencv-python-headless, requests, python-mpv, and setuptools (issue #1254)
* updated all the requirements.txts with 'python-dateutil', which has spotty default support and whose absence broke some/all of the macOS and Docker deployments last week
* added failsafe code in case python-dateutil is not available
* pylzma is no longer in the main requirements.txt. it doesn't have a wheel (and hence needs compiler tech to pip install), and it is only useful for some weird flash files. UPDATE: with the blessed assistance of stackexchange, I rewrote the 'decompress lzma-compressed flash file' routine to re-munge the flash header into a proper lzma header and use the python default 'lzma' library, so 'pylzma' is no longer needed and removed from all requirements.txts
* updated most of the actions in the build script to use updated node16 versions. node12 just started getting deprecation warnings. there is more work to do
* replaced the node12 pip installer action with a manual command on the reworked requirements.txts
* replaced most of the build script's uses of 'set-output', which just started getting deprecation warnings. there is more work to do

## [Version 502](https://github.com/hydrusnetwork/hydrus/releases/tag/v502)

### autocomplete dropdown
* the floating version of the autocomplete dropdown gets the same backend treatment the media hovers and the popup toaster recently received--it is no longer its own window, but now a normal widget floating inside its parent. it should look pretty much the same, but a variety of bugs are eliminated. clients with many search pages open now only have one top level window, rather than potentially hundreds of hidden ones
* if you have turned off floating a/c windows because of graphical bugs, please try turning them back on today. the checkbox is under _options->search_.
* as an additional consequence, I have decided to no longer allow 'floating' autocomplete windows in dialogs. I never liked how this worked or looked, overlapping the apply/cancel buttons, and it is not technically possible to make this work with the new tech, so they are always embedded in dialogs now. the related checkbox in _options->search_ is gone as a result
* if you ok or cancel on the 'OR' buttons, focus is now preserved back to the dropdown
* a bunch of weird interwindow-focus-juggling and 'what happens if the user's window manager allows them to close a floating a/c dropdown'-style code is cleared out. with simpler logic, some flicker jank is simply eliminated
* if you move the window around, any displaying floating a/c dropdowns now glide along with them; previously it updated at 10fps
* the way the client swaps a new thumbnail grid in when results are loaded or dismissed is faster and more atomic. there is less focus-cludge, and as a result the autocomplete is better at retaining focus and staying displayed as changes to the search state occur
* the way scroll events are caught is also improved, so the floating dropdown should fix its position on scroll more smoothly and capably

### date system predicates
* _this affects system:import time; :modified time; and :last viewed_
* updated the system:time UI for time delta so you are choosing 'before', 'since', and '+/- 15% of'
* updated the system:time UI for calendar date so you are choosing 'before', 'since', 'the day of', and '+/- a month of' rather than the ugly and awkward '<' stuff
* updated the calendar calculations with calendar time-based system predicates, so '~=' operator now does plus or minus one month to the same calendar day, no matter how many days were in that month (previously it did +/- 30 days)
* the system predicate parser now reassigns the '=' in a given 'system:time_type = time_delta' to '~='

### misc
* 'sort files by import time' now sorts files correctly even when two files were imported in the same second. thanks to the user who thought of the solution here!
* the 'recent' system predicates you see listed in the 'flesh out system pred' dialogs now have a 'X' button that lets you remove them from the recent/favourites
* fixed the crash that I disabled some code for last week and reactivated the code. the collect-by dropdown is back to refreshing itself whenever you change the settings in _options->sort/collect_. furthermore, this guy now spams less behind the scenes, only reinitialising if there are actual changes to the sort/collect settings
* brushed up some network content-range checking logic. this data is tracked better, and now any time a given 206 range response has insufficient data for what its header said, this is noted in the log. it doesn't raise an error, and the network job will still try to resume from the truncated point, but let's see how widespread this is. if a server delivers _more_ data than specified, this now does raise an error
* fixed a tiny bit of logic in how the server calculates changes in sibling and parent petition counts. I am not sure if I fixed the miscount the janitors have seen
* if a janitor asks for a petition and the current petition count for that type is miscounted, leading to a 404, the server now quickly recalculates that number for the next request
* updated the system predicate parser to replace all underscores with whitespace, so it can accept system predicates that use_underscores_instead_of_whilespace. I don't _think_ this messes up any of the parsing except in an odd case where a file service might have an underscore'd name, but we'll cross that bridge if and when we get to it
* added information about 'PRAGMA quick_check;' to 'help my db is broke.txt'
* patched a unit test that would rarely fail because of random data (issue #1217)

### client api
* /get_files/search_files:
* fixed the recent bug where an empty tag input with 'search all' permission would raise an error. entering no search predicates now returns an empty list in all cases, no matter your permissions (issue #1250)
* entering invalid tags now raises a 400 error
* improved the tag permissions check. only non-wildcard tags are now tested against the filter
* updated my unit tests to catch these cases
* /add_tags/search_tags:
* a unit test now explicitly tests that empty autocomplete input results in no tags
* the Client API now responds with Access-Control-Max-Age=86400 on OPTIONS checks, which should reduce some CORS pre-flight spam
* client api version is now 34

### misc cleanup
* cleaned up the signalling code in the 'recent system predicate' buttons
* shuffled some page widget and layout code to make the embedded a/c dropdown work
* deleted a bunch of a/c event handling and forced layout and other garbage code
* worked on some linter warnings

## [Version 501](https://github.com/hydrusnetwork/hydrus/releases/tag/v501)

### misc
* the Linux build gets the same 'cannot boot' setuptools version hotfix as last week's Windows build. sorry if you could not boot v500 on Linux! macOS never got the problem, I think because it uses pyoxidizer instead of pyinstaller
* fixed the error/crash when clients running with PyQt6 (rather than the default Qt6, PySide6) tried to open file or directory selection dialogs. there was a slight method name discrepancy between the two libraries in Qt6 that we had missed, and it was sufficiently core that it was causing errors and best, crashes at worst
* fixed a common crash caused after several options-saving events such as pausing/resuming subscriptions, repositories, import/export folders. thank you very much to the users who reported this, I was finally able to reproduce it an hour before the release was due. the collect control was causing the crash--its ability to update itself without a client restart is disabled for now
* unfortunately, it seems Deviant Art have locked off the API we were using to get nice data, so I am reverting the DA downloader this week to the old html parser, which nonetheless still sems to work well. I expect we'll have to revisit this when we rediscover bad nsfw support or similar--let me know how things go, and you might like to hit your DA subs and 'retry ignored'
* fixed a bad bug where manage rating dialogs that were launched on multiple files with disagreeing numerical ratings (where it shows the stars in dark grey), if okayed on that 'mixed' rating, rather than leaving them untouched, were resetting all those files back to the minimum allowed star value. I do not know when this bug came in, it is unusual, but I did do some rating state work a few weeks ago, so I am hoping it was then. I regret this and the inconvenience it has caused
* if you manually navigate while the media viewer slideshow is running, the slideshow timer now resets (e.g. if you go 'back' on an image 7 seconds into a 10 second slideshow, it will show the previous image for 10 seconds, not 3, before moving on again)
* fixed a type bug in PyQt hydrus when you tried to seek an mpv video when no file was loaded (usually happens when a seek event arrives late)
* when you drop a hydrus serialised png of assorted objects onto a multi-column list, the little error where it says 'this list does not take objects of type x' now only shows once! previously, if your png was a list of objects, it could make a separate type error for each in turn. it should now all be merged properly
* this import function also now presents a summary of how many objects were successfully imported
* updated all ui-level ipfs multihash fetching across the program. this is now a little less laggy and uses no extra db in most cases
* misc code and linter warning cleanup
* .
* tag right-click:
* the 'edit x' entry in the tag right-click menu is now moved to the 'search' submenu with the other search-changing 'exclude'/'remove' etc.. actions
* the 'edit x' entry no longer appears when you only select invertible, non-editable predicates
* if you right-click on a -negated tag, the 'search' menu's action label now says 'require samus aran' instead of the awkward 'exclude -samus aran'. it will also say the neutral 'invert selection' if things get complicated

### notes logic improvements
* if you set notes to append on conflict and the existing note already contains the new note, now no changes will be made (repeatedly parsing the same conflcting note now won't append it multiple times)
* if you set notes to rename on conflict and the note already exists on another name, now no changes will be made (i.e. repeatedly parsing the same conflicting note won't create (1), (2), (3)... rename dupes)

### client api
* /add_tags/search_tags gets a new parameter, 'tag_display_type', which lets you either keep searching the raw 'storage' tags (as you see in edit contexts like the 'manage tags' dialog), or the prettier sibling-processed 'display' tags (as you see in read contexts like a normal file search page)
* /get_files/file_metadata now returns 'ipfs_multihashes' structure, which gives ipfs service key(s) and multihashes
* if you run /get_files/search_files with no search predicates, or with only tags that do not parse correctly so you end up with no tags, the search now returns nothing, rather than system:everything. I will likely make this call raise errors on bad tags in future
* the client api help is updated to talk about these
* there's also unit tests for them
* client api version is now 33

### popup messages
* the background workings of the popup toaster are rewritten. it looks the same, but instead of technically being its own window, it is now embedded into the main gui as a raised widget. this should clear up a whole heap of jank this window has caused over the years. for instance, in some OSes/Window Managers, when a new subscription popup appeared, the main window would activate and steal focus. this annoying thing should, fingers crossed, no longer happen
* I have significantly rewritten the layout routine of the popup toaster. beyond a general iteration of code cleanup, popup messages should size their width more sensibly, expand to available space, and retract better after needing to grow wide
* unfortunately, some layout jank does remain, mostly in popup messages that change height significantly, like error tracebacks. they can sometimes take two frames to resize correctly, which can look flickery. I am still doing something 'bad' here, in Qt terms, and have to hack part of the layout update routine. let me know what else breaks for you, and I will revisit this in future
* the 'BUGFIX: Hide the popup toaster when the main gui is minimised/loses focus' checkboxes under _options->popups_ are retired. since the toaster is now embedded into the main gui just like any search page, these issues no longer apply. I am leaving the two 'freeze the popup toaster' checkboxes in place, just so we can play around with some virtual desktop issues I know some users are having, but they may soon go too
* the popup toaster components are updated to use Qt signals rather than borked object callables
* as a side thing, the popup toaster can no longer grow taller than the main window size

## [Version 500](https://github.com/hydrusnetwork/hydrus/releases/tag/v500)

### crashes
* I messed the mpv update up in v499. my golden rule is never to put out bleeding-edge library updates, but without thinking I gave everyone a dll from late august. it turns out this thing was pretty crashy, and many users were getting other unusual behaviour as well. it seems like people on very new versions of Windows were mostly ok, but a little instability, whereas some older-Windows users were unable to start the client or could boot but couldn't load mpv at all. these latter cases were plagued with other problems. thanks to user help, we discovered it was the newer mpv dll causing all the problems, and an older one, from early May, seems to be fine
* so, I am rolling back the mpv in the windows releases. the 'v3' 2022-08-29 I bundled in 499 was causing several users serious problems, possibly because of the advanced 'v3' chipset instructions or related advanced compiler tech. for the Qt6 release, we are going back to 2022-05-01, which several users report as stable, and for the Qt5 we are rolling back to the 498 version, 2021-02-28, which is back to mpv-1.dll. Since Qt5 users are increasingly going to be Win 7, we'll go super safe. THEREFORE, Qt5 extract users will want to perform a clean install this week: https://hydrusnetwork.github.io/hydrus/getting_started_installing.html#clean_installs
* (you can alternately just delete the now-surplus mpv-2.dll in your install directory, but a full clean install is good to do from time to time, so may as well)
* updated the sqlite dll in the windows release to 2022-05, and the exe in the db directory to 2022-09
* rewrote how some internal MPV events are signalled to Qt. they now have their own clean custom event types rather than piggy-backing on some bad old hydrus pubsub code
* I either fixed a rare boot crash related to the popup messaging system, maybe exclusively on macOS, or I improved it and we'll get a richer error now

### tag sibling search
* if you search explicitly for a tag that has a better sibling (one way this can happen is when loading up an old favourite search), the client will now auto-convert that tag to the ideal in the search code and give you results for the siblinged tag
* this started off as a predicted five minute thing and spilled out into a multi-hour saga of me realising some tag sibling search code was A) wrong in edge cases and B) slow in edge cases. I have subtly reshaped how core file-tag search works in the client so that it consults each tag service in turn based on its siblings and its mappings, rather than mixing them together. this does not matter for 99.98% of cases, but if you have some weird overlapping siblings across different services, you should now get the correct results. also, some optimisations are more effective, so any instance of searching for tags on small tag services on 'all known tags' is now a bit quicker
* big brain: please note the logic here is complex, and I have not yet updated autocomplete counting to handle this situation. if you type 'cat' and get 'cat (3)' from the three 'cat' tags on 'my tags', but 'cat' is siblinged to 'species:feline' on a big service like the PTR, it will still say (3), rather than (403) or whatever from the auto-corrected PTR results. I have a plan to fix this in a future cleanup round

### tag subtags and namespace wildcards
* searching for 'samus aran' no longer delivers files that have 'character:samus aran'. the subtag->namespace logic no longer applies. this was a fun idea from the very start of the program, but it was never all that useful as default behaviour and added several headaches, now eliminated. if you wish to perform this search going forward, please enter '*:samus aran', which is now an acceptable wildcard input
* tag lookup is unaffected. typing 'samus aran' will still provide 'character:samus aran' as a tag to choose from
* a heap of rinky-dink counting logic went along with this, such as providing tag search results like ('character:samus aran (100)', 'samus aran (100-105)'), where it tried to predict how many results would come with the unnamespaced search. this no longer exists, and a decent bit of CPU is now saved in any large tag search
* wildcard searching works on similar rules now, so if you enter 'sa*s ar', you will see 'character:samus aran' as a result in the tag list, but searching for it will not give results with 'character:samus aran'. again, enter '*:sa*s ar*' to search for all namespaces (which is now provided as a quick suggestion any time you enter an unnamespaced wildcard), or enter 'character:sa*s ar*' explicitly
* 'system:tag as number' also now follows similar rules, so if you leave the namespace field blank, it will search unnamespaced numbers. it now supports namespace wildcards, so you can enter '*' to get the old behaviour. the placeholder text on the namespace input now states this
* 'system:number of tags' now uses the same UI as 'system:tag as number', where you enter '*' as the namespace to mean all namespaces, rather than checking a box

### misc
* all tag, namespace, and wildcard search predicates are now properly editable from the active search box. shift+double-click or select from the right-click menu, and you now get a simple text input alongside any system predicate panels. previously, this would only offer you a button to invert the tag to -tag and _vice versa_. now, you can add or remove the '-' and '*' characters yourself info to freely convert between tags, namespace:anything, and wildcard search predicates (issue #1235)
* thanks to a user, you can now add '{#}' to an export filename pattern to get the '#' column in your filename (useful if you want to export files in the order they are currently in on the page)
* furthermore, if you delete items from the manual file export window, the '#' column now recalculates itself to stay contiguous and in order (previously, it left gaps)
* fixed a bug when deleting siblings on a local tags service. sorry for the trouble!
* on manage siblings, when you remove, add, or replace a pair on a local tags service, you will now get a simple 'note' reason informing you more on what is going on. the 'REPLACEMENT:' thing recently added to tag repositories should now work for you too
* when a downloader or similar adds files to a page, and you have at least one existing file selected, the status bar now updates correctly
* fixed a critical issue that was affecting some users with damaged similar file search trees. when starting similar file search tree rebalancing maintenence, their client would go into an infinite loop and spool the cyclic branch into an ever-growing journal file in their temp directory until their system drive briefly ran out of space. sorry for the trouble, and thank you for the excellent reports that helped to figure this out (issue #1239)
* the similar files search tree rebalance maintenance now detects more sorts of damaged trees and handles them gracefully, and the full tree regeneration clears out any damaged maintenance information too
* fixed another problem with the tree branch maintenance system when the root was accidentally queued for branch rebalance
* when you right-click->copy a wildcard search tag, it now copies the actual wildcard text, not the display text with (wildcard search) over the top
* I added ',' to the list of non-decodable characters in the hacky URL Class encoding/decoding routine. sites that use an encoded comma (%_2C) for regular path components or query parameters should now work
* a user has fixed a regex parsing problem in the predicate parser for system:hash
* OR search predicates now sort their sub-predicates on construction/editing, meaning the label is always of set order, and they can now compare with and hence reliably nullify each other
* the manage logins dialog now boots a little taller
* the main gui tab bar may look a bit nicer/more appropriate in macOS
* updated the help text on gui pages where it talks about overflowing rows of tabs, which auto-scroll even worse in Qt6, hooray

### client api
* the  client api now handles request disconnects better. the hydrus server code benefits from the same engine improvements
* the 'twisted.internet.defer.CancelledError' logspam is cleaned up!
* if a client disconnects before a client api autocomplete tag search or a file search is complete, that database job is now cancelled quickly just like when you type new characters in the client UI or stop a slow search
* if you are a client api dev, please let me know how this works out IRL. I'm not 100% sure what a 'disconnect' means in this context, but if you want to develope autocomplete quick lookup as the user types, and you have a way clientside to cancel/kill an ongoing request before it is complete, please give it a go and let me know if this all works. cancelled requests don't make a log record right now, but you should see the client's db lock free up instantly. at the very least, I have the proper infrastructure for this now, so I can add more/better 'cancel' hooks as we need them

### uninteresting code cleanup
* refactored the file note mapping db code to a new module
* refactored the file service pathing db code (this does directory structures and multihashes for ipfs) to a new module
* refactored some tag display, tag filtering, and tag autocomplete calls down to appropriate db modules
* refactored and extended some tag sibling database methods and names to clarify whether they were working with ids or strings

## [Version 499](https://github.com/hydrusnetwork/hydrus/releases/tag/v499)

### mpv
* updated the mpv version for Windows. this is more complicated than it sounds and has been fraught with difficulty at times, so I do not try it often, but the situation seems to be much better now. today we are updating about twelve months. I may be imagining it, but things seem a bit smoother. a variety of weird file support should be better--an old transparent apng that I know crashed older mpv no longer causes a crash--and there's some acceleration now for very new CPU chipsets. I've also insisted on precise seeking (rather than keyframe seeking, which some users may have defaulted to). mpv-1.dll is now mpv-2.dll
* I don't have an easy Linux testbed any more, so I would be interested in a Linux 'running from source' user trying out a similar update and letting me know how it goes. try getting the latest libmpv1 and then update python-mpv to 1.0.1 on pip. your 'mpv api version' in _help->about_ should now be 2.0. this new python-mpv seems to have several compatibility improvements, which is what has plagued us before here
* mpv on macOS is still a frustrating question mark, but if this works on Linux, it may open another door. who knows, maybe the new version doesn't crash instantly on load

### search change for potential duplicates
* this is subtle and complicated, so if you are a casual user of duplicates, don't worry about it. duplicates page = better now
* for those who are more invested in dupes, I have altered the main potential duplicate search query. when the filter prepares some potential dupes to compare, or you load up some random thumbs in the page, or simply when the duplicates processing page presents counts, this all now only tests kings. previously, it could compare any member of a duplicate group to any other, and it would nominate kings as group representatives, but this lead to some odd situations where if you said 'must be pixel dupes', you could get two low quality pixel dupes offering their better king(s) up for actual comparison, giving you a comparison that was not a pixel dupe. same for the general searching of potentials, where if you search for 'bad quality', any bad quality file you set as a dupe but didn't delete could get matched (including in 'both match' mode), and offer a 'nicer' king as tribute that didn't have the tag. now, it only searches kings. kings match searches, and it is those kings that must match pixel dupe rules. this also means that kings will always be available on the current file domain, and no fallback king-nomination-from-filtered-members routine is needed any more
* the knock-on effect here is minimal, but in general all database work in the duplicate filter should be a little faster, and some of your numbers may be a few counts smaller, typically after discounting weird edge case split-up duplicate groups that aren't real/common enough to really worry about. if you use a waterfall of multiple local file services to process your files, you might see significantly smaller counts due to kings not always being in the same file domain as their bad members, so you may want to try 'all my files' or just see how it goes--might be far less confusing, now you are only given unambiguous kings. anyway, in general, I think no big differences here for most users except better precision in searching!
* but let me know how you get on IRL!

### misc
* thank's to a user's hard work, the default twitter downloader gets some upgrades this week: you can now download from twitter lists, a twitter user's likes, and twitter collections (which are curated lists of tweets). the downloaders still get a lot of 'ignored' results for text-only tweets, and you still have to be logged in to get nsfw, but this adds some neat tools to the toolbox
* thanks to a user, the Client API now reports brief caching information and should boost Hydrus Companion performance (issue #605)
* the simple shortcut list in the edit shortcut action dialog now no longer shows any duplicates (such as 'close media viewer' in the dupes window)
* added a new default reason for tag petitions, 'clearing mass-pasted junk'. 'not applicable' is now 'not applicable/incorrect'
* in the petition processing page, the content boxes now specifically say ADD or DELETE to reinforce what you are doing and to differentiate the two boxes when you have a pixel petition
* in the petition processing page, the content boxes now grow and shrink in height, up to a max of 20 rows, depending on how much stuff is in them. I _think_ I have pixel perfect heights here, so let me know if yours are wrong!
* the 'service info' rows in review services are now presented in nicer order
* updated the header/title formatting across the help documentation. when you search for a page title, it should now show up in results (e.g. you type 'running from source', you get that nicely at the top, not a confusing sub-header of that article). the section links are also all now capitalised
* misc refactoring

### bunch of fixes
* fixed a weird and possible crash-inducing scrolling bug in the tag list some users had in Qt6
* fixed a typo error in file lookup scripts from when I added multi-line support to the parsing system (issue #1221)
* fixed some bad labels in 'speed and memory' that talked about 'MB' when the widget allowed setting different units. also, I updated the 'video buffer' option on that page to a full 'bytes value' widget too (issue #1223)
* the 'bytes value' widget, where you can set '100 MB' and similar, now gives the 'unit' dropdown a little more minimum width. it was getting a little thin on some styles and not showing the full text in the dropdown menu (issue #1222)
* fixed a bug in similar-shape-search-tree-rebalancing maintenance in the rare case that the queue of branches in need of regeneration become out of sync with the main tree (issue #1219)
* fixed a bug in archive/delete filter where clicks that were making actions would start borked drag-and-drop panning states if you dragged before releasing the click. it would cause warped media movement if you then clicked on hover window greyspace
* fixed the 'this was a cloudflare problem' scanner for the new 1.2.64 version of cloudscraper
* updated the popupmanager's positioning update code to use a nicer event filter and gave its position calculation code a quick pass. it might fix some popup toaster position bugs, not sure
* fixed a weird menu creation bug involving a QStandardItem appearing in the menu actions
* fixed a similar weird QStandardItem bug in the media viewer canvas code
* fixed an error that could appear on force-emptied pages that receive sort signals

## [Version 498](https://github.com/hydrusnetwork/hydrus/releases/tag/v498)

_almost all the changes this week are only important to server admins and janitors. regular users can skip updating this week_

## overview
* the server has important database and network updates this week. if your server has a lot of content, it has to count it all up, so it will take a short while to update. the petition protocol has also changed, so older clients will not be able to fetch new servers' petitions without an error. I think newer clients will be able to fetch older servers' ones, but it may be iffy
* I considered whether I should update the network protocol version number, which would (politely) force all users to update, but as this causes inconvenience every time I do it, and I expect to do more incremental updates here in coming weeks, and since this only affects admins and janitors, I decided to not. we are going to be in awkward flux for a little bit, so please make sure you update privileged clients and servers at roughly the same time

## server petition workflow
* the server now maintains an ongoing fast count of its various repository metadata, such as 'number of mappings' and 'number of petitions of type x'. when you fetch petition counts, no longer will it count live and max out at 1,000, it'll give you good full numbers every time, and real fast
* you can see the current numbers from the new 'service info' button on review services, which only appears in advanced mode. any user with an account key can see these numbers, which include number of petitions in the queue. I can make this more private if you like, but for now I think it is good if advanced users can see them all
* in the petition processing page, sibling and parent petitions will now include both delete and add rows if the account and reason are the same. I'm aiming to get better 'full' coverage of a replace petition, so you can see and approve/deny both the add and the remove parts in one go. for fetching, these combined petitions count as 'delete' petitions, and won't appear in the 'add' petition queue
* when users encounter an automatic conflict resolution in the manage siblings dialog, those auto-petitioned pairs are now assigned the same reason as the original conflicting pended pairs. they _should_ show up together in the new petition processing UI
* as part of this, sibling and parent petitions are no longer filtered by namespace. you will see everything with that same account and reason in one go. let's try it out, and if it is too much, I will add filters clientside or something. since we are now starting to see add and remove together, we'll want to at least have the option to see everything

## boring server stuff
* the petition object is updated to handle multiple actions per petition, and the clientside petition UI is updated appropriately
* the server tracks 'actionable' petition counts as separate to the number of raw petition rows. some of this was happening before, but the logic is improved, including clever counting of the new petitions that include both add and delete rows
* for when my count-update logic inevitably fails, there is now a 'regen service info' entry in the 'administrate services' menu for all repositories. numbers generated will be printed to server log
* some unusual repo upload logic is cleaned up, e.g. if a user with 'create permission' uploads a sibling or parent, any pending rows for that content will now be properly cleared)
* fixed a stupid swap logical bug where janitors who could only moderate siblings (and not parents) were only being given parent numbers and vice versa
* all server services now respond to /busy check. it requires no authentication and just returns 1 or 0 depending on the current lock state
* fixed a bug where tag siblings or parents that were denied would still make a new definition record for the child/bad tag
* with all the fine number changes, fleshed out the server unit tests with more examples of submitting and altering content and then checking for numbers afterwards. now checked are: file add, file admin delete, mapping add, mapping admin delete, mapping petition, mapping petition approve+deny, parent add, parent admin delete, parent pend, parent pend approve+deny, parent petition, parent petition approve+deny
* significant refactoring of the tail end of server content update pipeline. more things now go through logic-harmonised update methods that ensure count is reliable
* did some misc server db and constant enum code cleanup

## misc
* to match the new change in the server, in the client, tag and rating services now store their 'num_files' service info count as the new 'num_file_hashes'. existing numbers will be converted over during update
* fixed a probably ten year old bug where 'num pending/petitioned files' had the same enum as 'num pending/petitioned mappings'. never noticed, since no service has done both those things
* if the upload pending process fails due to an unusual permission error or similar, the pending menu should now recover and update itself (previously it stayed greyed out)

## [Version 497](https://github.com/hydrusnetwork/hydrus/releases/tag/v497)

### misc
* I bulked out the 'star' rating shape a bit more, since the new pentragram, while it looked better than my old 'by-eye' star, was a bit thin. if you prefer the pentagram, this is now selectable as a new shape type under manage services
* the Windows installer is now Qt6 exclusively. there are no special update instructions, it should all just work™
* the 'manage tag siblings/parents' dialogs now have explicit delete buttons, which should make mass-deletes a little easier to do. some of the background code is cleaned up too, and the 'add' button is moved up to the main button row
* you can now hide all sibling and/or parent text-suffix 'decorators' in the manage tags and autocomplete dropdown taglists, with four new checkboxes under _options->tags_. the right-click menus of these lists let you temporarily show/hide too, just like 'hide/show parent rows'
* when you change the namespace sort in the options, the existing collect-by dropdowns now update instantly (previously, existing pages needed a client restart to see any changes)
* I updated how the media viewer 'note' hover window lays out and does its 'how tall should I be?' estimate. it fits better, being exactly just tall enough in more cases, but it still seems to have trouble with multiple notes that include wrapping text
* added a link to the new flatpak release (easy Linux running-from-source setup) that a user made to the install help
* fixed an issue with the new 'default' file import options when you right-click a watcher/gallery download--the 'show files' menu now correctly adapts to you having a default file import options
* if you are set to elide page tab names, then all pages will tooltip their names on mouseover
* new clients now start with (ctrl+page up/down) as 'move page selection left/right'

### client api
* the Client API routine that fetches file statuses for a given URL no longer double-checks 'already in db' results against your actual file system. this check is more appropriate to an actual working import process, so it now defaults off in the Client API
* if you want to do this check because you are searching for missing files, you can turn it back on with the new 'doublecheck_file_system' parameter.
* the client api help has been updated to reference this
* the client api's Server header is now "client api/32 (497)". NOT "client api/17". it was stating the hydrus network version erroneously. it now states client api version and software version. if you are able to parse this header, it makes '/api_version' request superfluous
* the client api version is now 32

### multiline parsing
* the parser now supports limited multiline parsing. the main changes are hardcoded: the formulae beneath note content parsers and those that do subsidiary page parser splitting no longer remove newlines when they parse. all the parsing UI and the test panels and so on are now aware of this and set flags in all the right places, and parsed notes are now washed through the new trimming/cleaning method, and everything _seems_ to basically work. the main remaining problems is the complicated string processing UI has mixed single/multi-line testing support. some looks great, most gets coerced to single-line just for the previewed test results
* as an example, the default hentai foundry downloader now grabs the artist description as a multi-line note
* the parsing sub-system that extracts cohesive strings from complex html blocks now inserts newlines at 'p' and 'br' tags
* trying to parse clean multiline notes still caused several formatting issues this week, so I have updated the automatic note-washing routine to standardise hydrus notes in several new ways that I hope will not be too disruptive to manually written notes:
* the note washing routine now coerces all newline characters to 'backslash-n', regardless of platform
* the note washing routine now trims each line, so no leading or trailing whitespace anywhere. I am open to changing this in future, maybe for handwritten notes where you really want an indent somewhere, but parsing from complex nested html tags is making a heap of weird extra whitespace, for which this is a clean solution
* the note washing routine now trims newline gaps that are greater than two-newlines. you can split paragraphs by one empty line, but no more
* there may be other issues figuring out cleanly formatted strings from nested html tags--so give it a go and let me know what you think. maybe p and br blocks should always make two newlines, so we have separated paragraphs, maybe I need to parse more blocks, like h1 and friends. any specific example html blocks would also be helpful

### cleanup
* refactored ClientGUIParsing to its own 'parsing' module and split everything into four less tangled files
* cleaned up a bunch of taglist text presentation code, mostly simplicity and clarity in prep for future updates
* updated the checker options button to use a Qt signal instead of a callable

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
