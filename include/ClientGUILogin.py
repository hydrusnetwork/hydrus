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
from . import ClientGUIParsing
from . import ClientGUIScrolledPanels
from . import ClientGUIScrolledPanelsEdit
from . import ClientGUISerialisable
from . import ClientGUITopLevelWindows
from . import ClientImporting
from . import ClientNetworking
from . import ClientNetworkingBandwidth
from . import ClientNetworkingContexts
from . import ClientNetworkingDomain
from . import ClientNetworkingLogin
from . import ClientNetworkingJobs
from . import ClientNetworkingSessions
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
import os
import re
import threading
import traceback
import time
import wx

class EditLoginCredentialsPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, credential_definitions, credentials ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        #
        
        self._control_data = []
        
        rows = []
        
        credential_definitions = list( credential_definitions )
        
        credential_definitions.sort( key = lambda cd: cd.ShouldHide() )
        
        for credential_definition in credential_definitions:
            
            if credential_definition.ShouldHide():
                
                style = wx.TE_PASSWORD
                
            else:
                
                style = 0
                
            
            control = wx.TextCtrl( self, style = style )
            
            name = credential_definition.GetName()
            
            if name in credentials:
                
                control.SetValue( credentials[ name ] )
                
            
            control.Bind( wx.EVT_TEXT, self.EventKey )
            
            control_st = ClientGUICommon.BetterStaticText( self )
            
            self._control_data.append( ( credential_definition, control, control_st ) )
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.Add( control, CC.FLAGS_EXPAND_BOTH_WAYS )
            hbox.Add( control_st, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            rows.append( ( credential_definition.GetName() + ': ', hbox ) )
            
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        self.SetSizer( gridbox )
        
        self._UpdateSts()
        
    
    def _UpdateSts( self ):
        
        for ( credential_definition, control, control_st ) in self._control_data:
            
            value = control.GetValue()
            
            colour = ( 127, 0, 0 )
            
            if value == '':
                
                string_match = credential_definition.GetStringMatch()
                
                if string_match is None:
                    
                    st_label = ''
                    
                else:
                    
                    st_label = string_match.ToString()
                    
                
            else:
                
                try:
                    
                    credential_definition.Test( value )
                    
                    st_label = 'looks good \u2713'
                    
                    colour = ( 0, 127, 0 )
                    
                except Exception as e:
                    
                    st_label = str( e )
                    
                
            
            control_st.SetLabelText( st_label )
            control_st.SetForegroundColour( colour )
            
        
    
    def CanOK( self ):
        
        veto_errors = []
        
        for ( credential_definition, control, control_st ) in self._control_data:
            
            name = credential_definition.GetName()
            
            value = control.GetValue()
            
            if value == '':
                
                veto_errors.append( 'Value for ' + name + ' is blank!' )
                
            else:
                
                try:
                    
                    credential_definition.Test( value )
                    
                except Exception as e:
                    
                    veto_errors.append( 'For ' + name + ': ' + str( e ) )
                    
                
            
        
        if len( veto_errors ) > 0:
            
            message = 'These values are invalid--are you sure this is ok?'
            message += os.linesep * 2
            message += os.linesep.join( veto_errors )
            
            with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
                
                if dlg.ShowModal() != wx.ID_YES:
                    
                    return False
                    
                
            
        
        return True
        
    
    def EventKey( self, event ):
        
        self._UpdateSts()
        
        event.Skip()
        
    
    def GetValue( self ):
        
        credentials = {}
        
        for ( credential_definition, control, control_st ) in self._control_data:
            
            name = credential_definition.GetName()
            
            value = control.GetValue()
            
            credentials[ name ] = value
            
        
        return credentials
        
    
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
    
    def __init__( self, parent, engine, login_scripts, domains_to_login_info ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._engine = engine
        self._login_scripts = login_scripts
        
        self._domains_to_login_after_ok = []
        
        self._domains_and_login_info_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        columns = [ ( 'domain', 20 ), ( 'login script', -1 ), ( 'access given', 36 ), ( 'active?', 8 ), ( 'logged in now?', 28 ), ( 'validity', 28 ), ( 'recent error/delay?', 21 ) ]
        
        self._domains_and_login_info = ClientGUIListCtrl.BetterListCtrl( self._domains_and_login_info_panel, 'domains_to_login_info', 8, 36, columns, self._ConvertDomainAndLoginInfoListCtrlTuples, use_simple_delete = True, activation_callback = self._EditCredentials )
        
        self._domains_and_login_info_panel.SetListCtrl( self._domains_and_login_info )
        
        self._domains_and_login_info_panel.AddButton( 'add', self._Add )
        self._domains_and_login_info_panel.AddDeleteButton()
        self._domains_and_login_info_panel.AddSeparator()
        self._domains_and_login_info_panel.AddButton( 'edit credentials', self._EditCredentials, enabled_check_func = self._CanEditCreds )
        self._domains_and_login_info_panel.AddButton( 'change login script', self._EditLoginScript, enabled_only_on_selection = True )
        self._domains_and_login_info_panel.AddButton( 'flip active', self._FlipActive, enabled_only_on_selection = True )
        self._domains_and_login_info_panel.AddSeparator()
        self._domains_and_login_info_panel.AddButton( 'scrub invalidity', self._ScrubInvalidity, enabled_check_func = self._CanScrubInvalidity )
        self._domains_and_login_info_panel.AddButton( 'scrub delays', self._ScrubDelays, enabled_check_func = self._CanScrubDelays )
        self._domains_and_login_info_panel.NewButtonRow()
        self._domains_and_login_info_panel.AddButton( 'do login now', self._DoLogin, enabled_check_func = self._CanDoLogin )
        self._domains_and_login_info_panel.AddButton( 'reset login (delete cookies)', self._ClearSessions, enabled_only_on_selection = True )
        
        #
        
        listctrl_data = []
        
        for ( login_domain, ( login_script_key_and_name, credentials, login_access_type, login_access_text, active, validity, validity_error_text, no_work_until, no_work_until_reason ) ) in list(domains_to_login_info.items()):
            
            credentials_tuple = tuple( credentials.items() )
            
            domain_and_login_info = ( login_domain, login_script_key_and_name, credentials_tuple, login_access_type, login_access_text, active, validity, validity_error_text, no_work_until, no_work_until_reason )
            
            listctrl_data.append( domain_and_login_info )
            
        
        self._domains_and_login_info.AddDatas( listctrl_data )
        
        self._domains_and_login_info.Sort( 0 )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        warning = 'WARNING: Your credentials are stored in plaintext! For this and other reasons, I recommend you use throwaway accounts with hydrus!'
        
        warning_st = ClientGUICommon.BetterStaticText( self, warning )
        
        warning_st.SetForegroundColour( ( 128, 0, 0 ) )
        
        vbox.Add( warning_st, CC.FLAGS_CENTER )
        vbox.Add( self._domains_and_login_info_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
    
    def _Add( self ):
        
        if len( self._login_scripts ) == 0:
            
            wx.MessageBox( 'You have no login scripts, so you cannot add a new login!' )
            
            return
            
        
        choice_tuples = [ ( login_script.GetName(), login_script ) for login_script in self._login_scripts ]
        
        try:
            
            login_script = ClientGUIDialogsQuick.SelectFromList( self, 'select the login script to use', choice_tuples )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        example_domains = set( login_script.GetExampleDomains() )
        
        domains_in_use = { login_domain for ( login_domain, login_script_key_and_name, credentials_tuple, login_access_type, login_access_text, active, validity, validity_error_text, no_work_until, no_work_until_reason ) in self._domains_and_login_info.GetData() }
        
        available_examples = list( example_domains.difference( domains_in_use ) )
        
        available_examples.sort()
        
        if len( available_examples ) > 0:
            
            choice_tuples = [ ( login_domain, login_domain ) for login_domain in available_examples ]
            
            choice_tuples.append( ( 'use other domain', None ) )
            
            try:
                
                login_domain = ClientGUIDialogsQuick.SelectFromList( self, 'select the domain to use', choice_tuples, sort_tuples = False )
                
            except HydrusExceptions.CancelledException:
                
                return
                
            
            if login_domain is not None:
                
                ( login_access_type, login_access_text ) = login_script.GetExampleDomainInfo( login_domain )
                
            
        else:
            
            login_domain = None
            
        
        if login_domain is None:
            
            with ClientGUIDialogs.DialogTextEntry( self, 'enter the domain', default = 'example.com', allow_blank = False ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    login_domain = dlg.GetValue()
                    
                    if login_domain in domains_in_use:
                        
                        wx.MessageBox( 'That domain is already in use!' )
                        
                        return
                        
                    
                    a_types = [ ClientNetworkingLogin.LOGIN_ACCESS_TYPE_EVERYTHING, ClientNetworkingLogin.LOGIN_ACCESS_TYPE_NSFW, ClientNetworkingLogin.LOGIN_ACCESS_TYPE_SPECIAL, ClientNetworkingLogin.LOGIN_ACCESS_TYPE_USER_PREFS_ONLY ]
                    
                    choice_tuples = [ ( ClientNetworkingLogin.login_access_type_str_lookup[ a_type ], a_type ) for a_type in a_types ]
                    
                    try:
                        
                        login_access_type = ClientGUIDialogsQuick.SelectFromList( self, 'select what type of access the login gives to this domain', choice_tuples, sort_tuples = False )
                        
                    except HydrusExceptions.CancelledException:
                        
                        return
                        
                    
                    login_access_text = ClientNetworkingLogin.login_access_type_default_description_lookup[ login_access_type ]
                    
                    with ClientGUIDialogs.DialogTextEntry( self, 'edit the access description, if needed', default = login_access_text, allow_blank = False ) as dlg:
                        
                        if dlg.ShowModal() == wx.ID_OK:
                            
                            login_access_text = dlg.GetValue()
                            
                        else:
                            
                            return
                            
                        
                    
                else:
                    
                    return
                    
                
            
        
        credential_definitions = login_script.GetCredentialDefinitions()
        
        credentials = {}
        
        if len( credential_definitions ) > 0:
            
            with ClientGUITopLevelWindows.DialogEdit( self, 'edit login' ) as dlg:
                
                panel = EditLoginCredentialsPanel( dlg, credential_definitions, credentials )
                
                dlg.SetPanel( panel )
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    credentials = panel.GetValue()
                    
                else:
                    
                    return
                    
                
            
        
        try:
            
            login_script.CheckCanLogin( credentials )
            
            validity = ClientNetworkingLogin.VALIDITY_UNTESTED
            validity_error_text = ''
            
            # hacky: if there are creds, is at least one not empty string?
            creds_are_good = len( credentials ) == 0 or True in ( value != '' for value in list(credentials.values()) )
            
        except HydrusExceptions.ValidationException as e:
            
            validity = ClientNetworkingLogin.VALIDITY_INVALID
            validity_error_text = str( e )
            
            creds_are_good = False
            
        
        if creds_are_good:
            
            message = 'Activate this login script for this domain?'
            
            with ClientGUIDialogs.DialogYesNo( self, message, title = message ) as dlg:
                
                if dlg.ShowModal() == wx.ID_YES:
                    
                    active = True
                    
                else:
                    
                    active = False
                    
                
            
        else:
            
            active = False
            
        
        login_script_key_and_name = login_script.GetLoginScriptKeyAndName()
        credentials_tuple = tuple( credentials.items() )
        no_work_until = 0
        no_work_until_reason = ''
        
        domain_and_login_info = ( login_domain, login_script_key_and_name, credentials_tuple, login_access_type, login_access_text, active, validity, validity_error_text, no_work_until, no_work_until_reason )
        
        self._domains_and_login_info.AddDatas( ( domain_and_login_info, ) )
        
        self._domains_and_login_info.Sort()
        
    
    def _CanDoLogin( self ):
        
        domain_and_login_infos = self._domains_and_login_info.GetData( only_selected = True )
        
        for domain_and_login_info in domain_and_login_infos:
            
            ( login_domain, login_script_key_and_name, credentials_tuple, login_access_type, login_access_text, active, validity, validity_error_text, no_work_until, no_work_until_reason ) = domain_and_login_info
            
            if not active:
                
                continue
                
            
            if validity == ClientNetworkingLogin.VALIDITY_INVALID:
                
                continue
                
            
            try:
                
                login_script = self._GetLoginScript( login_script_key_and_name )
                
                network_context = ClientNetworkingContexts.NetworkContext( context_type = CC.NETWORK_CONTEXT_DOMAIN, context_data = login_domain )
                
                logged_in = login_script.IsLoggedIn( self._engine, network_context )
                
                if logged_in:
                    
                    continue
                    
                
            except HydrusExceptions.DataMissing:
                
                continue
                
            
            return True
            
        
        return False
        
    
    def _CanEditCreds( self ):
        
        domain_and_login_infos = self._domains_and_login_info.GetData( only_selected = True )
        
        for domain_and_login_info in domain_and_login_infos:
            
            ( login_domain, login_script_key_and_name, credentials_tuple, login_access_type, login_access_text, active, validity, validity_error_text, no_work_until, no_work_until_reason ) = domain_and_login_info
            
            try:
                
                login_script = self._GetLoginScript( login_script_key_and_name )
                
                if len( login_script.GetCredentialDefinitions() ) > 0:
                    
                    return True
                    
                
            except HydrusExceptions.DataMissing:
                
                continue
                
            
        
        return False
        
    
    def _CanScrubDelays( self ):
        
        domain_and_login_infos = self._domains_and_login_info.GetData( only_selected = True )
        
        for domain_and_login_info in domain_and_login_infos:
            
            ( login_domain, login_script_key_and_name, credentials_tuple, login_access_type, login_access_text, active, validity, validity_error_text, no_work_until, no_work_until_reason ) = domain_and_login_info
            
            if not HydrusData.TimeHasPassed( no_work_until ) or no_work_until_reason != '':
                
                return True
                
            
        
        return False
        
    
    def _CanScrubInvalidity( self ):
        
        domain_and_login_infos = self._domains_and_login_info.GetData( only_selected = True )
        
        for domain_and_login_info in domain_and_login_infos:
            
            ( login_domain, login_script_key_and_name, credentials_tuple, login_access_type, login_access_text, active, validity, validity_error_text, no_work_until, no_work_until_reason ) = domain_and_login_info
            
            if validity == ClientNetworkingLogin.VALIDITY_INVALID:
                
                return True
                
            
        
        return False
        
    
    def _ClearSessions( self ):
        
        domain_and_login_infos = self._domains_and_login_info.GetData( only_selected = True )
        
        if len( domain_and_login_infos ) > 0:
            
            message = 'Are you sure you want to clear these domains\' sessions? This will delete all their existing cookies and cannot be undone.'
            
            with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
                
                if dlg.ShowModal() != wx.ID_YES:
                    
                    return
                    
                
            
            for domain_and_login_info in domain_and_login_infos:
                
                ( login_domain, login_script_key_and_name, credentials_tuple, login_access_type, login_access_text, active, validity, validity_error_text, no_work_until, no_work_until_reason ) = domain_and_login_info
                
                network_context = ClientNetworkingContexts.NetworkContext( context_type = CC.NETWORK_CONTEXT_DOMAIN, context_data = login_domain )
                
                self._engine.session_manager.ClearSession( network_context )
                
            
            self._domains_and_login_info.UpdateDatas()
            
            self._domains_and_login_info_panel.UpdateButtons()
            
        
    
    def _ConvertDomainAndLoginInfoListCtrlTuples( self, domain_and_login_info ):
        
        ( login_domain, login_script_key_and_name, credentials_tuple, login_access_type, login_access_text, active, validity, validity_error_text, no_work_until, no_work_until_reason ) = domain_and_login_info
        
        login_expiry = None
        
        try:
            
            login_script = self._GetLoginScript( login_script_key_and_name )
            
            sort_login_script = login_script.GetName()
            
            network_context = ClientNetworkingContexts.NetworkContext( context_type = CC.NETWORK_CONTEXT_DOMAIN, context_data = login_domain )
            
            logged_in = login_script.IsLoggedIn( self._engine, network_context )
            
            if logged_in:
                
                login_expiry = login_script.GetLoginExpiry( self._engine, network_context )
                
            
        except HydrusExceptions.DataMissing:
            
            sort_login_script = 'login script not found'
            
            logged_in = False
            
        
        access = ClientNetworkingLogin.login_access_type_str_lookup[ login_access_type ] + ' - ' + login_access_text
        
        if active:
            
            sort_active = 'yes'
            
        else:
            
            sort_active = 'no'
            
        
        sort_validity = ClientNetworkingLogin.validity_str_lookup[ validity ]
        
        if len( validity_error_text ) > 0:
            
            sort_validity += ' - ' + validity_error_text
            
        
        sort_logged_in = ( logged_in, login_expiry )
        
        if HydrusData.TimeHasPassed( no_work_until ):
            
            pretty_no_work_until = ''
            
        else:
            
            pretty_no_work_until = HydrusData.ConvertTimestampToPrettyExpires( no_work_until ) + ' - ' + no_work_until_reason
            
        
        pretty_login_domain = login_domain
        pretty_login_script = sort_login_script
        pretty_access = access
        pretty_active = sort_active
        
        if active:
            
            pretty_validity = sort_validity
            
        else:
            
            pretty_validity = ''
            
        
        if logged_in:
            
            if login_expiry is None:
                
                pretty_login_expiry = 'session'
                
            else:
                
                pretty_login_expiry = HydrusData.ConvertTimestampToPrettyExpires( login_expiry )
                
            
            pretty_logged_in = 'yes - ' + pretty_login_expiry
            
        else:
            
            pretty_logged_in = 'no'
            
        
        display_tuple = ( pretty_login_domain, pretty_login_script, pretty_access, pretty_active, pretty_logged_in, pretty_validity, pretty_no_work_until )
        sort_tuple = ( login_domain, sort_login_script, access, sort_active, sort_logged_in, sort_validity, no_work_until )
        
        return ( display_tuple, sort_tuple )
        
    
    def _DoLogin( self ):
        
        domains_to_login = []
        
        domain_and_login_infos = self._domains_and_login_info.GetData( only_selected = True )
        
        for domain_and_login_info in domain_and_login_infos:
            
            ( login_domain, login_script_key_and_name, credentials_tuple, login_access_type, login_access_text, active, validity, validity_error_text, no_work_until, no_work_until_reason ) = domain_and_login_info
            
            if not active:
                
                continue
                
            
            if validity == ClientNetworkingLogin.VALIDITY_INVALID:
                
                continue
                
            
            try:
                
                login_script = self._GetLoginScript( login_script_key_and_name )
                
                network_context = ClientNetworkingContexts.NetworkContext( context_type = CC.NETWORK_CONTEXT_DOMAIN, context_data = login_domain )
                
                logged_in = login_script.IsLoggedIn( self._engine, network_context )
                
                if logged_in:
                    
                    continue
                    
                
            except HydrusExceptions.DataMissing:
                
                continue
                
            
            domains_to_login.append( login_domain )
            
        
        if len( domains_to_login ) == 0:
            
            wx.MessageBox( 'Unfortunately, none of the selected domains appear able to log in. Do you need to activate or scrub something somewhere?' )
            
        else:
            
            domains_to_login.sort()
            
            message = 'It looks like the following domains can log in:'
            message += os.linesep * 2
            message += os.linesep.join( domains_to_login )
            message += os.linesep * 2
            message += 'The dialog will ok and the login attempts will start. Is this ok?'
            
            with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
                
                if dlg.ShowModal() != wx.ID_YES:
                    
                    return
                    
                
            
            self._domains_to_login_after_ok = domains_to_login
            
            self.GetParent().DoOK()
            
        
    
    def _EditCredentials( self ):
        
        domain_and_login_infos = self._domains_and_login_info.GetData( only_selected = True )
        
        for domain_and_login_info in domain_and_login_infos:
            
            ( login_domain, login_script_key_and_name, credentials_tuple, login_access_type, login_access_text, active, validity, validity_error_text, no_work_until, no_work_until_reason ) = domain_and_login_info
            
            try:
                
                login_script = self._GetLoginScript( login_script_key_and_name )
                
            except HydrusExceptions.DataMissing:
                
                wx.MessageBox( 'Could not find a login script for "' + login_domain + '"! Please re-add the login script in the other dialog or update the entry here to a new one!' )
                
                return
                
            
            credential_definitions = login_script.GetCredentialDefinitions()
            
            if len( credential_definitions ) > 0:
                
                with ClientGUITopLevelWindows.DialogEdit( self, 'edit login' ) as dlg:
                    
                    credentials = dict( credentials_tuple )
                    
                    panel = EditLoginCredentialsPanel( dlg, credential_definitions, credentials )
                    
                    dlg.SetPanel( panel )
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        credentials = panel.GetValue()
                        
                    else:
                        
                        return
                        
                    
                
            else:
                
                continue
                
            
            try:
                
                login_script.CheckCanLogin( credentials )
                
                validity = ClientNetworkingLogin.VALIDITY_UNTESTED
                validity_error_text = ''
                
                # hacky: if there are creds, is at least one not empty string?
                creds_are_good = len( credentials ) == 0 or True in ( value != '' for value in list(credentials.values()) )
                
            except HydrusExceptions.ValidationException as e:
                
                validity = ClientNetworkingLogin.VALIDITY_INVALID
                validity_error_text = str( e )
                
                creds_are_good = False
                
            
            credentials_tuple = tuple( credentials.items() )
            
            if creds_are_good:
                
                if not active:
                    
                    message = 'Activate this login script for this domain?'
                    
                    with ClientGUIDialogs.DialogYesNo( self, message, title = message ) as dlg:
                        
                        if dlg.ShowModal() == wx.ID_YES:
                            
                            active = True
                            
                        
                    
                
            else:
                
                active = False
                
            
            no_work_until = 0
            no_work_until_reason = ''
            
            edited_domain_and_login_info = ( login_domain, login_script_key_and_name, credentials_tuple, login_access_type, login_access_text, active, validity, validity_error_text, no_work_until, no_work_until_reason )
            
            self._domains_and_login_info.DeleteDatas( ( domain_and_login_info, ) )
            self._domains_and_login_info.AddDatas( ( edited_domain_and_login_info, ) )
            
        
        self._domains_and_login_info.Sort()
        
    
    def _EditLoginScript( self ):
        
        domain_and_login_infos = self._domains_and_login_info.GetData( only_selected = True )
        
        for domain_and_login_info in domain_and_login_infos:
            
            ( login_domain, login_script_key_and_name, credentials_tuple, login_access_type, login_access_text, active, validity, validity_error_text, no_work_until, no_work_until_reason ) = domain_and_login_info
            
            try:
                
                current_login_script = self._GetLoginScript( login_script_key_and_name )
                
            except HydrusExceptions.DataMissing:
                
                current_login_script = None
                
            
            potential_login_scripts = list( self._login_scripts )
            
            potential_login_scripts.sort( key = lambda ls: ls.GetName() )
            
            matching_potential_login_scripts = [ login_script for login_script in potential_login_scripts if login_domain in login_script.GetExampleDomains() ]
            unmatching_potential_login_scripts = [ login_script for login_script in potential_login_scripts if login_domain not in login_script.GetExampleDomains() ]
            
            choice_tuples = [ ( login_script.GetName(), login_script ) for login_script in matching_potential_login_scripts ]
            
            if len( matching_potential_login_scripts ) > 0 and len( unmatching_potential_login_scripts ) > 0:
                
                choice_tuples.append( ( '------', None ) )
                
            
            choice_tuples.extend( [ ( login_script.GetName(), login_script ) for login_script in unmatching_potential_login_scripts ] )
            
            try:
                
                login_script = ClientGUIDialogsQuick.SelectFromList( self, 'select the login script to use', choice_tuples, value_to_select = current_login_script, sort_tuples = False )
                
            except HydrusExceptions.CancelledException:
                
                break
                
            
            if login_script is None:
                
                break
                
            
            if login_script == current_login_script:
                
                break
                
            
            login_script_key_and_name = login_script.GetLoginScriptKeyAndName()
            
            try:
                
                ( login_access_type, login_access_text ) = login_script.GetExampleDomainInfo( login_domain )
                
            except HydrusExceptions.DataMissing:
                
                a_types = [ ClientNetworkingLogin.LOGIN_ACCESS_TYPE_EVERYTHING, ClientNetworkingLogin.LOGIN_ACCESS_TYPE_NSFW, ClientNetworkingLogin.LOGIN_ACCESS_TYPE_SPECIAL, ClientNetworkingLogin.LOGIN_ACCESS_TYPE_USER_PREFS_ONLY ]
                
                choice_tuples = [ ( ClientNetworkingLogin.login_access_type_str_lookup[ a_type ], a_type ) for a_type in a_types ]
                
                try:
                    
                    login_access_type = ClientGUIDialogsQuick.SelectFromList( self, 'select what type of access the login gives to this domain', choice_tuples, sort_tuples = False )
                    
                except HydrusExceptions.CancelledException:
                    
                    break
                    
                
                login_access_text = ClientNetworkingLogin.login_access_type_default_description_lookup[ login_access_type ]
                
                with ClientGUIDialogs.DialogTextEntry( self, 'edit the access description, if needed', default = login_access_text, allow_blank = False ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        login_access_text = dlg.GetValue()
                        
                    else:
                        
                        break
                        
                    
                
            
            credentials = dict( credentials_tuple )
            
            try:
                
                login_script.CheckCanLogin( credentials )
                
                validity = ClientNetworkingLogin.VALIDITY_UNTESTED
                validity_error_text = ''
                
                creds_are_good = True
                
            except HydrusExceptions.ValidationException as e:
                
                validity = ClientNetworkingLogin.VALIDITY_INVALID
                validity_error_text = str( e )
                
                creds_are_good = False
                
            
            if not creds_are_good:
                
                active = False
                
            
            no_work_until = 0
            no_work_until_reason = ''
            
            edited_domain_and_login_info = ( login_domain, login_script_key_and_name, credentials_tuple, login_access_type, login_access_text, active, validity, validity_error_text, no_work_until, no_work_until_reason )
            
            self._domains_and_login_info.DeleteDatas( ( domain_and_login_info, ) )
            self._domains_and_login_info.AddDatas( ( edited_domain_and_login_info, ) )
            
        
        self._domains_and_login_info.Sort()
        
    
    def _FlipActive( self ):
        
        domain_and_login_infos = self._domains_and_login_info.GetData( only_selected = True )
        
        for domain_and_login_info in domain_and_login_infos:
            
            ( login_domain, login_script_key_and_name, credentials_tuple, login_access_type, login_access_text, active, validity, validity_error_text, no_work_until, no_work_until_reason ) = domain_and_login_info
            
            active = not active
            
            flipped_domain_and_login_info = ( login_domain, login_script_key_and_name, credentials_tuple, login_access_type, login_access_text, active, validity, validity_error_text, no_work_until, no_work_until_reason )
            
            self._domains_and_login_info.DeleteDatas( ( domain_and_login_info, ) )
            self._domains_and_login_info.AddDatas( ( flipped_domain_and_login_info, ) )
            
        
        self._domains_and_login_info.Sort()
        
    
    def _GetLoginScript( self, login_script_key_and_name ):
        
        ( login_script_key, login_script_name ) = login_script_key_and_name
        
        for login_script in self._login_scripts:
            
            if login_script.GetLoginScriptKey() == login_script_key:
                
                return login_script
                
            
        
        for login_script in self._login_scripts:
            
            if login_script.GetName() == login_script_name:
                
                return login_script
                
            
        
        raise HydrusExceptions.DataMissing( 'No login script found!' )
        
    
    def _ScrubDelays( self ):
        
        domain_and_login_infos = self._domains_and_login_info.GetData( only_selected = True )
        
        for domain_and_login_info in domain_and_login_infos:
            
            ( login_domain, login_script_key_and_name, credentials_tuple, login_access_type, login_access_text, active, validity, validity_error_text, no_work_until, no_work_until_reason ) = domain_and_login_info
            
            no_work_until = 0
            no_work_until_reason = ''
            
            scrubbed_domain_and_login_info = ( login_domain, login_script_key_and_name, credentials_tuple, login_access_type, login_access_text, active, validity, validity_error_text, no_work_until, no_work_until_reason )
            
            self._domains_and_login_info.DeleteDatas( ( domain_and_login_info, ) )
            self._domains_and_login_info.AddDatas( ( scrubbed_domain_and_login_info, ) )
            
        
        self._domains_and_login_info.Sort()
        
    
    def _ScrubInvalidity( self ):
        
        domain_and_login_infos = self._domains_and_login_info.GetData( only_selected = True )
        
        for domain_and_login_info in domain_and_login_infos:
            
            ( login_domain, login_script_key_and_name, credentials_tuple, login_access_type, login_access_text, active, validity, validity_error_text, no_work_until, no_work_until_reason ) = domain_and_login_info
            
            if validity != ClientNetworkingLogin.VALIDITY_INVALID:
                
                continue
                
            
            try:
                
                try:
                    
                    login_script = self._GetLoginScript( login_script_key_and_name )
                    
                except HydrusExceptions.DataMissing:
                    
                    continue
                    
                
                credentials = dict( credentials_tuple )
                
                login_script.CheckCanLogin( credentials )
                
                validity = ClientNetworkingLogin.VALIDITY_UNTESTED
                validity_error_text = ''
                
            except HydrusExceptions.ValidationException as e:
                
                validity = ClientNetworkingLogin.VALIDITY_INVALID
                validity_error_text = str( e )
                
            
            scrubbed_domain_and_login_info = ( login_domain, login_script_key_and_name, credentials_tuple, login_access_type, login_access_text, active, validity, validity_error_text, no_work_until, no_work_until_reason )
            
            self._domains_and_login_info.DeleteDatas( ( domain_and_login_info, ) )
            self._domains_and_login_info.AddDatas( ( scrubbed_domain_and_login_info, ) )
            
        
        self._domains_and_login_info.Sort()
        
    
    def GetDomainsToLoginAfterOK( self ):
        
        return self._domains_to_login_after_ok
        
    
    def GetValue( self ):
        
        domains_to_login_info = dict()
        
        for ( login_domain, login_script_key_and_name, credentials_tuple, login_access_type, login_access_text, active, validity, validity_error_text, no_work_until, no_work_until_reason ) in self._domains_and_login_info.GetData():
            
            credentials = dict( credentials_tuple )
            
            domains_to_login_info[ login_domain ] = ( login_script_key_and_name, credentials, login_access_type, login_access_text, active, validity, validity_error_text, no_work_until, no_work_until_reason )
            
        
        return domains_to_login_info
        
    
def GenerateTestNetworkJobPresentationContextFactory( window, network_job_control ):
    
    def network_job_presentation_context_factory( network_job ):
        
        def wx_set_it( nj ):
            
            if not window:
                
                return
                
            
            network_job_control.SetNetworkJob( nj )
            
        
        def enter_call():
            
            wx.CallAfter( wx_set_it, network_job )
            
        
        def exit_call():
            
            wx.CallAfter( wx_set_it, None )
            
        
        return ClientImporting.NetworkJobPresentationContext( enter_call, exit_call )
        
    
    return network_job_presentation_context_factory
    
class ReviewTestResultPanel( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent, test_result ):
        
        ClientGUIScrolledPanels.ReviewPanel.__init__( self, parent )
        
        ( name, url, body, self._downloaded_data, new_temp_strings, new_cookie_strings, result ) = test_result
        
        self._name = ClientGUICommon.BetterStaticText( self, label = name )
        self._url = wx.TextCtrl( self )
        
        self._body = wx.TextCtrl( self, style = wx.TE_MULTILINE )
        self._body.SetEditable( False )
        
        min_size = ClientGUIFunctions.ConvertTextToPixels( self._body, ( 64, 3 ) )
        
        self._body.SetMinClientSize( min_size )
        
        self._data_preview = wx.TextCtrl( self, style = wx.TE_MULTILINE )
        self._data_preview.SetEditable( False )
        
        min_size = ClientGUIFunctions.ConvertTextToPixels( self._data_preview, ( 64, 8 ) )
        
        self._data_preview.SetMinClientSize( min_size )
        
        self._data_copy_button = ClientGUICommon.BetterBitmapButton( self, CC.GlobalBMPs.copy, self._CopyData )
        self._data_copy_button.SetToolTip( 'Copy the current example data to the clipboard.' )
        
        self._temp_variables = wx.TextCtrl( self, style = wx.TE_MULTILINE )
        self._temp_variables.SetEditable( False )
        
        min_size = ClientGUIFunctions.ConvertTextToPixels( self._temp_variables, ( 64, 6 ) )
        
        self._temp_variables.SetMinClientSize( min_size )
        
        self._cookies = wx.TextCtrl( self, style = wx.TE_MULTILINE )
        self._cookies.SetEditable( False )
        
        min_size = ClientGUIFunctions.ConvertTextToPixels( self._cookies, ( 64, 6 ) )
        
        self._cookies.SetMinClientSize( min_size )
        
        self._result = ClientGUICommon.BetterStaticText( self, label = result )
        
        #
        
        self._url.SetValue( url )
        
        if body is not None:
            
            try:
                
                self._body.SetValue( body )
                
            except:
                
                self._body.SetValue( str( body ) )
                
            
        
        self._data_preview.SetValue( str( self._downloaded_data[:1024] ) )
        
        self._temp_variables.SetValue( os.linesep.join( new_temp_strings ) )
        self._cookies.SetValue( os.linesep.join( new_cookie_strings ) )
        
        #
        
        rows = []
        
        rows.append( ( 'name: ', self._name ) )
        rows.append( ( 'url: ', self._url ) )
        rows.append( ( 'body (if set): ', self._body ) )
        rows.append( ( 'data: ', self._data_preview ) )
        rows.append( ( 'copy data: ', self._data_copy_button ) )
        rows.append( ( 'new temp vars: ', self._temp_variables ) )
        rows.append( ( 'new cookies: ', self._cookies ) )
        rows.append( ( 'result: ', self._result ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        self.SetSizer( gridbox )
        
    
    def _CopyData( self ):
        
        HG.client_controller.pub( 'clipboard', 'text', self._downloaded_data )
        
    
class EditLoginScriptPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, login_script ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._original_login_script = login_script
        
        self._currently_testing = False
        
        self._test_domain = ''
        self._test_credentials = {}
        
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
        
        self._required_cookies_info = ClientGUIControls.StringMatchToStringMatchDictControl( required_cookies_info_box_panel, login_script.GetRequiredCookiesInfo(), min_height = 4, key_name = 'cookie name' )
        
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
        
        test_panel = ClientGUICommon.StaticBox( self, 'testing' )
        
        self._test_button = ClientGUICommon.BetterButton( test_panel, 'run test', self._DoTest )
        
        self._test_network_job_control = ClientGUIControls.NetworkJobControl( test_panel )
        
        test_listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( test_panel )
        
        columns = [ ( 'step', -1 ), ( 'url', 36 ), ( 'result', 14 ) ]
        
        self._test_listctrl = ClientGUIListCtrl.BetterListCtrl( test_listctrl_panel, 'test_login_script_results', 6, 20, columns, self._ConvertTestResultToListCtrlTuples, activation_callback = self._ReviewTestResult )
        
        test_listctrl_panel.SetListCtrl( self._test_listctrl )
        
        test_listctrl_panel.AddButton( 'review', self._ReviewTestResult, enabled_only_on_selection = True )
        
        self._final_test_result = ClientGUICommon.BetterStaticText( test_panel )
        
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
        
        test_panel.Add( self._test_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        test_panel.Add( self._test_network_job_control, CC.FLAGS_EXPAND_PERPENDICULAR )
        test_panel.Add( test_listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        test_panel.Add( self._final_test_result, CC.FLAGS_EXPAND_PERPENDICULAR )
        
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
        
        hbox = ClientGUICommon.BetterBoxSizer( wx.HORIZONTAL )
        
        hbox.Add( vbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        hbox.Add( test_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( hbox )
        
    
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
        
        try:
            
            new_access_type = ClientGUIDialogsQuick.SelectFromList( self, 'select what type of access the login gives to this domain', choice_tuples, value_to_select = access_type, sort_tuples = False )
            
        except HydrusExceptions.CancelledException:
            
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
        
        value = string_match.ToString()
        
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
        
    
    def _ConvertTestResultToListCtrlTuples( self, test_result ):
        
        ( name, url, body, downloaded_data, new_temp_strings, new_cookie_strings, result ) = test_result
        
        pretty_name = name
        
        pretty_url = url
        
        pretty_result = result
        
        display_tuple = ( pretty_name, pretty_url, pretty_result )
        sort_tuple = ( name, url, result )
        
        return ( display_tuple, sort_tuple )
        
    
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
        
    
    def _DoTest( self ):
        
        def wx_add_result( test_result ):
            
            if not self:
                
                return
                
            
            self._test_listctrl.AddDatas( ( test_result, ) )
            
        
        def receive_result( test_result ):
            
            wx.CallAfter( wx_add_result, test_result )
            
        
        def clean_up( final_result ):
            
            if not self:
                
                return
                
            
            wx.MessageBox( final_result )
            
            self._final_test_result.SetLabelText( final_result )
            
            self._test_button.Enable()
            
            self._currently_testing = False
            
        
        def do_it( login_script, domain, credentials, network_job_presentation_context_factory ):
            
            try:
                
                login_result = 'login did not finish'
                
                # a potential here is to properly inform the login manager of the domain map and hence read back the invalidation text
                # but I am catching the info in the raised exception, so nbd really, I think
                
                bandwidth_manager = ClientNetworkingBandwidth.NetworkBandwidthManager()
                session_manager = ClientNetworkingSessions.NetworkSessionManager()
                domain_manager = ClientNetworkingDomain.NetworkDomainManager()
                login_manager = ClientNetworkingLogin.NetworkLoginManager()
                
                network_engine = ClientNetworking.NetworkEngine( HG.client_controller, bandwidth_manager, session_manager, domain_manager, login_manager )
                
                HG.client_controller.CallToThreadLongRunning( network_engine.MainLoop )
                
                network_context = ClientNetworkingContexts.NetworkContext.STATICGenerateForDomain( domain )
                
                login_result = login_script.Start( network_engine, network_context, credentials, network_job_presentation_context_factory = network_job_presentation_context_factory, test_result_callable = wx_add_result )
                
            except Exception as e:
                
                login_result = str( e )
                
                HydrusData.ShowException( e )
                
            finally:
                
                network_engine.Shutdown()
                
                wx.CallAfter( clean_up, login_result )
                
            
        
        if self._currently_testing:
            
            wx.MessageBox( 'Currently testing already! Please cancel current job!' )
            
            return
            
        
        try:
            
            login_script = self.GetValue()
            
        except HydrusExceptions.VetoException:
            
            return
            
        
        if self._test_domain == '':
            
            example_domains = list( login_script.GetExampleDomains() )
            
            example_domains.sort()
            
            if len( example_domains ) > 0:
                
                self._test_domain = example_domains[0]
                
            
        
        with ClientGUIDialogs.DialogTextEntry( self, 'edit the domain', default = self._test_domain, allow_blank = False ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                self._test_domain = dlg.GetValue()
                
            else:
                
                return
                
            
        
        credential_definitions = login_script.GetCredentialDefinitions()
        
        if len( credential_definitions ) > 0:
            
            with ClientGUITopLevelWindows.DialogEdit( self, 'edit login' ) as dlg:
                
                panel = EditLoginCredentialsPanel( dlg, credential_definitions, self._test_credentials )
                
                dlg.SetPanel( panel )
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    self._test_credentials = panel.GetValue()
                    
                else:
                    
                    return
                    
                
            
        else:
            
            self._test_credentials = {}
            
        
        self._test_listctrl.DeleteDatas( self._test_listctrl.GetData() )
        
        self._test_button.Disable()
        
        network_job_presentation_context_factory = GenerateTestNetworkJobPresentationContextFactory( self, self._test_network_job_control )
        
        self._currently_testing = True
        
        HG.client_controller.CallToThread( do_it, login_script, self._test_domain, self._test_credentials, network_job_presentation_context_factory )
        
    
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
            
            try:
                
                new_access_type = ClientGUIDialogsQuick.SelectFromList( self, 'select what type of access the login gives to this domain', choice_tuples, value_to_select = access_type, sort_tuples = False )
                
            except HydrusExceptions.CancelledException:
                
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
        
    
    def _ReviewTestResult( self ):
        
        for test_result in self._test_listctrl.GetData( only_selected = True ):
            
            frame = ClientGUITopLevelWindows.FrameThatTakesScrollablePanel( self, 'login test result' )
            
            panel = ReviewTestResultPanel( frame, test_result )
            
            frame.SetPanel( panel )
            
        
    
    def GetValue( self ):
        
        if self._currently_testing:
            
            raise HydrusExceptions.VetoException( 'Currently testing! Please cancel it first!' )
            
        
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
            message += str( e )
            message += os.linesep * 2
            message += 'Do you want to proceed with this invalid script, or go back and fix it?'
            
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
        
        self._required_cookies_info = ClientGUIControls.StringMatchToStringMatchDictControl( required_cookies_info_box_panel, required_cookies_info, min_height = 4, key_name = 'cookie name' )
        
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
        
        vbox.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
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
        
    
