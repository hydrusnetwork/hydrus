from hydrus.core import HydrusSerialisable

IMPORT_OPTIONS_CALLER_TYPE_LOCAL_IMPORT = 0
IMPORT_OPTIONS_CALLER_TYPE_POST_URLS = 1
IMPORT_OPTIONS_CALLER_TYPE_SUBSCRIPTION = 2
IMPORT_OPTIONS_CALLER_TYPE_WATCHER_URLS = 3
IMPORT_OPTIONS_CALLER_TYPE_GLOBAL = 4
IMPORT_OPTIONS_CALLER_TYPE_URL_CLASS = 7
IMPORT_OPTIONS_CALLER_TYPE_SPECIFIC_IMPORTER = 8
IMPORT_OPTIONS_CALLER_TYPE_LOCAL_IMPORT_FOLDER = 9
IMPORT_OPTIONS_CALLER_TYPE_CLIENT_API = 10
IMPORT_OPTIONS_CALLER_TYPE_FAVOURITES = 11

import_options_caller_type_str_lookup = {
    IMPORT_OPTIONS_CALLER_TYPE_LOCAL_IMPORT : 'local hard drive import',
    IMPORT_OPTIONS_CALLER_TYPE_POST_URLS : 'gallery/post urls',
    IMPORT_OPTIONS_CALLER_TYPE_SUBSCRIPTION : 'subscription',
    IMPORT_OPTIONS_CALLER_TYPE_WATCHER_URLS : 'watchable urls',
    IMPORT_OPTIONS_CALLER_TYPE_GLOBAL : 'global',
    IMPORT_OPTIONS_CALLER_TYPE_URL_CLASS : 'url class',
    IMPORT_OPTIONS_CALLER_TYPE_SPECIFIC_IMPORTER : 'specific importer',
    IMPORT_OPTIONS_CALLER_TYPE_LOCAL_IMPORT_FOLDER : 'import folder',
    IMPORT_OPTIONS_CALLER_TYPE_CLIENT_API : 'client api',
    IMPORT_OPTIONS_CALLER_TYPE_FAVOURITES : 'favourites template',
}

import_options_caller_type_desc_lookup = {
    IMPORT_OPTIONS_CALLER_TYPE_LOCAL_IMPORT : 'This covers all imports from a local hard drive, via a local import page or an "import folder". This is the place to filter, route, or present files differently to downloads.',
    IMPORT_OPTIONS_CALLER_TYPE_POST_URLS : 'This covers any gallery search or "post" URL, be that in a gallery downloader, urls downloader, or subscription. A general catch-all for all normal URLs. This is a good place to set up metadata filtering.',
    IMPORT_OPTIONS_CALLER_TYPE_SUBSCRIPTION : 'This covers all subscriptions. A good place to set up quieter presentation options than a normal download page (e.g. to make your subscription popups less spammy).',
    IMPORT_OPTIONS_CALLER_TYPE_WATCHER_URLS : 'This covers all thread watcher work. A good place to set metadata filtering that differs from your gallery/post URL settings.',
    IMPORT_OPTIONS_CALLER_TYPE_GLOBAL : 'This is the base that all importers will default to if nothing else is set. This is the place to manage your general preferences.',
    IMPORT_OPTIONS_CALLER_TYPE_URL_CLASS : 'This covers all URLs of a particular class. It overrides most other defaults. This is the place to set up blacklists particular to a certain site. The logic of passing from one URL to another can get tricky depending on the question, so if the site is complicated, spam these settings to all the URLs that might be involved (gallery, post, any file...) so you are covering every step of parsing and processing. Generally, though, the final "Post URL" encountered is the one that matters.',
    IMPORT_OPTIONS_CALLER_TYPE_SPECIFIC_IMPORTER : 'These import options are attached to this specific importer alone. If you set something here, it will only apply here, and it will definitely apply, overriding any other default.',
    IMPORT_OPTIONS_CALLER_TYPE_LOCAL_IMPORT_FOLDER : 'This covers all import folders, if you want different behaviour to a regular local import. A good place to set up quieter presentation options.',
    IMPORT_OPTIONS_CALLER_TYPE_CLIENT_API : 'This covers all files directly imported via the Client API, i.e. when an external program posts a raw file or a file path to be imported, with no downloader page involved. Only appropriate for file filtering and routing.',
    IMPORT_OPTIONS_CALLER_TYPE_FAVOURITES : 'This is a template you can load and paste wherever you need it.',
}

NON_DOWNLOADER_IMPORT_OPTION_CALLER_TYPES = {
    IMPORT_OPTIONS_CALLER_TYPE_LOCAL_IMPORT,
    IMPORT_OPTIONS_CALLER_TYPE_LOCAL_IMPORT_FOLDER,
    IMPORT_OPTIONS_CALLER_TYPE_CLIENT_API
}

