---
title: Changelog
---

# changelog

!!! note
    This is the new changelog, only the most recent builds. For all versions, see the [old changelog](old_changelog.html).

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

## [Version 603](https://github.com/hydrusnetwork/hydrus/releases/tag/v603)

### misc

* fixed a typo that caused the 'sort files by' menu to (ironically) sort by crazy means
* fixed a bug with the time delta widget where the ms would not set to 0 when it initialised with a value that has no milliseconds component but the minimum allowed value had a milliseconds component
* the 'force metadata refetch' thumbnail submenu now shows actions for just the focused file, and in the media viewer it now shows these actions for the current file (previously this submenu was accidentally a stub in the media viewer since there is no concept of a 'multi-file selection' up there)
* the 'review bandwidth usage' panel now initialises its widgets immediately after it opens, not half a second later
* added some safety code to ensure file re-imports (and probably some other weird file import situations) integrate correctly into the similar files system
* added some EXPERIMENTAL options just for me to `options->speed and memory`

### archived file delete lock

* I have had a think about the delete lock in hydrus. I have never liked this system because it interacts with some complicated file service logic and inserts awkward logical workflow exceptions. furthermore, my initial implementation has not played well with multiple local file services. it was also imperfect, since certain signals to 'delete from all local services' or some odd variants of 'delete from trash' could skip the lock, and it disallowed removal of a file from one local file service even when the file was in others. several users have asked for various exceptions, either on an ad-hoc basis of for duplicate filtering. I played around with trying to fix and implement some of this stuff this week and realised I was digging an even worse hole for myself. I have decided to KISS and scale back what the lock does down to the simple emergency case of not wanting to lose nice things. **therefore: the archive-delete lock, henceforth, will only test for deleting files from the trash, i.e. a physical delete**
* the option UI is updated to say this, and I cleaned up and updated a bunch of hellish hacky code all around here
* the normal manual delete files dialog now filters the 'delete physically' and 'delete physically/no record' options according to the delete-lock, no moaning or popups
* this is obviously a workflow switch, and I apologise for the inconvenience. I know the guys who care about this do care about it. I should not have tried to make it complicated in the first place. let me know what works and what doesn't, but I will insist on keeping this whole thing KISS going forward. if you use the trash for storage, please consider making a new local file service and putting your unusual 'maybe I'll delete it' files there

### trash deletion rules

* while I was poking around the archived file delete lock stuff above, I saw some hacky delete logic. in several semi-automatic systems I saw code that would say 'send the file to trash, unless it is already in the trash, in which case "upgrade" to physically delete it'. I am making the formal choice to no longer do this, and this code is now amended to say just 'send the file to trash if it isn't already there. specifically--
* the duplicates filter page will no longer allow you to set a search domain in 'trash' or 'all local files' or 'all deleted files' (or, for advanced users, 'repository updates' lol). if it is somehow given a trashed file to process and receives a duplicate action that includes a file delete (like 'this is better, and delete the other'), it no longer tries to physically delete it; it just leaves it in the trash
* the Client API `/manage_file_relationships/set_file_relationships` call is the same; when you say to `delete_a/b`, it'll now ensure the file goes to the trash and that's it
* the archive/delete filter has long not allowed trashed files, but it too now no longer has any special logic for trashed files that it happens to encounter (e.g. the file is trashed by other means after the filter is created); it will now never provide a 'delete from hard disk' option in the final commit dialog. the top 'delete from' item in the commit choice, which is usually the current location context, is also filtered and selected more carefully for users who use multi-location search domains
* the manual export and export folders now explicitly, when set to delete files, now send to trash; they never delete from the trash
* I expect I've missed some clever situation, but typically, now, files are going to be physically deleted only if the `options->files and trash` settings kick in or you the user force it manually, and of course the new archived-file delete-lock prohibits this final step no matter the source

### media viewer

