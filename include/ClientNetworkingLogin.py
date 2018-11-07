import ClientConstants as CC
import ClientDefaults
import ClientNetworkingContexts
import ClientNetworkingDomain
import ClientNetworkingJobs
import ClientParsing
import ClientThreading
import cPickle
import HydrusConstants as HC
import HydrusGlobals as HG
import HydrusData
import HydrusExceptions
import HydrusSerialisable
import itertools
import os
import json
import requests
import re
import threading
import time
import urllib
import urlparse

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
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        # needs _dirty and setdirty and be on that serialisation check and so on
        
        self.engine = None
        
        self._dirty = False
        
        self._lock = threading.Lock()
        
        self._login_scripts = HydrusSerialisable.SerialisableList()
        self._domains_to_login_info = {}
        
        self._login_script_keys_to_login_scripts = {}
        self._login_script_names_to_login_scripts = {}
        
        self._hydrus_login_script = LoginScriptHydrus()
        
        self._error_names = set()
        
    
    def _GetLoginDomainStatus( self, network_context ):
        
        login_domain = None
        login_expected = False
        login_possible = True
        login_error_text = ''
        
        domain = network_context.context_data
        
        potential_login_domains = ClientNetworkingDomain.ConvertDomainIntoAllApplicableDomains( domain, discard_www = False )
        
        for potential_login_domain in potential_login_domains:
            
            if potential_login_domain in self._domains_to_login_info:
                
                login_domain = potential_login_domain
                
                ( login_script_key_and_name, credentials, login_access_type, login_access_text, active, validity, validity_error_text, no_work_until, no_work_until_reason ) = self._domains_to_login_info[ login_domain ]
                
                if active or login_access_type == LOGIN_ACCESS_TYPE_EVERYTHING:
                    
                    login_expected = True
                    
                
                if not active:
                    
                    login_possible = False
                    login_error_text = 'Not active - ' + login_access_text
                    
                elif validity == VALIDITY_INVALID:
                    
                    login_possible = False
                    login_error_text = validity_error_text
                    
                elif not HydrusData.TimeHasPassed( no_work_until ):
                    
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
                validity_error_text = HydrusData.ToUnicode( e )
                
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
        
        for ( login_domain, ( login_script_key_and_name, credentials, login_access_type, login_access_text, active, validity, validity_error_text, no_work_until, no_work_until_reason ) ) in self._domains_to_login_info.items():
            
            ( login_script_key, login_script_name ) = login_script_key_and_name
            
            serialisable_login_script_key_and_name = ( login_script_key.encode( 'hex' ), login_script_name )
            
            serialisable_domains_to_login_info[ login_domain ] = ( serialisable_login_script_key_and_name, credentials, login_access_type, login_access_text, active, validity, validity_error_text, no_work_until, no_work_until_reason )
            
        
        return ( serialisable_login_scripts, serialisable_domains_to_login_info )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_login_scripts, serialisable_domains_to_login_info ) = serialisable_info
        
        self._login_scripts = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_login_scripts )
        
        self._domains_to_login_info = {}
        
        for ( login_domain, ( serialisable_login_script_key_and_name, credentials, login_access_type, login_access_text, active, validity, validity_error_text, no_work_until, no_work_until_reason ) ) in serialisable_domains_to_login_info.items():
            
            ( serialisable_login_script_key, login_script_name ) = serialisable_login_script_key_and_name
            
            login_script_key_and_name = ( serialisable_login_script_key.decode( 'hex' ), login_script_name )
            
            self._domains_to_login_info[ login_domain ] = ( login_script_key_and_name, credentials, login_access_type, login_access_text, active, validity, validity_error_text, no_work_until, no_work_until_reason )
            
        
    
    def _RecalcCache( self ):
        
        self._login_script_keys_to_login_scripts = { login_script.GetLoginScriptKey() : login_script for login_script in self._login_scripts }
        self._login_script_names_to_login_scripts = { login_script.GetName() : login_script for login_script in self._login_scripts }
        
        self._RevalidateCache()
        
    
    def _RevalidateCache( self ):
        
        for login_domain in self._domains_to_login_info.keys():
            
            try:
                
                self._GetLoginScriptAndCredentials( login_domain )
                
            except HydrusExceptions.ValidationException:
                
                pass
                
            
        
    
    def _SetDirty( self ):
        
        self._dirty = True
        
    
    def CheckCanLogin( self, network_context ):
        
        with self._lock:
            
            if network_context.context_type == CC.NETWORK_CONTEXT_DOMAIN:
                '''
                domain = network_context.context_data
                
                if 'pixiv.net' in domain:
                    
                    if not LEGACY_LOGIN_OK:
                        
                        raise Exception( 'Legacy login broke last time--please either restart the client or contact hydrus dev!' )
                        
                    
                    result = self.engine.controller.Read( 'serialisable_simple', 'pixiv_account' )
                    
                    if result is None:
                        
                        raise HydrusExceptions.DataMissing( 'You need to set up your pixiv credentials in services->manage pixiv account.' )
                        
                    
                    return
                    
                elif 'hentai-foundry.com' in domain:
                    
                    if not LEGACY_LOGIN_OK:
                        
                        raise Exception( 'Legacy login broke last time--please either restart the client or contact hydrus dev!' )
                        
                    
                    return
                    
                '''
                ( login_domain, login_expected, login_possible, login_error_text ) = self._GetLoginDomainStatus( network_context )
                
                if login_domain is None or not login_expected:
                    
                    raise HydrusExceptions.ValidationException( 'The domain ' + login_domain + ' has no active login script--has it just been turned off?' )
                    
                elif not login_possible:
                    
                    raise HydrusExceptions.ValidationException( 'The domain ' + login_domain + ' cannot log in: ' + login_error_text )
                    
                
            elif network_context.context_type == CC.NETWORK_CONTEXT_HYDRUS:
                
                service_key = network_context.context_data
                
                services_manager = self.engine.controller.services_manager
                
                if not services_manager.ServiceExists( service_key ):
                    
                    raise HydrusExceptions.ValidationException( 'Service does not exist!' )
                    
                
                service = services_manager.GetService( service_key )
                
                try:
                    
                    service.CheckFunctional( including_account = False )
                    
                except Exception as e:
                    
                    message = 'Service has had a recent error or is otherwise not functional! Specific error was:'
                    message += os.linesep * 2
                    message += HydrusData.ToUnicode( e )
                    message += os.linesep * 2
                    message += 'You might like to try refreshing its account in \'review services\'.'
                    
                    raise HydrusExceptions.ValidationException( message )
                    
                
            
        
    
    def DelayLoginScript( self, login_domain, login_script_key, reason ):
        
        with self._lock:
            
            if login_domain not in self._domains_to_login_info:
                
                return
                
            
            ( login_script_key_and_name, credentials, login_access_type, login_access_text, active, validity, validity_error_text, no_work_until, no_work_until_reason ) = self._domains_to_login_info[ login_domain ]
            
            if login_script_key != login_script_key_and_name[0]:
                
                return
                
            
            no_work_until = HydrusData.GetNow() + 3600 * 4
            no_work_until_reason = reason
            
            self._domains_to_login_info[ login_domain ] = ( login_script_key_and_name, credentials, login_access_type, login_access_text, active, validity, validity_error_text, no_work_until, no_work_until_reason )
            
            self._SetDirty()
            
        
    
    def GenerateLoginProcess( self, network_context ):
        
        with self._lock:
            
            if network_context.context_type == CC.NETWORK_CONTEXT_DOMAIN:
                '''
                domain = network_context.context_data
                
                if 'pixiv.net' in domain:
                    
                    return LoginProcessLegacy( self.engine, PIXIV_NETWORK_CONTEXT, 'pixiv' )
                    
                elif 'hentai-foundry.com' in domain:
                    
                    return LoginProcessLegacy( self.engine, HENTAI_FOUNDRY_NETWORK_CONTEXT, 'hentai foundry' )
                    
                '''
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
            
            HydrusData.ShowText( 'The login for "' + login_domain + '" failed! It will not be reattempted until the problem is fixed. The failure reason was:' + os.linesep * 2 + validity_error_text )
            
            self._SetDirty()
            
        
    
    def IsDirty( self ):
        
        with self._lock:
            
            return self._dirty
            
        
    
    def NeedsLogin( self, network_context ):
        
        with self._lock:
            
            if network_context.context_type == CC.NETWORK_CONTEXT_DOMAIN:
                '''
                domain = network_context.context_data
                
                if 'pixiv.net' in domain:
                    
                    required_cookies = [ 'PHPSESSID' ]
                    
                    return not self._IsLoggedIn( PIXIV_NETWORK_CONTEXT, required_cookies )
                    
                elif 'hentai-foundry.com' in domain:
                    
                    required_cookies = [ 'PHPSESSID', 'YII_CSRF_TOKEN' ]
                    
                    return not self._IsLoggedIn( HENTAI_FOUNDRY_NETWORK_CONTEXT, required_cookies )
                    
                '''
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
                
            
        
    
    def OverwriteDefaultLoginScripts( self, login_script_names ):
        
        with self._lock:
            
            import ClientDefaults
            
            default_login_scripts = ClientDefaults.GetDefaultLoginScripts()
            
            for login_script in default_login_scripts:
                
                login_script.RegenerateLoginScriptKey()
                
            
            existing_login_scripts = list( self._login_scripts )
            
            new_login_scripts = [ login_script for login_script in existing_login_scripts if login_script.GetName() not in login_script_names ]
            new_login_scripts.extend( [ login_script for login_script in default_login_scripts if login_script.GetName() in login_script_names ] )
            
        
        self.SetLoginScripts( new_login_scripts )
        
    
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
            
        
    
    def SetDomainsToLoginInfo( self, domains_to_login_info ):
        
        with self._lock:
            
            self._domains_to_login_info = dict( domains_to_login_info )
            
            self._RecalcCache()
            
            self._SetDirty()
            
        
    
    def SetLoginScripts( self, login_scripts ):
        
        with self._lock:
            
            self._login_scripts = HydrusSerialisable.SerialisableList( login_scripts )
            
            # start with simple stuff first
            self._login_scripts.sort( key = lambda ls: len( ls.GetCredentialDefinitions() ) )
            
            for login_script in self._login_scripts:
                
                example_domains_info = login_script.GetExampleDomainsInfo()
                
                for ( login_domain, login_access_type, login_access_text ) in example_domains_info:
                    
                    if '.' in login_domain and login_domain not in self._domains_to_login_info:
                        
                        login_script_key_and_name = login_script.GetLoginScriptKeyAndName()
                        
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
            
        
    
    # these methods are from the old object:
    
    def _GetCookiesDict( self, network_context ):
        
        session = self.engine.session_manager.GetSession( network_context )
        
        cookies = session.cookies
        
        cookies.clear_expired_cookies()
        
        domains = cookies.list_domains()
        
        for domain in domains:
            
            if domain.endswith( network_context.context_data ):
                
                return cookies.get_dict( domain )
                
            
        
        return {}
        
    
    def _IsLoggedIn( self, network_context, required_cookies ):
        
        cookie_dict = self._GetCookiesDict( network_context )
        
        for name in required_cookies:
            
            if name not in cookie_dict:
                
                return False
                
            
        
        return True
        
    
    def EnsureLoggedIn( self, name ):
        
        with self._lock:
            
            if name in self._error_names:
                
                raise Exception( name + ' could not establish a session! This ugly error is temporary due to the network engine rewrite. Please restart the client to reattempt this network context.' )
                
            
            if name == 'hentai foundry':
                
                network_context = HENTAI_FOUNDRY_NETWORK_CONTEXT
                
                required_cookies = [ 'PHPSESSID', 'YII_CSRF_TOKEN' ]
                
            elif name == 'pixiv':
                
                network_context = PIXIV_NETWORK_CONTEXT
                
                required_cookies = [ 'PHPSESSID' ]
                
            
            if self._IsLoggedIn( network_context, required_cookies ):
                
                return
                
            
            try:
                
                if name == 'hentai foundry':
                    
                    self.LoginHF( network_context )
                    
                elif name == 'pixiv':
                    
                    result = self.engine.controller.Read( 'serialisable_simple', 'pixiv_account' )
                    
                    if result is None:
                        
                        raise HydrusExceptions.DataMissing( 'You need to set up your pixiv credentials in services->manage pixiv account.' )
                        
                    
                    ( pixiv_id, password ) = result
                    
                    self.LoginPixiv( network_context, pixiv_id, password )
                    
                
                if not self._IsLoggedIn( network_context, required_cookies ):
                    
                    raise Exception( name + ' login did not work correctly!' )
                    
                
                HydrusData.Print( 'Successfully logged into ' + name + '.' )
                
            except:
                
                self._error_names.add( name )
                
                raise
                
            
        
    
    def LoginHF( self, network_context ):
        
        session = self.engine.session_manager.GetSession( network_context )
        
        num_attempts = 0
        
        while True:
            
            try:
                
                response = session.get( 'https://www.hentai-foundry.com/', timeout = 10 )
                
                break
                
            except ( requests.exceptions.ConnectionError, requests.exceptions.ConnectTimeout ):
                
                if num_attempts < 3:
                    
                    num_attempts += 1
                    
                    time.sleep( 3 )
                    
                else:
                    
                    raise HydrusExceptions.ConnectionException( 'Could not connect to HF to log in!' )
                    
                
            
        
        time.sleep( 1 )
        
        response = session.get( 'https://www.hentai-foundry.com/?enterAgree=1' )
        
        time.sleep( 1 )
        
        cookie_dict = self._GetCookiesDict( network_context )
        
        raw_csrf = cookie_dict[ 'YII_CSRF_TOKEN' ] # 19b05b536885ec60b8b37650a32f8deb11c08cd1s%3A40%3A%222917dcfbfbf2eda2c1fbe43f4d4c4ec4b6902b32%22%3B
        
        processed_csrf = urllib.unquote( raw_csrf ) # 19b05b536885ec60b8b37650a32f8deb11c08cd1s:40:"2917dcfbfbf2eda2c1fbe43f4d4c4ec4b6902b32";
        
        csrf_token = processed_csrf.split( '"' )[1] # the 2917... bit
        
        hentai_foundry_form_info = ClientDefaults.GetDefaultHentaiFoundryInfo()
        
        hentai_foundry_form_info[ 'YII_CSRF_TOKEN' ] = csrf_token
        
        response = session.post( 'http://www.hentai-foundry.com/site/filters', data = hentai_foundry_form_info )
        
        time.sleep( 1 )
        
    
    # This updated login form is cobbled together from the example in PixivUtil2
    # it is breddy shid but getting better
    # Pixiv 400s if cookies and referrers aren't passed correctly
    # I am leaving this as a mess with the hope the eventual login engine will replace it
    def LoginPixiv( self, network_context, pixiv_id, password ):
        
        session = self.engine.session_manager.GetSession( network_context )
        
        response = session.get( 'https://accounts.pixiv.net/login' )
        
        soup = ClientParsing.GetSoup( response.content )
        
        # some whocking 20kb bit of json tucked inside a hidden form input wew lad
        i = soup.find( 'input', id = 'init-config' )
        
        raw_json = i['value']
        
        j = json.loads( raw_json )
        
        if 'pixivAccount.postKey' not in j:
            
            raise HydrusExceptions.ForbiddenException( 'When trying to log into Pixiv, I could not find the POST key! This is a problem with hydrus\'s pixiv parsing, not your login! Please contact hydrus dev!' )
            
        
        post_key = j[ 'pixivAccount.postKey' ]
        
        form_fields = {}
        
        form_fields[ 'pixiv_id' ] = pixiv_id
        form_fields[ 'password' ] = password
        form_fields[ 'captcha' ] = ''
        form_fields[ 'g_recaptcha_response' ] = ''
        form_fields[ 'return_to' ] = 'https://www.pixiv.net'
        form_fields[ 'lang' ] = 'en'
        form_fields[ 'post_key' ] = post_key
        form_fields[ 'source' ] = 'pc'
        
        headers = {}
        
        headers[ 'referer' ] = "https://accounts.pixiv.net/login?lang=en^source=pc&view_type=page&ref=wwwtop_accounts_index"
        headers[ 'origin' ] = "https://accounts.pixiv.net"
        
        session.post( 'https://accounts.pixiv.net/api/login?lang=en', data = form_fields, headers = headers )
        
        time.sleep( 1 )
        
    
    def LoginTumblrGDPR( self ):
        
        # t-thanks, EU
        # this is cribbed from poking around here https://github.com/johanneszab/TumblThree/commit/3563d6cebf1a467151d6b8d6eee9806ddd6e6364
        
        network_job = ClientNetworkingJobs.NetworkJob( 'GET', 'http://www.tumblr.com/' )
        
        network_job.SetForLogin( True )
        
        self.engine.AddJob( network_job )
        
        network_job.WaitUntilDone()
        
        html = network_job.GetContent()
        
        formula = ClientParsing.ParseFormulaHTML( tag_rules = [ ClientParsing.ParseRuleHTML( rule_type = ClientParsing.HTML_RULE_TYPE_DESCENDING, tag_name = 'meta', tag_attributes = { 'id' : 'tumblr_form_key' } ) ], content_to_fetch = ClientParsing.HTML_CONTENT_ATTRIBUTE, attribute_to_fetch = "content" )
        
        results = formula.Parse( {}, html )
        
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
        
    
    def TestPixiv( self, pixiv_id, password ):
        
        # this is just an ugly copy, but fuck it for the minute
        # we'll figure out a proper testing engine later with the login engine and tie the manage gui into it as well
        
        session = requests.Session()
        
        response = session.get( 'https://accounts.pixiv.net/login' )
        
        soup = ClientParsing.GetSoup( response.content )
        
        # some whocking 20kb bit of json tucked inside a hidden form input wew lad
        i = soup.find( 'input', id = 'init-config' )
        
        raw_json = i['value']
        
        j = json.loads( raw_json )
        
        if 'pixivAccount.postKey' not in j:
            
            return ( False, 'When trying to log into Pixiv, I could not find the POST key! This is a problem with hydrus\'s pixiv parsing, not your login! Please contact hydrus dev!' )
            
        
        post_key = j[ 'pixivAccount.postKey' ]
        
        form_fields = {}
        
        form_fields[ 'pixiv_id' ] = pixiv_id
        form_fields[ 'password' ] = password
        form_fields[ 'captcha' ] = ''
        form_fields[ 'g_recaptcha_response' ] = ''
        form_fields[ 'return_to' ] = 'https://www.pixiv.net'
        form_fields[ 'lang' ] = 'en'
        form_fields[ 'post_key' ] = post_key
        form_fields[ 'source' ] = 'pc'
        
        headers = {}
        
        headers[ 'referer' ] = "https://accounts.pixiv.net/login?lang=en^source=pc&view_type=page&ref=wwwtop_accounts_index"
        headers[ 'origin' ] = "https://accounts.pixiv.net"
        
        r = session.post( 'https://accounts.pixiv.net/api/login?lang=en', data = form_fields, headers = headers )
        
        if not r.ok:
            
            HydrusData.ShowText( r.content )
            
            return ( False, 'Login request failed! Info printed to log.' )
            
        
        cookies = session.cookies
        
        cookies.clear_expired_cookies()
        
        domains = cookies.list_domains()
        
        for domain in domains:
            
            if domain.endswith( 'pixiv.net' ):
                
                d = cookies.get_dict( domain )
                
                if 'PHPSESSID' not in d:
                    
                    HydrusData.ShowText( r.content )
                    
                    return ( False, 'Pixiv login failed to establish session! Info printed to log.' )
                    
                
                return ( True, '' )
                
            
        
        HydrusData.ShowText( r.content )
        
        return ( False, 'Pixiv login failed to establish session! Info printed to log.' )
        
    
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
            
            string_match = ClientParsing.StringMatch()
            
        
        HydrusSerialisable.SerialisableBaseNamed.__init__( self, name )
        
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
                
                raise HydrusExceptions.ValidationException( 'Could not validate "' + self._name + '" credential: ' + HydrusData.ToUnicode( e ) )
                
            
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_LOGIN_CREDENTIAL_DEFINITION ] = LoginCredentialDefinition

