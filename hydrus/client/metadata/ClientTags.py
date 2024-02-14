import collections
import typing

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
        
        return subtag
        
    else:
        
        if render_for_user:
            
            if new_options.GetBoolean( 'show_namespaces' ) or ( new_options.GetBoolean( 'show_number_namespaces' ) and namespace.isdecimal() ):
                
                connector = new_options.GetString( 'namespace_connector' )
                
            else:
                
                return subtag
                
            
        else:
            
            connector = ':'
            
        
        return namespace + connector + subtag
        
    
class ServiceKeysToTags( HydrusSerialisable.SerialisableBase, collections.defaultdict ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_SERVICE_KEYS_TO_TAGS
    SERIALISABLE_NAME = 'Service Keys To Tags'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, *args, **kwargs ):
        
        collections.defaultdict.__init__( self, set, *args, **kwargs )
        HydrusSerialisable.SerialisableBase.__init__( self )
        
    
    def _GetSerialisableInfo( self ):
        
        return [ ( service_key.hex(), list( tags ) ) for ( service_key, tags ) in self.items() ]
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        for ( service_key_hex, tags_list ) in serialisable_info:
            
            self[ bytes.fromhex( service_key_hex ) ] = set( tags_list )
            
        
    
    def Duplicate( self ) -> "ServiceKeysToTags":
        
        return ServiceKeysToTags( { service_key : set( tags ) for ( service_key, tags ) in self.items() } )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_SERVICE_KEYS_TO_TAGS ] = ServiceKeysToTags
