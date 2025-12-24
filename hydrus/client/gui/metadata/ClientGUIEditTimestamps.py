import collections.abc
import json

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusPaths
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTime

from hydrus.client import ClientApplicationCommand as CAC
from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientTime
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIShortcuts
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListConstants as CGLC
from hydrus.client.gui.lists import ClientGUIListCtrl
from hydrus.client.gui.metadata import ClientGUITime
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.gui.widgets import ClientGUIMenuButton
from hydrus.client.media import ClientMedia
from hydrus.client.metadata import ClientContentUpdates

class EditFileTimestampsPanel( CAC.ApplicationCommandProcessorMixin, ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, ordered_medias: list[ ClientMedia.MediaSingleton ] ):
        
        super().__init__( parent )
        
        self._ordered_medias = ordered_medias
        
        #
        
        # TODO: wangle archived time so it can set time to null-time medias that are nonetheless not hasinbox
        # it'll have to do one of those 'do you want to set this changed value for just the files that already have a time, or all of them?'
        self._archived_time = ClientGUITime.DateTimesButton( self, milliseconds_allowed = True, only_past_dates = True )
        self._file_modified_time = ClientGUITime.DateTimesButton( self, milliseconds_allowed = True, only_past_dates = True )
        
        self._last_viewed_media_viewer_time = ClientGUITime.DateTimesButton( self, milliseconds_allowed = True, only_past_dates = True )
        self._last_viewed_preview_viewer_time = ClientGUITime.DateTimesButton( self, milliseconds_allowed = True, only_past_dates = True )
        
        self._file_modified_time_warning_st = ClientGUICommon.BetterStaticText( self, label = 'initialising' )
        self._file_modified_time_warning_st.setObjectName( 'HydrusWarning' )
        self._file_modified_time_warning_st.setAlignment( QC.Qt.AlignmentFlag.AlignCenter )
        self._file_modified_time_warning_st.setVisible( False )
        
        domain_box = ClientGUICommon.StaticBox( self, 'web domain times' )
        
        self._domain_modified_list_ctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( domain_box )
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_DOMAIN_MODIFIED_TIMESTAMPS.ID, self._ConvertDomainToDomainModifiedDisplayTuple, self._ConvertDomainToDomainModifiedSortTuple )
        
        self._domain_modified_list_ctrl = ClientGUIListCtrl.BetterListCtrlTreeView( self._domain_modified_list_ctrl_panel, 8, model, use_simple_delete = True, activation_callback = self._EditDomainModifiedTimestamp )
        
        self._domain_modified_list_ctrl_panel.SetListCtrl( self._domain_modified_list_ctrl )
        
        self._domain_modified_list_ctrl_panel.AddButton( 'add', self._AddDomainModifiedTimestamp )
        self._domain_modified_list_ctrl_panel.AddButton( 'edit', self._EditDomainModifiedTimestamp, enabled_only_on_selection = True )
        self._domain_modified_list_ctrl_panel.AddDeleteButton()
        
        self._domain_modified_list_ctrl_data_dict = {}
        
        file_services_box = ClientGUICommon.StaticBox( self, 'file services' )
        
        self._file_services_list_ctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( file_services_box )
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_FILE_SERVICE_TIMESTAMPS.ID, self._ConvertDataRowToFileServiceDisplayTuple, self._ConvertDataRowToFileServiceSortTuple )
        
        self._file_services_list_ctrl = ClientGUIListCtrl.BetterListCtrlTreeView( self._file_services_list_ctrl_panel, 8, model, activation_callback = self._EditFileServiceTimestamp )
        
        self._file_services_list_ctrl_panel.SetListCtrl( self._file_services_list_ctrl )
        
        self._file_services_list_ctrl_panel.AddButton( 'edit', self._EditFileServiceTimestamp, enabled_only_on_selection = True )
        # TODO: An extension here is to add an 'add' button for files that have a _missing_ delete time
        # and/or wangle the controls and stuff so a None result is piped along and displays and is settable here
        
        self._file_services_list_ctrl_data_dict = {}
        
        #
        
        rows = []
        
        #
        
        datetime_value_range = ClientGUITime.DateTimeWidgetValueRange()
        
        for media in self._ordered_medias:
            
            datetime_value_range.AddValueTimestampMS( media.GetTimesManager().GetFileModifiedTimestampMS() )
            
        
        if datetime_value_range.IsAllNull():
            
            self._file_modified_time.setEnabled( False )
            self._file_modified_time.setText( 'unknown -- run file maintenance to determine' )
            
        else:
            
            self._file_modified_time.SetValue( datetime_value_range )
            
        
        rows.append( ( 'file modified time: ', self._file_modified_time ) )
        
        rows.append( self._file_modified_time_warning_st )
        
        #
        
        datetime_value_range = ClientGUITime.DateTimeWidgetValueRange()
        
        for media in self._ordered_medias:
            
            if media.HasInbox():
                
                continue
                
            
            datetime_value_range.AddValueTimestampMS( media.GetTimesManager().GetArchivedTimestampMS() )
            
        
        if datetime_value_range.IsAllNull():
            
            self._archived_time.setVisible( False )
            self._archived_time.setEnabled( False )
            
        else:
            
            self._archived_time.SetValue( datetime_value_range )
            
            rows.append( ( 'archived time: ', self._archived_time ) )
            
        
        #
        
        datetime_value_range = ClientGUITime.DateTimeWidgetValueRange()
        
        for media in self._ordered_medias:
            
            datetime_value_range.AddValueTimestampMS( media.GetTimesManager().GetLastViewedTimestampMS( CC.CANVAS_MEDIA_VIEWER ) )
            
        
        if datetime_value_range.IsAllNull():
            
            self._last_viewed_media_viewer_time.setVisible( False )
            self._last_viewed_media_viewer_time.setEnabled( False )
            
        else:
            
            self._last_viewed_media_viewer_time.SetValue( datetime_value_range )
            
            rows.append( ( 'last viewed in media viewer: ', self._last_viewed_media_viewer_time ) )
            
        
        datetime_value_range = ClientGUITime.DateTimeWidgetValueRange()
        
        for media in self._ordered_medias:
            
            datetime_value_range.AddValueTimestampMS( media.GetTimesManager().GetLastViewedTimestampMS( CC.CANVAS_PREVIEW ) )
            
        
        if datetime_value_range.IsAllNull():
            
            self._last_viewed_preview_viewer_time.setVisible( False )
            self._last_viewed_preview_viewer_time.setEnabled( False )
            
        else:
            
            self._last_viewed_preview_viewer_time.SetValue( datetime_value_range )
            
            rows.append( ( 'last viewed in preview viewer: ', self._last_viewed_preview_viewer_time ) )
            
        
        #
        
        domains_to_datetime_value_ranges = collections.defaultdict( ClientGUITime.DateTimeWidgetValueRange )
        domains_to_hashes = collections.defaultdict( list )
        
        for media in self._ordered_medias:
            
            hash = media.GetHash()
            
            for ( domain, timestamp_ms ) in media.GetTimesManager().GetDomainModifiedTimestampsMS().items():
                
                domains_to_hashes[ domain ].append( hash )
                
                domains_to_datetime_value_ranges[ domain ].AddValueTimestampMS( timestamp_ms )
                
            
        
        user_has_edited = False
        
        domains = list( domains_to_hashes.keys() )
        
        self._original_domain_modified_domains = set( domains )
        
        for domain in domains:
            
            hashes = domains_to_hashes[ domain ]
            datetime_value_range = domains_to_datetime_value_ranges[ domain ]
            
            datetime_value_range.AddValueQtDateTime( None, num_to_add = len( self._ordered_medias ) - len( hashes ) )
            
            self._domain_modified_list_ctrl_data_dict[ domain ] = ( hashes, datetime_value_range, user_has_edited )
            
        
        self._domain_modified_list_ctrl.AddDatas( domains )
        self._domain_modified_list_ctrl.Sort()
        
        file_service_keys_to_datetime_value_ranges = collections.defaultdict( ClientGUITime.DateTimeWidgetValueRange )
        file_service_keys_and_timestamp_types_to_hashes = collections.defaultdict( list )
        
        for media in self._ordered_medias:
            
            for timestamp_data in media.GetTimesManager().GetFileServiceTimestampDatas():
                
                file_service_key = timestamp_data.location
                timestamp_type = timestamp_data.timestamp_type
                
                row = ( file_service_key, timestamp_type )
                
                file_service_keys_and_timestamp_types_to_hashes[ row ].append( media.GetHash() )
                
                file_service_keys_to_datetime_value_ranges[ row ].AddValueTimestampMS( timestamp_data.timestamp_ms )
                
            
        
        user_has_edited = False
        
        file_service_keys_and_timestamp_types = list( file_service_keys_and_timestamp_types_to_hashes.keys() )
        
        for row in file_service_keys_and_timestamp_types:
            
            hashes = file_service_keys_and_timestamp_types_to_hashes[ row ]
            datetime_value_range = file_service_keys_to_datetime_value_ranges[ row ]
            
            datetime_value_range.AddValueQtDateTime( None, num_to_add = len( self._ordered_medias ) - len( hashes ) )
            
            self._file_services_list_ctrl_data_dict[ row ] = ( hashes, datetime_value_range, user_has_edited )
            
        
        self._file_services_list_ctrl.AddDatas( file_service_keys_and_timestamp_types )
        self._file_services_list_ctrl.Sort()
        
        #
        
        menu_template_items = []
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'all times', 'Copy every time here for pasting in another file\'s dialog.', self._Copy ) )
        
        c = HydrusData.Call( self._Copy, allowed_timestamp_types = ( HC.TIMESTAMP_TYPE_IMPORTED, HC.TIMESTAMP_TYPE_PREVIOUSLY_IMPORTED, HC.TIMESTAMP_TYPE_DELETED ) )
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'all file service times', 'Copy every imported/deleted/previously imported time here for pasting in another file\'s dialog.', c ) )
        
        self._copy_button = ClientGUIMenuButton.MenuIconButton( self, CC.global_icons().copy, menu_template_items )
        self._copy_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'Copy timestamps to the clipboard.' ) )
        
        self._paste_button = ClientGUICommon.IconButton( self, CC.global_icons().paste, self._Paste )
        self._paste_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'Paste timestamps from another timestamps dialog.\n\nCannot be simple strings, this needs to be rich data from another dialog. It also cannot create new web domain entries if the new file does not share entries which what was copied!' ) )
        
        #
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        st = ClientGUICommon.BetterStaticText( file_services_box, 'Select multiple domains to set the same time to all simultaneously.' )
        st.setWordWrap( True )
        
        domain_box.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
        domain_box.Add( self._domain_modified_list_ctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        st = ClientGUICommon.BetterStaticText( file_services_box, 'Select multiple services to set the same time to all simultaneously.' )
        st.setWordWrap( True )
        
        file_services_box.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
        file_services_box.Add( self._file_services_list_ctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        button_hbox = QP.HBoxLayout()
        
        if len( self._ordered_medias ) != 1:
            
            self._copy_button.hide()
            
        
        QP.AddToLayout( button_hbox, self._copy_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( button_hbox, self._paste_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, domain_box, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, file_services_box, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, button_hbox, CC.FLAGS_ON_RIGHT )
        
        self.widget().setLayout( vbox )
        
        self._my_shortcut_handler = ClientGUIShortcuts.ShortcutsHandler( self, self, [ 'global', 'media' ] )
        
        self._file_modified_time.dateTimeChanged.connect( self._ShowFileModifiedWarning )
        
        ClientGUIFunctions.SetFocusLater( self )
        
    
    def _ConvertDomainToDomainModifiedDisplayTuple( self, domain ):
        
        ( hashes, datetime_value_range, user_has_edited ) = self._domain_modified_list_ctrl_data_dict[ domain ]
        
        pretty_timestamp = datetime_value_range.ToString()
        
        display_tuple = ( domain, pretty_timestamp )
        
        return display_tuple
        
    
    def _ConvertDomainToDomainModifiedSortTuple( self, domain ):
        
        ( hashes, datetime_value_range, user_has_edited ) = self._domain_modified_list_ctrl_data_dict[ domain ]
        
        sort_timestamp = datetime_value_range
        
        sort_tuple = ( domain, sort_timestamp )
        
        return sort_tuple
        
    
    def _ConvertDataRowToFileServiceDisplayTuple( self, row ):
        
        ( file_service_key, timestamp_type ) = row
        
        ( hashes, datetime_value_range, user_has_edited ) = self._file_services_list_ctrl_data_dict[ row ]
        
        try:
            
            pretty_name = CG.client_controller.services_manager.GetName( file_service_key )
            
        except HydrusExceptions.DataMissing:
            
            pretty_name = 'unknown service!'
            
        
        pretty_timestamp_type = HC.timestamp_type_str_lookup[ timestamp_type ]
        pretty_timestamp = datetime_value_range.ToString()
        
        display_tuple = ( pretty_name, pretty_timestamp_type, pretty_timestamp )
        
        return display_tuple
        
    
    def _ConvertDataRowToFileServiceSortTuple( self, row ):
        
        ( file_service_key, timestamp_type ) = row
        
        ( hashes, datetime_value_range, user_has_edited ) = self._file_services_list_ctrl_data_dict[ row ]
        
        try:
            
            pretty_name = CG.client_controller.services_manager.GetName( file_service_key )
            
        except HydrusExceptions.DataMissing:
            
            pretty_name = 'unknown service!'
            
        
        sort_name = pretty_name
        
        pretty_timestamp_type = HC.timestamp_type_str_lookup[ timestamp_type ]
        
        sort_timestamp_type = pretty_timestamp_type
        
        sort_timestamp = datetime_value_range
        
        sort_tuple = ( sort_name, sort_timestamp_type, sort_timestamp )
        
        return sort_tuple
        
    
    def _Copy( self, allowed_timestamp_types = None ):
        
        if len( self._ordered_medias ) > 1:
            
            return
            
        
        list_of_timestamp_data = HydrusSerialisable.SerialisableList( [ timestamp_data for ( hashes, timestamp_data, step_ms ) in self._GetValidTimestampDatas() ] )
        
        if allowed_timestamp_types is not None:
            
            list_of_timestamp_data = HydrusSerialisable.SerialisableList( [ timestamp_data for timestamp_data in list_of_timestamp_data if timestamp_data.timestamp_type in allowed_timestamp_types ] )
            
        
        text = json.dumps( list_of_timestamp_data.GetSerialisableTuple() )
        
        CG.client_controller.pub( 'clipboard', 'text', text )
        
    
    def _AddDomainModifiedTimestamp( self ):
        
        message = 'Enter domain.'
        
        try:
            
            domain = ClientGUIDialogsQuick.EnterText( self, message )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        for existing_domain in self._domain_modified_list_ctrl.GetData():
            
            if domain == existing_domain:
                
                ClientGUIDialogsMessage.ShowWarning( self, 'Sorry, that domain already exists!' )
                
                return
                
            
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit datetime' ) as dlg_2:
            
            hashes = [ m.GetHash() for m in self._ordered_medias ]
            
            panel = ClientGUIScrolledPanels.EditSingleCtrlPanel( dlg_2 )
            
            control = ClientGUITime.DateTimesCtrl( self, seconds_allowed = True, milliseconds_allowed = True, none_allowed = False, only_past_dates = True )
            
            datetime_value_range = ClientGUITime.DateTimeWidgetValueRange()
            
            qt_datetime = QC.QDateTime.currentDateTime()
            
            datetime_value_range.AddValueQtDateTime( qt_datetime, num_to_add = len( hashes ) )
            
            control.SetValue( datetime_value_range )
            
            panel.SetControl( control )
            
            dlg_2.SetPanel( panel )
            
            if dlg_2.exec() == QW.QDialog.DialogCode.Accepted: # no 'haschanges' check here, we are ok with starting value
                
                new_datetime_value_range = control.GetValue()
                
                user_has_edited = True
                
                self._domain_modified_list_ctrl_data_dict[ domain ] = ( hashes, new_datetime_value_range, user_has_edited )
                
                self._domain_modified_list_ctrl.AddData( domain, select_sort_and_scroll = True )
                
            
        
    
    def _EditDomainModifiedTimestamp( self ):
        
        # We intentionally allow multiple domains here, rather than GetTopSelectedData stuff
        
        selected_domains = self._domain_modified_list_ctrl.GetData( only_selected = True )
        
        if len( selected_domains ) == 0:
            
            return
            
        
        first_domain = selected_domains[0]
        
        ( hashes, datetime_value_range, user_has_edited ) = self._domain_modified_list_ctrl_data_dict[ first_domain ]
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit datetime' ) as dlg:
            
            panel = ClientGUIScrolledPanels.EditSingleCtrlPanel( dlg )
            
            control = ClientGUITime.DateTimesCtrl( self, seconds_allowed = True, milliseconds_allowed = True, none_allowed = False, only_past_dates = True )
            
            control.SetValue( datetime_value_range )
            
            panel.SetControl( control )
            
            dlg.SetPanel( panel )
            
            override_with_all_hashes = False
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted and control.HasChanges():
                
                edited_datetime_value_range = control.GetValue()
                
                if len( hashes ) < len( self._ordered_medias ):
                    
                    result = ClientGUIDialogsQuick.GetYesNo( self, 'Not every file this dialog was launched on has a time for this domain. Do you want to apply what you just set to everything, or just the files that started with this domain?', yes_label = 'all files', no_label = 'only edit existing values' )
                    
                    if result == QW.QDialog.DialogCode.Accepted:
                        
                        override_with_all_hashes = True
                        
                    
                
                new_user_has_edited = True
                
                for domain in selected_domains:
                    
                    ( hashes, old_datetime_value_range, old_user_has_edited ) = self._domain_modified_list_ctrl_data_dict[ domain ]
                    
                    if edited_datetime_value_range.HasFixedValue():
                        
                        new_datetime_value_range = old_datetime_value_range.DuplicateWithNewQtDateTime( edited_datetime_value_range.GetFixedValue() )
                        
                    else:
                        
                        # don't think this will happen outside of crazy edge-cases
                        new_datetime_value_range = old_datetime_value_range.DuplicateWithNewQtDateTime( None )
                        
                    
                    new_datetime_value_range.SetStepMS( edited_datetime_value_range.GetStepMS() )
                    
                    if override_with_all_hashes:
                        
                        hashes = [ m.GetHash() for m in self._ordered_medias ]
                        
                        new_datetime_value_range = new_datetime_value_range.DuplicateWithOverwrittenNulls()
                        
                    
                    self._domain_modified_list_ctrl_data_dict[ domain ] = ( hashes, new_datetime_value_range, new_user_has_edited )
                    
                
                self._domain_modified_list_ctrl.UpdateDatas( selected_domains )
                
                self._domain_modified_list_ctrl.Sort()
                
            
        
    
    def _EditFileServiceTimestamp( self ):
        
        # We intentionally allow multiple domains here, rather than GetTopSelectedData stuff
        
        selected_file_service_keys_and_timestamp_types = self._file_services_list_ctrl.GetData( only_selected = True )
        
        if len( selected_file_service_keys_and_timestamp_types ) == 0:
            
            return
            
        
        first_row = selected_file_service_keys_and_timestamp_types[0]
        
        ( hashes, example_datetime_value_range, user_has_edited ) = self._file_services_list_ctrl_data_dict[ first_row ]
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit datetime' ) as dlg:
            
            panel = ClientGUIScrolledPanels.EditSingleCtrlPanel( dlg )
            
            control = ClientGUITime.DateTimesCtrl( self, seconds_allowed = True, milliseconds_allowed = True, none_allowed = False, only_past_dates = True )
            
            control.SetValue( example_datetime_value_range )
            
            panel.SetControl( control )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted and control.HasChanges():
                
                edited_datetime_value_range = control.GetValue()
                new_user_has_edited = True
                
                for row in selected_file_service_keys_and_timestamp_types:
                    
                    ( hashes, old_datetime_value_range, old_user_has_edited ) = self._file_services_list_ctrl_data_dict[ row ]
                    
                    if edited_datetime_value_range.HasFixedValue():
                        
                        new_datetime_value_range = old_datetime_value_range.DuplicateWithNewQtDateTime( edited_datetime_value_range.GetFixedValue() )
                        
                    else:
                        
                        # don't think this will happen outside of crazy edge-cases
                        new_datetime_value_range = old_datetime_value_range.DuplicateWithNewQtDateTime( None )
                        
                    
                    new_datetime_value_range.SetStepMS( edited_datetime_value_range.GetStepMS() )
                    
                    self._file_services_list_ctrl_data_dict[ row ] = ( hashes, new_datetime_value_range, new_user_has_edited )
                    
                
                self._file_services_list_ctrl.UpdateDatas( selected_file_service_keys_and_timestamp_types )
                
                self._file_services_list_ctrl.Sort()
                
            
        
    
    def _GetValidTimestampDatas( self, only_changes = False ) -> list[ tuple[ collections.abc.Collection[ bytes ], ClientTime.TimestampData, int ] ]:
        
        if not only_changes and len( self._ordered_medias ) != 1:
            
            raise HydrusExceptions.VetoException( 'Sorry, cannot get original timestamps when more than one media objects created this dialog! This should not happen, so please let hydev know what created this situation.' )
            
        
        result_tuples = []
        
        #
        
        if self._file_modified_time.HasChanges() or not only_changes:
            
            datetime_value_range = self._file_modified_time.GetValue()
            
            if datetime_value_range.HasFixedValue():
                
                file_modified_timestamp_ms = datetime_value_range.GetFixedValue().toMSecsSinceEpoch()
                
                hashes = [ media.GetHash() for media in self._ordered_medias if media.GetTimesManager().GetFileModifiedTimestampMS() is not None ]
                
                result_tuples.append( ( hashes, ClientTime.TimestampData.STATICFileModifiedTime( file_modified_timestamp_ms ), datetime_value_range.GetStepMS() ) )
                
            
        
        #
        
        if self._archived_time.isEnabled() and ( self._archived_time.HasChanges() or not only_changes ):
            
            datetime_value_range = self._archived_time.GetValue()
            
            if datetime_value_range.HasFixedValue():
                
                archive_timestamp_ms = datetime_value_range.GetFixedValue().toMSecsSinceEpoch()
                
                hashes = [ media.GetHash() for media in self._ordered_medias if not media.HasInbox() and media.GetTimesManager().GetArchivedTimestampMS() is not None ]
                
                result_tuples.append( ( hashes, ClientTime.TimestampData.STATICArchivedTime( archive_timestamp_ms ), datetime_value_range.GetStepMS() ) )
                
            
        
        #
        
        if self._last_viewed_media_viewer_time.isEnabled() and ( self._last_viewed_media_viewer_time.HasChanges() or not only_changes ):
            
            datetime_value_range = self._last_viewed_media_viewer_time.GetValue()
            
            if datetime_value_range.HasFixedValue():
                
                last_viewed_media_viewer_timestamp_ms = datetime_value_range.GetFixedValue().toMSecsSinceEpoch()
                
                hashes = [ media.GetHash() for media in self._ordered_medias if media.GetTimesManager().GetLastViewedTimestampMS( CC.CANVAS_MEDIA_VIEWER ) is not None ]
                
                result_tuples.append( ( hashes, ClientTime.TimestampData.STATICLastViewedTime( CC.CANVAS_MEDIA_VIEWER, last_viewed_media_viewer_timestamp_ms ), datetime_value_range.GetStepMS() ) )
                
            
        
        if self._last_viewed_preview_viewer_time.isEnabled() and ( self._last_viewed_preview_viewer_time.HasChanges() or not only_changes ):
            
            datetime_value_range = self._last_viewed_preview_viewer_time.GetValue()
            
            if datetime_value_range.HasFixedValue():
                
                last_viewed_preview_viewer_timestamp_ms = datetime_value_range.GetFixedValue().toMSecsSinceEpoch()
                
                hashes = [ media.GetHash() for media in self._ordered_medias if media.GetTimesManager().GetLastViewedTimestampMS( CC.CANVAS_PREVIEW ) is not None ]
                
                result_tuples.append( ( hashes, ClientTime.TimestampData.STATICLastViewedTime( CC.CANVAS_PREVIEW, last_viewed_preview_viewer_timestamp_ms ), datetime_value_range.GetStepMS() ) )
                
            
        
        #
        
        current_domains = self._domain_modified_list_ctrl.GetData()
        
        for domain in current_domains:
            
            ( hashes, datetime_value_range, user_has_edited ) = self._domain_modified_list_ctrl_data_dict[ domain ]
            
            if only_changes and not user_has_edited:
                
                continue
                
            
            if not datetime_value_range.HasFixedValue():
                
                continue
                
            
            qt_datetime = datetime_value_range.GetFixedValue()
            
            timestamp_ms = qt_datetime.toMSecsSinceEpoch()
            
            result_tuples.append( ( hashes, ClientTime.TimestampData.STATICDomainModifiedTime( domain, timestamp_ms ), datetime_value_range.GetStepMS() ) )
            
        
        deletee_timestamp_domains = [ domain for domain in self._original_domain_modified_domains.difference( current_domains ) ]
        
        deletee_result_tuples = [ ( hashes, ClientTime.TimestampData( timestamp_type = HC.TIMESTAMP_TYPE_MODIFIED_DOMAIN, location = domain ), datetime_value_range.GetStepMS() ) for ( domain, ( hashes, datetime_value_range, user_has_edited ) ) in self._domain_modified_list_ctrl_data_dict.items() if domain in deletee_timestamp_domains ]
        
        result_tuples.extend( deletee_result_tuples )
        
        #
        
        file_service_list_tuples = self._file_services_list_ctrl.GetData()
        
        for row in file_service_list_tuples:
            
            ( file_service_key, timestamp_type ) = row
            
            ( hashes, datetime_value_range, user_has_edited ) = self._file_services_list_ctrl_data_dict[ row ]
            
            if only_changes and not user_has_edited:
                
                continue
                
            
            if not datetime_value_range.HasFixedValue():
                
                continue
                
            
            qt_datetime = datetime_value_range.GetFixedValue()
            
            timestamp_ms = qt_datetime.toMSecsSinceEpoch()
            
            timestamp_data = ClientTime.TimestampData( timestamp_type = timestamp_type, location = file_service_key, timestamp_ms = timestamp_ms )
            
            result_tuples.append( ( hashes, timestamp_data, datetime_value_range.GetStepMS() ) )
            
        
        return result_tuples
        
    
    def _Paste( self ):
        
        try:
            
            raw_text = CG.client_controller.GetClipboardText()
            
        except HydrusExceptions.DataMissing as e:
            
            ClientGUIDialogsMessage.ShowCritical( self, 'Problem pasting!', str(e) )
            
            return
            
        
        try:
            
            serialisable_tuple = json.loads( raw_text )
            
            list_of_timestamp_data = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_tuple )
            
            for item in list_of_timestamp_data:
                
                if not isinstance( item, ClientTime.TimestampData ):
                    
                    raise Exception( 'Not a timestamp data!' )
                    
                
            
        except Exception as e:
            
            ClientGUIDialogsQuick.PresentClipboardParseError( self, raw_text, 'A list of JSON-serialised Timestamp Data objects', e )
            
            return
            
        
        self._SetValueTimestampDatas( list_of_timestamp_data, from_user = True )
        
    
    def _SetValueTimestampDatas( self, list_of_timestamp_data: collections.abc.Collection[ ClientTime.TimestampData ], from_user = True ):
        
        for timestamp_data in list_of_timestamp_data:
            
            if timestamp_data.timestamp_type == HC.TIMESTAMP_TYPE_ARCHIVED:
                
                if timestamp_data.timestamp_ms is None:
                    
                    continue
                    
                
                self._archived_time.SetValue( self._archived_time.GetValue().DuplicateWithNewTimestampMS( timestamp_data.timestamp_ms ), from_user = from_user )
                
            elif timestamp_data.timestamp_type == HC.TIMESTAMP_TYPE_MODIFIED_FILE:
                
                if timestamp_data.timestamp_ms is None:
                    
                    continue
                    
                
                self._file_modified_time.SetValue( self._file_modified_time.GetValue().DuplicateWithNewTimestampMS( timestamp_data.timestamp_ms ), from_user = from_user )
                
            elif timestamp_data.timestamp_type == HC.TIMESTAMP_TYPE_LAST_VIEWED:
                
                if timestamp_data.location is None or timestamp_data.timestamp_ms is None:
                    
                    continue
                    
                
                if timestamp_data.location == CC.CANVAS_MEDIA_VIEWER:
                    
                    if not self._last_viewed_media_viewer_time.isHidden():
                        
                        self._last_viewed_media_viewer_time.SetValue( self._last_viewed_media_viewer_time.GetValue().DuplicateWithNewTimestampMS( timestamp_data.timestamp_ms ), from_user = from_user )
                        
                    
                elif timestamp_data.location == CC.CANVAS_PREVIEW:
                    
                    if not self._last_viewed_preview_viewer_time.isHidden():
                        
                        self._last_viewed_preview_viewer_time.SetValue( self._last_viewed_preview_viewer_time.GetValue().DuplicateWithNewTimestampMS( timestamp_data.timestamp_ms ), from_user = from_user )
                        
                    
                
            elif timestamp_data.timestamp_type == HC.TIMESTAMP_TYPE_MODIFIED_DOMAIN:
                
                if timestamp_data.location is None:
                    
                    continue
                    
                
                domain = timestamp_data.location
                
                current_domains = self._domain_modified_list_ctrl.GetData()
                
                if domain in current_domains:
                    
                    if timestamp_data.timestamp_ms is None:
                        
                        del self._domain_modified_list_ctrl_data_dict[ domain ]
                        
                        self._domain_modified_list_ctrl.DeleteDatas( ( domain, ) )
                        
                    else:
                        
                        all_hashes = [ m.GetHash() for m in self._ordered_medias ]
                        
                        all_hashes_datetime_value_range = ClientGUITime.DateTimeWidgetValueRange()
                        
                        all_hashes_datetime_value_range.AddValueTimestampMS( timestamp_data.timestamp_ms, num_to_add = len( all_hashes ) )
                        
                        if domain in self._domain_modified_list_ctrl_data_dict:
                            
                            ( hashes, existing_datetime_value_range, user_has_edited ) = self._domain_modified_list_ctrl_data_dict[ domain ]
                            
                            datetime_value_range = existing_datetime_value_range.DuplicateWithNewTimestampMS( timestamp_data.timestamp_ms )
                            
                            if len( hashes ) < len( self._ordered_medias ):
                                
                                result = ClientGUIDialogsQuick.GetYesNo( self, 'Not every file this dialog was launched on has a time for this domain. Do you want to apply what you just set to everything, or just the files that started with this domain?', yes_label = 'all files', no_label = 'only edit existing values' )
                                
                                if result == QW.QDialog.DialogCode.Accepted:
                                    
                                    hashes = all_hashes
                                    datetime_value_range = all_hashes_datetime_value_range
                                    
                                
                            
                            if datetime_value_range == existing_datetime_value_range:
                                
                                continue
                                
                            
                        else:
                            
                            hashes = all_hashes
                            datetime_value_range = all_hashes_datetime_value_range
                            
                        
                        user_has_edited = True
                        
                        self._domain_modified_list_ctrl_data_dict[ domain ] = ( hashes, datetime_value_range, user_has_edited )
                        
                        self._domain_modified_list_ctrl.UpdateDatas( ( domain, ) )
                        
                    
                
            elif timestamp_data.timestamp_type in ClientTime.FILE_SERVICE_TIMESTAMP_TYPES:
                
                if timestamp_data.location is None or timestamp_data.timestamp_ms is None:
                    
                    continue
                    
                
                current_file_service_list_tuples = self._file_services_list_ctrl.GetData()
                
                for row in current_file_service_list_tuples:
                    
                    ( file_service_key, timestamp_type ) = row
                    
                    if timestamp_data.location == file_service_key and timestamp_data.timestamp_type == timestamp_type:
                        
                        ( hashes, existing_datetime_value_range, user_has_edited ) = self._file_services_list_ctrl_data_dict[ row ]
                        
                        datetime_value_range = existing_datetime_value_range.DuplicateWithNewTimestampMS( timestamp_data.timestamp_ms )
                        
                        if datetime_value_range != existing_datetime_value_range:
                            
                            user_has_edited = True
                            
                            self._file_services_list_ctrl_data_dict[ row ] = ( hashes, datetime_value_range, user_has_edited )
                            
                            self._file_services_list_ctrl.UpdateDatas( ( row, ) )
                            
                        
                        break
                        
                    
                
            
        
    
    def _ShowFileModifiedWarning( self ):
        
        for ( hashes, timestamp_data, step_ms ) in self._GetValidTimestampDatas( only_changes = True ):
            
            if timestamp_data.timestamp_type == HC.TIMESTAMP_TYPE_MODIFIED_FILE and timestamp_data.timestamp_ms is not None:
                
                self._file_modified_time_warning_st.setVisible( True )
                
                if HydrusPaths.FileModifiedTimeIsOk( HydrusTime.SecondiseMSFloat( timestamp_data.timestamp_ms ) ):
                    
                    self._file_modified_time_warning_st.setText( 'This will also change the modified time of the file on disk!' )
                    
                else:
                    
                    self._file_modified_time_warning_st.setText( 'File modified time on disk will not be changed--the timestamp is too early.' )
                    
                
                return
                
            
        
        self._file_modified_time_warning_st.setVisible( False )
        
    
    def GetFileModifiedUpdateData( self ) -> tuple[ collections.abc.Collection[ bytes ], int, int ] | None:
        
        for ( hashes, timestamp_data, step_ms ) in self._GetValidTimestampDatas( only_changes = True ):
            
            if timestamp_data.timestamp_type == HC.TIMESTAMP_TYPE_MODIFIED_FILE and timestamp_data.timestamp_ms is not None:
                
                if HydrusPaths.FileModifiedTimeIsOk( HydrusTime.SecondiseMSFloat( timestamp_data.timestamp_ms ) ):
                    
                    return ( hashes, timestamp_data.timestamp_ms, step_ms )
                    
                
            
        
        return None
        
    
    def GetContentUpdatePackage( self ) -> ClientContentUpdates.ContentUpdatePackage:
        
        content_updates = []
        
        for ( hashes, timestamp_data, step_ms ) in self._GetValidTimestampDatas( only_changes = True ):
            
            if timestamp_data.timestamp_ms is None:
                
                content_updates.append( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_TIMESTAMP, HC.CONTENT_UPDATE_DELETE, ( hashes, timestamp_data ) ) )
                
            else:
                
                if step_ms == 0:
                    
                    content_updates.append( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_TIMESTAMP, HC.CONTENT_UPDATE_SET, ( hashes, timestamp_data ) ) )
                    
                else:
                    
                    # let's force sort here to be safe
                    hashes = set( hashes )
                    hashes = [ media.GetHash() for media in self._ordered_medias if media.GetHash() in hashes ]
                    
                    for ( i, hash ) in enumerate( hashes ):
                        
                        sub_timestamp_data = ClientTime.TimestampData( timestamp_type = timestamp_data.timestamp_type, location = timestamp_data.location, timestamp_ms = timestamp_data.timestamp_ms + ( i * step_ms ) )
                        
                        content_updates.append( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_TIMESTAMP, HC.CONTENT_UPDATE_SET, ( ( hash, ), sub_timestamp_data ) ) )
                        
                    
                
            
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, content_updates )
        
        return content_update_package
        
    
    def GetValue( self ):
        
        return self.GetContentUpdatePackage()
        
    
    def ProcessApplicationCommand( self, command: CAC.ApplicationCommand ):
        
        command_processed = True
        
        if command.IsSimpleCommand():
            
            action = command.GetSimpleAction()
            
            if action == CAC.SIMPLE_MANAGE_FILE_TIMESTAMPS:
                
                self._OKParent()
                
            else:
                
                command_processed = False
                
            
        else:
            
            command_processed = False
            
        
        return command_processed
        
    
    def UserIsOKToOK( self ):
        
        content_update_package = self.GetContentUpdatePackage()
        
        total_changes = 0
        
        for ( service_key, content_updates ) in content_update_package.IterateContentUpdates():
            
            for content_update in content_updates:
                
                total_changes += len( content_update.GetHashes() )
                
            
        
        if total_changes > 100:
            
            message = 'This dialog is about to make more than 100 changes! Are you sure this is all correct?'
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message )
            
            if result != QW.QDialog.DialogCode.Accepted:
                
                return False
                
            
        
        return True
        
    
