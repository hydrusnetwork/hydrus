import random

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusTime

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientLocation
from hydrus.client.duplicates import ClientDuplicatesAutoResolution
from hydrus.client.duplicates import ClientPotentialDuplicatesSearchContext
from hydrus.client.media import ClientMediaResult
from hydrus.client.metadata import ClientContentUpdates

class DuplicatePairDecision( object ):
    
    def __init__( self, media_result_a: ClientMediaResult.MediaResult, media_result_b: ClientMediaResult.MediaResult ):
        
        self.media_result_a = media_result_a
        self.media_result_b = media_result_b
        
    
    def HasWorkToDo( self ):
        
        return True
        
    

class DuplicatePairDecisionSkip( DuplicatePairDecision ):
    
    def HasWorkToDo( self ):
        
        return False
        
    

class DuplicatePairDecisionSkipManual( DuplicatePairDecisionSkip ):
    
    pass
    

class DuplicatePairDecisionSkipAuto( DuplicatePairDecisionSkip ):
    
    pass
    

class DuplicatePairDecisionDuplicatesAction( DuplicatePairDecision ):
    
    def __init__(
        self,
        media_result_a: ClientMediaResult.MediaResult,
        media_result_b: ClientMediaResult.MediaResult,
        duplicate_type: int,
        content_update_packages: list[ ClientContentUpdates.ContentUpdatePackage ]
    ):
        
        self.duplicate_type = duplicate_type
        self.content_update_packages = content_update_packages
        
        super().__init__( media_result_a, media_result_b )
        
    

class DuplicatePairDecisionDeletion( DuplicatePairDecision ):
    
    def __init__(
        self,
        media_result_a: ClientMediaResult.MediaResult,
        media_result_b: ClientMediaResult.MediaResult,
        content_update_packages: list[ ClientContentUpdates.ContentUpdatePackage ]
    ):
        
        # I seem to remember we had a place where it would have been useful to consult this action for which files were hit. maybe we want to push the content update package generation down or preserve a/b deletion bools here?
        
        self.content_update_packages = content_update_packages
        
        super().__init__( media_result_a, media_result_b )
        
    

class DuplicatePairDecisionApproveDeny( DuplicatePairDecision ):
    
    def __init__(
        self,
        media_result_a: ClientMediaResult.MediaResult,
        media_result_b: ClientMediaResult.MediaResult,
        approved: bool
    ):
        
        self.approved = approved
        
        super().__init__( media_result_a, media_result_b )
        
    

class PotentialDuplicatePairFactory( object ):
    
    def DoInitialisationWork( self ) -> bool:
        
        return True
        
    
    def DoSearchWork( self, *args ) -> bool:
        
        return True
        
    
    def GetFirstSecondLabels( self ):
        
        return ( 'File One', 'File Two' )
        
    
    def GetLocationContext( self ) -> ClientLocation.LocationContext:
        
        raise NotImplementedError()
        
    
    def GetPotentialDuplicateMediaResultPairsAndDistances( self ) -> ClientPotentialDuplicatesSearchContext.PotentialDuplicateMediaResultPairsAndDistances:
        
        raise NotImplementedError()
        
    
    def GetWorkStatus( self ) -> str:
        
        return 'No pre-work needed'
        
    
    def InitialisationWorkLooksGood( self ):
        
        return True
        
    
    def InitialisationWorkNeeded( self ) -> bool:
        
        return False
        
    
    def InitialisationWorkStarted( self ) -> bool:
        
        return False
        
    
    def NotifyCommitDone( self ):
        
        pass
        
    
    def NotifyInitialisationWorkStarted( self ):
        
        pass
        
    
    def NotifyInitialisationWorkFinished( self ):
        
        pass
        
    
    def NotifyFetchMorePairs( self ):
        
        pass
        
    
    def SearchWorkIsDone( self ) -> bool:
        
        return True
        
    
    def SortAndABPairs( self ):
        
        pass
        
    

