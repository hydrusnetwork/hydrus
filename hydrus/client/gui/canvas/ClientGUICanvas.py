import collections.abc
import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusLists
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusTags
from hydrus.core import HydrusTime

from hydrus.client import ClientApplicationCommand as CAC
from hydrus.client import ClientConstants as CC
from hydrus.client import ClientData
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientLocation
from hydrus.client import ClientServices
from hydrus.client import ClientThreading
from hydrus.client.duplicates import ClientDuplicates
from hydrus.client.duplicates import ClientPotentialDuplicatesSearchContext
from hydrus.client.gui import ClientGUICore as CGC
from hydrus.client.gui import ClientGUIDialogsManage
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIMenus
from hydrus.client.gui import ClientGUIRatings
from hydrus.client.gui import ClientGUIShortcuts
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.canvas import ClientGUICanvasHoverFrames
from hydrus.client.gui.canvas import ClientGUICanvasMedia
from hydrus.client.gui.duplicates import ClientGUIDuplicateActions
from hydrus.client.gui.duplicates import ClientGUIDuplicatesContentMergeOptions
from hydrus.client.gui.media import ClientGUIMediaSimpleActions
from hydrus.client.gui.media import ClientGUIMediaModalActions
from hydrus.client.gui.media import ClientGUIMediaControls
from hydrus.client.gui.media import ClientGUIMediaMenus
from hydrus.client.gui.metadata import ClientGUIManageTags
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.panels import ClientGUIScrolledPanelsCommitFiltering
from hydrus.client.gui.panels import ClientGUIScrolledPanelsEdit
from hydrus.client.gui.widgets import ClientGUIPainterShapes
from hydrus.client.media import ClientMedia
from hydrus.client.media import ClientMediaResult
from hydrus.client.media import ClientMediaResultPrettyInfo
from hydrus.client.metadata import ClientContentUpdates
from hydrus.client.metadata import ClientRatings
from hydrus.client.metadata import ClientTags
from hydrus.client.metadata import ClientTagSorting

def AddAudioVolumeMenu( menu, canvas_type ):
    
    mute_volume_type = None
    volume_volume_type = ClientGUIMediaControls.AUDIO_GLOBAL
    
    if canvas_type in CC.CANVAS_MEDIA_VIEWER_TYPES:
        
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
    
    def __init__( self, my_canvas ):
        
        self._my_canvas = my_canvas
        
    
    def _GetColourFromOptions( self ):
        
        return self._my_canvas.GetColour( CC.COLOUR_MEDIA_BACKGROUND )
        
    
    def GetColour( self ) -> QG.QColor:
        
        return self._GetColourFromOptions()
        
    
    def CanDoTransparencyCheckerboard( self ) -> bool:
        
        return CG.client_controller.new_options.GetBoolean( 'draw_transparency_checkerboard_media_canvas' )
        
    

class CanvasBackgroundColourGeneratorDuplicates( CanvasBackgroundColourGenerator ):
    
    def CanDoTransparencyCheckerboard( self ) -> bool:
        
        return CG.client_controller.new_options.GetBoolean( 'draw_transparency_checkerboard_media_canvas' ) or CG.client_controller.new_options.GetBoolean( 'draw_transparency_checkerboard_media_canvas_duplicates' )
        
    
    def GetColour( self ) -> QG.QColor:
        
        new_options = CG.client_controller.new_options
        
        normal_colour = self._GetColourFromOptions()
        
        if self._my_canvas.IsShowingAPair():
            
            if self._my_canvas.IsShowingFileA():
                
                duplicate_intensity = new_options.GetNoneableInteger( 'duplicate_background_switch_intensity_a' )
                
            else:
                
                duplicate_intensity = new_options.GetNoneableInteger( 'duplicate_background_switch_intensity_b' )
                
            
            return ClientGUIFunctions.GetLighterDarkerColour( normal_colour, duplicate_intensity )
            
        
        return normal_colour
        
    

# cribbing from here https://doc.qt.io/qt-5/layout.html#how-to-write-a-custom-layout-manager
# not finished, but a start as I continue to refactor. might want to rename to 'draggable layout' or something too, since it doesn't actually care about media container that much, and instead subclass vboxlayout?
class CanvasLayout( QW.QLayout ):
    
    def __init__( self ):
        
        super().__init__()
        
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
            
            if watched == self.parent() and event.type() == QC.QEvent.Type.LayoutRequest:
                
                return True
                
            
        except Exception as e:
            
            HydrusData.ShowException( e )
            
            return True
            
        
        return False
        
    

