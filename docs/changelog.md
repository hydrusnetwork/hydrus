---
title: Changelog
---

# changelog

!!! note
    This is the new changelog, only the most recent builds. For all versions, see the [old changelog](old_changelog.html).

## [Version 509](https://github.com/hydrusnetwork/hydrus/releases/tag/v509)

### misc

* added an option 'mouse wheel can "scroll" through menu buttons' to _options->gui_. this turns off the behaviour where a mouse wheel event over, for instance, the file sort asc/desc button, will change the button's value rather than scrolling the underlying panel. if you found this annoying, you can finally turn it off!
* fixed an annoying 'save service' bug that some users saw last week with the introduction of serverside Tag Filters. some users had an old datatype in their service data storage--a legacy issue--but the system now coerces all datatypes and direct sub-objects to a saveable format on load or update
* the tag washing system now collapses more types of whitespace character to `space`. mostly this means tab is now converted to space, but some unicode stuff goes too
* the hangul filler character `\u3164` is no longer permitted as a namespace or subtag. it can be in longer tags, but isn't allowed on its own (where it appears to be a blank space). (hydev saw one in the wild, probably from some cheeky post title)
* let me know if you run across a newly invalid tag already in your system and the UI goes bananas--ideally hydrus should now catch this and either fix itself or report with a polite note, but let's see. if things go crazy, run _database->check and repair->fix invaliid tags_
* improved some image transparency detection and slicing logic. it is more accurate and saves more memory now. also, the system that saves thumbnails will more reliably use jpegs when it doesn't need png's transparency
* fixed some PSD thumbs showing a fully transparent transparency layer
* fixed a bug where you could enter capital letters into the namespace colour list in 'tag presentation' options panel
* the default twitter downloaders are all renamed to remove the confusing and technical 'syndication' label
* 'speedcopy' is now an optional supported library. a couple users have suggested this to make network copies on Windows and Linux much faster. I'd like some advanced users who run from source to try adding it to their venvs, and we'll see how it works out IRL in different situations (you can see if it is loaded under _help->about_)
* if you run from source, the 'advanced' setup route now offers a (t)est Qt install, which sets PySide6 6.4.1 (up from 6.3.21). feel free to try it out--it works well for me, but I want to test it more before trying to roll it to the releases
* in a side thing, thanks to the user who walked me through setting up signed commits to github with my own PGP key. you can see my new key in the contacts help page, id 76249F053212133C, and I am now committing with it. I'm not very familiar with the sheer mechanics of this tech, so bear with me, but I'm pretty sure I can sign or encrypt something if ever needed

### macOS build fix

* since v505, many macOS users were unable to boot the built app. it has taken multiple rounds of back and forth with users, but we figured it out. (looks like pyoxidizer updating from 0.22.0 to 0.23.0 simply broke qtpy/Qt bindings, so we force a rollback this week)
* also, the macOS app moves from PySide6 to PyQt6 this week. they are basically the same, but PyQt6 packages into a 258MB dmg, less than half the 548MB PySide6 one!
* let me know if the macOS app gives any more trouble. otherwise, to the people who helped out here, thank you very much for the help!

### mostly boring tag filter panel

* removed the 'add' buttons; added 'delete' buttons to the simple whitelist and blacklist panels; added 'block everything' to simple blacklist panel
* the panel now talks about the special sibling and namespace rules when you edit an explicit blacklist-mode-only filter (the tag import options blacklist works this way)
* the 'you didn't need to add that exception' text and 'filter is too complicated for this panel' texts now show/hide rather than waste empty space
* some of the simple-advanced interactions are better, but there's still some logical bork here. mostly stuff like when you hit the 'unnamespace' checkbox in the whitelist panel, it gets needlessly added to the 'except' column in the advanced, rather than just removed from the advanced 'exclude'. I'll fix this up in the near future
* the two namespace checkbox lists are now sized more appropriately
* the white/blacklist panels disable more simply and reliably

### boring cleanup