class PotentialDuplicatePairFactoryDB( PotentialDuplicatePairFactory ):
    
    def __init__( self, potential_duplicates_search_context: ClientPotentialDuplicatesSearchContext.PotentialDuplicatesSearchContext, duplicate_pair_sort_type: int, duplicate_pair_sort_asc: bool ):
        
        self._potential_duplicate_pairs_fragmentary_search = ClientPotentialDuplicatesSearchContext.PotentialDuplicatePairsFragmentarySearch( potential_duplicates_search_context, True )
        self._duplicate_pair_sort_type = duplicate_pair_sort_type
        self._duplicate_pair_sort_asc = duplicate_pair_sort_asc
        
        self._fetched_media_result_pairs_and_distances = ClientPotentialDuplicatesSearchContext.PotentialDuplicateMediaResultPairsAndDistances( [] )
        
    
    def DoInitialisationWork( self ) -> bool:
        
        location_context = self._potential_duplicate_pairs_fragmentary_search.GetPotentialDuplicatesSearchContext().GetFileSearchContext1().GetLocationContext()
        
        potential_duplicate_id_pairs_and_distances: ClientPotentialDuplicatesSearchContext.PotentialDuplicateIdPairsAndDistances = CG.client_controller.Read( 'potential_duplicate_id_pairs_and_distances', location_context )
        
        self._potential_duplicate_pairs_fragmentary_search.SetSearchSpace( potential_duplicate_id_pairs_and_distances )
        
        return True
        
    
    def GetLocationContext( self ) -> ClientLocation.LocationContext:
        
        return self._potential_duplicate_pairs_fragmentary_search.GetPotentialDuplicatesSearchContext().GetFileSearchContext1().GetLocationContext()
        
    
    def GetPotentialDuplicateMediaResultPairsAndDistances( self ) -> ClientPotentialDuplicatesSearchContext.PotentialDuplicateMediaResultPairsAndDistances:
        
        return self._fetched_media_result_pairs_and_distances
        
    
    def InitialisationWorkLooksGood( self ):
        
        if not self._potential_duplicate_pairs_fragmentary_search.SearchSpaceInitialised():
            
            raise Exception( 'Was asked about initialisation before it happened!' )
            
        
        return self._potential_duplicate_pairs_fragmentary_search.NumPairsInSearchSpace() > 0
        
    
    def InitialisationWorkNeeded( self ) -> bool:
        
        return not self._potential_duplicate_pairs_fragmentary_search.SearchSpaceInitialised()
        
    
    def InitialisationWorkStarted( self ) -> bool:
        
        return self._potential_duplicate_pairs_fragmentary_search.SearchSpaceFetchStarted()
        
    
    def NotifyCommitDone( self ):
        
        # unfortunate, but the old value is now invalid since we are about to change things
        # we may have knocked out potentials without merging media ids (set alternate) or, more rarely, added new potentials from merge inheritance
        self._potential_duplicate_pairs_fragmentary_search.ResetSearchSpace()
        
        self.NotifyFetchMorePairs()
        
    
    def NotifyInitialisationWorkStarted( self ):
        
        self._potential_duplicate_pairs_fragmentary_search.NotifySearchSpaceFetchStarted()
        
    
    def NotifyInitialisationWorkFinished( self ):
        
        pass # done in the fragmentary search when the search space is set
        
    
    def NotifyFetchMorePairs( self ):
        
        self._potential_duplicate_pairs_fragmentary_search = self._potential_duplicate_pairs_fragmentary_search.SpawnNewSearch()
        
        self._fetched_media_result_pairs_and_distances = ClientPotentialDuplicatesSearchContext.PotentialDuplicateMediaResultPairsAndDistances( [] )
        
    
    def SortAndABPairs( self ):
        
        self._fetched_media_result_pairs_and_distances.Sort( self._duplicate_pair_sort_type, self._duplicate_pair_sort_asc )
        
        self._fetched_media_result_pairs_and_distances.ABPairsUsingFastComparisonScore()
        
    

