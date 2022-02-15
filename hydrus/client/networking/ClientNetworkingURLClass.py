import typing
import urllib.parse

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusSerialisable

from hydrus.client import ClientStrings
from hydrus.client.networking import ClientNetworkingFunctions

GALLERY_INDEX_TYPE_PATH_COMPONENT = 0
GALLERY_INDEX_TYPE_PARAMETER = 1

SEND_REFERRAL_URL_ONLY_IF_PROVIDED = 0
SEND_REFERRAL_URL_NEVER = 1
SEND_REFERRAL_URL_CONVERTER_IF_NONE_PROVIDED = 2
SEND_REFERRAL_URL_ONLY_CONVERTER = 3

SEND_REFERRAL_URL_TYPES = [ SEND_REFERRAL_URL_ONLY_IF_PROVIDED, SEND_REFERRAL_URL_NEVER, SEND_REFERRAL_URL_CONVERTER_IF_NONE_PROVIDED, SEND_REFERRAL_URL_ONLY_CONVERTER ]

send_referral_url_string_lookup = {}

send_referral_url_string_lookup[ SEND_REFERRAL_URL_ONLY_IF_PROVIDED ] = 'send a referral url if available'
send_referral_url_string_lookup[ SEND_REFERRAL_URL_NEVER ] = 'never send a referral url'
send_referral_url_string_lookup[ SEND_REFERRAL_URL_CONVERTER_IF_NONE_PROVIDED ] = 'use the converter if no referral is available'
send_referral_url_string_lookup[ SEND_REFERRAL_URL_ONLY_CONVERTER ] = 'always use the converter referral url'

def ConvertURLClassesIntoAPIPairs( url_classes ):
    
    url_classes = list( url_classes )
    
    SortURLClassesListDescendingComplexity( url_classes )
    
    pairs = []
    
    for url_class in url_classes:
        
        if not url_class.UsesAPIURL():
            
            continue
            
        
        api_url = url_class.GetAPIURL( url_class.GetExampleURL() )
        
        for other_url_class in url_classes:
            
            if other_url_class == url_class:
                
                continue
                
            
            if other_url_class.Matches( api_url ):
                
                pairs.append( ( url_class, other_url_class ) )
                
                break
                
            
        
    
    return pairs
    
def SortURLClassesListDescendingComplexity( url_classes: typing.List[ "URLClass" ] ):
    
    # sort reverse = true so most complex come first
    
    # ( num_path_components, num_required_parameters, num_total_parameters, len_example_url )
    url_classes.sort( key = lambda u_c: u_c.GetSortingComplexityKey(), reverse = True )
    
