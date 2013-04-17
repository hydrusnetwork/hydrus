import bs4
import HydrusConstants as HC
import json
import lxml
import traceback
import urllib
import urlparse
import wx

def ConvertServiceIdentifiersToTagsToContentUpdates( hash, service_identifiers_to_tags ):
    
    content_updates = []
    
    for ( service_identifier, tags ) in service_identifiers_to_tags.items():
        
        if len( tags ) > 0:
            
            if service_identifier == HC.LOCAL_TAG_SERVICE_IDENTIFIER: action = HC.CONTENT_UPDATE_ADD
            else: action = HC.CONTENT_UPDATE_PENDING
            
            edit_log = [ ( action, tag ) for tag in tags ]
            
            content_updates.append( HC.ContentUpdate( HC.CONTENT_UPDATE_EDIT_LOG, service_identifier, ( hash, ), info = edit_log ) )
            
        
    
    return content_updates
    
def GetDownloader( site_download_type, *args ):
    
    if site_download_type == HC.SITE_DOWNLOAD_TYPE_BOORU: c = DownloaderBooru
    elif site_download_type == HC.SITE_DOWNLOAD_TYPE_DEVIANT_ART: c = DownloaderDeviantArt
    elif site_download_type == HC.SITE_DOWNLOAD_TYPE_GIPHY: c = DownloaderGiphy
    elif site_download_type == HC.SITE_DOWNLOAD_TYPE_HENTAI_FOUNDRY: c = DownloaderHentaiFoundry
    elif site_download_type == HC.SITE_DOWNLOAD_TYPE_PIXIV: c = DownloaderPixiv
    elif site_download_type == HC.SITE_DOWNLOAD_TYPE_TUMBLR: c = DownloaderTumblr
    
    return c( *args )
    
def ConvertTagsToServiceIdentifiersToTags( tags, advanced_tag_options ):
    
    tags = [ tag for tag in tags if tag is not None ]
    
    service_identifiers_to_tags = {}
    
    for ( service_identifier, namespaces ) in advanced_tag_options.items():
        
        if len( namespaces ) > 0:
            
            tags_to_add_here = []
            
            for namespace in namespaces:
                
                if namespace == '': tags_to_add_here.extend( [ HC.CleanTag( tag ) for tag in tags if not ':' in tag ] )
                else: tags_to_add_here.extend( [ HC.CleanTag( tag ) for tag in tags if tag.startswith( namespace + ':' ) ] )
                
            
            if len( tags_to_add_here ) > 0: service_identifiers_to_tags[ service_identifier ] = tags_to_add_here
            
        
    
    return service_identifiers_to_tags
    
class Downloader():
    
    def __init__( self ):
        
        self._we_are_done = False
        
        self._connections = {}
        
        self._all_urls_so_far = set()
        
        self._num_pages_done = 0
        
        example_url = self._GetNextGalleryPageURL()
        
    
    def _EstablishSession( self, connection ): pass
    
    def _GetConnection( self, url ):
        
        parse_result = urlparse.urlparse( url )
        
        ( scheme, host, port ) = ( parse_result.scheme, parse_result.hostname, parse_result.port )
        
        if ( scheme, host, port ) not in self._connections:
            
            connection = HC.AdvancedHTTPConnection( scheme = scheme, host = host, port = port )
            
            self._EstablishSession( connection )
            
            self._connections[ ( scheme, host, port ) ] = connection
            
        
        return self._connections[ ( scheme, host, port ) ]
        
    
    def GetAnotherPage( self ):
        
        if self._we_are_done: return []
        
        url = self._GetNextGalleryPageURL()
        
        connection = self._GetConnection( url )
        
        data = connection.geturl( url )
        
        url_info = self._ParseGalleryPage( data, url )
        
        self._num_pages_done += 1
        
        # stop ourselves getting into an accidental infinite loop
        
        url_info = [ info for info in url_info if info[0] not in self._all_urls_so_far ]
        
        self._all_urls_so_far.update( [ info[0] for info in url_info ] )
        
        # now url_info only contains new url info
        
        return url_info
        
    
    def GetFile( self, url, *args ):
        
        connection = self._GetConnection( url )
        
        return connection.geturl( url )
        
    
    def GetFileAndTags( self, url, *args ):
        
        file = self.GetFile( url, *args )
        tags = self.GetTags( url, *args )
        
        return ( file, tags )
        
    
    def GetTags( self, url ): pass
    
    def SetupGallerySearch( self ): pass
    