class PotentialDuplicatePairFactoryDBGroupMode( PotentialDuplicatePairFactoryDB ):
    
    def __init__( self, potential_duplicates_search_context: ClientPotentialDuplicatesSearchContext.PotentialDuplicatesSearchContext, duplicate_pair_sort_type: int, duplicate_pair_sort_asc: bool ):
        
        super().__init__( potential_duplicates_search_context, duplicate_pair_sort_type, duplicate_pair_sort_asc )
        
        # do not reset group media ids to set() in notifypreparenewbatch! we want to re-run groups over and over until they are empty
        self._group_media_ids = set()
        
    
    def DoSearchWork( self, *args ) -> bool:
        
        if len( self._group_media_ids ) == 0:
            
            # no group yet, so let's look for one
            
            if self._potential_duplicate_pairs_fragmentary_search.SearchDone():
                
                # shouldn't be able to get here
                
                return False
                
            
            # ok let's find a group if poss
            
            start_time = HydrusTime.GetNowPrecise()
            
            probing_potential_duplicate_media_result_pairs_and_distances = CG.client_controller.Read( 'potential_duplicate_id_pairs_and_distances_fragmentary', self._potential_duplicate_pairs_fragmentary_search )
            
            actual_work_period = HydrusTime.GetNowPrecise() - start_time
            
            self._potential_duplicate_pairs_fragmentary_search.NotifyWorkTimeForAutothrottle( actual_work_period, 0.5 )
            
            if len( probing_potential_duplicate_media_result_pairs_and_distances ) == 0:
                
                pass # no luck this time; make no changes and try again
                
            else:
                
                # we found one
                pairs = list( probing_potential_duplicate_media_result_pairs_and_distances.GetPairs() )
                
                pair = random.choice( pairs )
                
                self._group_media_ids = self._potential_duplicate_pairs_fragmentary_search.FilterWiderPotentialGroup( pair )
                
            
        else:
            
            group_fragmentary_search = self._potential_duplicate_pairs_fragmentary_search.SpawnMediaIdFilteredSearch( self._group_media_ids )
            
            self._fetched_media_result_pairs_and_distances: ClientPotentialDuplicatesSearchContext.PotentialDuplicateMediaResultPairsAndDistances = CG.client_controller.Read( 'potential_duplicate_media_result_pairs_and_distances', group_fragmentary_search )
            
            if len( self._fetched_media_result_pairs_and_distances ) == 0:
                
                # this group is now exhausted; we need to fetch a new one
                
                self.SelectNewGroup()
                
            
        
        return True
        
    
    def GetWorkStatus( self ) -> str:
        
        if self.SearchWorkIsDone():
            
            loading_text = 'Search is done!'
            
        else:
            
            if len( self._group_media_ids ) == 0:
                
                value = self._potential_duplicate_pairs_fragmentary_search.NumPairsSearched()
                range = self._potential_duplicate_pairs_fragmentary_search.NumPairsInSearchSpace()
                
                loading_text = f'Searching for group; {HydrusNumbers.ValueRangeToPrettyString(value, range)} pairs searched{HC.UNICODE_ELLIPSIS}'
                
            else:
                
                loading_text = f'Group found; loading{HC.UNICODE_ELLIPSIS}'
                
            
        
        return loading_text
        
    
    def SearchWorkIsDone( self ) -> bool:
        
        have_results = len( self._fetched_media_result_pairs_and_distances ) > 0
        found_nothing = self._potential_duplicate_pairs_fragmentary_search.SearchDone() and len( self._group_media_ids ) == 0
        
        return have_results or found_nothing
        
    
    def SelectNewGroup( self ):
        
        self._group_media_ids = set()
        
        self.NotifyFetchMorePairs()
        
    

