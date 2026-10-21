---
title: Changelog
---

# changelog

!!! note
    This is the new changelog, only the most recent builds. For all versions, see the [old changelog](old_changelog.html).

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

## [Version 687](https://github.com/hydrusnetwork/hydrus/releases/tag/v687)

### misc

* the popup toaster is now very anti-taking-focus. if you navigating the thumbs via keyboard while popups bounce around doing their thing, particularly subs, they should now be less likely to steal focus from what you were doing. even clicking buttons shouldn't do it. this is mostly an experiment, so let me know how it works out
* updated `mkdocs-material` from `6.7.1` to `6.7.7` due to a dependbot alert about an XSS issue with the search box

### simpler menubar

* in an effort to make the main gui's top-level menubar menus thinner and easier to mouse through, a machete has been applied. long labels are reworked or banished, 'manage x...' is now generally just 'x...', and some 'x and y' are now 'x/y', and some big weird things are pushed down to a submenu. Some tooltips are altered to help. I apologise for the jolt to muscle memory here, but I've been meaning to do this for ages and I'm trying to pack a bunch into one bigger frustration than continually reworking it in dribs and drabs
* one thing I'm not totally happy with is the 'pending' menu. putting the count of pending stuff at the top of the submenu keeps it tucked out of the way, but if you find you are clicking that and not 'commit' two weeks from now, I'll need to re-do it

### menubar boring details

* under the 'file' menu, I clipped the labels a bit
* the 'undo' menu is fine
* under the 'pages' menu, I pushed the page count and weight measure to a 'weight' flyout submenu, the 'sidebar and preview panels' submenu is now just 'sidebar', and the 'new x page' labels are clipped
* under the 'database' menu, all the long backup gubbins is put into a 'backup' submenu, 'move media files' is renamed to 'locations', and 'file viewing statistics' is renamed to 'clear'
* under the 'network' menu, 'downloader components' are folded into 'downloaders' and the 'logins' legacy label is pushed to the submenu. also, an ancient ancient and hacky tumblr GDPR click-through patch is removed
* under the 'services' menu, we just have 'review', 'edit', and 'administrate'. this is another "manage" to "edit" change, which is nomenclature borne from a stupid old technical difference that doesn't matter to the end user and which I am slowly changing. also this weird 'import update files' job is pushed to an 'advanced' submenu
* under the 'tags' menu, everything is cut to the bone and 'manage where siblings and parents apply' is pushed down to an 'advanced' submenu
* under the 'pending' menu, the count is now pushed to the flyout submenu, making the top menu just your service names. should make it both thinner and less bouncy as things are pending/uploading in the background
* under the 'help' menu, I clipped a couple things
* I think I updated all the help docs to point to the new labels, but let me know if you see something I missed

### executable manager

* the executable manager is now real. check it out under the 'external programs' options page. it supports 'open single file' and 'open url' pipelines to start, and like other hydrus things the objects can be exported and shared between users in a bunch of ways
* the 'default programs' options page uses the new executable manager. your existing launch paths will be converted to the new system. feel free to rename them. if you are feeling brave, poke around and make your own callable
* when you do 'open externally' on a file or URL, it all works on the new system. this includes stuff like hyperlinks. the call is cleaner, more secure, and has nicer failure reporting
* added a 'show PATH' button to the exe manager's process call edit panel. it throws up the PATH as hydrus sees it with a bit of blurb

### exe manager boring stuff

