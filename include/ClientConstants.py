import collections
import dircache
import gc
import hashlib
import httplib
import HydrusConstants as HC
import HydrusImageHandling
import HydrusMessageHandling
import itertools
import multipart
import os
import random
import sqlite3
import threading
import time
import threading
import traceback
import urlparse
import urllib
import yaml
import wx
import zlib

ID_NULL = wx.NewId()

# Hue is generally 200, Sat and Lum changes based on need
COLOUR_SELECTED = wx.Colour( 217, 242, 255 )
COLOUR_SELECTED_DARK = wx.Colour( 1, 17, 26 )
COLOUR_UNSELECTED = wx.Colour( 223, 227, 230 )

COLOUR_MESSAGE = wx.Colour( 230, 246, 255 )

SHORTCUT_HELP = '''You can set up many custom shortcuts in file->options->shortcuts. Please check that to see your current mapping.

Some shortcuts remain hardcoded, however:

- While Browsing -
Ctrl + A - Select all
Escape - Deselect all
Ctrl + C - Copy selected files to clipboard

- In Fullscreen -
Shift-LeftClick-Drag - Drag (in Filter)
Ctrl + MouseWheel - Zoom
Z - Zoom Full/Fit'''

CLIENT_DESCRIPTION = '''This client is the media management application of the hydrus software suite.'''

COLLECT_BY_S = 0
COLLECT_BY_SV = 1
COLLECT_BY_SVC = 2
NO_COLLECTIONS = 3

COLLECTION_CHOICES = [ 'collect by series', 'collect by series-volume', 'collect by series-volume-chapter', 'no collections' ]

collection_enum_lookup = {}

collection_enum_lookup[ 'collect by series' ] = COLLECT_BY_S
collection_enum_lookup[ 'collect by series-volume' ] = COLLECT_BY_SV
collection_enum_lookup[ 'collect by series-volume-chapter' ] = COLLECT_BY_SVC
collection_enum_lookup[ 'no collections' ] = NO_COLLECTIONS

collection_string_lookup = {}

collection_string_lookup[ COLLECT_BY_S ] = 'collect by series'
collection_string_lookup[ COLLECT_BY_SV ] = 'collect by series-volume'
collection_string_lookup[ COLLECT_BY_SVC ] = 'collect by series-volume-chapter'
collection_string_lookup[ NO_COLLECTIONS ] = 'no collections'

DISCRIMINANT_INBOX = 0
DISCRIMINANT_LOCAL = 1
DISCRIMINANT_NOT_LOCAL = 2
DISCRIMINANT_ARCHIVE = 3

DUMPER_NOT_DUMPED = 0
DUMPER_DUMPED_OK = 1
DUMPER_RECOVERABLE_ERROR = 2
DUMPER_UNRECOVERABLE_ERROR = 3

FIELD_VERIFICATION_RECAPTCHA = 0
FIELD_COMMENT = 1
FIELD_TEXT = 2
FIELD_CHECKBOX = 3
FIELD_FILE = 4
FIELD_THREAD_ID = 5
FIELD_PASSWORD = 6

FIELDS = [ FIELD_VERIFICATION_RECAPTCHA, FIELD_COMMENT, FIELD_TEXT, FIELD_CHECKBOX, FIELD_FILE, FIELD_THREAD_ID, FIELD_PASSWORD ]

field_enum_lookup = {}

field_enum_lookup[ 'recaptcha' ] = FIELD_VERIFICATION_RECAPTCHA
field_enum_lookup[ 'comment' ] = FIELD_COMMENT
field_enum_lookup[ 'text' ] = FIELD_TEXT
field_enum_lookup[ 'checkbox' ] = FIELD_CHECKBOX
field_enum_lookup[ 'file' ] = FIELD_FILE
field_enum_lookup[ 'thread id' ] = FIELD_THREAD_ID
field_enum_lookup[ 'password' ] = FIELD_PASSWORD

field_string_lookup = {}

field_string_lookup[ FIELD_VERIFICATION_RECAPTCHA ] = 'recaptcha'
field_string_lookup[ FIELD_COMMENT ] = 'comment'
field_string_lookup[ FIELD_TEXT ] = 'text'
field_string_lookup[ FIELD_CHECKBOX ] = 'checkbox'
field_string_lookup[ FIELD_FILE ] = 'file'
field_string_lookup[ FIELD_THREAD_ID ] = 'thread id'
field_string_lookup[ FIELD_PASSWORD ] = 'password'

LOG_ERROR = 0
LOG_MESSAGE = 1

log_string_lookup = {}

log_string_lookup[ LOG_ERROR ] = 'error'
log_string_lookup[ LOG_MESSAGE ] = 'message'

RESTRICTION_MIN_RESOLUTION = 0
RESTRICTION_MAX_RESOLUTION = 1
RESTRICTION_MAX_FILE_SIZE = 2
RESTRICTION_ALLOWED_MIMES = 3

SHUTDOWN_TIMESTAMP_VACUUM = 0
SHUTDOWN_TIMESTAMP_FATTEN_AC_CACHE = 1
SHUTDOWN_TIMESTAMP_DELETE_ORPHANS = 2

SORT_BY_SMALLEST = 0
SORT_BY_LARGEST = 1
SORT_BY_SHORTEST = 2
SORT_BY_LONGEST = 3
SORT_BY_NEWEST = 4
SORT_BY_OLDEST = 5
SORT_BY_MIME = 6
SORT_BY_RANDOM = 7
SORT_BY_LEXICOGRAPHIC_ASC = 8
SORT_BY_LEXICOGRAPHIC_DESC = 9
SORT_BY_INCIDENCE_ASC = 10
SORT_BY_INCIDENCE_DESC = 11

SORT_CHOICES = []

SORT_CHOICES.append( ( 'system', SORT_BY_SMALLEST ) )
SORT_CHOICES.append( ( 'system', SORT_BY_LARGEST ) )
SORT_CHOICES.append( ( 'system', SORT_BY_SHORTEST ) )
SORT_CHOICES.append( ( 'system', SORT_BY_LONGEST ) )
SORT_CHOICES.append( ( 'system', SORT_BY_NEWEST ) )
SORT_CHOICES.append( ( 'system', SORT_BY_OLDEST ) )
SORT_CHOICES.append( ( 'system', SORT_BY_MIME ) )
SORT_CHOICES.append( ( 'system', SORT_BY_RANDOM ) )

sort_enum_lookup = {}

sort_enum_lookup[ 'smallest first' ] = SORT_BY_SMALLEST
sort_enum_lookup[ 'largest first' ] = SORT_BY_LARGEST
sort_enum_lookup[ 'shortest first' ] = SORT_BY_SHORTEST
sort_enum_lookup[ 'longest first' ] = SORT_BY_LONGEST
sort_enum_lookup[ 'newest first' ] = SORT_BY_NEWEST
sort_enum_lookup[ 'oldest first' ] = SORT_BY_OLDEST
sort_enum_lookup[ 'order by mime' ] = SORT_BY_MIME
sort_enum_lookup[ 'random order' ] = SORT_BY_RANDOM

sort_string_lookup = {}

sort_string_lookup[ SORT_BY_SMALLEST ] = 'smallest first'
sort_string_lookup[ SORT_BY_LARGEST ] = 'largest first'
sort_string_lookup[ SORT_BY_SHORTEST ] = 'shortest first'
sort_string_lookup[ SORT_BY_LONGEST ] = 'longest first'
sort_string_lookup[ SORT_BY_NEWEST ] = 'newest first'
sort_string_lookup[ SORT_BY_OLDEST ] = 'oldest first'
sort_string_lookup[ SORT_BY_MIME ] = 'mime'
sort_string_lookup[ SORT_BY_RANDOM ] = 'random order'

THUMBNAIL_MARGIN = 2
THUMBNAIL_BORDER = 1

UNKNOWN_ACCOUNT_TYPE = HC.AccountType( 'unknown account', [], ( None, None ) )

def AddPaddingToDimensions( dimensions, padding ):
    
    ( x, y ) = dimensions
    
    return ( x + padding, y + padding )
    
def GenerateCollectByChoices( sort_by_choices ):
    
    already_added = set()
    
    collect_choices = []
    
    for ( sort_by_type, namespaces ) in sort_by_choices:
        
        for i in range( 1, len( namespaces ) ):
            
            combinations = itertools.combinations( namespaces, i )
            
            for combination in combinations:
                
                combination_set = frozenset( combination )
                
                if combination_set not in already_added:
                    
                    already_added.add( combination_set )
                    
                    collect_choices.append( ( 'collect by ' + '-'.join( combination ), combination ) )
                    
                
            
        '''
        namespaces_set = frozenset( namespaces )
        
        if namespaces_set not in already_added:
            
            collect_choices.append( ( 'collect by ' + '-'.join( namespaces ), namespaces ) )
            
            already_added.add( namespaces_set )
            
        
        for i in range( 1, len( namespaces ) ):
            
            sub_namespaces = namespaces[:-i]
            
            sub_namespaces_set = frozenset( sub_namespaces )
            
            if sub_namespaces_set not in already_added:
                
                collect_choices.append( ( 'collect by ' + '-'.join( sub_namespaces ), sub_namespaces ) )
                
                already_added.add( sub_namespaces_set )
                
            
        '''
    
    collect_choices.sort()
    
    collect_choices.insert( 0, ( 'no collections', None ) )
    
    return collect_choices
    
def GenerateDumpMultipartFormDataCTAndBody( fields ):
    
    m = multipart.Multipart()
    
    for ( name, type, value ) in fields:
        
        if type in ( FIELD_TEXT, FIELD_COMMENT, FIELD_PASSWORD, FIELD_VERIFICATION_RECAPTCHA, FIELD_THREAD_ID ): m.field( name, str( value ) )
        elif type == FIELD_CHECKBOX:
            
            if value: 
                
                ( name, value ) = value.split( '/', 1 )
                
                m.field( name, value )
                
            
        elif type == FIELD_FILE:
            
            ( hash, mime, file ) = value
            
            m.file( name, hash.encode( 'hex' ) + HC.mime_ext_lookup[ mime ], file, { 'Content-Type' : HC.mime_string_lookup[ mime ] } )
            
        
    
    return m.get()
    
def GenerateMultipartFormDataCTAndBodyFromDict( fields ):
    
    m = multipart.Multipart()
    
    for ( name, value ) in fields.items(): m.field( name, str( value ) )
    
    return m.get()
    
def GetFilePath( hash, mime ):
    
    hash_encoded = hash.encode( 'hex' )
    
    first_two_chars = hash_encoded[:2]
    
    return HC.CLIENT_FILES_DIR + os.path.sep + first_two_chars + os.path.sep + hash_encoded + HC.mime_ext_lookup[ mime ]
    
def GetMediasTagCount( pool, tag_service_identifier = HC.NULL_SERVICE_IDENTIFIER ):
    
    all_tags = []
    
    for media in pool:
        
        if media.IsCollection(): all_tags.extend( media.GetSingletonsTags() )
        else: all_tags.append( media.GetTags() )
        
    
    current_tags_to_count = collections.Counter()
    deleted_tags_to_count = collections.Counter()
    pending_tags_to_count = collections.Counter()
    petitioned_tags_to_count = collections.Counter()
    
    for tags in all_tags:
        
        if tag_service_identifier == HC.NULL_SERVICE_IDENTIFIER: ( current, deleted, pending, petitioned ) = tags.GetUnionCDPP()
        else: ( current, deleted, pending, petitioned ) = tags.GetCDPP( tag_service_identifier )
        
        current_tags_to_count.update( current )
        deleted_tags_to_count.update( pending )
        pending_tags_to_count.update( pending )
        petitioned_tags_to_count.update( petitioned )
        
    
    return ( current_tags_to_count, deleted_tags_to_count, pending_tags_to_count, petitioned_tags_to_count )
    
def GetThumbnailPath( hash ):
    
    hash_encoded = hash.encode( 'hex' )
    
    first_two_chars = hash_encoded[:2]
    
    return HC.CLIENT_THUMBNAILS_DIR + os.path.sep + first_two_chars + os.path.sep + hash_encoded
    
def GetUnknownAccount(): return HC.Account( 0, UNKNOWN_ACCOUNT_TYPE, 0, None, ( 0, 0 ) )

def IterateAllFilePaths():
    
    hex_chars = '0123456789abcdef'
    
    for ( one, two ) in itertools.product( hex_chars, hex_chars ):
        
        next_paths = dircache.listdir( HC.CLIENT_FILES_DIR + os.path.sep + one + two )
        
        for path in next_paths: yield path
        
    
def IterateAllThumbnailPaths():
    
    hex_chars = '0123456789abcdef'
    
    for ( one, two ) in itertools.product( hex_chars, hex_chars ):
        
        next_paths = dircache.listdir( HC.CLIENT_THUMBNAIL_DIR + os.path.sep + one + two )
        
        for path in next_paths: yield path
        
    
