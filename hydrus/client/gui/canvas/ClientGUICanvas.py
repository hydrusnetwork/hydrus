import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusLists
from hydrus.core import HydrusPaths
from hydrus.core import HydrusTags
from hydrus.core import HydrusTime
from hydrus.core.files.images import HydrusImageHandling

from hydrus.client import ClientApplicationCommand as CAC
from hydrus.client import ClientConstants as CC
from hydrus.client import ClientData
from hydrus.client import ClientDuplicates
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientLocation
from hydrus.client import ClientPaths
from hydrus.client.gui import ClientGUICore as CGC
from hydrus.client.gui import ClientGUIDialogs
from hydrus.client.gui import ClientGUIDialogsManage
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIDuplicates
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIMedia
from hydrus.client.gui import ClientGUIMediaActions
from hydrus.client.gui import ClientGUIMediaControls
from hydrus.client.gui import ClientGUIMediaMenus
from hydrus.client.gui import ClientGUIMenus
from hydrus.client.gui import ClientGUIRatings
from hydrus.client.gui import ClientGUIScrolledPanelsEdit
from hydrus.client.gui import ClientGUIScrolledPanelsManagement
from hydrus.client.gui import ClientGUIShortcuts
from hydrus.client.gui import ClientGUITags
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.canvas import ClientGUICanvasHoverFrames
from hydrus.client.gui.canvas import ClientGUICanvasMedia
from hydrus.client.media import ClientMedia
from hydrus.client.media import ClientMediaFileFilter
from hydrus.client.metadata import ClientContentUpdates
from hydrus.client.metadata import ClientRatings
from hydrus.client.metadata import ClientTags
from hydrus.client.metadata import ClientTagSorting
from hydrus.client.search import ClientSearch

def AddAudioVolumeMenu( menu, canvas_type ):
    
    mute_volume_type = None
    volume_volume_type = ClientGUIMediaControls.AUDIO_GLOBAL
    
    if canvas_type == CC.CANVAS_MEDIA_VIEWER:
        
        mute_volume_type = ClientGUIMediaControls.AUDIO_MEDIA_VIEWER
        
        if CG.client_controller.new_options.GetBoolean( 'media_viewer_uses_its_own_audio_volume' ):
            
            volume_volume_type = ClientGUIMediaControls.AUDIO_MEDIA_VIEWER
            
        
    elif canvas_type == CC.CANVAS_PREVIEW:
        
        mute_volume_type = ClientGUIMediaControls.AUDIO_PREVIEW
        
        if CG.client_controller.new_options.GetBoolean( 'preview_uses_its_own_audio_volume' ):
            
            volume_volume_type = ClientGUIMediaControls.AUDIO_PREVIEW
            
        
    
    volume_menu = ClientGUIMenus.GenerateMenu( menu )
    
    ( global_mute_option_name, global_volume_option_name ) = ClientGUIMediaControls.volume_types_to_option_names[ ClientGUIMediaControls.AUDIO_GLOBAL ]
    
    if CG.client_controller.new_options.GetBoolean( global_mute_option_name ):
        
        label = 'unmute global'
        
    else:
        
        label = 'mute global'
        
    
    ClientGUIMenus.AppendMenuItem( volume_menu, label, 'Mute/unmute audio.', ClientGUIMediaControls.FlipMute, ClientGUIMediaControls.AUDIO_GLOBAL )
    
    #
    
    if mute_volume_type is not None:
        
        ClientGUIMenus.AppendSeparator( volume_menu )
        
        ( mute_option_name, volume_option_name ) = ClientGUIMediaControls.volume_types_to_option_names[ mute_volume_type ]
        
        if CG.client_controller.new_options.GetBoolean( mute_option_name ):
            
            label = 'unmute {}'.format( ClientGUIMediaControls.volume_types_str_lookup[ mute_volume_type ] )
            
        else:
            
            label = 'mute {}'.format( ClientGUIMediaControls.volume_types_str_lookup[ mute_volume_type ] )
            
        
        ClientGUIMenus.AppendMenuItem( volume_menu, label, 'Mute/unmute audio.', ClientGUIMediaControls.FlipMute, mute_volume_type )
        
    
    #
    
    ClientGUIMenus.AppendSeparator( volume_menu )
    
    ( mute_option_name, volume_option_name ) = ClientGUIMediaControls.volume_types_to_option_names[ volume_volume_type ]
    
    # 0-100 inclusive
    volumes = list( range( 0, 110, 10 ) )
    
    current_volume = CG.client_controller.new_options.GetInteger( volume_option_name )
    
    if current_volume not in volumes:
        
        volumes.append( current_volume )
        
        volumes.sort()
        
    
    for volume in volumes:
        
        label = 'volume: {}'.format( volume )
        
        if volume == current_volume:
            
            ClientGUIMenus.AppendMenuCheckItem( volume_menu, label, 'Set the volume.', True, ClientGUIMediaControls.ChangeVolume, volume_volume_type, volume )
            
        else:
            
            ClientGUIMenus.AppendMenuItem( volume_menu, label, 'Set the volume.', ClientGUIMediaControls.ChangeVolume, volume_volume_type, volume )
            
        
    
    ClientGUIMenus.AppendMenu( menu, volume_menu, 'volume' )
    

class CanvasBackgroundColourGenerator( object ):
    
    def GetColour( self ) -> QG.QColor:
        
        return CG.client_controller.new_options.GetColour( CC.COLOUR_MEDIA_BACKGROUND )
        
    
    def CanDoTransparencyCheckerboard( self ) -> bool:
        
        return CG.client_controller.new_options.GetBoolean( 'draw_transparency_checkerboard_media_canvas' )
        
    

class CanvasBackgroundColourGeneratorDuplicates( CanvasBackgroundColourGenerator ):
    
    def __init__( self, duplicate_canvas ):
        
        CanvasBackgroundColourGenerator.__init__( self )
        
        self._duplicate_canvas = duplicate_canvas
        
    
    def CanDoTransparencyCheckerboard( self ) -> bool:
        
        return CG.client_controller.new_options.GetBoolean( 'draw_transparency_checkerboard_media_canvas' ) or CG.client_controller.new_options.GetBoolean( 'draw_transparency_checkerboard_media_canvas_duplicates' )
        
    
    def GetColour( self ) -> QG.QColor:
        
        new_options = CG.client_controller.new_options
        
        normal_colour = new_options.GetColour( CC.COLOUR_MEDIA_BACKGROUND )
        
        if self._duplicate_canvas.IsShowingAPair():
            
            if self._duplicate_canvas.IsShowingFileA():
                
                duplicate_intensity = new_options.GetNoneableInteger( 'duplicate_background_switch_intensity_a' )
                
            else:
                
                duplicate_intensity = new_options.GetNoneableInteger( 'duplicate_background_switch_intensity_b' )
                
            
            return ClientGUIFunctions.GetLighterDarkerColour( normal_colour, duplicate_intensity )
            
        
        return normal_colour
        
    

# cribbing from here https://doc.qt.io/qt-5/layout.html#how-to-write-a-custom-layout-manager
# not finished, but a start as I continue to refactor. might want to rename to 'draggable layout' or something too, since it doesn't actually care about media container that much, and instead subclass vboxlayout?
class CanvasLayout( QW.QLayout ):
    
    def __init__( self ):
        
        QW.QLayout.__init__( self )
        
        self._current_drag_delta = QC.QPoint( 0, 0 )
        
        self._layout_items = []
        
    
    def addItem( self, layout_item: QW.QLayoutItem ) -> None:
        
        self._layout_items.append( layout_item )
        
    
    def itemAt( self, index: int ):
        
        try:
            
            return self._layout_items[ index ]
            
        except IndexError:
            
            return None
            
        
    
    def minimumSize(self) -> QC.QSize:
        
        return self.sizeHint()
        
    
    def resetDragDelta( self ):
        
        self._current_drag_delta = QC.QPoint( 0, 0 )
        
    
    def setGeometry( self, rect: QC.QRect ) -> None:
        
        if len( self._layout_items ) == 0:
            
            return
            
        
        layout_item = self._layout_items[0]
        
        size = self.sizeHint()
        
        # the given rect is the whole canvas?
        
        natural_x = ( rect.width() - size.width() ) // 2
        natural_y = ( rect.height() - size.height() ) // 2
        
        topleft = QC.QPoint( natural_x, natural_y ) + self._current_drag_delta
        
        media_container_rect = QC.QRect( topleft, size )
        
        layout_item.setGeometry( media_container_rect )
        
    
    def sizeHint(self) -> QC.QSize:
        
        if len( self._layout_items ) == 0:
            
            return QC.QSize( 0, 0 )
            
        else:
            
            return self._layout_items[0].sizeHint()
            
        
    
    def takeAt( self, index: int ):
        
        layout_item = self.itemAt( index )
        
        if layout_item is None:
            
            return 0
            
        
        del self._layout_items[ index ]
        
        return layout_item
        
    
    def updateDragDelta( self, delta: QC.QPoint ):
        
        self._current_drag_delta += delta
        
    

class LayoutEventSilencer( QC.QObject ):
    
    def eventFilter( self, watched, event ):
        
        try:
            
            if watched == self.parent() and event.type() == QC.QEvent.LayoutRequest:
                
                return True
                
            
        except Exception as e:
            
            HydrusData.ShowException( e )
            
            return True
            
        
        return False
        
    

