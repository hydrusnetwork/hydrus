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
    if re.search( r'^[\d\.):]+$', domain ) is not None:
        
        return [ domain ]
        
    
    if domain == 'localhost':
        
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

def ConvertURLMatchesIntoAPIPairs( url_matches ):
    
    pairs = []
    
    for url_match in url_matches:
        
        if not url_match.UsesAPIURL():
            
            continue
            
        
        api_url = url_match.GetAPIURL( url_match.GetExampleURL() )
        
        for other_url_match in url_matches:
            
            if other_url_match == url_match:
                
                continue
                
            
            if other_url_match.Matches( api_url ):
                
                pairs.append( ( url_match, other_url_match ) )
                
            
        
    
    return pairs
    
def ConvertURLIntoDomain( url ):
    
    parser_result = urlparse.urlparse( url )
    
    if parser_result.scheme == '':
        
        raise HydrusExceptions.URLMatchException( 'URL "' + url + '" was not recognised--did you forget the http or https?' )
        
    
    if parser_result.netloc == '':
        
        raise HydrusExceptions.URLMatchException( 'URL "' + url + '" was not recognised--is it missing a domain?' )
        
    
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
    SERIALISABLE_VERSION = 3
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self.engine = None
        
        self._url_matches = HydrusSerialisable.SerialisableList()
        self._parsers = HydrusSerialisable.SerialisableList()
        self._network_contexts_to_custom_header_dicts = collections.defaultdict( dict )
        
        self._url_match_keys_to_display = set()
        self._url_match_keys_to_parser_keys = HydrusSerialisable.SerialisableBytesDictionary()
        
        self._domains_to_url_matches = collections.defaultdict( list )
        
        self._parser_keys_to_parsers = {}
        
        self._dirty = False
        
        self._lock = threading.Lock()
        
        self._RecalcCache()
        
    
    def _GetParser( self, url_match ):
        
        url_type = url_match.GetURLType()
        url_match_key = url_match.GetMatchKey()
        
        parser_key = None
        
        if url_match_key in self._url_match_keys_to_parser_keys:
            
            parser_key = self._url_match_keys_to_parser_keys[ url_match_key ]
            
            if parser_key is not None and parser_key in self._parser_keys_to_parsers:
                
                return self._parser_keys_to_parsers[ parser_key ]
                
            
        
        return None
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_url_matches = self._url_matches.GetSerialisableTuple()
        serialisable_url_match_keys_to_display = [ url_match_key.encode( 'hex' ) for url_match_key in self._url_match_keys_to_display ]
        serialisable_url_match_keys_to_parser_keys = self._url_match_keys_to_parser_keys.GetSerialisableTuple()
        serialisable_parsers = self._parsers.GetSerialisableTuple()
        serialisable_network_contexts_to_custom_header_dicts = [ ( network_context.GetSerialisableTuple(), custom_header_dict.items() ) for ( network_context, custom_header_dict ) in self._network_contexts_to_custom_header_dicts.items() ]
        
        return ( serialisable_url_matches, serialisable_url_match_keys_to_display, serialisable_url_match_keys_to_parser_keys, serialisable_parsers, serialisable_network_contexts_to_custom_header_dicts )
        
    
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
        
        ( serialisable_url_matches, serialisable_url_match_keys_to_display, serialisable_url_match_keys_to_parser_keys, serialisable_parsers, serialisable_network_contexts_to_custom_header_dicts ) = serialisable_info
        
        self._url_matches = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_url_matches )
        
        self._url_match_keys_to_display = { serialisable_url_match_key.decode( 'hex' ) for serialisable_url_match_key in serialisable_url_match_keys_to_display }
        self._url_match_keys_to_parser_keys = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_url_match_keys_to_parser_keys )
        
        self._parsers = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_parsers )
        
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
        
        # also, put more 'precise' URL types above more typically permissive, in the order:
        # file
        # post
        # gallery
        # watchable
        # sorting in reverse, so higher number means more precise
        
        def key( u_m ):
            
            u_t = u_m.GetURLType()
            
            if u_t == HC.URL_TYPE_FILE:
                
                u_t_precision_value = 2
                
            elif u_t == HC.URL_TYPE_POST:
                
                u_t_precision_value = 1
                
            else:
                
                u_t_precision_value = 0
                
            
            u_e = u_m.GetExampleURL()
            
            return ( u_t_precision_value, u_e.count( '/' ), u_e.count( '=' ) )
            
        
        for url_matches in self._domains_to_url_matches.values():
            
            url_matches.sort( key = key, reverse = True )
            
        
        self._parser_keys_to_parsers = {}
        
        for parser in self._parsers:
            
            self._parser_keys_to_parsers[ parser.GetParserKey() ] = parser
            
        
    
    def _SetDirty( self ):
        
        self._dirty = True
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( serialisable_url_matches, serialisable_network_contexts_to_custom_header_dicts ) = old_serialisable_info
            
            url_matches = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_url_matches )
            
            url_match_names_to_display = {}
            url_match_names_to_page_parser_keys = HydrusSerialisable.SerialisableBytesDictionary()
            url_match_names_to_gallery_parser_keys = HydrusSerialisable.SerialisableBytesDictionary()
            
            for url_match in url_matches:
                
                name = url_match.GetName()
                
                if url_match.IsPostURL():
                    
                    url_match_names_to_display[ name ] = True
                    
                    url_match_names_to_page_parser_keys[ name ] = None
                    
                
                if url_match.IsGalleryURL() or url_match.IsWatchableURL():
                    
                    url_match_names_to_gallery_parser_keys[ name ] = None
                    
                
            
            serialisable_url_match_names_to_display = url_match_names_to_display.items()
            serialisable_url_match_names_to_page_parser_keys = url_match_names_to_page_parser_keys.GetSerialisableTuple()
            serialisable_url_match_names_to_gallery_parser_keys = url_match_names_to_gallery_parser_keys.GetSerialisableTuple()
            
            new_serialisable_info = ( serialisable_url_matches, serialisable_url_match_names_to_display, serialisable_url_match_names_to_page_parser_keys, serialisable_url_match_names_to_gallery_parser_keys, serialisable_network_contexts_to_custom_header_dicts )
            
            return ( 2, new_serialisable_info )
            
        
        if version == 2:
            
            ( serialisable_url_matches, serialisable_url_match_names_to_display, serialisable_url_match_names_to_page_parser_keys, serialisable_url_match_names_to_gallery_parser_keys, serialisable_network_contexts_to_custom_header_dicts ) = old_serialisable_info
            
            parsers = HydrusSerialisable.SerialisableList()
            
            serialisable_parsing_parsers = parsers.GetSerialisableTuple()
            
            url_match_names_to_display = dict( serialisable_url_match_names_to_display )
            
            url_match_keys_to_display = []
            
            url_match_names_to_gallery_parser_keys = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_url_match_names_to_gallery_parser_keys )
            url_match_names_to_page_parser_keys = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_url_match_names_to_page_parser_keys )
            
            url_match_keys_to_parser_keys = HydrusSerialisable.SerialisableBytesDictionary()
            
            url_matches = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_url_matches )
            
            for url_match in url_matches:
                
                url_match_key = url_match.GetMatchKey()
                
                name = url_match.GetName()
                
                if name in url_match_names_to_display and url_match_names_to_display[ name ]:
                    
                    url_match_keys_to_display.append( url_match_key )
                    
                
            
            serialisable_url_matches = url_matches.GetSerialisableTuple() # added random key this week, so save these changes back again!
            
            serialisable_url_match_keys_to_display = [ url_match_key.encode( 'hex' ) for url_match_key in url_match_keys_to_display ]
            
            serialisable_url_match_keys_to_parser_keys = url_match_keys_to_parser_keys.GetSerialisableTuple()
            
            new_serialisable_info = ( serialisable_url_matches, serialisable_url_match_keys_to_display, serialisable_url_match_keys_to_parser_keys, serialisable_parsing_parsers, serialisable_network_contexts_to_custom_header_dicts )
            
            return ( 3, new_serialisable_info )
            
        
    
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
                    
                    url_match_key = url_match.GetMatchKey()
                    
                    if url_match.IsPostURL() and url_match_key in self._url_match_keys_to_display:
                        
                        url_match_name = url_match.GetName()
                        
                        url_tuples.append( ( url_match_name, url ) )
                        
                    
                
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
            
        
    
    def GetParser( self, url ):
        
        with self._lock:
            
            url_match = self._GetURLMatch( url )
            
            if url_match is None:
                
                return None
                
            
            parser = self._GetParser( url_match )
            
            return parser
            
        
    
    def GetParsers( self ):
        
        with self._lock:
            
            return list( self._parsers )
            
        
    
    def GetURLMatches( self ):
        
        with self._lock:
            
            return list( self._url_matches )
            
        
    
    def GetURLMatchLinks( self ):
        
        with self._lock:
            
            return ( set( self._url_match_keys_to_display ), dict( self._url_match_keys_to_parser_keys ) )
            
        
    
    def GetURLParseCapability( self, url ):
        
        with self._lock:
            
            url_match = self._GetURLMatch( url )
            
            if url_match is None:
                
                return ( HC.URL_TYPE_UNKNOWN, 'unknown url', False )
                
            
            url_type = url_match.GetURLType()
            match_name = url_match.GetName()
            
            parser_url_match = url_match
            
            while parser_url_match.UsesAPIURL():
                
                api_url = parser_url_match.GetAPIURL( url )
                
                parser_url_match = self._GetURLMatch( api_url )
                
                if parser_url_match is None:
                    
                    break
                    
                
            
            if parser_url_match is None:
                
                can_parse = False
                
            else:
                
                parser = self._GetParser( parser_url_match )
                
                if parser is None:
                    
                    can_parse = False
                    
                else:
                    
                    can_parse = True
                    
                
            
        
        return ( url_type, match_name, can_parse )
        
    
    def GetURLToFetchAndParser( self, url ):
        
        with self._lock:
            
            url_match = self._GetURLMatch( url )
            
            url = url_match.Normalise( url )
            
            if url_match is None:
                
                return ( url, None )
                
            
            fetch_url = url
            parser_url_match = url_match
            
            while parser_url_match.UsesAPIURL():
                
                fetch_url = parser_url_match.GetAPIURL( url )
                
                parser_url_match = self._GetURLMatch( fetch_url )
                
                if parser_url_match is None:
                    
                    break
                    
                
            
            if parser_url_match is None:
                
                parser = None
                
            else:
                
                parser = self._GetParser( parser_url_match )
                
            
        
        return ( fetch_url, parser )
        
    
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
            
        
    
    def SetParsers( self, parsers ):
        
        with self._lock:
            
            self._parsers = HydrusSerialisable.SerialisableList()
            
            self._parsers.extend( parsers )
            
            # delete orphans
            
            parser_keys = { parser.GetParserKey() for parser in parsers }
            
            deletee_url_match_keys = set()
            
            for ( url_match_key, parser_key ) in self._url_match_keys_to_parser_keys.items():
                
                if parser_key not in parser_keys:
                    
                    deletee_url_match_keys.add( url_match_key )
                    
                
            
            for deletee_url_match_key in deletee_url_match_keys:
                
                del self._url_match_keys_to_parser_keys[ deletee_url_match_key ]
                
            
            #
            
            self._RecalcCache()
            
            self._SetDirty()
            
        
    
    def SetURLMatches( self, url_matches ):
        
        with self._lock:
            
            # add new post url matches to the yes display set
            
            old_url_match_keys = { url_match.GetMatchKey() for url_match in self._url_matches if url_match.IsPostURL() }
            url_match_keys = { url_match.GetMatchKey() for url_match in url_matches if url_match.IsPostURL() }
            
            added_url_match_keys = url_match_keys.difference( old_url_match_keys )
            
            self._url_match_keys_to_display.update( added_url_match_keys )
            
            #
            
            self._url_matches = HydrusSerialisable.SerialisableList()
            
            self._url_matches.extend( url_matches )
            
            #
            
            # delete orphans
            
            url_match_keys = { url_match.GetMatchKey() for url_match in url_matches }
            
            self._url_match_keys_to_display.intersection_update( url_match_keys )
            
            for deletee_key in set( self._url_match_keys_to_parser_keys.keys() ).difference( url_match_keys ):
                
                del self._url_match_keys_to_parser_keys[ deletee_key ]
                
            
            # any url matches that link to another via the API conversion will not be using parsers
            
            url_match_api_pairs = ConvertURLMatchesIntoAPIPairs( self._url_matches )
            
            for ( url_match_original, url_match_api ) in url_match_api_pairs:
                
                url_match_key = url_match_original.GetMatchKey()
                
                if url_match_key in self._url_match_keys_to_parser_keys:
                    
                    del self._url_match_keys_to_parser_keys[ url_match_key ]
                    
                
            
            self._RecalcCache()
            
            self._SetDirty()
            
        
    
    def SetURLMatchLinks( self, url_match_keys_to_display, url_match_keys_to_parser_keys ):
        
        with self._lock:
            
            self._url_match_keys_to_display = set()
            self._url_match_keys_to_parser_keys = HydrusSerialisable.SerialisableBytesDictionary()
            
            self._url_match_keys_to_display.update( url_match_keys_to_display )
            self._url_match_keys_to_parser_keys.update( url_match_keys_to_parser_keys )
            
            self._SetDirty()
            
        
    
    def TryToLinkURLMatchesAndParsers( self ):
        
        with self._lock:
            
            new_url_match_keys_to_parser_keys = NetworkDomainManager.STATICLinkURLMatchesAndParsers( self._url_matches, self._parsers, self._url_match_keys_to_parser_keys )
            
            self._url_match_keys_to_parser_keys.update( new_url_match_keys_to_parser_keys )
            
            self._SetDirty()
            
        
    
    @staticmethod
    def STATICLinkURLMatchesAndParsers( url_matches, parsers, existing_url_match_keys_to_parser_keys ):
        
        new_url_match_keys_to_parser_keys = {}
        
        for url_match in url_matches:
            
            api_pairs = ConvertURLMatchesIntoAPIPairs( url_matches )
            
            # anything that goes to an api url will be parsed by that api's parser--it can't have its own
            api_pair_unparsable_url_matches = set()
            
            for ( a, b ) in api_pairs:
                
                api_pair_unparsable_url_matches.add( a )
                
            
            #
            
            listctrl_data = []
            
            for url_match in url_matches:
                
                if not url_match.IsParsable() or url_match in api_pair_unparsable_url_matches:
                    
                    continue
                    
                
                if not url_match.IsWatchableURL(): # only starting with the thread watcher atm
                    
                    continue
                    
                
                url_match_key = url_match.GetMatchKey()
                
                if url_match_key in existing_url_match_keys_to_parser_keys:
                    
                    continue
                    
                
                for parser in parsers:
                    
                    example_urls = parser.GetExampleURLs()
                    
                    if True in ( url_match.Matches( example_url ) for example_url in example_urls ):
                        
                        new_url_match_keys_to_parser_keys[ url_match_key ] = parser.GetParserKey()
                        
                        break
                        
                    
                
            
        
        return new_url_match_keys_to_parser_keys
        
    
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
    SERIALISABLE_VERSION = 2
    
    def __init__( self, name, url_match_key = None, url_type = None, preferred_scheme = 'https', netloc = 'hostname.com', allow_subdomains = False, keep_subdomains = False, path_components = None, parameters = None, api_lookup_converter = None, example_url = 'https://hostname.com/post/page.php?id=123456&s=view' ):
        
        if url_match_key is None:
            
            url_match_key = HydrusData.GenerateKey()
            
        
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
            
        
        if api_lookup_converter is None:
            
            api_lookup_converter = ClientParsing.StringConverter( example_string = 'https://hostname.com/post/page.php?id=123456&s=view' )
            
        
        # if the args are not serialisable stuff, lets overwrite here
        
        path_components = HydrusSerialisable.SerialisableList( path_components )
        parameters = HydrusSerialisable.SerialisableDictionary( parameters )
        
        HydrusSerialisable.SerialisableBaseNamed.__init__( self, name )
        
        self._url_match_key = url_match_key
        self._url_type = url_type
        self._preferred_scheme = preferred_scheme
        self._netloc = netloc
        self._allow_subdomains = allow_subdomains
        self._keep_subdomains = keep_subdomains
        self._path_components = path_components
        self._parameters = parameters
        self._api_lookup_converter = api_lookup_converter
        
        self._example_url = example_url
        
    
    def _ClipNetLoc( self, netloc ):
        
        if self._keep_subdomains:
            
            # for domains like artistname.website.com, where removing the subdomain may break the url, we leave it alone
            
            pass
            
        else:
            
            # for domains like mediaserver4.website.com, where multiple subdomains serve the same content as the larger site
            
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
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_url_match_key = self._url_match_key.encode( 'hex' )
        serialisable_path_components = self._path_components.GetSerialisableTuple()
        serialisable_parameters = self._parameters.GetSerialisableTuple()
        serialisable_api_lookup_converter = self._api_lookup_converter.GetSerialisableTuple()
        
        return ( serialisable_url_match_key, self._url_type, self._preferred_scheme, self._netloc, self._allow_subdomains, self._keep_subdomains, serialisable_path_components, serialisable_parameters, serialisable_api_lookup_converter, self._example_url )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_url_match_key, self._url_type, self._preferred_scheme, self._netloc, self._allow_subdomains, self._keep_subdomains, serialisable_path_components, serialisable_parameters, serialisable_api_lookup_converter, self._example_url ) = serialisable_info
        
        self._url_match_key = serialisable_url_match_key.decode( 'hex' )
        self._path_components = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_path_components )
        self._parameters = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_parameters )
        self._api_lookup_converter = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_api_lookup_converter )
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( url_type, preferred_scheme, netloc, allow_subdomains, keep_subdomains, serialisable_path_components, serialisable_parameters, example_url ) = old_serialisable_info
            
            url_match_key = HydrusData.GenerateKey()
            
            serialisable_url_match_key = url_match_key.encode( 'hex' )
            
            api_lookup_converter = ClientParsing.StringConverter( example_string = example_url )
            
            serialisable_api_lookup_converter = api_lookup_converter.GetSerialisableTuple()
            
            new_serialisable_info = ( serialisable_url_match_key, url_type, preferred_scheme, netloc, allow_subdomains, keep_subdomains, serialisable_path_components, serialisable_parameters, serialisable_api_lookup_converter, example_url )
            
            return ( 2, new_serialisable_info )
            
        
    
    def GetAPIURL( self, url ):
        
        return self._api_lookup_converter.Convert( url )
        
    
    def GetDomain( self ):
        
        return ConvertDomainIntoSecondLevelDomain( HydrusData.ToByteString( self._netloc ) )
        
    
    def GetExampleURL( self ):
        
        return self._example_url
        
    
    def GetMatchKey( self ):
        
        return self._url_match_key
        
    
    def GetURLType( self ):
        
        return self._url_type
        
    
    def IsGalleryURL( self ):
        
        return self._url_type == HC.URL_TYPE_GALLERY
        
    
    def IsParsable( self ):
        
        return self._url_type in ( HC.URL_TYPE_POST, HC.URL_TYPE_GALLERY, HC.URL_TYPE_WATCHABLE )
        
    
    def IsPostURL( self ):
        
        return self._url_type == HC.URL_TYPE_POST
        
    
    def IsWatchableURL( self ):
        
        return self._url_type == HC.URL_TYPE_WATCHABLE
        
    
    def Matches( self, url ):
        
        try:
            
            self.Test( url )
            
            return True
            
        except HydrusExceptions.URLMatchException:
            
            return False
            
        
    
    def Normalise( self, url ):
        
        p = urlparse.urlparse( url )
        
        scheme = self._preferred_scheme
        params = ''
        fragment = ''
        
        # gallery urls we don't want to clip stuff, but we do want to flip to https
        
        if self._url_type in ( HC.URL_TYPE_FILE, HC.URL_TYPE_POST ):
            
            netloc = self._ClipNetLoc( p.netloc )
            path = self._ClipPath( p.path )
            query = self._ClipQuery( p.query )
            
        else:
            
            netloc = p.netloc
            path = p.path
            query = p.query
            
        
        r = urlparse.ParseResult( scheme, netloc, path, params, query, fragment )
        
        return r.geturl()
        
    
    def RegenMatchKey( self ):
        
        self._url_match_key = HydrusData.GenerateKey()
        
    
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
                
                raise HydrusExceptions.URLMatchException( HydrusData.ToUnicode( e ) )
                
            
        
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
                
                raise HydrusExceptions.URLMatchException( HydrusData.ToUnicode( e ) )
                
            
        
    
    def ToTuple( self ):
        
        return ( self._url_type, self._preferred_scheme, self._netloc, self._allow_subdomains, self._keep_subdomains, self._path_components, self._parameters, self._api_lookup_converter, self._example_url )
        
    
    def UsesAPIURL( self ):
        
        return self._api_lookup_converter.MakesChanges()
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_URL_MATCH ] = URLMatch

