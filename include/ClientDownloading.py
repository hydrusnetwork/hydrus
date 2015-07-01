import bs4
import collections
import httplib
import HydrusConstants as HC
import HydrusExceptions
import HydrusNetworking
import HydrusThreading
import json
import os
import pafy
import re
import sys
import threading
import time
import traceback
import urllib
import urlparse
import wx
import zipfile
import HydrusTags
import HydrusData
import HydrusFileHandling
import ClientData
import ClientConstants as CC
import HydrusGlobals

# This is fairly ugly, but it works for what I need it to do

URL_EXTRA_INFO = {}
URL_EXTRA_INFO_LOCK = threading.Lock()

def GetExtraURLInfo( url ):
    
    with URL_EXTRA_INFO_LOCK:
        
        if url in URL_EXTRA_INFO:
            
            return URL_EXTRA_INFO[ url ]
            
        else:
            
            return None
            
        
    
def SetExtraURLInfo( url, info ):
    
    with URL_EXTRA_INFO_LOCK:
        
        URL_EXTRA_INFO[ url ] = info
        
    
def ConvertServiceKeysToTagsToServiceKeysToContentUpdates( hash, service_keys_to_tags ):
    
    hashes = set( ( hash, ) )
    
    service_keys_to_content_updates = {}
    
    for ( service_key, tags ) in service_keys_to_tags.items():
        
        if service_key == CC.LOCAL_TAG_SERVICE_KEY: action = HC.CONTENT_UPDATE_ADD
        else: action = HC.CONTENT_UPDATE_PENDING
        
        content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_DATA_TYPE_MAPPINGS, action, ( tag, hashes ) ) for tag in tags ]
        
        service_keys_to_content_updates[ service_key ] = content_updates
        
    
    return service_keys_to_content_updates
    
def GetGalleryParser( site_type, *args ):
    
    if site_type == HC.SITE_TYPE_BOORU: c = GalleryParserBooru
    elif site_type == HC.SITE_TYPE_DEVIANT_ART: c = GalleryParserDeviantArt
    elif site_type == HC.SITE_TYPE_GIPHY: c = GalleryParserGiphy
    elif site_type == HC.SITE_TYPE_HENTAI_FOUNDRY: c = GalleryParserHentaiFoundry
    elif site_type == HC.SITE_TYPE_PIXIV: c = GalleryParserPixiv
    elif site_type == HC.SITE_TYPE_TUMBLR: c = GalleryParserTumblr
    elif site_type == HC.SITE_TYPE_NEWGROUNDS: c = GalleryParserNewgrounds
    
    return c( *args )
    
def ConvertTagsToServiceKeysToTags( tags, advanced_tag_options ):
    
    tags = [ tag for tag in tags if tag is not None ]
    
    service_keys_to_tags = {}
    
    siblings_manager = wx.GetApp().GetManager( 'tag_siblings' )
    parents_manager = wx.GetApp().GetManager( 'tag_parents' )
    
    for ( service_key, namespaces ) in advanced_tag_options.items():
        
        if len( namespaces ) > 0:
            
            tags_to_add_here = []
            
            for namespace in namespaces:
                
                if namespace == '': tags_to_add_here.extend( [ tag for tag in tags if not ':' in tag ] )
                else: tags_to_add_here.extend( [ tag for tag in tags if tag.startswith( namespace + ':' ) ] )
                
            
            tags_to_add_here = HydrusTags.CleanTags( tags_to_add_here )
            
            if len( tags_to_add_here ) > 0:
                
                tags_to_add_here = siblings_manager.CollapseTags( tags_to_add_here )
                tags_to_add_here = parents_manager.ExpandTags( service_key, tags_to_add_here )
                
                service_keys_to_tags[ service_key ] = tags_to_add_here
                
            
        
    
    return service_keys_to_tags
    
def GetYoutubeFormats( youtube_url ):
    
    try: p = pafy.Pafy( youtube_url )
    except Exception as e:
        
        raise Exception( 'Could not fetch video info from youtube!' + os.linesep + HydrusData.ToString( e ) )
        
    
    info = { ( s.extension, s.resolution ) : ( s.url, s.title ) for s in p.streams if s.extension in ( 'flv', 'mp4' ) }
    
    return info
    
class GalleryParser( object ):
    
    def __init__( self ):
        
        self._we_are_done = False
        
        self._report_hooks = []
        
        self._all_urls_so_far = set()
        
    
    def _AddSessionCookies( self, request_headers ): pass
    
    def _FetchData( self, url, request_headers = None, report_hooks = None, temp_path = None ):
        
        if request_headers is None: request_headers = {}
        if report_hooks is None: report_hooks = []
        
        self._AddSessionCookies( request_headers )
        
        return wx.GetApp().DoHTTP( HC.GET, url, request_headers = request_headers, report_hooks = report_hooks, temp_path = temp_path )
        
    
    def _GetGalleryPageURL( self, page_index ):
        
        return ''
        
    
    def _GetGalleryPageURLs( self, page_index ):
        
        return ( self._GetGalleryPageURL( page_index ), )
        
    
    def _ParseGalleryPage( self, data, url ):
        
        raise NotImplementedError()
        
    
    def AddReportHook( self, hook ): self._report_hooks.append( hook )
    
    def ClearReportHooks( self ): self._report_hooks = []
    
    def GetFile( self, temp_path, url ): self._FetchData( url, report_hooks = self._report_hooks, temp_path = temp_path )
    
    def GetFileAndTags( self, temp_path, url ):
        
        temp_path = self.GetFile( temp_path, url )
        tags = self.GetTags( url )
        
        return tags
        
    
    def GetPage( self, page_index ):
        
        if self._we_are_done: return []
        
        gallery_urls = self._GetGalleryPageURLs( page_index )
        
        all_urls = []
        
        for gallery_url in gallery_urls:
            
            data = self._FetchData( gallery_url )
            
            page_of_urls = self._ParseGalleryPage( data, gallery_url )
            
            # stop ourselves getting into an accidental infinite loop
            
            all_urls += [ url for url in page_of_urls if url not in self._all_urls_so_far ]
            
            self._all_urls_so_far.update( page_of_urls )
            
        
        return all_urls
        
    
    def GetTags( self, url ): pass
    
    def SetupGallerySearch( self ): pass
    