class LoginProcess( object ):
    
    def __init__( self, engine, network_context, login_script ):
        
        self.engine = engine
        self.network_context = network_context
        self.login_script = login_script
        
        self._done = False
        
    
    def _Start( self ):
        
        raise NotImplementedError()
        
    
    def IsDone( self ):
        
        return self._done
        
    
    def Start( self ):
        
        try:
            
            self._Start()
            
        finally:
            
            self._done = True
            
        
    
class LoginProcessDomain( LoginProcess ):
    
    def __init__( self, engine, network_context, login_script, credentials ):
        
        LoginProcess.__init__( self, engine, network_context, login_script )
        
        self.credentials = credentials
        
    
    def _Start( self ):
        
        login_domain = self.network_context.context_data
        
        job_key = ClientThreading.JobKey( cancellable = True )
        
        job_key.SetVariable( 'popup_title', 'Logging in ' + login_domain )
        
        HG.client_controller.pub( 'message', job_key )
        
        HydrusData.Print( 'Starting login for ' + login_domain )
        
        result = self.login_script.Start( self.engine, self.network_context, self.credentials, job_key = job_key )
        
        HydrusData.Print( 'Finished login for ' + self.network_context.context_data + '. Result was: ' + result )
        
        job_key.SetVariable( 'popup_text_1', result )
        
        job_key.Finish()
        
        job_key.Delete( 4 )
        
    
