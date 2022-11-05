---
title: About These Docs
---

# About These Docs

The Hydrus docs are built with [MkDocs](https://www.mkdocs.org/) using the [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/) theme. The .md files in the `docs` directory are converted into nice html in the `help` directory. This is done automatically in the built releases, but if you run from source, you will want to build your own.

## Local Setup

To see or work on the docs locally, [install `mkdocs-material`](https://squidfunk.github.io/mkdocs-material/getting-started/):

The recommended installation method is `pip`:
```
pip install mkdocs-material
```

## Building

To build the help, run:
```
mkdocs build -d help
```
In the base hydrus directory (same as the `mkdocs.yml` file), which will build it into the `help` directory. You will then be good!

Repeat the command and MkDocs will clear out the old directory and update it, so you can fold this into any update script.

## Live Preview

To edit the `docs` directory, you can run the live preview development server with:
```
mkdocs serve 
```

Again in the base hydrus directory. It will host the help site at [http://127.0.0.1:8000/](http://127.0.0.1:8000/), and when you change a file, it will automatically rebuild and reload the page in your browser.
