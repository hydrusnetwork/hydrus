import ClientConstants as CC
import ClientParsing
import HydrusConstants as HC
import HydrusGlobals as HG
import HydrusData
import HydrusExceptions
import HydrusSerialisable
import threading
import urlparse

# this should do network_contexts->user-agent as well, with some kind of approval system in place
    # approval needs a new queue in the network engine. this will eventually test downloader validity and so on. failable at that stage
    # user-agent info should be exportable/importable on the ui as well
# eventually extend this to do urlmatch->downloader_key, I think.
# hence we'll be able to do some kind of dnd_url->new thread watcher page
# hide urls on media viewer based on domain
# decide whether we want to add this to the dirtyobjects loop, and it which case, if anything is appropriate to store in the db separately
  # hence making this a serialisableobject itself.
class DomainManager( object ):
    
    def __init__( self, controller ):
        
        self._controller = controller
        self._domains_to_url_matches = {}
        self._network_contexts_to_custom_headers = {} # user-agent here
        # ( header_key, header_value, approved, approval_reason )
        # approved is True for user created, None for imported and defaults
        
        self._lock = threading.Lock()
        
        self._Initialise()
        
    
    def _GetURLMatch( self, url ):
        
        domain = 'blah' # get top urldomain
        
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
        
    
    def _Initialise( self ):
        
        self._domains_to_url_matches = {}
        
        # fetch them all from controller's db
        # figure out domain -> urlmatch for each entry based on example url
        
        pass
        
    
    def CanApprove( self, network_contexts ):
        
        # if user selected false for any approval, return false
        # network job presumably throws a ValidationError at this point, which will cause any larger queue to pause.
        
        pass
        
    
    def DoApproval( self, network_contexts ):
        
        # if false on validity check, it presents the user with a yes/no popup with the approval_reason and waits
        
        pass
        
    
    def GetCustomHeaders( self, network_contexts ):
        
        with self._lock:
            
            pass
            
            # good order is global = least powerful, which I _think_ is how these come.
            
        
    
    def GetDownloader( self, url ):
        
        with self._lock:
            
            # this might be better as getdownloaderkey, but we'll see how it shakes out
            # might also be worth being a getifhasdownloader
            
            # match the url to a url_match, then lookup that in a 'this downloader can handle this url_match type' dict that we'll manage
            
            pass
            
        
    
    def NeedsApproval( self, network_contexts ):
        
        # this is called by the network engine in the new approval queue
        # if a job needs approval, it goes to a single step like the login one and waits, possibly failing.
        # checks for 'approved is None' on all ncs
        
        pass
        
    
    def NormaliseURL( self, url ):
        
        # call this before an entry into a seed cache or the db
        # use it in the dialog to review mass db-level changes
        
        with self._lock:
            
            url_match = self._GetURLMatch( url )
            
            if url_match is None:
                
                return url
                
            
            normalised_url = url_match.Normalise( url )
            
            return normalised_url
            
        
    
    def Reinitialise( self ):
        
        with self._lock:
            
            self._Initialise()
            
        
    
# make this serialisable--maybe with name as the name of a named serialisable
# __hash__ for name? not sure
# maybe all serialisable should return __hash__ of ( type, name ) if they don't already
# that might lead to problems elsewhere, so careful
class URLMatch( HydrusSerialisable.SerialisableBaseNamed ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_URL_MATCH
    SERIALISABLE_VERSION = 1
    
    def __init__( self, name, preferred_scheme = 'https', netloc = 'hostname.com', subdomain_is_important = False, path_components = None, parameters = None, example_url = 'https://hostname.com' ):
        
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
        
        self._preferred_scheme = 'https'
        self._netloc = 'hostname.com'
        self._subdomain_is_important = False
        self._path_components = HydrusSerialisable.SerialisableList()
        self._parameters = HydrusSerialisable.SerialisableDictionary()
        
        self._example_url = 'https://hostname.com/post/page.php?id=123456&s=view'
        
    
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