class GalleryParserBooru( GalleryParser ):
    
    def __init__( self, booru, tags ):
        
        self._booru = booru
        self._tags = tags
        
        self._gallery_advance_num = None
        
        ( self._search_url, self._advance_by_page_num, self._search_separator, self._thumb_classname ) = booru.GetGalleryParsingInfo()
        
        GalleryParser.__init__( self )
        
    
    def _GetGalleryPageURL( self, page_index ):
        
        if self._advance_by_page_num: url_index = page_index + 1
        else:
            
            if self._gallery_advance_num is None: url_index = 0
            else: url_index = page_index * self._gallery_advance_num
            
        
        return self._search_url.replace( '%tags%', self._search_separator.join( [ urllib.quote( tag ) for tag in self._tags ] ) ).replace( '%index%', HydrusData.ToString( url_index ) )
        
    
    def _ParseGalleryPage( self, html, url_base ):
        
        urls_set = set()
        urls = []
        
        soup = bs4.BeautifulSoup( html )
        
        # this catches 'post-preview' along with 'post-preview not-approved' sort of bullshit
        def starts_with_classname( classname ): return classname is not None and classname.startswith( self._thumb_classname )
        
        thumbnails = soup.find_all( class_ = starts_with_classname )
        
        # this is a sankaku thing
        popular_thumbnail_parent = soup.find( id = 'popular-preview' )
        
        if popular_thumbnail_parent is not None:
            
            popular_thumbnails = popular_thumbnail_parent.find_all( class_ = starts_with_classname )
            
            thumbnails = thumbnails[ len( popular_thumbnails ) : ]
            
        
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
                    urls.append( url )
                    
                
            
        
        return urls
        
    
    def _ParseImagePage( self, html, url_base ):
        
        ( search_url, search_separator, advance_by_page_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces ) = self._booru.GetData()
        
        soup = bs4.BeautifulSoup( html )
        
        image_base = None
        
        image_url = None
        
        if image_id is not None:
            
            image = soup.find( id = image_id )
            
            if image is None:
                
                image_string = soup.find( text = re.compile( 'Save this file' ) )
                
                if image_string is None: image_string = soup.find( text = re.compile( 'Save this video' ) )
                
                image = image_string.parent
                
                image_url = image[ 'href' ]
                
            else:
                
                if image.name in ( 'img', 'video' ):
                    
                    image_url = image[ 'src' ]
                    
                    if 'sample/sample-' in image_url:
                        
                        # danbooru resized image
                        
                        image = soup.find( id = 'image-resize-link' )
                        
                        image_url = image[ 'href' ]
                        
                    
                elif image.name == 'a':
                    
                    image_url = image[ 'href' ]
                    
                
            
        
        if image_data is not None:
            
            links = soup.find_all( 'a' )
            
            for link in links:
                
                if link.string == image_data: image_url = link[ 'href' ]
                
            
        
        if image_url is None:
            
            raise HydrusExceptions.NotFoundException( 'Could not find the image URL!' )
            
        
        image_url = urlparse.urljoin( url_base, image_url )
        
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
        
        html = self._FetchData( url )
        
        return self._ParseImagePage( html, url )
        
    
    def GetFile( self, temp_path, url ):
        
        ( file_url, tags ) = self._GetFileURLAndTags( url )
        
        self._FetchData( file_url, report_hooks = self._report_hooks, temp_path = temp_path )
        
    
    def GetFileAndTags( self, temp_path, url ):
        
        ( file_url, tags ) = self._GetFileURLAndTags( url )
        
        self._FetchData( file_url, report_hooks = self._report_hooks, temp_path = temp_path )
        
        return tags
        
    
    def GetTags( self, url ):
        
        ( file_url, tags ) = self._GetFileURLAndTags( url )
        
        return tags
        
    
class GalleryParserDeviantArt( GalleryParser ):
    
    def __init__( self, artist ):
        
        self._gallery_url = 'http://' + artist + '.deviantart.com/gallery/?catpath=/&offset='
        self._artist = artist
        
        GalleryParser.__init__( self )
        
    
    def _GetGalleryPageURL( self, page_index ):
        
        return self._gallery_url + HydrusData.ToString( page_index * 24 )
        
    
    def _ParseGalleryPage( self, html, url_base ):
        
        urls = []
        
        soup = bs4.BeautifulSoup( html )
        
        thumbs_container = soup.find( class_ = 'zones-container' )
        
        def starts_with_thumb( classname ): return classname is not None and classname.startswith( 'thumb' )
        
        links = thumbs_container.find_all( 'a', class_ = starts_with_thumb )
        
        for link in links:
            
            try: # starts_with_thumb picks up some false positives, but they break
                
                url = link[ 'href' ] # something in the form of blah.da.com/art/blah-123456
                
                raw_title = link[ 'title' ] # sweet dolls by AngeniaC, date, blah blah blah
                
                raw_title_reversed = raw_title[::-1] # trAtnaiveD no CainegnA yb sllod teews
                
                ( creator_and_gumpf_reversed, title_reversed ) = raw_title_reversed.split( ' yb ', 1 )
                
                title = title_reversed[::-1] # sweet dolls
                
                tags = []
                
                tags.append( 'title:' + title )
                tags.append( 'creator:' + self._artist )
                
                SetExtraURLInfo( url, tags )
                
                urls.append( url )
                
            except: pass
            
        
        return urls
        
    
    def _ParseImagePage( self, html ):
        
        soup = bs4.BeautifulSoup( html )
        
        # if can find download link:
        if False:
            
            pass # go fetch the popup page using tokens as appropriate. feels like it needs the GET token and a referrer, as middle click just redirects back to image page
            
        else:
            
            img = soup.find( class_ = 'dev-content-full' )
            
            src = img[ 'src' ]
            
            return src
            
        
    
    def _GetFileURL( self, url ):
        
        html = self._FetchData( url )
        
        return self._ParseImagePage( html )
        
    
    def GetFile( self, temp_path, url ):
        
        file_url = self._GetFileURL( url )
        
        self._FetchData( file_url, report_hooks = self._report_hooks, temp_path = temp_path )
        
    
    def GetTags( self, url ):
        
        result = GetExtraURLInfo( url )
        
        if result is None:
            
            return []
            
        else:
            
            return result
            
        
    
class GalleryParserGiphy( GalleryParser ):
    
    def __init__( self, tag ):
        
        self._gallery_url = 'http://giphy.com/api/gifs?tag=' + urllib.quote( tag.replace( ' ', '+' ) ) + '&page='
        
        GalleryParser.__init__( self )
        
    
    def _GetGalleryPageURL( self, page_index ):
        
        return self._gallery_url + HydrusData.ToString( page_index + 1 )
        
    
    def _ParseGalleryPage( self, data, url_base ):
        
        json_dict = json.loads( data )
        
        urls = []
        
        if 'data' in json_dict:
            
            json_data = json_dict[ 'data' ]
            
            for d in json_data:
                
                url = d[ 'image_original_url' ]
                id = d[ 'id' ]
                
                SetExtraURLInfo( url, id )
                
                urls.append( url )
                
            
        
        return urls
        
    
    def GetTags( self, url ):
        
        id = GetExtraURLInfo( url )
        
        if id is None:
            
            return []
            
        else:
            
            url = 'http://giphy.com/api/gifs/' + HydrusData.ToString( id )
            
            try:
                
                raw_json = self._FetchData( url )
                
                json_dict = json.loads( raw_json )
                
                tags_data = json_dict[ 'data' ][ 'tags' ]
                
                return [ tag_data[ 'name' ] for tag_data in tags_data ]
                
            except Exception as e:
                
                HydrusData.ShowException( e )
                
                return []
                
            
        
    
