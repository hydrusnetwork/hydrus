import collections
import dircache
import gc
import hashlib
import httplib
import HydrusConstants as HC
import HydrusEncryption
import HydrusExceptions
import HydrusFileHandling
import HydrusImageHandling
import HydrusMessageHandling
import HydrusNetworking
import HydrusTags
import itertools
import multipart
import os
import Queue
import random
import sqlite3
import sys
import threading
import time
import threading
import traceback
import urllib
import yaml
import wx
import zlib

ID_NULL = wx.NewId()

CAN_HIDE_MOUSE = True

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

# default options

CLIENT_DEFAULT_OPTIONS = {}

CLIENT_DEFAULT_OPTIONS[ 'play_dumper_noises' ] = True
CLIENT_DEFAULT_OPTIONS[ 'default_sort' ] = 0
CLIENT_DEFAULT_OPTIONS[ 'default_collect' ] = None
CLIENT_DEFAULT_OPTIONS[ 'export_path' ] = 'export'
CLIENT_DEFAULT_OPTIONS[ 'hpos' ] = 400
CLIENT_DEFAULT_OPTIONS[ 'vpos' ] = 700
CLIENT_DEFAULT_OPTIONS[ 'exclude_deleted_files' ] = False
CLIENT_DEFAULT_OPTIONS[ 'thumbnail_cache_size' ] = 100 * 1048576
CLIENT_DEFAULT_OPTIONS[ 'preview_cache_size' ] = 25 * 1048576
CLIENT_DEFAULT_OPTIONS[ 'fullscreen_cache_size' ] = 200 * 1048576
CLIENT_DEFAULT_OPTIONS[ 'thumbnail_dimensions' ] = [ 150, 125 ]
CLIENT_DEFAULT_OPTIONS[ 'password' ] = None
CLIENT_DEFAULT_OPTIONS[ 'num_autocomplete_chars' ] = 2
CLIENT_DEFAULT_OPTIONS[ 'gui_capitalisation' ] = False
CLIENT_DEFAULT_OPTIONS[ 'default_gui_session' ] = 'just a blank page'

system_predicates = {}

system_predicates[ 'age' ] = ( 0, 0, 0, 7 )
system_predicates[ 'duration' ] = ( 3, 0, 0 )
system_predicates[ 'height' ] = ( 1, 1200 )
system_predicates[ 'limit' ] = 600
system_predicates[ 'mime' ] = ( 0, 0 )
system_predicates[ 'num_tags' ] = ( 0, 4 )
system_predicates[ 'local_rating_numerical' ] = ( 0, 3 )
system_predicates[ 'local_rating_like' ] = 0
system_predicates[ 'ratio' ] = ( 0, 16, 9 )
system_predicates[ 'size' ] = ( 0, 200, 1 )
system_predicates[ 'width' ] = ( 1, 1920 )
system_predicates[ 'num_words' ] = ( 0, 30000 )

CLIENT_DEFAULT_OPTIONS[ 'file_system_predicates' ] = system_predicates

default_namespace_colours = {}

default_namespace_colours[ 'system' ] = ( 153, 101, 21 )
default_namespace_colours[ 'creator' ] = ( 170, 0, 0 )
default_namespace_colours[ 'character' ] = ( 0, 170, 0 )
default_namespace_colours[ 'series' ] = ( 170, 0, 170 )
default_namespace_colours[ None ] = ( 114, 160, 193 )
default_namespace_colours[ '' ] = ( 0, 111, 250 )

CLIENT_DEFAULT_OPTIONS[ 'namespace_colours' ] = default_namespace_colours

default_sort_by_choices = []

default_sort_by_choices.append( ( 'namespaces', [ 'series', 'creator', 'title', 'volume', 'chapter', 'page' ] ) )
default_sort_by_choices.append( ( 'namespaces', [ 'creator', 'series', 'title', 'volume', 'chapter', 'page' ] ) )

CLIENT_DEFAULT_OPTIONS[ 'sort_by' ] = default_sort_by_choices
CLIENT_DEFAULT_OPTIONS[ 'show_all_tags_in_autocomplete' ] = True
CLIENT_DEFAULT_OPTIONS[ 'fullscreen_borderless' ] = True

shortcuts = {}

shortcuts[ wx.ACCEL_NORMAL ] = {}
shortcuts[ wx.ACCEL_CTRL ] = {}
shortcuts[ wx.ACCEL_ALT ] = {}
shortcuts[ wx.ACCEL_SHIFT ] = {}

shortcuts[ wx.ACCEL_NORMAL ][ wx.WXK_F3 ] = 'manage_tags'
shortcuts[ wx.ACCEL_NORMAL ][ wx.WXK_F4 ] = 'manage_ratings'
shortcuts[ wx.ACCEL_NORMAL ][ wx.WXK_F5 ] = 'refresh'
shortcuts[ wx.ACCEL_NORMAL ][ wx.WXK_F7 ] = 'archive'
shortcuts[ wx.ACCEL_NORMAL ][ wx.WXK_F11 ] = 'ratings_filter'
shortcuts[ wx.ACCEL_NORMAL ][ wx.WXK_F12 ] = 'filter'
shortcuts[ wx.ACCEL_NORMAL ][ wx.WXK_F9 ] = 'new_page'
shortcuts[ wx.ACCEL_NORMAL ][ ord( 'F' ) ] = 'fullscreen_switch'
shortcuts[ wx.ACCEL_SHIFT ][ wx.WXK_F7 ] = 'inbox'
shortcuts[ wx.ACCEL_CTRL ][ ord( 'B' ) ] = 'frame_back'
shortcuts[ wx.ACCEL_CTRL ][ ord( 'N' ) ] = 'frame_next'
shortcuts[ wx.ACCEL_CTRL ][ ord( 'T' ) ] = 'new_page'
shortcuts[ wx.ACCEL_CTRL ][ ord( 'W' ) ] = 'close_page'
shortcuts[ wx.ACCEL_CTRL ][ ord( 'R' ) ] = 'show_hide_splitters'
shortcuts[ wx.ACCEL_CTRL ][ ord( 'S' ) ] = 'set_search_focus'
shortcuts[ wx.ACCEL_CTRL ][ ord( 'M' ) ] = 'set_media_focus'
shortcuts[ wx.ACCEL_CTRL ][ ord( 'I' ) ] = 'synchronised_wait_switch'
shortcuts[ wx.ACCEL_CTRL ][ ord( 'Z' ) ] = 'undo'
shortcuts[ wx.ACCEL_CTRL ][ ord( 'Y' ) ] = 'redo'

shortcuts[ wx.ACCEL_CTRL ][ wx.WXK_UP ] = 'previous'
shortcuts[ wx.ACCEL_CTRL ][ wx.WXK_LEFT ] = 'previous'
shortcuts[ wx.ACCEL_CTRL ][ wx.WXK_NUMPAD_UP ] = 'previous'
shortcuts[ wx.ACCEL_CTRL ][ wx.WXK_NUMPAD_LEFT ] = 'previous'
shortcuts[ wx.ACCEL_CTRL ][ wx.WXK_PAGEUP ] = 'previous'
shortcuts[ wx.ACCEL_CTRL ][ wx.WXK_NUMPAD_PAGEUP ] = 'previous'
shortcuts[ wx.ACCEL_CTRL ][ wx.WXK_DOWN ] = 'next'
shortcuts[ wx.ACCEL_CTRL ][ wx.WXK_RIGHT ] = 'next'
shortcuts[ wx.ACCEL_CTRL ][ wx.WXK_NUMPAD_DOWN ] = 'next'
shortcuts[ wx.ACCEL_CTRL ][ wx.WXK_NUMPAD_RIGHT ] = 'next'
shortcuts[ wx.ACCEL_CTRL ][ wx.WXK_PAGEDOWN ] = 'next'
shortcuts[ wx.ACCEL_CTRL ][ wx.WXK_NUMPAD_PAGEDOWN ] = 'next'
shortcuts[ wx.ACCEL_CTRL ][ wx.WXK_HOME ] = 'first'
shortcuts[ wx.ACCEL_CTRL ][ wx.WXK_NUMPAD_HOME ] = 'first'
shortcuts[ wx.ACCEL_CTRL ][ wx.WXK_END ] = 'last'
shortcuts[ wx.ACCEL_CTRL ][ wx.WXK_NUMPAD_END ] = 'last'

shortcuts[ wx.ACCEL_SHIFT ][ wx.WXK_UP ] = 'pan_up'
shortcuts[ wx.ACCEL_SHIFT ][ wx.WXK_DOWN ] = 'pan_down'
shortcuts[ wx.ACCEL_SHIFT ][ wx.WXK_LEFT ] = 'pan_left'
shortcuts[ wx.ACCEL_SHIFT ][ wx.WXK_RIGHT ] = 'pan_right'