class LoginProcessHydrus( LoginProcess ):
    
    def _Start( self ):
        
        self.login_script.Start( self.engine, self.network_context )
        
    
LEGACY_LOGIN_OK = True

class LoginProcessLegacy( LoginProcess ):
    
    def _GetCookiesDict( self, network_context ):
        
        session = self.engine.session_manager.GetSession( network_context )
        
        cookies = session.cookies
        
        cookies.clear_expired_cookies()
        
        domains = cookies.list_domains()
        
        for domain in domains:
            
            if domain.endswith( network_context.context_data ):
                
                return cookies.get_dict( domain )
                
            
        
        return {}
        
    
    def _Start( self ):
        
        try:
            
            name = self.login_script
            
            if name == 'hentai foundry':
                
                self.LoginHF( self.network_context )
                
            elif name == 'pixiv':
                
                result = self.engine.controller.Read( 'serialisable_simple', 'pixiv_account' )
                
                if result is None:
                    
                    raise HydrusExceptions.DataMissing( 'You need to set up your pixiv credentials in services->manage pixiv account.' )
                    
                
                ( pixiv_id, password ) = result
                
                self.LoginPixiv( self.network_context, pixiv_id, password )
                
            
        except:
            
            global LEGACY_LOGIN_OK
            
            LEGACY_LOGIN_OK = False
            
        
    
    def LoginHF( self, network_context ):
        
        session = self.engine.session_manager.GetSession( network_context )
        
        num_attempts = 0
        
        while True:
            
            try:
                
                response = session.get( 'https://www.hentai-foundry.com/', timeout = 10 )
                
                break
                
            except ( requests.exceptions.ConnectionError, requests.exceptions.ConnectTimeout ):
                
                if num_attempts < 3:
                    
                    num_attempts += 1
                    
                    time.sleep( 3 )
                    
                else:
                    
                    raise HydrusExceptions.ConnectionException( 'Could not connect to HF to log in!' )
                    
                
            
        
        time.sleep( 1 )
        
        response = session.get( 'https://www.hentai-foundry.com/?enterAgree=1' )
        
        time.sleep( 1 )
        
        cookie_dict = self._GetCookiesDict( network_context )
        
        raw_csrf = cookie_dict[ 'YII_CSRF_TOKEN' ] # 19b05b536885ec60b8b37650a32f8deb11c08cd1s%3A40%3A%222917dcfbfbf2eda2c1fbe43f4d4c4ec4b6902b32%22%3B
        
        processed_csrf = urllib.unquote( raw_csrf ) # 19b05b536885ec60b8b37650a32f8deb11c08cd1s:40:"2917dcfbfbf2eda2c1fbe43f4d4c4ec4b6902b32";
        
        csrf_token = processed_csrf.split( '"' )[1] # the 2917... bit
        
        hentai_foundry_form_info = ClientDefaults.GetDefaultHentaiFoundryInfo()
        
        hentai_foundry_form_info[ 'YII_CSRF_TOKEN' ] = csrf_token
        
        response = session.post( 'http://www.hentai-foundry.com/site/filters', data = hentai_foundry_form_info )
        
        time.sleep( 1 )
        
    
    # This updated login form is cobbled together from the example in PixivUtil2
    # it is breddy shid but getting better
    # Pixiv 400s if cookies and referrers aren't passed correctly
    # I am leaving this as a mess with the hope the eventual login engine will replace it
    def LoginPixiv( self, network_context, pixiv_id, password ):
        
        session = self.engine.session_manager.GetSession( network_context )
        
        response = session.get( 'https://accounts.pixiv.net/login' )
        
        soup = ClientParsing.GetSoup( response.content )
        
        # some whocking 20kb bit of json tucked inside a hidden form input wew lad
        i = soup.find( 'input', id = 'init-config' )
        
        raw_json = i['value']
        
        j = json.loads( raw_json )
        
        if 'pixivAccount.postKey' not in j:
            
            raise HydrusExceptions.ForbiddenException( 'When trying to log into Pixiv, I could not find the POST key! This is a problem with hydrus\'s pixiv parsing, not your login! Please contact hydrus dev!' )
            
        
        post_key = j[ 'pixivAccount.postKey' ]
        
        form_fields = {}
        
        form_fields[ 'pixiv_id' ] = pixiv_id
        form_fields[ 'password' ] = password
        form_fields[ 'captcha' ] = ''
        form_fields[ 'g_recaptcha_response' ] = ''
        form_fields[ 'return_to' ] = 'https://www.pixiv.net'
        form_fields[ 'lang' ] = 'en'
        form_fields[ 'post_key' ] = post_key
        form_fields[ 'source' ] = 'pc'
        
        headers = {}
        
        headers[ 'referer' ] = "https://accounts.pixiv.net/login?lang=en^source=pc&view_type=page&ref=wwwtop_accounts_index"
        headers[ 'origin' ] = "https://accounts.pixiv.net"
        
        session.post( 'https://accounts.pixiv.net/api/login?lang=en', data = form_fields, headers = headers )
        
        time.sleep( 1 )
        
    
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
        
        service = engine.controller.services_manager.GetService( service_key )
        
        base_url = service.GetBaseURL()
        
        url = base_url + 'session_key'
        
        access_key = service.GetCredentials().GetAccessKey()
        
        network_job = ClientNetworkingJobs.NetworkJobHydrus( service_key, 'GET', url )
        
        network_job.SetForLogin( True )
        
        network_job.AddAdditionalHeader( 'Hydrus-Key', access_key.encode( 'hex' ) )
        
        engine.AddJob( network_job )
        
        try:
            
            network_job.WaitUntilDone()
            
            if self._IsLoggedIn( engine, network_context ):
                
                HydrusData.Print( 'Successfully logged into ' + service.GetName() + '.' )
                
            else:
                
                service.DelayFutureRequests( 'Could not log in for unknown reason.' )
                
            
        except Exception as e:
            
            e_string = str( e )
            
            service.DelayFutureRequests( e_string )
            
        
    