* the confusing 'view this file's duplicates' menu label, which was an artifact of an old submenu label, is removed. if the duplicate menu wants to present the 'view' commands for two locations, it'll title with the respective location, otherwise the commands speak for themselves, no label
* some old 'check(er) timings' nomenclature is renamed to 'checker options' across the board
* the hydrus serialisable dictionary now washes any nested lists or dicts to hydrus serialised equivalents, which should stop situations like the save service bug in future
* the hydrus serialisable list can now handle a mix of hydrus serialisables and python primitives. it also washes its lists or dicts to serialisable equivalents
* improved the data-stability of some image channel slicing
* fixed some PIL fallback thumbnail generation, and improved its 'has transparency' png/jpeg decision-making
* fixed the main thumbnail loader being confused at times about which thumbnail mime to load with. the check I have added is ultra-fast on data we are loading anyway, so we shouldn't notice a difference, but if you get slow thumb loads, let me know
* fixed the media container embed buttons using the file mime rather than the thumb mime when loading thumbnails (again causing transparency issues)
* fixed more generally bad mime handling in the thumbnail generation routine that could have caused more unusual transparency handling for clip, psd, or flash files

## [Version 508](https://github.com/hydrusnetwork/hydrus/releases/tag/v508)

### misc

* added a shortcut action to the 'media' set for 'file relationships: show x', where x is duplicates, potential duplicates, alternates, or false positives, just like the action buried in the thumbnail right-click menu. this actually works in both thumbs and the canvas.
* fixed file deletes not getting processed in the duplicate filter when there were no normal duplicate actions committed in a batch. sorry for the trouble here--duplicate decisions and deletes are now counted and reported in the confirmation dialogs as separate numbers
* as an experiment, the duplicate filter now says (+50%, -33%) percentage differences in the file size comparison statement. while the numbers here are correct, I'm not sure if this is helpful or awkward. maybe it should be phrased differently--let me know
* url classes get two new checkboxes this week: 'do not allow any extra path components/parameters', which will stop a match if the testee URL is 'longer' than the url class's definition. this should help with some difficult 'path-nested URLs aren't matching to the right URL Class' problems
* when you import hard drive files manually or in an import folder, files with .txt, .json, or .xml suffixes are now ignored in the file scanning phase. when hydrus eventually supports text files and arbitrary files, the solution will be nicer here, but this patch makes the new sidecar system nicer to work with in the meantime without, I hope, causing too much other fuss
* the 'tags' button in the advanced-mode 'sort files' control now hides/shows based on the sort type. also, the asc/desc button now hides/shows when it is invalid (filetype, hash, random), rather than disable/enable. there was a bit more signals-cleanup behind the scenes here too
* updated the 'could not set up qtpy/QtCore' error handling yet again to try to figure out this macOS App boot problem some users are getting. the error handling now says what the initial QT_API env variable was and tries to import every possible Qt and prints the whole error for each. hopefully we'll now see why PySide6 is not loading
* cleaned up the 'old changelog' page. all the '.' separators are replaced with proper header tags and I rejiggered some of the ul and li elements to interleave better. its favicon is also fixed. btw if you want to edit 500-odd elements at a time in a 2MB document, PyCharm is mostly great. multi-hundred simultaneous edit hung for about five minutes per character, but multiline regex Find and Replace was instant
* added a link to a user-written guide for running Hydrus on Windows in Anaconda to the 'installing' help
* fixed some old/invalid dialog locations in the 'how to build a downloader' help

### client api

* a new `/get_files/file_hashes` command lets you look up any of the sha256, md5, sha1, sha512 hashes that hydrus knows about using any of the other hashes. if you have a bunch of md5 and want to figure out if you have them, or if you want to get the md5s of your files and run them against an external check, this is now possible
* added help and unit tests for this new command
* added a service enum to the `/get_services` Client API help
* client api version is now 37
* as a side thing, I rejiggered the 'what non-sha256 hash do these sha256 hashes have?' test here. it now returns a mapping, allowing for more efficient mass lookups, and it no longer creates new sha256 records for novel hashes. feel free to spam this on new sha256 hashes if you like

### interesting serverside

