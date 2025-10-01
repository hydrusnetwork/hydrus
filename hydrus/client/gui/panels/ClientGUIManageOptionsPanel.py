import os
import random
import typing

from qtpy import QtGui as QG
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusPSUtil
from hydrus.core import HydrusPaths
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusStaticDir
from hydrus.core import HydrusTags
from hydrus.core import HydrusText
from hydrus.core import HydrusTime
from hydrus.core.files.images import HydrusImageHandling

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientData
from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIShortcutControls
from hydrus.client.gui import ClientGUIShortcuts
from hydrus.client.gui import ClientGUIStyle
from hydrus.client.gui import ClientGUITagSorting
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.importing import ClientGUIImport
from hydrus.client.gui.importing import ClientGUIImportOptions
from hydrus.client.gui.lists import ClientGUIListBook
from hydrus.client.gui.lists import ClientGUIListBoxes
from hydrus.client.gui.lists import ClientGUIListConstants as CGLC
from hydrus.client.gui.lists import ClientGUIListCtrl
from hydrus.client.gui.metadata import ClientGUITagsEditNamespaceSort
from hydrus.client.gui.metadata import ClientGUITagSummaryGenerator
from hydrus.client.gui.metadata import ClientGUITime
from hydrus.client.gui.pages import ClientGUIMediaResultsPanelSortCollect
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.panels import ClientGUIScrolledPanelsEdit
from hydrus.client.gui.panels import ClientGUIScrolledPanelsEditRegexFavourites
from hydrus.client.gui.search import ClientGUIACDropdown
from hydrus.client.gui.search import ClientGUILocation
from hydrus.client.gui.widgets import ClientGUIBytes
from hydrus.client.gui.widgets import ClientGUIColourPicker
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.importing.options import FileImportOptions
from hydrus.client.media import ClientMedia
from hydrus.client.metadata import ClientTags
from hydrus.client.networking import ClientNetworkingSessions

class OptionsPagePanel( QW.QWidget ):
    
    def UpdateOptions( self ):
        
        raise NotImplementedError()
        
    

class ShortcutsPanel( OptionsPagePanel ):
    
    def __init__( self, parent, new_options, all_shortcuts: list[ ClientGUIShortcuts.ShortcutSet ] ):
        
        self._new_options = new_options
        
        call_mouse_buttons_primary_secondary = new_options.GetBoolean( 'call_mouse_buttons_primary_secondary' )
        shortcuts_merge_non_number_numpad = new_options.GetBoolean( 'shortcuts_merge_non_number_numpad' )
        
        self._have_edited_anything = False
        
        super().__init__( parent )
        
        help_button = ClientGUICommon.IconButton( self, CC.global_icons().help, self._ShowHelp )
        help_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'Show help regarding editing shortcuts.' ) )
        
        self._call_mouse_buttons_primary_secondary = QW.QCheckBox( self )
        self._call_mouse_buttons_primary_secondary.setToolTip( ClientGUIFunctions.WrapToolTip( 'Useful if you swap your buttons around.' ) )
        
        self._shortcuts_merge_non_number_numpad = QW.QCheckBox( self )
        self._shortcuts_merge_non_number_numpad.setToolTip( ClientGUIFunctions.WrapToolTip( 'This means a "numpad" variant of Return/Home/Arrow etc.. is just counted as a normal one. Helps clear up a bunch of annoying keyboard mappings.' ) )
        
        reserved_panel = ClientGUICommon.StaticBox( self, 'built-in hydrus shortcut sets' )
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_SHORTCUT_SETS.ID, self._GetDisplayTuple, self._GetSortTuple )
        
        self._reserved_shortcuts = ClientGUIListCtrl.BetterListCtrlTreeView( reserved_panel, 6, model, activation_callback = self._EditReserved )
        
        ( min_width, min_height ) = ClientGUIFunctions.ConvertTextToPixels( self._reserved_shortcuts, ( 32, 12 ) )
        
        self._reserved_shortcuts.setMinimumSize( min_width, min_height )
        
        self._edit_reserved_button = ClientGUICommon.BetterButton( reserved_panel, 'edit', self._EditReserved )
        self._restore_defaults_button = ClientGUICommon.BetterButton( reserved_panel, 'restore defaults', self._RestoreDefaults )
        
        #
        
        custom_panel = ClientGUICommon.StaticBox( self, 'custom user sets' )
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_SHORTCUT_SETS.ID, self._GetDisplayTuple, self._GetSortTuple )
        
        self._custom_shortcuts = ClientGUIListCtrl.BetterListCtrlTreeView( custom_panel, 6, model, delete_key_callback = self._Delete, activation_callback = self._EditCustom )
        
        self._add_button = ClientGUICommon.BetterButton( custom_panel, 'add', self._Add )
        self._edit_custom_button = ClientGUICommon.BetterButton( custom_panel, 'edit', self._EditCustom )
        self._delete_button = ClientGUICommon.BetterButton( custom_panel, 'delete', self._Delete )
        
        #
        
        self._call_mouse_buttons_primary_secondary.setChecked( call_mouse_buttons_primary_secondary )
        self._shortcuts_merge_non_number_numpad.setChecked( shortcuts_merge_non_number_numpad )
        
        reserved_shortcuts = [ shortcuts for shortcuts in all_shortcuts if shortcuts.GetName() in ClientGUIShortcuts.SHORTCUTS_RESERVED_NAMES ]
        custom_shortcuts = [ shortcuts for shortcuts in all_shortcuts if shortcuts.GetName() not in ClientGUIShortcuts.SHORTCUTS_RESERVED_NAMES ]
        
        self._reserved_shortcuts.SetData( reserved_shortcuts )
        
        self._reserved_shortcuts.Sort()
        
        self._original_custom_names = { shortcuts.GetName() for shortcuts in custom_shortcuts }
        
        self._custom_shortcuts.SetData( custom_shortcuts )
        
        self._custom_shortcuts.Sort()
        
        #
        
        rows = []
        
        rows.append( ( 'Treat all non-number numpad inputs as "normal": ', self._shortcuts_merge_non_number_numpad ) )
        rows.append( ( 'Replace "left/right"-click labels with "primary/secondary": ', self._call_mouse_buttons_primary_secondary ) )
        
        mouse_gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        #
        
        button_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( button_hbox, self._edit_reserved_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( button_hbox, self._restore_defaults_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        reserved_panel.Add( self._reserved_shortcuts, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        reserved_panel.Add( button_hbox, CC.FLAGS_ON_RIGHT )
        
        #
        
        button_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( button_hbox, self._add_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( button_hbox, self._edit_custom_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( button_hbox, self._delete_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        custom_panel_message = 'Custom shortcuts are advanced. They apply to the media viewer and must be turned on to take effect.'
        
        st = ClientGUICommon.BetterStaticText( custom_panel, custom_panel_message )
        st.setWordWrap( True )
        
        custom_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
        custom_panel.Add( self._custom_shortcuts, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        custom_panel.Add( button_hbox, CC.FLAGS_ON_RIGHT )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, help_button, CC.FLAGS_ON_RIGHT )
        QP.AddToLayout( vbox, mouse_gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, reserved_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, custom_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.setLayout( vbox )
        
    
    def _Add( self ):
        
        shortcut_set = ClientGUIShortcuts.ShortcutSet( 'new shortcuts' )
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit shortcuts' ) as dlg:
            
            call_mouse_buttons_primary_secondary = self._call_mouse_buttons_primary_secondary.isChecked()
            shortcuts_merge_non_number_numpad = self._shortcuts_merge_non_number_numpad.isChecked()
            
            panel = ClientGUIShortcutControls.EditShortcutSetPanel( dlg, shortcut_set, call_mouse_buttons_primary_secondary, shortcuts_merge_non_number_numpad )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                new_shortcuts = panel.GetValue()
                
                existing_names = self._GetExistingCustomShortcutNames()
                
                new_shortcuts.SetNonDupeName( existing_names )
                
                self._custom_shortcuts.AddData( new_shortcuts, select_sort_and_scroll = True )
                
                self._have_edited_anything = True
                
            
        
    
    def _Delete( self ):
        
        result = ClientGUIDialogsQuick.GetYesNo( self, 'Remove all selected?' )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            self._custom_shortcuts.DeleteSelected()
            
            self._have_edited_anything = True
            
        
    
    def _EditCustom( self ):
        
        data = self._custom_shortcuts.GetTopSelectedData()
        
        if data is None:
            
            return
            
        
        shortcuts = data
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit shortcuts' ) as dlg:
            
            call_mouse_buttons_primary_secondary = self._call_mouse_buttons_primary_secondary.isChecked()
            shortcuts_merge_non_number_numpad = self._shortcuts_merge_non_number_numpad.isChecked()
            
            panel = ClientGUIShortcutControls.EditShortcutSetPanel( dlg, shortcuts, call_mouse_buttons_primary_secondary, shortcuts_merge_non_number_numpad )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                edited_shortcuts = panel.GetValue()
                
                existing_names = self._GetExistingCustomShortcutNames()
                
                existing_names.discard( shortcuts.GetName() )
                
                edited_shortcuts.SetNonDupeName( existing_names )
                
                self._custom_shortcuts.ReplaceData( shortcuts, edited_shortcuts, sort_and_scroll = True )
                
                self._have_edited_anything = True
                
            
        
    
    def _EditReserved( self ):
        
        data = self._reserved_shortcuts.GetTopSelectedData()
        
        if data is None:
            
            return
            
        
        shortcuts = data
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit shortcuts' ) as dlg:
            
            call_mouse_buttons_primary_secondary = self._call_mouse_buttons_primary_secondary.isChecked()
            shortcuts_merge_non_number_numpad = self._shortcuts_merge_non_number_numpad.isChecked()
            
            panel = ClientGUIShortcutControls.EditShortcutSetPanel( dlg, shortcuts, call_mouse_buttons_primary_secondary, shortcuts_merge_non_number_numpad )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                edited_shortcuts = panel.GetValue()
                
                self._reserved_shortcuts.ReplaceData( shortcuts, edited_shortcuts, sort_and_scroll = True )
                
                self._have_edited_anything = True
                
            
        
    
    def _GetDisplayTuple( self, shortcuts ):
        
        name = shortcuts.GetName()
        
        if name in ClientGUIShortcuts.shortcut_names_to_descriptions:
            
            pretty_name = ClientGUIShortcuts.shortcut_names_to_pretty_names[ name ]
            
        else:
            
            pretty_name = name
            
        
        size = len( shortcuts )
        
        return ( pretty_name, HydrusNumbers.ToHumanInt( size ) )
        
    
    def _GetExistingCustomShortcutNames( self ):
        
        return { shortcuts.GetName() for shortcuts in self._custom_shortcuts.GetData() }
        
    
    def _GetSortTuple( self, shortcuts ):
        
        name = shortcuts.GetName()
        
        if name in ClientGUIShortcuts.shortcut_names_to_descriptions:
            
            sort_name = ClientGUIShortcuts.shortcut_names_sorted.index( name )
            
        else:
            
            sort_name = name
            
        
        size = len( shortcuts )
        
        return ( sort_name, size )
        
    
    def _RestoreDefaults( self ):
        
        from hydrus.client import ClientDefaults
        
        defaults = ClientDefaults.GetDefaultShortcuts()
        
        names_to_sets = { shortcut_set.GetName() : shortcut_set for shortcut_set in defaults }
        
        choice_tuples = [ ( name, name ) for name in names_to_sets ]
        
        try:
            
            name = ClientGUIDialogsQuick.SelectFromList( self, 'select which default to restore', choice_tuples )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        new_data = names_to_sets[ name ]
        
        existing_data = None
        
        for data in self._reserved_shortcuts.GetData():
            
            if data.GetName() == name:
                
                existing_data = data
                
                break
                
            
        
        if existing_data is None:
            
            ClientGUIDialogsMessage.ShowInformation( self, 'It looks like your client was missing the "{}" shortcut set! It will now be restored.'.format( name ) )
            
            self._reserved_shortcuts.AddData( new_data, select_sort_and_scroll = True )
            
        else:
            
            message = 'Are you certain you want to restore the defaults for "{}"? Any custom shortcuts you have set will be wiped.'.format( name )
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message )
            
            if result == QW.QDialog.DialogCode.Accepted:
                
                self._reserved_shortcuts.ReplaceData( existing_data, new_data, sort_and_scroll = True )
                
            
        
    
    def _ShowHelp( self ):
        
        message = 'I am in the process of converting the multiple old messy shortcut systems to this single unified engine. Many actions are not yet available here, and mouse support is very limited. I expect to overwrite the reserved shortcut sets back to (new and expanded) defaults at least once more, so don\'t remap everything yet unless you are ok with doing it again.'
        message += '\n' * 2
        message += '---'
        message += '\n' * 2
        message += 'In hydrus, shortcuts are split into different sets that are active in different contexts. Depending on where the program focus is, multiple sets can be active at the same time. On a keyboard or mouse event, the active sets will be consulted one after another (typically from the smallest and most precise focus to the largest and broadest parent) until an action match is found.'
        message += '\n' * 2
        message += 'There are two kinds--ones built-in to hydrus, and custom sets that you turn on and off:'
        message += '\n' * 2
        message += 'The built-in shortcut sets are always active in their contexts--the \'main_gui\' one is always consulted when you hit a key on the main gui window, for instance. They have limited actions to choose from, appropriate to their context. If you would prefer to, say, open the manage tags dialog with Ctrl+F3, edit or add that entry in the \'media\' set and that new shortcut will apply anywhere you are focused on some particular media.'
        message += '\n' * 2
        message += 'Custom shortcuts sets are those you can create and rename at will. They are only ever active in the media viewer window, and only when you set them so from the top hover-window\'s keyboard icon. They are primarily meant for setting tags and ratings with shortcuts, and are intended to be turned on and off as you perform different \'filtering\' jobs--for instance, you might like to set the 1-5 keys to the different values of a five-star rating system, or assign a few simple keystrokes to a number of common tags.'
        message += '\n' * 2
        message += 'The built-in \'media\' set also supports tag and rating actions, if you would like some of those to always be active.'
        
        ClientGUIDialogsMessage.ShowInformation( self, message )
        
    
    def GetValue( self ):
        
        # a stub for wrapper panels/dialogs to check validity versus a normal editpanel
        return True
        
    
    def UpdateOptions( self ):
        
        call_mouse_buttons_primary_secondary = self._call_mouse_buttons_primary_secondary.isChecked()
        shortcuts_merge_non_number_numpad = self._shortcuts_merge_non_number_numpad.isChecked()
        
        self._new_options.SetBoolean( 'call_mouse_buttons_primary_secondary', call_mouse_buttons_primary_secondary )
        self._new_options.SetBoolean( 'shortcuts_merge_non_number_numpad', shortcuts_merge_non_number_numpad )
        
        if self._have_edited_anything:
            
            shortcut_sets = []
            
            shortcut_sets.extend( self._reserved_shortcuts.GetData() )
            shortcut_sets.extend( self._custom_shortcuts.GetData() )
            
            dupe_shortcut_sets = [ shortcut_set.Duplicate() for shortcut_set in shortcut_sets ]
            
            CG.client_controller.Write( 'serialisables_overwrite', [ HydrusSerialisable.SERIALISABLE_TYPE_SHORTCUT_SET ], dupe_shortcut_sets )
            
            ClientGUIShortcuts.shortcuts_manager().SetShortcutSets( shortcut_sets )
            
        
    

class ManageOptionsPanel( ClientGUIScrolledPanels.ManagePanel ):
    
    def __init__( self, parent ):
        
        super().__init__( parent )
        
        self._original_options = dict( HC.options )
        
        self._new_options = CG.client_controller.new_options
        self._original_new_options = self._new_options.Duplicate()
        
        all_shortcuts = ClientGUIShortcuts.shortcuts_manager().GetShortcutSets()
        
        self._listbook = ClientGUIListBook.ListBook( self, list_chars_width = 28 )
        
        self._listbook.AddPage( 'gui', self._GUIPanel( self._listbook ) ) # leave this at the top, to make it default page
        self._listbook.AddPage( 'audio', self._AudioPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'command palette', self._CommandPalettePanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'colours', self._ColoursPanel( self._listbook ) )
        self._listbook.AddPage( 'connection', self._ConnectionPanel( self._listbook ) )
        self._listbook.AddPage( 'exporting', self._ExportingPanel( self._listbook ) )
        self._listbook.AddPage( 'external programs', self._ExternalProgramsPanel( self._listbook ) )
        self._listbook.AddPage( 'files and trash', self._FilesAndTrashPanel( self._listbook ) )
        self._listbook.AddPage( 'file search', self._FileSearchPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'file viewing statistics', self._FileViewingStatisticsPanel( self._listbook ) )
        self._listbook.AddPage( 'gui pages', self._GUIPagesPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'gui sessions', self._GUISessionsPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'maintenance and processing', self._MaintenanceAndProcessingPanel( self._listbook ) )
        self._listbook.AddPage( 'media viewer', self._MediaViewerPanel( self._listbook ) )
        self._listbook.AddPage( 'media viewer hovers', self._MediaViewerHoversPanel( self._listbook ) )
        self._listbook.AddPage( 'media playback', self._MediaPlaybackPanel( self._listbook ) )
        self._listbook.AddPage( 'speed and memory', self._SpeedAndMemoryPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'system tray', self._SystemTrayPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'popup notifications', self._PopupPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'regex favourites', self._RegexPanel( self._listbook ) )
        self._listbook.AddPage( 'file sort/collect', self._FileSortCollectPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'downloading', self._DownloadingPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'duplicates', self._DuplicatesPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'importing', self._ImportingPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'ratings', self._RatingsPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'shortcuts', ShortcutsPanel( self._listbook, self._new_options, all_shortcuts ) )
        self._listbook.AddPage( 'style', self._StylePanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'tag editing', self._TagEditingPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'tag presentation', self._TagPresentationPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'tag sort', self._TagSortPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'tag suggestions', self._TagSuggestionsPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'tag autocomplete tabs', self._TagsPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'thumbnails', self._ThumbnailsPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'system', self._SystemPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'notes', self._NotesPanel( self._listbook, self._new_options ) )
        
        self._listbook.SortList()
        
        self._listbook.AddPage( 'advanced', self._AdvancedPanel( self._listbook, self._new_options ) )
        
        if self._new_options.GetBoolean( 'remember_options_window_panel' ):
            
            self._listbook.currentChanged.connect( self.SetCurrentOptionsPanel )
            
            self._listbook.SelectName( self._new_options.GetString( 'last_options_window_panel' ) )
            
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._listbook, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
    class _AdvancedPanel( OptionsPagePanel ):
        
        def __init__( self, parent, new_options ):
            
            super().__init__( parent )
            
            self._new_options = new_options
            
            # https://github.com/hydrusnetwork/hydrus/issues/1558
            
            self._advanced_mode = QW.QCheckBox( self )
            self._advanced_mode.setToolTip( ClientGUIFunctions.WrapToolTip( 'This controls a variety of different features across the program, too many to list neatly. The plan is to blow this single option out into many granular options on this page.\n\nThis plan is failing!' ) )
            
            self._advanced_mode.setChecked( self._new_options.GetBoolean( 'advanced_mode' ) )
            
            vbox = QP.VBoxLayout()
            
            rows = []
            
            rows.append( ( 'Advanced mode: ', self._advanced_mode ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self, rows )
            
            #
            
            QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            vbox.addStretch( 0 )
            
            self.setLayout( vbox )
            
        
        def UpdateOptions( self ):
            
            self._new_options.SetBoolean( 'advanced_mode', self._advanced_mode.isChecked() )
            
        
    
    class _AudioPanel( OptionsPagePanel ):
        
        def __init__( self, parent, new_options ):
            
            super().__init__( parent )
            
            self._new_options = new_options
            
            #self._media_viewer_uses_its_own_audio_volume = QW.QCheckBox( self )
            self._preview_uses_its_own_audio_volume = QW.QCheckBox( self )
            
            self._has_audio_label = QW.QLineEdit( self )
            
            #
            
            tt = 'If unchecked, this media canvas will use the \'global\' audio volume slider. If checked, this media canvas will have its own separate one.'
            tt += '\n' * 2
            tt += 'Keep this on if you would like the preview viewer to be quieter than the main media viewer.'
            
            #self._media_viewer_uses_its_own_audio_volume.setChecked( self._new_options.GetBoolean( 'media_viewer_uses_its_own_audio_volume' ) )
            self._preview_uses_its_own_audio_volume.setChecked( self._new_options.GetBoolean( 'preview_uses_its_own_audio_volume' ) )
            
            #self._media_viewer_uses_its_own_audio_volume.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            self._preview_uses_its_own_audio_volume.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            self._has_audio_label.setText( self._new_options.GetString( 'has_audio_label' ) )
            
            #
            
            vbox = QP.VBoxLayout()
            
            rows = []
            
            rows.append( ( 'The preview window has its own volume: ', self._preview_uses_its_own_audio_volume ) )
            #rows.append( ( 'The media viewer has its own volume: ', self._media_viewer_uses_its_own_audio_volume ) )
            rows.append( ( 'Label for files with audio: ', self._has_audio_label ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self, rows )
            
            QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.addStretch( 0 )
            
            self.setLayout( vbox )
            
        
        def UpdateOptions( self ):
            
            #self._new_options.SetBoolean( 'media_viewer_uses_its_own_audio_volume', self._media_viewer_uses_its_own_audio_volume.isChecked() )
            self._new_options.SetBoolean( 'preview_uses_its_own_audio_volume', self._preview_uses_its_own_audio_volume.isChecked() )
            
            self._new_options.SetString( 'has_audio_label', self._has_audio_label.text() )
            
        
    
    class _ColoursPanel( OptionsPagePanel ):
        
        def __init__( self, parent ):
            
            super().__init__( parent )
            
            self._new_options = CG.client_controller.new_options
            
            help_text = 'Hey, this page is pretty old, and hydev is in the process of transforming it into a different system. Colours are generally managed through QSS stylesheets now, under the "style" page, but you can still override some stuff here if you want.'
            help_text += '\n\n'
            help_text += 'The "darkmode" in hydrus is also very old and only changes these colours; it does not change the stylesheet. Please bear with the awkwardness, this will be cleaned up eventually, thank you!'
            help_text += '\n\n'
            help_text += 'Tag colours are set under "tag presentation".'
            
            self._help_label = ClientGUICommon.BetterStaticText( self, label = help_text )
            
            self._help_label.setObjectName( 'HydrusWarning' )
            
            self._help_label.setWordWrap( True )
            
            self._override_stylesheet_colours = QW.QCheckBox( self )
            
            self._current_colourset = ClientGUICommon.BetterChoice( self )
            
            self._current_colourset.addItem( 'default', 'default' )
            self._current_colourset.addItem( 'darkmode', 'darkmode' )
            
            self._coloursets_panel = ClientGUICommon.StaticBox( self, 'coloursets' )
            
            self._notebook = QW.QTabWidget( self._coloursets_panel )
            
            self._gui_colours = {}
            
            for colourset in ( 'default', 'darkmode' ):
                
                self._gui_colours[ colourset ] = {}
                
                colour_panel = QW.QWidget( self._notebook )
                
                colour_types = []
                
                colour_types.append( CC.COLOUR_THUMB_BACKGROUND )
                colour_types.append( CC.COLOUR_THUMB_BACKGROUND_SELECTED )
                colour_types.append( CC.COLOUR_THUMB_BACKGROUND_REMOTE )
                colour_types.append( CC.COLOUR_THUMB_BACKGROUND_REMOTE_SELECTED )
                colour_types.append( CC.COLOUR_THUMB_BORDER )
                colour_types.append( CC.COLOUR_THUMB_BORDER_SELECTED )
                colour_types.append( CC.COLOUR_THUMB_BORDER_REMOTE )
                colour_types.append( CC.COLOUR_THUMB_BORDER_REMOTE_SELECTED )
                colour_types.append( CC.COLOUR_THUMBGRID_BACKGROUND )
                colour_types.append( CC.COLOUR_AUTOCOMPLETE_BACKGROUND )
                colour_types.append( CC.COLOUR_MEDIA_BACKGROUND )
                colour_types.append( CC.COLOUR_MEDIA_TEXT )
                colour_types.append( CC.COLOUR_TAGS_BOX )
                
                for colour_type in colour_types:
                    
                    ctrl = ClientGUIColourPicker.ColourPickerButton( colour_panel )
                    
                    ctrl.setMaximumWidth( 20 )
                    
                    ctrl.SetColour( self._new_options.GetColour( colour_type, colourset ) )
                    
                    self._gui_colours[ colourset ][ colour_type ] = ctrl
                    
                
                #
                
                rows = []
                
                hbox = QP.HBoxLayout()
                
                QP.AddToLayout( hbox, self._gui_colours[colourset][CC.COLOUR_THUMB_BACKGROUND], CC.FLAGS_CENTER_PERPENDICULAR )
                QP.AddToLayout( hbox, self._gui_colours[colourset][CC.COLOUR_THUMB_BACKGROUND_SELECTED], CC.FLAGS_CENTER_PERPENDICULAR )
                QP.AddToLayout( hbox, self._gui_colours[colourset][CC.COLOUR_THUMB_BACKGROUND_REMOTE], CC.FLAGS_CENTER_PERPENDICULAR )
                QP.AddToLayout( hbox, self._gui_colours[colourset][CC.COLOUR_THUMB_BACKGROUND_REMOTE_SELECTED], CC.FLAGS_CENTER_PERPENDICULAR )
                
                rows.append( ( 'thumbnail background (local: normal/selected, not local: normal/selected): ', hbox ) )
                
                hbox = QP.HBoxLayout()
                
                QP.AddToLayout( hbox, self._gui_colours[colourset][CC.COLOUR_THUMB_BORDER], CC.FLAGS_CENTER_PERPENDICULAR )
                QP.AddToLayout( hbox, self._gui_colours[colourset][CC.COLOUR_THUMB_BORDER_SELECTED], CC.FLAGS_CENTER_PERPENDICULAR )
                QP.AddToLayout( hbox, self._gui_colours[colourset][CC.COLOUR_THUMB_BORDER_REMOTE], CC.FLAGS_CENTER_PERPENDICULAR )
                QP.AddToLayout( hbox, self._gui_colours[colourset][CC.COLOUR_THUMB_BORDER_REMOTE_SELECTED], CC.FLAGS_CENTER_PERPENDICULAR )
                
                rows.append( ( 'thumbnail border (local: normal/selected, not local: normal/selected): ', hbox ) )
                
                rows.append( ( 'thumbnail grid background: ', self._gui_colours[ colourset ][ CC.COLOUR_THUMBGRID_BACKGROUND ] ) )
                rows.append( ( 'autocomplete background: ', self._gui_colours[ colourset ][ CC.COLOUR_AUTOCOMPLETE_BACKGROUND ] ) )
                rows.append( ( 'media viewer background: ', self._gui_colours[ colourset ][ CC.COLOUR_MEDIA_BACKGROUND ] ) )
                rows.append( ( 'media viewer text: ', self._gui_colours[ colourset ][ CC.COLOUR_MEDIA_TEXT ] ) )
                rows.append( ( 'tags box background: ', self._gui_colours[ colourset ][ CC.COLOUR_TAGS_BOX ] ) )
                
                gridbox = ClientGUICommon.WrapInGrid( colour_panel, rows )
                
                colour_panel.setLayout( gridbox )
                
                select = colourset == 'default'
                
                self._notebook.addTab( colour_panel, colourset )
                if select: self._notebook.setCurrentWidget( colour_panel )
                
            
            #
            
            self._override_stylesheet_colours.setChecked( self._new_options.GetBoolean( 'override_stylesheet_colours' ) )
            self._current_colourset.SetValue( self._new_options.GetString( 'current_colourset' ) )
            
            #
            
            rows = []
            
            rows.append( ( 'override what is set in the stylesheet with the colours on this page: ', self._override_stylesheet_colours ) )
            rows.append( ( 'current colourset: ', self._current_colourset ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self, rows )
            
            self._coloursets_panel.Add( self._notebook, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, self._help_label, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            QP.AddToLayout( vbox, self._coloursets_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.addStretch( 0 )
            
            self.setLayout( vbox )
            
            self._override_stylesheet_colours.clicked.connect( self._UpdateOverride )
            
            self._UpdateOverride()
            
        
        def _UpdateOverride( self ):
            
            self._coloursets_panel.setEnabled( self._override_stylesheet_colours.isChecked() )
            
        
        def UpdateOptions( self ):
            
            self._new_options.SetBoolean( 'override_stylesheet_colours', self._override_stylesheet_colours.isChecked() )
            
            for colourset in self._gui_colours:
                
                for ( colour_type, ctrl ) in list(self._gui_colours[ colourset ].items()):
                    
                    colour = ctrl.GetColour()
                    
                    self._new_options.SetColour( colour_type, colourset, colour )
                    
                
            
            self._new_options.SetString( 'current_colourset', self._current_colourset.GetValue() )
            
        
    
    class _ConnectionPanel( OptionsPagePanel ):
        
        def __init__( self, parent ):
            
            super().__init__( parent )
            
            self._new_options = CG.client_controller.new_options
            
            general = ClientGUICommon.StaticBox( self, 'general' )
            
            if self._new_options.GetBoolean( 'advanced_mode' ):
                
                network_timeout_min = 1
                network_timeout_max = 86400 * 30
                
                error_wait_time_min = 1
                error_wait_time_max = 86400 * 30
                
                max_network_jobs_max = 1000
                
                max_network_jobs_per_domain_max = 100
                
            else:
                
                network_timeout_min = 3
                network_timeout_max = 600
                
                error_wait_time_min = 3
                error_wait_time_max = 1800
                
                max_network_jobs_max = 30
                
                max_network_jobs_per_domain_max = 5
                
            
            self._max_connection_attempts_allowed = ClientGUICommon.BetterSpinBox( general, min = 1, max = 10 )
            self._max_connection_attempts_allowed.setToolTip( ClientGUIFunctions.WrapToolTip( 'This refers to timeouts when actually making the initial connection.' ) )
            
            self._max_request_attempts_allowed_get = ClientGUICommon.BetterSpinBox( general, min = 1, max = 10 )
            self._max_request_attempts_allowed_get.setToolTip( ClientGUIFunctions.WrapToolTip( 'This refers to timeouts when waiting for a response to our GET requests, whether that is the start or an interruption part way through.' ) )
            
            self._network_timeout = ClientGUICommon.BetterSpinBox( general, min = network_timeout_min, max = network_timeout_max )
            self._network_timeout.setToolTip( ClientGUIFunctions.WrapToolTip( 'If a network connection cannot be made in this duration or, once started, it experiences inactivity for six times this duration, it will be considered dead and retried or abandoned.' ) )
            
            self._connection_error_wait_time = ClientGUICommon.BetterSpinBox( general, min = error_wait_time_min, max = error_wait_time_max )
            self._connection_error_wait_time.setToolTip( ClientGUIFunctions.WrapToolTip( 'If a network connection times out as above, it will wait increasing multiples of this base time before retrying.' ) )
            
            self._serverside_bandwidth_wait_time = ClientGUICommon.BetterSpinBox( general, min = error_wait_time_min, max = error_wait_time_max )
            self._serverside_bandwidth_wait_time.setToolTip( ClientGUIFunctions.WrapToolTip( 'If a server returns a failure status code indicating it is short on bandwidth, and the server does not give a Retry-After header response, the network job will wait increasing multiples of this base time before retrying.' ) )
            
            self._domain_network_infrastructure_error_velocity = ClientGUITime.VelocityCtrl( general, 0, 100, 30, hours = True, minutes = True, seconds = True, per_phrase = 'within', unit = 'errors' )
            
            self._max_network_jobs = ClientGUICommon.BetterSpinBox( general, min = 1, max = max_network_jobs_max )
            self._max_network_jobs_per_domain = ClientGUICommon.BetterSpinBox( general, min = 1, max = max_network_jobs_per_domain_max )
            
            self._set_requests_ca_bundle_env = QW.QCheckBox( general )
            self._set_requests_ca_bundle_env.setToolTip( ClientGUIFunctions.WrapToolTip( 'Just testing something here; ignore unless hydev asks you to use it please. Requires restart. Note: this breaks the self-signed certificates of hydrus services.' ) )
            
            self._do_not_verify_regular_https = QW.QCheckBox( general )
            self._do_not_verify_regular_https.setToolTip( ClientGUIFunctions.WrapToolTip( 'This will not verify any HTTPS traffic. This tech is important for security, so only enable this mode temporarily, to test out unusual situations.' ) )
            
            #
            
            proxy_panel = ClientGUICommon.StaticBox( self, 'proxy settings' )
            
            if ClientNetworkingSessions.SOCKS_PROXY_OK:
                
                default_text = 'socks5://ip:port'
                
            else:
                
                default_text = 'http://ip:port'
                
            
            self._http_proxy = ClientGUICommon.NoneableTextCtrl( proxy_panel, default_text )
            self._https_proxy = ClientGUICommon.NoneableTextCtrl( proxy_panel, default_text )
            self._no_proxy = ClientGUICommon.NoneableTextCtrl( proxy_panel, '' )
            
            #
            
            self._set_requests_ca_bundle_env.setChecked( self._new_options.GetBoolean( 'set_requests_ca_bundle_env' ) )
            self._do_not_verify_regular_https.setChecked( not self._new_options.GetBoolean( 'verify_regular_https' ) )
            
            self._http_proxy.SetValue( self._new_options.GetNoneableString( 'http_proxy' ) )
            self._https_proxy.SetValue( self._new_options.GetNoneableString( 'https_proxy' ) )
            self._no_proxy.SetValue( self._new_options.GetNoneableString( 'no_proxy' ) )
            
            self._max_connection_attempts_allowed.setValue( self._new_options.GetInteger( 'max_connection_attempts_allowed' ) )
            self._max_request_attempts_allowed_get.setValue( self._new_options.GetInteger( 'max_request_attempts_allowed_get' ) )
            self._network_timeout.setValue( self._new_options.GetInteger( 'network_timeout' ) )
            self._connection_error_wait_time.setValue( self._new_options.GetInteger( 'connection_error_wait_time' ) )
            self._serverside_bandwidth_wait_time.setValue( self._new_options.GetInteger( 'serverside_bandwidth_wait_time' ) )
            
            number = self._new_options.GetInteger( 'domain_network_infrastructure_error_number' )
            time_delta = self._new_options.GetInteger( 'domain_network_infrastructure_error_time_delta' )
            
            self._domain_network_infrastructure_error_velocity.SetValue( ( number, time_delta ) )
            
            self._max_network_jobs.setValue( self._new_options.GetInteger( 'max_network_jobs' ) )
            self._max_network_jobs_per_domain.setValue( self._new_options.GetInteger( 'max_network_jobs_per_domain' ) )
            
            #
            
            if self._new_options.GetBoolean( 'advanced_mode' ):
                
                label = 'As you are in advanced mode, these options have very low and high limits. Be very careful about lowering delay time or raising max number of connections too far, as things will break.'
                
                st = ClientGUICommon.BetterStaticText( general, label = label )
                st.setObjectName( 'HydrusWarning' )
                
                st.setWordWrap( True )
                
                general.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
                
            
            rows = []
            
            rows.append( ( 'max connection attempts allowed per request: ', self._max_connection_attempts_allowed ) )
            rows.append( ( 'max retries allowed per request: ', self._max_request_attempts_allowed_get ) )
            rows.append( ( 'network timeout (seconds): ', self._network_timeout ) )
            rows.append( ( 'connection error retry wait (seconds): ', self._connection_error_wait_time ) )
            rows.append( ( 'serverside bandwidth retry wait (seconds): ', self._serverside_bandwidth_wait_time ) )
            rows.append( ( 'Halt new jobs as long as this many network infrastructure errors on their domain (0 for never wait): ', self._domain_network_infrastructure_error_velocity ) )
            rows.append( ( 'max number of simultaneous active network jobs: ', self._max_network_jobs ) )
            rows.append( ( 'max number of simultaneous active network jobs per domain: ', self._max_network_jobs_per_domain ) )
            rows.append( ( 'DEBUG: set the REQUESTS_CA_BUNDLE env to certifi cacert.pem on program start:', self._set_requests_ca_bundle_env ) )
            rows.append( ( 'DEBUG: do not verify regular https traffic:', self._do_not_verify_regular_https ) )
            
            gridbox = ClientGUICommon.WrapInGrid( general, rows )
            
            general.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            text = 'PROTIP: Use a system-wide VPN or other software to handle this externally if you can. This tech is old and imperfect.'
            text += '\n' * 2
            text += 'Enter strings such as "http://ip:port" or "http://user:pass@ip:port" to use for http and https traffic. It should take effect immediately on dialog ok. Note that you have to enter "http://", not "https://" (an HTTP proxy forwards your traffic, which when you talk to an https:// address will be encrypted, but it does not wrap that in an extra layer of encryption itself).'
            text += '\n' * 2
            text += '"NO_PROXY" DOES NOT WORK UNLESS YOU HAVE A CUSTOM BUILD OF REQUESTS, SORRY! no_proxy takes the form of comma-separated hosts/domains, just as in curl or the NO_PROXY environment variable. When http and/or https proxies are set, they will not be used for these.'
            text += '\n' * 2
            
            if ClientNetworkingSessions.SOCKS_PROXY_OK:
                
                text += 'It looks like you have SOCKS support! You should also be able to enter (socks4 or) "socks5://ip:port".'
                text += '\n'
                text += 'Use socks4a or socks5h to force remote DNS resolution, on the proxy server.'
                
            else:
                
                text += 'It does not look like you have SOCKS support! If you want it, try adding "pysocks" (or "requests[socks]")!'
                
            
            st = ClientGUICommon.BetterStaticText( proxy_panel, text )
            
            st.setWordWrap( True )
            
            proxy_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            rows = []
            
            rows.append( ( 'http: ', self._http_proxy ) )
            rows.append( ( 'https: ', self._https_proxy ) )
            rows.append( ( 'no_proxy: ', self._no_proxy ) )
            
            gridbox = ClientGUICommon.WrapInGrid( proxy_panel, rows )
            
            proxy_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, general, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, proxy_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.addStretch( 0 )
            
            self.setLayout( vbox )
            
        
        def UpdateOptions( self ):
            
            self._new_options.SetBoolean( 'set_requests_ca_bundle_env', self._set_requests_ca_bundle_env.isChecked() )
            self._new_options.SetBoolean( 'verify_regular_https', not self._do_not_verify_regular_https.isChecked() )
            
            self._new_options.SetNoneableString( 'http_proxy', self._http_proxy.GetValue() )
            self._new_options.SetNoneableString( 'https_proxy', self._https_proxy.GetValue() )
            self._new_options.SetNoneableString( 'no_proxy', self._no_proxy.GetValue() )
            
            self._new_options.SetInteger( 'max_connection_attempts_allowed', self._max_connection_attempts_allowed.value() )
            self._new_options.SetInteger( 'max_request_attempts_allowed_get', self._max_request_attempts_allowed_get.value() )
            self._new_options.SetInteger( 'network_timeout', self._network_timeout.value() )
            self._new_options.SetInteger( 'connection_error_wait_time', self._connection_error_wait_time.value() )
            self._new_options.SetInteger( 'serverside_bandwidth_wait_time', self._serverside_bandwidth_wait_time.value() )
            
            ( number, time_delta ) = self._domain_network_infrastructure_error_velocity.GetValue()
            
            self._new_options.SetInteger( 'domain_network_infrastructure_error_number', number )
            self._new_options.SetInteger( 'domain_network_infrastructure_error_time_delta', time_delta )
            
            self._new_options.SetInteger( 'max_network_jobs', self._max_network_jobs.value() )
            self._new_options.SetInteger( 'max_network_jobs_per_domain', self._max_network_jobs_per_domain.value() )
            
        
    
    class _DownloadingPanel( OptionsPagePanel ):
        
        def __init__( self, parent, new_options ):
            
            super().__init__( parent )
            
            self._new_options = new_options
            
            #
            
            gallery_downloader = ClientGUICommon.StaticBox( self, 'gallery downloader' )
            
            gug_key_and_name = CG.client_controller.network_engine.domain_manager.GetDefaultGUGKeyAndName()
            
            self._default_gug = ClientGUIImport.GUGKeyAndNameSelector( gallery_downloader, gug_key_and_name )
            
            self._override_bandwidth_on_file_urls_from_post_urls = QW.QCheckBox( gallery_downloader )
            tt = 'Sometimes, File URLs have tokens on them that cause them to time out. If this is on, all file urls will override all bandwidth rules within three seconds, ensuring they occur quickly after their spawning Post URL parsed them. I recommend you leave this on, but you can turn it off if you have troubles here.'
            self._override_bandwidth_on_file_urls_from_post_urls.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            self._gallery_page_wait_period_pages = ClientGUICommon.BetterSpinBox( gallery_downloader, min=1, max=3600 )
            self._gallery_file_limit = ClientGUICommon.NoneableSpinCtrl( gallery_downloader, 2000, none_phrase = 'no limit', min = 1, max = 1000000 )
            
            self._highlight_new_query = QW.QCheckBox( gallery_downloader )
            
            #
            
            subscriptions = ClientGUICommon.StaticBox( self, 'subscriptions' )
            
            self._gallery_page_wait_period_subscriptions = ClientGUICommon.BetterSpinBox( subscriptions, min=1, max=3600 )
            self._max_simultaneous_subscriptions = ClientGUICommon.BetterSpinBox( subscriptions, min=1, max=100 )
            
            self._subscription_file_error_cancel_threshold = ClientGUICommon.NoneableSpinCtrl( subscriptions, 5, min = 1, max = 1000000, unit = 'errors' )
            self._subscription_file_error_cancel_threshold.setToolTip( ClientGUIFunctions.WrapToolTip( 'This is a simple patch and will be replaced with a better "retry network errors later" system at some point, but is useful to increase if you have subs to unreliable websites.' ) )
            
            self._process_subs_in_random_order = QW.QCheckBox( subscriptions )
            self._process_subs_in_random_order.setToolTip( ClientGUIFunctions.WrapToolTip( 'Processing in random order is useful whenever bandwidth is tight, as it stops an \'aardvark\' subscription from always getting first whack at what is available. Otherwise, they will be processed in alphabetical order.' ) )
            
            checker_options = self._new_options.GetDefaultSubscriptionCheckerOptions()
            
            self._subscription_checker_options = ClientGUIImport.CheckerOptionsButton( subscriptions, checker_options )
            
            #
            
            watchers = ClientGUICommon.StaticBox( self, 'watchers' )
            
            self._watcher_page_wait_period = ClientGUICommon.BetterSpinBox( watchers, min=1, max=3600 )
            self._highlight_new_watcher = QW.QCheckBox( watchers )
            
            checker_options = self._new_options.GetDefaultWatcherCheckerOptions()
            
            self._watcher_checker_options = ClientGUIImport.CheckerOptionsButton( watchers, checker_options )
            
            #
            
            misc = ClientGUICommon.StaticBox( self, 'misc' )
            
            self._remove_leading_url_double_slashes = QW.QCheckBox( misc )
            tt = 'The client used to remove leading double slashes from an URL path, collapsing something like https://site.com//images/123456 to https://site.com/images/123456. This is not correct, and it no longer does this. If you need it to do this again, to fix some URL CLass, turn this on. I will retire this option eventually, so update your downloader to work in the new system (ideally recognise both formats).'
            self._remove_leading_url_double_slashes.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            self._replace_percent_twenty_with_space_in_gug_input = QW.QCheckBox( misc )
            tt = 'Checking this will cause any query text input into a downloader like "skirt%20blue_eyes" to be considered as "skirt blue_eyes". This lets you copy/paste an input straight from certain encoded URLs, but it also causes trouble if you need to input %20 raw, so this is no longer the default behaviour. This is a legacy option and I recommend you turn it off if you no longer think you need it.'
            self._replace_percent_twenty_with_space_in_gug_input.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            self._pause_character = QW.QLineEdit( misc )
            self._stop_character = QW.QLineEdit( misc )
            self._show_new_on_file_seed_short_summary = QW.QCheckBox( misc )
            self._show_deleted_on_file_seed_short_summary = QW.QCheckBox( misc )
            
            if self._new_options.GetBoolean( 'advanced_mode' ):
                
                delay_min = 1
                
            else:
                
                delay_min = 600
                
            
            self._subscription_network_error_delay = ClientGUITime.TimeDeltaButton( misc, min = delay_min, days = True, hours = True, minutes = True, seconds = True )
            self._subscription_other_error_delay = ClientGUITime.TimeDeltaButton( misc, min = delay_min, days = True, hours = True, minutes = True, seconds = True )
            self._downloader_network_error_delay = ClientGUITime.TimeDeltaButton( misc, min = delay_min, days = True, hours = True, minutes = True, seconds = True )
            
            #
            
            gallery_page_tt = 'Gallery page fetches are heavy requests with unusual fetch-time requirements. It is important they not wait too long, but it is also useful to throttle them:'
            gallery_page_tt += '\n' * 2
            gallery_page_tt += '- So they do not compete with file downloads for bandwidth, leading to very unbalanced 20/4400-type queues.'
            gallery_page_tt += '\n'
            gallery_page_tt += '- So you do not get 1000 items in your queue before realising you did not like that tag anyway.'
            gallery_page_tt += '\n'
            gallery_page_tt += '- To give servers a break (some gallery pages can be CPU-expensive to generate).'
            gallery_page_tt += '\n' * 2
            gallery_page_tt += 'These delays/lots are per-domain.'
            gallery_page_tt += '\n' * 2
            gallery_page_tt += 'If you do not understand this stuff, you can just leave it alone.'
            
            self._gallery_page_wait_period_pages.setValue( self._new_options.GetInteger( 'gallery_page_wait_period_pages' ) )
            self._gallery_page_wait_period_pages.setToolTip( ClientGUIFunctions.WrapToolTip( gallery_page_tt ) )
            self._gallery_file_limit.SetValue( HC.options['gallery_file_limit'] )
            
            self._override_bandwidth_on_file_urls_from_post_urls.setChecked( self._new_options.GetBoolean( 'override_bandwidth_on_file_urls_from_post_urls' ) )
            self._highlight_new_query.setChecked( self._new_options.GetBoolean( 'highlight_new_query' ) )
            
            self._gallery_page_wait_period_subscriptions.setValue( self._new_options.GetInteger( 'gallery_page_wait_period_subscriptions' ) )
            self._gallery_page_wait_period_subscriptions.setToolTip( ClientGUIFunctions.WrapToolTip( gallery_page_tt ) )
            self._max_simultaneous_subscriptions.setValue( self._new_options.GetInteger( 'max_simultaneous_subscriptions' ) )
            
            self._subscription_file_error_cancel_threshold.SetValue( self._new_options.GetNoneableInteger( 'subscription_file_error_cancel_threshold' ) )
            
            self._process_subs_in_random_order.setChecked( self._new_options.GetBoolean( 'process_subs_in_random_order' ) )
            
            self._remove_leading_url_double_slashes.setChecked( self._new_options.GetBoolean( 'remove_leading_url_double_slashes' ) )
            self._replace_percent_twenty_with_space_in_gug_input.setChecked( self._new_options.GetBoolean( 'replace_percent_twenty_with_space_in_gug_input' ) )
            self._pause_character.setText( self._new_options.GetString( 'pause_character' ) )
            self._stop_character.setText( self._new_options.GetString( 'stop_character' ) )
            self._show_new_on_file_seed_short_summary.setChecked( self._new_options.GetBoolean( 'show_new_on_file_seed_short_summary' ) )
            self._show_deleted_on_file_seed_short_summary.setChecked( self._new_options.GetBoolean( 'show_deleted_on_file_seed_short_summary' ) )
            
            self._watcher_page_wait_period.setValue( self._new_options.GetInteger( 'watcher_page_wait_period' ) )
            self._watcher_page_wait_period.setToolTip( ClientGUIFunctions.WrapToolTip( gallery_page_tt ) )
            self._highlight_new_watcher.setChecked( self._new_options.GetBoolean( 'highlight_new_watcher' ) )
            
            self._subscription_network_error_delay.SetValue( self._new_options.GetInteger( 'subscription_network_error_delay' ) )
            self._subscription_other_error_delay.SetValue( self._new_options.GetInteger( 'subscription_other_error_delay' ) )
            self._downloader_network_error_delay.SetValue( self._new_options.GetInteger( 'downloader_network_error_delay' ) )
            
            #
            
            rows = []
            
            rows.append( ( 'Default download source:', self._default_gug ) )
            rows.append( ( 'Additional fixed time (in seconds) to wait between gallery page fetches:', self._gallery_page_wait_period_pages ) )
            rows.append( ( 'By default, stop searching once this many files are found:', self._gallery_file_limit ) )
            rows.append( ( 'If new query entered and no current highlight, highlight the new query:', self._highlight_new_query ) )
            rows.append( ( 'Force file downloads to occur quickly after Post URL fetches:', self._override_bandwidth_on_file_urls_from_post_urls ) )
            
            gridbox = ClientGUICommon.WrapInGrid( gallery_downloader, rows )
            
            gallery_downloader.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            rows = []
            
            rows.append( ( 'Additional fixed time (in seconds) to wait between gallery page fetches:', self._gallery_page_wait_period_subscriptions ) )
            rows.append( ( 'Maximum number of subscriptions that can sync simultaneously:', self._max_simultaneous_subscriptions ) )
            rows.append( ( 'If a subscription has this many failed file imports, stop and continue later:', self._subscription_file_error_cancel_threshold ) )
            rows.append( ( 'Sync subscriptions in random order:', self._process_subs_in_random_order ) )
            rows.append( ( 'Default subscription checker options:', self._subscription_checker_options ) )
            
            gridbox = ClientGUICommon.WrapInGrid( subscriptions, rows )
            
            subscriptions.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            rows = []
            
            rows.append( ( 'Additional fixed time (in seconds) to wait between watcher checks:', self._watcher_page_wait_period ) )
            rows.append( ( 'If new watcher entered and no current highlight, highlight the new watcher:', self._highlight_new_watcher ) )
            rows.append( ( 'Default watcher checker options:', self._watcher_checker_options ) )
            
            gridbox = ClientGUICommon.WrapInGrid( watchers, rows )
            
            watchers.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            rows = []
            
            rows.append( ( 'Pause character:', self._pause_character ) )
            rows.append( ( 'Stop character:', self._stop_character ) )
            rows.append( ( 'Show a \'N\' (for \'new\') count on short file import summaries:', self._show_new_on_file_seed_short_summary ) )
            rows.append( ( 'Show a \'D\' (for \'deleted\') count on short file import summaries:', self._show_deleted_on_file_seed_short_summary ) )
            rows.append( ( 'Delay time on a gallery/watcher network error:', self._downloader_network_error_delay ) )
            rows.append( ( 'Delay time on a subscription network error:', self._subscription_network_error_delay ) )
            rows.append( ( 'Delay time on a subscription other error:', self._subscription_other_error_delay ) )
            rows.append( ( 'DEBUG: remove leading double-slashes from URL paths:', self._remove_leading_url_double_slashes ) )
            rows.append( ( 'DEBUG: consider %20 the same as space in downloader query text inputs:', self._replace_percent_twenty_with_space_in_gug_input ) )
            
            gridbox = ClientGUICommon.WrapInGrid( misc, rows )
            
            misc.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, gallery_downloader, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, subscriptions, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, watchers, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, misc, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.addStretch( 0 )
            
            self.setLayout( vbox )
            
        
        def UpdateOptions( self ):
            
            CG.client_controller.network_engine.domain_manager.SetDefaultGUGKeyAndName( self._default_gug.GetValue() )
            
            self._new_options.SetInteger( 'gallery_page_wait_period_pages', self._gallery_page_wait_period_pages.value() )
            HC.options[ 'gallery_file_limit' ] = self._gallery_file_limit.GetValue()
            self._new_options.SetBoolean( 'highlight_new_query', self._highlight_new_query.isChecked() )
            self._new_options.SetBoolean( 'override_bandwidth_on_file_urls_from_post_urls', self._override_bandwidth_on_file_urls_from_post_urls.isChecked() )
            
            self._new_options.SetInteger( 'gallery_page_wait_period_subscriptions', self._gallery_page_wait_period_subscriptions.value() )
            self._new_options.SetInteger( 'max_simultaneous_subscriptions', self._max_simultaneous_subscriptions.value() )
            self._new_options.SetNoneableInteger( 'subscription_file_error_cancel_threshold', self._subscription_file_error_cancel_threshold.GetValue() )
            self._new_options.SetBoolean( 'process_subs_in_random_order', self._process_subs_in_random_order.isChecked() )
            
            self._new_options.SetInteger( 'watcher_page_wait_period', self._watcher_page_wait_period.value() )
            self._new_options.SetBoolean( 'highlight_new_watcher', self._highlight_new_watcher.isChecked() )
            
            self._new_options.SetDefaultWatcherCheckerOptions( self._watcher_checker_options.GetValue() )
            self._new_options.SetDefaultSubscriptionCheckerOptions( self._subscription_checker_options.GetValue() )
            
            self._new_options.SetBoolean( 'remove_leading_url_double_slashes', self._remove_leading_url_double_slashes.isChecked() )
            self._new_options.SetBoolean( 'replace_percent_twenty_with_space_in_gug_input', self._replace_percent_twenty_with_space_in_gug_input.isChecked() )
            self._new_options.SetString( 'pause_character', self._pause_character.text() )
            self._new_options.SetString( 'stop_character', self._stop_character.text() )
            self._new_options.SetBoolean( 'show_new_on_file_seed_short_summary', self._show_new_on_file_seed_short_summary.isChecked() )
            self._new_options.SetBoolean( 'show_deleted_on_file_seed_short_summary', self._show_deleted_on_file_seed_short_summary.isChecked() )
            
            self._new_options.SetInteger( 'subscription_network_error_delay', self._subscription_network_error_delay.GetValue() )
            self._new_options.SetInteger( 'subscription_other_error_delay', self._subscription_other_error_delay.GetValue() )
            self._new_options.SetInteger( 'downloader_network_error_delay', self._downloader_network_error_delay.GetValue() )
            
        
    
    class _DuplicatesPanel( OptionsPagePanel ):
        
        def __init__( self, parent, new_options ):
            
            super().__init__( parent )
            
            self._new_options = new_options
            
            #
            
            open_panel = ClientGUICommon.StaticBox( self, 'open in a new duplicates filter page' )
            
            self._open_files_to_duplicate_filter_uses_all_my_files = QW.QCheckBox( open_panel )
            self._open_files_to_duplicate_filter_uses_all_my_files.setToolTip( ClientGUIFunctions.WrapToolTip( 'Normally, when you open a selection of files into a new page, the current file domain is preserved. For duplicates filters, you usually want to search in "all my files", so this sticks that. If you need domain-specific duplicates pages and know what you are doing, you can turn this off.' ) )
            
            duplicates_filter_page_panel = ClientGUICommon.StaticBox( self, 'duplicates filter page' )
            
            self._hide_duplicates_needs_work_message_when_reasonably_caught_up = QW.QCheckBox( duplicates_filter_page_panel )
            self._hide_duplicates_needs_work_message_when_reasonably_caught_up.setToolTip( ClientGUIFunctions.WrapToolTip( 'By default, the duplicates filter page will not highlight that there is potential duplicates search work to do if you are 99% done. This saves you being notified by the normal background burble of regular file imports. If you want to know whenever any work is pending, uncheck this.' ) )
            
            weights_panel = ClientGUICommon.StaticBox( self, 'duplicate filter comparison score weights' )
            
            self._duplicate_comparison_score_higher_jpeg_quality = ClientGUICommon.BetterSpinBox( weights_panel, min=-100, max=100 )
            self._duplicate_comparison_score_much_higher_jpeg_quality = ClientGUICommon.BetterSpinBox( weights_panel, min=-100, max=100 )
            self._duplicate_comparison_score_higher_filesize = ClientGUICommon.BetterSpinBox( weights_panel, min=-100, max=100 )
            self._duplicate_comparison_score_much_higher_filesize = ClientGUICommon.BetterSpinBox( weights_panel, min=-100, max=100 )
            self._duplicate_comparison_score_higher_resolution = ClientGUICommon.BetterSpinBox( weights_panel, min=-100, max=100 )
            self._duplicate_comparison_score_much_higher_resolution = ClientGUICommon.BetterSpinBox( weights_panel, min=-100, max=100 )
            self._duplicate_comparison_score_more_tags = ClientGUICommon.BetterSpinBox( weights_panel, min=-100, max=100 )
            self._duplicate_comparison_score_older = ClientGUICommon.BetterSpinBox( weights_panel, min=-100, max=100 )
            self._duplicate_comparison_score_nicer_ratio = ClientGUICommon.BetterSpinBox( weights_panel, min=-100, max=100 )
            self._duplicate_comparison_score_has_audio = ClientGUICommon.BetterSpinBox( weights_panel, min=-100, max=100 )
            
            self._duplicate_comparison_score_nicer_ratio.setToolTip( ClientGUIFunctions.WrapToolTip( 'For instance, 16:9 vs 640:357.') )
            
            batches_panel = ClientGUICommon.StaticBox( self, 'duplicate filter batches' )
            
            self._duplicate_filter_max_batch_size = ClientGUICommon.BetterSpinBox( batches_panel, min = 5, max = 1024 )
            self._duplicate_filter_max_batch_size.setToolTip( ClientGUIFunctions.WrapToolTip( 'In group mode you always see the whole group, which in some cases can be 1,000+ items.' ) )
            
            self._duplicate_filter_auto_commit_batch_size = ClientGUICommon.NoneableSpinCtrl( batches_panel, 1, min = 1, max = 50, none_phrase = 'no, always confirm' )
            self._duplicate_filter_auto_commit_batch_size.setToolTip( ClientGUIFunctions.WrapToolTip( 'When you are dealing with numerous 1/1 size batches/groups, it can get annoying to click through the confirm every time. This will auto-confirm any batch with this many decisions of fewer, assuming no manual skips.' ) )
            
            colours_panel = ClientGUICommon.StaticBox( self, 'colours' )
            
            self._duplicate_background_switch_intensity_a = ClientGUICommon.NoneableSpinCtrl( colours_panel, 3, none_phrase = 'do not change', min = 1, max = 9 )
            self._duplicate_background_switch_intensity_a.setToolTip( ClientGUIFunctions.WrapToolTip( 'This changes the background colour when you are looking at A. If you have a pure white/black background and do not have transparent images to show with checkerboard, it helps to highlight transparency vs opaque white/black image background.' ) )
            
            self._duplicate_background_switch_intensity_b = ClientGUICommon.NoneableSpinCtrl( colours_panel, 3, none_phrase = 'do not change', min = 1, max = 9 )
            self._duplicate_background_switch_intensity_b.setToolTip( ClientGUIFunctions.WrapToolTip( 'This changes the background colour when you are looking at B. Making it different to the A value helps to highlight switches between the two.' ) )
            
            self._draw_transparency_checkerboard_media_canvas_duplicates = QW.QCheckBox( colours_panel )
            self._draw_transparency_checkerboard_media_canvas_duplicates.setToolTip( ClientGUIFunctions.WrapToolTip( 'Same as the setting in _media playback_, but only for the duplicate filter. Only applies if that _media_ setting is unchecked.' ) )
            
            #
            
            self._open_files_to_duplicate_filter_uses_all_my_files.setChecked( self._new_options.GetBoolean( 'open_files_to_duplicate_filter_uses_all_my_files' ) )
            
            self._hide_duplicates_needs_work_message_when_reasonably_caught_up.setChecked( self._new_options.GetBoolean( 'hide_duplicates_needs_work_message_when_reasonably_caught_up' ) )
            
            self._duplicate_comparison_score_higher_jpeg_quality.setValue( self._new_options.GetInteger( 'duplicate_comparison_score_higher_jpeg_quality' ) )
            self._duplicate_comparison_score_much_higher_jpeg_quality.setValue( self._new_options.GetInteger( 'duplicate_comparison_score_much_higher_jpeg_quality' ) )
            self._duplicate_comparison_score_higher_filesize.setValue( self._new_options.GetInteger( 'duplicate_comparison_score_higher_filesize' ) )
            self._duplicate_comparison_score_much_higher_filesize.setValue( self._new_options.GetInteger( 'duplicate_comparison_score_much_higher_filesize' ) )
            self._duplicate_comparison_score_higher_resolution.setValue( self._new_options.GetInteger( 'duplicate_comparison_score_higher_resolution' ) )
            self._duplicate_comparison_score_much_higher_resolution.setValue( self._new_options.GetInteger( 'duplicate_comparison_score_much_higher_resolution' ) )
            self._duplicate_comparison_score_more_tags.setValue( self._new_options.GetInteger( 'duplicate_comparison_score_more_tags' ) )
            self._duplicate_comparison_score_older.setValue( self._new_options.GetInteger( 'duplicate_comparison_score_older' ) )
            self._duplicate_comparison_score_nicer_ratio.setValue( self._new_options.GetInteger( 'duplicate_comparison_score_nicer_ratio' ) )
            self._duplicate_comparison_score_has_audio.setValue( self._new_options.GetInteger( 'duplicate_comparison_score_has_audio' ) )
            
            self._duplicate_filter_max_batch_size.setValue( self._new_options.GetInteger( 'duplicate_filter_max_batch_size' ) )
            self._duplicate_filter_auto_commit_batch_size.SetValue( self._new_options.GetNoneableInteger( 'duplicate_filter_auto_commit_batch_size' ) )
            
            self._duplicate_background_switch_intensity_a.SetValue( self._new_options.GetNoneableInteger( 'duplicate_background_switch_intensity_a' ) )
            self._duplicate_background_switch_intensity_b.SetValue( self._new_options.GetNoneableInteger( 'duplicate_background_switch_intensity_b' ) )
            self._draw_transparency_checkerboard_media_canvas_duplicates.setChecked( self._new_options.GetBoolean( 'draw_transparency_checkerboard_media_canvas_duplicates' ) )
            
            #
            
            rows = []
            
            rows.append( ( 'Set to "all my files" when hitting "Open files in a new duplicates filter page":', self._open_files_to_duplicate_filter_uses_all_my_files ) )
            
            gridbox = ClientGUICommon.WrapInGrid( open_panel, rows )
            
            open_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            rows = []
            
            rows.append( ( 'Hide the "x% done" notification on preparation tab when >99% searched:', self._hide_duplicates_needs_work_message_when_reasonably_caught_up ) )
            
            gridbox = ClientGUICommon.WrapInGrid( duplicates_filter_page_panel, rows )
            
            duplicates_filter_page_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            rows = []
            
            rows.append( ( 'Score for jpeg with non-trivially higher jpeg quality:', self._duplicate_comparison_score_higher_jpeg_quality ) )
            rows.append( ( 'Score for jpeg with significantly higher jpeg quality:', self._duplicate_comparison_score_much_higher_jpeg_quality ) )
            rows.append( ( 'Score for file with non-trivially higher filesize:', self._duplicate_comparison_score_higher_filesize ) )
            rows.append( ( 'Score for file with significantly higher filesize:', self._duplicate_comparison_score_much_higher_filesize ) )
            rows.append( ( 'Score for file with higher resolution (as num pixels):', self._duplicate_comparison_score_higher_resolution ) )
            rows.append( ( 'Score for file with significantly higher resolution (as num pixels):', self._duplicate_comparison_score_much_higher_resolution ) )
            rows.append( ( 'Score for file with more tags:', self._duplicate_comparison_score_more_tags ) )
            rows.append( ( 'Score for file with non-trivially earlier import time:', self._duplicate_comparison_score_older ) )
            rows.append( ( 'Score for file with \'nicer\' resolution ratio:', self._duplicate_comparison_score_nicer_ratio ) )
            rows.append( ( 'Score for file with audio:', self._duplicate_comparison_score_has_audio ) )
            
            gridbox = ClientGUICommon.WrapInGrid( weights_panel, rows )
            
            label = 'When processing potential duplicate pairs in the duplicate filter, the client tries to present the \'best\' file first. It judges the two files on a variety of potential differences, each with a score. The file with the greatest total score is presented first. Here you can tinker with these scores.'
            label += '\n' * 2
            label += 'I recommend you leave all these as positive numbers, but if you wish, you can set a negative number to reduce the score.'
            
            st = ClientGUICommon.BetterStaticText( weights_panel, label )
            st.setWordWrap( True )
            
            weights_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
            weights_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            rows = []
            
            rows.append( ( 'Max size of duplicate filter pair batches (in mixed mode):', self._duplicate_filter_max_batch_size ) )
            rows.append( ( 'Auto-commit completed batches of this size or smaller:', self._duplicate_filter_auto_commit_batch_size ) )
            
            gridbox = ClientGUICommon.WrapInGrid( batches_panel, rows )
            
            batches_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            st = ClientGUICommon.BetterStaticText( colours_panel, label = 'The duplicate filter can darken/lighten your normal background colour. This highlights the transitions between A and B and, if your background colour is normally pure white or black, can differentiate transparency vs white/black opaque image background.' )
            st.setWordWrap( True )
            
            colours_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            rows = []
            
            rows.append( ( 'background light/dark switch intensity for A:', self._duplicate_background_switch_intensity_a ) )
            rows.append( ( 'background light/dark switch intensity for B:', self._duplicate_background_switch_intensity_b ) )
            rows.append( ( 'draw image transparency as checkerboard in the duplicate filter:', self._draw_transparency_checkerboard_media_canvas_duplicates ) )
            
            gridbox = ClientGUICommon.WrapInGrid( colours_panel, rows )
            
            colours_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, open_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, duplicates_filter_page_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, batches_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, weights_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, colours_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.addStretch( 0 )
            
            self.setLayout( vbox )
            
        
        def UpdateOptions( self ):
            
            self._new_options.SetBoolean( 'open_files_to_duplicate_filter_uses_all_my_files', self._open_files_to_duplicate_filter_uses_all_my_files.isChecked() )
            
            self._new_options.SetBoolean( 'hide_duplicates_needs_work_message_when_reasonably_caught_up', self._hide_duplicates_needs_work_message_when_reasonably_caught_up.isChecked() )
            
            self._new_options.SetInteger( 'duplicate_comparison_score_higher_jpeg_quality', self._duplicate_comparison_score_higher_jpeg_quality.value() )
            self._new_options.SetInteger( 'duplicate_comparison_score_much_higher_jpeg_quality', self._duplicate_comparison_score_much_higher_jpeg_quality.value() )
            self._new_options.SetInteger( 'duplicate_comparison_score_higher_filesize', self._duplicate_comparison_score_higher_filesize.value() )
            self._new_options.SetInteger( 'duplicate_comparison_score_much_higher_filesize', self._duplicate_comparison_score_much_higher_filesize.value() )
            self._new_options.SetInteger( 'duplicate_comparison_score_higher_resolution', self._duplicate_comparison_score_higher_resolution.value() )
            self._new_options.SetInteger( 'duplicate_comparison_score_much_higher_resolution', self._duplicate_comparison_score_much_higher_resolution.value() )
            self._new_options.SetInteger( 'duplicate_comparison_score_more_tags', self._duplicate_comparison_score_more_tags.value() )
            self._new_options.SetInteger( 'duplicate_comparison_score_older', self._duplicate_comparison_score_older.value() )
            self._new_options.SetInteger( 'duplicate_comparison_score_nicer_ratio', self._duplicate_comparison_score_nicer_ratio.value() )
            self._new_options.SetInteger( 'duplicate_comparison_score_has_audio', self._duplicate_comparison_score_has_audio.value() )
            
            self._new_options.SetInteger( 'duplicate_filter_max_batch_size', self._duplicate_filter_max_batch_size.value() )
            
            self._new_options.SetNoneableInteger( 'duplicate_filter_auto_commit_batch_size', self._duplicate_filter_auto_commit_batch_size.GetValue() )
            
            self._new_options.SetNoneableInteger( 'duplicate_background_switch_intensity_a', self._duplicate_background_switch_intensity_a.GetValue() )
            self._new_options.SetNoneableInteger( 'duplicate_background_switch_intensity_b', self._duplicate_background_switch_intensity_b.GetValue() )
            self._new_options.SetBoolean( 'draw_transparency_checkerboard_media_canvas_duplicates', self._draw_transparency_checkerboard_media_canvas_duplicates.isChecked() )
            
        
    
    class _ExportingPanel( OptionsPagePanel ):
        
        def __init__( self, parent ):
            
            super().__init__( parent )
            
            self._exports_panel = ClientGUICommon.StaticBox( self, 'all exports' )
            
            self._always_apply_ntfs_export_filename_rules = QW.QCheckBox( self._exports_panel )
            tt = 'IF YOU ARE DRAG AND DROPPING CLEVER FILENAMES TO NTFS, TURN THIS ON.\n\nWhen generating an export filename, hydrus will try to determine the filesystem of the destination, and if it is Windows-like (NTFS, exFAT, CIFS, etc..), it will remove colons and such from the filename. If you have a complicated mount setup where hydrus might not recognise this is true (e.g. NTFS behind NFS, or a mountpoint deeper than the base export folder that translates to NTFS), or if you are doing any drag and drops to an NTFS drive (in this case, hydrus first exports to your tempdir before the drag and drop even starts, and Qt & your OS handle the rest), turn this on and it will always make safer filenames.'
            self._always_apply_ntfs_export_filename_rules.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            self._export_dirname_character_limit = ClientGUICommon.NoneableSpinCtrl( self, 64, none_phrase = 'let hydrus decide', min = 16, max = 8192 )
            tt = 'BEST USED IN CONJUNCTION WITH THE PATH LIMIT FOR WHEN YOU ARE TESTING OUT VERY LONG PATH NAMES. When generating an export filename that includes subdirectory generation, hydrus will clip those subdirs so everything fits reasonable below the system path limit. This value forces the per-dirname to never be longer than this. On Windows, this means characters, on Linux/macOS, it means bytes (when encoding unicode characters). This stuff can get complicated, so be careful changing it too much! Most OS filesystems do not accept a directory name longer than 256 chars/bytes, but you should leave a little padding for surprises, and of course you will want some space for a filename too.'
            self._export_dirname_character_limit.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            self._export_path_character_limit = ClientGUICommon.NoneableSpinCtrl( self, 250, none_phrase = 'let hydrus decide', min = 96, max = 8192 )
            tt = 'When generating an export filename, hydrus will clip the generated subdirectories and filename so they fit into the system path limit. This value overrides that limit. On Windows, this means characters, on Linux/macOS, it means bytes (when encoding unicode characters). This stuff can get complicated, so be careful changing it too much! Most OS filesystems do not accept a directory name longer than 256 chars/bytes, but you should leave a little padding for surprises. Also, on Windows, the entire path typically also has to be shorter than 256 characters total, so do not go crazy here unless you know what you are doing! (Linux is usually 4096; macOS 1024.)'
            self._export_path_character_limit.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            self._export_filename_character_limit = ClientGUICommon.BetterSpinBox( self._exports_panel, min = 16, max = 8192 )
            tt = 'When generating an export filename, hydrus will clip the output so it is not longer than this. On Windows, this means characters, on Linux/macOS, it means bytes (when encoding unicode characters). This stuff can get complicated, so be careful changing it too much! Most OS filesystems do not accept a filename longer than 256 chars/bytes, but you should leave a little padding for stuff like sidecar suffixes and other surprises. If you have a Linux folder using eCryptFS, the filename limit is around 140 bytes, which with sophisticated unicode output can be really short. On Windows, the entire path typically also has to be shorter than 256 characters total! (Linux is usually 4096; macOS 1024.)'
            self._export_filename_character_limit.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            self._dnd_panel = ClientGUICommon.StaticBox( self, 'drag and drop' )
            
            # TODO: Yo, make the 50 files/200MB thresholds options of their own with warnings about lag!
            # ALSO do gubbins where the temp folder stuff is fired if ctrl is held down or something, otherwise no export and hash filenames
            
            self._discord_dnd_fix = QW.QCheckBox( self._dnd_panel )
            self._discord_dnd_fix.setToolTip( ClientGUIFunctions.WrapToolTip( 'This makes small file drag-and-drops a little laggier in exchange for Discord support. It also lets you set custom filenames for drag and drop exports.' ) )
            
            self._discord_dnd_filename_pattern = QW.QLineEdit( self._dnd_panel )
            self._discord_dnd_filename_pattern.setToolTip( ClientGUIFunctions.WrapToolTip( 'When you put your DnD files in your temp folder, we have a chance to rename them. This export phrase will do that. If no filename can be generated, hash will be used instead.' ) )
            
            self._export_pattern_button = ClientGUICommon.ExportPatternButton( self._dnd_panel )
            
            self._secret_discord_dnd_fix = QW.QCheckBox( self._dnd_panel )
            self._secret_discord_dnd_fix.setToolTip( ClientGUIFunctions.WrapToolTip( 'THIS SOMETIMES FIXES DnD FOR WEIRD PROGRAMS, BUT IT ALSO OFTEN BREAKS IT FOR OTHERS.\n\nBecause of weird security/permission issues, a program will sometimes not accept a drag and drop file export from hydrus unless the DnD is set to "move" rather than "copy" (discord has done this for some people). Since we do not want to let you accidentally move your files out of your primary file store, this is only enabled if you are copying the files in question to your temp folder first!' ) )
            
            self._export_folder_panel = ClientGUICommon.StaticBox( self, 'export folder' )
            
            self._export_location = QP.DirPickerCtrl( self._export_folder_panel )
            
            #
            
            self._new_options = CG.client_controller.new_options
            
            self._discord_dnd_fix.setChecked( self._new_options.GetBoolean( 'discord_dnd_fix' ) )
            
            self._discord_dnd_filename_pattern.setText( self._new_options.GetString( 'discord_dnd_filename_pattern' ) )
            
            self._secret_discord_dnd_fix.setChecked( self._new_options.GetBoolean( 'secret_discord_dnd_fix' ) )
            
            if HC.options[ 'export_path' ] is not None:
                
                abs_path = HydrusPaths.ConvertPortablePathToAbsPath( HC.options[ 'export_path' ] )
                
                if abs_path is not None:
                    
                    self._export_location.SetPath( abs_path )
                    
                
            
            self._always_apply_ntfs_export_filename_rules.setChecked( self._new_options.GetBoolean( 'always_apply_ntfs_export_filename_rules' ) )
            
            self._export_path_character_limit.SetValue( self._new_options.GetNoneableInteger( 'export_path_character_limit' ) )
            self._export_dirname_character_limit.SetValue( self._new_options.GetNoneableInteger( 'export_dirname_character_limit' ) )
            self._export_filename_character_limit.setValue( self._new_options.GetInteger( 'export_filename_character_limit' ) )
            
            #
            
            rows = []
            
            rows.append( ( 'ADVANCED: Always apply NTFS filename rules to export filenames: ', self._always_apply_ntfs_export_filename_rules ) )
            rows.append( ( 'ADVANCED: Export path length limit (characters/bytes): ', self._export_path_character_limit ) )
            rows.append( ( 'ADVANCED: Export dirname length limit (characters/bytes): ', self._export_dirname_character_limit ) )
            rows.append( ( 'ADVANCED: Export filename length limit (characters/bytes): ', self._export_filename_character_limit ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self._exports_panel, rows )
            
            self._exports_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            rows = []
            
            rows.append( ( 'Copy files to temp folder for drag-and-drop (works for <=50, <200MB file DnDs--fixes Discord!): ', self._discord_dnd_fix ) )
            rows.append( ( 'BUGFIX: Set drag-and-drops to have a "move" flag: ', self._secret_discord_dnd_fix ) )
            rows.append( ( 'Drag-and-drop export filename pattern: ', self._discord_dnd_filename_pattern ) )
            rows.append( ( '', self._export_pattern_button ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self._dnd_panel, rows )
            
            label = 'You can drag-and-drop a selection of files out of the client to quickly copy-export them to a folder or an external program (include web browser upload boxes).'
            
            if HC.PLATFORM_WINDOWS:
                
                label += '\n\nNote, however, that Windows will generally be unhappy about DnDs between two programs where one is in admin mode and the other not. In this case, you will want to export to a neutral folder like your Desktop and then do a second drag from there to your destination program.'
                
            
            st = ClientGUICommon.BetterStaticText( self._dnd_panel, label = label )
            
            st.setWordWrap( True )
            
            self._dnd_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            self._dnd_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            rows = []
            
            rows.append( ( 'Default export directory: ', self._export_location ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self._export_folder_panel, rows )
            
            self._export_folder_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, self._exports_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            QP.AddToLayout( vbox, self._dnd_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            QP.AddToLayout( vbox, self._export_folder_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            vbox.addStretch( 0 )
            
            self.setLayout( vbox )
            
            self._discord_dnd_fix.clicked.connect( self._UpdateDnDFilenameEnabled )
            
            self._UpdateDnDFilenameEnabled()
            
        
        def _UpdateDnDFilenameEnabled( self ):
            
            enabled = self._discord_dnd_fix.isChecked()
            
            self._discord_dnd_filename_pattern.setEnabled( enabled )
            self._export_pattern_button.setEnabled( enabled )
            self._secret_discord_dnd_fix.setEnabled( enabled )
            
        
        def UpdateOptions( self ):
            
            self._new_options.SetBoolean( 'always_apply_ntfs_export_filename_rules', self._always_apply_ntfs_export_filename_rules.isChecked() )
            self._new_options.SetNoneableInteger( 'export_path_character_limit', self._export_path_character_limit.GetValue() )
            self._new_options.SetNoneableInteger( 'export_dirname_character_limit', self._export_dirname_character_limit.GetValue() )
            self._new_options.SetInteger( 'export_filename_character_limit', self._export_filename_character_limit.value() )
            
            self._new_options.SetBoolean( 'discord_dnd_fix', self._discord_dnd_fix.isChecked() )
            self._new_options.SetString( 'discord_dnd_filename_pattern', self._discord_dnd_filename_pattern.text() )
            self._new_options.SetBoolean( 'secret_discord_dnd_fix', self._secret_discord_dnd_fix.isChecked() )
            
            path = str( self._export_location.GetPath() ).strip()
            
            if path != '':
                
                HC.options[ 'export_path' ] = HydrusPaths.ConvertAbsPathToPortablePath( self._export_location.GetPath() )
                
            else:
                
                HC.options[ 'export_path' ] = None
                
            
        
    
    class _ExternalProgramsPanel( OptionsPagePanel ):
        
        def __init__( self, parent ):
            
            super().__init__( parent )
            
            self._new_options = CG.client_controller.new_options
            
            browser_panel = ClientGUICommon.StaticBox( self, 'web browser launch path' )
            
            self._web_browser_path = QW.QLineEdit( browser_panel )
            
            web_browser_path = self._new_options.GetNoneableString( 'web_browser_path' )
            
            if web_browser_path is not None:
                
                self._web_browser_path.setText( web_browser_path )
                
            
            #
            
            mime_panel = ClientGUICommon.StaticBox( self, '\'open externally\' launch paths' )
            
            model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_EXTERNAL_PROGRAMS.ID, self._ConvertMimeToDisplayTuple, self._ConvertMimeToSortTuple )
            
            self._mime_launch_listctrl = ClientGUIListCtrl.BetterListCtrlTreeView( mime_panel, 15, model, activation_callback = self._EditMimeLaunch )
            
            for mime in HC.SEARCHABLE_MIMES:
                
                launch_path = self._new_options.GetMimeLaunch( mime )
                
                row = ( mime, launch_path )
                
                self._mime_launch_listctrl.AddData( row )
                
            
            self._mime_launch_listctrl.Sort()
            
            #
            
            vbox = QP.VBoxLayout()
            
            text = 'By default, when you ask to open a URL, hydrus will send it to your OS, and that figures out what your "default" web browser is. These OS launch commands can be buggy, though, and sometimes drop #anchor components. If this happens to you, set the specific launch command for your web browser here.'
            text += '\n' * 2
            text += 'The command here must include a "%path%" component, normally ideally within those quote marks, which is where hydrus will place the URL when it executes the command. A good example would be:'
            text += '\n' * 2
            
            if HC.PLATFORM_WINDOWS:
                
                text += 'C:\\program files\\firefox\\firefox.exe "%path%"'
                
            elif HC.PLATFORM_MACOS:
                
                text += 'open -a /Applications/Firefox.app -g "%path%"'
                
            else:
                
                text += 'firefox "%path%"'
                
            
            st = ClientGUICommon.BetterStaticText( browser_panel, text )
            st.setWordWrap( True )
            
            browser_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            rows = []
            
            rows.append( ( 'Manual web browser launch command: ', self._web_browser_path ) )
            
            gridbox = ClientGUICommon.WrapInGrid( mime_panel, rows )
            
            browser_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            vbox = QP.VBoxLayout()
            
            text = 'Similarly, when you ask to open a file "externally", hydrus will send it to your OS, and that figures out your "default" program. This may fail or direct to a program you do not want for several reasons, so you can set a specific override here.'
            text += '\n' * 2
            text += 'Again, make sure you include the "%path%" component. Most programs are going to be like \'program_exe "%path%"\', but some may need a profile switch or "-o" open command or similar.'
            
            st = ClientGUICommon.BetterStaticText( mime_panel, text )
            st.setWordWrap( True )
            
            mime_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            mime_panel.Add( self._mime_launch_listctrl, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            #
            
            QP.AddToLayout( vbox, browser_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, mime_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            self.setLayout( vbox )
            
        
        def _ConvertMimeToDisplayTuple( self, data ):
            
            ( mime, launch_path ) = data
            
            pretty_mime = HC.mime_string_lookup[ mime ]
            
            if launch_path is None:
                
                pretty_launch_path = 'default: {}'.format( HydrusPaths.GetDefaultLaunchPath() )
                
            else:
                
                pretty_launch_path = launch_path
                
            
            display_tuple = ( pretty_mime, pretty_launch_path )
            
            return display_tuple
            
        
        _ConvertMimeToSortTuple = _ConvertMimeToDisplayTuple
        
        def _EditMimeLaunch( self ):
            
            row = self._mime_launch_listctrl.GetTopSelectedData()
            
            if row is None:
                
                return
                
            
            ( mime, launch_path ) = row
            
            message = 'Enter the new launch path for {}'.format( HC.mime_string_lookup[ mime ] )
            message += '\n' * 2
            message += 'Hydrus will insert the file\'s full path wherever you put %path%, even multiple times!'
            message += '\n' * 2
            message += 'Set as blank to reset to default.'
            
            if launch_path is None:
                
                default = 'program "%path%"'
                
            else:
                
                default = launch_path
                
            
            try:
                
                new_launch_path = ClientGUIDialogsQuick.EnterText( self, message, default = default, allow_blank = True )
                
            except HydrusExceptions.CancelledException:
                
                return
                
            
            if new_launch_path == '':
                
                new_launch_path = None
                
            
            if new_launch_path not in ( launch_path, default ):
                
                if new_launch_path is not None and '%path%' not in new_launch_path:
                    
                    message = f'Hey, your command "{new_launch_path}" did not include %path%--it probably is not going to work! Are you sure this is ok?'
                    
                    result = ClientGUIDialogsQuick.GetYesNo( self, message )
                    
                    if result != QW.QDialog.DialogCode.Accepted:
                        
                        return
                        
                    
                
                edited_row = ( mime, new_launch_path )
                
                self._mime_launch_listctrl.ReplaceData( row, edited_row, sort_and_scroll = True )
                
            
        
        def UpdateOptions( self ):
            
            web_browser_path = self._web_browser_path.text()
            
            if web_browser_path == '':
                
                web_browser_path = None
                
            
            self._new_options.SetNoneableString( 'web_browser_path', web_browser_path )
            
            for ( mime, launch_path ) in self._mime_launch_listctrl.GetData():
                
                self._new_options.SetMimeLaunch( mime, launch_path )
                
            
        
    
    class _FilesAndTrashPanel( OptionsPagePanel ):
        
        def __init__( self, parent ):
            
            super().__init__( parent )
            
            self._new_options = CG.client_controller.new_options
            
            self._prefix_hash_when_copying = QW.QCheckBox( self )
            self._prefix_hash_when_copying.setToolTip( ClientGUIFunctions.WrapToolTip( 'If you often paste hashes into boorus, check this to automatically prefix with the type, like "md5:2496dabcbd69e3c56a5d8caabb7acde5".' ) )
            
            self._delete_to_recycle_bin = QW.QCheckBox( self )
            
            self._ms_to_wait_between_physical_file_deletes = ClientGUITime.TimeDeltaWidget( self, min = 0.02, days = False, hours = False, minutes = False, seconds = True, milliseconds = True )
            tt = 'Deleting a file from a hard disk can be resource expensive, so when files leave the trash, the actual physical file delete happens later, in the background. The operation is spread out so as not to give you lag spikes.'
            self._ms_to_wait_between_physical_file_deletes.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            self._confirm_trash = QW.QCheckBox( self )
            self._confirm_archive = QW.QCheckBox( self )
            
            self._confirm_multiple_local_file_services_copy = QW.QCheckBox( self )
            self._confirm_multiple_local_file_services_move = QW.QCheckBox( self )
            
            self._only_show_delete_from_all_local_domains_when_filtering = QW.QCheckBox( self )
            tt = 'When you finish filtering, if the files you chose to delete are in multiple local file domains, you are usually given the option of where you want to delete them from. If you always want to delete them from all locations and do not want the more complicated confirmation dialog, check this.'
            self._only_show_delete_from_all_local_domains_when_filtering.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            self._remove_filtered_files = QW.QCheckBox( self )
            self._remove_filtered_files.setToolTip( ClientGUIFunctions.WrapToolTip( 'This will remove all archived/deleted files from the source thumbnail page when you commit your archive/delete filter run.' ) )
            
            self._remove_filtered_files_even_when_skipped = QW.QCheckBox( self )
            self._remove_trashed_files = QW.QCheckBox( self )
            self._remove_local_domain_moved_files = QW.QCheckBox( self )
            
            # TODO: replace these with a new(?) noneabletimedelta and noneablebytesguy
            self._trash_max_age = ClientGUICommon.NoneableSpinCtrl( self, 72, none_phrase = 'no age limit', min = 0, max = 8640 )
            self._trash_max_size = ClientGUICommon.NoneableSpinCtrl( self, 2048, none_phrase = 'no size limit', min = 0, max = 20480 )
            
            self._do_not_do_chmod_mode = QW.QCheckBox( self )
            self._do_not_do_chmod_mode.setToolTip( ClientGUIFunctions.WrapToolTip( 'CAREFUL. When hydrus copies files around, it preserves or sets permission bits. If you are on ACL-backed storage, e.g. via NFSv4 with ACL set, chmod is going to raise errors and/or audit logspam. You can try stopping all chmod here--hydrus will use differing copy calls that only copy the file contents and try to preserve access/modified times.' ) )
            
            delete_lock_panel = ClientGUICommon.StaticBox( self, 'delete lock' )
            
            self._delete_lock_for_archived_files = QW.QCheckBox( delete_lock_panel )
            self._delete_lock_for_archived_files.setToolTip( ClientGUIFunctions.WrapToolTip( 'This will stop the client from physically deleting anything you have archived. You can still trash such files, but they cannot go further. It is a last-ditch catch to rescue accidentally deleted good files.' ) )
            
            self._delete_lock_reinbox_deletees_after_archive_delete = QW.QCheckBox( delete_lock_panel )
            self._delete_lock_reinbox_deletees_after_archive_delete.setToolTip( ClientGUIFunctions.WrapToolTip( 'Be careful with this!\n\nIf the delete lock is on, and you do an archive/delete filter, this will ensure that all deletee files are inboxed before being deleted.' ) )
            
            self._delete_lock_reinbox_deletees_after_duplicate_filter = QW.QCheckBox( delete_lock_panel )
            self._delete_lock_reinbox_deletees_after_duplicate_filter.setToolTip( ClientGUIFunctions.WrapToolTip( 'Be careful with this!\n\nIf the delete lock is on, and you do a duplicate filter, this will ensure that all file delese you manually trigger and all file deletees that come from merge options are inboxed before being deleted.' ) )
            
            self._delete_lock_reinbox_deletees_in_auto_resolution = QW.QCheckBox( delete_lock_panel )
            self._delete_lock_reinbox_deletees_in_auto_resolution.setToolTip( ClientGUIFunctions.WrapToolTip( 'Be careful with this!\n\nIf the delete lock is on, any auto-resolution rule action, semi-automatic or automatic, will ensure that all deletee files from merge options are inboxed before being deleted.' ) )
            
            advanced_file_deletion_panel = ClientGUICommon.StaticBox( self, 'advanced file deletion and custom reasons' )
            
            self._use_advanced_file_deletion_dialog = QW.QCheckBox( advanced_file_deletion_panel )
            self._use_advanced_file_deletion_dialog.setToolTip( ClientGUIFunctions.WrapToolTip( 'If this is set, the client will present a more complicated file deletion confirmation dialog that will permit you to set your own deletion reason and perform \'clean\' deletes that leave no deletion record (making later re-import easier).' ) )
            
            self._remember_last_advanced_file_deletion_special_action = QW.QCheckBox( advanced_file_deletion_panel )
            self._remember_last_advanced_file_deletion_special_action.setToolTip( ClientGUIFunctions.WrapToolTip( 'This will try to remember and restore the last action you set, whether that was trash, physical delete, or physical delete and clear history.') )
            
            self._remember_last_advanced_file_deletion_reason = QW.QCheckBox( advanced_file_deletion_panel )
            self._remember_last_advanced_file_deletion_reason.setToolTip( ClientGUIFunctions.WrapToolTip( 'This will remember and restore the last reason you set for a delete.' ) )
            
            self._advanced_file_deletion_reasons = ClientGUIListBoxes.QueueListBox( advanced_file_deletion_panel, 5, str, add_callable = self._AddAFDR, edit_callable = self._EditAFDR )
            
            #
            
            self._prefix_hash_when_copying.setChecked( self._new_options.GetBoolean( 'prefix_hash_when_copying' ) )
            
            self._delete_to_recycle_bin.setChecked( HC.options[ 'delete_to_recycle_bin' ] )
            
            self._ms_to_wait_between_physical_file_deletes.SetValue( HydrusTime.SecondiseMSFloat( self._new_options.GetInteger( 'ms_to_wait_between_physical_file_deletes' ) ) )
            
            self._confirm_trash.setChecked( HC.options[ 'confirm_trash' ] )
            tt = 'If there is only one place to delete the file from, you will get no delete dialog--it will just be deleted immediately. Applies the same way to undelete.'
            self._confirm_trash.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            self._confirm_archive.setChecked( HC.options[ 'confirm_archive' ] )
            
            self._confirm_multiple_local_file_services_copy.setChecked( self._new_options.GetBoolean( 'confirm_multiple_local_file_services_copy' ) )
            self._confirm_multiple_local_file_services_move.setChecked( self._new_options.GetBoolean( 'confirm_multiple_local_file_services_move' ) )
            
            self._only_show_delete_from_all_local_domains_when_filtering.setChecked( self._new_options.GetBoolean( 'only_show_delete_from_all_local_domains_when_filtering' ) )
            
            self._remove_filtered_files.setChecked( HC.options[ 'remove_filtered_files' ] )
            self._remove_filtered_files_even_when_skipped.setChecked( self._new_options.GetBoolean( 'remove_filtered_files_even_when_skipped' ) )
            self._remove_trashed_files.setChecked( HC.options[ 'remove_trashed_files' ] )
            self._remove_local_domain_moved_files.setChecked( self._new_options.GetBoolean( 'remove_local_domain_moved_files' ) )
            self._trash_max_age.SetValue( HC.options[ 'trash_max_age' ] )
            self._trash_max_size.SetValue( HC.options[ 'trash_max_size' ] )
            
            self._do_not_do_chmod_mode.setChecked( self._new_options.GetBoolean( 'do_not_do_chmod_mode' ) )
            
            self._delete_lock_for_archived_files.setChecked( self._new_options.GetBoolean( 'delete_lock_for_archived_files' ) )
            self._delete_lock_reinbox_deletees_after_archive_delete.setChecked( self._new_options.GetBoolean( 'delete_lock_reinbox_deletees_after_archive_delete' ) )
            self._delete_lock_reinbox_deletees_after_duplicate_filter.setChecked( self._new_options.GetBoolean( 'delete_lock_reinbox_deletees_after_duplicate_filter' ) )
            self._delete_lock_reinbox_deletees_in_auto_resolution.setChecked( self._new_options.GetBoolean( 'delete_lock_reinbox_deletees_in_auto_resolution' ) )
            
            self._use_advanced_file_deletion_dialog.setChecked( self._new_options.GetBoolean( 'use_advanced_file_deletion_dialog' ) )
            
            self._remember_last_advanced_file_deletion_special_action.setChecked( CG.client_controller.new_options.GetBoolean( 'remember_last_advanced_file_deletion_special_action' ) )
            self._remember_last_advanced_file_deletion_reason.setChecked( CG.client_controller.new_options.GetBoolean( 'remember_last_advanced_file_deletion_reason' ) )
            
            self._advanced_file_deletion_reasons.AddDatas( self._new_options.GetStringList( 'advanced_file_deletion_reasons' ) )
            
            #
            
            vbox = QP.VBoxLayout()
            
            text = 'If you set the default export directory blank, the client will use \'hydrus_export\' under the current user\'s home directory.'
            
            QP.AddToLayout( vbox, ClientGUICommon.BetterStaticText(self,text), CC.FLAGS_CENTER )
            
            rows = []
            
            rows.append( ( 'When copying file hashes, prefix with booru-friendly hash type: ', self._prefix_hash_when_copying ) )
            rows.append( ( 'Confirm sending files to trash: ', self._confirm_trash ) )
            rows.append( ( 'Confirm sending more than one file to archive or inbox: ', self._confirm_archive ) )
            rows.append( ( 'Confirm when copying files across local file services: ', self._confirm_multiple_local_file_services_copy ) )
            rows.append( ( 'Confirm when moving files across local file services: ', self._confirm_multiple_local_file_services_move ) )
            rows.append( ( 'When physically deleting files or folders, send them to the OS\'s recycle bin: ', self._delete_to_recycle_bin ) )
            rows.append( ( 'When maintenance physically deletes files, wait this long between each delete: ', self._ms_to_wait_between_physical_file_deletes ) )
            rows.append( ( 'When finishing filtering, always delete from all possible domains: ', self._only_show_delete_from_all_local_domains_when_filtering ) )
            rows.append( ( 'Remove files from view when they are archive/delete filtered: ', self._remove_filtered_files ) )
            rows.append( ( '--even skipped files: ', self._remove_filtered_files_even_when_skipped ) )
            rows.append( ( 'Remove files from view when they are sent to the trash: ', self._remove_trashed_files ) )
            rows.append( ( 'Remove files from view when they are moved to another local file domain: ', self._remove_local_domain_moved_files ) )
            rows.append( ( 'Number of hours a file can be in the trash before being deleted: ', self._trash_max_age ) )
            rows.append( ( 'Maximum size of trash (MB): ', self._trash_max_size ) )
            rows.append( ( 'ADVANCED: Do not do chmod when copying files', self._do_not_do_chmod_mode ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self, rows )
            
            QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            rows = []
            
            rows.append( ( 'Do not permit archived files to be deleted from the trash: ', self._delete_lock_for_archived_files ) )
            rows.append( ( 'After archive/delete filter, ensure deletees are inboxed before delete: ', self._delete_lock_reinbox_deletees_after_archive_delete ) )
            rows.append( ( 'After duplicate filter, ensure deletees are inboxed before delete: ', self._delete_lock_reinbox_deletees_after_duplicate_filter ) )
            rows.append( ( 'In duplicates auto-resolution, ensure deletees are inboxed before delete: ', self._delete_lock_reinbox_deletees_in_auto_resolution ) )
            
            gridbox = ClientGUICommon.WrapInGrid( delete_lock_panel, rows )
            
            delete_lock_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            QP.AddToLayout( vbox, delete_lock_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            #
            
            rows = []
            
            rows.append( ( 'Use the advanced file deletion dialog: ', self._use_advanced_file_deletion_dialog ) )
            rows.append( ( 'Remember the last action: ', self._remember_last_advanced_file_deletion_special_action ) )
            rows.append( ( 'Remember the last reason: ', self._remember_last_advanced_file_deletion_reason ) )
            
            gridbox = ClientGUICommon.WrapInGrid( advanced_file_deletion_panel, rows )
            
            advanced_file_deletion_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            advanced_file_deletion_panel.Add( self._advanced_file_deletion_reasons, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            #
            
            QP.AddToLayout( vbox, advanced_file_deletion_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            self.setLayout( vbox )
            
            self._delete_lock_for_archived_files.clicked.connect( self._UpdateLockControls )
            
            self._remove_filtered_files.clicked.connect( self._UpdateRemoveFiltered )
            
            self._use_advanced_file_deletion_dialog.clicked.connect( self._UpdateAdvancedControls )
            
            self._UpdateLockControls()
            self._UpdateRemoveFiltered()
            self._UpdateAdvancedControls()
            
        
        def _AddAFDR( self ):
            
            reason = 'I do not like the file.'
            
            return self._EditAFDR( reason )
            
        
        def _EditAFDR( self, reason ):
            
            try:
                
                reason = ClientGUIDialogsQuick.EnterText( self, 'Enter the reason', default = reason )
                
            except HydrusExceptions.CancelledException:
                
                raise
                
            
            return reason
            
        
        def _UpdateAdvancedControls( self ):
            
            advanced_enabled = self._use_advanced_file_deletion_dialog.isChecked()
            
            self._remember_last_advanced_file_deletion_special_action.setEnabled( advanced_enabled )
            self._remember_last_advanced_file_deletion_reason.setEnabled( advanced_enabled )
            self._advanced_file_deletion_reasons.setEnabled( advanced_enabled )
            
        
        def _UpdateRemoveFiltered( self ):
            
            self._remove_filtered_files_even_when_skipped.setEnabled( self._remove_filtered_files.isChecked() )
            
        
        def _UpdateLockControls( self ):
            
            self._delete_lock_reinbox_deletees_after_archive_delete.setEnabled( self._delete_lock_for_archived_files.isChecked() )
            self._delete_lock_reinbox_deletees_after_duplicate_filter.setEnabled( self._delete_lock_for_archived_files.isChecked() )
            self._delete_lock_reinbox_deletees_in_auto_resolution.setEnabled( self._delete_lock_for_archived_files.isChecked() )
            
        
        def UpdateOptions( self ):
            
            self._new_options.SetBoolean( 'prefix_hash_when_copying', self._prefix_hash_when_copying.isChecked() )
            
            HC.options[ 'delete_to_recycle_bin' ] = self._delete_to_recycle_bin.isChecked()
            HC.options[ 'confirm_trash' ] = self._confirm_trash.isChecked()
            HC.options[ 'confirm_archive' ] = self._confirm_archive.isChecked()
            HC.options[ 'remove_filtered_files' ] = self._remove_filtered_files.isChecked()
            self._new_options.SetBoolean( 'remove_filtered_files_even_when_skipped', self._remove_filtered_files_even_when_skipped.isChecked() )
            HC.options[ 'remove_trashed_files' ] = self._remove_trashed_files.isChecked()
            self._new_options.SetBoolean( 'remove_local_domain_moved_files', self._remove_local_domain_moved_files.isChecked() )
            HC.options[ 'trash_max_age' ] = self._trash_max_age.GetValue()
            HC.options[ 'trash_max_size' ] = self._trash_max_size.GetValue()
            
            self._new_options.SetBoolean( 'do_not_do_chmod_mode', self._do_not_do_chmod_mode.isChecked() )
            
            self._new_options.SetBoolean( 'only_show_delete_from_all_local_domains_when_filtering', self._only_show_delete_from_all_local_domains_when_filtering.isChecked() )
            
            self._new_options.SetInteger( 'ms_to_wait_between_physical_file_deletes', HydrusTime.MillisecondiseS( self._ms_to_wait_between_physical_file_deletes.GetValue() ) )
            
            self._new_options.SetBoolean( 'confirm_multiple_local_file_services_copy', self._confirm_multiple_local_file_services_copy.isChecked() )
            self._new_options.SetBoolean( 'confirm_multiple_local_file_services_move', self._confirm_multiple_local_file_services_move.isChecked() )
            
            self._new_options.SetBoolean( 'delete_lock_for_archived_files', self._delete_lock_for_archived_files.isChecked() )
            self._new_options.SetBoolean( 'delete_lock_reinbox_deletees_after_archive_delete', self._delete_lock_reinbox_deletees_after_archive_delete.isChecked() )
            self._new_options.SetBoolean( 'delete_lock_reinbox_deletees_after_duplicate_filter', self._delete_lock_reinbox_deletees_after_duplicate_filter.isChecked() )
            self._new_options.SetBoolean( 'delete_lock_reinbox_deletees_in_auto_resolution', self._delete_lock_reinbox_deletees_in_auto_resolution.isChecked() )
            
            self._new_options.SetBoolean( 'use_advanced_file_deletion_dialog', self._use_advanced_file_deletion_dialog.isChecked() )
            
            self._new_options.SetStringList( 'advanced_file_deletion_reasons', self._advanced_file_deletion_reasons.GetData() )
            
            CG.client_controller.new_options.SetBoolean( 'remember_last_advanced_file_deletion_special_action', self._remember_last_advanced_file_deletion_special_action.isChecked() )
            CG.client_controller.new_options.SetBoolean( 'remember_last_advanced_file_deletion_reason', self._remember_last_advanced_file_deletion_reason.isChecked() )
            
        
    
    class _FileSearchPanel( OptionsPagePanel ):
        
        def __init__( self, parent, new_options ):
            
            super().__init__( parent )
            
            self._new_options = new_options
            
            #
            
            self._read_autocomplete_panel = ClientGUICommon.StaticBox( self, 'file search autocomplete' )
            
            location_context = self._new_options.GetDefaultLocalLocationContext()
            
            self._default_local_location_context = ClientGUILocation.LocationSearchContextButton( self._read_autocomplete_panel, location_context )
            self._default_local_location_context.setToolTip( ClientGUIFunctions.WrapToolTip( 'This initialised into a bunch of dialogs across the program as a fallback. You can probably leave it alone forever, but if you delete or move away from \'my files\' as your main place to do work, please update it here.' ) )
            
            self._default_local_location_context.SetOnlyImportableDomainsAllowed( True )
            
            self._default_tag_service_search_page = ClientGUICommon.BetterChoice( self._read_autocomplete_panel )
            
            self._default_search_synchronised = QW.QCheckBox( self._read_autocomplete_panel )
            tt = 'This refers to the button on the autocomplete dropdown that enables new searches to start. If this is on, then new search pages will search as soon as you enter the first search predicate. If off, no search will happen until you switch it back on.'
            self._default_search_synchronised.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            self._autocomplete_float_main_gui = QW.QCheckBox( self._read_autocomplete_panel )
            tt = 'The autocomplete dropdown can either \'float\' on top of the main window, or if that does not work well for you, it can embed into the parent page panel.'
            self._autocomplete_float_main_gui.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            self._ac_read_list_height_num_chars = ClientGUICommon.BetterSpinBox( self._read_autocomplete_panel, min = 1, max = 128 )
            
            self._show_system_everything = QW.QCheckBox( self._read_autocomplete_panel )
            tt = 'After users get some experience with the program and a larger collection, they tend to have less use for system:everything.'
            self._show_system_everything.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            #
            
            misc_panel = ClientGUICommon.StaticBox( self, 'file search' )
            
            self._forced_search_limit = ClientGUICommon.NoneableSpinCtrl( misc_panel, 10000, min = 1, max = 100000000 )
            self._forced_search_limit.setToolTip( ClientGUIFunctions.WrapToolTip( 'This is overruled if you set an explicit system:limit larger than it.' ) )
            
            self._refresh_search_page_on_system_limited_sort_changed = QW.QCheckBox( misc_panel )
            tt = 'This is a fairly advanced option. It only fires if the sort is simple enough for the database to do the limited sort. Some people like it, some do not. If you turn it on and _do_ want to sort a limited set by a different sort, hit "searching immediately" to pause search updates.'
            self._refresh_search_page_on_system_limited_sort_changed.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            #
            
            self._default_tag_service_search_page.addItem( 'all known tags', CC.COMBINED_TAG_SERVICE_KEY )
            
            services = CG.client_controller.services_manager.GetServices( HC.REAL_TAG_SERVICES )
            
            for service in services:
                
                self._default_tag_service_search_page.addItem( service.GetName(), service.GetServiceKey() )
                
            
            self._default_tag_service_search_page.SetValue( self._new_options.GetKey( 'default_tag_service_search_page' ) )
            
            self._default_search_synchronised.setChecked( self._new_options.GetBoolean( 'default_search_synchronised' ) )
            
            self._autocomplete_float_main_gui.setChecked( self._new_options.GetBoolean( 'autocomplete_float_main_gui' ) )
            
            self._ac_read_list_height_num_chars.setValue( self._new_options.GetInteger( 'ac_read_list_height_num_chars' ) )
            
            self._show_system_everything.setChecked( self._new_options.GetBoolean( 'show_system_everything' ) )
            
            self._forced_search_limit.SetValue( self._new_options.GetNoneableInteger( 'forced_search_limit' ) )
            
            self._refresh_search_page_on_system_limited_sort_changed.setChecked( self._new_options.GetBoolean( 'refresh_search_page_on_system_limited_sort_changed' ) )
            
            #
            
            message = 'This tag autocomplete appears in file search pages and other places where you use tags and system predicates to search for files.'
            
            st = ClientGUICommon.BetterStaticText( self._read_autocomplete_panel, label = message )
            
            self._read_autocomplete_panel.Add( st, CC.FLAGS_CENTER )
            
            rows = []
            
            rows.append( ( 'Default/Fallback local file search location: ', self._default_local_location_context ) )
            rows.append( ( 'Default tag service in search pages: ', self._default_tag_service_search_page ) )
            rows.append( ( 'Autocomplete dropdown floats over file search pages: ', self._autocomplete_float_main_gui ) )
            rows.append( ( 'Autocomplete list height: ', self._ac_read_list_height_num_chars ) )
            rows.append( ( 'Start new search pages in \'searching immediately\': ', self._default_search_synchronised ) )
            rows.append( ( 'Show system:everything: ', self._show_system_everything ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self._read_autocomplete_panel, rows )
            
            self._read_autocomplete_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            
            #
            
            rows = []
            
            rows.append( ( 'Implicit system:limit for all searches: ', self._forced_search_limit ) )
            rows.append( ( 'If explicit system:limit, then refresh search when file sort changes: ', self._refresh_search_page_on_system_limited_sort_changed ) )
            
            gridbox = ClientGUICommon.WrapInGrid( misc_panel, rows )
            
            misc_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, self._read_autocomplete_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, misc_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.addStretch( 0 )
            
            self.setLayout( vbox )
            
        
        def UpdateOptions( self ):
            
            self._new_options.SetKey( 'default_tag_service_search_page', self._default_tag_service_search_page.GetValue() )
            
            self._new_options.SetDefaultLocalLocationContext( self._default_local_location_context.GetValue() )
            
            self._new_options.SetBoolean( 'default_search_synchronised', self._default_search_synchronised.isChecked() )
            
            self._new_options.SetBoolean( 'autocomplete_float_main_gui', self._autocomplete_float_main_gui.isChecked() )
            
            self._new_options.SetInteger( 'ac_read_list_height_num_chars', self._ac_read_list_height_num_chars.value() )
            
            self._new_options.SetBoolean( 'show_system_everything', self._show_system_everything.isChecked() )
            
            self._new_options.SetNoneableInteger( 'forced_search_limit', self._forced_search_limit.GetValue() )
            
            self._new_options.SetBoolean( 'refresh_search_page_on_system_limited_sort_changed', self._refresh_search_page_on_system_limited_sort_changed.isChecked() )
            
        
    
    class _FileSortCollectPanel( OptionsPagePanel ):
        
        def __init__( self, parent, new_options ):
            
            super().__init__( parent )
            
            self._new_options = new_options
            
            self._file_sort_panel = ClientGUICommon.StaticBox( self, 'file sort' )
            
            default_sort = self._new_options.GetDefaultSort()
            
            self._default_media_sort = ClientGUIMediaResultsPanelSortCollect.MediaSortControl( self._file_sort_panel, media_sort = default_sort )
            
            if self._default_media_sort.GetSort() != default_sort:
                
                media_sort = ClientMedia.MediaSort( ( 'system', CC.SORT_FILES_BY_FILESIZE ), CC.SORT_ASC )
                
                self._default_media_sort.SetSort( media_sort )
                
            
            fallback_sort = self._new_options.GetFallbackSort()
            
            self._fallback_media_sort = ClientGUIMediaResultsPanelSortCollect.MediaSortControl( self._file_sort_panel, media_sort = fallback_sort )
            
            if self._fallback_media_sort.GetSort() != fallback_sort:
                
                media_sort = ClientMedia.MediaSort( ( 'system', CC.SORT_FILES_BY_IMPORT_TIME ), CC.SORT_ASC )
                
                self._fallback_media_sort.SetSort( media_sort )
                
            
            self._save_page_sort_on_change = QW.QCheckBox( self._file_sort_panel )
            
            self._default_media_collect = ClientGUIMediaResultsPanelSortCollect.MediaCollectControl( self._file_sort_panel )
            
            #
            
            namespace_file_sorting_box = ClientGUICommon.StaticBox( self._file_sort_panel, 'namespace file sorting' )
            
            self._namespace_file_sort_by = ClientGUIListBoxes.QueueListBox( namespace_file_sorting_box, 8, self._ConvertNamespaceTupleToSortString, add_callable = self._AddNamespaceSort, edit_callable = self._EditNamespaceSort )
            
            #
            
            self._namespace_file_sort_by.AddDatas( [ media_sort.sort_type[1] for media_sort in CG.client_controller.new_options.GetDefaultNamespaceSorts() ] )
            
            self._save_page_sort_on_change.setChecked( self._new_options.GetBoolean( 'save_page_sort_on_change' ) )
            
            #
            
            sort_by_text = 'You can manage your namespace sorting schemes here.'
            sort_by_text += '\n'
            sort_by_text += 'The client will sort media by comparing their namespaces, moving from left to right until an inequality is found.'
            sort_by_text += '\n'
            sort_by_text += 'Any namespaces here will also appear in your collect-by dropdowns.'
            
            namespace_file_sorting_box.Add( ClientGUICommon.BetterStaticText( namespace_file_sorting_box, sort_by_text ), CC.FLAGS_EXPAND_PERPENDICULAR )
            namespace_file_sorting_box.Add( self._namespace_file_sort_by, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            #
            
            rows = []
            
            rows.append( ( 'Default file sort: ', self._default_media_sort ) )
            rows.append( ( 'Secondary file sort (when primary gives two equal values): ', self._fallback_media_sort ) )
            rows.append( ( 'Update default file sort every time a new sort is manually chosen: ', self._save_page_sort_on_change ) )
            rows.append( ( 'Default collect: ', self._default_media_collect ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self, rows )
            
            self._file_sort_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            self._file_sort_panel.Add( namespace_file_sorting_box, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, self._file_sort_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            self.setLayout( vbox )
            
        
        def _AddNamespaceSort( self ):
            
            default = ( ( 'creator', 'series', 'page' ), ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL )
            
            return self._EditNamespaceSort( default )
            
        
        def _ConvertNamespaceTupleToSortString( self, sort_data ):
            
            ( namespaces, tag_display_type ) = sort_data
            
            return '-'.join( namespaces )
            
        
        def _EditNamespaceSort( self, sort_data ):
            
            return ClientGUITagsEditNamespaceSort.EditNamespaceSort( self, sort_data )
            
        
        def UpdateOptions( self ):
            
            self._new_options.SetDefaultSort( self._default_media_sort.GetSort() )
            self._new_options.SetFallbackSort( self._fallback_media_sort.GetSort() )
            self._new_options.SetBoolean( 'save_page_sort_on_change', self._save_page_sort_on_change.isChecked() )
            self._new_options.SetDefaultCollect( self._default_media_collect.GetValue() )
            
            namespace_sorts = [ ClientMedia.MediaSort( sort_type = ( 'namespaces', sort_data ) ) for sort_data in self._namespace_file_sort_by.GetData() ]
            
            self._new_options.SetDefaultNamespaceSorts( namespace_sorts )
            
        
    
    class _FileViewingStatisticsPanel( OptionsPagePanel ):
        
        def __init__( self, parent ):
            
            super().__init__( parent )
            
            self._new_options = CG.client_controller.new_options
            
            self._file_viewing_statistics_active = QW.QCheckBox( self )
            self._file_viewing_statistics_active_on_archive_delete_filter = QW.QCheckBox( self )
            self._file_viewing_statistics_active_on_dupe_filter = QW.QCheckBox( self )
            self._file_viewing_statistics_media_min_time = ClientGUITime.NoneableTimeDeltaWidget( self, 2.0, none_phrase = 'count every view', minutes = True, seconds = True, milliseconds = True )
            min_tt = 'If you scroll quickly through many files, you probably do not want to count each of those loads as a view. Set a reasonable minimum here and brief looks will not be counted.'
            self._file_viewing_statistics_media_min_time.setToolTip( ClientGUIFunctions.WrapToolTip( min_tt ) )
            self._file_viewing_statistics_media_max_time = ClientGUITime.NoneableTimeDeltaWidget( self, 600.0, hours = True, minutes = True, seconds = True, milliseconds = True )
            max_tt = 'If you view a file for a very long time, the recorded viewtime is truncated to this. This stops an outrageous viewtime being saved because you left something open in the background. If the media you view has duration, like a video, the max viewtime is five times its length or this, whichever is larger.'
            self._file_viewing_statistics_media_max_time.setToolTip( ClientGUIFunctions.WrapToolTip( max_tt ) )
            
            self._file_viewing_statistics_preview_min_time = ClientGUITime.NoneableTimeDeltaWidget( self, 5.0, none_phrase = 'count every view', minutes = True, seconds = True, milliseconds = True )
            self._file_viewing_statistics_preview_min_time.setToolTip( ClientGUIFunctions.WrapToolTip( min_tt ) )
            self._file_viewing_statistics_preview_max_time = ClientGUITime.NoneableTimeDeltaWidget( self, 60.0, hours = True, minutes = True, seconds = True, milliseconds = True )
            self._file_viewing_statistics_preview_max_time.setToolTip( ClientGUIFunctions.WrapToolTip( max_tt ) )
            
            file_viewing_stats_interesting_canvas_types = self._new_options.GetIntegerList( 'file_viewing_stats_interesting_canvas_types' )
            
            self._file_viewing_stats_interesting_canvas_types = ClientGUICommon.BetterCheckBoxList( self )
            
            self._file_viewing_stats_interesting_canvas_types.Append( 'media views', CC.CANVAS_MEDIA_VIEWER, starts_checked = CC.CANVAS_MEDIA_VIEWER in file_viewing_stats_interesting_canvas_types )
            self._file_viewing_stats_interesting_canvas_types.Append( 'preview views', CC.CANVAS_PREVIEW, starts_checked = CC.CANVAS_PREVIEW in file_viewing_stats_interesting_canvas_types )
            self._file_viewing_stats_interesting_canvas_types.Append( 'client api views', CC.CANVAS_CLIENT_API, starts_checked = CC.CANVAS_CLIENT_API in file_viewing_stats_interesting_canvas_types )
            
            self._file_viewing_stats_interesting_canvas_types.SetHeightBasedOnContents()
            
            tt = 'This will also configure what counts when files are sorted by views/viewtime.'
            
            self._file_viewing_stats_interesting_canvas_types.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            self._file_viewing_stats_menu_display = ClientGUICommon.BetterChoice( self )
            
            self._file_viewing_stats_menu_display.addItem( 'show a combined value, and stack the separate values a submenu', CC.FILE_VIEWING_STATS_MENU_DISPLAY_SUMMED_AND_THEN_SUBMENU )
            self._file_viewing_stats_menu_display.addItem( 'stack the separate values', CC.FILE_VIEWING_STATS_MENU_DISPLAY_STACKED )
            
            #
            
            self._file_viewing_statistics_active.setChecked( self._new_options.GetBoolean( 'file_viewing_statistics_active' ) )
            self._file_viewing_statistics_active_on_archive_delete_filter.setChecked( self._new_options.GetBoolean( 'file_viewing_statistics_active_on_archive_delete_filter' ) )
            self._file_viewing_statistics_active_on_dupe_filter.setChecked( self._new_options.GetBoolean( 'file_viewing_statistics_active_on_dupe_filter' ) )
            self._file_viewing_statistics_media_min_time.SetValue( HydrusTime.SecondiseMSFloat( self._new_options.GetNoneableInteger( 'file_viewing_statistics_media_min_time_ms' ) ) )
            self._file_viewing_statistics_media_max_time.SetValue( HydrusTime.SecondiseMSFloat( self._new_options.GetNoneableInteger( 'file_viewing_statistics_media_max_time_ms' ) ) )
            self._file_viewing_statistics_preview_min_time.SetValue( HydrusTime.SecondiseMSFloat( self._new_options.GetNoneableInteger( 'file_viewing_statistics_preview_min_time_ms' ) ) )
            self._file_viewing_statistics_preview_max_time.SetValue( HydrusTime.SecondiseMSFloat( self._new_options.GetNoneableInteger( 'file_viewing_statistics_preview_max_time_ms' ) ) )
            
            self._file_viewing_stats_menu_display.SetValue( self._new_options.GetInteger( 'file_viewing_stats_menu_display' ) )
            
            #
            
            vbox = QP.VBoxLayout()
            
            rows = []
            
            rows.append( ( 'Enable file viewing statistics tracking?:', self._file_viewing_statistics_active ) )
            rows.append( ( 'Enable file viewing statistics tracking in the archive/delete filter?:', self._file_viewing_statistics_active_on_archive_delete_filter ) )
            rows.append( ( 'Enable file viewing statistics tracking in the duplicate filter?:', self._file_viewing_statistics_active_on_dupe_filter ) )
            rows.append( ( 'Min time to view on media viewer to count as a view:', self._file_viewing_statistics_media_min_time ) )
            rows.append( ( 'Cap any view on the media viewer to this maximum time:', self._file_viewing_statistics_media_max_time ) )
            rows.append( ( 'Min time to view on preview viewer to count as a view:', self._file_viewing_statistics_preview_min_time ) )
            rows.append( ( 'Cap any view on the preview viewer to this maximum time:', self._file_viewing_statistics_preview_max_time ) )
            rows.append( ( 'Show viewing stats on media right-click menus?:', self._file_viewing_stats_menu_display ) )
            rows.append( ( 'Which views to show?:', self._file_viewing_stats_interesting_canvas_types ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self, rows )
            
            QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            vbox.addStretch( 0 )
            
            self.setLayout( vbox )
            
        
        def UpdateOptions( self ):
            
            self._new_options.SetBoolean( 'file_viewing_statistics_active', self._file_viewing_statistics_active.isChecked() )
            self._new_options.SetBoolean( 'file_viewing_statistics_active_on_archive_delete_filter', self._file_viewing_statistics_active_on_archive_delete_filter.isChecked() )
            self._new_options.SetBoolean( 'file_viewing_statistics_active_on_dupe_filter', self._file_viewing_statistics_active_on_dupe_filter.isChecked() )
            self._new_options.SetNoneableInteger( 'file_viewing_statistics_media_min_time_ms', HydrusTime.MillisecondiseS( self._file_viewing_statistics_media_min_time.GetValue() ) )
            self._new_options.SetNoneableInteger( 'file_viewing_statistics_media_max_time_ms', HydrusTime.MillisecondiseS( self._file_viewing_statistics_media_max_time.GetValue() ) )
            self._new_options.SetNoneableInteger( 'file_viewing_statistics_preview_min_time_ms', HydrusTime.MillisecondiseS( self._file_viewing_statistics_preview_min_time.GetValue() ) )
            self._new_options.SetNoneableInteger( 'file_viewing_statistics_preview_max_time_ms', HydrusTime.MillisecondiseS( self._file_viewing_statistics_preview_max_time.GetValue() ) )
            
            self._new_options.SetInteger( 'file_viewing_stats_menu_display', self._file_viewing_stats_menu_display.GetValue() )
            self._new_options.SetIntegerList( 'file_viewing_stats_interesting_canvas_types', self._file_viewing_stats_interesting_canvas_types.GetValue() )
            
        
    
    class _GUIPanel( OptionsPagePanel ):
        
        def __init__( self, parent ):
            
            super().__init__( parent )
            
            self._main_gui_panel = ClientGUICommon.StaticBox( self, 'main window' )
            
            self._app_display_name = QW.QLineEdit( self._main_gui_panel )
            self._app_display_name.setToolTip( ClientGUIFunctions.WrapToolTip( 'This is placed in every window title, with current version name. Rename if you want to personalise or differentiate.' ) )
            
            self._confirm_client_exit = QW.QCheckBox( self._main_gui_panel )
            
            self._activate_window_on_tag_search_page_activation = QW.QCheckBox( self._main_gui_panel )
            
            tt = 'Middle-clicking one or more tags in a taglist will cause the creation of a new search page for those tags. If you do this from the media viewer or a child manage tags dialog, do you want to switch immediately to the main gui?'
            
            self._activate_window_on_tag_search_page_activation.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            #
            
            self._misc_panel = ClientGUICommon.StaticBox( self, 'misc' )
            
            self._always_show_iso_time = QW.QCheckBox( self._misc_panel )
            tt = 'In many places across the program (typically import status lists), the client will state a timestamp as "5 days ago". If you would prefer a standard ISO string, like "2018-03-01 12:40:23", check this.'
            self._always_show_iso_time.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            self._menu_choice_buttons_can_mouse_scroll = QW.QCheckBox( self._misc_panel )
            tt = 'Many buttons that produce menus when clicked are also "scrollable", so if you wheel your mouse over them, the selection will scroll through the underlying menu. If this is annoying for you, turn it off here!'
            self._menu_choice_buttons_can_mouse_scroll.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            self._use_native_menubar = QW.QCheckBox( self._misc_panel )
            tt = 'macOS and some Linux allows to embed the main GUI menubar into the OS. This can be buggy! Requires restart. Note that, in case this goes wrong, by default Ctrl+Shift+O should open this options dialog--confirm that before you try this!'
            self._use_native_menubar.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            self._human_bytes_sig_figs = ClientGUICommon.BetterSpinBox( self._misc_panel, min = 1, max = 6 )
            self._human_bytes_sig_figs.setToolTip( ClientGUIFunctions.WrapToolTip( 'When the program presents a bytes size above 1KB, like 21.3KB or 4.11GB, how many total digits do we want in the number? 2 or 3 is best.') )
            
            self._do_macos_debug_dialog_menus = QW.QCheckBox( self._misc_panel )
            self._do_macos_debug_dialog_menus.setToolTip( ClientGUIFunctions.WrapToolTip( 'There is a bug in Big Sur Qt regarding interacting with some menus in dialogs. The menus show but cannot be clicked. This shows the menu items in a debug dialog instead.' ) )
            
            self._use_qt_file_dialogs = QW.QCheckBox( self._misc_panel )
            self._use_qt_file_dialogs.setToolTip( ClientGUIFunctions.WrapToolTip( 'If you get crashes opening file/directory dialogs, try this.' ) )
            
            self._remember_options_window_panel = QW.QCheckBox( self._misc_panel )
            self._remember_options_window_panel.setToolTip( ClientGUIFunctions.WrapToolTip( 'This will cause the options window (this one) to reopen at the last panel you were looking at when it was closed.' ) )
            
            #
            
            frame_locations_panel = ClientGUICommon.StaticBox( self, 'frame locations' )
            
            self._disable_get_safe_position_test = QW.QCheckBox( self._misc_panel )
            self._disable_get_safe_position_test.setToolTip( ClientGUIFunctions.WrapToolTip( 'If your windows keep getting \'rescued\' despite being in a good location, try this.' ) )
            
            self._save_window_size_and_position_on_close = QW.QCheckBox( self._misc_panel )
            self._save_window_size_and_position_on_close.setToolTip( ClientGUIFunctions.WrapToolTip( 'If you want to save media viewer size when closing the window in addition to when it gets resized/moved normally, check this box. Can be useful behaviour when using multiple open media viewers.' ) )
            
            model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_FRAME_LOCATIONS.ID, self._GetPrettyFrameLocationInfo, self._GetPrettyFrameLocationInfo )
            
            self._frame_locations_panel = ClientGUIListCtrl.BetterListCtrlPanel( frame_locations_panel )
            
            self._frame_locations = ClientGUIListCtrl.BetterListCtrlTreeView( self._frame_locations_panel, 15, model, activation_callback = self.EditFrameLocations )
            
            self._frame_locations_panel.SetListCtrl( self._frame_locations )
            
            self._frame_locations_panel.AddButton( 'edit', self.EditFrameLocations, enabled_only_on_single_selection = True )
            self._frame_locations_panel.AddSeparator()
            self._frame_locations_panel.AddButton( 'flip remember size', self._FlipRememberSize, enabled_only_on_selection = True )
            self._frame_locations_panel.AddButton( 'flip remember position', self._FlipRememberPosition, enabled_only_on_selection = True )
            self._frame_locations_panel.NewButtonRow()
            self._frame_locations_panel.AddButton( 'reset last size', self._ResetLastSize, enabled_only_on_selection = True )
            self._frame_locations_panel.AddButton( 'reset last position', self._ResetLastPosition, enabled_only_on_selection = True )
            
            #
            
            self._new_options = CG.client_controller.new_options
            
            self._app_display_name.setText( self._new_options.GetString( 'app_display_name' ) )
            
            self._confirm_client_exit.setChecked( HC.options[ 'confirm_client_exit' ] )
            
            self._activate_window_on_tag_search_page_activation.setChecked( self._new_options.GetBoolean( 'activate_window_on_tag_search_page_activation' ) )
            
            self._always_show_iso_time.setChecked( self._new_options.GetBoolean( 'always_show_iso_time' ) )
            
            self._menu_choice_buttons_can_mouse_scroll.setChecked( self._new_options.GetBoolean( 'menu_choice_buttons_can_mouse_scroll' ) )
            
            self._use_native_menubar.setChecked( self._new_options.GetBoolean( 'use_native_menubar' ) )
            
            self._human_bytes_sig_figs.setValue( self._new_options.GetInteger( 'human_bytes_sig_figs' ) )
            
            self._do_macos_debug_dialog_menus.setChecked( self._new_options.GetBoolean( 'do_macos_debug_dialog_menus' ) )
            
            self._use_qt_file_dialogs.setChecked( self._new_options.GetBoolean( 'use_qt_file_dialogs' ) )
            
            self._remember_options_window_panel.setChecked( self._new_options.GetBoolean( 'remember_options_window_panel' ) )
            
            self._disable_get_safe_position_test.setChecked( self._new_options.GetBoolean( 'disable_get_safe_position_test' ) )
            
            self._save_window_size_and_position_on_close.setChecked( self._new_options.GetBoolean( 'save_window_size_and_position_on_close' ) )
            
            for ( name, info ) in self._new_options.GetFrameLocations():
                
                listctrl_data = QP.ListsToTuples( [ name ] + list( info ) )
                
                self._frame_locations.AddData( listctrl_data )
                
            
            self._frame_locations.Sort()
            
            #
            
            rows = []
            
            rows.append( ( 'Application display name: ', self._app_display_name ) )
            rows.append( ( 'Confirm client exit: ', self._confirm_client_exit ) )
            rows.append( ( 'Switch to main window when creating new file search page from media viewer: ', self._activate_window_on_tag_search_page_activation ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self._main_gui_panel, rows )
            
            self._main_gui_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            rows = []
            
            rows.append( ( 'Prefer ISO time ("2018-03-01 12:40:23") to "5 days ago": ', self._always_show_iso_time ) )
            rows.append( ( 'Mouse wheel can "scroll" through menu buttons: ', self._menu_choice_buttons_can_mouse_scroll ) )
            rows.append( ( 'Use Native MenuBar (if available): ', self._use_native_menubar ) )
            rows.append( ( 'EXPERIMENTAL: Bytes strings >1KB pseudo significant figures: ', self._human_bytes_sig_figs ) )
            rows.append( ( 'BUGFIX: If on macOS, show dialog menus in a debug menu: ', self._do_macos_debug_dialog_menus ) )
            rows.append( ( 'ANTI-CRASH BUGFIX: Use Qt file/directory selection dialogs, rather than OS native: ', self._use_qt_file_dialogs ) )
            rows.append( ( 'Remember last open options panel in this window: ', self._remember_options_window_panel ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self, rows )
            
            self._misc_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            text = 'Here you can override the current and default values for many frame and dialog sizing and positioning variables.'
            text += '\n'
            text += 'This is an advanced control. If you aren\'t confident of what you are doing here, come back later!'
            
            st = ClientGUICommon.BetterStaticText( frame_locations_panel, label = text )
            st.setWordWrap( True )
            
            frame_locations_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            rows = []
            
            rows.append( ( 'BUGFIX: Disable off-screen window rescue: ', self._disable_get_safe_position_test ) )
            
            rows.append( ( 'Save media viewer window size and position on close: ', self._save_window_size_and_position_on_close ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self, rows )
            
            frame_locations_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            frame_locations_panel.Add( self._frame_locations_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, self._main_gui_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            QP.AddToLayout( vbox, self._misc_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            QP.AddToLayout( vbox, frame_locations_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            self.setLayout( vbox )
            
        
        def _FlipRememberPosition( self ):
            
            existing_datas = self._frame_locations.GetData( only_selected = True )
            
            replacement_tuples = []
            
            for listctrl_list in existing_datas:
                
                ( name, remember_size, remember_position, last_size, last_position, default_gravity, default_position, maximised, fullscreen ) = listctrl_list
                
                remember_position = not remember_position
                
                new_listctrl_list = ( name, remember_size, remember_position, last_size, last_position, default_gravity, default_position, maximised, fullscreen )
                
                replacement_tuples.append( ( listctrl_list, new_listctrl_list ) )
                
            
            self._frame_locations.ReplaceDatas( replacement_tuples, sort_and_scroll = True )
            
        
        def _FlipRememberSize( self ):
            
            existing_datas = self._frame_locations.GetData( only_selected = True )
            
            replacement_tuples = []
            
            for listctrl_list in existing_datas:
                
                ( name, remember_size, remember_position, last_size, last_position, default_gravity, default_position, maximised, fullscreen ) = listctrl_list
                
                remember_size = not remember_size
                
                new_listctrl_list = ( name, remember_size, remember_position, last_size, last_position, default_gravity, default_position, maximised, fullscreen )
                
                replacement_tuples.append( ( listctrl_list, new_listctrl_list ) )
                
            
            self._frame_locations.ReplaceDatas( replacement_tuples, sort_and_scroll = True )
            
        
        def _ResetLastPosition( self ):
            
            existing_datas = self._frame_locations.GetData( only_selected = True )
            
            replacement_tuples = []
            
            for listctrl_list in existing_datas:
                
                ( name, remember_size, remember_position, last_size, last_position, default_gravity, default_position, maximised, fullscreen ) = listctrl_list
                
                last_position = None
                
                new_listctrl_list = ( name, remember_size, remember_position, last_size, last_position, default_gravity, default_position, maximised, fullscreen )
                
                replacement_tuples.append( ( listctrl_list, new_listctrl_list ) )
                
            
            self._frame_locations.ReplaceDatas( replacement_tuples, sort_and_scroll = True )
            
        
        def _ResetLastSize( self ):
            
            existing_datas = self._frame_locations.GetData( only_selected = True )
            
            replacement_tuples = []
            
            for listctrl_list in existing_datas:
                
                ( name, remember_size, remember_position, last_size, last_position, default_gravity, default_position, maximised, fullscreen ) = listctrl_list
                
                last_size = None
                
                new_listctrl_list = ( name, remember_size, remember_position, last_size, last_position, default_gravity, default_position, maximised, fullscreen )
                
                replacement_tuples.append( ( listctrl_list, new_listctrl_list ) )
                
            
            self._frame_locations.ReplaceDatas( replacement_tuples, sort_and_scroll = True )
            
        
        def _GetPrettyFrameLocationInfo( self, listctrl_list ):
            
            pretty_listctrl_list = []
            
            for item in listctrl_list:
                
                pretty_listctrl_list.append( str( item ) )
                
            
            return pretty_listctrl_list
            
        
        def EditFrameLocations( self ):
            
            data = self._frame_locations.GetTopSelectedData()
            
            if data is None:
                
                return
                
            
            listctrl_list = data
            
            title = 'set frame location information'
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, title ) as dlg:
                
                panel = ClientGUIScrolledPanelsEdit.EditFrameLocationPanel( dlg, listctrl_list )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                    
                    new_listctrl_list = panel.GetValue()
                    
                    self._frame_locations.ReplaceData( listctrl_list, new_listctrl_list, sort_and_scroll = True )
                    
                
            
        
        def UpdateOptions( self ):
            
            HC.options[ 'confirm_client_exit' ] = self._confirm_client_exit.isChecked()
            
            self._new_options.SetBoolean( 'always_show_iso_time', self._always_show_iso_time.isChecked() )
            self._new_options.SetBoolean( 'menu_choice_buttons_can_mouse_scroll', self._menu_choice_buttons_can_mouse_scroll.isChecked() )
            self._new_options.SetBoolean( 'use_native_menubar', self._use_native_menubar.isChecked() )
            
            self._new_options.SetInteger( 'human_bytes_sig_figs', self._human_bytes_sig_figs.value() )
            
            self._new_options.SetBoolean( 'activate_window_on_tag_search_page_activation', self._activate_window_on_tag_search_page_activation.isChecked() )
            
            app_display_name = self._app_display_name.text()
            
            if app_display_name == '':
                
                app_display_name = 'hydrus client'
                
            
            self._new_options.SetString( 'app_display_name', app_display_name )
            
            self._new_options.SetBoolean( 'do_macos_debug_dialog_menus', self._do_macos_debug_dialog_menus.isChecked() )
            self._new_options.SetBoolean( 'use_qt_file_dialogs', self._use_qt_file_dialogs.isChecked() )
            self._new_options.SetBoolean( 'remember_options_window_panel', self._remember_options_window_panel.isChecked() )
            
            self._new_options.SetBoolean( 'disable_get_safe_position_test', self._disable_get_safe_position_test.isChecked() )
            self._new_options.SetBoolean( 'save_window_size_and_position_on_close', self._save_window_size_and_position_on_close.isChecked() )
            
            for listctrl_list in self._frame_locations.GetData():
                
                ( name, remember_size, remember_position, last_size, last_position, default_gravity, default_position, maximised, fullscreen ) = listctrl_list
                
                self._new_options.SetFrameLocation( name, remember_size, remember_position, last_size, last_position, default_gravity, default_position, maximised, fullscreen )
                
            
        
    
    class _GUIPagesPanel( OptionsPagePanel ):
        
        def __init__( self, parent, new_options ):
            
            super().__init__( parent )
            
            self._new_options = new_options
            
            #
            
            self._controls_panel = ClientGUICommon.StaticBox( self, 'preview window' )
            
            self._hide_preview = QW.QCheckBox( self._controls_panel )
            
            #
            
            self._opening_and_closing_panel = ClientGUICommon.StaticBox( self, 'opening and closing' )
            
            self._default_new_page_goes = ClientGUICommon.BetterChoice( self._opening_and_closing_panel )
            
            for value in [ CC.NEW_PAGE_GOES_FAR_LEFT, CC.NEW_PAGE_GOES_LEFT_OF_CURRENT, CC.NEW_PAGE_GOES_RIGHT_OF_CURRENT, CC.NEW_PAGE_GOES_FAR_RIGHT ]:
                
                self._default_new_page_goes.addItem( CC.new_page_goes_string_lookup[ value ], value )
                
            
            self._show_all_my_files_on_page_chooser = QW.QCheckBox( self._opening_and_closing_panel )
            self._show_all_my_files_on_page_chooser.setToolTip( ClientGUIFunctions.WrapToolTip( 'This will only show if you have more than one local file domain.' ) )
            self._show_all_my_files_on_page_chooser_at_top = QW.QCheckBox( self._opening_and_closing_panel )
            self._show_all_my_files_on_page_chooser_at_top.setToolTip( ClientGUIFunctions.WrapToolTip( 'Put "all my files" at the top of the page chooser, to better see it if you have many local file domains.' ) )
            
            self._show_local_files_on_page_chooser = QW.QCheckBox( self._opening_and_closing_panel )
            self._show_local_files_on_page_chooser.setToolTip( ClientGUIFunctions.WrapToolTip( 'If you do not know what this is, you do not want it!' ) )
            self._show_local_files_on_page_chooser_at_top = QW.QCheckBox( self._opening_and_closing_panel )
            self._show_local_files_on_page_chooser_at_top.setToolTip( ClientGUIFunctions.WrapToolTip( 'Put "local files" at the top of the page chooser (above "all my files" as well, if it is present).' ) )
            
            self._close_page_focus_goes = ClientGUICommon.BetterChoice( self._opening_and_closing_panel )
            
            for value in [ CC.CLOSED_PAGE_FOCUS_GOES_LEFT, CC.CLOSED_PAGE_FOCUS_GOES_RIGHT ]:
                
                self._close_page_focus_goes.addItem( CC.closed_page_focus_string_lookup[ value ], value )
                
            
            self._confirm_all_page_closes = QW.QCheckBox( self._opening_and_closing_panel )
            self._confirm_all_page_closes.setToolTip( ClientGUIFunctions.WrapToolTip( 'With this, you will always be asked, even on single page closures of simple file pages.' ) )
            self._confirm_non_empty_downloader_page_close = QW.QCheckBox( self._opening_and_closing_panel )
            self._confirm_non_empty_downloader_page_close.setToolTip( ClientGUIFunctions.WrapToolTip( 'Helps to avoid accidental closes of big downloader pages.' ) )
            
            self._force_hide_page_signal_on_new_page = QW.QCheckBox( self._opening_and_closing_panel )
            
            self._force_hide_page_signal_on_new_page.setToolTip( ClientGUIFunctions.WrapToolTip( 'If your video still plays with sound in the preview viewer when you create a new page, please try this.' ) )
            
            #
            
            self._navigation_and_dnd = ClientGUICommon.StaticBox( self, 'navigation and drag-and-drop' )
            
            self._notebook_tab_alignment = ClientGUICommon.BetterChoice( self._navigation_and_dnd )
            
            for value in [ CC.DIRECTION_UP, CC.DIRECTION_LEFT, CC.DIRECTION_RIGHT, CC.DIRECTION_DOWN ]:
                
                self._notebook_tab_alignment.addItem( CC.directions_alignment_string_lookup[ value ], value )
                
            
            self._set_search_focus_on_page_change = QW.QCheckBox( self._navigation_and_dnd )
            self._set_search_focus_on_page_change.setToolTip( ClientGUIFunctions.WrapToolTip( 'Set it so whenever you switch between pages, the keyboard focus immediately moves to the tag autocomplete or search text input.' ) )
            
            self._page_drop_chase_normally = QW.QCheckBox( self._navigation_and_dnd )
            self._page_drop_chase_normally.setToolTip( ClientGUIFunctions.WrapToolTip( 'When you drop a page to a new location, should hydrus follow the page selection to the new location?' ) )
            self._page_drop_chase_with_shift = QW.QCheckBox( self._navigation_and_dnd )
            self._page_drop_chase_with_shift.setToolTip( ClientGUIFunctions.WrapToolTip( 'When you drop a page to a new location with shift held down, should hydrus follow the page selection to the new location?' ) )
            
            self._page_drag_change_tab_normally = QW.QCheckBox( self._navigation_and_dnd )
            self._page_drag_change_tab_normally.setToolTip( ClientGUIFunctions.WrapToolTip( 'When you drag media or a page to a new location, should hydrus navigate and change tabs as you move the mouse around?' ) )
            self._page_drag_change_tab_with_shift = QW.QCheckBox( self._navigation_and_dnd )
            self._page_drag_change_tab_with_shift.setToolTip( ClientGUIFunctions.WrapToolTip( 'When you drag media or a page to a new location with shift held down, should hydrus navigate and change tabs as you move the mouse around?' ) )
            
            self._wheel_scrolls_tab_bar = QW.QCheckBox( self._navigation_and_dnd )
            self._wheel_scrolls_tab_bar.setToolTip( ClientGUIFunctions.WrapToolTip( 'When you scroll your mouse wheel over some tabs, the normal behaviour is to change the tab selection. If you often have overloaded tab bars, you might like to have the mouse wheel actually scroll the tab bar itself.' ) )
            
            self._disable_page_tab_dnd = QW.QCheckBox( self._navigation_and_dnd )
            
            self._disable_page_tab_dnd.setToolTip( ClientGUIFunctions.WrapToolTip( 'Trying to debug some client hangs!' ) )
            
            #
            
            self._page_names_panel = ClientGUICommon.StaticBox( self, 'page tab names' )
            
            self._max_page_name_chars = ClientGUICommon.BetterSpinBox( self._page_names_panel, min=1, max=256 )
            self._elide_page_tab_names = QW.QCheckBox( self._page_names_panel )
            
            self._page_file_count_display = ClientGUICommon.BetterChoice( self._page_names_panel )
            
            for display_type in ( CC.PAGE_FILE_COUNT_DISPLAY_ALL, CC.PAGE_FILE_COUNT_DISPLAY_ONLY_IMPORTERS, CC.PAGE_FILE_COUNT_DISPLAY_NONE, CC.PAGE_FILE_COUNT_DISPLAY_ALL_BUT_ONLY_IF_GREATER_THAN_ZERO ):
                
                self._page_file_count_display.addItem( CC.page_file_count_display_string_lookup[ display_type ], display_type )
                
            
            self._import_page_progress_display = QW.QCheckBox( self._page_names_panel )
            
            self._rename_page_of_pages_on_pick_new = QW.QCheckBox( self._page_names_panel )
            self._rename_page_of_pages_on_pick_new.setToolTip( ClientGUIFunctions.WrapToolTip( 'When you create a new \'page of pages\' from the new page picker, should it automatically prompt you to give it a name other than \'pages\'?' ) )
            self._rename_page_of_pages_on_send = QW.QCheckBox( self._page_names_panel )
            self._rename_page_of_pages_on_send.setToolTip( ClientGUIFunctions.WrapToolTip( 'When you \'send this page down\' or \'send pages to the right\' to a new page of pages, should it also automatically prompt you to rename it?' ) )
            
            #
            
            self._show_all_my_files_on_page_chooser.setChecked( self._new_options.GetBoolean( 'show_all_my_files_on_page_chooser' ) )
            self._show_all_my_files_on_page_chooser_at_top.setChecked( self._new_options.GetBoolean( 'show_all_my_files_on_page_chooser_at_top' ) )
            self._show_local_files_on_page_chooser.setChecked( self._new_options.GetBoolean( 'show_local_files_on_page_chooser' ) )
            self._show_local_files_on_page_chooser_at_top.setChecked( self._new_options.GetBoolean( 'show_local_files_on_page_chooser_at_top' ) )
            
            self._confirm_all_page_closes.setChecked( self._new_options.GetBoolean( 'confirm_all_page_closes' ) )
            self._confirm_non_empty_downloader_page_close.setChecked( self._new_options.GetBoolean( 'confirm_non_empty_downloader_page_close' ) )
            
            self._default_new_page_goes.SetValue( self._new_options.GetInteger( 'default_new_page_goes' ) )
            self._close_page_focus_goes.SetValue( self._new_options.GetInteger( 'close_page_focus_goes' ) )
            
            self._notebook_tab_alignment.SetValue( self._new_options.GetInteger( 'notebook_tab_alignment' ) )
            
            self._max_page_name_chars.setValue( self._new_options.GetInteger( 'max_page_name_chars' ) )
            
            self._elide_page_tab_names.setChecked( self._new_options.GetBoolean( 'elide_page_tab_names' ) )
            
            self._page_file_count_display.SetValue( self._new_options.GetInteger( 'page_file_count_display' ) )
            
            self._import_page_progress_display.setChecked( self._new_options.GetBoolean( 'import_page_progress_display' ) )
            
            self._rename_page_of_pages_on_pick_new.setChecked( self._new_options.GetBoolean( 'rename_page_of_pages_on_pick_new' ) )
            self._rename_page_of_pages_on_send.setChecked( self._new_options.GetBoolean( 'rename_page_of_pages_on_send' ) )
            
            self._page_drop_chase_normally.setChecked( self._new_options.GetBoolean( 'page_drop_chase_normally' ) )
            self._page_drop_chase_with_shift.setChecked( self._new_options.GetBoolean( 'page_drop_chase_with_shift' ) )
            self._page_drag_change_tab_normally.setChecked( self._new_options.GetBoolean( 'page_drag_change_tab_normally' ) )
            self._page_drag_change_tab_with_shift.setChecked( self._new_options.GetBoolean( 'page_drag_change_tab_with_shift' ) )
            
            self._wheel_scrolls_tab_bar.setChecked( self._new_options.GetBoolean( 'wheel_scrolls_tab_bar' ) )
            
            self._disable_page_tab_dnd.setChecked( self._new_options.GetBoolean( 'disable_page_tab_dnd' ) )
            
            self._force_hide_page_signal_on_new_page.setChecked( self._new_options.GetBoolean( 'force_hide_page_signal_on_new_page' ) )
            
            self._set_search_focus_on_page_change.setChecked( self._new_options.GetBoolean( 'set_search_focus_on_page_change' ) )
            
            self._hide_preview.setChecked( HC.options[ 'hide_preview' ] )
            
            #
            
            rows = []
            
            rows.append( ( 'Put new page tabs on: ', self._default_new_page_goes ) )
            rows.append( ( 'In new page chooser, show "all my files" if appropriate:', self._show_all_my_files_on_page_chooser ) )
            rows.append( ( '  Put it at the top:', self._show_all_my_files_on_page_chooser_at_top ) )
            rows.append( ( 'In new page chooser, show "local files":', self._show_local_files_on_page_chooser ) )
            rows.append( ( '  Put it at the top:', self._show_local_files_on_page_chooser_at_top ) )
            rows.append( ( 'When closing the current tab, move focus: ', self._close_page_focus_goes ) )
            rows.append( ( 'Confirm when closing any page: ', self._confirm_all_page_closes ) )
            rows.append( ( 'Confirm when closing a non-empty importer page: ', self._confirm_non_empty_downloader_page_close ) )
            rows.append( ( 'BUGFIX: Force \'hide page\' signal when creating a new page: ', self._force_hide_page_signal_on_new_page ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self._opening_and_closing_panel, rows )
            
            self._opening_and_closing_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            rows = []
            
            rows.append( ( 'Notebook tab alignment: ', self._notebook_tab_alignment ) )
            rows.append( ( 'When switching to pages, move keyboard focus to any text input field: ', self._set_search_focus_on_page_change ) )
            rows.append( ( 'Selection chases dropped page after drag and drop: ', self._page_drop_chase_normally ) )
            rows.append( ( '  With shift held down?: ', self._page_drop_chase_with_shift ) )
            rows.append( ( 'Navigate tabs during drag and drop: ', self._page_drag_change_tab_normally ) )
            rows.append( ( '  With shift held down?: ', self._page_drag_change_tab_with_shift ) )
            rows.append( ( 'EXPERIMENTAL: Mouse wheel scrolls tab bar, not page selection: ', self._wheel_scrolls_tab_bar ) )
            rows.append( ( 'BUGFIX: Disable all page tab drag and drop: ', self._disable_page_tab_dnd ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self._navigation_and_dnd, rows )
            
            self._navigation_and_dnd.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            rows = []
            
            rows.append( ( 'Max characters to display in a page name: ', self._max_page_name_chars ) )
            rows.append( ( 'When there are too many tabs to fit, \'...\' elide their names so they fit: ', self._elide_page_tab_names ) )
            rows.append( ( 'Show page file count after its name: ', self._page_file_count_display ) )
            rows.append( ( 'Show import page x/y progress after its name: ', self._import_page_progress_display ) )
            rows.append( ( 'Automatically prompt to rename new \'page of pages\' after creation: ', self._rename_page_of_pages_on_pick_new ) )
            rows.append( ( '  Also automatically prompt when sending some pages to one: ', self._rename_page_of_pages_on_send ) )
            
            page_names_gridbox = ClientGUICommon.WrapInGrid( self._page_names_panel, rows )
            
            label = 'If you have enough pages in a row, left/right arrows will appear to navigate them back and forth.'
            label += '\n'
            label += 'Due to an unfortunate Qt issue, the tab bar will scroll so the current tab is right-most visible whenever you change page or a page is renamed. This is very annoying to live with.'
            label += '\n'
            label += 'Therefore, do not put import pages in a long row of tabs, as it will reset scroll position on every progress update. Try to avoid long rows in general.'
            label += '\n'
            label += 'Just make some nested \'page of pages\' so they are not all in the same row.'
            
            st = ClientGUICommon.BetterStaticText( self._page_names_panel, label )
            
            st.setToolTip( ClientGUIFunctions.WrapToolTip( 'https://bugreports.qt.io/browse/QTBUG-45381' ) )
            
            st.setWordWrap( True )
            
            self._page_names_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            self._page_names_panel.Add( page_names_gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            rows = []
            
            rows.append( ( 'Hide the bottom-left preview window: ', self._hide_preview ) )
            gridbox = ClientGUICommon.WrapInGrid( self._controls_panel, rows )
            
            self._controls_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            
            #
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, self._controls_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, self._opening_and_closing_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, self._navigation_and_dnd, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, self._page_names_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.addStretch( 0 )
            
            self.setLayout( vbox )
            
        
        def UpdateOptions( self ):
            
            self._new_options.SetInteger( 'notebook_tab_alignment', self._notebook_tab_alignment.GetValue() )
            
            self._new_options.SetBoolean( 'show_all_my_files_on_page_chooser', self._show_all_my_files_on_page_chooser.isChecked() )
            self._new_options.SetBoolean( 'show_all_my_files_on_page_chooser_at_top', self._show_all_my_files_on_page_chooser_at_top.isChecked() )
            self._new_options.SetBoolean( 'show_local_files_on_page_chooser', self._show_local_files_on_page_chooser.isChecked() )
            self._new_options.SetBoolean( 'show_local_files_on_page_chooser_at_top', self._show_local_files_on_page_chooser_at_top.isChecked() )
            
            self._new_options.SetBoolean( 'confirm_all_page_closes', self._confirm_all_page_closes.isChecked() )
            self._new_options.SetBoolean( 'confirm_non_empty_downloader_page_close', self._confirm_non_empty_downloader_page_close.isChecked() )
            
            self._new_options.SetInteger( 'default_new_page_goes', self._default_new_page_goes.GetValue() )
            self._new_options.SetInteger( 'close_page_focus_goes', self._close_page_focus_goes.GetValue() )
            
            self._new_options.SetInteger( 'max_page_name_chars', self._max_page_name_chars.value() )
            
            self._new_options.SetBoolean( 'elide_page_tab_names', self._elide_page_tab_names.isChecked() )
            
            self._new_options.SetInteger( 'page_file_count_display', self._page_file_count_display.GetValue() )
            self._new_options.SetBoolean( 'import_page_progress_display', self._import_page_progress_display.isChecked() )
            self._new_options.SetBoolean( 'rename_page_of_pages_on_pick_new', self._rename_page_of_pages_on_pick_new.isChecked() )
            self._new_options.SetBoolean( 'rename_page_of_pages_on_send', self._rename_page_of_pages_on_send.isChecked() )
            
            self._new_options.SetBoolean( 'disable_page_tab_dnd', self._disable_page_tab_dnd.isChecked() )
            self._new_options.SetBoolean( 'force_hide_page_signal_on_new_page', self._force_hide_page_signal_on_new_page.isChecked() )
            
            self._new_options.SetBoolean( 'page_drop_chase_normally', self._page_drop_chase_normally.isChecked() )
            self._new_options.SetBoolean( 'page_drop_chase_with_shift', self._page_drop_chase_with_shift.isChecked() )
            self._new_options.SetBoolean( 'page_drag_change_tab_normally', self._page_drag_change_tab_normally.isChecked() )
            self._new_options.SetBoolean( 'page_drag_change_tab_with_shift', self._page_drag_change_tab_with_shift.isChecked() )
            
            self._new_options.SetBoolean( 'wheel_scrolls_tab_bar', self._wheel_scrolls_tab_bar.isChecked() )
            
            self._new_options.SetBoolean( 'set_search_focus_on_page_change', self._set_search_focus_on_page_change.isChecked() )
            
            HC.options[ 'hide_preview' ] = self._hide_preview.isChecked()
            
        
    
    class _GUISessionsPanel( OptionsPagePanel ):
        
        def __init__( self, parent, new_options ):
            
            super().__init__( parent )
            
            self._new_options = new_options
            
            self._sessions_panel = ClientGUICommon.StaticBox( self, 'sessions' )
            
            self._default_gui_session = ClientGUICommon.BetterChoice( self._sessions_panel )
            
            self._last_session_save_period_minutes = ClientGUICommon.BetterSpinBox( self._sessions_panel, min = 1, max = 1440 )
            
            self._only_save_last_session_during_idle = QW.QCheckBox( self._sessions_panel )
            
            self._only_save_last_session_during_idle.setToolTip( ClientGUIFunctions.WrapToolTip( 'This is useful if you usually have a very large session (200,000+ files/import items open) and a client that is always on.' ) )
            
            self._number_of_gui_session_backups = ClientGUICommon.BetterSpinBox( self._sessions_panel, min = 1, max = 32 )
            
            self._number_of_gui_session_backups.setToolTip( ClientGUIFunctions.WrapToolTip( 'The client keeps multiple rolling backups of your gui sessions. If you have very large sessions, you might like to reduce this number.' ) )
            
            self._show_session_size_warnings = QW.QCheckBox( self._sessions_panel )
            
            self._show_session_size_warnings.setToolTip( ClientGUIFunctions.WrapToolTip( 'This will give you a once-per-boot warning popup if your active session contains more than 10M weight.' ) )
            
            #
            
            gui_session_names = CG.client_controller.Read( 'serialisable_names', HydrusSerialisable.SERIALISABLE_TYPE_GUI_SESSION_CONTAINER )
            
            if CC.LAST_SESSION_SESSION_NAME not in gui_session_names:
                
                gui_session_names.insert( 0, CC.LAST_SESSION_SESSION_NAME )
                
            
            self._default_gui_session.addItem( 'just a blank page', None )
            
            for name in gui_session_names:
                
                self._default_gui_session.addItem( name, name )
                
            
            self._default_gui_session.SetValue( HC.options['default_gui_session'] )
            
            self._last_session_save_period_minutes.setValue( self._new_options.GetInteger( 'last_session_save_period_minutes' ) )
            
            self._only_save_last_session_during_idle.setChecked( self._new_options.GetBoolean( 'only_save_last_session_during_idle' ) )
            
            self._number_of_gui_session_backups.setValue( self._new_options.GetInteger( 'number_of_gui_session_backups' ) )
            
            self._show_session_size_warnings.setChecked( self._new_options.GetBoolean( 'show_session_size_warnings' ) )
            
            #
            
            rows = []
            
            rows.append( ( 'Default session on startup: ', self._default_gui_session ) )
            rows.append( ( 'If \'last session\' above, autosave it how often (minutes)?', self._last_session_save_period_minutes ) )
            rows.append( ( 'If \'last session\' above, only autosave during idle time?', self._only_save_last_session_during_idle ) )
            rows.append( ( 'Number of session backups to keep: ', self._number_of_gui_session_backups ) )
            rows.append( ( 'Show warning popup if session size exceeds 10,000,000: ', self._show_session_size_warnings ) )
            
            sessions_gridbox = ClientGUICommon.WrapInGrid( self._sessions_panel, rows )
            
            self._sessions_panel.Add( sessions_gridbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, self._sessions_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            vbox.addStretch( 0 )
            
            self.setLayout( vbox )
            
        
        def UpdateOptions( self ):
            
            HC.options[ 'default_gui_session' ] = self._default_gui_session.GetValue()
            
            self._new_options.SetInteger( 'last_session_save_period_minutes', self._last_session_save_period_minutes.value() )
            
            self._new_options.SetInteger( 'number_of_gui_session_backups', self._number_of_gui_session_backups.value() )
            
            self._new_options.SetBoolean( 'show_session_size_warnings', self._show_session_size_warnings.isChecked() )
            
            self._new_options.SetBoolean( 'only_save_last_session_during_idle', self._only_save_last_session_during_idle.isChecked() )
            
        
    
    class _ImportingPanel( OptionsPagePanel ):
        
        def __init__( self, parent, new_options ):
            
            super().__init__( parent )
            
            self._new_options = new_options
            
            #
            
            drag_and_drop = ClientGUICommon.StaticBox( self, 'drag and drop' )
            
            self._show_destination_page_when_dnd_url = QW.QCheckBox( drag_and_drop )
            self._show_destination_page_when_dnd_url.setToolTip( ClientGUIFunctions.WrapToolTip( 'When dropping a URL on the program, should we switch to the destination page?' ) )
            
            #
            
            default_fios = ClientGUICommon.StaticBox( self, 'default file import options' )
            
            quiet_file_import_options = self._new_options.GetDefaultFileImportOptions( FileImportOptions.IMPORT_TYPE_QUIET )
            
            show_downloader_options = True
            allow_default_selection = False
            
            self._quiet_fios = ClientGUIImportOptions.ImportOptionsButton( self, show_downloader_options, allow_default_selection )
            
            self._quiet_fios.SetFileImportOptions( quiet_file_import_options )
            
            loud_file_import_options = self._new_options.GetDefaultFileImportOptions( FileImportOptions.IMPORT_TYPE_LOUD )
            
            self._loud_fios = ClientGUIImportOptions.ImportOptionsButton( self, show_downloader_options, allow_default_selection )
            
            self._loud_fios.SetFileImportOptions( loud_file_import_options )
            
            #
            
            self._show_destination_page_when_dnd_url.setChecked( self._new_options.GetBoolean( 'show_destination_page_when_dnd_url' ) )
            
            #
            
            rows = []
            
            rows.append( ( 'When DnDing a URL onto the program, switch to the download page:', self._show_destination_page_when_dnd_url ) )
            
            gridbox = ClientGUICommon.WrapInGrid( drag_and_drop, rows )
            
            drag_and_drop.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            st = ClientGUICommon.BetterStaticText( default_fios, label = 'You might like to set different "presentation options" for importers that work in the background vs those that work in a page in front of you.\n\nNOTE: I am likely to break "File Import Options" into smaller pieces in an upcoming update, and this options page will change too.' )
            
            st.setWordWrap( True )
            
            default_fios.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            rows = []
            
            rows.append( ( 'For import contexts that happen in a popup window or with no UI at all:\n(import folders, subscriptions, Client API)', self._quiet_fios ) )
            rows.append( ( 'For import contexts that happen on a page in the main gui window:\n(gallery or url import pages, watchers, local file import pages, any files/urls you drag and drop on the client)', self._loud_fios ) )
            
            gridbox = ClientGUICommon.WrapInGrid( default_fios, rows )
            
            default_fios.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, default_fios, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, drag_and_drop, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.addStretch( 0 )
            
            self.setLayout( vbox )
            
        
        def UpdateOptions( self ):
            
            self._new_options.SetBoolean( 'show_destination_page_when_dnd_url', self._show_destination_page_when_dnd_url.isChecked() )
            
            self._new_options.SetDefaultFileImportOptions( FileImportOptions.IMPORT_TYPE_QUIET, self._quiet_fios.GetFileImportOptions() )
            self._new_options.SetDefaultFileImportOptions( FileImportOptions.IMPORT_TYPE_LOUD, self._loud_fios.GetFileImportOptions() )
            
        
    
    class _CommandPalettePanel( OptionsPagePanel ):
        
        def __init__( self, parent, new_options ):
            
            self._new_options = new_options
            
            super().__init__( parent )
            
            self._command_palette_panel = ClientGUICommon.StaticBox( self, 'command palette' )
            
            self._command_palette_show_page_of_pages = QW.QCheckBox( self._command_palette_panel )
            self._command_palette_show_page_of_pages.setToolTip( ClientGUIFunctions.WrapToolTip( 'Show "page of pages" as selectable page results. This will focus the page, and whatever sub-page it previously focused (including none, if it has no child pages).' ) )
            
            self._command_palette_show_main_menu = QW.QCheckBox( self._command_palette_panel )
            self._command_palette_show_main_menu.setToolTip( ClientGUIFunctions.WrapToolTip(  'Show the main gui window\'s menubar actions.' ) )
            
            self._command_palette_show_media_menu = QW.QCheckBox( self._command_palette_panel )
            self._command_palette_show_media_menu.setToolTip( ClientGUIFunctions.WrapToolTip( 'Show the actions for the thumbnail menu on the current media page. Be careful with this, it basically just shows everything with slightly ugly labels..' ) )
            
            #
            
            self._command_palette_show_page_of_pages.setChecked( self._new_options.GetBoolean( 'command_palette_show_page_of_pages' ) )
            self._command_palette_show_main_menu.setChecked( self._new_options.GetBoolean( 'command_palette_show_main_menu' ) )
            self._command_palette_show_media_menu.setChecked( self._new_options.GetBoolean( 'command_palette_show_media_menu' ) )
            
            #
            
            rows = []
            
            rows.append( ( 'Show "page of pages" results: ', self._command_palette_show_page_of_pages ) )
            rows.append( ( 'ADVANCED: Show main menubar results (after typing): ', self._command_palette_show_main_menu ) )
            rows.append( ( 'ADVANCED: Show media menu results (after typing): ', self._command_palette_show_media_menu ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self, rows )
            
            text = 'By default, you can hit Ctrl+P to bring up a Command Palette. It initially shows your pages for quick navigation, but it can search for more.'
            
            st = ClientGUICommon.BetterStaticText( self._command_palette_panel, text )
            st.setWordWrap( True )
            
            self._command_palette_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
            self._command_palette_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, self._command_palette_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.addStretch( 0 )
            
            self.setLayout( vbox )
            
        
        def UpdateOptions( self ):
            
            self._new_options.SetBoolean( 'command_palette_show_page_of_pages', self._command_palette_show_page_of_pages.isChecked() )
            self._new_options.SetBoolean( 'command_palette_show_main_menu', self._command_palette_show_main_menu.isChecked() )
            self._new_options.SetBoolean( 'command_palette_show_media_menu', self._command_palette_show_media_menu.isChecked() )
            
        
    
    class _MaintenanceAndProcessingPanel( OptionsPagePanel ):
        
        def __init__( self, parent ):
            
            super().__init__( parent )
            
            self._new_options = CG.client_controller.new_options
            
            self._jobs_panel = ClientGUICommon.StaticBox( self, 'when to run high cpu jobs' )
            
            #
            
            self._idle_panel = ClientGUICommon.StaticBox( self._jobs_panel, 'idle', can_expand = True, start_expanded = False )
            
            self._idle_normal = QW.QCheckBox( self._idle_panel )
            self._idle_normal.clicked.connect( self._EnableDisableIdleNormal )
            
            self._idle_period = ClientGUICommon.NoneableSpinCtrl( self._idle_panel, 30, min = 1, max = 1000, multiplier = 60, unit = 'minutes', none_phrase = 'ignore normal browsing' )
            self._idle_mouse_period = ClientGUICommon.NoneableSpinCtrl( self._idle_panel, 10, min = 1, max = 1000, multiplier = 60, unit = 'minutes', none_phrase = 'ignore mouse movements' )
            self._idle_mode_client_api_timeout = ClientGUICommon.NoneableSpinCtrl( self._idle_panel, 5, min = 1, max = 1000, multiplier = 60, unit = 'minutes', none_phrase = 'ignore client api' )
            self._system_busy_cpu_percent = ClientGUICommon.BetterSpinBox( self._idle_panel, min = 5, max = 99 )
            self._system_busy_cpu_count = ClientGUICommon.NoneableSpinCtrl( self._idle_panel, 1, min = 1, max = 64, unit = 'cores', none_phrase = 'ignore cpu usage' )
            
            #
            
            self._shutdown_panel = ClientGUICommon.StaticBox( self._jobs_panel, 'shutdown', can_expand = True, start_expanded = False )
            
            self._idle_shutdown = ClientGUICommon.BetterChoice( self._shutdown_panel )
            
            for idle_id in ( CC.IDLE_NOT_ON_SHUTDOWN, CC.IDLE_ON_SHUTDOWN, CC.IDLE_ON_SHUTDOWN_ASK_FIRST ):
                
                self._idle_shutdown.addItem( CC.idle_string_lookup[ idle_id], idle_id )
                
            
            self._idle_shutdown.currentIndexChanged.connect( self._EnableDisableIdleShutdown )
            
            self._idle_shutdown_max_minutes = ClientGUICommon.BetterSpinBox( self._shutdown_panel, min=1, max=1440 )
            self._shutdown_work_period = ClientGUITime.TimeDeltaButton( self._shutdown_panel, min = 60, days = True, hours = True, minutes = True )
            
            #
            
            self._file_maintenance_panel = ClientGUICommon.StaticBox( self, 'file maintenance', can_expand = True, start_expanded = False )
            
            min_unit_value = 1
            max_unit_value = 1000
            min_time_delta = 1
            
            self._file_maintenance_during_idle = QW.QCheckBox( self._file_maintenance_panel )
            
            self._file_maintenance_idle_throttle_velocity = ClientGUITime.VelocityCtrl( self._file_maintenance_panel, min_unit_value, max_unit_value, min_time_delta, minutes = True, seconds = True, per_phrase = 'every', unit = 'heavy work units' )
            
            self._file_maintenance_during_active = QW.QCheckBox( self._file_maintenance_panel )
            
            self._file_maintenance_active_throttle_velocity = ClientGUITime.VelocityCtrl( self._file_maintenance_panel, min_unit_value, max_unit_value, min_time_delta, minutes = True, seconds = True, per_phrase = 'every', unit = 'heavy work units' )
            
            tt = 'Different jobs will count for more or less weight. A file metadata reparse will count as one work unit, but quicker jobs like checking for file presence will count as fractions of one and will will work more frequently.'
            tt += '\n' * 2
            tt += 'Please note that this throttle is not rigorous for long timescales, as file processing history is not currently saved on client exit. If you restart the client, the file manager thinks it has run 0 jobs and will be happy to run until the throttle kicks in again.'
            
            self._file_maintenance_idle_throttle_velocity.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            self._file_maintenance_active_throttle_velocity.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            #
            
            self._repository_processing_panel = ClientGUICommon.StaticBox( self, 'repository processing', can_expand = True, start_expanded = False )
            
            self._repository_processing_work_time_very_idle = ClientGUITime.TimeDeltaWidget( self._repository_processing_panel, min = 0.1, seconds = True, milliseconds = True )
            tt = 'DO NOT CHANGE UNLESS YOU KNOW WHAT YOU ARE DOING. Repository processing operates on a work-rest cycle. This setting determines how long it should work for in each work packet. Actual work time will normally be a little larger than this. Very Idle is after an hour of idle mode.'
            self._repository_processing_work_time_very_idle.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            self._repository_processing_rest_percentage_very_idle = ClientGUICommon.BetterSpinBox( self._repository_processing_panel, min = 0, max = 100000 )
            tt = 'DO NOT CHANGE UNLESS YOU KNOW WHAT YOU ARE DOING. Repository processing operates on a work-rest cycle. This setting determines how long it should wait before starting a new work packet, in multiples of the last work time. Very Idle is after an hour of idle mode.'
            self._repository_processing_rest_percentage_very_idle.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            self._repository_processing_work_time_idle = ClientGUITime.TimeDeltaWidget( self._repository_processing_panel, min = 0.1, seconds = True, milliseconds = True )
            tt = 'DO NOT CHANGE UNLESS YOU KNOW WHAT YOU ARE DOING. Repository processing operates on a work-rest cycle. This setting determines how long it should work for in each work packet. Actual work time will normally be a little larger than this. This is for idle mode.'
            self._repository_processing_work_time_idle.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            self._repository_processing_rest_percentage_idle = ClientGUICommon.BetterSpinBox( self._repository_processing_panel, min = 0, max = 100000 )
            tt = 'DO NOT CHANGE UNLESS YOU KNOW WHAT YOU ARE DOING. Repository processing operates on a work-rest cycle. This setting determines how long it should wait before starting a new work packet, in multiples of the last work time. This is for idle mode.'
            self._repository_processing_rest_percentage_idle.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            self._repository_processing_work_time_normal = ClientGUITime.TimeDeltaWidget( self._repository_processing_panel, min = 0.1, seconds = True, milliseconds = True )
            tt = 'DO NOT CHANGE UNLESS YOU KNOW WHAT YOU ARE DOING. Repository processing operates on a work-rest cycle. This setting determines how long it should work for in each work packet. Actual work time will normally be a little larger than this. This is for when you force-start work from review services.'
            self._repository_processing_work_time_normal.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            self._repository_processing_rest_percentage_normal = ClientGUICommon.BetterSpinBox( self._repository_processing_panel, min = 0, max = 100000 )
            tt = 'DO NOT CHANGE UNLESS YOU KNOW WHAT YOU ARE DOING. Repository processing operates on a work-rest cycle. This setting determines how long it should wait before starting a new work packet, in multiples of the last work time. This is for when you force-start work from review services.'
            self._repository_processing_rest_percentage_normal.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            #
            
            self._tag_display_processing_panel = ClientGUICommon.StaticBox( self, 'sibling/parent sync processing', can_expand = True, start_expanded = False )
            
            self._tag_display_maintenance_during_idle = QW.QCheckBox( self._tag_display_processing_panel )
            self._tag_display_maintenance_during_active = QW.QCheckBox( self._tag_display_processing_panel )
            tt = 'This can be a real killer. If you are catching up with the PTR and notice a lot of lag bumps, sometimes several seconds long, try turning this off.'
            self._tag_display_maintenance_during_active.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            self._tag_display_processing_work_time_idle = ClientGUITime.TimeDeltaWidget( self._tag_display_processing_panel, min = 0.1, seconds = True, milliseconds = True )
            tt = 'DO NOT CHANGE UNLESS YOU KNOW WHAT YOU ARE DOING. Sibling/parent sync operates on a work-rest cycle. This setting determines how long it should work for in each work packet. Actual work time will normally be a little larger than this. This is for idle mode.'
            self._tag_display_processing_work_time_idle.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            self._tag_display_processing_rest_percentage_idle = ClientGUICommon.BetterSpinBox( self._tag_display_processing_panel, min = 0, max = 100000 )
            tt = 'DO NOT CHANGE UNLESS YOU KNOW WHAT YOU ARE DOING. Sibling/parent sync operates on a work-rest cycle. This setting determines how long it should wait before starting a new work packet, in multiples of the last work time. This is for idle mode.'
            self._tag_display_processing_rest_percentage_idle.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            self._tag_display_processing_work_time_normal = ClientGUITime.TimeDeltaWidget( self._tag_display_processing_panel, min = 0.1, seconds = True, milliseconds = True )
            tt = 'DO NOT CHANGE UNLESS YOU KNOW WHAT YOU ARE DOING. Sibling/parent sync operates on a work-rest cycle. This setting determines how long it should work for in each work packet. Actual work time will normally be a little larger than this. This is for when you force-start work from review services.'
            self._tag_display_processing_work_time_normal.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            self._tag_display_processing_rest_percentage_normal = ClientGUICommon.BetterSpinBox( self._tag_display_processing_panel, min = 0, max = 100000 )
            tt = 'DO NOT CHANGE UNLESS YOU KNOW WHAT YOU ARE DOING. Sibling/parent sync operates on a work-rest cycle. This setting determines how long it should wait before starting a new work packet, in multiples of the last work time. This is for when you force-start work from review services.'
            self._tag_display_processing_rest_percentage_normal.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            self._tag_display_processing_work_time_work_hard = ClientGUITime.TimeDeltaWidget( self._tag_display_processing_panel, min = 0.1, seconds = True, milliseconds = True )
            tt = 'DO NOT CHANGE UNLESS YOU KNOW WHAT YOU ARE DOING. Sibling/parent sync operates on a work-rest cycle. This setting determines how long it should work for in each work packet. Actual work time will normally be a little larger than this. This is for when you force it to work hard through the dialog.'
            self._tag_display_processing_work_time_work_hard.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            self._tag_display_processing_rest_percentage_work_hard = ClientGUICommon.BetterSpinBox( self._tag_display_processing_panel, min = 0, max = 100000 )
            tt = 'DO NOT CHANGE UNLESS YOU KNOW WHAT YOU ARE DOING. Sibling/parent sync operates on a work-rest cycle. This setting determines how long it should wait before starting a new work packet, in multiples of the last work time. This is for when you force it to work hard through the dialog.'
            self._tag_display_processing_rest_percentage_work_hard.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            #
            
            self._potential_duplicates_panel = ClientGUICommon.StaticBox( self, 'potential duplicates search', can_expand = True, start_expanded = False )
            
            self._maintain_similar_files_duplicate_pairs_during_idle = QW.QCheckBox( self._potential_duplicates_panel )
            
            self._maintain_similar_files_duplicate_pairs_during_active = QW.QCheckBox( self._potential_duplicates_panel )
            
            self._potential_duplicates_search_work_time_idle = ClientGUITime.TimeDeltaWidget( self._potential_duplicates_panel, min = 0.02, seconds = True, milliseconds = True )
            tt = 'DO NOT CHANGE UNLESS YOU KNOW WHAT YOU ARE DOING. Potential search operates on a work-rest cycle. This setting determines how long it should work for in each work packet. Actual work time will normally be a little larger than this, and on large databases the minimum work time may be upwards of several seconds.'
            self._potential_duplicates_search_work_time_idle.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            self._potential_duplicates_search_rest_percentage_idle = ClientGUICommon.BetterSpinBox( self._potential_duplicates_panel, min = 0, max = 100000 )
            tt = 'DO NOT CHANGE UNLESS YOU KNOW WHAT YOU ARE DOING. Potential search operates on a work-rest cycle. This setting determines how long it should wait before starting a new work packet, as a percentage of the last work time.'
            self._potential_duplicates_search_rest_percentage_idle.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            self._potential_duplicates_search_work_time_active = ClientGUITime.TimeDeltaWidget( self._potential_duplicates_panel, min = 0.02, seconds = True, milliseconds = True )
            tt = 'DO NOT CHANGE UNLESS YOU KNOW WHAT YOU ARE DOING. Potential search operates on a work-rest cycle. This setting determines how long it should work for in each work packet. Actual work time will normally be a little larger than this, and on large databases the minimum work time may be upwards of several seconds.'
            self._potential_duplicates_search_work_time_active.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            self._potential_duplicates_search_rest_percentage_active = ClientGUICommon.BetterSpinBox( self._potential_duplicates_panel, min = 0, max = 100000 )
            tt = 'DO NOT CHANGE UNLESS YOU KNOW WHAT YOU ARE DOING. Potential search operates on a work-rest cycle. This setting determines how long it should wait before starting a new work packet, as a percentage of the last work time.'
            self._potential_duplicates_search_rest_percentage_active.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            #
            
            self._duplicates_auto_resolution_panel = ClientGUICommon.StaticBox( self, 'duplicates auto-resolution', can_expand = True, start_expanded = False )
            
            self._duplicates_auto_resolution_during_idle = QW.QCheckBox( self._duplicates_auto_resolution_panel )
            
            self._duplicates_auto_resolution_during_active = QW.QCheckBox( self._duplicates_auto_resolution_panel )
            
            self._duplicates_auto_resolution_work_time_idle = ClientGUITime.TimeDeltaWidget( self._duplicates_auto_resolution_panel, min = 0.1, seconds = True, milliseconds = True )
            tt = 'DO NOT CHANGE UNLESS YOU KNOW WHAT YOU ARE DOING. Duplicates auto-resolution operates on a work-rest cycle. This setting determines how long it should work for in each work packet. Actual work time will normally be a little larger than this, and when it hits large files it may be upwards of several seconds.'
            self._duplicates_auto_resolution_work_time_idle.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            self._duplicates_auto_resolution_rest_percentage_idle = ClientGUICommon.BetterSpinBox( self._duplicates_auto_resolution_panel, min = 0, max = 100000 )
            tt = 'DO NOT CHANGE UNLESS YOU KNOW WHAT YOU ARE DOING. Duplicates auto-resolution operates on a work-rest cycle. This setting determines how long it should wait before starting a new work packet, as a percentage of the last work time.'
            self._duplicates_auto_resolution_rest_percentage_idle.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            self._duplicates_auto_resolution_work_time_active = ClientGUITime.TimeDeltaWidget( self._duplicates_auto_resolution_panel, min = 0.1, seconds = True, milliseconds = True )
            tt = 'DO NOT CHANGE UNLESS YOU KNOW WHAT YOU ARE DOING. Duplicates auto-resolution operates on a work-rest cycle. This setting determines how long it should work for in each work packet. Actual work time will normally be a little larger than this, and when it hits large files it may be upwards of several seconds.'
            self._duplicates_auto_resolution_work_time_active.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            self._duplicates_auto_resolution_rest_percentage_active = ClientGUICommon.BetterSpinBox( self._duplicates_auto_resolution_panel, min = 0, max = 100000 )
            tt = 'DO NOT CHANGE UNLESS YOU KNOW WHAT YOU ARE DOING. Duplicates auto-resolution operates on a work-rest cycle. This setting determines how long it should wait before starting a new work packet, as a percentage of the last work time.'
            self._duplicates_auto_resolution_rest_percentage_active.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            #
            
            self._deferred_table_delete_panel = ClientGUICommon.StaticBox( self, 'deferred table delete', can_expand = True, start_expanded = False )
            
            self._deferred_table_delete_work_time_idle = ClientGUITime.TimeDeltaWidget( self._deferred_table_delete_panel, min = 0.1, seconds = True, milliseconds = True )
            tt = 'DO NOT CHANGE UNLESS YOU KNOW WHAT YOU ARE DOING. Deferred table delete operates on a work-rest cycle. This setting determines how long it should work for in each work packet. Actual work time will normally be a little larger than this. This is for idle mode.'
            self._deferred_table_delete_work_time_idle.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            self._deferred_table_delete_rest_percentage_idle = ClientGUICommon.BetterSpinBox( self._deferred_table_delete_panel, min = 0, max = 100000 )
            tt = 'DO NOT CHANGE UNLESS YOU KNOW WHAT YOU ARE DOING. Deferred table delete operates on a work-rest cycle. This setting determines how long it should wait before starting a new work packet, in multiples of the last work time. This is for idle mode.'
            self._deferred_table_delete_rest_percentage_idle.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            self._deferred_table_delete_work_time_normal = ClientGUITime.TimeDeltaWidget( self._deferred_table_delete_panel, min = 0.1, seconds = True, milliseconds = True )
            tt = 'DO NOT CHANGE UNLESS YOU KNOW WHAT YOU ARE DOING. Deferred table delete operates on a work-rest cycle. This setting determines how long it should work for in each work packet. Actual work time will normally be a little larger than this. This is for when you force-start work from review services.'
            self._deferred_table_delete_work_time_normal.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            self._deferred_table_delete_rest_percentage_normal = ClientGUICommon.BetterSpinBox( self._deferred_table_delete_panel, min = 0, max = 100000 )
            tt = 'DO NOT CHANGE UNLESS YOU KNOW WHAT YOU ARE DOING. Deferred table delete operates on a work-rest cycle. This setting determines how long it should wait before starting a new work packet, in multiples of the last work time. This is for when you force-start work from review services.'
            self._deferred_table_delete_rest_percentage_normal.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            self._deferred_table_delete_work_time_work_hard = ClientGUITime.TimeDeltaWidget( self._deferred_table_delete_panel, min = 0.1, seconds = True, milliseconds = True )
            tt = 'DO NOT CHANGE UNLESS YOU KNOW WHAT YOU ARE DOING. Deferred table delete operates on a work-rest cycle. This setting determines how long it should work for in each work packet. Actual work time will normally be a little larger than this. This is for when you force it to work hard through the dialog.'
            self._deferred_table_delete_work_time_work_hard.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            self._deferred_table_delete_rest_percentage_work_hard = ClientGUICommon.BetterSpinBox( self._deferred_table_delete_panel, min = 0, max = 100000 )
            tt = 'DO NOT CHANGE UNLESS YOU KNOW WHAT YOU ARE DOING. Deferred table delete operates on a work-rest cycle. This setting determines how long it should wait before starting a new work packet, in multiples of the last work time. This is for when you force it to work hard through the dialog.'
            self._deferred_table_delete_rest_percentage_work_hard.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            #
            
            self._idle_normal.setChecked( HC.options[ 'idle_normal' ] )
            self._idle_period.SetValue( HC.options['idle_period'] )
            self._idle_mouse_period.SetValue( HC.options['idle_mouse_period'] )
            self._idle_mode_client_api_timeout.SetValue( self._new_options.GetNoneableInteger( 'idle_mode_client_api_timeout' ) )
            self._system_busy_cpu_percent.setValue( self._new_options.GetInteger( 'system_busy_cpu_percent' ) )
            self._system_busy_cpu_count.SetValue( self._new_options.GetNoneableInteger( 'system_busy_cpu_count' ) )
            
            self._idle_shutdown.SetValue( HC.options[ 'idle_shutdown' ] )
            self._idle_shutdown_max_minutes.setValue( HC.options['idle_shutdown_max_minutes'] )
            self._shutdown_work_period.SetValue( self._new_options.GetInteger( 'shutdown_work_period' ) )
            
            self._file_maintenance_during_idle.setChecked( self._new_options.GetBoolean( 'file_maintenance_during_idle' ) )
            
            file_maintenance_idle_throttle_files = self._new_options.GetInteger( 'file_maintenance_idle_throttle_files' )
            file_maintenance_idle_throttle_time_delta = self._new_options.GetInteger( 'file_maintenance_idle_throttle_time_delta' )
            
            file_maintenance_idle_throttle_velocity = ( file_maintenance_idle_throttle_files, file_maintenance_idle_throttle_time_delta )
            
            self._file_maintenance_idle_throttle_velocity.SetValue( file_maintenance_idle_throttle_velocity )
            
            self._file_maintenance_during_active.setChecked( self._new_options.GetBoolean( 'file_maintenance_during_active' ) )
            
            file_maintenance_active_throttle_files = self._new_options.GetInteger( 'file_maintenance_active_throttle_files' )
            file_maintenance_active_throttle_time_delta = self._new_options.GetInteger( 'file_maintenance_active_throttle_time_delta' )
            
            file_maintenance_active_throttle_velocity = ( file_maintenance_active_throttle_files, file_maintenance_active_throttle_time_delta )
            
            self._file_maintenance_active_throttle_velocity.SetValue( file_maintenance_active_throttle_velocity )
            
            self._repository_processing_work_time_very_idle.SetValue( HydrusTime.SecondiseMSFloat( self._new_options.GetInteger( 'repository_processing_work_time_ms_very_idle' ) ) )
            self._repository_processing_rest_percentage_very_idle.setValue( self._new_options.GetInteger( 'repository_processing_rest_percentage_very_idle' ) )
            
            self._repository_processing_work_time_idle.SetValue( HydrusTime.SecondiseMSFloat( self._new_options.GetInteger( 'repository_processing_work_time_ms_idle' ) ) )
            self._repository_processing_rest_percentage_idle.setValue( self._new_options.GetInteger( 'repository_processing_rest_percentage_idle' ) )
            
            self._repository_processing_work_time_normal.SetValue( HydrusTime.SecondiseMSFloat( self._new_options.GetInteger( 'repository_processing_work_time_ms_normal' ) ) )
            self._repository_processing_rest_percentage_normal.setValue( self._new_options.GetInteger( 'repository_processing_rest_percentage_normal' ) )
            
            self._tag_display_maintenance_during_idle.setChecked( self._new_options.GetBoolean( 'tag_display_maintenance_during_idle' ) )
            self._tag_display_maintenance_during_active.setChecked( self._new_options.GetBoolean( 'tag_display_maintenance_during_active' ) )
            
            self._tag_display_processing_work_time_idle.SetValue( HydrusTime.SecondiseMSFloat( self._new_options.GetInteger( 'tag_display_processing_work_time_ms_idle' ) ) )
            self._tag_display_processing_rest_percentage_idle.setValue( self._new_options.GetInteger( 'tag_display_processing_rest_percentage_idle' ) )
            
            self._tag_display_processing_work_time_normal.SetValue( HydrusTime.SecondiseMSFloat( self._new_options.GetInteger( 'tag_display_processing_work_time_ms_normal' ) ) )
            self._tag_display_processing_rest_percentage_normal.setValue( self._new_options.GetInteger( 'tag_display_processing_rest_percentage_normal' ) )
            
            self._tag_display_processing_work_time_work_hard.SetValue( HydrusTime.SecondiseMSFloat( self._new_options.GetInteger( 'tag_display_processing_work_time_ms_work_hard' ) ) )
            self._tag_display_processing_rest_percentage_work_hard.setValue( self._new_options.GetInteger( 'tag_display_processing_rest_percentage_work_hard' ) )
            
            self._maintain_similar_files_duplicate_pairs_during_idle.setChecked( self._new_options.GetBoolean( 'maintain_similar_files_duplicate_pairs_during_idle' ) )
            self._maintain_similar_files_duplicate_pairs_during_active.setChecked( self._new_options.GetBoolean( 'maintain_similar_files_duplicate_pairs_during_active' ) )
            
            self._potential_duplicates_search_work_time_idle.SetValue( HydrusTime.SecondiseMSFloat( self._new_options.GetInteger( 'potential_duplicates_search_work_time_ms_idle' ) ) )
            self._potential_duplicates_search_rest_percentage_idle.setValue( self._new_options.GetInteger( 'potential_duplicates_search_rest_percentage_idle' ) )
            self._potential_duplicates_search_work_time_active.SetValue( HydrusTime.SecondiseMSFloat( self._new_options.GetInteger( 'potential_duplicates_search_work_time_ms_active' ) ) )
            self._potential_duplicates_search_rest_percentage_active.setValue( self._new_options.GetInteger( 'potential_duplicates_search_rest_percentage_active' ) )
            
            self._duplicates_auto_resolution_during_idle.setChecked( self._new_options.GetBoolean( 'duplicates_auto_resolution_during_idle' ) )
            self._duplicates_auto_resolution_during_active.setChecked( self._new_options.GetBoolean( 'duplicates_auto_resolution_during_active' ) )
            
            self._duplicates_auto_resolution_work_time_idle.SetValue( HydrusTime.SecondiseMSFloat( self._new_options.GetInteger( 'duplicates_auto_resolution_work_time_ms_idle' ) ) )
            self._duplicates_auto_resolution_rest_percentage_idle.setValue( self._new_options.GetInteger( 'duplicates_auto_resolution_rest_percentage_idle' ) )
            self._duplicates_auto_resolution_work_time_active.SetValue( HydrusTime.SecondiseMSFloat( self._new_options.GetInteger( 'duplicates_auto_resolution_work_time_ms_active' ) ) )
            self._duplicates_auto_resolution_rest_percentage_active.setValue( self._new_options.GetInteger( 'duplicates_auto_resolution_rest_percentage_active' ) )
            
            self._deferred_table_delete_work_time_idle.SetValue( HydrusTime.SecondiseMSFloat( self._new_options.GetInteger( 'deferred_table_delete_work_time_ms_idle' ) ) )
            self._deferred_table_delete_rest_percentage_idle.setValue( self._new_options.GetInteger( 'deferred_table_delete_rest_percentage_idle' ) )
            
            self._deferred_table_delete_work_time_normal.SetValue( HydrusTime.SecondiseMSFloat( self._new_options.GetInteger( 'deferred_table_delete_work_time_ms_normal' ) ) )
            self._deferred_table_delete_rest_percentage_normal.setValue( self._new_options.GetInteger( 'deferred_table_delete_rest_percentage_normal' ) )
            
            self._deferred_table_delete_work_time_work_hard.SetValue( HydrusTime.SecondiseMSFloat( self._new_options.GetInteger( 'deferred_table_delete_work_time_ms_work_hard' ) ) )
            self._deferred_table_delete_rest_percentage_work_hard.setValue( self._new_options.GetInteger( 'deferred_table_delete_rest_percentage_work_hard' ) )
            
            #
            
            rows = []
            
            rows.append( ( 'Run maintenance jobs when the client is idle and the system is not otherwise busy: ', self._idle_normal ) )
            rows.append( ( 'Permit idle mode if no general browsing activity has occurred in the past: ', self._idle_period ) )
            rows.append( ( 'Permit idle mode if the mouse has not been moved in the past: ', self._idle_mouse_period ) )
            rows.append( ( 'Permit idle mode if no Client API requests in the past: ', self._idle_mode_client_api_timeout ) )
            
            hbox = QP.HBoxLayout()
            
            QP.AddToLayout( hbox, self._system_busy_cpu_percent, CC.FLAGS_CENTER )
            QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText( self._idle_panel, label = '% on ' ), CC.FLAGS_CENTER )
            QP.AddToLayout( hbox, self._system_busy_cpu_count, CC.FLAGS_CENTER )
            
            if HydrusPSUtil.PSUTIL_OK:
                
                num_cores = HydrusPSUtil.psutil.cpu_count()
                
                label = f'(you appear to have {num_cores} cores)'
                
            else:
                
                label = 'You do not have the psutil library, so I do not believe any of these CPU checks will work!'
                
            
            QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText( self._idle_panel, label = label ), CC.FLAGS_CENTER )
            
            rows.append( ( 'Consider the system busy if CPU usage is above: ', hbox ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self._idle_panel, rows )
            
            self._idle_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            rows = []
            
            rows.append( ( 'Run jobs on shutdown: ', self._idle_shutdown ) )
            rows.append( ( 'Only run shutdown jobs once per: ', self._shutdown_work_period ) )
            rows.append( ( 'Max number of minutes to run shutdown jobs: ', self._idle_shutdown_max_minutes ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self._shutdown_panel, rows )
            
            self._shutdown_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            text = '***'
            text += '\n'
            text +='If you are a new user or do not completely understand these options, please do not touch them! Do not set the client to be idle all the time unless you know what you are doing or are testing something and are prepared for potential problems!'
            text += '\n'
            text += '***'
            text += '\n' * 2
            text += 'Sometimes, the client needs to do some heavy maintenance. This could be reformatting the database to keep it running fast or processing a large number of tags from a repository. Typically, these jobs will not allow you to use the gui while they run, and on slower computers--or those with not much memory--they can take a long time to complete.'
            text += '\n' * 2
            text += 'You can set these jobs to run only when the client is idle, or only during shutdown, or neither, or both. If you leave the client on all the time in the background, focusing on \'idle time\' processing is often ideal. If you have a slow computer, relying on \'shutdown\' processing (which you can manually start when convenient), is often better.'
            text += '\n' * 2
            text += 'If the client switches from idle to not idle during a job, it will try to abandon it and give you back control. This is not always possible, and even when it is, it will sometimes take several minutes, particularly on slower machines or those on HDDs rather than SSDs.'
            text += '\n' * 2
            text += 'If the client believes the system is busy, it will generally not start jobs.'
            
            st = ClientGUICommon.BetterStaticText( self._jobs_panel, label = text )
            st.setWordWrap( True )
            
            self._jobs_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
            self._jobs_panel.Add( self._idle_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            self._jobs_panel.Add( self._shutdown_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            #
            
            message = 'Scheduled jobs such as reparsing file metadata and regenerating thumbnails are performed in the background.'
            
            self._file_maintenance_panel.Add( ClientGUICommon.BetterStaticText( self._file_maintenance_panel, label = message ), CC.FLAGS_EXPAND_PERPENDICULAR )
            
            rows = []
            
            rows.append( ( 'Run file maintenance during idle time: ', self._file_maintenance_during_idle ) )
            rows.append( ( 'Idle throttle: ', self._file_maintenance_idle_throttle_velocity ) )
            rows.append( ( 'Run file maintenance during normal time: ', self._file_maintenance_during_active ) )
            rows.append( ( 'Normal throttle: ', self._file_maintenance_active_throttle_velocity ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self._file_maintenance_panel, rows )
            
            self._file_maintenance_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            message = 'Repository processing takes a lot of CPU and works best when it can rip for long periods in idle time.'
            
            self._repository_processing_panel.Add( ClientGUICommon.BetterStaticText( self._repository_processing_panel, label = message ), CC.FLAGS_EXPAND_PERPENDICULAR )
            
            rows = []
            
            rows.append( ( '"Very idle" ideal work packet time: ', self._repository_processing_work_time_very_idle ) )
            rows.append( ( '"Very idle" rest time percentage: ', self._repository_processing_rest_percentage_very_idle ) )
            rows.append( ( '"Idle" ideal work packet time: ', self._repository_processing_work_time_idle ) )
            rows.append( ( '"Idle" rest time percentage: ', self._repository_processing_rest_percentage_idle ) )
            rows.append( ( '"Normal" ideal work packet time: ', self._repository_processing_work_time_normal ) )
            rows.append( ( '"Normal" rest time percentage: ', self._repository_processing_rest_percentage_normal ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self._repository_processing_panel, rows )
            
            self._repository_processing_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            message = 'The database compiles sibling and parent implication calculations in the background. This can use a LOT of CPU in big bumps.'
            
            self._tag_display_processing_panel.Add( ClientGUICommon.BetterStaticText( self._tag_display_processing_panel, label = message ), CC.FLAGS_EXPAND_PERPENDICULAR )
            
            rows = []
            
            rows.append( ( 'Do work in "idle" time: ', self._tag_display_maintenance_during_idle ) )
            rows.append( ( '"Idle" ideal work packet time: ', self._tag_display_processing_work_time_idle ) )
            rows.append( ( '"Idle" rest time percentage: ', self._tag_display_processing_rest_percentage_idle ) )
            rows.append( ( 'Do work in "normal" time: ', self._tag_display_maintenance_during_active ) )
            rows.append( ( '"Normal" ideal work packet time: ', self._tag_display_processing_work_time_normal ) )
            rows.append( ( '"Normal" rest time percentage: ', self._tag_display_processing_rest_percentage_normal ) )
            rows.append( ( '"Work hard" ideal work packet time: ', self._tag_display_processing_work_time_work_hard ) )
            rows.append( ( '"Work hard" rest time percentage: ', self._tag_display_processing_rest_percentage_work_hard ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self._tag_display_processing_panel, rows )
            
            self._tag_display_processing_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            message = 'The discovery of new potential duplicate file pairs (as on the duplicates page, preparation tab) can run automatically.'
            
            self._potential_duplicates_panel.Add( ClientGUICommon.BetterStaticText( self._potential_duplicates_panel, label = message ), CC.FLAGS_EXPAND_PERPENDICULAR )
            
            rows = []
            
            rows.append( ( 'Search for potential duplicates in "idle" time: ', self._maintain_similar_files_duplicate_pairs_during_idle ) )
            rows.append( ( '"Idle" ideal work packet time: ', self._potential_duplicates_search_work_time_idle ) )
            rows.append( ( '"Idle" rest time percentage: ', self._potential_duplicates_search_rest_percentage_idle ) )
            rows.append( ( 'Search for potential duplicates in "normal" time: ', self._maintain_similar_files_duplicate_pairs_during_active ) )
            rows.append( ( '"Normal" ideal work packet time: ', self._potential_duplicates_search_work_time_active ) )
            rows.append( ( '"Normal" rest time percentage: ', self._potential_duplicates_search_rest_percentage_active ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self._potential_duplicates_panel, rows )
            
            self._potential_duplicates_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            message = 'The search, testing, and resolution work of duplicates auto-resolution rules (as on the duplicates page, auto-resolution tab) runs automatically in the background.'
            
            self._duplicates_auto_resolution_panel.Add( ClientGUICommon.BetterStaticText( self._duplicates_auto_resolution_panel, label = message ), CC.FLAGS_EXPAND_PERPENDICULAR )
            
            rows = []
            
            rows.append( ( 'Work duplicates auto-resolution in "idle" time: ', self._duplicates_auto_resolution_during_idle ) )
            rows.append( ( '"Idle" ideal work packet time: ', self._duplicates_auto_resolution_work_time_idle ) )
            rows.append( ( '"Idle" rest time percentage: ', self._duplicates_auto_resolution_rest_percentage_idle ) )
            rows.append( ( 'Work duplicates auto-resolution in "normal" time: ', self._duplicates_auto_resolution_during_active ) )
            rows.append( ( '"Normal" ideal work packet time: ', self._duplicates_auto_resolution_work_time_active ) )
            rows.append( ( '"Normal" rest time percentage: ', self._duplicates_auto_resolution_rest_percentage_active ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self._duplicates_auto_resolution_panel, rows )
            
            self._duplicates_auto_resolution_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            message = 'The database deletes old data in the background.'
            
            self._deferred_table_delete_panel.Add( ClientGUICommon.BetterStaticText( self._deferred_table_delete_panel, label = message ), CC.FLAGS_EXPAND_PERPENDICULAR )
            
            rows = []
            
            rows.append( ( '"Idle" ideal work packet time: ', self._deferred_table_delete_work_time_idle ) )
            rows.append( ( '"Idle" rest time percentage: ', self._deferred_table_delete_rest_percentage_idle ) )
            rows.append( ( '"Normal" ideal work packet time: ', self._deferred_table_delete_work_time_normal ) )
            rows.append( ( '"Normal" rest time percentage: ', self._deferred_table_delete_rest_percentage_normal ) )
            rows.append( ( '"Work hard" ideal work packet time: ', self._deferred_table_delete_work_time_work_hard ) )
            rows.append( ( '"Work hard" rest time percentage: ', self._deferred_table_delete_rest_percentage_work_hard ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self._deferred_table_delete_panel, rows )
            
            self._deferred_table_delete_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, self._jobs_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, self._file_maintenance_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, self._repository_processing_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, self._tag_display_processing_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, self._potential_duplicates_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, self._duplicates_auto_resolution_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, self._deferred_table_delete_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.addStretch( 0 )
            
            self.setLayout( vbox )
            
            self._EnableDisableIdleNormal()
            self._EnableDisableIdleShutdown()
            
            self._system_busy_cpu_count.valueChanged.connect( self._EnableDisableCPUPercent )
            
        
        def _EnableDisableCPUPercent( self ):
            
            enabled = self._system_busy_cpu_count.isEnabled() and self._system_busy_cpu_count.GetValue() is not None
            
            self._system_busy_cpu_percent.setEnabled( enabled )
            
        
        def _EnableDisableIdleNormal( self ):
            
            enabled = self._idle_normal.isChecked()
            
            self._idle_period.setEnabled( enabled )
            self._idle_mouse_period.setEnabled( enabled )
            self._idle_mode_client_api_timeout.setEnabled( enabled )
            self._system_busy_cpu_count.setEnabled( enabled )
            
            self._EnableDisableCPUPercent()
            
        
        def _EnableDisableIdleShutdown( self ):
            
            enabled = self._idle_shutdown.GetValue() != CC.IDLE_NOT_ON_SHUTDOWN
            
            self._shutdown_work_period.setEnabled( enabled )
            self._idle_shutdown_max_minutes.setEnabled( enabled )
            
        
        def UpdateOptions( self ):
            
            HC.options[ 'idle_normal' ] = self._idle_normal.isChecked()
            
            HC.options[ 'idle_period' ] = self._idle_period.GetValue()
            HC.options[ 'idle_mouse_period' ] = self._idle_mouse_period.GetValue()
            self._new_options.SetNoneableInteger( 'idle_mode_client_api_timeout', self._idle_mode_client_api_timeout.GetValue() )
            
            self._new_options.SetInteger( 'system_busy_cpu_percent', self._system_busy_cpu_percent.value() )
            self._new_options.SetNoneableInteger( 'system_busy_cpu_count', self._system_busy_cpu_count.GetValue() )
            
            HC.options[ 'idle_shutdown' ] = self._idle_shutdown.GetValue()
            HC.options[ 'idle_shutdown_max_minutes' ] = self._idle_shutdown_max_minutes.value()
            
            self._new_options.SetInteger( 'shutdown_work_period', self._shutdown_work_period.GetValue() )
            
            self._new_options.SetBoolean( 'file_maintenance_during_idle', self._file_maintenance_during_idle.isChecked() )
            
            file_maintenance_idle_throttle_velocity = self._file_maintenance_idle_throttle_velocity.GetValue()
            
            ( file_maintenance_idle_throttle_files, file_maintenance_idle_throttle_time_delta ) = file_maintenance_idle_throttle_velocity
            
            self._new_options.SetInteger( 'file_maintenance_idle_throttle_files', file_maintenance_idle_throttle_files )
            self._new_options.SetInteger( 'file_maintenance_idle_throttle_time_delta', file_maintenance_idle_throttle_time_delta )
            
            self._new_options.SetBoolean( 'file_maintenance_during_active', self._file_maintenance_during_active.isChecked() )
            
            file_maintenance_active_throttle_velocity = self._file_maintenance_active_throttle_velocity.GetValue()
            
            ( file_maintenance_active_throttle_files, file_maintenance_active_throttle_time_delta ) = file_maintenance_active_throttle_velocity
            
            self._new_options.SetInteger( 'file_maintenance_active_throttle_files', file_maintenance_active_throttle_files )
            self._new_options.SetInteger( 'file_maintenance_active_throttle_time_delta', file_maintenance_active_throttle_time_delta )
            
            self._new_options.SetInteger( 'repository_processing_work_time_ms_very_idle', HydrusTime.MillisecondiseS( self._repository_processing_work_time_very_idle.GetValue() ) )
            self._new_options.SetInteger( 'repository_processing_rest_percentage_very_idle', self._repository_processing_rest_percentage_very_idle.value() )
            
            self._new_options.SetInteger( 'repository_processing_work_time_ms_idle', HydrusTime.MillisecondiseS( self._repository_processing_work_time_idle.GetValue() ) )
            self._new_options.SetInteger( 'repository_processing_rest_percentage_idle', self._repository_processing_rest_percentage_idle.value() )
            
            self._new_options.SetInteger( 'repository_processing_work_time_ms_normal', HydrusTime.MillisecondiseS( self._repository_processing_work_time_normal.GetValue() ) )
            self._new_options.SetInteger( 'repository_processing_rest_percentage_normal', self._repository_processing_rest_percentage_normal.value() )
            
            self._new_options.SetBoolean( 'tag_display_maintenance_during_idle', self._tag_display_maintenance_during_idle.isChecked() )
            self._new_options.SetBoolean( 'tag_display_maintenance_during_active', self._tag_display_maintenance_during_active.isChecked() )
            
            self._new_options.SetInteger( 'tag_display_processing_work_time_ms_idle', HydrusTime.MillisecondiseS( self._tag_display_processing_work_time_idle.GetValue() ) )
            self._new_options.SetInteger( 'tag_display_processing_rest_percentage_idle', self._tag_display_processing_rest_percentage_idle.value() )
            
            self._new_options.SetInteger( 'tag_display_processing_work_time_ms_normal', HydrusTime.MillisecondiseS( self._tag_display_processing_work_time_normal.GetValue() ) )
            self._new_options.SetInteger( 'tag_display_processing_rest_percentage_normal', self._tag_display_processing_rest_percentage_normal.value() )
            
            self._new_options.SetInteger( 'tag_display_processing_work_time_ms_work_hard', HydrusTime.MillisecondiseS( self._tag_display_processing_work_time_work_hard.GetValue() ) )
            self._new_options.SetInteger( 'tag_display_processing_rest_percentage_work_hard', self._tag_display_processing_rest_percentage_work_hard.value() )
            
            self._new_options.SetBoolean( 'maintain_similar_files_duplicate_pairs_during_idle', self._maintain_similar_files_duplicate_pairs_during_idle.isChecked() )
            self._new_options.SetInteger( 'potential_duplicates_search_work_time_ms_idle', HydrusTime.MillisecondiseS( self._potential_duplicates_search_work_time_idle.GetValue() ) )
            self._new_options.SetInteger( 'potential_duplicates_search_rest_percentage_idle', self._potential_duplicates_search_rest_percentage_idle.value() )
            self._new_options.SetBoolean( 'maintain_similar_files_duplicate_pairs_during_active', self._maintain_similar_files_duplicate_pairs_during_active.isChecked() )
            self._new_options.SetInteger( 'potential_duplicates_search_work_time_ms_active', HydrusTime.MillisecondiseS( self._potential_duplicates_search_work_time_active.GetValue() ) )
            self._new_options.SetInteger( 'potential_duplicates_search_rest_percentage_active', self._potential_duplicates_search_rest_percentage_active.value() )
            
            self._new_options.SetBoolean( 'duplicates_auto_resolution_during_idle', self._duplicates_auto_resolution_during_idle.isChecked() )
            self._new_options.SetInteger( 'duplicates_auto_resolution_work_time_ms_idle', HydrusTime.MillisecondiseS( self._duplicates_auto_resolution_work_time_idle.GetValue() ) )
            self._new_options.SetInteger( 'duplicates_auto_resolution_rest_percentage_idle', self._duplicates_auto_resolution_rest_percentage_idle.value() )
            self._new_options.SetBoolean( 'duplicates_auto_resolution_during_active', self._duplicates_auto_resolution_during_active.isChecked() )
            self._new_options.SetInteger( 'duplicates_auto_resolution_work_time_ms_active', HydrusTime.MillisecondiseS( self._duplicates_auto_resolution_work_time_active.GetValue() ) )
            self._new_options.SetInteger( 'duplicates_auto_resolution_rest_percentage_active', self._duplicates_auto_resolution_rest_percentage_active.value() )
            
            self._new_options.SetInteger( 'deferred_table_delete_work_time_ms_idle', HydrusTime.MillisecondiseS( self._deferred_table_delete_work_time_idle.GetValue() ) )
            self._new_options.SetInteger( 'deferred_table_delete_rest_percentage_idle', self._deferred_table_delete_rest_percentage_idle.value() )
            
            self._new_options.SetInteger( 'deferred_table_delete_work_time_ms_normal', HydrusTime.MillisecondiseS( self._deferred_table_delete_work_time_normal.GetValue() ) )
            self._new_options.SetInteger( 'deferred_table_delete_rest_percentage_normal', self._deferred_table_delete_rest_percentage_normal.value() )
            
            self._new_options.SetInteger( 'deferred_table_delete_work_time_ms_work_hard', HydrusTime.MillisecondiseS( self._deferred_table_delete_work_time_work_hard.GetValue() ) )
            self._new_options.SetInteger( 'deferred_table_delete_rest_percentage_work_hard', self._deferred_table_delete_rest_percentage_work_hard.value() )
            
        
    
    class _MediaViewerPanel( OptionsPagePanel ):
        
        def __init__( self, parent ):
            
            super().__init__( parent )
            
            self._new_options = CG.client_controller.new_options
            
            #
            
            focus_panel = ClientGUICommon.StaticBox( self, 'closing focus' )
            
            self._focus_media_tab_on_viewer_close_if_possible = QW.QCheckBox( focus_panel )
            self._focus_media_tab_on_viewer_close_if_possible.setToolTip( ClientGUIFunctions.WrapToolTip( 'If the search page you opened a media viewer from is still open, navigate back to it upon media viewer close. Useful if you use multiple media viewers launched from different pages. There is also a shortcut action to perform this on an individual basis.' ) )
            
            self._focus_media_thumb_on_viewer_close = QW.QCheckBox( focus_panel )
            self._focus_media_thumb_on_viewer_close.setToolTip( ClientGUIFunctions.WrapToolTip( 'When you close a Media Viewer, it normally tells the original search page to change the current thumbnail selection to whatever you closed the media viewer on. If you prefer this not to happen, uncheck this!' ) )
            
            self._activate_main_gui_on_focusing_viewer_close = QW.QCheckBox( focus_panel )
            self._activate_main_gui_on_focusing_viewer_close.setToolTip( ClientGUIFunctions.WrapToolTip( 'This will "activate" the Main GUI Window when any Media Viewer closes with with a "focusing" action, either because you set the options above, or, more importantly, if they are set off above but you do it using a shortcut. This will bring the Main GUI to the front and give it keyboard focus. Try this if you regularly use multiple viewers and need fine control over the focus stack.' ) )
            
            self._activate_main_gui_on_viewer_close = QW.QCheckBox( focus_panel )
            self._activate_main_gui_on_viewer_close.setToolTip( ClientGUIFunctions.WrapToolTip( 'This will "activate" the Main GUI Window when any Media Viewer closes, which should bring it to the front and give it keyboard focus. Try this if your OS is playing funny games with focus when a media viewer closes.' ) )
            
            #
            
            media_viewer_panel = ClientGUICommon.StaticBox( self, 'mouse and animations' )
            
            self._animated_scanbar_height = ClientGUICommon.BetterSpinBox( media_viewer_panel, min=1, max=255 )
            self._animated_scanbar_hide_height = ClientGUICommon.NoneableSpinCtrl( media_viewer_panel, 5, none_phrase = 'no, hide it', min = 1, max = 255, unit = 'px' )
            self._animated_scanbar_nub_width = ClientGUICommon.BetterSpinBox( media_viewer_panel, min=1, max=63 )
            
            self._media_viewer_cursor_autohide_time_ms = ClientGUICommon.NoneableSpinCtrl( media_viewer_panel, 700, none_phrase = 'do not autohide', min = 100, max = 100000, unit = 'ms' )
            
            self._disallow_media_drags_on_duration_media = QW.QCheckBox( media_viewer_panel )
            
            self._anchor_and_hide_canvas_drags = QW.QCheckBox( media_viewer_panel )
            self._touchscreen_canvas_drags_unanchor = QW.QCheckBox( media_viewer_panel )
            
            #
            
            slideshow_panel = ClientGUICommon.StaticBox( self, 'slideshows' )
            
            self._slideshow_durations = QW.QLineEdit( slideshow_panel )
            self._slideshow_durations.setToolTip( ClientGUIFunctions.WrapToolTip( 'This is a bit hacky, but whatever you have here, in comma-separated floats, will end up in the slideshow menu in the media viewer.' ) )
            self._slideshow_durations.textChanged.connect( self.EventSlideshowChanged )
            
            self._slideshow_always_play_duration_media_once_through = QW.QCheckBox( slideshow_panel )
            self._slideshow_always_play_duration_media_once_through.setToolTip( ClientGUIFunctions.WrapToolTip( 'If this is on, then a slideshow will not move on until the current duration-having media has played once through.' ) )
            self._slideshow_always_play_duration_media_once_through.clicked.connect( self.EventSlideshowChanged )
            
            self._slideshow_short_duration_loop_seconds = ClientGUICommon.NoneableSpinCtrl( slideshow_panel, 10, none_phrase = 'do not use', min = 1, max = 86400, unit = 's' )
            tt = '(Ensures very short loops play for a bit, but not five minutes) A slideshow will move on early if the current duration-having media has a duration less than this many seconds (and this is less than the overall slideshow period).'
            self._slideshow_short_duration_loop_seconds.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            self._slideshow_short_duration_loop_percentage = ClientGUICommon.NoneableSpinCtrl( slideshow_panel, 20, none_phrase = 'do not use', min = 1, max = 99, unit = '%' )
            tt = '(Ensures short videos play for a bit, but not twenty minutes) A slideshow will move on early if the current duration-having media has a duration less than this percentage of the overall slideshow period.'
            self._slideshow_short_duration_loop_percentage.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            self._slideshow_short_duration_cutoff_percentage = ClientGUICommon.NoneableSpinCtrl( slideshow_panel, 75, none_phrase = 'do not use', min = 1, max = 99, unit = '%' )
            tt = '(Ensures that slightly shorter videos move the slideshow cleanly along as soon as they are done) A slideshow will move on early if the current duration-having media will have played exactly once through between this many percent and 100% of the slideshow period.'
            self._slideshow_short_duration_cutoff_percentage.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            self._slideshow_long_duration_overspill_percentage = ClientGUICommon.NoneableSpinCtrl( slideshow_panel, 50, none_phrase = 'do not use', min = 1, max = 500, unit = '%' )
            tt = '(Ensures slightly longer videos will not get cut off right at the end) A slideshow will delay moving on if playing the current duration-having media would stretch the overall slideshow period less than this amount.'
            self._slideshow_long_duration_overspill_percentage.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            #
            
            self._focus_media_tab_on_viewer_close_if_possible.setChecked( self._new_options.GetBoolean( 'focus_media_tab_on_viewer_close_if_possible' ) )
            self._focus_media_thumb_on_viewer_close.setChecked( self._new_options.GetBoolean( 'focus_media_thumb_on_viewer_close' ) )
            self._activate_main_gui_on_focusing_viewer_close.setChecked( self._new_options.GetBoolean( 'activate_main_gui_on_focusing_viewer_close' ) )
            self._activate_main_gui_on_viewer_close.setChecked( self._new_options.GetBoolean( 'activate_main_gui_on_viewer_close' ) )
            
            self._animated_scanbar_height.setValue( self._new_options.GetInteger( 'animated_scanbar_height' ) )
            self._animated_scanbar_nub_width.setValue( self._new_options.GetInteger( 'animated_scanbar_nub_width' ) )
            
            self._animated_scanbar_hide_height.SetValue( 5 )
            self._animated_scanbar_hide_height.SetValue( self._new_options.GetNoneableInteger( 'animated_scanbar_hide_height' ) )
            
            self._media_viewer_cursor_autohide_time_ms.SetValue( self._new_options.GetNoneableInteger( 'media_viewer_cursor_autohide_time_ms' ) )
            self._disallow_media_drags_on_duration_media.setChecked( self._new_options.GetBoolean( 'disallow_media_drags_on_duration_media' ) )
            self._anchor_and_hide_canvas_drags.setChecked( self._new_options.GetBoolean( 'anchor_and_hide_canvas_drags' ) )
            self._touchscreen_canvas_drags_unanchor.setChecked( self._new_options.GetBoolean( 'touchscreen_canvas_drags_unanchor' ) )
            
            slideshow_durations = self._new_options.GetSlideshowDurations()
            
            self._slideshow_durations.setText( ','.join( ( str( slideshow_duration ) for slideshow_duration in slideshow_durations ) ) )
            
            self._slideshow_always_play_duration_media_once_through.setChecked( self._new_options.GetBoolean( 'slideshow_always_play_duration_media_once_through' ) )
            self._slideshow_short_duration_loop_seconds.SetValue( self._new_options.GetNoneableInteger( 'slideshow_short_duration_loop_seconds' ) )
            self._slideshow_short_duration_loop_percentage.SetValue( self._new_options.GetNoneableInteger( 'slideshow_short_duration_loop_percentage' ) )
            self._slideshow_short_duration_cutoff_percentage.SetValue( self._new_options.GetNoneableInteger( 'slideshow_short_duration_cutoff_percentage' ) )
            self._slideshow_long_duration_overspill_percentage.SetValue( self._new_options.GetNoneableInteger( 'slideshow_long_duration_overspill_percentage' ) )
            
            #
            
            rows = []
            
            rows.append( ( 'When closing the media viewer, re-select original search page: ', self._focus_media_tab_on_viewer_close_if_possible ) )
            rows.append( ( 'When closing the media viewer, tell original search page to select exit media: ', self._focus_media_thumb_on_viewer_close ) )
            rows.append( ( 'ADVANCED: When closing the media viewer with the above focusing options, activate Main GUI: ', self._activate_main_gui_on_focusing_viewer_close ) )
            rows.append( ( 'DEBUG: When closing the media viewer at any time, activate Main GUI: ', self._activate_main_gui_on_viewer_close ) )
            
            gridbox = ClientGUICommon.WrapInGrid( focus_panel, rows )
            
            focus_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            rows = []
            
            rows.append( ( 'Time until mouse cursor autohides on media viewer:', self._media_viewer_cursor_autohide_time_ms ) )
            rows.append( ( 'Animation scanbar height:', self._animated_scanbar_height ) )
            rows.append( ( 'Animation scanbar height when mouse away:', self._animated_scanbar_hide_height ) )
            rows.append( ( 'Animation scanbar nub width:', self._animated_scanbar_nub_width ) )
            rows.append( ( 'Do not allow mouse media drag-panning when the media has duration:', self._disallow_media_drags_on_duration_media ) )
            rows.append( ( 'RECOMMEND WINDOWS ONLY: Hide and anchor mouse cursor on media viewer drags:', self._anchor_and_hide_canvas_drags ) )
            rows.append( ( 'RECOMMEND WINDOWS ONLY: If set to hide and anchor, undo on apparent touchscreen drag:', self._touchscreen_canvas_drags_unanchor ) )
            
            media_viewer_gridbox = ClientGUICommon.WrapInGrid( media_viewer_panel, rows )
            
            media_viewer_panel.Add( media_viewer_gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            rows = []
            
            rows.append( ( 'Slideshow durations:', self._slideshow_durations ) )
            rows.append( ( 'Always play media once through before moving on:', self._slideshow_always_play_duration_media_once_through ) )
            rows.append( ( 'Slideshow short-media skip seconds threshold:', self._slideshow_short_duration_loop_seconds ) )
            rows.append( ( 'Slideshow short-media skip percentage threshold:', self._slideshow_short_duration_loop_percentage ) )
            rows.append( ( 'Slideshow shorter-media cutoff percentage threshold:', self._slideshow_short_duration_cutoff_percentage ) )
            rows.append( ( 'Slideshow long-media allowed delay percentage threshold:', self._slideshow_long_duration_overspill_percentage ) )
            
            slideshow_gridbox = ClientGUICommon.WrapInGrid( slideshow_panel, rows )
            
            slideshow_panel.Add( slideshow_gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, media_viewer_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, slideshow_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, focus_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.addStretch( 0 )
            
            self.setLayout( vbox )
            
        
        def EventSlideshowChanged( self, text ):
            
            try:
                
                slideshow_durations = [ float( slideshow_duration ) for slideshow_duration in self._slideshow_durations.text().split( ',' ) ]
                
                self._slideshow_durations.setObjectName( '' )
                
            except ValueError:
                
                self._slideshow_durations.setObjectName( 'HydrusInvalid' )
                
            
            self._slideshow_durations.style().polish( self._slideshow_durations )
            
            self._slideshow_durations.update()
            
            always_once_through = self._slideshow_always_play_duration_media_once_through.isChecked()
            
            self._slideshow_long_duration_overspill_percentage.setEnabled( not always_once_through )
            
        
        def UpdateOptions( self ):
            
            self._new_options.SetBoolean( 'focus_media_tab_on_viewer_close_if_possible', self._focus_media_tab_on_viewer_close_if_possible.isChecked() )
            self._new_options.SetBoolean( 'focus_media_thumb_on_viewer_close', self._focus_media_thumb_on_viewer_close.isChecked() )
            self._new_options.SetBoolean( 'activate_main_gui_on_focusing_viewer_close', self._activate_main_gui_on_focusing_viewer_close.isChecked() )
            self._new_options.SetBoolean( 'activate_main_gui_on_viewer_close', self._activate_main_gui_on_viewer_close.isChecked() )
            
            self._new_options.SetBoolean( 'disallow_media_drags_on_duration_media', self._disallow_media_drags_on_duration_media.isChecked() )
            self._new_options.SetBoolean( 'anchor_and_hide_canvas_drags', self._anchor_and_hide_canvas_drags.isChecked() )
            self._new_options.SetBoolean( 'touchscreen_canvas_drags_unanchor', self._touchscreen_canvas_drags_unanchor.isChecked() )
            
            self._new_options.SetNoneableInteger( 'media_viewer_cursor_autohide_time_ms', self._media_viewer_cursor_autohide_time_ms.GetValue() )
            
            self._new_options.SetInteger( 'animated_scanbar_height', self._animated_scanbar_height.value() )
            self._new_options.SetInteger( 'animated_scanbar_nub_width', self._animated_scanbar_nub_width.value() )
            
            self._new_options.SetNoneableInteger( 'animated_scanbar_hide_height', self._animated_scanbar_hide_height.GetValue() )
            
            try:
                
                slideshow_durations = [ float( slideshow_duration ) for slideshow_duration in self._slideshow_durations.text().split( ',' ) ]
                
                slideshow_durations = [ slideshow_duration for slideshow_duration in slideshow_durations if slideshow_duration > 0.0 ]
                
                if len( slideshow_durations ) > 0:
                    
                    self._new_options.SetSlideshowDurations( slideshow_durations )
                    
                
            except ValueError:
                
                HydrusData.ShowText( 'Could not parse those slideshow durations, so they were not saved!' )
                
            
            self._new_options.SetBoolean( 'slideshow_always_play_duration_media_once_through', self._slideshow_always_play_duration_media_once_through.isChecked() )
            self._new_options.SetNoneableInteger( 'slideshow_short_duration_loop_percentage', self._slideshow_short_duration_loop_percentage.GetValue() )
            self._new_options.SetNoneableInteger( 'slideshow_short_duration_loop_seconds', self._slideshow_short_duration_loop_seconds.GetValue() )
            self._new_options.SetNoneableInteger( 'slideshow_short_duration_cutoff_percentage', self._slideshow_short_duration_cutoff_percentage.GetValue() )
            self._new_options.SetNoneableInteger( 'slideshow_long_duration_overspill_percentage', self._slideshow_long_duration_overspill_percentage.GetValue() )
            
        
    
    class _MediaViewerHoversPanel( OptionsPagePanel ):
        
        def __init__( self, parent ):
            
            super().__init__( parent )
            
            self._new_options = CG.client_controller.new_options
            
            #
            
            media_canvas_panel = ClientGUICommon.StaticBox( self, 'hover windows and background' )
            
            self._draw_tags_hover_in_media_viewer_background = QW.QCheckBox( media_canvas_panel )
            self._draw_tags_hover_in_media_viewer_background.setToolTip( ClientGUIFunctions.WrapToolTip( 'Draw the left list of tags in the background of the media viewer.' ) )
            self._disable_tags_hover_in_media_viewer = QW.QCheckBox( media_canvas_panel )
            self._disable_tags_hover_in_media_viewer.setToolTip( ClientGUIFunctions.WrapToolTip( 'Disable hovering on the left list of tags in the media viewer (does not affect background draw).' ) )
            self._draw_top_hover_in_media_viewer_background = QW.QCheckBox( media_canvas_panel )
            self._draw_top_hover_in_media_viewer_background.setToolTip( ClientGUIFunctions.WrapToolTip( 'Draw the center-top file metadata in the background of the media viewer.' ) )
            self._draw_top_right_hover_in_media_viewer_background = QW.QCheckBox( media_canvas_panel )
            self._draw_top_right_hover_in_media_viewer_background.setToolTip( ClientGUIFunctions.WrapToolTip( 'Draw the top-right ratings, inbox and URL information in the background of the media viewer.' ) )
            self._disable_top_right_hover_in_media_viewer = QW.QCheckBox( media_canvas_panel )
            self._disable_top_right_hover_in_media_viewer.setToolTip( ClientGUIFunctions.WrapToolTip( 'Disable hovering on the top-right ratings, inbox and URL information in the media viewer (does not affect background draw).' ) )
            self._draw_notes_hover_in_media_viewer_background = QW.QCheckBox( media_canvas_panel )
            self._draw_notes_hover_in_media_viewer_background.setToolTip( ClientGUIFunctions.WrapToolTip( 'Draw the right list of notes in the background of the media viewer.' ) )
            self._draw_bottom_right_index_in_media_viewer_background = QW.QCheckBox( media_canvas_panel )
            self._draw_bottom_right_index_in_media_viewer_background.setToolTip( ClientGUIFunctions.WrapToolTip( 'Draw the bottom-right index string in the background of the media viewer.' ) )
            
            self._use_nice_resolution_strings = QW.QCheckBox( media_canvas_panel )
            self._use_nice_resolution_strings.setToolTip( ClientGUIFunctions.WrapToolTip( 'Use "1080p" instead of "1920x1080" for common resolutions.' ) )
            
            #
            
            top_hover_summary_panel = ClientGUICommon.StaticBox( self, 'top hover file summary' )
            
            self._file_info_line_consider_archived_interesting = QW.QCheckBox( top_hover_summary_panel )
            self._file_info_line_consider_archived_interesting.setToolTip( ClientGUIFunctions.WrapToolTip( 'Should we show the fact a file is archived in the top hover file info summary?' ) )
            
            self._file_info_line_consider_archived_time_interesting = QW.QCheckBox( top_hover_summary_panel )
            self._file_info_line_consider_archived_time_interesting.setToolTip( ClientGUIFunctions.WrapToolTip( 'If we show the archived status, should we show when it happened?' ) )
            
            self._file_info_line_consider_file_services_interesting = QW.QCheckBox( top_hover_summary_panel )
            self._file_info_line_consider_file_services_interesting.setToolTip( ClientGUIFunctions.WrapToolTip( 'Should we show all the file services a file is in in the top hover file info summary?' ) )
            
            self._file_info_line_consider_file_services_import_times_interesting = QW.QCheckBox( top_hover_summary_panel )
            self._file_info_line_consider_file_services_import_times_interesting.setToolTip( ClientGUIFunctions.WrapToolTip( 'If we show the file services, should we show when they were added?' ) )
            
            self._file_info_line_consider_trash_time_interesting = QW.QCheckBox( top_hover_summary_panel )
            self._file_info_line_consider_trash_time_interesting.setToolTip( ClientGUIFunctions.WrapToolTip( 'Should we show the time a file is trashed in the top hover file info summary?' ) )
            
            self._file_info_line_consider_trash_reason_interesting = QW.QCheckBox( top_hover_summary_panel )
            self._file_info_line_consider_trash_reason_interesting.setToolTip( ClientGUIFunctions.WrapToolTip( 'Should we show the reason a file is trashed in the top hover file info summary?' ) )
            
            self._hide_uninteresting_modified_time = QW.QCheckBox( top_hover_summary_panel )
            self._hide_uninteresting_modified_time.setToolTip( ClientGUIFunctions.WrapToolTip( 'If the file has a modified time similar to its import time (specifically, the number of seconds since both events differs by less than 10%), hide the modified time in the top hover file info summary.' ) )
            
            #
            
            preview_hovers_panel = ClientGUICommon.StaticBox( self, 'preview window hovers' )
            
            self._preview_window_hover_top_right_shows_popup = QW.QCheckBox( preview_hovers_panel )
            self._preview_window_hover_top_right_shows_popup.setToolTip( ClientGUIFunctions.WrapToolTip( 'When you hover over the top right of the preview window, show the same top right popup window as in the media viewer.' ) )
            
            self._draw_top_right_hover_in_preview_window_background = QW.QCheckBox( preview_hovers_panel )
            self._draw_top_right_hover_in_preview_window_background.setToolTip( ClientGUIFunctions.WrapToolTip( 'Also draw the top-right hover window in the background of the preview window.' ) )
            
            #
            
            self._draw_tags_hover_in_media_viewer_background.setChecked( self._new_options.GetBoolean( 'draw_tags_hover_in_media_viewer_background' ) )
            self._disable_tags_hover_in_media_viewer.setChecked( self._new_options.GetBoolean( 'disable_tags_hover_in_media_viewer' ) )
            self._draw_top_hover_in_media_viewer_background.setChecked( self._new_options.GetBoolean( 'draw_top_hover_in_media_viewer_background' ) )
            self._draw_top_right_hover_in_media_viewer_background.setChecked( self._new_options.GetBoolean( 'draw_top_right_hover_in_media_viewer_background' ) )
            self._disable_top_right_hover_in_media_viewer.setChecked( self._new_options.GetBoolean( 'disable_top_right_hover_in_media_viewer' ) )
            self._draw_notes_hover_in_media_viewer_background.setChecked( self._new_options.GetBoolean( 'draw_notes_hover_in_media_viewer_background' ) )
            self._draw_bottom_right_index_in_media_viewer_background.setChecked( self._new_options.GetBoolean( 'draw_bottom_right_index_in_media_viewer_background' ) )
            self._use_nice_resolution_strings.setChecked( self._new_options.GetBoolean( 'use_nice_resolution_strings' ) )
            
            self._file_info_line_consider_archived_interesting.setChecked( self._new_options.GetBoolean( 'file_info_line_consider_archived_interesting' ) )
            self._file_info_line_consider_archived_time_interesting.setChecked( self._new_options.GetBoolean( 'file_info_line_consider_archived_time_interesting' ) )
            self._file_info_line_consider_file_services_interesting.setChecked( self._new_options.GetBoolean( 'file_info_line_consider_file_services_interesting' ) )
            self._file_info_line_consider_file_services_import_times_interesting.setChecked( self._new_options.GetBoolean( 'file_info_line_consider_file_services_import_times_interesting' ) )
            self._file_info_line_consider_trash_time_interesting.setChecked( self._new_options.GetBoolean( 'file_info_line_consider_trash_time_interesting' ) )
            self._file_info_line_consider_trash_reason_interesting.setChecked( self._new_options.GetBoolean( 'file_info_line_consider_trash_reason_interesting' ) )
            self._hide_uninteresting_modified_time.setChecked( self._new_options.GetBoolean( 'hide_uninteresting_modified_time' ) )
            
            self._preview_window_hover_top_right_shows_popup.setChecked( self._new_options.GetBoolean( 'preview_window_hover_top_right_shows_popup' ) )
            self._draw_top_right_hover_in_preview_window_background.setChecked( self._new_options.GetBoolean( 'draw_top_right_hover_in_preview_window_background' ) )
            
            #
            
            rows = []
            
            rows.append( ( 'Draw tags hover-window information in the background of the viewer:', self._draw_tags_hover_in_media_viewer_background ) )
            rows.append( ( 'Do not pop-in tags hover-window on mouseover:', self._disable_tags_hover_in_media_viewer ) )
            rows.append( ( 'Draw top hover-window information in the background of the viewer:', self._draw_top_hover_in_media_viewer_background ) )
            rows.append( ( 'Draw top-right hover-window information in the background of the viewer:', self._draw_top_right_hover_in_media_viewer_background ) )
            rows.append( ( 'Do not pop-in top-right hover-window on mouseover:', self._disable_top_right_hover_in_media_viewer ) )
            rows.append( ( 'Draw notes hover-window information in the background of the viewer:', self._draw_notes_hover_in_media_viewer_background ) )
            rows.append( ( 'Draw bottom-right index text in the background of the viewer:', self._draw_bottom_right_index_in_media_viewer_background ) )
            rows.append( ( 'Swap in common resolution labels:', self._use_nice_resolution_strings ) )
            
            media_canvas_gridbox = ClientGUICommon.WrapInGrid( media_canvas_panel, rows )
            
            media_canvas_panel.Add( media_canvas_gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            rows = []
            
            rows.append( ( 'Show archived status: ', self._file_info_line_consider_archived_interesting ) )
            rows.append( ( 'Show archived time: ', self._file_info_line_consider_archived_time_interesting ) )
            rows.append( ( 'Show file services: ', self._file_info_line_consider_file_services_interesting ) )
            rows.append( ( 'Show file service add times: ', self._file_info_line_consider_file_services_import_times_interesting ) )
            rows.append( ( 'Show file trash times: ', self._file_info_line_consider_trash_time_interesting ) )
            rows.append( ( 'Show file trash reasons: ', self._file_info_line_consider_trash_reason_interesting ) )
            rows.append( ( 'Hide uninteresting modified times: ', self._hide_uninteresting_modified_time ) )
            
            top_hover_summary_gridbox = ClientGUICommon.WrapInGrid( top_hover_summary_panel, rows )
            
            label = 'The top hover window shows a text summary of the file, usually the basic file metadata and the time it was imported. You can show more information here.'
            label += '\n\n'
            label += 'You set this same text to show in the main window status bar for single thumbnail selections under the "thumbnails" page.'
            
            st = ClientGUICommon.BetterStaticText( top_hover_summary_panel, label = label )
            st.setWordWrap( True )
            
            top_hover_summary_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
            top_hover_summary_panel.Add( top_hover_summary_gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            rows = []
            
            rows.append( ( 'Show top-right hover window popup in the preview window: ', self._preview_window_hover_top_right_shows_popup ) )
            rows.append( ( 'Draw top-right hover in preview window background: ', self._draw_top_right_hover_in_preview_window_background ) )
            
            preview_hovers_gridbox = ClientGUICommon.WrapInGrid( preview_hovers_panel, rows )
            
            preview_hovers_panel.Add( preview_hovers_gridbox, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            #
            
            vbox = QP.VBoxLayout()
            
            label = 'Hover windows are the pop-in panels in the Media Viewers. You typically have tags on the left, file info up top, and ratings, notes, and sometimes duplicate controls down the right.'
            st = ClientGUICommon.BetterStaticText( self, label = label )
            st.setWordWrap( True )
            
            QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, media_canvas_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, top_hover_summary_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, preview_hovers_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.addStretch( 0 )
            
            self.setLayout( vbox )
            
            self._file_info_line_consider_archived_interesting.clicked.connect( self._UpdateFileInfoLineWidgets )
            self._file_info_line_consider_file_services_interesting.clicked.connect( self._UpdateFileInfoLineWidgets )
            
            self._UpdateFileInfoLineWidgets()
            
        
        def _UpdateFileInfoLineWidgets( self ):
            
            self._file_info_line_consider_archived_time_interesting.setEnabled( self._file_info_line_consider_archived_interesting.isChecked() )
            self._file_info_line_consider_file_services_import_times_interesting.setEnabled( self._file_info_line_consider_file_services_interesting.isChecked() )
            
        
        def UpdateOptions( self ):
            
            self._new_options.SetBoolean( 'draw_tags_hover_in_media_viewer_background', self._draw_tags_hover_in_media_viewer_background.isChecked() )
            self._new_options.SetBoolean( 'disable_tags_hover_in_media_viewer', self._disable_tags_hover_in_media_viewer.isChecked() )
            self._new_options.SetBoolean( 'draw_top_hover_in_media_viewer_background', self._draw_top_hover_in_media_viewer_background.isChecked() )
            self._new_options.SetBoolean( 'draw_top_right_hover_in_media_viewer_background', self._draw_top_right_hover_in_media_viewer_background.isChecked() )
            self._new_options.SetBoolean( 'disable_top_right_hover_in_media_viewer', self._disable_top_right_hover_in_media_viewer.isChecked() )
            self._new_options.SetBoolean( 'draw_notes_hover_in_media_viewer_background', self._draw_notes_hover_in_media_viewer_background.isChecked() )
            self._new_options.SetBoolean( 'draw_bottom_right_index_in_media_viewer_background', self._draw_bottom_right_index_in_media_viewer_background.isChecked() )
            self._new_options.SetBoolean( 'use_nice_resolution_strings', self._use_nice_resolution_strings.isChecked() )
            
            self._new_options.SetBoolean( 'preview_window_hover_top_right_shows_popup', self._preview_window_hover_top_right_shows_popup.isChecked() )
            self._new_options.SetBoolean( 'draw_top_right_hover_in_preview_window_background', self._draw_top_right_hover_in_preview_window_background.isChecked() )
            
            self._new_options.SetBoolean( 'file_info_line_consider_archived_interesting', self._file_info_line_consider_archived_interesting.isChecked() )
            self._new_options.SetBoolean( 'file_info_line_consider_archived_time_interesting', self._file_info_line_consider_archived_time_interesting.isChecked() )
            self._new_options.SetBoolean( 'file_info_line_consider_file_services_interesting', self._file_info_line_consider_file_services_interesting.isChecked() )
            self._new_options.SetBoolean( 'file_info_line_consider_file_services_import_times_interesting', self._file_info_line_consider_file_services_import_times_interesting.isChecked() )
            self._new_options.SetBoolean( 'file_info_line_consider_trash_time_interesting', self._file_info_line_consider_trash_time_interesting.isChecked() )
            self._new_options.SetBoolean( 'file_info_line_consider_trash_reason_interesting', self._file_info_line_consider_trash_reason_interesting.isChecked() )
            self._new_options.SetBoolean( 'hide_uninteresting_modified_time', self._hide_uninteresting_modified_time.isChecked() )
            
        
    
    class _MediaPlaybackPanel( OptionsPagePanel ):
        
        def __init__( self, parent ):
            
            super().__init__( parent )
            
            self._new_options = CG.client_controller.new_options
            
            #
            
            media_panel = ClientGUICommon.StaticBox( self, 'media' )
            
            self._animation_start_position = ClientGUICommon.BetterSpinBox( media_panel, min=0, max=100 )
            
            self._always_loop_animations = QW.QCheckBox( media_panel )
            self._always_loop_animations.setToolTip( ClientGUIFunctions.WrapToolTip( 'Some GIFS and APNGs have metadata specifying how many times they should be played, usually 1. Uncheck this to obey that number.' ) )
            
            self._mpv_loop_playlist_instead_of_file = QW.QCheckBox( media_panel )
            self._mpv_loop_playlist_instead_of_file.setToolTip( ClientGUIFunctions.WrapToolTip( 'Try this if you get "too many events queued" error in mpv.' ) )
            
            self._do_not_setgeometry_on_an_mpv = QW.QCheckBox( media_panel )
            self._do_not_setgeometry_on_an_mpv.setToolTip( ClientGUIFunctions.WrapToolTip( 'Try this if X11 crashes when you zoom an mpv window.' ) )
            
            self._draw_transparency_checkerboard_media_canvas = QW.QCheckBox( media_panel )
            self._draw_transparency_checkerboard_media_canvas.setToolTip( ClientGUIFunctions.WrapToolTip( 'If unchecked, will fill in with the normal background colour. Does not apply to MPV.' ) )
            
            self._media_zooms = QW.QLineEdit( media_panel )
            self._media_zooms.setToolTip( ClientGUIFunctions.WrapToolTip( 'This is a bit hacky, but whatever you have here, in comma-separated floats, will be what the program steps through as you zoom a media up and down.' ) )
            self._media_zooms.textChanged.connect( self.EventZoomsChanged )
            
            from hydrus.client.gui.canvas import ClientGUICanvasMedia
            
            self._media_viewer_zoom_center = ClientGUICommon.BetterChoice( media_panel )
            
            for zoom_centerpoint_type in ClientGUICanvasMedia.ZOOM_CENTERPOINT_TYPES:
                
                self._media_viewer_zoom_center.addItem( ClientGUICanvasMedia.zoom_centerpoints_str_lookup[ zoom_centerpoint_type ], zoom_centerpoint_type )
                
            
            tt = 'When you zoom in or out, there is a centerpoint about which the image zooms. This point \'stays still\' while the image expands or shrinks around it. Different centerpoints give different feels, especially if you drag images around a bit before zooming.'
            
            self._media_viewer_zoom_center.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )

            #
            
            self._media_viewer_default_zoom_type_override = ClientGUICommon.BetterChoice( media_panel )
            
            for window_zoom_type in ClientGUICanvasMedia.MEDIA_VIEWER_ZOOM_TYPES:
                
                self._media_viewer_default_zoom_type_override.addItem( ClientGUICanvasMedia.media_viewer_zoom_type_str_lookup[ window_zoom_type ], window_zoom_type )
                
            
            self._media_viewer_default_zoom_type_override.setToolTip( ClientGUIFunctions.WrapToolTip( 'You can override the default zoom if you like.' ) )
            
            self._preview_default_zoom_type_override = ClientGUICommon.BetterChoice( media_panel )
            
            for window_zoom_type in ClientGUICanvasMedia.MEDIA_VIEWER_ZOOM_TYPES:
                
                self._preview_default_zoom_type_override.addItem( ClientGUICanvasMedia.media_viewer_zoom_type_str_lookup[ window_zoom_type ], window_zoom_type )
                
            
            self._preview_default_zoom_type_override.setToolTip( ClientGUIFunctions.WrapToolTip( 'You can override the default zoom if you like.' ) )
            
            #
            
            system_panel = ClientGUICommon.StaticBox( self, 'system' )
            
            self._mpv_conf_path = QP.FilePickerCtrl( system_panel, starting_directory = HydrusStaticDir.GetStaticPath( 'mpv-conf' ) )
            
            self._use_system_ffmpeg = QW.QCheckBox( system_panel )
            self._use_system_ffmpeg.setToolTip( ClientGUIFunctions.WrapToolTip( 'FFMPEG is used for file import metadata parsing and the native animation viewer. Check this to always default to the system ffmpeg in your path, rather than using any static ffmpeg in hydrus\'s bin directory. (requires restart)' ) )
            
            self._load_images_with_pil = QW.QCheckBox( system_panel )
            self._load_images_with_pil.setToolTip( ClientGUIFunctions.WrapToolTip( 'We are expecting to drop CV and move to PIL exclusively. This used to be a test option but is now default true and may soon be retired.' ) )
            
            self._do_icc_profile_normalisation = QW.QCheckBox( system_panel )
            self._do_icc_profile_normalisation.setToolTip( ClientGUIFunctions.WrapToolTip( 'Should PIL attempt to load ICC Profiles and normalise the colours of an image? This is usually fine, but when it janks out due to an additional OS/GPU ICC Profile, we can turn it off here.' ) )
            
            self._enable_truncated_images_pil = QW.QCheckBox( system_panel )
            self._enable_truncated_images_pil.setToolTip( ClientGUIFunctions.WrapToolTip( 'Should PIL be allowed to load broken images that are missing some data? This is usually fine, but some years ago we had stability problems when this was mixed with OpenCV. Now it is default on, but if you need to, you can disable it here.' ) )
            
            #
            
            filetype_handling_panel = ClientGUICommon.StaticBox( media_panel, 'per-filetype handling' )
            
            media_viewer_list_panel = ClientGUIListCtrl.BetterListCtrlPanel( filetype_handling_panel )
            
            model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_MEDIA_VIEWER_OPTIONS.ID, self._GetListCtrlDisplayTuple, self._GetListCtrlSortTuple )
            
            self._filetype_handling_listctrl = ClientGUIListCtrl.BetterListCtrlTreeView( media_viewer_list_panel, 20, model, activation_callback = self.EditMediaViewerOptions, use_simple_delete = True )
            
            media_viewer_list_panel.SetListCtrl( self._filetype_handling_listctrl )
            
            media_viewer_list_panel.AddButton( 'add', self.AddMediaViewerOptions, enabled_check_func = self._CanAddMediaViewOption )
            media_viewer_list_panel.AddButton( 'edit', self.EditMediaViewerOptions, enabled_only_on_single_selection = True )
            media_viewer_list_panel.AddDeleteButton( enabled_check_func = self._CanDeleteMediaViewOptions )
            
            #
            
            self._animation_start_position.setValue( int( HC.options['animation_start_position'] * 100.0 ) )
            self._always_loop_animations.setChecked( self._new_options.GetBoolean( 'always_loop_gifs' ) )
            self._mpv_loop_playlist_instead_of_file.setChecked( self._new_options.GetBoolean( 'mpv_loop_playlist_instead_of_file' ) )
            self._do_not_setgeometry_on_an_mpv.setChecked( self._new_options.GetBoolean( 'do_not_setgeometry_on_an_mpv' ) )
            self._draw_transparency_checkerboard_media_canvas.setChecked( self._new_options.GetBoolean( 'draw_transparency_checkerboard_media_canvas' ) )
            
            media_zooms = self._new_options.GetMediaZooms()
            
            self._media_zooms.setText( ','.join( ( str( media_zoom ) for media_zoom in media_zooms ) ) )
            
            self._media_viewer_zoom_center.SetValue( self._new_options.GetInteger( 'media_viewer_zoom_center' ) )

            self._media_viewer_default_zoom_type_override.SetValue( self._new_options.GetInteger( 'media_viewer_default_zoom_type_override' ) )
            self._preview_default_zoom_type_override.SetValue( self._new_options.GetInteger( 'preview_default_zoom_type_override' ) )
            
            self._load_images_with_pil.setChecked( self._new_options.GetBoolean( 'load_images_with_pil' ) )
            self._enable_truncated_images_pil.setChecked( self._new_options.GetBoolean( 'enable_truncated_images_pil' ) )
            self._do_icc_profile_normalisation.setChecked( self._new_options.GetBoolean( 'do_icc_profile_normalisation' ) )
            self._use_system_ffmpeg.setChecked( self._new_options.GetBoolean( 'use_system_ffmpeg' ) )
            
            all_media_view_options = self._new_options.GetMediaViewOptions()
            
            for ( mime, view_options ) in all_media_view_options.items():
                
                data = QP.ListsToTuples( [ mime ] + list( view_options ) )
                
                self._filetype_handling_listctrl.AddData( data )
                
            
            self._filetype_handling_listctrl.Sort()
            
            #
            
            vbox = QP.VBoxLayout()
            
            #
            
            filetype_handling_panel.Add( media_viewer_list_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            #
            
            rows = []
            
            rows.append( ( 'Centerpoint for media zooming:', self._media_viewer_zoom_center ) )
            rows.append( ( 'Media zooms:', self._media_zooms ) )
            rows.append( ( 'Media Viewer default zoom:', self._media_viewer_default_zoom_type_override ) )
            rows.append( ( 'Preview Viewer default zoom:', self._preview_default_zoom_type_override ) )
            rows.append( ( 'Start animations this % in:', self._animation_start_position ) )
            rows.append( ( 'Always Loop Animations:', self._always_loop_animations ) )
            rows.append( ( 'DEBUG: Loop Playlist instead of Loop File in mpv:', self._mpv_loop_playlist_instead_of_file ) )
            rows.append( ( 'LINUX DEBUG: Do not allow combined setGeometry on mpv window:', self._do_not_setgeometry_on_an_mpv ) )
            rows.append( ( 'Draw image transparency as checkerboard:', self._draw_transparency_checkerboard_media_canvas ) )
            
            gridbox = ClientGUICommon.WrapInGrid( media_panel, rows )
            
            media_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            media_panel.Add( filetype_handling_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            #
            
            label = 'MPV loads up the "mpv.conf" file in your database directory. Feel free to edit that file in place any time--it is reloaded in hydrus every time you ok this options dialog. Or, you can overwrite it from another path here.\n\nNote, though, that applying a new mpv.conf will not "reset/undo" any options that are now ommitted in the new file. If you want to remove a line, edit/update the mpv.conf and then restart the client.'
            
            st = ClientGUICommon.BetterStaticText( system_panel, label = label )
            st.setWordWrap( True )
            
            system_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            rows = []
            
            rows.append( ( 'Set a new mpv.conf on dialog ok?:', self._mpv_conf_path ) )
            rows.append( ( 'Prefer system FFMPEG:', self._use_system_ffmpeg ) )
            rows.append( ( 'Apply image ICC Profile colour adjustments:', self._do_icc_profile_normalisation ) )
            rows.append( ( 'Allow loading of truncated images:', self._enable_truncated_images_pil ) )
            rows.append( ( 'Load images with PIL:', self._load_images_with_pil ) )
            
            gridbox = ClientGUICommon.WrapInGrid( system_panel, rows )
            
            system_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            QP.AddToLayout( vbox, media_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
            QP.AddToLayout( vbox, system_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            #
            
            self.setLayout( vbox )
            
        
        def _CanAddMediaViewOption( self ):
            
            return len( self._GetUnsetMediaViewFiletypes() ) > 0
            
        
        def _CanDeleteMediaViewOptions( self ):
            
            deletable_mimes = set( HC.SEARCHABLE_MIMES )
            
            selected_mimes = set()
            
            for ( mime, media_show_action, media_start_paused, media_start_with_embed, preview_show_action, preview_start_paused, preview_start_with_embed, zoom_info ) in self._filetype_handling_listctrl.GetData( only_selected = True ):
                
                selected_mimes.add( mime )
                
            
            if len( selected_mimes ) == 0:
                
                return False
                
            
            all_selected_are_deletable = selected_mimes.issubset( deletable_mimes )
            
            return all_selected_are_deletable
            
        
        def _GetCopyOfGeneralMediaViewOptions( self, desired_mime ):
            
            general_mime_type = HC.mimes_to_general_mimetypes[ desired_mime ]
            
            for ( mime, media_show_action, media_start_paused, media_start_with_embed, preview_show_action, preview_start_paused, preview_start_with_embed, zoom_info ) in self._filetype_handling_listctrl.GetData():
                
                if mime == general_mime_type:
                    
                    view_options = ( desired_mime, media_show_action, media_start_paused, media_start_with_embed, preview_show_action, preview_start_paused, preview_start_with_embed, zoom_info )
                    
                    return view_options
                    
                
            
        
        def _GetUnsetMediaViewFiletypes( self ):
            
            editable_mimes = set( HC.SEARCHABLE_MIMES )
            
            set_mimes = set()
            
            for ( mime, media_show_action, media_start_paused, media_start_with_embed, preview_show_action, preview_start_paused, preview_start_with_embed, zoom_info ) in self._filetype_handling_listctrl.GetData():
                
                set_mimes.add( mime )
                
            
            unset_mimes = editable_mimes.difference( set_mimes )
            
            return unset_mimes
            
        
        def _GetListCtrlDisplayTuple( self, data ):
            
            ( mime, media_show_action, media_start_paused, media_start_with_embed, preview_show_action, preview_start_paused, preview_start_with_embed, zoom_info ) = data
            
            pretty_mime = self._GetPrettyMime( mime )
            
            pretty_media_show_action = CC.media_viewer_action_string_lookup[ media_show_action ]
            
            if media_start_paused:
                
                pretty_media_show_action += ', start paused'
                
            
            if media_start_with_embed:
                
                pretty_media_show_action += ', start with embed button'
                
            
            pretty_preview_show_action = CC.media_viewer_action_string_lookup[ preview_show_action ]
            
            if preview_start_paused:
                
                pretty_preview_show_action += ', start paused'
                
            
            if preview_start_with_embed:
                
                pretty_preview_show_action += ', start with embed button'
                
            
            no_show = { media_show_action, preview_show_action }.isdisjoint( { CC.MEDIA_VIEWER_ACTION_SHOW_WITH_NATIVE, CC.MEDIA_VIEWER_ACTION_SHOW_WITH_MPV, CC.MEDIA_VIEWER_ACTION_SHOW_WITH_QMEDIAPLAYER } )
            
            if no_show:
                
                pretty_zoom_info = ''
                
            else:
                
                pretty_zoom_info = str( zoom_info )
                
            
            display_tuple = ( pretty_mime, pretty_media_show_action, pretty_preview_show_action, pretty_zoom_info )
            
            return display_tuple
            
        
        _GetListCtrlSortTuple = _GetListCtrlDisplayTuple
        
        def _GetPrettyMime( self, mime ):
            
            pretty_mime = HC.mime_string_lookup[ mime ]
            
            if mime not in HC.GENERAL_FILETYPES:
                
                pretty_mime = '{}: {}'.format( HC.mime_string_lookup[ HC.mimes_to_general_mimetypes[ mime ] ], pretty_mime )
                
            
            return pretty_mime
            
        
        def AddMediaViewerOptions( self ):
            
            unset_filetypes = self._GetUnsetMediaViewFiletypes()
            
            if len( unset_filetypes ) == 0:
                
                ClientGUIDialogsMessage.ShowWarning( self, 'You cannot add any more specific filetype options!' )
                
                return
                
            
            choice_tuples = [ ( self._GetPrettyMime( mime ), mime ) for mime in unset_filetypes ]
            
            try:
                
                mime = ClientGUIDialogsQuick.SelectFromList( self, 'select the filetype to add', choice_tuples, sort_tuples = True )
                
            except HydrusExceptions.CancelledException:
                
                return
                
            
            data = self._GetCopyOfGeneralMediaViewOptions( mime )
            
            title = 'add media view options information'
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, title ) as dlg:
                
                panel = ClientGUIScrolledPanelsEdit.EditMediaViewOptionsPanel( dlg, data )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                    
                    new_data = panel.GetValue()
                    
                    self._filetype_handling_listctrl.AddData( new_data, select_sort_and_scroll = True )
                    
                
            
        
        def EditMediaViewerOptions( self ):
            
            data = self._filetype_handling_listctrl.GetTopSelectedData()
            
            if data is None:
                
                return
                
            
            title = 'edit media view options information'
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, title ) as dlg:
                
                panel = ClientGUIScrolledPanelsEdit.EditMediaViewOptionsPanel( dlg, data )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                    
                    new_data = panel.GetValue()
                    
                    self._filetype_handling_listctrl.ReplaceData( data, new_data, sort_and_scroll = True )
                    
                
            
        
        def EventZoomsChanged( self, text ):
            
            try:
                
                media_zooms = [ float( media_zoom ) for media_zoom in self._media_zooms.text().split( ',' ) ]
                
                self._media_zooms.setObjectName( '' )
                
            except ValueError:
                
                self._media_zooms.setObjectName( 'HydrusInvalid' )
                
            
            self._media_zooms.style().polish( self._media_zooms )
            
            self._media_zooms.update()
            
        
        def UpdateOptions( self ):
            
            HC.options[ 'animation_start_position' ] = self._animation_start_position.value() / 100.0
            self._new_options.SetBoolean( 'always_loop_gifs', self._always_loop_animations.isChecked() )
            self._new_options.SetBoolean( 'mpv_loop_playlist_instead_of_file', self._mpv_loop_playlist_instead_of_file.isChecked() )
            self._new_options.SetBoolean( 'do_not_setgeometry_on_an_mpv', self._do_not_setgeometry_on_an_mpv.isChecked() )
            self._new_options.SetBoolean( 'draw_transparency_checkerboard_media_canvas', self._draw_transparency_checkerboard_media_canvas.isChecked() )
            
            try:
                
                media_zooms = [ float( media_zoom ) for media_zoom in self._media_zooms.text().split( ',' ) ]
                
                media_zooms = [ media_zoom for media_zoom in media_zooms if media_zoom > 0.0 ]
                
                if len( media_zooms ) > 0:
                    
                    self._new_options.SetMediaZooms( media_zooms )
                    
                
            except ValueError:
                
                HydrusData.ShowText( 'Could not parse those zooms, so they were not saved!' )
                
            
            self._new_options.SetInteger( 'media_viewer_zoom_center', self._media_viewer_zoom_center.GetValue() )

            self._new_options.SetInteger( 'media_viewer_default_zoom_type_override', self._media_viewer_default_zoom_type_override.GetValue() )
            self._new_options.SetInteger( 'preview_default_zoom_type_override', self._preview_default_zoom_type_override.GetValue() )
            
            self._new_options.SetBoolean( 'load_images_with_pil', self._load_images_with_pil.isChecked() )
            self._new_options.SetBoolean( 'enable_truncated_images_pil', self._enable_truncated_images_pil.isChecked() )
            self._new_options.SetBoolean( 'do_icc_profile_normalisation', self._do_icc_profile_normalisation.isChecked() )
            self._new_options.SetBoolean( 'use_system_ffmpeg', self._use_system_ffmpeg.isChecked() )
            
            mpv_conf_path = self._mpv_conf_path.GetPath()
            
            if mpv_conf_path is not None and mpv_conf_path != '' and os.path.exists( mpv_conf_path ) and os.path.isfile( mpv_conf_path ):
                
                dest_mpv_conf_path = CG.client_controller.GetMPVConfPath()
                
                try:
                    
                    HydrusPaths.MirrorFile( mpv_conf_path, dest_mpv_conf_path )
                    
                except Exception as e:
                    
                    HydrusData.ShowText( 'Could not set the mpv conf path "{}" to "{}"! Error follows!'.format( mpv_conf_path, dest_mpv_conf_path ) )
                    HydrusData.ShowException( e )
                    
                
            
            mimes_to_media_view_options = {}
            
            for data in self._filetype_handling_listctrl.GetData():
                
                data = list( data )
                
                mime = data[0]
                
                value = data[1:]
                
                mimes_to_media_view_options[ mime ] = value
                
            
            self._new_options.SetMediaViewOptions( mimes_to_media_view_options )
            
        
    
    class _NotesPanel( OptionsPagePanel ):
        
        def __init__( self, parent, new_options ):
            
            super().__init__( parent )
            
            self._new_options = new_options
            
            self._start_note_editing_at_end = QW.QCheckBox( self )
            self._start_note_editing_at_end.setToolTip( ClientGUIFunctions.WrapToolTip( 'Otherwise, start the text cursor at the start of the document.' ) )
            
            self._start_note_editing_at_end.setChecked( self._new_options.GetBoolean( 'start_note_editing_at_end' ) )
            
            vbox = QP.VBoxLayout()
            
            rows = []
            
            rows.append( ( 'Start editing notes with the text cursor at the end of the document: ', self._start_note_editing_at_end ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self, rows )
            
            QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            vbox.addStretch( 0 )
            
            self.setLayout( vbox )
            
        
        def UpdateOptions( self ):
            
            self._new_options.SetBoolean( 'start_note_editing_at_end', self._start_note_editing_at_end.isChecked() )
            
        
    
    class _PopupPanel( OptionsPagePanel ):
        
        def __init__( self, parent, new_options ):
            
            super().__init__( parent )
            
            self._new_options = new_options
            
            #
            
            self._popup_panel = ClientGUICommon.StaticBox( self, 'popup window toaster' )
            
            self._popup_message_character_width = ClientGUICommon.BetterSpinBox( self._popup_panel, min = 16, max = 256 )
            
            self._popup_message_force_min_width = QW.QCheckBox( self._popup_panel )
            
            self._freeze_message_manager_when_mouse_on_other_monitor = QW.QCheckBox( self._popup_panel )
            self._freeze_message_manager_when_mouse_on_other_monitor.setToolTip( ClientGUIFunctions.WrapToolTip( 'This is useful if you have a virtual desktop and find the popup manager restores strangely when you hop back to the hydrus display.' ) )
            
            self._freeze_message_manager_when_main_gui_minimised = QW.QCheckBox( self._popup_panel )
            self._freeze_message_manager_when_main_gui_minimised.setToolTip( ClientGUIFunctions.WrapToolTip( 'This is useful if the popup toaster restores strangely after minimised changes.' ) )
            
            self._notify_client_api_cookies = QW.QCheckBox( self._popup_panel )
            self._notify_client_api_cookies.setToolTip( ClientGUIFunctions.WrapToolTip( 'This will make a short-lived popup message every time you get new cookie or http header information over the Client API.' ) )
            
            #
            
            self._popup_message_character_width.setValue( self._new_options.GetInteger( 'popup_message_character_width' ) )
            
            self._popup_message_force_min_width.setChecked( self._new_options.GetBoolean( 'popup_message_force_min_width' ) )
            
            self._freeze_message_manager_when_mouse_on_other_monitor.setChecked( self._new_options.GetBoolean( 'freeze_message_manager_when_mouse_on_other_monitor' ) )
            self._freeze_message_manager_when_main_gui_minimised.setChecked( self._new_options.GetBoolean( 'freeze_message_manager_when_main_gui_minimised' ) )
            
            self._notify_client_api_cookies.setChecked( self._new_options.GetBoolean( 'notify_client_api_cookies' ) )
            
            #
            
            rows = []
            
            rows.append( ( 'Approximate max width of popup messages (in characters): ', self._popup_message_character_width ) )
            rows.append( ( 'BUGFIX: Force this width as the fixed width for all popup messages: ', self._popup_message_force_min_width ) )
            rows.append( ( 'Freeze the popup toaster when mouse is on another display: ', self._freeze_message_manager_when_mouse_on_other_monitor ) )
            rows.append( ( 'Freeze the popup toaster when the main gui is minimised: ', self._freeze_message_manager_when_main_gui_minimised ) )
            rows.append( ( 'Make a short-lived popup on cookie/header updates through the Client API: ', self._notify_client_api_cookies ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self._popup_panel, rows )
            
            self._popup_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, self._popup_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            vbox.addStretch( 0 )
            
            self.setLayout( vbox )
            
        
        def UpdateOptions( self ):
            
            self._new_options.SetInteger( 'popup_message_character_width', self._popup_message_character_width.value() )
            
            self._new_options.SetBoolean( 'popup_message_force_min_width', self._popup_message_force_min_width.isChecked() )
            
            self._new_options.SetBoolean( 'freeze_message_manager_when_mouse_on_other_monitor', self._freeze_message_manager_when_mouse_on_other_monitor.isChecked() )
            self._new_options.SetBoolean( 'freeze_message_manager_when_main_gui_minimised', self._freeze_message_manager_when_main_gui_minimised.isChecked() )
            
            self._new_options.SetBoolean( 'notify_client_api_cookies', self._notify_client_api_cookies.isChecked() )
            
        
    
    class _RatingsPanel( OptionsPagePanel ):
        
        def __init__( self, parent, new_options ):
            
            super().__init__( parent )
            
            self._new_options = new_options
            
            #
            
            media_viewer_rating_panel = ClientGUICommon.StaticBox( self, 'media viewer' )
            
            self._media_viewer_rating_icon_size_px = ClientGUICommon.BetterDoubleSpinBox( media_viewer_rating_panel, min = 1.0, max = 255.0 )
            self._media_viewer_rating_icon_size_px.setToolTip( ClientGUIFunctions.WrapToolTip( 'Set size in pixels for like, numerical, and inc/dec rating icons for clicking on. This will be used for both width and height of the square icons.' ) )
            self._media_viewer_rating_incdec_height_px = ClientGUICommon.BetterDoubleSpinBox( media_viewer_rating_panel, min = 2.0, max = 255.0 )
            self._media_viewer_rating_incdec_height_px.setToolTip( ClientGUIFunctions.WrapToolTip( 'Set height in pixels for inc/dec rectangles in the media viewer. Width will be dynamic based on the rating. It is limited to be between twice and half of the normal ratings icons sizes.' ) )
            
            
            thumbnail_ratings_panel = ClientGUICommon.StaticBox( self, 'thumbnails' )
            
            ( thumbnail_width, thumbnail_height ) = HC.options[ 'thumbnail_dimensions' ]
            
            self._draw_thumbnail_rating_background = QW.QCheckBox( thumbnail_ratings_panel )
            tt = 'If you show any ratings on your thumbnails (you can set this under _services->manage services_), they can get lost in the noise of the underlying thumb. This draws a plain flat rectangle around them in the normal window panel colour. If you think it is ugly, turn it off here!'
            self._draw_thumbnail_rating_background.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            self._draw_thumbnail_rating_icon_size_px = ClientGUICommon.BetterDoubleSpinBox( thumbnail_ratings_panel, min = 1.0, max = thumbnail_width )
            tt = 'This is the size of any rating icons shown in pixels. It will be square, so this is both the width and height.'
            self._draw_thumbnail_rating_icon_size_px.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            self._draw_thumbnail_rating_incdec_height_px = ClientGUICommon.BetterDoubleSpinBox( thumbnail_ratings_panel, min = 2.0, max = thumbnail_width )
            tt = 'This is the width of the inc/dec rating buttons in pixels. Height is 1/2 this. Limited to a range around the rating icon sizes.'
            self._draw_thumbnail_rating_incdec_height_px.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            self._draw_thumbnail_numerical_ratings_collapsed_always = QW.QCheckBox( thumbnail_ratings_panel )
            tt = 'If this is checked, all numerical ratings will show collapsed in thumbnails (\'2/10 ▲\' instead of \'▲▲▼▼▼▼▼▼▼▼\') regardless of the per-service setting.'
            self._draw_thumbnail_numerical_ratings_collapsed_always.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            
            preview_window_rating_panel = ClientGUICommon.StaticBox( self, 'preview window' )
            
            self._preview_window_rating_icon_size_px = ClientGUICommon.BetterDoubleSpinBox( preview_window_rating_panel, min = 1.0, max = 255.0 )
            self._preview_window_rating_icon_size_px.setToolTip( ClientGUIFunctions.WrapToolTip( 'Set size in pixels for like and numerical rating icons for clicking on in the preview window.' ) )
            
            self._preview_window_rating_incdec_height_px  = ClientGUICommon.BetterDoubleSpinBox( preview_window_rating_panel, min = 2.0, max = 255.0 )
            self._preview_window_rating_incdec_height_px.setToolTip( ClientGUIFunctions.WrapToolTip( 'Set height in pixels for inc/dec rectangles in the preview window. Width will be dynamic based on the rating. It is limited to be between twice and half of the normal ratings icons sizes.' ) )
            
            
            manage_ratings_popup_panel = ClientGUICommon.StaticBox( self, 'dialogs' )
            
            self._dialog_rating_icon_size_px = ClientGUICommon.BetterDoubleSpinBox( manage_ratings_popup_panel, min = 6.0, max = 128.0 )
            self._dialog_rating_icon_size_px.setToolTip( ClientGUIFunctions.WrapToolTip( 'Set size in pixels for like and numerical rating icons for clicking on in the \'manage ratings\' dialog.' ) )
            
            self._dialog_rating_incdec_height_px = ClientGUICommon.BetterDoubleSpinBox( manage_ratings_popup_panel, min = 12.0, max = 128.0 )
            self._dialog_rating_incdec_height_px.setToolTip( ClientGUIFunctions.WrapToolTip( 'Set height in pixels for inc/dec rectangles in the \'manage ratings\' dialog.  Width will be dynamic based on the rating. It is limited to be between twice and half of the normal ratings icons sizes.' ) )
            
            #clamp inc/dec rectangles to min 0.5 and max 2x rating stars px for rating size stuff
            self._media_viewer_rating_icon_size_px.editingFinished.connect( self._icon_size_changed )
            self._draw_thumbnail_rating_icon_size_px.editingFinished.connect( self._icon_size_changed )
            self._preview_window_rating_icon_size_px.editingFinished.connect( self._icon_size_changed )
            
            #
            
            self._media_viewer_rating_icon_size_px.setValue( self._new_options.GetFloat( 'media_viewer_rating_icon_size_px' ) )
            self._media_viewer_rating_incdec_height_px.setValue( self._new_options.GetFloat( 'media_viewer_rating_incdec_height_px' ) )
            
            self._draw_thumbnail_rating_background.setChecked( self._new_options.GetBoolean( 'draw_thumbnail_rating_background' ) )
            self._draw_thumbnail_numerical_ratings_collapsed_always.setChecked( self._new_options.GetBoolean( 'draw_thumbnail_numerical_ratings_collapsed_always' ) )
            self._draw_thumbnail_rating_icon_size_px.setValue( self._new_options.GetFloat( 'draw_thumbnail_rating_icon_size_px' ) )
            self._draw_thumbnail_rating_incdec_height_px.setValue( self._new_options.GetFloat( 'thumbnail_rating_incdec_height_px' )  )
            
            self._preview_window_rating_icon_size_px.setValue( self._new_options.GetFloat( 'preview_window_rating_icon_size_px' ) )
            self._preview_window_rating_incdec_height_px.setValue( self._new_options.GetFloat( 'preview_window_rating_incdec_height_px' ) )
            
            self._dialog_rating_icon_size_px.setValue( self._new_options.GetFloat( 'dialog_rating_icon_size_px' ) )
            self._dialog_rating_incdec_height_px.setValue( self._new_options.GetFloat( 'dialog_rating_incdec_height_px' ) )
            
            #
            
            rows = []
            
            rows.append( ( 'Media viewer like/dislike and numerical rating icon size:', self._media_viewer_rating_icon_size_px ) )
            rows.append( ( 'Media viewer inc/dec rating icon height:', self._media_viewer_rating_incdec_height_px ) )
            
            media_viewer_rating_gridbox = ClientGUICommon.WrapInGrid( media_viewer_rating_panel, rows )
            media_viewer_rating_panel.Add( media_viewer_rating_gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            rows = []
            
            rows.append( ( 'Preview window like/dislike and numerical rating icon size:', self._preview_window_rating_icon_size_px ) )
            rows.append( ( 'Preview window inc/dec rating icon height:', self._preview_window_rating_incdec_height_px ) )
            
            preview_hovers_gridbox = ClientGUICommon.WrapInGrid( preview_window_rating_panel, rows )
            preview_window_rating_panel.Add( preview_hovers_gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            rows = []
            
            rows.append( ( 'Thumbnail like/dislike and numerical rating icon size: ', self._draw_thumbnail_rating_icon_size_px ) )
            rows.append( ( 'Thumbnail inc/dec rating height: ', self._draw_thumbnail_rating_incdec_height_px ) )
            rows.append( ( 'Give thumbnail ratings a flat background: ', self._draw_thumbnail_rating_background ) )
            rows.append( ( 'Always draw thumbnail numerical ratings collapsed: ', self._draw_thumbnail_numerical_ratings_collapsed_always ) )
            
            thumbnail_ratings_gridbox = ClientGUICommon.WrapInGrid( thumbnail_ratings_panel, rows )
            thumbnail_ratings_panel.Add( thumbnail_ratings_gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            rows = []
            
            rows.append( ( 'Dialogs like/dislike and numerical rating icon size:', self._dialog_rating_icon_size_px ) )
            rows.append( ( 'Dialogs inc/dec rating height:', self._dialog_rating_incdec_height_px ) )
            
            manage_ratings_gridbox = ClientGUICommon.WrapInGrid( manage_ratings_popup_panel, rows )
            
            manage_ratings_popup_panel.Add( manage_ratings_gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            media_viewer_rating_gridbox.setColumnStretch(0, 1)
            media_viewer_rating_gridbox.setColumnStretch(1, 1)
            preview_hovers_gridbox.setColumnStretch(0, 1)
            preview_hovers_gridbox.setColumnStretch(1, 1)
            thumbnail_ratings_gridbox.setColumnStretch(0, 1)
            thumbnail_ratings_gridbox.setColumnStretch(1, 1)
            manage_ratings_gridbox.setColumnStretch(0, 1)
            manage_ratings_gridbox.setColumnStretch(1, 1)
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, media_viewer_rating_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, preview_window_rating_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, thumbnail_ratings_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, manage_ratings_popup_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            vbox.addStretch( 0 )
            self.setLayout( vbox )
            
        
        def _icon_size_changed( self ):
            
            new_value = self._media_viewer_rating_icon_size_px.value()
            
            self._media_viewer_rating_incdec_height_px.setMaximum( new_value * 2 )
            self._media_viewer_rating_incdec_height_px.setMinimum( new_value * 0.5 )
            
            new_value = self._preview_window_rating_icon_size_px.value()
            
            self._preview_window_rating_incdec_height_px.setMaximum( new_value * 2 )
            self._preview_window_rating_incdec_height_px.setMinimum( new_value * 0.5 )
            
            new_value = self._draw_thumbnail_rating_icon_size_px.value()
            
            self._draw_thumbnail_rating_incdec_height_px.setMaximum( new_value * 2 )
            self._draw_thumbnail_rating_incdec_height_px.setMinimum( new_value * 0.5 )
            
        
        def UpdateOptions( self ):
            
            self._new_options.SetFloat( 'media_viewer_rating_icon_size_px', self._media_viewer_rating_icon_size_px.value() )
            self._new_options.SetFloat( 'media_viewer_rating_incdec_height_px', self._media_viewer_rating_incdec_height_px.value() )
            
            self._new_options.SetBoolean( 'draw_thumbnail_rating_background', self._draw_thumbnail_rating_background.isChecked() )
            self._new_options.SetBoolean( 'draw_thumbnail_numerical_ratings_collapsed_always', self._draw_thumbnail_numerical_ratings_collapsed_always.isChecked() )
            self._new_options.SetFloat( 'draw_thumbnail_rating_icon_size_px', self._draw_thumbnail_rating_icon_size_px.value() )
            self._new_options.SetFloat( 'thumbnail_rating_incdec_height_px', self._draw_thumbnail_rating_incdec_height_px.value() )
            
            self._new_options.SetFloat( 'preview_window_rating_icon_size_px', self._preview_window_rating_icon_size_px.value() )
            self._new_options.SetFloat( 'preview_window_rating_incdec_height_px', self._preview_window_rating_incdec_height_px.value() )
            
            self._new_options.SetFloat( 'dialog_rating_icon_size_px', self._dialog_rating_icon_size_px.value() )
            self._new_options.SetFloat( 'dialog_rating_incdec_height_px', self._dialog_rating_incdec_height_px.value() )
            
        
    
    class _RegexPanel( OptionsPagePanel ):
        
        def __init__( self, parent ):
            
            super().__init__( parent )
            
            regex_favourites = HC.options[ 'regex_favourites' ]
            
            self._regex_panel = ClientGUIScrolledPanelsEditRegexFavourites.EditRegexFavourites( self, regex_favourites )
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, self._regex_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            self.setLayout( vbox )
            
        
        def UpdateOptions( self ):
            
            regex_favourites = self._regex_panel.GetValue()
            
            HC.options[ 'regex_favourites' ] = regex_favourites
            
        
    
    class _SpeedAndMemoryPanel( OptionsPagePanel ):
        
        def __init__( self, parent, new_options ):
            
            super().__init__( parent )
            
            self._new_options = new_options
            
            #
            
            thumbnail_cache_panel = ClientGUICommon.StaticBox( self, 'thumbnail cache', can_expand = True, start_expanded = False )
            
            self._thumbnail_cache_size = ClientGUIBytes.BytesControl( thumbnail_cache_panel )
            self._thumbnail_cache_size.valueChanged.connect( self.EventThumbnailsUpdate )
            
            tt = 'When thumbnails are loaded from disk, their bitmaps are saved for a while in memory so near-future access is super fast. If the total store of thumbnails exceeds this size setting, the least-recent-to-be-accessed will be discarded until the total size is less than it again.'
            tt += '\n' * 2
            tt += 'Most thumbnails are RGB, which means their size here is roughly [width x height x 3].'
            
            self._thumbnail_cache_size.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            self._estimated_number_thumbnails = QW.QLabel( '', thumbnail_cache_panel )
            
            self._thumbnail_cache_timeout = ClientGUITime.TimeDeltaButton( thumbnail_cache_panel, min = 300, days = True, hours = True, minutes = True )
            
            tt = 'The amount of not-accessed time after which a thumbnail will naturally be removed from the cache.'
            
            self._thumbnail_cache_timeout.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            image_cache_panel = ClientGUICommon.StaticBox( self, 'image cache', can_expand = True, start_expanded = False )
            
            self._image_cache_size = ClientGUIBytes.BytesControl( image_cache_panel )
            self._image_cache_size.valueChanged.connect( self.EventImageCacheUpdate )
            
            tt = 'When images are loaded from disk, their 100% zoom renders are saved for a while in memory so near-future access is super fast. If the total store of images exceeds this size setting, the least-recent-to-be-accessed will be discarded until the total size is less than it again.'
            tt += '\n' * 2
            tt += 'Most images are RGB, which means their size here is roughly [width x height x 3], with those dimensions being at 100% zoom.'
            
            self._image_cache_size.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            self._estimated_number_fullscreens = QW.QLabel( '', image_cache_panel )
            
            self._image_cache_timeout = ClientGUITime.TimeDeltaButton( image_cache_panel, min = 300, days = True, hours = True, minutes = True )
            
            tt = 'The amount of not-accessed time after which a rendered image will naturally be removed from the cache.'
            
            self._image_cache_timeout.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            self._image_cache_storage_limit_percentage = ClientGUICommon.BetterSpinBox( image_cache_panel, min = 20, max = 50 )
            
            tt = 'This option sets how much of the cache can go towards one image. If an image\'s total size (usually width x height x 3) is too large compared to the cache, it should not be cached or it will just flush everything else out in one stroke.'
            
            self._image_cache_storage_limit_percentage.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            self._image_cache_storage_limit_percentage_st = ClientGUICommon.BetterStaticText( image_cache_panel, label = '' )
            
            tt = 'This represents the typical size we are talking about at this percentage level. Could be wider or taller, but overall should have the same number of pixels. Anything smaller will be saved in the cache after load, anything larger will be loaded on demand and forgotten as soon as you navigate away. If you want to have persistent fast access to images bigger than this, increase the total image cache size and/or the max % value permitted.'
            
            self._image_cache_storage_limit_percentage_st.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            self._image_cache_prefetch_limit_percentage = ClientGUICommon.BetterSpinBox( image_cache_panel, min = 5, max = 25 )
            
            tt = 'If you are browsing many big files, this option stops the prefetcher from overloading your cache by loading up seven or more gigantic images that each competitively flush each other out and need to be re-rendered over and over.'
            
            self._image_cache_prefetch_limit_percentage.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            self._image_cache_prefetch_limit_percentage_st = ClientGUICommon.BetterStaticText( image_cache_panel, label = '' )
            
            tt = 'This represents the typical size we are talking about at this percentage level. Could be wider or taller, but overall should have the same number of pixels. Anything smaller will be pre-fetched, anything larger will be loaded on demand. If you want images bigger than this to load fast as you browse, increase the total image cache size and/or the max % value permitted.'
            
            self._image_cache_prefetch_limit_percentage_st.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            prefetch_panel = ClientGUICommon.StaticBox( self, 'image prefetch', can_expand = True, start_expanded = False )
            
            self._media_viewer_prefetch_delay_base_ms = ClientGUICommon.BetterSpinBox( prefetch_panel, min = 0, max = 2000 )
            
            tt = 'How long to wait, after the current image is rendered, to start rendering neighbours. Does not matter so much any more, but if you have CPU lag, you can try boosting it a bit.'
            
            self._media_viewer_prefetch_delay_base_ms.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            self._media_viewer_prefetch_num_previous = ClientGUICommon.BetterSpinBox( prefetch_panel, min = 0, max = 50 )
            self._media_viewer_prefetch_num_next = ClientGUICommon.BetterSpinBox( prefetch_panel, min = 0, max = 50 )
            
            self._duplicate_filter_prefetch_num_pairs = ClientGUICommon.BetterSpinBox( prefetch_panel, min = 0, max = 25 )
            
            self._prefetch_label_warning = ClientGUICommon.BetterStaticText( prefetch_panel )
            self._prefetch_label_warning.setToolTip( ClientGUIFunctions.WrapToolTip( 'If you boost the prefetch numbers, make sure your image cache is big enough to handle it! Doubly so if you frequently load images that at 100% are far larger than your screen size. You really don\'t want to be prefetching more than your cache can hold!' ) )
            
            image_tile_cache_panel = ClientGUICommon.StaticBox( self, 'image tile cache', can_expand = True, start_expanded = False )
            
            self._image_tile_cache_size = ClientGUIBytes.BytesControl( image_tile_cache_panel )
            self._image_tile_cache_size.valueChanged.connect( self.EventImageTilesUpdate )
            
            tt = 'Zooming and displaying an image is expensive. When an image is rendered to screen at a particular zoom, the client breaks the virtual canvas into tiles and only scales and draws the image onto the viewable ones. As you pan around, new tiles may be needed and old ones discarded. It is all cached so you can pan and zoom over the same areas quickly.'
            
            self._image_tile_cache_size.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            self._estimated_number_image_tiles = QW.QLabel( '', image_tile_cache_panel )
            
            tt = 'You do not need to go crazy here unless you do a huge amount of zooming and really need multiple zoom levels cached for 10+ files you are comparing with each other.'
            
            self._estimated_number_image_tiles.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            self._image_tile_cache_timeout = ClientGUITime.TimeDeltaButton( image_tile_cache_panel, min = 300, hours = True, minutes = True )
            
            tt = 'The amount of not-accessed time after which a rendered tile will naturally be removed from the cache.'
            
            self._image_tile_cache_timeout.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            self._ideal_tile_dimension = ClientGUICommon.BetterSpinBox( image_tile_cache_panel, min = 256, max = 4096 )
            
            tt = 'This is the screen-visible square size the system will aim for. Smaller tiles are more memory efficient but prone to warping and other artifacts. Extreme values may waste CPU.'
            
            self._ideal_tile_dimension.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            #
            
            pages_panel = ClientGUICommon.StaticBox( self, 'download pages update', can_expand = True, start_expanded = False )
            
            self._gallery_page_status_update_time_minimum = ClientGUITime.TimeDeltaWidget( pages_panel, min = 0.25, seconds = True, milliseconds = True )
            self._gallery_page_status_update_time_ratio_denominator = ClientGUICommon.BetterSpinBox( pages_panel, min = 1 )
            
            self._watcher_page_status_update_time_minimum = ClientGUITime.TimeDeltaWidget( pages_panel, min = 0.25, seconds = True, milliseconds = True )
            self._watcher_page_status_update_time_ratio_denominator = ClientGUICommon.BetterSpinBox( pages_panel, min = 1 )
            
            #
            
            buffer_panel = ClientGUICommon.StaticBox( self, 'video buffer', can_expand = True, start_expanded = False )
            
            self._video_buffer_size = ClientGUIBytes.BytesControl( buffer_panel )
            self._video_buffer_size.valueChanged.connect( self.EventVideoBufferUpdate )
            
            self._estimated_number_video_frames = QW.QLabel( '', buffer_panel )
            
            #
            
            self._thumbnail_cache_size.SetValue( self._new_options.GetInteger( 'thumbnail_cache_size' ) )
            self._image_cache_size.SetValue( self._new_options.GetInteger( 'image_cache_size' ) )
            self._image_tile_cache_size.SetValue( self._new_options.GetInteger( 'image_tile_cache_size' ) )
            
            self._thumbnail_cache_timeout.SetValue( self._new_options.GetInteger( 'thumbnail_cache_timeout' ) )
            self._image_cache_timeout.SetValue( self._new_options.GetInteger( 'image_cache_timeout' ) )
            self._image_tile_cache_timeout.SetValue( self._new_options.GetInteger( 'image_tile_cache_timeout' ) )
            
            self._ideal_tile_dimension.setValue( self._new_options.GetInteger( 'ideal_tile_dimension' ) )
            
            self._gallery_page_status_update_time_minimum.SetValue( HydrusTime.SecondiseMSFloat( self._new_options.GetInteger( 'gallery_page_status_update_time_minimum_ms' ) ) )
            self._gallery_page_status_update_time_ratio_denominator.setValue( self._new_options.GetInteger( 'gallery_page_status_update_time_ratio_denominator' ) )
            
            self._watcher_page_status_update_time_minimum.SetValue( HydrusTime.SecondiseMSFloat( self._new_options.GetInteger( 'watcher_page_status_update_time_minimum_ms' ) ) )
            self._watcher_page_status_update_time_ratio_denominator.setValue( self._new_options.GetInteger( 'watcher_page_status_update_time_ratio_denominator' ) )
            
            self._video_buffer_size.SetValue( self._new_options.GetInteger( 'video_buffer_size' ) )
            
            self._media_viewer_prefetch_delay_base_ms.setValue( self._new_options.GetInteger( 'media_viewer_prefetch_delay_base_ms' ) )
            self._media_viewer_prefetch_num_previous.setValue( self._new_options.GetInteger( 'media_viewer_prefetch_num_previous' ) )
            self._media_viewer_prefetch_num_next.setValue( self._new_options.GetInteger( 'media_viewer_prefetch_num_next' ) )
            self._duplicate_filter_prefetch_num_pairs.setValue( self._new_options.GetInteger( 'duplicate_filter_prefetch_num_pairs' ) )
            
            self._image_cache_storage_limit_percentage.setValue( self._new_options.GetInteger( 'image_cache_storage_limit_percentage' ) )
            self._image_cache_prefetch_limit_percentage.setValue( self._new_options.GetInteger( 'image_cache_prefetch_limit_percentage' ) )
            
            #
            
            vbox = QP.VBoxLayout()
            
            text = 'These options are advanced! PROTIP: Do not go crazy here.'
            
            st = ClientGUICommon.BetterStaticText( self, text )
            
            QP.AddToLayout( vbox, st, CC.FLAGS_CENTER )
            
            #
            
            thumbnails_sizer = QP.HBoxLayout()
            
            QP.AddToLayout( thumbnails_sizer, self._thumbnail_cache_size, CC.FLAGS_CENTER )
            QP.AddToLayout( thumbnails_sizer, self._estimated_number_thumbnails, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            fullscreens_sizer = QP.HBoxLayout()
            
            QP.AddToLayout( fullscreens_sizer, self._image_cache_size, CC.FLAGS_CENTER_PERPENDICULAR )
            QP.AddToLayout( fullscreens_sizer, self._estimated_number_fullscreens, CC.FLAGS_CENTER_PERPENDICULAR )
            
            image_tiles_sizer = QP.HBoxLayout()
            
            QP.AddToLayout( image_tiles_sizer, self._image_tile_cache_size, CC.FLAGS_CENTER_PERPENDICULAR )
            QP.AddToLayout( image_tiles_sizer, self._estimated_number_image_tiles, CC.FLAGS_CENTER_PERPENDICULAR )
            
            image_cache_storage_sizer = QP.HBoxLayout()
            
            QP.AddToLayout( image_cache_storage_sizer, self._image_cache_storage_limit_percentage, CC.FLAGS_EXPAND_BOTH_WAYS_SHY )
            QP.AddToLayout( image_cache_storage_sizer, self._image_cache_storage_limit_percentage_st, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            image_cache_prefetch_sizer = QP.HBoxLayout()
            
            QP.AddToLayout( image_cache_prefetch_sizer, self._image_cache_prefetch_limit_percentage, CC.FLAGS_EXPAND_BOTH_WAYS_SHY )
            QP.AddToLayout( image_cache_prefetch_sizer, self._image_cache_prefetch_limit_percentage_st, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            video_buffer_sizer = QP.HBoxLayout()
            
            QP.AddToLayout( video_buffer_sizer, self._video_buffer_size, CC.FLAGS_CENTER_PERPENDICULAR )
            QP.AddToLayout( video_buffer_sizer, self._estimated_number_video_frames, CC.FLAGS_CENTER_PERPENDICULAR )
            
            #
            
            text = 'Does not change much, thumbs are cheap.'
            
            st = ClientGUICommon.BetterStaticText( thumbnail_cache_panel, text )
            
            thumbnail_cache_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            rows = []
            
            rows.append( ( 'Memory reserved for thumbnail cache:', thumbnails_sizer ) )
            rows.append( ( 'Thumbnail cache timeout:', self._thumbnail_cache_timeout ) )
            
            gridbox = ClientGUICommon.WrapInGrid( thumbnail_cache_panel, rows )
            
            thumbnail_cache_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            QP.AddToLayout( vbox, thumbnail_cache_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            #
            
            text = 'Important if you want smooth navigation between different images in the media viewer. If you deal with huge images, bump up cache size and max size that can be cached or prefetched, but be prepared to pay the memory price.'
            text += '\n' * 2
            text += 'Allowing more prefetch is great, but it needs CPU.'
            
            st = ClientGUICommon.BetterStaticText( image_cache_panel, text )
            
            st.setWordWrap( True )
            
            image_cache_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            rows = []
            
            rows.append( ( 'Memory reserved for image cache:', fullscreens_sizer ) )
            rows.append( ( 'Image cache timeout:', self._image_cache_timeout ) )
            rows.append( ( 'Maximum image size (in % of cache) that can be cached:', image_cache_storage_sizer ) )
            rows.append( ( 'Maximum image size (in % of cache) that will be prefetched:', image_cache_prefetch_sizer ) )
            
            gridbox = ClientGUICommon.WrapInGrid( image_cache_panel, rows )
            
            image_cache_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            QP.AddToLayout( vbox, image_cache_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            #
            
            rows = []
            
            rows.append( ( 'Base ms delay for Media Viewer neighbour render prefetch:', self._media_viewer_prefetch_delay_base_ms ) )
            rows.append( ( 'Num previous to prefetch in Media Viewer:', self._media_viewer_prefetch_num_previous ) )
            rows.append( ( 'Num next to prefetch in Media Viewer:', self._media_viewer_prefetch_num_next ) )
            rows.append( ( 'Num pairs to prefetch in Duplicate Filter:', self._duplicate_filter_prefetch_num_pairs ) )
            rows.append( ( 'Prefetch numbers exceed typical cache size?:', self._prefetch_label_warning ) )
            
            gridbox = ClientGUICommon.WrapInGrid( prefetch_panel, rows )
            
            prefetch_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            QP.AddToLayout( vbox, prefetch_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            #
            
            text = 'Important if you do a lot of zooming in and out on the same image or a small number of comparison images.'
            
            st = ClientGUICommon.BetterStaticText( image_tile_cache_panel, text )
            
            image_tile_cache_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            rows = []
            
            rows.append( ( 'Memory reserved for image tile cache:', image_tiles_sizer ) )
            rows.append( ( 'Image tile cache timeout:', self._image_tile_cache_timeout ) )
            rows.append( ( 'Ideal tile width/height px:', self._ideal_tile_dimension ) )
            
            gridbox = ClientGUICommon.WrapInGrid( image_tile_cache_panel, rows )
            
            image_tile_cache_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            QP.AddToLayout( vbox, image_tile_cache_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            #
            
            text = 'EXPERIMENTAL, HYDEV ONLY, STAY AWAY!'
            
            st = ClientGUICommon.BetterStaticText( pages_panel, text )
            
            st.setWordWrap( True )
            
            pages_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            rows = []
            
            rows.append( ( 'EXPERIMENTAL: Minimum gallery importer update time:', self._gallery_page_status_update_time_minimum ) )
            rows.append( ( 'EXPERIMENTAL: Gallery importer magic update time denominator:', self._gallery_page_status_update_time_ratio_denominator ) )
            
            rows.append( ( 'EXPERIMENTAL: Minimum watcher importer update time:', self._watcher_page_status_update_time_minimum ) )
            rows.append( ( 'EXPERIMENTAL: Watcher importer magic update time denominator:', self._watcher_page_status_update_time_ratio_denominator ) )
            
            gridbox = ClientGUICommon.WrapInGrid( pages_panel, rows )
            
            pages_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            QP.AddToLayout( vbox, pages_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            #
            
            text = 'This old option does not apply to mpv! It only applies to the native hydrus animation renderer!'
            text += '\n'
            text += 'Hydrus video rendering is CPU intensive.'
            text += '\n'
            text += 'If you have a lot of memory, you can set a generous potential video buffer to compensate.'
            text += '\n'
            text += 'If the video buffer can hold an entire video, it only needs to be rendered once and will play and loop very smoothly.'
            text += '\n'
            text += 'PROTIP: Do not go crazy here.'
            
            st = ClientGUICommon.BetterStaticText( buffer_panel, text )
            
            st.setWordWrap( True )
            
            buffer_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            rows = []
            
            rows.append( ( 'Memory for video buffer: ', video_buffer_sizer ) )
            
            gridbox = ClientGUICommon.WrapInGrid( buffer_panel, rows )
            
            buffer_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            QP.AddToLayout( vbox, buffer_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            #
            
            vbox.addStretch( 0 )
            
            self.setLayout( vbox )
            
            #
            
            self._image_cache_storage_limit_percentage.valueChanged.connect( self.EventImageCacheUpdate )
            self._image_cache_prefetch_limit_percentage.valueChanged.connect( self.EventImageCacheUpdate )
            
            self._media_viewer_prefetch_num_previous.valueChanged.connect( self.EventImageCacheUpdate )
            self._media_viewer_prefetch_num_next.valueChanged.connect( self.EventImageCacheUpdate )
            self._duplicate_filter_prefetch_num_pairs.valueChanged.connect( self.EventImageCacheUpdate )
            
            self.EventImageCacheUpdate()
            self.EventThumbnailsUpdate()
            self.EventImageTilesUpdate()
            self.EventVideoBufferUpdate()
            
        
        def EventImageCacheUpdate( self ):
            
            cache_size = self._image_cache_size.GetValue()
            
            display_size = ClientGUIFunctions.GetDisplaySize( self )
            
            estimated_bytes_per_fullscreen = 3 * display_size.width() * display_size.height()
            
            image_cache_estimate = cache_size // estimated_bytes_per_fullscreen
            
            self._estimated_number_fullscreens.setText( '(about {}-{} images the size of your screen)'.format( HydrusNumbers.ToHumanInt( image_cache_estimate // 2 ), HydrusNumbers.ToHumanInt( image_cache_estimate * 2 ) ) )
            
            num_pixels = cache_size * ( self._image_cache_storage_limit_percentage.value() / 100 ) / 3
            
            unit_square = num_pixels / ( 16 * 9 )
            
            unit_length = unit_square ** 0.5
            
            resolution = ( int( 16 * unit_length ), int( 9 * unit_length ) )
            
            self._image_cache_storage_limit_percentage_st.setText( '% - {} pixels, or about a {} image'.format( HydrusNumbers.ToHumanInt( num_pixels ), ClientData.ResolutionToPrettyString( resolution ) ) )
            
            num_pixels = cache_size * ( self._image_cache_prefetch_limit_percentage.value() / 100 ) / 3
            
            unit_square = num_pixels / ( 16 * 9 )
            
            unit_length = unit_square ** 0.5
            
            resolution = ( int( 16 * unit_length ), int( 9 * unit_length ) )
            
            self._image_cache_prefetch_limit_percentage_st.setText( '% - {} pixels, or about a {} image'.format( HydrusNumbers.ToHumanInt( num_pixels ), ClientData.ResolutionToPrettyString( resolution ) ) )
            
            #
            
            num_prefetch_media_viewer = 1 + self._media_viewer_prefetch_num_previous.value() + self._media_viewer_prefetch_num_next.value()
            num_prefetch_duplicate_filter = 2 + ( self._duplicate_filter_prefetch_num_pairs.value() * 2 )
            
            if num_prefetch_media_viewer > image_cache_estimate // 2:
                
                label = 'Yes! Reduce Media Viewer prefetch or increase your image cache!'
                object_name = 'HydrusWarning'
                
            elif num_prefetch_duplicate_filter > image_cache_estimate // 2:
                
                label = 'Yes! Reduce Duplicate Filter prefetch or increase your image cache!'
                object_name = 'HydrusWarning'
                
            else:
                
                label = 'No, looks good!'
                object_name = ''
                
            
            self._prefetch_label_warning.setText( label )
            
            if object_name != self._prefetch_label_warning.objectName():
                
                self._prefetch_label_warning.setObjectName( object_name )
                
                self._prefetch_label_warning.style().polish( self._prefetch_label_warning )
                
            
        
        def EventImageTilesUpdate( self ):
            
            value = self._image_tile_cache_size.GetValue()
            
            display_size = ClientGUIFunctions.GetDisplaySize( self )
            
            estimated_bytes_per_fullscreen = 3 * display_size.width() * display_size.height()
            
            estimate = value // estimated_bytes_per_fullscreen
            
            self._estimated_number_image_tiles.setText( '(about {} fullscreens)'.format( HydrusNumbers.ToHumanInt( estimate ) ) )
            
        
        def EventThumbnailsUpdate( self ):
            
            value = self._thumbnail_cache_size.GetValue()
            
            ( thumbnail_width, thumbnail_height ) = HC.options[ 'thumbnail_dimensions' ]
            
            res_string = ClientData.ResolutionToPrettyString( ( thumbnail_width, thumbnail_height ) )
            
            estimated_bytes_per_thumb = 3 * thumbnail_width * thumbnail_height
            
            estimated_thumbs = value // estimated_bytes_per_thumb
            
            self._estimated_number_thumbnails.setText( '(at '+res_string+', about '+HydrusNumbers.ToHumanInt(estimated_thumbs)+' thumbnails)' )
            
        
        def EventVideoBufferUpdate( self ):
            
            value = self._video_buffer_size.GetValue()
            
            estimated_720p_frames = int( value // ( 1280 * 720 * 3 ) )
            
            self._estimated_number_video_frames.setText( '(about '+HydrusNumbers.ToHumanInt(estimated_720p_frames)+' frames of 720p video)' )
            
        
        def UpdateOptions( self ):
            
            self._new_options.SetInteger( 'thumbnail_cache_size', self._thumbnail_cache_size.GetValue() )
            self._new_options.SetInteger( 'image_cache_size', self._image_cache_size.GetValue() )
            self._new_options.SetInteger( 'image_tile_cache_size', self._image_tile_cache_size.GetValue() )
            
            self._new_options.SetInteger( 'thumbnail_cache_timeout', self._thumbnail_cache_timeout.GetValue() )
            self._new_options.SetInteger( 'image_cache_timeout', self._image_cache_timeout.GetValue() )
            self._new_options.SetInteger( 'image_tile_cache_timeout', self._image_tile_cache_timeout.GetValue() )
            
            self._new_options.SetInteger( 'ideal_tile_dimension', self._ideal_tile_dimension.value() )
            
            self._new_options.SetInteger( 'media_viewer_prefetch_delay_base_ms', self._media_viewer_prefetch_delay_base_ms.value() )
            self._new_options.SetInteger( 'media_viewer_prefetch_num_previous', self._media_viewer_prefetch_num_previous.value() )
            self._new_options.SetInteger( 'media_viewer_prefetch_num_next', self._media_viewer_prefetch_num_next.value() )
            self._new_options.SetInteger( 'duplicate_filter_prefetch_num_pairs', self._duplicate_filter_prefetch_num_pairs.value() )
            
            self._new_options.SetInteger( 'image_cache_storage_limit_percentage', self._image_cache_storage_limit_percentage.value() )
            self._new_options.SetInteger( 'image_cache_prefetch_limit_percentage', self._image_cache_prefetch_limit_percentage.value() )
            
            self._new_options.SetInteger( 'gallery_page_status_update_time_minimum_ms', int( self._gallery_page_status_update_time_minimum.GetValue() * 1000 ) )
            self._new_options.SetInteger( 'gallery_page_status_update_time_ratio_denominator', self._gallery_page_status_update_time_ratio_denominator.value() )
            
            self._new_options.SetInteger( 'watcher_page_status_update_time_minimum_ms', int( self._watcher_page_status_update_time_minimum.GetValue() * 1000 ) )
            self._new_options.SetInteger( 'watcher_page_status_update_time_ratio_denominator', self._watcher_page_status_update_time_ratio_denominator.value() )
            
            self._new_options.SetInteger( 'video_buffer_size', self._video_buffer_size.GetValue() )
            
        
    
    class _StylePanel( OptionsPagePanel ):
        
        def __init__( self, parent, new_options ):
            
            super().__init__( parent )
            
            self._new_options = new_options
            
            #
            
            help_text = 'Hey, there are several custom widget colours that can be overridden in the "colours" page!'
            
            self._help_label = ClientGUICommon.BetterStaticText( self, label = help_text )
            
            self._help_label.setObjectName( 'HydrusWarning' )
            
            self._help_label.setWordWrap( True )
            
            self._qt_style_name = ClientGUICommon.BetterChoice( self )
            self._qt_stylesheet_name = ClientGUICommon.BetterChoice( self )
            
            self._qt_style_name.addItem( 'use default ("{}")'.format( ClientGUIStyle.ORIGINAL_STYLE_NAME ), None )
            
            try:
                
                for name in ClientGUIStyle.GetAvailableStyles():
                    
                    self._qt_style_name.addItem( name, name )
                    
                
            except HydrusExceptions.DataMissing as e:
                
                HydrusData.ShowException( e )
                
            
            self._qt_stylesheet_name.addItem( 'use default', None )
            
            try:
                
                for name in ClientGUIStyle.GetAvailableStyleSheets():
                    
                    self._qt_stylesheet_name.addItem( name, name )
                    
                
            except HydrusExceptions.DataMissing as e:
                
                HydrusData.ShowException( e )
                
            
            #
            
            self._qt_style_name.SetValue( self._new_options.GetNoneableString( 'qt_style_name' ) )
            self._qt_stylesheet_name.SetValue( self._new_options.GetNoneableString( 'qt_stylesheet_name' ) )
            
            #
            
            vbox = QP.VBoxLayout()
            
            #
            
            QP.AddToLayout( vbox, self._help_label, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            text = 'The current styles are what your Qt has available, the stylesheets are what .css and .qss files are currently in install_dir/static/qss or db_dir/static/qss (if you make one).'
            text += '\n' * 2
            text += 'If you run from source and select e621, or Paper_Dark stylesheets, which include external (svg) assets, you must make sure that your CWD is the hydrus install folder when you boot the program. For a custom QSS in your db_dir that uses external assets, you must edit the .QSS so it uses absolute path names.'
            
            st = ClientGUICommon.BetterStaticText( self, label = text )
            
            st.setWordWrap( True )
            
            QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            rows = []
            
            rows.append( ( 'Qt style:', self._qt_style_name ) )
            rows.append( ( 'Qt stylesheet:', self._qt_stylesheet_name ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self, rows )
            
            QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            vbox.addStretch( 0 )
            
            self.setLayout( vbox )
            
            self._qt_style_name.currentIndexChanged.connect( self.StyleChanged )
            self._qt_stylesheet_name.currentIndexChanged.connect( self.StyleChanged )
            
        
        def StyleChanged( self ):
            
            qt_style_name = self._qt_style_name.GetValue()
            qt_stylesheet_name = self._qt_stylesheet_name.GetValue()
            
            try:
                
                if qt_style_name is None:
                    
                    ClientGUIStyle.SetStyleFromName( ClientGUIStyle.ORIGINAL_STYLE_NAME )
                    
                else:
                    
                    ClientGUIStyle.SetStyleFromName( qt_style_name )
                    
                
            except Exception as e:
                
                HydrusData.PrintException( e )
                
                ClientGUIDialogsMessage.ShowCritical( self, 'Critical', f'Could not apply style: {e}' )
                
            
            CG.client_controller.gui._DoMenuBarStyleHack()
            
            try:
                
                if qt_stylesheet_name is None:
                    
                    ClientGUIStyle.ClearStyleSheet()
                    
                else:
                    
                    ClientGUIStyle.SetStyleSheetFromPath( qt_stylesheet_name )
                    
                
            except Exception as e:
                
                HydrusData.PrintException( e )
                
                ClientGUIDialogsMessage.ShowCritical( self, 'Critical', f'Could not apply stylesheet: {e}' )
                
            
        
        def UpdateOptions( self ):
            
            self._new_options.SetNoneableString( 'qt_style_name', self._qt_style_name.GetValue() )
            self._new_options.SetNoneableString( 'qt_stylesheet_name', self._qt_stylesheet_name.GetValue() )
            
        
    
    class _SystemPanel( OptionsPagePanel ):
        
        def __init__( self, parent, new_options ):
            
            super().__init__( parent )
            
            self._new_options = new_options
            
            #
            
            sleep_panel = ClientGUICommon.StaticBox( self, 'system sleep' )
            
            self._do_sleep_check = QW.QCheckBox( sleep_panel )
            self._do_sleep_check.setToolTip( ClientGUIFunctions.WrapToolTip( 'Hydrus detects sleeps via a hacky method where it simply checks the clock every 15 seconds. If too long a time has passed since the last check, it assumes it has just woken up from sleep. This produces false positives in certain UI-hanging situations, so you may, for debugging purposes, wish to turn it off here. When functioning well, it is useful and you should leave it on!' ) )
            
            self._wake_delay_period = ClientGUICommon.BetterSpinBox( sleep_panel, min = 0, max = 60 )
            
            tt = 'It sometimes takes a few seconds for your network adapter to reconnect after a wake. This adds a grace period after a detected wake-from-sleep to allow your OS to sort that out before Hydrus starts making requests.'
            
            self._wake_delay_period.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            self._file_system_waits_on_wakeup = QW.QCheckBox( sleep_panel )
            self._file_system_waits_on_wakeup.setToolTip( ClientGUIFunctions.WrapToolTip( 'This is useful if your hydrus is stored on a NAS that takes a few seconds to get going after your machine resumes from sleep.' ) )
            
            #
            
            self._do_sleep_check.setChecked( self._new_options.GetBoolean( 'do_sleep_check' ) )
            
            self._wake_delay_period.setValue( self._new_options.GetInteger( 'wake_delay_period' ) )
            
            self._file_system_waits_on_wakeup.setChecked( self._new_options.GetBoolean( 'file_system_waits_on_wakeup' ) )
            
            #
            
            rows = []
            
            rows.append( ( 'Allow wake-from-system-sleep detection:', self._do_sleep_check ) )
            rows.append( ( 'After a wake from system sleep, wait this many seconds before allowing new network access:', self._wake_delay_period ) )
            rows.append( ( 'Include the file system in this wait: ', self._file_system_waits_on_wakeup ) )
            
            gridbox = ClientGUICommon.WrapInGrid( sleep_panel, rows )
            
            sleep_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, sleep_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.addStretch( 0 )
            
            self.setLayout( vbox )
            
        
        def UpdateOptions( self ):
            
            self._new_options.SetBoolean( 'do_sleep_check', self._do_sleep_check.isChecked() )
            self._new_options.SetInteger( 'wake_delay_period', self._wake_delay_period.value() )
            self._new_options.SetBoolean( 'file_system_waits_on_wakeup', self._file_system_waits_on_wakeup.isChecked() )
            
        
    
    class _SystemTrayPanel( OptionsPagePanel ):
        
        def __init__( self, parent, new_options ):
            
            super().__init__( parent )
            
            self._new_options = new_options
            
            self._always_show_system_tray_icon = QW.QCheckBox( self )
            self._minimise_client_to_system_tray = QW.QCheckBox( self )
            self._close_client_to_system_tray = QW.QCheckBox( self )
            self._start_client_in_system_tray = QW.QCheckBox( self )
            
            #
            
            self._always_show_system_tray_icon.setChecked( self._new_options.GetBoolean( 'always_show_system_tray_icon' ) )
            self._minimise_client_to_system_tray.setChecked( self._new_options.GetBoolean( 'minimise_client_to_system_tray' ) )
            self._close_client_to_system_tray.setChecked( self._new_options.GetBoolean( 'close_client_to_system_tray' ) )
            self._start_client_in_system_tray.setChecked( self._new_options.GetBoolean( 'start_client_in_system_tray' ) )
            
            #
            
            vbox = QP.VBoxLayout()
            
            rows = []
            
            rows.append( ( 'Always show the hydrus system tray icon: ', self._always_show_system_tray_icon ) )
            rows.append( ( 'Minimise the main window to system tray: ', self._minimise_client_to_system_tray ) )
            rows.append( ( 'Close the main window to system tray: ', self._close_client_to_system_tray ) )
            rows.append( ( 'Start the client minimised to system tray: ', self._start_client_in_system_tray ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self, rows )
            
            from hydrus.client.gui import ClientGUISystemTray
            
            if not ClientGUISystemTray.SystemTrayAvailable():
                
                QP.AddToLayout( vbox, ClientGUICommon.BetterStaticText( self, 'Unfortunately, your system does not seem to have a supported system tray.' ), CC.FLAGS_EXPAND_PERPENDICULAR )
                
                self._always_show_system_tray_icon.setEnabled( False )
                self._minimise_client_to_system_tray.setEnabled( False )
                self._close_client_to_system_tray.setEnabled( False )
                self._start_client_in_system_tray.setEnabled( False )
                
                self._always_show_system_tray_icon.setChecked( False )
                self._minimise_client_to_system_tray.setChecked( False )
                self._close_client_to_system_tray.setChecked( False )
                self._start_client_in_system_tray.setChecked( False )
                
            elif not HC.PLATFORM_WINDOWS:
                
                if not CG.client_controller.new_options.GetBoolean( 'advanced_mode' ):
                    
                    label = 'This is turned off for non-advanced non-Windows users for now.'
                    
                    self._always_show_system_tray_icon.setEnabled( False )
                    self._minimise_client_to_system_tray.setEnabled( False )
                    self._close_client_to_system_tray.setEnabled( False )
                    self._start_client_in_system_tray.setEnabled( False )
                    
                else:
                    
                    label = 'This can be buggy/crashy on non-Windows, hydev will keep working on this.'
                    
                
                QP.AddToLayout( vbox, ClientGUICommon.BetterStaticText( self, label ), CC.FLAGS_EXPAND_PERPENDICULAR )
                
            
            QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            vbox.addStretch( 0 )
            
            self.setLayout( vbox )
            
        
        def UpdateOptions( self ):
            
            self._new_options.SetBoolean( 'always_show_system_tray_icon', self._always_show_system_tray_icon.isChecked() )
            self._new_options.SetBoolean( 'minimise_client_to_system_tray', self._minimise_client_to_system_tray.isChecked() )
            self._new_options.SetBoolean( 'close_client_to_system_tray', self._close_client_to_system_tray.isChecked() )
            self._new_options.SetBoolean( 'start_client_in_system_tray', self._start_client_in_system_tray.isChecked() )
            
        
    
    class _TagsPanel( OptionsPagePanel ):
        
        def __init__( self, parent, new_options ):
            
            super().__init__( parent )
            
            self._new_options = new_options
            
            #
            
            favourites_panel = ClientGUICommon.StaticBox( self, 'favourite tags' )
            
            desc = 'These tags will appear in every tag autocomplete results dropdown, under the \'favourites\' tab.'
            
            favourites_st = ClientGUICommon.BetterStaticText( favourites_panel, desc )
            favourites_st.setWordWrap( True )
            
            default_location_context = CG.client_controller.new_options.GetDefaultLocalLocationContext()
            
            self._favourites = ClientGUIListBoxes.ListBoxTagsStringsAddRemove( favourites_panel, CC.COMBINED_TAG_SERVICE_KEY, tag_display_type = ClientTags.TAG_DISPLAY_STORAGE )
            self._favourites_input = ClientGUIACDropdown.AutoCompleteDropdownTagsWrite( favourites_panel, self._favourites.AddTags, default_location_context, CC.COMBINED_TAG_SERVICE_KEY, show_paste_button = True )
            
            self._favourites.tagsChanged.connect( self._favourites_input.SetContextTags )
            
            self._favourites_input.externalCopyKeyPressEvent.connect( self._favourites.keyPressEvent )
            
            
            #
            
            children_panel = ClientGUICommon.StaticBox( self, 'children tags' )
            
            self._num_to_show_in_ac_dropdown_children_tab = ClientGUICommon.NoneableSpinCtrl( children_panel, 40, none_phrase = 'show all', min = 1 )
            tt = 'The "children" tab will show children of the current tag context (usually the list of tags above the autocomplete), ordered by file count. This can quickly get spammy, so I recommend you cull it to a reasonable size.'
            self._num_to_show_in_ac_dropdown_children_tab.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            self._num_to_show_in_ac_dropdown_children_tab.SetValue( 40 ) # init default
            
            #
            
            self._favourites.SetTags( self._new_options.GetStringList( 'favourite_tags' ) )
            
            #
            
            self._num_to_show_in_ac_dropdown_children_tab.SetValue( self._new_options.GetNoneableInteger( 'num_to_show_in_ac_dropdown_children_tab' ) )
            
            #
            
            favourites_panel.Add( favourites_st, CC.FLAGS_EXPAND_PERPENDICULAR )
            favourites_panel.Add( self._favourites, CC.FLAGS_EXPAND_BOTH_WAYS )
            favourites_panel.Add( self._favourites_input )
            
            #
            
            rows = []
            
            rows.append( ( 'How many tags to show in the children tab: ', self._num_to_show_in_ac_dropdown_children_tab ) )
            
            gridbox = ClientGUICommon.WrapInGrid( children_panel, rows )
            
            children_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, children_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, favourites_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            self.setLayout( vbox )
            
            #
            
            self._favourites_input.tagsPasted.connect( self.AddTagsOnlyAdd )
            
        
        def AddTagsOnlyAdd( self, tags ):
            
            current_tags = self._favourites.GetTags()
            
            tags = { tag for tag in tags if tag not in current_tags }
            
            if len( tags ) > 0:
                
                self._favourites.AddTags( tags )
                
            
        
        def UpdateOptions( self ):
            
            self._new_options.SetStringList( 'favourite_tags', sorted( self._favourites.GetTags(), key = HydrusText.HumanTextSortKey ) )
            
            #
            
            self._new_options.SetNoneableInteger( 'num_to_show_in_ac_dropdown_children_tab', self._num_to_show_in_ac_dropdown_children_tab.GetValue() )
            
        
    
    class _TagEditingPanel( OptionsPagePanel ):
        
        def __init__( self, parent, new_options ):
            
            super().__init__( parent )
            
            self._new_options = new_options
            
            #
            
            self._tag_services_panel = ClientGUICommon.StaticBox( self, 'tag dialogs' )
            
            self._use_listbook_for_tag_service_panels = QW.QCheckBox( self._tag_services_panel )
            
            self._expand_parents_on_storage_taglists = QW.QCheckBox( self._tag_services_panel )
            self._show_parent_decorators_on_storage_taglists = QW.QCheckBox( self._tag_services_panel )
            self._show_sibling_decorators_on_storage_taglists = QW.QCheckBox( self._tag_services_panel )
            
            self._num_recent_petition_reasons = ClientGUICommon.BetterSpinBox( self._tag_services_panel, initial = 5, min = 0, max = 100 )
            tt = 'In manage tags, tag siblings, and tag parents, you may be asked to provide a reason with a petition you make to a hydrus repository. There are some fixed reasons, but the dialog can also remember what you recently typed. This controls how many recent reasons it will remember.'
            self._num_recent_petition_reasons.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            self._save_default_tag_service_tab_on_change = QW.QCheckBox( self._tag_services_panel )
            
            self._default_tag_service_tab = ClientGUICommon.BetterChoice( self._tag_services_panel )
            
            #
            
            self._write_autocomplete_panel = ClientGUICommon.StaticBox( self, 'tag edit autocomplete' )
            
            self._ac_select_first_with_count = QW.QCheckBox( self._write_autocomplete_panel )
            
            self._skip_yesno_on_write_autocomplete_multiline_paste = QW.QCheckBox( self._write_autocomplete_panel )
            
            self._ac_write_list_height_num_chars = ClientGUICommon.BetterSpinBox( self._write_autocomplete_panel, min = 1, max = 128 )
            
            self._expand_parents_on_storage_autocomplete_taglists = QW.QCheckBox( self._write_autocomplete_panel )
            self._show_parent_decorators_on_storage_autocomplete_taglists = QW.QCheckBox( self._write_autocomplete_panel )
            self._show_sibling_decorators_on_storage_autocomplete_taglists = QW.QCheckBox( self._write_autocomplete_panel )
            
            #
            
            services = CG.client_controller.services_manager.GetServices( HC.REAL_TAG_SERVICES )
            
            for service in services:
                
                self._default_tag_service_tab.addItem( service.GetName(), service.GetServiceKey() )
                
            
            self._default_tag_service_tab.SetValue( self._new_options.GetKey( 'default_tag_service_tab' ) )
            
            self._num_recent_petition_reasons.setValue( self._new_options.GetInteger( 'num_recent_petition_reasons' ) )
            
            self._use_listbook_for_tag_service_panels.setChecked( self._new_options.GetBoolean( 'use_listbook_for_tag_service_panels' ) )
            self._use_listbook_for_tag_service_panels.setToolTip( ClientGUIFunctions.WrapToolTip( 'If you have many tag services, you might prefer to use a vertical list to navigate your various tag dialogs.' ) )
            
            self._save_default_tag_service_tab_on_change.setChecked( self._new_options.GetBoolean( 'save_default_tag_service_tab_on_change' ) )
            
            self._ac_select_first_with_count.setChecked( self._new_options.GetBoolean( 'ac_select_first_with_count' ) )
            
            self._ac_write_list_height_num_chars.setValue( self._new_options.GetInteger( 'ac_write_list_height_num_chars' ) )
            
            self._expand_parents_on_storage_taglists.setChecked( self._new_options.GetBoolean( 'expand_parents_on_storage_taglists' ) )
            self._expand_parents_on_storage_taglists.setToolTip( ClientGUIFunctions.WrapToolTip( 'This affects taglists in places like the manage tags dialog, where you edit tags as they actually are, and implied parents hang below tags.' ) )
            
            self._skip_yesno_on_write_autocomplete_multiline_paste.setChecked( self._new_options.GetBoolean( 'skip_yesno_on_write_autocomplete_multiline_paste' ) )
            self._skip_yesno_on_write_autocomplete_multiline_paste.setToolTip( ClientGUIFunctions.WrapToolTip( 'If you paste multiline content into the text box of an edit autocomplete that has a paste button, it will ask you if you want to add what you pasted as separate tags. Check this to skip that yes/no test and just do it every time.' ) )
            
            self._expand_parents_on_storage_autocomplete_taglists.setChecked( self._new_options.GetBoolean( 'expand_parents_on_storage_autocomplete_taglists' ) )
            self._expand_parents_on_storage_autocomplete_taglists.setToolTip( ClientGUIFunctions.WrapToolTip( 'This affects the autocomplete results taglist.' ) )
            
            self._show_parent_decorators_on_storage_taglists.setChecked( self._new_options.GetBoolean( 'show_parent_decorators_on_storage_taglists' ) )
            self._show_parent_decorators_on_storage_taglists.setToolTip( ClientGUIFunctions.WrapToolTip( 'This affects taglists in places like the manage tags dialog, where you edit tags as they actually are, and implied parents either hang below tags or summarise in a suffix.' ) )
            
            self._show_parent_decorators_on_storage_autocomplete_taglists.setChecked( self._new_options.GetBoolean( 'show_parent_decorators_on_storage_autocomplete_taglists' ) )
            self._show_parent_decorators_on_storage_autocomplete_taglists.setToolTip( ClientGUIFunctions.WrapToolTip( 'This affects the autocomplete results taglist.' ) )
            
            self._show_sibling_decorators_on_storage_taglists.setChecked( self._new_options.GetBoolean( 'show_sibling_decorators_on_storage_taglists' ) )
            self._show_sibling_decorators_on_storage_taglists.setToolTip( ClientGUIFunctions.WrapToolTip( 'This affects taglists in places like the manage tags dialog, where you edit tags as they actually are, and siblings summarise in a suffix.' ) )
            
            self._show_sibling_decorators_on_storage_autocomplete_taglists.setChecked( self._new_options.GetBoolean( 'show_sibling_decorators_on_storage_autocomplete_taglists' ) )
            self._show_sibling_decorators_on_storage_autocomplete_taglists.setToolTip( ClientGUIFunctions.WrapToolTip( 'This affects the autocomplete results taglist.' ) )
            
            #
            
            rows = []
            
            rows.append( ( 'Use listbook instead of tabbed notebook for tag service panels: ', self._use_listbook_for_tag_service_panels ) )
            rows.append( ( 'Remember last used default tag service in manage tag dialogs: ', self._save_default_tag_service_tab_on_change ) )
            rows.append( ( 'Default tag service in tag dialogs: ', self._default_tag_service_tab ) )
            rows.append( ( 'Number of recent petition reasons to remember in dialogs: ', self._num_recent_petition_reasons ) )
            rows.append( ( 'Show parent info by default on edit/write taglists: ', self._show_parent_decorators_on_storage_taglists ) )
            rows.append( ( 'Show parents expanded by default on edit/write taglists: ', self._expand_parents_on_storage_taglists ) )
            rows.append( ( 'Show sibling info by default on edit/write taglists: ', self._show_sibling_decorators_on_storage_taglists ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self._tag_services_panel, rows )
            
            self._tag_services_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            
            #
            
            message = 'This tag autocomplete appears in the manage tags dialog and other places where you edit a list of tags.'
            
            st = ClientGUICommon.BetterStaticText( self._write_autocomplete_panel, label = message )
            
            self._write_autocomplete_panel.Add( st, CC.FLAGS_CENTER )
            
            rows = []
            
            rows.append( ( 'By default, select the first tag result with actual count in write-autocomplete: ', self._ac_select_first_with_count ) )
            rows.append( ( 'When pasting multiline content into a write-autocomplete, skip the yes/no check: ', self._skip_yesno_on_write_autocomplete_multiline_paste ) )
            rows.append( ( 'Show parent info by default on edit/write autocomplete taglists: ', self._show_parent_decorators_on_storage_autocomplete_taglists ) )
            rows.append( ( 'Show parents expanded by default on edit/write autocomplete taglists: ', self._expand_parents_on_storage_autocomplete_taglists ) )
            rows.append( ( 'Show sibling info by default on edit/write autocomplete taglists: ', self._show_sibling_decorators_on_storage_autocomplete_taglists ) )
            rows.append( ( 'Autocomplete list height: ', self._ac_write_list_height_num_chars ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self._write_autocomplete_panel, rows )
            
            self._write_autocomplete_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            
            #
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, self._tag_services_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, self._write_autocomplete_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.addStretch( 0 )
            
            self.setLayout( vbox )
            
            self._UpdateDefaultTagServiceControl()
            
            self._save_default_tag_service_tab_on_change.clicked.connect( self._UpdateDefaultTagServiceControl )
            
        
        def _UpdateDefaultTagServiceControl( self ):
            
            enabled = not self._save_default_tag_service_tab_on_change.isChecked()
            
            self._default_tag_service_tab.setEnabled( enabled )
            
        
        def UpdateOptions( self ):
            
            self._new_options.SetBoolean( 'use_listbook_for_tag_service_panels', self._use_listbook_for_tag_service_panels.isChecked() )
            
            self._new_options.SetInteger( 'num_recent_petition_reasons', self._num_recent_petition_reasons.value() )
            
            self._new_options.SetBoolean( 'ac_select_first_with_count', self._ac_select_first_with_count.isChecked() )
            
            self._new_options.SetInteger( 'ac_write_list_height_num_chars', self._ac_write_list_height_num_chars.value() )
            
            self._new_options.SetBoolean( 'skip_yesno_on_write_autocomplete_multiline_paste', self._skip_yesno_on_write_autocomplete_multiline_paste.isChecked() )
            
            self._new_options.SetBoolean( 'show_parent_decorators_on_storage_taglists', self._show_parent_decorators_on_storage_taglists.isChecked() )
            self._new_options.SetBoolean( 'show_parent_decorators_on_storage_autocomplete_taglists', self._show_parent_decorators_on_storage_autocomplete_taglists.isChecked() )
            self._new_options.SetBoolean( 'expand_parents_on_storage_taglists', self._expand_parents_on_storage_taglists.isChecked() )
            self._new_options.SetBoolean( 'expand_parents_on_storage_autocomplete_taglists', self._expand_parents_on_storage_autocomplete_taglists.isChecked() )
            self._new_options.SetBoolean( 'show_sibling_decorators_on_storage_taglists', self._show_sibling_decorators_on_storage_taglists.isChecked() )
            self._new_options.SetBoolean( 'show_sibling_decorators_on_storage_autocomplete_taglists', self._show_sibling_decorators_on_storage_autocomplete_taglists.isChecked() )
            
            self._new_options.SetBoolean( 'save_default_tag_service_tab_on_change', self._save_default_tag_service_tab_on_change.isChecked() )
            self._new_options.SetKey( 'default_tag_service_tab', self._default_tag_service_tab.GetValue() )
            
        
    
    class _TagPresentationPanel( OptionsPagePanel ):
        
        def __init__( self, parent, new_options ):
            
            super().__init__( parent )
            
            self._new_options = new_options
            
            #
            
            self._tag_banners_panel = ClientGUICommon.StaticBox( self, 'tag banners' )
            
            tag_summary_generator = self._new_options.GetTagSummaryGenerator( 'thumbnail_top' )
            
            self._thumbnail_top = ClientGUITagSummaryGenerator.TagSummaryGeneratorButton( self._tag_banners_panel, tag_summary_generator )
            
            tag_summary_generator = self._new_options.GetTagSummaryGenerator( 'thumbnail_bottom_right' )
            
            self._thumbnail_bottom_right = ClientGUITagSummaryGenerator.TagSummaryGeneratorButton( self._tag_banners_panel, tag_summary_generator )
            
            tag_summary_generator = self._new_options.GetTagSummaryGenerator( 'media_viewer_top' )
            
            self._media_viewer_top = ClientGUITagSummaryGenerator.TagSummaryGeneratorButton( self._tag_banners_panel, tag_summary_generator )
            
            #
            
            self._selection_tags_panel = ClientGUICommon.StaticBox( self, 'selection tags' )
            
            self._number_of_unselected_medias_to_present_tags_for = ClientGUICommon.NoneableSpinCtrl( self._selection_tags_panel, 4096, max = 10000000 )
            
            #
            
            namespace_rendering_panel = ClientGUICommon.StaticBox( self, 'namespace rendering' )
            
            render_st = ClientGUICommon.BetterStaticText( namespace_rendering_panel, label = 'Namespaced tags are stored and directly edited in hydrus as "namespace:subtag", but most presentation windows can display them differently.' )
            
            self._show_namespaces = QW.QCheckBox( namespace_rendering_panel )
            self._show_number_namespaces = QW.QCheckBox( namespace_rendering_panel )
            self._show_number_namespaces.setToolTip( ClientGUIFunctions.WrapToolTip( 'This lets unnamespaced "16:9" show as that, not hiding the "16".' ) )
            self._show_subtag_number_namespaces = QW.QCheckBox( namespace_rendering_panel )
            self._show_subtag_number_namespaces.setToolTip( ClientGUIFunctions.WrapToolTip( 'This lets unnamespaced "page:3" show as that, not hiding the "page" where it can get mixed with chapter etc...' ) )
            self._namespace_connector = QW.QLineEdit( namespace_rendering_panel )
            
            #
            
            other_rendering_panel = ClientGUICommon.StaticBox( self, 'other rendering' )
            
            self._sibling_connector = QW.QLineEdit( other_rendering_panel )
            
            self._fade_sibling_connector = QW.QCheckBox( other_rendering_panel )
            tt = 'If set, then if the sibling goes from one namespace to another, that colour will fade across the distance of the sibling connector. Just a bit of fun.'
            self._fade_sibling_connector.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            self._sibling_connector_custom_namespace_colour = ClientGUICommon.NoneableTextCtrl( other_rendering_panel, 'system', none_phrase = 'use ideal tag colour' )
            tt = 'The sibling connector can use a particular namespace\'s colour.'
            self._sibling_connector_custom_namespace_colour.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            self._or_connector = QW.QLineEdit( other_rendering_panel )
            tt = 'When an OR predicate is rendered on one line, it splits the components by this text.'
            self._or_connector.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            self._or_connector_custom_namespace_colour = QW.QLineEdit( other_rendering_panel )
            tt = 'The "OR:" row can use a particular namespace\'s colour.'
            self._or_connector_custom_namespace_colour.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            self._replace_tag_underscores_with_spaces = QW.QCheckBox( other_rendering_panel )
            self._replace_tag_underscores_with_spaces.setToolTip( ClientGUIFunctions.WrapToolTip( 'This does not logically merge tags or change behaviour in any way, it only changes tag rendering in UI.' ) )
            
            self._replace_tag_emojis_with_boxes = QW.QCheckBox( other_rendering_panel )
            self._replace_tag_emojis_with_boxes.setToolTip( ClientGUIFunctions.WrapToolTip( 'This will replace emojis and weird symbols with □ in front-facing user views, in case you are getting crazy rendering. It may break some CJK punctuation.' ) )
            
            #
            
            namespace_colours_panel = ClientGUICommon.StaticBox( self, 'namespace colours' )
            
            self._namespace_colours = ClientGUIListBoxes.ListBoxTagsColourOptions( namespace_colours_panel, HC.options[ 'namespace_colours' ] )
            
            self._add_namespace_colour = ClientGUICommon.BetterButton( self, 'add', self._AddNamespaceColour )
            self._edit_namespace_colour = ClientGUICommon.BetterButton( self, 'edit', self._EditNamespaceColour )
            self._delete_namespace_colour = ClientGUICommon.BetterButton( self, 'delete', self._DeleteNamespaceColour )
            
            #
            
            self._number_of_unselected_medias_to_present_tags_for.SetValue( self._new_options.GetNoneableInteger( 'number_of_unselected_medias_to_present_tags_for' ) )
            self._number_of_unselected_medias_to_present_tags_for.setToolTip( ClientGUIFunctions.WrapToolTip( 'The "selection tags" box on any search page will show the tags for all files when none are selected. To save CPU, very large pages will cap out and not try to generate (and regenerate on any changes) for everything.') )
            
            self._show_namespaces.setChecked( new_options.GetBoolean( 'show_namespaces' ) )
            self._show_number_namespaces.setChecked( new_options.GetBoolean( 'show_number_namespaces' ) )
            self._show_subtag_number_namespaces.setChecked( new_options.GetBoolean( 'show_subtag_number_namespaces' ) )
            self._namespace_connector.setText( new_options.GetString( 'namespace_connector' ) )
            self._replace_tag_underscores_with_spaces.setChecked( new_options.GetBoolean( 'replace_tag_underscores_with_spaces' ) )
            self._replace_tag_emojis_with_boxes.setChecked( new_options.GetBoolean( 'replace_tag_emojis_with_boxes' ) )
            self._sibling_connector.setText( new_options.GetString( 'sibling_connector' ) )
            self._fade_sibling_connector.setChecked( new_options.GetBoolean( 'fade_sibling_connector' ) )
            self._sibling_connector_custom_namespace_colour.SetValue( new_options.GetNoneableString( 'sibling_connector_custom_namespace_colour' ) )
            self._or_connector.setText( new_options.GetString( 'or_connector' ) )
            self._or_connector_custom_namespace_colour.setText( new_options.GetNoneableString( 'or_connector_custom_namespace_colour' ) )
            
            #
            
            rows = []
            
            rows.append( ( 'Max number of thumbnails to compute tags for when none are selected: ', self._number_of_unselected_medias_to_present_tags_for ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self._selection_tags_panel, rows )
            
            self._selection_tags_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            namespace_colours_panel.Add( self._namespace_colours, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            hbox = QP.HBoxLayout()
            
            QP.AddToLayout( hbox, self._add_namespace_colour, CC.FLAGS_EXPAND_BOTH_WAYS )
            QP.AddToLayout( hbox, self._edit_namespace_colour, CC.FLAGS_EXPAND_BOTH_WAYS )
            QP.AddToLayout( hbox, self._delete_namespace_colour, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            namespace_colours_panel.Add( hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            #
            
            vbox = QP.VBoxLayout()
            
            #
            
            rows = []
            
            rows.append( ( 'On thumbnail top:', self._thumbnail_top ) )
            rows.append( ( 'On thumbnail bottom-right:', self._thumbnail_bottom_right ) )
            rows.append( ( 'On media viewer top:', self._media_viewer_top ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self, rows )
            
            self._tag_banners_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            rows = []
            
            rows.append( ( 'Show namespaces: ', self._show_namespaces ) )
            rows.append( ( 'Show namespace if it is a number: ', self._show_number_namespaces ) )
            rows.append( ( 'Show namespace if subtag is a number: ', self._show_subtag_number_namespaces ) )
            rows.append( ( 'If shown, namespace connecting string: ', self._namespace_connector ) )
            
            gridbox = ClientGUICommon.WrapInGrid( namespace_rendering_panel, rows )
            
            namespace_rendering_panel.Add( render_st, CC.FLAGS_EXPAND_PERPENDICULAR )
            namespace_rendering_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            rows = []
            
            rows.append( ( 'Sibling connecting string: ', self._sibling_connector ) )
            rows.append( ( 'Fade the colour of the sibling connector string on Qt6: ', self._fade_sibling_connector ) )
            rows.append( ( 'Namespace for the colour of the sibling connecting string: ', self._sibling_connector_custom_namespace_colour ) )
            rows.append( ( 'OR connecting string (on one line): ', self._or_connector ) )
            rows.append( ( 'Namespace for the OR top row: ', self._or_connector_custom_namespace_colour ) )
            rows.append( ( 'EXPERIMENTAL: Replace all underscores with spaces: ', self._replace_tag_underscores_with_spaces ) )
            rows.append( ( 'EXPERIMENTAL: Replace all emojis with □: ', self._replace_tag_emojis_with_boxes ) )
            
            gridbox = ClientGUICommon.WrapInGrid( other_rendering_panel, rows )
            
            other_rendering_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            QP.AddToLayout( vbox, self._tag_banners_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, self._selection_tags_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, namespace_rendering_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, other_rendering_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, namespace_colours_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            #
            
            self._NamespacesUpdated()
            self._SiblingColourStuffClicked()
            
            self._show_namespaces.clicked.connect( self._NamespacesUpdated )
            self._fade_sibling_connector.clicked.connect( self._SiblingColourStuffClicked )
            
            self.setLayout( vbox )
            
        
        def _AddNamespaceColour( self ):
            
            try:
                
                namespace = ClientGUIDialogsQuick.EnterText( self, 'Enter the namespace.' )
                
            except HydrusExceptions.CancelledException:
                
                return
                
            
            namespace = namespace.lower().strip()
            
            if namespace in ( '', ':' ):
                
                ClientGUIDialogsMessage.ShowWarning( self, 'Sorry, that namespace means unnamespaced/default namespaced, which are already listed.' )
                
                return
                
            
            while namespace.endswith( ':' ):
                
                namespace = namespace[:-1]
                
            
            if namespace != 'system':
                
                namespace = HydrusTags.StripTagTextOfGumpf( namespace )
                
            
            existing_namespaces = self._namespace_colours.GetNamespaceColours().keys()
            
            if namespace in existing_namespaces:
                
                ClientGUIDialogsMessage.ShowWarning( self, 'Sorry, that namespace is already listed!' )
                
                return
                
            
            self._namespace_colours.SetNamespaceColour( namespace, QG.QColor( random.randint(0,255), random.randint(0,255), random.randint(0,255) ) )
            
        
        def _DeleteNamespaceColour( self ):
            
            self._namespace_colours.DeleteSelected()
            
        
        def _EditNamespaceColour( self ):
            
            results = self._namespace_colours.GetSelectedNamespaceColours()
            
            for ( namespace, ( r, g, b ) ) in list( results.items() ):
                
                colour = QG.QColor( r, g, b )
                
                colour = ClientGUIColourPicker.EditColour( self, colour )
                
                self._namespace_colours.SetNamespaceColour( namespace, colour )
                
            
        
        def _SiblingColourStuffClicked( self ):
            
            choice_available = not self._fade_sibling_connector.isChecked()
            
            self._sibling_connector_custom_namespace_colour.setEnabled( choice_available )
            
        
        def _NamespacesUpdated( self ):
            
            self._show_number_namespaces.setEnabled( not self._show_namespaces.isChecked() )
            self._show_subtag_number_namespaces.setEnabled( not self._show_namespaces.isChecked() )
            
        
        def UpdateOptions( self ):
            
            self._new_options.SetNoneableInteger( 'number_of_unselected_medias_to_present_tags_for', self._number_of_unselected_medias_to_present_tags_for.GetValue() )
            
            self._new_options.SetTagSummaryGenerator( 'thumbnail_top', self._thumbnail_top.GetValue() )
            self._new_options.SetTagSummaryGenerator( 'thumbnail_bottom_right', self._thumbnail_bottom_right.GetValue() )
            self._new_options.SetTagSummaryGenerator( 'media_viewer_top', self._media_viewer_top.GetValue() )
            
            self._new_options.SetBoolean( 'show_namespaces', self._show_namespaces.isChecked() )
            self._new_options.SetBoolean( 'show_number_namespaces', self._show_number_namespaces.isChecked() )
            self._new_options.SetBoolean( 'show_subtag_number_namespaces', self._show_subtag_number_namespaces.isChecked() )
            self._new_options.SetString( 'namespace_connector', self._namespace_connector.text() )
            self._new_options.SetBoolean( 'replace_tag_underscores_with_spaces', self._replace_tag_underscores_with_spaces.isChecked() )
            self._new_options.SetBoolean( 'replace_tag_emojis_with_boxes', self._replace_tag_emojis_with_boxes.isChecked() )
            self._new_options.SetString( 'sibling_connector', self._sibling_connector.text() )
            self._new_options.SetBoolean( 'fade_sibling_connector', self._fade_sibling_connector.isChecked() )
            
            self._new_options.SetNoneableString( 'sibling_connector_custom_namespace_colour', self._sibling_connector_custom_namespace_colour.GetValue() )
            
            self._new_options.SetString( 'or_connector', self._or_connector.text() )
            self._new_options.SetNoneableString( 'or_connector_custom_namespace_colour', self._or_connector_custom_namespace_colour.text() )
            
            HC.options[ 'namespace_colours' ] = self._namespace_colours.GetNamespaceColours()
            
        
    
    class _TagSortPanel( OptionsPagePanel ):
        
        def __init__( self, parent, new_options ):
            
            super().__init__( parent )
            
            self._new_options = new_options
            
            self._tag_sort_panel = ClientGUICommon.StaticBox( self, 'tag sort' )
            
            self._default_tag_sort_search_page = ClientGUITagSorting.TagSortControl( self._tag_sort_panel, self._new_options.GetDefaultTagSort( CC.TAG_PRESENTATION_SEARCH_PAGE ) )
            self._default_tag_sort_search_page_manage_tags = ClientGUITagSorting.TagSortControl( self._tag_sort_panel, self._new_options.GetDefaultTagSort( CC.TAG_PRESENTATION_SEARCH_PAGE_MANAGE_TAGS ), show_siblings = True )
            self._default_tag_sort_media_viewer = ClientGUITagSorting.TagSortControl( self._tag_sort_panel, self._new_options.GetDefaultTagSort( CC.TAG_PRESENTATION_MEDIA_VIEWER ) )
            self._default_tag_sort_media_viewer_manage_tags = ClientGUITagSorting.TagSortControl( self._tag_sort_panel, self._new_options.GetDefaultTagSort( CC.TAG_PRESENTATION_MEDIA_VIEWER_MANAGE_TAGS ), show_siblings = True )
            
            #
            
            user_namespace_group_by_sort_box = ClientGUICommon.StaticBox( self._tag_sort_panel, 'namespace grouping sort' )
            
            self._user_namespace_group_by_sort = ClientGUIListBoxes.QueueListBox( user_namespace_group_by_sort_box, 8, ClientTags.RenderNamespaceForUser, add_callable = self._AddNamespaceGroupBySort, edit_callable = self._EditNamespaceGroupBySort, paste_callable = self._PasteNamespaceGroupBySort )
            
            #
            
            self._user_namespace_group_by_sort.AddDatas( CG.client_controller.new_options.GetStringList( 'user_namespace_group_by_sort' ) )
            
            #
            
            group_by_sort_text = 'You can manage the custom "(user)" namespace grouping sort here. This lets you put, say, "creator" tags above any other namespace in a tag sort.'
            group_by_sort_text += '\n'
            group_by_sort_text += 'Any namespaces not listed here will be listed afterwards in a-z format, with unnamespaced following, just like the normal (a-z) namespace grouping.'
            
            user_namespace_group_by_sort_box.Add( ClientGUICommon.BetterStaticText( user_namespace_group_by_sort_box, group_by_sort_text ), CC.FLAGS_EXPAND_PERPENDICULAR )
            user_namespace_group_by_sort_box.Add( self._user_namespace_group_by_sort, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            #
            
            rows = []
            
            rows.append( ( 'Default tag sort in search pages: ', self._default_tag_sort_search_page ) )
            rows.append( ( 'Default tag sort in search page manage tags dialogs: ', self._default_tag_sort_search_page_manage_tags ) )
            rows.append( ( 'Default tag sort in the media viewer: ', self._default_tag_sort_media_viewer ) )
            rows.append( ( 'Default tag sort in media viewer manage tags dialogs: ', self._default_tag_sort_media_viewer_manage_tags ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self._tag_sort_panel, rows )
            
            self._tag_sort_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            self._tag_sort_panel.Add( user_namespace_group_by_sort_box, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, self._tag_sort_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            self.setLayout( vbox )
            
        
        def _AddNamespaceGroupBySort( self ):
            
            default = 'namespace'
            
            return self._EditNamespaceGroupBySort( default )
            
        
        def _EditNamespaceGroupBySort( self, namespace ):
            
            message = 'Enter the namespace. Leave blank for unnamespaced tags, use ":" for all unspecified namespaced tags.'
            
            try:
                
                edited_namespace = ClientGUIDialogsQuick.EnterText( self, message, default = namespace, allow_blank = True )
                
            except HydrusExceptions.CancelledException:
                
                raise
                
            
            return edited_namespace
            
        
        def _PasteNamespaceGroupBySort( self ):
            
            try:
                
                text = CG.client_controller.GetClipboardText()
                
            except Exception as e:
                
                raise HydrusExceptions.VetoException()
                
            
            namespaces = HydrusText.DeserialiseNewlinedTexts( text )
            
            return namespaces
            
        
        def UpdateOptions( self ):
            
            self._new_options.SetDefaultTagSort( CC.TAG_PRESENTATION_SEARCH_PAGE, self._default_tag_sort_search_page.GetValue() )
            self._new_options.SetDefaultTagSort( CC.TAG_PRESENTATION_SEARCH_PAGE_MANAGE_TAGS, self._default_tag_sort_search_page_manage_tags.GetValue() )
            self._new_options.SetDefaultTagSort( CC.TAG_PRESENTATION_MEDIA_VIEWER, self._default_tag_sort_media_viewer.GetValue() )
            self._new_options.SetDefaultTagSort( CC.TAG_PRESENTATION_MEDIA_VIEWER_MANAGE_TAGS, self._default_tag_sort_media_viewer_manage_tags.GetValue() )
            
            user_namespace_group_by_sort = self._user_namespace_group_by_sort.GetData()
            
            self._new_options.SetStringList( 'user_namespace_group_by_sort', user_namespace_group_by_sort )
            
        
    
    class _TagSuggestionsPanel( OptionsPagePanel ):
        
        def __init__( self, parent, new_options ):
            
            super().__init__( parent )
            
            self._new_options = new_options
            
            suggested_tags_panel = ClientGUICommon.StaticBox( self, 'suggested tags' )
            
            self._suggested_tags_width = ClientGUICommon.BetterSpinBox( suggested_tags_panel, min=20, max=65535 )
            
            self._suggested_tags_layout = ClientGUICommon.BetterChoice( suggested_tags_panel )
            
            self._suggested_tags_layout.addItem( 'notebook', 'notebook' )
            self._suggested_tags_layout.addItem( 'side-by-side', 'columns' )
            
            self._default_suggested_tags_notebook_page = ClientGUICommon.BetterChoice( suggested_tags_panel )
            
            for item in [ 'favourites', 'related', 'file_lookup_scripts', 'recent' ]:
                
                label = 'most used' if item == 'favourites' else item
                
                self._default_suggested_tags_notebook_page.addItem( label, item )
                
            
            suggest_tags_panel_notebook = QW.QTabWidget( suggested_tags_panel )
            
            #
            
            suggested_tags_favourites_panel = QW.QWidget( suggest_tags_panel_notebook )
            
            suggested_tags_favourites_panel.setMinimumWidth( 400 )
            
            self._suggested_favourites_services = ClientGUICommon.BetterChoice( suggested_tags_favourites_panel )
            
            tag_services = CG.client_controller.services_manager.GetServices( HC.REAL_TAG_SERVICES )
            
            for tag_service in tag_services:
                
                self._suggested_favourites_services.addItem( tag_service.GetName(), tag_service.GetServiceKey() )
                
            
            self._suggested_favourites = ClientGUIListBoxes.ListBoxTagsStringsAddRemove( suggested_tags_favourites_panel, CC.COMBINED_TAG_SERVICE_KEY, tag_display_type = ClientTags.TAG_DISPLAY_STORAGE )
            
            self._current_suggested_favourites_service = None
            
            self._suggested_favourites_dict = {}
            
            default_location_context = CG.client_controller.new_options.GetDefaultLocalLocationContext()
            
            self._suggested_favourites_input = ClientGUIACDropdown.AutoCompleteDropdownTagsWrite( suggested_tags_favourites_panel, self._suggested_favourites.AddTags, default_location_context, CC.COMBINED_TAG_SERVICE_KEY, show_paste_button = True )
            
            self._suggested_favourites.tagsChanged.connect( self._suggested_favourites_input.SetContextTags )
            
            self._suggested_favourites_input.externalCopyKeyPressEvent.connect( self._suggested_favourites.keyPressEvent )
            
            #
            
            suggested_tags_related_panel = QW.QWidget( suggest_tags_panel_notebook )
            
            self._show_related_tags = QW.QCheckBox( suggested_tags_related_panel )
            
            self._related_tags_search_1_duration_ms = ClientGUICommon.BetterSpinBox( suggested_tags_related_panel, min=50, max=60000 )
            self._related_tags_search_2_duration_ms = ClientGUICommon.BetterSpinBox( suggested_tags_related_panel, min=50, max=60000 )
            self._related_tags_search_3_duration_ms = ClientGUICommon.BetterSpinBox( suggested_tags_related_panel, min=50, max=60000 )
            
            self._related_tags_concurrence_threshold_percent = ClientGUICommon.BetterSpinBox( suggested_tags_related_panel, min = 1, max = 100 )
            tt = 'The related tags system looks for tags that tend to be used on the same files. Here you can set how strict it is. How many percent of tag A\'s files must tag B on for tag B to be a good suggestion? Higher numbers will mean fewer but more relevant suggestions.'
            self._related_tags_concurrence_threshold_percent.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            #
            
            search_tag_slices_weight_box = ClientGUICommon.StaticBox( suggested_tags_related_panel, 'adjust scores by search tags' )
            
            search_tag_slices_weight_panel = ClientGUIListCtrl.BetterListCtrlPanel( search_tag_slices_weight_box )
            
            model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_TAG_SLICE_WEIGHT.ID, self._ConvertTagSliceAndWeightToDisplayTuple, self._ConvertTagSliceAndWeightToSortTuple )
            
            self._search_tag_slices_weights = ClientGUIListCtrl.BetterListCtrlTreeView( search_tag_slices_weight_panel, 8, model, activation_callback = self._EditSearchTagSliceWeight, use_simple_delete = True, can_delete_callback = self._CanDeleteSearchTagSliceWeight )
            tt = 'ADVANCED! These weights adjust the ranking scores of suggested tags by the tag type that searched for them. Set to 0 to not search with that type of tag.'
            self._search_tag_slices_weights.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            search_tag_slices_weight_panel.SetListCtrl( self._search_tag_slices_weights )
            
            search_tag_slices_weight_panel.AddButton( 'add', self._AddSearchTagSliceWeight )
            search_tag_slices_weight_panel.AddButton( 'edit', self._EditSearchTagSliceWeight, enabled_only_on_single_selection = True )
            search_tag_slices_weight_panel.AddDeleteButton( enabled_check_func = self._CanDeleteSearchTagSliceWeight )
            
            #
            
            result_tag_slices_weight_box = ClientGUICommon.StaticBox( suggested_tags_related_panel, 'adjust scores by suggested tags' )
            
            result_tag_slices_weight_panel = ClientGUIListCtrl.BetterListCtrlPanel( result_tag_slices_weight_box )
            
            model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_TAG_SLICE_WEIGHT.ID, self._ConvertTagSliceAndWeightToDisplayTuple, self._ConvertTagSliceAndWeightToSortTuple )
            
            self._result_tag_slices_weights = ClientGUIListCtrl.BetterListCtrlTreeView( result_tag_slices_weight_panel, 8, model, activation_callback = self._EditResultTagSliceWeight, use_simple_delete = True, can_delete_callback = self._CanDeleteResultTagSliceWeight )
            tt = 'ADVANCED! These weights adjust the ranking scores of suggested tags by their tag type. Set to 0 to not suggest that type of tag at all.'
            self._result_tag_slices_weights.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            result_tag_slices_weight_panel.SetListCtrl( self._result_tag_slices_weights )
            
            result_tag_slices_weight_panel.AddButton( 'add', self._AddResultTagSliceWeight )
            result_tag_slices_weight_panel.AddButton( 'edit', self._EditResultTagSliceWeight, enabled_only_on_single_selection = True )
            result_tag_slices_weight_panel.AddDeleteButton( enabled_check_func = self._CanDeleteResultTagSliceWeight )
            
            #
            
            suggested_tags_file_lookup_script_panel = QW.QWidget( suggest_tags_panel_notebook )
            
            self._show_file_lookup_script_tags = QW.QCheckBox( suggested_tags_file_lookup_script_panel )
            
            self._favourite_file_lookup_script = ClientGUICommon.BetterChoice( suggested_tags_file_lookup_script_panel )
            
            script_names = sorted( CG.client_controller.Read( 'serialisable_names', HydrusSerialisable.SERIALISABLE_TYPE_PARSE_ROOT_FILE_LOOKUP ) )
            
            for name in script_names:
                
                self._favourite_file_lookup_script.addItem( name, name )
                
            
            #
            
            suggested_tags_recent_panel = QW.QWidget( suggest_tags_panel_notebook )
            
            self._num_recent_tags = ClientGUICommon.NoneableSpinCtrl( suggested_tags_recent_panel, 20, message = 'number of recent tags to show', min = 1, none_phrase = 'do not show' )
            
            #
            
            self._suggested_tags_width.setValue( self._new_options.GetInteger( 'suggested_tags_width' ) )
            
            self._suggested_tags_layout.SetValue( self._new_options.GetNoneableString( 'suggested_tags_layout' ) )
            
            self._default_suggested_tags_notebook_page.SetValue( self._new_options.GetString( 'default_suggested_tags_notebook_page' ) )
            
            #
            
            self._show_related_tags.setChecked( self._new_options.GetBoolean( 'show_related_tags' ) )
            
            self._related_tags_search_1_duration_ms.setValue( self._new_options.GetInteger( 'related_tags_search_1_duration_ms' ) )
            self._related_tags_search_2_duration_ms.setValue( self._new_options.GetInteger( 'related_tags_search_2_duration_ms' ) )
            self._related_tags_search_3_duration_ms.setValue( self._new_options.GetInteger( 'related_tags_search_3_duration_ms' ) )
            
            self._related_tags_concurrence_threshold_percent.setValue( self._new_options.GetInteger( 'related_tags_concurrence_threshold_percent' ) )

            ( related_tags_search_tag_slices_weight_percent, related_tags_result_tag_slices_weight_percent ) = self._new_options.GetRelatedTagsTagSliceWeights()
            
            self._search_tag_slices_weights.SetData( related_tags_search_tag_slices_weight_percent )
            self._result_tag_slices_weights.SetData( related_tags_result_tag_slices_weight_percent )
            
            self._show_file_lookup_script_tags.setChecked( self._new_options.GetBoolean( 'show_file_lookup_script_tags' ) )
            
            self._favourite_file_lookup_script.SetValue( self._new_options.GetNoneableString( 'favourite_file_lookup_script' ) )
            
            self._num_recent_tags.SetValue( self._new_options.GetNoneableInteger( 'num_recent_tags' ) )
            
            #
            
            panel_vbox = QP.VBoxLayout()
            
            st = ClientGUICommon.BetterStaticText( suggested_tags_favourites_panel, 'Add your most used tags for each particular service here, and then you can just double-click to add, rather than typing every time.' )
            st.setWordWrap( True )
            
            QP.AddToLayout( panel_vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            rows = []
            
            rows.append( ( 'Tag service: ', self._suggested_favourites_services ) )
            
            gridbox = ClientGUICommon.WrapInGrid( suggested_tags_favourites_panel, rows )
            
            QP.AddToLayout( panel_vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            QP.AddToLayout( panel_vbox, self._suggested_favourites, CC.FLAGS_EXPAND_BOTH_WAYS )
            QP.AddToLayout( panel_vbox, self._suggested_favourites_input, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            suggested_tags_favourites_panel.setLayout( panel_vbox )
            
            #
            
            panel_vbox = QP.VBoxLayout()
            
            rows = []
            
            rows.append( ( 'Show related tags: ', self._show_related_tags ) )
            rows.append( ( 'Initial/Quick search duration (ms): ', self._related_tags_search_1_duration_ms ) )
            rows.append( ( 'Medium search duration (ms): ', self._related_tags_search_2_duration_ms ) )
            rows.append( ( 'Thorough search duration (ms): ', self._related_tags_search_3_duration_ms ) )
            rows.append( ( 'Tag concurrence threshold %: ', self._related_tags_concurrence_threshold_percent ) )
            
            gridbox = ClientGUICommon.WrapInGrid( suggested_tags_related_panel, rows )
            
            search_tag_slices_weight_box.Add( search_tag_slices_weight_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            result_tag_slices_weight_box.Add( result_tag_slices_weight_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            desc = 'This will search the database for tags statistically related to what your files already have. It only searches within the specific service atm. The score weights are advanced, so only change them if you know what is going on!'
            st = ClientGUICommon.BetterStaticText( suggested_tags_related_panel, desc )
            st.setWordWrap( True )
            
            QP.AddToLayout( panel_vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( panel_vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            QP.AddToLayout( panel_vbox, search_tag_slices_weight_box, CC.FLAGS_EXPAND_BOTH_WAYS )
            QP.AddToLayout( panel_vbox, result_tag_slices_weight_box, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            suggested_tags_related_panel.setLayout( panel_vbox )
            
            #
            
            panel_vbox = QP.VBoxLayout()
            
            rows = []
            
            rows.append( ( 'Show file lookup scripts on single-file manage tags windows: ', self._show_file_lookup_script_tags ) )
            rows.append( ( 'Favourite file lookup script: ', self._favourite_file_lookup_script ) )
            
            gridbox = ClientGUICommon.WrapInGrid( suggested_tags_file_lookup_script_panel, rows )
            
            desc = 'This is an increasingly defunct system, do not expect miracles!'
            st = ClientGUICommon.BetterStaticText( suggested_tags_related_panel, desc )
            st.setWordWrap( True )
            
            QP.AddToLayout( panel_vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( panel_vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            panel_vbox.addStretch( 0 )
            
            suggested_tags_file_lookup_script_panel.setLayout( panel_vbox )
            
            #
            
            panel_vbox = QP.VBoxLayout()
            
            desc = 'This simply saves the last n tags you have added for each service.'
            st = ClientGUICommon.BetterStaticText( suggested_tags_related_panel, desc )
            st.setWordWrap( True )
            
            QP.AddToLayout( panel_vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( panel_vbox, self._num_recent_tags, CC.FLAGS_EXPAND_PERPENDICULAR )
            panel_vbox.addStretch( 0 )
            
            suggested_tags_recent_panel.setLayout( panel_vbox )
            
            #
            
            suggest_tags_panel_notebook.addTab( suggested_tags_favourites_panel, 'most used' )
            suggest_tags_panel_notebook.addTab( suggested_tags_related_panel, 'related' )
            suggest_tags_panel_notebook.addTab( suggested_tags_file_lookup_script_panel, 'file lookup scripts' )
            suggest_tags_panel_notebook.addTab( suggested_tags_recent_panel, 'recent' )
            
            #
            
            rows = []
            
            rows.append( ( 'Width of suggested tags columns: ', self._suggested_tags_width ) )
            rows.append( ( 'Column layout: ', self._suggested_tags_layout ) )
            rows.append( ( 'Default notebook page: ', self._default_suggested_tags_notebook_page ) )
            
            gridbox = ClientGUICommon.WrapInGrid( suggested_tags_panel, rows )
            
            desc = 'The manage tags dialog can provide several kinds of tag suggestions.'
            
            suggested_tags_panel.Add( ClientGUICommon.BetterStaticText( suggested_tags_panel, desc ), CC.FLAGS_EXPAND_PERPENDICULAR )
            suggested_tags_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            suggested_tags_panel.Add( suggest_tags_panel_notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            #
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, suggested_tags_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            self.setLayout( vbox )
            
            #
            
            self._suggested_favourites_services.currentIndexChanged.connect( self.EventSuggestedFavouritesService )
            self._suggested_tags_layout.currentIndexChanged.connect( self._NotifyLayoutChanged )
            
            self._NotifyLayoutChanged()
            self.EventSuggestedFavouritesService( None )
            
        
        def _AddResultTagSliceWeight( self ):
            
            self._AddTagSliceWeight( self._result_tag_slices_weights )
            
        
        def _AddSearchTagSliceWeight( self ):
            
            self._AddTagSliceWeight( self._search_tag_slices_weights )
            
        
        def _AddTagSliceWeight( self, list_ctrl ):
            
            message = 'enter namespace'
            
            try:
                
                tag_slice = ClientGUIDialogsQuick.EnterText( self, message )
                
            except HydrusExceptions.CancelledException:
                
                return
                
            
            if tag_slice in ( '', ':' ):
                
                ClientGUIDialogsMessage.ShowWarning( self, 'Sorry, you cannot re-add unnamespaced or namespaced!' )
                
                return
                
            
            if not tag_slice.endswith( ':' ):
                
                tag_slice = tag_slice + ':'
                
            
            existing_tag_slices = { existing_tag_slice for ( existing_tag_slice, existing_weight ) in list_ctrl.GetData() }
            
            if tag_slice in existing_tag_slices:
                
                ClientGUIDialogsMessage.ShowWarning( self, 'Sorry, that namespace already exists!' )
                
                return
                
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'set weight' ) as dlg_2:
                
                panel = ClientGUIScrolledPanels.EditSingleCtrlPanel( dlg_2 )
                
                control = ClientGUICommon.BetterSpinBox( panel, initial = 100, min = 0, max = 10000 )
                
                panel.SetControl( control, perpendicular = True )
                
                dlg_2.SetPanel( panel )
                
                if dlg_2.exec() == QW.QDialog.DialogCode.Accepted:
                    
                    weight = control.value()
                    
                    new_data = ( tag_slice, weight )
                    
                    list_ctrl.AddData( new_data, select_sort_and_scroll = True )
                    
                
            
        
        def _CanDeleteResultTagSliceWeight( self ) -> bool:
            
            return self._CanDeleteTagSliceWeight( self._result_tag_slices_weights )
            
        
        def _CanDeleteSearchTagSliceWeight( self ) -> bool:
            
            return self._CanDeleteTagSliceWeight( self._search_tag_slices_weights )
            
        
        def _CanDeleteTagSliceWeight( self, list_ctrl ) -> bool:
            
            selected_tag_slices_and_weights = list_ctrl.GetData( only_selected = True )
            
            for ( tag_slice, weight ) in selected_tag_slices_and_weights:
                
                if tag_slice in ( '', ':' ):
                    
                    return False
                    
                
            
            return True
            
        
        def _ConvertTagSliceAndWeightToDisplayTuple( self, tag_slice_and_weight ):
            
            ( tag_slice, weight ) = tag_slice_and_weight
            
            pretty_tag_slice = HydrusTags.ConvertTagSliceToPrettyString( tag_slice )
            
            pretty_weight = HydrusNumbers.ToHumanInt( weight ) + '%'
            
            display_tuple = ( pretty_tag_slice, pretty_weight )
            
            return display_tuple
            
        
        def _ConvertTagSliceAndWeightToSortTuple( self, tag_slice_and_weight ):
            
            ( tag_slice, weight ) = tag_slice_and_weight
            
            pretty_tag_slice = HydrusTags.ConvertTagSliceToPrettyString( tag_slice )
            sort_tag_slice = pretty_tag_slice
            
            sort_tuple = ( sort_tag_slice, weight )
            
            return sort_tuple
            
        
        def _EditResultTagSliceWeight( self ):
            
            self._EditTagSliceWeight( self._result_tag_slices_weights )
            
        
        def _EditSearchTagSliceWeight( self ):
            
            self._EditTagSliceWeight( self._search_tag_slices_weights )
            
        
        def _EditTagSliceWeight( self, list_ctrl ):
            
            original_data = list_ctrl.GetTopSelectedData()
            
            if original_data is None:
                
                return
                
            
            ( tag_slice, weight ) = original_data
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit weight' ) as dlg:
                
                panel = ClientGUIScrolledPanels.EditSingleCtrlPanel( dlg )
                
                control = ClientGUICommon.BetterSpinBox( panel, initial = weight, min = 0, max = 10000 )
                
                panel.SetControl( control, perpendicular = True )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                    
                    edited_weight = control.value()
                    
                    edited_data = ( tag_slice, edited_weight )
                    
                    list_ctrl.ReplaceData( original_data, edited_data, sort_and_scroll = True )
                    
                
            
        
        def _NotifyLayoutChanged( self ):
            
            enable_default_page = self._suggested_tags_layout.GetValue() == 'notebook'
            
            self._default_suggested_tags_notebook_page.setEnabled( enable_default_page )
            
        
        def _SaveCurrentSuggestedFavourites( self ):
            
            if self._current_suggested_favourites_service is not None:
                
                self._suggested_favourites_dict[ self._current_suggested_favourites_service ] = self._suggested_favourites.GetTags()
                
            
        
        def EventSuggestedFavouritesService( self, index ):
            
            self._SaveCurrentSuggestedFavourites()
            
            self._current_suggested_favourites_service = self._suggested_favourites_services.GetValue()
            
            if self._current_suggested_favourites_service in self._suggested_favourites_dict:
                
                favourites = self._suggested_favourites_dict[ self._current_suggested_favourites_service ]
                
            else:
                
                favourites = self._new_options.GetSuggestedTagsFavourites( self._current_suggested_favourites_service )
                
            
            self._suggested_favourites.SetTagServiceKey( self._current_suggested_favourites_service )
            
            self._suggested_favourites.SetTags( favourites )
            
            self._suggested_favourites_input.SetTagServiceKey( self._current_suggested_favourites_service )
            self._suggested_favourites_input.SetDisplayTagServiceKey( self._current_suggested_favourites_service )
            
        
        def UpdateOptions( self ):
            
            self._new_options.SetInteger( 'suggested_tags_width', self._suggested_tags_width.value() )
            self._new_options.SetNoneableString( 'suggested_tags_layout', self._suggested_tags_layout.GetValue() )
            
            self._new_options.SetString( 'default_suggested_tags_notebook_page', self._default_suggested_tags_notebook_page.GetValue() )
            
            self._SaveCurrentSuggestedFavourites()
            
            for ( service_key, favourites ) in list(self._suggested_favourites_dict.items()):
                
                self._new_options.SetSuggestedTagsFavourites( service_key, favourites )
                
            
            self._new_options.SetBoolean( 'show_related_tags', self._show_related_tags.isChecked() )
            
            self._new_options.SetInteger( 'related_tags_search_1_duration_ms', self._related_tags_search_1_duration_ms.value() )
            self._new_options.SetInteger( 'related_tags_search_2_duration_ms', self._related_tags_search_2_duration_ms.value() )
            self._new_options.SetInteger( 'related_tags_search_3_duration_ms', self._related_tags_search_3_duration_ms.value() )
            
            self._new_options.SetInteger( 'related_tags_concurrence_threshold_percent', self._related_tags_concurrence_threshold_percent.value() )
            
            related_tags_search_tag_slices_weight_percent = self._search_tag_slices_weights.GetData()
            related_tags_result_tag_slices_weight_percent = self._result_tag_slices_weights.GetData()
            
            self._new_options.SetRelatedTagsTagSliceWeights( related_tags_search_tag_slices_weight_percent, related_tags_result_tag_slices_weight_percent )
            
            self._new_options.SetBoolean( 'show_file_lookup_script_tags', self._show_file_lookup_script_tags.isChecked() )
            self._new_options.SetNoneableString( 'favourite_file_lookup_script', self._favourite_file_lookup_script.GetValue() )
            
            self._new_options.SetNoneableInteger( 'num_recent_tags', self._num_recent_tags.GetValue() )
            
        
    
    class _ThumbnailsPanel( OptionsPagePanel ):
        
        def __init__( self, parent, new_options ):
            
            super().__init__( parent )
            
            self._new_options = new_options
            
            thumbnail_appearance_box = ClientGUICommon.StaticBox( self, 'appearance' )
            
            self._thumbnail_width = ClientGUICommon.BetterSpinBox( thumbnail_appearance_box, min=20, max=2048 )
            self._thumbnail_height = ClientGUICommon.BetterSpinBox( thumbnail_appearance_box, min=20, max=2048 )
            
            self._thumbnail_border = ClientGUICommon.BetterSpinBox( thumbnail_appearance_box, min=0, max=20 )
            self._thumbnail_margin = ClientGUICommon.BetterSpinBox( thumbnail_appearance_box, min=0, max=20 )
            
            self._thumbnail_scale_type = ClientGUICommon.BetterChoice( thumbnail_appearance_box )
            
            for t in ( HydrusImageHandling.THUMBNAIL_SCALE_DOWN_ONLY, HydrusImageHandling.THUMBNAIL_SCALE_TO_FIT, HydrusImageHandling.THUMBNAIL_SCALE_TO_FILL ):
                
                self._thumbnail_scale_type.addItem( HydrusImageHandling.thumbnail_scale_str_lookup[ t ], t )
                
            
            # I tried <100%, but Qt seems to cap it to 1.0. Sad!
            self._thumbnail_dpr_percentage = ClientGUICommon.BetterSpinBox( thumbnail_appearance_box, min = 100, max = 800 )
            tt = 'If your OS runs at an UI scale greater than 100%, mirror it here and your thumbnails will look crisp. If you have multiple monitors at different UI scales, or you change UI scale regularly, set it to the largest one you use.'
            tt += '\n' * 2
            tt += 'I believe the UI scale on the monitor this dialog opened on was {}'.format( HydrusNumbers.FloatToPercentage( self.devicePixelRatio() ) )
            self._thumbnail_dpr_percentage.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            self._video_thumbnail_percentage_in = ClientGUICommon.BetterSpinBox( thumbnail_appearance_box, min=0, max=100 )
            
            self._fade_thumbnails = QW.QCheckBox( thumbnail_appearance_box )
            tt = 'Whenever thumbnails change (appearing on a page, selecting, an icon or tag banner changes), they normally fade from the old to the new. If you would rather they change instantly, in one frame, uncheck this.'
            self._fade_thumbnails.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            self._allow_blurhash_fallback = QW.QCheckBox( thumbnail_appearance_box )
            tt = 'If hydrus does not have a thumbnail for a file (e.g. you are looking at a deleted file, or one unexpectedly missing), but it does know its blurhash, it will generate a blurry thumbnail based off that blurhash. Turning this behaviour off here will make it always show the default "hydrus" thumbnail.'
            self._allow_blurhash_fallback.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            #
            
            thumbnail_interaction_box = ClientGUICommon.StaticBox( self, 'interaction' )
            
            self._show_extended_single_file_info_in_status_bar = QW.QCheckBox( thumbnail_interaction_box )
            tt = 'This will show, any time you have a single thumbnail selected, the file info summary you normally see in the top hover window of the media viewer in the main gui status bar. Check the "media viewer hovers" options panel to edit what this summary includes.'
            self._show_extended_single_file_info_in_status_bar.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            self._focus_preview_on_ctrl_click = QW.QCheckBox( thumbnail_interaction_box )
            self._focus_preview_on_ctrl_click_only_static = QW.QCheckBox( thumbnail_interaction_box )
            self._focus_preview_on_shift_click = QW.QCheckBox( thumbnail_interaction_box )
            self._focus_preview_on_shift_click_only_static = QW.QCheckBox( thumbnail_interaction_box )
            
            self._thumbnail_visibility_scroll_percent = ClientGUICommon.BetterSpinBox( thumbnail_interaction_box, min=1, max=99 )
            self._thumbnail_visibility_scroll_percent.setToolTip( ClientGUIFunctions.WrapToolTip( 'Lower numbers will cause fewer scrolls, higher numbers more.' ) )
            
            self._thumbnail_scroll_rate = QW.QLineEdit( thumbnail_interaction_box )
            
            #
            
            thumbnail_misc_box = ClientGUICommon.StaticBox( self, 'media background' )
            
            self._media_background_bmp_path = QP.FilePickerCtrl( thumbnail_misc_box )
            
            #
            
            ( thumbnail_width, thumbnail_height ) = HC.options[ 'thumbnail_dimensions' ]
            
            self._thumbnail_width.setValue( thumbnail_width )
            self._thumbnail_height.setValue( thumbnail_height )
            
            self._thumbnail_border.setValue( self._new_options.GetInteger( 'thumbnail_border' ) )
            self._thumbnail_margin.setValue( self._new_options.GetInteger( 'thumbnail_margin' ) )
            
            self._thumbnail_scale_type.SetValue( self._new_options.GetInteger( 'thumbnail_scale_type' ) )
            self._thumbnail_dpr_percentage.setValue( self._new_options.GetInteger( 'thumbnail_dpr_percent' ) )
            
            self._video_thumbnail_percentage_in.setValue( self._new_options.GetInteger( 'video_thumbnail_percentage_in' ) )
            
            self._allow_blurhash_fallback.setChecked( self._new_options.GetBoolean( 'allow_blurhash_fallback' ) )
            
            self._fade_thumbnails.setChecked( self._new_options.GetBoolean( 'fade_thumbnails' ) )
            
            self._focus_preview_on_ctrl_click.setChecked( self._new_options.GetBoolean( 'focus_preview_on_ctrl_click' ) )
            self._focus_preview_on_ctrl_click_only_static.setChecked( self._new_options.GetBoolean( 'focus_preview_on_ctrl_click_only_static' ) )
            self._focus_preview_on_shift_click.setChecked( self._new_options.GetBoolean( 'focus_preview_on_shift_click' ) )
            self._focus_preview_on_shift_click_only_static.setChecked( self._new_options.GetBoolean( 'focus_preview_on_shift_click_only_static' ) )
            
            self._thumbnail_visibility_scroll_percent.setValue( self._new_options.GetInteger( 'thumbnail_visibility_scroll_percent' ) )
            
            self._thumbnail_scroll_rate.setText( self._new_options.GetString( 'thumbnail_scroll_rate' ) )
            
            media_background_bmp_path = self._new_options.GetNoneableString( 'media_background_bmp_path' )
            
            if media_background_bmp_path is not None:
                
                self._media_background_bmp_path.SetPath( media_background_bmp_path )
                
            
            self._show_extended_single_file_info_in_status_bar.setChecked( self._new_options.GetBoolean( 'show_extended_single_file_info_in_status_bar' ) )
            
            #
            
            rows = []
            
            rows.append( ( 'Thumbnail width: ', self._thumbnail_width ) )
            rows.append( ( 'Thumbnail height: ', self._thumbnail_height ) )
            rows.append( ( 'Thumbnail border: ', self._thumbnail_border ) )
            rows.append( ( 'Thumbnail margin: ', self._thumbnail_margin ) )
            rows.append( ( 'Thumbnail scaling: ', self._thumbnail_scale_type ) )
            rows.append( ( 'Thumbnail UI-scale supersampling %: ', self._thumbnail_dpr_percentage ) )
            rows.append( ( 'Generate video thumbnails this % in: ', self._video_thumbnail_percentage_in ) )
            rows.append( ( 'Fade thumbnails: ', self._fade_thumbnails ) )
            rows.append( ( 'Use blurhash missing thumbnail fallback: ', self._allow_blurhash_fallback ) )
            
            gridbox = ClientGUICommon.WrapInGrid( thumbnail_appearance_box, rows )
            
            thumbnail_appearance_box.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            rows = []
            
            rows.append( ( 'When a single thumbnail is selected, show the media viewer\'s normal top hover file text in the status bar: ', self._show_extended_single_file_info_in_status_bar ) )
            rows.append( ( 'On ctrl-click, focus thumbnails in the preview window: ', self._focus_preview_on_ctrl_click ) )
            rows.append( ( '  Only on files with no duration: ', self._focus_preview_on_ctrl_click_only_static ) )
            rows.append( ( 'On shift-click, focus thumbnails in the preview window: ', self._focus_preview_on_shift_click ) )
            rows.append( ( '  Only on files with no duration: ', self._focus_preview_on_shift_click_only_static ) )
            rows.append( ( 'Do not scroll down on key navigation if thumbnail at least this % visible: ', self._thumbnail_visibility_scroll_percent ) )
            rows.append( ( 'EXPERIMENTAL: Scroll thumbnails at this rate per scroll tick: ', self._thumbnail_scroll_rate ) )
            
            gridbox = ClientGUICommon.WrapInGrid( thumbnail_interaction_box, rows )
            
            thumbnail_interaction_box.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            rows = []
            
            rows.append( ( 'EXPERIMENTAL: Image path for thumbnail panel background image (set blank to clear): ', self._media_background_bmp_path ) )
            
            gridbox = ClientGUICommon.WrapInGrid( thumbnail_misc_box, rows )
            
            thumbnail_misc_box.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, thumbnail_appearance_box, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, thumbnail_interaction_box, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, thumbnail_misc_box, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.addStretch( 0 )
            
            self.setLayout( vbox )
            
            self._UpdatePreviewCheckboxes()
            
        
        def _UpdatePreviewCheckboxes( self ):
            
            self._focus_preview_on_ctrl_click_only_static.setEnabled( self._focus_preview_on_ctrl_click.isChecked() )
            self._focus_preview_on_shift_click_only_static.setEnabled( self._focus_preview_on_shift_click.isChecked() )
            
        
        def UpdateOptions( self ):
            
            new_thumbnail_dimensions = [self._thumbnail_width.value(), self._thumbnail_height.value()]
            
            HC.options[ 'thumbnail_dimensions' ] = new_thumbnail_dimensions
            
            self._new_options.SetInteger( 'thumbnail_border', self._thumbnail_border.value() )
            self._new_options.SetInteger( 'thumbnail_margin', self._thumbnail_margin.value() )
            
            self._new_options.SetInteger( 'thumbnail_scale_type', self._thumbnail_scale_type.GetValue() )
            self._new_options.SetInteger( 'thumbnail_dpr_percent', self._thumbnail_dpr_percentage.value() )
            
            self._new_options.SetInteger( 'video_thumbnail_percentage_in', self._video_thumbnail_percentage_in.value() )
            
            self._new_options.SetBoolean( 'focus_preview_on_ctrl_click', self._focus_preview_on_ctrl_click.isChecked() )
            self._new_options.SetBoolean( 'focus_preview_on_ctrl_click_only_static', self._focus_preview_on_ctrl_click_only_static.isChecked() )
            self._new_options.SetBoolean( 'focus_preview_on_shift_click', self._focus_preview_on_shift_click.isChecked() )
            self._new_options.SetBoolean( 'focus_preview_on_shift_click_only_static', self._focus_preview_on_shift_click_only_static.isChecked() )
            
            self._new_options.SetBoolean( 'allow_blurhash_fallback', self._allow_blurhash_fallback.isChecked() )
            
            self._new_options.SetBoolean( 'fade_thumbnails', self._fade_thumbnails.isChecked() )
            
            self._new_options.SetBoolean( 'show_extended_single_file_info_in_status_bar', self._show_extended_single_file_info_in_status_bar.isChecked() )
            
            try:
                
                thumbnail_scroll_rate = self._thumbnail_scroll_rate.text()
                
                float( thumbnail_scroll_rate )
                
                self._new_options.SetString( 'thumbnail_scroll_rate', thumbnail_scroll_rate )
                
            except:
                
                pass
                
            
            self._new_options.SetInteger( 'thumbnail_visibility_scroll_percent', self._thumbnail_visibility_scroll_percent.value() )
            
            media_background_bmp_path = self._media_background_bmp_path.GetPath()
            
            if media_background_bmp_path == '':
                
                media_background_bmp_path = None
                
            
            self._new_options.SetNoneableString( 'media_background_bmp_path', media_background_bmp_path )
            
        
    
    def SetCurrentOptionsPanel ( self ):
        
        current_panel_name = self._listbook.tabText( self._listbook.GetCurrentPageIndex() )
        
        self._new_options.SetString( 'last_options_window_panel', current_panel_name )
        
    
    def CommitChanges( self ):
        
        for page in self._listbook.GetPages():
            
            page = typing.cast( OptionsPagePanel, page )
            
            page.UpdateOptions()
            
        
        try:
            
            CG.client_controller.WriteSynchronous( 'save_options', HC.options )
            
            CG.client_controller.WriteSynchronous( 'serialisable', self._new_options )
            
            # TODO: move all this, including 'original options' gubbins, to the manageoptions call. this dialog shouldn't care about these signals
            # we do this to convert tuples to lists and so on
            test_new_options = self._new_options.Duplicate()
            
            if test_new_options.GetMediaViewOptions() != self._original_new_options.GetMediaViewOptions():
                
                CG.client_controller.pub( 'clear_image_tile_cache' )
                
            
            res_changed = HC.options[ 'thumbnail_dimensions' ] != self._original_options[ 'thumbnail_dimensions' ]
            type_changed = test_new_options.GetInteger( 'thumbnail_scale_type' ) != self._original_new_options.GetInteger( 'thumbnail_scale_type' )
            dpr_changed = test_new_options.GetInteger( 'thumbnail_dpr_percent' ) != self._original_new_options.GetInteger( 'thumbnail_dpr_percent' )
            
            if res_changed or type_changed or dpr_changed:
                
                CG.client_controller.pub( 'clear_thumbnail_cache' )
                
            
        except Exception as e:
            
            HydrusData.PrintException( e )
            
            ClientGUIDialogsMessage.ShowCritical( self, 'Problem saving options!', str( e ) )
            
        
    

def ManageShortcuts( win: QW.QWidget ):
    
    all_shortcuts = ClientGUIShortcuts.shortcuts_manager().GetShortcutSets()
    
    with ClientGUITopLevelWindowsPanels.DialogEdit( win, 'manage shortcuts' ) as dlg:
        
        panel = ClientGUIScrolledPanels.EditSingleCtrlPanel( dlg )
        
        widget = ShortcutsPanel( dlg, CG.client_controller.new_options, all_shortcuts )
        
        panel.SetControl( widget )
        
        dlg.SetPanel( panel )
        
        if dlg.exec() == QW.QDialog.DialogCode.Accepted:
            
            widget.UpdateOptions()
            
        
    
