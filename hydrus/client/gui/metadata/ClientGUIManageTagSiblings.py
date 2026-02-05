import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusLists
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusTags
from hydrus.core import HydrusText

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUIAsync
from hydrus.client.gui import ClientGUIDialogsFiles
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListBoxes
from hydrus.client.gui.lists import ClientGUIListBook
from hydrus.client.gui.lists import ClientGUIListConstants as CGLC
from hydrus.client.gui.lists import ClientGUIListCtrl
from hydrus.client.gui.metadata import ClientGUITagActions
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.search import ClientGUIACDropdown
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.gui.widgets import ClientGUIMenuButton
from hydrus.client.metadata import ClientContentUpdates
from hydrus.client.metadata import ClientTags

class ManageTagSiblings( ClientGUIScrolledPanels.ManagePanel ):
    
    def __init__( self, parent, tags = None ):
        
        super().__init__( parent )
        
        if CG.client_controller.new_options.GetBoolean( 'use_listbook_for_tag_service_panels' ):
            
            self._tag_services = ClientGUIListBook.ListBook( self )
            
        else:
            
            self._tag_services = ClientGUICommon.BetterNotebook( self )
            
        
        #
        
        default_tag_service_key = CG.client_controller.new_options.GetKey( 'default_tag_service_tab' )
        
        services = list( CG.client_controller.services_manager.GetServices( ( HC.LOCAL_TAG, ) ) )
        
        services.extend( CG.client_controller.services_manager.GetServices( ( HC.TAG_REPOSITORY, ) ) )
        
        for service in services:
            
            name = service.GetName()
            service_key = service.GetServiceKey()
            
            page = self._Panel( self._tag_services, service_key, tags )
            
            self._tag_services.addTab( page, name )
            
            if service_key == default_tag_service_key:
                
                # Py 3.11/PyQt6 6.5.0/two tabs/total tab characters > ~12/select second tab during init = first tab disappears bug
                CG.client_controller.CallAfterQtSafe( self._tag_services, self._tag_services.setCurrentWidget, page )
                
            
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._tag_services, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
        self._tag_services.currentChanged.connect( self._SaveDefaultTagServiceKey )
        
    
    def _SaveDefaultTagServiceKey( self ):
        
        if CG.client_controller.new_options.GetBoolean( 'save_default_tag_service_tab_on_change' ):
            
            current_page = typing.cast( ManageTagSiblings._Panel, self._tag_services.currentWidget() )
            
            if current_page is not None:
                
                CG.client_controller.new_options.SetKey( 'default_tag_service_tab', current_page.GetServiceKey() )
                
            
        
    
    def _SetSearchFocus( self ):
        
        current_page = typing.cast( ManageTagSiblings._Panel, self._tag_services.currentWidget() )
        
        if current_page is not None:
            
            current_page.SetTagBoxFocus()
            
        
    
    def CommitChanges( self ):
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage()
        
        for page in self._tag_services.GetPages():
            
            ( service_key, content_updates ) = page.GetContentUpdates()
            
            content_update_package.AddContentUpdates( service_key, content_updates )
            
        
        if content_update_package.HasContent():
            
            CG.client_controller.Write( 'content_updates', content_update_package )
            
        
    
    def UserIsOKToOK( self ):
        
        current_page = typing.cast( ManageTagSiblings._Panel, self._tag_services.currentWidget() )
        
        if current_page.HasUncommittedPair():
            
            message = 'Are you sure you want to OK? You have an uncommitted pair.'
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message )
            
            if result != QW.QDialog.DialogCode.Accepted:
                
                return False
                
            
        
        return True
        
    
    def EventServiceChanged( self, event ):
        
        current_page = typing.cast( ManageTagSiblings._Panel, self._tag_services.currentWidget() )
        
        if current_page is not None:
            
            CG.client_controller.CallAfterQtSafe( current_page, current_page.SetTagBoxFocus )
            
        
    
    class _Panel( QW.QWidget ):
        
        def __init__( self, parent, service_key, tags = None ):
            
            super().__init__( parent )
            
            self._current_pertinent_tags = set()
            
            self._service_key = service_key
            
            self._service = CG.client_controller.services_manager.GetService( self._service_key )
            
            self._i_am_local_tag_service = self._service.GetServiceType() == HC.LOCAL_TAG
            
            self._sibling_action_context = ClientGUITagActions.SiblingActionContext( self._service_key )
            
            self._current_new = None
            
            self._show_all = QW.QCheckBox( self )
            self._show_pending_and_petitioned = QW.QCheckBox( self )
            
            # leave up here since other things have updates based on them
            self._old_siblings = ClientGUIListBoxes.ListBoxTagsStringsAddRemove( self, self._service_key, tag_display_type = ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, height_num_chars = 4 )
            self._new_sibling = ClientGUICommon.BetterStaticText( self )
            self._new_sibling.setAlignment( QC.Qt.AlignmentFlag.AlignCenter )
            
            self._listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
            
            model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_TAG_SIBLINGS.ID, self._ConvertPairToDisplayTuple, self._ConvertPairToSortTuple )
            
            self._tag_siblings = ClientGUIListCtrl.BetterListCtrlTreeView( self._listctrl_panel, 14, model, delete_key_callback = self._DeleteSelectedRows, activation_callback = self._DeleteSelectedRows )
            
            self._listctrl_panel.SetListCtrl( self._tag_siblings )
            
            self._listctrl_panel.AddButton( 'add', self._AddButton, enabled_check_func = self._CanAddFromCurrentInput )
            self._listctrl_panel.AddButton( 'delete', self._DeleteSelectedRows, enabled_only_on_selection = True )
            
            self._tag_siblings.Sort()
            
            menu_template_items = []
            
            menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'from clipboard (add new pairs and ignore pre-existing)', 'Load siblings from text in your clipboard.', HydrusData.Call( self._ImportFromClipboard, True ) ) )
            menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'from .txt file (add new pairs and ignore pre-existing)', 'Load siblings from a .txt file.', HydrusData.Call( self._ImportFromTXT, True ) ) )
            
            self._listctrl_panel.AddMenuButton( 'import', menu_template_items )
            
            menu_template_items = []
            
            menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'to clipboard', 'Save selected siblings to your clipboard.', self._ExportToClipboard ) )
            menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'to .txt file', 'Save selected siblings to a .txt file.', self._ExportToTXT ) )
            
            self._listctrl_panel.AddMenuButton( 'export', menu_template_items, enabled_only_on_selection = True )
            
            ( gumpf, preview_height ) = ClientGUIFunctions.ConvertTextToPixels( self._old_siblings, ( 12, 4 ) )
            
            self._old_siblings.setMinimumHeight( preview_height )
            
            default_location_context = CG.client_controller.new_options.GetDefaultLocalLocationContext()
            
            self._old_input = ClientGUIACDropdown.AutoCompleteDropdownTagsWrite( self, self.EnterOlds, default_location_context, service_key, show_paste_button = True )
            self._new_input = ClientGUIACDropdown.AutoCompleteDropdownTagsWrite( self, self.SetNew, default_location_context, service_key, show_paste_button = True )
            
            self._old_siblings.tagsChanged.connect( self._old_input.SetContextTags )
            
            self._old_input.externalCopyKeyPressEvent.connect( self._old_siblings.keyPressEvent )
            
            #
            
            self._status_st = ClientGUICommon.BetterStaticText( self,'Tags on the left will appear as those on the right.' )
            self._sync_status_st = ClientGUICommon.BetterStaticText( self, '' )
            self._sync_status_st.setWordWrap( True )
            self._count_st = ClientGUICommon.BetterStaticText( self, '' )
            
            self._wipe_workspace = ClientGUICommon.BetterButton( self, 'wipe workspace', self._WipeWorkspace )
            self._wipe_workspace.setEnabled( False )
            
            old_sibling_box = QP.VBoxLayout()
            
            QP.AddToLayout( old_sibling_box, ClientGUICommon.BetterStaticText( self, label = 'set tags to be replaced' ), CC.FLAGS_CENTER )
            QP.AddToLayout( old_sibling_box, self._old_siblings, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            new_sibling_box = QP.VBoxLayout()
            
            QP.AddToLayout( new_sibling_box, ClientGUICommon.BetterStaticText( self, label = 'set new ideal tag' ), CC.FLAGS_CENTER )
            QP.AddToLayout( new_sibling_box, self._new_sibling, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            text_box = QP.HBoxLayout()
            
            QP.AddToLayout( text_box, old_sibling_box, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            QP.AddToLayout( text_box, new_sibling_box, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            
            input_box = QP.HBoxLayout()
            
            QP.AddToLayout( input_box, self._old_input, CC.FLAGS_EXPAND_BOTH_WAYS )
            QP.AddToLayout( input_box, self._new_input, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            workspace_hbox = QP.HBoxLayout()
            
            QP.AddToLayout( workspace_hbox, self._wipe_workspace, CC.FLAGS_SIZER_CENTER )
            QP.AddToLayout( workspace_hbox, self._count_st, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, self._status_st, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, self._sync_status_st, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, ClientGUICommon.WrapInText( self._show_all, self, 'show all pairs' ), CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, ClientGUICommon.WrapInText( self._show_pending_and_petitioned, self, 'show pending and petitioned groups' ), CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, workspace_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, self._listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
            QP.AddToLayout( vbox, text_box, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            QP.AddToLayout( vbox, input_box, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            self.setLayout( vbox )
            
            #
            
            self._listctrl_async_updater = self._InitialiseListCtrlAsyncUpdater()
            
            self._show_all.clicked.connect( self._listctrl_async_updater.update )
            self._show_pending_and_petitioned.clicked.connect( self._listctrl_async_updater.update )
            
            self._old_siblings.listBoxChanged.connect( self._listctrl_async_updater.update )
            
            self._sibling_action_context.RegisterQtUpdateCall( self, self._listctrl_async_updater.update )
            
            self._old_input.tagsPasted.connect( self.EnterOldsOnlyAdd )
            self._new_input.tagsPasted.connect( self.SetNew )
            
            self._STARTInitialisation( tags, self._service_key )
            
        
        def _AddButton( self ):
            
            if self._current_new is not None and len( self._old_siblings.GetTags() ) > 0:
                
                olds = self._old_siblings.GetTags()
                
                pairs = [ ( old, self._current_new ) for old in olds ]
                
                self._sibling_action_context.EnterPairs( self, pairs, only_add = True )
                
                self._old_siblings.SetTags( set() )
                self.SetNew( set() )
                
            
        
        def _CanAddFromCurrentInput( self ):
            
            if self._current_new is None or len( self._old_siblings.GetTags() ) == 0:
                
                return False
                
            
            return True
            
        
        def _ConvertPairToDisplayTuple( self, pair ):
            
            ( old, new ) = pair
            
            ( in_pending, in_petitioned, reason ) = self._sibling_action_context.GetPairListCtrlInfo( pair )
            
            note = reason
            
            if in_pending or in_petitioned:
                
                if in_pending:
                    
                    status = HC.CONTENT_STATUS_PENDING
                    
                else:
                    
                    status = HC.CONTENT_STATUS_PETITIONED
                    
                
            else:
                
                status = HC.CONTENT_STATUS_CURRENT
                
                note = ''
                
            
            pretty_status = HydrusData.status_to_prefix.get( status, '(?) ' )
            
            existing_olds = self._old_siblings.GetTags()
            
            if old in existing_olds:
                
                if self._current_new is None:
                    
                    if status == HC.CONTENT_STATUS_PENDING:
                        
                        note = 'POSSIBLE CONFLICT: May be auto-rescinded on add.'
                        
                    elif status == HC.CONTENT_STATUS_CURRENT:
                        
                        note = 'POSSIBLE CONFLICT: May be auto-petitioned/deleted on add.'
                        
                    
                else:
                    
                    if self._current_new == new:
                        
                        note = 'Already exists.'
                        
                    else:
                        
                        if status == HC.CONTENT_STATUS_PENDING:
                            
                            note = 'CONFLICT: Will be auto-rescinded on add.'
                            
                        elif status == HC.CONTENT_STATUS_CURRENT:
                            
                            note = 'CONFLICT: Will be auto-petitioned/deleted on add.'
                            
                        
                    
                
            
            return ( pretty_status, old, new, note )
            
        
        def _ConvertPairToSortTuple( self, pair ):
            
            ( old, new ) = pair
            
            ( in_pending, in_petitioned, reason ) = self._sibling_action_context.GetPairListCtrlInfo( pair )
            
            note = reason
            
            if in_pending or in_petitioned:
                
                if in_pending:
                    
                    status = HC.CONTENT_STATUS_PENDING
                    
                else:
                    
                    status = HC.CONTENT_STATUS_PETITIONED
                    
                
            else:
                
                status = HC.CONTENT_STATUS_CURRENT
                
                note = ''
                
            
            existing_olds = self._old_siblings.GetTags()
            
            if old in existing_olds:
                
                if status == HC.CONTENT_STATUS_PENDING:
                    
                    note = 'CONFLICT: Will be rescinded on add.'
                    
                elif status == HC.CONTENT_STATUS_CURRENT:
                    
                    note = 'CONFLICT: Will be petitioned/deleted on add.'
                    
                
            
            return ( status, old, new, note )
            
        
        def _DeleteSelectedRows( self ):
            
            pairs = self._tag_siblings.GetData( only_selected = True )
            
            if len( pairs ) > 0:
                
                self._sibling_action_context.EnterPairs( self, pairs )
                
            
        
        def _DeserialiseImportString( self, import_string ):
            
            tags = HydrusText.DeserialiseNewlinedTexts( import_string )
            
            if len( tags ) % 2 == 1:
                
                ClientGUIDialogsMessage.ShowInformation( self, 'Uneven number of tags in clipboard!' )
                
            
            pairs = []
            
            for i in range( len( tags ) // 2 ):
                
                try:
                    
                    pair = (
                        HydrusTags.CleanTag( tags[ 2 * i ] ),
                        HydrusTags.CleanTag( tags[ ( 2 * i ) + 1 ] )
                    )
                    
                except Exception as e:
                    
                    continue
                    
                
                pairs.append( pair )
                
            
            pairs = HydrusLists.DedupeList( pairs )
            
            return pairs
            
        
        def _ExportToClipboard( self ):
            
            export_string = self._GetExportString()
            
            CG.client_controller.pub( 'clipboard', 'text', export_string )
            
        
        def _ExportToTXT( self ):
            
            export_string = self._GetExportString()
            
            with ClientGUIDialogsFiles.FileDialog( self, 'Set the export path.', default_filename = 'siblings.txt', acceptMode = QW.QFileDialog.AcceptMode.AcceptSave, fileMode = QW.QFileDialog.FileMode.AnyFile ) as dlg:
                
                if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                    
                    path = dlg.GetPath()
                    
                    with open( path, 'w', encoding = 'utf-8' ) as f:
                        
                        f.write( export_string )
                        
                    
                
            
        
        def _GetExportString( self ):
            
            tags = []
            
            for ( a, b ) in self._tag_siblings.GetData( only_selected = True ):
                
                tags.append( a )
                tags.append( b )
                
            
            export_string = '\n'.join( tags )
            
            return export_string
            
        
        def _ImportFromClipboard( self, only_add = False ):
            
            try:
                
                raw_text = CG.client_controller.GetClipboardText()
                
            except HydrusExceptions.DataMissing as e:
                
                HydrusData.PrintException( e )
                
                ClientGUIDialogsMessage.ShowCritical( self, 'Problem importing!', str(e) )
                
                return
                
            
            try:
                
                pairs = self._DeserialiseImportString( raw_text )
                
                for ( a, b ) in pairs:
                    
                    self._current_pertinent_tags.add( a )
                    self._current_pertinent_tags.add( b )
                    
                
                self._sibling_action_context.EnterPairs( self, pairs, only_add = only_add )
                
            except Exception as e:
                
                ClientGUIDialogsQuick.PresentClipboardParseError( self, raw_text, 'Lines of lesser-ideal sibling line-pairs', e )
                
            
        
        def _ImportFromTXT( self, only_add = False ):
            
            with ClientGUIDialogsFiles.FileDialog( self, 'Select the file to import.', acceptMode = QW.QFileDialog.AcceptMode.AcceptOpen ) as dlg:
                
                if dlg.exec() != QW.QDialog.DialogCode.Accepted:
                    
                    return
                    
                else:
                    
                    path = dlg.GetPath()
                    
                
            
            with open( path, 'r', encoding = 'utf-8' ) as f:
                
                import_string = f.read()
                
            
            pairs = self._DeserialiseImportString( import_string )
            
            for ( a, b ) in pairs:
                
                self._current_pertinent_tags.add( a )
                self._current_pertinent_tags.add( b )
                
            
            self._sibling_action_context.EnterPairs( self, pairs, only_add = only_add )
            
        
        def _InitialiseListCtrlAsyncUpdater( self ) -> ClientGUIAsync.AsyncQtUpdater:
            
            def loading_callable():
                
                self._count_st.setText( 'loading' + HC.UNICODE_ELLIPSIS )
                
            
            def pre_work_callable():
                
                olds = self._old_siblings.GetTags()
                
                self._current_pertinent_tags.update( olds )
                
                if self._current_new is not None:
                    
                    self._current_pertinent_tags.add( self._current_new )
                    
                
                show_all = self._show_all.isChecked()
                
                self._show_pending_and_petitioned.setEnabled( not show_all )
                
                show_pending_and_petitioned = self._show_pending_and_petitioned.isEnabled() and self._show_pending_and_petitioned.isChecked()
                
                return ( set( self._current_pertinent_tags ), show_all, show_pending_and_petitioned, self._sibling_action_context )
                
            
            def work_callable( args ):
                
                ( pertinent_tags, show_all, show_pending_and_petitioned, sibling_action_context ) = args
                
                pursue_whole_chain = True # parent hack
                
                pertinent_pairs = sibling_action_context.GetPertinentPairsForTags( pertinent_tags, show_all, show_pending_and_petitioned, pursue_whole_chain )
                
                return pertinent_pairs
                
            
            def publish_callable( result ):
                
                pairs = result
                
                num_active_pertinent_tags = len( self._old_siblings.GetTags() )
                
                if self._current_new is not None:
                    
                    num_active_pertinent_tags += 1
                    
                
                self._wipe_workspace.setEnabled( len( self._current_pertinent_tags ) > num_active_pertinent_tags )
                
                message = 'This dialog will remember the tags you enter and leave all the related pairs in view. Once you are done editing a group, hit this and it will clear the old pairs away.'
                
                if len( self._current_pertinent_tags ) > 0:
                    
                    message += f' Current workspace:{HydrusText.ConvertManyStringsToNiceInsertableHumanSummary( self._current_pertinent_tags, no_trailing_whitespace = True )}'
                    
                
                self._wipe_workspace.setToolTip( ClientGUIFunctions.WrapToolTip( message ) )
                
                self._count_st.setText( f'{HydrusNumbers.ToHumanInt(len(pairs))} pairs.' )
                
                self._tag_siblings.SetData( pairs )
                
                self._listctrl_panel.UpdateButtons()
                
            
            return ClientGUIAsync.AsyncQtUpdater( 'tag siblings pertinent pairs', self, loading_callable, work_callable, publish_callable, pre_work_callable = pre_work_callable )
            
        
        def _WipeWorkspace( self ):
            
            self._current_pertinent_tags = set()
            
            self._listctrl_async_updater.update()
            
        
        def EnterOlds( self, olds ):
            
            if self._current_new in olds:
                
                self.SetNew( set() )
                
            
            self._old_siblings.EnterTags( olds )
            
            self._listctrl_async_updater.update()
            
        
        def EnterOldsOnlyAdd( self, olds ):
            
            current_olds = self._old_siblings.GetTags()
            
            olds = { old for old in olds if old not in current_olds }
            
            if len( olds ) > 0:
                
                self.EnterOlds( olds )
                
            
        
        def GetContentUpdates( self ):
            
            content_updates = self._sibling_action_context.GetContentUpdates()
            
            return ( self._service_key, content_updates )
            
        
        def GetServiceKey( self ):
            
            return self._service_key
            
        
        def HasUncommittedPair( self ):
            
            return len( self._old_siblings.GetTags() ) > 0 and self._current_new is not None
            
        
        def SetNew( self, new_tags ):
            
            if len( new_tags ) == 0:
                
                self._new_sibling.clear()
                
                self._current_new = None
                
            else:
                
                new = list( new_tags )[0]
                
                self._old_siblings.RemoveTags( { new } )
                
                self._new_sibling.setText( new )
                
                self._current_new = new
                
            
            self._listctrl_async_updater.update()
            
        
        def SetTagBoxFocus( self ):
            
            if len( self._old_siblings.GetTags() ) == 0:
                
                self._old_input.setFocus( QC.Qt.FocusReason.OtherFocusReason )
                
            else:
                
                self._new_input.setFocus( QC.Qt.FocusReason.OtherFocusReason )
                
            
        
        def _STARTInitialisation( self, tags, service_key ):
            
            def work_callable():
                
                ( master_service_keys_to_sibling_applicable_service_keys, master_service_keys_to_parent_applicable_service_keys ) = CG.client_controller.Read( 'tag_display_application' )
                
                service_keys_we_care_about = { s_k for ( s_k, s_ks ) in master_service_keys_to_sibling_applicable_service_keys.items() if service_key in s_ks }
                
                service_keys_to_work_to_do = {}
                
                for s_k in service_keys_we_care_about:
                    
                    status = CG.client_controller.Read( 'tag_display_maintenance_status', s_k )
                    
                    work_to_do = status[ 'num_siblings_to_sync' ] > 0
                    
                    service_keys_to_work_to_do[ s_k ] = work_to_do
                    
                
                return service_keys_to_work_to_do
                
            
            def publish_callable( result ):
                
                service_keys_to_work_to_do = result
                
                looking_good = True
                
                if len( service_keys_to_work_to_do ) == 0:
                    
                    looking_good = False
                    
                    status_text = 'No services currently apply these siblings. Changes here will have no effect unless sibling application is changed later.'
                    
                else:
                    
                    synced_names = sorted( ( CG.client_controller.services_manager.GetName( s_k ) for ( s_k, work_to_do ) in service_keys_to_work_to_do.items() if not work_to_do ) )
                    unsynced_names = sorted( ( CG.client_controller.services_manager.GetName( s_k ) for ( s_k, work_to_do ) in service_keys_to_work_to_do.items() if work_to_do ) )
                    
                    synced_string = ', '.join( ( '"{}"'.format( name ) for name in synced_names ) )
                    unsynced_string = ', '.join( ( '"{}"'.format( name ) for name in unsynced_names ) )
                    
                    if len( unsynced_names ) == 0:
                        
                        service_part = '{} apply these siblings and are fully synced.'.format( synced_string )
                        
                    else:
                        
                        looking_good = False
                        
                        if len( synced_names ) > 0:
                            
                            service_part = '{} apply these siblings and are fully synced, but {} still have work to do.'.format( synced_string, unsynced_string )
                            
                        else:
                            
                            service_part = '{} apply these siblings but still have sync work to do.'.format( unsynced_string )
                            
                        
                    
                    if CG.client_controller.new_options.GetBoolean( 'tag_display_maintenance_during_active' ):
                        
                        maintenance_part = 'Siblings are set to sync all the time in the background.'
                        
                        if looking_good:
                            
                            changes_part = 'Changes from this dialog should be reflected soon after closing the dialog.'
                            
                        else:
                            
                            changes_part = 'It may take some time for changes here to apply everywhere, though.'
                            
                        
                    else:
                        
                        looking_good = False
                        
                        if CG.client_controller.new_options.GetBoolean( 'tag_display_maintenance_during_idle' ):
                            
                            maintenance_part = 'Siblings are set to sync only when you are not using the client.'
                            changes_part = 'It may take some time for changes here to apply.'
                            
                        else:
                            
                            maintenance_part = 'Siblings are not set to sync.'
                            changes_part = 'Changes here will not apply unless sync is manually forced to run.'
                            
                        
                    
                    s = ' | '
                    status_text = s.join( ( service_part, maintenance_part, changes_part ) )
                    
                
                if not self._i_am_local_tag_service:
                    
                    account = self._service.GetAccount()
                    
                    if account.IsUnknown():
                        
                        looking_good = False
                        
                        s = 'The account for this service is currently unsynced! It is uncertain if you have permission to upload siblings! Please try to refresh the account in _review services_.'
                        
                        status_text = '{}\n\n{}'.format( s, status_text )
                        
                    elif not account.HasPermission( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.PERMISSION_ACTION_PETITION ):
                        
                        looking_good = False
                        
                        s = 'The account for this service does not seem to have permission to upload siblings! You can edit them here for now, but the pending menu will not try to upload any changes you make.'
                        
                        status_text = '{}\n\n{}'.format( s, status_text )
                        
                    
                
                self._sync_status_st.setText( status_text )
                
                if looking_good:
                    
                    self._sync_status_st.setObjectName( 'HydrusValid' )
                    
                else:
                    
                    self._sync_status_st.setObjectName( 'HydrusWarning' )
                    
                
                self._sync_status_st.style().polish( self._sync_status_st )
                
                if tags is None:
                    
                    self._listctrl_async_updater.update()
                    
                else:
                    
                    self.EnterOlds( tags )
                    
                
                if self.isVisible():
                    
                    self.SetTagBoxFocus()
                    
                
            
            self._sync_status_st.setText( 'initialising sync data' + HC.UNICODE_ELLIPSIS )
            
            job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
            
            job.start()
            
        
    
