---
title: Custom Assets
---

# static dir

Hydrus loads all of its icons and other UI images from `install_dir/static`. Feel free to poke around there. You can overwrite any of these files with something else by putting a mirror version under `db_dir/static`.

So, let's say you want a different splash screen image. The default is `install_dir/static/hydrus_splash.png`. Simply create a `static` folder in your db dir and put any other png under `db_dir/static/hydrus_splash.png`, and hydrus will use that when it boots or exits.

This is a bit hacky, so don't change the resolution or ratio of anything too much to start. In some cases, you can probably put a jpeg instead of a png (still using the .png filename) or an svg instead of an ico, and it may work! Let me know when stuff breaks and I'll see what I can do.

# QSS and SVGs

As well as replacing files, you can also complement a folder of defaults with your own custom files. `static/qss` and `static/rating_shapes` are the main examples here. You can create a `db_dir/static/rating_shapes`, and put some svgs in there, and hydrus will list them along with the defaults in `install_dir/static/rating_shapes` in the 'manage services' dialog for ratings. If there are filename conflicts, hydrus prefers the one in your userdir.

There's a couple extra notes for how these should work, so check the readme.txts in the install_dir folders.

# Debugging

There's a `--no_user_static_dir` launch argument that turns this feature off for a particular boot, if you need to.
