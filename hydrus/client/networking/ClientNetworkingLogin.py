import itertools
import re
import threading
import time
import typing
import urllib.parse

from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusText
from hydrus.core import HydrusTime

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientStrings
from hydrus.client import ClientThreading
from hydrus.client.networking import ClientNetworkingContexts
from hydrus.client.networking import ClientNetworkingFunctions
from hydrus.client.networking import ClientNetworkingJobs
from hydrus.client.parsing import ClientParsing
from hydrus.client.parsing import ClientParsingResults

VALIDITY_VALID = 0
VALIDITY_UNTESTED = 1
VALIDITY_INVALID = 2

validity_str_lookup = {}

validity_str_lookup[ VALIDITY_VALID ] = 'valid'
validity_str_lookup[ VALIDITY_UNTESTED ] = 'untested'
validity_str_lookup[ VALIDITY_INVALID ] = 'invalid'

LOGIN_ACCESS_TYPE_EVERYTHING = 0
LOGIN_ACCESS_TYPE_NSFW = 1
LOGIN_ACCESS_TYPE_SPECIAL = 2
LOGIN_ACCESS_TYPE_USER_PREFS_ONLY = 3

login_access_type_str_lookup = {}

login_access_type_str_lookup[ LOGIN_ACCESS_TYPE_EVERYTHING ] = 'Everything'
login_access_type_str_lookup[ LOGIN_ACCESS_TYPE_NSFW ] = 'NSFW'
login_access_type_str_lookup[ LOGIN_ACCESS_TYPE_SPECIAL ] = 'Special'
login_access_type_str_lookup[ LOGIN_ACCESS_TYPE_USER_PREFS_ONLY ] = 'User prefs'

login_access_type_default_description_lookup = {}

login_access_type_default_description_lookup[ LOGIN_ACCESS_TYPE_EVERYTHING ] = 'Login required to access any content.'
login_access_type_default_description_lookup[ LOGIN_ACCESS_TYPE_NSFW ] = 'Login required to access NSFW content.'
login_access_type_default_description_lookup[ LOGIN_ACCESS_TYPE_SPECIAL ] = 'Login required to access special content.'
login_access_type_default_description_lookup[ LOGIN_ACCESS_TYPE_USER_PREFS_ONLY ] = 'Login only required to access user preferences.'

PIXIV_NETWORK_CONTEXT = ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_DOMAIN, 'pixiv.net' )
HENTAI_FOUNDRY_NETWORK_CONTEXT = ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_DOMAIN, 'hentai-foundry.com' )