class Canvas( CAC.ApplicationCommandProcessorMixin, QW.QWidget ):
    
    CANVAS_TYPE = CC.CANVAS_MEDIA_VIEWER
    
    mediaCleared = QC.Signal()
    mediaChanged = QC.Signal( ClientMedia.MediaSingleton )
    
    def __init__( self, parent, location_context: ClientLocation.LocationContext ):
        
        self._qss_colours = {
            CC.COLOUR_MEDIA_BACKGROUND : QG.QColor( 255, 255, 255 ),
            CC.COLOUR_MEDIA_TEXT : QG.QColor( 0, 0, 0 )
        }
        
        super().__init__( parent )
        
        self.setObjectName( 'HydrusMediaViewer' )
        
        self.setSizePolicy( QW.QSizePolicy.Policy.Expanding, QW.QSizePolicy.Policy.Expanding )
        
        self._location_context = location_context
        
        self._background_colour_generator = CanvasBackgroundColourGenerator( self )
        
        self._current_media_start_time_ms = HydrusTime.GetNowMS()
        
        self._new_options = CG.client_controller.new_options
        
        self._canvas_type = CC.CANVAS_MEDIA_VIEWER
        self._canvas_key = HydrusData.GenerateKey()
        
        self._force_maintain_pan_and_zoom = False
        
        self._service_keys_to_services = {}
        
        self._current_media: typing.Optional[ ClientMedia.MediaSingleton ] = None
        
        catch_mouse = True
        
        # once we have catch_mouse full shortcut support for canvases, swap out this out for an option to swallow activating clicks
        ignore_activating_mouse_click = catch_mouse and self.CANVAS_TYPE != CC.CANVAS_PREVIEW
        
        self._my_shortcuts_handler = ClientGUIShortcuts.ShortcutsHandler( self, self, [ 'media', 'media_viewer' ], catch_mouse = catch_mouse, ignore_activating_mouse_click = ignore_activating_mouse_click )
        
        self._layout_silencer = LayoutEventSilencer( self )
        self.installEventFilter( self._layout_silencer )
        
        self._click_drag_reporting_filter = MediaContainerDragClickReportingFilter( self )
        
        self.installEventFilter( self._click_drag_reporting_filter )
        
        self._media_container = ClientGUICanvasMedia.MediaContainer( self, self.CANVAS_TYPE, self._background_colour_generator, self._click_drag_reporting_filter )
        
        self._last_drag_pos = None
        self._current_drag_is_touch = False
        self._last_motion_pos = QC.QPoint( 0, 0 )
        
        self._media_container.readyForNeighbourPrefetch.connect( self._PrefetchNeighbours )
        
        self._media_container.zoomChanged.connect( self.ZoomChanged )
        
        CG.client_controller.sub( self, 'ZoomIn', 'canvas_zoom_in' )
        CG.client_controller.sub( self, 'ZoomOut', 'canvas_zoom_out' )
        CG.client_controller.sub( self, 'ZoomSwitch', 'canvas_zoom_switch' )
        CG.client_controller.sub( self, 'ManageTags', 'canvas_manage_tags' )
        CG.client_controller.sub( self, 'update', 'notify_new_colourset' )
        CG.client_controller.sub( self, 'NotifyFilesNeedRedraw', 'notify_files_need_redraw' )
        
    
    def _Archive( self ):
        
        if self._current_media is not None:
            
            CG.client_controller.Write( 'content_updates', ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ARCHIVE, ( self._current_media.GetHash(), ) ) ) )
            
        
    
    def _Delete( self, media = None, default_reason = None, file_service_key = None, just_get_content_update_packages = False ) -> typing.Union[ bool, collections.abc.Collection[ ClientContentUpdates.ContentUpdatePackage ] ]:
        
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
            
        
        ClientGUIMediaModalActions.EditFileNotes( self, self._current_media, name_to_start_on = name_to_start_on )
        
    
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
                
                if isinstance( panel, ClientGUIManageTags.ManageTagsPanel ):
                    
                    child.activateWindow()
                    
                    command = CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_SET_SEARCH_FOCUS )
                    
                    panel.ProcessApplicationCommand( command )
                    
                    return
                    
                
            
        
        # take any focus away from hover window, which will mess up window order when it hides due to the new frame
        self.setFocus( QC.Qt.FocusReason.OtherFocusReason )
        
        title = 'manage tags'
        frame_key = 'manage_tags_frame'
        
        manage_tags = ClientGUITopLevelWindowsPanels.FrameThatTakesScrollablePanel( self, title, frame_key )
        
        panel = ClientGUIManageTags.ManageTagsPanel( manage_tags, self._location_context, CC.TAG_PRESENTATION_MEDIA_VIEWER_MANAGE_TAGS, [ self._current_media ], immediate_commit = True, canvas_key = self._canvas_key )
        
        manage_tags.SetPanel( panel )
        
    
    def _ManageTimestamps( self ):
        
        if self._current_media is None:
            
            return
            
        
        ClientGUIMediaModalActions.EditFileTimestamps( self, [ self._current_media ] )
        
    
    def _ManageURLs( self ):
        
        if self._current_media is None:
            
            return
            
        
        title = 'manage known urls'
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, title, frame_key = 'manage_urls_dialog' ) as dlg:
            
            panel = ClientGUIScrolledPanelsEdit.EditURLsPanel( dlg, ( self._current_media, ) )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                pending_content_updates = panel.GetValue()
                
                if len( pending_content_updates ) > 0:
                    
                    content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, pending_content_updates )
                    
                    CG.client_controller.Write( 'content_updates', content_update_package )
                    
                
            
        
    
    def _MediaFocusWentToExternalProgram( self ):
        
        if self._current_media is None:
            
            return
            
        
        if self._current_media.HasDuration():
            
            self._media_container.Pause()
            
        
    
    def _OpenKnownURL( self ):
        
        if self._current_media is not None:
            
            ClientGUIMediaModalActions.DoOpenKnownURLFromShortcut( self, self._current_media )
            
        
    
    def _PrefetchNeighbours( self ):
        
        pass
        
    
    def _SaveCurrentMediaViewTime( self ):
        
        now_ms = HydrusTime.GetNowMS()
        
        view_timestamp_ms = self._current_media_start_time_ms
        
        viewtime_delta_ms = now_ms - self._current_media_start_time_ms
        
        self._current_media_start_time_ms = now_ms
        
        if self._current_media is None:
            
            return
            
        
        CG.client_controller.file_viewing_stats_manager.FinishViewing( self._current_media.GetMediaResult(), self.CANVAS_TYPE, view_timestamp_ms, viewtime_delta_ms )
        
    
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
            
        
        ClientGUIMediaModalActions.UndeleteMedia( self, (self._current_media,) )
        
    
    def CleanBeforeDestroy( self ):
        
        self.ClearMedia()
        
    
    def ClearMedia( self ):
        
        self.SetMedia( None )
        
    
    def BeginDrag( self ):
        
        if self._current_media is not None and self._current_media.HasDuration() and CG.client_controller.new_options.GetBoolean( 'disallow_media_drags_on_duration_media' ):
            
            return
            
        
        point = self.mapFromGlobal( QG.QCursor.pos() )
        
        self._last_drag_pos = point
        self._current_drag_is_touch = False
        
    
    def resizeEvent( self, event ):
        
        my_size = self.size()
        
        if self._current_media is not None:
            
            media_container_size = self._media_container.size()
            
            if my_size != media_container_size:
                
                if self._new_options.GetBoolean( 'media_viewer_lock_current_zoom_type' ):
                    
                    self._media_container.ZoomToZoomType()
                    
                elif self._new_options.GetBoolean( 'media_viewer_lock_current_zoom' ):
                    
                    self._media_container.ZoomMaintainingZoom( self._current_media )
                    
                else:
                    
                    self._media_container.ZoomReinit()
                    
                
                #always reset center on window resize
                #if not self._new_options.GetBoolean( 'media_viewer_lock_current_pan' ):
                
                self._media_container.ResetCenterPosition()
                
                self.EndDrag()
                
            
        
        self.update()
        
    
    def EndDrag( self ):
        
        self._last_drag_pos = None
        
    
    def FlipActiveCustomShortcutName( self, name ):
        
        self._my_shortcuts_handler.FlipShortcuts( name )
        
    
    def GetActiveCustomShortcutNames( self ):
        
        return self._my_shortcuts_handler.GetCustomShortcutNames()
        
    
    def GetColour( self, colour_type ):
        
        if self._new_options.GetBoolean( 'override_stylesheet_colours' ):
            
            return self._new_options.GetColour( colour_type )
            
        else:
            
            return self._qss_colours.get( colour_type, QG.QColor( 127, 127, 127 ) )
            
        
    
    def GetMedia( self ):
        
        return self._current_media
        
    
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
            
        
    
    def NotifyFilesNeedRedraw( self, hashes ):
        
        if self._current_media is not None:
            
            hash = self._current_media.GetHash()
            
            if hash in hashes:
                
                media = self._current_media
                
                self.ClearMedia()
                self.SetMedia( media )
                
            
        
    
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
                
            elif action == CAC.SIMPLE_COPY_FILE_BITMAP:
                
                if self._current_media is None:
                    
                    return
                    
                
                bitmap_type = command.GetSimpleData()
                
                ClientGUIMediaSimpleActions.CopyMediaBitmap( self._current_media, bitmap_type )
                
            elif action == CAC.SIMPLE_COPY_FILES:
                
                if self._current_media is not None:
                    
                    ClientGUIMediaSimpleActions.CopyFilesToClipboard( [ self._current_media ] )
                    
                
            elif action == CAC.SIMPLE_COPY_FILE_ID:
                
                if self._current_media is not None:
                    
                    ClientGUIMediaSimpleActions.CopyFileIdsToClipboard( [ self._current_media ] )
                    
                
            elif action == CAC.SIMPLE_COPY_FILE_PATHS:
                
                if self._current_media is not None:
                    
                    ClientGUIMediaSimpleActions.CopyFilePathsToClipboard( [ self._current_media ] )
                    
                
            elif action == CAC.SIMPLE_COPY_FILE_HASHES:
                
                ( file_command_target, hash_type ) = command.GetSimpleData()
                
                if file_command_target in ( CAC.FILE_COMMAND_TARGET_FOCUSED_FILE, CAC.FILE_COMMAND_TARGET_SELECTED_FILES ):
                    
                    if self._current_media is not None:
                        
                        ClientGUIMediaModalActions.CopyHashesToClipboard( self, hash_type, [ self._current_media ] )
                        
                    
                
            elif action == CAC.SIMPLE_COPY_FILE_SERVICE_FILENAMES:
                
                hacky_ipfs_dict = command.GetSimpleData()
                
                ipfs_service_key = hacky_ipfs_dict[ 'ipfs_service_key' ]
                
                if self._current_media is not None:
                    
                    ClientGUIMediaSimpleActions.CopyServiceFilenamesToClipboard( ipfs_service_key, [ self._current_media ] )
                    
                
            elif action == CAC.SIMPLE_COPY_URLS:
                
                if self._current_media is not None:
                    
                    ClientGUIMediaSimpleActions.CopyMediaURLs( [ self._current_media ] )
                    
                
            elif action == CAC.SIMPLE_DELETE_FILE:
                
                self._Delete()
                
            elif action == CAC.SIMPLE_UNDELETE_FILE:
                
                self._Undelete()
                
            elif action == CAC.SIMPLE_INBOX_FILE:
                
                self._Inbox()
                
            elif action == CAC.SIMPLE_OPEN_FILE_IN_EXTERNAL_PROGRAM:
                
                it_worked = ClientGUIMediaSimpleActions.OpenExternally( self._current_media )
                
                if it_worked:
                    
                    self._MediaFocusWentToExternalProgram()
                    
                
            elif action == CAC.SIMPLE_OPEN_FILE_IN_FILE_EXPLORER:
                
                it_worked = ClientGUIMediaSimpleActions.OpenFileLocation( self._current_media )
                
                if it_worked:
                    
                    self._MediaFocusWentToExternalProgram()
                    
                
            elif action == CAC.SIMPLE_OPEN_FILE_IN_WEB_BROWSER:
                
                it_worked = ClientGUIMediaSimpleActions.OpenInWebBrowser( self._current_media )
                
                if it_worked:
                    
                    self._MediaFocusWentToExternalProgram()
                    
            elif action == CAC.SIMPLE_NATIVE_OPEN_FILE_PROPERTIES:
                
                it_worked = ClientGUIMediaSimpleActions.OpenNativeFileProperties( self._current_media )
                
                if it_worked:
                    
                    self._MediaFocusWentToExternalProgram()
                    
            elif action == CAC.SIMPLE_NATIVE_OPEN_FILE_WITH_DIALOG:
                
                it_worked = ClientGUIMediaSimpleActions.OpenFileWithDialog( self._current_media )
                
                if it_worked:
                    
                    self._MediaFocusWentToExternalProgram()
                    
                
            elif action == CAC.SIMPLE_OPEN_SELECTION_IN_NEW_PAGE:
                
                if self._current_media is not None:
                    
                    hash = self._current_media.GetHash()
                    
                    ClientGUIMediaSimpleActions.ShowFilesInNewPage( [ hash ], self._location_context )
                    
                    self._MediaFocusWentToExternalProgram()
                    
                
            elif action == CAC.SIMPLE_OPEN_SELECTION_IN_NEW_DUPLICATES_FILTER_PAGE:
                
                if self._current_media is not None:
                    
                    hash = self._current_media.GetHash()
                    
                    if CG.client_controller.new_options.GetBoolean( 'open_files_to_duplicate_filter_uses_all_my_files' ):
                        
                        location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY )
                        
                    else:
                        
                        location_context = self._location_context
                        
                    
                    ClientGUIMediaSimpleActions.ShowFilesInNewDuplicatesFilterPage( [ hash ], location_context )
                    
                    self._MediaFocusWentToExternalProgram()
                    
                
            elif action == CAC.SIMPLE_OPEN_SIMILAR_LOOKING_FILES:
                
                if self._current_media is not None:
                    
                    hamming_distance = command.GetSimpleData()
                    
                    if hamming_distance is None:
                        
                        from hydrus.client.gui.panels import ClientGUIScrolledPanels
                        from hydrus.client.gui.widgets import ClientGUICommon
                        
                        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'choose distance' ) as dlg:
                            
                            panel = ClientGUIScrolledPanels.EditSingleCtrlPanel( dlg )
                            
                            #
                            
                            # make a treeview control thing from menu
                            
                            control = ClientGUICommon.BetterSpinBox( panel )
                            
                            control.setSingleStep( 2 )
                            control.setValue( 10 )
                            
                            panel.SetControl( control )
                            
                            dlg.SetPanel( panel )
                            
                            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                                
                                hamming_distance = control.value()
                                
                            else:
                                
                                return
                                
                            
                        
                    
                    ClientGUIMediaSimpleActions.ShowSimilarFilesInNewPage( [ self._current_media ], self._location_context, hamming_distance )
                    
                
            elif action in ( CAC.SIMPLE_EXPORT_FILES, CAC.SIMPLE_EXPORT_FILES_QUICK_AUTO_EXPORT ):
                
                do_export_and_then_quit = action == CAC.SIMPLE_EXPORT_FILES_QUICK_AUTO_EXPORT
                
                if self._current_media is not None:
                    
                    medias = [ self._current_media ]
                    
                    ClientGUIMediaModalActions.ExportFiles( self, medias, do_export_and_then_quit = do_export_and_then_quit )
                    
                
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
                    
                    ClientGUIMediaSimpleActions.ShowDuplicatesInNewPage( self._location_context, hash, duplicate_type )
                    
                
            elif action == CAC.SIMPLE_DUPLICATE_MEDIA_CLEAR_ALL_FOCUSED_FALSE_POSITIVES:
                
                # TODO: when media knows dupe relationships, all these lads here need a media scan for the existence of alternate groups or whatever
                # no duplicate group->don't start the process
                
                if self._current_media is not None:
                    
                    hash = self._current_media.GetHash()
                    
                    ClientGUIDuplicateActions.ClearAllFalsePositives( self, ( hash, ) )
                    
                
            elif action == CAC.SIMPLE_DUPLICATE_MEDIA_CLEAR_ALL_FALSE_POSITIVES:
                
                if self._current_media is not None:
                    
                    hash = self._current_media.GetHash()
                    
                    ClientGUIDuplicateActions.ClearAllFalsePositives( self, ( hash, ) )
                    
                
            elif action == CAC.SIMPLE_DUPLICATE_MEDIA_DISSOLVE_FOCUSED_ALTERNATE_GROUP:
                
                if self._current_media is not None:
                    
                    hash = self._current_media.GetHash()
                    
                    ClientGUIDuplicateActions.DissolveAlternateGroup( self, ( hash, ) )
                    
                
            elif action == CAC.SIMPLE_DUPLICATE_MEDIA_DISSOLVE_ALTERNATE_GROUP:
                
                if self._current_media is not None:
                    
                    hash = self._current_media.GetHash()
                    
                    ClientGUIDuplicateActions.DissolveAlternateGroup( self, ( hash, ) )
                    
                
            elif action == CAC.SIMPLE_DUPLICATE_MEDIA_DISSOLVE_FOCUSED_DUPLICATE_GROUP:
                
                if self._current_media is not None:
                    
                    hash = self._current_media.GetHash()
                    
                    ClientGUIDuplicateActions.DissolveDuplicateGroup( self, ( hash, ) )
                    
                
            elif action == CAC.SIMPLE_DUPLICATE_MEDIA_DISSOLVE_DUPLICATE_GROUP:
                
                if self._current_media is not None:
                    
                    hash = self._current_media.GetHash()
                    
                    ClientGUIDuplicateActions.DissolveDuplicateGroup( self, ( hash, ) )
                    
                
            elif action == CAC.SIMPLE_DUPLICATE_MEDIA_REMOVE_FOCUSED_FROM_ALTERNATE_GROUP:
                
                if self._current_media is not None:
                    
                    hash = self._current_media.GetHash()
                    
                    ClientGUIDuplicateActions.RemoveFromAlternateGroup( self, ( hash, ) )
                    
                
            elif action == CAC.SIMPLE_DUPLICATE_MEDIA_REMOVE_FOCUSED_FROM_DUPLICATE_GROUP:
                
                if self._current_media is not None:
                    
                    hash = self._current_media.GetHash()
                    
                    ClientGUIDuplicateActions.RemoveFromDuplicateGroup( self, ( hash, ) )
                    
                
            elif action == CAC.SIMPLE_DUPLICATE_MEDIA_RESET_FOCUSED_POTENTIAL_SEARCH:
                
                if self._current_media is not None:
                    
                    hash = self._current_media.GetHash()
                    
                    ClientGUIDuplicateActions.ResetPotentialSearch( self, ( hash, ) )
                    
                
            elif action == CAC.SIMPLE_DUPLICATE_MEDIA_RESET_POTENTIAL_SEARCH:
                
                if self._current_media is not None:
                    
                    hash = self._current_media.GetHash()
                    
                    ClientGUIDuplicateActions.ResetPotentialSearch( self, ( hash, ) )
                    
                
            elif action == CAC.SIMPLE_DUPLICATE_MEDIA_REMOVE_FOCUSED_POTENTIALS:
                
                if self._current_media is not None:
                    
                    hash = self._current_media.GetHash()
                    
                    ClientGUIDuplicateActions.RemovePotentials( self, ( hash, ) )
                    
                
            elif action == CAC.SIMPLE_DUPLICATE_MEDIA_REMOVE_POTENTIALS:
                
                if self._current_media is not None:
                    
                    hash = self._current_media.GetHash()
                    
                    ClientGUIDuplicateActions.RemovePotentials( self, ( hash, ) )
                    
                
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
                
            elif action == CAC.SIMPLE_RESET_PAN_TO_CENTER:
                
                self._media_container.ResetCenterPosition()
                
            elif action == CAC.SIMPLE_RESIZE_WINDOW_TO_MEDIA:
                
                self._media_container.SizeSelfToMedia()
                
            elif action == CAC.SIMPLE_RESIZE_WINDOW_TO_MEDIA_VIEWER_CENTER:
            
                self._media_container.SizeSelfToMedia()
                
                self._media_container.ResetCenterPosition()
                
            elif action == CAC.SIMPLE_RESIZE_WINDOW_TO_MEDIA_ZOOMED:
                
                new_zoom = command.GetSimpleData()
                
                self._media_container.ZoomToZoomPercent( new_zoom )
                
                self._media_container.SizeSelfToMedia()
                
            elif action == CAC.SIMPLE_RESIZE_WINDOW_TO_MEDIA_ZOOMED_VIEWER_CENTER:
                
                new_zoom = command.GetSimpleData()
                
                self._media_container.ZoomToZoomPercent( new_zoom, zoom_center_type_override = ClientGUICanvasMedia.ZOOM_CENTERPOINT_VIEWER_CENTER )
                
                self._media_container.SizeSelfToMedia()
                
                self._media_container.ResetCenterPosition()
                
            elif action == CAC.SIMPLE_SWITCH_BETWEEN_100_PERCENT_AND_CANVAS_ZOOM:
                
                self._media_container.ZoomSwitch()
                
            elif action == CAC.SIMPLE_SWITCH_BETWEEN_100_PERCENT_AND_CANVAS_ZOOM_VIEWER_CENTER:
                
                self._media_container.ZoomSwitch( zoom_center_type_override = ClientGUICanvasMedia.ZOOM_CENTERPOINT_VIEWER_CENTER )
                
            elif action == CAC.SIMPLE_SWITCH_BETWEEN_100_PERCENT_AND_CANVAS_FIT_AND_FILL_ZOOM:
                
                self._media_container.ZoomSwitchCanvasThenFill()
                
            elif action == CAC.SIMPLE_SWITCH_BETWEEN_100_PERCENT_AND_CANVAS_FIT_AND_FILL_ZOOM_VIEWER_CENTER :
                
                self._media_container.ZoomSwitchCanvasThenFill( zoom_center_type_override = ClientGUICanvasMedia.ZOOM_CENTERPOINT_VIEWER_CENTER )
                
            elif action == CAC.SIMPLE_SWITCH_BETWEEN_100_PERCENT_AND_MAX_ZOOM:
                
                self._media_container.ZoomSwitch100Max()
                
            elif action == CAC.SIMPLE_SWITCH_BETWEEN_CANVAS_AND_MAX_ZOOM:
                
                self._media_container.ZoomSwitchCanvasMax()
                
            elif action == CAC.SIMPLE_ZOOM_100:
                
                self._media_container.Zoom100()
                
            elif action == CAC.SIMPLE_ZOOM_100_CENTER:
                
                self._media_container.Zoom100( zoom_center_type_override = ClientGUICanvasMedia.ZOOM_CENTERPOINT_VIEWER_CENTER )
                
            elif action == CAC.SIMPLE_ZOOM_CANVAS:
                
                self._media_container.ZoomCanvas()
                
            elif action == CAC.SIMPLE_ZOOM_CANVAS_VIEWER_CENTER:
                
                self._media_container.ZoomCanvas( zoom_center_type_override = ClientGUICanvasMedia.ZOOM_CENTERPOINT_VIEWER_CENTER )
                
            elif action == CAC.SIMPLE_ZOOM_CANVAS_FILL_X:
                
                self._media_container.ZoomCanvasFillX()
                
            elif action == CAC.SIMPLE_ZOOM_CANVAS_FILL_X_VIEWER_CENTER:
                
                self._media_container.ZoomCanvasFillX( zoom_center_type_override = ClientGUICanvasMedia.ZOOM_CENTERPOINT_VIEWER_CENTER )
                
            elif action == CAC.SIMPLE_ZOOM_CANVAS_FILL_Y:
                
                self._media_container.ZoomCanvasFillY()
                
            elif action == CAC.SIMPLE_ZOOM_CANVAS_FILL_Y_VIEWER_CENTER:
                
                self._media_container.ZoomCanvasFillY( zoom_center_type_override = ClientGUICanvasMedia.ZOOM_CENTERPOINT_VIEWER_CENTER )
                
            elif action == CAC.SIMPLE_ZOOM_CANVAS_FILL_AUTO:
                
                self._media_container.ZoomCanvasFillAuto()
                
            elif action == CAC.SIMPLE_ZOOM_CANVAS_FILL_AUTO_VIEWER_CENTER:
                
                self._media_container.ZoomCanvasFillAuto( zoom_center_type_override = ClientGUICanvasMedia.ZOOM_CENTERPOINT_VIEWER_CENTER )
                
            elif action == CAC.SIMPLE_ZOOM_DEFAULT:
                
                self._media_container.ZoomDefault()
                
            elif action == CAC.SIMPLE_ZOOM_DEFAULT_VIEWER_CENTER:
                
                self._media_container.ZoomDefault( zoom_center_type_override = ClientGUICanvasMedia.ZOOM_CENTERPOINT_VIEWER_CENTER )
                
            elif action == CAC.SIMPLE_ZOOM_MAX:
                
                self._media_container.ZoomMax()
                
            elif action == CAC.SIMPLE_ZOOM_TO_PERCENTAGE:
                
                new_zoom = command.GetSimpleData()
                
                self._media_container.ZoomToZoomPercent( new_zoom )
                
            elif action == CAC.SIMPLE_ZOOM_TO_PERCENTAGE_CENTER:
                                                        
                new_zoom = command.GetSimpleData()
                
                self._media_container.ZoomToZoomPercent( new_zoom, zoom_center_type_override = ClientGUICanvasMedia.ZOOM_CENTERPOINT_VIEWER_CENTER )
                
            elif action == CAC.SIMPLE_FLIP_ICC_PROFILE_APPLICATION:
                
                result = CG.client_controller.new_options.FlipBoolean( 'do_icc_profile_normalisation' )
                
                from hydrus.core.files.images import HydrusImageNormalisation
                
                HydrusImageNormalisation.SetDoICCProfileNormalisation( result )
                
            else:
                
                command_processed = False
                
            
        elif command.IsContentCommand():
            
            if self._current_media is None:
                
                return
                
            
            command_processed = ClientGUIMediaModalActions.ApplyContentApplicationCommandToMedia( self, command, (self._current_media,) )
            
        else:
            
            command_processed = False
            
        
        return command_processed
        
    
    def ResetMediaWindowCenterPosition( self ):
        
        self._media_container.ResetCenterPosition()
        
        self.EndDrag()
        
    
    def SetLocationContext( self, location_context: ClientLocation.LocationContext ):
        
        self._location_context = location_context
        
    
    def SetMedia( self, media: typing.Optional[ ClientMedia.MediaSingleton ], start_paused = None ):
        
        if media is not None and not self.isVisible():
            
            return
            
        
        if media is not None:
            
            media = media.GetDisplayMedia()
            
            if not ClientMedia.CanDisplayMedia( media ):
                
                media = None
                
            
        
        if media is not None:
            
            if self.CANVAS_TYPE == CC.CANVAS_PREVIEW:
                
                if not ClientMedia.UserWantsUsToDisplayMedia( media.GetMediaResult(), self.CANVAS_TYPE ):
                    
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
                
                if self._current_media.GetLocationsManager().IsLocal():
                    
                    maintain_zoom = False
                    maintain_zoom_type = False
                    maintain_pan = False
                    
                    if self._force_maintain_pan_and_zoom:
                        
                        maintain_zoom = True
                        maintain_pan = True
                        
                    elif self.CANVAS_TYPE in CC.CANVAS_MEDIA_VIEWER_TYPES:
                        
                        maintain_zoom = self._new_options.GetBoolean( 'media_viewer_lock_current_zoom' )
                        maintain_zoom_type = not maintain_zoom and self._new_options.GetBoolean( 'media_viewer_lock_current_zoom_type' )
                        maintain_pan = self._new_options.GetBoolean( 'media_viewer_lock_current_pan' )
                        
                    
                    self._media_container.SetMedia( self._current_media, maintain_zoom, maintain_zoom_type, maintain_pan, start_paused = start_paused )
                    
                else:
                    
                    self._current_media = None
                    
                
            
            if self._current_media is None:
                
                self.mediaCleared.emit()
                
            elif isinstance( self._current_media, ClientMedia.MediaSingleton ): # just to be safe on the delicate type def requirements here
                
                self.mediaChanged.emit( self._current_media )
                
            
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
            
        
    
    def get_hmv_background( self ):
        
        return self._qss_colours[ CC.COLOUR_MEDIA_BACKGROUND ]
        
    
    def get_hmv_text( self ):
        
        return self._qss_colours[ CC.COLOUR_MEDIA_TEXT ]
        
    
    def set_hmv_background( self, colour ):
        
        self._qss_colours[ CC.COLOUR_MEDIA_BACKGROUND ] = colour
        
    
    def set_hmv_text( self, colour ):
        
        self._qss_colours[ CC.COLOUR_MEDIA_TEXT ] = colour
        
    
    hmv_background = QC.Property( QG.QColor, get_hmv_background, set_hmv_background )
    hmv_text = QC.Property( QG.QColor, get_hmv_text, set_hmv_text )
    

