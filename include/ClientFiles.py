import ClientConstants as CC
import ClientData
import gc
import HydrusConstants as HC
import HydrusData
import HydrusExceptions
import HydrusFileHandling
import HydrusGlobals
import HydrusSerialisable
import itertools
import os
import random
import re
import shutil
import stat
import wx

def GenerateExportFilename( media, terms ):
    
    mime = media.GetMime()
    
    filename = ''
    
    for ( term_type, term ) in terms:
        
        tags_manager = media.GetTagsManager()
        
        if term_type == 'string': filename += term
        elif term_type == 'namespace':
            
            tags = tags_manager.GetNamespaceSlice( ( term, ), collapse_siblings = True )
            
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
            
        
    
    if HC.PLATFORM_WINDOWS:
        
        filename = re.sub( '\\\\|/|:|\\*|\\?|"|<|>|\\|', '_', filename, flags = re.UNICODE )
        
    else:
        
        filename = re.sub( '/', '_', filename, flags = re.UNICODE )
        
    
    return filename + HC.mime_ext_lookup[ mime ]
    
def GetAllPaths( raw_paths ):
    
    file_paths = []
    
    paths_to_process = raw_paths
    
    while len( paths_to_process ) > 0:
        
        next_paths_to_process = []
        
        for path in paths_to_process:
            
            if os.path.isdir( path ):
                
                subpaths = [ os.path.join( path, filename ) for filename in os.listdir( path ) ]
                
                next_paths_to_process.extend( subpaths )
                
            else:
                
                file_paths.append( path )
                
            
        
        paths_to_process = next_paths_to_process
        
    
    gc.collect()
    
    return file_paths

def GetAllThumbnailHashes():
    
    thumbnail_hashes = set()
    
    for path in IterateAllThumbnailPaths():
        
        ( base, filename ) = os.path.split( path )
        
        if not filename.endswith( '_resized' ):
            
            try: hash = filename.decode( 'hex' )
            except TypeError: continue
            
            thumbnail_hashes.add( hash )
            
        
    
    return thumbnail_hashes

def GetExpectedFilePath( hash, mime ):
    
    hash_encoded = hash.encode( 'hex' )
    
    first_two_chars = hash_encoded[:2]
    
    return os.path.join( HC.CLIENT_FILES_DIR, first_two_chars, hash_encoded + HC.mime_ext_lookup[ mime ] )
    
def GetExportPath():
    
    options = HydrusGlobals.client_controller.GetOptions()
    
    path = options[ 'export_path' ]
    
    if path is None:
        
        path = os.path.join( os.path.expanduser( '~' ), 'hydrus_export' )
        
        if not os.path.exists( path ):
            
            os.mkdir( path )
            
        
    
    path = os.path.normpath( path ) # converts slashes to backslashes for windows
    
    path = HydrusData.ConvertPortablePathToAbsPath( path )
    
    return path
    
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
    
def GetExpectedThumbnailPath( hash, full_size = True ):
    
    hash_encoded = hash.encode( 'hex' )
    
    first_two_chars = hash_encoded[:2]
    
    path = os.path.join( HC.CLIENT_THUMBNAILS_DIR, first_two_chars, hash_encoded )
    
    if not full_size:
        
        path += '_resized'
        
    
    return path

def GetThumbnailPath( hash, full_size = True ):
    
    path = GetExpectedThumbnailPath( hash, full_size )
    
    if not os.path.exists( path ):
        
        if full_size: raise HydrusExceptions.NotFoundException( 'Thumbnail not found!' )
        else:
            
            full_size_path = GetThumbnailPath( hash, True )
            
            options = HydrusGlobals.client_controller.GetOptions()
            
            thumbnail_dimensions = options[ 'thumbnail_dimensions' ]
            
            if tuple( thumbnail_dimensions ) == HC.UNSCALED_THUMBNAIL_DIMENSIONS:
                
                path = full_size_path
                
            else:
                
                thumbnail_resized = HydrusFileHandling.GenerateThumbnail( full_size_path, thumbnail_dimensions )
                
                with open( path, 'wb' ) as f: f.write( thumbnail_resized )
                
            
        
    
    return path
    
