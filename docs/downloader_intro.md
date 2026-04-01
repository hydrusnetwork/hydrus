---
title: Making a Downloader
---

# Making a Downloader

!!! caution
	Creating custom downloaders is only for advanced users who understand HTML or JSON. Beware! If you are simply looking for how to add new downloaders, please head over [here](adding_new_downloaders.md).
    
    Also this help is pretty old. The basics are unchanged, but the screenshots are out of date! Good luck!

## this system { id="intro" }

The first versions of hydrus's downloaders were all hardcoded and static--I wrote everything into the program itself and nothing was user-creatable or -fixable. After the maintenance burden of the entire messy system proved too large for me to keep up with and a semi-editable template system proved successful, I decided to overhaul the entire thing to allow user creation and sharing of every component. It is designed to be simple to the front-end user--they will typically handle a couple of special png files and then select a new downloader from a list--but very flexible (and hence potentially complicated) on the back-end. These help pages describe the different compontents with the intention of making an HTML- or JSON- fluent user able to create and share a full new downloader on their own.

Many years later, in 2026, I am now removing the default downloaders from the client entirely. I no longer maintain anything, and everything is managed by users. The tutorials here are similarly more generic. I only work on the tech, not the implementation! Your feedback on the system would be appreciated, and if something is confusing or simply way too out of date, please [let me know](contact.md).

Because the client is now empty at start, if you want rich examples to look at, you'll need to find some. If you haven't yet, I strongly recommend you import some downloaders before you start on this. Have the UI open while you go through everything and don't be afraid to click around. If you break something, just hit cancel a bunch.

## what is a downloader? { id="downloader" }

In hydrus, a downloader is one of:

**Gallery Downloader**
:   This takes a string like 'blue_eyes' to produce a series of thumbnail gallery page URLs that can be parsed for image page URLs which can ultimately be parsed for file URLs and metadata like tags. Boorus fall into this category.

**URL Downloader**
:   This does the non-search component of the Gallery Downloader--instead of taking a query text, it takes the gallery or post URLs directly from the user, whether that is one from a drag-and-drop event or pasted _en masse_ from clipboard. For our purposes here, the URL Downloader is a technical subset of the Gallery Downloader and we won't talk about it.

**Watcher**
:   This takes a URL that it will check in timed intervals, parsing it for new URLs that it then queues up to be downloaded. It typically stops checking after the 'file velocity' (such as '1 new file per day') drops below a certain level. It is mostly for watching imageboard threads.

**Simple Downloader**
:   This takes a URL one-time and parses it for direct file URLs to download. This is a miscellaneous system for certain simple gallery types and some testing/'I just need the third `<img>` tag's `src` on this one page' jobs.

The system currently supports HTML and JSON parsing. XML should be fine under the HTML parser--it isn't strict.

## what does a downloader do? { id="pipeline" }

The Gallery Downloader is the most complicated downloader and uses all the possible components. In order for hydrus to convert our example 'blue_eyes' query into a bunch of files with tags, it needs to:

*   Present some user interface named 'somebooru tag search' to the user that will convert their input of 'blue_eyes' into `https://somebooru.org/index.php?page=post&s=list&tags=blue_eyes&pid=0`.
*   Recognise `https://somebooru.org/index.php?page=post&s=list&tags=blue_eyes&pid=0` as a Somebooru Gallery URL.
*   Download and convert the HTML of a Somebooru Gallery URL into a list URLs like `https://somebooru.org/index.php?page=post&s=view&id=123456` and possibly a 'next page' URL (e.g. `https://somebooru.org/index.php?page=post&s=list&tags=blue_eyes&pid=40`) that points to the next page of thumbnails.
*   Recognise the list of `https://somebooru.org/index.php?page=post&s=view&id=123456`-like URLs as Somebooru Post URLs.
*   Download and convert the HTML of a Somebooru Post URL into a file URL like `https://somebooru.org//images/abcd/0123456789abcdef0123456789abcdef.jpg` and some tags like: 1girl, bangs, black gloves, blonde hair, blue eyes, braid, closed mouth, day, fingerless gloves, fingernails, gloves, grass, hair ornament, hairclip, hands clasped, creator:hankuri, interlocked fingers, long hair, long sleeves, outdoors, own hands together, parted bangs, pointy ears, character:cool princess, smile, solo, series:cool princess adventure.

So we have three components:

*   [**URL Class:**](downloader_url_classes.md) identifies URLs and informs the client how to deal with them.
*   [**Parser:**](downloader_parsers.md) converts data from URLs into hydrus-understandable metadata.
*   [**Gallery URL Generator (GUG):**](downloader_gugs.md) faces the user and converts text input into initialising Gallery URLs.

URL downloaders and watchers do not need the Gallery URL Generator, as their input _is_ an URL. And simple downloaders also have an explicit 'just download it and parse it with this simple rule' action, so they do not use URL Classes (or even full-fledged Page Parsers) either.
