from . import ClientImportFileSeeds
from . import ClientImportOptions
from . import ClientNetworkingDomain
from . import ClientParsing
from . import ClientThreading
from . import HydrusConstants as HC
from . import HydrusExceptions
from . import HydrusPaths
from . import HydrusSerialisable
from . import HydrusThreading
import random
import threading
from . import HydrusData
from . import ClientConstants as CC
from . import HydrusGlobals as HG

def ConvertBooruToNewObjects( booru ):
    
    name = booru.GetName()
    
    name = 'zzz - auto-generated from legacy booru system - ' + name
    
    ( search_url, search_separator, advance_by_page_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces ) = booru.GetData()
    
    if advance_by_page_num:
        
        search_url = search_url.replace( '%index%', '1' )
        
    else:
        
        search_url = search_url.replace( '%index%', '0' )
        
    
    gug = ClientNetworkingDomain.GalleryURLGenerator( name + ' search', url_template = search_url, replacement_phrase = '%tags%', search_terms_separator = search_separator, initial_search_text = 'tag search', example_search_text = 'blonde_hair blue_eyes' )
    
    #
    
    tag_rules = []
    
    rule_type = ClientParsing.HTML_RULE_TYPE_DESCENDING
    tag_name = None
    tag_attributes = { 'class' : thumb_classname }
    tag_index = None
    
    tag_rules.append( ClientParsing.ParseRuleHTML( rule_type = rule_type, tag_name = tag_name, tag_attributes = tag_attributes, tag_index = tag_index ) )
    
    rule_type = ClientParsing.HTML_RULE_TYPE_DESCENDING
    tag_name = 'a'
    tag_attributes = None
    tag_index = None
    
    tag_rules.append( ClientParsing.ParseRuleHTML( rule_type = rule_type, tag_name = tag_name, tag_attributes = tag_attributes, tag_index = tag_index ) )
    
    formula = ClientParsing.ParseFormulaHTML( tag_rules = tag_rules, content_to_fetch = ClientParsing.HTML_CONTENT_ATTRIBUTE, attribute_to_fetch = 'href' )
    
    url_type = HC.URL_TYPE_DESIRED
    priority = 50
    
    additional_info = ( url_type, priority )
    
    thumb_content_parser = ClientParsing.ContentParser( name = 'get post urls (based on old booru thumb search)', content_type = HC.CONTENT_TYPE_URLS, formula = formula, additional_info = additional_info )
    
    gallery_parser = ClientParsing.PageParser( name + ' gallery page parser', content_parsers = [ thumb_content_parser ], example_urls = [ gug.GetExampleURL() ] )
    
    #
    
    content_parsers = []
    
    if image_id is not None:
        
        tag_rules = []
        
        rule_type = ClientParsing.HTML_RULE_TYPE_DESCENDING
        tag_name = 'a'
        tag_attributes = { 'id' : image_id }
        tag_index = None
        
        tag_rules.append( ClientParsing.ParseRuleHTML( rule_type = rule_type, tag_name = tag_name, tag_attributes = tag_attributes, tag_index = tag_index ) )
        
        formula = ClientParsing.ParseFormulaHTML( tag_rules = tag_rules, content_to_fetch = ClientParsing.HTML_CONTENT_ATTRIBUTE, attribute_to_fetch = 'href' )
        
        url_type = HC.URL_TYPE_DESIRED
        priority = 75
        
        additional_info = ( url_type, priority )
        
        image_link_content_parser = ClientParsing.ContentParser( name = 'get image file link url (based on old booru parser)', content_type = HC.CONTENT_TYPE_URLS, formula = formula, additional_info = additional_info )
        
        content_parsers.append( image_link_content_parser )
        
        #
        
        tag_rules = []
        
        rule_type = ClientParsing.HTML_RULE_TYPE_DESCENDING
        tag_name = 'img'
        tag_attributes = { 'id' : image_id }
        tag_index = None
        
        tag_rules.append( ClientParsing.ParseRuleHTML( rule_type = rule_type, tag_name = tag_name, tag_attributes = tag_attributes, tag_index = tag_index ) )
        
        formula = ClientParsing.ParseFormulaHTML( tag_rules = tag_rules, content_to_fetch = ClientParsing.HTML_CONTENT_ATTRIBUTE, attribute_to_fetch = 'src' )
        
        url_type = HC.URL_TYPE_DESIRED
        priority = 50
        
        additional_info = ( url_type, priority )
        
        image_src_content_parser = ClientParsing.ContentParser( name = 'get image file src url (based on old booru parser)', content_type = HC.CONTENT_TYPE_URLS, formula = formula, additional_info = additional_info )
        
        content_parsers.append( image_src_content_parser )
        
    elif image_data is not None:
        
        tag_rules = []
        
        rule_type = ClientParsing.HTML_RULE_TYPE_DESCENDING
        tag_name = 'a'
        tag_attributes = None
        tag_index = None
        
        string_match = ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = image_data, example_string = image_data )
        
        tag_rules.append( ClientParsing.ParseRuleHTML( rule_type = rule_type, tag_name = tag_name, tag_attributes = tag_attributes, tag_index = tag_index, should_test_tag_string = True, tag_string_string_match = string_match ) )
        
        formula = ClientParsing.ParseFormulaHTML( tag_rules = tag_rules, content_to_fetch = ClientParsing.HTML_CONTENT_ATTRIBUTE, attribute_to_fetch = 'href' )
        
        url_type = HC.URL_TYPE_DESIRED
        priority = 50
        
        additional_info = ( url_type, priority )
        
        image_link_content_parser = ClientParsing.ContentParser( name = 'get image file url (based on old booru parser)', content_type = HC.CONTENT_TYPE_URLS, formula = formula, additional_info = additional_info )
        
        content_parsers.append( image_link_content_parser )
        
    
    for ( classname, namespace ) in list(tag_classnames_to_namespaces.items()):
        
        tag_rules = []
        
        rule_type = ClientParsing.HTML_RULE_TYPE_DESCENDING
        tag_name = None
        tag_attributes = { 'class' : classname }
        tag_index = None
        
        tag_rules.append( ClientParsing.ParseRuleHTML( rule_type = rule_type, tag_name = tag_name, tag_attributes = tag_attributes, tag_index = tag_index ) )
        
        rule_type = ClientParsing.HTML_RULE_TYPE_DESCENDING
        tag_name = 'a'
        tag_attributes = None
        tag_index = None
        
        tag_rules.append( ClientParsing.ParseRuleHTML( rule_type = rule_type, tag_name = tag_name, tag_attributes = tag_attributes, tag_index = tag_index ) )
        
        formula = ClientParsing.ParseFormulaHTML( tag_rules = tag_rules, content_to_fetch = ClientParsing.HTML_CONTENT_STRING )
        
        additional_info = namespace
        
        tag_content_parser = ClientParsing.ContentParser( name = 'get "' + namespace + '" tags', content_type = HC.CONTENT_TYPE_MAPPINGS, formula = formula, additional_info = additional_info )
        
        content_parsers.append( tag_content_parser )
        
    
    post_parser = ClientParsing.PageParser( name + ' post page parser', content_parsers = content_parsers, example_urls = [] )
    
    #
    
    return ( gug, gallery_parser, post_parser )
    
