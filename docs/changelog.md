---
title: Changelog
---

# changelog

!!! note
    This is the new changelog, only the most recent builds. For all versions, see the [old changelog](old_changelog.html).

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
