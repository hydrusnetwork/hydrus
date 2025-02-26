import typing

from hydrus.core import HydrusSerialisable

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientLocation
from hydrus.client.duplicates import ClientDuplicates

from hydrus.client.search import ClientSearchFileSearchContext
from hydrus.client.search import ClientSearchPredicate

class PotentialDuplicatesSearchContext( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_POTENTIAL_DUPLICATES_SEARCH_CONTEXT
    SERIALISABLE_NAME = 'Potential Duplicates Search Context'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, location_context: typing.Optional[ ClientLocation.LocationContext ] = None, initial_predicates = None ):
        
        if location_context is None:
            
            try:
                
                location_context = CG.client_controller.new_options.GetDefaultLocalLocationContext()
                
            except:
                
                location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY )
                
            
        
        if initial_predicates is None:
            
            initial_predicates = [ ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_EVERYTHING ) ]
            
        
        file_search_context = ClientSearchFileSearchContext.FileSearchContext( location_context = location_context, predicates = initial_predicates )
        
        self._file_search_context_1 = file_search_context
        self._file_search_context_2 = file_search_context.Duplicate()
        self._dupe_search_type = ClientDuplicates.DUPE_SEARCH_ONE_FILE_MATCHES_ONE_SEARCH
        self._pixel_dupes_preference = ClientDuplicates.SIMILAR_FILES_PIXEL_DUPES_ALLOWED
        self._max_hamming_distance = 4
        
    
    def __eq__( self, other ):
        
        if isinstance( other, PotentialDuplicatesSearchContext ):
            
            return self.GetSerialisableTuple() == other.GetSerialisableTuple()
            
        
        return NotImplemented
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_file_search_context_1 = self._file_search_context_1.GetSerialisableTuple()
        serialisable_file_search_context_2 = self._file_search_context_2.GetSerialisableTuple()
        
        return ( serialisable_file_search_context_1, serialisable_file_search_context_2, self._dupe_search_type, self._pixel_dupes_preference, self._max_hamming_distance )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_file_search_context_1, serialisable_file_search_context_2, self._dupe_search_type, self._pixel_dupes_preference, self._max_hamming_distance ) = serialisable_info
        
        self._file_search_context_1 = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_search_context_1 )
        self._file_search_context_2 = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_search_context_2 )
        
    
    def GetDupeSearchType( self ) -> int:
        
        return self._dupe_search_type
        
    
    def GetFileSearchContext1( self ) -> ClientSearchFileSearchContext.FileSearchContext:
        
        return self._file_search_context_1
        
    
    def GetFileSearchContext2( self ) -> ClientSearchFileSearchContext.FileSearchContext:
        
        return self._file_search_context_2
        
    
    def GetMaxHammingDistance( self ) -> int:
        
        return self._max_hamming_distance
        
    
    def GetPixelDupesPreference( self ) -> int:
        
        return self._pixel_dupes_preference
        
    
    def GetSummary( self ) -> str:
        
        if self._dupe_search_type == ClientDuplicates.DUPE_SEARCH_BOTH_FILES_MATCH_DIFFERENT_SEARCHES:
            
            search_string = f'files matching [{self._file_search_context_1.GetSummary()}] and [{self._file_search_context_2.GetSummary()}]'
            
        elif self._dupe_search_type == ClientDuplicates.DUPE_SEARCH_BOTH_FILES_MATCH_ONE_SEARCH:
            
            search_string = f'both files matching [{self._file_search_context_1.GetSummary()}]'
            
        else:
            
            search_string = f'one file matching [{self._file_search_context_1.GetSummary()}]'
            
        
        pixel_dupes_string = ''
        
        if self._pixel_dupes_preference == ClientDuplicates.SIMILAR_FILES_PIXEL_DUPES_REQUIRED:
            
            pixel_dupes_string = ', pixel duplicates'
            
        elif self._pixel_dupes_preference == ClientDuplicates.SIMILAR_FILES_PIXEL_DUPES_EXCLUDED:
            
            pixel_dupes_string = ', not pixel duplicates'
            
        
        return search_string + pixel_dupes_string
        
    
    def OptimiseForSearch( self ):
        
        if self._dupe_search_type == ClientDuplicates.DUPE_SEARCH_BOTH_FILES_MATCH_ONE_SEARCH and ( self._file_search_context_1.IsJustSystemEverything() or self._file_search_context_1.HasNoPredicates() ):
            
            self._dupe_search_type = ClientDuplicates.DUPE_SEARCH_ONE_FILE_MATCHES_ONE_SEARCH
            
        elif self._dupe_search_type == ClientDuplicates.DUPE_SEARCH_BOTH_FILES_MATCH_DIFFERENT_SEARCHES:
            
            if self._file_search_context_1.IsJustSystemEverything() or self._file_search_context_1.HasNoPredicates():
                
                f = self._file_search_context_1
                self._file_search_context_1 = self._file_search_context_2
                self._file_search_context_2 = f
                
                self._dupe_search_type = ClientDuplicates.DUPE_SEARCH_ONE_FILE_MATCHES_ONE_SEARCH
                
            elif self._file_search_context_2.IsJustSystemEverything() or self._file_search_context_2.HasNoPredicates():
                
                self._dupe_search_type = ClientDuplicates.DUPE_SEARCH_ONE_FILE_MATCHES_ONE_SEARCH
                
            
        
    
    def SetDupeSearchType( self, value: int ):
        
        self._dupe_search_type = value
        
    
    def SetFileSearchContext1( self, value: ClientSearchFileSearchContext ):
        
        self._file_search_context_1 = value
        
    
    def SetFileSearchContext2( self, value : ClientSearchFileSearchContext ):
        
        self._file_search_context_2 = value
        
    
    def SetMaxHammingDistance( self, value : int ):
        
        self._max_hamming_distance = value
        
    
    def SetPixelDupesPreference( self, value : int ):
        
        self._pixel_dupes_preference = value
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_POTENTIAL_DUPLICATES_SEARCH_CONTEXT ] = PotentialDuplicatesSearchContext