* on init or update, an exe manager is created and populated with defaults or a migration of your existing string launch paths
* the exe manager now tracks dirty/clean status and is plugged into the normal manager save checker
* the existing 'open url/file' options are converted to the new calls, and the new exe manager is populated with executables for the old launch paths
* all the 'default programs' UI is converted to the new 'select which exe' system. it provides live choices from the current the 'external programs' page
* hooked up some extra safety code to make sure the exe manager provides the fallback default OS call when there is nothing else set, and to remove defunct items on dialog ok and such
* process calls in the executable manager system now clean their parameters on init, deserialisation, or simple dialog editing. newlines are removed, leading or trailing whitespace is stripped, and multiple whitespace is collapsed to single
* wrote some migration code for the legacy string templates to the new executable callable objects
* cleaned up the whole 'open url/file' pipeline of all sorts of old cruft, and updated it to work on media results rather than media singles (part of a long-time cleanup job). similarly deleted a bunch of old code
* wrote more safety code to inject and fall back to the 'open with default OS call' for 'open file/url' calls that have no options set up for whatever reason
* fixed some edge case harmless errors when hitting 'open file/url' in the media viewer in the moment it is closing
* all the open file/url calls now catch the new exceptions and report in nice info popup dialogs when things go wrong
* fixed some tucked away 'open this url' menu entries (stuff like the regex help link) that were using the wrong 'launch url' call in last week's multi-browser-launch-options refactor
* refactored some 'populate exe manager with defaults' code to share the same call
* refactored the executable manager action calls out of the manager to their own file and moved some 'open url with default browser' calls in there too
* refactored the 'open help docs here' to better tapdance around the new 'open url' pipeline
* wrote up a slender gui-executable-actions wrapper module for all 'open url/file' commands so if there is error, there is always an UI context upon which to throw up an information error message dialog. there is better testing and error reporting when trying to open a non-local file externally

## [Version 686](https://github.com/hydrusnetwork/hydrus/releases/tag/v686)

### misc

* the 'give child windows a tool flag' test setting went well, and I am switching everyone to use this mode as default now. if you have trouble with 'review services' or similar, please hit `options->gui` and hit the new `BUGFIX: Set child windows as non-tool flagged`
* the `force that hitting Enter/Return on radio button lists triggers a dialog ok` checkbox is now set to true by default, and everyone is switched over this week. same as before, the test went well. if you prefer it the other way, please hit up `options->gui` and switch it back
* the content summary strings in the duplicate auto-resolution thumbnail pair lists have some formatting improvements: the 'add mappings a, add mappings b, add mappings c...' stuff is now 'add mappings: a, b, c'; different service lines are now newline-separated; and the thumbnail rows are a little taller by minimum to typically fit this text in better
* decided to finally remove the long-time disabled 'potential pairs' line from Mr Bones. the newer duplicates page with its fragmentary and cancellable search handles all this better, and since the potential pairs space exists only for local files rather than Mr Bones's ability to look into deleted files, it is best just not to bring this number back here. He now only handles total dupes and alternates made
* improved the maths behind the alternates counts in Mr Bones. it also works a bit faster. the 'x alternate groups' number is now filtered correctly according to the current search context, and some interesting edge cases are consciously handled so a search for 'system:file relationships - number of alternates = 0' produces the correct 0/0 results. there's a couple of ways of looking at these numbers and I've taken the most conservative to occasionally undercount but never overcount

### new thumbnail grid rendering tech

* we've been testing out a new, cleverer way of rendering the thumbnail grid. it works and looks basically exactly like the old system for now but will support new layouts and resizable thumbs in future. we are happy with the test, so I am switching everyone to use it today. ideally, you do not notice any differences. if you suddenly do have trouble with your thumbs, hit up `options->thumbnails`, switch off the new rendering mode, restart the client, and let me know
* I made the 'which file to select when you press an arrow/page key' work more humanly in the new grid; now, if your current focus file is removed and you then press a movement key, the 'ghost selection' media is now selected, re-initialising your position. previously, it would navigate _from_ the ghost to a neighbour, which always felt weird. also, the ghost is now the _next_ non-removed file (used to be previous), unless the removees stretch to the end of the list, in which case the _previous_ is chosen. this feels a bit more natural and catches some odd cases since previously it worked on selections rather than removees
* this is more controversial and may mess with muscle memory, but I have also made it so a shift-select does not move the "navigate from here" ghost. this ghost now sticks to the current focus. if this drives you crazy, there is a new checkbox under `options->thumbnails` to switch back to moving the ghost to the last file you hit to alter the shift-selection. if you understand what this means, you are a true patrician and I personally recommend mapping ctrl and shift to your mouse. also, I may start rendering the ghost as a dotted line or something just like you'd get in a file explorer or something
* as part of this, I fixed an issue with the new tech where it could have trouble finding a new media to select after certain removal of non-selected items, for instance after zero-selection archive/delete filtering or a background file delete
* fixed the enable-reactivity of the ctrl- and shift-selection checkboxes under `options->thumbnails`
* I fixed up some various other focus items and 'these were selected in the current shift-select' variables that were not properly cleansing themselves after a media remove event
* the new graphics view thumbgrid test can now process an interactive 'entry dialog' content update shortcut
* fixed a trace error with the interactive 'entry dialog' command when nothing is selected in the thumbgrid

