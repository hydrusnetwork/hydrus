---
title: Changelog
---

# changelog

!!! note
    This is the new changelog, only the most recent builds. For all versions, see the [old changelog](old_changelog.html).

## [Version 522](https://github.com/hydrusnetwork/hydrus/releases/tag/v522)

### notes in sidecars

* the sidecars system now supports notes!
* my sidecars only support univariate rows atm (a list of strings, rather than, say, a list of pairs of strings), so I had to make a decision how to handle note names. if I reworked the pipeline to handle multivariate data, it would take weeks; if I incorporated explicit names into the sidecar object, it would have made 'get/export all my notes' awkward or impossible and not solved the storage problem; so I have compromised in this first version by choosing to import/export everything and merging the name and text into the same row. it expects/says 'name: text' for input and output. let me know what you think. I may revisit this, depending on how it goes
* I added a note to the sidecars help about this special 'name: text' rule along with a couple ideas for tricky situations

### misc

* added 'system:framerate' and 'system:number of frames' to the system predicate parser!
* I am undoing two changes to tag logic from last week: you can now have as many colons at the start of a tag as you like, and the content parser no longer tries to stop double-stacked namespaces. both of these were more trouble than they were worth. in related news, '::' is now a valid tag again, displaying as ':', and you can create ':blush:'-style tags by typing '::blush:'. I'm pretty sure these tags will autocomplete search awfully, so if you end up using something like this legit, let me know how it goes
* if you change the 'media/preview viewer uses its own volume' setting, the client now updates the UI sliders for this immediately, it doesn't need a client restart. the actual volume on the video also changes immediately
* when an mpv window is called to play media that has 'no audio', the mpv window is now explicitly muted. we'll see if this fixes an interesting issue where on one system, videos that have an audio channel with no sound, which hydrus detects as 'no audio', were causing cracks and pops and bursts of hellnoise in mpv (we suspect some sort of normalisation gain error)

### file safety with duplicate symlinked directory entries

* the main hydrus function that merges/mirrors files and directories now checks if the source and destination are the same location but with two different representations (e.g. a mapped drive and its network location). if so, to act as a final safety backstop, the mirror skips work and the merge throws an error. previously, if you wangled two entries for the same location into 'migrate database' and started a migration, it could cause file deletions!
* I've also updated my database migration routines to recognise and handle this situation explicitly. it now skips all file operations and just updates the location record instantly. it is now safe to have the same location twice in the dialog using different names, and to migrate from one to the other. the only bizzaro thing is if you look in the directory, it of course has boths' contents. as always though, I'll say make backups regularly, and sync them before you do any big changes like a migration--then if something goes wrong, you always have an up-to-date backup to roll back to
* the 'migrate database' dialog no longer chases the real path of what you give it. if you want to give it the mapped drive Z:, it'll take and remember it
* some related 'this is in the wrong place' recovery code handles these symlink situations better as well

### advanced new parsing tricks

* thanks to a clever user doing the heavy lifting, there are two neat but advanced additions to the downloader system
* first, the parsing system has a new content parser type, 'http headers', which lets you parse http headers to be used on subsequent downloads created by the parsing downloader object (e.g. next gallery page urls, file downloads from post pages, multi-file posts that split off to single post page urls). should be possible to wangle tokenized gallery searches and file downloads and some hacky login systems
* second, the string converter system now lets you calculate the normal hydrus hashes--md5, sha1, sha256, sha512--of any string (decoding it by utf-8), outputting hexadecimal

### http headers on the client api

* the client api now lets you see and edit the http headers (as under _network->data->review http headers_) for the global network context and specific domains. the commands are `/manage_headers/get_headers` and `/manage_headers/set_headers`
* if you have the 'Make a short-lived popup on cookie updates through the Client API' option set (under 'popups' options page), this now applies to these header changes too
* also debuting on the side is a 'network context' object in the `get_headers` response, confirming the domain you set for. this is an internal object that does domain location stuff all over. it isn't important here, but as we do more network domain setting editing, I expect we'll see more of this guy
* I added some some documentation for all this, as normal, to the client api help
* the labels and help around 'manage cookies' permission are now 'manage cookies and headers'
* the client api version is now 43
* the old `/manage_headers/set_user_agent` still works. ideally, please move to `set_headers`, since it isn't that complex, but no rush. I've made a job to delete it in a year
* while I was doing this, I realised get/set_cookies is pretty bad. I hate their old 'just spam tuples' approach. I've slowly been replacing this stuff with nicer named JSON Objects as is more typical in APIs and is easier to update, so I expect I'll overhaul them at some point

### boring cleanup

* gave the about window a pass. it now runs on the newer scrolling panel system using my hydrus UI objects (so e.g. the hyperlink now opens on a custom browser command, if you need it), says what platform you are on and whether you are source/build/app, and the version info lines are cleaned a little
* fixed/cleaned some bad code all around http header management
* wrote some unit tests for http headers in the client api
* wrote some unit tests for notes in sidecars

## [Version 521](https://github.com/hydrusnetwork/hydrus/releases/tag/v521)

### some tag presentation

* building on last week's custom sibling connector, if you don't like the fade you can now override the 'namespace' colour of the sibling connector if you like
* you can also set the ' OR ' connector text
* and you can set the OR connector's 'namespace' colour. it was 'system' before
* also turned off the new namespace colour fading for OR predicates, where it was unintentionally kicking in and looking horrible lol

### misc