def MediaIntersectCDPPTagServiceIdentifiers( media, service_identifier ):
    
    all_tag_cdpps = [ m.GetTags().GetCDPP( service_identifier ) for m in media ]
    
    current = list( HC.IntelligentMassIntersect( ( cdpp[0] for cdpp in all_tag_cdpps ) ) )
    deleted = list( HC.IntelligentMassIntersect( ( cdpp[1] for cdpp in all_tag_cdpps ) ) )
    pending = list( HC.IntelligentMassIntersect( ( cdpp[2] for cdpp in all_tag_cdpps ) ) )
    petitioned = list( HC.IntelligentMassIntersect( ( cdpp[3] for cdpp in all_tag_cdpps ) ) )
    
    return ( current, deleted, pending, petitioned )
    
def ParseImportablePaths( raw_paths, include_subdirs = True ):
    
    file_paths = []
    
    if include_subdirs: title = 'Parsing files and subdirectories'
    else: title = 'Parsing files'
    
    progress = wx.ProgressDialog( title, u'Preparing', 1000, None, style=wx.PD_APP_MODAL | wx.PD_AUTO_HIDE | wx.PD_CAN_ABORT | wx.PD_ELAPSED_TIME | wx.PD_ESTIMATED_TIME | wx.PD_REMAINING_TIME )
    
    try:
        
        paths_to_process = raw_paths
        
        total_paths_to_process = len( paths_to_process )
        
        num_processed = 0
        
        while len( paths_to_process ) > 0:
            
            next_paths_to_process = []
            
            for path in paths_to_process:
                
                # would rather use progress.SetRange( total_paths_to_process ) here, but for some reason wx python doesn't support it!
                
                permill = int( 1000 * ( float( num_processed ) / float( total_paths_to_process ) ) )
                
                ( should_continue, skip ) = progress.Update( permill, 'Done ' + str( num_processed ) + '/' + str( total_paths_to_process ) )
                
                if not should_continue:
                    
                    progress.Destroy()
                    
                    return []
                    
                
                if os.path.isdir( path ):
                    
                    if include_subdirs:
                        
                        subpaths = [ path + os.path.sep + filename for filename in dircache.listdir( path ) ]
                        
                        total_paths_to_process += len( subpaths )
                        
                        next_paths_to_process.extend( subpaths )
                        
                    
                else: file_paths.append( path )
                
                num_processed += 1
                
            
            paths_to_process = next_paths_to_process
            
        
    except: wx.MessageBox( traceback.format_exc() )
    
    progress.Destroy()
    
    good_paths = []
    odd_paths = []
    
    num_file_paths = len( file_paths )
    
    progress = wx.ProgressDialog( 'Checking files\' mimetypes', u'Preparing', num_file_paths, None, style=wx.PD_APP_MODAL | wx.PD_AUTO_HIDE | wx.PD_CAN_ABORT | wx.PD_ELAPSED_TIME | wx.PD_ESTIMATED_TIME | wx.PD_REMAINING_TIME )
    
    for ( i, path ) in enumerate( file_paths ):
        
        ( should_continue, skip ) = progress.Update( i, 'Done ' + str( i ) + '/' + str( num_file_paths ) )
        
        if not should_continue: break
        
        mime = HC.GetMimeFromPath( path )
        
        if mime in HC.ALLOWED_MIMES:
            
            info = os.lstat( path )
            
            size = info[6]
            
            if size > 0: good_paths.append( path )
            
        else: odd_paths.append( path )
        
    
    progress.Destroy()
    
    if len( odd_paths ) > 0:
        
        print( 'Because of mime, the client could not import the following files:' )
        for odd_path in odd_paths: print( odd_path )
        
        wx.MessageBox( 'The ' + str( len( odd_paths ) ) + ' files that were not jpegs, pngs, bmps or gifs will not be added. If you are interested, their paths have been written to the log.' )
        
    
    return good_paths
    
class AutocompleteMatches():
    
    def __init__( self, matches ):
        
        self._matches = matches
        
        self._matches.sort()
        
    
    def GetMatches( self, search ): return [ match for match in self._matches if HC.SearchEntryMatchesTag( search, match ) ]
    
class AutocompleteMatchesCounted():
    
    def __init__( self, matches_to_count ):
        
        self._matches_to_count = matches_to_count
        self._matches = self._matches_to_count.keys()
        
        def cmp_func( x, y ): return cmp( matches_to_count[ x ], matches_to_count[ y ] )
        
        self._matches.sort( cmp = cmp_func, reverse = True )
        
    
    def GetMatches( self, search ): return [ ( match, self._matches_to_count[ match ] ) for match in self._matches if HC.SearchEntryMatchesTag( search, match ) ]
    
class AutocompleteMatchesPredicates():
    
    def __init__( self, predicates ):
        
        self._predicates = predicates
        
        def cmp_func( x, y ): return cmp( x.GetCount(), y.GetCount() )
        
        self._predicates.sort( cmp = cmp_func, reverse = True )
        
    
    def GetMatches( self, search ): return [ predicate for predicate in self._predicates if HC.SearchEntryMatchesPredicate( search, predicate ) ]
    
class Booru( HC.HydrusYAMLBase ):
    
    yaml_tag = u'!Booru'
    
    def __init__( self, name, search_url, search_separator, advance_by_page_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces ):
        
        self._name = name
        self._search_url = search_url
        self._search_separator = search_separator
        self._advance_by_page_num = advance_by_page_num
        self._thumb_classname = thumb_classname
        self._image_id = image_id
        self._image_data = image_data
        self._tag_classnames_to_namespaces = tag_classnames_to_namespaces
        
    
    def GetData( self ): return ( self._search_url, self._search_separator, self._advance_by_page_num, self._thumb_classname, self._image_id, self._image_data, self._tag_classnames_to_namespaces )
    
    def GetGalleryParsingInfo( self ): return ( self._search_url, self._advance_by_page_num, self._search_separator, self._thumb_classname )
    
    def GetName( self ): return self._name
    
    def GetNamespaces( self ): return self._tag_classnames_to_namespaces.values()
    
sqlite3.register_adapter( Booru, yaml.safe_dump )

DEFAULT_BOORUS = []

name = 'gelbooru'
search_url = 'http://gelbooru.com/index.php?page=post&s=list&tags=%tags%&pid=%index%'
search_separator = '+'
advance_by_page_num = False
thumb_classname = 'thumb'
image_id = None
image_data = 'Original image'
tag_classnames_to_namespaces = { 'tag-type-general' : '', 'tag-type-character' : 'character', 'tag-type-copyright' : 'series', 'tag-type-artist' : 'creator' }

DEFAULT_BOORUS.append( Booru( name, search_url, search_separator, advance_by_page_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces ) )

name = 'safebooru'
search_url = 'http://safebooru.org/index.php?page=post&s=list&tags=%tags%&pid=%index%'
search_separator = '+'
advance_by_page_num = False
thumb_classname = 'thumb'
image_id = None
image_data = 'Original image'
tag_classnames_to_namespaces = { 'tag-type-general' : '', 'tag-type-character' : 'character', 'tag-type-copyright' : 'series', 'tag-type-artist' : 'creator' }

DEFAULT_BOORUS.append( Booru( name, search_url, search_separator, advance_by_page_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces ) )

name = 'e621'
search_url = 'http://e621.net/post/index?page=%index%&tags=%tags%'
search_separator = '%20'
advance_by_page_num = True
thumb_classname = 'thumb blacklisted'
image_id = None
image_data = 'Download'
tag_classnames_to_namespaces = { 'tag-type-general' : '', 'tag-type-character' : 'character', 'tag-type-copyright' : 'series', 'tag-type-artist' : 'creator' }

DEFAULT_BOORUS.append( Booru( name, search_url, search_separator, advance_by_page_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces ) )

name = 'rule34@paheal'
search_url = 'http://rule34.paheal.net/post/list/%tags%/%index%'
search_separator = '%20'
advance_by_page_num = True
thumb_classname = 'thumb'
image_id = 'main_image'
image_data = None
tag_classnames_to_namespaces = { 'tag_name' : '' }

DEFAULT_BOORUS.append( Booru( name, search_url, search_separator, advance_by_page_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces ) )

name = 'danbooru'
search_url = 'http://danbooru.donmai.us/post/index?tags=%tags%&commit=Search&page=%index%'
search_separator = '%20'
advance_by_page_num = True
thumb_classname = 'thumb blacklisted'
image_id = 'image'
image_data = None
tag_classnames_to_namespaces = { 'tag-type-general' : '', 'tag-type-character' : 'character', 'tag-type-copyright' : 'series', 'tag-type-artist' : 'creator' }

DEFAULT_BOORUS.append( Booru( name, search_url, search_separator, advance_by_page_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces ) )

name = 'mishimmie'
search_url = 'http://shimmie.katawa-shoujo.com/post/list/%tags%/%index%'
search_separator = '%20'
advance_by_page_num = True
thumb_classname = 'thumb'
image_id = 'main_image'
image_data = None
tag_classnames_to_namespaces = { 'tag_name' : '' }

DEFAULT_BOORUS.append( Booru( name, search_url, search_separator, advance_by_page_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces ) )

name = 'rule34@booru.org'
search_url = 'http://rule34.xxx/index.php?page=post&s=list&tags=%tags%&pid=%index%'
search_separator = '%20'
advance_by_page_num = False
thumb_classname = 'thumb'
image_id = None
image_data = 'Original image'
tag_classnames_to_namespaces = { 'tag-type-general' : '' }

DEFAULT_BOORUS.append( Booru( name, search_url, search_separator, advance_by_page_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces ) )

name = 'furry@booru.org'
search_url = 'http://furry.booru.org/index.php?page=post&s=list&tags=%tags%&pid=%index%'
search_separator = '+'
advance_by_page_num = False
thumb_classname = 'thumb'
image_id = None
image_data = 'Original image'
tag_classnames_to_namespaces = { 'tag-type-general' : '', 'tag-type-character' : 'character', 'tag-type-copyright' : 'series', 'tag-type-artist' : 'creator' }

DEFAULT_BOORUS.append( Booru( name, search_url, search_separator, advance_by_page_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces ) )

name = 'xbooru'
search_url = 'http://xbooru.com/index.php?page=post&s=list&tags=%tags%&pid=%index%'
search_separator = '+'
advance_by_page_num = False
thumb_classname = 'thumb'
image_id = None
image_data = 'Original image'
tag_classnames_to_namespaces = { 'tag-type-general' : '', 'tag-type-character' : 'character', 'tag-type-copyright' : 'series', 'tag-type-artist' : 'creator' }

DEFAULT_BOORUS.append( Booru( name, search_url, search_separator, advance_by_page_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces ) )

name = 'konachan'
search_url = 'http://konachan.com/post?page=%index%&tags=%tags%'
search_separator = '+'
advance_by_page_num = True
thumb_classname = 'thumb'
image_id = None
image_data = 'View larger version'
tag_classnames_to_namespaces = { 'tag-type-general' : '', 'tag-type-character' : 'character', 'tag-type-copyright' : 'series', 'tag-type-artist' : 'creator' }

DEFAULT_BOORUS.append( Booru( name, search_url, search_separator, advance_by_page_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces ) )

name = 'tbib'
search_url = 'http://tbib.org/index.php?page=post&s=list&tags=%tags%&pid=%index%'
search_separator = '+'
advance_by_page_num = False
thumb_classname = 'thumb'
image_id = None
image_data = 'Original image'
tag_classnames_to_namespaces = { 'tag-type-general' : '', 'tag-type-character' : 'character', 'tag-type-copyright' : 'series', 'tag-type-artist' : 'creator' }

DEFAULT_BOORUS.append( Booru( name, search_url, search_separator, advance_by_page_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces ) )