class Canvas( CAC.ApplicationCommandProcessorMixin, QW.QWidget ):
    
    CANVAS_TYPE = CC.CANVAS_MEDIA_VIEWER
    
    def __init__( self, parent, location_context: ClientLocation.LocationContext ):
        
        QW.QWidget.__init__( self, parent )
        CAC.ApplicationCommandProcessorMixin.__init__( self )
        
        self.setSizePolicy( QW.QSizePolicy.Expanding, QW.QSizePolicy.Expanding )
        
        self._location_context = location_context
        
        self._background_colour_generator = CanvasBackgroundColourGenerator()
        
        self._current_media_start_time_ms = HydrusTime.GetNowMS()
        
        self._new_options = CG.client_controller.new_options
        
        self._canvas_key = HydrusData.GenerateKey()
        
        self._maintain_pan_and_zoom = False
        
        self._service_keys_to_services = {}
        
        self._current_media = None
        
        catch_mouse = True
        
        # once we have catch_mouse full shortcut support for canvases, swap out this out for an option to swallow activating clicks
        ignore_activating_mouse_click = catch_mouse and self.CANVAS_TYPE != CC.CANVAS_PREVIEW
        
        self._my_shortcuts_handler = ClientGUIShortcuts.ShortcutsHandler( self, [ 'media', 'media_viewer' ], catch_mouse = catch_mouse, ignore_activating_mouse_click = ignore_activating_mouse_click )
        
        self._layout_silencer = LayoutEventSilencer( self )
        self.installEventFilter( self._layout_silencer )
        
        self._click_drag_reporting_filter = MediaContainerDragClickReportingFilter( self )
        
        self.installEventFilter( self._click_drag_reporting_filter )
        
        self._media_container = ClientGUICanvasMedia.MediaContainer( self, self.CANVAS_TYPE, self._background_colour_generator, self._click_drag_reporting_filter )
        
        self._last_drag_pos = None
        self._current_drag_is_touch = False
        self._last_motion_pos = QC.QPoint( 0, 0 )
        
        self._widget_event_filter = QP.WidgetEventFilter( self )
        
        self._media_container.readyForNeighbourPrefetch.connect( self._PrefetchNeighbours )
        
        self._media_container.zoomChanged.connect( self.ZoomChanged )
        
        CG.client_controller.sub( self, 'ZoomIn', 'canvas_zoom_in' )
        CG.client_controller.sub( self, 'ZoomOut', 'canvas_zoom_out' )
        CG.client_controller.sub( self, 'ZoomSwitch', 'canvas_zoom_switch' )
        CG.client_controller.sub( self, 'OpenExternally', 'canvas_open_externally' )
        CG.client_controller.sub( self, 'ManageTags', 'canvas_manage_tags' )
        CG.client_controller.sub( self, 'update', 'notify_new_colourset' )
        
    
    def _Archive( self ):
        
        if self._current_media is not None:
            
            CG.client_controller.Write( 'content_updates', ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ARCHIVE, ( self._current_media.GetHash(), ) ) ) )
            
        
    
    def _CopyBMPToClipboard( self, resolution = None ):
        
        copied = False
        
        if self._current_media is not None:
            
            if self._current_media.IsStaticImage():
                
                CG.client_controller.pub( 'clipboard', 'bmp', ( self._current_media, resolution ) )
                
                copied = True
                
            
        
        return copied
        
    
    def _CopyHashToClipboard( self, hash_type ):
        
        if self._current_media is None:
            
            return
            
        
        ClientGUIMedia.CopyHashesToClipboard( self, hash_type, [ self._current_media ] )
        
    
    def _CopyFileToClipboard( self ):
        
        if self._current_media is not None:
            
            client_files_manager = CG.client_controller.client_files_manager
            
            paths = [ client_files_manager.GetFilePath( self._current_media.GetHash(), self._current_media.GetMime() ) ]
            
            CG.client_controller.pub( 'clipboard', 'paths', paths )
            
        
    
    def _CopyPathToClipboard( self ):
        
        if self._current_media is not None:
            
            client_files_manager = CG.client_controller.client_files_manager
            
            path = client_files_manager.GetFilePath( self._current_media.GetHash(), self._current_media.GetMime() )
            
            CG.client_controller.pub( 'clipboard', 'text', path )
            
        
    
    def _Delete( self, media = None, default_reason = None, file_service_key = None, just_get_content_update_packages = False ) -> typing.Union[ bool, typing.Collection[ ClientContentUpdates.ContentUpdatePackage ] ]:
        
        if media is None:
            
            if self._current_media is None:
                
                return False
                
            
            media = [ self._current_media ]
            
        
        if default_reason is None:
            
            default_reason = 'Deleted from Preview or Media Viewer.'
            
        
        if file_service_key is None:
            
            if len( self._location_context.current_service_keys ) == 1:
                
                ( possible_suggested_file_service_key, ) = self._location_context.current_service_keys
                
                if CG.client_controller.services_manager.GetServiceType( possible_suggested_file_service_key ) in HC.SPECIFIC_LOCAL_FILE_SERVICES + ( HC.FILE_REPOSITORY, ):
                    
                    file_service_key = possible_suggested_file_service_key
                    
                
            
        
        try:
            
            ( hashes_physically_deleted, content_update_packages ) = ClientGUIDialogsQuick.GetDeleteFilesJobs( self, media, default_reason, suggested_file_service_key = file_service_key )
            
        except HydrusExceptions.CancelledException:
            
            return False
            
        
        def do_it( content_update_packages ):
            
            for content_update_package in content_update_packages:
                
                CG.client_controller.WriteSynchronous( 'content_updates', content_update_package )
                
            
        
        if just_get_content_update_packages:
            
            return content_update_packages
            
        else:
            
            CG.client_controller.CallToThread( do_it, content_update_packages )
            
            return True
            
        
    
    def _DrawBackgroundBitmap( self, painter: QG.QPainter ):
        
        background_colour = self._background_colour_generator.GetColour()
        
        painter.setBackground( QG.QBrush( background_colour ) )
        
        painter.eraseRect( painter.viewport() )
        
        self._DrawBackgroundDetails( painter )
        
    
    def _DrawBackgroundDetails( self, painter ):
        
        pass
        
    
    def _GetIndexString( self ):
        
        return ''
        
    
    def _Inbox( self ):
        
        if self._current_media is None:
            
            return
            
        
        CG.client_controller.Write( 'content_updates', ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_INBOX, ( self._current_media.GetHash(), ) ) ) )
        
    
    def _ManageNotes( self, name_to_start_on = None ):
        
        if self._current_media is None:
            
            return
            
        
        ClientGUIMediaActions.EditFileNotes( self, self._current_media, name_to_start_on = name_to_start_on )
        
    
    def _ManageRatings( self ):
        
        if self._current_media is None:
            
            return
            
        
        if len( CG.client_controller.services_manager.GetServices( HC.RATINGS_SERVICES ) ) > 0:
            
            with ClientGUIDialogsManage.DialogManageRatings( self, ( self._current_media, ) ) as dlg:
                
                dlg.exec()
                
            
        
    
    def _ManageTags( self ):
        
        if self._current_media is None:
            
            return
            
        
        for child in self.children():
            
            if isinstance( child, ClientGUITopLevelWindowsPanels.FrameThatTakesScrollablePanel ):
                
                panel = child.GetPanel()
                
                if isinstance( panel, ClientGUITags.ManageTagsPanel ):
                    
                    child.activateWindow()
                    
                    command = CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_SET_SEARCH_FOCUS )
                    
                    panel.ProcessApplicationCommand( command )
                    
                    return
                    
                
            
        
        # take any focus away from hover window, which will mess up window order when it hides due to the new frame
        self.setFocus( QC.Qt.OtherFocusReason )
        
        title = 'manage tags'
        frame_key = 'manage_tags_frame'
        
        manage_tags = ClientGUITopLevelWindowsPanels.FrameThatTakesScrollablePanel( self, title, frame_key )
        
        panel = ClientGUITags.ManageTagsPanel( manage_tags, self._location_context, ( self._current_media, ), immediate_commit = True, canvas_key = self._canvas_key )
        
        manage_tags.SetPanel( panel )
        
    
    def _ManageTimestamps( self ):
        
        if self._current_media is None:
            
            return
            
        
        ClientGUIMediaActions.EditFileTimestamps( self, [ self._current_media ] )
        
    
    def _ManageURLs( self ):
        
        if self._current_media is None:
            
            return
            
        
        title = 'manage known urls'
        
        with ClientGUITopLevelWindowsPanels.DialogManage( self, title ) as dlg:
            
            panel = ClientGUIScrolledPanelsManagement.ManageURLsPanel( dlg, ( self._current_media, ) )
            
            dlg.SetPanel( panel )
            
            dlg.exec()
            
        
    
    def _MediaFocusWentToExternalProgram( self ):
        
        if self._current_media is None:
            
            return
            
        
        mime = self._current_media.GetMime()
        
        if self._current_media.HasDuration():
            
            self._media_container.Pause()
            
        
    
    def _OpenExternally( self ):
        
        if self._current_media is None:
            
            return
            
        
        hash = self._current_media.GetHash()
        mime = self._current_media.GetMime()
        
        client_files_manager = CG.client_controller.client_files_manager
        
        path = client_files_manager.GetFilePath( hash, mime )
        
        launch_path = self._new_options.GetMimeLaunch( mime )
        
        HydrusPaths.LaunchFile( path, launch_path )
        
        self._MediaFocusWentToExternalProgram()
        
    
    def _OpenFileInWebBrowser( self ):
        
        if self._current_media is not None:
            
            hash = self._current_media.GetHash()
            mime = self._current_media.GetMime()
            
            client_files_manager = CG.client_controller.client_files_manager
            
            path = client_files_manager.GetFilePath( hash, mime )
            
            ClientPaths.LaunchPathInWebBrowser( path )
            
            self._MediaFocusWentToExternalProgram()
            
        
    
    def _OpenFileLocation( self ):
        
        if self._current_media is not None:
            
            ClientGUIMedia.OpenFileLocation( self._current_media )
            
            self._MediaFocusWentToExternalProgram()
            
        
    
    def _OpenKnownURL( self ):
        
        if self._current_media is not None:
            
            ClientGUIMedia.DoOpenKnownURLFromShortcut( self, self._current_media )
            
        
    
    def _PrefetchNeighbours( self ):
        
        pass
        
    
    def _SaveCurrentMediaViewTime( self ):
        
        now_ms = HydrusTime.GetNowMS()
        
        view_timestamp_ms = self._current_media_start_time_ms
        
        viewtime_delta = ( now_ms - self._current_media_start_time_ms ) // 1000
        
        self._current_media_start_time_ms = now_ms
        
        if self._current_media is None:
            
            return
            
        
        hash = self._current_media.GetHash()
        
        CG.client_controller.file_viewing_stats_manager.FinishViewing( self._current_media, self.CANVAS_TYPE, view_timestamp_ms, viewtime_delta )
        
    
    def _SeekDeltaCurrentMedia( self, direction, duration_ms ):
        
        if self._current_media is None:
            
            return
            
        
        self._media_container.SeekDelta( direction, duration_ms )
        
    
    def _ShowMediaInNewPage( self ):
        
        if self._current_media is None:
            
            return
            
        
        hash = self._current_media.GetHash()
        
        hashes = { hash }
        
        CG.client_controller.pub( 'new_page_query', self._location_context, initial_hashes = hashes )
        
    
    def _Undelete( self ):
        
        if self._current_media is None:
            
            return
            
        
        ClientGUIMediaActions.UndeleteMedia( self, ( self._current_media, ) )
        
    
    def CleanBeforeDestroy( self ):
        
        self.ClearMedia()
        
    
    def ClearMedia( self ):
        
        self.SetMedia( None )
        
    
    def BeginDrag( self ):
        
        point = self.mapFromGlobal( QG.QCursor.pos() )
        
        self._last_drag_pos = point
        self._current_drag_is_touch = False
        
    
    def resizeEvent( self, event ):
        
        my_size = self.size()
        
        if self._current_media is not None:
            
            media_container_size = self._media_container.size()
            
            if my_size != media_container_size:
                
                self._media_container.ZoomReinit()
                
                self._media_container.ResetCenterPosition()
                
                self.EndDrag()
                
            
        
        self.update()
        
    
    def EndDrag( self ):
        
        self._last_drag_pos = None
        
    
    def FlipActiveCustomShortcutName( self, name ):
        
        self._my_shortcuts_handler.FlipShortcuts( name )
        
    
    def GetActiveCustomShortcutNames( self ):
        
        return self._my_shortcuts_handler.GetCustomShortcutNames()
        
    
    def ManageNotes( self, canvas_key, name_to_start_on = None ):
        
        if canvas_key == self._canvas_key:
            
            self._ManageNotes( name_to_start_on = name_to_start_on )
            
        
    
    def ManageTags( self, canvas_key ):
        
        if canvas_key == self._canvas_key:
            
            self._ManageTags()
            
        
    
    def MouseIsNearAnimationBar( self ):
        
        if self._current_media is None:
            
            return False
            
        else:
            
            return self._media_container.MouseIsNearAnimationBar()
            
        
    
    def MouseIsOverMedia( self ):
        
        if self._current_media is None:
            
            return False
            
        else:
            
            media_mouse_pos = self._media_container.mapFromGlobal( QG.QCursor.pos() )
            
            media_rect = self._media_container.rect()
            
            return media_rect.contains( media_mouse_pos )
            
        
    
    def OpenExternally( self, canvas_key ):
        
        if self._canvas_key == canvas_key:
            
            self._OpenExternally()
            
        
    
    def paintEvent( self, event ):
        
        painter = QG.QPainter( self )
        
        self._DrawBackgroundBitmap( painter )
        
    
    def PauseMedia( self ):
        
        self._media_container.Pause()
        
    
    def ProcessApplicationCommand( self, command: CAC.ApplicationCommand ):
        
        command_processed = True
        
        if command.IsSimpleCommand():
            
            action = command.GetSimpleAction()
            
            if action == CAC.SIMPLE_MANAGE_FILE_RATINGS:
                
                self._ManageRatings()
                
            elif action == CAC.SIMPLE_MANAGE_FILE_TAGS:
                
                self._ManageTags()
                
            elif action == CAC.SIMPLE_MANAGE_FILE_URLS:
                
                self._ManageURLs()
                
            elif action == CAC.SIMPLE_MANAGE_FILE_NOTES:
                
                self._ManageNotes()
                
            elif action == CAC.SIMPLE_MANAGE_FILE_TIMESTAMPS:
                
                self._ManageTimestamps()
                
            elif action == CAC.SIMPLE_OPEN_KNOWN_URL:
                
                self._OpenKnownURL()
                
            elif action == CAC.SIMPLE_ARCHIVE_FILE:
                
                self._Archive()
                
            elif action in ( CAC.SIMPLE_COPY_BMP, CAC.SIMPLE_COPY_BMP_OR_FILE_IF_NOT_BMPABLE, CAC.SIMPLE_COPY_LITTLE_BMP ):
                
                if self._current_media is None:
                    
                    return
                    
                
                copied = False
                
                if self._current_media.IsStaticImage():
                    
                    ( width, height ) = self._current_media.GetResolution()
                    
                    if width is not None and height is not None:
                        
                        if action == CAC.SIMPLE_COPY_LITTLE_BMP and ( width > 1024 or height > 1024 ):
                            
                            target_resolution = HydrusImageHandling.GetThumbnailResolution( self._current_media.GetResolution(), ( 1024, 1024 ), HydrusImageHandling.THUMBNAIL_SCALE_TO_FIT, 100 )
                            
                            copied = self._CopyBMPToClipboard( resolution = target_resolution )
                            
                        else:
                            
                            copied = self._CopyBMPToClipboard()
                            
                        
                    
                if action == CAC.SIMPLE_COPY_BMP_OR_FILE_IF_NOT_BMPABLE and not copied:
                    
                    self._CopyFileToClipboard()
                    
                
            elif action == CAC.SIMPLE_COPY_FILE:
                
                self._CopyFileToClipboard()
                
            elif action == CAC.SIMPLE_COPY_PATH:
                
                self._CopyPathToClipboard()
                
            elif action == CAC.SIMPLE_COPY_SHA256_HASH:
                
                self._CopyHashToClipboard( 'sha256' )
                
            elif action == CAC.SIMPLE_COPY_MD5_HASH:
                
                self._CopyHashToClipboard( 'md5' )
                
            elif action == CAC.SIMPLE_COPY_SHA1_HASH:
                
                self._CopyHashToClipboard( 'sha1' )
                
            elif action == CAC.SIMPLE_COPY_SHA512_HASH:
                
                self._CopyHashToClipboard( 'sha512' )
                
            elif action == CAC.SIMPLE_DELETE_FILE:
                
                self._Delete()
                
            elif action == CAC.SIMPLE_UNDELETE_FILE:
                
                self._Undelete()
                
            elif action == CAC.SIMPLE_INBOX_FILE:
                
                self._Inbox()
                
            elif action == CAC.SIMPLE_OPEN_FILE_IN_EXTERNAL_PROGRAM:
                
                self._OpenExternally()
                
            elif action == CAC.SIMPLE_OPEN_FILE_IN_FILE_EXPLORER:
                
                self._OpenFileLocation()
                
            elif action == CAC.SIMPLE_PAN_UP:
                
                self._media_container.DoManualPan( 0, -1 )
                
            elif action == CAC.SIMPLE_PAN_DOWN:
                
                self._media_container.DoManualPan( 0, 1 )
                
            elif action == CAC.SIMPLE_PAN_LEFT:
                
                self._media_container.DoManualPan( -1, 0 )
                
            elif action == CAC.SIMPLE_PAN_RIGHT:
                
                self._media_container.DoManualPan( 1, 0 )
                
            elif action in ( CAC.SIMPLE_PAN_TOP_EDGE, CAC.SIMPLE_PAN_BOTTOM_EDGE, CAC.SIMPLE_PAN_LEFT_EDGE, CAC.SIMPLE_PAN_RIGHT_EDGE, CAC.SIMPLE_PAN_VERTICAL_CENTER, CAC.SIMPLE_PAN_HORIZONTAL_CENTER ):
                
                self._media_container.DoEdgePan( action )
                
            elif action == CAC.SIMPLE_PAUSE_MEDIA:
                
                self._media_container.Pause()
                
            elif action == CAC.SIMPLE_PAUSE_PLAY_MEDIA:
                
                self._media_container.PausePlay()
                
            elif action == CAC.SIMPLE_SHOW_DUPLICATES:
                
                if self._current_media is not None:
                    
                    hash = self._current_media.GetHash()
                    
                    duplicate_type = command.GetSimpleData()
                    
                    ClientGUIMedia.ShowDuplicatesInNewPage( self._location_context, hash, duplicate_type )
                    
                
            elif action == CAC.SIMPLE_DUPLICATE_MEDIA_CLEAR_FOCUSED_FALSE_POSITIVES:
                
                # TODO: when media knows dupe relationships, all these lads here need a media scan for the existence of alternate groups or whatever
                # no duplicate group->don't start the process
                
                if self._current_media is not None:
                    
                    hash = self._current_media.GetHash()
                    
                    ClientGUIDuplicates.ClearFalsePositives( self, ( hash, ) )
                    
                
            elif action == CAC.SIMPLE_DUPLICATE_MEDIA_CLEAR_FALSE_POSITIVES:
                
                if self._current_media is not None:
                    
                    hash = self._current_media.GetHash()
                    
                    ClientGUIDuplicates.ClearFalsePositives( self, ( hash, ) )
                    
                
            elif action == CAC.SIMPLE_DUPLICATE_MEDIA_DISSOLVE_FOCUSED_ALTERNATE_GROUP:
                
                if self._current_media is not None:
                    
                    hash = self._current_media.GetHash()
                    
                    ClientGUIDuplicates.DissolveAlternateGroup( self, ( hash, ) )
                    
                
            elif action == CAC.SIMPLE_DUPLICATE_MEDIA_DISSOLVE_ALTERNATE_GROUP:
                
                if self._current_media is not None:
                    
                    hash = self._current_media.GetHash()
                    
                    ClientGUIDuplicates.DissolveAlternateGroup( self, ( hash, ) )
                    
                
            elif action == CAC.SIMPLE_DUPLICATE_MEDIA_DISSOLVE_FOCUSED_DUPLICATE_GROUP:
                
                if self._current_media is not None:
                    
                    hash = self._current_media.GetHash()
                    
                    ClientGUIDuplicates.DissolveDuplicateGroup( self, ( hash, ) )
                    
                
            elif action == CAC.SIMPLE_DUPLICATE_MEDIA_DISSOLVE_DUPLICATE_GROUP:
                
                if self._current_media is not None:
                    
                    hash = self._current_media.GetHash()
                    
                    ClientGUIDuplicates.DissolveDuplicateGroup( self, ( hash, ) )
                    
                
            elif action == CAC.SIMPLE_DUPLICATE_MEDIA_REMOVE_FOCUSED_FROM_ALTERNATE_GROUP:
                
                if self._current_media is not None:
                    
                    hash = self._current_media.GetHash()
                    
                    ClientGUIDuplicates.RemoveFromAlternateGroup( self, ( hash, ) )
                    
                
            elif action == CAC.SIMPLE_DUPLICATE_MEDIA_REMOVE_FOCUSED_FROM_DUPLICATE_GROUP:
                
                if self._current_media is not None:
                    
                    hash = self._current_media.GetHash()
                    
                    ClientGUIDuplicates.RemoveFromDuplicateGroup( self, ( hash, ) )
                    
                
            elif action == CAC.SIMPLE_DUPLICATE_MEDIA_RESET_FOCUSED_POTENTIAL_SEARCH:
                
                if self._current_media is not None:
                    
                    hash = self._current_media.GetHash()
                    
                    ClientGUIDuplicates.ResetPotentialSearch( self, ( hash, ) )
                    
                
            elif action == CAC.SIMPLE_DUPLICATE_MEDIA_RESET_POTENTIAL_SEARCH:
                
                if self._current_media is not None:
                    
                    hash = self._current_media.GetHash()
                    
                    ClientGUIDuplicates.ResetPotentialSearch( self, ( hash, ) )
                    
                
            elif action == CAC.SIMPLE_DUPLICATE_MEDIA_REMOVE_FOCUSED_POTENTIALS:
                
                if self._current_media is not None:
                    
                    hash = self._current_media.GetHash()
                    
                    ClientGUIDuplicates.RemovePotentials( self, ( hash, ) )
                    
                
            elif action == CAC.SIMPLE_DUPLICATE_MEDIA_REMOVE_POTENTIALS:
                
                if self._current_media is not None:
                    
                    hash = self._current_media.GetHash()
                    
                    ClientGUIDuplicates.RemovePotentials( self, ( hash, ) )
                    
                
            elif action == CAC.SIMPLE_MEDIA_SEEK_DELTA:
                
                ( direction, ms ) = command.GetSimpleData()
                
                self._SeekDeltaCurrentMedia( direction, ms )
                
            elif action == CAC.SIMPLE_MOVE_ANIMATION_TO_PREVIOUS_FRAME:
                
                self._media_container.GotoPreviousOrNextFrame( -1 )
                
            elif action == CAC.SIMPLE_MOVE_ANIMATION_TO_NEXT_FRAME:
                
                self._media_container.GotoPreviousOrNextFrame( 1 )
                
            elif action == CAC.SIMPLE_ZOOM_IN:
                
                self._media_container.ZoomIn()
                
            elif action == CAC.SIMPLE_ZOOM_IN_VIEWER_CENTER:
                
                self._media_container.ZoomIn( zoom_center_type_override = ClientGUICanvasMedia.ZOOM_CENTERPOINT_VIEWER_CENTER )
                
            elif action == CAC.SIMPLE_ZOOM_OUT:
                
                self._media_container.ZoomOut()
                
            elif action == CAC.SIMPLE_ZOOM_OUT_VIEWER_CENTER:
                
                self._media_container.ZoomOut( zoom_center_type_override = ClientGUICanvasMedia.ZOOM_CENTERPOINT_VIEWER_CENTER )
                
            elif action == CAC.SIMPLE_SWITCH_BETWEEN_100_PERCENT_AND_CANVAS_ZOOM:
                
                self._media_container.ZoomSwitch()
                
            elif action == CAC.SIMPLE_SWITCH_BETWEEN_100_PERCENT_AND_MAX_ZOOM:
                
                self._media_container.ZoomSwitch100Max()
                
            elif action == CAC.SIMPLE_SWITCH_BETWEEN_CANVAS_AND_MAX_ZOOM:
                
                self._media_container.ZoomSwitchCanvasMax()
                
            elif action == CAC.SIMPLE_ZOOM_100:
                
                self._media_container.Zoom100()
                
            elif action == CAC.SIMPLE_ZOOM_CANVAS:
                
                self._media_container.ZoomCanvas()
                
            elif action == CAC.SIMPLE_ZOOM_DEFAULT:
                
                self._media_container.ZoomDefault()
                
            elif action == CAC.SIMPLE_ZOOM_MAX:
                
                self._media_container.ZoomMax()
                
            elif action == CAC.SIMPLE_SWITCH_BETWEEN_100_PERCENT_AND_CANVAS_ZOOM_VIEWER_CENTER:
                
                self._media_container.ZoomSwitch( zoom_center_type_override = ClientGUICanvasMedia.ZOOM_CENTERPOINT_VIEWER_CENTER )
                
            else:
                
                command_processed = False
                
            
        elif command.IsContentCommand():
            
            if self._current_media is None:
                
                return
                
            
            command_processed = ClientGUIMediaActions.ApplyContentApplicationCommandToMedia( self, command, ( self._current_media, ) )
            
        else:
            
            command_processed = False
            
        
        return command_processed
        
    
    def ResetMediaWindowCenterPosition( self ):
        
        self._media_container.ResetCenterPosition()
        
        self.EndDrag()
        
    
    def SetLocationContext( self, location_context: ClientLocation.LocationContext ):
        
        self._location_context = location_context
        
    
    def SetMedia( self, media: typing.Optional[ ClientMedia.MediaSingleton ] ):
        
        if media is not None and not self.isVisible():
            
            return
            
        
        if media is not None:
            
            media = media.GetDisplayMedia()
            
            if not ClientMedia.CanDisplayMedia( media ):
                
                media = None
                
            
        
        if media is not None:
            
            if self.CANVAS_TYPE == CC.CANVAS_PREVIEW:
                
                if not ClientMedia.UserWantsUsToDisplayMedia( media, self.CANVAS_TYPE ):
                    
                    media = None
                    
                
            
        
        if media != self._current_media:
            
            self.EndDrag()
            
            CG.client_controller.ResetIdleTimer()
            
            self._SaveCurrentMediaViewTime()
            
            previous_media = self._current_media
            
            self._current_media = media
            
            if self._current_media is None:
                
                self._media_container.ClearMedia()
                
            else:
                
                ( media_width, media_height ) = self._current_media.GetResolution()
                
                maintain_zoom = self._maintain_pan_and_zoom and previous_media is not None
                maintain_pan = self._maintain_pan_and_zoom

                if self._current_media.GetLocationsManager().IsLocal():
                    
                    self._media_container.SetMedia( self._current_media, maintain_zoom, maintain_pan )
                    
                else:
                    
                    self._current_media = None
                    
                
            
            CG.client_controller.pub( 'canvas_new_display_media', self._canvas_key, self._current_media )
            
            CG.client_controller.pub( 'canvas_new_index_string', self._canvas_key, self._GetIndexString() )
            
            self.update()
            
        
    
    def minimumSizeHint( self ):
        
        return QC.QSize( 120, 120 )
        
    
    def ZoomChanged( self ):
        
        self.update()
        
    
    def ZoomIn( self, canvas_key ):
        
        if canvas_key == self._canvas_key:
            
            self._media_container.ZoomIn()
            
        
    
    def ZoomOut( self, canvas_key ):
        
        if canvas_key == self._canvas_key:
            
            self._media_container.ZoomOut()
            
        
    
    def ZoomSwitch( self, canvas_key ):
        
        if canvas_key == self._canvas_key:
            
            self._media_container.ZoomSwitch()
            
        
    

