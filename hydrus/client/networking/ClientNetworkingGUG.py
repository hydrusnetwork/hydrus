from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusSerialisable

from hydrus.client import ClientGlobals as CG
from hydrus.client.networking import ClientNetworkingFunctions

class GalleryURLGenerator( HydrusSerialisable.SerialisableBaseNamed ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_GALLERY_URL_GENERATOR
    SERIALISABLE_NAME = 'Gallery URL Generator'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, name, gug_key = None, url_template = None, replacement_phrase = None, search_terms_separator = None, initial_search_text = None, example_search_text = None ):
        
        if gug_key is None:
            
            gug_key = HydrusData.GenerateKey()
            
        
        if url_template is None:
            
            url_template = 'https://example.com/search?q=%tags%&index=0'
            
        
        if replacement_phrase is None:
            
            replacement_phrase = '%tags%'
            
        
        if search_terms_separator is None:
            
            search_terms_separator = '+'
            
        
        if initial_search_text is None:
            
            initial_search_text = 'search tags'
            
        
        if example_search_text is None:
            
            example_search_text = 'blue_eyes blonde_hair'
            
        
        super().__init__( name )
        
        self._gallery_url_generator_key = gug_key
        self._url_template = url_template
        self._replacement_phrase = replacement_phrase
        self._search_terms_separator = search_terms_separator
        self._initial_search_text = initial_search_text
        self._example_search_text = example_search_text
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_gallery_url_generator_key = self._gallery_url_generator_key.hex()
        
        return ( serialisable_gallery_url_generator_key, self._url_template, self._replacement_phrase, self._search_terms_separator, self._initial_search_text, self._example_search_text )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_gallery_url_generator_key, self._url_template, self._replacement_phrase, self._search_terms_separator, self._initial_search_text, self._example_search_text ) = serialisable_info
        
        self._gallery_url_generator_key = bytes.fromhex( serialisable_gallery_url_generator_key )
        
    
    def CheckFunctional( self ):
        
        try:
            
            example_url = self.GetExampleURL()
            
            ( url_type, match_name, can_parse, cannot_parse_reason ) = CG.client_controller.network_engine.domain_manager.GetURLParseCapability( example_url )
            
        except Exception as e:
            
            raise HydrusExceptions.ParseException( 'Unusual error: {}'.format( e ) )
            
        
        if url_type == HC.URL_TYPE_UNKNOWN:
            
            raise HydrusExceptions.ParseException( 'No URL Class for example URL!' )
            
        
        if not can_parse:
            
            raise HydrusExceptions.ParseException( 'Cannot parse {}: {}'.format( match_name, cannot_parse_reason ) )
            
        
    
    def GenerateGalleryURL( self, query_text ):
        
        if self._replacement_phrase == '':
            
            raise HydrusExceptions.GUGException( 'No replacement phrase!' )
            
        
        if self._replacement_phrase not in self._url_template:
            
            raise HydrusExceptions.GUGException( 'Replacement phrase not in URL template!' )
            
        
        if CG.client_controller.new_options.GetBoolean( 'replace_percent_twenty_with_space_in_gug_input' ):
            
            query_text = query_text.replace( '%20', ' ' )
            
        
        search_terms = query_text.split( ' ' )
        
        looks_like_tags_are_going_into_params = False
        
        if '?' in self._url_template:
            
            ( first_half, second_half ) = self._url_template.split( '?', 1 )
            
            if self._replacement_phrase in second_half:
                
                looks_like_tags_are_going_into_params = True
                
            
        
        if looks_like_tags_are_going_into_params:
            
            # we pre-encode each term here because we are not talking about URL with RFC 3986 rules, but the taglist, which is 'encode each tag to %-encoding thanks'
            # we need to handle the '6+girls+skirt' = '6%2Bgirls+skirt' scenario
            
            encoded_search_terms = [ ClientNetworkingFunctions.ensure_component_is_encoded( search_term, '' ) for search_term in search_terms ]
            
        else:
            
            # in this case, we are just plonking an artist name in a path component, so we want normal path encoding rules, not 'encode everything mate'
            encoded_search_terms = [ ClientNetworkingFunctions.ensure_path_component_is_encoded( search_term ) for search_term in search_terms ]
            
        
        try:
            
            search_phrase = self._search_terms_separator.join( encoded_search_terms )
            
            gallery_url = self._url_template.replace( self._replacement_phrase, search_phrase )
            
        except Exception as e:
            
            raise HydrusExceptions.GUGException( str( e ) )
            
        
        return ClientNetworkingFunctions.EnsureURLIsEncoded( gallery_url )
        
    
    def GenerateGalleryURLs( self, query_text ):
        
        return ( self.GenerateGalleryURL( query_text ), )
        
    
    def GetExampleURL( self ):
        
        return self.GenerateGalleryURL( self._example_search_text )
        
    
    def GetExampleURLs( self ):
        
        return ( self.GetExampleURL(), )
        
    
    def GetGUGKey( self ):
        
        return self._gallery_url_generator_key
        
    
    def GetGUGKeyAndName( self ):
        
        return ( self._gallery_url_generator_key, self._name )
        
    
    def GetInitialSearchText( self ):
        
        return self._initial_search_text
        
    
    def GetSafeSummary( self ):
        
        return 'Downloader "' + self._name + '" - ' + ClientNetworkingFunctions.ConvertURLIntoDomain( self.GetExampleURL() )
        
    
    def GetURLTemplateVariables( self ):
        
        return ( self._url_template, self._replacement_phrase, self._search_terms_separator, self._example_search_text )
        
    
    def IsFunctional( self ):
        
        try:
            
            self.CheckFunctional()
            
            return True
            
        except HydrusExceptions.ParseException:
            
            return False
            
        
    
    def IsMultiDomainNGUG( self ):
        
        return False
        
    
    def SetGUGKey( self, gug_key: bytes ):
        
        self._gallery_url_generator_key = gug_key
        
    
    def SetGUGKeyAndName( self, gug_key_and_name ):
        
        ( gug_key, name ) = gug_key_and_name
        
        self._gallery_url_generator_key = gug_key
        self._name = name
        
    
    def RegenerateGUGKey( self ):
        
        self._gallery_url_generator_key = HydrusData.GenerateKey()
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_GALLERY_URL_GENERATOR ] = GalleryURLGenerator

