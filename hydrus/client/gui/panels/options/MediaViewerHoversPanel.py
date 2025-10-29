from qtpy import QtWidgets as QW

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.panels.options import ClientGUIOptionsPanelBase
from hydrus.client.gui.widgets import ClientGUICommon

class MediaViewerHoversPanel( ClientGUIOptionsPanelBase.OptionsPagePanel ):
    
    def __init__( self, parent ):
        
        super().__init__( parent )
        
        self._new_options = CG.client_controller.new_options
        
        #
        
        media_canvas_panel = ClientGUICommon.StaticBox( self, 'hover windows and background' )
        
        self._draw_tags_hover_in_media_viewer_background = QW.QCheckBox( media_canvas_panel )
        self._draw_tags_hover_in_media_viewer_background.setToolTip( ClientGUIFunctions.WrapToolTip( 'Draw the left list of tags in the background of the media viewer.' ) )
        self._disable_tags_hover_in_media_viewer = QW.QCheckBox( media_canvas_panel )
        self._disable_tags_hover_in_media_viewer.setToolTip( ClientGUIFunctions.WrapToolTip( 'Disable hovering on the left list of tags in the media viewer (does not affect background draw).' ) )
        self._draw_top_hover_in_media_viewer_background = QW.QCheckBox( media_canvas_panel )
        self._draw_top_hover_in_media_viewer_background.setToolTip( ClientGUIFunctions.WrapToolTip( 'Draw the center-top file metadata in the background of the media viewer.' ) )
        self._draw_top_right_hover_in_media_viewer_background = QW.QCheckBox( media_canvas_panel )
        self._draw_top_right_hover_in_media_viewer_background.setToolTip( ClientGUIFunctions.WrapToolTip( 'Draw the top-right ratings, inbox and URL information in the background of the media viewer.' ) )
        self._disable_top_right_hover_in_media_viewer = QW.QCheckBox( media_canvas_panel )
        self._disable_top_right_hover_in_media_viewer.setToolTip( ClientGUIFunctions.WrapToolTip( 'Disable hovering on the top-right ratings, inbox and URL information in the media viewer (does not affect background draw).' ) )
        self._draw_notes_hover_in_media_viewer_background = QW.QCheckBox( media_canvas_panel )
        self._draw_notes_hover_in_media_viewer_background.setToolTip( ClientGUIFunctions.WrapToolTip( 'Draw the right list of notes in the background of the media viewer.' ) )
        self._draw_bottom_right_index_in_media_viewer_background = QW.QCheckBox( media_canvas_panel )
        self._draw_bottom_right_index_in_media_viewer_background.setToolTip( ClientGUIFunctions.WrapToolTip( 'Draw the bottom-right index string in the background of the media viewer.' ) )
        
        self._use_nice_resolution_strings = QW.QCheckBox( media_canvas_panel )
        self._use_nice_resolution_strings.setToolTip( ClientGUIFunctions.WrapToolTip( 'Use "1080p" instead of "1920x1080" for common resolutions.' ) )
        
        #
        
        top_hover_summary_panel = ClientGUICommon.StaticBox( self, 'top hover file summary' )
        
        self._file_info_line_consider_archived_interesting = QW.QCheckBox( top_hover_summary_panel )
        self._file_info_line_consider_archived_interesting.setToolTip( ClientGUIFunctions.WrapToolTip( 'Should we show the fact a file is archived in the top hover file info summary?' ) )
        
        self._file_info_line_consider_archived_time_interesting = QW.QCheckBox( top_hover_summary_panel )
        self._file_info_line_consider_archived_time_interesting.setToolTip( ClientGUIFunctions.WrapToolTip( 'If we show the archived status, should we show when it happened?' ) )
        
        self._file_info_line_consider_file_services_interesting = QW.QCheckBox( top_hover_summary_panel )
        self._file_info_line_consider_file_services_interesting.setToolTip( ClientGUIFunctions.WrapToolTip( 'Should we show all the file services a file is in in the top hover file info summary?' ) )
        
        self._file_info_line_consider_file_services_import_times_interesting = QW.QCheckBox( top_hover_summary_panel )
        self._file_info_line_consider_file_services_import_times_interesting.setToolTip( ClientGUIFunctions.WrapToolTip( 'If we show the file services, should we show when they were added?' ) )
        
        self._file_info_line_consider_trash_time_interesting = QW.QCheckBox( top_hover_summary_panel )
        self._file_info_line_consider_trash_time_interesting.setToolTip( ClientGUIFunctions.WrapToolTip( 'Should we show the time a file is trashed in the top hover file info summary?' ) )
        
        self._file_info_line_consider_trash_reason_interesting = QW.QCheckBox( top_hover_summary_panel )
        self._file_info_line_consider_trash_reason_interesting.setToolTip( ClientGUIFunctions.WrapToolTip( 'Should we show the reason a file is trashed in the top hover file info summary?' ) )
        
        self._hide_uninteresting_modified_time = QW.QCheckBox( top_hover_summary_panel )
        self._hide_uninteresting_modified_time.setToolTip( ClientGUIFunctions.WrapToolTip( 'If the file has a modified time similar to its import time (specifically, the number of seconds since both events differs by less than 10%), hide the modified time in the top hover file info summary.' ) )
        
        #
        
        preview_hovers_panel = ClientGUICommon.StaticBox( self, 'preview window hovers' )
        
        self._preview_window_hover_top_right_shows_popup = QW.QCheckBox( preview_hovers_panel )
        self._preview_window_hover_top_right_shows_popup.setToolTip( ClientGUIFunctions.WrapToolTip( 'When you hover over the top right of the preview window, show the same top right popup window as in the media viewer.' ) )
        
        self._draw_top_right_hover_in_preview_window_background = QW.QCheckBox( preview_hovers_panel )
        self._draw_top_right_hover_in_preview_window_background.setToolTip( ClientGUIFunctions.WrapToolTip( 'Also draw the top-right hover window in the background of the preview window.' ) )
        
        #
        
        self._draw_tags_hover_in_media_viewer_background.setChecked( self._new_options.GetBoolean( 'draw_tags_hover_in_media_viewer_background' ) )
        self._disable_tags_hover_in_media_viewer.setChecked( self._new_options.GetBoolean( 'disable_tags_hover_in_media_viewer' ) )
        self._draw_top_hover_in_media_viewer_background.setChecked( self._new_options.GetBoolean( 'draw_top_hover_in_media_viewer_background' ) )
        self._draw_top_right_hover_in_media_viewer_background.setChecked( self._new_options.GetBoolean( 'draw_top_right_hover_in_media_viewer_background' ) )
        self._disable_top_right_hover_in_media_viewer.setChecked( self._new_options.GetBoolean( 'disable_top_right_hover_in_media_viewer' ) )
        self._draw_notes_hover_in_media_viewer_background.setChecked( self._new_options.GetBoolean( 'draw_notes_hover_in_media_viewer_background' ) )
        self._draw_bottom_right_index_in_media_viewer_background.setChecked( self._new_options.GetBoolean( 'draw_bottom_right_index_in_media_viewer_background' ) )
        self._use_nice_resolution_strings.setChecked( self._new_options.GetBoolean( 'use_nice_resolution_strings' ) )
        
        self._file_info_line_consider_archived_interesting.setChecked( self._new_options.GetBoolean( 'file_info_line_consider_archived_interesting' ) )
        self._file_info_line_consider_archived_time_interesting.setChecked( self._new_options.GetBoolean( 'file_info_line_consider_archived_time_interesting' ) )
        self._file_info_line_consider_file_services_interesting.setChecked( self._new_options.GetBoolean( 'file_info_line_consider_file_services_interesting' ) )
        self._file_info_line_consider_file_services_import_times_interesting.setChecked( self._new_options.GetBoolean( 'file_info_line_consider_file_services_import_times_interesting' ) )
        self._file_info_line_consider_trash_time_interesting.setChecked( self._new_options.GetBoolean( 'file_info_line_consider_trash_time_interesting' ) )
        self._file_info_line_consider_trash_reason_interesting.setChecked( self._new_options.GetBoolean( 'file_info_line_consider_trash_reason_interesting' ) )
        self._hide_uninteresting_modified_time.setChecked( self._new_options.GetBoolean( 'hide_uninteresting_modified_time' ) )
        
        self._preview_window_hover_top_right_shows_popup.setChecked( self._new_options.GetBoolean( 'preview_window_hover_top_right_shows_popup' ) )
        self._draw_top_right_hover_in_preview_window_background.setChecked( self._new_options.GetBoolean( 'draw_top_right_hover_in_preview_window_background' ) )
        
        #
        
        rows = []
        
        rows.append( ( 'Draw tags hover-window information in the background of the viewer:', self._draw_tags_hover_in_media_viewer_background ) )
        rows.append( ( 'Do not pop-in tags hover-window on mouseover:', self._disable_tags_hover_in_media_viewer ) )
        rows.append( ( 'Draw top hover-window information in the background of the viewer:', self._draw_top_hover_in_media_viewer_background ) )
        rows.append( ( 'Draw top-right hover-window information in the background of the viewer:', self._draw_top_right_hover_in_media_viewer_background ) )
        rows.append( ( 'Do not pop-in top-right hover-window on mouseover:', self._disable_top_right_hover_in_media_viewer ) )
        rows.append( ( 'Draw notes hover-window information in the background of the viewer:', self._draw_notes_hover_in_media_viewer_background ) )
        rows.append( ( 'Draw bottom-right index text in the background of the viewer:', self._draw_bottom_right_index_in_media_viewer_background ) )
        rows.append( ( 'Swap in common resolution labels:', self._use_nice_resolution_strings ) )
        
        media_canvas_gridbox = ClientGUICommon.WrapInGrid( media_canvas_panel, rows )
        
        media_canvas_panel.Add( media_canvas_gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        rows = []
        
        rows.append( ( 'Show archived status: ', self._file_info_line_consider_archived_interesting ) )
        rows.append( ( 'Show archived time: ', self._file_info_line_consider_archived_time_interesting ) )
        rows.append( ( 'Show file services: ', self._file_info_line_consider_file_services_interesting ) )
        rows.append( ( 'Show file service add times: ', self._file_info_line_consider_file_services_import_times_interesting ) )
        rows.append( ( 'Show file trash times: ', self._file_info_line_consider_trash_time_interesting ) )
        rows.append( ( 'Show file trash reasons: ', self._file_info_line_consider_trash_reason_interesting ) )
        rows.append( ( 'Hide uninteresting modified times: ', self._hide_uninteresting_modified_time ) )
        
        top_hover_summary_gridbox = ClientGUICommon.WrapInGrid( top_hover_summary_panel, rows )
        
        label = 'The top hover window shows a text summary of the file, usually the basic file metadata and the time it was imported. You can show more information here.'
        label += '\n\n'
        label += 'You set this same text to show in the main window status bar for single thumbnail selections under the "thumbnails" page.'
        
        st = ClientGUICommon.BetterStaticText( top_hover_summary_panel, label = label )
        st.setWordWrap( True )
        
        top_hover_summary_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
        top_hover_summary_panel.Add( top_hover_summary_gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        rows = []
        
        rows.append( ( 'Show top-right hover window popup in the preview window: ', self._preview_window_hover_top_right_shows_popup ) )
        rows.append( ( 'Draw top-right hover in preview window background: ', self._draw_top_right_hover_in_preview_window_background ) )
        
        preview_hovers_gridbox = ClientGUICommon.WrapInGrid( preview_hovers_panel, rows )
        
        preview_hovers_panel.Add( preview_hovers_gridbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        vbox = QP.VBoxLayout()
        
        label = 'Hover windows are the pop-in panels in the Media Viewers. You typically have tags on the left, file info up top, and ratings, notes, and sometimes duplicate controls down the right.'
        st = ClientGUICommon.BetterStaticText( self, label = label )
        st.setWordWrap( True )
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, media_canvas_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, top_hover_summary_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, preview_hovers_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.addStretch( 0 )
        
        self.setLayout( vbox )
        
        self._file_info_line_consider_archived_interesting.clicked.connect( self._UpdateFileInfoLineWidgets )
        self._file_info_line_consider_file_services_interesting.clicked.connect( self._UpdateFileInfoLineWidgets )
        
        self._UpdateFileInfoLineWidgets()
        
    
    def _UpdateFileInfoLineWidgets( self ):
        
        self._file_info_line_consider_archived_time_interesting.setEnabled( self._file_info_line_consider_archived_interesting.isChecked() )
        self._file_info_line_consider_file_services_import_times_interesting.setEnabled( self._file_info_line_consider_file_services_interesting.isChecked() )
        
    
    def UpdateOptions( self ):
        
        self._new_options.SetBoolean( 'draw_tags_hover_in_media_viewer_background', self._draw_tags_hover_in_media_viewer_background.isChecked() )
        self._new_options.SetBoolean( 'disable_tags_hover_in_media_viewer', self._disable_tags_hover_in_media_viewer.isChecked() )
        self._new_options.SetBoolean( 'draw_top_hover_in_media_viewer_background', self._draw_top_hover_in_media_viewer_background.isChecked() )
        self._new_options.SetBoolean( 'draw_top_right_hover_in_media_viewer_background', self._draw_top_right_hover_in_media_viewer_background.isChecked() )
        self._new_options.SetBoolean( 'disable_top_right_hover_in_media_viewer', self._disable_top_right_hover_in_media_viewer.isChecked() )
        self._new_options.SetBoolean( 'draw_notes_hover_in_media_viewer_background', self._draw_notes_hover_in_media_viewer_background.isChecked() )
        self._new_options.SetBoolean( 'draw_bottom_right_index_in_media_viewer_background', self._draw_bottom_right_index_in_media_viewer_background.isChecked() )
        self._new_options.SetBoolean( 'use_nice_resolution_strings', self._use_nice_resolution_strings.isChecked() )
        
        self._new_options.SetBoolean( 'preview_window_hover_top_right_shows_popup', self._preview_window_hover_top_right_shows_popup.isChecked() )
        self._new_options.SetBoolean( 'draw_top_right_hover_in_preview_window_background', self._draw_top_right_hover_in_preview_window_background.isChecked() )
        
        self._new_options.SetBoolean( 'file_info_line_consider_archived_interesting', self._file_info_line_consider_archived_interesting.isChecked() )
        self._new_options.SetBoolean( 'file_info_line_consider_archived_time_interesting', self._file_info_line_consider_archived_time_interesting.isChecked() )
        self._new_options.SetBoolean( 'file_info_line_consider_file_services_interesting', self._file_info_line_consider_file_services_interesting.isChecked() )
        self._new_options.SetBoolean( 'file_info_line_consider_file_services_import_times_interesting', self._file_info_line_consider_file_services_import_times_interesting.isChecked() )
        self._new_options.SetBoolean( 'file_info_line_consider_trash_time_interesting', self._file_info_line_consider_trash_time_interesting.isChecked() )
        self._new_options.SetBoolean( 'file_info_line_consider_trash_reason_interesting', self._file_info_line_consider_trash_reason_interesting.isChecked() )
        self._new_options.SetBoolean( 'hide_uninteresting_modified_time', self._hide_uninteresting_modified_time.isChecked() )
        
    
