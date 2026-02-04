from hydrus.core import HydrusSerialisable

DO_NOT_CHECK = 0
DO_CHECK = 1
DO_CHECK_AND_MATCHES_ARE_DISPOSITIVE = 2

class PrefetchImportOptions( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_PREFETCH_IMPORT_OPTIONS
    SERIALISABLE_NAME = 'Prefetch Import Options'
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        super().__init__()
        
        self._preimport_hash_check_type = DO_CHECK_AND_MATCHES_ARE_DISPOSITIVE
        self._preimport_url_check_type = DO_CHECK
        self._preimport_url_check_looks_for_neighbour_spam = True
        #self._fetch_metadata_even_if_url_recognised_and_file_already_in_db = False
        #self._fetch_metadata_even_if_hash_recognised_and_file_already_in_db = False
        
    
    def __eq__( self, other ):
        
        if isinstance( other, PrefetchImportOptions ):
            
            return self.__hash__() == other.__hash__()
            
        
        return NotImplemented
        
    
    def __hash__( self ):
        
        return ( self._preimport_hash_check_type, self._preimport_url_check_type, self._preimport_url_check_looks_for_neighbour_spam ).__hash__()
        
    
    def _GetSerialisableInfo( self ):
        
        return ( self._preimport_hash_check_type, self._preimport_url_check_type, self._preimport_url_check_looks_for_neighbour_spam )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._preimport_hash_check_type, self._preimport_url_check_type, self._preimport_url_check_looks_for_neighbour_spam ) = serialisable_info
        
    
    def GetPreImportHashCheckType( self ):
        
        return self._preimport_hash_check_type
        
    
    def GetPreImportURLCheckType( self ):
        
        return self._preimport_url_check_type
        
    
    def PreImportURLCheckLooksForNeighbourSpam( self ) -> bool:
        
        return self._preimport_url_check_looks_for_neighbour_spam
        
    
    def SetPreImportHashCheckType( self, preimport_hash_check_type: int ):
        
        self._preimport_hash_check_type = preimport_hash_check_type
        
    
    def SetPreImportURLCheckLooksForNeighbourSpam( self, preimport_url_check_looks_for_neighbour_spam: bool ):
        
        self._preimport_url_check_looks_for_neighbour_spam = preimport_url_check_looks_for_neighbour_spam
        
    
    def SetPreImportURLCheckType( self, preimport_url_check_type: int ):
        
        self._preimport_url_check_type = preimport_url_check_type
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_PREFETCH_IMPORT_OPTIONS ] = PrefetchImportOptions
