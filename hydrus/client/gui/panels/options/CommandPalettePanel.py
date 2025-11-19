from qtpy import QtWidgets as QW

from hydrus.client import ClientConstants as CC
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.panels.options import ClientGUIOptionsPanelBase
from hydrus.client.gui.widgets import ClientGUICommon

class CommandPalettePanel( ClientGUIOptionsPanelBase.OptionsPagePanel ):
    
    def __init__( self, parent, new_options ):
        
        self._new_options = new_options
        
        super().__init__( parent )
        
        self._command_palette_panel = ClientGUICommon.StaticBox( self, 'command palette' )
        
        self._command_palette_show_page_of_pages = QW.QCheckBox( self._command_palette_panel )
        self._command_palette_show_page_of_pages.setToolTip( ClientGUIFunctions.WrapToolTip( 'Show "page of pages" as selectable page results. This will focus the page, and whatever sub-page it previously focused (including none, if it has no child pages).' ) )
        
        self._command_palette_initially_show_all_pages = QW.QCheckBox( self._command_palette_panel )
        self._command_palette_initially_show_all_pages.setToolTip( ClientGUIFunctions.WrapToolTip( 'If unchecked, the command palette will not load any results until you start typing. This can help with performance with larger sessions.' ) )
        
        self._command_palette_limit_page_results = ClientGUICommon.BetterSpinBox( self._command_palette_panel, min=0, max=1000 )
        self._command_palette_limit_page_results.setToolTip( ClientGUIFunctions.WrapToolTip( 'The maximum number of page results to show before requiring typing to filter them down. Set to 0 to always show all results.' ) )
        
        self._command_palette_initially_show_history = QW.QCheckBox( self._command_palette_panel )
        self._command_palette_initially_show_history.setToolTip( ClientGUIFunctions.WrapToolTip( 'By default, the command palette shows all your pages when opened. If you enable this, it will show your page navigation history first, which is often more useful for quick switching.' ) )
        
        self._command_palette_limit_history_results = ClientGUICommon.BetterSpinBox( self._command_palette_panel, min=0, max=1000 )
        self._command_palette_limit_history_results.setToolTip( ClientGUIFunctions.WrapToolTip( 'The maximum number of page history results to show before requiring typing to filter them down. Set to 0 to always show all results.' ) )
        
        self._command_palette_show_main_menu = QW.QCheckBox( self._command_palette_panel )
        self._command_palette_show_main_menu.setToolTip( ClientGUIFunctions.WrapToolTip(  'Show the main gui window\'s menubar actions.' ) )
        
        self._command_palette_show_media_menu = QW.QCheckBox( self._command_palette_panel )
        self._command_palette_show_media_menu.setToolTip( ClientGUIFunctions.WrapToolTip( 'Show the actions for the thumbnail menu on the current media page. Be careful with this, it basically just shows everything with slightly ugly labels..' ) )
        
        #
        
        self._command_palette_show_page_of_pages.setChecked( self._new_options.GetBoolean( 'command_palette_show_page_of_pages' ) )
        self._command_palette_initially_show_all_pages.setChecked( self._new_options.GetBoolean( 'command_palette_initially_show_all_pages' ) )
        self._command_palette_limit_page_results.setValue( self._new_options.GetInteger( 'command_palette_limit_page_results' ) )
        self._command_palette_initially_show_history.setChecked( self._new_options.GetBoolean( 'command_palette_initially_show_history' ) )
        self._command_palette_limit_history_results.setValue( self._new_options.GetInteger( 'command_palette_limit_history_results' ) )
        self._command_palette_show_main_menu.setChecked( self._new_options.GetBoolean( 'command_palette_show_main_menu' ) )
        self._command_palette_show_media_menu.setChecked( self._new_options.GetBoolean( 'command_palette_show_media_menu' ) )
        
        #
        
        rows = []
        
        rows.append( ( 'Show "page of pages" results: ', self._command_palette_show_page_of_pages ) )
        rows.append( ( 'Initially show all page results (otherwise wait for typing): ', self._command_palette_initially_show_all_pages ) )
        rows.append( ( 'Limit page results to: ', self._command_palette_limit_page_results ) )
        rows.append( ( 'Initially show page history results (otherwise wait for typing):', self._command_palette_initially_show_history ) )
        rows.append( ( 'Limit page history results to: ', self._command_palette_limit_history_results ) )
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
        self._new_options.SetBoolean( 'command_palette_initially_show_all_pages', self._command_palette_initially_show_all_pages.isChecked() )
        self._new_options.SetInteger( 'command_palette_limit_page_results', self._command_palette_limit_page_results.value() )
        self._new_options.SetBoolean( 'command_palette_initially_show_history', self._command_palette_initially_show_history.isChecked() )
        self._new_options.SetInteger( 'command_palette_limit_history_results', self._command_palette_limit_history_results.value() )
        self._new_options.SetBoolean( 'command_palette_show_main_menu', self._command_palette_show_main_menu.isChecked() )
        self._new_options.SetBoolean( 'command_palette_show_media_menu', self._command_palette_show_media_menu.isChecked() )
        
    