class CDPPFileServiceIdentifiers():
    
    def __init__( self, current, deleted, pending, petitioned ):
        
        self._current = current
        self._deleted = deleted
        self._pending = pending
        self._petitioned = petitioned
        
    
    def DeletePending( self, service_identifier ):
        
        self._pending.discard( service_identifier )
        self._petitioned.discard( service_identifier )
        
    
    def GetCDPP( self ): return ( self._current, self._deleted, self._pending, self._petitioned )
    
    def GetCurrent( self ): return self._current
    def GetCurrentRemote( self ): return self._current - set( ( HC.LOCAL_FILE_SERVICE_IDENTIFIER, ) )
    
    def GetDeleted( self ): return self._deleted
    def GetDeletedRemote( self ): return self._deleted - set( ( HC.LOCAL_FILE_SERVICE_IDENTIFIER, ) )
    
    def GetPending( self ): return self._pending
    def GetPendingRemote( self ): return self._pending - set( ( HC.LOCAL_FILE_SERVICE_IDENTIFIER, ) )
    
    def GetPetitioned( self ): return self._petitioned
    def GetPetitionedRemote( self ): return self._petitioned - set( ( HC.LOCAL_FILE_SERVICE_IDENTIFIER, ) )
    
    def HasDownloading( self ): return HC.LOCAL_FILE_SERVICE_IDENTIFIER in self._pending
    
    def HasLocal( self ): return HC.LOCAL_FILE_SERVICE_IDENTIFIER in self._current
    
    def ProcessContentUpdate( self, content_update ):
        
        action = content_update.GetAction()
        
        service_identifier = content_update.GetServiceIdentifier()
        
        if action == HC.CONTENT_UPDATE_ADD:
            
            self._current.add( service_identifier )
            
            self._deleted.discard( service_identifier )
            self._pending.discard( service_identifier )
            
        elif action == HC.CONTENT_UPDATE_DELETE:
            
            self._deleted.add( service_identifier )
            
            self._current.discard( service_identifier )
            self._petitioned.discard( service_identifier )
            
        elif action == HC.CONTENT_UPDATE_PENDING:
            
            if service_identifier not in self._current: self._pending.add( service_identifier )
            
        elif action == HC.CONTENT_UPDATE_PETITION:
            
            if service_identifier not in self._deleted: self._petitioned.add( service_identifier )
            
        elif action == HC.CONTENT_UPDATE_RESCIND_PENDING: self._pending.discard( service_identifier )
        elif action == HC.CONTENT_UPDATE_RESCIND_PETITION: self._petitioned.discard( service_identifier )
        
    
    def ResetService( self, service_identifier ):
        
        self._current.discard( service_identifier )
        self._deleted.discard( service_identifier )
        self._petitioned.discard( service_identifier )
        
    
class CDPPTagServiceIdentifiers():
    
    def __init__( self, tag_service_precedence, service_identifiers_to_cdpp ):
        
        self._tag_service_precedence = tag_service_precedence
        
        self._service_identifiers_to_cdpp = service_identifiers_to_cdpp
        
        self._Recalc()
        
    
    def _Recalc( self ):
        
        self._current = set()
        self._deleted = set()
        self._pending = set()
        self._petitioned = set()
        
        t_s_p = list( self._tag_service_precedence )
        
        t_s_p.reverse()
        
        for service_identifier in t_s_p:
            
            if service_identifier in self._service_identifiers_to_cdpp:
                
                ( current, deleted, pending, petitioned ) = self._service_identifiers_to_cdpp[ service_identifier ]
                
                # the difference_update stuff is making active_mappings from tag_service_precedence
                
                self._current.update( current )
                self._current.difference_update( deleted )
                
                self._deleted.update( deleted )
                self._deleted.difference_update( current )
                
                self._pending.update( pending )
                self._pending.difference_update( deleted )
                
                self._petitioned.update( petitioned )
                self._petitioned.difference_update( current )
                
            
        
        self._creators = set()
        self._series = set()
        self._titles = set()
        self._volumes = set()
        self._chapters = set()
        self._pages = set()
        
        for tag in self._current | self._pending:
            
            if tag.startswith( 'creator:' ): self._creators.add( tag.split( 'creator:', 1 )[1] )
            elif tag.startswith( 'series:' ): self._series.add( tag.split( 'series:', 1 )[1] )
            elif tag.startswith( 'title:' ): self._titles.add( tag.split( 'title:', 1 )[1] )
            elif tag.startswith( 'volume:' ): self._volumes.add( int( tag.split( 'volume:', 1 )[1] ) )
            elif tag.startswith( 'chapter:' ): self._chapters.add( int( tag.split( 'chapter:', 1 )[1] ) )
            elif tag.startswith( 'page:' ): self._pages.add( int( tag.split( 'page:', 1 )[1] ) )
            
        
    
    def GetCSTVCP( self ): return ( self._creators, self._series, self._titles, self._volumes, self._chapters, self._pages )
    
    def DeletePending( self, service_identifier ):
        
        if service_identifier in self._service_identifiers_to_cdpp:
            
            ( current, deleted, pending, petitioned ) = self._service_identifiers_to_cdpp[ service_identifier ]
            
            if len( pending ) > 0 or len( petitioned ) > 0:
                
                self._service_identifiers_to_cdpp[ service_identifier ] = ( current, deleted, set(), set() )
                
                self._Recalc()
                
            
        
    
    def GetCDPP( self, service_identifier ):
        
        if service_identifier in self._service_identifiers_to_cdpp: return self._service_identifiers_to_cdpp[ service_identifier ]
        else: return ( set(), set(), set(), set() )
        
    
    def GetNamespaceSlice( self, namespaces ): return frozenset( [ tag for tag in list( self._current ) + list( self._pending ) if True in ( tag.startswith( namespace + ':' ) for namespace in namespaces ) ] )
    
    def GetNumTags( self, tag_service_identifier, include_current_tags = True, include_pending_tags = False ):
        
        num_tags = 0
        
        if tag_service_identifier == HC.NULL_SERVICE_IDENTIFIER:
            
            if include_current_tags: num_tags += len( self._current )
            if include_pending_tags: num_tags += len( self._pending )
            
        else:
            
            ( current, deleted, pending, petitioned ) = self.GetCDPP( tag_service_identifier )
            
            if include_current_tags: num_tags += len( current )
            if include_pending_tags: num_tags += len( pending )
            
        
        return num_tags
        
    
    def GetServiceIdentifiersToCDPP( self ): return self._service_identifiers_to_cdpp
    
    def GetUnionCDPP( self ): return ( self._current, self._deleted, self._pending, self._petitioned )
    
    def HasTag( self, tag ): return tag in self._current or tag in self._pending
    
    def ProcessContentUpdate( self, content_update ):
        
        service_identifier = content_update.GetServiceIdentifier()
        
        if service_identifier in self._service_identifiers_to_cdpp: ( current, deleted, pending, petitioned ) = self._service_identifiers_to_cdpp[ service_identifier ]
        else:
            
            ( current, deleted, pending, petitioned ) = ( set(), set(), set(), set() )
            
            self._service_identifiers_to_cdpp[ service_identifier ] = ( current, deleted, pending, petitioned )
            
        
        action = content_update.GetAction()
        
        if action == HC.CONTENT_UPDATE_ADD:
            
            tag = content_update.GetInfo()
            
            current.add( tag )
            
            deleted.discard( tag )
            pending.discard( tag )
            
        elif action == HC.CONTENT_UPDATE_DELETE:
            
            tag = content_update.GetInfo()
            
            deleted.add( tag )
            
            current.discard( tag )
            petitioned.discard( tag )
            
        elif action == HC.CONTENT_UPDATE_EDIT_LOG:
            
            edit_log = content_update.GetInfo()
            
            for ( action, info ) in edit_log:
                
                if action == HC.CONTENT_UPDATE_ADD:
                    
                    tag = info
                    
                    current.add( tag )
                    
                    deleted.discard( tag )
                    pending.discard( tag )
                    
                elif action == HC.CONTENT_UPDATE_DELETE:
                    
                    tag = info
                    
                    deleted.add( tag )
                    
                    current.discard( tag )
                    petitioned.discard( tag )
                    
                elif action == HC.CONTENT_UPDATE_PENDING:
                    
                    tag = info
                    
                    if tag not in current: pending.add( tag )
                    
                elif action == HC.CONTENT_UPDATE_RESCIND_PENDING:
                    
                    tag = info
                    
                    pending.discard( tag )
                    
                elif action == HC.CONTENT_UPDATE_PETITION:
                    
                    ( tag, reason ) = info
                    
                    if tag not in deleted: petitioned.add( tag )
                    
                elif action == HC.CONTENT_UPDATE_RESCIND_PETITION:
                    
                    tag = info
                    
                    petitioned.discard( tag )
                    
                
            
        
        self._Recalc()
        
    
    def ResetService( self, service_identifier ):
        
        if service_identifier in self._service_identifiers_to_cdpp:
            
            ( current, deleted, pending, petitioned ) = self._service_identifiers_to_cdpp[ service_identifier ]
            
            self._service_identifiers_to_cdpp[ service_identifier ] = ( set(), set(), pending, set() )
            
            self._Recalc()
            
        
    
class LocalRatings():
    
    # c for current; feel free to rename this stupid thing
    
    def __init__( self, service_identifiers_to_ratings ):
        
        self._service_identifiers_to_ratings = service_identifiers_to_ratings
        
    
    def GetRating( self, service_identifier ):
        
        if service_identifier in self._service_identifiers_to_ratings: return self._service_identifiers_to_ratings[ service_identifier ]
        else: return None
        
    
    def GetRatingSlice( self, service_identifiers ): return frozenset( { self._service_identifiers_to_ratings[ service_identifier ] for service_identifier in service_identifiers if service_identifier in self._service_identifiers_to_ratings } )
    
    def GetServiceIdentifiersToRatings( self ): return self._service_identifiers_to_ratings
    
    def ProcessContentUpdate( self, content_update ):
        
        service_identifier = content_update.GetServiceIdentifier()
        
        action = content_update.GetAction()
        
        if action == HC.CONTENT_UPDATE_RATING:
            
            rating = content_update.GetInfo()
            
            if rating is None and service_identifier in self._service_identifiers_to_ratings: del self._service_identifiers_to_ratings[ service_identifier ]
            else: self._service_identifiers_to_ratings[ service_identifier ] = rating
            
        
    
    def ResetService( self, service_identifier ):
        
        if service_identifier in self._service_identifiers_to_ratings: del self._service_identifiers_to_ratings[ service_identifier ]
        
    