def ConvertGalleryIdentifierToGUGKeyAndName( gallery_identifier ):
    
    gug_name = ConvertGalleryIdentifierToGUGName( gallery_identifier )
    
    from . import ClientDefaults
    
    gugs = ClientDefaults.GetDefaultGUGs()
    
    for gug in gugs:
        
        if gug.GetName() == gug_name:
            
            return gug.GetGUGKeyAndName()
            
        
    
    return ( HydrusData.GenerateKey(), gug_name )
    
def ConvertGalleryIdentifierToGUGName( gallery_identifier ):
    
    site_type = gallery_identifier.GetSiteType()
    
    if site_type == HC.SITE_TYPE_DEVIANT_ART:
        
        return 'deviant art artist lookup'
        
    elif site_type == HC.SITE_TYPE_TUMBLR:
        
        return 'tumblr username lookup'
        
    elif site_type == HC.SITE_TYPE_NEWGROUNDS:
        
        return 'newgrounds artist lookup'
        
    elif site_type == HC.SITE_TYPE_HENTAI_FOUNDRY_ARTIST:
        
        return 'hentai foundry artist lookup'
        
    elif site_type == HC.SITE_TYPE_HENTAI_FOUNDRY_TAGS:
        
        return 'hentai foundry tag search'
        
    elif site_type == HC.SITE_TYPE_PIXIV_ARTIST_ID:
        
        return 'pixiv artist lookup'
        
    elif site_type == HC.SITE_TYPE_PIXIV_TAG:
        
        return 'pixiv tag search'
        
    elif site_type == HC.SITE_TYPE_BOORU:
        
        booru_name_converter = {}
        
        booru_name_converter[ 'gelbooru' ] = 'gelbooru tag search'
        booru_name_converter[ 'safebooru' ] = 'safebooru tag search'
        booru_name_converter[ 'e621' ] = 'e621 tag search'
        booru_name_converter[ 'rule34@paheal' ] = 'rule34.paheal tag search'
        booru_name_converter[ 'danbooru' ] = 'danbooru tag search'
        booru_name_converter[ 'rule34@booru.org' ] = 'rule34.xxx tag search'
        booru_name_converter[ 'furry@booru.org' ] = 'furry.booru.org tag search'
        booru_name_converter[ 'xbooru' ] = 'xbooru tag search'
        booru_name_converter[ 'konachan' ] = 'konachan tag search'
        booru_name_converter[ 'yande.re' ] = 'yande.re tag search'
        booru_name_converter[ 'tbib' ] = 'tbib tag search'
        booru_name_converter[ 'sankaku chan' ] = 'sankaku channel tag search'
        booru_name_converter[ 'sankaku idol' ] = 'sankaku idol tag search'
        booru_name_converter[ 'rule34hentai' ] = 'rule34hentai tag search'
        
        booru_name = gallery_identifier.GetAdditionalInfo()
        
        if booru_name in booru_name_converter:
            
            return booru_name_converter[ booru_name ]
            
        else:
            
            return booru_name
            
        
    else:
        
        return 'unknown site'
        
    