class NetworkLoginManager( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_LOGIN_MANAGER
    SERIALISABLE_NAME = 'Login Manager'
    SERIALISABLE_VERSION = 1
    
    SESSION_TIMEOUT = 60 * 45
    
    def __init__( self ):
        
        super().__init__()
        
        self.engine = None
        
        self._dirty = False
        
        self._lock = threading.Lock()
        
        self._login_scripts = HydrusSerialisable.SerialisableList()
        self._domains_to_login_info = {}
        
        self._login_script_keys_to_login_scripts = {}
        self._login_script_names_to_login_scripts = {}
        
        self._current_login_process: LoginProcess | None = None
        
        self._hydrus_login_script = LoginScriptHydrus()
        
        self._error_names = set()
        
    
    def _GetBestLoginScript( self, login_domain ):
        
        self._login_scripts.sort( key = lambda ls: len( ls.GetCredentialDefinitions() ) )
        
        for login_script in self._login_scripts:
            
            if login_domain in login_script.GetExampleDomains():
                
                return login_script
                
            
        
        return None
        
    
    def _GetLoginDomainStatus( self, network_context ):
        
        login_domain = None
        login_expected = False
        login_possible = True
        login_error_text = ''
        
        domain = network_context.context_data
        
        potential_login_domains = ClientNetworkingFunctions.ConvertDomainIntoAllApplicableDomains( domain, discard_www = False )
        
        for potential_login_domain in potential_login_domains:
            
            if potential_login_domain in self._domains_to_login_info:
                
                login_domain = potential_login_domain
                
                ( login_script_key_and_name, credentials, login_access_type, login_access_text, active, validity, validity_error_text, no_work_until, no_work_until_reason ) = self._domains_to_login_info[ login_domain ]
                
                if active:
                    
                    login_expected = True
                    
                
                if not active:
                    
                    login_possible = False
                    login_error_text = 'Not active - ' + login_access_text
                    
                elif validity == VALIDITY_INVALID:
                    
                    login_possible = False
                    login_error_text = validity_error_text
                    
                elif not HydrusTime.TimeHasPassed( no_work_until ):
                    
                    login_possible = False
                    login_error_text = no_work_until_reason
                    
                
                break
                
            
        
        return ( login_domain, login_expected, login_possible, login_error_text )
        
    
    def _GetLoginScriptAndCredentials( self, login_domain ):
        
        if login_domain in self._domains_to_login_info:
            
            ( login_script_key_and_name, credentials, login_access_type, login_access_text, active, validity, validity_error_text, no_work_until, no_work_until_reason ) = self._domains_to_login_info[ login_domain ]
            
            ( login_script_key, login_script_name ) = login_script_key_and_name
            
            if login_script_key in self._login_script_keys_to_login_scripts:
                
                login_script = self._login_script_keys_to_login_scripts[ login_script_key ]
                
            elif login_script_name in self._login_script_names_to_login_scripts:
                
                login_script = self._login_script_names_to_login_scripts[ login_script_name ]
                
                login_script_key_and_name = login_script.GetLoginScriptKeyAndName()
                
                self._SetDirty()
                
                self._domains_to_login_info[ login_domain ] = ( login_script_key_and_name, credentials, login_access_type, login_access_text, active, validity, validity_error_text, no_work_until, no_work_until_reason )
                
            else:
                
                validity = VALIDITY_INVALID
                validity_error_text = 'Could not find the login script for "' + login_domain + '"!'
                
                self._domains_to_login_info[ login_domain ] = ( login_script_key_and_name, credentials, login_access_type, login_access_text, active, validity, validity_error_text, no_work_until, no_work_until_reason )
                
                self._SetDirty()
                
                raise HydrusExceptions.ValidationException( validity_error_text )
                
            
            try:
                
                login_script.CheckCanLogin( credentials )
                
            except HydrusExceptions.ValidationException as e:
                
                validity = VALIDITY_INVALID
                validity_error_text = str( e )
                
                self._domains_to_login_info[ login_domain ] = ( login_script_key_and_name, credentials, login_access_type, login_access_text, active, validity, validity_error_text, no_work_until, no_work_until_reason )
                
                self._SetDirty()
                
                raise
                
            
            if validity == VALIDITY_UNTESTED and validity_error_text != '':
                
                # cleaning up the 'restart dialog to test validity in cases where it is valid
                
                validity_error_text = ''
                
                self._domains_to_login_info[ login_domain ] = ( login_script_key_and_name, credentials, login_access_type, login_access_text, active, validity, validity_error_text, no_work_until, no_work_until_reason )
                
            
            return ( login_script, credentials )
            
        else:
            
            raise HydrusExceptions.ValidationException( 'Could not find any login entry for "' + login_domain + '"!' )
            
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_login_scripts = self._login_scripts.GetSerialisableTuple()
        
        serialisable_domains_to_login_info = {}
        
        for ( login_domain, ( login_script_key_and_name, credentials, login_access_type, login_access_text, active, validity, validity_error_text, no_work_until, no_work_until_reason ) ) in list(self._domains_to_login_info.items()):
            
            ( login_script_key, login_script_name ) = login_script_key_and_name
            
            serialisable_login_script_key_and_name = ( login_script_key.hex(), login_script_name )
            
            serialisable_domains_to_login_info[ login_domain ] = ( serialisable_login_script_key_and_name, credentials, login_access_type, login_access_text, active, validity, validity_error_text, no_work_until, no_work_until_reason )
            
        
        return ( serialisable_login_scripts, serialisable_domains_to_login_info )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_login_scripts, serialisable_domains_to_login_info ) = serialisable_info
        
        self._login_scripts = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_login_scripts )
        
        self._domains_to_login_info = {}
        
        for ( login_domain, ( serialisable_login_script_key_and_name, credentials, login_access_type, login_access_text, active, validity, validity_error_text, no_work_until, no_work_until_reason ) ) in list(serialisable_domains_to_login_info.items()):
            
            ( serialisable_login_script_key, login_script_name ) = serialisable_login_script_key_and_name
            
            login_script_key_and_name = ( bytes.fromhex( serialisable_login_script_key ), login_script_name )
            
            self._domains_to_login_info[ login_domain ] = ( login_script_key_and_name, credentials, login_access_type, login_access_text, active, validity, validity_error_text, no_work_until, no_work_until_reason )
            
        
    
    def _RecalcCache( self ):
        
        self._login_script_keys_to_login_scripts = { login_script.GetLoginScriptKey() : login_script for login_script in self._login_scripts }
        self._login_script_names_to_login_scripts = { login_script.GetName() : login_script for login_script in self._login_scripts }
        
        self._RevalidateCache()
        
    
    def _RevalidateCache( self ):
        
        for login_domain in list(self._domains_to_login_info.keys()):
            
            try:
                
                self._GetLoginScriptAndCredentials( login_domain )
                
            except HydrusExceptions.ValidationException:
                
                pass
                
            
        
    
    def _SetDirty( self ):
        
        self._dirty = True
        
    
    def AlreadyHaveExactlyThisLoginScript( self, new_login_script ):
        
        with self._lock:
            
            # absent irrelevant variables, do we have the exact same object already in?
            
            login_script_key_and_name = new_login_script.GetLoginScriptKeyAndName()
            
            dupe_login_scripts = [ login_script.Duplicate() for login_script in self._login_scripts ]
            
            for dupe_login_script in dupe_login_scripts:
                
                dupe_login_script.SetLoginScriptKeyAndName( login_script_key_and_name )
                
                if dupe_login_script.DumpToString() == new_login_script.DumpToString():
                    
                    return True
                    
                
            
        
        return False
        
    
    def AutoAddLoginScripts( self, login_scripts ):
        
        with self._lock:
            
            next_login_scripts = list( self._login_scripts )
            
            for login_script in login_scripts:
                
                login_script.RegenerateLoginScriptKey()
                
            
            next_login_scripts.extend( login_scripts )
            
        
        self.SetLoginScripts( next_login_scripts )
        
    
    def CheckCanLogin( self, network_context ):
        
        with self._lock:
            
            if network_context.context_type == CC.NETWORK_CONTEXT_DOMAIN:
                
                ( login_domain, login_expected, login_possible, login_error_text ) = self._GetLoginDomainStatus( network_context )
                
                if login_domain is None or not login_expected:
                    
                    raise HydrusExceptions.ValidationException( f'The domain "{login_domain}" has no active login script--has it just been turned off?' )
                    
                elif not login_possible:
                    
                    raise HydrusExceptions.ValidationException( f'The domain "{login_domain}" cannot log in: {login_error_text}' )
                    
                
            elif network_context.context_type == CC.NETWORK_CONTEXT_HYDRUS:
                
                service_key = network_context.context_data
                
                services_manager = self.engine.controller.services_manager
                
                if not services_manager.ServiceExists( service_key ):
                    
                    raise HydrusExceptions.ValidationException( 'Service does not exist!' )
                    
                
                service = services_manager.GetService( service_key )
                
                try:
                    
                    service.CheckFunctional( including_bandwidth = False, including_account = False )
                    
                except Exception as e:
                    
                    message = 'Service has had a recent error or is otherwise not functional! You might like to try refreshing its account in \'review services\'. Specific error was: {}'.format( e )
                    
                    raise HydrusExceptions.ValidationException( message )
                    
                
            
        
    
    def CurrentlyNeedsLogin( self, network_context ):
        
        with self._lock:
            
            if self._current_login_process is not None and self._current_login_process.network_context == network_context:
                
                # this network context is currently being logged in, so yes, we still need to wait for that to finish
                
                return True
                
            
            if network_context.context_type == CC.NETWORK_CONTEXT_DOMAIN:
                
                ( login_domain, login_expected, login_possible, login_error_text ) = self._GetLoginDomainStatus( network_context )
                
                if login_domain is None or not login_expected:
                    
                    return False # no login required, no problem
                    
                else:
                    
                    try:
                        
                        ( login_script, credentials ) = self._GetLoginScriptAndCredentials( login_domain )
                        
                    except HydrusExceptions.ValidationException:
                        
                        # couldn't find the script or something. assume we need a login to move errors forward to checkcanlogin trigger phase
                        
                        return True
                        
                    
                    login_network_context = ClientNetworkingContexts.NetworkContext( context_type = CC.NETWORK_CONTEXT_DOMAIN, context_data = login_domain )
                    
                    return not login_script.IsLoggedIn( self.engine, login_network_context )
                    
                
            elif network_context.context_type == CC.NETWORK_CONTEXT_HYDRUS:
                
                return not self._hydrus_login_script.IsLoggedIn( self.engine, network_context )
                
            
        
    
    def DelayLoginScript( self, login_domain, login_script_key, reason ):
        
        with self._lock:
            
            if login_domain not in self._domains_to_login_info:
                
                return
                
            
            ( login_script_key_and_name, credentials, login_access_type, login_access_text, active, validity, validity_error_text, no_work_until, no_work_until_reason ) = self._domains_to_login_info[ login_domain ]
            
            if login_script_key != login_script_key_and_name[0]:
                
                return
                
            
            no_work_until = HydrusTime.GetNow() + 3600 * 4
            no_work_until_reason = reason
            
            self._domains_to_login_info[ login_domain ] = ( login_script_key_and_name, credentials, login_access_type, login_access_text, active, validity, validity_error_text, no_work_until, no_work_until_reason )
            
            self._SetDirty()
            
        
    
    def DeleteLoginDomain( self, login_domain ):
        
        with self._lock:
            
            if login_domain in self._domains_to_login_info:
                
                del self._domains_to_login_info[ login_domain ]
                
                self._RecalcCache()
                
                self._SetDirty()
                
            
        
    
    def DeleteLoginScripts( self, login_script_names ):
        
        with self._lock:
            
            login_scripts = [ login_script for login_script in self._login_scripts if login_script.GetName() not in login_script_names ]
            
        
        self.SetLoginScripts( login_scripts )
        
    
    def DomainHasALoginScript( self, login_domain ):
        
        with self._lock:
            
            if login_domain in self._domains_to_login_info:
                
                ( login_script_key_and_name, credentials, login_access_type, login_access_text, active, validity, validity_error_text, no_work_until, no_work_until_reason ) = self._domains_to_login_info[ login_domain ]
                
                ( login_script_key, login_script_name ) = login_script_key_and_name
                
                if login_script_key in self._login_script_keys_to_login_scripts or login_script_name in self._login_script_names_to_login_scripts:
                    
                    return True
                    
                
            
            return False
            
        
    
    def GenerateLoginProcess( self, network_context ):
        
        with self._lock:
            
            if network_context.context_type == CC.NETWORK_CONTEXT_DOMAIN:
                
                ( login_domain, login_expected, login_possible, login_error_text ) = self._GetLoginDomainStatus( network_context )
                
                if login_domain is None or not login_expected:
                    
                    raise HydrusExceptions.ValidationException( 'The domain ' + login_domain + ' has no active login script--has it just been turned off?' )
                    
                elif not login_possible:
                    
                    raise HydrusExceptions.ValidationException( 'The domain ' + login_domain + ' cannot log in: ' + login_error_text )
                    
                else:
                    
                    login_network_context = ClientNetworkingContexts.NetworkContext( context_type = CC.NETWORK_CONTEXT_DOMAIN, context_data = login_domain )
                    
                    ( login_script, credentials ) = self._GetLoginScriptAndCredentials( login_domain )
                    
                    login_process = LoginProcessDomain( self.engine, login_network_context, login_script, credentials )
                    
                    return login_process
                    
                
            elif network_context.context_type == CC.NETWORK_CONTEXT_HYDRUS:
                
                login_process = LoginProcessHydrus( self.engine, network_context, self._hydrus_login_script )
                
                return login_process
                
            
        
    
    def GenerateLoginProcessForDomain( self, login_domain ):
        
        network_context = ClientNetworkingContexts.NetworkContext.STATICGenerateForDomain( login_domain )
        
        return self.GenerateLoginProcess( network_context )
        
    
    def GetDomainsToLoginInfo( self ):
        
        with self._lock:
            
            self._RevalidateCache()
            
            return dict( self._domains_to_login_info )
            
        
    
    def GetLoginScripts( self ):
        
        with self._lock:
            
            return list( self._login_scripts )
            
        
    
    def Initialise( self ):
        
        self._RecalcCache()
        
    
    def InvalidateLoginScript( self, login_domain, login_script_key, reason ):
        
        with self._lock:
            
            if login_domain not in self._domains_to_login_info:
                
                return
                
            
            ( login_script_key_and_name, credentials, login_access_type, login_access_text, active, validity, validity_error_text, no_work_until, no_work_until_reason ) = self._domains_to_login_info[ login_domain ]
            
            if login_script_key != login_script_key_and_name[0]:
                
                return
                
            
            validity = VALIDITY_INVALID
            validity_error_text = reason
            
            self._domains_to_login_info[ login_domain ] = ( login_script_key_and_name, credentials, login_access_type, login_access_text, active, validity, validity_error_text, no_work_until, no_work_until_reason )
            
            HydrusData.ShowText( 'The login for "' + login_domain + '" failed! It will not be reattempted until the problem is fixed. The failure reason was:' + '\n' * 2 + validity_error_text )
            
            self._SetDirty()
            
        
    
    def IsDirty( self ):
        
        with self._lock:
            
            return self._dirty
            
        
    
    def OverwriteDefaultLoginScripts( self, login_script_names ):
        
        with self._lock:
            
            from hydrus.client import ClientDefaults
            
            default_login_scripts = ClientDefaults.GetDefaultLoginScripts()
            
            for login_script in default_login_scripts:
                
                login_script.RegenerateLoginScriptKey()
                
            
            existing_login_scripts = list( self._login_scripts )
            
            new_login_scripts = [ login_script for login_script in existing_login_scripts if login_script.GetName() not in login_script_names ]
            new_login_scripts.extend( [ login_script for login_script in default_login_scripts if login_script.GetName() in login_script_names ] )
            
        
        self.SetLoginScripts( new_login_scripts, auto_link_these_names = login_script_names )
        
    
    def SetActive( self, login_domain, name, new_active ):
        
        # used for hacky db updates
        
        with self._lock:
            
            if login_domain not in self._domains_to_login_info:
                
                return
                
            
            ( login_script_key_and_name, credentials, login_access_type, login_access_text, active, validity, validity_error_text, no_work_until, no_work_until_reason ) = self._domains_to_login_info[ login_domain ]
            
            if login_script_key_and_name[1] == name:
                
                active = new_active
                
                self._domains_to_login_info[ login_domain ] = ( login_script_key_and_name, credentials, login_access_type, login_access_text, active, validity, validity_error_text, no_work_until, no_work_until_reason )
                
                self._SetDirty()
                
            
        
    
    def SetClean( self ):
        
        with self._lock:
            
            self._dirty = False
            
        
    
    def SetCredentialsAndActivate( self, login_domain, new_credentials ):
        
        with self._lock:
            
            if login_domain not in self._domains_to_login_info:
                
                return
                
            
            ( login_script_key_and_name, credentials, login_access_type, login_access_text, active, validity, validity_error_text, no_work_until, no_work_until_reason ) = self._domains_to_login_info[ login_domain ]
            
            credentials = new_credentials
            active = True
            
            validity = VALIDITY_UNTESTED
            validity_error_text = ''
            
            self._domains_to_login_info[ login_domain ] = ( login_script_key_and_name, credentials, login_access_type, login_access_text, active, validity, validity_error_text, no_work_until, no_work_until_reason )
            
            self._SetDirty()
            
        
    
    def SetCurrentLoginProcess( self, login_process: "LoginProcess | None" ):
        
        self._current_login_process = login_process
        
    
    def SetDomainsToLoginInfo( self, domains_to_login_info ):
        
        with self._lock:
            
            self._domains_to_login_info = dict( domains_to_login_info )
            
            self._RecalcCache()
            
            self._SetDirty()
            
        
    
    def SetLoginScripts( self, login_scripts, auto_link = False, auto_link_these_names = None ):
        
        if auto_link_these_names is None:
            
            auto_link_these_names = set()
            
        
        with self._lock:
            
            self._login_scripts = HydrusSerialisable.SerialisableList( login_scripts )
            
            # start with simple stuff first
            self._login_scripts.sort( key = lambda ls: len( ls.GetCredentialDefinitions() ) )
            
            for login_script in self._login_scripts:
                
                login_script_key_and_name = login_script.GetLoginScriptKeyAndName()
                
                example_domains_info = login_script.GetExampleDomainsInfo()
                
                for ( login_domain, login_access_type, login_access_text ) in example_domains_info:
                    
                    if '.' in login_domain:
                        
                        # looks good, so let's see if we can update/add some info
                        
                        if login_domain in self._domains_to_login_info:
                            
                            ( old_login_script_key_and_name, credentials, old_login_access_type, old_login_access_text, active, validity, validity_error_text, no_work_until, no_work_until_reason ) = self._domains_to_login_info[ login_domain ]
                            
                            if old_login_script_key_and_name[1] == login_script_key_and_name[1]:
                                
                                # this is probably a newly overwritten script
                                if auto_link or login_script.GetName() in auto_link_these_names:
                                    
                                    if validity == VALIDITY_INVALID:
                                        
                                        validity = VALIDITY_UNTESTED
                                        validity_error_text = ''
                                        
                                        no_work_until = 0
                                        no_work_until_reason = ''
                                        
                                    
                                
                                self._domains_to_login_info[ login_domain ] = ( login_script_key_and_name, credentials, login_access_type, login_access_text, active, validity, validity_error_text, no_work_until, no_work_until_reason )
                                
                            
                        else:
                            
                            if auto_link or login_script.GetName() in auto_link_these_names:
                                
                                credentials = {}
                                
                                # if there is nothing to enter, turn it on by default, like HF click-through
                                active = len( login_script.GetCredentialDefinitions() ) == 0
                                
                                validity = VALIDITY_UNTESTED
                                validity_error_text = ''
                                
                                no_work_until = 0
                                no_work_until_reason = ''
                                
                                self._domains_to_login_info[ login_domain ] = ( login_script_key_and_name, credentials, login_access_type, login_access_text, active, validity, validity_error_text, no_work_until, no_work_until_reason )
                                
                            
                        
                    
                
            
            self._RecalcCache()
            
            self._SetDirty()
            
        
    
    def ValidateLoginScript( self, login_domain, login_script_key ):
        
        with self._lock:
            
            if login_domain not in self._domains_to_login_info:
                
                return
                
            
            ( login_script_key_and_name, credentials, login_access_type, login_access_text, active, validity, validity_error_text, no_work_until, no_work_until_reason ) = self._domains_to_login_info[ login_domain ]
            
            if login_script_key != login_script_key_and_name[0]:
                
                return
                
            
            validity = VALIDITY_VALID
            validity_error_text = ''
            
            self._domains_to_login_info[ login_domain ] = ( login_script_key_and_name, credentials, login_access_type, login_access_text, active, validity, validity_error_text, no_work_until, no_work_until_reason )
            
            self._SetDirty()
            
        
    
    def TryToLinkMissingLoginScripts( self, login_domains ):
        
        with self._lock:
            
            for login_domain in login_domains:
                
                try:
                    
                    ( existing_login_script, existing_credentials ) = self._GetLoginScriptAndCredentials( login_domain )
                    
                    continue # already seems to have a good login script, so nothing to fix
                    
                except HydrusExceptions.ValidationException:
                    
                    pass
                    
                
                ( login_script_key_and_name, credentials, login_access_type, login_access_text, active, validity, validity_error_text, no_work_until, no_work_until_reason ) = self._domains_to_login_info[ login_domain ]
                
                login_script = self._GetBestLoginScript( login_domain )
                
                if login_script is None:
                    
                    continue
                    
                
                validity = VALIDITY_UNTESTED
                validity_error_text = ''
                
                login_script_key_and_name = login_script.GetLoginScriptKeyAndName()
                
                self._domains_to_login_info[ login_domain ] = ( login_script_key_and_name, credentials, login_access_type, login_access_text, active, validity, validity_error_text, no_work_until, no_work_until_reason )
                
            
            self._SetDirty()
            
        
    
    def LoginTumblrGDPR( self ):
        
        # t-thanks, EU
        # this is cribbed from poking around here https://github.com/johanneszab/TumblThree/commit/3563d6cebf1a467151d6b8d6eee9806ddd6e6364
        
        network_job = ClientNetworkingJobs.NetworkJob( 'GET', 'https://www.tumblr.com/' )
        
        network_job.SetForLogin( True )
        
        self.engine.AddJob( network_job )
        
        network_job.WaitUntilDone()
        
        html = network_job.GetContentText()
        
        formula = ClientParsing.ParseFormulaHTML( tag_rules = [ ClientParsing.ParseRuleHTML( rule_type = ClientParsing.HTML_RULE_TYPE_DESCENDING, tag_name = 'meta', tag_attributes = { 'id' : 'tumblr_form_key' } ) ], content_to_fetch = ClientParsing.HTML_CONTENT_ATTRIBUTE, attribute_to_fetch = "content" )
        
        collapse_newlines = True
        
        results = formula.Parse( {}, html, collapse_newlines )
        
        if len( results ) != 1:
            
            raise HydrusExceptions.ParseException( 'Could not figure out the tumblr form key for the GDPR click-through.' )
            
        
        tumblr_form_key = results[0]
        
        #
        
        body = '{\"eu_resident\":true,\"gdpr_is_acceptable_age\":true,\"gdpr_consent_core\":true,\"gdpr_consent_first_party_ads\":true,\"gdpr_consent_third_party_ads\":true,\"gdpr_consent_search_history\":true,\"redirect_to\":\"\"}'
        referral_url = 'https://www.tumblr.com/privacy/consent?redirect='
        
        network_job = ClientNetworkingJobs.NetworkJob( 'POST', 'https://www.tumblr.com/svc/privacy/consent', body = body, referral_url = referral_url )
        
        network_job.SetForLogin( True )
        
        network_job.AddAdditionalHeader( 'Accept', 'application/json, text/javascript, */*; q=0.01')
        network_job.AddAdditionalHeader( 'Content-Type', 'application/json' )
        network_job.AddAdditionalHeader( 'X-Requested-With', 'XMLHttpRequest' )
        network_job.AddAdditionalHeader( 'X-tumblr-form-key', tumblr_form_key )
        
        self.engine.AddJob( network_job )
        
        network_job.WaitUntilDone()
        
        # test cookies here or something
        
        HydrusData.ShowText( 'Looks like tumblr GDPR click-through worked! You should be good for a year, at which point we should have an automatic solution for this!' )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_LOGIN_MANAGER ] = NetworkLoginManager

