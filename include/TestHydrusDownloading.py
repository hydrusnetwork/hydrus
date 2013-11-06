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
        
        HC.get_connection = TestConstants.fake_http_connection_manager.GetConnection
        
    
    @classmethod
    def tearDownClass( self ):
        
        HC.get_connection = HC.AdvancedHTTPConnection
        
    
    def test_deviantart( self ):
        
        with open( HC.STATIC_DIR + os.path.sep + 'testing' + os.path.sep + 'da_gallery.html' ) as f: da_gallery = f.read()
        with open( HC.STATIC_DIR + os.path.sep + 'testing' + os.path.sep + 'da_page.html' ) as f: da_page = f.read()
        
        fake_connection = TestConstants.FakeHTTPConnection( host = 'sakimichan.deviantart.com' )
        
        fake_connection.SetResponse( 'GET', '/gallery/?catpath=/&offset=0', da_gallery )
        fake_connection.SetResponse( 'GET', '/art/Thumbs-up-411079893', da_page )
        
        TestConstants.fake_http_connection_manager.SetConnection( fake_connection, host = 'sakimichan.deviantart.com' )
        
        fake_connection = TestConstants.FakeHTTPConnection( host = 'fc04.deviantart.net' )
        
        fake_connection.SetResponse( 'GET', '/fs70/f/2013/306/1/5/thumbs_up_by_sakimichan-d6sqv9x.jpg', 'image file' )
        
        TestConstants.fake_http_connection_manager.SetConnection( fake_connection, host = 'fc04.deviantart.net' )
        
        #
        
        downloader = HydrusDownloading.DownloaderDeviantArt( 'sakimichan' )
        
        #
        
        gallery_urls = downloader.GetAnotherPage()
        
        expected_gallery_urls = [('http://sakimichan.deviantart.com/art/Thumbs-up-411079893', ['title:Thumbs up', 'creator:akimichan', 'Digital Art', 'Drawings & Paintings', 'Sci-Fi']), ('http://sakimichan.deviantart.com/art/The-Major-405852926', ['title:The Major', 'creator:akimichan', 'Fan Art', 'Cartoons & Comics', 'Digital', 'Movies & TV']), ('http://sakimichan.deviantart.com/art/Little-mermaid-fearie-401197163', ['title:Little mermaid fearie', 'creator:akimichan', 'Digital Art', 'Drawings & Paintings', 'Fantasy']), ('http://sakimichan.deviantart.com/art/Get-Em-Boy-or-not-399250537', ['title:Get Em Boy..or not', 'creator:akimichan', 'Digital Art', 'Drawings & Paintings', 'Fantasy']), ('http://sakimichan.deviantart.com/art/Welcome-To-The-Gang-398381756', ['title:Welcome To The Gang', 'creator:akimichan', 'Digital Art', 'Drawings & Paintings', 'Fantasy']), ('http://sakimichan.deviantart.com/art/Sci-Fi-Elf-398195577', ['title:Sci-Fi Elf', 'creator:akimichan', 'Digital Art', 'Drawings & Paintings', 'Sci-Fi']), ('http://sakimichan.deviantart.com/art/Ahri-391295844', ['title:Ahri', 'creator:akimichan', 'Fan Art', 'Cartoons & Comics', 'Digital', 'Games']), ('http://sakimichan.deviantart.com/art/Orphan-386257383', ['title:Orphan', 'creator:akimichan', 'Manga & Anime', 'Digital Media', 'Drawings']), ('http://sakimichan.deviantart.com/art/The-summon-385996679', ['title:The summon', 'creator:akimichan', 'Digital Art', 'Drawings & Paintings', 'Fantasy']), ('http://sakimichan.deviantart.com/art/Rainbow2-377174679', ['title:Rainbow2', 'creator:akimichan', 'Manga & Anime', 'Digital Media', 'Drawings']), ('http://sakimichan.deviantart.com/art/Sword-Art-online-378517412', ['title:Sword Art online', 'creator:akimichan', 'Fan Art', 'Cartoons & Comics', 'Digital', 'Movies & TV']), ('http://sakimichan.deviantart.com/art/Adventure-Time-Group-photo-371913392', ['title:Adventure Time Group photo', 'creator:akimichan', 'Fan Art', 'Cartoons & Comics', 'Digital', 'Movies & TV']), ('http://sakimichan.deviantart.com/art/resurrection-353827147', ['title:resurrection', 'creator:akimichan', 'Digital Art', 'Drawings & Paintings', 'Fantasy']), ('http://sakimichan.deviantart.com/art/playful-Snow-Harpy-343275265', ['title:playful Snow Harpy', 'creator:akimichan', 'Digital Art', 'Drawings & Paintings', 'Fantasy']), ('http://sakimichan.deviantart.com/art/Link-369553015', ['title:Link', 'creator:akimichan', 'Fan Art', 'Digital Art', 'Painting & Airbrushing', 'Games']), ('http://sakimichan.deviantart.com/art/Dc-girls-363385250', ['title:Dc girls', 'creator:akimichan', 'Digital Art', 'Drawings & Paintings', 'Fantasy']), ('http://sakimichan.deviantart.com/art/Running-With-Spirits-337981944', ['title:Running With Spirits', 'creator:akimichan', 'Digital Art', 'Drawings & Paintings', 'Fantasy']), ('http://sakimichan.deviantart.com/art/FMA-358647977', ['title:FMA', 'creator:akimichan', 'Fan Art', 'Cartoons & Comics', 'Digital', 'Movies & TV']), ('http://sakimichan.deviantart.com/art/Wonder-woman-347864644', ['title:Wonder woman', 'creator:akimichan', 'Fan Art', 'Cartoons & Comics', 'Digital', 'Movies & TV']), ('http://sakimichan.deviantart.com/art/Ariel-found-Headphones-341927000', ['title:Ariel found Headphones', 'creator:akimichan', 'Fan Art', 'Cartoons & Comics', 'Digital', 'Movies & TV']), ('http://sakimichan.deviantart.com/art/Jack-Frost-340925669', ['title:Jack Frost', 'creator:akimichan', 'Fan Art', 'Cartoons & Comics', 'Digital', 'Movies & TV']), ('http://sakimichan.deviantart.com/art/Musics-blooming-336308163', ['title:Musics blooming', 'creator:akimichan', 'Digital Art', 'Drawings', 'Fantasy']), ('http://sakimichan.deviantart.com/art/Yin-Yang-Goddess-327641961', ['title:Yin Yang Goddess', 'creator:akimichan', 'Digital Art', 'Drawings & Paintings', 'Fantasy']), ('http://sakimichan.deviantart.com/art/Angelof-Justice-322844340', ['title:Angelof Justice', 'creator:akimichan', 'Digital Art', 'Drawings & Paintings', 'Fantasy'])]
        
        self.assertEqual( gallery_urls, expected_gallery_urls )
        
        #
        
        tags = ['title:Thumbs up', 'creator:akimichan', 'Digital Art', 'Drawings & Paintings', 'Sci-Fi']
        
        info = downloader.GetFileAndTags( 'http://sakimichan.deviantart.com/art/Thumbs-up-411079893', tags )
        
        ( temp_path, tags ) = info
        
        with open( temp_path, 'rb' ) as f: data = f.read()
        
        info = ( data, tags )
        
        expected_info = ('image file', tags)
        
        self.assertEqual( info, expected_info )
        
    
    def test_newgrounds( self ):
        
        with open( HC.STATIC_DIR + os.path.sep + 'testing' + os.path.sep + 'newgrounds_gallery_games.html' ) as f: newgrounds_gallery_games = f.read()
        with open( HC.STATIC_DIR + os.path.sep + 'testing' + os.path.sep + 'newgrounds_gallery_movies.html' ) as f: newgrounds_gallery_movies = f.read()
        
        fake_connection = TestConstants.FakeHTTPConnection( host = 'warlord-of-noodles.newgrounds.com' )
        
        fake_connection.SetResponse( 'GET', '/games/', newgrounds_gallery_games )
        fake_connection.SetResponse( 'GET', '/movies/', newgrounds_gallery_movies )
        
        TestConstants.fake_http_connection_manager.SetConnection( fake_connection, host = 'warlord-of-noodles.newgrounds.com' )
        
        #
        
        downloader = HydrusDownloading.DownloaderNewgrounds( 'warlord-of-noodles' )
        
        #
        
        gallery_urls = downloader.GetAnotherPage()
        
        expected_gallery_urls = [('http://www.newgrounds.com/portal/view/621259',), ('http://www.newgrounds.com/portal/view/617915',), ('http://www.newgrounds.com/portal/view/612665',), ('http://www.newgrounds.com/portal/view/610813',), ('http://www.newgrounds.com/portal/view/609683',), ('http://www.newgrounds.com/portal/view/593806',), ('http://www.newgrounds.com/portal/view/606387',), ('http://www.newgrounds.com/portal/view/606111',), ('http://www.newgrounds.com/portal/view/604603',), ('http://www.newgrounds.com/portal/view/604152',), ('http://www.newgrounds.com/portal/view/603027',), ('http://www.newgrounds.com/portal/view/601680',), ('http://www.newgrounds.com/portal/view/600626',), ('http://www.newgrounds.com/portal/view/591049',), ('http://www.newgrounds.com/portal/view/583715',), ('http://www.newgrounds.com/portal/view/584272',), ('http://www.newgrounds.com/portal/view/577497',), ('http://www.newgrounds.com/portal/view/563780',), ('http://www.newgrounds.com/portal/view/562785',), ('http://www.newgrounds.com/portal/view/553298',), ('http://www.newgrounds.com/portal/view/550882',), ('http://www.newgrounds.com/portal/view/488200',), ('http://www.newgrounds.com/portal/view/509249',), ('http://www.newgrounds.com/portal/view/509175',), ('http://www.newgrounds.com/portal/view/488180',)]
        
        self.assertEqual( gallery_urls, expected_gallery_urls )
        
        #
        
        with open( HC.STATIC_DIR + os.path.sep + 'testing' + os.path.sep + 'newgrounds_page.html' ) as f: newgrounds_page = f.read()
        
        fake_connection = TestConstants.FakeHTTPConnection( host = 'www.newgrounds.com' )
        
        fake_connection.SetResponse( 'GET', '/portal/view/583715', newgrounds_page )
        
        TestConstants.fake_http_connection_manager.SetConnection( fake_connection, host = 'www.newgrounds.com' )
        
        fake_connection = TestConstants.FakeHTTPConnection( host = 'uploads.ungrounded.net' )
        
        fake_connection.SetResponse( 'GET', '/583000/583715_catdust.swf', 'swf file' )
        
        TestConstants.fake_http_connection_manager.SetConnection( fake_connection, host = 'uploads.ungrounded.net' )
        
        info = downloader.GetFileAndTags( 'http://www.newgrounds.com/portal/view/583715' )
        
        ( temp_path, tags ) = info
        
        with open( temp_path, 'rb' ) as f: data = f.read()
        
        info = ( data, tags )
        
        expected_info = ('swf file', set([u'chores', u'laser', u'silent', u'title:Cat Dust', u'creator:warlord-of-noodles', u'pointer']))
        
        self.assertEqual( info, expected_info )
        
    
    def test_booru_e621( self ):
        
        with open( HC.STATIC_DIR + os.path.sep + 'testing' + os.path.sep + 'e621_gallery.html' ) as f: e621_gallery = f.read()
        with open( HC.STATIC_DIR + os.path.sep + 'testing' + os.path.sep + 'e621_page.html' ) as f: e621_page = f.read()
        
        fake_connection = TestConstants.FakeHTTPConnection( host = 'e621.net' )
        
        fake_connection.SetResponse( 'GET', '/post/index?page=1&tags=flash', e621_gallery )
        fake_connection.SetResponse( 'GET', '/post/show/360338/2013-3_toes-anal-anal_penetration-animated-argonia', e621_page )
        
        TestConstants.fake_http_connection_manager.SetConnection( fake_connection, host = 'e621.net' )
        
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
        
        fake_connection = TestConstants.FakeHTTPConnection( host = 'www.hentai-foundry.com' )
        
        # what about page/1 or whatever?
        
        fake_connection.SetResponse( 'GET', '/pictures/user/Sparrow/page/1', picture_gallery )
        fake_connection.SetResponse( 'GET', '/pictures/user/Sparrow/scraps/page/1', scrap_gallery )
        fake_connection.SetResponse( 'GET', '/pictures/user/Sparrow/226304/Ashantae', picture_page )
        fake_connection.SetResponse( 'GET', '/pictures/user/Sparrow/226084/Swegabe-Sketches--Gabrielle-027', scrap_page )
        
        TestConstants.fake_http_connection_manager.SetConnection( fake_connection, host = 'www.hentai-foundry.com' )
        
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
        info[ 'rating_loli' ] = 1
        info[ 'rating_shota' ] = 1
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
        
        pictures_downloader = HydrusDownloading.GetDownloader( HC.SITE_DOWNLOAD_TYPE_HENTAI_FOUNDRY, 'artist pictures', 'Sparrow', info )
        scraps_downloader = HydrusDownloading.GetDownloader( HC.SITE_DOWNLOAD_TYPE_HENTAI_FOUNDRY, 'artist scraps', 'Sparrow', info )
        
        #
        
        gallery_urls = pictures_downloader.GetAnotherPage()
        
        expected_gallery_urls = [('http://www.hentai-foundry.com/pictures/user/Sparrow/226304/Ashantae',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/225935/Coco-VS-Admiral-Swiggins',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/225472/Poon-Cellar',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/225063/Goal-Tending',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/223991/Coco-VS-StarStorm',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/221783/Gala-Event',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/221379/Linda-Rinda',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/220615/Farahs-Day-Off--27',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/219856/Viewing-Room-Workout',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/219284/Farahs-Day-Off--26',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/218886/Nyaow-Streaming',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/218035/Farahs-Day-Off--25',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/216981/A-Vivi-draws-near.-Command',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/216642/Farahs-Day-Off--24',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/215266/Farahs-Day-Off--23',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/213132/Relative-Risk',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/212665/Farahs-Day-Off--21',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/212282/Sticky-Sheva-Situation',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/211269/Farahs-Day-Off-20-2',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/211268/Farahs-Day-Off-20-1',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/211038/Newcomers',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/209967/Farahs-Day-Off-19',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/209292/The-New-Adventures-of-Helena-Lovelace-01',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/208609/Farahs-Day-Off--18',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/207979/Wonderful-Backlit-Foreign-Boyfriend-Experience',)]
        
        self.assertEqual( gallery_urls, expected_gallery_urls )
        
        gallery_urls = scraps_downloader.GetAnotherPage()
        
        expected_gallery_urls = [('http://www.hentai-foundry.com/pictures/user/Sparrow/226084/Swegabe-Sketches--Gabrielle-027',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/224103/Make-Trade',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/220618/Swegabe-Sketches--Gabrielle-020',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/216451/Bigger-Dipper',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/213985/Swegabe-Sketches--Gabrielle-008',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/211271/Swegabe-Sketches--Gabrielle-003',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/210311/Himari-Says-Hi',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/209971/Swegabe-Sketches--Gabrielle-002',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/209970/Swegabe-Sketches--Gabrielle-001',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/204463/Minobred-Overkill',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/203723/Single-File-Please',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/202593/Kneel-O-April',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/201296/McPie-2',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/195882/HANDLED',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/184275/Relative-Frequency',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/183458/Coco-VS-Voltar',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/183085/Coco-VS-Froggy-G',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/181508/Mystra-Meets-Mister-18',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/180699/Tunnel-Trouble',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/177549/Coco-VS-Leon',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/175824/The-Ladies-Boyle',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/168744/Coco-VS-Yuri',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/166167/VVVVViewtiful',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/165429/Walled',), ('http://www.hentai-foundry.com/pictures/user/Sparrow/164936/Coco-VS-Lonestar',)]
        
        self.assertEqual( gallery_urls, expected_gallery_urls )
        
        #
        
        fake_connection = TestConstants.FakeHTTPConnection( host = 'pictures.hentai-foundry.com' )
        
        fake_connection.SetResponse( 'GET', '//s/Sparrow/226304.jpg', 'picture' )
        fake_connection.SetResponse( 'GET', '//s/Sparrow/226084.jpg', 'scrap' )
        
        TestConstants.fake_http_connection_manager.SetConnection( fake_connection, host = 'pictures.hentai-foundry.com' )
        
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
        
    