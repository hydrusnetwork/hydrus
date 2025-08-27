from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusTags

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.duplicates import ClientDuplicates
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui.importing import ClientGUIImportOptions
from hydrus.client.gui.lists import ClientGUIListConstants as CGLC
from hydrus.client.gui.lists import ClientGUIListCtrl
from hydrus.client.gui.metadata import ClientGUITagFilter
from hydrus.client.gui.widgets import ClientGUICommon

class EditDuplicateContentMergeOptionsWidget( ClientGUICommon.StaticBox ):
    
    def __init__( self, parent: QW.QWidget, duplicate_action, duplicate_content_merge_options: ClientDuplicates.DuplicateContentMergeOptions, for_custom_action = False, can_expand = False, start_expanded = True ):
        
        super().__init__( parent, 'duplicate metadata merge options', can_expand = can_expand, start_expanded = start_expanded )
        
        self._duplicate_action = duplicate_action
        self._for_custom_action = for_custom_action
        
        self._not_better_note_st = ClientGUICommon.BetterStaticText( self, label = '' )
        self._not_better_note_st.setWordWrap( True )
        
        #
        
        tag_services_panel = ClientGUICommon.StaticBox( self, 'tag services' )
        
        tag_services_listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( tag_services_panel )
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_DUPLICATE_CONTENT_MERGE_OPTIONS_TAG_SERVICES.ID, self._ConvertTagDataToDisplayTuple, self._ConvertTagDataToSortTuple )
        
        self._tag_service_actions = ClientGUIListCtrl.BetterListCtrlTreeView( tag_services_listctrl_panel, 5, model, delete_key_callback = self._DeleteTag )
        
        tag_services_listctrl_panel.SetListCtrl( self._tag_service_actions )
        
        tag_services_listctrl_panel.AddButton( 'add', self._AddTag )
        self._edit_tag_action_button = tag_services_listctrl_panel.AddButton( 'edit action', self._EditTagAction, enabled_only_on_single_selection = True )
        tag_services_listctrl_panel.AddButton( 'edit filter', self._EditTagFilter, enabled_only_on_single_selection = True )
        tag_services_listctrl_panel.AddButton( 'delete', self._DeleteTag, enabled_only_on_selection = True )
        
        #
        
        rating_services_panel = ClientGUICommon.StaticBox( self, 'rating services' )
        
        rating_services_listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( rating_services_panel )
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_DUPLICATE_CONTENT_MERGE_OPTIONS_RATING_SERVICES.ID, self._ConvertRatingDataToDisplayTuple, self._ConvertRatingDataToSortTuple )
        
        self._rating_service_actions = ClientGUIListCtrl.BetterListCtrlTreeView( rating_services_listctrl_panel, 5, model, delete_key_callback = self._DeleteRating, activation_callback = self._EditRating )
        
        rating_services_listctrl_panel.SetListCtrl( self._rating_service_actions )
        
        rating_services_listctrl_panel.AddButton( 'add', self._AddRating )
        self._edit_rating_button = rating_services_listctrl_panel.AddButton( 'edit action', self._EditRating, enabled_only_on_single_selection = True )
        rating_services_listctrl_panel.AddButton( 'delete', self._DeleteRating, enabled_only_on_selection = True )
        
        #
        
        self._sync_archive_action = ClientGUICommon.BetterChoice( self )
        
        self._sync_archive_action.addItem( 'make no change', ClientDuplicates.SYNC_ARCHIVE_NONE )
        self._sync_archive_action.addItem( 'if one is archived, archive the other', ClientDuplicates.SYNC_ARCHIVE_IF_ONE_DO_BOTH )
        self._sync_archive_action.addItem( 'always archive both', ClientDuplicates.SYNC_ARCHIVE_DO_BOTH_REGARDLESS )
        
        self._sync_archive_action.setToolTip( ClientGUIFunctions.WrapToolTip( 'In the duplicates auto-resolution system, "always archive both" (which assumes human eyes) will be treated as "if one is archived, archive the other".' ) )
        
        self._sync_urls_action = ClientGUICommon.BetterChoice( self )
        self._sync_urls_action.setToolTip( ClientGUIFunctions.WrapToolTip( 'This will also sync domain modified times for the respective URLs, assuming they are reasonable and older than any existing domain times.' ) )
        
        self._sync_file_modified_date_action = ClientGUICommon.BetterChoice( self )
        self._sync_notes_action = ClientGUICommon.BetterChoice( self )
        
        self._sync_note_import_options_button = ClientGUICommon.BetterButton( self, 'note merge settings', self._EditNoteImportOptions )
        
        #
        
        self._UpdateDuplicateTypeControls()
        
        self._SetValue( duplicate_content_merge_options )
        
        #
        
        tag_services_panel.Add( tag_services_listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        st = ClientGUICommon.BetterStaticText( rating_services_panel, label = 'If both files have a rating, inc/dec ratings will move/copy via simple addition. Star ratings will overwrite only if the source has a higher rating than the destination.' )
        st.setWordWrap( True )
        
        rating_services_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
        rating_services_panel.Add( rating_services_listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        self.Add( self._not_better_note_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        self.Add( tag_services_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        self.Add( rating_services_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        rows = []
        
        rows.append( ( 'sync archived status?: ', self._sync_archive_action ) )
        rows.append( ( 'sync file modified time?: ', self._sync_file_modified_date_action ) )
        rows.append( ( 'sync known urls?: ', self._sync_urls_action ) )
        rows.append( ( 'sync notes?: ', self._sync_notes_action ) )
        rows.append( ( '', self._sync_note_import_options_button ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        self.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self._UpdateNoteControls()
        
        self._sync_notes_action.currentIndexChanged.connect( self._UpdateNoteControls )
        
    
    def _AddRating( self ):
        
        services_manager = CG.client_controller.services_manager
        
        choice_tuples = []
        
        for service in services_manager.GetServices( HC.RATINGS_SERVICES ):
            
            service_key = service.GetServiceKey()
            
            if service_key not in self._service_keys_to_rating_options:
                
                name = service.GetName()
                
                choice_tuples.append( ( name, service_key ) )
                
            
        
        if len( choice_tuples ) == 0:
            
            ClientGUIDialogsMessage.ShowWarning( self, 'You have no more tag or rating services to add! Try editing the existing ones instead!' )
            
        else:
            
            try:
                
                service_key = ClientGUIDialogsQuick.SelectFromList( self, 'select service', choice_tuples )
                
            except HydrusExceptions.CancelledException:
                
                return
                
            
            if self._duplicate_action == HC.DUPLICATE_BETTER:
                
                service = services_manager.GetService( service_key )
                
                service_type = service.GetServiceType()
                
                if service_type == HC.LOCAL_RATING_INCDEC:
                    
                    str_lookup_dict = HC.content_number_merge_string_lookup
                    
                elif service_type in HC.STAR_RATINGS_SERVICES:
                    
                    str_lookup_dict = HC.content_merge_string_lookup
                    
                else:
                    
                    return
                    
                
                possible_actions = [ HC.CONTENT_MERGE_ACTION_COPY, HC.CONTENT_MERGE_ACTION_MOVE, HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE ]
                
                choice_tuples = [ ( str_lookup_dict[ action ], action ) for action in possible_actions ]
                
                try:
                    
                    action = ClientGUIDialogsQuick.SelectFromList( self, 'select action', choice_tuples )
                    
                except HydrusExceptions.CancelledException:
                    
                    return
                    
                
            else:
                
                action = HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE
                
            
            self._service_keys_to_rating_options[ service_key ] = action
            
            self._rating_service_actions.AddData( service_key, select_sort_and_scroll = True )
            
        
    
    def _AddTag( self ):
        
        services_manager = CG.client_controller.services_manager
        
        choice_tuples = []
        
        for service in services_manager.GetServices( HC.REAL_TAG_SERVICES ):
            
            service_key = service.GetServiceKey()
            
            if service_key not in self._service_keys_to_tag_options:
                
                name = service.GetName()
                
                choice_tuples.append( ( name, service_key ) )
                
            
        
        if len( choice_tuples ) == 0:
            
            ClientGUIDialogsMessage.ShowWarning( self, 'You have no more tag or rating services to add! Try editing the existing ones instead!' )
            
        else:
            
            try:
                
                service_key = ClientGUIDialogsQuick.SelectFromList( self, 'select service', choice_tuples )
                
            except HydrusExceptions.CancelledException:
                
                return
                
            
            if self._duplicate_action == HC.DUPLICATE_BETTER:
                
                service = services_manager.GetService( service_key )
                
                if service.GetServiceType() == HC.TAG_REPOSITORY:
                    
                    possible_actions = [ HC.CONTENT_MERGE_ACTION_COPY, HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE ]
                    
                else:
                    
                    possible_actions = [ HC.CONTENT_MERGE_ACTION_COPY, HC.CONTENT_MERGE_ACTION_MOVE, HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE ]
                    
                
                choice_tuples = [ ( HC.content_merge_string_lookup[ action ], action ) for action in possible_actions ]
                
                try:
                    
                    action = ClientGUIDialogsQuick.SelectFromList( self, 'select action', choice_tuples )
                    
                except HydrusExceptions.CancelledException:
                    
                    return
                    
                
            else:
                
                action = HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE
                
            
            tag_filter = HydrusTags.TagFilter()
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit which tags will be merged' ) as dlg_3:
                
                namespaces = CG.client_controller.network_engine.domain_manager.GetParserNamespaces()
                
                panel = ClientGUITagFilter.EditTagFilterPanel( dlg_3, tag_filter, namespaces = namespaces )
                
                dlg_3.SetPanel( panel )
                
                if dlg_3.exec() == QW.QDialog.DialogCode.Accepted:
                    
                    tag_filter = panel.GetValue()
                    
                    self._service_keys_to_tag_options[ service_key ] = ( action, tag_filter )
                    
                    self._tag_service_actions.AddData( service_key, select_sort_and_scroll = True )
                    
                
            
        
    
    def _ConvertRatingDataToDisplayTuple( self, service_key ):
        
        action = self._service_keys_to_rating_options[ service_key ]
        
        try:
            
            service = CG.client_controller.services_manager.GetService( service_key )
            
            service_name = service.GetName()
            
            service_type = service.GetServiceType()
            
        except HydrusExceptions.DataMissing:
            
            service_name = 'missing service!'
            service_type = HC.LOCAL_RATING_LIKE
            
        
        if service_type == HC.LOCAL_RATING_INCDEC:
            
            str_lookup_dict = HC.content_number_merge_string_lookup
            
        else:
            
            str_lookup_dict = HC.content_merge_string_lookup
            
        
        pretty_action = str_lookup_dict[ action ]
        
        display_tuple = ( service_name, pretty_action )
        
        return display_tuple
        
    
    _ConvertRatingDataToSortTuple = _ConvertRatingDataToDisplayTuple
    
    def _ConvertTagDataToDisplayTuple( self, service_key ):
        
        ( action, tag_filter ) = self._service_keys_to_tag_options[ service_key ]
        
        try:
            
            service_name = CG.client_controller.services_manager.GetName( service_key )
            
        except HydrusExceptions.DataMissing:
            
            service_name = 'missing service!'
            
        
        pretty_action = HC.content_merge_string_lookup[ action ]
        pretty_tag_filter = tag_filter.ToPermittedString()
        
        display_tuple = ( service_name, pretty_action, pretty_tag_filter )
        
        return display_tuple
        
    
    _ConvertTagDataToSortTuple = _ConvertTagDataToDisplayTuple
    
    def _DeleteRating( self ):
        
        result = ClientGUIDialogsQuick.GetYesNo( self, 'Remove all selected?' )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            for service_key in self._rating_service_actions.GetData( only_selected = True ):
                
                del self._service_keys_to_rating_options[ service_key ]
                
            
            self._rating_service_actions.DeleteSelected()
            
        
    
    def _DeleteTag( self ):
        
        result = ClientGUIDialogsQuick.GetYesNo( self, 'Remove all selected?' )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            for service_key in self._tag_service_actions.GetData( only_selected = True ):
                
                del self._service_keys_to_tag_options[ service_key ]
                
            
            self._tag_service_actions.DeleteSelected()
            
        
    
    def _EditNoteImportOptions( self ):
        
        allow_default_selection = False
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit note merge options' ) as dlg:
            
            panel = ClientGUIImportOptions.EditNoteImportOptionsPanel( dlg, self._sync_note_import_options, allow_default_selection, simple_mode = True )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                self._sync_note_import_options = panel.GetValue()
                
            
        
    
    def _EditRating( self ):
        
        service_key = self._rating_service_actions.GetTopSelectedData()
        
        if service_key is None:
            
            return
            
        
        action = self._service_keys_to_rating_options[ service_key ]
        
        if self._duplicate_action == HC.DUPLICATE_BETTER:
            
            service = CG.client_controller.services_manager.GetService( service_key )
            
            service_type = service.GetServiceType()
            
            if service_type == HC.LOCAL_RATING_INCDEC:
                
                str_lookup_dict = HC.content_number_merge_string_lookup
                
            elif service_type in HC.STAR_RATINGS_SERVICES:
                
                str_lookup_dict = HC.content_merge_string_lookup
                
            else:
                
                return
                
            
            possible_actions = [ HC.CONTENT_MERGE_ACTION_COPY, HC.CONTENT_MERGE_ACTION_MOVE, HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE ]
            
            choice_tuples = [ ( str_lookup_dict[ action ], action ) for action in possible_actions ]
            
            try:
                
                action = ClientGUIDialogsQuick.SelectFromList( self, 'select action', choice_tuples, value_to_select = action )
                
            except HydrusExceptions.CancelledException:
                
                return
                
            
        else: # This shouldn't get fired because the edit button is hidden, but w/e
            
            action = HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE
            
        
        self._service_keys_to_rating_options[ service_key ] = action
        
        self._rating_service_actions.UpdateDatas( ( service_key, ) )
        
        self._rating_service_actions.Sort()
        
    
    def _EditTagAction( self ):
        
        service_key = self._tag_service_actions.GetTopSelectedData()
        
        if service_key is None:
            
            return
            
        
        ( action, tag_filter ) = self._service_keys_to_tag_options[ service_key ]
        
        if self._duplicate_action == HC.DUPLICATE_BETTER:
            
            service = CG.client_controller.services_manager.GetService( service_key )
            
            if service.GetServiceType() == HC.TAG_REPOSITORY:
                
                possible_actions = [ HC.CONTENT_MERGE_ACTION_COPY, HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE ]
                
            else:
                
                possible_actions = [ HC.CONTENT_MERGE_ACTION_COPY, HC.CONTENT_MERGE_ACTION_MOVE, HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE ]
                
            
            choice_tuples = [ ( HC.content_merge_string_lookup[ action ], action ) for action in possible_actions ]
            
            try:
                
                action = ClientGUIDialogsQuick.SelectFromList( self, 'select action', choice_tuples, value_to_select = action )
                
            except HydrusExceptions.CancelledException:
                
                return
                
            
        else:
            
            action = HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE
            
        
        self._service_keys_to_tag_options[ service_key ] = ( action, tag_filter )
        
        self._tag_service_actions.UpdateDatas( ( service_key, ) )
        
        self._tag_service_actions.Sort()
        
    
    def _EditTagFilter( self ):
        
        service_key = self._tag_service_actions.GetTopSelectedData()
        
        if service_key is None:
            
            return
            
        
        ( action, tag_filter ) = self._service_keys_to_tag_options[ service_key ]
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit which tags will be merged' ) as dlg_3:
            
            namespaces = CG.client_controller.network_engine.domain_manager.GetParserNamespaces()
            
            panel = ClientGUITagFilter.EditTagFilterPanel( dlg_3, tag_filter, namespaces = namespaces )
            
            dlg_3.SetPanel( panel )
            
            if dlg_3.exec() == QW.QDialog.DialogCode.Accepted:
                
                tag_filter = panel.GetValue()
                
                self._service_keys_to_tag_options[ service_key ] = ( action, tag_filter )
                
                self._tag_service_actions.UpdateDatas( ( service_key, ) )
                
                self._tag_service_actions.Sort()
                
            
        
    
    def _SetValue( self, duplicate_content_merge_options: ClientDuplicates.DuplicateContentMergeOptions ):
        
        tag_service_options = duplicate_content_merge_options.GetTagServiceActions()
        rating_service_options = duplicate_content_merge_options.GetRatingServiceActions()
        sync_archive_action = duplicate_content_merge_options.GetSyncArchiveAction()
        sync_urls_action = duplicate_content_merge_options.GetSyncURLsAction()
        sync_file_modified_date_action = duplicate_content_merge_options.GetSyncFileModifiedDateAction()
        sync_notes_action = duplicate_content_merge_options.GetSyncNotesAction()
        self._sync_note_import_options = duplicate_content_merge_options.GetSyncNoteImportOptions()
        
        services_manager = CG.client_controller.services_manager
        
        self._service_keys_to_tag_options = { service_key : ( action, tag_filter ) for ( service_key, action, tag_filter ) in tag_service_options if services_manager.ServiceExists( service_key ) }
        
        self._tag_service_actions.SetData( list( self._service_keys_to_tag_options.keys() ) )
        
        self._tag_service_actions.Sort()
        
        self._service_keys_to_rating_options = { service_key : action for ( service_key, action ) in rating_service_options if services_manager.ServiceExists( service_key ) }
        
        self._rating_service_actions.SetData( list( self._service_keys_to_rating_options.keys() ) )
        
        self._rating_service_actions.Sort()
        
        self._sync_archive_action.SetValue( sync_archive_action )
        
        #
        
        if self._duplicate_action in ( HC.DUPLICATE_ALTERNATE, HC.DUPLICATE_FALSE_POSITIVE ) and not self._for_custom_action:
            
            self._sync_urls_action.setEnabled( False )
            self._sync_file_modified_date_action.setEnabled( False )
            self._sync_notes_action.setEnabled( False )
            
            self._sync_urls_action.SetValue( HC.CONTENT_MERGE_ACTION_NONE )
            self._sync_file_modified_date_action.SetValue( HC.CONTENT_MERGE_ACTION_NONE )
            self._sync_notes_action.SetValue( HC.CONTENT_MERGE_ACTION_NONE )
            
        else:
            
            self._sync_urls_action.setEnabled( True )
            self._sync_file_modified_date_action.setEnabled( True )
            self._sync_notes_action.setEnabled( True )
            
            self._sync_urls_action.SetValue( sync_urls_action )
            self._sync_file_modified_date_action.SetValue( sync_file_modified_date_action )
            self._sync_notes_action.SetValue( sync_notes_action )
            
        
    
    def _UpdateDuplicateTypeControls( self ):
        
        we_better_dupe = self._duplicate_action == HC.DUPLICATE_BETTER
        
        note = 'Editing for "{}".'.format( HC.duplicate_type_string_lookup[ self._duplicate_action ] )
        
        if not we_better_dupe:
            
            note += '\n' * 2
            note += 'Note that this has fewer actions than the "this is better" decision. You can mostly just copy in both directions.'
            
        
        self._edit_tag_action_button.setVisible( we_better_dupe )
        
        self._not_better_note_st.setText( note )
        
        self._edit_rating_button.setVisible( we_better_dupe ) # because there is only one valid action otherwise
        
        self._sync_urls_action.clear()
        self._sync_file_modified_date_action.clear()
        self._sync_notes_action.clear()
        
        self._sync_urls_action.addItem( HC.content_merge_string_lookup[ HC.CONTENT_MERGE_ACTION_NONE ], HC.CONTENT_MERGE_ACTION_NONE )
        self._sync_file_modified_date_action.addItem( HC.content_modified_date_merge_string_lookup[ HC.CONTENT_MERGE_ACTION_NONE ], HC.CONTENT_MERGE_ACTION_NONE )
        self._sync_notes_action.addItem( HC.content_merge_string_lookup[ HC.CONTENT_MERGE_ACTION_NONE ], HC.CONTENT_MERGE_ACTION_NONE )
        
        if we_better_dupe:
            
            self._sync_urls_action.addItem( HC.content_merge_string_lookup[ HC.CONTENT_MERGE_ACTION_COPY ], HC.CONTENT_MERGE_ACTION_COPY )
            self._sync_file_modified_date_action.addItem( HC.content_modified_date_merge_string_lookup[ HC.CONTENT_MERGE_ACTION_COPY ], HC.CONTENT_MERGE_ACTION_COPY )
            self._sync_notes_action.addItem( HC.content_merge_string_lookup[ HC.CONTENT_MERGE_ACTION_COPY ], HC.CONTENT_MERGE_ACTION_COPY )
            self._sync_notes_action.addItem( HC.content_merge_string_lookup[ HC.CONTENT_MERGE_ACTION_MOVE ], HC.CONTENT_MERGE_ACTION_MOVE )
            
        
        self._sync_urls_action.addItem( HC.content_merge_string_lookup[ HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE ], HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE )
        self._sync_file_modified_date_action.addItem( HC.content_modified_date_merge_string_lookup[ HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE ], HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE )
        self._sync_notes_action.addItem( HC.content_merge_string_lookup[ HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE ], HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE )
        
    
    def _UpdateNoteControls( self ):
        
        sync_notes_action = self._sync_notes_action.GetValue()
        
        self._sync_note_import_options_button.setEnabled( sync_notes_action != HC.CONTENT_MERGE_ACTION_NONE )
        
    
    def GetDuplicateAction( self ):
        
        return self._duplicate_action
        
    
    def GetValue( self ) -> ClientDuplicates.DuplicateContentMergeOptions:
        
        tag_service_actions = [ ( service_key, action, tag_filter ) for ( service_key, ( action, tag_filter ) ) in self._service_keys_to_tag_options.items() ]
        rating_service_actions = [ ( service_key, action ) for ( service_key, action ) in self._service_keys_to_rating_options.items() ]
        sync_archive_action = self._sync_archive_action.GetValue()
        sync_urls_action = self._sync_urls_action.GetValue()
        sync_file_modified_date_action = self._sync_file_modified_date_action.GetValue()
        sync_notes_action = self._sync_notes_action.GetValue()
        
        duplicate_content_merge_options = ClientDuplicates.DuplicateContentMergeOptions()
        
        duplicate_content_merge_options.SetTagServiceActions( tag_service_actions )
        duplicate_content_merge_options.SetRatingServiceActions( rating_service_actions )
        duplicate_content_merge_options.SetSyncArchiveAction( sync_archive_action )
        duplicate_content_merge_options.SetSyncURLsAction( sync_urls_action )
        duplicate_content_merge_options.SetSyncFileModifiedDateAction( sync_file_modified_date_action )
        duplicate_content_merge_options.SetSyncNotesAction( sync_notes_action )
        duplicate_content_merge_options.SetSyncNoteImportOptions( self._sync_note_import_options )
        
        return duplicate_content_merge_options
        
    
    def SetValue( self, duplicate_type, duplicate_content_merge_options: ClientDuplicates.DuplicateContentMergeOptions ):
        
        self._duplicate_action = duplicate_type
        self._UpdateDuplicateTypeControls()
        self._SetValue( duplicate_content_merge_options )
        
    
