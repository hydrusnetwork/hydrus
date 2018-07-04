import collections
import HydrusConstants as HC
import ClientData
import os
import TestConstants
import unittest
import HydrusData
import ClientConstants as CC

class TestFunctions( unittest.TestCase ):
    
    def test_dict_to_content_updates( self ):
        
        hash = HydrusData.GenerateKey()
        
        hashes = { hash }
        
        local_key = CC.LOCAL_TAG_SERVICE_KEY
        remote_key = HydrusData.GenerateKey()
        
        service_keys_to_tags = { local_key : { 'a' } }
        
        content_updates = { local_key : [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'a', hashes ) ) ] }
        
        self.assertEqual( ClientData.ConvertServiceKeysToTagsToServiceKeysToContentUpdates( { hash }, service_keys_to_tags ), content_updates )
        
        service_keys_to_tags = { remote_key : { 'c' } }
        
        content_updates = { remote_key : [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PEND, ( 'c', hashes ) ) ] }
        
        self.assertEqual( ClientData.ConvertServiceKeysToTagsToServiceKeysToContentUpdates( { hash }, service_keys_to_tags ), content_updates )
        
        service_keys_to_tags = { local_key : [ 'a', 'character:b' ], remote_key : [ 'c', 'series:d' ] }
        
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
        
    
    def test_unicode_conversion( self ):
        
        u = u'here is a unicode character: \u76f4'
        
        b = HydrusData.ToByteString( u )
        
        bu = HydrusData.ToUnicode( b )
        
        self.assertEqual( type( b ), str )
        self.assertEqual( b, 'here is a unicode character: \xe7\x9b\xb4' )
        
        self.assertEqual( type( bu ), unicode )
        self.assertEqual( bu, u )
        
        d = {}
        
        u = HydrusData.ToUnicode( d )
        b = HydrusData.ToByteString( d )
        
        self.assertEqual( type( u ), unicode )
        self.assertEqual( u, u'{}' )
        
        self.assertEqual( type( b ), str )
        self.assertEqual( b, '{}' )
        
        pretty_num = HydrusData.ToHumanInt( 123456789 )
        
        self.assertEqual( type( pretty_num ), unicode )
        
    
