---
title: Changelog
---

# changelog

!!! note
    This is the new changelog, only the most recent builds. For all versions, see the [old changelog](old_changelog.html).

## [Version 628](https://github.com/hydrusnetwork/hydrus/releases/tag/v628)

### ratings

* thanks to a user, we have another round of new ratings UI features--
* under `options->media viewer` you can now have the ratings hover window and background appear, just like in the normal media viewer! quick ratings setting from the preview!
* under the new `options->ratings`, you can now customise the size of ratings in the manage ratings dialog and the preview viewer. you can also set a different width for inc/dec ratings
* also under `options->ratings`, you can now set numerical ratings to only show the `3/5` fraction and a single star on the thumbnail view
* under the `services->manage services` panel of a 'numerical' rating service, you can now set to have the `3/5` fraction written to the left/right of the stars display
* a bunch of misc code cleanup. we are slowly tearing out some of my bad old code to make a more decoupled renderer here, and ideally to eventually figure out a proper 'what this rating will look like' preview widget alongside these options
* thanks to another user, we have a bunch of new rating svgs available by default: `architecture`, `art-palette`, `cinema-reel`, `eye`, `heart-cute`, `inspiration`, `scenery`, `smile`, and `wallpaper`. I think they look great!

### misc

* the new 'export filename' generation routine now parses any subdirs your pattern makes and forces a 64 character limit on Windows and a ~250 byte limit otherwise. you can now put `{character}\{hash}` as the pattern and it will create stable and reliable folder names. this is a hardcoded hack waiting for a richer path generation system (issue #1751)
* fixed a bug when loading an OR predicate that held a rating predicate during database initialisation (which could happen during a db update or, it seems, when loading the core options structure after the user had done some OR/ratings work that populated the 'recently used predicates' structure)
* fixed a bug when rendering any rating predicate to text during database initialisation
* since it is a clever routine and it has caused us trouble before, predicates now never fail to render themselves. if there's an error, they print it to log and return `error:cannot render this predicate`
* fixed a bug in the 'present this list of texts to the user' renderer that was causing the last line not to render when there were more than 4 items to show. this made for a completely empty output if you pasted five really short texts into 'paste queries'. it was also undercounting the 'and x others' line by one, when there were more than 24 lines of content
* the 'stop removing double slashes at the start of an URL' test went well, so all users are now flipped to working this way by default. the 'TEST' checkbox under `options->downloading` is now a 'DEBUG' one, if you need to go back to the old way
* the program no longer logs the full error when FFMPEG cannot render a PSD
* the program no longer logs the full error when Qt cannot render a PDF for a thumbnail

### potential duplicate pairs count is smoother

* the widget that edits a potential duplicate pairs search context (which you see in the duplicate filter page sidebar and the duplicates auto-resolution search panel) now has an integrated duplicate pairs count. this count calculates in an iterative/incremental way, doing a bit of counting over and over rather than one big job, just like the duplicates auto-resolution preview page, and thus opening a duplicates filter page is no longer an instant db lag. updating the search context or getting a signal of new potential pairs will quickly cancel any ongoing search and restart the count. it also pauses an ongoing count while you are not looking at it. the count also only disables the 'launch the filter' and 'show some random potential pairs' buttons until it finds at least one pair. this should all just work better!
* note that I did a bit more assumptive 'things haven't changed in the past five minutes' logic with this work, so while it should still update itself on big changes, I made it lazier on the small stuff. let me know if and when it undercounts. I also stopped it refreshing after every 'random potential pairs' action, too. the refresh button should fix any undercounting or other desync, so let's see how it does IRL

### duplicates auto-resolution

* the approve/deny actions in the review rule panel now work in chunks, which gives other jobs time to get at the database (no more freezing up), and they report '16/55' status on the button you clicked, so you can see how it is doing
* this panel also gets a 'select all' button
* I tweaked the suggested 'A and B are visual dupes' rule to queue up 128 files and broke it into two rules--one that requires `A has filesize > 1.1x B` and the other doing `A has width/height > 1.1x B`, mostly to increase confidence on the 'better' action. I didn't have time to add times to the comparator system, but that's next. I want 'A modified date earlier than B' on both rules as an extra safety guard rail for what I suggest as a default
* added a new 'archived file delete lock' exception under `options->files and trash`, for any auto-resolution action
* I've hidden the 'work hard' button. I don't really like it and it wasn't working pleasantly. maybe I'll bring it back, but if I do it'll be with some nicer UI

### boring duplicate cleanup

* the initial work that goes into setting up the new iterative potential duplicate pair fetch is now cached and shared amongst all callers, so a variety of refresh calls and duplicate filter or rule edit panel loads will now be that bit faster off the mark. this is important if you have like 700k potential pairs
* the new iterative potential duplicate pair fetch now pre-filters to any simple local file domain, so when it runs on a single local file domain with a small relative file count, it is now much much faster
* the new iterative potential duplicate pair fetch is now faster with `system:everything` searches
* the new iterative potential duplicate pair fetch tech now grabs in blocks of 4096 pairs, up from 1024. the core auto-resolution rule searcher is now 4096, too, down from 8192
* the old monolithic potential duplicate pairs counter, which now only occurs in unit tests and an API call, uses the new tech (just by iterating over the whole search space in one transaction), and is thus a good bit faster and cleaner etc.. in various situations. I was able to delete a bunch of semi-duplicated code after this!
* all duplicate pair searches that are both `system:everything` and a union of multiple local file domains now run at good speed (they were previously extremely unoptimised in many situations)

### boring cleanup

* when editing favourite regexes, the 'add' call now shows a rich regex edit box, and both add and edit calls' regex boxes are a little wider and no longer offer a recursive 'manage favourites' command from their menu lol
* moved the edit regex favourites panel to its own class
* moved the autocomplete dropdown resize code from old wx hacks to Qt Events
* moved the frame size and position saving code from old wx hacks to Qt Events and Timers and a nicer eventFilter, and reduced some save spam
* since they are no longer used anywhere, cleared out these old wx move and maximise event catching hacks
* when you enter a password through the database menu, it now asks for it a second time to confirm you typed it all ok, and if you clear it, it gives a yes/no to confirm that
* the slideshow custom period input now defaults to `15.0` so the user knows they can do sub-second input, and it now presents a graphical message if the time was unparseable
* the various 'separate' subscription choices should be better about sorting the to-be-split queries with human sort rather than just ascii
* my 'select from a list' and 'select from a checkbox list' mini-dialogs now sort their contents with richer human sort
* in the edit duplicates auto-resolution rule panel, the 'max pairs in pending queue' widget now disables more carefully based on the starting operation mode. btw I think I was crazy defining the pause state via a third operation mode choice and will most likely rework this to a separate checkbox
* updated the example response in the Client API `/manage_pages/get_page_info` documentation to include `hash_ids`
* cleaned some misc client db job-to-command mapping stuff
* bunch of little logical improvements for various text entry dialog feel, mostly making some 'edit this if you want' cancel outcomes in sub merge/separate no longer mean a cancel of the larger multi-step workflow
* `help->about` now says your numpy version
* broke `ClientGUITags`, which was ~230KB, into smaller files for Manage Tags, Manage Tag Siblings, Manage Tag Parents, Incremental Tagging, Tag Filters, Sync Maintenance EditReview, Tag Display Options, Edit Namespace Sort, and Tag Summary Generators in `hydrus.client.gui.metadata`

### text entry dialog overhaul

* migrated the ancient 'enter single line of text' dialog to my newer edit panel system. migrated all the old dialog calls over to the new class, being: sort-by namespace custom entry; password setup entry; password boot entry; debug fetch an url entry; janitor file repo file info lookup hash entry; janitor account lookup account key entry; file lookup script custom input; gui session name input; string-to-string widget add and edit key/value inputs; string-to-string-match widget add and edit key inputs; sub merge name input; select subs by name input; non-half subscription separate name input; tag filter favourite import name input and save name input; manage tags reason input; tag summary generator namespace/prefix/separator edit inputs; slideshow custom period input; some tag petition reason input; note import options whitelist add/edit name input; add domain modified timestamp domain entry; json object exporter name input; tag sibling/parent pend and petition reason entry; export downloader domain input; parser example url input; login management domain and access description entry; login script example domain and access description entry; parsing test panel url fetch input; petition files reason input; ipfs directory naming input; new page of pages naming-on-creation and naming-on-send-down option input; page renaming; registration token entry; ipfs share note input; simple downloader formulae naming input; external program launch path input; advanced file deletion reasons edit; namespace colour namespace input; namespace sort options panel editing input; tag suggestion slice weight; edit notes name input; regex favourites regex and description input
* aaaiiiieeeeeeeee

### library updates

* the 'future build' last week went without any problems, so I am folding its updates in to this build. we have--
* On All--
    - `requests` moved from `2.32.3` to `2.32.4` (security fix)
* On Linux and Windows--
    - `PyInstaller` moved from `6.7` to `6.14.1` (handles new numpy)
    - `setuptools` moved from `70.3.0` to `78.1.1` (security fix)
    - `numpy` moved from `2.2.6` to `2.3.1` (lots of improvements, py 3.11+)
* On Windows--
    - `sqlite` dll moved from `3.45.3` to `3.50.1`
* Source venvs--
    - `numpy` moved from `>=2.0.0` to `<=2.3.1`
* the pyinstaller bump is the most important, I think, and it should fix a bunch of dll load and OS API issues. there are no special install instructions, but let me know if you run into any trouble

## [Version 627](https://github.com/hydrusnetwork/hydrus/releases/tag/v627)

### misc

* windows that remember position are better about saving that position on a window move. some window managers (particularly on Linux) were not recognising the previous 'window move has ended' tech, nor non-mouse moves, so I wrote something that will work more generally. let me know if any windows start positioning crazy this week during drags!
* fixed variable framerate render timing in the native viewer for animated webp files. I messed up some logic when I first rolled this out in v620; should be working correct now (issue #1749)
* fixed an issue where import sidecars were losing their texts' order (they were being pseudorandomly re-sorted) in the outer layer of string processing where multiple sidecar texts are combined. the sidecar pipeline now preserves original sort throughout the pipeline (issue #1746)
* added a `TEST: Stop mpv before media transition` in an attempt to early-cancel laggy mpv when transitioning media when the current (looping and pre-buffering) media is near the end. may also help some situations with laggy storage, but we'll see. I think this mode might have some load bugs

### visual duplicate detection is ready

* the 'A and B are visual duplicates' system now compares spatial edge data and is better able to recognise mosaic/blur patches, minor alterations or repositions, and subtle alternates in busy areas like eye pupils. all the remaining difficult false positives I have are fixed, and the test easily catches several pairs that were previously tricky, allowing me to remove a hacky test on the colour testing side of things that was producing some false negatives
* this test is now available as a comparator in duplicates auto-resolution rules! you can choose it to be at least 'very probably', 'almost certainly', or 'near-perfect'. I default to and recommend 'almost certainly' for now. I am still interested in seeing any new false positives you encounter
* note that this tool is CPU heavy--expect about a second per pair tested! the UI seems to be holding up well with the delay, but I've added a new label to the preview panel to show when it is running slow and there are pairs still to be tested
* added a new and generally cautious 'visually similar pairs - eliminate smaller' suggested rule. it does an 'A and B are almost certainly visual duplicates' test on similar filetypes, preferring an A that is larger in size and larger or equal in resolution, and is semi-automatic. if you have been following all this, please give it a go and let me know what you think
* assuming this tech holds up, this was the last big difficult thing in my auto-resolution superjob. there is still a lot I want to do, but it'll mostly be cleaner UI, some more comparator types, a way to interact with the denied pairs log, smoother counting and pair load in more places, a way to load up a duplicate rule's pending decisions in the normal filter, richer duplicate-aware pair preview/review, that sort of thing

### cleanup/docs/boring

* added some notes to the 'migrate' and 'source' help regarding needing to rebuild your venv every time you move the install folder
* added some 'better software for x' links to 'getting started with files' to ComicRackCE, Lanaragi, and Calibre
* added a little about 'A and B are visual duplicates' to the duplicates auto-resolution help
* the 'LabHistogram' stuff that does the new 'A and B are visual duplicates' is now renamed generally to 'VisualData', and the LabHistogram stuff is rejiggered into a subclass
* fixed a small warning bug when the thumbnail pair list in the auto-resolution preview panel is updated to have a new rule while it is empty
* fixed a duplicate file system bug where it wasn't able to negotiate the correct `media id` for a file when the duplicate group had an identity definition but somehow was desynced and did not list the king as a member
* added a new 'pixel-perlfect jpegs vs pngs - except when png is smaller' alternate suggested rule that does pixel perfect jpegs and pngs but only actions when the jpeg is smaller than the png
* wrote some unit tests for 'A and B are visual duplicates'
* I think I silenced OpenCV's warning logspam. if you ever saw `[ WARN:44@43420.823] global grfmt_png.cpp:695 read_chunk chunk data is too large` kind of thing in your log, you shouldn't any more

### future build

* I am making another future build this week. This is a special build with new libraries that I would like advanced users to test out so I know they are safe to fold into the normal release.
* in the release post, I will link to this alternate build. if you are experienced and would like to help me, please check it out
* the new numpy version that caused trouble for Arch users also broke our build right afterwards, so this is an attempt to fix that while rolling in some security updates. updating PyInstaller more than a year to the same numpy fix they rolled out two weeks ago did not, I was surprised to discover, appear to break anything, so the builds may be significantly more stable and OS-compatible. as usual, I will be interested to know if anyone on Win 10 or any other older OS has trouble running this. as far as I can tell, a clean install is _not_ required
* the specific changes this week are--
* On All--
    - `requests` moved from `2.32.3` to `2.32.4` (security fix)
* On Linux and Windows--
    - `PyInstaller` moved from `6.7` to `6.14.1` (handles new numpy)
    - `setuptools` moved from `70.3.0` to `78.1.1` (security fix)
    - `numpy` moved from `2.2.6` to `2.3.1` (lots of improvements, py 3.11+)
* On Windows--
    - `sqlite` dll moved from `3.45.3` to `3.50.1`
* Source venvs--
    - `numpy` moved from `>=2.0.0` to `<=2.3.1`

## [Version 626](https://github.com/hydrusnetwork/hydrus/releases/tag/v626)

### AUR numpy problem

* there was a problem with the AUR (Arch Linux) hydrus package while I was on vacation. the python package `numpy` updated and a couple deprecated lines I had missed now threw errors. for those who auto-update to the newest of things (eg. as on AUR), this broke video view and file import. sorry for the trouble! by luck I had fixed half of this by accident a few weeks ago, but I also missed a few more lines. a user kindly figured out the fix and I was able to merge it into master early for those who could pull. rolling back numpy to `<2.3.0` was another temporary solution. the fix is now properly in this v626, so when AUR v626 rolls out, everyone should be good again. if you are an AUR guy and really want to avoid this in future, I recommend moving to your own source install, as here: https://hydrusnetwork.github.io/hydrus/running_from_source.html it takes a couple minutes to set up, but with our own venv that we control, we can fix the library versions to stuff that we know will work in perpetuity.(issue #1744)

### Paint.NET

* Paint.NET files are now importable (or at least anything since ~2006). the client pulls resolution and should be able to do thumbnail, but cannot render them fully. they count as an 'image project file'. let me know if you have any v3 .pdn files that don't work!

### default downloaders

* the derpibooru file page parser is updated to get tags again. I think I updated everything correct, but let me know if anything is parsing different to how it was before

### duplicates auto-resolution

* improved my 'A and B are visual duplicates' algorithm with a new pre-histogram gaussian filter to better tune out jpeg artifacts and a more careful later 'absolute skew pull' inspection
* many previously 'definitely visual duplicates' false positives are now detected as various states of 'not visual duplicates' or 'very probably visual duplicates'
* many previously false negatives are now correctly detected as 'definitely' or 'near-perfect' visual duplicates
* many previously true positive duplicates are now detected as higher levels of confidence of duplicate
* thank you all for submitting your false positives and false negatives. I now have one pair that still false positives as 'definitely visual duplicates', and a couple that still go 'very problably', which I would like to fix. the remaining problem to solve is file-to-file edge difference comparison, which I feel pretty good about attempting at this stage. I also feel better about finally turning this system on for the duplicates auto-resolution rules soon, with the caveat that I'll probably recommend users only go 'near-perfect' to start
* after thinking about it, I renamed the 'definitely' to 'almost certainly'. with an even more confident tier in 'near-perfect', 'definite' is the wrong word
* I am still interested in any false positives or false negatives you encounter hereon. the main problem I now have to beat in image terms is where the alternate is an artist correction that moves a small object of interest a few pixels amidst a sea of similarly coloured pixels, for instance moving an anime nose a few pixels right. eyes that have slight differences (tear-drops, heart-shapes) are also proving a problem, but the main one is a small thing moving without changing average colours anywhere. also, obviously, if today's algorithm is actually worse anywhere, let me know!

### better export filenames

* the call that generates export filenames for manual exports, export folders, and drag and drops with export filenames is improved in several ways--
* - you can now set your own 'max filename length' under `options->exporting`. defaults to 220 (most OSes are 256, although Linux eCryptFS is ~140)
* - on Windows it now tests filename and total path length against characters rather than encoded bytes
* - the test against max total path length (260 characters on Windows, which we shave to 250 for extra safety) is more reliable
* - on Linux it now tests against a max total path length of 4096 bytes, and on macOS 1024 bytes. we shave by another 20 bytes for safety
* - the test against total filename length now recognises when a filename pattern produces subdirectories and will not include them for the filename length test
* - there is less padding fudge in the system, around 54 characters! if you were clipped before, you will likely see longer filenames immediately
* if you have an export folder that uses frequently elided filenames, it is going to be busy as it generates new filenames on next run. let me know how you get on!
* added a bunch of unit tests to test filename eliding, for: null, filename, path, filename and long path cases, for ascii and unicode, for character limits (windows) and byte limits (linux)

### url slash test

* when I first made the network engine, I had the URL normalisation routine collapse multiple leading slashes on a URL path down to one. for instance, `https://site.com//images/123456.jpg` becomes `https://site.com/images/123456.jpg`. this is actually incorrect handling on my part, and there's a site or two where it matters. unfortunately, I cannot make the switch without breaking URL Classes that already relied on the collapse, and I do not know how many of these there are out there
* so, I have added a checkbox to `options->downloading` where you can participate in a TEST to change the normalisation behaviour. I would like advanced users who use unusual downloaders to turn on the test and run their subs and stuff as normal. let me know if anything suddenly doesn't work. I suspect 99.8% of everything will be fine, but I don't know so let's test it
* as a side thing, I have adjusted my master URL lookup tool, which checks for duplicates in the file log and does 'already in db'/'previously deleted' url status lookups, to consider the leading single slash as matching the two slashes. I can't do the same for URL Classes though!

### enter vs add tags

* the manage tag parents and siblings dialogs are now 'add_only' from the 'add' button. previously, this was really an 'enter' command that would add new but petition pre-existing, but this workflow was never very intuitive and now we are reguarly dealing with hundreds of rows it is only ever confusing and annoying. similarly, the 'import' button now only offers a way to add new rows. sorry for the inconvenience here--I regret this took so long to figure out. if you want to do very large clever deletes, select the rows you do not want with ctrl/shift+click and hit the 'delete' button. if you want programmatic ways to remove rows (maybe a return of the 'import' conflict-remove, or a full-on only_delete mode), let me know how you would like it to look
* the 'CONFLICT: Will be deleted on add.' list notes as you enter siblings are now more varied and precise
* similarly, in manage tags, the 'allow remove/petition result on tag input for already existing tag' cog-menu option now defaults for new users to False, and all updating users will be set to False in v626. I don't like to force option changes on update, but most people are surprised to learn this option even exists, so I'm flicking us all, one-time, to the less confusing mode

### duplicates

* auto-resolution rules are now processed in alphabetical order. the preferred order in which rules and pairs are processed is a complicated topic and I am not sure on what is generally ideal, but if you have an opinion you can now force it
* I think I fixed some layout squish with the duplicates hover window. the window sometimes won't grow to be a little taller, particularly if a comparison statement goes from single line to multiple, which was causing the buttons to squish to make everything fit, until the user jiggled a window resize
* I think I fixed some transitional layout flicker with the duplicates hover window, particularly when some of the comparison statements are multiple line. also the previous pair's score line now properly blanks out while the new comparison statements are being loaded
* if a duplicate metadata merge options panel no longer allows you to set 'move from worse to better' tag action when you hit 'edit action' on a tag repository. this choice was accidentally being included here.
* if a duplicate metadata merge options does have 'move from worse to better' tag action set for a tag repository, through whatever grandfathered legacy reason, this is now treated as a copy action. previously it was hitting a 'you should not have been able to select this' safety check and doing nothing! if you have a hole because of this, don't panic--it is just another hole we'll want to fill in with retroactive duplicate merge, when we get around to that

### misc

* when the client adds or edits services, it now forces case-insensitive unique names. you can use whatever upper case you like, but you won't be able to make two services called 'score' and 'Score' any more. this helps out some parsing stuff
* same deal for subscriptions, duplicates auto-resolution rules, and import/export folders. not because we parse these names, but just to better differentiate big objects we want to be careful about
* fixed name deduplication when editing an import folder
* thanks to a user who submitted a PNG with 'srgb' colourspace metadata, I have fixed PNG colours for these files. this is related to the recent gamma/chromaticity work. a bunch of PNGs that previously rendered slow will now do so fast and with correct colours
* I've added `system:inbox/archive` to the list of selectable system predicates for all search file domains (previously they were hidden when your search domain had no 'real' and 'current' file domain). inbox/archive doesn't really have meaning outside of your local files, but advanced searches that switch file domain do sometimes carry these preds over to something like 'deleted from my files', so we might as well support them officially and fix the exposed nails. I think the logic will be crazy sometimes, and any counts too, so if you do clever searches and use them, let me know if and when they fail
* the routine that bundles many items into a single UI presentation text (for instance, when you paste a whole bunch of query texts into a sub and it talks to you about them) now deals with very long lists better. it'll now max out at 25 lines, each line about 64 characters, with the last being some form of 'and 741 others' overflow. we think that pasting many thousands of queries into a sub may have been causing out of memory crashes when a dialog &gt;32k pixels tall was being created. this obviously also generally fixes crazy tall dialogs in these cases
* when the file migration system chooses locations to pull from and push to, it no longer selects candidates of equal urgency pseudorandomly, but now pulls from the disk with the least free disk space and pushes to the one with the most
* fixed some 'repair missing file location' handling when the incorrect path is stored in the database in an invalid portable/absolute format. this may be related to some flatpak path magic
* a related problem where in rare cases a normal file migration would abandon the job early because it could not delist the old location is fixed

### help and env stuff

* updated help regarding running the db on BTRFS and NTFS filesystem compression. thanks to the users who let me know that BTRFS is ok and faster these days, particularly on WAL journalling, which we use by default
* added 'how to test and get `git`' to the Linux and macOS 'running from source' help
* clarified some 1/2, A/B stuff in the duplicates auto-resolution dialog text
* fixed some bad newline .md formatting in 'running from source' help
* updated the 'test' `mpv` version to `1.0.8` and `PySide6` to `6.9.1`

## [Version 625](https://github.com/hydrusnetwork/hydrus/releases/tag/v625)

### more ratings work and some QoL

* thanks to a user, we have several new items--
* in `services->manage services`, all numerical rating services have a new 'icon padding' value, which allows you to squeeze the stars together or push them apart. set to 0 to restore the old 'loading bar' way of presenting (square) numerical ratings
* the `manage ratings` dialog has better layout
* also, two new checkboxes in `options->gui pages` allow you to have the client ask you to auto-name new 'page of pages' on either creation or 'send pages to a new page of pages' events

### options

* `file->shortcuts` is gone! the same panel is now under `file->options->shortcuts`. I still hate how this guy works and want to merge all the sub-panels into one big user-friendly list with a filter and stuff
* the 'custom shortcuts' panel is now viewable in non-advanced-mode
* `options->sort/collect` is now split into `tag sort` and `file sort/collect`. the 'namespace grouping sort' is now in the correct location under the tag box whoops
* `options->media viewer` has all hover/background related options sent to the new `options->media viewer hovers`
* `options->gui pages` has had a reshuffle and the session stuff is pulled out to a new `options->gui sessions`
* all the stuff in `options->speed and memory` now starts collapsed
* the options dialog should be a little shorter by default now
* rewangled how the 'replace left/right with primary/secondary' and 'numpad non-number keys are normal' options in `shortcuts` work in the sub-dialogs--they still appear to apply instantly in the dialogs, but they now reset correctly if you cancel out of the main dialog
* the edit shortcuts panel now only writes to disk on ok if you actually edited something

### file relationships

* added a new 'media' file relationships shortcut command, `file relationships: delete false positives within selection`, and an equivalent menu command when you have multiple thumbs selected, `delete all false-positive relationships these files' alternate groups have between each other`, which removes false positives only between pairs of files in the selection, rather than the other 'remove false positives' command, which removes all known false positives. if you accidentally set a false positive on a pair, this is now specifically undoable by selecting the pair and hitting this
* when you do the various 'delete false positives' actions, you now get a popup saying how many were deleted
* gave the 'file relationships' file menu a quick pass. it stacks better and now says when a file has no relationships. the reset/remove submenus are also split apart to clarify action importance. this horrible thing should nonetheless absolutely be replaced, wholesale, with a nice review and/or edit panel
* cleaned up some of the various duplicate merge logic, replacing hacky stuff with unified calls etc.. I think some redundant potentials are now removed more smartly when you merge certain alternate group members together, and I think the 'confirmed alternates' list is properly cleared of B entries when you merge B into A now. some 'merge alternate groups when two files are set dupe' stuff is clearer and works more thoroughly too. I expect to add a 'clear orphans' maintenance command here in future to handle these legacy issues and cleverly fix any db damage
* when you explicitly set files as alternate, any previous false positive relationship between the two is now repealed rather than the job silently failing

### duplicates

* the 'A and B are visual duplicates' test now gives a negative result if either file has transparency, confidently if only one does and not if both do--it isn't smart enough to handle this yet
* the approve/deny buttons in semi-automatic auto-resolution rule review now do their work off the main thread and no longer block the UI on big jobs
* the 'preview' panel of an auto-resolution rule now fetches each block of pairs in a random order it figures out every dialog boot. if you open up a rule that has worked a bunch already, you can sit there watching it climb up to 500,000/700,000 and find nothing since it already did that front work. now it fetches randomly and will start population more swiftly. of course the results will now be in a roughly different order every time you boot the dialog, so that's not amazing--let me know how you find it. I think I may be adding a lot more random access like this, and that means where we will want unified pair sorting settings (much like we want in the manual duplicate filter, which still produces a garbage hardcoded fixed order of pairs!)

### subs and downloads

* a core multi-column list update routine is optimised significantly. when many new items come to a list after an edit event (usually mass add or some mass edits), it now selects all items at once. previously it was doing so one at a time, which was triggering a billion button update calls. doing a mass paste into a subscription, or doing a 'separate sub of 1000 queries into 1000 separate subs of one query' now takes about three seconds, instead of many minutes
* when you paste queries into a subscription, if some already exist in the sub but are DEAD, you are now yes/no asked if you want to revive them
* if a subscription has a gallery page that decides searching should stop, which for this purpose typically means it has 'caught up' to a previous sync, all additional pending gallery url jobs of the same url class in the gallery log will now be set to 'skipped' with a reason of 'previous blah url said: (original stop reason)'. this ensures that downloaders that produce multiple gallery pages in one step are now processed efficiently and obey the catch-up mechanic rather than overspilling the cull limit and adding old files back in--as soon as one page is 'caught up', the rest are skipped. I made this only skip of the same url class so as not to break NGUG subscriptions. if an NGUG produces multiple gallery pages of the same class, they may be thrown off by this since they will no longer check every outstanding gallery url unless the previous produced something useful--if you are clever enough to know what this means, let me know how you get on
* when a network job downloads a file from a Post URL, it now registers the bandwidth use to the Post URL's domains as well, if they differ. this should soon fix the issue where a site that produces files on completely different domain was not pausing when the file domain hits its bandwidth rules (file urls override bandwidth rules within three seconds in order to keep post/file url hits close together, which helps some token stuff, but if the post url never becomes aware of how much bandwidth it is eating, it just keeps on chugging. now it won't!)
* added a checkbox to stop the 'override bandwidth in 3 seconds' rule under `options->downloading`, but I'm hoping the above overall fixes the issue

### misc

* the page tab menu gets a new 'collapse pages' submenu. depending on where you click, it'll say 'this page', 'pages from here to the right', and 'pages to the right'. it will suck up all the files from the given pages and place them in a new locked search page, closing the old pages in the same step. use this for when you have eight small import pages in a row you want to collapse into a single processing page. it isn wrapped in a yes/no. it works on 'page of pages' too. this action is cool to do, so try it out
* the 'send down to a new page of pages' gets the same 'pages from here to the right' option too, so you can do both operations from the very left-hand side if that's what you want
* fixed a benign error popup when you hold the 'next image' shortcut while closing out on the last pair in a duplicates filter
* if attempting to send a file to the OS recycle bin results in a `0x80270021` error (many causes for this, but it seems it can also be an unluckily-timed sharing violation or a recycle bin with 100k+ items in it and being mega laggy), it is now re-attempted twice, with short breaks in between
* when, under `services->manage services`, you open an edit panel for a rating service that has stars, the client now repopulates the cache it stores of all your current custom svgs. no need to reboot now, just reload the dialog and it'll show what is current
* I _may_ have solved some indirect threading deadlocks. all threaded jobs also initialise just a tiny bit faster now
* blurhash generation, which can be a whack of CPU per import, is now a tiny bit more efficient

### boring stuff

* removed `setuptools` from the requirements.txts that don't have `pyinstaller`. we freeze the `setuptools` version to ensure a stable frozen build structure, so this isn't explicitly needed anywhere else
* refactored some of my advanced dev requirements.txts
* brushed up the 'running from source' help doc and added some info about testing/installing `pip` and `venv`, which aren't always available by default in Linux
* replaced all the `typing.Collection` style typedefs across the program with the `collections.abc` equivalents. this stuff was deprecated starting Python 3.9 lol. also, I'm pretty sure this was already true, but hydrus will now definitely not run in Python 3.8
* replaced all the basic `typing.List` style typedefs across the program with the standard `list` equivalents. same deal as above
* overhauled the 'db duplicates' unit tests, breaking up the previous monolith rollercoaster into something a bit more atomic. it is still a huge mess, but much better than before
* added some unit tests for the new 'remove false positives within selection'

## [Version 624](https://github.com/hydrusnetwork/hydrus/releases/tag/v624)

### locked pages

* the search page state where it could hold files but have no active search is back with some bells and whistles. it is now much easier to manage a 'scratchpad' file page that won't suddenly get messed up if you hit F5 (issue #1602, and likely others in different ways)
* all normal file search pages now have a padlock icon beside the autocomplete text input. clicking this collapses the current search to a single system:hash of the current media in view and swaps the search panel for an 'unlock' button. this page will not refresh its query until unlocked, at which point you are given the system:hash back
* if you add files to or remove files from the page, the underlying system:hash will update to the new contents of the page
* lock status is saved in the session, so it persists through restart etc..
* any time you create a page with files, which typically means, 'open files in a new page' and subscription file-popups, they now start in the locked state. since the system:hash updates for new files, you can drag and drop new files onto the page, or add more subscription files from a later sync, and the underlying system:hash now stays updated. play around with it--you'll see how it works
* if you are big brain and wish in some cases _not_ to sync the underlying system:hash on add/remove file events, a cog icon beside the unlock button lets you set this
* if you have a bunch of existing subscription landing pages and other 'I'll process this later' pages, please go through them after update and lock them. it'll say 'hey, you already have a system:hash but it differs to what is currently in view, do you want to overwrite this old one with one for the current files?' and you do, so click yes
* next step here is to finally figure out some sort of 'sort files by system:hash/downloader' sort type so these sorts of pages can restore original sort

### duplicates

* the 'preview' panel of an auto-resolution rule has had a complete pipeline overhaul. after a much, much, briefer one-time initialisation, it now loads results in fast small batches and streams pass/fail pairs to the lists one by one. it shows search progress and presents ongoing count of pairs. it no longer gets the total count of the search every time--unless you let it run all the way and get everything. the refresh buttons are more efficient, the 'only sample this many' widget updates the dialog live as you edit it, and there are pause buttons for both search and testing. it also cancels work faster if the dialog is closed amidst work. this dialog is now ready for the relatively CPU-expensive 'A and B are visual duplicates' integration
* when the core duplicate file searches they rely on are CPU-expensive, the duplicates filter batch pair fetch, duplicates filter count fetch, duplicates 'show some random pairs', and duplicates auto-resolution rule preview now load up faster, particularly when you have few potential pairs remaining
* auto-resolution rules that are in semi-automatic mode now only queue up a max of 512 files in the 'pending' queue. it can take some CPU to run these tests, so it is good to keep the queue short and snappy in case you need to change anything (thus resetting the queue) in future. you can alter the 512 limit, including removing it completely, in the edit rule panel
* auto-resolution rules now categorise their comparators into a cross-reference of fast + order-possibly-important. the main testing routine and 'can this pair fit either way' test now cascades through some logic to get a dispositive true negative result faster
* the program now recognises and gracefully handles the situation where the duplicate filter is closed and program shut down initiated before a slow-loading visual duplicate pair can finish (it was outputting some mysterious error lines to the log)

### a and b are visual duplicates

* if the images are very simple, e.g. just one or two flat colours, they are now considered 'too simple to compare' and not visual duplicates. these edge cases are often deceptively tricky
* if the images have a perfectly matching interesting tile, the presence of any non-matching tile now results in 'probably not visual duplicates/(small difference?)'
* I experimented with many new techniques: pre-decimation histogram population, histogram absolute difference comparison, tile phashes, longer tile phashes, gaussian edge detection histograms, gaussian edge map average block 2d wasserstein scoring, and even gaussian edge map phashes, but unfortunately these all pretty much failed. the algorithm as-is is good, but there are still a couple of false positive situations it cannot catch. the delicate edge detection is the main thing--a difference with a subtle shade (e.g. a soft line, or a transparent water droplet) that is clear to the human eye can still be missed. please keep sending in any false positives, and I'll keep thinking about all this
* cleaned and polished a bunch of this code

### misc

* thanks to a user, the new resizable ratings have improved visuals! the little padding clipping bugs are fixed and everything lines up nice
* 'less than or equal to' and 'greater than or equal to' are added to all the modernised places you can set a number comparison, such as `system:height` or duplicates auto-resolution comparison statements
* fixed the broken `Ctrl+C = copy selected files` default 'media' shortcut for newer users--if it is broken for you (it'll say 'Unknown Application Command' in the shortcut UI), it will fix itself on update

### updated Linux and Windows builds

* the 'future build' last week went without any reports of problems, so I am folding the changes into today's normal build. both Windows and Linux are updating several core components and will gain a host of small and large bug fixes and performance improvements. It does not seem that a clean install is needed this week, but if you use the zip or tar.zst extracts, you might like to take this opportunity to do one anyway: https://hydrusnetwork.github.io/hydrus/getting_started_installing.html#clean_installs
* the WIndows installer basically does a clean install every week, so no special instructions there
* the changes are--
* Windows and Linux: moved from python 3.11 to python 3.12
* Windows and Linux: moved from PySide6 (Qt) 6.7.3 to 6.8.2.1
* Windows: moved from windows-2019 runner to windows-2022 (2019 runner is being retired next month)
* if you use a particularly old, un-updated version of Windows 10, it is possible the new Windows builds will not run for you. try running from source and choosing an older Qt version: https://hydrusnetwork.github.io/hydrus/running_from_source.html
* if you already run from source, you might like to rebuild your venv this week to get the new Qt. users on Python 3.13 no longer have to choose the (a)dvanced mode for the (t)est Qt version-- on a typical OS, all pythons from 3.10-13 should now work with (s) out of the box!

### weird/boring stuff

* I fixed some encoding in my png gamma/chromaticity ICC Profile generator. it still isn't there, but I know where to look. also wangled the `wtpt` and `chad` to handle non-D65 source whitepoints
* I may have fixed an issue where the thumbnail banners could be drawn with bold text
* my asynchronous updater object can now deal with several mid-job cancel events
* my thumbnail pair list can now handle streaming appends
* deleted the monolith 'get potential pairs that match this duplicate context' routine the preview panel was relying on. I'll migrate more duplicates stuff to incremental fetches like this, and I feel good we can make the duplicate filter and so on initialise much quicker
* updated the client api help's Hydrus Video Deduplicator link to https://github.com/hydrusvideodeduplicator/hydrus-video-deduplicator

## [Version 623](https://github.com/hydrusnetwork/hydrus/releases/tag/v623)

### misc

* thanks to a user, we have a new `Paper_Dark` stylesheet. it has many custom svg assets that will redraw checkboxes and so on
* the client now tries to adjust for timezone when it parses a modified date from a server response. some downloaders will now get a more precise 'modified date' for their domains
* fixed a typo bug that was causing existing 'set numerical or inc/dec rating' commands to fail to initialise in the shortcut panel on edit (staying as the default 'simple command, archive file')
* a new `DEBUG: Activate Main GUI when closing the media viewer` checkbox under `options->media viewer`, default fa!se, lets you force an "activate" call on the Main GUI (bringing it to the front and setting keyboard focus) on any media viewer close
* the core hydrus server/client api response object now better tries to clear out ongoing file downloads when the connection is disconnected early. if you noticed in Hydrus Web or similar that scrubbing through a bunch of big videos one after another could get laggy, let me know if it is any better now

### duplicates

* all duplicate filters now have the 'A and B are visual duplicates' comparison statement. this is a custom algorthim that inspects the images and attempts to differentiate resizes/re-encodes from recolours/alternates. please rely on it as you do normal duplicate filtering of images from now on, and if it produces any false positives, I'd love to see the files!
* I improved this 'A and B are visual duplicates' algorithm after our test. overall it went very well, with only a couple false positives found. thank you for your feedback, everyone. I improved the 'skewness' test to reduce the number of false negatives, and I added a new special test to catch the false positives submitted. further, I have softened the 'no' result texts and categorised the 'yes' results into three clear 'very probably'/'definitely'/'perfectly' lines so you can better recognise edge cases. when this test is integrated into the auto-resolution system, I will default to just definitely/perfectly results to start
* fixed the bug in auto-resolution where when you edited a rule, its labels would sometimes would not update in the main duplicates page review list (the rule was working fine, and opening a new duplicates page would show the rule correct). this was a bug in the list update code itself when dealing with a special case of very similar objects. I don't think anywhere else in the program was affected, but it is sorted now
* the right-hand duplicates hover window should be less jittery as it lays out the new asynchronously loading comparison statements. in a couple of cases, the buttons were getting squashed and snapping to different sizes on window resize and so on--should be better now

### AVIF note

* some AVIF files may have weird rotation since the recent shift to `pillow-avif-plugn`. sorry for the trouble! there is no easy fix here. since Pillow proper will hopefully be getting native AVIF support in 11.3 sometime in July, I am delaying doing a hacky fix here until we see how 'real' Pillow handles this issue (issue #1728)
* due to some recent definition reshuffling, new AVIF files were accidentally not being scanned for icc profiles, exif data, or human-readable metadata. I've turned these flags back on for now, and when we are settled into happy stable Pillow land and know it is all working right, I'll schedule a full rescan for all existing AVIFs

### pngs with gamma/chromaticity info

* my new gamma/chromaticity png correction code now uses much less memory--somewhere around one twelfth and one sixteenth of what it did. sorry about the decompression bombs on loading certain large (&gt;4k) pngs! it still runs a little slow, so there is more work to do here
* fixed a divide by zero error when a png provides invalid gamma/chromaticity info
* I dumped a ton of time into trying to convert this info to an ICC Profile, as GIMP and Qt are able to do, but I couldn't quite figure out how they did some whitepoint and colourspace translations. I expect to revisit this, since if we could merge all colourspace conversions to one fast and low-memory pipeline, that's better than me maintaining a dozen math hacks. if you are an enterprising programmer with ICC Profile experience who wants to help out, please feel free to check my work under the new `HydrusImageICCProfiles.py`, and the Dequanitze caller in `HydrusImageNormalisation.py`--what's the correct translation/value for the `wtpt` and `chad` ICC Profile tags, and how should the `rgbXYZ` and `rgbRTC` tags be modified from the original gamma and chromaticity stuff?

### better file maintenance jobs cascade

* this was happening in patches before, but it is now formalised--
* if the exif status of a file changes during file maintenance, this now auto-triggers a file metadata call to check for rotation changes
* if the previously understood appearance of a file changes in file metadata, has icc profile, or has transparency file maintenance, this now triggers a thumbnail regen, a pixel hash regen, and perceptual hash regen
* if a thumb is regenned in file maintenance, this now triggers a blurhash regen
* when files are told they have new display data because of file maintenance, the image cache and image tiles cache now explicitly remove all data related to the files so they can be quickly regenned if looked at currently or in the near future (this was spotty before)

### boring cleanup

* bit of type cleaning in my List code (my IDE updated and new linting rules went bananas)
* cleaned up several dozen type defs, mostly QEvent stuff, that turned up in project linting
* fixed up numpy array type hints across the program
* fixed a unit test that had a very small chance of failing with some improved setup code

### future build

* there's a future build this week for Windows and Linux. they both have important changes, but both ran for me and neither needed a clean install when upgrading from v622. I _think_ this will run on a reasonably updated version of Windows 10, but we are now pushing this so that's the top concern. if you are an advanced user and would like to help me test, please check it out
* the changes are--
* Windows and Linux: moved from python 3.11 to python 3.12
* Windows and Linux: moved from PySide6 (Qt) 6.7.3 to 6.8.2.1
* Windows: moved from windows-2019 runner to windows-2022 (2019 runner is being retired next month)

## [Version 622](https://github.com/hydrusnetwork/hydrus/releases/tag/v622)

### misc

* fixed several sub-pixel problems with the new rating drawing when using PyQt6. in some cases it seems this was breaking boot. sorry for the trouble!
* fixed a 'The chosen db path "db_dir" is not writeable-to!' error when you try to boot two clients/servers at the same time, usually with cold memory (it seems like they were syncing into early bootup checking at the exact same time due to uncached dlls and then interfering with each other's directory write-test)
* if the 'selection tags' list is capped to only showing the first (by default) 4096 unselected files, it now says so in its box title
* if you hit paste (ctrl+v or shift+insert) on the text input in a write/edit tag autocomplete that has a paste button (e.g. in 'manage tags' dialog), and your clipboard has multiple lines of content, you now get a little yes/no dialog asking if you want to enter everything as separate tags (otherwise, as before, it munges all the lines into your input)
* a new checkbox in `options->tag editing` lets you skip the yes/no check in this case (i.e. always immediately pasting multiline content you enter)
* the manage tags dialog paste button is now beside the text input box. it still only does 'add only' actions
* all new clients, and all existing clients that don't have `Ctrl+Shift+O` set in `main_gui` shortcut set already, now get `Ctrl+Shift+O` as 'open options dialog'. the 'Use Native MenuBar' option's tooltip now highlights this shortcut (a couple of users have been soft-locked out options dialog to unset this when it borked out)

### duplicates

* if you are in advanced mode, the manual duplicate filter will have a new "(not) visual duplicates" line with some numbers after it. this is the new "A and B are visual duplicates" test I have been working on, which uses a bunch of histogram statistics to programatically differentiate resizes/re-encodes from files with significant visual differences. if you do duplicate filtering this week, please look at this new line and let me know how its predictions hold up. I have tuned over about 100 real pairs, and I feel fairly good, but let's see on a larger scale. it sometimes false negatives (saying they are not visual duplicates when they actually are) when the pair has a particularly wide difference in scale or encoding quality, and I'm ok with that failure, but I do not get any false positives (saying they are visual duplicates when there is actually a watermark or something). I am most interested in false positives, since we hope to fold this tool into the duplicates auto-resolution system and I don't want a positive fail. the statement will also suggest a little more info if it thinks there is an obvious watermark or recolour. please send me any pairs that are reported wrong, and if you like you can look at the numbers. I will retune this tool as needed and fold it into the automatic system, and I'll launch this test as a real comparison statement for all users (but without the ugly debug numbers). thank you for testing!
* updated my 'A and B are visual duplicates' test to return a false when the files have resolution ratio that differs by more than 1%
* updated my 'A and B are visual duplicates' test to return a false when either file has resolution below (32x32)
* the duplicate filter comparison statements are now generated asynchronously. if and when the comparison statements need high CPU, they won't lag the initial pair load
* the 'this is a pixel-for-pixel duplicate png!' comparison statement and associated high score no longer applies to webp/png pairs. webp can be lossless, where this decision is less clear. if and when we get a nice 'this webp is lossy/lossless' detector, I'll bring this back
* the duplicates auto-resolution thumbnail pair lists should be less crazily tall if you have large thumbnails
* the cache that aids potential duplicate pair discovery has its cap (1 million search nodes) removed. on clients with many millions of files, ongoing similar files search will be I think around ~16-50% faster. each node is four numbers and an 8-byte hash, so this will add something in the range of 100-200MB of memory use for giganto clients. for interest, search distance 10 seems to cover a search space of ~40% of the entire tree, so on a db of a million images, that's 400,000 nodes to do hamming distance calculation on. thankfully each test is only about two microseconds, but it adds up, and search distance is the core determinant of search size, so keep it low!

### png colours

* PNG files are now scanned for gamma and chromaticity metadata on load. if they have this information (and no ICC Profile, which supercedes this info), it is applied much like an ICC Profile to colour-adjust the PNG to what was originally intended. usually these adjustments are very slight, just a shade one way or another
* all PNGs with this data (about one in twenty, I think?) should now render better. if any of your PNGs render crazy bright/dark/wrong this week, let me know!
* I did this in hopes of fixing some pixel hash stuff (no collision between a png and a non-png that should collide if this data is applied correctly), but my colour translation math seems to be slightly imperfect, so I may revisit this. I won't schedule mass pixel hash regen until I have this figured out

### delete lock

* added a new checkbox to `options->files and trash` that lets you say 'if the archive delete lock is on, then when I finish an archive/delete filter, ensure all the deletees are inboxed before the delete'
* added a similar checkbox that lets you say 'if the archive delete lock is on, then when I do a manual duplicate filter, ensure all the deletees from merge options are inboxed before the delete'
* I don't really want to write exceptions to the delete lock filter, but I hadn't thought about it from quite this angle before. lets see how this works as nice simple solution for this particular problem. if you use the delete lock and want to try this, make sure you are confident it is what you want
* if this ends up being a tangle of ugly logic, and/or if the delete lock extends to properties other than 'file is archived' in future, I may yank these options

### client api

* thanks to a user, the Client API now has calls to get/set the favourite tags. these calls use the existing 'add tags' permission (issue #311)
* updated the help and wrote some unit tests for this
* client api version is now 80

### boring cleanup and weird stuff

* fixed a couple places in the Client API documentation where it said a POST request didn't need a header; they all pretty much need `Content-Type: application/json`
* the duplicate comparison statements in the duplicate filter hover window are now center-aligned using the correct method/flag
* the operator radio buttons in the `NumberTest` widget (which appears in several places to manage 'X is &gt; Y', and the operators where it says &lt;, ≈, ≠, etc..) now have tooltips more clearly explaining what each is
* rejiggered some duplicate content update stuff to better separate the metadata updates from the delete file calls; I wasn't sure which order this stuff was happening, but now it is explicit and the delete happens at the end
* my 'merge directory' call now strictly does not delete anything from the source dir until it is finished copying with no problems. previously, it would move files as it went, so if the copy failed half way through due to an I/O failure, the source was left partial. this no longer happens
* fixed a couple of dumb path translation lines in my directory mirror/merge calls so they can better handle weird dirnames
* the advanced mode 'experimental' tag list menu that lets you change the tag display context now shows the 'single media views' option as well

## [Version 621](https://github.com/hydrusnetwork/hydrus/releases/tag/v621)

### more ratings

* thanks to a user, we have many new rating options--
* `options->media viewer` and `options->thumbnails` now let you alter the size of ratings!
* there are now many new rating shapes to choose from under `services->manage services`: triangles pointing up/down/left/right; diamond; rhombus pointing right/left; pentagon; hexagon and small hexagon; six point star; eight point starburst; hourglass; large + and X shapes
* also, in an experiment, you can now also set a custom svg to your rating. there's a new folder, `install_dir/static/star_shapes`, that you can drop svgs into to have them available. I've put a couple of simple examples in already. try to do a squarish shape with a clear sillhouette on transparency. we will keep working on this, but feel free to try it out yourself and give feedback. I suspect we'll migrate all the existing custom polygons to nicer svgs in future if and when we nail nice svg border colours and stuff
* I added a help button to the `manage services` edit panel here, linking to the ratings help, which has a new section on the svg rating shapes
* I reworked some stuff behind the scenes to more neatly integrate this rating tech and allow for svg ratings. the 'edit service star shape' UI in `manage services` has two dropdowns now, too
* we are experimenting with fractional pixel sizing and drawing here, so some of the new ratings may seem a little blurry in places and/or not line up well, including between the underlying canvas and the top-right hover pop-up. I'm going to work on this a bit and see what I can do to make it more pixel-perfect
* we may figure out unicode character ratings in future also

### misc

* fixed a bug in the duplicates system's 'pixel hash' test. my current pixel hash is dimensionless, and thus, by accident, a completely flat-colour (or careful checkerboard etc..) image of 100x500 has the same pixel hash as the same colour of 200x250. it obviously doesn't come up much, but I regret the error. rather than recompute everyone's pixel hashes with dimension data, we are first patching the test code to double-check the images both have the same width. it seems ok here, but let me know if your 'must (not) be pixel duplicates' duplicate file searches are now interminably slow
* split the prefetch settings in `options->speed and memory` into their own box, and updated the labels a bit
* added a setting to this new box to govern how many pairs the duplicate filter will prefetch. previously this was hardcoded to 1, now it defaults to 5 and you can set whatever
* when the client or server checks if it is already running, the 'client_running' file's 'process creation time' is now only tested to within a second's accuracy. if you have a bespoke backup workflow that involves creating your own client_running file, it should get caught better now despite float imprecision
* updated the various Linux install/running-from-source stuff to talk about `libmpv2` as well as `libmpv1`.
* I rolled out a v620a hotfix last week after my refactoring accidentally broke the manual duplicate filter. sorry for the trouble! I have improved my testing regime to catch this in future

### duplicates auto-resolution

* you can now add 'system:known url' and 'system:number of urls' predicates to the 'test A or B' comparators
* you can now add 'system:number of urls' to the 'test A against B using file info' comparators
* added unit tests for these, and cleaned up some of the unit tests in this area

### avif

* the `pillow-avif-plugin` test last week seemed to go well. this library is now folded into the main builds, and AVIF rendering should be more reliable for the time being (issue #1720)
* if you run from source, you might like to rebuild your venv this week to get this

### psd_tools replacement

* `psd-tools` is no longer used by the program
* thanks to a user report, we discovered that the Linux build was including an old and vulnerable version of a bz2 decoder. this thing was hanging around because of a drawing library included by a psd parser we use. I am not sure if the decoder was ever called, given what we use the library for. I did a test build of Linux with the bad file simply deleted, and it seemed to boot ok, but I wasn't sure if the file was bundled into a pyd on the Windows and macOS side, and I'm pretty sure it would be included in a source install, so I wasn't really happy
* ultimately I decided I didn't like having this complicated psd library hanging around when we only needed to pull dimensions, icc profile existence, and pulling an embedded render preview file, so I cobbled together some other backup solutions we already mostly figured out, including an ffmpeg renderer, and wrote a simple file parser and replaced all the psd_tools stuff with our own calls
* there are some psd files ffmpeg seems not to render as good as psd_tools did, but I'm fine with it for now
* I seem to be detecting icc profiles that psd tools did not recognise, so I'm scheduling all psds for a 'has an icc profile?' check on update. maybe I'm false-positiving, but I'll make sure the existing store reflects current code at least
* I also fixed some psd rendering for files that had weird 100% transparency
* along the way I improved some PSD error messages and handling. PSDs that have no embedded preview should stop spamming that info to the log on thumbnail regen

### swfrender removal

* since cleaning was on my mind, I'm removing the swfrender exes too. new swf files you import will just get default 'flash' thumbnails from now on. having these ancient executables hanging around to load unknown flash files is not an excellent idea these days, even though it has been fun
* the actively developed 'Ruffle' flash emulator seems to be working on a CLI executable that can render flash frames, which could be a much better and more reliable replacement in future
* I haven't played with it properly yet, but ffmpeg can apparently thumbnail some flv-embed-style flash files, so I'll explore this too

### refactoring and cleanup

* moved some ffmpeg stuff from `HydrusVideoHandling` to the new `HydrusFFMPEG`
* merged all 'ffmpeg was missing' and 'ffmpeg output no content' error handling to single calls and improved coverage
* wrote some 'render to pipe' stuff for ffmpeg to make some of the ffmpeg based rendering work a little quicker and without the temp dir
* deleted the `HydrusPSDTools` file
* moved some more old network reporting mode code to a cleaner unified method

## [Version 620](https://github.com/hydrusnetwork/hydrus/releases/tag/v620)

### user gui improvements

* thanks to a user, we have some more UI features--
* the options dialog now remembers its last page (can uncheck this if you like under `gui` page)
* a checkbox under `gui` that says whether to save media viewer size and position on close (normally it only saves on move/resize, but if you regularly use multiple viewers, you may wish to override so a final close saves what you want)
* the media viewer gets a 'drag' button in the top hover. drag the button, you drag the window. useful if you are using it in the newer frameless mode
* if you right-click this new button, there are some neat new commands to change the fit the window size to the current mediia size too
* the new 'resize frame to media' commands are mappable on the 'media viewer' shortcut set. you can set the specific zoom
* we now have a command for 'zoom to x%', also! same deal, it is now in the 'media viewer' shortcut set
* the media viewer should be better about saving its position when moved by programmatic window position-setters like Windows Snap
* two checkboxes under `gui pages` let you promote 'all my files' or 'all local files' buttons to the top of the page picker (for, e.g. if you have many file domains that spill over what the dialog can show)

### misc

* wrote an animated webp frame duration parser and integrated it into our file metadata stuff. animated webp files are no longer fixed to 12fps and support variable framerate (issue #1694)
* on update, all animated webps will be scheduled for a metadata regen to get corrected total duration times
* fixed some url unit tests I accidentally broke last week because of the defunct url classes I removed, and updated some of the 'how to make url classes and parsers' and client api help to use more generic url examples
* improved the grammar and general presentation of the 'files being parsed' message text in the 'import files' dialog. this text also tooltips itself in case it gets crazy long
* the 'quality info' button in the 'edit subscription' dialog is now aware of which queries actually exist on disk versus those that were generated in this 'edit subscriptions' session. it now presents info only on selected queries that actually exist, and if only new queries are selected, it disables itself
* the system tray checkboxes are now set to false along with being disabled if the current system does not support a system tray (e.g. Docker). the calls these settings make have an additional protection layer that checks if the current system has a system tray (issue #1569)
* the 'show pending and petitioned groups' and 'show whole chains' checkboxes in the manage tag siblings and parents dialogs now disable if you hit 'show all pairs'. these are inherently true with 'show all pairs'
* the file maintenance routine that attempts to re-queue known urls for files that are missing or damaged now double-checks that any 'Post URLs' are currently parseable. (some 'decorative' urls have 'Post URL' url classes so as to appear in the media viewer but aren't actually linked to anything)
* in the 'thumbnails' shortcut set, you can now set a 'select: not selected' command, to invert the current selection
* the display names of normal pages are now clipped to 256 characters and are better about removing accidentally included newline characters
* the macOS dialog double-positioning thing we added in March that fixed dialogs slowly creeping like 26 pixels down on every dialog session is now careful not to apply to the main window on boot. it seems the fix was making the main gui move ~100px sideways, no idea why

### future build and more AVIF fun

* it looks like the AVIF fix last week was not reliable--some boots it would work, others it would not. I don't know if this is some random fail triggered by the deprecated status, but whatever: we should promptly move to the designated 'use this in the interim while Pillow proper figure it out their end' solution to get good AVIF rendering back (issue #1720)
* thus I am making another 'future build' this week. I had been planning one for a while, particularly to try out a new mpv dll, but I'm just going to keep it nice and simple this week to test out the AVIF fix. if you are an advanced user, please try it out on your platform and let me know if there are any problems. if you run from source, you can rebuild your venv, and if you select (a)dvanced, you'll get a question if you want to install the AVIF test library
* assuming no problems, I'll fold this into v621
* on boot, hydrus now imports the `pillow-avif-plugin` library in preference to the old `pillow_heif` solution
* as a side thing, it looks like Pillow are going to try slender AVIF binaries in their wheels for 11.3, so this all may get simpler soon
* also, hydrus now reports 'avif ok' and 'heif ok' separately in various errors and the `help->about` dialog

### json parsing

* the json formula now supports two new parsing rules--
* first, a 'walk back up ancestors' parsing rule. it moves `n` steps back up the parsing stack, so if you have an Object where you need to test for one key's existence but you actually need to grab a sibling or cousin value, you can now walk back and it should work
* second, a 'filter strings/numbers/bools with string match' parsing rule. if you have grabbed strings or other simple variables, you can test them against a String Match. if you combine this with the 'walk back' step, you can now test Object values and then walk back up and grab a different thing
* wrote some unit tests for the existing and new json formula rules

### duplicates auto-resolution

* fixed an issue with renaming existing rules. due to a saving bug, renaming rules was causing duplicate entries behind the scenes. you might get an update message about it--if you do, your new rule may have rolled back to a previous version. I will have paused it, to be safe, so if you were hit by this, please double-check your rule is named as you wish and the settings are all good and then set it back to semi-automatic or automatic if you are happy
* added a maintenance job to the cog to clear the cached pair counts that the rules use to talk about their progress. if there's ever a miscount, this will fix it
* when you approve/deny some pending pairs, the selection now tries to preserve to the earliest selection you had before. previously it always fell back to position 0
* stopped the duplicates auto-resolution work from sending unintended 'I am not idle' signals as it did file search, prohibiting idle mode from kicking in
* fixed a stupid typo error when you say to add a new comparator rule but cancel the 'select which type' add dialog
* fixed an issue where a duplicates auto-resolution table wasn't being deleted correctly on rule delete. not a big deal, just a cleanup thing

### duplicates auto-resolution exact match detection

* _tl;dr: I think I can do the 'A is a resize/re-encode of B' in future_
* I did some research and bashed my head against different strategies, and I think I have figured out the core of a routine that can differentiate between resize/re-encode 'exact match' duplicates and files that have significant changes such as corrections or watermarks or recolours. It uses a bunch of math to break the images into normalised tiles, compute a weighted 'wasserstein distance' (earth-mover distance) of the tiles' Lab channel histograms, and reviews those scores, and their mean, variance, and skewness to exclude various classes of differing files
* I still have a bit of work to actually plug it in, since each judgment here requires a full image render for both in the pair and some of the UI isn't yet ready to handle a ~1 second delay per pair. I also need to figure out a nicer tuning/testing regime to ensure I didn't just overfit for the examples I generated. I think I'll plug it into the manual duplicate filter's comparison statements and we'll see with human eyes how it does. overall, I feel really good about it. I thought this would be a nightmare, but it looks doable. if you want to check my math and send in your own thoughts, check out the new `ClientImageHistograms.py`

### boring refactoring and cleanup

* pulled the rich maintenance manager code out of `ClientFiles` to a new `ClientFilesMaintenance`
* pulled the file storage manager out of `ClientFiles` to a new `ClientFilesManager`
* pulled the phash code out of `ClientImageHandling` and moved it to a new `ClientImagePerceptualHashes`
* moved the above files and `ClientFilesPhysical` to new `hydrus.client.files(.images)` modules
* reworked the images, image tiles, and thumbnails caches to be explicitly named variables in the client controller, mostly to improve some type checking stuff
* standardised some variable names around the cache access, and made the images and image tiles caches work in media results rather than media objects
* removed the afaik defunct `cloudscraper` from the code and requirements and a weird insert we needed in the client.spec build templates

## [Version 619](https://github.com/hydrusnetwork/hydrus/releases/tag/v619)

### cleaner tags

* updated the tag filter to exclude many weird unicode characters. all sorts of Control Characters, right-to-left formatting, zero-width spaces, surrogates, and more is now all removed. Zero-Width characters ZWNJ and ZWJ are allowed unless the rest of the tag is only in extended-latin. the hangul filler character is allowed if the tag includes other hangul syllable or jamo. there is no perfect solution here, but a bunch of mis-parses and other garbage is cleaned up with this (issue #1709)
* **your client will clean its tags on update. this will take several minutes if you sync with the PTR**. you will probably see tens of thousands of bad tags--don't worry about it too much, and everything is logged if you are super interested in the saga of `ç¿«∪ç¸`-legacy-decode-jank, `( ͡° ͜ʖ ͡°)`-that-includes-a-hidden-Byte-Order-Mark, and a relatively common `normaltag[ZWNJ]` that's probably either an IME input mistake or some HTML parsing error from years ago
* I've been fairly aggressive here, so if I have broken something you do want to input, or something that requires temporary invalid status via an IME, let me know. rest assured, however, that everyone's favourite compound emojis such as `👨‍👩‍👧‍👦` should still work

### linux build

* the Linux build failed last week because I missed notifications about the Ubuntu 20.04 runner being retired. sorry for the trouble! this has happened before, so I am going to keep a better check on retiring runner news in future
* the Linux build is now generated on the 22.04 runner. there _are_ some .so file differences, but it seems to all boot ok, and in one case it actually fixed a previously broken mpv load. also, a normal extract-update seems to have worked in our tests, so we don't think a clean install is strictly needed. You might like to do a clean install anyway, just to be neat: https://hydrusnetwork.github.io/hydrus/getting_started_installing.html#clean_installs

### misc

* AVIF rendering is fixed. I confidently wrote some code last week that said 'when Pillow updates to 1.21.1, don't load the recently deprecated AVIF support from our external plugin any more because Pillow will now have it natively', and then the Pillow update happened last week and they decided not to bundle in AVIF in their convenient wheel because it bloated their files. I have undone my version check, frozen the plugin at its current version to keep support, and will check this manually on the actual version of Pillow in future before I switch over again. sorry for the trouble! (issue #1714)
* added a new `Tell original search page to select exit media when closing the media viewer` checkbox to `options->media viewer` (default on). this lets you turn off the behaviour where your exit media is selected in the thumbgrid when you exit a media viewer (issue #1712)
* the default value for `When maintenance physically deletes files, wait this many ms between each delete:` in `files and trash` is now 600ms, up from 250ms. if you are set to the old default of 250, the update will bump you up. furthermore, the widget in `files and trash` is now a rich time delta widget rather than just a ms integer spinner
* the 'are you sure you want to exit the program, these pages say they are not done' yes/no dialog now spawns with yes disabled for 1.2 seconds, just like the archive/delete filter confirmation, enough to jolt you out of an autopilot enter press

### default downloaders

* the safebooru parser is more careful about fetching valid associable source urls. it was previously juxtaposing the safebooru domain with non-https-having garbage
* added a thread parser for holotower
* deleted some parsers and url classes for long-defunct sites

### sidecar sorting

* sidecar objects no longer do a hardcoded sort of their strings before the export step. if you set a different sort via the 'processing' step's string processor, that's directly what will export to the destination
* all new sidecar objects now start with a--and all existing sidecar objects will update to get a new--processing step that does 'human text sort (asc)'. thus, all sidecars _should_ continue behaving pretty much as they were before, but if you don't want that, you can now edit it!

### actual vs ideal tags

* the right-click tag menu that shows current parents and siblings now shows the _ideal_ tag display space, rather than the _actual_. the difference between these two is the ideal is what your settings say whereas the actual is what the client currently has calculated as per _tags->sibling/parent sync->review current sync_. this guy was previously showing the actual calc, which was revealing confusing interim technical states after the preferences changed. I am not sure if this change is correct or helpful and suspect I'll need some better UI around here to quickly detect and explain a discrepancy
* updated the `/add_tags/get_siblings_and_parents` help to discuss that it fetches actual rather than ideal tags

### duplicates auto-resolution

* **the duplicates auto-resolution UI is all enabled**, and I've un-hidden the 'add rule' button. have fun with this new tech, but don't go crazy yet. I think pixel-duplicate pairs are now easy to solve if you have firm preferences about keeping exif etc..
* finished off a comparison rule for duplicates auto-resolution that tests things like 'A has more than 2x the num pixels as B'. it can test size, width, height, num_pixels, duration, and num_frames and supports equals, not equals, greater than, less than, approx equal (percentage or absolute), and you can set a coefficient (A has more than 2x filesize of B) and/or an absolute delta (A has more than 200 px more height than B)
* added two hardcoded comparison rules for 'A and B have the same/differing filetypes'. nice and simple way to ensure you are or aren't comparing like to like in a rule
* the one-file comparators can now do exif, icc profile, and human-readable metadata tests
* the 'add suggested rules' button now has three choices--the original pixel-duplicates jpeg/png one, and `pixel-perfect pairs - keep EXIF or ICC data` (eliminate pixel duplicate pairs of the same filetype where only one has Exif/ICC data) and `pixel-perfect pairs - eliminate bloat`, (eliminate pixel duplicate pairs of the same filetype where neither have EXIF/ICC data but one is smaller than the other)
* the 'action' column in the duplicates auto-resolution preview panels now tooltips to the full text. if this becomes like 100 tags and several URLs, you can now read it!
* although we can now poke at the easiest dupe pairs, I think we are still missing a puzzle piece to differentiate alternates from duplicates programatically, even on 'exact-match' searches. we either need cleverer and higher-resolution phashes or a comparison rule that does hardcoded pixel inspection and allows for 'A is &gt; 99.7% pixel-similar to B' in some semantically rich way so we can automatically differentiate jpeg artifacts from banners or watermarks or even colour-only costume changes. while better and perhaps colour-sensitive phashes may come one day, I am going to go for this pixel comparison tech. this will add render CPU cost to each pair decision, which is going to add some bumps to this whole workflow, particularly the preview window, but I suspected we'd have to do this so I've mostly built for it

### boring duplicates auto-resolution

* wrote unit tests for the new system predicate media-result-extraction system for the types it can currently extract
* wrote unit tests for the new relative pair file info comparator
* wrote unit tests for the new hardcoded filetype comparator
* wrote unit tests for the new one-file comparator capabilities
* the number test widget now emits value-changed signals
* fixed an issue where many system pred stubs, until now only appearing temporarily, would not serialise
* fixed an issue with the duplicates auto-resolution preview panel	 where the 'pass' list was not ordering correct for rules beyond the pixel dupe test rule
* fixed an issue where the duplicates auto-resolution dialog would not allow you to add more than one new rule per dialog session
* brushed up the auto-resolution help a bit

### boring cleanup

* moved the 'human text sort' stuff from `HydrusData` to `HydrusText`, and improved its sort reliability when strings differ on order of int/str
* merged the generic tag sort code into the human text sort system, since they were both doing the same thing. cleaned up some bad old ideas along the way
* fixed some bad old tag processing when generating thumbnail banners and the file has more than two tags of a particular namespace and at least one tag includes non-number data
* a bunch of places that have some text beside a widget, e.g. the 'show whole chains' checkbox in 'manage tag parents', now copy the tooltip from the widget itself to the text

## [Version 618](https://github.com/hydrusnetwork/hydrus/releases/tag/v618)

### misc

* fixed the tag import options setup on 'force metadata refresh'. sorry, I broke this by accident last week!
* the weird 'always show system:everything, even if you have more than 10k files' (default off) checkbox under the 'file search' options panel is now replaced with a simpler 'show system:everything' (default on). once users get more experienced, they can turn this off themselves when they notice it. existing users will upgrade to get an appropriate value--if you currently see system:everything, it should default to True to you
* the crazy 'hide inbox and archive system predicates if either has no files' option, also under 'file search', is removed. this produces more confusion than value
* gave my top-level help and getting started index pages a pass, making it plainer and more concise for new users and clearing out some unneeded waffling/cringe and defunct or advanced info (the tumblr contact link still had an 'rss' alternate link, lol)
* fixed an issue where the simple downloader would be unable to resume a parsing job that never finished in a previous session (e.g. if you had network traffic paused). in this case, the gallery result would sit unresolved in the gallery log; the job is now only removed from the pending jobs queue, and the gallery log entry only saved to the log, once the job is complete
* if the user has the 'archived file delete lock' on, file maintenance jobs that check for missing/incorrect files now recognise if a record to be deleted is delete-locked and now just send the file to the trash instead. you get a different popup letting you know what happened, and the log maps out what happened too if you need to do sophisticated recovery. it sounds backwards to deny the deletion of a record for a file that does not actually exist, but I will not budge on the delete lock--trying to write exceptions is only going to tie us in knots (issue #1706)
* when repairing the client file storage system, or when doing 'move files now', if the source folder has been stored in the file system as an absolute path despite being beneath the db folder, the system now recognises this and recovers. if neither portable nor absolute path worked (i.e. some very odd path normalisation has happened), the system now stops what it was doing and raises an appropriate error. previously, it was possible to get your client into a situation where it would have doubled-up entries for certain prefixes. this whole system could do with a revamp, I think, especially when I get back to background file migration
* reworked the last check, last file, and next check column sorts in manage subscription(s) dialogs. the various 'not initialised yet' values were sorting as very old rather than imminent

### ipfs update

* I have done a pass over the IPFS service in hydrus, catching it up to what their modern daemon's API wants. if you use a new version of IPFS, hydrus should be able to pin directories again. if you use an old version of IPFS, update it please
* most importantly, I have removed the `nocopy` feature. the way we did the symlink redirect trick is not supposed to work on modern IPFS. this was always crazy and experimental, so for KISS reasons I will no longer support it
* I have also removed the native IPFS multihash download from the client. there were a couple of really obscure ways to launch this rickety old download process that could even spawn a tree selection dialog for picking which files in a directory you wanted to get. it was a big mess and a threading nightmare. all IPFS daemons offer web access to multihashes, so if we want this tech back, I think I want to make a downloader and/or URL Class or something instead, and maybe add like 'parse multihash' content update routine, so we can use all the nice downloader UI instead. you can also, of course, just paste an IPFS direct file URL straight into an url downloader and it should work
* the 'pin new directory' command is fixed!! (issue #1710)
* if you update your IPFS daemon a lot (as I did this week), I am uncertain if existing pins or directory pins will parse correct, and doubly so if there was nocopy stuff going on before. if nothing is working your end and you can't unpin-then-repin to fix it, I think the best solution is just to prep your currently pinned files in some search pages so you can find them again and then remove/re-add the ipfs service and basically tell hydrus to start over
* I gave the ipfs help a full pass, here: https://hydrusnetwork.github.io/hydrus/ipfs.html

### boring cleanup

* I replaced the last three hacky old duct-taped 'queue' listboxes (where you have a list of texts with up/delete/down buttons beside) with my integrated class that has some more bells and whistles, for instance reactive buttons that only enable when they can fire and selection preservation when you do up/down. the replaced widgets are: the one on the simple downloader page; the list of html parsing formula rules; the list of json parsing formula rules. no more pain in the neck as you reorder parse rules!!
* the 'queue' listbox now accepts delete key presses
* the 'queue listbox that can edit now only edits the top selected item
* the 'queue' listbox has some finer Qt signals working behind the scenes, too
* deleted some ancient and terrible data fetching and list manipulation functions that were originally from wx and are thankfully now no longer used
* fixed up some more layout flag transitions for my expand/collapse boxes. the IPFS shares box now starts off collapsed but expands to eat up space
