import os
import time
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusTags
from hydrus.core import HydrusTime
from hydrus.core.files import HydrusFileHandling
from hydrus.core.files.images import HydrusImageHandling
from hydrus.core.networking import HydrusServerRequest
from hydrus.core.networking import HydrusServerResources

from hydrus.client import ClientAPI
from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientLocation
from hydrus.client import ClientRendering
from hydrus.client import ClientThreading
from hydrus.client import ClientUgoiraHandling
from hydrus.client.media import ClientMedia
from hydrus.client.media import ClientMediaResult
from hydrus.client.media import ClientMediaManagers
from hydrus.client.metadata import ClientTags
from hydrus.client.networking.api import ClientLocalServerCore
from hydrus.client.networking.api import ClientLocalServerResources
from hydrus.client.search import ClientSearchFileSearchContext
from hydrus.client.search import ClientSearchTagContext


class HydrusResourceClientAPIRestrictedGetFiles( ClientLocalServerResources.HydrusResourceClientAPIRestricted ):
    
    def _CheckAPIPermissions( self, request: HydrusServerRequest.HydrusRequest ):
        
        request.client_api_permissions.CheckPermission( ClientAPI.CLIENT_API_PERMISSION_SEARCH_FILES )
        
    

class HydrusResourceClientAPIRestrictedGetFilesSearchFiles( HydrusResourceClientAPIRestrictedGetFiles ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        location_context = ClientLocalServerCore.ParseLocationContext( request, ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY ) )
        
        tag_service_key = ClientLocalServerCore.ParseTagServiceKey( request )
        
        if tag_service_key == CC.COMBINED_TAG_SERVICE_KEY and location_context.IsAllKnownFiles():
            
            raise HydrusExceptions.BadRequestException( 'Sorry, search for all known tags over all known files is not supported!' )
            
        
        include_current_tags = request.parsed_request_args.GetValue( 'include_current_tags', bool, default_value = True )
        include_pending_tags = request.parsed_request_args.GetValue( 'include_pending_tags', bool, default_value = True )
        
        tag_context = ClientSearchTagContext.TagContext( service_key = tag_service_key, include_current_tags = include_current_tags, include_pending_tags = include_pending_tags )
        predicates = ClientLocalServerCore.ParseClientAPISearchPredicates( request )
        
        return_hashes = False
        return_file_ids = True
        
        if len( predicates ) == 0:
            
            hash_ids = []
            
        else:
            
            file_search_context = ClientSearchFileSearchContext.FileSearchContext( location_context = location_context, tag_context = tag_context, predicates = predicates )
            
            file_sort_type = CC.SORT_FILES_BY_IMPORT_TIME
            
            if 'file_sort_type' in request.parsed_request_args:
                
                file_sort_type = request.parsed_request_args[ 'file_sort_type' ]
                
            
            if file_sort_type not in CC.SYSTEM_SORT_TYPES:
                
                raise HydrusExceptions.BadRequestException( 'Sorry, did not understand that sort type!' )
                
            
            file_sort_asc = False
            
            if 'file_sort_asc' in request.parsed_request_args:
                
                file_sort_asc = request.parsed_request_args.GetValue( 'file_sort_asc', bool )
                
            
            sort_order = CC.SORT_ASC if file_sort_asc else CC.SORT_DESC
            
            # newest first
            sort_by = ClientMedia.MediaSort( sort_type = ( 'system', file_sort_type ), sort_order = sort_order )
            
            if 'return_hashes' in request.parsed_request_args:
                
                return_hashes = request.parsed_request_args.GetValue( 'return_hashes', bool )
                
            
            if 'return_file_ids' in request.parsed_request_args:
                
                return_file_ids = request.parsed_request_args.GetValue( 'return_file_ids', bool )
                
            
            job_status = ClientThreading.JobStatus( cancellable = True )
            
            request.disconnect_callables.append( job_status.Cancel )
            
            hash_ids = CG.client_controller.Read( 'file_query_ids', file_search_context, job_status = job_status, sort_by = sort_by, apply_implicit_limit = False )
            
        
        request.client_api_permissions.SetLastSearchResults( hash_ids )
        
        body_dict = {}
        
        if return_hashes:
            
            hash_ids_to_hashes = CG.client_controller.Read( 'hash_ids_to_hashes', hash_ids = hash_ids )
            
            # maintain sort
            body_dict[ 'hashes' ] = [ hash_ids_to_hashes[ hash_id ].hex() for hash_id in hash_ids ]
            
        
        if return_file_ids:
            
            body_dict[ 'file_ids' ] = list( hash_ids )
            
        
        body = ClientLocalServerCore.Dumps( body_dict, request.preferred_mime )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = request.preferred_mime, body = body )
        
        return response_context
        
    

