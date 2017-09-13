import ClientConstants as CC
import HydrusConstants as HC
import HydrusGlobals as HG
import HydrusData
import HydrusExceptions
import threading
import urlparse

# this should do network_contexts->user-agent as well, with some kind of approval system in place
    # user-agent info should be exportable/importable on the ui as well
# eventually extend this to do urlmatch->downloader, I think.
# hence we'll be able to do some kind of dnd_url->new thread watcher page
class DomainManager( object ):
    
    def __init__( self, controller ):
        
        self._controller = controller
        self._domains_to_url_matches = {}
        
        self._lock = threading.Lock()
        
        self._Initialise()
        
    
    def _Initialise( self ):
        
        self._domains_to_url_matches = {}
        
        # fetch them all from controller's db
        # figure out domain -> urlmatch for each entry based on example url
        
        pass
        
    
    def GetURLMatch( self, url ):
        
        with self._lock:
            
            domain = 'blah' # get top urldomain
            
            if domain in self._domains_to_url_matches:
                
                url_matches = self._domains_to_url_matches[ domain ]
                
                for url_match in url_matches:
                    
                    ( result_bool, result_reason ) = url_match.Test( url )
                    
                    if result_bool:
                        
                        return url_match
                        
                    
                
            
            return None
            
        
    
    def Reinitialise( self ):
        
        with self._lock:
            
            self._Initialise()
            
        
    
# make this serialisable--maybe with name as the name of a named serialisable
# __hash__ for name? not sure
# maybe all serialisable should return __hash__ of ( type, name ) if they don't already
# that might lead to problems elsewhere, so careful
class URLMatch( object ):
    
    def __init__( self ):
        
        # an edit dialog panel for this that has example url and testing of current values
        # a parent panel or something that lists all current urls in the db that match and how they will be clipped, is this ok? kind of thing.
        
        self._preferred_scheme = None
        self._netloc = None
        self._subdomain_is_important = False
        self._path_components = None
        self._parameters = {}
        
        self._name = None
        self._example_url = None
        
    
    def _ClipNetLoc( self, netloc ):
        
        if self._subdomain_is_important:
            
            # for domains like artistname.website.com, where removing the subdomain may break the url, we leave it alone
            
            pass
            
        else:
            
            # for domains like mediaserver4.website.com, where multiple subdomains serve the same content as the larger site
            # if the main site doesn't deliver the same content as the subdomain, then subdomain_is_important
            
            netloc = self._netloc
            
        
        return netloc
        
    
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
        
    
    def Clip( self, url ):
        
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
        
    
