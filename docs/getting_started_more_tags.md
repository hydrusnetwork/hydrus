---
title: More Tags
---

# Tags Can Get Complicated

Tags are powerful, and there are many tools within hydrus to customise how they apply and display. I recommend you play around with the basics before making your own new local tag services or jumping right into the PTR, so take it slow. 

## Tag services
Hydrus lets you organise tags across multiple separate 'services'. By default there are two, but you can have however many you want (`services->manage services`). You might like to add more for different sets of siblings/parents, tags you don't want to see but still search by, parsing tags into different services based on reliability of the source or the source itself. You could for example parse all tags from Pixiv into one service, Danbooru tags into another, Deviantart etc. and so on as you chose. You must always have at least one local tag service.

Local tag services are stored only on your hard drive--they are completely private. No tags, siblings, or parents will accidentally leak, so feel free to go wild with whatever odd scheme you want to try out.

Each tag service comes with its own tags, siblings and parents.

### My tags
The intent is to use this service for tags you yourself want to add.

### Downloader tags
The default [tag parse target](getting_started_downloading.md#parsing). Tags of things you download will end up here unless you change the settings. It's probably a good idea to set up some tag blacklists for tags you don't want.

## Tag repositories

It can take a long time to tag even small numbers of files well, so I created _tag repositories_ so people can share the work.

Tag repos store many file->tag relationships. Anyone who has an access key to the repository can sync with it and hence download all these relationships. If any of their own files match up, they will get those tags. Access keys will also usually have permission to upload new tags and ask for incorrect ones to be deleted.

Anyone can run a tag repository, but it is a bit complicated for new users. I ran a public tag repository for a long time, and now this large central store is run by users. It has over a billion tags and is free to access and contribute to.

To connect with it, please check [here](access_keys.md). **Please read that page if you want to try out the PTR. It is only appropriate for someone on an SSD!**

If you add it, your client will download updates from the repository over time and, usually when it is idle or shutting down, 'process' them into its database until it is fully synchronised. The processing step is CPU and HDD heavy, and you can customise when it happens in _file->options->maintenance and processing_. As the repository synchronises, you should see some new tags appear, particularly on famous files that lots of people have.

You can watch more detailed synchronisation progress in the _services->review services_ window.

![](images/review_repos_public_tag_repo.png)

Your new service should now be listed on the left of the manage tags dialog. Adding tags to a repository works very similarly to the 'my tags' service except hitting 'apply' will not immediately confirm your changes--it will put them in a queue to be uploaded. These 'pending' tags will be counted with a plus '+' or minus '-' sign:

[![](images/rlm_pending.png)](images/rlm_pending.png)

Notice that a 'pending' menu has appeared on the main window. This lets you start the upload when you are ready and happy with everything that you have queued.

When you upload your pending tags, they will commit and look to you like any other tag. The tag repository will anonymously bundle them into the next update, which everyone else will download in a day or so. They will see your tags just like you saw theirs.

If you attempt to remove a tag that has been uploaded, you may be prompted to give a reason, creating a petition that a janitor for the repository will review.

I recommend you not spam tags to the public tag repo until you get a rough feel for the [guidelines](https://github.com/CuddleBear92/Hydrus-Presets-and-Scripts/blob/master/tag%20guidelines), and my original [tag schema](tagging_schema.html) thoughts, or just lurk until you get the idea. It roughly follows what you will see on a typical booru. The general rule is to only add factual tags--no subjective opinion.

You can connect to more than one tag repository if you like. When you are in the _manage tags_ dialog, pressing the up or down arrow keys on an empty input switches between your services.

[FAQ: why can my friend not see what I just uploaded?](faq.md#delays)

## Siblings and parents
For more in-depth information, see [siblings](advanced_siblings.md) and [parents](advanced_parents.md).

tl;dr: Siblings rename/alias tags in an undoable way. Parents virtually add/imply one or more tags (parents) if the 'child' tag is present. The PTR has a _lot_ of them.

### Display rules
If you go to `tags -> manage where siblings and parents apply` you'll get a window where you can customise where and in what order siblings and parents apply. The service at the top of the list has precedence over all else, then second, and so on depending on how many you have. If you for example have PTR you can use a tag service to overwrite tags/siblings for cases where you disagree with the PTR standards.