def GetExpectedContentUpdatePackagePath( service_key, begin, subindex ):
    
    return os.path.join( GetExpectedUpdateDir( service_key ), str( begin ) + '_' + str( subindex ) + '.json' )
    
def GetExpectedServiceUpdatePackagePath( service_key, begin ):
    
    return os.path.join( GetExpectedUpdateDir( service_key ), str( begin ) + '_metadata.json' )
    
def GetExpectedUpdateDir( service_key ):
    
    return os.path.join( HC.CLIENT_UPDATES_DIR, service_key.encode( 'hex' ) )
    
def IterateAllFileHashes():
    
    for path in IterateAllFilePaths():
        
        ( base, filename ) = os.path.split( path )
        
        result = filename.split( '.', 1 )
        
        if len( result ) != 2: continue
        
        ( hash_encoded, ext ) = result
        
        try: hash = hash_encoded.decode( 'hex' )
        except TypeError: continue
        
        yield hash
        
    
def IterateAllFilePaths():
    
    hex_chars = '0123456789abcdef'
    
    for ( one, two ) in itertools.product( hex_chars, hex_chars ):
        
        dir = os.path.join( HC.CLIENT_FILES_DIR, one + two )
        
        next_paths = os.listdir( dir )
        
        for path in next_paths:
            
            yield os.path.join( dir, path )
            
        

def IterateAllThumbnailPaths():
    
    hex_chars = '0123456789abcdef'
    
    for ( one, two ) in itertools.product( hex_chars, hex_chars ):
        
        dir = os.path.join( HC.CLIENT_THUMBNAILS_DIR, one + two )
        
        next_paths = os.listdir( dir )
        
        for path in next_paths:
            
            yield os.path.join( dir, path )
            
        
    
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
    
