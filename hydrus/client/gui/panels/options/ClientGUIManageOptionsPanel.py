import typing

from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIShortcuts
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListBook
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.panels.options import AdvancedPanel
from hydrus.client.gui.panels.options import AudioPanel
from hydrus.client.gui.panels.options import ClientGUIOptionsPanelBase
from hydrus.client.gui.panels.options import ColoursPanel
from hydrus.client.gui.panels.options import CommandPalettePanel
from hydrus.client.gui.panels.options import ConnectionPanel
from hydrus.client.gui.panels.options import DownloadingPanel
from hydrus.client.gui.panels.options import DuplicatesPanel
from hydrus.client.gui.panels.options import ExportingPanel
from hydrus.client.gui.panels.options import ExternalProgramsPanel
from hydrus.client.gui.panels.options import FilesAndTrashPanel
from hydrus.client.gui.panels.options import FileSearchPanel
from hydrus.client.gui.panels.options import FileSortCollectPanel
from hydrus.client.gui.panels.options import FileViewingStatisticsPanel
from hydrus.client.gui.panels.options import GUIPagesPanel
from hydrus.client.gui.panels.options import GUIPanel
from hydrus.client.gui.panels.options import GUISessionsPanel
from hydrus.client.gui.panels.options import ImportingPanel
from hydrus.client.gui.panels.options import MaintenanceAndProcessingPanel
from hydrus.client.gui.panels.options import MediaPlaybackPanel
from hydrus.client.gui.panels.options import MediaViewerHoversPanel
from hydrus.client.gui.panels.options import MediaViewerPanel
from hydrus.client.gui.panels.options import NotesPanel
from hydrus.client.gui.panels.options import PopupPanel
from hydrus.client.gui.panels.options import RatingsPanel
from hydrus.client.gui.panels.options import RegexPanel
from hydrus.client.gui.panels.options import ShortcutsPanel
from hydrus.client.gui.panels.options import SpeedAndMemoryPanel
from hydrus.client.gui.panels.options import StylePanel
from hydrus.client.gui.panels.options import SystemPanel
from hydrus.client.gui.panels.options import SystemTrayPanel
from hydrus.client.gui.panels.options import TagEditingPanel
from hydrus.client.gui.panels.options import TagPresentationPanel
from hydrus.client.gui.panels.options import TagSortPanel
from hydrus.client.gui.panels.options import TagsPanel
from hydrus.client.gui.panels.options import TagSuggestionsPanel
from hydrus.client.gui.panels.options import ThumbnailsPanel

