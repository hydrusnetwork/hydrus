import collections
import collections.abc
import itertools

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusLists
from hydrus.core import HydrusPaths
from hydrus.core.files.images import HydrusImageHandling

from hydrus.client import ClientApplicationCommand as CAC
from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientLocation
from hydrus.client import ClientPaths
from hydrus.client.media import ClientMedia
from hydrus.client.metadata import ClientContentUpdates
from hydrus.client.search import ClientSearchPredicate

def GetLocalMediaPaths( medias: collections.abc.Collection[ ClientMedia.Media ] ):
    
    medias = ClientMedia.FlattenMedia( medias )
    
    client_files_manager = CG.client_controller.client_files_manager
    
    paths = []
    
    for media in medias:
        
        if not media.GetLocationsManager().IsLocal():
            
            continue
            
        
        hash = media.GetHash()
        mime = media.GetMime()
        
        path = client_files_manager.GetFilePath( hash, mime, check_file_exists = False )
        
        paths.append( path )
        
    
    return paths
    

def CopyFilesToClipboard( medias: collections.abc.Collection[ ClientMedia.Media ] ):
    
    paths = GetLocalMediaPaths( medias )
    
    if len( paths ) > 0:
        
        CG.client_controller.pub( 'clipboard', 'paths', paths )
        
    

def CopyFileIdsToClipboard( medias: collections.abc.Collection[ ClientMedia.Media ] ):
    
    flat_media = ClientMedia.FlattenMedia( medias )
    
    ids = [ media.GetMediaResult().GetHashId() for media in flat_media ]
    
    if len( ids ) > 0:
        
        text = '\n'.join( ( str( id ) for id in ids ) )
        
        CG.client_controller.pub( 'clipboard', 'text', text )
        
    

def CopyFilePathsToClipboard( medias: collections.abc.Collection[ ClientMedia.Media ] ):
    
    paths = GetLocalMediaPaths( medias )
    
    if len( paths ) > 0:
        
        text = '\n'.join( paths )
        
        CG.client_controller.pub( 'clipboard', 'text', text )
        
    

def CopyMediaBitmap( media: ClientMedia.MediaSingleton, bitmap_type: int ):
    
    if bitmap_type == CAC.BITMAP_TYPE_THUMBNAIL:
        
        if media.GetMime() not in HC.MIMES_WITH_THUMBNAILS:
            
            return
            
        
        CG.client_controller.pub( 'clipboard', 'thumbnail_bmp', media )
        
    else:
        
        if not media.GetLocationsManager().IsLocal():
            
            return
            
        
        copied = False
        
        if media.IsStaticImage():
            
            ( width, height ) = media.GetResolution()
            
            if width is not None and height is not None:
                
                if bitmap_type == CAC.BITMAP_TYPE_SOURCE_LOOKUPS and ( width > 1024 or height > 1024 ):
                    
                    target_resolution = HydrusImageHandling.GetThumbnailResolution( media.GetResolution(), ( 1024, 1024 ), HydrusImageHandling.THUMBNAIL_SCALE_TO_FIT, 100 )
                    
                    CG.client_controller.pub( 'clipboard', 'bmp', ( media, target_resolution ) )
                    
                else:
                    
                    CG.client_controller.pub( 'clipboard', 'bmp', ( media, None ) )
                    
                
                copied = True
                
            
        
        if bitmap_type == CAC.BITMAP_TYPE_FULL_OR_FILE and not copied:
            
            CopyFilesToClipboard( [ media ] )
            
        
    

def CopyMediaURLs( medias ):
    
    urls = set()
    
    for media in medias:
        
        media_urls = media.GetLocationsManager().GetURLs()
        
        urls.update( media_urls )
        
    
    urls = sorted( urls )
    
    urls_string = '\n'.join( urls )
    
    CG.client_controller.pub( 'clipboard', 'text', urls_string )
    

def CopyMediaURLClassURLs( medias, url_class ):
    
    urls = set()
    
    for media in medias:
        
        media_urls = media.GetLocationsManager().GetURLs()
        
        for url in media_urls:
            
            # can't do 'url_class.matches', as it will match too many
            if CG.client_controller.network_engine.domain_manager.GetURLClass( url ) == url_class:
                
                urls.add( url )
                
            
        
    
    urls = sorted( urls )
    
    urls_string = '\n'.join( urls )
    
    CG.client_controller.pub( 'clipboard', 'text', urls_string )
    

