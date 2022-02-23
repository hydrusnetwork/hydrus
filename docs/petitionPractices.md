---
title: Petition practices
---
# Petitions practices
This document exists to give a rough idea what to do in regard to the PTR to avoid creating uncecessary work for the janitors.

## General practice
Kindly avoid creating unnecessary work.  
Create siblings for underscore and non-namespaced/namespaced versions.  
Petition for deletion if they are wrong. Providing a reason outside of the stock choices helps the petition getting accepted.  
If, for whatever reason, you have some mega job that needs doing it's often a good idea to talk to a janitor instead since we can just go ahead and do the job directly without having to deal with potentially tens of petitions because of how Hydrus splits them on the server. An example that we often come across is the removal of the awful Sankaku URLs that are almost everywhere these days due to people using a faulty parser. It's a pretty easy search and delete for a janitor, but a lot of annoying clicking if dealt with as a petition since one big petition can be split out to God-only-knows-how many.

Eventually the PTR janitors will get tools to replace various bad but correct tags on the server itself. These include underscored, wrong or no namespace, common misspelling, wrong locale, and so on. Since we're going to have to do the job eventually anyway there's not much of a point making us do it twice by petitioning the existing bad but correct tags. Just sibling them and leave them be for now.

## Ambiguity
Don't make additions involving ambiguous tags. `hibiki` -> `character:hibiki (kantai collection)` is bad since there's far more than one character with that name. There's quite a few wrongly tagged images because of things like this. Petitioning the deletion of such a bad sibling is good.

## Petitions involving system predicates
Anything that's covered by system predicates. Siblinging these is unecessary and parenting pointless. There's no harm leaving them be aside from crowding the tag list but there's no harm to deleting them either.

 - `system:dimensions` covers most everything related to resolution and aspect ratios. `medium:high resolution`, `4:3 aspect ratio`, and pixel count.

 - `system:duration` for whether something has duration (is a video or animated gif/png/whatever), or is a still image.

 - `system:has audio` for if an image has audio or not. `system:has duration + system:no audio` replaces `video with no sound` as an example.

 - `system:filesize` for things like `huge filesize`.

 - `system:filetype` for filetypes. Gif, webm, mp4, psd, and so on. Anything that Hydrus can recognise which is quite a bit.

## Parents
Don't push parents for tags that are not top-level siblings. It makes tracking down potential issues hard.

Only push parents for relations that are literally always true, no exceptions.  
`character:james bond` -> `series:james bond` is a good example because James Bond always belong to that series. -> `gender:male` is bad because an artist might decide to draw a genderbent piece of art. Similarily -> `person:pierce brosnan` is bad because there have been other actors for the character.

List of some bad parents to `character:` tags as an example:
 - `species:` due to the various -zations (humanization, animalization, mechanization).
 - `creator:` since just about anybody can draw art of the character.
 - `gender:` Since `genderswap` and variations exists.
 - Any form of physical characteristics such as hair or eye colour, hair length, clothing and accessories, etc.

## Translations
Translations should be siblinged to what the closest in-use romanised tag is if there's no proper translation. If the tag is ambiguous, such as `響` or `ヒビキ` which means `hibiki`, just sibling them to the ambiguous tag. The tag can then later on be deleted and replaced by a less ambiguous tag. On the other hand, `響(艦隊これくしょん)` straight up means `hibiki (kantai kollection)` and can safely be siblinged to the proper `character:` tag.  
Do the same for subjective tags. `魅惑のふともも` can be translated to `bewitching thighs`. `まったく、駆逐艦は最高だぜ!!` straight up translates to `Geez, destroyers are the best!!`, which does not contain much usable information for Hydrus currently. These can then either be siblinged down to an unsubjective tag (`thighs`) if there's objective information in the tag, deleted if purely subjective, or deleted and replaced if ambiguous.