import ClientConstants as CC
import ClientParsing
import ClientThreading
import collections
import HydrusConstants as HC
import HydrusGlobals as HG
import HydrusData
import HydrusExceptions
import HydrusSerialisable
import threading
import time
import urlparse

def ConvertDomainIntoAllApplicableDomains( domain ):
    
    domains = []
    
    while domain.count( '.' ) > 0:
        
        # let's discard www.blah.com so we don't end up tracking it separately to blah.com--there's not much point!
        startswith_www = domain.count( '.' ) > 1 and domain.startswith( 'www' )
        
        if not startswith_www:
            
            domains.append( domain )
            
        
        domain = '.'.join( domain.split( '.' )[1:] ) # i.e. strip off the leftmost subdomain maps.google.com -> google.com
        
    
    return domains
    
def ConvertURLIntoDomain( url ):
    
    parser_result = urlparse.urlparse( url )
    
    domain = HydrusData.ToByteString( parser_result.netloc )
    
    return domain
    
VALID_DENIED = 0
VALID_APPROVED = 1
VALID_UNKNOWN = 2
# this should do network_contexts->user-agent as well, with some kind of approval system in place
    # approval needs a new queue in the network engine. this will eventually test downloader validity and so on. failable at that stage
    # user-agent info should be exportable/importable on the ui as well
# eventually extend this to do urlmatch->downloader_key, I think.
# hence we'll be able to do some kind of dnd_url->new thread watcher page
# hide urls on media viewer based on domain
# decide whether we want to add this to the dirtyobjects loop, and it which case, if anything is appropriate to store in the db separately
  # hence making this a serialisableobject itself.
class NetworkDomainManager( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_BANDWIDTH_MANAGER
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self.engine = None
        
        self._url_matches = HydrusSerialisable.SerialisableList()
        self._network_contexts_to_custom_headers = {}
        
        self._domains_to_url_matches = collections.defaultdict( list )
        
        self._dirty = False
        
        self._lock = threading.Lock()
        
        self._RecalcCache()
        
    
    def _GetURLMatch( self, url ):
        
        domain = ConvertURLIntoDomain( url )
        
        if domain in self._domains_to_url_matches:
            
            url_matches = self._domains_to_url_matches[ domain ]
            
            # it would be nice to somehow sort these based on descending complexity
            # maybe by length of example url
            # in this way, url matches can have overlapping desmaign
            # e.g. 'post url' vs 'post url, manga subpage'
            
            for url_match in url_matches:
                
                ( result_bool, result_reason ) = url_match.Test( url )
                
                if result_bool:
                    
                    return url_match
                    
                
            
        
        return None
        
    
    def _RecalcCache( self ):
        
        self._domains_to_url_matches = collections.defaultdict( list )
        
        for url_match in self._url_matches:
            
            domain = url_match.GetDomain()
            
            self._domains_to_url_matches[ domain ].append( url_match )
            
        
    
    def _SetDirty( self ):
        
        self._dirty = True
        
    
    def CanValidateInPopup( self, network_contexts ):
        
        # we can always do this for headers
        
        return True
        
    
    def GenerateValidationProcess( self, network_contexts ):
        
        # generate a process that will, when threadcalled maybe with .Start() , ask the user, one after another, all the key-value pairs
        # Should (network context) apply "(key)" header "(value)"?
        # Reason given is: "You need this to make it work lol."
        # once all the yes/nos are set, update db, reinitialise domain manager, set IsDone to true.
        
        pass
        
    
    def GetCustomHeaders( self, network_contexts ):
        
        keys_to_values = {}
        
        with self._lock:
            
            pass
            
            # good order is global = least powerful, which I _think_ is how these come.
            # e.g. a site User-Agent should overwrite a global default
            
        
        return keys_to_values
        
    
    def GetDownloader( self, url ):
        
        with self._lock:
            
            # this might be better as getdownloaderkey, but we'll see how it shakes out
            # might also be worth being a getifhasdownloader
            
            # match the url to a url_match, then lookup that in a 'this downloader can handle this url_match type' dict that we'll manage
            
            pass
            
        
    
    def IsValid( self, network_contexts ):
        
        # for now, let's say that denied headers are simply not added, not that they invalidate a query
        
        for network_context in network_contexts:
            
            if network_context in self._network_contexts_to_custom_headers:
                
                custom_headers = self._network_contexts_to_custom_headers[ network_context ]
                
                for ( key, value, approved, reason ) in custom_headers:
                    
                    if approved == VALID_UNKNOWN:
                        
                        return False
                        
                    
                
            
        
        return True
        
    
    def NormaliseURL( self, url ):
        
        # call this before an entry into a seed cache or the db
        # use it in the dialog to review mass db-level changes
        
        with self._lock:
            
            url_match = self._GetURLMatch( url )
            
            if url_match is None:
                
                return url
                
            
            normalised_url = url_match.Normalise( url )
            
            return normalised_url
            
        
    
    def SetClean( self ):
        
        with self._lock:
            
            self._dirty = False
            
        
    
    def SetHeaderValidation( self, network_context, key, approved ):
        
        with self._lock:
            
            custom_headers = self._network_contexts_to_custom_headers[ network_context ]
            
            
            
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_DOMAIN_MANAGER ] = NetworkDomainManager

