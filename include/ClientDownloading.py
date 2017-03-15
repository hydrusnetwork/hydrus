import bs4
import ClientNetworking
import HydrusConstants as HC
import HydrusExceptions
import HydrusPaths
import HydrusSerialisable
import json
import lxml # to force import for later bs4 stuff
import os
import pafy
import re
import threading
import urllib
import urlparse
import HydrusData
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
            
        
    
def GetGalleryStreamIdentifiers( gallery_identifier ):
    
    site_type = gallery_identifier.GetSiteType()
    
    if site_type == HC.SITE_TYPE_HENTAI_FOUNDRY_ARTIST:
        
        gallery_stream_identifiers = [ GalleryIdentifier( HC.SITE_TYPE_HENTAI_FOUNDRY_ARTIST_PICTURES ), GalleryIdentifier( HC.SITE_TYPE_HENTAI_FOUNDRY_ARTIST_SCRAPS ) ]
        
    elif site_type == HC.SITE_TYPE_NEWGROUNDS:
        
        gallery_stream_identifiers = [ GalleryIdentifier( HC.SITE_TYPE_NEWGROUNDS_GAMES ), GalleryIdentifier( HC.SITE_TYPE_NEWGROUNDS_MOVIES ) ]
        
    else:
        
        gallery_stream_identifiers = [ gallery_identifier ]
        
    
    return gallery_stream_identifiers
    
def SetExtraURLInfo( url, info ):
    
    with URL_EXTRA_INFO_LOCK:
        
        URL_EXTRA_INFO[ url ] = info
        
    
def GetGallery( gallery_identifier ):
    
    site_type = gallery_identifier.GetSiteType()
    
    if site_type == HC.SITE_TYPE_BOORU:
        
        booru_name = gallery_identifier.GetAdditionalInfo()
        
        return GalleryBooru( booru_name )
        
    elif site_type == HC.SITE_TYPE_DEVIANT_ART:
        
        return GalleryDeviantArt()
        
    elif site_type == HC.SITE_TYPE_GIPHY:
        
        return GalleryGiphy()
        
    elif site_type in ( HC.SITE_TYPE_HENTAI_FOUNDRY, HC.SITE_TYPE_HENTAI_FOUNDRY_ARTIST ):
        
        return GalleryHentaiFoundry()
        
    elif site_type == HC.SITE_TYPE_HENTAI_FOUNDRY_ARTIST_PICTURES:
        
        return GalleryHentaiFoundryArtistPictures()
        
    elif site_type == HC.SITE_TYPE_HENTAI_FOUNDRY_ARTIST_SCRAPS:
        
        return GalleryHentaiFoundryArtistScraps()
        
    elif site_type == HC.SITE_TYPE_HENTAI_FOUNDRY_TAGS:
        
        return GalleryHentaiFoundryTags()
        
    elif site_type == HC.SITE_TYPE_NEWGROUNDS:
        
        return GalleryNewgrounds()
        
    elif site_type == HC.SITE_TYPE_NEWGROUNDS_GAMES:
        
        return GalleryNewgroundsGames()
        
    elif site_type == HC.SITE_TYPE_NEWGROUNDS_MOVIES:
        
        return GalleryNewgroundsMovies()
        
    elif site_type == HC.SITE_TYPE_PIXIV:
        
        return GalleryPixiv()
        
    elif site_type == HC.SITE_TYPE_PIXIV_ARTIST_ID:
        
        return GalleryPixivArtistID()
        
    elif site_type == HC.SITE_TYPE_PIXIV_TAG:
        
        return GalleryPixivTag()
        
    elif site_type == HC.SITE_TYPE_TUMBLR:
        
        return GalleryTumblr()
        
    
_8CHAN_BOARDS_TO_MEDIA_HOSTS = {}

def GetImageboardFileURL( thread_url, filename, ext ):
    
    ( thread_url, host, board, thread_id ) = ParseImageboardThreadURL( thread_url )
    
    is_4chan = '4chan.org' in host
    is_8chan = '8ch.net' in host
    
    if is_4chan:
        
        return 'http://i.4cdn.org/' + board + '/' + filename + ext
        
    elif is_8chan:
        
        if len( filename ) == 64: # new sha256 filename
            
            return 'https://media.8ch.net/file_store/' + filename + ext
            
        else:
            
            if board not in _8CHAN_BOARDS_TO_MEDIA_HOSTS:
                
                try:
                    
                    html_url = 'http://8ch.net/' + board + '/res/' + thread_id + '.html'
                    
                    response = ClientNetworking.RequestsGet( html_url )
                    
                    thread_html = response.content
                    
                    soup = GetSoup( thread_html )
                    
                    file_infos = soup.find_all( 'p', class_ = "fileinfo" )
                    
                    example_file_url = file_infos[0].find( 'a' )[ 'href' ]
                    
                    parse_result = urlparse.urlparse( example_file_url )
                    
                    hostname = parse_result.hostname
                    
                    if hostname is None:
                        
                        hostname = '8ch.net'
                        
                    
                    _8CHAN_BOARDS_TO_MEDIA_HOSTS[ board ] = hostname
                    
                except Exception as e:
                    
                    _8CHAN_BOARDS_TO_MEDIA_HOSTS[ board ] = 'media.8ch.net'
                    
                
            
            media_host = _8CHAN_BOARDS_TO_MEDIA_HOSTS[ board ]
        
            return 'http://' + media_host + '/' + board + '/src/' + filename + ext
            
        
    