def CopyServiceFilenamesToClipboard( service_key: bytes, medias: collections.abc.Collection[ ClientMedia.Media ] ):
    
    flat_media = ClientMedia.FlattenMedia( medias )
    
    flat_media = [ m for m in flat_media if service_key in m.GetLocationsManager().GetCurrent() ]
    
    if len( flat_media ) == 0:
        
        HydrusData.ShowText( 'Could not find any files with the requested service!' )
        
        return
        
    
    prefix = ''
    
    service = CG.client_controller.services_manager.GetService( service_key )
    
    if service.GetServiceType() == HC.IPFS:
        
        prefix = service.GetMultihashPrefix()
        
    
    filenames_or_none = [ media.GetLocationsManager().GetServiceFilename( service_key ) for media in flat_media ]
    
    filenames = [ f for f in filenames_or_none if f is not None ]
    
    lines = [ prefix + filename for filename in filenames ]
    
    if len( lines ) > 0:
        
        text = '\n'.join( lines )
        
        CG.client_controller.pub( 'clipboard', 'text', text )
        
    else:
        
        HydrusData.ShowText( 'Could not find any service filenames for that selection!' )
        
    

def GetLocalFileActionServiceKeys( media: collections.abc.Collection[ ClientMedia.MediaSingleton ] ):
    
    local_media_file_service_keys = set( CG.client_controller.services_manager.GetServiceKeys( ( HC.LOCAL_FILE_DOMAIN, ) ) )
    
    local_duplicable_to_file_service_keys = collections.Counter()
    local_moveable_from_and_to_file_service_keys = collections.Counter()
    local_mergable_from_and_to_file_service_keys = collections.Counter()
    
    for m in media:
        
        locations_manager = m.GetLocationsManager()
        
        if CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY not in locations_manager.GetCurrent():
            
            continue
            
        
        current = locations_manager.GetCurrent()
        
        if locations_manager.IsLocal():
            
            can_send_to = local_media_file_service_keys.difference( current )
            can_send_from = local_media_file_service_keys.intersection( current )
            
            if len( can_send_to ) > 0:
                
                local_duplicable_to_file_service_keys.update( can_send_to )
                
                if len( can_send_from ) > 0:
                    
                    local_moveable_from_and_to_file_service_keys.update( list( itertools.product( can_send_from, can_send_to ) ) )
                    
                
            
            if len( can_send_from ) > 0:
                
                local_mergable_from_and_to_file_service_keys.update( [ ( f, t ) for ( f, t ) in itertools.product( can_send_from, local_media_file_service_keys ) if f != t ] )
                
            
        
    
    return ( local_duplicable_to_file_service_keys, local_moveable_from_and_to_file_service_keys, local_mergable_from_and_to_file_service_keys )
    

def OpenExternally( media: ClientMedia.MediaSingleton | None ) -> bool:
    
    if media is None:
        
        return False
        
    
    if not media.GetLocationsManager().IsLocal():
        
        return False
        
    
    hash = media.GetHash()
    mime = media.GetMime()
    
    path = CG.client_controller.client_files_manager.GetFilePath( hash, mime )
    
    launch_path = CG.client_controller.new_options.GetMimeLaunch( mime )
    
    HydrusPaths.LaunchFile( path, launch_path )
    
    return True
    

def OpenFileLocation( media: ClientMedia.MediaSingleton | None ) -> bool:
    
    if media is None:
        
        return False
        
    
    if not media.GetLocationsManager().IsLocal():
        
        return False
        
    
    hash = media.GetHash()
    mime = media.GetMime()
    
    path = CG.client_controller.client_files_manager.GetFilePath( hash, mime )
    
    ClientPaths.OpenFileLocation( path )
    
    return True
    

def OpenInWebBrowser( media: ClientMedia.MediaSingleton | None ) -> bool:
    
    if media is None:
        
        return False
        
    
    if not media.GetLocationsManager().IsLocal():
        
        return False
        
    
    hash = media.GetHash()
    mime = media.GetMime()
    
    path = CG.client_controller.client_files_manager.GetFilePath( hash, mime )
    
    ClientPaths.LaunchPathInWebBrowser( path )
    
    return True
    
def OpenNativeFileProperties( media: ClientMedia.MediaSingleton | None ) -> bool:
    
    if media is None:
        
        return False
        
    
    if not media.GetLocationsManager().IsLocal():
        
        return False
        
    
    hash = media.GetHash()
    mime = media.GetMime()
    
    path = CG.client_controller.client_files_manager.GetFilePath( hash, mime )
    
    ClientPaths.OpenNativeFileProperties( path )
    
    return True