class MediaContainerDragClickReportingFilter( QC.QObject ):
    
    def __init__( self, parent: Canvas ):
        
        QC.QObject.__init__( self, parent )
        
        self._canvas = parent
        
    
    def eventFilter( self, watched, event ):
        
        try:
            
            if event.type() == QC.QEvent.MouseButtonPress and event.button() == QC.Qt.LeftButton:
                
                self._canvas.BeginDrag()
                
            elif event.type() == QC.QEvent.MouseButtonRelease and event.button() == QC.Qt.LeftButton:
                
                self._canvas.EndDrag()
                
            
        except Exception as e:
            
            HydrusData.ShowException( e )
            
            return True
            
        
        return False
        
    
class CanvasPanel( Canvas ):
    
    CANVAS_TYPE = CC.CANVAS_PREVIEW
    
    def __init__( self, parent, page_key, location_context: ClientLocation.LocationContext ):
        
        Canvas.__init__( self, parent, location_context )
        
        self._page_key = page_key
        
        self._hidden_page_current_media = None
        self._hidden_page_paused_status = False
        
        self._media_container.launchMediaViewer.connect( self.LaunchMediaViewer )
        
        CG.client_controller.sub( self, 'ProcessContentUpdatePackage', 'content_updates_gui' )
        
    
    def mouseReleaseEvent( self, event ):
        
        if event.button() != QC.Qt.RightButton:
            
            Canvas.mouseReleaseEvent( self, event )
            
            return
            
        
        # contextmenu doesn't quite work here yet due to focus issues
        
        self.ShowMenu()
        
    
    def ClearMedia( self ):
        
        self._hidden_page_current_media = None
        
        Canvas.ClearMedia( self )
        
    
    def PageHidden( self ):
        
        if self._hidden_page_current_media is not None:
            
            return
            
        
        # TODO: ultimately, make an object for media/paused/position and have any media player able to give that and take it instead of setmedia
        # then we'll be able to 'continue' playing state from preview to full view and other stuff like this, and simply
        # also use that for all setmedia, and then if we have %-in-start options and paused/play-start options, we can initialise this object for that
        hidden_page_current_media = self._current_media
        hidden_page_pause_status = self._media_container.IsPaused()
        
        self.ClearMedia()
        
        self._hidden_page_current_media = hidden_page_current_media
        self._hidden_page_paused_status = hidden_page_pause_status
        
    
    def PageShown( self ):
        
        self.SetMedia( self._hidden_page_current_media )
        
        self._hidden_page_current_media = None
        
        if self._media_container.IsPaused() != self._hidden_page_paused_status:
            
            self._media_container.PausePlay()
            
        
    
    def ShowMenu( self ):
        
        menu = ClientGUIMenus.GenerateMenu( self )
        
        new_options = CG.client_controller.new_options
        
        advanced_mode = new_options.GetBoolean( 'advanced_mode' )
        
        if self._current_media is not None:
            
            services = CG.client_controller.services_manager.GetServices()
            
            locations_manager = self._current_media.GetLocationsManager()
            
            local_ratings_services = [ service for service in services if service.GetServiceType() in HC.RATINGS_SERVICES ]
            
            i_can_post_ratings = len( local_ratings_services ) > 0
            
            #
            
            info_lines = list( self._current_media.GetPrettyInfoLines() )
            
            top_line = info_lines.pop( 0 )
            
            info_menu = ClientGUIMenus.GenerateMenu( menu )
            
            ClientGUIMediaMenus.AddPrettyInfoLines( info_menu, info_lines )
            
            ClientGUIMediaMenus.AddFileViewingStatsMenu( info_menu, ( self._current_media, ) )
            
            ClientGUIMenus.AppendMenu( menu, info_menu, top_line )
            
            ClientGUIMenus.AppendSeparator( menu )
            
        
        AddAudioVolumeMenu( menu, self.CANVAS_TYPE )
        
        if self._current_media is not None:
            
            #
            
            ClientGUIMenus.AppendSeparator( menu )
            
            if self._current_media.HasInbox():
                
                ClientGUIMenus.AppendMenuItem( menu, 'archive', 'Archive this file.', self._Archive )
                
            
            if self._current_media.HasArchive():
                
                ClientGUIMenus.AppendMenuItem( menu, 'inbox', 'Send this files back to the inbox.', self._Inbox )
                
            
            ClientGUIMenus.AppendSeparator( menu )
            
            local_file_service_keys = CG.client_controller.services_manager.GetServiceKeys( ( HC.LOCAL_FILE_DOMAIN, ) )
            
            # brush this up to handle different service keys
            # undelete do an optional service key too
            
            local_file_service_keys_we_are_in = sorted( locations_manager.GetCurrent().intersection( local_file_service_keys ), key = CG.client_controller.services_manager.GetName )
            
            for file_service_key in local_file_service_keys_we_are_in:
                
                ClientGUIMenus.AppendMenuItem( menu, 'delete from {}'.format( CG.client_controller.services_manager.GetName( file_service_key ) ), 'Delete this file.', self._Delete, file_service_key = file_service_key )
                
            
            if locations_manager.IsTrashed():
                
                ClientGUIMenus.AppendMenuItem( menu, 'delete completely', 'Physically delete this file from disk.', self._Delete, file_service_key = CC.COMBINED_LOCAL_FILE_SERVICE_KEY )
                ClientGUIMenus.AppendMenuItem( menu, 'undelete', 'Take this file out of the trash.', self._Undelete )
                
            
            ClientGUIMenus.AppendSeparator( menu )
            
            manage_menu = ClientGUIMenus.GenerateMenu( menu )
            
            ClientGUIMenus.AppendMenuItem( manage_menu, 'tags', 'Manage this file\'s tags.', self._ManageTags )
            
            if i_can_post_ratings:
                
                ClientGUIMenus.AppendMenuItem( manage_menu, 'ratings', 'Manage this file\'s ratings.', self._ManageRatings )
                
            
            ClientGUIMenus.AppendMenuItem( manage_menu, 'urls', 'Manage this file\'s known URLs.', self._ManageURLs )
            
            num_notes = self._current_media.GetNotesManager().GetNumNotes()
            
            notes_str = 'notes'
            
            if num_notes > 0:
                
                notes_str = '{} ({})'.format( notes_str, HydrusData.ToHumanInt( num_notes ) )
                
            
            ClientGUIMenus.AppendMenuItem( manage_menu, notes_str, 'Manage this file\'s notes.', self._ManageNotes )
            
            ClientGUIMenus.AppendMenuItem( manage_menu, 'times', 'Edit the timestamps for your files.', self._ManageTimestamps )
            ClientGUIMenus.AppendMenuItem( manage_menu, 'force filetype', 'Force your files to appear as a different filetype.', ClientGUIMediaActions.SetFilesForcedFiletypes, self, [ self._current_media ] )
            
            ClientGUIMediaMenus.AddManageFileViewingStatsMenu( self, manage_menu, [ self._current_media ] )
            
            ClientGUIMenus.AppendMenu( menu, manage_menu, 'manage' )
            
            ClientGUIMediaMenus.AddKnownURLsViewCopyMenu( self, menu, self._current_media )
            
            open_menu = ClientGUIMenus.GenerateMenu( menu )
            
            ClientGUIMenus.AppendMenuItem( open_menu, 'in external program', 'Open this file in your OS\'s default program.', self._OpenExternally )
            ClientGUIMenus.AppendMenuItem( open_menu, 'in a new page', 'Show your current media in a simple new page.', self._ShowMediaInNewPage )
            ClientGUIMenus.AppendMenuItem( open_menu, 'in web browser', 'Show this file in your OS\'s web browser.', self._OpenFileInWebBrowser )
            
            show_open_in_explorer = advanced_mode and ( HC.PLATFORM_WINDOWS or HC.PLATFORM_MACOS )
            
            if show_open_in_explorer:
                
                ClientGUIMenus.AppendMenuItem( open_menu, 'in file browser', 'Show this file in your OS\'s file browser.', self._OpenFileLocation )
                
            
            ClientGUIMenus.AppendMenu( menu, open_menu, 'open' )
            
            share_menu = ClientGUIMenus.GenerateMenu( menu )
            
            copy_menu = ClientGUIMenus.GenerateMenu( share_menu )

            ClientGUIMenus.AppendMenuItem( copy_menu, 'file', 'Copy this file to your clipboard.', self._CopyFileToClipboard )
            
            copy_hash_menu = ClientGUIMenus.GenerateMenu( copy_menu )

            ClientGUIMenus.AppendMenuItem( copy_hash_menu, 'sha256 ({})'.format( self._current_media.GetHash().hex() ), 'Copy this file\'s SHA256 hash.', self._CopyHashToClipboard, 'sha256' )
            ClientGUIMenus.AppendMenuItem( copy_hash_menu, 'md5', 'Copy this file\'s MD5 hash.', self._CopyHashToClipboard, 'md5' )
            ClientGUIMenus.AppendMenuItem( copy_hash_menu, 'sha1', 'Copy this file\'s SHA1 hash.', self._CopyHashToClipboard, 'sha1' )
            ClientGUIMenus.AppendMenuItem( copy_hash_menu, 'sha512', 'Copy this file\'s SHA512 hash.', self._CopyHashToClipboard, 'sha512' )
            
            file_info_manager = self._current_media.GetFileInfoManager()
            
            if file_info_manager.blurhash is not None:
                
                ClientGUIMenus.AppendMenuItem( copy_hash_menu, f'blurhash ({file_info_manager.blurhash})', 'Copy this file\'s blurhash.', self._CopyHashToClipboard, 'blurhash' )
                
            
            if file_info_manager.pixel_hash is not None:
                
                ClientGUIMenus.AppendMenuItem( copy_hash_menu, f'pixel ({file_info_manager.pixel_hash.hex()})', 'Copy this file\'s pixel hash.', self._CopyHashToClipboard, 'pixel_hash' )
                
            
            ClientGUIMenus.AppendMenu( copy_menu, copy_hash_menu, 'hash' )
            
            if advanced_mode:
                
                hash_id_str = str( self._current_media.GetHashId() )
                
                ClientGUIMenus.AppendMenuItem( copy_menu, 'file_id ({})'.format( hash_id_str ), 'Copy this file\'s internal file/hash_id.', CG.client_controller.pub, 'clipboard', 'text', hash_id_str )
                
            
            if self._current_media.IsStaticImage():
                
                ClientGUIMenus.AppendMenuItem( copy_menu, 'bitmap', 'Copy this file to your clipboard as a bitmap.', self._CopyBMPToClipboard )

                ( width, height ) = self._current_media.GetResolution()
                
                if width is not None and height is not None and ( width > 1024 or height > 1024 ):
                    
                    target_resolution = HydrusImageHandling.GetThumbnailResolution( self._current_media.GetResolution(), ( 1024, 1024 ), HydrusImageHandling.THUMBNAIL_SCALE_TO_FIT, 100 )
                    
                    ClientGUIMenus.AppendMenuItem( copy_menu, 'source lookup bitmap ({}x{})'.format( target_resolution[0], target_resolution[1] ), 'Copy a smaller bitmap of this file, for quicker lookup on source-finding websites.', self._CopyBMPToClipboard, target_resolution )
                    
                

            ClientGUIMenus.AppendMenuItem( copy_menu, 'path', 'Copy this file\'s path to your clipboard.', self._CopyPathToClipboard )
            
            ClientGUIMenus.AppendMenu( share_menu, copy_menu, 'copy' )
            
            ClientGUIMenus.AppendMenu( menu, share_menu, 'share' )
            
        
        CGC.core().PopupMenu( self, menu )
        
    
    def LaunchMediaViewer( self ):
        
        CG.client_controller.pub( 'launch_media_viewer', self._page_key )
        
    
    def MediaFocusWentToExternalProgram( self, page_key ):
        
        if page_key == self._page_key:
            
            self._MediaFocusWentToExternalProgram()
            
        
    
    def ProcessContentUpdatePackage( self, content_update_package: ClientContentUpdates.ContentUpdatePackage ):
        
        if self._current_media is not None:
            
            my_hash = self._current_media.GetHash()
            
            do_redraw = False
            
            for ( service_key, content_updates ) in content_update_package.IterateContentUpdates():
                
                if True in ( my_hash in content_update.GetHashes() for content_update in content_updates ):
                    
                    do_redraw = True
                    
                    break
                    
                
            
            if do_redraw:
                
                self.update()
                
            
        
    
    def SetMedia( self, media ):
        
        if HC.options[ 'hide_preview' ]:
            
            return
            
        
        Canvas.SetMedia( self, media )
        
    