def GetImageboardThreadJSONURL( thread_url ):
    
    ( thread_url, host, board, thread_id ) = ParseImageboardThreadURL( thread_url )
    
    is_4chan = '4chan.org' in host
    is_8chan = '8ch.net' in host
    
    # 4chan
    # http://a.4cdn.org/asp/thread/382059.json
    
    # 8chan
    # http://8ch.net/v/res/406061.json
    
    if is_4chan:
        
        return 'http://a.4cdn.org/' + board + '/thread/' + thread_id + '.json'
        
    elif is_8chan:
        
        return 'http://8ch.net/' + board + '/res/' + thread_id + '.json'
        
    
def GetSoup( html ):
    
    return bs4.BeautifulSoup( html, 'lxml' )
    
def GetYoutubeFormats( youtube_url ):
    
    try: p = pafy.new( youtube_url )
    except Exception as e:
        
        raise Exception( 'Could not fetch video info from youtube!' + os.linesep + HydrusData.ToUnicode( e ) )
        
    
    info = { ( s.extension, s.resolution ) : ( s.url, s.title ) for s in p.streams if s.extension in ( 'flv', 'mp4', 'webm' ) }
    
    return info
    
def THREADDownloadURL( job_key, url, url_string ):
    
    job_key.SetVariable( 'popup_title', url_string )
    job_key.SetVariable( 'popup_text_1', 'initialising' )
    
    ( os_file_handle, temp_path ) = HydrusPaths.GetTempPath()
    
    try:
        
        response = ClientNetworking.RequestsGet( url, stream = True )
        
        with open( temp_path, 'wb' ) as f:
            
            ClientNetworking.StreamResponseToFile( job_key, response, f )
            
        
        job_key.SetVariable( 'popup_text_1', 'importing' )
        
        client_files_manager = HydrusGlobals.client_controller.GetClientFilesManager()
        
        ( result, hash ) = client_files_manager.ImportFile( temp_path )
        
    except HydrusExceptions.CancelledException:
        
        return
        
    except HydrusExceptions.NetworkException:
        
        job_key.Cancel()
        
        raise
        
    finally:
        
        HydrusPaths.CleanUpTempPath( os_file_handle, temp_path )
        
    
    if result in ( CC.STATUS_SUCCESSFUL, CC.STATUS_REDUNDANT ):
        
        if result == CC.STATUS_SUCCESSFUL:
            
            job_key.SetVariable( 'popup_text_1', 'successful!' )
            
        else:
            
            job_key.SetVariable( 'popup_text_1', 'was already in the database!' )
            
        
        job_key.SetVariable( 'popup_files', { hash } )
        
    elif result == CC.STATUS_DELETED:
        
        job_key.SetVariable( 'popup_text_1', 'had already been deleted!' )
        
    
    job_key.Finish()
    
def THREADDownloadURLs( job_key, urls, title ):
    
    job_key.SetVariable( 'popup_title', title )
    job_key.SetVariable( 'popup_text_1', 'initialising' )
    
    num_successful = 0
    num_redundant = 0
    num_deleted = 0
    num_failed = 0
    
    successful_hashes = set()
    
    for ( i, url ) in enumerate( urls ):
        
        ( i_paused, should_quit ) = job_key.WaitIfNeeded()
        
        if should_quit:
            
            break
            
        
        job_key.SetVariable( 'popup_text_1', HydrusData.ConvertValueRangeToPrettyString( i + 1, len( urls ) ) )
        job_key.SetVariable( 'popup_gauge_1', ( i + 1, len( urls ) ) )
        
        ( os_file_handle, temp_path ) = HydrusPaths.GetTempPath()
        
        try:
            
            try:
                
                response = ClientNetworking.RequestsGet( url, stream = True )
                
                with open( temp_path, 'wb' ) as f:
                    
                    ClientNetworking.StreamResponseToFile( job_key, response, f )
                    
                
            except HydrusExceptions.CancelledException:
                
                return
                
            except HydrusExceptions.NetworkException:
                
                job_key.Cancel()
                
                raise
                
            
            try:
                
                job_key.SetVariable( 'popup_text_2', 'importing' )
                
                client_files_manager = HydrusGlobals.client_controller.GetClientFilesManager()
                
                ( result, hash ) = client_files_manager.ImportFile( temp_path )
                
            except Exception as e:
                
                job_key.DeleteVariable( 'popup_text_2' )
                
                HydrusData.Print( url + ' failed to import!' )
                HydrusData.PrintException( e )
                
                num_failed += 1
                
                continue
                
            
        finally:
            
            HydrusPaths.CleanUpTempPath( os_file_handle, temp_path )
            
        
        if result in ( CC.STATUS_SUCCESSFUL, CC.STATUS_REDUNDANT ):
            
            if result == CC.STATUS_SUCCESSFUL:
                
                num_successful += 1
                
            else:
                
                num_redundant += 1
                
            
            successful_hashes.add( hash )
            
        elif result == CC.STATUS_DELETED:
            
            num_deleted += 1
            
        
    
    text_components = []
    
    if num_successful > 0:
        
        text_components.append( HydrusData.ConvertIntToPrettyString( num_successful ) + ' successful' )
        
    
    if num_redundant > 0:
        
        text_components.append( HydrusData.ConvertIntToPrettyString( num_redundant ) + ' already in db' )
        
    
    if num_deleted > 0:
        
        text_components.append( HydrusData.ConvertIntToPrettyString( num_deleted ) + ' deleted' )
        
    
    if num_failed > 0:
        
        text_components.append( HydrusData.ConvertIntToPrettyString( num_failed ) + ' failed (errors written to log)' )
        
    
    job_key.SetVariable( 'popup_text_1', ', '.join( text_components ) )
    
    if len( successful_hashes ) > 0:
        
        job_key.SetVariable( 'popup_files', successful_hashes )
        
    
    job_key.DeleteVariable( 'popup_gauge_1' )
    job_key.DeleteVariable( 'popup_text_2' )
    job_key.DeleteVariable( 'popup_gauge_2' )
    
    job_key.Finish()
    