* fixed a bug where the top-right hover window was, when the mouse is over it and the media changes from one with no URLs to one with URLs, not be able to immediately figure out how tall the URLs list should be and was giving you a height-truncated window
* I also, after some head banging and dark art, seem to have finally and properly fixed the annoying adjust-flicker that can happen to top-right hovers with urls or note hovers where a moment after showing it may grow three pixels taller etc... the top-right and center-right hovers now appear to size perfectly every single time; at least on Windows, I cannot break them even if I try. to keep things clean, I have removed some old hacks we built up over the years, but perhaps some of these are still relevent, so let me know how things appear on different OSes
* I improved the (re)layout after you hide/show a note with middle/right-click. it _should_ recalculate its new size immediately
* the notes that are drawn in the background of the media viewer are now always as wide as the hover window that pops up over them. I improved the padding calculations, so they are more closely aligned with the hover, but it isn't perfect yet--however I think I will be able to make it so in future
* fixed a variety of issues with the media viewer volume button and its slider flyout. it could stay open on media change and in some cases open up if the mouse was over where the flyout should be on a media change, or flickering into just slightly the wrong overlapping location if the mouse comes in at the wrong angle. there's still a couple weird ways you can break it (e.g. sending a 'move media' keyboard shortcut while the mouse is over the slider), but I'll leave that for another day
* fixed an issue with the media viewer's top hover window disappearing while your mouse was over the volume slider
* reduced some change-media flicker with the seek bar in the media viewer

### misc cleanup

