import os
import typing

from qtpy import QtCore as QC
from qtpy import QtGui as QG
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusPaths
from hydrus.core import HydrusTemp
from hydrus.core import HydrusText
from hydrus.core import HydrusTime

from hydrus.client import ClientGlobals as CG
from hydrus.client.exporting import ClientExportingFiles
from hydrus.client.gui import ClientGUIFunctions

# we do this because some programs like discord will disallow exports with additional custom mimetypes (like 'application/hydrus-files')
# as this is only ever an internal transfer, and as the python mimedata object is preserved through the dnd, we can just tack this info on with a subclass and python variables
class QMimeDataHydrusFiles( QC.QMimeData ):
    
    def __init__( self ):
        
        super().__init__()
        
        self._hydrus_files = None
        
    
    def hydrusFiles( self ):
        
        return self._hydrus_files
        
    
    def setHydrusFiles( self, page_key, hashes ):
        
        self._hydrus_files = ( page_key, hashes )
        
    

DND_TEMP_DIRS = []

def DoFileExportDragDrop( drag_object: QG.QDrag, page_key, media, alt_down ):
    
    data_object = QMimeDataHydrusFiles()
    
    #
    
    new_options = CG.client_controller.new_options
    
    #
    
    client_files_manager = CG.client_controller.client_files_manager
    
    original_paths = []
    media_and_original_paths = []
    
    total_size = 0
    
    for m in media:
        
        hash = m.GetHash()
        mime = m.GetMime()
        
        total_size += m.GetSize()
        
        original_path = client_files_manager.GetFilePath( hash, mime, check_file_exists = False )
        
        original_paths.append( original_path )
        media_and_original_paths.append( ( m, original_path ) )
        
    
    #
    
    discord_dnd_fix_possible = new_options.GetBoolean( 'discord_dnd_fix' ) and len( original_paths ) <= 50 and total_size < 200 * 1048576
    
    if discord_dnd_fix_possible:
        
        global DND_TEMP_DIRS
        
        TEMP_DIR_TIMEOUT = 3600 * 6
        
        new_list = []
        
        for ( creation_time, path ) in DND_TEMP_DIRS:
            
            if HydrusTime.TimeHasPassed( creation_time + TEMP_DIR_TIMEOUT ):
                
                HydrusPaths.DeletePath( path )
                
            else:
                
                new_list.append( ( creation_time, path ) )
                
            
        
        DND_TEMP_DIRS = new_list
        
        this_dnd_temp_dir = HydrusTemp.GetSubTempDir( prefix = 'DnD' )
        
        if this_dnd_temp_dir is None or not os.path.exists( this_dnd_temp_dir ):
            
            raise Exception( f'Could not create a temporary directory ("{this_dnd_temp_dir}") to handle the drag and drop!' )
            
        
        DND_TEMP_DIRS.append( ( HydrusTime.GetNow(), this_dnd_temp_dir ) )
        
        make_it_a_move_flag = new_options.GetBoolean( 'secret_discord_dnd_fix' )
        
        if make_it_a_move_flag:
            
            flags = QC.Qt.DropAction.MoveAction
            
        else:
            
            flags = QC.Qt.DropAction.MoveAction | QC.Qt.DropAction.CopyAction
            
        
        seen_export_filenames = set()
        
        fallback_filename_terms = ClientExportingFiles.ParseExportPhrase( '{hash}' )
        
        try:
            
            filename_pattern = new_options.GetString( 'discord_dnd_filename_pattern' )
            filename_terms = ClientExportingFiles.ParseExportPhrase( filename_pattern )
            
            if len( filename_terms ) == 0:
                
                raise Exception()
                
            
        except Exception as e:
            
            filename_terms = fallback_filename_terms
            
        
        dnd_paths = []
        
        for ( i, ( m, original_path ) ) in enumerate( media_and_original_paths ):
            
            try:
                
                filename = ClientExportingFiles.GenerateExportFilename( this_dnd_temp_dir, m, filename_terms, i + 1, do_not_use_filenames = seen_export_filenames )
                
                if filename == HC.mime_ext_lookup[ m.GetMime() ]:
                    
                    raise Exception()
                    
                
            except Exception as e:
                
                filename = ClientExportingFiles.GenerateExportFilename( this_dnd_temp_dir, m, fallback_filename_terms, i + 1, do_not_use_filenames = seen_export_filenames )
                
            
            seen_export_filenames.add( filename )
            
            dnd_path = os.path.join( this_dnd_temp_dir, filename )
            
            # YO, filename may include a pathsep according to various export filename rules. there are a couple ways we could handle this, but let's just follow the general rules of Export Folders and manual exports
            
            path_dir = os.path.dirname( dnd_path )
            
            HydrusPaths.MakeSureDirectoryExists( path_dir )
            
            HydrusPaths.MirrorFile( original_path, dnd_path )
            
            dnd_paths.append( dnd_path )
            
        
    else:
        
        dnd_paths = original_paths
        flags = QC.Qt.DropAction.CopyAction
        
    
    uri_list = []
    
    for path in dnd_paths:
        
        uri_list.append( QC.QUrl.fromLocalFile( path ) )
        
    
    data_object.setUrls( uri_list )
    
    #
    
    hashes = [ m.GetHash() for m in media ]
    
    data_object.setHydrusFiles( page_key, hashes )
    
    # old way of doing this that makes some external programs (discord) reject it
    '''
    if page_key is None:
        
        encoded_page_key = None
        
    else:
        
        encoded_page_key = page_key.hex()
        
    
    data_obj = ( encoded_page_key, [ hash.hex() for hash in hashes ] )
    
    data_str = json.dumps( data_obj )
    
    data_bytes = bytes( data_str, 'utf-8' )
    
    data_object.setData( 'application/hydrus-media', data_bytes )
    '''
    #
    
    drag_object.setMimeData( data_object )
    
    cursor = QG.QCursor( QC.Qt.CursorShape.ClosedHandCursor )
    
    drag_object.setDragCursor( cursor.pixmap(), QC.Qt.DropAction.MoveAction )
    
    result = drag_object.exec_( flags, QC.Qt.DropAction.CopyAction )
    
    return result
    