def Parse4chanPostScreen( html ):
    
    soup = GetSoup( html )
    
    title_tag = soup.find( 'title' )
    
    if title_tag.string == 'Post successful!': return ( 'success', None )
    elif title_tag.string == '4chan - Banned':
        
        HydrusData.Print( soup )
        
        text = 'You are banned from this board! html written to log.'
        
        HydrusData.ShowText( text )
        
        return ( 'big error', text )
        
    else:
        
        try:
            
            problem_tag = soup.find( id = 'errmsg' )
            
            if problem_tag is None:
                
                HydrusData.Print( soup )
                
                text = 'Unknown problem; html written to log.'
                
                HydrusData.ShowText( text )
                
                return ( 'error', text )
                
            
            problem = HydrusData.ToUnicode( problem_tag )
            
            if 'CAPTCHA' in problem: return ( 'captcha', None )
            elif 'seconds' in problem: return ( 'too quick', None )
            elif 'Duplicate' in problem: return ( 'error', 'duplicate file detected' )
            else: return ( 'error', problem )
            
        except: return ( 'error', 'unknown error' )
        
    
def ParseImageboardFileURLFromPost( thread_url, post ):
    
    url_filename = str( post[ 'tim' ] )
    url_ext = post[ 'ext' ]
    
    file_original_filename = post[ 'filename' ]
    file_url = GetImageboardFileURL( thread_url, url_filename, url_ext )
    
    if 'md5' in post:
        
        file_md5_base64 = post[ 'md5' ]
        
    else:
        
        file_md5_base64 = None
        
    
    return ( file_url, file_md5_base64, file_original_filename )
    
def ParseImageboardFileURLsFromJSON( thread_url, raw_json ):

    json_dict = json.loads( raw_json )
    
    posts_list = json_dict[ 'posts' ]
    
    file_infos = []
    
    for post in posts_list:
        
        if 'filename' not in post:
            
            continue
            
        
        file_infos.append( ParseImageboardFileURLFromPost( thread_url, post ) )
        
        if 'extra_files' in post:
            
            for extra_file in post[ 'extra_files' ]:
                
                if 'filename' not in extra_file:
                    
                    continue
                    
                
                file_infos.append( ParseImageboardFileURLFromPost( thread_url, extra_file ) )
                
            
        
    
    return file_infos
    
def ParseImageboardThreadURL( thread_url ):
    
    try:
        
        if '#' in thread_url:
            
            ( thread_url, post_anchor_gumpf ) = thread_url.split( '#', 1 )
            
        
        parse_result = urlparse.urlparse( thread_url )
        
        host = parse_result.hostname
        
        request = parse_result.path
        
        if host is None or request is None:
            
            raise Exception()
            
        
    except:
        
        raise Exception ( 'Could not understand that url!' )
    
    is_4chan = '4chan.org' in host
    is_8chan = '8ch.net' in host
    
    if not ( is_4chan or is_8chan ):
        
        raise Exception( 'This only works for 4chan and 8chan right now!' )
        
    
    try:
        
        # 4chan
        # /asp/thread/382059/post-your-favourite-martial-arts-video-if-martin
        
        # 8chan
        # /v/res/406061.html
        
        if is_4chan:
            
            ( board, rest_of_request ) = request[1:].split( '/thread/', 1 )
            
            if '/' in rest_of_request:
                
                ( thread_id, gumpf ) = rest_of_request.split( '/' )
                
            else:
                
                thread_id = rest_of_request
                
            
        elif is_8chan:
            
            ( board, rest_of_request ) = request[1:].split( '/res/', 1 )
            
            thread_id = rest_of_request[:-5]
            
        
    except Exception as e:
        
        raise Exception( 'Could not understand the board or thread id!' )
        
    
    return ( thread_url, host, board, thread_id )
    
def ParsePageForURLs( html, starting_url ):
    
    soup = GetSoup( html )
    
    all_links = soup.find_all( 'a' )
    
    links_with_images = [ link for link in all_links if len( link.find_all( 'img' ) ) > 0 ]
    
    urls = [ urlparse.urljoin( starting_url, link[ 'href' ] ) for link in links_with_images ]
    
    return urls
    
