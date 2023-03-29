---
title: API documentation
hide: navigation
---

# API documentation

## Library modules created by hydrus users

* [Hydrus API](https://gitlab.com/cryzed/hydrus-api): A python module that talks to the API.
* [hydrus.js](https://github.com/cravxx/hydrus.js): A node.js module that talks to the API.
* [more projects on github](https://github.com/stars/hydrusnetwork/lists/hydrus-related-projects)

## API

In general, the API deals with standard UTF-8 JSON. POST requests and 200 OK responses are generally going to be a JSON 'Object' with variable names as keys and values obviously as values. There are examples throughout this document. For GET requests, everything is in standard GET parameters, but some variables are complicated and will need to be JSON encoded and then URL encoded. An example would be the 'tags' parameter on [GET /get\_files/search\_files](#get_files_search_files), which is a list of strings. Since GET http URLs have limits on what characters are allowed, but hydrus tags can have all sorts of characters, you'll be doing this:

*   Your list of tags:
    
    ```
    [ 'character:samus aran', 'creator:青い桜', 'system:height > 2000' ]
    ```
    
*   JSON encoded:
    
    ```json
    ["character:samus aran", "creator:\\u9752\\u3044\\u685c", "system:height > 2000"]
    ```
    
*   Then URL encoded:
    
    ```
    %5B%22character%3Asamus%20aran%22%2C%20%22creator%3A%5Cu9752%5Cu3044%5Cu685c%22%2C%20%22system%3Aheight%20%3E%202000%22%5D
    ```
    
*   In python, converting your tag list to the URL encoded string would be:
    
    ```
    urllib.parse.quote( json.dumps( tag_list ) )
    ```
    
*   Full URL path example:
    
    ```
    /get_files/search_files?file_sort_type=6&file_sort_asc=false&tags=%5B%22character%3Asamus%20aran%22%2C%20%22creator%3A%5Cu9752%5Cu3044%5Cu685c%22%2C%20%22system%3Aheight%20%3E%202000%22%5D
    ```
    

On 200 OK, the API returns JSON for everything except actual file/thumbnail requests. On 4XX and 5XX, assume it will return plain text, which may be a raw traceback that I'd be interested in seeing. You'll typically get 400 for a missing parameter, 401/403/419 for missing/insufficient/expired access, and 500 for a real deal serverside error.

!!! note
    For any request sent to the API, the total size of the initial request line (this includes the URL and any parameters) and the headers must not be larger than 2 megabytes.
    Exceeding this limit will cause the request to fail. Make sure to use pagination if you are passing very large JSON arrays as parameters in a GET request.
    

## CBOR

The API now tentatively supports CBOR, which is basically 'byte JSON'. If you are in a lower level language or need to do a lot of heavy work quickly, try it out!

To send CBOR, for POST put Content-Type `application/cbor` in your request header instead of `application/json`, and for GET just add a `cbor=1` parameter to the URL string. Use CBOR to encode any parameters that you would previously put in JSON:

For POST requests, just print the pure bytes in the body, like this:

```
cbor2.dumps( arg_dict )
```

For GET, encode the parameter value in base64, like this:

```
base64.urlsafe_b64encode( cbor2.dumps( argument ) )
```
-or-
```
str( base64.urlsafe_b64encode( cbor2.dumps( argument ) ), 'ascii' )
```

If you send CBOR, the client will return CBOR. If you want to send CBOR and get JSON back, or _vice versa_ (or you are uploading a file and can't set CBOR Content-Type), send the Accept request header, like so:

```
Accept: application/cbor
Accept: application/json
```

If the client does not support CBOR, you'll get 406.

## Access and permissions

The client gives access to its API through different 'access keys', which are the typical 64-character hex used in many other places across hydrus. Each guarantees different permissions such as handling files or tags. Most of the time, a user will provide full access, but do not assume this. If the access header or parameter is not provided, you will get 401, and all insufficient permission problems will return 403 with appropriate error text.

Access is required for every request. You can provide this as an http header, like so:

```
Hydrus-Client-API-Access-Key : 0150d9c4f6a6d2082534a997f4588dcf0c56dffe1d03ffbf98472236112236ae
```    

Or you can include it in the normal parameters of any request (except _POST /add\_files/add\_file_, which uses the entire POST body for the file's bytes). For GET, this means including it into the URL parameters:

```
/get_files/thumbnail?file_id=452158&Hydrus-Client-API-Access-Key=0150d9c4f6a6d2082534a997f4588dcf0c56dffe1d03ffbf98472236112236ae
```    

For POST, this means in the JSON body parameters, like so:

```
{
    "hash_id" : 123456,
    "Hydrus-Client-API-Access-Key" : "0150d9c4f6a6d2082534a997f4588dcf0c56dffe1d03ffbf98472236112236ae"
}
```

There is also a simple 'session' system, where you can get a temporary key that gives the same access without having to include the permanent access key in every request. You can fetch a session key with the [/session_key](#session_key) command and thereafter use it just as you would an access key, just with _Hydrus-Client-API-Session-Key_ instead.

Session keys will expire if they are not used within 24 hours, or if the client is restarted, or if the underlying access key is deleted. An invalid/expired session key will give a **419** result with an appropriate error text.

Bear in mind the Client API is still under construction. Setting up the Client API to be accessible across the internet requires technical experience to be convenient. HTTPS is available for encrypted comms, but the default certificate is self-signed (which basically means an eavesdropper can't see through it, but your ISP/government could if they decided to target you). If you have your own domain to host from and an SSL cert, you can replace them and it'll use them instead (check the db directory for client.crt and client.key). Otherwise, be careful about transmitting sensitive content outside of your localhost/network.

## Common Complex Parameters

### **files** { id="parameters_files" }

If you need to refer to some files, you can use any of the following:

Arguments:
:   
    *   `file_id`: (selective, a numerical file id)
    *   `file_ids`: (selective, a list of numerical file ids)
    *   `hash`: (selective, a hexadecimal SHA256 hash)
    *   `hashes`: (selective, a list of hexadecimal SHA256 hashes)

In GET requests, make sure any list is percent-encoded.

### **file domain** { id="parameters_file_domain" }

When you are searching, you may want to specify a particular file domain. Most of the time, you'll want to just set `file_service_key`, but this can get complex:

Arguments:
:   
    *   `file_service_key`: (optional, selective A, hexadecimal, the file domain on which to search)
    *   `file_service_keys`: (optional, selective A, list of hexadecimals, the union of file domains on which to search)
    *   `deleted_file_service_key`: (optional, selective B, hexadecimal, the 'deleted from this file domain' on which to search)
    *   `deleted_file_service_keys`: (optional, selective B, list of hexadecimals, the union of 'deleted from this file domain' on which to search)

The service keys are as in [/get\_services](#get_services).

Hydrus supports two concepts here:

* Searching over a UNION of subdomains. If the user has several local file domains, e.g. 'favourites', 'personal', 'sfw', and 'nsfw', they might like to search two of them at once.
* Searching deleted files of subdomains. You can specifically, and quickly, search the files that have been deleted from somewhere.

You can play around with this yourself by clicking 'multiple locations' in the client with _help->advanced mode_ on.

In extreme edge cases, these two can be mixed by populating both A and B selective, making a larger union of both current and deleted file records.

Please note that unions can be very very computationally expensive. If you can achieve what you want with a single file_service_key, two queries in a row with different service keys, or an umbrella like `all my files` or `all local files`, please do. Otherwise, let me know what is running slow and I'll have a look at it.

'deleted from all local files' includes all files that have been physically deleted (i.e. deleted from the trash) and not available any more for fetch file/thumbnail requests. 'deleted from all my files' includes all of those physically deleted files _and_ the trash. If a file is deleted with the special 'do not leave a deletion record' command, then it won't show up in a 'deleted from file domain' search!

'all known files' is a tricky domain. It converts much of the search tech to ignore where files actually are and look at the accompanying tag domain (e.g. all the files that have been tagged), and can sometimes be very expensive.

Also, if you have the option to set both file and tag domains, you cannot enter 'all known files'/'all known tags'. It is too complicated to support, sorry!

### **legacy service_name parameters** { id="legacy_service_name_parameters" }

The Client API used to respond to name-based service identifiers, for instance using 'my tags' instead of something like '6c6f63616c2074616773'. Service names can change, and they aren't _strictly_ unique either, so I have moved away from them, but there is some soft legacy support.

The client will attempt to convert any of these to their 'service_key(s)' equivalents:

* file_service_name
* tag_service_name
* service_names_to_tags
* service_names_to_actions_to_tags
* service_names_to_additional_tags

But I strongly encourage you to move away from them as soon as reasonably possible. Look up the service keys you need with [/get\_service](#get_service) or [/get\_services](#get_services).

If you have a clever script/program that does many things, then hit up [/get\_services](#get_services) on session initialisation and cache an internal map of key_to_name for the labels to use when you present services to the user.

Also, note that all users can now copy their service keys from _review services_.

## Access Management

### **GET `/api_version`** { id="api_version" }

_Gets the current API version. I will increment this every time I alter the API._

Restricted access: NO.
    
Required Headers: n/a
    
Arguments: n/a
    
Response:
: Some simple JSON describing the current api version (and hydrus client version, if you are interested).
: Note that this is mostly obselete now, since the 'Server' header of every response (and a duplicated 'Hydrus-Server' one, if you have a complicated proxy situation that overwrites 'Server') are now in the form "client api/{client_api_version} ({software_version})", e.g. "client api/32 (497)". 

```json title="Example response"
{
  "version" : 17,
  "hydrus_version" : 441
}
```

### **GET `/request_new_permissions`** { id="request_new_permissions" }

_Register a new external program with the client. This requires the 'add from api request' mini-dialog under_ services->review services _to be open, otherwise it will 403._

Restricted access: NO.
    
Required Headers: n/a
    
Arguments:
    
:   *   `name`: (descriptive name of your access)
    *   `basic_permissions`: A JSON-encoded list of numerical permission identifiers you want to request.
        
        The permissions are currently:

        *   0 - Import and Edit URLs
        *   1 - Import and Delete Files
        *   2 - Edit File Tags
        *   3 - Search for and Fetch Files
        *   4 - Manage Pages
        *   5 - Manage Cookies and Headers
        *   6 - Manage Database
        *   7 - Edit File Notes
        *   8 - Manage File Relationships

    ``` title="Example request"
    /request_new_permissions?name=my%20import%20script&basic_permissions=[0,1]
    ```
        
Response: 
:   Some JSON with your access key, which is 64 characters of hex. This will not be valid until the user approves the request in the client ui.
```json title="Example response"
{"access_key" : "73c9ab12751dcf3368f028d3abbe1d8e2a3a48d0de25e64f3a8f00f3a1424c57"}
```     

### **GET `/session_key`** { id="session_key" }

_Get a new session key._

Restricted access: YES. No permissions required.
    
Required Headers: n/a
    
Arguments: n/a
    
Response: 
:   Some JSON with a new session key in hex.    
```json title="Example response"
{
  "session_key" : "f6e651e7467255ade6f7c66050f3d595ff06d6f3d3693a3a6fb1a9c2b278f800"
}
```
        
!!! note
    Note that the access you provide to get a new session key **can** be a session key, if that happens to be useful. As long as you have some kind of access, you can generate a new session key.
    
    A session key expires after 24 hours of inactivity, whenever the client restarts, or if the underlying access key is deleted. A request on an expired session key returns 419.
    

### **GET `/verify_access_key`** { id="verify_access_key" }

_Check your access key is valid._

Restricted access: YES. No permissions required.
    
Required Headers: n/a
    
Arguments: n/a
    
Response: 
:   401/403/419 and some error text if the provided access/session key is invalid, otherwise some JSON with basic permission info. 
```json title="Example response"
{
  "basic_permissions" : [0, 1, 3],
  "human_description" : "API Permissions (autotagger): add tags to files, import files, search for files: Can search: only autotag this"
}
```
        

### **GET `/get_service`** { id="get_service" }

_Ask the client about a specific service._

Restricted access: 
:   YES. At least one of Add Files, Add Tags, Manage Pages, or Search Files permission needed.
    
Required Headers: n/a
    
Arguments:
:       
    *   `service_name`: (selective, string, the name of the service)
    *   `service_key`: (selective, hex string, the service key of the service)

Example requests:
:   
    ```title="Example requests"
    /get_service?service_name=my%20tags
    /get_service?service_key=6c6f63616c2074616773
    ```

Response: 
:   Some JSON about the service. The same basic format as [/get\_services](#get_services)
```json title="Example response"
{
  "service" : {
    "name" : "my tags",
    "service_key" : "6c6f63616c2074616773",
    "type" : 5,
    "type_pretty" : "local tag service"
  }
}
```

If the service does not exist, this gives 404. It is very unlikely but edge-case possible that two services will have the same name, in this case you'll get the pseudorandom first.

It will only respond to services in the /get_services list. I will expand the available types in future as we add ratings etc... to the Client API.

### **GET `/get_services`** { id="get_services" }

_Ask the client about its file and tag services._

Restricted access: 
:   YES. At least one of Add Files, Add Tags, Manage Pages, or Search Files permission needed.
    
Required Headers: n/a
    
Arguments: n/a
    
Response: 
:   Some JSON listing the client's file and tag services by name and 'service key'.
```json title="Example response"
{
  "local_tags" : [
    {
      "name" : "my tags",
      "service_key" : "6c6f63616c2074616773",
      "type" : 5,
      "type_pretty" : "local tag service"
    },
    {
      "name" : "filenames",
      "service_key" : "231a2e992b67101318c410abb6e7d98b6e32050623f138ca93bd4ad2993de31b",
      "type" : 5,
      "type_pretty" : "local tag service"
    }
  ],
  "tag_repositories" : [
    {
      "name" : "PTR",
      "service_key" : "ccb0cf2f9e92c2eb5bd40986f72a339ef9497014a5fb8ce4cea6d6c9837877d9",
      "type" : 0,
      "type_pretty" : "hydrus tag repository"
    }
  ],
  "file_repositories" : [
    {
      "name" : "kamehameha central",
      "service_key" : "89295dc26dae3ea7d395a1746a8fe2cb836b9472b97db48024bd05587f32ab0b",
      "type" : 1,
      "type_pretty" : "hydrus file repository"
    }
  ],
  "local_files" : [
    {
      "name" : "my files",
      "service_key" : "6c6f63616c2066696c6573",
      "type" : 2,
      "type_pretty" : "local file domain"
    }
  ],
  "all_local_media" : [
    {
      "name" : "all my files",
      "service_key" : "616c6c206c6f63616c206d65646961",
      "type" : 21,
      "type_pretty" : "virtual combined local media service"
    }
  ],
  "trash" : [
    {
      "name" : "trash",
      "service_key" : "7472617368",
      "type" : 14,
      "type_pretty" : "local trash file domain"
    }
  ],
  "local_updates" : [
    {
      "name" : "repository updates",
      "service_key" : "7265706f7369746f72792075706461746573",
      "type" : 20,
      "type_pretty" : "local update file domain"
    }
  ],
  "all_local_files" : [
    {
      "name" : "all local files",
      "service_key" : "616c6c206c6f63616c2066696c6573",
      "type" : 15,
      "type_pretty" : "virtual combined local file service"
    }
  ],
  "all_known_files" : [
    {
      "name" : "all known files",
      "service_key" : "616c6c206b6e6f776e2066696c6573",
      "type" : 11,
      "type_pretty" : "virtual combined file service"
    }
  ],
  "all_known_tags" : [
    {
      "name" : "all known tags",
      "service_key" : "616c6c206b6e6f776e2074616773",
      "type" : 10,
      "type_pretty" : "virtual combined tag service"
    }
  ]
}
```  

    Note that a user can rename their services, so while they will recognise `name`, it is not an excellent identifier, and definitely not something to save to any permanent config file.
    
    `service_key` is non-mutable and is the main service identifier. The hardcoded/initial services have shorter fixed service key strings (it is usually just 'all known files' etc.. ASCII-converted to hex), but user-created services will have random 64-character hex.
    
    Now that I state `type` and `type_pretty` here, I may rearrange this call, probably into a flat list. The `all_known_files` Object keys here are arbitrary.
    
    For service `type`, you won't see all these, and you'll only ever need some, but the enum is:
    
    * 0 - tag repository
    * 1 - file repository
    * 2 - a local file domain like 'my files'
    * 5 - a local tag domain like 'my tags'
    * 6 - a 'numerical' rating service with several stars
    * 7 - a 'like/dislike' rating service with on/off status
    * 10 - all known tags -- a union of all the tag services
    * 11 - all known files -- a union of all the file services and files that appear in tag services
    * 12 - the local booru -- you can ignore this
    * 13 - IPFS
    * 14 - trash
    * 15 - all local files -- all files on hard disk ('all my files' + updates + trash) 
    * 17 - file notes
    * 18 - Client API
    * 19 - all deleted files -- you can ignore this
    * 20 - local updates -- a file domain to store repository update files in
    * 21 - all my files -- union of all local file domains
    * 22 - a 'inc/dec' rating service with positive integer rating
    * 99 - server administration
    
    `type_pretty` is something you can show users if you like. Hydrus uses the same labels in _manage services_ and so on.

## Importing and Deleting Files

### **POST `/add_files/add_file`** { id="add_files_add_file" }

_Tell the client to import a file._

Restricted access:
:   YES. Import Files permission needed.
    
Required Headers:
:   - Content-Type: `application/json` (if sending path), `application/octet-stream` (if sending file)

Arguments (in JSON):
:   - `path`: (the path you want to import)

```json title="Example request body"
{"path" : "E:\\to_import\\ayanami.jpg"}
```

Arguments (as bytes): 
:   You can alternately just send the file's bytes as the POST body.
    
Response: 
:   Some JSON with the import result. Please note that file imports for large files may take several seconds, and longer if the client is busy doing other db work, so make sure your request is willing to wait that long for the response.
```json title="Example response"
{
  "status" : 1,
  "hash" : "29a15ad0c035c0a0e86e2591660207db64b10777ced76565a695102a481c3dd1",
  "note" : ""
}
```
    
    `status` is:
    
    *   1 - File was successfully imported
    *   2 - File already in database
    *   3 - File previously deleted
    *   4 - File failed to import
    *   7 - File vetoed
    
    A file 'veto' is caused by the file import options (which in this case is the 'quiet' set under the client's _options->importing_) stopping the file due to its resolution or minimum file size rules, etc...
    
    'hash' is the file's SHA256 hash in hexadecimal, and 'note' is some occasional additional human-readable text appropriate to the file status that you may recognise from hydrus's normal import workflow. For an import error, it will always be the full traceback.
    

### **POST `/add_files/delete_files`** { id="add_files_delete_files" }

_Tell the client to send files to the trash._

Restricted access:
:   YES. Import Files permission needed.
    
Required Headers:
:   
*   `Content-Type`: `application/json`

Arguments (in JSON):
:   
*   [files](#parameters_files)
*   [file domain](#parameters_file_domain) (optional, defaults to 'all my files')
*   `reason`: (optional, string, the reason attached to the delete action)

```json title="Example request body"
{"hash" : "78f92ba4a786225ee2a1236efa6b7dc81dd729faf4af99f96f3e20bad6d8b538"}
```
    
Response:
:   200 and no content.

If you specify a file service, the file will only be deleted from that location. Only local file domains are allowed (so you can't delete from a file repository or unpin from ipfs yet). It defaults to 'all my files', which will delete from all local services (i.e. force sending to trash). Sending 'all local files' on a file already in the trash will trigger a physical file delete. 

### **POST `/add_files/undelete_files`** { id="add_files_undelete_files" }

_Tell the client to pull files back out of the trash._

Restricted access:
:   YES. Import Files permission needed.
    
Required Headers:
:   
*   `Content-Type`: application/json

Arguments (in JSON):
:   
*   [files](#parameters_files)
*   [file domain](#parameters_file_domain) (optional, defaults to 'all my files')

```json title="Example request body"
{"hash" : "78f92ba4a786225ee2a1236efa6b7dc81dd729faf4af99f96f3e20bad6d8b538"}
```

Response: 
:   200 and no content.
    
You can use hash or hashes, whichever is more convenient.
    
This is the reverse of a delete_files--removing files from trash and putting them back where they came from. If you specify a file service, the files will only be undeleted to there (if they have a delete record, otherwise this is nullipotent). The default, 'all my files', undeletes to all local file services for which there are deletion records. There is no error if any of the files do not currently exist in 'trash'.
    

### **POST `/add_files/archive_files`** { id="add_files_archive_files" }

_Tell the client to archive inboxed files._

Restricted access: 
:  YES. Import Files permission needed.
    
Required Headers:
:   
*   `Content-Type`: application/json

Arguments (in JSON):
:  
*   [files](#parameters_files)

```json title="Example request body"
{"hash" : "78f92ba4a786225ee2a1236efa6b7dc81dd729faf4af99f96f3e20bad6d8b538"}
```
    
Response: 
:   200 and no content.
    
This puts files in the 'archive', taking them out of the inbox. It only has meaning for files currently in 'my files' or 'trash'. There is no error if any files do not currently exist or are already in the archive.
    

### **POST `/add_files/unarchive_files`** { id="add_files_unarchive_files" }

_Tell the client re-inbox archived files._

Restricted access: 
:  YES. Import Files permission needed.
    
Required Headers:
:   
*   `Content-Type`: application/json

Arguments (in JSON):
:  
*   [files](#parameters_files)

```json title="Example request body"
{"hash" : "78f92ba4a786225ee2a1236efa6b7dc81dd729faf4af99f96f3e20bad6d8b538"}
```
    
Response: 
:   200 and no content.
    
This puts files back in the inbox, taking them out of the archive. It only has meaning for files currently in 'my files' or 'trash'. There is no error if any files do not currently exist or are already in the inbox.
    

## Importing and Editing URLs

### **GET `/add_urls/get_url_files`** { id="add_urls_get_url_files" }

_Ask the client about an URL's files._

Restricted access:
:   YES. Import URLs permission needed.
    
Required Headers: n/a
    
Arguments:
:       
    *   `url`: (the url you want to ask about)
    *   `doublecheck_file_system`: true or false (optional, defaults False)

Example request:
:   for URL `http://safebooru.org/index.php?page=post&s=view&id=2753608`:
    ```
    /add_urls/get_url_files?url=http%3A%2F%2Fsafebooru.org%2Findex.php%3Fpage%3Dpost%26s%3Dview%26id%3D2753608
    ```

Response: 
:   Some JSON which files are known to be mapped to that URL. Note this needs a database hit, so it may be delayed if the client is otherwise busy. Don't rely on this to always be fast. 
```json title="Example response"
{
  "normalised_url" : "https://safebooru.org/index.php?id=2753608&page=post&s=view",
  "url_file_statuses" : [
    {
      "status" : 2,
      "hash" : "20e9002824e5e7ffc240b91b6e4a6af552b3143993c1778fd523c30d9fdde02c",
      "note" : "url recognised: Imported at 2015/10/18 10:58:01, which was 3 years 4 months ago (before this check)."
    }
  ]
}
```

The `url_file_statuses` is a list of zero-to-n JSON Objects, each representing a file match the client found in its database for the URL. Typically, it will be of length 0 (for as-yet-unvisited URLs or Gallery/Watchable URLs that are not attached to files) or 1, but sometimes multiple files are given the same URL (sometimes by mistaken misattribution, sometimes by design, such as pixiv manga pages). Handling n files per URL is a pain but an unavoidable issue you should account for.

`status` is the same as for `/add_files/add_file`:

  *   0 - File not in database, ready for import (you will only see this very rarely--usually in this case you will just get no matches)
  *   2 - File already in database
  *   3 - File previously deleted

`hash` is the file's SHA256 hash in hexadecimal, and 'note' is some occasional additional human-readable text you may recognise from hydrus's normal import workflow.

If you set `doublecheck_file_system` to `true`, then any result that is 'already in db' (2) will be double-checked against the actual file system. This check happens on any normal file import process, just to check for and fix missing files (if the file is missing, the status becomes 0--new), but the check can take more than a few milliseconds on an HDD or a network drive, so the default behaviour, assuming you mostly just want to spam for 'seen this before' file statuses, is to not do it. 

### **GET `/add_urls/get_url_info`** { id="add_urls_get_url_info" }

_Ask the client for information about a URL._

Restricted access:
:   YES. Import URLs permission needed.
    
Required Headers: n/a
    
Arguments:
:   
    *   `url`: (the url you want to ask about)

Example request:
:   for URL `https://8ch.net/tv/res/1846574.html`:
    ```
    /add_urls/get_url_info?url=https%3A%2F%2F8ch.net%2Ftv%2Fres%2F1846574.html
    ```
        
Response: 
:   Some JSON describing what the client thinks of the URL.
```json title="Example response"
{
  "normalised_url" : "https://8ch.net/tv/res/1846574.html",
  "url_type" : 4,
  "url_type_string" : "watchable url",
  "match_name" : "8chan thread",
  "can_parse" : true
}
```

    The url types are currently:
    
    *   0 - Post URL
    *   2 - File URL
    *   3 - Gallery URL
    *   4 - Watchable URL
    *   5 - Unknown URL (i.e. no matching URL Class)
    
    'Unknown' URLs are treated in the client as direct File URLs. Even though the 'File URL' type is available, most file urls do not have a URL Class, so they will appear as Unknown. Adding them to the client will pass them to the URL Downloader as a raw file for download and import.
    

### **POST `/add_urls/add_url`** { id="add_urls_add_url" }

_Tell the client to 'import' a URL. This triggers the exact same routine as drag-and-dropping a text URL onto the main client window._

Restricted access: 
:   YES. Import URLs permission needed. Add Tags needed to include tags.
    
Required Headers:
:   
    *   `Content-Type`: `application/json`

Arguments (in JSON):
:    

    *   `url`: (the url you want to add)
    *   `destination_page_key`: (optional page identifier for the page to receive the url)
    *   `destination_page_name`: (optional page name to receive the url)
    *   `show_destination_page`: (optional, defaulting to false, controls whether the UI will change pages on add)
    *   `service_keys_to_additional_tags`: (optional, selective, tags to give to any files imported from this url)
    *   `filterable_tags`: (optional tags to be filtered by any tag import options that applies to the URL)

If you specify a `destination_page_name` and an appropriate importer page already exists with that name, that page will be used. Otherwise, a new page with that name will be recreated (and used by subsequent calls with that name). Make sure it that page name is unique (e.g. '/b/ threads', not 'watcher') in your client, or it may not be found.

Alternately, `destination_page_key` defines exactly which page should be used. Bear in mind this page key is only valid to the current session (they are regenerated on client reset or session reload), so you must figure out which one you want using the [/manage\_pages/get\_pages](#manage_pages_get_pages) call. If the correct page_key is not found, or the page it corresponds to is of the incorrect type, the standard page selection/creation rules will apply.

`show_destination_page` defaults to False to reduce flicker when adding many URLs to different pages quickly. If you turn it on, the client will behave like a URL drag and drop and select the final page the URL ends up on.

`service_keys_to_additional_tags` uses the same data structure as in /add\_tags/add\_tags--service keys to a list of tags to add. You will need 'add tags' permission or this will 403. These tags work exactly as 'additional' tags work in a _tag import options_. They are service specific, and always added unless some advanced tag import options checkbox (like 'only add tags to new files') is set.

filterable_tags works like the tags parsed by a hydrus downloader. It is just a list of strings. They have no inherant service and will be sent to a _tag import options_, if one exists, to decide which tag services get what. This parameter is useful if you are pulling all a URL's tags outside of hydrus and want to have them processed like any other downloader, rather than figuring out service names and namespace filtering on your end. Note that in order for a tag import options to kick in, I think you will have to have a Post URL URL Class hydrus-side set up for the URL so some tag import options (whether that is Class-specific or just the default) can be loaded at import time.

```json title="Example request body"
{
  "url" : "https://8ch.net/tv/res/1846574.html",
  "destination_page_name" : "kino zone",
  "service_keys_to_additional_tags" : {
    "6c6f63616c2074616773" : ["as seen on /tv/"]
  }
}
```
```json title="Example request body"
{
  "url" : "https://safebooru.org/index.php?page=post&s=view&id=3195917",
  "filterable_tags" : [
    "1girl",
    "artist name",
    "creator:azto dio",
    "blonde hair",
    "blue eyes",
    "breasts",
    "character name",
    "commentary",
    "english commentary",
    "formal",
    "full body",
    "glasses",
    "gloves",
    "hair between eyes",
    "high heels",
    "highres",
    "large breasts",
    "long hair",
    "long sleeves",
    "looking at viewer",
    "series:metroid",
    "mole",
    "mole under mouth",
    "patreon username",
    "ponytail",
    "character:samus aran",
    "solo",
    "standing",
    "suit",
    "watermark"
  ]
}
```
        
Response:
:   Some JSON with info on the URL added.
```json title="Example response"
{
  "human_result_text" : "\"https://8ch.net/tv/res/1846574.html\" URL added successfully.",
  "normalised_url" : "https://8ch.net/tv/res/1846574.html"
}
```

        

### **POST `/add_urls/associate_url`** { id="add_urls_associate_url" }

_Manage which URLs the client considers to be associated with which files._

Restricted access: 
:   YES. Import URLs permission needed.
    
Required Headers:
:       
    *   `Content-Type`: `application/json`


Arguments (in JSON):
:   
    *   `url_to_add`: (optional, selective A, an url you want to associate with the file(s))
    *   `urls_to_add`: (optional, selective A, a list of urls you want to associate with the file(s))
    *   `url_to_delete`: (optional, selective B, an url you want to disassociate from the file(s))
    *   `urls_to_delete`: (optional, selective B, a list of urls you want to disassociate from the file(s))
    *   [files](#parameters_files)

    The single/multiple arguments work the same--just use whatever is convenient for you. Unless you really know what you are doing with URL Classes, I strongly recommend you stick to associating URLs with just one single 'hash' at a time. Multiple hashes pointing to the same URL is unusual and frequently unhelpful.
```json title="Example request body"
{
  "url_to_add" : "https://rule34.xxx/index.php?id=2588418&page=post&s=view",
  "hash" : "3b820114f658d768550e4e3d4f1dced3ff8db77443472b5ad93700647ad2d3ba"
}
```
        
Response: 
:   200 with no content. Like when adding tags, this is safely idempotent--do not worry about re-adding URLs associations that already exist or accidentally trying to delete ones that don't.
    

## Editing File Tags

### **GET `/add_tags/clean_tags`** { id="add_tags_clean_tags" }

_Ask the client about how it will see certain tags._

Restricted access: 
:   YES. Add Tags permission needed.
    
Required Headers: n/a
    
Arguments (in percent-encoded JSON):
:   
*   `tags`: (a list of the tags you want cleaned)

Example request:
:   Given tags `#!json [ " bikini ", "blue    eyes", " character : samus aran ", " :)", "   ", "", "10", "11", "9", "system:wew", "-flower" ]`:
    ```
    /add_tags/clean_tags?tags=%5B%22%20bikini%20%22%2C%20%22blue%20%20%20%20eyes%22%2C%20%22%20character%20%3A%20samus%20aran%20%22%2C%20%22%3A%29%22%2C%20%22%20%20%20%22%2C%20%22%22%2C%20%2210%22%2C%20%2211%22%2C%20%229%22%2C%20%22system%3Awew%22%2C%20%22-flower%22%5D
    ```

Response: 
:  The tags cleaned according to hydrus rules. They will also be in hydrus human-friendly sorting order.
```json title="Example response"
{
  "tags" : ["9", "10", "11", " ::)", "bikini", "blue eyes", "character:samus aran", "flower", "wew"]
}
```

    Mostly, hydrus simply trims excess whitespace, but the other examples are rare issues you might run into. 'system' is an invalid namespace, tags cannot be prefixed with hyphens, and any tag starting with ':' is secretly dealt with internally as "\[no namespace\]:\[colon-prefixed-subtag\]". Again, you probably won't run into these, but if you see a mismatch somewhere and want to figure it out, or just want to sort some numbered tags, you might like to try this.
    

### **GET `/add_tags/search_tags`** { id="add_tags_search_tags" }

_Search the client for tags._

Restricted access:
:   YES. Search for Files permission needed.

Required Headers: n/a

Arguments:
:   
    * `search`: (the tag text to search for, enter exactly what you would in the client UI)
    * [file domain](#parameters_file_domain) (optional, defaults to 'all my files')
    * `tag_service_key`: (optional, hexadecimal, the tag domain on which to search, defaults to 'all known tags')
    * `tag_display_type`: (optional, string, to select whether to search raw or sibling-processed tags, defaults to 'storage')

The `file domain` and `tag_service_key` perform the function of the file and tag domain buttons in the client UI.

The `tag_display_type` can be either `storage` (the default), which searches your file's stored tags, just as they appear in a 'manage tags' dialog, or `display`, which searches the sibling-processed tags, just as they appear in a normal file search page. In the example above, setting the `tag_display_type` to `display` could well combine the two kim possible tags and give a count of 3 or 4. 

'all my files'/'all known tags' works fine for most cases, but a specific tag service or 'all known files'/'tag service' can work better for editing tag repository `storage` contexts, since it provides results just for that service, and for repositories, it gives tags for all the non-local files other users have tagged.

Example request:
:   
```http title="Example request"
/add_tags/search_tags?search=kim&tag_display_type=display
```

Response:
:   Some JSON listing the client's matching tags.

:   
```json title="Example response"
{
  "tags" : [
    {
      "value" : "series:kim possible", 
      "count" : 3
    },
    {
      "value" : "kimchee", 
      "count" : 2
    },
    {
      "value" : "character:kimberly ann possible", 
      "count" : 1
    }
  ]
}
```

The `tags` list will be sorted by descending count. The various rules in _tags->manage tag display and search_ (e.g. no pure `*` searches on certain services) will also be checked--and if violated, you will get 200 OK but an empty result.

Note that if your client api access is only allowed to search certain tags, the results will be similarly filtered.

### **POST `/add_tags/add_tags`** { id="add_tags_add_tags" }

_Make changes to the tags that files have._

Restricted access:
:   YES. Add Tags permission needed.
    
Required Headers: n/a
    
Arguments (in JSON):
:   
*   [files](#parameters_files)
*   `service_keys_to_tags`: (selective B, an Object of service keys to lists of tags to be 'added' to the files)
*   `service_keys_to_actions_to_tags`: (selective B, an Object of service keys to content update actions to lists of tags)

    In 'service\_keys\_to...', the keys are as in [/get\_services](#get_services). You may need some selection UI on your end so the user can pick what to do if there are multiple choices.
    
    Also, you can use either '...to\_tags', which is simple and add-only, or '...to\_actions\_to\_tags', which is more complicated and allows you to remove/petition or rescind pending content.
    
    The permitted 'actions' are:

    *   0 - Add to a local tag service.
    *   1 - Delete from a local tag service.
    *   2 - Pend to a tag repository.
    *   3 - Rescind a pend from a tag repository.
    *   4 - Petition from a tag repository. (This is special)
    *   5 - Rescind a petition from a tag repository.

    When you petition a tag from a repository, a 'reason' for the petition is typically needed. If you send a normal list of tags here, a default reason of "Petitioned from API" will be given. If you want to set your own reason, you can instead give a list of \[ tag, reason \] pairs.

Some example requests:
:   
```json title="Adding some tags to a file"
{
  "hash" : "df2a7b286d21329fc496e3aa8b8a08b67bb1747ca32749acb3f5d544cbfc0f56",
  "service_keys_to_tags" : {
    "6c6f63616c2074616773" : ["character:supergirl", "rating:safe"]
  }
}
```
```json title="Adding more tags to two files"
{
  "hashes" : [
    "df2a7b286d21329fc496e3aa8b8a08b67bb1747ca32749acb3f5d544cbfc0f56",
    "f2b022214e711e9a11e2fcec71bfd524f10f0be40c250737a7861a5ddd3faebf"
  ],
  "service_keys_to_tags" : {
    "6c6f63616c2074616773" : ["process this"],
    "ccb0cf2f9e92c2eb5bd40986f72a339ef9497014a5fb8ce4cea6d6c9837877d9" : ["creator:dandon fuga"]
  }
}
```
```json title="A complicated transaction with all possible actions"
{
  "hash" : "df2a7b286d21329fc496e3aa8b8a08b67bb1747ca32749acb3f5d544cbfc0f56",
  "service_keys_to_actions_to_tags" : {
    "6c6f63616c2074616773" : {
      "0" : ["character:supergirl", "rating:safe"],
      "1" : ["character:superman"]
    },
    "aa0424b501237041dab0308c02c35454d377eebd74cfbc5b9d7b3e16cc2193e9" : {
      "2" : ["character:supergirl", "rating:safe"],
      "3" : ["filename:image.jpg"],
      "4" : [["creator:danban faga", "typo"], ["character:super_girl", "underscore"]],
      "5" : ["skirt"]
    }
  }
}
```

    This last example is far more complicated than you will usually see. Pend rescinds and petition rescinds are not common. Petitions are also quite rare, and gathering a good petition reason for each tag is often a pain.

    Note that the enumerated status keys in the service\_keys\_to\_actions\_to_tags structure are strings, not ints (JSON does not support int keys for Objects).

Response description:
:  200 and no content.

!!! note
    Note also that hydrus tag actions are safely idempotent. You can pend a tag that is already pended, or add a tag that already exists, and not worry about an error--the surplus add action will be discarded. The same is true if you try to pend a tag that actually already exists, or rescinding a petition that doesn't. Any invalid actions will fail silently.
    
    It is fine to just throw your 'process this' tags at every file import and not have to worry about checking which files you already added them to.

!!! danger "HOWEVER"
    When you delete a tag, a deletion record is made _even if the tag does not exist on the file_. This is important if you expect to add the tags again via parsing, because, in general, when hydrus adds tags through a downloader, it will not overwrite a previously 'deleted' tag record (this is to stop re-downloads overwriting the tags you hand-removed previously). Undeletes usually have to be done manually by a human.  
    
    So, _do_ be careful about how you spam delete unless it is something that doesn't matter or it is something you'll only be touching again via the API anyway.

## Editing File Notes

### **POST `/add_notes/set_notes`** { id="add_notes_set_notes" }

_Add or update notes associated with a file._

Restricted access: 
:   YES. Add Notes permission needed.
    
Required Headers:
:       
    *   `Content-Type`: `application/json`
    
Arguments (in percent-encoded JSON):
:   
* `notes`: (an Object mapping string names to string texts)
* `hash`: (selective, an SHA256 hash for the file in 64 characters of hexadecimal)
* `file_id`: (selective, the integer numerical identifier for the file)
* `merge_cleverly`: true or false (optional, defaults false)
* `extend_existing_note_if_possible`: true or false (optional, defaults true)
* `conflict_resolution`: 0, 1, 2, or 3 (optional, defaults 3)

With `merge_cleverly` left `false`, then this is a simple update operation. Existing notes will be overwritten exactly as you specify. Any other notes the file has will be untouched.
```json title="Example request body"
{
  "notes" : {
      "note name" : "content of note",
      "another note" : "asdf"
  },
  "hash" : "3b820114f658d768550e4e3d4f1dced3ff8db77443472b5ad93700647ad2d3ba"
}
```

If you turn on `merge_cleverly`, then the client will merge your new notes into the file's existing notes using the same logic you have seen in Note Import Options and the Duplicate Metadata Merge Options. This navigates conflict resolution, and you should use it if you are adding potential duplicate content from an 'automatic' source like a parser and do not want to wade into the logic. Do not use it for a user-editing experience (a user expects a strict overwrite/replace experience and will be confused by this mode).

To start off, in this mode, if your note text exists under a different name for the file, your dupe note will not be added to your new name. `extend_existing_note_if_possible` makes it so your existing note text will overwrite an existing name (or a '... (1)' rename of that name) if the existing text is inside your given text. `conflict_resolution` is an enum governing what to do in all other conflicts:

_If a new note name already exists and its new text differs from what already exists:_
:  
* 0 - replace - Overwrite the existing conflicting note.
* 1 - ignore - Make no changes.
* 2 - append - Append the new text to the existing text.
* 3 - rename (default) - Add the new text under a 'name (x)'-style rename.

Response: 
:   200 with the note changes actually sent through. If `merge_cleverly=false`, this is exactly what you gave, and this operation is idempotent. If `merge_cleverly=true`, then this may differ, even be empty, and this operation might not be idempotent.
```json title="Example response"
{
  "notes" : {
    "note name" : "content of note",
    "another note (1)" : "asdf"
  }
}
```


### **POST `/add_notes/delete_notes`** { id="add_notes_delete_notes" }

_Remove notes associated with a file._

Restricted access: 
:   YES. Add Notes permission needed.
    
Required Headers:
:       
    *   `Content-Type`: `application/json`
    
Arguments (in percent-encoded JSON):
:   
*   `note_names`: (a list of string note names to delete)
*   `hash`: (selective, an SHA256 hash for the file in 64 characters of hexadecimal)
*   `file_id`: (selective, the integer numerical identifier for the file)

```json title="Example request body"
{
  "note_names" : ["note name", "another note"],
  "hash" : "3b820114f658d768550e4e3d4f1dced3ff8db77443472b5ad93700647ad2d3ba"
}
```

Response:  
:   200 with no content. This operation is idempotent.

## Searching and Fetching Files

File search in hydrus is not paginated like a booru--all searches return all results in one go. In order to keep this fast, search is split into two steps--fetching file identifiers with a search, and then fetching file metadata in batches. You may have noticed that the client itself performs searches like this--thinking a bit about a search and then bundling results in batches of 256 files before eventually throwing all the thumbnails on screen.

### **GET `/get_files/search_files`** { id="get_files_search_files" }

_Search for the client's files._

Restricted access: 
:   YES. Search for Files permission needed. Additional search permission limits may apply.
    
Required Headers: n/a
    
Arguments (in percent-encoded JSON):
:   
    *   `tags`: (a list of tags you wish to search for)
    *   [file domain](#parameters_file_domain) (optional, defaults to 'all my files')
    *   `tag_service_key`: (optional, hexadecimal, the tag domain on which to search, defaults to 'all my files')
    *   `file_sort_type`: (optional, integer, the results sort method, defaults to 'all known tags')
    *   `file_sort_asc`: true or false (optional, the results sort order)
    *   `return_file_ids`: true or false (optional, default true, returns file id results)
    *   `return_hashes`: true or false (optional, default false, returns hex hash results)

``` title='Example request for 16 files (system:limit=16) in the inbox with tags "blue eyes", "blonde hair", and "кино"'
/get_files/search_files?tags=%5B%22blue%20eyes%22%2C%20%22blonde%20hair%22%2C%20%22%5Cu043a%5Cu0438%5Cu043d%5Cu043e%22%2C%20%22system%3Ainbox%22%2C%20%22system%3Alimit%3D16%22%5D
```
    

If the access key's permissions only permit search for certain tags, at least one positive whitelisted/non-blacklisted tag must be in the "tags" list or this will 403. Tags can be prepended with a hyphen to make a negated tag (e.g. "-green eyes"), but these will not be checked against the permissions whitelist.

Wildcards and namespace searches are supported, so if you search for 'character:sam*' or 'series:*', this will be handled correctly clientside.

**Many system predicates are also supported using a text parser!** The parser was designed by a clever user for human input and allows for a certain amount of error (e.g. ~= instead of ≈, or "isn't" instead of "is not") or requires more information (e.g. the specific hashes for a hash lookup). **Here's a big list of examples that are supported:**

??? example "System Predicates" 
    *   system:everything
    *   system:inbox
    *   system:archive
    *   system:has duration
    *   system:no duration
    *   system:is the best quality file of its duplicate group
    *   system:is not the best quality file of its duplicate group
    *   system:has audio
    *   system:no audio
    *   system:has exif
    *   system:no exif
    *   system:has human-readable embedded metadata
    *   system:no human-readable embedded metadata
    *   system:has icc profile
    *   system:no icc profile
    *   system:has tags
    *   system:no tags
    *   system:untagged
    *   system:number of tags > 5
    *   system:number of tags ~= 10
    *   system:number of tags > 0
    *   system:number of words < 2
    *   system:height = 600
    *   system:height > 900
    *   system:width < 200
    *   system:width > 1000
    *   system:filesize ~= 50 kilobytes
    *   system:filesize > 10megabytes
    *   system:filesize < 1 GB
    *   system:filesize > 0 B
    *   system:similar to abcdef01 abcdef02 abcdef03, abcdef04 with distance 3
    *   system:similar to abcdef distance 5
    *   system:limit = 100
    *   system:filetype = image/jpg, image/png, apng
    *   system:hash = abcdef01 abcdef02 abcdef03 _(this does sha256)_
    *   system:hash = abcdef01 abcdef02 md5
    *   system:modified date < 7 years 45 days 7h
    *   system:modified date > 2011-06-04
    *   system:last viewed time < 7 years 45 days 7h
    *   system:last view time < 7 years 45 days 7h
    *   system:date modified > 7 years 2 months
    *   system:date modified < 0 years 1 month 1 day 1 hour
    *   system:import time < 7 years 45 days 7h
    *   system:time imported < 7 years 45 days 7h
    *   system:time imported > 2011-06-04
    *   system:time imported > 7 years 2 months
    *   system:time imported < 0 years 1 month 1 day 1 hour
    *   system:time imported ~= 2011-1-3
    *   system:time imported ~= 1996-05-2
    *   system:duration < 5 seconds
    *   system:duration ~= 600 msecs
    *   system:duration > 3 milliseconds
    *   system:file service is pending to my files
    *   system:file service currently in my files
    *   system:file service is not currently in my files
    *   system:file service is not pending to my files
    *   system:number of file relationships = 2 duplicates
    *   system:number of file relationships > 10 potential duplicates
    *   system:num file relationships < 3 alternates
    *   system:num file relationships > 3 false positives
    *   system:ratio is wider than 16:9
    *   system:ratio is 16:9
    *   system:ratio taller than 1:1
    *   system:num pixels > 50 px
    *   system:num pixels < 1 megapixels
    *   system:num pixels ~= 5 kilopixel
    *   system:media views ~= 10
    *   system:all views > 0
    *   system:preview views < 10
    *   system:media viewtime < 1 days 1 hour 0 minutes
    *   system:all viewtime > 1 hours 100 seconds
    *   system:preview viewtime ~= 1 day 30 hours 100 minutes 90s
    *   system:has url matching regex index\\.php
    *   system:does not have a url matching regex index\\.php
    *   system:has url https://safebooru.donmai.us/posts/4695284
    *   system:does not have url https://safebooru.donmai.us/posts/4695284
    *   system:has domain safebooru.com
    *   system:does not have domain safebooru.com
    *   system:has a url with class safebooru file page
    *   system:does not have a url with url class safebooru file page
    *   system:tag as number page < 5
    *   system:has notes
    *   system:no notes
    *   system:does not have notes
    *   system:num notes is 5
    *   system:num notes > 1
    *   system:has note with name note name
    *   system:no note with name note name
    *   system:does not have note with name note name

Please test out the system predicates you want to send. If you are in _help-&gt;advanced mode_, you can test this parser in the advanced text input dialog when you click the OR\* button on a tag autocomplete dropdown. More system predicate types and input formats will be available in future. Reverse engineering system predicate data from text is obviously tricky. If a system predicate does not parse, you'll get 400.

Also, OR predicates are now supported! Just nest within the tag list, and it'll be treated like an OR. For instance:

*   `#!json [ "skirt", [ "samus aran", "lara croft" ], "system:height > 1000" ]`

Makes:

*   skirt
*   samus aran OR lara croft
*   system:height > 1000

The file and tag services are for search domain selection, just like clicking the buttons in the client. They are optional--default is 'all my files' and 'all known tags'. 

File searches occur in the `display` `tag_display_type`. If you want to pair autocomplete tag lookup from [/search_tags](#add_tags_search_tags) to this file search (e.g. for making a standard booru search interface), then make sure you are searching `display` tags there.

file\_sort\_asc is 'true' for ascending, and 'false' for descending. The default is descending.

file\_sort\_type is by default _import time_. It is an integer according to the following enum, and I have written the semantic (asc/desc) meaning for each type after:

* 0 - file size (smallest first/largest first)
* 1 - duration (shortest first/longest first)
* 2 - import time (oldest first/newest first)
* 3 - filetype (N/A)
* 4 - random (N/A)
* 5 - width (slimmest first/widest first)
* 6 - height (shortest first/tallest first)
* 7 - ratio (tallest first/widest first)
* 8 - number of pixels (ascending/descending)
* 9 - number of tags (on the current tag domain) (ascending/descending)
* 10 - number of media views (ascending/descending)
* 11 - total media viewtime (ascending/descending)
* 12 - approximate bitrate (smallest first/largest first)
* 13 - has audio (audio first/silent first)
* 14 - modified time (oldest first/newest first)
* 15 - framerate (slowest first/fastest first)
* 16 - number of frames (smallest first/largest first)
* 18 - last viewed time (oldest first/newest first)
* 19 - archive timestamp (oldest first/newest first)
* 20 - hash hex (N/A)

Response:
:   The full list of numerical file ids that match the search.
```json title="Example response"
{
	"file_ids" : [125462, 4852415, 123, 591415]
}
```
```json title="Example response with return_hashes=true"
{
  "hashes" : [
    "1b04c4df7accd5a61c5d02b36658295686b0abfebdc863110e7d7249bba3f9ad",
    "fe416723c731d679aa4d20e9fd36727f4a38cd0ac6d035431f0f452fad54563f",
    "b53505929c502848375fbc4dab2f40ad4ae649d34ef72802319a348f81b52bad"
  ],
  "file_ids" : [125462, 4852415, 123]
}
```

    You can of course also specify `return_hashes=true&return_file_ids=false` just to get the hashes. The order of both lists is the same.

    File ids are internal and specific to an individual client. For a client, a file with hash H always has the same file id N, but two clients will have different ideas about which N goes with which H. IDs are a bit faster to retrieve than hashes and search with _en masse_, which is why they are exposed here.

    This search does **not** apply the implicit limit that most clients set to all searches (usually 10,000), so if you do system:everything on a client with millions of files, expect to get boshed. Even with a system:limit included, complicated queries with large result sets may take several seconds to respond. Just like the client itself.

### **GET `/get_files/file_hashes`** { id="get_files_file_hashes" }

_Lookup file hashes from other hashes._

Restricted access: 
:   YES. Search for Files permission needed.
    
Required Headers: n/a
    
Arguments (in percent-encoded JSON):
:   
    *   `hash`: (selective, a hexadecimal hash)
    *   `hashes`: (selective, a list of hexadecimal hashes)
    *   `source_hash_type`: [sha256|md5|sha1|sha512] (optional, defaulting to sha256)
    *   `desired_hash_type`: [sha256|md5|sha1|sha512]

If you have some MD5 hashes and want to see what their SHA256 are, or _vice versa_, this is the place. Hydrus records the non-SHA256 hashes for every file it has ever imported. This data is not removed on file deletion.

``` title="Example request"
/get_files/file_hashes?hash=ec5c5a4d7da4be154597e283f0b6663c&source_hash_type=md5&desired_hash_type=sha256
```

Response:
:   A mapping Object of the successful lookups. Where no matching hash is found, no entry will be made (therefore, if none of your source hashes have matches on the client, this will return an empty `hashes` Object).
```json title="Example response"
{
  "hashes" : {
    "ec5c5a4d7da4be154597e283f0b6663c" : "2a0174970defa6f147f2eabba829c5b05aba1f1aea8b978611a07b7bb9cf9399"
  }
}
```

### **GET `/get_files/file_metadata`** { id="get_files_file_metadata" }

_Get metadata about files in the client._

Restricted access: 
:   YES. Search for Files permission needed. Additional search permission limits may apply.

Required Headers: n/a

Arguments (in percent-encoded JSON):
:   
    *   [files](#parameters_files)
    *   `create_new_file_ids`: true or false (optional if asking with hash(es), defaulting to false)
    *   `only_return_identifiers`: true or false (optional, defaulting to false)
    *   `only_return_basic_information`: true or false (optional, defaulting to false)
    *   `detailed_url_information`: true or false (optional, defaulting to false)
    *   `include_notes`: true or false (optional, defaulting to false)
    *   `hide_service_keys_tags`: **Deprecated, will be deleted soon!** true or false (optional, defaulting to true)

If your access key is restricted by tag, **the files you search for must have been in the most recent search result**.

``` title="Example request for two files with ids 123 and 4567"
/get_files/file_metadata?file_ids=%5B123%2C%204567%5D
```
    
``` title="The same, but only wants hashes back"
/get_files/file_metadata?file_ids=%5B123%2C%204567%5D&only_return_identifiers=true
```
    
``` title="And one that fetches two hashes"
/get_files/file_metadata?hashes=%5B%224c77267f93415de0bc33b7725b8c331a809a924084bee03ab2f5fae1c6019eb2%22%2C%20%223e7cb9044fe81bda0d7a84b5cb781cba4e255e4871cba6ae8ecd8207850d5b82%22%5D
```

This request string can obviously get pretty ridiculously long. It also takes a bit of time to fetch metadata from the database. In its normal searches, the client usually fetches file metadata in batches of 256.

Response:
:   A list of JSON Objects that store a variety of file metadata.
```json title="Example response"
{
  "metadata" : [
    {
      "file_id" : 123,
      "hash" : "4c77267f93415de0bc33b7725b8c331a809a924084bee03ab2f5fae1c6019eb2",
      "size" : 63405,
      "mime" : "image/jpeg",
      "ext" : ".jpg",
      "width" : 640,
      "height" : 480,
      "thumbnail_width" : 200,
      "thumbnail_height" : 150,
      "duration" : null,
      "time_modified" : null,
      "time_modified_details" : {},
      "file_services" : {
        "current" : {},
        "deleted" : {}
      },
      "ipfs_multihashes" : {},
      "has_audio" : false,
      "num_frames" : null,
      "num_words" : null,
      "is_inbox" : false,
      "is_local" : false,
      "is_trashed" : false,
      "is_deleted" : false,
      "has_exif" : true,
      "has_human_readable_embedded_metadata" : true,
      "has_icc_profile" : true,
      "known_urls" : [],
      "tags" : {
        "6c6f63616c2074616773" : {
          "name" : "local tags",
          "type" : 5,
          "type_pretty" : "local tag service",
          "storage_tags" : {},
          "display_tags" : {}
        },
        "37e3849bda234f53b0e9792a036d14d4f3a9a136d1cb939705dbcd5287941db4" : {
          "name" : "public tag repo",
          "type" : 1,
          "type_pretty" : "hydrus tag repository",
          "storage_tags" : {},
          "display_tags" : {}
        },
        "616c6c206b6e6f776e2074616773" : {
          "name" : "all known tags",
          "type" : 10,
          "type_pretty" : "virtual combined tag service",
          "storage_tags" : {},
          "display_tags" : {}
        }
      }
    },
    {
      "file_id" : 4567,
      "hash" : "3e7cb9044fe81bda0d7a84b5cb781cba4e255e4871cba6ae8ecd8207850d5b82",
      "size" : 199713,
      "mime" : "video/webm",
      "ext" : ".webm",
      "width" : 1920,
      "height" : 1080,
      "thumbnail_width" : 200,
      "thumbnail_height" : 113,
      "duration" : 4040,
      "time_modified" : 1604055647,
      "time_modified_details" : {
        "local" : 1641044491,
        "gelbooru.com" : 1604055647
      },
      "file_services" : {
        "current" : {
          "616c6c206c6f63616c2066696c6573" : {
            "name" : "all local files",
            "type" : 15,
            "type_pretty" : "virtual combined local file service",
            "time_imported" : 1641044491
          },
          "616c6c206c6f63616c2066696c6573" : {
            "name" : "all my files",
            "type" : 21,
            "type_pretty" : "virtual combined local media service",
            "time_imported" : 1641044491
          },
          "cb072cffbd0340b67aec39e1953c074e7430c2ac831f8e78fb5dfbda6ec8dcbd" : {
            "name" : "cool space babes",
            "type" : 2,
            "type_pretty" : "local file domain",
            "time_imported" : 1641204220
          }
        },
        "deleted" : {
          "6c6f63616c2066696c6573" : {
            "name" : "my files",
            "type" : 2,
            "type_pretty" : "local file domain",
            "time_deleted" : 1641204274,
            "time_imported" : 1641044491
          }
        }
      },
      "ipfs_multihashes" : {
        "55af93e0deabd08ce15ffb2b164b06d1254daab5a18d145e56fa98f71ddb6f11" : "QmReHtaET3dsgh7ho5NVyHb5U13UgJoGipSWbZsnuuM8tb"
      },
      "has_audio" : true,
      "num_frames" : 102,
      "num_words" : null,
      "is_inbox" : false,
      "is_local" : true,
      "is_trashed" : false,
      "is_deleted" : false,
      "has_exif" : false,
      "has_human_readable_embedded_metadata" : false,
      "has_icc_profile" : false,
      "known_urls" : [
        "https://gelbooru.com/index.php?page=post&s=view&id=4841557",
        "https://img2.gelbooru.com//images/80/c8/80c8646b4a49395fb36c805f316c49a9.jpg",
        "http://origin-orig.deviantart.net/ed31/f/2019/210/7/8/beachqueen_samus_by_dandonfuga-ddcu1xg.jpg"
      ],
      "tags" : {
        "6c6f63616c2074616773" : {
          "name" : "local tags",
          "type" : 5,
          "type_pretty" : "local tag service",
          "storage_tags" : {
            "0" : ["samus favourites"],
            "2" : ["process this later"]
          },
          "display_tags" : {
            "0" : ["samus favourites", "favourites"],
            "2" : ["process this later"]
          }
        },
        "37e3849bda234f53b0e9792a036d14d4f3a9a136d1cb939705dbcd5287941db4" : {
          "name" : "public tag repo",
          "type" : 1,
          "type_pretty" : "hydrus tag repository",
          "storage_tags" : {
            "0" : ["blonde_hair", "blue_eyes", "looking_at_viewer"],
            "1" : ["bodysuit"]
          },
          "display_tags" : {
            "0" : ["blonde hair", "blue_eyes", "looking at viewer"],
            "1" : ["bodysuit", "clothing"]
          }
        },
        "616c6c206b6e6f776e2074616773" : {
          "name" : "all known tags",
          "type" : 10,
          "type_pretty" : "virtual combined tag service",
          "storage_tags" : {
            "0" : ["samus favourites", "blonde_hair", "blue_eyes", "looking_at_viewer"],
            "1" : ["bodysuit"]
          },
          "display_tags" : {
            "0" : ["samus favourites", "favourites", "blonde hair", "blue_eyes", "looking at viewer"],
            "1" : ["bodysuit", "clothing"]
          }
        }
      }
    }
  ]
}
```
```json title="And one where only_return_identifiers is true"
{
  "metadata" : [
    {
      "file_id" : 123,
      "hash" : "4c77267f93415de0bc33b7725b8c331a809a924084bee03ab2f5fae1c6019eb2"
    },
    {
      "file_id" : 4567,
      "hash" : "3e7cb9044fe81bda0d7a84b5cb781cba4e255e4871cba6ae8ecd8207850d5b82"
    }
  ]
}
```
```json title="And where only_return_basic_information is true"
{
  "metadata" : [
    {
      "file_id" : 123,
      "hash" : "4c77267f93415de0bc33b7725b8c331a809a924084bee03ab2f5fae1c6019eb2",
      "size" : 63405,
      "mime" : "image/jpeg",
      "ext" : ".jpg",
      "width" : 640,
      "height" : 480,
      "duration" : null,
      "has_audio" : false,
      "num_frames" : null,
      "num_words" : null,
    },
    {
      "file_id" : 4567,
      "hash" : "3e7cb9044fe81bda0d7a84b5cb781cba4e255e4871cba6ae8ecd8207850d5b82",
      "size" : 199713,
      "mime" : "video/webm",
      "ext" : ".webm",
      "width" : 1920,
      "height" : 1080,
      "duration" : 4040,
      "has_audio" : true,
      "num_frames" : 102,
      "num_words" : null,
    }
  ]
}
```

#### basics

Size is in bytes. Duration is in milliseconds, and may be an int or a float.

`is_trashed` means if the file is currently in the trash but available on the hard disk. `is_deleted` means currently either in the trash or completely deleted from disk.

`file_services` stores which file services the file is <i>current</i>ly in and _deleted_ from. The entries are by the service key, same as for tags later on. In rare cases, the timestamps may be `null`, if they are unknown (e.g. a `time_deleted` for the file deleted before this information was tracked). The `time_modified` can also be null. Time modified is just the filesystem modified time for now, but it will evolve into more complicated storage in future with multiple locations (website post times) that'll be aggregated to a sensible value in UI.

`ipfs_multihashes` stores the ipfs service key to any known multihash for the file. 

The `thumbnail_width` and `thumbnail_height` are a generally reliable prediction but aren't a promise. The actual thumbnail you get from [/get\_files/thumbnail](#get_files_thumbnail) will be different if the user hasn't looked at it since changing their thumbnail options. You only get these rows for files that hydrus actually generates an actual thumbnail for. Things like pdf won't have it. You can use your own thumb, or ask the api and it'll give you a fixed fallback; those are mostly 200x200, but you can and should size them to whatever you want.

#### tags

The 'tags' structures are undergoing transition. Previously, this was a mess of different Objects in different domains, all `service_xxx_to_xxx_tags`, but they are being transitioned to the combined `tags` Object.

`hide_service_keys_tags` is deprecated and will be deleted soon. When set to `false`, it shows the old `service_keys_to_statuses_to_tags` and `service_keys_to_statuses_to_display_tags` Objects.

The `tags` structures are similar to the [/add\_tags/add\_tags](#add_tags_add_tags) scheme, excepting that the status numbers are:

*   0 - current
*   1 - pending
*   2 - deleted
*   3 - petitioned

!!! note
    Since JSON Object keys must be strings, these status numbers are strings, not ints.

To learn more about service names and keys on a client, use the [/get\_services](#get_services) call.

While the 'storage_tags' represent the actual tags stored on the database for a file, 'display_tags' reflect how tags appear in the UI, after siblings are collapsed and parents are added. If you want to edit a file's tags, refer to the storage tags. If you want to render to the user, use the display tags. The display tag calculation logic is very complicated; if the storage tags change, do not try to guess the new display tags yourself--just ask the API again. 

#### parameters

If you ask with hashes rather than file_ids, hydrus will, by default, only return results when it has seen those hashes before. This is to stop the client making thousands of new file_id records in its database if you perform a scanning operation. If you ask about a hash the client has never encountered before--for which there is no file_id--you will get this style of result:

```json title="Missing file_id example"
{
    "metadata" : [
        {
            "file_id" : null,
            "hash" : "766da61f81323629f982bc1b71b5c1f9bba3f3ed61caf99906f7f26881c3ae93"
        }
    ]
}
```

You can change this behaviour with `create_new_file_ids=true`, but bear in mind you will get a fairly 'empty' metadata result with lots of 'null' lines, so this is only useful for gathering the numerical ids for later Client API work.

If you ask about any file_ids that do not exist, you'll get 404.

If you set `only_return_basic_information=true`, this will be much faster for first-time requests than the full metadata result, but it will be slower for repeat requests. The full metadata object is cached after first fetch, the limited file info object is not.

If you add `detailed_url_information=true`, a new entry, `detailed_known_urls`, will be added for each file, with a list of the same structure as /`add_urls/get_url_info`. This may be an expensive request if you are querying thousands of files at once.

```json title="For example"
{
  "detailed_known_urls": [
    {
      "normalised_url": "https://gelbooru.com/index.php?id=4841557&page=post&s=view",
      "url_type": 0,
      "url_type_string": "post url",
      "match_name": "gelbooru file page",
      "can_parse": true
    },
    {
      "normalised_url": "https://img2.gelbooru.com//images/80/c8/80c8646b4a49395fb36c805f316c49a9.jpg",
      "url_type": 5,
      "url_type_string": "unknown url",
      "match_name": "unknown url",
      "can_parse": false
    }
  ]
}
```


### **GET `/get_files/file`** { id="get_files_file" }

_Get a file._

Restricted access: 
:   YES. Search for Files permission needed. Additional search permission limits may apply.
    
Required Headers: n/a
    
Arguments :
:   
    *   `file_id`: (numerical file id for the file)
    *   `hash`: (a hexadecimal SHA256 hash for the file)

    Only use one. As with metadata fetching, you may only use the hash argument if you have access to all files. If you are tag-restricted, you will have to use a file_id in the last search you ran.

    ``` title="Example request"
    /get_files/file?file_id=452158
    ```
    ``` title="Example request"
    /get_files/file?hash=7f30c113810985b69014957c93bc25e8eb4cf3355dae36d8b9d011d8b0cf623a
    ```
   
Response:
:   The file itself. You should get the correct mime type as the Content-Type header.


### **GET `/get_files/thumbnail`** { id="get_files_thumbnail" }

_Get a file's thumbnail._

Restricted access: 
:   YES. Search for Files permission needed. Additional search permission limits may apply.
    
Required Headers: n/a
    
Arguments:
:   
    *   `file_id`: (numerical file id for the file)
    *   `hash`: (a hexadecimal SHA256 hash for the file)

    Only use one. As with metadata fetching, you may only use the hash argument if you have access to all files. If you are tag-restricted, you will have to use a file_id in the last search you ran.

``` title="Example request"
/get_files/thumbnail?file_id=452158
```
``` title="Example request"
/get_files/thumbnail?hash=7f30c113810985b69014957c93bc25e8eb4cf3355dae36d8b9d011d8b0cf623a
```

Response:
:   The thumbnail for the file. Some hydrus thumbs are jpegs, some are pngs. It should give you the correct image/jpeg or image/png Content-Type.

    If hydrus keeps no thumbnail for the filetype, for instance with pdfs, then you will get the same default 'pdf' icon you see in the client. If the file does not exist in the client, or the thumbnail was expected but is missing from storage, you will get the fallback 'hydrus' icon, again just as you would in the client itself. This request should never give a 404.

!!! note
    If you get a 'default' filetype thumbnail like the pdf or hydrus one, you will be pulling the defaults straight from the hydrus/static folder. They will most likely be 200x200 pixels. 

    

## Managing File Relationships

This refers to the File Relationships system, which includes 'potential duplicates', 'duplicates', and 'alternates'.

This system is pending significant rework and expansion, so please do not get too married to some of the routines here. I am mostly just exposing my internal commands, so things are a little ugly/hacked. I expect duplicate and alternate groups to get some form of official identifier in future, which may end up being the way to refer and edit things here.

Also, at least for now, 'Manage File Relationships' permission is not going to be bound by the search permission restrictions that normal file search does. Getting this file relationship management permission allows you to search anything.

_There is more work to do here, including adding various 'dissolve'/'undo' commands to break groups apart._

### **GET `/manage_file_relationships/get_file_relationships`** { id="manage_file_relationships_get_file_relationships" }

_Get the current relationships for one or more files._

Restricted access: 
:   YES. Manage File Relationships permission needed.
    
Required Headers: n/a
    
Arguments (in percent-encoded JSON):
:   
    *   [files](#parameters_files)
    *   [file domain](#parameters_file_domain) (optional, defaults to 'all my files')

``` title="Example request"
/manage_file_relationships/get_file_relationships?hash=ac940bb9026c430ea9530b4f4f6980a12d9432c2af8d9d39dfc67b05d91df11d
```

Response:
:   A JSON Object mapping the hashes to their relationships.
``` json title="Example response"
{
	"file_relationships" : {
        "ac940bb9026c430ea9530b4f4f6980a12d9432c2af8d9d39dfc67b05d91df11d" : {
            "is_king" : false,
            "king" : "8784afbfd8b59de3dcf2c13dc1be9d7cb0b3d376803c8a7a8b710c7c191bb657",
            "king_is_on_file_domain" : true,
            "king_is_local" : true,
            "0" : [
            ],
            "1" : [],
            "3" : [
                "8bf267c4c021ae4fd7c4b90b0a381044539519f80d148359b0ce61ce1684fefe"
            ],
            "8" : [
                "8784afbfd8b59de3dcf2c13dc1be9d7cb0b3d376803c8a7a8b710c7c191bb657",
                "3fa8ef54811ec8c2d1892f4f08da01e7fc17eed863acae897eb30461b051d5c3"
            ]
        }
    }
}
```

`king` refers to which file is set as the best of a duplicate group. If you are doing potential duplicate comparisons, the kings of your two groups are usually the ideal representatives, and the 'get some pairs to filter'-style commands try to select the kings of the various to-be-compared duplicate groups. `is_king` is a convenience bool for when a file is king of its own group.

**It is possible for the king to not be available.** Every group has a king, but if that file has been deleted, or if the file domain here is limited and the king is on a different file service, then it may not be available. A similar issue occurs when you search for filtering pairs--while it is ideal to compare kings with kings, if you set 'files must be pixel dupes', then the user will expect to see those pixel duplicates, not their champions--you may be forced to compare non-kings. `king_is_on_file_domain` lets you know if the king is on the file domain you set, and `king_is_local` lets you know if it is on the hard disk--if `king_is_local=true`, you can do a `/get_files/file` request on it. It is generally rare, but you have to deal with the king being unavailable--in this situation, your best bet is to just use the file itself as its own representative.

All the relationships you get are filtered by the file domain. If you set the file domain to 'all known files', you will get every relationship a file has, including all deleted files, which is often less useful than you would think. The default, 'all my files' is usually most useful.

A file that has no duplicates is considered to be in a duplicate group of size 1 and thus is always its own king.

The numbers are from a duplicate status enum, as so:

* 0 - potential duplicates
* 1 - false positives
* 3 - alternates
* 8 - duplicates

Note that because of JSON constraints, these are the string versions of the integers since they are Object keys.

All the hashes given here are in 'all my files', i.e. not in the trash. A file may have duplicates that have long been deleted, but, like the null king above, they will not show here.

### **GET `/manage_file_relationships/get_potentials_count`** { id="manage_file_relationships_get_potentials_count" }

_Get the count of remaining potential duplicate pairs in a particular search domain. Exactly the same as the counts you see in the duplicate processing page._

Restricted access: 
:   YES. Manage File Relationships permission needed.
    
Required Headers: n/a
    
Arguments (in percent-encoded JSON):
:   
    *   [file domain](#parameters_file_domain) (optional, defaults to 'all my files')
    *   `tag_service_key_1`: (optional, default 'all known tags', a hex tag service key)
    *   `tags_1`: (optional, default system:everything, a list of tags you wish to search for)
    *   `tag_service_key_2`: (optional, default 'all known tags', a hex tag service key)
    *   `tags_2`: (optional, default system:everything, a list of tags you wish to search for)
    *   `potentials_search_type`: (optional, integer, default 0, regarding how the pairs should match the search(es))
    *   `pixel_duplicates`: (optional, integer, default 1, regarding whether the pairs should be pixel duplicates)
    *   `max_hamming_distance`: (optional, integer, default 4, the max 'search distance' of the pairs)

``` title="Example request"
/manage_file_relationships/get_potentials_count?tag_service_key_1=c1ba23c60cda1051349647a151321d43ef5894aacdfb4b4e333d6c4259d56c5f&tags_1=%5B%22dupes_to_process%22%2C%20%22system%3Awidth%3C400%22%5D&potentials_search_type=1&pixel_duplicates=2&max_hamming_distance=0&max_num_pairs=50
```

`tag_service_key_x` and `tags_x` work the same as [/get\_files/search\_files](#get_files_search_files). The `_2` variants are only useful if the `potentials_search_type` is 2.

`potentials_search_type` and `pixel_duplicates` are enums:

* 0 - one file matches search 1
* 1 - both files match search 1
* 2 - one file matches search 1, the other 2

-and-

* 0 - must be pixel duplicates
* 1 - can be pixel duplicates
* 2 - must not be pixel duplicates

The `max_hamming_distance` is the same 'search distance' you see in the Client UI. A higher number means more speculative 'similar files' search. If `pixel_duplicates` is set to 'must be', then `max_hamming_distance` is obviously ignored.

Response:
:   A JSON Object stating the count.
``` json title="Example response"
{
	"potential_duplicates_count" : 17
}
```

If you confirm that a pair of potentials are duplicates, this may transitively collapse other potential pairs and decrease the count by more than 1.

### **GET `/manage_file_relationships/get_potential_pairs`** { id="manage_file_relationships_get_potential_pairs" }

_Get some potential duplicate pairs for a filtering workflow. Exactly the same as the 'duplicate filter' in the duplicate processing page._

Restricted access: 
:   YES. Manage File Relationships permission needed.
    
Required Headers: n/a
    
Arguments (in percent-encoded JSON):
:   
    *   [file domain](#parameters_file_domain) (optional, defaults to 'all my files')
    *   `tag_service_key_1`: (optional, default 'all known tags', a hex tag service key)
    *   `tags_1`: (optional, default system:everything, a list of tags you wish to search for)
    *   `tag_service_key_2`: (optional, default 'all known tags', a hex tag service key)
    *   `tags_2`: (optional, default system:everything, a list of tags you wish to search for)
    *   `potentials_search_type`: (optional, integer, default 0, regarding how the pairs should match the search(es))
    *   `pixel_duplicates`: (optional, integer, default 1, regarding whether the pairs should be pixel duplicates)
    *   `max_hamming_distance`: (optional, integer, default 4, the max 'search distance' of the pairs)
    *   `max_num_pairs`: (optional, integer, defaults to client's option, how many pairs to get in a batch)

``` title="Example request"
/manage_file_relationships/get_potential_pairs?tag_service_key_1=c1ba23c60cda1051349647a151321d43ef5894aacdfb4b4e333d6c4259d56c5f&tags_1=%5B%22dupes_to_process%22%2C%20%22system%3Awidth%3C400%22%5D&potentials_search_type=1&pixel_duplicates=2&max_hamming_distance=0&max_num_pairs=50
```

The search arguments work the same as [/manage\_file\_relationships/get\_potentials\_count](#manage_file_relationships_get_potentials_count).

`max_num_pairs` is simple and just caps how many pairs you get.

Response:
:   A JSON Object listing a batch of hash pairs.
```json title="Example response"
{
	"potential_duplicate_pairs" : [
        [ "16470d6e73298cd75d9c7e8e2004810e047664679a660a9a3ba870b0fa3433d3", "7ed062dc76265d25abeee5425a859cfdf7ab26fd291f50b8de7ca381e04db079" ],
        [ "eeea390357f259b460219d9589b4fa11e326403208097b1a1fbe63653397b210", "9215dfd39667c273ddfae2b73d90106b11abd5fd3cbadcc2afefa526bb226608" ],
        [ "a1ea7d671245a3ae35932c603d4f3f85b0d0d40c5b70ffd78519e71945031788", "8e9592b2dfb436fe0a8e5fa15de26a34a6dfe4bca9d4363826fac367a9709b25" ]
	]
}
```

The selected pair sample and their order is strictly hardcoded for now (e.g. to guarantee that a decision will not invalidate any other pair in the batch, you shouldn't see the same file twice in a batch, nor two files in the same duplicate group). Treat it as the client filter does, where you fetch batches to process one after another. I expect to make it more flexible in future, in the client itself and here.

You will see significantly fewer than `max_num_pairs` (and potential duplicate count) as you close to the last available pairs, and when there are none left, you will get an empty list.

### **GET `/manage_file_relationships/get_random_potentials`** { id="manage_file_relationships_get_random_potentials" }

_Get some random potentially duplicate file hashes. Exactly the same as the 'show some random potential dupes' button in the duplicate processing page._

Restricted access: 
:   YES. Manage File Relationships permission needed.
    
Required Headers: n/a
    
Arguments (in percent-encoded JSON):
:   
    *   [file domain](#parameters_file_domain) (optional, defaults to 'all my files')
    *   `tag_service_key_1`: (optional, default 'all known tags', a hex tag service key)
    *   `tags_1`: (optional, default system:everything, a list of tags you wish to search for)
    *   `tag_service_key_2`: (optional, default 'all known tags', a hex tag service key)
    *   `tags_2`: (optional, default system:everything, a list of tags you wish to search for)
    *   `potentials_search_type`: (optional, integer, default 0, regarding how the files should match the search(es))
    *   `pixel_duplicates`: (optional, integer, default 1, regarding whether the files should be pixel duplicates)
    *   `max_hamming_distance`: (optional, integer, default 4, the max 'search distance' of the files)

``` title="Example request"
/manage_file_relationships/get_random_potentials?tag_service_key_1=c1ba23c60cda1051349647a151321d43ef5894aacdfb4b4e333d6c4259d56c5f&tags_1=%5B%22dupes_to_process%22%2C%20%22system%3Awidth%3C400%22%5D&potentials_search_type=1&pixel_duplicates=2&max_hamming_distance=0
```

The arguments work the same as [/manage\_file\_relationships/get\_potentials\_count](#manage_file_relationships_get_potentials_count), with the caveat that `potentials_search_type` has special logic:

* 0 - first file matches search 1
* 1 - all files match search 1
* 2 - first file matches search 1, the others 2

Essentially, the first hash is the 'master' to which the others are paired. The other files will include every matching file.

Response:
:   A JSON Object listing a group of hashes exactly as the client would.
```json title="Example response"
{
	"random_potential_duplicate_hashes" : [
		"16470d6e73298cd75d9c7e8e2004810e047664679a660a9a3ba870b0fa3433d3",
        "7ed062dc76265d25abeee5425a859cfdf7ab26fd291f50b8de7ca381e04db079",
        "9e0d6b928b726562d70e1f14a7b506ba987c6f9b7f2d2e723809bb11494c73e6",
        "9e01744819b5ff2a84dda321e3f1a326f40d0e7f037408ded9f18a11ee2b2da8"
	]
}
```

If there are no potential duplicate groups in the search, this returns an empty list.

### **POST `/manage_file_relationships/set_file_relationships`** { id="manage_file_relationships_set_file_relationships" }

Set the relationships to the specified file pairs.

Restricted access: 
:   YES. Manage File Relationships permission needed.
    
Required Headers:
:   
    *   `Content-Type`: application/json

Arguments (in JSON):
:   
    *   `relationships`: (a list of Objects, one for each file-pair being set)

Each Object is:

    *   `hash_a`: (a hexadecimal SHA256 hash)
    *   `hash_b`: (a hexadecimal SHA256 hash)
    *   `relationship`: (integer enum for the relationship being set)
    *   `do_default_content_merge`: (bool)
    *   `delete_a`: (optional, bool, default false)
    *   `delete_b`: (optional, bool, default false)

`hash_a` and `hash_b` are normal hex SHA256 hashes for your file pair.

`relationship` is one of this enum:

* 0 - set as potential duplicates
* 1 - set as false positives
* 2 - set as same quality
* 3 - set as alternates
* 4 - set A as better
* 7 - set B as better

2, 4, and 7 all make the files 'duplicates' (8 under `/get_file_relationships`), which, specifically, merges the two files' duplicate groups. 'same quality' has different duplicate content merge options to the better/worse choices, but it ultimately sets something similar to A>B (but see below for more complicated outcomes). You obviously don't have to use 'B is better' if you prefer just to swap the hashes. Do what works for you.

`do_default_content_merge` sets whether the user's duplicate content merge options should be loaded and applied to the files along with the relationship. Most operations in the client do this automatically, so the user may expect it to apply, but if you want to do content merge yourself, set this to false.

`delete_a` and `delete_b` are booleans that select whether to delete A and/or B in the same operation as setting the relationship. You can also do this externally if you prefer.

```json title="Example request body"
{
  "relationships" : [
    {
      "hash_a" : "b54d09218e0d6efc964b78b070620a1fa19c7e069672b4c6313cee2c9b0623f2",
      "hash_b" : "bbaa9876dab238dcf5799bfd8319ed0bab805e844f45cf0de33f40697b11a845",
      "relationship" : 4,
      "do_default_content_merge" : true,
      "delete_b" : true
    },
    {
      "hash_a" : "22667427eaa221e2bd7ef405e1d2983846c863d40b2999ce8d1bf5f0c18f5fb2",
      "hash_b" : "65d228adfa722f3cd0363853a191898abe8bf92d9a514c6c7f3c89cfed0bf423",
      "relationship" : 4,
      "do_default_content_merge" : true,
      "delete_b" : true
    },
    {
      "hash_a" : "0480513ffec391b77ad8c4e57fe80e5b710adfa3cb6af19b02a0bd7920f2d3ec",
      "hash_b" : "5fab162576617b5c3fc8caabea53ce3ab1a3c8e0a16c16ae7b4e4a21eab168a7",
      "relationship" : 2,
      "do_default_content_merge" : true
    }
  ]
}
```

Response:
:   200 with no content.

If you try to add an invalid or redundant relationship, for instance setting files that are already duplicates as potential duplicates, no changes are made.

This is the file relationships request that is probably most likely to change in future. I may implement content merge options. I may move from file pairs to group identifiers. When I expand alternates, those file groups are going to support more variables.

#### king merge rules

Recall in `/get_file_relationships` that we discussed how duplicate groups have a 'king' for their best file. This file is the most useful representative when you do comparisons, since if you say "King A > King B", then we know that King A is also better than all of King B's normal duplicate group members. We can merge the group simply just by folding King B and all the other members into King A's group.

So what happens if you say 'A = B'? We have to have a king, so which should it be?

What happens if you say "non-king member of A > non-king member of B"? We don't want to merge all of B into A, since King B might be higher quality than King A.

The logic here can get tricky, but I have tried my best to avoid overcommitting and accidentally promoting the wrong king. Here are all the possible situations ('>' means 'better than', and '=' means 'same quality as'):

??? abstract "Merges" 
    * King A > King B  
        * Merge B into A
        * King A is king of the new combined group
    * Non-King A > King B
        * Merge B into A
        * King of A is king of the new combined group
    * King A > Non-King B
        * Remove Non-King B from B and merge it into A
        * King A stays king of A
        * King of B stays king of B
    * Non-King A > Non-King B
        * Remove Non-King B from B and merge it into A
        * King of A stays king of A
        * King of B stays king of B
    * King A = King B
        * Merge B into A
        * King A is king of the new combined group
    * Non-King A = King B
        * Merge B into A
        * King of A is king of the new combined group
    * King A = Non-King B
        * Merge A into B
        * King of B is king of the new combined group
    * Non-King A = Non-King B
        * Remove Non-King B from B and merge it into A
        * King of A stays king of A
        * King of B stays king of B

So, if you can, always present kings to your users, and action using those kings' hashes. It makes the merge logic easier in all cases. Remember that you can set `system:is the best quality file of its duplicate group` in any file search to exclude any non-kings (e.g. if you are hunting for easily actionable pixel potential duplicates).

### **POST `/manage_file_relationships/set_kings`** { id="manage_file_relationships_set_kings" }

Set the specified files to be the kings of their duplicate groups.

Restricted access: 
:   YES. Manage File Relationships permission needed.
    
Required Headers:
:   
    *   `Content-Type`: application/json

Arguments (in JSON):
:   
    *   [files](#parameters_files)

```json title="Example request body"
{
  "file_id" : 123
}
```

Response:
:   200 with no content.

The files will be promoted to be the kings of their respective duplicate groups. If the file is already the king (also true for any file with no duplicates), this is idempotent. It also processes the files in the given order, so if you specify two files in the same group, the latter will be the king at the end of the request.

## Managing Cookies

This refers to the cookies held in the client's session manager, which you can review under _network->data->manage session cookies_. These are sent to every request on the respective domains.

### **GET `/manage_cookies/get_cookies`** { id="manage_cookies_get_cookies" }

_Get the cookies for a particular domain._

Restricted access: 
:   YES. Manage Cookies and Headers permission needed.
    
Required Headers: n/a
    
Arguments:
:   *  `domain`

``` title="Example request (for gelbooru.com)"
/manage_cookies/get_cookies?domain=gelbooru.com
```

Response:
:   A JSON Object listing all the cookies for that domain in \[ name, value, domain, path, expires \] format.

```json title="Example response"
{
	"cookies" : [
		["__cfduid", "f1bef65041e54e93110a883360bc7e71", ".gelbooru.com", "/", 1596223327],
		["pass_hash", "0b0833b797f108e340b315bc5463c324", "gelbooru.com", "/", 1585855361],
		["user_id", "123456", "gelbooru.com", "/", 1585855361]
	]
}
```

    Note that these variables are all strings except 'expires', which is either an integer timestamp or _null_ for session cookies.

    This request will also return any cookies for subdomains. The session system in hydrus generally stores cookies according to the second-level domain, so if you request for specific.someoverbooru.net, you will still get the cookies for someoverbooru.net and all its subdomains.

### **POST `/manage_cookies/set_cookies`** { id="manage_cookies_set_cookies" }

Set some new cookies for the client. This makes it easier to 'copy' a login from a web browser or similar to hydrus if hydrus's login system can't handle the site yet.

Restricted access: 
:   YES. Manage Cookies and Headers permission needed.
    
Required Headers:
:   
    *   `Content-Type`: application/json

Arguments (in JSON):
:   
    *   `cookies`: (a list of cookie rows in the same format as the GET request above)

```json title="Example request body"
{
  "cookies" : [
    ["PHPSESSID", "07669eb2a1a6e840e498bb6e0799f3fb", ".somesite.com", "/", 1627327719],
    ["tag_filter", "1", ".somesite.com", "/", 1627327719]
  ]
}
```

You can set 'value' to be null, which will clear any existing cookie with the corresponding name, domain, and path (acting essentially as a delete).

Expires can be null, but session cookies will time-out in hydrus after 60 minutes of non-use.

## Managing HTTP Headers

This refers to the custom headers you can see under _network->data->manage http headers_.

### **GET `/manage_headers/get_headers`** { id="manage_headers_get_headers" }

Get the custom http headers.

Restricted access: 
:   YES. Manage Cookies and Headers permission needed.
    
Required Headers: n/a
    
Arguments:
:   *  `domain`: optional, the domain to fetch headers for

``` title="Example request (for gelbooru.com)"
/manage_headers/get_headers?domain=gelbooru.com
```

``` title="Example request (for global)"
/manage_headers/get_headers
```

Response:
:   A JSON Object listing all the headers:

```json title="Example response"
{
  "network_context" : {
    "type" : 2,
    "data" : "gelbooru.com"
  },
  "headers" : {
    "User-Agent" : {
      "value" : "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:56.0) Gecko/20100101 Firefox/56.0",
      "approved" : "approved",
      "reason" : "Set by Client API"
    },
    "DNT" : {
      "value" : "1",
      "approved" : "approved",
      "reason" : "Set by Client API"
    }
  }
}
```

### **POST `/manage_headers/set_headers`** { id="manage_headers_set_headers" }

Manages the custom http headers.

Restricted access: 
:   YES. Manage Cookies and Headers permission needed.
    
Required Headers:
:    
    *   `Content-Type`: application/json

Arguments (in JSON):
:       
    *   `domain`: (optional, the specific domain to set the header for)
    *   `headers`: (a JSON Object that holds "key" objects)

```json title="Example request body"
{
  "domain" : "mysite.com",
  "headers" : {
    "User-Agent" : {
      "value" : "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:56.0) Gecko/20100101 Firefox/56.0"
    },
    "DNT" : {
      "value" : "1"
    },
    "CoolStuffToken" : {
      "value" : "abcdef0123456789",
      "approved" : "pending",
      "reason" : "This unlocks the Sonic fanfiction!"
    }
  }
}
```

```json title="Example request body that deletes"
{
  "domain" : "myothersite.com",
  "headers" : {
    "User-Agent" : {
      "value" : null
    },
    "Authorization" : {
      "value" : null
    }
  }
}
```

If you do not set a domain, or you set it to `null`, the 'context' will be the global context, which applies as a fallback to all jobs.

Domain headers also apply to their subdomains--unless they are overwritten by specific subdomain entries.

Each `key` Object under `headers` has the same form as [/manage\_headers/get\_headers](#manage_headers_get_headers). `value` is obvious--it is the value of the header. If the pair doesn't exist yet, you need the `value`, but if you just want to approve something, it is optional. Set it to `null` to delete an existing pair.

You probably won't ever use `approved` or `reason`, but they plug into the 'validation' system in the client. They are both optional. Approved can be any of `[ approved, denied, pending ]`, and by default everything you add will be `approved`. If there is anything `pending` when a network job asks, the user will be presented with a yes/no popup presenting the reason for the header. If they click 'no', the header is set to `denied` and the network job goes ahead without it. If you have a header that changes behaviour or unlocks special content, you might like to make it optional in this way.

If you need to reinstate it, the default `global` `User-Agent` is `Mozilla/5.0 (compatible; Hydrus Client)`.

### **POST `/manage_headers/set_user_agent`** { id="manage_headers_set_user_agent" }

_This is deprecated--move to [/manage\_headers/set\_headers](#manage_headers_set_headers)!_

This sets the 'Global' User-Agent for the client, as typically editable under _network->data->manage http headers_, for instance if you want hydrus to appear as a specific browser associated with some cookies.

Restricted access: 
:   YES. Manage Cookies and Headers permission needed.
    
Required Headers:
:    
    *   `Content-Type`: application/json

Arguments (in JSON):
:       
    *   `user-agent`: (a string)

```json title="Example request body"
{
  "user-agent" : "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:56.0) Gecko/20100101 Firefox/56.0"
}
```

Send an empty string to reset the client back to the default User-Agent, which should be `Mozilla/5.0 (compatible; Hydrus Client)`.

## Managing Pages

This refers to the pages of the main client UI.

### **GET `/manage_pages/get_pages`** { id="manage_pages_get_pages" }

_Get the page structure of the current UI session._

Restricted access: 
:   YES. Manage Pages permission needed.
    
Required Headers: n/a
    
Arguments: n/a
    

Response: 
:   A JSON Object of the top-level page 'notebook' (page of pages) detailing its basic information and current sub-pages. Page of pages beneath it will list their own sub-page lists.
```json title="Example response"
{
  "pages" : {
    "name" : "top pages notebook",
    "page_key" : "3b28d8a59ec61834325eb6275d9df012860a1ecfd9e1246423059bc47fb6d5bd",
    "page_state" : 0,
    "page_type" : 10,
    "selected" : true,
    "pages" : [
      {
        "name" : "files",
        "page_key" : "d436ff5109215199913705eb9a7669d8a6b67c52e41c3b42904db083255ca84d",
        "page_state" : 0,
        "page_type" : 6,
        "selected" : false
      },
      {
        "name" : "thread watcher",
        "page_key" : "40887fa327edca01e1d69b533dddba4681b2c43e0b4ebee0576177852e8c32e7",
        "page_state" : 0,
        "page_type" : 9,
        "selected" : false
      },
      {
        "name" : "pages",
        "page_key" : "2ee7fa4058e1e23f2bd9e915cdf9347ae90902a8622d6559ba019a83a785c4dc",
        "page_state" : 0,
        "page_type" : 10,
        "selected" : true,
        "pages" : [
          {
            "name" : "urls",
            "page_key" : "9fe22cb760d9ee6de32575ed9f27b76b4c215179cf843d3f9044efeeca98411f",
            "page_state" : 0,
            "page_type" : 7,
            "selected" : true
          },
          {
            "name" : "files",
            "page_key" : "2977d57fc9c588be783727bcd54225d577b44e8aa2f91e365a3eb3c3f580dc4e",
            "page_state" : 0,
            "page_type" : 6,
            "selected" : false
          }
        ]
      }
    ]
  }
}
```

    `name` is the full text on the page tab. 
    
    `page_key` is a unique identifier for the page. It will stay the same for a particular page throughout the session, but new ones are generated on a session reload.
    
    `page_type` is as follows:

    *   1 - Gallery downloader
    *   2 - Simple downloader
    *   3 - Hard drive import
    *   5 - Petitions (used by repository janitors)
    *   6 - File search
    *   7 - URL downloader
    *   8 - Duplicates
    *   9 - Thread watcher
    *   10 - Page of pages
    
    `page_state` is as follows:
    
    * 0 - ready
    * 1 - initialising
    * 2 - searching/loading
    * 3 - search cancelled
    
    Most pages will be 0, normal/ready, at all times. Large pages will start in an 'initialising' state for a few seconds, which means their session-saved thumbnails aren't loaded yet. Search pages will enter 'searching' after a refresh or search change and will either return to 'ready' when the search is complete, or fall to 'search cancelled' if the search was interrupted (usually this means the user clicked the 'stop' button that appears after some time). 
    
    `selected` means which page is currently in view. It will propagate down the page of pages until it terminates. It may terminate in an empty page of pages, so do not assume it will end on a media page.    
    
    The top page of pages will always be there, and always selected.
    

### **GET `/manage_pages/get_page_info`** { id="manage_pages_get_page_info" }

_Get information about a specific page._

!!! warning "Under Construction"
    This is under construction. The current call dumps a ton of info for different downloader pages. Please experiment in IRL situations and give feedback for now! I will flesh out this help with more enumeration info and examples as this gets nailed down. POST commands to alter pages (adding, removing, highlighting), will come later.

Restricted access: 
:   YES. Manage Pages permission needed.
    
Required Headers: n/a
    
Arguments:
:   
    *   `page_key`: (hexadecimal page\_key as stated in [/manage\_pages/get\_pages](#manage_pages_get_pages))
    *   `simple`: true or false (optional, defaulting to true)

    ``` title="Example request"
    /manage_pages/get_page_info?page_key=aebbf4b594e6986bddf1eeb0b5846a1e6bc4e07088e517aff166f1aeb1c3c9da&simple=true
    ```

Response description
:   A JSON Object of the page's information. At present, this mostly means downloader information.
```json title="Example response with simple = true"
{
  "page_info" : {
    "name" : "threads",
    "page_key" : "aebbf4b594e6986bddf1eeb0b5846a1e6bc4e07088e517aff166f1aeb1c3c9da",
    "page_state" : 0,
    "page_type" : 3,
    "management" : {
      "multiple_watcher_import" : {
        "watcher_imports" : [
          {
            "url" : "https://someimageboard.net/m/123456",
            "watcher_key" : "cf8c3525c57a46b0e5c2625812964364a2e801f8c49841c216b8f8d7a4d06d85",
            "created" : 1566164269,
            "last_check_time" : 1566164272,
            "next_check_time" : 1566174272,
            "files_paused" : false,
            "checking_paused" : false,
            "checking_status" : 0,
            "subject" : "gundam pictures",
            "imports" : {
              "status" : "4 successful (2 already in db)",
              "simple_status" : "4",
              "total_processed" : 4,
              "total_to_process" : 4
            },
            "gallery_log" : {
              "status" : "1 successful",
              "simple_status" : "1",
              "total_processed" : 1,
              "total_to_process" : 1
            }
          },
          {
            "url" : "https://someimageboard.net/a/1234",
            "watcher_key" : "6bc17555b76da5bde2dcceedc382cf7d23281aee6477c41b643cd144ec168510",
            "created" : 1566063125,
            "last_check_time" : 1566063133,
            "next_check_time" : 1566104272,
            "files_paused" : false,
            "checking_paused" : true,
            "checking_status" : 1,
            "subject" : "anime pictures",
            "imports" : {
              "status" : "124 successful (22 already in db), 2 previously deleted",
              "simple_status" : "124",
              "total_processed" : 124,
              "total_to_process" : 124
            },
            "gallery_log" : {
              "status" : "3 successful",
              "simple_status" : "3",
              "total_processed" : 3,
              "total_to_process" : 3
            }
          }
        ]
      },
      "highlight" : "cf8c3525c57a46b0e5c2625812964364a2e801f8c49841c216b8f8d7a4d06d85"
    }
  },
  "media" : {
    "num_files" : 4
  }
}
```

    `name`, `page_key`, `page_state`, and `page_type` are as in [/manage\_pages/get\_pages](#manage_pages_get_pages).
    
    As you can see, even the 'simple' mode can get very large. Imagine that response for a page watching 100 threads! Turning simple mode off will display every import item, gallery log entry, and all hashes in the media (thumbnail) panel.
    
    For this first version, the five importer pages--hdd import, simple downloader, url downloader, gallery page, and watcher page--all give rich info based on their specific variables. The first three only have one importer/gallery log combo, but the latter two of course can have multiple. The "imports" and "gallery_log" entries are all in the same data format.
    

### **POST `/manage_pages/add_files`** { id="manage_pages_add_files" }

_Add files to a page._

Restricted access: 
:   YES. Manage Pages permission needed.
    
Required Headers:
:   
    *   `Content-Type`: application/json

Arguments (in JSON):
:   
    *   `page_key`: (the page key for the page you wish to add files to)
    *   [files](#parameters_files)

The files you set will be appended to the given page, just like a thumbnail drag and drop operation. The page key is the same as fetched in the [/manage\_pages/get\_pages](#manage_pages_get_pages) call.

```json title="Example request body"
{
  "page_key" : "af98318b6eece15fef3cf0378385ce759bfe056916f6e12157cd928eb56c1f18",
  "file_ids" : [123, 124, 125]
}
```

Response:
:   200 with no content. If the page key is not found, this will 404.

### **POST `/manage_pages/focus_page`** { id="manage_pages_focus_page" }

_'Show' a page in the main GUI, making it the current page in view. If it is already the current page, no change is made._

Restricted access: 
:   YES. Manage Pages permission needed.
    
Required Headers:
:   
    *   `Content-Type`: application/json

Arguments (in JSON):
:   
    *   `page_key`: (the page key for the page you wish to show)

The page key is the same as fetched in the [/manage\_pages/get\_pages](#manage_pages_get_pages) call.

```json title="Example request body"
{
  "page_key" : "af98318b6eece15fef3cf0378385ce759bfe056916f6e12157cd928eb56c1f18"
}
```

Response:
:   200 with no content. If the page key is not found, this will 404.
    

### **POST `/manage_pages/refresh_page`** { id="manage_pages_refresh_page" }

_Refresh a page in the main GUI. Like hitting F5 in the client, this obviously makes file search pages perform their search again, but for other page types it will force the currently in-view files to be re-sorted._

Restricted access: 
:   YES. Manage Pages permission needed.
    
Required Headers:
:   
    *   `Content-Type`: application/json

Arguments (in JSON):
:   
    *   `page_key`: (the page key for the page you wish to refresh)

The page key is the same as fetched in the [/manage\_pages/get\_pages](#manage_pages_get_pages) call. If a file search page is not set to 'searching immediately', a 'refresh' command does nothing.

```json title="Example request body"
{
  "page_key" : "af98318b6eece15fef3cf0378385ce759bfe056916f6e12157cd928eb56c1f18"
}
```

Response:
:   200 with no content. If the page key is not found, this will 404.

Poll the `page_state` in [/manage\_pages/get\_pages](#manage_pages_get_pages) or [/manage\_pages/get\_page\_info](#manage_pages_get_page_info) to see when the search is complete.

## Managing the Database

### **POST `/manage_database/lock_on`** { id="manage_database_lock_on" }

_Pause the client's database activity and disconnect the current connection._

Restricted access: 
:   YES. Manage Database permission needed.
    
Arguments: None

This is a hacky prototype. It commands the client database to pause its job queue and release its connection (and related file locks and journal files). This puts the client in a similar position as a long VACUUM command--it'll hang in there, but not much will work, and since the UI async code isn't great yet, the UI may lock up after a minute or two. If you would like to automate database backup without shutting the client down, this is the thing to play with.

This should return pretty quick, but it will wait up to five seconds for the database to actually disconnect. If there is a big job (like a VACUUM) current going on, it may take substantially longer to finish that up and process this STOP command. You might like to check for the existence of a journal file in the db dir just to be safe.

As long as this lock is on, all Client API calls except the unlock command will return 503. (This is a decent way to test the current lock status, too)

### **POST `/manage_database/lock_off`** { id="manage_database_lock_off" }

_Reconnect the client's database and resume activity._

Restricted access: 
:   YES. Manage Database permission needed.
    
Arguments: None

This is the obvious complement to the lock. The client will resume processing its job queue and will catch up. If the UI was frozen, it should free up in a few seconds, just like after a big VACUUM.

### **GET `/manage_database/mr_bones`** { id="manage_database_mr_bones" }

_Get the data from help->how boned am I?. This is a simple Object of numbers just for hacky advanced purposes if you want to build up some stats in the background. The numbers are the same as the dialog shows, so double check that to confirm what means what._

Restricted access:
:   YES. Manage Database permission needed.

Arguments: None

```json title="Example response"
{
  "boned_stats" : {
    "num_inbox" : 8356,
    "num_archive" : 229,
    "num_deleted" : 7010,
    "size_inbox" : 7052596762,
    "size_archive" : 262911007,
    "size_deleted" : 13742290193,
    "earliest_import_time" : 1451408539,
    "total_viewtime" : [3280, 41621, 2932, 83021],
    "total_alternate_files" : 265,
    "total_duplicate_files" : 125,
    "total_potential_pairs" : 3252
  }
}
```
