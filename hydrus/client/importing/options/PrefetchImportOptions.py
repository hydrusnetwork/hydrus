from hydrus.core import HydrusSerialisable

DO_NOT_CHECK = 0
DO_CHECK = 1
DO_CHECK_AND_MATCHES_ARE_DISPOSITIVE = 2

class PrefetchImportOptions( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_PREFETCH_IMPORT_OPTIONS
    SERIALISABLE_NAME = 'Prefetch Import Options'
    SERIALISABLE_VERSION = 2
    
    def __init__( self ):
        
        super().__init__()
        
        self._preimport_hash_check_type = DO_CHECK_AND_MATCHES_ARE_DISPOSITIVE
        self._preimport_url_check_type = DO_CHECK
        self._preimport_url_check_looks_for_neighbour_spam = True
        self._fetch_metadata_even_if_url_recognised_and_file_already_in_db = False
        self._fetch_metadata_even_if_hash_recognised_and_file_already_in_db = False
        
    
    def __eq__( self, other ):
        
        if isinstance( other, PrefetchImportOptions ):
            
            return self.__hash__() == other.__hash__()
            
        
        return NotImplemented
        
    
    def __hash__( self ):
        
        return (
            self._preimport_hash_check_type,
            self._preimport_url_check_type,
            self._preimport_url_check_looks_for_neighbour_spam,
            self._fetch_metadata_even_if_url_recognised_and_file_already_in_db,
            self._fetch_metadata_even_if_hash_recognised_and_file_already_in_db,
        ).__hash__()
        
    
    def _GetSerialisableInfo( self ):
        
        return (
            self._preimport_hash_check_type,
            self._preimport_url_check_type,
            self._preimport_url_check_looks_for_neighbour_spam,
            self._fetch_metadata_even_if_url_recognised_and_file_already_in_db,
            self._fetch_metadata_even_if_hash_recognised_and_file_already_in_db,
        )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        (
            self._preimport_hash_check_type,
            self._preimport_url_check_type,
            self._preimport_url_check_looks_for_neighbour_spam,
            self._fetch_metadata_even_if_url_recognised_and_file_already_in_db,
            self._fetch_metadata_even_if_hash_recognised_and_file_already_in_db,
        ) = serialisable_info
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            (
                preimport_hash_check_type,
                preimport_url_check_type,
                preimport_url_check_looks_for_neighbour_spam
            ) = old_serialisable_info
            
            fetch_metadata_even_if_url_recognised_and_file_already_in_db = False
            fetch_metadata_even_if_hash_recognised_and_file_already_in_db = False
            
            new_serialisable_info = (
                preimport_hash_check_type,
                preimport_url_check_type,
                preimport_url_check_looks_for_neighbour_spam,
                fetch_metadata_even_if_url_recognised_and_file_already_in_db,
                fetch_metadata_even_if_hash_recognised_and_file_already_in_db
            )
            
            return ( 2, new_serialisable_info )
            
        
    
    def GetPreImportHashCheckType( self ):
        
        return self._preimport_hash_check_type
        
    
    def GetPreImportURLCheckType( self ):
        
        return self._preimport_url_check_type
        
    
    def GetSummary( self, show_downloader_options: bool = True ):
        
        statements = []
        
        if not show_downloader_options:
            
            return ''
            
        
        if self._preimport_hash_check_type == DO_NOT_CHECK and self._preimport_url_check_type == DO_NOT_CHECK:
            
            statements.append( 'WARNING: always redownloads files!' )
            
        elif self._preimport_hash_check_type == DO_NOT_CHECK:
            
            statements.append( 'WARNING: ignores hashes for file redownload checks!' )
            
        elif self._preimport_hash_check_type == DO_NOT_CHECK:
            
            statements.append( 'WARNING: ignores URLs for file redownload checks!' )
            
        
        if self._fetch_metadata_even_if_hash_recognised_and_file_already_in_db and self._fetch_metadata_even_if_url_recognised_and_file_already_in_db:
            
            statements.append( 'always redownloads metadata!' )
            
        elif self._fetch_metadata_even_if_hash_recognised_and_file_already_in_db:
            
            statements.append( 'ignores hashes for metadata redownload checks' )
            
        elif self._fetch_metadata_even_if_url_recognised_and_file_already_in_db:
            
            statements.append( 'ignores URLs for metadata redownload checks' )
            
        
        #
        
        if len( statements ) == 0:
            
            statements.append( 'everything is fine' )
            
        
        summary = ', '.join( statements )
        
        return summary
        
    
    def PreImportURLCheckLooksForNeighbourSpam( self ) -> bool:
        
        return self._preimport_url_check_looks_for_neighbour_spam
        
    
    def ShouldFetchMetadataEvenIfHashKnownAndFileAlreadyInDB( self ):
        
        return self._fetch_metadata_even_if_hash_recognised_and_file_already_in_db
        
    
    def ShouldFetchMetadataEvenIfURLKnownAndFileAlreadyInDB( self ):
        
        return self._fetch_metadata_even_if_url_recognised_and_file_already_in_db
        
    
    def SetPreImportHashCheckType( self, preimport_hash_check_type: int ):
        
        self._preimport_hash_check_type = preimport_hash_check_type
        
    
    def SetPreImportURLCheckLooksForNeighbourSpam( self, preimport_url_check_looks_for_neighbour_spam: bool ):
        
        self._preimport_url_check_looks_for_neighbour_spam = preimport_url_check_looks_for_neighbour_spam
        
    
    def SetPreImportURLCheckType( self, preimport_url_check_type: int ):
        
        self._preimport_url_check_type = preimport_url_check_type
        
    
    def SetShouldFetchMetadataEvenIfHashKnownAndFileAlreadyInDB( self, value: bool ):
        
        self._fetch_metadata_even_if_hash_recognised_and_file_already_in_db = value
        
    
    def SetShouldFetchMetadataEvenIfURLKnownAndFileAlreadyInDB( self, value: bool ):
        
        self._fetch_metadata_even_if_url_recognised_and_file_already_in_db = value
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_PREFETCH_IMPORT_OPTIONS ] = PrefetchImportOptions
