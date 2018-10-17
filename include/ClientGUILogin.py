import ClientConstants as CC
import ClientData
import ClientDefaults
import ClientGUICommon
import ClientGUIDialogs
import ClientGUIMenus
import ClientGUIControls
import ClientGUIListBoxes
import ClientGUIListCtrl
import ClientGUIParsing
import ClientGUIScrolledPanels
import ClientGUIScrolledPanelsEdit
import ClientGUISerialisable
import ClientGUITopLevelWindows
import ClientNetworkingContexts
import ClientNetworkingDomain
import ClientNetworkingLogin
import ClientNetworkingJobs
import ClientParsing
import ClientPaths
import ClientSerialisable
import ClientThreading
import HydrusConstants as HC
import HydrusData
import HydrusExceptions
import HydrusGlobals as HG
import HydrusSerialisable
import HydrusTags
import HydrusText
import itertools
import os
import re
import threading
import traceback
import time
import wx

class EditLoginCredentialsPanel( ClientGUIScrolledPanels.EditPanel ):
    
    pass
    
class EditLoginCredentialDefinitionPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, credential_definition ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        #
        
        self._name = wx.TextCtrl( self )
        
        self._credential_type = ClientGUICommon.BetterChoice( self )
        
        for credential_type in [ ClientNetworkingLogin.CREDENTIAL_TYPE_TEXT, ClientNetworkingLogin.CREDENTIAL_TYPE_PASS ]:
            
            self._credential_type.Append( ClientNetworkingLogin.credential_type_str_lookup[ credential_type ], credential_type )
            
        
        string_match = credential_definition.GetStringMatch()
        
        self._string_match = ClientGUIControls.StringMatchButton( self, string_match )
        
        #
        
        self._name.SetValue( credential_definition.GetName() )
        self._credential_type.SelectClientData( credential_definition.GetType() )
        
        #
        
        rows = []
        
        rows.append( ( 'name: ', self._name ) )
        rows.append( ( 'input type: ', self._credential_type ) )
        rows.append( ( 'permitted input: ', self._string_match ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        self.SetSizer( gridbox )
        
    
    def GetValue( self ):
        
        name = self._name.GetValue()
        credential_type = self._credential_type.GetChoice()
        string_match = self._string_match.GetValue()
        
        credential_definition = ClientNetworkingLogin.LoginCredentialDefinition( name = name, credential_type = credential_type, string_match = string_match )
        
        return credential_definition
        
    
class EditLoginsPanel( ClientGUIScrolledPanels.EditPanel ):
    
    pass
    
class EditLoginScriptPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, login_script ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._original_login_script = login_script
        
        #
        
        menu_items = []
        
        page_func = HydrusData.Call( ClientPaths.LaunchPathInWebBrowser, os.path.join( HC.HELP_DIR, 'downloader_login.html' ) )
        
        menu_items.append( ( 'normal', 'open the login scripts help', 'Open the help page for login scripts in your web browser.', page_func ) )
        
        help_button = ClientGUICommon.MenuBitmapButton( self, CC.GlobalBMPs.help, menu_items )
        
        help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help for this panel -->', wx.Colour( 0, 0, 255 ) )
        
        #
        
        self._name = wx.TextCtrl( self )
        
        #
        
        credential_definitions_box_panel = ClientGUICommon.StaticBox( self, 'credential definitions' )
        
        credential_definitions_panel = ClientGUIListCtrl.BetterListCtrlPanel( credential_definitions_box_panel )
        
        columns = [ ( 'name', -1 ), ( 'type', 10 ), ( 'value', 16 ) ]
        
        self._credential_definitions = ClientGUIListCtrl.BetterListCtrl( credential_definitions_panel, 'credential_definitions', 4, 16, columns, self._ConvertCredentialDefinitionToListCtrlTuples, use_simple_delete = True, activation_callback = self._EditCredentialDefinitions )
        
        credential_definitions_panel.SetListCtrl( self._credential_definitions )
        
        credential_definitions_panel.AddButton( 'add', self._AddCredentialDefinition )
        credential_definitions_panel.AddButton( 'edit', self._EditCredentialDefinitions, enabled_only_on_selection = True )
        credential_definitions_panel.AddDeleteButton()
        
        #
        
        login_steps_box_panel = ClientGUICommon.StaticBox( self, 'login steps' )
        
        columns = [ ( 'name', -1 ), ( 'url', 56 ) ]
        
        self._login_steps = ClientGUIListBoxes.QueueListBox( login_steps_box_panel, 5, self._ConvertLoginStepToListBoxString, add_callable = self._AddLoginStep, edit_callable = self._EditLoginStep )
        
        #
        
        required_cookies_info_box_panel = ClientGUICommon.StaticBox( self, 'cookies required to consider session logged in' )
        
        self._required_cookies_info = ClientGUIControls.StringToStringMatchDictControl( required_cookies_info_box_panel, login_script.GetRequiredCookiesInfo(), min_height = 4, key_name = 'cookie name' )
        
        #
        
        example_domains_info_box_panel = ClientGUICommon.StaticBox( self, 'example domains' )
        
        example_domains_info_panel = ClientGUIListCtrl.BetterListCtrlPanel( example_domains_info_box_panel )
        
        columns = [ ( 'domain', -1 ), ( 'access type', 14 ), ( 'description', 40 ) ]
        
        self._example_domains_info = ClientGUIListCtrl.BetterListCtrl( example_domains_info_panel, 'example_domains_info', 6, 16, columns, self._ConvertExampleDomainInfoToListCtrlTuples, use_simple_delete = True, activation_callback = self._EditExampleDomainsInfo )
        
        example_domains_info_panel.SetListCtrl( self._example_domains_info )
        
        example_domains_info_panel.AddButton( 'add', self._AddExampleDomainsInfo )
        example_domains_info_panel.AddButton( 'edit', self._EditExampleDomainsInfo, enabled_only_on_selection = True )
        example_domains_info_panel.AddDeleteButton()
        
        #
        
        self._name.SetValue( login_script.GetName() )
        
        self._credential_definitions.SetData( login_script.GetCredentialDefinitions() )
        self._login_steps.AddDatas( login_script.GetLoginSteps() )
        self._example_domains_info.SetData( login_script.GetExampleDomainsInfo() )
        
        #
        
        credential_definitions_box_panel.Add( credential_definitions_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        login_steps_box_panel.Add( self._login_steps, CC.FLAGS_EXPAND_BOTH_WAYS )
        required_cookies_info_box_panel.Add( self._required_cookies_info, CC.FLAGS_EXPAND_BOTH_WAYS )
        example_domains_info_box_panel.Add( example_domains_info_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        rows = []
        
        rows.append( ( 'name: ', self._name ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        vbox = ClientGUICommon.BetterBoxSizer( wx.VERTICAL )
        
        vbox.Add( help_hbox, CC.FLAGS_BUTTON_SIZER )
        vbox.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.Add( credential_definitions_box_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.Add( login_steps_box_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.Add( required_cookies_info_box_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.Add( example_domains_info_box_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
    
    def _AddCredentialDefinition( self ):
        
        new_credential_definition = ClientNetworkingLogin.LoginCredentialDefinition()
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit parser', frame_key = 'deeply_nested_dialog' ) as dlg_edit:
            
            panel = EditLoginCredentialDefinitionPanel( dlg_edit, new_credential_definition )
            
            dlg_edit.SetPanel( panel )
            
            if dlg_edit.ShowModal() == wx.ID_OK:
                
                new_credential_definition = panel.GetValue()
                
                HydrusSerialisable.SetNonDupeName( new_credential_definition, self._GetExistingCredentialDefinitionNames() )
                
                self._credential_definitions.AddDatas( ( new_credential_definition, ) )
                
                self._credential_definitions.Sort()
                
            
        
    
    def _AddExampleDomainsInfo( self ):
        
        ( domain, access_type, access_text ) = ( 'example.com', ClientNetworkingLogin.LOGIN_ACCESS_TYPE_NSFW, ClientNetworkingLogin.login_access_type_default_description_lookup[ ClientNetworkingLogin.LOGIN_ACCESS_TYPE_NSFW ] )
        
        with ClientGUIDialogs.DialogTextEntry( self, 'edit the domain', default = domain, allow_blank = False ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                domain = dlg.GetValue()
                
            else:
                
                return
                
            
        
        existing_domains = self._GetExistingDomains()
        
        if domain in existing_domains:
            
            wx.MessageBox( 'That domain already exists!' )
            
            return
            
        
        a_types = [ ClientNetworkingLogin.LOGIN_ACCESS_TYPE_EVERYTHING, ClientNetworkingLogin.LOGIN_ACCESS_TYPE_NSFW, ClientNetworkingLogin.LOGIN_ACCESS_TYPE_SPECIAL, ClientNetworkingLogin.LOGIN_ACCESS_TYPE_USER_PREFS_ONLY ]
        
        choice_tuples = [ ( ClientNetworkingLogin.login_access_type_str_lookup[ a_type ], a_type ) for a_type in a_types ]
        
        with ClientGUIDialogs.DialogSelectFromList( self, 'select what type of access the login gives to this domain', choice_tuples, value_to_select = access_type, sort_tuples = False ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                new_access_type = dlg.GetChoice()
                
            else:
                
                return
                
            
        
        if new_access_type != access_type:
            
            access_type = new_access_type
            
            access_text = ClientNetworkingLogin.login_access_type_default_description_lookup[ access_type ]
            
        
        with ClientGUIDialogs.DialogTextEntry( self, 'edit the access description, if needed', default = access_text, allow_blank = False ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                access_text = dlg.GetValue()
                
            else:
                
                return
                
            
        
        example_domain_info = ( domain, access_type, access_text )
        
        self._example_domains_info.AddDatas( ( example_domain_info, ) )
        
        self._example_domains_info.Sort()
        
    
    def _AddLoginStep( self ):
        
        login_step = ClientNetworkingLogin.LoginStep()
        
        return self._EditLoginStep( login_step )
        
    
    def _ConvertCredentialDefinitionToListCtrlTuples( self, credential_definition ):
        
        name = credential_definition.GetName()
        credential_type = credential_definition.GetType()
        
        type_string = ClientNetworkingLogin.credential_type_str_lookup[ credential_type ]
        
        string_match = credential_definition.GetStringMatch()
        
        value = string_match.ToUnicode()
        
        pretty_name = name
        pretty_type_string = type_string
        pretty_value = value
        
        display_tuple = ( pretty_name, pretty_type_string, pretty_value )
        sort_tuple = ( name, type_string, value )
        
        return ( display_tuple, sort_tuple )
        
    
    def _ConvertExampleDomainInfoToListCtrlTuples( self, example_domain_info ):
        
        ( domain, access_type, access_text ) = example_domain_info
        
        pretty_domain = domain
        pretty_access_type = ClientNetworkingLogin.login_access_type_str_lookup[ access_type ]
        pretty_access_text = access_text
        
        display_tuple = ( pretty_domain, pretty_access_type, pretty_access_text )
        sort_tuple = ( domain, pretty_access_type, access_text )
        
        return ( display_tuple, sort_tuple )
        
    
    def _ConvertLoginStepToListBoxString( self, login_step ):
        
        name = login_step.GetName()
        
        return name
        
    
    def _EditCredentialDefinitions( self ):
        
        credential_definitions = self._credential_definitions.GetData( only_selected = True )
        
        for credential_definition in credential_definitions:
            
            with ClientGUITopLevelWindows.DialogEdit( self, 'edit login script', frame_key = 'deeply_nested_dialog' ) as dlg:
                
                panel = EditLoginCredentialDefinitionPanel( dlg, credential_definition )
                
                dlg.SetPanel( panel )
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    edited_credential_definition = panel.GetValue()
                    
                    self._credential_definitions.DeleteDatas( ( credential_definition, ) )
                    
                    HydrusSerialisable.SetNonDupeName( edited_credential_definition, self._GetExistingCredentialDefinitionNames() )
                    
                    self._credential_definitions.AddDatas( ( edited_credential_definition, ) )
                    
                else:
                    
                    break
                    
                
            
        
        self._credential_definitions.Sort()
        
    
    
    def _EditExampleDomainsInfo( self ):
        
        selected_example_domains_info = self._example_domains_info.GetData( only_selected = True )
        
        for example_domain_info in selected_example_domains_info:
            
            ( original_domain, access_type, access_text ) = example_domain_info
            
            with ClientGUIDialogs.DialogTextEntry( self, 'edit the domain', default = original_domain, allow_blank = False ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    domain = dlg.GetValue()
                    
                else:
                    
                    break
                    
                
            
            existing_domains = self._GetExistingDomains()
            
            if domain != original_domain and domain in existing_domains:
                
                wx.MessageBox( 'That domain already exists!' )
                
                break
                
            
            a_types = [ ClientNetworkingLogin.LOGIN_ACCESS_TYPE_EVERYTHING, ClientNetworkingLogin.LOGIN_ACCESS_TYPE_NSFW, ClientNetworkingLogin.LOGIN_ACCESS_TYPE_SPECIAL, ClientNetworkingLogin.LOGIN_ACCESS_TYPE_USER_PREFS_ONLY ]
            
            choice_tuples = [ ( ClientNetworkingLogin.login_access_type_str_lookup[ a_type ], a_type ) for a_type in a_types ]
            
            with ClientGUIDialogs.DialogSelectFromList( self, 'select what type of access the login gives to this domain', choice_tuples, value_to_select = access_type, sort_tuples = False ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    new_access_type = dlg.GetChoice()
                    
                else:
                    
                    break
                    
                
            
            if new_access_type != access_type:
                
                access_type = new_access_type
                
                access_text = ClientNetworkingLogin.login_access_type_default_description_lookup[ access_type ]
                
            
            with ClientGUIDialogs.DialogTextEntry( self, 'edit the access description, if needed', default = access_text, allow_blank = False ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    access_text = dlg.GetValue()
                    
                else:
                    
                    break
                    
                
            
            self._example_domains_info.DeleteDatas( ( example_domain_info, ) )
            
            edited_example_domain_info = ( domain, access_type, access_text )
            
            self._example_domains_info.AddDatas( ( edited_example_domain_info, ) )
            
        
        self._example_domains_info.Sort()
        
    
    def _EditLoginStep( self, login_step ):
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit login step' ) as dlg:
            
            panel = EditLoginStepPanel( dlg, login_step )
            
            dlg.SetPanel( panel )
            
            if dlg.ShowModal() == wx.ID_OK:
                
                login_step = panel.GetValue()
                
                return login_step
                
            else:
                
                raise HydrusExceptions.VetoException()
                
            
        
    
    def _GetExistingCredentialDefinitionNames( self ):
        
        return { credential_definition.GetName() for credential_definition in self._credential_definitions.GetData() }
        
    
    def _GetExistingDomains( self ):
        
        return { domain for ( domain, access_type, access_text ) in self._example_domains_info.GetData() }
        
    
    def GetValue( self ):
        
        name = self._name.GetValue()
        
        login_script_key = self._original_login_script.GetLoginScriptKey()
        
        required_cookies_info = self._required_cookies_info.GetValue()
        credential_definitions = self._credential_definitions.GetData()
        login_steps = self._login_steps.GetData()
        example_domains_info = self._example_domains_info.GetData()
        
        credential_names = { credential_definition.GetName() for credential_definition in credential_definitions }
        
        login_script = ClientNetworkingLogin.LoginScriptDomain( name = name, login_script_key = login_script_key, required_cookies_info = required_cookies_info, credential_definitions = credential_definitions, login_steps = login_steps, example_domains_info = example_domains_info )
        
        login_script.SetLoginScriptKey( login_script_key )
        
        try:
            
            login_script.CheckIsValid()
            
        except HydrusExceptions.ValidationException as e:
            
            message = 'There is a problem with this script. The reason is:'
            message += os.linesep * 2
            message += HydrusData.ToUnicode( e )
            message += os.linesep * 2
            message += 'Do you want to ok the dialog on this invalid script, or go back and fix it?'
            
            with ClientGUIDialogs.DialogYesNo( self, message, yes_label = 'ok as invalid', no_label = 'go back' ) as dlg:
                
                if dlg.ShowModal() != wx.ID_YES:
                    
                    raise HydrusExceptions.VetoException( 'The ok event has been cancelled!' )
                    
                
            
        
        return login_script
        
    
class EditLoginScriptsPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, login_scripts ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        login_scripts_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        columns = [ ( 'name', -1 ), ( 'example domains', 40 ) ]
        
        self._login_scripts = ClientGUIListCtrl.BetterListCtrl( login_scripts_panel, 'login_scripts', 20, 24, columns, self._ConvertLoginScriptToListCtrlTuples, use_simple_delete = True, activation_callback = self._Edit )
        
        login_scripts_panel.SetListCtrl( self._login_scripts )
        
        login_scripts_panel.AddButton( 'add', self._Add )
        login_scripts_panel.AddButton( 'edit', self._Edit, enabled_only_on_selection = True )
        login_scripts_panel.AddDeleteButton()
        login_scripts_panel.AddSeparator()
        login_scripts_panel.AddImportExportButtons( ( ClientNetworkingLogin.LoginScriptDomain, ), self._AddLoginScript )
        login_scripts_panel.AddSeparator()
        login_scripts_panel.AddDefaultsButton( ClientDefaults.GetDefaultLoginScripts, self._AddLoginScript )
        
        #
        
        self._login_scripts.AddDatas( login_scripts )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( login_scripts_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
    
    def _Add( self ):
        
        new_login_script = ClientNetworkingLogin.LoginScriptDomain()
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit login script', frame_key = 'deeply_nested_dialog' ) as dlg_edit:
            
            panel = EditLoginScriptPanel( dlg_edit, new_login_script )
            
            dlg_edit.SetPanel( panel )
            
            if dlg_edit.ShowModal() == wx.ID_OK:
                
                new_login_script = panel.GetValue()
                
                self._AddLoginScript( new_login_script )
                
                self._login_scripts.Sort()
                
            
        
    
    def _AddLoginScript( self, login_script ):
        
        HydrusSerialisable.SetNonDupeName( login_script, self._GetExistingNames() )
        
        login_script.RegenerateLoginScriptKey()
        
        self._login_scripts.AddDatas( ( login_script, ) )
        
    
    def _ConvertLoginScriptToListCtrlTuples( self, login_script ):
        
        name = login_script.GetName()
        
        example_domains = list( login_script.GetExampleDomains() )
        example_domains.sort()
        
        pretty_name = name
        pretty_example_domains = ', '.join( example_domains )
        
        display_tuple = ( pretty_name, pretty_example_domains )
        sort_tuple = ( name, example_domains )
        
        return ( display_tuple, sort_tuple )
        
    
    def _Edit( self ):
        
        login_scripts = self._login_scripts.GetData( only_selected = True )
        
        for login_script in login_scripts:
            
            with ClientGUITopLevelWindows.DialogEdit( self, 'edit login script', frame_key = 'deeply_nested_dialog' ) as dlg:
                
                panel = EditLoginScriptPanel( dlg, login_script )
                
                dlg.SetPanel( panel )
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    edited_login_script = panel.GetValue()
                    
                    self._login_scripts.DeleteDatas( ( login_script, ) )
                    
                    HydrusSerialisable.SetNonDupeName( edited_login_script, self._GetExistingNames() )
                    
                    self._login_scripts.AddDatas( ( edited_login_script, ) )
                    
                else:
                    
                    break
                    
                
            
        
        self._login_scripts.Sort()
        
    
    def _GetExistingNames( self ):
        
        names = { login_script.GetName() for login_script in self._login_scripts.GetData() }
        
        return names
        
    
    def GetValue( self ):
        
        return self._login_scripts.GetData()
        
    
class EditLoginStepPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, login_step ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        #
        
        name = login_step.GetName()
        
        ( scheme, method, subdomain, path, required_credentials, static_args, temp_args, required_cookies_info, content_parsers ) = login_step.ToTuple()
        
        #
        
        self._name = wx.TextCtrl( self )
        
        self._method = ClientGUICommon.BetterChoice( self )
        
        self._method.Append( 'GET', 'GET' )
        self._method.Append( 'POST', 'POST' )
        
        self._scheme = ClientGUICommon.BetterChoice( self )
        
        self._scheme.Append( 'http', 'http' )
        self._scheme.Append( 'https', 'https' )
        
        self._subdomain = ClientGUICommon.NoneableTextCtrl( self, none_phrase = 'none' )
        
        self._path = wx.TextCtrl( self )
        
        required_credentials_panel = ClientGUICommon.StaticBox( self, 'credentials to send' )
        
        self._required_credentials = ClientGUIControls.StringToStringDictControl( required_credentials_panel, required_credentials, min_height = 4, key_name = 'credential name', value_name = 'parameter name' )
        
        #
        
        static_args_panel = ClientGUICommon.StaticBox( self, 'static variables to send' )
        
        self._static_args = ClientGUIControls.StringToStringDictControl( static_args_panel, static_args, min_height = 4, key_name = 'parameter name', value_name = 'value' )
        
        #
        
        temp_args_panel = ClientGUICommon.StaticBox( self, 'temporary variables to send' )
        
        self._temp_args = ClientGUIControls.StringToStringDictControl( temp_args_panel, temp_args, min_height = 4, key_name = 'temp variable name', value_name = 'parameter name' )
        
        #
        
        required_cookies_info_box_panel = ClientGUICommon.StaticBox( self, 'cookies required to consider step successful' )
        
        self._required_cookies_info = ClientGUIControls.StringToStringMatchDictControl( required_cookies_info_box_panel, required_cookies_info, min_height = 4, key_name = 'cookie name' )
        
        #
        
        content_parsers_panel = ClientGUICommon.StaticBox( self, 'content parsers' )
        
        test_context_callable = lambda: ( {}, '' )
        
        permitted_content_types = [ HC.CONTENT_TYPE_VARIABLE, HC.CONTENT_TYPE_VETO ]
        
        self._content_parsers = ClientGUIParsing.EditContentParsersPanel( content_parsers_panel, test_context_callable, permitted_content_types )
        
        # a test panel a la pageparsers
        
        #
        
        self._name.SetValue( name )
        self._scheme.SelectClientData( scheme )
        self._method.SelectClientData( method )
        self._subdomain.SetValue( subdomain )
        self._path.SetValue( path )
        
        self._content_parsers.AddDatas( content_parsers )
        
        #
        
        required_credentials_panel.Add( self._required_credentials, CC.FLAGS_EXPAND_BOTH_WAYS )
        static_args_panel.Add( self._static_args, CC.FLAGS_EXPAND_BOTH_WAYS )
        temp_args_panel.Add( self._temp_args, CC.FLAGS_EXPAND_BOTH_WAYS )
        required_cookies_info_box_panel.Add( self._required_cookies_info, CC.FLAGS_EXPAND_BOTH_WAYS )
        content_parsers_panel.Add( self._content_parsers, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        rows = []
        
        rows.append( ( 'name: ', self._name ) )
        rows.append( ( 'scheme: ', self._scheme ) )
        rows.append( ( 'method: ', self._method ) )
        rows.append( ( 'subdomain (replaces www, if present): ', self._subdomain ) )
        rows.append( ( 'path: ', self._path ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        vbox = ClientGUICommon.BetterBoxSizer( wx.VERTICAL )
        
        vbox.Add( gridbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( required_credentials_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.Add( static_args_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.Add( temp_args_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.Add( required_cookies_info_box_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.Add( content_parsers_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
    
    def GetValue( self ):
        
        name = self._name.GetValue()
        scheme = self._scheme.GetChoice()
        method = self._method.GetChoice()
        subdomain = self._subdomain.GetValue()
        path = self._path.GetValue()
        
        required_credentials = self._required_credentials.GetValue()
        static_args = self._static_args.GetValue()
        temp_args = self._temp_args.GetValue()
        required_cookies_info = self._required_cookies_info.GetValue()
        content_parsers = self._content_parsers.GetData()
        
        if subdomain == '':
            
            subdomain = None
            
        
        login_step = ClientNetworkingLogin.LoginStep( name = name, scheme = scheme, method = method, subdomain = subdomain, path = path )
        
        login_step.SetComplicatedVariables( required_credentials, static_args, temp_args, required_cookies_info, content_parsers )
        
        return login_step
        
    