class GalleryIdentifier( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_GALLERY_IDENTIFIER
    SERIALISABLE_NAME = 'Gallery Identifier'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, site_type = None, additional_info = None ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._site_type = site_type
        self._additional_info = additional_info
        
    
    def __eq__( self, other ):
        
        return self.__hash__() == other.__hash__()
        
    
    def __hash__( self ):
        
        return ( self._site_type, self._additional_info ).__hash__()
        
    
    def __ne__( self, other ):
        
        return self.__hash__() != other.__hash__()
        
    
    def __repr__( self ):
        
        text = 'Gallery Identifier: ' + HC.site_type_string_lookup[ self._site_type ]
        
        if self._site_type == HC.SITE_TYPE_BOORU:
            
            text += ': ' + str( self._additional_info )
            
        
        return text
        
    
    def _GetSerialisableInfo( self ):
        
        return ( self._site_type, self._additional_info )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._site_type, self._additional_info ) = serialisable_info
        
    
    def GetAdditionalInfo( self ):
        
        return self._additional_info
        
    
    def GetSiteType( self ):
        
        return self._site_type
        
    
    def ToString( self ):
        
        text = HC.site_type_string_lookup[ self._site_type ]
        
        if self._site_type == HC.SITE_TYPE_BOORU and self._additional_info is not None:
            
            booru_name = self._additional_info
            
            text = booru_name
            
        
        return text
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_GALLERY_IDENTIFIER ] = GalleryIdentifier

