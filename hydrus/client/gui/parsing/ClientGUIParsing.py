import collections.abc
import itertools
import traceback

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusSerialisable

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientDefaults
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientStrings
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUISerialisable
from hydrus.client.gui import ClientGUIStringControls
from hydrus.client.gui import ClientGUIStringPanels
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListBoxes
from hydrus.client.gui.lists import ClientGUIListConstants as CGLC
from hydrus.client.gui.lists import ClientGUIListCtrl
from hydrus.client.gui.networking import ClientGUINetworkJobControl
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.parsing import ClientGUIParsingFormulae
from hydrus.client.gui.parsing import ClientGUIParsingTest
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.gui.widgets import ClientGUIMenuButton
from hydrus.client.networking import ClientNetworkingContexts
from hydrus.client.networking import ClientNetworkingDomain
from hydrus.client.networking import ClientNetworkingFunctions
from hydrus.client.networking import ClientNetworkingGUG
from hydrus.client.networking import ClientNetworkingJobs
from hydrus.client.networking import ClientNetworkingURLClass
from hydrus.client.parsing import ClientParsing
from hydrus.client.parsing import ClientParsingResults

class DownloaderExportPanel( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent, network_engine ):
        
        super().__init__( parent )
        
        self._network_engine = network_engine
        
        menu_template_items = []
        
        page_func = HydrusData.Call( ClientGUIDialogsQuick.OpenDocumentation, self, HC.DOCUMENTATION_DOWNLOADER_SHARING )
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'open the downloader sharing help', 'Open the help page for sharing downloaders in your web browser.', page_func ) )
        
        help_button = ClientGUIMenuButton.MenuIconButton( self, CC.global_icons().help, menu_template_items )
        
        help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help for this panel -->', object_name = 'HydrusIndeterminate' )
        
        listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_DOWNLOADER_EXPORT.ID, self._ConvertContentToDisplayTuple, self._ConvertContentToSortTuple )
        
        self._listctrl = ClientGUIListCtrl.BetterListCtrlTreeView( listctrl_panel, 14, model, use_simple_delete = True )
        
        self._listctrl.Sort()
        
        listctrl_panel.SetListCtrl( self._listctrl )
        
        listctrl_panel.AddButton( 'add gug', self._AddGUG )
        listctrl_panel.AddButton( 'add url class', self._AddURLClass )
        listctrl_panel.AddButton( 'add parser', self._AddParser )
        listctrl_panel.AddButton( 'add login script', self._AddLoginScript )
        listctrl_panel.AddButton( 'add headers/bandwidth rules', self._AddDomainMetadata )
        listctrl_panel.AddDeleteButton()
        listctrl_panel.AddSeparator()
        listctrl_panel.AddButton( 'export to png', self._Export, enabled_check_func = self._CanExport )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, help_hbox, CC.FLAGS_ON_RIGHT )
        QP.AddToLayout( vbox, listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
    def _AddDomainMetadata( self ):
        
        message = 'Enter domain.'
        
        try:
            
            domain = ClientGUIDialogsQuick.EnterText( self, message )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        domain_metadatas = self._GetDomainMetadatasToInclude( { domain } )
        
        if len( domain_metadatas ) > 0:
            
            self._listctrl.AddDatas( domain_metadatas )
            
        else:
            
            ClientGUIDialogsMessage.ShowInformation( self, 'No headers/bandwidth rules found!' )
            
        
    
    def _AddGUG( self ):
        
        existing_data = self._listctrl.GetData()
        
        choosable_gugs = [ gug for gug in self._network_engine.domain_manager.GetGUGs() if gug.IsFunctional() and gug not in existing_data ]
        
        choice_tuples = [ ( gug.GetName(), gug, False ) for gug in choosable_gugs ]
        
        try:
            
            gugs_to_include = ClientGUIDialogsQuick.SelectMultipleFromList( self, 'select gugs', choice_tuples )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        gugs_to_include = self._FleshOutNGUGsWithGUGs( gugs_to_include )
        
        domains = { ClientNetworkingFunctions.ConvertURLIntoDomain( example_url ) for example_url in itertools.chain.from_iterable( ( gug.GetExampleURLs() for gug in gugs_to_include ) ) }
        
        domain_metadatas_to_include = self._GetDomainMetadatasToInclude( domains )
        
        url_classes_to_include = self._GetURLClassesToInclude( gugs_to_include )
        
        url_classes_to_include = self._FleshOutURLClassesWithAPILinks( url_classes_to_include )
        
        parsers_to_include = self._GetParsersToInclude( url_classes_to_include )
        
        self._listctrl.AddDatas( domain_metadatas_to_include )
        self._listctrl.AddDatas( gugs_to_include )
        self._listctrl.AddDatas( url_classes_to_include )
        self._listctrl.AddDatas( parsers_to_include )
        
    
    def _AddLoginScript( self ):
        
        existing_data = self._listctrl.GetData()
        
        choosable_login_scripts = [ ls for ls in self._network_engine.login_manager.GetLoginScripts() if ls not in existing_data ]
        
        choice_tuples = [ ( login_script.GetName(), login_script, False ) for login_script in choosable_login_scripts ]
        
        try:
            
            login_scripts_to_include = ClientGUIDialogsQuick.SelectMultipleFromList( self, 'select login scripts', choice_tuples )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        self._listctrl.AddDatas( login_scripts_to_include )
        
    
    def _AddParser( self ):
        
        existing_data = self._listctrl.GetData()
        
        choosable_parsers = [ p for p in self._network_engine.domain_manager.GetParsers() if p not in existing_data ]
        
        choice_tuples = [ ( parser.GetName(), parser, False ) for parser in choosable_parsers ]
        
        try:
            
            parsers_to_include = ClientGUIDialogsQuick.SelectMultipleFromList( self, 'select parsers to include', choice_tuples )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        self._listctrl.AddDatas( parsers_to_include )
        
    
    def _AddURLClass( self ):
        
        existing_data = self._listctrl.GetData()
        
        choosable_url_classes = [ u for u in self._network_engine.domain_manager.GetURLClasses() if u not in existing_data ]
        
        choice_tuples = [ ( url_class.GetName(), url_class, False ) for url_class in choosable_url_classes ]
        
        try:
            
            url_classes_to_include = ClientGUIDialogsQuick.SelectMultipleFromList( self, 'select url classes to include', choice_tuples )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        url_classes_to_include = self._FleshOutURLClassesWithAPILinks( url_classes_to_include )
        
        parsers_to_include = self._GetParsersToInclude( url_classes_to_include )
        
        self._listctrl.AddDatas( url_classes_to_include )
        self._listctrl.AddDatas( parsers_to_include )
        
    
    def _CanExport( self ):
        
        return len( self._listctrl.GetData() ) > 0
        
    
    def _ConvertContentToDisplayTuple( self, content ):
        
        if isinstance( content, ClientNetworkingDomain.DomainMetadataPackage ):
            
            name = content.GetDomain()
            
        else:
            
            name = content.GetName()
            
        
        t = content.SERIALISABLE_NAME
        
        return ( name, t )
        
    
    _ConvertContentToSortTuple = _ConvertContentToDisplayTuple
    
    def _Export( self ):
        
        export_object = HydrusSerialisable.SerialisableList( self._listctrl.GetData() )
        
        message = 'The end-user will see this sort of summary:'
        message += '\n' * 2
        message += '\n'.join( ( obj.GetSafeSummary() for obj in export_object[:20] ) )
        
        if len( export_object ) > 20:
            
            message += '\n'
            message += '(and ' + HydrusNumbers.ToHumanInt( len( export_object ) - 20 ) + ' others)'
            
        
        message += '\n' * 2
        message += 'Does that look good? (Ideally, every object should have correct and sane domains listed here)'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result != QW.QDialog.DialogCode.Accepted:
            
            return
            
        
        gug_names = set()
        
        for obj in export_object:
            
            if isinstance( obj, ( ClientNetworkingGUG.GalleryURLGenerator, ClientNetworkingGUG.NestedGalleryURLGenerator ) ):
                
                gug_names.add( obj.GetName() )
                
            
        
        gug_names = sorted( gug_names )
        
        num_gugs = len( gug_names )
        
        with ClientGUITopLevelWindowsPanels.DialogNullipotent( self, 'export to png' ) as dlg:
            
            title = 'easy-import downloader png'
            
            if num_gugs == 0:
                
                description = 'some download components'
                
            else:
                
                title += ' - ' + HydrusNumbers.ToHumanInt( num_gugs ) + ' downloaders'
                
                description = ', '.join( gug_names )
                
            
            panel = ClientGUISerialisable.PNGExportPanel( dlg, export_object, title = title, description = description )
            
            dlg.SetPanel( panel )
            
            dlg.exec()
            
        
    
    def _FleshOutNGUGsWithGUGs( self, gugs ):
        
        gugs_to_include = set( gugs )
        
        existing_data = self._listctrl.GetData()
        
        possible_new_gugs = [ gug for gug in self._network_engine.domain_manager.GetGUGs() if gug.IsFunctional() and gug not in existing_data and gug not in gugs_to_include ]
        
        interesting_gug_keys_and_names = list( itertools.chain.from_iterable( [ gug.GetGUGKeysAndNames() for gug in gugs_to_include if isinstance( gug, ClientNetworkingGUG.NestedGalleryURLGenerator ) ] ) )
        
        interesting_gugs = [ gug for gug in possible_new_gugs if gug.GetGUGKeyAndName() in interesting_gug_keys_and_names ]
        
        gugs_to_include.update( interesting_gugs )
        
        if True in ( isinstance( gug, ClientNetworkingGUG.NestedGalleryURLGenerator ) for gug in interesting_gugs ):
            
            return self._FleshOutNGUGsWithGUGs( gugs_to_include )
            
        else:
            
            return gugs_to_include
            
        
    
    def _FleshOutURLClassesWithAPILinks( self, url_classes ):
        
        url_classes_to_include = set( url_classes )
        
        api_links_dict = dict( ClientNetworkingURLClass.ConvertURLClassesIntoAPIPairs( self._network_engine.domain_manager.GetURLClasses() ) )
        
        for url_class in url_classes:
            
            added_this_cycle = set()
            
            while url_class in api_links_dict and url_class not in added_this_cycle:
                
                added_this_cycle.add( url_class )
                
                url_class = api_links_dict[ url_class ]
                
                url_classes_to_include.add( url_class )
                
            
        
        existing_data = self._listctrl.GetData()
        
        url_classes_to_include = [ u for u in url_classes_to_include if u not in existing_data ]
        
        return url_classes_to_include
        
    
    def _GetDomainMetadatasToInclude( self, domains ):
        
        domains = { d for d in itertools.chain.from_iterable( ClientNetworkingFunctions.ConvertDomainIntoAllApplicableDomains( domain ) for domain in domains ) }
        
        existing_domains = { obj.GetDomain() for obj in self._listctrl.GetData() if isinstance( obj, ClientNetworkingDomain.DomainMetadataPackage ) }
        
        domains = domains.difference( existing_domains )
        
        domains = sorted( domains )
        
        domain_metadatas = []
        
        for domain in domains:
            
            network_context = ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_DOMAIN, domain )
            
            if self._network_engine.domain_manager.HasCustomHeaders( network_context ):
                
                headers_list = self._network_engine.domain_manager.GetShareableCustomHeaders( network_context )
                
            else:
                
                headers_list = None
                
            
            if self._network_engine.bandwidth_manager.HasRules( network_context ):
                
                bandwidth_rules = self._network_engine.bandwidth_manager.GetRules( network_context )
                
            else:
                
                bandwidth_rules = None
                
            
            if headers_list is not None or bandwidth_rules is not None:
                
                domain_metadata = ClientNetworkingDomain.DomainMetadataPackage( domain = domain, headers_list = headers_list, bandwidth_rules = bandwidth_rules )
                
                domain_metadatas.append( domain_metadata )
                
            
        
        for domain_metadata in domain_metadatas:
            
            ClientGUIDialogsMessage.ShowInformation( self, domain_metadata.GetDetailedSafeSummary() )
            
        
        return domain_metadatas
        
    
    def _GetParsersToInclude( self, url_classes ):
        
        parsers_to_include = set()
        
        for url_class in url_classes:
            
            example_url = url_class.GetExampleURL()
            
            ( url_type, match_name, can_parse, cannot_parse_reason ) = self._network_engine.domain_manager.GetURLParseCapability( example_url )
            
            if can_parse:
                
                try:
                    
                    ( url_to_fetch, parser ) = self._network_engine.domain_manager.GetURLToFetchAndParser( example_url )
                    
                    parsers_to_include.add( parser )
                    
                except Exception as e:
                    
                    pass
                    
                
            
        
        existing_data = self._listctrl.GetData()
        
        return [ p for p in parsers_to_include if p not in existing_data ]
        
    
    def _GetURLClassesToInclude( self, gugs ):
        
        url_classes_to_include = set()
        
        for gug in gugs:
            
            if isinstance( gug, ClientNetworkingGUG.GalleryURLGenerator ):
                
                example_urls = ( gug.GetExampleURL(), )
                
            elif isinstance( gug, ClientNetworkingGUG.NestedGalleryURLGenerator ):
                
                example_urls = gug.GetExampleURLs()
                
            
            for example_url in example_urls:
                
                try:
                    
                    url_class = self._network_engine.domain_manager.GetURLClass( example_url )
                    
                except HydrusExceptions.URLClassException:
                    
                    continue
                    
                
                if url_class is not None:
                    
                    url_classes_to_include.add( url_class )
                    
                    # add post url matches from same domain
                    
                    domain = ClientNetworkingFunctions.ConvertURLIntoSecondLevelDomain( example_url )
                    
                    for um in list( self._network_engine.domain_manager.GetURLClasses() ):
                        
                        if ClientNetworkingFunctions.ConvertURLIntoSecondLevelDomain( um.GetExampleURL() ) == domain and um.GetURLType() in ( HC.URL_TYPE_POST, HC.URL_TYPE_FILE ):
                            
                            url_classes_to_include.add( um )
                            
                        
                    
                
            
        
        existing_data = self._listctrl.GetData()
        
        return [ u for u in url_classes_to_include if u not in existing_data ]
        
    
