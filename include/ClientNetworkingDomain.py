import ClientConstants as CC
import ClientParsing
import ClientThreading
import collections
import HydrusConstants as HC
import HydrusGlobals as HG
import HydrusData
import HydrusExceptions
import HydrusSerialisable
import os
import re
import threading
import time
import urlparse

def ConvertDomainIntoAllApplicableDomains( domain ):
    
    # is an ip address, possibly with a port
    if re.search( '^[\d\.):]+$', domain ) is not None:
        
        return [ domain ]
        
    
    domains = []
    
    while domain.count( '.' ) > 0:
        
        # let's discard www.blah.com and www2.blah.com so we don't end up tracking it separately to blah.com--there's not much point!
        startswith_www = domain.count( '.' ) > 1 and domain.startswith( 'www' )
        
        if not startswith_www:
            
            domains.append( domain )
            
        
        domain = '.'.join( domain.split( '.' )[1:] ) # i.e. strip off the leftmost subdomain maps.google.com -> google.com
        
    
    return domains
    
def ConvertDomainIntoSecondLevelDomain( domain ):
    
    return ConvertDomainIntoAllApplicableDomains( domain )[-1]
    
def ConvertURLIntoDomain( url ):
    
    parser_result = urlparse.urlparse( url )
    
    domain = HydrusData.ToByteString( parser_result.netloc )
    
    return domain
    
def GetCookie( cookies, search_domain, name ):
    
    existing_domains = cookies.list_domains()
    
    for existing_domain in existing_domains:
        
        # blah.com is viewable by blah.com
        matches_exactly = existing_domain == search_domain
        
        # .blah.com is viewable by blah.com
        matches_dot = existing_domain == '.' + search_domain
        
        # .blah.com applies to subdomain.blah.com, blah.com does not
        valid_subdomain = existing_domain.startwith( '.' ) and search_domain.endswith( existing_domain )
        
        if matches_exactly or matches_dot or valid_subdomain:
            
            cookie_dict = cookies.get_dict( existing_domain )
            
            if name in cookie_dict:
                
                return cookie_dict[ name ]
                
            
        
    
    raise HydrusExceptions.DataMissing( 'Cookie ' + name + ' not found for domain ' + search_domain + '!' )
    
VALID_DENIED = 0
VALID_APPROVED = 1
VALID_UNKNOWN = 2

valid_str_lookup = {}

valid_str_lookup[ VALID_DENIED ] = 'denied'
valid_str_lookup[ VALID_APPROVED ] = 'approved'
valid_str_lookup[ VALID_UNKNOWN ] = 'unknown'

