import ClientConstants
import HydrusConstants as HC
import os
import random
import TestConstants

def GenerateClientServiceIdentifier( service_type ):
    
    if service_type == HC.LOCAL_TAG: return HC.LOCAL_TAG_SERVICE_IDENTIFIER
    elif service_type == HC.LOCAL_FILE: return HC.LOCAL_FILE_SERVICE_IDENTIFIER
    else:
        
        service_key = os.urandom( 32 )
        service_name = random.sample( 'abcdefghijklmnopqrstuvwxyz ', 12 )
        
        return HC.ClientServiceIdentifier( service_key, service_type, service_name )
        
    
class App():
    
    def __init__( self ):
        
        HC.app = self
        
        self._reads = {}
        
        self._reads[ 'tag_parents' ] = {}
        self._reads[ 'tag_service_precedence' ] = []
        self._reads[ 'tag_siblings' ] = {}
        
        self._tag_parents_manager = ClientConstants.TagParentsManager()
        self._tag_siblings_manager = ClientConstants.TagSiblingsManager()
        
    
    def GetTagParentsManager( self ): return self._tag_parents_manager
    def GetTagSiblingsManager( self ): return self._tag_siblings_manager
    
    def Read( self, name ): return self._reads[ name ]
    
    def SetRead( self, name, value ): self._reads[ name ] = value