class ExportFolder( HydrusSerialisable.SerialisableBaseNamed ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_EXPORT_FOLDER
    SERIALISABLE_VERSION = 1
    
    def __init__( self, name, export_type = HC.EXPORT_FOLDER_TYPE_REGULAR, file_search_context = None, period = 3600, phrase = '{hash}' ):
        
        HydrusSerialisable.SerialisableBaseNamed.__init__( self, name )
        
        self._export_type = export_type
        self._file_search_context = file_search_context
        self._period = period
        self._phrase = phrase
        self._last_checked = 0
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_file_search_context = self._file_search_context.GetSerialisableTuple()
        
        return ( self._export_type, serialisable_file_search_context, self._period, self._phrase, self._last_checked )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._export_type, serialisable_file_search_context, self._period, self._phrase, self._last_checked ) = serialisable_info
        
        self._file_search_context = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_search_context )
        
    
    def DoWork( self ):
        
        if HydrusGlobals.special_debug_mode: HydrusData.ShowText( self._name + ' checking' )
        
        if HydrusData.TimeHasPassed( self._last_checked + self._period ):
            
            if HydrusGlobals.special_debug_mode: HydrusData.ShowText( self._name + ' time to begin' )
            
            folder_path = self._name
            
            if os.path.exists( folder_path ) and os.path.isdir( folder_path ):
                
                if HydrusGlobals.special_debug_mode: HydrusData.ShowText( self._name + ' folder checks out ok' )
                
                query_hash_ids = HydrusGlobals.client_controller.Read( 'file_query_ids', self._file_search_context )
                
                if HydrusGlobals.special_debug_mode: HydrusData.ShowText( self._name + ' results found: ' + str( len( query_hash_ids ) ) )
                
                query_hash_ids = list( query_hash_ids )
                
                random.shuffle( query_hash_ids )
                
                limit = self._file_search_context.GetSystemPredicates().GetLimit()
                
                if limit is not None: query_hash_ids = query_hash_ids[ : limit ]
                
                media_results = []
                
                i = 0
                
                base = 256
                
                while i < len( query_hash_ids ):
                    
                    if HydrusGlobals.special_debug_mode: HydrusData.ShowText( self._name + ' building results: ' + str( i ) + '/' + str( len( query_hash_ids ) ) )
                    
                    if HC.options[ 'pause_export_folders_sync' ]: return
                    
                    if i == 0: ( last_i, i ) = ( 0, base )
                    else: ( last_i, i ) = ( i, i + base )
                    
                    sub_query_hash_ids = query_hash_ids[ last_i : i ]
                    
                    more_media_results = HydrusGlobals.client_controller.Read( 'media_results_from_ids', CC.LOCAL_FILE_SERVICE_KEY, sub_query_hash_ids )
                    
                    media_results.extend( more_media_results )
                    
                
                if HydrusGlobals.special_debug_mode: HydrusData.ShowText( self._name + ' media_results: ' + str( len( media_results ) ) )
                
                #
                
                terms = ParseExportPhrase( self._phrase )
                
                previous_filenames = set( os.listdir( HydrusData.ToUnicode( folder_path ) ) )
                
                if HydrusGlobals.special_debug_mode: HydrusData.ShowText( self._name + ' existing filenames: ' + str( len( previous_filenames ) ) )
                if HydrusGlobals.special_debug_mode:
                    for previous_filename in previous_filenames:
                        
                        print( previous_filename )
                        
                    
                
                sync_filenames = set()
                
                for media_result in media_results:
                    
                    hash = media_result.GetHash()
                    mime = media_result.GetMime()
                    size = media_result.GetSize()
                    
                    source_path = GetFilePath( hash, mime )
                    
                    filename = GenerateExportFilename( media_result, terms )
                    
                    dest_path = os.path.join( folder_path, filename )
                    if HydrusGlobals.special_debug_mode: HydrusData.ShowText( self._name + ' dest path: ' + dest_path )
                    do_copy = True
                    
                    if filename in sync_filenames:
                        if HydrusGlobals.special_debug_mode: HydrusData.ShowText( self._name + ' it was already attempted this run' )
                        do_copy = False
                        
                    elif os.path.exists( dest_path ):
                        if HydrusGlobals.special_debug_mode: HydrusData.ShowText( self._name + ' it exists' )
                        dest_info = os.lstat( dest_path )
                        
                        dest_size = dest_info[6]
                        
                        if dest_size == size:
                            if HydrusGlobals.special_debug_mode: HydrusData.ShowText( self._name + ' and the file size is the same' )
                            do_copy = False
                            
                        
                    if HydrusGlobals.special_debug_mode: HydrusData.ShowText( self._name + ' copy decision: ' + str( do_copy ) )
                    if do_copy:
                        if HydrusGlobals.special_debug_mode: HydrusData.ShowText( self._name + ' copy started' )
                        shutil.copy( source_path, dest_path )
                        shutil.copystat( source_path, dest_path )
                        
                        try: os.chmod( dest_path, stat.S_IWRITE | stat.S_IREAD )
                        except: pass
                        if HydrusGlobals.special_debug_mode: HydrusData.ShowText( self._name + ' copy ok' )
                    
                    sync_filenames.add( filename )
                    
                if HydrusGlobals.special_debug_mode: HydrusData.ShowText( self._name + ' media results done' )
                if self._export_type == HC.EXPORT_FOLDER_TYPE_SYNCHRONISE:
                    if HydrusGlobals.special_debug_mode: HydrusData.ShowText( self._name + ' inside sync delete code' )
                    deletee_filenames = previous_filenames.difference( sync_filenames )
                    if HydrusGlobals.special_debug_mode: HydrusData.ShowText( self._name + ' delete filenames: ' + str( len( deletee_filenames ) ) )
                    for deletee_filename in deletee_filenames:
                        
                        deletee_path = os.path.join( folder_path, deletee_filename )
                        if HydrusGlobals.special_debug_mode: print( deletee_path )
                        ClientData.DeletePath( deletee_path )
                        
                    
                
            
            self._last_checked = HydrusData.GetNow()
            if HydrusGlobals.special_debug_mode: HydrusData.ShowText( self._name + ' writing self back to db' )
            HydrusGlobals.client_controller.WriteSynchronous( 'serialisable', self )
            if HydrusGlobals.special_debug_mode: HydrusData.ShowText( self._name + ' saved ok' )
        
    
    def ToTuple( self ):
        
        return ( self._name, self._export_type, self._file_search_context, self._period, self._phrase )
        
    
    def SetTuple( self, folder_path, export_type, file_search_context, period, phrase ):
        
        self._name = folder_path
        self._export_type = export_type
        self._file_search_context = file_search_context
        self._period = period
        self._phrase = phrase
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_EXPORT_FOLDER ] = ExportFolder