class CanvasWithDetails( Canvas ):
    
    def __init__( self, parent, location_context ):
        
        Canvas.__init__( self, parent, location_context )
        
        CG.client_controller.sub( self, 'RedrawDetails', 'refresh_all_tag_presentation_gui' )
        
    
    def _DrawAdditionalTopMiddleInfo( self, painter: QG.QPainter, current_y ):
        
        pass
        
    
    def _DrawBackgroundDetails( self, painter: QG.QPainter ):
        
        my_size = self.size()
        
        my_width = my_size.width()
        my_height = my_size.height()
        
        if self._current_media is None:
            
            text = self._GetNoMediaText()
            
            ( text_size, text ) = ClientGUIFunctions.GetTextSizeFromPainter( painter, text )
            
            x = ( my_width - text_size.width() ) // 2
            y = ( my_height - text_size.height() ) // 2
            
            ClientGUIFunctions.DrawText( painter, x, y, text )
            
        else:
            
            self._DrawTags( painter )
            
            self._DrawTopMiddle( painter )
            
            current_y = self._DrawTopRight( painter )
            
            self._DrawNotes( painter, current_y )
            
            self._DrawIndexAndZoom( painter )
            
        
    
    def _DrawIndexAndZoom( self, painter: QG.QPainter ):
        
        my_size = self.size()
        
        my_width = my_size.width()
        my_height = my_size.height()
        
        # bottom-right index
        
        bottom_right_string = ClientData.ConvertZoomToPercentage( self._media_container.GetCurrentZoom() )
        
        index_string = self._GetIndexString()
        
        if len( index_string ) > 0:
            
            bottom_right_string = '{} - {}'.format( bottom_right_string, index_string )
            
        
        ( text_size, bottom_right_string ) = ClientGUIFunctions.GetTextSizeFromPainter( painter, bottom_right_string )
        
        ClientGUIFunctions.DrawText( painter, my_width - text_size.width() - 3, my_height - text_size.height() - 3, bottom_right_string )
        
    
    def _DrawNotes( self, painter: QG.QPainter, current_y: int ):
        
        notes_manager = self._current_media.GetNotesManager()
        
        names_to_notes = notes_manager.GetNamesToNotes()
        
        if len( names_to_notes ) == 0:
            
            return
            
        
        my_size = self.size()
        
        my_width = my_size.width()
        my_height = my_size.height()
        
        max_notes_width_percentage = 20
        
        PADDING = 4
        
        max_notes_width = int( my_width * ( max_notes_width_percentage / 100 ) ) - ( PADDING * 2 )
        
        notes_width = 0
        
        original_font = painter.font()
        
        name_font = QG.QFont( original_font )
        name_font.setBold( True )
        
        notes_font = QG.QFont( original_font )
        notes_font.setBold( False )
        
        for ( name, note ) in names_to_notes.items():
            
            # without wrapping, let's see if we fit into a smaller box than the max possible
            
            painter.setFont( name_font )
            
            name_text_size = painter.fontMetrics().size( 0, name )
            
            painter.setFont( notes_font )
            
            note_text_size = painter.fontMetrics().size( 0, note )
            
            notes_width = max( notes_width, name_text_size.width(), note_text_size.width() )
            
            if notes_width > max_notes_width:
                
                notes_width = max_notes_width
                
                break
                
            
        
        left_x = my_width - ( notes_width + PADDING )
        
        current_y += PADDING * 2
        
        draw_a_test_rect = False
        
        if draw_a_test_rect:
            
            painter.setPen( QG.QPen( QG.QColor( 20, 20, 20 ) ) )
            painter.setBrush( QC.Qt.NoBrush )
            
            painter.drawRect( left_x, current_y, notes_width, 100 )
            
        
        for name in sorted( names_to_notes.keys() ):
            
            painter.setFont( name_font )
            
            text_rect = painter.fontMetrics().boundingRect( left_x, current_y, notes_width, 100, QC.Qt.AlignHCenter | QC.Qt.TextWordWrap, name )
            
            painter.drawText( text_rect, QC.Qt.AlignHCenter | QC.Qt.TextWordWrap, name )
            
            current_y += text_rect.height() + PADDING
            
            #
            
            painter.setFont( notes_font )
            
            note = notes_manager.GetNote( name )
            
            text_rect = painter.fontMetrics().boundingRect( left_x, current_y, notes_width, 100, QC.Qt.AlignJustify | QC.Qt.TextWordWrap, note )
            
            painter.drawText( text_rect, QC.Qt.AlignJustify | QC.Qt.TextWordWrap, note )
            
            current_y += text_rect.height() + PADDING
            
            if current_y >= my_height:
                
                break
                
            
            # draw a horizontal line
            
            
        
        painter.setFont( original_font )
        
    
    def _DrawTags( self, painter: QG.QPainter ):
        
        # tags on the top left
        
        original_pen = painter.pen()
        
        tags_manager = self._current_media.GetTagsManager()
        
        current = tags_manager.GetCurrent( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_SINGLE_MEDIA )
        pending = tags_manager.GetPending( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_SINGLE_MEDIA )
        petitioned = tags_manager.GetPetitioned( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_SINGLE_MEDIA )
        
        tags_i_want_to_display = set()
        
        tags_i_want_to_display.update( current )
        tags_i_want_to_display.update( pending )
        tags_i_want_to_display.update( petitioned )
        
        tags_i_want_to_display = list( tags_i_want_to_display )
        
        tag_sort = CG.client_controller.new_options.GetDefaultTagSort()
        
        ClientTagSorting.SortTags( tag_sort, tags_i_want_to_display )
        
        current_y = 3
        
        namespace_colours = HC.options[ 'namespace_colours' ]
        
        for tag in tags_i_want_to_display:
            
            display_string = ClientTags.RenderTag( tag, True )
            
            if tag in pending:
                
                display_string += ' (+)'
                
            
            if tag in petitioned:
                
                display_string += ' (-)'
                
            
            ( namespace, subtag ) = HydrusTags.SplitTag( tag )
            
            if namespace in namespace_colours:
                
                ( r, g, b ) = namespace_colours[ namespace ]
                
            else:
                
                ( r, g, b ) = namespace_colours[ None ]
                
            
            painter.setPen( QG.QPen( QG.QColor( r, g, b ) ) )
            
            ( text_size, display_string ) = ClientGUIFunctions.GetTextSizeFromPainter( painter, display_string )
            
            ClientGUIFunctions.DrawText( painter, 5, current_y, display_string )
            
            current_y += text_size.height()
            
        
        painter.setPen( original_pen )
        
    
    def _DrawTopMiddle( self, painter: QG.QPainter ):
        
        my_size = self.size()
        
        my_width = my_size.width()
        my_height = my_size.height()
        
        # top-middle
        
        painter.setPen( QG.QPen( self._new_options.GetColour( CC.COLOUR_MEDIA_TEXT ) ) )
        
        current_y = 3
        
        title_string = self._current_media.GetTitleString()
        
        if len( title_string ) > 0:
            
            ( text_size, title_string ) = ClientGUIFunctions.GetTextSizeFromPainter( painter, title_string )
            
            ClientGUIFunctions.DrawText( painter, ( my_width - text_size.width() ) // 2, current_y, title_string )
            
            current_y += text_size.height() + 3
            
        
        info_string = self._GetInfoString()
        
        ( text_size, info_string ) = ClientGUIFunctions.GetTextSizeFromPainter( painter, info_string )
        
        ClientGUIFunctions.DrawText( painter, ( my_width - text_size.width() ) // 2, current_y, info_string )
        
        current_y += text_size.height() + 3
        
        self._DrawAdditionalTopMiddleInfo( painter, current_y )
        
    
    def _DrawTopRight( self, painter: QG.QPainter ) -> int:
        
        my_size = self.size()
        
        my_width = my_size.width()
        my_height = my_size.height()
        
        current_y = 2
        
        # ratings
        
        services_manager = CG.client_controller.services_manager
        
        like_services = services_manager.GetServices( ( HC.LOCAL_RATING_LIKE, ) )
        
        like_services.reverse()
        
        like_rating_current_x = my_width - 16 - 2 # -2 to line up exactly with the floating panel
        
        for like_service in like_services:
            
            service_key = like_service.GetServiceKey()
            
            rating_state = ClientRatings.GetLikeStateFromMedia( ( self._current_media, ), service_key )
            
            ClientGUIRatings.DrawLike( painter, like_rating_current_x, current_y, service_key, rating_state )
            
            like_rating_current_x -= 16
            
        
        if len( like_services ) > 0:
            
            current_y += 18
            
        
        numerical_services = services_manager.GetServices( ( HC.LOCAL_RATING_NUMERICAL, ) )
        
        for numerical_service in numerical_services:
            
            service_key = numerical_service.GetServiceKey()
            
            ( rating_state, rating ) = ClientRatings.GetNumericalStateFromMedia( ( self._current_media, ), service_key )
            
            numerical_width = ClientGUIRatings.GetNumericalWidth( service_key )
            
            ClientGUIRatings.DrawNumerical( painter, my_width - numerical_width - 2, current_y, service_key, rating_state, rating ) # -2 to line up exactly with the floating panel
            
            current_y += 18
            
        
        incdec_services = services_manager.GetServices( ( HC.LOCAL_RATING_INCDEC, ) )
        
        incdec_services.reverse()
        
        control_width = ClientGUIRatings.INCDEC_SIZE.width()
        
        incdec_rating_current_x = my_width - control_width - 2 # -2 to line up exactly with the floating panel
        
        for incdec_service in incdec_services:
            
            service_key = incdec_service.GetServiceKey()
            
            ( rating_state, rating ) = ClientRatings.GetIncDecStateFromMedia( ( self._current_media, ), service_key )
            
            ClientGUIRatings.DrawIncDec( painter, incdec_rating_current_x, current_y, service_key, rating_state, rating )
            
            incdec_rating_current_x -= control_width
            
        
        if len( incdec_services ) > 0:
            
            current_y += 18
            
        
        # icons
        
        icons_to_show = []
        
        if self._current_media.GetLocationsManager().IsTrashed():
            
            icons_to_show.append( CC.global_pixmaps().trash )
            
        
        if self._current_media.HasInbox():
            
            icons_to_show.append( CC.global_pixmaps().inbox )
            
        
        if len( icons_to_show ) > 0:
            
            icon_x = 0
            
            for icon in icons_to_show:
                
                painter.drawPixmap( my_width + icon_x - 18, current_y, icon )
                
                icon_x -= 18
                
            
            current_y += 18
            
        
        painter.setPen( QG.QPen( self._new_options.GetColour( CC.COLOUR_MEDIA_TEXT ) ) )
        
        # repo strings
        
        remote_strings = self._current_media.GetLocationsManager().GetRemoteLocationStrings()
        
        for remote_string in remote_strings:
            
            ( text_size, remote_string ) = ClientGUIFunctions.GetTextSizeFromPainter( painter, remote_string )
            
            ClientGUIFunctions.DrawText( painter, my_width - text_size.width() - 3, current_y, remote_string )
            
            current_y += text_size.height()
            
        
        # urls
        
        urls = self._current_media.GetLocationsManager().GetURLs()
        
        url_tuples = CG.client_controller.network_engine.domain_manager.ConvertURLsToMediaViewerTuples( urls )
        
        for ( display_string, url ) in url_tuples:
            
            ( text_size, display_string ) = ClientGUIFunctions.GetTextSizeFromPainter( painter, display_string )
            
            ClientGUIFunctions.DrawText( painter, my_width - text_size.width() - 3, current_y, display_string )
            
            current_y += text_size.height() + 2
            
        
        return current_y
        
    
    def _GetInfoString( self ):
        
        lines = [ line for line in self._current_media.GetPrettyInfoLines( only_interesting_lines = True ) if isinstance( line, str ) ]
        
        lines.insert( 1, ClientData.ConvertZoomToPercentage( self._media_container.GetCurrentZoom() ) )
        
        info_string = ' | '.join( lines )
        
        return info_string
        
    
    def _GetNoMediaText( self ):
        
        return 'No media to display'
        
    
    def RedrawDetails( self ):
        
        self.update()
        
    
    def TryToDoPreClose( self ):
        
        can_close = True
        
        return can_close
        
    
class CanvasWithHovers( CanvasWithDetails ):
    
    def __init__( self, parent, location_context ):
        
        CanvasWithDetails.__init__( self, parent, location_context )
        
        self._hovers = []
        
        top_hover = self._GenerateHoverTopFrame()
        
        top_hover.sendApplicationCommand.connect( self.ProcessApplicationCommand )
        
        self._media_container.zoomChanged.connect( top_hover.SetCurrentZoom )
        
        self._hovers.append( top_hover )
        
        self._my_shortcuts_handler.AddWindowToFilter( top_hover )
        
        tags_hover = ClientGUICanvasHoverFrames.CanvasHoverFrameTags( self, self, top_hover, self._canvas_key )
        
        tags_hover.sendApplicationCommand.connect( self.ProcessApplicationCommand )
        
        self._hovers.append( tags_hover )
        
        self._my_shortcuts_handler.AddWindowToFilter( tags_hover )
        
        top_right_hover = ClientGUICanvasHoverFrames.CanvasHoverFrameTopRight( self, self, top_hover, self._canvas_key )
        
        top_right_hover.sendApplicationCommand.connect( self.ProcessApplicationCommand )
        
        self._hovers.append( top_right_hover )
        
        self._my_shortcuts_handler.AddWindowToFilter( top_right_hover )
        
        self._right_notes_hover = ClientGUICanvasHoverFrames.CanvasHoverFrameRightNotes( self, self, top_right_hover, self._canvas_key )
        
        self._right_notes_hover.sendApplicationCommand.connect( self.ProcessApplicationCommand )
        
        self._hovers.append( self._right_notes_hover )
        
        self._my_shortcuts_handler.AddWindowToFilter( self._right_notes_hover )
        
        for name in self._new_options.GetStringList( 'default_media_viewer_custom_shortcuts' ):
            
            self._my_shortcuts_handler.AddShortcuts( name )
            
        
        #
        
        self._timer_cursor_hide_job = None
        self._last_cursor_autohide_touch_time = HydrusTime.GetNowFloat()
        
        # need this as we need un-button-pressed move events for cursor hide
        self.setMouseTracking( True )
        
        self._RestartCursorHideWait()
        
        CG.client_controller.sub( self, 'CloseFromHover', 'canvas_close' )
        CG.client_controller.sub( self, 'FullscreenSwitch', 'canvas_fullscreen_switch' )
        
        CG.client_controller.gui.RegisterUIUpdateWindow( self )
        
    
    def _GenerateHoverTopFrame( self ):
        
        raise NotImplementedError()
        
    
    def _HideCursorCheck( self ):
        
        hide_time_ms = CG.client_controller.new_options.GetNoneableInteger( 'media_viewer_cursor_autohide_time_ms' )
        
        if hide_time_ms is None:
            
            return
            
        
        hide_time = hide_time_ms / 1000
        
        can_hide = HydrusTime.TimeHasPassedFloat( self._last_cursor_autohide_touch_time + hide_time )
        
        can_check_again = ClientGUIFunctions.MouseIsOverWidget( self )
        
        if not CC.CAN_HIDE_MOUSE:
            
            can_hide = False
            
        
        if CGC.core().MenuIsOpen():
            
            can_hide = False
            
        
        if ClientGUIFunctions.DialogIsOpen():
            
            can_hide = False
            
            can_check_again = False
            
        
        if can_hide:
            
            self.setCursor( QG.QCursor( QC.Qt.BlankCursor ) )
            
        elif can_check_again:
            
            self._RestartCursorHideCheckJob()
            
        
    
    def _RestartCursorHideWait( self ):
        
        self._last_cursor_autohide_touch_time = HydrusTime.GetNowFloat()
        
        self._RestartCursorHideCheckJob()
        
    
    def _RestartCursorHideCheckJob( self ):
        
        if self._timer_cursor_hide_job is not None:
            
            timer_is_running_or_finished = self._timer_cursor_hide_job.CurrentlyWorking() or self._timer_cursor_hide_job.IsWorkComplete()
            
            if not timer_is_running_or_finished:
                
                return
                
            
        
        self._timer_cursor_hide_job = CG.client_controller.CallLaterQtSafe( self, 0.1, 'hide cursor check', self._HideCursorCheck )
        
    
    def _TryToCloseWindow( self ):
        
        self.window().close()
        
    
    def CleanBeforeDestroy( self ):
        
        self.setCursor( QG.QCursor( QC.Qt.ArrowCursor ) )
        
        CanvasWithDetails.CleanBeforeDestroy( self )
        
    
    def CloseFromHover( self, canvas_key ):
        
        if canvas_key == self._canvas_key:
            
            self._TryToCloseWindow()
            
        
    
    def FullscreenSwitch( self, canvas_key ):
        
        if canvas_key == self._canvas_key:
            
            self.parentWidget().FullscreenSwitch()
            
        
    
    def mouseMoveEvent( self, event ):
        
        current_focus_tlw = QW.QApplication.activeWindow()
        
        my_tlw = self.window()
        
        if isinstance( current_focus_tlw, ClientGUICanvasHoverFrames.CanvasHoverFrame ) and ClientGUIFunctions.IsQtAncestor( current_focus_tlw, my_tlw, through_tlws = True ):
            
            my_tlw.activateWindow()
            
        
        #
        
        CC.CAN_HIDE_MOUSE = True
        
        # due to the mouse setPos below, the event pos can get funky I think due to out of order coordinate setting events, so we'll poll current value directly
        event_pos = self.mapFromGlobal( QG.QCursor.pos() )
        
        mouse_currently_shown = self.cursor().shape() == QC.Qt.ArrowCursor
        show_mouse = mouse_currently_shown
        
        is_dragging = event.buttons() & QC.Qt.LeftButton and self._last_drag_pos is not None
        has_moved = event_pos != self._last_motion_pos
        
        if is_dragging:
            
            delta = event_pos - self._last_drag_pos
            
            approx_distance = delta.manhattanLength()
            
            if approx_distance > 0:
                
                touchscreen_canvas_drags_unanchor = CG.client_controller.new_options.GetBoolean( 'touchscreen_canvas_drags_unanchor' )
                
                if not self._current_drag_is_touch and approx_distance > 50:
                    
                    # if user is able to generate such a large distance, they are almost certainly touching
                    
                    self._current_drag_is_touch = True
                    
                
                # touch events obviously don't mix with warping well. the touch just warps it back and again and we get a massive delta!
                
                touch_anchor_override = touchscreen_canvas_drags_unanchor and self._current_drag_is_touch
                anchor_and_hide_canvas_drags = CG.client_controller.new_options.GetBoolean( 'anchor_and_hide_canvas_drags' )
                
                if anchor_and_hide_canvas_drags and not touch_anchor_override:
                    
                    show_mouse = False
                    
                    global_mouse_pos = self.mapToGlobal( self._last_drag_pos )
                    
                    QG.QCursor.setPos( global_mouse_pos )
                    
                    ClientGUIShortcuts.CUMULATIVE_MOUSEWARP_MANHATTAN_LENGTH += approx_distance
                    
                else:
                    
                    show_mouse = True
                    
                    self._last_drag_pos = QC.QPoint( event_pos )
                    
                
                self._media_container.MoveDelta( delta )
                
            
        else:
            
            if has_moved:
                
                self._last_motion_pos = QC.QPoint( event_pos )
                
                show_mouse = True
                
            
        
        if show_mouse:
            
            if not mouse_currently_shown:
                
                self.setCursor( QG.QCursor( QC.Qt.ArrowCursor ) )
                
            
            self._RestartCursorHideWait()
            
        else:
            
            if mouse_currently_shown:
                
                self.setCursor( QG.QCursor( QC.Qt.BlankCursor ) )
                
            
        
        CanvasWithDetails.mouseMoveEvent( self, event )
        
    
    def ProcessApplicationCommand( self, command: CAC.ApplicationCommand ):
        
        command_processed = True
        
        if command.IsSimpleCommand():
            
            action = command.GetSimpleAction()
            
            if action == CAC.SIMPLE_CLOSE_MEDIA_VIEWER:
                
                self._TryToCloseWindow()
                
            else:
                
                command_processed = False
                
            
        else:
            
            command_processed = False
            
        
        if not command_processed:
            
            command_processed = CanvasWithDetails.ProcessApplicationCommand( self, command )
            
        
        return command_processed
        
    
    def TIMERUIUpdate( self ):
        
        for hover in self._hovers:
            
            hover.DoRegularHideShow()
            
        
class CanvasFilterDuplicates( CanvasWithHovers ):
    
    CANVAS_TYPE = CC.CANVAS_MEDIA_VIEWER_DUPLICATES
    
    showPairInPage = QC.Signal( list )
    
    def __init__( self, parent, file_search_context_1: ClientSearch.FileSearchContext, file_search_context_2: ClientSearch.FileSearchContext, dupe_search_type, pixel_dupes_preference, max_hamming_distance ):
        
        location_context = file_search_context_1.GetLocationContext()
        
        CanvasWithHovers.__init__( self, parent, location_context )
        
        self._duplicates_right_hover = ClientGUICanvasHoverFrames.CanvasHoverFrameRightDuplicates( self, self, self._canvas_key )
        
        self._right_notes_hover.AddHoverThatCanBeOnTop( self._duplicates_right_hover )
        
        self._duplicates_right_hover.showPairInPage.connect( self._ShowPairInPage )
        self._duplicates_right_hover.sendApplicationCommand.connect( self.ProcessApplicationCommand )
        
        self._hovers.append( self._duplicates_right_hover )
        
        self._background_colour_generator = CanvasBackgroundColourGeneratorDuplicates( self )
        
        self._media_container.SetBackgroundColourGenerator( self._background_colour_generator )
        
        self._my_shortcuts_handler.AddWindowToFilter( self._duplicates_right_hover )
        
        self._file_search_context_1 = file_search_context_1
        self._file_search_context_2 = file_search_context_2
        self._dupe_search_type = dupe_search_type
        self._pixel_dupes_preference = pixel_dupes_preference
        self._max_hamming_distance = max_hamming_distance
        
        self._maintain_pan_and_zoom = True
        
        self._currently_fetching_pairs = False
        
        self._batch_of_pairs_to_process = []
        self._current_pair_index = 0
        self._processed_pairs = []
        self._hashes_due_to_be_deleted_in_this_batch = set()
        
        # ok we started excluding pairs if they had been deleted, now I am extending it to any files that have been processed.
        # main thing is if you have AB, AC, that's neat and a bunch of people want it, but current processing system doesn't do B->A->C merge if it happens in a single batch
        # I need to store dupe merge options rather than content updates apply them in db transaction or do the retroactive sync or similar to get this done properly
        # so regrettably I turn it off for now
        
        self._hashes_processed_in_this_batch = set()
        
        self._media_list = ClientMedia.ListeningMediaList( location_context, [] )
        
        self._my_shortcuts_handler.AddShortcuts( 'media_viewer_browser' )
        self._my_shortcuts_handler.AddShortcuts( 'duplicate_filter' )
        
        CG.client_controller.sub( self, 'ProcessContentUpdatePackage', 'content_updates_gui' )
        CG.client_controller.sub( self, 'Delete', 'canvas_delete' )
        CG.client_controller.sub( self, 'Undelete', 'canvas_undelete' )
        CG.client_controller.sub( self, 'SwitchMedia', 'canvas_show_next' )
        CG.client_controller.sub( self, 'SwitchMedia', 'canvas_show_previous' )
        
        QP.CallAfter( self._LoadNextBatchOfPairs )
        
    
    def _CommitProcessed( self, blocking = True ):
        
        pair_info = []
        
        for ( duplicate_type, first_media, second_media, content_update_packages, was_auto_skipped ) in self._processed_pairs:
            
            if duplicate_type is None:
                
                if len( content_update_packages ) > 0:
                    
                    for content_update_package in content_update_packages:
                        
                        if blocking:
                            
                            CG.client_controller.WriteSynchronous( 'content_updates', content_update_package )
                            
                        else:
                            
                            CG.client_controller.Write( 'content_updates', content_update_package )
                            
                        
                    
                
                continue
                
            
            if was_auto_skipped:
                
                continue # it was a 'skip' decision
                
            
            first_hash = first_media.GetHash()
            second_hash = second_media.GetHash()
            
            pair_info.append( ( duplicate_type, first_hash, second_hash, content_update_packages ) )
            
        
        if len( pair_info ) > 0:
            
            if blocking:
                
                CG.client_controller.WriteSynchronous( 'duplicate_pair_status', pair_info )
                
            else:
                
                CG.client_controller.Write( 'duplicate_pair_status', pair_info )
                
            
        
        self._processed_pairs = []
        self._hashes_due_to_be_deleted_in_this_batch = set()
        self._hashes_processed_in_this_batch = set()
        
    
    def _CurrentMediaIsBetter( self, delete_second = True ):
        
        self._ProcessPair( HC.DUPLICATE_BETTER, delete_second = delete_second )
        
    
    def _Delete( self, media = None, reason = None, file_service_key = None ):
        
        if self._current_media is None:
            
            return False
            
        
        first_media = self._current_media
        second_media = self._media_list.GetNext( self._current_media )
        
        message = 'Delete just this file, or both?'
        
        yes_tuples = []
        
        yes_tuples.append( ( 'delete just this one', 'current' ) )
        yes_tuples.append( ( 'delete both', 'both' ) )
        
        try:
            
            result = ClientGUIDialogsQuick.GetYesYesNo( self, message, yes_tuples = yes_tuples, no_label = 'forget it' )
            
        except HydrusExceptions.CancelledException:
            
            return False
            
        
        if result == 'current':
            
            media = [ first_media ]
            
            default_reason = 'Deleted manually in Duplicate Filter.'
            
        elif result == 'both':
            
            media = [ first_media, second_media ]
            
            default_reason = 'Deleted manually in Duplicate Filter, along with its potential duplicate.'
            
        
        content_update_packages = CanvasWithHovers._Delete( self, media = media, default_reason = default_reason, file_service_key = file_service_key, just_get_content_update_packages = True )
        
        deleted = isinstance( content_update_packages, list ) and len( content_update_packages ) > 0
        
        if deleted:
            
            for m in media:
                
                self._hashes_due_to_be_deleted_in_this_batch.update( m.GetHashes() )
                
            
            was_auto_skipped = False
            
            ( first_media_result, second_media_result ) = self._batch_of_pairs_to_process[ self._current_pair_index ]
            
            first_media = ClientMedia.MediaSingleton( first_media_result )
            second_media = ClientMedia.MediaSingleton( second_media_result )
            
            process_tuple = ( None, first_media, second_media, content_update_packages, was_auto_skipped )
            
            self._ShowNextPair( process_tuple )
            
        
        return deleted
        
    
    def _DoCustomAction( self ):
        
        if self._current_media is None:
            
            return
            
        
        duplicate_types = [ HC.DUPLICATE_BETTER, HC.DUPLICATE_SAME_QUALITY, HC.DUPLICATE_ALTERNATE, HC.DUPLICATE_FALSE_POSITIVE ]
        
        choice_tuples = [ ( HC.duplicate_type_string_lookup[ duplicate_type ], duplicate_type ) for duplicate_type in duplicate_types ]
        
        try:
            
            duplicate_type = ClientGUIDialogsQuick.SelectFromList( self, 'select duplicate type', choice_tuples )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        new_options = CG.client_controller.new_options
        
        if duplicate_type in [ HC.DUPLICATE_BETTER, HC.DUPLICATE_SAME_QUALITY ] or ( new_options.GetBoolean( 'advanced_mode' ) and duplicate_type == HC.DUPLICATE_ALTERNATE ):
            
            duplicate_content_merge_options = new_options.GetDuplicateContentMergeOptions( duplicate_type )
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit duplicate merge options' ) as dlg_2:
                
                panel = ClientGUIScrolledPanelsEdit.EditDuplicateContentMergeOptionsPanel( dlg_2, duplicate_type, duplicate_content_merge_options, for_custom_action = True )
                
                dlg_2.SetPanel( panel )
                
                if dlg_2.exec() == QW.QDialog.Accepted:
                    
                    duplicate_content_merge_options = panel.GetValue()
                    
                else:
                    
                    return
                    
                
            
        else:
            
            duplicate_content_merge_options = None
            
        
        message = 'Delete any of the files?'
        
        yes_tuples = []
        
        yes_tuples.append( ( 'delete neither', 'delete_neither' ) )
        yes_tuples.append( ( 'delete this one', 'delete_first' ) )
        yes_tuples.append( ( 'delete the other', 'delete_second' ) )
        yes_tuples.append( ( 'delete both', 'delete_both' ) )
        
        try:
            
            result = ClientGUIDialogsQuick.GetYesYesNo( self, message, yes_tuples = yes_tuples, no_label = 'forget it' )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        delete_first = False
        delete_second = False
        
        if result == 'delete_first':
            
            delete_first = True
            
        elif result == 'delete_second':
            
            delete_second = True
            
        elif result == 'delete_both':
            
            delete_first = True
            delete_second = True
            
        
        self._ProcessPair( duplicate_type, delete_first = delete_first, delete_second = delete_second, duplicate_content_merge_options = duplicate_content_merge_options )
        
    
    def _DrawBackgroundDetails( self, painter ):
        
        if self._currently_fetching_pairs:
            
            text = 'Loading pairs' + HC.UNICODE_ELLIPSIS
            
            ( text_size, text ) = ClientGUIFunctions.GetTextSizeFromPainter( painter, text )
            
            my_size = self.size()
            
            x = ( my_size.width() - text_size.width() ) // 2
            y = ( my_size.height() - text_size.height() ) // 2
            
            ClientGUIFunctions.DrawText( painter, x, y, text )
            
        else:
            
            CanvasWithHovers._DrawBackgroundDetails( self, painter )
            
        
    
    def _GenerateHoverTopFrame( self ):
        
        return ClientGUICanvasHoverFrames.CanvasHoverFrameTopDuplicatesFilter( self, self, self._canvas_key )
        
    
    def _GetIndexString( self ):
        
        if self._current_media is None or len( self._media_list ) == 0:
            
            return '-'
            
        else:
            
            current_media_label = 'A' if self._current_media == self._media_list.GetFirst() else 'B'
            
            progress = self._current_pair_index + 1
            total = len( self._batch_of_pairs_to_process )
            
            index_string = HydrusData.ConvertValueRangeToPrettyString( progress, total )
            
            num_committable = self._GetNumCommittableDecisions()
            num_deletable = self._GetNumCommittableDeletes()
            
            components = []
            
            if num_committable > 0:
                
                components.append( '{} decisions'.format( HydrusData.ToHumanInt( num_committable ) ) )
                
            
            if num_deletable > 0:
                
                components.append( '{} deletes'.format( HydrusData.ToHumanInt( num_deletable ) ) )
                
            
            if len( components ) == 0:
                
                num_decisions_string = 'no decisions yet'
                
            else:
                
                num_decisions_string = ', '.join( components )
                
            
            return '{} - {} - {}'.format( current_media_label, index_string, num_decisions_string )
            
        
    
    def _GetNoMediaText( self ):
        
        return 'Looking for pairs to compare--please wait.'
        
    
    def _GetNumCommittableDecisions( self ):
        
        return len( [ 1 for ( duplicate_type, first_media, second_media, content_update_packages, was_auto_skipped ) in self._processed_pairs if duplicate_type is not None ] )
        
    
    def _GetNumCommittableDeletes( self ):
        
        return len( [ 1 for ( duplicate_type, first_media, second_media, content_update_packages, was_auto_skipped ) in self._processed_pairs if duplicate_type is None and len( content_update_packages ) > 0 ] )
        
    
    def _GetNumRemainingDecisions( self ):
        
        # this looks a little weird, but I want to be clear that we make a decision on the final index
        
        last_decision_index = len( self._batch_of_pairs_to_process ) - 1
        
        number_of_decisions_after_the_current = last_decision_index - self._current_pair_index
        
        return max( 0, 1 + number_of_decisions_after_the_current )
        
    
    def _GoBack( self ):
        
        if self._current_pair_index > 0:
            
            it_went_ok = self._RewindProcessing()
            
            if it_went_ok:
                
                self._ShowCurrentPair()
                
            
        
    
    def _LoadNextBatchOfPairs( self ):
        
        self._hashes_due_to_be_deleted_in_this_batch = set()
        self._hashes_processed_in_this_batch = set()
        self._processed_pairs = [] # just in case someone 'skip'ed everything in the last batch, so this never got cleared above in the commit
        
        self.ClearMedia()
        
        self._media_list = ClientMedia.ListeningMediaList( self._location_context, [] )
        
        self._currently_fetching_pairs = True
        
        CG.client_controller.CallToThread( self.THREADFetchPairs, self._file_search_context_1, self._file_search_context_2, self._dupe_search_type, self._pixel_dupes_preference, self._max_hamming_distance )
        
        self.update()
        
    
    def _MediaAreAlternates( self ):
        
        self._ProcessPair( HC.DUPLICATE_ALTERNATE )
        
    
    def _MediaAreFalsePositive( self ):
        
        self._ProcessPair( HC.DUPLICATE_FALSE_POSITIVE )
        
    
    def _MediaAreTheSame( self ):
        
        self._ProcessPair( HC.DUPLICATE_SAME_QUALITY )
        
    
    def _PrefetchNeighbours( self ):
        
        if self._current_media is None:
            
            return
            
        
        other_media = self._media_list.GetNext( self._current_media )
        
        media_to_prefetch = [ other_media ]
        
        # this doesn't handle big skip events, but that's a job for later
        if self._GetNumRemainingDecisions() > 1: # i.e. more than the current one we are looking at
            
            media_to_prefetch.extend( self._batch_of_pairs_to_process[ self._current_pair_index + 1 ] )
            
        
        image_cache = CG.client_controller.GetCache( 'images' )
        
        for media in media_to_prefetch:
            
            hash = media.GetHash()
            mime = media.GetMime()
            
            if media.IsStaticImage() and ClientGUICanvasMedia.WeAreExpectingToLoadThisMediaFile( media, self.CANVAS_TYPE ):
                
                if not image_cache.HasImageRenderer( hash ):
                    
                    # we do qt safe to make sure the job is cancelled if we are destroyed
                    
                    CG.client_controller.CallAfterQtSafe( self, 'image pre-fetch', image_cache.PrefetchImageRenderer, media )
                    
                
            
        
    
    def _ProcessPair( self, duplicate_type, delete_first = False, delete_second = False, duplicate_content_merge_options = None ):
        
        if self._current_media is None:
            
            return
            
        
        if duplicate_content_merge_options is None:
            
            if duplicate_type in [ HC.DUPLICATE_BETTER, HC.DUPLICATE_SAME_QUALITY ] or ( CG.client_controller.new_options.GetBoolean( 'advanced_mode' ) and duplicate_type == HC.DUPLICATE_ALTERNATE ):
                
                new_options = CG.client_controller.new_options
                
                duplicate_content_merge_options = new_options.GetDuplicateContentMergeOptions( duplicate_type )
                
            else:
                
                duplicate_content_merge_options = ClientDuplicates.DuplicateContentMergeOptions()
                
            
        
        first_media = self._current_media
        second_media = self._media_list.GetNext( first_media )
        
        was_auto_skipped = False
        
        self._hashes_processed_in_this_batch.update( first_media.GetHashes() )
        self._hashes_processed_in_this_batch.update( second_media.GetHashes() )
        
        if delete_first or delete_second:
            
            if delete_first:
                
                self._hashes_due_to_be_deleted_in_this_batch.update( first_media.GetHashes() )
                
            
            if delete_second:
                
                self._hashes_due_to_be_deleted_in_this_batch.update( second_media.GetHashes() )
                
            
            if duplicate_type in ( HC.DUPLICATE_BETTER, HC.DUPLICATE_WORSE ):
                
                file_deletion_reason = 'better/worse'
                
                if delete_second:
                    
                    file_deletion_reason += ', worse file deleted'
                    
                
            else:
                
                file_deletion_reason = HC.duplicate_type_string_lookup[ duplicate_type ]
                
            
            if delete_first and delete_second:
                
                file_deletion_reason += ', both files deleted'
                
            
            file_deletion_reason = 'Deleted in Duplicate Filter ({}).'.format( file_deletion_reason )
            
        else:
            
            file_deletion_reason = None
            
        
        content_update_packages = [ duplicate_content_merge_options.ProcessPairIntoContentUpdatePackage( first_media, second_media, delete_first = delete_first, delete_second = delete_second, file_deletion_reason = file_deletion_reason ) ]
        
        process_tuple = ( duplicate_type, first_media, second_media, content_update_packages, was_auto_skipped )
        
        self._ShowNextPair( process_tuple )
        
    
    def _RewindProcessing( self ) -> bool:
        
        if self._currently_fetching_pairs:
            
            return False
            
        
        def test_we_can_pop():
            
            if len( self._processed_pairs ) == 0:
                
                # the first one shouldn't be auto-skipped, so if it was and now we can't pop, something weird happened
                
                CG.client_controller.pub( 'new_similar_files_potentials_search_numbers' )
                
                ClientGUIDialogsMessage.ShowCritical( self, 'Hell!', 'Due to an unexpected series of events, the duplicate filter has no valid pair to back up to. It could be some files were deleted during processing. The filter will now close.' )
                
                self.window().deleteLater()
                
                return False
                
            
            return True
            
        
        if self._current_pair_index > 0:
            
            while True:
                
                if not test_we_can_pop():
                    
                    return False
                    
                
                ( duplicate_type, first_media, second_media, content_update_packages, was_auto_skipped ) = self._processed_pairs.pop()
                
                self._current_pair_index -= 1
                
                if not was_auto_skipped:
                    
                    break
                    
                
            
            # only want this for the one that wasn't auto-skipped
            for m in ( first_media, second_media ):
                
                hash = m.GetHash()
                
                self._hashes_due_to_be_deleted_in_this_batch.discard( hash )
                self._hashes_processed_in_this_batch.discard( hash )
                
            
            return True
            
        
        return False
        
    
    def _ShowCurrentPair( self ):
        
        if self._currently_fetching_pairs:
            
            return
            
        
        ( first_media_result, second_media_result ) = self._batch_of_pairs_to_process[ self._current_pair_index ]
        
        first_media = ClientMedia.MediaSingleton( first_media_result )
        second_media = ClientMedia.MediaSingleton( second_media_result )
        
        score = ClientDuplicates.GetDuplicateComparisonScore( first_media, second_media )
        
        if score > 0:
            
            media_results_with_better_first = ( first_media_result, second_media_result )
            
        else:
            
            media_results_with_better_first = ( second_media_result, first_media_result )
            
        
        self._media_list = ClientMedia.ListeningMediaList( self._location_context, media_results_with_better_first )
        
        # reset zoom gubbins
        self.SetMedia( None )
        
        self.SetMedia( self._media_list.GetFirst() )

        self._media_container.hide()
        
        self._media_container.ZoomReinit()
        
        self._media_container.ResetCenterPosition()
        
        self.EndDrag()
        
        self._media_container.show()
        
    
    def _ShowNextPair( self, process_tuple: tuple ):
        
        if self._currently_fetching_pairs:
            
            return
            
        
        # hackery dackery doo to quick solve something that is calling this a bunch of times while the 'and continue?' dialog is open, making like 16 of them
        # a full rewrite is needed on this awful workflow
        
        tlws = QW.QApplication.topLevelWidgets()
        
        for tlw in tlws:
            
            if isinstance( tlw, ClientGUITopLevelWindowsPanels.DialogCustomButtonQuestion ) and tlw.isModal():
                
                return
                
            
        
        #
        
        def pair_is_good( pair ):
            
            ( first_media_result, second_media_result ) = pair
            
            first_hash = first_media_result.GetHash()
            second_hash = second_media_result.GetHash()
            
            if first_hash in self._hashes_processed_in_this_batch or second_hash in self._hashes_processed_in_this_batch:
                
                return False
                
            
            if first_hash in self._hashes_due_to_be_deleted_in_this_batch or second_hash in self._hashes_due_to_be_deleted_in_this_batch:
                
                return False
                
            
            first_media = ClientMedia.MediaSingleton( first_media_result )
            second_media = ClientMedia.MediaSingleton( second_media_result )
            
            if not ClientMedia.CanDisplayMedia( first_media ) or not ClientMedia.CanDisplayMedia( second_media ):
                
                return False
                
            
            return True
            
        
        #
        
        self._processed_pairs.append( process_tuple )
        
        self._current_pair_index += 1
        
        while True:
            
            num_remaining = self._GetNumRemainingDecisions()
            
            if num_remaining == 0:
                
                num_committable = self._GetNumCommittableDecisions()
                num_deletable = self._GetNumCommittableDeletes()
                
                if num_committable + num_deletable > 0:
                    
                    components = []
                    
                    if num_committable > 0:
                        
                        components.append( '{} decisions'.format( HydrusData.ToHumanInt( num_committable ) ) )
                        
                    
                    if num_deletable > 0:
                        
                        components.append( '{} deletes'.format( HydrusData.ToHumanInt( num_deletable ) ) )
                        
                    
                    label = 'commit {} and continue?'.format( ' and '.join( components ) )
                    
                    result = ClientGUIDialogsQuick.GetInterstitialFilteringAnswer( self, label )
                    
                    if result == QW.QDialog.Accepted:
                        
                        self._CommitProcessed( blocking = True )
                        
                    else:
                        
                        it_went_ok = self._RewindProcessing()
                        
                        if it_went_ok:
                            
                            self._ShowCurrentPair()
                            
                        
                        return
                        
                    
                else:
                    
                    # nothing to commit, so let's see if we have a big problem here or if user just skipped all
                    
                    we_saw_a_non_auto_skip = False
                    
                    for ( duplicate_type, first_media, second_media, content_update_packages, was_auto_skipped ) in self._processed_pairs:
                        
                        if not was_auto_skipped:
                            
                            we_saw_a_non_auto_skip = True
                            
                            break
                            
                        
                    
                    if not we_saw_a_non_auto_skip:
                        
                        CG.client_controller.pub( 'new_similar_files_potentials_search_numbers' )
                        
                        ClientGUIDialogsMessage.ShowCritical( self, 'Hell!', 'It seems an entire batch of pairs were unable to be displayed. The duplicate filter will now close.' )
                        
                        self.window().deleteLater()
                        
                        return
                        
                    
                
                self._LoadNextBatchOfPairs()
                
                return
                
            
            current_pair = self._batch_of_pairs_to_process[ self._current_pair_index ]
            
            if pair_is_good( current_pair ):
                
                self._ShowCurrentPair()
                
                return
                
            else:
                
                was_auto_skipped = True
                
                self._processed_pairs.append( ( None, None, None, [], was_auto_skipped ) )
                
                self._current_pair_index += 1
                
            
        
    
    def _ShowPairInPage( self ):
        
        if self._current_media is None:
            
            return
            
        
        self.showPairInPage.emit( [ self._current_media, self._media_list.GetNext( self._current_media ) ] )
        
    
    def _SkipPair( self ):
        
        if self._current_media is None:
            
            return
            
        
        was_auto_skipped = False

        ( first_media_result, second_media_result ) = self._batch_of_pairs_to_process[ self._current_pair_index ]
        
        first_media = ClientMedia.MediaSingleton( first_media_result )
        second_media = ClientMedia.MediaSingleton( second_media_result )
        
        process_tuple = ( None, first_media, second_media, [], was_auto_skipped )
        
        self._ShowNextPair( process_tuple )
        
    
    def _SwitchMedia( self ):
        
        if self._current_media is not None:
            
            try:
                
                other_media = self._media_list.GetNext( self._current_media )
                
                self.SetMedia( other_media )
                
            except HydrusExceptions.DataMissing:
                
                return
                
            
        
    
    def Archive( self, canvas_key ):
        
        if self._canvas_key == canvas_key:
            
            self._Archive()
            
        
    
    def CleanBeforeDestroy( self ):
        
        CG.client_controller.pub( 'new_similar_files_potentials_search_numbers' )
        
        ClientDuplicates.hashes_to_jpeg_quality = {} # clear the cache
        
        CanvasWithHovers.CleanBeforeDestroy( self )
        
    
    def Delete( self, canvas_key ):
        
        if self._canvas_key == canvas_key:
            
            self._Delete()
            
        
    
    def Inbox( self, canvas_key ):
        
        if self._canvas_key == canvas_key:
            
            self._Inbox()
            
        
    
    def IsShowingAPair( self ):
        
        return self._current_media is not None and len( self._media_list ) > 1
        
    
    def IsShowingFileA( self ):
        
        if not self.IsShowingAPair():
            
            return False
            
        
        return self._current_media == self._media_list.GetFirst()
        
    
    def ProcessApplicationCommand( self, command: CAC.ApplicationCommand ):
        
        command_processed = True
        
        if command.IsSimpleCommand():
            
            action = command.GetSimpleAction()
            
            if action == CAC.SIMPLE_DUPLICATE_FILTER_THIS_IS_BETTER_AND_DELETE_OTHER:
                
                self._CurrentMediaIsBetter( delete_second = True )
                
            elif action == CAC.SIMPLE_DUPLICATE_FILTER_THIS_IS_BETTER_BUT_KEEP_BOTH:
                
                self._CurrentMediaIsBetter( delete_second = False )
                
            elif action == CAC.SIMPLE_DUPLICATE_FILTER_EXACTLY_THE_SAME:
                
                self._MediaAreTheSame()
                
            elif action == CAC.SIMPLE_DUPLICATE_FILTER_ALTERNATES:
                
                self._MediaAreAlternates()
                
            elif action == CAC.SIMPLE_DUPLICATE_FILTER_FALSE_POSITIVE:
                
                self._MediaAreFalsePositive()
                
            elif action == CAC.SIMPLE_DUPLICATE_FILTER_CUSTOM_ACTION:
                
                self._DoCustomAction()
                
            elif action == CAC.SIMPLE_DUPLICATE_FILTER_SKIP:
                
                self._SkipPair()
                
            elif action == CAC.SIMPLE_DUPLICATE_FILTER_BACK:
                
                self._GoBack()
                
            elif action in ( CAC.SIMPLE_VIEW_FIRST, CAC.SIMPLE_VIEW_LAST, CAC.SIMPLE_VIEW_PREVIOUS, CAC.SIMPLE_VIEW_NEXT ):
                
                self._SwitchMedia()
                
            else:
                
                command_processed = False
                
            
        else:
            
            command_processed = False
            
        
        if not command_processed:
            
            command_processed = CanvasWithHovers.ProcessApplicationCommand( self, command )
            
        
        return command_processed
        
    
    def ProcessContentUpdatePackage( self, content_update_package: ClientContentUpdates.ContentUpdatePackage ):
        
        def catch_up():
            
            # ugly, but it will do for now
            
            if len( self._media_list ) < 2 and len( self._batch_of_pairs_to_process ) > self._current_pair_index:
                
                was_auto_skipped = True
                
                ( first_media_result, second_media_result ) = self._batch_of_pairs_to_process[ self._current_pair_index ]
                
                first_media = ClientMedia.MediaSingleton( first_media_result )
                second_media = ClientMedia.MediaSingleton( second_media_result )
                
                process_tuple = ( None, first_media, second_media, [], was_auto_skipped )
                
                self._ShowNextPair( process_tuple )
                
            else:
                
                self.update()
                
            
        
        CG.client_controller.CallLaterQtSafe( self, 0.01, 'duplicates filter post-processing wait', catch_up )
        
    
    def SetMedia( self, media ):
        
        CanvasWithHovers.SetMedia( self, media )
        
        if media is not None:
            
            shown_media = self._current_media
            comparison_media = self._media_list.GetNext( shown_media )
            
            if shown_media != comparison_media:
                
                CG.client_controller.pub( 'canvas_new_duplicate_pair', self._canvas_key, shown_media, comparison_media )
                
            
        
    
    def SwitchMedia( self, canvas_key ):
        
        if canvas_key == self._canvas_key:
            
            self._SwitchMedia()
            
        
    
    def TryToDoPreClose( self ):
        
        num_committable = self._GetNumCommittableDecisions()
        num_deletable = self._GetNumCommittableDeletes()
        
        if num_committable + num_deletable > 0:
            
            components = []
            
            if num_committable > 0:
                
                components.append( '{} decisions'.format( HydrusData.ToHumanInt( num_committable ) ) )
                
            
            if num_deletable > 0:
                
                components.append( '{} deletes'.format( HydrusData.ToHumanInt( num_deletable ) ) )
                
            
            label = 'commit {}?'.format( ' and '.join( components ) )
            
            ( result, cancelled ) = ClientGUIDialogsQuick.GetFinishFilteringAnswer( self, label )
            
            if cancelled:
                
                close_was_triggered_by_everything_being_processed = self._GetNumRemainingDecisions() == 0
                
                if close_was_triggered_by_everything_being_processed:
                    
                    self._GoBack()
                    
                
                return False
                
            elif result == QW.QDialog.Accepted:
                
                self._CommitProcessed( blocking = False )
                
            
        
        return CanvasWithHovers.TryToDoPreClose( self )
        
    
    def Undelete( self, canvas_key ):
        
        if canvas_key == self._canvas_key:
            
            self._Undelete()
            
        
    
    def THREADFetchPairs( self, file_search_context_1, file_search_context_2, dupe_search_type, pixel_dupes_preference, max_hamming_distance ):
        
        def qt_close():
            
            if not self or not QP.isValid( self ):
                
                return
                
            
            ClientGUIDialogsMessage.ShowInformation( self, 'All pairs have been filtered!' )
            
            self._TryToCloseWindow()
            
        
        def qt_continue( unprocessed_pairs ):
            
            if not self or not QP.isValid( self ):
                
                return
                
            
            self._batch_of_pairs_to_process = unprocessed_pairs
            self._current_pair_index = 0
            
            self._currently_fetching_pairs = False
            
            self._ShowCurrentPair()
            
        
        result = CG.client_controller.Read( 'duplicate_pairs_for_filtering', file_search_context_1, file_search_context_2, dupe_search_type, pixel_dupes_preference, max_hamming_distance )
        
        if len( result ) == 0:
            
            QP.CallAfter( qt_close )
            
        else:
            
            QP.CallAfter( qt_continue, result )
            
        
    
class CanvasMediaList( ClientMedia.ListeningMediaList, CanvasWithHovers ):
    
    exitFocusMedia = QC.Signal( ClientMedia.Media )
    
    def __init__( self, parent, page_key, location_context: ClientLocation.LocationContext, media_results ):
        
        CanvasWithHovers.__init__( self, parent, location_context )
        ClientMedia.ListeningMediaList.__init__( self, location_context, media_results )
        
        self._page_key = page_key
        
        self._just_started = True
        
    
    def TryToDoPreClose( self ):
        
        if self._current_media is not None:
            
            self.exitFocusMedia.emit( self._current_media )
            
        
        return CanvasWithHovers.TryToDoPreClose( self )
        
    
    def _GenerateHoverTopFrame( self ):
        
        raise NotImplementedError()
        
    
    def _GetIndexString( self ):
        
        if self._current_media is None:
            
            index_string = '-/' + HydrusData.ToHumanInt( len( self._sorted_media ) )
            
        else:
            
            index_string = HydrusData.ConvertValueRangeToPrettyString( self._sorted_media.index( self._current_media ) + 1, len( self._sorted_media ) )
            
        
        return index_string
        
    
    def _PrefetchNeighbours( self ):
        
        media_looked_at = set()
        
        to_render = []
        
        previous = self._current_media
        next = self._current_media
        
        delay_base = CG.client_controller.new_options.GetInteger( 'media_viewer_prefetch_delay_base_ms' ) / 1000
        
        num_to_go_back = CG.client_controller.new_options.GetInteger( 'media_viewer_prefetch_num_previous' )
        num_to_go_forward = CG.client_controller.new_options.GetInteger( 'media_viewer_prefetch_num_next' )
        
        # if media_looked_at nukes the list, we want shorter delays, so do next first
        
        for i in range( num_to_go_forward ):
            
            next = self._GetNext( next )
            
            if next in media_looked_at:
                
                break
                
            else:
                
                media_looked_at.add( next )
                
            
            delay = delay_base * ( i + 1 )
            
            to_render.append( ( next, delay ) )
            
        
        for i in range( num_to_go_back ):
            
            previous = self._GetPrevious( previous )
            
            if previous in media_looked_at:
                
                break
                
            else:
                
                media_looked_at.add( previous )
                
            
            delay = delay_base * 2 * ( i + 1 )
            
            to_render.append( ( previous, delay ) )
            
        
        image_cache = CG.client_controller.GetCache( 'images' )
        
        for ( media, delay ) in to_render:
            
            hash = media.GetHash()
            mime = media.GetMime()
            
            if media.IsStaticImage() and ClientGUICanvasMedia.WeAreExpectingToLoadThisMediaFile( media, self.CANVAS_TYPE ):
                
                if not image_cache.HasImageRenderer( hash ):
                    
                    # we do qt safe to make sure the job is cancelled if we are destroyed
                    
                    CG.client_controller.CallLaterQtSafe( self, delay, 'image pre-fetch', image_cache.PrefetchImageRenderer, media )
                    
                
            
        
    
    def _Remove( self ):
        
        next_media = self._GetNext( self._current_media )
        
        if next_media == self._current_media:
            
            next_media = None
            
        
        hashes = { self._current_media.GetHash() }
        
        CG.client_controller.pub( 'remove_media', self._page_key, hashes )
        
        singleton_media = { self._current_media }
        
        ClientMedia.ListeningMediaList._RemoveMediaDirectly( self, singleton_media, {} )
        
        if self.HasNoMedia():
            
            self._TryToCloseWindow()
            
        elif self.HasMedia( self._current_media ):
            
            CG.client_controller.pub( 'canvas_new_index_string', self._canvas_key, self._GetIndexString() )
            
            self.update()
            
        else:
            
            self.SetMedia( next_media )
            
        
    
    def _ShowFirst( self ):
        
        self.SetMedia( self._GetFirst() )
        
    
    def _ShowLast( self ):
        
        self.SetMedia( self._GetLast() )
        
    
    def _ShowNext( self ):
        
        self.SetMedia( self._GetNext( self._current_media ) )
        
    
    def _ShowPrevious( self ):
        
        self.SetMedia( self._GetPrevious( self._current_media ) )
        
    
    def _StartSlideshow( self, interval: float ):
        
        pass
        
    
    def AddMediaResults( self, page_key, media_results ):
        
        if page_key == self._page_key:
            
            ClientMedia.ListeningMediaList.AddMediaResults( self, media_results )
            
            CG.client_controller.pub( 'canvas_new_index_string', self._canvas_key, self._GetIndexString() )
            
            self.update()
            
        
    
    def EventFullscreenSwitch( self, event ):
        
        self.parentWidget().FullscreenSwitch()
        
    
    def ProcessContentUpdatePackage( self, content_update_package: ClientContentUpdates.ContentUpdatePackage ):
        
        if self._current_media is None:
            
            # probably a file view stats update as we close down--ignore it
            
            return
            
        
        if self.HasMedia( self._current_media ):
            
            next_media = self._GetNext( self._current_media )
            
            if next_media == self._current_media:
                
                next_media = None
                
            
        else:
            
            next_media = None
            
        
        ClientMedia.ListeningMediaList.ProcessContentUpdatePackage( self, content_update_package )
        
        if self.HasNoMedia():
            
            self._TryToCloseWindow()
            
        elif self.HasMedia( self._current_media ):
            
            CG.client_controller.pub( 'canvas_new_index_string', self._canvas_key, self._GetIndexString() )
            
            self.update()
            
        elif self.HasMedia( next_media ):
            
            self.SetMedia( next_media )
            
        else:
            
            self.SetMedia( self._GetFirst() )
            
        
    
def CommitArchiveDelete( page_key: bytes, location_context: ClientLocation.LocationContext, kept: typing.Collection[ ClientMedia.MediaSingleton ], deleted: typing.Collection[ ClientMedia.MediaSingleton ] ):
    
    kept = list( kept )
    deleted = list( deleted )
    
    kept_hashes = [ m.GetHash() for m in kept ]
    deleted_hashes = [ m.GetHash() for m in deleted ]
    
    if HC.options[ 'remove_filtered_files' ]:
        
        all_hashes = set()
        
        all_hashes.update( kept_hashes )
        all_hashes.update( deleted_hashes )
        
        CG.client_controller.pub( 'remove_media', page_key, all_hashes )
        
    
    location_context = location_context.Duplicate()
    
    location_context.FixMissingServices( ClientLocation.ValidLocalDomainsFilter )
    
    if location_context.IncludesCurrent():
        
        deletee_file_service_keys = location_context.current_service_keys
        
    else:
        
        # if we are in a weird search domain, then just say 'delete from all local'
        deletee_file_service_keys = [ CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY ]
        
    
    for block_of_deleted in HydrusLists.SplitListIntoChunks( deleted, 64 ):
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage()
        
        reason = 'Deleted in Archive/Delete filter.'
        
        for deletee_file_service_key in deletee_file_service_keys:
            
            block_of_deleted_hashes = [ m.GetHash() for m in block_of_deleted if deletee_file_service_key in m.GetLocationsManager().GetCurrent() ]
            
            content_update_package.AddContentUpdate( deletee_file_service_key, ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, block_of_deleted_hashes, reason = reason ) )
            
        
        CG.client_controller.WriteSynchronous( 'content_updates', content_update_package )
        
        # we do a second set of removes to deal with late processing and a quick F5ing user
        
        if HC.options[ 'remove_filtered_files' ]:
            
            block_of_deleted_hashes = [ m.GetHash() for m in block_of_deleted ]
            
            CG.client_controller.pub( 'remove_media', page_key, block_of_deleted_hashes )
            
        
        CG.client_controller.WaitUntilViewFree()
        
    
    for block_of_kept_hashes in HydrusLists.SplitListIntoChunks( kept_hashes, 64 ):
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ARCHIVE, block_of_kept_hashes ) )
        
        CG.client_controller.WriteSynchronous( 'content_updates', content_update_package )
        
        if HC.options[ 'remove_filtered_files' ]:
            
            CG.client_controller.pub( 'remove_media', page_key, block_of_kept_hashes )
            
        
        CG.client_controller.WaitUntilViewFree()
        
    