class NetworkDomainManager( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_DOMAIN_MANAGER
    SERIALISABLE_NAME = 'Domain Manager'
    SERIALISABLE_VERSION = 2
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self.engine = None
        
        self._url_matches = HydrusSerialisable.SerialisableList()
        self._network_contexts_to_custom_header_dicts = collections.defaultdict( dict )
        
        self._url_match_names_to_display = {}
        self._url_match_names_to_page_parsing_keys = HydrusSerialisable.SerialisableBytesDictionary()
        self._url_match_names_to_gallery_parsing_keys = HydrusSerialisable.SerialisableBytesDictionary()
        
        self._domains_to_url_matches = collections.defaultdict( list )
        
        self._dirty = False
        
        self._lock = threading.Lock()
        
        self._RecalcCache()
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_url_matches = self._url_matches.GetSerialisableTuple()
        serialisable_url_match_names_to_display = self._url_match_names_to_display.items()
        serialisable_url_match_names_to_page_parsing_keys = self._url_match_names_to_page_parsing_keys.GetSerialisableTuple()
        serialisable_url_match_names_to_gallery_parsing_keys = self._url_match_names_to_gallery_parsing_keys.GetSerialisableTuple()
        serialisable_network_contexts_to_custom_header_dicts = [ ( network_context.GetSerialisableTuple(), custom_header_dict.items() ) for ( network_context, custom_header_dict ) in self._network_contexts_to_custom_header_dicts.items() ]
        
        return ( serialisable_url_matches, serialisable_url_match_names_to_display, serialisable_url_match_names_to_page_parsing_keys, serialisable_url_match_names_to_gallery_parsing_keys, serialisable_network_contexts_to_custom_header_dicts )
        
    
    def _GetURLMatch( self, url ):
        
        domain = ConvertDomainIntoSecondLevelDomain( ConvertURLIntoDomain( url ) )
        
        if domain in self._domains_to_url_matches:
            
            url_matches = self._domains_to_url_matches[ domain ]
            
            for url_match in url_matches:
                
                try:
                    
                    url_match.Test( url )
                    
                    return url_match
                    
                except HydrusExceptions.URLMatchException:
                    
                    continue
                    
                
            
        
        return None
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_url_matches, serialisable_url_match_names_to_display, serialisable_url_match_names_to_page_parsing_keys, serialisable_url_match_names_to_gallery_parsing_keys, serialisable_network_contexts_to_custom_header_dicts ) = serialisable_info
        
        self._url_matches = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_url_matches )
        
        self._url_match_names_to_display = dict( serialisable_url_match_names_to_display )
        self._url_match_names_to_page_parsing_keys = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_url_match_names_to_page_parsing_keys )
        self._url_match_names_to_gallery_parsing_keys = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_url_match_names_to_gallery_parsing_keys )
        
        self._network_contexts_to_custom_header_dicts = collections.defaultdict( dict )
        
        for ( serialisable_network_context, custom_header_dict_items ) in serialisable_network_contexts_to_custom_header_dicts:
            
            network_context = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_network_context )
            custom_header_dict = dict( custom_header_dict_items )
            
            self._network_contexts_to_custom_header_dicts[ network_context ] = custom_header_dict
            
        
    
    def _RecalcCache( self ):
        
        self._domains_to_url_matches = collections.defaultdict( list )
        
        for url_match in self._url_matches:
            
            domain = url_match.GetDomain()
            
            self._domains_to_url_matches[ domain ].append( url_match )
            
        
        # we now sort them in descending complexity so that
        # post url/manga subpage
        # is before
        # post url
        
        def key( u_m ):
            
            return u_m.GetExampleURL().count( '/' )
            
        
        for url_matches in self._domains_to_url_matches.values():
            
            url_matches.sort( key = key, reverse = True )
            
        
    
    def _SetDirty( self ):
        
        self._dirty = True
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( serialisable_url_matches, serialisable_network_contexts_to_custom_header_dicts ) = old_serialisable_info
            
            url_matches = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_url_matches )
            
            url_match_names_to_display = {}
            url_match_names_to_page_parsing_keys = HydrusSerialisable.SerialisableBytesDictionary()
            url_match_names_to_gallery_parsing_keys = HydrusSerialisable.SerialisableBytesDictionary()
            
            for url_match in url_matches:
                
                name = url_match.GetName()
                
                if url_match.IsPostURL():
                    
                    url_match_names_to_display[ name ] = True
                    
                    url_match_names_to_page_parsing_keys[ name ] = None
                    
                
                if url_match.IsGalleryURL() or url_match.IsWatchableURL():
                    
                    url_match_names_to_gallery_parsing_keys[ name ] = None
                    
                
            
            serialisable_url_match_names_to_display = url_match_names_to_display.items()
            serialisable_url_match_names_to_page_parsing_keys = url_match_names_to_page_parsing_keys.GetSerialisableTuple()
            serialisable_url_match_names_to_gallery_parsing_keys = url_match_names_to_gallery_parsing_keys.GetSerialisableTuple()
            
            new_serialisable_info = ( serialisable_url_matches, serialisable_url_match_names_to_display, serialisable_url_match_names_to_page_parsing_keys, serialisable_url_match_names_to_gallery_parsing_keys, serialisable_network_contexts_to_custom_header_dicts )
            
            return ( 2, new_serialisable_info )
            
        
    
    def _UpdateURLMatchLinks( self ):
        
        for url_match in self._url_matches:
            
            name = url_match.GetName()
            
            if url_match.IsPostURL():
                
                if name not in self._url_match_names_to_display:
                    
                    self._url_match_names_to_display[ name ] = True
                    
                
                if name not in self._url_match_names_to_page_parsing_keys:
                    
                    self._url_match_names_to_page_parsing_keys[ name ] = None
                    
                
            
            if url_match.IsGalleryURL() or url_match.IsWatchableURL():
                
                if name not in self._url_match_names_to_gallery_parsing_keys:
                    
                    self._url_match_names_to_gallery_parsing_keys[ name ] = None
                    
                
            
        
    
    def CanValidateInPopup( self, network_contexts ):
        
        # we can always do this for headers
        
        return True
        
    
    def ConvertURLsToMediaViewerTuples( self, urls ):
        
        url_tuples = []
        
        with self._lock:
            
            for url in urls:
                
                url_match = self._GetURLMatch( url )
                
                if url_match is None:
                    
                    domain = ConvertURLIntoDomain( url )
                    
                    url_tuples.append( ( domain, url ) )
                    
                else:
                    
                    name = url_match.GetName()
                    
                    if url_match.IsPostURL() and name in self._url_match_names_to_display:
                        
                        if self._url_match_names_to_display[ name ]:
                            
                            url_tuples.append( ( name, url ) )
                            
                        
                    
                
                if len( url_tuples ) == 10:
                    
                    break
                    
                
            
        
        url_tuples.sort()
        
        return url_tuples
        
    
    def GenerateValidationPopupProcess( self, network_contexts ):
        
        with self._lock:
            
            header_tuples = []
            
            for network_context in network_contexts:
                
                if network_context in self._network_contexts_to_custom_header_dicts:
                    
                    custom_header_dict = self._network_contexts_to_custom_header_dicts[ network_context ]
                    
                    for ( key, ( value, approved, reason ) ) in custom_header_dict.items():
                        
                        if approved == VALID_UNKNOWN:
                            
                            header_tuples.append( ( network_context, key, value, reason ) )
                            
                        
                    
                
            
            process = DomainValidationPopupProcess( self, header_tuples )
            
            return process
            
        
    
    def GetDownloader( self, url ):
        
        with self._lock:
            
            # this might be better as getdownloaderkey, but we'll see how it shakes out
            # might also be worth being a getifhasdownloader
            
            # match the url to a url_match, then lookup that in a 'this downloader can handle this url_match type' dict that we'll manage
            
            pass
            
        
    
    def GetHeaders( self, network_contexts ):
        
        with self._lock:
            
            headers = {}
            
            for network_context in network_contexts:
                
                if network_context in self._network_contexts_to_custom_header_dicts:
                    
                    custom_header_dict = self._network_contexts_to_custom_header_dicts[ network_context ]
                    
                    for ( key, ( value, approved, reason ) ) in custom_header_dict.items():
                        
                        if approved == VALID_APPROVED:
                            
                            headers[ key ] = value
                            
                        
                    
                
            
            return headers
            
        
    
    def GetNetworkContextsToCustomHeaderDicts( self ):
        
        with self._lock:
            
            return dict( self._network_contexts_to_custom_header_dicts )
            
        
    
    def GetURLMatches( self ):
        
        with self._lock:
            
            return list( self._url_matches )
            
        
    
    def GetURLMatchLinks( self ):
        
        with self._lock:
            
            return ( dict( self._url_match_names_to_display ), dict( self._url_match_names_to_page_parsing_keys ), dict( self._url_match_names_to_gallery_parsing_keys ) )
            
        
    
    def Initialise( self ):
        
        self._RecalcCache()
        
    
    def IsDirty( self ):
        
        with self._lock:
            
            return self._dirty
            
        
    
    def IsValid( self, network_contexts ):
        
        # for now, let's say that denied headers are simply not added, not that they invalidate a query
        
        for network_context in network_contexts:
            
            if network_context in self._network_contexts_to_custom_header_dicts:
                
                custom_header_dict = self._network_contexts_to_custom_header_dicts[ network_context ]
                
                for ( value, approved, reason ) in custom_header_dict.values():
                    
                    if approved == VALID_UNKNOWN:
                        
                        return False
                        
                    
                
            
        
        return True
        
    
    def NormaliseURL( self, url ):
        
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
            
            if network_context in self._network_contexts_to_custom_header_dicts:
                
                custom_header_dict = self._network_contexts_to_custom_header_dicts[ network_context ]
                
                if key in custom_header_dict:
                    
                    ( value, old_approved, reason ) = custom_header_dict[ key ]
                    
                    custom_header_dict[ key ] = ( value, approved, reason )
                    
                
            
            self._SetDirty()
            
        
    
    def SetNetworkContextsToCustomHeaderDicts( self, network_contexts_to_custom_header_dicts ):
        
        with self._lock:
            
            self._network_contexts_to_custom_header_dicts = network_contexts_to_custom_header_dicts
            
            self._SetDirty()
            
        
    
    def SetURLMatches( self, url_matches ):
        
        with self._lock:
            
            self._url_matches = HydrusSerialisable.SerialisableList()
            
            self._url_matches.extend( url_matches )
            
            self._UpdateURLMatchLinks()
            
            self._RecalcCache()
            
            self._SetDirty()
            
        
    
    def SetURLMatchLinks( self, url_match_names_to_display, url_match_names_to_page_parsing_keys, url_match_names_to_gallery_parsing_keys ):
        
        with self._lock:
            
            self._url_match_names_to_display = {}
            self._url_match_names_to_page_parsing_keys = HydrusSerialisable.SerialisableBytesDictionary()
            self._url_match_names_to_gallery_parsing_keys = HydrusSerialisable.SerialisableBytesDictionary()
            
            self._url_match_names_to_display.update( url_match_names_to_display )
            self._url_match_names_to_page_parsing_keys.update( url_match_names_to_page_parsing_keys )
            self._url_match_names_to_gallery_parsing_keys.update( url_match_names_to_gallery_parsing_keys )
            
            self._SetDirty()
            
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_DOMAIN_MANAGER ] = NetworkDomainManager

