import HydrusConstants as HC
import HydrusExceptions
import itertools
import os

def GetAllHashes( file_type ): return { os.path.split( path )[1].decode( 'hex' ) for path in IterateAllPaths( file_type ) }

def GetExpectedPath( file_type, hash ):
    
    if file_type == 'file': directory = HC.SERVER_FILES_DIR
    elif file_type == 'thumbnail': directory = HC.SERVER_THUMBNAILS_DIR
    elif file_type == 'message': directory = HC.SERVER_MESSAGES_DIR
    
    hash_encoded = hash.encode( 'hex' )
    
    first_two_chars = hash_encoded[:2]
    
    path = os.path.join( directory, first_two_chars, hash_encoded )
    
    return path
    
def GetExpectedContentUpdatePackagePath( service_key, begin, subindex ):
    
    path = os.path.join( GetExpectedUpdateDir( service_key ), str( int( begin ) ) + '_' + str( subindex ) )
    
    return path
    
def GetExpectedServiceUpdatePackagePath( service_key, begin ):
    
    path = os.path.join( GetExpectedUpdateDir( service_key ), str( int( begin ) ) + '_metadata' )
    
    return path
    
def GetExpectedUpdateDir( service_key ):
    
    return os.path.join( HC.SERVER_UPDATES_DIR, service_key.encode( 'hex' ) )
    
def GetPath( file_type, hash ):
    
    path = GetExpectedPath( file_type, hash )
    
    if not os.path.exists( path ):
        
        raise HydrusExceptions.NotFoundException( file_type + ' not found!' )
        
    
    return path
    
def GetContentUpdatePackagePath( service_key, begin, subindex ):
    
    path = GetExpectedContentUpdatePackagePath( service_key, begin, subindex )
    
    if not os.path.exists( path ):
        
        raise HydrusExceptions.NotFoundException( 'Update not found!' )
        
    
    return path
    
def GetServiceUpdatePackagePath( service_key, begin ):
    
    path = GetExpectedServiceUpdatePackagePath( service_key, begin )
    
    if not os.path.exists( path ):
        
        raise HydrusExceptions.NotFoundException( 'Update not found!' )
        
    
    return path
    
def IterateAllPaths( file_type ):
    
    if file_type == 'file': directory = HC.SERVER_FILES_DIR
    elif file_type == 'thumbnail': directory = HC.SERVER_THUMBNAILS_DIR
    elif file_type == 'message': directory = HC.SERVER_MESSAGES_DIR
    
    hex_chars = '0123456789abcdef'
    
    for ( one, two ) in itertools.product( hex_chars, hex_chars ):
        
        dir = os.path.join( directory, one + two )
        
        next_paths = os.listdir( dir )
        
        for path in next_paths:
            
            yield os.path.join( dir, path )
            
        
    