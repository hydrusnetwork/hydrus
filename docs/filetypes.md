---
title: Supported Filetypes
---

This is a list of all filetypes Hydrus can import. Hydrus determines the filetype based on examining the file itself rather than the extension or MIME type.

The filetype for a file can be overridden with `manage -> force filetype` in the context menu for a file. 

## Images

| Filetype   | Extension | MIME type      | Thumbnails | Viewable in Hydrus | Notes                 |
| ---------- | --------- | -------------- | :--------: | :----------------: | --------------------- |
| jpeg       | `.jpeg`   | `image/jpeg`   |     ✅     |         ✅         |                       |
| png        | `.png`    | `image/png`    |     ✅     |         ✅         |                       |
| static gif | `.gif`    | `image/gif`    |     ✅     |         ✅         |                       |
| webp       | `.webp`   | `image/webp`   |     ✅     |         ✅         |                       |
| avif       | `.avif`   | `image/avif`   |     ✅     |         ✅         |                       |
| jxl        | `.jxl`    | `image/jxl`    |     ✅     |         ✅         |  JPEG XL              |
| bitmap     | `.bmp`    | `image/bmp`    |     ✅     |         ✅         |                       |
| heic       | `.heic`   | `image/heic`   |     ✅     |         ✅         |                       |
| heif       | `.heif`   | `image/heif`   |     ✅     |         ✅         |                       |
| icon       | `.ico`    | `image/x-icon` |     ✅     |         ✅         |                       |
| qoi        | `.qoi`    | `image/qoi`    |     ✅     |         ✅         | Quite OK Image Format |
| tiff       | `.tiff`   | `image/tiff`   |     ✅     |         ✅         |                       |



## Animations

