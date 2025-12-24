import collections
import collections.abc
import itertools
import random
import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusLists
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusTags
from hydrus.core import HydrusText
from hydrus.core.networking import HydrusNetwork

from hydrus.client import ClientApplicationCommand as CAC
from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientLocation
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIShortcuts
from hydrus.client.gui import ClientGUITagSuggestions
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListBoxes
from hydrus.client.gui.lists import ClientGUIListBook
from hydrus.client.gui.metadata import ClientGUIIncrementalTagging
from hydrus.client.gui.metadata import ClientGUIMigrateTags
from hydrus.client.gui.networking import ClientGUIHydrusNetwork
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.search import ClientGUIACDropdown
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.gui.widgets import ClientGUIMenuButton
from hydrus.client.media import ClientMedia
from hydrus.client.metadata import ClientContentUpdates
from hydrus.client.metadata import ClientTags
from hydrus.client.search import ClientSearchTagContext

class ManageTagsPanel( CAC.ApplicationCommandProcessorMixin, ClientGUIScrolledPanels.ManagePanel ):
    
    def __init__( self, parent, location_context: ClientLocation.LocationContext, tag_presentation_location: int, medias: list[ ClientMedia.MediaSingleton ], immediate_commit = False, canvas_key = None ):
        
        super().__init__( parent )
        
        self._location_context = location_context
        self._tag_presentation_location = tag_presentation_location
        
        self._immediate_commit = immediate_commit
        self._canvas_key = canvas_key
        
        self._current_media = [ m.Duplicate() for m in medias ]
        
        self._hashes = set()
        
        for m in self._current_media:
            
            self._hashes.update( m.GetHashes() )
            
        
        if CG.client_controller.new_options.GetBoolean( 'use_listbook_for_tag_service_panels' ):
            
            self._tag_services = ClientGUIListBook.ListBook( self )
            
        else:
            
            self._tag_services = ClientGUICommon.BetterNotebook( self )
            
        
        #
        
        services = list( CG.client_controller.services_manager.GetServices( ( HC.LOCAL_TAG, ) ) )
        
        services.extend( CG.client_controller.services_manager.GetServices( ( HC.TAG_REPOSITORY, ) ) )
        
        if HG.gui_report_mode:
            
            HydrusData.ShowText( f'Opening manage tags on these services: {services}' )
            
        
        default_tag_service_key = CG.client_controller.new_options.GetKey( 'default_tag_service_tab' )
        
        for service in services:
            
            service_key = service.GetServiceKey()
            name = service.GetName()
            
            if HG.gui_report_mode:
                
                HydrusData.ShowText( 'Opening manage tags panel on {}, {}, {}'.format( service, name, service_key.hex() ) )
                
            
            page = self._Panel( self._tag_services, self._location_context, service.GetServiceKey(), self._tag_presentation_location, self._current_media, self._immediate_commit, canvas_key = self._canvas_key )
            
            self._tag_services.addTab( page, name )
            
            page.movePageLeft.connect( self.MovePageLeft )
            page.movePageRight.connect( self.MovePageRight )
            page.showPrevious.connect( self.ShowPrevious )
            page.showNext.connect( self.ShowNext )
            
            page.okSignal.connect( self.okSignal )
            
            page.valueChanged.connect( self._UpdatePageTabNames )
            
            if service_key == default_tag_service_key:
                
                # Py 3.11/PyQt6 6.5.0/two tabs/total tab characters > ~12/select second tab during init = first tab disappears bug
                CG.client_controller.CallAfterQtSafe( self._tag_services, self._tag_services.setCurrentWidget, page )
                
            
        
        if HG.gui_report_mode:
            
            HydrusData.ShowText( 'Opening manage tags panel, notebook tab count is {}'.format( self._tag_services.count() ) )
            
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._tag_services, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
        CG.client_controller.CallAfterQtSafe( self._tag_services, self._tag_services.currentChanged.connect, self.EventServiceChanged )
        
        if self._canvas_key is not None:
            
            CG.client_controller.sub( self, 'CanvasHasNewMedia', 'canvas_new_display_media' )
            
        
        self._my_shortcut_handler = ClientGUIShortcuts.ShortcutsHandler( self, self, [ 'global', 'media', 'main_gui' ] )
        
        self._UpdatePageTabNames()
        
        CG.client_controller.CallAfterQtSafe( self, self._SetSearchFocus )
        
    
    def _GetContentUpdatePackages( self ):
        
        content_update_packages = []
        
        for page in self._tag_services.GetPages():
            
            content_update_packages.extend( page.GetContentUpdatePackages() )
            
        
        return content_update_packages
        
    
    def _SetSearchFocus( self ):
        
        current_page = typing.cast( ManageTagsPanel._Panel, self._tag_services.currentWidget() )
        
        if current_page is not None:
            
            current_page.SetTagBoxFocus()
            
        
    
    def _UpdatePageTabNames( self ):
        
        for index in range( self._tag_services.count() ):
            
            page = typing.cast( ManageTagsPanel._Panel, self._tag_services.widget( index ) )
            
            service_key = page.GetServiceKey()
            
            service_name = CG.client_controller.services_manager.GetServiceName( service_key )
            
            num_tags = page.GetTagCount()
            
            if num_tags > 0:
                
                tab_name = f'{service_name} ({num_tags})'
                
            else:
                
                tab_name = service_name
                
            
            if page.HasChanges():
                
                tab_name += ' *'
                
            
            if self._tag_services.tabText( index ) != tab_name:
                
                self._tag_services.setTabText( index, tab_name )
                
            
        
    
    def CanvasHasNewMedia( self, canvas_key, new_media_singleton ):
        
        if canvas_key == self._canvas_key:
            
            if new_media_singleton is not None:
                
                self._current_media = ( new_media_singleton.Duplicate(), )
                
                for page in self._tag_services.GetPages():
                    
                    page.SetMedia( self._current_media )
                    
                
                self._UpdatePageTabNames()
                
            
        
    
    def CleanBeforeDestroy( self ):
        
        ClientGUIScrolledPanels.ManagePanel.CleanBeforeDestroy( self )
        
        for page in self._tag_services.GetPages():
            
            page.CleanBeforeDestroy()
            
        
    
    def CommitChanges( self ):
        
        content_update_packages = self._GetContentUpdatePackages()
        
        for content_update_package in content_update_packages:
            
            CG.client_controller.WriteSynchronous( 'content_updates', content_update_package )
            
        
    
    def EventServiceChanged( self, index ):
        
        if self.sender() != self._tag_services:
            
            return
            
        
        current_page: ManageTagsPanel._Panel | None = self._tag_services.currentWidget()
        
        if current_page is not None:
            
            CG.client_controller.CallAfterQtSafe( current_page, current_page.SetTagBoxFocus )
            
        
        if CG.client_controller.new_options.GetBoolean( 'save_default_tag_service_tab_on_change' ):
            
            CG.client_controller.new_options.SetKey( 'default_tag_service_tab', current_page.GetServiceKey() )
            
        
    
    def ProcessApplicationCommand( self, command: CAC.ApplicationCommand ):
        
        command_processed = True
        
        if command.IsSimpleCommand():
            
            action = command.GetSimpleAction()
            
            if action == CAC.SIMPLE_MANAGE_FILE_TAGS:
                
                self._OKParent()
                
            elif action == CAC.SIMPLE_FOCUS_MEDIA_VIEWER:
                
                tlws = ClientGUIFunctions.GetTLWParents( self )
                
                from hydrus.client.gui.canvas import ClientGUICanvasFrame
                
                command_processed = False
                
                for tlw in tlws:
                    
                    if isinstance( tlw, ClientGUICanvasFrame.CanvasFrame ):
                        
                        tlw.TakeFocusForUser()
                        
                        command_processed = True
                        
                        break
                        
                    
                
            elif action == CAC.SIMPLE_SET_SEARCH_FOCUS:
                
                self._SetSearchFocus()
                
            else:
                
                command_processed = False
                
            
        else:
            
            command_processed = False
            
        
        return command_processed
        
    
    def MovePageRight( self ):
        
        self._tag_services.SelectRight()
        
        self._SetSearchFocus()
        
    
    def MovePageLeft( self ):
        
        self._tag_services.SelectLeft()
        
        self._SetSearchFocus()
        
    
    def ShowNext( self ):
        
        if self._canvas_key is not None:
            
            CG.client_controller.pub( 'canvas_show_next', self._canvas_key )
            
        
    
    def ShowPrevious( self ):
        
        if self._canvas_key is not None:
            
            CG.client_controller.pub( 'canvas_show_previous', self._canvas_key )
            
        
    
    def UserIsOKToCancel( self ):
        
        content_update_packages = self._GetContentUpdatePackages()
        
        if len( content_update_packages ) > 0:
            
            message = 'Are you sure you want to cancel? You have uncommitted changes that will be lost.'
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message )
            
            if result != QW.QDialog.DialogCode.Accepted:
                
                return False
                
            
        
        return True
        
    
    class _Panel( CAC.ApplicationCommandProcessorMixin, QW.QWidget ):
        
        okSignal = QC.Signal()
        movePageLeft = QC.Signal()
        movePageRight = QC.Signal()
        showPrevious = QC.Signal()
        showNext = QC.Signal()
        valueChanged = QC.Signal()
        
        def __init__( self, parent, location_context: ClientLocation.LocationContext, tag_service_key, tag_presentation_location: int, media: list[ ClientMedia.MediaSingleton ], immediate_commit, canvas_key = None ):
            
            super().__init__( parent )
            
            self._location_context = location_context
            self._tag_service_key = tag_service_key
            self._tag_presentation_location = tag_presentation_location
            self._immediate_commit = immediate_commit
            self._canvas_key = canvas_key
            
            self._pending_content_update_packages = []
            
            self._service = CG.client_controller.services_manager.GetService( self._tag_service_key )
            
            self._i_am_local_tag_service = self._service.GetServiceType() == HC.LOCAL_TAG
            
            tags_panel = QW.QWidget( self )
            
            self._tags_box_sorter = ClientGUIListBoxes.StaticBoxSorterForListBoxTags( tags_panel, 'tags', self._tag_presentation_location, show_siblings_sort = True )
            
            self._tags_box = ClientGUIListBoxes.ListBoxTagsMediaTagsDialog( self._tags_box_sorter, self._tag_presentation_location, self.EnterTags, self.RemoveTags )
            
            self._tags_box_sorter.SetTagsBox( self._tags_box )
            
            #
            
            self._new_options = CG.client_controller.new_options
            
            if self._i_am_local_tag_service:
                
                text = 'remove all/selected tags'
                
            else:
                
                text = 'petition to remove all/selected tags'
                
            
            self._remove_tags = ClientGUICommon.BetterButton( self._tags_box_sorter, text, self._RemoveTagsButton )
            
            self._copy_button = ClientGUICommon.IconButton( self._tags_box_sorter, CC.global_icons().copy, self._Copy )
            self._copy_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'Copy selected tags to the clipboard. If none are selected, copies all.' ) )
            
            menu_template_items = []
            
            check_manager = ClientGUICommon.CheckboxManagerOptions( 'allow_remove_on_manage_tags_input' )
            
            menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCheck( 'allow remove/petition result on tag input for already existing tag', 'If checked, inputting a tag that already exists will try to remove it.', check_manager ) )
            
            check_manager = ClientGUICommon.CheckboxManagerOptions( 'yes_no_on_remove_on_manage_tags' )
            
            menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCheck( 'confirm remove/petition tags on explicit delete actions', 'If checked, clicking the remove/petition tags button (or hitting the deleted key on the list) will first confirm the action with a yes/no dialog.', check_manager ) )
            
            check_manager = ClientGUICommon.CheckboxManagerOptions( 'ac_select_first_with_count' )
            
            menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCheck( 'select the first tag result with actual count', 'If checked, when results come in, the typed entry, if it has no count, will be skipped.', check_manager ) )
            
            menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemSeparator() )
            
            menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'migrate tags for these files', 'Migrate the tags for the files used to launch this manage tags panel.', self._MigrateTags ) )
            
            if not self._i_am_local_tag_service and self._service.HasPermission( HC.CONTENT_TYPE_ACCOUNTS, HC.PERMISSION_ACTION_MODERATE ):
                
                menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemSeparator() )
                
                menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'modify users who added the selected tags', 'Modify the users who added the selected tags.', self._ModifyMappers ) )
                
            
            self._incremental_tagging_button = ClientGUICommon.BetterButton( self._tags_box_sorter, HC.UNICODE_PLUS_OR_MINUS, self._DoIncrementalTagging )
            self._incremental_tagging_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'Incremental Tagging' ) )
            self._incremental_tagging_button.setVisible( len( media ) > 1 )
            
            width = ClientGUIFunctions.ConvertTextToPixelWidth( self._incremental_tagging_button, 5 )
            self._incremental_tagging_button.setFixedWidth( width )
            
            self._cog_button = ClientGUIMenuButton.CogIconButton( self._tags_box_sorter, menu_template_items )
            
            #
            
            self._deleted_tags_panel = QW.QWidget( self._tags_box_sorter )
            
            self._deleted_tags_label = ClientGUICommon.BetterStaticText( self._deleted_tags_panel, label = '0 deleted tags' )
            self._deleted_tags_label.setAlignment( QC.Qt.AlignmentFlag.AlignRight )
            self._deleted_tags_show_button = ClientGUICommon.IconButton( self._deleted_tags_panel, CC.global_icons().eye, self._FlipShowDeleted )
            
            #
            
            self._add_tag_box = ClientGUIACDropdown.AutoCompleteDropdownTagsWrite( tags_panel, self.AddTags, self._location_context, self._tag_service_key, show_paste_button = True )
            
            self._add_tag_box.movePageLeft.connect( self.movePageLeft )
            self._add_tag_box.movePageRight.connect( self.movePageRight )
            self._add_tag_box.showPrevious.connect( self.showPrevious )
            self._add_tag_box.showNext.connect( self.showNext )
            self._add_tag_box.externalCopyKeyPressEvent.connect( self._tags_box.keyPressEvent )
            self._add_tag_box.tagsPasted.connect( self._PasteComingFromAC )
            
            self._add_tag_box.nullEntered.connect( self.OK )
            
            self._tags_box.tagsChanged.connect( self._add_tag_box.SetContextTags )
            
            self._tags_box.SetTagServiceKey( self._tag_service_key )
            
            self._suggested_tags = ClientGUITagSuggestions.SuggestedTagsPanel( self, self._tag_service_key, self._tag_presentation_location, len( media ) == 1, self.AddTags )
            
            self._UpdateShowDeleted() # before setmedia
            
            self.SetMedia( media )
            
            button_hbox = QP.HBoxLayout()
            
            QP.AddToLayout( button_hbox, self._remove_tags, CC.FLAGS_CENTER_PERPENDICULAR )
            QP.AddToLayout( button_hbox, self._copy_button, CC.FLAGS_CENTER_PERPENDICULAR )
            QP.AddToLayout( button_hbox, self._incremental_tagging_button, CC.FLAGS_CENTER_PERPENDICULAR )
            QP.AddToLayout( button_hbox, self._cog_button, CC.FLAGS_CENTER_PERPENDICULAR )
            
            self._tags_box_sorter.Add( button_hbox, CC.FLAGS_ON_RIGHT )
            
            deleted_tags_hbox = QP.HBoxLayout( margin = 0 )
            
            QP.AddToLayout( deleted_tags_hbox, self._deleted_tags_label, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH )
            QP.AddToLayout( deleted_tags_hbox, self._deleted_tags_show_button, CC.FLAGS_CENTER_PERPENDICULAR )
            
            self._deleted_tags_panel.setLayout( deleted_tags_hbox )
            
            self._tags_box_sorter.Add( self._deleted_tags_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, self._tags_box_sorter, CC.FLAGS_EXPAND_BOTH_WAYS )
            QP.AddToLayout( vbox, self._add_tag_box, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            tags_panel.setLayout( vbox )
            
            #
            
            hbox = QP.HBoxLayout()
            
            QP.AddToLayout( hbox, self._suggested_tags, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( hbox, tags_panel, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            
            #
            
            self._my_shortcut_handler = ClientGUIShortcuts.ShortcutsHandler( self, self, [ 'global', 'main_gui' ] )
            
            self.setLayout( hbox )
            
            if self._immediate_commit:
                
                CG.client_controller.sub( self, 'ProcessContentUpdatePackage', 'content_updates_gui' )
                
            
            self._suggested_tags.mouseActivationOccurred.connect( self.SetTagBoxFocus )
            
            self._tags_box.tagsSelected.connect( self._suggested_tags.SetSelectedTags )
            
            CG.client_controller.sub( self, '_UpdateShowDeleted', 'notify_options_manage_tags_show_deleted_mappings' )
            
        
        def _EnterTags( self, tags, only_add = False, only_remove = False, forced_reason = None ):
            
            tags = HydrusTags.CleanTags( tags )
            
            if not self._i_am_local_tag_service and self._service.HasPermission( HC.CONTENT_TYPE_MAPPINGS, HC.PERMISSION_ACTION_MODERATE ):
                
                forced_reason = 'Entered by a janitor.'
                
            
            tags_managers = [ m.GetTagsManager() for m in self._media ]
            
            # TODO: All this should be extracted to another object that does some prep work and then answers questions like 'can I add this tag?' or 'what are the human-text/content-action choices for this tag?'
            # then we'll be able to do quick-add in other locations and so on with less hassle!
            
            currents = [ tags_manager.GetCurrent( self._tag_service_key, ClientTags.TAG_DISPLAY_STORAGE ) for tags_manager in tags_managers ]
            pendings = [ tags_manager.GetPending( self._tag_service_key, ClientTags.TAG_DISPLAY_STORAGE ) for tags_manager in tags_managers ]
            petitioneds = [ tags_manager.GetPetitioned( self._tag_service_key, ClientTags.TAG_DISPLAY_STORAGE ) for tags_manager in tags_managers ]
            
            num_files = len( self._media )
            
            # let's figure out what these tags can mean for the media--add, remove, or what?
            
            choices = collections.defaultdict( list )
            
            for tag in tags:
                
                num_current = sum( ( 1 for current in currents if tag in current ) )
                
                if self._i_am_local_tag_service:
                    
                    if not only_remove:
                        
                        if num_current < num_files:
                            
                            num_non_current = num_files - num_current
                            
                            choices[ HC.CONTENT_UPDATE_ADD ].append( ( tag, num_non_current ) )
                            
                        
                    
                    if not only_add:
                        
                        if num_current > 0:
                            
                            choices[ HC.CONTENT_UPDATE_DELETE ].append( ( tag, num_current ) )
                            
                        
                    
                else:
                    
                    num_pending = sum( ( 1 for pending in pendings if tag in pending ) )
                    num_petitioned = sum( ( 1 for petitioned in petitioneds if tag in petitioned ) )
                    
                    if not only_remove:
                        
                        # it is possible to have content petitioned without being current
                        # we don't want to pend in this case!
                        
                        if num_current + num_pending + num_petitioned < num_files:
                            
                            num_pendable = num_files - ( num_current + num_pending + num_petitioned )
                            
                            choices[ HC.CONTENT_UPDATE_PEND ].append( ( tag, num_pendable ) )
                            
                        
                    
                    if not only_add:
                        
                        # although it is technically possible to petition content that doesn't exist yet...
                        # for human uses, we do not want to provide petition as an option unless it is already current
                        
                        if num_current > num_petitioned and not only_add:
                            
                            num_petitionable = num_current - num_petitioned
                            
                            choices[ HC.CONTENT_UPDATE_PETITION ].append( ( tag, num_petitionable ) )
                            
                        
                        if num_pending > 0 and not only_add:
                            
                            choices[ HC.CONTENT_UPDATE_RESCIND_PEND ].append( ( tag, num_pending ) )
                            
                        
                    
                    if not only_remove:
                        
                        if num_petitioned > 0:
                            
                            choices[ HC.CONTENT_UPDATE_RESCIND_PETITION ].append( ( tag, num_petitioned ) )
                            
                        
                    
                
            
            if len( choices ) == 0:
                
                return
                
            
            # now we have options, let's ask the user what they want to do
            
            if len( choices ) == 1:
                
                [ ( choice_action, tag_counts ) ] = list( choices.items() )
                
                tags = { tag for ( tag, count ) in tag_counts }
                
            else:
                
                bdc_choices = []
                
                preferred_order = [ HC.CONTENT_UPDATE_ADD, HC.CONTENT_UPDATE_DELETE, HC.CONTENT_UPDATE_PEND, HC.CONTENT_UPDATE_RESCIND_PEND, HC.CONTENT_UPDATE_PETITION, HC.CONTENT_UPDATE_RESCIND_PETITION ]
                
                choice_text_lookup = {}
                
                choice_text_lookup[ HC.CONTENT_UPDATE_ADD ] = 'add'
                choice_text_lookup[ HC.CONTENT_UPDATE_DELETE ] = 'delete'
                choice_text_lookup[ HC.CONTENT_UPDATE_PEND ] = 'pend (add)'
                choice_text_lookup[ HC.CONTENT_UPDATE_PETITION ] = 'petition to remove'
                choice_text_lookup[ HC.CONTENT_UPDATE_RESCIND_PEND ] = 'undo pend'
                choice_text_lookup[ HC.CONTENT_UPDATE_RESCIND_PETITION ] = 'undo petition to remove'
                
                choice_tooltip_lookup = {}
                
                choice_tooltip_lookup[ HC.CONTENT_UPDATE_ADD ] = 'this adds the tags to this local tag domain'
                choice_tooltip_lookup[ HC.CONTENT_UPDATE_DELETE ] = 'this deletes the tags from this local tag domain'
                choice_tooltip_lookup[ HC.CONTENT_UPDATE_PEND ] = 'this pends the tags to be added to this tag repository when you upload'
                choice_tooltip_lookup[ HC.CONTENT_UPDATE_PETITION ] = 'this petitions the tags for deletion from this tag repository when you upload'
                choice_tooltip_lookup[ HC.CONTENT_UPDATE_RESCIND_PEND ] = 'this rescinds the currently pending tags, so they will not be added'
                choice_tooltip_lookup[ HC.CONTENT_UPDATE_RESCIND_PETITION ] = 'this rescinds the current tag petitions, so they will not be deleted'
                
                for choice_action in preferred_order:
                    
                    if choice_action not in choices:
                        
                        continue
                        
                    
                    choice_text_prefix = choice_text_lookup[ choice_action ]
                    
                    tag_counts = choices[ choice_action ]
                    
                    choice_tags = { tag for ( tag, count ) in tag_counts }
                    
                    if len( choice_tags ) == 1:
                        
                        [ ( tag, count ) ] = tag_counts
                        
                        text = '{} "{}" for {} files'.format( choice_text_prefix, HydrusText.ElideText( tag, 64 ), HydrusNumbers.ToHumanInt( count ) )
                        
                    else:
                        
                        text = '{} {} tags'.format( choice_text_prefix, HydrusNumbers.ToHumanInt( len( choice_tags ) ) )
                        
                    
                    data = ( choice_action, choice_tags )
                    
                    t_c_lines = [ choice_tooltip_lookup[ choice_action ] ]
                    
                    if len( tag_counts ) > 25:
                        
                        t_c = tag_counts[:25]
                        
                    else:
                        
                        t_c = tag_counts
                        
                    
                    t_c_lines.extend( ( '{} - {} files'.format( tag, HydrusNumbers.ToHumanInt( count ) ) for ( tag, count ) in t_c ) )
                    
                    if len( tag_counts ) > 25:
                        
                        t_c_lines.append( 'and {} others'.format( HydrusNumbers.ToHumanInt( len( tag_counts ) - 25 ) ) )
                        
                    
                    tooltip = '\n'.join( t_c_lines )
                    
                    bdc_choices.append( ( text, data, tooltip ) )
                    
                
                try:
                    
                    if len( tags ) > 1:
                        
                        message = 'The file{} some of those tags, but not all, so there are different things you can do.'.format( 's have' if len( self._media ) > 1 else ' has' )
                        
                    else:
                        
                        message = 'Of the {} files being managed, some have that tag, but not all of them do, so there are different things you can do.'.format( HydrusNumbers.ToHumanInt( len( self._media ) ) )
                        
                    
                    ( choice_action, tags ) = ClientGUIDialogsQuick.SelectFromListButtons( self, 'What would you like to do?', bdc_choices, message = message )
                    
                except HydrusExceptions.CancelledException:
                    
                    return
                    
                
            
            reason = None
            
            if choice_action == HC.CONTENT_UPDATE_PETITION:
                
                if forced_reason is None:
                    
                    # add the easy reason buttons here
                    
                    if len( tags ) == 1:
                        
                        ( tag, ) = tags
                        
                        tag_text = '"' + tag + '"'
                        
                    else:
                        
                        tag_text = 'the ' + HydrusNumbers.ToHumanInt( len( tags ) ) + ' tags'
                        
                    
                    message = 'Enter a reason for ' + tag_text + ' to be removed. A janitor will review your petition.'
                    
                    fixed_suggestions = [
                        'mangled parse/typo',
                        'not applicable/incorrect',
                        'clearing mass-pasted junk',
                        'splitting filename/title/etc... into individual tags'
                    ]
                    
                    suggestions = CG.client_controller.new_options.GetRecentPetitionReasons( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_DELETE )
                    
                    suggestions.extend( fixed_suggestions )
                    
                    try:
                        
                        reason = ClientGUIDialogsQuick.EnterText( self, message, suggestions = suggestions )
                        
                    except HydrusExceptions.CancelledException:
                        
                        return
                        
                    
                    if reason not in fixed_suggestions:
                        
                        CG.client_controller.new_options.PushRecentPetitionReason( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_DELETE, reason )
                        
                    
                else:
                    
                    reason = forced_reason
                    
                
            
            # we have an action and tags, so let's effect the content updates
            
            content_updates_for_this_call = []
            
            recent_tags = set()
            
            medias_and_tags_managers = [ ( m, m.GetTagsManager() ) for m in self._media ]
            medias_and_sets_of_tags = [ ( m, tm.GetCurrent( self._tag_service_key, ClientTags.TAG_DISPLAY_STORAGE ), tm.GetPending( self._tag_service_key, ClientTags.TAG_DISPLAY_STORAGE ), tm.GetPetitioned( self._tag_service_key, ClientTags.TAG_DISPLAY_STORAGE ) ) for ( m, tm ) in medias_and_tags_managers ]
            
            # there is a big CPU hit here as every time you ProcessContentUpdatePackage, the tagsmanagers need to regen caches lmao
            # so if I refetch current tags etc... for every tag loop, we end up getting 16 million tagok calls etc...
            # however, as tags is a set, thus with unique members, let's say for now this is ok, don't need to regen just to consult current
            
            for tag in tags:
                
                if choice_action == HC.CONTENT_UPDATE_ADD:
                    
                    media_to_affect = [ m for ( m, mc, mp, mpt ) in medias_and_sets_of_tags if tag not in mc ]
                    
                elif choice_action == HC.CONTENT_UPDATE_DELETE:
                    
                    media_to_affect = [ m for ( m, mc, mp, mpt ) in medias_and_sets_of_tags if tag in mc ]
                    
                elif choice_action == HC.CONTENT_UPDATE_PEND:
                    
                    # check petitioned too, we don't want both at once!
                    media_to_affect = [ m for ( m, mc, mp, mpt ) in medias_and_sets_of_tags if tag not in mc and tag not in mp and tag not in mpt ]
                    
                elif choice_action == HC.CONTENT_UPDATE_PETITION:
                    
                    # check current even though we don't have to (it makes it more human to say things need to be current here before being petitioned)
                    # check pending too, we don't want both at once!
                    media_to_affect = [ m for ( m, mc, mp, mpt ) in medias_and_sets_of_tags if tag in mc and tag not in mpt and tag not in mp ]
                    
                elif choice_action == HC.CONTENT_UPDATE_RESCIND_PEND:
                    
                    media_to_affect = [ m for ( m, mc, mp, mpt ) in medias_and_sets_of_tags if tag in mp ]
                    
                elif choice_action == HC.CONTENT_UPDATE_RESCIND_PETITION:
                    
                    media_to_affect = [ m for ( m, mc, mp, mpt ) in medias_and_sets_of_tags if tag in mpt ]
                    
                else:
                    
                    raise Exception( 'Unknown tag action choice!' )
                    
                
                hashes = set( itertools.chain.from_iterable( ( m.GetHashes() for m in media_to_affect ) ) )
                
                if len( hashes ) > 0:
                    
                    content_updates = []
                    
                    if choice_action in ( HC.CONTENT_UPDATE_ADD, HC.CONTENT_UPDATE_PEND ):
                        
                        recent_tags.add( tag )
                        
                    
                    content_updates.append( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, choice_action, ( tag, hashes ), reason = reason ) )
                    
                    if len( content_updates ) > 0:
                        
                        if not self._immediate_commit:
                            
                            for m in media_to_affect:
                                
                                mt = m.GetTagsManager()
                                
                                for content_update in content_updates:
                                    
                                    mt.ProcessContentUpdate( self._tag_service_key, content_update )
                                    
                                
                            
                        
                        content_updates_for_this_call.extend( content_updates )
                        
                    
                
            
            num_recent_tags = CG.client_controller.new_options.GetNoneableInteger( 'num_recent_tags' )
            
            if len( recent_tags ) > 0 and num_recent_tags is not None:
                
                recent_tags = list( recent_tags )
                
                if len( recent_tags ) > num_recent_tags:
                    
                    recent_tags = random.sample( recent_tags, num_recent_tags )
                    
                
                CG.client_controller.Write( 'push_recent_tags', self._tag_service_key, recent_tags )
                
            
            if len( content_updates_for_this_call ) > 0:
                
                content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( self._tag_service_key, content_updates_for_this_call )
                
                if self._immediate_commit:
                    
                    CG.client_controller.WriteSynchronous( 'content_updates', content_update_package )
                    
                else:
                    
                    self._pending_content_update_packages.append( content_update_package )
                    
                    self._suggested_tags.MediaUpdated()
                    
                
            
            self._tags_box.SetTagsByMedia( self._media )
            
            self._UpdateDeletedMappingsLabelAndVisibility()
            
            self.valueChanged.emit()
            
        
        def _Copy( self ):
            
            tags = list( self._tags_box.GetSelectedTags() )
            
            if len( tags ) == 0:
                
                ( current_tags_to_count, deleted_tags_to_count, pending_tags_to_count, petitioned_tags_to_count ) = ClientMedia.GetMediasTagCount( self._media, self._tag_service_key, ClientTags.TAG_DISPLAY_STORAGE )
                
                tags = set( current_tags_to_count.keys() ).union( pending_tags_to_count.keys() )
                
            
            if len( tags ) > 0:
                
                tags = HydrusTags.SortNumericTags( tags )
                
                text = '\n'.join( tags )
                
                CG.client_controller.pub( 'clipboard', 'text', text )
                
            
        
        def _DoIncrementalTagging( self ):
            
            title = 'Incremental Tagging'
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, title ) as dlg:
                
                panel = ClientGUIIncrementalTagging.IncrementalTaggingPanel( dlg, self._tag_service_key, self._media )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                    
                    content_update_package = panel.GetValue()
                    
                    if content_update_package.HasContent():
                        
                        if self._immediate_commit:
                            
                            CG.client_controller.WriteSynchronous( 'content_updates', content_update_package )
                            
                        else:
                            
                            self._pending_content_update_packages.append( content_update_package )
                            
                            self.ProcessContentUpdatePackage( content_update_package )
                            
                        
                    
                
            
        
        def _FlipShowDeleted( self ):
            
            CG.client_controller.new_options.FlipBoolean( 'manage_tags_show_deleted_mappings' )
            
            CG.client_controller.pub( 'notify_options_manage_tags_show_deleted_mappings' )
            
        
        def _MigrateTags( self ):
            
            hashes = set()
            
            for m in self._media:
                
                hashes.update( m.GetHashes() )
                
            
            def do_it( tag_service_key, hashes ):
                
                tlw = CG.client_controller.GetMainTLW()
                
                frame = ClientGUITopLevelWindowsPanels.FrameThatTakesScrollablePanel( tlw, 'migrate tags' )
                
                panel = ClientGUIMigrateTags.MigrateTagsPanel( frame, tag_service_key, hashes )
                
                frame.SetPanel( panel )
                
            
            CG.client_controller.CallAfterQtSafe( self, do_it, self._tag_service_key, hashes )
            
            self.OK()
            
        
        def _ModifyMappers( self ):
            
            contents = []
            
            tags = self._tags_box.GetSelectedTags()
            
            if len( tags ) == 0:
                
                ClientGUIDialogsMessage.ShowWarning( self, 'Please select some tags first!' )
                
                return
                
            
            hashes_and_current_tags = [ ( m.GetHashes(), m.GetTagsManager().GetCurrent( self._tag_service_key, ClientTags.TAG_DISPLAY_STORAGE ) ) for m in self._media ]
            
            for tag in tags:
                
                hashes_iter = itertools.chain.from_iterable( ( hashes for ( hashes, current_tags ) in hashes_and_current_tags if tag in current_tags ) )
                
                contents.extend( [ HydrusNetwork.Content( HC.CONTENT_TYPE_MAPPING, ( tag, hash ) ) for hash in hashes_iter ] )
                
            
            if len( contents ) > 0:
                
                subject_account_identifiers = [ HydrusNetwork.AccountIdentifier( content = content ) for content in contents ]
                
                frame = ClientGUITopLevelWindowsPanels.FrameThatTakesScrollablePanel( self.window().parentWidget(), 'manage accounts' )
                
                panel = ClientGUIHydrusNetwork.ModifyAccountsPanel( frame, self._tag_service_key, subject_account_identifiers )
                
                frame.SetPanel( panel )
                
            
        
        def _PasteComingFromAC( self, tags: list[ str ] ):
            
            self.AddTags( tags, only_add = True )
            
        
        def _RemoveTagsButton( self ):
            
            tags_managers = [ m.GetTagsManager() for m in self._media ]
            
            removable_tags = set()
            
            for tags_manager in tags_managers:
                
                removable_tags.update( tags_manager.GetCurrent( self._tag_service_key, ClientTags.TAG_DISPLAY_STORAGE ) )
                removable_tags.update( tags_manager.GetPending( self._tag_service_key, ClientTags.TAG_DISPLAY_STORAGE ) )
                
            
            selected_tags = list( self._tags_box.GetSelectedTags() )
            
            if len( selected_tags ) == 0:
                
                tags_to_remove = list( removable_tags )
                
            else:
                
                tags_to_remove = [ tag for tag in selected_tags if tag in removable_tags ]
                
            
            tags_to_remove = HydrusTags.SortNumericTags( tags_to_remove )
            
            self.RemoveTags( tags_to_remove )
            
        
        def _UpdateDeletedMappingsLabelAndVisibility( self ):
            
            tag_context = ClientSearchTagContext.TagContext( service_key = self._tag_service_key )
            
            num_deleted_mappings = sum( ( m.GetTagsManager().GetNumDeletedMappings( tag_context, ClientTags.TAG_DISPLAY_STORAGE ) for m in self._media ) )
            
            self._deleted_tags_label.setText( f'{HydrusNumbers.ToHumanInt( num_deleted_mappings )} deleted mappings' )
            
            self._deleted_tags_panel.setVisible( num_deleted_mappings > 0 )
            
        
        def _UpdateShowDeleted( self ):
            
            manage_tags_show_deleted_mappings = CG.client_controller.new_options.GetBoolean( 'manage_tags_show_deleted_mappings' )
            
            self._tags_box.SetShow( 'deleted', manage_tags_show_deleted_mappings )
            
            icon = CC.global_icons().eye if manage_tags_show_deleted_mappings else CC.global_icons().eye_closed
            tooltip = 'hide deleted mappings' if manage_tags_show_deleted_mappings else 'show deleted mappings'
            
            self._deleted_tags_show_button.SetIconSmart( icon )
            self._deleted_tags_show_button.setToolTip( ClientGUIFunctions.WrapToolTip( tooltip ) )
            
        
        def AddTags( self, tags, only_add = False ):
            
            if not self._new_options.GetBoolean( 'allow_remove_on_manage_tags_input' ):
                
                only_add = True
                
            
            if len( tags ) > 0:
                
                self.EnterTags( tags, only_add = only_add )
                
            
        
        def CleanBeforeDestroy( self ):
            
            self._add_tag_box.CancelCurrentResultsFetchJob()
            
        
        def ClearMedia( self ):
            
            self.SetMedia( set() )
            
        
        def EnterTags( self, tags, only_add = False ):
            
            if len( tags ) > 0:
                
                self._EnterTags( tags, only_add = only_add )
                
            
        
        def GetContentUpdatePackages( self ):
            
            return self._pending_content_update_packages
            
        
        def GetTagCount( self ):
            
            return self._tags_box.GetNumTerms()
            
        
        def GetServiceKey( self ):
            
            return self._tag_service_key
            
        
        def HasChanges( self ):
            
            return len( self._pending_content_update_packages ) > 0
            
        
        def NotifyTagDisplaySettingsChanged( self ):
            
            self._tags_box.update()
            
        
        def OK( self ):
            
            self.okSignal.emit()
            
        
        def ProcessApplicationCommand( self, command: CAC.ApplicationCommand ):
            
            command_processed = True
            
            if command.IsSimpleCommand():
                
                action = command.GetSimpleAction()
                
                if action == CAC.SIMPLE_SET_SEARCH_FOCUS:
                    
                    self.SetTagBoxFocus()
                    
                elif action in ( CAC.SIMPLE_SHOW_AND_FOCUS_MANAGE_TAGS_FAVOURITE_TAGS, CAC.SIMPLE_SHOW_AND_FOCUS_MANAGE_TAGS_RELATED_TAGS, CAC.SIMPLE_SHOW_AND_FOCUS_MANAGE_TAGS_FILE_LOOKUP_SCRIPT_TAGS, CAC.SIMPLE_SHOW_AND_FOCUS_MANAGE_TAGS_RECENT_TAGS ):
                    
                    self._suggested_tags.TakeFocusForUser( action )
                    
                elif action == CAC.SIMPLE_REFRESH_RELATED_TAGS:
                    
                    self._suggested_tags.RefreshRelatedThorough()
                    
                else:
                    
                    command_processed = False
                    
                
            else:
                
                command_processed = False
                
            
            return command_processed
            
        
        def ProcessContentUpdatePackage( self, content_update_package: ClientContentUpdates.ContentUpdatePackage ):
            
            for ( service_key, content_updates ) in content_update_package.IterateContentUpdates():
                
                for content_update in content_updates:
                    
                    for m in self._media:
                        
                        if HydrusLists.SetsIntersect( m.GetHashes(), content_update.GetHashes() ):
                            
                            m.GetMediaResult().ProcessContentUpdate( service_key, content_update )
                            
                        
                    
                
            
            self._tags_box.SetTagsByMedia( self._media )
            
            self._UpdateDeletedMappingsLabelAndVisibility()
            
            self.valueChanged.emit()
            
            self._suggested_tags.MediaUpdated()
            
        
        def RemoveTags( self, tags ):
            
            if len( tags ) > 0:
                
                if self._new_options.GetBoolean( 'yes_no_on_remove_on_manage_tags' ):
                    
                    if len( tags ) < 10:
                        
                        message = 'Are you sure you want to remove these tags:'
                        message += '\n' * 2
                        message += '\n'.join( ( HydrusText.ElideText( tag, 64 ) for tag in tags ) )
                        
                    else:
                        
                        message = 'Are you sure you want to remove these ' + HydrusNumbers.ToHumanInt( len( tags ) ) + ' tags?'
                        
                    
                    result = ClientGUIDialogsQuick.GetYesNo( self, message )
                    
                    if result != QW.QDialog.DialogCode.Accepted:
                        
                        return
                        
                    
                
                self._EnterTags( tags, only_remove = True )
                
            
        
        def SetMedia( self, media ):
            
            if media is None:
                
                media = set()
                
            
            self._media = media
            
            self._tags_box.SetTagsByMedia( self._media )
            
            self._UpdateDeletedMappingsLabelAndVisibility()
            
            self.valueChanged.emit()
            
            self._suggested_tags.SetMedia( media )
            
        
        def SetTagBoxFocus( self ):
            
            self._add_tag_box.setFocus( QC.Qt.FocusReason.OtherFocusReason )
            
        
