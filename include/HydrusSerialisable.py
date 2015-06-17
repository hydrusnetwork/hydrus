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
SERIALISABLE_TYPE_SEED_QUEUE = 8
SERIALISABLE_TYPE_HDD_IMPORT = 9
SERIALISABLE_TYPE_SERVER_TO_CLIENT_CONTENT_UPDATE_PACKAGE = 10
SERIALISABLE_TYPE_SERVER_TO_CLIENT_SERVICE_UPDATE_PACKAGE = 11
SERIALISABLE_TYPE_MANAGEMENT_CONTROLLER = 12

SERIALISABLE_TYPES_TO_OBJECT_TYPES = {}

def CreateFromNetworkString( network_string ):
    
    obj_string = lz4.loads( network_string )
    
    return CreateFromString( obj_string )
    
def CreateFromString( obj_string ):
    
    obj_tuple = json.loads( obj_string )
    
    return CreateFromTuple( obj_tuple )
    
def CreateFromTuple( obj_tuple ):
    
    if len( obj_tuple ) == 3:
        
        ( serialisable_type, version, serialised_info ) = obj_tuple
        
        obj = SERIALISABLE_TYPES_TO_OBJECT_TYPES[ serialisable_type ]()
        
    else:
        
        ( serialisable_type, name, version, serialised_info ) = obj_tuple
        
        obj = SERIALISABLE_TYPES_TO_OBJECT_TYPES[ serialisable_type ]( name )
        
    
    obj.InitialiseFromSerialisedInfo( version, serialised_info )
    
    return obj
    
def DumpToNetworkString( obj ):
    
    obj_string = DumpToString( obj )
    
    return lz4.dumps( obj_string )
    
def DumpToString( obj ):
    
    obj_tuple = DumpToTuple( obj )
    
    return json.dumps( obj_tuple )
    
def DumpToTuple( obj ):
    
    if isinstance( obj, SerialisableBaseNamed ):
        
        return ( obj.SERIALISABLE_TYPE, obj.GetName(), obj.SERIALISABLE_VERSION, obj.GetSerialisedInfo() )
        
    else:
        
        return ( obj.SERIALISABLE_TYPE, obj.SERIALISABLE_VERSION, obj.GetSerialisedInfo() )
        
    
class SerialisableBase( object ):
    
    SERIALISABLE_TYPE = SERIALISABLE_TYPE_BASE
    SERIALISABLE_VERSION = 1
    
    def _GetSerialisableInfo( self ):
        
        raise NotImplementedError()
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        raise NotImplementedError()
        
    
    def _UpdateInfo( self, version, old_info ):
        
        return old_info
        
    
    def GetSerialisedInfo( self ):
        
        serialisable_info = self._GetSerialisableInfo()
        
        serialised_info = json.dumps( serialisable_info )
        
        return serialised_info
        
    
    def GetTypeAndVersion( self ):
        
        return ( self.SERIALISABLE_TYPE, self.SERIALISABLE_VERSION )
        
    
    def InitialiseFromSerialisedInfo( self, version, serialised_info ):
        
        serialisable_info = json.loads( serialised_info )
        
        if version != self.SERIALISABLE_VERSION:
            
            serialisable_info = self._UpdateInfo( version, serialisable_info )
            
        
        self._InitialiseFromSerialisableInfo( serialisable_info )
        
    
class SerialisableBaseNamed( SerialisableBase ):
    
    SERIALISABLE_TYPE = SERIALISABLE_TYPE_BASE_NAMED
    
    def __init__( self, name ):
        
        SerialisableBase.__init__( self )
        
        self._name = name
        
    
    def GetName( self ): return self._name
    
    def SetName( self, name ): self._name = name
    