class DownloaderBooru( Downloader ):
    
    def __init__( self, booru, tags ):
        
        self._booru = booru
        self._tags = tags
        
        self._gallery_advance_num = None
        
        ( self._search_url, self._advance_by_page_num, self._search_separator, self._thumb_classname ) = booru.GetGalleryParsingInfo()
        
        Downloader.__init__( self )
        
    
    def _GetNextGalleryPageURL( self ):
        
        if self._advance_by_page_num: num_page_base = 1
        else: num_page_base = 0
        
        if self._gallery_advance_num is None: gallery_advance_num = 0
        else: gallery_advance_num = self._gallery_advance_num
        
        return self._search_url.replace( '%tags%', self._search_separator.join( self._tags ) ).replace( '%index%', str( num_page_base + ( self._num_pages_done * gallery_advance_num ) ) )
        
    
    def _ParseGalleryPage( self, html, url_base ):
        
        urls_set = set()
        urls = []
        
        soup = bs4.BeautifulSoup( html )
        
        thumbnails = soup.find_all( class_ = self._thumb_classname )
        
        if self._gallery_advance_num is None:
            
            if len( thumbnails ) == 0: self._we_are_done = True
            else: self._gallery_advance_num = len( thumbnails )
            
        
        for thumbnail in thumbnails:
            
            links = thumbnail.find_all( 'a' )
            
            if thumbnail.name == 'a': links.append( thumbnail )
            
            for link in links:
                
                if link.string is not None and link.string == 'Image Only': continue # rule 34 @ paheal fix
                
                url = link[ 'href' ]
                
                url = urlparse.urljoin( url_base, url )
                
                if url not in urls_set:
                    
                    urls_set.add( url )
                    urls.append( ( url, ) )
                    
                
            
        
        return urls
        
    
    def _ParseImagePage( self, html, url_base ):
        
        ( search_url, search_separator, advance_by_page_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces ) = self._booru.GetData()
        
        soup = bs4.BeautifulSoup( html )
        
        image_base = None
        
        if image_id is not None:
            
            image = soup.find( id = image_id )
            
            image_url = image[ 'src' ]
            
        
        if image_data is not None:
            
            links = soup.find_all( 'a' )
            
            for link in links:
                
                if link.string == image_data: image_url = link[ 'href' ]
                
            
        
        image_url = urlparse.urljoin( url_base, image_url )
        
        image_url = image_url.replace( 'sample/sample-', '' ) # fix for danbooru resizing
        
        tags = []
        
        for ( tag_classname, namespace ) in tag_classnames_to_namespaces.items():
            
            tag_list_entries = soup.find_all( class_ = tag_classname )
            
            for tag_list_entry in tag_list_entries:
                
                links = tag_list_entry.find_all( 'a' )
                
                if tag_list_entry.name == 'a': links.append( tag_list_entry )
                
                for link in links:
                    
                    if link.string not in ( '?', '-', '+' ):
                        
                        if namespace == '': tags.append( link.string )
                        else: tags.append( namespace + ':' + link.string )
                        
                    
                
            
        
        return ( image_url, tags )
        
    
    def _GetFileURLAndTags( self, url ):
        
        connection = self._GetConnection( url )
        
        html = connection.geturl( url )
        
        return self._ParseImagePage( html, url )
        
    
    def GetFile( self, url ):
        
        ( file_url, tags ) = self._GetFileURLAndTags( url )
        
        connection = self._GetConnection( file_url )
        
        return connection.geturl( file_url )
        
    
    def GetFileAndTags( self, url ):
        
        ( file_url, tags ) = self._GetFileURLAndTags( url )
        
        connection = self._GetConnection( file_url )
        
        file = connection.geturl( file_url )
        
        return ( file, tags )
        
    
    def GetTags( self, url ):
        
        ( file_url, tags ) = self._GetFileURLAndTags( url )
        
        return tags
        
    
