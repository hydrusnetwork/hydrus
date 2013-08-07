import ClientConstants as CC
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
        
        #
        
        HC.get_connection = HC.AdvancedHTTPConnection
        
    
    def test_booru_e621( self ):
        
        with HC.o( HC.STATIC_DIR + os.path.sep + 'testing' + os.path.sep + 'e621_gallery.html' ) as f: e621_gallery = f.read()
        with HC.o( HC.STATIC_DIR + os.path.sep + 'testing' + os.path.sep + 'e621_page.html' ) as f: e621_page = f.read()
        
        fake_connection = TestConstants.FakeHTTPConnection( host = 'e621.net' )
        
        fake_connection.SetResponse( 'GET', '/post/index?page=1&tags=flash', e621_gallery )
        fake_connection.SetResponse( 'GET', '/post/show/360338/2013-3_toes-anal-anal_penetration-animated-argonia', e621_page )
        
        TestConstants.fake_http_connection_manager.SetConnection( fake_connection, host = 'e621.net' )
        
        HC.get_connection = TestConstants.fake_http_connection_manager.GetConnection
        
        #
        
        downloader = HydrusDownloading.DownloaderBooru( CC.DEFAULT_BOORUS[ 'e621' ], [ 'flash' ] )
        
        #
        
        gallery_urls = downloader.GetAnotherPage()
        
        expected_gallery_urls = [(u'http://e621.net/post/show/360338/2013-3_toes-anal-anal_penetration-animated-argonia',), (u'http://e621.net/post/show/359813/2013-abdominal_bulge-ambiguous_gender-amwulf-anal-',), (u'http://e621.net/post/show/359715/animated-avian-bird-bukkake-chirpy-cum-cum_everywh',), (u'http://e621.net/post/show/359711/animated-avian-bird-bukkake-chirpy-cum-cum_everywh',), (u'http://e621.net/post/show/359684/after_sex-animated-anthro-areola-breasts-cat-cum_e',), (u'http://e621.net/post/show/359303/abs-adam_wan-alcohol-anal-animated-anklet-antlers-',), (u'http://e621.net/post/show/359234/anal-animated-cat-cub-feline-flash-gay-lagomorph-m',), (u'http://e621.net/post/show/358988/2013-animated-blue_eyes-blue_hair-bonbon_-mlp-book',), (u'http://e621.net/post/show/358732/all_fours-anal-animated-anus-balls-bent_over-black',), (u'http://e621.net/post/show/358416/3d-alien-animated-black_eyes-cameltoe_slide-chubby',), (u'http://e621.net/post/show/358367/animated-butt-coco_bandicoot-cosplay-cute-flash-lo',), (u'http://e621.net/post/show/358140/3d-animated-cum-cum_in_pussy-cum_inside-das-doggys',), (u'http://e621.net/post/show/357912/animated-anthro-big_breasts-breasts-cat-cum-cum_in',), (u'http://e621.net/post/show/356813/amazing-animated-bear-bikini-breasts-cephalopod-ce',), (u'http://e621.net/post/show/356583/aircraft-airplane-animated-anime-canine-cat-cloud-',), (u'http://e621.net/post/show/356515/3d-alien-animated-autofellatio-black_eyes-chubby-c',), (u'http://e621.net/post/show/355999/animated-balls-claws-cum-cum_in_mouth-cum_on_face-',), (u'http://e621.net/post/show/355265/abdominal_bulge-animated-areola-balls-big_breasts-',), (u'http://e621.net/post/show/355159/3d-animated-cunnilingus-duo-erection-eye_contact-e',), (u'http://e621.net/post/show/355087/2013-animated-anthro-anthrofied-antler-balls-blue_',), (u'http://e621.net/post/show/354998/animated-equine-flash-fluttershy_-mlp-friendship_i',), (u'http://e621.net/post/show/354942/animated-baddoganimations-balls-battle_angel-big_b',), (u'http://e621.net/post/show/354906/animated-censor_bar-censored-crossgender-dickgirl-',), (u'http://e621.net/post/show/354602/animated-baddoganimations-big_breasts-breasts-dick',), (u'http://e621.net/post/show/354597/anal-anal_penetration-animated-baddoganimations-bi',), (u'http://e621.net/post/show/354090/2013-3_toes-anal-anal_penetration-animated-arms_be',), (u'http://e621.net/post/show/354042/16-9-2012-2013-abs-adam_wan-alcohol-animated-ankle',), (u'http://e621.net/post/show/353861/alligator-animated-applejack_-mlp-cat-derpy_hooves',), (u'http://e621.net/post/show/353800/3_toes-3d-animated-balls-bayleef-cgi-cum-cum_infla',), (u'http://e621.net/post/show/353254/alcohol-amphibian-animated-beverage-candles-canine',), (u'http://e621.net/post/show/353140/2013-animated-blue_fur-crossgender-cum-cum_in_hair',), (u'http://e621.net/post/show/352892/anal-animated-breasts-butt-english_text-female-fis',), (u'http://e621.net/post/show/352800/abs-after_sex-alcohol-amily_-coc-anal-anal_penetra',), (u'http://e621.net/post/show/352670/2013-abs-adult-animated-anthro-balls-biceps-big_pe',), (u'http://e621.net/post/show/352394/2013-anal-anal_penetration-animated-avian-balls-ba',), (u'http://e621.net/post/show/352303/animated-breasts-butt-cunnilingus-dark_skin-dialog',), (u'http://e621.net/post/show/352044/2013-4_toes-animated-arm_support-barefoot-black_no',), (u'http://e621.net/post/show/351504/2013-animated-avian-big_breasts-bike_shorts-bird-b',), (u'http://e621.net/post/show/351409/2013-animated-black_fur-blue_hair-cutie_mark-death',), (u'http://e621.net/post/show/351372/-animated-big-big_muffintosh-blue_background-blush',), (u'http://e621.net/post/show/351360/anal-anal_penetration-animated-anthro-autofellatio',), (u'http://e621.net/post/show/351238/2013-3d-animated-balls-big_balls-black_fur-blue_ey',), (u'http://e621.net/post/show/350992/animated-antlers-basket-bottle-bush-canine-clothin',), (u'http://e621.net/post/show/350989/3d-animated-bed-bestiality-black_fur-breasts-build',), (u'http://e621.net/post/show/350548/animated-balls-bed-canine-erection-flash-humbuged-',)]
        
        self.assertEqual( gallery_urls, expected_gallery_urls )
        
        #
        
        TestConstants.fake_http_connection_manager.SetConnection( fake_connection, host = 'e621.net' )
        
        fake_connection = TestConstants.FakeHTTPConnection( scheme = 'https', host = 'static1.e621.net' )
        
        fake_connection.SetResponse( 'GET', '/data/f5/48/f54897c2543e0264e1a64d7f7c33c9f9.swf', 'swf file' )
        
        TestConstants.fake_http_connection_manager.SetConnection( fake_connection, scheme = 'https', host = 'static1.e621.net' )
        
        info = downloader.GetFileAndTags( 'http://e621.net/post/show/360338/2013-3_toes-anal-anal_penetration-animated-argonia' )
        
        expected_info = ('swf file', [u'creator:jasonafex', u'creator:kabier', u'2013', u'3 toes', u'anal', u'anal penetration', u'animated', u'balls', u'barefoot', u'bed', u'bedroom', u'biceps', u'blue skin', u'butt', u'claws', u'clock', u'collaboration', u'couple', u'cum', u'cum in ass', u'cum inside', u'cyan skin', u'erection', u'flash', u'gay', u'green eyes', u'hairless', u'hand holding', u'happy sex', u'hi res', u'horn', u'humanoid penis', u'lamp', u'licking', u'lying', u'male', u'missionary position', u'muscles', u'night', u'on back', u'open mouth', u'paws', u'penetration', u'penis', u'raised leg', u'red penis', u'red skin', u'room', u'saliva', u'sharp teeth', u'side view', u'stripes', u'teeth', u'thick thighs', u'tongue', u'video games', u'wood', u'yellow sclera', u'series:the elder scrolls', u'species:argonian', u'species:dragon', u'species:scalie', u'character:spyke'])
        
        self.assertEqual( info, expected_info )
        
        #
        
        HC.get_connection = HC.AdvancedHTTPConnection
        
    