class GalleryParserHentaiFoundry( GalleryParser ):
    
    def __init__( self, query_type, query, advanced_hentai_foundry_options ):
        
        self._query_type = query_type
        self._query = query
        self._advanced_hentai_foundry_options = advanced_hentai_foundry_options
        
        GalleryParser.__init__( self )
        
    
    def _AddSessionCookies( self, request_headers ):
        
        manager = wx.GetApp().GetManager( 'web_sessions' )
        
        cookies = manager.GetCookies( 'hentai foundry' )
        
        HydrusNetworking.AddCookiesToHeaders( cookies, request_headers )
        
    
    def _GetFileURLAndTags( self, url ):
        
        html = self._FetchData( url )
        
        return self._ParseImagePage( html, url )
        
    
    def _GetGalleryPageURL( self, page_index ):
        
        if self._query_type in ( 'artist', 'artist pictures' ):
            
            artist = self._query
            
            gallery_url = 'http://www.hentai-foundry.com/pictures/user/' + artist
            
            return gallery_url + '/page/' + HydrusData.ToString( page_index + 1 )
            
        elif self._query_type == 'artist scraps':
            
            artist = self._query
            
            gallery_url = 'http://www.hentai-foundry.com/pictures/user/' + artist + '/scraps'
            
            return gallery_url + '/page/' + HydrusData.ToString( page_index + 1 )
            
        elif self._query_type == 'tags':
            
            tags = self._query
            
            return 'http://www.hentai-foundry.com/search/pictures?query=' + '+'.join( tags ) + '&search_in=all&scraps=-1&page=' + HydrusData.ToString( page_index + 1 )
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
            
        
        urls = []
        
        links = soup.find_all( 'a', href = correct_url )
        
        for link in links:
            
            url = 'http://www.hentai-foundry.com' + link['href']
            
            if url not in urls_set:
                
                urls_set.add( url )
                
                urls.append( url )
                
            
        
        # this is copied from old code. surely we can improve it?
        if 'class="next"' not in html: self._we_are_done = True
        
        return urls
        
    
    def _ParseImagePage( self, html, url_base ):
        
        # can't parse this easily normally because HF is a pain with the preview->click to see full size business.
        # find http://pictures.hentai-foundry.com//
        # then extend it to http://pictures.hentai-foundry.com//k/KABOS/172144.jpg
        # the .jpg bit is what we really need, but whatever
        try:
            
            index = html.index( 'pictures.hentai-foundry.com' )
            
            image_url = html[ index : index + 256 ]
            
            if '"' in image_url: ( image_url, gumpf ) = image_url.split( '"', 1 )
            if '&#039;' in image_url: ( image_url, gumpf ) = image_url.split( '&#039;', 1 )
            
            image_url = 'http://' + image_url
            
        except Exception as e:
            
            raise Exception( 'Could not parse image url!' + os.linesep + HydrusData.ToString( e ) )
            
        
        soup = bs4.BeautifulSoup( html )
        
        tags = []
        
        try:
            
            title = soup.find( 'title' )
            
            ( data, nothing ) = HydrusData.ToString( title.string ).split( ' - Hentai Foundry' )
            
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
        
    
    def GetFile( self, temp_path, url ):
        
        ( file_url, tags ) = self._GetFileURLAndTags( url )
        
        self._FetchData( file_url, report_hooks = self._report_hooks, temp_path = temp_path )
        
    
    def GetFileAndTags( self, temp_path, url ):
        
        ( file_url, tags ) = self._GetFileURLAndTags( url )
        
        self._FetchData( file_url, report_hooks = self._report_hooks, temp_path = temp_path )
        
        return tags
        
    
    def GetTags( self, url ):
        
        ( file_url, tags ) = self._GetFileURLAndTags( url )
        
        return tags
        
    
    def SetupGallerySearch( self ):
        
        manager = wx.GetApp().GetManager( 'web_sessions' )
        
        cookies = manager.GetCookies( 'hentai foundry' )
        
        raw_csrf = cookies[ 'YII_CSRF_TOKEN' ] # 19b05b536885ec60b8b37650a32f8deb11c08cd1s%3A40%3A%222917dcfbfbf2eda2c1fbe43f4d4c4ec4b6902b32%22%3B
        
        processed_csrf = urllib.unquote( raw_csrf ) # 19b05b536885ec60b8b37650a32f8deb11c08cd1s:40:"2917dcfbfbf2eda2c1fbe43f4d4c4ec4b6902b32";
        
        csrf_token = processed_csrf.split( '"' )[1] # the 2917... bit
        
        self._advanced_hentai_foundry_options[ 'YII_CSRF_TOKEN' ] = csrf_token
        
        body = urllib.urlencode( self._advanced_hentai_foundry_options )
        
        request_headers = {}
        request_headers[ 'Content-Type' ] = 'application/x-www-form-urlencoded'
        
        self._AddSessionCookies( request_headers )
        
        wx.GetApp().DoHTTP( HC.POST, 'http://www.hentai-foundry.com/site/filters', request_headers = request_headers, body = body )
        
    
class GalleryParserNewgrounds( GalleryParser ):
    
    def __init__( self, query ):
        
        self._query = query
        
        GalleryParser.__init__( self )
        
    
    def _GetFileURLAndTags( self, url ):
        
        html = self._FetchData( url )
        
        return self._ParseImagePage( html, url )
        
    
    def _GetGalleryPageURLs( self, page_index ):
        
        artist = self._query
        
        gallery_urls = []
        
        gallery_urls.append( 'http://' + artist + '.newgrounds.com/games/' )
        gallery_urls.append( 'http://' + artist + '.newgrounds.com/movies/' )
        
        self._we_are_done = True
        
        return gallery_urls
        
    
    def _ParseGalleryPage( self, html, url_base ):
        
        soup = bs4.BeautifulSoup( html )
        
        fatcol = soup.find( 'div', class_ = 'fatcol' )
        
        links = fatcol.find_all( 'a' )
        
        urls_set = set()
        
        urls = []
        
        for link in links:
            
            try:
                
                url = link[ 'href' ]
                
                if url not in urls_set:
                    
                    if url.startswith( 'http://www.newgrounds.com/portal/view/' ): 
                        
                        urls_set.add( url )
                        
                        urls.append( url )
                        
                    
                
            except: pass
            
        
        return urls
        
    
    def _ParseImagePage( self, html, url_base ):
        
        soup = bs4.BeautifulSoup( html )
        
        tags = set()
        
        author_links = soup.find( 'ul', class_ = 'authorlinks' )
        
        if author_links is not None:
            
            authors = set()
            
            links = author_links.find_all( 'a' )
            
            for link in links:
                
                try:
                    
                    href = link[ 'href' ] # http://warlord-of-noodles.newgrounds.com
                    
                    creator = href.replace( 'http://', '' ).replace( '.newgrounds.com', '' )
                    
                    tags.add( u'creator:' + creator )
                    
                except: pass
                
            
        
        try:
            
            title = soup.find( 'title' )
            
            tags.add( u'title:' + title.string )
            
        except: pass
        
        all_links = soup.find_all( 'a' )
        
        for link in all_links:
            
            try:
                
                href = link[ 'href' ]
                
                if '/browse/tag/' in href: tags.add( link.string )
                
            except: pass
            
        
        #
        
        try:
            
            components = html.split( '"http://uploads.ungrounded.net/' )
            
            # there is sometimes another bit of api flash earlier on that we don't want
            # it is called http://uploads.ungrounded.net/apiassets/sandbox.swf
            
            if len( components ) == 2: flash_url = components[1]
            else: flash_url = components[2]
            
            flash_url = flash_url.split( '"', 1 )[0]
            
            flash_url = 'http://uploads.ungrounded.net/' + flash_url
            
        except: raise Exception( 'Could not find the swf file! It was probably an mp4!' )
        
        return ( flash_url, tags )
        
    
    def GetFile( self, temp_path, url ):
        
        ( file_url, tags ) = self._GetFileURLAndTags( url )
        
        self._FetchData( file_url, report_hooks = self._report_hooks, temp_path = temp_path )
        
    
    def GetFileAndTags( self, temp_path, url ):
        
        ( file_url, tags ) = self._GetFileURLAndTags( url )
        
        self._FetchData( file_url, report_hooks = self._report_hooks, temp_path = temp_path )
        
        return tags
        
    
    def GetTags( self, url ):
        
        ( file_url, tags ) = self._GetFileURLAndTags( url )
        
        return tags
        
    
