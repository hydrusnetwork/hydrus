import os

from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusPaths
from hydrus.core import HydrusStaticDir

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListConstants as CGLC
from hydrus.client.gui.lists import ClientGUIListCtrl
from hydrus.client.gui.panels import ClientGUIScrolledPanelsEdit
from hydrus.client.gui.panels.options import ClientGUIOptionsPanelBase
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.gui.widgets import ClientGUIPathWidgets

class MediaPlaybackPanel( ClientGUIOptionsPanelBase.OptionsPagePanel ):
    
    def __init__( self, parent ):
        
        super().__init__( parent )
        
        self._new_options = CG.client_controller.new_options
        
        #
        
        zoom_panel = ClientGUICommon.StaticBox( self, 'zoom and position' )
        
        self._media_zooms = QW.QLineEdit( zoom_panel )
        self._media_zooms.setToolTip( ClientGUIFunctions.WrapToolTip( 'This is a bit hacky, but whatever you have here, in comma-separated floats, will be what the program steps through as you zoom a media up and down.' ) )
        self._media_zooms.textChanged.connect( self.EventZoomsChanged )
        
        from hydrus.client.gui.canvas import ClientGUICanvasMedia
        
        self._media_viewer_zoom_center = ClientGUICommon.BetterChoice( zoom_panel )
        
        for zoom_centerpoint_type in ClientGUICanvasMedia.ZOOM_CENTERPOINT_TYPES:
            
            self._media_viewer_zoom_center.addItem( ClientGUICanvasMedia.zoom_centerpoints_str_lookup[ zoom_centerpoint_type ], zoom_centerpoint_type )
            
        
        tt = 'When you zoom in or out, there is a centerpoint about which the image zooms. This point \'stays still\' while the image expands or shrinks around it. Different centerpoints give different feels, especially if you drag images around a bit before zooming.'
        
        self._media_viewer_zoom_center.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        #
        
        self._media_viewer_default_zoom_type_override = ClientGUICommon.BetterChoice( zoom_panel )
        
        for window_zoom_type in ClientGUICanvasMedia.MEDIA_VIEWER_ZOOM_TYPES:
            
            self._media_viewer_default_zoom_type_override.addItem( ClientGUICanvasMedia.media_viewer_zoom_type_str_lookup[ window_zoom_type ], window_zoom_type )
            
        
        self._media_viewer_default_zoom_type_override.setToolTip( ClientGUIFunctions.WrapToolTip( 'You can override the default zoom if you like.' ) )
        
        self._preview_default_zoom_type_override = ClientGUICommon.BetterChoice( zoom_panel )
        
        for window_zoom_type in ClientGUICanvasMedia.MEDIA_VIEWER_ZOOM_TYPES:
            
            self._preview_default_zoom_type_override.addItem( ClientGUICanvasMedia.media_viewer_zoom_type_str_lookup[ window_zoom_type ], window_zoom_type )
            
        
        self._preview_default_zoom_type_override.setToolTip( ClientGUIFunctions.WrapToolTip( 'You can override the default zoom if you like.' ) )
        
        self._media_viewer_recenter_media_on_window_resize = QW.QCheckBox( zoom_panel )
        self._media_viewer_recenter_media_on_window_resize.setToolTip( ClientGUIFunctions.WrapToolTip( 'If unchecked, when you resize the media viewer window, the media inside it will stay exactly as it is with respect to location and size. This is useful if you want to resize the window while zoomed-in to look at details. While checked, media will re-center and zoom itself as normal whenever a media viewer window is resized.' ) )
        
        #
        
        animations_panel = ClientGUICommon.StaticBox( self, 'video/animations' )
        
        self._animation_start_position = ClientGUICommon.BetterSpinBox( animations_panel, min=0, max=100 )
        
        self._always_loop_animations = QW.QCheckBox( animations_panel )
        self._always_loop_animations.setToolTip( ClientGUIFunctions.WrapToolTip( 'Some GIFS and APNGs have metadata specifying how many times they should be played, usually 1. Uncheck this to obey that number.' ) )
        
        #
        
        mpv_panel = ClientGUICommon.StaticBox( self, 'mpv' )
        
        self._mpv_conf_path = ClientGUIPathWidgets.FilePickerCtrl( mpv_panel, starting_directory = HydrusStaticDir.GetStaticPath( 'mpv-conf' ) )
        
        self._use_legacy_mpv_mediator = QW.QCheckBox( mpv_panel )
        self._use_legacy_mpv_mediator.setToolTip( ClientGUIFunctions.WrapToolTip( 'Leave this off it you can. You can try it if mpv errors out or does not show seekbar progress on any load (probably because of an older mpv version). If you have opened any mpv windows, restart the client to take effect.' ) )
        
        self._mpv_loop_playlist_instead_of_file = QW.QCheckBox( mpv_panel )
        self._mpv_loop_playlist_instead_of_file.setToolTip( ClientGUIFunctions.WrapToolTip( 'Try this if you get "too many events queued" error in mpv.' ) )
        
        self._persist_media_window_mpv = QW.QCheckBox( mpv_panel )
        self._persist_media_window_mpv.setToolTip( ClientGUIFunctions.WrapToolTip( 'When moving from video to video, should we re-use the same mpv player or create/swap to a different one? This has been unstable or flickery in the past, but I am ready to test it now.' ) )
        
        self._mpv_destruction_test = QW.QCheckBox( mpv_panel )
        self._mpv_destruction_test.setToolTip( ClientGUIFunctions.WrapToolTip( 'Instead of re-using mpv windows, this will destroy old ones and re-create new ones as needed. This has previously been extremely crashy, but hydev thinks it might be ok now. Try it out, try pushing mpv a little harder than usual, and let him know how it goes.' ) )
        
        self._do_not_setgeometry_on_an_mpv = QW.QCheckBox( mpv_panel )
        self._do_not_setgeometry_on_an_mpv.setToolTip( ClientGUIFunctions.WrapToolTip( 'Try this if X11 crashes when you zoom an mpv window.' ) )
        
        #
        
        qt_media_panel = ClientGUICommon.StaticBox( self, 'QtMediaPlayer' )
        
        self._persist_media_window_qt_media_player = QW.QCheckBox( mpv_panel )
        self._persist_media_window_qt_media_player.setToolTip( ClientGUIFunctions.WrapToolTip( 'When moving from video to video, should we re-use the same Qt player or create/swap to a different one? This has been unstable or flickery in the past, but I am ready to test it now.' ) )
        
        self._qt_media_player_opengl_test = QW.QCheckBox( qt_media_panel )
        self._qt_media_player_opengl_test.setToolTip( ClientGUIFunctions.WrapToolTip( 'Try this and load up some big heavy vids--does it improve performance? Cause crashes? I noticed some flickering in Windows as windows reinitialise, but maybe it helps elsewhere?' ) )
        
        #
        
        transparency_panel = ClientGUICommon.StaticBox( self, 'transparency' )
        
        self._file_has_transparency_strictness = ClientGUICommon.BetterChoice( transparency_panel )
        
        tt = 'This affects image rendering and the "has transparency" property for new files. If you decide to change this and like it, you will probably want to queue up a large "has transparency" recheck for all your images/animations in the file maintenance system to update all your existing files.'
        tt += '\n\n'
        tt += 'Most users will want to keep this on the "human" setting.'
        
        self._file_has_transparency_strictness.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        from hydrus.core.files.images import HydrusImageColours
        
        for strictness in (
            HydrusImageColours.HAS_TRANSPARENCY_STRICTNESS_HUMAN,
            HydrusImageColours.HAS_TRANSPARENCY_STRICTNESS_NOT_BLACK_OR_WHITE,
            HydrusImageColours.HAS_TRANSPARENCY_STRICTNESS_CHANNEL_PRESENCE
        ):
            
            self._file_has_transparency_strictness.addItem( HydrusImageColours.has_transparency_strictness_string_lookup[ strictness ], strictness )
            
        
        self._draw_transparency_checkerboard_media_canvas = QW.QCheckBox( transparency_panel )
        self._draw_transparency_checkerboard_media_canvas.setToolTip( ClientGUIFunctions.WrapToolTip( 'If unchecked, will fill in with the normal background colour. Does not apply to MPV.' ) )
        
        self._draw_transparency_checkerboard_as_greenscreen = QW.QCheckBox( transparency_panel )
        self._draw_transparency_checkerboard_as_greenscreen.setToolTip( ClientGUIFunctions.WrapToolTip( 'Instead of a checkerboard pattern, draw a bright green colour.' ) )
        
        #
        
        system_panel = ClientGUICommon.StaticBox( self, 'system' )
        
        self._use_system_ffmpeg = QW.QCheckBox( system_panel )
        self._use_system_ffmpeg.setToolTip( ClientGUIFunctions.WrapToolTip( 'FFMPEG is used for file import metadata parsing and the native animation viewer. Check this to always default to the system ffmpeg in your path, rather than using any static ffmpeg in hydrus\'s bin directory. (requires restart)' ) )
        
        self._load_images_with_pil = QW.QCheckBox( system_panel )
        self._load_images_with_pil.setToolTip( ClientGUIFunctions.WrapToolTip( 'We are expecting to drop CV and move to PIL exclusively. This used to be a test option but is now default true and may soon be retired.' ) )
        
        self._do_icc_profile_normalisation = QW.QCheckBox( system_panel )
        self._do_icc_profile_normalisation.setToolTip( ClientGUIFunctions.WrapToolTip( 'Should PIL attempt to load ICC Profiles and normalise the colours of an image? This is usually fine, but when it janks out due to an additional OS/GPU ICC Profile, we can turn it off here.' ) )
        
        self._enable_truncated_images_pil = QW.QCheckBox( system_panel )
        self._enable_truncated_images_pil.setToolTip( ClientGUIFunctions.WrapToolTip( 'Should PIL be allowed to load broken images that are missing some data? This is usually fine, but some years ago we had stability problems when this was mixed with OpenCV. Now it is default on, but if you need to, you can disable it here.' ) )
        
        #
        
        filetype_handling_panel = ClientGUICommon.StaticBox( self, 'per-filetype handling' )
        
        media_viewer_list_panel = ClientGUIListCtrl.BetterListCtrlPanel( filetype_handling_panel )
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_MEDIA_VIEWER_OPTIONS.ID, self._GetListCtrlDisplayTuple, self._GetListCtrlSortTuple )
        
        self._filetype_handling_listctrl = ClientGUIListCtrl.BetterListCtrlTreeView( media_viewer_list_panel, 12, model, activation_callback = self.EditMediaViewerOptions, use_simple_delete = True )
        
        media_viewer_list_panel.SetListCtrl( self._filetype_handling_listctrl )
        
        media_viewer_list_panel.AddButton( 'add', self.AddMediaViewerOptions, enabled_check_func = self._CanAddMediaViewOption )
        media_viewer_list_panel.AddButton( 'edit', self.EditMediaViewerOptions, enabled_only_on_single_selection = True )
        media_viewer_list_panel.AddDeleteButton( enabled_check_func = self._CanDeleteMediaViewOptions )
        
        #
        
        self._animation_start_position.setValue( int( HC.options['animation_start_position'] * 100.0 ) )
        self._always_loop_animations.setChecked( self._new_options.GetBoolean( 'always_loop_gifs' ) )
        self._use_legacy_mpv_mediator.setChecked( self._new_options.GetBoolean( 'use_legacy_mpv_mediator' ) )
        self._mpv_loop_playlist_instead_of_file.setChecked( self._new_options.GetBoolean( 'mpv_loop_playlist_instead_of_file' ) )
        self._persist_media_window_mpv.setChecked( self._new_options.GetBoolean( 'persist_media_window_mpv' ) )
        self._mpv_destruction_test.setChecked( self._new_options.GetBoolean( 'mpv_destruction_test' ) )
        self._do_not_setgeometry_on_an_mpv.setChecked( self._new_options.GetBoolean( 'do_not_setgeometry_on_an_mpv' ) )
        self._qt_media_player_opengl_test.setChecked( self._new_options.GetBoolean( 'qt_media_player_opengl_test' ) )
        self._persist_media_window_qt_media_player.setChecked( self._new_options.GetBoolean( 'persist_media_window_qt_media_player' ) )
        self._file_has_transparency_strictness.SetValue( self._new_options.GetInteger( 'file_has_transparency_strictness' ) )
        self._draw_transparency_checkerboard_media_canvas.setChecked( self._new_options.GetBoolean( 'draw_transparency_checkerboard_media_canvas' ) )
        self._draw_transparency_checkerboard_as_greenscreen.setChecked( self._new_options.GetBoolean( 'draw_transparency_checkerboard_as_greenscreen' ) )
        
        media_zooms = self._new_options.GetMediaZooms()
        
        self._media_zooms.setText( ','.join( ( str( media_zoom ) for media_zoom in media_zooms ) ) )
        
        self._media_viewer_zoom_center.SetValue( self._new_options.GetInteger( 'media_viewer_zoom_center' ) )

        self._media_viewer_default_zoom_type_override.SetValue( self._new_options.GetInteger( 'media_viewer_default_zoom_type_override' ) )
        self._preview_default_zoom_type_override.SetValue( self._new_options.GetInteger( 'preview_default_zoom_type_override' ) )
        self._media_viewer_recenter_media_on_window_resize.setChecked( self._new_options.GetBoolean( 'media_viewer_recenter_media_on_window_resize' ) )
        
        self._load_images_with_pil.setChecked( self._new_options.GetBoolean( 'load_images_with_pil' ) )
        self._enable_truncated_images_pil.setChecked( self._new_options.GetBoolean( 'enable_truncated_images_pil' ) )
        self._do_icc_profile_normalisation.setChecked( self._new_options.GetBoolean( 'do_icc_profile_normalisation' ) )
        self._use_system_ffmpeg.setChecked( self._new_options.GetBoolean( 'use_system_ffmpeg' ) )
        
        all_media_view_options = self._new_options.GetMediaViewOptions()
        
        for ( mime, view_options ) in all_media_view_options.items():
            
            data = QP.ListsToTuples( [ mime ] + list( view_options ) )
            
            self._filetype_handling_listctrl.AddData( data )
            
        
        self._filetype_handling_listctrl.Sort()
        
        #
        
        vbox = QP.VBoxLayout()
        
        #
        
        filetype_handling_panel.Add( media_viewer_list_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        rows = []
        
        rows.append( ( 'Centerpoint for media zooming:', self._media_viewer_zoom_center ) )
        rows.append( ( 'Media zooms:', self._media_zooms ) )
        rows.append( ( 'Media Viewer default zoom:', self._media_viewer_default_zoom_type_override ) )
        rows.append( ( 'Preview Viewer default zoom:', self._preview_default_zoom_type_override ) )
        rows.append( ( 'Re-center media on window resize:', self._media_viewer_recenter_media_on_window_resize ) )
        
        gridbox = ClientGUICommon.WrapInGrid( zoom_panel, rows )
        
        zoom_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        rows = []
        
        rows.append( ( 'Start animations this % in:', self._animation_start_position ) )
        rows.append( ( 'Always Loop Animations:', self._always_loop_animations ) )
        
        gridbox = ClientGUICommon.WrapInGrid( animations_panel, rows )
        
        animations_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        rows = []
        
        rows.append( ( 'Set a new mpv.conf on dialog ok?:', self._mpv_conf_path ) )
        rows.append( ( 'DEBUG: Use legacy mpv communication method:', self._use_legacy_mpv_mediator ) )
        rows.append( ( 'DEBUG: Loop Playlist instead of Loop File in mpv:', self._mpv_loop_playlist_instead_of_file ) )
        rows.append( ( 'TEST: Use the same mpv player through media transitions:', self._persist_media_window_mpv ) )
        rows.append( ( 'TEST: Destroy/recreate mpv players instead of recycling them:', self._mpv_destruction_test ) )
        rows.append( ( 'LINUX DEBUG: Do not allow combined setGeometry on mpv window:', self._do_not_setgeometry_on_an_mpv ) )
        
        gridbox = ClientGUICommon.WrapInGrid( mpv_panel, rows )
        
        label = 'MPV loads up the "mpv.conf" file in your database directory. Feel free to edit that file in place any time--it is reloaded in hydrus every time you ok this options dialog. Or, if you have everything set up in a different file already, you can overwrite your mpv.conf from that path here.\n\nNote, however, that applying a new mpv.conf will not "reset/undo" any options that are now ommitted in the new file. If you want to remove a line, edit/update the mpv.conf and then restart the client.'
        
        st = ClientGUICommon.BetterStaticText( mpv_panel, label = label )
        st.setWordWrap( True )
        
        mpv_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
        mpv_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        rows = []
        
        rows.append( ( 'TEST: Use the same QtMediaPlayer through media transitions:', self._persist_media_window_qt_media_player ) )
        rows.append( ( 'TEST: Use OpenGL Window in QtMediaPlayer:', self._qt_media_player_opengl_test ) )
        
        gridbox = ClientGUICommon.WrapInGrid( qt_media_panel, rows )
        
        qt_media_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        rows = []
        
        rows.append( ( 'Consider a file as "having transparency" when:', self._file_has_transparency_strictness ) )
        rows.append( ( 'Draw image transparency as checkerboard:', self._draw_transparency_checkerboard_media_canvas ) )
        rows.append( ( '--Instead of checkerboard, use a bright greenscreen:', self._draw_transparency_checkerboard_as_greenscreen ) )
        
        gridbox = ClientGUICommon.WrapInGrid( transparency_panel, rows )
        
        transparency_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        rows = []
        
        rows.append( ( 'Prefer system FFMPEG:', self._use_system_ffmpeg ) )
        rows.append( ( 'Apply image ICC Profile colour adjustments:', self._do_icc_profile_normalisation ) )
        rows.append( ( 'Allow loading of truncated images:', self._enable_truncated_images_pil ) )
        rows.append( ( 'Load images with PIL:', self._load_images_with_pil ) )
        
        gridbox = ClientGUICommon.WrapInGrid( system_panel, rows )
        
        system_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        QP.AddToLayout( vbox, zoom_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, transparency_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, animations_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, filetype_handling_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, mpv_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, qt_media_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, system_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        self.setLayout( vbox )
        
    
    def _CanAddMediaViewOption( self ):
        
        return len( self._GetUnsetMediaViewFiletypes() ) > 0
        
    
    def _CanDeleteMediaViewOptions( self ):
        
        deletable_mimes = set( HC.SEARCHABLE_MIMES )
        
        selected_mimes = set()
        
        for ( mime, media_show_action, media_start_paused, media_start_with_embed, preview_show_action, preview_start_paused, preview_start_with_embed, zoom_info ) in self._filetype_handling_listctrl.GetData( only_selected = True ):
            
            selected_mimes.add( mime )
            
        
        if len( selected_mimes ) == 0:
            
            return False
            
        
        all_selected_are_deletable = selected_mimes.issubset( deletable_mimes )
        
        return all_selected_are_deletable
        
    
    def _GetCopyOfGeneralMediaViewOptions( self, desired_mime ):
        
        general_mime_type = HC.mimes_to_general_mimetypes[ desired_mime ]
        
        for ( mime, media_show_action, media_start_paused, media_start_with_embed, preview_show_action, preview_start_paused, preview_start_with_embed, zoom_info ) in self._filetype_handling_listctrl.GetData():
            
            if mime == general_mime_type:
                
                view_options = ( desired_mime, media_show_action, media_start_paused, media_start_with_embed, preview_show_action, preview_start_paused, preview_start_with_embed, zoom_info )
                
                return view_options
                
            
        
    
    def _GetUnsetMediaViewFiletypes( self ):
        
        editable_mimes = set( HC.SEARCHABLE_MIMES )
        
        set_mimes = set()
        
        for ( mime, media_show_action, media_start_paused, media_start_with_embed, preview_show_action, preview_start_paused, preview_start_with_embed, zoom_info ) in self._filetype_handling_listctrl.GetData():
            
            set_mimes.add( mime )
            
        
        unset_mimes = editable_mimes.difference( set_mimes )
        
        return unset_mimes
        
    
    def _GetListCtrlDisplayTuple( self, data ):
        
        ( mime, media_show_action, media_start_paused, media_start_with_embed, preview_show_action, preview_start_paused, preview_start_with_embed, zoom_info ) = data
        
        pretty_mime = self._GetPrettyMime( mime )
        
        pretty_media_show_action = CC.media_viewer_action_string_lookup[ media_show_action ]
        
        if media_start_paused:
            
            pretty_media_show_action += ', start paused'
            
        
        if media_start_with_embed:
            
            pretty_media_show_action += ', start with embed button'
            
        
        pretty_preview_show_action = CC.media_viewer_action_string_lookup[ preview_show_action ]
        
        if preview_start_paused:
            
            pretty_preview_show_action += ', start paused'
            
        
        if preview_start_with_embed:
            
            pretty_preview_show_action += ', start with embed button'
            
        
        no_show = { media_show_action, preview_show_action }.isdisjoint( { CC.MEDIA_VIEWER_ACTION_SHOW_WITH_NATIVE, CC.MEDIA_VIEWER_ACTION_SHOW_WITH_MPV, CC.MEDIA_VIEWER_ACTION_SHOW_WITH_QMEDIAPLAYER_VIDEO_WIDGET, CC.MEDIA_VIEWER_ACTION_SHOW_WITH_QMEDIAPLAYER_GRAPHICS_VIEW } )
        
        if no_show:
            
            pretty_zoom_info = ''
            
        else:
            
            pretty_zoom_info = str( zoom_info )
            
        
        display_tuple = ( pretty_mime, pretty_media_show_action, pretty_preview_show_action, pretty_zoom_info )
        
        return display_tuple
        
    
    _GetListCtrlSortTuple = _GetListCtrlDisplayTuple
    
    def _GetPrettyMime( self, mime ):
        
        pretty_mime = HC.mime_string_lookup[ mime ]
        
        if mime not in HC.GENERAL_FILETYPES:
            
            pretty_mime = '{}: {}'.format( HC.mime_string_lookup[ HC.mimes_to_general_mimetypes[ mime ] ], pretty_mime )
            
        
        return pretty_mime
        
    
    def AddMediaViewerOptions( self ):
        
        unset_filetypes = self._GetUnsetMediaViewFiletypes()
        
        if len( unset_filetypes ) == 0:
            
            ClientGUIDialogsMessage.ShowWarning( self, 'You cannot add any more specific filetype options!' )
            
            return
            
        
        choice_tuples = [ ( self._GetPrettyMime( mime ), mime ) for mime in unset_filetypes ]
        
        try:
            
            mime = ClientGUIDialogsQuick.SelectFromList( self, 'select the filetype to add', choice_tuples, sort_tuples = True )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        data = self._GetCopyOfGeneralMediaViewOptions( mime )
        
        title = 'add media view options information'
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, title ) as dlg:
            
            panel = ClientGUIScrolledPanelsEdit.EditMediaViewOptionsPanel( dlg, data )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                new_data = panel.GetValue()
                
                self._filetype_handling_listctrl.AddData( new_data, select_sort_and_scroll = True )
                
            
        
    
    def EditMediaViewerOptions( self ):
        
        data = self._filetype_handling_listctrl.GetTopSelectedData()
        
        if data is None:
            
            return
            
        
        title = 'edit media view options information'
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, title ) as dlg:
            
            panel = ClientGUIScrolledPanelsEdit.EditMediaViewOptionsPanel( dlg, data )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                new_data = panel.GetValue()
                
                self._filetype_handling_listctrl.ReplaceData( data, new_data, sort_and_scroll = True )
                
            
        
    
    def EventZoomsChanged( self, text ):
        
        try:
            
            media_zooms = [ float( media_zoom ) for media_zoom in self._media_zooms.text().split( ',' ) ]
            
            self._media_zooms.setObjectName( '' )
            
        except ValueError:
            
            self._media_zooms.setObjectName( 'HydrusInvalid' )
            
        
        self._media_zooms.style().polish( self._media_zooms )
        
        self._media_zooms.update()
        
    
    def UpdateOptions( self ):
        
        HC.options[ 'animation_start_position' ] = self._animation_start_position.value() / 100.0
        self._new_options.SetBoolean( 'always_loop_gifs', self._always_loop_animations.isChecked() )
        self._new_options.SetBoolean( 'use_legacy_mpv_mediator', self._use_legacy_mpv_mediator.isChecked() )
        self._new_options.SetBoolean( 'mpv_loop_playlist_instead_of_file', self._mpv_loop_playlist_instead_of_file.isChecked() )
        self._new_options.SetBoolean( 'persist_media_window_mpv', self._persist_media_window_mpv.isChecked() )
        self._new_options.SetBoolean( 'mpv_destruction_test', self._mpv_destruction_test.isChecked() )
        self._new_options.SetBoolean( 'do_not_setgeometry_on_an_mpv', self._do_not_setgeometry_on_an_mpv.isChecked() )
        self._new_options.SetBoolean( 'persist_media_window_qt_media_player', self._persist_media_window_qt_media_player.isChecked() )
        self._new_options.SetBoolean( 'qt_media_player_opengl_test', self._qt_media_player_opengl_test.isChecked() )
        self._new_options.SetInteger( 'file_has_transparency_strictness', self._file_has_transparency_strictness.GetValue() )
        self._new_options.SetBoolean( 'draw_transparency_checkerboard_media_canvas', self._draw_transparency_checkerboard_media_canvas.isChecked() )
        self._new_options.SetBoolean( 'draw_transparency_checkerboard_as_greenscreen', self._draw_transparency_checkerboard_as_greenscreen.isChecked() )
        
        try:
            
            media_zooms = [ float( media_zoom ) for media_zoom in self._media_zooms.text().split( ',' ) ]
            
            media_zooms = [ media_zoom for media_zoom in media_zooms if media_zoom > 0.0 ]
            
            if len( media_zooms ) > 0:
                
                self._new_options.SetMediaZooms( media_zooms )
                
            
        except ValueError:
            
            HydrusData.ShowText( 'Could not parse those zooms, so they were not saved!' )
            
        
        self._new_options.SetInteger( 'media_viewer_zoom_center', self._media_viewer_zoom_center.GetValue() )

        self._new_options.SetInteger( 'media_viewer_default_zoom_type_override', self._media_viewer_default_zoom_type_override.GetValue() )
        self._new_options.SetInteger( 'preview_default_zoom_type_override', self._preview_default_zoom_type_override.GetValue() )
        self._new_options.SetBoolean( 'media_viewer_recenter_media_on_window_resize', self._media_viewer_recenter_media_on_window_resize.isChecked() )
        
        self._new_options.SetBoolean( 'load_images_with_pil', self._load_images_with_pil.isChecked() )
        self._new_options.SetBoolean( 'enable_truncated_images_pil', self._enable_truncated_images_pil.isChecked() )
        self._new_options.SetBoolean( 'do_icc_profile_normalisation', self._do_icc_profile_normalisation.isChecked() )
        self._new_options.SetBoolean( 'use_system_ffmpeg', self._use_system_ffmpeg.isChecked() )
        
        mpv_conf_path = self._mpv_conf_path.GetPath()
        
        if mpv_conf_path is not None and mpv_conf_path != '' and os.path.exists( mpv_conf_path ) and os.path.isfile( mpv_conf_path ):
            
            dest_mpv_conf_path = CG.client_controller.GetMPVConfPath()
            
            try:
                
                HydrusPaths.MirrorFile( mpv_conf_path, dest_mpv_conf_path )
                
            except Exception as e:
                
                HydrusData.ShowText( 'Could not set the mpv conf path "{}" to "{}"! Error follows!'.format( mpv_conf_path, dest_mpv_conf_path ) )
                HydrusData.ShowException( e )
                
            
        
        mimes_to_media_view_options = {}
        
        for data in self._filetype_handling_listctrl.GetData():
            
            data = list( data )
            
            mime = data[0]
            
            value = data[1:]
            
            mimes_to_media_view_options[ mime ] = value
            
        
        self._new_options.SetMediaViewOptions( mimes_to_media_view_options )
        
    