class ConnectionToService():
    
    def __init__( self, service_identifier, credentials ):
        
        self._service_identifier = service_identifier
        self._credentials = credentials
        
        try:
            
            ( host, port ) = self._credentials.GetAddress()
            
            self._connection = HC.AdvancedHTTPConnection( host = host, port = port, service_identifier = self._service_identifier, accept_cookies = True )
            
            self._connection.connect()
            
        except:
            
            error_message = 'Could not connect.'
            
            if self._service_identifier is not None: HC.pubsub.pub( 'service_update_db', HC.ServiceUpdate( HC.SERVICE_UPDATE_ERROR, self._service_identifier, error_message ) )
            
            raise Exception( error_message )
            
        
    
    def _GetHeaders( self, request ):
        
        headers = {}
        
        if request == 'init': pass
        elif request == 'session_key':
            
            if self._credentials.HasAccessKey():
                
                access_key = self._credentials.GetAccessKey()
                
                if access_key != '': headers[ 'Authorization' ] = 'hydrus_network ' + access_key.encode( 'hex' )
                
            else: raise Exception( 'No access key!' )
            
        elif self._service_identifier.GetType() in HC.RESTRICTED_SERVICES:
            
            session_key = wx.GetApp().GetSessionKey( self._service_identifier )
            
            headers[ 'Cookie' ] = 'session_key=' + session_key.encode( 'hex' )
            
        
        return headers
        
    
    def _SendRequest( self, request_type, request, request_args = {} ):
        
        # prepare
        
        if request_type == HC.GET:
            
            request_type_string = 'GET'
            
            request_string = '/' + request
            
            if 'subject_identifier' in request_args:
                
                subject_identifier = request_args[ 'subject_identifier' ]
                
                del request_args[ 'subject_identifier' ]
                
                if subject_identifier.HasAccessKey():
                    
                    subject_access_key = subject_identifier.GetAccessKey()
                    
                    request_args[ 'subject_access_key' ] = subject_access_key.encode( 'hex' )
                    
                elif subject_identifier.HasAccountId():
                    
                    subject_account_id = subject_identifier.GetAccountId()
                    
                    request_args[ 'subject_account_id' ] = subject_account_id
                    
                elif subject_identifier.HasHash():
                    
                    subject_hash = subject_identifier.GetHash()
                    
                    request_args[ 'subject_hash' ] = subject_hash.encode( 'hex' )
                    
                    if subject_identifier.HasMapping():
                        
                        ( subject_tag, subject_hash ) = subject_identifier.GetMapping()
                        
                        request_args[ 'subject_tag' ] = subject_tag.encode( 'hex' )
                        
                    
                
            
            if 'title' in request_args:
                
                request_args[ 'title' ] = request_args[ 'title' ].encode( 'hex' )
                
            
            if len( request_args ) > 0: request_string += '?' + '&'.join( [ key + '=' + str( value ) for ( key, value ) in request_args.items() ] )
            
            body = None
            
        elif request_type == HC.POST:
            
            request_type_string = 'POST'
            
            request_string = '/' + request
            
            if request == 'file': body = request_args[ 'file' ]
            else: body = yaml.safe_dump( request_args )
            
        
        headers = self._GetHeaders( request )
        
        # send
        
        try: response = self._connection.request( request_type_string, request_string, headers = headers, body = body )
        except HC.ForbiddenException as e:
            
            if unicode( e ) == 'Session not found!':
                
                wx.GetApp().DeleteSessionKey( self._service_identifier )
                
                response = self._connection.request( request_type_string, request_string, headers = headers, body = body )
                
            else: raise e
            
        
        return response
        
    
    def Close( self ):
        
        try: self._connection.close()
        except: pass
        
    
    def Get( self, request, **kwargs ):
        
        response = self._SendRequest( HC.GET, request, kwargs )
        
        if request in ( 'registration_keys', 'init' ):
            
            if request == 'registration_keys':
                
                body = os.linesep.join( [ 'r' + key.encode( 'hex' ) for key in response ] )
                
                filename = 'registration keys.txt'
                
            elif request == 'init':
                
                filename = 'admin access key.txt'
                
                access_key = response
                
                body = access_key.encode( 'hex' )
                
                ( host, port ) = self._credentials.GetAddress()
                
                self._credentials = Credentials( host, port, access_key )
                
                edit_log = [ ( 'edit', ( self._service_identifier, ( self._service_identifier, self._credentials, None ) ) ) ]
                
                wx.GetApp().Write( 'update_services', edit_log )
                
            
            with wx.FileDialog( None, style=wx.FD_SAVE, defaultFile = filename ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    with open( dlg.GetPath(), 'wb' ) as f: f.write( body )
                    
                
            
        elif request == 'account':
            
            account = response
            
            account.MakeFresh()
            
            HC.pubsub.pub( 'service_update_db', HC.ServiceUpdate( HC.SERVICE_UPDATE_ACCOUNT, self._service_identifier, account ) )
            
        elif request == 'update':
            
            update = response
            
            HC.pubsub.pub( 'service_update_db', HC.ServiceUpdate( HC.SERVICE_UPDATE_NEXT_BEGIN, self._service_identifier, update.GetNextBegin() ) )
            
        
        return response
        
    
    def GetCookies( self ): return self._connection.GetCookies()
    
    def Post( self, request, **kwargs ): response = self._SendRequest( HC.POST, request, kwargs )
    
class CPRemoteRatingsServiceIdentifiers():
    
    def __init__( self, service_identifiers_to_cp ):
        
        self._service_identifiers_to_cp = service_identifiers_to_cp
        
    
    def GetCP( self, service_identifier ):
        
        if service_identifier in self._service_identifiers_to_cp: return self._service_identifiers_to_cp[ service_identifier ]
        else: return ( None, None )
        
    
    def GetRatingSlice( self, service_identifiers ):
        
        # this doesn't work yet. it should probably use self.GetScore( s_i ) like I think Sort by remote rating does
        
        return frozenset( { self._service_identifiers_to_ratings[ service_identifier ] for service_identifier in service_identifiers if service_identifier in self._service_identifiers_to_ratings } )
        
    
    def GetServiceIdentifiersToCP( self ): return self._service_identifiers_to_cp
    
    def ProcessContentUpdate( self, content_update ):
        
        service_identifier = content_update.GetServiceIdentifier()
        
        if service_identifier in self._service_identifiers_to_cp: ( current, pending ) = self._service_identifiers_to_cp[ service_identifier ]
        else:
            
            ( current, pending ) = ( None, None )
            
            self._service_identifiers_to_cp[ service_identifier ] = ( current, pending )
            
        
        action = content_update.GetAction()
        
        # this may well need work; need to figure out how to set the pending back to None after an upload. rescind seems ugly
        
        if action == HC.CONTENT_UPDATE_ADD:
            
            rating = content_update.GetInfo()
            
            current = rating
            
        elif action == HC.CONTENT_UPDATE_DELETE:
            
            current = None
            
        elif action == HC.CONTENT_UPDATE_RESCIND_PENDING:
            
            pending = None
            
        elif action == HC.CONTENT_UPDATE_DELETE:
            
            rating = content_update.GetInfo()
            
            pending = rating
            
        
    
    def ResetService( self, service_identifier ):
        
        if service_identifier in self._service_identifiers_to_cp:
            
            ( current, pending ) = self._service_identifiers_to_cp[ service_identifier ]
            
            self._service_identifiers_to_cp[ service_identifier ] = ( None, pending )
            
        
    
class Credentials( HC.HydrusYAMLBase ):
    
    yaml_tag = u'!Credentials'
    
    def __init__( self, host, port, access_key = None ):
        
        HC.HydrusYAMLBase.__init__( self )
        
        if host == 'localhost': host = '127.0.0.1'
        
        self._host = host
        self._port = port
        self._access_key = access_key
        
    
    def __eq__( self, other ): return self.__hash__() == other.__hash__()
    
    def __hash__( self ): return ( self._host, self._port, self._access_key ).__hash__()
    
    def __ne__( self, other ): return self.__hash__() != other.__hash__()
    
    def GetAccessKey( self ): return self._access_key
    
    def GetAddress( self ): return ( self._host, self._port )
    
    def GetConnectionString( self ):
        
        connection_string = ''
        
        if self._access_key is not None: connection_string += self._access_key.encode( 'hex' ) + '@'
        
        connection_string += self._host + ':' + str( self._port )
        
        return connection_string
        
    
    def HasAccessKey( self ): return self._access_key is not None and self._access_key is not ''
    
    def SetAccessKey( self, access_key ): self._access_key = access_key
    
class DataCache():
    
    def __init__( self, options, cache_size_key ):
        
        self._options = options
        self._cache_size_key = cache_size_key
        
        self._keys_to_data = {}
        self._keys_fifo = []
        
        self._total_estimated_memory_footprint = 0
        
    
    def Clear( self ):
        
        self._keys_to_data = {}
        self._keys_fifo = []
        
        self._total_estimated_memory_footprint = 0
        
    
    def AddData( self, key, data ):
        
        self._keys_to_data[ key ] = data
        
        self._keys_fifo.append( key )
        
        self._total_estimated_memory_footprint += data.GetEstimatedMemoryFootprint()
        
        while self._total_estimated_memory_footprint > self._options[ self._cache_size_key ]:
            
            deletee_key = self._keys_fifo.pop( 0 )
            
            deletee_data = self._keys_to_data[ deletee_key ]
            
            self._total_estimated_memory_footprint -= deletee_data.GetEstimatedMemoryFootprint()
            
            del self._keys_to_data[ deletee_key ]
            
        
    
    def GetData( self, key ):
        
        self._keys_fifo.remove( key )
        
        self._keys_fifo.append( key )
        
        return self._keys_to_data[ key ]
        
    
    def HasData( self, key ): return key in self._keys_to_data
    
class FileQueryResult():
    
    def __init__( self, file_service_identifier, predicates, media_results ):
        
        self._file_service_identifier = file_service_identifier
        self._predicates = predicates
        self._hashes_to_media_results = { media_result.GetHash() : media_result for media_result in media_results }
        self._hashes = { hash for hash in self._hashes_to_media_results.keys() }
        
        HC.pubsub.sub( self, 'ProcessContentUpdates', 'content_updates_data' )
        HC.pubsub.sub( self, 'ProcessServiceUpdate', 'service_update_data' )
        
    
    def __iter__( self ):
        
        for media_result in self._hashes_to_media_results.values(): yield media_result
        
    
    def __len__( self ): return len( self._hashes )
    
    def _Remove( self, hashes ):
        
        for hash in hashes:
            
            if hash in self._hashes_to_media_results:
                
                del self._hashes_to_media_results[ hash ]
                
            
        
        self._hashes.difference_update( hashes )
        
    
    def AddMediaResult( self, media_result ):
        
        hash = media_result.GetHash()
        
        if hash in self._hashes: return # this is actually important, as sometimes we don't want the media result overwritten
        
        self._hashes_to_media_results[ hash ] = media_result
        
        self._hashes.add( hash )
        
    
    def GetHashes( self ): return self._hashes
    
    def GetMediaResult( self, hash ): return self._hashes_to_media_results[ hash ]
    
    def GetMediaResults( self ): return self._hashes_to_media_results.values()
    
    def ProcessContentUpdates( self, content_updates ):
        
        for content_update in content_updates:
            
            action = content_update.GetAction()
            
            service_identifier = content_update.GetServiceIdentifier()
            
            service_type = service_identifier.GetType()
            
            hashes = content_update.GetHashes()
            
            if action == HC.CONTENT_UPDATE_ARCHIVE:
                
                if 'system:inbox' in self._predicates: self._Remove( hashes )
                
            elif action == HC.CONTENT_UPDATE_INBOX:
                
                if 'system:archive' in self._predicates: self._Remove( hashes )
                
            elif action == HC.CONTENT_UPDATE_DELETE and service_identifier == self._file_service_identifier: self._Remove( hashes )
            
            for hash in self._hashes.intersection( hashes ):
                
                media_result = self._hashes_to_media_results[ hash ]
                
                media_result.ProcessContentUpdate( content_update )
                
            
        
    
    def ProcessServiceUpdate( self, update ):
        
        action = update.GetAction()
        
        service_identifier = update.GetServiceIdentifier()
        
        if action == HC.SERVICE_UPDATE_DELETE_PENDING:
            
            for media_result in self._hashes_to_media_results.values(): media_result.DeletePending( service_identifier )
            
        elif action == HC.SERVICE_UPDATE_RESET:
            
            for media_result in self._hashes_to_media_results.values(): media_result.ResetService( service_identifier )
            
        
    
class FileSearchContext():
    
    def __init__( self, file_service_identifier = HC.LOCAL_FILE_SERVICE_IDENTIFIER, tag_service_identifier = HC.NULL_SERVICE_IDENTIFIER, include_current_tags = True, include_pending_tags = True, predicates = [] ):
        
        self._file_service_identifier = file_service_identifier
        self._tag_service_identifier = tag_service_identifier
        
        self._include_current_tags = include_current_tags
        self._include_pending_tags = include_pending_tags
        
        self._predicates = predicates
        
        system_predicates = [ predicate for predicate in predicates if predicate.GetPredicateType() == HC.PREDICATE_TYPE_SYSTEM ]
        
        self._system_predicates = FileSystemPredicates( system_predicates )
        
        tag_predicates = [ predicate for predicate in predicates if predicate.GetPredicateType() == HC.PREDICATE_TYPE_TAG ]
        
        self._tags_to_include = []
        self._tags_to_exclude = []
        
        for predicate in tag_predicates:
            
            ( operator, tag ) = predicate.GetValue()
            
            if operator == '+': self._tags_to_include.append( tag )
            elif operator == '-': self._tags_to_exclude.append( tag )
            
        
        namespace_predicates = [ predicate for predicate in predicates if predicate.GetPredicateType() == HC.PREDICATE_TYPE_NAMESPACE ]
        
        self._namespaces_to_include = []
        self._namespaces_to_exclude = []
        
        for predicate in namespace_predicates:
            
            ( operator, namespace ) = predicate.GetValue()
            
            if operator == '+': self._namespaces_to_include.append( namespace )
            elif operator == '-': self._namespaces_to_exclude.append( namespace )
            
        
    
    def GetFileServiceIdentifier( self ): return self._file_service_identifier
    def GetNamespacesToExclude( self ): return self._namespaces_to_exclude
    def GetNamespacesToInclude( self ): return self._namespaces_to_include
    def GetPredicates( self ): return self._predicates
    def GetSystemPredicates( self ): return self._system_predicates
    def GetTagServiceIdentifier( self ): return self._tag_service_identifier
    def GetTagsToExclude( self ): return self._tags_to_exclude
    def GetTagsToInclude( self ): return self._tags_to_include
    def IncludeCurrentTags( self ): return self._include_current_tags
    def IncludePendingTags( self ): return self._include_pending_tags

class FileSystemPredicates():
    
    INBOX = 0
    LOCAL = 1
    HASH = 2
    TIMESTAMP = 3
    DURATION = 4
    SIZE = 5
    NUM_TAGS = 6
    WIDTH = 7
    HEIGHT = 8
    RATIO = 9
    REPOSITORIES = 10
    MIME = 11
    
    def __init__( self, system_predicates ):
        
        self._predicates = {}
        
        self._predicates[ self.INBOX ] = []
        self._predicates[ self.LOCAL ] = [] # not using this!
        self._predicates[ self.HASH ] = []
        self._predicates[ self.MIME ] = []
        self._predicates[ self.TIMESTAMP ] = []
        self._predicates[ self.DURATION ] = []
        self._predicates[ self.SIZE ] = []
        self._predicates[ self.NUM_TAGS ] = []
        self._predicates[ self.WIDTH ] = []
        self._predicates[ self.HEIGHT ] = []
        self._predicates[ self.RATIO ] = []
        self._predicates[ self.REPOSITORIES ] = []
        
        self._inbox = False
        self._archive = False
        self._local = False
        self._not_local = False
        
        self._num_tags_zero = False
        self._num_tags_nonzero = False
        
        self._hash = None
        self._min_size = None
        self._size = None
        self._max_size = None
        self._mimes = None
        self._min_timestamp = None
        self._max_timestamp = None
        self._min_width = None
        self._width = None
        self._max_width = None
        self._min_height = None
        self._height = None
        self._max_height = None
        self._min_num_words = None
        self._num_words = None
        self._max_num_words = None
        self._min_duration = None
        self._duration = None
        self._max_duration = None
        
        self._limit = None
        self._similar_to = None
        
        self._file_services_to_include_current = []
        self._file_services_to_include_pending = []
        self._file_services_to_exclude_current = []
        self._file_services_to_exclude_pending = []
        
        self._ratings_predicates = []
        
        isin = lambda a, b: a in b
        startswith = lambda a, b: a.startswith( b )
        lessthan = lambda a, b: a < b
        greaterthan = lambda a, b: a > b
        equals = lambda a, b: a == b
        about_equals = lambda a, b: a < b * 1.15 and a > b * 0.85
        
        for predicate in system_predicates:
            
            ( system_predicate_type, info ) = predicate.GetValue()
            
            if system_predicate_type == HC.SYSTEM_PREDICATE_TYPE_INBOX: self._inbox = True
            if system_predicate_type == HC.SYSTEM_PREDICATE_TYPE_ARCHIVE: self._archive = True
            if system_predicate_type == HC.SYSTEM_PREDICATE_TYPE_LOCAL: self._local = True
            if system_predicate_type == HC.SYSTEM_PREDICATE_TYPE_NOT_LOCAL: self._not_local = True
            
            if system_predicate_type == HC.SYSTEM_PREDICATE_TYPE_HASH:
                
                hash = info
                
                self._hash = hash
                
            
            if system_predicate_type == HC.SYSTEM_PREDICATE_TYPE_AGE:
                
                ( operator, years, months, days ) = info
                
                timestamp = int( time.time() ) - ( ( ( ( ( years * 12 ) + months ) * 30 ) + days ) * 86400 )
                
                # this is backwards because we are talking about age, not timestamp
                
                if operator == '<': self._min_timestamp = timestamp
                elif operator == '>': self._max_timestamp = timestamp
                elif operator == u'\u2248':
                    
                    self._min_timestamp = int( timestamp * 0.85 )
                    self._max_timestamp = int( timestamp * 1.15 )
                    
                
            
            if system_predicate_type == HC.SYSTEM_PREDICATE_TYPE_MIME:
                
                mimes = info
                
                if type( mimes ) == int: mimes = ( mimes, )
                
                self._mimes = mimes
                
            
            if system_predicate_type == HC.SYSTEM_PREDICATE_TYPE_DURATION:
                
                ( operator, duration ) = info
                
                if operator == '<': self._max_duration = duration
                elif operator == '>': self._min_duration = duration
                elif operator == '=': self._duration = duration
                elif operator == u'\u2248':
                    
                    self._min_duration = int( duration * 0.85 )
                    self._max_duration = int( duration * 1.15 )
                    
                
            
            if system_predicate_type == HC.SYSTEM_PREDICATE_TYPE_RATING:
                
                ( service_identifier, operator, value ) = info
                
                self._ratings_predicates.append( ( service_identifier, operator, value ) )
                
            
            if system_predicate_type == HC.SYSTEM_PREDICATE_TYPE_RATIO:
                
                ( operator, ratio ) = info
                
                if operator == '=': self._predicates[ self.RATIO ].append( ( equals, ratio ) )
                elif operator == u'\u2248': self._predicates[ self.RATIO ].append( ( about_equals, ratio ) )
                
            
            if system_predicate_type == HC.SYSTEM_PREDICATE_TYPE_SIZE:
                
                ( operator, size, unit ) = info
                
                size = size * unit
                
                if operator == '<': self._max_size = size
                elif operator == '>': self._min_size = size
                elif operator == '=': self._size = size
                elif operator == u'\u2248':
                    
                    self._min_size = int( size * 0.85 )
                    self._max_size = int( size * 1.15 )
                    
                
            
            if system_predicate_type == HC.SYSTEM_PREDICATE_TYPE_NUM_TAGS:
                
                ( operator, num_tags ) = info
                
                if operator == '<': self._predicates[ self.NUM_TAGS ].append( ( lessthan, num_tags ) )
                elif operator == '>':
                    
                    self._predicates[ self.NUM_TAGS ].append( ( greaterthan, num_tags ) )
                    
                    if num_tags == 0: self._num_tags_nonzero = True
                    
                elif operator == '=':
                    
                    self._predicates[ self.NUM_TAGS ].append( ( equals, num_tags ) )
                    
                    if num_tags == 0: self._num_tags_zero = True
                    
                
            
            if system_predicate_type == HC.SYSTEM_PREDICATE_TYPE_WIDTH:
                
                ( operator, width ) = info
                
                if operator == '<': self._max_width = width
                elif operator == '>': self._min_width = width
                elif operator == '=': self._width = width
                elif operator == u'\u2248':
                    
                    self._min_width = int( width * 0.85 )
                    self._max_width = int( width * 1.15 )
                    
                
            
            if system_predicate_type == HC.SYSTEM_PREDICATE_TYPE_HEIGHT:
                
                ( operator, height ) = info
                
                if operator == '<': self._max_height = height
                elif operator == '>': self._min_height = height
                elif operator == '=': self._height = height
                elif operator == u'\u2248':
                    
                    self._min_height = int( height * 0.85 )
                    self._max_height = int( height * 1.15 )
                    
                
            
            if system_predicate_type == HC.SYSTEM_PREDICATE_TYPE_NUM_WORDS:
                
                ( operator, num_words ) = info
                
                if operator == '<': self._max_num_words = num_words
                elif operator == '>': self._min_num_words = num_words
                elif operator == '=': self._num_words = num_words
                elif operator == u'\u2248':
                    
                    self._min_num_words = int( num_words * 0.85 )
                    self._max_num_words = int( num_words * 1.15 )
                    
                
            
            if system_predicate_type == HC.SYSTEM_PREDICATE_TYPE_LIMIT:
                
                limit = info
                
                self._limit = limit
                
            
            if system_predicate_type == HC.SYSTEM_PREDICATE_TYPE_FILE_SERVICE:
                
                ( operator, current_or_pending, service_identifier ) = info
                
                if operator == True:
                    
                    if current_or_pending == HC.CURRENT: self._file_services_to_include_current.append( service_identifier )
                    else: self._file_services_to_include_pending.append( service_identifier )
                    
                else:
                    
                    if current_or_pending == HC.CURRENT: self._file_services_to_exclude_current.append( service_identifier )
                    else: self._file_services_to_exclude_pending.append( service_identifier )
                    
                
            
            if system_predicate_type == HC.SYSTEM_PREDICATE_TYPE_SIMILAR_TO:
                
                ( hash, max_hamming ) = info
                
                self._similar_to = ( hash, max_hamming )
                
            
        
    
    def CanPreFirstRoundLimit( self ):
        
        if self._limit is None: return False
        
        if len( self._predicates[ self.RATIO ] ) > 0: return False
        
        return self.CanPreSecondRoundLimit()
        
    
    def CanPreSecondRoundLimit( self ):
        
        if self._limit is None: return False
        
        if len( self._predicates[ self.NUM_TAGS ] ) > 0: return False
        
        return True
        
    
    def GetFileServiceInfo( self ): return ( self._file_services_to_include_current, self._file_services_to_include_pending, self._file_services_to_exclude_current, self._file_services_to_exclude_pending )
    
    def GetInfo( self ): return ( self._hash, self._min_size, self._size, self._max_size, self._mimes, self._min_timestamp, self._max_timestamp, self._min_width, self._width, self._max_width, self._min_height, self._height, self._max_height, self._min_num_words, self._num_words, self._max_num_words, self._min_duration, self._duration, self._max_duration )
    
    def GetLimit( self ): return self._limit
    
    def GetNumTagsInfo( self ): return ( self._num_tags_zero, self._num_tags_nonzero )
    
    def GetRatingsPredicates( self ): return self._ratings_predicates
    
    def GetSimilarTo( self ): return self._similar_to
    
    def HasSimilarTo( self ): return self._similar_to is not None
    
    def MustBeArchive( self ): return self._archive
    
    def MustBeInbox( self ): return self._inbox
    
    def MustBeLocal( self ): return self._local
    
    def MustNotBeLocal( self ): return self._not_local
    
    def OkFirstRound( self, width, height ):
        
        if len( self._predicates[ self.RATIO ] ) > 0 and ( width is None or height is None ): return False
        
        if False in ( function( float( width ) / float( height ), arg ) for ( function, arg ) in self._predicates[ self.RATIO ] ): return False
        
        return True
        
    
    def OkSecondRound( self, num_tags ):
        
        if False in ( function( num_tags, arg ) for ( function, arg ) in self._predicates[ self.NUM_TAGS ] ): return False
        
        return True
        
    
class GlobalBMPs():
    
    @staticmethod
    def STATICInitialise():
        
        # these have to be created after the wxApp is instantiated, for silly GDI reasons
        
        GlobalBMPs.bold_bmp = wx.Image( HC.STATIC_DIR + os.path.sep + 'silk icons' + os.path.sep + 'text_bold.png', type=wx.BITMAP_TYPE_PNG ).ConvertToBitmap()
        GlobalBMPs.italic_bmp = wx.Image( HC.STATIC_DIR + os.path.sep + 'silk icons' + os.path.sep + 'text_italic.png', type=wx.BITMAP_TYPE_PNG ).ConvertToBitmap()
        GlobalBMPs.underline_bmp = wx.Image( HC.STATIC_DIR + os.path.sep + 'silk icons' + os.path.sep + 'text_underline.png', type=wx.BITMAP_TYPE_PNG ).ConvertToBitmap()
        
        GlobalBMPs.align_left_bmp = wx.Image( HC.STATIC_DIR + os.path.sep + 'silk icons' + os.path.sep + 'text_align_left.png', type=wx.BITMAP_TYPE_PNG ).ConvertToBitmap()
        GlobalBMPs.align_center_bmp = wx.Image( HC.STATIC_DIR + os.path.sep + 'silk icons' + os.path.sep + 'text_align_center.png', type=wx.BITMAP_TYPE_PNG ).ConvertToBitmap()
        GlobalBMPs.align_right_bmp = wx.Image( HC.STATIC_DIR + os.path.sep + 'silk icons' + os.path.sep + 'text_align_right.png', type=wx.BITMAP_TYPE_PNG ).ConvertToBitmap()
        GlobalBMPs.align_justify_bmp = wx.Image( HC.STATIC_DIR + os.path.sep + 'silk icons' + os.path.sep + 'text_align_justify.png', type=wx.BITMAP_TYPE_PNG ).ConvertToBitmap()
        
        GlobalBMPs.indent_less_bmp = wx.Image( HC.STATIC_DIR + os.path.sep + 'silk icons' + os.path.sep + 'text_indent_remove.png', type=wx.BITMAP_TYPE_PNG ).ConvertToBitmap()
        GlobalBMPs.indent_more_bmp = wx.Image( HC.STATIC_DIR + os.path.sep + 'silk icons' + os.path.sep + 'text_indent.png', type=wx.BITMAP_TYPE_PNG ).ConvertToBitmap()
        
        GlobalBMPs.font_bmp = wx.Image( HC.STATIC_DIR + os.path.sep + 'silk icons' + os.path.sep + 'font.png', type=wx.BITMAP_TYPE_PNG ).ConvertToBitmap()
        GlobalBMPs.colour_bmp = wx.Image( HC.STATIC_DIR + os.path.sep + 'silk icons' + os.path.sep + 'color_swatch.png', type=wx.BITMAP_TYPE_PNG ).ConvertToBitmap()
        
        GlobalBMPs.link_bmp = wx.Image( HC.STATIC_DIR + os.path.sep + 'silk icons' + os.path.sep + 'link.png', type=wx.BITMAP_TYPE_PNG ).ConvertToBitmap()
        GlobalBMPs.link_break_bmp = wx.Image( HC.STATIC_DIR + os.path.sep + 'silk icons' + os.path.sep + 'link_break.png', type=wx.BITMAP_TYPE_PNG ).ConvertToBitmap()
        
        GlobalBMPs.transparent_bmp = wx.Image( HC.STATIC_DIR + os.path.sep + 'transparent.png', type=wx.BITMAP_TYPE_PNG ).ConvertToBitmap()
        GlobalBMPs.downloading_bmp = wx.Image( HC.STATIC_DIR + os.path.sep + 'downloading.png', type=wx.BITMAP_TYPE_PNG ).ConvertToBitmap()
        GlobalBMPs.file_repository_bmp = wx.Image( HC.STATIC_DIR + os.path.sep + 'file_repository_small.png', type=wx.BITMAP_TYPE_PNG ).ConvertToBitmap()
        GlobalBMPs.file_repository_pending_bmp = wx.Image( HC.STATIC_DIR + os.path.sep + 'file_repository_pending_small.png', type=wx.BITMAP_TYPE_PNG ).ConvertToBitmap()
        GlobalBMPs.file_repository_petitioned_bmp = wx.Image( HC.STATIC_DIR + os.path.sep + 'file_repository_petitioned_small.png', type=wx.BITMAP_TYPE_PNG ).ConvertToBitmap()
        GlobalBMPs.inbox_bmp = wx.Image( HC.STATIC_DIR + os.path.sep + 'inbox.png', type=wx.BITMAP_TYPE_PNG ).ConvertToBitmap()
        GlobalBMPs.collection_bmp = wx.Image( HC.STATIC_DIR + os.path.sep + 'collection.png', type=wx.BITMAP_TYPE_PNG ).ConvertToBitmap()
        GlobalBMPs.dump_ok = wx.Image( HC.STATIC_DIR + os.path.sep + 'dump_ok.png', type=wx.BITMAP_TYPE_PNG ).ConvertToBitmap()
        GlobalBMPs.dump_recoverable = wx.Image( HC.STATIC_DIR + os.path.sep + 'dump_recoverable.png', type=wx.BITMAP_TYPE_PNG ).ConvertToBitmap()
        GlobalBMPs.dump_fail = wx.Image( HC.STATIC_DIR + os.path.sep + 'dump_fail.png', type=wx.BITMAP_TYPE_PNG ).ConvertToBitmap()
        
    
class Imageboard( HC.HydrusYAMLBase ):
    
    yaml_tag = u'!Imageboard'
    
    def __init__( self, name, post_url, flood_time, form_fields, restrictions ):
        
        self._name = name
        self._post_url = post_url
        self._flood_time = flood_time
        self._form_fields = form_fields
        self._restrictions = restrictions
        
    
    def IsOkToPost( self, media_result ):
        
        ( hash, inbox, size, mime, timestamp, width, height, duration, num_frames, num_words, tags, file_service_identifiers, local_ratings, remote_ratings ) = media_result.GetInfo()
        
        if RESTRICTION_MIN_RESOLUTION in self._restrictions:
            
            ( min_width, min_height ) = self._restrictions[ RESTRICTION_MIN_RESOLUTION ]
            
            if width < min_width or height < min_height: return False
            
        
        if RESTRICTION_MAX_RESOLUTION in self._restrictions:
            
            ( max_width, max_height ) = self._restrictions[ RESTRICTION_MAX_RESOLUTION ]
            
            if width > max_width or height > max_height: return False
            
        
        if RESTRICTION_MAX_FILE_SIZE in self._restrictions and size > self._restrictions[ RESTRICTION_MAX_FILE_SIZE ]: return False
        
        if RESTRICTION_ALLOWED_MIMES in self._restrictions and mime not in self._restrictions[ RESTRICTION_ALLOWED_MIMES ]: return False
        
        return True
        
    
    def GetBoardInfo( self ): return ( self._post_url, self._flood_time, self._form_fields, self._restrictions )
    
    def GetName( self ): return self._name
    
sqlite3.register_adapter( Imageboard, yaml.safe_dump )

DEFAULT_IMAGEBOARDS = []

fourchan_common_form_fields = []

fourchan_common_form_fields.append( ( 'resto', FIELD_THREAD_ID, 'thread_id', True ) )
fourchan_common_form_fields.append( ( 'email', FIELD_TEXT, '', True ) )
fourchan_common_form_fields.append( ( 'pwd', FIELD_PASSWORD, '', True ) )
fourchan_common_form_fields.append( ( 'recaptcha_response_field', FIELD_VERIFICATION_RECAPTCHA, '6Ldp2bsSAAAAAAJ5uyx_lx34lJeEpTLVkP5k04qc', True ) )
fourchan_common_form_fields.append( ( 'com', FIELD_COMMENT, '', True ) )
fourchan_common_form_fields.append( ( 'upfile', FIELD_FILE, '', True ) )
fourchan_common_form_fields.append( ( 'mode', FIELD_TEXT, 'regist', False ) )

fourchan_typical_form_fields = list( fourchan_common_form_fields )

fourchan_typical_form_fields.insert( 1, ( 'name', FIELD_TEXT, '', True ) )
fourchan_typical_form_fields.insert( 3, ( 'sub', FIELD_TEXT, '', True ) )

fourchan_anon_form_fields = list( fourchan_common_form_fields )

fourchan_anon_form_fields.insert( 1, ( 'name', FIELD_TEXT, '', False ) )
fourchan_anon_form_fields.insert( 3, ( 'sub', FIELD_TEXT, '', False ) )

fourchan_spoiler_form_fields = list( fourchan_typical_form_fields )

fourchan_spoiler_form_fields.append( ( 'spoiler/on', FIELD_CHECKBOX, 'False', True ) )

GJP = [ HC.IMAGE_GIF, HC.IMAGE_PNG, HC.IMAGE_JPEG ]

fourchan_typical_restrictions = { RESTRICTION_MAX_FILE_SIZE : 3145728, RESTRICTION_ALLOWED_MIMES : GJP }

fourchan_imageboards = []

fourchan_imageboards.append( Imageboard( '/3/', 'https://sys.4chan.org/3/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
fourchan_imageboards.append( Imageboard( '/a/', 'https://sys.4chan.org/a/post', 75, fourchan_spoiler_form_fields, fourchan_typical_restrictions ) )
fourchan_imageboards.append( Imageboard( '/adv/', 'https://sys.4chan.org/adv/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
fourchan_imageboards.append( Imageboard( '/an/', 'https://sys.4chan.org/an/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
fourchan_imageboards.append( Imageboard( '/b/', 'https://sys.4chan.org/b/post', 75, fourchan_anon_form_fields, { RESTRICTION_MAX_FILE_SIZE : 2097152, RESTRICTION_ALLOWED_MIMES : GJP } ) )
fourchan_imageboards.append( Imageboard( '/c/', 'https://sys.4chan.org/c/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
fourchan_imageboards.append( Imageboard( '/cgl/', 'https://sys.4chan.org/cgl/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
fourchan_imageboards.append( Imageboard( '/ck/', 'https://sys.4chan.org/ck/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
fourchan_imageboards.append( Imageboard( '/cm/', 'https://sys.4chan.org/cm/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
fourchan_imageboards.append( Imageboard( '/co/', 'https://sys.4chan.org/co/post', 75, fourchan_spoiler_form_fields, fourchan_typical_restrictions ) )
fourchan_imageboards.append( Imageboard( '/d/', 'https://sys.4chan.org/d/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
fourchan_imageboards.append( Imageboard( '/diy/', 'https://sys.4chan.org/diy/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
fourchan_imageboards.append( Imageboard( '/e/', 'https://sys.4chan.org/e/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
fourchan_imageboards.append( Imageboard( '/fa/', 'https://sys.4chan.org/fa/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
fourchan_imageboards.append( Imageboard( '/fit/', 'https://sys.4chan.org/fit/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
fourchan_imageboards.append( Imageboard( '/g/', 'https://sys.4chan.org/g/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
fourchan_imageboards.append( Imageboard( '/gif/', 'https://sys.4chan.org/gif/post', 75, fourchan_typical_form_fields, { RESTRICTION_MAX_FILE_SIZE : 4194304, RESTRICTION_ALLOWED_MIMES : [ HC.IMAGE_GIF ] } ) )
fourchan_imageboards.append( Imageboard( '/h/', 'https://sys.4chan.org/h/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
fourchan_imageboards.append( Imageboard( '/hc/', 'https://sys.4chan.org/hc/post', 75, fourchan_typical_form_fields, { RESTRICTION_MAX_FILE_SIZE : 8388608, RESTRICTION_ALLOWED_MIMES : GJP } ) )
fourchan_imageboards.append( Imageboard( '/hm/', 'https://sys.4chan.org/hm/post', 75, fourchan_typical_form_fields, { RESTRICTION_MAX_FILE_SIZE : 8388608, RESTRICTION_ALLOWED_MIMES : GJP } ) )
fourchan_imageboards.append( Imageboard( '/hr/', 'https://sys.4chan.org/hr/post', 75, fourchan_typical_form_fields, { RESTRICTION_MAX_FILE_SIZE : 8388608, RESTRICTION_ALLOWED_MIMES : GJP, RESTRICTION_MIN_RESOLUTION : ( 700, 700 ), RESTRICTION_MAX_RESOLUTION : ( 10000, 10000 ) } ) )
fourchan_imageboards.append( Imageboard( '/int/', 'https://sys.4chan.org/int/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
fourchan_imageboards.append( Imageboard( '/jp/', 'https://sys.4chan.org/jp/post', 75, fourchan_spoiler_form_fields, fourchan_typical_restrictions ) )
fourchan_imageboards.append( Imageboard( '/k/', 'https://sys.4chan.org/k/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
fourchan_imageboards.append( Imageboard( '/lit/', 'https://sys.4chan.org/lit/post', 75, fourchan_spoiler_form_fields, fourchan_typical_restrictions ) )
fourchan_imageboards.append( Imageboard( '/m/', 'https://sys.4chan.org/m/post', 75, fourchan_spoiler_form_fields, fourchan_typical_restrictions ) )
fourchan_imageboards.append( Imageboard( '/mlp/', 'https://sys.4chan.org/mlp/post', 75, fourchan_spoiler_form_fields, fourchan_typical_restrictions ) )
fourchan_imageboards.append( Imageboard( '/mu/', 'https://sys.4chan.org/mu/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
fourchan_imageboards.append( Imageboard( '/n/', 'https://sys.4chan.org/n/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
fourchan_imageboards.append( Imageboard( '/o/', 'https://sys.4chan.org/o/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
fourchan_imageboards.append( Imageboard( '/p/', 'https://sys.4chan.org/p/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
fourchan_imageboards.append( Imageboard( '/po/', 'https://sys.4chan.org/po/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
fourchan_imageboards.append( Imageboard( '/pol/', 'https://sys.4chan.org/pol/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
fourchan_imageboards.append( Imageboard( '/r9k/', 'https://sys.4chan.org/r9k/post', 75, fourchan_spoiler_form_fields, { RESTRICTION_MAX_FILE_SIZE : 2097152, RESTRICTION_ALLOWED_MIMES : GJP } ) )
fourchan_imageboards.append( Imageboard( '/s/', 'https://sys.4chan.org/s/post', 75, fourchan_typical_form_fields, { RESTRICTION_MAX_FILE_SIZE : 8388608, RESTRICTION_ALLOWED_MIMES : GJP } ) )
fourchan_imageboards.append( Imageboard( '/sci/', 'https://sys.4chan.org/sci/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
fourchan_imageboards.append( Imageboard( '/soc/', 'https://sys.4chan.org/soc/post', 75, fourchan_anon_form_fields, { RESTRICTION_MAX_FILE_SIZE : 2097152, RESTRICTION_ALLOWED_MIMES : GJP } ) )
fourchan_imageboards.append( Imageboard( '/sp/', 'https://sys.4chan.org/sp/post', 75, fourchan_typical_form_fields, { RESTRICTION_MAX_FILE_SIZE : 4194304, RESTRICTION_ALLOWED_MIMES : GJP } ) )
fourchan_imageboards.append( Imageboard( '/tg/', 'https://sys.4chan.org/tg/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
fourchan_imageboards.append( Imageboard( '/toy/', 'https://sys.4chan.org/toy/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
fourchan_imageboards.append( Imageboard( '/trv/', 'https://sys.4chan.org/trv/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
fourchan_imageboards.append( Imageboard( '/tv/', 'https://sys.4chan.org/tv/post', 75, fourchan_spoiler_form_fields, fourchan_typical_restrictions ) )
fourchan_imageboards.append( Imageboard( '/u/', 'https://sys.4chan.org/u/post', 75, fourchan_spoiler_form_fields, fourchan_typical_restrictions ) )
fourchan_imageboards.append( Imageboard( '/v/', 'https://sys.4chan.org/v/post', 75, fourchan_spoiler_form_fields, fourchan_typical_restrictions ) )
fourchan_imageboards.append( Imageboard( '/vg/', 'https://sys.4chan.org/vg/post', 75, fourchan_spoiler_form_fields, fourchan_typical_restrictions ) )
fourchan_imageboards.append( Imageboard( '/w/', 'https://sys.4chan.org/w/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
fourchan_imageboards.append( Imageboard( '/wg/', 'https://sys.4chan.org/wg/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
fourchan_imageboards.append( Imageboard( '/x/', 'https://sys.4chan.org/x/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
fourchan_imageboards.append( Imageboard( '/y/', 'https://sys.4chan.org/y/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
fourchan_imageboards.append( Imageboard( '/vp/', 'https://sys.4chan.org/vp/post', 75, fourchan_spoiler_form_fields, fourchan_typical_restrictions ) )

DEFAULT_IMAGEBOARDS.append( ( '4chan', fourchan_imageboards ) )

class Job( threading.Thread ):
    
    def __init__( self, job_key, name ):
        
        threading.Thread.__init__( self, name = name )
        
        self._job_key = job_key
        
    
    def _NotifyAllDone( self ): pass
    
    def _NotifyPartDone( self, i ): pass
    
    def _NotifyStart( self ): pass
    
    def run( self ):
        
        pass # think about this more
        

class Log():
    
    def __init__( self ):
        
        self._entries = []
        
        HC.pubsub.sub( self, 'AddMessage', 'log_message' )
        HC.pubsub.sub( self, 'AddError', 'log_error' )
        
    
    def __iter__( self ): return self._entries.__iter__()
    
    def AddError( self, source, message ): self._entries.append( ( LOG_ERROR, source, message, time.time() ) )
    
    def AddMessage( self, source, message ): self._entries.append( ( LOG_MESSAGE, source, message, time.time() ) )

class MediaResult():
    
    def __init__( self, tuple ):
        
        # hash, inbox, size, mime, timestamp, width, height, duration, num_frames, num_words, tag_service_identifiers_cdpp, file_service_identifiers_cdpp, local_ratings, remote_ratings
        
        self._tuple = tuple
        
    
    def DeletePending( self, service_identifier ):
        
        service_type = service_identifier.GetType()
        
        ( hash, inbox, size, mime, timestamp, width, height, duration, num_frames, num_words, tag_service_identifiers_cdpp, file_service_identifiers_cdpp, local_ratings, remote_ratings ) = self._tuple
        
        if service_type == HC.TAG_REPOSITORY: tag_service_identifiers_cdpp.DeletePending( service_identifier )
        elif service_type in ( HC.FILE_REPOSITORY, HC.LOCAL_FILE ): file_service_identifiers_cdpp.DeletePending( service_identifier )
        
    
    def GetHash( self ): return self._tuple[0]
    
    def GetDuration( self ): return self._tuple[7]
    
    def GetInbox( self ): return self._tuple[1]
    
    def GetFileServiceIdentifiersCDPP( self ): return self._tuple[11]
    
    def GetMime( self ): return self._tuple[3]
    
    def GetNumFrames( self ): return self._tuple[8]
    
    def GetNumWords( self ): return self._tuple[9]
    
    def GetRatings( self ): return ( self._tuple[12], self._tuple[13] )
    
    def GetResolution( self ): return ( self._tuple[5], self._tuple[6] )
    
    def GetSize( self ): return self._tuple[2]
    
    def GetTags( self ): return self._tuple[10]
    
    def GetTimestamp( self ): return self._tuple[4]
    
    def GetInfo( self ): return self._tuple
    
    def ProcessContentUpdate( self, content_update ):
        
        ( hash, inbox, size, mime, timestamp, width, height, duration, num_frames, num_words, tag_service_identifiers_cdpp, file_service_identifiers_cdpp, local_ratings, remote_ratings ) = self._tuple
        
        service_identifier = content_update.GetServiceIdentifier()
        
        service_type = service_identifier.GetType()
        
        if service_type in ( HC.LOCAL_TAG, HC.TAG_REPOSITORY ): tag_service_identifiers_cdpp.ProcessContentUpdate( content_update )
        elif service_type in ( HC.FILE_REPOSITORY, HC.LOCAL_FILE ):
            
            if service_type == HC.LOCAL_FILE:
                
                action = content_update.GetAction()
                
                if action == HC.CONTENT_UPDATE_ADD and not file_service_identifiers_cdpp.HasLocal(): inbox = True
                elif action == HC.CONTENT_UPDATE_ARCHIVE: inbox = False
                elif action == HC.CONTENT_UPDATE_INBOX: inbox = True
                elif action == HC.CONTENT_UPDATE_DELETE: inbox = False
                
                self._tuple = ( hash, inbox, size, mime, timestamp, width, height, duration, num_frames, num_words, tag_service_identifiers_cdpp, file_service_identifiers_cdpp, local_ratings, remote_ratings )
                
            
            file_service_identifiers_cdpp.ProcessContentUpdate( content_update )
            
        elif service_type in HC.RATINGS_SERVICES:
            
            if service_type in ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ): local_ratings.ProcessContentUpdate( content_update )
            else: remote_ratings.ProcessContentUpdate( content_update )
            
        
    
    def ResetService( self, service_identifier ):
        
        service_type = service_identifier.GetType()
        
        ( hash, inbox, size, mime, timestamp, width, height, duration, num_frames, num_words, tag_service_identifiers_cdpp, file_service_identifiers_cdpp, local_ratings, remote_ratings ) = self._tuple
        
        if service_type == HC.TAG_REPOSITORY: tag_service_identifiers_cdpp.ResetService( service_identifier )
        elif service_type == HC.FILE_REPOSITORY: file_service_identifiers_cdpp.ResetService( service_identifier )
        
    
class MenuEventIdToActionCache():
    
    def __init__( self ):
        
        self._ids_to_actions = {}
        self._actions_to_ids = {}
        
    
    def GetAction( self, id ):
        
        if id in self._ids_to_actions: return self._ids_to_actions[ id ]
        else: return None
        
    
    def GetId( self, command, data = None ):
        
        action = ( command, data )
        
        if action not in self._actions_to_ids:
            
            id = wx.NewId()
            
            self._ids_to_actions[ id ] = action
            self._actions_to_ids[ action ] = id
            
        
        return self._actions_to_ids[ action ]
        
    
MENU_EVENT_ID_TO_ACTION_CACHE = MenuEventIdToActionCache()

class RenderedImageCache():
    
    def __init__( self, db, options, type ):
        
        self._options = options
        self._type = type
        
        if self._type == 'fullscreen': self._data_cache = DataCache( options, 'fullscreen_cache_size' )
        elif self._type == 'preview': self._data_cache = DataCache( options, 'preview_cache_size' )
        
        self._total_estimated_memory_footprint = 0
        
        self._keys_being_rendered = {}
        
        HC.pubsub.sub( self, 'FinishedRendering', 'finished_rendering' )
        
    
    def Clear( self ): self._data_cache.Clear()
    
    def GetImage( self, hash, resolution ):
        
        try:
            
            key = ( hash, resolution )
            
            if self._data_cache.HasData( key ): return self._data_cache.GetData( key )
            elif key in self._keys_being_rendered: return self._keys_being_rendered[ key ]
            else:
                
                file = wx.GetApp().Read( 'file', hash )
                
                image_container = HydrusImageHandling.RenderImageFromFile( file, hash, target_resolution = resolution, synchronous = False )
                
                self._keys_being_rendered[ key ] = image_container
                
                return image_container
                
            
        except:
            
            print( traceback.format_exc() )
            
            raise
            
        
    
    def HasImage( self, hash, resolution ):
        
        key = ( hash, resolution )
        
        return self._data_cache.HasData( key ) or key in self._keys_being_rendered
        
    
    def FinishedRendering( self, key ):
        
        if key in self._keys_being_rendered:
            
            image_container = self._keys_being_rendered[ key ]
            
            del self._keys_being_rendered[ key ]
            
            self._data_cache.AddData( key, image_container )
            
        
    
class Service( HC.HydrusYAMLBase ):
    
    yaml_tag = u'!Service'
    
    def __init__( self, service_identifier ):
        
        HC.HydrusYAMLBase.__init__( self )
        
        self._service_identifier = service_identifier
        
    
    def GetExtraInfo( self ): return None
    
    def GetServiceIdentifier( self ): return self._service_identifier
    
class ServiceLocalRatingLike( Service ):
    
    yaml_tag = u'!ServiceLocalRatingLike'
    
    def __init__( self, service_identifier, like, dislike ):
        
        Service.__init__( self, service_identifier )
        
        self._like = like
        self._dislike = dislike
        
    
    def GetExtraInfo( self ): return ( self._like, self._dislike )
    
class ServiceLocalRatingNumerical( Service ):
    
    yaml_tag = u'!ServiceLocalRatingNumerical'
    
    def __init__( self, service_identifier, lower, upper ):
        
        Service.__init__( self, service_identifier )
        
        self._lower = lower
        self._upper = upper
        
    
    def GetExtraInfo( self ): return ( self._lower, self._upper )
    
class ServiceRemote( Service ):
    
    yaml_tag = u'!ServiceRemote'
    
    def __init__( self, service_identifier, credentials, last_error ):
        
        Service.__init__( self, service_identifier )
        
        self._credentials = credentials
        self._last_error = last_error
        
        HC.pubsub.sub( self, 'ProcessServiceUpdate', 'service_update_data' )
        
    
    def GetConnection( self ): return ConnectionToService( self._service_identifier, self._credentials )
    
    def GetCredentials( self ): return self._credentials
    
    def GetRecentErrorPending( self ): return HC.ConvertTimestampToPrettyPending( self._last_error + 600 )
    
    def HasRecentError( self ): return self._last_error + 600 > int( time.time() )
    
    def SetCredentials( self, credentials ): self._credentials = credentials
    
    def ProcessServiceUpdate( self, update ):
        
        if update.GetServiceIdentifier() == self._service_identifier:
            
            action = update.GetAction()
            
            if action == HC.SERVICE_UPDATE_ERROR: self._last_error = int( time.time() )
            elif action == HC.SERVICE_UPDATE_RESET:
                
                self._service_identifier = update.GetInfo()
                
                self._last_error = 0
                
            
        
    
class ServiceRemoteRestricted( ServiceRemote ):
    
    yaml_tag = u'!ServiceRemoteRestricted'
    
    def __init__( self, service_identifier, credentials, last_error, account ):
        
        ServiceRemote.__init__( self, service_identifier, credentials, last_error )
        
        self._account = account
        
    
    def CanDownload( self ): return self._account.HasPermission( HC.GET_DATA ) and not self.HasRecentError()
    
    def CanUpload( self ): return self._account.HasPermission( HC.POST_DATA ) and not self.HasRecentError()
    
    def GetAccount( self ): return self._account
    
    def GetRecentErrorPending( self ):
        
        if self._account.HasPermission( HC.GENERAL_ADMIN ): return HC.ConvertTimestampToPrettyPending( self._last_error + 600 )
        else: return HC.ConvertTimestampToPrettyPending( self._last_error + 3600 * 4 )
        
    
    def HasRecentError( self ):
        
        if self._account.HasPermission( HC.GENERAL_ADMIN ): return self._last_error + 600 > int( time.time() )
        else: return self._last_error + 3600 * 4 > int( time.time() )
        
    
    def IsInitialised( self ):
        
        service_type = self._service_identifier.GetType()
        
        if service_type == HC.SERVER_ADMIN: return self._credentials.HasAccessKey()
        else: return True
        
    
    def ProcessServiceUpdate( self, update ):
        
        ServiceRemote.ProcessServiceUpdate( self, update )
        
        if update.GetServiceIdentifier() == self.GetServiceIdentifier():
            
            action = update.GetAction()
            
            if action == HC.SERVICE_UPDATE_ACCOUNT:
                
                account = update.GetInfo()
                
                self._account = account
                self._last_error = 0
                
            elif action == HC.SERVICE_UPDATE_REQUEST_MADE:
                
                num_bytes = update.GetInfo()
                
                self._account.RequestMade( num_bytes )
                
            
        
    
class ServiceRemoteRestrictedRepository( ServiceRemoteRestricted ):
    
    yaml_tag = u'!ServiceRemoteRestrictedRepository'
    
    def __init__( self, service_identifier, credentials, last_error, account, first_begin, next_begin ):
        
        ServiceRemoteRestricted.__init__( self, service_identifier, credentials, last_error, account )
        
        self._first_begin = first_begin
        self._next_begin = next_begin
        
    
    def CanUpdate( self ): return self._account.HasPermission( HC.GET_DATA ) and not self.HasRecentError() and self.HasUpdateDue()
    
    def GetFirstBegin( self ): return self._first_begin
    
    def GetNextBegin( self ): return self._next_begin
    
    def GetUpdateStatus( self ):
        
        if not self._account.HasPermission( HC.GET_DATA ): return 'updates on hold'
        else:
            
            if self.CanUpdate(): return HC.ConvertTimestampToPrettySync( self._next_begin )
            else:
                
                if self.HasRecentError(): return 'due to a previous error, update is delayed - next check ' + self.GetRecentErrorPending()
                else: return 'fully synchronised - next update ' + HC.ConvertTimestampToPrettyPending( self._next_begin + HC.UPDATE_DURATION + 1800 )
                
            
        
    
    def HasUpdateDue( self ): return self._next_begin + HC.UPDATE_DURATION + 1800 < int( time.time() )
    
    def SetNextBegin( self, next_begin ):
        
        if next_begin > self._next_begin:
            
            if self._first_begin == 0: self._first_begin = next_begin
            
            self._next_begin = next_begin
            
        
    
    def ProcessServiceUpdate( self, update ):
        
        ServiceRemoteRestricted.ProcessServiceUpdate( self, update )
        
        if update.GetServiceIdentifier() == self.GetServiceIdentifier():
            
            action = update.GetAction()
            
            if action == HC.SERVICE_UPDATE_NEXT_BEGIN:
                
                next_begin = update.GetInfo()
                
                self.SetNextBegin( next_begin )
                
            elif action == HC.SERVICE_UPDATE_RESET:
                
                self._service_identifier = update.GetInfo()
                
                self._first_begin = 0
                self._next_begin = 0
                
            
        
    
class ServiceRemoteRestrictedRepositoryRatingLike( ServiceRemoteRestrictedRepository ):
    
    yaml_tag = u'!ServiceRemoteRestrictedRepositoryRatingLike'
    
    def __init__( self, service_identifier, credentials, last_error, account, first_begin, next_begin, like, dislike ):
        
        ServiceRemoteRestricted.__init__( self, service_identifier, credentials, last_error, account, first_begin, next_begin )
        
        self._like = like
        self._dislike = dislike
        
    
    def GetExtraInfo( self ): return ( self._like, self._dislike )
    
class ServiceRemoteRestrictedRepositoryRatingNumerical( ServiceRemoteRestrictedRepository ):
    
    yaml_tag = u'!ServiceRemoteRestrictedRepositoryRatingNumerical'
    
    def __init__( self, service_identifier, credentials, last_error, account, first_begin, next_begin, lower, upper ):
        
        ServiceRemoteRestricted.__init__( self, service_identifier, credentials, last_error, account, first_begin, next_begin )
        
        self._lower = lower
        self._upper = upper
        
    
    def GetExtraInfo( self ): return ( self._lower, self._upper )
    
class ServiceRemoteRestrictedDepot( ServiceRemoteRestricted ):
    
    yaml_tag = u'!ServiceRemoteRestrictedDepot'
    
    def __init__( self, service_identifier, credentials, last_error, account, last_check, check_period ):
        
        ServiceRemoteRestricted.__init__( self, service_identifier, credentials, last_error, account )
        
        self._last_check = last_check
        self._check_period = check_period
        
    
    def CanCheck( self ): return self._account.HasPermission( HC.GET_DATA ) and not self.HasRecentError() and self.HasCheckDue()
    
    def GetExtraInfo( self ): return self._check_period
    
    def GetLastCheck( self ): return self._last_check
    
    def GetCheckStatus( self ):
        
        if not self._account.HasPermission( HC.GET_DATA ): return 'checks on hold'
        else:
            
            if self.CanCheck(): return HC.ConvertTimestampToPrettySync( self._last_check + self._check_period )
            else:
                
                if self.HasRecentError(): return 'due to a previous error, check is delayed - next attempt ' + self.GetRecentErrorPending()
                else: return 'next check ' + HC.ConvertTimestampToPrettyPending( self._last_check + self._check_period )
                
            
        
    
    def HasCheckDue( self ): return self._last_check + self._check_period + 5 < int( time.time() )
    
    def ProcessServiceUpdate( self, update ):
        
        ServiceRemoteRestricted.ProcessServiceUpdate( self, update )
        
        if update.GetServiceIdentifier() == self.GetServiceIdentifier():
            
            action = update.GetAction()
            
            if action == HC.SERVICE_UPDATE_LAST_CHECK:
                
                last_check = update.GetInfo()
                
                self._last_check = last_check
                
            elif action == HC.SERVICE_UPDATE_RESET:
                
                self._service_identifier = update.GetInfo()
                
                self._last_check = 0
                
            
        
    
class ServiceRemoteRestrictedDepotMessage( ServiceRemoteRestrictedDepot ):
    
    yaml_tag = u'!ServiceRemoteRestrictedDepotMessage'
    
    def __init__( self, service_identifier, credentials, last_error, account, last_check, check_period, contact, private_key, receive_anon ):
        
        ServiceRemoteRestrictedDepot.__init__( self, service_identifier, credentials, last_error, account, last_check, check_period )
        
        self._contact = contact
        self._private_key = private_key
        self._receive_anon = receive_anon
        
    
    def GetContact( self ): return self._contact
    
    def GetExtraInfo( self ): return ( self._contact.GetName(), self._check_period, self._private_key, self._receive_anon )
    
    def GetPrivateKey( self ): return self._private_key
    
    def ReceivesAnon( self ): return self._receive_anon
    
    def Decrypt( self, encrypted_message ): return HydrusMessageHandling.UnpackageDeliveredMessage( encrypted_message, self._private_key )
    
class ThumbnailCache():
    
    def __init__( self, db, options ):
        
        self._db = db
        
        self._options = options
        
        self._data_cache = DataCache( options, 'thumbnail_cache_size' )
        
        with open( HC.STATIC_DIR + os.path.sep + 'hydrus.png', 'rb' ) as f: self._not_found_file = f.read()
        with open( HC.STATIC_DIR + os.path.sep + 'flash.png', 'rb' ) as f: self._flash_file = f.read()
        with open( HC.STATIC_DIR + os.path.sep + 'flv.png', 'rb' ) as f: self._flv_file = f.read()
        with open( HC.STATIC_DIR + os.path.sep + 'pdf.png', 'rb' ) as f: self._pdf_file = f.read()
        
        self._not_found = HydrusImageHandling.GenerateHydrusBitmapFromFile( HydrusImageHandling.GenerateThumbnailFileFromFile( self._not_found_file, self._options[ 'thumbnail_dimensions' ] ) )
        self._flash = HydrusImageHandling.GenerateHydrusBitmapFromFile( HydrusImageHandling.GenerateThumbnailFileFromFile( self._flash_file, self._options[ 'thumbnail_dimensions' ] ) )
        self._flv = HydrusImageHandling.GenerateHydrusBitmapFromFile( HydrusImageHandling.GenerateThumbnailFileFromFile( self._flv_file, self._options[ 'thumbnail_dimensions' ] ) )
        self._pdf = HydrusImageHandling.GenerateHydrusBitmapFromFile( HydrusImageHandling.GenerateThumbnailFileFromFile( self._pdf_file, self._options[ 'thumbnail_dimensions' ] ) )
        
        HC.pubsub.sub( self, 'Clear', 'thumbnail_resize' )
        
    
    def Clear( self ):
        
        self._data_cache.Clear()
        
        self._not_found = HydrusImageHandling.GenerateHydrusBitmapFromFile( HydrusImageHandling.GenerateThumbnailFileFromFile( self._not_found_file, self._options[ 'thumbnail_dimensions' ] ) )
        self._flash = HydrusImageHandling.GenerateHydrusBitmapFromFile( HydrusImageHandling.GenerateThumbnailFileFromFile( self._flash_file, self._options[ 'thumbnail_dimensions' ] ) )
        self._flv = HydrusImageHandling.GenerateHydrusBitmapFromFile( HydrusImageHandling.GenerateThumbnailFileFromFile( self._flv_file, self._options[ 'thumbnail_dimensions' ] ) )
        self._pdf = HydrusImageHandling.GenerateHydrusBitmapFromFile( HydrusImageHandling.GenerateThumbnailFileFromFile( self._pdf_file, self._options[ 'thumbnail_dimensions' ] ) )
        
    
    def GetFlashThumbnail( self ): return self._flash
    def GetFLVThumbnail( self ): return self._flv
    def GetNotFoundThumbnail( self ): return self._not_found
    def GetPDFThumbnail( self ): return self._pdf
    
    def GetThumbnail( self, service_identifier, hash ):
        
        service_identifier_and_hash = ( service_identifier, hash )
        
        if not self._data_cache.HasData( service_identifier_and_hash ):
            
            try: hydrus_bitmap = HydrusImageHandling.GenerateHydrusBitmapFromFile( wx.GetApp().Read( 'thumbnail', hash ) )
            except:
                print( traceback.format_exc() )
                return self._not_found
            
            self._data_cache.AddData( service_identifier_and_hash, hydrus_bitmap )
            
        
        return self._data_cache.GetData( service_identifier_and_hash )
        
    
    def PrefetchThumbnails( self, hashes ): self._db.PrefetchThumbnails( hashes )
    
class VPTreeNode():
    
    def __init__( self, phashes ):
        
        ghd = HydrusImageHandling.GetHammingDistance
        
        if len( phashes ) == 1:
            
            ( self._phash, ) = phashes
            self._radius = 0
            
            inner_phashes = []
            outer_phashes = []
            
        else:
            
            # we want to choose a good node.
            # a good node is one that doesn't overlap with other circles much
            
            # get a random sample with big lists, to keep cpu costs down
            if len( phashes ) > 50: phashes_sample = random.sample( phashes, 50 )
            else: phashes_sample = phashes
            
            all_nodes_comparisons = { phash1 : [ ( ghd( phash1, phash2 ), phash2 ) for phash2 in phashes_sample if phash2 != phash1 ] for phash1 in phashes_sample }
            
            for comparisons in all_nodes_comparisons.values(): comparisons.sort()
            
            # the median of the sorted hamming distances makes a decent radius
            
            all_nodes_radii = [ ( comparisons[ len( comparisons ) / 2 ], phash ) for ( phash, comparisons ) in all_nodes_comparisons.items() ]
            
            all_nodes_radii.sort()
            
            # let's make our node the phash with the smallest predicted radius
            
            ( ( predicted_radius, whatever ), self._phash ) = all_nodes_radii[ 0 ]
            
            if len( phashes ) > 50:
                
                my_hammings = [ ( ghd( self._phash, phash ), phash ) for phash in phashes if phash != self._phash ]
                
                my_hammings.sort()
                
            else: my_hammings = all_nodes_comparisons[ self._phash ]
            
            median_index = len( my_hammings ) / 2
            
            ( self._radius, whatever ) = my_hammings[ median_index ]
            
            # lets bump our index up until we actually get outside the radius
            while median_index + 1 < len( my_hammings ) and my_hammings[ median_index + 1 ][0] == self._radius: median_index += 1
            
            # now separate my phashes into inside and outside that radius
            
            inner_phashes = [ phash for ( hamming, phash ) in my_hammings[ : median_index + 1 ] ]
            outer_phashes = [ phash for ( hamming, phash ) in my_hammings[ median_index + 1 : ] ]
            
        
        if len( inner_phashes ) == 0: self._inner_node = VPTreeNodeEmpty()
        else: self._inner_node = VPTreeNode( inner_phashes )
        
        if len( outer_phashes ) == 0: self._outer_node = VPTreeNodeEmpty()
        else: self._outer_node = VPTreeNode( outer_phashes )
        
    
    def __len__( self ): return len( self._inner_node ) + len( self._outer_node ) + 1
    
    def GetMatches( self, phash, max_hamming ):
        
        hamming_distance_to_me = HydrusImageHandling.GetHammingDistance( self._phash, phash )
        
        matches = []
        
        if hamming_distance_to_me <= max_hamming: matches.append( self._phash )
        
        if hamming_distance_to_me <= ( self._radius + max_hamming ): matches.extend( self._inner_node.GetMatches( phash, max_hamming ) ) # i.e. result could be in inner
        if hamming_distance_to_me >= ( self._radius - max_hamming ): matches.extend( self._outer_node.GetMatches( phash, max_hamming ) ) # i.e. result could be in outer
        
        return matches
        
    
class VPTreeNodeEmpty():
    
    def __init__( self ): pass
    
    def __len__( self ): return 0
    
    def GetMatches( self, phash, max_hamming ): return []
    
class WebSessionManagerClient():
    
    def __init__( self ):
        
        existing_sessions = wx.GetApp().Read( 'web_sessions' )
        
        self._sessions = { name : ( cookies, expiry ) for ( name, cookies, expiry ) in existing_sessions }
        
        self._lock = threading.Lock()
        
    
    def GetCookies( self, name ):
        
        now = int( time.time() )
        
        with self._lock:
            
            if name in self._sessions:
                
                ( cookies, expiry ) = self._sessions[ name ]
                
                if now + 300 > expiry: del self._sessions[ name ]
                else: return cookies
                
            
            # name not found, or expired
            
            if name == 'hentai foundry':
                
                connection = HC.AdvancedHTTPConnection( url = 'http://www.hentai-foundry.com', accept_cookies = True )
                
                # this establishes the php session cookie, the csrf cookie, and tells hf that we are 18 years of age
                connection.request( 'GET', '/?enterAgree=1' )
                
                cookies = connection.GetCookies()
                
                expiry = now + 90 * 60
                
            elif name == 'pixiv':
                
                ( id, password ) = wx.GetApp().Read( 'pixiv_account' )
                
                if id == '' and password == '':
                    
                    raise Exception( 'You need to set up your pixiv credentials in services->manage pixiv account.' )
                    
                
                connection = HC.AdvancedHTTPConnection( url = 'http://www.pixiv.net', accept_cookies = True )
                
                form_fields = {}
                
                form_fields[ 'mode' ] = 'login'
                form_fields[ 'pixiv_id' ] = id
                form_fields[ 'pass' ] = password
                form_fields[ 'skip' ] = '1'
                
                body = urllib.urlencode( form_fields )
                
                headers = {}
                headers[ 'Content-Type' ] = 'application/x-www-form-urlencoded'
                
                # this logs in and establishes the php session cookie
                response = connection.request( 'POST', '/login.php', headers = headers, body = body, follow_redirects = False )
                
                cookies = connection.GetCookies()
                
                # _ only given to logged in php sessions
                if 'PHPSESSID' not in cookies or '_' not in cookies[ 'PHPSESSID' ]: raise Exception( 'Login credentials not accepted!' )
                
                expiry = now + 30 * 86400
                
            
            self._sessions[ name ] = ( cookies, expiry )
            
            wx.GetApp().Write( 'web_session', name, cookies, expiry )
            
            return cookies
            
        
    