| Filetype          | Extension | MIME type             | Thumbnails | Viewable in Hydrus | Notes                |
| ----------------- | --------- | --------------------- | :--------: | :----------------: | -------------------- |
| animated gif      | `.gif`    | `image/gif`           |     ✅     |         ✅         |                      |
| apng              | `.apng`   | `image/apng`          |     ✅     |         ✅         |                      |
| animated webp     | `.webp`   | `image/webp`          |     ✅     |         ✅         |                      |
| avif sequence     | `.avifs`  | `image/avif-sequence` |     ✅     |         ✅         |                      |
| heic sequence     | `.heics`  | `image/heic-sequence` |     ✅     |         ✅         |                      |
| heif sequence     | `.heifs`  | `image/heif-sequence` |     ✅     |         ✅         |                      |
| [ugoira](#ugoira) | `.zip`    | `application/zip`     |     ✅     |        ⚠️        | [More info](#ugoira) |


### Ugoira

[Pixiv Ugoira format](https://www.pixiv.help/hc/en-us/articles/235584628-What-are-Ugoira-) is a custom animation format used by Pixiv. The Pixiv API provides a list of frame files (normally JPEG or PNG) and their durations. The frames can be stored in a ZIP file along with a JSON file containing the frame and duration information. A zip file containing images with 6 digit zero-padded filenames will be identified as a Ugoira file in hydrus. 

If there are no frame durations provided hydrus will assume each frame should last 125ms. Hydrus will look inside the zip for a file called `animation.json` and try to parse it as the 2 most common metadata formats that PixivUtil and gallery-dl generate. The Ugoira file will only have a duration in the database if it contains a valid `animation.json`. 

When played hydrus will first attempt to use the `animation.json` file, but if that does not exist, it will look for notes containing frame delays. First it looks for a note named `ugoira json` and attempts to read it like the `animation.json`, it then looks for a note called `ugoira frame delay array` which should be a note containing a simple JSON array, for example: `#!json [90, 90, 40, 90]`.


## Video

| Filetype  | Extension | MIME type                | Thumbnails | Viewable in Hydrus | Notes |
| --------- | --------- | ------------------------ | :--------: | :----------------: | ----- |
| mp4       | `.mp4`    | `video/mp4`              |     ✅     |         ✅         |       |
| webm      | `.webm`   | `video/webm`             |     ✅     |         ✅         |       |
| matroska  | `.mkv`    | `video/x-matroska`       |     ✅     |         ✅         |       |
| avi       | `.avi`    | `video/x-msvideo`        |     ✅     |         ✅         |       |
| flv       | `.flv`    | `video/x-flv`            |     ✅     |         ✅         |       |
| quicktime | `.mov`    | `video/quicktime`        |     ✅     |         ✅         |       |
| mpeg      | `.mpeg`   | `video/mpeg`             |     ✅     |         ✅         |       |
| ogv       | `.ogv`    | `video/ogg`              |     ✅     |         ✅         |       |
| realvideo | `.rm`     | `video/vnd.rn-realvideo` |     ✅     |         ✅         |       |
| wmv       | `.wmv`    | `video/x-ms-wmv`         |     ✅     |         ✅         |       |


## Audio

| Filetype       | Extension | MIME type                | Viewable in Hydrus | Notes |
| -------------- | --------- | ------------------------ | :----------------: | ----- |
| mp3            | `.mp3`    | `audio/mp3`              |         ✅         |       |
| ogg            | `.ogg`    | `audio/ogg`              |         ✅         |       |
| flac           | `.flac`   | `audio/flac`             |         ✅         |       |
| m4a            | `.m4a`    | `audio/mp4`              |         ✅         |       |
| matroska audio | `.mkv`    | `audio/x-matroska`       |         ✅         |       |
| mp4 audio      | `.mp4`    | `audio/mp4`              |         ✅         |       |
| realaudio      | `.ra`     | `audio/vnd.rn-realaudio` |         ✅         |       |
| tta            | `.tta`    | `audio/x-tta`            |         ✅         |       |
| wave           | `.wav`    | `audio/x-wav`            |         ✅         |       |
| wavpack        | `.wv`     | `audio/wavpack`          |         ✅         |       |
| wma            | `.wma`    | `audio/x-ms-wma`         |         ✅         |       |


## Applications

| Filetype | Extension | MIME type                                                                   | Thumbnails | Viewable in Hydrus | Notes                                                                      |
| -------- | --------- | --------------------------------------------------------------------------- | :--------: | :----------------: | -------------------------------------------------------------------------- |
| flash    | `.swf`    | `application/x-shockwave-flash`                                             |     ✅     |         ❌         |                                                                            |
| pdf      | `.pdf`    | `application/pdf`                                                           |     ✅     |         ❌         | 300 DPI assumed for resolution. No thumbnails for encrypted PDFs.          |
| epub     | `.epub`   | `application/epub+zip`                                                      |     ❌     |         ❌         |                                                                            |
| djvu     | `.djvu`   | `image/vnd.djvu`                                                            |     ❌     |         ❌         |                                                                            |
| docx     | `.docx`   | `application/vnd.openxmlformats-officedocument.wordprocessingml.document`   |     ❌     |         ❌         |                                                                            |
| xlsx     | `.xlsx`   | `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`         |     ❌     |         ❌         |                                                                            |
| pptx     | `.pptx`   | `application/vnd.openxmlformats-officedocument.presentationml.presentation` |     ✅     |         ❌         | 300 DPI assumed for resolution. Thumbnail only if embedded in the document |
| doc      | `.doc`    | `application/msword`                                                        |     ❌     |         ❌         |                                                                            |
| xls      | `.xls`    | `application/vnd.ms-excel`                                                  |     ❌     |         ❌         |                                                                            |
| ppt      | `.ppt`    | `application/vnd.ms-powerpoint`                                             |     ❌     |         ❌         |                                                                            |
| rtf      | `.rtf`    | `application/rtf`                                                           |     ❌     |         ❌         |                                                                            |


## Image Project Files

| Filetype  | Extension    | MIME type                     | Thumbnails | Viewable in Hydrus | Notes                                                                            |
| --------- | ------------ | ----------------------------- | :--------: | :----------------: | -------------------------------------------------------------------------------- |
| clip      | `.clip`      | `application/clip`[^1]        |     ✅     |         ❌         | Clip Studio Paint                                                                |
| krita     | `.kra`       | `application/x-krita`         |     ✅     |         ✅         | Krita. Hydrus shows the embedded preview image if present in the file.           |
| procreate | `.procreate` | `application/x-procreate`[^1] |     ✅     |         ❌         | Procreate app                                                                    |
| psd       | `.psd`       | `image/vnd.adobe.photoshop`   |     ✅     |         ✅         | Adobe Photoshop. Hydrus shows the embedded preview image if present in the file. |
| sai2      | `.sai2`      | `application/sai2`[^1]        |     ❌     |         ❌         | PaintTool SAI2                                                                   |
| svg       | `.svg`       | `image/svg+xml`               |     ✅     |         ❌         |                                                                                  |
| xcf       | `.xcf`       | `application/x-xcf`           |     ❌     |         ❌         | GIMP                                                                             |


## Archives

| Filetype | Extension | MIME type                       | Thumbnails | Notes                                                                                                                                                                                                                                                                                                |
| -------- | --------- | ------------------------------- | :--------: | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| cbz      | `.cbz`    | `application/vnd.comicbook+zip` |     ✅     | A zip file containing images with incrementing numbers in their filenames will be identified as a cbz file. The code for identifying a cbz file is in [`hydrus/core/files/HydrusArchiveHandling.py`](https://github.com/hydrusnetwork/hydrus/blob/master/hydrus/core/files/HydrusArchiveHandling.py) |
| 7z       | `.7z`     | `application/x-7z-compressed`   |     ❌     |                                                                                                                                                                                                                                                                                                      |
| gzip     | `.gz`     | `application/gzip`              |     ❌     |                                                                                                                                                                                                                                                                                                      |
| rar      | `.rar`    | `application/vnd.rar`           |     ❌     |                                                                                                                                                                                                                                                                                                      |
| zip      | `.zip`    | `application/zip`               |     ❌     |                                                                                                                                                                                                                                                                                                      |

[^1]: This filetype doesn't have an official or de facto media type, the one listed was made up for Hydrus.