CREDENTIAL_TYPE_TEXT = 0
CREDENTIAL_TYPE_PASS = 1

credential_type_str_lookup = {}

credential_type_str_lookup[ CREDENTIAL_TYPE_TEXT ] = 'normal'
credential_type_str_lookup[ CREDENTIAL_TYPE_PASS ] = 'hidden (password)'

class LoginCredentialDefinition( HydrusSerialisable.SerialisableBaseNamed ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_LOGIN_CREDENTIAL_DEFINITION
    SERIALISABLE_NAME = 'Login Credential Definition'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, name = 'username', credential_type = CREDENTIAL_TYPE_TEXT, string_match = None ):
        
        if string_match is None:
            
            string_match = ClientStrings.StringMatch()
            
        
        super().__init__( name )
        
        self._credential_type = credential_type
        self._string_match = string_match
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_string_match = self._string_match.GetSerialisableTuple()
        
        return ( self._credential_type, serialisable_string_match )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._credential_type, serialisable_string_match ) = serialisable_info
        
        self._string_match = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_string_match )
        
    
    def GetStringMatch( self ):
        
        return self._string_match
        
    
    def GetType( self ):
        
        return self._credential_type
        
    
    def SetStringMatch( self, string_match ):
        
        self._string_match = string_match
        
    
    def SetType( self, credential_type ):
        
        self._credential_type = credential_type
        
    
    def ShouldHide( self ):
        
        return self._credential_type == CREDENTIAL_TYPE_PASS
        
    
    def Test( self, text ):
        
        if self._string_match is not None:
            
            try:
                
                self._string_match.Test( text )
                
            except HydrusExceptions.StringMatchException as e:
                
                raise HydrusExceptions.ValidationException( 'Could not validate "' + self._name + '" credential: ' + str( e ) )
                
            
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_LOGIN_CREDENTIAL_DEFINITION ] = LoginCredentialDefinition

