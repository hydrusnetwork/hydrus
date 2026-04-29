---
title: Import Options
---

!!! warning "THIS IS A DRAFT"
    This is a draft of a system not yet released! I am going to migrate the file/tag/note import options to a more granular system that allows favourites/templates.
    
    Feel free to read on and let me know what is confusing. We'll all be on this before June!

# Import Options

There are several ways to import files to hydrus, whether that is a drag-and-drop import from your hard drive, a downloader pulling from a site, or a file you push through the Client API. Imports may come with additional metadata like tags or URLs. Sometimes you want to grab everything, and sometimes you want to say 'only get the jpegs', or 'send just these tags here'.

We control how importers operate using "Import Options", which is an umbrella term for a selection of sub-options. Import Options are sophisticated and are designed to be set up ahead of time. You rarely touch them in normal operation.

!!! warning "tl;dr"
    This stuff can get crazy. If you are a new user, rest assured the default setup here is fine, and you do not need to learn all this ASAP. You never _need_ to learn this. You can just let stuff work and slowly dip your toes in if and when you need it to work differently. Some things you can do with this system are:
    
    - sending tags to different locations, force-adding tags
    - sending files to different locations, auto-archiving
    - skipping import based on file properties or tags
    
    So, feel free to ignore this page for now and come back if and when you have these sorts of needs.

If you would like to learn more now, then know that there are multiple types of Import Options attached to each file import:

- **Prefetch Import Options**: This tells a downloader whether to skip redownloading a recognised file or its metadata to save time. Use this when you need a downloader to force-fetch something.
- **File Filtering Import Options**: This tells an importer which types of files it should allow. Use this if you need to exclude very large files or similar.
- **Tag Filtering Import Options**: This tells an importer to blacklist/whitelist a file based on its tags. Use this if you need to stop all the files with tag x or only allow the files with tag y.
- **Location Import Options**: This tells an importer where to send files and if they should be auto-archived. Use this if you have multiple local file domains and need to place certain imports in a different location.
- **Tag Import Options**: This tells an importer where to send the tags a file may come with. Use this if your file downloader parses tags.
- **Note Import Options**: This tells an importer whether to save any parsed 'note' text that comes with a file. Use this if you want to shape how notes are added.
- **Presentation Import Options**: This tells an importer how to display the files it successfully imports in UI. Use this if you don't want to see, say, files that were already in your database.

Every single import has every one of these, but in many cases the specific options set will have nothing interesting to say or the import may not need to consult it. A local file import, from your hard drive, will not consider the Prefetch Import Options, for instance.

# The Defaults System

So, how are these Import Options set up for a particular file import? It would be too annoying to set up a whole set of import options every time for each new importer, so instead Hydrus has a sophisticated _defaults_ system, where all import contexts of type x can be set up to generally use the same import options of type y, so you might say 'in general, all gallery downloads should grab all the tags and send them here'. At the moment of import, the system looks at what is going on, say "we are importing from this URL through this type of page", and freezes a mix-and-match of the various default settings and goes ahead.

**Importantly**, a setting here for a type of import can abstain, saying, for instance: "subscriptions have no custom note import options". When an import context says this, which is does by saying 'just use the default', it is telling the system to defer to the next most general layer for actual settings to use. Most of the options structure starts like this, not setting anything, and thus most imports will by default use the base 'global' settings.

The 'global' set of Import Options are the backstop that will be used if nothing else involved has any custom Import Options set. Each importer has one or more 'types' that are used to fetch default templates that may override the globals, and each individual importer (think an individual importer page or subscription) can have its own custom Import Options to force its behaviour one way or another. It is all arranged in a preference stack, like so:

(non-confusing image of custom/local hard drive import/global. green dots on the global line, which has entries everywhere)

This is the default situation for a local hard drive import page. There is nothing special set up. Imagine, though, if you did this:

(diagram of hitting file filtering import options on the import page itself and said to not exclude previously deleted. perhaps in a couple stages with arrows)

We would now have this situation:

(same diagram as before, but now green dot is on custom line. global line for file filtering is black)

We overrode what the global defaults were for this import, and this import page will now allow previously deleted files. The most specific pertinent options is the one used, so if there are 'note import options' for all gallery downloaders, that will completely override whatever any more general layer has set. You cannot (yet) set 'do what the lower layer says _and_ also do this'.

Now load up `options->import options`:

(pic of it with 'local hard drive import' highlighted, and then that specific edit panel)

Here we can tell hydrus that any local hard drive import should have different File Filtering, Locations, or Presentation Import Options than the global. If you wanted all your manual file imports to always allow previously deleted files or to always import to a particular local file domain, you could set it here and then you wouldn't have to set it specifically as we did earlier! Any local import page will consult its private settings, then the 'local hard drive import' settings, and then fall back to the globals.