class DomainValidationPopupProcess( object ):
    
    def __init__( self, domain_manager, header_tuples ):
        
        self._domain_manager = domain_manager
        
        self._header_tuples = header_tuples
        
        self._is_done = False
        
    
    def IsDone( self ):
        
        return self._is_done
        
    
    def Start( self ):
        
        try:
            
            results = []
            
            for ( network_context, key, value, reason ) in self._header_tuples:
                
                job_key = ClientThreading.JobKey()
                
                # generate question
                
                question = 'For the network context ' + network_context.ToUnicode() + ', can the client set this header?'
                question += os.linesep * 2
                question += key + ': ' + value
                question += os.linesep * 2
                question += reason
                
                job_key.SetVariable( 'popup_yes_no_question', question )
                
                HG.client_controller.pub( 'message', job_key )
                
                result = job_key.GetIfHasVariable( 'popup_yes_no_answer' )
                
                while result is None:
                    
                    if HG.view_shutdown:
                        
                        return
                        
                    
                    time.sleep( 0.25 )
                    
                    result = job_key.GetIfHasVariable( 'popup_yes_no_answer' )
                    
                
                if result:
                    
                    approved = VALID_APPROVED
                    
                else:
                    
                    approved = VALID_DENIED
                    
                
                self._domain_manager.SetHeaderValidation( network_context, key, approved )
                
            
        finally:
            
            self._is_done = True
            
        
    
