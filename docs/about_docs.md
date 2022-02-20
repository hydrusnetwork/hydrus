# About These Docs

The Hydrus docs are built with [MkDocs](https://www.mkdocs.org/) using the [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/) theme.

## Local Setup

To work on the docs locally, [install `mkdocs-material`](https://squidfunk.github.io/mkdocs-material/getting-started/):

The recommended installation method is `pip`:
```
pip install mkdocs-material
```

## Live Preview

Once installed you can run the live preview development server with
```
mkdocs serve 
```

It will automatically rebuild the site when you save it and reload the page in your browser.

## Building

To build the docs site (for example if running from source), run:
```
mkdocs build
```
This by default builds the docs into the `site/` directory. To build to the traditional `help/` directory use
```
mkdocs build -d help
```

The docs are automatically deployed to GitHub Pages on every push to the `master` branch. They are also built automatically in the GitHub Actions workflows for each release and included in those builds.