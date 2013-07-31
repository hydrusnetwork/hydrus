import collections
import HydrusConstants as HC
import HydrusDownloading
import os
import TestConstants
import unittest

class TestDownloaders( unittest.TestCase ):
    
    def test_newgrounds( self ):
        
        with HC.o( HC.STATIC_DIR + os.path.sep + 'testing' + os.path.sep + 'newgrounds_gallery_games.html' ) as f: newgrounds_gallery_games = f.read()
        with HC.o( HC.STATIC_DIR + os.path.sep + 'testing' + os.path.sep + 'newgrounds_gallery_movies.html' ) as f: newgrounds_gallery_movies = f.read()
        
        fake_connection = TestConstants.FakeHTTPConnection( host = 'warlord-of-noodles.newgrounds.com' )
        
        fake_connection.SetResponse( 'GET', '/games/', newgrounds_gallery_games )
        fake_connection.SetResponse( 'GET', '/movies/', newgrounds_gallery_movies )
        
        TestConstants.fake_http_connection_manager.SetConnection( fake_connection, host = 'warlord-of-noodles.newgrounds.com' )
        
        HC.get_connection = TestConstants.fake_http_connection_manager.GetConnection
        
        #
        
        downloader = HydrusDownloading.DownloaderNewgrounds( 'warlord-of-noodles' )
        
        #
        
        gallery_urls = downloader.GetAnotherPage()
        
        expected_gallery_urls = [('http://www.newgrounds.com/portal/view/621259',), ('http://www.newgrounds.com/portal/view/617915',), ('http://www.newgrounds.com/portal/view/612665',), ('http://www.newgrounds.com/portal/view/610813',), ('http://www.newgrounds.com/portal/view/609683',), ('http://www.newgrounds.com/portal/view/593806',), ('http://www.newgrounds.com/portal/view/606387',), ('http://www.newgrounds.com/portal/view/606111',), ('http://www.newgrounds.com/portal/view/604603',), ('http://www.newgrounds.com/portal/view/604152',), ('http://www.newgrounds.com/portal/view/603027',), ('http://www.newgrounds.com/portal/view/601680',), ('http://www.newgrounds.com/portal/view/600626',), ('http://www.newgrounds.com/portal/view/591049',), ('http://www.newgrounds.com/portal/view/583715',), ('http://www.newgrounds.com/portal/view/584272',), ('http://www.newgrounds.com/portal/view/577497',), ('http://www.newgrounds.com/portal/view/563780',), ('http://www.newgrounds.com/portal/view/562785',), ('http://www.newgrounds.com/portal/view/553298',), ('http://www.newgrounds.com/portal/view/550882',), ('http://www.newgrounds.com/portal/view/488200',), ('http://www.newgrounds.com/portal/view/509249',), ('http://www.newgrounds.com/portal/view/509175',), ('http://www.newgrounds.com/portal/view/488180',)]
        
        self.assertEqual( gallery_urls, expected_gallery_urls )
        
        #
        
        with HC.o( HC.STATIC_DIR + os.path.sep + 'testing' + os.path.sep + 'newgrounds_page.html' ) as f: newgrounds_page = f.read()
        
        fake_connection = TestConstants.FakeHTTPConnection( host = 'www.newgrounds.com' )
        
        fake_connection.SetResponse( 'GET', '/portal/view/583715', newgrounds_page )
        
        TestConstants.fake_http_connection_manager.SetConnection( fake_connection, host = 'www.newgrounds.com' )
        
        fake_connection = TestConstants.FakeHTTPConnection( host = 'uploads.ungrounded.net' )
        
        fake_connection.SetResponse( 'GET', '/583000/583715_catdust.swf', 'swf file' )
        
        TestConstants.fake_http_connection_manager.SetConnection( fake_connection, host = 'uploads.ungrounded.net' )
        
        info = downloader.GetFileAndTags( 'http://www.newgrounds.com/portal/view/583715' )
        
        expected_info = ('swf file', set([u'chores', u'laser', u'silent', u'title:Cat Dust', u'creator:warlord-of-noodles', u'pointer']))
        
        self.assertEqual( info, expected_info )
        
        # check the swf url and tags are correct
        
        #
        
        HC.get_connection = HC.AdvancedHTTPConnection
        
    