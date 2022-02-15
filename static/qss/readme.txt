Place a .css or .qss Qt Stylesheet file in here, and hydrus will provide it as an UI stylesheet option.

Don't edit any of the files in here--they'll just be overwritten the next time you install. Copy to your own custom filenames if you want to edit anything.

The default_hydrus.qss is used by the client to draw some custom widget colours. It is prepended to any custom stylesheet that is loaded, check it out for the class names you want want to override in your own custom QSS.

This is still a bit of a test. I think to do this properly we'll want to move to folders so we can include additional assets like images.

Here's some examples, there are some QSS files buried here:

https://wiki.qt.io/Gallery_of_Qt_CSS_Based_Styles