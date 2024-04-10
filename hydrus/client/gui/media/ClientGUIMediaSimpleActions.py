import collections
import itertools
import os
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusPaths
from hydrus.core import HydrusData

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientLocation
from hydrus.client import ClientPaths
from hydrus.client.media import ClientMedia
from hydrus.client.metadata import ClientContentUpdates
from hydrus.client.search import ClientSearch

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
    

def GetLocalFileActionServiceKeys( media: typing.Collection[ ClientMedia.MediaSingleton ] ):
    
    local_media_file_service_keys = set( CG.client_controller.services_manager.GetServiceKeys( ( HC.LOCAL_FILE_DOMAIN, ) ) )
    
    local_duplicable_to_file_service_keys = set()
    local_moveable_from_and_to_file_service_keys = set()
    
    for m in media:
        
        locations_manager = m.GetLocationsManager()
        
        current = locations_manager.GetCurrent()
        
        if locations_manager.IsLocal():
            
            can_send_to = local_media_file_service_keys.difference( current )
            can_send_from = local_media_file_service_keys.intersection( current )
            
            if len( can_send_to ) > 0:
                
                local_duplicable_to_file_service_keys.update( can_send_to )
                
                if len( can_send_from ) > 0:
                    
                    # can_send_from does not include trash. we won't say 'move from trash to blah' since that's a little complex. we'll just say 'add to blah' in that case I think
                    
                    local_moveable_from_and_to_file_service_keys.update( list( itertools.product( can_send_from, can_send_to ) ) )
                    
                
            
        
    
    return ( local_duplicable_to_file_service_keys, local_moveable_from_and_to_file_service_keys )
    

def OpenExternally( media: typing.Optional[ ClientMedia.MediaSingleton ] ) -> bool:
    
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
    

def OpenFileLocation( media: typing.Optional[ ClientMedia.MediaSingleton ] ) -> bool:
    
    if media is None:
        
        return False
        
    
    if not media.GetLocationsManager().IsLocal():
        
        return False
        
    
    hash = media.GetHash()
    mime = media.GetMime()
    
    path = CG.client_controller.client_files_manager.GetFilePath( hash, mime )
    
    HydrusPaths.OpenFileLocation( path )
    
    return True
    

def OpenInWebBrowser( media: typing.Optional[ ClientMedia.MediaSingleton ] ) -> bool:
    
    if media is None:
        
        return False
        
    
    if not media.GetLocationsManager().IsLocal():
        
        return False
        
    
    hash = media.GetHash()
    mime = media.GetMime()
    
    path = CG.client_controller.client_files_manager.GetFilePath( hash, mime )
    
    ClientPaths.LaunchPathInWebBrowser( path )
    
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
            
        
    

def ShowFilesInNewDuplicatesFilterPage( hashes: typing.Collection[ bytes ], location_context: ClientLocation.LocationContext ):
    
    activate_window = CG.client_controller.new_options.GetBoolean( 'activate_window_on_tag_search_page_activation' )
    
    predicates = [ ClientSearch.Predicate( predicate_type = ClientSearch.PREDICATE_TYPE_SYSTEM_HASH, value = ( tuple( hashes ), 'sha256' ) ) ]
    
    page_name = 'duplicates'
    
    CG.client_controller.pub( 'new_page_duplicates', location_context, initial_predicates = predicates, page_name = page_name, activate_window = activate_window )
    

def ShowFilesInNewPage( hashes: typing.Collection[ bytes ], location_context: ClientLocation.LocationContext, media_sort = None, media_collect = None ):
    
    CG.client_controller.pub( 'new_page_query', location_context, initial_hashes = hashes, initial_sort = media_sort, initial_collect = media_collect )
    

def ShowSimilarFilesInNewPage( media: typing.Collection[ ClientMedia.MediaSingleton ], location_context: ClientLocation.LocationContext, max_hamming: int ):
    
    hashes = set()
    
    for m in media:
        
        if m.GetMime() in HC.FILES_THAT_HAVE_PERCEPTUAL_HASH:
            
            hashes.add( m.GetHash() )
            
        
    
    if len( hashes ) > 0:
        
        initial_predicates = [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_SIMILAR_TO_FILES, ( tuple( hashes ), max_hamming ) ) ]
        
        CG.client_controller.pub( 'new_page_query', location_context, initial_predicates = initial_predicates )
        
    

def UndeleteFiles( hashes ):
    
    local_file_service_keys = CG.client_controller.services_manager.GetServiceKeys( ( HC.LOCAL_FILE_DOMAIN, ) )
    
    for chunk_of_hashes in HydrusData.SplitIteratorIntoChunks( hashes, 64 ):
        
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
            
        
    
