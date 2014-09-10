import BaseHTTPServer
import ClientConstants as CC
import Cookie
import hashlib
import httplib
import HydrusAudioHandling
import HydrusConstants as HC
import HydrusDocumentHandling
import HydrusExceptions
import HydrusFileHandling
import HydrusFlashHandling
import HydrusNATPunch
import HydrusImageHandling
import os
import random
import ServerConstants as SC
import SocketServer
import threading
import time
import traceback
import urllib
import wx
import yaml
from twisted.internet import reactor, defer
from twisted.internet.threads import deferToThread
from twisted.web.server import Request, Site, NOT_DONE_YET
from twisted.web.resource import Resource
from twisted.web.static import File as FileResource, NoRangeStaticProducer
from twisted.python import log

CLIENT_ROOT_MESSAGE = '''<html>
    <head>
        <title>hydrus client</title>
    </head>
    <body>
        <p>This hydrus client uses software version ''' + HC.u( HC.SOFTWARE_VERSION ) + ''' and network version ''' + HC.u( HC.NETWORK_VERSION ) + '''.</p>
        <p>It only serves requests from 127.0.0.1.</p>
    </body>
</html>'''

ROOT_MESSAGE_BEGIN = '''<html>
    <head>
        <title>hydrus service</title>
    </head>
    <body>
        <p>This hydrus service uses software version ''' + HC.u( HC.SOFTWARE_VERSION ) + ''' and network version ''' + HC.u( HC.NETWORK_VERSION ) + '''.</p>
        <p>'''

ROOT_MESSAGE_END = '''</p>
    </body>
</html>'''

def ParseFileArguments( path ):
    
    HydrusImageHandling.ConvertToPngIfBmp( path )
    
    hash = HydrusFileHandling.GetHashFromPath( path )
    
    try: ( size, mime, width, height, duration, num_frames, num_words ) = HydrusFileHandling.GetFileInfo( path )
    except HydrusExceptions.SizeException: raise HydrusExceptions.ForbiddenException( 'File is of zero length!' )
    except HydrusExceptions.MimeException: raise HydrusExceptions.ForbiddenException( 'Filetype is not permitted!' )
    except Exception as e: raise HydrusExceptions.ForbiddenException( HC.u( e ) )
    
    args = {}
    
    args[ 'path' ] = path
    args[ 'hash' ] = hash
    args[ 'size' ] = size
    args[ 'mime' ] = mime
    
    if width is not None: args[ 'width' ] = width
    if height is not None: args[ 'height' ] = height
    if duration is not None: args[ 'duration' ] = duration
    if num_frames is not None: args[ 'num_frames' ] = num_frames
    if num_words is not None: args[ 'num_words' ] = num_words
    
    if mime in HC.IMAGES:
        
        try: thumbnail = HydrusFileHandling.GenerateThumbnail( path )
        except: raise HydrusExceptions.ForbiddenException( 'Could not generate thumbnail from that file.' )
        
        args[ 'thumbnail' ] = thumbnail
        
    
    return args
    
hydrus_favicon = FileResource( HC.STATIC_DIR + os.path.sep + 'hydrus.ico', defaultType = 'image/x-icon' )
local_booru_css = FileResource( HC.STATIC_DIR + os.path.sep + 'local_booru_style.css', defaultType = 'text/css' )

class HydrusDomain( object ):
    
    def __init__( self, local_only ):
        
        self._local_only = local_only
        
    
    def CheckValid( self, client_ip ):
        
        if self._local_only and client_ip != '127.0.0.1': raise HydrusExceptions.ForbiddenException( 'Only local access allowed!' )
        
    
class HydrusResourceWelcome( Resource ):
    
    def __init__( self, service_key, service_type, message ):
        
        Resource.__init__( self )
        
        if service_key == HC.LOCAL_FILE_SERVICE_KEY: body = CLIENT_ROOT_MESSAGE
        else: body = ROOT_MESSAGE_BEGIN + message + ROOT_MESSAGE_END
        
        self._body = body.encode( 'utf-8' )
        
        self._server_version_string = HC.service_string_lookup[ service_type ] + '/' + str( HC.NETWORK_VERSION )
        

    def render_GET( self, request ):
        
        request.setHeader( 'Server', self._server_version_string )
        
        return self._body
        
    
