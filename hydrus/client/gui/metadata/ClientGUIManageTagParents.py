import itertools
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

class ManageTagParents( ClientGUIScrolledPanels.ManagePanel ):
    
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
            
            current_page = typing.cast( ManageTagParents._Panel, self._tag_services.currentWidget() )
            
            CG.client_controller.new_options.SetKey( 'default_tag_service_tab', current_page.GetServiceKey() )
            
        
    
    def _SetSearchFocus( self ):
        
        current_page = typing.cast( ManageTagParents._Panel, self._tag_services.currentWidget() )
        
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
        
        current_page = typing.cast( ManageTagParents._Panel, self._tag_services.currentWidget() )
        
        if current_page.HasUncommittedPair():
            
            message = 'Are you sure you want to OK? You have an uncommitted pair.'
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message )
            
            if result != QW.QDialog.DialogCode.Accepted:
                
                return False
                
            
        
        return True
        
    
    class _Panel( QW.QWidget ):
        
        def __init__( self, parent, service_key, tags = None ):
            
            super().__init__( parent )
            
            self._current_pertinent_tags = set()
            
            self._service_key = service_key
            
            self._service = CG.client_controller.services_manager.GetService( self._service_key )
            
            self._i_am_local_tag_service = self._service.GetServiceType() == HC.LOCAL_TAG
            
            self._parent_action_context = ClientGUITagActions.ParentActionContext( self._service_key )
            
            self._current_new = None
            
            self._show_all = QW.QCheckBox( self )
            self._show_pending_and_petitioned = QW.QCheckBox( self )
            self._pursue_whole_chain = QW.QCheckBox( self )
            
            tt = 'When you enter tags in the bottom boxes, the upper list is filtered to pertinent related relationships.'
            tt += '\n' * 2
            tt += 'With this off, it will show (grand)children and (grand)parents only. With it on, it walks up and down the full chain, including cousins. This can be overwhelming!'
            
            self._pursue_whole_chain.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            # leave up here since other things have updates based on them
            self._children = ClientGUIListBoxes.ListBoxTagsStringsAddRemove( self, self._service_key, tag_display_type = ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, height_num_chars = 4 )
            self._parents = ClientGUIListBoxes.ListBoxTagsStringsAddRemove( self, self._service_key, tag_display_type = ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, height_num_chars = 4 )
            
            self._listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
            
            model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_TAG_PARENTS.ID, self._ConvertPairToDisplayTuple, self._ConvertPairToSortTuple )
            
            self._tag_parents = ClientGUIListCtrl.BetterListCtrlTreeView( self._listctrl_panel, 6, model, delete_key_callback = self._DeleteSelectedRows, activation_callback = self._DeleteSelectedRows )
            
            self._listctrl_panel.SetListCtrl( self._tag_parents )
            
            self._listctrl_panel.AddButton( 'add', self._AddButton, enabled_check_func = self._CanAddFromCurrentInput )
            self._listctrl_panel.AddButton( 'delete', self._DeleteSelectedRows, enabled_only_on_selection = True )
            
            self._tag_parents.Sort()
            
            menu_template_items = []
            
            menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'from clipboard', 'Load siblings from text in your clipboard.', HydrusData.Call( self._ImportFromClipboard, True ) ) )
            menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'from .txt file', 'Load siblings from a .txt file.', HydrusData.Call( self._ImportFromTXT, True ) ) )
            
            self._listctrl_panel.AddMenuButton( 'import', menu_template_items )
            
            menu_template_items = []
            
            menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'to clipboard', 'Save selected siblings to your clipboard.', self._ExportToClipboard ) )
            menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'to .txt file', 'Save selected siblings to a .txt file.', self._ExportToTXT ) )
            
            self._listctrl_panel.AddMenuButton( 'export', menu_template_items, enabled_only_on_selection = True )
            
            ( gumpf, preview_height ) = ClientGUIFunctions.ConvertTextToPixels( self._children, ( 12, 6 ) )
            
            self._children.setMinimumHeight( preview_height )
            self._parents.setMinimumHeight( preview_height )
            
            default_location_context = CG.client_controller.new_options.GetDefaultLocalLocationContext()
            
            self._children_input = ClientGUIACDropdown.AutoCompleteDropdownTagsWrite( self, self.EnterChildren, default_location_context, service_key, show_paste_button = True )
            
            self._parents_input = ClientGUIACDropdown.AutoCompleteDropdownTagsWrite( self, self.EnterParents, default_location_context, service_key, show_paste_button = True )
            
            self._children.tagsChanged.connect( self._children_input.SetContextTags )
            self._parents.tagsChanged.connect( self._parents_input.SetContextTags )
            
            self._children_input.externalCopyKeyPressEvent.connect( self._children.keyPressEvent )
            self._parents_input.externalCopyKeyPressEvent.connect( self._parents.keyPressEvent )
            
            #
            
            self._status_st = ClientGUICommon.BetterStaticText( self,'Files with any tag on the left will also be given the tags on the right.' )
            self._sync_status_st = ClientGUICommon.BetterStaticText( self, '' )
            self._sync_status_st.setWordWrap( True )
            self._count_st = ClientGUICommon.BetterStaticText( self, '' )
            
            self._wipe_workspace = ClientGUICommon.BetterButton( self, 'wipe workspace', self._WipeWorkspace )
            self._wipe_workspace.setEnabled( False )
            
            children_vbox = QP.VBoxLayout()
            
            QP.AddToLayout( children_vbox, ClientGUICommon.BetterStaticText( self, label = 'set children' ), CC.FLAGS_CENTER )
            QP.AddToLayout( children_vbox, self._children, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            parents_vbox = QP.VBoxLayout()
            
            QP.AddToLayout( parents_vbox, ClientGUICommon.BetterStaticText( self, label = 'set parents' ), CC.FLAGS_CENTER )
            QP.AddToLayout( parents_vbox, self._parents, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            tags_box = QP.HBoxLayout()
            
            QP.AddToLayout( tags_box, children_vbox, CC.FLAGS_EXPAND_BOTH_WAYS )
            QP.AddToLayout( tags_box, parents_vbox, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            input_box = QP.HBoxLayout()
            
            QP.AddToLayout( input_box, self._children_input, CC.FLAGS_EXPAND_BOTH_WAYS )
            QP.AddToLayout( input_box, self._parents_input, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            workspace_hbox = QP.HBoxLayout()
            
            QP.AddToLayout( workspace_hbox, self._wipe_workspace, CC.FLAGS_SIZER_CENTER )
            QP.AddToLayout( workspace_hbox, self._count_st, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, self._status_st, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, self._sync_status_st, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, ClientGUICommon.WrapInText( self._show_all, self, 'show all pairs' ), CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, ClientGUICommon.WrapInText( self._show_pending_and_petitioned, self, 'show pending and petitioned groups' ), CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, ClientGUICommon.WrapInText( self._pursue_whole_chain, self, 'show whole chains' ), CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, workspace_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, self._listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
            QP.AddToLayout( vbox, tags_box, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            QP.AddToLayout( vbox, input_box, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            self.setLayout( vbox )
            
            #
            
            self._listctrl_async_updater = self._InitialiseListCtrlAsyncUpdater()
            
            self._children.listBoxChanged.connect( self._listctrl_async_updater.update )
            self._parents.listBoxChanged.connect( self._listctrl_async_updater.update )
            self._show_all.clicked.connect( self._listctrl_async_updater.update )
            self._show_pending_and_petitioned.clicked.connect( self._listctrl_async_updater.update )
            self._pursue_whole_chain.clicked.connect( self._listctrl_async_updater.update )
            
            self._children_input.tagsPasted.connect( self.EnterChildrenOnlyAdd )
            self._parents_input.tagsPasted.connect( self.EnterParentsOnlyAdd )
            
            self._parent_action_context.RegisterQtUpdateCall( self, self._listctrl_async_updater.update )
            
            self._STARTInitialisation( tags, self._service_key )
            
        
        def _AddButton( self ):
            
            children = self._children.GetTags()
            parents = self._parents.GetTags()
            
            if len( children ) > 0 and len( parents ) > 0:
                
                pairs = list( itertools.product( children, parents ) )
                
                self._parent_action_context.EnterPairs( self, pairs, only_add = True )
                
                self._children.SetTags( [] )
                self._parents.SetTags( [] )
                
            
        
        def _CanAddFromCurrentInput( self ):
            
            if len( self._children.GetTags() ) == 0 or len( self._parents.GetTags() ) == 0:
                
                return False
                
            
            return True
            
        
        def _ConvertPairToDisplayTuple( self, pair ):
            
            ( old, new ) = pair
            
            ( in_pending, in_petitioned, reason ) = self._parent_action_context.GetPairListCtrlInfo( pair )
            
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
            
            return ( pretty_status, old, new, note )
            
        
        def _ConvertPairToSortTuple( self, pair ):
            
            ( old, new ) = pair
            
            ( in_pending, in_petitioned, reason ) = self._parent_action_context.GetPairListCtrlInfo( pair )
            
            note = reason
            
            if in_pending or in_petitioned:
                
                if in_pending:
                    
                    status = HC.CONTENT_STATUS_PENDING
                    
                else:
                    
                    status = HC.CONTENT_STATUS_PETITIONED
                    
                
            else:
                
                status = HC.CONTENT_STATUS_CURRENT
                
                note = ''
                
            
            return ( status, old, new, note )
            
        
        def _DeleteSelectedRows( self ):
            
            pairs = self._tag_parents.GetData( only_selected = True )
            
            if len( pairs ) > 0:
                
                self._parent_action_context.EnterPairs( self, pairs )
                
            
        
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
            
            with ClientGUIDialogsFiles.FileDialog( self, 'Set the export path.', default_filename = 'parents.txt', acceptMode = QW.QFileDialog.AcceptMode.AcceptSave, fileMode = QW.QFileDialog.FileMode.AnyFile ) as dlg:
                
                if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                    
                    path = dlg.GetPath()
                    
                    with open( path, 'w', encoding = 'utf-8' ) as f:
                        
                        f.write( export_string )
                        
                    
                
            
        
        def _GetExportString( self ):
            
            tags = []
            
            for ( a, b ) in self._tag_parents.GetData( only_selected = True ):
                
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
                    
                
                self._parent_action_context.EnterPairs( self, pairs, only_add = only_add )
                
            except Exception as e:
                
                ClientGUIDialogsQuick.PresentClipboardParseError( self, raw_text, 'Lines of child-parent line-pairs', e )
                
            
        
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
                
            
            self._parent_action_context.EnterPairs( self, pairs, only_add = only_add )
            
        
        def _InitialiseListCtrlAsyncUpdater( self ) -> ClientGUIAsync.AsyncQtUpdater:
            
            def loading_callable():
                
                self._count_st.setText( 'loading' + HC.UNICODE_ELLIPSIS )
                
            
            def pre_work_callable():
                
                children = self._children.GetTags()
                parents = self._parents.GetTags()
                
                self._current_pertinent_tags.update( children )
                self._current_pertinent_tags.update( parents )
                
                show_all = self._show_all.isChecked()
                
                self._show_pending_and_petitioned.setEnabled( not show_all )
                self._pursue_whole_chain.setEnabled( not show_all )
                
                show_pending_and_petitioned = self._show_pending_and_petitioned.isEnabled() and self._show_pending_and_petitioned.isChecked()
                pursue_whole_chain = self._pursue_whole_chain.isEnabled() and self._pursue_whole_chain.isChecked()
                
                return ( set( self._current_pertinent_tags ), show_all, show_pending_and_petitioned, pursue_whole_chain, self._parent_action_context )
                
            
            def work_callable( args ):
                
                ( pertinent_tags, show_all, show_pending_and_petitioned, pursue_whole_chain, parent_action_context ) = args
                
                pertinent_pairs = parent_action_context.GetPertinentPairsForTags( pertinent_tags, show_all, show_pending_and_petitioned, pursue_whole_chain )
                
                return pertinent_pairs
                
            
            def publish_callable( result ):
                
                pairs = result
                
                num_active_pertinent_tags = len( self._children.GetTags() ) + len( self._parents.GetTags() )
                
                self._wipe_workspace.setEnabled( len( self._current_pertinent_tags ) > num_active_pertinent_tags )
                
                message = 'This dialog will remember the tags you enter and leave all the related pairs in view. Once you are done editing a group, hit this and it will clear the old pairs away.'
                
                if len( self._current_pertinent_tags ) > 0:
                    
                    message += f' Current workspace:{HydrusText.ConvertManyStringsToNiceInsertableHumanSummary( self._current_pertinent_tags, no_trailing_whitespace = True )}'
                    
                
                self._wipe_workspace.setToolTip( ClientGUIFunctions.WrapToolTip( message ) )
                
                self._count_st.setText( f'{HydrusNumbers.ToHumanInt(len(pairs))} pairs.' )
                
                self._tag_parents.SetData( pairs )
                
                self._listctrl_panel.UpdateButtons()
                
            
            return ClientGUIAsync.AsyncQtUpdater( 'tag parents pertinent pairs', self, loading_callable, work_callable, publish_callable, pre_work_callable = pre_work_callable )
            
        
        def _WipeWorkspace( self ):
            
            self._current_pertinent_tags = set()
            
            self._listctrl_async_updater.update()
            
        
        def EnterChildren( self, tags ):
            
            if len( tags ) > 0:
                
                self._parents.RemoveTags( tags )
                
                self._children.EnterTags( tags )
                
            
            self._listctrl_async_updater.update()
            
        
        def EnterChildrenOnlyAdd( self, tags ):
            
            current_children = self._children.GetTags()
            
            tags = { tag for tag in tags if tag not in current_children }
            
            if len( tags ) > 0:
                
                self.EnterChildren( tags )
                
            
        
        def EnterParents( self, tags ):
            
            if len( tags ) > 0:
                
                self._children.RemoveTags( tags )
                
                self._parents.EnterTags( tags )
                
            
            self._listctrl_async_updater.update()
            
        
        def EnterParentsOnlyAdd( self, tags ):
            
            current_parents = self._parents.GetTags()
            
            tags = { tag for tag in tags if tag not in current_parents }
            
            if len( tags ) > 0:
                
                self.EnterParents( tags )
                
            
        
        def GetContentUpdates( self ):
            
            content_updates = self._parent_action_context.GetContentUpdates()
            
            return ( self._service_key, content_updates )
            
        
        def GetServiceKey( self ):
            
            return self._service_key
            
        
        def HasUncommittedPair( self ):
            
            return len( self._children.GetTags() ) > 0 and len( self._parents.GetTags() ) > 0
            
        
        def SetTagBoxFocus( self ):
            
            if len( self._children.GetTags() ) == 0:
                
                self._children_input.setFocus( QC.Qt.FocusReason.OtherFocusReason )
                
            else:
                
                self._parents_input.setFocus( QC.Qt.FocusReason.OtherFocusReason )
                
            
        
        def _STARTInitialisation( self, tags, service_key ):
            
            def work_callable():
                
                ( master_service_keys_to_sibling_applicable_service_keys, master_service_keys_to_parent_applicable_service_keys ) = CG.client_controller.Read( 'tag_display_application' )
                
                service_keys_we_care_about = { s_k for ( s_k, s_ks ) in master_service_keys_to_parent_applicable_service_keys.items() if service_key in s_ks }
                
                service_keys_to_work_to_do = {}
                
                for s_k in service_keys_we_care_about:
                    
                    status = CG.client_controller.Read( 'tag_display_maintenance_status', s_k )
                    
                    work_to_do = status[ 'num_parents_to_sync' ] > 0
                    
                    service_keys_to_work_to_do[ s_k ] = work_to_do
                    
                
                return service_keys_to_work_to_do
                
            
            def publish_callable( result ):
                
                service_keys_to_work_to_do = result
                
                looking_good = True
                
                if len( service_keys_to_work_to_do ) == 0:
                    
                    looking_good = False
                    
                    status_text = 'No services currently apply these parents. Changes here will have no effect unless parent application is changed later.'
                    
                else:
                    
                    synced_names = sorted( ( CG.client_controller.services_manager.GetName( s_k ) for ( s_k, work_to_do ) in service_keys_to_work_to_do.items() if not work_to_do ) )
                    unsynced_names = sorted( ( CG.client_controller.services_manager.GetName( s_k ) for ( s_k, work_to_do ) in service_keys_to_work_to_do.items() if work_to_do ) )
                    
                    synced_string = ', '.join( ( '"{}"'.format( name ) for name in synced_names ) )
                    unsynced_string = ', '.join( ( '"{}"'.format( name ) for name in unsynced_names ) )
                    
                    if len( unsynced_names ) == 0:
                        
                        service_part = '{} apply these parents and are fully synced.'.format( synced_string )
                        
                    else:
                        
                        looking_good = False
                        
                        if len( synced_names ) > 0:
                            
                            service_part = '{} apply these parents and are fully synced, but {} still have work to do.'.format( synced_string, unsynced_string )
                            
                        else:
                            
                            service_part = '{} apply these parents but still have sync work to do.'.format( unsynced_string )
                            
                        
                    
                    if CG.client_controller.new_options.GetBoolean( 'tag_display_maintenance_during_active' ):
                        
                        maintenance_part = 'Parents are set to sync all the time in the background.'
                        
                        if looking_good:
                            
                            changes_part = 'Changes from this dialog should be reflected soon after closing the dialog.'
                            
                        else:
                            
                            changes_part = 'It may take some time for changes here to apply everywhere, though.'
                            
                        
                    else:
                        
                        looking_good = False
                        
                        if CG.client_controller.new_options.GetBoolean( 'tag_display_maintenance_during_idle' ):
                            
                            maintenance_part = 'Parents are set to sync only when you are not using the client.'
                            changes_part = 'It may take some time for changes here to apply.'
                            
                        else:
                            
                            maintenance_part = 'Parents are not set to sync.'
                            changes_part = 'Changes here will not apply unless sync is manually forced to run.'
                            
                        
                    
                    s = ' | '
                    status_text = s.join( ( service_part, maintenance_part, changes_part ) )
                    
                
                if not self._i_am_local_tag_service:
                    
                    account = self._service.GetAccount()
                    
                    if account.IsUnknown():
                        
                        looking_good = False
                        
                        s = 'The account for this service is currently unsynced! It is uncertain if you have permission to upload parents! Please try to refresh the account in _review services_.'
                        
                        status_text = '{}\n\n{}'.format( s, status_text )
                        
                    elif not account.HasPermission( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.PERMISSION_ACTION_PETITION ):
                        
                        looking_good = False
                        
                        s = 'The account for this service does not seem to have permission to upload parents! You can edit them here for now, but the pending menu will not try to upload any changes you make.'
                        
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
                    
                    self.EnterChildren( tags )
                    
                
                if self.isVisible():
                    
                    self.SetTagBoxFocus()
                    
                
            
            self._sync_status_st.setText( 'initialising sync data' + HC.UNICODE_ELLIPSIS )
            
            job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
            
            job.start()
            
        
    
