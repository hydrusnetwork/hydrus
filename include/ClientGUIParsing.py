import bs4
from . import ClientConstants as CC
from . import ClientData
from . import ClientDefaults
from . import ClientGUICommon
from . import ClientGUIDialogs
from . import ClientGUIDialogsQuick
from . import ClientGUIMenus
from . import ClientGUIControls
from . import ClientGUIFunctions
from . import ClientGUIListBoxes
from . import ClientGUIListCtrl
from . import ClientGUIScrolledPanels
from . import ClientGUIScrolledPanelsEdit
from . import ClientGUISerialisable
from . import ClientGUITopLevelWindows
from . import ClientNetworkingContexts
from . import ClientNetworkingDomain
from . import ClientNetworkingJobs
from . import ClientParsing
from . import ClientPaths
from . import ClientSerialisable
from . import ClientThreading
from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusExceptions
from . import HydrusGlobals as HG
from . import HydrusSerialisable
from . import HydrusTags
from . import HydrusText
import itertools
import json
import os
import sys
import threading
import traceback
import time
import wx

class DownloaderExportPanel( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent, network_engine ):
        
        ClientGUIScrolledPanels.ReviewPanel.__init__( self, parent )
        
        self._network_engine = network_engine
        
        menu_items = []
        
        page_func = HydrusData.Call( ClientPaths.LaunchPathInWebBrowser, os.path.join( HC.HELP_DIR, 'downloader_sharing.html' ) )
        
        menu_items.append( ( 'normal', 'open the downloader sharing help', 'Open the help page for sharing downloaders in your web browser.', page_func ) )
        
        help_button = ClientGUICommon.MenuBitmapButton( self, CC.GlobalBMPs.help, menu_items )
        
        help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help for this panel -->', wx.Colour( 0, 0, 255 ) )
        
        listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        columns = [ ( 'name', -1 ), ( 'type', 40 ) ]
        
        self._listctrl = ClientGUIListCtrl.BetterListCtrl( listctrl_panel, 'downloader_export', 14, 36, columns, self._ConvertContentToListCtrlTuples, use_simple_delete = True )
        
        self._listctrl.Sort( 1 )
        
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
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( help_hbox, CC.FLAGS_BUTTON_SIZER )
        vbox.Add( listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
    
    def _AddDomainMetadata( self ):
        
        message = 'Enter domain:'
        
        with ClientGUIDialogs.DialogTextEntry( self, message ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                domain = dlg.GetValue()
                
            else:
                
                return
                
            
        
        domain_metadatas = self._GetDomainMetadatasToInclude( { domain } )
        
        if len( domain_metadatas ) > 0:
            
            self._listctrl.AddDatas( domain_metadatas )
            
        else:
            
            wx.MessageBox( 'No headers/bandwidth rules found!' )
            
        
    
    def _AddGUG( self ):
        
        existing_data = self._listctrl.GetData()
        
        choosable_gugs = [ gug for gug in self._network_engine.domain_manager.GetGUGs() if gug.IsFunctional() and gug not in existing_data ]
        
        choice_tuples = [ ( gug.GetName(), gug, False ) for gug in choosable_gugs ]
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'select gugs' ) as dlg:
            
            panel = ClientGUIScrolledPanelsEdit.EditChooseMultiple( dlg, choice_tuples )
            
            dlg.SetPanel( panel )
            
            if dlg.ShowModal() == wx.ID_OK:
                
                gugs_to_include = panel.GetValue()
                
            else:
                
                return
                
            
        
        gugs_to_include = self._FleshOutNGUGsWithGUGs( gugs_to_include )
        
        domains = { ClientNetworkingDomain.ConvertURLIntoDomain( example_url ) for example_url in itertools.chain.from_iterable( ( gug.GetExampleURLs() for gug in gugs_to_include ) ) }
        
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
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'select login scripts' ) as dlg:
            
            panel = ClientGUIScrolledPanelsEdit.EditChooseMultiple( dlg, choice_tuples )
            
            dlg.SetPanel( panel )
            
            if dlg.ShowModal() == wx.ID_OK:
                
                login_scripts_to_include = panel.GetValue()
                
            else:
                
                return
                
            
        
        self._listctrl.AddDatas( login_scripts_to_include )
        
    
    def _AddParser( self ):
        
        existing_data = self._listctrl.GetData()
        
        choosable_parsers = [ p for p in self._network_engine.domain_manager.GetParsers() if p not in existing_data ]
        
        choice_tuples = [ ( parser.GetName(), parser, False ) for parser in choosable_parsers ]
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'select parsers' ) as dlg:
            
            panel = ClientGUIScrolledPanelsEdit.EditChooseMultiple( dlg, choice_tuples )
            
            dlg.SetPanel( panel )
            
            if dlg.ShowModal() == wx.ID_OK:
                
                parsers_to_include = panel.GetValue()
                
            else:
                
                return
                
            
        
        self._listctrl.AddDatas( parsers_to_include )
        
    
    def _AddURLClass( self ):
        
        existing_data = self._listctrl.GetData()
        
        choosable_url_classes = [ u for u in self._network_engine.domain_manager.GetURLClasses() if u not in existing_data ]
        
        choice_tuples = [ ( url_class.GetName(), url_class, False ) for url_class in choosable_url_classes ]
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'select url classes' ) as dlg:
            
            panel = ClientGUIScrolledPanelsEdit.EditChooseMultiple( dlg, choice_tuples )
            
            dlg.SetPanel( panel )
            
            if dlg.ShowModal() == wx.ID_OK:
                
                url_classes_to_include = panel.GetValue()
                
            else:
                
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
        
        with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
            
            if dlg.ShowModal() != wx.ID_YES:
                
                return
                
            
        
        gug_names = set()
        
        for obj in export_object:
            
            if isinstance( obj, ( ClientNetworkingDomain.GalleryURLGenerator, ClientNetworkingDomain.NestedGalleryURLGenerator ) ):
                
                gug_names.add( obj.GetName() )
                
            
        
        gug_names = list( gug_names )
        
        gug_names.sort()
        
        num_gugs = len( gug_names )
        
        with ClientGUITopLevelWindows.DialogNullipotent( self, 'export to png' ) as dlg:
            
            title = 'easy-import downloader png'
            
            if num_gugs == 0:
                
                description = 'some download components'
                
            else:
                
                title += ' - ' + HydrusData.ToHumanInt( num_gugs ) + ' downloaders'
                
                description = ', '.join( gug_names )
                
            
            panel = ClientGUISerialisable.PngExportPanel( dlg, export_object, title = title, description = description )
            
            dlg.SetPanel( panel )
            
            dlg.ShowModal()
            
        
    
    def _FleshOutNGUGsWithGUGs( self, gugs ):
        
        gugs_to_include = set( gugs )
        
        existing_data = self._listctrl.GetData()
        
        possible_new_gugs = [ gug for gug in self._network_engine.domain_manager.GetGUGs() if gug.IsFunctional() and gug not in existing_data and gug not in gugs_to_include ]
        
        interesting_gug_keys_and_names = list( itertools.chain.from_iterable( [ gug.GetGUGKeysAndNames() for gug in gugs_to_include if isinstance( gug, ClientNetworkingDomain.NestedGalleryURLGenerator ) ] ) )
        
        interesting_gugs = [ gug for gug in possible_new_gugs if gug.GetGUGKeyAndName() in interesting_gug_keys_and_names ]
        
        gugs_to_include.update( interesting_gugs )
        
        if True in ( isinstance( gug, ClientNetworkingDomain.NestedGalleryURLGenerator ) for gug in interesting_gugs ):
            
            return self._FleshOutNGUGsWithGUGs( gugs_to_include )
            
        else:
            
            return gugs_to_include
            
        
    
    def _FleshOutURLClassesWithAPILinks( self, url_classes ):
        
        url_classes_to_include = set( url_classes )
        
        api_links_dict = dict( ClientNetworkingDomain.ConvertURLClassesIntoAPIPairs( self._network_engine.domain_manager.GetURLClasses() ) )
        
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
        
        domains = { d for d in itertools.chain.from_iterable( ClientNetworkingDomain.ConvertDomainIntoAllApplicableDomains( domain ) for domain in domains ) }
        
        existing_domains = { obj.GetDomain() for obj in self._listctrl.GetData() if isinstance( obj, ClientNetworkingDomain.DomainMetadataPackage ) }
        
        domains = domains.difference( existing_domains )
        
        domains = list( domains )
        
        domains.sort()
        
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
            
            wx.MessageBox( domain_metadata.GetDetailedSafeSummary() )
            
        
        return domain_metadatas
        
    
    def _GetParsersToInclude( self, url_classes ):
        
        parsers_to_include = set()
        
        for url_class in url_classes:
            
            example_url = url_class.GetExampleURL()
            
            ( url_type, match_name, can_parse ) = self._network_engine.domain_manager.GetURLParseCapability( example_url )
            
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
            
            if isinstance( gug, ClientNetworkingDomain.GalleryURLGenerator ):
                
                example_urls = ( gug.GetExampleURL(), )
                
            elif isinstance( gug, ClientNetworkingDomain.NestedGalleryURLGenerator ):
                
                example_urls = gug.GetExampleURLs()
                
            
            for example_url in example_urls:
                
                url_class = self._network_engine.domain_manager.GetURLClass( example_url )
                
                if url_class is not None:
                    
                    url_classes_to_include.add( url_class )
                    
                    # add post url matches from same domain
                    
                    domain = ClientNetworkingDomain.ConvertURLIntoSecondLevelDomain( example_url )
                    
                    for um in list( self._network_engine.domain_manager.GetURLClasses() ):
                        
                        if ClientNetworkingDomain.ConvertURLIntoSecondLevelDomain( um.GetExampleURL() ) == domain and um.GetURLType() in ( HC.URL_TYPE_POST, HC.URL_TYPE_FILE ):
                            
                            url_classes_to_include.add( um )
                            
                        
                    
                
            
        
        existing_data = self._listctrl.GetData()
        
        return [ u for u in url_classes_to_include if u not in existing_data ]
        
    
class EditCompoundFormulaPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, formula, test_context ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        #
        
        menu_items = []
        
        page_func = HydrusData.Call( ClientPaths.LaunchPathInWebBrowser, os.path.join( HC.HELP_DIR, 'downloader_parsers_formulae.html#compound_formula' ) )
        
        menu_items.append( ( 'normal', 'open the compound formula help', 'Open the help page for compound formulae in your web browser.', page_func ) )
        
        help_button = ClientGUICommon.MenuBitmapButton( self, CC.GlobalBMPs.help, menu_items )
        
        help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help for this panel -->', wx.Colour( 0, 0, 255 ) )
        
        #
        
        edit_panel = ClientGUICommon.StaticBox( self, 'edit' )
        
        edit_panel.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
        
        self._formulae = wx.ListBox( edit_panel, style = wx.LB_SINGLE )
        self._formulae.Bind( wx.EVT_LEFT_DCLICK, self.EventEdit )
        
        self._add_formula = ClientGUICommon.BetterButton( edit_panel, 'add', self.Add )
        
        self._edit_formula = ClientGUICommon.BetterButton( edit_panel, 'edit', self.Edit )
        
        self._move_formula_up = ClientGUICommon.BetterButton( edit_panel, '\u2191', self.MoveUp )
        
        self._delete_formula = ClientGUICommon.BetterButton( edit_panel, 'X', self.Delete )
        
        self._move_formula_down = ClientGUICommon.BetterButton( edit_panel, '\u2193', self.MoveDown )
        
        self._sub_phrase = wx.TextCtrl( edit_panel )
        
        ( formulae, sub_phrase, string_match, string_converter ) = formula.ToTuple()
        
        self._string_match_button = ClientGUIControls.StringMatchButton( edit_panel, string_match )
        
        self._string_converter_button = ClientGUIControls.StringConverterButton( edit_panel, string_converter )
        
        #
        
        test_panel = ClientGUICommon.StaticBox( self, 'test' )
        
        test_panel.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
        
        self._test_panel = TestPanel( test_panel, self.GetValue, test_context = test_context )
        
        #
        
        for formula in formulae:
            
            pretty_formula = formula.ToPrettyString()
            
            self._formulae.Append( pretty_formula, formula )
            
        
        self._sub_phrase.SetValue( sub_phrase )
        
        #
        
        udd_button_vbox = wx.BoxSizer( wx.VERTICAL )
        
        udd_button_vbox.Add( ( 20, 20 ), CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        udd_button_vbox.Add( self._move_formula_up, CC.FLAGS_VCENTER )
        udd_button_vbox.Add( self._delete_formula, CC.FLAGS_VCENTER )
        udd_button_vbox.Add( self._move_formula_down, CC.FLAGS_VCENTER )
        udd_button_vbox.Add( ( 20, 20 ), CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        formulae_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        formulae_hbox.Add( self._formulae, CC.FLAGS_EXPAND_BOTH_WAYS )
        formulae_hbox.Add( udd_button_vbox, CC.FLAGS_VCENTER )
        
        ae_button_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        ae_button_hbox.Add( self._add_formula, CC.FLAGS_VCENTER )
        ae_button_hbox.Add( self._edit_formula, CC.FLAGS_VCENTER )
        
        rows = []
        
        rows.append( ( 'substitution phrase:', self._sub_phrase ) )
        
        gridbox = ClientGUICommon.WrapInGrid( edit_panel, rows )
        
        edit_panel.Add( formulae_hbox, CC.FLAGS_EXPAND_BOTH_WAYS )
        edit_panel.Add( ae_button_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        edit_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        edit_panel.Add( ClientGUICommon.BetterStaticText( edit_panel, 'Newlines are removed from parsed strings right after parsing, before this String Match is tested.', style = wx.ST_ELLIPSIZE_END ), CC.FLAGS_EXPAND_PERPENDICULAR )
        edit_panel.Add( self._string_match_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        edit_panel.Add( self._string_converter_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        test_panel.Add( self._test_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( edit_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        hbox.Add( test_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( help_hbox, CC.FLAGS_BUTTON_SIZER )
        vbox.Add( hbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
    
    def Add( self ):
        
        existing_formula = ClientParsing.ParseFormulaHTML()
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit formula', frame_key = 'deeply_nested_dialog' ) as dlg:
            
            panel = EditFormulaPanel( dlg, existing_formula, self._test_panel.GetTestContext )
            
            dlg.SetPanel( panel )
            
            if dlg.ShowModal() == wx.ID_OK:
                
                new_formula = panel.GetValue()
                
                pretty_formula = new_formula.ToPrettyString()
                
                self._formulae.Append( pretty_formula, new_formula )
                
            
        
    
    def Delete( self ):
        
        selection = self._formulae.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            if self._formulae.GetCount() == 1:
                
                wx.MessageBox( 'A compound formula needs at least one sub-formula!' )
                
            else:
                
                self._formulae.Delete( selection )
                
            
        
    
    def Edit( self ):
        
        selection = self._formulae.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            old_formula = self._formulae.GetClientData( selection )
            
            with ClientGUITopLevelWindows.DialogEdit( self, 'edit formula', frame_key = 'deeply_nested_dialog' ) as dlg:
                
                panel = EditFormulaPanel( dlg, old_formula, self._test_panel.GetTestContext )
                
                dlg.SetPanel( panel )
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    new_formula = panel.GetValue()
                    
                    pretty_formula = new_formula.ToPrettyString()
                    
                    self._formulae.SetString( selection, pretty_formula )
                    self._formulae.SetClientData( selection, new_formula )
                    
                
            
        
    
    def EventEdit( self, event ):
        
        self.Edit()
        
    
    def GetValue( self ):
        
        formulae = [ self._formulae.GetClientData( i ) for i in range( self._formulae.GetCount() ) ]
        
        sub_phrase = self._sub_phrase.GetValue()
        
        string_match = self._string_match_button.GetValue()
        
        string_converter = self._string_converter_button.GetValue()
        
        formula = ClientParsing.ParseFormulaCompound( formulae, sub_phrase, string_match, string_converter )
        
        return formula
        
    
    def MoveDown( self ):
        
        selection = self._formulae.GetSelection()
        
        if selection != wx.NOT_FOUND and selection + 1 < self._formulae.GetCount():
            
            pretty_rule = self._formulae.GetString( selection )
            rule = self._formulae.GetClientData( selection )
            
            self._formulae.Delete( selection )
            
            self._formulae.Insert( pretty_rule, selection + 1, rule )
            
        
    
    def MoveUp( self ):
        
        selection = self._formulae.GetSelection()
        
        if selection != wx.NOT_FOUND and selection > 0:
            
            pretty_rule = self._formulae.GetString( selection )
            rule = self._formulae.GetClientData( selection )
            
            self._formulae.Delete( selection )
            
            self._formulae.Insert( pretty_rule, selection - 1, rule )
            
        
    
class EditContextVariableFormulaPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, formula, test_context ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        #
        
        menu_items = []
        
        page_func = HydrusData.Call( ClientPaths.LaunchPathInWebBrowser, os.path.join( HC.HELP_DIR, 'downloader_parsers_formulae.html#context_variable_formula' ) )
        
        menu_items.append( ( 'normal', 'open the context variable formula help', 'Open the help page for context variable formulae in your web browser.', page_func ) )
        
        help_button = ClientGUICommon.MenuBitmapButton( self, CC.GlobalBMPs.help, menu_items )
        
        help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help for this panel -->', wx.Colour( 0, 0, 255 ) )
        
        #
        
        edit_panel = ClientGUICommon.StaticBox( self, 'edit' )
        
        edit_panel.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
        
        self._variable_name = wx.TextCtrl( edit_panel )
        
        ( variable_name, string_match, string_converter ) = formula.ToTuple()
        
        self._string_match_button = ClientGUIControls.StringMatchButton( edit_panel, string_match )
        
        self._string_converter_button = ClientGUIControls.StringConverterButton( edit_panel, string_converter )
        
        #
        
        test_panel = ClientGUICommon.StaticBox( self, 'test' )
        
        test_panel.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
        
        self._test_panel = TestPanel( test_panel, self.GetValue, test_context = test_context )
        
        #
        
        self._variable_name.SetValue( variable_name )
        
        #
        
        rows = []
        
        rows.append( ( 'variable name:', self._variable_name ) )
        
        gridbox = ClientGUICommon.WrapInGrid( edit_panel, rows )
        
        edit_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        edit_panel.Add( ClientGUICommon.BetterStaticText( edit_panel, 'Newlines are removed from parsed strings right after parsing, before this String Match is tested.', style = wx.ST_ELLIPSIZE_END ), CC.FLAGS_EXPAND_PERPENDICULAR )
        edit_panel.Add( self._string_match_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        edit_panel.Add( self._string_converter_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        test_panel.Add( self._test_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( edit_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        hbox.Add( test_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( help_hbox, CC.FLAGS_BUTTON_SIZER )
        vbox.Add( hbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
    
    def GetValue( self ):
        
        variable_name = self._variable_name.GetValue()
        
        string_match = self._string_match_button.GetValue()
        
        string_converter = self._string_converter_button.GetValue()
        
        formula = ClientParsing.ParseFormulaContextVariable( variable_name, string_match, string_converter )
        
        return formula
        
    
class EditFormulaPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, formula, test_context_callable ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._current_formula = formula
        self._test_context_callable = test_context_callable
        
        #
        
        my_panel = ClientGUICommon.StaticBox( self, 'formula' )
        
        self._formula_description = ClientGUICommon.SaneMultilineTextCtrl( my_panel )
        
        ( width, height ) = ClientGUIFunctions.ConvertTextToPixels( self._formula_description, ( 90, 8 ) )
        
        self._formula_description.SetInitialSize( ( width, height ) )
        
        self._formula_description.Disable()
        
        self._edit_formula = ClientGUICommon.BetterButton( my_panel, 'edit formula', self._EditFormula )
        
        self._change_formula_type = ClientGUICommon.BetterButton( my_panel, 'change formula type', self._ChangeFormulaType )
        
        #
        
        self._UpdateControls()
        
        #
        
        button_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        button_hbox.Add( self._edit_formula, CC.FLAGS_EXPAND_BOTH_WAYS )
        button_hbox.Add( self._change_formula_type, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        my_panel.Add( self._formula_description, CC.FLAGS_EXPAND_BOTH_WAYS )
        my_panel.Add( button_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( my_panel, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
    
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
            
        
        test_context = self._test_context_callable()
        
        dlg_title = 'edit formula'
        
        with ClientGUITopLevelWindows.DialogEdit( self, dlg_title, frame_key = 'deeply_nested_dialog' ) as dlg:
            
            panel = panel_class( dlg, self._current_formula, test_context )
            
            dlg.SetPanel( panel )
            
            if dlg.ShowModal() == wx.ID_OK:
                
                self._current_formula = panel.GetValue()
                
                self._UpdateControls()
                
            
        
    
    def _UpdateControls( self ):
        
        if self._current_formula is None:
            
            self._formula_description.SetValue( '' )
            
            self._edit_formula.Disable()
            self._change_formula_type.Disable()
            
        else:
            
            self._formula_description.SetValue( self._current_formula.ToPrettyMultilineString() )
            
            self._edit_formula.Enable()
            self._change_formula_type.Enable()
            
        
    
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
        
        self._rule_type.Append( 'search descendents', ClientParsing.HTML_RULE_TYPE_DESCENDING )
        self._rule_type.Append( 'walk back up ancestors', ClientParsing.HTML_RULE_TYPE_ASCENDING )
        
        self._tag_name = wx.TextCtrl( self )
        
        self._tag_attributes = ClientGUIControls.StringToStringDictControl( self, tag_attributes, min_height = 4 )
        
        self._tag_index = ClientGUICommon.NoneableSpinCtrl( self, 'index to fetch', none_phrase = 'get all', min = 0, max = 255 )
        
        self._tag_depth = wx.SpinCtrl( self, min = 1, max = 255 )
        
        self._should_test_tag_string = wx.CheckBox( self )
        
        self._tag_string_string_match = ClientGUIControls.StringMatchButton( self, tag_string_string_match )
        
        #
        
        self._rule_type.SelectClientData( rule_type )
        self._tag_name.SetValue( tag_name )
        self._tag_index.SetValue( tag_index )
        self._tag_depth.SetValue( tag_depth )
        self._should_test_tag_string.SetValue( should_test_tag_string )
        
        self._UpdateTypeControls()
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
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
        
        vbox.Add( self._current_description, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        vbox.Add( gridbox_1, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.Add( self._tag_attributes, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.Add( gridbox_2, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.Add( gridbox_3, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self.SetSizer( vbox )
        
        self._UpdateShouldTest()
        
        #
        
        self._rule_type.Bind( wx.EVT_CHOICE, self.EventTypeChanged )
        self._tag_name.Bind( wx.EVT_TEXT, self.EventVariableChanged )
        self._tag_attributes.Bind( ClientGUIListCtrl.EVT_LIST_CTRL, self.EventVariableChanged)
        self._tag_index.Bind( wx.EVT_SPINCTRL, self.EventVariableChanged )
        self._tag_depth.Bind( wx.EVT_SPINCTRL, self.EventVariableChanged )
        
        self._should_test_tag_string.Bind( wx.EVT_CHECKBOX, self.EventShouldTestChanged )
        
    
    def _UpdateShouldTest( self ):
        
        if self._should_test_tag_string.GetValue():
            
            self._tag_string_string_match.Enable()
            
        else:
            
            self._tag_string_string_match.Disable()
            
        
    
    def _UpdateTypeControls( self ):
        
        rule_type = self._rule_type.GetChoice()
        
        if rule_type == ClientParsing.HTML_RULE_TYPE_DESCENDING:
            
            self._tag_attributes.Enable()
            self._tag_index.Enable()
            
            self._tag_depth.Disable()
            
        else:
            
            self._tag_attributes.Disable()
            self._tag_index.Disable()
            
            self._tag_depth.Enable()
            
        
        self._UpdateDescription()
        
    
    def _UpdateDescription( self ):
        
        tag_rule = self.GetValue()
        
        label = tag_rule.ToString()
        
        self._current_description.SetLabelText( label )
        
    
    def EventShouldTestChanged( self, event ):
        
        self._UpdateShouldTest()
        
    
    def EventTypeChanged( self, event ):
        
        self._UpdateTypeControls()
        
        event.Skip()
        
    
    def EventVariableChanged( self, event ):
        
        self._UpdateDescription()
        
        event.Skip()
        
    
    def GetValue( self ):
        
        rule_type = self._rule_type.GetChoice()
        
        tag_name = self._tag_name.GetValue()
        
        if tag_name == '':
            
            tag_name = None
            
        
        should_test_tag_string = self._should_test_tag_string.GetValue()
        tag_string_string_match = self._tag_string_string_match.GetValue()
        
        if rule_type == ClientParsing.HTML_RULE_TYPE_DESCENDING:
            
            tag_attributes = self._tag_attributes.GetValue()
            tag_index = self._tag_index.GetValue()
            
            tag_rule = ClientParsing.ParseRuleHTML( rule_type = rule_type, tag_name = tag_name, tag_attributes = tag_attributes, tag_index = tag_index, should_test_tag_string = should_test_tag_string, tag_string_string_match = tag_string_string_match )
            
        elif rule_type == ClientParsing.HTML_RULE_TYPE_ASCENDING:
            
            tag_depth = self._tag_depth.GetValue()
            
            tag_rule = ClientParsing.ParseRuleHTML( rule_type = rule_type, tag_name = tag_name, tag_depth = tag_depth, should_test_tag_string = should_test_tag_string, tag_string_string_match = tag_string_string_match )
            
        
        return tag_rule
        
    
class EditHTMLFormulaPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, formula, test_context ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        #
        
        menu_items = []
        
        page_func = HydrusData.Call( ClientPaths.LaunchPathInWebBrowser, os.path.join( HC.HELP_DIR, 'downloader_parsers_formulae.html#html_formula' ) )
        
        menu_items.append( ( 'normal', 'open the html formula help', 'Open the help page for html formulae in your web browser.', page_func ) )
        
        help_button = ClientGUICommon.MenuBitmapButton( self, CC.GlobalBMPs.help, menu_items )
        
        help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help for this panel -->', wx.Colour( 0, 0, 255 ) )
        
        #
        
        edit_panel = ClientGUICommon.StaticBox( self, 'edit' )
        
        edit_panel.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
        
        self._tag_rules = wx.ListBox( edit_panel, style = wx.LB_SINGLE )
        self._tag_rules.Bind( wx.EVT_LEFT_DCLICK, self.EventEdit )
        
        self._add_rule = ClientGUICommon.BetterButton( edit_panel, 'add', self.Add )
        
        self._edit_rule = ClientGUICommon.BetterButton( edit_panel, 'edit', self.Edit )
        
        self._move_rule_up = ClientGUICommon.BetterButton( edit_panel, '\u2191', self.MoveUp )
        
        self._delete_rule = ClientGUICommon.BetterButton( edit_panel, 'X', self.Delete )
        
        self._move_rule_down = ClientGUICommon.BetterButton( edit_panel, '\u2193', self.MoveDown )
        
        self._content_to_fetch = ClientGUICommon.BetterChoice( edit_panel )
        
        self._content_to_fetch.Append( 'attribute', ClientParsing.HTML_CONTENT_ATTRIBUTE )
        self._content_to_fetch.Append( 'string', ClientParsing.HTML_CONTENT_STRING )
        self._content_to_fetch.Append( 'html', ClientParsing.HTML_CONTENT_HTML )
        
        self._content_to_fetch.Bind( wx.EVT_CHOICE, self.EventContentChoice )
        
        self._attribute_to_fetch = wx.TextCtrl( edit_panel )
        
        ( tag_rules, content_to_fetch, attribute_to_fetch, string_match, string_converter ) = formula.ToTuple()
        
        self._string_match_button = ClientGUIControls.StringMatchButton( edit_panel, string_match )
        
        self._string_converter_button = ClientGUIControls.StringConverterButton( edit_panel, string_converter )
        
        #
        
        test_panel = ClientGUICommon.StaticBox( self, 'test' )
        
        test_panel.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
        
        self._test_panel = TestPanel( test_panel, self.GetValue, test_context = test_context )
        
        #
        
        for rule in tag_rules:
            
            pretty_rule = rule.ToString()
            
            self._tag_rules.Append( pretty_rule, rule )
            
        
        self._content_to_fetch.SelectClientData( content_to_fetch )
        
        self._attribute_to_fetch.SetValue( attribute_to_fetch )
        
        self._UpdateControls()
        
        #
        
        udd_button_vbox = wx.BoxSizer( wx.VERTICAL )
        
        udd_button_vbox.Add( ( 20, 20 ), CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        udd_button_vbox.Add( self._move_rule_up, CC.FLAGS_VCENTER )
        udd_button_vbox.Add( self._delete_rule, CC.FLAGS_VCENTER )
        udd_button_vbox.Add( self._move_rule_down, CC.FLAGS_VCENTER )
        udd_button_vbox.Add( ( 20, 20 ), CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        tag_rules_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        tag_rules_hbox.Add( self._tag_rules, CC.FLAGS_EXPAND_BOTH_WAYS )
        tag_rules_hbox.Add( udd_button_vbox, CC.FLAGS_VCENTER )
        
        ae_button_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        ae_button_hbox.Add( self._add_rule, CC.FLAGS_VCENTER )
        ae_button_hbox.Add( self._edit_rule, CC.FLAGS_VCENTER )
        
        rows = []
        
        rows.append( ( 'content to fetch:', self._content_to_fetch ) )
        rows.append( ( 'attribute to fetch: ', self._attribute_to_fetch ) )
        
        gridbox = ClientGUICommon.WrapInGrid( edit_panel, rows )
        
        edit_panel.Add( tag_rules_hbox, CC.FLAGS_EXPAND_BOTH_WAYS )
        edit_panel.Add( ae_button_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        edit_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        edit_panel.Add( ClientGUICommon.BetterStaticText( edit_panel, 'Newlines are removed from parsed strings right after parsing, before this String Match is tested.', style = wx.ST_ELLIPSIZE_END ), CC.FLAGS_EXPAND_PERPENDICULAR )
        edit_panel.Add( self._string_match_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        edit_panel.Add( self._string_converter_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        test_panel.Add( self._test_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( edit_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        hbox.Add( test_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( help_hbox, CC.FLAGS_BUTTON_SIZER )
        vbox.Add( hbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
    
    def _UpdateControls( self ):
        
        if self._content_to_fetch.GetChoice() == ClientParsing.HTML_CONTENT_ATTRIBUTE:
            
            self._attribute_to_fetch.Enable()
            
        else:
            
            self._attribute_to_fetch.Disable()
            
        
    
    def Add( self ):
        
        dlg_title = 'edit tag rule'
        
        with ClientGUITopLevelWindows.DialogEdit( self, dlg_title, frame_key = 'deeply_nested_dialog' ) as dlg:
            
            new_rule = ClientParsing.ParseRuleHTML()
            
            panel = EditHTMLTagRulePanel( dlg, new_rule )
            
            dlg.SetPanel( panel )
            
            if dlg.ShowModal() == wx.ID_OK:
                
                rule = panel.GetValue()
                
                pretty_rule = rule.ToString()
                
                self._tag_rules.Append( pretty_rule, rule )
                
            
        
    
    def Delete( self ):
        
        selection = self._tag_rules.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            self._tag_rules.Delete( selection )
            
        
    
    def Edit( self ):
        
        selection = self._tag_rules.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            rule = self._tag_rules.GetClientData( selection )
            
            dlg_title = 'edit tag rule'
            
            with ClientGUITopLevelWindows.DialogEdit( self, dlg_title, frame_key = 'deeply_nested_dialog' ) as dlg:
                
                panel = EditHTMLTagRulePanel( dlg, rule )
                
                dlg.SetPanel( panel )
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    rule = panel.GetValue()
                    
                    pretty_rule = rule.ToString()
                    
                    self._tag_rules.SetString( selection, pretty_rule )
                    self._tag_rules.SetClientData( selection, rule )
                    
                
            
        
    
    def EventContentChoice( self, event ):
        
        self._UpdateControls()
        
    
    def EventEdit( self, event ):
        
        self.Edit()
        
    
    def GetValue( self ):
        
        tags_rules = [ self._tag_rules.GetClientData( i ) for i in range( self._tag_rules.GetCount() ) ]
        
        content_to_fetch = self._content_to_fetch.GetChoice()
        
        attribute_to_fetch = self._attribute_to_fetch.GetValue()
        
        if content_to_fetch == ClientParsing.HTML_CONTENT_ATTRIBUTE and attribute_to_fetch == '':
            
            raise HydrusExceptions.VetoException( 'Please enter an attribute to fetch!' )
            
        
        string_match = self._string_match_button.GetValue()
        
        string_converter = self._string_converter_button.GetValue()
        
        formula = ClientParsing.ParseFormulaHTML( tags_rules, content_to_fetch, attribute_to_fetch, string_match, string_converter )
        
        return formula
        
    
    def MoveDown( self ):
        
        selection = self._tag_rules.GetSelection()
        
        if selection != wx.NOT_FOUND and selection + 1 < self._tag_rules.GetCount():
            
            pretty_rule = self._tag_rules.GetString( selection )
            rule = self._tag_rules.GetClientData( selection )
            
            self._tag_rules.Delete( selection )
            
            self._tag_rules.Insert( pretty_rule, selection + 1, rule )
            
        
    
    def MoveUp( self ):
        
        selection = self._tag_rules.GetSelection()
        
        if selection != wx.NOT_FOUND and selection > 0:
            
            pretty_rule = self._tag_rules.GetString( selection )
            rule = self._tag_rules.GetClientData( selection )
            
            self._tag_rules.Delete( selection )
            
            self._tag_rules.Insert( pretty_rule, selection - 1, rule )
            
        
    
class EditJSONParsingRulePanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, rule ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._parse_rule_type = ClientGUICommon.BetterChoice( self )
        
        self._parse_rule_type.Append( 'dictionary entry', ClientParsing.JSON_PARSE_RULE_TYPE_DICT_KEY )
        self._parse_rule_type.Append( 'all dictionary/list items', ClientParsing.JSON_PARSE_RULE_TYPE_ALL_ITEMS )
        self._parse_rule_type.Append( 'indexed list item', ClientParsing.JSON_PARSE_RULE_TYPE_INDEXED_ITEM )
        
        self._string_match = ClientGUIControls.EditStringMatchPanel( self, string_match = ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'posts', example_string = 'posts' ) )
        
        self._index = wx.SpinCtrl( self, min = 0, max = 65535 )
        
        #
        
        ( parse_rule_type, parse_rule ) = rule
        
        self._parse_rule_type.SelectClientData( parse_rule_type )
        
        if parse_rule_type == ClientParsing.JSON_PARSE_RULE_TYPE_INDEXED_ITEM:
            
            self._index.SetValue( parse_rule )
            
        elif parse_rule_type == ClientParsing.JSON_PARSE_RULE_TYPE_DICT_KEY:
            
            self._string_match.SetValue( parse_rule )
            
        
        self._UpdateHideShow()
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        rows = []
        
        rows.append( ( 'list index: ', self._index ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        vbox.Add( self._parse_rule_type, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._string_match, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self.SetSizer( vbox )
        
        #
        
        self._parse_rule_type.Bind( wx.EVT_CHOICE, self.EventChoice )
        
    
    def _UpdateHideShow( self ):
        
        self._string_match.Disable()
        self._index.Disable()
        
        parse_rule_type = self._parse_rule_type.GetChoice()
        
        if parse_rule_type == ClientParsing.JSON_PARSE_RULE_TYPE_DICT_KEY:
            
            self._string_match.Enable()
            
        elif parse_rule_type == ClientParsing.JSON_PARSE_RULE_TYPE_INDEXED_ITEM:
            
            self._index.Enable()
            
        
    
    def EventChoice( self, event ):
        
        self._UpdateHideShow()
        
    
    def GetValue( self ):
        
        parse_rule_type = self._parse_rule_type.GetChoice()
        
        if parse_rule_type == ClientParsing.JSON_PARSE_RULE_TYPE_DICT_KEY:
            
            parse_rule = self._string_match.GetValue()
            
        elif parse_rule_type == ClientParsing.JSON_PARSE_RULE_TYPE_INDEXED_ITEM:
            
            parse_rule = self._index.GetValue()
            
        elif parse_rule_type == ClientParsing.JSON_PARSE_RULE_TYPE_ALL_ITEMS:
            
            parse_rule = None
            
        
        return ( parse_rule_type, parse_rule )
        
    
class EditJSONFormulaPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, formula, test_context ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        #
        
        menu_items = []
        
        page_func = HydrusData.Call( ClientPaths.LaunchPathInWebBrowser, os.path.join( HC.HELP_DIR, 'downloader_parsers_formulae.html#json_formula' ) )
        
        menu_items.append( ( 'normal', 'open the json formula help', 'Open the help page for json formulae in your web browser.', page_func ) )
        
        help_button = ClientGUICommon.MenuBitmapButton( self, CC.GlobalBMPs.help, menu_items )
        
        help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help for this panel -->', wx.Colour( 0, 0, 255 ) )
        
        #
        
        edit_panel = ClientGUICommon.StaticBox( self, 'edit' )
        
        edit_panel.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
        
        self._parse_rules = wx.ListBox( edit_panel, style = wx.LB_SINGLE )
        self._parse_rules.Bind( wx.EVT_LEFT_DCLICK, self.EventEdit )
        
        self._add_rule = ClientGUICommon.BetterButton( edit_panel, 'add', self.Add )
        
        self._edit_rule = ClientGUICommon.BetterButton( edit_panel, 'edit', self.Edit )
        
        self._move_rule_up = ClientGUICommon.BetterButton( edit_panel, '\u2191', self.MoveUp )
        
        self._delete_rule = ClientGUICommon.BetterButton( edit_panel, 'X', self.Delete )
        
        self._move_rule_down = ClientGUICommon.BetterButton( edit_panel, '\u2193', self.MoveDown )
        
        self._content_to_fetch = ClientGUICommon.BetterChoice( edit_panel )
        
        self._content_to_fetch.Append( 'string', ClientParsing.JSON_CONTENT_STRING )
        self._content_to_fetch.Append( 'dictionary keys', ClientParsing.JSON_CONTENT_DICT_KEYS )
        self._content_to_fetch.Append( 'json', ClientParsing.JSON_CONTENT_JSON )
        
        ( parse_rules, content_to_fetch, string_match, string_converter ) = formula.ToTuple()
        
        self._string_match_button = ClientGUIControls.StringMatchButton( edit_panel, string_match )
        
        self._string_converter_button = ClientGUIControls.StringConverterButton( edit_panel, string_converter )
        
        #
        
        test_panel = ClientGUICommon.StaticBox( self, 'test' )
        
        test_panel.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
        
        self._test_panel = TestPanel( test_panel, self.GetValue, test_context = test_context )
        
        #
        
        for rule in parse_rules:
            
            pretty_rule = ClientParsing.RenderJSONParseRule( rule )
            
            self._parse_rules.Append( pretty_rule, rule )
            
        
        self._content_to_fetch.SelectClientData( content_to_fetch )
        
        #
        
        udd_button_vbox = wx.BoxSizer( wx.VERTICAL )
        
        udd_button_vbox.Add( ( 20, 20 ), CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        udd_button_vbox.Add( self._move_rule_up, CC.FLAGS_VCENTER )
        udd_button_vbox.Add( self._delete_rule, CC.FLAGS_VCENTER )
        udd_button_vbox.Add( self._move_rule_down, CC.FLAGS_VCENTER )
        udd_button_vbox.Add( ( 20, 20 ), CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        parse_rules_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        parse_rules_hbox.Add( self._parse_rules, CC.FLAGS_EXPAND_BOTH_WAYS )
        parse_rules_hbox.Add( udd_button_vbox, CC.FLAGS_VCENTER )
        
        ae_button_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        ae_button_hbox.Add( self._add_rule, CC.FLAGS_VCENTER )
        ae_button_hbox.Add( self._edit_rule, CC.FLAGS_VCENTER )
        
        rows = []
        
        rows.append( ( 'content to fetch:', self._content_to_fetch ) )
        
        gridbox = ClientGUICommon.WrapInGrid( edit_panel, rows )
        
        edit_panel.Add( parse_rules_hbox, CC.FLAGS_EXPAND_BOTH_WAYS )
        edit_panel.Add( ae_button_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        edit_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        edit_panel.Add( ClientGUICommon.BetterStaticText( edit_panel, 'Newlines are removed from parsed strings right after parsing, before this String Match is tested.', style = wx.ST_ELLIPSIZE_END ), CC.FLAGS_EXPAND_PERPENDICULAR )
        edit_panel.Add( self._string_match_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        edit_panel.Add( self._string_converter_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        test_panel.Add( self._test_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( edit_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        hbox.Add( test_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( help_hbox, CC.FLAGS_BUTTON_SIZER )
        vbox.Add( hbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
    
    def Add( self ):
        
        dlg_title = 'edit parse rule'
        
        with ClientGUITopLevelWindows.DialogEdit( self, dlg_title, frame_key = 'deeply_nested_dialog' ) as dlg:
            
            new_rule = ( ClientParsing.JSON_PARSE_RULE_TYPE_DICT_KEY, ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'posts', example_string = 'posts' ) )
            
            panel = EditJSONParsingRulePanel( dlg, new_rule )
            
            dlg.SetPanel( panel )
            
            if dlg.ShowModal() == wx.ID_OK:
                
                rule = panel.GetValue()
                
                pretty_rule = ClientParsing.RenderJSONParseRule( rule )
                
                self._parse_rules.Append( pretty_rule, rule )
                
            
        
    
    def Delete( self ):
        
        selection = self._parse_rules.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            self._parse_rules.Delete( selection )
            
        
    
    def Edit( self ):
        
        selection = self._parse_rules.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            rule = self._parse_rules.GetClientData( selection )
            
            dlg_title = 'edit parse rule'
            
            with ClientGUITopLevelWindows.DialogEdit( self, dlg_title, frame_key = 'deeply_nested_dialog' ) as dlg:
                
                panel = EditJSONParsingRulePanel( dlg, rule )
                
                dlg.SetPanel( panel )
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    rule = panel.GetValue()
                    
                    pretty_rule = ClientParsing.RenderJSONParseRule( rule )
                    
                    self._parse_rules.SetString( selection, pretty_rule )
                    self._parse_rules.SetClientData( selection, rule )
                    
                
            
        
    
    def EventEdit( self, event ):
        
        self.Edit()
        
    
    def GetValue( self ):
        
        parse_rules = [ self._parse_rules.GetClientData( i ) for i in range( self._parse_rules.GetCount() ) ]
        
        content_to_fetch = self._content_to_fetch.GetChoice()
        
        string_match = self._string_match_button.GetValue()
        
        string_converter = self._string_converter_button.GetValue()
        
        formula = ClientParsing.ParseFormulaJSON( parse_rules, content_to_fetch, string_match, string_converter )
        
        return formula
        
    
    def MoveDown( self ):
        
        selection = self._parse_rules.GetSelection()
        
        if selection != wx.NOT_FOUND and selection + 1 < self._parse_rules.GetCount():
            
            pretty_rule = self._parse_rules.GetString( selection )
            rule = self._parse_rules.GetClientData( selection )
            
            self._parse_rules.Delete( selection )
            
            self._parse_rules.Insert( pretty_rule, selection + 1, rule )
            
        
    
    def MoveUp( self ):
        
        selection = self._parse_rules.GetSelection()
        
        if selection != wx.NOT_FOUND and selection > 0:
            
            pretty_rule = self._parse_rules.GetString( selection )
            rule = self._parse_rules.GetClientData( selection )
            
            self._parse_rules.Delete( selection )
            
            self._parse_rules.Insert( pretty_rule, selection - 1, rule )
            
        
    
class EditContentParserPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, content_parser, test_context, permitted_content_types ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        #
        
        menu_items = []
        
        page_func = HydrusData.Call( ClientPaths.LaunchPathInWebBrowser, os.path.join( HC.HELP_DIR, 'downloader_parsers_content_parsers.html#content_parsers' ) )
        
        menu_items.append( ( 'normal', 'open the content parsers help', 'Open the help page for content parsers in your web browser.', page_func ) )
        
        help_button = ClientGUICommon.MenuBitmapButton( self, CC.GlobalBMPs.help, menu_items )
        
        help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help for this panel -->', wx.Colour( 0, 0, 255 ) )
        
        #
        
        self._edit_panel = ClientGUICommon.StaticBox( self, 'edit' )
        
        self._edit_panel.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
        
        self._name = wx.TextCtrl( self._edit_panel )
        
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
            
            self._content_type.Append( types_to_str[ permitted_content_type ], permitted_content_type )
            
        
        self._content_type.Bind( wx.EVT_CHOICE, self.EventContentTypeChange )
        
        self._urls_panel = wx.Panel( self._content_panel )
        
        self._url_type = ClientGUICommon.BetterChoice( self._urls_panel )
        
        self._url_type.Append( 'url to download/pursue (file/post url)', HC.URL_TYPE_DESIRED )
        self._url_type.Append( 'url to associate (source url)', HC.URL_TYPE_SOURCE )
        self._url_type.Append( 'next gallery page', HC.URL_TYPE_NEXT )
        
        self._file_priority = wx.SpinCtrl( self._urls_panel, min = 0, max = 100 )
        self._file_priority.SetValue( 50 )
        
        self._mappings_panel = wx.Panel( self._content_panel )
        
        self._namespace = wx.TextCtrl( self._mappings_panel )
        
        self._hash_panel = wx.Panel( self._content_panel )
        
        self._hash_type = ClientGUICommon.BetterChoice( self._hash_panel )
        
        for hash_type in ( 'md5', 'sha1', 'sha256', 'sha512' ):
            
            self._hash_type.Append( hash_type, hash_type )
            
        
        self._timestamp_panel = wx.Panel( self._content_panel )
        
        self._timestamp_type = ClientGUICommon.BetterChoice( self._timestamp_panel )
        
        self._timestamp_type.Append( 'source time', HC.TIMESTAMP_TYPE_SOURCE )
        
        self._title_panel = wx.Panel( self._content_panel )
        
        self._title_priority = wx.SpinCtrl( self._title_panel, min = 0, max = 100 )
        self._title_priority.SetValue( 50 )
        
        self._veto_panel = wx.Panel( self._content_panel )
        
        self._veto_if_matches_found = wx.CheckBox( self._veto_panel )
        self._string_match = ClientGUIControls.EditStringMatchPanel( self._veto_panel )
        
        self._temp_variable_panel = wx.Panel( self._content_panel )
        
        self._temp_variable_name = wx.TextCtrl( self._temp_variable_panel )
        
        self._sort_type = ClientGUICommon.BetterChoice( self._content_panel )
        
        self._sort_type.Append( 'do not sort formula text results', ClientParsing.CONTENT_PARSER_SORT_TYPE_NONE )
        self._sort_type.Append( 'sort by human-friendly lexicographic', ClientParsing.CONTENT_PARSER_SORT_TYPE_HUMAN_SORT )
        self._sort_type.Append( 'sort by strict lexicographic', ClientParsing.CONTENT_PARSER_SORT_TYPE_LEXICOGRAPHIC )
        
        self._sort_type.Bind( wx.EVT_CHOICE, self.EventSortTypeChange )
        
        self._sort_asc = ClientGUICommon.BetterChoice( self._content_panel )
        
        self._sort_asc.Append( 'sort ascending', True )
        self._sort_asc.Append( 'sort descending', False )
        
        ( name, content_type, formula, sort_type, sort_asc, additional_info ) = content_parser.ToTuple()
        
        self._formula = EditFormulaPanel( self._edit_panel, formula, self.GetTestContext )
        
        #
        
        test_panel = ClientGUICommon.StaticBox( self, 'test' )
        
        test_panel.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
        
        self._test_panel = TestPanel( test_panel, self.GetValue, test_context = test_context )
        
        #
        
        self._name.SetValue( name )
        
        self._content_type.SelectClientData( content_type )
        
        if content_type == HC.CONTENT_TYPE_URLS:
            
            ( url_type, priority ) = additional_info
            
            self._url_type.SelectClientData( url_type )
            self._file_priority.SetValue( priority )
            
        elif content_type == HC.CONTENT_TYPE_MAPPINGS:
            
            namespace = additional_info
            
            self._namespace.SetValue( namespace )
            
        elif content_type == HC.CONTENT_TYPE_HASH:
            
            hash_type = additional_info
            
            self._hash_type.SelectClientData( hash_type )
            
        elif content_type == HC.CONTENT_TYPE_TIMESTAMP:
            
            timestamp_type = additional_info
            
            self._timestamp_type.SelectClientData( timestamp_type )
            
        elif content_type == HC.CONTENT_TYPE_TITLE:
            
            priority = additional_info
            
            self._title_priority.SetValue( priority )
            
        elif content_type == HC.CONTENT_TYPE_VETO:
            
            ( veto_if_matches_found, string_match ) = additional_info
            
            self._veto_if_matches_found.SetValue( veto_if_matches_found )
            self._string_match.SetValue( string_match )
            
        elif content_type == HC.CONTENT_TYPE_VARIABLE:
            
            temp_variable_name = additional_info
            
            self._temp_variable_name.SetValue( temp_variable_name )
            
        
        self._sort_type.SelectClientData( sort_type )
        self._sort_asc.SelectClientData( sort_asc )
        
        #
        
        rows = []
        
        rows.append( ( 'url type: ', self._url_type ) )
        rows.append( ( 'file url quality precedence (higher is better): ', self._file_priority ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._urls_panel, rows )
        
        self._urls_panel.SetSizer( gridbox )
        
        #
        
        rows = []
        
        rows.append( ( 'namespace: ', self._namespace ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._mappings_panel, rows )
        
        self._mappings_panel.SetSizer( gridbox )
        
        #
        
        rows = []
        
        rows.append( ( 'hash type: ', self._hash_type ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._hash_panel, rows )
        
        self._hash_panel.SetSizer( gridbox )
        
        #
        
        rows = []
        
        rows.append( ( 'timestamp type: ', self._timestamp_type ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._timestamp_panel, rows )
        
        self._timestamp_panel.SetSizer( gridbox )
        
        #
        
        rows = []
        
        rows.append( ( 'title precedence (higher is better): ', self._title_priority ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._title_panel, rows )
        
        self._title_panel.SetSizer( gridbox )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        rows = []
        
        rows.append( ( 'veto if match found (OFF means \'veto if match not found\'): ', self._veto_if_matches_found ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._veto_panel, rows )
        
        vbox.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.Add( self._string_match, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self._veto_panel.SetSizer( vbox )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        rows = []
        
        rows.append( ( 'variable name: ', self._temp_variable_name ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._temp_variable_panel, rows )
        
        vbox.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self._temp_variable_panel.SetSizer( vbox )
        
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
        self._content_panel.Add( self._sort_type, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._content_panel.Add( self._sort_asc, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        rows = []
        
        rows.append( ( 'name or description (optional): ', self._name ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._edit_panel, rows )
        
        self._edit_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._edit_panel.Add( self._content_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._edit_panel.Add( self._formula, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        test_panel.Add( self._test_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( self._edit_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        hbox.Add( test_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( help_hbox, CC.FLAGS_BUTTON_SIZER )
        vbox.Add( hbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
        self.EventContentTypeChange( None )
        self.EventSortTypeChange( None )
        
    
    def EventContentTypeChange( self, event ):
        
        choice = self._content_type.GetChoice()
        
        self._urls_panel.Hide()
        self._mappings_panel.Hide()
        self._hash_panel.Hide()
        self._timestamp_panel.Hide()
        self._title_panel.Hide()
        self._veto_panel.Hide()
        self._temp_variable_panel.Hide()
        
        if choice == HC.CONTENT_TYPE_URLS:
            
            self._urls_panel.Show()
            
        elif choice == HC.CONTENT_TYPE_MAPPINGS:
            
            self._mappings_panel.Show()
            
        elif choice == HC.CONTENT_TYPE_HASH:
            
            self._hash_panel.Show()
            
        elif choice == HC.CONTENT_TYPE_TIMESTAMP:
            
            self._timestamp_panel.Show()
            
        elif choice == HC.CONTENT_TYPE_TITLE:
            
            self._title_panel.Show()
            
        elif choice == HC.CONTENT_TYPE_VETO:
            
            self._veto_panel.Show()
            
        elif choice == HC.CONTENT_TYPE_VARIABLE:
            
            self._temp_variable_panel.Show()
            
        
        self._content_panel.Layout()
        self._edit_panel.Layout()
        
    
    def EventSortTypeChange( self, event ):
        
        choice = self._sort_type.GetChoice()
        
        if choice == ClientParsing.CONTENT_PARSER_SORT_TYPE_NONE:
            
            self._sort_asc.Disable()            
            
        else:
            
            self._sort_asc.Enable()
            
        
    
    def GetTestContext( self ):
        
        return self._test_panel.GetTestContext()
        
    
    def GetValue( self ):
        
        name = self._name.GetValue()
        
        content_type = self._content_type.GetChoice()
        
        formula = self._formula.GetValue()
        
        sort_type = self._sort_type.GetChoice()
        sort_asc = self._sort_asc.GetChoice()
        
        if content_type == HC.CONTENT_TYPE_URLS:
            
            url_type = self._url_type.GetChoice()
            priority = self._file_priority.GetValue()
            
            additional_info = ( url_type, priority )
            
        elif content_type == HC.CONTENT_TYPE_MAPPINGS:
            
            namespace = self._namespace.GetValue()
            
            additional_info = namespace
            
        elif content_type == HC.CONTENT_TYPE_HASH:
            
            hash_type = self._hash_type.GetChoice()
            
            additional_info = hash_type
            
        elif content_type == HC.CONTENT_TYPE_TIMESTAMP:
            
            timestamp_type = self._timestamp_type.GetChoice()
            
            additional_info = timestamp_type
            
        elif content_type == HC.CONTENT_TYPE_TITLE:
            
            priority = self._title_priority.GetValue()
            
            additional_info = priority
            
        elif content_type == HC.CONTENT_TYPE_VETO:
            
            veto_if_matches_found = self._veto_if_matches_found.GetValue()
            string_match = self._string_match.GetValue()
            
            additional_info = ( veto_if_matches_found, string_match )
            
        elif content_type == HC.CONTENT_TYPE_VARIABLE:
            
            temp_variable_name = self._temp_variable_name.GetValue()
            
            additional_info = temp_variable_name
            
        
        content_parser = ClientParsing.ContentParser( name = name, content_type = content_type, formula = formula, sort_type = sort_type, sort_asc = sort_asc, additional_info = additional_info )
        
        return content_parser
        
    
class EditContentParsersPanel( ClientGUICommon.StaticBox ):
    
    def __init__( self, parent, test_context_callable, permitted_content_types ):
        
        ClientGUICommon.StaticBox.__init__( self, parent, 'content parsers' )
        
        self._test_context_callable = test_context_callable
        self._permitted_content_types = permitted_content_types
        
        content_parsers_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        columns = [ ( 'name', -1 ), ( 'produces', 40 ) ]
        
        self._content_parsers = ClientGUIListCtrl.BetterListCtrl( content_parsers_panel, 'content_parsers', 6, 24, columns, self._ConvertContentParserToListCtrlTuples, use_simple_delete = True, activation_callback = self._Edit )
        
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
        
        test_context = self._test_context_callable()
        
        ( example_parsing_context, example_data ) = test_context
        
        if len( example_data ) > 0 and HydrusText.LooksLikeJSON( example_data ):
            
            formula = ClientParsing.ParseFormulaJSON()
            
        else:
            
            formula = ClientParsing.ParseFormulaHTML()
            
        
        content_parser = ClientParsing.ContentParser( 'new content parser', formula = formula )
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit content parser', frame_key = 'deeply_nested_dialog' ) as dlg_edit:
            
            panel = EditContentParserPanel( dlg_edit, content_parser, test_context, self._permitted_content_types )
            
            dlg_edit.SetPanel( panel )
            
            if dlg_edit.ShowModal() == wx.ID_OK:
                
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
            
            with ClientGUITopLevelWindows.DialogEdit( self, 'edit content parser', frame_key = 'deeply_nested_dialog' ) as dlg:
                
                test_context = self._test_context_callable()
                
                panel = EditContentParserPanel( dlg, content_parser, test_context, self._permitted_content_types )
                
                dlg.SetPanel( panel )
                
                if dlg.ShowModal() == wx.ID_OK:
                    
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
        
    
class EditNodes( wx.Panel ):
    
    def __init__( self, parent, nodes, referral_url_callable, example_data_callable ):
        
        wx.Panel.__init__( self, parent )
        
        self._referral_url_callable = referral_url_callable
        self._example_data_callable = example_data_callable
        
        self._nodes = ClientGUIListCtrl.SaneListCtrlForSingleObject( self, 200, [ ( 'name', 120 ), ( 'node type', 80 ), ( 'produces', -1 ) ], delete_key_callback = self.Delete, activation_callback = self.Edit )
        
        menu_items = []
        
        menu_items.append( ( 'normal', 'content node', 'A node that parses the given data for content.', self.AddContentNode ) )
        menu_items.append( ( 'normal', 'link node', 'A node that parses the given data for a link, which it then pursues.', self.AddLinkNode ) )
        
        self._add_button = ClientGUICommon.MenuButton( self, 'add', menu_items )
        
        self._copy_button = ClientGUICommon.BetterButton( self, 'copy', self.Copy )
        
        self._paste_button = ClientGUICommon.BetterButton( self, 'paste', self.Paste )
        
        self._duplicate_button = ClientGUICommon.BetterButton( self, 'duplicate', self.Duplicate )
        
        self._edit_button = ClientGUICommon.BetterButton( self, 'edit', self.Edit )
        
        self._delete_button = ClientGUICommon.BetterButton( self, 'delete', self.Delete )
        
        #
        
        for node in nodes:
            
            ( display_tuple, sort_tuple ) = self._ConvertNodeToTuples( node )
            
            self._nodes.Append( display_tuple, sort_tuple, node )
            
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        button_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        button_hbox.Add( self._add_button, CC.FLAGS_VCENTER )
        button_hbox.Add( self._copy_button, CC.FLAGS_VCENTER )
        button_hbox.Add( self._paste_button, CC.FLAGS_VCENTER )
        button_hbox.Add( self._duplicate_button, CC.FLAGS_VCENTER )
        button_hbox.Add( self._edit_button, CC.FLAGS_VCENTER )
        button_hbox.Add( self._delete_button, CC.FLAGS_VCENTER )
        
        vbox.Add( self._nodes, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.Add( button_hbox, CC.FLAGS_BUTTON_SIZER )
        
        self.SetSizer( vbox )
        
    
    def _ConvertNodeToTuples( self, node ):
        
        ( name, node_type, produces ) = node.ToPrettyStrings()
        
        return ( ( name, node_type, produces ), ( name, node_type, produces ) )
        
    
    def _GetExportObject( self ):
        
        to_export = HydrusSerialisable.SerialisableList()
        
        for node in self._nodes.GetObjects( only_selected = True ):
            
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
                
                ( display_tuple, sort_tuple ) = self._ConvertNodeToTuples( node )
                
                self._nodes.Append( display_tuple, sort_tuple, node )
                
            else:
                
                wx.MessageBox( 'That was not a script--it was a: ' + type( obj ).__name__ )
                
            
        
    
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
        
        with ClientGUITopLevelWindows.DialogEdit( self, dlg_title, frame_key = 'deeply_nested_dialog' ) as dlg_edit:
            
            referral_url = self._referral_url_callable()
            example_data = self._example_data_callable()
            
            if isinstance( empty_node, ClientParsing.ContentParser ):
                
                panel = panel_class( dlg_edit, empty_node, ( {}, example_data ), [ HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_TYPE_VETO ] )
                
            else:
                
                panel = panel_class( dlg_edit, empty_node, referral_url, example_data )
                
            
            dlg_edit.SetPanel( panel )
            
            if dlg_edit.ShowModal() == wx.ID_OK:
                
                new_node = panel.GetValue()
                
                ( display_tuple, sort_tuple ) = self._ConvertNodeToTuples( new_node )
                
                self._nodes.Append( display_tuple, sort_tuple, new_node )
                
            
        
    
    def Copy( self ):
        
        export_object = self._GetExportObject()
        
        if export_object is not None:
            
            json = export_object.DumpToString()
            
            HG.client_controller.pub( 'clipboard', 'text', json )
            
        
    
    def Delete( self ):
        
        with ClientGUIDialogs.DialogYesNo( self, 'Remove all selected?' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                self._nodes.RemoveAllSelected()
                
            
        
    
    def Duplicate( self ):
        
        nodes_to_dupe = self._nodes.GetObjects( only_selected = True )
        
        for node in nodes_to_dupe:
            
            dupe_node = node.Duplicate()
            
            ( display_tuple, sort_tuple ) = self._ConvertNodeToTuples( dupe_node )
            
            self._nodes.Append( display_tuple, sort_tuple, dupe_node )
            
        
    
    def Edit( self ):
        
        for i in self._nodes.GetAllSelected():
            
            node = self._nodes.GetObject( i )
            
            with ClientGUITopLevelWindows.DialogEdit( self, 'edit node', frame_key = 'deeply_nested_dialog' ) as dlg:
                
                referral_url = self._referral_url_callable()
                example_data = self._example_data_callable()
                
                if isinstance( node, ClientParsing.ContentParser ):
                    
                    panel = EditContentParserPanel( dlg, node, ( {}, example_data ), [ HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_TYPE_VETO ] )
                    
                elif isinstance( node, ClientParsing.ParseNodeContentLink ):
                    
                    panel = EditParseNodeContentLinkPanel( dlg, node, example_data = example_data )
                    
                
                dlg.SetPanel( panel )
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    edited_node = panel.GetValue()
                    
                    ( display_tuple, sort_tuple ) = self._ConvertNodeToTuples( edited_node )
                    
                    self._nodes.UpdateRow( i, display_tuple, sort_tuple, edited_node )
                    
                
                
            
        
    
    def GetValue( self ):
        
        return self._nodes.GetObjects()
        
    
    def Paste( self ):
        
        try:
            
            raw_text = HG.client_controller.GetClipboardText()
            
        except HydrusExceptions.DataMissing as e:
            
            wx.MessageBox( str( e ) )
            
            return
            
        
        try:
            
            obj = HydrusSerialisable.CreateFromString( raw_text )
            
            self._ImportObject( obj )
            
        except:
            
            wx.MessageBox( 'I could not understand what was in the clipboard' )
            
        
    
class EditParseNodeContentLinkPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, node, referral_url = None, example_data = None ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        if referral_url is None:
            
            referral_url = 'test-url.com/test_query'
            
        
        self._referral_url = referral_url
        
        if example_data is None:
            
            example_data = ''
            
        
        self._my_example_url = None
        
        notebook = wx.Notebook( self )
        
        ( name, formula, children ) = node.ToTuple()
        
        #
        
        edit_panel = wx.Panel( notebook )
        
        edit_panel.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
        
        self._name = wx.TextCtrl( edit_panel )
        
        get_example_parsing_context = lambda: {}
        
        self._formula = EditFormulaPanel( edit_panel, formula, self.GetTestContext )
        
        children_panel = ClientGUICommon.StaticBox( edit_panel, 'content parsing children' )
        
        self._children = EditNodes( children_panel, children, self.GetExampleURL, self.GetExampleData )
        
        #
        
        test_panel = wx.Panel( notebook )
        
        test_panel.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
        
        self._example_data = ClientGUICommon.SaneMultilineTextCtrl( test_panel )
        
        self._example_data.SetMinSize( ( -1, 200 ) )
        
        self._example_data.SetValue( example_data )
        
        self._test_parse = wx.Button( test_panel, label = 'test parse' )
        self._test_parse.Bind( wx.EVT_BUTTON, self.EventTestParse )
        
        self._results = ClientGUICommon.SaneMultilineTextCtrl( test_panel )
        
        self._results.SetMinSize( ( -1, 200 ) )
        
        self._test_fetch_result = wx.Button( test_panel, label = 'try fetching the first result' )
        self._test_fetch_result.Bind( wx.EVT_BUTTON, self.EventTestFetchResult )
        self._test_fetch_result.Disable()
        
        self._my_example_data = ClientGUICommon.SaneMultilineTextCtrl( test_panel )
        
        #
        
        info_panel = wx.Panel( notebook )
        
        message = '''This node looks for one or more urls in the data it is given, requests each in turn, and gives the results to its children for further parsing.

If your previous query result responds with links to where the actual content is, use this node to bridge the gap.

The formula should attempt to parse full or relative urls. If the url is relative (like href="/page/123"), it will be appended to the referral url given by this node's parent. It will then attempt to GET them all.'''
        
        info_st = ClientGUICommon.BetterStaticText( info_panel, label = message )
        
        info_st.SetWrapWidth( 400 )
        
        #
        
        self._name.SetValue( name )
        
        #
        
        children_panel.Add( self._children, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        rows = []
        
        rows.append( ( 'name or description (optional): ', self._name ) )
        
        gridbox = ClientGUICommon.WrapInGrid( edit_panel, rows )
        
        vbox.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.Add( self._formula, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.Add( children_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        edit_panel.SetSizer( vbox )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( self._example_data, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.Add( self._test_parse, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._results, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.Add( self._test_fetch_result, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._my_example_data, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        test_panel.SetSizer( vbox )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( info_st, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        info_panel.SetSizer( vbox )
        
        #
        
        notebook.AddPage( edit_panel, 'edit', select = True )
        notebook.AddPage( test_panel, 'test', select = False )
        notebook.AddPage( info_panel, 'info', select = False )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( notebook, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
        
    
    def EventTestFetchResult( self, event ):
        
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
        
    
    def EventTestParse( self, event ):
        
        def wx_code( parsed_urls ):
            
            if not self:
                
                return
                
            
            if len( parsed_urls ) > 0:
                
                self._my_example_url = parsed_urls[0]
                self._test_fetch_result.Enable()
                
            
            result_lines = [ '*** ' + HydrusData.ToHumanInt( len( parsed_urls ) ) + ' RESULTS BEGIN ***' ]
            
            result_lines.extend( parsed_urls )
            
            result_lines.append( '*** RESULTS END ***' )
            
            results_text = os.linesep.join( result_lines )
            
            self._results.SetValue( results_text )
            
        
        def do_it( node, data, referral_url ):
            
            try:
                
                stop_time = HydrusData.GetNow() + 30
                
                job_key = ClientThreading.JobKey( cancellable = True, stop_time = stop_time )
                
                parsed_urls = node.ParseURLs( job_key, data, referral_url )
                
                wx.CallAfter( wx_code, parsed_urls )
                
            except Exception as e:
                
                HydrusData.ShowException( e )
                
                message = 'Could not parse!'
                
                wx.CallAfter( wx.MessageBox, message )
                
            
        
        node = self.GetValue()
        data = self._example_data.GetValue()
        referral_url = self._referral_url
        
        HG.client_controller.CallToThread( do_it, node, data, referral_url )
        
    
    def GetExampleData( self ):
        
        return self._example_data.GetValue()
        
    
    def GetExampleURL( self ):
        
        if self._my_example_url is not None:
            
            return self._my_example_url
            
        else:
            
            return ''
            
        
    
    def GetTestContext( self ):
        
        return ( {}, self._example_data.GetValue() )
        
    
    def GetValue( self ):
        
        name = self._name.GetValue()
        
        formula = self._formula.GetValue()
        
        children = self._children.GetValue()
        
        node = ClientParsing.ParseNodeContentLink( name = name, formula = formula, children = children )
        
        return node
        
    
class EditPageParserPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, parser, formula = None, test_context = None ):
        
        self._original_parser = parser
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        if test_context is None:
            
            example_parsing_context = parser.GetExampleParsingContext()
            example_data = ''
            
            test_context = ( example_parsing_context, example_data )
            
        
        #
        
        menu_items = []
        
        page_func = HydrusData.Call( ClientPaths.LaunchPathInWebBrowser, os.path.join( HC.HELP_DIR, 'downloader_parsers_page_parsers.html#page_parsers' ) )
        
        menu_items.append( ( 'normal', 'open the page parser help', 'Open the help page for page parsers in your web browser.', page_func ) )
        
        help_button = ClientGUICommon.MenuBitmapButton( self, CC.GlobalBMPs.help, menu_items )
        
        help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help for this panel -->', wx.Colour( 0, 0, 255 ) )
        
        #
        
        edit_panel = ClientGUICommon.StaticBox( self, 'edit' )
        
        edit_notebook = wx.Notebook( edit_panel )
        
        #
        
        main_panel = wx.Panel( edit_notebook )
        
        main_panel.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
        
        self._name = wx.TextCtrl( main_panel )
        
        #
        
        conversion_panel = ClientGUICommon.StaticBox( main_panel, 'pre-parsing conversion' )
        
        string_converter = parser.GetStringConverter()
        
        self._string_converter = ClientGUIControls.StringConverterButton( conversion_panel, string_converter )
        
        #
        
        example_urls_panel = ClientGUICommon.StaticBox( main_panel, 'example urls' )
        
        self._example_urls = ClientGUIListBoxes.AddEditDeleteListBox( example_urls_panel, 6, str, self._AddExampleURL, self._EditExampleURL )
        
        #
        
        formula_panel = wx.Panel( edit_notebook )
        
        formula_test_callable = lambda: test_context
        
        self._formula = EditFormulaPanel( formula_panel, formula, formula_test_callable )
        
        #
        
        sub_page_parsers_notebook_panel = wx.Panel( edit_notebook )
        
        sub_page_parsers_notebook_panel.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
        
        #
        
        sub_page_parsers_panel = ClientGUIListCtrl.BetterListCtrlPanel( sub_page_parsers_notebook_panel )
        
        columns = [ ( 'name', 24 ), ( '\'post\' separation formula', 24 ), ( 'produces', -1 ) ]
        
        self._sub_page_parsers = ClientGUIListCtrl.BetterListCtrl( sub_page_parsers_panel, 'sub_page_parsers', 4, 36, columns, self._ConvertSubPageParserToListCtrlTuples, use_simple_delete = True, activation_callback = self._EditSubPageParser )
        
        sub_page_parsers_panel.SetListCtrl( self._sub_page_parsers )
        
        sub_page_parsers_panel.AddButton( 'add', self._AddSubPageParser )
        sub_page_parsers_panel.AddButton( 'edit', self._EditSubPageParser, enabled_only_on_selection = True )
        sub_page_parsers_panel.AddDeleteButton()
        
        #
        
        
        content_parsers_panel = wx.Panel( edit_notebook )
        
        content_parsers_panel.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
        
        #
        
        permitted_content_types = [ HC.CONTENT_TYPE_URLS, HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_TYPE_HASH, HC.CONTENT_TYPE_TIMESTAMP, HC.CONTENT_TYPE_TITLE, HC.CONTENT_TYPE_VETO ]
        
        self._content_parsers = EditContentParsersPanel( content_parsers_panel, self.GetTestContext, permitted_content_types )
        
        #
        
        test_panel = ClientGUICommon.StaticBox( self, 'test' )
        
        test_panel.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
        
        test_url_fetch_panel = ClientGUICommon.StaticBox( test_panel, 'fetch test data from url' )
        
        self._test_url = wx.TextCtrl( test_url_fetch_panel )
        self._test_referral_url = wx.TextCtrl( test_url_fetch_panel )
        self._fetch_example_data = ClientGUICommon.BetterButton( test_url_fetch_panel, 'fetch test data from url', self._FetchExampleData )
        self._test_network_job_control = ClientGUIControls.NetworkJobControl( test_url_fetch_panel )
        
        if formula is None:
            
            self._test_panel = TestPanelPageParser( test_panel, self.GetValue, self._string_converter.GetValue, test_context = test_context )
            
        else:
            
            self._test_panel = TestPanelPageParserSubsidiary( test_panel, self.GetValue, self._string_converter.GetValue, self.GetFormula, test_context = test_context )
            
        
        #
        
        name = parser.GetName()
        
        ( sub_page_parsers, content_parsers ) = parser.GetContentParsers()
        
        example_urls = parser.GetExampleURLs()
        
        if len( example_urls ) > 0:
            
            self._test_url.SetValue( example_urls[0] )
            
        
        self._name.SetValue( name )
        
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
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        rows = []
        
        rows.append( ( 'name or description (optional): ', self._name ) )
        
        gridbox = ClientGUICommon.WrapInGrid( main_panel, rows )
        
        vbox.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.Add( conversion_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( example_urls_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        main_panel.SetSizer( vbox )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( self._formula, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        formula_panel.SetSizer( vbox )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( sub_page_parsers_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        sub_page_parsers_notebook_panel.SetSizer( vbox )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( self._content_parsers, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        content_parsers_panel.SetSizer( vbox )
        
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
            
            test_url_fetch_panel.Hide()
            
        
        #
        
        if formula is None:
            
            formula_panel.Hide()
            
        else:
            
            example_urls_panel.Hide()
            edit_notebook.AddPage( formula_panel, 'separation formula', select = False )
            
        
        edit_notebook.AddPage( main_panel, 'main', select = True )
        edit_notebook.AddPage( sub_page_parsers_notebook_panel, 'subsidiary page parsers', select = False )
        edit_notebook.AddPage( content_parsers_panel, 'content parsers', select = False )
        
        edit_panel.Add( edit_notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( edit_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        hbox.Add( test_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( help_hbox, CC.FLAGS_BUTTON_SIZER )
        vbox.Add( hbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
    
    def _AddExampleURL( self ):
        
        url = ''
        
        return self._EditExampleURL( url )
        
    
    def _AddSubPageParser( self ):
        
        formula = ClientParsing.ParseFormulaHTML( tag_rules = [ ClientParsing.ParseRuleHTML( rule_type = ClientParsing.HTML_RULE_TYPE_DESCENDING, tag_name = 'div', tag_attributes = { 'class' : 'thumb' } ) ], content_to_fetch = ClientParsing.HTML_CONTENT_HTML )
        page_parser = ClientParsing.PageParser( 'new sub page parser' )
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit sub page parser', frame_key = 'deeply_nested_dialog' ) as dlg:
            
            panel = EditPageParserPanel( dlg, page_parser, formula = formula, test_context = self._test_panel.GetTestContext() )
            
            dlg.SetPanel( panel )
            
            if dlg.ShowModal() == wx.ID_OK:
                
                new_page_parser = panel.GetValue()
                
                new_formula = panel.GetFormula()
                
                new_sub_page_parser = ( new_formula, new_page_parser )
                
                self._sub_page_parsers.AddDatas( ( new_sub_page_parser, ) )
                
                self._sub_page_parsers.Sort()
                
            
        
    
    def _ConvertSubPageParserToListCtrlTuples( self, sub_page_parser ):
        
        ( formula, page_parser ) = sub_page_parser
        
        name = page_parser.GetName()
        
        produces = page_parser.GetParsableContent()
        
        produces = list( produces )
        
        produces.sort()
        
        pretty_name = name
        pretty_formula = formula.ToPrettyString()
        pretty_produces = ClientParsing.ConvertParsableContentToPrettyString( produces )
        
        display_tuple = ( pretty_name, pretty_formula, pretty_produces )
        sort_tuple = ( name, pretty_formula, produces )
        
        return ( display_tuple, sort_tuple )
        
    
    def _EditExampleURL( self, example_url ):
        
        message = 'Enter example URL.'
        
        with ClientGUIDialogs.DialogTextEntry( self, message, default = example_url ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                return dlg.GetValue()
                
            else:
                
                raise HydrusExceptions.VetoException()
                
            
        
    
    def _EditSubPageParser( self ):
        
        selected_data = self._sub_page_parsers.GetData( only_selected = True )
        
        for sub_page_parser in selected_data:
            
            ( formula, page_parser ) = sub_page_parser
            
            with ClientGUITopLevelWindows.DialogEdit( self, 'edit sub page parser', frame_key = 'deeply_nested_dialog' ) as dlg:
                
                panel = EditPageParserPanel( dlg, page_parser, formula = formula, test_context = self._test_panel.GetTestContext() )
                
                dlg.SetPanel( panel )
                
                if dlg.ShowModal() == wx.ID_OK:
                    
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
            
            def wx_tidy_up( example_data ):
                
                if not self:
                    
                    return
                    
                
                example_parsing_context = self._test_panel.GetExampleParsingContext()
                
                example_parsing_context[ 'url' ] = url
                
                self._test_panel.SetExampleParsingContext( example_parsing_context )
                
                self._test_panel.SetExampleData( example_data )
                
                self._test_network_job_control.ClearNetworkJob()
                
            
            try:
                
                network_job.WaitUntilDone()
                
                example_data = network_job.GetContentText()
                
            except HydrusExceptions.CancelledException:
                
                example_data = 'fetch cancelled'
                
            except Exception as e:
                
                example_data = 'fetch failed:' + os.linesep * 2 + str( e )
                
                HydrusData.ShowException( e )
                
            
            wx.CallAfter( wx_tidy_up, example_data )
            
        
        url = self._test_url.GetValue()
        referral_url = self._test_referral_url.GetValue()
        
        if referral_url == '':
            
            referral_url = None
            
        
        network_job = ClientNetworkingJobs.NetworkJob( 'GET', url, referral_url = referral_url )
        
        self._test_network_job_control.SetNetworkJob( network_job )
        
        network_job.OverrideBandwidth()
        
        HG.client_controller.network_engine.AddJob( network_job )
        
        HG.client_controller.CallToThread( wait_and_do_it, network_job )
        
    
    def GetTestContext( self ):
        
        return self._test_panel.GetTestContext()
        
    
    def GetFormula( self ):
        
        return self._formula.GetValue()
        
    
    def GetValue( self ):
        
        name = self._name.GetValue()
        
        parser_key = self._original_parser.GetParserKey()
        
        string_converter = self._string_converter.GetValue()
        
        sub_page_parsers = self._sub_page_parsers.GetData()
        
        content_parsers = self._content_parsers.GetData()
        
        example_urls = self._example_urls.GetData()
        
        example_parsing_context = self._test_panel.GetExampleParsingContext()
        
        parser = ClientParsing.PageParser( name, parser_key = parser_key, string_converter = string_converter, sub_page_parsers = sub_page_parsers, content_parsers = content_parsers, example_urls = example_urls, example_parsing_context = example_parsing_context )
        
        return parser
        
    
class EditParsersPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, parsers ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        parsers_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        columns = [ ( 'name', -1 ), ( 'example urls', 40 ), ( 'produces', 40 ) ]
        
        self._parsers = ClientGUIListCtrl.BetterListCtrl( parsers_panel, 'parsers', 20, 24, columns, self._ConvertParserToListCtrlTuples, use_simple_delete = True, activation_callback = self._Edit )
        
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
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( parsers_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
    
    def _Add( self ):
        
        new_parser = ClientParsing.PageParser( 'new page parser' )
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit parser', frame_key = 'deeply_nested_dialog' ) as dlg_edit:
            
            panel = EditPageParserPanel( dlg_edit, new_parser )
            
            dlg_edit.SetPanel( panel )
            
            if dlg_edit.ShowModal() == wx.ID_OK:
                
                new_parser = panel.GetValue()
                
                self._AddParser( new_parser )
                
                self._parsers.Sort()
                
            
        
    
    def _AddParser( self, parser ):
        
        HydrusSerialisable.SetNonDupeName( parser, self._GetExistingNames() )
        
        parser.RegenerateParserKey()
        
        self._parsers.AddDatas( ( parser, ) )
        
    
    def _ConvertParserToListCtrlTuples( self, parser ):
        
        name = parser.GetName()
        
        example_urls = list( parser.GetExampleURLs() )
        example_urls.sort()
        
        produces = list( parser.GetParsableContent() )
        
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
            
            with ClientGUITopLevelWindows.DialogEdit( self, 'edit parser', frame_key = 'deeply_nested_dialog' ) as dlg:
                
                panel = EditPageParserPanel( dlg, parser )
                
                dlg.SetPanel( panel )
                
                if dlg.ShowModal() == wx.ID_OK:
                    
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
        
        notebook = wx.Notebook( self )
        
        #
        
        edit_panel = wx.Panel( notebook )
        
        edit_panel.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
        
        self._name = wx.TextCtrl( edit_panel )
        
        query_panel = ClientGUICommon.StaticBox( edit_panel, 'query' )
        
        self._url = wx.TextCtrl( query_panel )
        
        self._url.SetValue( url )
        
        self._query_type = ClientGUICommon.BetterChoice( query_panel )
        
        self._query_type.Append( 'GET', HC.GET )
        self._query_type.Append( 'POST', HC.POST )
        
        self._file_identifier_type = ClientGUICommon.BetterChoice( query_panel )
        
        for t in [ ClientParsing.FILE_IDENTIFIER_TYPE_FILE, ClientParsing.FILE_IDENTIFIER_TYPE_MD5, ClientParsing.FILE_IDENTIFIER_TYPE_SHA1, ClientParsing.FILE_IDENTIFIER_TYPE_SHA256, ClientParsing.FILE_IDENTIFIER_TYPE_SHA512, ClientParsing.FILE_IDENTIFIER_TYPE_USER_INPUT ]:
            
            self._file_identifier_type.Append( ClientParsing.file_identifier_string_lookup[ t ], t )
            
        
        self._file_identifier_string_converter = ClientGUIControls.StringConverterButton( query_panel, file_identifier_string_converter )
        
        self._file_identifier_arg_name = wx.TextCtrl( query_panel )
        
        static_args_panel = ClientGUICommon.StaticBox( query_panel, 'static arguments' )
        
        self._static_args = ClientGUIControls.StringToStringDictControl( static_args_panel, static_args, min_height = 4 )
        
        children_panel = ClientGUICommon.StaticBox( edit_panel, 'content parsing children' )
        
        self._children = EditNodes( children_panel, children, self.GetExampleURL, self.GetExampleData )
        
        #
        
        test_panel = wx.Panel( notebook )
        
        test_panel.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
        
        self._test_script_management = ScriptManagementControl( test_panel )
        
        self._test_arg = wx.TextCtrl( test_panel )
        
        self._test_arg.SetValue( 'enter example file path, hex hash, or raw user input here' )
        
        self._fetch_data = wx.Button( test_panel, label = 'fetch response' )
        self._fetch_data.Bind( wx.EVT_BUTTON, self.EventFetchData )
        
        self._example_data = ClientGUICommon.SaneMultilineTextCtrl( test_panel )
        
        self._example_data.SetMinSize( ( -1, 200 ) )
        
        self._test_parsing = wx.Button( test_panel, label = 'test parse (note if you have \'link\' nodes, they will make their requests)' )
        self._test_parsing.Bind( wx.EVT_BUTTON, self.EventTestParse )
        
        self._results = ClientGUICommon.SaneMultilineTextCtrl( test_panel )
        
        self._results.SetMinSize( ( -1, 200 ) )
        
        #
        
        info_panel = wx.Panel( notebook )
        
        message = '''This script looks up tags for a single file.

It will download the result of a query that might look something like this:

http://www.file-lookup.com/form.php?q=getsometags&md5=[md5-in-hex]

And pass that html to a number of 'parsing children' that will each look through it in turn and try to find tags.'''
        
        info_st = ClientGUICommon.BetterStaticText( info_panel, label = message )
        
        info_st.SetWrapWidth( 400 )
        
        #
        
        self._name.SetValue( name )
        
        self._query_type.SelectClientData( query_type )
        self._file_identifier_type.SelectClientData( file_identifier_type )
        self._file_identifier_arg_name.SetValue( file_identifier_arg_name )
        
        self._results.SetValue( 'Successfully parsed results will be printed here.' )
        
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
        
        query_panel.Add( wx.StaticText( query_panel, label = query_message ), CC.FLAGS_EXPAND_PERPENDICULAR )
        query_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        query_panel.Add( static_args_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        children_message = 'The data returned by the query will be passed to each of these children for content parsing.'
        
        children_panel.Add( wx.StaticText( children_panel, label = children_message ), CC.FLAGS_EXPAND_PERPENDICULAR )
        children_panel.Add( self._children, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        rows = []
        
        rows.append( ( 'script name: ', self._name ) )
        
        gridbox = ClientGUICommon.WrapInGrid( edit_panel, rows )
        
        vbox.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.Add( query_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.Add( children_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        edit_panel.SetSizer( vbox )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( self._test_script_management, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._test_arg, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._fetch_data, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._example_data, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.Add( self._test_parsing, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._results, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        test_panel.SetSizer( vbox )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( info_st, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        info_panel.SetSizer( vbox )
        
        #
        
        notebook.AddPage( edit_panel, 'edit', select = True )
        notebook.AddPage( test_panel, 'test', select = False )
        notebook.AddPage( info_panel, 'info', select = False )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( notebook, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
    
    def EventFetchData( self, event ):
        
        script = self.GetValue()
        
        test_arg = self._test_arg.GetValue()
        
        file_identifier_type = self._file_identifier_type.GetChoice()
        
        if file_identifier_type == ClientParsing.FILE_IDENTIFIER_TYPE_FILE:
            
            if not os.path.exists( test_arg ):
                
                wx.MessageBox( 'That file does not exist!' )
                
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
                
                self._example_data.SetValue( parsing_text )
                
            except UnicodeDecodeError:
                
                self._example_data.SetValue( 'The fetched data, which had length ' + HydrusData.ToHumanBytes( len( parsing_text ) ) + ', did not appear to be displayable text.' )
                
            
        except Exception as e:
            
            HydrusData.ShowException( e )
            
            message = 'Could not fetch data!'
            message += os.linesep * 2
            message += str( e )
            
            wx.MessageBox( message )
            
        finally:
            
            job_key.Finish()
            
        
    
    def EventTestParse( self, event ):
        
        def wx_code( results ):
            
            if not self:
                
                return
                
            
            result_lines = [ '*** ' + HydrusData.ToHumanInt( len( results ) ) + ' RESULTS BEGIN ***' ]
            
            result_lines.extend( ( ClientParsing.ConvertParseResultToPrettyString( result ) for result in results ) )
            
            result_lines.append( '*** RESULTS END ***' )
            
            results_text = os.linesep.join( result_lines )
            
            self._results.SetValue( results_text )
            
        
        def do_it( script, job_key, data ):
            
            try:
                
                results = script.Parse( job_key, data )
                
                wx.CallAfter( wx_code, results )
                
            except Exception as e:
                
                HydrusData.ShowException( e )
                
                message = 'Could not parse!'
                
                wx.CallAfter( wx.MessageBox, message )
                
            finally:
                
                job_key.Finish()
                
            
        
        script = self.GetValue()
        
        stop_time = HydrusData.GetNow() + 30
        
        job_key = ClientThreading.JobKey( cancellable = True, stop_time = stop_time )
        
        self._test_script_management.SetJobKey( job_key )
        
        data = self._example_data.GetValue()
        
        HG.client_controller.CallToThread( do_it, script, job_key, data )
        
    
    def GetExampleData( self ):
        
        return self._example_data.GetValue()
        
    
    def GetExampleURL( self ):
        
        return self._url.GetValue()
        
    
    def GetValue( self ):
        
        name = self._name.GetValue()
        url = self._url.GetValue()
        query_type = self._query_type.GetChoice()
        file_identifier_type = self._file_identifier_type.GetChoice()
        file_identifier_string_converter = self._file_identifier_string_converter.GetValue()
        file_identifier_arg_name = self._file_identifier_arg_name.GetValue()
        static_args = self._static_args.GetValue()
        children = self._children.GetValue()
        
        script = ClientParsing.ParseRootFileLookup( name, url = url, query_type = query_type, file_identifier_type = file_identifier_type, file_identifier_string_converter = file_identifier_string_converter, file_identifier_arg_name = file_identifier_arg_name, static_args = static_args, children = children )
        
        return script
        
    
class ManageParsingScriptsPanel( ClientGUIScrolledPanels.ManagePanel ):
    
    SCRIPT_TYPES = []
    
    SCRIPT_TYPES.append( HydrusSerialisable.SERIALISABLE_TYPE_PARSE_ROOT_FILE_LOOKUP )
    
    def __init__( self, parent ):
        
        ClientGUIScrolledPanels.ManagePanel.__init__( self, parent )
        
        self._scripts = ClientGUIListCtrl.SaneListCtrlForSingleObject( self, 200, [ ( 'name', 140 ), ( 'query type', 80 ), ( 'script type', 80 ), ( 'produces', -1 ) ], delete_key_callback = self.Delete, activation_callback = self.Edit )
        
        menu_items = []
        
        menu_items.append( ( 'normal', 'file lookup script', 'A script that fetches content for a known file.', self.AddFileLookupScript ) )
        
        self._add_button = ClientGUICommon.MenuButton( self, 'add', menu_items )
        
        menu_items = []
        
        menu_items.append( ( 'normal', 'to clipboard', 'Serialise the script and put it on your clipboard.', self.ExportToClipboard ) )
        menu_items.append( ( 'normal', 'to png', 'Serialise the script and encode it to an image file you can easily share with other hydrus users.', self.ExportToPng ) )
        
        self._export_button = ClientGUICommon.MenuButton( self, 'export', menu_items )
        
        menu_items = []
        
        menu_items.append( ( 'normal', 'from clipboard', 'Load a script from text in your clipboard.', self.ImportFromClipboard ) )
        menu_items.append( ( 'normal', 'from png', 'Load a script from an encoded png.', self.ImportFromPng ) )
        
        self._import_button = ClientGUICommon.MenuButton( self, 'import', menu_items )
        
        self._duplicate_button = ClientGUICommon.BetterButton( self, 'duplicate', self.Duplicate )
        
        self._edit_button = ClientGUICommon.BetterButton( self, 'edit', self.Edit )
        
        self._delete_button = ClientGUICommon.BetterButton( self, 'delete', self.Delete )
        
        #
        
        scripts = []
        
        for script_type in self.SCRIPT_TYPES:
            
            scripts.extend( HG.client_controller.Read( 'serialisable_named', script_type ) )
            
        
        for script in scripts:
            
            ( display_tuple, sort_tuple ) = self._ConvertScriptToTuples( script )
            
            self._scripts.Append( display_tuple, sort_tuple, script )
            
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        button_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        button_hbox.Add( self._add_button, CC.FLAGS_VCENTER )
        button_hbox.Add( self._export_button, CC.FLAGS_VCENTER )
        button_hbox.Add( self._import_button, CC.FLAGS_VCENTER )
        button_hbox.Add( self._duplicate_button, CC.FLAGS_VCENTER )
        button_hbox.Add( self._edit_button, CC.FLAGS_VCENTER )
        button_hbox.Add( self._delete_button, CC.FLAGS_VCENTER )
        
        vbox.Add( self._scripts, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.Add( button_hbox, CC.FLAGS_BUTTON_SIZER )
        
        self.SetSizer( vbox )
        
    
    def _ConvertScriptToTuples( self, script ):
        
        ( name, query_type, script_type, produces ) = script.ToPrettyStrings()
        
        return ( ( name, query_type, script_type, produces ), ( name, query_type, script_type, produces ) )
        
    
    def _GetExportObject( self ):
        
        to_export = HydrusSerialisable.SerialisableList()
        
        for script in self._scripts.GetObjects( only_selected = True ):
            
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
                
                ( display_tuple, sort_tuple ) = self._ConvertScriptToTuples( script )
                
                self._scripts.Append( display_tuple, sort_tuple, script )
                
            else:
                
                wx.MessageBox( 'That was not a script--it was a: ' + type( obj ).__name__ )
                
            
        
    
    def AddFileLookupScript( self ):
        
        name = 'new script'
        url = ''
        query_type = HC.GET
        file_identifier_type = ClientParsing.FILE_IDENTIFIER_TYPE_MD5
        file_identifier_string_converter = ClientParsing.StringConverter( ( ( ClientParsing.STRING_TRANSFORMATION_ENCODE, 'hex' ), ), 'some hash bytes' )
        file_identifier_arg_name = 'md5'
        static_args = {}
        children = []
        
        dlg_title = 'edit file metadata lookup script'
        
        empty_script = ClientParsing.ParseRootFileLookup( name, url = url, query_type = query_type, file_identifier_type = file_identifier_type, file_identifier_string_converter = file_identifier_string_converter, file_identifier_arg_name = file_identifier_arg_name, static_args = static_args, children = children)
        
        panel_class = EditParsingScriptFileLookupPanel
        
        self.AddScript( dlg_title, empty_script, panel_class )
        
    
    def AddScript( self, dlg_title, empty_script, panel_class ):
        
        with ClientGUITopLevelWindows.DialogEdit( self, dlg_title, frame_key = 'deeply_nested_dialog' ) as dlg_edit:
            
            panel = panel_class( dlg_edit, empty_script )
            
            dlg_edit.SetPanel( panel )
            
            if dlg_edit.ShowModal() == wx.ID_OK:
                
                new_script = panel.GetValue()
                
                self._scripts.SetNonDupeName( new_script )
                
                ( display_tuple, sort_tuple ) = self._ConvertScriptToTuples( new_script )
                
                self._scripts.Append( display_tuple, sort_tuple, new_script )
                
            
        
    
    def CommitChanges( self ):
        
        scripts = self._scripts.GetObjects()
        
        HG.client_controller.Write( 'serialisables_overwrite', self.SCRIPT_TYPES, scripts )
        
    
    def Delete( self ):
        
        with ClientGUIDialogs.DialogYesNo( self, 'Remove all selected?' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                self._scripts.RemoveAllSelected()
                
            
        
    
    def Duplicate( self ):
        
        scripts_to_dupe = self._scripts.GetObjects( only_selected = True )
        
        for script in scripts_to_dupe:
            
            dupe_script = script.Duplicate()
            
            self._scripts.SetNonDupeName( dupe_script )
            
            ( display_tuple, sort_tuple ) = self._ConvertScriptToTuples( dupe_script )
            
            self._scripts.Append( display_tuple, sort_tuple, dupe_script )
            
        
    
    def Edit( self ):
        
        for i in self._scripts.GetAllSelected():
            
            script = self._scripts.GetObject( i )
            
            if isinstance( script, ClientParsing.ParseRootFileLookup ):
                
                panel_class = EditParsingScriptFileLookupPanel
                
                dlg_title = 'edit file lookup script'
                
            
            with ClientGUITopLevelWindows.DialogEdit( self, dlg_title, frame_key = 'deeply_nested_dialog' ) as dlg:
                
                original_name = script.GetName()
                
                panel = panel_class( dlg, script )
                
                dlg.SetPanel( panel )
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    edited_script = panel.GetValue()
                    
                    if edited_script.GetName() != original_name:
                        
                        self._scripts.SetNonDupeName( edited_script )
                        
                    
                    ( display_tuple, sort_tuple ) = self._ConvertScriptToTuples( edited_script )
                    
                    self._scripts.UpdateRow( i, display_tuple, sort_tuple, edited_script )
                    
                
                
            
        
    
    def ExportToClipboard( self ):
        
        export_object = self._GetExportObject()
        
        if export_object is not None:
            
            json = export_object.DumpToString()
            
            HG.client_controller.pub( 'clipboard', 'text', json )
            
        
    
    def ExportToPng( self ):
        
        export_object = self._GetExportObject()
        
        if export_object is not None:
            
            with ClientGUITopLevelWindows.DialogNullipotent( self, 'export to png' ) as dlg:
                
                panel = ClientGUISerialisable.PngExportPanel( dlg, export_object )
                
                dlg.SetPanel( panel )
                
                dlg.ShowModal()
                
            
        
    
    def ImportFromClipboard( self ):
        
        try:
            
            raw_text = HG.client_controller.GetClipboardText()
            
        except HydrusExceptions.DataMissing as e:
            
            wx.MessageBox( str( e ) )
            
            return
            
        
        try:
            
            obj = HydrusSerialisable.CreateFromString( raw_text )
            
            self._ImportObject( obj )
            
        except Exception as e:
            
            wx.MessageBox( 'I could not understand what was in the clipboard' )
            
        
    
    def ImportFromPng( self ):
        
        with wx.FileDialog( self, 'select the png with the encoded script', wildcard = 'PNG (*.png)|*.png' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                path = dlg.GetPath()
                
                try:
                    
                    payload = ClientSerialisable.LoadFromPng( path )
                    
                except Exception as e:
                    
                    wx.MessageBox( str( e ) )
                    
                    return
                    
                
                try:
                    
                    obj = HydrusSerialisable.CreateFromNetworkBytes( payload )
                    
                    self._ImportObject( obj )
                    
                except:
                    
                    wx.MessageBox( 'I could not understand what was encoded in the png!' )
                    
                
            
        
    
class ScriptManagementControl( wx.Panel ):
    
    def __init__( self, parent ):
        
        wx.Panel.__init__( self, parent )
        
        self._job_key = None
        
        self._lock = threading.Lock()
        
        self._recent_urls = []
        
        main_panel = ClientGUICommon.StaticBox( self, 'script control' )
        
        self._status = ClientGUICommon.BetterStaticText( main_panel )
        self._gauge = ClientGUICommon.Gauge( main_panel )
        
        self._link_button = ClientGUICommon.BetterBitmapButton( main_panel, CC.GlobalBMPs.link, self.LinkButton )
        self._link_button.SetToolTip( 'urls found by the script' )
        
        self._cancel_button = ClientGUICommon.BetterBitmapButton( main_panel, CC.GlobalBMPs.stop, self.CancelButton )
        
        #
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( self._gauge, CC.FLAGS_EXPAND_BOTH_WAYS )
        hbox.Add( self._link_button, CC.FLAGS_VCENTER )
        hbox.Add( self._cancel_button, CC.FLAGS_VCENTER )
        
        main_panel.Add( self._status, CC.FLAGS_EXPAND_PERPENDICULAR )
        main_panel.Add( hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( main_panel, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
        #
        
        self._Reset()
        
    
    def _Reset( self ):
        
        self._status.SetLabelText( '' )
        self._gauge.SetRange( 1 )
        self._gauge.SetValue( 0 )
        
        self._link_button.Disable()
        self._cancel_button.Disable()
        
    
    def _Update( self ):
        
        if self._job_key is None:
            
            self._Reset()
            
        else:
            
            if self._job_key.HasVariable( 'script_status' ):
                
                status = self._job_key.GetIfHasVariable( 'script_status' )
                
            else:
                
                status = ''
                
            
            self._status.SetLabelText( status )
            
            if self._job_key.HasVariable( 'script_gauge' ):
                
                ( value, range ) = self._job_key.GetIfHasVariable( 'script_gauge' )
                
            else:
                
                ( value, range ) = ( 0, 1 )
                
            
            self._gauge.SetRange( range )
            self._gauge.SetValue( value )
            
            urls = self._job_key.GetURLs()
            
            if len( urls ) == 0:
                
                if self._link_button.IsEnabled():
                    
                    self._link_button.Disable()
                    
                
            else:
                
                if not self._link_button.IsEnabled():
                    
                    self._link_button.Enable()
                    
                
            
            if self._job_key.IsDone():
                
                if self._cancel_button.IsEnabled():
                    
                    self._cancel_button.Disable()
                    
                
            else:
                
                if not self._cancel_button.IsEnabled():
                    
                    self._cancel_button.Enable()
                    
                
            
        
    
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
            
        
        menu = wx.Menu()
        
        for url in urls:
            
            ClientGUIMenus.AppendMenuItem( self, menu, url, 'launch this url in your browser', ClientPaths.LaunchURLInWebBrowser, url )
            
        
        HG.client_controller.PopupMenu( self, menu )
        
        
    
    def SetJobKey( self, job_key ):
        
        with self._lock:
            
            self._job_key = job_key
            
        
        HG.client_controller.gui.RegisterUIUpdateWindow( self )
        
    
class TestPanel( wx.Panel ):
    
    def __init__( self, parent, object_callable, test_context = None ):
        
        wx.Panel.__init__( self, parent )
        
        if test_context is None:
            
            test_context = ( {}, '' )
            
        
        self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
        
        self._object_callable = object_callable
        
        self._example_parsing_context = ClientGUIControls.StringToStringDictButton( self, 'edit example parsing context' )
        
        self._data_preview_notebook = wx.Notebook( self )
        
        raw_data_panel = wx.Panel( self._data_preview_notebook )
        
        self._example_data_raw_description = ClientGUICommon.BetterStaticText( raw_data_panel )
        
        self._copy_button = ClientGUICommon.BetterBitmapButton( raw_data_panel, CC.GlobalBMPs.copy, self._Copy )
        self._copy_button.SetToolTip( 'Copy the current example data to the clipboard.' )
        
        self._fetch_button = ClientGUICommon.BetterBitmapButton( raw_data_panel, CC.GlobalBMPs.link, self._FetchFromURL )
        self._fetch_button.SetToolTip( 'Fetch data from a URL.' )
        
        self._paste_button = ClientGUICommon.BetterBitmapButton( raw_data_panel, CC.GlobalBMPs.paste, self._Paste )
        self._paste_button.SetToolTip( 'Paste the current clipboard data into here.' )
        
        self._example_data_raw_preview = ClientGUICommon.SaneMultilineTextCtrl( raw_data_panel, style = wx.TE_READONLY )
        
        size = ClientGUIFunctions.ConvertTextToPixels( self._example_data_raw_preview, ( 60, 9 ) )
        
        self._example_data_raw_preview.SetInitialSize( size )
        
        self._test_parse = ClientGUICommon.BetterButton( self, 'test parse', self.TestParse )
        
        self._results = ClientGUICommon.SaneMultilineTextCtrl( self )
        
        size = ClientGUIFunctions.ConvertTextToPixels( self._example_data_raw_preview, ( 80, 12 ) )
        
        self._results.SetInitialSize( size )
        
        #
        
        ( example_parsing_context, example_data ) = test_context
        
        self._example_parsing_context.SetValue( example_parsing_context )
        
        self._example_data_raw = ''
        
        self._results.SetValue( 'Successfully parsed results will be printed here.' )
        
        #
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( self._example_data_raw_description, CC.FLAGS_EXPAND_BOTH_WAYS )
        hbox.Add( self._copy_button, CC.FLAGS_VCENTER )
        hbox.Add( self._fetch_button, CC.FLAGS_VCENTER )
        hbox.Add( self._paste_button, CC.FLAGS_VCENTER )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.Add( self._example_data_raw_preview, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        raw_data_panel.SetSizer( vbox )
        
        self._data_preview_notebook.AddPage( raw_data_panel, 'raw data', select = True )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( self._example_parsing_context, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._data_preview_notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.Add( self._test_parse, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._results, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
        wx.CallAfter( self._SetExampleData, example_data )
        
    
    def _Copy( self ):
        
        HG.client_controller.pub( 'clipboard', 'text', self._example_data_raw )
        
    
    def _FetchFromURL( self ):
        
        def wx_code( example_data ):
            
            if not self:
                
                return
                
            
            example_parsing_context = self._example_parsing_context.GetValue()
            
            example_parsing_context[ 'url' ] = url
            
            self._example_parsing_context.SetValue( example_parsing_context )
            
            self._SetExampleData( example_data )
            
        
        def do_it( url ):
            
            network_job = ClientNetworkingJobs.NetworkJob( 'GET', url )
            
            network_job.OverrideBandwidth()
            
            HG.client_controller.network_engine.AddJob( network_job )
            
            try:
                
                network_job.WaitUntilDone()
                
                example_data = network_job.GetContentText()
                
            except HydrusExceptions.CancelledException:
                
                example_data = 'fetch cancelled'
                
            except Exception as e:
                
                example_data = 'fetch failed:' + os.linesep * 2 + str( e )
                
                HydrusData.ShowException( e )
                
            
            wx.CallAfter( wx_code, example_data )
            
        
        message = 'Enter URL to fetch data for.'
        
        with ClientGUIDialogs.DialogTextEntry( self, message, default = 'enter url', allow_blank = False) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                url = dlg.GetValue()
                
                HG.client_controller.CallToThread( do_it, url )
                
            
        
    
    def _Paste( self ):
        
        try:
            
            raw_text = HG.client_controller.GetClipboardText()
            
        except HydrusExceptions.DataMissing as e:
            
            wx.MessageBox( str( e ) )
            
            return
            
        
        self._SetExampleData( raw_text )
        
    
    def _SetExampleData( self, example_data ):
        
        self._example_data_raw = example_data
        
        if len( example_data ) > 0:
            
            parse_phrase = 'uncertain data type'
            
            # can't just throw this at bs4 to see if it 'works', as it'll just wrap any unparsable string in some bare <html><body><p> tags
            if HydrusText.LooksLikeHTML( example_data ):
                
                parse_phrase = 'looks like HTML'
                
            
            # put this second, so if the JSON contains some HTML, it'll overwrite here. decent compromise
            if HydrusText.LooksLikeJSON( example_data ):
                
                parse_phrase = 'looks like JSON'
                
            
            description = HydrusData.ToHumanBytes( len( example_data ) ) + ' total, ' + parse_phrase
            
            if len( example_data ) > 1024:
                
                preview = 'PREVIEW:' + os.linesep + str( example_data[:1024] )
                
            else:
                
                preview = example_data
                
            
            self._test_parse.Enable()
            
        else:
            
            description = 'no example data set yet'
            preview = ''
            
            self._test_parse.Disable()
            
        
        self._example_data_raw_description.SetLabelText( description )
        self._example_data_raw_preview.SetValue( preview )
        
    
    def GetExampleParsingContext( self ):
        
        return self._example_parsing_context.GetValue()
        
    
    def GetTestContext( self ):
        
        example_parsing_context = self._example_parsing_context.GetValue()
        
        return ( example_parsing_context, self._example_data_raw )
        
    
    def SetExampleData( self, example_data ):
        
        self._SetExampleData( example_data )
        
    
    def SetExampleParsingContext( self, example_parsing_context ):
        
        self._example_parsing_context.SetValue( example_parsing_context )
        
    
    def TestParse( self ):
        
        obj = self._object_callable()
        
        ( example_parsing_context, example_data ) = self.GetTestContext()
        
        try:
            
            results_text = obj.ParsePretty( example_parsing_context, example_data )
            
            self._results.SetValue( results_text )
            
        except Exception as e:
            
            etype = type( e )
            
            ( etype, value, tb ) = sys.exc_info()
            
            trace = ''.join( traceback.format_exception( etype, value, tb ) )
            
            message = 'Exception:' + os.linesep + str( etype.__name__ ) + ': ' + str( e ) + os.linesep + trace
            
            self._results.SetValue( message )
            
        
    
class TestPanelPageParser( TestPanel ):
    
    def __init__( self, parent, object_callable, pre_parsing_conversion_callable, test_context = None ):
        
        self._pre_parsing_conversion_callable = pre_parsing_conversion_callable
        
        TestPanel.__init__( self, parent, object_callable, test_context = test_context )
        
        post_conversion_panel = wx.Panel( self._data_preview_notebook )
        
        self._example_data_post_conversion_description = ClientGUICommon.BetterStaticText( post_conversion_panel )
        
        self._copy_button_post_conversion = ClientGUICommon.BetterBitmapButton( post_conversion_panel, CC.GlobalBMPs.copy, self._CopyPostConversion )
        self._copy_button_post_conversion.SetToolTip( 'Copy the current post conversion data to the clipboard.' )
        
        self._refresh_post_conversion_button = ClientGUICommon.BetterBitmapButton( post_conversion_panel, CC.GlobalBMPs.refresh, self._RefreshDataPreviews )
        self._example_data_post_conversion_preview = ClientGUICommon.SaneMultilineTextCtrl( post_conversion_panel, style = wx.TE_READONLY )
        
        #
        
        self._example_data_post_conversion = ''
        
        #
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( self._example_data_post_conversion_description, CC.FLAGS_EXPAND_BOTH_WAYS )
        hbox.Add( self._copy_button_post_conversion, CC.FLAGS_VCENTER )
        hbox.Add( self._refresh_post_conversion_button, CC.FLAGS_VCENTER )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.Add( self._example_data_post_conversion_preview, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        post_conversion_panel.SetSizer( vbox )
        
        #
        
        self._data_preview_notebook.AddPage( post_conversion_panel, 'post pre-parsing conversion', select = False )
        
    
    def _CopyPostConversion( self ):
        
        HG.client_controller.pub( 'clipboard', 'text', self._example_data_post_conversion )
        
    
    def _RefreshDataPreviews( self ):
        
        self._SetExampleData( self._example_data_raw )
        
    
    def _SetExampleData( self, example_data ):
        
        TestPanel._SetExampleData( self, example_data )
        
        pre_parsing_conversion = self._pre_parsing_conversion_callable()
        
        if pre_parsing_conversion.MakesChanges():
            
            try:
                
                post_conversion_example_data = ClientParsing.MakeParsedTextPretty( pre_parsing_conversion.Convert( self._example_data_raw ) )
                
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
            
            description = self._example_data_raw_description.GetLabelText()
            
        
        self._example_data_post_conversion_description.SetLabelText( description )
        
        self._example_data_post_conversion = post_conversion_example_data
        
        self._example_data_post_conversion_preview.SetValue( preview )
        
    
    def GetTestContext( self ):
        
        example_parsing_context = self._example_parsing_context.GetValue()
        
        return ( example_parsing_context, self._example_data_post_conversion )
        
    
class TestPanelPageParserSubsidiary( TestPanelPageParser ):
    
    def __init__( self, parent, object_callable, pre_parsing_conversion_callable, formula_callable, test_context = None ):
        
        TestPanelPageParser.__init__( self, parent, object_callable, pre_parsing_conversion_callable, test_context = test_context )
        
        self._formula_callable = formula_callable
        
        post_separation_panel = wx.Panel( self._data_preview_notebook )
        
        self._example_data_post_separation_description = ClientGUICommon.BetterStaticText( post_separation_panel )
        
        self._copy_button_post_separation = ClientGUICommon.BetterBitmapButton( post_separation_panel, CC.GlobalBMPs.copy, self._CopyPostSeparation )
        self._copy_button_post_separation.SetToolTip( 'Copy the current post separation data to the clipboard.' )
        
        self._refresh_post_separation_button = ClientGUICommon.BetterBitmapButton( post_separation_panel, CC.GlobalBMPs.refresh, self._RefreshDataPreviews )
        self._example_data_post_separation_preview = ClientGUICommon.SaneMultilineTextCtrl( post_separation_panel, style = wx.TE_READONLY )
        
        #
        
        self._example_data_post_separation = []
        
        #
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( self._example_data_post_separation_description, CC.FLAGS_EXPAND_BOTH_WAYS )
        hbox.Add( self._copy_button_post_separation, CC.FLAGS_VCENTER )
        hbox.Add( self._refresh_post_separation_button, CC.FLAGS_VCENTER )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.Add( self._example_data_post_separation_preview, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        post_separation_panel.SetSizer( vbox )
        
        #
        
        self._data_preview_notebook.AddPage( post_separation_panel, 'post separation conversion', select = False )
        
    
    def _CopyPostSeparation( self ):
        
        joiner = os.linesep * 2
        
        HG.client_controller.pub( 'clipboard', 'text', joiner.join( self._example_data_post_separation ) )
        
    
    def _SetExampleData( self, example_data ):
        
        TestPanelPageParser._SetExampleData( self, example_data )
        
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
                
            
        
        self._example_data_post_separation_description.SetLabelText( description )
        
        self._example_data_post_separation = separation_example_data
        
        self._example_data_post_separation_preview.SetValue( preview )
        
    
    def GetTestContext( self ):
        
        example_parsing_context = self._example_parsing_context.GetValue()
        
        if len( self._example_data_post_separation ) == 0:
            
            example_data = ''
            
        else:
            
            # I had ideas on making this some clever random stuff, but screw it, let's just KISS and send up the first
            
            example_data = self._example_data_post_separation[0]
            
        
        return ( example_parsing_context, example_data )
        
    
    def TestParse( self ):
        
        formula = self._formula_callable()
        
        page_parser = self._object_callable()
        
        try:
            
            example_parsing_context = self._example_parsing_context.GetValue()
            
            if formula is None:
                
                posts = [ self._example_data_raw ]
                
            else:
                
                posts = formula.Parse( example_parsing_context, self._example_data_raw )
                
            
            pretty_texts = []
            
            for post in posts:
                
                pretty_text = page_parser.ParsePretty( example_parsing_context, post )
                
                pretty_texts.append( pretty_text )
                
            
            separator = os.linesep * 2
            
            end_pretty_text = separator.join( pretty_texts )
            
            self._results.SetValue( end_pretty_text )
            
        except Exception as e:
            
            etype = type( e )
            
            ( etype, value, tb ) = sys.exc_info()
            
            trace = ''.join( traceback.format_exception( etype, value, tb ) )
            
            message = 'Exception:' + os.linesep + str( etype.__name__ ) + ': ' + str( e ) + os.linesep + trace
            
            self._results.SetValue( message )
            
        
    
    