class MediaContainerDragClickReportingFilter( QC.QObject ):
    
    def __init__( self, parent: Canvas ):
        
        super().__init__( parent )
        
        self._canvas = parent
        
    
    def eventFilter( self, watched, event ):
        
        try:
            
            if event.type() == QC.QEvent.Type.MouseButtonPress:
                
                event = typing.cast( QG.QMouseEvent, event )
                
                if event.button() == QC.Qt.MouseButton.LeftButton:
                    
                    self._canvas.BeginDrag()
                    
                
            elif event.type() == QC.QEvent.Type.MouseButtonRelease:
                
                event = typing.cast( QG.QMouseEvent, event )
                
                if event.button() == QC.Qt.MouseButton.LeftButton:
                    
                    self._canvas.EndDrag()
                    
                
            
        except Exception as e:
            
            HydrusData.ShowException( e )
            
            return True
            
        
        return False
        
    
class CanvasPanel( Canvas ):
    
    launchMediaViewer = QC.Signal()
    
    CANVAS_TYPE = CC.CANVAS_PREVIEW
    
    def __init__( self, parent, page_key, location_context: ClientLocation.LocationContext ):
        
        super().__init__( parent, location_context )
        
        self._canvas_type = CC.CANVAS_PREVIEW
        self._page_key = page_key
        
        self._hidden_page_current_media = None
        self._hidden_page_paused_status = False
        
        self._is_splitter_hidden = False
        
        self._media_container.launchMediaViewer.connect( self.launchMediaViewer )
        
        CG.client_controller.sub( self, 'ProcessContentUpdatePackage', 'content_updates_gui' )
        
    
    def mouseReleaseEvent( self, event ):
        
        if event.button() != QC.Qt.MouseButton.RightButton:
            
            Canvas.mouseReleaseEvent( self, event )
            
            return
            
        
        # contextmenu doesn't quite work here yet due to focus issues
        
        self.ShowMenu()
        
    
    def ClearMedia( self ):
        
        self._hidden_page_current_media = None
        self._hidden_splitter_current_media = None
        
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
        
        self.SetMedia( self._hidden_page_current_media, start_paused = self._hidden_page_paused_status )
        
        self._hidden_page_current_media = None
        
    
    def ShowMenu( self ):
        
        menu = ClientGUIMenus.GenerateMenu( self )
        
        if self._current_media is not None:
            
            services = CG.client_controller.services_manager.GetServices()
            
            locations_manager = self._current_media.GetLocationsManager()
            
            local_ratings_services = [ service for service in services if service.GetServiceType() in HC.RATINGS_SERVICES ]
            
            i_can_post_ratings = len( local_ratings_services ) > 0
            
            #
            
            info_lines = ClientMediaResultPrettyInfo.GetPrettyMediaResultInfoLines( self._current_media.GetMediaResult() )
            
            info_menu = ClientGUIMenus.GenerateMenu( menu )
            
            ClientGUIMediaMenus.AddPrettyMediaResultInfoLines( info_menu, info_lines )
            
            ClientGUIMediaMenus.AddFileViewingStatsMenu( info_menu, (self._current_media,) )
            
            filetype_summary = ClientMedia.GetMediasFiletypeSummaryString( [ self._current_media ] )
            size_summary = HydrusData.ToHumanBytes( self._current_media.GetSize() )
            
            info_summary = f'{filetype_summary}, {size_summary}'
            
            ClientGUIMenus.AppendMenu( menu, info_menu, info_summary )
            
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
                
            
            num_notes = self._current_media.GetNotesManager().GetNumNotes()
            
            notes_str = 'notes'
            
            if num_notes > 0:
                
                notes_str = '{} ({})'.format( notes_str, HydrusNumbers.ToHumanInt( num_notes ) )
                
            
            ClientGUIMenus.AppendMenuItem( manage_menu, notes_str, 'Manage this file\'s notes.', self._ManageNotes )
            
            ClientGUIMenus.AppendMenuItem( manage_menu, 'times', 'Edit the timestamps for your files.', self._ManageTimestamps )
            ClientGUIMenus.AppendMenuItem( manage_menu, 'force filetype', 'Force your files to appear as a different filetype.', ClientGUIMediaModalActions.SetFilesForcedFiletypes, self, [ self._current_media ] )
            
            ClientGUIMediaMenus.AddManageFileViewingStatsMenu( self, manage_menu, [ self._current_media ] )
            
            ClientGUIMenus.AppendMenu( menu, manage_menu, 'manage' )
            
            ClientGUIMediaMenus.AddKnownURLsViewCopyMenu( self, self, menu, self._current_media, 1 )
            
            ClientGUIMediaMenus.AddOpenMenu( self, self, menu, self._current_media, [ self._current_media ] )
            
            ClientGUIMediaMenus.AddShareMenu( self, self, menu, self._current_media, [ self._current_media ] )
            
        
        CGC.core().PopupMenu( self, menu )
        
    
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
                
            
        
    
    def SetMedia( self, media, start_paused = None ):
        
        if HC.options[ 'hide_preview' ] or self._is_splitter_hidden or ( media is not None and not self.isVisible() ):
            
            return
            
        
        Canvas.SetMedia( self, media, start_paused = start_paused )
        
    
    def SetSplitterHiddenStatus( self, is_hidden ):
        
        # TODO: this is whack. I should fold all this into the pagehidden/shown system, I think?
        # rather than saving that status, I should have a freeze/restore stack or similar, and it should probably be handled at the media container level, not the canvas bruh
        
        if is_hidden and not self._is_splitter_hidden:
            
            # we are hiding
            
            self.ClearMedia()
            
        elif self._is_splitter_hidden and not is_hidden:
            
            # we are showing again. I could do a restore status thing like I have for pagehidden/shown in future, but for now this is a nice simple thing
            
            pass
            
        
        self._is_splitter_hidden = is_hidden
        
    