CLIENT_DEFAULT_OPTIONS[ 'shortcuts' ] = shortcuts

CLIENT_DEFAULT_OPTIONS[ 'confirm_client_exit' ] = False

CLIENT_DEFAULT_OPTIONS[ 'default_tag_repository' ] = HC.LOCAL_TAG_SERVICE_IDENTIFIER
CLIENT_DEFAULT_OPTIONS[ 'default_tag_sort' ] = SORT_BY_LEXICOGRAPHIC_ASC

CLIENT_DEFAULT_OPTIONS[ 'pause_export_folders_sync' ] = False
CLIENT_DEFAULT_OPTIONS[ 'pause_import_folders_sync' ] = False
CLIENT_DEFAULT_OPTIONS[ 'pause_repo_sync' ] = False
CLIENT_DEFAULT_OPTIONS[ 'pause_subs_sync' ] = False

client_size = {}

client_size[ 'gui_maximised' ] = True
client_size[ 'gui_restored_size' ] = [ 640, 480 ]
client_size[ 'gui_restored_position' ] = [ 20, 20 ]
client_size[ 'fs_maximised' ] = True
client_size[ 'fs_restored_size' ] = [ 640, 480 ]
client_size[ 'fs_restored_position' ] = [ 20, 20 ]

CLIENT_DEFAULT_OPTIONS[ 'client_size' ] = client_size

CLIENT_DEFAULT_OPTIONS[ 'local_port' ] = HC.DEFAULT_LOCAL_FILE_PORT

def AddPaddingToDimensions( dimensions, padding ):
    
    ( x, y ) = dimensions
    
    return ( x + padding, y + padding )
    
def CatchExceptionClient( etype, value, tb ):
    
    try:
        
        if etype == HydrusExceptions.DBException:
            
            ( text, caller_traceback, db_traceback ) = value
            
            info = {}
            
            info[ 'text' ] = text
            info[ 'caller_traceback' ] = caller_traceback
            info[ 'db_traceback' ] = db_traceback
            
            message = HC.Message( HC.MESSAGE_TYPE_DB_ERROR, info )
            
        else:
            
            trace_list = traceback.format_tb( tb )
            
            trace = ''.join( trace_list )
            
            message = HC.Message( HC.MESSAGE_TYPE_ERROR, { 'error' : ( etype, value, trace ) } )
            
        
        HC.pubsub.pub( 'message', message )
        
        
    except:
        
        text = 'Encountered an error I could not parse:'
        
        text += os.linesep
        
        text += HC.u( ( etype, value, tb ) )
        
        try: text += traceback.format_exc()
        except: pass
        
        HC.ShowText( text )
        
    
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
        
        if type in ( FIELD_TEXT, FIELD_COMMENT, FIELD_PASSWORD, FIELD_VERIFICATION_RECAPTCHA, FIELD_THREAD_ID ): m.field( name, HC.b( value ) )
        elif type == FIELD_CHECKBOX:
            
            if value: 
                
                # spoiler/on -> name : spoiler, value : on
                # we don't say true/false for checkboxes
                
                ( name, value ) = name.split( '/', 1 )
                
                m.field( name, value )
                
            
        elif type == FIELD_FILE:
            
            ( hash, mime, file ) = value
            
            m.file( name, hash.encode( 'hex' ) + HC.mime_ext_lookup[ mime ], file, { 'Content-Type' : HC.mime_string_lookup[ mime ] } )
            
        
    
    return m.get()
    
def GenerateExportFilename( media, terms ):

    filename = ''
    
    for ( term_type, term ) in terms:
        
        tags_manager = media.GetTagsManager()
        
        if term_type == 'string': filename += term
        elif term_type == 'namespace':
            
            tags = tags_manager.GetNamespaceSlice( ( term, ) )
            
            filename += ', '.join( [ tag.split( ':' )[1] for tag in tags ] )
            
        elif term_type == 'predicate':
            
            if term in ( 'tags', 'nn tags' ):
                
                current = tags_manager.GetCurrent()
                pending = tags_manager.GetPending()
                
                tags = list( current.union( pending ) )
                
                if term == 'nn tags': tags = [ tag for tag in tags if ':' not in tag ]
                else: tags = [ tag if ':' not in tag else tag.split( ':' )[1] for tag in tags ]
                
                tags.sort()
                
                filename += ', '.join( tags )
                
            elif term == 'hash':
                
                hash = media.GetHash()
                
                filename += hash.encode( 'hex' )
                
            
        elif term_type == 'tag':
            
            if ':' in term: term = term.split( ':' )[1]
            
            if tags_manager.HasTag( term ): filename += term
            
        
    
    return filename
    
def GenerateMultipartFormDataCTAndBodyFromDict( fields ):
    
    m = multipart.Multipart()
    
    for ( name, value ) in fields.items(): m.field( name, HC.b( value ) )
    
    return m.get()
    
def GetAllFileHashes():
    
    file_hashes = set()
    
    for path in IterateAllFilePaths():
        
        ( base, filename ) = os.path.split( path )
        
        try:
            
            ( hash_encoded, ext ) = filename.split( '.', 1 )
            
            file_hashes.add( hash_encoded.decode( 'hex' ) )
            
        except: continue
        
    
    return file_hashes
    
def GetAllPaths( raw_paths ):
    
    file_paths = []
    
    title = 'Parsing files and subdirectories'
    
    paths_to_process = raw_paths
    
    total_paths_to_process = len( paths_to_process )
    
    num_processed = 0
    
    while len( paths_to_process ) > 0:
        
        next_paths_to_process = []
        
        for path in paths_to_process:
            
            if os.path.isdir( path ):
                
                subpaths = [ path + os.path.sep + filename for filename in dircache.listdir( path ) ]
                
                total_paths_to_process += len( subpaths )
                
                next_paths_to_process.extend( subpaths )
                
            else: file_paths.append( path )
            
            num_processed += 1
            
        
        paths_to_process = next_paths_to_process
        
    
    gc.collect()
    
    return file_paths
    
def GetAllThumbnailHashes():
    
    thumbnail_hashes = set()
    
    for path in IterateAllThumbnailPaths():
        
        ( base, filename ) = os.path.split( path )
        
        if not filename.endswith( '_resized' ):
            
            try: thumbnail_hashes.add( filename.decode( 'hex' ) )
            except: continue
            
        
    
    return thumbnail_hashes
    
def GetExpectedFilePath( hash, mime ):
    
    hash_encoded = hash.encode( 'hex' )
    
    first_two_chars = hash_encoded[:2]
    
    return HC.CLIENT_FILES_DIR + os.path.sep + first_two_chars + os.path.sep + hash_encoded + HC.mime_ext_lookup[ mime ]
    
def GetFilePath( hash, mime = None ):
    
    if mime is None:
        
        path = None
        
        for potential_mime in HC.ALLOWED_MIMES:
            
            potential_path = GetExpectedFilePath( hash, potential_mime )
            
            if os.path.exists( potential_path ):
                
                path = potential_path
                
                break
                
            
        
    else: path = GetExpectedFilePath( hash, mime )
    
    if path is None or not os.path.exists( path ): raise HydrusExceptions.NotFoundException( 'File not found!' )
    
    return path
    
def GetMediasTagCount( pool, tag_service_identifier = HC.COMBINED_TAG_SERVICE_IDENTIFIER ):
    
    tags_managers = []
    
    for media in pool:
        
        if media.IsCollection(): tags_managers.extend( media.GetSingletonsTagsManagers() )
        else: tags_managers.append( media.GetTagsManager() )
        
    
    current_tags_to_count = collections.Counter()
    deleted_tags_to_count = collections.Counter()
    pending_tags_to_count = collections.Counter()
    petitioned_tags_to_count = collections.Counter()
    
    for tags_manager in tags_managers:
        
        statuses_to_tags = tags_manager.GetStatusesToTags( tag_service_identifier )
        
        current_tags_to_count.update( statuses_to_tags[ HC.CURRENT ] )
        deleted_tags_to_count.update( statuses_to_tags[ HC.DELETED ] )
        pending_tags_to_count.update( statuses_to_tags[ HC.PENDING ] )
        petitioned_tags_to_count.update( statuses_to_tags[ HC.PETITIONED ] )
        
    
    return ( current_tags_to_count, deleted_tags_to_count, pending_tags_to_count, petitioned_tags_to_count )
    
def GetExpectedThumbnailPath( hash, full_size = True ):
    
    hash_encoded = hash.encode( 'hex' )
    
    first_two_chars = hash_encoded[:2]
    
    path = HC.CLIENT_THUMBNAILS_DIR + os.path.sep + first_two_chars + os.path.sep + hash_encoded
    
    if not full_size: path += '_resized'
    
    return path
    
