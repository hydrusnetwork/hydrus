---
title: Searching and Sorting
---

# Searching and sorting
The primary purpose of tags is to be able to find what you've tagged again. Let's see more how it works.

## Searching
Just open a new search page (`pages > new file search page` or <kbd>Ctrl+T</kbd> `> file search`) and start typing in the search field which should be focused when you first open the page.

### The dropdown controls

Let's look at the tag autocomplete dropdown:

![](images/ac_dropdown.png)

*   **system predicates**
    
    Hydrus calls search terms _predicates_. 'system predicates', which search metadata other than simple tags, show on any search page with an empty autocomplete input. You can mix them into any search alongside tags. They are very useful, so try them out!
    
*   **include current/pending tags**
    
    Turn these on and off to control whether tag _predicates_ apply to tags that exist, or those pending to be uploaded to a tag repository. Just searching 'pending' tags is useful if you want to scan what you have pending to go up to the PTR--just turn off 'current' tags and search `system:num tags > 0`.
    
*   **searching immediately**
    
    This controls whether a change to the list of current search predicates will instantly run the new search and get new results. Turning this off is helpful if you want to add, remove, or replace several heavy search terms in a row without getting UI lag.
    
*   **[OR](getting_started_searching.md#or_searching)**
    
    You only see this if you have 'advanced mode' on. It lets you enter some pretty complicated tags!
    
*   **file/tag domains**
    
    By default, you will search in 'my files' and 'all known tags' domain. This is the intersection of your local media files (on your hard disk) and the union of all known tag searches. If you search for `character:samus aran`, then you will get file results from your 'my files' domain that have `character:samus aran` in any known tag service. For most purposes, this combination is fine, but as you use the client more, you will sometimes want to access different search domains.
    
    For instance, if you change the file domain to 'trash', then you will instead get files that are in your trash. Setting the tag domain to 'my tags' will ignore other tag services (e.g. the PTR) for all tag search predicates, so a `system:num_tags` or a `character:samus aran` will only look 'my tags'.
    
    Turning on 'advanced mode' gives access to more search domains. Some of them are subtly complicated, run extremely slowly, and only useful for clever jobs--most of the time, you still want 'my files' and 'all known tags'.
    
*   **favourite searches star**
    
    Once you are more experienced, have a play with this. It lets you save your common searches for future, so you don't have to either keep re-entering them or keep them open all the time. If you close big things down when you aren't using them, you will keep your client lightweight and save time.
    

When you type a tag in a search page, Hydrus will treat a space the same way as an underscore. Searching `character:samus aran` will find files tagged with `character:samus aran` and `character:samus_aran`. This is true of some other syntax characters, `[](){}/\"'-`, too.

Tags will be searchable by all their [siblings](advanced_siblings.md). If there's a sibling for `large` -> `huge` then typing `large` will provide `huge` as a suggestion. This goes for the whole sibling chain, no matter how deep or a tag's position in it.

### Wildcards

The autocomplete tag dropdown supports wildcard searching with `*`.

![](images/wildcard_gelion.png)

The `*` will match any number of characters. Every normal autocomplete search has a secret `*` on the end that you don't see, which is how full words get matched from you only typing in a few letters.

This is useful when you can only remember part of a word, or can't spell part of it. You can put `*` characters anywhere, but you should experiment to get used to the exact way these searches work. Some results can be surprising!

![](images/wildcard_vage.png)

You can select the special predicate inserted at the top of your autocomplete results (the highlighted `*gelion` and `*va*ge*` above). **It will return all files that match that wildcard,** i.e. every file for every other tag in the dropdown list.

This is particularly useful if you have a number of files with commonly structured over-informationed tags, like this:

![](images/wildcard_cool_pic.png)

In this case, selecting the `title:cool pic*` predicate will return all three images in the same search, where you can conveniently give them some more-easily searched tags like `series:cool pic` and `page:1`, `page:2`, `page:3`.

### Editing Predicates

You can edit any selected 'active' search predicates by either its <kbd>Right-Click</kbd> menu or through <kbd>Shift+Double-Left-Click</kbd> on the selection. For simple tags, this means just changing the text (and, say, adding/removing a leading hyphen for negation/inclusion), but any 'system' predicate can be fully edited with its original panel. If you entered 'system:filesize < 200KB' and want to make it a little bigger, don't delete and re-add--just edit the existing one in place.

### Other Shortcuts

These will eventually be migrated to the shortcut system where they will be more visible and changeable, but for now:

- <kbd>Left-Click</kbd> on any taglist is draggable, if you want to select multiple tags quickly.
- <kbd>Shift+Left-Click</kbd> across any taglist will do a multi-select. This click is also draggable.
- <kbd>Ctrl+Left-Click</kbd> on any taglist will add to or remove from the selection. This is draggable, and if you start on a 'remove', the drag will be a 'remove' drag. Play with it--you'll see how it works.
- <kbd>Double-Left-Click</kbd> on one or more tags in the 'selection tags' box moves them to the active search box. Doing the same on the active search box removes them.
- <kbd>Ctrl+Double-Left-Click</kbd> on one or more tags in the 'selection tags' box will add their negation (i.e. '-skirt').
- <kbd>Shift+Double-Left-Click</kbd> on more than one tags in the 'selection tags' box will add their 'OR' to the active search box. What's an OR? Well:

## OR searching
Searches find files that match every search 'predicate' in the list (it is an **AND** search), which makes it difficult to search for files that include one **OR** another tag. For example the query `red eyes` **AND** `green eyes` (aka what you get if you enter each tag by itself) will only find files that has both tags. While the query `red eyes` **OR** `green eyes` will present you with files that are tagged with red eyes or green eyes, or both.

More recently, simple OR search support was added. All you have to do is hold down ++shift++ when you enter/double-click a tag in the autocomplete entry area. Instead of sending the tag up to the active search list up top, it will instead start an under-construction 'OR chain' in the tag results below:

![](images/or_under_construction.png)

You can keep searching for and entering new tags. Holding down ++Shift++ on new tags will extend the OR chain, and entering them as normal will 'cap' the chain and send it to the complete and active search predicates above.

![](images/or_done.png)

Any file that has one or more of those OR sub-tags will match.

If you enter an OR tag incorrectly, you can either cancel or 'rewind' the under-construction search predicate with these new buttons that will appear:

![](images/or_buttons.png)

You can also cancel an under-construction OR by hitting Esc on an empty input. You can add any sort of search term to an OR search predicate, including system predicates. Some unusual sub-predicates (typically a `-tag`, or a very broad system predicate) can run very slowly, but they will run much faster if you include non-OR search predicates in the search:

![](images/or_mixed.png)

This search will return all files that have the tag `fanfic` and one or more of `medium:text`, a positive value for the like/dislike rating 'read later', or PDF mime.

There's a more advanced OR search function available by pressing the OR button. Previous knowledge of operators expected and required.

## Sorting
At the top-left of most pages there's a `sort by: ` dropdown menu. Most of the options are self-explanatory. They do nothing except change in what order Hydrus presents the currently searched files to you.

Default sort order and more `sort by: namespace` are found in `file -> options -> sort/collect`.

### Sorting with `system:limit`

If you add `system:limit` to a search, the client will consider what that page's file sort currently is. If it is simple enough--something like file size or import time--then it will sort your results before they come back and clip the limit according to that sort, getting the n 'largest file size' or 'newest imports' and so on. This can be a great way to set up a lightweight filtering page for 'the 256 biggest videos in my inbox'.

If you change the sort, hydrus will not refresh the search, it'll just re-sort the n files you have. Hit F5 to refresh the search with a new sort.

Not all sorts are supported. Anything complicated like tag sort will result in a random sample instead.

## Collecting
Collection is found under the `sort by: ` dropdown and uses namespaces listed in the `sort by: namespace` sort options. The new namespaces will only be available in new pages.
