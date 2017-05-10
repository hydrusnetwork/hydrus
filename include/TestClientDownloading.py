import ClientConstants as CC
import ClientDefaults
import collections
import HydrusConstants as HC
import HydrusPaths
import ClientDownloading
import os
import TestConstants
import unittest
import HydrusGlobals as HG

class TestDownloaders( unittest.TestCase ):
    
    @classmethod
    def setUpClass( cls ):
        
        cls.old_http = HG.test_controller.GetHTTP()
        
        HG.test_controller.SetHTTP( TestConstants.FakeHTTPConnectionManager() )
        
    
    @classmethod
    def tearDownClass( cls ):
        
        HG.test_controller.SetHTTP( cls.old_http )
        
    
    def test_newgrounds( self ):
        
        with open( os.path.join( HC.STATIC_DIR, 'testing', 'newgrounds_gallery_games.html' ) ) as f: newgrounds_gallery_games = f.read()
        with open( os.path.join( HC.STATIC_DIR, 'testing', 'newgrounds_gallery_movies.html' ) ) as f: newgrounds_gallery_movies = f.read()
        
        HG.test_controller.GetHTTP().SetResponse( HC.GET, 'http://warlord-of-noodles.newgrounds.com/games/', newgrounds_gallery_games )
        HG.test_controller.GetHTTP().SetResponse( HC.GET, 'http://warlord-of-noodles.newgrounds.com/movies/', newgrounds_gallery_movies )
        
        #
        
        gallery_games = ClientDownloading.GalleryNewgroundsGames()
        gallery_movies = ClientDownloading.GalleryNewgroundsMovies()
        
        #
        
        ( page_of_urls, definitely_no_more_pages ) = gallery_games.GetPage( 'warlord-of-noodles', 0 )
        
        expected_gallery_urls = []
        
        self.assertEqual( page_of_urls, expected_gallery_urls )
        self.assertTrue( definitely_no_more_pages )
        
        #
        
        ( page_of_urls, definitely_no_more_pages ) = gallery_movies.GetPage( 'warlord-of-noodles', 0 )
        
        expected_gallery_urls = [ 'http://www.newgrounds.com/portal/view/621259', 'http://www.newgrounds.com/portal/view/617915', 'http://www.newgrounds.com/portal/view/612665', 'http://www.newgrounds.com/portal/view/610813', 'http://www.newgrounds.com/portal/view/609683', 'http://www.newgrounds.com/portal/view/593806', 'http://www.newgrounds.com/portal/view/606387', 'http://www.newgrounds.com/portal/view/606111', 'http://www.newgrounds.com/portal/view/604603', 'http://www.newgrounds.com/portal/view/604152', 'http://www.newgrounds.com/portal/view/603027', 'http://www.newgrounds.com/portal/view/601680', 'http://www.newgrounds.com/portal/view/600626', 'http://www.newgrounds.com/portal/view/591049', 'http://www.newgrounds.com/portal/view/583715', 'http://www.newgrounds.com/portal/view/584272', 'http://www.newgrounds.com/portal/view/577497', 'http://www.newgrounds.com/portal/view/563780', 'http://www.newgrounds.com/portal/view/562785', 'http://www.newgrounds.com/portal/view/553298', 'http://www.newgrounds.com/portal/view/550882', 'http://www.newgrounds.com/portal/view/488200', 'http://www.newgrounds.com/portal/view/509249', 'http://www.newgrounds.com/portal/view/509175', 'http://www.newgrounds.com/portal/view/488180' ]
        
        self.assertEqual( page_of_urls, expected_gallery_urls )
        self.assertTrue( definitely_no_more_pages )
        
        #
        
        with open( os.path.join( HC.STATIC_DIR, 'testing', 'newgrounds_page.html' ) ) as f: newgrounds_page = f.read()
        
        HG.test_controller.GetHTTP().SetResponse( HC.GET, 'http://www.newgrounds.com/portal/view/583715', newgrounds_page )
        
        HG.test_controller.GetHTTP().SetResponse( HC.GET, 'http://uploads.ungrounded.net/583000/583715_catdust.swf', 'swf file' )
        
        ( os_file_handle, temp_path ) = HydrusPaths.GetTempPath()
        
        try:
            
            gallery = ClientDownloading.GalleryNewgrounds()
            
            tags = gallery.GetFileAndTags( temp_path, 'http://www.newgrounds.com/portal/view/583715' )
            
            with open( temp_path, 'rb' ) as f: data = f.read()
            
        finally:
            
            HydrusPaths.CleanUpTempPath( os_file_handle, temp_path )
            
        
        info = ( data, tags )
        
        expected_info = ( 'swf file', set([u'chores', u'laser', u'silent', u'title:Cat Dust', u'creator:warlord-of-noodles', u'pointer']) )
        
        self.assertEqual( info, expected_info )
        
    
    def test_pixiv( self ):
        
        with open( os.path.join( HC.STATIC_DIR, 'testing', 'pixiv_gallery.html' ) ) as f: pixiv_gallery = f.read()
        with open( os.path.join( HC.STATIC_DIR, 'testing', 'pixiv_image_page.html' ) ) as f: pixiv_page = f.read()
        
        HG.test_controller.GetHTTP().SetResponse( HC.GET, 'http://www.pixiv.net/search.php?word=naruto&s_mode=s_tag_full&order=date_d&p=1', pixiv_gallery )
        HG.test_controller.GetHTTP().SetResponse( HC.GET, 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=50926312', pixiv_page )
        
        HG.test_controller.GetHTTP().SetResponse( HC.GET, 'http://i3.pixiv.net/img-original/img/2014/01/25/19/21/56/41171994_p0.jpg', 'image file' )
        
        #
        
        gallery = ClientDownloading.GalleryPixivTag()
        
        #
        
        ( page_of_urls, definitely_no_more_pages ) = gallery.GetPage( 'naruto', 0 )
        
        # a manga one, http://www.pixiv.net/member_illust.php?mode=medium&illust_id=51078392, is currently filtered
        
        expected_gallery_urls = [ u'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=50926312', 'a bunch of others' ]
        
        self.assertEqual( page_of_urls[0], expected_gallery_urls[0] )
        
        #
        
        ( os_file_handle, temp_path ) = HydrusPaths.GetTempPath()
        
        try:
            
            tags = gallery.GetFileAndTags( temp_path, 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=50926312' )
            
            with open( temp_path, 'rb' ) as f: data = f.read()
            
        finally:
            
            HydrusPaths.CleanUpTempPath( os_file_handle, temp_path )
            
        
        info = ( data, tags )
        
        expected_tags = [u'VOCALOID', u'\u93e1\u97f3\u30ea\u30f3', u'\u5973\u306e\u5b50', u'creator:Canon', u'title:\u30ea\u30f3\u3061\u3083\u3093']
        
        expected_info = ( 'image file', expected_tags )
        
        self.assertEqual( info, expected_info )
        
    
    '''
    # hid this when sankaku started cloudflare 503ing and removed sankaku from the booru defaults
    def test_sankaku( self ):
        
        with open( os.path.join( HC.STATIC_DIR, 'testing', 'sankaku_gallery.html' ) ) as f: sankaku_gallery = f.read()
        with open( os.path.join( HC.STATIC_DIR, 'testing', 'sankaku_page.html' ) ) as f: sankaku_page = f.read()
        
        HG.test_controller.GetHTTP().SetResponse( HC.GET, 'https://chan.sankakucomplex.com/?tags=animal_ears&page=1', sankaku_gallery )
        HG.test_controller.GetHTTP().SetResponse( HC.GET, 'https://chan.sankakucomplex.com/post/show/4324703', sankaku_page )
        
        #
        
        HG.test_controller.SetRead( 'remote_booru', ClientDefaults.GetDefaultBoorus()[ 'sankaku chan' ] )
        
        gallery = ClientDownloading.GalleryBooru( 'sankaku chan' )
        
        #
        
        ( page_of_urls, definitely_no_more_pages ) = gallery.GetPage( 'animal_ears', 0 )
        
        expected_gallery_urls = [ u'https://chan.sankakucomplex.com/post/show/4324703', u'https://chan.sankakucomplex.com/post/show/4324435', u'https://chan.sankakucomplex.com/post/show/4324426', u'https://chan.sankakucomplex.com/post/show/4324365', u'https://chan.sankakucomplex.com/post/show/4324343', u'https://chan.sankakucomplex.com/post/show/4324309', u'https://chan.sankakucomplex.com/post/show/4324134', u'https://chan.sankakucomplex.com/post/show/4324107', u'https://chan.sankakucomplex.com/post/show/4324095', u'https://chan.sankakucomplex.com/post/show/4324086', u'https://chan.sankakucomplex.com/post/show/4323969', u'https://chan.sankakucomplex.com/post/show/4323967', u'https://chan.sankakucomplex.com/post/show/4323665', u'https://chan.sankakucomplex.com/post/show/4323620', u'https://chan.sankakucomplex.com/post/show/4323586', u'https://chan.sankakucomplex.com/post/show/4323581', u'https://chan.sankakucomplex.com/post/show/4323580', u'https://chan.sankakucomplex.com/post/show/4323520', u'https://chan.sankakucomplex.com/post/show/4323512', u'https://chan.sankakucomplex.com/post/show/4323498' ]
        
        self.assertEqual( page_of_urls, expected_gallery_urls )
        self.assertFalse( definitely_no_more_pages )
        
        #
        
        HG.test_controller.GetHTTP().SetResponse( HC.GET, 'https://cs.sankakucomplex.com/data/c5/c3/c5c3c91ca68bd7662f546cc44fe0d378.jpg?4324703', 'image file' )
        
        ( os_file_handle, temp_path ) = HydrusPaths.GetTempPath()
        
        try:
            
            tags = gallery.GetFileAndTags( temp_path, 'https://chan.sankakucomplex.com/post/show/4324703' )
            
            with open( temp_path, 'rb' ) as f: data = f.read()
            
        finally:
            
            HydrusPaths.CleanUpTempPath( os_file_handle, temp_path )
            
        
        info = ( data, tags )
        
        expected_info = ('image file', [ u'medium:uncensored', u'character:heinrike prinzessin zu sayn-wittgenstein', u'character:rosalie de hemricourt de grunne', u'2girls', u'alternative costume', u'anal beads', u'animal ears', u'anus', u'ass', u'ass cutout', u'backless panties', u'blonde', u'blue eyes', u'blush', u'braid', u'butt plug', u'butt plug tail', u'cameltoe', u'cat tail', u'cheerleader', u'dildo', u'fake animal ears', u'fang', u'green eyes', u'hands', u'happy', u'heart cutout', u'kneepits', u'long hair', u'looking at viewer', u'multiple girls', u'nekomimi', u'open mouth', u'pantsu', u'spread anus', u'sweat', u'tail', u'tape', u'underwear', u'white panties', u'creator:null (nyanpyoun)', u'series:strike witches'])
        
        self.assertEqual( info, expected_info )
        
        # flash is tricky for sankaku
        
        with open( os.path.join( HC.STATIC_DIR, 'testing', 'sankaku_flash.html' ) ) as f: sankaku_flash = f.read()
        
        HG.test_controller.GetHTTP().SetResponse( HC.GET, 'https://chan.sankakucomplex.com/post/show/4318061', sankaku_flash )
        HG.test_controller.GetHTTP().SetResponse( HC.GET, 'https://cs.sankakucomplex.com/data/48/ce/48cecd707d8a562d47db74d934505f51.swf?4318061', 'swf file' )
        
        ( os_file_handle, temp_path ) = HydrusPaths.GetTempPath()
        
        try:
            
            gallery.GetFile( temp_path, 'https://chan.sankakucomplex.com/post/show/4318061' )
            
            with open( temp_path, 'rb' ) as f: data = f.read()
            
        finally:
            
            HydrusPaths.CleanUpTempPath( os_file_handle, temp_path )
            
        
        self.assertEqual( data, 'swf file' )
        
    '''
    def test_booru_e621( self ):
        
        with open( os.path.join( HC.STATIC_DIR, 'testing', 'e621_gallery.html' ) ) as f: e621_gallery = f.read()
        with open( os.path.join( HC.STATIC_DIR, 'testing', 'e621_page.html' ) ) as f: e621_page = f.read()
        
        HG.test_controller.GetHTTP().SetResponse( HC.GET, 'https://e621.net/post/index/1/hair', e621_gallery )
        HG.test_controller.GetHTTP().SetResponse( HC.GET, 'https://e621.net/post/show/672179/2015-ambiguous_gender-animal_genitalia-anon-balls-', e621_page )
        
        #
        
        HG.test_controller.SetRead( 'remote_booru', ClientDefaults.GetDefaultBoorus()[ 'e621' ] )
        
        gallery = ClientDownloading.GalleryBooru( 'e621' )
        
        #
        
        ( page_of_urls, definitely_no_more_pages ) = gallery.GetPage( 'hair', 0 )
        
        expected_gallery_urls = [u'https://e621.net/post/show/672179/2015-ambiguous_gender-animal_genitalia-anon-balls-', u'https://e621.net/post/show/672174/2015-blonde_hair-crown-derp_eyes-derpy_hooves_-mlp', u'https://e621.net/post/show/672173/acino_-artist-anal-anal_penetration-anthro-bisexua', u'https://e621.net/post/show/672167/2015-3-anthro-balls-blush-camera-erection-frottage', u'https://e621.net/post/show/672153/2015-anthro-canine-claws-cum-cum_in_mouth-cum_insi', u'https://e621.net/post/show/672151/2015-anthro-canine-clothing-cum-erection-fox-fur-h', u'https://e621.net/post/show/672149/2015-animal_genitalia-anthro-anthro_on_feral-balls', u'https://e621.net/post/show/672148/all_fours-animal_genitalia-balls-bestiality-breast', u'https://e621.net/post/show/672144/4_arms-big_breasts-blonde_hair-bound-breasts-butt-', u'https://e621.net/post/show/672142/abdominal_bulge-anal-anal_penetration-bestiality-b', u'https://e621.net/post/show/672141/abs-animal_ears-beach-big_breasts-bikini-blonde_ha', u'https://e621.net/post/show/672140/all_fours-animal_ears-anthro-big_breasts-blush-bre', u'https://e621.net/post/show/672139/animal_ears-big_breasts-blue_eyes-breasts-bukkake-', u'https://e621.net/post/show/672138/blonde_hair-blue_eyes-blush-breasts-clothing-crown', u'https://e621.net/post/show/672136/2015-apron-brown_fur-brown_hair-butt-clothed-cloth', u'https://e621.net/post/show/672131/animal_ears-black_hair-cat-cat_ears-feline-fight-h', u'https://e621.net/post/show/672130/2015-3d-animated-blush-carrot_top_-mlp-clothing-cu', u'https://e621.net/post/show/672127/balls-bikini-blush-cat-chewycuticle-clothing-cross', u'https://e621.net/post/show/672126/-3-big_breasts-big_penis-blonde_hair-breasts-canin', u'https://e621.net/post/show/672116/canine-eyes_closed-female-fur-grey_fur-grey_hair-h', u'https://e621.net/post/show/672115/animal_ears-breasts-canine-clitoris-cub-cum-cum_dr', u'https://e621.net/post/show/672114/blue_fur-breasts-canine-censor_bar-censored-clitor', u'https://e621.net/post/show/672112/canine-censored-female-fox-green_hair-hair-kemono-', u'https://e621.net/post/show/672111/big_breasts-breasts-brown_eyes-canine-chubby-clito', u'https://e621.net/post/show/672109/blonde_hair-caprine-clothing-comic-cover-doujinshi', u'https://e621.net/post/show/672103/blue_eyes-cheerleader-clothing-cotora-cute-equine-', u'https://e621.net/post/show/672102/canine-cotora-cute-female-fox-green_eyes-hair-kemo', u'https://e621.net/post/show/672101/canine-cotora-cute-female-fox-green_eyes-hair-kemo', u'https://e621.net/post/show/672099/blonde_hair-caprine-cotora-hair-horn-kemono-long_h', u'https://e621.net/post/show/672097/black_hair-cheese-chubby-cute-eyes_closed-female-g', u'https://e621.net/post/show/672095/blush-caprine-eyes_closed-eyewear-female-glasses-h', u'https://e621.net/post/show/672092/black_hair-canine-eating-female-feral-fox-hair-kem', u'https://e621.net/post/show/672091/blue_eyes-breasts-brown_hair-clothing-cute-fur-hai', u'https://e621.net/post/show/672090/black_eyes-blush-canine-cum-dog-female-hair-hat-ke', u'https://e621.net/post/show/672089/canine-cute-dog-drooling-eyes_closed-female-fur-ha', u'https://e621.net/post/show/672087/blush-cute-female-feral-flat_chested-hair-kemono-l', u'https://e621.net/post/show/672086/breasts-brown_eyes-canine-clothing-female-flat_che', u'https://e621.net/post/show/672082/2015-anal-anal_penetration-animal_genitalia-anthro', u'https://e621.net/post/show/672080/-3-anthro-big_breasts-blonde_hair-blue_eyes-bra-br', u'https://e621.net/post/show/672079/cutie_mark-equine-female-feral-friendship_is_magic', u'https://e621.net/post/show/672076/-belt-bench-blush-bra-breasts-cat-clothing-crossge', u'https://e621.net/post/show/672074/2015-amber_eyes-anal-anal_penetration-anthro-areol', u'https://e621.net/post/show/672072/2015-anthro-anthrofied-blue_eyes-blue_hair-blue_ni', u'https://e621.net/post/show/672071/2015-anthro-anthrofied-blue_eyes-blue_hair-blush-b', u'https://e621.net/post/show/672069/2015-angry-blue_hair-crown-english_text-equine-fem', u'https://e621.net/post/show/672063/2015-anthro-big_breasts-big_butt-black_lips-black_', u'https://e621.net/post/show/672060/2015-3-anthro-barefoot-big_breasts-big_butt-big_pe', u'https://e621.net/post/show/672056/anal-censored-cephalopod-deep_penetration-hair-her', u'https://e621.net/post/show/672053/cephalopod-clothing-cunnilingus-female-hair-humano', u'https://e621.net/post/show/672050/2015-clitoris-cum-cum_in_pussy-cum_inside-female-h', u'https://e621.net/post/show/672047/anthro-areola-big_breasts-bow-breast_prod-breasts-', u'https://e621.net/post/show/672045/2015-anthro-anthrofied-areola-big_breasts-blue_eye', u'https://e621.net/post/show/672037/ambiguous_gender-anthro-black_nose-boots-canine-cl', u'https://e621.net/post/show/672034/2015-anthro-anthrofied-big_breasts-breasts-changel', u'https://e621.net/post/show/672031/anus-bed-butt-conrie-cutie_mark-dildo-duo-equine-f', u'https://e621.net/post/show/672029/amphibian-andross-anthro-ape-avian-bird-black_nose', u'https://e621.net/post/show/672025/2015-amber_eyes-anthro-bat-bat_wings-big_penis-bla', u'https://e621.net/post/show/672024/anthro-bare_shoulders-black_nose-blue_eyes-blue_fu', u'https://e621.net/post/show/672023/angry-anthro-belt-black_fur-black_nose-black_panth', u'https://e621.net/post/show/672020/all_fours-anthro-belt-black_nose-clothing-eyeshado', u'https://e621.net/post/show/672019/-3-beverage-blue_hair-blush-coco_pommel_-mlp-cunni', u'https://e621.net/post/show/672018/animal_genitalia-balls-blue_eyes-dickgirl-english_', u'https://e621.net/post/show/672017/anatomically_correct-anatomically_correct_pussy-an', u'https://e621.net/post/show/672015/-3-anthro-b_-artist-belt-black_nose-bodysuit-canin', u'https://e621.net/post/show/672012/anthro-b_-artist-black_nose-bodysuit-canine-clothi', u'https://e621.net/post/show/672009/bear-big_breasts-big_butt-breasts-butt-chubby-clot', u'https://e621.net/post/show/671997/anthro-ball-black_nose-blue_fur-blue_hair-blush-bo', u'https://e621.net/post/show/671992/anthro-belt-bodysuit-boots-canine-clothing-female-', u'https://e621.net/post/show/671988/2015-3-after_sex-aloe_-mlp-blue_eyes-cum-cum_in_mo', u'https://e621.net/post/show/671987/2015-3-after_sex-aloe_-mlp-animal_genitalia-blue_e', u'https://e621.net/post/show/671986/anthro-belt-bodysuit-boots-canine-clothing-female-', u'https://e621.net/post/show/671985/all_fours-bent_over-big_breasts-big_butt-book-brea', u'https://e621.net/post/show/671980/2015-equine-female-feral-friendship_is_magic-fur-h', u'https://e621.net/post/show/671977/2013-anthro-blue_hair-breasts-claws-cloud-collar-e', u'https://e621.net/post/show/671975/2012-anthro-bareisyo-blue_hair-blush-breasts-engli']
        
        self.assertEqual( page_of_urls, expected_gallery_urls )
        self.assertFalse( definitely_no_more_pages )
        
        #
        
        HG.test_controller.GetHTTP().SetResponse( HC.GET, 'https://static1.e621.net/data/75/88/758892ccca10cef5d242b9f49a0b2a13.png', 'png file' )
        
        ( os_file_handle, temp_path ) = HydrusPaths.GetTempPath()
        
        try:
            
            tags = gallery.GetFileAndTags( temp_path, 'https://e621.net/post/show/672179/2015-ambiguous_gender-animal_genitalia-anon-balls-' )
            
            with open( temp_path, 'rb' ) as f: data = f.read()
            
        finally:
            
            HydrusPaths.CleanUpTempPath( os_file_handle, temp_path )
            
        
        info = ( data, tags )
        
        expected_info = ('png file', [u'species:earth pony', u'species:equine', u'species:horse', u'species:mammal', u'species:pony', u'character:anon', u'character:ms harshwhinny (mlp)', u'2015', u'ambiguous gender', u'animal genitalia', u'balls', u'black and white', u'cutie mark', u'dialogue', u'dickgirl', u'duo', u'english text', u'erection', u'hair', u'horsecock', u'huge penis', u'intersex', u'monochrome', u'penis', u'sweat', u'tea bagging', u'text', u'vein', u'creator:dotkwa', u'series:friendship is magic', u'series:my little pony'])
        
        self.assertEqual( info, expected_info )
        
    
    def test_hentai_foundry( self ):
        
        with open( os.path.join( HC.STATIC_DIR, 'testing', 'hf_picture_gallery.html' ) ) as f: picture_gallery = f.read()
        with open( os.path.join( HC.STATIC_DIR, 'testing', 'hf_scrap_gallery.html' ) ) as f: scrap_gallery = f.read()
        with open( os.path.join( HC.STATIC_DIR, 'testing', 'hf_picture_page.html' ) ) as f: picture_page = f.read()
        with open( os.path.join( HC.STATIC_DIR, 'testing', 'hf_scrap_page.html' ) ) as f: scrap_page = f.read()
        
        # what about page/1 or whatever?
        
        HG.test_controller.GetHTTP().SetResponse( HC.GET, 'http://www.hentai-foundry.com/pictures/user/Sparrow/page/1', picture_gallery )
        HG.test_controller.GetHTTP().SetResponse( HC.GET, 'http://www.hentai-foundry.com/pictures/user/Sparrow/scraps/page/1', scrap_gallery )
        HG.test_controller.GetHTTP().SetResponse( HC.GET, 'http://www.hentai-foundry.com/pictures/user/Sparrow/226304/Ashantae', picture_page )
        HG.test_controller.GetHTTP().SetResponse( HC.GET, 'http://www.hentai-foundry.com/pictures/user/Sparrow/226084/Swegabe-Sketches--Gabrielle-027', scrap_page )
        
        cookies = { 'YII_CSRF_TOKEN' : '19b05b536885ec60b8b37650a32f8deb11c08cd1s%3A40%3A%222917dcfbfbf2eda2c1fbe43f4d4c4ec4b6902b32%22%3B' }
        
        HG.test_controller.SetWebCookies( 'hentai foundry', cookies )
        
        #
        
        gallery_pictures = ClientDownloading.GalleryHentaiFoundryArtistPictures()
        gallery_scraps = ClientDownloading.GalleryHentaiFoundryArtistScraps()
        
        #
        
        ( page_of_urls, definitely_no_more_pages ) = gallery_pictures.GetPage( 'Sparrow', 0 )
        
        expected_gallery_urls = ['http://www.hentai-foundry.com/pictures/user/Sparrow/226304/Ashantae', 'http://www.hentai-foundry.com/pictures/user/Sparrow/225935/Coco-VS-Admiral-Swiggins', 'http://www.hentai-foundry.com/pictures/user/Sparrow/225472/Poon-Cellar', 'http://www.hentai-foundry.com/pictures/user/Sparrow/225063/Goal-Tending', 'http://www.hentai-foundry.com/pictures/user/Sparrow/223991/Coco-VS-StarStorm', 'http://www.hentai-foundry.com/pictures/user/Sparrow/221783/Gala-Event', 'http://www.hentai-foundry.com/pictures/user/Sparrow/221379/Linda-Rinda', 'http://www.hentai-foundry.com/pictures/user/Sparrow/220615/Farahs-Day-Off--27', 'http://www.hentai-foundry.com/pictures/user/Sparrow/219856/Viewing-Room-Workout', 'http://www.hentai-foundry.com/pictures/user/Sparrow/219284/Farahs-Day-Off--26', 'http://www.hentai-foundry.com/pictures/user/Sparrow/218886/Nyaow-Streaming', 'http://www.hentai-foundry.com/pictures/user/Sparrow/218035/Farahs-Day-Off--25', 'http://www.hentai-foundry.com/pictures/user/Sparrow/216981/A-Vivi-draws-near.-Command', 'http://www.hentai-foundry.com/pictures/user/Sparrow/216642/Farahs-Day-Off--24', 'http://www.hentai-foundry.com/pictures/user/Sparrow/215266/Farahs-Day-Off--23', 'http://www.hentai-foundry.com/pictures/user/Sparrow/213132/Relative-Risk', 'http://www.hentai-foundry.com/pictures/user/Sparrow/212665/Farahs-Day-Off--21', 'http://www.hentai-foundry.com/pictures/user/Sparrow/212282/Sticky-Sheva-Situation', 'http://www.hentai-foundry.com/pictures/user/Sparrow/211269/Farahs-Day-Off-20-2', 'http://www.hentai-foundry.com/pictures/user/Sparrow/211268/Farahs-Day-Off-20-1', 'http://www.hentai-foundry.com/pictures/user/Sparrow/211038/Newcomers', 'http://www.hentai-foundry.com/pictures/user/Sparrow/209967/Farahs-Day-Off-19', 'http://www.hentai-foundry.com/pictures/user/Sparrow/209292/The-New-Adventures-of-Helena-Lovelace-01', 'http://www.hentai-foundry.com/pictures/user/Sparrow/208609/Farahs-Day-Off--18', 'http://www.hentai-foundry.com/pictures/user/Sparrow/207979/Wonderful-Backlit-Foreign-Boyfriend-Experience' ]
        
        self.assertEqual( page_of_urls, expected_gallery_urls )
        self.assertFalse( definitely_no_more_pages )
        
        ( page_of_urls, definitely_no_more_pages ) = gallery_scraps.GetPage( 'Sparrow', 0 )
        
        expected_gallery_urls = [ 'http://www.hentai-foundry.com/pictures/user/Sparrow/226084/Swegabe-Sketches--Gabrielle-027', 'http://www.hentai-foundry.com/pictures/user/Sparrow/224103/Make-Trade', 'http://www.hentai-foundry.com/pictures/user/Sparrow/220618/Swegabe-Sketches--Gabrielle-020', 'http://www.hentai-foundry.com/pictures/user/Sparrow/216451/Bigger-Dipper', 'http://www.hentai-foundry.com/pictures/user/Sparrow/213985/Swegabe-Sketches--Gabrielle-008', 'http://www.hentai-foundry.com/pictures/user/Sparrow/211271/Swegabe-Sketches--Gabrielle-003', 'http://www.hentai-foundry.com/pictures/user/Sparrow/210311/Himari-Says-Hi', 'http://www.hentai-foundry.com/pictures/user/Sparrow/209971/Swegabe-Sketches--Gabrielle-002', 'http://www.hentai-foundry.com/pictures/user/Sparrow/209970/Swegabe-Sketches--Gabrielle-001', 'http://www.hentai-foundry.com/pictures/user/Sparrow/204463/Minobred-Overkill', 'http://www.hentai-foundry.com/pictures/user/Sparrow/203723/Single-File-Please', 'http://www.hentai-foundry.com/pictures/user/Sparrow/202593/Kneel-O-April', 'http://www.hentai-foundry.com/pictures/user/Sparrow/201296/McPie-2', 'http://www.hentai-foundry.com/pictures/user/Sparrow/195882/HANDLED', 'http://www.hentai-foundry.com/pictures/user/Sparrow/184275/Relative-Frequency', 'http://www.hentai-foundry.com/pictures/user/Sparrow/183458/Coco-VS-Voltar', 'http://www.hentai-foundry.com/pictures/user/Sparrow/183085/Coco-VS-Froggy-G', 'http://www.hentai-foundry.com/pictures/user/Sparrow/181508/Mystra-Meets-Mister-18', 'http://www.hentai-foundry.com/pictures/user/Sparrow/180699/Tunnel-Trouble', 'http://www.hentai-foundry.com/pictures/user/Sparrow/177549/Coco-VS-Leon', 'http://www.hentai-foundry.com/pictures/user/Sparrow/175824/The-Ladies-Boyle', 'http://www.hentai-foundry.com/pictures/user/Sparrow/168744/Coco-VS-Yuri', 'http://www.hentai-foundry.com/pictures/user/Sparrow/166167/VVVVViewtiful', 'http://www.hentai-foundry.com/pictures/user/Sparrow/165429/Walled', 'http://www.hentai-foundry.com/pictures/user/Sparrow/164936/Coco-VS-Lonestar' ]
        
        self.assertEqual( page_of_urls, expected_gallery_urls )
        self.assertFalse( definitely_no_more_pages )
        
        #
        
        HG.test_controller.GetHTTP().SetResponse( HC.GET, 'http://pictures.hentai-foundry.com//s/Sparrow/226304.jpg', 'picture' )
        HG.test_controller.GetHTTP().SetResponse( HC.GET, 'http://pictures.hentai-foundry.com//s/Sparrow/226084.jpg', 'scrap' )
        
        gallery = ClientDownloading.GalleryHentaiFoundry()
        
        # ask for specific url
        
        ( os_file_handle, temp_path ) = HydrusPaths.GetTempPath()
        
        try:
            
            tags = gallery.GetFileAndTags( temp_path, 'http://www.hentai-foundry.com/pictures/user/Sparrow/226304/Ashantae' )
            
            with open( temp_path, 'rb' ) as f: data = f.read()
            
        finally:
            
            HydrusPaths.CleanUpTempPath( os_file_handle, temp_path )
            
        
        info = ( data, tags )
        
        expected_info = ('picture', [u'creator:Sparrow', u'title:Ashantae!'])
        
        self.assertEqual( info, expected_info )
        
        ( os_file_handle, temp_path ) = HydrusPaths.GetTempPath()
        
        try:
            
            tags = gallery.GetFileAndTags( temp_path, 'http://www.hentai-foundry.com/pictures/user/Sparrow/226084/Swegabe-Sketches--Gabrielle-027' )
            
            with open( temp_path, 'rb' ) as f: data = f.read()
            
        finally:
            
            HydrusPaths.CleanUpTempPath( os_file_handle, temp_path )
            
        
        info = ( data, tags )
        
        expected_info = ('scrap', [u'creator:Sparrow', u'title:Swegabe Sketches \u2013 Gabrielle 027'])
        
        self.assertEqual( info, expected_info )
        
    
