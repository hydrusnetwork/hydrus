---
title: Parsers
---

# Parsers

In hydrus, a parser is an object that takes a single block of HTML or JSON data and returns many kinds of hydrus-level metadata.

Parsers are flexible and potentially quite complicated. I assume you have imported some downloaders already, for reference. You might like to open _network->downloader components->manage parsers_ and explore the UI as you read these pages. If you want to write a new one, see if another like it already exists--it is usually easier to duplicate and edit an existing parser than create a new one from scratch every time.

There are three main components in the parsing system (click to open each component's help page):

*   [**Formulae:**](downloader_parsers_formulae.md) Take parsable data, search it in some manner, and return 0 to n strings.
*   [**Content Parsers:**](downloader_parsers_content_parsers.md) Take parsable data, apply a formula to it to get some strings, and apply a single metadata 'type' and perhaps some additional modifiers.
*   [**Page Parsers:**](downloader_parsers_page_parsers.md) Take parsable data, apply content parsers to it, and return all the metadata in an appropriate structure.

Once you are comfortable with these objects, you might like to check out these walkthroughs, which create full parsers from nothing:

*   [gallery page](downloader_parsers_full_example_gallery_page.md)
*   [file page](downloader_parsers_full_example_file_page.md)
*   [JSON file page](downloader_parsers_full_example_api.md)

Some parsers are simple, others are complicated and use more unusual hydrus tech to get their job done. Older internet tech is easier, newer stuff is often too complicated and you may need to rely on a third-party downloader.

When you are making a parser, consider this checklist (you might want to copy/have your own version of this somewhere):

*   Do you get good URLs with good priority? Do you ever accidentally get favourite/popular/advert results you didn't mean to?
*   If you need a next gallery page URL, is it ever not available (and hence needs a URL Class fix)? Does it change for search tags with unicode or http-restricted characters?
*   Do you get nice namespaced tags? Are any unwanted single characters like -/+/? getting through?
*   Is the file hash available anywhere?
*   Is a source/post time available?
*   Is a source URL available? Is it good quality, or does it often just point to an artist's base social media profile URL rather than an actual file post URL?
