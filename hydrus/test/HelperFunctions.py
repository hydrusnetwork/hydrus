import random
import unittest

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusTime

from hydrus.client import ClientConstants as CC
from hydrus.client.media import ClientMediaManagers
from hydrus.client.media import ClientMediaResult
from hydrus.client.metadata import ClientContentUpdates

def compare_content_update_packages( ut: unittest.TestCase, content_update_package: ClientContentUpdates.ContentUpdatePackage, expected_content_update_package: ClientContentUpdates.ContentUpdatePackage ):
    
    service_keys_to_content_updates = dict( content_update_package.IterateContentUpdates() )
    expected_service_keys_to_content_updates = dict( expected_content_update_package.IterateContentUpdates() )
    
    ut.assertEqual( len( service_keys_to_content_updates ), len( expected_service_keys_to_content_updates ) )
    
    for ( service_key, content_updates ) in service_keys_to_content_updates.items():
        
        expected_content_updates = expected_service_keys_to_content_updates[ service_key ]
        
        content_updates = sorted( content_updates, key = lambda c_u: str( c_u ) )
        expected_content_updates = sorted( expected_content_updates, key = lambda c_u: str( c_u ) )
        
        # TODO: go back to this when this works right, with ContentUpdateAction rewrite
        # content_update.__hash__ isn't always reliable :(
        #ut.assertEqual( content_updates, expected_content_updates )
        
        c_u_tuples = [ ( c_u.ToTuple(), c_u.GetReason() ) for c_u in content_updates ]
        e_c_u_tuples = [ ( e_c_u.ToTuple(), e_c_u.GetReason() ) for e_c_u in expected_content_updates ]
        
        ut.assertEqual( c_u_tuples, e_c_u_tuples )
        
    

def GetFakeMediaResult( hash: bytes ):
    
    hash_id = random.randint( 0, 200 * ( 1024 ** 2 ) )
    
    size = random.randint( 8192, 20 * 1048576 )
    mime = random.choice( [ HC.IMAGE_JPEG, HC.VIDEO_WEBM, HC.APPLICATION_PDF ] )
    width = random.randint( 200, 4096 )
    height = random.randint( 200, 4096 )
    duration = random.choice( [ 220, 16.66667, None ] )
    has_audio = random.choice( [ True, False ] )
    
    file_info_manager = ClientMediaManagers.FileInfoManager( hash_id, hash, size = size, mime = mime, width = width, height = height, duration = duration, has_audio = has_audio )
    
    file_info_manager.has_exif = True
    file_info_manager.has_icc_profile = True
    
    service_keys_to_statuses_to_tags = { CC.DEFAULT_LOCAL_TAG_SERVICE_KEY : { HC.CONTENT_STATUS_CURRENT : { 'blue_eyes', 'blonde_hair' }, HC.CONTENT_STATUS_PENDING : { 'bodysuit' } } }
    service_keys_to_statuses_to_display_tags = { CC.DEFAULT_LOCAL_TAG_SERVICE_KEY : { HC.CONTENT_STATUS_CURRENT : { 'blue eyes', 'blonde hair' }, HC.CONTENT_STATUS_PENDING : { 'bodysuit', 'clothing' } } }
    
    service_keys_to_filenames = {}
    
    tags_manager = ClientMediaManagers.TagsManager( service_keys_to_statuses_to_tags, service_keys_to_statuses_to_display_tags )
    
    times_manager = ClientMediaManagers.TimesManager()
    
    import_timestamp_ms = random.randint( HydrusTime.GetNowMS() - 1000000000, HydrusTime.GetNowMS() - 15 )
    
    file_modified_timestamp_ms = random.randint( import_timestamp_ms - 50000000, import_timestamp_ms - 1 )
    
    times_manager.SetFileModifiedTimestampMS( file_modified_timestamp_ms )
    
    current_to_timestamps_ms = { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : import_timestamp_ms, CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY : import_timestamp_ms, CC.LOCAL_FILE_SERVICE_KEY : import_timestamp_ms }
    
    times_manager.SetImportedTimestampsMS( current_to_timestamps_ms )
    
    locations_manager = ClientMediaManagers.LocationsManager(
        set( current_to_timestamps_ms.keys() ),
        set(),
        set(),
        set(),
        times_manager,
        inbox = False,
        urls = set(),
        service_keys_to_filenames = service_keys_to_filenames
    )
    ratings_manager = ClientMediaManagers.RatingsManager( {} )
    notes_manager = ClientMediaManagers.NotesManager( { 'note' : 'hello', 'note2' : 'hello2' } )
    file_viewing_stats_manager = ClientMediaManagers.FileViewingStatsManager.STATICGenerateEmptyManager( times_manager )
    
    media_result = ClientMediaResult.MediaResult( file_info_manager, tags_manager, times_manager, locations_manager, ratings_manager, notes_manager, file_viewing_stats_manager )
    
    return media_result
    
