import functools
import re
import typing
import urllib.parse

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusText

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
            
        
        example_url = url_class.GetExampleURL()
        
        try:
            
            api_url = url_class.GetAPIURL( example_url )
            
        except:
            
            continue
            
        
        for other_url_class in url_classes:
            
            if other_url_class == url_class:
                
                continue
                
            
            if other_url_class.Matches( api_url ):
                
                pairs.append( ( url_class, other_url_class ) )
                
                break
                
            
        
    
    return pairs
    

def SortURLClassesListDescendingComplexity( url_classes: list[ "URLClass" ] ):
    
    # sort reverse = true so most complex come first
    
    # ( num_path_components, num_required_parameters, num_total_parameters, len_example_url )
    url_classes.sort( key = lambda u_c: u_c.GetSortingComplexityKey(), reverse = True )
    

class URLClassParameterFixedName( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_URL_CLASS_PARAMETER_FIXED_NAME
    SERIALISABLE_NAME = 'URL Class Parameter - Fixed Name'
    SERIALISABLE_VERSION = 2
    
    def __init__( self, name = None, value_string_match = None ):
        
        if name is None:
            
            name = 'name'
            
        
        if value_string_match is None:
            
            value_string_match = ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FIXED, match_value = 'value', example_string = 'value' )
            
        
        super().__init__()
        
        self._name = name
        self._value_string_match = value_string_match
        
        self._is_ephemeral = False
        
        self._default_value = None
        self._default_value_string_processor = ClientStrings.StringProcessor()
        
    
    def __repr__( self ):
        
        text = f'URL Class Parameter - Fixed Name: {self._name}: {self._value_string_match.ToString()}'
        
        return text
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_value_string_match = self._value_string_match.GetSerialisableTuple()
        serialisable_default_value_string_processor = self._default_value_string_processor.GetSerialisableTuple()
        
        return ( self._name, serialisable_value_string_match, self._is_ephemeral, self._default_value, serialisable_default_value_string_processor )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._name, serialisable_value_string_match, self._is_ephemeral, self._default_value, serialisable_default_value_string_processor ) = serialisable_info
        
        self._value_string_match = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_value_string_match )
        self._default_value_string_processor = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_default_value_string_processor )
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( name, serialisable_value_string_match, default_value ) = old_serialisable_info
            
            is_ephemeral = False
            default_value_string_processor = ClientStrings.StringConverter()
            
            serialisable_default_value_string_processor = default_value_string_processor.GetSerialisableTuple()
            
            new_serialisable_info = ( name, serialisable_value_string_match, is_ephemeral, default_value, serialisable_default_value_string_processor )
            
            return ( 2, new_serialisable_info )
            
        
    
    def GetDefaultValue( self, with_processing = False ) -> typing.Optional[ str ]:
        
        if with_processing and self._default_value is not None:
            
            try:
                
                result = self._default_value_string_processor.ProcessStrings( [ self._default_value ] )
                
                return result[0]
                
            except:
                
                return self._default_value
                
            
        else:
            
            return self._default_value
            
        
    
    def GetDefaultValueStringProcessor( self ) -> ClientStrings.StringProcessor:
        
        return self._default_value_string_processor
        
    
    def GetName( self ):
        
        return self._name
        
    
    def GetValueStringMatch( self ):
        
        return self._value_string_match
        
    
    def HasDefaultValue( self ):
        
        return self._default_value is not None
        
    
    def IsEphemeralToken( self ):
        
        return self._is_ephemeral
        
    
    def MustBeInOriginalURL( self ):
        
        return self._default_value is None and not self.IsEphemeralToken()
        
    
    def MatchesName( self, name ):
        
        return self._name == name
        
    
    def MatchesValue( self, value ):
        
        return self._value_string_match.Matches( value )
        
    
    def SetDefaultValue( self, default_value: typing.Optional[ str ] ):
        
        self._default_value = default_value
        
    
    def SetDefaultValueStringProcessor( self, default_value_string_processor: ClientStrings.StringProcessor ):
        
        self._default_value_string_processor = default_value_string_processor
        
    
    def SetIsEphemeral( self, value ):
        
        self._is_ephemeral = value
        
    
    def TestValue( self, value ):
        
        self._value_string_match.Test( value )
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_URL_CLASS_PARAMETER_FIXED_NAME ] = URLClassParameterFixedName

