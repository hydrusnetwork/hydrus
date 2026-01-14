import warnings

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusText
from hydrus.core import HydrusTime
from hydrus.core.files.images import HydrusImageHandling

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.media import ClientMediaResult
from hydrus.client.metadata import ClientTags

def AddMissingHashToFileMetadata( metadata_list: list[ dict ], hash: bytes ):
    
    metadata_row = {
        'file_id' : None,
        'hash' : hash.hex()
    }
    
    metadata_list.append( metadata_row )
    

def GetMediaResultAPIDict( media_result: ClientMediaResult.MediaResult ):
    
    metadata_list = []
    hashes_to_media_results = { media_result.GetHash() : media_result }
    hashes = list( hashes_to_media_results.keys() )
    
    PopulateMetadataAPIDict( metadata_list, hashes, hashes_to_media_results )
    
    metadata_dict = metadata_list[0]
    
    return metadata_dict
    

def PopulateMetadataAPIDict( metadata_list: list[ dict ], hashes: list[ bytes ], hashes_to_media_results: dict[ bytes, ClientMediaResult.MediaResult ], hide_service_keys_tags = True, detailed_url_information = True, include_notes = True, include_milliseconds = True ):
    
    if not hide_service_keys_tags:
        
        warnings.warn(
            'Hey, the hide_service_keys_tags parameter is deprecated, but a Client API script you are using it just relied on it! That script may stop working in v668 if it is not updated to use the newer "tags" structure!',
            FutureWarning,
            stacklevel = 2
        )
        
    
    if include_milliseconds:
        
        time_converter = HydrusTime.SecondiseMSFloat
        
    else:
        
        time_converter = HydrusTime.SecondiseMS
        
    
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
                
            
            metadata_dict = {
                'file_id' : file_info_manager.hash_id,
                'hash' : file_info_manager.hash.hex(),
                'size' : file_info_manager.size,
                'mime' : HC.mime_mimetype_string_lookup[ mime ],
                'filetype_human' : HC.mime_string_lookup[ file_info_manager.mime ],
                'filetype_enum' : file_info_manager.mime,
                'ext' : HC.mime_ext_lookup[ mime ],
                'width' : width,
                'height' : height,
                'duration' : file_info_manager.duration_ms,
                'num_frames' : file_info_manager.num_frames,
                'num_words' : file_info_manager.num_words,
                'has_audio' : file_info_manager.has_audio,
                'blurhash' : file_info_manager.blurhash,
                'pixel_hash' : pixel_hash_encoded
            }
            
            filetype_forced = file_info_manager.FiletypeIsForced()
            
            metadata_dict[ 'filetype_forced' ] = filetype_forced
            
            if filetype_forced:
                
                metadata_dict[ 'original_mime' ] = HC.mime_mimetype_string_lookup[ file_info_manager.original_mime ]
                
            
            if file_info_manager.mime in HC.MIMES_WITH_THUMBNAILS:
                
                if width is not None and height is not None and width > 0 and height > 0:
                    
                    ( expected_thumbnail_width, expected_thumbnail_height ) = HydrusImageHandling.GetThumbnailResolution( ( width, height ), thumbnail_bounding_dimensions, thumbnail_scale_type, thumbnail_dpr_percent )
                    
                    metadata_dict[ 'thumbnail_width' ] = expected_thumbnail_width
                    metadata_dict[ 'thumbnail_height' ] = expected_thumbnail_height
                    
                
            
            if include_notes:
                
                metadata_dict[ 'notes' ] = media_result.GetNotesManager().GetNamesToNotes()
                
            
            locations_manager = media_result.GetLocationsManager()
            
            metadata_dict[ 'file_services' ] = {
                'current' : {},
                'deleted' : {}
            }
            
            times_manager = locations_manager.GetTimesManager()
            
            current = locations_manager.GetCurrent()
            
            for file_service_key in current:
                
                metadata_dict[ 'file_services' ][ 'current' ][ file_service_key.hex() ] = {
                    'name' : service_keys_to_names[ file_service_key ],
                    'type' : service_keys_to_types[ file_service_key ],
                    'type_pretty' : HC.service_string_lookup[ service_keys_to_types[ file_service_key ] ],
                    'time_imported' : time_converter( times_manager.GetImportedTimestampMS( file_service_key ) )
                }
                
            
            deleted = locations_manager.GetDeleted()
            
            for file_service_key in deleted:
                
                metadata_dict[ 'file_services' ][ 'deleted' ][ file_service_key.hex() ] = {
                    'name' : service_keys_to_names[ file_service_key ],
                    'type' : service_keys_to_types[ file_service_key ],
                    'type_pretty' : HC.service_string_lookup[ service_keys_to_types[ file_service_key ] ],
                    'time_deleted' : time_converter( times_manager.GetDeletedTimestampMS( file_service_key ) ),
                    'time_imported' : time_converter( times_manager.GetPreviouslyImportedTimestampMS( file_service_key ) )
                }
                
            
            metadata_dict[ 'time_modified' ] = time_converter( times_manager.GetAggregateModifiedTimestampMS() )
            
            domains_to_file_modified_timestamps_ms = times_manager.GetDomainModifiedTimestampsMS()
            
            local_modified_timestamp_ms = times_manager.GetFileModifiedTimestampMS()
            
            if local_modified_timestamp_ms is not None:
                
                domains_to_file_modified_timestamps_ms[ 'local' ] = local_modified_timestamp_ms
                
            
            metadata_dict[ 'time_modified_details' ] = { domain : time_converter( timestamp_ms ) for ( domain, timestamp_ms ) in domains_to_file_modified_timestamps_ms.items() }
            
            metadata_dict[ 'is_inbox' ] = locations_manager.inbox
            metadata_dict[ 'is_local' ] = locations_manager.IsLocal()
            metadata_dict[ 'is_trashed' ] = locations_manager.IsTrashed()
            metadata_dict[ 'is_deleted' ] = CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY in locations_manager.GetDeleted() or locations_manager.IsTrashed()
            
            metadata_dict[ 'has_transparency' ] = file_info_manager.has_transparency
            metadata_dict[ 'has_exif' ] = file_info_manager.has_exif
            metadata_dict[ 'has_human_readable_embedded_metadata' ] = file_info_manager.has_human_readable_embedded_metadata
            metadata_dict[ 'has_icc_profile' ] = file_info_manager.has_icc_profile
            
            known_urls = sorted( locations_manager.GetURLs() )
            
            metadata_dict[ 'known_urls' ] = known_urls
            
            metadata_dict[ 'ipfs_multihashes' ] = { ipfs_service_key.hex() : multihash for ( ipfs_service_key, multihash ) in locations_manager.GetServiceFilenames().items() if ipfs_service_key in ipfs_service_keys }
            
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
                    
                
                metadata_dict[ 'detailed_known_urls' ] = detailed_known_urls
                
            
            ratings_manager = media_result.GetRatingsManager()
            
            ratings_dict = {}
            
            for rating_service_key in rating_service_keys:
                
                rating_object = ratings_manager.GetRatingForAPI( rating_service_key )
                
                ratings_dict[ rating_service_key.hex() ] = rating_object
                
            
            metadata_dict[ 'ratings' ] = ratings_dict
            
            tags_manager = media_result.GetTagsManager()
            
            tags_dict = {}
            
            for tag_service_key in tag_service_keys:
                
                storage_statuses_to_tags = tags_manager.GetStatusesToTags( tag_service_key, ClientTags.TAG_DISPLAY_STORAGE )
                
                storage_tags_json_serialisable = { str( status ) : sorted( tags, key = HydrusText.HumanTextSortKey ) for ( status, tags ) in storage_statuses_to_tags.items() if len( tags ) > 0 }
                
                display_statuses_to_tags = tags_manager.GetStatusesToTags( tag_service_key, ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL )
                
                display_tags_json_serialisable = { str( status ) : sorted( tags, key = HydrusText.HumanTextSortKey ) for ( status, tags ) in display_statuses_to_tags.items() if len( tags ) > 0 }
                
                tags_dict_object = {
                    'name' : service_keys_to_names[ tag_service_key ],
                    'type' : service_keys_to_types[ tag_service_key ],
                    'type_pretty' : HC.service_string_lookup[ service_keys_to_types[ tag_service_key ] ],
                    'storage_tags' : storage_tags_json_serialisable,
                    'display_tags' : display_tags_json_serialisable
                }
                
                tags_dict[ tag_service_key.hex() ] = tags_dict_object
                
            
            metadata_dict[ 'tags' ] = tags_dict
            
            #
            
            file_viewing_stats_list = []
            
            fvsm = media_result.GetFileViewingStatsManager()
            
            for canvas_type in [
                CC.CANVAS_MEDIA_VIEWER,
                CC.CANVAS_PREVIEW,
                CC.CANVAS_CLIENT_API
            ]:
                
                views = fvsm.GetViews( canvas_type )
                viewtime = HydrusTime.SecondiseMSFloat( fvsm.GetViewtimeMS( canvas_type ) )
                last_viewed_timestamp = HydrusTime.SecondiseMSFloat( times_manager.GetLastViewedTimestampMS( canvas_type ) )
                
                json_object = {
                    'canvas_type' : canvas_type,
                    'canvas_type_pretty' : CC.canvas_type_str_lookup[ canvas_type ],
                    'views' : views,
                    'viewtime' : viewtime,
                    'last_viewed_timestamp' : last_viewed_timestamp
                }
                
                file_viewing_stats_list.append( json_object )
                
            
            metadata_dict[ 'file_viewing_statistics' ] = file_viewing_stats_list
            
            # Old stuff starts here
            
            api_service_keys_to_statuses_to_tags = {}
            
            service_keys_to_statuses_to_tags = tags_manager.GetServiceKeysToStatusesToTags( ClientTags.TAG_DISPLAY_STORAGE )
            
            for ( service_key, statuses_to_tags ) in service_keys_to_statuses_to_tags.items():
                
                statuses_to_tags_json_serialisable = { str( status ) : sorted( tags, key = HydrusText.HumanTextSortKey ) for ( status, tags ) in statuses_to_tags.items() if len( tags ) > 0 }
                
                if len( statuses_to_tags_json_serialisable ) > 0:
                    
                    api_service_keys_to_statuses_to_tags[ service_key.hex() ] = statuses_to_tags_json_serialisable
                    
                
            
            if not hide_service_keys_tags:
                
                metadata_dict[ 'service_keys_to_statuses_to_tags' ] = api_service_keys_to_statuses_to_tags
                
            
            #
            
            api_service_keys_to_statuses_to_tags = {}
            
            service_keys_to_statuses_to_tags = tags_manager.GetServiceKeysToStatusesToTags( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL )
            
            for ( service_key, statuses_to_tags ) in service_keys_to_statuses_to_tags.items():
                
                statuses_to_tags_json_serialisable = { str( status ) : sorted( tags, key = HydrusText.HumanTextSortKey ) for ( status, tags ) in statuses_to_tags.items() if len( tags ) > 0 }
                
                if len( statuses_to_tags_json_serialisable ) > 0:
                    
                    api_service_keys_to_statuses_to_tags[ service_key.hex() ] = statuses_to_tags_json_serialisable
                    
                
            
            if not hide_service_keys_tags:
                
                metadata_dict[ 'service_keys_to_statuses_to_display_tags' ] = api_service_keys_to_statuses_to_tags
                
            
            # old stuff ends here
            
            #
            
            metadata_list.append( metadata_dict )
            
        else:
            
            AddMissingHashToFileMetadata( metadata_list, hash )
            
        
    
