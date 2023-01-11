import random
import unittest

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusGlobals as HG

from hydrus.client import ClientConstants as CC
from hydrus.client.media import ClientMediaManagers
from hydrus.client.media import ClientMediaResult

def compare_content_updates( ut: unittest.TestCase, service_keys_to_content_updates, expected_service_keys_to_content_updates ):
    
    ut.assertEqual( len( service_keys_to_content_updates ), len( expected_service_keys_to_content_updates ) )
    
    for ( service_key, content_updates ) in service_keys_to_content_updates.items():
        
        expected_content_updates = expected_service_keys_to_content_updates[ service_key ]
        
        c_u_tuples = sorted( ( ( c_u.ToTuple(), c_u.GetReason() ) for c_u in content_updates ) )
        e_c_u_tuples = sorted( ( ( e_c_u.ToTuple(), e_c_u.GetReason() ) for e_c_u in expected_content_updates ) )
        
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
    
    import_timestamp = random.randint( HydrusData.GetNow() - 1000000, HydrusData.GetNow() - 15 )
    
    current_to_timestamps = { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : import_timestamp, CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY : import_timestamp, CC.LOCAL_FILE_SERVICE_KEY : import_timestamp }
    
    tags_manager = ClientMediaManagers.TagsManager( service_keys_to_statuses_to_tags, service_keys_to_statuses_to_display_tags )
    
    timestamp_manager = ClientMediaManagers.TimestampManager()
    
    file_modified_timestamp = random.randint( import_timestamp - 50000, import_timestamp - 1 )
    
    timestamp_manager.SetFileModifiedTimestamp( file_modified_timestamp )
    
    locations_manager = ClientMediaManagers.LocationsManager(
        current_to_timestamps,
        {},
        set(),
        set(),
        inbox = False,
        urls = set(),
        service_keys_to_filenames = service_keys_to_filenames,
        timestamp_manager = timestamp_manager
    )
    ratings_manager = ClientMediaManagers.RatingsManager( {} )
    notes_manager = ClientMediaManagers.NotesManager( { 'note' : 'hello', 'note2' : 'hello2' } )
    file_viewing_stats_manager = ClientMediaManagers.FileViewingStatsManager.STATICGenerateEmptyManager()
    
    media_result = ClientMediaResult.MediaResult( file_info_manager, tags_manager, locations_manager, ratings_manager, notes_manager, file_viewing_stats_manager )
    
    return media_result
    
