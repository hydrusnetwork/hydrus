import ClientConstants as CC
import ClientDefaults
import ClientNetworkingContexts
import ClientNetworkingDomain
import ClientNetworkingJobs
import ClientParsing
import HydrusConstants as HC
import HydrusGlobals as HG
import HydrusData
import HydrusExceptions
import HydrusSerialisable
import os
import json
import requests

import threading
import time
import urllib

VALIDITY_VALID = 0
VALIDITY_UNTESTED = 1
VALIDITY_INVALID = 2

# make this serialisable
class LoginCredentials( object ):
    
    def __init__( self ):
        
        self._credentials = {} # user-facing name (unique) : string
        
        self._validity = VALIDITY_UNTESTED
        
    
    def GetCredential( self, name ):
        
        return self._credentials[ name ]
        
    
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
        
        self._lock = threading.Lock()
        
        self._domains_to_login_scripts_and_credentials = {}
        
        self._hydrus_login_script = LoginScriptHydrus()
        
        # as a login script can apply to multiple places, the actual credentials should be a separate object
        # this makes script import/export privacy a little easier!
        # these credentials should have validity tracking too
        # the script failing vs the credentials failing are different things, wew
        
        # track recent error at the script level? some sensible way of dealing with 'domain is currently down, so try again later'
        # maybe this should be at the domain manager's validity level, yeah.
        
        # so, we fetch all the logins, ask them for the network contexts so we can set up the dict
        # variables from old object here
        self._error_names = set()
        
        # should this be handled in the session manager? yeah, prob
        self._network_contexts_to_session_timeouts = {}
        
    
    def _GetLoginNetworkContext( self, network_context ):
        
        nc_domain = network_context.context_data
        
        domains = ClientNetworkingDomain.ConvertDomainIntoAllApplicableDomains( nc_domain )
        
        for domain in domains:
            
            if domain in self._domains_to_login_scripts_and_credentials:
                
                return domain
                
            
        
        return None
        
    
    def _GetSerialisableInfo( self ):
        
        return {}
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        self._network_contexts_to_logins = {}
        
    
    def CheckCanLogin( self, network_context ):
        
        with self._lock:
            
            if network_context.context_type == CC.NETWORK_CONTEXT_DOMAIN:
                
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
                    
                
                login_network_context = self._GetLoginNetworkContext( network_context )
                
                if login_network_context is None:
                    
                    raise HydrusExceptions.LoginException( 'Could not find a network context to login with!' )
                    
                
                ( login_script, credentials ) = self._domains_to_login_scripts_and_credentials[ login_network_context.context_data ]
                
                login_script.CheckCanLogin( credentials )
                
            elif network_context.context_type == CC.NETWORK_CONTEXT_HYDRUS:
                
                service_key = network_context.context_data
                
                services_manager = self.engine.controller.services_manager
                
                if not services_manager.ServiceExists( service_key ):
                    
                    raise HydrusExceptions.LoginException( 'Service does not exist!' )
                    
                
                service = services_manager.GetService( service_key )
                
                try:
                    
                    service.CheckFunctional( including_account = False )
                    
                except Exception as e:
                    
                    message = 'Service has had a recent error or is otherwise not functional! Specific error was:'
                    message += os.linesep * 2
                    message += HydrusData.ToUnicode( e )
                    message += os.linesep * 2
                    message += 'You might like to try refreshing its account in \'review services\'.'
                    
                    raise HydrusExceptions.LoginException( message )
                    
                
            
        
    
    def GenerateLoginProcess( self, network_context ):
        
        with self._lock:
            
            if network_context.context_type == CC.NETWORK_CONTEXT_DOMAIN:
                
                domain = network_context.context_data
                
                if 'pixiv.net' in domain:
                    
                    return LoginProcessLegacy( self.engine, PIXIV_NETWORK_CONTEXT, 'pixiv' )
                    
                elif 'hentai-foundry.com' in domain:
                    
                    return LoginProcessLegacy( self.engine, HENTAI_FOUNDRY_NETWORK_CONTEXT, 'hentai foundry' )
                    
                
                login_network_context = self._GetLoginNetworkContext( network_context )
                
                if login_network_context is None:
                    
                    raise HydrusExceptions.DataMissing()
                    
                
                ( login_script, credentials ) = self._domains_to_login_scripts_and_credentials[ login_network_context.context_data ]
                
                login_process = LoginProcessDomain( self.engine, login_network_context, login_script, credentials )
                
            elif network_context.context_type == CC.NETWORK_CONTEXT_HYDRUS:
                
                login_process = LoginProcessHydrus( self.engine, network_context, self._hydrus_login_script )
                
                return login_process
                
            
        
    
    def NeedsLogin( self, network_context ):
        
        with self._lock:
            
            if network_context.context_type == CC.NETWORK_CONTEXT_DOMAIN:
                
                domain = network_context.context_data
                
                if 'pixiv.net' in domain:
                    
                    required_cookies = [ 'PHPSESSID' ]
                    
                    return not self._IsLoggedIn( PIXIV_NETWORK_CONTEXT, required_cookies )
                    
                elif 'hentai-foundry.com' in domain:
                    
                    required_cookies = [ 'PHPSESSID', 'YII_CSRF_TOKEN' ]
                    
                    return not self._IsLoggedIn( HENTAI_FOUNDRY_NETWORK_CONTEXT, required_cookies )
                    
                
                login_network_context = self._GetLoginNetworkContext( network_context )
                
                if login_network_context is None:
                    
                    return False
                    
                
                ( login_script, credentials ) = self._domains_to_login_scripts_and_credentials[ login_network_context.context_data ]
                
                return not login_script.IsLoggedIn( self.engine, login_network_context )
                
            elif network_context.context_type == CC.NETWORK_CONTEXT_HYDRUS:
                
                return not self._hydrus_login_script.IsLoggedIn( self.engine, network_context )
                
            
        
    
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
        
        self.login_script.Start( self.engine, self.network_context, self.credentials )
        
    
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
    
    def _IsLoggedIn( self, session ):
        
        cookies = session.cookies
        
        cookies.clear_expired_cookies()
        
        return 'session_key' in cookies
        
    
    def IsLoggedIn( self, engine, network_context ):
        
        session = engine.session_manager.GetSession( network_context )
        
        return self._IsLoggedIn( session )
        
    
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
            
            session = engine.session_manager.GetSession( network_context )
            
            if self._IsLoggedIn( session ):
                
                HydrusData.Print( 'Successfully logged into ' + service.GetName() + '.' )
                
            else:
                
                service.DelayFutureRequests( 'Could not log in for unknown reason.' )
                
            
        except Exception as e:
            
            e_string = str( e )
            
            service.DelayFutureRequests( e_string )
            
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_LOGIN_MANAGER ] = NetworkLoginManager