def ParseAndFetchMediaResult( request: HydrusServerRequest.HydrusRequest ) -> ClientMediaResult.MediaResult:
    
    try:
        
        if 'file_id' in request.parsed_request_args:
            
            file_id = request.parsed_request_args.GetValue( 'file_id', int )
            
            request.client_api_permissions.CheckPermissionToSeeFiles( ( file_id, ) )
            
            ( media_result, ) = CG.client_controller.Read( 'media_results_from_ids', ( file_id, ) )
            
        elif 'hash' in request.parsed_request_args:
            
            request.client_api_permissions.CheckCanSeeAllFiles()
            
            hash = request.parsed_request_args.GetValue( 'hash', bytes )
            
            media_result = CG.client_controller.Read( 'media_result', hash )
            
        else:
            
            raise HydrusExceptions.BadRequestException( 'Please include a file_id or hash parameter!' )
            
        
    except HydrusExceptions.DataMissing as e:
        
        raise HydrusExceptions.NotFoundException( 'One or more of those file identifiers was missing!' )
        
    
    return media_result
    

class HydrusResourceClientAPIRestrictedGetFilesGetFile( HydrusResourceClientAPIRestrictedGetFiles ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        media_result = ParseAndFetchMediaResult( request )
        
        if not media_result.GetLocationsManager().IsLocal():
            
            raise HydrusExceptions.FileMissingException( 'The client does not have this file!' )
            
        
        try:
            
            hash = media_result.GetHash()
            mime = media_result.GetMime()
            
            path = CG.client_controller.client_files_manager.GetFilePath( hash, mime )
            
            if not os.path.exists( path ):
                
                raise HydrusExceptions.FileMissingException()
                
            
        except HydrusExceptions.FileMissingException:
            
            raise HydrusExceptions.NotFoundException( 'That file seems to be missing!' )
            
        
        is_attachment = request.parsed_request_args.GetValue( 'download', bool, default_value = False )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = mime, path = path, is_attachment = is_attachment )
        
        return response_context
        
    