class GalleryParserPixiv( GalleryParser ):
    
    def __init__( self, query_type, query ):
        
        self._query_type = query_type
        self._query = query
        
        GalleryParser.__init__( self )
        
    
    def _AddSessionCookies( self, request_headers ):
        
        manager = wx.GetApp().GetManager( 'web_sessions' )
        
        cookies = manager.GetCookies( 'pixiv' )
        
        HydrusNetworking.AddCookiesToHeaders( cookies, request_headers )
        
    
    def _GetGalleryPageURL( self, page_index ):
        
        if self._query_type == 'artist_id':
            
            artist_id = self._query
            
            gallery_url = 'http://www.pixiv.net/member_illust.php?id=' + HydrusData.ToString( artist_id )
            
        elif self._query_type == 'tags':
            
            tag = self._query
            
            gallery_url = 'http://www.pixiv.net/search.php?word=' + urllib.quote( tag.encode( 'utf-8' ) ) + '&s_mode=s_tag_full&order=date_d'
            
        
        return gallery_url + '&p=' + HydrusData.ToString( page_index + 1 )
        
    
    def _ParseGalleryPage( self, html, url_base ):
        
        urls = []
        
        soup = bs4.BeautifulSoup( html )
        
        thumbnail_links = soup.find_all( class_ = 'work' )
        
        for thumbnail_link in thumbnail_links:
            
            url = urlparse.urljoin( url_base, thumbnail_link[ 'href' ] ) # http://www.pixiv.net/member_illust.php?mode=medium&illust_id=33500690
            
            urls.append( url )
            
        
        return urls
        
    
    def _ParseImagePage( self, html, page_url ):
        
        if 'member_illust.php?mode=manga' in html:
            
            manga_url = page_url.replace( 'medium', 'manga' )
            
            raise Exception( page_url + ' was manga, not a single image, so could not be downloaded.' )
            
        
        soup = bs4.BeautifulSoup( html )
        
        #
        
        # this is the page that holds the full size of the image.
        # pixiv won't serve the image unless it thinks this page is the referrer
        #referral_url = page_url.replace( 'medium', 'big' ) # http://www.pixiv.net/member_illust.php?mode=big&illust_id=33500690
        
        #
        
        original_image = soup.find( class_ = 'original-image' )
        
        image_url = original_image[ 'data-src' ] # http://i3.pixiv.net/img-original/img/2014/01/25/19/21/56/41171994_p0.jpg
        
        #
        
        tags = soup.find( 'ul', class_ = 'tagCloud' )
        
        # <a href="/member_illust.php?id=5754629&amp;tag=Ib">Ib<span class="cnt">(2)</span></a> -> Ib
        tags = [ a_item.contents[0] for a_item in tags.find_all( 'a' ) ]
        
        user = soup.find( 'h1', class_ = 'user' )
        
        tags.append( 'creator:' + user.string )
        
        title_parent = soup.find( 'section', class_ = re.compile( 'work-info' ) )
        
        title = title_parent.find( 'h1', class_ = 'title' )
        
        tags.append( 'title:' + title.string )
        
        return ( image_url, tags )
        
    
    def _GetFileURLAndTags( self, page_url ):
        
        html = self._FetchData( page_url )
        
        return self._ParseImagePage( html, page_url )
        
    
    def GetFile( self, temp_path, url ):
        
        ( image_url, tags ) = self._GetFileURLAndTags( url )
        
        request_headers = { 'Referer' : url }
        
        self._FetchData( image_url, request_headers = request_headers, report_hooks = self._report_hooks, temp_path = temp_path )
        
    
    def GetFileAndTags( self, temp_path, url ):
        
        ( image_url, tags ) = self._GetFileURLAndTags( url )
        
        request_headers = { 'Referer' : url }
        
        self._FetchData( image_url, request_headers = request_headers, report_hooks = self._report_hooks, temp_path = temp_path )
        
        return tags
        
    
    def GetTags( self, url ):
        
        ( image_url, tags ) = self._GetFileURLAndTags( url )
        
        return tags
        
    
class GalleryParserTumblr( GalleryParser ):
    
    def __init__( self, username ):
        
        self._gallery_url = 'http://' + username + '.tumblr.com/api/read/json?start=%start%&num=50'
        
        self._urls_to_tags = {}
        
        GalleryParser.__init__( self )
        
    
    def _GetGalleryPageURL( self, page_index ):
        
        return self._gallery_url.replace( '%start%', HydrusData.ToString( page_index * 50 ) )
        
    
    def _ParseGalleryPage( self, data, url_base ):
        
        processed_raw_json = data.split( 'var tumblr_api_read = ' )[1][:-2] # -2 takes a couple newline chars off at the end
        
        json_object = json.loads( processed_raw_json )
        
        urls = []
        
        if 'posts' in json_object:
            
            for post in json_object[ 'posts' ]:
                
                if 'tags' in post: tags = post[ 'tags' ]
                else: tags = []
                
                post_type = post[ 'type' ]
                
                if post_type == 'photo':
                    
                    if len( post[ 'photos' ] ) == 0:
                        
                        try:
                            
                            url = post[ 'photo-url-1280' ]
                            
                            SetExtraURLInfo( url, tags )
                            
                            urls.append( url )
                            
                        except: pass
                        
                    else:
                        
                        for photo in post[ 'photos' ]:
                            
                            try:
                                
                                url = photo[ 'photo-url-1280' ]
                                
                                SetExtraURLInfo( url, tags )
                                
                                urls.append( url )
                                
                            except: pass
                            
                        
                    
                
            
        
        return urls
        
    
    def GetTags( self, url ):
        
        result = GetExtraURLInfo( url )
        
        if result is None:
            
            return []
            
        else:
            
            return result
            
        
    