class HydrusResourceCommand( Resource ):
    
    def __init__( self, service_key, service_type, domain ):
        
        Resource.__init__( self )
        
        self._service_key = service_key
        self._service_type = service_type
        self._domain = domain
        
        self._server_version_string = HC.service_string_lookup[ service_type ] + '/' + str( HC.NETWORK_VERSION )
        
    
    def _callbackCheckRestrictions( self, request ):
        
        self._checkUserAgent( request )
        
        self._domain.CheckValid( request.getClientIP() )
        
        return request
        
    
    def _callbackParseGETArgs( self, request ):
        
        hydrus_args = {}
        
        for name in request.args:
            
            values = request.args[ name ]
            
            value = values[0]
            
            if name in ( 'begin', 'expiry', 'lifetime', 'num', 'subject_account_id', 'service_type', 'service_port', 'since', 'timespan' ):
                
                try: hydrus_args[ name ] = int( value )
                except: raise HydrusExceptions.ForbiddenException( 'I was expecting to parse \'' + name + '\' as an integer, but it failed.' )
                
            elif name in ( 'access_key', 'title', 'subject_access_key', 'contact_key', 'hash', 'subject_hash', 'subject_tag', 'message_key', 'share_key' ):
                
                try: hydrus_args[ name ] = value.decode( 'hex' )
                except: raise HydrusExceptions.ForbiddenException( 'I was expecting to parse \'' + name + '\' as a hex-encoded string, but it failed.' )
                
            
        
        if 'subject_account_id' in hydrus_args: hydrus_args[ 'subject_identifier' ] = HC.AccountIdentifier( account_id = hydrus_args[ 'subject_account_id' ] )
        elif 'subject_access_key' in hydrus_args: hydrus_args[ 'subject_identifier' ] = HC.AccountIdentifier( access_key = hydrus_args[ 'subject_access_key' ] )
        elif 'subject_hash' in hydrus_args:
            
            if 'subject_tag' in hydrus_args: hydrus_args[ 'subject_identifier' ] = HC.AccountIdentifier( tag = hydrus_args[ 'subject_tag' ], hash = hydrus_args[ 'subject_hash' ] )
            else: hydrus_args[ 'subject_identifier' ] = HC.AccountIdentifier( hash = hydrus_args[ 'subject_hash' ] )
            
        
        request.hydrus_args = hydrus_args
        
        return request
        
    
    def _callbackParsePOSTArgs( self, request ):
        
        request.content.seek( 0 )
        
        if not request.requestHeaders.hasHeader( 'Content-Type' ): raise HydrusExceptions.ForbiddenException( 'No Content-Type header found!' )
        
        content_types = request.requestHeaders.getRawHeaders( 'Content-Type' )
        
        content_type = content_types[0]
        
        try: mime = HC.mime_enum_lookup[ content_type ]
        except: raise HydrusExceptions.ForbiddenException( 'Did not recognise Content-Type header!' )
        
        if mime == HC.APPLICATION_YAML:
            
            yaml_string = request.content.read()
            
            request.hydrus_request_data_usage += len( yaml_string )
            
            hydrus_args = yaml.safe_load( yaml_string )
            
        else:
            
            temp_path = HC.GetTempPath()
            
            with open( temp_path, 'wb' ) as f:
                
                block_size = 65536
                
                while True:
                    
                    block = request.content.read( block_size )
                    
                    if block == '': break
                    
                    f.write( block )
                    
                    request.hydrus_request_data_usage += len( block )
                    
                
            
            hydrus_args = ParseFileArguments( temp_path )
            
        
        request.hydrus_args = hydrus_args
        
        return request
        
    
    def _callbackRenderResponseContext( self, request ):
        
        response_context = request.hydrus_response_context
        
        status_code = response_context.GetStatusCode()
        
        request.setResponseCode( status_code )
        
        for ( k, v, kwargs ) in response_context.GetCookies(): request.addCookie( k, v, **kwargs )
        
        do_finish = True
        
        if response_context.HasBody():
            
            ( mime, body ) = response_context.GetMimeBody()
            
            content_type = HC.mime_string_lookup[ mime ]
            
            content_length = len( body )
            
            request.setHeader( 'Content-Type', content_type )
            request.setHeader( 'Content-Length', str( content_length ) )
            
            if type( body ) == unicode: body = body.encode( 'utf-8' )
            
            request.write( body )
            
        elif response_context.HasPath():
            
            path = response_context.GetPath()
            
            info = os.lstat( path )
            
            size = info[6]
            
            if response_context.IsYAML():
                
                mime = HC.APPLICATION_YAML
                
                content_type = HC.mime_string_lookup[ mime ]
                
            else:
                
                mime = HydrusFileHandling.GetMime( path )
                
                ( base, filename ) = os.path.split( path )
                
                content_type = HC.mime_string_lookup[ mime ] + '; ' + filename
                
            
            content_length = size
            
            request.setHeader( 'Content-Type', content_type )
            request.setHeader( 'Content-Length', str( content_length ) )
            
            request.setHeader( 'Expires', time.strftime( '%a, %d %b %Y %H:%M:%S GMT', time.gmtime( time.time() + 86400 * 365 ) ) )
            request.setHeader( 'Cache-Control', str( 86400 * 365  ) )
            
            fileObject = open( path, 'rb' )
            
            producer = NoRangeStaticProducer( request, fileObject )
            
            producer.start()
            
            do_finish = False
            
        else:
            
            content_length = 0
            
            request.setHeader( 'Content-Length', str( content_length ) )
            
        
        request.hydrus_request_data_usage += content_length
        
        self._recordDataUsage( request )
        
        if do_finish: request.finish()
        
    
    def _callbackDoGETJob( self, request ):
        
        def wrap_thread_result( response_context ):
            
            request.hydrus_response_context = response_context
            
            return request
            
        
        d = deferToThread( self._threadDoGETJob, request )
        
        d.addCallback( wrap_thread_result )
        
        return d
        
    
    def _callbackDoPOSTJob( self, request ):
        
        def wrap_thread_result( response_context ):
            
            request.hydrus_response_context = response_context
            
            return request
            
        
        d = deferToThread( self._threadDoPOSTJob, request )
        
        d.addCallback( wrap_thread_result )
        
        return d
        
    
    def _checkUserAgent( self, request ):
        
        request.is_hydrus_user_agent = False
        
        if request.requestHeaders.hasHeader( 'User-Agent' ):
            
            user_agent_texts = request.requestHeaders.getRawHeaders( 'User-Agent' )
            
            user_agent_text = user_agent_texts[0]
            
            try:
                
                user_agents = user_agent_text.split( ' ' )
                
            except: return # crazy user agent string, so just assume not a hydrus client
            
            for user_agent in user_agents:
                
                if '/' in user_agent:
                    
                    ( client, network_version ) = user_agent.split( '/', 1 )
                    
                    if client == 'hydrus':
                        
                        request.is_hydrus_user_agent = True
                        
                        network_version = int( network_version )
                        
                        if network_version == HC.NETWORK_VERSION: return
                        else:
                            
                            if network_version < HC.NETWORK_VERSION: message = 'Your client is out of date; please download the latest release.'
                            else: message = 'This server is out of date; please ask its admin to update to the latest release.'
                            
                            raise HydrusExceptions.NetworkVersionException( 'Network version mismatch! This server\'s network version is ' + HC.u( HC.NETWORK_VERSION ) + ', whereas your client\'s is ' + HC.u( network_version ) + '! ' + message )
                            
                        
                    
                
            
        
    
    def _errbackHandleEmergencyError( self, failure, request ):
        
        print( failure.getTraceback() )
        
        try: request.write( failure.getTraceback() )
        except: pass
        
        try: request.finish()
        except: pass
        
    
    def _errbackHandleProcessingError( self, failure, request ):
        
        do_yaml = True
        
        try:
            
            # the error may have occured before user agent was set up!
            if not request.is_hydrus_user_agent: do_yaml = False
            
        except: pass
        
        if do_yaml:
            
            default_mime = HC.APPLICATION_YAML
            default_encoding = lambda x: yaml.safe_dump( HC.u( x ) )
            
        else:
            
            default_mime = HC.TEXT_HTML
            default_encoding = lambda x: HC.u( x )
            
        
        if failure.type == KeyError: response_context = HC.ResponseContext( 403, mime = default_mime, body = default_encoding( 'It appears one or more parameters required for that request were missing:' + os.linesep + failure.getTraceback() ) )
        elif failure.type == HydrusExceptions.PermissionException: response_context = HC.ResponseContext( 401, mime = default_mime, body = default_encoding( failure.value ) )
        elif failure.type == HydrusExceptions.ForbiddenException: response_context = HC.ResponseContext( 403, mime = default_mime, body = default_encoding( failure.value ) )
        elif failure.type == HydrusExceptions.NotFoundException: response_context = HC.ResponseContext( 404, mime = default_mime, body = default_encoding( failure.value ) )
        elif failure.type == HydrusExceptions.NetworkVersionException: response_context = HC.ResponseContext( 426, mime = default_mime, body = default_encoding( failure.value ) )
        elif failure.type == HydrusExceptions.SessionException: response_context = HC.ResponseContext( 403, mime = default_mime, body = default_encoding( failure.value ) )
        else:
            
            print( failure.getTraceback() )
            
            response_context = HC.ResponseContext( 500, mime = default_mime, body = default_encoding( 'The repository encountered an error it could not handle! Here is a dump of what happened, which will also be written to your client.log file. If it persists, please forward it to hydrus.admin@gmail.com:' + os.linesep + os.linesep + failure.getTraceback() ) )
            
        
        request.hydrus_response_context = response_context
        
        return request
        
    
    def _parseAccessKey( self, request ):
        
        if not request.requestHeaders.hasHeader( 'Hydrus-Key' ): raise HydrusExceptions.PermissionException( 'No hydrus key header found!' )
        
        hex_keys = request.requestHeaders.getRawHeaders( 'Hydrus-Key' )
        
        hex_key = hex_keys[0]
        
        try: access_key = hex_key.decode( 'hex' )
        except: raise HydrusExceptions.ForbiddenException( 'Could not parse the hydrus key!' )
        
        return access_key
        
    
    def _recordDataUsage( self, request ): pass
    
    def _threadDoGETJob( self, request ): raise HydrusExceptions.NotFoundException( 'This service does not support that request!' )
    
    def _threadDoPOSTJob( self, request ): raise HydrusExceptions.NotFoundException( 'This service does not support that request!' )
    
    def render_GET( self, request ):
        
        request.setHeader( 'Server', self._server_version_string )
        
        d = defer.Deferred()
        
        d.addCallback( self._callbackCheckRestrictions )
        
        d.addCallback( self._callbackParseGETArgs )
        
        d.addCallback( self._callbackDoGETJob )
        
        d.addErrback( self._errbackHandleProcessingError, request )
        
        d.addCallback( self._callbackRenderResponseContext )
        
        d.addErrback( self._errbackHandleEmergencyError, request )
        
        reactor.callLater( 0, d.callback, request )
        
        return NOT_DONE_YET
        
    
    def render_POST( self, request ):
        
        request.setHeader( 'Server', self._server_version_string )
        
        d = defer.Deferred()
        
        d.addCallback( self._callbackCheckRestrictions )
        
        d.addCallback( self._callbackParsePOSTArgs )
        
        d.addCallback( self._callbackDoPOSTJob )
        
        d.addErrback( self._errbackHandleProcessingError, request )
        
        d.addCallback( self._callbackRenderResponseContext )
        
        d.addErrback( self._errbackHandleEmergencyError, request )
        
        reactor.callLater( 0, d.callback, request )
        
        return NOT_DONE_YET
        
    