class CanvasPanelWithHovers( CanvasPanel ):
    
    def __init__( self, parent, page_key, location_context: ClientLocation.LocationContext ):
        
        self._canvas_type = CC.CANVAS_PREVIEW
        
        super().__init__( parent, page_key, location_context )
        
        #
        
        self._hovers = []
        
        self._top_right_hover = ClientGUICanvasHoverFrames.CanvasHoverFrameTopRight( self, self, None, self._canvas_key )
        
        self.mediaChanged.connect( self._top_right_hover.SetMedia )
        self.mediaCleared.connect( self._top_right_hover.ClearMedia )
        
        self._top_right_hover.sendApplicationCommand.connect( self.ProcessApplicationCommand )
        
        self._hovers.append( self._top_right_hover )
        
        #
        
        self._my_shortcuts_handler.AddWindowToFilter( self._top_right_hover )
        
        CG.client_controller.gui.RegisterUIUpdateWindow( self )
        
    
    def _DrawBackgroundDetails( self, painter: QG.QPainter ):
        
        if self._current_media is None:
            
            # maybe we'll want something here, but I think I prefer it blank for default for now
            pass
            
            '''
            my_size = self.size()
            
            my_width = my_size.width()
            my_height = my_size.height()
            
            text = 'No media selected'
            
            ( text_size, text ) = ClientGUIFunctions.GetTextSizeFromPainter( painter, text )
            
            x = ( my_width - text_size.width() ) // 2
            y = ( my_height - text_size.height() ) // 2
            
            ClientGUIFunctions.DrawText( painter, x, y, text )
            '''
        else: #TODO maybe implement some of the commented out options with custom draw for sizes / overlapping shiz / +"bottom info" bar to preview window with extended details?
            
            new_options = CG.client_controller.new_options
            
            # if new_options.GetBoolean( 'draw_tags_hover_in_preview_window_background' ):
                
            #     self._DrawTags( painter )
                
            
            # if new_options.GetBoolean( 'draw_top_hover_in_preview_window_background' ):
                
            #     self._DrawTopMiddle( painter )
                
            
            if new_options.GetBoolean( 'draw_top_right_hover_in_preview_window_background' ):
                
                current_y = self._DrawTopRight( painter )
                
            # else:
                
            #     current_y = 0
                
            
            # if new_options.GetBoolean( 'draw_notes_hover_in_preview_window_background' ):
                
            #     self._DrawNotes( painter, current_y )
                
            
            # if new_options.GetBoolean( 'draw_bottom_right_index_in_preview_window_background' ):
                
            #     self._DrawIndexAndZoom( painter )
                
            
        
    
    def _DrawTopRight( self, painter: QG.QPainter ) -> int:
        
        my_size = self.size()
        
        my_width = my_size.width()
        my_height = my_size.height()
        
        try:
            
            QFRAME_PADDING = self._top_right_hover.frameWidth()
            
            ( VBOX_SPACING, VBOX_MARGIN ) = self._top_right_hover.GetVboxSpacingAndMargin()
            
        except:
            
            QFRAME_PADDING = 2
            ( VBOX_SPACING, VBOX_MARGIN ) = ( 2, 2 )
            
        
        current_y = QFRAME_PADDING + VBOX_MARGIN + round( ClientGUIPainterShapes.PAD_PX / 2 )
        
        # ratings
        
        RATING_ICON_SET_SIZE = round( self._new_options.GetFloat( 'preview_window_rating_icon_size_px' ) )
        RATING_INCDEC_SET_WIDTH = round( self._new_options.GetFloat( 'preview_window_rating_incdec_width_px' ) )
        STAR_DX = RATING_ICON_SET_SIZE
        STAR_DY = RATING_ICON_SET_SIZE
        STAR_PAD = ClientGUIPainterShapes.PAD
        
        services_manager = CG.client_controller.services_manager
        
        
        like_services = services_manager.GetServices( ( HC.LOCAL_RATING_LIKE, ) )
        
        like_services.reverse()
        
        like_rating_current_x = my_width - ( STAR_DX + round( STAR_PAD.width() / 2 ) ) - ( QFRAME_PADDING + VBOX_MARGIN )
        
        for like_service in like_services:
            
            service_key = like_service.GetServiceKey()
            
            rating_state = ClientRatings.GetLikeStateFromMedia( ( self._current_media, ), service_key )
            
            ClientGUIRatings.DrawLike( painter, like_rating_current_x, current_y, service_key, rating_state, QC.QSize( STAR_DX, STAR_DY ))
            
            like_rating_current_x -= STAR_DX + STAR_PAD.width()
            
        
        if len( like_services ) > 0:
            
            current_y += STAR_DY + STAR_PAD.height() + VBOX_SPACING
            
        
        
        numerical_services = services_manager.GetServices( ( HC.LOCAL_RATING_NUMERICAL, ) )
        
        for numerical_service in numerical_services:
            
            service_key = numerical_service.GetServiceKey()
            
            custom_pad = numerical_service.GetCustomPad()
            
            ( rating_state, rating ) = ClientRatings.GetNumericalStateFromMedia( ( self._current_media, ), service_key )
            
            numerical_width = ClientGUIRatings.GetNumericalWidth( service_key, RATING_ICON_SET_SIZE, custom_pad, False, rating_state, rating )
            
            current_x = my_width - numerical_width - ( QFRAME_PADDING + VBOX_MARGIN ) + round( STAR_PAD.width() / 2 )
            
            ClientGUIRatings.DrawNumerical( painter, current_x, current_y, service_key, rating_state, rating, QC.QSize( STAR_DX, STAR_DY ), custom_pad )
            
            current_y += STAR_DY + STAR_PAD.height() + VBOX_SPACING
            
        
        
        incdec_services = services_manager.GetServices( ( HC.LOCAL_RATING_INCDEC, ) )
        
        incdec_services.reverse()
        
        control_width = RATING_INCDEC_SET_WIDTH + 1
        
        incdec_rating_current_x = my_width - ( control_width ) - ( QFRAME_PADDING + VBOX_MARGIN )
        
        for incdec_service in incdec_services:
            
            service_key = incdec_service.GetServiceKey()
            
            ( rating_state, rating ) = ClientRatings.GetIncDecStateFromMedia( ( self._current_media, ), service_key )
            
            ClientGUIRatings.DrawIncDec( painter, incdec_rating_current_x, current_y, service_key, rating_state, rating, QC.QSize( round( RATING_INCDEC_SET_WIDTH ), round( RATING_INCDEC_SET_WIDTH / 2 ) ) )
            
            incdec_rating_current_x -= control_width    #+ STAR_PAD.width() #instead of spacing these out, we will just have them pixel-adjacent in all cases
            
        
        if len( incdec_services ) > 0:
            
            current_y += round( RATING_INCDEC_SET_WIDTH / 2 ) + round( STAR_PAD.height() / 2 ) + VBOX_SPACING
            
        
        # icons
        
        icons_to_show = []
        
        if self._current_media.GetLocationsManager().IsTrashed():
            
            icons_to_show.append( CC.global_pixmaps().trash )
            
        
        if self._current_media.HasInbox():
            
            icons_to_show.append( CC.global_pixmaps().inbox )
            
        
        if len( icons_to_show ) > 0:
            
            current_y += VBOX_MARGIN
            
            icon_x = - ( QFRAME_PADDING + VBOX_MARGIN )
            
            for icon in icons_to_show:
                
                painter.drawPixmap( my_width + icon_x - ( 16 + VBOX_SPACING ), current_y, icon )
                
                icon_x -= 16 + VBOX_SPACING
                
            
            # this appears to be correct for the wrong reasons
            
            current_y += 16 + VBOX_SPACING
            
            current_y += VBOX_MARGIN
            
        
        pen_colour = self.GetColour( CC.COLOUR_MEDIA_TEXT )
        
        painter.setPen( QG.QPen( pen_colour ) )
        
        # location strings
        
        location_strings = self._current_media.GetLocationsManager().GetLocationStrings()
        
        for location_string in location_strings:
            
            ( text_size, location_string ) = ClientGUIFunctions.GetTextSizeFromPainter( painter, location_string )
            
            ClientGUIFunctions.DrawText( painter, my_width - ( text_size.width() + QFRAME_PADDING + VBOX_MARGIN ), current_y, location_string )
            
            current_y += text_size.height()
            
        
        # urls
        
        urls = self._current_media.GetLocationsManager().GetURLs()
        
        url_tuples = CG.client_controller.network_engine.domain_manager.ConvertURLsToMediaViewerTuples( urls )
        
        if len( url_tuples ) > 0:
            
            current_y += VBOX_MARGIN
            
            for ( display_string, url ) in url_tuples:
                
                ( text_size, display_string ) = ClientGUIFunctions.GetTextSizeFromPainter( painter, display_string )
                
                ClientGUIFunctions.DrawText( painter, my_width - ( text_size.width() + QFRAME_PADDING + VBOX_MARGIN ), current_y, display_string )
                
                current_y += text_size.height() + VBOX_SPACING
                
            
            # again this appears to be correct but for the wrong reasons
            # flying completely by my pants here
            
            current_y -= VBOX_MARGIN
            
        
        current_y += VBOX_MARGIN + QFRAME_PADDING
        
        return current_y
        
    
    def GetCanvasType( self ):
        
        return self._canvas_type
        
    def TIMERUIUpdate( self ):
        
        for hover in self._hovers:
            
            hover.DoRegularHideShow()
            
        
    