# make this serialisable
class LoginScriptDomain( object ):
    
    def __init__( self ):
        
        self._name = 'gelbooru v2.0 login script'
        self._login_steps = []
        self._validity = VALIDITY_UNTESTED
        self._error_reason = ''
        
        self._expected_cookies_for_login = [] # [ name, stringmatch, minimum_expiry ]
        
    
    def _IsLoggedIn( self, network_context, session ):
        
        # this is more complicated for sadpanda, right?
        # I may need some way to have an override of some kind that is like 'this login script specifically logs in to one domain, although it applies to others'
        # need to research sadpanda exact mechanism--is it IP based?
        
        # this should also return ( result, reason ) for testing and other purposes
        
        cookies = session.cookies
        
        cookies.clear_expired_cookies()
        
        search_domain = network_context.context_data
        
        for ( name, string_match ) in self._expected_cookies_for_login:
            
            try:
                
                cookie_text = ClientNetworkingDomain.GetCookie( cookies, search_domain, name )
                
            except HydrusExceptions.DataMissing as e:
                
                return False
                
            
            try:
                
                string_match.Test( cookie_text )
                
            except HydrusExceptions.StringMatchException:
                
                return False
                
            
        
        return True
        
    
    def CheckCanLogin( self, credentials ):
        
        if self._validity == VALIDITY_INVALID:
            
            raise HydrusExceptions.LoginException( 'Login script is not valid: ' + self._error_reason )
            
        
        for step in self._login_steps:
            
            try:
                
                step.TestCredentials( credentials )
                
            except HydrusExceptions.ValidationException as e:
                
                raise HydrusExceptions.LoginException( str( e ) )
                
            
        
    
    def GetExpectedCredentialDestinations( self, domain ):
        
        # for step in steps, say where each named credential is going
        # return a dict like:
        
        # login.pixiv.net : username, password
        # evilsite.bg.cx : username, password
        
        # This'll be presented on the cred entering form so it can't be missed
        
        pass
        
    
    def GetRequiredCredentials( self ):
        
        required_creds = []
        
        for step in self._login_steps:
            
            required_creds.extend( step.GetRequiredCredentials() ) # [ ( credential_type, name, arg_name, string_match ) ] with an order
            
        
        return required_creds
        
    
    def IsLoggedIn( self, engine, network_context ):
        
        session = engine.session_manager.GetSession( network_context )
        
        return self._IsLoggedIn( network_context, session )
        
    
    def Start( self, engine, domain, network_context, credentials ):
        
        # don't mess with the domain--assume that we are given precisely the right domain
        
        # this maybe takes some job_key or something so it can present to the user login process status
        # this will be needed in the dialog where we test this. we need good feedback on how it is going
        # irl, this could be a 'login popup' message as well, just to inform the user on the progress of any delay
        
        temp_variables = {}
        
        for step in self._login_steps:
            
            try:
                
                step.Start( engine, credentials, temp_variables )
                
            except HydrusExceptions.ValidationException as e:
                
                self._error_reason = str( e )
                
                self._validity = VALIDITY_INVALID
                
                engine.login_manager.SetDirty()
                
            except Exception as e:
                
                # set error info
                
                self._validity = VALIDITY_INVALID
                
                # inform login manager that I'm dirty and need to be saved
                
                return False
                
            
        
        # test session logged in status here, erroring gracefully
        
        return True
        
    