* added a checkbox to 'file viewing statistcs' to turn off tracking for the archive/delete filter, if you don't like that
* file viewing statistics now maxes out at five times a duration-having media's duration, if that is more than your max view time
* the simple version of the file delete dialog will now never overwrite a file deletion reason if all of the to-be-deleted files already have deletion reasons (e.g. when physically deleting trash)	
* the advanced version of the dialog now always selects 'keep existing reason' or 'do not alter existing reasons' when they exist, regardless of your 'remember previous reason' action. also, the 'remember previous reason' saved reason no longer updates if 'keep existing reason' or 'do not alter existing reasons' is set--it will stick on whatever it was before
* I might have fixed a height-layout bug in the petition management page

### advanced change to unnamespaced tags and their parsing

* the rule that allows ':p' as a tag (by secretly storing it as '::p') has been expanded--now any unnamespaced tag can include a colon as long as it starts with an explicit colon, which in hydrus rendering contexts is usually hidden. you can now type these in simply by beginning your tag with ':'--the secret character will be quickly swallowed
* for the parsing system, content parsers that get tags can now decide whether to set an explicit namespace or not. from now on, content parsers that are set to get unnamespaced tags will force all tags they get to be unnamespaced! this stops some site that has incidental colons in their 'subtags' from spamming twenty different new namespaces to hydrus. to preserve old parser behaviour, all existing content parsers that were left blank (no namespace) will be updated to not set an explicit namespace. if you are a parser maker, please consider whether you want to go with 'unnamespaced' or 'any namespace' going forward in your parsers--since most places don't use the hydrus 'namespace:subtag' format, I suspect when we want to make the decision, we'll want 'unnamespaced'
* I updated the pixiv parser to specifically ask for unnamespaced tags when parsing regular user tags, since it has some of these colon-having tags
* as a side thing, extra colons are now collapsed at the start of a tag--anything that starts with four colons will be collapsed down to two, with one displaying to humans
* also, during parsing, if a content parser gets a tag and the subtag already starts with its namespace, it will no longer double the namespace. parse 'character:dave' with namespace set to 'character', it will no longer produce 'character:character:dave'

### advanced file domain and file import options stuff

* all import pages that need to consult their file domain now do so on a 'realised' version of 'default file import options', so if you are set to import to 'my imports', and you open a new page from a tag or some thumbs on that import page, the new file page will be set to 'my imports', not some weird 'my files' stub value (in clients that deleted 'my files', this would be 'initialising...' forever)
* more stages of the file import process 'realise' default file import options stubs, just in case more of these problems slip through in future (e.g. in my file import unit tests, which I just discovered were all broken)
* the 'default' file import options stub is now initialised with your first local file domain rather than 'my files', so if this thing is ever still consulted anywhere, it should serve as a better last resort
* also fixed the file domain button getting stuck on 'initialising' if it starts with an empty file domain
* when you open the edit file import options dialog on a 'default' FIO and switch to a non-default, it now fills in all the details with the current LOUD FIO

### boring cleanup

* extracted the master file search method (~1800 lines of code) from the monolithic database object and into its own module. then broke several sub-pieces like rating or note searching code out into that module and cleaned misc stuff along the way. not done by any means, but this was a big db-cleanup hump
* reshuffled all the page management objects so they no longer keep an explicit copy of their current file domain--now they always consult their respective sub-objects, whether that is a file search or an importer or what. any time a page needs to consult its file domain, it'll always get the live and sensible version. as above, they also 'realise' default file import options stubs
* broke the 'getting started with tags' help page into two and straddled the 'getting started with searching' page with them. the intention is to get users typing a few tags into their first import pages, just that, and then playing around with them in search, before moving on to more complicated tag subjects
* split the 'autocomplete' section of the 'search' options into two, for read/write a/c contexts, and the default file and tag domain options have been moved there from 'files and trash' and 'tags'

## [Version 520](https://github.com/hydrusnetwork/hydrus/releases/tag/v520)

### autocomplete

* in autocomplete dropdowns, the advanced 'all known files' file domain now generally appears as 'all known files with tags'. the way file+tag search works here has been obscure and confusing for a long time; now the label specifically says what's going on
* to complement 'all known files with tags', all users now see a new 'all files ever imported/deleted', which is what most people actually want when they try 'all known files'. this quick-select entry for 'currently in or deleted from all my files' will run super quick in almost all cases and allows 'all known tags'!
* the new 'preserve selection between prefetch and full results' behaviour in tag autocomplete no longer applies if you have 'select the first item with count' turned on. these things just don't play well together
* that 'select the first item with count' option is now available in the manage tags dialog's cog icon too
* the 'edit' autocomplete tag search should be better about shuffling the top results. it now tries to put 'ideal of what you entered' at the very top (if that differs from what you typed), then what you actually typed (with or without count), and no longer shuffles other siblings to the top--while they are still included in the results, they weren't so helpful being spammed to the top every time!
* any search predicate that has a wildcard asterisk in its namespace is now coloured by default as the 'namespaced tags' fallback colour. this includes the somewhat new (any namespace) search tags. behind the scenes, the colour I assign is for a namespace of just '\*', so you can set your own colour if you like
* the different 'edit tags' autocomplete panels that have paste buttons--in manage siblings, manage parents, filename tagging, tag import options, and favourite tag management--are now all 'add only'. if any of the tags you are pasting already exist in the list, they now won't be removed

### misc