class ImportArgsGenerator( object ):
    
    def __init__( self, job_key, item, advanced_import_options ):
        
        self._job_key = job_key
        self._item = item
        self._advanced_import_options = advanced_import_options
        
    
    def __call__( self ):
        
        try:
            
            ( result, media_result ) = self._CheckCurrentStatus()
            
            if result == CC.STATUS_NEW:
                
                ( os_file_handle, temp_path ) = HydrusFileHandling.GetTempPath()
                
                try:
                    
                    ( name, service_keys_to_tags, url ) = self._GetArgs( temp_path )
                    
                    self._job_key.SetVariable( 'status', 'importing' )
                    
                    ( result, media_result ) = wx.GetApp().WriteSynchronous( 'import_file', temp_path, advanced_import_options = self._advanced_import_options, service_keys_to_tags = service_keys_to_tags, generate_media_result = True, url = url )
                    
                finally:
                    
                    HydrusFileHandling.CleanUpTempPath( os_file_handle, temp_path )
                    
                
            
            self._job_key.SetVariable( 'result', result )
            
            if result in ( CC.STATUS_SUCCESSFUL, CC.STATUS_REDUNDANT ):
                
                page_key = self._job_key.GetVariable( 'page_key' )
                
                if media_result is not None and page_key is not None:
                    
                    HydrusGlobals.pubsub.pub( 'add_media_results', page_key, ( media_result, ) )
                    
                
            
            self._job_key.SetVariable( 'status', '' )
            
            self._job_key.Finish()
            
            self._CleanUp() # e.g. possibly delete the file for hdd importargsgenerator
            
        except Exception as e:
            
            self._job_key.SetVariable( 'result', CC.STATUS_FAILED )
            
            if 'name' in locals(): HydrusData.ShowText( 'There was a problem importing ' + name + '!' )
            
            HydrusData.ShowException( e )
            
            time.sleep( 2 )
            
            self._job_key.Cancel()
            
        
    
    def _CleanUp( self ): pass
    
    def _CheckCurrentStatus( self ): return ( CC.STATUS_NEW, None )
    
    def _GetArgs( self, temp_path ):
        
        raise NotImplementedError()
        
    
class ImportArgsGeneratorGallery( ImportArgsGenerator ):
    
    def __init__( self, job_key, item, advanced_import_options, advanced_tag_options, gallery_parsers_factory ):
        
        ImportArgsGenerator.__init__( self, job_key, item, advanced_import_options )
        
        self._advanced_tag_options = advanced_tag_options
        self._gallery_parsers_factory = gallery_parsers_factory
        
    
    def _GetArgs( self, temp_path ):
        
        url = self._item
        
        self._job_key.SetVariable( 'status', 'downloading' )
        
        gallery_parser = self._gallery_parsers_factory( 'example' )[0]
        
        def hook( gauge_range, gauge_value ):
            
            self._job_key.SetVariable( 'range', gauge_range )
            self._job_key.SetVariable( 'value', gauge_value )
            
        
        gallery_parser.AddReportHook( hook )
        
        do_tags = len( self._advanced_tag_options ) > 0
        
        if do_tags:
            
            tags = gallery_parser.GetFileAndTags( temp_path, url )
            
        else:
            
            gallery_parser.GetFile( temp_path, url )
            
            tags = []
            
        
        gallery_parser.ClearReportHooks()
        
        service_keys_to_tags = ConvertTagsToServiceKeysToTags( tags, self._advanced_tag_options )
        
        time.sleep( 3 )
        
        return ( url, service_keys_to_tags, url )
        
    
    def _CheckCurrentStatus( self ):
        
        url = self._item
        
        self._job_key.SetVariable( 'status', 'checking url status' )
        
        gallery_parser = self._gallery_parsers_factory( 'example' )[0]
        
        ( status, hash ) = wx.GetApp().Read( 'url_status', url )
        
        if status == CC.STATUS_DELETED and not self._advanced_import_options[ 'exclude_deleted_files' ]: status = CC.STATUS_NEW
        
        if status == CC.STATUS_REDUNDANT:
            
            ( media_result, ) = wx.GetApp().Read( 'media_results', CC.LOCAL_FILE_SERVICE_KEY, ( hash, ) )
            
            do_tags = len( self._advanced_tag_options ) > 0
            
            if do_tags:
                
                tags = gallery_parser.GetTags( url )
                
                service_keys_to_tags = ConvertTagsToServiceKeysToTags( tags, self._advanced_tag_options )
                
                service_keys_to_content_updates = ConvertServiceKeysToTagsToServiceKeysToContentUpdates( hash, service_keys_to_tags )
                
                wx.GetApp().Write( 'content_updates', service_keys_to_content_updates )
                
                time.sleep( 3 )
                
            
            return ( status, media_result )
            
        else: return ( status, None )
        
    
class ImportArgsGeneratorHDD( ImportArgsGenerator ):
    
    def __init__( self, job_key, item, advanced_import_options, paths_to_tags, delete_after_success ):
        
        ImportArgsGenerator.__init__( self, job_key, item, advanced_import_options )
        
        self._paths_to_tags = paths_to_tags
        self._delete_after_success = delete_after_success
        
    
    def _CleanUp( self ):
        
        result = self._job_key.GetVariable( 'result' )
        
        if self._delete_after_success and result in ( CC.STATUS_SUCCESSFUL, CC.STATUS_REDUNDANT ):
            
            ( path_type, path_info ) = self._item
            
            if path_type == 'path':
                
                path = path_info
                
                try: os.remove( path )
                except: pass
                
            
        
    
    def _GetArgs( self, temp_path ):
        
        self._job_key.SetVariable( 'status', 'reading from hdd' )
        
        ( path_type, path_info ) = self._item
        
        service_keys_to_tags = {}
        
        if path_type == 'path':
            
            path = path_info
            
            with open( path, 'rb' ) as f_source:
                
                with open( temp_path, 'wb' ) as f_dest:
                    
                    HydrusFileHandling.CopyFileLikeToFileLike( f_source, f_dest )
                    
                
            
            if path in self._paths_to_tags: service_keys_to_tags = self._paths_to_tags[ path ]
            
        elif path_type == 'zip':
            
            ( zip_path, name ) = path_info
            
            with open( temp_path, 'wb' ) as f:
                
                with zipfile.ZipFile( zip_path, 'r' ) as z: f.write( z.read( name ) )
                
            
            pretty_path = zip_path + os.path.sep + name
            
            if pretty_path in self._paths_to_tags: service_keys_to_tags = self._paths_to_tags[ pretty_path ]
            
            path = pretty_path
            
        
        return ( path, service_keys_to_tags, None )
        
    
class ImportArgsGeneratorThread( ImportArgsGenerator ):
    
    def __init__( self, job_key, item, advanced_import_options, advanced_tag_options ):
        
        ImportArgsGenerator.__init__( self, job_key, item, advanced_import_options )
        
        self._advanced_tag_options = advanced_tag_options
        
    
    def _GetArgs( self, temp_path ):
        
        self._job_key.SetVariable( 'status', 'downloading' )
        
        ( md5, image_url, filename ) = self._item
        
        def hook( gauge_range, gauge_value ):
            
            self._job_key.SetVariable( 'range', gauge_range )
            self._job_key.SetVariable( 'value', gauge_value )
            
        
        wx.GetApp().DoHTTP( HC.GET, image_url, report_hooks = [ hook ], temp_path = temp_path )
        
        tags = [ 'filename:' + filename ]
        
        service_keys_to_tags = ConvertTagsToServiceKeysToTags( tags, self._advanced_tag_options )
        
        time.sleep( 3 )
        
        return ( image_url, service_keys_to_tags, image_url )
        
    
    def _CheckCurrentStatus( self ):
        
        self._job_key.SetVariable( 'status', 'checking md5 status' )
        
        ( md5, image_url, filename ) = self._item
        
        ( status, hash ) = wx.GetApp().Read( 'md5_status', md5 )
        
        if status == CC.STATUS_DELETED and not self._advanced_import_options[ 'exclude_deleted_files' ]: status = CC.STATUS_NEW
        
        if status == CC.STATUS_REDUNDANT:
            
            ( media_result, ) = wx.GetApp().Read( 'media_results', CC.LOCAL_FILE_SERVICE_KEY, ( hash, ) )
            
            do_tags = len( self._advanced_tag_options ) > 0
            
            if do_tags:
                
                tags = [ 'filename:' + filename ]
                
                service_keys_to_tags = ConvertTagsToServiceKeysToTags( tags, self._advanced_tag_options )
                
                service_keys_to_content_updates = ConvertServiceKeysToTagsToServiceKeysToContentUpdates( hash, service_keys_to_tags )
                
                wx.GetApp().Write( 'content_updates', service_keys_to_content_updates )
                
                time.sleep( 3 )
                
            
            return ( status, media_result )
            
        else: return ( status, None )
        
    
