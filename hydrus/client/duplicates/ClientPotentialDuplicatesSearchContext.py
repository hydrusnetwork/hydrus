import collections
import math
import random

from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusLists
from hydrus.core import HydrusTime

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientLocation
from hydrus.client.duplicates import ClientDuplicates
from hydrus.client.media import ClientMediaResult

from hydrus.client.search import ClientSearchFileSearchContext
from hydrus.client.search import ClientSearchPredicate
from hydrus.client.search import ClientSearchTagContext

POTENTIAL_DUPLICATE_PAIRS_BLOCK_SIZE_GUIDELINE = 4000

PAIRS_UPDATE_CLEAR_ALL = 0
PAIRS_UPDATE_DELETE_PAIRS = 1
PAIRS_UPDATE_DELETE_PAIRS_BY_MEDIA_ID = 2
PAIRS_UPDATE_ADD_ROWS = 3

class PotentialDuplicateIdPairsAndDistances( object ):
    
    def __init__( self, potential_id_pairs_and_distances: collections.abc.Collection[ tuple[ int, int, int ] ] ):
        
        self._potential_id_pairs_and_distances = list( potential_id_pairs_and_distances )
        
        self._media_ids_to_other_media_ids_to_distances = collections.defaultdict( dict )
        self._mapping_initialised = False
        
        self._current_search_block_size = POTENTIAL_DUPLICATE_PAIRS_BLOCK_SIZE_GUIDELINE
        
    
    def __len__( self ):
        
        return len( self._potential_id_pairs_and_distances )
        
    
    def _AddToMappingIfInitialised( self, rows ):
        
        if not self._mapping_initialised:
            
            return
            
        
        for ( smaller_media_id, larger_media_id, distance ) in rows:
            
            self._media_ids_to_other_media_ids_to_distances[ smaller_media_id ][ larger_media_id ] = distance
            self._media_ids_to_other_media_ids_to_distances[ larger_media_id ][ smaller_media_id ] = distance
            
        
    
    def _DeleteFromMappingIfInitialised( self, deletee_pairs ):
        
        if not self._mapping_initialised:
            
            return
            
        
        for ( deletee_smaller_media_id, deletee_larger_media_id ) in deletee_pairs:
            
            for ( deletee_media_id_a, deletee_media_id_b ) in [
                ( deletee_smaller_media_id, deletee_larger_media_id ),
                ( deletee_larger_media_id, deletee_smaller_media_id ),
            ]:
                
                if deletee_media_id_a in self._media_ids_to_other_media_ids_to_distances:
                    
                    other_media_ids_to_distances = self._media_ids_to_other_media_ids_to_distances[ deletee_media_id_a ]
                    
                    if deletee_media_id_b in other_media_ids_to_distances:
                        
                        del other_media_ids_to_distances[ deletee_media_id_b ]
                        
                        if len( other_media_ids_to_distances ) == 0:
                            
                            del self._media_ids_to_other_media_ids_to_distances[ deletee_media_id_a ]
                            
                        
                    
                
            
        
    
    def _FilterExistingPairs( self, pairs ):
        
        if not self._mapping_initialised:
            
            self._InitialiseMapping()
            
        
        existing_pairs = [
            ( smaller_media_id, larger_media_id )
            for ( smaller_media_id, larger_media_id )
            in pairs
            if smaller_media_id in self._media_ids_to_other_media_ids_to_distances and larger_media_id in self._media_ids_to_other_media_ids_to_distances[ smaller_media_id ]
        ]
        
        return existing_pairs
        
    
    def _FilterNonExistingRows( self, rows ):
        
        if not self._mapping_initialised:
            
            self._InitialiseMapping()
            
        
        new_rows = [
            ( smaller_media_id, larger_media_id, distance )
            for ( smaller_media_id, larger_media_id, distance )
            in rows
            if smaller_media_id not in self._media_ids_to_other_media_ids_to_distances or larger_media_id not in self._media_ids_to_other_media_ids_to_distances[ smaller_media_id ]
        ]
        
        return new_rows
        
    
    def _GetPairsFromMediaId( self, media_id ):
        
        if not self._mapping_initialised:
            
            self._InitialiseMapping()
            
        
        if media_id in self._media_ids_to_other_media_ids_to_distances:
            
            return [ ( min( media_id, other_media_id ), max( media_id, other_media_id ) ) for other_media_id in self._media_ids_to_other_media_ids_to_distances[ media_id ] ]
            
        else:
            
            return []
            
        
    
    def _InitialiseMapping( self ):
        
        self._media_ids_to_other_media_ids_to_distances = collections.defaultdict( dict )
        
        for ( smaller_media_id, larger_media_id, distance ) in self._potential_id_pairs_and_distances:
            
            self._media_ids_to_other_media_ids_to_distances[ smaller_media_id ][ larger_media_id ] = distance
            self._media_ids_to_other_media_ids_to_distances[ larger_media_id ][ smaller_media_id ] = distance
            
        
        self._mapping_initialised = True
        
    
    def AddRows( self, rows ):
        
        if len( rows ) == 0:
            
            return
            
        
        new_rows = self._FilterNonExistingRows( rows )
        
        if len( new_rows ) == 0:
            
            return
            
        
        self._potential_id_pairs_and_distances.extend( new_rows )
        
        self._AddToMappingIfInitialised( new_rows )
        
    
    def ClearPairs( self ):
        
        self._potential_id_pairs_and_distances = []
        
        self._mapping_initialised = False
        
    
    def DeletePairs( self, deletee_pairs ):
        
        if len( deletee_pairs ) == 0:
            
            return
            
        
        existing_deletee_pairs = self._FilterExistingPairs( deletee_pairs )
        
        if len( existing_deletee_pairs ) == 0:
            
            return
            
        
        if not isinstance( existing_deletee_pairs, set ):
            
            existing_deletee_pairs = set( existing_deletee_pairs )
            
        
        self._potential_id_pairs_and_distances = [ ( smaller_media_id, larger_media_id, distance ) for ( smaller_media_id, larger_media_id, distance ) in self._potential_id_pairs_and_distances if ( smaller_media_id, larger_media_id ) not in existing_deletee_pairs ]
        
        self._DeleteFromMappingIfInitialised( existing_deletee_pairs )
        
    
    def DeletePairsByMediaId( self, deletee_media_id: int ):
        
        deletee_pairs = self._GetPairsFromMediaId( deletee_media_id )
        
        self.DeletePairs( deletee_pairs )
        
    
    def Duplicate( self ) -> "PotentialDuplicateIdPairsAndDistances":
        
        return PotentialDuplicateIdPairsAndDistances( self._potential_id_pairs_and_distances )
        
    
    def FilterWiderPotentialGroup( self, media_ids: collections.abc.Collection[ int ] ):
        
        # ok, the caller wants to process a 'whole group' of similar files all at once, so let's get them all. recall that merging a pair merges peasant potentials to the king too
        # given this file (of a pair), what are all the other pairs this file has? what are all the potentials those other files have? keep searching until the whole network is mapped
        
        if not self._mapping_initialised:
            
            self._InitialiseMapping()
            
        
        searched = set()
        still_to_search = list( media_ids )
        rows_found = []
        
        while len( still_to_search ) > 0:
            
            search_media_id = still_to_search.pop()
            
            searched.add( search_media_id )
            
            other_media_ids_to_distances = self._media_ids_to_other_media_ids_to_distances[ search_media_id ]
            
            for ( result_media_id, distance ) in other_media_ids_to_distances.items():
                
                if result_media_id in searched:
                    
                    continue
                    
                
                rows_found.append( ( min( search_media_id, result_media_id ), max( search_media_id, result_media_id ), distance ) )
                
                still_to_search.append( result_media_id )
                
            
        
        return PotentialDuplicateIdPairsAndDistances( rows_found )
        
    
    def IterateBlocks( self ):
        
        for block in HydrusLists.SplitListIntoChunks( self._potential_id_pairs_and_distances, POTENTIAL_DUPLICATE_PAIRS_BLOCK_SIZE_GUIDELINE ):
            
            yield PotentialDuplicateIdPairsAndDistances( block )
            
        
    
    def IteratePairs( self ):
        
        for ( smaller_media_id, larger_media_id, distance ) in self._potential_id_pairs_and_distances:
            
            yield ( smaller_media_id, larger_media_id )
            
        
    
    def GetPairs( self ) -> list[ tuple[ int, int ] ]:
        
        return [ ( smaller_media_id, larger_media_id ) for ( smaller_media_id, larger_media_id, distance ) in self._potential_id_pairs_and_distances ]
        
    
    def GetPairListsBySmallestDistanceFirst( self ) -> list[ list[ tuple[ int, int ] ] ]:
        
        distance_to_pairs = collections.defaultdict( list )
        
        for ( smaller_media_id, larger_media_id, distance ) in self._potential_id_pairs_and_distances:
            
            distance_to_pairs[ distance ].append( ( smaller_media_id, larger_media_id ) )
            
        
        distances = sorted( distance_to_pairs.keys() )
        
        return [ distance_to_pairs[ distance ] for distance in distances ]
        
    
    def GetRows( self ):
        
        return list( self._potential_id_pairs_and_distances )
        
    
    def IterateRows( self ):
        
        return self._potential_id_pairs_and_distances.__iter__()
        
    
    def Merge( self, potential_duplicate_id_pairs_and_distances: "PotentialDuplicateIdPairsAndDistances" ):
        
        rows = potential_duplicate_id_pairs_and_distances.GetRows()
        
        self.AddRows( rows )
        
    
    def NotifyPotentialDuplicatePairsUpdate( self, update_type, *args ):
        
        if update_type == PAIRS_UPDATE_CLEAR_ALL:
            
            # no args
            
            self.ClearPairs()
            
        elif update_type == PAIRS_UPDATE_DELETE_PAIRS:
            
            ( location_context, pairs ) = args
            
            self.DeletePairs( pairs )
            
        elif update_type == PAIRS_UPDATE_DELETE_PAIRS_BY_MEDIA_ID:
            
            ( media_id, ) = args 
            
            self.DeletePairsByMediaId( media_id )
            
        elif update_type == PAIRS_UPDATE_ADD_ROWS:
            
            ( location_context, rows ) = args
            
            self.AddRows( rows )
            
        
    
    def NotifyWorkTimeForAutothrottle( self, actual_work_period: float, ideal_work_period: float ):
        
        minimum_block_size = int( POTENTIAL_DUPLICATE_PAIRS_BLOCK_SIZE_GUIDELINE / 10 )
        maximum_block_size = int( POTENTIAL_DUPLICATE_PAIRS_BLOCK_SIZE_GUIDELINE * 25 )
        
        if actual_work_period > ideal_work_period * 1.1:
            
            self._current_search_block_size = max( minimum_block_size, int( self._current_search_block_size * 0.5 ) )
            
        elif actual_work_period < ideal_work_period / 1.1:
            
            self._current_search_block_size = min( maximum_block_size, int( self._current_search_block_size * 1.1 ) )
            
        
    
    def PopBlock( self, block_size = None ):
        
        if block_size is None:
            
            block_size = self._current_search_block_size
            
        
        block_of_id_pairs_and_distances = self._potential_id_pairs_and_distances[ : block_size ]
        
        self._potential_id_pairs_and_distances = self._potential_id_pairs_and_distances[ block_size : ]
        
        self._mapping_initialised = False
        
        return PotentialDuplicateIdPairsAndDistances( block_of_id_pairs_and_distances )
        
    
    def RandomiseForFastSearch( self ):
        
        # this ensures all the ids are lined up
        self._potential_id_pairs_and_distances.sort()
        
        # this ensures we still have a decent random selection within that
        self._potential_id_pairs_and_distances = HydrusLists.RandomiseListByChunks( self._potential_id_pairs_and_distances, POTENTIAL_DUPLICATE_PAIRS_BLOCK_SIZE_GUIDELINE )
        
    
    def RandomiseForRichEstimate( self ):
        
        # we want hits early and thus are going for a very fine-grained randomisation
        # I'd just do random.shuffle but it is a bit slow at n=1 tbh
        self._potential_id_pairs_and_distances = HydrusLists.RandomiseListByChunks( self._potential_id_pairs_and_distances, 32 )
        
    