def GetThumbnailPath( hash, full_size = True ):
    
    path = GetExpectedThumbnailPath( hash, full_size )
    
    if not os.path.exists( path ):
        
        if full_size: raise HydrusExceptions.NotFoundException( 'Thumbnail not found!' )
        else:
            
            full_size_path = GetThumbnailPath( hash, True )
            
            thumbnail_dimensions = HC.options[ 'thumbnail_dimensions' ]
            
            thumbnail_resized = HydrusImageHandling.GenerateThumbnail( full_size_path, thumbnail_dimensions )
            
            with open( path, 'wb' ) as f: f.write( thumbnail_resized )
            
        
    
    return path
    
def GetUpdatePath( service_key, begin ):
    
    return HC.CLIENT_UPDATES_DIR + os.path.sep + service_key.encode( 'hex' ) + '_' + str( begin ) + '.yaml'
    
def IterateAllFilePaths():
    
    hex_chars = '0123456789abcdef'
    
    for ( one, two ) in itertools.product( hex_chars, hex_chars ):
        
        dir = HC.CLIENT_FILES_DIR + os.path.sep + one + two
        
        next_paths = dircache.listdir( dir )
        
        for path in next_paths: yield dir + os.path.sep + path
        
    
def IterateAllThumbnailPaths():
    
    hex_chars = '0123456789abcdef'
    
    for ( one, two ) in itertools.product( hex_chars, hex_chars ):
        
        dir = HC.CLIENT_THUMBNAILS_DIR + os.path.sep + one + two
        
        next_paths = dircache.listdir( dir )
        
        for path in next_paths: yield dir + os.path.sep + path
        
    
def IntersectTags( tags_managers, service_identifier = HC.COMBINED_TAG_SERVICE_IDENTIFIER ):
    
    current = list( HC.IntelligentMassIntersect( ( tags_manager.GetCurrent( service_identifier ) for tags_manager in tags_managers ) ) )
    deleted = list( HC.IntelligentMassIntersect( ( tags_manager.GetDeleted( service_identifier ) for tags_manager in tags_managers ) ) )
    pending = list( HC.IntelligentMassIntersect( ( tags_manager.GetPending( service_identifier ) for tags_manager in tags_managers ) ) )
    petitioned = list( HC.IntelligentMassIntersect( ( tags_manager.GetPetitioned( service_identifier ) for tags_manager in tags_managers ) ) )
    
    return ( current, deleted, pending, petitioned )
    
def ParseExportPhrase( phrase ):
    
    try:
        
        terms = [ ( 'string', phrase ) ]
        
        new_terms = []
        
        for ( term_type, term ) in terms:
            
            if term_type == 'string':
                
                while '[' in term:
                    
                    ( pre, term ) = term.split( '[', 1 )
                    
                    ( namespace, term ) = term.split( ']', 1 )
                    
                    new_terms.append( ( 'string', pre ) )
                    new_terms.append( ( 'namespace', namespace ) )
                    
                
            
            new_terms.append( ( term_type, term ) )
            
        
        terms = new_terms
        
        new_terms = []
        
        for ( term_type, term ) in terms:
            
            if term_type == 'string':
                
                while '{' in term:
                    
                    ( pre, term ) = term.split( '{', 1 )
                    
                    ( predicate, term ) = term.split( '}', 1 )
                    
                    new_terms.append( ( 'string', pre ) )
                    new_terms.append( ( 'predicate', predicate ) )
                    
                
            
            new_terms.append( ( term_type, term ) )
            
        
        terms = new_terms
        
        new_terms = []
        
        for ( term_type, term ) in terms:
            
            if term_type == 'string':
                
                while '(' in term:
                    
                    ( pre, term ) = term.split( '(', 1 )
                    
                    ( tag, term ) = term.split( ')', 1 )
                    
                    new_terms.append( ( 'string', pre ) )
                    new_terms.append( ( 'tag', tag ) )
                    
                
            
            new_terms.append( ( term_type, term ) )
            
        
        terms = new_terms
        
    except: raise Exception( 'Could not parse that phrase!' )
    
    return terms
    
def ShowExceptionClient( e ):
    
    if isinstance( e, HydrusExceptions.DBException ):
        
        ( text, caller_traceback, db_traceback ) = e.args
        
        info = {}
        
        info[ 'text' ] = text
        info[ 'caller_traceback' ] = caller_traceback
        info[ 'db_traceback' ] = db_traceback
        
        message = HC.Message( HC.MESSAGE_TYPE_DB_ERROR, info )
        
    else:
        
        ( etype, value, tb ) = sys.exc_info()
        
        if etype is None:
            
            etype = type( e )
            value = HC.u( e )
            
            trace = ''.join( traceback.format_stack() )
            
        else: trace = ''.join( traceback.format_exception( etype, value, tb ) )
        
        message = HC.Message( HC.MESSAGE_TYPE_ERROR, { 'error' : ( etype, value, trace ) } )
        
    
    HC.pubsub.pub( 'message', message )
    
def ShowTextClient( text ): HC.pubsub.pub( 'message', HC.Message( HC.MESSAGE_TYPE_TEXT, { 'text' : text } ) )

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
    
    def __init__( self, service_identifier, predicates, collapse = True ):
        
        self._service_identifier = service_identifier
        self._predicates = predicates
        self._collapse = collapse
        
        # do siblings
        
        if self._collapse:
            
            siblings_manager = HC.app.GetManager( 'tag_siblings' )
            
            self._predicates = siblings_manager.CollapsePredicates( self._predicates )
            
        
        def cmp_func( x, y ): return cmp( x.GetCount(), y.GetCount() )
        
        self._predicates.sort( cmp = cmp_func, reverse = True )
        
    
    def GetMatches( self, search ):
        
        matches = [ predicate for predicate in self._predicates if HC.SearchEntryMatchesPredicate( search, predicate ) ]
        
        if not self._collapse:
            
            parents_manager = HC.app.GetManager( 'tag_parents' )
            
            matches = parents_manager.ExpandPredicates( self._service_identifier, matches )
            
        
        return matches
        
    
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

DEFAULT_BOORUS = {}

name = 'gelbooru'
search_url = 'http://gelbooru.com/index.php?page=post&s=list&tags=%tags%&pid=%index%'
search_separator = '+'
advance_by_page_num = False
thumb_classname = 'thumb'
image_id = None
image_data = 'Original image'
tag_classnames_to_namespaces = { 'tag-type-general' : '', 'tag-type-character' : 'character', 'tag-type-copyright' : 'series', 'tag-type-artist' : 'creator' }

DEFAULT_BOORUS[ 'gelbooru' ] = Booru( name, search_url, search_separator, advance_by_page_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces )

name = 'safebooru'
search_url = 'http://safebooru.org/index.php?page=post&s=list&tags=%tags%&pid=%index%'
search_separator = '+'
advance_by_page_num = False
thumb_classname = 'thumb'
image_id = None
image_data = 'Original image'
tag_classnames_to_namespaces = { 'tag-type-general' : '', 'tag-type-character' : 'character', 'tag-type-copyright' : 'series', 'tag-type-artist' : 'creator' }

DEFAULT_BOORUS[ 'safebooru' ] = Booru( name, search_url, search_separator, advance_by_page_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces )

name = 'e621'
search_url = 'http://e621.net/post/index?page=%index%&tags=%tags%'
search_separator = '%20'
advance_by_page_num = True
thumb_classname = 'thumb'
image_id = None
image_data = 'Download'
tag_classnames_to_namespaces = { 'tag-type-general categorized-tag' : '', 'tag-type-character categorized-tag' : 'character', 'tag-type-copyright categorized-tag' : 'series', 'tag-type-artist categorized-tag' : 'creator', 'tag-type-species categorized-tag' : 'species' }

DEFAULT_BOORUS[ 'e621' ] = Booru( name, search_url, search_separator, advance_by_page_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces )

name = 'rule34@paheal'
search_url = 'http://rule34.paheal.net/post/list/%tags%/%index%'
search_separator = '%20'
advance_by_page_num = True
thumb_classname = 'thumb'
image_id = 'main_image'
image_data = None
tag_classnames_to_namespaces = { 'tag_name' : '' }

DEFAULT_BOORUS[ 'rule34@paheal' ] = Booru( name, search_url, search_separator, advance_by_page_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces )

name = 'danbooru'
search_url = 'http://danbooru.donmai.us/posts?page=%index%&tags=%tags%'
search_separator = '%20'
advance_by_page_num = True
thumb_classname = 'post-preview'
image_id = 'image'
image_data = None
tag_classnames_to_namespaces = { 'category-0' : '', 'category-4' : 'character', 'category-3' : 'series', 'category-1' : 'creator' }

DEFAULT_BOORUS[ 'danbooru' ] = Booru( name, search_url, search_separator, advance_by_page_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces )

name = 'mishimmie'
search_url = 'http://shimmie.katawa-shoujo.com/post/list/%tags%/%index%'
search_separator = '%20'
advance_by_page_num = True
thumb_classname = 'thumb'
image_id = 'main_image'
image_data = None
tag_classnames_to_namespaces = { 'tag_name' : '' }