class GalleryIdentifier( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_GALLERY_IDENTIFIER
    SERIALISABLE_VERSION = 1
    
    def __init__( self, site_type = None, additional_info = None ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._site_type = site_type
        self._additional_info = additional_info
        
    
    def __eq__( self, other ):
        
        return self.__hash__() == other.__hash__()
        
    
    def __hash__( self ):
        
        return ( self._site_type, self._additional_info ).__hash__()
        
    
    def __ne__( self, other ):
        
        return self.__hash__() != other.__hash__()
        
    
    def __repr__( self ):
        
        text = 'Gallery Identifier: ' + HC.site_type_string_lookup[ self._site_type ]
        
        if self._site_type == HC.SITE_TYPE_BOORU:
            
            text += ': ' + HydrusData.ToUnicode( self._additional_info )
            
        
        return text
        
    
    def _GetSerialisableInfo( self ):
        
        return ( self._site_type, self._additional_info )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._site_type, self._additional_info ) = serialisable_info
        
    
    def GetAdditionalInfo( self ):
        
        return self._additional_info
        
    
    def GetSiteType( self ):
        
        return self._site_type
        
    
    def ToString( self ):
        
        text = HC.site_type_string_lookup[ self._site_type ]
        
        if self._site_type == HC.SITE_TYPE_BOORU and self._additional_info is not None:
            
            booru_name = self._additional_info
            
            text = HC.site_type_string_lookup[ self._site_type ] + ': ' + booru_name
            
        
        return text
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_GALLERY_IDENTIFIER ] = GalleryIdentifier

class Gallery( object ):
    
    def _AddSessionCookies( self, request_headers ): pass
    
    def _FetchData( self, url, referer_url = None, report_hooks = None, temp_path = None ):
        
        if report_hooks is None: report_hooks = []
        
        request_headers = {}
        
        if referer_url is not None:
            
            request_headers[ 'Referer' ] = referer_url
            
        
        self._AddSessionCookies( request_headers )
        
        return HydrusGlobals.client_controller.DoHTTP( HC.GET, url, request_headers = request_headers, report_hooks = report_hooks, temp_path = temp_path )
        
    
    def _GetGalleryPageURL( self, query, page_index ):
        
        raise NotImplementedError()
        
    
    def _ParseGalleryPage( self, data, url ):
        
        raise NotImplementedError()
        
    
    def GetFile( self, temp_path, url, report_hooks = None ):
        
        self._FetchData( url, report_hooks = report_hooks, temp_path = temp_path )
        
    
    def GetFileAndTags( self, temp_path, url, report_hooks = None ):
        
        temp_path = self.GetFile( temp_path, url, report_hooks )
        tags = self.GetTags( url, report_hooks = report_hooks )
        
        return tags
        
    
    def GetPage( self, query, page_index ):
        
        gallery_url = self._GetGalleryPageURL( query, page_index )
        
        data = self._FetchData( gallery_url )
        
        ( page_of_urls, definitely_no_more_pages ) = self._ParseGalleryPage( data, gallery_url )
        
        return ( page_of_urls, definitely_no_more_pages )
        
    
    def GetTags( self, url, report_hooks = None ):
        
        raise NotImplementedError()
        
    
