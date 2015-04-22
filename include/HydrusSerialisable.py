import json
import lz4

SERIALISABLE_TYPE_BASE = 0
SERIALISABLE_TYPE_BASE_NAMED = 1
SERIALISABLE_TYPE_SHORTCUTS = 2

SERIALISABLE_TYPES_TO_OBJECT_TYPES = {}

class SerialisableBase( object ):
    
    SERIALISABLE_TYPE = SERIALISABLE_TYPE_BASE
    VERSION = 1
    
    def _GetSerialisableInfo( self ):
        
        raise NotImplementedError()
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        raise NotImplementedError()
        
    
    def _UpdateInfo( self, version, old_info ):
        
        return old_info
        
    
    def GetSerialisedInfo( self ):
        
        serialisable_info = self._GetSerialisableInfo()
        
        serialised_info = json.dumps( serialisable_info )
        
        compressed_serialised_info = lz4.dumps( serialised_info )
        
        return compressed_serialised_info
        
    
    def GetTypeAndVersion( self ):
        
        return ( self.SERIALISABLE_TYPE, self.VERSION )
        
    
    def InitialiseFromSerialisedInfo( self, version, compressed_serialised_info ):
        
        serialised_info = lz4.loads( compressed_serialised_info )
        
        serialisable_info = json.loads( serialised_info )
        
        if version != self.VERSION:
            
            serialisable_info = self._UpdateInfo( version, serialisable_info )
            
        
        self._InitialiseFromSerialisableInfo( serialisable_info )
        
    
class SerialisableBaseNamed( SerialisableBase ):
    
    SERIALISABLE_TYPE = SERIALISABLE_TYPE_BASE_NAMED
    VERSION = 1
    
    def __init__( self, name ):
        
        SerialisableBase.__init__( self )
        
        self._name = name
        
    
    def GetName( self ): return self._name
    
    def SetName( self, name ): self._name = name
    