class DownloaderDeviantArt( Downloader ):
    
    def __init__( self, artist ):
        
        self._gallery_url = 'http://' + artist + '.deviantart.com/gallery/?catpath=/&offset='
        
        Downloader.__init__( self )
        
    
    def _GetNextGalleryPageURL( self ): return self._gallery_url + str( self._num_pages_done * 24 )
    
    def _ParseGalleryPage( self, html, url_base ):
        
        results = []
        
        soup = bs4.BeautifulSoup( html )
        
        thumbs_container = soup.find( class_ = 'zones-container' )
        
        def starts_with_thumb( classname ): return classname is not None and classname.startswith( 'thumb' )
        
        links = thumbs_container.find_all( 'a', class_ = starts_with_thumb )
        
        for link in links:
            
            page_url = link[ 'href' ] # something in the form of blah.da.com/art/blah-123456
            
            page_url_split = page_url.split( '-' )
            
            deviant_art_file_id = page_url_split[-1]
            
            image_url = 'http://www.deviantart.com/download/' + deviant_art_file_id + '/' # trailing slash is important
            
            raw_title = link[ 'title' ] # sweet dolls by ~AngeniaC, Feb 29, 2012 in Artisan Crafts &gt; Miniatures &gt; Jewelry
            
            raw_title_reversed = raw_title[::-1] # yrleweJ ;tg& serutainiM ;tg& stfarC nasitrA ni 2102 ,92 beF ,CainegnA~ yb sllod teews
            
            ( creator_and_date_and_tags_reversed, title_reversed ) = raw_title_reversed.split( ' yb ', 1 )
            
            creator_and_date_and_tags = creator_and_date_and_tags_reversed[::-1] # ~AngeniaC, Feb 29, 2012 in Artisan Crafts &gt; Miniatures &gt; Jewelry
            
            ( creator_with_username_char, date_and_tags ) = creator_and_date_and_tags.split( ',', 1 )
            
            creator = creator_with_username_char[1:] # AngeniaC
            
            title = title_reversed[::-1] # sweet dolls
            
            try: ( date_gumpf, raw_category_tags ) = date_and_tags.split( ' in ', 1 )
            except:
                
                print( raw_title )
                print( date_and_tags )
                
                raise
                
            
            category_tags = raw_category_tags.split( ' > ' )
            
            tags = []
            
            tags.append( 'title:' + title )
            tags.append( 'creator:' + creator )
            tags.extend( category_tags )
            
            results.append( ( image_url, tags ) )
            
        
        return results
        
    
    def GetTags( self, url, tags ): return tags
    
class DownloaderGiphy( Downloader ):
    
    def __init__( self, tag ):
        
        self._gallery_url = 'http://giphy.com/api/gifs?tag=' + tag.replace( ' ', '+' ) + '&page='
        
        Downloader.__init__( self )
        
    
    def _GetNextGalleryPageURL( self ): return self._gallery_url + str( self._num_pages_done + 1 )
    
    def _ParseGalleryPage( self, data, url_base ):
        
        json_dict = json.loads( data )
        
        if 'data' in json_dict:
            
            json_data = json_dict[ 'data' ]
            
            return [ ( d[ 'image_original_url' ], d[ 'id' ] ) for d in json_data ]
            
        else: return []
        
    
    def GetTags( self, url, id ):
        
        url = 'http://giphy.com/api/gifs/' + str( id )
        
        connection = self._GetConnection( url )
        
        try:
            
            raw_json = connection.geturl( url )
            
            json_dict = json.loads( raw_json )
            
            tags_data = json_dict[ 'data' ][ 'tags' ]
            
            tags = [ tag_data[ 'name' ] for tag_data in tags_data ]
            
        except:
            
            print( traceback.format_exc() )
            
            tags = []
            
        
        return tags
        
    