class LoginScriptDomain( HydrusSerialisable.SerialisableBaseNamed ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_LOGIN_SCRIPT_DOMAIN
    SERIALISABLE_NAME = 'Login Script - Domain'
    SERIALISABLE_VERSION = 1
    
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
            
        
        HydrusSerialisable.SerialisableBaseNamed.__init__( self, name )
        
        self._login_script_key = HydrusData.GenerateKey()
        self._required_cookies_info = required_cookies_info # name : stringmatch
        self._credential_definitions = credential_definitions
        self._login_steps = login_steps
        self._example_domains_info = example_domains_info # domain | login_access_type | login_access_text
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_login_script_key = self._login_script_key.encode( 'hex' )
        serialisable_required_cookies = self._required_cookies_info.GetSerialisableTuple()
        serialisable_credential_definitions = self._credential_definitions.GetSerialisableTuple()
        serialisable_login_steps = self._login_steps.GetSerialisableTuple()
        
        return ( serialisable_login_script_key, serialisable_required_cookies, serialisable_credential_definitions, serialisable_login_steps, self._example_domains_info )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_login_script_key, serialisable_required_cookies, serialisable_credential_definitions, serialisable_login_steps, self._example_domains_info ) = serialisable_info
        
        self._login_script_key = serialisable_login_script_key.decode( 'hex' )
        self._required_cookies_info = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_required_cookies )
        self._credential_definitions = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_credential_definitions )
        self._login_steps = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_login_steps )
        
        # convert lists to tups for listctrl data hashing
        self._example_domains_info = [ tuple( l ) for l in self._example_domains_info ]
        
    
    def _IsLoggedIn( self, engine, network_context, validation_check = False ):
        
        session = engine.session_manager.GetSession( network_context )
        
        cookies = session.cookies
        
        cookies.clear_expired_cookies()
        
        search_domain = network_context.context_data
        
        for ( cookie_name, string_match ) in self._required_cookies_info.items():
            
            try:
                
                cookie_text = ClientNetworkingDomain.GetCookie( cookies, search_domain, cookie_name )
                
            except HydrusExceptions.DataMissing as e:
                
                if validation_check:
                    
                    raise HydrusExceptions.ValidationException( 'Missing cookie "' + cookie_name + '"!' )
                    
                
                return False
                
            
            try:
                
                string_match.Test( cookie_text )
                
            except HydrusExceptions.StringMatchException:
                
                if validation_check:
                    
                    raise HydrusExceptions.ValidationException( 'Cookie "' + cookie_name + '" failed: ' + HydrusData.ToUnicode( e ) + '!' )
                    
                
                return False
                
            
        
        return True
        
    
    def CheckCanLogin( self, given_credentials ):
        
        self.CheckIsValid()
        
        given_cred_names = set( given_credentials.keys() )
        required_cred_names = { name for name in itertools.chain.from_iterable( ( step.GetRequiredCredentials() for step in self._login_steps ) ) }
        
        missing_givens = required_cred_names.difference( given_cred_names )
        
        if len( missing_givens ) > 0:
            
            missing_givens = list( missing_givens )
            missing_givens.sort()
            
            raise HydrusExceptions.ValidationException( 'Missing required credentials: ' + ', '.join( missing_givens ) )
            
        
        #
        
        cred_names_to_definitions = { credential_definition.GetName() : credential_definition for credential_definition in self._credential_definitions }
        
        for ( pretty_name, text ) in given_credentials.items():
            
            credential_definition = cred_names_to_definitions[ pretty_name ]
            
            credential_definition.Test( text )
            
        
    
    def CheckIsValid( self ):
        
        defined_cred_names = { credential_definition.GetName() for credential_definition in self._credential_definitions }
        required_cred_names = { name for name in itertools.chain.from_iterable( ( step.GetRequiredCredentials() for step in self._login_steps ) ) }
        
        missing_definitions = required_cred_names.difference( defined_cred_names )
        
        if len( missing_definitions ) > 0:
            
            missing_definitions = list( missing_definitions )
            missing_definitions.sort()
            
            raise HydrusExceptions.ValidationException( 'Missing required credential definitions: ' + ', '.join( missing_definitions ) )
            
        
        #
        
        temp_vars = set()
        
        for login_step in self._login_steps:
            
            ( required_vars, set_vars ) = login_step.GetRequiredAndSetTempVariables()
            
            missing_vars = required_vars.difference( temp_vars )
            
            if len( missing_vars ) > 0:
                
                missing_vars = list( missing_vars )
                missing_vars.sort()
                
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
        
    
    def IsLoggedIn( self, engine, network_context ):
        
        return self._IsLoggedIn( engine, network_context )
        
    
    def RegenerateLoginScriptKey( self ):
        
        self._login_script_key = HydrusData.GenerateKey()
        
    
    def SetLoginScriptKey( self, login_script_key ):
        
        self._login_script_key = login_script_key
        
    
    def Start( self, engine, network_context, given_credentials, network_job_presentation_context_factory = None, test_result_callable = None, job_key = None ):
        
        # don't mess with the domain--assume that we are given precisely the right domain
        
        login_domain = network_context.context_data
        
        temp_variables = {}
        
        last_url_used = None
        
        for login_step in self._login_steps:
            
            if job_key is not None:
                
                if job_key.IsCancelled():
                    
                    message = 'User cancelled the login process.'
                    
                    engine.login_manager.DelayLoginScript( login_domain, self._login_script_key, message )
                    
                    return message
                    
                
                job_key.SetVariable( 'popup_text_1', login_step.GetName() )
                
            
            try:
                
                last_url_used = login_step.Start( engine, login_domain, given_credentials, temp_variables, referral_url = last_url_used, network_job_presentation_context_factory = network_job_presentation_context_factory, test_result_callable = test_result_callable )
                
            except HydrusExceptions.ValidationException as e:
                
                if test_result_callable is not None:
                    
                    HydrusData.ShowException( e )
                    
                
                message = HydrusData.ToUnicode( e )
                
                engine.login_manager.InvalidateLoginScript( login_domain, self._login_script_key, message )
                
                return 'Verification error: ' + message
                
            except HydrusExceptions.NetworkException as e:
                
                if test_result_callable is not None:
                    
                    HydrusData.ShowException( e )
                    
                
                message = HydrusData.ToUnicode( e )
                
                engine.login_manager.DelayLoginScript( login_domain, self._login_script_key, message )
                
                return 'Network error: ' + message
                
            except Exception as e:
                
                if test_result_callable is not None:
                    
                    HydrusData.ShowException( e )
                    
                
                message = HydrusData.ToUnicode( e )
                
                engine.login_manager.InvalidateLoginScript( login_domain, self._login_script_key, message )
                
                return 'Unusual error: ' + message
                
            
            time.sleep( 2 )
            
        
        try:
            
            self._IsLoggedIn( engine, network_context, validation_check = True )
            
        except Exception as e:
            
            if test_result_callable is not None:
                
                HydrusData.ShowException( e )
                
            
            message = HydrusData.ToUnicode( e )
            
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
    SERIALISABLE_VERSION = 1
    
    def __init__( self, name = 'hit home page to establish session', scheme = 'https', method = 'GET', subdomain = None, path = '/' ):
        
        HydrusSerialisable.SerialisableBaseNamed.__init__( self, name )
        
        self._scheme = scheme
        self._method = method
        self._subdomain = subdomain
        self._path = path
        
        self._CleanseSubdomainAndPath()
        
        self._required_credentials = {} # pretty_name : arg name
        
        self._static_args = {} # arg name : string
        
        self._temp_args = {} # temp arg name : arg name
        
        self._required_cookies_info = HydrusSerialisable.SerialisableDictionary() # name : string match
        
        self._content_parsers = HydrusSerialisable.SerialisableList()
        
    
    def _CleanseSubdomainAndPath( self ):
        
        if self._subdomain is not None:
            
            self._subdomain = re.sub( '[^a-z\.]+', '', self._subdomain, flags = re.UNICODE )
            
        
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
        
    
    def GetRequiredCredentials( self ):
        
        return [ pretty_name for ( pretty_name, arg_name ) in self._required_credentials.items() ]
        
    
    def GetRequiredAndSetTempVariables( self ):
        
        required_temp_variables = set( self._temp_args.keys() )
        
        set_temp_variables = { additional_info for [ ( name, content_type, additional_info ) ] in [ content_parser.GetParsableContent() for content_parser in self._content_parsers ] }
        
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
                    
                    pretty_expiry = HydrusData.ConvertTimestampToPrettyExpires( expiry )
                    
                
                s += pretty_expiry
                
                cookie_strings.add( s )
                
            
            return cookie_strings
            
        
        url = 'Did not make a url.'
        test_result_body = None
        downloaded_data = 'Did not download data.'
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
            
            for ( pretty_name, arg_name ) in self._required_credentials.items():
                
                query_dict[ arg_name ] = given_credentials[ pretty_name ]
                
            
            for ( temp_name, arg_name ) in self._temp_args.items():
                
                if temp_name not in temp_variables:
                    
                    raise HydrusExceptions.ValidationException( 'The temporary variable \'' + temp_name + '\' was not found!' )
                    
                
                query_dict[ arg_name ] = temp_variables[ temp_name ]
                
            
            scheme = self._scheme
            netloc = domain_to_hit
            path = self._path
            params = ''
            fragment = ''
            
            if self._method == 'GET':
                
                query = ClientNetworkingDomain.ConvertQueryDictToText( query_dict )
                body = None
                test_result_body = ''
                
            elif self._method == 'POST':
                
                query = ''
                body = query_dict
                test_result_body = ClientNetworkingDomain.ConvertQueryDictToText( query_dict )
                
            
            r = urlparse.ParseResult( scheme, netloc, path, params, query, fragment )
            
            url = r.geturl()
            
            network_job = ClientNetworkingJobs.NetworkJob( self._method, url, body = body, referral_url = referral_url )
            
            if self._method == 'POST' and referral_url is not None:
                
                p = urlparse.urlparse( referral_url )
                
                r = urlparse.ParseResult( p.scheme, p.netloc, '', '', '', '' )
                
                origin = r.geturl() # https://accounts.pixiv.net
                
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
            
            for ( cookie_name, string_match ) in self._required_cookies_info.items():
                
                try:
                    
                    cookie_text = ClientNetworkingDomain.GetCookie( cookies, domain, cookie_name )
                    
                except HydrusExceptions.DataMissing as e:
                    
                    raise HydrusExceptions.ValidationException( 'Missing cookie "' + cookie_name + '" on step "' + self._name + '"!' )
                    
                
                try:
                    
                    string_match.Test( cookie_text )
                    
                except HydrusExceptions.StringMatchException as d:
                    
                    raise HydrusExceptions.ValidationException( 'Cookie "' + cookie_name + '" failed on step "' + self._name + '": ' + HydrusData.ToUnicode( e ) + '!' )
                    
                
            
            downloaded_data = network_job.GetContent()
            
            parsing_context = {}
            
            parsing_context[ 'url' ] = url
            
            for content_parser in self._content_parsers:
                
                try:
                    
                    parse_results = content_parser.Parse( parsing_context, downloaded_data )
                    
                except HydrusExceptions.VetoException as e:
                    
                    raise HydrusExceptions.ValidationException( HydrusData.ToUnicode( e ) )
                    
                
                result = ClientParsing.GetVariableFromParseResults( parse_results )
                
                if result is not None:
                    
                    ( temp_name, value ) = result
                    
                    new_temp_variables[ temp_name ] = value
                    
                
            
            temp_variables.update( new_temp_variables )
            
            test_script_result = 'OK!'
            
            return url
            
        except Exception as e:
            
            test_script_result = HydrusData.ToUnicode( e )
            
            raise
            
        finally:
            
            if test_result_callable is not None:
                
                current_cookie_strings = session_to_cookie_strings( engine.session_manager.GetSessionForDomain( domain ) )
                
                new_cookie_strings = tuple( current_cookie_strings.difference( original_cookie_strings ) )
                
                new_temp_strings = tuple( ( key + ': ' + value for ( key, value ) in new_temp_variables.items() ) )
                
                test_result = ( self._name, url, test_result_body, downloaded_data, new_temp_strings, new_cookie_strings, test_script_result )
                
                test_result_callable( test_result )
                
            
        
    
    def ToTuple( self ):
        
        return ( self._scheme, self._method, self._subdomain, self._path, self._required_credentials, self._static_args, self._temp_args, self._required_cookies_info, self._content_parsers )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_LOGIN_STEP ] = LoginStep