class PotentialDuplicateMediaResultPairsAndDistances( object ):
    
    def __init__( self, potential_media_result_pairs_and_distances: collections.abc.Collection[ tuple[ ClientMediaResult.MediaResult, ClientMediaResult.MediaResult, int ] ] ):
        
        self._potential_media_result_pairs_and_distances = list( potential_media_result_pairs_and_distances )
        
    
    def __len__( self ):
        
        return len( self._potential_media_result_pairs_and_distances )
        
    
    def ABPairsUsingFastComparisonScore( self ):
        
        from hydrus.client.duplicates import ClientDuplicatesComparisonStatements
        
        new_potential_media_result_pairs_and_distances = []
        
        for ( media_result_1, media_result_2, distance ) in self._potential_media_result_pairs_and_distances:
            
            pair_score_12 = ClientDuplicatesComparisonStatements.GetDuplicateComparisonScoreFast( media_result_1, media_result_2 )
            
            if pair_score_12 > 0:
                
                new_tuple = ( media_result_1, media_result_2, distance )
                
            else:
                
                new_tuple = ( media_result_2, media_result_1, distance )
                
            
            new_potential_media_result_pairs_and_distances.append( new_tuple )
            
        
        self._potential_media_result_pairs_and_distances = new_potential_media_result_pairs_and_distances
        
    
    def AppendRow( self, row ):
        
        self._potential_media_result_pairs_and_distances.append( row )
        
    
    def Duplicate( self ) -> "PotentialDuplicateMediaResultPairsAndDistances":
        
        return PotentialDuplicateMediaResultPairsAndDistances( self._potential_media_result_pairs_and_distances )
        
    
    def IteratePairs( self ):
        
        for ( media_result_1, media_result_2, distance ) in self._potential_media_result_pairs_and_distances:
            
            yield ( media_result_1, media_result_2 )
            
        
    
    def IterateRows( self ):
        
        return self._potential_media_result_pairs_and_distances.__iter__()
        
    
    def GetPairs( self ) -> list[ tuple[ ClientMediaResult.MediaResult, ClientMediaResult.MediaResult ] ]:
        
        return [ ( media_result_1, media_result_2 ) for ( media_result_1, media_result_2, distance ) in self._potential_media_result_pairs_and_distances ]
        
    
    def GetRows( self ):
        
        return list( self._potential_media_result_pairs_and_distances )
        
    
    def Merge( self, potential_duplicate_media_result_pairs_and_distances: "PotentialDuplicateMediaResultPairsAndDistances" ):
        
        self._potential_media_result_pairs_and_distances.extend( potential_duplicate_media_result_pairs_and_distances.GetRows() )
        
    
    def Sort( self, duplicate_pair_sort_type: int, sort_asc: bool ):
        
        handle_invalid = lambda i: 1 if i is None or i == 0 else i
        
        if duplicate_pair_sort_type == ClientDuplicates.DUPE_PAIR_SORT_SIMILARITY:
            
            def sort_key( row: tuple[ ClientMediaResult.MediaResult, ClientMediaResult.MediaResult, int ] ):
                
                ( m_r_1, m_r_2, distance ) = row
                
                m_r_1_size = handle_invalid( m_r_1.GetSize() )
                m_r_2_size = handle_invalid( m_r_2.GetSize() )
                
                return ( distance, max( m_r_1_size, m_r_2_size ) / min( m_r_1_size, m_r_2_size ) )
                
            
        elif duplicate_pair_sort_type == ClientDuplicates.DUPE_PAIR_SORT_MAX_FILESIZE:
            
            def sort_key( row: tuple[ ClientMediaResult.MediaResult, ClientMediaResult.MediaResult, int ] ):
                
                ( m_r_1, m_r_2, distance ) = row
                
                m_r_1_size = handle_invalid( m_r_1.GetSize() )
                m_r_2_size = handle_invalid( m_r_2.GetSize() )
                
                return ( max( m_r_1_size, m_r_2_size ), min( m_r_1_size, m_r_2_size ) )
                
            
        elif duplicate_pair_sort_type == ClientDuplicates.DUPE_PAIR_SORT_MIN_FILESIZE:
            
            # what I would like auto-resolution to hook into, but I think it isn't easy to wangle
            
            def sort_key( row: tuple[ ClientMediaResult.MediaResult, ClientMediaResult.MediaResult, int ] ):
                
                ( m_r_1, m_r_2, distance ) = row
                
                m_r_1_size = handle_invalid( m_r_1.GetSize() )
                m_r_2_size = handle_invalid( m_r_2.GetSize() )
                
                return ( min( m_r_1_size, m_r_2_size ), max( m_r_1_size, m_r_2_size ) )
                
            
        elif duplicate_pair_sort_type == ClientDuplicates.DUPE_PAIR_SORT_RANDOM:
            
            random.shuffle( self._potential_media_result_pairs_and_distances )
            
            return
            
        else:
            
            raise NotImplementedError( 'Did not understand that duplicate sort!' )
            
        
        self._potential_media_result_pairs_and_distances.sort( key = sort_key )
        
        if not sort_asc:
            
            self._potential_media_result_pairs_and_distances.reverse()
            
        
    