### new ways to open files and urls externally

* in prep for the exe manager taking over, the options for 'default programs' that handles web browser calls and 'open externally' for different filetypes are updated
* the web browser setting is now a list of calls, so you can set up alternate web browsers or profiles if you like. if you have multiple, the top one is selected for quick/default url-openings and in the media 'urls' menu you now get multiple submenus to choose which one you want
* the file 'open externally' has two changes--now you can set the default 'open externally' call for "all files" and "all images/videos/whatever" as well as for individual filetypes. I hope this makes it simpler to just switch from x image viewer to y for everything while still allowing something special for avif or whatever. your existing options are going to be eaten up and converted to the simplest suitable umbrella solution
* and, secondly, each of those entries now support multiple calls, so you can say 'open images with x program or y' and then, like with the urls, the top item is the default for quick actions but otherwise your media 'open externally' menu is going to dynamically expand into multiple options if you set that up
* the string program cals are all going to be converted to the exe manager in a week or two. feel free to add new paths now, or wait for that, at which point you'll be selecting from a dropdown here

### potential pair discovery scheduling logic

* I cleaned up a bunch of edge-case logic around how files are set to be searched for potential pairs. an interesting bug (#2086) revealed that previously-deleted files were not being scheduled for re-entry into the potential pairs search system, and when I looked into it, this revealed some more messy logic. I've cleaned it up and now blank square files are 'find similar files' searchable
* first off, when a previously deleted file is re-imported, it is now scheduled for potential-pair discovery as expected
* further, the determinant of whether a file should be searched for potentiar-pair discovery is now strictly that it has non-blank phashes. files with blank or near-blank phashes are now entered into the search tree, but they are not scheduled for potential pair discovery (blank files produce many false positive pairs, so we do not want them)
* the 'ensure file is in similar files search system' job is now careful to only consider that question, and it no longer triggers any pixel or phash regens
* files that are discovered to have no useful phashes are deregistered from the system correctly. previously, some pixel hash and re-import events would trigger an accidental listing or not trigger a proper delisting; now the logic is KISS
* all files that currently have no phashes (blank files and some weird non-renderable things) are scheduled for a phash regen on update, which will make 'system:similar to' work for them
* identical blank files (we had an example of two pure white comic pages with the same resolution, once) that share the same pixel hash will no longer naturally appear in the potential pair search
* pasting a blank or near-blank image into the 'system:similar files' panel also now produces phashes in the box. it is now possible to search for blank and blank-like images with this system. if you are interested, the blank phash is `8000000000000000`. paste it in once the maintenance has caught up here and brace yourself for a rollercoaster ride
* the names and descriptions of the 'check for membership in...' and 'regenerate perceptual hashes' file maintenance jobs are clarified

### boring stuff

* fixed an issue where non-advanced users saw the 'external programs (TESTING)' page in the options lol
* cleaned up the application processing code's responses and formalised that a shortcut will be caught if it matches an entry, not only if it matches and the command produced an arbitrary result. if you say 'copy bitmap' when no file is selected, the shortcut is swallowed there; it won't go "ok nothing happened" and see if anything higher matches your shortcut
* a user reported an interesting statistical bug in the duplicate pairs fragmentary search; where it does a confidence interval check, in one case it had more searched items than the entire search space. it seems this was a race condition. I have wrapped all the code in proper locking, added nicer guards before the math, and tidied up some redundant code along the way
* misc linting and typing, blah

## [Version 685](https://github.com/hydrusnetwork/hydrus/releases/tag/v685)

### misc

* the 3-second tooltip micro-notification experiment on the 'edit notes' 'copy urls' button worked out, so I wrote the code up properly and made it so all 20+ copy icon buttons across the program say something like 'Copied!' or 'Copied x ratings!' on click, all 23+ paste icon buttons similarly do 'Pasted!' or 'Pasted x texts!'. I'll slowly integrate this into other buttons that do a thing that isn't immediately obvious
* the media viewer right-click menu's 'volume' submenu now has a volume slider rather than the list of checkboxes
* fixed a recent regression that was stopping the media viewer from finding and activating an already-existing manage tags window when you did 'manage tags' from the media viewer--it was instead creating multiple windows, which is not desired (#2085)
* if you have very large or very small thumbnails, the thumbnail pair lists in auto-resolution now size better, setting saner min/max sizes for the thumbnail item cells and scaling thumbs to that size when a min/max limit applies (#2079)
* added a 'show anything with specific bandwidth rules' checkbox to 'review bandwidth usage'. if you import a downloader and it comes with bandwidth rules, you can now find those without having to actually use the site
* added a 'can you run the client headless? (not yet)' to the FAQ page, and then added a test line to it from a user who found a possible way

### alternate software

* expanded and formalised the 'if you like hydrus, maybe you will like this software too/instead' section in the help here: https://hydrusnetwork.github.io/hydrus/getting_started_files.html#other_software
* as part of this, I am listing three hydrus-adjacent projects that are coming into public this month, same way as I list stuff in the Client API page. feel free to check them out! they are--
* IDHAN (https://github.com/KJNeko/IDHAN) - A high-performance hydrus-like media manager server with a web UI. Very sophisticated.
* Naiad (https://github.com/scoopscoop/naiad-net) - A hydrus-like media manager with its own PTR-style tag-sharing solution.
* refr (https://github.com/therandomlance/refr) - An Immich-like with a focus on managing art reference images.
* if you create your own hydrus-like or similar tech that hydrus users may like, please link me and I'll list it there!

### executable manager

* I invite advanced users to play with this again (`options->external programs`). there's a little change in the call we were playing with last week
* after talking it out with people, I realised it would be better not to have two 'local process calls' for 'one template string' vs 'command + list of params', and updated the current prototype object, which was the former, to be the latter. thus the current terminal call is updated to have an exe and a list of params with replacement strings, rather than just one template string. it calls the process directly with the params all nice and separate rather than a raw string to your shell, so no quotespam needed. although editing separate params is more of a pain than just a text box, it is neater and more secure to only do it like this, saving us several headaches, and the only blocking cost of eliminating the worse yet easier option is writing some good UI to make editing the better option easier
* I've therefore tried to make some decent edit UI. nice and simple exe and param list, and copy/paste buttons so you can just paste a raw template if you have a nice simple one
* the 'availability call' and 'which availability call' settings are gone; we now just do a `which` on the given exe. this breaks the macOS 'open "Google Chrome" blah' calls, but we'll revisit this if it ever proves a big problem
* the 'open externally' job now provides 'file hash (sha256)' and 'file id' input parameters
* some stuff is renamed from, say, 'local terminal call' to 'local process call' and so on to reflect the changes around here
* improved some labels and update signals in the ui--stuff like updating the example templates on a string processor change

### new thumbnail grid test

* advanced users are encouraged to play with this more (`options->thumbnails->New Rendering Tech Test`). I think we have it pretty much nailed down now and so I'm mostly just optimising and cleaning in prep for switching everyone over, and I'd like to see if there are any more visual bugs lurking
* a bug in the new thumbnail grid test where thumbnails would not redraw is fixed. it turned out there was some duff redraw logic when the 'fade thumbnails' option was off
* set it so the new thumbnail grid only registers with the animation timer while it has thumbs animating--as soon as there is no more work, it delists itself
* the new thumbnail grid no longer attempts to animate thumbs if it is not currently on a visible page; it just schedules them for instant draw
* a thumbnail now correctly understands it is no longer animating if its paint errors out or its fade-in time or backing pixmap are invalidated, which triggers the above delisting
* added `help->debug->report modes->graphics view thumbnail update report mode`, which spams a bunch of decisions about the new painting tech to log

### boring cleanup

* did some MainLoop Daemon refactoring, just getting over a hump to move some responsibility to the superclass
* moved to nicer ui-cleanup calls in a bunch of my async code

## [Version 684](https://github.com/hydrusnetwork/hydrus/releases/tag/v684)

### misc

* every thumb/viewer media menu now has 'show detailed embedded file metadata' in the top-row flyout; this is the same window that opens with the media viewer top hover, to which I've been adding EXIF and stuff
* there's a new shortcut command to spawn this window under the 'media' set, `open detailed embedded file metadata window`
* I finally got around to figuring out and adding a `Force that hitting Enter/Return on radio button lists triggers a dialog ok` checkbox to `options->gui`. On Windows, an Enter/Return on a radio button list triggers a dialog ok, but on other OSes, it does not. it is one of those platform policy things and Qt is being good and obeying. this casually annoyed me for years, particularly when doing advanced file delete dialogs where rather than a simple yes/no it has a couple of radio button lists, and since moving to Linux full time I finally got my finger out and figured it out. it is default off so I don't mess with anyone's muscle memory etc.., but if this was annoying you, try it out
* added `TEST: Set tool flag to child windows` to `options->gui`. this test sets a different flag and hopefully improves some window behaviour--specifically, stuff like "review services" should stay on top of the parent, not get a taskbar/alt+tab entry, but still look ok. let me know how it goes, and if no problems, I'll set everyone to it
* I gave the 'my auto-resolution rule says it has x pairs to search/resolve but it cannot clear them' issue another push. thanks to a user, we figured out an interesting orphaned pair situation. I fixed the logical hole in the maintenance code and updated the new error handling to A) indefinitely pause a rule that hits this, to stop pause/error loops, and B) run the full orphan-clearing maintenance code rather than just the re-count job
* noneable string widgets now blank their placeholder text when set to none
* test result text boxes in exe manager and parsing UI now have monospaced font

### hash-search

* system:hash gets a logical makeover. this thing has always been a bit of a mess as it tried to navigate prefixes like `sha256:abcd...`. I have made it simpler
* the edit dialog now lets you type or paste whatever, with no instant auto-correct. there are now two buttons underneath, `clean up text and guess hash type` and `clean up text and guess hash type (remove bad lines)`, which do the parsing on demand. the first button moans about any errors at all; the second removes errors, so if you want to post a mix of garbage and have hydrus filter it, go ahead
* the ok button is plugged into this tech too and, as the parsing is also improved, gives richer errors. if you hit ok and the hashes are fine but the hash type seems wrong, it now gives you a special error text
* hydrus hash parsing now recognises and removes an `0x` prefix from a hash
* hydrus hash parsing is now much better about case insensitivity. `MD5:AbCD...` is fine
* hydrus hash parsing now has an error state for hashes with a non-even number of hex characters
* hydrus hash parsing no longer attempts to hex filter an incoming line; if a hash includes a non-hex character, this now goes in a new error bucket for reporting

### notes quality of life

* added a 'when you middle-click to copy a note hover, only copy the text (not the title)' setting to `options->notes`
* added that and the 'put cursor at the end' checkboxes to the cog icon button in the edit notes panel
* added a 'link' icon button to notes that sucks up all the URLs from the current note text. it isn't perfect, but covers all normal 'http...' situations using a `https?://[^\s<>"\']+` regex
* in a new test, when you do this 'copy URLs in the note' job, it fires off a '3 URLs!' tooltip micro-notification for feedback. give it a go, let me know how it feels, and I think I'll spam this all over the place

### exe manager

* finished off the core edit UI for my exe manager, which still only advanced users can see under `options->external programs`. you can edit everything, and there's a fullly functional test panel that reports return code and stdout/stderr on failures. it isn't perfect, but I'm happy with it as a first step. I will again ask advanced users to check it out, with these instructions: look at the defaults, pick a call that you should have, and then edit it and put in a sensible file path or URL in the test panel and try it! Let me know if you have any errors and where I need to add help text!
* the defaults button now asks if you want all the default calls or just those for your platform
* many many other improvements and finishings-off here, and a touch of misc new subprocess tech

### boring exe manager stuff

* rewangled the 'windows startfile' hardcoded launch call to be a platform-agnostic 'OS launch file'
* added a 'OS launch URL' hardcoded launch call in the same way
* improved the hydrus subprocess 'this process has timed out' detection system. in doing exe manager work this week, I realised it was waiting after a kill fallback in a blocking way and only reporting the timeout after the final (indefinite) reap went through
* improved some subprocess error formatting

## [Version 683](https://github.com/hydrusnetwork/hydrus/releases/tag/v683)

### file metadata

* I am ready to roll out the new file metadata flags. on update, you will be given a yes/no dialog asking if you want to schedule a big file metadata regen on pretty much all your images. I recommend all users click yes, but if you want to handle it yourself, you can click no, no worries
* it will schedule 'has xmp', 'has iptc', 'has software-source', and new 'has human-readable' flag inspection for all your jpegs and some other image formats depending on the type
* recall you can look at the maintenance progress under `database->file maintenance->manage scheduled jobs` and tweak the file maintenance background work velocity under `options->maintenance and processing`. as a general principle, I do not recommend you try to hurry huge work; just let it do its thing
* XMP, IPTC, and software/source values are now stripped of leading/trailing whitespace
* empty XMP, IPTC, and software/source values/list-items are now skipped

### duplicates auto-resolution

* I have added two new hardcoded comparators: "A has same or better metadata flags to B" and "A has ICC Profile if B does". the auto-suggested rules now use these, and the help talks about them, so we do away with the old and awkward and ugly 'both have same x OR B doesn't' formulation. also added some unit tests for this
* the metadata comparator tests each of EXIF, XMP, IPTC, software/source, and human-readable flags
* enthusiastic users of auto-resolution may like to swap over to the new comparators once these new flags populate so they can cover more situations
* if an auto-resolution rule thinks it wants to do search or resolution work but there is no actual pair in the queue, the database now auto-triggers some maintenance to safely temp-pause the rule, regenerate the cached (and miscounted) numbers, and continue. it makes a popup if this happens
* auto-resolution rules now stop work quickly when paused during a busy work cycle
* the maintenance jobs that regen auto-resolution rules numbers and clear all potential duplicate pairs generally now trigger a proper, full reload of any list of auto-resolution rules in UI. previously, these guys needed an explicit refresh button click to catch up

### more UI features

* a user has submitted more UI improvements!
* the media viewer's 'always on top' transition should now be flickerless for Windows
* further, we now have a tentative 'always on top (while playing)' option. the always-on-top transition in Linux is still flickery, and if you have mpv up it causes a buzzy-noise crash, so I patched it to simply not happen in this situation, and if you are on Linux, the 'eye' menu in the media viewer has a 'THIS MAY BE BUGGY/CRASHY' warning
* the new treeview test has several updates: double-clicking on treeview empty tab area opens the new page picker, treeview rows now use alternating colours, some bugs are fixed, the layout signaling is less janky, some code is cleaned, menu code is simplified, and there are several new user-controllable options (row height, indentation, alternating line colours)
* extra note from hydev: if you have been playing with the treeview, hit up the new cog icon menu and look at the in-menu 'tree row dimensions' sliders and give them a spin. absolute space magic

### audio files with embedded images

* the QtMediaPlayer will now show an embedded image if an audio file has one. I pulled this off with some slightly funky tech, so let me know how it goes IRL
* the default mpv.conf now has a `audio-display=embedded-first` line (thanks to a user, for this) that shows embedded images for audio files. if you never tweaked your mpv.conf, you might like to hit up `options->media playback` and reset back to the default mpv conf there (just hit the 'browse' button and it should start you in the static/mpv-conf dir)

### misc

* added a link to https://github.com/asadtoast/aether in the Client API help; this is an Android app with a bunch of features, including archive/delete and duplicate filtering
* fixed an issue that was stopping adding potential duplicate pair relationships to files not already registered in the duplicates system. this broke hydrus video duplicate detector and similar tools. sorry for the trouble--I was too keen last week with the valid pair filtering! (issue #2076)
* the 'external programs' options page is moved to 'default programs'

### executable manager

* the work on this system continues to go well. I fleshed out my previous skeleton, so most of the spinning wheels are connectable now
* advanced users will see a new 'external programs (TESTING)' options page. this has the first UI available. edit panel isn't ready yet, but you can load the defaults and see what I'm going for
* wrote out defaults for common OS file launchers and 'open file in web browser' commands
* I added 'open multiple files externally' tech in prep for finally actually doing this from thumbnail menu
* next step is to finish the edit panel for this first local call and start a test for advanced users. I'd like to get an early version of this working pretty soon, and get 'open externally' working on it and migrated over, and then I'll add new tech and pipelines to the live system; stuff like tag suggestions

### boring stuff

* added info to the 'help my db is broke' help page regarding `.clone` crashing/halting, the `.backup` command, and a very clever trick a user discovered regarding editing the `sqlite_schema` table to skip cloning a known-malformed table
* the Docker package is updated to `Alpine 3.24` and should have improved HEIF support
* skipped 'software/source' inspection when examining importing pdfs (this was silently failing, previously, because it was trying to load them as images)

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
