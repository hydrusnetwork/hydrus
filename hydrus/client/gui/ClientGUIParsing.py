import itertools
import json
import os
import sys
import threading
import traceback
import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusFileHandling
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTemp
from hydrus.core import HydrusText

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientDefaults
from hydrus.client import ClientParsing
from hydrus.client import ClientPaths
from hydrus.client import ClientSerialisable
from hydrus.client import ClientStrings
from hydrus.client import ClientThreading
from hydrus.client.gui import ClientGUIDialogs
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIMenus
from hydrus.client.gui import ClientGUICore as CGC
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIScrolledPanels
from hydrus.client.gui import ClientGUISerialisable
from hydrus.client.gui import ClientGUIStringControls
from hydrus.client.gui import ClientGUIStringPanels
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListBoxes
from hydrus.client.gui.lists import ClientGUIListConstants as CGLC
from hydrus.client.gui.lists import ClientGUIListCtrl
from hydrus.client.gui.networking import ClientGUINetworkJobControl
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.gui.widgets import ClientGUIControls
from hydrus.client.gui.widgets import ClientGUIMenuButton
from hydrus.client.networking import ClientNetworkingContexts
from hydrus.client.networking import ClientNetworkingDomain
from hydrus.client.networking import ClientNetworkingFunctions
from hydrus.client.networking import ClientNetworkingGUG
from hydrus.client.networking import ClientNetworkingJobs
from hydrus.client.networking import ClientNetworkingURLClass