class URLClass( HydrusSerialisable.SerialisableBaseNamed ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_URL_CLASS
    SERIALISABLE_NAME = 'URL Class'
    SERIALISABLE_VERSION = 11
    
    def __init__(
        self,
        name: str,
        url_class_key = None,
        url_type = None,
        preferred_scheme = 'https',
        netloc = 'hostname.com',
        path_components = None,
        parameters = None,
        has_single_value_parameters = False,
        single_value_parameters_string_match = None,
        header_overrides = None,
        api_lookup_converter = None,
        send_referral_url = SEND_REFERRAL_URL_ONLY_IF_PROVIDED,
        referral_url_converter = None,
        gallery_index_type = None,
        gallery_index_identifier = None,
        gallery_index_delta = 1,
        example_url = 'https://hostname.com/post/page.php?id=123456&s=view'
    ):
        
        if url_class_key is None:
            
            url_class_key = HydrusData.GenerateKey()
            
        
        if url_type is None:
            
            url_type = HC.URL_TYPE_POST
            
        
        if path_components is None:
            
            path_components = []
            
            path_components.append( ( ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FIXED, match_value = 'post', example_string = 'post' ), None ) )
            path_components.append( ( ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FIXED, match_value = 'page.php', example_string = 'page.php' ), None ) )
            
        
        if parameters is None:
            
            parameters = {}
            
            parameters[ 's' ] = ( ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FIXED, match_value = 'view', example_string = 'view' ), None )
            parameters[ 'id' ] = ( ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FLEXIBLE, match_value = ClientStrings.NUMERIC, example_string = '123456' ), None )
            
        
        if single_value_parameters_string_match is None:
            
            single_value_parameters_string_match = ClientStrings.StringMatch()
            
        
        if header_overrides is None:
            
            header_overrides = {}
            
        
        if api_lookup_converter is None:
            
            api_lookup_converter = ClientStrings.StringConverter( example_string = 'https://hostname.com/post/page.php?id=123456&s=view' )
            
        
        if referral_url_converter is None:
            
            referral_url_converter = ClientStrings.StringConverter( example_string = 'https://hostname.com/post/page.php?id=123456&s=view' )
            
        
        # if the args are not serialisable stuff, lets overwrite here
        
        path_components = HydrusSerialisable.SerialisableList( path_components )
        parameters = HydrusSerialisable.SerialisableDictionary( parameters )
        
        HydrusSerialisable.SerialisableBaseNamed.__init__( self, name )
        
        self._url_class_key = url_class_key
        self._url_type = url_type
        self._preferred_scheme = preferred_scheme
        self._netloc = netloc
        
        self._match_subdomains = False
        self._keep_matched_subdomains = False
        self._alphabetise_get_parameters = True
        self._can_produce_multiple_files = False
        self._should_be_associated_with_files = True
        self._keep_fragment = False
        
        self._path_components = path_components
        self._parameters = parameters
        self._has_single_value_parameters = has_single_value_parameters
        self._single_value_parameters_string_match = single_value_parameters_string_match
        self._header_overrides = header_overrides
        self._api_lookup_converter = api_lookup_converter
        
        self._send_referral_url = send_referral_url
        self._referral_url_converter = referral_url_converter
        
        self._gallery_index_type = gallery_index_type
        self._gallery_index_identifier = gallery_index_identifier
        self._gallery_index_delta = gallery_index_delta
        
        self._example_url = example_url
        
    
    def _ClipNetLoc( self, netloc ):
        
        if self._keep_matched_subdomains:
            
            # for domains like artistname.website.com, where removing the subdomain may break the url, we leave it alone
            
            pass
            
        else:
            
            # for domains like mediaserver4.website.com, where multiple subdomains serve the same content as the larger site
            
            if not ClientNetworkingFunctions.DomainEqualsAnotherForgivingWWW( netloc, self._netloc ):
                
                netloc = self._netloc
                
            
        
        return netloc
        
    
    def _ClipAndFleshOutPath( self, path, allow_clip = True ):
        
        # /post/show/1326143/akunim-anthro-armband-armwear-clothed-clothing-fem
        
        while path.startswith( '/' ):
            
            path = path[ 1 : ]
            
        
        # post/show/1326143/akunim-anthro-armband-armwear-clothed-clothing-fem
        
        path_components = path.split( '/' )
        
        if allow_clip or len( path_components ) < len( self._path_components ):
            
            clipped_path_components = []
            
            for ( index, ( string_match, default ) ) in enumerate( self._path_components ):
                
                if len( path_components ) > index: # the given path has the value
                    
                    clipped_path_component = path_components[ index ]
                    
                elif default is not None:
                    
                    clipped_path_component = default
                    
                else:
                    
                    raise HydrusExceptions.URLClassException( 'Could not clip path--given url appeared to be too short!' )
                    
                
                clipped_path_components.append( clipped_path_component )
                
            
            path = '/'.join( clipped_path_components )
            
        
        # post/show/1326143
        
        path = '/' + path
        
        # /post/show/1326143
        
        return path
        
    
    def _ClipAndFleshOutQuery( self, query, allow_clip = True ):
        
        ( query_dict, single_value_parameters, param_order ) = ClientNetworkingFunctions.ConvertQueryTextToDict( query )
        
        if allow_clip:
            
            query_dict = { key : value for ( key, value ) in query_dict.items() if key in self._parameters }
            
        
        for ( key, ( string_match, default ) ) in self._parameters.items():
            
            if key not in query_dict:
                
                if default is None:
                    
                    raise HydrusExceptions.URLClassException( 'Could not flesh out query--no default for ' + key + ' defined!' )
                    
                else:
                    
                    query_dict[ key ] = default
                    
                    param_order.append( key )
                    
                
            
        
        if self._alphabetise_get_parameters:
            
            param_order = None
            
        
        if not self._has_single_value_parameters:
            
            single_value_parameters = []
            
        
        query = ClientNetworkingFunctions.ConvertQueryDictToText( query_dict, single_value_parameters, param_order = param_order )
        
        return query
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_url_class_key = self._url_class_key.hex()
        serialisable_path_components = [ ( string_match.GetSerialisableTuple(), default ) for ( string_match, default ) in self._path_components ]
        serialisable_parameters = [ ( key, ( string_match.GetSerialisableTuple(), default ) ) for ( key, ( string_match, default ) ) in self._parameters.items() ]
        serialisable_single_value_parameters_string_match = self._single_value_parameters_string_match.GetSerialisableTuple()
        serialisable_header_overrides = list( self._header_overrides.items() )
        serialisable_api_lookup_converter = self._api_lookup_converter.GetSerialisableTuple()
        serialisable_referral_url_converter = self._referral_url_converter.GetSerialisableTuple()
        
        booleans = ( self._match_subdomains, self._keep_matched_subdomains, self._alphabetise_get_parameters, self._can_produce_multiple_files, self._should_be_associated_with_files, self._keep_fragment )
        
        return (
            serialisable_url_class_key,
            self._url_type,
            self._preferred_scheme,
            self._netloc,
            booleans,
            serialisable_path_components,
            serialisable_parameters,
            self._has_single_value_parameters,
            serialisable_single_value_parameters_string_match,
            serialisable_header_overrides,
            serialisable_api_lookup_converter,
            self._send_referral_url,
            serialisable_referral_url_converter,
            self._gallery_index_type,
            self._gallery_index_identifier,
            self._gallery_index_delta,
            self._example_url
        )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        (
            serialisable_url_class_key,
            self._url_type,
            self._preferred_scheme,
            self._netloc,
            booleans,
            serialisable_path_components,
            serialisable_parameters,
            self._has_single_value_parameters,
            serialisable_single_value_parameters_string_match,
            serialisable_header_overrides,
            serialisable_api_lookup_converter,
            self._send_referral_url,
            serialisable_referral_url_converter,
            self._gallery_index_type,
            self._gallery_index_identifier,
            self._gallery_index_delta,
            self._example_url
            ) = serialisable_info
        
        ( self._match_subdomains, self._keep_matched_subdomains, self._alphabetise_get_parameters, self._can_produce_multiple_files, self._should_be_associated_with_files, self._keep_fragment ) = booleans
        
        self._url_class_key = bytes.fromhex( serialisable_url_class_key )
        self._path_components = [ ( HydrusSerialisable.CreateFromSerialisableTuple( serialisable_string_match ), default ) for ( serialisable_string_match, default ) in serialisable_path_components ]
        self._parameters = { key : ( HydrusSerialisable.CreateFromSerialisableTuple( serialisable_string_match ), default ) for ( key, ( serialisable_string_match, default ) ) in serialisable_parameters }
        self._single_value_parameters_string_match = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_single_value_parameters_string_match )
        self._header_overrides = dict( serialisable_header_overrides )
        self._api_lookup_converter = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_api_lookup_converter )
        self._referral_url_converter = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_referral_url_converter )
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( url_type, preferred_scheme, netloc, match_subdomains, keep_matched_subdomains, serialisable_path_components, serialisable_parameters, example_url ) = old_serialisable_info
            
            url_class_key = HydrusData.GenerateKey()
            
            serialisable_url_class_key = url_class_key.hex()
            
            api_lookup_converter = ClientStrings.StringConverter( example_string = example_url )
            
            serialisable_api_lookup_converter = api_lookup_converter.GetSerialisableTuple()
            
            new_serialisable_info = ( serialisable_url_class_key, url_type, preferred_scheme, netloc, match_subdomains, keep_matched_subdomains, serialisable_path_components, serialisable_parameters, serialisable_api_lookup_converter, example_url )
            
            return ( 2, new_serialisable_info )
            
        
        if version == 2:
            
            ( serialisable_url_class_key, url_type, preferred_scheme, netloc, match_subdomains, keep_matched_subdomains, serialisable_path_components, serialisable_parameters, serialisable_api_lookup_converter, example_url ) = old_serialisable_info
            
            if url_type in ( HC.URL_TYPE_FILE, HC.URL_TYPE_POST ):
                
                should_be_associated_with_files = True
                
            else:
                
                should_be_associated_with_files = False
                
            
            new_serialisable_info = ( serialisable_url_class_key, url_type, preferred_scheme, netloc, match_subdomains, keep_matched_subdomains, serialisable_path_components, serialisable_parameters, serialisable_api_lookup_converter, should_be_associated_with_files, example_url )
            
            return ( 3, new_serialisable_info )
            
        
        if version == 3:
            
            ( serialisable_url_class_key, url_type, preferred_scheme, netloc, match_subdomains, keep_matched_subdomains, serialisable_path_components, serialisable_parameters, serialisable_api_lookup_converter, should_be_associated_with_files, example_url ) = old_serialisable_info
            
            can_produce_multiple_files = False
            
            new_serialisable_info = ( serialisable_url_class_key, url_type, preferred_scheme, netloc, match_subdomains, keep_matched_subdomains, serialisable_path_components, serialisable_parameters, serialisable_api_lookup_converter, can_produce_multiple_files, should_be_associated_with_files, example_url )
            
            return ( 4, new_serialisable_info )
            
        
        if version == 4:
            
            ( serialisable_url_class_key, url_type, preferred_scheme, netloc, match_subdomains, keep_matched_subdomains, serialisable_path_components, serialisable_parameters, serialisable_api_lookup_converter, can_produce_multiple_files, should_be_associated_with_files, example_url ) = old_serialisable_info
            
            gallery_index_type = None
            gallery_index_identifier = None
            gallery_index_delta = 1
            
            new_serialisable_info = ( serialisable_url_class_key, url_type, preferred_scheme, netloc, match_subdomains, keep_matched_subdomains, serialisable_path_components, serialisable_parameters, serialisable_api_lookup_converter, can_produce_multiple_files, should_be_associated_with_files, gallery_index_type, gallery_index_identifier, gallery_index_delta, example_url )
            
            return ( 5, new_serialisable_info )
            
        
        if version == 5:
            
            ( serialisable_url_class_key, url_type, preferred_scheme, netloc, match_subdomains, keep_matched_subdomains, serialisable_path_components, serialisable_parameters, serialisable_api_lookup_converter, can_produce_multiple_files, should_be_associated_with_files, gallery_index_type, gallery_index_identifier, gallery_index_delta, example_url ) = old_serialisable_info
            
            path_components = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_path_components )
            parameters = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_parameters )
            
            path_components = [ ( value, None ) for value in path_components ]
            parameters = { key : ( value, None ) for ( key, value ) in list(parameters.items()) }
            
            serialisable_path_components = [ ( string_match.GetSerialisableTuple(), default ) for ( string_match, default ) in path_components ]
            serialisable_parameters = [ ( key, ( string_match.GetSerialisableTuple(), default ) ) for ( key, ( string_match, default ) ) in list(parameters.items()) ]
            
            new_serialisable_info = ( serialisable_url_class_key, url_type, preferred_scheme, netloc, match_subdomains, keep_matched_subdomains, serialisable_path_components, serialisable_parameters, serialisable_api_lookup_converter, can_produce_multiple_files, should_be_associated_with_files, gallery_index_type, gallery_index_identifier, gallery_index_delta, example_url )
            
            return ( 6, new_serialisable_info )
            
        
        if version == 6:
            
            ( serialisable_url_class_key, url_type, preferred_scheme, netloc, match_subdomains, keep_matched_subdomains, serialisable_path_components, serialisable_parameters, serialisable_api_lookup_converter, can_produce_multiple_files, should_be_associated_with_files, gallery_index_type, gallery_index_identifier, gallery_index_delta, example_url ) = old_serialisable_info
            
            send_referral_url = SEND_REFERRAL_URL_ONLY_IF_PROVIDED
            referral_url_converter = ClientStrings.StringConverter( example_string = 'https://hostname.com/post/page.php?id=123456&s=view' )
            
            serialisable_referrel_url_converter = referral_url_converter.GetSerialisableTuple()
            
            new_serialisable_info = ( serialisable_url_class_key, url_type, preferred_scheme, netloc, match_subdomains, keep_matched_subdomains, serialisable_path_components, serialisable_parameters, serialisable_api_lookup_converter, send_referral_url, serialisable_referrel_url_converter, can_produce_multiple_files, should_be_associated_with_files, gallery_index_type, gallery_index_identifier, gallery_index_delta, example_url )
            
            return ( 7, new_serialisable_info )
            
        
        if version == 7:
            
            ( serialisable_url_class_key, url_type, preferred_scheme, netloc, match_subdomains, keep_matched_subdomains, serialisable_path_components, serialisable_parameters, serialisable_api_lookup_converter, send_referral_url, serialisable_referrel_url_converter, can_produce_multiple_files, should_be_associated_with_files, gallery_index_type, gallery_index_identifier, gallery_index_delta, example_url ) = old_serialisable_info
            
            alphabetise_get_parameters = True
            
            new_serialisable_info = ( serialisable_url_class_key, url_type, preferred_scheme, netloc, match_subdomains, keep_matched_subdomains, alphabetise_get_parameters, serialisable_path_components, serialisable_parameters, serialisable_api_lookup_converter, send_referral_url, serialisable_referrel_url_converter, can_produce_multiple_files, should_be_associated_with_files, gallery_index_type, gallery_index_identifier, gallery_index_delta, example_url )
            
            return ( 8, new_serialisable_info )
            
        
        if version == 8:
            
            ( serialisable_url_class_key, url_type, preferred_scheme, netloc, match_subdomains, keep_matched_subdomains, alphabetise_get_parameters, serialisable_path_components, serialisable_parameters, serialisable_api_lookup_converter, send_referral_url, serialisable_referrel_url_converter, can_produce_multiple_files, should_be_associated_with_files, gallery_index_type, gallery_index_identifier, gallery_index_delta, example_url ) = old_serialisable_info
            
            keep_fragment = False
            
            booleans = ( match_subdomains, keep_matched_subdomains, alphabetise_get_parameters, can_produce_multiple_files, should_be_associated_with_files, keep_fragment )
            
            new_serialisable_info = ( serialisable_url_class_key, url_type, preferred_scheme, netloc, booleans, serialisable_path_components, serialisable_parameters, serialisable_api_lookup_converter, send_referral_url, serialisable_referrel_url_converter, gallery_index_type, gallery_index_identifier, gallery_index_delta, example_url )
            
            return ( 9, new_serialisable_info )
            
        
        if version == 9:
            
            ( serialisable_url_class_key, url_type, preferred_scheme, netloc, booleans, serialisable_path_components, serialisable_parameters, serialisable_api_lookup_converter, send_referral_url, serialisable_referrel_url_converter, gallery_index_type, gallery_index_identifier, gallery_index_delta, example_url ) = old_serialisable_info
            
            header_overrides = {}
            
            serialisable_header_overrides = list( header_overrides.items() )
            
            new_serialisable_info = ( serialisable_url_class_key, url_type, preferred_scheme, netloc, booleans, serialisable_path_components, serialisable_parameters, serialisable_header_overrides, serialisable_api_lookup_converter, send_referral_url, serialisable_referrel_url_converter, gallery_index_type, gallery_index_identifier, gallery_index_delta, example_url )
            
            return ( 10, new_serialisable_info )
            
        
        if version == 10:
            
            ( serialisable_url_class_key, url_type, preferred_scheme, netloc, booleans, serialisable_path_components, serialisable_parameters, serialisable_header_overrides, serialisable_api_lookup_converter, send_referral_url, serialisable_referrel_url_converter, gallery_index_type, gallery_index_identifier, gallery_index_delta, example_url ) = old_serialisable_info
            
            has_single_value_parameters = False
            single_value_parameters_string_match = ClientStrings.StringMatch()
            
            serialisable_single_value_parameters_match = single_value_parameters_string_match.GetSerialisableTuple()
            
            new_serialisable_info = (
                serialisable_url_class_key,
                url_type,
                preferred_scheme,
                netloc,
                booleans,
                serialisable_path_components,
                serialisable_parameters,
                has_single_value_parameters,
                serialisable_single_value_parameters_match,
                serialisable_header_overrides,
                serialisable_api_lookup_converter,
                send_referral_url,
                serialisable_referrel_url_converter,
                gallery_index_type,
                gallery_index_identifier,
                gallery_index_delta,
                example_url
            )
            
            return ( 11, new_serialisable_info )
            
        
    
    def AlphabetiseGetParameters( self ):
        
        return self._alphabetise_get_parameters
        
    
    def CanGenerateNextGalleryPage( self ):
        
        if self._url_type == HC.URL_TYPE_GALLERY:
            
            if self._gallery_index_type is not None:
                
                return True
                
            
        
        return False
        
    
    def CanReferToMultipleFiles( self ):
        
        is_a_gallery_page = self._url_type in ( HC.URL_TYPE_GALLERY, HC.URL_TYPE_WATCHABLE )
        
        is_a_multipost_post_page = self._url_type == HC.URL_TYPE_POST and self._can_produce_multiple_files
        
        return is_a_gallery_page or is_a_multipost_post_page
        
    
    def ClippingIsAppropriate( self ):
        
        return self._should_be_associated_with_files or self.UsesAPIURL()
        
    
    def GetAPIURL( self, url = None ):
        
        if url is None:
            
            url = self._example_url
            
        
        url = self.Normalise( url )
        
        return self._api_lookup_converter.Convert( url )
        
    
    def GetClassKey( self ):
        
        return self._url_class_key
        
    
    def GetDomain( self ):
        
        return self._netloc
        
    
    def GetExampleURL( self ):
        
        return self._example_url
        
    
    def GetGalleryIndexValues( self ):
        
        return ( self._gallery_index_type, self._gallery_index_identifier, self._gallery_index_delta )
        
    
    def GetHeaderOverrides( self ):
        
        return self._header_overrides
        
    
    def GetNextGalleryPage( self, url ):
        
        url = self.Normalise( url )
        
        p = ClientNetworkingFunctions.ParseURL( url )
        
        scheme = p.scheme
        netloc = p.netloc
        path = p.path
        query = p.query
        params = ''
        fragment = p.fragment
        
        if self._gallery_index_type == GALLERY_INDEX_TYPE_PATH_COMPONENT:
            
            page_index_path_component_index = self._gallery_index_identifier
            
            while path.startswith( '/' ):
                
                path = path[ 1 : ]
                
            
            path_components = path.split( '/' )
            
            try:
                
                page_index = path_components[ page_index_path_component_index ]
                
            except IndexError:
                
                raise HydrusExceptions.URLClassException( 'Could not generate next gallery page--not enough path components!' )
                
            
            try:
                
                page_index = int( page_index )
                
            except:
                
                raise HydrusExceptions.URLClassException( 'Could not generate next gallery page--index component was not an integer!' )
                
            
            path_components[ page_index_path_component_index ] = str( page_index + self._gallery_index_delta )
            
            path = '/' + '/'.join( path_components )
            
        elif self._gallery_index_type == GALLERY_INDEX_TYPE_PARAMETER:
            
            page_index_name = self._gallery_index_identifier
            
            ( query_dict, single_value_parameters, param_order ) = ClientNetworkingFunctions.ConvertQueryTextToDict( query )
            
            if page_index_name not in query_dict:
                
                raise HydrusExceptions.URLClassException( 'Could not generate next gallery page--did not find ' + str( self._gallery_index_identifier ) + ' in parameters!' )
                
            
            page_index = query_dict[ page_index_name ]
            
            try:
                
                page_index = int( page_index )
                
            except:
                
                raise HydrusExceptions.URLClassException( 'Could not generate next gallery page--index component was not an integer!' )
                
            
            query_dict[ page_index_name ] = page_index + self._gallery_index_delta
            
            if self._alphabetise_get_parameters:
                
                param_order = None
                
            
            if not self._has_single_value_parameters:
                
                single_value_parameters = []
                
            
            query = ClientNetworkingFunctions.ConvertQueryDictToText( query_dict, single_value_parameters, param_order = param_order )
            
        else:
            
            raise NotImplementedError( 'Did not understand the next gallery page rules!' )
            
        
        r = urllib.parse.ParseResult( scheme, netloc, path, params, query, fragment )
        
        return r.geturl()
        
    
    def GetReferralURL( self, url, referral_url ):
        
        if self._send_referral_url == SEND_REFERRAL_URL_ONLY_IF_PROVIDED:
            
            return referral_url
            
        elif self._send_referral_url == SEND_REFERRAL_URL_NEVER:
            
            return None
            
        elif self._send_referral_url in ( SEND_REFERRAL_URL_CONVERTER_IF_NONE_PROVIDED, SEND_REFERRAL_URL_ONLY_CONVERTER ):
            
            try:
                
                converted_referral_url = self._referral_url_converter.Convert( url )
                
            except HydrusExceptions.StringConvertException:
                
                return referral_url
                
            
            p1 = self._send_referral_url == SEND_REFERRAL_URL_ONLY_CONVERTER
            p2 = self._send_referral_url == SEND_REFERRAL_URL_CONVERTER_IF_NONE_PROVIDED and referral_url is None
            
            if p1 or p2:
                
                return converted_referral_url
                
            else:
                
                return referral_url
                
            
        
        return referral_url
        
    
    def GetSafeSummary( self ):
        
        return 'URL Class "' + self._name + '" - ' + ClientNetworkingFunctions.ConvertURLIntoDomain( self.GetExampleURL() )
        
    
    def GetSingleValueParameterData( self ):
        
        return ( self._has_single_value_parameters, self._single_value_parameters_string_match )
        
    
    def GetSortingComplexityKey( self ):
        
        # we sort url classes so that
        # site.com/post/123456
        # comes before
        # site.com/search?query=blah
        
        # I used to do gallery first, then post, then file, but it ultimately was unhelpful in some situations and better handled by strict component/parameter matching
        
        num_required_path_components = len( [ 1 for ( string_match, default ) in self._path_components if default is None ] )
        num_total_path_components = len( self._path_components )
        num_required_parameters = len( [ 1 for ( key, ( string_match, default ) ) in self._parameters.items() if default is None ] )
        num_total_parameters = len( self._parameters )
        len_example_url = len( self.Normalise( self._example_url ) )
        
        return ( num_required_parameters, num_total_path_components, num_required_parameters, num_total_parameters, len_example_url )
        
    
    def GetURLBooleans( self ):
        
        return ( self._match_subdomains, self._keep_matched_subdomains, self._alphabetise_get_parameters, self._can_produce_multiple_files, self._should_be_associated_with_files, self._keep_fragment )
        
    
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
            
        except HydrusExceptions.URLClassException:
            
            return False
            
        
    
    def MatchesSubdomains( self ):
        
        return self._match_subdomains
        
    
    def Normalise( self, url ):
        
        p = ClientNetworkingFunctions.ParseURL( url )
        
        scheme = self._preferred_scheme
        params = ''
        
        if self._keep_fragment:
            
            fragment = p.fragment
            
        else:
            
            fragment = ''
            
        
        if self.ClippingIsAppropriate():
            
            netloc = self._ClipNetLoc( p.netloc )
            path = self._ClipAndFleshOutPath( p.path )
            query = self._ClipAndFleshOutQuery( p.query )
            
        else:
            
            netloc = p.netloc
            path = self._ClipAndFleshOutPath( p.path, allow_clip = False )
            query = self._ClipAndFleshOutQuery( p.query, allow_clip = False )
            
        
        r = urllib.parse.ParseResult( scheme, netloc, path, params, query, fragment )
        
        return r.geturl()
        
    
    def RefersToOneFile( self ):
        
        is_a_direct_file_page = self._url_type == HC.URL_TYPE_FILE
        
        is_a_single_file_post_page = self._url_type == HC.URL_TYPE_POST and not self._can_produce_multiple_files
        
        return is_a_direct_file_page or is_a_single_file_post_page
        
    
    def RegenerateClassKey( self ):
        
        self._url_class_key = HydrusData.GenerateKey()
        
    
    def SetAlphabetiseGetParameters( self, alphabetise_get_parameters: bool ):
        
        self._alphabetise_get_parameters = alphabetise_get_parameters
        
    
    def SetClassKey( self, match_key ):
        
        self._url_class_key = match_key
        
    
    def SetExampleURL( self, example_url ):
        
        self._example_url = example_url
        
    
    def SetSingleValueParameterData( self, has_single_value_parameters: bool, single_value_parameters_string_match: ClientStrings.StringMatch ):
        
        self._has_single_value_parameters = has_single_value_parameters
        self._single_value_parameters_string_match = single_value_parameters_string_match
        
    
    def SetURLBooleans(
        self,
        match_subdomains: bool,
        keep_matched_subdomains: bool,
        alphabetise_get_parameters: bool,
        can_produce_multiple_files: bool,
        should_be_associated_with_files: bool,
        keep_fragment: bool
    ):
        
        self._match_subdomains = match_subdomains
        self._keep_matched_subdomains = keep_matched_subdomains
        self._alphabetise_get_parameters = alphabetise_get_parameters
        self._can_produce_multiple_files = can_produce_multiple_files
        self._should_be_associated_with_files = should_be_associated_with_files
        self._keep_fragment = keep_fragment
        
    
    def ShouldAssociateWithFiles( self ):
        
        return self._should_be_associated_with_files
        
    
    def Test( self, url ):
        
        p = ClientNetworkingFunctions.ParseURL( url )
        
        if self._match_subdomains:
            
            if p.netloc != self._netloc and not p.netloc.endswith( '.' + self._netloc ):
                
                raise HydrusExceptions.URLClassException( p.netloc + ' (potentially excluding subdomains) did not match ' + self._netloc )
                
            
        else:
            
            if not ClientNetworkingFunctions.DomainEqualsAnotherForgivingWWW( p.netloc, self._netloc ):
                
                raise HydrusExceptions.URLClassException( p.netloc + ' did not match ' + self._netloc )
                
            
        
        url_path = p.path
        
        while url_path.startswith( '/' ):
            
            url_path = url_path[ 1 : ]
            
        
        url_path_components = url_path.split( '/' )
        
        for ( index, ( string_match, default ) ) in enumerate( self._path_components ):
            
            if len( url_path_components ) > index:
                
                url_path_component = url_path_components[ index ]
                
                try:
                    
                    string_match.Test( url_path_component )
                    
                except HydrusExceptions.StringMatchException as e:
                    
                    raise HydrusExceptions.URLClassException( str( e ) )
                    
                
            elif default is None:
                
                raise HydrusExceptions.URLClassException( url_path + ' did not have enough of the required path components!' )
                
            
        
        ( url_parameters, single_value_parameters, param_order ) = ClientNetworkingFunctions.ConvertQueryTextToDict( p.query )
        
        for ( key, ( string_match, default ) ) in self._parameters.items():
            
            if key not in url_parameters:
                
                if default is None:
                    
                    raise HydrusExceptions.URLClassException( key + ' not found in ' + p.query )
                    
                else:
                    
                    continue
                    
                
            
            value = url_parameters[ key ]
            
            try:
                
                string_match.Test( value )
                
            except HydrusExceptions.StringMatchException as e:
                
                raise HydrusExceptions.URLClassException( str( e ) )
                
            
        
        if self._has_single_value_parameters:
            
            if len( single_value_parameters ) == 0:
                
                raise HydrusExceptions.URLClassException( 'Was expecting single-value parameter(s), but this URL did not seem to have any.' )
                
            
            for single_value_parameter in single_value_parameters:
                
                try:
                    
                    self._single_value_parameters_string_match.Test( single_value_parameter )
                    
                except HydrusExceptions.StringMatchException as e:
                    
                    raise HydrusExceptions.URLClassException( str( e ) )
                    
                
            
        
    
    def ToTuple( self ):
        
        return ( self._url_type, self._preferred_scheme, self._netloc, self._path_components, self._parameters, self._api_lookup_converter, self._send_referral_url, self._referral_url_converter, self._example_url )
        
    
    def UsesAPIURL( self ):
        
        return self._api_lookup_converter.MakesChanges()
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_URL_CLASS ] = URLClass
