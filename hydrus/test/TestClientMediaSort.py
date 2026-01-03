import unittest
from unittest import mock

import numpy

from hydrus.client import ClientConstants as CC
from hydrus.client.media import ClientMedia
from hydrus.client.search import ClientSearchTagContext


class _DummyTagsManager:
    
    def __init__( self, tags ):
        
        self._tags = set( tags )
        
    
    def GetCurrentAndPending( self, service_key, tag_display_type ):
        
        return set( self._tags )
        
    

class _DummyFileInfoManager:
    
    def __init__( self, blurhash ):
        
        self.blurhash = blurhash
        
    

class _DummyMediaResult:
    
    def __init__( self, blurhash ):
        
        self._file_info_manager = _DummyFileInfoManager( blurhash )
        
    
    def GetFileInfoManager( self ):
        
        return self._file_info_manager
        
    

class _DummyMedia:
    
    def __init__( self, blurhash = None, tags = None ):
        
        self._media_result = _DummyMediaResult( blurhash )
        self._tags_manager = _DummyTagsManager( tags or set() )
        
    
    def GetDisplayMedia( self ):
        
        return self
        
    
    def GetMediaResult( self ):
        
        return self._media_result
        
    
    def GetTagsManager( self ):
        
        return self._tags_manager
        
    

class TestClientMediaSeriation( unittest.TestCase ):
    
    def test_seriation_blurhash_greedy_order( self ):
        
        m1 = _DummyMedia( blurhash = 'bh1' )
        m2 = _DummyMedia( blurhash = 'bh2' )
        m3 = _DummyMedia( blurhash = 'bh3' )
        m4 = _DummyMedia( blurhash = None )
        
        mapping = {
            'bh1' : numpy.array( [[[ 0, 0, 0 ]]], dtype = numpy.float32 ),
            'bh2' : numpy.array( [[[ 1, 1, 1 ]]], dtype = numpy.float32 ),
            'bh3' : numpy.array( [[[ 4, 4, 4 ]]], dtype = numpy.float32 )
        }
        colour_mapping = {
            'bh1' : ( 0, 0, 0 ),
            'bh2' : ( 1, 1, 1 ),
            'bh3' : ( 4, 4, 4 )
        }
        
        def fake_blurhash( blurhash, width, height ):
            
            return mapping[ blurhash ]
            
        
        def fake_average_colour( blurhash ):
            
            return colour_mapping[ blurhash ]
            
        
        with mock.patch( 'hydrus.client.media.ClientMedia.HydrusBlurhash.GetNumpyFromBlurhash', side_effect = fake_blurhash ), mock.patch( 'hydrus.client.media.ClientMedia.HydrusBlurhash.GetAverageColourFromBlurhash', side_effect = fake_average_colour ):
            
            ordered = ClientMedia.GetSeriationOrderingForMediasByBlurhash( [ m1, m2, m3, m4 ], reverse = False )
            self.assertEqual( ordered, [ m2, m1, m3, m4 ] )
            
            ordered_reverse = ClientMedia.GetSeriationOrderingForMediasByBlurhash( [ m1, m2, m3, m4 ], reverse = True )
            self.assertEqual( ordered_reverse, [ m4, m3, m1, m2 ] )
            
        
    
    def test_seriation_tags_greedy_order( self ):
        
        m0 = _DummyMedia( tags = { 'a', 'b' } )
        m1 = _DummyMedia( tags = { 'a', 'b', 'c' } )
        m2 = _DummyMedia( tags = { 'c' } )
        m3 = _DummyMedia( tags = { 'd' } )
        m4 = _DummyMedia( tags = set() )
        
        tag_context = ClientSearchTagContext.TagContext( service_key = CC.COMBINED_TAG_SERVICE_KEY )
        ordered = ClientMedia.GetSeriationOrderingForMediasByTags( [ m0, m1, m2, m3, m4 ], reverse = False, tag_context = tag_context )
        self.assertEqual( ordered, [ m1, m0, m2, m3, m4 ] )
        
        ordered_reverse = ClientMedia.GetSeriationOrderingForMediasByTags( [ m0, m1, m2, m3, m4 ], reverse = True, tag_context = tag_context )
        self.assertEqual( ordered_reverse, [ m4, m3, m2, m0, m1 ] )
        
    
    def test_seriation_visual_and_tags_greedy_order( self ):
        
        m0 = _DummyMedia( blurhash = 'bh1', tags = { 'a' } )
        m1 = _DummyMedia( blurhash = 'bh2', tags = { 'a', 'b' } )
        m2 = _DummyMedia( blurhash = 'bh3', tags = { 'c' } )
        m3 = _DummyMedia( tags = { 'c' } )
        
        mapping = {
            'bh1' : numpy.array( [[[ 0, 0, 0 ]]], dtype = numpy.float32 ),
            'bh2' : numpy.array( [[[ 1, 1, 1 ]]], dtype = numpy.float32 ),
            'bh3' : numpy.array( [[[ 4, 4, 4 ]]], dtype = numpy.float32 )
        }
        colour_mapping = {
            'bh1' : ( 0, 0, 0 ),
            'bh2' : ( 1, 1, 1 ),
            'bh3' : ( 4, 4, 4 )
        }
        
        def fake_blurhash( blurhash, width, height ):
            
            return mapping[ blurhash ]
            
        
        def fake_average_colour( blurhash ):
            
            return colour_mapping[ blurhash ]
            
        
        tag_context = ClientSearchTagContext.TagContext( service_key = CC.COMBINED_TAG_SERVICE_KEY )
        
        with mock.patch( 'hydrus.client.media.ClientMedia.HydrusBlurhash.GetNumpyFromBlurhash', side_effect = fake_blurhash ), mock.patch( 'hydrus.client.media.ClientMedia.HydrusBlurhash.GetAverageColourFromBlurhash', side_effect = fake_average_colour ):
            
            ordered = ClientMedia.GetSeriationOrderingForMediasByVisualAndTags( [ m0, m1, m2, m3 ], reverse = False, tag_context = tag_context )
            self.assertEqual( ordered, [ m1, m0, m2, m3 ] )
            
            ordered_reverse = ClientMedia.GetSeriationOrderingForMediasByVisualAndTags( [ m0, m1, m2, m3 ], reverse = True, tag_context = tag_context )
            self.assertEqual( ordered_reverse, [ m3, m2, m0, m1 ] )
            
        