class GalleryBooru( Gallery ):
    
    def __init__( self, booru_name ):
        
        try:
            
            self._booru = HydrusGlobals.client_controller.Read( 'remote_booru', booru_name )
            
        except:
            
            raise Exception( 'Attempted to find booru "' + booru_name + '", but it was missing from the database!' )
            
        
        self._gallery_advance_num = None
        
        ( self._search_url, self._advance_by_page_num, self._search_separator, self._thumb_classname ) = self._booru.GetGalleryParsingInfo()
        
        Gallery.__init__( self )
        
    
    def _GetGalleryPageURL( self, query, page_index ):
        
        if self._advance_by_page_num:
            
            url_index = page_index + 1
            
        else:
            
            if self._gallery_advance_num is None:
                
                if page_index == 0:
                    
                    url_index = page_index
                    
                else:
                    
                    self.GetPage( query, 0 )
                    
                    if self._gallery_advance_num is None:
                        
                        raise Exception( 'Unable to calculate the booru\'s gallery advance number.' )
                        
                    else:
                        
                        url_index = page_index * self._gallery_advance_num
                        
                    
                
            else:
                
                url_index = page_index * self._gallery_advance_num
                
            
        
        tags = query.split( ' ' )
        
        if 'e621' in self._search_url:
            
            tags_to_use = []
            
            for tag in tags:
                
                if '/' in tag:
                    
                    tag = tag.replace( '/', '%-2F' )
                    
                
                tags_to_use.append( tag )
                
            
            tags = tags_to_use
            
        
        tags_replace = self._search_separator.join( [ urllib.quote( HydrusData.ToByteString( tag ), '' ) for tag in tags ] )
        
        return self._search_url.replace( '%tags%', tags_replace ).replace( '%index%', str( url_index ) )
        
    
    def _ParseGalleryPage( self, html, url_base ):
        
        definitely_no_more_pages = False
        
        urls_set = set()
        urls = []
        
        soup = GetSoup( html )
        
        # this catches 'post-preview' along with 'post-preview not-approved' sort of bullshit
        def starts_with_classname( classname ): return classname is not None and classname.startswith( self._thumb_classname )
        
        thumbnails = soup.find_all( class_ = starts_with_classname )
        
        # this is a sankaku thing
        popular_thumbnail_parent = soup.find( id = 'popular-preview' )
        
        if popular_thumbnail_parent is not None:
            
            popular_thumbnails = popular_thumbnail_parent.find_all( class_ = starts_with_classname )
            
            thumbnails = thumbnails[ len( popular_thumbnails ) : ]
            
        
        if self._gallery_advance_num is None:
            
            if len( thumbnails ) == 0:
                
                definitely_no_more_pages = True
                
            else:
                
                self._gallery_advance_num = len( thumbnails )
                
            
        
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
                    
                
            
        
        return ( urls, definitely_no_more_pages )
        
    
    def _ParseImagePage( self, html, url_base ):
        
        ( search_url, search_separator, advance_by_page_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces ) = self._booru.GetData()
        
        soup = GetSoup( html )
        
        image_base = None
        
        image_url = None
        
        try:
            
            if image_id is not None:
                
                image = soup.find( id = image_id )
                
                if image is None:
                    
                    image_string = soup.find( text = re.compile( 'Save this file' ) )
                    
                    if image_string is None: image_string = soup.find( text = re.compile( 'Save this video' ) )
                    
                    if image_string is None:
                        
                        # catchall for rule34hentai.net's webms
                        
                        if image_url is None:
                            
                            a_tags = soup.find_all( 'a' )
                            
                            for a_tag in a_tags:
                                
                                href = a_tag[ 'href' ]
                                
                                if href is not None:
                                    
                                    if href.endswith( '.webm' ):
                                        
                                        image_url = href
                                        
                                        break
                                        
                                    
                                
                            
                        
                    else:
                        
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
                
                ok_link = None
                better_link = None
                
                for link in links:
                    
                    if link.string is not None:
                        
                        if link.string.startswith( image_data ):
                            
                            ok_link = link[ 'href' ]
                            
                        
                        if link.string.startswith( 'Download PNG' ):
                            
                            better_link = link[ 'href' ]
                            
                            break
                            
                        
                    
                
                if better_link is not None:
                    
                    image_url = better_link
                    
                else:
                    
                    image_url = ok_link
                    
                
            
        except Exception as e:
            
            raise HydrusExceptions.DataMissing( 'Could not parse a download link for ' + url_base + '!' + os.linesep + HydrusData.ToUnicode( e ) )
            
        
        if image_url is None:
            
            raise HydrusExceptions.DataMissing( 'Could not parse a download link for ' + url_base + '!' )
            
        
        image_url = urlparse.urljoin( url_base, image_url )
        
        tags = []
        
        for ( tag_classname, namespace ) in tag_classnames_to_namespaces.items():
            
            tag_list_entries = soup.find_all( class_ = tag_classname )
            
            for tag_list_entry in tag_list_entries:
                
                links = tag_list_entry.find_all( 'a' )
                
                if tag_list_entry.name == 'a': links.append( tag_list_entry )
                
                for link in links:
                    
                    if link.string is None:
                        
                        continue
                        
                    
                    if link.string not in ( '?', '-', '+' ):
                        
                        if namespace == '': tags.append( link.string )
                        else: tags.append( namespace + ':' + link.string )
                        
                    
                
            
        
        return ( image_url, tags )
        
    
    def _GetFileURLAndTags( self, url, report_hooks = None ):
        
        html = self._FetchData( url, report_hooks = report_hooks )
        
        return self._ParseImagePage( html, url )
        
    
    def GetFile( self, temp_path, url, report_hooks = None ):
        
        ( file_url, tags ) = self._GetFileURLAndTags( url, report_hooks = report_hooks )
        
        self._FetchData( file_url, referer_url = url, report_hooks = report_hooks, temp_path = temp_path )
        
    
    def GetFileAndTags( self, temp_path, url, report_hooks = None ):
        
        ( file_url, tags ) = self._GetFileURLAndTags( url, report_hooks = report_hooks )
        
        self._FetchData( file_url, referer_url = url, report_hooks = report_hooks, temp_path = temp_path )
        
        return tags
        
    
    def GetTags( self, url, report_hooks = None ):
        
        ( file_url, tags ) = self._GetFileURLAndTags( url, report_hooks = report_hooks )
        
        return tags
        
    
