import itertools

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusLists
from hydrus.core import HydrusNumbers

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientLocation
from hydrus.client.duplicates import ClientDuplicatesAutoResolution
from hydrus.client.gui import ClientGUIAsync
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.canvas import ClientGUICanvas
from hydrus.client.gui.canvas import ClientGUICanvasFrame
from hydrus.client.gui.duplicates import ThumbnailPairList
from hydrus.client.gui.media import ClientGUIMediaSimpleActions
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.widgets import ClientGUICommon

class ReviewActionsPanel( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent: QW.QWidget, rule: ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule ):
        
        super().__init__( parent )
        
        self._rule = rule
        
        self._pending_action_pairs = []
        self._actioned_pairs_with_info = []
        
        self._main_notebook = ClientGUICommon.BetterNotebook( self )
        
        self._pending_actions_panel = ClientGUICommon.StaticBox( self, 'pending actions' )
        
        self._pending_actions_label = ClientGUICommon.BetterStaticText( self._pending_actions_panel, 'initialising' )
        
        self._refetch_pending_actions_button = ClientGUICommon.BetterBitmapButton( self._pending_actions_panel, CC.global_pixmaps().refresh, self._RefetchPendingActionPairs )
        self._refetch_pending_actions_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'Refresh the pending pairs' ) )
        
        self._pending_pairs_num_to_fetch = ClientGUICommon.NoneableSpinCtrl( self._pending_actions_panel, 256, min = 1, none_phrase = 'fetch all' )
        
        self._pending_actions_pair_list = ThumbnailPairList.ThumbnailPairListReviewPendingPreviewAutoResolutionAction( self._pending_actions_panel, rule )
        
        self._approve_selected_button = ClientGUICommon.BetterButton( self._pending_actions_panel, 'approve', self._ApproveSelectedPending )
        self._deny_selected_button = ClientGUICommon.BetterButton( self._pending_actions_panel, 'deny', self._DenySelectedPending )
        
        self._select_all_button = ClientGUICommon.BetterButton( self._pending_actions_panel, 'select all', self._SelectAllPending )
        
        #
        
        self._actioned_pairs_panel = ClientGUICommon.StaticBox( self, 'actioned pairs' )
        
        self._actioned_pairs_label = ClientGUICommon.BetterStaticText( self._actioned_pairs_panel, 'initialising' )
        
        self._refetch_actioned_pairs_button = ClientGUICommon.BetterBitmapButton( self._actioned_pairs_panel, CC.global_pixmaps().refresh, self._RefetchActionedPairs )
        self._refetch_actioned_pairs_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'Refresh the actioned pairs' ) )
        
        self._actioned_pairs_num_to_fetch = ClientGUICommon.NoneableSpinCtrl( self._actioned_pairs_panel, 256, min = 1, none_phrase = 'fetch all' )
        
        self._actioned_pairs_pair_list = ThumbnailPairList.ThumbnailPairListTakenAutoResolutionAction( self._actioned_pairs_panel )
        
        self._undo_selected_button = ClientGUICommon.BetterButton( self._pending_actions_panel, 'undo', self._UndoSelectedActions )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._pending_actions_label, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH )
        QP.AddToLayout( hbox, self._refetch_pending_actions_button, CC.FLAGS_CENTER )
        
        self._pending_actions_panel.Add( hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        rows = []
        
        rows.append( ( 'only sample this many: ', self._pending_pairs_num_to_fetch ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        self._pending_actions_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._pending_actions_panel.Add( self._pending_actions_pair_list, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._approve_selected_button, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH )
        QP.AddToLayout( hbox, self._deny_selected_button, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH )
        
        self._pending_actions_panel.Add( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self._pending_actions_panel.Add( self._select_all_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._actioned_pairs_label, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH )
        QP.AddToLayout( hbox, self._refetch_actioned_pairs_button, CC.FLAGS_CENTER )
        
        self._actioned_pairs_panel.Add( hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        rows = []
        
        rows.append( ( 'only sample this many: ', self._actioned_pairs_num_to_fetch ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        self._actioned_pairs_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._actioned_pairs_panel.Add( self._actioned_pairs_pair_list, CC.FLAGS_EXPAND_BOTH_WAYS )
        self._actioned_pairs_panel.Add( self._undo_selected_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        self._main_notebook.addTab( self._pending_actions_panel, 'pending actions' )
        self._main_notebook.addTab( self._actioned_pairs_panel, 'actions taken' )
        
        vbox = QP.VBoxLayout()
        
        st = ClientGUICommon.BetterStaticText( self, label = rule.GetName() )
        st.setWordWrap( True )
        st.setAlignment( QC.Qt.AlignmentFlag.AlignCenter )
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._main_notebook, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
        #
        
        self._pending_actions_pair_list.activated.connect( self._PendingRowActivated )
        self._actioned_pairs_pair_list.activated.connect( self._ActionedRowActivated )
        
        self._enter_catcher_pending = ThumbnailPairList.ListEnterCatcher( self, self._pending_actions_pair_list )
        self._enter_catcher_actioned = ThumbnailPairList.ListEnterCatcher( self, self._actioned_pairs_pair_list )
        
        self._main_notebook.currentChanged.connect( self._CurrentPageChanged )
        
        self._RefetchPendingActionPairs()
        
        CG.client_controller.sub( self, 'CloseFromEditDialog', 'edit_duplicates_auto_resolution_rules_dialog_opening' )
        
    
    def _ActionedRowActivated( self, model_index: QC.QModelIndex ):
        
        if not model_index.isValid():
            
            return
            
        
        row = model_index.row()
        
        ( media_result_1, media_result_2 ) = self._actioned_pairs_pair_list.model().GetMediaResultPair( row )
        
        self._ShowMediaViewer( media_result_1, media_result_2 )
        
    
    def _ApproveSelectedPending( self ):
        
        model = self._pending_actions_pair_list.model()
        indices = self._pending_actions_pair_list.selectedIndexes()
        
        selected_pairs = [ model.GetMediaResultPair( index.row() ) for index in indices ]
        
        selected_pairs = HydrusData.DedupeList( selected_pairs )
        
        if len( selected_pairs ) == 0:
            
            return
            
        
        earliest_selected_row_index = min( ( index.row() for index in indices ) )
        
        if len( selected_pairs ) > 5:
            
            message = f'Are you sure you want to approve the {HydrusNumbers.ToHumanInt( len( selected_pairs ) )} pairs?'
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message )
            
            if result != QW.QDialog.DialogCode.Accepted:
                
                return
                
            
        
        def status_hook( status: str ):
            
            self._approve_selected_button.setText( status )
            
        
        rule = self._rule
        
        def work_callable():
            
            for ( num_done, num_to_do, chunk ) in HydrusLists.SplitListIntoChunksRich( selected_pairs, 4 ):
                
                message = f'approving: {HydrusNumbers.ValueRangeToPrettyString( num_done, num_to_do )}'
                
                CG.client_controller.CallAfterQtSafe( self, 'approve pairs status hook', status_hook, message )
                
                # this is safe to run on a bunch of related pairs like AB, AC, DB--the db figures that out
                CG.client_controller.WriteSynchronous( 'duplicate_auto_resolution_approve_pending_pairs', rule, chunk )
                
            
            return 1
            
        
        def publish_callable( _ ):
            
            self._pending_actions_panel.setEnabled( True )
            
            self._pending_action_pairs = [ pair for pair in self._pending_action_pairs if pair not in selected_pairs ]
            
            self._pending_actions_label.setText( f'{HydrusNumbers.ToHumanInt(len(self._pending_action_pairs))} pairs remaining.' )
            
            self._pending_actions_pair_list.SetData( self._pending_action_pairs )
            
            self._actioned_pairs_with_info = [] # trigger a refresh
            
            self._approve_selected_button.setText( original_approve_button_label )
            
            if len( self._pending_action_pairs ) > 0:
                
                if len( self._pending_action_pairs ) > earliest_selected_row_index:
                    
                    self._pending_actions_pair_list.selectRow( earliest_selected_row_index )
                    
                else:
                    
                    self._pending_actions_pair_list.selectRow( len( self._pending_action_pairs ) - 1 )
                    
                
            else:
                
                self._RefetchPendingActionPairs()
                
            
        
        original_approve_button_label = self._approve_selected_button.text()
        
        self._pending_actions_panel.setEnabled( False )
        
        job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
        
        job.start()
        
    
    def _CurrentPageChanged( self ):
        
        page = self._main_notebook.currentWidget()
        
        if page == self._pending_actions_panel:
            
            if len( self._pending_action_pairs ) == 0:
                
                self._RefetchPendingActionPairs()
                
            
        elif page == self._actioned_pairs_panel:
            
            if len( self._actioned_pairs_with_info ) == 0:
                
                self._RefetchActionedPairs()
                
            
        
    
    def _DenySelectedPending( self ):
        
        model = self._pending_actions_pair_list.model()
        indices = self._pending_actions_pair_list.selectedIndexes()
        
        selected_pairs = [ model.GetMediaResultPair( index.row() ) for index in indices ]
        
        selected_pairs = HydrusData.DedupeList( selected_pairs )
        
        if len( selected_pairs ) == 0:
            
            return
            
        
        earliest_selected_row_index = min( ( index.row() for index in indices ) )
        
        if len( selected_pairs ) > 5:
            
            message = f'Are you sure you want to deny the {HydrusNumbers.ToHumanInt( len( selected_pairs ) )} pairs?'
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message )
            
            if result != QW.QDialog.DialogCode.Accepted:
                
                return
                
            
        
        def status_hook( status: str ):
            
            self._deny_selected_button.setText( status )
            
        
        rule = self._rule
        
        def work_callable():
            
            for ( num_done, num_to_do, chunk ) in HydrusLists.SplitListIntoChunksRich( selected_pairs, 4 ):
                
                message = f'denying: {HydrusNumbers.ValueRangeToPrettyString( num_done, num_to_do )}'
                
                CG.client_controller.CallAfterQtSafe( self, 'deny pairs status hook', status_hook, message )
                
                # this is safe to run on a bunch of related pairs like AB, AC, DB--the db figures that out
                CG.client_controller.WriteSynchronous( 'duplicate_auto_resolution_deny_pending_pairs', rule, selected_pairs )
                
            
            return 1
            
        
        def publish_callable( _ ):
            
            self._pending_actions_panel.setEnabled( True )
            
            self._pending_action_pairs = [ pair for pair in self._pending_action_pairs if pair not in selected_pairs ]
            
            self._pending_actions_label.setText( f'{HydrusNumbers.ToHumanInt(len(self._pending_action_pairs))} pairs remaining.' )
            
            self._pending_actions_pair_list.SetData( self._pending_action_pairs )
            
            self._deny_selected_button.setText( original_deny_button_label )
            
            if len( self._pending_action_pairs ) > 0:
                
                if len( self._pending_action_pairs ) > earliest_selected_row_index:
                    
                    self._pending_actions_pair_list.selectRow( earliest_selected_row_index )
                    
                else:
                    
                    self._pending_actions_pair_list.selectRow( len( self._pending_action_pairs ) - 1 )
                    
                
            else:
                
                self._RefetchPendingActionPairs()
                
            
        
        original_deny_button_label = self._deny_selected_button.text()
        
        self._pending_actions_panel.setEnabled( False )
        
        job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
        
        job.start()
        
    
    def _PendingRowActivated( self, model_index: QC.QModelIndex ):
        
        if not model_index.isValid():
            
            return
            
        
        row = model_index.row()
        
        ( media_result_1, media_result_2 ) = self._pending_actions_pair_list.model().GetMediaResultPair( row )
        
        self._ShowMediaViewer( media_result_1, media_result_2 )
        
    
    def _RefetchActionedPairs( self ):
        
        def work_callable():
            
            actioned_pairs_with_info = CG.client_controller.Read( 'duplicates_auto_resolution_actioned_pairs', rule, fetch_limit = fetch_limit )
            
            reformatted_actioned_pairs_with_info = [ ( media_result_a, media_result_b, ( duplicate_type, timestamp_ms ) ) for ( media_result_a, media_result_b, duplicate_type, timestamp_ms ) in actioned_pairs_with_info ]
            
            return reformatted_actioned_pairs_with_info
            
        
        def publish_callable( actioned_pairs_with_info ):
            
            self._actioned_pairs_with_info = actioned_pairs_with_info
            
            self._actioned_pairs_label.setText( f'Found {HydrusNumbers.ToHumanInt(len(actioned_pairs_with_info))} pairs.' )
            
            self._actioned_pairs_pair_list.SetData( self._actioned_pairs_with_info )
            
        
        self._actioned_pairs_pair_list.SetData( [] )
        
        rule = self._rule
        fetch_limit = self._actioned_pairs_num_to_fetch.GetValue()
        
        self._actioned_pairs_label.setText( f'fetching and calculating pairs{HC.UNICODE_ELLIPSIS}' )
        
        async_job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
        
        async_job.start()
        
    
    def _RefetchPendingActionPairs( self ):
        
        def work_callable():
            
            pending_action_pairs = CG.client_controller.Read( 'duplicates_auto_resolution_pending_action_pairs', rule, fetch_limit = fetch_limit )
            
            return pending_action_pairs
            
        
        def publish_callable( pending_action_pairs ):
            
            self._pending_action_pairs = pending_action_pairs
            
            self._pending_actions_label.setText( f'Found {HydrusNumbers.ToHumanInt(len(pending_action_pairs))} pairs.' )
            
            self._pending_actions_pair_list.SetData( self._pending_action_pairs )
            
        
        self._pending_actions_pair_list.SetData( [] )
        
        if self._rule.GetOperationMode() == ClientDuplicatesAutoResolution.DUPLICATES_AUTO_RESOLUTION_RULE_OPERATION_MODE_FULLY_AUTOMATIC:
            
            self._pending_actions_label.setText( 'This rule is fully automatic; it will not wait for human approval.' )
            
        else:
            
            rule = self._rule
            fetch_limit = self._pending_pairs_num_to_fetch.GetValue()
            
            self._pending_actions_label.setText( f'fetching and calculating pairs{HC.UNICODE_ELLIPSIS}' )
            
            async_job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
            
            async_job.start()
            
        
    
    def _SelectAllPending( self ):
        
        self._pending_actions_pair_list.selectAll()
        
    
    def _ShowMediaViewer( self, media_result_1, media_result_2 ):
        
        canvas_frame = ClientGUICanvasFrame.CanvasFrame( self.window(), set_parent = True )
        
        page_key = HydrusData.GenerateKey()
        location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY )
        media_results = [ media_result_1, media_result_2 ]
        
        media_results = [ mr for mr in media_results if mr.GetLocationsManager().IsLocal() ]
        
        if len( media_results ) == 0:
            
            ClientGUIDialogsMessage.ShowWarning( self, 'Sorry, but neither of those files is local (they were probably deleted), so they cannot be displayed in the media viewer!' )
            
            return
            
        
        first_hash = media_result_1.GetHash()
        
        canvas_window = ClientGUICanvas.CanvasMediaListBrowser( canvas_frame, page_key, location_context, media_results, first_hash )
        
        canvas_window.canvasWithHoversExiting.connect( CG.client_controller.gui.NotifyMediaViewerExiting )
        
        canvas_frame.SetCanvas( canvas_window )
        
    
    def _UndoSelectedActions( self ):
        
        model = self._actioned_pairs_pair_list.model()
        indices = self._actioned_pairs_pair_list.selectedIndexes()
        
        selected_pairs = { model.GetMediaResultPair( index.row() ) for index in indices }
        
        if len( selected_pairs ) == 0:
            
            return
            
        
        all_hashes = set( itertools.chain.from_iterable( [ ( media_result_1.GetHash(), media_result_2.GetHash() ) for ( media_result_1, media_result_2 ) in selected_pairs ] ) )
        
        message = f'Are you sure you want to undo the auto-resolution actions covering these {HydrusNumbers.ToHumanInt( len( all_hashes ) )} files? This is a serious action.\n\nThe only way to do this reliably is to completely dissolve the respective duplicate group(s), which may undo many other decisions. All the files in the duplicate group(s) (not just what you selected) will be queued up for search in the potential duplicates system once more. Any files that are in trash will be undeleted. This action will not remove the entries from this audit log nor undo any content merge.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result != QW.QDialog.DialogCode.Accepted:
            
            return
            
        
        ClientGUIMediaSimpleActions.UndeleteFiles( all_hashes )
        
        CG.client_controller.WriteSynchronous( 'dissolve_duplicates_group', all_hashes )
        
        self._RefetchActionedPairs()
        
    
    def CloseFromEditDialog( self ):
        
        self.window().close()
        
    