* the '(displays as xxx)' sibling suffix is shortened to a simpler unicode arrow, " → ". if you don't like it, you can edit it under _options->tag presentation_!
* I also went full meme and made the sibling connecting block's background colour a gradient on Qt6 (and lol the unselected text is a gradient too, but you need to alter it to something longer to really see). if you don't like it, you can turn it off in the same place! I also tweaked some of the padding sizes here so the different text blocks line up a little nicer
* thanks to a user's continued good work, I am rolling in another update to the Deviant Art file downloader that can grab the 'original quality' file from the logged-in-only download button that some artists turn on. furthermore, there are five new 'File URL' classes for the different qualities the file urls represent, which will propagate to all of your existing DA files, be searchable with system:known url, and hence allow you to find the medium/original/whatever quality versions that you have. now, not every 'medium quality' post on the site has the 'original' download button, but if you are an advanced user with a long DA download history, then with a bit of magic wand waving with your file import options, you can set up an url downloader for a one-time rescan that'll check and redownload your favourite mediums' URLs, or the mediums you know will have 'original quality', for that better version--try it in a small batch first, and let me know what you discover!
* fixed note content update pipeline so it can handle various instances of multiple notes with the same name coming in at once. previously it would pseudorandomly pick one and discard the others, now it does all the normal '(1)' renaming rules (and even note text extension merging, and hopefully in a good reliable order) as it goes through them
* if you are a madlad, you can now boost the 'prefetch previous/next' options under 'speed and memory' up to 50 either way. a new label complains if you set them too high given your current image cache size
* the file maintenance system now catches serious IOErrors, which usually suggest big deal hard drive problems, give the user a special popup message, and stops all future file maintenance work that boot
* the file maintenance system is better at stopping work for program shutdown while in the midst of a larger batch job
* fixed the second 'current and pending' label on 'migrate tags'--the new action was 'pending only' as intended, the bad label was just a stupid copy/paste typo
* thanks to a detailed user report, fixed multiple broken internal #anchor links in the help

### repository

* (both server and client need to be updated to get this)
* last week's 'delete all content' command failed IRL. it locked up the PTR for six hours and then appeared to fail (rollback) on a seemingly normal account. I am not sure what the inefficiency was here, but this job obviously has to be re-thought for real world use, so this week I am altering the command to break the job up into smaller pieces and stop safely after twenty seconds of work. the janitor client will receive a message on whether everything was deleted or not
* this is not a total solution or a nice solution, but it should be a stopgap that still allows deletion of small accounts' content while not breaking for big accounts. the ultimate answer here is going to look like proper account content-count caching (rather than the '5000 mappings' limit), and an asynchronous 'purge' maintenance system that runs in the background that janitor clients can check up on and even cancel

## [Version 519](https://github.com/hydrusnetwork/hydrus/releases/tag/v519)

### inc/dec ratings service

* I have written a new number 'rating' service type, called 'inc/dec'. it is simply a no-upper-limit positive integer--you left-click to increment, right to decrement. middle-click to edit directly
* it appears and works like other ratings in the top-right media viewer hover and the manage ratings dialog. there's a section under system:ratings too. the main logical difference is every file is always rated in this system--the default for all files is 0--so there's no searching for 'unrated'
* the duplicate merge options support this new inc/dec rating by adding/summing in one or both directions. its action labels in the dialog are a little different because of this

### misc

