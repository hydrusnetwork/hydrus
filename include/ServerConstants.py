import dircache
import HydrusConstants as HC
import HydrusExceptions
import itertools
import os

def GetExpectedPath( file_type, hash ):
    
    if file_type == 'file': directory = HC.SERVER_FILES_DIR
    elif file_type == 'thumbnail': directory = HC.SERVER_THUMBNAILS_DIR
    elif file_type == 'update': directory = HC.SERVER_UPDATES_DIR
    elif file_type == 'message': directory = HC.SERVER_MESSAGES_DIR
    
    hash_encoded = hash.encode( 'hex' )
    
    first_two_chars = hash_encoded[:2]
    
    path = directory + os.path.sep + first_two_chars + os.path.sep + hash_encoded
    
    return path
    
def GetPath( file_type, hash ):
    
    path = GetExpectedPath( file_type, hash )
    
    if not os.path.exists( path ): raise HydrusExceptions.NotFoundException( file_type + ' not found!' )
    
    return path
    
def GetAllHashes( file_type ): return { os.path.split( path )[1].decode( 'hex' ) for path in IterateAllPaths( file_type ) }

def IterateAllPaths( file_type ):
    
    if file_type == 'file': directory = HC.SERVER_FILES_DIR
    elif file_type == 'thumbnail': directory = HC.SERVER_THUMBNAILS_DIR
    elif file_type == 'update': directory = HC.SERVER_UPDATES_DIR
    elif file_type == 'message': directory = HC.SERVER_MESSAGES_DIR
    
    hex_chars = '0123456789abcdef'
    
    for ( one, two ) in itertools.product( hex_chars, hex_chars ):
        
        dir = directory + os.path.sep + one + two
        
        next_paths = dircache.listdir( dir )
        
        for path in next_paths: yield dir + os.path.sep + path
        
    