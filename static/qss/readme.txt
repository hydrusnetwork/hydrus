Place a .css or .qss Qt StyleSheet file in here, and hydrus will provide it as an UI stylesheet option.

Don't edit any of the files in here in place--they'll just be overwritten the next time you update. Copy to your own custom filenames if you want to edit anything.

The default_hydrus.qss is used by the client to draw some custom widget colours. It is prepended to any custom stylesheet that is loaded, so check it out for the class names you want want to override in your own QSS.

Here's some examples, there are some QSS files buried here:

https://wiki.qt.io/Gallery_of_Qt_CSS_Based_Styles

And a bunch of random projects have some too, such as:

https://github.com/ModOrganizer2/modorganizer/tree/master/src/stylesheets