* I replaced a bunch of `isVisible` with `not isHidden` in Qt. I was using the former for some widget and panel hide/show situations, but they are not quite the same: `isVisible` tests up the ancestor heirarchy; `isHidden` tests only the given widget's visibility bool
* reworded the 'blacklist' explanation a bit in 'getting started with downloaders' and added a screenshot
* updated the Linux running from source help to talk about `libgthread`, the lack of which may stop Qt6 from booting
* I cleaned up the `/manage_file_relationships/set_relationships` Client API call a little, including fixing a slightly incorrect object type that was missed in a recent rewrite of the duplicates content pipeline. I am not sure if this was causing any bugs, but it is better now
* brushed up some of the labels/tooltips in the `options->file viewing statistics` page (issue #1644)
* stopped the logging of a 'custom' `REQUESTS_CA_BUNDLE` with the new `options->connection` debug checkbox if it is what we would have set anyway (this was occuring if you went `file->restart`, since the new instance shares the same process/env)
* fixed some unit tests for the new duplicate merge delete rules
* did some misc linting

### fixed up tag filter UI

* everything is in layout boxes now, some collapsible
* fixed up some layout flags so things are aligned or expand better, and the global namespaces list shouldn't have a scrollbar any more

### macOS build

* updated the macOS build script to retry the hdiutil dmg-building step multiple times in the very frequent case of it, seemingly, getting lock-kekked by XProtectBehaviorService (https://github.com/actions/runner-images/issues/7522)

## [Version 602](https://github.com/hydrusnetwork/hydrus/releases/tag/v602)

### media viewer top hover file info line

* added four checkboxes to `options->media viewer` to alter what shows in the media viewer top hover window's file info summary line. you can say whether archived status is mentioned; and if it is, if there should be a timestamp; and you can say whether individual file services should be enumerated; and if so, whether they should have timestamps
* this same line is reflected in the main gui status bar when you have the new `options->thumbnails` checkbox set on--so if you missed seeing your current local file services on the status bar, it should be doable now, and in a more compact way

### archived times

* there has been a bug for some time where if you import files with 'automatically archive' set in the file import options, an 'archive time' was not being recorded! this is now fixed going forward
* for the past instances of this happening, I have written a new `database->file maintenance->fix missing file archived times` job to fill these gaps with synthetic values. it can also fill in gaps from before archive times were recorded (v474, in 2022-02)
* on the v602 update, your client will scan for this. **if you have a large database, the update may take a couple minutes this week**. if you have either problem, it will point you to the new job
* the job itself looks for both problems and gives you the choice of what to fix. for files imported since 2022-02, it assumes these were 'archive on import' files and inserts an archive time the same as the import time. for files imported before 2022-02, the synthetic values will be 20% between the import time and (any known deletion time or 2022-02), which is imperfect but I think it'll do

### system predicates

* the system tags for `duration`, `framerate`, `frames`, `width`, `height`, `notes`, `urls`, and `words` are now written `system: has/no xxxxx` rather than `system:xxxxx: has/no xxxxx`
* the `system:file properties` UI panel is now a two-column grid. 'has xxxxx' on the left, 'no xxxxx' on the right
* `system:has/no duration` added to `system:file properties` (it is also still in `system:duration`, but let's see how it goes having it in both places. I am 50% sold on the idea)
* the 'paste image!' button in the `system:similar files` edit panel now understands file paths when they are copied from something like Windows Explorer. previously it was only reading bitmaps or raw text, but when you hit ctrl+c on an actual file, it actually gets encoded as a URI, which is slightly different to raw text. should work now!
* fixed the `system:duration` predicate's string presentation around 0ms, where it would sometimes unhelpfully insert '+/- no duration' and other such weirdness
* fixed the `system:duration` edit predicate window initialising with sub-second values. previously, the ms amount on the main value or the +/- were being zeroed
* the various `NumberTest` objects across the program that have a +/- in absolute or percentage terms now test that boundary in an inclusive manner. previously it was doing `x < n < y`; now it does `x <= n <= y`, which satisfies 5 = 5 +/- 0, 6 = 4 +/- 50%, and 0 = 600 +/- 100%
* the 'has/no' system pred shortcuts now all parse in the system predicate parser. the old format will still parse too. I added unit tests to check this, and more to fill in gaps for 'framerate' and 'num frames'

### rating predicates specifically

* system:rating search predicates are now edited separately, which means that in the edit panel, each rating widget has its own 'ok' button. you edit one at a time with a clearer workflow
* the radio buttons involved here are now less confusing. no 'do not search' nonsense or 'is = NULL' to search for 'no rating'--you now just say 'has rating', 'no rating', or set the specific rating
* the inc/dec system pred box now has quick-select choices for 'has count' and 'no count'
* rating predicates have slightly simpler and nicer natural language labels. 'is like' and 'more than 2/3' rather than '= like' and '> 2/3'. 'count' instead of 'rating' for the inc/dec ratings. inc/dec rating predicates will also now swap in the new 'has count' and 'no count' too, rather than saying "> 0" explicitly
* the system predicate parser is updated to handle the new 'count' labels (but the old format will still work, so nothing should break™). new unit tests check this
* these panels now recover better from a predicate that refers to a service that no longer exists. in general, if you try to edit a bad pred (e.g. from an old session) it'll try to just ignore it and give you a popup letting you know

### deleted similar files search

* the similar files system no longer de-lists files from the search tree when they are deleted. phashes being disassociated from deleted files was not intentionally enforced before, but it was legacy policy from an old optimisation when the search tech was far more limited than today; now the file filtering tech is better, and we can handle it CPU wise, and I now intentionally want to keep them. it should be possible to search similar deleted files in future. the similar files search code can get pretty wew mode though, so I wouldn't be surprised if there are some bugs in odd 'all known files' situations
* I do not think this functionality is _too_ useful, but we might want to build a 'oh we have seen this file before and we deleted it then, so stop this import' auto-tech one day, maybe, if we combine it with multiple/better similar files hashes, so keeping deleted file data in our search trees will be the policy going forward. although I regret these perceptual hash disassociations, the good news is that pixel hashes were never removed, and this will be more useful for this objective

### misc

* renamed 'human-readable embedded metadata' to 'embedded metadata' across the program, mostly just to stop it being so wide. I hate this system predicate, and with the jpeg stuff it is now a catch-all and basically useless as a discriminator. I have plans to replace it with a flexible all-in-one system that will integrate all the 'has icc profile' stuff together and bundle in fine search for 'jpeg:interlaced' or arbitrary EXIF data row search so you can search for what you actually want rather than the blanket 'uh some metadata I guess'
* the 'move files now' dialog in `database->move media files` has a new 'run for custom time' button so you don't have to do 10/30/60/indefinite. note I also hate this whole system and want to replace it in the middle-term future with a background migration job, so fingers crossed this whole mess will be gone before long
* when you manually lock the database with the Client API, the bottom-right status bar cell now says 'db locked'. when it is reading or writing, it now also just says 'db reading/writing' rather than 'db read/write locked'
* the way the database updates the status bar with 'db reading' and stuff is now a little overhead efficient (it only updates the db cell, not the whole status bar)
* clarified the text in `options->importing`
* moved the 'default export directory' option from 'files and trash' to the new 'exporting' panel
* if an SSLCertVerificationError occurs in a connection, the exception now has some extra info explaining the potential causes of the problem (issue #1642)

### env stuff

* I added a DEBUG checkbox to `options->connection` that explicitly sets the `REQUESTS_CA_BUNDLE` environment variable to your `certifi`'s `cacert.pem` path, assuming that path exists and the env variable has not already been set. I'd like to test this a bit and see if it helps or breaks any situations, and maybe force it one day, or add some more options. also, I don't know much about `CURL_CA_BUNDLE`, but if you want me to defer to that rather than `certifi` if it is already set, or you have other thoughts, let me know what you think
* added `help->debug->data actions->show env`, which simply spams it to a popup and writes it to the log. it also splits up your various PATH vars for readability, but the list is usually giant so this is best actually read in the log rather than the popup atm. a couple other places where the env is spammed to screen also now uses this now format

### Qt enum cleanup

* fixed up more Qt5 Enums to the new Qt6 locations, including those now under `Qt.ItemDataRole`,  `Qt.ItemFlag`,  `Qt.SortOrder`, `Qt.ContextMenuPolicy`, `Qt.Key`, `Qt.KeyboardModifier`, `Qt.MouseButton`, `Qt.DropAction`, `Qt.AlignmentFlag`, `Qt.LayoutDirection`, `Qt.Orientation`,  `Qt.CursorShape`, `Qt.WidgetAttribute`, `Qt.WindowState`, `Qt.WindowType`, `Qt.GlobalColor`, `Qt.FocusReason`, `Qt.FocusPolicy`, `Qt.CheckState`, `Qt.TextElideMode`, `Qt.TextFormat`, `Qt.TextFlag`, `Qt.TextInteractionFlag`, `Qt.ShortcutContext`, `Qt.ScrollBarPolicy`, `Qt.TimerType`, `Qt.ToolButtonsTyle`, `Qt.PenStyle`, and `Qt.BrushStyle`
* and `QEvent.Type`
* and `QItemSelectionModel.SelectionFlag`

### other code cleanup

* cleaned up the recent 'make width sort before height in most places' hacks into something nicer
* deleted the old 'Edit Multiple Predicates' panel py file, which was only handling the ratings stuff. was probably an interesting idea at some point, but it was too convoluted IRL, both for users and me to work with
* decoupled some rating-to-stars and stars-to-rating rating conversion code out of the rating services object

### new macOS App

* sorry for no macOS App last week; github retired the old 'runner' that builds the App, and I missed the notifications. we are today updating from `macos-12` to `macos-13`, which appears to still work on intel machines
* `macos-14`, whose migration will presumably come in a few years, will likely require Apple Silicon (ARM), at which point I'll have to tell older mac users to run from source, but that's a problem for the future

## [Version 601](https://github.com/hydrusnetwork/hydrus/releases/tag/v601)

### this page is still importing

* when you try to close the client or a page of pages and one of the sub-pages protests with a reason like "I am still importing", you now get a yes/no dialog with an extra 'no, but show me the pages' button that will spawn a window listing buttons for every page that protested. clicking a button takes you to that page. this window is a frame, not a dialog, and will not go away on a click. if a page is susequently closed, clicking the button greys it out

### misc

* the 'archived time' pretty text string is no longer flagged as an 'uninteresting' line, which again, as intended, elevates it to the top hover window and main gui status bar if you have detailed info set to show
* `system:width` is now before `system:height` in the `system:dimensions` flesh-out panel. I also hacked this in the 'edit multiple preds' panel for existing fleshed-out predicates, but it is a whack implementation like I did for the sort stuff last week. as I've discussed with some others, the real answer here is probably a `system:resolution` that combines the two
* re-classified the 'move flag' DnD option under `options->exporting` as a BUGFIX option, and altered the tooltip
* fixed the new `Set to "all my files" when hitting "Open files in a new duplicates filter page"` `options->duplicates` checkbox, which was not saving on dialog ok
* changed the 'needs work' tab name suffix on the duplicates filter page to 'x% done'. it will max out at 99.9% and then hide, never rounding up to 100.0%
* added `Hide the "x% done" notification on preparation tab when >99% searched:` to `options->duplicates` for those who always want to see this for any outstanding work

### sidecar importers

* multiline .txt note sidecar importing is fixed. I previously added some 'clear out empty lines' parsing input cleaning, but this collapsed multiline content by accident. this content-agnostic stage of import is not where cleanup should occur!
* some explicit unit tests now test CRLF splitting and multiline note parsing from .txt files (previously it was just doing tags). multiline note sidecars have broken a couple times now, precisely because it was un-tested. it will not break for so stupid a reason again!
* fixed some stupid scrollbars appearing on the 'destination' panel of the main 'metadata migration router' (sidecar job) edit panel, and made sure the 'note name' text input can't get super thin (issue #1634)
* when a multi-column list is given multi-line content for a cell, it now says `[top line]... (+n lines)` so you know there was more (previously it just trancated to the top line). this now pops up in a couple of note parsing test panel places
* notes are now specified as notes in the main sidecar path list with expected content (they looked a bit like tags before)
* it isn't a big deal, but a thing that sorts the sidecar-imported text rows before handing them off to the exporter now only does a (namespace-aware) tag-sort if the exporter is tags, and otherwise just does a straight-up normal text sort

### some dialog validation

* the 'edit cookie' panel now strips leading and trailing whitespace from the name, value, domain, and path
* the 'edit cookie' panel will now not allow an ok if you accidentally paste a newline into any of these values
* the 'edit header' panel now strips leading and trailing whitespace from the key and value
* the 'edit header' panel will now not allow an ok if you accidentally paste a newline into either either

### boring linting cleanup

* now my IDE no longer has a cheeky multi-Qt env, its linter went nuts about old to-be-deprecated Enum references so I did more cleanup
* moved from QDialog.Accepted/Rejected to the Qt6-only DialogCode Enum reference. there were about 400 of these I think
* and `QFileDialog.AcceptMode`, `QFileDialog.FileMode`, and `QFileDialog.Option`
* and `QLineEdit.EchoMode`
* and `QAbstractItemView.SelectionMode`, `QAbstractItemView.SelectionBehavior`, and `QAbstractItemView.EditTrigger`
* and `QSlider.TickPosition`
* and `QFrame.Shadow` and `QFrame.Shape`
* and `QSizePolicy.Policy`
* and `QToolButton.ToolButtonPopupMode`
* and `QTabWidget.TabPosition`
* and I played around with typing.cast in a few places to handle some custom panels here and there. it is ok!
* also figured out some nicer typing in my newer command-processing menu generation code, and filled in some places where the Command Processor Mixin was needed
* also fixed some bad test panel stuff in the ancient lookup script panels

### Qt when running from source

* **I no longer support Qt5!** it may run, depending on version, if you set up your own venv, but my `setup_venv` scripts no longer offer it as a choice and I will no longer fix any new non-trivial Qt5 bugs. if I didn't break it this week with all the Enum linting, then at some point I expect I will use a Qt6 technique for which there is no Qt5 equivalent and things will simply stop working
* I cleaned up the Qt choice more in the `setup_venv` scripts, reducing it down to the one choice regarding Qt6 options and removing the '(m)iddle' choice in favour of simple old/new/test, and then a new '(q) for PyQt6' that just gets the latest PyQt6, and the '(w)rite your own'
* the 'setup_venv' scripts now tell you that Python 3.13 is probably not going to work. they also say, in prep for when it will, in the '(w)rite your own' Qt version step, that Python 3.13's earliest version is 6.8.0.2. this is actually later than our current 'test' version, which is 6.7.something. I've now set up a 3.13 dev environment and did get the program booting but there seem to be problems with numpy<2.0.0. too, and then with scikit for psd-tools, which seems to have no Windows wheel, so I'll keep working here and update everything once I figure out something that will work out of the box. for now, assume python 3.13 is a no-go unless you know how to use pip. probably best to just wait six months for all the base stuff here to catch up and settle
* I removed some Qt5 gubbins from the 'running from source' document

### build stuff

* updated a deprecated term in the Windows inno setup (the installer exe) user script
* silenced a compiler warning about User-space-while-using-admin-installer in the Windows inno setup script. no good solution here, I think, but it isn't a huge deal

## [Version 600](https://github.com/hydrusnetwork/hydrus/releases/tag/v600)

### misc

* fixed a typoed type def that caused a boot error in python 3.10. this also sometimes/always broke the v599 macOS App, which I yanked. I have improved my testing situation to catch anything like this in future (ironically, I accidentally stopped booting the program in py 3.10 every Wednesday just recently when I stopped testing for Qt5) (issue #1630)
* brought back the 'show more text about one file on the status bar' functionality with the new 'show additional status bar text when a single thumbnail is selected' checkbox under `options->thumbnails`. this tech works with single-file collections now, too. **this checkbox is default off, so go hit it if you miss this!**
* the 'manage times' dialog now also shows '(3 days ago)' accompanying string variants with all the times displayed. time objects can get complicated, so let me know how this works out if you have weird times from the future or whatever
* if your similar files search progress is greater than 99%, the tab no longer says (needs work). don't worry about that tiny little bit on every file import lads, the ride never ends
* the 'open similar files in a new page' file menu now has a 'custom' entry that spawns a simple spinner to choose a different hamming distance. it starts at 10 and has step 2 (i.e. 10, 12, 14...). **related:** I understand there are sometimes small file count differences between a hamming distance of (even number) n and (odd) n+1, but it typically isn't significant. I force a hamming distance step of 2 in some places and allow a step of 1 in others. if you care about this stuff, would you be ok with me enforcing step 2 everywhere, or do you have use for odd-number hamming distance searches?
* the various core file copy/move operations used in hydrus are now wrapped in retry modes for `BlockingIOError`, which can be raised by NASes and the like that are under deep stress. these will be retried five times, with ~1-3 second delays between re-attempts, before raising the Exception as before. thanks to the user who pointed out this could even happen. let me know if anything more complicated, let's say folder mirrors/merges, can still trip the problem
* the 'analyze' database maintenance job's yes/no dialog is now a yes/yes/no dialog. the 'soft' and 'full' options are green, the cancel is red
* cleaned up how hidden or non-functional galleries are chosen in the gallery-selector. the respective entries now have ellipses, and if there is only one item to select, it still shows the 'select from list' thing rather than confusingly insta-selecting that item
* collections now sort by anything involving width and height by using its largest-num-pixels image as proxy. this isn't perfect, and it is invisible, and I suspect in particularly crazy situations the sort may change depending on the previous sort, but collections should at least do something here now rather than always counting as 'none' for their dimensions. a thought was floated to optionally sort collections by 'average' file property in places, which may be another avenue to explore here--for instance, although sum num_pixels might make some sense, sum of height doesn't
* the 'sort by dimensions' submenu now lists width first, then height. a three-part hack was needed to make this work lol

### more vacuum and db stuff

* last week the vacuum stuff went well, but I forgot to update the dialog to use the new 'do we have enough free space to do a vacuum?' check! the dialog now properly uses the new check and won't moan about you not having enough temporary space
* if you try to do a vacuum with an external program connected to the database file we want to vacuum (it tests this by looking for '-wal' or '-journal' journal sidecars), the program now abandons the vacuum attempt and tells you to disconnect and try again (or switch to WAL, if you are in TRUNCATE). one user did this by accident this week, with a pending write commit from the external program, and it caused malformation!! hydrus will now not let this happen
* if the client or server have a failed vacuum due to a file rename failing and do not fix it themselves, and the program thus next boots with a db file with the `db_path.prevacuum` filename, the program now recognises this, tells you about it, automatically recovers from the situation, and, if one exists, tells you what to do with the `db_path.vacuum` file
* the 'do we have a missing database file?' initialisation check is improved: it will now report on a mix of missing main and external files; it will now differentiate between the first connection attempt and subsequent normal reconnections (and only run 'create db' checks and so on on the first attempt); and it will recognise if a database file suddenly goes missing during program operation and trigger an immediate program halt after its popup
* the various places the database can trigger an immediate program halt are now formalised into one careful method in a special place that won't be accidentally shuffled around or called via typo
* I rejiggered the 'let's map our incoming db command to the bound method call' process and finally replaced the comp-sci-tier 80-line-tall if/else towers in the main `ClientDB` read/write methods. it is all now a much nicer dynamically initialised name-&gt;method dict. I don't suppose it really saves all that much overhead per call, but it is finally done
* the database now reports 'db committing' in the main gui status bar when it does this in its 'idle' time. previously it only reported after a big job overran the due time

### more hover windows

* I may have fixed another hover window position bug (most probably certain window managers in Linux only, where sometimes windows will defer geometry updates until they are shown), where, before being shown any other time in that media viewer, it could flash into place in the correct position for one frame despite the mouse not being over it
* simplified the hover window show/hide logic a bit more and removed an unusual hack that handled Window Managers that weren't happy about taskbarless top level hover windows appearing (because hover windows are no longer top level but just internal widgets to the normal media viewer)
* re-integrated some spammy hover window reporting text into the 'hover window report mode', and rejiggered the logic to ensure the critical show/hide calls here are not so spammy

### client api

* added a new command, `/manage_database/force_commit`, which immediately and synchronously commits the database, flushing all pending (savepointed) changes to disk
* added help for this: https://hydrusnetwork.github.io/hydrus/developer_api.html#manage_database_force_commit
* the client api version is now 76

### debugging

* added a new `help->debug->report modes->file sort report mode`, which spams the thumbnail sorts going on with all the `sort_key` results it saw. we're trying to figure out some weird namespace sort, so let's see what this generates
* file and search logs have a new advanced menu item, tucked under the 'whole log' submenu, to export the current selection to the clipboard in JSON serialised format

### boring cleanup

* fixed some more unresolved references caused by Qt enums

### new mpv and sqlite on Windows

* I am rolling in two new dlls for Windows today, for SQLite (database) and libmpv (video/audio player)
* SQLite is updated from 3.45.3 to 3.47.0
* mpv is updated from 2023-08-20 to 2024-10-20
* both dlls are mostly just bugfixes and performance improvements, but the mpv release is slightly special--in the 'future test' we ran a few weeks ago, users with unusual Windows, be that Windows Server, under-updated Windows 10, or Windows 10 on a VM, might see a grid of black bars over some webms. no one on Windows 11 or normal updated Windows 10 reported any problems. the new mpv does perform much better than the older, and I am told it fixes some gif bugs, so I do want to update, but I do so hesitantly. if many users on updated/normal Windows do run into trouble with this release, I expect to roll back again. in the meantime, I have updated the 'running from source' help to talk more about stable versions of mpv on older Windows. users who need to keep their OS under-updated are now recommended to run from source: https://hydrusnetwork.github.io/hydrus/running_from_source.html

## [Version 599](https://github.com/hydrusnetwork/hydrus/releases/tag/v599)

### misc

* some users ended up getting a crazy wide duplicates page after the recent mix-up with the new auto-resolution multi-column list's ID. on update, the list will be reset to default widths, which should fix the rest of the duplicates page. let me know if you have any more trouble! (issue #1625)
* the e621 downloader is fixed to find search results again (I updated the gallery parser to reflect their recent html changes). I understand they may be updating again soon, so let me know if anything breaks again (issue #1628)
* I cleaned the media viewer hover window show/hide and size/position code a bit more and think I reduced more layout flicker, particularly the 'do another adjustment layout right after showing' issue the notes hover often does when super tall. I _might_ have also fixed the 'ok I guess I am going to sometimes initialise as a super wide guy in the middle of the viewer and when the user moves the mouse over my ghost I will flicker for one frame before moving where I belong' issue too
* the timestamps in the media viewer top hover window and all the timestamp lines in the media right-click menu's top-row submenu now have a tooltip that has times with the reverse of your 'always show ISO times' settings. if you see '2022-11-20 14:39:52', it'll say '2 years ago' on the tooltip, and vice versa!
* when you hit "open files in a new duplicates filter page", the file domain is now set explicitly to "all my files". if you know what you are doing and need to turn this off, there's a new checkbox under `options->duplicates`
* new duplicates filter pages now also start on "all my files" rather than your default fallback file domain. "all my files" is the ideal default duplicates search context bros
* if you have an OR predicate under construction in a file search tag autocomplete (use Shift+Enter when you enter stuff), hitting Escape on an empty text input now 'rewinds' it one predicate at a time before cancelling it entirely
* animations that report they have exactly 100fps are now distrusted and their frames are counted manually. this 'count the frames manually' routine will now trigger generally in more cases and on larger files
* all files with ~100fps will be metadata-rescanned on update

### new vacuum tech

* the vacuum in the client and server now uses `VACUUM INTO` SQLite tech. rather than writing a copy of the db to your temp dir and then to the WAL and then writing that 'commit' into the original file (which it seems is actually what happens--there's no atomic filename swap at the end), we now vacuum to a fresh file beside the original, no temp dir or WAL gubbins needed, and do a filename swap afterwards. this appears to work significantly faster than the old method, with the only caveat that there is a very brief dangerzone where neither file is named what we need, so if the hard drive disconnects or similar in that 2ms window, hydrus cannot automatically recover itself
* all operations err on the side of failsafe, and I have added copious error handling code to navigate all the possible problems. if anything does go wrong, the user will be presented with a record of what happened, and in the case where hydrus could not fix itself, how they can fix it
* the various 'do we have enough space to vacuum?' and 'how long will it take?' tests are adapted to the new rules. it doesn't use the temp dir any more, so if you have been struggling to find system drive space for client.mappings.db, this is no longer a problem
* when the job is complete, the log message, which previously just said the time taken, now records the size change and the bytes per second, and this message is also now thrown into a popup. on my dev machine SSD, I have seen 170MB/s on database files that are in memory and ~30MB/s on a 4GB file not in memory. I guess we now asymptote to about 10MB/s on a superhuge file. I am interested in what users see in their different situations
* If you are on an HDD and have a big db, you still have no hope, its over
* thanks to the user who suggested this option

### duplicates auto-resolution

* _the duplicates auto-resolution system is moving forward. still lots to do, but I'm still feeling good about it all_
* fleshed out the objects more--most stuff is now serialisable and has typedefs, getter/setters, and summary generation methods
* connected most of the decision pipeline together, and we are basically ready to process our initial jpeg/png pixel pairs
* did a hair more UI
* my taglists now handle setEnabled calls properly, so the stub UI in the duplicates auto-resolution panel is now properly un-editable

### boring cleanup

* overhauled the way medias produce the various nice info strings on the right-click menu top-row submenu (and some other places). rather than a tangle of tuples, there's a couple simple classes being passed around that can do tooltip overrides and stuff. I also cleaned up the code around here generally
* the main gui window status bar info when you only have one file selected is now much simpler. I previously piped the 'interesting' file info lines to it, but it too often ended up a spammy huge long line--not a good summary!
* rewrote the 'always show iso time' solution from the old BaseMethod-to-Method replace trick to a simpler and saner global bool, as I recently did with some PIL/ICC settings
* import folders now 'action' their original files immediately after import is done. previously they would do it in batches of ten, and if the import folder were interrupted by something like program shutdown, they'd have to wait for the next run to be cleared. I'm not totally sure, but I also think import folders set to 'ignore, not try again' on a large number of files may run a bit faster now
* clarified the additional ways to import downloaders in the Lain import dialog. Lain's paste button now also accepts URI-aware file paths (i.e. if you select some files in your file explorer and tell your OS to 'copy') as the clipboard source
* converted some duplicates processing code, and, relatedly, some delete-lock reporting stuff, from the being-overhauled `MediaSingleton` to `MediaResult`. this allowed me to clean up some wew code in duplicates auto-resolution, the duplicates filter, test code, and the Client API
* updated the running from source help to talk about mpv/libmpv on Linux
* fixed some bad panel/dialog calls into nicer Qt signals
* added some typedefs to clear out about a hundred more PyUnresolvedReferences that PyCharm found. mostly custom widget calls
