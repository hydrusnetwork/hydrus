---
title: Filtering Duplicates Automatically
---

## Hey, this is a draft for a system that is not yet working, you can ignore it for now

# the problem with duplicates processing

The duplicates filter can be pretty tedious to work with. Pairs that have trivial differences are easy to resolve, but working through dozens of obvious resizes or pixel duplicates that all follow the same pattern can get boring.

If only there were some way to automate common situations! We could have hydrus solve these trivial duplicates in the background, leaving us with less, more interesting work to do.

## duplicates auto-resolution

_This is a new system that I am still developing. The plan is to roll out a hardcoded rule that resolves jpeg and png pixel dupes and then iterate on the UI and workflow to let users add their own custom rules. If you try it, let me know how you find things!_

So, let's start with a simple and generally non-controversial example: pixel duplicate jpegs and pngs. When you save a jpeg, you get some 'fuzzy' artifacts, but when you save a png, it is always pixel perfect. Thus, when you have a normal jpeg and a png that are pixel duplicates, you _know_, for certain, that the png is a copy of the jpeg. This happens most often when someone is posting from one application to another, or with a phone, and rather than uploading the source jpeg, they do 'copy image' and paste that into the upload box--the browser creates the accursed 'Clipboard.png', and we are thus overwhelmed with spam.

In this case, we always want to keep the (almost always smaller) jpeg and ditch the (bloated, derived) png, which in the duplicates system would be:

- A two-part duplicates search, for 'system:filetype is jpg' and 'system:filetype is png', with 'must be pixel dupes'.
- Arranging 'the jpeg is A, the png is B'
- Sending the normal duplicate action of 'set A as better than B, and delete B'.

Let's check out the 'auto-resolution' tab under the duplicates filtering page:

(image)

The auto-resolution system lets you have multiple 'rules'. Each represents a search, a way of testing pairs, and then an action. Let's check the edit dialog:

(image of edit rules)

(image of edit rule, png vs jpeg)

Note that this adds the 'system:height/width > 128' predicates as a failsafe to ensure we are checking real images in this case, not tiny 16x16 icons where there might be a legitimate accidentaly jpeg/png pixel dupe, and where the decision on what to keep is not so simple. Automated systems are powerful magic wands, and we should always be careful waving them around.

Talk about metadata conditional objects here.

Talk about the pair Comparator stuff, 4x filesize and so on. Might be more UI, so maybe a picture of the sub-panel.

Hydrus will work these rules in its normal background maintenance time. You can force them to work a bit harder if you want to catch up somewhere, but normally you can just leave them alone and they'll stay up to date with new imports.

## future

I will expand the Metadata Conditional to cover more tests, including most of the hooks in the duplicates filter summaries, like 'this has exif data'. And, assuming the trivial cases go well, I'd like to push toward less-certain comparions and have some sort of tools for 'A is at least 99.7% similar to B', which will help with resize comparisons and differentiating dupes from alternates.

I'd also eventually like auto-resolution to apply to files _as_ they are imported, so, in the vein of 'previously deleted', you could have an instant import result of 'duplicate discarded: (rule name)'.