class DomainValidationProcess( object ):
    
    def __init__( self, domain_manager, header_tuples ):
        
        self._domain_manager = domain_manager
        
        self._header_tuples = header_tuples
        
        self._is_done = False
        
    
    def IsDone( self ):
        
        return self._is_done
        
    
    def Start( self ):
        
        try:
            
            results = []
            
            for ( network_context, key, value, approval_reason ) in self._header_tuples:
                
                job_key = ClientThreading.JobKey()
                
                # generate question
                question = 'intro text ' + approval_reason
                
                job_key.SetVariable( 'popup_yes_no_question', question )
                
                # pub it
                
                result = job_key.GetIfHasVariable( 'popup_yes_no_answer' )
                
                while result is None:
                    
                    if HG.view_shutdown:
                        
                        return
                        
                    
                    time.sleep( 0.25 )
                    
                
                if result:
                    
                    approved = VALID_APPROVED
                    
                else:
                    
                    approved = VALID_DENIED
                    
                
                self._domain_manager.SetHeaderValidation( network_context, key, approved )
                
            
        finally:
            
            self._is_done = True
            
        
    
# make this serialisable--maybe with name as the name of a named serialisable
# __hash__ for name? not sure
# maybe all serialisable should return __hash__ of ( type, name ) if they don't already
# that might lead to problems elsewhere, so careful
class URLMatch( HydrusSerialisable.SerialisableBaseNamed ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_URL_MATCH
    SERIALISABLE_VERSION = 1
    
    def __init__( self, name, preferred_scheme = 'https', netloc = 'hostname.com', subdomain_is_important = False, path_components = None, parameters = None, example_url = 'https://hostname.com/post/page.php?id=123456&s=view' ):
        
        if path_components is None:
            
            path_components = HydrusSerialisable.SerialisableList()
            
            path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'post', example_string = 'post' ) )
            path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'page.php', example_string = 'page.php' ) )
            
        
        if parameters is None:
            
            parameters = HydrusSerialisable.SerialisableDictionary()
            
            parameters[ 's' ] = ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'view', example_string = 'view' )
            parameters[ 'id' ] = ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FLEXIBLE, match_value = ClientParsing.NUMERIC, example_string = '123456' )
            
        
        # an edit dialog panel for this that has example url and testing of current values
        # a parent panel or something that lists all current urls in the db that match and how they will be clipped, is this ok? kind of thing.
        
        HydrusSerialisable.SerialisableBaseNamed.__init__( self, name )
        
        self._preferred_scheme = preferred_scheme
        self._netloc = netloc
        self._subdomain_is_important = subdomain_is_important
        self._path_components = path_components
        self._parameters = parameters
        
        self._example_url = example_url
        
    
    def _ClipNetLoc( self, netloc ):
        
        if self._subdomain_is_important:
            
            # for domains like artistname.website.com, where removing the subdomain may break the url, we leave it alone
            
            pass
            
        else:
            
            # for domains like mediaserver4.website.com, where multiple subdomains serve the same content as the larger site
            # if the main site doesn't deliver the same content as the subdomain, then subdomain_is_important
            
            netloc = self._netloc
            
        
        return netloc
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_path_components = self._path_components.GetSerialisableTuple()
        serialisable_parameters = self._parameters.GetSerialisableTuple()
        
        return ( self._preferred_scheme, self._netloc, self._subdomain_is_important, serialisable_path_components, serialisable_parameters, self._example_url )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._preferred_scheme, self._netloc, self._subdomain_is_important, serialisable_path_components, serialisable_parameters, self._example_url ) = serialisable_info
        
        self._path_components = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_path_components )
        self._parameters = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_parameters )
        
    
    def _ClipPath( self, path ):
        
        # /post/show/1326143/akunim-anthro-armband-armwear-clothed-clothing-fem
        
        while path.startswith( '/' ):
            
            path = path[ 1 : ]
            
        
        # post/show/1326143/akunim-anthro-armband-armwear-clothed-clothing-fem
        
        path_components = path.split( '/' )
        
        path = '/'.join( path_components[ : len( self._path_components ) ] )
        
        # post/show/1326143
        
        if len( path ) > 0:
            
            path = '/' + path
            
        
        # /post/show/1326143
        
        return path
        
    
    def _ClipQuery( self, query ):
        
        valid_parameters = []
        
        for ( key, value ) in urlparse.parse_qsl( query ):
            
            if key in self._parameters:
                
                valid_parameters.append( ( key, value ) )
                
            
        
        valid_parameters.sort()
        
        query = '&'.join( ( key + '=' + value for ( key, value ) in valid_parameters ) )
        
        return query
        
    
    def GetDomain( self ):
        
        return ConvertURLIntoDomain( self._example_url )
        
    
    def Normalise( self, url ):
        
        p = urlparse.urlparse( url )
        
        scheme = self._preferred_scheme
        netloc = self._ClipNetLoc( p.netloc )
        path = self._ClipPath( p.path )
        params = ''
        query = self._ClipQuery( p.query )
        fragment = ''
        
        r = urlparse.ParseResult( scheme, netloc, path, params, query, fragment )
        
        return r.geturl()
        
    
    def Test( self, url ):
        
        # split the url into parts according to urlparse
        p = urlparse.urlparse( url )
        
        # test p.netloc with netloc, taking subdomain_is_important into account
        
        url_path = p.path
        
        while url_path.startswith( '/' ):
            
            url_path = url_path[ 1 : ]
            
        
        url_path_components = p.path.split( '/' )
        
        if len( url_path_components ) < len( self._path_components ):
            
            return ( False, p.path + ' did not have ' + str( len( self._path_components ) ) + ' components' )
            
        
        for ( url_path_component, expected_path_component ) in zip( url_path_components, self._path_components ):
            
            ( bool_result, reason ) = expected_path_component.Test( url_path_component )
            
            if not bool_result:
                
                return ( bool_result, reason )
                
            
        
        url_parameters_list = urlparse.parse_qsl( p.query )
        
        if len( url_parameters_list ) < len( self._parameters ):
            
            return ( False, p.query + ' did not have ' + str( len( self._parameters ) ) + ' value pairs' )
            
        
        for ( key, url_value ) in url_parameters_list:
            
            if key not in self._parameters:
                
                return ( False, key + ' not found in ' + p.query )
                
            
            expected_value = self._parameters[ key ]
            
            ( bool_result, reason ) = expected_value.Test( url_value )
            
            if not bool_result:
                
                return ( bool_result, reason )
                
            
        
        return ( True, 'good' )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_URLS_IMPORT ] = URLMatch

