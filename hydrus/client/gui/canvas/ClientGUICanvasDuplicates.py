import collections.abc
import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusTime

from hydrus.client import ClientApplicationCommand as CAC
from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientServices
from hydrus.client import ClientThreading
from hydrus.client.duplicates import ClientDuplicatesAutoResolution
from hydrus.client.duplicates import ClientDuplicates
from hydrus.client.duplicates import ClientDuplicatesComparisonStatements
from hydrus.client.duplicates import ClientPotentialDuplicatesPairFactory
from hydrus.client.gui import ClientGUIAsync
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui.canvas import ClientGUICanvasHoverFrames
from hydrus.client.gui.canvas import ClientGUICanvasMedia
from hydrus.client.gui.canvas import ClientGUICanvas
from hydrus.client.gui.duplicates import ClientGUIDuplicatesContentMergeOptions
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.panels import ClientGUIScrolledPanelsCommitFiltering
from hydrus.client.media import ClientMedia
from hydrus.client.metadata import ClientContentUpdates

def CommitDecision(
    potential_duplicate_pair_factory: ClientPotentialDuplicatesPairFactory.PotentialDuplicatePairFactory,
    duplicate_pair_decision: ClientPotentialDuplicatesPairFactory.DuplicatePairDecision
):
    
    if isinstance( duplicate_pair_decision, ClientPotentialDuplicatesPairFactory.DuplicatePairDecisionDeletion ):
        
        content_update_packages = duplicate_pair_decision.content_update_packages
        
        if len( content_update_packages ) > 0:
            
            for content_update_package in content_update_packages:
                
                CG.client_controller.WriteSynchronous( 'content_updates', content_update_package )
                
            
        
    elif isinstance( potential_duplicate_pair_factory, ClientPotentialDuplicatesPairFactory.PotentialDuplicatePairFactoryAutoResolutionReview ) and isinstance( duplicate_pair_decision, ClientPotentialDuplicatesPairFactory.DuplicatePairDecisionApproveDeny ):
        
        rule = potential_duplicate_pair_factory.GetRule()
        
        ClientDuplicatesAutoResolution.ActionAutoResolutionReviewPairs( rule, ( duplicate_pair_decision, ) )
        
    elif isinstance( duplicate_pair_decision, ClientPotentialDuplicatesPairFactory.DuplicatePairDecisionDuplicatesAction ):
        
        info_tuple = (
            duplicate_pair_decision.duplicate_type,
            duplicate_pair_decision.media_result_a.GetHash(),
            duplicate_pair_decision.media_result_b.GetHash(),
            duplicate_pair_decision.content_update_packages
        )
        
        CG.client_controller.WriteSynchronous( 'duplicate_pair_status', ( info_tuple, ) )
        
    

def THREADCommitDuplicatePairDecisions(
    potential_duplicate_pair_factory: ClientPotentialDuplicatesPairFactory.PotentialDuplicatePairFactory,
    duplicate_pair_decisions: list[ ClientPotentialDuplicatesPairFactory.DuplicatePairDecision ]
):
    
    start_time = HydrusTime.GetNowFloat()
    
    job_status = ClientThreading.JobStatus()
    have_published_job_status = False
    
    job_status.SetStatusTitle( 'committing duplicate decisions' )
    
    num_to_do = len( duplicate_pair_decisions )
    
    for ( i, duplicate_pair_decision ) in enumerate( duplicate_pair_decisions ):
        
        if not have_published_job_status and HydrusTime.TimeHasPassedFloat( start_time + 1 ):
            
            CG.client_controller.pub( 'message', job_status )
            
            have_published_job_status = True
            
        
        num_done = i
        
        job_status.SetStatusText( f'decisions: {HydrusNumbers.ValueRangeToPrettyString( num_done, num_to_do )}' )
        job_status.SetGauge( num_done, num_to_do )
        
        CommitDecision( potential_duplicate_pair_factory, duplicate_pair_decision )
        
    
    job_status.FinishAndDismiss()
    
    CG.client_controller.pub( 'new_similar_files_potentials_search_numbers' )
    CG.client_controller.pub( 'notify_duplicate_filter_non_blocking_commit_complete' )
    

