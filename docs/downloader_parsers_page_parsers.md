---
title: Page Parsers
---

# Page Parsers

We can now produce individual rows of rich metadata. To arrange them all into a useful structure, we will use Page Parsers.

The Page Parser is the top level parsing object. It takes a single document and produces a list--or a list of lists--of metadata. Each Post/Gallery/Watchable URL Class should have a corresponding Page Parser linked to it under `network->downloader components->manage url class links`. 

Load up a parser you have imported into the system and look at the UI. Notice that the edit panel has three sub-pages--main, content parsers, and subsidiary page parsers.

## main { id="main" }

*   **Name**: Like for content parsers, I recommend you add good names for your parsers. Something like "my_site file post parser - 2024-06-11" is great.
*   **Pre-parsing conversion**: If your API source encodes or wraps the data you want to parse, you can do some string transformations here. You almost certainly will not need this, but if the site is crazy and spits out an invalid response or wraps JSON inside a javascript variable, this is where to look.
*   **Example URLs**: Here you should add a list of example URLs the parser works for. This lets the client automatically link this parser up with URL classes for you and any users you share the parser with.

## content parsers { id="content_parsers" }

We've seen this before in the content parser help. All these things are putting out different rows of interesting metadata. The test panel directly shows their merged output.

## subsidiary page parsers { id="subsidiary_page_parsers" }

Here be dragons. This was an attempt to make parsing more helpful in certain API situations, but it ended up ugly. I do not recommend you use it unless you see another example use it and intuitively understand what is going on. It basically splits the page up into pieces that can then be parsed by nested page parsers as separate objects, but the UI and workflow is hell.
