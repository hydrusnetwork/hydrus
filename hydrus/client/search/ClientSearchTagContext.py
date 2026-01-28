from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTags
from hydrus.core import HydrusText

from hydrus.client import ClientConstants as CC

IGNORED_TAG_SEARCH_CHARACTERS = '[](){}/\\"\'-_'
IGNORED_TAG_SEARCH_CHARACTERS_UNICODE_TRANSLATE = { ord( char ) : ' ' for char in IGNORED_TAG_SEARCH_CHARACTERS }

def CollapseWildcardCharacters( text ):
    
    while '**' in text:
        
        text = text.replace( '**', '*' )
        
    
    return text
    

def ConvertSubtagToSearchable( subtag ):
    
    if subtag == '':
        
        return ''
        
    
    subtag = CollapseWildcardCharacters( subtag )
    
    subtag = subtag.translate( IGNORED_TAG_SEARCH_CHARACTERS_UNICODE_TRANSLATE )
    
    subtag = HydrusText.re_one_or_more_whitespace.sub( ' ', subtag )
    
    subtag = subtag.strip()
    
    return subtag
    

def ConvertTagToSearchable( tag ):
    
    ( namespace, subtag ) = HydrusTags.SplitTag( tag )
    
    searchable_subtag = ConvertSubtagToSearchable( subtag )
    
    return HydrusTags.CombineTag( namespace, searchable_subtag )
    

class TagContext( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_TAG_CONTEXT
    SERIALISABLE_NAME = 'Tag Search Context'
    SERIALISABLE_VERSION = 2
    
    def __init__( self, service_key = CC.COMBINED_TAG_SERVICE_KEY, include_current_tags = True, include_pending_tags = True, display_service_key = None ):
        
        self.service_key = service_key
        
        self.include_current_tags = include_current_tags
        self.include_pending_tags = include_pending_tags
        
        if display_service_key is None:
            
            self.display_service_key = self.service_key
            
        else:
            
            self.display_service_key = display_service_key
            
        
    
    def __eq__( self, other ):
        
        if isinstance( other, TagContext ):
            
            return self.__hash__() == other.__hash__()
            
        
        return NotImplemented
        
    
    def __hash__( self ):
        
        return ( self.service_key, self.include_current_tags, self.include_pending_tags, self.display_service_key ).__hash__()
        
    
    def _GetSerialisableInfo( self ):
        
        return ( self.service_key.hex(), self.include_current_tags, self.include_pending_tags, self.display_service_key.hex() )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( encoded_service_key, self.include_current_tags, self.include_pending_tags, encoded_display_service_key ) = serialisable_info
        
        self.service_key = bytes.fromhex( encoded_service_key )
        self.display_service_key = bytes.fromhex( encoded_display_service_key )
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( encoded_service_key, self.include_current_tags, self.include_pending_tags ) = old_serialisable_info
            
            encoded_display_service_key = encoded_service_key
            
            new_serialisable_info = ( encoded_service_key, self.include_current_tags, self.include_pending_tags, encoded_display_service_key )
            
            return ( 2, new_serialisable_info )
            
        
    
    def FixMissingServices( self, filter_method ):
        
        if len( filter_method( [ self.service_key ] ) ) == 0:
            
            self.service_key = CC.COMBINED_TAG_SERVICE_KEY
            
        
        if len( filter_method( [ self.display_service_key ] ) ) == 0:
            
            self.display_service_key = CC.COMBINED_TAG_SERVICE_KEY
            
        
    
    def IsAllKnownTags( self ):
        
        return self.service_key == CC.COMBINED_TAG_SERVICE_KEY
        
    
    def ToString( self, name_method ):
        
        return name_method( self.service_key )
        
    
    def ToDictForAPI( self ):
        
        return {
            'service_key' : self.service_key.hex(), 
            'include_current_tags' : self.include_current_tags, 
            'include_pending_tags' : self.include_pending_tags, 
            'display_service_key' : self.display_service_key.hex()
        }
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_TAG_CONTEXT ] = TagContext
