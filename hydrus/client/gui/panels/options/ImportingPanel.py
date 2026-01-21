from qtpy import QtWidgets as QW

from hydrus.client import ClientConstants as CC
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.importing import ClientGUIImportOptions
from hydrus.client.gui.panels.options import ClientGUIOptionsPanelBase
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.importing.options import FileImportOptionsLegacy

class ImportingPanel( ClientGUIOptionsPanelBase.OptionsPagePanel ):
    
    def __init__( self, parent, new_options ):
        
        super().__init__( parent )
        
        self._new_options = new_options
        
        #
        
        drag_and_drop = ClientGUICommon.StaticBox( self, 'drag and drop' )
        
        self._show_destination_page_when_dnd_url = QW.QCheckBox( drag_and_drop )
        self._show_destination_page_when_dnd_url.setToolTip( ClientGUIFunctions.WrapToolTip( 'When dropping a URL on the program, should we switch to the destination page?' ) )
        
        #
        
        default_fios = ClientGUICommon.StaticBox( self, 'default file import options' )
        
        quiet_file_import_options = self._new_options.GetDefaultFileImportOptions( FileImportOptionsLegacy.IMPORT_TYPE_QUIET )
        
        show_downloader_options = True
        allow_default_selection = False
        
        self._quiet_fios = ClientGUIImportOptions.ImportOptionsButton( self, show_downloader_options, allow_default_selection )
        
        self._quiet_fios.SetFileImportOptions( quiet_file_import_options )
        
        loud_file_import_options = self._new_options.GetDefaultFileImportOptions( FileImportOptionsLegacy.IMPORT_TYPE_LOUD )
        
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
        
        self._new_options.SetDefaultFileImportOptions( FileImportOptionsLegacy.IMPORT_TYPE_QUIET, self._quiet_fios.GetFileImportOptions() )
        self._new_options.SetDefaultFileImportOptions( FileImportOptionsLegacy.IMPORT_TYPE_LOUD, self._loud_fios.GetFileImportOptions() )
        
    
