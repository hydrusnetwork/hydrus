from qtpy import QtWidgets as QW

from hydrus.core import HydrusTime

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.metadata import ClientGUITime
from hydrus.client.gui.panels.options import ClientGUIOptionsPanelBase
from hydrus.client.gui.widgets import ClientGUICommon

class FileViewingStatisticsPanel( ClientGUIOptionsPanelBase.OptionsPagePanel ):
    
    def __init__( self, parent ):
        
        super().__init__( parent )
        
        self._new_options = CG.client_controller.new_options
        
        self._file_viewing_statistics_active = QW.QCheckBox( self )
        self._file_viewing_statistics_active_on_archive_delete_filter = QW.QCheckBox( self )
        self._file_viewing_statistics_active_on_dupe_filter = QW.QCheckBox( self )
        self._file_viewing_statistics_media_min_time = ClientGUITime.NoneableTimeDeltaWidget( self, 2.0, none_phrase = 'count every view', minutes = True, seconds = True, milliseconds = True )
        min_tt = 'If you scroll quickly through many files, you probably do not want to count each of those loads as a view. Set a reasonable minimum here and brief looks will not be counted.'
        self._file_viewing_statistics_media_min_time.setToolTip( ClientGUIFunctions.WrapToolTip( min_tt ) )
        self._file_viewing_statistics_media_max_time = ClientGUITime.NoneableTimeDeltaWidget( self, 600.0, hours = True, minutes = True, seconds = True, milliseconds = True )
        max_tt = 'If you view a file for a very long time, the recorded viewtime is truncated to this. This stops an outrageous viewtime being saved because you left something open in the background. If the media you view has duration, like a video, the max viewtime is five times its length or this, whichever is larger.'
        self._file_viewing_statistics_media_max_time.setToolTip( ClientGUIFunctions.WrapToolTip( max_tt ) )
        
        self._file_viewing_statistics_preview_min_time = ClientGUITime.NoneableTimeDeltaWidget( self, 5.0, none_phrase = 'count every view', minutes = True, seconds = True, milliseconds = True )
        self._file_viewing_statistics_preview_min_time.setToolTip( ClientGUIFunctions.WrapToolTip( min_tt ) )
        self._file_viewing_statistics_preview_max_time = ClientGUITime.NoneableTimeDeltaWidget( self, 60.0, hours = True, minutes = True, seconds = True, milliseconds = True )
        self._file_viewing_statistics_preview_max_time.setToolTip( ClientGUIFunctions.WrapToolTip( max_tt ) )
        
        file_viewing_stats_interesting_canvas_types = self._new_options.GetIntegerList( 'file_viewing_stats_interesting_canvas_types' )
        
        self._file_viewing_stats_interesting_canvas_types = ClientGUICommon.BetterCheckBoxList( self )
        
        self._file_viewing_stats_interesting_canvas_types.Append( 'media views', CC.CANVAS_MEDIA_VIEWER, starts_checked = CC.CANVAS_MEDIA_VIEWER in file_viewing_stats_interesting_canvas_types )
        self._file_viewing_stats_interesting_canvas_types.Append( 'preview views', CC.CANVAS_PREVIEW, starts_checked = CC.CANVAS_PREVIEW in file_viewing_stats_interesting_canvas_types )
        self._file_viewing_stats_interesting_canvas_types.Append( 'client api views', CC.CANVAS_CLIENT_API, starts_checked = CC.CANVAS_CLIENT_API in file_viewing_stats_interesting_canvas_types )
        
        self._file_viewing_stats_interesting_canvas_types.SetHeightBasedOnContents()
        
        tt = 'This will also configure what counts when files are sorted by views/viewtime.'
        
        self._file_viewing_stats_interesting_canvas_types.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._file_viewing_stats_menu_display = ClientGUICommon.BetterChoice( self )
        
        self._file_viewing_stats_menu_display.addItem( 'show a combined value, and stack the separate values a submenu', CC.FILE_VIEWING_STATS_MENU_DISPLAY_SUMMED_AND_THEN_SUBMENU )
        self._file_viewing_stats_menu_display.addItem( 'stack the separate values', CC.FILE_VIEWING_STATS_MENU_DISPLAY_STACKED )
        
        #
        
        self._file_viewing_statistics_active.setChecked( self._new_options.GetBoolean( 'file_viewing_statistics_active' ) )
        self._file_viewing_statistics_active_on_archive_delete_filter.setChecked( self._new_options.GetBoolean( 'file_viewing_statistics_active_on_archive_delete_filter' ) )
        self._file_viewing_statistics_active_on_dupe_filter.setChecked( self._new_options.GetBoolean( 'file_viewing_statistics_active_on_dupe_filter' ) )
        self._file_viewing_statistics_media_min_time.SetValue( HydrusTime.SecondiseMSFloat( self._new_options.GetNoneableInteger( 'file_viewing_statistics_media_min_time_ms' ) ) )
        self._file_viewing_statistics_media_max_time.SetValue( HydrusTime.SecondiseMSFloat( self._new_options.GetNoneableInteger( 'file_viewing_statistics_media_max_time_ms' ) ) )
        self._file_viewing_statistics_preview_min_time.SetValue( HydrusTime.SecondiseMSFloat( self._new_options.GetNoneableInteger( 'file_viewing_statistics_preview_min_time_ms' ) ) )
        self._file_viewing_statistics_preview_max_time.SetValue( HydrusTime.SecondiseMSFloat( self._new_options.GetNoneableInteger( 'file_viewing_statistics_preview_max_time_ms' ) ) )
        
        self._file_viewing_stats_menu_display.SetValue( self._new_options.GetInteger( 'file_viewing_stats_menu_display' ) )
        
        #
        
        vbox = QP.VBoxLayout()
        
        rows = []
        
        rows.append( ( 'Enable file viewing statistics tracking?:', self._file_viewing_statistics_active ) )
        rows.append( ( 'Enable file viewing statistics tracking in the archive/delete filter?:', self._file_viewing_statistics_active_on_archive_delete_filter ) )
        rows.append( ( 'Enable file viewing statistics tracking in the duplicate filter?:', self._file_viewing_statistics_active_on_dupe_filter ) )
        rows.append( ( 'Min time to view on media viewer to count as a view:', self._file_viewing_statistics_media_min_time ) )
        rows.append( ( 'Cap any view on the media viewer to this maximum time:', self._file_viewing_statistics_media_max_time ) )
        rows.append( ( 'Min time to view on preview viewer to count as a view:', self._file_viewing_statistics_preview_min_time ) )
        rows.append( ( 'Cap any view on the preview viewer to this maximum time:', self._file_viewing_statistics_preview_max_time ) )
        rows.append( ( 'Show viewing stats on media right-click menus?:', self._file_viewing_stats_menu_display ) )
        rows.append( ( 'Which views to show?:', self._file_viewing_stats_interesting_canvas_types ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.addStretch( 0 )
        
        self.setLayout( vbox )
        
    
    def UpdateOptions( self ):
        
        self._new_options.SetBoolean( 'file_viewing_statistics_active', self._file_viewing_statistics_active.isChecked() )
        self._new_options.SetBoolean( 'file_viewing_statistics_active_on_archive_delete_filter', self._file_viewing_statistics_active_on_archive_delete_filter.isChecked() )
        self._new_options.SetBoolean( 'file_viewing_statistics_active_on_dupe_filter', self._file_viewing_statistics_active_on_dupe_filter.isChecked() )
        self._new_options.SetNoneableInteger( 'file_viewing_statistics_media_min_time_ms', HydrusTime.MillisecondiseS( self._file_viewing_statistics_media_min_time.GetValue() ) )
        self._new_options.SetNoneableInteger( 'file_viewing_statistics_media_max_time_ms', HydrusTime.MillisecondiseS( self._file_viewing_statistics_media_max_time.GetValue() ) )
        self._new_options.SetNoneableInteger( 'file_viewing_statistics_preview_min_time_ms', HydrusTime.MillisecondiseS( self._file_viewing_statistics_preview_min_time.GetValue() ) )
        self._new_options.SetNoneableInteger( 'file_viewing_statistics_preview_max_time_ms', HydrusTime.MillisecondiseS( self._file_viewing_statistics_preview_max_time.GetValue() ) )
        
        self._new_options.SetInteger( 'file_viewing_stats_menu_display', self._file_viewing_stats_menu_display.GetValue() )
        self._new_options.SetIntegerList( 'file_viewing_stats_interesting_canvas_types', self._file_viewing_stats_interesting_canvas_types.GetValue() )
        
    