* the tag repository now manages a tag filter. admins with 'modify options' permission can alter it under the new menu command _services->administrate services->tag repo->edit tag filter_.
* any time new tags are pended to the tag repository, they are now washed through the tag filter. any that don't pass are silently discarded
* normal users will regularly fetch the tag filter as long as their client is relatively new. they can review it under a new read-only Tag Filter panel from _review services_. if their client is super old (or the server), account sync and the UI should fail gracefully
* if you are in advanced mode and your client account-syncs and discovers the tag filter has changed, it will make a popup with a summary of the changes. I am not sure how spammy/annoying this will be, so let me know if you'd rather turn them off or auto-hide after two hours or something
* future updates will have more feedback on _manage tags_ dialog and similar, just to let you know there and then if an entered tag is not wanted. also, admins who change the tag filter will be able to retroactively remove tags that apply to the filter, not just stop new ones. I'd also like some sibling hard-replace to go along with this, so we don't accidentalyl remove tags that are otherwise sibling'd to be good--we'll see
* the hydrus server won't bug out so much at unusual errors now. previously, I ingrained that any error during any request would kick off automatic delays, but I have rejiggered it a bit so this mostly just happens during automatic work like update downloading

### boring serverside

* added get/set and similar to the tag repo's until-now-untouched tag filter
* wrote a nice helper method that splays two tag filters into their added/changed/deleted rules and another that can present that in human-readable format. it prints to the server log whenever a human changes the tag filter, and will be used in future retroactive syncing
* cleaned up how the service options are delivered to the client. previously, there would have been a version desync pain if I had ever updated the tag filter internal version. now, the service options delivered to the client are limited to python primitives, atm just update period and nullification period, and tag filter and other complex objects will have their own get calls and fail in quiet isolation
* I fixed some borked nullification period initialisation serverside
* whenever a tag filter describes itself, if either black or whitelist have more than 12 rules, it now summarises rather than listing every single one

## [Version 507](https://github.com/hydrusnetwork/hydrus/releases/tag/v507)

### misc

* fixed an issue where you could set 'all known tags' in the media-tag exporter box in the sidecars system
* if a media-tag exporter in the sidecars system is set to an invalid (missing) tag service, the dialog now protests when you try to OK it. also, when you boot into this dialog, it will now moan about the invalid service. also, new media-tag exporters will always start with a valid local tag service.
* Qt import error states are handled better. when the client boots, the various 'could not find Qt' errors at different qtpy and QtCore import stages are now handled separately. the Qt selected by qtpy, if any, is reported, as is the state of QT_API and whether hydrus thought it was importable. it seems like there have been a couple of users caught by something like system-wide QT_API env variables here, which this should reveal better in boot-crash logs from now on
* all the new setup scripts in the base directory now push their location as the new CWD when they start, and they pop back to your original when they exit. you should be able to call them from anywhere now!
* I've written a 'setup_desktop.sh' install script for Linux users to 'install' a hydrus.desktop file for the current install location to your applications directory. thanks to the user who made the original hydrus.desktop file for the help here
* I fixed the focus when you open a 'edit predicate' panel that only has buttons, like 'has audio'/'no audio'. top button should have focus again, so you can hit enter quick
* added updated link to hydownloader on the client api page

### dupes apply better to groups of thumbs

* tl;dr: when the user sets a 'copy both ways' duplicate file status on more than two thumbnails, the duplicate metadata merge options are applied better now
* advanced explanation: previously, all merge updates were calculated before applying the updates, so when applied to a group of interconnected relationships, the nodes that were not directly connected to each other were not syncing data. now, all merge updates are calculated and applied to each pair in turn, and then the whole batch is repeated once more, ensuring two-way transitivity. for instance, if you are set to copy tags in both directions and set 'A is the best' of three files 'ABC', and B has tag 'x' and C has 'y', then previously A would get 'x' and 'y', but B would not get 'y' and C would not get 'x'. now, A gets 'x' before the AC merge is calculated, so A and C get x, and then the whole operation is repeated, so when AB is re-calculated, B now gets 'y' from the updated A. same thing if you set to archive if either file is archived--now that archived status will propagate across the whole group in one action

### client api

