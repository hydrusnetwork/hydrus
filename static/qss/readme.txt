- What is this folder? -

The qss files in this place (and, if you create it, in a mirrored location under your db dir) appear as the UI stylesheet options under _options->style_.


- How to create custom stylesheets -

Don't edit any of the files in here in place--they'll just be overwritten the next time you update. Instead, create a new folder under "db_dir/static/qss" and copy one of these over for editing. Search the help files for 'custom assets' for more info on how this works.

The best thing is just to change some colour hex code, but if you feel brave, feel free to try inserting your own stuff. QSS is cool, and you can edit text size, change colours, make borders, add hover behaviour, all sorts.

Check out these existing QSS files for common names you might want to refer to in your own QSS. Hydrus uses some standard Qt widget names, custom class names, and some property loading.

The default_hydrus.qss is used by the client to draw some custom widget colours. It is prepended to any custom stylesheet that is loaded.


- More QSS -

For more inspiration, there are more QSS files here:

https://wiki.qt.io/Gallery_of_Qt_CSS_Based_Styles

And a bunch of random projects have some too, such as:

https://github.com/ModOrganizer2/modorganizer/tree/master/src/stylesheets


- QSS Assets -

A QSS that has assets under a subfolder, like you see here for 'e621' and 'Paper', can be tricky. The QSS usually defines its assets as a relative path, but hydrus cannot tell Qt where the QSS is coming from, so the relative path is always be calculated from the CWD when you launch the program. We have to make sure these line up all correct (e.g. the e621 qss refers to "static/qss/e621/dropdown.svg"). If you ensure your CWD is the base install dir, things should line up for these default QSS files, but for custom QSSes, you should edit the QSS to use absolute paths like "C:\hydrus\my_dir\static\qss\my_qss\thing.svg" or "/blah/db_dir/static/qss/my_qss/thing.svg" explicitly.