class CanvasWithHovers( Canvas ):
    
    canvasWithHoversExiting = QC.Signal()
    
    def __init__( self, parent, location_context ):
        
        super().__init__( parent, location_context )
        
        self._hovers = []
        
        top_hover = self._GenerateHoverTopFrame()
        
        self.mediaChanged.connect( top_hover.SetMedia )
        self.mediaCleared.connect( top_hover.ClearMedia )
        
        top_hover.sendApplicationCommand.connect( self.ProcessApplicationCommand )
        
        self._media_container.zoomChanged.connect( top_hover.SetCurrentZoom )
        
        self._hovers.append( top_hover )
        
        self._my_shortcuts_handler.AddWindowToFilter( top_hover )
        
        self._tags_hover = ClientGUICanvasHoverFrames.CanvasHoverFrameTags( self, self, top_hover, self._canvas_key, self._location_context )
        
        self.mediaChanged.connect( self._tags_hover.SetMedia )
        self.mediaCleared.connect( self._tags_hover.ClearMedia )
        
        self._tags_hover.sendApplicationCommand.connect( self.ProcessApplicationCommand )
        
        self._hovers.append( self._tags_hover )
        
        self._my_shortcuts_handler.AddWindowToFilter( self._tags_hover )
        
        self._top_right_hover = ClientGUICanvasHoverFrames.CanvasHoverFrameTopRight( self, self, top_hover, self._canvas_key )
        
        self.mediaChanged.connect( self._top_right_hover.SetMedia )
        self.mediaCleared.connect( self._top_right_hover.ClearMedia )
        
        self._top_right_hover.sendApplicationCommand.connect( self.ProcessApplicationCommand )
        
        self._hovers.append( self._top_right_hover )
        
        self._my_shortcuts_handler.AddWindowToFilter( self._top_right_hover )
        
        self._right_notes_hover = ClientGUICanvasHoverFrames.CanvasHoverFrameRightNotes( self, self, self._top_right_hover, self._canvas_key )
        
        self.mediaChanged.connect( self._right_notes_hover.SetMedia )
        self.mediaCleared.connect( self._right_notes_hover.ClearMedia )
        
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
        
        CG.client_controller.sub( self, 'RedrawDetails', 'refresh_all_tag_presentation_gui' )
        CG.client_controller.sub( self, 'CloseFromHover', 'canvas_close' )
        CG.client_controller.sub( self, 'FullscreenSwitch', 'canvas_fullscreen_switch' )
        
        CG.client_controller.gui.RegisterUIUpdateWindow( self )
        
    
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
            
            new_options = CG.client_controller.new_options
            
            if new_options.GetBoolean( 'draw_tags_hover_in_media_viewer_background' ):
                
                self._DrawTags( painter )
                
            
            if new_options.GetBoolean( 'draw_top_hover_in_media_viewer_background' ):
                
                self._DrawTopMiddle( painter )
                
            
            if new_options.GetBoolean( 'draw_top_right_hover_in_media_viewer_background' ):
                
                current_y = self._DrawTopRight( painter )
                
            else:
                
                # ah this is actually wrong, bleargh
                current_y = 0
                
            
            if new_options.GetBoolean( 'draw_notes_hover_in_media_viewer_background' ):
                
                self._DrawNotes( painter, current_y )
                
            
            if new_options.GetBoolean( 'draw_bottom_right_index_in_media_viewer_background' ):
                
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
        
        try:
            
            QFRAME_PADDING = self._right_notes_hover.frameWidth()
            
            ( NOTE_SPACING, NOTE_MARGIN ) = self._right_notes_hover.GetNoteSpacingAndMargin()
            
        except:
            
            QFRAME_PADDING = 2
            ( NOTE_SPACING, NOTE_MARGIN ) = ( 2, 2 )
            
        
        notes_width = int( my_width * ClientGUICanvasHoverFrames.SIDE_HOVER_PROPORTIONS ) - ( ( QFRAME_PADDING + NOTE_MARGIN ) * 2 )
        
        painter.save()
        
        try:
            
            original_font = painter.font()
            
            name_font = QG.QFont( original_font )
            name_font.setBold( True )
            
            notes_font = QG.QFont( original_font )
            notes_font.setBold( False )
            
            # old code that tried to draw it to a smaller box
            '''
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
                    
                
            '''
            
            left_x = my_width - ( notes_width + QFRAME_PADDING + NOTE_MARGIN )
            
            current_y += QFRAME_PADDING + NOTE_MARGIN
            
            draw_a_test_rect = False
            
            if draw_a_test_rect:
                
                painter.setPen( QG.QPen( QG.QColor( 20, 20, 20 ) ) )
                painter.setBrush( QC.Qt.BrushStyle.NoBrush )
                
                painter.drawRect( left_x, current_y, notes_width, 100 )
                
            
            for name in sorted( names_to_notes.keys() ):
                
                current_y += NOTE_MARGIN
                
                painter.setFont( name_font )
                
                text_rect = painter.fontMetrics().boundingRect( left_x, current_y, notes_width, 100, QC.Qt.AlignmentFlag.AlignHCenter | QC.Qt.TextFlag.TextWordWrap, name )
                
                painter.drawText( text_rect, QC.Qt.AlignmentFlag.AlignHCenter | QC.Qt.TextFlag.TextWordWrap, name )
                
                current_y += text_rect.height() + NOTE_SPACING
                
                #
                
                painter.setFont( notes_font )
                
                note = notes_manager.GetNote( name )
                
                text_rect = painter.fontMetrics().boundingRect( left_x, current_y, notes_width, 100, QC.Qt.AlignmentFlag.AlignJustify | QC.Qt.TextFlag.TextWordWrap, note )
                
                # this is important to make sure the justify does fill the available space, rather than the above bounding rect, which is the minimum width using justify
                text_rect.setWidth( notes_width )
                
                painter.drawText( text_rect, QC.Qt.AlignmentFlag.AlignJustify | QC.Qt.TextFlag.TextWordWrap, note )
                
                current_y += text_rect.height()
                
                current_y += NOTE_MARGIN
                
                if current_y >= my_height:
                    
                    break
                    
                
            
        finally:
            
            painter.restore()
            
        
    
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
        
        tag_sort = CG.client_controller.new_options.GetDefaultTagSort( CC.TAG_PRESENTATION_MEDIA_VIEWER )
        
        ClientTagSorting.SortTags( tag_sort, tags_i_want_to_display )
        
        namespace_colours = HC.options[ 'namespace_colours' ]
        
        try:
            
            QFRAME_PADDING = self._right_notes_hover.frameWidth()
            
        except:
            
            QFRAME_PADDING = 2
            
        
        current_y = QFRAME_PADDING + 3
        
        x = QFRAME_PADDING + 5
        
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
            
            ClientGUIFunctions.DrawText( painter, x, current_y, display_string )
            
            current_y += text_size.height()
            
        
        painter.setPen( original_pen )
        
    
    def _DrawTopMiddle( self, painter: QG.QPainter ):
        
        my_size = self.size()
        
        my_width = my_size.width()
        my_height = my_size.height()
        
        # top-middle
        
        pen_colour = self.GetColour( CC.COLOUR_MEDIA_TEXT )
        
        painter.setPen( QG.QPen( pen_colour ) )
        
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
        
        try:
            
            QFRAME_PADDING = self._top_right_hover.frameWidth()
            
            ( VBOX_SPACING, VBOX_MARGIN ) = self._top_right_hover.GetVboxSpacingAndMargin()
            
        except:
            
            QFRAME_PADDING = 2
            ( VBOX_SPACING, VBOX_MARGIN ) = ( 2, 2 )
            
        
        current_y = QFRAME_PADDING + VBOX_MARGIN + round( ClientGUIPainterShapes.PAD_PX / 2 )
        
        # ratings
        
        RATING_ICON_SET_SIZE = round( self._new_options.GetFloat( 'media_viewer_rating_icon_size_px' ) )
        RATING_INCDEC_SET_WIDTH = round( self._new_options.GetFloat( 'media_viewer_rating_incdec_width_px' ) )
        STAR_DX = RATING_ICON_SET_SIZE
        STAR_DY = RATING_ICON_SET_SIZE
        STAR_PAD = ClientGUIPainterShapes.PAD
        
        services_manager = CG.client_controller.services_manager
        
        
        like_services = services_manager.GetServices( ( HC.LOCAL_RATING_LIKE, ) )
        
        like_services.reverse()
        
        like_rating_current_x = my_width - ( STAR_DX + round( STAR_PAD.width() / 2 ) ) - ( QFRAME_PADDING + VBOX_MARGIN )
        
        for like_service in like_services:
            
            service_key = like_service.GetServiceKey()
            
            rating_state = ClientRatings.GetLikeStateFromMedia( ( self._current_media, ), service_key )
            
            ClientGUIRatings.DrawLike( painter, like_rating_current_x, current_y, service_key, rating_state, QC.QSize( STAR_DX, STAR_DY ))
            
            like_rating_current_x -= STAR_DX + STAR_PAD.width()
            
        
        if len( like_services ) > 0:
            
            current_y += STAR_DY + STAR_PAD.height() + VBOX_SPACING
            
        
        
        numerical_services = services_manager.GetServices( ( HC.LOCAL_RATING_NUMERICAL, ) )
        
        for numerical_service in numerical_services:
            
            service_key = numerical_service.GetServiceKey()
            
            custom_pad = numerical_service.GetCustomPad()
            
            ( rating_state, rating ) = ClientRatings.GetNumericalStateFromMedia( ( self._current_media, ), service_key )
            
            numerical_width = ClientGUIRatings.GetNumericalWidth( service_key, RATING_ICON_SET_SIZE, custom_pad, False, rating_state, rating )
            
            current_x = my_width - numerical_width - ( QFRAME_PADDING + VBOX_MARGIN ) + round( STAR_PAD.width() / 2 )
            
            ClientGUIRatings.DrawNumerical( painter, current_x, current_y, service_key, rating_state, rating, QC.QSize( STAR_DX, STAR_DY ), custom_pad )
            
            current_y += STAR_DY + STAR_PAD.height() + VBOX_SPACING
            
        
        
        incdec_services = services_manager.GetServices( ( HC.LOCAL_RATING_INCDEC, ) )
        
        incdec_services.reverse()
        
        control_width = RATING_INCDEC_SET_WIDTH + 1
        
        incdec_rating_current_x = my_width - ( control_width ) - ( QFRAME_PADDING + VBOX_MARGIN )
        
        for incdec_service in incdec_services:
            
            service_key = incdec_service.GetServiceKey()
            
            ( rating_state, rating ) = ClientRatings.GetIncDecStateFromMedia( ( self._current_media, ), service_key )
            
            ClientGUIRatings.DrawIncDec( painter, incdec_rating_current_x, current_y, service_key, rating_state, rating, QC.QSize( round( RATING_INCDEC_SET_WIDTH ), round( RATING_INCDEC_SET_WIDTH / 2 ) ) )
            
            incdec_rating_current_x -= control_width    #+ STAR_PAD.width() #instead of spacing these out, we will just have them pixel-adjacent in all cases
            
        
        if len( incdec_services ) > 0:
            
            current_y += round( RATING_INCDEC_SET_WIDTH / 2 ) + round( STAR_PAD.height() / 2 ) + VBOX_SPACING
            
        
        # icons
        
        icons_to_show = []
        
        if self._current_media.GetLocationsManager().IsTrashed():
            
            icons_to_show.append( CC.global_pixmaps().trash )
            
        
        if self._current_media.HasInbox():
            
            icons_to_show.append( CC.global_pixmaps().inbox )
            
        
        if len( icons_to_show ) > 0:
            
            current_y += VBOX_MARGIN
            
            icon_x = - ( QFRAME_PADDING + VBOX_MARGIN )
            
            for icon in icons_to_show:
                
                painter.drawPixmap( my_width + icon_x - ( 16 + VBOX_SPACING ), current_y, icon )
                
                icon_x -= 16 + VBOX_SPACING
                
            
            # this appears to be correct for the wrong reasons
            
            current_y += 16 + VBOX_SPACING
            
            current_y += VBOX_MARGIN
            
        
        pen_colour = self.GetColour( CC.COLOUR_MEDIA_TEXT )
        
        painter.setPen( QG.QPen( pen_colour ) )
        
        # location strings
        
        location_strings = self._current_media.GetLocationsManager().GetLocationStrings()
        
        for location_string in location_strings:
            
            ( text_size, location_string ) = ClientGUIFunctions.GetTextSizeFromPainter( painter, location_string )
            
            ClientGUIFunctions.DrawText( painter, my_width - ( text_size.width() + QFRAME_PADDING + VBOX_MARGIN ), current_y, location_string )
            
            current_y += text_size.height()
            
        
        # urls
        
        urls = self._current_media.GetLocationsManager().GetURLs()
        
        url_tuples = CG.client_controller.network_engine.domain_manager.ConvertURLsToMediaViewerTuples( urls )
        
        if len( url_tuples ) > 0:
            
            current_y += VBOX_MARGIN
            
            for ( display_string, url ) in url_tuples:
                
                ( text_size, display_string ) = ClientGUIFunctions.GetTextSizeFromPainter( painter, display_string )
                
                ClientGUIFunctions.DrawText( painter, my_width - ( text_size.width() + QFRAME_PADDING + VBOX_MARGIN ), current_y, display_string )
                
                current_y += text_size.height() + VBOX_SPACING
                
            
            # again this appears to be correct but for the wrong reasons
            # flying completely by my pants here
            
            current_y -= VBOX_MARGIN
            
        
        current_y += VBOX_MARGIN + QFRAME_PADDING
        
        return current_y
        
    
    def _GenerateHoverTopFrame( self ):
        
        raise NotImplementedError()
        
    
    def _GetInfoString( self ):
        
        lines = ClientMediaResultPrettyInfo.GetPrettyMediaResultInfoLines( self._current_media.GetMediaResult(), only_interesting_lines = True )
        
        lines = [ line for line in lines if not line.IsSubmenu() ]
        
        texts = [ line.text for line in lines ]
        
        texts.insert( 1, ClientData.ConvertZoomToPercentage( self._media_container.GetCurrentZoom() ) )
        
        info_string = ' | '.join( texts )
        
        return info_string
        
    
    def _GetNoMediaText( self ):
        
        return 'No media to display'
        
    
    def _HideCursorCheck( self ):
        
        hide_time_ms = CG.client_controller.new_options.GetNoneableInteger( 'media_viewer_cursor_autohide_time_ms' )
        
        if hide_time_ms is None:
            
            return
            
        
        hide_time = HydrusTime.SecondiseMSFloat( hide_time_ms )
        
        can_hide = HydrusTime.TimeHasPassedFloat( self._last_cursor_autohide_touch_time + hide_time )
        
        can_check_again = ClientGUIFunctions.MouseIsOverWidget( self )
        
        if not CC.CAN_HIDE_MOUSE:
            
            can_hide = False
            
        
        if CGC.core().MenuIsOpen():
            
            can_hide = False
            
        
        if ClientGUIFunctions.DialogIsOpenAndIAmNotItsChild( self ):
            
            can_hide = False
            
            can_check_again = False
            
        
        if can_hide:
            
            self.setCursor( QG.QCursor( QC.Qt.CursorShape.BlankCursor ) )
            
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
        
    
    def _TryToShowPageThatLaunchedUs( self ):
        
        pass
        
    
    def CleanBeforeDestroy( self ):
        
        self.setCursor( QG.QCursor( QC.Qt.CursorShape.ArrowCursor ) )
        
        self.canvasWithHoversExiting.emit()
        
        super().CleanBeforeDestroy()
        
    
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
        
        mouse_currently_shown = self.cursor().shape() == QC.Qt.CursorShape.ArrowCursor
        show_mouse = mouse_currently_shown
        
        is_dragging = event.buttons() & QC.Qt.MouseButton.LeftButton and self._last_drag_pos is not None
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
                
                self.setCursor( QG.QCursor( QC.Qt.CursorShape.ArrowCursor ) )
                
            
            self._RestartCursorHideWait()
            
        else:
            
            if mouse_currently_shown:
                
                self.setCursor( QG.QCursor( QC.Qt.CursorShape.BlankCursor ) )
                
            
        
        super().mouseMoveEvent( event )
        
    
    def GetCanvasType( self ):
        
        return self._canvas_type
        
    
    def ProcessApplicationCommand( self, command: CAC.ApplicationCommand ):
        
        command_processed = True
        
        if command.IsSimpleCommand():
            
            action = command.GetSimpleAction()
            
            if action == CAC.SIMPLE_CLOSE_MEDIA_VIEWER:
                
                self._TryToCloseWindow()
                
            elif action == CAC.SIMPLE_CLOSE_MEDIA_VIEWER_AND_FOCUS_TAB:
                
                self._TryToShowPageThatLaunchedUs()
                
                self._TryToCloseWindow()
                
            elif action == CAC.SIMPLE_SWITCH_BETWEEN_FULLSCREEN_BORDERLESS_AND_REGULAR_FRAMED_WINDOW:
                
                self.parentWidget().FullscreenSwitch()
                
            else:
                
                command_processed = False
                
            
        else:
            
            command_processed = False
            
        
        if not command_processed:
            
            command_processed = super().ProcessApplicationCommand( command )
            
        
        return command_processed
        
    
    def RedrawDetails( self ):
        
        self.update()
        
    
    def TryToDoPreClose( self ):
        
        can_close = True
        
        return can_close
        
    
    def TIMERUIUpdate( self ):
        
        for hover in self._hovers:
            
            hover.DoRegularHideShow()
            
        
    