POTENTIAL_PAIRS_REFRESH_TIMEOUT = 3600

class PotentialDuplicatePairsFragmentarySearch( object ):
    
    def __init__( self, potential_duplicates_search_context: "PotentialDuplicatesSearchContext", is_searching_full_space: bool ):
        
        self._potential_duplicates_search_context = potential_duplicates_search_context
        self._is_searching_full_space = is_searching_full_space
        
        self._search_space_fetch_started = False
        self._search_space_initialised = False
        self._search_space_initialised_time = 0.0
        
        self._potential_duplicate_id_pairs_and_distances_search_space = PotentialDuplicateIdPairsAndDistances( [] )
        self._potential_duplicate_id_pairs_and_distances_still_to_search = PotentialDuplicateIdPairsAndDistances( [] )
        self._potential_duplicate_id_pairs_and_distances_that_hit = PotentialDuplicateIdPairsAndDistances( [] )
        
        self._desired_num_hits = None
        
    
    def AddHits( self, matching_pairs_and_distances: tuple[ int, int, int ] ):
        
        self._potential_duplicate_id_pairs_and_distances_that_hit.AddRows( matching_pairs_and_distances )
        
    
    def DoingFileBasedSearchIsOK( self ):
        
        # don't do it for partial searches, and a sanity check
        return self._is_searching_full_space and self.NumPairsInSearchSpace() > 10000 and not self.ThereIsJustABitLeftBro() and CG.client_controller.new_options.GetBoolean( 'potential_duplicate_pairs_search_can_do_file_search_based_optimisation' )
        
    
    def EstimatedNumHits( self ):
        
        num_hits = len( self._potential_duplicate_id_pairs_and_distances_that_hit )
        num_searched = self.NumPairsSearched()
        
        if num_searched == 0:
            
            return 0
            
        
        estimate = int( num_hits * ( self.NumPairsInSearchSpace() / self.NumPairsSearched() ) )
        
        return estimate
        
    
    def EstimatedNumRowsStillToSearch( self ):
        
        num_still_to_search = self.NumPairsStillToSearch()
        
        num_hits = len( self._potential_duplicate_id_pairs_and_distances_that_hit )
        
        if self._desired_num_hits is not None and num_hits > 0:
            
            num_hits_still_to_get = self._desired_num_hits - num_hits
            
            if num_hits_still_to_get > 0:
                
                rows_per_hit = self.NumPairsSearched() / num_hits
                
                expected_remaining_rows_until_we_are_good = int( rows_per_hit * num_hits_still_to_get )
                
                return expected_remaining_rows_until_we_are_good
                
            
        
        return num_still_to_search
        
    
    def FilterWiderPotentialGroup( self, media_ids: collections.abc.Collection[ int ] ):
        
        group_potential_duplicate_id_pairs_and_distances = self._potential_duplicate_id_pairs_and_distances_search_space.FilterWiderPotentialGroup( media_ids )
        
        return { media_id for pair in group_potential_duplicate_id_pairs_and_distances.GetRows() for media_id in pair }
        
    
    def GetLocationContext( self ) -> ClientLocation.LocationContext:
        
        return self._potential_duplicates_search_context.GetLocationContext()
        
    
    def GetNumHits( self ) -> int:
        
        return len( self._potential_duplicate_id_pairs_and_distances_that_hit )
        
    
    def GetPotentialDuplicatesSearchContext( self ):
        
        return self._potential_duplicates_search_context
        
    
    def GetRelativeErrorAt95Certainty( self ):
        """
        How precise is the current search state for an estimate, 95% of the time?
        """
        
        # this is mostly AI vomit, but I'm generally there. 95% of <2.5%, simple as
        
        Z_CONFIDENCE = 1.9599639845 # 95% confidence
        
        def finite_population_correction( n: int, N: int ) -> float:
            """FPC multiplier for standard errors; 1 if N is None or n==0."""
            
            if n <= 1:
                
                return 1.0
                
            
            return math.sqrt((N - n) / (N - 1))
            
        
        def wilson_ci( x: int, n: int, z: float ) -> tuple[float, float]:
            """Wilson interval for p, clipped to [0,1]."""
            
            if n <= 0:
                
                return (0.0, 1.0)
                
            
            # Guard against invalid counts: Wilson assumes 0 <= x <= n
            if x < 0 or x > n:
                
                return (0.0, 1.0)
                
            
            phat = x / n
            z2 = z*z
            denom = 1 + z2/n
            center = phat + z2/(2*n)
            adj = z * math.sqrt(phat*(1-phat)/n + z2/(4*n*n))
            lo = max(0.0, (center - adj)/denom)
            hi = min(1.0, (center + adj)/denom)
            
            return ( lo, hi )
            
        
        def wilson_ci_with_fpc( x: int, n: int, z: float, N: int ) -> tuple[float, float]:
            """Apply FPC by shrinking the Wilson half-width (approximation)."""
            
            ( lo, hi ) = wilson_ci( x, n, z )
            mid = 0.5*(lo + hi)
            half = 0.5*(hi - lo)
            half *= finite_population_correction(n, N)
            
            return ( max( 0.0, mid - half ), min( 1.0, mid + half ) )
            
        
        def relative_halfwidth_from_counts( x: int, n: int, N: int ) -> float:
            """
            Returns rel_halfwidth where that is halfwidth / phat.
            If x==0 or n==0, rel_halfwidth is math.inf.
            """
            
            z = Z_CONFIDENCE
            
            ( lo, hi ) = wilson_ci_with_fpc( x, n, z, N )
            phat = x/n if n > 0 else 0.0
            half = 0.5*(hi - lo)
            rel = half / phat if phat > 0 else math.inf
            
            return rel
            
        
        x = len( self._potential_duplicate_id_pairs_and_distances_that_hit )
        n = self.NumPairsSearched()
        N = self.NumPairsInSearchSpace()
        
        if x > n: # something went wrong mate, didn't reset a count properly somewhere
            
            return 1.0
            
        
        if n == N:
            
            return 0.0
            
        
        rel = relative_halfwidth_from_counts( x, n, N )
        
        return rel
        
    
    def NotifyPotentialDuplicatePairsUpdate( self, update_type, *args ):
        
        if not self._search_space_initialised:
            
            return
            
        
        if update_type in ( PAIRS_UPDATE_ADD_ROWS, PAIRS_UPDATE_DELETE_PAIRS ):
            
            ( location_context, rows_of_data ) = args
            
            if location_context != self._potential_duplicates_search_context.GetLocationContext():
                
                return
                
            
        
        self._potential_duplicate_id_pairs_and_distances_search_space.NotifyPotentialDuplicatePairsUpdate( update_type, *args )
        self._potential_duplicate_id_pairs_and_distances_still_to_search.NotifyPotentialDuplicatePairsUpdate( update_type, *args )
        
        if update_type != PAIRS_UPDATE_ADD_ROWS:
            
            self._potential_duplicate_id_pairs_and_distances_that_hit.NotifyPotentialDuplicatePairsUpdate( update_type, *args )
            
        
    
    def NotifySearchSpaceFetchStarted( self ):
        
        self._search_space_fetch_started = True
        
    
    def NotifyWorkTimeForAutothrottle( self, actual_work_period: float, ideal_work_period: float ):
        
        self._potential_duplicate_id_pairs_and_distances_still_to_search.NotifyWorkTimeForAutothrottle( actual_work_period, ideal_work_period )
        
    
    def NumPairsInSearchSpace( self ):
        
        return len( self._potential_duplicate_id_pairs_and_distances_search_space )
        
    
    def NumPairsSearched( self ):
        
        return self.NumPairsInSearchSpace() - self.NumPairsStillToSearch()
        
    
    def NumPairsStillToSearch( self ):
        
        return len( self._potential_duplicate_id_pairs_and_distances_still_to_search )
        
    
    def PopBlock( self ):
        
        return self._potential_duplicate_id_pairs_and_distances_still_to_search.PopBlock()
        
    
    def PopRemaining( self ):
        
        result = self._potential_duplicate_id_pairs_and_distances_still_to_search.GetRows()
        
        self._potential_duplicate_id_pairs_and_distances_still_to_search = PotentialDuplicateIdPairsAndDistances( [] )
        
        return result
        
    
    def ResetSearchSpace( self ):
        
        self._potential_duplicate_id_pairs_and_distances_search_space = PotentialDuplicateIdPairsAndDistances( [] )
        self._potential_duplicate_id_pairs_and_distances_still_to_search = PotentialDuplicateIdPairsAndDistances( [] )
        self._potential_duplicate_id_pairs_and_distances_that_hit = PotentialDuplicateIdPairsAndDistances( [] )
        
        self._search_space_initialised = False
        self._search_space_fetch_started = False
        self._search_space_initialised_time = 0
        
    
    def SearchDone( self ):
        
        return self.NumPairsStillToSearch() == 0
        
    
    def SearchSpaceFetchStarted( self ):
        
        return self._search_space_fetch_started
        
    
    def SearchSpaceInitialised( self ) -> bool:
        
        return self._search_space_initialised
        
    
    def SearchSpaceIsEmpty( self ):
        
        return len( self._potential_duplicate_id_pairs_and_distances_search_space ) == 0
        
    
    def SearchSpaceIsStale( self ):
        
        return HydrusTime.TimeHasPassed( self._search_space_initialised_time + POTENTIAL_PAIRS_REFRESH_TIMEOUT )
        
    
    def SetDesiredNumHits( self, desired_num_hits: int ):
        
        self._desired_num_hits = desired_num_hits
        
    
    def SetPotentialDuplicatesSearchContext( self, potential_duplicates_search_context: "PotentialDuplicatesSearchContext" ):
        
        reset_search_space = self._potential_duplicates_search_context.GetLocationContext() != potential_duplicates_search_context.GetLocationContext()
        
        self._potential_duplicates_search_context = potential_duplicates_search_context
        
        if reset_search_space:
            
            self.ResetSearchSpace()
            
        
    
    def SetSearchSpace( self, potential_duplicate_id_pairs_and_distances: PotentialDuplicateIdPairsAndDistances ):
        
        if self._desired_num_hits is None and not self._is_searching_full_space:
            
            potential_duplicate_id_pairs_and_distances.RandomiseForFastSearch()
            
        else:
            
            potential_duplicate_id_pairs_and_distances.RandomiseForRichEstimate()
            
        
        self._potential_duplicate_id_pairs_and_distances_search_space = potential_duplicate_id_pairs_and_distances
        
        self._search_space_initialised = True
        self._search_space_fetch_started = False
        self._search_space_initialised_time = HydrusTime.GetNowFloat()
        
        self.StartNewSearch()
        
    
    def SpawnMediaIdFilteredSearch( self, media_ids ) -> "PotentialDuplicatePairsFragmentarySearch":
        
        my_copy = PotentialDuplicatePairsFragmentarySearch(
            self._potential_duplicates_search_context,
            False
        )
        
        potential_duplicate_id_pairs_and_distances_for_media_ids = self._potential_duplicate_id_pairs_and_distances_search_space.FilterWiderPotentialGroup( media_ids )
        
        my_copy.SetSearchSpace( potential_duplicate_id_pairs_and_distances_for_media_ids )
        
        return my_copy
        
    
    def SpawnNewSearch( self ) -> "PotentialDuplicatePairsFragmentarySearch":
        
        # we do this when the caller has a mix of async re-init and search work
        # spawning a new search ditches the old 'still to search', so we don't have to worry about an ongoing search messing with any new search space
        
        my_copy = PotentialDuplicatePairsFragmentarySearch(
            self._potential_duplicates_search_context,
            self._is_searching_full_space
        )
        
        if self._search_space_initialised:
            
            my_copy.SetSearchSpace( self._potential_duplicate_id_pairs_and_distances_search_space )
            
        else:
            
            my_copy.StartNewSearch()
            
        
        return my_copy
        
    
    def StartNewSearch( self ):
        
        self._potential_duplicate_id_pairs_and_distances_still_to_search = self._potential_duplicate_id_pairs_and_distances_search_space.Duplicate()
        
        self._potential_duplicate_id_pairs_and_distances_that_hit = PotentialDuplicateIdPairsAndDistances( [] )
        
    
    def ThereIsJustABitLeftBro( self ):
        
        # we are in a '1700 out of 1703 rows' situation. in this case we don't want any funny business--just do those last three
        
        num_in_search_space = self.NumPairsInSearchSpace()
        num_still_to_search = self.NumPairsStillToSearch()
        
        if num_still_to_search < 1024:
            
            return True
            
        
        if num_still_to_search < num_in_search_space * 0.05:
            
            return True
            
        
        return False
        
    
    def ThisAppearsToHaveAHitRateLowerThan( self, percentage_float ):
        
        # 95%, but one-sided
        ONE_SIDED_Z_CONFIDENCE = 1.6448536269
        ONE_SIDED_Z_SQUARED = 2.7055434539
        
        def wilson_upper_one_sided():
            
            z = ONE_SIDED_Z_CONFIDENCE
            z_squared = ONE_SIDED_Z_SQUARED
            
            p_hat = x / n if n else 0.0
            
            # variance term with optional finite-population correction
            var = (p_hat * (1 - p_hat) / n) * ( (N - n)/(N - 1) if (N > 1 and n > 0) else 1.0 )
            
            den = 1.0 + z_squared/n
            
            num = p_hat + z_squared/(2*n) + z*math.sqrt(var + z_squared/(4*n**2))
            
            U = num / den
            
            return U # We are 95% confident the hitrate will be below this
            
        
        x = len( self._potential_duplicate_id_pairs_and_distances_that_hit )
        n = self.NumPairsSearched()
        N = self.NumPairsInSearchSpace()
        
        if n == 0:
            
            return False
            
        
        U = wilson_upper_one_sided()
        
        return U < percentage_float
        
    