class HydrusResourceCommandAccessKey( HydrusResourceCommand ):
    
    def _threadDoGETJob( self, request ):
        
        registration_key = self._parseAccessKey( request )
        
        access_key = HC.app.Read( 'access_key', registration_key )
        
        body = yaml.safe_dump( { 'access_key' : access_key } )
        
        response_context = HC.ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceCommandAccessKeyVerification( HydrusResourceCommand ):
    
    def _threadDoGETJob( self, request ):
        
        access_key = self._parseAccessKey( request )
        
        verified = HC.app.Read( 'verify_access_key', self._service_key, access_key )
        
        body = yaml.safe_dump( { 'verified' : verified } )
        
        response_context = HC.ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceCommandBooru( HydrusResourceCommand ):
    
    RECORD_GET_DATA_USAGE = False
    RECORD_POST_DATA_USAGE = False
    
    def _recordDataUsage( self, request ):
        
        p1 = request.method == 'GET' and self.RECORD_GET_DATA_USAGE
        p2 = request.method == 'POST' and self.RECORD_POST_DATA_USAGE
        
        if p1 or p2:
            
            num_bytes = request.hydrus_request_data_usage
            
            HC.pubsub.pub( 'service_updates_delayed', { HC.LOCAL_BOORU_SERVICE_KEY : [ HC.ServiceUpdate( HC.SERVICE_UPDATE_REQUEST_MADE, num_bytes ) ] } )
            
        
    
    def _callbackCheckRestrictions( self, request ):
        
        self._checkUserAgent( request )
        
        self._domain.CheckValid( request.getClientIP() )
        
        return request
        
    
