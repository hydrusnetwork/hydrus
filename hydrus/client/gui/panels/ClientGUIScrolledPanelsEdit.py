import collections.abc
import json
import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusLists
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusText

from hydrus.client import ClientApplicationCommand as CAC
from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIShortcuts
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtInit
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.canvas import ClientGUIMPV
from hydrus.client.gui.importing import ClientGUIImportOptions
from hydrus.client.gui.lists import ClientGUIListBoxes
from hydrus.client.gui.lists import ClientGUIListConstants as CGLC
from hydrus.client.gui.lists import ClientGUIListCtrl
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.importing.options import NoteImportOptions
from hydrus.client.importing.options import TagImportOptions
from hydrus.client.media import ClientMedia
from hydrus.client.media import ClientMediaResult
from hydrus.client.metadata import ClientContentUpdates
from hydrus.client.networking import ClientNetworkingFunctions

# TODO: ok the general plan here is to move rich panels to topical gui.xxx modules
# this new gui.panels is going to be for basic panel template stuff

class EditDefaultImportOptionsPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__(
        self,
        parent: QW.QWidget,
        url_classes,
        parsers,
        url_class_keys_to_parser_keys: dict[ bytes, bytes ],
        file_post_default_tag_import_options: TagImportOptions.TagImportOptions,
        watchable_default_tag_import_options: TagImportOptions.TagImportOptions,
        url_class_keys_to_tag_import_options: dict[ bytes, TagImportOptions.TagImportOptions ],
        file_post_default_note_import_options: NoteImportOptions.NoteImportOptions,
        watchable_default_note_import_options: NoteImportOptions.NoteImportOptions,
        url_class_keys_to_note_import_options: dict[ bytes, NoteImportOptions.NoteImportOptions ]
    ):
        
        super().__init__( parent )
        
        self._url_classes = url_classes
        self._parsers = parsers
        self._url_class_keys_to_parser_keys = url_class_keys_to_parser_keys
        self._parser_keys_to_parsers = { parser.GetParserKey() : parser for parser in self._parsers }
        
        self._url_class_keys_to_tag_import_options = dict( url_class_keys_to_tag_import_options )
        self._url_class_keys_to_note_import_options = dict( url_class_keys_to_note_import_options )
        
        #
        
        show_downloader_options = True
        allow_default_selection = False
        
        self._file_post_default_import_options_button = ClientGUIImportOptions.ImportOptionsButton( self, show_downloader_options, allow_default_selection )
        
        self._file_post_default_import_options_button.SetTagImportOptions( file_post_default_tag_import_options )
        self._file_post_default_import_options_button.SetNoteImportOptions( file_post_default_note_import_options )
        
        self._watchable_default_import_options_button = ClientGUIImportOptions.ImportOptionsButton( self, show_downloader_options, allow_default_selection )
        
        self._watchable_default_import_options_button.SetTagImportOptions( watchable_default_tag_import_options )
        self._watchable_default_import_options_button.SetNoteImportOptions( watchable_default_note_import_options )
        
        self._list_ctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_DEFAULT_TAG_IMPORT_OPTIONS.ID, self._ConvertDataToDisplayTuple, self._ConvertDataToSortTuple )
        
        self._list_ctrl = ClientGUIListCtrl.BetterListCtrlTreeView( self._list_ctrl_panel, 15, model, activation_callback = self._Edit )
        
        self._list_ctrl_panel.SetListCtrl( self._list_ctrl )
        
        self._list_ctrl_panel.AddButton( 'copy tags', self._CopyTags, enabled_check_func = self._OnlyOneTIOSelected )
        self._list_ctrl_panel.AddButton( 'copy notes', self._CopyNotes, enabled_check_func = self._OnlyOneNIOSelected )
        self._list_ctrl_panel.AddButton( 'paste', self._Paste, enabled_only_on_selection = True )
        self._list_ctrl_panel.AddButton( 'edit', self._Edit, enabled_only_on_single_selection = True )
        self._list_ctrl_panel.AddButton( 'clear tags', self._ClearTags, enabled_check_func = self._AtLeastOneTIOSelected )
        self._list_ctrl_panel.AddButton( 'clear notes', self._ClearNotes, enabled_check_func = self._AtLeastOneNIOSelected )
        
        #
        
        eligible_url_classes = [ url_class for url_class in url_classes if url_class.GetURLType() in ( HC.URL_TYPE_POST, HC.URL_TYPE_WATCHABLE, HC.URL_TYPE_GALLERY ) and url_class.GetClassKey() in self._url_class_keys_to_parser_keys ]
        
        self._list_ctrl.AddDatas( eligible_url_classes )
        
        self._list_ctrl.Sort()
        
        #
        
        rows = []
        
        rows.append( ( 'default for file posts: ', self._file_post_default_import_options_button ) )
        rows.append( ( 'default for watchable urls: ', self._watchable_default_import_options_button ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        vbox = QP.VBoxLayout()
        
        label = 'Hydrus will first check the URL that you see in the "file log". If it matches an URL Class entry in the list below, and that row has specific defaults set, those will be used. If no match is found (or the URL is Unknown/File URL), hydrus will look at the Referral URL, which is usually a Gallery or Watchable URL. If that has specific options, those will be used; if not, then the default for file posts or watchable urls will be chosen respectively.'
        label += '\n\n'
        label += 'Make sure you set good options that you will always be happy with under "default for file posts", since that will be used most often. Then, if you need a special blacklist or tag rules for a certain site, try to set it to the appropriate "Post URL", if any. If the downloader produces raw file URLs in the "file log", then set options for the Gallery or Watchable URL you see in the "search/check log".'
        label += '\n\n'
        label += 'If you figure out some good options here and need to "re-run" some earlier downloads with the new defaults, do not just re-queue the files\' URLs for a redownload in an URLs downloader page--hydrus will skip booru-style URLs it has seen before, so it will not refetch the metadata for your new options in this case. Instead, try selecting the files and _right-click->urls->force metadata refetch->url class_, which will do that same job for you but with a special flag set to force the refetch.'
        
        st = ClientGUICommon.BetterStaticText( self, label = label )
        st.setWordWrap( True )
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, self._list_ctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
    def _AtLeastOneNIOSelected( self ):
        
        selected = self._list_ctrl.GetData( only_selected = True )
        
        for url_class in selected:
            
            url_class_key = url_class.GetClassKey()
            
            if url_class_key in self._url_class_keys_to_note_import_options:
                
                return True
                
            
        
        return False
        
    
    def _AtLeastOneTIOSelected( self ):
        
        selected = self._list_ctrl.GetData( only_selected = True )
        
        for url_class in selected:
            
            url_class_key = url_class.GetClassKey()
            
            if url_class_key in self._url_class_keys_to_tag_import_options:
                
                return True
                
            
        
        return False
        
    
    def _ConvertDataToDisplayTuple( self, url_class ):
        
        url_class_key = url_class.GetClassKey()
        
        name = url_class.GetName()
        url_type = url_class.GetURLType()
        
        pretty_name = name
        pretty_url_type = HC.url_type_string_lookup[ url_type ]
        
        defaults_components = []
        
        if url_class_key in self._url_class_keys_to_tag_import_options:
            
            defaults_components.append( 'tags' )
            
        
        if url_class_key in self._url_class_keys_to_note_import_options:
            
            defaults_components.append( 'notes' )
            
        
        pretty_defaults_set = ', '.join( defaults_components )
        
        display_tuple = ( pretty_name, pretty_url_type, pretty_defaults_set )
        
        return display_tuple
        
    
    _ConvertDataToSortTuple = _ConvertDataToDisplayTuple
    
    def _ClearNotes( self ):
        
        result = ClientGUIDialogsQuick.GetYesNo( self, 'Clear set note import options for all selected?' )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            url_classes_to_clear = self._list_ctrl.GetData( only_selected = True )
            
            for url_class in url_classes_to_clear:
                
                url_class_key = url_class.GetClassKey()
                
                if url_class_key in self._url_class_keys_to_note_import_options:
                    
                    del self._url_class_keys_to_note_import_options[ url_class_key ]
                    
                
            
            self._list_ctrl.UpdateDatas( url_classes_to_clear )
            
        
    
    def _ClearTags( self ):
        
        result = ClientGUIDialogsQuick.GetYesNo( self, 'Clear set tag import options for all selected?' )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            url_classes_to_clear = self._list_ctrl.GetData( only_selected = True )
            
            for url_class in url_classes_to_clear:
                
                url_class_key = url_class.GetClassKey()
                
                if url_class_key in self._url_class_keys_to_tag_import_options:
                    
                    del self._url_class_keys_to_tag_import_options[ url_class_key ]
                    
                
            
            self._list_ctrl.UpdateDatas( url_classes_to_clear )
            
        
    
    def _CopyNotes( self ):
        
        selected = self._list_ctrl.GetData( only_selected = True )
        
        if len( selected ) == 1:
            
            url_class = selected[0]
            
            url_class_key = url_class.GetClassKey()
            
            if url_class_key in self._url_class_keys_to_note_import_options:
                
                note_import_options = self._url_class_keys_to_note_import_options[ url_class_key ]
                
                json_string = note_import_options.DumpToString()
                
                CG.client_controller.pub( 'clipboard', 'text', json_string )
                
            
        
    
    def _CopyTags( self ):
        
        selected = self._list_ctrl.GetData( only_selected = True )
        
        if len( selected ) == 1:
            
            url_class = selected[0]
            
            url_class_key = url_class.GetClassKey()
            
            if url_class_key in self._url_class_keys_to_tag_import_options:
                
                tag_import_options = self._url_class_keys_to_tag_import_options[ url_class_key ]
                
                json_string = tag_import_options.DumpToString()
                
                CG.client_controller.pub( 'clipboard', 'text', json_string )
                
            
        
    
    def _Edit( self ):
        
        url_classes_to_edit = self._list_ctrl.GetData( only_selected = True )
        
        for url_class in url_classes_to_edit:
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit tag import options' ) as dlg:
                
                tag_import_options = self._GetDefaultTagImportOptions( url_class )
                note_import_options = self._GetDefaultNoteImportOptions( url_class )
                
                show_downloader_options = True
                allow_default_selection = True
                
                panel = ClientGUIImportOptions.EditImportOptionsPanel( dlg, show_downloader_options, allow_default_selection )
                
                panel.SetTagImportOptions( tag_import_options )
                panel.SetNoteImportOptions( note_import_options )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                    
                    url_class_key = url_class.GetClassKey()
                    
                    if url_class_key in self._url_class_keys_to_tag_import_options:
                        
                        del self._url_class_keys_to_tag_import_options[ url_class_key ]
                        
                    
                    tag_import_options = panel.GetTagImportOptions()
                    
                    if not tag_import_options.IsDefault():
                        
                        self._url_class_keys_to_tag_import_options[ url_class_key ] = tag_import_options
                        
                    
                    if url_class_key in self._url_class_keys_to_note_import_options:
                        
                        del self._url_class_keys_to_note_import_options[ url_class_key ]
                        
                    
                    note_import_options = panel.GetNoteImportOptions()
                    
                    if not note_import_options.IsDefault():
                        
                        self._url_class_keys_to_note_import_options[ url_class_key ] = note_import_options
                        
                    
                else:
                    
                    break
                    
                
            
        
        self._list_ctrl.UpdateDatas( url_classes_to_edit )
        
    
    def _GetDefaultNoteImportOptions( self, url_class ):
        
        url_class_key = url_class.GetClassKey()
        
        if url_class_key in self._url_class_keys_to_note_import_options:
            
            note_import_options = self._url_class_keys_to_note_import_options[ url_class_key ]
            
        else:
            
            url_type = url_class.GetURLType()
            
            if url_type == HC.URL_TYPE_WATCHABLE:
                
                note_import_options = self._watchable_default_import_options_button.GetNoteImportOptions()
                
            else:
                
                note_import_options = self._file_post_default_import_options_button.GetNoteImportOptions()
                
            
            note_import_options = note_import_options.Duplicate()
            
            note_import_options.SetIsDefault( True )
            
        
        return note_import_options
        
    
    def _GetDefaultTagImportOptions( self, url_class ):
        
        url_class_key = url_class.GetClassKey()
        
        if url_class_key in self._url_class_keys_to_tag_import_options:
            
            tag_import_options = self._url_class_keys_to_tag_import_options[ url_class_key ]
            
        else:
            
            url_type = url_class.GetURLType()
            
            if url_type == HC.URL_TYPE_WATCHABLE:
                
                tag_import_options = self._watchable_default_import_options_button.GetTagImportOptions()
                
            else:
                
                tag_import_options = self._file_post_default_import_options_button.GetTagImportOptions()
                
            
            tag_import_options = tag_import_options.Duplicate()
            
            tag_import_options.SetIsDefault( True )
            
        
        return tag_import_options
        
    
    def _OnlyOneNIOSelected( self ):
        
        selected = self._list_ctrl.GetData( only_selected = True )
        
        if len( selected ) == 1:
            
            url_class = selected[0]
            
            url_class_key = url_class.GetClassKey()
            
            if url_class_key in self._url_class_keys_to_note_import_options:
                
                return True
                
            
        
        return False
        
    
    def _OnlyOneTIOSelected( self ):
        
        selected = self._list_ctrl.GetData( only_selected = True )
        
        if len( selected ) == 1:
            
            url_class = selected[0]
            
            url_class_key = url_class.GetClassKey()
            
            if url_class_key in self._url_class_keys_to_tag_import_options:
                
                return True
                
            
        
        return False
        
    
    def _Paste( self ):
        
        try:
            
            raw_text = CG.client_controller.GetClipboardText()
            
        except HydrusExceptions.DataMissing as e:
            
            ClientGUIDialogsMessage.ShowCritical( self, 'Problem pasting!', str(e) )
            
            return
            
        
        try:
            
            unknown_import_options = HydrusSerialisable.CreateFromString( raw_text )
            
            if isinstance( unknown_import_options, TagImportOptions.TagImportOptions ):
                
                insert_dict = self._url_class_keys_to_tag_import_options
                
            elif isinstance( unknown_import_options, NoteImportOptions.NoteImportOptions ):
                
                insert_dict = self._url_class_keys_to_note_import_options
                
            else:
                
                raise Exception( 'Not a Tag or Note Import Options!' )
                
            
            for url_class in self._list_ctrl.GetData( only_selected = True ):
                
                url_class_key = url_class.GetClassKey()
                
                insert_dict[ url_class_key ] = unknown_import_options.Duplicate()
                
            
            self._list_ctrl.UpdateDatas()
            
        except Exception as e:
            
            ClientGUIDialogsQuick.PresentClipboardParseError( self, raw_text, 'An instance of JSON-serialised tag or note import options', e )
            
        
    
    def GetValue( self ):
        
        file_post_default_tag_import_options = self._file_post_default_import_options_button.GetTagImportOptions()
        watchable_default_tag_import_options = self._watchable_default_import_options_button.GetTagImportOptions()
        
        file_post_default_note_import_options = self._file_post_default_import_options_button.GetNoteImportOptions()
        watchable_default_note_import_options = self._watchable_default_import_options_button.GetNoteImportOptions()
        
        return (
            file_post_default_tag_import_options,
            watchable_default_tag_import_options,
            self._url_class_keys_to_tag_import_options,
            file_post_default_note_import_options,
            watchable_default_note_import_options,
            self._url_class_keys_to_note_import_options
        )
        
    
class EditDeleteFilesPanel( ClientGUIScrolledPanels.EditPanel ):
    
    SPECIAL_CHOICE_CUSTOM = 0
    SPECIAL_CHOICE_NO_REASON = 1
    
    def __init__( self, parent: QW.QWidget, media, default_reason, suggested_file_service_key = None ):
        
        super().__init__( parent )
        
        self._default_reason = default_reason
        
        local_file_service_domains = list( CG.client_controller.services_manager.GetServices( ( HC.LOCAL_FILE_DOMAIN, ) ) )
        
        if suggested_file_service_key is None:
            
            suggested_file_service_key = local_file_service_domains[0].GetServiceKey()
            
        
        self._media = ClientMedia.FlattenMedia( media )
        
        self._question_is_already_resolved = len( self._media ) == 0
        
        ( self._all_files_have_existing_file_deletion_reasons, self._existing_shared_file_deletion_reason ) = self._GetExistingSharedFileDeletionReason()
        
        self._simple_description = ClientGUICommon.BetterStaticText( self, label = 'init' )
        
        self._num_actionable_local_file_service_domains = 0
        self._permitted_action_choices = []
        self._this_dialog_includes_service_keys = False
        
        self._InitialisePermittedActionChoices()
        
        self._action_radio = ClientGUICommon.BetterRadioBox( self, self._permitted_action_choices, vertical = True )
        
        self._action_radio.Select( 0 )
        
        selection_success = False
        
        if CG.client_controller.new_options.GetBoolean( 'remember_last_advanced_file_deletion_special_action' ):
            
            last_advanced_file_deletion_special_action = CG.client_controller.new_options.GetNoneableString( 'last_advanced_file_deletion_special_action' )
            
            selection_success = self._TryToSelectAction( last_advanced_file_deletion_special_action )
            
        
        if not selection_success:
            
            self._TryToSelectAction( suggested_file_service_key )
            
        
        self._reason_panel = ClientGUICommon.StaticBox( self, 'reason' )
        
        existing_reason_is_in_list = False
        last_advanced_file_deletion_reason_is_in_list = False
        
        permitted_reason_choices = []
        
        forced_existing_reason_selection_index = None
        
        advanced_file_deletion_reasons = CG.client_controller.new_options.GetStringList( 'advanced_file_deletion_reasons' )
        
        general_selection_index = 0 # default, top row
        
        if default_reason not in advanced_file_deletion_reasons:
            
            if self._existing_shared_file_deletion_reason is not None and self._existing_shared_file_deletion_reason == default_reason:
                
                if not existing_reason_is_in_list:
                    
                    existing_reason_is_in_list = True
                    
                    permitted_reason_choices.append( ( 'keep existing reason: {}'.format( default_reason ), default_reason ) )
                    
                    forced_existing_reason_selection_index = len( permitted_reason_choices ) - 1
                    
                
            else:
                
                permitted_reason_choices.append( ( default_reason, default_reason ) )
                
            
        
        if CG.client_controller.new_options.GetBoolean( 'remember_last_advanced_file_deletion_reason' ):
            
            last_advanced_file_deletion_reason = CG.client_controller.new_options.GetNoneableString( 'last_advanced_file_deletion_reason' )
            
        else:
            
            last_advanced_file_deletion_reason = None
            
        
        for ( i, s ) in enumerate( advanced_file_deletion_reasons ):
            
            if self._existing_shared_file_deletion_reason is not None and self._existing_shared_file_deletion_reason == s:
                
                if not existing_reason_is_in_list:
                    
                    existing_reason_is_in_list = True
                    
                    permitted_reason_choices.append( ( 'keep existing reason: {}'.format( s ), s ) )
                    
                    forced_existing_reason_selection_index = len( permitted_reason_choices ) - 1
                    
                
            else:
                
                permitted_reason_choices.append( ( s, s ) )
                
            
            if last_advanced_file_deletion_reason is None and default_reason == s:
                
                general_selection_index = len( permitted_reason_choices ) - 1
                
            
            if last_advanced_file_deletion_reason is not None and last_advanced_file_deletion_reason == s:
                
                if not last_advanced_file_deletion_reason_is_in_list:
                    
                    last_advanced_file_deletion_reason_is_in_list = True
                    
                    general_selection_index = len( permitted_reason_choices ) - 1
                    
                
            
        
        permitted_reason_choices.append( ( 'custom', self.SPECIAL_CHOICE_CUSTOM ) )
        
        custom_input_index = len( permitted_reason_choices ) - 1
        
        if self._existing_shared_file_deletion_reason is not None and not existing_reason_is_in_list:
            
            permitted_reason_choices.append( ( 'keep existing reason: {}'.format( self._existing_shared_file_deletion_reason ), self._existing_shared_file_deletion_reason ) )
            
            existing_reason_is_in_list = True
            
            forced_existing_reason_selection_index = len( permitted_reason_choices ) - 1
            
        
        if self._all_files_have_existing_file_deletion_reasons and self._existing_shared_file_deletion_reason is None:
            
            existing_reason_is_in_list = True
            
            permitted_reason_choices.append( ( '(all files have existing file deletion reasons and they differ): do not alter them.', self.SPECIAL_CHOICE_NO_REASON ) )
            
            forced_existing_reason_selection_index = len( permitted_reason_choices ) - 1
            
        
        self._reason_radio = ClientGUICommon.BetterRadioBox( self._reason_panel, permitted_reason_choices, vertical = True )
        
        self._custom_reason = QW.QLineEdit( self._reason_panel )
        
        if last_advanced_file_deletion_reason is not None and not last_advanced_file_deletion_reason_is_in_list:
            
            last_advanced_file_deletion_reason_is_in_list = True
            
            self._custom_reason.setText( last_advanced_file_deletion_reason )
            
            general_selection_index = custom_input_index
            
        
        if forced_existing_reason_selection_index is not None:
            
            selection_index_to_make = forced_existing_reason_selection_index
            
        else:
            
            selection_index_to_make = general_selection_index
            
        
        self._reason_radio.Select( selection_index_to_make )
        
        #
        
        ( file_service_key, content_update_packages, save_reason, hashes_physically_deleted, description ) = self._action_radio.GetValue()
        
        self._simple_description.setText( description )
        
        if len( self._permitted_action_choices ) == 1:
            
            self._action_radio.hide()
            self._action_radio.setEnabled( False )
            
        else:
            
            self._simple_description.hide()
            
        
        if not CG.client_controller.new_options.GetBoolean( 'use_advanced_file_deletion_dialog' ):
            
            self._reason_panel.hide()
            self._reason_panel.setEnabled( False )
            
        
        self._action_radio.radioBoxChanged.connect( self._UpdateControls )
        self._reason_radio.radioBoxChanged.connect( self._UpdateControls )
        
        self._UpdateControls()
        
        #
        
        self._reason_panel.Add( self._reason_radio, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        rows = []
        
        rows.append( ( 'custom reason: ', self._custom_reason ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._reason_panel, rows )
        
        self._reason_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._simple_description, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._action_radio, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._reason_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.addStretch( 0 )
        
        self.widget().setLayout( vbox )
        
        CG.client_controller.CallAfterQtSafe( self, self._SetFocus )
        
    
    def _GetExistingSharedFileDeletionReason( self ):
        
        all_files_have_existing_file_deletion_reasons = True
        reasons = set()
        
        for m in self._media:
            
            lm = m.GetLocationsManager()
            
            if not lm.HasLocalFileDeletionReason():
                
                all_files_have_existing_file_deletion_reasons = False
                
                return ( all_files_have_existing_file_deletion_reasons, None )
                
            
            reason = lm.GetLocalFileDeletionReason()
            
            reasons.add( reason )
            
        
        shared_reason = None
        
        if all_files_have_existing_file_deletion_reasons and len( reasons ) == 1:
            
            shared_reason = list( reasons )[0]
            
        
        return ( all_files_have_existing_file_deletion_reasons, shared_reason )
        
    
    def _GetReason( self ):
        
        if self._reason_panel.isEnabled():
            
            reason = self._reason_radio.GetValue()
            
            if reason == self.SPECIAL_CHOICE_CUSTOM:
                
                reason = self._custom_reason.text()
                
            elif reason == self.SPECIAL_CHOICE_NO_REASON:
                
                reason = None
                
            
        else:
            
            if self._all_files_have_existing_file_deletion_reasons or self._existing_shared_file_deletion_reason is not None:
                
                # do not overwrite
                reason = None
                
            else:
                
                reason = self._default_reason
                
            
        
        return reason
        
    
    def _InitialisePermittedActionChoices( self ):
        
        we_are_advanced_delete_dialog = CG.client_controller.new_options.GetBoolean( 'use_advanced_file_deletion_dialog' )
        
        possible_file_service_keys = []
        
        local_file_service_domains = list( CG.client_controller.services_manager.GetServices( ( HC.LOCAL_FILE_DOMAIN, ) ) )
        local_file_service_domain_keys = { service.GetServiceKey() for service in local_file_service_domains }
        
        possible_file_service_keys.extend( ( ( lfs.GetServiceKey(), lfs.GetServiceKey() ) for lfs in local_file_service_domains ) )
        
        possible_file_service_keys.append( ( CC.TRASH_SERVICE_KEY, CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY ) )
        
        if we_are_advanced_delete_dialog:
            
            possible_file_service_keys.append( ( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY ) )
            
        else:
            
            # if not advanced, we still want regular users, in odd fixing situations, able to delete update files
            possible_file_service_keys.append( ( CC.LOCAL_UPDATE_SERVICE_KEY, CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY ) )
            
        
        possible_file_service_keys.extend( ( ( rfs.GetServiceKey(), rfs.GetServiceKey() ) for rfs in CG.client_controller.services_manager.GetServices( ( HC.FILE_REPOSITORY, ) ) ) )
        
        def PhysicalDeleteLockOK( s_k: bytes, media_result: ClientMediaResult.MediaResult ):
            
            if s_k in ( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, CC.TRASH_SERVICE_KEY ):
                
                return not media_result.IsPhysicalDeleteLocked()
                
            
            return True
            
        
        keys_to_hashes = { ( selection_file_service_key, deletee_file_service_key ) : [ m.GetHash() for m in self._media if selection_file_service_key in m.GetLocationsManager().GetCurrent() if PhysicalDeleteLockOK( deletee_file_service_key, m.GetMediaResult() ) ] for ( selection_file_service_key, deletee_file_service_key ) in possible_file_service_keys }
        
        trashed_key = ( CC.TRASH_SERVICE_KEY, CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY )
        combined_key = ( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY )
        
        if trashed_key in keys_to_hashes and combined_key in keys_to_hashes and keys_to_hashes[ trashed_key ] == keys_to_hashes[ combined_key ]:
            
            del keys_to_hashes[ combined_key ]
            
        
        possible_file_service_keys_and_hashes = [ ( fsk, keys_to_hashes[ fsk ] ) for fsk in possible_file_service_keys if fsk in keys_to_hashes and len( keys_to_hashes[ fsk ] ) > 0 ]
        
        self._num_actionable_local_file_service_domains = len( local_file_service_domain_keys.intersection( ( fsk[0] for ( fsk, hashes ) in possible_file_service_keys_and_hashes ) ) )
        
        possibilities_involve_spicy_physical_delete = False
        
        num_local_services_done = 0
        
        for ( fsk, hashes ) in possible_file_service_keys_and_hashes:
            
            if len( hashes ) == 0:
                
                continue
                
            
            num_to_delete = len( hashes )
            
            ( selection_file_service_key, deletee_file_service_key ) = fsk
            
            deletee_service = CG.client_controller.services_manager.GetService( deletee_file_service_key )
            
            deletee_service_type = deletee_service.GetServiceType()
            
            if deletee_service_type == HC.LOCAL_FILE_DOMAIN:
                
                self._this_dialog_includes_service_keys = True
                
                if num_to_delete == 1:
                    
                    file_desc = 'one file'
                    
                else:
                    
                    file_desc = '{} files'.format( HydrusNumbers.ToHumanInt( num_to_delete ) )
                    
                
                if self._num_actionable_local_file_service_domains == 1:
                    
                    template = 'Send {} from {} to trash?'
                    
                else:
                    
                    template = 'Remove {} from {}?'
                    
                
                text = template.format( file_desc, deletee_service.GetName() )
                
                content_updates = [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, chunk_of_hashes ) for chunk_of_hashes in HydrusLists.SplitListIntoChunks( hashes, 16 ) ]
                
                content_update_packages = [ ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( deletee_file_service_key, content_update ) for content_update in content_updates ]
                
                save_reason = True
                
                hashes_physically_deleted = []
                
                num_local_services_done += 1
                
                # this is an ugly place to put this, and the mickey-mouse append, but it works
                if self._num_actionable_local_file_service_domains > 1 and num_local_services_done == self._num_actionable_local_file_service_domains:
                    
                    self._permitted_action_choices.append( ( text, ( deletee_file_service_key, content_update_packages, save_reason, hashes_physically_deleted, text ) ) )
                    
                    deletee_file_service_key = CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY
                    
                    h = [ m.GetHash() for m in self._media if CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY in m.GetLocationsManager().GetCurrent() ]
                    
                    content_updates = [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, chunk_of_hashes ) for chunk_of_hashes in HydrusLists.SplitListIntoChunks( h, 16 ) ]
                    
                    content_update_packages = [ ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( deletee_file_service_key, content_update ) for content_update in content_updates ]
                    
                    text = 'Delete from all local services? (force send to trash)'
                    
                    save_reason = True
                    
                    hashes_physically_deleted = []
                    
                
            elif deletee_service_type == HC.FILE_REPOSITORY:
                
                if deletee_service.HasPermission( HC.CONTENT_TYPE_FILES, HC.PERMISSION_ACTION_PETITION ):
                    
                    self._this_dialog_includes_service_keys = True
                    
                    if num_to_delete == 1:
                        
                        file_desc = 'one file'
                        
                    else:
                        
                        file_desc = '{} files'.format( HydrusNumbers.ToHumanInt( num_to_delete ) )
                        
                    
                    if deletee_service.HasPermission( HC.CONTENT_TYPE_FILES, HC.PERMISSION_ACTION_MODERATE ):
                        
                        text = 'Admin-delete {} from {}?'.format( file_desc, deletee_service.GetName() )
                        
                        save_reason = False
                        reason = 'admin'
                        
                    else:
                        
                        text = 'Petition {} from {}?'.format( file_desc, deletee_service.GetName() )
                        
                        save_reason = True
                        reason = None
                        
                    
                    content_updates = [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_PETITION, hashes, reason = reason ) ]
                    
                    content_update_packages = [ ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( deletee_file_service_key, content_updates ) ]
                    
                    hashes_physically_deleted = []
                    
                
            elif deletee_file_service_key == CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY:
                
                possibilities_involve_spicy_physical_delete = True
                
                # do a physical delete now, skipping or force-removing from trash
                
                deletee_file_service_key = 'physical_delete'
                
                if selection_file_service_key == CC.TRASH_SERVICE_KEY:
                    
                    suffix = 'trashed '
                    
                else:
                    
                    suffix = ''
                    
                
                if num_to_delete == 1:
                    
                    suffix = 'one {}file'.format( suffix )
                    
                else:
                    
                    suffix = '{} {}files'.format( HydrusNumbers.ToHumanInt( num_to_delete ), suffix )
                    
                
                text = 'Permanently delete {}?'.format( suffix )
                
                content_updates = [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, chunk_of_hashes ) for chunk_of_hashes in HydrusLists.SplitListIntoChunks( hashes, 16 ) ]
                
                content_update_packages = [ ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, content_update ) for content_update in content_updates ]
                
                save_reason = True
                
                hashes_physically_deleted = hashes
                
            
            self._permitted_action_choices.append( ( text, ( deletee_file_service_key, content_update_packages, save_reason, hashes_physically_deleted, text ) ) )
            
        
        unnatural_spicy_physical_delete = possibilities_involve_spicy_physical_delete and not we_are_advanced_delete_dialog
        
        if self._num_actionable_local_file_service_domains == 1 and not unnatural_spicy_physical_delete and not HC.options[ 'confirm_trash' ]:
            
            # this dialog will never show
            self._question_is_already_resolved = True
            
        
        if CG.client_controller.new_options.GetBoolean( 'use_advanced_file_deletion_dialog' ):
            
            hashes = [ m.GetHash() for m in self._media if CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY in m.GetLocationsManager().GetCurrent() if PhysicalDeleteLockOK( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, m.GetMediaResult() ) ]
            
            num_to_delete = len( hashes )
            
            if num_to_delete > 0:
                
                if num_to_delete == 1:
                    
                    text = 'Permanently delete this file and do not save a deletion record?'
                    
                else:
                    
                    text = 'Permanently delete these ' + HydrusNumbers.ToHumanInt( num_to_delete ) + ' files and do not save a deletion record?'
                    
                
                chunks_of_hashes = list( HydrusLists.SplitListIntoChunks( hashes, 16 ) ) # iterator, so list it to use it more than once, jej
                
                content_update_packages = []
                
                content_updates = [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, chunk_of_hashes ) for chunk_of_hashes in chunks_of_hashes ]
                
                content_update_packages.extend( [ ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, content_update ) for content_update in content_updates ] )
                
                content_updates = [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_CLEAR_DELETE_RECORD, chunk_of_hashes ) for chunk_of_hashes in chunks_of_hashes ]
                
                content_update_packages.extend( [ ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, content_update ) for content_update in content_updates ] )
                
                save_reason = False
                
                hashes_physically_deleted = hashes
                
                self._permitted_action_choices.append( ( text, ( 'clear_delete', content_update_packages, save_reason, hashes_physically_deleted, text ) ) )
                
            
        
        if len( self._permitted_action_choices ) == 0:
            
            raise HydrusExceptions.CancelledException( 'No valid delete choices!' )
            
        
    
    def _SetFocus( self ):
        
        if self._action_radio.isEnabled():
            
            self._action_radio.setFocus( QC.Qt.FocusReason.OtherFocusReason )
            
        elif self._reason_panel.isEnabled():
            
            self._reason_radio.setFocus( QC.Qt.FocusReason.OtherFocusReason )
            
        
    
    def _TryToSelectAction( self, action ) -> bool:
        
        if action is None:
            
            return False
            
        
        # this is a mess since action could be 'clear_delete' or a file service key
        
        if isinstance( action, bytes ):
            
            action = action.hex()
            
        
        for ( i, choice ) in enumerate( self._permitted_action_choices ):
            
            deletee_file_service_key = choice[1][0]
            
            if isinstance( deletee_file_service_key, bytes ):
                
                comparison_text = deletee_file_service_key.hex()
                
            else:
                
                comparison_text = deletee_file_service_key
                
            
            if comparison_text == action:
                
                self._action_radio.Select( i )
                
                return True
                
            
        
        return False
        
    
    def _UpdateControls( self ):
        
        ( file_service_key, content_update_packages, save_reason, hashes_physically_deleted, description ) = self._action_radio.GetValue()
        
        reason_permitted = save_reason
        
        if reason_permitted:
            
            self._reason_panel.setEnabled( True )
            
            reason = self._reason_radio.GetValue()
            
            if reason == self.SPECIAL_CHOICE_CUSTOM:
                
                self._custom_reason.setEnabled( True )
                
            else:
                
                self._custom_reason.setEnabled( False )
                
            
        else:
            
            self._reason_panel.setEnabled( False )
            
        
    
    def GetValue( self ):
        
        if len( self._permitted_action_choices ) == 0 or len( self._media ) == 0:
            
            return ( False, [] )
            
        
        ( file_service_key, content_update_packages, save_reason, hashes_physically_deleted, description ) = self._action_radio.GetValue()
        
        if save_reason:
            
            reason = self._GetReason()
            
            for content_update_package in content_update_packages:
                
                for ( service_key, content_updates ) in content_update_package.IterateContentUpdates():
                    
                    for content_update in content_updates:
                        
                        content_update.SetReason( reason )
                        
                    
                
            
        
        save_action = True
        
        if isinstance( file_service_key, bytes ):
            
            last_advanced_file_deletion_special_action = file_service_key.hex()
            
        else:
            
            previous_last_advanced_file_deletion_special_action = CG.client_controller.new_options.GetNoneableString( 'last_advanced_file_deletion_special_action' )
            
            # if there is nothing to do but physically delete, then we don't want to overwrite an existing 'use service' setting
            # HACKMODE ALERT. len() == 64 is a stupid test for 'looks like a service key mate'
            if ( previous_last_advanced_file_deletion_special_action is None or len( previous_last_advanced_file_deletion_special_action ) == 64 ) and not self._this_dialog_includes_service_keys:
                
                save_action = False
                
            
            last_advanced_file_deletion_special_action = file_service_key
            
        
        if save_action and CG.client_controller.new_options.GetBoolean( 'remember_last_advanced_file_deletion_special_action' ):
            
            CG.client_controller.new_options.SetNoneableString( 'last_advanced_file_deletion_special_action', last_advanced_file_deletion_special_action )
            
        
        if save_reason and CG.client_controller.new_options.GetBoolean( 'remember_last_advanced_file_deletion_reason' ):
            
            reasons_ok = self._reason_radio.isVisible() and self._reason_radio.isEnabled()
            
            user_selected_existing_or_make_no_change = reason == self._existing_shared_file_deletion_reason or reason is None
            
            if reasons_ok and not user_selected_existing_or_make_no_change:
                
                if reason == self._default_reason:
                    
                    last_advanced_file_deletion_reason = None
                    
                else:
                    
                    last_advanced_file_deletion_reason = reason
                    
                
                CG.client_controller.new_options.SetNoneableString( 'last_advanced_file_deletion_reason', last_advanced_file_deletion_reason )
                
            
        
        return ( hashes_physically_deleted, content_update_packages )
        
    
    def QuestionIsAlreadyResolved( self ):
        
        return self._question_is_already_resolved
        
    

class EditFilesForcedFiletypePanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, original_mimes_count: dict[ int, int ], forced_mimes_count: dict[ int, int ] ):
        
        super().__init__( parent )
        
        total_file_count = sum( original_mimes_count.values() )
        total_forced_mimes_count = sum( forced_mimes_count.values() )
        
        self._forced_mime = ClientGUICommon.BetterChoice( self )
        
        if total_forced_mimes_count > 0:
            
            self._forced_mime.addItem( 'remove all forced filetypes', None )
            
        
        do_not_allow_this_mime = None
        
        if len( original_mimes_count.keys() ) == 1:
            
            # we only have one filetype to start with, so don't let user say set to that
            
            do_not_allow_this_mime = list( original_mimes_count.keys() )[0]
            
        
        general_mime_types = [
            HC.GENERAL_IMAGE,
            HC.GENERAL_ANIMATION,
            HC.GENERAL_VIDEO,
            HC.GENERAL_AUDIO,
            HC.GENERAL_APPLICATION,
            HC.GENERAL_IMAGE_PROJECT,
            HC.GENERAL_APPLICATION_ARCHIVE
        ]
        
        mimes_in_order = []
        
        for general_mime_type in general_mime_types:
            
            mimes_in_order.extend( HC.general_mimetypes_to_mime_groups[ general_mime_type ] )
            
        
        mimes_in_order.append( HC.APPLICATION_HYDRUS_UPDATE_DEFINITIONS )
        mimes_in_order.append( HC.APPLICATION_HYDRUS_UPDATE_CONTENT )
        
        for mime in mimes_in_order:
            
            if mime == do_not_allow_this_mime:
                
                continue
                
            
            label = HC.mime_string_lookup[ mime ]
            
            if mime in HC.mimes_to_general_mimetypes:
                
                general_mime = HC.mimes_to_general_mimetypes[ mime ]
                
                label = f'{HC.mime_string_lookup[ general_mime ]} - {label}'
                
            
            self._forced_mime.addItem( label, mime )
            
        
        #
        
        original_filetype_statements = []
        
        for mime in mimes_in_order:
            
            if mime in original_mimes_count:
                
                count = original_mimes_count[ mime ]
                
                original_filetype_statements.append( f'{HydrusNumbers.ToHumanInt(count)} {HC.mime_string_lookup[ mime ]}')
                
            
        
        original_filetype_summary = ', '.join( original_filetype_statements )
        
        if total_forced_mimes_count == 0:
            
            forced_filetype_summary = 'None are currently forced to be anything else.'
            
        else:
            
            forced_filetype_statements = []
            
            for mime in mimes_in_order:
                
                if mime in forced_mimes_count:
                    
                    count = forced_mimes_count[ mime ]
                    
                    forced_filetype_statements.append( f'{HydrusNumbers.ToHumanInt(count)} {HC.mime_string_lookup[ mime ]}')
                    
                
            
            forced_filetype_summary = ', '.join( forced_filetype_statements )
            
            if total_forced_mimes_count == total_file_count:
                
                forced_filetype_summary = f'All are currently being forced: {forced_filetype_summary}.'
                
            else:
                
                forced_filetype_summary = f'{HydrusNumbers.ToHumanInt(total_forced_mimes_count)} are currently being forced, to: {forced_filetype_summary}.'
                
            
        
        vbox = QP.VBoxLayout()
        
        text = 'WARNING: This is advanced and experimental! Be careful!'
        text += '\n\n'
        text += 'This will override what hydrus thinks the filetype is for all of these files. Files will be renamed to receive their new file extensions. The original filetype is not forgotten, and this can be undone.'
        text += '\n\n'
        text += f'Of the {HydrusNumbers.ToHumanInt( total_file_count )} files, there are {original_filetype_summary}. {forced_filetype_summary}'
        
        st = ClientGUICommon.BetterStaticText( self, text )
        st.setWordWrap( True )
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._forced_mime, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.widget().setLayout( vbox )
        
    
    def GetValue( self ):
        
        forced_mime = self._forced_mime.GetValue()
        
        return forced_mime
        
    