class DownloaderHentaiFoundry( Downloader ):
    
    def __init__( self, query_type, query, advanced_hentai_foundry_options ):
        
        self._query_type = query_type
        self._query = query
        self._advanced_hentai_foundry_options = advanced_hentai_foundry_options
        
        Downloader.__init__( self )
        
    
    def _EstablishSession( self, connection ):
        
        cookies = wx.GetApp().GetWebCookies( 'hentai foundry' )
        
        for ( key, value ) in cookies.items(): connection.SetCookie( key, value )
        
    
    def _GetFileURLAndTags( self, url ):
        
        connection = self._GetConnection( url )
        
        html = connection.geturl( url )
        
        return self._ParseImagePage( html, url )
        
    
    def _GetNextGalleryPageURL( self ):
        
        if self._query_type in ( 'artist', 'artist pictures' ):
            
            artist = self._query
            
            gallery_url = 'http://www.hentai-foundry.com/pictures/user/' + artist
            
            return gallery_url + '/page/' + str( self._num_pages_done + 1 )
            
        elif self._query_type == 'artist scraps':
            
            artist = self._query
            
            gallery_url = 'http://www.hentai-foundry.com/pictures/user/' + artist + '/scraps'
            
            return gallery_url + '/page/' + str( self._num_pages_done + 1 )
            
        elif self._query_type == 'tags':
            
            tags = self._query
            
            return 'http://www.hentai-foundry.com/search/pictures?query=' + '+'.join( tags ) + '&search_in=all&scraps=-1&page=' + str( self._num_pages_done + 1 )
            # scraps = 0 hide
            # -1 means show both
            # 1 means scraps only. wetf
            
        
    
    def _ParseGalleryPage( self, html, url_base ):
        
        urls_set = set()
        
        soup = bs4.BeautifulSoup( html )
        
        def correct_url( href ):
            
            # a good url is in the form "/pictures/user/artist_name/file_id/title"
            
            if href.count( '/' ) == 5 and href.startswith( '/pictures/user/' ):
                
                ( nothing, pictures, user, artist_name, file_id, title ) = href.split( '/' )
                
                # /pictures/user/artist_name/page/3
                if file_id != 'page': return True
                
            
            return False
            
        
        links = soup.find_all( 'a', href = correct_url )
        
        urls = [ 'http://www.hentai-foundry.com' + link['href'] for link in links ]
        
        result_urls = []
        
        for url in urls:
            
            if url not in urls_set:
                
                urls_set.add( url )
                
                result_urls.append( ( url, ) )
                
            
        
        # this is copied from old code. surely we can improve it?
        if 'class="next"' not in html: self._we_are_done = True
        
        return result_urls
        
    
    def _ParseImagePage( self, html, url_base ):
        
        # can't parse this easily normally because HF is a pain with the preview->click to see full size business.
        # find http://pictures.hentai-foundry.com//
        # then extend it to http://pictures.hentai-foundry.com//k/KABOS/172144.jpg
        # the .jpg bit is what we really need, but whatever
        try:
            
            index = html.index( 'http://pictures.hentai-foundry.com//' )
            
            stuff = html[ index : index + 100 ]
            
            try: ( image_url, gumpf ) = stuff.split( '"', 1 )
            except: ( image_url, gumpf ) = stuff.split( '&#039;', 1 )
            
        except: raise Exception( 'Could not parse image url!' )
        
        soup = bs4.BeautifulSoup( html )
        
        tags = []
        
        try:
            
            title = soup.find( 'title' )
            
            ( data, nothing ) = unicode( title.string ).split( ' - Hentai Foundry' )
            
            data_reversed = data[::-1] # want to do it right-side first, because title might have ' by ' in it
            
            ( artist_reversed, title_reversed ) = data_reversed.split( ' yb ' )
            
            artist = artist_reversed[::-1]
            
            title = title_reversed[::-1]
            
            tags.append( 'creator:' + artist )
            tags.append( 'title:' + title )
            
        except: pass
        
        tag_links = soup.find_all( 'a', rel = 'tag' )
        
        for tag_link in tag_links: tags.append( tag_link.string )
        
        return ( image_url, tags )
        
    
    def GetFile( self, url ):
        
        ( file_url, tags ) = self._GetFileURLAndTags( url )
        
        connection = self._GetConnection( file_url )
        
        return connection.geturl( file_url )
        
    
    def GetFileAndTags( self, url ):
        
        ( file_url, tags ) = self._GetFileURLAndTags( url )
        
        connection = self._GetConnection( file_url )
        
        file = connection.geturl( file_url )
        
        return ( file, tags )
        
    
    def GetTags( self, url ):
        
        ( file_url, tags ) = self._GetFileURLAndTags( url )
        
        return tags
        
    
    def SetupGallerySearch( self ):
        
        connection = self._GetConnection( 'http://www.hentai-foundry.com/site/filters' )
        
        cookies = connection.GetCookies()
        
        raw_csrf = cookies[ 'YII_CSRF_TOKEN' ] # YII_CSRF_TOKEN=19b05b536885ec60b8b37650a32f8deb11c08cd1s%3A40%3A%222917dcfbfbf2eda2c1fbe43f4d4c4ec4b6902b32%22%3B
        
        processed_csrf = urllib.unquote( raw_csrf ) # 19b05b536885ec60b8b37650a32f8deb11c08cd1s:40:"2917dcfbfbf2eda2c1fbe43f4d4c4ec4b6902b32";
        
        csrf_token = processed_csrf.split( '"' )[1] # the 2917... bit
        
        self._advanced_hentai_foundry_options[ 'YII_CSRF_TOKEN' ] = csrf_token
        
        body = urllib.urlencode( self._advanced_hentai_foundry_options )
        
        headers = {}
        headers[ 'Content-Type' ] = 'application/x-www-form-urlencoded'
        
        connection.request( 'POST', '/site/filters', headers = headers, body = body )
        
    