class HydrusResourceCommandBooruGallery( HydrusResourceCommandBooru ):
    
    RECORD_GET_DATA_USAGE = True
    
    def _threadDoGETJob( self, request ):
        
        # in future, make this a standard frame with a search key that'll load xml or yaml AJAX stuff
        # with file info included, so the page can sort and whatever
        
        share_key = request.hydrus_args[ 'share_key' ]
        
        local_booru_manager = HC.app.GetManager( 'local_booru' )
        
        local_booru_manager.CheckShareAuthorised( share_key )
        
        ( name, text, timeout, media_results ) = local_booru_manager.GetGalleryInfo( share_key )
        
        body = '''<html>
    <head>'''
        
        if name == '': body += '''
        <title>hydrus network local booru share</title>'''
        else: body += '''
        <title>''' + name + '''</title>'''
        
        body += '''
        
        <link href="hydrus.ico" rel="shortcut icon" />
        <link href="style.css" rel="stylesheet" type="text/css" />'''
        
        ( thumbnail_width, thumbnail_height ) = HC.options[ 'thumbnail_dimensions' ]
        
        body += '''
        <style>
            .thumbnail_container { width: ''' + str( thumbnail_width ) + '''px; height: ''' + str( thumbnail_height ) + '''px; }
        </style>'''
        
        body += '''
    </head>
    <body>'''
        
        body += '''
        <div class="timeout">This share ''' + HC.ConvertTimestampToPrettyExpiry( timeout ) + '''.</div>'''
        
        if name != '': body += '''
        <h3>''' + name + '''</h3>'''
        
        if text != '':
            
            newline = '''</p>
        <p>'''
            
            body += '''
        <p>''' + text.replace( os.linesep, newline ).replace( '\n', newline ) + '''</p>'''
        
        body+= '''
        <div class="media">'''
        
        for media_result in media_results:
            
            hash = media_result.GetHash()
            mime = media_result.GetMime()
            
            # if mime in flash or pdf or whatever, get other thumbnail
            
            body += '''
            <span class="thumbnail">
                <span class="thumbnail_container">
                    <a href="page?share_key=''' + share_key.encode( 'hex' ) + '''&hash=''' + hash.encode( 'hex' ) + '''">
                        <img src="thumbnail?share_key=''' + share_key.encode( 'hex' ) + '''&hash=''' + hash.encode( 'hex' ) + '''" />
                    </a>
                </span>
            </span>'''
            
        
        body += '''
        </div>
        <div class="footer"><a href="http://hydrusnetwork.github.io/hydrus/">hydrus network</a></div>
    </body>
</html>'''
        
        response_context = HC.ResponseContext( 200, mime = HC.TEXT_HTML, body = body )
        
        return response_context
        
    
