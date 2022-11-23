---
title: Changelog
---

# changelog

!!! note
    This is the new changelog, only the most recent builds. For all versions, see the [old changelog](old_changelog.html).

## [Version 507](https://github.com/hydrusnetwork/hydrus/releases/tag/v506)

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