class LoginProcess( object ):
    
    def __init__( self, engine, network_context, login_script ):
        
        self.engine = engine
        self.network_context = network_context
        self.login_script = login_script
        
        self._done = False
        
    
    def _Start( self ):
        
        raise NotImplementedError()
        
    
    def GetNetworkContext( self ):
        
        return self.network_context
        
    
    def IsDone( self ):
        
        return self._done
        
    
    def Start( self ):
        
        try:
            
            self._Start()
            
        finally:
            
            self._done = True
            
        
    
class LoginProcessDomain( LoginProcess ):
    
    def __init__( self, engine, network_context, login_script, credentials ):
        
        super().__init__( engine, network_context, login_script )
        
        self.credentials = credentials
        
    
    def _Start( self ):
        
        login_domain = self.network_context.context_data
        
        job_status = ClientThreading.JobStatus( cancellable = True )
        
        job_status.SetStatusTitle( 'Logging in ' + login_domain )
        
        CG.client_controller.pub( 'message', job_status )
        
        HydrusData.Print( 'Starting login for ' + login_domain )
        
        result = self.login_script.Start( self.engine, self.network_context, self.credentials, job_status = job_status )
        
        HydrusData.Print( 'Finished login for ' + self.network_context.context_data + '. Result was: ' + result )
        
        job_status.SetStatusText( result )
        
        job_status.FinishAndDismiss( 4 )
        
    