class EditFileNotesPanel( CAC.ApplicationCommandProcessorMixin, ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, names_to_notes: dict[ str, str ], name_to_start_on: str | None ):
        
        super().__init__( parent )
        
        self._original_names = set()
        self._original_names_to_notes = dict( names_to_notes )
        
        self._notebook = QW.QTabWidget( self )
        
        ( min_width, min_height ) = ClientGUIFunctions.ConvertTextToPixels( self._notebook, ( 80, 14 ) )
        
        self._notebook.setMinimumSize( min_width, min_height )
        
        self._add_button = ClientGUICommon.BetterButton( self, 'add', self._AddNote )
        self._edit_button = ClientGUICommon.BetterButton( self, 'edit current name', self._EditName )
        self._delete_button = ClientGUICommon.BetterButton( self, 'delete current note', self._DeleteNote )
        
        self._copy_button = ClientGUICommon.IconButton( self, CC.global_icons().copy, self._Copy )
        self._copy_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'Copy all notes to the clipboard.' ) )
        
        self._paste_button = ClientGUICommon.IconButton( self, CC.global_icons().paste, self._Paste )
        self._paste_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'Paste from a copy from another notes dialog.' ) )
        
        #
        
        index_to_select = 0
        
        if len( names_to_notes ) == 0:
            
            self._AddNotePanel( 'notes', '' )
            
        else:
            
            names = sorted( names_to_notes.keys() )
            
            for ( i, name ) in enumerate( names ):
                
                if name == name_to_start_on:
                    
                    index_to_select = i
                    
                
                note = names_to_notes[ name ]
                
                self._original_names.add( name )
                
                self._AddNotePanel( name, note )
                
            
        
        self._notebook.setCurrentIndex( index_to_select )
        
        first_panel = typing.cast( QW.QPlainTextEdit, self._notebook.currentWidget() )
        
        ClientGUIFunctions.SetFocusLater( first_panel )
        
        #
        
        button_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( button_hbox, self._add_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( button_hbox, self._edit_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( button_hbox, self._delete_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( button_hbox, self._copy_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( button_hbox, self._paste_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, button_hbox, CC.FLAGS_ON_RIGHT )
        
        self.widget().setLayout( vbox )
        
        self._my_shortcut_handler = ClientGUIShortcuts.ShortcutsHandler( self, self, [ 'global', 'media' ] )
        
        self._notebook.tabBarDoubleClicked.connect( self._TabBarDoubleClicked )
        self._notebook.currentChanged.connect( self._CurrentNoteChanged )
        
    
    def _AddNote( self ):
        
        ( names_to_notes, deletee_names ) = self.GetValue()
        
        existing_names = set( names_to_notes.keys() )
        
        message = 'Enter the name for the note.'
        
        try:
            
            name = ClientGUIDialogsQuick.EnterText( self, message )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        name = HydrusData.GetNonDupeName( name, existing_names )
        
        self._AddNotePanel( name, '' )
        
    
    def _AddNotePanel( self, name, note ):
        
        control = QW.QPlainTextEdit( self._notebook )
        
        try:
            
            control.setPlainText( note )
            
        except:
            
            control.setPlainText( repr( note ) )
            
        
        self._notebook.addTab( control, name )
        
        self._notebook.setCurrentWidget( control )
        
        ClientGUIFunctions.SetFocusLater( control )
        
        if CG.client_controller.new_options.GetBoolean( 'start_note_editing_at_end' ):
            
            CG.client_controller.CallAfterQtSafe( control, control.moveCursor, QG.QTextCursor.MoveOperation.End )
            
        else:
            
            CG.client_controller.CallAfterQtSafe( control, control.moveCursor, QG.QTextCursor.MoveOperation.Start )
            
        
        self._UpdateButtons()
        
    
    def _Copy( self ):
        
        ( names_to_notes, deletee_names ) = self.GetValue()
        
        text = json.dumps( names_to_notes )
        
        CG.client_controller.pub( 'clipboard', 'text', text )
        
    
    def _CurrentNoteChanged( self ):
        
        if self._notebook.count() > 0:
            
            ClientGUIFunctions.SetFocusLater( self._notebook.currentWidget() )
            
        
    
    def _Paste( self ):
        
        try:
            
            raw_text = CG.client_controller.GetClipboardText()
            
        except HydrusExceptions.DataMissing as e:
            
            ClientGUIDialogsMessage.ShowCritical( self, 'Problem pasting!', str(e) )
            
            return
            
        
        try:
            
            names_and_notes = json.loads( raw_text )
            
            clean_names_and_notes = []
            
            if isinstance( names_and_notes, dict ):
                
                names_and_notes = list( names_and_notes.items() )
                
            
            for item in names_and_notes:
                
                if not HydrusLists.IsAListLikeCollection( item ):
                    
                    continue
                    
                
                if len( item ) != 2:
                    
                    raise Exception( 'Not a two-tuple!' )
                    

                ( key, value ) = item
                
                if not isinstance( key, str ):
                    
                    raise Exception( 'Key not a string!' )
                    
                
                if not isinstance( value, str ):
                    
                    raise Exception( 'Value not a string!' )
                    
                
                clean_names_and_notes.append( item )
                
            
            names_and_notes = clean_names_and_notes
            
        except Exception as e:
            
            ClientGUIDialogsQuick.PresentClipboardParseError( self, raw_text, 'JSON names and notes, either as an Object or a list of pairs', e )
            
            return
            
        
        ( existing_names_to_notes, deletee_names ) = self.GetValue()
        
        note_import_options = NoteImportOptions.NoteImportOptions()
        
        note_import_options.SetIsDefault( False )
        note_import_options.SetExtendExistingNoteIfPossible( True )
        note_import_options.SetConflictResolution( NoteImportOptions.NOTE_IMPORT_CONFLICT_RENAME )
        
        new_names_to_notes = note_import_options.GetUpdateeNamesToNotes( existing_names_to_notes, names_and_notes )
        
        existing_panel_names_to_widgets = { self._notebook.tabText( i ) : self._notebook.widget( i ) for i in range( self._notebook.count() ) }
        
        for ( name, note ) in new_names_to_notes.items():
            
            if name in existing_panel_names_to_widgets:
                
                control = typing.cast( QW.QPlainTextEdit, existing_panel_names_to_widgets[ name ] )
                
                try:
                    
                    control.setPlainText( note )
                    
                except:
                    
                    control.setPlainText( repr( note ) )
                    
                
            else:
                
                self._AddNotePanel( name, note )
                
            
        
    
    def _DeleteNote( self ):
        
        text = 'Delete this note?'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, text )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            index = self._notebook.currentIndex()
            
            panel = self._notebook.currentWidget()
            
            self._notebook.removeTab( index )
            
            panel.deleteLater()
            
            self._UpdateButtons()
            
        
    
    def _EditName( self, index = None ):
        
        if index is None:
            
            index = self._notebook.currentIndex()
            
        
        name = self._notebook.tabText( index )
        
        ( names_to_notes, deletee_names ) = self.GetValue()
        
        existing_names = set( names_to_notes.keys() )
        
        existing_names.discard( name )
        
        message = 'Enter the name for the note.'
        
        try:
            
            name = ClientGUIDialogsQuick.EnterText( self, message, default = name )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        name = HydrusData.GetNonDupeName( name, existing_names )
        
        self._notebook.setTabText( index, name )
        
    
    def _TabBarDoubleClicked( self, index: int ):
        
        if index == -1:
            
            self._AddNote()
            
        else:
            
            self._EditName( index = index )
            
        
    
    def _UpdateButtons( self ):
        
        can_edit = self._notebook.count() > 0
        
        self._edit_button.setEnabled( can_edit )
        self._delete_button.setEnabled( can_edit )
        
    
    def GetValue( self ) -> tuple[ dict[ str, str ], set[ str ] ]:
        
        names_to_notes = { self._notebook.tabText( i ) : HydrusText.CleanNoteText( typing.cast( QW.QPlainTextEdit, self._notebook.widget( i ) ).toPlainText() ) for i in range( self._notebook.count() ) }
        
        names_to_notes = { name : text for ( name, text ) in names_to_notes.items() if text != '' }
        
        deletee_names = { name for name in self._original_names if name not in names_to_notes }
        
        return ( names_to_notes, deletee_names )
        
    
    def ProcessApplicationCommand( self, command: CAC.ApplicationCommand ):
        
        command_processed = True
        
        if command.IsSimpleCommand():
            
            action = command.GetSimpleAction()
            
            if action == CAC.SIMPLE_MANAGE_FILE_NOTES:
                
                self._OKParent()
                
            else:
                
                command_processed = False
                
            
        else:
            
            command_processed = False
            
        
        return command_processed
        
    
    def UserIsOKToCancel( self ):
        
        ( names_to_notes, deletee_names ) = self.GetValue()
        
        if names_to_notes != self._original_names_to_notes:
            
            message = 'It looks like you have made changes--are you sure you want to cancel?'
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message )
            
            if result != QW.QDialog.DialogCode.Accepted:
                
                return False
                
            
        
        return True
        
    
    def UserIsOKToOK( self ):
        
        ( names_to_notes, deletee_names ) = self.GetValue()
        
        empty_note_names = sorted( ( name for ( name, note ) in names_to_notes.items() if note == '' ) )
        
        if len( empty_note_names ) > 0:
            
            message = 'These notes are empty, and will not be saved--is this ok?'
            message += '\n' * 2
            message += ', '.join( empty_note_names )
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message )
            
            if result != QW.QDialog.DialogCode.Accepted:
                
                return False
                
            
        
        return True
        
    

class EditFrameLocationPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, info ):
        
        super().__init__( parent )
        
        self._original_info = info
        
        self._remember_size = QW.QCheckBox( 'remember size', self )
        self._remember_position = QW.QCheckBox( 'remember position', self )
        
        self._last_size = ClientGUICommon.NoneableDoubleSpinCtrl( self, ( 640, 480 ),'last size', none_phrase = 'none set', min = 100, max = 1000000, unit = None )
        self._last_position = ClientGUICommon.NoneableDoubleSpinCtrl( self, ( 20, 20 ),'last position', none_phrase = 'none set', min = -1000000, max = 1000000, unit = None )
        
        self._default_gravity_x = ClientGUICommon.BetterChoice( self )
        
        self._default_gravity_x.addItem( 'by default, expand to width of parent', 1 )
        self._default_gravity_x.addItem( 'by default, expand width as much as needed', -1 )
        
        self._default_gravity_y = ClientGUICommon.BetterChoice( self )
        
        self._default_gravity_y.addItem( 'by default, expand to height of parent', 1 )
        self._default_gravity_y.addItem( 'by default, expand height as much as needed', -1 )
        
        self._default_position = ClientGUICommon.BetterChoice( self )
        
        self._default_position.addItem( 'by default, position off the top-left corner of parent', 'topleft')
        self._default_position.addItem( 'by default, position centered on the parent', 'center')
        
        self._maximised = QW.QCheckBox( 'start maximised', self )
        self._fullscreen = QW.QCheckBox( 'start fullscreen', self )
        
        #
        
        ( name, remember_size, remember_position, last_size, last_position, default_gravity, default_position, maximised, fullscreen ) = self._original_info
        
        self._remember_size.setChecked( remember_size )
        self._remember_position.setChecked( remember_position )
        
        self._last_size.SetValue( last_size )
        self._last_position.SetValue( last_position )
        
        ( x, y ) = default_gravity
        
        self._default_gravity_x.SetValue( x )
        self._default_gravity_y.SetValue( y )
        
        self._default_position.SetValue( default_position )
        
        self._maximised.setChecked( maximised )
        self._fullscreen.setChecked( fullscreen )
        
        #
        
        vbox = QP.VBoxLayout()
        
        text = 'Setting frame location info for ' + name + '.'
        
        if name == 'manage_tags_dialog':
            
            text += '\n\nThis is the manage tags dialog launched off the thumbnail grid.'
            
        elif name == 'manage_tags_frame':
            
            text += '\n\nThis is the manage tags dialog launched off the media viewer.'
            
        
        QP.AddToLayout( vbox, ClientGUICommon.BetterStaticText(self,text), CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._remember_size, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._remember_position, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._last_size, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._last_position, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._default_gravity_x, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._default_gravity_y, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._default_position, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._maximised, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._fullscreen, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.widget().setLayout( vbox )
        
    
    def GetValue( self ):
        
        ( name, remember_size, remember_position, last_size, last_position, default_gravity, default_position, maximised, fullscreen ) = self._original_info
        
        remember_size = self._remember_size.isChecked()
        remember_position = self._remember_position.isChecked()
        
        last_size = self._last_size.GetValue()
        last_position = self._last_position.GetValue()
        
        x = self._default_gravity_x.GetValue()
        y = self._default_gravity_y.GetValue()
        
        default_gravity = ( x, y )
        
        default_position = self._default_position.GetValue()
        
        maximised = self._maximised.isChecked()
        fullscreen = self._fullscreen.isChecked()
        
        return ( name, remember_size, remember_position, last_size, last_position, default_gravity, default_position, maximised, fullscreen )
        
    

class EditMediaViewOptionsPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, info ):
        
        super().__init__( parent )
        
        self._original_info = info
        
        ( self._mime, media_show_action, media_start_paused, media_start_with_embed, preview_show_action, preview_start_paused, preview_start_with_embed, ( media_scale_up, media_scale_down, preview_scale_up, preview_scale_down, exact_zooms_only, scale_up_quality, scale_down_quality ) ) = self._original_info
        
        ( possible_show_actions, can_start_paused, can_start_with_embed ) = CC.media_viewer_capabilities[ self._mime ]
        
        self._media_show_action = ClientGUICommon.BetterChoice( self )
        self._media_start_paused = QW.QCheckBox( self )
        self._media_start_with_embed = QW.QCheckBox( self )
        self._preview_show_action = ClientGUICommon.BetterChoice( self )
        self._preview_start_paused = QW.QCheckBox( self )
        self._preview_start_with_embed = QW.QCheckBox( self )
        
        advanced_mode = CG.client_controller.new_options.GetBoolean( 'advanced_mode' )
        
        for action in possible_show_actions:
            
            if action == CC.MEDIA_VIEWER_ACTION_SHOW_WITH_MPV and not ClientGUIMPV.MPV_IS_AVAILABLE:
                
                continue
                
            
            simple_mode = not advanced_mode
            not_source = not HC.RUNNING_FROM_SOURCE
            not_qt_6 = not QtInit.WE_ARE_QT6
            
            if action == CC.MEDIA_VIEWER_ACTION_SHOW_WITH_QMEDIAPLAYER and ( simple_mode or not_source or not_qt_6 ):
                
                continue
                
            
            s = CC.media_viewer_action_string_lookup[ action ]
            
            if action == CC.MEDIA_VIEWER_ACTION_SHOW_WITH_NATIVE and self._mime in [ HC.GENERAL_VIDEO ] + list( HC.VIDEO ):
                
                s += ' (no audio support)'
                
            
            self._media_show_action.addItem( s, action )
            
            if action != CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW_ON_ACTIVATION_OPEN_EXTERNALLY:
                
                self._preview_show_action.addItem( s, action )
                
            
        
        self._media_show_action.currentIndexChanged.connect( self.EventActionChange )
        self._preview_show_action.currentIndexChanged.connect( self.EventActionChange )
        
        self._media_scale_up = ClientGUICommon.BetterChoice( self )
        self._media_scale_down = ClientGUICommon.BetterChoice( self )
        self._preview_scale_up = ClientGUICommon.BetterChoice( self )
        self._preview_scale_down = ClientGUICommon.BetterChoice( self )
        
        for scale_action in ( CC.MEDIA_VIEWER_SCALE_100, CC.MEDIA_VIEWER_SCALE_MAX_REGULAR, CC.MEDIA_VIEWER_SCALE_TO_CANVAS ):
            
            text = CC.media_viewer_scale_string_lookup[ scale_action ]
            
            self._media_scale_up.addItem( text, scale_action )
            self._preview_scale_up.addItem( text, scale_action )
            
            self._media_scale_down.addItem( text, scale_action )
            self._preview_scale_down.addItem( text, scale_action )
            
        
        self._exact_zooms_only = QW.QCheckBox( self )
        self._exact_zooms_only.setToolTip( ClientGUIFunctions.WrapToolTip( 'This limits zooms to 25%, 50%, 100%, 200%, 400%, and so on. It makes for fast resize and is useful for files that often have flat colours and hard edges, which often scale badly otherwise. The \'canvas fit\' zoom will still be inserted.' ) )
        
        self._scale_up_quality = ClientGUICommon.BetterChoice( self )
        
        for zoom in ( CC.ZOOM_NEAREST, CC.ZOOM_LINEAR, CC.ZOOM_CUBIC, CC.ZOOM_LANCZOS4 ):
            
            self._scale_up_quality.addItem( CC.zoom_string_lookup[ zoom], zoom )
            
        
        self._scale_down_quality = ClientGUICommon.BetterChoice( self )
        
        for zoom in ( CC.ZOOM_NEAREST, CC.ZOOM_LINEAR, CC.ZOOM_AREA ):
            
            self._scale_down_quality.addItem( CC.zoom_string_lookup[ zoom], zoom )
            
        
        #
        
        self._media_show_action.SetValue( media_show_action )
        self._media_start_paused.setChecked( media_start_paused )
        self._media_start_with_embed.setChecked( media_start_with_embed )
        
        self._preview_show_action.SetValue( preview_show_action )
        self._preview_start_paused.setChecked( preview_start_paused )
        self._preview_start_with_embed.setChecked( preview_start_with_embed )
        
        self._media_scale_up.SetValue( media_scale_up )
        self._media_scale_down.SetValue( media_scale_down )
        self._preview_scale_up.SetValue( preview_scale_up )
        self._preview_scale_down.SetValue( preview_scale_down )
        
        self._exact_zooms_only.setChecked( exact_zooms_only )
        
        self._scale_up_quality.SetValue( scale_up_quality )
        self._scale_down_quality.SetValue( scale_down_quality )
        
        #
        
        vbox = QP.VBoxLayout()
        
        text = 'Setting media view options for ' + HC.mime_string_lookup[ self._mime ] + '.'
        
        if not ClientGUIMPV.MPV_IS_AVAILABLE:
            
            text += ' MPV is not available for this client.'
            
        
        QP.AddToLayout( vbox, ClientGUICommon.BetterStaticText(self,text), CC.FLAGS_EXPAND_PERPENDICULAR )
        
        # TODO: Yo this layout sucks, figure out some better dynamic presentation of these options based on mime viewing capability, atm doing enable/disable and weird hide/show here is bad
        
        rows = []
        
        rows.append( ( 'media viewer show action: ', self._media_show_action ) )
        rows.append( ( 'media starts paused: ', self._media_start_paused ) )
        rows.append( ( 'media starts covered with an embed button: ', self._media_start_with_embed ) )
        rows.append( ( 'preview viewer show action: ', self._preview_show_action ) )
        rows.append( ( 'preview starts paused: ', self._preview_start_paused ) )
        rows.append( ( 'preview starts covered with an embed button: ', self._preview_start_with_embed ) )
        
        if set( possible_show_actions ).isdisjoint( { CC.MEDIA_VIEWER_ACTION_SHOW_WITH_NATIVE, CC.MEDIA_VIEWER_ACTION_SHOW_WITH_MPV, CC.MEDIA_VIEWER_ACTION_SHOW_WITH_QMEDIAPLAYER } ):
            
            self._media_scale_up.hide()
            self._media_scale_down.hide()
            self._preview_scale_up.hide()
            self._preview_scale_down.hide()
            
            self._exact_zooms_only.setVisible( False )
            
            self._scale_up_quality.hide()
            self._scale_down_quality.hide()
            
        else:
            
            rows.append( ( 'if the media is smaller than the media viewer canvas: ', self._media_scale_up ) )
            rows.append( ( 'if the media is larger than the media viewer canvas: ', self._media_scale_down ) )
            rows.append( ( 'if the media is smaller than the preview canvas: ', self._preview_scale_up ) )
            rows.append( ( 'if the media is larger than the preview canvas: ', self._preview_scale_down ) )
            rows.append( ( 'only permit half and double zooms', self._exact_zooms_only ) )
            rows.append( ClientGUICommon.BetterStaticText( self, 'Nearest neighbour is fast and ugly, 8x8 lanczos and area resampling are slower but beautiful.' ) )
            rows.append(( '>100% (interpolation) quality: ', self._scale_up_quality ) )
            rows.append(( '<100% (decimation) quality: ', self._scale_down_quality ) )
            
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        if self._mime == HC.APPLICATION_FLASH:
            
            self._scale_up_quality.setEnabled( False )
            self._scale_down_quality.setEnabled( False )
            
        
        vbox.addStretch( 0 )
        
        self.widget().setLayout( vbox )
        
        self._UpdateControls()
        
    
    def _UpdateControls( self ):
        
        media_ok = self._media_show_action.GetValue() not in CC.unsupported_media_actions
        preview_ok = self._preview_show_action.GetValue() not in CC.unsupported_media_actions
        
        if media_ok or preview_ok:
            
            self._exact_zooms_only.setEnabled( True )
            
            self._scale_up_quality.setEnabled( True )
            self._scale_down_quality.setEnabled( True )
            
        else:
            
            self._exact_zooms_only.setEnabled( False )
            
            self._scale_up_quality.setEnabled( False )
            self._scale_down_quality.setEnabled( False )
            
        
        if media_ok:
            
            self._media_scale_up.setEnabled( True )
            self._media_scale_down.setEnabled( True )
            
            self._media_start_paused.setEnabled( True )
            self._media_start_with_embed.setEnabled( True )
            
        else:
            
            self._media_scale_up.setEnabled( False )
            self._media_scale_down.setEnabled( False )
            
            self._media_start_paused.setEnabled( False )
            self._media_start_with_embed.setEnabled( False )
            
        
        if preview_ok:
            
            self._preview_scale_up.setEnabled( True )
            self._preview_scale_down.setEnabled( True )
            
            self._preview_start_paused.setEnabled( True )
            self._preview_start_with_embed.setEnabled( True )
            
        else:
            
            self._preview_scale_up.setEnabled( False )
            self._preview_scale_down.setEnabled( False )
            
            self._preview_start_paused.setEnabled( False )
            self._preview_start_with_embed.setEnabled( False )
            
        
        is_application = self._mime == HC.GENERAL_APPLICATION or self._mime in HC.general_mimetypes_to_mime_groups[ HC.GENERAL_APPLICATION ]
        is_archive = self._mime == HC.GENERAL_APPLICATION_ARCHIVE or self._mime in HC.general_mimetypes_to_mime_groups[ HC.GENERAL_APPLICATION_ARCHIVE ]
        
        # this is the one that is likely to get tricky, with SVG and PSD. maybe we'll move to 'renderable image projects' something
        is_image_project = self._mime == HC.GENERAL_IMAGE_PROJECT or self._mime in HC.general_mimetypes_to_mime_groups[ HC.GENERAL_IMAGE_PROJECT ]
        is_image = self._mime == HC.GENERAL_IMAGE or self._mime in HC.general_mimetypes_to_mime_groups[ HC.GENERAL_IMAGE ]
        is_audio = self._mime == HC.GENERAL_AUDIO or self._mime in HC.general_mimetypes_to_mime_groups[ HC.GENERAL_AUDIO ]
        
        if not is_image:
            
            self._scale_up_quality.setEnabled( False )
            self._scale_down_quality.setEnabled( False )
            
        
        if is_image or is_application or is_archive or is_image_project:
            
            self._media_start_paused.setEnabled( False )
            self._preview_start_paused.setEnabled( False )
            
        
        if is_audio:
            
            self._media_scale_up.setEnabled( False )
            self._media_scale_down.setEnabled( False )
            self._preview_scale_up.setEnabled( False )
            self._preview_scale_down.setEnabled( False )
            
        
    
    def EventActionChange( self, index ):
        
        self._UpdateControls()
        
    
    def GetValue( self ):
        
        media_show_action = self._media_show_action.GetValue()
        media_start_paused = self._media_start_paused.isChecked()
        media_start_with_embed = self._media_start_with_embed.isChecked()
        
        preview_show_action = self._preview_show_action.GetValue()
        preview_start_paused = self._preview_start_paused.isChecked()
        preview_start_with_embed = self._preview_start_with_embed.isChecked()
        
        media_scale_up = self._media_scale_up.GetValue()
        media_scale_down = self._media_scale_down.GetValue()
        preview_scale_up = self._preview_scale_up.GetValue()
        preview_scale_down = self._preview_scale_down.GetValue()
        
        exact_zooms_only = self._exact_zooms_only.isChecked()
        
        scale_up_quality = self._scale_up_quality.GetValue()
        scale_down_quality = self._scale_down_quality.GetValue()
        
        zoom_info = ( media_scale_up, media_scale_down, preview_scale_up, preview_scale_down, exact_zooms_only, scale_up_quality, scale_down_quality )
        
        return ( self._mime, media_show_action, media_start_paused, media_start_with_embed, preview_show_action, preview_start_paused, preview_start_with_embed, zoom_info )
        
    