class GalleryDeviantArt( Gallery ):
    
    def _AddSessionCookies( self, request_headers ):
        
        manager = HydrusGlobals.client_controller.GetManager( 'web_sessions' )
        
        cookies = manager.GetCookies( 'deviant art' )
        
        ClientNetworking.AddCookiesToHeaders( cookies, request_headers )
        
    
    def _GetGalleryPageURL( self, query, page_index ):
        
        artist = query
        
        return 'http://' + artist + '.deviantart.com/gallery/?catpath=/&offset=' + str( page_index * 24 )
        
    
    def _ParseGalleryPage( self, html, url_base ):
        
        definitely_no_more_pages = False
        
        urls = []
        
        soup = GetSoup( html )
        
        thumbs_container = soup.find( 'div', class_ = 'torpedo-container' )
        
        artist = url_base.split( 'http://' )[1].split( '.deviantart.com' )[0]
        
        thumbs = thumbs_container.find_all( 'span', class_ = 'thumb' )
        
        for thumb in thumbs:
            
            url = thumb[ 'href' ] # something in the form of blah.da.com/art/blah-123456
            
            urls.append( url )
            
            tags = []
            
            tags.append( 'creator:' + artist )
            
            title_tag = thumb.find( 'span', class_ = 'title' )
            
            if title_tag is not None:
                
                title = title_tag.string
                
                if title is not None and title != '':
                    
                    tags.append( 'title:' + title )
                    
                
            
            SetExtraURLInfo( url, tags )
            
        
        return ( urls, definitely_no_more_pages )
        
    
    def _ParseImagePage( self, html, referer_url ):
        
        soup = GetSoup( html )
        
        download_button = soup.find( 'a', class_ = 'dev-page-download' )
        
        if download_button is None:
            
            # this method maxes out at 1024 width
            
            img = soup.find( class_ = 'dev-content-full' )
            
            if img is None:
                
                # this probably means it is mature
                # DA hide the url pretty much everywhere except the tumblr share thing
                
                a_tumblr = soup.find( id = 'gmi-ResourceViewShareTumblr' )
                
                tumblr_url = a_tumblr[ 'href' ] # http://www.tumblr.com/share/photo?source=http%3A%2F%2Fimg09.deviantart.net%2Ff19a%2Fi%2F2015%2F054%2Fe%2Fd%2Fass_by_gmgkaiser-d8j7ija.png&amp;caption=%3Ca+href%3D%22http%3A%2F%2Fgmgkaiser.deviantart.com%2Fart%2Fass-515992726%22%3Eass%3C%2Fa%3E+by+%3Ca+href%3D%22http%3A%2F%2Fgmgkaiser.deviantart.com%2F%22%3EGMGkaiser%3C%2Fa%3E&amp;clickthru=http%3A%2F%2Fgmgkaiser.deviantart.com%2Fart%2Fass-515992726
                
                parse_result = urlparse.urlparse( tumblr_url )
                
                query_parse_result = urlparse.parse_qs( parse_result.query )
                
                img_url = query_parse_result[ 'source' ][0] # http://img09.deviantart.net/f19a/i/2015/054/e/d/ass_by_gmgkaiser-d8j7ija.png
                
            else:
                
                img_url = img[ 'src' ]
                
            
        else:
            
            # something like http://www.deviantart.com/download/518046750/varda_and_the_sacred_trees_of_valinor_by_implosinoatic-d8kfjfi.jpg?token=476cb73aa2ab22bb8554542bc9f14982e09bd534&ts=1445717843
            # given the right cookies, it redirects to the truly fullsize image_url
            # otherwise, it seems to redirect to a small interstitial redirect page that heads back to the original image page
            
            img_url = download_button[ 'href' ]
            
        
        return img_url
        
    
    def _GetFileURL( self, url, report_hooks = None ):
        
        html = self._FetchData( url, report_hooks = report_hooks )
        
        return self._ParseImagePage( html, url )
        
    
    def GetFile( self, temp_path, url, report_hooks = None ):
        
        file_url = self._GetFileURL( url, report_hooks = report_hooks )
        
        self._FetchData( file_url, referer_url = url, report_hooks = report_hooks, temp_path = temp_path )
        
    
    def GetTags( self, url, report_hooks = None ):
        
        result = GetExtraURLInfo( url )
        
        if result is None:
            
            return []
            
        else:
            
            return result
            
        
    
class GalleryGiphy( Gallery ):
    
    def _GetGalleryPageURL( self, query, page_index ):
        
        tag = query
        
        return 'http://giphy.com/api/gifs?tag=' + urllib.quote( HydrusData.ToByteString( tag ).replace( ' ', '+' ), '' ) + '&page=' + str( page_index + 1 )
        
    
    def _ParseGalleryPage( self, data, url_base ):
        
        definitely_no_more_pages = False
        
        json_dict = json.loads( data )
        
        urls = []
        
        if 'data' in json_dict:
            
            json_data = json_dict[ 'data' ]
            
            for d in json_data:
                
                url = d[ 'image_original_url' ]
                id = d[ 'id' ]
                
                SetExtraURLInfo( url, id )
                
                urls.append( url )
                
            
        
        return ( urls, definitely_no_more_pages )
        
    
    def GetTags( self, url, report_hooks = None ):
        
        id = GetExtraURLInfo( url )
        
        if id is None:
            
            return []
            
        else:
            
            url = 'http://giphy.com/api/gifs/' + str( id )
            
            try:
                
                raw_json = self._FetchData( url, report_hooks = report_hooks )
                
                json_dict = json.loads( raw_json )
                
                tags_data = json_dict[ 'data' ][ 'tags' ]
                
                return [ tag_data[ 'name' ] for tag_data in tags_data ]
                
            except Exception as e:
                
                HydrusData.ShowException( e )
                
                return []
                
            
        
    
