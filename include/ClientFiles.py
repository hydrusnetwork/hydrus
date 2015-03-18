import gc
import HydrusConstants as HC
import HydrusExceptions
import HydrusFileHandling
import os
import dircache
import itertools

def GetAllFileHashes():
    
    file_hashes = set()
    
    for path in IterateAllFilePaths():
        
        ( base, filename ) = os.path.split( path )
        
        result = filename.split( '.', 1 )
        
        if len( result ) != 2: continue
        
        ( hash_encoded, ext ) = result
        
        try: hash = hash_encoded.decode( 'hex' )
        except TypeError: continue
        
        file_hashes.add( hash )
        
    
    return file_hashes

def GetAllPaths( raw_paths ):
    
    file_paths = []
    
    paths_to_process = raw_paths
    
    while len( paths_to_process ) > 0:
        
        next_paths_to_process = []
        
        for path in paths_to_process:
            
            if os.path.isdir( path ):
                
                subpaths = [ path + os.path.sep + filename for filename in dircache.listdir( path ) ]
                
                next_paths_to_process.extend( subpaths )
                
            else: file_paths.append( path )
            
        
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

class LocationsManager( object ):
    
    def __init__( self, current, deleted, pending, petitioned ):
        
        self._current = current
        self._deleted = deleted
        self._pending = pending
        self._petitioned = petitioned
        
    
    def DeletePending( self, service_key ):
        
        self._pending.discard( service_key )
        self._petitioned.discard( service_key )
        
    
    def GetCDPP( self ): return ( self._current, self._deleted, self._pending, self._petitioned )
    
    def GetCurrent( self ): return self._current
    def GetCurrentRemote( self ): return self._current - set( ( HC.LOCAL_FILE_SERVICE_KEY, ) )
    
    def GetDeleted( self ): return self._deleted
    def GetDeletedRemote( self ): return self._deleted - set( ( HC.LOCAL_FILE_SERVICE_KEY, ) )
    
    def GetPending( self ): return self._pending
    def GetPendingRemote( self ): return self._pending - set( ( HC.LOCAL_FILE_SERVICE_KEY, ) )
    
    def GetPetitioned( self ): return self._petitioned
    def GetPetitionedRemote( self ): return self._petitioned - set( ( HC.LOCAL_FILE_SERVICE_KEY, ) )
    
    def HasDownloading( self ): return HC.LOCAL_FILE_SERVICE_KEY in self._pending
    
    def HasLocal( self ): return HC.LOCAL_FILE_SERVICE_KEY in self._current
    
    def ProcessContentUpdate( self, service_key, content_update ):
        
        ( data_type, action, row ) = content_update.ToTuple()
        
        if action == HC.CONTENT_UPDATE_ADD:
            
            self._current.add( service_key )
            
            self._deleted.discard( service_key )
            self._pending.discard( service_key )
            
        elif action == HC.CONTENT_UPDATE_DELETE:
            
            self._deleted.add( service_key )
            
            self._current.discard( service_key )
            self._petitioned.discard( service_key )
            
        elif action == HC.CONTENT_UPDATE_PENDING:
            
            if service_key not in self._current: self._pending.add( service_key )
            
        elif action == HC.CONTENT_UPDATE_PETITION:
            
            if service_key not in self._deleted: self._petitioned.add( service_key )
            
        elif action == HC.CONTENT_UPDATE_RESCIND_PENDING: self._pending.discard( service_key )
        elif action == HC.CONTENT_UPDATE_RESCIND_PETITION: self._petitioned.discard( service_key )
        
    
    def ResetService( self, service_key ):
        
        self._current.discard( service_key )
        self._pending.discard( service_key )
        self._deleted.discard( service_key )
        self._petitioned.discard( service_key )

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
            
            thumbnail_resized = HydrusFileHandling.GenerateThumbnail( full_size_path, thumbnail_dimensions )
            
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
        
    
        
    
    
    
    
        
    
    
    
    
    
    
