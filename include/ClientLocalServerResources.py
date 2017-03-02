import ClientConstants as CC
import ClientFiles
import HydrusConstants as HC
import HydrusData
import HydrusExceptions
import HydrusGlobals
import HydrusServerResources
import os
from twisted.web.static import File as FileResource

local_booru_css = FileResource( os.path.join( HC.STATIC_DIR, 'local_booru_style.css' ), defaultType = 'text/css' )

class HydrusResourceBooru( HydrusServerResources.HydrusResource ):
    
    def _recordDataUsage( self, request ):
        
        path = request.path[1:] # /account -> account
        
        if request.method == 'GET': method = HC.GET
        else: method = HC.POST
        
        num_bytes = request.hydrus_request_data_usage
        
        self._service.RequestMade( num_bytes )
        
    
    def _checkService( self, request ):
        
        HydrusServerResources.HydrusResource._checkService( self, request )
        
        if not self._service.BandwidthOk():
            
            raise HydrusExceptions.BandwidthException( 'This service has run out of bandwidth. Please try again later.' )
            
        
    
class HydrusResourceBooruFile( HydrusResourceBooru ):
    
    def _threadDoGETJob( self, request ):
        
        share_key = request.hydrus_args[ 'share_key' ]
        hash = request.hydrus_args[ 'hash' ]
        
        local_booru_manager = HydrusGlobals.client_controller.GetManager( 'local_booru' )
        
        local_booru_manager.CheckFileAuthorised( share_key, hash )
        
        client_files_manager = HydrusGlobals.client_controller.GetClientFilesManager()
        
        path = client_files_manager.GetFilePath( hash )
        
        response_context = HydrusServerResources.ResponseContext( 200, path = path )
        
        return response_context
        
    
class HydrusResourceBooruGallery( HydrusResourceBooru ):
    
    def _threadDoGETJob( self, request ):
        
        # in future, make this a standard frame with a search key that'll load xml or yaml AJAX stuff
        # with file info included, so the page can sort and whatever
        
        share_key = request.hydrus_args[ 'share_key' ]
        
        local_booru_manager = HydrusGlobals.client_controller.GetManager( 'local_booru' )
        
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
        <div class="timeout">This share ''' + HydrusData.ConvertTimestampToPrettyExpires( timeout ) + '''.</div>'''
        
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
        <div class="footer"><a href="https://hydrusnetwork.github.io/hydrus/">hydrus network</a></div>
    </body>
</html>'''
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = HC.TEXT_HTML, body = body )
        
        return response_context
        
    
class HydrusResourceBooruPage( HydrusResourceBooru ):
    
    def _threadDoGETJob( self, request ):
        
        share_key = request.hydrus_args[ 'share_key' ]
        hash = request.hydrus_args[ 'hash' ]
        
        local_booru_manager = HydrusGlobals.client_controller.GetManager( 'local_booru' )
        
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
        <div class="timeout">This share ''' + HydrusData.ConvertTimestampToPrettyExpires( timeout ) + '''.</div>'''
        
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
        <div class="footer"><a href="https://hydrusnetwork.github.io/hydrus/">hydrus network</a></div>
    </body>
</html>'''
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = HC.TEXT_HTML, body = body )
        
        return response_context
        
    
class HydrusResourceBooruThumbnail( HydrusResourceBooru ):
    
    def _threadDoGETJob( self, request ):
        
        share_key = request.hydrus_args[ 'share_key' ]
        hash = request.hydrus_args[ 'hash' ]
        
        local_booru_manager = HydrusGlobals.client_controller.GetManager( 'local_booru' )
        
        local_booru_manager.CheckFileAuthorised( share_key, hash )
        
        media_result = local_booru_manager.GetMediaResult( share_key, hash )
        
        mime = media_result.GetMime()
        
        response_context_mime = HC.IMAGE_PNG
        
        if mime in HC.MIMES_WITH_THUMBNAILS:
            
            client_files_manager = HydrusGlobals.client_controller.GetClientFilesManager()
            
            path = client_files_manager.GetFullSizeThumbnailPath( hash )
            
            response_context_mime = HC.APPLICATION_UNKNOWN
            
        elif mime in HC.AUDIO: path = os.path.join( HC.STATIC_DIR, 'audio.png' )
        elif mime == HC.APPLICATION_PDF: path = os.path.join( HC.STATIC_DIR, 'pdf.png' )
        else: path = os.path.join( HC.STATIC_DIR, 'hydrus.png' )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = response_context_mime, path = path )
        
        return response_context
        
    
class HydrusResourceLocalFile( HydrusServerResources.HydrusResource ):
    
    def _threadDoGETJob( self, request ):
        
        hash = request.hydrus_args[ 'hash' ]
        
        client_files_manager = HydrusGlobals.client_controller.GetClientFilesManager()
        
        path = client_files_manager.GetFilePath( hash )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = HC.APPLICATION_UNKNOWN, path = path )
        
        return response_context
        
    
class HydrusResourceLocalThumbnail( HydrusServerResources.HydrusResource ):
    
    def _threadDoGETJob( self, request ):
        
        hash = request.hydrus_args[ 'hash' ]
        
        client_files_manager = HydrusGlobals.client_controller.GetClientFilesManager()
        
        path = client_files_manager.GetFullSizeThumbnailPath( hash )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = HC.APPLICATION_UNKNOWN, path = path )
        
        return response_context
        
    