class URLDomainMask( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_URL_DOMAIN_MASK
    SERIALISABLE_NAME = 'URL Domain Mask'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, raw_domains: typing.Optional[ list[ str ] ] = None, domain_regexes: typing.Optional[ list[ str ] ] = None, match_subdomains: bool = False, keep_matched_subdomains: bool = False ):
        
        if raw_domains is None:
            
            raw_domains = []
            
        
        if domain_regexes is None:
            
            domain_regexes = []
            
        
        self._raw_domains = tuple( sorted( raw_domains ) )
        self._domain_regexes = tuple( sorted( domain_regexes ) )
        self.match_subdomains = match_subdomains
        self.keep_matched_subdomains = keep_matched_subdomains
        
        self._re_match_patterns = []
        self._re_clip_patterns = []
        self._cache_initialised = False
        
    
    def __eq__( self, other ):
        
        if isinstance( other, URLDomainMask ):
            
            return self.__hash__() == other.__hash__()
            
        
        return NotImplemented
        
    
    def __hash__( self ):
        
        return ( self._raw_domains, self._domain_regexes, self.match_subdomains ).__hash__()
        
    
    def _GetSerialisableInfo( self ):
        
        return (
            list( self._raw_domains ),
            list( self._domain_regexes ),
            self.match_subdomains,
            self.keep_matched_subdomains
        )
        
    
    def _InitialiseCache( self ):
        
        all_domain_regexes = list( self._domain_regexes )
        all_domain_regexes.extend( ( re.escape( raw_domain ) for raw_domain in self._raw_domains ) )
        all_domain_regexes.sort()
        
        try:
            
            if self.match_subdomains:
                
                # anything.ourdomain or ourdomain
                self._re_match_patterns = [ re.compile( r'^(.*\.)?' + domain_regex + '$' ) for domain_regex in all_domain_regexes ]
                
            else:
                
                # wwwanything.ourdomain or ourdomain
                self._re_match_patterns = [ re.compile( r'^(www[^\.]*\.)?' + domain_regex + '$' ) for domain_regex in all_domain_regexes ]
                
            
            self._re_clip_patterns = [ re.compile( domain_regex + '$' ) for domain_regex in all_domain_regexes ]
            
        except:
            
            self._re_match_patterns = []
            self._re_clip_patterns = []
            
        
        self._cache_initialised = True
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        (
            raw_domains,
            domain_regexes,
            self.match_subdomains,
            self.keep_matched_subdomains
        ) = serialisable_info
        
        self._raw_domains = tuple( sorted( raw_domains ) )
        self._domain_regexes = tuple( sorted( domain_regexes ) )
        
    
    def GetDomainRegexes( self ) -> list[ str ]:
        
        return list( self._domain_regexes )
        
    
    def GetRawDomains( self ) -> list[ str ]:
        
        return list( self._raw_domains )
        
    
    def GetSortingComplexity( self ) -> int:
        
        all_items = [ len( raw_domain ) for raw_domain in self._raw_domains ] + [ len( domain_regex ) for domain_regex in self._domain_regexes ]
        
        if len( all_items ) == 0:
            
            return 10
            
        else:
            
            return max( all_items )
            
        
    
    def IsSingleRawDomain( self ):
        
        return len( self._raw_domains ) == 1 and self.NoRegexes()
        
    
    @functools.lru_cache( 128 )
    def Matches( self, domain: str ) -> bool:
        
        if not self._cache_initialised:
            
            self._InitialiseCache()
            
        
        return True in ( pattern.match( domain ) is not None for pattern in self._re_match_patterns )
        
    
    def Normalise( self, domain: str ):
        
        if self.keep_matched_subdomains:
            
            return domain
            
        else:
            
            if not self._cache_initialised:
                
                self._InitialiseCache()
                
            
            for pattern in self._re_clip_patterns:
                
                result = pattern.search( domain )
                
                if result is not None:
                    
                    return result[0]
                    
                
            
            raise HydrusExceptions.URLClassException( 'Could not match that domain with this domain mask!' )
            
        
    
    def NoRegexes( self ):
        
        return len( self._domain_regexes ) == 0
        
    
    def Test( self, domain: str ):
        
        if not self.Matches( domain ):
            
            me_str = self.ToString()
            
            if self.match_subdomains:
                
                raise HydrusExceptions.URLClassException( domain + ' (potentially excluding subdomains) did not match ' + me_str )
                
            else:
                
                raise HydrusExceptions.URLClassException( domain + ' did not match ' + me_str )
                
            
        
    
    def ToString( self ):
        
        if len( self._raw_domains ) > 0:
            
            self_domain_description = HydrusText.ConvertManyStringsToNiceInsertableHumanSummarySingleLine( self._raw_domains, 'domains' )
            
            if len( self._domain_regexes ) > 0:
                
                self_domain_description += HydrusText.ConvertManyStringsToNiceInsertableHumanSummarySingleLine( self._domain_regexes, 'domain regexes' )
                
            
        else:
            
            if len( self._domain_regexes ) > 0:
                
                self_domain_description = HydrusText.ConvertManyStringsToNiceInsertableHumanSummarySingleLine( self._domain_regexes, 'domain regexes' )
                
            else:
                
                self_domain_description = 'no domain rules, will not match anything!'
                
            
        
        return f'URL Domain Mask: {self_domain_description}'
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_URL_DOMAIN_MASK ] = URLDomainMask

