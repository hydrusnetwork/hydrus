import json
import lz4

SERIALISABLE_TYPE_BASE = 0
SERIALISABLE_TYPE_BASE_NAMED = 1
SERIALISABLE_TYPE_SHORTCUTS = 2
SERIALISABLE_TYPE_SUBSCRIPTION = 3
SERIALISABLE_TYPE_PERIODIC = 4
SERIALISABLE_TYPE_GALLERY_QUERY = 5
SERIALISABLE_TYPE_IMPORT_TAG_OPTIONS = 6
SERIALISABLE_TYPE_IMPORT_FILE_OPTIONS = 7
SERIALISABLE_TYPE_SEED_CACHE = 8
SERIALISABLE_TYPE_HDD_IMPORT = 9
SERIALISABLE_TYPE_SERVER_TO_CLIENT_CONTENT_UPDATE_PACKAGE = 10
SERIALISABLE_TYPE_SERVER_TO_CLIENT_SERVICE_UPDATE_PACKAGE = 11
SERIALISABLE_TYPE_MANAGEMENT_CONTROLLER = 12
SERIALISABLE_TYPE_GUI_SESSION = 13
SERIALISABLE_TYPE_PREDICATE = 14
SERIALISABLE_TYPE_FILE_SEARCH_CONTEXT = 15
SERIALISABLE_TYPE_EXPORT_FOLDER = 16
SERIALISABLE_TYPE_THREAD_WATCHER_IMPORT = 17
SERIALISABLE_TYPE_PAGE_OF_IMAGES_IMPORT = 18

SERIALISABLE_TYPES_TO_OBJECT_TYPES = {}

def CreateFromNetworkString( network_string ):
    
    obj_string = lz4.loads( network_string )
    
    return CreateFromString( obj_string )
    
def CreateFromString( obj_string ):
    
    obj_tuple = json.loads( obj_string )
    
    return CreateFromSerialisableTuple( obj_tuple )
    
def CreateFromSerialisableTuple( obj_tuple ):
    
    if len( obj_tuple ) == 3:
        
        ( serialisable_type, version, serialisable_info ) = obj_tuple
        
        obj = SERIALISABLE_TYPES_TO_OBJECT_TYPES[ serialisable_type ]()
        
    else:
        
        ( serialisable_type, name, version, serialisable_info ) = obj_tuple
        
        obj = SERIALISABLE_TYPES_TO_OBJECT_TYPES[ serialisable_type ]( name )
        
    
    obj.InitialiseFromSerialisableInfo( version, serialisable_info )
    
    return obj
    
def DumpToNetworkString( obj ):
    
    obj_string = DumpToString( obj )
    
    return lz4.dumps( obj_string )
    
def DumpToString( obj ):
    
    obj_tuple = GetSerialisableTuple( obj )
    
    return json.dumps( obj_tuple )
    
def GetSerialisableTuple( obj ):
    
    if isinstance( obj, SerialisableBaseNamed ):
        
        return ( obj.SERIALISABLE_TYPE, obj.GetName(), obj.SERIALISABLE_VERSION, obj.GetSerialisableInfo() )
        
    else:
        
        return ( obj.SERIALISABLE_TYPE, obj.SERIALISABLE_VERSION, obj.GetSerialisableInfo() )
        
    
class SerialisableBase( object ):
    
    SERIALISABLE_TYPE = SERIALISABLE_TYPE_BASE
    SERIALISABLE_VERSION = 1
    
    def _GetSerialisableInfo( self ):
        
        raise NotImplementedError()
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        raise NotImplementedError()
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        return old_serialisable_info
        
    
    def GetSerialisableInfo( self ):
        
        serialisable_info = self._GetSerialisableInfo()
        
        return serialisable_info
        
    
    def GetTypeAndVersion( self ):
        
        return ( self.SERIALISABLE_TYPE, self.SERIALISABLE_VERSION )
        
    
    def InitialiseFromSerialisableInfo( self, version, serialisable_info ):
        
        while version < self.SERIALISABLE_VERSION:
            
            ( version, serialisable_info ) = self._UpdateSerialisableInfo( version, serialisable_info )
            
        
        self._InitialiseFromSerialisableInfo( serialisable_info )
        
    
class SerialisableBaseNamed( SerialisableBase ):
    
    SERIALISABLE_TYPE = SERIALISABLE_TYPE_BASE_NAMED
    
    def __init__( self, name ):
        
        SerialisableBase.__init__( self )
        
        self._name = name
        
    
    def GetName( self ): return self._name
    
    def SetName( self, name ): self._name = name
    