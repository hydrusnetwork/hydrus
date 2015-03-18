import collections
import HydrusConstants as HC
import HydrusDownloading
import os
import TestConstants
import unittest

class TestHydrusDownloadingFunctions( unittest.TestCase ):
    
    def test_dict_to_content_updates( self ):
        
        hash = os.urandom( 32 )
        
        hashes = set( [ hash ] )
        
        local_key = HC.LOCAL_TAG_SERVICE_KEY
        remote_key = os.urandom( 32 )
        
        service_keys_to_tags = { local_key : { 'a' } }
        
        content_updates = { local_key : [ HC.ContentUpdate( HC.CONTENT_DATA_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'a', hashes ) ) ] }
        
        self.assertEqual( HydrusDownloading.ConvertServiceKeysToTagsToServiceKeysToContentUpdates( hash, service_keys_to_tags ), content_updates )
        
        service_keys_to_tags = { remote_key : { 'c' } }
        
        content_updates = { remote_key : [ HC.ContentUpdate( HC.CONTENT_DATA_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PENDING, ( 'c', hashes ) ) ] }
        
        self.assertEqual( HydrusDownloading.ConvertServiceKeysToTagsToServiceKeysToContentUpdates( hash, service_keys_to_tags ), content_updates )
        
        service_keys_to_tags = { local_key : [ 'a', 'character:b' ], remote_key : [ 'c', 'series:d' ] }
        
        content_updates = {}
        
        content_updates[ local_key ] = [ HC.ContentUpdate( HC.CONTENT_DATA_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'a', hashes ) ), HC.ContentUpdate( HC.CONTENT_DATA_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'character:b', hashes ) ) ]
        content_updates[ remote_key ] = [ HC.ContentUpdate( HC.CONTENT_DATA_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PENDING, ( 'c', hashes ) ), HC.ContentUpdate( HC.CONTENT_DATA_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PENDING, ( 'series:d', hashes ) ) ]
        
        self.assertEqual( HC.ContentUpdate( HC.CONTENT_DATA_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PENDING, 'c' ), HC.ContentUpdate( HC.CONTENT_DATA_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PENDING, 'c' ) )
        self.assertEqual( HydrusDownloading.ConvertServiceKeysToTagsToServiceKeysToContentUpdates( hash, service_keys_to_tags ), content_updates )
        
    
    def test_number_conversion( self ):
        
        i = 123456789
        
        i_pretty = HC.ConvertIntToPrettyString( i )
        
        # this test only works on anglo computers; it is mostly so I can check it is working on mine
        
        self.assertEqual( i_pretty, '123,456,789' )
        
    
    def test_tags_to_dict( self ):
        
        local_key = os.urandom( 32 )
        remote_key = os.urandom( 32 )
        
        advanced_tag_options = {}
        
        advanced_tag_options[ local_key ] = [ '', 'character' ]
        advanced_tag_options[ remote_key ] = [ '', 'character' ]
        
        tags = [ 'a', 'character:b', 'series:c' ]
        
        service_keys_to_tags = { local_key : { 'a', 'character:b' }, remote_key : { 'a', 'character:b' } }
        
        self.assertEqual( HydrusDownloading.ConvertTagsToServiceKeysToTags( tags, advanced_tag_options ), service_keys_to_tags )
        
    
if __name__ == '__main__':
    
    app = TestConstants.TestController()
    
    unittest.main( verbosity = 2, exit = False )
    
    raw_input()
    