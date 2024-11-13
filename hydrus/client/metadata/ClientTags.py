import collections
import re

from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTags

from hydrus.client import ClientGlobals as CG

TAG_DISPLAY_STORAGE = 0
TAG_DISPLAY_DISPLAY_ACTUAL = 1
TAG_DISPLAY_SINGLE_MEDIA = 2
TAG_DISPLAY_SELECTION_LIST = 3
TAG_DISPLAY_DISPLAY_IDEAL = 4

tag_display_str_lookup = {
    TAG_DISPLAY_STORAGE : 'stored tags',
    TAG_DISPLAY_DISPLAY_ACTUAL : 'display tags',
    TAG_DISPLAY_SINGLE_MEDIA : 'single media view tags',
    TAG_DISPLAY_SELECTION_LIST : 'multiple media view tags',
    TAG_DISPLAY_DISPLAY_IDEAL : 'ideal display tags'
}

emoji_pattern = re.compile("[" 
    u"\U0001F600-\U0001F64F"  # emoticons
    u"\U0001F300-\U0001F5FF"  # symbols & pictographs
    u"\U0001F680-\U0001F6FF"  # transport & map symbols
    u"\U0001F700-\U0001F77F"  # alchemical symbols
    u"\U0001F780-\U0001F7FF"  # Geometric Shapes Extended
    u"\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
    u"\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
    u"\U0001FA00-\U0001FA6F"  # Chess Symbols
    u"\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
    u"\U00002600-\U000026FF"  # Miscellaneous Symbols
    u"\U00002702-\U000027B0"  # Dingbats
    u"\U00003000-\U0000303F"  # CJK Symbols and Punctuation
    "]+(?:\U0000FE0F)?", # make the preding character a colourful emoji, decode this for an example: b'\xe2\x9b\x93\xef\xb8\x8f'
flags=re.UNICODE)

have_shown_invalid_tag_warning = False

def RenderNamespaceForUser( namespace ):
    
    if namespace == '' or namespace is None:
        
        return 'unnamespaced'
        
    else:
        
        return namespace
        
    

def RenderTag( tag, render_for_user: bool ):
    
    if render_for_user:
        
        new_options = CG.client_controller.new_options
        
        if new_options.GetBoolean( 'replace_tag_underscores_with_spaces' ):
            
            tag = tag.replace( '_', ' ' )
            
        
    
    ( namespace, subtag ) = HydrusTags.SplitTag( tag )
    
    if namespace == '':
        
        result = subtag
        
    else:
        
        if render_for_user:
            
            # TODO: this is garbage. figure out a factory that does this without the options check for every tag, then update the factory on options update
            # same with the underscore stuff above
            
            if new_options.GetBoolean( 'show_namespaces' ) or ( new_options.GetBoolean( 'show_number_namespaces' ) and namespace.isdecimal() ) or ( new_options.GetBoolean( 'show_subtag_number_namespaces' ) and subtag.isdecimal() ):
                
                connector = new_options.GetString( 'namespace_connector' )
                
            else:
                
                return subtag
                
            
        else:
            
            connector = ':'
            
        
        result = namespace + connector + subtag
        
    
    if render_for_user:
        
        if new_options.GetBoolean( 'replace_tag_emojis_with_boxes' ):
            
            result = emoji_pattern.sub( '□', result )
            
        
    
    return result
    

class ServiceKeysToTags( HydrusSerialisable.SerialisableBase, collections.defaultdict ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_SERVICE_KEYS_TO_TAGS
    SERIALISABLE_NAME = 'Service Keys To Tags'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, *args, **kwargs ):
        
        super().__init__( set, *args, **kwargs )
        
    
    def _GetSerialisableInfo( self ):
        
        return [ ( service_key.hex(), list( tags ) ) for ( service_key, tags ) in self.items() ]
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        for ( service_key_hex, tags_list ) in serialisable_info:
            
            self[ bytes.fromhex( service_key_hex ) ] = set( tags_list )
            
        
    
    def Duplicate( self ) -> "ServiceKeysToTags":
        
        return ServiceKeysToTags( { service_key : set( tags ) for ( service_key, tags ) in self.items() } )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_SERVICE_KEYS_TO_TAGS ] = ServiceKeysToTags