DEFAULT_BOORUS[ 'mishimmie' ] = Booru( name, search_url, search_separator, advance_by_page_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces )

name = 'rule34@booru.org'
search_url = 'http://rule34.xxx/index.php?page=post&s=list&tags=%tags%&pid=%index%'
search_separator = '%20'
advance_by_page_num = False
thumb_classname = 'thumb'
image_id = None
image_data = 'Original image'
tag_classnames_to_namespaces = { 'tag-type-general' : '' }

DEFAULT_BOORUS[ 'rule34@booru.org' ] = Booru( name, search_url, search_separator, advance_by_page_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces )

name = 'furry@booru.org'
search_url = 'http://furry.booru.org/index.php?page=post&s=list&tags=%tags%&pid=%index%'
search_separator = '+'
advance_by_page_num = False
thumb_classname = 'thumb'
image_id = None
image_data = 'Original image'
tag_classnames_to_namespaces = { 'tag-type-general' : '', 'tag-type-character' : 'character', 'tag-type-copyright' : 'series', 'tag-type-artist' : 'creator' }

DEFAULT_BOORUS[ 'furry@booru.org' ] = Booru( name, search_url, search_separator, advance_by_page_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces )

name = 'xbooru'
search_url = 'http://xbooru.com/index.php?page=post&s=list&tags=%tags%&pid=%index%'
search_separator = '+'
advance_by_page_num = False
thumb_classname = 'thumb'
image_id = None
image_data = 'Original image'
tag_classnames_to_namespaces = { 'tag-type-general' : '', 'tag-type-character' : 'character', 'tag-type-copyright' : 'series', 'tag-type-artist' : 'creator' }

DEFAULT_BOORUS[ 'xbooru' ] = Booru( name, search_url, search_separator, advance_by_page_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces )

name = 'konachan'
search_url = 'http://konachan.com/post?page=%index%&tags=%tags%'
search_separator = '+'
advance_by_page_num = True
thumb_classname = 'thumb'
image_id = None
image_data = 'View larger version'
tag_classnames_to_namespaces = { 'tag-type-general' : '', 'tag-type-character' : 'character', 'tag-type-copyright' : 'series', 'tag-type-artist' : 'creator' }

DEFAULT_BOORUS[ 'konachan' ] = Booru( name, search_url, search_separator, advance_by_page_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces )

name = 'tbib'
search_url = 'http://tbib.org/index.php?page=post&s=list&tags=%tags%&pid=%index%'
search_separator = '+'
advance_by_page_num = False
thumb_classname = 'thumb'
image_id = None
image_data = 'Original image'
tag_classnames_to_namespaces = { 'tag-type-general' : '', 'tag-type-character' : 'character', 'tag-type-copyright' : 'series', 'tag-type-artist' : 'creator' }

DEFAULT_BOORUS[ 'tbib' ] = Booru( name, search_url, search_separator, advance_by_page_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces )

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
    
    def ProcessContentUpdate( self, service_identifier, content_update ):
        
        ( data_type, action, row ) = content_update.ToTuple()
        
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
        self._pending.discard( service_identifier )
        self._deleted.discard( service_identifier )
        self._petitioned.discard( service_identifier )
        
    
class LocalRatings():
    
    # c for current; feel free to rename this stupid thing
    
    def __init__( self, service_identifiers_to_ratings ):
        
        self._service_identifiers_to_ratings = service_identifiers_to_ratings
        
    
    def GetRating( self, service_identifier ):
        
        if service_identifier in self._service_identifiers_to_ratings: return self._service_identifiers_to_ratings[ service_identifier ]
        else: return None
        
    
    def GetRatingSlice( self, service_identifiers ): return frozenset( { self._service_identifiers_to_ratings[ service_identifier ] for service_identifier in service_identifiers if service_identifier in self._service_identifiers_to_ratings } )
    
    def GetServiceIdentifiersToRatings( self ): return self._service_identifiers_to_ratings
    
    def ProcessContentUpdate( self, service_identifier, content_update ):
        
        ( data_type, action, row ) = content_update.ToTuple()
        
        if action == HC.CONTENT_UPDATE_ADD:
            
            ( rating, hashes ) = row
            
            if rating is None and service_identifier in self._service_identifiers_to_ratings: del self._service_identifiers_to_ratings[ service_identifier ]
            else: self._service_identifiers_to_ratings[ service_identifier ] = rating
            
        
    
    def ResetService( self, service_identifier ):
        
        if service_identifier in self._service_identifiers_to_ratings: del self._service_identifiers_to_ratings[ service_identifier ]
        
    
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
    
    def ProcessContentUpdate( self, service_identifier, content_update ):
        
        ( data_type, action, row ) = content_update.ToTuple()
        
        if service_identifier in self._service_identifiers_to_cp: ( current, pending ) = self._service_identifiers_to_cp[ service_identifier ]
        else:
            
            ( current, pending ) = ( None, None )
            
            self._service_identifiers_to_cp[ service_identifier ] = ( current, pending )
            
        
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
            
            self._service_identifiers_to_cp[ service_identifier ] = ( None, None )
            
        
    
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
    
    def __repr__( self ): return 'Credentials: ' + HC.u( ( self._host, self._port, self._access_key.encode( 'hex' ) ) )
    
    def GetAccessKey( self ): return self._access_key
    
    def GetAddress( self ): return ( self._host, self._port )
    
    def GetConnectionString( self ):
        
        connection_string = ''
        
        if self.HasAccessKey(): connection_string += self._access_key.encode( 'hex' ) + '@'
        
        connection_string += self._host + ':' + HC.u( self._port )
        
        return connection_string
        
    
    def HasAccessKey( self ): return self._access_key is not None and self._access_key is not ''
    
    def SetAccessKey( self, access_key ): self._access_key = access_key
    
class DataCache():
    
    def __init__( self, cache_size_key, decay_duration = 1200 ):
        
        self._cache_size_key = cache_size_key
        
        self._decay_duration = decay_duration
        
        self._keys_to_data = {}
        self._keys_fifo = []
        
        self._total_estimated_memory_footprint = 0
        
        self._lock = threading.Lock()
        
        wx.CallLater( 60 * 1000, self.MaintainCache )
        
    
    def Clear( self ):
        
        with self._lock:
            
            self._keys_to_data = {}
            self._keys_fifo = []
            
            self._total_estimated_memory_footprint = 0
            
        
    
    def AddData( self, key, data ):
        
        with self._lock:
            
            if key not in self._keys_to_data:
                
                while self._total_estimated_memory_footprint > HC.options[ self._cache_size_key ] or ( random.randint( 0, 2 ) == 0 and len( self._keys_to_data ) > 0 ):
                    
                    ( deletee_key, last_access_time ) = self._keys_fifo.pop( 0 )
                    
                    deletee_data = self._keys_to_data[ deletee_key ]
                    
                    self._total_estimated_memory_footprint -= deletee_data.GetEstimatedMemoryFootprint()
                    
                    del self._keys_to_data[ deletee_key ]
                    
                
                self._keys_to_data[ key ] = data
                
                self._keys_fifo.append( ( key, HC.GetNow() ) )
                
                self._total_estimated_memory_footprint += data.GetEstimatedMemoryFootprint()
                
            
        
    
    def GetData( self, key ):
        
        with self._lock:
            
            if key not in self._keys_to_data:
                
                message = 'Cache error! Looking for ' + HC.u( key ) + ', but it was missing.'
                
                raise Exception( message )
                
            
            i = 0
            
            for ( fifo_key, last_access_time ) in self._keys_fifo:
                
                if fifo_key == key:
                    
                    del self._keys_fifo[ i ]
                    
                    break
                    
                else: i += 1
                
            
            self._keys_fifo.append( ( key, HC.GetNow() ) )
            
            return self._keys_to_data[ key ]
            
        
    
    def GetKeys( self ):

        with self._lock: return list( self._keys_to_data.keys() )
        
    
    def HasData( self, key ):
        
        with self._lock: return key in self._keys_to_data
        
    
    def MaintainCache( self ):
        
        now = HC.GetNow()
        
        with self._lock:
            
            while True:
                
                if len( self._keys_fifo ) == 0: break
                else:
                    
                    ( key, last_access_time ) = self._keys_fifo[ 0 ]
                    
                    if now - last_access_time > self._decay_duration:
                        
                        del self._keys_fifo[ 0 ]
                        
                        data = self._keys_to_data[ key ]
                        
                        self._total_estimated_memory_footprint -= data.GetEstimatedMemoryFootprint()
                        
                        del self._keys_to_data[ key ]
                        
                    else: break
                    
                
            
        
        wx.CallLater( 60 * 1000, self.MaintainCache )
        
    