class ImportArgsGeneratorURLs( ImportArgsGenerator ):
    
    def _GetArgs( self, temp_path ):
        
        url = self._item
        
        self._job_key.SetVariable( 'status', 'downloading' )
        
        def hook( gauge_range, gauge_value ):
            
            self._job_key.SetVariable( 'range', gauge_range )
            self._job_key.SetVariable( 'value', gauge_value )
            
        
        wx.GetApp().DoHTTP( HC.GET, url, report_hooks = [ hook ], temp_path = temp_path )
        
        service_keys_to_tags = {}
        
        return ( url, service_keys_to_tags, url )
        
    
    def _CheckCurrentStatus( self ):
        
        url = self._item
        
        self._job_key.SetVariable( 'status', 'checking url status' )
        
        ( status, hash ) = wx.GetApp().Read( 'url_status', url )
        
        if status == CC.STATUS_DELETED and not self._advanced_import_options[ 'exclude_deleted_files' ]: status = CC.STATUS_NEW
        
        if status == CC.STATUS_REDUNDANT:
            
            ( media_result, ) = wx.GetApp().Read( 'media_results', CC.LOCAL_FILE_SERVICE_KEY, ( hash, ) )
            
            return ( status, media_result )
            
        else: return ( status, None )
        
    
class ImportController( object ):
    
    def __init__( self, import_args_generator_factory, import_queue_builder_factory, page_key = None ):
        
        self._controller_job_key = self._GetNewJobKey( 'controller' )
        
        self._import_args_generator_factory = import_args_generator_factory
        self._import_queue_builder_factory = import_queue_builder_factory
        self._page_key = page_key
        
        self._import_job_key = self._GetNewJobKey( 'import' )
        self._import_queue_job_key = self._GetNewJobKey( 'import_queue' )
        self._import_queue_builder_job_key = self._GetNewJobKey( 'import_queue_builder' )
        self._pending_import_queue_jobs = []
        
        self._lock = threading.Lock()
        
    
    def _GetNewJobKey( self, job_type ):
        
        job_key = HydrusData.JobKey( pausable = True, cancellable = True )
        
        if job_type == 'controller':
            
            result_counts = {}
            
            result_counts[ CC.STATUS_SUCCESSFUL ] = 0
            result_counts[ CC.STATUS_FAILED ] = 0
            result_counts[ CC.STATUS_DELETED ] = 0
            result_counts[ CC.STATUS_REDUNDANT ] = 0
            
            job_key.SetVariable( 'result_counts', result_counts )
            
        else:
            
            job_key.SetVariable( 'status', '' )
            
            if job_type == 'import':
                
                job_key.SetVariable( 'page_key', self._page_key )
                job_key.SetVariable( 'range', 1 )
                job_key.SetVariable( 'value', 0 )
                
            elif job_type == 'import_queue':
                
                job_key.SetVariable( 'queue_position', 0 )
                
            elif job_type == 'import_queue_builder':
                
                job_key.SetVariable( 'queue', [] )
                
            
        
        return job_key
        
    
    def CleanBeforeDestroy( self ): self._controller_job_key.Cancel()
    
    def GetJobKey( self, job_type ):
        
        with self._lock:
            
            if job_type == 'controller': return self._controller_job_key
            elif job_type == 'import': return self._import_job_key
            elif job_type == 'import_queue': return self._import_queue_job_key
            elif job_type == 'import_queue_builder': return self._import_queue_builder_job_key
            
        
    
    def GetPendingImportQueueJobs( self ):
        
        with self._lock: return self._pending_import_queue_jobs
        
    
    def PendImportQueueJob( self, job ):
        
        with self._lock: self._pending_import_queue_jobs.append( job )
        
    
    def RemovePendingImportQueueJob( self, job ):
        
        with self._lock:
            
            if job in self._pending_import_queue_jobs: self._pending_import_queue_jobs.remove( job )
            
        
    
    def MovePendingImportQueueJobUp( self, job ):
        
        with self._lock:
            
            if job in self._pending_import_queue_jobs:
                
                index = self._pending_import_queue_jobs.index( job )
                
                if index > 0:
                    
                    self._pending_import_queue_jobs.remove( job )
                    
                    self._pending_import_queue_jobs.insert( index - 1, job )
                    
                
            
        
    
    def MovePendingImportQueueJobDown( self, job ):
        
        with self._lock:
            
            if job in self._pending_import_queue_jobs:
                
                index = self._pending_import_queue_jobs.index( job )
                
                if index + 1 < len( self._pending_import_queue_jobs ):
                    
                    self._pending_import_queue_jobs.remove( job )
                    
                    self._pending_import_queue_jobs.insert( index + 1, job )
                    
                
            
        
    
    def MainLoop( self ):
        
        try:
            
            while not self._controller_job_key.IsDone():
                
                create_import_item = False
                create_import_queue_item = False
                
                while self._controller_job_key.IsPaused():
                    
                    time.sleep( 0.1 )
                    
                    self._import_job_key.Pause()
                    self._import_queue_job_key.Pause()
                    self._import_queue_builder_job_key.Pause()
                    
                    if HydrusGlobals.shutdown or self._controller_job_key.IsDone(): break
                    
                
                if HydrusGlobals.shutdown or self._controller_job_key.IsDone(): break
                
                with self._lock:
                    
                    queue_position = self._import_queue_job_key.GetVariable( 'queue_position' )
                    queue = self._import_queue_builder_job_key.GetVariable( 'queue' )
                    
                    if self._import_job_key.IsDone():
                        
                        result = self._import_job_key.GetVariable( 'result' )
                        
                        result_counts = self._controller_job_key.GetVariable( 'result_counts' )
                        
                        result_counts[ result ] += 1
                        
                        self._import_job_key = self._GetNewJobKey( 'import' )
                        
                        queue_position += 1
                        
                        self._import_queue_job_key.SetVariable( 'queue_position', queue_position )
                        
                    
                    position_string = HydrusData.ConvertValueRangeToPrettyString( queue_position + 1, len( queue ) )
                    
                    if self._import_queue_job_key.IsPaused(): self._import_queue_job_key.SetVariable( 'status', 'paused at ' + position_string )
                    elif self._import_queue_job_key.IsWorking():
                        
                        if self._import_job_key.IsWorking():
                            
                            self._import_queue_job_key.SetVariable( 'status', 'processing ' + position_string )
                            
                        else:
                            
                            if queue_position < len( queue ):
                                
                                self._import_queue_job_key.SetVariable( 'status', 'preparing ' + position_string )
                                
                                self._import_job_key.Begin()
                                
                                import_item = queue[ queue_position ]
                                
                                create_import_item = True
                                
                            else:
                                
                                if self._import_queue_builder_job_key.IsWorking(): self._import_queue_job_key.SetVariable( 'status', 'waiting for more items' )
                                else: self._import_queue_job_key.Finish()
                                
                            
                        
                    else:
                        
                        if self._import_queue_job_key.IsDone():
                            
                            if self._import_queue_job_key.IsCancelled(): status = 'cancelled at ' + position_string
                            else: status = 'done'
                            
                            self._import_queue_job_key = self._GetNewJobKey( 'import_queue' )
                            
                            self._import_queue_builder_job_key = self._GetNewJobKey( 'import_queue_builder' )
                            
                        else: status = ''
                        
                        self._import_queue_job_key.SetVariable( 'status', status )
                        
                        if len( self._pending_import_queue_jobs ) > 0:
                            
                            self._import_queue_job_key.Begin()
                            
                            self._import_queue_builder_job_key.Begin()
                            
                            queue_item = self._pending_import_queue_jobs.pop( 0 )
                            
                            create_import_queue_item = True
                            
                        
                    
                
                # This is outside the lock, as it may call wx-blocking stuff, and other wx bits will sometimes wait on the lock
                if create_import_item:
                    
                    args_generator = self._import_args_generator_factory( self._import_job_key, import_item )
                    
                    HydrusThreading.CallToThread( args_generator )
                    
                
                if create_import_queue_item:
                    
                    queue_builder = self._import_queue_builder_factory( self._import_queue_builder_job_key, queue_item )
                    
                    # make it a daemon, not a thread job, as it has a loop!
                    threading.Thread( target = queue_builder ).start()
                    
                
                time.sleep( 0.05 )
                
            
        except Exception as e:
            
            HydrusData.ShowException( e )
            
        finally:
            
            self._import_job_key.Cancel()
            self._import_queue_job_key.Cancel()
            self._import_queue_builder_job_key.Cancel()
            
        
    
    def StartDaemon( self ): threading.Thread( target = self.MainLoop ).start()
    
