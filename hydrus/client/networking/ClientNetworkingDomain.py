import collections
import collections.abc
import functools
import threading
import time
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusLists
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTime
from hydrus.core.networking import HydrusNetworking

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientThreading
from hydrus.client.networking import ClientNetworkingContexts
from hydrus.client.networking import ClientNetworkingFunctions
from hydrus.client.networking import ClientNetworkingURLClass

VALID_DENIED = 0
VALID_APPROVED = 1
VALID_UNKNOWN = 2

valid_str_lookup = {
    VALID_DENIED : 'denied',
    VALID_APPROVED : 'approved',
    VALID_UNKNOWN : 'pending'
}

valid_enum_lookup = { value : key for ( key, value ) in valid_str_lookup.items() }

class NetworkDomainManager( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_DOMAIN_MANAGER
    SERIALISABLE_NAME = 'Domain Manager'
    SERIALISABLE_VERSION = 7
    
    def __init__( self ):
        
        super().__init__()
        
        self._gugs = HydrusSerialisable.SerialisableList()
        self._url_classes = HydrusSerialisable.SerialisableList()
        self._parsers = HydrusSerialisable.SerialisableList()
        self._network_contexts_to_custom_header_dicts = collections.defaultdict( dict )
        
        self._parser_namespaces = []
        
        self._gug_keys_to_display = set()
        
        self._url_class_keys_to_display = set()
        self._url_class_keys_to_parser_keys = HydrusSerialisable.SerialisableBytesDictionary()
        
        self._url_domain_masks_to_url_classes = collections.defaultdict( list )
        
        self._second_level_domains_to_network_infrastructure_errors = collections.defaultdict( list )
        
        from hydrus.client.importing.options import TagImportOptions
        
        self._file_post_default_tag_import_options = TagImportOptions.TagImportOptions()
        self._watchable_default_tag_import_options = TagImportOptions.TagImportOptions()
        
        self._url_class_keys_to_default_tag_import_options = {}
        
        from hydrus.client.importing.options import NoteImportOptions
        
        self._file_post_default_note_import_options = NoteImportOptions.NoteImportOptions()
        self._watchable_default_note_import_options = NoteImportOptions.NoteImportOptions()
        
        self._url_class_keys_to_default_note_import_options = {}
        
        self._gug_keys_to_gugs = {}
        self._gug_names_to_gugs = {}
        
        self._parser_keys_to_parsers = {}
        
        self._dirty = False
        
        self._lock = threading.Lock()
        
        self._RecalcCache()
        
    
    def _CleanURLClassKeysToParserKeys( self ):
        
        api_pairs = ClientNetworkingURLClass.ConvertURLClassesIntoAPIPairs( self._url_classes )
        
        # anything that goes to an api url will be parsed by that api's parser--it can't have its own
        for ( a, b ) in api_pairs:
            
            unparseable_url_class_key = a.GetClassKey()
            
            if unparseable_url_class_key in self._url_class_keys_to_parser_keys:
                
                del self._url_class_keys_to_parser_keys[ unparseable_url_class_key ]
                
            
        
    
    def _GetDefaultNoteImportOptionsForURL( self, referral_url: typing.Optional[ str ], file_or_post_url: str ):
        
        urls_to_examine_in_order = [ file_or_post_url ]
        
        if referral_url is not None:
            
            urls_to_examine_in_order.append( referral_url )
            
        
        ClientNetworkingFunctions.NetworkReportMode( f'Doing default tag import options lookup for {urls_to_examine_in_order}.' )
        
        for url in urls_to_examine_in_order:
            
            url_class = self._GetURLClass( url )
            
            if url_class is not None:
                
                try:
                    
                    # we store options for the final link in the api redirect chain
                    ( url_class, api_url ) = self._GetNormalisedAPIURLClassAndURL( url )
                    
                except HydrusExceptions.URLClassException as e:
                    
                    ClientNetworkingFunctions.NetworkReportMode( f'Failed to API-redirect-resolve on {url}: {e}.' )
                    
                    continue
                    
                
                url_class_key = url_class.GetClassKey()
                
                if url_class_key in self._url_class_keys_to_default_note_import_options:
                    
                    ClientNetworkingFunctions.NetworkReportMode( f'{url} resolved to specific note import options.' )
                    
                    return self._url_class_keys_to_default_note_import_options[ url_class_key ]
                    
                else:
                    
                    url_type = url_class.GetURLType()
                    
                    if url_type == HC.URL_TYPE_POST:
                        
                        ClientNetworkingFunctions.NetworkReportMode( f'{url} resolved to default post note import options.' )
                        
                        return self._file_post_default_note_import_options
                        
                    elif url_type == HC.URL_TYPE_WATCHABLE:
                        
                        ClientNetworkingFunctions.NetworkReportMode( f'{url} resolved to default watcher note import options.' )
                        
                        return self._watchable_default_note_import_options
                        
                    
                
            
        
        ClientNetworkingFunctions.NetworkReportMode( f'No matches; resolving to default post note import options.' )
        
        return self._file_post_default_note_import_options
        
    
    def _GetDefaultTagImportOptionsForURL( self, referral_url: typing.Optional[ str ], file_or_post_url: str ):
        
        urls_to_examine_in_order = [ file_or_post_url ]
        
        if referral_url is not None:
            
            urls_to_examine_in_order.append( referral_url )
            
        
        ClientNetworkingFunctions.NetworkReportMode( f'Doing default tag import options lookup for {urls_to_examine_in_order}.' )
        
        for url in urls_to_examine_in_order:
            
            url_class = self._GetURLClass( url )
            
            if url_class is not None:
                
                try:
                    
                    # we store options for the final link in the api redirect chain
                    ( url_class, api_url ) = self._GetNormalisedAPIURLClassAndURL( url )
                    
                except HydrusExceptions.URLClassException as e:
                    
                    ClientNetworkingFunctions.NetworkReportMode( f'Failed to API-redirect-resolve on {url}: {e}.' )
                    
                    continue
                    
                
                url_class_key = url_class.GetClassKey()
                
                if url_class_key in self._url_class_keys_to_default_tag_import_options:
                    
                    ClientNetworkingFunctions.NetworkReportMode( f'{url} resolved to specific tag import options.' )
                    
                    return self._url_class_keys_to_default_tag_import_options[ url_class_key ]
                    
                else:
                    
                    url_type = url_class.GetURLType()
                    
                    if url_type == HC.URL_TYPE_POST:
                        
                        ClientNetworkingFunctions.NetworkReportMode( f'{url} resolved to default post tag import options.' )
                        
                        return self._file_post_default_tag_import_options
                        
                    elif url_type == HC.URL_TYPE_WATCHABLE:
                        
                        ClientNetworkingFunctions.NetworkReportMode( f'{url} resolved to default watcher tag import options.' )
                        
                        return self._watchable_default_tag_import_options
                        
                    
                
            
        
        ClientNetworkingFunctions.NetworkReportMode( f'No matches; resolving to default post tag import options.' )
        
        return self._file_post_default_tag_import_options
        
    
    def _GetGUG( self, gug_key_and_name ):
        
        ( gug_key, gug_name ) = gug_key_and_name
        
        if gug_key in self._gug_keys_to_gugs:
            
            return self._gug_keys_to_gugs[ gug_key ]
            
        elif gug_name in self._gug_names_to_gugs:
            
            return self._gug_names_to_gugs[ gug_name ]
            
        else:
            
            return None
            
        
    
    def _GetNormalisedAPIURLClassAndURL( self, url ) -> tuple[ ClientNetworkingURLClass.URLClass, str ]:
        
        url_class = self._GetURLClass( url )
        
        if url_class is None:
            
            raise HydrusExceptions.URLClassException( 'Could not find a URL Class for ' + url + '!' )
            
        
        seen_url_classes = set()
        
        seen_url_classes.add( url_class )
        
        api_url_class = url_class
        api_url = url
        
        while api_url_class.UsesAPIURL():
            
            api_url = api_url_class.GetAPIURL( api_url )
            
            api_url_class = self._GetURLClass( api_url )
            
            if api_url_class is None:
                
                raise HydrusExceptions.URLClassException( 'Could not find an API/Redirect URL Class for ' + api_url + ' URL, which originally came from ' + url + '!' )
                
            
            if api_url_class in seen_url_classes:
                
                loop_size = len( seen_url_classes )
                
                if loop_size == 1:
                    
                    message = 'Could not find an API/Redirect URL Class for ' + url + ' as the url class API-linked to itself!'
                    
                elif loop_size == 2:
                    
                    message = 'Could not find an API/Redirect URL Class for ' + url + ' as the url class and its API url class API-linked to each other!'
                    
                else:
                    
                    message = 'Could not find an API/Redirect URL Class for ' + url + ' as it and its API url classes linked in a loop of size ' + HydrusNumbers.ToHumanInt( loop_size ) + '!'
                    
                
                raise HydrusExceptions.URLClassException( message )
                
            
            seen_url_classes.add( api_url_class )
            
        
        api_url = api_url_class.Normalise( api_url, for_server = True )
        
        return ( api_url_class, api_url )
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_gugs = self._gugs.GetSerialisableTuple()
        serialisable_gug_keys_to_display = [ gug_key.hex() for gug_key in self._gug_keys_to_display ]
        
        serialisable_url_classes = self._url_classes.GetSerialisableTuple()
        serialisable_url_class_keys_to_display = [ url_class_key.hex() for url_class_key in self._url_class_keys_to_display ]
        serialisable_url_class_keys_to_parser_keys = self._url_class_keys_to_parser_keys.GetSerialisableTuple()
        
        serialisable_file_post_default_tag_import_options = self._file_post_default_tag_import_options.GetSerialisableTuple()
        serialisable_watchable_default_tag_import_options = self._watchable_default_tag_import_options.GetSerialisableTuple()
        serialisable_url_class_keys_to_default_tag_import_options = [ ( url_class_key.hex(), tag_import_options.GetSerialisableTuple() ) for ( url_class_key, tag_import_options ) in self._url_class_keys_to_default_tag_import_options.items() ]
        
        serialisable_default_tag_import_options_tuple = ( serialisable_file_post_default_tag_import_options, serialisable_watchable_default_tag_import_options, serialisable_url_class_keys_to_default_tag_import_options )
        
        serialisable_file_post_default_note_import_options = self._file_post_default_note_import_options.GetSerialisableTuple()
        serialisable_watchable_default_note_import_options = self._watchable_default_note_import_options.GetSerialisableTuple()
        serialisable_url_class_keys_to_default_note_import_options = [ ( url_class_key.hex(), note_import_options.GetSerialisableTuple() ) for ( url_class_key, note_import_options ) in self._url_class_keys_to_default_note_import_options.items() ]
        
        serialisable_default_note_import_options_tuple = ( serialisable_file_post_default_note_import_options, serialisable_watchable_default_note_import_options, serialisable_url_class_keys_to_default_note_import_options )
        
        serialisable_parsers = self._parsers.GetSerialisableTuple()
        serialisable_network_contexts_to_custom_header_dicts = [ ( network_context.GetSerialisableTuple(), list( custom_header_dict.items() ) ) for ( network_context, custom_header_dict ) in self._network_contexts_to_custom_header_dicts.items() ]
        
        return ( serialisable_gugs, serialisable_gug_keys_to_display, serialisable_url_classes, serialisable_url_class_keys_to_display, serialisable_url_class_keys_to_parser_keys, serialisable_default_tag_import_options_tuple, serialisable_default_note_import_options_tuple, serialisable_parsers, serialisable_network_contexts_to_custom_header_dicts )
        
    
    def _GetURLClass( self, url ):
        
        try:
            
            domain = ClientNetworkingFunctions.ConvertURLIntoDomain( url )
            
        except HydrusExceptions.URLClassException:
            
            return None
            
        
        url_domain_masks = self._GetURLDomainMasks( domain )
        
        for url_domain_mask in url_domain_masks:
            
            url_classes = self._url_domain_masks_to_url_classes[ url_domain_mask ]
            
            for url_class in url_classes:
                
                try:
                    
                    url_class.Test( url )
                    
                    return url_class
                    
                except HydrusExceptions.URLClassException:
                    
                    continue
                    
                
            
        
        return None
        
    
    @functools.lru_cache( 128 )
    def _GetURLDomainMasks( self, domain ) -> list[ ClientNetworkingURLClass.URLDomainMask ]:
        
        url_domain_masks = []
        
        for url_domain_mask in self._url_domain_masks_to_url_classes.keys():
            
            if url_domain_mask.Matches( domain ):
                
                url_domain_masks.append( url_domain_mask )
                
            
        
        url_domain_masks.sort( key = lambda udm: udm.GetSortingComplexity(), reverse = True )
        
        return url_domain_masks
        
    
    def _GetURLToFetch( self, url: str ):
        
        url_class = self._GetURLClass( url )
        
        if url_class is None:
            
            return url
            
        
        try:
            
            ( url_class, url_to_fetch ) = self._GetNormalisedAPIURLClassAndURL( url )
            
        except HydrusExceptions.URLClassException as e:
            
            raise HydrusExceptions.URLClassException( 'Could not find a URL class for ' + url + '!' + '\n' * 2 + str( e ) )
            
        
        return url_to_fetch
        
    
    def _GetURLToFetchAndParser( self, url ):
        
        try:
            
            ( parser_url_class, parser_url ) = self._GetNormalisedAPIURLClassAndURL( url )
            
        except HydrusExceptions.URLClassException as e:
            
            raise HydrusExceptions.URLClassException( 'Could not find a URL class for ' + url + '!' + '\n' * 2 + str( e ) )
            
        
        url_class_key = parser_url_class.GetClassKey()
        
        if url_class_key in self._url_class_keys_to_parser_keys:
            
            parser_key = self._url_class_keys_to_parser_keys[ url_class_key ]
            
            if parser_key is not None and parser_key in self._parser_keys_to_parsers:
                
                return ( parser_url, self._parser_keys_to_parsers[ parser_key ] )
                
            
        
        raise HydrusExceptions.URLClassException( 'Could not find a parser for ' + parser_url_class.GetName() + ' URL Class!' )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_gugs, serialisable_gug_keys_to_display, serialisable_url_classes, serialisable_url_class_keys_to_display, serialisable_url_class_keys_to_parser_keys, serialisable_default_tag_import_options_tuple, serialisable_default_note_import_options_tuple, serialisable_parsers, serialisable_network_contexts_to_custom_header_dicts ) = serialisable_info
        
        self._gugs = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_gugs )
        
        self._gug_keys_to_display = { bytes.fromhex( serialisable_gug_key ) for serialisable_gug_key in serialisable_gug_keys_to_display }
        
        self._url_classes = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_url_classes )
        
        self._url_class_keys_to_display = { bytes.fromhex( serialisable_url_class_key ) for serialisable_url_class_key in serialisable_url_class_keys_to_display }
        self._url_class_keys_to_parser_keys = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_url_class_keys_to_parser_keys )
        
        ( serialisable_file_post_default_tag_import_options, serialisable_watchable_default_tag_import_options, serialisable_url_class_keys_to_default_tag_import_options ) = serialisable_default_tag_import_options_tuple
        
        self._file_post_default_tag_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_post_default_tag_import_options )
        self._watchable_default_tag_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_watchable_default_tag_import_options )
        
        self._url_class_keys_to_default_tag_import_options = { bytes.fromhex( serialisable_url_class_key ) : HydrusSerialisable.CreateFromSerialisableTuple( serialisable_tag_import_options ) for ( serialisable_url_class_key, serialisable_tag_import_options ) in serialisable_url_class_keys_to_default_tag_import_options }
        
        ( serialisable_file_post_default_note_import_options, serialisable_watchable_default_note_import_options, serialisable_url_class_keys_to_default_note_import_options ) = serialisable_default_note_import_options_tuple
        
        self._file_post_default_note_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_post_default_note_import_options )
        self._watchable_default_note_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_watchable_default_note_import_options )
        
        self._url_class_keys_to_default_note_import_options = { bytes.fromhex( serialisable_url_class_key ) : HydrusSerialisable.CreateFromSerialisableTuple( serialisable_note_import_options ) for ( serialisable_url_class_key, serialisable_note_import_options ) in serialisable_url_class_keys_to_default_note_import_options }
        
        self._parsers = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_parsers )
        
        self._network_contexts_to_custom_header_dicts = collections.defaultdict( dict )
        
        for ( serialisable_network_context, custom_header_dict_items ) in serialisable_network_contexts_to_custom_header_dicts:
            
            network_context = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_network_context )
            custom_header_dict = dict( custom_header_dict_items )
            
            self._network_contexts_to_custom_header_dicts[ network_context ] = custom_header_dict
            
        
    
    def _RecalcCache( self ):
        
        self._GetURLDomainMasks.cache_clear()
        
        self._url_domain_masks_to_url_classes = collections.defaultdict( list )
        
        for url_class in self._url_classes:
            
            self._url_domain_masks_to_url_classes[ url_class.GetURLDomainMask() ].append( url_class )
            
        
        for url_classes in self._url_domain_masks_to_url_classes.values():
            
            ClientNetworkingURLClass.SortURLClassesListDescendingComplexity( url_classes )
            
        
        self._gug_keys_to_gugs = { gug.GetGUGKey() : gug for gug in self._gugs }
        self._gug_names_to_gugs = { gug.GetName() : gug for gug in self._gugs }
        
        self._parser_keys_to_parsers = { parser.GetParserKey() : parser for parser in self._parsers }
        
        namespaces = set()
        
        for parser in self._parsers:
            
            namespaces.update( parser.GetNamespaces() )
            
        
        self._parser_namespaces = sorted( namespaces )
        
    
    def _SetDirty( self ):
        
        self._dirty = True
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( serialisable_url_classes, serialisable_network_contexts_to_custom_header_dicts ) = old_serialisable_info
            
            url_classes = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_url_classes )
            
            url_class_names_to_display = {}
            url_class_names_to_page_parser_keys = HydrusSerialisable.SerialisableBytesDictionary()
            url_class_names_to_gallery_parser_keys = HydrusSerialisable.SerialisableBytesDictionary()
            
            for url_class in url_classes:
                
                name = url_class.GetName()
                
                if url_class.IsPostURL():
                    
                    url_class_names_to_display[ name ] = True
                    
                    url_class_names_to_page_parser_keys[ name ] = None
                    
                
                if url_class.IsGalleryURL() or url_class.IsWatchableURL():
                    
                    url_class_names_to_gallery_parser_keys[ name ] = None
                    
                
            
            serialisable_url_class_names_to_display = list(url_class_names_to_display.items())
            serialisable_url_class_names_to_page_parser_keys = url_class_names_to_page_parser_keys.GetSerialisableTuple()
            serialisable_url_class_names_to_gallery_parser_keys = url_class_names_to_gallery_parser_keys.GetSerialisableTuple()
            
            new_serialisable_info = ( serialisable_url_classes, serialisable_url_class_names_to_display, serialisable_url_class_names_to_page_parser_keys, serialisable_url_class_names_to_gallery_parser_keys, serialisable_network_contexts_to_custom_header_dicts )
            
            return ( 2, new_serialisable_info )
            
        
        if version == 2:
            
            ( serialisable_url_classes, serialisable_url_class_names_to_display, serialisable_url_class_names_to_page_parser_keys, serialisable_url_class_names_to_gallery_parser_keys, serialisable_network_contexts_to_custom_header_dicts ) = old_serialisable_info
            
            parsers = HydrusSerialisable.SerialisableList()
            
            serialisable_parsing_parsers = parsers.GetSerialisableTuple()
            
            url_class_names_to_display = dict( serialisable_url_class_names_to_display )
            
            url_class_keys_to_display = []
            
            url_class_names_to_gallery_parser_keys = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_url_class_names_to_gallery_parser_keys )
            url_class_names_to_page_parser_keys = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_url_class_names_to_page_parser_keys )
            
            url_class_keys_to_parser_keys = HydrusSerialisable.SerialisableBytesDictionary()
            
            url_classes = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_url_classes )
            
            for url_class in url_classes:
                
                url_class_key = url_class.GetClassKey()
                
                name = url_class.GetName()
                
                if name in url_class_names_to_display and url_class_names_to_display[ name ]:
                    
                    url_class_keys_to_display.append( url_class_key )
                    
                
            
            serialisable_url_classes = url_classes.GetSerialisableTuple() # added random key this week, so save these changes back again!
            
            serialisable_url_class_keys_to_display = [ url_class_key.hex() for url_class_key in url_class_keys_to_display ]
            
            serialisable_url_class_keys_to_parser_keys = url_class_keys_to_parser_keys.GetSerialisableTuple()
            
            new_serialisable_info = ( serialisable_url_classes, serialisable_url_class_keys_to_display, serialisable_url_class_keys_to_parser_keys, serialisable_parsing_parsers, serialisable_network_contexts_to_custom_header_dicts )
            
            return ( 3, new_serialisable_info )
            
        
        if version == 3:
            
            ( serialisable_url_classes, serialisable_url_class_keys_to_display, serialisable_url_class_keys_to_parser_keys, serialisable_parsing_parsers, serialisable_network_contexts_to_custom_header_dicts ) = old_serialisable_info
            
            from hydrus.client.importing.options import TagImportOptions
            
            file_post_default_tag_import_options = TagImportOptions.TagImportOptions()
            watchable_default_tag_import_options = TagImportOptions.TagImportOptions()
            
            url_class_keys_to_default_tag_import_options = {}
            
            serialisable_file_post_default_tag_import_options = file_post_default_tag_import_options.GetSerialisableTuple()
            serialisable_watchable_default_tag_import_options = watchable_default_tag_import_options.GetSerialisableTuple()
            serialisable_url_class_keys_to_default_tag_import_options = [ ( url_class_key.hex(), tag_import_options.GetSerialisableTuple() ) for ( url_class_key, tag_import_options ) in url_class_keys_to_default_tag_import_options.items() ]
            
            serialisable_default_tag_import_options_tuple = ( serialisable_file_post_default_tag_import_options, serialisable_watchable_default_tag_import_options, serialisable_url_class_keys_to_default_tag_import_options )
            
            new_serialisable_info = ( serialisable_url_classes, serialisable_url_class_keys_to_display, serialisable_url_class_keys_to_parser_keys, serialisable_default_tag_import_options_tuple, serialisable_parsing_parsers, serialisable_network_contexts_to_custom_header_dicts )
            
            return ( 4, new_serialisable_info )
            
        
        if version == 4:
            
            ( serialisable_url_classes, serialisable_url_class_keys_to_display, serialisable_url_class_keys_to_parser_keys, serialisable_default_tag_import_options_tuple, serialisable_parsing_parsers, serialisable_network_contexts_to_custom_header_dicts ) = old_serialisable_info
            
            gugs = HydrusSerialisable.SerialisableList()
            
            serialisable_gugs = gugs.GetSerialisableTuple()
            
            new_serialisable_info = ( serialisable_gugs, serialisable_url_classes, serialisable_url_class_keys_to_display, serialisable_url_class_keys_to_parser_keys, serialisable_default_tag_import_options_tuple, serialisable_parsing_parsers, serialisable_network_contexts_to_custom_header_dicts )
            
            return ( 5, new_serialisable_info )
            
        
        if version == 5:
            
            ( serialisable_gugs, serialisable_url_classes, serialisable_url_class_keys_to_display, serialisable_url_class_keys_to_parser_keys, serialisable_default_tag_import_options_tuple, serialisable_parsing_parsers, serialisable_network_contexts_to_custom_header_dicts ) = old_serialisable_info
            
            gugs = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_gugs )
            
            gug_keys_to_display = [ gug.GetGUGKey() for gug in gugs if 'ugoira' not in gug.GetName() ]
            
            serialisable_gug_keys_to_display = [ gug_key.hex() for gug_key in gug_keys_to_display ]
            
            new_serialisable_info = ( serialisable_gugs, serialisable_gug_keys_to_display, serialisable_url_classes, serialisable_url_class_keys_to_display, serialisable_url_class_keys_to_parser_keys, serialisable_default_tag_import_options_tuple, serialisable_parsing_parsers, serialisable_network_contexts_to_custom_header_dicts )
            
            return ( 6, new_serialisable_info )
            
        
        if version == 6:
            
            ( serialisable_gugs, serialisable_gug_keys_to_display, serialisable_url_classes, serialisable_url_class_keys_to_display, serialisable_url_class_keys_to_parser_keys, serialisable_default_tag_import_options_tuple, serialisable_parsing_parsers, serialisable_network_contexts_to_custom_header_dicts ) = old_serialisable_info
            
            from hydrus.client.importing.options import NoteImportOptions
            
            file_post_default_note_import_options = NoteImportOptions.NoteImportOptions()
            watchable_default_note_import_options = NoteImportOptions.NoteImportOptions()
            
            url_class_keys_to_default_note_import_options = {}
            
            serialisable_file_post_default_note_import_options = file_post_default_note_import_options.GetSerialisableTuple()
            serialisable_watchable_default_note_import_options = watchable_default_note_import_options.GetSerialisableTuple()
            serialisable_url_class_keys_to_default_note_import_options = [ ( url_class_key.hex(), note_import_options.GetSerialisableTuple() ) for ( url_class_key, note_import_options ) in url_class_keys_to_default_note_import_options.items() ]
            
            serialisable_default_note_import_options_tuple = ( serialisable_file_post_default_note_import_options, serialisable_watchable_default_note_import_options, serialisable_url_class_keys_to_default_note_import_options )
            
            new_serialisable_info = ( serialisable_gugs, serialisable_gug_keys_to_display, serialisable_url_classes, serialisable_url_class_keys_to_display, serialisable_url_class_keys_to_parser_keys, serialisable_default_tag_import_options_tuple, serialisable_default_note_import_options_tuple, serialisable_parsing_parsers, serialisable_network_contexts_to_custom_header_dicts )
            
            return ( 7, new_serialisable_info )
            
        
    
    def AddGUGs( self, new_gugs ):
        
        with self._lock:
            
            gugs = list( self._gugs )
            
            for gug in new_gugs:
                
                gug.SetNonDupeName( [ g.GetName() for g in gugs ] )
                
                gugs.append( gug )
                
            
        
        self.SetGUGs( gugs )
        
    
    def AddParsers( self, new_parsers ):
        
        with self._lock:
            
            parsers = list( self._parsers )
            
            for parser in new_parsers:
                
                parser.SetNonDupeName( [ p.GetName() for p in parsers ] )
                
                parsers.append( parser )
                
            
        
        self.SetParsers( parsers )
        
    
    def AddURLClasses( self, new_url_classes ):
        
        with self._lock:
            
            url_classes = list( self._url_classes )
            
            for url_class in new_url_classes:
                
                url_class.SetNonDupeName( [ u.GetName() for u in url_classes ] )
                
                url_classes.append( url_class )
                
            
        
        self.SetURLClasses( url_classes )
        
    
    def AlreadyHaveExactlyTheseHeaders( self, network_context, headers_list ):
        
        with self._lock:
            
            if network_context in self._network_contexts_to_custom_header_dicts:
                
                custom_headers_dict = self._network_contexts_to_custom_header_dicts[ network_context ]
                
                if len( headers_list ) != len( custom_headers_dict ):
                    
                    return False
                    
                
                for ( key, value, reason ) in headers_list:
                    
                    if key not in custom_headers_dict:
                        
                        return False
                        
                    
                    ( existing_value, existing_approved, existing_reason ) = custom_headers_dict[ key ]
                    
                    if existing_value != value:
                        
                        return False
                        
                    
                
                return True
                
            
        
        return False
        
    
    def AlreadyHaveExactlyThisGUG( self, new_gug ):
        
        with self._lock:
            
            # absent irrelevant variables, do we have the exact same object already in?
            
            gug_key_and_name = new_gug.GetGUGKeyAndName()
            
            dupe_gugs = [ gug.Duplicate() for gug in self._gugs ]
            
            for dupe_gug in dupe_gugs:
                
                dupe_gug.SetGUGKeyAndName( gug_key_and_name )
                
                if dupe_gug.DumpToString() == new_gug.DumpToString():
                    
                    return True
                    
                
            
        
        return False
        
    
    def AlreadyHaveExactlyThisParser( self, new_parser ):
        
        with self._lock:
            
            # absent irrelevant variables, do we have the exact same object already in?
            
            new_name = new_parser.GetName()
            new_parser_key = new_parser.GetParserKey()
            new_example_urls = new_parser.GetExampleURLs()
            new_example_parsing_context = new_parser.GetExampleParsingContext()
            
            dupe_parsers = [ ( parser.Duplicate(), parser ) for parser in self._parsers ]
            
            for ( dupe_parser, parser ) in dupe_parsers:
                
                dupe_parser.SetName( new_name )
                dupe_parser.SetParserKey( new_parser_key )
                dupe_parser.SetExampleURLs( new_example_urls )
                dupe_parser.SetExampleParsingContext( new_example_parsing_context )
                
                if dupe_parser.DumpToString() == new_parser.DumpToString():
                    
                    # since these are the 'same', let's merge example urls
                    
                    parser_example_urls = set( parser.GetExampleURLs() )
                    
                    parser_example_urls.update( new_example_urls )
                    
                    parser_example_urls = list( parser_example_urls )
                    
                    parser.SetExampleURLs( parser_example_urls )
                    
                    self._SetDirty()
                    
                    return True
                    
                
            
        
        return False
        
    
    def AlreadyHaveExactlyThisURLClass( self, new_url_class ):
        
        with self._lock:
            
            # absent irrelevant variables, do we have the exact same object already in?
            
            name = new_url_class.GetName()
            match_key = new_url_class.GetClassKey()
            example_url = new_url_class.GetExampleURL()
            
            dupe_url_classes = [ url_class.Duplicate() for url_class in self._url_classes ]
            
            for dupe_url_class in dupe_url_classes:
                
                dupe_url_class.SetName( name )
                dupe_url_class.SetClassKey( match_key )
                dupe_url_class.SetExampleURL( example_url )
                
                if dupe_url_class.DumpToString() == new_url_class.DumpToString():
                    
                    return True
                    
                
            
        
        return False
        
    
    def AutoAddDomainMetadatas( self, domain_metadatas, approved = VALID_APPROVED ):
        
        for domain_metadata in domain_metadatas:
            
            if not domain_metadata.HasHeaders():
                
                continue
                
            
            with self._lock:
                
                domain = domain_metadata.GetDomain()
                
                network_context = ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_DOMAIN, domain )
                
                headers_list = domain_metadata.GetHeaders()
                
                custom_headers_dict = { key : ( value, approved, reason ) for ( key, value, reason ) in headers_list }
                
                self._network_contexts_to_custom_header_dicts[ network_context ] = custom_headers_dict
                
            
        
    
    def AutoAddURLClassesAndParsers( self, new_url_classes, dupe_url_classes, new_parsers ):
        
        for url_class in new_url_classes:
            
            url_class.RegenerateClassKey()
            
        
        for parser in new_parsers:
            
            parser.RegenerateParserKey()
            
        
        # any existing url matches that already do the job of the new ones should be hung on to but renamed
        
        with self._lock:
            
            prefix = 'zzz - renamed due to auto-import - '
            
            renamees = []
            
            for existing_url_class in self._url_classes:
                
                if existing_url_class.GetName().startswith( prefix ):
                    
                    continue
                    
                
                for new_url_class in new_url_classes:
                    
                    if new_url_class.Matches( existing_url_class.GetExampleURL() ) and existing_url_class.Matches( new_url_class.GetExampleURL() ):
                        
                        # the url matches match each other, so they are doing the same job
                        
                        renamees.append( existing_url_class )
                        
                        break
                        
                    
                
                
            
            for renamee in renamees:
                
                existing_names = [ url_class.GetName() for url_class in self._url_classes if url_class != renamee ]
                
                renamee.SetName( prefix + renamee.GetName() )
                
                renamee.SetNonDupeName( existing_names )
                
            
        
        self.AddURLClasses( new_url_classes )
        self.AddParsers( new_parsers )
        
        # we want to match these url matches and parsers together if possible
        
        with self._lock:
            
            url_classes_to_link = list( new_url_classes )
            
            # if downloader adds existing url match but updated parser, we want to update the existing link
            
            for dupe_url_class in dupe_url_classes:
                
                # this is to make sure we have the right match keys for the link update in a minute
                
                actual_existing_dupe_url_class = self._GetURLClass( dupe_url_class.GetExampleURL() )
                
                if actual_existing_dupe_url_class is not None:
                    
                    url_classes_to_link.append( actual_existing_dupe_url_class )
                    
                
            
            new_url_class_keys_to_parser_keys = NetworkDomainManager.STATICLinkURLClassesAndParsers( url_classes_to_link, new_parsers, {} )
            
            self._url_class_keys_to_parser_keys.update( new_url_class_keys_to_parser_keys )
            
            self._CleanURLClassKeysToParserKeys()
            
        
        # let's do a trytolink just in case there are loose ends due to some dupe being discarded earlier (e.g. url match is new, but parser was not).
        
        self.TryToLinkURLClassesAndParsers()
        
    
    def CanValidateInPopup( self, network_contexts ):
        
        # we can always do this for headers
        
        return True
        
    
    def ConvertURLsToMediaViewerTuples( self, urls ):
        
        show_unmatched_urls_in_media_viewer = CG.client_controller.new_options.GetBoolean( 'show_unmatched_urls_in_media_viewer' )
        
        url_tuples = []
        unmatched_url_tuples = []
        
        with self._lock:
            
            for url in urls:
                
                try:
                    
                    url_class = self._GetURLClass( url )
                    
                except HydrusExceptions.URLClassException:
                    
                    continue
                    
                
                if url_class is None:
                    
                    if show_unmatched_urls_in_media_viewer:
                        
                        try:
                            
                            domain = ClientNetworkingFunctions.ConvertURLIntoDomain( url )
                            
                        except HydrusExceptions.URLClassException:
                            
                            domain = 'unknown'
                            
                        
                        unmatched_url_tuples.append( ( domain, url ) )
                        
                    
                else:
                    
                    url_class_key = url_class.GetClassKey()
                    
                    if url_class_key in self._url_class_keys_to_display:
                        
                        url_class_name = url_class.GetName()
                        
                        if not url_class.GetURLDomainMask().IsSingleRawDomain():
                            
                            try:
                                
                                domain = ClientNetworkingFunctions.ConvertURLIntoDomain( url )
                                
                            except HydrusExceptions.URLClassException:
                                
                                domain = 'unknown'
                                
                            
                            url_class_name = f'{url_class_name} ({domain})'
                            
                        
                        url_tuples.append( ( url_class_name, url ) )
                        
                    
                
                if len( url_tuples ) == 10:
                    
                    break
                    
                
            
        
        url_tuples.sort()
        
        unmatched_url_tuples.sort()
        
        url_tuples.extend( unmatched_url_tuples )
        
        return url_tuples
        
    
    def DeleteCustomHeader( self, network_context: ClientNetworkingContexts.NetworkContext, key: str ):
        
        with self._lock:
            
            if network_context in self._network_contexts_to_custom_header_dicts:
                
                custom_header_dict = self._network_contexts_to_custom_header_dicts[ network_context ]
                
                if key in custom_header_dict:
                    
                    del custom_header_dict[ key ]
                    
                
            
            self._SetDirty()
            
        
    
    def DeleteGUGs( self, deletee_names ):
        
        with self._lock:
            
            gugs = [ gug for gug in self._gugs if gug.GetName() not in deletee_names ]
            
        
        self.SetGUGs( gugs )
        
    
    def DeleteParsers( self, deletee_names ):
        
        with self._lock:
            
            parsers = [ parser for parser in self._parsers if parser.GetName() not in deletee_names ]
            
        
        self.SetParsers( parsers )
        
    
    def DeleteURLClasses( self, deletee_names ):
        
        with self._lock:
            
            url_classes = [ url_class for url_class in self._url_classes if url_class.GetName() not in deletee_names ]
            
        
        self.SetURLClasses( url_classes )
        
    
    def DissolveParserLink( self, url_class_name, parser_name ):
        
        with self._lock:
            
            the_url_class = None
            
            for url_class in self._url_classes:
                
                if url_class.GetName() == url_class_name:
                    
                    the_url_class = url_class
                    
                    break
                    
                
            
            the_parser = None
            
            for parser in self._parsers:
                
                if parser.GetName() == parser_name:
                    
                    the_parser = parser
                    
                    break
                    
                
            
            if the_url_class is not None and the_parser is not None:
                
                url_class_key = the_url_class.GetClassKey()
                parser_key = the_parser.GetParserKey()
                
                if url_class_key in self._url_class_keys_to_parser_keys and self._url_class_keys_to_parser_keys[ url_class_key ] == parser_key:
                    
                    del self._url_class_keys_to_parser_keys[ url_class_key ]
                    
                
            
        
    
    def DomainOK( self, url ):
        
        with self._lock:
            
            try:
                
                domain = ClientNetworkingFunctions.ConvertURLIntoSecondLevelDomain( url )
                
            except:
                
                return True
                
            
            # this will become flexible and customisable when I have domain profiles/status/ui
            # also should extend it to 'global', so if multiple domains are having trouble, we maybe assume the whole connection is down? it would really be nicer to have a better sockets-level check there
            
            if domain in self._second_level_domains_to_network_infrastructure_errors:
                
                number_of_errors = CG.client_controller.new_options.GetInteger( 'domain_network_infrastructure_error_number' )
                
                if number_of_errors == 0:
                    
                    return True
                    
                
                error_time_delta = CG.client_controller.new_options.GetInteger( 'domain_network_infrastructure_error_time_delta' )
                
                network_infrastructure_errors = self._second_level_domains_to_network_infrastructure_errors[ domain ]
                
                network_infrastructure_errors = [ timestamp for timestamp in network_infrastructure_errors if not HydrusTime.TimeHasPassed( timestamp + error_time_delta ) ]
                
                self._second_level_domains_to_network_infrastructure_errors[ domain ] = network_infrastructure_errors
                
                if len( network_infrastructure_errors ) >= number_of_errors:
                    
                    return False
                    
                elif len( network_infrastructure_errors ) == 0:
                    
                    del self._second_level_domains_to_network_infrastructure_errors[ domain ]
                    
                
            
            return True
            
        
    
    def GenerateValidationPopupProcess( self, network_contexts ):
        
        with self._lock:
            
            header_tuples = []
            
            for network_context in network_contexts:
                
                if network_context in self._network_contexts_to_custom_header_dicts:
                    
                    custom_header_dict = self._network_contexts_to_custom_header_dicts[ network_context ]
                    
                    for ( key, ( value, approved, reason ) ) in list(custom_header_dict.items()):
                        
                        if approved == VALID_UNKNOWN:
                            
                            header_tuples.append( ( network_context, key, value, reason ) )
                            
                        
                    
                
            
            process = DomainValidationPopupProcess( self, header_tuples )
            
            return process
            
        
    
    def GetDefaultGUGKeyAndName( self ):
        
        with self._lock:
            
            gug_key = CG.client_controller.new_options.GetKey( 'default_gug_key' )
            gug_name = CG.client_controller.new_options.GetString( 'default_gug_name' )
            
            return ( gug_key, gug_name )
            
        
    
    def GetDefaultNoteImportOptions( self ):
        
        with self._lock:
            
            return ( self._file_post_default_note_import_options, self._watchable_default_note_import_options, self._url_class_keys_to_default_note_import_options )
            
        
    
    def GetDefaultNoteImportOptionsForURL( self, referral_url, url ):
        
        with self._lock:
            
            return self._GetDefaultNoteImportOptionsForURL( referral_url, url )
            
        
    
    def GetDefaultTagImportOptions( self ):
        
        with self._lock:
            
            return ( self._file_post_default_tag_import_options, self._watchable_default_tag_import_options, self._url_class_keys_to_default_tag_import_options )
            
        
    
    def GetDefaultTagImportOptionsForURL( self, referral_url, url ):
        
        with self._lock:
            
            return self._GetDefaultTagImportOptionsForURL( referral_url, url )
            
        
    
    def GetDownloader( self, url ):
        
        with self._lock:
            
            # this might be better as getdownloaderkey, but we'll see how it shakes out
            # might also be worth being a getifhasdownloader
            
            # match the url to a url_class, then lookup that in a 'this downloader can handle this url_class type' dict that we'll manage
            
            pass
            
        
    
    def GetGUG( self, gug_key_and_name ):
        
        with self._lock:
            
            return self._GetGUG( gug_key_and_name )
            
        
    
    def GetGUGs( self ):
        
        with self._lock:
            
            return list( self._gugs )
            
        
    
    def GetGUGKeysToDisplay( self ):
        
        with self._lock:
            
            return set( self._gug_keys_to_display )
            
        
    
    def GetHeaders( self, network_contexts ):
        
        with self._lock:
            
            headers = {}
            
            for network_context in network_contexts:
                
                if network_context in self._network_contexts_to_custom_header_dicts:
                    
                    custom_header_dict = self._network_contexts_to_custom_header_dicts[ network_context ]
                    
                    for ( key, ( value, approved, reason ) ) in list( custom_header_dict.items() ):
                        
                        if approved == VALID_APPROVED:
                            
                            headers[ key ] = value
                            
                        
                    
                
            
            return headers
            
        
    
    def GetInitialSearchText( self, gug_key_and_name ):
        
        with self._lock:
            
            gug = self._GetGUG( gug_key_and_name )
            
            if gug is None:
                
                return 'unknown downloader'
                
            else:
                
                return gug.GetInitialSearchText()
                
            
        
    
    def GetNetworkContextsToCustomHeaderDicts( self ):
        
        with self._lock:
            
            return dict( self._network_contexts_to_custom_header_dicts )
            
        
    
    def GetParser( self, name ):
        
        with self._lock:
            
            for parser in self._parsers:
                
                if parser.GetName() == name:
                    
                    return parser
                    
                
            
        
        return None
        
    
    def GetParsers( self ):
        
        with self._lock:
            
            return list( self._parsers )
            
        
    
    def GetParserNamespaces( self ):
        
        with self._lock:
            
            return list( self._parser_namespaces )
            
        
    
    def GetReferralURL( self, url, referral_url ):
        
        with self._lock:
            
            url_class = self._GetURLClass( url )
            
            if url_class is None:
                
                return referral_url
                
            else:
                
                return url_class.GetReferralURL( url, referral_url )
                
            
        
    
    def GetShareableCustomHeaders( self, network_context ):
        
        with self._lock:
            
            headers_list = []
            
            if network_context in self._network_contexts_to_custom_header_dicts:
                
                custom_header_dict = self._network_contexts_to_custom_header_dicts[ network_context ]
                
                for ( key, ( value, approved, reason ) ) in list( custom_header_dict.items() ):
                    
                    if approved == VALID_APPROVED:
                        
                        headers_list.append( ( key, value, reason ) )
                        
                    
                
            
            return headers_list
            
        
    
    def GetURLClass( self, url ) -> typing.Optional[ ClientNetworkingURLClass.URLClass ]:
        
        with self._lock:
            
            return self._GetURLClass( url )
            
        
    
    def GetURLClassFromName( self, name: str ):
        
        with self._lock:
            
            name_search = name.casefold()
            
            for url_class in self._url_classes:
                
                if url_class.GetName().casefold() == name_search:
                    
                    return url_class
                    
                
            
        
        raise HydrusExceptions.DataMissing( 'Did not find URL Class called "{}"!'.format( name ) )
        
    
    def GetURLClassHeaders( self, url ):
        
        with self._lock:
            
            url_class = self._GetURLClass( url )
            
            if url_class is not None:
                
                return url_class.GetHeaderOverrides()
                
            else:
                
                return {}
                
            
        
    
    def GetURLClasses( self ):
        
        with self._lock:
            
            return list( self._url_classes )
            
        
    
    def GetURLClassKeysToParserKeys( self ):
        
        with self._lock:
            
            return dict( self._url_class_keys_to_parser_keys )
            
        
    
    def GetURLClassKeysToDisplay( self ):
        
        with self._lock:
            
            return set( self._url_class_keys_to_display )
            
        
    
    def GetURLParseCapability( self, url ):
        
        with self._lock:
            
            url_class = self._GetURLClass( url )
            
            if url_class is None:
                
                return ( HC.URL_TYPE_UNKNOWN, 'unknown url', False, 'unknown url class' )
                
            
            url_type = url_class.GetURLType()
            match_name = url_class.GetName()
            
            try:
                
                ( url_to_fetch, parser ) = self._GetURLToFetchAndParser( url )
                
                can_parse = True
                cannot_parse_reason = ''
                
            except HydrusExceptions.URLClassException as e:
                
                can_parse = False
                cannot_parse_reason = str( e )
                
            
        
        return ( url_type, match_name, can_parse, cannot_parse_reason )
        
    
    def GetURLToFetch( self, url ):
        
        with self._lock:
            
            url_to_fetch = self._GetURLToFetch( url )
            
            if url_to_fetch != url:
                
                message = f'Request for URL to fetch:\n{url}\n->\n{url_to_fetch}'
                
            else:
                
                message = f'Request for URL to fetch:\n{url}\n->\n(no transformation)'
                
            
            ClientNetworkingFunctions.NetworkReportMode( message )
            
            return url_to_fetch
            
        
    
    def GetURLToFetchAndParser( self, url ):
        
        with self._lock:
            
            result = self._GetURLToFetchAndParser( url )
            
            if HG.network_report_mode:
                
                url_class = self._GetURLClass( url )
                
                if url_class is None:
                    
                    url_name = 'unknown url type'
                    
                else:
                    
                    url_name = url_class.GetName()
                    
                
                ( url_to_fetch, parser ) = result
                
                if url_to_fetch != url:
                    
                    url_to_fetch_match = self._GetURLClass( url_to_fetch )
                    
                    if url_to_fetch_match is None:
                        
                        url_to_fetch_name = 'unknown url type'
                        
                    else:
                        
                        url_to_fetch_name = url_to_fetch_match.GetName()
                        
                    
                    message = f'Request for URL to fetch and parser:\n{url} ({url_name})\n->\n{url_to_fetch} ({url_to_fetch_name}): {parser.GetName()}'
                    
                else:
                    
                    message = f'Request for URL to fetch and parser:\n{url} ({url_name})\n->\n(no transformation): {parser.GetName()}'
                    
                
                ClientNetworkingFunctions.NetworkReportMode( message )
                
            
            return result
            
        
    
    def HasCustomHeaders( self, network_context ):
        
        with self._lock:
            
            return network_context in self._network_contexts_to_custom_header_dicts and len( self._network_contexts_to_custom_header_dicts[ network_context ] ) > 0
            
        
    
    def Initialise( self ):
        
        self._RecalcCache()
        
    
    def IsDirty( self ):
        
        with self._lock:
            
            return self._dirty
            
        
    
    def IsValid( self, network_contexts ):
        
        # denied headers are simply not added--they don't invalidate a query
        
        for network_context in network_contexts:
            
            if network_context in self._network_contexts_to_custom_header_dicts:
                
                custom_header_dict = self._network_contexts_to_custom_header_dicts[ network_context ]
                
                for ( value, approved, reason ) in list(custom_header_dict.values()):
                    
                    if approved == VALID_UNKNOWN:
                        
                        return False
                        
                    
                
            
        
        return True
        
    
    def NormaliseURL( self, url, for_server = False ):
        
        with self._lock:
            
            try:
                
                ClientNetworkingFunctions.CheckLooksLikeAFullURL( url )
                
            except HydrusExceptions.URLClassException:
                
                return url
                
            
            url_class = self._GetURLClass( url )
            
            if url_class is None:
                
                # this is less about washing as it is about stripping the fragment
                normalised_url = ClientNetworkingFunctions.EnsureURLIsEncoded( url, keep_fragment = False )
                
            else:
                
                normalised_url = url_class.Normalise( url, for_server = for_server )
                
            
            return normalised_url
            
        
    
    def NormaliseURLs( self, urls: collections.abc.Collection[ str ], for_server = False ) -> list[ str ]:
        
        normalised_urls = []
        
        for url in urls:
            
            try:
                
                normalised_url = self.NormaliseURL( url, for_server = for_server )
                
            except HydrusExceptions.URLClassException:
                
                continue
                
            
            normalised_urls.append( normalised_url )
            
        
        normalised_urls = HydrusLists.DedupeList( normalised_urls )
        
        return normalised_urls
        
    
    def OverwriteDefaultGUGs( self, gug_names ):
        
        with self._lock:
            
            from hydrus.client import ClientDefaults
            
            default_gugs = ClientDefaults.GetDefaultGUGs()
            
            existing_gug_names_to_keys = { gug.GetName() : gug.GetGUGKey() for gug in self._gugs }
            
            for gug in default_gugs:
                
                gug_name = gug.GetName()
                
                if gug_name in existing_gug_names_to_keys:
                    
                    gug.SetGUGKey( existing_gug_names_to_keys[ gug_name ] )
                    
                else:
                    
                    gug.RegenerateGUGKey()
                    
                
            
            existing_gugs = list( self._gugs )
            
            new_gugs = [ gug for gug in existing_gugs if gug.GetName() not in gug_names ]
            new_gugs.extend( [ gug for gug in default_gugs if gug.GetName() in gug_names ] )
            
        
        self.SetGUGs( new_gugs )
        
    
    def OverwriteDefaultParsers( self, parser_names ):
        
        with self._lock:
            
            from hydrus.client import ClientDefaults
            
            default_parsers = ClientDefaults.GetDefaultParsers()
            
            existing_parser_names_to_keys = { parser.GetName() : parser.GetParserKey() for parser in self._parsers }
            
            for parser in default_parsers:
                
                name = parser.GetName()
                
                if name in existing_parser_names_to_keys:
                    
                    parser.SetParserKey( existing_parser_names_to_keys[ name ] )
                    
                else:
                    
                    parser.RegenerateParserKey()
                    
                
            
            existing_parsers = list( self._parsers )
            
            new_parsers = [ parser for parser in existing_parsers if parser.GetName() not in parser_names ]
            new_parsers.extend( [ parser for parser in default_parsers if parser.GetName() in parser_names ] )
            
        
        self.SetParsers( new_parsers )
        
    
    def OverwriteDefaultURLClasses( self, url_class_names ):
        
        with self._lock:
            
            from hydrus.client import ClientDefaults
            
            default_url_classes = ClientDefaults.GetDefaultURLClasses()
            
            existing_class_names_to_keys = { url_class.GetName() : url_class.GetClassKey() for url_class in self._url_classes }
            
            for url_class in default_url_classes:
                
                name = url_class.GetName()
                
                if name in existing_class_names_to_keys:
                    
                    url_class.SetClassKey( existing_class_names_to_keys[ name ] )
                    
                else:
                    
                    url_class.RegenerateClassKey()
                    
                
            
            for url_class in default_url_classes:
                
                url_class.RegenerateClassKey()
                
            
            existing_url_classes = list( self._url_classes )
            
            new_url_classes = [ url_class for url_class in existing_url_classes if url_class.GetName() not in url_class_names ]
            new_url_classes.extend( [ url_class for url_class in default_url_classes if url_class.GetName() in url_class_names ] )
            
        
        self.SetURLClasses( new_url_classes )
        
    
    def OverwriteParserLink( self, url_class_name, parser_name ):
        
        with self._lock:
            
            url_class_to_link = None
            
            for url_class in self._url_classes:
                
                if url_class.GetName() == url_class_name:
                    
                    url_class_to_link = url_class
                    
                    break
                    
                
            
            if url_class_to_link is None:
                
                return False
                
            
            parser_to_link = None
            
            for parser in self._parsers:
                
                if parser.GetName() == parser_name:
                    
                    parser_to_link = parser
                    
                    break
                    
                
            
            if parser_to_link is None:
                
                return False
                
            
            url_class_key = url_class_to_link.GetClassKey()
            parser_key = parser_to_link.GetParserKey()
            
            self._url_class_keys_to_parser_keys[ url_class_key ] = parser_key
            
            return True
            
        
    
    def RenameGUG( self, original_name, new_name ):
        
        with self._lock:
            
            existing_gug_names_to_gugs = { gug.GetName() : gug for gug in self._gugs }
            
        
        if original_name in existing_gug_names_to_gugs:
            
            gug = existing_gug_names_to_gugs[ original_name ]
            
            del existing_gug_names_to_gugs[ original_name ]
            
            gug.SetName( new_name )
            
            gug.SetNonDupeName( set( existing_gug_names_to_gugs.keys() ) )
            
            existing_gug_names_to_gugs[ gug.GetName() ] = gug
            
            new_gugs = list( existing_gug_names_to_gugs.values() )
            
            self.SetGUGs( new_gugs )
            
        
    
    def ReportNetworkInfrastructureError( self, url ):
        
        with self._lock:
            
            try:
                
                domain = ClientNetworkingFunctions.ConvertURLIntoDomain( url )
                
            except:
                
                return
                
            
            self._second_level_domains_to_network_infrastructure_errors[ domain ].append( HydrusTime.GetNow() )
            
        
    
    def ScrubDomainErrors( self, url ):
        
        with self._lock:
            
            try:
                
                domain = ClientNetworkingFunctions.ConvertURLIntoSecondLevelDomain( url )
                
            except:
                
                return
                
            
            if domain in self._second_level_domains_to_network_infrastructure_errors:
                
                del self._second_level_domains_to_network_infrastructure_errors[ domain ]
                
            
        
    
    def SetClean( self ):
        
        with self._lock:
            
            self._dirty = False
            
        
    
    def SetCustomHeader( self, network_context: ClientNetworkingContexts.NetworkContext, key, value = None, approved = None, reason = None ):
        
        with self._lock:
            
            fallback_value = None
            fallback_approved = VALID_APPROVED
            fallback_reason = 'Set by Client API'
            
            if network_context not in self._network_contexts_to_custom_header_dicts:
                
                self._network_contexts_to_custom_header_dicts[ network_context ] = {}
                
            
            custom_header_dict = self._network_contexts_to_custom_header_dicts[ network_context ]
            
            if key in custom_header_dict:
                
                ( fallback_value, fallback_approved, fallback_reason ) = custom_header_dict[ key ]
                
            
            if value is None:
                
                if fallback_value is None:
                    
                    raise Exception( 'Sorry, was called to set HTTP Header information for key "{}" on "{}", but there was no attached value and it did not already exist!'.format( key, network_context ) )
                    
                else:
                    
                    value = fallback_value
                    
                
            
            if approved is None:
                
                approved = fallback_approved
                
            
            if reason is None:
                
                reason = fallback_reason
                
            
            custom_header_dict[ key ] = ( value, approved, reason )
            
            self._SetDirty()
            
        
    
    def SetDefaultFilePostNoteImportOptions( self, note_import_options ):
        
        with self._lock:
            
            self._file_post_default_note_import_options = note_import_options
            
            self._SetDirty()
            
        
    
    def SetDefaultFilePostTagImportOptions( self, tag_import_options ):
        
        with self._lock:
            
            self._file_post_default_tag_import_options = tag_import_options
            
            self._SetDirty()
            
        
    
    def SetDefaultGUGKeyAndName( self, gug_key_and_name ):
        
        with self._lock:
            
            ( gug_key, gug_name ) = gug_key_and_name
            
            CG.client_controller.new_options.SetKey( 'default_gug_key', gug_key )
            CG.client_controller.new_options.SetString( 'default_gug_name', gug_name )
            
        
    
    def SetDefaultNoteImportOptions( self, file_post_default_note_import_options, watchable_default_note_import_options, url_class_keys_to_note_import_options ):
        
        with self._lock:
            
            self._file_post_default_note_import_options = file_post_default_note_import_options
            self._watchable_default_note_import_options = watchable_default_note_import_options
            
            self._url_class_keys_to_default_note_import_options = url_class_keys_to_note_import_options
            
            self._SetDirty()
            
        
    
    def SetDefaultTagImportOptions( self, file_post_default_tag_import_options, watchable_default_tag_import_options, url_class_keys_to_tag_import_options ):
        
        with self._lock:
            
            self._file_post_default_tag_import_options = file_post_default_tag_import_options
            self._watchable_default_tag_import_options = watchable_default_tag_import_options
            
            self._url_class_keys_to_default_tag_import_options = url_class_keys_to_tag_import_options
            
            self._SetDirty()
            
        
    
    def SetGUGs( self, gugs ):
        
        with self._lock:
            
            # by default, we will show new gugs
            
            old_gug_keys = { gug.GetGUGKey() for gug in self._gugs }
            gug_keys = { gug.GetGUGKey() for gug in gugs }
            
            added_gug_keys = gug_keys.difference( old_gug_keys )
            
            self._gug_keys_to_display.update( added_gug_keys )
            
            #
            
            self._gugs = HydrusSerialisable.SerialisableList( gugs )
            
            self._RecalcCache()
            
            self._SetDirty()
            
        
    
    def SetGUGKeysToDisplay( self, gug_keys_to_display ):
        
        with self._lock:
            
            self._gug_keys_to_display = set()
            
            self._gug_keys_to_display.update( gug_keys_to_display )
            
            self._SetDirty()
            
        
    
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
            
            self._parsers.sort( key = lambda p: p.GetName() )
            
            # delete orphans
            
            parser_keys = { parser.GetParserKey() for parser in parsers }
            
            deletee_url_class_keys = set()
            
            for ( url_class_key, parser_key ) in self._url_class_keys_to_parser_keys.items():
                
                if parser_key not in parser_keys:
                    
                    deletee_url_class_keys.add( url_class_key )
                    
                
            
            for deletee_url_class_key in deletee_url_class_keys:
                
                del self._url_class_keys_to_parser_keys[ deletee_url_class_key ]
                
            
            #
            
            self._RecalcCache()
            
            self._SetDirty()
            
        
    
    def SetURLClasses( self, url_classes ):
        
        with self._lock:
            
            # by default, we will show post urls
            
            old_post_url_class_keys = { url_class.GetClassKey() for url_class in self._url_classes if url_class.IsPostURL() }
            post_url_class_keys = { url_class.GetClassKey() for url_class in url_classes if url_class.IsPostURL() }
            
            added_post_url_class_keys = post_url_class_keys.difference( old_post_url_class_keys )
            
            self._url_class_keys_to_display.update( added_post_url_class_keys )
            
            #
            
            self._url_classes = HydrusSerialisable.SerialisableList()
            
            self._url_classes.extend( url_classes )
            
            self._url_classes.sort( key = lambda u: u.GetName() )
            
            #
            
            # delete orphans
            
            url_class_keys = { url_class.GetClassKey() for url_class in url_classes }
            
            self._url_class_keys_to_display.intersection_update( url_class_keys )
            
            for deletee_key in set( self._url_class_keys_to_parser_keys.keys() ).difference( url_class_keys ):
                
                del self._url_class_keys_to_parser_keys[ deletee_key ]
                
            
            # any url matches that link to another via the API conversion will not be using parsers
            
            url_class_api_pairs = ClientNetworkingURLClass.ConvertURLClassesIntoAPIPairs( self._url_classes )
            
            for ( url_class_original, url_class_api ) in url_class_api_pairs:
                
                url_class_key = url_class_original.GetClassKey()
                
                if url_class_key in self._url_class_keys_to_parser_keys:
                    
                    del self._url_class_keys_to_parser_keys[ url_class_key ]
                    
                
            
            self._RecalcCache()
            
            self._SetDirty()
            
        
    
    def SetURLClassKeysToParserKeys( self, url_class_keys_to_parser_keys ):
        
        with self._lock:
            
            self._url_class_keys_to_parser_keys = HydrusSerialisable.SerialisableBytesDictionary()
            
            self._url_class_keys_to_parser_keys.update( url_class_keys_to_parser_keys )
            
            self._CleanURLClassKeysToParserKeys()
            
            self._SetDirty()
            
        
    
    def SetURLClassKeysToDisplay( self, url_class_keys_to_display ):
        
        with self._lock:
            
            self._url_class_keys_to_display = set()
            
            self._url_class_keys_to_display.update( url_class_keys_to_display )
            
            self._SetDirty()
            
        
    
    def ShouldAssociateURLWithFiles( self, url ):
        
        with self._lock:
            
            url_class = self._GetURLClass( url )
            
            if url_class is None:
                
                return True
                
            
            return url_class.ShouldAssociateWithFiles()
            
        
    
    def TryToLinkURLClassesAndParsers( self ):
        
        with self._lock:
            
            new_url_class_keys_to_parser_keys = NetworkDomainManager.STATICLinkURLClassesAndParsers( self._url_classes, self._parsers, self._url_class_keys_to_parser_keys )
            
            self._url_class_keys_to_parser_keys.update( new_url_class_keys_to_parser_keys )
            
            self._CleanURLClassKeysToParserKeys()
            
            self._SetDirty()
            
        
    
    def URLCanReferToMultipleFiles( self, url ):
        
        with self._lock:
            
            url_class = self._GetURLClass( url )
            
            if url_class is None:
                
                return False
                
            
            return url_class.CanReferToMultipleFiles()
            
        
    
    def URLDefinitelyRefersToOneFile( self, url ):
        
        with self._lock:
            
            url_class = self._GetURLClass( url )
            
            if url_class is None:
                
                return False
                
            
            return url_class.RefersToOneFile()
            
        
    
    @staticmethod
    def STATICLinkURLClassesAndParsers( url_classes, parsers, existing_url_class_keys_to_parser_keys ):
        
        url_classes = list( url_classes )
        
        ClientNetworkingURLClass.SortURLClassesListDescendingComplexity( url_classes )
        
        parsers = list( parsers )
        
        parsers.sort( key = lambda p: p.GetName() )
        
        new_url_class_keys_to_parser_keys = {}
        
        api_pairs = ClientNetworkingURLClass.ConvertURLClassesIntoAPIPairs( url_classes )
        
        # anything that goes to an api url will be parsed by that api's parser--it can't have its own
        api_pair_unparsable_url_classes = set()
        
        for ( a, b ) in api_pairs:
            
            api_pair_unparsable_url_classes.add( a )
            
        
        #
        
        # I have to do this backwards, going through parsers and then url_classes, so I can do a proper url match lookup like the real domain manager does it
        # otherwise, if we iterate through url matches looking for parsers to match them, we have gallery url matches thinking they match parser post urls
        # e.g.
        # The page parser might say it supports https://danbooru.donmai.us/posts/3198277
        # But the gallery url class might think it recognises that as https://danbooru.donmai.us/posts
        # 
        # So we have to do the normal lookup in the proper descending complexity order, not searching any further than the first, correct match
        
        for parser in parsers:
            
            example_urls = parser.GetExampleURLs()
            
            for example_url in example_urls:
                
                for url_class in url_classes:
                    
                    if url_class in api_pair_unparsable_url_classes:
                        
                        continue
                        
                    
                    if url_class.Matches( example_url ):
                        
                        # we have a match. this is the 'correct' match for this example url, and we should not search any more, so we break below
                        
                        url_class_key = url_class.GetClassKey()
                        
                        parsable = url_class.IsParsable()
                        linkable = url_class_key not in existing_url_class_keys_to_parser_keys and url_class_key not in new_url_class_keys_to_parser_keys
                        
                        if parsable and linkable:
                            
                            new_url_class_keys_to_parser_keys[ url_class_key ] = parser.GetParserKey()
                            
                        
                        break
                        
                    
                
            
        '''
        #
        
        for url_class in url_classes:
            
            if not url_class.IsParsable() or url_class in api_pair_unparsable_url_classes:
                
                continue
                
            
            url_class_key = url_class.GetClassKey()
            
            if url_class_key in existing_url_class_keys_to_parser_keys:
                
                continue
                
            
            for parser in parsers:
                
                example_urls = parser.GetExampleURLs()
                
                if True in ( url_class.Matches( example_url ) for example_url in example_urls ):
                    
                    new_url_class_keys_to_parser_keys[ url_class_key ] = parser.GetParserKey()
                    
                    break
                    
                
            
        '''
        return new_url_class_keys_to_parser_keys
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_DOMAIN_MANAGER ] = NetworkDomainManager

