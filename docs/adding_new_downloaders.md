---
title: adding new downloaders
---

# adding new downloaders

## all downloaders are user-creatable and -shareable { id="anonymous" }

Since the big downloader overhaul, all downloaders can be created, edited, and shared by any user. Creating one from scratch is not simple, and it takes a little technical knowledge, but importing what someone else has created is easy.

Hydrus objects like downloaders can sometimes be shared as data encoded into png files, like this:

![](images/easy-import-realbooru.com-search-2018.09.21.png)

This contains all the information needed for a client to add a realbooru tag search entry to the list you select from when you start a new download or subscription.

You can get these pngs from anyone who has experience in the downloader system. An archive is maintained [here](https://github.com/CuddleBear92/Hydrus-Presets-and-Scripts/tree/master/Downloaders).

To 'add' the easy-import pngs to your client, hit _network->downloaders->import downloaders_. A little image-panel will appear onto which you can drag-and-drop these png files. The client will then decode and go through the png, looking for interesting new objects and automatically import and link them up without you having to do any more. Your only further input on your end is a 'does this look correct?' check right before the actual import, just to make sure there isn't some mistake or other glaring problem.

Objects imported this way will take precedence over existing functionality, so if one of your downloaders breaks due to a site change, importing a fixed png here will overwrite the broken entries and become the new default.