class EditContentParserPanel( ClientGUIScrolledPanels.EditPanel ):
    
    contentTypeChanged = QC.Signal( int )
    
    def __init__( self, parent: QW.QWidget, content_parser: ClientParsing.ContentParser, test_data: ClientParsing.ParsingTestData, permitted_content_types ):
        
        self._original_content_parser = content_parser
        
        super().__init__( parent )
        
        #
        
        menu_template_items = []
        
        page_func = HydrusData.Call( ClientGUIDialogsQuick.OpenDocumentation, self, HC.DOCUMENTATION_DOWNLOADER_PARSERS_CONTENT_PARSERS_CONTENT_PARSERS )
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'open the content parsers help', 'Open the help page for content parsers in your web browser.', page_func ) )
        
        help_button = ClientGUIMenuButton.MenuIconButton( self, CC.global_icons().help, menu_template_items )
        
        help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help for this panel -->', object_name = 'HydrusIndeterminate' )
        
        #
        
        test_panel = ClientGUICommon.StaticBox( self, 'test' )
        
        self._test_panel = ClientGUIParsingTest.TestPanel( test_panel, self.GetValue, test_data = test_data )
        
        #
        
        self._edit_panel = ClientGUICommon.StaticBox( self, 'edit' )
        
        self._name = QW.QLineEdit( self._edit_panel )
        
        self._content_panel = ClientGUICommon.StaticBox( self._edit_panel, 'content type' )
        
        self._content_type = ClientGUICommon.BetterChoice( self._content_panel )
        
        types_to_str = {}
        
        types_to_str[ HC.CONTENT_TYPE_URLS ] = 'urls'
        types_to_str[ HC.CONTENT_TYPE_MAPPINGS ] = 'tags'
        types_to_str[ HC.CONTENT_TYPE_NOTES ] = 'notes'
        types_to_str[ HC.CONTENT_TYPE_HASH ] = 'file hash'
        types_to_str[ HC.CONTENT_TYPE_TIMESTAMP ] = 'timestamp'
        types_to_str[ HC.CONTENT_TYPE_TITLE ] = 'watcher title'
        types_to_str[ HC.CONTENT_TYPE_HTTP_HEADERS ] = 'http headers'
        types_to_str[ HC.CONTENT_TYPE_VETO ] = 'veto'
        types_to_str[ HC.CONTENT_TYPE_VARIABLE ] = 'temporary variable'
        
        for permitted_content_type in permitted_content_types:
            
            self._content_type.addItem( types_to_str[ permitted_content_type ], permitted_content_type )
            
        
        self._content_type.currentIndexChanged.connect( self.EventContentTypeChange )
        
        #
        
        self._urls_panel = QW.QWidget( self._content_panel )
        
        self._url_type = ClientGUICommon.BetterChoice( self._urls_panel )
        
        self._url_type.addItem( 'url to download/pursue (file/post url)', HC.URL_TYPE_DESIRED )
        self._url_type.addItem( 'POST parsers only: url to associate (source url)', HC.URL_TYPE_SOURCE )
        self._url_type.addItem( 'GALLERY parsers only: next gallery page (not queued if no post/file urls found)', HC.URL_TYPE_NEXT )
        self._url_type.addItem( 'GALLERY parsers only: sub-gallery page (is queued even if no post/file urls found--be careful, only use if you know you need it)', HC.URL_TYPE_SUB_GALLERY )
        
        self._file_priority = ClientGUICommon.BetterSpinBox( self._urls_panel, min=0, max=100 )
        self._file_priority.setValue( 50 )
        
        #
        
        self._mappings_panel = QW.QWidget( self._content_panel )
        
        self._namespace = ClientGUICommon.NoneableTextCtrl( self._mappings_panel, '', none_phrase = 'any namespace' )
        tt = 'The difference between "any namespace" and setting an empty input (for "unnamespaced") is "unnamespaced" will force unnamespaced, even, magically, if the parsed tag includes a colon. If you are parsing hydrus content and expect to see "namespace:subtag", hit "any namespace", and if you are parsing normal boorus that might have a colon in for weird reasons, try "unnamespaced".'
        self._namespace.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        #
        
        self._notes_panel = QW.QWidget( self._content_panel )
        
        self._note_name = QW.QLineEdit( self._notes_panel )
        
        #
        
        self._hash_panel = QW.QWidget( self._content_panel )
        
        self._hash_type = ClientGUICommon.BetterChoice( self._hash_panel )
        
        for hash_type in ( 'md5', 'sha1', 'sha256', 'sha512' ):
            
            self._hash_type.addItem( hash_type, hash_type )
            
        
        self._hash_encoding = ClientGUICommon.BetterChoice( self._hash_panel )
        
        for hash_encoding in ( 'hex', 'base64' ):
            
            self._hash_encoding.addItem( hash_encoding, hash_encoding )
            
        
        #
        
        self._timestamp_panel = QW.QWidget( self._content_panel )
        
        self._timestamp_type = ClientGUICommon.BetterChoice( self._timestamp_panel )
        
        self._timestamp_type.addItem( 'source time', HC.TIMESTAMP_TYPE_MODIFIED_DOMAIN )
        
        #
        
        self._title_panel = QW.QWidget( self._content_panel )
        
        self._title_priority = ClientGUICommon.BetterSpinBox( self._title_panel, min=0, max=100 )
        self._title_priority.setValue( 50 )
        
        #
        
        self._header_panel = QW.QWidget( self._content_panel )
        
        self._header_name = QW.QLineEdit( self._header_panel )
        tt = 'Any header you parse here will be passed on to subsequent jobs/objects created by this same parse. Next gallery pages, file downloads from post urls, post pages spawned from multi-file posts. And the headers will be passed on to their children. Should help with tokenised searches or weird guest-login issues.'
        self._header_name.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        #
        
        self._veto_panel = QW.QWidget( self._content_panel )
        
        self._veto_if_matches_found = QW.QCheckBox( self._veto_panel )
        self._string_match = ClientGUIStringPanels.EditStringMatchPanel( self._veto_panel, ClientStrings.StringMatch() )
        
        #
        
        self._temp_variable_panel = QW.QWidget( self._content_panel )
        
        self._temp_variable_name = QW.QLineEdit( self._temp_variable_panel )
        
        #
        
        ( name, content_type, formula, additional_info ) = content_parser.ToTuple()
        
        self._formula = ClientGUIParsingFormulae.EditFormulaPanel( self._edit_panel, formula, self._test_panel.GetTestDataForChild )
        
        #
        
        self._name.setText( name )
        
        self._content_type.SetValue( content_type )
        
        if content_type == HC.CONTENT_TYPE_URLS:
            
            ( url_type, priority ) = additional_info
            
            self._url_type.SetValue( url_type )
            self._file_priority.setValue( priority )
            
        elif content_type == HC.CONTENT_TYPE_MAPPINGS:
            
            namespace = additional_info
            
            self._namespace.SetValue( namespace )
            
        elif content_type == HC.CONTENT_TYPE_NOTES:
            
            note_name = additional_info
            
            self._note_name.setText( note_name )
            
        elif content_type == HC.CONTENT_TYPE_HASH:
            
            ( hash_type, hash_encoding ) = additional_info
            
            self._hash_type.SetValue( hash_type )
            self._hash_encoding.SetValue( hash_encoding )
            
        elif content_type == HC.CONTENT_TYPE_TIMESTAMP:
            
            timestamp_type = additional_info
            
            self._timestamp_type.SetValue( timestamp_type )
            
        elif content_type == HC.CONTENT_TYPE_TITLE:
            
            priority = additional_info
            
            self._title_priority.setValue( priority )
            
        elif content_type == HC.CONTENT_TYPE_HTTP_HEADERS:
            
            header_name = additional_info
            
            self._header_name.setText( header_name )
            
        elif content_type == HC.CONTENT_TYPE_VETO:
            
            ( veto_if_matches_found, string_match ) = additional_info
            
            self._veto_if_matches_found.setChecked( veto_if_matches_found )
            self._string_match.SetValue( string_match )
            
        elif content_type == HC.CONTENT_TYPE_VARIABLE:
            
            temp_variable_name = additional_info
            
            self._temp_variable_name.setText( temp_variable_name )
            
        
        #
        
        rows = []
        
        rows.append( ( 'url type: ', self._url_type ) )
        rows.append( ( 'url quality precedence (higher is better): ', self._file_priority ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._urls_panel, rows )
        
        self._urls_panel.setLayout( gridbox )
        
        #
        
        rows = []
        
        rows.append( ( 'namespace: ', self._namespace ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._mappings_panel, rows )
        
        self._mappings_panel.setLayout( gridbox )
        
        #
        
        rows = []
        
        rows.append( ( 'note name: ', self._note_name ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._notes_panel, rows )
        
        vbox = QP.VBoxLayout()
        
        label = 'Try to make sure you will only ever parse one text result here. A single content parser with a single note name producing eleven different note texts is going to be conflict hell for the user at the end.'
        
        st = ClientGUICommon.BetterStaticText( self._notes_panel, label = label )
        
        st.setWordWrap( True )
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self._notes_panel.setLayout( vbox )
        
        #
        
        rows = []
        
        rows.append( ( 'hash type: ', self._hash_type ) )
        rows.append( ( 'hash encoding: ', self._hash_encoding ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._hash_panel, rows )
        
        self._hash_panel.setLayout( gridbox )
        
        #
        
        rows = []
        
        rows.append( ( 'timestamp type: ', self._timestamp_type ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._timestamp_panel, rows )
        
        self._timestamp_panel.setLayout( gridbox )
        
        #
        
        rows = []
        
        rows.append( ( 'title precedence (higher is better): ', self._title_priority ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._title_panel, rows )
        
        self._title_panel.setLayout( gridbox )
        
        #
        self._urls_panel.setLayout( gridbox )
        rows = []
        
        rows.append( ( 'header name: ', self._header_name ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._header_panel, rows )
        
        vbox = QP.VBoxLayout()
        
        label = 'The value from this content parser will be used for the specified HTTP header on all URLs derived.'

        st = ClientGUICommon.BetterStaticText( self._header_panel, label = label )
        
        st.setWordWrap( True )
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self._header_panel.setLayout( vbox )
        
        #
        
        vbox = QP.VBoxLayout()
        
        rows = []
        
        rows.append( ( 'veto if match found (OFF means \'veto if match not found\'): ', self._veto_if_matches_found ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._veto_panel, rows )
        
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, self._string_match, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self._veto_panel.setLayout( vbox )
        
        #
        
        vbox = QP.VBoxLayout()
        
        rows = []
        
        rows.append( ( 'variable name: ', self._temp_variable_name ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._temp_variable_panel, rows )
        
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self._temp_variable_panel.setLayout( vbox )
        
        #
        
        rows = []
        
        rows.append( ( 'content type: ', self._content_type ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._content_panel, rows )
        
        self._content_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._content_panel.Add( self._urls_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._content_panel.Add( self._mappings_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._content_panel.Add( self._notes_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._content_panel.Add( self._hash_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._content_panel.Add( self._timestamp_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._content_panel.Add( self._title_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._content_panel.Add( self._header_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._content_panel.Add( self._veto_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._content_panel.Add( self._temp_variable_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        vbox = QP.VBoxLayout()
        
        rows = []
        
        rows.append( ( 'name or description (optional): ', self._name ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._edit_panel, rows )
        
        self._edit_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._edit_panel.Add( self._content_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._edit_panel.Add( self._formula, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        test_panel.Add( self._test_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._edit_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, test_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, help_hbox, CC.FLAGS_ON_RIGHT )
        QP.AddToLayout( vbox, hbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
        self.EventContentTypeChange( None )
        
    
    def EventContentTypeChange( self, index ):
        
        content_type = self._content_type.GetValue()
        
        self._urls_panel.setVisible( False )
        self._mappings_panel.setVisible( False )
        self._notes_panel.setVisible( False )
        self._hash_panel.setVisible( False )
        self._timestamp_panel.setVisible( False )
        self._title_panel.setVisible( False )
        self._header_panel.setVisible( False )
        self._veto_panel.setVisible( False )
        self._temp_variable_panel.setVisible( False )
        
        collapse_newlines = content_type != HC.CONTENT_TYPE_NOTES
        
        self._test_panel.SetCollapseNewlines( collapse_newlines )
        self._formula.SetCollapseNewlines( collapse_newlines )
        
        if content_type == HC.CONTENT_TYPE_URLS:
            
            self._urls_panel.show()
            
        elif content_type == HC.CONTENT_TYPE_MAPPINGS:
            
            self._mappings_panel.show()
            
        elif content_type == HC.CONTENT_TYPE_NOTES:
            
            self._notes_panel.show()
            
        elif content_type == HC.CONTENT_TYPE_HASH:
            
            self._hash_panel.show()
            
        elif content_type == HC.CONTENT_TYPE_TIMESTAMP:
            
            self._timestamp_panel.show()
            
        elif content_type == HC.CONTENT_TYPE_TITLE:
            
            self._title_panel.show()
            
        elif content_type == HC.CONTENT_TYPE_HTTP_HEADERS:
            
            self._header_panel.show()
            
        elif content_type == HC.CONTENT_TYPE_VETO:
            
            self._veto_panel.show()
            
        elif content_type == HC.CONTENT_TYPE_VARIABLE:
            
            self._temp_variable_panel.show()
            
        
        self.contentTypeChanged.emit( content_type )
        
    
    def GetValue( self ):
        
        name = self._name.text()
        
        content_type = self._content_type.GetValue()
        
        formula = self._formula.GetValue()
        
        if content_type == HC.CONTENT_TYPE_URLS:
            
            url_type = self._url_type.GetValue()
            priority = self._file_priority.value()
            
            additional_info = ( url_type, priority )
            
        elif content_type == HC.CONTENT_TYPE_MAPPINGS:
            
            namespace = self._namespace.GetValue()
            
            additional_info = namespace
            
        elif content_type == HC.CONTENT_TYPE_NOTES:
            
            note_name = self._note_name.text()
            
            if note_name == '':
                
                note_name = 'note'
                
            
            additional_info = note_name
            
        elif content_type == HC.CONTENT_TYPE_HASH:
            
            hash_type = self._hash_type.GetValue()
            hash_encoding = self._hash_encoding.GetValue()
            
            additional_info = ( hash_type, hash_encoding )
            
        elif content_type == HC.CONTENT_TYPE_TIMESTAMP:
            
            timestamp_type = self._timestamp_type.GetValue()
            
            additional_info = timestamp_type
            
        elif content_type == HC.CONTENT_TYPE_TITLE:
            
            priority = self._title_priority.value()
            
            additional_info = priority
            
        elif content_type == HC.CONTENT_TYPE_HTTP_HEADERS:
            
            header_name = self._header_name.text()
            
            additional_info = header_name
            
        elif content_type == HC.CONTENT_TYPE_VETO:
            
            veto_if_matches_found = self._veto_if_matches_found.isChecked()
            string_match = self._string_match.GetValue()
            
            additional_info = ( veto_if_matches_found, string_match )
            
        elif content_type == HC.CONTENT_TYPE_VARIABLE:
            
            temp_variable_name = self._temp_variable_name.text()
            
            additional_info = temp_variable_name
            
        
        content_parser = ClientParsing.ContentParser( name = name, content_type = content_type, formula = formula, additional_info = additional_info )
        
        return content_parser
        
    
    def UserIsOKToCancel( self ):
        
        if self._original_content_parser.GetSerialisableTuple() != self.GetValue().GetSerialisableTuple():
            
            text = 'It looks like you have made changes to the content parser--are you sure you want to cancel?'
            
            result = ClientGUIDialogsQuick.GetYesNo( self, text )
            
            return result == QW.QDialog.DialogCode.Accepted
            
        else:
            
            return True
            
        
    
class EditContentParsersPanel( ClientGUICommon.StaticBox ):
    
    def __init__( self, parent: QW.QWidget, test_data_callable: collections.abc.Callable[ [], ClientParsing.ParsingTestData ], permitted_content_types ):
        
        super().__init__( parent, 'content parsers' )
        
        self._test_data_callable = test_data_callable
        self._permitted_content_types = permitted_content_types
        
        content_parsers_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_CONTENT_PARSERS.ID, self._ConvertContentParserToDisplayTuple, self._ConvertContentParserToSortTuple )
        
        self._content_parsers = ClientGUIListCtrl.BetterListCtrlTreeView( content_parsers_panel, 6, model, use_simple_delete = True, activation_callback = self._Edit )
        
        content_parsers_panel.SetListCtrl( self._content_parsers )
        
        content_parsers_panel.AddButton( 'add', self._Add )
        content_parsers_panel.AddButton( 'edit', self._Edit, enabled_only_on_single_selection = True )
        content_parsers_panel.AddDeleteButton()
        content_parsers_panel.AddSeparator()
        content_parsers_panel.AddImportExportButtons( ( ClientParsing.ContentParser, ), self._AddContentParser )
        
        #
        
        self.Add( content_parsers_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
    
    def _Add( self ):
        
        dlg_title = 'edit content node'
        
        test_data = self._test_data_callable()
        
        if test_data.LooksLikeJSON():
            
            formula = ClientParsing.ParseFormulaJSON()
            
        else:
            
            formula = ClientParsing.ParseFormulaHTML()
            
        
        content_parser = ClientParsing.ContentParser( 'new content parser', formula = formula )
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit content parser', frame_key = 'deeply_nested_dialog' ) as dlg_edit:
            
            panel = EditContentParserPanel( dlg_edit, content_parser, test_data, self._permitted_content_types )
            
            dlg_edit.SetPanel( panel )
            
            if dlg_edit.exec() == QW.QDialog.DialogCode.Accepted:
                
                new_content_parser = panel.GetValue()
                
                self._AddContentParser( new_content_parser )
                
            
        
    
    def _AddContentParser( self, content_parser ):
        
        HydrusSerialisable.SetNonDupeName( content_parser, self._GetExistingNames() )
        
        self._content_parsers.AddData( content_parser, select_sort_and_scroll = True )
        
    
    def _ConvertContentParserToDisplayTuple( self, content_parser: ClientParsing.ContentParser ):
        
        name = content_parser.GetName()
        
        pretty_produces = content_parser.GetParsableContentDescription().ToString()
        
        return ( name, pretty_produces )
        
    
    _ConvertContentParserToSortTuple = _ConvertContentParserToDisplayTuple
    
    def _Edit( self ):
        
        content_parser = self._content_parsers.GetTopSelectedData()
        
        if content_parser is None:
            
            return
            
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit content parser', frame_key = 'deeply_nested_dialog' ) as dlg:
            
            test_data = self._test_data_callable()
            
            panel = EditContentParserPanel( dlg, content_parser, test_data, self._permitted_content_types )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                edited_content_parser = panel.GetValue()
                
                existing_names = self._GetExistingNames()
                
                existing_names.discard( content_parser.GetName() )
                
                non_dupe_name = HydrusData.GetNonDupeName( edited_content_parser.GetName(), existing_names )
                
                edited_content_parser.SetName( non_dupe_name )
                
                self._content_parsers.ReplaceData( content_parser, edited_content_parser, sort_and_scroll = True )
                
            
        
    
    def _GetExistingNames( self ):
        
        names = { content_parser.GetName() for content_parser in self._content_parsers.GetData() }
        
        return names
        
    
    def GetData( self ):
        
        return self._content_parsers.GetData()
        
    
    def AddDatas( self, content_parsers ):
        
        self._content_parsers.AddDatas( content_parsers )
        
        self._content_parsers.Sort()
        
    

class EditPageParserPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, parser: ClientParsing.PageParser, formula = None, sort_posts_by_source_time = None, test_data = None ):
        
        self._original_parser = parser
        
        super().__init__( parent )
        
        if test_data is None:
            
            example_parsing_context = parser.GetExampleParsingContext()
            example_data = ''
            
            test_data = ClientParsing.ParsingTestData( example_parsing_context, ( example_data, ) )
            
        
        #
        
        menu_template_items = []
        
        page_func = HydrusData.Call( ClientGUIDialogsQuick.OpenDocumentation, self, HC.DOCUMENTATION_DOWNLOADER_PARSERS_PAGE_PARSERS_PAGE_PARSERS )
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'open the page parser help', 'Open the help page for page parsers in your web browser.', page_func ) )
        
        help_button = ClientGUIMenuButton.MenuIconButton( self, CC.global_icons().help, menu_template_items )
        
        help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help for this panel -->', object_name = 'HydrusIndeterminate' )
        
        #
        
        edit_panel = ClientGUICommon.StaticBox( self, 'edit' )
        
        edit_notebook = QW.QTabWidget( edit_panel )
        
        #
        
        main_panel = QW.QWidget( edit_notebook )
        
        self._name = QW.QLineEdit( main_panel )
        
        self._sort_posts_by_source_time = QW.QCheckBox( main_panel )
        tt = 'If you are fetching posts from an unusually ordered source (e.g. "bookmarked time" or similar), but you are able to parse a source time for each separate post with a content parser in here, this will tell the parser to sort them by that timestamp you parsed, obviously newest first.'
        self._sort_posts_by_source_time.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        #
        
        conversion_panel = ClientGUICommon.StaticBox( main_panel, 'pre-parsing conversion' )
        
        string_converter = parser.GetStringConverter()
        
        self._string_converter = ClientGUIStringControls.StringConverterButton( conversion_panel, string_converter )
        
        #
        
        test_panel = ClientGUICommon.StaticBox( self, 'test' )
        
        test_url_fetch_panel = ClientGUICommon.StaticBox( test_panel, 'fetch test data from url' )
        
        self._test_url = QW.QLineEdit( test_url_fetch_panel )
        self._test_referral_url = QW.QLineEdit( test_url_fetch_panel )
        self._fetch_example_data = ClientGUICommon.BetterButton( test_url_fetch_panel, 'fetch test data from url', self._FetchExampleData )
        self._test_network_job_control = ClientGUINetworkJobControl.NetworkJobControl( test_url_fetch_panel )
        
        if formula is None:
            
            self._test_panel = ClientGUIParsingTest.TestPanelPageParser( test_panel, self._GetPageParser, self._string_converter.GetValue, test_data = test_data )
            
        else:
            
            self._test_panel = ClientGUIParsingTest.TestPanelPageParserSubsidiary( test_panel, self._GetPageParser, self._string_converter.GetValue, self.GetValue, test_data = test_data )
            
            self._test_panel.SetCollapseNewlines( False )
            
        
        #
        
        example_urls_panel = ClientGUICommon.StaticBox( main_panel, 'example urls' )
        
        self._example_urls = ClientGUIListBoxes.AddEditDeleteListBox( example_urls_panel, 6, str, self._AddExampleURL, self._EditExampleURL )
        
        self._example_urls.AddSimpleCopyPasteTextButtons()
        
        #
        
        formula_panel = QW.QWidget( edit_notebook )
        
        self._formula = ClientGUIParsingFormulae.EditFormulaPanel( formula_panel, formula, self._test_panel.GetTestData )
        
        self._formula.SetCollapseNewlines( False )
        
        #
        
        subsidiary_page_parsers_notebook_panel = QW.QWidget( edit_notebook )
        
        #
        
        subsidiary_page_parsers_panel = ClientGUIListCtrl.BetterListCtrlPanel( subsidiary_page_parsers_notebook_panel )
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_SUBSIDIARY_PAGE_PARSERS.ID, self._ConvertSubPageParserToDisplayTuple, self._ConvertSubPageParserToSortTuple )
        
        self._subsidiary_page_parsers = ClientGUIListCtrl.BetterListCtrlTreeView( subsidiary_page_parsers_panel, 4, model, use_simple_delete = True, activation_callback = self._EditSubPageParser )
        
        subsidiary_page_parsers_panel.SetListCtrl( self._subsidiary_page_parsers )
        
        subsidiary_page_parsers_panel.AddButton( 'add', self._AddSubPageParser )
        subsidiary_page_parsers_panel.AddButton( 'edit', self._EditSubPageParser, enabled_only_on_single_selection = True )
        subsidiary_page_parsers_panel.AddDeleteButton()
        
        subsidiary_page_parsers_panel.AddSeparator()
        
        subsidiary_page_parsers_panel.AddImportExportButtons(
            permitted_object_types = ( ClientParsing.SubsidiaryPageParser, ),
            import_add_callable = self._ImportAddSubsidiaryPageParser
        )
        
        #
        
        content_parsers_panel = QW.QWidget( edit_notebook )
        
        #
        
        permitted_content_types = [ HC.CONTENT_TYPE_URLS, HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_TYPE_NOTES, HC.CONTENT_TYPE_HASH, HC.CONTENT_TYPE_TIMESTAMP, HC.CONTENT_TYPE_TITLE, HC.CONTENT_TYPE_HTTP_HEADERS, HC.CONTENT_TYPE_VETO ]
        
        self._content_parsers = EditContentParsersPanel( content_parsers_panel, self._test_panel.GetTestDataForChild, permitted_content_types )
        
        #
        
        name = parser.GetName()
        
        ( subsidiary_page_parsers, content_parsers ) = parser.GetContentParsers()
        
        example_urls = parser.GetExampleURLs( encoded = False )
        
        if len( example_urls ) > 0:
            
            self._test_url.setText( example_urls[0] )
            
        
        self._name.setText( name )
        
        if sort_posts_by_source_time is not None:
            
            self._sort_posts_by_source_time.setChecked( sort_posts_by_source_time )
            
        
        self._subsidiary_page_parsers.AddDatas( subsidiary_page_parsers )
        
        self._subsidiary_page_parsers.Sort()
        
        self._content_parsers.AddDatas( content_parsers )
        
        self._example_urls.AddDatas( example_urls )
        
        #
        
        st = ClientGUICommon.BetterStaticText( conversion_panel, 'If the data this parser gets is wrapped in some quote marks or is otherwise encoded,\nyou can convert it to neat HTML/JSON first with this.' )
        
        conversion_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
        conversion_panel.Add( self._string_converter, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        example_urls_panel.Add( self._example_urls, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        vbox = QP.VBoxLayout()
        
        rows = []
        
        rows.append( ( 'name or description (optional): ', self._name ) )
        
        if sort_posts_by_source_time is None:
            
            self._sort_posts_by_source_time.setVisible( False )
            
        else:
            
            rows.append( ( 'sort posts by source time: ', self._sort_posts_by_source_time ) )
            
        
        gridbox = ClientGUICommon.WrapInGrid( main_panel, rows )
        
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, conversion_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, example_urls_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        vbox.addStretch( 0 )
        
        main_panel.setLayout( vbox )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._formula, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        formula_panel.setLayout( vbox )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, subsidiary_page_parsers_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        subsidiary_page_parsers_notebook_panel.setLayout( vbox )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._content_parsers, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        content_parsers_panel.setLayout( vbox )
        
        #
        
        rows = []
        
        rows.append( ( 'url: ', self._test_url ) )
        rows.append( ( 'referral url (optional): ', self._test_referral_url ) )
        
        gridbox = ClientGUICommon.WrapInGrid( test_url_fetch_panel, rows )
        
        test_url_fetch_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        test_url_fetch_panel.Add( self._fetch_example_data, CC.FLAGS_EXPAND_PERPENDICULAR )
        test_url_fetch_panel.Add( self._test_network_job_control, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        test_panel.Add( test_url_fetch_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        test_panel.Add( self._test_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        if formula is not None:
            
            test_url_fetch_panel.hide()
            
        
        #
        
        if formula is None:
            
            formula_panel.setVisible( False )
            
        else:
            
            example_urls_panel.hide()
            edit_notebook.addTab( formula_panel, 'separation formula' )
            
        
        edit_notebook.addTab( main_panel, 'main' )
        edit_notebook.setCurrentWidget( main_panel )
        edit_notebook.addTab( subsidiary_page_parsers_notebook_panel, 'subsidiary page parsers' )
        edit_notebook.addTab( content_parsers_panel, 'content parsers' )
        
        edit_panel.Add( edit_notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, edit_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, test_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, help_hbox, CC.FLAGS_ON_RIGHT )
        QP.AddToLayout( vbox, hbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
    def _AddExampleURL( self ):
        
        url = ''
        
        return self._EditExampleURL( url )
        
    
    def _AddSubPageParser( self ):
        
        subsidiary_page_parser = ClientParsing.SubsidiaryPageParser()
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit sub page parser', frame_key = 'deeply_nested_dialog' ) as dlg:
            
            panel = EditSubsidiaryPageParserPanel( dlg, subsidiary_page_parser, test_data = self._test_panel.GetTestDataForChild() )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                new_subsidiary_page_parser = panel.GetValue()
                
                self._subsidiary_page_parsers.AddData( new_subsidiary_page_parser, select_sort_and_scroll = True )
                
            
        
    
    def _ConvertSubPageParserToDisplayTuple( self, subsidiary_page_parser: ClientParsing.SubsidiaryPageParser ):
        
        formula = subsidiary_page_parser.GetFormula()
        page_parser = subsidiary_page_parser.GetPageParser()
        
        name = page_parser.GetName()
        
        parseable_content_descriptions = page_parser.GetParsableContentDescriptions()
        
        pretty_formula = formula.ToPrettyString()
        pretty_produces = ClientParsingResults.ConvertParsableContentDescriptionsToPrettyString( parseable_content_descriptions )
        
        return ( name, pretty_formula, pretty_produces )
        
    
    _ConvertSubPageParserToSortTuple = _ConvertSubPageParserToDisplayTuple
    
    def _EditExampleURL( self, example_url ):
        
        message = 'Enter example URL.'
        
        try:
            
            url = ClientGUIDialogsQuick.EnterText( self, message, default = example_url )
            
        except HydrusExceptions.CancelledException:
            
            raise
            
        
        return url
        
    
    def _EditSubPageParser( self ):
        
        subsidiary_page_parser = self._subsidiary_page_parsers.GetTopSelectedData()
        
        if subsidiary_page_parser is None:
            
            return
            
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit sub page parser', frame_key = 'deeply_nested_dialog' ) as dlg:
            
            panel = EditSubsidiaryPageParserPanel( dlg, subsidiary_page_parser, test_data = self._test_panel.GetTestDataForChild() )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                new_subsidiary_page_parser = panel.GetValue()
                
                self._subsidiary_page_parsers.ReplaceData( subsidiary_page_parser, new_subsidiary_page_parser, sort_and_scroll = True )
                
            
        
    
    def _FetchExampleData( self ):
        
        def wait_and_do_it( network_job ):
            
            def qt_tidy_up( example_data, example_bytes, error ):
                
                example_parsing_context = self._test_panel.GetExampleParsingContext()
                
                example_parsing_context[ 'url' ] = url
                example_parsing_context[ 'post_index' ] = '0'
                
                self._test_panel.SetExampleParsingContext( example_parsing_context )
                
                self._test_panel.SetExampleData( example_data, example_bytes = example_bytes )
                
                self._test_network_job_control.ClearNetworkJob()
                
                if error is not None:
                    
                    self._test_network_job_control.SetError( error )
                    
                
            
            example_bytes = None
            error = None
            
            try:
                
                network_job.WaitUntilDone()
                
                example_data = network_job.GetContentText()
                
                example_bytes = network_job.GetContentBytes()
                
            except HydrusExceptions.CancelledException:
                
                example_data = 'fetch cancelled'
                
            except Exception as e:
                
                error = traceback.format_exc()
                
                try:
                    
                    stuff_read = network_job.GetContentText()
                    
                except Exception as e:
                    
                    stuff_read = 'no response'
                    
                
                example_data = 'fetch failed: {}'.format( e ) + '\n' * 2 + stuff_read
                
            
            CG.client_controller.CallAfterQtSafe( self, qt_tidy_up, example_data, example_bytes, error )
            
        
        raw_url = self._test_url.text().strip()
        
        if raw_url == '':
            
            example_urls = self._example_urls.GetData()
            
            if len( example_urls ) > 0:
                
                self._test_url.setText( example_urls[0] )
                
            
            return
            
        
        url = ClientNetworkingFunctions.EnsureURLIsEncoded( raw_url )
        referral_url = self._test_referral_url.text()
        
        if referral_url == '':
            
            referral_url = None
            
        
        network_job = ClientNetworkingJobs.NetworkJob( 'GET', url, referral_url = referral_url )
        
        network_job.OnlyTryConnectionOnce()
        
        self._test_network_job_control.ClearError()
        self._test_network_job_control.SetNetworkJob( network_job )
        
        network_job.OverrideBandwidth()
        
        CG.client_controller.network_engine.AddJob( network_job )
        
        CG.client_controller.CallToThread( wait_and_do_it, network_job )
        
    
    def _GetPageParser( self ):
        
        name = self._name.text()
        
        parser_key = self._original_parser.GetParserKey()
        
        string_converter = self._string_converter.GetValue()
        
        subsidiary_page_parsers = self._subsidiary_page_parsers.GetData()
        
        content_parsers = self._content_parsers.GetData()
        
        example_urls = self._example_urls.GetData()
        
        example_parsing_context = self._test_panel.GetExampleParsingContext()
        
        page_parser = ClientParsing.PageParser( name, parser_key = parser_key, string_converter = string_converter, subsidiary_page_parsers = subsidiary_page_parsers, content_parsers = content_parsers, example_urls = example_urls, example_parsing_context = example_parsing_context )
        
        return page_parser
        
    
    def _ImportAddSubsidiaryPageParser( self, subsidiary_page_parser: ClientParsing.SubsidiaryPageParser ):
        
        self._subsidiary_page_parsers.AddData( subsidiary_page_parser, select_sort_and_scroll = True )
        
    
    def GetFormula( self ):
        
        return self._formula.GetValue()
        
    
    def GetSortPostsBySourceTime( self ):
        
        return self._sort_posts_by_source_time.isChecked()
        
    
    def GetValue( self ):
        
        page_parser = self._GetPageParser()
        
        return page_parser
        
    
    def UserIsOKToCancel( self ):
        
        original_parser = self._original_parser.Duplicate()
        current_parser = self._GetPageParser()
        
        original_parser.NullifyTestData()
        current_parser.NullifyTestData()
        
        # just a note, this thing was false-positiving a while ago because the content parsers were rearranging, I guess the UI was sorting them in the list in a diff way or whatever
        # the solution was to change the serialisation routine to sort subsidiary parsers and content parsers by name, so keep this in mind bro
        if original_parser.GetSerialisableTuple() != current_parser.GetSerialisableTuple():
            
            text = 'It looks like you have made changes to the parser--are you sure you want to cancel?'
            
            result = ClientGUIDialogsQuick.GetYesNo( self, text )
            
            return result == QW.QDialog.DialogCode.Accepted
            
        else:
            
            return True
            
        
    

class EditSubsidiaryPageParserPanel( EditPageParserPanel ):
    
    def __init__( self, parent: QW.QWidget, subsidiary_page_parser: ClientParsing.SubsidiaryPageParser, test_data = None ):
        
        page_parser = subsidiary_page_parser.GetPageParser()
        formula = subsidiary_page_parser.GetFormula()
        sort_posts_by_source_time = subsidiary_page_parser.GetSortPostsBySourceTime()
        
        super().__init__(
            parent,
            page_parser,
            formula = formula,
            sort_posts_by_source_time = sort_posts_by_source_time,
            test_data = test_data
        )
        
    
    def GetValue( self ):
        
        page_parser = self._GetPageParser()
        formula = self.GetFormula()
        sort_posts_by_source_time = self.GetSortPostsBySourceTime()
        
        subsidiary_page_parser = ClientParsing.SubsidiaryPageParser(
            formula = formula,
            sort_posts_by_source_time = sort_posts_by_source_time,
            page_parser = page_parser
        )
        
        return subsidiary_page_parser
        
    

class EditParsersPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, parsers ):
        
        super().__init__( parent )
        
        parsers_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_PARSERS.ID, self._ConvertParserToDisplayTuple, self._ConvertParserToSortTuple )
        
        self._parsers = ClientGUIListCtrl.BetterListCtrlTreeView( parsers_panel, 20, model, use_simple_delete = True, activation_callback = self._Edit )
        
        parsers_panel.SetListCtrl( self._parsers )
        
        parsers_panel.AddButton( 'add', self._Add )
        parsers_panel.AddButton( 'edit', self._Edit, enabled_only_on_single_selection = True )
        parsers_panel.AddDeleteButton()
        parsers_panel.AddSeparator()
        parsers_panel.AddImportExportButtons( ( ClientParsing.PageParser, ), self._AddParser )
        parsers_panel.AddSeparator()
        parsers_panel.AddDefaultsButton( ClientDefaults.GetDefaultParsers, self._AddParser )
        
        #
        
        self._parsers.AddDatas( parsers )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, parsers_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
    def _Add( self ):
        
        new_parser = ClientParsing.PageParser( 'new page parser' )
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit parser', frame_key = 'deeply_nested_dialog' ) as dlg_edit:
            
            panel = EditPageParserPanel( dlg_edit, new_parser )
            
            dlg_edit.SetPanel( panel )
            
            if dlg_edit.exec() == QW.QDialog.DialogCode.Accepted:
                
                new_parser = panel.GetValue()
                
                self._AddParser( new_parser, select_sort_and_scroll = True )
                
            
        
    
    def _AddParser( self, parser, select_sort_and_scroll = False ):
        
        HydrusSerialisable.SetNonDupeName( parser, self._GetExistingNames() )
        
        parser.RegenerateParserKey()
        
        self._parsers.AddData( parser, select_sort_and_scroll = select_sort_and_scroll )
        
    
    def _ConvertParserToDisplayTuple( self, parser: ClientParsing.PageParser ):
        
        name = parser.GetName()
        
        example_urls = sorted( parser.GetExampleURLs() )
        
        parsable_content_descriptions = parser.GetParsableContentDescriptions()
        
        pretty_produces = ClientParsingResults.ConvertParsableContentDescriptionsToPrettyString( parsable_content_descriptions )
        
        pretty_name = name
        pretty_example_urls = ', '.join( example_urls )
        
        display_tuple = ( pretty_name, pretty_example_urls, pretty_produces )
        
        return display_tuple
        
    
    def _ConvertParserToSortTuple( self, parser: ClientParsing.PageParser ):
        
        name = parser.GetName()
        
        example_urls = sorted( parser.GetExampleURLs() )
        
        parsable_content_descriptions = parser.GetParsableContentDescriptions()
        
        pretty_produces = ClientParsingResults.ConvertParsableContentDescriptionsToPrettyString( parsable_content_descriptions )
        
        sort_produces = pretty_produces
        
        sort_tuple = ( name, example_urls, sort_produces )
        
        return sort_tuple
        
    
    def _Edit( self ):
        
        data = self._parsers.GetTopSelectedData()
        
        if data is None:
            
            return
            
        
        parser: ClientParsing.PageParser = data
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit parser', frame_key = 'deeply_nested_dialog' ) as dlg:
            
            panel = EditPageParserPanel( dlg, parser )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                edited_parser = panel.GetValue()
                
                if edited_parser.GetName() != parser.GetName():
                    
                    HydrusSerialisable.SetNonDupeName( edited_parser, self._GetExistingNames() )
                    
                
                self._parsers.ReplaceData( parser, edited_parser, sort_and_scroll = True )
                
            
        
    
    def _GetExistingNames( self ):
        
        names = { parser.GetName() for parser in self._parsers.GetData() }
        
        return names
        
    
    def GetValue( self ):
        
        return self._parsers.GetData()
        