class URLMatch( HydrusSerialisable.SerialisableBaseNamed ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_URL_MATCH
    SERIALISABLE_NAME = 'URL Match'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, name, url_type = None, preferred_scheme = 'https', netloc = 'hostname.com', allow_subdomains = False, keep_subdomains = False, path_components = None, parameters = None, example_url = 'https://hostname.com/post/page.php?id=123456&s=view' ):
        
        if url_type is None:
            
            url_type = HC.URL_TYPE_POST
            
        
        if path_components is None:
            
            path_components = HydrusSerialisable.SerialisableList()
            
            path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'post', example_string = 'post' ) )
            path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'page.php', example_string = 'page.php' ) )
            
        
        if parameters is None:
            
            parameters = HydrusSerialisable.SerialisableDictionary()
            
            parameters[ 's' ] = ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'view', example_string = 'view' )
            parameters[ 'id' ] = ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FLEXIBLE, match_value = ClientParsing.NUMERIC, example_string = '123456' )
            
        
        # if the args are not serialisable stuff, lets overwrite here
        
        path_components = HydrusSerialisable.SerialisableList( path_components )
        parameters = HydrusSerialisable.SerialisableDictionary( parameters )
        
        HydrusSerialisable.SerialisableBaseNamed.__init__( self, name )
        
        self._url_type = url_type
        self._preferred_scheme = preferred_scheme
        self._netloc = netloc
        self._allow_subdomains = allow_subdomains
        self._keep_subdomains = keep_subdomains
        self._path_components = path_components
        self._parameters = parameters
        
        self._example_url = example_url
        
    
    def _ClipNetLoc( self, netloc ):
        
        if self._keep_subdomains:
            
            # for domains like artistname.website.com, where removing the subdomain may break the url, we leave it alone
            
            pass
            
        else:
            
            # for domains like mediaserver4.website.com, where multiple subdomains serve the same content as the larger site
            
            netloc = self._netloc
            
        
        return netloc
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_path_components = self._path_components.GetSerialisableTuple()
        serialisable_parameters = self._parameters.GetSerialisableTuple()
        
        return ( self._url_type, self._preferred_scheme, self._netloc, self._allow_subdomains, self._keep_subdomains, serialisable_path_components, serialisable_parameters, self._example_url )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._url_type, self._preferred_scheme, self._netloc, self._allow_subdomains, self._keep_subdomains, serialisable_path_components, serialisable_parameters, self._example_url ) = serialisable_info
        
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
        
        return ConvertDomainIntoSecondLevelDomain( HydrusData.ToByteString( self._netloc ) )
        
    
    def GetExampleURL( self ):
        
        return self._example_url
        
    
    def GetURLType( self ):
        
        return self._url_type
        
    
    def IsGalleryURL( self ):
        
        return self._url_type == HC.URL_TYPE_GALLERY
        
    
    def IsPostURL( self ):
        
        return self._url_type == HC.URL_TYPE_POST
        
    
    def IsWatchableURL( self ):
        
        return self._url_type == HC.URL_TYPE_WATCHABLE
        
    
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
        
        p = urlparse.urlparse( url )
        
        if self._allow_subdomains:
            
            if p.netloc != self._netloc and not p.netloc.endswith( '.' + self._netloc ):
                
                raise HydrusExceptions.URLMatchException( p.netloc + ' (potentially excluding subdomains) did not match ' + self._netloc )
                
            
        else:
            
            if p.netloc != self._netloc:
                
                raise HydrusExceptions.URLMatchException( p.netloc + ' did not match ' + self._netloc )
                
            
        
        url_path = p.path
        
        while url_path.startswith( '/' ):
            
            url_path = url_path[ 1 : ]
            
        
        url_path_components = url_path.split( '/' )
        
        if len( url_path_components ) < len( self._path_components ):
            
            raise HydrusExceptions.URLMatchException( url_path + ' did not have ' + str( len( self._path_components ) ) + ' components' )
            
        
        for ( url_path_component, expected_path_component ) in zip( url_path_components, self._path_components ):
            
            try:
                
                expected_path_component.Test( url_path_component )
                
            except HydrusExceptions.StringMatchException as e:
                
                raise HydrusExceptions.URLMatchException( unicode( e ) )
                
            
        
        url_parameters_list = urlparse.parse_qsl( p.query )
        
        url_parameters = dict( url_parameters_list )
        
        if len( url_parameters ) < len( self._parameters ):
            
            raise HydrusExceptions.URLMatchException( p.query + ' did not have ' + str( len( self._parameters ) ) + ' value pairs' )
            
        
        for ( key, string_match ) in self._parameters.items():
            
            if key not in url_parameters:
                
                raise HydrusExceptions.URLMatchException( key + ' not found in ' + p.query )
                
            
            value = url_parameters[ key ]
            
            try:
                
                string_match.Test( value )
                
            except HydrusExceptions.StringMatchException as e:
                
                raise HydrusExceptions.URLMatchException( unicode( e ) )
                
            
        
    
    def ToTuple( self ):
        
        return ( self._url_type, self._preferred_scheme, self._netloc, self._allow_subdomains, self._keep_subdomains, self._path_components, self._parameters, self._example_url )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_URL_MATCH ] = URLMatch

