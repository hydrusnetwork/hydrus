import random

from hydrus.core import HydrusData
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusLists
from hydrus.core import HydrusSerialisable
from hydrus.core.files.images import HydrusBlurhash

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientLocation
from hydrus.client.metadata import ClientTags
from hydrus.client.search import ClientSearchTagContext

sort_data_to_blurhash_to_sortable_calls = {
    CC.SORT_FILES_BY_AVERAGE_COLOUR_LIGHTNESS : HydrusBlurhash.ConvertBlurhashToSortableLightness,
    CC.SORT_FILES_BY_AVERAGE_COLOUR_CHROMATIC_MAGNITUDE : HydrusBlurhash.ConvertBlurhashToSortableChromaticMagnitude,
    CC.SORT_FILES_BY_AVERAGE_COLOUR_CHROMATICITY_GREEN_RED : HydrusBlurhash.ConvertBlurhashToSortableGreenRed,
    CC.SORT_FILES_BY_AVERAGE_COLOUR_CHROMATICITY_BLUE_YELLOW : HydrusBlurhash.ConvertBlurhashToSortableBlueYellow,
    CC.SORT_FILES_BY_AVERAGE_COLOUR_HUE : HydrusBlurhash.ConvertBlurhashToSortableHue
}

def GetBlurhashToSortableCall( sort_data: int ):
    
    return sort_data_to_blurhash_to_sortable_calls.get( sort_data, HydrusBlurhash.ConvertBlurhashToSortableLightness )
    