* the new 'tags' structure in `/get_files/file_metadata` now has the 'all known tags' service's tags
* the 'file_services' structure in `/get_files/file_metadata` now states service name, type, and pretty type, like 'tags'
* `/get_services` now says the service `type` and `type_pretty`, like 'tags'. `/get_services` may be reformatted to a service_key key'd Object at some point, since it uses an old custom human-readable service type as Object key atm and I'd rather we move to the same labels and references for everything, but we'll see
* updated the client api help with more example result data for the above changes (and other stuff like 'all my files')
* updated the client api unit tests to deal with the above changes
* client api version is now 36

### server/janitor improvements

* I recommend server admins update their servers this week! everything old still works, but jannies who update have new abilities that won't work until you update
* the petition processing page now has an 'account id' text field. paste an account id in there, and you'll get the petition counts just for that account! the petitions requested will also only be for that account!
* if you get a 404 on a 'get petition' call (either due to another janitor clearing the last, or from a server count cache miscount), it no longer throws an error. instead, a popup appears for five seconds saying 'hey, there wasn't one after all, please hit refresh counts'

### boring server improvements

* refactored the account-fetching routine a little. some behind the scenes account identifier code, which determines an account from a mapping or file record, is now cleaner and more cleanly separated from the 'fetch account from account key' calls. account key is the master account identifier henceforth, and any content lookups will look up the account key and then do normal account lookup after. I will clean this further in the near future
* a new server call looks up the account key from a content object explicitly; this will get more use in future
* all the 'get number of x' server calls now support 'get number of x made by y' for account-specific counting. these numbers aren't cached, but should be fairly quick for janitorial purposes
* same deal for petitions, the server can now fetch petitions by a particular user, if any
* added/updated unit tests for these changes
* general server code cleanup

## [Version 506](https://github.com/hydrusnetwork/hydrus/releases/tag/v506)

### misc