IMPORT_OPTIONS_CALLER_TYPES_CANONICAL_ORDER = [
    IMPORT_OPTIONS_CALLER_TYPE_GLOBAL,
    IMPORT_OPTIONS_CALLER_TYPE_CLIENT_API,
    IMPORT_OPTIONS_CALLER_TYPE_LOCAL_IMPORT,
    IMPORT_OPTIONS_CALLER_TYPE_LOCAL_IMPORT_FOLDER,
    IMPORT_OPTIONS_CALLER_TYPE_WATCHER_URLS,
    IMPORT_OPTIONS_CALLER_TYPE_POST_URLS,
    IMPORT_OPTIONS_CALLER_TYPE_SUBSCRIPTION,
    IMPORT_OPTIONS_CALLER_TYPE_URL_CLASS,
    IMPORT_OPTIONS_CALLER_TYPE_SPECIFIC_IMPORTER,
]

IMPORT_OPTIONS_CALLER_TYPES_EDITABLE_CANONICAL_ORDER = [ ioct for ioct in IMPORT_OPTIONS_CALLER_TYPES_CANONICAL_ORDER if ioct not in ( IMPORT_OPTIONS_CALLER_TYPE_URL_CLASS, IMPORT_OPTIONS_CALLER_TYPE_SPECIFIC_IMPORTER ) ]

IMPORT_OPTIONS_TYPE_PREFETCH = 0
IMPORT_OPTIONS_TYPE_FILE_FILTERING = 1
IMPORT_OPTIONS_TYPE_TAG_FILTERING = 2
IMPORT_OPTIONS_TYPE_LOCATIONS = 3
IMPORT_OPTIONS_TYPE_TAGS = 4
IMPORT_OPTIONS_TYPE_NOTES = 5
IMPORT_OPTIONS_TYPE_PRESENTATION = 6
IMPORT_OPTIONS_TYPE_EXTERNAL_PROGRAMS = 7

import_options_type_str_lookup = {    
    IMPORT_OPTIONS_TYPE_PREFETCH : 'prefetch logic',
    IMPORT_OPTIONS_TYPE_FILE_FILTERING : 'file filtering',
    IMPORT_OPTIONS_TYPE_TAG_FILTERING : 'tag filtering',
    IMPORT_OPTIONS_TYPE_LOCATIONS : 'locations',
    IMPORT_OPTIONS_TYPE_TAGS : 'tags',
    IMPORT_OPTIONS_TYPE_NOTES : 'notes',
    IMPORT_OPTIONS_TYPE_PRESENTATION : 'presentation',
    IMPORT_OPTIONS_TYPE_EXTERNAL_PROGRAMS : 'external programs',
}

import_options_type_desc_lookup = {
    IMPORT_OPTIONS_TYPE_PREFETCH : 'Hydrus tries to save bandwidth. In most cases, it will not redownload a file page (HTML/JSON) or the file itself if it can correctly identify that it already has the file, or, in conjunction with file filtering options, wishes to exclude previously deleted files. Adjusting these settings can and will waste bandwidth and is only appropriate for one-off jobs where some forced recheck is needed.',
    IMPORT_OPTIONS_TYPE_FILE_FILTERING : 'Before a file is imported, it can be checked against these rules. If it fails one of these rules, it will get an "ignored" status.',
    IMPORT_OPTIONS_TYPE_TAG_FILTERING : 'Before a file is imported, its tags can be checked against a tag blacklist and/or whitelist. If a tag hits the blacklist, or no tag hits the whitelist, the import will get an "ignored" status. Only the tags that are parsed as part of the download are used in these tests.',
    IMPORT_OPTIONS_TYPE_LOCATIONS : 'If you have multiple local file services, you can choose to place incoming files in a different location than your default (probably "my files"). You can also send them to multiple locations.',
    IMPORT_OPTIONS_TYPE_TAGS : 'A file may pick up tags through the downloading and parsing process. Here you choose where to send any parsed tags.',
    IMPORT_OPTIONS_TYPE_NOTES : 'A file may pick up notes through the downloading and parsing process. Here you choose what to do with these notes. Default options are usually fine unless you have particular needs.',
    IMPORT_OPTIONS_TYPE_PRESENTATION : 'When files are imported, the importer will then likely want to show them, whether that is adding thumbnails to a page or publishing files to a popup button. Here you can filter which files are actually presented to UI. Selecting "only new" or "only inbox" are often useful to remove clutter in background/automated import workflows.',
    IMPORT_OPTIONS_TYPE_EXTERNAL_PROGRAMS : 'Here you can choose to run an external program for every file imported. This is only appropriate if you are maintaining a secondary database of additional metadata beside hydrus. Be careful with this!',
}

