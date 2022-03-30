---
title: exporting files
---

# exporting files

## exporting { id="exporting" }

There are many ways to export files from the client:

* **drag and drop**
    
    Just dragging from the thumbnail view will export (copy) all the selected files to wherever you drop them. You can also start a drag and drop for single files from the media viewer using this arrow button on the top hover window:
    
    ![](images/media_viewer_dnd.png)
    
    If you want to drag and drop to discord, check the special BUGFIX option under _options->gui_.
    
    By default, the files will be named by their ugly hexadecimal [hash](faq.md#hashes), which is how they are stored inside the database. Once you learn filename patterns (practise with manual exports, as below!), you will be able to change this in the options if you wish.
    
    If you use a drag and drop to open a file inside an image editing program, remember to hit 'save as' and give it a new filename in a new location! The client does not expect files inside its db directory to ever change.
    
* **share->copy->files**
    
    This will copy the files themselves to your clipboard. You can then paste them wherever you like, just as with normal files. They will have their hashes for filenames.
    
    This is a very quick operation. It can also be triggered by hitting Ctrl+C.
    
* **share->copy->image (bitmap)**
    
    This copies a file's rendered image data to your clipboard. This is useful for pasting into an image editor, but do not use it to upload images to the internet. 
    
* **share->copy->hashes**
    
    This will copy the files' unique identifiers to your clipboard, in hexadecimal.
    
    You will not have to do this often. It is best when you want to identify a number of files to someone else without having to send them the actual files.
    
* **export dialog**
    
    Right clicking some files and selecting _share->export->files_ will open this dialog:
    
    ![](images/export.png)
    
    Which lets you export the selected files with custom filenames. It will initialise trying to export the files named by their hashes, but once you are comfortable with tags, you'll be able to generate much cleverer and prettier filenames.
    
* **export folders**
    
    You can set up a regularly repeating export under _file->import and export folders_. This is an advanced operation, so best left until you know the client a bit better, but it is very useful if you want to regularly export some of your collection to a revolving wallpaper directory or similar.
