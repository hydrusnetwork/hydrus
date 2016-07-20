import HydrusConstants as HC
import HydrusData
import HydrusExceptions
import itertools
import os

def GetAllHashes( file_type ):
    
    return { os.path.split( path )[1].decode( 'hex' ) for path in IterateAllPaths( file_type ) }
    
def GetExpectedFilePath( hash ):
    
    hash_encoded = hash.encode( 'hex' )
    
    first_two_chars = hash_encoded[:2]
    
    path = os.path.join( HC.SERVER_FILES_DIR, first_two_chars, hash_encoded )
    
    return path
    
def GetExpectedThumbnailPath( hash ):
    
    hash_encoded = hash.encode( 'hex' )
    
    first_two_chars = hash_encoded[:2]
    
    path = os.path.join( HC.SERVER_FILES_DIR, first_two_chars, hash_encoded + '.thumbnail' )
    
    return path
    
def GetExpectedContentUpdatePackagePath( service_key, begin, subindex ):
    
    path = os.path.join( GetExpectedUpdateDir( service_key ), str( int( begin ) ) + '_' + str( subindex ) )
    
    return path
    
def GetExpectedServiceUpdatePackagePath( service_key, begin ):
    
    path = os.path.join( GetExpectedUpdateDir( service_key ), str( int( begin ) ) + '_metadata' )
    
    return path
    
def GetExpectedUpdateDir( service_key ):
    
    return os.path.join( HC.SERVER_UPDATES_DIR, service_key.encode( 'hex' ) )
    
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
    
def GetFilePath( hash ):
    
    path = GetExpectedFilePath( hash )
    
    if not os.path.exists( path ):
        
        raise HydrusExceptions.NotFoundException( 'File not found!' )
        
    
    return path
    
def GetThumbnailPath( hash ):
    
    path = GetExpectedThumbnailPath( hash )
    
    if not os.path.exists( path ):
        
        raise HydrusExceptions.NotFoundException( 'Thumbnail not found!' )
        
    
    return path
    
def IterateAllPaths( file_type ):
    
    for prefix in HydrusData.IterateHexPrefixes():
        
        dir = os.path.join( HC.SERVER_FILES_DIR, prefix )
        
        filenames = os.listdir( dir )
        
        for filename in filenames:
            
            if file_type == 'file' and filename.endswith( '.thumbnail' ):
                
                continue
                
            elif file_type == 'thumbnail' and not filename.endswith( '.thumbnail' ):
                
                continue
                
            
            yield os.path.join( dir, filename )
            
        
    