class NestedGalleryURLGenerator( HydrusSerialisable.SerialisableBaseNamed ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_NESTED_GALLERY_URL_GENERATOR
    SERIALISABLE_NAME = 'Nested Gallery URL Generator'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, name, gug_key = None, initial_search_text = None, gug_keys_and_names = None ):
        
        if gug_key is None:
            
            gug_key = HydrusData.GenerateKey()
            
        
        if initial_search_text is None:
            
            initial_search_text = 'search tags'
            
        
        if gug_keys_and_names is None:
            
            gug_keys_and_names = []
            
        
        super().__init__( name )
        
        self._gallery_url_generator_key = gug_key
        self._initial_search_text = initial_search_text
        self._gug_keys_and_names = gug_keys_and_names
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_gug_key = self._gallery_url_generator_key.hex()
        serialisable_gug_keys_and_names = [ ( gug_key.hex(), gug_name ) for ( gug_key, gug_name ) in self._gug_keys_and_names ]
        
        return ( serialisable_gug_key, self._initial_search_text, serialisable_gug_keys_and_names )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_gug_key, self._initial_search_text, serialisable_gug_keys_and_names ) = serialisable_info
        
        self._gallery_url_generator_key = bytes.fromhex( serialisable_gug_key )
        self._gug_keys_and_names = [ ( bytes.fromhex( gug_key ), gug_name ) for ( gug_key, gug_name ) in serialisable_gug_keys_and_names ]
        
    
    def CheckFunctional( self ):
        
        for gug_key_and_name in self._gug_keys_and_names:
            
            gug = CG.client_controller.network_engine.domain_manager.GetGUG( gug_key_and_name )
            
            if gug is not None:
                
                gug.CheckFunctional()
                
            
        
    
    def GenerateGalleryURLs( self, query_text ):
        
        gallery_urls = []
        
        for gug_key_and_name in self._gug_keys_and_names:
            
            gug = CG.client_controller.network_engine.domain_manager.GetGUG( gug_key_and_name )
            
            if gug is not None:
                
                gallery_urls.append( gug.GenerateGalleryURL( query_text ) )
                
            
        
        return gallery_urls
        
    
    def GetExampleURLs( self ):
        
        example_urls = []
        
        for gug_key_and_name in self._gug_keys_and_names:
            
            gug = CG.client_controller.network_engine.domain_manager.GetGUG( gug_key_and_name )
            
            if gug is not None:
                
                example_urls.append( gug.GetExampleURL() )
                
            
        
        return example_urls
        
    
    def GetGUGKey( self ):
        
        return self._gallery_url_generator_key
        
    
    def GetGUGKeys( self ):
        
        return [ gug_key for ( gug_key, gug_name ) in self._gug_keys_and_names ]
        
    
    def GetGUGKeysAndNames( self ):
        
        return list( self._gug_keys_and_names )
        
    
    def GetGUGKeyAndName( self ):
        
        return ( self._gallery_url_generator_key, self._name )
        
    
    def GetGUGNames( self ):
        
        return [ gug_name for ( gug_key, gug_name ) in self._gug_keys_and_names ]
        
    
    def GetInitialSearchText( self ):
        
        return self._initial_search_text
        
    
    def GetSafeSummary( self ):
        
        return 'Nested downloader "' + self._name + '" - ' + ', '.join( ( name for ( gug_key, name ) in self._gug_keys_and_names ) )
        
    
    def IsFunctional( self ):
        
        try:
            
            self.CheckFunctional()
            
            return True
            
        except HydrusExceptions.ParseException:
            
            return False
            
        
    
    def IsMultiDomainNGUG( self ):
        
        try:
            
            example_urls = self.GetExampleURLs()
            
        except Exception as e:
            
            return False
            
        
        example_url_domains = { ClientNetworkingFunctions.ConvertURLIntoDomain( url ) for url in example_urls }
        
        # not perfect, but it'll do for most cases for now
        example_url_second_level_domains = { ClientNetworkingFunctions.ConvertDomainIntoSecondLevelDomain( domain ) for domain in example_url_domains }
        
        return len( example_url_second_level_domains ) > 1
        
    
    def RegenerateGUGKey( self ):
        
        self._gallery_url_generator_key = HydrusData.GenerateKey()
        
        self._gug_keys_and_names = [ ( HydrusData.GenerateKey(), name ) for ( gug_key, name ) in self._gug_keys_and_names ]
        
    
    def RepairGUGs( self, available_gugs ):
        
        available_keys_to_gugs = { gug.GetGUGKey() : gug for gug in available_gugs }
        available_names_to_gugs = { gug.GetName() : gug for gug in available_gugs }
        
        good_gug_keys_and_names = []
        
        for ( gug_key, gug_name ) in self._gug_keys_and_names:
            
            if gug_key in available_keys_to_gugs:
                
                gug = available_keys_to_gugs[ gug_key ]
                
            elif gug_name in available_names_to_gugs:
                
                gug = available_names_to_gugs[ gug_name ]
                
            else:
                
                continue
                
            
            good_gug_keys_and_names.append( ( gug.GetGUGKey(), gug.GetName() ) )
            
        
        self._gug_keys_and_names = good_gug_keys_and_names
        
    
    def SetGUGKey( self, gug_key: bytes ):
        
        self._gallery_url_generator_key = gug_key
        
    
    def SetGUGKeyAndName( self, gug_key_and_name ):
        
        ( gug_key, name ) = gug_key_and_name
        
        self._gallery_url_generator_key = gug_key
        self._name = name
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_NESTED_GALLERY_URL_GENERATOR ] = NestedGalleryURLGenerator