class URLClass( HydrusSerialisable.SerialisableBaseNamed ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_URL_CLASS
    SERIALISABLE_NAME = 'URL Class'
    SERIALISABLE_VERSION = 15
    
    def __init__(
        self,
        name: str,
        url_class_key = None,
        url_type = None,
        preferred_scheme = 'https',
        url_domain_mask = None,
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
            
        
        if url_domain_mask is None:
            
            url_domain_mask = URLDomainMask( raw_domains = [ 'hostname.com' ] )
            
        
        if path_components is None:
            
            path_components = []
            
            path_components.append( ( ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FIXED, match_value = 'post', example_string = 'post' ), None ) )
            path_components.append( ( ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FIXED, match_value = 'page.php', example_string = 'page.php' ), None ) )
            
        
        if parameters is None:
            
            parameters = []
            
            p = URLClassParameterFixedName(
                name = 's',
                value_string_match = ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FIXED, match_value = 'view', example_string = 'view' )
            )
            
            parameters.append( p )
            
            p = URLClassParameterFixedName(
                name = 'id',
                value_string_match = ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FLEXIBLE, match_value = ClientStrings.FLEXIBLE_MATCH_NUMERIC, example_string = '123456' )
            )
            
            parameters.append( p )
            
        
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
        parameters = HydrusSerialisable.SerialisableList( parameters )
        
        super().__init__( name )
        
        self._url_class_key = url_class_key
        self._url_type = url_type
        self._preferred_scheme = preferred_scheme
        
        self._url_domain_mask = url_domain_mask
        
        self._alphabetise_get_parameters = True
        self._no_more_path_components_than_this = False
        self._no_more_parameters_than_this = False
        self._keep_extra_parameters_for_server = True
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
        
        if self._no_more_parameters_than_this:
            
            self._keep_extra_parameters_for_server = False
            
        
    
    def __eq__( self, other ):
        
        if isinstance( other, URLClass ):
            
            return self.__hash__() == other.__hash__()
            
        
        return NotImplemented
        
    
    def __hash__( self ):
        
        return ( self._name, self._url_class_key ).__hash__()
        
    
    def _ClipNetLoc( self, netloc ):
        
        return self._url_domain_mask.Normalise( netloc )
        
    
    def _ClipAndFleshOutPath( self, path_components: list[ str ], for_server: bool ):
        
        # /post/show/1326143/akunim-anthro-armband-armwear-clothed-clothing-fem
        
        do_clip = self.UsesAPIURL() or not for_server
        flesh_out = len( path_components ) < len( self._path_components )
        
        if do_clip or flesh_out:
            
            clipped_path_components = []
            
            for ( index, ( string_match, default ) ) in enumerate( self._path_components ):
                
                if len( path_components ) > index: # the given path has the value
                    
                    clipped_path_component = path_components[ index ]
                    
                elif default is not None:
                    
                    clipped_path_component = default
                    
                else:
                    
                    raise HydrusExceptions.URLClassException( 'Could not clip path--given url appeared to be too short!' )
                    
                
                clipped_path_components.append( clipped_path_component )
                
            
            path_components = clipped_path_components
            
        
        path = '/' + '/'.join( path_components )
        
        # /post/show/1326143
        
        return path
        
    
    def _ClipAndFleshOutQuery( self, query_dict: dict[ str, str ], single_value_parameters: list[ str ], param_order: list[ str ], for_server: bool ):
        
        query_dict_keys_to_parameters = {}
        
        remaining_query_dict_names = set( query_dict.keys() )
        
        # if we were feeling clever, we could sort these guys from most specific name to least, but w/e
        for parameter in self._parameters:
            
            match_found = False
            
            for name in remaining_query_dict_names:
                
                if parameter.MatchesName( name ):
                    
                    query_dict_keys_to_parameters[ name ] = parameter
                    
                    remaining_query_dict_names.discard( name )
                    
                    match_found = True
                    
                    break
                    
                
            
            if not match_found:
                
                if parameter.HasDefaultValue():
                    
                    if isinstance( parameter, URLClassParameterFixedName ):
                        
                        name = parameter.GetName()
                        
                        query_dict_keys_to_parameters[ name ] = parameter
                        
                        query_dict[ name ] = parameter.GetDefaultValue( with_processing = True )
                        
                        param_order.append( name )
                        
                    else:
                        
                        raise HydrusExceptions.URLClassException( f'Could not flesh out query--cannot figure out a fixed name for {parameter}!' )
                        
                    
                else:
                    
                    ok_to_be_missing = parameter.IsEphemeralToken()
                    
                    if not ok_to_be_missing:
                        
                        raise HydrusExceptions.URLClassException( f'Could not flesh out query--no default for {name} defined!' )
                        
                    
                
            
        
        for name in remaining_query_dict_names:
            
            query_dict_keys_to_parameters[ name ] = None
            
        
        # ok, we now have our fully fleshed out query_dict. let's filter it
        
        filtered_query_dict = {}
        
        for ( name, possible_parameter ) in query_dict_keys_to_parameters.items():
            
            if possible_parameter is None:
                
                if not ( for_server and self._keep_extra_parameters_for_server ):
                    
                    # no matching param, discard it
                    continue
                    
                
            else:
                
                if possible_parameter.IsEphemeralToken() and not for_server:
                    
                    continue
                    
                
            
            filtered_query_dict[ name ] = query_dict[ name ]
            
        
        query_dict = filtered_query_dict
        
        #
        
        if self._alphabetise_get_parameters:
            
            param_order = None
            
        
        we_want_single_value_params = self._has_single_value_parameters or ( for_server and self._keep_extra_parameters_for_server )
        
        if not we_want_single_value_params:
            
            single_value_parameters = []
            
        
        query = ClientNetworkingFunctions.ConvertQueryDictToText( query_dict, single_value_parameters, param_order = param_order )
        
        return query
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_url_domain_mask = self._url_domain_mask.GetSerialisableTuple()
        serialisable_url_class_key = self._url_class_key.hex()
        serialisable_path_components = [ ( string_match.GetSerialisableTuple(), default ) for ( string_match, default ) in self._path_components ]
        serialisable_parameters = self._parameters.GetSerialisableTuple()
        serialisable_single_value_parameters_string_match = self._single_value_parameters_string_match.GetSerialisableTuple()
        serialisable_header_overrides = list( self._header_overrides.items() )
        serialisable_api_lookup_converter = self._api_lookup_converter.GetSerialisableTuple()
        serialisable_referral_url_converter = self._referral_url_converter.GetSerialisableTuple()
        
        booleans = ( self._alphabetise_get_parameters, self._no_more_path_components_than_this, self._no_more_parameters_than_this, self._keep_extra_parameters_for_server, self._can_produce_multiple_files, self._should_be_associated_with_files, self._keep_fragment )
        
        return (
            serialisable_url_class_key,
            self._url_type,
            self._preferred_scheme,
            serialisable_url_domain_mask,
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
            serialisable_url_domain_mask,
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
        
        ( self._alphabetise_get_parameters, self._no_more_path_components_than_this, self._no_more_parameters_than_this, self._keep_extra_parameters_for_server, self._can_produce_multiple_files, self._should_be_associated_with_files, self._keep_fragment ) = booleans
        
        self._url_domain_mask = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_url_domain_mask )
        self._url_class_key = bytes.fromhex( serialisable_url_class_key )
        self._path_components = [ ( HydrusSerialisable.CreateFromSerialisableTuple( serialisable_string_match ), default ) for ( serialisable_string_match, default ) in serialisable_path_components ]
        self._parameters = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_parameters )
        self._single_value_parameters_string_match = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_single_value_parameters_string_match )
        self._header_overrides = dict( serialisable_header_overrides )
        self._api_lookup_converter = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_api_lookup_converter )
        self._referral_url_converter = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_referral_url_converter )
        
        if self._no_more_parameters_than_this:
            
            self._keep_extra_parameters_for_server = False
            
        
    
    def _TestPathComponents( self, path: str ):
        
        path_components = ClientNetworkingFunctions.ConvertPathTextToList( path )
        
        if self._no_more_path_components_than_this:
            
            if len( path_components ) > len( self._path_components ):
                
                raise HydrusExceptions.URLClassException( '"{}" has {} path components, but I will not allow more than my defined {}!'.format( path, len( path_components ), len( self._path_components ) ) )
                
            
        
        for ( index, ( string_match, default ) ) in enumerate( self._path_components ):
            
            if len( path_components ) > index:
                
                path_component = path_components[ index ]
                
                try:
                    
                    string_match.Test( path_component )
                    
                except HydrusExceptions.StringMatchException as e:
                    
                    raise HydrusExceptions.URLClassException( str( e ) )
                    
                
            elif default is None:
                
                if index + 1 == len( self._path_components ):
                    
                    message = '"{}" has {} path components, but I was expecting {}!'.format( path, len( path_components ), len( self._path_components ) )
                    
                else:
                    
                    message = '"{}" has {} path components, but I was expecting at least {} and maybe as many as {}!'.format( path, len( path_components ), index + 1, len( self._path_components ) )
                    
                
                raise HydrusExceptions.URLClassException( message )
                
            
        
    
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
            
        
        if version == 11:
            
            (
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
            ) = old_serialisable_info
            
            ( match_subdomains, keep_matched_subdomains, alphabetise_get_parameters, can_produce_multiple_files, should_be_associated_with_files, keep_fragment ) = booleans
            
            no_more_path_components_than_this = False
            no_more_parameters_than_this = False
            
            booleans = ( match_subdomains, keep_matched_subdomains, alphabetise_get_parameters, no_more_path_components_than_this, no_more_parameters_than_this, can_produce_multiple_files, should_be_associated_with_files, keep_fragment )
            
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
            
            return ( 12, new_serialisable_info )
            
        
        if version == 12:
            
            (
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
            ) = old_serialisable_info
            
            def encode_fixed_string_match_param( s_m: ClientStrings.StringMatch ) -> ClientStrings.StringMatch:
                
                ( match_type, match_value, min_chars, max_chars, example_string ) = s_m.ToTuple()
                
                if match_type == ClientStrings.STRING_MATCH_FIXED:
                    
                    match_value = ClientNetworkingFunctions.ensure_param_component_is_encoded( match_value )
                    example_string = ClientNetworkingFunctions.ensure_param_component_is_encoded( example_string )
                    
                    s_m = ClientStrings.StringMatch(
                        match_type = match_type,
                        match_value = match_value,
                        min_chars = min_chars,
                        max_chars = max_chars,
                        example_string = example_string
                    )
                    
                
                return s_m
                
            
            def encode_fixed_string_match_path( s_m: ClientStrings.StringMatch ) -> ClientStrings.StringMatch:
                
                ( match_type, match_value, min_chars, max_chars, example_string ) = s_m.ToTuple()
                
                if match_type == ClientStrings.STRING_MATCH_FIXED:
                    
                    match_value = ClientNetworkingFunctions.ensure_path_component_is_encoded( match_value )
                    example_string = ClientNetworkingFunctions.ensure_path_component_is_encoded( example_string )
                    
                    s_m = ClientStrings.StringMatch(
                        match_type = match_type,
                        match_value = match_value,
                        min_chars = min_chars,
                        max_chars = max_chars,
                        example_string = example_string
                    )
                    
                
                return s_m
                
            
            new_parameters = HydrusSerialisable.SerialisableList()
            
            for ( name, ( serialisable_value_string_match, default_value ) ) in serialisable_parameters:
                
                # we are converting from post[id] to post%5Bid%5D
                name = ClientNetworkingFunctions.ensure_param_component_is_encoded( name )
                
                value_string_match = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_value_string_match )
                
                value_string_match = encode_fixed_string_match_param( value_string_match )
                
                parameter = URLClassParameterFixedName(
                    name = name,
                    value_string_match = value_string_match
                )
                
                if default_value is not None:
                    
                    default_value = ClientNetworkingFunctions.ensure_param_component_is_encoded( default_value )
                    
                    parameter.SetDefaultValue( default_value )
                    
                
                new_parameters.append( parameter )
                
            
            serialisable_parameters = new_parameters.GetSerialisableTuple()
            
            path_components = [ ( HydrusSerialisable.CreateFromSerialisableTuple( serialisable_string_match ), default ) for ( serialisable_string_match, default ) in serialisable_path_components ]
            
            new_path_components = []
            
            for ( string_match, default ) in path_components:
                
                string_match = encode_fixed_string_match_path( string_match )
                
                if default is not None:
                    
                    default = ClientNetworkingFunctions.ensure_path_component_is_encoded( default )
                    
                
                new_path_components.append( ( string_match, default ) )
                
            
            serialisable_path_components = [ ( string_match.GetSerialisableTuple(), default ) for ( string_match, default ) in new_path_components ]
            
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
            
            return ( 13, new_serialisable_info )
            
        
        if version == 13:
            
            (
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
            ) = old_serialisable_info
            
            ( match_subdomains, keep_matched_subdomains, alphabetise_get_parameters, no_more_path_components_than_this, no_more_parameters_than_this, can_produce_multiple_files, should_be_associated_with_files, keep_fragment ) = booleans
            
            api_lookup_converter = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_api_lookup_converter )
            
            keep_extra_parameters_for_server = True
            
            if no_more_parameters_than_this or api_lookup_converter.MakesChanges() or url_type not in ( HC.URL_TYPE_GALLERY, HC.URL_TYPE_WATCHABLE ):
                
                keep_extra_parameters_for_server = False
                
            
            booleans = ( match_subdomains, keep_matched_subdomains, alphabetise_get_parameters, no_more_path_components_than_this, no_more_parameters_than_this, keep_extra_parameters_for_server, can_produce_multiple_files, should_be_associated_with_files, keep_fragment )
            
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
            
            return ( 14, new_serialisable_info )
            
        
        if version == 14:
            
            (
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
            ) = old_serialisable_info
            
            ( match_subdomains, keep_matched_subdomains, alphabetise_get_parameters, no_more_path_components_than_this, no_more_parameters_than_this, keep_extra_parameters_for_server, can_produce_multiple_files, should_be_associated_with_files, keep_fragment ) = booleans
            
            url_domain_mask = URLDomainMask( raw_domains = [ netloc ], match_subdomains = match_subdomains, keep_matched_subdomains = keep_matched_subdomains )
            
            booleans = ( alphabetise_get_parameters, no_more_path_components_than_this, no_more_parameters_than_this, keep_extra_parameters_for_server, can_produce_multiple_files, should_be_associated_with_files, keep_fragment )
            
            serialisable_url_domain_mask = url_domain_mask.GetSerialisableTuple()
            
            new_serialisable_info = (
                serialisable_url_class_key,
                url_type,
                preferred_scheme,
                serialisable_url_domain_mask,
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
            
            return ( 15, new_serialisable_info )
            
        
    
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
        
    
    def GetAPILookupConverter( self ):
        
        return self._api_lookup_converter
        
    
    def GetAPIURL( self, url ):
        
        request_url = self.Normalise( url, for_server = True )
        
        return self._api_lookup_converter.Convert( request_url )
        
    
    def GetClassKey( self ):
        
        return self._url_class_key
        
    
    def GetExampleURL( self, encoded = True ):
        
        if encoded:
            
            return ClientNetworkingFunctions.EnsureURLIsEncoded( self._example_url )
            
        else:
            
            return self._example_url
            
        
    
    def GetGalleryIndexValues( self ):
        
        return ( self._gallery_index_type, self._gallery_index_identifier, self._gallery_index_delta )
        
    
    def GetHeaderOverrides( self ):
        
        return self._header_overrides
        
    
    def GetNextGalleryPage( self, url ):
        
        url = self.Normalise( url, for_server = True )
        
        p = ClientNetworkingFunctions.ParseURL( url )
        
        scheme = p.scheme
        netloc = p.netloc
        path = p.path
        query = p.query
        params = ''
        fragment = p.fragment
        
        if self._gallery_index_type == GALLERY_INDEX_TYPE_PATH_COMPONENT:
            
            page_index_path_component_index = self._gallery_index_identifier
            
            path_components = ClientNetworkingFunctions.ConvertPathTextToList( path )
            
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
            
        
        next_gallery_url = urllib.parse.urlunparse( ( scheme, netloc, path, params, query, fragment ) )
        
        return next_gallery_url
        
    
    def GetParameters( self ) -> list[ URLClassParameterFixedName ]:
        
        return self._parameters
        
    
    def GetPathComponents( self ):
        
        return self._path_components
        
    
    def GetPreferredScheme( self ):
        
        return self._preferred_scheme
        
    
    def GetReferralURL( self, url, referral_url ):
        
        if self._send_referral_url == SEND_REFERRAL_URL_ONLY_IF_PROVIDED:
            
            return referral_url
            
        elif self._send_referral_url == SEND_REFERRAL_URL_NEVER:
            
            return None
            
        elif self._send_referral_url in ( SEND_REFERRAL_URL_CONVERTER_IF_NONE_PROVIDED, SEND_REFERRAL_URL_ONLY_CONVERTER ):
            
            request_url = self.Normalise( url, for_server = True )
            
            try:
                
                converted_referral_url = self._referral_url_converter.Convert( request_url )
                
            except HydrusExceptions.StringConvertException:
                
                return referral_url
                
            
            p1 = self._send_referral_url == SEND_REFERRAL_URL_ONLY_CONVERTER
            p2 = self._send_referral_url == SEND_REFERRAL_URL_CONVERTER_IF_NONE_PROVIDED and referral_url is None
            
            if p1 or p2:
                
                return converted_referral_url
                
            else:
                
                return referral_url
                
            
        
        return referral_url
        
    
    def GetReferralURLInfo( self ):
        
        return ( self._send_referral_url, self._referral_url_converter )
        
    
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
        
        # note, we have added a bunch of extra params and stuff here, and here's another one, 2024-05:
            # adding domain length so that api.vxtwitter.com will match before vxtwitter.com. subdomains before domains!
        
        len_domain = self._url_domain_mask.GetSortingComplexity()
        num_required_path_components = len( [ 1 for ( string_match, default ) in self._path_components if default is None ] )
        num_total_path_components = len( self._path_components )
        num_required_parameters = len( [ 1 for parameter in self._parameters if not parameter.HasDefaultValue() ] )
        num_total_parameters = len( self._parameters )
        
        try:
            
            len_example_url = len( self.Normalise( self._example_url, for_server = True ) )
            
        except:
            
            len_example_url = len( self._example_url )
            
        
        return ( len_domain, num_required_path_components, num_total_path_components, num_required_parameters, num_total_parameters, len_example_url )
        
    
    def GetURLBooleans( self ):
        
        return ( self._alphabetise_get_parameters, self._can_produce_multiple_files, self._should_be_associated_with_files, self._keep_fragment )
        
    
    def GetURLDomainMask( self ) -> URLDomainMask:
        
        return self._url_domain_mask
        
    
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
        
    
    def KeepExtraParametersForServer( self ):
        
        return self._keep_extra_parameters_for_server
        
    
    def Matches( self, url ):
        
        try:
            
            self.Test( url )
            
            return True
            
        except HydrusExceptions.URLClassException:
            
            return False
            
        
    
    def Normalise( self, url, for_server = False ):
        
        p = ClientNetworkingFunctions.ParseURL( url )
        
        scheme = self._preferred_scheme
        params = ''
        
        if self._keep_fragment:
            
            fragment = p.fragment
            
        else:
            
            fragment = ''
            
        
        path_components = ClientNetworkingFunctions.ConvertPathTextToList( p.path )
        ( query_dict, single_value_parameters, param_order ) = ClientNetworkingFunctions.ConvertQueryTextToDict( p.query )
        
        netloc = self._ClipNetLoc( p.netloc )
        path = self._ClipAndFleshOutPath( path_components, for_server )
        query = self._ClipAndFleshOutQuery( query_dict, single_value_parameters, param_order, for_server )
        
        normalised_url = urllib.parse.urlunparse( ( scheme, netloc, path, params, query, fragment ) )
        
        return normalised_url
        
    
    def NoMorePathComponentsThanThis( self ) -> bool:
        
        return self._no_more_path_components_than_this
        
    
    def NoMoreParametersThanThis( self ) -> bool:
        
        return self._no_more_parameters_than_this
        
    
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
        
    
    def SetKeepExtraParametersForServer( self, value ):
        
        self._keep_extra_parameters_for_server = value
        
    
    def SetNoMorePathComponentsThanThis( self, no_more: bool ):
        
        self._no_more_path_components_than_this = no_more
        
    
    def SetNoMoreParametersThanThis( self, no_more: bool ):
        
        self._no_more_parameters_than_this = no_more
        
    
    def SetSingleValueParameterData( self, has_single_value_parameters: bool, single_value_parameters_string_match: ClientStrings.StringMatch ):
        
        self._has_single_value_parameters = has_single_value_parameters
        self._single_value_parameters_string_match = single_value_parameters_string_match
        
    
    def SetURLBooleans(
        self,
        alphabetise_get_parameters: bool,
        can_produce_multiple_files: bool,
        should_be_associated_with_files: bool,
        keep_fragment: bool
    ):
        
        self._alphabetise_get_parameters = alphabetise_get_parameters
        self._can_produce_multiple_files = can_produce_multiple_files
        self._should_be_associated_with_files = should_be_associated_with_files
        self._keep_fragment = keep_fragment
        
    
    def SetURLDomainMask( self, url_domain_mask: URLDomainMask ):
        
        self._url_domain_mask = url_domain_mask
        
    
    def ShouldAssociateWithFiles( self ):
        
        return self._should_be_associated_with_files
        
    
    def Test( self, url ):
        
        url = ClientNetworkingFunctions.EnsureURLIsEncoded( url )
        
        p = ClientNetworkingFunctions.ParseURL( url )
        
        self._url_domain_mask.Test( p.netloc )
        
        path = p.path
        query = p.query
        
        self._TestPathComponents( path )
        
        ( query_dict, single_value_parameters, param_order ) = ClientNetworkingFunctions.ConvertQueryTextToDict( query )
        
        if self._no_more_parameters_than_this:
            
            good_fixed_names = { parameter.GetName() for parameter in self._parameters if isinstance( parameter, URLClassParameterFixedName ) }
            
            for ( name, value ) in query_dict.items():
                
                if name not in good_fixed_names:
                    
                    raise HydrusExceptions.URLClassException( f'"This has a "{name}" parameter, but I am set to not allow any unexpected parameters!' )
                    
                
            
        
        for parameter in self._parameters:
            
            if isinstance( parameter, URLClassParameterFixedName ):
                
                name = parameter.GetName()
                
                if name not in query_dict:
                    
                    if parameter.MustBeInOriginalURL():
                        
                        raise HydrusExceptions.URLClassException( f'{name} not found in {p.query}' )
                        
                    else:
                        
                        continue
                        
                    
                
                value = query_dict[ name ]
                
                try:
                    
                    parameter.TestValue( value )
                    
                except HydrusExceptions.StringMatchException as e:
                    
                    raise HydrusExceptions.URLClassException( f'Problem with {name}: ' + str( e ) )
                    
                
            
        
        if len( single_value_parameters ) > 0 and not self._has_single_value_parameters and self._no_more_parameters_than_this:
            
            raise HydrusExceptions.URLClassException( '"{}" has unexpected single-value parameters, but I am set to not allow any unexpected parameters!'.format( query ) )
            
        
        if self._has_single_value_parameters:
            
            if len( single_value_parameters ) == 0:
                
                raise HydrusExceptions.URLClassException( 'Was expecting single-value parameter(s), but this URL did not seem to have any.' )
                
            
            for single_value_parameter in single_value_parameters:
                
                try:
                    
                    self._single_value_parameters_string_match.Test( single_value_parameter )
                    
                except HydrusExceptions.StringMatchException as e:
                    
                    raise HydrusExceptions.URLClassException( str( e ) )
                    
                
            
        
    
    def UsesAPIURL( self ):
        
        return self._api_lookup_converter.MakesChanges()
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_URL_CLASS ] = URLClass