class GalleryHentaiFoundry( Gallery ):
    
    def _AddSessionCookies( self, request_headers ):
        
        manager = HydrusGlobals.client_controller.GetManager( 'web_sessions' )
        
        cookies = manager.GetCookies( 'hentai foundry' )
        
        ClientNetworking.AddCookiesToHeaders( cookies, request_headers )
        
    
    def _GetFileURLAndTags( self, url, report_hooks = None ):
        
        html = self._FetchData( url, report_hooks = report_hooks )
        
        return self._ParseImagePage( html, url )
        
    
    def _ParseGalleryPage( self, html, url_base ):
        
        definitely_no_more_pages = False
        
        urls_set = set()
        
        soup = GetSoup( html )
        
        def correct_url( href ):
            
            if href is None:
                
                return False
                
            
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
        if 'class="next"' not in html:
            
            definitely_no_more_pages = True
            
        
        return ( urls, definitely_no_more_pages )
        
    
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
            
            raise Exception( 'Could not parse image url!' + os.linesep + HydrusData.ToUnicode( e ) )
            
        
        soup = GetSoup( html )
        
        tags = []
        
        try:
            
            title = soup.find( 'title' )
            
            ( data, nothing ) = title.string.split( ' - Hentai Foundry' )
            
            data_reversed = data[::-1] # want to do it right-side first, because title might have ' by ' in it
            
            ( artist_reversed, title_reversed ) = data_reversed.split( ' yb ' )
            
            artist = artist_reversed[::-1]
            
            title = title_reversed[::-1]
            
            tags.append( 'creator:' + artist )
            tags.append( 'title:' + title )
            
        except: pass
        
        return ( image_url, tags )
        
    
    def GetFile( self, temp_path, url, report_hooks = None ):
        
        ( file_url, tags ) = self._GetFileURLAndTags( url, report_hooks = report_hooks )
        
        self._FetchData( file_url, referer_url = url, report_hooks = report_hooks, temp_path = temp_path )
        
    
    def GetFileAndTags( self, temp_path, url, report_hooks = None ):
        
        ( file_url, tags ) = self._GetFileURLAndTags( url, report_hooks = report_hooks )
        
        self._FetchData( file_url, referer_url = url, report_hooks = report_hooks, temp_path = temp_path )
        
        return tags
        
    
    def GetTags( self, url, report_hooks = None ):
        
        ( file_url, tags ) = self._GetFileURLAndTags( url, report_hooks = report_hooks )
        
        return tags
        
    
class GalleryHentaiFoundryArtistPictures( GalleryHentaiFoundry ):
    
    def _GetGalleryPageURL( self, query, page_index ):
        
        artist = query
        
        gallery_url = 'http://www.hentai-foundry.com/pictures/user/' + artist
        
        return gallery_url + '/page/' + str( page_index + 1 )
        
    
class GalleryHentaiFoundryArtistScraps( GalleryHentaiFoundry ):
    
    def _GetGalleryPageURL( self, query, page_index ):
        
        artist = query
        
        gallery_url = 'http://www.hentai-foundry.com/pictures/user/' + artist + '/scraps'
        
        return gallery_url + '/page/' + str( page_index + 1 )
        
    
class GalleryHentaiFoundryTags( GalleryHentaiFoundry ):
    
    def _GetGalleryPageURL( self, query, page_index ):
        
        tags = query.split( ' ' )
        
        return 'http://www.hentai-foundry.com/search/pictures?query=' + '+'.join( tags ) + '&search_in=all&scraps=-1&page=' + str( page_index + 1 )
        # scraps = 0 hide
        # -1 means show both
        # 1 means scraps only. wetf
        
    
class GalleryNewgrounds( Gallery ):
    
    def _GetFileURLAndTags( self, url, report_hooks = None ):
        
        html = self._FetchData( url, report_hooks = report_hooks )
        
        return self._ParseImagePage( html, url )
        
    
    def _ParseGalleryPage( self, html, url_base ):
        
        soup = GetSoup( html )
        
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
            
        
        definitely_no_more_pages = True
        
        return ( urls, definitely_no_more_pages )
        
    
    def _ParseImagePage( self, html, url_base ):
        
        soup = GetSoup( html )
        
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
        
        flash_url = html.split( '"http:\/\/uploads.ungrounded.net\/', 1 )[1]
        
        flash_url = flash_url.split( '"', 1 )[0]
        
        flash_url = flash_url.replace( "\/", '/' )
        
        flash_url = 'http://uploads.ungrounded.net/' + flash_url
        
        return ( flash_url, tags )
        
    
    def GetFile( self, temp_path, url, report_hooks = None ):
        
        ( file_url, tags ) = self._GetFileURLAndTags( url, report_hooks = report_hooks )
        
        self._FetchData( file_url, referer_url = url, report_hooks = report_hooks, temp_path = temp_path )
        
    
    def GetFileAndTags( self, temp_path, url, report_hooks = None ):
        
        ( file_url, tags ) = self._GetFileURLAndTags( url, report_hooks = report_hooks )
        
        self._FetchData( file_url, referer_url = url, report_hooks = report_hooks, temp_path = temp_path )
        
        return tags
        
    
    def GetTags( self, url, report_hooks = None ):
        
        ( file_url, tags ) = self._GetFileURLAndTags( url, report_hooks = report_hooks )
        
        return tags
        
    
class GalleryNewgroundsGames( GalleryNewgrounds ):
    
    def _GetGalleryPageURL( self, query, page_index ):
        
        artist = query
        
        return 'http://' + artist + '.newgrounds.com/games/'
        
    
class GalleryNewgroundsMovies( GalleryNewgrounds ):
    
    def _GetGalleryPageURL( self, query, page_index ):
        
        artist = query
        
        return 'http://' + artist + '.newgrounds.com/movies/'
        
    