IMPORT_OPTIONS_TYPES_DOWNLOADER_ONLY = {
    IMPORT_OPTIONS_TYPE_PREFETCH,
    IMPORT_OPTIONS_TYPE_TAGS,
    IMPORT_OPTIONS_TYPE_TAG_FILTERING,
    IMPORT_OPTIONS_TYPE_NOTES,
}

IMPORT_OPTIONS_TYPES_CANONICAL_ORDER = [
    IMPORT_OPTIONS_TYPE_PREFETCH,
    IMPORT_OPTIONS_TYPE_FILE_FILTERING,
    IMPORT_OPTIONS_TYPE_TAG_FILTERING,
    IMPORT_OPTIONS_TYPE_LOCATIONS,
    IMPORT_OPTIONS_TYPE_TAGS,
    IMPORT_OPTIONS_TYPE_NOTES,
    IMPORT_OPTIONS_TYPE_EXTERNAL_PROGRAMS,
    IMPORT_OPTIONS_TYPE_PRESENTATION,
]

IMPORT_OPTIONS_TYPES_SIMPLE_MODE_LOOKUP = {
    IMPORT_OPTIONS_CALLER_TYPE_GLOBAL : IMPORT_OPTIONS_TYPES_CANONICAL_ORDER,
    IMPORT_OPTIONS_CALLER_TYPE_LOCAL_IMPORT : [ IMPORT_OPTIONS_TYPE_FILE_FILTERING, IMPORT_OPTIONS_TYPE_LOCATIONS, IMPORT_OPTIONS_TYPE_EXTERNAL_PROGRAMS, IMPORT_OPTIONS_TYPE_PRESENTATION ],
    IMPORT_OPTIONS_CALLER_TYPE_LOCAL_IMPORT_FOLDER : [ IMPORT_OPTIONS_TYPE_LOCATIONS, IMPORT_OPTIONS_TYPE_EXTERNAL_PROGRAMS, IMPORT_OPTIONS_TYPE_PRESENTATION ],
    IMPORT_OPTIONS_CALLER_TYPE_SUBSCRIPTION : [ IMPORT_OPTIONS_TYPE_LOCATIONS, IMPORT_OPTIONS_TYPE_PRESENTATION ],
    IMPORT_OPTIONS_CALLER_TYPE_POST_URLS : [ IMPORT_OPTIONS_TYPE_FILE_FILTERING, IMPORT_OPTIONS_TYPE_TAG_FILTERING, IMPORT_OPTIONS_TYPE_LOCATIONS, IMPORT_OPTIONS_TYPE_TAGS, IMPORT_OPTIONS_TYPE_NOTES, IMPORT_OPTIONS_TYPE_PRESENTATION ],
    IMPORT_OPTIONS_CALLER_TYPE_WATCHER_URLS : [ IMPORT_OPTIONS_TYPE_FILE_FILTERING, IMPORT_OPTIONS_TYPE_TAG_FILTERING, IMPORT_OPTIONS_TYPE_LOCATIONS, IMPORT_OPTIONS_TYPE_TAGS, IMPORT_OPTIONS_TYPE_NOTES, IMPORT_OPTIONS_TYPE_PRESENTATION ],
    IMPORT_OPTIONS_CALLER_TYPE_URL_CLASS : [ IMPORT_OPTIONS_TYPE_PREFETCH, IMPORT_OPTIONS_TYPE_FILE_FILTERING, IMPORT_OPTIONS_TYPE_TAG_FILTERING, IMPORT_OPTIONS_TYPE_LOCATIONS, IMPORT_OPTIONS_TYPE_TAGS, IMPORT_OPTIONS_TYPE_NOTES ],
    IMPORT_OPTIONS_CALLER_TYPE_CLIENT_API : [ IMPORT_OPTIONS_TYPE_FILE_FILTERING, IMPORT_OPTIONS_TYPE_LOCATIONS ],
    IMPORT_OPTIONS_CALLER_TYPE_SPECIFIC_IMPORTER : IMPORT_OPTIONS_TYPES_CANONICAL_ORDER,
    IMPORT_OPTIONS_CALLER_TYPE_FAVOURITES : IMPORT_OPTIONS_TYPES_CANONICAL_ORDER,
}

class ImportOptionsMetatype( HydrusSerialisable.SerialisableBase ):
    
    IMPORT_OPTIONS_TYPE = -1
    
    def _GetSerialisableInfo( self ):
        
        raise NotImplementedError()
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        raise NotImplementedError()
        
    
    def GetSummary( self, import_options_caller_type: int ) -> str:
        
        raise NotImplementedError()
        
    