class DownloaderPixiv( Downloader ):
    
    def __init__( self, query_type, query ):
        
        self._query_type = query_type
        self._query = query
        
        Downloader.__init__( self )
        
    
    def _EstablishSession( self, connection ):
        
        cookies = wx.GetApp().GetWebCookies( 'pixiv' )
        
        for ( key, value ) in cookies.items(): connection.SetCookie( key, value )
        
    
    def _GetNextGalleryPageURL( self ):
        
        if self._query_type == 'artist':
            
            artist_id = self._query
            
            gallery_url = 'http://www.pixiv.net/member_illust.php?id=' + str( artist_id )
            
        elif self._query_type == 'tag':
            
            tag = self._query
            
            tag = urllib.quote( tag.encode( 'utf-8' ) )
            
            gallery_url = 'http://www.pixiv.net/search.php?word=' + tag + '&s_mode=s_tag_full&order=date_d'
            
        
        return gallery_url + '&p=' + str( self._num_pages_done + 1 )
        
    
    def _ParseGalleryPage( self, html, url_base ):
        
        results = []
        
        soup = bs4.BeautifulSoup( html )
        
        thumbnail_links = soup.find_all( class_ = 'work' )
        
        for thumbnail_link in thumbnail_links:
            
            url = urlparse.urljoin( url_base, thumbnail_link[ 'href' ] ) # http://www.pixiv.net/member_illust.php?mode=medium&illust_id=33500690
            
            results.append( ( url, ) )
            
        
        return results
        
    
    def _ParseImagePage( self, html, page_url ):
        
        soup = bs4.BeautifulSoup( html )
        
        #
        
        # this is the page that holds the full size of the image.
        # pixiv won't serve the image unless it thinks this page is the referrer
        referral_url = page_url.replace( 'medium', 'big' ) # http://www.pixiv.net/member_illust.php?mode=big&illust_id=33500690
        
        #
        
        works_display = soup.find( class_ = 'works_display' )
        
        img = works_display.find( 'img' )
        
        img_url = img[ 'src' ] # http://i2.pixiv.net/img122/img/amanekukagenoyuragi/34992468_m.png
        
        image_url = img_url.replace( '_m.', '.' ) # http://i2.pixiv.net/img122/img/amanekukagenoyuragi/34992468.png
        
        #
        
        tags = soup.find( 'ul', class_ = 'tags' )
        
        tags = [ a_item.string for a_item in tags.find_all( 'a', class_ = 'text' ) ]
        
        user = soup.find( 'h1', class_ = 'user' )
        
        tags.append( 'creator:' + user.string )
        
        title_parent = soup.find( 'section', class_ = 'work-info' )
        
        title = title_parent.find( 'h1', class_ = 'title' )
        
        tags.append( 'title:' + title.string )
        
        try: tags.append( 'creator:' + image_url.split( '/' )[ -2 ] ) # http://i2.pixiv.net/img02/img/dnosuke/462657.jpg -> dnosuke
        except: pass
        
        return ( referral_url, image_url, tags )
        
    
    def _GetReferralURLFileURLAndTags( self, page_url ):
        
        connection = self._GetConnection( page_url )
        
        html = connection.geturl( page_url )
        
        return self._ParseImagePage( html, page_url )
        
    
    def GetFile( self, url ):
        
        ( referral_url, image_url, tags ) = self._GetReferralURLFileURLAndTags( url )
        
        connection = self._GetConnection( image_url )
        
        headers = { 'Referer' : referral_url }
        
        return connection.geturl( image_url, headers = headers )
        
    
    def GetFileAndTags( self, url ):
        
        ( referral_url, image_url, tags ) = self._GetReferralURLFileURLAndTags( url )
        
        connection = self._GetConnection( image_url )
        
        headers = { 'Referer' : referral_url }
        
        file = connection.geturl( image_url, headers = headers )
        
        return ( file, tags )
        
    
    def GetTags( self, url ):
        
        ( referral_url, image_url, tags ) = self._GetReferralURLFileURLAndTags( url )
        
        return tags
        
    