class LoginProcessHydrus( LoginProcess ):
    
    def _Start( self ):
        
        self.login_script.Start( self.engine, self.network_context )
        
    
class LoginScriptHydrus( object ):
    
    def _IsLoggedIn( self, engine, network_context ):
        
        session = engine.session_manager.GetSession( network_context )
        
        cookies = session.cookies
        
        cookies.clear_expired_cookies()
        
        return 'session_key' in cookies
        
    
    def IsLoggedIn( self, engine, network_context ):
        
        return self._IsLoggedIn( engine, network_context )
        
    
    def Start( self, engine, network_context ):
        
        service_key = network_context.context_data
        
        try:
            
            service = engine.controller.services_manager.GetService( service_key )
            
        except HydrusExceptions.DataMissing:
            
            return
            
        
        base_url = service.GetBaseURL()
        
        url = base_url + 'session_key'
        
        access_key = service.GetCredentials().GetAccessKey()
        
        network_job = ClientNetworkingJobs.NetworkJobHydrus( service_key, 'GET', url )
        
        network_job.SetForLogin( True )
        
        network_job.OnlyTryConnectionOnce()
        
        network_job.AddAdditionalHeader( 'Hydrus-Key', access_key.hex() )
        
        engine.AddJob( network_job )
        
        try:
            
            network_job.WaitUntilDone()
            
            if self._IsLoggedIn( engine, network_context ):
                
                HydrusData.Print( 'Successfully logged into ' + service.GetName() + '.' )
                
            elif service.IsFunctional():
                
                ( is_ok, status_string ) = service.GetStatusInfo()
                
                service.DelayFutureRequests( 'Could not log in for unknown reason. Current service status: {}'.format( status_string ) )
                
            
        except Exception as e:
            
            e_string = str( e )
            
            service.DelayFutureRequests( e_string )
            
        
    
