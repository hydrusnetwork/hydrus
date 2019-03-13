import collections
from . import HydrusConstants as HC
from . import ClientData
from . import ClientTags
import os
import unittest
from . import HydrusData
from . import ClientConstants as CC

class TestFunctions( unittest.TestCase ):
    
    def test_dict_to_content_updates( self ):
        
        hash = HydrusData.GenerateKey()
        
        hashes = { hash }
        
        local_key = CC.LOCAL_TAG_SERVICE_KEY
        remote_key = HydrusData.GenerateKey()
        
        service_keys_to_tags = ClientTags.ServiceKeysToTags( { local_key : { 'a' } } )
        
        content_updates = { local_key : [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'a', hashes ) ) ] }
        
        self.assertEqual( ClientData.ConvertServiceKeysToTagsToServiceKeysToContentUpdates( { hash }, service_keys_to_tags ), content_updates )
        
        service_keys_to_tags = ClientTags.ServiceKeysToTags( { remote_key : { 'c' } } )
        
        content_updates = { remote_key : [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PEND, ( 'c', hashes ) ) ] }
        
        self.assertEqual( ClientData.ConvertServiceKeysToTagsToServiceKeysToContentUpdates( { hash }, service_keys_to_tags ), content_updates )
        
        service_keys_to_tags = ClientTags.ServiceKeysToTags( { local_key : [ 'a', 'character:b' ], remote_key : [ 'c', 'series:d' ] } )
        
        content_updates = {}
        
        content_updates[ local_key ] = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'a', hashes ) ), HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'character:b', hashes ) ) ]
        content_updates[ remote_key ] = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PEND, ( 'c', hashes ) ), HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PEND, ( 'series:d', hashes ) ) ]
        
        self.assertEqual( HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PEND, 'c' ), HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PEND, 'c' ) )
        self.assertEqual( ClientData.ConvertServiceKeysToTagsToServiceKeysToContentUpdates( { hash }, service_keys_to_tags ), content_updates )
        
    
    def test_number_conversion( self ):
        
        i = 123456789
        
        i_pretty = HydrusData.ToHumanInt( i )
        
        # this test only works on anglo computers; it is mostly so I can check it is working on mine
        
        self.assertEqual( i_pretty, '123,456,789' )
        
    