class PotentialDuplicatesSearchContext( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_POTENTIAL_DUPLICATES_SEARCH_CONTEXT
    SERIALISABLE_NAME = 'Potential Duplicates Search Context'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, location_context: ClientLocation.LocationContext | None = None, initial_predicates = None ):
        
        if location_context is None:
            
            try:
                
                location_context = CG.client_controller.new_options.GetDefaultLocalLocationContext()
                
            except Exception as e:
                
                location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY )
                
            
        
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
        
        self._file_search_context_1: ClientSearchFileSearchContext.FileSearchContext = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_search_context_1 )
        self._file_search_context_2: ClientSearchFileSearchContext.FileSearchContext = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_search_context_2 )
        
    
    def GetDupeSearchType( self ) -> int:
        
        return self._dupe_search_type
        
    
    def GetFileSearchContext1( self ) -> ClientSearchFileSearchContext.FileSearchContext:
        
        return self._file_search_context_1
        
    
    def GetFileSearchContext2( self ) -> ClientSearchFileSearchContext.FileSearchContext:
        
        return self._file_search_context_2
        
    
    def GetLocationContext( self ) -> ClientLocation.LocationContext:
        
        return self._file_search_context_1.GetLocationContext()
        
    
    def GetMaxHammingDistance( self ) -> int:
        
        return self._max_hamming_distance
        
    
    def GetPixelDupesPreference( self ) -> int:
        
        return self._pixel_dupes_preference
        
    
    def GetSummary( self ) -> str:
        
        components = []
        
        if self._pixel_dupes_preference == ClientDuplicates.SIMILAR_FILES_PIXEL_DUPES_REQUIRED:
            
            components.append( 'pixel duplicates' )
            
        elif self._pixel_dupes_preference == ClientDuplicates.SIMILAR_FILES_PIXEL_DUPES_EXCLUDED:
            
            components.append( 'not pixel duplicates' )
            
        
        if self._dupe_search_type == ClientDuplicates.DUPE_SEARCH_BOTH_FILES_MATCH_DIFFERENT_SEARCHES:
            
            components.append( f'files matching [{self._file_search_context_1.GetSummary()}] and [{self._file_search_context_2.GetSummary()}]' )
            
        elif self._dupe_search_type == ClientDuplicates.DUPE_SEARCH_BOTH_FILES_MATCH_ONE_SEARCH:
            
            components.append( f'both files matching [{self._file_search_context_1.GetSummary()}]' )
            
        else:
            
            components.append( f'one file matching [{self._file_search_context_1.GetSummary()}]' )
            
        
        if self._pixel_dupes_preference != ClientDuplicates.SIMILAR_FILES_PIXEL_DUPES_REQUIRED:
            
            components.append( f'max search distance: {self._max_hamming_distance}' )
            
        
        return ', '.join( components )
        
    
    def GetTagContext( self ) -> ClientSearchTagContext.TagContext:
        
        return self._file_search_context_1.GetTagContext()
        
    
    def OptimiseForSearch( self ):
        
        if self._dupe_search_type == ClientDuplicates.DUPE_SEARCH_BOTH_FILES_MATCH_ONE_SEARCH and ( self._file_search_context_1.IsJustSystemEverything() or self._file_search_context_1.HasNoPredicates() ):
            
            self._dupe_search_type = ClientDuplicates.DUPE_SEARCH_ONE_FILE_MATCHES_ONE_SEARCH
            
        elif self._dupe_search_type == ClientDuplicates.DUPE_SEARCH_BOTH_FILES_MATCH_DIFFERENT_SEARCHES:
            
            if self._file_search_context_1.IsJustSystemEverything() or self._file_search_context_1.HasNoPredicates():
                
                ( self._file_search_context_2, self._file_search_context_1 ) = ( self._file_search_context_1, self._file_search_context_2 )
                
                self._dupe_search_type = ClientDuplicates.DUPE_SEARCH_ONE_FILE_MATCHES_ONE_SEARCH
                
            elif self._file_search_context_2.IsJustSystemEverything() or self._file_search_context_2.HasNoPredicates():
                
                self._dupe_search_type = ClientDuplicates.DUPE_SEARCH_ONE_FILE_MATCHES_ONE_SEARCH
                
            
        
    
    def SetDupeSearchType( self, value: int ):
        
        self._dupe_search_type = value
        
    
    def SetFileSearchContext1( self, value: ClientSearchFileSearchContext.FileSearchContext ):
        
        self._file_search_context_1 = value
        
    
    def SetFileSearchContext2( self, value: ClientSearchFileSearchContext.FileSearchContext ):
        
        self._file_search_context_2 = value
        
    
    def SetMaxHammingDistance( self, value : int ):
        
        self._max_hamming_distance = value
        
    
    def SetPixelDupesPreference( self, value : int ):
        
        self._pixel_dupes_preference = value
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_POTENTIAL_DUPLICATES_SEARCH_CONTEXT ] = PotentialDuplicatesSearchContext
