import ClientConstants as CC
import ClientData
import gc
import HydrusConstants as HC
import HydrusData
import HydrusExceptions
import HydrusFileHandling
import HydrusGlobals
import HydrusPaths
import HydrusSerialisable
import itertools
import os
import random
import re
import shutil
import stat
import wx

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
    
def GetExpectedContentUpdatePackagePath( service_key, begin, subindex ):
    
    return os.path.join( GetExpectedUpdateDir( service_key ), str( begin ) + '_' + str( subindex ) + '.json' )
    
def GetExpectedServiceUpdatePackagePath( service_key, begin ):
    
    return os.path.join( GetExpectedUpdateDir( service_key ), str( begin ) + '_metadata.json' )
    
def GetExpectedUpdateDir( service_key ):
    
    updates_dir = HydrusGlobals.client_controller.GetUpdatesDir()
    
    return os.path.join( updates_dir, service_key.encode( 'hex' ) )
    