class CanvasMediaListFilterArchiveDelete( CanvasMediaList ):
    
    CANVAS_TYPE = CC.CANVAS_MEDIA_VIEWER_ARCHIVE_DELETE
    
    def __init__( self, parent, page_key, location_context: ClientLocation.LocationContext, media_results ):
        
        CanvasMediaList.__init__( self, parent, page_key, location_context, media_results )
        
        self._my_shortcuts_handler.AddShortcuts( 'archive_delete_filter' )
        
        self._kept = set()
        self._deleted = set()
        
        CG.client_controller.sub( self, 'Delete', 'canvas_delete' )
        CG.client_controller.sub( self, 'Undelete', 'canvas_undelete' )
        
        first_media = self._GetFirst()
        
        if first_media is not None:
            
            QP.CallAfter( self.SetMedia, first_media ) # don't set this until we have a size > (20, 20)!
            
        
    
    def _Back( self ):
        
        if self._current_media == self._GetFirst():
            
            return
            
        else:
            
            self._ShowPrevious()
            
            self._kept.discard( self._current_media )
            self._deleted.discard( self._current_media )
            
        
    
    def TryToDoPreClose( self ):
        
        kept = list( self._kept )
        
        deleted = ClientMediaFileFilter.FilterAndReportDeleteLockFailures( self._deleted )
        
        if len( kept ) > 0 or len( deleted ) > 0:
            
            if len( kept ) > 0:
                
                kept_label = 'keep {}'.format( HydrusData.ToHumanInt( len( kept ) ) )
                
            else:
                
                kept_label = None
                
            
            deletion_options = []
            
            if len( deleted ) > 0:
                
                location_contexts_to_present_options_for = []
                
                if not self._location_context.IsAllLocalFiles():
                    
                    location_contexts_to_present_options_for.append( self._location_context )
                    
                
                current_local_service_keys = HydrusData.MassUnion( [ m.GetLocationsManager().GetCurrent() for m in deleted ] )
                
                local_file_domain_service_keys = [ service_key for service_key in current_local_service_keys if CG.client_controller.services_manager.GetServiceType( service_key ) == HC.LOCAL_FILE_DOMAIN ]
                
                location_contexts_to_present_options_for.extend( [ ClientLocation.LocationContext.STATICCreateSimple( service_key ) for service_key in local_file_domain_service_keys ] )
                
                all_my_files_location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY )
                
                if len( local_file_domain_service_keys ) > 1:
                    
                    location_contexts_to_present_options_for.append( all_my_files_location_context )
                    
                elif len( local_file_domain_service_keys ) == 1:
                    
                    if all_my_files_location_context in location_contexts_to_present_options_for:
                        
                        location_contexts_to_present_options_for.remove( all_my_files_location_context )
                        
                    
                
                if CC.TRASH_SERVICE_KEY in current_local_service_keys or CC.LOCAL_UPDATE_SERVICE_KEY in current_local_service_keys:
                    
                    location_contexts_to_present_options_for.append( ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_FILE_SERVICE_KEY ) )
                    
                
                location_contexts_to_present_options_for = HydrusData.DedupeList( location_contexts_to_present_options_for )
                
                for location_context in location_contexts_to_present_options_for:
                    
                    file_service_keys = location_context.current_service_keys
                    
                    num_deletable = len( [ m for m in deleted if len( m.GetLocationsManager().GetCurrent().intersection( file_service_keys ) ) > 0 ] )
                    
                    if num_deletable > 0:
                        
                        if location_context == ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY ):
                            
                            location_label = 'all local file domains'
                            
                        elif location_context == ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_FILE_SERVICE_KEY ):
                            
                            location_label = 'my hard disk'
                            
                        else:
                            
                            location_label = location_context.ToString( CG.client_controller.services_manager.GetName )
                            
                        
                        delete_label = 'delete {} from {}'.format( HydrusData.ToHumanInt( num_deletable ), location_label )
                        
                        deletion_options.append( ( location_context, delete_label ) )
                        
                    
                
            
            ( result, deletee_location_context, cancelled ) = ClientGUIDialogsQuick.GetFinishArchiveDeleteFilteringAnswer( self, kept_label, deletion_options )
            
            if cancelled:
                
                if self._current_media in self._kept:
                    
                    self._kept.remove( self._current_media )
                    
                
                if self._current_media in self._deleted:
                    
                    self._deleted.remove( self._current_media )
                    
                
                return False
                
            elif result == QW.QDialog.Accepted:
                
                self._kept = set()
                self._deleted = set()
                
                self._current_media = self._GetFirst() # so the pubsub on close is better
                
                CG.client_controller.CallToThread( CommitArchiveDelete, self._page_key, deletee_location_context, kept, deleted )
                
            
        
        return CanvasMediaList.TryToDoPreClose( self )
        
    
    def _Delete( self, media = None, reason = None, file_service_key = None ):
        
        if self._current_media is None:
            
            return False
            
        
        if self._current_media.HasDeleteLocked():
            
            message = 'This file is delete-locked! Send it back to the inbox to delete it!'
            
            ClientGUIDialogsMessage.ShowWarning( self, message )
            
            return False
            
        
        self._deleted.add( self._current_media )
        
        if self._current_media == self._GetLast():
            
            self._TryToCloseWindow()
            
        else:
            
            self._ShowNext()
            
        
        return True
        
    
    def _GenerateHoverTopFrame( self ):
        
        return ClientGUICanvasHoverFrames.CanvasHoverFrameTopArchiveDeleteFilter( self, self, self._canvas_key )
        
    
    def _Keep( self ):
        
        self._kept.add( self._current_media )
        
        if self._current_media == self._GetLast():
            
            self._TryToCloseWindow()
            
        else:
            
            self._ShowNext()
            
        
    
    def _Skip( self ):
        
        if self._current_media == self._GetLast():
            
            self._TryToCloseWindow()
            
        else:
            
            self._ShowNext()
            
        
    
    def Keep( self, canvas_key ):
        
        if canvas_key == self._canvas_key:
            
            self._Keep()
            
        
    
    def Back( self, canvas_key ):
        
        if canvas_key == self._canvas_key:
            
            self._Back()
            
        
    
    def Delete( self, canvas_key ):
        
        if canvas_key == self._canvas_key:
            
            self._Delete()
            
        
    
    def ProcessApplicationCommand( self, command: CAC.ApplicationCommand ):
        
        command_processed = True
        
        if command.IsSimpleCommand():
            
            action = command.GetSimpleAction()
            
            if action in ( CAC.SIMPLE_ARCHIVE_DELETE_FILTER_KEEP, CAC.SIMPLE_ARCHIVE_FILE ):
                
                self._Keep()
                
            elif action in ( CAC.SIMPLE_ARCHIVE_DELETE_FILTER_DELETE, CAC.SIMPLE_DELETE_FILE ):
                
                self._Delete()
                
            elif action == CAC.SIMPLE_ARCHIVE_DELETE_FILTER_SKIP:
                
                self._Skip()
                
            elif action == CAC.SIMPLE_ARCHIVE_DELETE_FILTER_BACK:
                
                self._Back()
                
            elif action == CAC.SIMPLE_LAUNCH_THE_ARCHIVE_DELETE_FILTER:
                
                self._TryToCloseWindow()
                
            else:
                
                command_processed = False
                
            
        else:
            
            command_processed = False
            
        
        if not command_processed:
            
            command_processed = CanvasMediaList.ProcessApplicationCommand( self, command )
            
        
        return command_processed
        
    
    def Skip( self, canvas_key ):
        
        if canvas_key == self._canvas_key:
            
            self._Skip()
            
        
    
    def Undelete( self, canvas_key ):
        
        if canvas_key == self._canvas_key:
            
            self._Undelete()
            
        
    