class CanvasFilterDuplicates( CanvasWithHovers ):
    
    CANVAS_TYPE = CC.CANVAS_MEDIA_VIEWER_DUPLICATES
    
    showPairInPage = QC.Signal( list )
    
    def __init__( self, parent, potential_duplicates_search_context: ClientPotentialDuplicatesSearchContext.PotentialDuplicatesSearchContext ):
        
        self._potential_duplicates_search_context = potential_duplicates_search_context
        
        location_context = self._potential_duplicates_search_context.GetFileSearchContext1().GetLocationContext()
        
        super().__init__( parent, location_context )
        
        self._canvas_type = CC.CANVAS_MEDIA_VIEWER_DUPLICATES
        
        self._duplicates_right_hover = ClientGUICanvasHoverFrames.CanvasHoverFrameRightDuplicates( self, self, self._canvas_key )
        
        self.mediaChanged.connect( self._duplicates_right_hover.SetMedia )
        self.mediaCleared.connect( self._duplicates_right_hover.ClearMedia )
        
        self._right_notes_hover.AddHoverThatCanBeOnTop( self._duplicates_right_hover )
        
        self._duplicates_right_hover.showPairInPage.connect( self._ShowPairInPage )
        self._duplicates_right_hover.sendApplicationCommand.connect( self.ProcessApplicationCommand )
        
        self._hovers.append( self._duplicates_right_hover )
        
        self._background_colour_generator = CanvasBackgroundColourGeneratorDuplicates( self )
        
        self._media_container.SetBackgroundColourGenerator( self._background_colour_generator )
        
        self._my_shortcuts_handler.AddWindowToFilter( self._duplicates_right_hover )
        
        self._force_maintain_pan_and_zoom = True
        
        self._currently_fetching_pairs = False
        
        self._current_pair_score = 0
        
        self._batch_of_pairs_to_process = []
        self._current_pair_index = 0
        self._processed_pairs = []
        self._hashes_due_to_be_deleted_in_this_batch = set()
        
        # ok we started excluding pairs if they had been deleted, now I am extending it to any files that have been processed.
        # main thing is if you have AB, AC, that's neat and a bunch of people want it, but current processing system doesn't do B->A->C merge if it happens in a single batch
        # I need to store dupe merge options rather than content updates apply them in db transaction or do the retroactive sync or similar to get this done properly
        # so regrettably I turn it off for now
        
        self._hashes_processed_in_this_batch = set()
        
        self._media_list = ClientMedia.MediaList( location_context, [] )
        
        self._my_shortcuts_handler.AddShortcuts( 'media_viewer_browser' )
        self._my_shortcuts_handler.AddShortcuts( 'duplicate_filter' )
        
        CG.client_controller.sub( self, 'Delete', 'canvas_delete' )
        CG.client_controller.sub( self, 'Undelete', 'canvas_undelete' )
        CG.client_controller.sub( self, 'SwitchMedia', 'canvas_show_next' )
        CG.client_controller.sub( self, 'SwitchMedia', 'canvas_show_previous' )
        
        QP.CallAfter( self._LoadNextBatchOfPairs )
        
        CG.client_controller.sub( self, 'ProcessContentUpdatePackage', 'content_updates_gui' )
        CG.client_controller.sub( self, 'ProcessServiceUpdates', 'service_updates_gui' )
        
    
    def _CommitProcessed( self, blocking = True ):
        
        pair_info = []
        
        for ( duplicate_type, media_a, media_b, content_update_packages, was_auto_skipped ) in self._processed_pairs:
            
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
                
            
            hash_a = media_a.GetHash()
            hash_b = media_b.GetHash()
            
            pair_info.append( ( duplicate_type, hash_a, hash_b, content_update_packages ) )
            
        
        if len( pair_info ) > 0:
            
            if blocking:
                
                CG.client_controller.WriteSynchronous( 'duplicate_pair_status', pair_info )
                
            else:
                
                CG.client_controller.Write( 'duplicate_pair_status', pair_info )
                
            
        
        self._processed_pairs = []
        self._hashes_due_to_be_deleted_in_this_batch = set()
        self._hashes_processed_in_this_batch = set()
        
    
    def _CurrentMediaIsBetter( self, delete_b = True ):
        
        self._ProcessPair( HC.DUPLICATE_BETTER, delete_b = delete_b )
        
    
    def _Delete( self, media = None, reason = None, file_service_key = None ):
        
        if self._current_media is None:
            
            return False
            
        
        media_a = self._current_media
        media_b = self._media_list.GetNext( self._current_media )
        
        message = 'Delete just this file, or both?'
        
        yes_tuples = []
        
        yes_tuples.append( ( 'delete just this one', 'current' ) )
        yes_tuples.append( ( 'delete both', 'both' ) )
        
        try:
            
            result = ClientGUIDialogsQuick.GetYesYesNo( self, message, yes_tuples = yes_tuples, no_label = 'forget it' )
            
        except HydrusExceptions.CancelledException:
            
            return False
            
        
        if result == 'current':
            
            media = [ media_a ]
            
            default_reason = 'Deleted manually in Duplicate Filter.'
            
        elif result == 'both':
            
            media = [ media_a, media_b ]
            
            default_reason = 'Deleted manually in Duplicate Filter, along with its potential duplicate.'
            
        
        content_update_packages = super()._Delete( media = media, default_reason = default_reason, file_service_key = file_service_key, just_get_content_update_packages = True )
        
        deleted = isinstance( content_update_packages, list ) and len( content_update_packages ) > 0
        
        if deleted:
            
            for m in media:
                
                self._hashes_due_to_be_deleted_in_this_batch.update( m.GetHashes() )
                
            
            was_auto_skipped = False
            
            ( media_result_a, media_result_b ) = self._batch_of_pairs_to_process[ self._current_pair_index ]
            
            media_a = ClientMedia.MediaSingleton( media_result_a )
            media_b = ClientMedia.MediaSingleton( media_result_b )
            
            process_tuple = ( None, media_a, media_b, content_update_packages, was_auto_skipped )
            
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
                
                panel = ClientGUIScrolledPanels.EditSingleCtrlPanel( dlg_2 )
                
                ctrl = ClientGUIDuplicatesContentMergeOptions.EditDuplicateContentMergeOptionsWidget( panel, duplicate_type, duplicate_content_merge_options, for_custom_action = True )
                
                panel.SetControl( ctrl )
                
                dlg_2.SetPanel( panel )
                
                if dlg_2.exec() == QW.QDialog.DialogCode.Accepted:
                    
                    duplicate_content_merge_options = ctrl.GetValue()
                    
                else:
                    
                    return
                    
                
            
        else:
            
            duplicate_content_merge_options = None
            
        
        message = 'Delete any of the files?'
        
        yes_tuples = []
        
        yes_tuples.append( ( 'delete neither', 'delete_neither' ) )
        yes_tuples.append( ( 'delete this one', 'delete_a' ) )
        yes_tuples.append( ( 'delete the other', 'delete_b' ) )
        yes_tuples.append( ( 'delete both', 'delete_both' ) )
        
        try:
            
            result = ClientGUIDialogsQuick.GetYesYesNo( self, message, yes_tuples = yes_tuples, no_label = 'forget it' )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        delete_a = False
        delete_b = False
        
        if result == 'delete_a':
            
            delete_a = True
            
        elif result == 'delete_b':
            
            delete_b = True
            
        elif result == 'delete_both':
            
            delete_a = True
            delete_b = True
            
        
        self._ProcessPair( duplicate_type, delete_a = delete_a, delete_b = delete_b, duplicate_content_merge_options = duplicate_content_merge_options )
        
    
    def _DrawBackgroundDetails( self, painter ):
        
        if self._currently_fetching_pairs:
            
            text = 'Loading pairs' + HC.UNICODE_ELLIPSIS
            
            ( text_size, text ) = ClientGUIFunctions.GetTextSizeFromPainter( painter, text )
            
            my_size = self.size()
            
            x = ( my_size.width() - text_size.width() ) // 2
            y = ( my_size.height() - text_size.height() ) // 2
            
            ClientGUIFunctions.DrawText( painter, x, y, text )
            
        else:
            
            super()._DrawBackgroundDetails( painter )
            
        
    
    def _GenerateHoverTopFrame( self ):
        
        return ClientGUICanvasHoverFrames.CanvasHoverFrameTopDuplicatesFilter( self, self, self._canvas_key )
        
    
    def _GetIndexString( self ):
        
        if self._current_media is None or len( self._media_list ) == 0:
            
            return '-'
            
        else:
            
            current_media_label = f'File One' if self._current_media == self._media_list.GetFirst() else f'File Two'
            
            progress = self._current_pair_index + 1
            total = len( self._batch_of_pairs_to_process )
            
            index_string = HydrusNumbers.ValueRangeToPrettyString( progress, total )
            
            num_committable = self._GetNumCommittableDecisions()
            num_deletable = self._GetNumCommittableDeletes()
            
            components = []
            
            if num_committable > 0:
                
                components.append( '{} decisions'.format( HydrusNumbers.ToHumanInt( num_committable ) ) )
                
            
            if num_deletable > 0:
                
                components.append( '{} deletes'.format( HydrusNumbers.ToHumanInt( num_deletable ) ) )
                
            
            if len( components ) == 0:
                
                num_decisions_string = 'no decisions yet'
                
            else:
                
                num_decisions_string = ', '.join( components )
                
            
            return '{} - {} - {}'.format( current_media_label, index_string, num_decisions_string )
            
        
    
    def _GetNoMediaText( self ):
        
        return 'Looking for pairs to compare--please wait.'
        
    
    def _GetNumCommittableDecisions( self ):
        
        return len( [ 1 for ( duplicate_type, media_a, media_b, content_update_packages, was_auto_skipped ) in self._processed_pairs if duplicate_type is not None ] )
        
    
    def _GetNumCommittableDeletes( self ):
        
        return len( [ 1 for ( duplicate_type, media_a, media_b, content_update_packages, was_auto_skipped ) in self._processed_pairs if duplicate_type is None and len( content_update_packages ) > 0 ] )
        
    
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
        
        self._media_list = ClientMedia.MediaList( self._location_context, [] )
        
        self._currently_fetching_pairs = True
        
        CG.client_controller.CallToThread( self.THREADFetchPairs, self._potential_duplicates_search_context )
        
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
            
        
        other_media: ClientMedia.MediaSingleton = self._media_list.GetNext( self._current_media )
        
        media_results_to_prefetch = [ other_media.GetMediaResult() ]
        
        duplicate_filter_prefetch_num_pairs = CG.client_controller.new_options.GetInteger( 'duplicate_filter_prefetch_num_pairs' )
        
        if duplicate_filter_prefetch_num_pairs > 0:
            
            # this isn't clever enough to handle pending skip logic, but that's fine
            
            start_pos = self._current_pair_index + 1
            
            pairs_to_do = self._batch_of_pairs_to_process[ start_pos : start_pos + duplicate_filter_prefetch_num_pairs ]
            
            for pair in pairs_to_do:
                
                media_results_to_prefetch.extend( pair )
                
            
        
        delay_base = HydrusTime.SecondiseMSFloat( CG.client_controller.new_options.GetInteger( 'media_viewer_prefetch_delay_base_ms' ) )
        
        images_cache = CG.client_controller.images_cache
        
        for ( i, media_result ) in enumerate( media_results_to_prefetch ):
            
            delay = i * delay_base
            
            hash = media_result.GetHash()
            mime = media_result.GetMime()
            
            if media_result.IsStaticImage() and ClientGUICanvasMedia.WeAreExpectingToLoadThisMediaFile( media_result, self.CANVAS_TYPE ):
                
                if not images_cache.HasImageRenderer( hash ):
                    
                    CG.client_controller.CallLaterQtSafe( self, delay, 'image pre-fetch', images_cache.PrefetchImageRenderer, media_result )
                    
                
            
        
    
    def _ProcessPair( self, duplicate_type, delete_a = False, delete_b = False, duplicate_content_merge_options = None ):
        
        if self._current_media is None:
            
            return
            
        
        if duplicate_content_merge_options is None:
            
            if duplicate_type in [ HC.DUPLICATE_BETTER, HC.DUPLICATE_SAME_QUALITY ] or ( CG.client_controller.new_options.GetBoolean( 'advanced_mode' ) and duplicate_type == HC.DUPLICATE_ALTERNATE ):
                
                new_options = CG.client_controller.new_options
                
                duplicate_content_merge_options = new_options.GetDuplicateContentMergeOptions( duplicate_type )
                
            else:
                
                duplicate_content_merge_options = ClientDuplicates.DuplicateContentMergeOptions()
                
            
        
        media_a = self._current_media
        media_b = typing.cast( ClientMedia.MediaSingleton, self._media_list.GetNext( media_a ) )
        
        was_auto_skipped = False
        
        self._hashes_processed_in_this_batch.update( media_a.GetHashes() )
        self._hashes_processed_in_this_batch.update( media_b.GetHashes() )
        
        if delete_a or delete_b:
            
            if delete_a:
                
                self._hashes_due_to_be_deleted_in_this_batch.update( media_a.GetHashes() )
                
            
            if delete_b:
                
                self._hashes_due_to_be_deleted_in_this_batch.update( media_b.GetHashes() )
                
            
            if duplicate_type == HC.DUPLICATE_BETTER:
                
                file_deletion_reason = 'better/worse'
                
                if delete_b:
                    
                    file_deletion_reason += ', worse file deleted'
                    
                
            else:
                
                file_deletion_reason = HC.duplicate_type_string_lookup[ duplicate_type ]
                
            
            if delete_a and delete_b:
                
                file_deletion_reason += ', both files deleted'
                
            
            file_deletion_reason = 'Deleted in Duplicate Filter ({}).'.format( file_deletion_reason )
            
        else:
            
            file_deletion_reason = None
            
        
        content_update_packages = duplicate_content_merge_options.ProcessPairIntoContentUpdatePackages( media_a.GetMediaResult(), media_b.GetMediaResult(), delete_a = delete_a, delete_b = delete_b, file_deletion_reason = file_deletion_reason )
        
        process_tuple = ( duplicate_type, media_a, media_b, content_update_packages, was_auto_skipped )
        
        self._ShowNextPair( process_tuple )
        
    
    def _RecoverAfterMediaUpdate( self ):
        
        if len( self._media_list ) < 2 and len( self._batch_of_pairs_to_process ) > self._current_pair_index:
            
            was_auto_skipped = True
            
            ( media_result_a, media_result_b ) = self._batch_of_pairs_to_process[ self._current_pair_index ]
            
            media_a = ClientMedia.MediaSingleton( media_result_a )
            media_b = ClientMedia.MediaSingleton( media_result_b )
            
            process_tuple = ( None, media_a, media_b, [], was_auto_skipped )
            
            self._ShowNextPair( process_tuple )
            
        else:
            
            self.update()
            
        
    
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
                    
                
                ( duplicate_type, media_a, media_b, content_update_packages, was_auto_skipped ) = self._processed_pairs.pop()
                
                self._current_pair_index -= 1
                
                if not was_auto_skipped:
                    
                    break
                    
                
            
            # only want this for the one that wasn't auto-skipped
            for m in ( media_a, media_b ):
                
                hash = m.GetHash()
                
                self._hashes_due_to_be_deleted_in_this_batch.discard( hash )
                self._hashes_processed_in_this_batch.discard( hash )
                
            
            return True
            
        
        return False
        
    
    def _ShowCurrentPair( self ):
        
        if self._currently_fetching_pairs:
            
            return
            
        
        ( media_result_1, media_result_2 ) = self._batch_of_pairs_to_process[ self._current_pair_index ]
        
        self._current_pair_score = ClientDuplicates.GetDuplicateComparisonScore( media_result_1, media_result_2 )
        
        if self._current_pair_score > 0:
            
            media_results_with_better_first = ( media_result_1, media_result_2 )
            
        else:
            
            self._current_pair_score = - self._current_pair_score
            
            media_results_with_better_first = ( media_result_2, media_result_1 )
            
        
        self._media_list = ClientMedia.MediaList( self._location_context, media_results_with_better_first )
        
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
            
            ( media_result_a, media_result_b ) = pair
            
            hash_a = media_result_a.GetHash()
            hash_b = media_result_b.GetHash()
            
            if hash_a in self._hashes_processed_in_this_batch or hash_b in self._hashes_processed_in_this_batch:
                
                return False
                
            
            if hash_a in self._hashes_due_to_be_deleted_in_this_batch or hash_b in self._hashes_due_to_be_deleted_in_this_batch:
                
                return False
                
            
            media_a = ClientMedia.MediaSingleton( media_result_a )
            media_b = ClientMedia.MediaSingleton( media_result_b )
            
            if not ClientMedia.CanDisplayMedia( media_a ) or not ClientMedia.CanDisplayMedia( media_b ):
                
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
                        
                        components.append( '{} decisions'.format( HydrusNumbers.ToHumanInt( num_committable ) ) )
                        
                    
                    if num_deletable > 0:
                        
                        components.append( '{} deletes'.format( HydrusNumbers.ToHumanInt( num_deletable ) ) )
                        
                    
                    label = 'commit {} and continue?'.format( ' and '.join( components ) )
                    
                    result = ClientGUIScrolledPanelsCommitFiltering.GetInterstitialFilteringAnswer( self, label )
                    
                    if result == QW.QDialog.DialogCode.Accepted:
                        
                        self._CommitProcessed( blocking = True )
                        
                    else:
                        
                        it_went_ok = self._RewindProcessing()
                        
                        if it_went_ok:
                            
                            self._ShowCurrentPair()
                            
                        
                        return
                        
                    
                else:
                    
                    # nothing to commit, so let's see if we have a big problem here or if user just skipped all
                    
                    we_saw_a_non_auto_skip = False
                    
                    for ( duplicate_type, media_a, media_b, content_update_packages, was_auto_skipped ) in self._processed_pairs:
                        
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

        ( media_result_a, media_result_b ) = self._batch_of_pairs_to_process[ self._current_pair_index ]
        
        media_a = ClientMedia.MediaSingleton( media_result_a )
        media_b = ClientMedia.MediaSingleton( media_result_b )
        
        process_tuple = ( None, media_a, media_b, [], was_auto_skipped )
        
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
        
        super().CleanBeforeDestroy()
        
    
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
                
                self._CurrentMediaIsBetter( delete_b = True )
                
            elif action == CAC.SIMPLE_DUPLICATE_FILTER_THIS_IS_BETTER_BUT_KEEP_BOTH:
                
                self._CurrentMediaIsBetter( delete_b = False )
                
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
            
            command_processed = super().ProcessApplicationCommand( command )
            
        
        return command_processed
        
    
    def ProcessContentUpdatePackage( self, content_update_package: ClientContentUpdates.ContentUpdatePackage ):
        
        self._media_list.ProcessContentUpdatePackage( content_update_package )
        
        self._RecoverAfterMediaUpdate()
        
    
    def ProcessServiceUpdates( self, service_keys_to_service_updates: dict[ bytes, collections.abc.Collection[ ClientServices.ServiceUpdate ] ]  ):
        
        self._media_list.ProcessServiceUpdates( service_keys_to_service_updates )
        
        self._RecoverAfterMediaUpdate()
        
    
    def SetMedia( self, media ):
        
        super().SetMedia( media )
        
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
                
                components.append( '{} decisions'.format( HydrusNumbers.ToHumanInt( num_committable ) ) )
                
            
            if num_deletable > 0:
                
                components.append( '{} deletes'.format( HydrusNumbers.ToHumanInt( num_deletable ) ) )
                
            
            label = 'commit {}?'.format( ' and '.join( components ) )
            
            ( result, cancelled ) = ClientGUIScrolledPanelsCommitFiltering.GetFinishFilteringAnswer( self, label )
            
            if cancelled:
                
                close_was_triggered_by_everything_being_processed = self._GetNumRemainingDecisions() == 0
                
                if close_was_triggered_by_everything_being_processed:
                    
                    self._GoBack()
                    
                
                return False
                
            elif result == QW.QDialog.DialogCode.Accepted:
                
                self._CommitProcessed( blocking = False )
                
            
        
        return super().TryToDoPreClose()
        
    
    def Undelete( self, canvas_key ):
        
        if canvas_key == self._canvas_key:
            
            self._Undelete()
            
        
    
    def THREADFetchPairs( self, potential_duplicates_search_context: ClientPotentialDuplicatesSearchContext.PotentialDuplicatesSearchContext ):
        
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
            
        
        result = CG.client_controller.Read( 'duplicate_pairs_for_filtering', potential_duplicates_search_context )
        
        if len( result ) == 0:
            
            QP.CallAfter( qt_close )
            
        else:
            
            QP.CallAfter( qt_continue, result )
            
        
    