def OpenFileWithDialog( media: ClientMedia.MediaSingleton | None ) -> bool:
    
    if media is None:
        
        return False
        
    
    if not media.GetLocationsManager().IsLocal():
        
        return False
        
    
    hash = media.GetHash()
    mime = media.GetMime()
    
    path = CG.client_controller.client_files_manager.GetFilePath( hash, mime )
    
    ClientPaths.OpenFileWithDialog( path )
    
    return True
    

def ShowDuplicatesInNewPage( location_context: ClientLocation.LocationContext, hash, duplicate_type ):
    
    # TODO: this can be replaced by a call to the MediaResult when it holds these hashes
    # don't forget to return itself in position 0!
    hashes = CG.client_controller.Read( 'file_duplicate_hashes', location_context, hash, duplicate_type )
    
    if hashes is not None and len( hashes ) > 1:
        
        CG.client_controller.pub( 'new_page_query', location_context, initial_hashes = hashes )
        
    else:
        
        location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_FILE_SERVICE_KEY )
        
        hashes = CG.client_controller.Read( 'file_duplicate_hashes', location_context, hash, duplicate_type )
        
        if hashes is not None and len( hashes ) > 1:
            
            HydrusData.ShowText( 'Could not find the members of this group in this location, so searched all known files and found more.' )
            
            CG.client_controller.pub( 'new_page_query', location_context, initial_hashes = hashes )
            
        else:
            
            HydrusData.ShowText( 'Sorry, could not find the members of this group either at the given location or in all known files. There may be a problem here, so let hydev know.' )
            
        
    

def ShowFilesInNewDuplicatesFilterPage( hashes: collections.abc.Collection[ bytes ], location_context: ClientLocation.LocationContext ):
    
    activate_window = CG.client_controller.new_options.GetBoolean( 'activate_window_on_tag_search_page_activation' )
    
    predicates = [ ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HASH, value = ( tuple( hashes ), 'sha256' ) ) ]
    
    page_name = 'duplicates'
    
    CG.client_controller.pub( 'new_page_duplicates', location_context, initial_predicates = predicates, page_name = page_name, activate_window = activate_window )
    

def ShowFilesInNewPage( hashes: collections.abc.Collection[ bytes ], location_context: ClientLocation.LocationContext, media_sort = None, media_collect = None ):
    
    CG.client_controller.pub( 'new_page_query', location_context, initial_hashes = hashes, initial_sort = media_sort, initial_collect = media_collect )
    

def ShowSimilarFilesInNewPage( media: collections.abc.Collection[ ClientMedia.MediaSingleton ], location_context: ClientLocation.LocationContext, max_hamming: int ):
    
    hashes = set()
    
    for m in media:
        
        if m.GetMime() in HC.FILES_THAT_HAVE_PERCEPTUAL_HASH:
            
            hashes.add( m.GetHash() )
            
        
    
    if len( hashes ) > 0:
        
        initial_predicates = [ ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_SIMILAR_TO_FILES, ( tuple( hashes ), max_hamming ) ) ]
        
        CG.client_controller.pub( 'new_page_query', location_context, initial_predicates = initial_predicates )
        
    

def UndeleteFiles( hashes ):
    
    local_file_service_keys = CG.client_controller.services_manager.GetServiceKeys( ( HC.LOCAL_FILE_DOMAIN, ) )
    
    for chunk_of_hashes in HydrusLists.SplitIteratorIntoChunks( hashes, 64 ):
        
        media_results = CG.client_controller.Read( 'media_results', chunk_of_hashes )
        
        service_keys_to_hashes = collections.defaultdict( list )
        
        for media_result in media_results:
            
            locations_manager = media_result.GetLocationsManager()
            
            if CC.TRASH_SERVICE_KEY not in locations_manager.GetCurrent():
                
                continue
                
            
            hash = media_result.GetHash()
            
            for service_key in locations_manager.GetDeleted().intersection( local_file_service_keys ):
                
                service_keys_to_hashes[ service_key ].append( hash )
                
            
        
        for ( service_key, service_hashes ) in service_keys_to_hashes.items():
            
            content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_UNDELETE, service_hashes )
            
            content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( service_key, content_update )
            
            CG.client_controller.WriteSynchronous( 'content_updates', content_update_package )
            
        
    
