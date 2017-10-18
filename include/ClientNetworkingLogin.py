import ClientConstants as CC
import ClientDefaults
import ClientDownloading
import ClientNetworking
import ClientNetworkingDomain
import HydrusConstants as HC
import HydrusGlobals as HG
import HydrusData
import HydrusExceptions
import HydrusSerialisable
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
        
    
    # get current values
    
    # test current values, including fail for not having enough/having too many

class NetworkLoginManager( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_LOGIN_MANAGER
    SERIALISABLE_VERSION = 1
    
    SESSION_TIMEOUT = 60 * 60
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self.engine = None
        
        self._lock = threading.Lock()
        
        self._domains_to_logins = {}
        
        # a login has:
          # a login script
          # rules to check validity in cookies in a current session (fold that into the login script, which may have several stages of this)
          # current user/pass/whatever
          # current script validity
          # current credentials validity
          # recent error? some way of dealing with 'domain is currently down, so try again later'
        
        # so, we fetch all the logins, ask them for the network contexts so we can set up the dict
        # variables from old object here
        self._error_names = set()
        
        self._network_contexts_to_session_timeouts = {}
        
    
    def _GetSerialisableInfo( self ):
        
        return {}
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        self._network_contexts_to_logins = {}
        
    
    def CanLogin( self, network_contexts ):
        
        # look them up in our structure
        # if they have a login, is it valid?
          # valid means we have tested credentials and it hasn't been invalidated by a parsing error or similar
          # I think this just means saying Login.CanLogin( credentials )
        
        return False
        
    
    def GenerateLoginProcess( self, network_contexts ):
        
        # look up the logins
          # login_process = Login.GenerateLoginProcess
          # return login_process
        
        raise NotImplementedError()
        
    
    def NeedsLogin( self, network_context ):
        
        with self._lock:
            
            if network_context.context_type == CC.NETWORK_CONTEXT_DOMAIN:
                
                nc_domain = network_context.context_data
                
                domains = ClientNetworkingDomain.ConvertDomainIntoAllApplicableDomains( nc_domain )
                
                for domain in domains:
                    
                    if domain in self._domains_to_logins:
                        
                        # fetch session
                        # does the login script reckon the session is logged in?
                        # if not, return True
                        
                        pass
                        
                    
                
            elif network_context.context_type == CC.NETWORK_CONTEXT_HYDRUS:
                
                service_key = network_context.context_data
                
                # figure it out here
                
            
            return False
            
        
    
    # these methods are from the old object:
    
    def _GetCookiesDict( self, network_context ):
        
        session = self._GetSession( network_context )
        
        cookies = session.cookies
        
        cookies.clear_expired_cookies()
        
        domains = cookies.list_domains()
        
        for domain in domains:
            
            if domain.endswith( network_context.context_data ):
                
                return cookies.get_dict( domain )
                
            
        
        return {}
        
    
    def _GetSession( self, network_context ):
        
        session = self.engine.controller.network_engine.session_manager.GetSession( network_context )
        
        if network_context not in self._network_contexts_to_session_timeouts:
            
            self._network_contexts_to_session_timeouts[ network_context ] = 0
            
        
        if HydrusData.TimeHasPassed( self._network_contexts_to_session_timeouts[ network_context ] ):
            
            session.cookies.clear_session_cookies()
            
        
        self._network_contexts_to_session_timeouts[ network_context ] = HydrusData.GetNow() + self.SESSION_TIMEOUT
        
        return session
        
    
    def _IsLoggedIn( self, network_context, required_cookies ):
        
        cookie_dict = self._GetCookiesDict( network_context )
        
        for name in required_cookies:
            
            if name not in cookie_dict:
                
                return False
                
            
        
        return True
        
    
    def EnsureHydrusSessionIsOK( self, service_key ):
        
        with self._lock:
            
            if not self.engine.controller.services_manager.ServiceExists( service_key ):
                
                raise HydrusExceptions.DataMissing( 'Service does not exist!' )
                
            
            name = self.engine.controller.services_manager.GetService( service_key ).GetName()
            
            if service_key in self._error_names:
                
                raise Exception( 'Could not establish a hydrus network session for ' + name + '! This ugly error is temporary due to the network engine rewrite. Please restart the client to reattempt this network context.' )
                
            
            network_context = ClientNetworking.NetworkContext( CC.NETWORK_CONTEXT_HYDRUS, service_key )
            
            required_cookies = [ 'session_key' ]
            
            if self._IsLoggedIn( network_context, required_cookies ):
                
                return
                
            
            try:
                
                self.SetupHydrusSession( service_key )
                
                if not self._IsLoggedIn( network_context, required_cookies ):
                    
                    return
                    
                
                HydrusData.Print( 'Successfully logged into ' + name + '.' )
                
            except:
                
                self._error_names.add( service_key )
                
                raise
                
            
        
    
    def EnsureLoggedIn( self, name ):
        
        with self._lock:
            
            if name in self._error_names:
                
                raise Exception( name + ' could not establish a session! This ugly error is temporary due to the network engine rewrite. Please restart the client to reattempt this network context.' )
                
            
            if name == 'hentai foundry':
                
                network_context = ClientNetworking.NetworkContext( CC.NETWORK_CONTEXT_DOMAIN, 'hentai-foundry.com' )
                
                required_cookies = [ 'PHPSESSID', 'YII_CSRF_TOKEN' ]
                
            elif name == 'pixiv':
                
                network_context = ClientNetworking.NetworkContext( CC.NETWORK_CONTEXT_DOMAIN, 'pixiv.net' )
                
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
        
        session = self._GetSession( network_context )
        
        response = session.get( 'https://www.hentai-foundry.com/' )
        
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
    # it is breddy shid because I'm not using mechanize or similar browser emulation (like requests's sessions) yet
    # Pixiv 400s if cookies and referrers aren't passed correctly
    # I am leaving this as a mess with the hope the eventual login engine will replace it
    def LoginPixiv( self, network_context, pixiv_id, password ):
        
        session = self._GetSession( network_context )
        
        response = session.get( 'https://accounts.pixiv.net/login' )
        
        soup = ClientDownloading.GetSoup( response.content )
        
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
        
    
    def SetupHydrusSession( self, service_key ):
        
        # nah, replace this with a proper login script
        
        service = self.engine.controller.services_manager.GetService( service_key )
        
        if not service.HasAccessKey():
            
            raise HydrusExceptions.DataMissing( 'No access key for this service, so cannot set up session!' )
            
        
        access_key = service.GetAccessKey()
        
        url = 'blah'
        
        network_job = ClientNetworking.NetworkJobHydrus( service_key, 'GET', url )
        
        network_job.SetForLogin( True )
        
        network_job.AddAdditionalHeader( 'Hydrus-Key', access_key.encode( 'hex' ) )
        
        self.engine.controller.network_engine.AddJob( network_job )
        
        network_job.WaitUntilDone()
        
    
    def TestPixiv( self, pixiv_id, password ):
        
        # this is just an ugly copy, but fuck it for the minute
        # we'll figure out a proper testing engine later with the login engine and tie the manage gui into it as well
        
        session = requests.Session()
        
        response = session.get( 'https://accounts.pixiv.net/login' )
        
        soup = ClientDownloading.GetSoup( response.content )
        
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

# make this serialisable
class LoginProcess( object ):
    
    def __init__( self ):
        
        self._network_context = None
        self._login_steps = []
        self._validity = VALIDITY_UNTESTED
        
        # possible error info
        
        self._temp_variables = {}
        
    
    def Start( self, controller, credentials ):
        
        # this maybe takes some job_key or something so it can present to the user login process status
        # this will be needed in the dialog where we test this. we need good feedback on how it is going
        # irl, this could be a 'login popup' message as well, just to inform the user on the progress of any delay
        
        for step in self._login_steps:
            
            try:
                
                step.Start( controller, credentials, self._temp_variables )
                
            except HydrusExceptions.VetoException: # or something--invalidscript exception?
                
                # set error info
                
                self._validity = VALIDITY_INVALID
                
                return False
                
            except Exception as e:
                
                # set error info
                
                self._validity = VALIDITY_INVALID
                
                return False
                
            
        
        return True
        
    
    def GetRequiredCredentials( self ):
        
        required_creds = []
        
        for step in self._login_steps:
            
            required_creds.extend( step.GetRequiredCredentials() ) # user facing name : string match
            
        
        return required_creds
        
    
LOGIN_PARAMETER_TYPE_PARAMETER = 0
LOGIN_PARAMETER_TYPE_COOKIE = 1
LOGIN_PARAMETER_TYPE_HEADER = 2

# make this serialisable
class LoginStep( object ):
    
    def __init__( self ):
        
        self._method = None # get/post
        self._url = 'blah' # maybe this should be split up more?
        
        self._statics = [] # type | arg name | string
        
        self._credentials = [] # type | user-facing name (unique) | arg name | string match
        
        self._temps = [] # type | arg name
        
        self._expected_cookies = [] # name | string match
        
        self._veto_scripts = [] # list of scripts that can veto
        
        self._temp_variable_scripts = [] # name | script that produces a single bit of text or vetoes
        
    
    def Start( self, controller, credentials, temp_variables ):
        
        # construct the url, failing if creds or temps missing
        
        # hit the url, failing on connection fault or whatever
        
        # throw the response at veto parsing gubbins, failing appropriately
        
        # throw the response at variable parsing gubbins, failing appropriately
        
        pass
        
    

