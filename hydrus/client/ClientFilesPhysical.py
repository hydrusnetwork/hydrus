import os
import typing

from hydrus.core import HydrusData
from hydrus.core import HydrusPaths
from hydrus.core import HydrusExceptions

def CheckFullPrefixCoverage( merge_target, prefixes ):
    
    missing_prefixes = GetMissingPrefixes( merge_target, prefixes )
    
    if len( missing_prefixes ) > 0:
        
        list_of_problems = ', '.join( missing_prefixes )
        
        raise HydrusExceptions.DataMissing( 'Missing storage spaces! They are, or are sub-divisions of:' + list_of_problems )
        
    

def GetMissingPrefixes( merge_target: str, prefixes: typing.Collection[ str ], min_prefix_length_allowed = 3, prefixes_are_filtered: bool = False ):
    
    # given a merge target of 'tf'
    # do these prefixes, let's say { tf0, tf1, tf2, tf3, tf4, tf5, tf6, tf7, tf8, tf9, tfa, tfb, tfc, tfd, tfe, tff }, add up to 'tf'?
    
    hex_chars = '0123456789abcdef'
    
    if prefixes_are_filtered:
        
        matching_prefixes = prefixes
        
    else:
        
        matching_prefixes = { prefix for prefix in prefixes if prefix.startswith( merge_target ) }
        
    
    missing_prefixes = []
    
    for char in hex_chars:
        
        expected_prefix = merge_target + char
        
        if expected_prefix in matching_prefixes:
            
            # we are good
            pass
            
        else:
            
            matching_prefixes_for_this_char = { prefix for prefix in prefixes if prefix.startswith( expected_prefix ) }
            
            if len( matching_prefixes_for_this_char ) > 0 or len( expected_prefix ) < min_prefix_length_allowed:
                
                missing_for_this_char = GetMissingPrefixes( expected_prefix, matching_prefixes_for_this_char, prefixes_are_filtered = True )
                
                missing_prefixes.extend( missing_for_this_char )
                
            else:
                
                missing_prefixes.append( expected_prefix )
                
            
        
    
    return missing_prefixes
    

class FilesStorageSubfolder( object ):
    
    def __init__( self, prefix: str, base_location: str, purge: bool = False ):
        
        self.prefix = prefix
        self.base_location = base_location
        self.purge = purge
        
        #
        
        first_char = self.prefix[0]
        hex_chars = self.prefix[1:]
        
        # convert 'b' to ['b'], 'ba' to ['ba'], 'bad' to ['ba', 'd'], and so on  
        our_subfolders = [ hex_chars[ i : i + 2 ] for i in range( 0, len( hex_chars ), 2 ) ]
        
        # restore the f/t char
        our_subfolders[0] = first_char + our_subfolders[0]
        
        self.directory = os.path.join( self.base_location, *our_subfolders )
        
    
    def __str__( self ):
        
        if self.prefix[0] == 'f':
            
            t = 'file'
            
        elif self.prefix[0] == 't':
            
            t = 'thumbnail'
            
        else:
            
            t = 'unknown'
            
        
        return f'{t} {self.prefix[1:]} at {self.directory}'
        
    
    def BaseLocationExists( self ):
        
        return os.path.exists( self.base_location ) and os.path.isdir( self.base_location )
        
    
    def DirectoryExists( self ):
        
        return os.path.exists( self.directory ) and os.path.isdir( self.directory )
        
    
    def GetPath( self, filename: str ) -> str:
        
        return os.path.join( self.directory, filename )
        
    
    def GetPortableBaseLocation( self ):
        
        return HydrusPaths.ConvertAbsPathToPortablePath( self.base_location )
        
    
    def MakeSureExists( self ):
        
        HydrusPaths.MakeSureDirectoryExists( self.directory )
        
    