class HydrusResourceCommandBooruFile( HydrusResourceCommandBooru ):
    
    RECORD_GET_DATA_USAGE = True
    
    def _threadDoGETJob( self, request ):
        
        share_key = request.hydrus_args[ 'share_key' ]
        hash = request.hydrus_args[ 'hash' ]
        
        local_booru_manager = HC.app.GetManager( 'local_booru' )
        
        local_booru_manager.CheckFileAuthorised( share_key, hash )
        
        path = CC.GetFilePath( hash )
        
        response_context = HC.ResponseContext( 200, path = path )
        
        return response_context
        
    
class HydrusResourceCommandBooruPage( HydrusResourceCommandBooru ):
    
    RECORD_GET_DATA_USAGE = True
    
    def _threadDoGETJob( self, request ):
        
        share_key = request.hydrus_args[ 'share_key' ]
        hash = request.hydrus_args[ 'hash' ]
        
        local_booru_manager = HC.app.GetManager( 'local_booru' )
        
        local_booru_manager.CheckFileAuthorised( share_key, hash )
        
        ( name, text, timeout, media_result ) = local_booru_manager.GetPageInfo( share_key, hash )
        
        body = '''<html>
    <head>'''
        
        if name == '': body += '''
        <title>hydrus network local booru share</title>'''
        else: body += '''
        <title>''' + name + '''</title>'''
        
        body += '''
        
        <link href="hydrus.ico" rel="shortcut icon" />
        <link href="style.css" rel="stylesheet" type="text/css" />'''
        
        body += '''
    </head>
    <body>'''
        
        body += '''
        <div class="timeout">This share ''' + HC.ConvertTimestampToPrettyExpiry( timeout ) + '''.</div>'''
        
        if name != '': body += '''
        <h3>''' + name + '''</h3>'''
        
        if text != '':
            
            newline = '''</p>
        <p>'''
            
            body += '''
        <p>''' + text.replace( os.linesep, newline ).replace( '\n', newline ) + '''</p>'''
        
        body+= '''
        <div class="media">'''
        
        mime = media_result.GetMime()
        
        if mime in HC.IMAGES:
            
            ( width, height ) = media_result.GetResolution()
            
            body += '''
            <img width="''' + str( width ) + '''" height="''' + str( height ) + '''" src="file?share_key=''' + share_key.encode( 'hex' ) + '''&hash=''' + hash.encode( 'hex' ) + '''" />'''
            
        elif mime in HC.VIDEO:
            
            ( width, height ) = media_result.GetResolution()
            
            body += '''
            <video width="''' + str( width ) + '''" height="''' + str( height ) + '''" controls="" loop="" autoplay="" src="file?share_key=''' + share_key.encode( 'hex' ) + '''&hash=''' + hash.encode( 'hex' ) + '''" />
            <p><a href="file?share_key=''' + share_key.encode( 'hex' ) + '''&hash=''' + hash.encode( 'hex' ) + '''">link to ''' + HC.mime_string_lookup[ mime ] + ''' file</a></p>'''
            
        elif mime == HC.APPLICATION_FLASH:
            
            ( width, height ) = media_result.GetResolution()
            
            body += '''
            <embed width="''' + str( width ) + '''" height="''' + str( height ) + '''" src="file?share_key=''' + share_key.encode( 'hex' ) + '''&hash=''' + hash.encode( 'hex' ) + '''" />
            <p><a href="file?share_key=''' + share_key.encode( 'hex' ) + '''&hash=''' + hash.encode( 'hex' ) + '''">link to ''' + HC.mime_string_lookup[ mime ] + ''' file</a></p>'''
            
        else:
            
            body += '''
            <p><a href="file?share_key=''' + share_key.encode( 'hex' ) + '''&hash=''' + hash.encode( 'hex' ) + '''">link to ''' + HC.mime_string_lookup[ mime ] + ''' file</a></p>'''
            
        
        body += '''
        </div>
        <div class="footer"><a href="http://hydrusnetwork.github.io/hydrus/">hydrus network</a></div>
    </body>
</html>'''
        
        response_context = HC.ResponseContext( 200, mime = HC.TEXT_HTML, body = body )
        
        return response_context
        
    