class PotentialDuplicatePairFactoryDBMixed( PotentialDuplicatePairFactoryDB ):
    
    def __init__( self, potential_duplicates_search_context: ClientPotentialDuplicatesSearchContext.PotentialDuplicatesSearchContext, duplicate_pair_sort_type: int, duplicate_pair_sort_asc: bool, no_more_than: int ):
        
        super().__init__( potential_duplicates_search_context, duplicate_pair_sort_type, duplicate_pair_sort_asc )
        
        self._no_more_than = no_more_than
        
        self._potential_duplicate_pairs_fragmentary_search.SetDesiredNumHits( self._no_more_than )
        
    
    def DoSearchWork( self, *args ) -> bool:
        
        start_time = HydrusTime.GetNowPrecise()
        
        potential_duplicate_media_result_pairs_and_distances = CG.client_controller.Read( 'potential_duplicate_media_result_pairs_and_distances_fragmentary', self._potential_duplicate_pairs_fragmentary_search, no_more_than = self._no_more_than )
        
        actual_work_period = HydrusTime.GetNowPrecise() - start_time
        
        self._potential_duplicate_pairs_fragmentary_search.NotifyWorkTimeForAutothrottle( actual_work_period, 0.5 )
        
        for row in potential_duplicate_media_result_pairs_and_distances.IterateRows():
            
            self._fetched_media_result_pairs_and_distances.AppendRow( row )
            
            if len( self._fetched_media_result_pairs_and_distances ) >= self._no_more_than:
                
                break
                
            
        
        return True
        
    
    def GetWorkStatus( self ) -> str:
        
        if self.SearchWorkIsDone():
            
            loading_text = 'Search is done!'
            
        else:
            
            value = self._potential_duplicate_pairs_fragmentary_search.NumPairsSearched()
            range = self._potential_duplicate_pairs_fragmentary_search.NumPairsInSearchSpace()
            
            loading_text = f'{HydrusNumbers.ValueRangeToPrettyString(value, range)} pairs searched; {HydrusNumbers.ToHumanInt( len( self._fetched_media_result_pairs_and_distances ) )} matched{HC.UNICODE_ELLIPSIS}'
            
        
        return loading_text
        
    
    def SearchWorkIsDone( self ):
        
        search_exhausted = self._potential_duplicate_pairs_fragmentary_search.SearchDone()
        
        we_have_enough = len( self._fetched_media_result_pairs_and_distances ) >= self._no_more_than
        
        return search_exhausted or we_have_enough
        
    

class PotentialDuplicatePairFactoryMediaResults( PotentialDuplicatePairFactory ):
    
    def __init__( self, potential_duplicate_media_result_pairs_and_distances: ClientPotentialDuplicatesSearchContext.PotentialDuplicateMediaResultPairsAndDistances ):
        
        self._potential_duplicate_media_result_pairs_and_distances = potential_duplicate_media_result_pairs_and_distances
        
    
    def GetFirstSecondLabels( self ):
        
        return ( 'A', 'B' )
        
    
    def GetLocationContext( self ) -> ClientLocation.LocationContext:
        
        return ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY )
        
    
    def GetPotentialDuplicateMediaResultPairsAndDistances( self ) -> ClientPotentialDuplicatesSearchContext.PotentialDuplicateMediaResultPairsAndDistances:
        
        return self._potential_duplicate_media_result_pairs_and_distances.Duplicate()
        
    
    def NotifyCommitDone( self ):
        
        self._potential_duplicate_media_result_pairs_and_distances = ClientPotentialDuplicatesSearchContext.PotentialDuplicateMediaResultPairsAndDistances( [] )
        
    
    def SortAndABPairs( self ):
        
        # leaving this as pass just so I can comment
        # not only is the sort pre-defined, but the AB order is also!
        pass
        
    

class PotentialDuplicatePairFactoryAutoResolutionReview( PotentialDuplicatePairFactoryMediaResults ):
    
    def __init__( self, potential_duplicate_media_result_pairs_and_distances: ClientPotentialDuplicatesSearchContext.PotentialDuplicateMediaResultPairsAndDistances, auto_resolution_rule: ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule ):
        
        self._auto_resolution_rule = auto_resolution_rule
        
        super().__init__( potential_duplicate_media_result_pairs_and_distances )
        
    
    def GetRule( self ):
        
        return self._auto_resolution_rule
        
    