class QuickDownloadManager( object ):
    
    def __init__( self, controller ):
        
        self._controller = controller
        
        self._pending_hashes = set()
        
        self._lock = threading.Lock()
        
        self._shutting_down = False
        
        self._new_files_event = threading.Event()
        
        self._controller.sub( self, 'Wake', 'wake_daemons' )
        
    
    def DownloadFiles( self, hashes ):
        
        with self._lock:
            
            self._pending_hashes.update( hashes )
            
            self._new_files_event.set()
            
        
    
    def MainLoop( self ):
        
        hashes_still_to_download_in_this_run = set()
        total_hashes_in_this_run = 0
        total_successful_hashes_in_this_run = 0
        
        while not ( HydrusThreading.IsThreadShuttingDown() or self._shutting_down or HG.view_shutdown ):
            
            with self._lock:
                
                if len( self._pending_hashes ) > 0:
                    
                    if total_hashes_in_this_run == 0:
                        
                        job_key = ClientThreading.JobKey( cancellable = True )
                        
                        job_key.SetVariable( 'popup_title', 'downloading' )
                        
                        job_key.SetVariable( 'popup_text_1', 'initialising downloader' )
                        
                        job_key_pub_job = self._controller.CallLater( 2.0, self._controller.pub, 'message', job_key )
                        
                    
                    num_before = len( hashes_still_to_download_in_this_run )
                    
                    hashes_still_to_download_in_this_run.update( self._pending_hashes )
                    
                    num_after = len( hashes_still_to_download_in_this_run )
                    
                    total_hashes_in_this_run += num_after - num_before
                    
                    self._pending_hashes = set()
                    
                
            
            if len( hashes_still_to_download_in_this_run ) == 0:
                
                total_hashes_in_this_run = 0
                total_successful_hashes_in_this_run = 0
                
                self._new_files_event.wait( 5 )
                
                self._new_files_event.clear()
                
                continue
                
            
            if job_key.IsCancelled():
                
                hashes_still_to_download_in_this_run = set()
                
                continue
                
            
            hash = random.sample( hashes_still_to_download_in_this_run, 1 )[0]
            
            hashes_still_to_download_in_this_run.discard( hash )
            
            total_done = total_hashes_in_this_run - len( hashes_still_to_download_in_this_run )
            
            job_key.SetVariable( 'popup_text_1', 'downloading files from remote services: {}'.format( HydrusData.ConvertValueRangeToPrettyString( total_done, total_hashes_in_this_run ) ) )
            job_key.SetVariable( 'popup_gauge_1', ( total_done, total_hashes_in_this_run ) )
            
            try:
                
                errors_occured = []
                file_successful = False
                
                ( media_result, ) = self._controller.Read( 'media_results', ( hash, ) )
                
                service_keys = list( media_result.GetLocationsManager().GetCurrent() )
                
                random.shuffle( service_keys )
                
                if CC.LOCAL_FILE_SERVICE_KEY in service_keys:
                    
                    total_successful_hashes_in_this_run += 1
                    
                    continue
                    
                
                for service_key in service_keys:
                    
                    try:
                        
                        service = self._controller.services_manager.GetService( service_key )
                        
                    except:
                        
                        continue
                        
                    
                    try:
                        
                        if service.GetServiceType() == HC.FILE_REPOSITORY:
                            
                            file_repository = service
                            
                            if file_repository.IsFunctional():
                                
                                ( os_file_handle, temp_path ) = HydrusPaths.GetTempPath()
                                
                                try:
                                    
                                    file_repository.Request( HC.GET, 'file', { 'hash' : hash }, temp_path = temp_path )
                                    
                                    self._controller.WaitUntilModelFree()
                                    
                                    exclude_deleted = False # this is the important part here
                                    do_not_check_known_urls_before_importing = False
                                    do_not_check_hashes_before_importing = False
                                    allow_decompression_bombs = True
                                    min_size = None
                                    max_size = None
                                    max_gif_size = None
                                    min_resolution = None
                                    max_resolution = None
                                    automatic_archive = False
                                    associate_source_urls = True
                                    
                                    file_import_options = ClientImportOptions.FileImportOptions()
                                    
                                    file_import_options.SetPreImportOptions( exclude_deleted, do_not_check_known_urls_before_importing, do_not_check_hashes_before_importing, allow_decompression_bombs, min_size, max_size, max_gif_size, min_resolution, max_resolution )
                                    file_import_options.SetPostImportOptions( automatic_archive, associate_source_urls )
                                    
                                    file_import_job = ClientImportFileSeeds.FileImportJob( temp_path, file_import_options )
                                    
                                    file_import_job.DoWork()
                                    
                                    file_successful = True
                                    
                                    break
                                    
                                finally:
                                    
                                    HydrusPaths.CleanUpTempPath( os_file_handle, temp_path )
                                    
                                
                            
                        elif service.GetServiceType() == HC.IPFS:
                            
                            multihashes = HG.client_controller.Read( 'service_filenames', service_key, { hash } )
                            
                            if len( multihashes ) > 0:
                                
                                multihash = multihashes[0]
                                
                                service.ImportFile( multihash, silent = True )
                                
                                file_successful = True
                                
                                break
                                
                            
                        
                    except Exception as e:
                        
                        errors_occured.append( e )
                        
                    
                
                if file_successful:
                    
                    total_successful_hashes_in_this_run += 1
                    
                
                if len( errors_occured ) > 0:
                    
                    if not file_successful:
                        
                        raise errors_occured[0]
                        
                    
                
            except Exception as e:
                
                HydrusData.ShowException( e )
                
                hashes_still_to_download_in_this_run = 0
                
            finally:
                
                if len( hashes_still_to_download_in_this_run ) == 0:
                    
                    job_key.DeleteVariable( 'popup_text_1' )
                    job_key.DeleteVariable( 'popup_gauge_1' )
                    
                    if total_successful_hashes_in_this_run > 0:
                        
                        job_key.SetVariable( 'popup_text_1', HydrusData.ToHumanInt( total_successful_hashes_in_this_run ) + ' files downloaded' )
                        
                    
                    job_key_pub_job.Cancel()
                    
                    job_key.Finish()
                    
                    job_key.Delete( 1 )
                    
                
            
        
    
    def Shutdown( self ):
        
        self._shutting_down = True
        
        self._new_files_event.set()
        
    
    def Wake( self ):
        
        self._new_files_event.set()
        
