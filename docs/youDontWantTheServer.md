---
title: You don't want the server
---

# You don't want the server
The server.exe/server.py is the victim of many a misconception. You don't need to use the server to use Hydrus. The vast majority of features are contained in the client itself so if you're new to Hydrus, just use that.

The server is only really useful for a few specific cases which will not apply for the vast majority of users.

## The server
The Hydrus server doesn't really work as most people envision a server working. Rather than on-demand viewing, when you link with a Hydrus server, you synchronise a complete copy of all its data. For the tag repository, you download every single tag it has ever been told about. For the file repository, you download the whole file list, related file info, and every single thumbnail, which lets you browse the whole repository in your client in a regular search page--to view files in the media viewer, you need to download and import them specifically.

## You don't want the server (probably)
Do you want to remotely view your files? You don't want the server.

Do you want to host your files on another computer since your daily driver don't have a lot of storage space? You don't want the server.

Do you want to use multiple clients and have everything synced between them? You don't want the server.

Do you want to expose API for Hydrus Web, Hydroid, or some other third-party tool? You don't want the server.

Do you want to share some files and/or tags in a small group of friends? You might actually want the server.

## The options
Now, you're not the first person to have any of the above ideas and some of the thinkers even had enough programming know-how to make something for it. Below is a list of some options, see [this page](client_api.md) for a few more.

### [Hydrus Web](https://github.com/floogulinc/hydrus-web)
 - Lets you browse and manage your collection.

### [Hydroid](https://github.com/thatfuckingbird/hydroid)
 - Lets you browse and manage your collection.

### [Animeboxes](https://www.animebox.es/)
 - Lets you browse your collection.

### [Database migration](https://hydrusnetwork.github.io/hydrus/help/database_migration.html)
 - Lets you host your files on another drive, even on another computer in the network.