class GalleryPixiv( Gallery ):
    
    def _AddSessionCookies( self, request_headers ):
        
        manager = HydrusGlobals.client_controller.GetManager( 'web_sessions' )
        
        cookies = manager.GetCookies( 'pixiv' )
        
        ClientNetworking.AddCookiesToHeaders( cookies, request_headers )
        
    
    def _ParseGalleryPage( self, html, url_base ):
        
        definitely_no_more_pages = False
        
        urls = []
        
        soup = GetSoup( html )
        
        manga_links = soup.find_all( class_ = 'manga' )
        thumbnail_links = soup.find_all( class_ = 'work' )
        
        manga_urls = { manga_link[ 'href' ] for manga_link in manga_links }
        thumbnail_urls = [ thumbnail_link[ 'href' ] for thumbnail_link in thumbnail_links ]
        
        for thumbnail_url in thumbnail_urls:
            
            if thumbnail_url in manga_urls:
                
                # I think the best way to handle this is to wait until I have cbz support or whatever and sort it out in getfileandtags
                # download each file in turn and write to a cbz on temp_path
                # replace this with the mode=manga url so it is easily noticed at that stage
                # but for now, just skip it
                
                pass
                
            else:
                
                url = urlparse.urljoin( url_base, thumbnail_url ) # http://www.pixiv.net/member_illust.php?mode=medium&illust_id=33500690
                
                urls.append( url )
                
            
        
        return ( urls, definitely_no_more_pages )
        
    
    def _ParseImagePage( self, html, page_url ):
        
        if 'member_illust.php?mode=manga' in html:
            
            manga_url = page_url.replace( 'medium', 'manga' )
            
            raise HydrusExceptions.MimeException( page_url + ' was manga, not a single image, so could not be downloaded.' )
            
        
        if 'member_illust.php?mode=ugoira_view' in html:
            
            raise HydrusExceptions.MimeException( page_url + ' was ugoira, not a single image, so could not be downloaded.' )
            
        
        soup = GetSoup( html )
        
        #
        
        original_image = soup.find( class_ = 'original-image' )
        
        image_url = original_image[ 'data-src' ] # http://i3.pixiv.net/img-original/img/2014/01/25/19/21/56/41171994_p0.jpg
        
        #
        
        tags_parent = soup.find( 'section', class_ = 'work-tags' )
        
        # <a href="/search.php?s_mode=s_tag_full&amp;word=%E3%83%8F%E3%83%B3%E3%83%89%E3%83%A1%E3%82%A4%E3%83%89" class="text">[unicode tag here]</a>
        tags = [ link.string for link in tags_parent.find_all( 'a', class_ = 'text' ) ]
        
        user = soup.find( 'h1', class_ = 'user' )
        
        tags.append( 'creator:' + user.string )
        
        title_parent = soup.find( 'section', class_ = re.compile( 'work-info' ) )
        
        title = title_parent.find( 'h1', class_ = 'title' )
        
        tags.append( 'title:' + title.string )
        
        return ( image_url, tags )
        
    
    def _GetFileURLAndTags( self, page_url, report_hooks = None ):
        
        html = self._FetchData( page_url, report_hooks = report_hooks )
        
        return self._ParseImagePage( html, page_url )
        
    
    def GetFile( self, temp_path, url, report_hooks = None ):
        
        ( image_url, tags ) = self._GetFileURLAndTags( url, report_hooks = report_hooks )
        
        self._FetchData( image_url, referer_url = url, report_hooks = report_hooks, temp_path = temp_path )
        
    
    def GetFileAndTags( self, temp_path, url, report_hooks = None ):
        
        ( image_url, tags ) = self._GetFileURLAndTags( url, report_hooks = report_hooks )
        
        self._FetchData( image_url, referer_url = url, report_hooks = report_hooks, temp_path = temp_path )
        
        return tags
        
    
    def GetTags( self, url, report_hooks = None ):
        
        ( image_url, tags ) = self._GetFileURLAndTags( url, report_hooks = report_hooks )
        
        return tags
        
    
class GalleryPixivArtistID( GalleryPixiv ):
    
    def _GetGalleryPageURL( self, query, page_index ):
        
        artist_id = query
        
        gallery_url = 'http://www.pixiv.net/member_illust.php?type=illust&id=' + str( artist_id )
        
        return gallery_url + '&p=' + str( page_index + 1 )
        
    
class GalleryPixivTag( GalleryPixiv ):
    
    def _GetGalleryPageURL( self, query, page_index ):
        
        tag = query
        
        gallery_url = 'http://www.pixiv.net/search.php?word=' + urllib.quote( HydrusData.ToByteString( tag ), '' ) + '&s_mode=s_tag_full&order=date_d'
        
        return gallery_url + '&p=' + str( page_index + 1 )
        
    
class GalleryTumblr( Gallery ):
    
    def _GetGalleryPageURL( self, query, page_index ):
        
        username = query
        
        return 'http://' + username + '.tumblr.com/api/read/json?start=' + str( page_index * 50 ) + '&num=50'
        
    
    def _ParseGalleryPage( self, data, url_base ):
        
        definitely_no_more_pages = False
        
        processed_raw_json = data.split( 'var tumblr_api_read = ' )[1][:-2] # -1 takes a js ';' off the end
        
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
                            
                        
                    
                
            
        
        return ( urls, definitely_no_more_pages )
        
    
    def GetTags( self, url, report_hooks = None ):
        
        result = GetExtraURLInfo( url )
        
        if result is None:
            
            return []
            
        else:
            
            return result
            
        
    
