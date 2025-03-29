---
title: Filtering Duplicates Automatically
---

**Hey, this is all for a system that is only just launching. Not everything is active/ready yet!**

## the problem with duplicates processing

The duplicates filter can get pretty tedious. Pairs that are obvious resizes or pixel duplicates are easy to resolve but boring to work through.

If only there were some way to automate common decisions! We could have hydrus solve these trivial duplicates in the background, leaving us with less, more interesting work to do.

!!! warning "Be careful!"
    Automated systems are powerful magic wands, and we should always be careful waving them around. Make sure you are hesitant rather than confident and always check the preview tab to make sure what you are about to do makes sense. There's no undo once a rule starts going!
    
    If you plan to do something huge, like deleting 50,000 files, make a backup before it starts.

!!! warning "Default merge options"
    Check your default duplicate metadata merge options before engaging with this! If they say 'always archive both', which assumes you were looking at both in the duplicate filter, that's probably not appropriate for automatic merging.

!!! info "Everything is off by default"
    Resolving duplicates is a highly subjective issue. Maybe you think EXIF data is the best, or maybe you always want it gone. Maybe you never want to delete low quality files, or always merge URLs, or set an artist correction as a duplicate instead of an alternate. People simply differ.
    
    This system has templated quick-start suggestions, but they are not mandatory. The intention is to let you set up what you want how you want. Everything is off by default!

## duplicates auto-resolution

_This is a new system that I am still developing. I am rolling out a hardcoded rule that resolves jpeg and png pixel dupes so we can test performance, and then I will produce more tools for user-customisable rules in future weeks. If you try it, let me know how you find things!_

So, let's start with a simple and generally non-controversial example: pixel-duplicate jpeg & png pairs.

When converting between typical image formats, if you save to a jpeg, the output file will have some new 'fuzzy' artifacts, but if you save a png, it is pixel perfect to the original. This is one of the reasons why jpegs of rich images tend to be smaller than pngs--jpegs are a _lossy_ simulation and compress well, pngs are _lossless_ and have to account for everything perfectly.

Thus, when you have a normal potential duplicate pair that is pixel-duplicates (i.e. they have exactly the same pixel image content) and which has one jpeg and one png, you _know_, for certain, that the png is a copy of the jpeg. The lossless pixel-perfect copy was made from the lossy original. This happens most often when someone is posting from one application to another, or with a phone, where rather than uploading the source jpeg, they do 'copy image' and paste that into the upload box--the browser eats the bitmap on the clipboard and creates the accursed 'Clipboard.png', and it all eventually percolates to our clients as duplicate spam.

In this case, we always want to keep the (usually smaller, original) jpeg and ditch the (bloated, derived) png. In the duplicates system, this would be:

- A two-part duplicates search, for 'system:filetype is jpeg' and 'system:filetype is png', with 'must be pixel dupes'.
- Arranging each incoming pair as 'the jpeg is A, the png is B'
- Sending the duplicate action of 'set A as better than B, and delete B'.

We could follow this script every time and be happy with it. Let's do it!

### search

Let's check out the 'auto-resolution' tab under the duplicates filtering page. There's a dialog to edit the current 'auto-resolution rules' and a button to add some suggested ones where everything is set up for you:

[![](images/duplicates_auto_resolution_search.png)](images/duplicates_auto_resolution_search.png)

Each rule represents a search, a way of testing pairs, and then a duplicate action.

Note that in addition to the jpeg/png filetype predicates, I have added `width > 128` and `height > 128` to each search. I said above that we are confident of this rule for _normal_ images, but what about 16x16 icons? There a jpeg might, by chance, be a pixel-perfect match of a png, and maybe we want to keep the png anyway for odd cases.

!!! info "Specific search is good"
    Note, of course, that we didn't have to add our width and height predicates to the 'png' side, since both files in a pixel-perfect pair will have the same resolution. However, the duplicates auto-resolution system runs faster with more specific searches, since this reduces the number of files and pairs it needs to track for a specific rule.
    
    Try to make a specific search if you can--not always 'system:everything'.