class ImportQueueBuilder( object ):
    
    def __init__( self, job_key, item ):
        
        self._job_key = job_key
        self._item = item
        
    
    def __call__( self ):
        
        queue = self._item
        
        self._job_key.SetVariable( 'queue', queue )
        
        self._job_key.Finish()
        
    
class ImportQueueBuilderGallery( ImportQueueBuilder ):
    
    def __init__( self, job_key, item, gallery_parsers_factory ):
        
        ImportQueueBuilder.__init__( self, job_key, item )
        
        self._gallery_parsers_factory = gallery_parsers_factory
        
    
    def __call__( self ):
        
        try:
            
            ( raw_query, self._get_tags_if_redundant, self._file_limit ) = self._item
            
            gallery_parsers = list( self._gallery_parsers_factory( raw_query ) )
            
            gallery_parsers[0].SetupGallerySearch() # for now this is cookie-based for hf, so only have to do it on one
            
            total_urls_found = 0
            
            num_pages_found = 0
            
            page_index = 0
            
            first_run = True
            
            while True:
                
                gallery_parsers_to_remove = []
                
                for gallery_parser in gallery_parsers:
                    
                    urls_in_pages = HydrusData.ConvertIntToPrettyString( total_urls_found ) + ' urls in ' + HydrusData.ConvertIntToPrettyString( num_pages_found ) + ' pages'
                    
                    while self._job_key.IsPaused():
                        
                        time.sleep( 0.1 )
                        
                        self._job_key.SetVariable( 'status', 'paused after finding ' + urls_in_pages )
                        
                        if HydrusGlobals.shutdown or self._job_key.IsDone(): break
                        
                    
                    if HydrusGlobals.shutdown or self._job_key.IsDone(): break
                    
                    self._job_key.SetVariable( 'status', 'found ' + urls_in_pages + '. waiting a few seconds' )
                    
                    if first_run: first_run = False
                    else: time.sleep( 5 )
                    
                    self._job_key.SetVariable( 'status', 'found ' + urls_in_pages + '. looking for next page' )
                    
                    page_of_urls = gallery_parser.GetPage( page_index )
                    
                    if len( page_of_urls ) == 0: gallery_parsers_to_remove.append( gallery_parser )
                    else:
                        
                        queue = self._job_key.GetVariable( 'queue' )
                        
                        queue = list( queue )
                        
                        if self._file_limit is not None:
                            
                            while len( page_of_urls ) > 0 and total_urls_found < self._file_limit:
                                
                                url = page_of_urls.pop( 0 )
                                
                                queue.append( url )
                                
                                total_urls_found += 1
                                
                            
                        else:
                            
                            queue.extend( page_of_urls )
                            
                            total_urls_found += len( page_of_urls )
                            
                        
                        self._job_key.SetVariable( 'queue', queue )
                        
                        num_pages_found += 1
                        
                    
                
                urls_in_pages = HydrusData.ConvertIntToPrettyString( total_urls_found ) + ' urls in ' + HydrusData.ConvertIntToPrettyString( num_pages_found ) + ' pages'
                
                for gallery_parser in gallery_parsers_to_remove: gallery_parsers.remove( gallery_parser )
                
                if len( gallery_parsers ) == 0: break
                
                while self._job_key.IsPaused():
                    
                    time.sleep( 0.1 )
                    
                    self._job_key.SetVariable( 'status', 'paused after finding ' + urls_in_pages )
                    
                    if HydrusGlobals.shutdown or self._job_key.IsDone(): break
                    
                
                if HydrusGlobals.shutdown or self._job_key.IsDone(): break
                
                if self._file_limit is not None and total_urls_found >= self._file_limit: break
                
                page_index += 1
                
            
            self._job_key.SetVariable( 'status', 'finished. found ' + urls_in_pages )
            
            time.sleep( 5 )
            
            self._job_key.SetVariable( 'status', '' )
            
        except Exception as e:
            
            self._job_key.SetVariable( 'status', HydrusData.ToString( e ) )
            
            HydrusData.ShowException( e )
            
            time.sleep( 2 )
            
        finally: self._job_key.Finish()
        
    
class ImportQueueBuilderURLs( ImportQueueBuilder ):
    
    def __call__( self ):
        
        try:
            
            ( url, get_tags_if_redundant, file_limit ) = self._item
            
            self._job_key.SetVariable( 'status', 'Connecting to address' )
            
            try: html = wx.GetApp().DoHTTP( HC.GET, url )
            except: raise Exception( 'Could not download that url' )
            
            self._job_key.SetVariable( 'status', 'parsing html' )
            
            try: urls = ParsePageForURLs( html, url )
            except: raise Exception( 'Could not parse that URL\'s html' )
            
            queue = urls
            
            self._job_key.SetVariable( 'queue', queue )
            
        except Exception as e:
            
            self._job_key.SetVariable( 'status', HydrusData.ToString( e ) )
            
            HydrusData.ShowException( e )
            
            time.sleep( 2 )
            
        finally: self._job_key.Finish()
        
    