class CanvasMediaList( CanvasWithHovers ):
    
    exitFocusMedia = QC.Signal( ClientMedia.Media )
    userRemovedMedia = QC.Signal( set )
    
    def __init__( self, parent, page_key, location_context: ClientLocation.LocationContext, media_results ):
        
        super().__init__( parent, location_context )
        
        self._media_list = ClientMedia.MediaList( location_context, media_results )
        
        self._page_key = page_key
        
        self._just_started = True
        
        CG.client_controller.sub( self, 'ProcessContentUpdatePackage', 'content_updates_gui' )
        CG.client_controller.sub( self, 'ProcessServiceUpdates', 'service_updates_gui' )
        
    
    def _TryToShowPageThatLaunchedUs( self ):
        
        if CG.client_controller.gui.GetPageFromPageKey( self._page_key ) is not None:
            
            CG.client_controller.gui.ShowPage( self._page_key )
            
        
    
    def TryToDoPreClose( self ):
        
        if self._current_media is not None and CG.client_controller.new_options.GetBoolean( 'focus_media_thumb_on_viewer_close' ):
            
            self.exitFocusMedia.emit( self._current_media )
            
        
        return super().TryToDoPreClose()
        
    
    def _GenerateHoverTopFrame( self ):
        
        raise NotImplementedError()
        
    
    def _GetIndexString( self ):
        
        if self._current_media is None:
            
            index_string = '-/' + HydrusNumbers.ToHumanInt( len( self._media_list ) )
            
        else:
            
            index_string = HydrusNumbers.ValueRangeToPrettyString( self._media_list.IndexOf( self._current_media ) + 1, len( self._media_list ) )
            
        
        return index_string
        
    
    def _PrefetchNeighbours( self ):
        
        media_looked_at = set()
        
        to_render = []
        
        previous = self._current_media
        next = self._current_media
        
        delay_base = HydrusTime.SecondiseMSFloat( CG.client_controller.new_options.GetInteger( 'media_viewer_prefetch_delay_base_ms' ) )
        
        num_to_go_back = CG.client_controller.new_options.GetInteger( 'media_viewer_prefetch_num_previous' )
        num_to_go_forward = CG.client_controller.new_options.GetInteger( 'media_viewer_prefetch_num_next' )
        
        # if media_looked_at nukes the list, we want shorter delays, so do next first
        
        for i in range( num_to_go_forward ):
            
            next = self._media_list.GetNext( next )
            
            if next in media_looked_at:
                
                break
                
            else:
                
                media_looked_at.add( next )
                
            
            delay = delay_base * ( i + 1 )
            
            to_render.append( ( next, delay ) )
            
        
        for i in range( num_to_go_back ):
            
            previous = self._media_list.GetPrevious( previous )
            
            if previous in media_looked_at:
                
                break
                
            else:
                
                media_looked_at.add( previous )
                
            
            delay = delay_base * 2 * ( i + 1 )
            
            to_render.append( ( previous, delay ) )
            
        
        images_cache = CG.client_controller.images_cache
        
        for ( media, delay ) in to_render:
            
            hash = media.GetHash()
            mime = media.GetMime()
            
            if media.IsStaticImage() and ClientGUICanvasMedia.WeAreExpectingToLoadThisMediaFile( media.GetMediaResult(), self.CANVAS_TYPE ):
                
                if not images_cache.HasImageRenderer( hash ):
                    
                    # we do qt safe to make sure the job is cancelled if we are destroyed
                    
                    CG.client_controller.CallLaterQtSafe( self, delay, 'image pre-fetch', images_cache.PrefetchImageRenderer, media.GetMediaResult() )
                    
                
            
        
    
    def _ShowFirst( self ):
        
        self.SetMedia( self._media_list.GetFirst() )
        
    
    def _ShowLast( self ):
        
        self.SetMedia( self._media_list.GetLast() )
        
    
    def _ShowNext( self ):
        
        self.SetMedia( self._media_list.GetNext( self._current_media ) )
        
    
    def _ShowPrevious( self ):
        
        self.SetMedia( self._media_list.GetPrevious( self._current_media ) )
        
    
    def _StartSlideshow( self, interval: float ):
        
        pass
        
    
    def AddMediaResults( self, page_key, media_results ):
        
        if page_key == self._page_key:
            
            self._media_list.AddMediaResults( media_results )
            
            CG.client_controller.pub( 'canvas_new_index_string', self._canvas_key, self._GetIndexString() )
            
            self.update()
            
        
    
    def EventFullscreenSwitch( self, event ):
        
        self.ProcessApplicationCommand( CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_SWITCH_BETWEEN_FULLSCREEN_BORDERLESS_AND_REGULAR_FRAMED_WINDOW ) )
        
    
    def ProcessContentUpdatePackage( self, content_update_package: ClientContentUpdates.ContentUpdatePackage ):
        
        if self._current_media is None:
            
            # probably a file view stats update as we close down--ignore it
            
            return
            
        
        if self._media_list.HasMedia( self._current_media ):
            
            next_media = self._media_list.GetNext( self._current_media )
            
            if next_media == self._current_media:
                
                next_media = None
                
            
        else:
            
            next_media = None
            
        
        self._media_list.ProcessContentUpdatePackage( content_update_package )
        
        if self._media_list.HasNoMedia():
            
            self._TryToCloseWindow()
            
        elif self._media_list.HasMedia( self._current_media ):
            
            CG.client_controller.pub( 'canvas_new_index_string', self._canvas_key, self._GetIndexString() )
            
            self.update()
            
        elif self._media_list.HasMedia( next_media ):
            
            self.SetMedia( next_media )
            
        else:
            
            self.SetMedia( self._media_list.GetFirst() )
            
        
    
    def ProcessServiceUpdates( self, service_keys_to_service_updates: dict[ bytes, collections.abc.Collection[ ClientServices.ServiceUpdate ] ]  ):
        
        self._media_list.ProcessServiceUpdates( service_keys_to_service_updates )
        
        self.update()
        
    

def CommitArchiveDelete( deletee_location_context: ClientLocation.LocationContext, kept: collections.abc.Collection[ ClientMediaResult.MediaResult ], deleted: collections.abc.Collection[ ClientMediaResult.MediaResult ] ):
    
    # there's a problem here that if the user hits F5 super quick, they may see files they just actioned get archived/deleted late
    # we had some odd 'remove again' calls to try to double-action the remove in this case, but it was awkward especially as we moved to Qt signals for that stuff
    # thus I'm now wangling a job status to show archive/delete status when it takes more than two seconds. the slow-computer/fast-F5ing user will see that thing popup and know what happened
    
    start_time = HydrusTime.GetNowFloat()
    
    job_status = ClientThreading.JobStatus()
    
    job_status.SetStatusTitle( 'Committing Archive/Delete' )
    
    have_shown_popup = False
    
    kept = list( kept )
    deleted = list( deleted )
    
    deletee_location_context = deletee_location_context.Duplicate()
    
    deletee_location_context.FixMissingServices( ClientLocation.ValidLocalDomainsFilter )
    
    if deletee_location_context.IncludesCurrent():
        
        deletee_file_service_keys = deletee_location_context.current_service_keys
        
    else:
        
        # if we are in a weird search domain, then just say 'delete from all local'
        deletee_file_service_keys = [ CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY ]
        
    
    BLOCK_SIZE = 64
    num_to_do = len( deleted )
    
    for ( i, block_of_deleted ) in enumerate( HydrusLists.SplitListIntoChunks( deleted, BLOCK_SIZE ) ):
        
        if not have_shown_popup and HydrusTime.TimeHasPassedFloat( start_time + 2.0 ):
            
            CG.client_controller.pub( 'message', job_status )
            
        
        job_status.SetStatusText( f'Deleting - {HydrusNumbers.ValueRangeToPrettyString( i * BLOCK_SIZE, num_to_do )}' )
        job_status.SetVariable( 'popup_gauge_1', ( i * BLOCK_SIZE, num_to_do ) )
        
        if CG.client_controller.new_options.GetBoolean( 'delete_lock_for_archived_files' ) and CG.client_controller.new_options.GetBoolean( 'delete_lock_reinbox_deletees_after_archive_delete' ):
            
            block_of_deleted_hashes = [ m.GetHash() for m in block_of_deleted if not m.GetLocationsManager().inbox ]
            
            content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_INBOX, block_of_deleted_hashes ) )
            
            CG.client_controller.WriteSynchronous( 'content_updates', content_update_package )
            
            CG.client_controller.WaitUntilViewFree()
            
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage()
        
        reason = 'Deleted in Archive/Delete filter.'
        
        for deletee_file_service_key in deletee_file_service_keys:
            
            block_of_deleted_hashes = [ m.GetHash() for m in block_of_deleted if deletee_file_service_key in m.GetLocationsManager().GetCurrent() ]
            
            content_update_package.AddContentUpdate( deletee_file_service_key, ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, block_of_deleted_hashes, reason = reason ) )
            
        
        CG.client_controller.WriteSynchronous( 'content_updates', content_update_package )
        
        CG.client_controller.WaitUntilViewFree()
        
    
    kept_hashes = [ m.GetHash() for m in kept ]
    
    num_to_do = len( kept_hashes )
    
    for ( i, block_of_kept_hashes ) in enumerate( HydrusLists.SplitListIntoChunks( kept_hashes, BLOCK_SIZE ) ):
        
        if not have_shown_popup and HydrusTime.TimeHasPassedFloat( start_time + 2.0 ):
            
            CG.client_controller.pub( 'message', job_status )
            
        
        job_status.SetStatusText( f'Archiving - {HydrusNumbers.ValueRangeToPrettyString( i * BLOCK_SIZE, num_to_do )}' )
        job_status.SetVariable( 'popup_gauge_1', ( i * BLOCK_SIZE, num_to_do ) )
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ARCHIVE, block_of_kept_hashes ) )
        
        CG.client_controller.WriteSynchronous( 'content_updates', content_update_package )
        
        CG.client_controller.WaitUntilViewFree()
        
    
    job_status.SetStatusText( 'Done!' )
    job_status.DeleteVariable( 'popup_gauge_1' )
    
    job_status.FinishAndDismiss( 2 )
    