LOGIN_PARAMETER_TYPE_PARAMETER = 0
LOGIN_PARAMETER_TYPE_COOKIE = 1
LOGIN_PARAMETER_TYPE_HEADER = 2

# make this serialisable
class LoginStep( object ):
    
    def __init__( self ):
        
        self._name = 'hit home page to establish session'
        
        self._method = None # get/post
        self._domain_string_converter = None
        self._query = 'login.php'
        
        self._statics = [] # arg name | string
        
        self._required_credentials = [] # type | user-facing name (unique) | arg name | string match
        
        self._required_temps = [] # arg name
        
        self._expected_cookies = [] # name | string match
        
        self._content_parsing_nodes = []
        
    
    def _TestCredentials( self, credentials ):
        
        for ( credential_type, pretty_name, arg_name, string_match ) in self._required_credentials:
        
            if arg_name not in credentials:
                
                raise HydrusExceptions.ValidationException( 'The credential \'' + pretty_name + '\' was missing!' )
                
            
            arg_value = credentials.GetCredential( arg_name )
            
            try:
                
                string_match.Test( arg_name )
                
            except HydrusExceptions.StringMatchException as e:
                
                reason = HydrusData.ToUnicode( e )
                
                raise HydrusExceptions.ValidationException( 'The credential \'' + pretty_name + '\' did not match requirements:' + os.linesep + reason )
                
            
        
    
    def GetRequiredCredentials( self ):
        
        return list( self._required_credentials )
        
    
    def Start( self, engine, domain, credentials, temp_variables ):
        
        # e.g. converting 'website.com' to 'login.website.com'
        url_base = self._domain_string_converter.Convert( domain )
        
        arguments = {}
        
        arguments.update( self._statics )
        
        self._TestCredentials( credentials )
        
        for ( credential_type, pretty_name, arg_name, string_match ) in self._required_credentials:
            
            arguments[ arg_name ] = credentials.GetCredential( arg_name )
            
        
        for name in self._required_temps:
            
            if name not in temp_variables:
                
                raise HydrusExceptions.ValidationException( 'The temporary variable \'' + name + '\' was not found!' )
                
            
            arguments[ name ] = temp_variables[ name ]
            
        
        if self._method == 'POST':
            
            pass # make it into body
            
        elif self._method == 'GET':
            
            pass # make it into query
            
        
        # construct the url, failing if creds or temps missing
        
        # hit the url, failing on connection fault or whatever
        
        for parsing_node in self._content_parsing_nodes:
            
            try:
                
                parsing_node.Vetoes()
                
            except HydrusExceptions.VetoException as e:
                
                raise HydrusExceptions.ValidationException( HydrusData.ToUnicode( e ) )
                
            
            # if content type is a temp variable:
            
            # get it and add to temp_variables
            
            pass
            
        
    
    def TestCredentials( self, credentials ):
        
        self._TestCredentials( credentials )
        