class FileQueryResult():
    
    def __init__( self, media_results ):
        
        self._hashes_to_media_results = { media_result.GetHash() : media_result for media_result in media_results }
        self._hashes_ordered = [ media_result.GetHash() for media_result in media_results ]
        self._hashes = set( self._hashes_ordered )
        
        HC.pubsub.sub( self, 'ProcessContentUpdates', 'content_updates_data' )
        HC.pubsub.sub( self, 'ProcessServiceUpdates', 'service_updates_data' )
        HC.pubsub.sub( self, 'RecalcCombinedTags', 'new_tag_service_precedence' )
        
    
    def __iter__( self ):
        
        for hash in self._hashes_ordered: yield self._hashes_to_media_results[ hash ]
        
    
    def __len__( self ): return len( self._hashes_ordered )
    
    def _Remove( self, hashes ):
        
        for hash in hashes:
            
            if hash in self._hashes_to_media_results:
                
                del self._hashes_to_media_results[ hash ]
                
                self._hashes_ordered.remove( hash )
                
            
        
        self._hashes.difference_update( hashes )
        
    
    def AddMediaResults( self, media_results ):
        
        for media_result in media_results:
            
            hash = media_result.GetHash()
            
            if hash in self._hashes: continue # this is actually important, as sometimes we don't want the media result overwritten
            
            self._hashes_to_media_results[ hash ] = media_result
            
            self._hashes_ordered.append( hash )
            
            self._hashes.add( hash )
            
        
    
    def GetHashes( self ): return self._hashes
    
    def GetMediaResult( self, hash ): return self._hashes_to_media_results[ hash ]
    
    def GetMediaResults( self ): return [ self._hashes_to_media_results[ hash ] for hash in self._hashes_ordered ]
    
    def ProcessContentUpdates( self, service_identifiers_to_content_updates ):
        
        for ( service_identifier, content_updates ) in service_identifiers_to_content_updates.items():
            
            for content_update in content_updates:
                
                hashes = content_update.GetHashes()
                
                if len( hashes ) > 0:
                    
                    for hash in self._hashes.intersection( hashes ):
                        
                        media_result = self._hashes_to_media_results[ hash ]
                        
                        media_result.ProcessContentUpdate( service_identifier, content_update )
                        
                    
                
            
        
    
    def ProcessServiceUpdates( self, service_identifiers_to_service_updates ):
        
        for ( service_identifier, service_updates ) in service_identifiers_to_service_updates.items():
            
            for service_update in service_updates:
                
                ( action, row ) = service_update.ToTuple()
                
                if action == HC.SERVICE_UPDATE_DELETE_PENDING:
                    
                    for media_result in self._hashes_to_media_results.values(): media_result.DeletePending( service_identifier )
                    
                elif action == HC.SERVICE_UPDATE_RESET:
                    
                    for media_result in self._hashes_to_media_results.values(): media_result.ResetService( service_identifier )
                    
                
            
        
    