class ImportQueueBuilderThread( ImportQueueBuilder ):
    
    def __call__( self ):
        
        try:
            
            ( json_url, image_base ) = self._item
            
            last_thread_check = 0
            image_infos_already_added = set()
            
            first_run = True
            manual_refresh = False
            
            while True:
                
                if not first_run:
                    
                    thread_times_to_check = self._job_key.GetVariable( 'thread_times_to_check' )
                    
                    while thread_times_to_check == 0:
                        
                        self._job_key.SetVariable( 'status', 'checking is finished' )
                        
                        time.sleep( 1 )
                        
                        if self._job_key.IsCancelled(): break
                        
                        thread_times_to_check = self._job_key.GetVariable( 'thread_times_to_check' )
                        
                    
                
                while self._job_key.IsPaused():
                    
                    time.sleep( 0.1 )
                    
                    self._job_key.SetVariable( 'status', 'paused' )
                    
                    if HydrusGlobals.shutdown or self._job_key.IsDone(): break
                    
                
                if HydrusGlobals.shutdown or self._job_key.IsDone(): break
                
                thread_time = self._job_key.GetVariable( 'thread_time' )
                
                if thread_time < 30: thread_time = 30
                
                next_thread_check = last_thread_check + thread_time
                
                manual_refresh = self._job_key.GetVariable( 'manual_refresh' )
                
                not_too_soon_for_manual_refresh = HydrusData.TimeHasPassed( last_thread_check + 10 )
                
                if ( manual_refresh and not_too_soon_for_manual_refresh ) or HydrusData.TimeHasPassed( next_thread_check ):
                    
                    self._job_key.SetVariable( 'status', 'checking thread' )
                    
                    try:
                        
                        raw_json = wx.GetApp().DoHTTP( HC.GET, json_url )
                        
                        json_dict = json.loads( raw_json )
                        
                        posts_list = json_dict[ 'posts' ]
                        
                        image_infos = []
                        
                        for post in posts_list:
                            
                            if 'md5' not in post: continue
                            
                            image_md5 = post[ 'md5' ].decode( 'base64' )
                            image_url = image_base + HydrusData.ToString( post[ 'tim' ] ) + post[ 'ext' ]
                            image_original_filename = post[ 'filename' ] + post[ 'ext' ]
                            
                            image_infos.append( ( image_md5, image_url, image_original_filename ) )
                            
                        
                        image_infos_i_can_add = [ image_info for image_info in image_infos if image_info not in image_infos_already_added ]
                        
                        image_infos_already_added.update( image_infos_i_can_add )
                        
                        if len( image_infos_i_can_add ) > 0:
                            
                            queue = self._job_key.GetVariable( 'queue' )
                            
                            queue = list( queue )
                            
                            queue.extend( image_infos_i_can_add )
                            
                            self._job_key.SetVariable( 'queue', queue )
                            
                        
                    except HydrusExceptions.NotFoundException: raise Exception( 'Thread 404' )
                    except Exception as e:
                        
                        self._job_key.SetVariable( 'status', HydrusData.ToString( e ) )
                        
                        HydrusData.ShowException( e )
                        
                        time.sleep( 2 )
                        
                    
                    last_thread_check = HydrusData.GetNow()
                    
                    if first_run: first_run = False
                    elif manual_refresh: self._job_key.SetVariable( 'manual_refresh', False )
                    else:
                        
                        if thread_times_to_check > 0: self._job_key.SetVariable( 'thread_times_to_check', thread_times_to_check - 1 )
                        
                    
                else: self._job_key.SetVariable( 'status', 'rechecking thread ' + HydrusData.ConvertTimestampToPrettyPending( next_thread_check ) )
                
                time.sleep( 0.1 )
                
            
        except Exception as e:
            
            self._job_key.SetVariable( 'status', HydrusData.ToString( e ) )
            
            HydrusData.ShowException( e )
            
            time.sleep( 2 )
            
        finally: self._job_key.Finish()
        
    
def THREADDownloadURL( job_key, url, url_string ):
    
    def hook( gauge_range, gauge_value ):
        
        if gauge_range is None: text = url_string + ' - ' + HydrusData.ConvertIntToBytes( gauge_value )
        else: text = url_string + ' - ' + HydrusData.ConvertValueRangeToPrettyString( gauge_value, gauge_range )
        
        job_key.SetVariable( 'popup_text_1', text )
        job_key.SetVariable( 'popup_gauge_1', ( gauge_value, gauge_range ) )
        
    
    ( os_file_handle, temp_path ) = HydrusFileHandling.GetTempPath()
    
    try:
        
        wx.GetApp().DoHTTP( HC.GET, url, temp_path = temp_path, report_hooks = [ hook ] )
        
        job_key.DeleteVariable( 'popup_gauge_1' )
        job_key.SetVariable( 'popup_text_1', 'importing ' + url_string )
        
        ( result, hash ) = wx.GetApp().WriteSynchronous( 'import_file', temp_path )
        
    finally:
        
        HydrusFileHandling.CleanUpTempPath( os_file_handle, temp_path )
        
    
    if result in ( CC.STATUS_SUCCESSFUL, CC.STATUS_REDUNDANT ):
        
        job_key.SetVariable( 'popup_text_1', url_string )
        job_key.SetVariable( 'popup_files', { hash } )
        
    elif result == CC.STATUS_DELETED:
        
        job_key.SetVariable( 'popup_text_1', url_string + ' was already deleted!' )
        
    
def Parse4chanPostScreen( html ):
    
    soup = bs4.BeautifulSoup( html )
    
    title_tag = soup.find( 'title' )
    
    if title_tag.string == 'Post successful!': return ( 'success', None )
    elif title_tag.string == '4chan - Banned':
        
        print( repr( soup ) )
        
        text = 'You are banned from this board! html written to log.'
        
        HydrusData.ShowText( text )
        
        return ( 'big error', text )
        
    else:
        
        try:
            
            problem_tag = soup.find( id = 'errmsg' )
            
            if problem_tag is None:
                
                try: print( repr( soup ) )
                except: pass
                
                text = 'Unknown problem; html written to log.'
                
                HydrusData.ShowText( text )
                
                return ( 'error', text )
                
            
            problem = HydrusData.ToString( problem_tag )
            
            if 'CAPTCHA' in problem: return ( 'captcha', None )
            elif 'seconds' in problem: return ( 'too quick', None )
            elif 'Duplicate' in problem: return ( 'error', 'duplicate file detected' )
            else: return ( 'error', problem )
            
        except: return ( 'error', 'unknown error' )
        
    
def ParsePageForURLs( html, starting_url ):
    
    soup = bs4.BeautifulSoup( html )
    
    all_links = soup.find_all( 'a' )
    
    links_with_images = [ link for link in all_links if len( link.find_all( 'img' ) ) > 0 ]
    
    urls = [ urlparse.urljoin( starting_url, link[ 'href' ] ) for link in links_with_images ]
    
    # old version included (images that don't have a link wrapped around them)'s src
    
    return urls
    