* the manage tag siblings dialog now shows all members of a chain when it filters the current in-view pairs according to the current pertinent tags. previously, it just showed the pairs that included your entered tags; now it chases everything
* the same is also now broadly true of manage tag parents, but there's a checkbox that sets how crazy it goes. by default it won't pursue 'cousins', since that can make a really overwhelming list (imagine seeing every character nintendo ever created, including every pokemon, when you just wanted to add a samus costume variant). more work can and will be done here, also with sibling-cross referencing
* the system:ratings panel now lists the groups of rating services in alphabetical order
* fixed an issue where the hydrus native animation renderer was drawing animations at small size in the top-left with garbled surrounds when the monitor UI scale was >100% (issue #1334)
* I think I have hacked an ugly fix for the 'this window keeps growing horizontally until it reaches the width of the screen' bug that hits some people. the sizing code is now supposed to recognise when this happens and stop it in place. if you get this problem, let me know if it is fixed or what! (issue #1331)
* if a file in the duplicate filter (or any other media viewer, if you can wangle it) has a 'show action' of 'do not show in the media viewer' or 'do not show, open externally on thumbnail activate', the media viewer now falls back to 'show open externally button'. previously, it was halting in an ugly state and no longer able to proceed (issue #1329)
* if repository processing runs into any missing/invalid file trouble, it now queues up a wider array of potential file maintenance jobs, assuming there may be a problem with the file records themselves
* if, during repository processing, an update file is missing, the error note now asks users to run _database->maintenance->clear orphan file records_. might be that the above fix helps here too, but this will be the sledgehammer solution on top, clearing up unusual cases where one service thinks the files exist when actually they don't
* fixed the recent 'when ffmpeg can't generate a video thumb, use hydrus thumb' routine to cover more situations
* thanks to a user, fixed a bunch of unit tests for python 3.11

### misc cleanup

* updated my async updater object to handle some pre-call UI-side argument-construction and cleaned up some related garbage shared memory hacks I had before
* in a step towards less laggy sibling/parents dialogs, I have moved the 'manage tag siblings' dialog's list-filtering routine to a thread. I'll do parents too, sometime, and plan to eventually move to very fast on-demand existing-pair fetching based on the above lookup rule improvements rather than the super laggy 'load everything on dialog boot' current system. a next big step would obviously be visual graph representation of sibling and parent chains
* cleaned some ratings code and fixed some weird little bugs like numerical rating tooltips not updating properly after a click
* added some unit tests for inc/dec ratings

### server admin

* (the server and client both need to be updated to get this)
* I updated and reinstated the old 'superban' function for janitors! it is now just 'delete all account content' on the account modification dialog, separate from the banning process. note that since the server only remembers account ownership of content through the anonymisation period, it cannot auto-remove content older than that date!
* the account info you see in the modify account dialog now only shows file count/bytes for file repositories and tag counts for tag repositories. to improve readability, it also shows every key/value pair on a separate line, sorted by keys
* that account info now shows, for tag repositories, number of current, pending, and petitioned sibling and parent rows, and it shows number of petitioned mapping rows. all this stuff obviously goes to 0 if you hit 'delete all account content'--let me know if any of it doesn't!
* the modify accounts dialog no longer shows the 'null' account type as a choice to set things to. duh! its yes/no also now confirms the account type you are settting
* all the commands in the modify accounts dialog now have nicer yes/no dialogs that say the number of accounts being affected and talk more about what is happening
* fixed up some logical jank in the dialog. adding time to expires no longer tells you about 0 accounts having no expiry, and if circumstances mean 0 accounts are selected/valid for an operation, it no longer says 'want to set expiry for 0 accounts?' etc...
* when modifying multiple accounts, the current account focus/selection is now preserved through list refreshes after jobs go through

## [Version 518](https://github.com/hydrusnetwork/hydrus/releases/tag/v518)

### autocomplete improvements

* tl;dr: I went through the whole tag autocomplete search pipeline, cleaned out the cruft, and made the pre-fetch results more sensible. searching for tags on thumbnails isn't horrible any more!
* -
* when you type a tag search, either in search or edit autocomplete contexts, and it needs to spend some time reading from the database, the search now always does the 'exact match' search first on what you typed. if you type in 'cat', it will show 'cat' and 'species:cat' and 'character:cat' and anything else that matches 'cat' exactly, with counts, and easy to select, while you are waiting for the full autocomplete results to come back
* in edit contexts, this exact-matching pre-fetch results here now include sibling suggestions, even if the results have no count
* in edit contexts, the full results should more reliably include sibling suggestions, including those with no count. in some situations ('all known tags'), there may be too many siblings, so let me know!
* the main predicate sorting method now sorts by string secondarily, stabilising the sort between same-count preds
* when the results list transitions from pre-fetch results to full results, your current selection is now preserved!!! selecting and then hitting enter right when the full results come in should be safe now!
* when you type on a set of full results and it quickly filters down on the results cache to a smaller result, it now preserves selection. I'm not sure how totally useful this will be, but I did it anyway. hitting backspace and filtering 'up' will reset selection
* when you search for tags on a page of thumbnails, you should now get some early results super fast! these results are lacking sibling data and will be replaced with the better answer soon after, but if you want something simple, they'll work! no more waiting ages for anything on thumbnail tag searches!
* fixed an issue where the edit autocomplete was not caching results properly when you had the 'unnamespaced input gives (any namespace) wildcard results' option on
* the different loading states of autocomplete all now have clear 'loading...' labels, and each label is a little different based on what it is doing, like 'loading sibling data...'
* I generally cleared out jank. as the results move from one type to another, or as they filter down as you type, they _should_ flicker less
* added a new gui debug mode to force a three second delay on all autocomplete database jobs, to help simulate slow searches and play with the above
* NOTE: autocomplete has a heap of weird options under _tags->manage tag display and search_. I'm really happy with the above changes, but I messed around with the result injection rules, so I may have broken one of the combinations of wildcard rules here. let me know how you get on and I'll fix anything that I busted.

### pympler

* hydrus now optionally uses 'pympler', a python memory profiling library. for now, it replaces my old python gc (garbage collection) summarising commands under _help->debug->memory actions_, and gives much nicer formatting and now various estimates of actual memory use. this is a first version that mostly just replicates old behaviour, but I added a 'spam a more accurate total mem size of all the Qt widgets' in there too. I will keep developing this in future. we should be able to track some memory leaks better in future
* pympler is now in all the requirements.txts, so if you run from source and want to play with it, please reinstall your venv and you'll be sorted. _help->about_ says whether you have it or not

### misc

* the system:time predicates now allow you to specify the hh:mm time on the calendar control. if needed, you can now easily search for files viewed between 10pm-11:30pm yesterday. all existing 'date' system predicates will update to midnight. if you are a time-search nerd, note this changes the precision of existing time predicates--previously they searched _before/after_ the given date, but now they search including the given date, pivoting around the minute (default: 0:00am) rather than the integer calendar day! 'same day as' remains the same, though--midnight to midnight of the given calendar day
* if hydrus has previously initial-booted without mpv available and so set the media view options for video/animations/audio to 'show with native viewer', and you then boot with mpv available, hydrus now sets your view options to use mpv and gives a popup saying so. trying to get mpv to work should be a bit easier to test now, since it'll popup and fix itself as soon as you get it working, and people who never realised it was missing and fix it accidentally will now get sorted without having to do anything extra
* made some small speed and memory optimisations to content processing for busy clients with large sessions, particularly those with large collect-by'd pages
* also boosted the speed of the content update pipeline as it consults which files are affected by which update object
* the migrate tags dialog now lets you filter the tag source by pending only on tag repositories
* cleaned up some calendar/time code
* updated the Client API help on how Hydrus-Client-API-Access-Key works in GET vs POST arguments
* patched the legacy use of 'service_names_to_tags' in `/add_urls/add_url` in the client api. this parameter is more obsolete than the other legacy names (it got renamed a while ago to 'service_names_to_additional_tags'), but I'm supporting it again, just for a bit, for Hydrus Companion users stuck on an older version. sorry for the trouble here, this missed my legacy checks!

### windows mpv test

* hey, if you are an advanced windows user and want to run a test for me, please rename your mpv-2.dll to .old and then get this https://sourceforge.net/projects/mpv-player-windows/files/libmpv/mpv-dev-x86_64-20230212-git-a40958c.7z/download . extract the libmpv-2.dll and rename it to mpv-2.dll. does it work for you, showing api v2.1 in _help->about_? are you running the built windows release, or from source? it runs great for me from source, but I'd like to get a wider canvas before I update it for everyone. if it doesn't work, then delete the new dll and rename the .old back, and then let me know your windows version etc.., thank you!

## [Version 517](https://github.com/hydrusnetwork/hydrus/releases/tag/v517)

### misc

* thanks to a user, export folders finally support exporting to symlinks!
* if a symlink export-create fails on Windows, the error now tells you to try again in 'run as Admin' mode--seems like this is needed in Win 10+ unless you mess with Group Policy Editor
* 'related tags' should no longer suggest sibling ideals or parents of existing tags! I think!
* when a thumbnail fails to load, the error popup now has a button to open the specific problem-causing file in a new page
* generation of video thumbnails is faster, should fail less in odd cases, and when it completely fails, it now gives the hydrus icon as a final fallback
* generation of image thumbnails now falls back to the hydrus icon as a final fallback
* I think I fixed a focus logic problem where the autocomplete dropdowns on the duplicate filter page would hide if you clicked a results/favourites tab or greyspace
* fixed an error when seeking an mpv video while the video was loading or unloading
* the max 'nullification period' (after which uploads to a hydrus repository are anonymised) is raised from 1 year to 5 (needs server and client update to work)

### transparency and duplicate filter

* two new options, under _media_ and _duplicates_, now control if you would like transpararency-having images to have a checkerboard background rather than the normal media canvas background! you can have it on all the time or just under the duplicate filter. it uses the same style of grid as MPV
* I have a plan for proper native (non-MPV) transparency for gifs and apng, but I think I'll wait for an imagemagick plugin I am planning first
* if you have a white/black media viewer background and prefer not to use the checkerboard, the duplicate filter can now adjust the background colour, either lighter or darker, for both A and B of the pair. altering A as well exposes truly transparent-having images vs ones with opaque white/black fill, which will otherwise blend into a purely white/black background colour. these options are available in the options dialog and the duplicate filter right-hand hover window cog button
* the native image window, embed button, and animation window (with PIL gif rendering) now all adjust their background colour to any odd changes like the duplicate filter's A/B lighten/darken adjustment

### boring cleanup

* cleaned up how popup file buttons are set and cleared
* cleaned up how popup main and secondary texts are set and cleared
* misc linting cleanup

## [Version 516](https://github.com/hydrusnetwork/hydrus/releases/tag/v516)

### misc

* the 'manage sidecar routers' control, which is on manage import folders, manage export folders, path-tagging-before-manual-import, and manual export files, now has import/export/duplicate buttons. you can save and transfer your work now! if you try to import 'export to sidecar' routers to an 'import from sidecar' context or _vice versa_, it should give you a nicely worded error
* fixed the error that was raising when you turn related tags off with the suggestions set to side-by-side layout. very sorry for the trouble!
* apngs that are set to 'loop x times' (usually once) now only loop that many times, on both mpv and my native renderer! like gifs, the 'always loop animations' setting under _options->media_ overrides it!
* fixed an issue with my native renderer not updating on scanbar scrubs very well. should be back to nice smooth instant draw as you scrub
* thanks to a user, folded in another deviant art parser update to the defaults
* updated the setuptools version in the requirements.txt due to a security note--I don't think the problem (which was about some vulnerable regex when fetching malicious package info) applies to us, but running from source users might like to run setup_venv again this week anyway

### related tags

* a new 'concurrence threshold' setting under _options->tag suggestions_ allows you to set how 'strict' the related tags search is. a higher percentage causes fewer but more relevant results. I'm increasing the default this week from 4% to 6%
* two new 'namespace to weight' settings under _options->tag suggestions_ now manage how much weight the 'search' and 'suggestion' sides of related tags have. you can say 'rank the suggestions from character tags highly' or 'rank unnamespaced suggestions lower', and 'do not search x tags' and 'do not suggest y tags'. I have prepped it with some 'creator/character/series namespaces are better than unnamespaced, and title/filename/page/chapter/volume are useless' defaults, but feel free to play around with it
* the related tags algorithm takes a larger sample now, resulting in a _little_ less ranking-variability

### client api

* changed and fixed an issue in the client api's new `get_file_relationships` call. previously, I said 'king' would be null if it was not on the given file domain, but this was not working correctly--it was giving pseudorandom 'fallback' kings. now it always gives the king, no matter what! a new param, `king_is_on_file_domain` says whether the king is on the given domain. `king_is_local` says whether the king is available on disk
* added some discussion and a list of the 8 possible 'better than' and 'same quality' logical combinations to the `set_file_relationships` help so you can see how group merge involving non-kings works
* client api is now version 42

## [Version 515](https://github.com/hydrusnetwork/hydrus/releases/tag/v515)

### related tags

* I worked on last week's related tags algorithm test, bringing it up to usable standard. the old buttons now use the new algorithm exclusively. all users now get 'related tags' showing in manage tags by default (if you don't like it, you can turn it off under _options->tag suggestions_)
* the new algorithm has new cancel tech and does a 'work for 600ms' kind of deal, like the old system, and the last-minute blocks from last week are gone--it will search as much as it has time for, including partial results. it also won't lag you out for thirty seconds (unless you tell it to in the options). it searches tags with low count first, so don't worry if it doesn't get to everything--'1girl' usually doesn't have a huge amount extra to offer once everything else has run
* it also uses 'hydev actually thought about this' statistical sampling tech to work massively faster on larger-count tags at the cost of some variance in rank and the odd false positive (considered sufficiently related when it actually shouldn't meet the threshold) nearer the bottom end of the tags result list
* rather than 'new 1' and 'new 2', there is now an on/off button for searching your local files or all known files on tag repositories. 'all known files' = great results, but very slow, which the tooltip explains
* there's also a new status label that will tell you when it is searching and how well the search went (e.g. '12/51 tags searched fully in 459ms')
* I also added the 'quick' search button back in, since we can now repeat searches for just selections of tags
* I fixed a couple typos in the algorthim that were messing some results
* in the manage tags dialog, if you have the suggested tag panels 'side-to-side', they now go in named boxes
* in the manage tags dialog, if you have suggested tag panels in a notebook, 'related tags' will only refresh its search on a media change event (including dialog initialisation) when it is the selected page. it won't lag you from the background!
* options->tag suggestions now lets you pick which notebook'd tag suggestions page you want to show by default. this defaults to 'related'
* I have more plans here. these related tags results are very cachable, so that's an obvious next step to speed up results, and when I have done some other long-term tag improvements elsewhere in the program, I'll be able to quickly filter out unhelpful sibling and parent suggestions. more immediately, I think we'll want some options for namespace weighting (e.g. 'series:' tags' suggestions could have higher rank than 'smile'), so we can tune things a bit

### misc

* the 'open externally' canvas widget, which shows any available thumbnail of the flash or psd or whatever, now sizes itself correctly and draws the thumbnail nicely if you set the new thumbnail supersampling option to >100%. if your thumbnail is the wrong size (and probably in a queue to be regenerated soon), I _think_ it'll still make the window too big/small, but it'll draw the thumbnail to fit
* if a tag content update comes in with an invalid tag (such as could happen with sidecars recently), the client now heals better. the bad tag is corrected live in more places, and this should be propagated to the UI. if you got a warning about 'you have invalid tags in view' recently but running the routine found no problems, please reboot, and I think you'll be fixed. I'm pretty sure the database wasn't being damaged at all here (it has cleaning safeguards, so it _shouldn't_ be possible to actually save bad tags)--it was just a thing to do with the UI not being told of the cleaned tag, and it shouldn't happen again. thank you for the reports! (issue #1324)
* export folders and the file maintenance dialog no longer apply the implicit system:limit (defaults to max 10k files) to their searches!
* old OR predicates that you load with saved searches and similar should now always have alphebetised components, and if you double-click them to remove them, they will now clear correctly (previously, they were doing something similar to the recent filetype problem, where instead of recognising themselves and deleting, they would instead duplicate a normalised (sorted) copy of themselves)
* thanks to a user, updated the recently note-and-ai-updated pixiv parser again to grab the canonical pixiv URL and translated tags, if present
* thanks to a user, updated the sankaku parser to grab some more tags
* the file location context and tag context buttons under tag autocompletes now put menu separators between each type of file/tag service in their menus. for basic users, this'll be a separator for every row, but for advanced users with multiple local domains, it will help categorise the list a bit

## [Version 514](https://github.com/hydrusnetwork/hydrus/releases/tag/v514)

### downloaders

* twitter took down the API we were using, breaking all our nice twitter downloaders! argh!
* a user has figured out a basic new downloader that grabs the tweets amongst the first twenty tweets-and-retweets of an account. yes, only the first twenty max, and usually fewer. because this is a big change, the client will ask about it when you update. if you have some complicated situation where you are working on the old default twitter downloaders and don't want them deleted, you can select 'no' on the dialog it throws up, but everyone else wants to say 'yes'. then check your twitter subs: make sure they moved to the new downloader, and you probably want to make them check more frequently too.
* given the rate of changes at twitter, I think we can expect more changes and blocks in future. I don't know whether nitter will be viable alternative, so if the artists you like end up on a nice simple booru _anywhere_, I strongly recommend just moving there. twitter appears to be explicitly moving to non-third-party-friendly
* thanks to a user's work, the 'danbooru - get webm ugoira' parser is fixed!
* thanks to a user's work, the deviant art parser is updated to get the highest res image in more situations!
* thanks to a user's work, the pixiv downloader now gets the artist note, in japanese (and translated, if there is one), and a 'medium:ai generated' tag!

### sidecars

* I wrote some sidecar help here! https://hydrusnetwork.github.io/hydrus/advanced_sidecars.html
* when the client parses files for import, the 'does this look like a sidecar?' test now also checks that the base component of the base filename (e.g. 'Image123' from 'Image123.jpg.txt') actually appears in the list of non-txt/json/xml ext files. a random yo.txt file out of nowhere will now be inspected in case it is secretly a jpeg again, for good or ill
* when you drop some files on the client, the number of files skipped because they looked like sidecars is now stated in the status label
* fixed a typo bug that meant tags imported from sidecars were not being properly cleaned, despite preview appearance otherwise, for instance ':)', which in hydrus needs to be secretly stored as '::)' was being imported as ')'
* as a special case, tags that in hydrus are secretly '::)' will be converted to ':)' on export to sidecar too, the inverse of the above problem. there may be some other tag cleaning quirks to undo here, so let me know what you run into

### related tags overhaul

* the 'related tags' suggestion system, turned on under _options->tag suggestions_, has several changes, including some prototype tech I'd love feedback on
* first off, there are two new search buttons, 'new 1' and 'new 2' ('2' is available on repositories only).. these use an upgraded statistical search and scoring system that a user worked on and sent in. I have butchered his specific namespace searching system to something more general/flexible and easy for me to maintain, but it works better and more comprehensibly than my old method! give it a go and let me know how each button does--the first one will be fast but less useful on the PTR, the second will be slower but generally give richer results (although it cannot do tags with too-high count)
* the new search routine works on multiple files, so 'related tags' now shows on tag dialogs launched from a selection of thumbnails!
* also, all the related search buttons now search any selection of tags you make!!! so if you can't remember that character's name, just click on the series or another character they are often with and hit the search, and you should get a whole bunch appear
* I am going to keep working on this in the future. the new buttons will become the only buttons, I'll try and mitigate the prototype search limitations, add some cancel tech, move to a time-based search length like the current buttons, and I'll add more settings, including for filtering so we aren't looking up related tags for 'page:x' and so on. I'm interested in knowing how you get on with IRL data. are there too many recommendations (is the tolerance too high?)? is the sorting good (is the stuff at the top relevant or often just noise?)?

### misc

* all users can now copy their service keys (which are a technical non-changing hex identifier for your client's services) from the review services window--advanced mode is no longer needed. this may be useful as the client api transitions to service keys
* when a job in the downloader search log generates new jobs (e.g. fetches the next page), the new job(s) are now inserted after the parent. previously, they were appended to the end of the list. this changes how ngugs operate, converting their searches from interleaved to sequential!
* restarting search log jobs now also places the new job after the restarted job
* when you create a new export folder, if you have default metadata export sidecar settings from a previous manual file export, the program now asks if you want those for the new export folder or an empty list. previously, it just assigned the saved default, which could be jarring if it was saved from ages ago
* added a migration guide to the running from source help. also brushed up some language and fixed a bunch of borked title weights in that document
* the max initial and periodic file limits in subscriptions is now 50k when in advanced mode. I can't promise that would be nice though!
* the file history chart no longer says that inbox and delete time tracking are new

### misc fixes

* fixed a cursor type detection test that was stopping the cursor from hiding immediately when you do a media viewer drag in Qt6
* fixed an issue where 'clear deletion record' calls were not deleting from the newer 'all my files' domain. the erroneous extra records will be searched for and scrubbed on update
* fixed the issue where if you had the new 'unnamespaced input gives (any namespace) wildcard results' search option on, you couldn't add any novel tags in WRITE autocomplete contexts like 'manage tags'!!! it could only offer the automatically converted wildcard tags as suggested input, which of course aren't appropriate for a WRITE context. the way I ultimately fixed this was horrible; the whole thing needs more work to deal with clever logic like this better, so let me know if you get any more trouble here
* I think I fixed an infinite hang when trying to add certain siblings in manage tag siblings. I believe this was occuring when the dialog was testing if the new pair would create a loop when the sibling structure already contains a loop. now it throws up a message and breaks the test
* fixed an issue where certain system:filetype predicates would spawn apparent duplicates of themselves instead of removing on double-click. images+audio+video+swf+pdf was one example. it was a 'all the image types' vs 'list of (all the) image types' conversion/comparison/sorting issue

### client api

* **this is later than I expected, but as was planned last year, I am clearing up several obsolete parameters and data structures this week. mostly it is bad service name-identification that seemed simple or flexible to support but just added maintenance debt, induced bad implementation practises, and hindered future expansions. if you have a custom api script, please read on--and if you have not yet moved to the alternatives, do so before updating!**
* **all `...service_name...` parameters are officially obsolete! they will still work via some legacy hacks, so old scripts shouldn't break, but they are no longer documented. please move to the `...service_key...` alternates as soon as reasonably possible (check out `/get_services` if you need to learn about service keys)**
* **`/add_tags/get_tag_services` is removed! use `/get_services` instead!**
* **`hide_service_names_tags`, previously made default true, is removed and its data structures `service_names_to_statuses_to_...` are also gone! move to the new `tags` structure.**
* **`hide_service_keys_tags` is now default true. it will be removed in 4 weeks or so. same deal as with `service_names_to_statuses_to_...`--move to `tags`**
* **`system_inbox` and `system_archive` are removed from `/get_files/search_files`! just use 'system:inbox/archive' in the tags list**
* **the 'set_file_relationships' command from last week has been reworked to have a nicer Object parameter with a new name. please check the updated help!** normally I wouldn't change something so quick, but we are still in early prototype, so I'm ok shifting it (and the old method still works lmao, but I'll clear that code out in a few weeks, so please move over--the Object will be much nicer to expand in future, which I forgot about in v513)
* many Client API commands now support modern file domain objects, meaning you can search a UNION of file services and 'deleted-from' file services. affected commands are
* * /add_files/delete_files
* * /add_files/undelete_files
* * /add_tags/search_tags
* * /get_files/search_files
* * /manage_file_relationships/get_everything
* a new `/get_service` call now lets you ask about an individual service by service name or service key, basically a parameterised /get_services
* the `/manage_pages/get_pages` and `/manage_pages/get_page_info` calls now give the `page_state`, a new enum that says if the page is ready, initialised, searching, or search-cancelled
* to reduce duplicate argument spam, the client api help now specifies the complicated 'these files' and now 'this file domain' arguments into sub-sections, and the commands that use them just point to the subsections. check it out--it makes sense when you look at it.
* `/add_tags/add_tags` now raises 400 if you give an invalid content action (e.g. pending to a local tag service). previously it skipped these rows silently
* added and updated unit tests and help for the above changes
* client api version is now 41

### boring optimisation

* when you are looking at a search log or file log, if entries are added, removed, or moved around, all the log entries that have changed row # now update (previously it just sent a redraw signal for the new rows, not the second-order affected rows that were shuffled up/down. many access routines for these logs are sped up
* file log status checking is completely rewritten. the ways it searches, caches and optimises the 'which is the next item with x status' queues is faster and requires far less maintenance. large import queues have less overhead, so the in and outs of general download work should scale up much better now
* the main data cache that stores rendered images, image tiles, and thumbnails now maintains itself far more efficiently. there was a hellish O(n) overhead when adding or removing an item which has been reduced to constant time. this gonk was being spammed every few minutes during normal memory maintenance, when hundreds of thumbs can be purged at once. clients with tens of thousands of thumbnails in memory will maintain that list far more smoothly
* physical file delete is now more efficient, requiring far fewer hard drive hits to delete a media file. it is also far less aggressive, with a new setting in _options->files and trash_ that sets how long to wait between individual file deletes, default 250ms. before, it was full LFG mode with minor delays every hundred/thousand jobs, and since it takes a write lock, it was lagging out thumbnail load when hitting a lot of work. the daemon here also shuts down faster if caught working during program shut down

### boring code cleanup

* refactored some parsing routines to be more flexible
* added some more dictionary and enum type testing to the client api parameter parsing routines. error messages should be better!
* improved how `/add_tags/add_tags` parsing works. ensuring both access methods check all types and report nicer errors
* cleaned up the `/search_files/file_metadata` call's parsing, moving to the new generalised method and smoothing out some old code flow. it now checks hashes against the last search, too
* cleaned up `/manage_pages/add_files` similarly
* cleaned up how tag services are parsed and their errors reported in the client api
* the client api is better about processing the file identifiers you give it in the same order you gave
* fixed bad 'potentials_search_type'/'search_type' inconsistency in the client api help examples
* obviously a bunch of client api unit test and help cleanup to account for the obsolete stuff and various other changes here
* updated a bunch of the client api unit tests to handle some of the new parsing
* fixed the remaining 'randomly fail due to complex counting logic' potential count unit tests. turns out there were like seven more of them

## [Version 513](https://github.com/hydrusnetwork/hydrus/releases/tag/v513)

### client api

* the Client API now supports the duplicates system! this is early stages, and what I've exposed is ugly and technical, but if you want to try out some external dupe processing, give it a go and let me know what you think! (issue #347)
* a new 'manage file relationships' permission gives your api keys access
* the new GET commands are:
* - `/manage_file_relationships/get_file_relationships`, which fetches potential dupes, dupes, alternates, false positives, and dupe kings
* - `/manage_file_relationships/get_potentials_count`, which can take two file searches, a potential dupes search type, a pixel match type, and max hamming distance, and will give the number of potential pairs in that domain
* - `/manage_file_relationships/get_potential_pairs`, which takes the same params as count and a `max_num_pairs` and gives you a batch of pairs to process, just like the dupe filter
* - `/manage_file_relationships/get_random_potentials`, which takes the same params as count and gives you some hashes just like the 'show some random potential pairs' button
* the new POST commands are:
* - `/manage_file_relationships/set_file_relationships`, which sets potential/dupe/alternate/false positive relationships between file pairs with some optional content merge and file deletes
* - `/manage_file_relationships/set_kings`, which sets duplicate group kings
* more commands will be written in the future for various remove/dissolve actions
* wrote unit tests for all the commands!
* wrote help for all the commands!
* fixed an issue in the '/manage_pages/get_pages' call where the response data structure was saying 'focused' instead of 'selected' for 'page of pages'
* cilent api version is now 40

### boring misc cleanup and refactoring

* cleaned and wrote some more parsing methods for the api to support duplicate search tech and reduce copypasted parsing code
* renamed the client api permission labels a little, just making it all clearer and line up better. also, the 'edit client permissions' dialog now sorts the permissions
* reordered and renamed the dev help headers in the same way
* simple but significant rename-refactoring in file duplicates database module, tearing off the old 'Duplicates' prefixes to every method ha ha
* updated the advanced Windows 'running from source' help to talk more about VC build tools. some old scripts don't seem to work any more in Win 11, but you also don't really need it any more (I moved to a new dev machine this week so had to set everything up again)