class HydrusResourceCommandBooruThumbnail( HydrusResourceCommandBooru ):
    
    RECORD_GET_DATA_USAGE = True
    
    def _threadDoGETJob( self, request ):
        
        share_key = request.hydrus_args[ 'share_key' ]
        hash = request.hydrus_args[ 'hash' ]
        
        local_booru_manager = HC.app.GetManager( 'local_booru' )
        
        local_booru_manager.CheckFileAuthorised( share_key, hash )
        
        media_result = local_booru_manager.GetMediaResult( share_key, hash )
        
        mime = media_result.GetMime()
        
        if mime in HC.MIMES_WITH_THUMBNAILS: path = CC.GetThumbnailPath( hash, full_size = False )
        elif mime in HC.AUDIO: path = HC.STATIC_DIR + os.path.sep + 'audio_resized.png'
        elif mime in HC.VIDEO: path = HC.STATIC_DIR + os.path.sep + 'video_resized.png'
        elif mime == HC.APPLICATION_FLASH: path = HC.STATIC_DIR + os.path.sep + 'flash_resized.png'
        elif mime == HC.APPLICATION_PDF: path = HC.STATIC_DIR + os.path.sep + 'pdf_resized.png'
        else: path = HC.STATIC_DIR + os.path.sep + 'hydrus_resized.png'
        
        response_context = HC.ResponseContext( 200, path = path )
        
        return response_context
        
    
class HydrusResourceCommandInit( HydrusResourceCommand ):
    
    def _threadDoGETJob( self, request ):
        
        access_key = HC.app.Read( 'init' )
        
        body = yaml.safe_dump( { 'access_key' : access_key } )
        
        response_context = HC.ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceCommandLocalFile( HydrusResourceCommand ):
    
    def _threadDoGETJob( self, request ):
        
        hash = request.hydrus_args[ 'hash' ]
        
        path = CC.GetFilePath( hash )
        
        response_context = HC.ResponseContext( 200, path = path )
        
        return response_context
        
    
class HydrusResourceCommandLocalThumbnail( HydrusResourceCommand ):
    
    def _threadDoGETJob( self, request ):
        
        hash = request.hydrus_args[ 'hash' ]
        
        path = CC.GetThumbnailPath( hash )
        
        response_context = HC.ResponseContext( 200, path = path )
        
        return response_context
        
    
class HydrusResourceCommandSessionKey( HydrusResourceCommand ):
    
    def _threadDoGETJob( self, request ):
        
        access_key = self._parseAccessKey( request )
        
        session_manager = HC.app.GetManager( 'restricted_services_sessions' )
        
        ( session_key, expiry ) = session_manager.AddSession( self._service_key, access_key )
        
        now = HC.GetNow()
        
        max_age = now - expiry
        
        cookies = [ ( 'session_key', session_key.encode( 'hex' ), { 'max_age' : max_age, 'path' : '/' } ) ]
        
        response_context = HC.ResponseContext( 200, cookies = cookies )
        
        return response_context
        
    
class HydrusResourceCommandRestricted( HydrusResourceCommand ):
    
    GET_PERMISSION = HC.GENERAL_ADMIN
    POST_PERMISSION = HC.GENERAL_ADMIN
    RECORD_GET_DATA_USAGE = False
    RECORD_POST_DATA_USAGE = False
    
    def _callbackCheckRestrictions( self, request ):
        
        self._checkUserAgent( request )
        
        self._domain.CheckValid( request.getClientIP() )
        
        self._checkSession( request )
        
        self._checkPermission( request )
        
        return request
        
    
    def _checkPermission( self, request ):
        
        account = request.hydrus_account
        
        method = request.method
        
        if method == 'GET': permission = self.GET_PERMISSION
        elif method == 'POST': permission = self.POST_PERMISSION
        
        if permission is not None: account.CheckPermission( permission )
        
        return request
        
    
    def _checkSession( self, request ):
        
        if not request.requestHeaders.hasHeader( 'Cookie' ): raise HydrusExceptions.PermissionException( 'No cookies found!' )
        
        cookie_texts = request.requestHeaders.getRawHeaders( 'Cookie' )
        
        cookie_text = cookie_texts[0]
        
        try:
            
            cookies = Cookie.SimpleCookie( cookie_text )
            
            if 'session_key' not in cookies: session_key = None
            else: session_key = cookies[ 'session_key' ].value.decode( 'hex' )
            
        except: raise Exception( 'Problem parsing cookies!' )
        
        session_manager = HC.app.GetManager( 'restricted_services_sessions' )
        
        account = session_manager.GetAccount( self._service_key, session_key )
        
        request.hydrus_account = account
        
        return request
        
    
    def _recordDataUsage( self, request ):
        
        p1 = request.method == 'GET' and self.RECORD_GET_DATA_USAGE
        p2 = request.method == 'POST' and self.RECORD_POST_DATA_USAGE
        
        if p1 or p2:
            
            account = request.hydrus_account
            
            if account is not None:
                
                num_bytes = request.hydrus_request_data_usage
                
                account.RequestMade( num_bytes )
                
                HC.pubsub.pub( 'request_made', ( self._service_key, account, num_bytes ) )
                
            
        
    