The stack gets more complicated for downloaders. Hydrus now considers the type of URL, so different sites can have different blacklists or tag parsing rules. We also split URLs into two broad categories--'gallery/post urls' and 'watchable urls', which correspond to a gallery downloader page or a thread watcher page.

Let's look at subscriptions:

(non-confusing picture of the swiss cheese stack)
(make sure it follows the actual defaults so the user can follow along)

If you are a new user, this should be the same default you see, so feel free to check with the options page. What's special?

- In general, we want to grab tags from gallery sites. Most tags from gallery downloaders are mostly good, so the default there is 'yes we want everything', and to pipe them to your "downloader tags" local tags domain. Note that watcher urls do not have any tag parsing--watchers only tend to have filename spam tags and so the default is to not get anything.
- In general, we don't want subscriptions to spam you (via their buttons or pages) with stuff you have already dealt with. Sometimes subscriptions overlap or they show things you just downloaded manually yesterday. We tell them to only present "new files", which means stuff that did not get 'already in db'.

If you never want to import any content with the tag "goblin", you could set that up in "Tag Filtering Import Options" for your 'gallery/post urls', and then any normal downloader is going to ignore any such file. If that "goblin" problem only appears on a certain site, you could set it up with the appropriate URL Class. If it only applies to a very specific clever subscription, you can set it up just on that sub in the 'edit subscriptions' dialog.

# Import Options In Detail

Let's look at each panel:

## Prefetch Import Options

(picture)

You don't need to touch this guy unless you need to force a downloader to run inefficiently. Stay away!

## File Filtering Import Options

(picture)

You can choose to ignore files of certain filetypes or set size limits. This is most useful for one-time jobs where you have a big mess of files and don't want to pick through it all to exclude the 32x32 icons or whatever is mixed in. The 'exclude previously deleted' checkbox is important, and in most cases you want it on.

## Tag Filtering Import Options

(picture)

This is great when you have a downloader that you cannot easily filter with a query. Maybe you want everything by artist 'x', but only their 'y' content. To exclude their 'z' stuff you can set up a blacklist that matches 'z' and any time a file comes with any matching tags, it will be ignored instead of imported. On rare occasion, you may want the slightly different whitelist logic of 'only import if it has "y"'.

This is also useful for your general hatelist. Throw your personal 'diaper', 'vore', 'queen of spades', and such into the 'gallery/post urls' entry and you can skip it all.

## Location Import Options

(picture)

If you end up falling in love with multiple local file domains (which adds places to put files beyond 'my files'), you can drive certain imports into one place, or multiple places.

This is useful to set up at the global level, and you may want to set up some templates for quick-loading frequent jobs.

## Tag Import Options

(picture)

This is a big one. Note that it generally only handles downloader tags. The filename tagging you can do via a manual file import already assigns tags to different services and works on a different system. In most cases, a simple 'get all' click on the place you want downloader tags to land will work, but if you want to get complicated and say 'only creator/series/character tags' and such, you can. There are some turbo-brain settings under the cog menu.

The 'additional tags' buttons let you force-add a list of tags to each file being imported. This is useful for one-time jobs, sometimes, that need a special label.

## Note Import Options

(picture)

This panel is a mess, and all note deduplication handling is a mess. Leave it on the default settings--or go crazy trying to figure out how it works.

## Presentation Import Options

(picture)

This is for advanced users. When you get annoyed by seeing old stuff appear in new importers, poke around here.

# Favourites/Templates and Copy/Paste

Ok, so you have played with the system. Let's say you now know, "I want every x downloader to work _exactly this way_," but now you are dreading setting it up on the eight separate URL Classes or import folders you are planning. The good news is everything is copyable to your clipboard and there is a favourites system where you can save whole setups or templates.

(picture of import options panel, circle the buttons)

Since you may be copying up to seven things and may be pasting on top of up to seven things, there are several kinds of paste:

(picture of the paste dropdown menu)

If you learn this system back-to-front, then you'll use the quick verbs, but for now just use the 'custom paste' up top. You'll get this:

(picture of the paste dialog)

The column on the left is what options were set in this place beforehand; the middle column is what your paste/load has to offer; the right is what the outcome of this overwrite currently looks like. Use the checkboxes to change what you are overwriting.

If you need to set up the same options for twelve URL Classes in a row, set up exactly what you want for one of them and then 'copy' and use the 'replace-paste' on a selection of the rest.

If you have a common setup (for instance, 'import to x local file domain and auto-archive', save it to your favourites! You can load it up quickly to any importer:

(picture of the import options button and the load favourite thing in the arrow dropdown)