class DomainMetadataPackage( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_DOMAIN_METADATA_PACKAGE
    SERIALISABLE_NAME = 'Domain Metadata'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, domain = None, headers_list = None, bandwidth_rules = None ):
        
        super().__init__()
        
        if domain is None:
            
            domain = 'example.com'
            
        
        self._domain = domain
        self._headers_list = headers_list
        self._bandwidth_rules = bandwidth_rules
        
    
    def _GetSerialisableInfo( self ):
        
        if self._bandwidth_rules is None:
            
            serialisable_bandwidth_rules = self._bandwidth_rules
            
        else:
            
            serialisable_bandwidth_rules = self._bandwidth_rules.GetSerialisableTuple()
            
        
        return ( self._domain, self._headers_list, serialisable_bandwidth_rules )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._domain, self._headers_list, serialisable_bandwidth_rules ) = serialisable_info
        
        if serialisable_bandwidth_rules is None:
            
            self._bandwidth_rules = serialisable_bandwidth_rules
            
        else:
            
            self._bandwidth_rules = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_bandwidth_rules )
            
        
    
    def GetBandwidthRules( self ):
        
        return self._bandwidth_rules
        
    
    def GetDetailedSafeSummary( self ):
        
        components = [ 'For domain "' + self._domain + '":' ]
        
        if self.HasBandwidthRules():
            
            m = 'Bandwidth rules: '
            m += '\n'
            m += '\n'.join( [ HydrusNetworking.ConvertBandwidthRuleToString( rule ) for rule in self._bandwidth_rules.GetRules() ] )
            
            components.append( m )
            
        
        if self.HasHeaders():
            
            m = 'Headers: '
            m += '\n'
            m += '\n'.join( [ key + ' : ' + value + ' - ' + reason for ( key, value, reason ) in self._headers_list ] )
            
            components.append( m )
            
        
        joiner = '\n' * 2
        
        s = joiner.join( components )
        
        return s
        
    
    def GetDomain( self ):
        
        return self._domain
        
    
    def GetHeaders( self ):
        
        return self._headers_list
        
    
    def GetSafeSummary( self ):
        
        components = []
        
        if self.HasBandwidthRules():
            
            components.append( 'bandwidth rules' )
            
        
        if self.HasHeaders():
            
            components.append( 'headers' )
            
        
        return ' and '.join( components ) + ' - ' + self._domain
        
    
    def HasBandwidthRules( self ):
        
        return self._bandwidth_rules is not None
        
    
    def HasHeaders( self ):
        
        return self._headers_list is not None
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_DOMAIN_METADATA_PACKAGE ] = DomainMetadataPackage

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
                
                job_status = ClientThreading.JobStatus()
                
                # generate question
                
                question = 'For the network context ' + network_context.ToString() + ', can the client set this header?'
                question += '\n' * 2
                question += key + ': ' + value
                question += '\n' * 2
                question += reason
                
                job_status.SetVariable( 'popup_yes_no_question', question )
                
                CG.client_controller.pub( 'message', job_status )
                
                result = job_status.GetIfHasVariable( 'popup_yes_no_answer' )
                
                while result is None:
                    
                    if HG.started_shutdown:
                        
                        return
                        
                    
                    time.sleep( 0.25 )
                    
                    result = job_status.GetIfHasVariable( 'popup_yes_no_answer' )
                    
                
                if result:
                    
                    approved = VALID_APPROVED
                    
                else:
                    
                    approved = VALID_DENIED
                    
                
                self._domain_manager.SetHeaderValidation( network_context, key, approved )
                
            
        finally:
            
            self._is_done = True
            
        
