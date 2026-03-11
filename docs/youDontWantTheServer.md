---
title: You don't want the server
---

# You don't want the server
The hydrus_server.exe/hydrus_server.py is the victim of many misconceptions. You don't need to use the server to use Hydrus. The vast majority of features are contained in the client itself. If you are new to Hydrus, just use that.

The server is only really useful for a few specific cases which will not apply for the vast majority of users.

## The server
The Hydrus server doesn't really work as most people envision a server working. Rather than on-demand viewing, when you link with a Hydrus server, you synchronise a complete copy of all its data. It stores a lot of information very efficiently with a slow update latency. For the tag repository, you download every single tag it has ever been told about. For the file repository, you download the whole file list, related file info, and every single thumbnail, which lets you browse the whole repository in your client in a regular search page--to view files in the media viewer, you need to download and import them specifically.

## You don't want the server (probably)
Do you want to remotely view your files? You don't want the server.

Do you want to host your files on another computer since your daily machine doesn't have a lot of storage space? You don't want the server.

Do you want to use multiple clients and have everything synced between them? You don't want the server.

Do you want to expose API for Hydrus Web, Hydroid, or some other third-party tool? You don't want the server.

Do you want to share some files and/or tags in a small group of friends? You might actually want the server.

## The options
You are not the first person to have any of the above ideas. Some of them are possible with the Client API. Check out the most popular projects to see what is possible [here](client_api.md).

Maintaining a database across multiple computers is particularly tricky, and there is no good solution yet. Each database only entertains one client. Some users have figured out `rsync` solutions that simply copy a whole install around, which is annoying but works for small databases. If you want to dial into a big database with multiple thin clients, this is simply not yet possible. One day, perhaps, and with the Client API, not the server.

Related info on the database structure: [Database migration](https://hydrusnetwork.github.io/hydrus/help/database_migration.html)