### comparison

Now let's look at the comparison tab:

[![](images/duplicates_auto_resolution_comparison.png)](images/duplicates_auto_resolution_comparison.png)

This is the area of the system that will see most future work. It uses the normal system predicate system for its logic. Only a few predicate types are supported right now, but this will expand. Also, the system only supports `A matches test` or `B matches test`, testing each file in isolation, but in future we'll have `A's filesize >= 5x B's filesize` and so on.

For our rule, we know that every 1,2 pair from the search will include one jpeg and one png, but they will come in random order. We can tell hydrus to orient it always as jpeg-png by saying that A has to be the jpeg.

### action

The 'action' tab simply sets what we want to do. This all works the same way as in the duplicate filter. For our rule, we want to say A, the jpeg, is better, and we want to delete B, the worse png. We'll leave the content merge options as the default, merging tags and ratings and so on just as we would for a 'set better than' in a normal duplicate filter.

[![](images/duplicates_auto_resolution_action.png)](images/duplicates_auto_resolution_action.png)

### preview

Lastly, we want to check what we are about to do. We'll see how many pairs the search produces and how many pass or fail our comparison test.

[![](images/duplicates_auto_resolution_preview.png)](images/duplicates_auto_resolution_preview.png)

This may run a little slow, but bear with it. You can double-click a row to see the pair in a normal media viewer.

In our simple jpeg/png pixel duplicates, nothing will fail the test, because we only selected for `A == jpeg`, and since every pair will have exactly one jpeg, the test is always satisfiable. If you were testing for comparable filesize, you would likely see some that do not match. Non-matching pairs will not be touched by the rule in any way.

Note also that the matching pairs may or may not have a specific order. If you set ambiguous comparison rules, it may be that a pair could set its AB as 1,2 or 2,1, and if that's the case, it will say so--and if you spam the refresh button, you'll see those rows flip back and forth. Ambiguous AB order is fine if you are setting 'alternates' or 'same quality', but know that hydrus will choose 1,2 or 2,1 randomly when it does its work for real, so it is simply not appropriate for 'better than'. If you need to fix this situation, go back to the 'comparison' tab and tighten up the rules.

Once we are happy, we can apply the dialogs and save our rule back. It will start working immediately.

## how does this all work?

When you add a new rule, hydrus will throw all the current potential duplicate pairs at the rule and then work in small background packets, doing bits of search and then resolution, usually half a second or so at a time, finding which pairs match the search, and then processing any pairs that match the comparison test. The list on the duplicates page will update with a live summary.

When you import new files and the regular potential dupes search (on the 'preparation' tab of the duplicates page) finds new pairs amongst them, the auto-resolution rules will be told about them and will quickly see if they can action them. You can force the system to work a bit harder on a particular rule if you want to catch up somewhere, but normally you can just leave it all alone and be happy that it is saving you time in the background.

## future

I will expand the 'comparison' tab allow for more system predicate types and figure out 'A vs B' tests too. Pixel-perfect jpeg/png is easy and simple to logically define, but we'll want to push into fuzzier territory like 'delete all files that are close-match dupes but the resolution difference is greater than 1.4x' etc.. Depending on how things go, we may figure out some new hardcoded tools that do more sophisticated A vs B similarity testing, like "A is >= 99.7% pixel-similar to B" or "A is pixel-perfect-in-greyscale to B" (for recolour detection) and so on.

I'd also eventually love if auto-resolution rules applied to files _as_ they are imported, so, in the vein of a 'previously deleted' import result, you could have an instant result of 'duplicate discarded: (rule name)'. This may be tricky though and make file imports take +800ms each, so we'll see how our early tests shake out.

If you try out the system, thank you. Let me know how it works and I'll keep iterating.