class HydrusResourceCommandRestrictedAccount( HydrusResourceCommandRestricted ):
    
    GET_PERMISSION = None
    POST_PERMISSION = HC.MANAGE_USERS
    
    def _threadDoGETJob( self, request ):
        
        account = request.hydrus_account
        
        body = yaml.safe_dump( { 'account' : account } )
        
        response_context = HC.ResponseContext( 200, body = body )
        
        return response_context
        
    
    def _threadDoPOSTJob( self, request ):
        
        admin_account = request.hydrus_account
        
        action = request.hydrus_args[ 'action' ]
        
        subject_identifiers = request.hydrus_args[ 'subject_identifiers' ]
        
        kwargs = request.hydrus_args # for things like expiry, title, and so on
        
        HC.app.Write( 'account', self._service_key, admin_account, action, subject_identifiers, kwargs )
        
        session_manager = HC.app.GetManager( 'restricted_services_sessions' )
        
        session_manager.RefreshAccounts( self._service_key, subject_identifiers )
        
        response_context = HC.ResponseContext( 200 )
        
        return response_context
        
    
class HydrusResourceCommandRestrictedAccountInfo( HydrusResourceCommandRestricted ):
    
    GET_PERMISSION = HC.GENERAL_ADMIN
    
    def _threadDoGETJob( self, request ):
        
        subject_identifier = request.hydrus_args[ 'subject_identifier' ]
        
        account_info = HC.app.Read( 'account_info', self._service_key, subject_identifier )
        
        body = yaml.safe_dump( { 'account_info' : account_info } )
        
        response_context = HC.ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceCommandRestrictedAccountTypes( HydrusResourceCommandRestricted ):
    
    GET_PERMISSION = HC.GENERAL_ADMIN
    POST_PERMISSION = HC.GENERAL_ADMIN
    
    def _threadDoGETJob( self, request ):
        
        account_types = HC.app.Read( 'account_types', self._service_key )
        
        body = yaml.safe_dump( { 'account_types' : account_types } )
        
        response_context = HC.ResponseContext( 200, body = body )
        
        return response_context
        
    
    def _threadDoPOSTJob( self, request ):
        
        edit_log = request.hydrus_args[ 'edit_log' ]
        
        HC.app.Write( 'account_types', self._service_key, edit_log )
        
        response_context = HC.ResponseContext( 200 )
        
        return response_context
        
    
class HydrusResourceCommandRestrictedBackup( HydrusResourceCommandRestricted ):
    
    POST_PERMISSION = HC.GENERAL_ADMIN
    
    def _threadDoPOSTJob( self, request ):
        
        #threading.Thread( target = HC.app.Write, args = ( 'backup', ), name = 'Backup Thread' ).start()
        
        HC.app.Write( 'backup' )
        
        response_context = HC.ResponseContext( 200 )
        
        return response_context
        
    
class HydrusResourceCommandRestrictedIP( HydrusResourceCommandRestricted ):
    
    GET_PERMISSION = HC.GENERAL_ADMIN
    
    def _threadDoGETJob( self, request ):
        
        hash = request.hydrus_args[ 'hash' ]
        
        ( ip, timestamp ) = HC.app.Read( 'ip', self._service_key, hash )
        
        body = yaml.safe_dump( { 'ip' : ip, 'timestamp' : timestamp } )
        
        response_context = HC.ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceCommandRestrictedNews( HydrusResourceCommandRestricted ):
    
    POST_PERMISSION = HC.GENERAL_ADMIN
    
    def _threadDoPOSTJob( self, request ):
        
        news = request.hydrus_args[ 'news' ]
        
        HC.app.Write( 'news', self._service_key, news )
        
        response_context = HC.ResponseContext( 200 )
        
        return response_context
        
    
