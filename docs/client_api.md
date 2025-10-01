---
title: Client API
---

# Client API

The hydrus client now supports a very simple API so you can access it with external programs.

## Enabling the API

By default, the Client API is not turned on. Go to _services->manage services_ and give it a port to get it started. I recommend you not allow non-local connections (i.e. only requests from the same computer will work) to start with.

The Client API should start immediately. It will only be active while the client is open. To test it is running all correct (and assuming you used the default port of 45869), try loading this:

[`http://127.0.0.1:45869`](http://127.0.0.1:45869)

You should get a welcome page. By default, the Client API is HTTP, which means it is ok for communication on the same computer or across your home network (e.g. your computer's web browser talking to your computer's hydrus), but not secure for transmission across the internet (e.g. your phone to your home computer). You can turn on HTTPS, but due to technical complexities it will give itself a self-signed 'certificate', so the security is good but imperfect, and whatever is talking to it (e.g. your web browser looking at [https://127.0.0.1:45869](https://127.0.0.1:45869)) may need to add an exception.

The Client API is still experimental and sometimes not user friendly. If you want to talk to your home computer across the internet, you will need some networking experience. You'll need a static IP or reverse proxy service or dynamic domain solution like no-ip.org so your device can locate it, and potentially port-forwarding on your router to expose the port. If you have a way of hosting a domain and have a signed certificate (e.g. from [Let's Encrypt](https://letsencrypt.org/)), you can overwrite the client.crt and client.key files in your 'db' directory and HTTPS hydrus should host with those.

Once the API is running, go to its entry in _services->review services_. Each external program trying to access the API will need its own access key, which is the familiar 64-character hexadecimal used in many places in hydrus. You can enter the details manually from the review services panel and then copy/paste the key to your external program, or the program may have the ability to request its own access while a mini-dialog launched from the review services panel waits to catch the request.

## Tools created by hydrus users

### Browser Add-on

* [Hydrus Companion](https://gitgud.io/prkc/hydrus-companion): A Chrome/Firefox extension for hydrus that allows easy download queueing as you browse and advanced login support.

### Client Browsing

* [Hydrus Web](https://github.com/floogulinc/hydrus-web): A web client for hydrus with an advanced but also phone-friendly interface.
* [Hydrui](https://hydrui.dev) [(Repo)](https://github.com/hydrui/hydrui): A web client for hydrus with an interface similar to the regular client.
* [Hybooru](https://github.com/funmaker/Hybooru): A read-only booru-like web wrapper for hydrus.
* [Anime Boxes](https://www.animebox.es/): A booru browser, now supports adding your client as a Hydrus Server.
* [LoliSnatcher](https://github.com/NO-ob/LoliSnatcher_Droid): A booru client for Android that can talk to hydrus.
* [Hyshare](https://github.com/floogulinc/hyshare): A way to share small galleries with friends--a replacement for the old 'local booru' system.
* [Hydra Vista](https://github.com/konkrotte/hydravista): A macOS client for hydrus.
* [FlipFlip](https://ififfy.github.io/flipflip/#/): An advanced slideshow interface, now supports hydrus as a source.
* [Hydrus Archive Delete](https://gitgud.io/koto/hydrus-archive-delete): Archive/Delete filter in your web browser.

### Advanced Downloading

* [hydownloader](https://gitgud.io/thatfuckingbird/hydownloader): Hydrus-like download system based on gallery-dl. It solves many advanced problems the native downloader cannot handle.

### Auto-taggers

* [hydrus-dd](https://gitgud.io/koto/hydrus-dd): DeepDanbooru tagging for Hydrus.
* [wd-e621-hydrus-tagger](https://github.com/Garbevoir/wd-e621-hydrus-tagger): More AI tagging, with more models.

### Misc

* [Hydrus Video Deduplicator](https://github.com/hydrusvideodeduplicator/hydrus-video-deduplicator): Discovers duplicate videos in your client and queues them for the duplicate filter. 
* [tagrank](https://github.com/matjojo/tagrank): Shows you comparison images and cleverly ranks your favourite tag.
* [hyextract](https://github.com/floogulinc/hyextract): Extract archives from Hydrus and reimport with tags and URL associations.
* [Send to Hydrus](https://github.com/Wyrrrd/send-to-hydrus): Send URLs from your Android device to your client.
* [Iwara-Hydrus](https://github.com/GoAwayNow/Iwara-Hydrus): A userscript to simplify sending Iwara videos to Hydrus Network.
* [dolphin-hydrus-actions](https://gitgud.io/prkc/dolphin-hydrus-actions): Adds Hydrus right-click context menu actions to Dolphin file manager.
* [more projects on github](https://github.com/stars/hydrusnetwork/lists/hydrus-related-projects)

_If you create a tool that uses the Client API, let me know if/when you are willing to share it, and I'll add it here!_ 