class DownloaderTumblr( Downloader ):
    
    def __init__( self, username ):
        
        self._gallery_url = 'http://' + username + '.tumblr.com/api/read/json?start=%start%&num=50'
        
        Downloader.__init__( self )
        
    
    def _GetNextGalleryPageURL( self ): return self._gallery_url.replace( '%start%', str( self._num_pages_done * 50 ) )
    
    def _ParseGalleryPage( self, data, url_base ):
        
        processed_raw_json = data.split( 'var tumblr_api_read = ' )[1][:-2] # -2 takes a couple newline chars off at the end
        
        json_object = json.loads( processed_raw_json )
        
        results = []
        
        if 'posts' in json_object:
            
            for post in json_object[ 'posts' ]:
                
                if 'tags' in post: tags = post[ 'tags' ]
                else: tags = []
                
                post_type = post[ 'type' ]
                
                if post_type == 'photo':
                    
                    if len( post[ 'photos' ] ) == 0:
                        
                        try: results.append( ( post[ 'photo-url-1280' ], tags ) )
                        except: pass
                        
                    else:
                        
                        for photo in post[ 'photos' ]:
                            
                            try: results.append( ( photo[ 'photo-url-1280' ], tags ) )
                            except: pass
                            
                        
                    
                
            
        
        return results
        
    
    def GetTags( self, url, tags ): return tags
    