import bs4
import HydrusConstants as HC
import json
import lxml
import traceback
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
    
def GetDownloader( subscription_type, *args ):
    
    if subscription_type == HC.SUBSCRIPTION_TYPE_BOORU: c = DownloaderBooru
    elif subscription_type == HC.SUBSCRIPTION_TYPE_DEVIANT_ART: c = DownloaderDeviantArt
    elif subscription_type == HC.SUBSCRIPTION_TYPE_GIPHY: c = DownloaderGiphy
    elif subscription_type == HC.SUBSCRIPTION_TYPE_HENTAI_FOUNDRY: c = DownloaderHentaiFoundry
    elif subscription_type == HC.SUBSCRIPTION_TYPE_PIXIV: c = DownloaderPixiv
    elif subscription_type == HC.SUBSCRIPTION_TYPE_TUMBLR: c = DownloaderTumblr
    
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
        
        self._connections = {}
        
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
        
        url = self._GetNextGalleryPageURL()
        
        connection = self._GetConnection( url )
        
        data = connection.geturl( url )
        
        url_info = self._ParseGalleryPage( data, url )
        
        self._num_pages_done += 1
        
        return url_info
        
    
    def GetFile( self, url, *args ):
        
        connection = self._GetConnection( url )
        
        return connection.geturl( url )
        
    
    def GetFileAndTags( self, url, *args ):
        
        file = self.GetFile( url, *args )
        tags = self.GetTags( url, *args )
        
        return ( file, tags )
        
    
    def GetTags( self, url ): pass
    
class DownloaderBooru( Downloader ):
    
    def __init__( self, booru, query ):
        
        self._booru = booru
        self._tags = query
        
        ( self._search_url, self._gallery_advance_num, self._search_separator, self._thumb_classname ) = booru.GetGalleryParsingInfo()
        
        Downloader.__init__( self )
        
    
    def _GetNextGalleryPageURL( self ):
        
        if self._gallery_advance_num == 1: num_page_base = 1
        else: num_page_base = 0
        
        return self._search_url.replace( '%tags%', self._search_separator.join( self._tags ) ).replace( '%index%', str( num_page_base + ( self._num_pages_done * self._gallery_advance_num ) ) )
        
    
    def _ParseGalleryPage( self, html, url_base ):
        
        urls_set = set()
        urls = []
        
        soup = bs4.BeautifulSoup( html )
        
        thumbnails = soup.find_all( class_ = self._thumb_classname )
        
        for thumbnail in thumbnails:
            
            links = thumbnail.find_all( 'a' )
            
            if thumbnail.name == 'a': links.append( thumbnail )
            
            for link in links:
                
                if link.string is not None and link.string == 'Image Only': continue # rule 34 @ paheal fix
                
                url = link[ 'href' ]
                
                url = urlparse.urljoin( url_base, url )
                
                if url not in urls_set:
                    
                    urls_set.add( url )
                    urls.append( url )
                    
                
            
        
        return urls
        
    
    def _ParseImagePage( self, html, url_base ):
        
        ( search_url, search_separator, gallery_advance_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces ) = self._booru.GetData()
        
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
    
    def __init__( self, query ):
        
        artist = query
        
        self._gallery_url = 'http://' + artist + '.deviantart.com/gallery/?catpath=/&offset='
        
        Downloader.__init__( self )
        
    
    def _GetNextGalleryPageURL( self ): return self._gallery_url + str( self._num_pages_done * 24 )
    
    def _ParseGalleryPage( self, html, url_base ):
        
        results = []
        
        soup = bs4.BeautifulSoup( html )
        
        thumbs_container = soup.find( class_ = 'stream stream-fh' )
        
        def starts_with_thumb( classname ): return classname is not None and classname.startswith( 'thumb' )
        
        links = thumbs_container.find_all( 'a', class_ = starts_with_thumb )
        
        for link in links:
            
            page_url = link[ 'href' ] # something in the form of blah.da.com/art/blah-123456
            
            page_url_split = page_url.split( '-' )
            
            deviant_art_file_id = page_url_split[-1 ]
            
            image_url = 'http://www.deviantart.com/download/' + deviant_art_file_id + '/' # trailing slash is important
            
            raw_title = link[ 'title' ] # something in the form sweet dolls by ~AngeniaC, Feb 29, 2012 in Artisan Crafts &gt; Miniatures &gt; Jewelry
            
            tags = []
            
            ( title, raw_title ) = raw_title.split( ' by ~', 1 )
            
            ( creator, raw_title ) = raw_title.split( ', ', 1 )
            
            ( date_gumpf, raw_category_tags ) = raw_title.split( ' in ', 1 )
            
            category_tags = raw_category_tags.split( ' > ' )
            
            tags = []
            
            tags.append( 'title:' + title )
            tags.append( 'creator:' + creator )
            tags.extend( category_tags )
            
            results.append( ( image_url, tags ) )
            
        
        return results
        
    
    def GetTags( self, url, tags ): return tags
    
