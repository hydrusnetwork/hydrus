---
title: Changelog
---

# changelog

!!! note
    This is the new changelog, only the most recent builds. For all versions, see the [old changelog](old_changelog.html).

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

## [Version 492](https://github.com/hydrusnetwork/hydrus/releases/tag/v492)

### sort and collect updates
* for big brain users, the collect control now has a tag domain button. it only shows if you are in advanced mode (issue #572)
* the sort control also has a tag domain button hidden behind advanced mode. it applies to system:num tags and namespace sorting
* the collect control now appears on all import pages

### archived file delete lock
* the duplicate processing action code now no longer archives files that are due for deletion right before that deletion. this was hitting the archive delete lock
* if archive delete lock is on and the 'other' file in the duplicate filter is archived, the option to 'this is better, delete the other' is now disabled
* if you attempt to delete a delete-locked file during normal browsing, or if an automatic system like export folders wants to but fails on some, a popup is now made with a button to show the files that were filtered out so you can review the situation and fix it if you want
* I am considering adding a dialog to say 'hey, this is locked, want to send back to inbox?' to fix these situations in a nice way, but I think this is probably a bad idea in terms of workflow, design, and my sanity given all the edge cases and potential future expansions of lock rules. maybe I'll add a simple 'delete and override lock checks' option, but a lock is a lock tbh. for now, I will focus on this better UI feedback of currently delete-locked files and make it simpler for humans to remove any locks

### misc
* using black magic, I have made it so the shortcuts for 'move left/right one page' 'and 'move home/end' do not dip down to the lowest level of a neighbouring page of pages for the next command. it now stays on the current tab level for three seconds after the most recent move command. this works in testing but may be jank in some IRL situations, so if this matters to you, let me know how it works out
* fixed a bug in 'do a full metadata resync' that meant unprocessed row orphans were not being deleted, which lead to lingering 1950/2000-style processed gauges that didn't actually cause any work to be done on 'process now'
* the duplicate filter now shows if one or both files have an icc profile. for now the score for this is always 0, neutral
* I think I have reduced general lag on some busy clients

### code cleaning and minor fixes
* refactored file viewing stats management to a new database module
* refactored file physical storage management to a new database module
* cleaned up an ugly bridge that made inbox/archive work and moved it all to a clean new separate database module
* improved some client file physical storage repair code, both in how it repairs and how it recovers in the current boot
* updated the yes/no dialog texts when you apply 'not related' or 'alternates' to a selection
* added a bunch of tooltips to the 'speed and memory' options panel. also clarified the example image sizes in number of pixels
* improved how my grid layout propagates tooltips from the widget to the text when the widget is compound and in its own layout
* consolidated where the delete lock test occurs to just one location for db, gui
* added infrastructure to filter and report delete-locked files. callers no longer care about specific lock rules, opening this up to future expansion
* cleaned and simplified some duplicate action processing code
* cleaned up some file collect code, optimised it a bit too
* the sort control now only changes sort type on mouse wheel events if the mouse is over that button
* renamed 'tag search context' to 'tag context' across the program, mirroring a recent change with the location context, and gave it some bells and whistles. in future, the tag context will hold multiple tag services
* wrote a new button to edit tag contexts

## [Version 491](https://github.com/hydrusnetwork/hydrus/releases/tag/v491)

### system predicates
* the advanced OR input, where you can type tags in complicated logical expressions, now supports system predicates! most system predicates are supported using their typical display strings. it uses the same engine as the client api, so check the examples here https://hydrusnetwork.github.io/hydrus/developer_api.html#get_files_search_files sorry for the delay here
* the advanced input also runs tags better through the hydrus tag 'cleaning' process, so things like whitespace between the namespace colon and the subtag are cleaned up correctly, and invalid tags should be excluded
* it also starts with the keyboard focus in the text input
* and I think I fixed an issue with '!'', 'not', or '-' negation prefixes not parsing
* highlighted the example parseable system predicate texts in the Client API help, and added 'last viewed' to it

### misc
* altering your services in _manage services_ no longer causes a full page refresh for all currently open search pages
* in a related thing, if you click the file or tag domain of a file search page to be the same as it just was, you no longer get a page refresh
* the rating widgets now show their current rating value on their tooltips
* when setting a numerical rating by a drag, it no longer matters if your mouse strays above or below the widget--it will still set
* the String Processing system has a new 'String Tag Filter' processing step. this applies the normal tag filtering object to your list of strings and also performs the hydrus 'tag cleaning' process on them, making them all lowercase and trimming whitespace and so on
* the sibling/parent sync is now even more polite when told to do work in 'normal' time. this has been hitting a lot of new users really hard, so it should now really trickle work during normal time, throttling down when it hits a bump to avoid stunlocking you but also responding quickly to recent changes if you are fully synced
* the database repair code is now better at healing damaged fast-text-search (FTS) tables. previously, in cases of partial damage to the virtual table, the repair code would error out
* fixed a bug where certain search predicate calendar dates that are acceptable in Linux but not in Windows caused Windows to fail to load the session. if you put in 1965 as a search date, it should now revert to the current time one next load etc...
* the test to see if a directory is writeable-to is improved and now handles Windows's Program Files directory correctly
* improved how the boot scripts handle incorrect/bad database directory paths. the error handling works better, and it figures out a fallback location for crash.log better
* a new button on 'review services' now lets advanced users copy the service key to the clipboard
* the migrate tags dialog now lists file repositories, ipfs services, and 'all my files' as potential file filter domains
* when checking it has space for a large transaction like a vacuum, hydrus now tries to check if you are running on a ramdisk or other severely space-limited temp dir and offers more text if this is true
* updated the '4chan style thread api parser' to handle posts with multiple files, which fixes tvchan.moe and probably anything else running NPFchan
* some logic testing around showing 'return to inbox' and the actual operation is fixed so it only applies to local files. in some weird advanced situations, you could previously send deleted files to inbox

### new import/export framework
* started a new modular metadata import/export pipeline. this thing starts out today by doing the work of newline-separated tags in a .txt sidecar file and will expand to do all sorts of metadata in other formats like JSON and XML. it will also, eventually, support arbitrary cross-type conversions like tags to urls or ratings to tags
* export folders now support '.txt' sidecar tag exporting!
* the '.txt' sidecar tag importing in import folders or manual imports is now handled by the new pipeline
* the '.txt' sidecar exporting in the manual export dialog is now handled by the new pipeline
* please expect the UI around '.txt' sidecar importing and exporting to change significantly in future. you'll be selecting different metadata types to import or export, make string processing steps to alter or filter what you get, and of course be able to compile it all into more complicated filetypes

### cleanup and refactoring
* mr bones gets two new columns to line up the numbers better
* a bunch of export code got moved around. created a new module 'exporting', and moved ClientExporting.py to it, renaming to ClientExportingFiles.py
* removed an old prototype for sidecar exporting and related plans for UI
* the 'missing file folders on boot' dialog now points users to 'help my media files are broke.txt'
* brushed up the 'help my x is broke.txt' documents in the database directory a little
* fixed some surplus double backslashes in the help
* a secret tiny label change/fix, let's see if anyone notices
* cleaned up how the rating widgets manage and update rating state. it was ancient bad code
* updated how different rating values are converted to UI text
* misc cleanup of some free space checking code
* fixed some bad quote characters in client api help JSON examples
* improved some error handling for uploading pending content and sped up file uploads a little

## [Version 490](https://github.com/hydrusnetwork/hydrus/releases/tag/v490)

### misc
* fixed a stupid bug that meant the image caches were initialising with default values (as under _speed and memory_) until you opened and OKed the options dialog (or did some other options-refresh events). sorry for the trouble, please enjoy some smoother image browsing.
* mr bones now shows more numbers, and in a neater table. it should be clearer what the percentages are for now, too
* the _manage->regenerate_ thumbnail menu has additional quick maintenance commands for presence and integrity checks and regenerating data in the similar files system
* wrote a new 'special duplicate' button for the edit shortcut set dialog. the list on this dialog doesn't allow duplicates (which meant the old 'duplicate' button was doing nothing), so this duplicates the current actions with 'incremented' shortcut keys. 'a' becomes 'b', 'ctrl+5' becomes 'ctrl+6', and so on. it doesn't always work, but if you want to make ten shortcuts for setting rating 1-10, this should help
* fixed an issue where the thumbnail banner text and the media viewer background text was not changing size or font according to QSS stylesheet rules (issue #1173)
* SIGTERM should now cause a clean program exit (previously it killed the GUI App but left some daemon threads alive for thirty seconds or more). unlike SIGINT, it will not ask you if you are sure you want to exit or if you would like to do shutdown maintenance--it just closes the client promptly
* fixed a bug in last week's importer page status improvements--the hard drive import page wasn't showing all the updates it should have
* brushed up some backup help

### file services
* fixed a bug where advanced users could set 'all known files'/'all known tags' on a search dropdown. this search domain is not supported
* in the archive/delete filter, if the current location is 'all my files' and the files being deleted are only in one local file domain, the surplus 'all my files' will no longer appear at the top of the filter's commit dialog
* the file services in the thumbnail select/remove menu are now sorted in the same order as the file domain button in search dropdowns
* the thumbnail select/remove menus now exclude 'all my files' and 'all local files' if those choices are redundant (e.g. if you only have files in 'my files', 'all my files' will be hidden)
* fixed some incorrect 'delete from x' actions appearing in thumbnail right-click menus

### orphan files
* there's a persistent processing bug some users have where some update files are missing but they won't redownload correctly. I think I fix that this week naturally so existing maintenance routines will now be able to fix it themselves after another round
* fixed some issues related to deleting files from the repository updates file domain.
* the 'clear orphan file records' maintenance command now fixes the 'all my files' umbrella services as well as the 'all local files' one. it also has nicer description, does some additional file-removal cleanup, and triggers a file recount if problems are found
* moved 'clear orphan files' to the 'files' maintenance menu

## [Version 489](https://github.com/hydrusnetwork/hydrus/releases/tag/v489)

### downloader pages
* greatly improved the status reporting for downloader pages. the way the little text updates on your file and gallery progress are generated and presented is overhauled, and tests are unified across the different downloader pages. you now get specific texts on all possible reasons the queue cannot currently process, such as the emergency pause states under the _network_ menu or specific info like hitting the file limit, and all the code involved here is much cleaner
* the 'working/pending' status, when you have a whole bunch of galleries or watchers wanting to run at the same time, is now calculated more reliably, and the UI will report 'waiting for a work slot' on pending jobs. no more blank pending!
* when you pause mid-job, the 'pausing - status' text is generated is a little neater too
* with luck, we'll also have fewer examples of 64KB of 503 error html spamming the UI
* any critical unhandled errors during importing proper now stop that queue until a client restart and make an appropriate status text and popup (in some situations, they previously could spam every thirty seconds)
* the simple downloader and urls downloader now support the 'delay work until later' error system. actual UI for status reporting on these downloaders remains limited, however
* a bunch of misc downloader page cleanup

### archive/delete
* the final 'commit/forget/back' confirmation dialog on the archive/delete filter now lists all the possible local file domains you could delete from with separate file counts and 'commit' buttons, including 'all my files' if there are multiple, defaulting to the parent page's location at the top of the list. this let's you do a 'yes, purge all these from everywhere' delete or a 'no, just from here' delete as needed and generally makes what is going on more visible
* fixed archive/delete commit for users with the 'archived file delete lock' turned on

### misc
* fixed a bug in the parsing sanity check that makes sure bad 'last modified' timestamps are not added. some ~1970-01-01 results were slipping through. on update, all modified dates within a week of this epoch will be retroactively removed
* the 'connection' panel in the options now lets you configure how many times a network request can retry connections and requests. the logic behind these values is improved, too--network jobs now count connection and request errors separately
* optimised the master tag update routine when you petition tags
* the Client API help for /add_tags/add_tags now clarifies that deleting a tag that does not exist _will_ make a change--it makes a deletion record
* thanks to a user, the 'getting started with files' help has had a pass
* I looked into memory bloat some users are seeing after media viewer use, but I couldn't reproduce it locally. I am now making a plan to finally integrate a memory profiler and add some memory debug UI so we can better see what is going on when a couple gigs suddenly appear

### important repository processing fixes
* I've been trying to chase down a persistent processing bug some users got, where no matter what resyncs or checks they do, a content update seems to be cast as a definition update. fingers crossed, I have finally fixed it this week. it turns out there was a bug near my 'is this a definition or a content update?' check that is used for auto-repair maintenance here (long story short, ffmpeg was false-positive discovering mpegs in json). whatever the case, I have scheduled all users for a repository update file metadata check, so with luck anyone with a bad record will be fixed automatically in the background within a few hours of background work. anyone who encounters this problem in future should be fixed by the automatic repair too. thank you very much to the patient users who sent in reports about this and worked with me to figure this out. please try processing again, and let me know if you still have any issues
* I also cleaned some of the maintenance code, and made it more aggressive, so 'do a full metadata resync' is now be even more uncompromising
* also, the repository updates file service gets a bit of cleanup. it seems some ghost files have snuck in there over time, and today their records are corrected. the bug that let this happen in the first place is also fixed
* there remains an issue where some users' clients have tried to hit the PTR with 404ing update file hashes. I am still investigating this
