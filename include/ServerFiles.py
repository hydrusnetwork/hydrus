import HydrusConstants as HC
import HydrusData
import HydrusExceptions
import HydrusGlobals
import itertools
import os

def GetAllHashes( file_type ):
    
    return { os.path.split( path )[1].decode( 'hex' ) for path in IterateAllPaths( file_type ) }
    
def GetExpectedFilePath( hash ):
    
    files_dir = HydrusGlobals.server_controller.GetFilesDir()
    
    hash_encoded = hash.encode( 'hex' )
    
    first_two_chars = hash_encoded[:2]
    
    path = os.path.join( files_dir, first_two_chars, hash_encoded )
    
    return path
    
def GetExpectedThumbnailPath( hash ):
    
    files_dir = HydrusGlobals.server_controller.GetFilesDir()
    
    hash_encoded = hash.encode( 'hex' )
    
    first_two_chars = hash_encoded[:2]
    
    path = os.path.join( files_dir, first_two_chars, hash_encoded + '.thumbnail' )
    
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
    
    files_dir = HydrusGlobals.server_controller.GetFilesDir()
    
    for prefix in HydrusData.IterateHexPrefixes():
        
        dir = os.path.join( files_dir, prefix )
        
        filenames = os.listdir( dir )
        
        for filename in filenames:
            
            if file_type == 'file' and filename.endswith( '.thumbnail' ):
                
                continue
                
            elif file_type == 'thumbnail' and not filename.endswith( '.thumbnail' ):
                
                continue
                
            
            yield os.path.join( dir, filename )
            
        
    