class DownloaderGiphy( Downloader ):
    
    def __init__( self, query ):
        
        tag = query
        
        self._gallery_url = 'http://giphy.com/api/gifs?tag=' + tag.replace( ' ', '+' ) + '&page='
        
        Downloader.__init__( self )
        
    
    def _GetNextGalleryPageURL( self ): return self._gallery_url + str( self._num_pages_done )
    
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
    
    def __init__( self, query_type, query ):
        
        self._query_type = query
        self._query = query
        
        Downloader.__init__( self )
        
    
    def _EstablishSession( self, connection ):
        
        cookies = wx.GetApp().GetWebCookies( 'hentai foundry' )
        
        for ( key, value ) in cookies.items(): connection.SetCookie( key, value )
        
    
    def _GetNextGalleryPageURL( self ):
        
        if self._query_type == 'artist':
            
            pass
            
            # this is slightly more difficult since it needs to manage scraps interlace
            
        elif self._query_type == 'tags':
            
            tags = self._query
            
            return 'http://www.hentai-foundry.com/search/pictures?query=' + '+'.join( tags ) + '&search_in=all&scraps=-1&page=' + str( self._num_pages_done )
            
        
    
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
                
                result_urls.append( url )
                
            
        
        return result_urls
        
    
    def _ParseImagePage( self, html ):
        
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
        
    
class DownloaderPixiv( Downloader ):
    
    def __init__( self, query_type, query ):
        
        self._query_type = query_type
        self._query = query
        
        Downloader.__init__( self )
        
    
    def _EstablishSession( self, connection ):
        
        cookies = wx.GetApp().GetWebCookies( 'pixiv' )
        
        for ( key, value ) in cookies.items(): connection.SetCookie( key, value )
        
    
    def _GetNextGalleryPageURL( self ):
        
        if self._query_type == 'artist': pass
        elif self._query_type == 'tags': pass
        
    
    def _ParseGalleryPage( self, html, url_base ):
        
        results = []
        
        soup = bs4.BeautifulSoup( html )
        
        thumbnail_links = soup.find_all( class_ = 'work' )
        
        for thumbnail_link in thumbnail_links:
            
            url = urlparse.urljoin( url_base, thumbnail_link[ 'href' ] ) # http://www.pixiv.net/member_illust.php?mode=medium&illust_id=33500690
            
            image_url_reference_url = url.replace( 'medium', 'big' ) # http://www.pixiv.net/member_illust.php?mode=big&illust_id=33500690
            
            thumbnail_img = thumbnail_link.find( class_ = '_thumbnail' )
            
            thumbnail_image_url = thumbnail_img[ 'src' ] # http://i2.pixiv.net/img02/img/dnosuke/462657_s.jpg
            
            image_url = thumbnail_image_url.replace( '_s', '' ) # http://i2.pixiv.net/img02/img/dnosuke/462657.jpg
            
            results.append( ( url, image_url_reference_url, image_url ) )
            
        
        return results
        
    
    def _ParseImagePage( self, html, image_url ):
        
        soup = bs4.BeautifulSoup( html )
        
        tags = soup.find( 'ul', class_ = 'tags' )
        
        tags = [ a_item.string for a_item in tags.find_all( 'a', class_ = 'text' ) ]
        
        user = soup.find( 'h1', class_ = 'user' )
        
        tags.append( 'creator:' + user.string )
        
        title_parent = soup.find( 'section', class_ = 'work-info' )
        
        title = title_parent.find( 'h1', class_ = 'title' )
        
        tags.append( 'title:' + title.string )
        
        try: tags.append( 'creator:' + image_url.split( '/' )[ -2 ] ) # http://i2.pixiv.net/img02/img/dnosuke/462657.jpg -> dnosuke
        except: pass
        
        return tags
        
    
    def GetFile( self, url, image_url_reference_url, image_url ):
        
        connection = self._GetConnection( image_url )
        
        headers = { 'Referer' : image_url_reference_url }
        
        return connection.geturl( image_url, headers = headers )
        
    
    def GetFileAndTags( self, url, image_url_reference_url, image_url ):
        
        file = self.GetFile( url, image_url_reference_url, image_url )
        tags = self.GetTags( url, image_url_reference_url, image_url )
        
    
    def GetTags( self, url, image_url_reference_url, image_url ):
        
        connection = self._GetConnection( url )
        
        html = self._page_connection.geturl( url )
        
        return self._ParseImagePage( html, image_url )
        
    
class DownloaderTumblr( Downloader ):
    
    def __init__( self, query ):
        
        username = query
        
        self._gallery_url = 'http://' + username + '.tumblr.com/api/read/json?start=%start%&num=50'
        
        Downloader.__init__( self )
        
    
    def _GetNextGalleryPageURL( self ): return search_url.replace( '%start%', str( self._num_pages_done * 50 ) )
    
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
    