class DownloaderExportPanel( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent, network_engine ):
        
        ClientGUIScrolledPanels.ReviewPanel.__init__( self, parent )
        
        self._network_engine = network_engine
        
        menu_items = []
        
        page_func = HydrusData.Call( ClientPaths.LaunchPathInWebBrowser, os.path.join( HC.HELP_DIR, 'downloader_sharing.html' ) )
        
        menu_items.append( ( 'normal', 'open the downloader sharing help', 'Open the help page for sharing downloaders in your web browser.', page_func ) )
        
        help_button = ClientGUIMenuButton.MenuBitmapButton( self, CC.global_pixmaps().help, menu_items )
        
        help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help for this panel -->', object_name = 'HydrusIndeterminate' )
        
        listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        self._listctrl = ClientGUIListCtrl.BetterListCtrl( listctrl_panel, CGLC.COLUMN_LIST_DOWNLOADER_EXPORT.ID, 14, self._ConvertContentToListCtrlTuples, use_simple_delete = True )
        
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
        
        message = 'Enter domain:'
        
        with ClientGUIDialogs.DialogTextEntry( self, message ) as dlg:
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                domain = dlg.GetValue()
                
            else:
                
                return
                
            
        
        domain_metadatas = self._GetDomainMetadatasToInclude( { domain } )
        
        if len( domain_metadatas ) > 0:
            
            self._listctrl.AddDatas( domain_metadatas )
            
        else:
            
            QW.QMessageBox.information( self, 'Information', 'No headers/bandwidth rules found!' )
            
        
    
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
        
    
    def _ConvertContentToListCtrlTuples( self, content ):
        
        if isinstance( content, ClientNetworkingDomain.DomainMetadataPackage ):
            
            name = content.GetDomain()
            
        else:
            
            name = content.GetName()
            
        
        t = content.SERIALISABLE_NAME
        
        pretty_name = name
        pretty_t = t
        
        display_tuple = ( pretty_name, pretty_t )
        sort_tuple = ( name, t )
        
        return ( display_tuple, sort_tuple )
        
    
    def _Export( self ):
        
        export_object = HydrusSerialisable.SerialisableList( self._listctrl.GetData() )
        
        message = 'The end-user will see this sort of summary:'
        message += os.linesep * 2
        message += os.linesep.join( ( obj.GetSafeSummary() for obj in export_object[:20] ) )
        
        if len( export_object ) > 20:
            
            message += os.linesep
            message += '(and ' + HydrusData.ToHumanInt( len( export_object ) - 20 ) + ' others)'
            
        
        message += os.linesep * 2
        message += 'Does that look good? (Ideally, every object should have correct and sane domains listed here)'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result != QW.QDialog.Accepted:
            
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
                
                title += ' - ' + HydrusData.ToHumanInt( num_gugs ) + ' downloaders'
                
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
            
            QW.QMessageBox.information( self, 'Information', domain_metadata.GetDetailedSafeSummary() )
            
        
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
                    
                except:
                    
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
        
    
class EditCompoundFormulaPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, formula: ClientParsing.ParseFormulaCompound, test_data: ClientParsing.ParsingTestData ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        #
        
        menu_items = []
        
        page_func = HydrusData.Call( ClientPaths.LaunchPathInWebBrowser, os.path.join( HC.HELP_DIR, 'downloader_parsers_formulae.html#compound_formula' ) )
        
        menu_items.append( ( 'normal', 'open the compound formula help', 'Open the help page for compound formulae in your web browser.', page_func ) )
        
        help_button = ClientGUIMenuButton.MenuBitmapButton( self, CC.global_pixmaps().help, menu_items )
        
        help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help for this panel -->', object_name = 'HydrusIndeterminate' )
        
        #
        
        test_panel = ClientGUICommon.StaticBox( self, 'test' )
        
        self._test_panel = TestPanelFormula( test_panel, self.GetValue, test_data = test_data )
        
        #
        
        edit_panel = ClientGUICommon.StaticBox( self, 'edit' )
        
        self._formulae = QW.QListWidget( edit_panel )
        self._formulae.setSelectionMode( QW.QAbstractItemView.SingleSelection )
        self._formulae.itemDoubleClicked.connect( self.Edit )
        
        self._add_formula = ClientGUICommon.BetterButton( edit_panel, 'add', self.Add )
        
        self._edit_formula = ClientGUICommon.BetterButton( edit_panel, 'edit', self.Edit )
        
        self._move_formula_up = ClientGUICommon.BetterButton( edit_panel, '\u2191', self.MoveUp )
        
        self._delete_formula = ClientGUICommon.BetterButton( edit_panel, 'X', self.Delete )
        
        self._move_formula_down = ClientGUICommon.BetterButton( edit_panel, '\u2193', self.MoveDown )
        
        self._sub_phrase = QW.QLineEdit( edit_panel )
        
        formulae = formula.GetFormulae()
        sub_phrase = formula.GetSubstitutionPhrase()
        string_processor = formula.GetStringProcessor()
        
        self._string_processor_button = ClientGUIStringControls.StringProcessorButton( edit_panel, string_processor, self._test_panel.GetTestDataForStringProcessor )
        
        #
        
        for formula in formulae:
            
            pretty_formula = formula.ToPrettyString()
            
            item = QW.QListWidgetItem()
            item.setText( pretty_formula )
            item.setData( QC.Qt.UserRole, formula )
            self._formulae.addItem( item )
            
        
        self._sub_phrase.setText( sub_phrase )
        
        #
        
        udd_button_vbox = QP.VBoxLayout()
        
        udd_button_vbox.addStretch( 1 )
        QP.AddToLayout( udd_button_vbox, self._move_formula_up, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( udd_button_vbox, self._delete_formula, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( udd_button_vbox, self._move_formula_down, CC.FLAGS_CENTER_PERPENDICULAR )
        udd_button_vbox.addStretch( 1 )
        
        formulae_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( formulae_hbox, self._formulae, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( formulae_hbox, udd_button_vbox, CC.FLAGS_CENTER_PERPENDICULAR )
        
        ae_button_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( ae_button_hbox, self._add_formula, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( ae_button_hbox, self._edit_formula, CC.FLAGS_CENTER_PERPENDICULAR )
        
        rows = []
        
        rows.append( ( 'substitution phrase:', self._sub_phrase ) )
        
        gridbox = ClientGUICommon.WrapInGrid( edit_panel, rows )
        
        edit_panel.Add( formulae_hbox, CC.FLAGS_EXPAND_BOTH_WAYS )
        edit_panel.Add( ae_button_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        edit_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        edit_panel.Add( ClientGUICommon.BetterStaticText( edit_panel, 'Newlines are removed from parsed strings right after parsing, before string processing.', ellipsize_end = True ), CC.FLAGS_EXPAND_PERPENDICULAR )
        edit_panel.Add( self._string_processor_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        test_panel.Add( self._test_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, edit_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, test_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, help_hbox, CC.FLAGS_ON_RIGHT )
        QP.AddToLayout( vbox, hbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
    def Add( self ):
        
        existing_formula = ClientParsing.ParseFormulaHTML()
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit formula', frame_key = 'deeply_nested_dialog' ) as dlg:
            
            panel = EditFormulaPanel( dlg, existing_formula, self._test_panel.GetTestDataForChild )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                new_formula = panel.GetValue()
                
                pretty_formula = new_formula.ToPrettyString()
                
                item = QW.QListWidgetItem()
                item.setText( pretty_formula )
                item.setData( QC.Qt.UserRole, new_formula )
                self._formulae.addItem( item )
                
            
        
    
    def Delete( self ):
        
        selection = QP.ListWidgetGetSelection( self._formulae ) 
        
        if selection != -1:
            
            if self._formulae.count() == 1:
                
                QW.QMessageBox.critical( self, 'Error', 'A compound formula needs at least one sub-formula!' )
                
            else:
                
                QP.ListWidgetDelete( self._formulae, selection )
                
            
        
    
    def Edit( self ):
        
        selection = QP.ListWidgetGetSelection( self._formulae ) 
        
        if selection != -1:
            
            old_formula = QP.GetClientData( self._formulae, selection )
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit formula', frame_key = 'deeply_nested_dialog' ) as dlg:
                
                panel = EditFormulaPanel( dlg, old_formula, self._test_panel.GetTestDataForChild )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    new_formula = panel.GetValue()
                    
                    pretty_formula = new_formula.ToPrettyString()
                    
                    self._formulae.item( selection ).setText( pretty_formula )
                    self._formulae.item( selection ).setData( QC.Qt.UserRole, new_formula )
                    
                
            
        
    
    def GetValue( self ):
        
        formulae = [ QP.GetClientData( self._formulae, i ) for i in range( self._formulae.count() ) ]
        
        sub_phrase = self._sub_phrase.text()
        
        string_processor = self._string_processor_button.GetValue()
        
        formula = ClientParsing.ParseFormulaCompound( formulae, sub_phrase, string_processor )
        
        return formula
        
    
    def MoveDown( self ):
        
        selection = QP.ListWidgetGetSelection( self._formulae ) 
        
        if selection != -1 and selection + 1 < self._formulae.count():
            
            pretty_rule = self._formulae.item( selection ).text()
            rule = QP.GetClientData( self._formulae, selection )
            
            QP.ListWidgetDelete( self._formulae, selection )
            
            item = QW.QListWidgetItem()
            item.setText( pretty_rule )
            item.setData( QC.Qt.UserRole, rule )
            self._formulae.insertItem( selection + 1, item )
            
        
    
    def MoveUp( self ):
        
        selection = QP.ListWidgetGetSelection( self._formulae ) 
        
        if selection != -1 and selection > 0:
            
            pretty_rule = self._formulae.item( selection ).text()
            rule = QP.GetClientData( self._formulae, selection )
            
            QP.ListWidgetDelete( self._formulae, selection )
            
            item = QW.QListWidgetItem()
            item.setText( pretty_rule )
            item.setData( QC.Qt.UserRole, rule )
            self._formulae.insertItem( selection - 1, item )
            
        
    
class EditContextVariableFormulaPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, formula: ClientParsing.ParseFormulaContextVariable, test_data: ClientParsing.ParsingTestData ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        #
        
        menu_items = []
        
        page_func = HydrusData.Call( ClientPaths.LaunchPathInWebBrowser, os.path.join( HC.HELP_DIR, 'downloader_parsers_formulae.html#context_variable_formula' ) )
        
        menu_items.append( ( 'normal', 'open the context variable formula help', 'Open the help page for context variable formulae in your web browser.', page_func ) )
        
        help_button = ClientGUIMenuButton.MenuBitmapButton( self, CC.global_pixmaps().help, menu_items )
        
        help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help for this panel -->', object_name = 'HydrusIndeterminate' )
        
        #
        
        test_panel = ClientGUICommon.StaticBox( self, 'test' )
        
        self._test_panel = TestPanelFormula( test_panel, self.GetValue, test_data = test_data )
        
        #
        
        edit_panel = ClientGUICommon.StaticBox( self, 'edit' )
        
        self._variable_name = QW.QLineEdit( edit_panel )
        
        variable_name = formula.GetVariableName()
        string_processor = formula.GetStringProcessor()
        
        self._string_processor_button = ClientGUIStringControls.StringProcessorButton( edit_panel, string_processor, self._test_panel.GetTestDataForStringProcessor )
        
        #
        
        self._variable_name.setText( variable_name )
        
        #
        
        rows = []
        
        rows.append( ( 'variable name:', self._variable_name ) )
        
        gridbox = ClientGUICommon.WrapInGrid( edit_panel, rows )
        
        edit_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        edit_panel.Add( ClientGUICommon.BetterStaticText( edit_panel, 'Newlines are removed from parsed strings right after parsing, before string processing.', ellipsize_end = True ), CC.FLAGS_EXPAND_PERPENDICULAR )
        edit_panel.Add( self._string_processor_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        test_panel.Add( self._test_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, edit_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, test_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, help_hbox, CC.FLAGS_ON_RIGHT )
        QP.AddToLayout( vbox, hbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
    def GetValue( self ):
        
        variable_name = self._variable_name.text()
        
        string_processor = self._string_processor_button.GetValue()
        
        formula = ClientParsing.ParseFormulaContextVariable( variable_name, string_processor )
        
        return formula
        
    
class EditFormulaPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, formula: ClientParsing.ParseFormula, test_data_callable: typing.Callable[ [], ClientParsing.ParsingTestData ] ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._current_formula = formula
        self._test_data_callable = test_data_callable
        
        #
        
        my_panel = ClientGUICommon.StaticBox( self, 'formula' )
        
        self._formula_description = QW.QPlainTextEdit( my_panel )
        
        ( width, height ) = ClientGUIFunctions.ConvertTextToPixels( self._formula_description, ( 90, 8 ) )
        
        self._formula_description.setMinimumWidth( width )
        self._formula_description.setMinimumHeight( height )
        
        self._formula_description.setEnabled( False )
        
        self._edit_formula = ClientGUICommon.BetterButton( my_panel, 'edit formula', self._EditFormula )
        
        self._change_formula_type = ClientGUICommon.BetterButton( my_panel, 'change formula type', self._ChangeFormulaType )
        
        #
        
        self._UpdateControls()
        
        #
        
        button_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( button_hbox, self._edit_formula, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( button_hbox, self._change_formula_type, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        my_panel.Add( self._formula_description, CC.FLAGS_EXPAND_BOTH_WAYS )
        my_panel.Add( button_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, my_panel, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
    def _ChangeFormulaType( self ):
        
        if self._current_formula.ParsesSeparatedContent():
            
            new_html = ClientParsing.ParseFormulaHTML( content_to_fetch = ClientParsing.HTML_CONTENT_HTML )
            new_json = ClientParsing.ParseFormulaJSON( content_to_fetch = ClientParsing.JSON_CONTENT_JSON )
            
        else:
            
            new_html = ClientParsing.ParseFormulaHTML()
            new_json = ClientParsing.ParseFormulaJSON()
            
        
        new_compound = ClientParsing.ParseFormulaCompound()
        new_context_variable = ClientParsing.ParseFormulaContextVariable()
        
        if isinstance( self._current_formula, ClientParsing.ParseFormulaHTML ):
            
            order = ( 'json', 'compound', 'context_variable' )
            
        elif isinstance( self._current_formula, ClientParsing.ParseFormulaJSON ):
            
            order = ( 'html', 'compound', 'context_variable' )
            
        elif isinstance( self._current_formula, ClientParsing.ParseFormulaCompound ):
            
            order = ( 'html', 'json', 'context_variable' )
            
        elif isinstance( self._current_formula, ClientParsing.ParseFormulaContextVariable ):
            
            order = ( 'html', 'json', 'compound', 'context_variable' )
            
        
        choice_tuples = []
        
        for formula_type in order:
            
            if formula_type == 'html':
                
                choice_tuples.append( ( 'change to a new HTML formula', new_html ) )
                
            elif formula_type == 'json':
                
                choice_tuples.append( ( 'change to a new JSON formula', new_json ) )
                
            elif formula_type == 'compound':
                
                choice_tuples.append( ( 'change to a new COMPOUND formula', new_compound ) )
                
            elif formula_type == 'context_variable':
                
                choice_tuples.append( ( 'change to a new CONTEXT VARIABLE formula', new_context_variable ) )
                
            
        
        try:
            
            self._current_formula = ClientGUIDialogsQuick.SelectFromList( self, 'select formula type', choice_tuples )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        self._UpdateControls()
        
    
    def _EditFormula( self ):
        
        if isinstance( self._current_formula, ClientParsing.ParseFormulaHTML ):
            
            panel_class = EditHTMLFormulaPanel
            
        elif isinstance( self._current_formula, ClientParsing.ParseFormulaJSON ):
            
            panel_class = EditJSONFormulaPanel
            
        elif isinstance( self._current_formula, ClientParsing.ParseFormulaCompound ):
            
            panel_class = EditCompoundFormulaPanel
            
        elif isinstance( self._current_formula, ClientParsing.ParseFormulaContextVariable ):
            
            panel_class = EditContextVariableFormulaPanel
            
        
        test_data = self._test_data_callable()
        
        dlg_title = 'edit formula'
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, dlg_title, frame_key = 'deeply_nested_dialog' ) as dlg:
            
            panel = panel_class( dlg, self._current_formula, test_data )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                self._current_formula = panel.GetValue()
                
                self._UpdateControls()
                
            
        
    
    def _UpdateControls( self ):
        
        if self._current_formula is None:
            
            self._formula_description.clear()
            
            self._edit_formula.setEnabled( False )
            self._change_formula_type.setEnabled( False )
            
        else:
            
            self._formula_description.setPlainText( self._current_formula.ToPrettyMultilineString() )
            
            self._edit_formula.setEnabled( True )
            self._change_formula_type.setEnabled( True )
            
        
    
    def GetValue( self ):
        
        return self._current_formula
        
    
class EditHTMLTagRulePanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, tag_rule ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        ( rule_type, tag_name, tag_attributes, tag_index, tag_depth, should_test_tag_string, tag_string_string_match ) = tag_rule.ToTuple()
        
        if tag_name is None:
            
            tag_name = ''
            
        
        if tag_attributes is None:
            
            tag_attributes = {}
            
        
        if tag_depth is None:
            
            tag_depth = 1
            
        
        self._current_description = ClientGUICommon.BetterStaticText( self )
        
        self._rule_type = ClientGUICommon.BetterChoice( self )
        
        self._rule_type.addItem( 'search descendants', ClientParsing.HTML_RULE_TYPE_DESCENDING )
        self._rule_type.addItem( 'walk back up ancestors', ClientParsing.HTML_RULE_TYPE_ASCENDING )
        
        self._tag_name = QW.QLineEdit( self )
        
        self._tag_attributes = ClientGUIStringControls.StringToStringDictControl( self, tag_attributes, min_height = 4 )
        
        self._tag_index = ClientGUICommon.NoneableSpinCtrl( self, 'index to fetch', none_phrase = 'get all', min = -65536, max = 65535 )
        self._tag_index.setToolTip( 'You can make this negative to do negative indexing, i.e. "Select the second from last item".' )
        
        self._tag_depth = QP.MakeQSpinBox( self, min=1, max=255 )
        
        self._should_test_tag_string = QW.QCheckBox( self )
        
        self._tag_string_string_match = ClientGUIStringControls.StringMatchButton( self, tag_string_string_match )
        
        #
        
        self._rule_type.SetValue( rule_type )
        self._tag_name.setText( tag_name )
        self._tag_index.SetValue( tag_index )
        self._tag_depth.setValue( tag_depth )
        self._should_test_tag_string.setChecked( should_test_tag_string )
        
        self._UpdateTypeControls()
        
        #
        
        vbox = QP.VBoxLayout()
        
        rows = []
        
        rows.append( ( 'rule type: ', self._rule_type ) )
        rows.append( ( 'tag name: ', self._tag_name ) )
        
        gridbox_1 = ClientGUICommon.WrapInGrid( self, rows )
        
        rows = []
        
        rows.append( ( 'index to fetch: ', self._tag_index ) )
        rows.append( ( 'depth to climb: ', self._tag_depth ) )
        
        gridbox_2 = ClientGUICommon.WrapInGrid( self, rows )
        
        rows = []
        
        rows.append( ( 'should test tag string: ', self._should_test_tag_string ) )
        rows.append( ( 'tag string match: ', self._tag_string_string_match ) )
        
        gridbox_3 = ClientGUICommon.WrapInGrid( self, rows )
        
        QP.AddToLayout( vbox, self._current_description, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        QP.AddToLayout( vbox, gridbox_1, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, self._tag_attributes, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, gridbox_2, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, gridbox_3, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self.widget().setLayout( vbox )
        
        self._UpdateShouldTest()
        
        #
        
        self._rule_type.currentIndexChanged.connect( self.EventTypeChanged )
        self._tag_name.textChanged.connect( self.EventVariableChanged )
        self._tag_attributes.columnListContentsChanged.connect( self.EventVariableChanged )
        self._tag_index.valueChanged.connect( self.EventVariableChanged )
        self._tag_depth.valueChanged.connect( self.EventVariableChanged )
        
        self._should_test_tag_string.clicked.connect( self.EventShouldTestChanged )
        
    
    def _UpdateShouldTest( self ):
        
        if self._should_test_tag_string.isChecked():
            
            self._tag_string_string_match.setEnabled( True )
            
        else:
            
            self._tag_string_string_match.setEnabled( False )
            
        
    
    def _UpdateTypeControls( self ):
        
        rule_type = self._rule_type.GetValue()
        
        if rule_type == ClientParsing.HTML_RULE_TYPE_DESCENDING:
            
            self._tag_attributes.setEnabled( True )
            self._tag_index.setEnabled( True )
            
            self._tag_depth.setEnabled( False )
            
        else:
            
            self._tag_attributes.setEnabled( False )
            self._tag_index.setEnabled( False )
            
            self._tag_depth.setEnabled( True )
            
        
        self._UpdateDescription()
        
    
    def _UpdateDescription( self ):
        
        tag_rule = self.GetValue()
        
        label = tag_rule.ToString()
        
        self._current_description.setText( label )
        
    
    def EventShouldTestChanged( self ):
        
        self._UpdateShouldTest()
        
    
    def EventTypeChanged( self, index ):
        
        self._UpdateTypeControls()
        
    
    def EventVariableChanged( self ):
        
        self._UpdateDescription()
        
    
    def GetValue( self ):
        
        rule_type = self._rule_type.GetValue()
        
        tag_name = self._tag_name.text()
        
        if tag_name == '':
            
            tag_name = None
            
        
        should_test_tag_string = self._should_test_tag_string.isChecked()
        tag_string_string_match = self._tag_string_string_match.GetValue()
        
        if rule_type == ClientParsing.HTML_RULE_TYPE_DESCENDING:
            
            tag_attributes = self._tag_attributes.GetValue()
            tag_index = self._tag_index.GetValue()
            
            tag_rule = ClientParsing.ParseRuleHTML( rule_type = rule_type, tag_name = tag_name, tag_attributes = tag_attributes, tag_index = tag_index, should_test_tag_string = should_test_tag_string, tag_string_string_match = tag_string_string_match )
            
        elif rule_type == ClientParsing.HTML_RULE_TYPE_ASCENDING:
            
            tag_depth = self._tag_depth.value()
            
            tag_rule = ClientParsing.ParseRuleHTML( rule_type = rule_type, tag_name = tag_name, tag_depth = tag_depth, should_test_tag_string = should_test_tag_string, tag_string_string_match = tag_string_string_match )
            
        
        return tag_rule
        
    
class EditHTMLFormulaPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, formula: ClientParsing.ParseFormulaHTML, test_data: ClientParsing.ParsingTestData ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        #
        
        menu_items = []
        
        page_func = HydrusData.Call( ClientPaths.LaunchPathInWebBrowser, os.path.join( HC.HELP_DIR, 'downloader_parsers_formulae.html#html_formula' ) )
        
        menu_items.append( ( 'normal', 'open the html formula help', 'Open the help page for html formulae in your web browser.', page_func ) )
        
        help_button = ClientGUIMenuButton.MenuBitmapButton( self, CC.global_pixmaps().help, menu_items )
        
        help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help for this panel -->', object_name = 'HydrusIndeterminate' )
        
        #
        
        test_panel = ClientGUICommon.StaticBox( self, 'test' )
        
        self._test_panel = TestPanelFormula( test_panel, self.GetValue, test_data = test_data )
        
        #
        
        edit_panel = ClientGUICommon.StaticBox( self, 'edit' )
        
        self._tag_rules = QW.QListWidget( edit_panel )
        self._tag_rules.setSelectionMode( QW.QAbstractItemView.SingleSelection )

        self._tag_rules.itemDoubleClicked.connect( self.Edit )
        
        self._add_rule = ClientGUICommon.BetterButton( edit_panel, 'add', self.Add )
        
        self._edit_rule = ClientGUICommon.BetterButton( edit_panel, 'edit', self.Edit )
        
        self._move_rule_up = ClientGUICommon.BetterButton( edit_panel, '\u2191', self.MoveUp )
        
        self._delete_rule = ClientGUICommon.BetterButton( edit_panel, 'X', self.Delete )
        
        self._move_rule_down = ClientGUICommon.BetterButton( edit_panel, '\u2193', self.MoveDown )
        
        self._content_to_fetch = ClientGUICommon.BetterChoice( edit_panel )
        
        self._content_to_fetch.addItem( 'attribute', ClientParsing.HTML_CONTENT_ATTRIBUTE )
        self._content_to_fetch.addItem( 'string', ClientParsing.HTML_CONTENT_STRING )
        self._content_to_fetch.addItem( 'html', ClientParsing.HTML_CONTENT_HTML )
        
        self._content_to_fetch.currentIndexChanged.connect( self._UpdateControls )
        
        self._attribute_to_fetch = QW.QLineEdit( edit_panel )
        
        tag_rules = formula.GetTagRules()
        content_to_fetch = formula.GetContentToFetch()
        attribute_to_fetch = formula.GetAttributeToFetch()
        string_processor = formula.GetStringProcessor()
        
        self._string_processor_button = ClientGUIStringControls.StringProcessorButton( edit_panel, string_processor, self._test_panel.GetTestDataForStringProcessor )
        
        #
        
        for rule in tag_rules:
            
            pretty_rule = rule.ToString()
            
            item = QW.QListWidgetItem()
            item.setText( pretty_rule )
            item.setData( QC.Qt.UserRole, rule )
            self._tag_rules.addItem( item )
            
        
        self._content_to_fetch.SetValue( content_to_fetch )
        
        self._attribute_to_fetch.setText( attribute_to_fetch )
        
        self._UpdateControls()
        
        #
        
        udd_button_vbox = QP.VBoxLayout()
        
        udd_button_vbox.addStretch( 1 )
        QP.AddToLayout( udd_button_vbox, self._move_rule_up, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( udd_button_vbox, self._delete_rule, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( udd_button_vbox, self._move_rule_down, CC.FLAGS_CENTER_PERPENDICULAR )
        udd_button_vbox.addStretch( 1 )
        
        tag_rules_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( tag_rules_hbox, self._tag_rules, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( tag_rules_hbox, udd_button_vbox, CC.FLAGS_CENTER_PERPENDICULAR )
        
        ae_button_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( ae_button_hbox, self._add_rule, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( ae_button_hbox, self._edit_rule, CC.FLAGS_CENTER_PERPENDICULAR )
        
        rows = []
        
        rows.append( ( 'content to fetch:', self._content_to_fetch ) )
        rows.append( ( 'attribute to fetch: ', self._attribute_to_fetch ) )
        
        gridbox = ClientGUICommon.WrapInGrid( edit_panel, rows )
        
        edit_panel.Add( tag_rules_hbox, CC.FLAGS_EXPAND_BOTH_WAYS )
        edit_panel.Add( ae_button_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        edit_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        edit_panel.Add( ClientGUICommon.BetterStaticText( edit_panel, 'Newlines are removed from parsed strings right after parsing, before string processing.', ellipsize_end = True ), CC.FLAGS_EXPAND_PERPENDICULAR )
        edit_panel.Add( self._string_processor_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        test_panel.Add( self._test_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, edit_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, test_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, help_hbox, CC.FLAGS_ON_RIGHT )
        QP.AddToLayout( vbox, hbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
    def _UpdateControls( self ):
        
        if self._content_to_fetch.GetValue() == ClientParsing.HTML_CONTENT_ATTRIBUTE:
            
            self._attribute_to_fetch.setEnabled( True )
            
        else:
            
            self._attribute_to_fetch.setEnabled( False )
            
        
    
    def Add( self ):
        
        dlg_title = 'edit tag rule'
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, dlg_title, frame_key = 'deeply_nested_dialog' ) as dlg:
            
            new_rule = ClientParsing.ParseRuleHTML()
            
            panel = EditHTMLTagRulePanel( dlg, new_rule )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                rule = panel.GetValue()
                
                pretty_rule = rule.ToString()
                
                item = QW.QListWidgetItem()
                item.setText( pretty_rule )
                item.setData( QC.Qt.UserRole, rule )
                self._tag_rules.addItem( item )
                
            
        
    
    def Delete( self ):
        
        selection = QP.ListWidgetGetSelection( self._tag_rules ) 
        
        if selection != -1:
            
            QP.ListWidgetDelete( self._tag_rules, selection )
            
        
    
    def Edit( self ):
        
        selection = QP.ListWidgetGetSelection( self._tag_rules ) 
        
        if selection != -1:
            
            rule = QP.GetClientData( self._tag_rules, selection )
            
            dlg_title = 'edit tag rule'
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, dlg_title, frame_key = 'deeply_nested_dialog' ) as dlg:
                
                panel = EditHTMLTagRulePanel( dlg, rule )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    rule = panel.GetValue()
                    
                    pretty_rule = rule.ToString()
                    
                    self._tag_rules.item( selection ).setText( pretty_rule )
                    self._tag_rules.item( selection ).setData( QC.Qt.UserRole, rule )
                    
                
            
        
    
    def GetValue( self ):
        
        tags_rules = [ QP.GetClientData( self._tag_rules, i ) for i in range( self._tag_rules.count() ) ]
        
        content_to_fetch = self._content_to_fetch.GetValue()
        
        attribute_to_fetch = self._attribute_to_fetch.text()
        
        if content_to_fetch == ClientParsing.HTML_CONTENT_ATTRIBUTE and attribute_to_fetch == '':
            
            raise HydrusExceptions.VetoException( 'Please enter an attribute to fetch!' )
            
        
        string_processor = self._string_processor_button.GetValue()
        
        formula = ClientParsing.ParseFormulaHTML( tags_rules, content_to_fetch, attribute_to_fetch, string_processor )
        
        return formula
        
    
    def MoveDown( self ):
        
        selection = QP.ListWidgetGetSelection( self._tag_rules ) 
        
        if selection != -1 and selection + 1 < self._tag_rules.count():
            
            pretty_rule = self._tag_rules.item( selection ).text()
            rule = QP.GetClientData( self._tag_rules, selection )
            
            QP.ListWidgetDelete( self._tag_rules, selection )
            
            item = QW.QListWidgetItem()
            item.setText( pretty_rule )
            item.setData( QC.Qt.UserRole, rule )
            self._tag_rules.insertItem( selection + 1, item )
            
        
    
    def MoveUp( self ):
        
        selection = QP.ListWidgetGetSelection( self._tag_rules ) 
        
        if selection != -1 and selection > 0:
            
            pretty_rule = self._tag_rules.item( selection ).text()
            rule = QP.GetClientData( self._tag_rules, selection )
            
            QP.ListWidgetDelete( self._tag_rules, selection )
            
            item = QW.QListWidgetItem()
            item.setText( pretty_rule )
            item.setData( QC.Qt.UserRole, rule )
            self._tag_rules.insertItem( selection - 1, item )
            
        
    
class EditJSONParsingRulePanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, rule: ClientParsing.ParseRuleHTML ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._parse_rule_type = ClientGUICommon.BetterChoice( self )
        
        self._parse_rule_type.addItem( 'dictionary entry', ClientParsing.JSON_PARSE_RULE_TYPE_DICT_KEY )
        self._parse_rule_type.addItem( 'all dictionary/list items', ClientParsing.JSON_PARSE_RULE_TYPE_ALL_ITEMS )
        self._parse_rule_type.addItem( 'indexed item', ClientParsing.JSON_PARSE_RULE_TYPE_INDEXED_ITEM )
        
        string_match = ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FIXED, match_value = 'posts', example_string = 'posts' )
        
        self._string_match = ClientGUIStringPanels.EditStringMatchPanel( self, string_match )
        
        self._index = QP.MakeQSpinBox( self, min=-65536, max=65535 )
        self._index.setToolTip( 'You can make this negative to do negative indexing, i.e. "Select the second from last item".' )
        
        #
        
        ( parse_rule_type, parse_rule ) = rule
        
        self._parse_rule_type.SetValue( parse_rule_type )
        
        if parse_rule_type == ClientParsing.JSON_PARSE_RULE_TYPE_INDEXED_ITEM:
            
            self._index.setValue( parse_rule )
            
        elif parse_rule_type == ClientParsing.JSON_PARSE_RULE_TYPE_DICT_KEY:
            
            self._string_match.SetValue( parse_rule )
            
        
        self._UpdateHideShow()
        
        #
        
        vbox = QP.VBoxLayout()
        
        rows = []
        
        rows.append( ( 'list index: ', self._index ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        QP.AddToLayout( vbox, self._parse_rule_type, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._string_match, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self.widget().setLayout( vbox )
        
        #
        
        self._parse_rule_type.currentIndexChanged.connect( self._UpdateHideShow )
        
    
    def _UpdateHideShow( self ):
        
        self._string_match.setEnabled( False )
        self._index.setEnabled( False )
        
        parse_rule_type = self._parse_rule_type.GetValue()
        
        if parse_rule_type == ClientParsing.JSON_PARSE_RULE_TYPE_DICT_KEY:
            
            self._string_match.setEnabled( True )
            
        elif parse_rule_type == ClientParsing.JSON_PARSE_RULE_TYPE_INDEXED_ITEM:
            
            self._index.setEnabled( True )
            
        
    
    def GetValue( self ):
        
        parse_rule_type = self._parse_rule_type.GetValue()
        
        if parse_rule_type == ClientParsing.JSON_PARSE_RULE_TYPE_DICT_KEY:
            
            parse_rule = self._string_match.GetValue()
            
        elif parse_rule_type == ClientParsing.JSON_PARSE_RULE_TYPE_INDEXED_ITEM:
            
            parse_rule = self._index.value()
            
        elif parse_rule_type == ClientParsing.JSON_PARSE_RULE_TYPE_ALL_ITEMS:
            
            parse_rule = None
            
        
        return ( parse_rule_type, parse_rule )
        
    
class EditJSONFormulaPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, formula: ClientParsing.ParseFormulaJSON, test_data: ClientParsing.ParsingTestData ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        #
        
        menu_items = []
        
        page_func = HydrusData.Call( ClientPaths.LaunchPathInWebBrowser, os.path.join( HC.HELP_DIR, 'downloader_parsers_formulae.html#json_formula' ) )
        
        menu_items.append( ( 'normal', 'open the json formula help', 'Open the help page for json formulae in your web browser.', page_func ) )
        
        help_button = ClientGUIMenuButton.MenuBitmapButton( self, CC.global_pixmaps().help, menu_items )
        
        help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help for this panel -->', object_name = 'HydrusIndeterminate' )
        
        #
        
        test_panel = ClientGUICommon.StaticBox( self, 'test' )
        
        self._test_panel = TestPanelFormula( test_panel, self.GetValue, test_data = test_data )
        
        #
        
        edit_panel = ClientGUICommon.StaticBox( self, 'edit' )
        
        self._parse_rules = QW.QListWidget( edit_panel )
        self._parse_rules.setSelectionMode( QW.QAbstractItemView.SingleSelection )
        self._parse_rules.itemDoubleClicked.connect( self.Edit )
        
        self._add_rule = ClientGUICommon.BetterButton( edit_panel, 'add', self.Add )
        
        self._edit_rule = ClientGUICommon.BetterButton( edit_panel, 'edit', self.Edit )
        
        self._move_rule_up = ClientGUICommon.BetterButton( edit_panel, '\u2191', self.MoveUp )
        
        self._delete_rule = ClientGUICommon.BetterButton( edit_panel, 'X', self.Delete )
        
        self._move_rule_down = ClientGUICommon.BetterButton( edit_panel, '\u2193', self.MoveDown )
        
        self._content_to_fetch = ClientGUICommon.BetterChoice( edit_panel )
        
        self._content_to_fetch.addItem( 'string', ClientParsing.JSON_CONTENT_STRING )
        self._content_to_fetch.addItem( 'dictionary keys', ClientParsing.JSON_CONTENT_DICT_KEYS )
        self._content_to_fetch.addItem( 'json', ClientParsing.JSON_CONTENT_JSON )
        
        parse_rules = formula.GetParseRules()
        content_to_fetch = formula.GetContentToFetch()
        string_processor = formula.GetStringProcessor()
        
        self._string_processor_button = ClientGUIStringControls.StringProcessorButton( edit_panel, string_processor, self._test_panel.GetTestDataForStringProcessor )
        
        #
        
        for rule in parse_rules:
            
            pretty_rule = ClientParsing.RenderJSONParseRule( rule )
            
            item = QW.QListWidgetItem()
            item.setText( pretty_rule )
            item.setData( QC.Qt.UserRole, rule )
            self._parse_rules.addItem( item )
            
        
        self._content_to_fetch.SetValue( content_to_fetch )
        
        #
        
        udd_button_vbox = QP.VBoxLayout()
        
        udd_button_vbox.addStretch( 1 )
        QP.AddToLayout( udd_button_vbox, self._move_rule_up, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( udd_button_vbox, self._delete_rule, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( udd_button_vbox, self._move_rule_down, CC.FLAGS_CENTER_PERPENDICULAR )
        udd_button_vbox.addStretch( 1 )
        
        parse_rules_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( parse_rules_hbox, self._parse_rules, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( parse_rules_hbox, udd_button_vbox, CC.FLAGS_CENTER_PERPENDICULAR )
        
        ae_button_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( ae_button_hbox, self._add_rule, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( ae_button_hbox, self._edit_rule, CC.FLAGS_CENTER_PERPENDICULAR )
        
        rows = []
        
        rows.append( ( 'content to fetch:', self._content_to_fetch ) )
        
        gridbox = ClientGUICommon.WrapInGrid( edit_panel, rows )
        
        edit_panel.Add( parse_rules_hbox, CC.FLAGS_EXPAND_BOTH_WAYS )
        edit_panel.Add( ae_button_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        edit_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        edit_panel.Add( ClientGUICommon.BetterStaticText( edit_panel, 'Newlines are removed from parsed strings right after parsing, before string processing.', ellipsize_end = True ), CC.FLAGS_EXPAND_PERPENDICULAR )
        edit_panel.Add( self._string_processor_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        test_panel.Add( self._test_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, edit_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, test_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, help_hbox, CC.FLAGS_ON_RIGHT )
        QP.AddToLayout( vbox, hbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
    def Add( self ):
        
        dlg_title = 'edit parse rule'
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, dlg_title, frame_key = 'deeply_nested_dialog' ) as dlg:
            
            new_rule = ( ClientParsing.JSON_PARSE_RULE_TYPE_DICT_KEY, ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FIXED, match_value = 'posts', example_string = 'posts' ) )
            
            panel = EditJSONParsingRulePanel( dlg, new_rule )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                rule = panel.GetValue()
                
                pretty_rule = ClientParsing.RenderJSONParseRule( rule )

                item = QW.QListWidgetItem()
                item.setText( pretty_rule )
                item.setData( QC.Qt.UserRole, rule )
                self._parse_rules.addItem( item )
                
            
        
    
    def Delete( self ):
        
        selection = QP.ListWidgetGetSelection( self._parse_rules ) 
        
        if selection != -1:
            
            QP.ListWidgetDelete( self._parse_rules, selection )
            
        
    
    def Edit( self ):
        
        selection = QP.ListWidgetGetSelection( self._parse_rules ) 
        
        if selection != -1:
            
            rule = QP.GetClientData( self._parse_rules, selection )
            
            dlg_title = 'edit parse rule'
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, dlg_title, frame_key = 'deeply_nested_dialog' ) as dlg:
                
                panel = EditJSONParsingRulePanel( dlg, rule )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    rule = panel.GetValue()
                    
                    pretty_rule = ClientParsing.RenderJSONParseRule( rule )
                    
                    self._parse_rules.item( selection ).setText( pretty_rule )
                    self._parse_rules.item( selection ).setData( QC.Qt.UserRole, rule )
                    
                
            
        
    
    def GetValue( self ):
        
        parse_rules = [ QP.GetClientData( self._parse_rules, i ) for i in range( self._parse_rules.count() ) ]
        
        content_to_fetch = self._content_to_fetch.GetValue()
        
        string_processor = self._string_processor_button.GetValue()
        
        formula = ClientParsing.ParseFormulaJSON( parse_rules, content_to_fetch, string_processor )
        
        return formula
        
    
    def MoveDown( self ):
        
        selection = QP.ListWidgetGetSelection( self._parse_rules ) 
        
        if selection != -1 and selection + 1 < self._parse_rules.count():
            
            pretty_rule = self._parse_rules.item( selection ).text()
            rule = QP.GetClientData( self._parse_rules, selection )
            
            QP.ListWidgetDelete( self._parse_rules, selection )
            
            item = QW.QListWidgetItem()
            item.setText( pretty_rule )
            item.setData( QC.Qt.UserRole, rule )
            self._parse_rules.insertItem( selection + 1, item )
            
        
    
    def MoveUp( self ):
        
        selection = QP.ListWidgetGetSelection( self._parse_rules ) 
        
        if selection != -1 and selection > 0:
            
            pretty_rule = self._parse_rules.item( selection ).text()
            rule = QP.GetClientData( self._parse_rules, selection )
            
            QP.ListWidgetDelete( self._parse_rules, selection )
            
            item = QW.QListWidgetItem()
            item.setText( pretty_rule )
            item.setData( QC.Qt.UserRole, rule )
            self._parse_rules.insertItem( selection - 1, item )
            
        
    
class EditContentParserPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, content_parser: ClientParsing.ContentParser, test_data: ClientParsing.ParsingTestData, permitted_content_types ):
        
        self._original_content_parser = content_parser
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        #
        
        menu_items = []
        
        page_func = HydrusData.Call( ClientPaths.LaunchPathInWebBrowser, os.path.join( HC.HELP_DIR, 'downloader_parsers_content_parsers.html#content_parsers' ) )
        
        menu_items.append( ( 'normal', 'open the content parsers help', 'Open the help page for content parsers in your web browser.', page_func ) )
        
        help_button = ClientGUIMenuButton.MenuBitmapButton( self, CC.global_pixmaps().help, menu_items )
        
        help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help for this panel -->', object_name = 'HydrusIndeterminate' )
        
        #
        
        test_panel = ClientGUICommon.StaticBox( self, 'test' )
        
        self._test_panel = TestPanel( test_panel, self.GetValue, test_data = test_data )
        
        #
        
        self._edit_panel = ClientGUICommon.StaticBox( self, 'edit' )
        
        self._name = QW.QLineEdit( self._edit_panel )
        
        self._content_panel = ClientGUICommon.StaticBox( self._edit_panel, 'content type' )
        
        self._content_type = ClientGUICommon.BetterChoice( self._content_panel )
        
        types_to_str = {}
        
        types_to_str[ HC.CONTENT_TYPE_URLS ] = 'urls'
        types_to_str[ HC.CONTENT_TYPE_MAPPINGS ] = 'tags'
        types_to_str[ HC.CONTENT_TYPE_HASH ] = 'file hash'
        types_to_str[ HC.CONTENT_TYPE_TIMESTAMP ] = 'timestamp'
        types_to_str[ HC.CONTENT_TYPE_TITLE ] = 'watcher title'
        types_to_str[ HC.CONTENT_TYPE_VETO ] = 'veto'
        types_to_str[ HC.CONTENT_TYPE_VARIABLE ] = 'temporary variable'
        
        for permitted_content_type in permitted_content_types:
            
            self._content_type.addItem( types_to_str[ permitted_content_type ], permitted_content_type )
            
        
        self._content_type.currentIndexChanged.connect( self.EventContentTypeChange )
        
        self._urls_panel = QW.QWidget( self._content_panel )
        
        self._url_type = ClientGUICommon.BetterChoice( self._urls_panel )
        
        self._url_type.addItem( 'url to download/pursue (file/post url)', HC.URL_TYPE_DESIRED )
        self._url_type.addItem( 'POST parsers only: url to associate (source url)', HC.URL_TYPE_SOURCE )
        self._url_type.addItem( 'GALLERY parsers only: next gallery page (not queued if no post/file urls found)', HC.URL_TYPE_NEXT )
        self._url_type.addItem( 'GALLERY parsers only: sub-gallery page (is queued even if no post/file urls found--be careful, only use if you know you need it)', HC.URL_TYPE_SUB_GALLERY )
        
        self._file_priority = QP.MakeQSpinBox( self._urls_panel, min=0, max=100 )
        self._file_priority.setValue( 50 )
        
        self._mappings_panel = QW.QWidget( self._content_panel )
        
        self._namespace = QW.QLineEdit( self._mappings_panel )
        
        self._hash_panel = QW.QWidget( self._content_panel )
        
        self._hash_type = ClientGUICommon.BetterChoice( self._hash_panel )
        
        for hash_type in ( 'md5', 'sha1', 'sha256', 'sha512' ):
            
            self._hash_type.addItem( hash_type, hash_type )
            
        
        self._hash_encoding = ClientGUICommon.BetterChoice( self._hash_panel )
        
        for hash_encoding in ( 'hex', 'base64' ):
            
            self._hash_encoding.addItem( hash_encoding, hash_encoding )
            
        
        self._timestamp_panel = QW.QWidget( self._content_panel )
        
        self._timestamp_type = ClientGUICommon.BetterChoice( self._timestamp_panel )
        
        self._timestamp_type.addItem( 'source time', HC.TIMESTAMP_TYPE_SOURCE )
        
        self._title_panel = QW.QWidget( self._content_panel )
        
        self._title_priority = QP.MakeQSpinBox( self._title_panel, min=0, max=100 )
        self._title_priority.setValue( 50 )
        
        self._veto_panel = QW.QWidget( self._content_panel )
        
        self._veto_if_matches_found = QW.QCheckBox( self._veto_panel )
        self._string_match = ClientGUIStringPanels.EditStringMatchPanel( self._veto_panel, ClientStrings.StringMatch() )
        
        self._temp_variable_panel = QW.QWidget( self._content_panel )
        
        self._temp_variable_name = QW.QLineEdit( self._temp_variable_panel )
        
        ( name, content_type, formula, additional_info ) = content_parser.ToTuple()
        
        self._formula = EditFormulaPanel( self._edit_panel, formula, self._test_panel.GetTestDataForChild )
        
        #
        
        self._name.setText( name )
        
        self._content_type.SetValue( content_type )
        
        if content_type == HC.CONTENT_TYPE_URLS:
            
            ( url_type, priority ) = additional_info
            
            self._url_type.SetValue( url_type )
            self._file_priority.setValue( priority )
            
        elif content_type == HC.CONTENT_TYPE_MAPPINGS:
            
            namespace = additional_info
            
            self._namespace.setText( namespace )
            
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
        self._content_panel.Add( self._urls_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._content_panel.Add( self._mappings_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._content_panel.Add( self._hash_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._content_panel.Add( self._timestamp_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._content_panel.Add( self._title_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._content_panel.Add( self._veto_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._content_panel.Add( self._temp_variable_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
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
        
        choice = self._content_type.GetValue()
        
        self._urls_panel.setVisible( False )
        self._mappings_panel.setVisible( False )
        self._hash_panel.setVisible( False )
        self._timestamp_panel.setVisible( False )
        self._title_panel.setVisible( False )
        self._veto_panel.setVisible( False )
        self._temp_variable_panel.setVisible( False )
        
        if choice == HC.CONTENT_TYPE_URLS:
            
            self._urls_panel.show()
            
        elif choice == HC.CONTENT_TYPE_MAPPINGS:
            
            self._mappings_panel.show()
            
        elif choice == HC.CONTENT_TYPE_HASH:
            
            self._hash_panel.show()
            
        elif choice == HC.CONTENT_TYPE_TIMESTAMP:
            
            self._timestamp_panel.show()
            
        elif choice == HC.CONTENT_TYPE_TITLE:
            
            self._title_panel.show()
            
        elif choice == HC.CONTENT_TYPE_VETO:
            
            self._veto_panel.show()
            
        elif choice == HC.CONTENT_TYPE_VARIABLE:
            
            self._temp_variable_panel.show()
            
        
    
    def GetValue( self ):
        
        name = self._name.text()
        
        content_type = self._content_type.GetValue()
        
        formula = self._formula.GetValue()
        
        if content_type == HC.CONTENT_TYPE_URLS:
            
            url_type = self._url_type.GetValue()
            priority = self._file_priority.value()
            
            additional_info = ( url_type, priority )
            
        elif content_type == HC.CONTENT_TYPE_MAPPINGS:
            
            namespace = self._namespace.text()
            
            additional_info = namespace
            
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
            
            return result == QW.QDialog.Accepted
            
        else:
            
            return True
            
        
    
class EditContentParsersPanel( ClientGUICommon.StaticBox ):
    
    def __init__( self, parent: QW.QWidget, test_data_callable: typing.Callable[ [], ClientParsing.ParsingTestData ], permitted_content_types ):
        
        ClientGUICommon.StaticBox.__init__( self, parent, 'content parsers' )
        
        self._test_data_callable = test_data_callable
        self._permitted_content_types = permitted_content_types
        
        content_parsers_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        self._content_parsers = ClientGUIListCtrl.BetterListCtrl( content_parsers_panel, CGLC.COLUMN_LIST_CONTENT_PARSERS.ID, 6, self._ConvertContentParserToListCtrlTuples, use_simple_delete = True, activation_callback = self._Edit )
        
        content_parsers_panel.SetListCtrl( self._content_parsers )
        
        content_parsers_panel.AddButton( 'add', self._Add )
        content_parsers_panel.AddButton( 'edit', self._Edit, enabled_only_on_selection = True )
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
            
            if dlg_edit.exec() == QW.QDialog.Accepted:
                
                new_content_parser = panel.GetValue()
                
                self._AddContentParser( new_content_parser )
                
            
        
    
    def _AddContentParser( self, content_parser ):
        
        HydrusSerialisable.SetNonDupeName( content_parser, self._GetExistingNames() )
        
        self._content_parsers.AddDatas( ( content_parser, ) )
        
        self._content_parsers.Sort()
        
    
    def _ConvertContentParserToListCtrlTuples( self, content_parser ):
        
        name = content_parser.GetName()
        
        produces = list( content_parser.GetParsableContent() )
        
        pretty_name = name
        
        pretty_produces = ClientParsing.ConvertParsableContentToPrettyString( produces, include_veto = True )
        
        display_tuple = ( pretty_name, pretty_produces )
        sort_tuple = ( name, produces )
        
        return ( display_tuple, sort_tuple )
        
    
    def _Edit( self ):
        
        content_parsers = self._content_parsers.GetData( only_selected = True )
        
        for content_parser in content_parsers:
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit content parser', frame_key = 'deeply_nested_dialog' ) as dlg:
                
                test_data = self._test_data_callable()
                
                panel = EditContentParserPanel( dlg, content_parser, test_data, self._permitted_content_types )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    edited_content_parser = panel.GetValue()
                    
                    self._content_parsers.DeleteDatas( ( content_parser, ) )
                    
                    HydrusSerialisable.SetNonDupeName( edited_content_parser, self._GetExistingNames() )
                    
                    self._content_parsers.AddDatas( ( edited_content_parser, ) )
                    
                else:
                    
                    break
                    
                
            
        
        self._content_parsers.Sort()
        
    
    def _GetExistingNames( self ):
        
        names = { content_parser.GetName() for content_parser in self._content_parsers.GetData() }
        
        return names
        
    
    def GetData( self ):
        
        return self._content_parsers.GetData()
        
    
    def AddDatas( self, content_parsers ):
        
        self._content_parsers.AddDatas( content_parsers )
        
        self._content_parsers.Sort()
        
    
class EditNodes( QW.QWidget ):
    
    def __init__( self, parent, nodes, referral_url_callable, example_data_callable ):
        
        QW.QWidget.__init__( self, parent )
        
        self._referral_url_callable = referral_url_callable
        self._example_data_callable = example_data_callable
        
        self._nodes = ClientGUIListCtrl.BetterListCtrl( self, CGLC.COLUMN_LIST_NODES.ID, 20, self._ConvertNodeToTuples, delete_key_callback = self.Delete, activation_callback = self.Edit )
        
        menu_items = []
        
        menu_items.append( ( 'normal', 'content node', 'A node that parses the given data for content.', self.AddContentNode ) )
        menu_items.append( ( 'normal', 'link node', 'A node that parses the given data for a link, which it then pursues.', self.AddLinkNode ) )
        
        self._add_button = ClientGUIMenuButton.MenuButton( self, 'add', menu_items )
        
        self._copy_button = ClientGUICommon.BetterButton( self, 'copy', self.Copy )
        
        self._paste_button = ClientGUICommon.BetterButton( self, 'paste', self.Paste )
        
        self._duplicate_button = ClientGUICommon.BetterButton( self, 'duplicate', self.Duplicate )
        
        self._edit_button = ClientGUICommon.BetterButton( self, 'edit', self.Edit )
        
        self._delete_button = ClientGUICommon.BetterButton( self, 'delete', self.Delete )
        
        #
        
        self._nodes.AddDatas( nodes )
        
        #
        
        vbox = QP.VBoxLayout()
        
        button_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( button_hbox, self._add_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( button_hbox, self._copy_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( button_hbox, self._paste_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( button_hbox, self._duplicate_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( button_hbox, self._edit_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( button_hbox, self._delete_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        QP.AddToLayout( vbox, self._nodes, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, button_hbox, CC.FLAGS_ON_RIGHT )
        
        self.setLayout( vbox )
        
    
    def _ConvertNodeToTuples( self, node ):
        
        ( name, node_type, produces ) = node.ToPrettyStrings()
        
        return ( ( name, node_type, produces ), ( name, node_type, produces ) )
        
    
    def _GetExportObject( self ):
        
        to_export = HydrusSerialisable.SerialisableList()
        
        for node in self._nodes.GetData( only_selected = True ):
            
            to_export.append( node )
            
        
        if len( to_export ) == 0:
            
            return None
            
        elif len( to_export ) == 1:
            
            return to_export[0]
            
        else:
            
            return to_export
            
        
    
    def _ImportObject( self, obj ):
        
        if isinstance( obj, HydrusSerialisable.SerialisableList ):
            
            for sub_obj in obj:
                
                self._ImportObject( sub_obj )
                
            
        else:
            
            if isinstance( obj, ( ClientParsing.ContentParser, ClientParsing.ParseNodeContentLink ) ):
                
                node = obj
                
                self._nodes.AddDatas( [ node ] )
                
            else:
                
                QW.QMessageBox.warning( self, 'Warning', 'That was not a script--it was a: '+type(obj).__name__ )
                
            
        
    
    def AddContentNode( self ):
        
        dlg_title = 'edit content node'
        
        empty_node = ClientParsing.ContentParser()
        
        panel_class = EditContentParserPanel
        
        self.AddNode( dlg_title, empty_node, panel_class )
        
    
    def AddLinkNode( self ):
        
        dlg_title = 'edit link node'
        
        empty_node = ClientParsing.ParseNodeContentLink()
        
        panel_class = EditParseNodeContentLinkPanel
        
        self.AddNode( dlg_title, empty_node, panel_class )
        
    
    def AddNode( self, dlg_title, empty_node, panel_class ):
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, dlg_title, frame_key = 'deeply_nested_dialog' ) as dlg_edit:
            
            referral_url = self._referral_url_callable()
            example_data = self._example_data_callable()
            
            if isinstance( empty_node, ClientParsing.ContentParser ):
                
                panel = panel_class( dlg_edit, empty_node, ClientParsing.ParsingTestData( {}, ( example_data, ) ), [ HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_TYPE_VETO ] )
                
            else:
                
                panel = panel_class( dlg_edit, empty_node, referral_url, example_data )
                
            
            dlg_edit.SetPanel( panel )
            
            if dlg_edit.exec() == QW.QDialog.Accepted:
                
                new_node = panel.GetValue()
                
                self._nodes.AddDatas( [ new_node ] )
                
            
        
    
    def Copy( self ):
        
        export_object = self._GetExportObject()
        
        if export_object is not None:
            
            json = export_object.DumpToString()
            
            HG.client_controller.pub( 'clipboard', 'text', json )
            
        
    
    def Delete( self ):
        
        text = 'Remove all selected?'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, text )
        
        if result == QW.QDialog.Accepted:
            
            self._nodes.DeleteSelected()
            
        
    
    def Duplicate( self ):
        
        nodes_to_dupe = self._nodes.GetData( only_selected = True )
        
        for node in nodes_to_dupe:
            
            dupe_node = node.Duplicate()
            
            self._nodes.AddDatas( [ dupe_node ] )
            
        
    
    def Edit( self ):
        
        for node in self._nodes.GetData( only_selected = True ):
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit node', frame_key = 'deeply_nested_dialog' ) as dlg:
                
                referral_url = self._referral_url_callable()
                example_data = self._example_data_callable()
                
                if isinstance( node, ClientParsing.ContentParser ):
                    
                    panel = EditContentParserPanel( dlg, node, ClientParsing.ParsingTestData( {}, ( example_data, ) ), [ HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_TYPE_VETO ] )
                    
                elif isinstance( node, ClientParsing.ParseNodeContentLink ):
                    
                    panel = EditParseNodeContentLinkPanel( dlg, node, example_data = example_data )
                    
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    edited_node = panel.GetValue()
                    
                    self._nodes.ReplaceData( node, edited_node )
                    
                
                
            
        
    
    def GetValue( self ):
        
        return self._nodes.GetData()
        
    
    def Paste( self ):
        
        try:
            
            raw_text = HG.client_controller.GetClipboardText()
            
        except HydrusExceptions.DataMissing as e:
            
            QW.QMessageBox.critical( self, 'Error', str(e) )
            
            return
            
        
        try:
            
            obj = HydrusSerialisable.CreateFromString( raw_text )
            
            self._ImportObject( obj )
            
        except:
            
            QW.QMessageBox.critical( self, 'Error', 'I could not understand what was in the clipboard' )
            
        
    
class EditParseNodeContentLinkPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, node, referral_url = None, example_data = None ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        if referral_url is None:
            
            referral_url = 'test-url.com/test_query'
            
        
        self._referral_url = referral_url
        
        if example_data is None:
            
            example_data = ''
            
        
        self._my_example_url = None
        
        notebook = QW.QTabWidget( self )
        
        ( name, formula, children ) = node.ToTuple()
        
        #
        
        edit_panel = QW.QWidget( notebook )
        
        self._name = QW.QLineEdit( edit_panel )
        
        self._formula = EditFormulaPanel( edit_panel, formula, self.GetTestData )
        
        children_panel = ClientGUICommon.StaticBox( edit_panel, 'content parsing children' )
        
        self._children = EditNodes( children_panel, children, self.GetExampleURL, self.GetExampleData )
        
        #
        
        test_panel = QW.QWidget( notebook )
        
        self._example_data = QW.QPlainTextEdit( test_panel )
        
        self._example_data.setMinimumHeight( 200 )
        
        self._example_data.setPlainText( example_data )
        
        self._test_parse = QW.QPushButton( 'test parse', test_panel )
        self._test_parse.clicked.connect( self.EventTestParse )
        
        self._results = QW.QPlainTextEdit( test_panel )
        
        self._results.setMinimumHeight( 200 )
        
        self._test_fetch_result = QW.QPushButton( 'try fetching the first result', test_panel )
        self._test_fetch_result.clicked.connect( self.EventTestFetchResult )
        self._test_fetch_result.setEnabled( False )
        
        self._my_example_data = QW.QPlainTextEdit( test_panel )
        
        #
        
        info_panel = QW.QWidget( notebook )
        
        message = '''This node looks for one or more urls in the data it is given, requests each in turn, and gives the results to its children for further parsing.

If your previous query result responds with links to where the actual content is, use this node to bridge the gap.

The formula should attempt to parse full or relative urls. If the url is relative (like href="/page/123"), it will be appended to the referral url given by this node's parent. It will then attempt to GET them all.'''
        
        info_st = ClientGUICommon.BetterStaticText( info_panel, label = message )
        
        #
        
        self._name.setText( name )
        
        #
        
        children_panel.Add( self._children, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        vbox = QP.VBoxLayout()
        
        rows = []
        
        rows.append( ( 'name or description (optional): ', self._name ) )
        
        gridbox = ClientGUICommon.WrapInGrid( edit_panel, rows )
        
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, self._formula, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, children_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        edit_panel.setLayout( vbox )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._example_data, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, self._test_parse, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._results, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, self._test_fetch_result, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._my_example_data, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        test_panel.setLayout( vbox )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, info_st, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        info_panel.setLayout( vbox )
        
        #
        
        notebook.addTab( edit_panel, 'edit' )
        notebook.setCurrentWidget( edit_panel )
        notebook.addTab( test_panel, 'test' )
        notebook.addTab( info_panel, 'info' )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, notebook, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
        
    
    def EventTestFetchResult( self ):
        
        # this should be published to a job key panel or something so user can see it and cancel if needed
        
        network_job = ClientNetworkingJobs.NetworkJob( 'GET', self._my_example_url, referral_url = self._referral_url )
        
        network_job.OverrideBandwidth()
        
        HG.client_controller.network_engine.AddJob( network_job )
        
        try:
            
            network_job.WaitUntilDone()
            
        except HydrusExceptions.CancelledException:
            
            self._my_example_data.SetValue( 'fetch cancelled' )
            
            return
            
        except HydrusExceptions.NetworkException as e:
            
            self._my_example_data.SetValue( 'fetch failed' )
            
            raise
            
        
        example_text = network_job.GetContentText()
        
        self._example_data.SetValue( example_text )
        
    
    def EventTestParse( self ):
        
        def qt_code( parsed_urls ):
            
            if not self or not QP.isValid( self ):
                
                return
                
            
            if len( parsed_urls ) > 0:
                
                self._my_example_url = parsed_urls[0]
                self._test_fetch_result.setEnabled( True )
                
            
            result_lines = [ '*** ' + HydrusData.ToHumanInt( len( parsed_urls ) ) + ' RESULTS BEGIN ***' ]
            
            result_lines.extend( parsed_urls )
            
            result_lines.append( '*** RESULTS END ***' )
            
            results_text = os.linesep.join( result_lines )
            
            self._results.setPlainText( results_text )
            
        
        def do_it( node, data, referral_url ):
            
            try:
                
                stop_time = HydrusData.GetNow() + 30
                
                job_key = ClientThreading.JobKey( cancellable = True, stop_time = stop_time )
                
                parsed_urls = node.ParseURLs( job_key, data, referral_url )
                
                QP.CallAfter( qt_code, parsed_urls )
                
            except Exception as e:
                
                HydrusData.ShowException( e )
                
                message = 'Could not parse!'
                
                QP.CallAfter( QW.QMessageBox.critical, None, 'Error', message )
                
            
        
        node = self.GetValue()
        data = self._example_data.toPlainText()
        referral_url = self._referral_url
        
        HG.client_controller.CallToThread( do_it, node, data, referral_url )
        
    
    def GetExampleData( self ):
        
        return self._example_data.toPlainText()
        
    
    def GetExampleURL( self ):
        
        if self._my_example_url is not None:
            
            return self._my_example_url
            
        else:
            
            return ''
            
        
    
    def GetTestData( self ):
        
        return ClientParsing.ParsingTestData( {}, ( self._example_data.toPlainText(), ) )
        
    
    def GetValue( self ):
        
        name = self._name.text()
        
        formula = self._formula.GetValue()
        
        children = self._children.GetValue()
        
        node = ClientParsing.ParseNodeContentLink( name = name, formula = formula, children = children )
        
        return node
        
    
class EditPageParserPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, parser: ClientParsing.PageParser, formula = None, test_data = None ):
        
        self._original_parser = parser
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        if test_data is None:
            
            example_parsing_context = parser.GetExampleParsingContext()
            example_data = ''
            
            test_data = ClientParsing.ParsingTestData( example_parsing_context, ( example_data, ) )
            
        
        #
        
        menu_items = []
        
        page_func = HydrusData.Call( ClientPaths.LaunchPathInWebBrowser, os.path.join( HC.HELP_DIR, 'downloader_parsers_page_parsers.html#page_parsers' ) )
        
        menu_items.append( ( 'normal', 'open the page parser help', 'Open the help page for page parsers in your web browser.', page_func ) )
        
        help_button = ClientGUIMenuButton.MenuBitmapButton( self, CC.global_pixmaps().help, menu_items )
        
        help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help for this panel -->', object_name = 'HydrusIndeterminate' )
        
        #
        
        edit_panel = ClientGUICommon.StaticBox( self, 'edit' )
        
        edit_notebook = QW.QTabWidget( edit_panel )
        
        #
        
        main_panel = QW.QWidget( edit_notebook )
        
        self._name = QW.QLineEdit( main_panel )
        
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
            
            self._test_panel = TestPanelPageParser( test_panel, self.GetValue, self._string_converter.GetValue, test_data = test_data )
            
        else:
            
            self._test_panel = TestPanelPageParserSubsidiary( test_panel, self.GetValue, self._string_converter.GetValue, self.GetFormula, test_data = test_data )
            
        
        #
        
        example_urls_panel = ClientGUICommon.StaticBox( main_panel, 'example urls' )
        
        self._example_urls = ClientGUIListBoxes.AddEditDeleteListBox( example_urls_panel, 6, str, self._AddExampleURL, self._EditExampleURL )
        
        #
        
        formula_panel = QW.QWidget( edit_notebook )
        
        self._formula = EditFormulaPanel( formula_panel, formula, self._test_panel.GetTestData )
        
        #
        
        sub_page_parsers_notebook_panel = QW.QWidget( edit_notebook )
        
        #
        
        sub_page_parsers_panel = ClientGUIListCtrl.BetterListCtrlPanel( sub_page_parsers_notebook_panel )
        
        self._sub_page_parsers = ClientGUIListCtrl.BetterListCtrl( sub_page_parsers_panel, CGLC.COLUMN_LIST_SUB_PAGE_PARSERS.ID, 4, self._ConvertSubPageParserToListCtrlTuples, use_simple_delete = True, activation_callback = self._EditSubPageParser )
        
        sub_page_parsers_panel.SetListCtrl( self._sub_page_parsers )
        
        sub_page_parsers_panel.AddButton( 'add', self._AddSubPageParser )
        sub_page_parsers_panel.AddButton( 'edit', self._EditSubPageParser, enabled_only_on_selection = True )
        sub_page_parsers_panel.AddDeleteButton()
        
        #
        
        content_parsers_panel = QW.QWidget( edit_notebook )
        
        #
        
        permitted_content_types = [ HC.CONTENT_TYPE_URLS, HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_TYPE_HASH, HC.CONTENT_TYPE_TIMESTAMP, HC.CONTENT_TYPE_TITLE, HC.CONTENT_TYPE_VETO ]
        
        self._content_parsers = EditContentParsersPanel( content_parsers_panel, self._test_panel.GetTestDataForChild, permitted_content_types )
        
        #
        
        name = parser.GetName()
        
        ( sub_page_parsers, content_parsers ) = parser.GetContentParsers()
        
        example_urls = parser.GetExampleURLs()
        
        if len( example_urls ) > 0:
            
            self._test_url.setText( example_urls[0] )
            
        
        self._name.setText( name )
        
        self._sub_page_parsers.AddDatas( sub_page_parsers )
        
        self._sub_page_parsers.Sort()
        
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
        
        gridbox = ClientGUICommon.WrapInGrid( main_panel, rows )
        
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, conversion_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, example_urls_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        main_panel.setLayout( vbox )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._formula, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        formula_panel.setLayout( vbox )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, sub_page_parsers_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        sub_page_parsers_notebook_panel.setLayout( vbox )
        
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
        edit_notebook.addTab( sub_page_parsers_notebook_panel, 'subsidiary page parsers' )
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
        
        formula = ClientParsing.ParseFormulaHTML( tag_rules = [ ClientParsing.ParseRuleHTML( rule_type = ClientParsing.HTML_RULE_TYPE_DESCENDING, tag_name = 'div', tag_attributes = { 'class' : 'thumb' } ) ], content_to_fetch = ClientParsing.HTML_CONTENT_HTML )
        page_parser = ClientParsing.PageParser( 'new sub page parser' )
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit sub page parser', frame_key = 'deeply_nested_dialog' ) as dlg:
            
            panel = EditPageParserPanel( dlg, page_parser, formula = formula, test_data = self._test_panel.GetTestDataForChild() )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                new_page_parser = panel.GetValue()
                
                new_formula = panel.GetFormula()
                
                new_sub_page_parser = ( new_formula, new_page_parser )
                
                self._sub_page_parsers.AddDatas( ( new_sub_page_parser, ) )
                
                self._sub_page_parsers.Sort()
                
            
        
    
    def _ConvertSubPageParserToListCtrlTuples( self, sub_page_parser ):
        
        ( formula, page_parser ) = sub_page_parser
        
        name = page_parser.GetName()
        
        produces = page_parser.GetParsableContent()
        
        produces = sorted( produces )
        
        pretty_name = name
        pretty_formula = formula.ToPrettyString()
        pretty_produces = ClientParsing.ConvertParsableContentToPrettyString( produces )
        
        display_tuple = ( pretty_name, pretty_formula, pretty_produces )
        sort_tuple = ( name, pretty_formula, produces )
        
        return ( display_tuple, sort_tuple )
        
    
    def _EditExampleURL( self, example_url ):
        
        message = 'Enter example URL.'
        
        with ClientGUIDialogs.DialogTextEntry( self, message, default = example_url ) as dlg:
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                return dlg.GetValue()
                
            else:
                
                raise HydrusExceptions.VetoException()
                
            
        
    
    def _EditSubPageParser( self ):
        
        selected_data = self._sub_page_parsers.GetData( only_selected = True )
        
        for sub_page_parser in selected_data:
            
            ( formula, page_parser ) = sub_page_parser
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit sub page parser', frame_key = 'deeply_nested_dialog' ) as dlg:
                
                panel = EditPageParserPanel( dlg, page_parser, formula = formula, test_data = self._test_panel.GetTestDataForChild() )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    self._sub_page_parsers.DeleteDatas( ( sub_page_parser, ) )
                    
                    new_page_parser = panel.GetValue()
                    
                    new_formula = panel.GetFormula()
                    
                    new_sub_page_parser = ( new_formula, new_page_parser )
                    
                    self._sub_page_parsers.AddDatas( ( new_sub_page_parser, ) )
                    
                else:
                    
                    break
                    
                
            
        
        self._sub_page_parsers.Sort()
        
    
    def _FetchExampleData( self ):
        
        def wait_and_do_it( network_job ):
            
            def qt_tidy_up( example_data, example_bytes, error ):
                
                if not self or not QP.isValid( self ):
                    
                    return
                    
                
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
                    
                except:
                    
                    stuff_read = 'no response'
                    
                
                example_data = 'fetch failed: {}'.format( e ) + os.linesep * 2 + stuff_read
                
            
            QP.CallAfter( qt_tidy_up, example_data, example_bytes, error )
            
        
        url = self._test_url.text()
        referral_url = self._test_referral_url.text()
        
        if referral_url == '':
            
            referral_url = None
            
        
        network_job = ClientNetworkingJobs.NetworkJob( 'GET', url, referral_url = referral_url )
        
        network_job.OnlyTryConnectionOnce()
        
        self._test_network_job_control.ClearError()
        self._test_network_job_control.SetNetworkJob( network_job )
        
        network_job.OverrideBandwidth()
        
        HG.client_controller.network_engine.AddJob( network_job )
        
        HG.client_controller.CallToThread( wait_and_do_it, network_job )
        
    
    def GetFormula( self ):
        
        return self._formula.GetValue()
        
    
    def GetValue( self ):
        
        name = self._name.text()
        
        parser_key = self._original_parser.GetParserKey()
        
        string_converter = self._string_converter.GetValue()
        
        sub_page_parsers = self._sub_page_parsers.GetData()
        
        content_parsers = self._content_parsers.GetData()
        
        example_urls = self._example_urls.GetData()
        
        example_parsing_context = self._test_panel.GetExampleParsingContext()
        
        parser = ClientParsing.PageParser( name, parser_key = parser_key, string_converter = string_converter, sub_page_parsers = sub_page_parsers, content_parsers = content_parsers, example_urls = example_urls, example_parsing_context = example_parsing_context )
        
        return parser
        
    
    def UserIsOKToCancel( self ):
        
        original_parser = self._original_parser.Duplicate()
        current_parser = self.GetValue()
        
        original_parser.NullifyTestData()
        current_parser.NullifyTestData()
        
        if original_parser.GetSerialisableTuple() != current_parser.GetSerialisableTuple():
            
            text = 'It looks like you have made changes to the parser--are you sure you want to cancel?'
            
            result = ClientGUIDialogsQuick.GetYesNo( self, text )
            
            return result == QW.QDialog.Accepted
            
        else:
            
            return True
            
        
    
class EditParsersPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, parsers ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        parsers_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        self._parsers = ClientGUIListCtrl.BetterListCtrl( parsers_panel, CGLC.COLUMN_LIST_PARSERS.ID, 20, self._ConvertParserToListCtrlTuples, use_simple_delete = True, activation_callback = self._Edit )
        
        parsers_panel.SetListCtrl( self._parsers )
        
        parsers_panel.AddButton( 'add', self._Add )
        parsers_panel.AddButton( 'edit', self._Edit, enabled_only_on_selection = True )
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
            
            if dlg_edit.exec() == QW.QDialog.Accepted:
                
                new_parser = panel.GetValue()
                
                self._AddParser( new_parser )
                
                self._parsers.Sort()
                
            
        
    
    def _AddParser( self, parser ):
        
        HydrusSerialisable.SetNonDupeName( parser, self._GetExistingNames() )
        
        parser.RegenerateParserKey()
        
        self._parsers.AddDatas( ( parser, ) )
        
    
    def _ConvertParserToListCtrlTuples( self, parser ):
        
        name = parser.GetName()
        
        example_urls = sorted( parser.GetExampleURLs() )
        
        produces = parser.GetParsableContent()
        
        pretty_produces = ClientParsing.ConvertParsableContentToPrettyString( produces )
        
        sort_produces = pretty_produces
        
        pretty_name = name
        pretty_example_urls = ', '.join( example_urls )
        
        display_tuple = ( pretty_name, pretty_example_urls, pretty_produces )
        sort_tuple = ( name, example_urls, sort_produces )
        
        return ( display_tuple, sort_tuple )
        
    
    def _Edit( self ):
        
        parsers = self._parsers.GetData( only_selected = True )
        
        for parser in parsers:
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit parser', frame_key = 'deeply_nested_dialog' ) as dlg:
                
                panel = EditPageParserPanel( dlg, parser )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    edited_parser = panel.GetValue()
                    
                    self._parsers.DeleteDatas( ( parser, ) )
                    
                    HydrusSerialisable.SetNonDupeName( edited_parser, self._GetExistingNames() )
                    
                    self._parsers.AddDatas( ( edited_parser, ) )
                    
                else:
                    
                    break
                    
                
            
        
        self._parsers.Sort()
        
    
    def _GetExistingNames( self ):
        
        names = { parser.GetName() for parser in self._parsers.GetData() }
        
        return names
        
    
    def GetValue( self ):
        
        return self._parsers.GetData()
        
    
class EditParsingScriptFileLookupPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, script ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        ( name, url, query_type, file_identifier_type, file_identifier_string_converter, file_identifier_arg_name, static_args, children ) = script.ToTuple()
        
        #
        
        notebook = QW.QTabWidget( self )
        
        #
        
        edit_panel = QW.QWidget( notebook )
        
        self._name = QW.QLineEdit( edit_panel )
        
        query_panel = ClientGUICommon.StaticBox( edit_panel, 'query' )
        
        self._url = QW.QLineEdit( query_panel )
        
        self._url.setText( url )
        
        self._query_type = ClientGUICommon.BetterChoice( query_panel )
        
        self._query_type.addItem( 'GET', HC.GET )
        self._query_type.addItem( 'POST', HC.POST )
        
        self._file_identifier_type = ClientGUICommon.BetterChoice( query_panel )
        
        for t in [ ClientParsing.FILE_IDENTIFIER_TYPE_FILE, ClientParsing.FILE_IDENTIFIER_TYPE_MD5, ClientParsing.FILE_IDENTIFIER_TYPE_SHA1, ClientParsing.FILE_IDENTIFIER_TYPE_SHA256, ClientParsing.FILE_IDENTIFIER_TYPE_SHA512, ClientParsing.FILE_IDENTIFIER_TYPE_USER_INPUT ]:
            
            self._file_identifier_type.addItem( ClientParsing.file_identifier_string_lookup[ t], t )
            
        
        self._file_identifier_string_converter = ClientGUIStringControls.StringConverterButton( query_panel, file_identifier_string_converter )
        
        self._file_identifier_arg_name = QW.QLineEdit( query_panel )
        
        static_args_panel = ClientGUICommon.StaticBox( query_panel, 'static arguments' )
        
        self._static_args = ClientGUIStringControls.StringToStringDictControl( static_args_panel, static_args, min_height = 4 )
        
        children_panel = ClientGUICommon.StaticBox( edit_panel, 'content parsing children' )
        
        self._children = EditNodes( children_panel, children, self.GetExampleURL, self.GetExampleData )
        
        #
        
        test_panel = QW.QWidget( notebook )
        
        self._test_script_management = ScriptManagementControl( test_panel )
        
        self._test_arg = QW.QLineEdit( test_panel )
        
        self._test_arg.setText( 'enter example file path, hex hash, or raw user input here' )
        
        self._fetch_data = QW.QPushButton( 'fetch response', test_panel )
        self._fetch_data.clicked.connect( self.EventFetchData )
        
        self._example_data = QW.QPlainTextEdit( test_panel )
        
        self._example_data.setMinimumHeight( 200 )
        
        self._test_parsing = QW.QPushButton( 'test parse (note if you have \'link\' nodes, they will make their requests)', test_panel )
        self._test_parsing.clicked.connect( self.EventTestParse )
        
        self._results = QW.QPlainTextEdit( test_panel )
        
        self._results.setMinimumHeight( 200 )
        
        #
        
        info_panel = QW.QWidget( notebook )
        
        message = '''This script looks up tags for a single file.

It will download the result of a query that might look something like this:

https://www.file-lookup.com/form.php?q=getsometags&md5=[md5-in-hex]

And pass that html to a number of 'parsing children' that will each look through it in turn and try to find tags.'''
        
        info_st = ClientGUICommon.BetterStaticText( info_panel, label = message )
        
        info_st.setWordWrap( True )
        
        #
        
        self._name.setText( name )
        
        self._query_type.SetValue( query_type )
        self._file_identifier_type.SetValue( file_identifier_type )
        self._file_identifier_arg_name.setText( file_identifier_arg_name )
        
        self._results.setPlainText( 'Successfully parsed results will be printed here.' )
        
        #
        
        rows = []
        
        rows.append( ( 'url', self._url ) )
        rows.append( ( 'query type: ', self._query_type ) )
        rows.append( ( 'file identifier type: ', self._file_identifier_type ) )
        rows.append( ( 'file identifier conversion (typically to hex): ', self._file_identifier_string_converter ) )
        rows.append( ( 'file identifier GET/POST argument name: ', self._file_identifier_arg_name ) )
        
        gridbox = ClientGUICommon.WrapInGrid( query_panel, rows )
        
        static_args_panel.Add( self._static_args, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        query_message = 'This query will be executed first.'
        
        query_panel.Add( QW.QLabel( query_message, query_panel ), CC.FLAGS_EXPAND_PERPENDICULAR )
        query_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        query_panel.Add( static_args_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        children_message = 'The data returned by the query will be passed to each of these children for content parsing.'
        
        children_panel.Add( QW.QLabel( children_message, children_panel ), CC.FLAGS_EXPAND_PERPENDICULAR )
        children_panel.Add( self._children, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        vbox = QP.VBoxLayout()
        
        rows = []
        
        rows.append( ( 'script name: ', self._name ) )
        
        gridbox = ClientGUICommon.WrapInGrid( edit_panel, rows )
        
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, query_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, children_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        edit_panel.setLayout( vbox )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._test_script_management, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._test_arg, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._fetch_data, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._example_data, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, self._test_parsing, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._results, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        test_panel.setLayout( vbox )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, info_st, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        info_panel.setLayout( vbox )
        
        #
        
        notebook.addTab( edit_panel, 'edit' )
        notebook.setCurrentWidget( edit_panel )
        notebook.addTab( test_panel, 'test' )
        notebook.addTab( info_panel, 'info' )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, notebook, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
    def EventFetchData( self ):
        
        script = self.GetValue()
        
        test_arg = self._test_arg.text()
        
        file_identifier_type = self._file_identifier_type.GetValue()
        
        if file_identifier_type == ClientParsing.FILE_IDENTIFIER_TYPE_FILE:
            
            if not os.path.exists( test_arg ):
                
                QW.QMessageBox.critical( self, 'Error', 'That file does not exist!' )
                
                return
                
            
            file_identifier = test_arg
            
        elif file_identifier_type == ClientParsing.FILE_IDENTIFIER_TYPE_USER_INPUT:
            
            file_identifier = test_arg
            
        else:
            
            file_identifier = bytes.fromhex( test_arg )
            
        
        try:
            
            stop_time = HydrusData.GetNow() + 30
            
            job_key = ClientThreading.JobKey( cancellable = True, stop_time = stop_time )
            
            self._test_script_management.SetJobKey( job_key )
            
            parsing_text = script.FetchParsingText( job_key, file_identifier )
            
            try:
                
                self._example_data.setPlainText( parsing_text )
                
            except UnicodeDecodeError:
                
                self._example_data.setPlainText( 'The fetched data, which had length ' + HydrusData.ToHumanBytes( len( parsing_text ) ) + ', did not appear to be displayable text.' )
                
            
        except Exception as e:
            
            HydrusData.ShowException( e )
            
            message = 'Could not fetch data!'
            message += os.linesep * 2
            message += str( e )
            
            QW.QMessageBox.critical( self, 'Error', message )
            
        finally:
            
            job_key.Finish()
            
        
    
    def EventTestParse( self ):
        
        def qt_code( results ):
            
            if not self or not QP.isValid( self ):
                
                return
                
            
            result_lines = [ '*** ' + HydrusData.ToHumanInt( len( results ) ) + ' RESULTS BEGIN ***' ]
            
            result_lines.extend( ( ClientParsing.ConvertParseResultToPrettyString( result ) for result in results ) )
            
            result_lines.append( '*** RESULTS END ***' )
            
            results_text = os.linesep.join( result_lines )
            
            self._results.setPlainText( results_text )
            
        
        def do_it( script, job_key, data ):
            
            try:
                
                results = script.Parse( job_key, data )
                
                QP.CallAfter( qt_code, results )
                
            except Exception as e:
                
                HydrusData.ShowException( e )
                
                message = 'Could not parse!'
                
                QP.CallAfter( QW.QMessageBox.critical, None, 'Error', message )
                
            finally:
                
                job_key.Finish()
                
            
        
        script = self.GetValue()
        
        stop_time = HydrusData.GetNow() + 30
        
        job_key = ClientThreading.JobKey( cancellable = True, stop_time = stop_time )
        
        self._test_script_management.SetJobKey( job_key )
        
        data = self._example_data.toPlainText()
        
        HG.client_controller.CallToThread( do_it, script, job_key, data )
        
    
    def GetExampleData( self ):
        
        return self._example_data.toPlainText()
        
    
    def GetExampleURL( self ):
        
        return self._url.text()
        
    
    def GetValue( self ):
        
        name = self._name.text()
        url = self._url.text()
        query_type = self._query_type.GetValue()
        file_identifier_type = self._file_identifier_type.GetValue()
        file_identifier_string_converter = self._file_identifier_string_converter.GetValue()
        file_identifier_arg_name = self._file_identifier_arg_name.text()
        static_args = self._static_args.GetValue()
        children = self._children.GetValue()
        
        script = ClientParsing.ParseRootFileLookup( name, url = url, query_type = query_type, file_identifier_type = file_identifier_type, file_identifier_string_converter = file_identifier_string_converter, file_identifier_arg_name = file_identifier_arg_name, static_args = static_args, children = children )
        
        return script
        
    
class ManageParsingScriptsPanel( ClientGUIScrolledPanels.ManagePanel ):
    
    SCRIPT_TYPES = []
    
    SCRIPT_TYPES.append( HydrusSerialisable.SERIALISABLE_TYPE_PARSE_ROOT_FILE_LOOKUP )
    
    def __init__( self, parent ):
        
        ClientGUIScrolledPanels.ManagePanel.__init__( self, parent )
        
        self._scripts = ClientGUIListCtrl.BetterListCtrl( self, CGLC.COLUMN_LIST_PARSING_SCRIPTS.ID, 20, self._ConvertScriptToTuples, delete_key_callback = self.Delete, activation_callback = self.Edit )
        
        menu_items = []
        
        menu_items.append( ( 'normal', 'file lookup script', 'A script that fetches content for a known file.', self.AddFileLookupScript ) )
        
        self._add_button = ClientGUIMenuButton.MenuButton( self, 'add', menu_items )
        
        menu_items = []
        
        menu_items.append( ( 'normal', 'to clipboard', 'Serialise the script and put it on your clipboard.', self.ExportToClipboard ) )
        menu_items.append( ( 'normal', 'to png', 'Serialise the script and encode it to an image file you can easily share with other hydrus users.', self.ExportToPNG ) )
        
        self._export_button = ClientGUIMenuButton.MenuButton( self, 'export', menu_items )
        
        menu_items = []
        
        menu_items.append( ( 'normal', 'from clipboard', 'Load a script from text in your clipboard.', self.ImportFromClipboard ) )
        menu_items.append( ( 'normal', 'from png', 'Load a script from an encoded png.', self.ImportFromPNG ) )
        
        self._import_button = ClientGUIMenuButton.MenuButton( self, 'import', menu_items )
        
        self._duplicate_button = ClientGUICommon.BetterButton( self, 'duplicate', self.Duplicate )
        
        self._edit_button = ClientGUICommon.BetterButton( self, 'edit', self.Edit )
        
        self._delete_button = ClientGUICommon.BetterButton( self, 'delete', self.Delete )
        
        #
        
        scripts = []
        
        for script_type in self.SCRIPT_TYPES:
            
            scripts.extend( HG.client_controller.Read( 'serialisable_named', script_type ) )
            
        
        for script in scripts:
            
            self._scripts.AddDatas( ( script, ) )
            
        
        #
        
        vbox = QP.VBoxLayout()
        
        button_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( button_hbox, self._add_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( button_hbox, self._export_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( button_hbox, self._import_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( button_hbox, self._duplicate_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( button_hbox, self._edit_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( button_hbox, self._delete_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        QP.AddToLayout( vbox, self._scripts, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, button_hbox, CC.FLAGS_ON_RIGHT )
        
        self.widget().setLayout( vbox )
        
    
    def _ConvertScriptToTuples( self, script ):
        
        ( name, query_type, script_type, produces ) = script.ToPrettyStrings()
        
        return ( ( name, query_type, script_type, produces ), ( name, query_type, script_type, produces ) )
        
    
    def _GetExportObject( self ):
        
        to_export = HydrusSerialisable.SerialisableList()
        
        for script in self._scripts.GetData( only_selected = True ):
            
            to_export.append( script )
            
        
        if len( to_export ) == 0:
            
            return None
            
        elif len( to_export ) == 1:
            
            return to_export[0]
            
        else:
            
            return to_export
            
        
    
    def _ImportObject( self, obj ):
        
        if isinstance( obj, HydrusSerialisable.SerialisableList ):
            
            for sub_obj in obj:
                
                self._ImportObject( sub_obj )
                
            
        else:
            
            if isinstance( obj, ClientParsing.ParseRootFileLookup ):
                
                script = obj
                
                self._scripts.SetNonDupeName( script )
                
                self._scripts.AddDatas( ( script, ) )
                
            else:
                
                QW.QMessageBox.warning( self, 'Warning', 'That was not a script--it was a: '+type(obj).__name__ )
                
            
        
    
    def AddFileLookupScript( self ):
        
        name = 'new script'
        url = ''
        query_type = HC.GET
        file_identifier_type = ClientParsing.FILE_IDENTIFIER_TYPE_MD5
        file_identifier_string_converter = ClientStrings.StringConverter( ( ( ClientStrings.STRING_CONVERSION_ENCODE, 'hex' ), ), 'some hash bytes' )
        file_identifier_arg_name = 'md5'
        static_args = {}
        children = []
        
        dlg_title = 'edit file metadata lookup script'
        
        empty_script = ClientParsing.ParseRootFileLookup( name, url = url, query_type = query_type, file_identifier_type = file_identifier_type, file_identifier_string_converter = file_identifier_string_converter, file_identifier_arg_name = file_identifier_arg_name, static_args = static_args, children = children)
        
        panel_class = EditParsingScriptFileLookupPanel
        
        self.AddScript( dlg_title, empty_script, panel_class )
        
    
    def AddScript( self, dlg_title, empty_script, panel_class ):
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, dlg_title, frame_key = 'deeply_nested_dialog' ) as dlg_edit:
            
            panel = panel_class( dlg_edit, empty_script )
            
            dlg_edit.SetPanel( panel )
            
            if dlg_edit.exec() == QW.QDialog.Accepted:
                
                new_script = panel.GetValue()
                
                self._scripts.SetNonDupeName( new_script )
                
                self._scripts.AddDatas( ( new_script, ) )
                
            
        
    
    def CommitChanges( self ):
        
        scripts = self._scripts.GetData()
        
        HG.client_controller.Write( 'serialisables_overwrite', self.SCRIPT_TYPES, scripts )
        
    
    def Delete( self ):
        
        text = 'Remove all selected?'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, text )
        
        if result == QW.QDialog.Accepted:
            
            self._scripts.DeleteSelected()
            
        
    
    def Duplicate( self ):
        
        scripts_to_dupe = self._scripts.GetData( only_selected = True )
        
        for script in scripts_to_dupe:
            
            dupe_script = script.Duplicate()
            
            self._scripts.SetNonDupeName( dupe_script )
                       
            self._scripts.AddDatas( ( dupe_script, ) )
            
        
    
    def Edit( self ):
        
        for script in self._scripts.GetData( only_selected = True ):

            if isinstance( script, ClientParsing.ParseRootFileLookup ):
                
                panel_class = EditParsingScriptFileLookupPanel
                
                dlg_title = 'edit file lookup script'
                
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, dlg_title, frame_key = 'deeply_nested_dialog' ) as dlg:
                
                original_name = script.GetName()
                
                panel = panel_class( dlg, script )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    edited_script = panel.GetValue()
                    
                    if edited_script.GetName() != original_name:
                        
                        self._scripts.SetNonDupeName( edited_script )
                        
                    
                    self._scripts.ReplaceData( script, edited_script )
                    
                
                
            
        
    
    def ExportToClipboard( self ):
        
        export_object = self._GetExportObject()
        
        if export_object is not None:
            
            json = export_object.DumpToString()
            
            HG.client_controller.pub( 'clipboard', 'text', json )
            
        
    
    def ExportToPNG( self ):
        
        export_object = self._GetExportObject()
        
        if export_object is not None:
            
            with ClientGUITopLevelWindowsPanels.DialogNullipotent( self, 'export to png' ) as dlg:
                
                panel = ClientGUISerialisable.PNGExportPanel( dlg, export_object )
                
                dlg.SetPanel( panel )
                
                dlg.exec()
                
            
        
    
    def ImportFromClipboard( self ):
        
        try:
            
            raw_text = HG.client_controller.GetClipboardText()
            
        except HydrusExceptions.DataMissing as e:
            
            QW.QMessageBox.critical( self, 'Error', str(e) )
            
            return
            
        
        try:
            
            obj = HydrusSerialisable.CreateFromString( raw_text )
            
            self._ImportObject( obj )
            
        except Exception as e:
            
            QW.QMessageBox.critical( self, 'Error', 'I could not understand what was in the clipboard' )
            
        
    
    def ImportFromPNG( self ):
        
        with QP.FileDialog( self, 'select the png with the encoded script', wildcard = 'PNG (*.png)' ) as dlg:
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                path = dlg.GetPath()
                
                try:
                    
                    payload = ClientSerialisable.LoadFromPNG( path )
                    
                except Exception as e:
                    
                    QW.QMessageBox.critical( self, 'Error', str(e) )
                    
                    return
                    
                
                try:
                    
                    obj = HydrusSerialisable.CreateFromNetworkBytes( payload )
                    
                    self._ImportObject( obj )
                    
                except:
                    
                    QW.QMessageBox.critical( self, 'Error', 'I could not understand what was encoded in the png!' )
                    
                
            
        
    
class ScriptManagementControl( QW.QWidget ):
    
    def __init__( self, parent ):
        
        QW.QWidget.__init__( self, parent )
        
        self._job_key = None
        
        self._lock = threading.Lock()
        
        self._recent_urls = []
        
        main_panel = ClientGUICommon.StaticBox( self, 'script control' )
        
        self._status = ClientGUICommon.BetterStaticText( main_panel )
        self._gauge = ClientGUICommon.Gauge( main_panel )
        
        self._status.setWordWrap( True )
        
        self._link_button = ClientGUICommon.BetterBitmapButton( main_panel, CC.global_pixmaps().link, self.LinkButton )
        self._link_button.setToolTip( 'urls found by the script' )
        
        self._cancel_button = ClientGUICommon.BetterBitmapButton( main_panel, CC.global_pixmaps().stop, self.CancelButton )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._gauge, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, self._link_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._cancel_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        main_panel.Add( self._status, CC.FLAGS_EXPAND_PERPENDICULAR )
        main_panel.Add( hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, main_panel, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.setLayout( vbox )
        
        #
        
        self._Reset()
        
    
    def _Reset( self ):
        
        self._status.clear()
        self._gauge.SetRange( 1 )
        self._gauge.SetValue( 0 )
        
        self._link_button.setEnabled( False )
        self._cancel_button.setEnabled( False )
        
    
    def _Update( self ):
        
        if self._job_key is None:
            
            self._Reset()
            
        else:
            
            if self._job_key.HasVariable( 'script_status' ):
                
                status = self._job_key.GetIfHasVariable( 'script_status' )
                
            else:
                
                status = ''
                
            
            self._status.setText( status )
            
            if self._job_key.HasVariable( 'script_gauge' ):
                
                ( value, range ) = self._job_key.GetIfHasVariable( 'script_gauge' )
                
            else:
                
                ( value, range ) = ( 0, 1 )
                
            
            self._gauge.SetRange( range )
            self._gauge.SetValue( value )
            
            urls = self._job_key.GetURLs()
            
            if len( urls ) == 0:
                
                if self._link_button.isEnabled():
                    
                    self._link_button.setEnabled( False )
                    
                
            else:
                
                if not self._link_button.isEnabled():
                    
                    self._link_button.setEnabled( True )
                    
                
            
            if self._job_key.IsDone():
                
                if self._cancel_button.isEnabled():
                    
                    self._cancel_button.setEnabled( False )
                    
                
            else:
                
                if not self._cancel_button.isEnabled():
                    
                    self._cancel_button.setEnabled( True )
                    
                
            
        
    
    def TIMERUIUpdate( self ):
        
        with self._lock:
            
            self._Update()
            
            if self._job_key is None:
                
                HG.client_controller.gui.UnregisterUIUpdateWindow( self )
                
            
        
    
    def CancelButton( self ):
        
        with self._lock:
            
            if self._job_key is not None:
                
                self._job_key.Cancel()
                
            
        
    
    def LinkButton( self ):
        
        with self._lock:
            
            if self._job_key is None:
                
                return
                
            
            urls = self._job_key.GetURLs()
            
        
        menu = QW.QMenu()
        
        for url in urls:
            
            ClientGUIMenus.AppendMenuItem( menu, url, 'launch this url in your browser', ClientPaths.LaunchURLInWebBrowser, url )
            
        
        CGC.core().PopupMenu( self, menu )
        
        
    
    def SetJobKey( self, job_key ):
        
        with self._lock:
            
            self._job_key = job_key
            
        
        HG.client_controller.gui.RegisterUIUpdateWindow( self )
        
    
class TestPanel( QW.QWidget ):
    
    def __init__( self, parent, object_callable, test_data: typing.Optional[ ClientParsing.ParsingTestData ] = None ):
        
        QW.QWidget.__init__( self, parent )
        
        if test_data is None:
            
            test_data = ClientParsing.ParsingTestData( {}, ( '', ) )
            
        
        self._object_callable = object_callable
        
        self._example_parsing_context = ClientGUIStringControls.StringToStringDictButton( self, 'edit example parsing context' )
        
        self._data_preview_notebook = QW.QTabWidget( self )
        
        raw_data_panel = QW.QWidget( self._data_preview_notebook )
        
        self._example_data_raw_description = ClientGUICommon.BetterStaticText( raw_data_panel )
        
        self._copy_button = ClientGUICommon.BetterBitmapButton( raw_data_panel, CC.global_pixmaps().copy, self._Copy )
        self._copy_button.setToolTip( 'Copy the current example data to the clipboard.' )
        
        self._fetch_button = ClientGUICommon.BetterBitmapButton( raw_data_panel, CC.global_pixmaps().link, self._FetchFromURL )
        self._fetch_button.setToolTip( 'Fetch data from a URL.' )
        
        self._paste_button = ClientGUICommon.BetterBitmapButton( raw_data_panel, CC.global_pixmaps().paste, self._Paste )
        self._paste_button.setToolTip( 'Paste the current clipboard data into here.' )
        
        self._example_data_raw_preview = QW.QPlainTextEdit( raw_data_panel )
        self._example_data_raw_preview.setReadOnly( True )
        
        ( width, height ) = ClientGUIFunctions.ConvertTextToPixels( self._example_data_raw_preview, ( 60, 9 ) )
        
        self._example_data_raw_preview.setMinimumWidth( width )
        self._example_data_raw_preview.setMinimumHeight( height )
        
        self._test_parse = ClientGUICommon.BetterButton( self, 'test parse', self.TestParse )
        
        self._results = QW.QPlainTextEdit( self )
        
        ( width, height ) = ClientGUIFunctions.ConvertTextToPixels( self._results, ( 80, 12 ) )
        
        self._results.setMinimumWidth( width )
        self._results.setMinimumHeight( height )
        
        #
        
        self._example_parsing_context.SetValue( test_data.parsing_context )
        
        self._example_data_raw = ''
        
        self._results.setPlainText( 'Successfully parsed results will be printed here.' )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._example_data_raw_description, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, self._copy_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._fetch_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._paste_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, self._example_data_raw_preview, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        raw_data_panel.setLayout( vbox )
        
        self._data_preview_notebook.addTab( raw_data_panel, 'raw data' )
        self._data_preview_notebook.setCurrentWidget( raw_data_panel )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._example_parsing_context, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._data_preview_notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, self._test_parse, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._results, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.setLayout( vbox )
        
        if len( test_data.texts ) > 0:
            
            QP.CallAfter( self._SetExampleData, test_data.texts[0] )
            
        
    
    def _Copy( self ):
        
        HG.client_controller.pub( 'clipboard', 'text', self._example_data_raw )
        
    
    def _FetchFromURL( self ):
        
        def qt_code( example_data, example_bytes ):
            
            if not self or not QP.isValid( self ):
                
                return
                
            
            example_parsing_context = self._example_parsing_context.GetValue()
            
            example_parsing_context[ 'url' ] = url
            example_parsing_context[ 'post_index' ] = '0'
            
            self._example_parsing_context.SetValue( example_parsing_context )
            
            self._SetExampleData( example_data, example_bytes = example_bytes )
            
        
        def do_it( url ):
            
            network_job = ClientNetworkingJobs.NetworkJob( 'GET', url )
            
            network_job.OverrideBandwidth()
            
            HG.client_controller.network_engine.AddJob( network_job )
            
            example_bytes = None
            
            try:
                
                network_job.WaitUntilDone()
                
                example_data = network_job.GetContentText()
                
                example_bytes = network_job.GetContentBytes()
                
            except HydrusExceptions.CancelledException:
                
                example_data = 'fetch cancelled'
                
            except Exception as e:
                
                example_data = 'fetch failed:' + os.linesep * 2 + str( e )
                
                HydrusData.ShowException( e )
                
            
            QP.CallAfter( qt_code, example_data, example_bytes )
            
        
        message = 'Enter URL to fetch data for.'
        
        with ClientGUIDialogs.DialogTextEntry( self, message, placeholder = 'enter url', allow_blank = False) as dlg:
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                url = dlg.GetValue()
                
                HG.client_controller.CallToThread( do_it, url )
                
            
        
    
    def _Paste( self ):
        
        try:
            
            raw_text = HG.client_controller.GetClipboardText()
            
            try:
                
                raw_bytes = raw_text.decode( 'utf-8' )
                
            except:
                
                raw_bytes = None
                
            
        except HydrusExceptions.DataMissing as e:
            
            QW.QMessageBox.critical( self, 'Error', str(e) )
            
            return
            
        
        self._SetExampleData( raw_text, example_bytes = raw_bytes )
        
    
    def _SetExampleData( self, example_data, example_bytes = None ):
        
        self._example_data_raw = example_data
        
        test_parse_ok = True
        looked_like_json = False
        
        MAX_CHARS_IN_PREVIEW = 1024 * 64
        
        if len( example_data ) > 0:
            
            good_type_found = True
            
            if HydrusText.LooksLikeJSON( example_data ):
                
                # prioritise this, so if the JSON contains some HTML, it'll overwrite here. decent compromise
                
                looked_like_json = True
                
                parse_phrase = 'looks like JSON'
                
            elif HydrusText.LooksLikeHTML( example_data ):
                
                # can't just throw this at bs4 to see if it 'works', as it'll just wrap any unparsable string in some bare <html><body><p> tags
                
                parse_phrase = 'looks like HTML'
                
            else:
                
                good_type_found = False
                
                if example_bytes is not None:
                    
                    ( os_file_handle, temp_path ) = HydrusTemp.GetTempPath()
                    
                    try:
                        
                        with open( temp_path, 'wb' ) as f:
                            
                            f.write( example_bytes )
                            
                        
                        mime = HydrusFileHandling.GetMime( temp_path )
                        
                    except:
                        
                        mime = HC.APPLICATION_UNKNOWN
                        
                    finally:
                        
                        HydrusTemp.CleanUpTempPath( os_file_handle, temp_path )
                        
                    
                else:
                    
                    mime = HC.APPLICATION_UNKNOWN
                    
                
            
            if good_type_found:
                
                description = HydrusData.ToHumanBytes( len( example_data ) ) + ' total, ' + parse_phrase
                
                example_data_to_show = example_data
                
                if looked_like_json:
                    
                    try:
                        
                        j = HG.client_controller.parsing_cache.GetJSON( example_data )
                        
                        example_data_to_show = json.dumps( j, indent = 4 )
                        
                    except:
                        
                        pass
                        
                    
                
                if len( example_data_to_show ) > MAX_CHARS_IN_PREVIEW:
                    
                    preview = 'PREVIEW:' + os.linesep + str( example_data_to_show[:MAX_CHARS_IN_PREVIEW] )
                    
                else:
                    
                    preview = example_data_to_show
                    
                
            else:
                
                if mime in HC.ALLOWED_MIMES:
                    
                    description = 'that looked like a {}!'.format( HC.mime_string_lookup[ mime ] )
                    
                    preview = 'no preview'
                    
                    test_parse_ok = False
                    
                else:
                    
                    description = 'that did not look like HTML or JSON, but will try to show it anyway'
                    
                    if len( example_data ) > MAX_CHARS_IN_PREVIEW:
                        
                        preview = 'PREVIEW:' + os.linesep + repr( example_data[:MAX_CHARS_IN_PREVIEW] )
                        
                    else:
                        
                        preview = repr( example_data )
                        
                    
                
            
        else:
            
            description = 'no example data set yet'
            preview = ''
            
            test_parse_ok = False
            
        
        self._test_parse.setEnabled( test_parse_ok )
        
        self._example_data_raw_description.setText( description )
        self._example_data_raw_preview.setPlainText( preview )
        
    
    def GetExampleParsingContext( self ):
        
        return self._example_parsing_context.GetValue()
        
    
    def GetTestData( self ):
        
        example_parsing_context = self._example_parsing_context.GetValue()
        
        return ClientParsing.ParsingTestData( example_parsing_context, ( self._example_data_raw, ) )
        
    
    def GetTestDataForChild( self ):
        
        return self.GetTestData()
        
    
    def SetExampleData( self, example_data, example_bytes = None ):
        
        self._SetExampleData( example_data, example_bytes = example_bytes )
        
    
    def SetExampleParsingContext( self, example_parsing_context ):
        
        self._example_parsing_context.SetValue( example_parsing_context )
        
    
    def TestParse( self ):
        
        obj = self._object_callable()
        
        test_data = self.GetTestData()
        
        test_text = ''
        
        # change this to be for every text, do a diff panel, whatever
        
        if len( test_data.texts ) > 0:
            
            test_text = test_data.texts[0]
            
        
        try:
            
            if 'post_index' in test_data.parsing_context:
                
                del test_data.parsing_context[ 'post_index' ]
                
            
            results_text = obj.ParsePretty( test_data.parsing_context, test_data.texts[0] )
            
            self._results.setPlainText( results_text )
            
        except Exception as e:
            
            etype = type( e )
            
            ( etype, value, tb ) = sys.exc_info()
            
            trace = ''.join( traceback.format_exception( etype, value, tb ) )
            
            message = 'Exception:' + os.linesep + str( etype.__name__ ) + ': ' + str( e ) + os.linesep + trace
            
            self._results.setPlainText( message )
            
        
        
    
class TestPanelFormula( TestPanel ):
    
    def GetTestDataForStringProcessor( self ):
        
        example_parsing_context = self._example_parsing_context.GetValue()
        
        formula = self._object_callable()
        
        try:
            
            formula.SetStringProcessor( ClientStrings.StringProcessor() )
            
            texts = formula.Parse( example_parsing_context, self._example_data_raw )
            
        except:
            
            texts = [ '' ]
            
        
        return ClientParsing.ParsingTestData( example_parsing_context, texts )
        
    
class TestPanelPageParser( TestPanel ):
    
    def __init__( self, parent, object_callable, pre_parsing_converter_callable, test_data = None ):
        
        self._pre_parsing_converter_callable = pre_parsing_converter_callable
        
        TestPanel.__init__( self, parent, object_callable, test_data = test_data )
        
        post_conversion_panel = QW.QWidget( self._data_preview_notebook )
        
        self._example_data_post_conversion_description = ClientGUICommon.BetterStaticText( post_conversion_panel )
        
        self._copy_button_post_conversion = ClientGUICommon.BetterBitmapButton( post_conversion_panel, CC.global_pixmaps().copy, self._CopyPostConversion )
        self._copy_button_post_conversion.setToolTip( 'Copy the current post conversion data to the clipboard.' )
        
        self._refresh_post_conversion_button = ClientGUICommon.BetterBitmapButton( post_conversion_panel, CC.global_pixmaps().refresh, self._RefreshDataPreviews )
        self._example_data_post_conversion_preview = QW.QPlainTextEdit( post_conversion_panel )
        self._example_data_post_conversion_preview.setReadOnly( True )
        
        #
        
        self._example_data_post_conversion = ''
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._example_data_post_conversion_description, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, self._copy_button_post_conversion, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._refresh_post_conversion_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, self._example_data_post_conversion_preview, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        post_conversion_panel.setLayout( vbox )
        
        #
        
        self._data_preview_notebook.addTab( post_conversion_panel, 'post pre-parsing conversion' )
        
    
    def _CopyPostConversion( self ):
        
        HG.client_controller.pub( 'clipboard', 'text', self._example_data_post_conversion )
        
    
    def _RefreshDataPreviews( self ):
        
        self._SetExampleData( self._example_data_raw )
        
    
    def _SetExampleData( self, example_data, example_bytes = None ):
        
        TestPanel._SetExampleData( self, example_data, example_bytes = example_bytes )
        
        pre_parsing_converter = self._pre_parsing_converter_callable()
        
        if pre_parsing_converter.MakesChanges():
            
            try:
                
                post_conversion_example_data = ClientParsing.MakeParsedTextPretty( pre_parsing_converter.Convert( self._example_data_raw ) )
                
                if len( post_conversion_example_data ) > 1024:
                    
                    preview = 'PREVIEW:' + os.linesep + str( post_conversion_example_data[:1024] )
                    
                else:
                    
                    preview = post_conversion_example_data
                    
                
                parse_phrase = 'uncertain data type'
                
                # can't just throw this at bs4 to see if it 'works', as it'll just wrap any unparsable string in some bare <html><body><p> tags
                if HydrusText.LooksLikeHTML( post_conversion_example_data ):
                    
                    parse_phrase = 'looks like HTML'
                    
                
                # put this second, so if the JSON contains some HTML, it'll overwrite here. decent compromise
                if HydrusText.LooksLikeJSON( example_data ):
                    
                    parse_phrase = 'looks like JSON'
                    
                
                description = HydrusData.ToHumanBytes( len( post_conversion_example_data ) ) + ' total, ' + parse_phrase
                
            except Exception as e:
                
                post_conversion_example_data = self._example_data_raw
                
                etype = type( e )
                
                ( etype, value, tb ) = sys.exc_info()
                
                trace = ''.join( traceback.format_exception( etype, value, tb ) )
                
                message = 'Exception:' + os.linesep + str( etype.__name__ ) + ': ' + str( e ) + os.linesep + trace
                
                preview = message
                
                description = 'Could not convert.'
                
            
        else:
            
            post_conversion_example_data = self._example_data_raw
            
            preview = 'No changes made.'
            
            description = self._example_data_raw_description.text()
            
        
        self._example_data_post_conversion_description.setText( description )
        
        self._example_data_post_conversion = post_conversion_example_data
        
        self._example_data_post_conversion_preview.setPlainText( preview )
        
    
    def GetTestDataForChild( self ):
        
        example_parsing_context = self._example_parsing_context.GetValue()
        
        return ClientParsing.ParsingTestData( example_parsing_context, ( self._example_data_post_conversion, ) )
        
    
class TestPanelPageParserSubsidiary( TestPanelPageParser ):
    
    def __init__( self, parent, object_callable, pre_parsing_converter_callable, formula_callable, test_data = None ):
        
        TestPanelPageParser.__init__( self, parent, object_callable, pre_parsing_converter_callable, test_data = test_data )
        
        self._formula_callable = formula_callable
        
        post_separation_panel = QW.QWidget( self._data_preview_notebook )
        
        self._example_data_post_separation_description = ClientGUICommon.BetterStaticText( post_separation_panel )
        
        self._copy_button_post_separation = ClientGUICommon.BetterBitmapButton( post_separation_panel, CC.global_pixmaps().copy, self._CopyPostSeparation )
        self._copy_button_post_separation.setToolTip( 'Copy the current post separation data to the clipboard.' )
        
        self._refresh_post_separation_button = ClientGUICommon.BetterBitmapButton( post_separation_panel, CC.global_pixmaps().refresh, self._RefreshDataPreviews )
        self._example_data_post_separation_preview = QW.QPlainTextEdit( post_separation_panel )
        self._example_data_post_separation_preview.setReadOnly( True )
        
        #
        
        self._example_data_post_separation = []
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._example_data_post_separation_description, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, self._copy_button_post_separation, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._refresh_post_separation_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, self._example_data_post_separation_preview, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        post_separation_panel.setLayout( vbox )
        
        #
        
        self._data_preview_notebook.addTab( post_separation_panel, 'post separation' )
        
    
    def _CopyPostSeparation( self ):
        
        joiner = os.linesep * 2
        
        HG.client_controller.pub( 'clipboard', 'text', joiner.join( self._example_data_post_separation ) )
        
    
    def _SetExampleData( self, example_data, example_bytes = None ):
        
        TestPanelPageParser._SetExampleData( self, example_data, example_bytes = example_bytes )
        
        formula = self._formula_callable()
        
        if formula is None:
            
            separation_example_data = []
            description = 'No formula set!'
            preview = ''
            
        else:
            
            try:
                
                example_parsing_context = self._example_parsing_context.GetValue()
                
                separation_example_data = formula.Parse( example_parsing_context, self._example_data_post_conversion )
                
                joiner = os.linesep * 2
                
                preview = joiner.join( separation_example_data )
                
                if len( preview ) > 1024:
                    
                    preview = 'PREVIEW:' + os.linesep + str( preview[:1024] )
                    
                
                description = HydrusData.ToHumanInt( len( separation_example_data ) ) + ' subsidiary posts parsed'
                
            except Exception as e:
                
                separation_example_data = []
                
                etype = type( e )
                
                ( etype, value, tb ) = sys.exc_info()
                
                trace = ''.join( traceback.format_exception( etype, value, tb ) )
                
                message = 'Exception:' + os.linesep + str( etype.__name__ ) + ': ' + str( e ) + os.linesep + trace
                
                preview = message
                
                description = 'Could not convert.'
                
            
        
        self._example_data_post_separation_description.setText( description )
        
        self._example_data_post_separation = separation_example_data
        
        self._example_data_post_separation_preview.setPlainText( preview )
        
    
    def GetTestDataForChild( self ):
        
        example_parsing_context = self._example_parsing_context.GetValue()
        
        return ClientParsing.ParsingTestData( example_parsing_context, list( self._example_data_post_separation ) )
        
    
    def TestParse( self ):
        
        formula = self._formula_callable()
        
        page_parser = self._object_callable()
        
        try:
            
            test_data = self.GetTestData()
            
            test_data.parsing_context[ 'post_index' ] = 0
            
            if formula is None:
                
                posts = test_data.texts
                
            else:
                
                posts = []
                
                for test_text in test_data.texts:
                    
                    posts.extend( formula.Parse( test_data.parsing_context, test_text ) )
                    
                
            
            pretty_texts = []
            
            for post in posts:
                
                pretty_text = page_parser.ParsePretty( test_data.parsing_context, post )
                
                pretty_texts.append( pretty_text )
                
            
            separator = os.linesep * 2
            
            end_pretty_text = separator.join( pretty_texts )
            
            self._results.setPlainText( end_pretty_text )
            
        except Exception as e:
            
            etype = type( e )
            
            ( etype, value, tb ) = sys.exc_info()
            
            trace = ''.join( traceback.format_exception( etype, value, tb ) )
            
            message = 'Exception:' + os.linesep + str( etype.__name__ ) + ': ' + str( e ) + os.linesep + trace
            
            self._results.setPlainText( message )
            
        
    
    
