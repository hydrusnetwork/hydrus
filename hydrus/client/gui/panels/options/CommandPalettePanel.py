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
        
    
