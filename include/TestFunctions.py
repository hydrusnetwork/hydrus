import ClientConstants
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
        
        local = TestConstants.GenerateClientServiceIdentifier( HC.LOCAL_TAG )
        remote = TestConstants.GenerateClientServiceIdentifier( HC.TAG_REPOSITORY )
        
        service_identifiers_to_tags = { local : { 'a' } }
        
        content_updates = { local : [ HC.ContentUpdate( HC.CONTENT_DATA_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'a', hashes ) ) ] }
        
        self.assertEqual( HydrusDownloading.ConvertServiceIdentifiersToTagsToServiceIdentifiersToContentUpdates( hash, service_identifiers_to_tags ), content_updates )
        
        service_identifiers_to_tags = { remote : { 'c' } }
        
        content_updates = { remote : [ HC.ContentUpdate( HC.CONTENT_DATA_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PENDING, ( 'c', hashes ) ) ] }
        
        self.assertEqual( HydrusDownloading.ConvertServiceIdentifiersToTagsToServiceIdentifiersToContentUpdates( hash, service_identifiers_to_tags ), content_updates )
        
        service_identifiers_to_tags = { local : [ 'a', 'character:b' ], remote : [ 'c', 'series:d' ] }
        
        content_updates = {}
        
        content_updates[ local ] = [ HC.ContentUpdate( HC.CONTENT_DATA_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'a', hashes ) ), HC.ContentUpdate( HC.CONTENT_DATA_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'character:b', hashes ) ) ]
        content_updates[ remote ] = [ HC.ContentUpdate( HC.CONTENT_DATA_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PENDING, ( 'c', hashes ) ), HC.ContentUpdate( HC.CONTENT_DATA_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PENDING, ( 'series:d', hashes ) ) ]
        
        self.assertEqual( HC.ContentUpdate( HC.CONTENT_DATA_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PENDING, 'c' ), HC.ContentUpdate( HC.CONTENT_DATA_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PENDING, 'c' ) )
        self.assertEqual( HydrusDownloading.ConvertServiceIdentifiersToTagsToServiceIdentifiersToContentUpdates( hash, service_identifiers_to_tags ), content_updates )
        
    
    def test_tags_to_dict( self ):
        
        local = TestConstants.GenerateClientServiceIdentifier( HC.LOCAL_TAG )
        remote = TestConstants.GenerateClientServiceIdentifier( HC.TAG_REPOSITORY )
        
        advanced_tag_options = {}
        
        advanced_tag_options[ local ] = [ '', 'character' ]
        advanced_tag_options[ remote ] = [ '', 'character' ]
        
        tags = [ 'a', 'character:b', 'series:c' ]
        
        service_identifiers_to_tags = { local : { 'a', 'character:b' }, remote : { 'a', 'character:b' } }
        
        self.assertEqual( HydrusDownloading.ConvertTagsToServiceIdentifiersToTags( tags, advanced_tag_options ), service_identifiers_to_tags )
        
    
if __name__ == '__main__':
    
    app = TestConstants.TestController()
    
    unittest.main( verbosity = 2, exit = False )
    
    raw_input()
    