class FileSearchContext():
    
    def __init__( self, file_service_identifier = HC.COMBINED_FILE_SERVICE_IDENTIFIER, tag_service_identifier = HC.COMBINED_TAG_SERVICE_IDENTIFIER, include_current_tags = True, include_pending_tags = True, predicates = [] ):
        
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
    
    def __init__( self, system_predicates ):
        
        self._inbox = False
        self._archive = False
        self._local = False
        self._not_local = False
        
        self._min_num_tags = None
        self._num_tags = None
        self._max_num_tags = None
        
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
        self._min_ratio = None
        self._ratio = None
        self._max_ratio = None
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
                
                ( operator, years, months, days, hours ) = info
                
                age = ( ( ( ( ( ( ( years * 12 ) + months ) * 30 ) + days ) * 24 ) + hours ) * 3600 )
                
                now = HC.GetNow()
                
                # this is backwards because we are talking about age, not timestamp
                
                if operator == '<': self._min_timestamp = now - age
                elif operator == '>': self._max_timestamp = now - age
                elif operator == u'\u2248':
                    
                    self._min_timestamp = now - int( age * 1.15 )
                    self._max_timestamp = now - int( age * 0.85 )
                    
                
            
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
                    
                    if duration == 0: self._duration = 0
                    else:
                        
                        self._min_duration = int( duration * 0.85 )
                        self._max_duration = int( duration * 1.15 )
                        
                    
                
            
            if system_predicate_type == HC.SYSTEM_PREDICATE_TYPE_RATING:
                
                ( service_identifier, operator, value ) = info
                
                self._ratings_predicates.append( ( service_identifier, operator, value ) )
                
            
            if system_predicate_type == HC.SYSTEM_PREDICATE_TYPE_RATIO:
                
                ( operator, ratio_width, ratio_height ) = info
                
                if operator == '=': self._ratio = ( ratio_width, ratio_height )
                elif operator == u'\u2248':
                    
                    self._min_ratio = ( ratio_width * 0.85, ratio_height )
                    self._max_ratio = ( ratio_width * 1.15, ratio_height )
                    
                
            
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
                
                if operator == '<': self._max_num_tags = num_tags
                elif operator == '=': self._num_tags = num_tags
                elif operator == '>': self._min_num_tags = num_tags
                
            
            if system_predicate_type == HC.SYSTEM_PREDICATE_TYPE_WIDTH:
                
                ( operator, width ) = info
                
                if operator == '<': self._max_width = width
                elif operator == '>': self._min_width = width
                elif operator == '=': self._width = width
                elif operator == u'\u2248':
                    
                    if width == 0: self._width = 0
                    else:
                        
                        self._min_width = int( width * 0.85 )
                        self._max_width = int( width * 1.15 )
                        
                    
                
            
            if system_predicate_type == HC.SYSTEM_PREDICATE_TYPE_HEIGHT:
                
                ( operator, height ) = info
                
                if operator == '<': self._max_height = height
                elif operator == '>': self._min_height = height
                elif operator == '=': self._height = height
                elif operator == u'\u2248':
                    
                    if height == 0: self._height = 0
                    else:
                        
                        self._min_height = int( height * 0.85 )
                        self._max_height = int( height * 1.15 )
                        
                    
                
            
            if system_predicate_type == HC.SYSTEM_PREDICATE_TYPE_NUM_WORDS:
                
                ( operator, num_words ) = info
                
                if operator == '<': self._max_num_words = num_words
                elif operator == '>': self._min_num_words = num_words
                elif operator == '=': self._num_words = num_words
                elif operator == u'\u2248':
                    
                    if num_words == 0: self._num_words = 0
                    else:
                        
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
                
            
        
    
    def GetFileServiceInfo( self ): return ( self._file_services_to_include_current, self._file_services_to_include_pending, self._file_services_to_exclude_current, self._file_services_to_exclude_pending )
    
    def GetInfo( self ): return ( self._hash, self._min_size, self._size, self._max_size, self._mimes, self._min_timestamp, self._max_timestamp, self._min_width, self._width, self._max_width, self._min_height, self._height, self._max_height, self._min_ratio, self._ratio, self._max_ratio, self._min_num_words, self._num_words, self._max_num_words, self._min_duration, self._duration, self._max_duration )
    
    def GetLimit( self ): return self._limit
    
    def GetNumTagsInfo( self ): return ( self._min_num_tags, self._num_tags, self._max_num_tags )
    
    def GetRatingsPredicates( self ): return self._ratings_predicates
    
    def GetSimilarTo( self ): return self._similar_to
    
    def HasSimilarTo( self ): return self._similar_to is not None
    
    def MustBeArchive( self ): return self._archive
    
    def MustBeInbox( self ): return self._inbox
    
    def MustBeLocal( self ): return self._local
    
    def MustNotBeLocal( self ): return self._not_local
    
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
        
        ( hash, inbox, size, mime, timestamp, width, height, duration, num_frames, num_words, tags, file_service_identifiers, local_ratings, remote_ratings ) = media_result.ToTuple()
        
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
fourchan_imageboards.append( Imageboard( '/asp/', 'https://sys.4chan.org/asp/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
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
fourchan_imageboards.append( Imageboard( '/gd/', 'https://sys.4chan.org/gd/post', 75, fourchan_typical_form_fields, { RESTRICTION_MAX_FILE_SIZE : 8388608, RESTRICTION_ALLOWED_MIMES : [ HC.IMAGE_GIF, HC.IMAGE_PNG, HC.IMAGE_JPEG, HC.APPLICATION_PDF ] } ) )
fourchan_imageboards.append( Imageboard( '/gif/', 'https://sys.4chan.org/gif/post', 75, fourchan_typical_form_fields, { RESTRICTION_MAX_FILE_SIZE : 4194304, RESTRICTION_ALLOWED_MIMES : [ HC.IMAGE_GIF ] } ) )
fourchan_imageboards.append( Imageboard( '/h/', 'https://sys.4chan.org/h/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
fourchan_imageboards.append( Imageboard( '/hc/', 'https://sys.4chan.org/hc/post', 75, fourchan_typical_form_fields, { RESTRICTION_MAX_FILE_SIZE : 8388608, RESTRICTION_ALLOWED_MIMES : GJP } ) )
fourchan_imageboards.append( Imageboard( '/hm/', 'https://sys.4chan.org/hm/post', 75, fourchan_typical_form_fields, { RESTRICTION_MAX_FILE_SIZE : 8388608, RESTRICTION_ALLOWED_MIMES : GJP } ) )
fourchan_imageboards.append( Imageboard( '/hr/', 'https://sys.4chan.org/hr/post', 75, fourchan_typical_form_fields, { RESTRICTION_MAX_FILE_SIZE : 8388608, RESTRICTION_ALLOWED_MIMES : GJP, RESTRICTION_MIN_RESOLUTION : ( 700, 700 ), RESTRICTION_MAX_RESOLUTION : ( 10000, 10000 ) } ) )
fourchan_imageboards.append( Imageboard( '/int/', 'https://sys.4chan.org/int/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
fourchan_imageboards.append( Imageboard( '/jp/', 'https://sys.4chan.org/jp/post', 75, fourchan_spoiler_form_fields, fourchan_typical_restrictions ) )
fourchan_imageboards.append( Imageboard( '/k/', 'https://sys.4chan.org/k/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
fourchan_imageboards.append( Imageboard( '/lgbt/', 'https://sys.4chan.org/lgbt/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
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
fourchan_imageboards.append( Imageboard( '/vr/', 'https://sys.4chan.org/vr/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
fourchan_imageboards.append( Imageboard( '/w/', 'https://sys.4chan.org/w/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
fourchan_imageboards.append( Imageboard( '/wg/', 'https://sys.4chan.org/wg/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
fourchan_imageboards.append( Imageboard( '/wsg/', 'https://sys.4chan.org/wsg/post', 75, fourchan_typical_form_fields, { RESTRICTION_MAX_FILE_SIZE : 4194304, RESTRICTION_ALLOWED_MIMES : [ HC.IMAGE_GIF ] } ) )
fourchan_imageboards.append( Imageboard( '/x/', 'https://sys.4chan.org/x/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
fourchan_imageboards.append( Imageboard( '/y/', 'https://sys.4chan.org/y/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
fourchan_imageboards.append( Imageboard( '/vp/', 'https://sys.4chan.org/vp/post', 75, fourchan_spoiler_form_fields, fourchan_typical_restrictions ) )

DEFAULT_IMAGEBOARDS.append( ( '4chan', fourchan_imageboards ) )

class Log():
    
    def __init__( self ):
        
        self._entries = []
        
        HC.pubsub.sub( self, 'AddMessage', 'message' )
        
    
    def __iter__( self ): return self._entries.__iter__()
    
    def AddMessage( self, message ): self._entries.append( ( message, HC.GetNow() ) )

class MediaResult():
    
    def __init__( self, tuple ):
        
        # hash, inbox, size, mime, timestamp, width, height, duration, num_frames, num_words, tags_manager, file_service_identifiers_cdpp, local_ratings, remote_ratings
        
        self._tuple = tuple
        
    
    def DeletePending( self, service_identifier ):
        
        service_type = service_identifier.GetType()
        
        ( hash, inbox, size, mime, timestamp, width, height, duration, num_frames, num_words, tags_manager, file_service_identifiers_cdpp, local_ratings, remote_ratings ) = self._tuple
        
        if service_type == HC.TAG_REPOSITORY: tags_manager.DeletePending( service_identifier )
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
    
    def GetTagsManager( self ): return self._tuple[10]
    
    def GetTimestamp( self ): return self._tuple[4]
    
    def ProcessContentUpdate( self, service_identifier, content_update ):
        
        ( data_type, action, row ) = content_update.ToTuple()
        
        ( hash, inbox, size, mime, timestamp, width, height, duration, num_frames, num_words, tags_manager, file_service_identifiers_cdpp, local_ratings, remote_ratings ) = self._tuple
        
        service_type = service_identifier.GetType()
        
        if service_type in ( HC.LOCAL_TAG, HC.TAG_REPOSITORY ): tags_manager.ProcessContentUpdate( service_identifier, content_update )
        elif service_type in ( HC.FILE_REPOSITORY, HC.LOCAL_FILE ):
            
            if service_type == HC.LOCAL_FILE:
                
                if action == HC.CONTENT_UPDATE_ADD and not file_service_identifiers_cdpp.HasLocal(): inbox = True
                elif action == HC.CONTENT_UPDATE_ARCHIVE: inbox = False
                elif action == HC.CONTENT_UPDATE_INBOX: inbox = True
                elif action == HC.CONTENT_UPDATE_DELETE: inbox = False
                
                self._tuple = ( hash, inbox, size, mime, timestamp, width, height, duration, num_frames, num_words, tags_manager, file_service_identifiers_cdpp, local_ratings, remote_ratings )
                
            
            file_service_identifiers_cdpp.ProcessContentUpdate( service_identifier, content_update )
            
        elif service_type in HC.RATINGS_SERVICES:
            
            if service_type in ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ): local_ratings.ProcessContentUpdate( service_identifier, content_update )
            else: remote_ratings.ProcessContentUpdate( service_identifier, content_update )
            
        
    
    def ResetService( self, service_identifier ):
        
        service_type = service_identifier.GetType()
        
        ( hash, inbox, size, mime, timestamp, width, height, duration, num_frames, num_words, tags_manager, file_service_identifiers_cdpp, local_ratings, remote_ratings ) = self._tuple
        
        if service_type in ( HC.TAG_REPOSITORY, HC.COMBINED_TAG ): tags_manager.ResetService( service_identifier )
        elif service_type == HC.FILE_REPOSITORY: file_service_identifiers_cdpp.ResetService( service_identifier )
        
    
    def ToTuple( self ): return self._tuple
    
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
    
    def __init__( self, type ):
        
        self._type = type
        
        if self._type == 'fullscreen': self._data_cache = DataCache( 'fullscreen_cache_size' )
        elif self._type == 'preview': self._data_cache = DataCache( 'preview_cache_size' )
        
        self._total_estimated_memory_footprint = 0
        
        self._keys_being_rendered = {}
        
        HC.pubsub.sub( self, 'FinishedRendering', 'finished_rendering' )
        
    
    def Clear( self ): self._data_cache.Clear()
    
    def GetImage( self, hash, mime, resolution ):
        
        key = ( hash, resolution )
        
        if self._data_cache.HasData( key ): return self._data_cache.GetData( key )
        elif key in self._keys_being_rendered: return self._keys_being_rendered[ key ]
        else:
            
            path = GetFilePath( hash, mime )
            
            image_container = HydrusImageHandling.RenderImage( path, hash, target_resolution = resolution, synchronous = False )
            
            self._keys_being_rendered[ key ] = image_container
            
            return image_container
            
        
    
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
    
    def __init__( self, service_identifier, info ):
        
        HC.HydrusYAMLBase.__init__( self )
        
        self._service_identifier = service_identifier
        self._info = info
        
        HC.pubsub.sub( self, 'ProcessServiceUpdates', 'service_updates_data' )
        
    
    def __hash__( self ): return self._service_identifier.__hash__()
    
    def CanDownload( self ): return self._info[ 'account' ].HasPermission( HC.GET_DATA ) and not self.HasRecentError()
    
    def CanDownloadUpdate( self ):
        
        update_due = self._info[ 'next_download_timestamp' ] + HC.UPDATE_DURATION + 1800 < HC.GetNow()
        
        return not self.IsPaused() and self.CanDownload() and update_due
        
    
    def CanProcessUpdate( self ): return self._info[ 'next_download_timestamp' ] > self._info[ 'next_processing_timestamp' ]
    
    def CanUpload( self ): return self._info[ 'account' ].HasPermission( HC.POST_DATA ) and not self.HasRecentError()
    
    def GetAccount( self ): return self._info[ 'account' ]
    
    def GetCredentials( self ):
        
        host = self._info[ 'host' ]
        port = self._info[ 'port' ]
        if 'access_key' in self._info: access_key = self._info[ 'access_key' ]
        else: access_key = None
        
        credentials = Credentials( host, port, access_key )
        
        return credentials
        
    
    def GetInfo( self ): return self._info
    
    def GetLikeDislike( self ): return ( self._info[ 'like' ], self._info[ 'dislike' ] )
    
    def GetLowerUpper( self ): return ( self._info[ 'lower' ], self._info[ 'upper' ] )
    
    def GetRecentErrorPending( self ):
        
        if 'account' in self._info and self._info[ 'account' ].HasPermission( HC.GENERAL_ADMIN ): return HC.ConvertTimestampToPrettyPending( self._info[ 'last_error' ] + 600 )
        else: return HC.ConvertTimestampToPrettyPending( self._info[ 'last_error' ] + 3600 * 4 )
        
    
    def GetServiceIdentifier( self ): return self._service_identifier
    
    def GetTimestamps( self ): return ( self._info[ 'first_timestamp' ], self._info[ 'next_download_timestamp' ], self._info[ 'next_processing_timestamp' ] )
    
    def GetUpdateStatus( self ):
        
        account = self._info[ 'account' ]
        
        now = HC.GetNow()
        first_timestamp = self._info[ 'first_timestamp' ]
        next_download_timestamp = self._info[ 'next_download_timestamp' ]
        next_processing_timestamp = self._info[ 'next_processing_timestamp' ]
        
        if first_timestamp is None:
            
            num_updates = 0
            num_updates_downloaded = 0
            num_updates_processed = 0
            
        else:
            
            num_updates = ( now - first_timestamp ) / HC.UPDATE_DURATION
            num_updates_downloaded = ( next_download_timestamp - first_timestamp ) / HC.UPDATE_DURATION
            num_updates_processed = ( next_processing_timestamp - first_timestamp ) / HC.UPDATE_DURATION
            
        
        downloaded_text = HC.ConvertIntToPrettyString( num_updates_downloaded ) + '/' + HC.ConvertIntToPrettyString( num_updates )
        
        if not self._info[ 'account' ].HasPermission( HC.GET_DATA ): status = 'updates on hold'
        else:
            
            if self.CanDownloadUpdate(): status = 'downloaded up to ' + HC.ConvertTimestampToPrettySync( self._info[ 'next_download_timestamp' ] )
            elif self.CanProcessUpdate(): status = 'processed up to ' + HC.ConvertTimestampToPrettySync( self._info[ 'next_processing_timestamp' ] )
            elif self.HasRecentError(): status = 'due to a previous error, update is delayed - next check ' + self.GetRecentErrorPending()
            else: status = 'fully synchronised - next update ' + HC.ConvertTimestampToPrettyPending( self._info[ 'next_download_timestamp' ] + HC.UPDATE_DURATION + 1800 )
            
        
        return downloaded_text + ' - ' + status
        
    
    def HasRecentError( self ):
        
        if 'account' in self._info and self._info[ 'account' ].HasPermission( HC.GENERAL_ADMIN ): return self._info[ 'last_error' ] + 900 > HC.GetNow()
        else: return self._info[ 'last_error' ] + 3600 * 4 > HC.GetNow()
        
    
    def IsInitialised( self ):
        
        service_type = self._service_identifier.GetType()
        
        if service_type == HC.SERVER_ADMIN: return 'access_key' in self._info
        else: return True
        
    
    def IsPaused( self ): return self._info[ 'paused' ]
    
    def ProcessServiceUpdates( self, service_identifiers_to_service_updates ):
        
        for ( service_identifier, service_updates ) in service_identifiers_to_service_updates.items():
            
            for service_update in service_updates:
                
                if service_identifier == self._service_identifier:
                    
                    ( action, row ) = service_update.ToTuple()
                    
                    if action == HC.SERVICE_UPDATE_ERROR: self._info[ 'last_error' ] = HC.GetNow()
                    elif action == HC.SERVICE_UPDATE_RESET:
                        
                        self._info[ 'last_error' ] = 0
                        
                        if 'next_processing_timestamp' in self._info: self._info[ 'next_processing_timestamp' ] = 0
                        
                    elif action == HC.SERVICE_UPDATE_ACCOUNT:
                        
                        account = row
                        
                        self._info[ 'account' ] = account
                        self._info[ 'last_error' ] = 0
                        
                    elif action == HC.SERVICE_UPDATE_REQUEST_MADE:
                        
                        num_bytes = row
                        
                        self._info[ 'account' ].RequestMade( num_bytes )
                        
                    elif action == HC.SERVICE_UPDATE_NEXT_DOWNLOAD_TIMESTAMP:
                        
                        next_download_timestamp = row
                        
                        if next_download_timestamp > self._info[ 'next_download_timestamp' ]:
                            
                            if self._info[ 'first_timestamp' ] is None: self._info[ 'first_timestamp' ] = next_download_timestamp
                            
                            self._info[ 'next_download_timestamp' ] = next_download_timestamp
                            
                        
                    elif action == HC.SERVICE_UPDATE_NEXT_PROCESSING_TIMESTAMP:
                        
                        next_processing_timestamp = row
                        
                        if next_processing_timestamp > self._info[ 'next_processing_timestamp' ]:
                            
                            self._info[ 'next_processing_timestamp' ] = next_processing_timestamp
                            
                        
                    
                
            
        
    
    def Request( self, method, command, request_args = {}, request_headers = {}, report_hooks = [], response_to_path = False, return_cookies = False ):
        
        try:
            
            credentials = self.GetCredentials()
            
            if command in ( 'access_key', 'init' ): pass
            elif command in ( 'session_key', 'access_key_verification' ): HydrusNetworking.AddHydrusCredentialsToHeaders( credentials, request_headers )
            else: HydrusNetworking.AddHydrusSessionKeyToHeaders( self._service_identifier, request_headers )
            
            if command == 'backup': long_timeout = True
            else: long_timeout = False
            
            path = '/' + command
            
            if method == HC.GET:
                
                query = HydrusNetworking.ConvertHydrusGETArgsToQuery( request_args )
                
                body = ''
                
            elif method == HC.POST:
                
                query = ''
                
                if command == 'file':
                    
                    content_type = HC.APPLICATION_OCTET_STREAM
                    
                    body = request_args[ 'file' ]
                    
                    del request_args[ 'file' ]
                    
                else:
                    
                    content_type = HC.APPLICATION_YAML
                    
                    body = yaml.safe_dump( request_args )
                    
                
                request_headers[ 'Content-Type' ] = HC.mime_string_lookup[ content_type ]
                
            
            if query != '': path_and_query = path + '?' + query
            else: path_and_query = path
            
            ( host, port ) = credentials.GetAddress()
            
            url = 'http://' + host + ':' + HC.u( port ) + path_and_query
            
            ( response, size_of_response, response_headers, cookies ) = HC.http.Request( method, url, request_headers, body, report_hooks = report_hooks, response_to_path = response_to_path, return_everything = True, long_timeout = long_timeout )
            
            HydrusNetworking.CheckHydrusVersion( self._service_identifier, response_headers )
            
            if method == HC.GET: data_used = size_of_response
            elif method == HC.POST: data_used = len( body )
            
            HydrusNetworking.DoHydrusBandwidth( self._service_identifier, method, command, data_used )
            
            if return_cookies: return ( response, cookies )
            else: return response
            
        except Exception as e:
            
            if isinstance( e, HydrusExceptions.ForbiddenException ):
                
                if HC.u( e ) == 'Session not found!':
                    
                    session_manager = HC.app.GetManager( 'hydrus_sessions' )
                    
                    session_manager.DeleteSessionKey( self._service_identifier )
                    
                
            
            HC.app.Write( 'service_updates', { self._service_identifier : [ HC.ServiceUpdate( HC.SERVICE_UPDATE_ERROR, HC.u( e ) ) ] } )
            
            if isinstance( e, ( HydrusExceptions.PermissionException, HydrusExceptions.NetworkVersionException ) ):
                
                HC.app.Write( 'service_updates', { self._service_identifier : [ HC.ServiceUpdate( HC.SERVICE_UPDATE_ACCOUNT, HC.GetUnknownAccount() ) ] } )
                
            
            raise
            
        
    
    def SetCredentials( self, credentials ):
        
        ( host, port ) = credentials.GetAddress()
        
        self._info[ 'host' ] = host
        self._info[ 'port' ] = port
        
        if credentials.HasAccessKey(): self._info[ 'access_key' ] = credentials.GetAccessKey()
        
    
class ThumbnailCache():
    
    def __init__( self ):
        
        self._data_cache = DataCache( 'thumbnail_cache_size' )
        
        self._queue = Queue.Queue()
        
        self.Clear()
        
        threading.Thread( target = self.DAEMONWaterfall, name = 'Waterfall Daemon' ).start()
        
        HC.pubsub.sub( self, 'Clear', 'thumbnail_resize' )
        
    
    def Clear( self ):
        
        self._data_cache.Clear()
        
        self._special_thumbs = {}
        
        names = [ 'hydrus', 'flash', 'pdf', 'audio', 'video' ]
        
        for name in names:
            
            path = HC.STATIC_DIR + os.path.sep + name + '.png'
            
            thumbnail = HydrusImageHandling.GenerateThumbnail( path, HC.options[ 'thumbnail_dimensions' ] )
            
            temp_path = HC.GetTempPath()
            
            with open( temp_path, 'wb' ) as f: f.write( thumbnail )
            
            hydrus_bitmap = HydrusImageHandling.GenerateHydrusBitmap( temp_path )
            
            self._special_thumbs[ name ] = hydrus_bitmap
            
        
    
    def GetThumbnail( self, media ):
        
        mime = media.GetDisplayMedia().GetMime()
        
        if mime in HC.IMAGES:
            
            hash = media.GetDisplayMedia().GetHash()
            
            if not self._data_cache.HasData( hash ):
                
                try:
                    
                    path = GetThumbnailPath( hash, False )
                    
                    hydrus_bitmap = HydrusImageHandling.GenerateHydrusBitmap( path )
                    
                except Exception as e:
                    HC.ShowException( e )
                    return self._not_found
                
                self._data_cache.AddData( hash, hydrus_bitmap )
                
            
            return self._data_cache.GetData( hash )
            
        elif mime in HC.AUDIO: return self._special_thumbs[ 'audio' ]
        elif mime in HC.VIDEO: return self._special_thumbs[ 'video' ]
        elif mime == HC.APPLICATION_FLASH: return self._special_thumbs[ 'flash' ]
        elif mime == HC.APPLICATION_PDF: return self._special_thumbs[ 'pdf' ]
        else: return self._special_thumbs[ 'hydrus' ]
        
    
    def Waterfall( self, page_key, medias ): self._queue.put( ( page_key, medias ) )
    
    def DAEMONWaterfall( self ):
        
        last_paused = time.clock()
        
        while not HC.shutdown:
            
            try:
                
                ( page_key, medias ) = self._queue.get( timeout = 1 )
                
                random.shuffle( medias )
                
                for media in medias:
                    
                    thumbnail = self.GetThumbnail( media )
                    
                    HC.pubsub.pub( 'waterfall_thumbnail', page_key, media, thumbnail )
                    
                    if time.clock() - last_paused > 0.005:
                        
                        time.sleep( 0.0001 )
                        
                        last_paused = time.clock()
                        
                    
                
            except: pass
            
        
    
class UndoManager():
    
    def __init__( self ):
        
        self._commands = []
        self._inverted_commands = []
        self._current_index = 0
        
        HC.pubsub.sub( self, 'Undo', 'undo' )
        HC.pubsub.sub( self, 'Redo', 'redo' )
        
    
    def _FilterServiceIdentifiersToContentUpdates( self, service_identifiers_to_content_updates ):
        
        filtered_service_identifiers_to_content_updates = {}
        
        for ( service_identifier, content_updates ) in service_identifiers_to_content_updates.items():
            
            filtered_content_updates = []
            
            for content_update in content_updates:
                
                ( data_type, action, row ) = content_update.ToTuple()
                
                if data_type == HC.CONTENT_DATA_TYPE_FILES:
                    if action in ( HC.CONTENT_UPDATE_ADD, HC.CONTENT_UPDATE_DELETE, HC.CONTENT_UPDATE_RESCIND_PETITION ): continue
                elif data_type == HC.CONTENT_DATA_TYPE_MAPPINGS:
                    
                    if action in ( HC.CONTENT_UPDATE_RESCIND_PETITION, HC.CONTENT_UPDATE_ADVANCED ): continue
                    
                else: continue
                
                filtered_content_update = HC.ContentUpdate( data_type, action, row )
                
                filtered_content_updates.append( filtered_content_update )
                
            
            if len( filtered_content_updates ) > 0:
                
                filtered_service_identifiers_to_content_updates[ service_identifier ] = filtered_content_updates
                
            
        
        return filtered_service_identifiers_to_content_updates
        
    
    def _InvertServiceIdentifiersToContentUpdates( self, service_identifiers_to_content_updates ):
        
        inverted_service_identifiers_to_content_updates = {}
        
        for ( service_identifier, content_updates ) in service_identifiers_to_content_updates.items():
            
            inverted_content_updates = []
            
            for content_update in content_updates:
                
                ( data_type, action, row ) = content_update.ToTuple()
                
                inverted_row = row
                
                if data_type == HC.CONTENT_DATA_TYPE_FILES:
                    
                    if action == HC.CONTENT_UPDATE_ARCHIVE: inverted_action = HC.CONTENT_UPDATE_INBOX
                    elif action == HC.CONTENT_UPDATE_INBOX: inverted_action = HC.CONTENT_UPDATE_ARCHIVE
                    elif action == HC.CONTENT_UPDATE_PENDING: inverted_action = HC.CONTENT_UPDATE_RESCIND_PENDING
                    elif action == HC.CONTENT_UPDATE_RESCIND_PENDING: inverted_action = HC.CONTENT_UPDATE_PENDING
                    elif action == HC.CONTENT_UPDATE_PETITION:
                        
                        inverted_action = HC.CONTENT_UPDATE_RESCIND_PETITION
                        
                        ( hashes, reason ) = row
                        
                        inverted_row = hashes
                        
                    
                elif data_type == HC.CONTENT_DATA_TYPE_MAPPINGS:
                    
                    if action == HC.CONTENT_UPDATE_ADD: inverted_action = HC.CONTENT_UPDATE_DELETE
                    elif action == HC.CONTENT_UPDATE_DELETE: inverted_action = HC.CONTENT_UPDATE_ADD
                    elif action == HC.CONTENT_UPDATE_PENDING: inverted_action = HC.CONTENT_UPDATE_RESCIND_PENDING
                    elif action == HC.CONTENT_UPDATE_RESCIND_PENDING: inverted_action = HC.CONTENT_UPDATE_PENDING
                    elif action == HC.CONTENT_UPDATE_PETITION:
                        
                        inverted_action = HC.CONTENT_UPDATE_RESCIND_PETITION
                        
                        ( tag, hashes, reason ) = row
                        
                        inverted_row = ( tag, hashes )
                        
                    
                
                inverted_content_update = HC.ContentUpdate( data_type, inverted_action, inverted_row )
                
                inverted_content_updates.append( inverted_content_update )
                
            
            inverted_service_identifiers_to_content_updates[ service_identifier ] = inverted_content_updates
            
        
        return inverted_service_identifiers_to_content_updates
        
    
    def AddCommand( self, action, *args, **kwargs ):
        
        inverted_action = action
        inverted_args = args
        inverted_kwargs = kwargs
        
        if action == 'content_updates':
            
            ( service_identifiers_to_content_updates, ) = args
            
            service_identifiers_to_content_updates = self._FilterServiceIdentifiersToContentUpdates( service_identifiers_to_content_updates )
            
            if len( service_identifiers_to_content_updates ) == 0: return
            
            inverted_service_identifiers_to_content_updates = self._InvertServiceIdentifiersToContentUpdates( service_identifiers_to_content_updates )
            
            if len( inverted_service_identifiers_to_content_updates ) == 0: return
            
            inverted_args = ( inverted_service_identifiers_to_content_updates, )
            
        else: return
        
        self._commands = self._commands[ : self._current_index ]
        self._inverted_commands = self._inverted_commands[ : self._current_index ]
        
        self._commands.append( ( action, args, kwargs ) )
        
        self._inverted_commands.append( ( inverted_action, inverted_args, inverted_kwargs ) )
        
        self._current_index += 1
        
        HC.pubsub.pub( 'notify_new_undo' )
        
    
    def GetUndoRedoStrings( self ):
        
        ( undo_string, redo_string ) = ( None, None )
        
        if self._current_index > 0:
            
            undo_index = self._current_index - 1
            
            ( action, args, kwargs ) = self._commands[ undo_index ]
            
            if action == 'content_updates':
                
                ( service_identifiers_to_content_updates, ) = args
                
                undo_string = 'undo ' + HC.ConvertServiceIdentifiersToContentUpdatesToPrettyString( service_identifiers_to_content_updates )
                
            
        
        if len( self._commands ) > 0 and self._current_index < len( self._commands ):
            
            redo_index = self._current_index
            
            ( action, args, kwargs ) = self._commands[ redo_index ]
            
            if action == 'content_updates':
                
                ( service_identifiers_to_content_updates, ) = args
                
                redo_string = 'redo ' + HC.ConvertServiceIdentifiersToContentUpdatesToPrettyString( service_identifiers_to_content_updates )
                
            
        
        return ( undo_string, redo_string )
        
    
    def Undo( self ):
        
        if self._current_index > 0:
            
            self._current_index -= 1
            
            ( action, args, kwargs ) = self._inverted_commands[ self._current_index ]
            
            HC.app.WriteSynchronous( action, *args, **kwargs )
            
            HC.pubsub.pub( 'notify_new_undo' )
            
        
    
    def Redo( self ):
        
        if len( self._commands ) > 0 and self._current_index < len( self._commands ):
            
            ( action, args, kwargs ) = self._commands[ self._current_index ]
            
            self._current_index += 1
            
            HC.app.WriteSynchronous( action, *args, **kwargs )
            
            HC.pubsub.pub( 'notify_new_undo' )
            
        
    
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
    