class CanvasMediaListFilterArchiveDelete( CanvasMediaList ):
    
    CANVAS_TYPE = CC.CANVAS_MEDIA_VIEWER_ARCHIVE_DELETE
    
    def __init__( self, parent, page_key, location_context: ClientLocation.LocationContext, media_results ):
        
        super().__init__( parent, page_key, location_context, media_results )
        
        self._my_shortcuts_handler.AddShortcuts( 'archive_delete_filter' )
        
        self._canvas_type = CC.CANVAS_MEDIA_VIEWER_ARCHIVE_DELETE
        
        self._kept = set()
        self._deleted = set()
        self._skipped = set()
        
        CG.client_controller.sub( self, 'Delete', 'canvas_delete' )
        CG.client_controller.sub( self, 'Undelete', 'canvas_undelete' )
        
        first_media = self._media_list.GetFirst()
        
        if first_media is not None:
            
            QP.CallAfter( self.SetMedia, first_media ) # don't set this until we have a size > (20, 20)!
            
        
    
    def _Back( self ):
        
        if self._current_media == self._media_list.GetFirst():
            
            return
            
        else:
            
            self._ShowPrevious()
            
            self._kept.discard( self._current_media )
            self._deleted.discard( self._current_media )
            self._skipped.discard( self._current_media )
            
        
    
    def TryToDoPreClose( self ):
        
        kept = list( self._kept )
        
        deleted = list( self._deleted )
        
        skipped = list( self._skipped )
        
        if len( kept ) > 0 or len( deleted ) > 0:
            
            if len( kept ) > 0:
                
                kept_label = 'keep {}'.format( HydrusNumbers.ToHumanInt( len( kept ) ) )
                
            else:
                
                kept_label = None
                
            
            deletion_options = []
            
            if len( deleted ) > 0:
                
                location_contexts_to_present_options_for = []
                
                possible_location_context_at_top = self._location_context.Duplicate()
                
                possible_location_context_at_top.LimitToServiceTypes( CG.client_controller.services_manager.GetServiceType, ( HC.COMBINED_LOCAL_MEDIA, HC.LOCAL_FILE_DOMAIN ) )
                
                if len( possible_location_context_at_top.current_service_keys ) > 0:
                    
                    location_contexts_to_present_options_for.append( possible_location_context_at_top )
                    
                
                current_local_service_keys = HydrusLists.MassUnion( [ m.GetLocationsManager().GetCurrent() for m in deleted ] )
                
                local_file_domain_service_keys = [ service_key for service_key in current_local_service_keys if CG.client_controller.services_manager.GetServiceType( service_key ) == HC.LOCAL_FILE_DOMAIN ]
                
                location_contexts_to_present_options_for.extend( [ ClientLocation.LocationContext.STATICCreateSimple( service_key ) for service_key in local_file_domain_service_keys ] )
                
                all_my_files_location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY )
                
                if len( local_file_domain_service_keys ) > 1:
                    
                    location_contexts_to_present_options_for.append( all_my_files_location_context )
                    
                elif len( local_file_domain_service_keys ) == 1:
                    
                    if all_my_files_location_context in location_contexts_to_present_options_for:
                        
                        location_contexts_to_present_options_for.remove( all_my_files_location_context )
                        
                    
                
                location_contexts_to_present_options_for = HydrusData.DedupeList( location_contexts_to_present_options_for )
                
                only_allow_all_media_files = len( location_contexts_to_present_options_for ) > 1 and CG.client_controller.new_options.GetBoolean( 'only_show_delete_from_all_local_domains_when_filtering' ) and True in ( location_context.IsAllMediaFiles() for location_context in location_contexts_to_present_options_for )
                
                if only_allow_all_media_files:
                    
                    location_contexts_to_present_options_for = [ ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY ) ]
                    
                
                for location_context in location_contexts_to_present_options_for:
                    
                    file_service_keys = location_context.current_service_keys
                    
                    num_deletable = len( [ m for m in deleted if len( m.GetLocationsManager().GetCurrent().intersection( file_service_keys ) ) > 0 ] )
                    
                    if num_deletable > 0:
                        
                        if location_context == ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY ):
                            
                            location_label = 'all local file domains'
                            
                        else:
                            
                            location_label = location_context.ToString( CG.client_controller.services_manager.GetName )
                            
                        
                        delete_label = 'delete {} from {}'.format( HydrusNumbers.ToHumanInt( num_deletable ), location_label )
                        
                        deletion_options.append( ( location_context, delete_label ) )
                        
                    
                
            
            ( result, deletee_location_context, cancelled ) = ClientGUIScrolledPanelsCommitFiltering.GetFinishArchiveDeleteFilteringAnswer( self, kept_label, deletion_options )
            
            if cancelled:
                
                self._kept.discard( self._current_media )
                self._deleted.discard( self._current_media )
                self._skipped.discard( self._current_media )
                
                return False
                
            elif result == QW.QDialog.DialogCode.Accepted:
                
                self._kept = set()
                self._deleted = set()
                self._skipped = set()
                
                self._current_media = self._media_list.GetFirst() # so the pubsub on close is better
                
                if HC.options[ 'remove_filtered_files' ]:
                    
                    kept_hashes = [ m.GetHash() for m in kept ]
                    deleted_hashes = [ m.GetHash() for m in deleted ]
                    
                    all_hashes = set()
                    
                    all_hashes.update( kept_hashes )
                    all_hashes.update( deleted_hashes )
                    
                    if CG.client_controller.new_options.GetBoolean( 'remove_filtered_files_even_when_skipped' ):
                        
                        skipped_hashes = [ m.GetHash() for m in skipped ]
                        
                        all_hashes.update( skipped_hashes )
                        
                    
                    self.userRemovedMedia.emit( all_hashes )
                    
                
                kept_mr = [ m.GetMediaResult() for m in kept ]
                deleted_mr = [ m.GetMediaResult() for m in deleted ]
                
                CG.client_controller.CallToThread( CommitArchiveDelete, deletee_location_context, kept_mr, deleted_mr )
                
            
        
        return CanvasMediaList.TryToDoPreClose( self )
        
    
    def _Delete( self, media = None, reason = None, file_service_key = None ):
        
        if self._current_media is None:
            
            return False
            
        
        self._deleted.add( self._current_media )
        
        if self._current_media == self._media_list.GetLast():
            
            self._TryToCloseWindow()
            
        else:
            
            self._ShowNext()
            
        
        return True
        
    
    def _GenerateHoverTopFrame( self ):
        
        return ClientGUICanvasHoverFrames.CanvasHoverFrameTopArchiveDeleteFilter( self, self, self._canvas_key )
        
    
    def _Keep( self ):
        
        self._kept.add( self._current_media )
        
        if self._current_media == self._media_list.GetLast():
            
            self._TryToCloseWindow()
            
        else:
            
            self._ShowNext()
            
        
    
    def _Skip( self ):
        
        self._skipped.add( self._current_media )
        
        if self._current_media == self._media_list.GetLast():
            
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
        
        super().__init__( parent, page_key, location_context, media_results )
        
        self._my_shortcuts_handler.AddShortcuts( 'media_viewer_browser' )
        
        CG.client_controller.sub( self, 'Delete', 'canvas_delete' )
        CG.client_controller.sub( self, 'ShowNext', 'canvas_show_next' )
        CG.client_controller.sub( self, 'ShowPrevious', 'canvas_show_previous' )
        CG.client_controller.sub( self, 'Undelete', 'canvas_undelete' )
        
    
    def _GenerateHoverTopFrame( self ):
        
        return ClientGUICanvasHoverFrames.CanvasHoverFrameTopNavigableList( self, self, self._canvas_key )
        
    
    def _Remove( self ):
        
        next_media = self._media_list.GetNext( self._current_media )
        
        if next_media == self._current_media:
            
            next_media = None
            
        
        hashes = { self._current_media.GetHash() }
        
        self.userRemovedMedia.emit( hashes )
        
        singleton_media = { self._current_media }
        
        self._media_list.RemoveMediaDirectly( singleton_media, {} )
        
        if self._media_list.HasNoMedia():
            
            self._TryToCloseWindow()
            
        elif self._media_list.HasMedia( self._current_media ):
            
            CG.client_controller.pub( 'canvas_new_index_string', self._canvas_key, self._GetIndexString() )
            
            self.update()
            
        else:
            
            self.SetMedia( next_media )
            
        
    
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
        
        super().__init__( parent, page_key, location_context, media_results )
        
        self._slideshow_is_running = False
        self._last_slideshow_switch_time = 0
        self._normal_slideshow_period = 0.0
        self._special_slideshow_period_for_current_media = None
        
        if first_hash is None:
            
            first_media = self._media_list.GetFirst()
            
        else:
            
            try:
                
                # TODO: fix this ugly, temporary hack from refactoring
                first_media = self._media_list.GetMediaByHashes( { first_hash } )[0]
                
            except:
                
                first_media = self._media_list.GetFirst()
                
            
        
        if first_media is not None:
            
            QP.CallAfter( self.SetMedia, first_media ) # don't set this until we have a size > (20, 20)!
            
        
        CG.client_controller.sub( self, 'AddMediaResults', 'add_media_results' )
        
        self.userChangedMedia.connect( self.NotifyUserChangedMedia )
        
    
    def _CalculateAnySpecialSlideshowPeriodForCurrentMedia( self ):
        
        if self._media_container.CurrentlyPresentingMediaWithDuration():
            
            stop_after_one_play = False
            
            duration_s = self._current_media.GetMediaResult().GetDurationS()
            
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
        
        try:
            
            message = 'Enter the interval, in seconds.'
            
            period_str = ClientGUIDialogsQuick.EnterText( self, message, default = '15.0', min_char_width = 12 )
            
        except HydrusExceptions.CancelledException:
            
            raise
            
        
        try:
            
            period = float( period_str )
            
            self._StartSlideshow( period )
            
        except:
            
            ClientGUIDialogsMessage.ShowWarning( self, 'Could not parse that slideshow period!' )
            
        
    
    def _StopSlideshow( self ):
        
        if self._slideshow_is_running:
            
            self._slideshow_is_running = False
            self._special_slideshow_period_for_current_media = None
            
            self._media_container.StopForSlideshow( False )
            
        
    
    def contextMenuEvent( self, event ):
        
        if event.reason() == QG.QContextMenuEvent.Reason.Keyboard:
            
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
            
            command_processed = super().ProcessApplicationCommand( command )
            
        
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
            
            info_lines = ClientMediaResultPrettyInfo.GetPrettyMediaResultInfoLines( self._current_media.GetMediaResult() )
            
            info_menu = ClientGUIMenus.GenerateMenu( menu )
            
            ClientGUIMediaMenus.AddPrettyMediaResultInfoLines( info_menu, info_lines )
            
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
                
                ClientGUIMenus.AppendMenuItem( menu, 'exit fullscreen', 'Make this media viewer a regular window with borders.', self.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_SWITCH_BETWEEN_FULLSCREEN_BORDERLESS_AND_REGULAR_FRAMED_WINDOW ) )
                
            else:
                
                ClientGUIMenus.AppendMenuItem( menu, 'go fullscreen', 'Make this media viewer a fullscreen window without borders.', self.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_SWITCH_BETWEEN_FULLSCREEN_BORDERLESS_AND_REGULAR_FRAMED_WINDOW ) )
                
            
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
                
            
            num_notes = self._current_media.GetNotesManager().GetNumNotes()
            
            notes_str = 'notes'
            
            if num_notes > 0:
                
                notes_str = '{} ({})'.format( notes_str, HydrusNumbers.ToHumanInt( num_notes ) )
                
            
            ClientGUIMenus.AppendMenuItem( manage_menu, notes_str, 'Manage this file\'s notes.', self._ManageNotes )
            
            ClientGUIMenus.AppendMenuItem( manage_menu, 'times', 'Edit the timestamps for your files.', self._ManageTimestamps )
            ClientGUIMenus.AppendMenuItem( manage_menu, 'force filetype', 'Force your files to appear as a different filetype.', ClientGUIMediaModalActions.SetFilesForcedFiletypes, self, [ self._current_media ] )
            
            ClientGUIMediaMenus.AddManageFileViewingStatsMenu( self, manage_menu, [ self._current_media ] )
            
            ClientGUIMenus.AppendMenu( menu, manage_menu, 'manage' )
            
            ( local_duplicable_to_file_service_keys, local_moveable_from_and_to_file_service_keys ) = ClientGUIMediaSimpleActions.GetLocalFileActionServiceKeys( (self._current_media,) )
            
            multiple_selected = False
            
            if len( local_duplicable_to_file_service_keys ) > 0 or len( local_moveable_from_and_to_file_service_keys ) > 0:
                
                locations_menu = ClientGUIMenus.GenerateMenu( menu )
                
                ClientGUIMediaMenus.AddLocalFilesMoveAddToMenu( self, locations_menu, local_duplicable_to_file_service_keys, local_moveable_from_and_to_file_service_keys, multiple_selected, self.ProcessApplicationCommand )
                
                ClientGUIMenus.AppendMenu( menu, locations_menu, 'locations' )
                
            
            ClientGUIMediaMenus.AddKnownURLsViewCopyMenu( self, self, menu, self._current_media, 1 )
            
            ClientGUIMediaMenus.AddOpenMenu( self, self, menu, self._current_media, [ self._current_media ] )
            
            ClientGUIMediaMenus.AddShareMenu( self, self, menu, self._current_media, [ self._current_media ] )
            
            CGC.core().PopupMenu( self, menu )
            
        
    
    def TIMERUIUpdate( self ):
        
        super().TIMERUIUpdate()
        
        if self._slideshow_is_running:
            
            self._DoSlideshowWork()
            
        
    