class CanvasMediaListNavigable( CanvasMediaList ):
    
    userChangedMedia = QC.Signal()
    
    def __init__( self, parent, page_key, location_context: ClientLocation.LocationContext, media_results ):
        
        CanvasMediaList.__init__( self, parent, page_key, location_context, media_results )
        
        self._my_shortcuts_handler.AddShortcuts( 'media_viewer_browser' )
        
        CG.client_controller.sub( self, 'Delete', 'canvas_delete' )
        CG.client_controller.sub( self, 'ShowNext', 'canvas_show_next' )
        CG.client_controller.sub( self, 'ShowPrevious', 'canvas_show_previous' )
        CG.client_controller.sub( self, 'Undelete', 'canvas_undelete' )
        
    
    def _GenerateHoverTopFrame( self ):
        
        return ClientGUICanvasHoverFrames.CanvasHoverFrameTopNavigableList( self, self, self._canvas_key )
        
    
    def Archive( self, canvas_key ):
        
        if self._canvas_key == canvas_key:
            
            self._Archive()
            
        
    
    def Delete( self, canvas_key ):
        
        if self._canvas_key == canvas_key:
            
            self._Delete()
            
        
    
    def Inbox( self, canvas_key ):
        
        if self._canvas_key == canvas_key:
            
            self._Inbox()
            
        
    
    def ProcessApplicationCommand( self, command: CAC.ApplicationCommand ):
        
        command_processed = True
        
        if command.IsSimpleCommand():
            
            action = command.GetSimpleAction()
            
            if action == CAC.SIMPLE_REMOVE_FILE_FROM_VIEW:
                
                self._Remove()
                
            elif action == CAC.SIMPLE_VIEW_FIRST:
                
                self._ShowFirst()
                
                self.userChangedMedia.emit()
                
            elif action == CAC.SIMPLE_VIEW_LAST:
                
                self._ShowLast()
                
                self.userChangedMedia.emit()
                
            elif action == CAC.SIMPLE_VIEW_PREVIOUS:
                
                self._ShowPrevious()
                
                self.userChangedMedia.emit()
                
            elif action == CAC.SIMPLE_VIEW_NEXT:
                
                self._ShowNext()
                
                self.userChangedMedia.emit()
                
            else:
                
                command_processed = False
                
            
        else:
            
            command_processed = False
            
        
        if not command_processed:
            
            command_processed = CanvasMediaList.ProcessApplicationCommand( self, command )
            
        
        return command_processed
        
    
    def ShowFirst( self, canvas_key ):
        
        if canvas_key == self._canvas_key:
            
            self._ShowFirst()
            
            self.userChangedMedia.emit()
            
        
    
    def ShowLast( self, canvas_key ):
        
        if canvas_key == self._canvas_key:
            
            self._ShowLast()
            
            self.userChangedMedia.emit()
            
        
    
    def ShowNext( self, canvas_key ):
        
        if canvas_key == self._canvas_key:
            
            self._ShowNext()
            
            self.userChangedMedia.emit()
            
        
    
    def ShowPrevious( self, canvas_key ):
        
        if canvas_key == self._canvas_key:
            
            self._ShowPrevious()
            
            self.userChangedMedia.emit()
            
        
    
    def Undelete( self, canvas_key ):
        
        if canvas_key == self._canvas_key:
            
            self._Undelete()
            
        
    