class LoginScriptDomain( HydrusSerialisable.SerialisableBaseNamed ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_LOGIN_SCRIPT_DOMAIN
    SERIALISABLE_NAME = 'Login Script - Domain'
    SERIALISABLE_VERSION = 2
    
    def __init__( self, name = 'login script', login_script_key = None, required_cookies_info = None, credential_definitions = None, login_steps = None, example_domains_info = None ):
        
        if required_cookies_info is None:
            
            required_cookies_info = {}
            
        
        required_cookies_info = HydrusSerialisable.SerialisableDictionary( required_cookies_info )
        
        if credential_definitions is None:
            
            credential_definitions = []
            
        
        credential_definitions = HydrusSerialisable.SerialisableList( credential_definitions )
        
        if login_steps is None:
            
            login_steps = []
            
        
        login_steps = HydrusSerialisable.SerialisableList( login_steps )
        
        if example_domains_info is None:
            
            example_domains_info = []
            
        
        super().__init__( name )
        
        self._login_script_key = HydrusData.GenerateKey()
        self._required_cookies_info = required_cookies_info # string match : string match
        self._credential_definitions = credential_definitions
        self._login_steps = login_steps
        self._example_domains_info = example_domains_info # domain | login_access_type | login_access_text
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_login_script_key = self._login_script_key.hex()
        serialisable_required_cookies = self._required_cookies_info.GetSerialisableTuple()
        serialisable_credential_definitions = self._credential_definitions.GetSerialisableTuple()
        serialisable_login_steps = self._login_steps.GetSerialisableTuple()
        
        return ( serialisable_login_script_key, serialisable_required_cookies, serialisable_credential_definitions, serialisable_login_steps, self._example_domains_info )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_login_script_key, serialisable_required_cookies, serialisable_credential_definitions, serialisable_login_steps, self._example_domains_info ) = serialisable_info
        
        self._login_script_key = bytes.fromhex( serialisable_login_script_key )
        self._required_cookies_info = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_required_cookies )
        self._credential_definitions = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_credential_definitions )
        self._login_steps = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_login_steps )
        
        # convert lists to tups for listctrl data hashing
        self._example_domains_info = [ tuple( list_of_info ) for list_of_info in self._example_domains_info ]
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( serialisable_login_script_key, serialisable_required_cookies, serialisable_credential_definitions, serialisable_login_steps, example_domains_info ) = old_serialisable_info
            
            old_required_cookies_info = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_required_cookies )
            new_required_cookies_info = HydrusSerialisable.SerialisableDictionary()
            
            for ( name, value_string_match ) in list(old_required_cookies_info.items()):
                
                key_string_match = ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FIXED, match_value = name, example_string = name )
                
                new_required_cookies_info[ key_string_match ] = value_string_match
                
            
            serialisable_required_cookies = new_required_cookies_info.GetSerialisableTuple()
            
            new_serialisable_info = ( serialisable_login_script_key, serialisable_required_cookies, serialisable_credential_definitions, serialisable_login_steps, example_domains_info )
            
            return ( 2, new_serialisable_info )
            
        
    
    def _IsLoggedIn( self, engine, network_context, validation_check = False ):
        
        session = engine.session_manager.GetSession( network_context )
        
        cookies = session.cookies
        
        search_domain = network_context.context_data
        
        for ( cookie_name_string_match, value_string_match ) in self._required_cookies_info.items():
            
            try:
                
                cookie = ClientNetworkingFunctions.GetCookie( cookies, search_domain, cookie_name_string_match )
                
            except HydrusExceptions.DataMissing as e:
                
                if validation_check:
                    
                    raise HydrusExceptions.ValidationException( 'Missing cookie "' + cookie_name_string_match.ToString() + '"!' )
                    
                
                return False
                
            
            cookie_text = cookie.value
            
            try:
                
                value_string_match.Test( cookie_text )
                
            except HydrusExceptions.StringMatchException as e:
                
                if validation_check:
                    
                    raise HydrusExceptions.ValidationException( 'Cookie "' + cookie_name_string_match.ToString() + '" failed: ' + str( e ) + '!' )
                    
                
                return False
                
            
        
        return True
        
    
    def CheckCanLogin( self, given_credentials ):
        
        self.CheckIsValid()
        
        given_cred_names = set( given_credentials.keys() )
        required_cred_names = { name for name in itertools.chain.from_iterable( ( step.GetRequiredCredentials() for step in self._login_steps ) ) }
        
        missing_givens = required_cred_names.difference( given_cred_names )
        
        if len( missing_givens ) > 0:
            
            missing_givens = sorted( missing_givens )
            
            raise HydrusExceptions.ValidationException( 'Missing required credentials: ' + ', '.join( missing_givens ) )
            
        
        #
        
        cred_names_to_definitions = { credential_definition.GetName() : credential_definition for credential_definition in self._credential_definitions }
        
        for ( pretty_name, text ) in given_credentials.items():
            
            if pretty_name not in cred_names_to_definitions:
                
                continue
                
            
            credential_definition = cred_names_to_definitions[ pretty_name ]
            
            credential_definition.Test( text )
            
        
    
    def CheckIsValid( self ):
        
        defined_cred_names = { credential_definition.GetName() for credential_definition in self._credential_definitions }
        required_cred_names = { name for name in itertools.chain.from_iterable( ( step.GetRequiredCredentials() for step in self._login_steps ) ) }
        
        missing_definitions = required_cred_names.difference( defined_cred_names )
        
        if len( missing_definitions ) > 0:
            
            missing_definitions = sorted( missing_definitions )
            
            raise HydrusExceptions.ValidationException( 'Missing required credential definitions: ' + ', '.join( missing_definitions ) )
            
        
        #
        
        temp_vars = set()
        
        for login_step in self._login_steps:
            
            ( required_vars, set_vars ) = login_step.GetRequiredAndSetTempVariables()
            
            missing_vars = required_vars.difference( temp_vars )
            
            if len( missing_vars ) > 0:
                
                missing_vars = sorted( missing_vars )
                
                raise HydrusExceptions.ValidationException( 'Missing temp variables for login step "' + login_step.GetName() + '": ' + ', '.join( missing_vars ) )
                
            
            temp_vars.update( set_vars )
            
        
    
    def GetCredentialDefinitions( self ):
        
        return self._credential_definitions
        
    
    def GetExampleDomains( self ):
        
        return [ domain for ( domain, login_access_type, login_access_text ) in self._example_domains_info ]
        
    
    def GetExampleDomainsInfo( self ):
        
        return self._example_domains_info
        
    
    def GetExampleDomainInfo( self, given_domain ):
        
        for ( domain, login_access_type, login_access_text ) in self._example_domains_info:
            
            if domain == given_domain:
                
                return ( login_access_type, login_access_text )
                
            
        
        raise HydrusExceptions.DataMissing( 'Could not find that domain!' )
        
    
    def GetRequiredCookiesInfo( self ):
        
        return self._required_cookies_info
        
    
    def GetLoginExpiry( self, engine, network_context ):
        
        session = engine.session_manager.GetSession( network_context )
        
        cookies = session.cookies
        
        cookies.clear_expired_cookies()
        
        search_domain = network_context.context_data
        
        session_cookies = False
        expiry_timestamps = []
        
        for cookie_name_string_match in list(self._required_cookies_info.keys()):
            
            try:
                
                cookie = ClientNetworkingFunctions.GetCookie( cookies, search_domain, cookie_name_string_match )
                
            except HydrusExceptions.DataMissing as e:
                
                return None
                
            
            expiry = cookie.expires
            
            if expiry is None:
                
                session_cookies = True
                
            else:
                
                expiry_timestamps.append( expiry )
                
            
        
        if session_cookies or len( expiry_timestamps ) == 0:
            
            return None
            
        else:
            
            return min( expiry_timestamps )
            
        
    
    def GetLoginScriptKey( self ):
        
        return self._login_script_key
        
    
    def GetLoginScriptKeyAndName( self ):
        
        return ( self._login_script_key, self._name )
        
    
    def GetLoginSteps( self ):
        
        return self._login_steps
        
    
    def GetRequiredCredentials( self ):
        
        required_creds = []
        
        for login_step in self._login_steps:
            
            required_creds.extend( login_step.GetRequiredCredentials() ) # name with an order
            
        
        return required_creds
        
    
    def GetSafeSummary( self ):
        
        return 'Login Script "' + self._name + '" - ' + ', '.join( self.GetExampleDomains() )
        
    
    def IsLoggedIn( self, engine, network_context ):
        
        return self._IsLoggedIn( engine, network_context )
        
    
    def RegenerateLoginScriptKey( self ):
        
        self._login_script_key = HydrusData.GenerateKey()
        
    
    def SetLoginScriptKey( self, login_script_key ):
        
        self._login_script_key = login_script_key
        
    
    def SetLoginScriptKeyAndName( self, login_script_key_and_name ):
        
        ( login_script_key, name ) = login_script_key_and_name
        
        self._login_script_key = login_script_key
        self._name = name
        
    
    def Start( self, engine, network_context, given_credentials, network_job_presentation_context_factory = None, test_result_callable = None, job_status = None ):
        
        # don't mess with the domain--assume that we are given precisely the right domain
        
        login_domain = network_context.context_data
        
        temp_variables = {}
        
        last_url_used = None
        
        for login_step in self._login_steps:
            
            if job_status is not None:
                
                if job_status.IsCancelled():
                    
                    message = 'User cancelled the login process.'
                    
                    engine.login_manager.DelayLoginScript( login_domain, self._login_script_key, message )
                    
                    return message
                    
                
                job_status.SetStatusText( login_step.GetName() )
                
            
            try:
                
                last_url_used = login_step.Start( engine, login_domain, given_credentials, temp_variables, referral_url = last_url_used, network_job_presentation_context_factory = network_job_presentation_context_factory, test_result_callable = test_result_callable )
                
            except HydrusExceptions.ValidationException as e:
                
                if test_result_callable is not None:
                    
                    HydrusData.ShowException( e )
                    
                
                message = str( e )
                
                engine.login_manager.InvalidateLoginScript( login_domain, self._login_script_key, message )
                
                return 'Verification error: ' + message
                
            except HydrusExceptions.NetworkException as e:
                
                if test_result_callable is not None:
                    
                    HydrusData.ShowException( e )
                    
                
                if isinstance( e, HydrusExceptions.InsufficientCredentialsException ):
                    
                    message = '403 - login script or credentials may be invalid'
                    
                elif isinstance( e, HydrusExceptions.MissingCredentialsException ):
                    
                    message = '401 - login script or credentials may be invalid'
                    
                else:
                    
                    message = HydrusText.GetFirstLine( str( e ) )
                    
                
                engine.login_manager.DelayLoginScript( login_domain, self._login_script_key, message )
                
                return 'Network error: ' + message
                
            except Exception as e:
                
                if test_result_callable is not None:
                    
                    HydrusData.ShowException( e )
                    
                
                message = str( e )
                
                engine.login_manager.InvalidateLoginScript( login_domain, self._login_script_key, message )
                
                return 'Unusual error: ' + message
                
            
            time.sleep( 2 )
            
        
        try:
            
            self._IsLoggedIn( engine, network_context, validation_check = True )
            
        except Exception as e:
            
            if test_result_callable is not None:
                
                HydrusData.ShowException( e )
                
            
            message = str( e )
            
            engine.login_manager.InvalidateLoginScript( login_domain, self._login_script_key, message )
            
            return 'Final cookie check failed: ' + message
            
        
        engine.login_manager.ValidateLoginScript( login_domain, self._login_script_key )
        
        return 'Login OK!'
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_LOGIN_SCRIPT_DOMAIN ] = LoginScriptDomain