class ManageOptionsPanel( ClientGUIScrolledPanels.ManagePanel ):
    
    def __init__( self, parent ):
        
        super().__init__( parent )
        
        self._original_options = dict( HC.options )
        
        self._new_options = CG.client_controller.new_options
        self._original_new_options = self._new_options.Duplicate()
        
        all_shortcuts = ClientGUIShortcuts.shortcuts_manager().GetShortcutSets()
        
        self._listbook = ClientGUIListBook.ListBook( self, list_chars_width = 28 )
        
        self._listbook.AddPage( 'gui', GUIPanel.GUIPanel( self._listbook ) ) # leave this at the top, to make it default page
        self._listbook.AddPage( 'audio', AudioPanel.AudioPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'command palette', CommandPalettePanel.CommandPalettePanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'colours', ColoursPanel.ColoursPanel( self._listbook ) )
        self._listbook.AddPage( 'connection', ConnectionPanel.ConnectionPanel( self._listbook ) )
        self._listbook.AddPage( 'exporting', ExportingPanel.ExportingPanel( self._listbook ) )
        self._listbook.AddPage( 'external programs', ExternalProgramsPanel.ExternalProgramsPanel( self._listbook ) )
        self._listbook.AddPage( 'files and trash', FilesAndTrashPanel.FilesAndTrashPanel( self._listbook ) )
        self._listbook.AddPage( 'file search', FileSearchPanel.FileSearchPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'file viewing statistics', FileViewingStatisticsPanel.FileViewingStatisticsPanel( self._listbook ) )
        self._listbook.AddPage( 'gui pages', GUIPagesPanel.GUIPagesPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'gui sessions', GUISessionsPanel.GUISessionsPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'maintenance and processing', MaintenanceAndProcessingPanel.MaintenanceAndProcessingPanel( self._listbook ) )
        self._listbook.AddPage( 'media viewer', MediaViewerPanel.MediaViewerPanel( self._listbook ) )
        self._listbook.AddPage( 'media viewer hovers', MediaViewerHoversPanel.MediaViewerHoversPanel( self._listbook ) )
        self._listbook.AddPage( 'media playback', MediaPlaybackPanel.MediaPlaybackPanel( self._listbook ) )
        self._listbook.AddPage( 'speed and memory', SpeedAndMemoryPanel.SpeedAndMemoryPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'system tray', SystemTrayPanel.SystemTrayPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'popup notifications', PopupPanel.PopupPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'regex favourites', RegexPanel.RegexPanel( self._listbook ) )
        self._listbook.AddPage( 'file sort/collect', FileSortCollectPanel.FileSortCollectPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'downloading', DownloadingPanel.DownloadingPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'duplicates', DuplicatesPanel.DuplicatesPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'importing', ImportingPanel.ImportingPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'ratings', RatingsPanel.RatingsPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'shortcuts', ShortcutsPanel.ShortcutsPanel( self._listbook, self._new_options, all_shortcuts ) )
        self._listbook.AddPage( 'style', StylePanel.StylePanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'tag editing', TagEditingPanel.TagEditingPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'tag presentation', TagPresentationPanel.TagPresentationPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'tag sort', TagSortPanel.TagSortPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'tag suggestions', TagSuggestionsPanel.TagSuggestionsPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'tag autocomplete tabs', TagsPanel.TagsPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'thumbnails', ThumbnailsPanel.ThumbnailsPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'system', SystemPanel.SystemPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'notes', NotesPanel.NotesPanel( self._listbook, self._new_options ) )
        
        self._listbook.SortList()
        
        self._listbook.AddPage( 'advanced', AdvancedPanel.AdvancedPanel( self._listbook, self._new_options ) )
        
        if self._new_options.GetBoolean( 'remember_options_window_panel' ):
            
            self._listbook.currentChanged.connect( self.SetCurrentOptionsPanel )
            
            self._listbook.SelectName( self._new_options.GetString( 'last_options_window_panel' ) )
            
        
        #
        self._options_search = QW.QLineEdit( self )
        self._options_search.setPlaceholderText( 'Search options... (Experimental!)' )
        self._options_search.setSizePolicy( QW.QSizePolicy.Policy.Expanding, QW.QSizePolicy.Policy.Fixed )
        self._options_search.setFixedHeight( self._options_search.sizeHint().height() )
        
        completer_strings = []
        self._completer_map = {}
        
        for index, page in enumerate( self._listbook.GetPages() ):
            
            page_name = self._listbook.tabText( index )
            
            for widget in page.findChildren( QW.QWidget ):
                
                text = ""
                
                if isinstance( widget, QW.QLabel ):
                    text = widget.text()
                elif isinstance( widget, QW.QCheckBox ):
                    text = widget.text()
                elif isinstance( widget, QW.QGroupBox ):
                    text = widget.title()
                elif isinstance( widget, QW.QComboBox ):
                    text = widget.currentText()
                
                if text:
                    key = f"{text} ({page_name})"
                    completer_strings.append( key )
                    self._completer_map[key] = ( page_name, widget )
                    
                
            
        
        from qtpy import QtCore as QC
        
        self._completer = QW.QCompleter( completer_strings, self._options_search )
        self._completer.setCaseSensitivity( QC.Qt.CaseSensitivity.CaseInsensitive )
        self._completer.setFilterMode( QC.Qt.MatchFlag.MatchContains )
        self._completer.setCompletionMode( QW.QCompleter.CompletionMode.PopupCompletion )
        self._completer.setMaxVisibleItems( 10 )
        self._options_search.setCompleter( self._completer )
        
        def on_completer_activated( text: str ):
            
            if text in self._completer_map:
                
                page_name, widget = self._completer_map[text]
                self._listbook.SelectName( page_name )
                
                widget.setStyleSheet( "background-color: rgba(255, 255, 0, 128);" )
                widget.repaint()
                
            
            QC.QTimer.singleShot( 0, lambda: self._options_search.setText('') )
            
        
        self._completer.activated.connect( on_completer_activated )
        
        #
        
        vbox = QP.VBoxLayout()
        
        if self._new_options.GetBoolean( 'options_search_bar_top_of_window' ):
            
            QP.AddToLayout( vbox, self._options_search, CC.FLAGS_EXPAND_BOTH_WAYS )
            QP.AddToLayout( vbox, self._listbook, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            
        else:
            
            QP.AddToLayout( vbox, self._listbook, CC.FLAGS_EXPAND_BOTH_WAYS )
            QP.AddToLayout( vbox, self._options_search, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            
        
        self.widget().setLayout( vbox )
        
        self._options_search.setFocus()
        

    def SetCurrentOptionsPanel ( self ):
        
        current_panel_name = self._listbook.tabText( self._listbook.GetCurrentPageIndex() )
        
        self._new_options.SetString( 'last_options_window_panel', current_panel_name )
        
    
    def CommitChanges( self ):
        
        for page in self._listbook.GetPages():
            
            page = typing.cast( ClientGUIOptionsPanelBase.OptionsPagePanel, page )
            
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
        
        widget = ShortcutsPanel.ShortcutsPanel( dlg, CG.client_controller.new_options, all_shortcuts )
        
        panel.SetControl( widget )
        
        dlg.SetPanel( panel )
        
        if dlg.exec() == QW.QDialog.DialogCode.Accepted:
            
            widget.UpdateOptions()
            
        
    
