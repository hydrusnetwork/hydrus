import collections.abc

from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusText

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientDefaults
from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListConstants as CGLC
from hydrus.client.gui.lists import ClientGUIListCtrl
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.gui.widgets import ClientGUIMenuButton
from hydrus.client.networking import ClientNetworkingDomain
from hydrus.client.networking import ClientNetworkingFunctions
from hydrus.client.networking import ClientNetworkingGUG
from hydrus.client.networking import ClientNetworkingURLClass

def Show403Info( win: QW.QWidget ):
    
    message = 'Hydrus\'s downloader tech is pretty old, and as the infrastructure of the internet changes, some things are breaking.'
    message += '\n\n'
    message += 'You may get a 403 result for a search or file download. This is often because a CDN (e.g. CloudFlare) is gating the site with a captcha-like test. It can hit users in certain IP regions or VPN networks worse. The rules are often applied dynamically, so it sometimes passes within a week.'
    message += '\n\n'
    message += 'The situation is, unfortunately, generally getting worse. Some users have had success with tools like Hydrus Companion, which can synchronise browser User-Agent and cookies to hydrus, but this is proving less reliable these days. Others have been experimenting with alternate downloaders that use official APIs. These are sometimes great; but some are very restricted and need a login. Check out the user-run downloader repository to see what people have figured out. There are also more sophisticated downloader solutions like hydownloader and gallery-dl, but these take some time to set up.'
    message += '\n\n'
    message += 'Hydev is planning to retire default downloaders that become less reliable. I am not yet sure what I will do long-term, but I am thinking about it. Sorry for the trouble!'
    
    ClientGUIDialogsMessage.ShowInformation( win, message )
    

class EditDownloaderDisplayPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, network_engine, gugs, gug_keys_to_display, url_classes, url_class_keys_to_display, show_unmatched_urls_in_media_viewer ):
        
        super().__init__( parent )
        
        self._gugs = gugs
        self._gug_keys_to_gugs: dict[ bytes, ClientNetworkingGUG.GalleryURLGenerator ] = { gug.GetGUGKey() : gug for gug in self._gugs }
        
        self._url_classes = url_classes
        self._url_class_keys_to_url_classes: dict[ bytes, ClientNetworkingURLClass.URLClass ] = { url_class.GetClassKey() : url_class for url_class in self._url_classes }
        
        self._network_engine = network_engine
        
        #
        
        self._notebook = QW.QTabWidget( self )
        
        #
        
        self._gug_display_list_ctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self._notebook )
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_GUG_KEYS_TO_DISPLAY.ID, self._ConvertGUGDisplayDataToDisplayTuple, self._ConvertGUGDisplayDataToSortTuple )
        
        self._gug_display_list_ctrl = ClientGUIListCtrl.BetterListCtrlTreeView( self._gug_display_list_ctrl_panel, 15, model, activation_callback = self._EditGUGDisplay )
        
        self._gug_display_list_ctrl_panel.SetListCtrl( self._gug_display_list_ctrl )
        
        self._gug_display_list_ctrl_panel.AddButton( 'edit', self._EditGUGDisplay, enabled_only_on_selection = True )
        
        #
        
        media_viewer_urls_panel = QW.QWidget( self._notebook )
        
        self._url_display_list_ctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( media_viewer_urls_panel )
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_URL_CLASS_KEYS_TO_DISPLAY.ID, self._ConvertURLDisplayDataToDisplayTuple, self._ConvertURLDisplayDataToSortTuple )
        
        self._url_display_list_ctrl = ClientGUIListCtrl.BetterListCtrlTreeView( self._url_display_list_ctrl_panel, 15, model, activation_callback = self._EditURLDisplay )
        
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
        
        QP.AddToLayout( vbox, self._url_display_list_ctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        media_viewer_urls_panel.setLayout( vbox )
        
        #
        
        self._notebook.addTab( self._gug_display_list_ctrl_panel, 'downloaders selector' )
        self._notebook.setCurrentWidget( self._gug_display_list_ctrl_panel )
        self._notebook.addTab( media_viewer_urls_panel, 'media viewer urls' )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
    def _ConvertGUGDisplayDataToDisplayTuple( self, data ):
        
        ( gug_key, display ) = data
        
        gug = self._gug_keys_to_gugs[ gug_key ]
        
        name = gug.GetName()
        
        pretty_name = name
        
        if display:
            
            pretty_display = 'yes'
            
        else:
            
            pretty_display = 'no'
            
        
        return ( pretty_name, pretty_display )
        
    
    def _ConvertGUGDisplayDataToSortTuple( self, data ):
        
        ( gug_key, display ) = data
        
        gug = self._gug_keys_to_gugs[ gug_key ]
        
        name = gug.GetName()
        
        return ( name, display )
        
    
    def _ConvertURLDisplayDataToDisplayTuple( self, data ):
        
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
            
        
        return ( pretty_name, pretty_url_type, pretty_display )
        
    
    def _ConvertURLDisplayDataToSortTuple( self, data ):
        
        ( url_class_key, display ) = data
        
        url_class = self._url_class_keys_to_url_classes[ url_class_key ]
        
        url_class_name = url_class.GetName()
        url_type = url_class.GetURLType()
        
        pretty_url_type = HC.url_type_string_lookup[ url_type ]
        
        return ( url_class_name, pretty_url_type, display )
        
    
    def _EditGUGDisplay( self ):
        
        gug_keys_and_displays = self._gug_display_list_ctrl.GetData( only_selected = True )
        
        if len( gug_keys_and_displays ) == 0:
            
            return
            
        
        names = [ self._gug_keys_to_gugs[ gug_key_and_display[0] ].GetName() for gug_key_and_display in gug_keys_and_displays ]
        
        message = f'Show{HydrusText.ConvertManyStringsToNiceInsertableHumanSummary( names )}in the main selector list?'
        
        ( result, closed_by_user ) = ClientGUIDialogsQuick.GetYesNo( self, message, title = 'Show in the first list?', check_for_cancelled = True )
        
        if closed_by_user:
            
            return
            
        
        should_display = result == QW.QDialog.DialogCode.Accepted
        
        replacement_tuples = []
        
        for gug_key_and_display in gug_keys_and_displays:
            
            new_gug_key_and_display = ( gug_key_and_display[0], should_display )
            
            replacement_tuples.append( ( gug_key_and_display, new_gug_key_and_display ) )
            
        
        self._gug_display_list_ctrl.ReplaceDatas( replacement_tuples, sort_and_scroll = True )
        
    
    def _EditURLDisplay( self ):
        
        url_class_keys_and_displays = self._url_display_list_ctrl.GetData( only_selected = True )
        
        if len( url_class_keys_and_displays ) == 0:
            
            return
            
        
        names = [ self._url_class_keys_to_url_classes[ url_class_key_and_display[0] ].GetName() for url_class_key_and_display in url_class_keys_and_displays ]
        
        message = f'Show{HydrusText.ConvertManyStringsToNiceInsertableHumanSummary( names )}in the media viewer?'
        
        ( result, closed_by_user ) = ClientGUIDialogsQuick.GetYesNo( self, message, title = 'Show in the media viewer?', check_for_cancelled = True )
        
        if closed_by_user:
            
            return
            
        
        should_display = result == QW.QDialog.DialogCode.Accepted
        
        replacement_tuples = []
        
        for url_class_key_and_display in url_class_keys_and_displays:
            
            new_url_class_key_and_display = ( url_class_key_and_display[0], should_display )
            
            replacement_tuples.append( ( url_class_key_and_display, new_url_class_key_and_display ) )
            
        
        self._url_display_list_ctrl.ReplaceDatas( replacement_tuples, sort_and_scroll = True )
        
    
    def GetValue( self ):
        
        gug_keys_to_display = { gug_key for ( gug_key, display ) in self._gug_display_list_ctrl.GetData() if display }
        url_class_keys_to_display = { url_class_key for ( url_class_key, display ) in self._url_display_list_ctrl.GetData() if display }
        
        show_unmatched_urls_in_media_viewer = self._show_unmatched_urls_in_media_viewer.isChecked()
        
        return ( gug_keys_to_display, url_class_keys_to_display, show_unmatched_urls_in_media_viewer )
        
    
class EditGUGPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, gug: ClientNetworkingGUG.GalleryURLGenerator ):
        
        super().__init__( parent )
        
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
        self._example_url.setToolTip( ClientGUIFunctions.WrapToolTip( 'This is the raw URL generated by the GUG template.' ) )
        
        self._normalised_url = QW.QLineEdit( self )
        self._normalised_url.setReadOnly( True )
        self._normalised_url.setToolTip( ClientGUIFunctions.WrapToolTip( 'This is the Request URL--what will be sent to the server, with any additional normalisation the matching URL Class will add.' ) )
        
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
        rows.append( ( 'raw url: ', self._example_url ) )
        rows.append( ( 'matches as a: ', self._matched_url_class ) )
        rows.append( ( 'normalised url: ', self._normalised_url ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.addStretch( 0 )
        
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
            
            ClientNetworkingFunctions.CheckLooksLikeAFullURL( example_url )
            
            self._example_url.setText( example_url )
            
            normalised_url = CG.client_controller.network_engine.domain_manager.NormaliseURL( example_url, for_server = True )
            
            self._normalised_url.setText( normalised_url )
            
        except ( HydrusExceptions.GUGException, HydrusExceptions.URLClassException ) as e:
            
            reason = str( e )
            
            self._example_url.setText( 'Could not generate - ' + reason )
            self._normalised_url.setText( '' )
            
            example_url = None
            
        
        if example_url is None:
            
            self._matched_url_class.clear()
            
        else:
            
            try:
                
                url_class = CG.client_controller.network_engine.domain_manager.GetURLClass( example_url )
                
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
    
    def __init__( self, parent: QW.QWidget, ngug: ClientNetworkingGUG.NestedGalleryURLGenerator, available_gugs: collections.abc.Iterable[ ClientNetworkingGUG.GalleryURLGenerator ] ):
        
        super().__init__( parent )
        
        self._original_ngug = ngug
        self._available_gugs = list( available_gugs )
        
        self._available_gugs.sort( key = lambda g: g.GetName() )
        
        self._name = QW.QLineEdit( self )
        
        self._initial_search_text = QW.QLineEdit( self )
        
        self._gug_list_ctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_NGUG_GUGS.ID, self._ConvertGUGDataToDisplayTuple, self._ConvertGUGDataToSortTuple )
        
        self._gug_list_ctrl = ClientGUIListCtrl.BetterListCtrlTreeView( self._gug_list_ctrl_panel, 8, model, use_simple_delete = True )
        
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
        
        self._gug_list_ctrl.AddData( gug_key_and_name, select_sort_and_scroll = True )
        
    
    def _AddGUGButtonClick( self ):
        
        existing_gug_keys = { gug_key for ( gug_key, gug_name ) in self._gug_list_ctrl.GetData() }
        existing_gug_names = { gug_name for ( gug_key, gug_name ) in self._gug_list_ctrl.GetData() }
        
        choice_tuples = [ ( gug.GetName(), gug, False ) for gug in self._available_gugs if gug.GetName() not in existing_gug_names and gug.GetGUGKey() not in existing_gug_keys ]
        
        if len( choice_tuples ) == 0:
            
            ClientGUIDialogsMessage.ShowWarning( self, 'No remaining gugs available!' )
            
            return
            
        
        try:
            
            chosen_gugs = ClientGUIDialogsQuick.SelectMultipleFromList( self, 'choose gugs', choice_tuples )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        for gug in chosen_gugs:
            
            self._AddGUG( gug )
            
        
    
    def _ConvertGUGDataToDisplayTuple( self, gug_key_and_name ):
        
        ( gug_key, gug_name ) = gug_key_and_name
        
        name = gug_name
        pretty_name = name
        
        available = gug_key in ( gug.GetGUGKey() for gug in self._available_gugs ) or gug_name in ( gug.GetName() for gug in self._available_gugs )
        
        if available:
            
            pretty_available = 'yes'
            
        else:
            
            pretty_available = 'no'
            
        
        return ( pretty_name, pretty_available )
        
    
    def _ConvertGUGDataToSortTuple( self, gug_key_and_name ):
        
        ( gug_key, gug_name ) = gug_key_and_name
        
        name = gug_name
        
        available = gug_key in ( gug.GetGUGKey() for gug in self._available_gugs ) or gug_name in ( gug.GetName() for gug in self._available_gugs )
        
        return ( name, available )
        
    
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
        
        super().__init__( parent )
        
        menu_template_items = []
        
        call = HydrusData.Call( ClientGUIDialogsQuick.OpenDocumentation, self, HC.DOCUMENTATION_DOWNLOADER_GUGS )
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'open the gugs help', 'Open the help page for gugs in your web browser.', call ) )
        
        help_button = ClientGUIMenuButton.MenuIconButton( self, CC.global_icons().help, menu_template_items )
        
        help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help for this panel -->', object_name = 'HydrusIndeterminate' )
        
        #
        
        self._notebook = QW.QTabWidget( self )
        
        #
        
        self._gug_list_ctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self._notebook )
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_GUGS.ID, self._ConvertGUGToDisplayTuple, self._ConvertGUGToSortTuple )
        
        self._gug_list_ctrl = ClientGUIListCtrl.BetterListCtrlTreeView( self._gug_list_ctrl_panel, 30, model, delete_key_callback = self._DeleteGUG, activation_callback = self._EditGUG )
        
        self._gug_list_ctrl_panel.SetListCtrl( self._gug_list_ctrl )
        
        self._gug_list_ctrl_panel.AddButton( 'add', self._AddNewGUG )
        self._gug_list_ctrl_panel.AddButton( 'edit', self._EditGUG, enabled_only_on_single_selection = True )
        self._gug_list_ctrl_panel.AddDeleteButton()
        self._gug_list_ctrl_panel.AddSeparator()
        self._gug_list_ctrl_panel.AddImportExportButtons( ( ClientNetworkingGUG.GalleryURLGenerator, ), self._AddGUG )
        self._gug_list_ctrl_panel.AddSeparator()
        self._gug_list_ctrl_panel.AddDefaultsButton( ClientDefaults.GetDefaultSingleGUGs, self._AddGUG )
        
        #
        
        self._ngug_list_ctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self._notebook )
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_NGUGS.ID, self._ConvertNGUGToDisplayTuple, self._ConvertNGUGToSortTuple )
        
        self._ngug_list_ctrl = ClientGUIListCtrl.BetterListCtrlTreeView( self._ngug_list_ctrl_panel, 20, model, use_simple_delete = True, activation_callback = self._EditNGUG )
        
        self._ngug_list_ctrl_panel.SetListCtrl( self._ngug_list_ctrl )
        
        self._ngug_list_ctrl_panel.AddButton( 'add', self._AddNewNGUG )
        self._ngug_list_ctrl_panel.AddButton( 'edit', self._EditNGUG, enabled_only_on_single_selection = True )
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
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                gug = panel.GetValue()
                
                self._AddGUG( gug, select_sort_and_scroll = True )
                
            
        
    
    def _AddNewNGUG( self ):
        
        ngug = ClientNetworkingGUG.NestedGalleryURLGenerator( 'new nested gallery url generator' )
        
        available_gugs = self._gug_list_ctrl.GetData()
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit nested gallery url generator' ) as dlg:
            
            panel = EditNGUGPanel( dlg, ngug, available_gugs )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                ngug = panel.GetValue()
                
                self._AddNGUG( ngug, select_sort_and_scroll = True )
                
            
        
    
    def _AddGUG( self, gug, select_sort_and_scroll = False ):
        
        HydrusSerialisable.SetNonDupeName( gug, self._GetExistingNames() )
        
        gug.RegenerateGUGKey()
        
        self._gug_list_ctrl.AddData( gug, select_sort_and_scroll = select_sort_and_scroll )
        
    
    def _AddNGUG( self, ngug, select_sort_and_scroll = False ):
        
        HydrusSerialisable.SetNonDupeName( ngug, self._GetExistingNames() )
        
        ngug.RegenerateGUGKey()
        
        self._ngug_list_ctrl.AddData( ngug, select_sort_and_scroll = select_sort_and_scroll )
        
    
    def _ConvertGUGToDisplayTuple( self, gug ):
        
        name = gug.GetName()
        example_url = gug.GetExampleURL()
        
        try:
            
            ClientNetworkingFunctions.CheckLooksLikeAFullURL( example_url )
            
            example_url = CG.client_controller.network_engine.domain_manager.NormaliseURL( example_url, for_server = True )
            
            url_class = CG.client_controller.network_engine.domain_manager.GetURLClass( example_url )
            
        except Exception as e:
            
            example_url = 'unable to parse example url'
            url_class = None
            
        
        if url_class is None:
            
            pretty_gallery_url_class = ''
            
        else:
            
            pretty_gallery_url_class = url_class.GetName()
            
        
        pretty_name = name
        pretty_example_url = example_url
        
        return ( pretty_name, pretty_example_url, pretty_gallery_url_class )
        
    
    _ConvertGUGToSortTuple = _ConvertGUGToDisplayTuple
    
    def _ConvertNGUGToDisplayTuple( self, ngug ):
        
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
            
        
        return ( pretty_name, pretty_gugs, pretty_missing )
        
    
    def _ConvertNGUGToSortTuple( self, ngug ):
        
        existing_names = { gug.GetName() for gug in self._gug_list_ctrl.GetData() }
        
        name = ngug.GetName()
        gugs = ngug.GetGUGNames()
        missing = len( set( gugs ).difference( existing_names ) ) > 0
        
        sort_gugs = len( gugs )
        
        return ( name, sort_gugs, missing )
        
    
    def _DeleteGUG( self ):
        
        ngugs = self._ngug_list_ctrl.GetData()
        
        deletees = self._gug_list_ctrl.GetData( only_selected = True )
        
        result = ClientGUIDialogsQuick.GetYesNo( self, 'Remove all selected?' )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            for deletee in deletees:
                
                deletee_ngug_key = deletee.GetGUGKey()
                
                affected_ngug_names = []
                
                for ngug in ngugs:
                    
                    if deletee_ngug_key in ngug.GetGUGKeys():
                        
                        affected_ngug_names.append( ngug.GetName() )
                        
                    
                
                if len( affected_ngug_names ) > 0:
                    
                    affected_ngug_names.sort()
                    
                    message = 'The GUG "' + deletee.GetName() + '" is in the NGUGs:'
                    message += '\n' * 2
                    message += '\n'.join( affected_ngug_names )
                    message += '\n' * 2
                    message += 'Deleting this GUG will ultimately remove it from those NGUGs--are you sure that is ok?'
                    
                    result = ClientGUIDialogsQuick.GetYesNo( self, message )
                    
                    if result != QW.QDialog.DialogCode.Accepted:
                        
                        break
                        
                    
                
                self._gug_list_ctrl.DeleteDatas( ( deletee, ) )
                
            
        
    
    def _EditGUG( self ):
        
        data = self._gug_list_ctrl.GetTopSelectedData()
        
        if data is None:
            
            return
            
        
        gug: ClientNetworkingGUG.GalleryURLGenerator = data
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit gallery url generator' ) as dlg:
            
            panel = EditGUGPanel( dlg, gug )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                existing_names = self._GetExistingNames()
                existing_names.discard( gug.GetName() )
                
                edited_gug = panel.GetValue()
                
                HydrusSerialisable.SetNonDupeName( edited_gug, existing_names )
                
                self._gug_list_ctrl.ReplaceData( gug, edited_gug, sort_and_scroll = True )
                
            
        
    
    
    def _EditNGUG( self ):
        
        data = self._ngug_list_ctrl.GetTopSelectedData()
        
        if data is None:
            
            return
            
        
        ngug: ClientNetworkingGUG.NestedGalleryURLGenerator = data
        
        available_gugs = self._gug_list_ctrl.GetData()
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit nested gallery url generator' ) as dlg:
            
            panel = EditNGUGPanel( dlg, ngug, available_gugs )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                existing_names = self._GetExistingNames()
                existing_names.discard( ngug.GetName() )
                
                edited_ngug = panel.GetValue()
                
                HydrusSerialisable.SetNonDupeName( edited_ngug, existing_names )
                
                self._ngug_list_ctrl.ReplaceData( ngug, edited_ngug, sort_and_scroll = True )
                
            
        
    
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
        
    

class EditURLClassLinksPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, network_engine, url_classes, parsers, url_class_keys_to_parser_keys ):
        
        super().__init__( parent )
        
        self._url_classes = url_classes
        self._url_class_keys_to_url_classes = { url_class.GetClassKey() : url_class for url_class in self._url_classes }
        
        self._parsers = parsers
        self._parser_keys_to_parsers = { parser.GetParserKey() : parser for parser in self._parsers }
        
        self._network_engine = network_engine
        
        #
        
        self._notebook = QW.QTabWidget( self )
        
        #
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_URL_CLASS_API_PAIRS.ID, self._ConvertAPIPairDataToDisplayTuple, self._ConvertAPIPairDataToSortTuple )
        
        self._api_pairs_list_ctrl = ClientGUIListCtrl.BetterListCtrlTreeView( self._notebook, 10, model )
        
        #
        
        self._parser_list_ctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self._notebook )
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_URL_CLASS_KEYS_TO_PARSER_KEYS.ID, self._ConvertParserDataToDisplayTuple, self._ConvertParserDataToSortTuple )
        
        self._parser_list_ctrl = ClientGUIListCtrl.BetterListCtrlTreeView( self._parser_list_ctrl_panel, 24, model, activation_callback = self._EditParser )
        
        self._parser_list_ctrl_panel.SetListCtrl( self._parser_list_ctrl )
        
        self._parser_list_ctrl_panel.AddButton( 'edit', self._EditParser, enabled_only_on_single_selection = True )
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
        self._notebook.addTab( self._api_pairs_list_ctrl, 'api/redirect link review' )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
    def _ClearParser( self ):
        
        result = ClientGUIDialogsQuick.GetYesNo( self, 'Clear all the selected linked parsers?' )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            replace_tuples = []
            
            for data in self._parser_list_ctrl.GetData( only_selected = True ):
                
                ( url_class_key, parser_key ) = data
                
                new_data = ( url_class_key, None )
                
                replace_tuples.append( ( data, new_data ) )
                
            
            self._parser_list_ctrl.ReplaceDatas( replace_tuples, sort_and_scroll = True )
            
        
    
    def _ConvertAPIPairDataToDisplayTuple( self, data ):
        
        ( a, b ) = data
        
        a_name = a.GetName()
        b_name = b.GetName()
        
        return ( a_name, b_name )
        
    
    _ConvertAPIPairDataToSortTuple = _ConvertAPIPairDataToDisplayTuple
    
    def _ConvertParserDataToDisplayTuple( self, data ):
        
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
        
        return ( pretty_url_class_name, pretty_url_type, pretty_parser_name )
        
    
    _ConvertParserDataToSortTuple = _ConvertParserDataToDisplayTuple
    
    def _EditParser( self ):
        
        if len( self._parsers ) == 0:
            
            ClientGUIDialogsMessage.ShowWarning( self, 'Unfortunately, you do not have any parsers, so none can be linked to your url classes. Please create some!' )
            
            return
            
        
        data = self._parser_list_ctrl.GetTopSelectedData()
        
        if data is None:
            
            return
            
        
        ( url_class_key, parser_key ) = data
        
        url_class = self._url_class_keys_to_url_classes[ url_class_key ]
        default_parser = self._parser_keys_to_parsers.get( parser_key, None )
        
        matching_parsers = [ parser for parser in self._parsers if True in ( url_class.Matches( url ) for url in parser.GetExampleURLs() ) ]
        unmatching_parsers = [ parser for parser in self._parsers if parser not in matching_parsers ]
        
        matching_parsers.sort( key = lambda p: p.GetName() )
        unmatching_parsers.sort( key = lambda p: p.GetName() )
        
        choice_tuples = [ ( parser.GetName(), parser ) for parser in matching_parsers ]
        choice_tuples.append( ( '------', None ) )
        choice_tuples.extend( [ ( parser.GetName(), parser ) for parser in unmatching_parsers ] )
        
        try:
            
            parser = ClientGUIDialogsQuick.SelectFromList( self, 'select parser for ' + url_class.GetName(), choice_tuples, sort_tuples = False, value_to_select = default_parser )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        if parser is None:
            
            return
            
        
        new_data = ( url_class_key, parser.GetParserKey() )
        
        self._parser_list_ctrl.ReplaceData( data, new_data, sort_and_scroll = True )
        
    
    def _GapsExist( self ):
        
        return None in ( parser_key for ( url_class_key, parser_key ) in self._parser_list_ctrl.GetData() )
        
    
    def _LinksOnCurrentSelection( self ):
        
        non_none_parser_keys = [ parser_key for ( url_class_key, parser_key ) in self._parser_list_ctrl.GetData( only_selected = True ) if parser_key is not None ]
        
        return len( non_none_parser_keys ) > 0
        
    
    def _TryToLinkURLClassesAndParsers( self ):
        
        existing_url_class_keys_to_parser_keys = { url_class_key : parser_key for ( url_class_key, parser_key ) in self._parser_list_ctrl.GetData() if parser_key is not None }
        
        new_url_class_keys_to_parser_keys = ClientNetworkingDomain.NetworkDomainManager.STATICLinkURLClassesAndParsers( self._url_classes, self._parsers, existing_url_class_keys_to_parser_keys )
        
        if len( new_url_class_keys_to_parser_keys ) > 0:
            
            replacement_tuples = []
            
            for row in existing_url_class_keys_to_parser_keys.items():
                
                ( url_class_key, parser_key ) = row
                
                if url_class_key in new_url_class_keys_to_parser_keys:
                    
                    replacement_tuples.append( ( row, ( url_class_key, new_url_class_keys_to_parser_keys[ url_class_key ] ) ) )
                    
                
            
            self._parser_list_ctrl.ReplaceDatas( replacement_tuples, sort_and_scroll = True )
            
        
    
    def GetValue( self ):
        
        url_class_keys_to_parser_keys = { url_class_key : parser_key for ( url_class_key, parser_key ) in self._parser_list_ctrl.GetData() if parser_key is not None }
        
        return url_class_keys_to_parser_keys
        
    