class CanvasMediaListBrowser( CanvasMediaListNavigable ):
    
    def __init__( self, parent, page_key, location_context: ClientLocation.LocationContext, media_results, first_hash ):
        
        CanvasMediaListNavigable.__init__( self, parent, page_key, location_context, media_results )
        
        self._slideshow_is_running = False
        self._last_slideshow_switch_time = 0
        self._normal_slideshow_period = 0.0
        self._special_slideshow_period_for_current_media = None
        
        if first_hash is None:
            
            first_media = self._GetFirst()
            
        else:
            
            try:
                
                first_media = self._GetMedia( { first_hash } )[0]
                
            except:
                
                first_media = self._GetFirst()
                
            
        
        if first_media is not None:
            
            QP.CallAfter( self.SetMedia, first_media ) # don't set this until we have a size > (20, 20)!
            
        
        CG.client_controller.sub( self, 'AddMediaResults', 'add_media_results' )
        
        self.userChangedMedia.connect( self.NotifyUserChangedMedia )
        
    
    def _CalculateAnySpecialSlideshowPeriodForCurrentMedia( self ):
        
        if self._media_container.CurrentlyPresentingMediaWithDuration():
            
            stop_after_one_play = False
            
            duration_s = self._current_media.GetMediaResult().GetDuration()
            
            if duration_s is None:
                
                self._StopSlideshow()
                
                return
                
            
            new_options = CG.client_controller.new_options
            
            if duration_s < self._normal_slideshow_period:
                
                # ok, we have a short video. maybe we want to move the slideshow on early
                
                short_cutoff_periods = []
                
                slideshow_short_duration_loop_percentage = new_options.GetNoneableInteger( 'slideshow_short_duration_loop_percentage' )
                
                if slideshow_short_duration_loop_percentage is not None:
                    
                    short_cutoff_periods.append( self._normal_slideshow_period * ( slideshow_short_duration_loop_percentage / 100 ) )
                    
                
                slideshow_short_duration_loop_seconds = new_options.GetNoneableInteger( 'slideshow_short_duration_loop_seconds' )
                
                if slideshow_short_duration_loop_seconds is not None:
                    
                    short_cutoff_periods.append( slideshow_short_duration_loop_seconds )
                    
                
                short_cutoff_periods.sort( reverse = True )
                
                for short_cutoff_period in short_cutoff_periods:
                    
                    if short_cutoff_period > self._normal_slideshow_period:
                        
                        continue
                        
                    
                    if duration_s <= short_cutoff_period: # will it play once in this shorter time?
                        
                        self._special_slideshow_period_for_current_media = short_cutoff_period
                        
                    
                
                slideshow_short_duration_cutoff_percentage = new_options.GetNoneableInteger( 'slideshow_short_duration_cutoff_percentage' )
                
                if slideshow_short_duration_cutoff_percentage is not None:
                    
                    if self._normal_slideshow_period * ( slideshow_short_duration_cutoff_percentage / 100 ) < duration_s < self._normal_slideshow_period:
                        
                        self._special_slideshow_period_for_current_media = duration_s
                        
                        stop_after_one_play = True
                        
                        
                    
                
                # ok, if we are a shorter vid, we have now moved to the earliest valid time to switch
                
            else:
                
                # ok, we have a longer vid. maybe we want to permit a little overspill to show the whole thing
                
                slideshow_long_duration_overspill_percentage = new_options.GetNoneableInteger( 'slideshow_long_duration_overspill_percentage' )
                
                if slideshow_long_duration_overspill_percentage is not None:
                    
                    potential_overspill_quotient = 1 + ( slideshow_long_duration_overspill_percentage / 100 )
                    
                    if duration_s < self._normal_slideshow_period * potential_overspill_quotient: # ok it fits in this time
                        
                        self._special_slideshow_period_for_current_media = duration_s
                        
                        stop_after_one_play = True
                        
                    
                
                # ok, if we have a long overspill video, we have now moved to the earliest valid time to switch
                
            
            if stop_after_one_play:
                
                self._media_container.StopForSlideshow( True )
                
            
        
    
    def _DoSlideshowWork( self ):
        
        if self._slideshow_is_running:
            
            if self._current_media is None:
                
                return
                
            
            if CGC.core().MenuIsOpen():
                
                return
                
            
            if self._media_container.CurrentlyPresentingMediaWithDuration():
                
                if CG.client_controller.new_options.GetBoolean( 'slideshow_always_play_duration_media_once_through' ):
                    
                    if not self._media_container.HasPlayedOnceThrough():
                        
                        return
                        
                    
                
            
            if self._special_slideshow_period_for_current_media is None:
                
                time_to_switch = self._last_slideshow_switch_time + self._normal_slideshow_period
                
            else:
                
                time_to_switch = self._last_slideshow_switch_time + self._special_slideshow_period_for_current_media
                
            
            if not HydrusTime.TimeHasPassedFloat( time_to_switch ):
                
                return
                
            
            self._ShowNext()
            
            self._RegisterNextSlideshowPresentation()
            
        
    
    def _PausePlaySlideshow( self ):
        
        if self._slideshow_is_running:
            
            self._StopSlideshow()
            
        elif self._normal_slideshow_period > 0.0:
            
            self._StartSlideshow( self._normal_slideshow_period )
            
        
    
    def _RegisterNextSlideshowPresentation( self ):
        
        if self._slideshow_is_running:
            
            self._last_slideshow_switch_time = HydrusTime.GetNowFloat()
            
            self._special_slideshow_period_for_current_media = None
            
            self._CalculateAnySpecialSlideshowPeriodForCurrentMedia()
            
        
    
    def _StartSlideshow( self, period: float ):
        
        self._StopSlideshow()
        
        if period > 0.0:
            
            self._normal_slideshow_period = period
            
            self._slideshow_is_running = True
            
            self._RegisterNextSlideshowPresentation()
            
        
    
    def _StartSlideshowCustomPeriod( self ):
        
        with ClientGUIDialogs.DialogTextEntry( self, 'Enter the interval, in seconds.', default = '15', min_char_width = 12 ) as dlg:
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                try:
                    
                    period = float( dlg.GetValue() )
                    
                    self._StartSlideshow( period )
                    
                except:
                    
                    pass
                    
                
            
        
    
    def _StopSlideshow( self ):
        
        if self._slideshow_is_running:
            
            self._slideshow_is_running = False
            self._special_slideshow_period_for_current_media = None
            
            self._media_container.StopForSlideshow( False )
            
        
    
    def contextMenuEvent( self, event ):
        
        if event.reason() == QG.QContextMenuEvent.Keyboard:
            
            self.ShowMenu()
            
        
    
    def NotifyUserChangedMedia( self ):
        
        self._RegisterNextSlideshowPresentation()
        
    
    def ProcessApplicationCommand( self, command: CAC.ApplicationCommand ):
        
        command_processed = True
        
        if command.IsSimpleCommand():
            
            action = command.GetSimpleAction()
            
            if action == CAC.SIMPLE_PAUSE_PLAY_SLIDESHOW:
                
                self._PausePlaySlideshow()
                
            elif action == CAC.SIMPLE_SHOW_MENU:
                
                self.ShowMenu()
                
            else:
                
                command_processed = False
                
            
        else:
            
            command_processed = False
            
        
        if not command_processed:
            
            command_processed = CanvasMediaListNavigable.ProcessApplicationCommand( self, command )
            
        
        return command_processed
        
    
    def ShowMenu( self ):
        
        if self._current_media is not None:
            
            new_options = CG.client_controller.new_options
            
            advanced_mode = new_options.GetBoolean( 'advanced_mode' )
            
            services = CG.client_controller.services_manager.GetServices()
            
            local_ratings_services = [ service for service in services if service.GetServiceType() in HC.RATINGS_SERVICES ]
            
            i_can_post_ratings = len( local_ratings_services ) > 0
            
            self.EndDrag() # to stop successive right-click drag warp bug
            
            locations_manager = self._current_media.GetLocationsManager()
            
            menu = ClientGUIMenus.GenerateMenu( self )
            
            #
            
            info_lines = self._current_media.GetPrettyInfoLines()
            
            info_menu = ClientGUIMenus.GenerateMenu( menu )
            
            ClientGUIMediaMenus.AddPrettyInfoLines( info_menu, info_lines )
            
            ClientGUIMenus.AppendSeparator( info_menu )
            
            ClientGUIMediaMenus.AddFileViewingStatsMenu( info_menu, ( self._current_media, ) )
            
            filetype_summary = ClientMedia.GetMediasFiletypeSummaryString( [ self._current_media ] )
            size_summary = HydrusData.ToHumanBytes( self._current_media.GetSize() )
            
            info_summary = f'{filetype_summary}, {size_summary}'
            
            ClientGUIMenus.AppendMenu( menu, info_menu, info_summary )
            
            #
            
            ClientGUIMenus.AppendSeparator( menu )
            
            if self._media_container.IsZoomable():
                
                zoom_menu = ClientGUIMenus.GenerateMenu( menu )
                
                ClientGUIMenus.AppendMenuItem( zoom_menu, 'zoom in', 'Zoom the media in.', self._media_container.ZoomIn )
                ClientGUIMenus.AppendMenuItem( zoom_menu, 'zoom out', 'Zoom the media out.', self._media_container.ZoomOut )
                
                current_zoom = self._media_container.GetCurrentZoom()
                
                if current_zoom != 1.0:
                    
                    ClientGUIMenus.AppendMenuItem( zoom_menu, 'zoom to 100%', 'Set the zoom to 100%.', self._media_container.ZoomSwitch )
                    
                elif current_zoom != self._media_container.GetCanvasZoom():
                    
                    ClientGUIMenus.AppendMenuItem( zoom_menu, 'zoom fit', 'Set the zoom so the media fits the canvas.', self._media_container.ZoomSwitch )
                    
                
                if not self._media_container.IsAtMaxZoom():
                    
                    ClientGUIMenus.AppendMenuItem( zoom_menu, 'zoom to max', 'Set the zoom to the maximum possible.', self._media_container.ZoomMax )
                    
                
                ClientGUIMenus.AppendMenu( menu, zoom_menu, 'zoom: {}'.format( ClientData.ConvertZoomToPercentage( self._media_container.GetCurrentZoom() ) ) )
                
            
            if self.parentWidget().isFullScreen():
                
                ClientGUIMenus.AppendMenuItem( menu, 'exit fullscreen', 'Make this media viewer a regular window with borders.', self.parentWidget().FullscreenSwitch )
                
            else:
                
                ClientGUIMenus.AppendMenuItem( menu, 'go fullscreen', 'Make this media viewer a fullscreen window without borders.', self.parentWidget().FullscreenSwitch )
                
            
            slideshow = ClientGUIMenus.GenerateMenu( menu )
            
            slideshow_durations = CG.client_controller.new_options.GetSlideshowDurations()
            
            for slideshow_duration in slideshow_durations:
                
                pretty_duration = HydrusTime.TimeDeltaToPrettyTimeDelta( slideshow_duration )
                
                ClientGUIMenus.AppendMenuItem( slideshow, pretty_duration, f'Start a slideshow that changes media every {pretty_duration}.', self._StartSlideshow, slideshow_duration )
                
            
            ClientGUIMenus.AppendMenuItem( slideshow, 'very fast', 'Start a very fast slideshow.', self._StartSlideshow, 0.08 )
            ClientGUIMenus.AppendMenuItem( slideshow, 'custom interval', 'Start a slideshow with a custom interval.', self._StartSlideshowCustomPeriod )
            
            ClientGUIMenus.AppendMenu( menu, slideshow, 'start slideshow' )
            
            if self._slideshow_is_running:
                
                ClientGUIMenus.AppendMenuItem( menu, 'stop slideshow', 'Stop the current slideshow.', self._PausePlaySlideshow )
                
            
            ClientGUIMenus.AppendSeparator( menu )
            
            AddAudioVolumeMenu( menu, self.CANVAS_TYPE )
            
            ClientGUIMenus.AppendSeparator( menu )
            
            ClientGUIMenus.AppendMenuItem( menu, 'remove from view', 'Remove this file from the list you are viewing.', self._Remove )
            
            ClientGUIMenus.AppendSeparator( menu )
            
            if self._current_media.HasInbox():

                ClientGUIMenus.AppendMenuItem( menu, 'archive', 'Archive this file, taking it out of the inbox.', self._Archive )
                
            elif self._current_media.HasArchive() and self._current_media.GetLocationsManager().IsLocal():
                
                ClientGUIMenus.AppendMenuItem( menu, 'return to inbox', 'Put this file back in the inbox.', self._Inbox )
                
            
            ClientGUIMenus.AppendSeparator( menu )
            
            #
            
            local_file_service_keys = CG.client_controller.services_manager.GetServiceKeys( ( HC.LOCAL_FILE_DOMAIN, ) )
            
            # brush this up to handle different service keys
            # undelete do an optional service key too
            
            local_file_service_keys_we_are_in = sorted( locations_manager.GetCurrent().intersection( local_file_service_keys ), key = CG.client_controller.services_manager.GetName )
            
            if len( local_file_service_keys_we_are_in ) > 0:
                
                delete_menu = ClientGUIMenus.GenerateMenu( menu )
                
                for file_service_key in local_file_service_keys_we_are_in:
                    
                    ClientGUIMenus.AppendMenuItem( delete_menu, 'from {}'.format( CG.client_controller.services_manager.GetName( file_service_key ) ), 'Delete this file.', self._Delete, file_service_key = file_service_key )
                    
                
                ClientGUIMenus.AppendMenu( menu, delete_menu, 'delete' )
                
            
            #
            
            if locations_manager.IsTrashed():
                
                ClientGUIMenus.AppendMenuItem( menu, 'delete physically now', 'Delete this file immediately. This cannot be undone.', self._Delete, file_service_key = CC.COMBINED_LOCAL_FILE_SERVICE_KEY )
                ClientGUIMenus.AppendMenuItem( menu, 'undelete', 'Take this file out of the trash, returning it to its original file service.', self._Undelete )
                
            
            ClientGUIMenus.AppendSeparator( menu )
            
            manage_menu = ClientGUIMenus.GenerateMenu( menu )
            
            ClientGUIMenus.AppendMenuItem( manage_menu, 'tags', 'Manage this file\'s tags.', self._ManageTags )
            
            if i_can_post_ratings:
                
                ClientGUIMenus.AppendMenuItem( manage_menu, 'ratings', 'Manage this file\'s ratings.', self._ManageRatings )
                
            
            ClientGUIMenus.AppendMenuItem( manage_menu, 'urls', 'Manage this file\'s known urls.', self._ManageURLs )
            
            num_notes = self._current_media.GetNotesManager().GetNumNotes()
            
            notes_str = 'notes'
            
            if num_notes > 0:
                
                notes_str = '{} ({})'.format( notes_str, HydrusData.ToHumanInt( num_notes ) )
                
            
            ClientGUIMenus.AppendMenuItem( manage_menu, notes_str, 'Manage this file\'s notes.', self._ManageNotes )
            
            ClientGUIMenus.AppendMenuItem( manage_menu, 'times', 'Edit the timestamps for your files.', self._ManageTimestamps )
            ClientGUIMenus.AppendMenuItem( manage_menu, 'force filetype', 'Force your files to appear as a different filetype.', ClientGUIMediaActions.SetFilesForcedFiletypes, self, [ self._current_media ] )
            
            ClientGUIMediaMenus.AddManageFileViewingStatsMenu( self, manage_menu, [ self._current_media ] )
            
            ClientGUIMenus.AppendMenu( menu, manage_menu, 'manage' )
            
            ( local_duplicable_to_file_service_keys, local_moveable_from_and_to_file_service_keys ) = ClientGUIMediaActions.GetLocalFileActionServiceKeys( ( self._current_media, ) )
            
            multiple_selected = False
            
            ClientGUIMediaMenus.AddLocalFilesMoveAddToMenu( self, menu, local_duplicable_to_file_service_keys, local_moveable_from_and_to_file_service_keys, multiple_selected, self.ProcessApplicationCommand )
            
            ClientGUIMediaMenus.AddKnownURLsViewCopyMenu( self, menu, self._current_media )
            
            open_menu = ClientGUIMenus.GenerateMenu( menu )
            
            ClientGUIMenus.AppendMenuItem( open_menu, 'in external program', 'Open this file in the default external program.', self._OpenExternally )
            ClientGUIMenus.AppendMenuItem( open_menu, 'in a new page', 'Show your current media in a simple new page.', self._ShowMediaInNewPage )
            ClientGUIMenus.AppendMenuItem( open_menu, 'in web browser', 'Show this file in your OS\'s web browser.', self._OpenFileInWebBrowser )
            
            show_open_in_explorer = advanced_mode and ( HC.PLATFORM_WINDOWS or HC.PLATFORM_MACOS )
            
            if show_open_in_explorer:
                
                ClientGUIMenus.AppendMenuItem( open_menu, 'in file browser', 'Show this file in your OS\'s file browser.', self._OpenFileLocation )
                
            
            ClientGUIMenus.AppendMenu( menu, open_menu, 'open' )
            
            share_menu = ClientGUIMenus.GenerateMenu( menu )
            
            copy_menu = ClientGUIMenus.GenerateMenu( share_menu )

            ClientGUIMenus.AppendMenuItem( copy_menu, 'file', 'Copy this file to your clipboard.', self._CopyFileToClipboard )
            
            copy_hash_menu = ClientGUIMenus.GenerateMenu( copy_menu )

            ClientGUIMenus.AppendMenuItem( copy_hash_menu, 'sha256 ({})'.format( self._current_media.GetHash().hex() ), 'Copy this file\'s SHA256 hash to your clipboard.', self._CopyHashToClipboard, 'sha256' )
            ClientGUIMenus.AppendMenuItem( copy_hash_menu, 'md5', 'Copy this file\'s MD5 hash to your clipboard.', self._CopyHashToClipboard, 'md5' )
            ClientGUIMenus.AppendMenuItem( copy_hash_menu, 'sha1', 'Copy this file\'s SHA1 hash to your clipboard.', self._CopyHashToClipboard, 'sha1' )
            ClientGUIMenus.AppendMenuItem( copy_hash_menu, 'sha512', 'Copy this file\'s SHA512 hash to your clipboard.', self._CopyHashToClipboard, 'sha512' )
            
            file_info_manager = self._current_media.GetFileInfoManager()
            
            if file_info_manager.blurhash is not None:
                
                ClientGUIMenus.AppendMenuItem( copy_hash_menu, f'blurhash ({file_info_manager.blurhash})', 'Copy this file\'s blurhash.', self._CopyHashToClipboard, 'blurhash' )
                
            
            if file_info_manager.pixel_hash is not None:
                
                ClientGUIMenus.AppendMenuItem( copy_hash_menu, f'pixel ({file_info_manager.pixel_hash.hex()})', 'Copy this file\'s pixel hash.', self._CopyHashToClipboard, 'pixel_hash' )
                
            
            ClientGUIMenus.AppendMenu( copy_menu, copy_hash_menu, 'hash' )
            
            if advanced_mode:
                
                hash_id_str = str( self._current_media.GetHashId() )
                
                ClientGUIMenus.AppendMenuItem( copy_menu, 'file_id ({})'.format( hash_id_str ), 'Copy this file\'s internal file/hash_id.', CG.client_controller.pub, 'clipboard', 'text', hash_id_str )
                
            
            if self._current_media.IsStaticImage():
                
                ClientGUIMenus.AppendMenuItem( copy_menu, 'bitmap', 'Copy this file to your clipboard as a bitmap.', self._CopyBMPToClipboard )
                
                ( width, height ) = self._current_media.GetResolution()
                
                if width is not None and height is not None and ( width > 1024 or height > 1024 ):
                    
                    target_resolution = HydrusImageHandling.GetThumbnailResolution( self._current_media.GetResolution(), ( 1024, 1024 ), HydrusImageHandling.THUMBNAIL_SCALE_TO_FIT, 100 )
                    
                    ClientGUIMenus.AppendMenuItem( copy_menu, 'source lookup bitmap ({}x{})'.format( target_resolution[0], target_resolution[1] ), 'Copy a smaller bitmap of this file, for quicker lookup on source-finding websites.', self._CopyBMPToClipboard, target_resolution )
                    
                

            ClientGUIMenus.AppendMenuItem( copy_menu, 'path', 'Copy this file\'s path to your clipboard.', self._CopyPathToClipboard )
            
            ClientGUIMenus.AppendMenu( share_menu, copy_menu, 'copy' )
            
            ClientGUIMenus.AppendMenu( menu, share_menu, 'share' )
            
            CGC.core().PopupMenu( self, menu )
            
        
    
    def TIMERUIUpdate( self ):
        
        CanvasMediaListNavigable.TIMERUIUpdate( self )
        
        if self._slideshow_is_running:
            
            self._DoSlideshowWork()
            
        
    