class EditURLsPanel( CAC.ApplicationCommandProcessorMixin, ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, medias: collections.abc.Collection[ ClientMedia.MediaSingleton ] ):
        
        super().__init__( parent )
        
        self._current_media = [ m.Duplicate() for m in medias ]
        
        self._multiple_files_warning = ClientGUICommon.BetterStaticText( self, label = 'Warning: you are editing urls for multiple files!\nBe very careful about adding URLs here, as they will apply to everything.\nAdding the same URL to multiple files is only appropriate for Post URLs that are set to expect multiple files, or if you really need to associate a Gallery URL.' )
        self._multiple_files_warning.setObjectName( 'HydrusWarning' )
        
        if len( self._current_media ) == 1:
            
            self._multiple_files_warning.hide()
            
        
        self._urls_listbox = ClientGUIListBoxes.BetterQListWidget( self, delete_callable = self.DeleteSelected )
        self._urls_listbox.setSelectionMode( QW.QAbstractItemView.SelectionMode.ExtendedSelection )
        self._urls_listbox.setSortingEnabled( False )
        self._urls_listbox.itemDoubleClicked.connect( self.ListDoubleClicked )
        
        ( width, height ) = ClientGUIFunctions.ConvertTextToPixels( self._urls_listbox, ( 120, 10 ) )
        
        self._urls_listbox.setMinimumWidth( width )
        self._urls_listbox.setMinimumHeight( height )
        
        self._url_input = QW.QLineEdit( self )
        self._url_input.installEventFilter( ClientGUICommon.TextCatchEnterEventFilter( self._url_input, self.AddURL ) )
        
        self._copy_button = ClientGUICommon.IconButton( self, CC.global_icons().copy, self._Copy )
        self._copy_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'Copy selected URLs to the clipboard, or all URLs if none are selected.' ) )
        
        self._paste_button = ClientGUICommon.IconButton( self, CC.global_icons().paste, self._Paste )
        self._paste_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'Paste URLs from the clipboard.' ) )
        
        self._urls_to_add = set()
        self._urls_to_remove = set()
        
        #
        
        self._pending_content_updates = []
        
        self._current_urls_count = collections.Counter()
        
        self._UpdateList()
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._copy_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._paste_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._multiple_files_warning, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._urls_listbox, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, self._url_input, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, hbox, CC.FLAGS_ON_RIGHT )
        
        self.widget().setLayout( vbox )
        
        self._my_shortcut_handler = ClientGUIShortcuts.ShortcutsHandler( self, self, [ 'global', 'media', 'main_gui' ] )
        
        ClientGUIFunctions.SetFocusLater( self._url_input )
        
    
    def _Copy( self ):
        
        urls = self._urls_listbox.GetData( only_selected = True )
        
        if len( urls ) == 0:
            
            urls = self._urls_listbox.GetData()
            
        
        text = '\n'.join( urls )
        
        CG.client_controller.pub( 'clipboard', 'text', text )
        
    
    def _EnterURLs( self, urls, only_add = False ):
        
        normalised_urls = []
        weird_urls = []
        
        for url in urls:
            
            try:
                
                ClientNetworkingFunctions.CheckLooksLikeAFullURL( url )
                
                normalised_url = CG.client_controller.network_engine.domain_manager.NormaliseURL( url, for_server = True )
                
                normalised_urls.append( normalised_url )
                
            except HydrusExceptions.URLClassException:
                
                weird_urls.append( url )
                
            
        
        if len( weird_urls ) > 0:
            
            message = 'The URLs:'
            message += '\n' * 2
            message += '\n'.join( weird_urls )
            message += '\n' * 2
            message += '--did not parse. Normally I would not recommend importing invalid URLs, but do you want to force it anyway?'
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message )
            
            if result != QW.QDialog.DialogCode.Accepted:
                
                return False
                
            
            normalised_urls.extend( weird_urls )
            
        
        normalised_urls = HydrusLists.DedupeList( normalised_urls )
        
        for normalised_url in normalised_urls:
            
            addee_media = set()
            
            for m in self._current_media:
                
                locations_manager = m.GetLocationsManager()
                
                if normalised_url not in locations_manager.GetURLs():
                    
                    addee_media.add( m )
                    
                
            
            if len( addee_media ) > 0:
                
                addee_hashes = { m.GetHash() for m in addee_media }
                
                content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_URLS, HC.CONTENT_UPDATE_ADD, ( ( normalised_url, ), addee_hashes ) )
                
                for m in addee_media:
                    
                    m.GetMediaResult().ProcessContentUpdate( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, content_update )
                    
                
                self._pending_content_updates.append( content_update )
                
            
        
        #
        
        self._UpdateList()
        
    
    def _Paste( self ):
        
        try:
            
            raw_text = CG.client_controller.GetClipboardText()
            
        except HydrusExceptions.DataMissing as e:
            
            ClientGUIDialogsMessage.ShowWarning( self, str(e) )
            
            return
            
        
        try:
            
            urls = HydrusText.DeserialiseNewlinedTexts( raw_text )
            
            self._EnterURLs( urls, only_add = True )
            
        except Exception as e:
            
            ClientGUIDialogsQuick.PresentClipboardParseError( self, raw_text, 'Lines of URLs', e )
            
        
    
    def _RemoveURL( self, url ):
        
        removee_media = set()
        
        for m in self._current_media:
            
            locations_manager = m.GetLocationsManager()
            
            if url in locations_manager.GetURLs():
                
                removee_media.add( m )
                
            
        
        if len( removee_media ) > 0:
            
            removee_hashes = { m.GetHash() for m in removee_media }
            
            content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_URLS, HC.CONTENT_UPDATE_DELETE, ( ( url, ), removee_hashes ) )
            
            for m in removee_media:
                
                m.GetMediaResult().ProcessContentUpdate( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, content_update )
                
            
            self._pending_content_updates.append( content_update )
            
        
        #
        
        self._UpdateList()
        
    
    def _SetSearchFocus( self ):
        
        self._url_input.setFocus( QC.Qt.FocusReason.OtherFocusReason )
        
    
    def _UpdateList( self ):
        
        self._urls_listbox.clear()
        
        self._current_urls_count = collections.Counter()
        
        for m in self._current_media:
            
            locations_manager = m.GetLocationsManager()
            
            for url in locations_manager.GetURLs():
                
                self._current_urls_count[ url ] += 1
                
            
        
        for ( url, count ) in sorted( self._current_urls_count.items() ):
            
            if len( self._current_media ) == 1:
                
                label = url
                
            else:
                
                label = '{} ({})'.format( url, count )
                
            
            item = QW.QListWidgetItem()
            item.setText( label )
            item.setData( QC.Qt.ItemDataRole.UserRole, url )
            
            self._urls_listbox.addItem( item )
            
        
    
    def AddURL( self ):
        
        url = self._url_input.text()
        
        if url == '':
            
            self._OKParent()
            
        else:
            
            try:
                
                self._EnterURLs( [ url ] )
                
                self._url_input.clear()
                
            except Exception as e:
                
                ClientGUIDialogsMessage.ShowCritical( self, 'Problem with URL!', f'I could not add that URL: {e}' )
                
            
        
    
    def DeleteSelected( self ):
        
        urls = self._urls_listbox.GetData( only_selected = True )
        
        for url in urls:
            
            self._RemoveURL( url )
            
        
    
    def GetValue( self ):
        
        return list( self._pending_content_updates )
        
    
    def ListDoubleClicked( self, item ):
        
        urls = self._urls_listbox.GetData( only_selected = True )
        
        for url in urls:
            
            self._RemoveURL( url )
            
        
        if len( urls ) == 1:
            
            url = urls[0]
            
            self._url_input.setText( url )
            
        
    
    def ProcessApplicationCommand( self, command: CAC.ApplicationCommand ):
        
        command_processed = True
        
        if command.IsSimpleCommand():
            
            action = command.GetSimpleAction()
            
            if action == CAC.SIMPLE_MANAGE_FILE_URLS:
                
                self._OKParent()
                
            elif action == CAC.SIMPLE_SET_SEARCH_FOCUS:
                
                self._SetSearchFocus()
                
            else:
                
                command_processed = False
                
            
        else:
            
            command_processed = False
            
        
        return command_processed
        
    
    def UserIsOKToOK( self ):
        
        current_text = self._url_input.text()
        
        if current_text != '':
            
            message = 'You have text still in the input! Sure you are ok to apply?'
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message )
            
            if result != QW.QDialog.DialogCode.Accepted:
                
                return False
                
            
        
        return True
        
    