class HydrusResourceClientAPIRestrictedGetFilesGetRenderedFile( HydrusResourceClientAPIRestrictedGetFiles ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        
        
        try:
            
            media_result: ClientMediaResult.MediaResult
            
            if 'file_id' in request.parsed_request_args:
                
                file_id = request.parsed_request_args.GetValue( 'file_id', int )
                
                request.client_api_permissions.CheckPermissionToSeeFiles( ( file_id, ) )
                
                ( media_result, ) = CG.client_controller.Read( 'media_results_from_ids', ( file_id, ) )
                
            elif 'hash' in request.parsed_request_args:
                
                request.client_api_permissions.CheckCanSeeAllFiles()
                
                hash = request.parsed_request_args.GetValue( 'hash', bytes )
                
                media_result = CG.client_controller.Read( 'media_result', hash )
                
            else:
                
                raise HydrusExceptions.BadRequestException( 'Please include a file_id or hash parameter!' )
                
            
        except HydrusExceptions.DataMissing as e:
            
            raise HydrusExceptions.NotFoundException( 'One or more of those file identifiers was missing!' )
            
        
        if media_result.IsStaticImage():
            
            if 'render_format' in request.parsed_request_args:
                
                format = request.parsed_request_args.GetValue( 'render_format', int )
                
                if not format in [ HC.IMAGE_PNG, HC.IMAGE_JPEG, HC.IMAGE_WEBP ]:
                    
                    raise HydrusExceptions.BadRequestException( 'Invalid render format!' )
                
            else:
                
                format = HC.IMAGE_PNG
            
            renderer: ClientRendering.ImageRenderer = CG.client_controller.GetCache( 'images' ).GetImageRenderer( media_result )
            
            while not renderer.IsReady():
                
                if request.disconnected:
                    
                    return
                    
                
                time.sleep( 0.01 )
                
            
            numpy_image = renderer.GetNumPyImage()
            
            if 'width' in request.parsed_request_args and 'height' in request.parsed_request_args:
                
                width = request.parsed_request_args.GetValue( 'width', int )
                height = request.parsed_request_args.GetValue( 'height', int )
                
                if width < 1:
                    
                    raise HydrusExceptions.BadRequestException( 'Width must be greater than 0!' )
                    
                
                if height < 1:
                    
                    raise HydrusExceptions.BadRequestException( 'Height must be greater than 0!' )
                    
                
                numpy_image = HydrusImageHandling.ResizeNumPyImage( numpy_image, ( width, height ) )
                
            
            if 'render_quality' in request.parsed_request_args:
                
                quality = request.parsed_request_args.GetValue( 'render_quality', int )
                
            else:
                
                if format == HC.IMAGE_PNG:
                    
                    quality = 1  # fastest png compression
                    
                else:
                    
                    quality = 80
                    
                
            max_age = 86400 * 365
            
            body = HydrusImageHandling.GenerateFileBytesForRenderAPI( numpy_image, format, quality )
        
        elif media_result.GetMime() == HC.ANIMATION_UGOIRA:
            
            if 'render_format' in request.parsed_request_args:
                
                format = request.parsed_request_args.GetValue( 'render_format', int )
                
                if not format in [ HC.ANIMATION_APNG, HC.ANIMATION_WEBP ]:
                    
                    raise HydrusExceptions.BadRequestException( 'Invalid render format!' )
                
            else:
                
                format = HC.ANIMATION_APNG # maybe we should default to animated webp, it is much faster
                
            
            if 'render_quality' in request.parsed_request_args:
                
                quality = request.parsed_request_args.GetValue( 'render_quality', int )
                
            else:
                
                quality = 80 # compress_level has no effect for APNG so we don't use quality in that case.
            
            body = ClientUgoiraHandling.ConvertUgoiraToBytesForAPI( media_result, format, quality )
            
            if media_result.GetDurationMS() is not None:
                
                # if a ugoira has a duration, it has valid animation.json
                # thus frame timings and the resulting render are immutable
                max_age = 86400 * 365
                
            else:
                
                # frame timing could change with notes!
                max_age = 3600
        
        else:
            
            raise HydrusExceptions.BadRequestException('Requested file is not an image!')
        
        is_attachment = request.parsed_request_args.GetValue( 'download', bool, default_value = False )

        response_context = HydrusServerResources.ResponseContext( 200, mime = format, body = body, is_attachment = is_attachment, max_age = max_age )
        
        return response_context
        
    
class HydrusResourceClientAPIRestrictedGetFilesFileHashes( HydrusResourceClientAPIRestrictedGetFiles ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        supported_hash_types = ( 'sha256', 'md5', 'sha1', 'sha512' )
        
        source_hash_type = request.parsed_request_args.GetValue( 'source_hash_type', str, default_value = 'sha256' )
        
        if source_hash_type not in supported_hash_types:
            
            raise HydrusExceptions.BadRequestException( 'I do not support that hash type!' )
            
        
        desired_hash_type = request.parsed_request_args.GetValue( 'desired_hash_type', str )
        
        if desired_hash_type not in supported_hash_types:
            
            raise HydrusExceptions.BadRequestException( 'I do not support that hash type!' )
            
        
        source_hashes = set()
        
        if 'hash' in request.parsed_request_args:
            
            request_hash = request.parsed_request_args.GetValue( 'hash', bytes )
            
            source_hashes.add( request_hash )
            
        
        if 'hashes' in request.parsed_request_args:
            
            request_hashes = request.parsed_request_args.GetValue( 'hashes', list, expected_list_type = bytes )
            
            source_hashes.update( request_hashes )
            
        
        if len( source_hashes ) == 0:
            
            raise HydrusExceptions.BadRequestException( 'You have to specify a hash to look up!' )
            
        
        ClientLocalServerCore.CheckHashLength( source_hashes, hash_type = source_hash_type )
        
        source_to_desired = CG.client_controller.Read( 'file_hashes', source_hashes, source_hash_type, desired_hash_type )
        
        encoded_source_to_desired = { source_hash.hex() : desired_hash.hex() for ( source_hash, desired_hash ) in source_to_desired.items() }
        
        body_dict = {
            'hashes' : encoded_source_to_desired
        }
        
        body = ClientLocalServerCore.Dumps( body_dict, request.preferred_mime )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = request.preferred_mime, body = body )
        
        return response_context
        
    

def AddMissingHashToFileMetadata( metadata: list, hash: bytes ):
    
    metadata_row = {
        'file_id' : None,
        'hash' : hash.hex()
    }
    
    metadata.append( metadata_row )
    

class HydrusResourceClientAPIRestrictedGetFilesFileMetadata( HydrusResourceClientAPIRestrictedGetFiles ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        only_return_identifiers = request.parsed_request_args.GetValue( 'only_return_identifiers', bool, default_value = False )
        only_return_basic_information = request.parsed_request_args.GetValue( 'only_return_basic_information', bool, default_value = False )
        hide_service_keys_tags = request.parsed_request_args.GetValue( 'hide_service_keys_tags', bool, default_value = True )
        detailed_url_information = request.parsed_request_args.GetValue( 'detailed_url_information', bool, default_value = False )
        include_notes = request.parsed_request_args.GetValue( 'include_notes', bool, default_value = False )
        include_milliseconds = request.parsed_request_args.GetValue( 'include_milliseconds', bool, default_value = False )
        include_services_object = request.parsed_request_args.GetValue( 'include_services_object', bool, default_value = True )
        create_new_file_ids = request.parsed_request_args.GetValue( 'create_new_file_ids', bool, default_value = False )
        include_blurhash = request.parsed_request_args.GetValue( 'include_blurhash', bool, default_value = False )
        
        if include_milliseconds:
            
            time_converter = lambda t: t / 1000 if t is not None else None
            
        else:
            
            time_converter = HydrusTime.SecondiseMS
            
        
        hashes = ClientLocalServerCore.ParseHashes( request )
        
        hash_ids_to_hashes = CG.client_controller.Read( 'hash_ids_to_hashes', hashes = hashes, create_new_hash_ids = create_new_file_ids )
        
        hashes_to_hash_ids = { hash : hash_id for ( hash_id, hash ) in hash_ids_to_hashes.items() }
        
        hash_ids = set( hash_ids_to_hashes.keys() )
        
        request.client_api_permissions.CheckPermissionToSeeFiles( hash_ids )
        
        body_dict = {}
        
        metadata = []
        
        if only_return_identifiers:
            
            for hash in hashes:
                
                if hash in hashes_to_hash_ids:
                    
                    metadata_row = {
                        'file_id' : hashes_to_hash_ids[ hash ],
                        'hash' : hash.hex()
                    }
                    
                    metadata.append( metadata_row )
                    
                else:
                    
                    AddMissingHashToFileMetadata( metadata, hash )
                    
                
            
        elif only_return_basic_information:
            
            file_info_managers: typing.List[ ClientMediaManagers.FileInfoManager ] = CG.client_controller.Read( 'file_info_managers_from_ids', hash_ids )
            
            hashes_to_file_info_managers = { file_info_manager.hash : file_info_manager for file_info_manager in file_info_managers }
            
            for hash in hashes:
                
                if hash in hashes_to_file_info_managers:
                    
                    file_info_manager = hashes_to_file_info_managers[ hash ]
                    
                    metadata_row = {
                        'file_id' : file_info_manager.hash_id,
                        'hash' : file_info_manager.hash.hex(),
                        'size' : file_info_manager.size,
                        'mime' : HC.mime_mimetype_string_lookup[ file_info_manager.mime ],
                        'filetype_human' : HC.mime_string_lookup[ file_info_manager.mime ],
                        'filetype_enum' : file_info_manager.mime,
                        'ext' : HC.mime_ext_lookup[ file_info_manager.mime ],
                        'width' : file_info_manager.width,
                        'height' : file_info_manager.height,
                        'duration' : file_info_manager.duration,
                        'num_frames' : file_info_manager.num_frames,
                        'num_words' : file_info_manager.num_words,
                        'has_audio' : file_info_manager.has_audio
                    }
                    
                    filetype_forced = file_info_manager.FiletypeIsForced()
                    
                    metadata_row[ 'filetype_forced' ] = filetype_forced
                    
                    if filetype_forced:
                        
                        metadata_row[ 'original_mime' ] = HC.mime_mimetype_string_lookup[ file_info_manager.original_mime ]
                        
                    
                    if include_blurhash:
                        
                        metadata_row[ 'blurhash' ] = file_info_manager.blurhash
                        
                    
                    metadata.append( metadata_row )
                    
                else:
                    
                    AddMissingHashToFileMetadata( metadata, hash )
                    
                
            
        else:
            
            media_results: typing.List[ ClientMediaResult.MediaResult ] = CG.client_controller.Read( 'media_results_from_ids', hash_ids )
            
            hashes_to_media_results = { media_result.GetFileInfoManager().hash : media_result for media_result in media_results }
            
            services_manager = CG.client_controller.services_manager
            
            rating_service_keys = services_manager.GetServiceKeys( HC.RATINGS_SERVICES )
            tag_service_keys = services_manager.GetServiceKeys( HC.ALL_TAG_SERVICES )
            service_keys_to_types = { service.GetServiceKey() : service.GetServiceType() for service in services_manager.GetServices() }
            service_keys_to_names = services_manager.GetServiceKeysToNames()
            
            ipfs_service_keys = services_manager.GetServiceKeys( ( HC.IPFS, ) )
            
            thumbnail_bounding_dimensions = CG.client_controller.options[ 'thumbnail_dimensions' ]
            thumbnail_scale_type = CG.client_controller.new_options.GetInteger( 'thumbnail_scale_type' )
            thumbnail_dpr_percent = CG.client_controller.new_options.GetInteger( 'thumbnail_dpr_percent' )
            
            for hash in hashes:
                
                if hash in hashes_to_media_results:
                    
                    media_result = hashes_to_media_results[ hash ]
                    
                    file_info_manager = media_result.GetFileInfoManager()
                    
                    mime = file_info_manager.mime
                    width = file_info_manager.width
                    height = file_info_manager.height
                    
                    pixel_hash = file_info_manager.pixel_hash
                    
                    if pixel_hash is not None:
                        
                        pixel_hash_encoded = pixel_hash.hex()
                        
                    else:
                        
                        pixel_hash_encoded = None
                        
                    
                    metadata_row = {
                        'file_id' : file_info_manager.hash_id,
                        'hash' : file_info_manager.hash.hex(),
                        'size' : file_info_manager.size,
                        'mime' : HC.mime_mimetype_string_lookup[ mime ],
                        'filetype_human' : HC.mime_string_lookup[ file_info_manager.mime ],
                        'filetype_enum' : file_info_manager.mime,
                        'ext' : HC.mime_ext_lookup[ mime ],
                        'width' : width,
                        'height' : height,
                        'duration' : file_info_manager.duration,
                        'num_frames' : file_info_manager.num_frames,
                        'num_words' : file_info_manager.num_words,
                        'has_audio' : file_info_manager.has_audio,
                        'blurhash' : file_info_manager.blurhash,
                        'pixel_hash' : pixel_hash_encoded
                    }
                    
                    filetype_forced = file_info_manager.FiletypeIsForced()
                    
                    metadata_row[ 'filetype_forced' ] = filetype_forced
                    
                    if filetype_forced:
                        
                        metadata_row[ 'original_mime' ] = HC.mime_mimetype_string_lookup[ file_info_manager.original_mime ]
                        
                    
                    if file_info_manager.mime in HC.MIMES_WITH_THUMBNAILS:
                        
                        if width is not None and height is not None and width > 0 and height > 0:
                            
                            ( expected_thumbnail_width, expected_thumbnail_height ) = HydrusImageHandling.GetThumbnailResolution( ( width, height ), thumbnail_bounding_dimensions, thumbnail_scale_type, thumbnail_dpr_percent )
                            
                            metadata_row[ 'thumbnail_width' ] = expected_thumbnail_width
                            metadata_row[ 'thumbnail_height' ] = expected_thumbnail_height
                            
                        
                    
                    if include_notes:
                        
                        metadata_row[ 'notes' ] = media_result.GetNotesManager().GetNamesToNotes()
                        
                    
                    locations_manager = media_result.GetLocationsManager()
                    
                    metadata_row[ 'file_services' ] = {
                        'current' : {},
                        'deleted' : {}
                    }
                    
                    times_manager = locations_manager.GetTimesManager()
                    
                    current = locations_manager.GetCurrent()
                    
                    for file_service_key in current:
                        
                        metadata_row[ 'file_services' ][ 'current' ][ file_service_key.hex() ] = {
                            'name' : service_keys_to_names[ file_service_key ],
                            'type' : service_keys_to_types[ file_service_key ],
                            'type_pretty' : HC.service_string_lookup[ service_keys_to_types[ file_service_key ] ],
                            'time_imported' : time_converter( times_manager.GetImportedTimestampMS( file_service_key ) )
                        }
                        
                    
                    deleted = locations_manager.GetDeleted()
                    
                    for file_service_key in deleted:
                        
                        metadata_row[ 'file_services' ][ 'deleted' ][ file_service_key.hex() ] = {
                            'name' : service_keys_to_names[ file_service_key ],
                            'type' : service_keys_to_types[ file_service_key ],
                            'type_pretty' : HC.service_string_lookup[ service_keys_to_types[ file_service_key ] ],
                            'time_deleted' : time_converter( times_manager.GetDeletedTimestampMS( file_service_key ) ),
                            'time_imported' : time_converter( times_manager.GetPreviouslyImportedTimestampMS( file_service_key ) )
                        }
                        
                    
                    metadata_row[ 'time_modified' ] = time_converter( times_manager.GetAggregateModifiedTimestampMS() )
                    
                    domains_to_file_modified_timestamps_ms = times_manager.GetDomainModifiedTimestampsMS()
                    
                    local_modified_timestamp_ms = times_manager.GetFileModifiedTimestampMS()
                    
                    if local_modified_timestamp_ms is not None:
                        
                        domains_to_file_modified_timestamps_ms[ 'local' ] = local_modified_timestamp_ms
                        
                    
                    metadata_row[ 'time_modified_details' ] = { domain : time_converter( timestamp_ms ) for ( domain, timestamp_ms ) in domains_to_file_modified_timestamps_ms.items() }
                    
                    metadata_row[ 'is_inbox' ] = locations_manager.inbox
                    metadata_row[ 'is_local' ] = locations_manager.IsLocal()
                    metadata_row[ 'is_trashed' ] = locations_manager.IsTrashed()
                    metadata_row[ 'is_deleted' ] = CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY in locations_manager.GetDeleted() or locations_manager.IsTrashed()
                    
                    metadata_row[ 'has_transparency' ] = file_info_manager.has_transparency
                    metadata_row[ 'has_exif' ] = file_info_manager.has_exif
                    metadata_row[ 'has_human_readable_embedded_metadata' ] = file_info_manager.has_human_readable_embedded_metadata
                    metadata_row[ 'has_icc_profile' ] = file_info_manager.has_icc_profile
                    
                    known_urls = sorted( locations_manager.GetURLs() )
                    
                    metadata_row[ 'known_urls' ] = known_urls
                    
                    metadata_row[ 'ipfs_multihashes' ] = { ipfs_service_key.hex() : multihash for ( ipfs_service_key, multihash ) in locations_manager.GetServiceFilenames().items() if ipfs_service_key in ipfs_service_keys }
                    
                    if detailed_url_information:
                        
                        detailed_known_urls = []
                        
                        for known_url in known_urls:
                            
                            try:
                                
                                normalised_url = CG.client_controller.network_engine.domain_manager.NormaliseURL( known_url )
                                
                                ( url_type, match_name, can_parse, cannot_parse_reason ) = CG.client_controller.network_engine.domain_manager.GetURLParseCapability( normalised_url )
                                
                            except HydrusExceptions.URLClassException as e:
                                
                                continue
                                
                            
                            detailed_dict = { 'normalised_url' : normalised_url, 'url_type' : url_type, 'url_type_string' : HC.url_type_string_lookup[ url_type ], 'match_name' : match_name, 'can_parse' : can_parse }
                            
                            if not can_parse:
                                
                                detailed_dict[ 'cannot_parse_reason' ] = cannot_parse_reason
                                
                            
                            detailed_known_urls.append( detailed_dict )
                            
                        
                        metadata_row[ 'detailed_known_urls' ] = detailed_known_urls
                        
                    
                    ratings_manager = media_result.GetRatingsManager()
                    
                    ratings_dict = {}
                    
                    for rating_service_key in rating_service_keys:
                        
                        rating_object = ratings_manager.GetRatingForAPI( rating_service_key )
                        
                        ratings_dict[ rating_service_key.hex() ] = rating_object
                        
                    
                    metadata_row[ 'ratings' ] = ratings_dict
                    
                    tags_manager = media_result.GetTagsManager()
                    
                    tags_dict = {}
                    
                    for tag_service_key in tag_service_keys:
                        
                        storage_statuses_to_tags = tags_manager.GetStatusesToTags( tag_service_key, ClientTags.TAG_DISPLAY_STORAGE )
                        
                        storage_tags_json_serialisable = { str( status ) : sorted( tags, key = HydrusTags.ConvertTagToSortable ) for ( status, tags ) in storage_statuses_to_tags.items() if len( tags ) > 0 }
                        
                        display_statuses_to_tags = tags_manager.GetStatusesToTags( tag_service_key, ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL )
                        
                        display_tags_json_serialisable = { str( status ) : sorted( tags, key = HydrusTags.ConvertTagToSortable ) for ( status, tags ) in display_statuses_to_tags.items() if len( tags ) > 0 }
                        
                        tags_dict_object = {
                            'name' : service_keys_to_names[ tag_service_key ],
                            'type' : service_keys_to_types[ tag_service_key ],
                            'type_pretty' : HC.service_string_lookup[ service_keys_to_types[ tag_service_key ] ],
                            'storage_tags' : storage_tags_json_serialisable,
                            'display_tags' : display_tags_json_serialisable
                        }
                        
                        tags_dict[ tag_service_key.hex() ] = tags_dict_object
                        
                    
                    metadata_row[ 'tags' ] = tags_dict
                    
                    # Old stuff starts here
                    
                    api_service_keys_to_statuses_to_tags = {}
                    
                    service_keys_to_statuses_to_tags = tags_manager.GetServiceKeysToStatusesToTags( ClientTags.TAG_DISPLAY_STORAGE )
                    
                    for ( service_key, statuses_to_tags ) in service_keys_to_statuses_to_tags.items():
                        
                        statuses_to_tags_json_serialisable = { str( status ) : sorted( tags, key = HydrusTags.ConvertTagToSortable ) for ( status, tags ) in statuses_to_tags.items() if len( tags ) > 0 }
                        
                        if len( statuses_to_tags_json_serialisable ) > 0:
                            
                            api_service_keys_to_statuses_to_tags[ service_key.hex() ] = statuses_to_tags_json_serialisable
                            
                        
                    
                    if not hide_service_keys_tags:
                        
                        metadata_row[ 'service_keys_to_statuses_to_tags' ] = api_service_keys_to_statuses_to_tags
                        
                    
                    #
                    
                    api_service_keys_to_statuses_to_tags = {}
                    
                    service_keys_to_statuses_to_tags = tags_manager.GetServiceKeysToStatusesToTags( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL )
                    
                    for ( service_key, statuses_to_tags ) in service_keys_to_statuses_to_tags.items():
                        
                        statuses_to_tags_json_serialisable = { str( status ) : sorted( tags, key = HydrusTags.ConvertTagToSortable ) for ( status, tags ) in statuses_to_tags.items() if len( tags ) > 0 }
                        
                        if len( statuses_to_tags_json_serialisable ) > 0:
                            
                            api_service_keys_to_statuses_to_tags[ service_key.hex() ] = statuses_to_tags_json_serialisable
                            
                        
                    
                    if not hide_service_keys_tags:
                        
                        metadata_row[ 'service_keys_to_statuses_to_display_tags' ] = api_service_keys_to_statuses_to_tags
                        
                    
                    # old stuff ends here
                    
                    #
                    
                    metadata.append( metadata_row )
                    
                else:
                    
                    AddMissingHashToFileMetadata( metadata, hash )
                    
                
            
        
        body_dict[ 'metadata' ] = metadata
        
        if include_services_object:
            
            body_dict[ 'services' ] = ClientLocalServerCore.GetServicesDict()
            
        
        mime = request.preferred_mime
        body = ClientLocalServerCore.Dumps( body_dict, mime )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = mime, body = body )
        
        return response_context
        
    

class HydrusResourceClientAPIRestrictedGetFilesGetThumbnail( HydrusResourceClientAPIRestrictedGetFiles ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        media_result = ParseAndFetchMediaResult( request )
        
        mime = media_result.GetMime()
        
        if mime in HC.MIMES_WITH_THUMBNAILS:
            
            try:
                
                path = CG.client_controller.client_files_manager.GetThumbnailPath( media_result )
                
                if not os.path.exists( path ):
                    
                    # not _supposed_ to happen, but it seems in odd situations it can
                    raise HydrusExceptions.FileMissingException()
                    
                
            except HydrusExceptions.FileMissingException:
                
                path = HydrusFileHandling.mimes_to_default_thumbnail_paths[ mime ]
                
            
        else:
            
            path = HydrusFileHandling.mimes_to_default_thumbnail_paths[ mime ]
            
        
        response_mime = HydrusFileHandling.GetThumbnailMime( path )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = response_mime, path = path )
        
        return response_context
        
    

class HydrusResourceClientAPIRestrictedGetFilesGetLocalPath( HydrusResourceClientAPIRestrictedGetFilesSearchFiles ):
    
    def _CheckAPIPermissions( self, request: HydrusServerRequest.HydrusRequest ):
        
        request.client_api_permissions.CheckPermission( ClientAPI.CLIENT_API_PERMISSION_SEE_LOCAL_PATHS )
        
        super()._CheckAPIPermissions( request )
        
    

class HydrusResourceClientAPIRestrictedGetFilesGetLocalFileStorageLocations( HydrusResourceClientAPIRestrictedGetFilesGetLocalPath ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        all_subfolders = CG.client_controller.client_files_manager.GetAllSubfolders()
        
        base_locations_to_subfolders = HydrusData.BuildKeyToListDict( [ ( subfolder.base_location, subfolder ) for subfolder in all_subfolders ] )
        
        locations_list = []
        
        for ( base_location, subfolders ) in sorted( base_locations_to_subfolders.items(), key = lambda b_l_s: b_l_s[0].path ):
            
            locations_structure = {
                "path" : base_location.path,
                "ideal_weight" : base_location.ideal_weight,
                "max_num_bytes" : base_location.max_num_bytes,
                "prefixes" : sorted( [ subfolder.prefix for subfolder in subfolders ] )
            }
            
            locations_list.append( locations_structure )
            
        
        body_dict = {
            'locations' : locations_list
        }
        
        mime = request.preferred_mime
        body = ClientLocalServerCore.Dumps( body_dict, mime )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = mime, body = body )
        
        return response_context
        
    

class HydrusResourceClientAPIRestrictedGetFilesGetFilePath( HydrusResourceClientAPIRestrictedGetFilesGetLocalPath ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        media_result = ParseAndFetchMediaResult( request )
        
        if not media_result.GetLocationsManager().IsLocal():
            
            raise HydrusExceptions.FileMissingException( 'The client does not have this file!' )
            
        
        try:
            
            hash = media_result.GetHash()
            mime = media_result.GetMime()
            size = media_result.GetSize()
            
            path = CG.client_controller.client_files_manager.GetFilePath( hash, mime )
            
            if not os.path.exists( path ):
                
                raise HydrusExceptions.FileMissingException()
                
            
        except HydrusExceptions.FileMissingException:
            
            raise HydrusExceptions.NotFoundException( 'That file seems to be missing!' )
            
        
        body_dict = {
            'path' : path,
            'filetype' : HC.mime_mimetype_string_lookup[ mime ],
            'size' : size
        }
        
        mime = request.preferred_mime
        body = ClientLocalServerCore.Dumps( body_dict, mime )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = mime, body = body )
        
        return response_context
        
    

class HydrusResourceClientAPIRestrictedGetFilesGetThumbnailPath( HydrusResourceClientAPIRestrictedGetFilesGetLocalPath ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        include_thumbnail_filetype = request.parsed_request_args.GetValue( 'include_thumbnail_filetype', bool, default_value = False )
        
        media_result = ParseAndFetchMediaResult( request )
        
        mime = media_result.GetMime()
        
        if mime in HC.MIMES_WITH_THUMBNAILS:
            
            try:
                
                path = CG.client_controller.client_files_manager.GetThumbnailPath( media_result )
                
                if not os.path.exists( path ):
                    
                    # not _supposed_ to happen, but it seems in odd situations it can
                    raise HydrusExceptions.FileMissingException()
                    
                
            except HydrusExceptions.FileMissingException:
                
                raise HydrusExceptions.FileMissingException( 'Could not find that thumbnail!' )
                
            
        else:
            
            raise HydrusExceptions.BadRequestException( 'Sorry, this file type does not have a thumbnail!' )
            
        
        if include_thumbnail_filetype:
            
            thumb_mime = HydrusFileHandling.GetThumbnailMime( path )
            
            body_dict = {
                'path' : path,
                'filetype' : HC.mime_mimetype_string_lookup[ thumb_mime ]
            }
            
        else:
            
            body_dict = {
                'path' : path
            }
            
        
        mime = request.preferred_mime
        body = ClientLocalServerCore.Dumps( body_dict, mime )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = mime, body = body )
        
        return response_context
        
    
