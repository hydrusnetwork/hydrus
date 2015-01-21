import ClientConstants as CC
import collections
import HydrusConstants as HC
import HydrusDownloading
import os
import TestConstants
import unittest

class TestDownloaders( unittest.TestCase ):
    
    @classmethod
    def setUpClass( self ):
        
        self.old_http = HC.http
        
        HC.http = TestConstants.FakeHTTPConnectionManager()
        
    
    @classmethod
    def tearDownClass( self ):
        
        HC.http = self.old_http
        
        
    
    def test_deviantart( self ):
        
        with open( HC.STATIC_DIR + os.path.sep + 'testing' + os.path.sep + 'da_gallery.html' ) as f: da_gallery = f.read()
        with open( HC.STATIC_DIR + os.path.sep + 'testing' + os.path.sep + 'da_page.html' ) as f: da_page = f.read()
        
        HC.http.SetResponse( HC.GET, 'http://sakimichan.deviantart.com/gallery/?catpath=/&offset=0', da_gallery )
        HC.http.SetResponse( HC.GET, 'http://sakimichan.deviantart.com/art/Sailor-moon-in-PJs-506918040', da_page )
        
        HC.http.SetResponse( HC.GET, 'http://fc00.deviantart.net/fs71/f/2015/013/3/c/3c026edbe356b22c802e7be0db6fbd0b-d8dt0go.jpg', 'image file' )
        
        #
        
        downloader = HydrusDownloading.DownloaderDeviantArt( 'sakimichan' )
        
        #
        
        gallery_urls = downloader.GetAnotherPage()
        
        expected_gallery_urls = [('http://sakimichan.deviantart.com/art/Sailor-moon-in-PJs-506918040', ['title:Sailor moon in PJs', 'creator:sakimichan']), ('http://sakimichan.deviantart.com/art/Johnny-Bravo-505601401', ['title:Johnny Bravo', 'creator:sakimichan']), ('http://sakimichan.deviantart.com/art/Daphne-505394693', ['title:Daphne !', 'creator:sakimichan']), ('http://sakimichan.deviantart.com/art/kim-Possible-505195132', ['title:kim Possible', 'creator:sakimichan']), ('http://sakimichan.deviantart.com/art/Levi-s-evil-plan-504966437', ["title:Levi's evil plan", 'creator:sakimichan']), ('http://sakimichan.deviantart.com/art/Velma-504483448', ['title:Velma', 'creator:sakimichan']), ('http://sakimichan.deviantart.com/art/Scoobydoo-504238131', ['title:Scoobydoo', 'creator:sakimichan']), ('http://sakimichan.deviantart.com/art/Kerrigan-chilling-503477012', ['title:Kerrigan chilling', 'creator:sakimichan']), ('http://sakimichan.deviantart.com/art/Kiki-498525851', ['title:Kiki', 'creator:sakimichan']), ('http://sakimichan.deviantart.com/art/Waiter-Howl-502377515', ['title:Waiter Howl', 'creator:sakimichan']), ('http://sakimichan.deviantart.com/art/Modern-Loki-497985045', ['title:Modern Loki', 'creator:sakimichan']), ('http://sakimichan.deviantart.com/art/Emma-501919103', ['title:Emma', 'creator:sakimichan']), ('http://sakimichan.deviantart.com/art/Lola-494941222', ['title:Lola', 'creator:sakimichan']), ('http://sakimichan.deviantart.com/art/Elsas-501262184', ['title:Elsas', 'creator:sakimichan']), ('http://sakimichan.deviantart.com/art/Tsunade-499517356', ['title:Tsunade', 'creator:sakimichan']), ('http://sakimichan.deviantart.com/art/A-little-cold-out-commission-498326494', ['title:A little cold out(commission)', 'creator:sakimichan']), ('http://sakimichan.deviantart.com/art/Girl-496999831', ['title:Girl', 'creator:sakimichan']), ('http://sakimichan.deviantart.com/art/Green-elf-496797148', ['title:Green elf', 'creator:sakimichan']), ('http://sakimichan.deviantart.com/art/Itachi-496625357', ['title:Itachi', 'creator:sakimichan']), ('http://sakimichan.deviantart.com/art/Sesshomaru-495474394', ['title:Sesshomaru', 'creator:sakimichan']), ('http://sakimichan.deviantart.com/art/Mononoke-years-later-502160436', ['title:Mononoke years later', 'creator:sakimichan']), ('http://sakimichan.deviantart.com/art/Jinx-488513585', ['title:Jinx', 'creator:sakimichan']), ('http://sakimichan.deviantart.com/art/Alex-in-wonderland-485819661', ['title:Alex in wonderland', 'creator:sakimichan']), ('http://sakimichan.deviantart.com/art/Ariels-476991263', ['title:Ariels', 'creator:sakimichan'])]
        
        self.assertEqual( gallery_urls, expected_gallery_urls )
        
        #
        
        tags = ['title:Sailor moon in PJs', 'creator:sakimichan']
        
        info = downloader.GetFileAndTags( 'http://sakimichan.deviantart.com/art/Sailor-moon-in-PJs-506918040', tags )
        
        ( temp_path, tags ) = info
        
        with open( temp_path, 'rb' ) as f: data = f.read()
        
        info = ( data, tags )
        
        expected_info = ('image file', tags)
        
        self.assertEqual( info, expected_info )
        
    
    def test_newgrounds( self ):
        
        with open( HC.STATIC_DIR + os.path.sep + 'testing' + os.path.sep + 'newgrounds_gallery_games.html' ) as f: newgrounds_gallery_games = f.read()
        with open( HC.STATIC_DIR + os.path.sep + 'testing' + os.path.sep + 'newgrounds_gallery_movies.html' ) as f: newgrounds_gallery_movies = f.read()
        
        HC.http.SetResponse( HC.GET, 'http://warlord-of-noodles.newgrounds.com/games/', newgrounds_gallery_games )
        HC.http.SetResponse( HC.GET, 'http://warlord-of-noodles.newgrounds.com/movies/', newgrounds_gallery_movies )
        
        #
        
        downloader = HydrusDownloading.DownloaderNewgrounds( 'warlord-of-noodles' )
        
        #
        
        gallery_urls = downloader.GetAnotherPage()
        
        expected_gallery_urls = [('http://www.newgrounds.com/portal/view/621259',), ('http://www.newgrounds.com/portal/view/617915',), ('http://www.newgrounds.com/portal/view/612665',), ('http://www.newgrounds.com/portal/view/610813',), ('http://www.newgrounds.com/portal/view/609683',), ('http://www.newgrounds.com/portal/view/593806',), ('http://www.newgrounds.com/portal/view/606387',), ('http://www.newgrounds.com/portal/view/606111',), ('http://www.newgrounds.com/portal/view/604603',), ('http://www.newgrounds.com/portal/view/604152',), ('http://www.newgrounds.com/portal/view/603027',), ('http://www.newgrounds.com/portal/view/601680',), ('http://www.newgrounds.com/portal/view/600626',), ('http://www.newgrounds.com/portal/view/591049',), ('http://www.newgrounds.com/portal/view/583715',), ('http://www.newgrounds.com/portal/view/584272',), ('http://www.newgrounds.com/portal/view/577497',), ('http://www.newgrounds.com/portal/view/563780',), ('http://www.newgrounds.com/portal/view/562785',), ('http://www.newgrounds.com/portal/view/553298',), ('http://www.newgrounds.com/portal/view/550882',), ('http://www.newgrounds.com/portal/view/488200',), ('http://www.newgrounds.com/portal/view/509249',), ('http://www.newgrounds.com/portal/view/509175',), ('http://www.newgrounds.com/portal/view/488180',)]
        
        self.assertEqual( gallery_urls, expected_gallery_urls )
        
        #
        
        with open( HC.STATIC_DIR + os.path.sep + 'testing' + os.path.sep + 'newgrounds_page.html' ) as f: newgrounds_page = f.read()
        
        HC.http.SetResponse( HC.GET, 'http://www.newgrounds.com/portal/view/583715', newgrounds_page )
        
        HC.http.SetResponse( HC.GET, 'http://uploads.ungrounded.net/583000/583715_catdust.swf', 'swf file' )
        
        info = downloader.GetFileAndTags( 'http://www.newgrounds.com/portal/view/583715' )
        
        ( temp_path, tags ) = info
        
        with open( temp_path, 'rb' ) as f: data = f.read()
        
        info = ( data, tags )
        
        expected_info = ( 'swf file', set([u'chores', u'laser', u'silent', u'title:Cat Dust', u'creator:warlord-of-noodles', u'pointer']) )
        
        self.assertEqual( info, expected_info )
        
    
    def test_pixiv( self ):
        
        with open( HC.STATIC_DIR + os.path.sep + 'testing' + os.path.sep + 'pixiv_gallery.html' ) as f: pixiv_gallery = f.read()
        with open( HC.STATIC_DIR + os.path.sep + 'testing' + os.path.sep + 'pixiv_page.html' ) as f: pixiv_page = f.read()
        
        HC.http.SetResponse( HC.GET, 'http://www.pixiv.net/search.php?word=naruto&s_mode=s_tag_full&order=date_d&p=1', pixiv_gallery )
        HC.http.SetResponse( HC.GET, 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=43718605', pixiv_page )
        
        HC.http.SetResponse( HC.GET, 'http://i1.pixiv.net/img59/img/dbhope/43718605.jpg', 'image file' )
        
        #
        
        downloader = HydrusDownloading.DownloaderPixiv( 'tags', 'naruto' )
        
        #
        
        gallery_urls = downloader.GetAnotherPage()
        
        expected_gallery_urls = [ ( u'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=43718605', ), 'a bunch of others' ]
        
        self.assertEqual( gallery_urls[0], expected_gallery_urls[0] )
        
        #
        
        info = downloader.GetFileAndTags( 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=43718605' )
        
        ( temp_path, tags ) = info
        
        with open( temp_path, 'rb' ) as f: data = f.read()
        
        info = ( data, tags )
        
        expected_tags = [ u'1P\u6f2b\u753b', u'\u7720\u305f\u3044', u'NARUTO', u'\u30ca\u30eb\u30c8', u'\u30b5\u30b9\u30b1', u'\u30b5\u30af\u30e9', u'\u30d2\u30ca\u30bf', u'creator:\u30df\u30c4\u30ad\u30e8\u3063\u3057\uff5e', u'title:\u7720\u305f\u3044', 'creator:dbhope' ]
        
        expected_info = ( 'image file', expected_tags )
        
        self.assertEqual( info, expected_info )
        
    
    def test_sankaku( self ):
        
        with open( HC.STATIC_DIR + os.path.sep + 'testing' + os.path.sep + 'sankaku_gallery.html' ) as f: sankaku_gallery = f.read()
        with open( HC.STATIC_DIR + os.path.sep + 'testing' + os.path.sep + 'sankaku_page.html' ) as f: sankaku_page = f.read()
        
        HC.http.SetResponse( HC.GET, 'https://chan.sankakucomplex.com/?tags=animal_ears&page=1', sankaku_gallery )
        HC.http.SetResponse( HC.GET, 'https://chan.sankakucomplex.com/post/show/4324703', sankaku_page )
        
        #
        
        downloader = HydrusDownloading.DownloaderBooru( CC.DEFAULT_BOORUS[ 'sankaku chan' ], [ 'animal_ears' ] )
        
        #
        
        gallery_urls = downloader.GetAnotherPage()
        
        expected_gallery_urls = [(u'https://chan.sankakucomplex.com/post/show/4324703',), (u'https://chan.sankakucomplex.com/post/show/4324435',), (u'https://chan.sankakucomplex.com/post/show/4324426',), (u'https://chan.sankakucomplex.com/post/show/4324365',), (u'https://chan.sankakucomplex.com/post/show/4324343',), (u'https://chan.sankakucomplex.com/post/show/4324309',), (u'https://chan.sankakucomplex.com/post/show/4324134',), (u'https://chan.sankakucomplex.com/post/show/4324107',), (u'https://chan.sankakucomplex.com/post/show/4324095',), (u'https://chan.sankakucomplex.com/post/show/4324086',), (u'https://chan.sankakucomplex.com/post/show/4323969',), (u'https://chan.sankakucomplex.com/post/show/4323967',), (u'https://chan.sankakucomplex.com/post/show/4323665',), (u'https://chan.sankakucomplex.com/post/show/4323620',), (u'https://chan.sankakucomplex.com/post/show/4323586',), (u'https://chan.sankakucomplex.com/post/show/4323581',), (u'https://chan.sankakucomplex.com/post/show/4323580',), (u'https://chan.sankakucomplex.com/post/show/4323520',), (u'https://chan.sankakucomplex.com/post/show/4323512',), (u'https://chan.sankakucomplex.com/post/show/4323498',)]
        
        self.assertEqual( gallery_urls, expected_gallery_urls )
        
        #
        
        HC.http.SetResponse( HC.GET, 'https://cs.sankakucomplex.com/data/c5/c3/c5c3c91ca68bd7662f546cc44fe0d378.jpg?4324703', 'image file' )
        
        info = downloader.GetFileAndTags( 'https://chan.sankakucomplex.com/post/show/4324703' )
        
        ( temp_path, tags ) = info
        
        with open( temp_path, 'rb' ) as f: data = f.read()
        
        info = ( data, tags )
        
        expected_info = ('image file', [u'character:heinrike prinzessin zu sayn-wittgenstein', u'character:rosalie de hemricourt de grunne', u'2girls', u'alternative costume', u'anal beads', u'animal ears', u'anus', u'ass', u'ass cutout', u'backless panties', u'blonde', u'blue eyes', u'blush', u'braid', u'butt plug', u'butt plug tail', u'cameltoe', u'cat tail', u'cheerleader', u'dildo', u'fake animal ears', u'fang', u'green eyes', u'hands', u'happy', u'heart cutout', u'kneepits', u'long hair', u'looking at viewer', u'multiple girls', u'nekomimi', u'open mouth', u'pantsu', u'spread anus', u'sweat', u'tail', u'tape', u'underwear', u'white panties', u'creator:null (nyanpyoun)', u'series:strike witches'])
        
        self.assertEqual( info, expected_info )
        
        # flash is tricky for sankaku
        
        with open( HC.STATIC_DIR + os.path.sep + 'testing' + os.path.sep + 'sankaku_flash.html' ) as f: sankaku_flash = f.read()
        
        HC.http.SetResponse( HC.GET, 'https://chan.sankakucomplex.com/post/show/4318061', sankaku_flash )
        HC.http.SetResponse( HC.GET, 'https://cs.sankakucomplex.com/data/48/ce/48cecd707d8a562d47db74d934505f51.swf?4318061', 'swf file' )
        
        temp_path = downloader.GetFile( 'https://chan.sankakucomplex.com/post/show/4318061' )
        
        with open( temp_path, 'rb' ) as f: data = f.read()
        
        self.assertEqual( data, 'swf file' )
        
    
    def test_booru_e621( self ):
        
        with open( HC.STATIC_DIR + os.path.sep + 'testing' + os.path.sep + 'e621_gallery.html' ) as f: e621_gallery = f.read()
        with open( HC.STATIC_DIR + os.path.sep + 'testing' + os.path.sep + 'e621_page.html' ) as f: e621_page = f.read()
        
        HC.http.SetResponse( HC.GET, 'http://e621.net/post/index?page=1&tags=flash', e621_gallery )
        HC.http.SetResponse( HC.GET, 'http://e621.net/post/show/360338/2013-3_toes-anal-anal_penetration-animated-argonia', e621_page )
        
        #
        
        downloader = HydrusDownloading.DownloaderBooru( CC.DEFAULT_BOORUS[ 'e621' ], [ 'flash' ] )
        
        #
        
        gallery_urls = downloader.GetAnotherPage()
        
        expected_gallery_urls = [(u'http://e621.net/post/show/360338/2013-3_toes-anal-anal_penetration-animated-argonia',), (u'http://e621.net/post/show/359813/2013-abdominal_bulge-ambiguous_gender-amwulf-anal-',), (u'http://e621.net/post/show/359715/animated-avian-bird-bukkake-chirpy-cum-cum_everywh',), (u'http://e621.net/post/show/359711/animated-avian-bird-bukkake-chirpy-cum-cum_everywh',), (u'http://e621.net/post/show/359684/after_sex-animated-anthro-areola-breasts-cat-cum_e',), (u'http://e621.net/post/show/359303/abs-adam_wan-alcohol-anal-animated-anklet-antlers-',), (u'http://e621.net/post/show/359234/anal-animated-cat-cub-feline-flash-gay-lagomorph-m',), (u'http://e621.net/post/show/358988/2013-animated-blue_eyes-blue_hair-bonbon_-mlp-book',), (u'http://e621.net/post/show/358732/all_fours-anal-animated-anus-balls-bent_over-black',), (u'http://e621.net/post/show/358416/3d-alien-animated-black_eyes-cameltoe_slide-chubby',), (u'http://e621.net/post/show/358367/animated-butt-coco_bandicoot-cosplay-cute-flash-lo',), (u'http://e621.net/post/show/358140/3d-animated-cum-cum_in_pussy-cum_inside-das-doggys',), (u'http://e621.net/post/show/357912/animated-anthro-big_breasts-breasts-cat-cum-cum_in',), (u'http://e621.net/post/show/356813/amazing-animated-bear-bikini-breasts-cephalopod-ce',), (u'http://e621.net/post/show/356583/aircraft-airplane-animated-anime-canine-cat-cloud-',), (u'http://e621.net/post/show/356515/3d-alien-animated-autofellatio-black_eyes-chubby-c',), (u'http://e621.net/post/show/355999/animated-balls-claws-cum-cum_in_mouth-cum_on_face-',), (u'http://e621.net/post/show/355265/abdominal_bulge-animated-areola-balls-big_breasts-',), (u'http://e621.net/post/show/355159/3d-animated-cunnilingus-duo-erection-eye_contact-e',), (u'http://e621.net/post/show/355087/2013-animated-anthro-anthrofied-antler-balls-blue_',), (u'http://e621.net/post/show/354998/animated-equine-flash-fluttershy_-mlp-friendship_i',), (u'http://e621.net/post/show/354942/animated-baddoganimations-balls-battle_angel-big_b',), (u'http://e621.net/post/show/354906/animated-censor_bar-censored-crossgender-dickgirl-',), (u'http://e621.net/post/show/354602/animated-baddoganimations-big_breasts-breasts-dick',), (u'http://e621.net/post/show/354597/anal-anal_penetration-animated-baddoganimations-bi',), (u'http://e621.net/post/show/354090/2013-3_toes-anal-anal_penetration-animated-arms_be',), (u'http://e621.net/post/show/354042/16-9-2012-2013-abs-adam_wan-alcohol-animated-ankle',), (u'http://e621.net/post/show/353861/alligator-animated-applejack_-mlp-cat-derpy_hooves',), (u'http://e621.net/post/show/353800/3_toes-3d-animated-balls-bayleef-cgi-cum-cum_infla',), (u'http://e621.net/post/show/353254/alcohol-amphibian-animated-beverage-candles-canine',), (u'http://e621.net/post/show/353140/2013-animated-blue_fur-crossgender-cum-cum_in_hair',), (u'http://e621.net/post/show/352892/anal-animated-breasts-butt-english_text-female-fis',), (u'http://e621.net/post/show/352800/abs-after_sex-alcohol-amily_-coc-anal-anal_penetra',), (u'http://e621.net/post/show/352670/2013-abs-adult-animated-anthro-balls-biceps-big_pe',), (u'http://e621.net/post/show/352394/2013-anal-anal_penetration-animated-avian-balls-ba',), (u'http://e621.net/post/show/352303/animated-breasts-butt-cunnilingus-dark_skin-dialog',), (u'http://e621.net/post/show/352044/2013-4_toes-animated-arm_support-barefoot-black_no',), (u'http://e621.net/post/show/351504/2013-animated-avian-big_breasts-bike_shorts-bird-b',), (u'http://e621.net/post/show/351409/2013-animated-black_fur-blue_hair-cutie_mark-death',), (u'http://e621.net/post/show/351372/-animated-big-big_muffintosh-blue_background-blush',), (u'http://e621.net/post/show/351360/anal-anal_penetration-animated-anthro-autofellatio',), (u'http://e621.net/post/show/351238/2013-3d-animated-balls-big_balls-black_fur-blue_ey',), (u'http://e621.net/post/show/350992/animated-antlers-basket-bottle-bush-canine-clothin',), (u'http://e621.net/post/show/350989/3d-animated-bed-bestiality-black_fur-breasts-build',), (u'http://e621.net/post/show/350548/animated-balls-bed-canine-erection-flash-humbuged-',)]
        
        self.assertEqual( gallery_urls, expected_gallery_urls )
        
        #
        
        HC.http.SetResponse( HC.GET, 'https://static1.e621.net/data/f5/48/f54897c2543e0264e1a64d7f7c33c9f9.swf', 'swf file' )
        
        info = downloader.GetFileAndTags( 'http://e621.net/post/show/360338/2013-3_toes-anal-anal_penetration-animated-argonia' )
        
        ( temp_path, tags ) = info
        
        with open( temp_path, 'rb' ) as f: data = f.read()
        
        info = ( data, tags )
        
        expected_info = ('swf file', [u'creator:jasonafex', u'creator:kabier', u'2013', u'3 toes', u'anal', u'anal penetration', u'animated', u'balls', u'barefoot', u'bed', u'bedroom', u'biceps', u'blue skin', u'butt', u'claws', u'clock', u'collaboration', u'couple', u'cum', u'cum in ass', u'cum inside', u'cyan skin', u'erection', u'flash', u'gay', u'green eyes', u'hairless', u'hand holding', u'happy sex', u'hi res', u'horn', u'humanoid penis', u'lamp', u'licking', u'lying', u'male', u'missionary position', u'muscles', u'night', u'on back', u'open mouth', u'paws', u'penetration', u'penis', u'raised leg', u'red penis', u'red skin', u'room', u'saliva', u'sharp teeth', u'side view', u'stripes', u'teeth', u'thick thighs', u'tongue', u'video games', u'wood', u'yellow sclera', u'series:the elder scrolls', u'species:argonian', u'species:dragon', u'species:scalie', u'character:spyke'])
        
        self.assertEqual( info, expected_info )
        
    
    def test_hentai_foundry( self ):
        
        with open( HC.STATIC_DIR + os.path.sep + 'testing' + os.path.sep + 'hf_picture_gallery.html' ) as f: picture_gallery = f.read()
        with open( HC.STATIC_DIR + os.path.sep + 'testing' + os.path.sep + 'hf_scrap_gallery.html' ) as f: scrap_gallery = f.read()
        with open( HC.STATIC_DIR + os.path.sep + 'testing' + os.path.sep + 'hf_picture_page.html' ) as f: picture_page = f.read()
        with open( HC.STATIC_DIR + os.path.sep + 'testing' + os.path.sep + 'hf_scrap_page.html' ) as f: scrap_page = f.read()
        
        # what about page/1 or whatever?
        
        HC.http.SetResponse( HC.GET, 'http://www.hentai-foundry.com/pictures/user/Sparrow/page/1', picture_gallery )
        HC.http.SetResponse( HC.GET, 'http://www.hentai-foundry.com/pictures/user/Sparrow/scraps/page/1', scrap_gallery )
        HC.http.SetResponse( HC.GET, 'http://www.hentai-foundry.com/pictures/user/Sparrow/226304/Ashantae', picture_page )
        HC.http.SetResponse( HC.GET, 'http://www.hentai-foundry.com/pictures/user/Sparrow/226084/Swegabe-Sketches--Gabrielle-027', scrap_page )
        
        cookies = { 'YII_CSRF_TOKEN' : '19b05b536885ec60b8b37650a32f8deb11c08cd1s%3A40%3A%222917dcfbfbf2eda2c1fbe43f4d4c4ec4b6902b32%22%3B' }
        
        HC.app.SetWebCookies( 'hentai foundry', cookies )
        
        #
        
        info = {}
        
        info[ 'rating_nudity' ] = 3
        info[ 'rating_violence' ] = 3
        info[ 'rating_profanity' ] = 3
        info[ 'rating_racism' ] = 3
        info[ 'rating_sex' ] = 3
        info[ 'rating_spoilers' ] = 3
        
        info[ 'rating_yaoi' ] = 1
        info[ 'rating_yuri' ] = 1
        info[ 'rating_teen' ] = 1
        info[ 'rating_guro' ] = 1
        info[ 'rating_furry' ] = 1
        info[ 'rating_beast' ] = 1
        info[ 'rating_male' ] = 1
        info[ 'rating_female' ] = 1
        info[ 'rating_futa' ] = 1
        info[ 'rating_other' ] = 1
        
        info[ 'filter_media' ] = 'A'
        info[ 'filter_order' ] = 0
        info[ 'filter_type' ] = 0
        
        pictures_downloader = HydrusDownloading.GetDownloader( HC.SITE_TYPE_HENTAI_FOUNDRY, 'artist pictures', 'Sparrow', info )
        scraps_downloader = HydrusDownloading.GetDownloader( HC.SITE_TYPE_HENTAI_FOUNDRY, 'artist scraps', 'Sparrow', info )
        
        #
        
        gallery_urls = pictures_downloader.GetAnotherPage()
        
        expected_gallery_urls = [('http://www.hentai-foundry.com/pictures/user/Sparrow/226304/Ashantae',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/225935/Coco-VS-Admiral-Swiggins',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/225472/Poon-Cellar',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/225063/Goal-Tending',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/223991/Coco-VS-StarStorm',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/221783/Gala-Event',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/221379/Linda-Rinda',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/220615/Farahs-Day-Off--27',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/219856/Viewing-Room-Workout',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/219284/Farahs-Day-Off--26',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/218886/Nyaow-Streaming',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/218035/Farahs-Day-Off--25',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/216981/A-Vivi-draws-near.-Command',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/216642/Farahs-Day-Off--24',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/215266/Farahs-Day-Off--23',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/213132/Relative-Risk',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/212665/Farahs-Day-Off--21',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/212282/Sticky-Sheva-Situation',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/211269/Farahs-Day-Off-20-2',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/211268/Farahs-Day-Off-20-1',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/211038/Newcomers',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/209967/Farahs-Day-Off-19',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/209292/The-New-Adventures-of-Helena-Lovelace-01',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/208609/Farahs-Day-Off--18',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/207979/Wonderful-Backlit-Foreign-Boyfriend-Experience',)]
        
        self.assertEqual( gallery_urls, expected_gallery_urls )
        
        gallery_urls = scraps_downloader.GetAnotherPage()
        
        expected_gallery_urls = [('http://www.hentai-foundry.com/pictures/user/Sparrow/226084/Swegabe-Sketches--Gabrielle-027',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/224103/Make-Trade',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/220618/Swegabe-Sketches--Gabrielle-020',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/216451/Bigger-Dipper',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/213985/Swegabe-Sketches--Gabrielle-008',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/211271/Swegabe-Sketches--Gabrielle-003',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/210311/Himari-Says-Hi',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/209971/Swegabe-Sketches--Gabrielle-002',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/209970/Swegabe-Sketches--Gabrielle-001',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/204463/Minobred-Overkill',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/203723/Single-File-Please',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/202593/Kneel-O-April',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/201296/McPie-2',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/195882/HANDLED',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/184275/Relative-Frequency',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/183458/Coco-VS-Voltar',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/183085/Coco-VS-Froggy-G',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/181508/Mystra-Meets-Mister-18',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/180699/Tunnel-Trouble',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/177549/Coco-VS-Leon',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/175824/The-Ladies-Boyle',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/168744/Coco-VS-Yuri',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/166167/VVVVViewtiful',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/165429/Walled',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/164936/Coco-VS-Lonestar',)]
        
        self.assertEqual( gallery_urls, expected_gallery_urls )
        
        #
        
        HC.http.SetResponse( HC.GET, 'http://pictures.hentai-foundry.com//s/Sparrow/226304.jpg', 'picture' )
        HC.http.SetResponse( HC.GET, 'http://pictures.hentai-foundry.com//s/Sparrow/226084.jpg', 'scrap' )
        
        # ask for specific url
        
        info = pictures_downloader.GetFileAndTags( 'http://www.hentai-foundry.com/pictures/user/Sparrow/226304/Ashantae' )
        
        ( temp_path, tags ) = info
        
        with open( temp_path, 'rb' ) as f: data = f.read()
        
        info = ( data, tags )
        
        expected_info = ('picture', [u'creator:Sparrow', u'title:Ashantae!', u'Shantae', u'Asha', u'Monster_World', u'cosplay', u'nips'])
        
        self.assertEqual( info, expected_info )
        
        info = scraps_downloader.GetFileAndTags( 'http://www.hentai-foundry.com/pictures/user/Sparrow/226084/Swegabe-Sketches--Gabrielle-027' )
        
        ( temp_path, tags ) = info
        
        with open( temp_path, 'rb' ) as f: data = f.read()
        
        info = ( data, tags )
        
        expected_info = ('scrap', [u'creator:Sparrow', u'title:Swegabe Sketches \u2013 Gabrielle 027', u'bukkake', u'horsecock', u'gokkun', u'prom_night'])
        
        self.assertEqual( info, expected_info )
        
    