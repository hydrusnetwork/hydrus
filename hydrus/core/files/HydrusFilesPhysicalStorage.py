import collections
import itertools

from hydrus.core import HydrusExceptions

# we are moving this to 3 for 4096 folders
# careful not to overwrite Server file storage, which will presumably still be on 2
DEFAULT_PREFIX_LENGTH = 2

def CheckFullPrefixCoverage( prefix_type: str, prefixes_found: collections.abc.Collection[ str ], prefix_length = DEFAULT_PREFIX_LENGTH ):
    
    missing_prefixes = GetMissingPrefixes( prefix_type, prefixes_found, prefix_length = prefix_length )
    
    if len( missing_prefixes ) > 0:
        
        list_of_problems = ', '.join( missing_prefixes )
        
        raise HydrusExceptions.DataMissing( 'Missing storage spaces! They are:' + list_of_problems )
        
    

def GetMissingPrefixes( prefix_type: str, prefixes_found: collections.abc.Collection[ str ], prefix_length = DEFAULT_PREFIX_LENGTH ):
    
    expected_prefixes = set( IteratePrefixes( prefix_type, prefix_length = prefix_length ) )
    
    missing_prefixes = sorted( expected_prefixes.difference( prefixes_found ) )
    
    return missing_prefixes
    

def GetPrefix( hash: bytes, prefix_type: str, prefix_length = DEFAULT_PREFIX_LENGTH ) -> str:
    
    return prefix_type + hash.hex()[ : prefix_length ]
    

def IteratePrefixes( prefix_type: str, prefix_length = DEFAULT_PREFIX_LENGTH ):
    
    hex_chars = '0123456789abcdef'
    
    args = [ hex_chars for _ in range( prefix_length ) ]
    
    for list_of_chars in itertools.product( *args ):
        
        prefix = prefix_type + ''.join( list_of_chars )
        
        yield prefix
        
    