class FileDropTarget( QC.QObject ):
    
    def __init__( self, parent: QW.QWidget, filenames_callable = None, url_callable = None, media_callable = None ):
        
        super().__init__( parent )
        
        self._parent = parent
        
        if parent:
            
            parent.setAcceptDrops( True )
            
        
        self._filenames_callable = filenames_callable
        self._url_callable = url_callable
        self._media_callable = media_callable
        
    
    def eventFilter( self, watched, event ):
        
        try:
            
            if event.type() == QC.QEvent.Type.Drop:
                
                event = typing.cast( QG.QDropEvent, event )
                
                if self.OnDrop( event.position().toPoint().x(), event.position().toPoint().y() ):
                    
                    event.setDropAction( self.OnData( event.mimeData(), event.proposedAction() ) )
                    
                    event.accept()
                    
                
            elif event.type() == QC.QEvent.Type.DragEnter:
                
                event.accept()
                
            
        except Exception as e:
            
            HydrusData.ShowException( e )
            
            return True
            
        
        return False
        
    
    def OnData( self, mime_data, result ):
        
        media_dnd = isinstance( mime_data, QMimeDataHydrusFiles )
        urls_dnd = mime_data.hasUrls()
        text_dnd = mime_data.hasText()
        
        if media_dnd and self._media_callable is not None:
            
            result = mime_data.hydrusFiles()
            
            if result is not None:
                
                ( page_key, hashes ) = result
                
                if page_key is not None:
                    
                    CG.client_controller.CallAfterQtSafe( self, self._media_callable, page_key, hashes )  # callafter so we can terminate dnd event now
                    
                
            
            result = QC.Qt.DropAction.MoveAction
            
            # old way of doing it that messed up discord et al
            '''
        elif mime_data.formats().count( 'application/hydrus-media' ) and self._media_callable is not None:
            
            mview = mime_data.data( 'application/hydrus-media' )

            data_bytes = mview.data()

            data_str = str( data_bytes, 'utf-8' )

            (encoded_page_key, encoded_hashes) = json.loads( data_str )

            if encoded_page_key is not None:
                
                page_key = bytes.fromhex( encoded_page_key )
                hashes = [ bytes.fromhex( encoded_hash ) for encoded_hash in encoded_hashes ]

                CG.client_controller.CallAfterQtSafe( self, self._media_callable, page_key, hashes )  # callafter so we can terminate dnd event now
                

            result = QC.Qt.DropAction.MoveAction
            '''
        elif urls_dnd or text_dnd:
            
            paths = []
            urls = []
            
            if urls_dnd:
                
                dnd_items = mime_data.urls()
                
                for dnd_item in dnd_items:
                    
                    if dnd_item.isLocalFile():
                        
                        paths.append( os.path.normpath( dnd_item.toLocalFile() ) )
                        
                    else:
                        
                        urls.append( dnd_item.url() )
                        
                    
                
            else:
                
                text = mime_data.text()
                
                text = HydrusText.CleanseImportText( text )
                
                text_lines = HydrusText.DeserialiseNewlinedTexts( text )
                
                for text_line in text_lines:
                    
                    if text_line.startswith( 'http' ):
                        
                        urls.append( text_line )
                        
                        # ignore 'paths'
                        
                    
                
            
            if self._filenames_callable is not None:
                
                if len( paths ) > 0:
                    
                    CG.client_controller.CallAfterQtSafe( self, self._filenames_callable, paths ) # callafter to terminate dnd event now
                    
                
            
            if self._url_callable is not None:
                
                if len( urls ) > 0:
                    
                    for url in urls:
                        
                        # https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/Data_URIs
                        # data:image/png;base64,(data)
                        # so what I prob have to do here is parse the file, decode from base64 or whatever, and then write to a fresh temp location and call self._filenames_callable
                        # but I need to figure out a way to reproduce this on my own. Chrome is supposed to do it on image DnD, but didn't for me
                        if url.startswith( 'data:' ) or len( url ) > 8 * 1024:
                            
                            HydrusData.ShowText( 'This drag and drop was in the unsupported \'Data URL\' format. hydev would like to know more about this so he can fix it.' )
                            
                            continue
                            
                        
                        CG.client_controller.CallAfterQtSafe( self, self._url_callable, url ) # callafter to terminate dnd event now
                        
                    
                
            
            result = QC.Qt.DropAction.IgnoreAction
            
        else:
            
            result = QC.Qt.DropAction.IgnoreAction
            
        
        return result
        
    
    def OnDrop( self, x, y ):
        
        screen_position = ClientGUIFunctions.ClientToScreen( self._parent, QC.QPoint( x, y ) )
        
        drop_tlw = QW.QApplication.topLevelAt( screen_position )
        my_tlw = self._parent.window()
        
        if drop_tlw == my_tlw:
            
            return True
            
        else:
            
            return False
            
        
    
    # setting OnDragOver to return copy gives Linux trouble with page tab drops with shift held down