* the thumbnail/media viewer's right-click menu now shows all known modified dates for a file (under the top row submenu). any file downloaded in the past few months should have some extra ones, and you can see how the aggregate number is the reasonable minimum of what you have
* added media viewer shortcut actions for 'zoom: 100/canvas fit/default'
* like with the recent system:time update, the system:rating dialog now has nicer labels for the different numerical operators, saying 'more than' instead of '>' and so on
* also on system:rating, the the 'rated' and 'not rated' choices are now folded into the main radio buttons. to say 'is rated in some way', select 'has rating.' to say 'not rated', set 'is' and make the rating blank. to not search that rating, select 'do not search'. I've wired up the click events here a little, too, to flip from 'do not search' to 'is' when you click and so on
* to make it a little easier to get to, the 'view this file's relationships' submenu is bumped up a level, and the parent 'file relationships' menu is moved above the viewing stats row
* thanks to a user, the install_dir/static dir now has an example hydrus.desktop file for Linux users. feel free to play around with it. the user taught me how this stuff works, so I'm going to try to integrate it into my setup scripts in the near future
* I think I fixed a bug where on rare occasion the client would take 30 seconds to close while waiting on a random daemon like 'sleep check'
* I undid last week's Windows auto-darkmode detection in a hotfix. thanks to the users who quickly notified me that this wasn't working well enough IRL. it is now opt-in, using launch parameter `--win_qt_darkmode_test`, and it applies darkmode 1 rather than 2. if there are no problems with this, then I will make 1 default and 2 opt-in, so let me know how it goes
* the new Windows taskbar grouping identifier now only applies to the source version of the program. if you pinned the built exe to the taskbar, it was not grouping on that pin (issues #1273, #1271)
* added a custom popup message if a subscription query comes up DEAD on the first sync. it was previously firing off the 'didn't find anything on first sync' error by accident
* when you ok the manage options dialog, if you didn't change the thumbnail size, the thumbnail grids across the program no longer purge and regen
* when you ok the manage options dialog, if you changed the media view options, the image tile cache now clears itself
* when you ok the manage options dialog, if the set mpv.conf content hasn't changed, mpv is no longer told to reload it

### sidecar paths

* sidecars get more options regarding their file paths. it is all collected in a new 'sidecar filename' box in the normal metadata routing UI, either for sidecar importers or exporters
* first off, a checkbox now allows you to remove the source media file's extension from the sidecar. with 'my_image.jpg', this would change the default sidecar path from 'my_image.jpg.txt' to 'my_image.txt'. I've heard the the new AI/ML artist .txt outputters use this!
* secondly, an ADVANCED String Converter button lets you go bananas and convert the sidecar path to whatever you need using regexes or whatever
* and lastly, it now has live test/result UI so you can put in an example media path and see what the sidecar will be. this thing is populated with sensible defaults and updates the string converter button's internal example text if you change things
* I added some unit tests for these new features

### client api

* the `/get_files/file_metadata` call has several expansions: 
* a new `tags` structure shows all a file's tags in a neater, combined way. it can do everything the 'service_blah_to_blah_tags' structures do while still giving all information efficiently. please migrate to using this structure within the next eight weeks
* `hide_service_names_tags` is now default True and deprecated. if you are still using it, please move off it; I will remove it in four weeks
* added `hide_service_keys_tags` to do similar. it is default False for now, but I will make it True in four weeks and then delete it four weeks later just like `names`
* the `time_modified` value is now the aggregated modified timestamp, not the local file modified timestamp
* the new `time_modified_details` value is an Object of domain : timestamp for all known modified timestamps, by domain
* added `thumbnail_width` and `thumbnail_height` for files that have proper thumbnails. they are a reliable prediction, but not a promise
* added `is_deleted`, which refers to whether the file is either in the trash or has been fully deleted from the client
* added `has_exif`, `has_human_readable_embedded_metadata` and `has_icc_profile` to the metadata Object
* the unit tests have been updated to test these changes
* the help has been updated to reflect these changes. also fixed up some little 'you wouldn't actually get that' issues in the mega 'file_metadata' response example
* the client api version is now 35

### running from source

* if the venv activation fails in the setup script or launch script, they now stop there with an error message on all platforms
* linux and macOS setup scripts now look to use 'python3' for initial venv setup, falling back to 'python' if that does not exist
* updated the build scripts to always use 'python -m pip' instead of 'pip' or 'pip3' directly. this stops some weirder environments getting confused about which pip to use
* updated the running from source help with several clarifications and little fixes and notes users have contributed

### cleanup

* refactored some menu templating functions from the cluttered ClientGUIMedia and ClientGUIResults to the new ClientGUIMediaMenus
* for the new expanded modified dates stuff, cleaned up how the media 'pretty info lines' are sent to a menu
* replaced a crash-prone emergency-error-handling dialog hook in the database migration rebalance routine with a simple popup message
* cleaned up some bad type hints and other linter warnings
* cleaned up some canvas zoom code
* fixed another 'duplicates' unit test that would on rare occasion fail due to a too-specific test
* removed a no-longer needed token declaration from the github build script that was raising a warning

## [Version 505](https://github.com/hydrusnetwork/hydrus/releases/tag/v505)

### exif update

* the client now has the ability to check your image files for basic human-readable metadata. sometimes this is timing data for a gif, often it is something like DPI, and for many of the recent ML-generated pngs, this is the original generating prompt. this is now viewable in the same way as EXIF, on the same panel. since this (and future expansions) are not EXIF _per se_, the overarching UI around here is broadly renamed 'embedded metadata'
* the client now scans for and remembers if files have EXIF or human-readable embedded metadata. two predicates, 'system:image has exif' and 'system:image has human-readable embedded metadata' let you search for them. the vast majority of images have some sort of human-readable embedded metadata, so 'system:no human-readable embedded metadata' may typically be the more useful predicate in the latter case
* the system predicate parser can handle these new system preds
* to keep the system predicate list tidy, the new system preds are wrapped with 'has icc profile' into a meta-system predicate 'system:embedded metadata', like how 'system:dimensions' works
* the media viewer now knows ahead of time if a media has embedded metadata. the button in the media viewer's top hover window that shows this is no longer a cog but a little text-on-window image, and it now only appears if the file has data to show. the tooltip previews whether this is EXIF, other data, or both
* this knowledge is obviously now generated on file imports going forward, and new file maintenance jobs can retroactively scan for it
* all your existing image files and gifs/apngs are scheduled for this work. they will catch up in the background over the coming weeks
* the duplicate filter shows if one or both files have exif or other human-readable data. I had written off adding new 'scores' to the dupe filter panel until a full overhaul, but this was a simple copy/paste of the icc profile statement, so I snuck it in. also, these statements now only appear if for one image it is true and the other is false--no more 'they both have icc profiles m8', which is not a helpful comparison statement
* added some unit tests for this new tech
* a future expansion here will be to record the specific keys and values into the database so you can search specifically over those values (e.g. 'EXIF ISO level > 400', or 'has "parameters" text value')

### misc

* the 'reverse page drop shift behaviour' checkbox in _options->gui pages_ is replaced with four checkboxes. two govern whether page drops should chase the drop, either normally or with shift held down, and two new ones govern whether hydrus should dynamically navigate tabs as you move a media or page drag and drop over the tab bar. set them how you like!
* a new EXPERIMENTAL checkbox just beneath these lets you change what the mouse wheel does to a row of page tabs--by default, the wheel will change tab selection, but if you often have an overloaded row (i.e. they overspill the bar width and you see the left/right arrows), you can set the wheel to _scroll/pan the bar_ instead
* the 'if file is missing, remove record' job is now split into two--one that leaves no deletion record (old behaviour), and one that does (new). this new job lets you do some 'yes and I want it to stay gone' tasks like if you are syncing an old database backup to a newer client_files structure
* thanks to user pointing out what was needed, turned on a beta 'darkmode detection' in Qt for Windows. if you launch the client in official Windows 'Apps darkmode' (under Windows settings->Colors), it should now start with your system darkmode colours. switching between light and dark mode while the client is running is pretty buggy (also my Explorer windows are buggy at this too jej), but this is a step forward. fingers crossed this feature matures and gets reliable multiplatform support in future (issue #756)

### fixes

* thanks to a user, the twitter downloader is fixed. seems like twitter (maybe due to Elon's new team?) changed one tiny name in the API we use. let's see if they change anything more significant in the coming weeks (issue #1268)
* thanks to a user the 'gelbooru 0.1.11 file page parser' stops getting borked 'Rating: ' tags, and I fixed its source time fetch too. I'm pretty sure these broke because of the multiline string processing change a couple months ago, sorry for the trouble!
* fixed a recent stupid typo that broke the media viewer's do an edge pan' action (issue #1266)
* fixed an issue with the furry.booru.org url classes, which were normalising URLs to http rather than https for some accidental reason
* I finally figured out the weird bug where the colour picker dialog would sometimes treat mouse moves as mouse drags over the colour-selection gradient box. this is due to a bug in Qt6 where if you have a stylesheet with a certain hover value set, the colour picker goes bananas. I tried many things to fix this and finally settled on a sledgehammer: if you have the offending value in your stylesheet, it now does some stuff that takes a second or two of lag to launch the colour picker and a second or two of lag to exit it. sorry, but that fixes it! if you want to skip the lag in the options dialog, set your stylesheet to 'default' for the duration (issue #1260)
* fixed an issue where the new sidecar importer system was not correctly cleaning tags (removing extra whitespace, lowercasing) before committing them to the database! if you got hit with this, a simple restart should fix the incorrect labels (it wasn't _actually_ writing bad tags to the database), but if a restart does not fix it, please run _database->check and repair->fix invalid tags_ (issue #1264)
* fixed an issue opening the new metadata sidecar edit UI when you had removed and replaced the original 'my tags' service
* think I fixed a bug in the duplicate filter where if a file in the current pair is deleted (and removed from view), the index/pair tracking would desynchronise and cause an error if you attempted to rewind to the first pair
* I fixed the reported 'committable decisions' count for duplicate filters set to do no duplicate content merge at all

### build version woes

* all the builds now run on python 3.9 (Linux and Windows were 3.8 previously). any users on systems too old to run 3.9 are encouraged to run from source instead
* the linux build is rolled back to the older version of python-mpv. thanks to the users who helped me test this, and the specific user who let me know about the different version incompatibilities going on. basically we can't move to the new mpv on the Linux build for a little while, so the official release is rolling back to safe and stable. if you are on a newer Linux flavour, like 22.04, I recommend you pursue running from source, which is now easy on Linux
* I am considering, in let's say two or three months, no longer supporting the Linux build. we'll see how well the running from source easy-setup scripts work out, but if they aren't a hassle, that really is the proper way to do things on Linux, and it'll solve many crashes and mpv issues

### running from source is now simple and easy for everyone

* transcribed the setup .bat files in the base directory to .sh for linux users and .command for macOS users! the 'running from source' help is updated too. all users are now welcome to try it out!
* folded the 'setup_venv_qt5.bat' script into the main 'setup_venv.bat' script as a user choice for 'advanced' setup, and expanded it with prompts for qt5, mpv, and opencv
* the setup files now say your python version and guide you through all choices
* as Windows 8.1 users have reported problems with Qt6, the help and script recommendations on Qt5 are now <=8.1, not just 7. but it is easy to switch now, so if you want to play around, let me know what you discover

### boring running from source and help gubbins

* took the 'update' option out of the 'setup-venv.bat' script. this process was not doing what I thought it would and was not particularly useful. the script now always reinstalls after user hits Enter to continue, which is very reliable, gets newer versions of libraries when available, and almost always takes less than a minute
* updated the github readme and website index to point obviously and directly at the getting started guide
* took out some of the bloviating from the initial introduction page
* updated the running from source help to talk about the new advanced setup and added a couple extra warnings
* updated the running from source help to talk about Linux and macOS
* if qtpy is missing at the very start of the program, a new error catch asks the user if they installed and activated their venv correctly (should also catch people who run client.py right off the bat without reading the docs)
* deleted the old user-written help document about which packages to use with which Linux flavours, as the author says it is now out of date and modern pip as used by the scripts navigates it better nowadays
* the setup_venv.bat now checks and informs the user if they do not have python installed
* cleaned up the flow control of the batch files. more conditionals, fewer gotos
* to keep the base install dir clean, moved the 'advanced' setup script's cut-up requirements.txts to a new folder under static/requirements. if you are manually setting up a venv and need unusual libraries, check them out for known good specific versions, otherwise you are set with the basic requirements.txt
* to keep the install dir clean, moved the obscure 'build' requirements.txts to a new folder under static/requirements. these are mostly just notes for me when setting up a new test dev environment

### cleanup and other boring stuff

* as recommended by the pyopenssl page, I moved the server self-signed cert generation routine to 'cryptography' (which I'm pretty sure pyopenssl was just wrapping anyway). cryptography is added to the requirements.txt, but you should already have it. pyopenssl is still used by twisted, so it stays in the requirements.txts. both of these libraries remain optional and are only used by people hosting https services
* if you load up a favourite search, the focus no longer goes to the autocomplete text box right after. hydev liked most of the focus propagation changes here but found this one incredibly annoying
* when you are in profile mode and doing repository processing, the current speed is now printed regularly to the profile log to help see how fast the profiled jobs are at each step
* simplified some duplicate filter code
* the 'add tags/urls with the import' window now also shows 'cleaned' tags in the preview column for sidecar routers that go to tags
* added some extra help text and tooltips to the new sidecar exporter UI
* removed the weird '()' empty name component in .json exporters
* cleaned up the namespace colour list widget in options->tag presentation. it now has proper add and delete buttons
* refactored the colour picker button significantly and moved and merged its old wx patch code into the main object
* the duplicate filter handles 'cannot rewind' errors better, including if the first pair is no longer viewable
* pretty sure I fixed a long-time stupid hang in the unit tests that appeared occasionally after a 'favicon' fech test. it was due to a previous network engine shutdown test applying too broadly to test objects
* cleaned up some edge cases in the 'which account added this file/mapping to the server?' tech, where it might have been possible, when looking up deleted content, to get another janitor account (i.e. who deleted the content), although I am pretty sure this situation was never possible to actually start in UI. if I add 'who deleted this?' tech in future, it'll be a separate specific call
* cleaned up some specifically 'Qt6' references in the build script. the build requirements.txts and spec files are also collapsed down, with old Qt5 versions removed
* filled out some incomplete abstract class definitions

## [Version 504](https://github.com/hydrusnetwork/hydrus/releases/tag/v504)

### Qt5
* as a reminder, I am no longer supporting Qt5 with the official builds. if you are on Windows 7 (and I have heard at least one version of Win 8.1), or a similarly old OS, you likely cannot run the official builds now. if this is you, please check the 'running from source' guide in the help, which will allow you to keep updating the program. this process is now easy in Windows and should be similarly easy on other platforms soon

### misc
* if you run from source in windows, the program _should_ now have its own taskbar group  and use the correct hydrus icon. if you try and pin it to taskbar, it will revert to the 'python' icon, but you can give a shortcut to a batch file an icon and pin that to start
* unfortunately, I have to remove the 'deviant art tag search' downloader this week. they killed the old API we were using, and what remaining open date-paginated search results the site offers is obfuscated and tokenised (no permanent links), more than I could quickly unravel. other downloader creators are welcome to give it a go. if you have a subscription for a da tag search, it will likely complain on its next run. please pause it and try to capture the best artists from that search (until DA kill their free artist api, then who knows what will happen). the oauth/phone app menace marches on
* focus on the thumbnail panel is now preserved whenever it swaps out for another (like when you refresh the search)
* fixed an issue where cancelling service selection on database->c&r->repopulate truncated would create an empty modal message
* fixed a stupid typo in the recently changed server petition counting auto-fixing code

### importer/exporter sidecar expansion
* when you import or export files from/to disk, either manually or automatically, the option to pull or send tags to .txt files is now expanded:
* - you can now import or export URLs
* - you can now read or write .json files
* - you can now import from or export to multiple sidecars, and have multiple separate  pipelines
* - you can now give sidecar files suffixes, for ".tags.txt" and similar
* - you can now filter and transform all the strings in this pipeline using the powerful String Processor just like in the parsing system
* this affects manual imports, manual exports, import folders, and export folders. instead of smart .txt checkboxes, there's now a button leading to some nested dialogs to customise your 'routers' and, in manual imports, a new page tab in the 'add tags before import' window
* this bones of this system was already working in the background when I introduced it earlier this year, but now all components are exposed
* new export folders now start with the same default metadata migration as set in the last manual file export dialog
* this system will expand in future. most important is to add a 'favourites' system so you can easily save/load your different setups. then adding more content types (e.g. ratings) and .xml. I'd also like to add purely internal file-to-itself datatype transformation (e.g. pulling url:(url) tags and converting them to actual known urls, and vice versa)

### importer/exporter sidecar expansion (boring stuff)
* split the importer/exporter objects into separate importers and exporters. existing router objects will update and split their internal objects safely
* all objects in this system can now describe themselves
* all import/export nodes now produce appropriate example texts for string processing and parsing UI test panels
* Filename Tagging Options objects no longer track neighbouring .txt file importing, and their UI removes it too. Import Folders will suck their old data on update and convert to metadata routers
* wrote a json sidecar importer that takes a parsing formula
* wrote a json sidecar exporter that takes a list of dictionary names to export to. it will edit an existing file
* wrote some ui panels to edit single file metadata migration routers
* wrote some ui panels to edit single file metadata migration importers
* wrote some ui panels to edit single file metadata migration exporters
* updated edit export folder panel to use the new UI. it was already using a full static version of the system behind the scenes; now this is exposed and editable
* updated the manual file export panel to use the new UI. it was using a half version of the system before--now the default options are updated to the new router object and you can create multiple exports
* updated import folders to use the new UI. the filename tagging options no longer handles .txt, it is now on a separate button on the import folder
* updated manual file imports to use the new UI. the 'add tags before import' window now has a 'sidecars' page tab, which lets you edit metadata routers. it updates a path preview list live with what it expects to parse
* a full suite of new unit tests now checks the router, the four import nodes, and the four export nodes thoroughly
* renamed ClientExportingMetadata to ClientMetadataMigration and moved to the metadata module. refactored the importers, exporters, and shared methods to their own files in the same module
* created a gui.metadata module for the new router and metadata import/export widgets and panels
* created a gui.exporting module for the existing export folder and manual export gui code
* reworked some of the core importer/exporter objects and inheritance in clientmetadatamigration
* updated the HDDImport object and creation pipeline to handle metadata routers (as piped from the new sidecars tab)
* when the hdd import or import folder is set to delete original files, now all defined sidecars are deleted along with the media file
* cleaned up a bunch of related metadata importer/exporter code
* cleaned import folder code
* cleaned hdd importer code

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