class MediaSort( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_MEDIA_SORT
    SERIALISABLE_NAME = 'Media Sort'
    SERIALISABLE_VERSION = 3
    
    def __init__( self, sort_type = None, sort_order = None, tag_context = None ):
        
        if sort_type is None:
            
            sort_type = ( 'system', CC.SORT_FILES_BY_FILESIZE )
            
        
        if sort_order is None:
            
            sort_order = CC.SORT_ASC
            
        
        if tag_context is None:
            
            tag_context = ClientSearchTagContext.TagContext( service_key = CC.COMBINED_TAG_SERVICE_KEY )
            
        
        ( sort_metatype, sort_data ) = sort_type
        
        if sort_metatype == 'namespaces':
            
            ( namespaces, tag_display_type ) = sort_data
            
            sort_data = ( tuple( namespaces ), tag_display_type )
            
            sort_type = ( sort_metatype, sort_data )
            
        
        self.sort_type = sort_type
        self.sort_order = sort_order
        self.tag_context = tag_context
        
    
    def __eq__( self, other ):
        
        if isinstance( other, MediaSort ):
            
            return self.__hash__() == other.__hash__()
            
        
        return NotImplemented
        
    
    def __hash__( self ):
        
        return ( self.sort_type, self.sort_order, self.tag_context ).__hash__()
        
    
    def _GetSerialisableInfo( self ):
        
        ( sort_metatype, sort_data ) = self.sort_type
        
        if sort_metatype == 'system':
            
            serialisable_sort_data = sort_data
            
        elif sort_metatype == 'namespaces':
            
            serialisable_sort_data = sort_data
            
        elif sort_metatype == 'rating':
            
            service_key = sort_data
            
            serialisable_sort_data = service_key.hex()
            
        
        serialisable_tag_context = self.tag_context.GetSerialisableTuple()
        
        return ( sort_metatype, serialisable_sort_data, self.sort_order, serialisable_tag_context )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( sort_metatype, serialisable_sort_data, self.sort_order, serialisable_tag_context ) = serialisable_info
        
        if sort_metatype == 'system':
            
            sort_data = serialisable_sort_data
            
        elif sort_metatype == 'namespaces':
            
            ( namespaces, tag_display_type ) = serialisable_sort_data
            
            sort_data = ( tuple( namespaces ), tag_display_type )
            
        elif sort_metatype == 'rating':
            
            sort_data = bytes.fromhex( serialisable_sort_data )
            
        
        self.sort_type = ( sort_metatype, sort_data )
        
        self.tag_context = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_tag_context )
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( sort_metatype, serialisable_sort_data, sort_order ) = old_serialisable_info
            
            if sort_metatype == 'namespaces':
                
                namespaces = serialisable_sort_data
                serialisable_sort_data = ( namespaces, ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL )
                
            
            new_serialisable_info = ( sort_metatype, serialisable_sort_data, sort_order )
            
            return ( 2, new_serialisable_info )
            
        
        if version == 2:
            
            ( sort_metatype, serialisable_sort_data, sort_order ) = old_serialisable_info
            
            tag_context = ClientSearchTagContext.TagContext( service_key = CC.COMBINED_TAG_SERVICE_KEY )
            
            serialisable_tag_context = tag_context.GetSerialisableTuple()
            
            new_serialisable_info = ( sort_metatype, serialisable_sort_data, sort_order, serialisable_tag_context )
            
            return ( 3, new_serialisable_info )
            
        
    
    def CanAsc( self ):
        
        ( sort_metatype, sort_data ) = self.sort_type
        
        if sort_metatype == 'system':
            
            if sort_data in ( CC.SORT_FILES_BY_MIME, CC.SORT_FILES_BY_RANDOM ):
                
                return False
                
            
        
        return True
        
    
    def CanSortAtDBLevel( self, location_context: ClientLocation.LocationContext ) -> bool:
        
        if location_context.IsAllKnownFiles():
            
            return False
            
        
        ( sort_metadata, sort_data ) = self.sort_type
        
        if sort_metadata == 'system':
            
            return sort_data in {
                CC.SORT_FILES_BY_IMPORT_TIME,
                CC.SORT_FILES_BY_FILESIZE,
                CC.SORT_FILES_BY_DURATION,
                CC.SORT_FILES_BY_FRAMERATE,
                CC.SORT_FILES_BY_NUM_FRAMES,
                CC.SORT_FILES_BY_WIDTH,
                CC.SORT_FILES_BY_HEIGHT,
                CC.SORT_FILES_BY_RATIO,
                CC.SORT_FILES_BY_NUM_PIXELS,
                CC.SORT_FILES_BY_MEDIA_VIEWS,
                CC.SORT_FILES_BY_MEDIA_VIEWTIME,
                CC.SORT_FILES_BY_APPROX_BITRATE,
                CC.SORT_FILES_BY_FILE_MODIFIED_TIMESTAMP,
                CC.SORT_FILES_BY_LAST_VIEWED_TIME,
                CC.SORT_FILES_BY_ARCHIVED_TIMESTAMP,
                CC.SORT_FILES_BY_RANDOM,
                CC.SORT_FILES_BY_HASH,
                CC.SORT_FILES_BY_PIXEL_HASH,
                CC.SORT_FILES_BY_BLURHASH,
                CC.SORT_FILES_BY_AVERAGE_COLOUR_LIGHTNESS,
                CC.SORT_FILES_BY_AVERAGE_COLOUR_CHROMATIC_MAGNITUDE,
                CC.SORT_FILES_BY_AVERAGE_COLOUR_CHROMATICITY_GREEN_RED,
                CC.SORT_FILES_BY_AVERAGE_COLOUR_CHROMATICITY_BLUE_YELLOW,
                CC.SORT_FILES_BY_AVERAGE_COLOUR_HUE
            }
            
        
        return False
        
    
    def GetNamespaces( self ):
        
        ( sort_metadata, sort_data ) = self.sort_type
        
        if sort_metadata == 'namespaces':
            
            ( namespaces, tag_display_type ) = sort_data
            
            return list( namespaces )
            
        else:
            
            return []
            
        
    
    def GetSortKeyAndReverse( self, location_context: ClientLocation.LocationContext ):
        
        ( sort_metadata, sort_data ) = self.sort_type
        
        def deal_with_none( x ):
            
            if x is None: return -1
            else: return x
            
        
        reverse = self.sort_order == CC.SORT_DESC
        
        if sort_metadata == 'system':
            
            if sort_data == CC.SORT_FILES_BY_RANDOM:
                
                def sort_key( x ):
                    
                    return random.random()
                    
                
            elif sort_data == CC.SORT_FILES_BY_HASH:
                
                def sort_key( x ):
                    
                    return x.GetHash().hex()
                    
                
            elif sort_data == CC.SORT_FILES_BY_PIXEL_HASH:
                
                def sort_key( x ):
                    
                    display_media_result = x.GetDisplayMediaResult()
                    
                    if display_media_result is None:
                        
                        return ( 0 if reverse else 1, b'\xff' * 32 )
                        
                    
                    pixel_hash = display_media_result.GetFileInfoManager().pixel_hash
                    
                    if pixel_hash is None:
                        
                        return ( 0 if reverse else 1, b'\xff' * 32 )
                        
                    else:
                        
                        return ( 1 if reverse else 0, pixel_hash )
                        
                    
                
            elif sort_data == CC.SORT_FILES_BY_BLURHASH:
                
                def sort_key( x ):
                    
                    display_media_result = x.GetDisplayMediaResult()
                    
                    if display_media_result is None:
                        
                        return ( 0 if reverse else 1, '' )
                        
                    
                    blurhash = display_media_result.GetFileInfoManager().blurhash
                    
                    if blurhash is None:
                        
                        return ( 0 if reverse else 1, '' )
                        
                    else:
                        
                        return ( 1 if reverse else 0, blurhash )
                        
                    
                
            elif sort_data in CC.AVERAGE_COLOUR_FILE_SORTS:
                
                blurhash_converter = GetBlurhashToSortableCall( sort_data )
                
                def sort_key( x ):
                    
                    display_media_result = x.GetDisplayMediaResult()
                    
                    if display_media_result is None:
                        
                        return ( 0 if reverse else 1, '' )
                        
                    
                    blurhash = display_media_result.GetFileInfoManager().blurhash
                    
                    if blurhash is None:
                        
                        return ( 0 if reverse else 1, '' )
                        
                    else:
                        
                        return ( 1 if reverse else 0, blurhash_converter( blurhash, reverse ) )
                        
                    
                
            elif sort_data == CC.SORT_FILES_BY_APPROX_BITRATE:
                
                def sort_key( x ):
                    
                    # videos > images > pdfs
                    # heavy vids first, heavy images first
                    
                    duration_ms = x.GetDurationMS()
                    num_frames = x.GetNumFrames()
                    size = x.GetSize()
                    resolution = x.GetResolution()
                    
                    if duration_ms is None or duration_ms == 0:
                        
                        if size is None or size == 0:
                            
                            duration_bitrate = -1
                            frame_bitrate = -1
                            
                        else:
                            
                            duration_bitrate = 0
                            
                            if resolution is None:
                                
                                frame_bitrate = 0
                                
                            else:
                                
                                ( width, height ) = x.GetResolution()
                                
                                if size is None or size == 0 or not x.HasUsefulResolution():
                                    
                                    frame_bitrate = -1
                                    
                                else:
                                    
                                    num_pixels = width * height
                                    
                                    frame_bitrate = size / num_pixels
                                    
                                
                            
                        
                    else:
                        
                        if size is None or size == 0:
                            
                            duration_bitrate = -1
                            frame_bitrate = -1
                            
                        else:
                            
                            duration_bitrate = size / duration_ms
                            
                            if num_frames is None or num_frames == 0:
                                
                                frame_bitrate = 0
                                
                            else:
                                
                                frame_bitrate = duration_bitrate / num_frames
                                
                            
                        
                    
                    return ( duration_bitrate, frame_bitrate )
                    
                
            elif sort_data == CC.SORT_FILES_BY_FILESIZE:
                
                def sort_key( x ):
                    
                    return deal_with_none( x.GetSize() )
                    
                
            elif sort_data == CC.SORT_FILES_BY_DURATION:
                
                def sort_key( x ):
                    
                    return deal_with_none( x.GetDurationMS() )
                    
                
            elif sort_data == CC.SORT_FILES_BY_FRAMERATE:
                
                def sort_key( x ):
                    
                    framerate = x.GetFramerate()
                    
                    if framerate is None:
                        
                        return -1
                        
                    else:
                        
                        return framerate
                        
                    
                
            elif sort_data == CC.SORT_FILES_BY_NUM_COLLECTION_FILES:
                
                def sort_key( x ):
                    
                    return ( x.GetNumFiles(), x.IsCollection() )
                    
                
            elif sort_data == CC.SORT_FILES_BY_NUM_FRAMES:
                
                def sort_key( x ):
                    
                    return deal_with_none( x.GetNumFrames() )
                    
                
            elif sort_data == CC.SORT_FILES_BY_HAS_AUDIO:
                
                def sort_key( x ):
                    
                    return - deal_with_none( x.HasAudio() )
                    
                
            elif sort_data == CC.SORT_FILES_BY_IMPORT_TIME:
                
                def sort_key( x ):
                    
                    # note we use hash_id here, thanks to a user for pointing it out, as a nice way to break 1-second-resolution ties
                    
                    return ( deal_with_none( x.GetLocationsManager().GetBestCurrentTimestamp( location_context ) ), x.GetEarliestHashId() )
                    
                
            elif sort_data == CC.SORT_FILES_BY_FILE_MODIFIED_TIMESTAMP:
                
                def sort_key( x ):
                    
                    return deal_with_none( x.GetLocationsManager().GetTimesManager().GetAggregateModifiedTimestampMS() )
                    
                
            elif sort_data == CC.SORT_FILES_BY_LAST_VIEWED_TIME:
                
                def sort_key( x ):
                    
                    times_manager = x.GetFileViewingStatsManager().GetTimesManager()
                    
                    # do not do viewtime as a secondary sort here, to allow for user secondary sort to help out
                    
                    return deal_with_none( times_manager.GetLastViewedTimestampMS( CC.CANVAS_MEDIA_VIEWER ) )
                    
                
            elif sort_data == CC.SORT_FILES_BY_ARCHIVED_TIMESTAMP:
                
                def sort_key( x ):
                    
                    locations_manager = x.GetLocationsManager()
                    
                    return ( not locations_manager.inbox, deal_with_none( x.GetLocationsManager().GetTimesManager().GetArchivedTimestampMS() ) )
                    
                
            elif sort_data == CC.SORT_FILES_BY_HEIGHT:
                
                def sort_key( x ):
                    
                    return deal_with_none( x.GetResolution()[1] )
                    
                
            elif sort_data == CC.SORT_FILES_BY_WIDTH:
                
                def sort_key( x ):
                    
                    return deal_with_none( x.GetResolution()[0] )
                    
                
            elif sort_data == CC.SORT_FILES_BY_RATIO:
                
                def sort_key( x ):
                    
                    ( width, height ) = x.GetResolution()
                    
                    if not x.HasUsefulResolution():
                        
                        return -1
                        
                    else:
                        
                        return width / height
                        
                    
                
            elif sort_data == CC.SORT_FILES_BY_NUM_PIXELS:
                
                def sort_key( x ):
                    
                    ( width, height ) = x.GetResolution()
                    
                    if width is None or height is None:
                        
                        return -1
                        
                    else:
                        
                        return width * height
                        
                    
                
            elif sort_data == CC.SORT_FILES_BY_NUM_TAGS:
                
                def sort_key( x ):
                    
                    tags_manager = x.GetTagsManager()
                    
                    # this is self.tag_context, not the given tag context
                    
                    return len( tags_manager.GetCurrentAndPending( self.tag_context.service_key, ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL ) )
                    
                
            elif sort_data == CC.SORT_FILES_BY_MIME:
                
                def sort_key( x ):
                    
                    return x.GetMime()
                    
                
            elif sort_data in ( CC.SORT_FILES_BY_MEDIA_VIEWS, CC.SORT_FILES_BY_MEDIA_VIEWTIME ):
                
                desired_canvas_types = CG.client_controller.new_options.GetIntegerList( 'file_viewing_stats_interesting_canvas_types' )
                
                if sort_data == CC.SORT_FILES_BY_MEDIA_VIEWS:
                    
                    def sort_key( x ):
                        
                        fvsm = x.GetFileViewingStatsManager()
                        
                        # do not do viewtime as a secondary sort here, to allow for user secondary sort to help out
                        
                        return sum( fvsm.GetViews( canvas_type ) for canvas_type in desired_canvas_types )
                        
                    
                else:
                    
                    def sort_key( x ):
                        
                        fvsm = x.GetFileViewingStatsManager()
                        
                        # do not do views as a secondary sort here, to allow for user secondary sort to help out
                        
                        return sum( fvsm.GetViewtimeMS( canvas_type ) for canvas_type in desired_canvas_types )
                        
                    
                
            
        elif sort_metadata == 'namespaces':
            
            ( namespaces, tag_display_type ) = sort_data
            
            def sort_key( x ):
                
                x_tags_manager = x.GetTagsManager()
                
                return [ x_tags_manager.GetComparableNamespaceSlice( self.tag_context.service_key, ( namespace, ), tag_display_type ) for namespace in namespaces ]
                
            
        elif sort_metadata == 'rating':
            
            service_key = sort_data
            
            def sort_key( x ):
                
                x_ratings_manager = x.GetRatingsManager()
                
                rating = deal_with_none( x_ratings_manager.GetRating( service_key ) )
                
                return rating
                
            
        
        return ( sort_key, reverse )
        
    
    def GetSortOrderStrings( self ):
        
        ( sort_metatype, sort_data ) = self.sort_type
        
        if sort_metatype == 'system':
            
            sort_string_lookup = {}
            
            sort_string_lookup[ CC.SORT_FILES_BY_APPROX_BITRATE ] = ( 'smallest first', 'largest first', CC.SORT_DESC )
            sort_string_lookup[ CC.SORT_FILES_BY_FILESIZE ] = ( 'smallest first', 'largest first', CC.SORT_DESC )
            sort_string_lookup[ CC.SORT_FILES_BY_DURATION ] = ( 'shortest first', 'longest first', CC.SORT_DESC )
            sort_string_lookup[ CC.SORT_FILES_BY_FRAMERATE ] = ( 'slowest first', 'fastest first', CC.SORT_DESC )
            sort_string_lookup[ CC.SORT_FILES_BY_NUM_COLLECTION_FILES ] = ( 'fewest first', 'most first', CC.SORT_DESC )
            sort_string_lookup[ CC.SORT_FILES_BY_NUM_FRAMES ] = ( 'smallest first', 'largest first', CC.SORT_DESC )
            sort_string_lookup[ CC.SORT_FILES_BY_HAS_AUDIO ] = ( 'audio first', 'silent first', CC.SORT_ASC )
            sort_string_lookup[ CC.SORT_FILES_BY_IMPORT_TIME ] = ( 'oldest first', 'newest first', CC.SORT_DESC )
            sort_string_lookup[ CC.SORT_FILES_BY_FILE_MODIFIED_TIMESTAMP ] = ( 'oldest first', 'newest first', CC.SORT_DESC )
            sort_string_lookup[ CC.SORT_FILES_BY_LAST_VIEWED_TIME ] = ( 'oldest first', 'newest first', CC.SORT_DESC )
            sort_string_lookup[ CC.SORT_FILES_BY_ARCHIVED_TIMESTAMP ] = ( 'oldest first', 'newest first', CC.SORT_DESC )
            sort_string_lookup[ CC.SORT_FILES_BY_MIME ] = ( 'filetype', 'filetype', CC.SORT_ASC )
            sort_string_lookup[ CC.SORT_FILES_BY_RANDOM ] = ( 'random', 'random', CC.SORT_ASC )
            sort_string_lookup[ CC.SORT_FILES_BY_PIXEL_HASH ] = ( 'lexicographic', 'reverse lexicographic', CC.SORT_ASC )
            sort_string_lookup[ CC.SORT_FILES_BY_HASH ] = ( 'lexicographic', 'reverse lexicographic', CC.SORT_ASC )
            sort_string_lookup[ CC.SORT_FILES_BY_BLURHASH ] = ( 'lexicographic', 'reverse lexicographic', CC.SORT_ASC )
            sort_string_lookup[ CC.SORT_FILES_BY_AVERAGE_COLOUR_LIGHTNESS ] = ( 'darkest first', 'lightest first', CC.SORT_DESC )
            sort_string_lookup[ CC.SORT_FILES_BY_AVERAGE_COLOUR_CHROMATIC_MAGNITUDE ] = ( 'greys first', 'colours first', CC.SORT_DESC )
            sort_string_lookup[ CC.SORT_FILES_BY_AVERAGE_COLOUR_CHROMATICITY_GREEN_RED ] = ( 'greens first', 'reds first', CC.SORT_ASC )
            sort_string_lookup[ CC.SORT_FILES_BY_AVERAGE_COLOUR_CHROMATICITY_BLUE_YELLOW ] = ( 'blues first', 'yellows first', CC.SORT_ASC )
            sort_string_lookup[ CC.SORT_FILES_BY_AVERAGE_COLOUR_HUE ] = ( 'rainbow - red first', 'rainbow - purple first', CC.SORT_ASC )
            sort_string_lookup[ CC.SORT_FILES_BY_WIDTH ] = ( 'slimmest first', 'widest first', CC.SORT_ASC )
            sort_string_lookup[ CC.SORT_FILES_BY_HEIGHT ] = ( 'shortest first', 'tallest first', CC.SORT_ASC )
            sort_string_lookup[ CC.SORT_FILES_BY_RATIO ] = ( 'tallest first', 'widest first', CC.SORT_ASC )
            sort_string_lookup[ CC.SORT_FILES_BY_NUM_PIXELS ] = ( 'ascending', 'descending', CC.SORT_DESC )
            sort_string_lookup[ CC.SORT_FILES_BY_NUM_TAGS ] = ( 'ascending', 'descending', CC.SORT_ASC )
            sort_string_lookup[ CC.SORT_FILES_BY_MEDIA_VIEWS ] = ( 'ascending', 'descending', CC.SORT_DESC )
            sort_string_lookup[ CC.SORT_FILES_BY_MEDIA_VIEWTIME ] = ( 'ascending', 'descending', CC.SORT_DESC )
            
            return sort_string_lookup[ sort_data ]
            
        elif sort_metatype == 'namespaces':
            
            return ( 'a-z', 'z-a', CC.SORT_ASC )
            
        else:
            
            return ( 'ascending', 'descending', CC.SORT_DESC )
            
        
    
    def GetSortTypeString( self ):
        
        ( sort_metatype, sort_data ) = self.sort_type
        
        sort_string = 'sort by '
        
        if sort_metatype == 'system':
            
            sort_string += CC.sort_type_string_lookup[ sort_data ]
            
        elif sort_metatype == 'namespaces':
            
            ( namespaces, tag_display_type ) = sort_data
            
            sort_string += 'tags: ' + '-'.join( namespaces )
            
        elif sort_metatype == 'rating':
            
            service_key = sort_data
            
            name = CG.client_controller.services_manager.GetNameSafe( service_key )
            
            sort_string += 'rating: {}'.format( name )
            
        
        return sort_string
        
    
    def Sort( self, location_context: ClientLocation.LocationContext, tag_context: ClientSearchTagContext.TagContext, media_results_list: HydrusLists.FastIndexUniqueList ):
        
        # the tag context here is that of the page overall. I removed it from GetSortKeyAndReverse when I started sucking it from the media sort here for num_tags, but maybe in future we'll want some
        # sophisticated logic somewhere that soys 'use the page' instead of what the sort has. so don't remove it too aggressively m8
        
        ( sort_metadata, sort_data ) = self.sort_type
        
        if sort_data == CC.SORT_FILES_BY_RANDOM:
            
            media_results_list.random_sort()
            
        else:
            
            ( sort_key, reverse ) = self.GetSortKeyAndReverse( location_context )
            
            media_results_list.sort( key = sort_key, reverse = reverse )
            
            if HG.file_sort_report_mode:
                
                HydrusData.ShowText( f'Sort occurred according to {self.ToString()}' )
                
                for mr in media_results_list:
                    
                    HydrusData.ShowText( ( mr.GetHash().hex(), sort_key( mr ) ) )
                    
                
            
        
    
    def ToString( self ):
        
        sort_type_string = self.GetSortTypeString()
        
        ( asc_string, desc_string, sort_gumpf ) = self.GetSortOrderStrings()
        
        sort_order_string = asc_string if self.sort_order == CC.SORT_ASC else desc_string
        
        return '{}, {}'.format( sort_type_string, sort_order_string )
        
    
    def ToDictForAPI( self ):

        ( sort_metatype, sort_data ) = self.sort_type

        data = {
            'sort_metatype' : sort_metatype,
            'sort_order' : self.sort_order,
            'tag_context': self.tag_context.ToDictForAPI(),
        }

        if sort_metatype == 'system':
            
            data[ 'sort_type' ] = sort_data
            
        elif sort_metatype == 'namespaces':
            
            (namespaces, tag_display_type) = sort_data

            data[ 'namespaces' ] = self.GetNamespaces()
            data[ 'tag_display_type' ] = tag_display_type
            
        elif sort_metatype == 'rating':
            
            service_key = sort_data
            
            data[ 'service_key' ] = service_key.hex()
        
        return data
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_MEDIA_SORT ] = MediaSort
