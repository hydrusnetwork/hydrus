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
        
        self._potential_duplicates_search_context = potential_duplicates_search_context
        self._duplicate_pair_sort_type = duplicate_pair_sort_type
        self._duplicate_pair_sort_asc = duplicate_pair_sort_asc
        
        self._potential_duplicate_id_pairs_and_distances = ClientPotentialDuplicatesSearchContext.PotentialDuplicateIdPairsAndDistances( [] )
        self._potential_duplicate_id_pairs_and_distances_initialised = False
        self._potential_duplicate_id_pairs_and_distances_fetch_started = False
        
        self._potential_duplicate_id_pairs_and_distances_still_to_search = ClientPotentialDuplicatesSearchContext.PotentialDuplicateIdPairsAndDistances( [] )
        
        self._fetched_media_result_pairs_and_distances = ClientPotentialDuplicatesSearchContext.PotentialDuplicateMediaResultPairsAndDistances( [] )
        
    
    def DoInitialisationWork( self ) -> bool:
        
        location_context = self._potential_duplicates_search_context.GetFileSearchContext1().GetLocationContext()
        
        potential_duplicate_id_pairs_and_distances: ClientPotentialDuplicatesSearchContext.PotentialDuplicateIdPairsAndDistances = CG.client_controller.Read( 'potential_duplicate_id_pairs_and_distances', location_context )
        
        # ok randomise the order we'll do this guy, but only at the block level
        # we'll preserve order each block came in since we'll then keep db-proximal indices close together on each actual block fetch
        potential_duplicate_id_pairs_and_distances.RandomiseBlocks()
        
        self._potential_duplicate_id_pairs_and_distances = potential_duplicate_id_pairs_and_distances
        
        return True
        
    
    def GetLocationContext( self ) -> ClientLocation.LocationContext:
        
        return self._potential_duplicates_search_context.GetFileSearchContext1().GetLocationContext()
        
    
    def GetPotentialDuplicateMediaResultPairsAndDistances( self ) -> ClientPotentialDuplicatesSearchContext.PotentialDuplicateMediaResultPairsAndDistances:
        
        return self._fetched_media_result_pairs_and_distances
        
    
    def InitialisationWorkLooksGood( self ):
        
        if not self._potential_duplicate_id_pairs_and_distances_initialised:
            
            raise Exception( 'Was asked about initialisation before it happened!' )
            
        
        return len( self._potential_duplicate_id_pairs_and_distances ) > 0
        
    
    def InitialisationWorkNeeded( self ) -> bool:
        
        return not self._potential_duplicate_id_pairs_and_distances_initialised
        
    
    def InitialisationWorkStarted( self ) -> bool:
        
        return self._potential_duplicate_id_pairs_and_distances_fetch_started
        
    
    def NotifyCommitDone( self ):
        
        # unfortunate, but the old value is now invalid since we are about to change things
        # we may have knocked out potentials without merging media ids (set alternate) or, more rarely, added new potentials from merge inheritance
        self._potential_duplicate_id_pairs_and_distances = ClientPotentialDuplicatesSearchContext.PotentialDuplicateIdPairsAndDistances( [] )
        self._potential_duplicate_id_pairs_and_distances_initialised = False
        
        self.NotifyFetchMorePairs()
        
    
    def NotifyInitialisationWorkStarted( self ):
        
        self._potential_duplicate_id_pairs_and_distances_fetch_started = True
        
    
    def NotifyInitialisationWorkFinished( self ):
        
        self._potential_duplicate_id_pairs_and_distances_initialised = True
        self._potential_duplicate_id_pairs_and_distances_fetch_started = False
        
    
    def NotifyFetchMorePairs( self ):
        
        self._potential_duplicate_id_pairs_and_distances_still_to_search = self._potential_duplicate_id_pairs_and_distances.Duplicate()
        
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
            
            if len( self._potential_duplicate_id_pairs_and_distances_still_to_search ) == 0:
                
                # shouldn't be able to get here
                
                return False
                
            
            block_of_id_pairs_and_distances = self._potential_duplicate_id_pairs_and_distances_still_to_search.PopBlock()
            
            # ok let's find a group if poss
            
            start_time = HydrusTime.GetNowPrecise()
            
            probing_potential_duplicate_media_result_pairs_and_distances = CG.client_controller.Read( 'potential_duplicate_id_pairs_and_distances_fragmentary', self._potential_duplicates_search_context, block_of_id_pairs_and_distances )
            
            actual_work_period = HydrusTime.GetNowPrecise() - start_time
            
            self._potential_duplicate_id_pairs_and_distances_still_to_search.NotifyWorkTimeForAutothrottle( actual_work_period, 0.5 )
            
            if len( probing_potential_duplicate_media_result_pairs_and_distances ) == 0:
                
                pass # no luck this time; make no changes and try again
                
            else:
                
                # we found one
                pairs = list( probing_potential_duplicate_media_result_pairs_and_distances.GetPairs() )
                
                pair = random.choice( pairs )
                
                group_potential_duplicate_id_pairs_and_distances = self._potential_duplicate_id_pairs_and_distances.FilterWiderPotentialGroup( pair )
                
                self._group_media_ids = { media_id for pair in group_potential_duplicate_id_pairs_and_distances.GetRows() for media_id in pair }
                
            
        else:
            
            # ok we have a group; we want to re-fetch it
            group_potential_duplicate_id_pairs_and_distances = self._potential_duplicate_id_pairs_and_distances.FilterWiderPotentialGroup( self._group_media_ids )
            
            self._fetched_media_result_pairs_and_distances = CG.client_controller.Read( 'potential_duplicate_media_result_pairs_and_distances_fragmentary', self._potential_duplicates_search_context, group_potential_duplicate_id_pairs_and_distances )
            
            if len( self._fetched_media_result_pairs_and_distances ) == 0:
                
                # this group is now exhausted; we need to fetch a new one
                
                self.SelectNewGroup()
                
            
        
        return True
        
    
    def GetWorkStatus( self ) -> str:
        
        if self.SearchWorkIsDone():
            
            loading_text = 'Search is done!'
            
        else:
            
            if len( self._group_media_ids ) == 0:
                
                value = len( self._potential_duplicate_id_pairs_and_distances ) - len( self._potential_duplicate_id_pairs_and_distances_still_to_search )
                range = len( self._potential_duplicate_id_pairs_and_distances )
                
                loading_text = f'Searching for group; {HydrusNumbers.ValueRangeToPrettyString(value, range)} pairs searched{HC.UNICODE_ELLIPSIS}'
                
            else:
                
                loading_text = f'Group found; loading{HC.UNICODE_ELLIPSIS}'
                
            
        
        return loading_text
        
    
    def SearchWorkIsDone( self ) -> bool:
        
        have_results = len( self._fetched_media_result_pairs_and_distances ) > 0
        found_nothing = len( self._potential_duplicate_id_pairs_and_distances_still_to_search ) == 0 and len( self._group_media_ids ) == 0
        
        return have_results or found_nothing
        
    
    def SelectNewGroup( self ):
        
        self._group_media_ids = set()
        
        self.NotifyFetchMorePairs()
        
    