LOGIN_PARAMETER_TYPE_PARAMETER = 0
LOGIN_PARAMETER_TYPE_COOKIE = 1
LOGIN_PARAMETER_TYPE_HEADER = 2

class LoginStep( HydrusSerialisable.SerialisableBaseNamed ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_LOGIN_STEP
    SERIALISABLE_NAME = 'Login Step'
    SERIALISABLE_VERSION = 2
    
    def __init__( self, name = 'hit home page to establish session', scheme = 'https', method = 'GET', subdomain = None, path = '/' ):
        
        super().__init__( name )
        
        self._scheme = scheme
        self._method = method
        self._subdomain = subdomain
        self._path = path
        
        self._CleanseSubdomainAndPath()
        
        self._required_credentials = {} # pretty_name : arg name
        
        self._static_args = {} # arg name : string
        
        self._temp_args = {} # temp arg name : arg name
        
        self._required_cookies_info = HydrusSerialisable.SerialisableDictionary() # string match : string match
        
        self._content_parsers = HydrusSerialisable.SerialisableList()
        
    
    def _CleanseSubdomainAndPath( self ):
        
        if self._subdomain is not None:
            
            self._subdomain = re.sub( '[^a-z.]+', '', self._subdomain )
            
        
        if not self._path.startswith( '/' ):
            
            self._path = '/' + self._path
            
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_required_cookies = self._required_cookies_info.GetSerialisableTuple()
        serialisable_content_parsers = self._content_parsers.GetSerialisableTuple()
        
        return ( self._scheme, self._method, self._subdomain, self._path, self._required_credentials, self._static_args, self._temp_args, serialisable_required_cookies, serialisable_content_parsers )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._scheme, self._method, self._subdomain, self._path, self._required_credentials, self._static_args, self._temp_args, serialisable_required_cookies, serialisable_content_parsers ) = serialisable_info
        
        self._CleanseSubdomainAndPath()
        
        self._required_cookies_info = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_required_cookies )
        self._content_parsers = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_content_parsers )
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( scheme, method, subdomain, path, required_credentials, static_args, temp_args, serialisable_required_cookies, serialisable_content_parsers ) = old_serialisable_info
            
            old_required_cookies_info = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_required_cookies )
            new_required_cookies_info = HydrusSerialisable.SerialisableDictionary()
            
            for ( name, value_string_match ) in list(old_required_cookies_info.items()):
                
                key_string_match = ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FIXED, match_value = name, example_string = name )
                
                new_required_cookies_info[ key_string_match ] = value_string_match
                
            
            serialisable_required_cookies = new_required_cookies_info.GetSerialisableTuple()
            
            new_serialisable_info = ( scheme, method, subdomain, path, required_credentials, static_args, temp_args, serialisable_required_cookies, serialisable_content_parsers )
            
            return ( 2, new_serialisable_info )
            
        
    
    def GetRequiredCredentials( self ):
        
        return [ pretty_name for ( pretty_name, arg_name ) in list(self._required_credentials.items()) ]
        
    
    def GetRequiredAndSetTempVariables( self ):
        
        required_temp_variables = set( self._temp_args.keys() )
        
        set_temp_variables = { parsable_content_description.temp_variable_name for parsable_content_description in [ content_parser.GetParsableContentDescription() for content_parser in self._content_parsers ] if isinstance( parsable_content_description, ClientParsingResults.ParsableContentDescriptionVariable ) }
        
        return ( required_temp_variables, set_temp_variables )
        
    
    def SetComplicatedVariables( self, required_credentials, static_args, temp_args, required_cookies_info, content_parsers ):
        
        self._required_credentials = required_credentials
        
        self._static_args = static_args
        
        self._temp_args = temp_args
        
        self._required_cookies_info = HydrusSerialisable.SerialisableDictionary( required_cookies_info )
        
        self._content_parsers = HydrusSerialisable.SerialisableList( content_parsers )
        
    
    def Start( self, engine, domain, given_credentials, temp_variables, referral_url = None, network_job_presentation_context_factory = None, test_result_callable = None ):
        
        def session_to_cookie_strings( sess ):
            
            cookie_strings = set()
            
            for cookie in sess.cookies:
                
                s = cookie.name + ': ' + cookie.value + ' | ' + cookie.domain + ' | '
                
                expiry = cookie.expires
                
                if expiry is None:
                    
                    expiry = -1
                    pretty_expiry = 'session'
                    
                else:
                    
                    pretty_expiry = HydrusTime.TimestampToPrettyExpires( expiry )
                    
                
                s += pretty_expiry
                
                cookie_strings.add( s )
                
            
            return cookie_strings
            
        
        url = 'Did not make a url.'
        test_result_body = None
        downloaded_text = 'Did not download data.'
        new_temp_variables = {}
        original_cookie_strings = session_to_cookie_strings( engine.session_manager.GetSessionForDomain( domain ) )
        test_script_result = 'Did not start.'
        
        try:
            
            domain_to_hit = domain
            
            if self._subdomain is not None:
                
                if domain.startswith( 'www.' ):
                    
                    domain = domain[4:]
                    
                
                domain_to_hit = self._subdomain + '.' + domain
                
            
            query_dict = {}
            
            query_dict.update( self._static_args )
            
            for ( pretty_name, arg_name ) in list(self._required_credentials.items()):
                
                query_dict[ arg_name ] = given_credentials[ pretty_name ]
                
            
            for ( temp_name, arg_name ) in list(self._temp_args.items()):
                
                if temp_name not in temp_variables:
                    
                    raise HydrusExceptions.ValidationException( 'The temporary variable \'' + temp_name + '\' was not found!' )
                    
                
                query_dict[ arg_name ] = temp_variables[ temp_name ]
                
            
            scheme = self._scheme
            netloc = domain_to_hit
            path = self._path
            params = ''
            query = ''
            fragment = ''
            
            single_value_parameters = []
            
            if self._method == 'GET':
                
                query = ClientNetworkingFunctions.ConvertQueryDictToText( query_dict, single_value_parameters )
                body = None
                test_result_body = ''
                
            elif self._method == 'POST':
                
                query = ''
                body = query_dict
                test_result_body = ClientNetworkingFunctions.ConvertQueryDictToText( query_dict, single_value_parameters )
                
            
            url = urllib.parse.urlunparse( ( scheme, netloc, path, params, query, fragment ) )
            
            network_job = ClientNetworkingJobs.NetworkJob( self._method, url, body = body, referral_url = referral_url )
            
            if self._method == 'POST' and referral_url is not None:
                
                p = ClientNetworkingFunctions.ParseURL( url )
                
                origin = urllib.parse.urlunparse( ( p.scheme, p.netloc, '', '', '', '' ) ) # https://accounts.pixiv.net
                
                network_job.AddAdditionalHeader( 'origin', origin ) # GET/POST forms are supposed to have this for CSRF. we'll try it just with POST for now
                
            
            network_job.SetForLogin( True )
            
            engine.AddJob( network_job )
            
            if network_job_presentation_context_factory is not None:
                
                with network_job_presentation_context_factory( network_job ) as njpc:
                    
                    network_job.WaitUntilDone()
                    
                
            else:
                
                network_job.WaitUntilDone()
                
            
            session = network_job.GetSession()
            
            cookies = session.cookies
            
            for ( cookie_name_string_match, string_match ) in list(self._required_cookies_info.items()):
                
                try:
                    
                    cookie = ClientNetworkingFunctions.GetCookie( cookies, domain, cookie_name_string_match )
                    
                except HydrusExceptions.DataMissing as e:
                    
                    raise HydrusExceptions.ValidationException( 'Missing cookie "' + cookie_name_string_match.ToString() + '" on step "' + self._name + '"!' )
                    
                
                cookie_text = cookie.value
                
                try:
                    
                    string_match.Test( cookie_text )
                    
                except HydrusExceptions.StringMatchException as e:
                    
                    raise HydrusExceptions.ValidationException( 'Cookie "' + cookie_name_string_match.ToString() + '" failed on step "' + self._name + '": ' + str( e ) + '!' )
                    
                
            
            downloaded_text = network_job.GetContentText()
            
            parsing_context = {}
            
            parsing_context[ 'url' ] = url
            
            for content_parser in self._content_parsers:
                
                content_parser = typing.cast( ClientParsing.ContentParser, content_parser )
                
                try:
                    
                    parsed_post = content_parser.Parse( parsing_context, downloaded_text )
                    
                except HydrusExceptions.VetoException as e:
                    
                    raise HydrusExceptions.ValidationException( str( e ) )
                    
                
                result = parsed_post.GetVariable()
                
                if result is not None:
                    
                    ( temp_name, value ) = result
                    
                    new_temp_variables[ temp_name ] = value
                    
                
            
            temp_variables.update( new_temp_variables )
            
            test_script_result = 'OK!'
            
            return url
            
        except Exception as e:
            
            test_script_result = str( e )
            
            raise
            
        finally:
            
            if test_result_callable is not None:
                
                current_cookie_strings = session_to_cookie_strings( engine.session_manager.GetSessionForDomain( domain ) )
                
                new_cookie_strings = tuple( current_cookie_strings.difference( original_cookie_strings ) )
                
                new_temp_strings = tuple( ( key + ': ' + value for ( key, value ) in list(new_temp_variables.items()) ) )
                
                test_result = ( self._name, url, test_result_body, downloaded_text, new_temp_strings, new_cookie_strings, test_script_result )
                
                test_result_callable( test_result )
                
            
        
    
    def ToTuple( self ):
        
        return ( self._scheme, self._method, self._subdomain, self._path, self._required_credentials, self._static_args, self._temp_args, self._required_cookies_info, self._content_parsers )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_LOGIN_STEP ] = LoginStep