class CanvasFilterDuplicates( ClientGUICanvas.CanvasWithHovers ):
    
    CANVAS_TYPE = CC.CANVAS_MEDIA_VIEWER_DUPLICATES
    
    showPairInPage = QC.Signal( list )
    
    def __init__( self, parent, potential_duplicate_pair_factory: ClientPotentialDuplicatesPairFactory.PotentialDuplicatePairFactory ):
        
        self._potential_duplicate_pair_factory = potential_duplicate_pair_factory
        
        location_context = self._potential_duplicate_pair_factory.GetLocationContext()
        
        super().__init__( parent, location_context )
        
        self._loading_text = 'initialising'
        self._current_pair_score = 0
        self._force_maintain_pan_and_zoom = True
        
        self._batch_of_pairs_to_process = []
        self._current_pair_index = 0
        self._duplicate_pair_decisions: list[ ClientPotentialDuplicatesPairFactory.DuplicatePairDecision ] = []
        self._hashes_due_to_be_deleted_in_this_batch = set()
        self._hashes_due_to_be_media_merged_in_this_batch = set()
        
        self._num_items_to_commit = 0
        self._duplicate_pair_decisions_we_are_committing = []
        
        self._search_work_updater = self._InitialiseSearchWorkUpdater()
        
        self._commit_work_updater = self._InitialiseCommitWorkUpdater()
        
        self._canvas_type = CC.CANVAS_MEDIA_VIEWER_DUPLICATES
        
        show_approve_deny = isinstance( potential_duplicate_pair_factory, ClientPotentialDuplicatesPairFactory.PotentialDuplicatePairFactoryAutoResolutionReview )
        
        self._duplicates_right_hover = ClientGUICanvasHoverFrames.CanvasHoverFrameRightDuplicates( self, self, self._canvas_key, show_approve_deny = show_approve_deny )
        
        self.mediaChanged.connect( self._duplicates_right_hover.SetMedia )
        self.mediaCleared.connect( self._duplicates_right_hover.ClearMedia )
        
        self._right_notes_hover.AddHoverThatCanBeOnTop( self._duplicates_right_hover )
        
        self._duplicates_right_hover.showPairInPage.connect( self._ShowPairInPage )
        self._duplicates_right_hover.sendApplicationCommand.connect( self.ProcessApplicationCommand )
        
        self._hovers.append( self._duplicates_right_hover )
        
        self._background_colour_generator = ClientGUICanvas.CanvasBackgroundColourGeneratorDuplicates( self )
        
        self._media_container.SetBackgroundColourGenerator( self._background_colour_generator )
        
        self._my_shortcuts_handler.AddWindowToFilter( self._duplicates_right_hover )
        
        self._media_list = ClientMedia.MediaList( location_context, [] )
        
        self._my_shortcuts_handler.AddShortcuts( 'media_viewer_browser' )
        self._my_shortcuts_handler.AddShortcuts( 'duplicate_filter' )
        
        CG.client_controller.sub( self, 'Delete', 'canvas_delete' )
        CG.client_controller.sub( self, 'Undelete', 'canvas_undelete' )
        CG.client_controller.sub( self, 'SwitchMedia', 'canvas_show_next' )
        CG.client_controller.sub( self, 'SwitchMedia', 'canvas_show_previous' )
        
        CG.client_controller.sub( self, 'ProcessContentUpdatePackage', 'content_updates_gui' )
        CG.client_controller.sub( self, 'ProcessServiceUpdates', 'service_updates_gui' )
        
        CG.client_controller.CallAfter( self, self._LoadNextBatchOfPairs )
        
    
    def _ApproveDenyAutoResolutionPair( self, approved: bool ):
        
        if self._current_media is None:
            
            return
            
        
        if not isinstance( self._potential_duplicate_pair_factory, ClientPotentialDuplicatesPairFactory.PotentialDuplicatePairFactoryAutoResolutionReview ):
            
            return
            
        
        ( media_result_1, media_result_2 ) = self._batch_of_pairs_to_process[ self._current_pair_index ]
        
        ( media_result_a, media_result_b ) = ( media_result_1, media_result_2 )
        
        rule = self._potential_duplicate_pair_factory.GetRule()
        
        duplicate_type = rule.GetAction()
        
        if duplicate_type in ( HC.DUPLICATE_BETTER, HC.DUPLICATE_SAME_QUALITY ):
            
            self._hashes_due_to_be_media_merged_in_this_batch.add( media_result_a.GetHash() )
            
        
        ( delete_a, delete_b ) = rule.GetDeleteInfo()
        
        if delete_a:
            
            self._hashes_due_to_be_deleted_in_this_batch.add( media_result_a.GetHash() )
            
        
        if delete_b:
            
            self._hashes_due_to_be_deleted_in_this_batch.add( media_result_b.GetHash() )
            
        
        duplicate_pair_decision = ClientPotentialDuplicatesPairFactory.DuplicatePairDecisionApproveDeny( media_result_a, media_result_b, approved )
        
        self._ShowNextPair( duplicate_pair_decision )
        
    
    def _CommitProcessed( self, blocking = True ):
        
        self.ClearMedia()
        self._media_list = ClientMedia.MediaList( self._location_context, [] )
        
        self._num_items_to_commit = 0
        
        self._potential_duplicate_pair_factory.NotifyCommitDone()
        
        self._duplicate_pair_decisions_we_are_committing = [ decision for decision in self._duplicate_pair_decisions if decision.HasWorkToDo() ]
        
        self._duplicate_pair_decisions = []
        self._hashes_due_to_be_deleted_in_this_batch = set()
        self._hashes_due_to_be_media_merged_in_this_batch = set()
        
        self._num_items_to_commit = len( self._duplicate_pair_decisions_we_are_committing )
        
        if self._num_items_to_commit > 0:
            
            if blocking:
                
                self._commit_work_updater.update()
                
            else:
                
                CG.client_controller.CallToThread( THREADCommitDuplicatePairDecisions, self._potential_duplicate_pair_factory, self._duplicate_pair_decisions_we_are_committing )
                
                self._num_items_to_commit = 0
                self._duplicate_pair_decisions_we_are_committing = []
                
            
        
    
    def _CurrentMediaIsBetter( self, delete_b = True ):
        
        self._ProcessPair( HC.DUPLICATE_BETTER, delete_b = delete_b )
        
    
    def _CurrentlyCommitting( self ):
        
        return len( self._duplicate_pair_decisions_we_are_committing ) > 0 
        
    
    def _Delete( self, media = None, reason = None, file_service_key = None ):
        
        if self._current_media is None:
            
            return False
            
        
        media_a = self._current_media
        media_b = self._media_list.GetNext( self._current_media )
        
        message = 'Delete just this file, or both?'
        
        yes_tuples = []
        
        yes_tuples.append( ( 'delete just this one', 'current' ) )
        yes_tuples.append( ( 'delete both', 'both' ) )
        
        try:
            
            result = ClientGUIDialogsQuick.GetYesYesNo( self, message, yes_tuples = yes_tuples, no_label = 'forget it' )
            
        except HydrusExceptions.CancelledException:
            
            return False
            
        
        if result == 'current':
            
            media = [ media_a ]
            
            default_reason = 'Deleted manually in Duplicate Filter.'
            
        elif result == 'both':
            
            media = [ media_a, media_b ]
            
            default_reason = 'Deleted manually in Duplicate Filter, along with its potential duplicate.'
            
        else:
            
            raise NotImplementedError( 'Unknown delete command!' )
            
        
        content_update_packages = []
        
        if CG.client_controller.new_options.GetBoolean( 'delete_lock_reinbox_deletees_after_duplicate_filter' ):
            
            content_update_package = ClientContentUpdates.ContentUpdatePackage()
            
            content_update_package.AddContentUpdate( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_INBOX, { m.GetHash() for m in media } ) )
            
            content_update_packages.append( content_update_package )
            
        
        deleted = False
        
        result = super()._Delete( media = media, default_reason = default_reason, file_service_key = file_service_key, just_get_content_update_packages = True )
        
        if isinstance( result, list ):
            
            deleted = len( result ) > 0
            
            content_update_packages.extend( result )
            
        
        if deleted:
            
            for m in media:
                
                self._hashes_due_to_be_deleted_in_this_batch.update( m.GetHashes() )
                
            
            ( media_result_1, media_result_2 ) = self._batch_of_pairs_to_process[ self._current_pair_index ]
            
            duplicate_pair_decision = ClientPotentialDuplicatesPairFactory.DuplicatePairDecisionDeletion( media_result_1, media_result_2, content_update_packages )
            
            self._ShowNextPair( duplicate_pair_decision )
            
        
        return deleted
        
    
    def _DoCommitWork( self ):
        
        self._commit_work_updater.update()
        
    
    def _DoCustomAction( self ):
        
        if self._current_media is None:
            
            return
            
        
        duplicate_types = [ HC.DUPLICATE_BETTER, HC.DUPLICATE_SAME_QUALITY, HC.DUPLICATE_ALTERNATE, HC.DUPLICATE_FALSE_POSITIVE ]
        
        choice_tuples = [ ( HC.duplicate_type_string_lookup[ duplicate_type ], duplicate_type ) for duplicate_type in duplicate_types ]
        
        try:
            
            duplicate_type = ClientGUIDialogsQuick.SelectFromList( self, 'select duplicate type', choice_tuples )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        new_options = CG.client_controller.new_options
        
        if duplicate_type in [ HC.DUPLICATE_BETTER, HC.DUPLICATE_SAME_QUALITY ] or ( new_options.GetBoolean( 'advanced_mode' ) and duplicate_type == HC.DUPLICATE_ALTERNATE ):
            
            duplicate_content_merge_options = new_options.GetDuplicateContentMergeOptions( duplicate_type )
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit duplicate merge options' ) as dlg_2:
                
                panel = ClientGUIScrolledPanels.EditSingleCtrlPanel( dlg_2 )
                
                ctrl = ClientGUIDuplicatesContentMergeOptions.EditDuplicateContentMergeOptionsWidget( panel, duplicate_type, duplicate_content_merge_options, for_custom_action = True )
                
                panel.SetControl( ctrl )
                
                dlg_2.SetPanel( panel )
                
                if dlg_2.exec() == QW.QDialog.DialogCode.Accepted:
                    
                    duplicate_content_merge_options = ctrl.GetValue()
                    
                else:
                    
                    return
                    
                
            
        else:
            
            duplicate_content_merge_options = None
            
        
        message = 'Delete any of the files?'
        
        yes_tuples = []
        
        yes_tuples.append( ( 'delete neither', 'delete_neither' ) )
        yes_tuples.append( ( 'delete this one', 'delete_a' ) )
        yes_tuples.append( ( 'delete the other', 'delete_b' ) )
        yes_tuples.append( ( 'delete both', 'delete_both' ) )
        
        try:
            
            result = ClientGUIDialogsQuick.GetYesYesNo( self, message, yes_tuples = yes_tuples, no_label = 'forget it' )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        delete_a = False
        delete_b = False
        
        if result == 'delete_a':
            
            delete_a = True
            
        elif result == 'delete_b':
            
            delete_b = True
            
        elif result == 'delete_both':
            
            delete_a = True
            delete_b = True
            
        
        self._ProcessPair( duplicate_type, delete_a = delete_a, delete_b = delete_b, duplicate_content_merge_options = duplicate_content_merge_options )
        
    
    def _DoSearchWork( self ):
        
        self._search_work_updater.update()
        
    
    def _GenerateHoverTopFrame( self ):
        
        return ClientGUICanvasHoverFrames.CanvasHoverFrameTopDuplicatesFilter( self, self, self._canvas_key )
        
    
    def _GetIndexString( self ):
        
        if self._current_media is None or len( self._media_list ) == 0:
            
            return '-'
            
        else:
            
            ( first_label, second_label ) = self._potential_duplicate_pair_factory.GetFirstSecondLabels()
            
            current_media_label = first_label if self._current_media == self._media_list.GetFirst() else second_label
            
            progress = self._current_pair_index + 1
            total = len( self._batch_of_pairs_to_process )
            
            index_string = HydrusNumbers.ValueRangeToPrettyString( progress, total )
            
            num_committable = self._GetNumCommittableDecisions()
            num_deletable = self._GetNumCommittableDeletes()
            
            components = []
            
            if num_committable > 0:
                
                components.append( '{} decisions'.format( HydrusNumbers.ToHumanInt( num_committable ) ) )
                
            
            if num_deletable > 0:
                
                components.append( '{} deletes'.format( HydrusNumbers.ToHumanInt( num_deletable ) ) )
                
            
            if len( components ) == 0:
                
                num_decisions_string = 'no decisions yet'
                
            else:
                
                num_decisions_string = ', '.join( components )
                
            
            return '{} - {} - {}'.format( current_media_label, index_string, num_decisions_string )
            
        
    
    def _GetNoMediaText( self ):
        
        return self._loading_text
        
    
    def _GetNumAutoSkips( self ):
        
        return len( [ 1 for duplicate_pair_decision in self._duplicate_pair_decisions if isinstance( duplicate_pair_decision, ClientPotentialDuplicatesPairFactory.DuplicatePairDecisionSkipAuto ) ] )
        
    
    def _GetNumCommittableDecisions( self ):
        
        return len( [ 1 for duplicate_pair_decision in self._duplicate_pair_decisions if isinstance( duplicate_pair_decision, ( ClientPotentialDuplicatesPairFactory.DuplicatePairDecisionDuplicatesAction, ClientPotentialDuplicatesPairFactory.DuplicatePairDecisionApproveDeny ) ) ] )
        
    
    def _GetNumCommittableDeletes( self ):
        
        return len( [ 1 for duplicate_pair_decision in self._duplicate_pair_decisions if isinstance( duplicate_pair_decision, ClientPotentialDuplicatesPairFactory.DuplicatePairDecisionDeletion ) ] )
        
    
    def _GetNumRemainingDecisions( self ):
        
        # this looks a little weird, but I want to be clear that we make a decision on the final index
        
        last_decision_index = len( self._batch_of_pairs_to_process ) - 1
        
        number_of_decisions_after_the_current = last_decision_index - self._current_pair_index
        
        return max( 0, 1 + number_of_decisions_after_the_current )
        
    
    def _GoBack( self ):
        
        if self._current_pair_index > 0:
            
            it_went_ok = self._RewindProcessing()
            
            if it_went_ok:
                
                self._ShowCurrentPair()
                
            
        
    
    def _HaveFetchedPairsToWork( self ):
        
        return len( self._batch_of_pairs_to_process ) > 0
        
    
    def _InitialisePotentialDuplicatePairs( self ):
        
        if self._CurrentlyCommitting():
            
            return
            
        
        if not self._potential_duplicate_pair_factory.InitialisationWorkNeeded() or self._potential_duplicate_pair_factory.InitialisationWorkStarted():
            
            return
            
        
        self._potential_duplicate_pair_factory.NotifyInitialisationWorkStarted()
        
        def publish_callable( result: bool ):
            
            self._potential_duplicate_pair_factory.NotifyInitialisationWorkFinished()
            
            if not self._potential_duplicate_pair_factory.InitialisationWorkLooksGood():
                
                ClientGUIDialogsMessage.ShowInformation( self, 'All potential pairs are cleared!' )
                
                CG.client_controller.pub( 'new_similar_files_potentials_search_numbers' )
                
                self._TryToCloseWindow()
                
                return
                
            
            self._LoadNextBatchOfPairs()
            
        
        self._loading_text = 'Initialising pair search--please wait.'
        
        self.update()
        
        async_job = ClientGUIAsync.AsyncQtJob( self, self._potential_duplicate_pair_factory.DoInitialisationWork, publish_callable )
        
        async_job.start()
        
    
    def _InitialiseCommitWorkUpdater( self ):
        
        def loading_callable():
            
            pass
            
        
        def pre_work_callable():
            
            num_work_to_do = len( self._duplicate_pair_decisions_we_are_committing )
            
            if num_work_to_do == 0:
                
                raise HydrusExceptions.CancelledException()
                
            else:
                
                value = self._num_items_to_commit - num_work_to_do
                range = self._num_items_to_commit
                
                self._loading_text = f'committed {HydrusNumbers.ValueRangeToPrettyString( value, range )} decisions{HC.UNICODE_ELLIPSIS}'
                
            
            NUM_DECISIONS_IN_BLOCK = 4
            
            block_of_duplicate_pair_decisions = self._duplicate_pair_decisions_we_are_committing[ : NUM_DECISIONS_IN_BLOCK ]
            
            self._duplicate_pair_decisions_we_are_committing = self._duplicate_pair_decisions_we_are_committing[ NUM_DECISIONS_IN_BLOCK : ]
            
            self.update()
            
            return ( self._potential_duplicate_pair_factory, block_of_duplicate_pair_decisions )
            
        
        def work_callable( args ):
            
            ( potential_duplicate_pair_factory, block_of_duplicate_pair_decisions ) = args
            
            for duplicate_pair_decision in block_of_duplicate_pair_decisions:
                
                CommitDecision( potential_duplicate_pair_factory, duplicate_pair_decision )
                
            
            return 1
            
        
        def publish_callable( result ):
            
            if len( self._duplicate_pair_decisions_we_are_committing ) == 0:
                
                self._LoadNextBatchOfPairs()
                
            else:
                
                self._DoCommitWork()
                
            
            self.update()
            
        
        return ClientGUIAsync.AsyncQtUpdater( self, loading_callable, work_callable, publish_callable, pre_work_callable = pre_work_callable )
        
    
    def _InitialiseSearchWorkUpdater( self ):
        
        def loading_callable():
            
            pass
            
        
        def pre_work_callable():
            
            if self._CurrentlyCommitting():
                
                raise HydrusExceptions.CancelledException()
                
            
            if self._potential_duplicate_pair_factory.InitialisationWorkNeeded():
                
                raise HydrusExceptions.CancelledException()
                
            
            if self._potential_duplicate_pair_factory.SearchWorkIsDone():
                
                raise HydrusExceptions.CancelledException()
                
            
            self._loading_text = self._potential_duplicate_pair_factory.GetWorkStatus()
            
            self.update()
            
            return 1
            
        
        def publish_callable( result ):
            
            if self._potential_duplicate_pair_factory.SearchWorkIsDone():
                
                self._PresentFactoryPairs()
                
            else:
                
                self._DoSearchWork()
                
            
        
        return ClientGUIAsync.AsyncQtUpdater( self, loading_callable, self._potential_duplicate_pair_factory.DoSearchWork, publish_callable, pre_work_callable = pre_work_callable )
        
    
    def _LoadNextBatchOfPairs( self ):
        
        if self._CurrentlyCommitting():
            
            return
            
        
        if self._potential_duplicate_pair_factory.InitialisationWorkNeeded():
            
            if not self._potential_duplicate_pair_factory.InitialisationWorkStarted():
                
                self._InitialisePotentialDuplicatePairs()
                
            
            return
            
        
        self._batch_of_pairs_to_process = []
        self._duplicate_pair_decisions = []
        self._hashes_due_to_be_deleted_in_this_batch = set()
        self._hashes_due_to_be_media_merged_in_this_batch = set()
        
        self._loading_text = 'Loading more pairs--please wait.'
        
        self._potential_duplicate_pair_factory.NotifyFetchMorePairs()
        
        self.ClearMedia()
        
        self._media_list = ClientMedia.MediaList( self._location_context, [] )
        
        if self._potential_duplicate_pair_factory.SearchWorkIsDone():
            
            self._PresentFactoryPairs()
            
        else:
            
            self._DoSearchWork()
            
        
        self.update()
        
    
    def _MediaAreAlternates( self ):
        
        self._ProcessPair( HC.DUPLICATE_ALTERNATE )
        
    
    def _MediaAreFalsePositive( self ):
        
        self._ProcessPair( HC.DUPLICATE_FALSE_POSITIVE )
        
    
    def _MediaAreTheSame( self ):
        
        self._ProcessPair( HC.DUPLICATE_SAME_QUALITY )
        
    
    def _PrefetchNeighbours( self ):
        
        if self._current_media is None:
            
            return
            
        
        other_media: ClientMedia.MediaSingleton = self._media_list.GetNext( self._current_media )
        
        media_results_to_prefetch = [ other_media.GetMediaResult() ]
        
        duplicate_filter_prefetch_num_pairs = CG.client_controller.new_options.GetInteger( 'duplicate_filter_prefetch_num_pairs' )
        
        if duplicate_filter_prefetch_num_pairs > 0:
            
            # this isn't clever enough to handle pending skip logic, but that's fine
            
            start_pos = self._current_pair_index + 1
            
            pairs_to_do = self._batch_of_pairs_to_process[ start_pos : start_pos + duplicate_filter_prefetch_num_pairs ]
            
            for pair in pairs_to_do:
                
                media_results_to_prefetch.extend( pair )
                
            
        
        delay_base = HydrusTime.SecondiseMSFloat( CG.client_controller.new_options.GetInteger( 'media_viewer_prefetch_delay_base_ms' ) )
        
        images_cache = CG.client_controller.images_cache
        
        for ( i, media_result ) in enumerate( media_results_to_prefetch ):
            
            delay = i * delay_base
            
            hash = media_result.GetHash()
            mime = media_result.GetMime()
            
            if media_result.IsStaticImage() and ClientGUICanvasMedia.WeAreExpectingToLoadThisMediaFile( media_result, self.CANVAS_TYPE ):
                
                if not images_cache.HasImageRenderer( hash ):
                    
                    CG.client_controller.CallLaterQtSafe( self, delay, 'image pre-fetch', images_cache.PrefetchImageRenderer, media_result )
                    
                
            
        
    
    def _PresentFactoryPairs( self ):
        
        self._potential_duplicate_pair_factory.SortAndABPairs()
        
        media_result_pairs_and_distances = self._potential_duplicate_pair_factory.GetPotentialDuplicateMediaResultPairsAndDistances()
        
        if len( media_result_pairs_and_distances ) == 0:
            
            skip_message = isinstance( self._potential_duplicate_pair_factory, ClientPotentialDuplicatesPairFactory.PotentialDuplicatePairFactoryMediaResults )
            
            if not skip_message:
                
                ClientGUIDialogsMessage.ShowInformation( self, 'All pairs have been filtered!' )
                
            
            CG.client_controller.pub( 'new_similar_files_potentials_search_numbers' )
            
            self._TryToCloseWindow()
            
        else:
            
            self._batch_of_pairs_to_process = media_result_pairs_and_distances.GetPairs()
            self._current_pair_index = 0
            
            self._ShowCurrentPair()
            
        
    
    def _ProcessPair( self, duplicate_type, delete_a = False, delete_b = False, duplicate_content_merge_options = None ):
        
        if self._current_media is None:
            
            return
            
        
        if duplicate_content_merge_options is None:
            
            if duplicate_type in [ HC.DUPLICATE_BETTER, HC.DUPLICATE_SAME_QUALITY ] or ( CG.client_controller.new_options.GetBoolean( 'advanced_mode' ) and duplicate_type == HC.DUPLICATE_ALTERNATE ):
                
                new_options = CG.client_controller.new_options
                
                duplicate_content_merge_options = new_options.GetDuplicateContentMergeOptions( duplicate_type )
                
            else:
                
                duplicate_content_merge_options = ClientDuplicates.DuplicateContentMergeOptions()
                
            
        
        media_a = self._current_media
        media_b = typing.cast( ClientMedia.MediaSingleton, self._media_list.GetNext( media_a ) )
        
        if duplicate_type in ( HC.DUPLICATE_BETTER, HC.DUPLICATE_SAME_QUALITY ):
            
            self._hashes_due_to_be_media_merged_in_this_batch.update( media_b.GetHashes() )
            
        
        if delete_a or delete_b:
            
            if delete_a:
                
                self._hashes_due_to_be_deleted_in_this_batch.update( media_a.GetHashes() )
                
            
            if delete_b:
                
                self._hashes_due_to_be_deleted_in_this_batch.update( media_b.GetHashes() )
                
            
            if duplicate_type == HC.DUPLICATE_BETTER:
                
                file_deletion_reason = 'better/worse'
                
                if delete_b:
                    
                    file_deletion_reason += ', worse file deleted'
                    
                
            else:
                
                file_deletion_reason = HC.duplicate_type_string_lookup[ duplicate_type ]
                
            
            if delete_a and delete_b:
                
                file_deletion_reason += ', both files deleted'
                
            
            file_deletion_reason = 'Deleted in Duplicate Filter ({}).'.format( file_deletion_reason )
            
        else:
            
            file_deletion_reason = None
            
        
        content_update_packages = duplicate_content_merge_options.ProcessPairIntoContentUpdatePackages( media_a.GetMediaResult(), media_b.GetMediaResult(), delete_a = delete_a, delete_b = delete_b, file_deletion_reason = file_deletion_reason )
        
        duplicate_pair_decision = ClientPotentialDuplicatesPairFactory.DuplicatePairDecisionDuplicatesAction(
            media_a.GetMediaResult(),
            media_b.GetMediaResult(),
            duplicate_type,
            content_update_packages
        )
        
        self._ShowNextPair( duplicate_pair_decision )
        
    
    def _RecoverAfterMediaUpdate( self ):
        
        if len( self._media_list ) < 2 and len( self._batch_of_pairs_to_process ) > self._current_pair_index:
            
            ( media_result_1, media_result_2 ) = self._batch_of_pairs_to_process[ self._current_pair_index ]
            
            duplicate_pair_decision = ClientPotentialDuplicatesPairFactory.DuplicatePairDecisionSkipAuto( media_result_1, media_result_2 )
            
            self._ShowNextPair( duplicate_pair_decision )
            
        else:
            
            self.update()
            
        
    
    def _RewindProcessing( self ) -> bool:
        
        if not self._HaveFetchedPairsToWork():
            
            return False
            
        
        def test_we_can_pop():
            
            if len( self._duplicate_pair_decisions ) == 0:
                
                # the first one shouldn't be auto-skipped, so if it was and now we can't pop, something weird happened
                
                CG.client_controller.pub( 'new_similar_files_potentials_search_numbers' )
                
                ClientGUIDialogsMessage.ShowCritical( self, 'Hell!', 'Due to an unexpected series of events, the duplicate filter has no valid pair to back up to. It could be some files were deleted during processing. The filter will now close.' )
                
                self.window().deleteLater()
                
                return False
                
            
            return True
            
        
        if self._current_pair_index > 0:
            
            while True:
                
                # rewind back through all our auto-skips until we get to something human
                
                if not test_we_can_pop():
                    
                    return False
                    
                
                duplicate_pair_decision = self._duplicate_pair_decisions.pop()
                
                self._current_pair_index -= 1
                
                if not isinstance( duplicate_pair_decision, ClientPotentialDuplicatesPairFactory.DuplicatePairDecisionSkipAuto ):
                    
                    break
                    
                
            
            # only want this for the one that wasn't auto-skipped
            for m in ( duplicate_pair_decision.media_result_a, duplicate_pair_decision.media_result_a ):
                
                hash = m.GetHash()
                
                self._hashes_due_to_be_deleted_in_this_batch.discard( hash )
                self._hashes_due_to_be_media_merged_in_this_batch.discard( hash )
                
            
            return True
            
        
        return False
        
    
    def _ShowCurrentPair( self ):
        
        if not self._HaveFetchedPairsToWork():
            
            return
            
        
        # better file first is now handled by the pair factory; we used to do it here
        ( media_result_1, media_result_2 ) = self._batch_of_pairs_to_process[ self._current_pair_index ]
        
        self._current_pair_score = ClientDuplicatesComparisonStatements.GetDuplicateComparisonScoreFast( media_result_1, media_result_2 )
        
        self._media_list = ClientMedia.MediaList( self._location_context, ( media_result_1, media_result_2 ) )
        
        # reset zoom gubbins
        self.SetMedia( None )
        
        self.SetMedia( self._media_list.GetFirst() )
        
        self._media_container.hide()
        
        self._media_container.ZoomReinit()
        
        self._media_container.ResetCenterPosition()
        
        self.EndDrag()
        
        self._media_container.show()
        
    
    def _ShowNextPair( self, duplicate_pair_decision: ClientPotentialDuplicatesPairFactory.DuplicatePairDecision ):
        
        if not self._HaveFetchedPairsToWork():
            
            return
            
        
        # hackery dackery doo to quick solve something that is calling this a bunch of times while the 'and continue?' dialog is open, making like 16 of them
        # a full rewrite is needed on this awful workflow
        
        tlws = QW.QApplication.topLevelWidgets()
        
        for tlw in tlws:
            
            if isinstance( tlw, ClientGUITopLevelWindowsPanels.DialogCustomButtonQuestion ) and tlw.isModal():
                
                return
                
            
        
        #
        
        def pair_is_good( pair ):
            
            ( media_result_1, media_result_2 ) = pair
            
            hash_1 = media_result_1.GetHash()
            hash_2 = media_result_2.GetHash()
            
            if hash_1 in self._hashes_due_to_be_media_merged_in_this_batch or hash_2 in self._hashes_due_to_be_media_merged_in_this_batch:
                
                return False
                
            
            if hash_1 in self._hashes_due_to_be_deleted_in_this_batch or hash_2 in self._hashes_due_to_be_deleted_in_this_batch:
                
                return False
                
            
            media_1 = ClientMedia.MediaSingleton( media_result_1 )
            media_2 = ClientMedia.MediaSingleton( media_result_2 )
            
            if not ClientMedia.CanDisplayMedia( media_1 ) or not ClientMedia.CanDisplayMedia( media_2 ):
                
                return False
                
            
            return True
            
        
        #
        
        self._duplicate_pair_decisions.append( duplicate_pair_decision )
        
        self._current_pair_index += 1
        
        while True:
            
            num_remaining = self._GetNumRemainingDecisions()
            
            if num_remaining == 0:
                
                num_committable = self._GetNumCommittableDecisions()
                num_deletable = self._GetNumCommittableDeletes()
                
                if num_committable + num_deletable > 0:
                    
                    just_do_it = False
                    
                    just_do_it_threshold = CG.client_controller.new_options.GetNoneableInteger( 'duplicate_filter_auto_commit_batch_size' )
                    
                    if just_do_it_threshold is not None:
                        
                        num_auto_skips = self._GetNumAutoSkips()
                        
                        # we want to carefully test that there were no manual skips
                        if num_committable + num_deletable <= just_do_it_threshold and num_committable + num_deletable + num_auto_skips == len( self._duplicate_pair_decisions ):
                            
                            just_do_it = True
                            
                        
                    
                    if just_do_it:
                        
                        do_it = True
                        
                    else:
                        
                        do_it = False
                        
                        components = []
                        
                        if num_committable > 0:
                            
                            components.append( '{} decisions'.format( HydrusNumbers.ToHumanInt( num_committable ) ) )
                            
                        
                        if num_deletable > 0:
                            
                            components.append( '{} deletes'.format( HydrusNumbers.ToHumanInt( num_deletable ) ) )
                            
                        
                        label = 'commit {} and continue?'.format( ' and '.join( components ) )
                        
                        result = ClientGUIScrolledPanelsCommitFiltering.GetInterstitialFilteringAnswer( self, label )
                        
                        if result == QW.QDialog.DialogCode.Accepted:
                            
                            do_it = True
                            
                        
                    
                    if do_it:
                        
                        self._CommitProcessed( blocking = True )
                        
                    else:
                        
                        it_went_ok = self._RewindProcessing()
                        
                        if it_went_ok:
                            
                            self._ShowCurrentPair()
                            
                        
                        return
                        
                    
                else:
                    
                    # nothing to commit, so let's see if we have a big problem here or if user just skipped all
                    
                    we_saw_a_non_auto_skip = True in ( not isinstance( duplicate_pair_decision, ClientPotentialDuplicatesPairFactory.DuplicatePairDecisionSkipAuto ) for duplicate_pair_decision in self._duplicate_pair_decisions )
                    
                    if we_saw_a_non_auto_skip:
                        
                        if isinstance( self._potential_duplicate_pair_factory, ClientPotentialDuplicatesPairFactory.PotentialDuplicatePairFactoryDBGroupMode ):
                            
                            text = 'You appear to have skipped this whole group. Do you want to load up a different one?'
                            
                            result = ClientGUIDialogsQuick.GetYesNo( self, text )
                            
                            if result == QW.QDialog.DialogCode.Accepted:
                                
                                self._potential_duplicate_pair_factory.SelectNewGroup() # this resets search and will select a new group from scratch
                                
                            
                        
                    else:
                        
                        CG.client_controller.pub( 'new_similar_files_potentials_search_numbers' )
                        
                        HydrusData.Print( 'Rows that could not be displayed:' )
                        
                        for duplicate_pair_decision in self._duplicate_pair_decisions:
                            
                            print( f'Dup: {duplicate_pair_decision}, Hashes: {duplicate_pair_decision.media_result_a.GetHash().hex()}, {duplicate_pair_decision.media_result_b.GetHash().hex()}' )
                            
                        
                        ClientGUIDialogsMessage.ShowCritical( self, 'Hell!', 'It seems an entire batch of pairs were unable to be displayed. The duplicate filter will now close. More information has been written to the log.' )
                        
                        self.window().deleteLater()
                        
                        return
                        
                    
                
                self._LoadNextBatchOfPairs()
                
                return
                
            
            ( media_result_1, media_result_2 ) = self._batch_of_pairs_to_process[ self._current_pair_index ]
            
            if pair_is_good( ( media_result_1, media_result_2 ) ):
                
                self._ShowCurrentPair()
                
                return
                
            else:
                
                duplicate_pair_decision = ClientPotentialDuplicatesPairFactory.DuplicatePairDecisionSkipAuto( media_result_1, media_result_2 )
                
                self._duplicate_pair_decisions.append( duplicate_pair_decision )
                
                self._current_pair_index += 1
                
            
        
    
    def _ShowPairInPage( self ):
        
        if self._current_media is None:
            
            return
            
        
        self.showPairInPage.emit( [ self._current_media, self._media_list.GetNext( self._current_media ) ] )
        
    
    def _SkipPair( self ):
        
        if self._current_media is None:
            
            return
            
        
        ( media_result_1, media_result_2 ) = self._batch_of_pairs_to_process[ self._current_pair_index ]
        
        duplicate_pair_decision = ClientPotentialDuplicatesPairFactory.DuplicatePairDecisionSkipManual( media_result_1, media_result_2 )
        
        self._ShowNextPair( duplicate_pair_decision )
        
    
    def _SwitchMedia( self ):
        
        if self._current_media is not None:
            
            try:
                
                other_media = self._media_list.GetNext( self._current_media )
                
                self.SetMedia( other_media )
                
            except HydrusExceptions.DataMissing:
                
                return
                
            
        
    
    def Archive( self, canvas_key ):
        
        if self._canvas_key == canvas_key:
            
            self._Archive()
            
        
    
    def Delete( self, canvas_key ):
        
        if self._canvas_key == canvas_key:
            
            self._Delete()
            
        
    
    def Inbox( self, canvas_key ):
        
        if self._canvas_key == canvas_key:
            
            self._Inbox()
            
        
    
    def IsShowingAPair( self ):
        
        return self._current_media is not None and len( self._media_list ) > 1
        
    
    def IsShowingFileA( self ):
        
        if not self.IsShowingAPair():
            
            return False
            
        
        return self._current_media == self._media_list.GetFirst()
        
    
    def ProcessApplicationCommand( self, command: CAC.ApplicationCommand ):
        
        command_processed = True
        
        if command.IsSimpleCommand():
            
            action = command.GetSimpleAction()
            
            if action == CAC.SIMPLE_DUPLICATE_FILTER_THIS_IS_BETTER_AND_DELETE_OTHER:
                
                self._CurrentMediaIsBetter( delete_b = True )
                
            elif action == CAC.SIMPLE_DUPLICATE_FILTER_THIS_IS_BETTER_BUT_KEEP_BOTH:
                
                self._CurrentMediaIsBetter( delete_b = False )
                
            elif action == CAC.SIMPLE_DUPLICATE_FILTER_EXACTLY_THE_SAME:
                
                self._MediaAreTheSame()
                
            elif action == CAC.SIMPLE_DUPLICATE_FILTER_ALTERNATES:
                
                self._MediaAreAlternates()
                
            elif action == CAC.SIMPLE_DUPLICATE_FILTER_FALSE_POSITIVE:
                
                self._MediaAreFalsePositive()
                
            elif action == CAC.SIMPLE_DUPLICATE_FILTER_CUSTOM_ACTION:
                
                self._DoCustomAction()
                
            elif action == CAC.SIMPLE_DUPLICATE_FILTER_SKIP:
                
                self._SkipPair()
                
            elif action == CAC.SIMPLE_DUPLICATE_FILTER_BACK:
                
                self._GoBack()
                
            elif action in ( CAC.SIMPLE_VIEW_FIRST, CAC.SIMPLE_VIEW_LAST, CAC.SIMPLE_VIEW_PREVIOUS, CAC.SIMPLE_VIEW_NEXT ):
                
                self._SwitchMedia()
                
            elif action in ( CAC.SIMPLE_DUPLICATE_FILTER_APPROVE_AUTO_RESOLUTION, CAC.SIMPLE_DUPLICATE_FILTER_DENY_AUTO_RESOLUTION ):
                
                approved = action == CAC.SIMPLE_DUPLICATE_FILTER_APPROVE_AUTO_RESOLUTION
                
                self._ApproveDenyAutoResolutionPair( approved )
                
            else:
                
                command_processed = False
                
            
        else:
            
            command_processed = False
            
        
        if not command_processed:
            
            command_processed = super().ProcessApplicationCommand( command )
            
        
        return command_processed
        
    
    def ProcessContentUpdatePackage( self, content_update_package: ClientContentUpdates.ContentUpdatePackage ):
        
        self._media_list.ProcessContentUpdatePackage( content_update_package )
        
        self._RecoverAfterMediaUpdate()
        
    
    def ProcessServiceUpdates( self, service_keys_to_service_updates: dict[ bytes, collections.abc.Collection[ ClientServices.ServiceUpdate ] ]  ):
        
        self._media_list.ProcessServiceUpdates( service_keys_to_service_updates )
        
        self._RecoverAfterMediaUpdate()
        
    
    def SetMedia( self, media, start_paused = None ):
        
        super().SetMedia( media, start_paused = start_paused )
        
        if media is not None:
            
            shown_media = self._current_media
            comparison_media = self._media_list.GetNext( shown_media )
            
            if shown_media != comparison_media:
                
                CG.client_controller.pub( 'canvas_new_duplicate_pair', self._canvas_key, shown_media, comparison_media )
                
            
        
    
    def SwitchMedia( self, canvas_key ):
        
        if canvas_key == self._canvas_key:
            
            self._SwitchMedia()
            
        
    
    def TryToDoPreClose( self ):
        
        if self._CurrentlyCommitting():
            
            self._DoCommitWork()
            
            return False
            
        
        num_committable = self._GetNumCommittableDecisions()
        num_deletable = self._GetNumCommittableDeletes()
        
        if num_committable + num_deletable > 0:
            
            components = []
            
            if num_committable > 0:
                
                components.append( '{} decisions'.format( HydrusNumbers.ToHumanInt( num_committable ) ) )
                
            
            if num_deletable > 0:
                
                components.append( '{} deletes'.format( HydrusNumbers.ToHumanInt( num_deletable ) ) )
                
            
            label = 'commit {}?'.format( ' and '.join( components ) )
            
            ( result, cancelled ) = ClientGUIScrolledPanelsCommitFiltering.GetFinishFilteringAnswer( self, label )
            
            if cancelled:
                
                close_was_triggered_by_everything_being_processed = self._GetNumRemainingDecisions() == 0
                
                if close_was_triggered_by_everything_being_processed:
                    
                    self._GoBack()
                    
                
                return False
                
            elif result == QW.QDialog.DialogCode.Accepted:
                
                self._CommitProcessed( blocking = False )
                
            
        
        return super().TryToDoPreClose()
        
    
    def Undelete( self, canvas_key ):
        
        if canvas_key == self._canvas_key:
            
            self._Undelete()
            
        
    
