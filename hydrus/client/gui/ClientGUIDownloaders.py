import os
import typing

from qtpy import QtWidgets as QW
from qtpy import QtGui as QG

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusSerialisable

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientDefaults
from hydrus.client import ClientPaths
from hydrus.client import ClientStrings
from hydrus.client.gui import ClientGUIDialogs
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIScrolledPanels
from hydrus.client.gui import ClientGUIStringControls
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListBoxes
from hydrus.client.gui.lists import ClientGUIListConstants as CGLC
from hydrus.client.gui.lists import ClientGUIListCtrl
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.gui.widgets import ClientGUIMenuButton
from hydrus.client.networking import ClientNetworkingDomain
from hydrus.client.networking import ClientNetworkingGUG
from hydrus.client.networking import ClientNetworkingURLClass

class EditDownloaderDisplayPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, network_engine, gugs, gug_keys_to_display, url_classes, url_class_keys_to_display, show_unmatched_urls_in_media_viewer ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._gugs = gugs
        self._gug_keys_to_gugs = { gug.GetGUGKey() : gug for gug in self._gugs }
        
        self._url_classes = url_classes
        self._url_class_keys_to_url_classes = { url_class.GetClassKey() : url_class for url_class in self._url_classes }
        
        self._network_engine = network_engine
        
        #
        
        self._notebook = QW.QTabWidget( self )
        
        #
        
        self._gug_display_list_ctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self._notebook )
        
        self._gug_display_list_ctrl = ClientGUIListCtrl.BetterListCtrl( self._gug_display_list_ctrl_panel, CGLC.COLUMN_LIST_GUG_KEYS_TO_DISPLAY.ID, 15, self._ConvertGUGDisplayDataToListCtrlTuples, activation_callback = self._EditGUGDisplay )
        
        self._gug_display_list_ctrl_panel.SetListCtrl( self._gug_display_list_ctrl )
        
        self._gug_display_list_ctrl_panel.AddButton( 'edit', self._EditGUGDisplay, enabled_only_on_selection = True )
        
        #
        
        media_viewer_urls_panel = QW.QWidget( self._notebook )
        
        self._url_display_list_ctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( media_viewer_urls_panel )
        
        self._url_display_list_ctrl = ClientGUIListCtrl.BetterListCtrl( self._url_display_list_ctrl_panel, CGLC.COLUMN_LIST_URL_CLASS_KEYS_TO_DISPLAY.ID, 15, self._ConvertURLDisplayDataToListCtrlTuples, activation_callback = self._EditURLDisplay )
        
        self._url_display_list_ctrl_panel.SetListCtrl( self._url_display_list_ctrl )
        
        self._url_display_list_ctrl_panel.AddButton( 'edit', self._EditURLDisplay, enabled_only_on_selection = True )
        
        self._show_unmatched_urls_in_media_viewer = QW.QCheckBox( media_viewer_urls_panel )
        
        #
        
        listctrl_data = []
        
        for ( gug_key, gug ) in list(self._gug_keys_to_gugs.items()):
            
            display = gug_key in gug_keys_to_display
            
            listctrl_data.append( ( gug_key, display ) )
            
        
        self._gug_display_list_ctrl.AddDatas( listctrl_data )
        
        self._gug_display_list_ctrl.Sort()
        
        #
        
        listctrl_data = []
        
        for ( url_class_key, url_class ) in self._url_class_keys_to_url_classes.items():
            
            display = url_class_key in url_class_keys_to_display
            
            listctrl_data.append( ( url_class_key, display ) )
            
        
        self._url_display_list_ctrl.AddDatas( listctrl_data )
        
        self._url_display_list_ctrl.Sort()
        
        self._show_unmatched_urls_in_media_viewer.setChecked( show_unmatched_urls_in_media_viewer )
        
        #
        
        vbox = QP.VBoxLayout()
        
        rows = []
        
        rows.append( ( 'show urls that do not have a matching url class?: ', self._show_unmatched_urls_in_media_viewer ) )
        
        gridbox = ClientGUICommon.WrapInGrid( media_viewer_urls_panel, rows )
        
        QP.AddToLayout( vbox, self._url_display_list_ctrl, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        media_viewer_urls_panel.setLayout( vbox )
        
        #
        
        self._notebook.addTab( self._gug_display_list_ctrl_panel, 'downloaders selector' )
        self._notebook.setCurrentWidget( self._gug_display_list_ctrl_panel )
        self._notebook.addTab( media_viewer_urls_panel, 'media viewer urls' )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
    def _ConvertGUGDisplayDataToListCtrlTuples( self, data ):
        
        ( gug_key, display ) = data
        
        gug = self._gug_keys_to_gugs[ gug_key ]
        
        name = gug.GetName()
        
        pretty_name = name
        
        if display:
            
            pretty_display = 'yes'
            
        else:
            
            pretty_display = 'no'
            
        
        display_tuple = ( pretty_name, pretty_display )
        sort_tuple = ( name, display )
        
        return ( display_tuple, sort_tuple )
        
    
    def _ConvertURLDisplayDataToListCtrlTuples( self, data ):
        
        ( url_class_key, display ) = data
        
        url_class = self._url_class_keys_to_url_classes[ url_class_key ]
        
        url_class_name = url_class.GetName()
        url_type = url_class.GetURLType()
        
        pretty_name = url_class_name
        pretty_url_type = HC.url_type_string_lookup[ url_type ]
        
        if display:
            
            pretty_display = 'yes'
            
        else:
            
            pretty_display = 'no'
            
        
        display_tuple = ( pretty_name, pretty_url_type, pretty_display )
        sort_tuple = ( url_class_name, pretty_url_type, display )
        
        return ( display_tuple, sort_tuple )
        
    
    def _EditGUGDisplay( self ):
        
        for data in self._gug_display_list_ctrl.GetData( only_selected = True ):
            
            ( gug_key, display ) = data
            
            name = self._gug_keys_to_gugs[ gug_key ].GetName()
            
            message = 'Show "{}" in the main selector list?'.format( name )
            
            result, closed_by_user = ClientGUIDialogsQuick.GetYesNo( self, message, title = 'Show in the first list?', check_for_cancelled = True )
            
            if not closed_by_user:
                
                display = result == QW.QDialog.Accepted
                
                self._gug_display_list_ctrl.DeleteDatas( ( data, ) )
                
                new_data = ( gug_key, display )
                
                self._gug_display_list_ctrl.AddDatas( ( new_data, ) )
                
            else:
                
                break
                
            
        
        self._gug_display_list_ctrl.Sort()
        
    
    def _EditURLDisplay( self ):
        
        for data in self._url_display_list_ctrl.GetData( only_selected = True ):
            
            ( url_class_key, display ) = data
            
            url_class_name = self._url_class_keys_to_url_classes[ url_class_key ].GetName()
            
            message = 'Show ' + url_class_name + ' in the media viewer?'
            
            result, closed_by_user = ClientGUIDialogsQuick.GetYesNo( self, message, title = 'Show in the media viewer?', check_for_cancelled = True )
            
            if not closed_by_user:
                
                display = result == QW.QDialog.Accepted
                
                self._url_display_list_ctrl.DeleteDatas( ( data, ) )
                
                new_data = ( url_class_key, display )
                
                self._url_display_list_ctrl.AddDatas( ( new_data, ) )
                
            else:
                
                break
                
            
        
        self._url_display_list_ctrl.Sort()
        
    
    def GetValue( self ):
        
        gug_keys_to_display = { gug_key for ( gug_key, display ) in self._gug_display_list_ctrl.GetData() if display }
        url_class_keys_to_display = { url_class_key for ( url_class_key, display ) in self._url_display_list_ctrl.GetData() if display }
        
        show_unmatched_urls_in_media_viewer = self._show_unmatched_urls_in_media_viewer.isChecked()
        
        return ( gug_keys_to_display, url_class_keys_to_display, show_unmatched_urls_in_media_viewer )
        
    
class EditGUGPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, gug: ClientNetworkingGUG.GalleryURLGenerator ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._original_gug = gug
        
        self._name = QW.QLineEdit( self )
        
        self._url_template = QW.QLineEdit( self )
        
        min_width = ClientGUIFunctions.ConvertTextToPixelWidth( self._url_template, 74 )
        
        QP.SetMinClientSize( self._url_template, (min_width,-1) )
        
        self._replacement_phrase = QW.QLineEdit( self )
        self._search_terms_separator = QW.QLineEdit( self )
        self._initial_search_text = QW.QLineEdit( self )
        self._example_search_text = QW.QLineEdit( self )
        
        self._example_url = QW.QLineEdit( self )
        self._example_url.setReadOnly( True )
        self._matched_url_class = QW.QLineEdit( self )
        self._matched_url_class.setReadOnly( True )
        
        #
        
        name = gug.GetName()
        
        ( url_template, replacement_phrase, search_terms_separator, example_search_text ) = gug.GetURLTemplateVariables()
        
        initial_search_text = gug.GetInitialSearchText()
        
        self._name.setText( name )
        self._url_template.setText( url_template )
        self._replacement_phrase.setText( replacement_phrase )
        self._search_terms_separator.setText( search_terms_separator )
        self._initial_search_text.setText( initial_search_text )
        self._example_search_text.setText( example_search_text )
        
        self._UpdateExampleURL()
        
        #
        
        rows = []
        
        rows.append( ( 'name: ', self._name ) )
        rows.append( ( 'url template: ', self._url_template) )
        rows.append( ( 'replacement phrase: ', self._replacement_phrase ) )
        rows.append( ( 'search terms separator: ', self._search_terms_separator ) )
        rows.append( ( 'initial search text (to prompt user): ', self._initial_search_text ) )
        rows.append( ( 'example search text: ', self._example_search_text ) )
        rows.append( ( 'example url: ', self._example_url ) )
        rows.append( ( 'matches as a: ', self._matched_url_class ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self.widget().setLayout( vbox )
        
        #
        
        self._url_template.textChanged.connect( self._UpdateExampleURL )
        self._replacement_phrase.textChanged.connect( self._UpdateExampleURL )
        self._search_terms_separator.textChanged.connect( self._UpdateExampleURL )
        self._example_search_text.textChanged.connect( self._UpdateExampleURL )
        
    
    def _GetValue( self ):
        
        gug_key = self._original_gug.GetGUGKey()
        name = self._name.text()
        url_template = self._url_template.text()
        replacement_phrase = self._replacement_phrase.text()
        search_terms_separator = self._search_terms_separator.text()
        initial_search_text = self._initial_search_text.text()
        example_search_text = self._example_search_text.text()
        
        gug = ClientNetworkingGUG.GalleryURLGenerator( name, gug_key = gug_key, url_template = url_template, replacement_phrase = replacement_phrase, search_terms_separator = search_terms_separator, initial_search_text = initial_search_text, example_search_text = example_search_text )
        
        return gug
        
    
    def _UpdateExampleURL( self ):
        
        gug = self._GetValue()
        
        try:
            
            example_url = gug.GetExampleURL()
            
            example_url = HG.client_controller.network_engine.domain_manager.NormaliseURL( example_url )
            
            self._example_url.setText( example_url )
            
        except ( HydrusExceptions.GUGException, HydrusExceptions.URLClassException ) as e:
            
            reason = str( e )
            
            self._example_url.setText( 'Could not generate - ' + reason )
            
            example_url = None
            
        
        if example_url is None:
            
            self._matched_url_class.clear()
            
        else:
            
            try:
                
                url_class = HG.client_controller.network_engine.domain_manager.GetURLClass( example_url )
                
                if url_class is None:
                    
                    url_class_text = 'Did not match a known url class.'
                    
                else:
                    
                    url_class_text = 'Matched ' + url_class.GetName() + ' url class.'
                    
                
            except HydrusExceptions.URLClassException:
                
                url_class_text = 'That did not look like a URL!'
                
            
            self._matched_url_class.setText( url_class_text )
            
        
    
    def GetValue( self ) -> ClientNetworkingGUG.GalleryURLGenerator:
        
        gug = self._GetValue()
        
        try:
            
            gug.GetExampleURL()
            
        except HydrusExceptions.GUGException:
            
            raise HydrusExceptions.VetoException( 'Please ensure your generator can make an example url!' )
            
        
        return gug
        
    
class EditNGUGPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, ngug: ClientNetworkingGUG.NestedGalleryURLGenerator, available_gugs: typing.Iterable[ ClientNetworkingGUG.GalleryURLGenerator ] ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._original_ngug = ngug
        self._available_gugs = list( available_gugs )
        
        self._available_gugs.sort( key = lambda g: g.GetName() )
        
        self._name = QW.QLineEdit( self )
        
        self._initial_search_text = QW.QLineEdit( self )
        
        self._gug_list_ctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        self._gug_list_ctrl = ClientGUIListCtrl.BetterListCtrl( self._gug_list_ctrl_panel, CGLC.COLUMN_LIST_NGUG_GUGS.ID, 30, self._ConvertGUGDataToListCtrlTuples, use_simple_delete = True )
        
        self._gug_list_ctrl_panel.SetListCtrl( self._gug_list_ctrl )
        
        self._add_button = ClientGUICommon.BetterButton( self._gug_list_ctrl_panel, 'add', self._AddGUGButtonClick )
        
        self._gug_list_ctrl_panel.AddWindow( self._add_button )
        self._gug_list_ctrl_panel.AddDeleteButton()
        
        #
        
        name = ngug.GetName()
        
        initial_search_text = ngug.GetInitialSearchText()
        
        self._name.setText( name )
        self._initial_search_text.setText( initial_search_text )
        
        gug_keys_and_names = ngug.GetGUGKeysAndNames()
        
        self._gug_list_ctrl.AddDatas( gug_keys_and_names )
        
        self._gug_list_ctrl.Sort()
        
        #
        
        rows = []
        
        rows.append( ( 'name: ', self._name ) )
        rows.append( ( 'initial search text (to prompt user): ', self._initial_search_text ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, self._gug_list_ctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
    def _AddGUG( self, gug ):
        
        gug_key_and_name = gug.GetGUGKeyAndName()
        
        self._gug_list_ctrl.AddDatas( ( gug_key_and_name, ) )
        
    
    def _AddGUGButtonClick( self ):
        
        existing_gug_keys = { gug_key for ( gug_key, gug_name ) in self._gug_list_ctrl.GetData() }
        existing_gug_names = { gug_name for ( gug_key, gug_name ) in self._gug_list_ctrl.GetData() }
        
        choice_tuples = [ ( gug.GetName(), gug, False ) for gug in self._available_gugs if gug.GetName() not in existing_gug_names and gug.GetGUGKey() not in existing_gug_keys ]
        
        if len( choice_tuples ) == 0:
            
            QW.QMessageBox.critical( self, 'Error', 'No remaining gugs available!' )
            
            return
            
        
        try:
            
            chosen_gugs = ClientGUIDialogsQuick.SelectMultipleFromList( self, 'choose gugs', choice_tuples )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        for gug in chosen_gugs:
            
            self._AddGUG( gug )
            
        
    
    def _ConvertGUGDataToListCtrlTuples( self, gug_key_and_name ):
        
        ( gug_key, gug_name ) = gug_key_and_name
        
        name = gug_name
        pretty_name = name
        
        available = gug_key in ( gug.GetGUGKey() for gug in self._available_gugs ) or gug_name in ( gug.GetName() for gug in self._available_gugs )
        
        if available:
            
            pretty_available = 'yes'
            
        else:
            
            pretty_available = 'no'
            
        
        display_tuple = ( pretty_name, pretty_available )
        sort_tuple = ( name, available )
        
        return ( display_tuple, sort_tuple )
        
    
    def GetValue( self ) -> ClientNetworkingGUG.NestedGalleryURLGenerator:
        
        gug_key = self._original_ngug.GetGUGKey()
        name = self._name.text()
        initial_search_text = self._initial_search_text.text()
        
        gug_keys_and_names = self._gug_list_ctrl.GetData()
        
        ngug = ClientNetworkingGUG.NestedGalleryURLGenerator( name, gug_key = gug_key, initial_search_text = initial_search_text, gug_keys_and_names = gug_keys_and_names )
        
        ngug.RepairGUGs( self._available_gugs )
        
        return ngug
        
    
class EditGUGsPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, gugs ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        menu_items = []
        
        call = HydrusData.Call( ClientPaths.LaunchPathInWebBrowser, os.path.join( HC.HELP_DIR, 'downloader_gugs.html' ) )
        
        menu_items.append( ( 'normal', 'open the gugs help', 'Open the help page for gugs in your web browser.', call ) )
        
        help_button = ClientGUIMenuButton.MenuBitmapButton( self, CC.global_pixmaps().help, menu_items )
        
        help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help for this panel -->', object_name = 'HydrusIndeterminate' )
        
        #
        
        self._notebook = QW.QTabWidget( self )
        
        #
        
        self._gug_list_ctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self._notebook )
        
        self._gug_list_ctrl = ClientGUIListCtrl.BetterListCtrl( self._gug_list_ctrl_panel, CGLC.COLUMN_LIST_GUGS.ID, 30, self._ConvertGUGToListCtrlTuples, delete_key_callback = self._DeleteGUG, activation_callback = self._EditGUG )
        
        self._gug_list_ctrl_panel.SetListCtrl( self._gug_list_ctrl )
        
        self._gug_list_ctrl_panel.AddButton( 'add', self._AddNewGUG )
        self._gug_list_ctrl_panel.AddButton( 'edit', self._EditGUG, enabled_only_on_selection = True )
        self._gug_list_ctrl_panel.AddDeleteButton()
        self._gug_list_ctrl_panel.AddSeparator()
        self._gug_list_ctrl_panel.AddImportExportButtons( ( ClientNetworkingGUG.GalleryURLGenerator, ), self._AddGUG )
        self._gug_list_ctrl_panel.AddSeparator()
        self._gug_list_ctrl_panel.AddDefaultsButton( ClientDefaults.GetDefaultSingleGUGs, self._AddGUG )
        
        #
        
        self._ngug_list_ctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self._notebook )
        
        self._ngug_list_ctrl = ClientGUIListCtrl.BetterListCtrl( self._ngug_list_ctrl_panel, CGLC.COLUMN_LIST_NGUGS.ID, 20, self._ConvertNGUGToListCtrlTuples, use_simple_delete = True, activation_callback = self._EditNGUG )
        
        self._ngug_list_ctrl_panel.SetListCtrl( self._ngug_list_ctrl )
        
        self._ngug_list_ctrl_panel.AddButton( 'add', self._AddNewNGUG )
        self._ngug_list_ctrl_panel.AddButton( 'edit', self._EditNGUG, enabled_only_on_selection = True )
        self._ngug_list_ctrl_panel.AddDeleteButton()
        self._ngug_list_ctrl_panel.AddSeparator()
        self._ngug_list_ctrl_panel.AddImportExportButtons( ( ClientNetworkingGUG.NestedGalleryURLGenerator, ), self._AddNGUG )
        self._ngug_list_ctrl_panel.AddSeparator()
        self._ngug_list_ctrl_panel.AddDefaultsButton( ClientDefaults.GetDefaultNGUGs, self._AddNGUG )
        
        #
        
        single_gugs = [ gug for gug in gugs if isinstance( gug, ClientNetworkingGUG.GalleryURLGenerator ) ]
        
        self._gug_list_ctrl.AddDatas( single_gugs )
        
        self._gug_list_ctrl.Sort()
        
        ngugs = [ gug for gug in gugs if isinstance( gug, ClientNetworkingGUG.NestedGalleryURLGenerator ) ]
        
        self._ngug_list_ctrl.AddDatas( ngugs )
        
        self._ngug_list_ctrl.Sort()
        
        #
        
        self._notebook.addTab( self._gug_list_ctrl_panel, 'gallery url generators' )
        self._notebook.setCurrentWidget( self._gug_list_ctrl_panel )
        self._notebook.addTab( self._ngug_list_ctrl_panel, 'nested gallery url generators' )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, help_hbox, CC.FLAGS_ON_RIGHT )
        QP.AddToLayout( vbox, self._notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
    def _AddNewGUG( self ):
        
        gug = ClientNetworkingGUG.GalleryURLGenerator( 'new gallery url generator' )
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit gallery url generator' ) as dlg:
            
            panel = EditGUGPanel( dlg, gug )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                gug = panel.GetValue()
                
                self._AddGUG( gug )
                
                self._gug_list_ctrl.Sort()
                
            
        
    
    def _AddNewNGUG( self ):
        
        ngug = ClientNetworkingGUG.NestedGalleryURLGenerator( 'new nested gallery url generator' )
        
        available_gugs = self._gug_list_ctrl.GetData()
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit nested gallery url generator' ) as dlg:
            
            panel = EditNGUGPanel( dlg, ngug, available_gugs )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                ngug = panel.GetValue()
                
                self._AddNGUG( ngug )
                
                self._ngug_list_ctrl.Sort()
                
            
        
    
    def _AddGUG( self, gug ):
        
        HydrusSerialisable.SetNonDupeName( gug, self._GetExistingNames() )
        
        gug.RegenerateGUGKey()
        
        self._gug_list_ctrl.AddDatas( ( gug, ) )
        
    
    def _AddNGUG( self, ngug ):
        
        HydrusSerialisable.SetNonDupeName( ngug, self._GetExistingNames() )
        
        ngug.RegenerateGUGKey()
        
        self._ngug_list_ctrl.AddDatas( ( ngug, ) )
        
    
    def _ConvertGUGToListCtrlTuples( self, gug ):
        
        name = gug.GetName()
        example_url = gug.GetExampleURL()
        
        try:
            
            example_url = HG.client_controller.network_engine.domain_manager.NormaliseURL( example_url )
            
            url_class = HG.client_controller.network_engine.domain_manager.GetURLClass( example_url )
            
        except:
            
            example_url = 'unable to parse example url'
            url_class = None
            
        
        if url_class is None:
            
            gallery_url_class = False
            pretty_gallery_url_class = ''
            
        else:
            
            gallery_url_class = True
            pretty_gallery_url_class = url_class.GetName()
            
        
        pretty_name = name
        pretty_example_url = example_url
        
        display_tuple = ( pretty_name, pretty_example_url, pretty_gallery_url_class )
        sort_tuple = ( name, example_url, gallery_url_class )
        
        return ( display_tuple, sort_tuple )
        
    
    def _ConvertNGUGToListCtrlTuples( self, ngug ):
        
        existing_names = { gug.GetName() for gug in self._gug_list_ctrl.GetData() }
        
        name = ngug.GetName()
        gugs = ngug.GetGUGNames()
        missing = len( set( gugs ).difference( existing_names ) ) > 0
        
        pretty_name = name
        pretty_gugs = ', '.join( gugs )
        
        if missing:
            
            pretty_missing = 'yes'
            
        else:
            
            pretty_missing = ''
            
        
        sort_gugs = len( gugs )
        
        display_tuple = ( pretty_name, pretty_gugs, pretty_missing )
        sort_tuple = ( name, sort_gugs, missing )
        
        return ( display_tuple, sort_tuple )
        
    
    def _DeleteGUG( self ):
        
        ngugs = self._ngug_list_ctrl.GetData()
        
        deletees = self._gug_list_ctrl.GetData( only_selected = True )
        
        result = ClientGUIDialogsQuick.GetYesNo( self, 'Remove all selected?' )
        
        if result == QW.QDialog.Accepted:
            
            for deletee in deletees:
                
                deletee_ngug_key = deletee.GetGUGKey()
                
                affected_ngug_names = []
                
                for ngug in ngugs:
                    
                    if deletee_ngug_key in ngug.GetGUGKeys():
                        
                        affected_ngug_names.append( ngug.GetName() )
                        
                    
                
                if len( affected_ngug_names ) > 0:
                    
                    affected_ngug_names.sort()
                    
                    message = 'The GUG "' + deletee.GetName() + '" is in the NGUGs:'
                    message += os.linesep * 2
                    message += os.linesep.join( affected_ngug_names )
                    message += os.linesep * 2
                    message += 'Deleting this GUG will ultimately remove it from those NGUGs--are you sure that is ok?'
                    
                    result = ClientGUIDialogsQuick.GetYesNo( self, message )
                    
                    if result != QW.QDialog.Accepted:
                        
                        break
                        
                    
                
                self._gug_list_ctrl.DeleteDatas( ( deletee, ) )
                
            
        
    
    def _EditGUG( self ):
        
        for gug in self._gug_list_ctrl.GetData( only_selected = True ):
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit gallery url generator' ) as dlg:
                
                panel = EditGUGPanel( dlg, gug )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    self._gug_list_ctrl.DeleteDatas( ( gug, ) )
                    
                    gug = panel.GetValue()
                    
                    HydrusSerialisable.SetNonDupeName( gug, self._GetExistingNames() )
                    
                    self._gug_list_ctrl.AddDatas( ( gug, ) )
                    
                else:
                    
                    break
                    
                
            
        
        self._gug_list_ctrl.Sort()
        
    
    def _EditNGUG( self ):
        
        available_gugs = self._gug_list_ctrl.GetData()
        
        for ngug in self._ngug_list_ctrl.GetData( only_selected = True ):
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit nested gallery url generator' ) as dlg:
                
                panel = EditNGUGPanel( dlg, ngug, available_gugs )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    self._ngug_list_ctrl.DeleteDatas( ( ngug, ) )
                    
                    ngug = panel.GetValue()
                    
                    HydrusSerialisable.SetNonDupeName( ngug, self._GetExistingNames() )
                    
                    self._ngug_list_ctrl.AddDatas( ( ngug, ) )
                    
                else:
                    
                    break
                    
                
            
        
        self._ngug_list_ctrl.Sort()
        
    
    def _GetExistingNames( self ):
        
        gugs = self._gug_list_ctrl.GetData()
        ngugs = self._ngug_list_ctrl.GetData()
        
        names = { gug.GetName() for gug in gugs }
        names.update( ( ngug.GetName() for ngug in ngugs ) )
        
        return names
        
    
    def GetValue( self ):
        
        gugs = list( self._gug_list_ctrl.GetData() )
        
        ngugs = self._ngug_list_ctrl.GetData()
        
        for ngug in ngugs:
            
            ngug.RepairGUGs( gugs )
            
        
        gugs.extend( ngugs )
        
        return gugs
        
    
class EditURLClassPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, url_class: ClientNetworkingURLClass.URLClass ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._update_already_in_progress = False # Used to avoid infinite recursion on control updates.
        
        self._original_url_class = url_class
        
        self._name = QW.QLineEdit( self )
        
        self._url_type = ClientGUICommon.BetterChoice( self )
        
        for u_t in ( HC.URL_TYPE_POST, HC.URL_TYPE_GALLERY, HC.URL_TYPE_WATCHABLE, HC.URL_TYPE_FILE ):
            
            self._url_type.addItem( HC.url_type_string_lookup[ u_t ], u_t )
            
        
        ( url_type, preferred_scheme, netloc, path_components, parameters, api_lookup_converter, send_referral_url, referral_url_converter, example_url ) = url_class.ToTuple()
        
        self._notebook = ClientGUICommon.BetterNotebook( self )
        
        #
        
        self._matching_panel = ClientGUICommon.StaticBox( self._notebook, 'matching' )
        
        #
        
        self._preferred_scheme = ClientGUICommon.BetterChoice( self._matching_panel )
        
        self._preferred_scheme.addItem( 'http', 'http' )
        self._preferred_scheme.addItem( 'https', 'https' )
        
        self._netloc = QW.QLineEdit( self._matching_panel )
        
        self._match_subdomains = QW.QCheckBox( self._matching_panel )
        
        tt = 'Should this class apply to subdomains as well?'
        tt += os.linesep * 2
        tt += 'For instance, if this url class has domain \'example.com\', should it match a url with \'boards.example.com\' or \'artistname.example.com\'?'
        tt += os.linesep * 2
        tt += 'Any subdomain starting with \'www\' is automatically matched, so do not worry about having to account for that.'
        
        self._match_subdomains.setToolTip( tt )
        
        #
        
        path_components_panel = ClientGUICommon.StaticBox( self._matching_panel, 'path components' )
        
        self._path_components = ClientGUIListBoxes.QueueListBox( path_components_panel, 6, self._ConvertPathComponentRowToString, self._AddPathComponent, self._EditPathComponent )
        
        #
        
        parameters_panel = ClientGUICommon.StaticBox( self._matching_panel, 'parameters' )
        
        parameters_listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( parameters_panel )
        
        self._parameters = ClientGUIListCtrl.BetterListCtrl( parameters_listctrl_panel, CGLC.COLUMN_LIST_URL_CLASS_PATH_COMPONENTS.ID, 5, self._ConvertParameterToListCtrlTuples, delete_key_callback = self._DeleteParameters, activation_callback = self._EditParameters )
        
        parameters_listctrl_panel.SetListCtrl( self._parameters )
        
        parameters_listctrl_panel.AddButton( 'add', self._AddParameters )
        parameters_listctrl_panel.AddButton( 'edit', self._EditParameters, enabled_only_on_selection = True )
        parameters_listctrl_panel.AddDeleteButton()
        
        #
        
        ( has_single_value_parameters, single_value_parameters_string_match ) = url_class.GetSingleValueParameterData()
        
        self._has_single_value_parameters = QW.QCheckBox( self._matching_panel )
        
        tt = 'Some URLs have parameters with just a key or a value, not a "key=value" pair. Normally these are removed on normalisation, but if you turn this on, then this URL will keep them and require at least one.'
        
        self._has_single_value_parameters.setToolTip( tt )
        
        self._has_single_value_parameters.setChecked( has_single_value_parameters )
        
        self._single_value_parameters_string_match = ClientGUIStringControls.StringMatchButton( self._matching_panel, single_value_parameters_string_match )
        
        tt = 'All single-value parameters must match this!'
        
        #
        
        self._notebook.addTab( self._matching_panel, 'match rules' )
        
        #
        
        self._options_panel = ClientGUICommon.StaticBox( self._notebook, 'options' )
        
        #
        
        self._keep_matched_subdomains = QW.QCheckBox( self._options_panel )
        
        tt = 'Should this url keep its matched subdomains when it is normalised?'
        tt += os.linesep * 2
        tt += 'This is typically useful for direct file links that are often served on a numbered CDN subdomain like \'img3.example.com\' but are also valid on the neater main domain.'
        
        self._keep_matched_subdomains.setToolTip( tt )
        
        self._alphabetise_get_parameters = QW.QCheckBox( self._options_panel )
        
        tt = 'Normally, to ensure the same URLs are merged, hydrus will alphabetise GET parameters as part of the normalisation process.'
        tt += os.linesep * 2
        tt += 'Almost all servers support GET params in any order. One or two do not. Uncheck this if you know there is a problem.'
        
        self._alphabetise_get_parameters.setToolTip( tt )
        
        self._can_produce_multiple_files = QW.QCheckBox( self._options_panel )
        
        tt = 'If checked, the client will not rely on instances of this URL class to predetermine \'already in db\' or \'previously deleted\' outcomes. This is important for post types like pixiv pages (which can ultimately be manga, and represent many pages) and tweets (which can have multiple images).'
        tt += os.linesep * 2
        tt += 'Most booru-type Post URLs only produce one file per URL and should not have this checked. Checking this avoids some bad logic where the client would falsely think it if it had seen one file at the URL, it had seen them all, but it then means the client has to download those pages\' content again whenever it sees them (so it can check against the direct File URLs, which are always considered one-file each).'
        
        self._can_produce_multiple_files.setToolTip( tt )
        
        self._should_be_associated_with_files = QW.QCheckBox( self._options_panel )
        
        tt = 'If checked, the client will try to remember this url with any files it ends up importing. It will present this url in \'known urls\' ui across the program.'
        tt += os.linesep * 2
        tt += 'If this URL is a File or Post URL and the client comes across it after having already downloaded it once, it can skip the redundant download since it knows it already has (or has already deleted) the file once before.'
        tt += os.linesep * 2
        tt += 'Turning this on is only useful if the URL is non-ephemeral (i.e. the URL will produce the exact same file(s) in six months\' time). It is usually not appropriate for booru gallery or thread urls, which alter regularly, but is for static Post URLs or some fixed doujin galleries.'
        
        self._should_be_associated_with_files.setToolTip( tt )
        
        self._keep_fragment = QW.QCheckBox( self._options_panel )
        
        tt = 'If checked, fragment text will be kept. This is the component sometimes after an URL that starts with a "#", such as "#kwGFb3xhA3k8B".'
        tt += os.linesep * 2
        tt += 'This data is never sent to a server, so in normal cases should never be kept, but for some clever services such as Mega, with complicated javascript navigation, it may contain unique clientside navigation data if you open the URL in your browser.'
        tt += os.linesep * 2
        tt += 'Only turn this on if you know it is needed. For almost all sites, it only hurts the normalisation process.'
        
        self._keep_fragment.setToolTip( tt )
        
        #
        
        self._referral_url_panel = ClientGUICommon.StaticBox( self._options_panel, 'referral url' )
        
        self._send_referral_url = ClientGUICommon.BetterChoice( self._referral_url_panel )
        
        for s_r_u_t in ClientNetworkingURLClass.SEND_REFERRAL_URL_TYPES:
            
            self._send_referral_url.addItem( ClientNetworkingURLClass.send_referral_url_string_lookup[ s_r_u_t ], s_r_u_t )
            
        
        tt = 'Do not change this unless you know you need to. It fixes complicated problems.'
        
        self._send_referral_url.setToolTip( tt )
        
        self._referral_url_converter = ClientGUIStringControls.StringConverterButton( self._referral_url_panel, referral_url_converter )
        
        tt = 'This will generate a referral URL from the original URL. If the URL needs a referral URL, and you can infer what that would be from just this URL, this will let hydrus download this URL without having to previously visit the referral URL (e.g. letting the user drag-and-drop import). It also lets you set up alternate referral URLs for perculiar situations.'
        
        self._referral_url_converter.setToolTip( tt )
        
        self._referral_url = QW.QLineEdit( self._referral_url_panel )
        self._referral_url.setReadOnly( True )
        
        #
        
        self._api_url_panel = ClientGUICommon.StaticBox( self._options_panel, 'api url' )
        
        self._api_lookup_converter = ClientGUIStringControls.StringConverterButton( self._api_url_panel, api_lookup_converter )
        
        tt = 'This will let you generate an alternate URL for the client to use for the actual download whenever it encounters a URL in this class. You must have a separate URL class to match the API type (which will link to parsers).'
        
        self._api_lookup_converter.setToolTip( tt )
        
        self._api_url = QW.QLineEdit( self._api_url_panel )
        self._api_url.setReadOnly( True )
        
        #
        
        self._next_gallery_page_panel = ClientGUICommon.StaticBox( self._options_panel, 'next gallery page' )
        
        self._next_gallery_page_choice = ClientGUICommon.BetterChoice( self._next_gallery_page_panel )
        
        self._next_gallery_page_delta = QP.MakeQSpinBox( self._next_gallery_page_panel, min=1, max=65536 )
        
        self._next_gallery_page_url = QW.QLineEdit( self._next_gallery_page_panel )
        self._next_gallery_page_url.setReadOnly( True )
        
        #
        
        headers_panel = ClientGUICommon.StaticBox( self._options_panel, 'header overrides' )
        
        header_overrides = url_class.GetHeaderOverrides()
        
        self._header_overrides = ClientGUIStringControls.StringToStringDictControl( headers_panel, header_overrides, min_height = 4 )
        
        #
        
        self._notebook.addTab( self._options_panel, 'options' )
        
        #
        
        self._example_url = QW.QLineEdit( self )
        
        self._example_url_classes = ClientGUICommon.BetterStaticText( self )
        
        self._normalised_url = QW.QLineEdit( self )
        self._normalised_url.setReadOnly( True )
        
        tt = 'The same url can be expressed in different ways. The parameters can be reordered, and descriptive \'sugar\' like "/123456/bodysuit-samus_aran" can be altered at a later date, say to "/123456/bodysuit-green_eyes-samus_aran". In order to collapse all the different expressions of a url down to a single comparable form, the client will \'normalise\' them based on the essential definitions in their url class. Parameters will be alphebatised and non-defined elements will be removed.'
        tt += os.linesep * 2
        tt += 'All normalisation will switch to the preferred scheme (http/https). The alphabetisation of parameters and stripping out of non-defined elements will occur for all URLs except Gallery URLs or Watchable URLs that do not use an API Lookup. (In general, you can define gallery and watchable urls a little more loosely since they generally do not need to be compared, but if you will be saving it with a file or need to perform some regex conversion into an API URL, you\'ll want a rigorously defined url class that will normalise to something reliable and pretty.)'
        
        self._normalised_url.setToolTip( tt )
        
        #
        
        name = url_class.GetName()
        
        self._name.setText( name )
        
        self._url_type.SetValue( url_type )
        
        self._preferred_scheme.SetValue( preferred_scheme )
        
        self._netloc.setText( netloc )
        
        ( match_subdomains, keep_matched_subdomains, alphabetise_get_parameters, can_produce_multiple_files, should_be_associated_with_files, keep_fragment ) = url_class.GetURLBooleans()
        
        self._alphabetise_get_parameters.setChecked( alphabetise_get_parameters )
        self._match_subdomains.setChecked( match_subdomains )
        self._keep_matched_subdomains.setChecked( keep_matched_subdomains )
        self._can_produce_multiple_files.setChecked( can_produce_multiple_files )
        self._should_be_associated_with_files.setChecked( should_be_associated_with_files )
        self._keep_fragment.setChecked( keep_fragment )
        
        self._path_components.AddDatas( path_components )
        
        self._parameters.AddDatas( list( parameters.items() ) )
        
        self._parameters.Sort()
        
        self._example_url.setText( example_url )
        
        example_url_width = ClientGUIFunctions.ConvertTextToPixelWidth( self._example_url, 75 )
        
        self._example_url.setMinimumWidth( example_url_width )
        
        self._send_referral_url.SetValue( send_referral_url )
        
        ( gallery_index_type, gallery_index_identifier, gallery_index_delta ) = url_class.GetGalleryIndexValues()
        
        # this preps it for the upcoming update
        self._next_gallery_page_choice.addItem( 'initialisation', ( gallery_index_type, gallery_index_identifier ) )
        self._next_gallery_page_choice.setCurrentIndex( 0 )
        
        self._next_gallery_page_delta.setValue( gallery_index_delta )
        
        self._UpdateControls()
        
        #
        
        path_components_panel.Add( self._path_components, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        parameters_panel.Add( parameters_listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        headers_panel.Add( self._header_overrides, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        rows = []
        
        rows.append( ( 'preferred scheme: ', self._preferred_scheme ) )
        rows.append( ( 'network location: ', self._netloc ) )
        rows.append( ( 'should subdomains also match this class?: ', self._match_subdomains ) )
        
        gridbox_1 = ClientGUICommon.WrapInGrid( self._matching_panel, rows )
        
        rows = []
        
        rows.append( ( 'has single-value parameter(s): ', self._has_single_value_parameters ) )
        rows.append( ( 'string match for single-value parameters: ', self._single_value_parameters_string_match ) )
        
        gridbox_2 = ClientGUICommon.WrapInGrid( self._matching_panel, rows )
        
        self._matching_panel.Add( gridbox_1, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._matching_panel.Add( path_components_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        self._matching_panel.Add( parameters_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        self._matching_panel.Add( gridbox_2, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._next_gallery_page_choice, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, self._next_gallery_page_delta, CC.FLAGS_CENTER_PERPENDICULAR )
        
        rows = []
        
        rows.append( ( 'next gallery page url: ', self._next_gallery_page_url ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._next_gallery_page_panel, rows )
        
        self._next_gallery_page_panel.Add( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._next_gallery_page_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        rows = []
        
        rows.append( ( 'send referral url?: ', self._send_referral_url ) )
        rows.append( ( 'optional referral url converter: ', self._referral_url_converter ) )
        rows.append( ( 'referral url: ', self._referral_url ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._referral_url_panel, rows )
        
        self._referral_url_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        rows = []
        
        rows.append( ( 'optional api url converter: ', self._api_lookup_converter ) )
        rows.append( ( 'api url: ', self._api_url ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._api_url_panel, rows )
        
        self._api_url_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        rows = []
        
        rows.append( ( 'if matching by subdomain, keep it when normalising?: ', self._keep_matched_subdomains ) )
        rows.append( ( 'alphabetise GET parameters when normalising?: ', self._alphabetise_get_parameters ) )
        rows.append( ( 'keep fragment when normalising?: ', self._keep_fragment ) )
        rows.append( ( 'post page can produce multiple files?: ', self._can_produce_multiple_files ) )
        rows.append( ( 'associate a \'known url\' with resulting files?: ', self._should_be_associated_with_files ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._options_panel, rows )
        
        self._options_panel.Add( gridbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._options_panel.Add( self._api_url_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._options_panel.Add( self._referral_url_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._options_panel.Add( self._next_gallery_page_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._options_panel.Add( headers_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        rows = []
        
        rows.append( ( 'name: ', self._name ) )
        rows.append( ( 'url type: ', self._url_type ) )
        
        gridbox_1 = ClientGUICommon.WrapInGrid( self._matching_panel, rows )
        
        rows = []
        
        rows.append( ( 'example url: ', self._example_url ) )
        rows.append( ( 'normalised url: ', self._normalised_url ) )
        
        gridbox_2 = ClientGUICommon.WrapInGrid( self, rows )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, gridbox_1, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, self._example_url_classes, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, gridbox_2, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.widget().setLayout( vbox )
        
        #
        
        self._preferred_scheme.currentIndexChanged.connect( self._UpdateControls )
        self._netloc.textChanged.connect( self._UpdateControls )
        self._alphabetise_get_parameters.clicked.connect( self._UpdateControls )
        self._match_subdomains.clicked.connect( self._UpdateControls )
        self._keep_matched_subdomains.clicked.connect( self._UpdateControls )
        self._keep_fragment.clicked.connect( self._UpdateControls )
        self._can_produce_multiple_files.clicked.connect( self._UpdateControls )
        self._next_gallery_page_choice.currentIndexChanged.connect( self._UpdateControls )
        self._next_gallery_page_delta.valueChanged.connect( self._UpdateControls )
        self._example_url.textChanged.connect( self._UpdateControls )
        self._path_components.listBoxChanged.connect( self._UpdateControls )
        self._url_type.currentIndexChanged.connect( self.EventURLTypeUpdate )
        self._send_referral_url.currentIndexChanged.connect( self._UpdateControls )
        self._referral_url_converter.valueChanged.connect( self._UpdateControls )
        self._api_lookup_converter.valueChanged.connect( self._UpdateControls )
        self._has_single_value_parameters.clicked.connect( self._UpdateControls )
        self._single_value_parameters_string_match.valueChanged.connect( self._UpdateControls )
        
        self._should_be_associated_with_files.clicked.connect( self.EventAssociationUpdate )
        
    
    def _AddParameters( self ):
        
        with ClientGUIDialogs.DialogTextEntry( self, 'edit the key', placeholder = 'key', allow_blank = False ) as dlg:
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                key = dlg.GetValue()
                
            else:
                
                return
                
            
        
        existing_keys = self._GetExistingKeys()
        
        if key in existing_keys:
            
            QW.QMessageBox.critical( self, 'Error', 'That key already exists!' )
            
            return
            
        
        string_match = ClientStrings.StringMatch()
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit value' ) as dlg:
            
            from hydrus.client.gui import ClientGUIStringPanels
            
            panel = ClientGUIStringPanels.EditStringMatchPanel( dlg, string_match )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                string_match = panel.GetValue()
                
                with ClientGUIDialogs.DialogTextEntry( self, 'Enter optional \'default\' value for this parameter, which will be filled in if missing. Leave blank for none (recommended).', allow_blank = True ) as dlg_default:
                    
                    if dlg_default.exec() == QW.QDialog.Accepted:
                        
                        default = dlg_default.GetValue()
                        
                        if default == '':
                            
                            default = None
                            
                        elif not string_match.Matches( default ):
                            
                            QW.QMessageBox.warning( self, 'Warning', 'That default does not match the given rule! Clearing it to none!' )
                            
                            default = None
                            
                        
                    else:
                        
                        return
                        
                    
                
            else:
                
                return
                
            
        
        data = ( key, ( string_match, default ) )
        
        self._parameters.AddDatas( ( data, ) )
        
        self._parameters.Sort()
        
        self._UpdateControls()
        
    
    def _AddPathComponent( self ):
        
        string_match = ClientStrings.StringMatch()
        default = None
        
        return self._EditPathComponent( ( string_match, default ) )
        
    
    def _ConvertParameterToListCtrlTuples( self, data ):
        
        ( key, ( string_match, default ) ) = data
        
        pretty_key = key
        pretty_string_match = string_match.ToString()
        
        if default is not None:
            
            pretty_string_match += ' (default "' + default + '")'
            
        
        sort_key = pretty_key
        sort_string_match = pretty_string_match
        
        display_tuple = ( pretty_key, pretty_string_match )
        sort_tuple = ( sort_key, sort_string_match )
        
        return ( display_tuple, sort_tuple )
        
    
    def _ConvertPathComponentRowToString( self, row ):
        
        ( string_match, default ) = row
        
        s = string_match.ToString()
        
        if default is not None:
            
            s += ' (default "' + default + '")'
            
        
        return s
        
    
    def _DeleteParameters( self ):
        
        self._parameters.ShowDeleteSelectedDialog()
        
        self._UpdateControls()
        
    
    def _EditParameters( self ):
        
        selected_params = self._parameters.GetData( only_selected = True )
        
        for parameter in selected_params:
            
            ( original_key, ( original_string_match, original_default ) ) = parameter
            
            with ClientGUIDialogs.DialogTextEntry( self, 'edit the key', default = original_key, allow_blank = False ) as dlg:
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    key = dlg.GetValue()
                    
                else:
                    
                    return
                    
                
            
            if key != original_key:
                
                existing_keys = self._GetExistingKeys()
                
                if key in existing_keys:
                    
                    QW.QMessageBox.critical( self, 'Error', 'That key already exists!' )
                    
                    return
                    
                
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit value' ) as dlg:
                
                from hydrus.client.gui import ClientGUIStringPanels
                
                panel = ClientGUIStringPanels.EditStringMatchPanel( dlg, original_string_match )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    string_match = panel.GetValue()
                    
                    if original_default is None:
                        
                        original_default = ''
                        
                    
                    with ClientGUIDialogs.DialogTextEntry( self, 'Enter optional \'default\' value for this parameter, which will be filled in if missing. Leave blank for none (recommended).', default = original_default, allow_blank = True ) as dlg_default:
                        
                        if dlg_default.exec() == QW.QDialog.Accepted:
                            
                            default = dlg_default.GetValue()
                            
                            if default == '':
                                
                                default = None
                                
                            elif not string_match.Matches( default ):
                                
                                QW.QMessageBox.warning( self, 'Warning', 'That default does not match the given rule! Clearing it to none!' )
                                
                                default = None
                                
                            
                        else:
                            
                            return
                            
                        
                    
                else:
                    
                    return
                    
                
            
            self._parameters.DeleteDatas( ( parameter, ) )
            
            new_parameter = ( key, ( string_match, default ) )
            
            self._parameters.AddDatas( ( new_parameter, ) )
            
        
        self._parameters.Sort()
        
        self._UpdateControls()
        
    
    def _EditPathComponent( self, row ):
        
        ( string_match, default ) = row
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit path component' ) as dlg:
            
            from hydrus.client.gui import ClientGUIStringPanels
            
            panel = ClientGUIStringPanels.EditStringMatchPanel( dlg, string_match )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                new_string_match = panel.GetValue()
                
                if default is None:
                    
                    default = ''
                    
                
                with ClientGUIDialogs.DialogTextEntry( self, 'Enter optional \'default\' value for this path component, which will be filled in if missing. Leave blank for none (recommended).', default = default, allow_blank = True ) as dlg_default:
                    
                    if dlg_default.exec() == QW.QDialog.Accepted:
                        
                        new_default = dlg_default.GetValue()
                        
                        if new_default == '':
                            
                            new_default = None
                            
                        elif not string_match.Matches( new_default ):
                            
                            QW.QMessageBox.warning( self, 'Warning', 'That default does not match the given rule! Clearing it to none!' )
                            
                            new_default = None
                            
                        
                        new_row = ( new_string_match, new_default )
                        
                        QP.CallAfter( self._UpdateControls ) # seems sometimes this doesn't kick in naturally
                        
                        return new_row
                        
                    
                
            
            raise HydrusExceptions.VetoException()
            
        
    
    def _GetExistingKeys( self ):
        
        params = self._parameters.GetData()
        
        keys = { key for ( key, string_match ) in params }
        
        return keys
        
    
    def _GetValue( self ):
        
        url_class_key = self._original_url_class.GetClassKey()
        name = self._name.text()
        url_type = self._url_type.GetValue()
        preferred_scheme = self._preferred_scheme.GetValue()
        netloc = self._netloc.text()
        path_components = self._path_components.GetData()
        parameters = dict( self._parameters.GetData() )
        has_single_value_parameters = self._has_single_value_parameters.isChecked()
        single_value_parameters_string_match = self._single_value_parameters_string_match.GetValue()
        header_overrides = self._header_overrides.GetValue()
        api_lookup_converter = self._api_lookup_converter.GetValue()
        send_referral_url = self._send_referral_url.GetValue()
        referral_url_converter = self._referral_url_converter.GetValue()
        
        ( gallery_index_type, gallery_index_identifier ) = self._next_gallery_page_choice.GetValue()
        gallery_index_delta = self._next_gallery_page_delta.value()
        
        example_url = self._example_url.text()
        
        url_class = ClientNetworkingURLClass.URLClass(
            name,
            url_class_key = url_class_key,
            url_type = url_type,
            preferred_scheme = preferred_scheme,
            netloc = netloc,
            path_components = path_components,
            parameters = parameters,
            has_single_value_parameters = has_single_value_parameters,
            single_value_parameters_string_match = single_value_parameters_string_match,
            header_overrides = header_overrides,
            api_lookup_converter = api_lookup_converter,
            send_referral_url = send_referral_url,
            referral_url_converter = referral_url_converter,
            gallery_index_type = gallery_index_type,
            gallery_index_identifier = gallery_index_identifier,
            gallery_index_delta = gallery_index_delta,
            example_url = example_url
        )
        
        match_subdomains = self._match_subdomains.isChecked()
        keep_matched_subdomains = self._keep_matched_subdomains.isChecked()
        alphabetise_get_parameters = self._alphabetise_get_parameters.isChecked()
        can_produce_multiple_files = self._can_produce_multiple_files.isChecked()
        should_be_associated_with_files = self._should_be_associated_with_files.isChecked()
        keep_fragment = self._keep_fragment.isChecked()
        
        url_class.SetURLBooleans(
            match_subdomains,
            keep_matched_subdomains,
            alphabetise_get_parameters,
            can_produce_multiple_files,
            should_be_associated_with_files,
            keep_fragment
        )
        
        return url_class
        
    
    def _UpdateControls( self ):
        
        # we need to regen possible next gallery page choices before we fetch current value and update everything else
        
        if self._update_already_in_progress: return # Could use blockSignals but this way I don't have to block signals on individual controls

        self._update_already_in_progress = True
        
        if self._url_type.GetValue() == HC.URL_TYPE_GALLERY:
            
            self._next_gallery_page_panel.setEnabled( True )
            
            choices = [ ( 'no next gallery page info set', ( None, None ) ) ]
            
            for ( index, ( string_match, default ) ) in enumerate( self._path_components.GetData() ):
                
                if True in ( string_match.Matches( n ) for n in ( '0', '1', '10', '100', '42' ) ):
                    
                    choices.append( ( HydrusData.ConvertIntToPrettyOrdinalString( index + 1 ) + ' path component', ( ClientNetworkingURLClass.GALLERY_INDEX_TYPE_PATH_COMPONENT, index ) ) )
                    
                
            
            for ( index, ( key, ( string_match, default ) ) ) in enumerate( self._parameters.GetData() ):
                
                if True in ( string_match.Matches( n ) for n in ( '0', '1', '10', '100', '42' ) ):
                    
                    choices.append( ( key + ' parameter', ( ClientNetworkingURLClass.GALLERY_INDEX_TYPE_PARAMETER, key ) ) )
                    
                
            
            existing_choice = self._next_gallery_page_choice.GetValue()
            
            self._next_gallery_page_choice.clear()
            
            for ( name, data ) in choices:
                
                self._next_gallery_page_choice.addItem( name, data )
                
            
            self._next_gallery_page_choice.SetValue( existing_choice ) # this should fail to ( None, None )
            
            ( gallery_index_type, gallery_index_identifier ) = self._next_gallery_page_choice.GetValue() # what was actually set?
            
            if gallery_index_type is None:
                
                self._next_gallery_page_delta.setEnabled( False )
                
            else:
                
                self._next_gallery_page_delta.setEnabled( True )
                
            
        else:
            
            self._next_gallery_page_panel.setEnabled( False )
            
        
        self._single_value_parameters_string_match.setEnabled( self._has_single_value_parameters.isChecked() )
        
        #
        
        url_class = self._GetValue()
        
        url_type = url_class.GetURLType()
        
        if url_type == HC.URL_TYPE_POST:
            
            self._can_produce_multiple_files.setEnabled( True )
            
        else:
            
            self._can_produce_multiple_files.setEnabled( False )
            
        
        if url_class.ClippingIsAppropriate():
            
            if self._match_subdomains.isChecked():
                
                self._keep_matched_subdomains.setEnabled( True )
                
            else:
                
                self._keep_matched_subdomains.setChecked( False )
                self._keep_matched_subdomains.setEnabled( False )
                
            
        else:
            
            self._keep_matched_subdomains.setEnabled( False )
            
        
        try:
            
            example_url = self._example_url.text()
            
            url_class.Test( example_url )
            
            self._example_url_classes.setText( 'Example matches ok!' )
            self._example_url_classes.setObjectName( 'HydrusValid' )
            
            normalised = url_class.Normalise( example_url )
            
            self._normalised_url.setText( normalised )
            
            self._referral_url_converter.SetExampleString( normalised )
            self._api_lookup_converter.SetExampleString( normalised )
            
            if url_class.UsesAPIURL():
                
                self._send_referral_url.setEnabled( False )
                self._referral_url_converter.setEnabled( False )
                
                self._referral_url.setText( 'Not used, as API converter will redirect.' )
                
            else:
                
                self._send_referral_url.setEnabled( True )
                self._referral_url_converter.setEnabled( True )
                
                send_referral_url = self._send_referral_url.GetValue()
                
                if send_referral_url in ( ClientNetworkingURLClass.SEND_REFERRAL_URL_ONLY_IF_PROVIDED, ClientNetworkingURLClass.SEND_REFERRAL_URL_NEVER ):
                    
                    self._referral_url_converter.setEnabled( False )
                    
                else:
                    
                    self._referral_url_converter.setEnabled( True )
                    
                
                if send_referral_url == ClientNetworkingURLClass.SEND_REFERRAL_URL_CONVERTER_IF_NONE_PROVIDED:
                    
                    referral_url = url_class.GetReferralURL( normalised, None )
                    
                    referral_url = 'normal referral url -or- {}'.format( referral_url )
                    
                else:
                    
                    referral_url = url_class.GetReferralURL( normalised, 'normal referral url' )
                    
                
                if referral_url is None:
                    
                    self._referral_url.setText( 'None' )
                    
                else:
                    
                    self._referral_url.setText( referral_url )
                    
                
            
            try:
                
                if url_class.UsesAPIURL():
                    
                    api_lookup_url = url_class.GetAPIURL( normalised )
                    
                    if url_class.Matches( api_lookup_url ):
                        
                        self._example_url_classes.setText( 'Matches own API URL!' )
                        self._example_url_classes.setObjectName( 'HydrusInvalid' )
                        
                    
                else:
                    
                    api_lookup_url = 'none set'
                    
                
                self._api_url.setText( api_lookup_url )
                
            except HydrusExceptions.StringConvertException as e:
                
                reason = str( e )
                
                self._api_url.setText( 'Could not convert - ' + reason )
                
                self._example_url_classes.setText( 'API URL Problem!' )
                self._example_url_classes.setObjectName( 'HydrusInvalid' )
                
            
            try:
                
                if url_class.CanGenerateNextGalleryPage():
                    
                    next_gallery_page_url = url_class.GetNextGalleryPage( normalised )
                    
                else:
                    
                    next_gallery_page_url = 'none set'
                    
                
                self._next_gallery_page_url.setText( next_gallery_page_url )
                
            except Exception as e:
                
                reason = str( e )
                
                self._next_gallery_page_url.setText( 'Could not convert - ' + reason )
                
            
        except HydrusExceptions.URLClassException as e:
            
            reason = str( e )
            
            self._example_url_classes.setText( 'Example does not match - '+reason )
            self._example_url_classes.setObjectName( 'HydrusInvalid' )
            
            self._normalised_url.clear()
            self._api_url.clear()
            
        
        self._example_url_classes.style().polish( self._example_url_classes )
        
        self._update_already_in_progress = False
        
    
    def EventAssociationUpdate( self ):
        
        if self._should_be_associated_with_files.isChecked():
            
            if self._url_type.GetValue() in ( HC.URL_TYPE_GALLERY, HC.URL_TYPE_WATCHABLE ):
                
                message = 'Please note that it is only appropriate to associate a Gallery or Watchable URL with a file if that URL is non-ephemeral. It is only appropriate if the exact same URL will definitely give the same files in six months\' time (like a fixed doujin chapter gallery).'
                message += os.linesep * 2
                message += 'If you are not sure what this means, turn this back off.'
                
                QW.QMessageBox.information( self, 'Information', message )
                
            
        else:
            
            if self._url_type.GetValue() in ( HC.URL_TYPE_FILE, HC.URL_TYPE_POST ):
                
                message = 'Hydrus uses these file associations to make sure not to re-download the same file when it comes across the same URL in future. It is only appropriate to not associate a file or post url with a file if that url is particularly ephemeral, such as if the URL includes a non-removable random key that becomes invalid after a few minutes.'
                message += os.linesep * 2
                message += 'If you are not sure what this means, turn this back on.'
                
                QW.QMessageBox.information( self, 'Information', message )
            
        
    
    def EventURLTypeUpdate( self, event ):
        
        url_type = self._url_type.GetValue()
        
        if url_type in ( HC.URL_TYPE_FILE, HC.URL_TYPE_POST ):
            
            self._should_be_associated_with_files.setChecked( True )
            
        else:
            
            self._should_be_associated_with_files.setChecked( False )
            
        
        self._UpdateControls()
        
    
    def GetValue( self ) -> ClientNetworkingURLClass.URLClass:
        
        url_class = self._GetValue()
        
        example_url = self._example_url.text()
        
        try:
            
            url_class.Test( example_url )
            
        except HydrusExceptions.URLClassException:
            
            raise HydrusExceptions.VetoException( 'Please enter an example url that matches the given rules!' )
            
        
        if url_class.UsesAPIURL():
            
            try:
                
                api_lookup_url = url_class.GetAPIURL( example_url )
                
            except HydrusExceptions.StringConvertException as e:
                
                raise HydrusExceptions.VetoException( 'Problem making API URL!' )
                
            
        
        return url_class
        
    
    def UserIsOKToOK( self ):
        
        url_class = self._GetValue()
        
        example_url = self._example_url.text()
        
        if url_class.UsesAPIURL():
            
            try:
                
                api_lookup_url = url_class.GetAPIURL( example_url )
                
            except HydrusExceptions.StringConvertException as e:
                
                return True
                
            
            if url_class.Matches( api_lookup_url ):
                
                message = 'This URL class matches its own API URL! This can break a downloader unless there is a more specific URL Class the matches the API URL before this. I recommend you fix this here, but you do not have to. Exit now?'
                
                result = ClientGUIDialogsQuick.GetYesNo( self, message )
                
                if result != QW.QDialog.Accepted:
                    
                    return False
                    
                
            
        
        return True
        
    
class EditURLClassesPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, url_classes: typing.Iterable[ ClientNetworkingURLClass.URLClass ] ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        menu_items = []
        
        call = HydrusData.Call( ClientPaths.LaunchPathInWebBrowser, os.path.join( HC.HELP_DIR, 'downloader_url_classes.html' ) )
        
        menu_items.append( ( 'normal', 'open the url classes help', 'Open the help page for url classes in your web browser.', call ) )
        
        help_button = ClientGUIMenuButton.MenuBitmapButton( self, CC.global_pixmaps().help, menu_items )
        
        help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help for this panel -->', object_name = 'HydrusIndeterminate' )
        
        self._url_class_checker = QW.QLineEdit( self )
        self._url_class_checker.textChanged.connect( self.EventURLClassCheckerText )
        
        self._url_class_checker_st = ClientGUICommon.BetterStaticText( self )
        
        self._list_ctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        self._list_ctrl = ClientGUIListCtrl.BetterListCtrl( self._list_ctrl_panel, CGLC.COLUMN_LIST_URL_CLASSES.ID, 15, self._ConvertDataToListCtrlTuples, use_simple_delete = True, activation_callback = self._Edit )
        
        self._list_ctrl_panel.SetListCtrl( self._list_ctrl )
        
        self._list_ctrl_panel.AddButton( 'add', self._Add )
        self._list_ctrl_panel.AddButton( 'edit', self._Edit, enabled_only_on_selection = True )
        self._list_ctrl_panel.AddDeleteButton()
        self._list_ctrl_panel.AddSeparator()
        self._list_ctrl_panel.AddImportExportButtons( ( ClientNetworkingURLClass.URLClass, ), self._AddURLClass )
        self._list_ctrl_panel.AddSeparator()
        self._list_ctrl_panel.AddDefaultsButton( ClientDefaults.GetDefaultURLClasses, self._AddURLClass )
        
        #
        
        self._list_ctrl.AddDatas( url_classes )
        
        self._list_ctrl.Sort()
        
        #
        
        url_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( url_hbox, self._url_class_checker, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( url_hbox, self._url_class_checker_st, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, help_hbox, CC.FLAGS_ON_RIGHT )
        QP.AddToLayout( vbox, url_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._list_ctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
        #
        
        self._UpdateURLClassCheckerText()
        
    
    def _Add( self ):
        
        url_class = ClientNetworkingURLClass.URLClass( 'new url class' )
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit url class' ) as dlg:
            
            panel = EditURLClassPanel( dlg, url_class )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                url_class = panel.GetValue()
                
                self._AddURLClass( url_class )
                
                self._list_ctrl.Sort()
                
            
        
    
    def _AddURLClass( self, url_class ):
        
        HydrusSerialisable.SetNonDupeName( url_class, self._GetExistingNames() )
        
        url_class.RegenerateClassKey()
        
        self._list_ctrl.AddDatas( ( url_class, ) )
        
    
    def _ConvertDataToListCtrlTuples( self, url_class ):
        
        name = url_class.GetName()
        url_type = url_class.GetURLType()
        example_url = url_class.Normalise( url_class.GetExampleURL() )
        
        pretty_name = name
        pretty_url_type = HC.url_type_string_lookup[ url_type ]
        pretty_example_url = example_url
        
        display_tuple = ( pretty_name, pretty_url_type, pretty_example_url )
        sort_tuple = ( name, url_type, example_url )
        
        return ( display_tuple, sort_tuple )
        
    
    def _Edit( self ):
        
        for url_class in self._list_ctrl.GetData( only_selected = True ):
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit url class' ) as dlg:
                
                panel = EditURLClassPanel( dlg, url_class )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    self._list_ctrl.DeleteDatas( ( url_class, ) )
                    
                    url_class = panel.GetValue()
                    
                    HydrusSerialisable.SetNonDupeName( url_class, self._GetExistingNames() )
                    
                    self._list_ctrl.AddDatas( ( url_class, ) )
                    
                else:
                    
                    break
                    
                
            
        
        self._list_ctrl.Sort()
        
    
    def _GetExistingNames( self ):
        
        url_classes = self._list_ctrl.GetData()
        
        names = { url_class.GetName() for url_class in url_classes }
        
        return names
        
    
    def _UpdateURLClassCheckerText( self ):
        
        url = self._url_class_checker.text()
        
        if url == '':
            
            text = '<-- Enter a URL here to see which url class it currently matches!'
            
        else:
            
            url_classes = self.GetValue()
            
            domain_manager = ClientNetworkingDomain.NetworkDomainManager()
            
            domain_manager.Initialise()
            
            domain_manager.SetURLClasses( url_classes )
            
            try:
                
                url_class = domain_manager.GetURLClass( url )
                
                if url_class is None:
                    
                    text = 'No match!'
                    
                else:
                    
                    text = 'Matches "' + url_class.GetName() + '"'
                    
                
            except HydrusExceptions.URLClassException as e:
                
                text = str( e )
                
            
        
        self._url_class_checker_st.setText( text )
        
    
    def EventURLClassCheckerText( self, text ):
        
        self._UpdateURLClassCheckerText()
        
    
    def GetValue( self ) -> typing.List[ ClientNetworkingURLClass.URLClass ]:
        
        url_classes = self._list_ctrl.GetData()
        
        return url_classes
        
    
class EditURLClassLinksPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, network_engine, url_classes, parsers, url_class_keys_to_parser_keys ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._url_classes = url_classes
        self._url_class_keys_to_url_classes = { url_class.GetClassKey() : url_class for url_class in self._url_classes }
        
        self._parsers = parsers
        self._parser_keys_to_parsers = { parser.GetParserKey() : parser for parser in self._parsers }
        
        self._network_engine = network_engine
        
        #
        
        self._notebook = QW.QTabWidget( self )
        
        #
        
        self._api_pairs_list_ctrl = ClientGUIListCtrl.BetterListCtrl( self._notebook, CGLC.COLUMN_LIST_URL_CLASS_API_PAIRS.ID, 10, self._ConvertAPIPairDataToListCtrlTuples )
        
        #
        
        self._parser_list_ctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self._notebook )
        
        self._parser_list_ctrl = ClientGUIListCtrl.BetterListCtrl( self._parser_list_ctrl_panel, CGLC.COLUMN_LIST_URL_CLASS_KEYS_TO_PARSER_KEYS.ID, 24, self._ConvertParserDataToListCtrlTuples, activation_callback = self._EditParser )
        
        self._parser_list_ctrl_panel.SetListCtrl( self._parser_list_ctrl )
        
        self._parser_list_ctrl_panel.AddButton( 'edit', self._EditParser, enabled_only_on_selection = True )
        self._parser_list_ctrl_panel.AddButton( 'clear', self._ClearParser, enabled_check_func = self._LinksOnCurrentSelection )
        self._parser_list_ctrl_panel.AddButton( 'try to fill in gaps based on example urls', self._TryToLinkURLClassesAndParsers, enabled_check_func = self._GapsExist )
        
        #
        
        api_pairs = ClientNetworkingURLClass.ConvertURLClassesIntoAPIPairs( url_classes )
        
        self._api_pairs_list_ctrl.AddDatas( api_pairs )
        
        self._api_pairs_list_ctrl.Sort()
        
        # anything that goes to an api url will be parsed by that api's parser--it can't have its own
        api_pair_unparsable_url_classes = set()
        
        for ( a, b ) in api_pairs:
            
            api_pair_unparsable_url_classes.add( a )
            
        
        #
        
        listctrl_data = []
        
        for url_class in url_classes:
            
            if not url_class.IsParsable() or url_class in api_pair_unparsable_url_classes:
                
                continue
                
            
            url_class_key = url_class.GetClassKey()
            
            if url_class_key in url_class_keys_to_parser_keys:
                
                parser_key = url_class_keys_to_parser_keys[ url_class_key ]
                
            else:
                
                parser_key = None
                
            
            listctrl_data.append( ( url_class_key, parser_key ) )
            
        
        self._parser_list_ctrl.AddDatas( listctrl_data )
        
        self._parser_list_ctrl.Sort()
        
        #
        
        self._notebook.addTab( self._parser_list_ctrl_panel, 'parser links' )
        self._notebook.addTab( self._api_pairs_list_ctrl, 'api link review' )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
    def _ClearParser( self ):
        
        result = ClientGUIDialogsQuick.GetYesNo( self, 'Clear all the selected linked parsers?' )
        
        if result == QW.QDialog.Accepted:
            
            for data in self._parser_list_ctrl.GetData( only_selected = True ):
                
                self._parser_list_ctrl.DeleteDatas( ( data, ) )
                
                ( url_class_key, parser_key ) = data
                
                new_data = ( url_class_key, None )
                
                self._parser_list_ctrl.AddDatas( ( new_data, ) )
                
            
            self._parser_list_ctrl.Sort()
            
        
    
    def _ConvertAPIPairDataToListCtrlTuples( self, data ):
        
        ( a, b ) = data
        
        a_name = a.GetName()
        b_name = b.GetName()
        
        pretty_a_name = a_name
        pretty_b_name = b_name
        
        display_tuple = ( pretty_a_name, pretty_b_name )
        sort_tuple = ( a_name, b_name )
        
        return ( display_tuple, sort_tuple )
        
    
    def _ConvertParserDataToListCtrlTuples( self, data ):
        
        ( url_class_key, parser_key ) = data
        
        url_class = self._url_class_keys_to_url_classes[ url_class_key ]
        
        url_class_name = url_class.GetName()
        
        url_type = url_class.GetURLType()
        
        if parser_key is None:
            
            parser_name = ''
            
        else:
            
            parser = self._parser_keys_to_parsers[ parser_key ]
            
            parser_name = parser.GetName()
            
        
        pretty_url_class_name = url_class_name
        
        pretty_url_type = HC.url_type_string_lookup[ url_type ]
        
        pretty_parser_name = parser_name
        
        display_tuple = ( pretty_url_class_name, pretty_url_type, pretty_parser_name )
        sort_tuple = ( url_class_name, pretty_url_type, parser_name )
        
        return ( display_tuple, sort_tuple )
        
    
    def _EditParser( self ):
        
        if len( self._parsers ) == 0:
            
            QW.QMessageBox.information( self, 'Information', 'Unfortunately, you do not have any parsers, so none can be linked to your url classes. Please create some!' )
            
            return
            
        
        for data in self._parser_list_ctrl.GetData( only_selected = True ):
            
            ( url_class_key, parser_key ) = data
            
            url_class = self._url_class_keys_to_url_classes[ url_class_key ]
            
            matching_parsers = [ parser for parser in self._parsers if True in ( url_class.Matches( url ) for url in parser.GetExampleURLs() ) ]
            unmatching_parsers = [ parser for parser in self._parsers if parser not in matching_parsers ]
            
            matching_parsers.sort( key = lambda p: p.GetName() )
            unmatching_parsers.sort( key = lambda p: p.GetName() )
            
            choice_tuples = [ ( parser.GetName(), parser ) for parser in matching_parsers ]
            choice_tuples.append( ( '------', None ) )
            choice_tuples.extend( [ ( parser.GetName(), parser ) for parser in unmatching_parsers ] )
            
            try:
                
                parser = ClientGUIDialogsQuick.SelectFromList( self, 'select parser for ' + url_class.GetName(), choice_tuples, sort_tuples = False )
                
            except HydrusExceptions.CancelledException:
                
                break
                
            
            if parser is None:
                
                break
                
            
            self._parser_list_ctrl.DeleteDatas( ( data, ) )
            
            new_data = ( url_class_key, parser.GetParserKey() )
            
            self._parser_list_ctrl.AddDatas( ( new_data, ) )
            
        
        self._parser_list_ctrl.Sort()
        
    
    def _GapsExist( self ):
        
        return None in ( parser_key for ( url_class_key, parser_key ) in self._parser_list_ctrl.GetData() )
        
    
    def _LinksOnCurrentSelection( self ):
        
        non_none_parser_keys = [ parser_key for ( url_class_key, parser_key ) in self._parser_list_ctrl.GetData( only_selected = True ) if parser_key is not None ]
        
        return len( non_none_parser_keys ) > 0
        
    
    def _TryToLinkURLClassesAndParsers( self ):
        
        existing_url_class_keys_to_parser_keys = { url_class_key : parser_key for ( url_class_key, parser_key ) in self._parser_list_ctrl.GetData() if parser_key is not None }
        
        new_url_class_keys_to_parser_keys = ClientNetworkingDomain.NetworkDomainManager.STATICLinkURLClassesAndParsers( self._url_classes, self._parsers, existing_url_class_keys_to_parser_keys )
        
        if len( new_url_class_keys_to_parser_keys ) > 0:
            
            removees = []
            
            for row in self._parser_list_ctrl.GetData():
                
                ( url_class_key, parser_key ) = row
                
                if url_class_key in new_url_class_keys_to_parser_keys:
                    
                    removees.append( row )
                    
                
            
            self._parser_list_ctrl.DeleteDatas( removees )
            
            self._parser_list_ctrl.AddDatas( list(new_url_class_keys_to_parser_keys.items()) )
            
            self._parser_list_ctrl.Sort()
            
        
    
    def GetValue( self ):
        
        url_class_keys_to_parser_keys = { url_class_key : parser_key for ( url_class_key, parser_key ) in self._parser_list_ctrl.GetData() if parser_key is not None }
        
        return url_class_keys_to_parser_keys
        
    