class PotentialDuplicatePairFactoryDBMixed( PotentialDuplicatePairFactoryDB ):
    
    def __init__( self, potential_duplicates_search_context: ClientPotentialDuplicatesSearchContext.PotentialDuplicatesSearchContext, duplicate_pair_sort_type: int, duplicate_pair_sort_asc: bool, no_more_than: int ):
        
        super().__init__( potential_duplicates_search_context, duplicate_pair_sort_type, duplicate_pair_sort_asc )
        
        self._no_more_than = no_more_than
        
    
    def DoSearchWork( self, *args ) -> bool:
        
        block_of_id_pairs_and_distances = self._potential_duplicate_id_pairs_and_distances_still_to_search.PopBlock()
        
        start_time = HydrusTime.GetNowPrecise()
        
        potential_duplicate_media_result_pairs_and_distances = CG.client_controller.Read( 'potential_duplicate_media_result_pairs_and_distances_fragmentary', self._potential_duplicates_search_context, block_of_id_pairs_and_distances, no_more_than = self._no_more_than )
        
        actual_work_period = HydrusTime.GetNowPrecise() - start_time
        
        self._potential_duplicate_id_pairs_and_distances_still_to_search.NotifyWorkTimeForAutothrottle( actual_work_period, 0.5 )
        
        for row in potential_duplicate_media_result_pairs_and_distances.IterateRows():
            
            self._fetched_media_result_pairs_and_distances.AppendRow( row )
            
            if len( self._fetched_media_result_pairs_and_distances ) >= self._no_more_than:
                
                break
                
            
        
        return True
        
    
    def GetWorkStatus( self ) -> str:
        
        if self.SearchWorkIsDone():
            
            loading_text = 'Search is done!'
            
        else:
            
            value = len( self._potential_duplicate_id_pairs_and_distances ) - len( self._potential_duplicate_id_pairs_and_distances_still_to_search )
            range = len( self._potential_duplicate_id_pairs_and_distances )
            
            loading_text = f'{HydrusNumbers.ValueRangeToPrettyString(value, range)} pairs searched; {HydrusNumbers.ToHumanInt( len( self._fetched_media_result_pairs_and_distances ) )} matched{HC.UNICODE_ELLIPSIS}'
            
        
        return loading_text
        
    
    def SearchWorkIsDone( self ):
        
        search_exhausted = len( self._potential_duplicate_id_pairs_and_distances_still_to_search ) == 0
        
        we_have_enough = len( self._fetched_media_result_pairs_and_distances ) >= self._no_more_than
        
        return search_exhausted or we_have_enough
        
    

class PotentialDuplicatePairFactoryMediaResults( PotentialDuplicatePairFactory ):
    
    def __init__( self, potential_duplicate_media_result_pairs_and_distances: ClientPotentialDuplicatesSearchContext.PotentialDuplicateMediaResultPairsAndDistances ):
        
        self._potential_duplicate_media_result_pairs_and_distances = potential_duplicate_media_result_pairs_and_distances
        
    
    def GetFirstSecondLabels( self ):
        
        return ( 'A', 'B' )
        
    
    def GetLocationContext( self ) -> ClientLocation.LocationContext:
        
        return ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY )
        
    
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
        
    
