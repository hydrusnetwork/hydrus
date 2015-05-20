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
SERIALISABLE_TYPE_URL_CACHE = 8
SERIALISABLE_TYPE_HDD_IMPORT = 9

SERIALISABLE_TYPES_TO_OBJECT_TYPES = {}

def CreateFromEasy( ( serialisable_type, version, serialised_info ) ):
    
    obj = SERIALISABLE_TYPES_TO_OBJECT_TYPES[ serialisable_type ]()
    
    obj.InitialiseFromSerialisedInfo( version, serialised_info )
    
    return obj

class SerialisableBase( object ):
    
    SERIALISABLE_TYPE = SERIALISABLE_TYPE_BASE
    VERSION = 1
    
    def _GetSerialisableInfo( self ):
        
        raise NotImplementedError()
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        raise NotImplementedError()
        
    
    def _UpdateInfo( self, version, old_info ):
        
        return old_info
        
    
    def GetCompressedSerialisedInfo( self ):
        
        serialised_info = self.GetSerialisedInfo()
        
        compressed_serialised_info = lz4.dumps( serialised_info )
        
        return compressed_serialised_info
        
    
    def GetEasySerialisedInfo( self ):
        
        return ( self.SERIALISABLE_TYPE, self.VERSION, self.GetSerialisedInfo() )
        
    
    def GetSerialisedInfo( self ):
        
        serialisable_info = self._GetSerialisableInfo()
        
        serialised_info = json.dumps( serialisable_info )
        
        return serialised_info
        
    
    def GetTypeAndVersion( self ):
        
        return ( self.SERIALISABLE_TYPE, self.VERSION )
        
    
    def InitialiseFromCompressedSerialisedInfo( self, version, compressed_serialised_info ):
        
        serialised_info = lz4.loads( compressed_serialised_info )
        
        self.InitialiseFromSerialisedInfo( version, serialised_info )
        
    
    def InitialiseFromSerialisedInfo( self, version, serialised_info ):
        
        serialisable_info = json.loads( serialised_info )
        
        if version != self.VERSION:
            
            serialisable_info = self._UpdateInfo( version, serialisable_info )
            
        
        self._InitialiseFromSerialisableInfo( serialisable_info )
        
    
class SerialisableBaseNamed( SerialisableBase ):
    
    SERIALISABLE_TYPE = SERIALISABLE_TYPE_BASE_NAMED
    
    def __init__( self, name ):
        
        SerialisableBase.__init__( self )
        
        self._name = name
        
    
    def GetName( self ): return self._name
    
    def SetName( self, name ): self._name = name
    