class HydrusResourceCommandRestrictedNumPetitions( HydrusResourceCommandRestricted ):
    
    GET_PERMISSION = HC.RESOLVE_PETITIONS
    
    def _threadDoGETJob( self, request ):
        
        num_petitions = HC.app.Read( 'num_petitions', self._service_key )
        
        body = yaml.safe_dump( { 'num_petitions' : num_petitions } )
        
        response_context = HC.ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceCommandRestrictedPetition( HydrusResourceCommandRestricted ):
    
    GET_PERMISSION = HC.RESOLVE_PETITIONS
    
    def _threadDoGETJob( self, request ):
        
        petition = HC.app.Read( 'petition', self._service_key )
        
        body = yaml.safe_dump( { 'petition' : petition } )
        
        response_context = HC.ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceCommandRestrictedRegistrationKeys( HydrusResourceCommandRestricted ):
    
    GET_PERMISSION = HC.GENERAL_ADMIN
    
    def _threadDoGETJob( self, request ):
        
        num = request.hydrus_args[ 'num' ]
        title = request.hydrus_args[ 'title' ]
        
        if 'lifetime' in request.hydrus_args: lifetime = request.hydrus_args[ 'lifetime' ]
        else: lifetime = None
        
        registration_keys = HC.app.Read( 'registration_keys', self._service_key, num, title, lifetime )
        
        body = yaml.safe_dump( { 'registration_keys' : registration_keys } )
        
        response_context = HC.ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceCommandRestrictedRepositoryFile( HydrusResourceCommandRestricted ):
    
    GET_PERMISSION = HC.GET_DATA
    POST_PERMISSION = HC.POST_DATA
    RECORD_GET_DATA_USAGE = True
    RECORD_POST_DATA_USAGE = True
    
    def _threadDoGETJob( self, request ):
        
        hash = request.hydrus_args[ 'hash' ]
        
        # don't I need to check that we aren't stealing the file from another service?
        
        path = SC.GetPath( 'file', hash )
        
        response_context = HC.ResponseContext( 200, path = path )
        
        return response_context
        
    
    def _threadDoPOSTJob( self, request ):
        
        account = request.hydrus_account
        
        file_dict = request.hydrus_args
        
        file_dict[ 'ip' ] = request.getClientIP()
        
        HC.app.Write( 'file', self._service_key, account, file_dict )
        
        response_context = HC.ResponseContext( 200 )
        
        return response_context
        
    
class HydrusResourceCommandRestrictedRepositoryThumbnail( HydrusResourceCommandRestricted ):
    
    GET_PERMISSION = HC.GET_DATA
    RECORD_GET_DATA_USAGE = True
    
    def _threadDoGETJob( self, request ):
        
        hash = request.hydrus_args[ 'hash' ]
        
        # don't I need to check that we aren't stealing the file from another service?
        
        path = SC.GetPath( 'thumbnail', hash )
        
        response_context = HC.ResponseContext( 200, path = path )
        
        return response_context
        
    
class HydrusResourceCommandRestrictedServices( HydrusResourceCommandRestricted ):
    
    GET_PERMISSION = HC.GENERAL_ADMIN
    POST_PERMISSION = HC.GENERAL_ADMIN
    
    def _threadDoGETJob( self, request ):
        
        services_info = HC.app.Read( 'services' )
        
        body = yaml.safe_dump( { 'services_info' : services_info } )
        
        response_context = HC.ResponseContext( 200, body = body )
        
        return response_context
        
    
    def _threadDoPOSTJob( self, request ):
        
        account = request.hydrus_account
        
        edit_log = request.hydrus_args[ 'edit_log' ]
        
        service_keys_to_access_keys = HC.app.Write( 'services', account, edit_log )
        
        body = yaml.safe_dump( { 'service_keys_to_access_keys' : service_keys_to_access_keys } )
        
        response_context = HC.ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceCommandRestrictedStats( HydrusResourceCommandRestricted ):
    
    GET_PERMISSION = HC.GENERAL_ADMIN
    
    def _threadDoGETJob( self, request ):
        
        stats = HC.app.Read( 'stats', self._service_key )
        
        body = yaml.safe_dump( { 'stats' : stats } )
        
        response_context = HC.ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceCommandRestrictedUpdate( HydrusResourceCommandRestricted ):
    
    GET_PERMISSION = HC.GET_DATA
    POST_PERMISSION = HC.POST_DATA
    RECORD_GET_DATA_USAGE = True
    RECORD_POST_DATA_USAGE = True
    
    def _threadDoGETJob( self, request ):
        
        begin = request.hydrus_args[ 'begin' ]
        
        path = SC.GetUpdatePath( self._service_key, begin )
        
        response_context = HC.ResponseContext( 200, path = path, is_yaml = True )
        
        return response_context
        
    
    def _threadDoPOSTJob( self, request ):
        
        account = request.hydrus_account
        
        update = request.hydrus_args[ 'update' ]
        
        HC.app.Write( 'update', self._service_key, account, update )
        
        response_context = HC.ResponseContext( 200 )
        
        return response_context
        
    