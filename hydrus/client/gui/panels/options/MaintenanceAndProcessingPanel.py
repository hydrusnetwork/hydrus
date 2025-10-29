from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusPSUtil
from hydrus.core import HydrusTime

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.metadata import ClientGUITime
from hydrus.client.gui.panels.options import ClientGUIOptionsPanelBase
from hydrus.client.gui.widgets import ClientGUICommon

class MaintenanceAndProcessingPanel( ClientGUIOptionsPanelBase.OptionsPagePanel ):
    
    def __init__( self, parent ):
        
        super().__init__( parent )
        
        self._new_options = CG.client_controller.new_options
        
        self._jobs_panel = ClientGUICommon.StaticBox( self, 'when to run high cpu jobs' )
        
        #
        
        self._idle_panel = ClientGUICommon.StaticBox( self._jobs_panel, 'idle', can_expand = True, start_expanded = False )
        
        self._idle_normal = QW.QCheckBox( self._idle_panel )
        self._idle_normal.clicked.connect( self._EnableDisableIdleNormal )
        
        self._idle_period = ClientGUICommon.NoneableSpinCtrl( self._idle_panel, 30, min = 1, max = 1000, multiplier = 60, unit = 'minutes', none_phrase = 'ignore normal browsing' )
        self._idle_mouse_period = ClientGUICommon.NoneableSpinCtrl( self._idle_panel, 10, min = 1, max = 1000, multiplier = 60, unit = 'minutes', none_phrase = 'ignore mouse movements' )
        self._idle_mouse_period.setToolTip( ClientGUIFunctions.WrapToolTip( 'This applies to mouse movements anywhere in your system, not just over the hydrus window.' ) )
        self._idle_mode_client_api_timeout = ClientGUICommon.NoneableSpinCtrl( self._idle_panel, 5, min = 1, max = 1000, multiplier = 60, unit = 'minutes', none_phrase = 'ignore client api' )
        self._system_busy_cpu_percent = ClientGUICommon.BetterSpinBox( self._idle_panel, min = 5, max = 99 )
        self._system_busy_cpu_count = ClientGUICommon.NoneableSpinCtrl( self._idle_panel, 1, min = 1, max = 64, unit = 'cores', none_phrase = 'ignore cpu usage' )
        
        #
        
        self._shutdown_panel = ClientGUICommon.StaticBox( self._jobs_panel, 'shutdown', can_expand = True, start_expanded = False )
        
        self._idle_shutdown = ClientGUICommon.BetterChoice( self._shutdown_panel )
        
        for idle_id in ( CC.IDLE_NOT_ON_SHUTDOWN, CC.IDLE_ON_SHUTDOWN, CC.IDLE_ON_SHUTDOWN_ASK_FIRST ):
            
            self._idle_shutdown.addItem( CC.idle_string_lookup[ idle_id], idle_id )
            
        
        self._idle_shutdown.currentIndexChanged.connect( self._EnableDisableIdleShutdown )
        
        self._idle_shutdown_max_minutes = ClientGUICommon.BetterSpinBox( self._shutdown_panel, min=1, max=1440 )
        self._shutdown_work_period = ClientGUITime.TimeDeltaButton( self._shutdown_panel, min = 60, days = True, hours = True, minutes = True )
        
        #
        
        self._file_maintenance_panel = ClientGUICommon.StaticBox( self, 'file maintenance', can_expand = True, start_expanded = False )
        
        min_unit_value = 1
        max_unit_value = 1000
        min_time_delta = 1
        
        self._file_maintenance_during_idle = QW.QCheckBox( self._file_maintenance_panel )
        
        self._file_maintenance_idle_throttle_velocity = ClientGUITime.VelocityCtrl( self._file_maintenance_panel, min_unit_value, max_unit_value, min_time_delta, minutes = True, seconds = True, per_phrase = 'every', unit = 'heavy work units' )
        
        self._file_maintenance_during_active = QW.QCheckBox( self._file_maintenance_panel )
        
        self._file_maintenance_active_throttle_velocity = ClientGUITime.VelocityCtrl( self._file_maintenance_panel, min_unit_value, max_unit_value, min_time_delta, minutes = True, seconds = True, per_phrase = 'every', unit = 'heavy work units' )
        
        tt = 'Different jobs will count for more or less weight. A file metadata reparse will count as one work unit, but quicker jobs like checking for file presence will count as fractions of one and will will work more frequently.'
        tt += '\n' * 2
        tt += 'Please note that this throttle is not rigorous for long timescales, as file processing history is not currently saved on client exit. If you restart the client, the file manager thinks it has run 0 jobs and will be happy to run until the throttle kicks in again.'
        
        self._file_maintenance_idle_throttle_velocity.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        self._file_maintenance_active_throttle_velocity.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        #
        
        self._repository_processing_panel = ClientGUICommon.StaticBox( self, 'repository processing', can_expand = True, start_expanded = False )
        
        self._repository_processing_work_time_very_idle = ClientGUITime.TimeDeltaWidget( self._repository_processing_panel, min = 0.1, seconds = True, milliseconds = True )
        tt = 'DO NOT CHANGE UNLESS YOU KNOW WHAT YOU ARE DOING. Repository processing operates on a work-rest cycle. This setting determines how long it should work for in each work packet. Actual work time will normally be a little larger than this. Very Idle is after an hour of idle mode.'
        self._repository_processing_work_time_very_idle.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._repository_processing_rest_percentage_very_idle = ClientGUICommon.BetterSpinBox( self._repository_processing_panel, min = 0, max = 100000 )
        tt = 'DO NOT CHANGE UNLESS YOU KNOW WHAT YOU ARE DOING. Repository processing operates on a work-rest cycle. This setting determines how long it should wait before starting a new work packet, in multiples of the last work time. Very Idle is after an hour of idle mode.'
        self._repository_processing_rest_percentage_very_idle.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._repository_processing_work_time_idle = ClientGUITime.TimeDeltaWidget( self._repository_processing_panel, min = 0.1, seconds = True, milliseconds = True )
        tt = 'DO NOT CHANGE UNLESS YOU KNOW WHAT YOU ARE DOING. Repository processing operates on a work-rest cycle. This setting determines how long it should work for in each work packet. Actual work time will normally be a little larger than this. This is for idle mode.'
        self._repository_processing_work_time_idle.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._repository_processing_rest_percentage_idle = ClientGUICommon.BetterSpinBox( self._repository_processing_panel, min = 0, max = 100000 )
        tt = 'DO NOT CHANGE UNLESS YOU KNOW WHAT YOU ARE DOING. Repository processing operates on a work-rest cycle. This setting determines how long it should wait before starting a new work packet, in multiples of the last work time. This is for idle mode.'
        self._repository_processing_rest_percentage_idle.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._repository_processing_work_time_normal = ClientGUITime.TimeDeltaWidget( self._repository_processing_panel, min = 0.1, seconds = True, milliseconds = True )
        tt = 'DO NOT CHANGE UNLESS YOU KNOW WHAT YOU ARE DOING. Repository processing operates on a work-rest cycle. This setting determines how long it should work for in each work packet. Actual work time will normally be a little larger than this. This is for when you force-start work from review services.'
        self._repository_processing_work_time_normal.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._repository_processing_rest_percentage_normal = ClientGUICommon.BetterSpinBox( self._repository_processing_panel, min = 0, max = 100000 )
        tt = 'DO NOT CHANGE UNLESS YOU KNOW WHAT YOU ARE DOING. Repository processing operates on a work-rest cycle. This setting determines how long it should wait before starting a new work packet, in multiples of the last work time. This is for when you force-start work from review services.'
        self._repository_processing_rest_percentage_normal.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        #
        
        self._tag_display_processing_panel = ClientGUICommon.StaticBox( self, 'sibling/parent sync processing', can_expand = True, start_expanded = False )
        
        self._tag_display_maintenance_during_idle = QW.QCheckBox( self._tag_display_processing_panel )
        self._tag_display_maintenance_during_active = QW.QCheckBox( self._tag_display_processing_panel )
        tt = 'This can be a real killer. If you are catching up with the PTR and notice a lot of lag bumps, sometimes several seconds long, try turning this off.'
        self._tag_display_maintenance_during_active.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._tag_display_processing_work_time_idle = ClientGUITime.TimeDeltaWidget( self._tag_display_processing_panel, min = 0.1, seconds = True, milliseconds = True )
        tt = 'DO NOT CHANGE UNLESS YOU KNOW WHAT YOU ARE DOING. Sibling/parent sync operates on a work-rest cycle. This setting determines how long it should work for in each work packet. Actual work time will normally be a little larger than this. This is for idle mode.'
        self._tag_display_processing_work_time_idle.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._tag_display_processing_rest_percentage_idle = ClientGUICommon.BetterSpinBox( self._tag_display_processing_panel, min = 0, max = 100000 )
        tt = 'DO NOT CHANGE UNLESS YOU KNOW WHAT YOU ARE DOING. Sibling/parent sync operates on a work-rest cycle. This setting determines how long it should wait before starting a new work packet, in multiples of the last work time. This is for idle mode.'
        self._tag_display_processing_rest_percentage_idle.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._tag_display_processing_work_time_normal = ClientGUITime.TimeDeltaWidget( self._tag_display_processing_panel, min = 0.1, seconds = True, milliseconds = True )
        tt = 'DO NOT CHANGE UNLESS YOU KNOW WHAT YOU ARE DOING. Sibling/parent sync operates on a work-rest cycle. This setting determines how long it should work for in each work packet. Actual work time will normally be a little larger than this. This is for when you force-start work from review services.'
        self._tag_display_processing_work_time_normal.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._tag_display_processing_rest_percentage_normal = ClientGUICommon.BetterSpinBox( self._tag_display_processing_panel, min = 0, max = 100000 )
        tt = 'DO NOT CHANGE UNLESS YOU KNOW WHAT YOU ARE DOING. Sibling/parent sync operates on a work-rest cycle. This setting determines how long it should wait before starting a new work packet, in multiples of the last work time. This is for when you force-start work from review services.'
        self._tag_display_processing_rest_percentage_normal.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._tag_display_processing_work_time_work_hard = ClientGUITime.TimeDeltaWidget( self._tag_display_processing_panel, min = 0.1, seconds = True, milliseconds = True )
        tt = 'DO NOT CHANGE UNLESS YOU KNOW WHAT YOU ARE DOING. Sibling/parent sync operates on a work-rest cycle. This setting determines how long it should work for in each work packet. Actual work time will normally be a little larger than this. This is for when you force it to work hard through the dialog.'
        self._tag_display_processing_work_time_work_hard.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._tag_display_processing_rest_percentage_work_hard = ClientGUICommon.BetterSpinBox( self._tag_display_processing_panel, min = 0, max = 100000 )
        tt = 'DO NOT CHANGE UNLESS YOU KNOW WHAT YOU ARE DOING. Sibling/parent sync operates on a work-rest cycle. This setting determines how long it should wait before starting a new work packet, in multiples of the last work time. This is for when you force it to work hard through the dialog.'
        self._tag_display_processing_rest_percentage_work_hard.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        #
        
        self._potential_duplicates_panel = ClientGUICommon.StaticBox( self, 'potential duplicates search', can_expand = True, start_expanded = False )
        
        self._maintain_similar_files_duplicate_pairs_during_idle = QW.QCheckBox( self._potential_duplicates_panel )
        
        self._maintain_similar_files_duplicate_pairs_during_active = QW.QCheckBox( self._potential_duplicates_panel )
        
        self._potential_duplicates_search_work_time_idle = ClientGUITime.TimeDeltaWidget( self._potential_duplicates_panel, min = 0.02, seconds = True, milliseconds = True )
        tt = 'DO NOT CHANGE UNLESS YOU KNOW WHAT YOU ARE DOING. Potential search operates on a work-rest cycle. This setting determines how long it should work for in each work packet. Actual work time will normally be a little larger than this, and on large databases the minimum work time may be upwards of several seconds.'
        self._potential_duplicates_search_work_time_idle.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._potential_duplicates_search_rest_percentage_idle = ClientGUICommon.BetterSpinBox( self._potential_duplicates_panel, min = 0, max = 100000 )
        tt = 'DO NOT CHANGE UNLESS YOU KNOW WHAT YOU ARE DOING. Potential search operates on a work-rest cycle. This setting determines how long it should wait before starting a new work packet, as a percentage of the last work time.'
        self._potential_duplicates_search_rest_percentage_idle.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._potential_duplicates_search_work_time_active = ClientGUITime.TimeDeltaWidget( self._potential_duplicates_panel, min = 0.02, seconds = True, milliseconds = True )
        tt = 'DO NOT CHANGE UNLESS YOU KNOW WHAT YOU ARE DOING. Potential search operates on a work-rest cycle. This setting determines how long it should work for in each work packet. Actual work time will normally be a little larger than this, and on large databases the minimum work time may be upwards of several seconds.'
        self._potential_duplicates_search_work_time_active.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._potential_duplicates_search_rest_percentage_active = ClientGUICommon.BetterSpinBox( self._potential_duplicates_panel, min = 0, max = 100000 )
        tt = 'DO NOT CHANGE UNLESS YOU KNOW WHAT YOU ARE DOING. Potential search operates on a work-rest cycle. This setting determines how long it should wait before starting a new work packet, as a percentage of the last work time.'
        self._potential_duplicates_search_rest_percentage_active.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        #
        
        self._duplicates_auto_resolution_panel = ClientGUICommon.StaticBox( self, 'duplicates auto-resolution', can_expand = True, start_expanded = False )
        
        self._duplicates_auto_resolution_during_idle = QW.QCheckBox( self._duplicates_auto_resolution_panel )
        
        self._duplicates_auto_resolution_during_active = QW.QCheckBox( self._duplicates_auto_resolution_panel )
        
        self._duplicates_auto_resolution_work_time_idle = ClientGUITime.TimeDeltaWidget( self._duplicates_auto_resolution_panel, min = 0.1, seconds = True, milliseconds = True )
        tt = 'DO NOT CHANGE UNLESS YOU KNOW WHAT YOU ARE DOING. Duplicates auto-resolution operates on a work-rest cycle. This setting determines how long it should work for in each work packet. Actual work time will normally be a little larger than this, and when it hits large files it may be upwards of several seconds.'
        self._duplicates_auto_resolution_work_time_idle.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._duplicates_auto_resolution_rest_percentage_idle = ClientGUICommon.BetterSpinBox( self._duplicates_auto_resolution_panel, min = 0, max = 100000 )
        tt = 'DO NOT CHANGE UNLESS YOU KNOW WHAT YOU ARE DOING. Duplicates auto-resolution operates on a work-rest cycle. This setting determines how long it should wait before starting a new work packet, as a percentage of the last work time.'
        self._duplicates_auto_resolution_rest_percentage_idle.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._duplicates_auto_resolution_work_time_active = ClientGUITime.TimeDeltaWidget( self._duplicates_auto_resolution_panel, min = 0.1, seconds = True, milliseconds = True )
        tt = 'DO NOT CHANGE UNLESS YOU KNOW WHAT YOU ARE DOING. Duplicates auto-resolution operates on a work-rest cycle. This setting determines how long it should work for in each work packet. Actual work time will normally be a little larger than this, and when it hits large files it may be upwards of several seconds.'
        self._duplicates_auto_resolution_work_time_active.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._duplicates_auto_resolution_rest_percentage_active = ClientGUICommon.BetterSpinBox( self._duplicates_auto_resolution_panel, min = 0, max = 100000 )
        tt = 'DO NOT CHANGE UNLESS YOU KNOW WHAT YOU ARE DOING. Duplicates auto-resolution operates on a work-rest cycle. This setting determines how long it should wait before starting a new work packet, as a percentage of the last work time.'
        self._duplicates_auto_resolution_rest_percentage_active.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        #
        
        self._deferred_table_delete_panel = ClientGUICommon.StaticBox( self, 'deferred table delete', can_expand = True, start_expanded = False )
        
        self._deferred_table_delete_work_time_idle = ClientGUITime.TimeDeltaWidget( self._deferred_table_delete_panel, min = 0.1, seconds = True, milliseconds = True )
        tt = 'DO NOT CHANGE UNLESS YOU KNOW WHAT YOU ARE DOING. Deferred table delete operates on a work-rest cycle. This setting determines how long it should work for in each work packet. Actual work time will normally be a little larger than this. This is for idle mode.'
        self._deferred_table_delete_work_time_idle.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._deferred_table_delete_rest_percentage_idle = ClientGUICommon.BetterSpinBox( self._deferred_table_delete_panel, min = 0, max = 100000 )
        tt = 'DO NOT CHANGE UNLESS YOU KNOW WHAT YOU ARE DOING. Deferred table delete operates on a work-rest cycle. This setting determines how long it should wait before starting a new work packet, in multiples of the last work time. This is for idle mode.'
        self._deferred_table_delete_rest_percentage_idle.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._deferred_table_delete_work_time_normal = ClientGUITime.TimeDeltaWidget( self._deferred_table_delete_panel, min = 0.1, seconds = True, milliseconds = True )
        tt = 'DO NOT CHANGE UNLESS YOU KNOW WHAT YOU ARE DOING. Deferred table delete operates on a work-rest cycle. This setting determines how long it should work for in each work packet. Actual work time will normally be a little larger than this. This is for when you force-start work from review services.'
        self._deferred_table_delete_work_time_normal.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._deferred_table_delete_rest_percentage_normal = ClientGUICommon.BetterSpinBox( self._deferred_table_delete_panel, min = 0, max = 100000 )
        tt = 'DO NOT CHANGE UNLESS YOU KNOW WHAT YOU ARE DOING. Deferred table delete operates on a work-rest cycle. This setting determines how long it should wait before starting a new work packet, in multiples of the last work time. This is for when you force-start work from review services.'
        self._deferred_table_delete_rest_percentage_normal.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._deferred_table_delete_work_time_work_hard = ClientGUITime.TimeDeltaWidget( self._deferred_table_delete_panel, min = 0.1, seconds = True, milliseconds = True )
        tt = 'DO NOT CHANGE UNLESS YOU KNOW WHAT YOU ARE DOING. Deferred table delete operates on a work-rest cycle. This setting determines how long it should work for in each work packet. Actual work time will normally be a little larger than this. This is for when you force it to work hard through the dialog.'
        self._deferred_table_delete_work_time_work_hard.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._deferred_table_delete_rest_percentage_work_hard = ClientGUICommon.BetterSpinBox( self._deferred_table_delete_panel, min = 0, max = 100000 )
        tt = 'DO NOT CHANGE UNLESS YOU KNOW WHAT YOU ARE DOING. Deferred table delete operates on a work-rest cycle. This setting determines how long it should wait before starting a new work packet, in multiples of the last work time. This is for when you force it to work hard through the dialog.'
        self._deferred_table_delete_rest_percentage_work_hard.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        #
        
        self._idle_normal.setChecked( HC.options[ 'idle_normal' ] )
        self._idle_period.SetValue( HC.options['idle_period'] )
        self._idle_mouse_period.SetValue( HC.options['idle_mouse_period'] )
        self._idle_mode_client_api_timeout.SetValue( self._new_options.GetNoneableInteger( 'idle_mode_client_api_timeout' ) )
        self._system_busy_cpu_percent.setValue( self._new_options.GetInteger( 'system_busy_cpu_percent' ) )
        self._system_busy_cpu_count.SetValue( self._new_options.GetNoneableInteger( 'system_busy_cpu_count' ) )
        
        self._idle_shutdown.SetValue( HC.options[ 'idle_shutdown' ] )
        self._idle_shutdown_max_minutes.setValue( HC.options['idle_shutdown_max_minutes'] )
        self._shutdown_work_period.SetValue( self._new_options.GetInteger( 'shutdown_work_period' ) )
        
        self._file_maintenance_during_idle.setChecked( self._new_options.GetBoolean( 'file_maintenance_during_idle' ) )
        
        file_maintenance_idle_throttle_files = self._new_options.GetInteger( 'file_maintenance_idle_throttle_files' )
        file_maintenance_idle_throttle_time_delta = self._new_options.GetInteger( 'file_maintenance_idle_throttle_time_delta' )
        
        file_maintenance_idle_throttle_velocity = ( file_maintenance_idle_throttle_files, file_maintenance_idle_throttle_time_delta )
        
        self._file_maintenance_idle_throttle_velocity.SetValue( file_maintenance_idle_throttle_velocity )
        
        self._file_maintenance_during_active.setChecked( self._new_options.GetBoolean( 'file_maintenance_during_active' ) )
        
        file_maintenance_active_throttle_files = self._new_options.GetInteger( 'file_maintenance_active_throttle_files' )
        file_maintenance_active_throttle_time_delta = self._new_options.GetInteger( 'file_maintenance_active_throttle_time_delta' )
        
        file_maintenance_active_throttle_velocity = ( file_maintenance_active_throttle_files, file_maintenance_active_throttle_time_delta )
        
        self._file_maintenance_active_throttle_velocity.SetValue( file_maintenance_active_throttle_velocity )
        
        self._repository_processing_work_time_very_idle.SetValue( HydrusTime.SecondiseMSFloat( self._new_options.GetInteger( 'repository_processing_work_time_ms_very_idle' ) ) )
        self._repository_processing_rest_percentage_very_idle.setValue( self._new_options.GetInteger( 'repository_processing_rest_percentage_very_idle' ) )
        
        self._repository_processing_work_time_idle.SetValue( HydrusTime.SecondiseMSFloat( self._new_options.GetInteger( 'repository_processing_work_time_ms_idle' ) ) )
        self._repository_processing_rest_percentage_idle.setValue( self._new_options.GetInteger( 'repository_processing_rest_percentage_idle' ) )
        
        self._repository_processing_work_time_normal.SetValue( HydrusTime.SecondiseMSFloat( self._new_options.GetInteger( 'repository_processing_work_time_ms_normal' ) ) )
        self._repository_processing_rest_percentage_normal.setValue( self._new_options.GetInteger( 'repository_processing_rest_percentage_normal' ) )
        
        self._tag_display_maintenance_during_idle.setChecked( self._new_options.GetBoolean( 'tag_display_maintenance_during_idle' ) )
        self._tag_display_maintenance_during_active.setChecked( self._new_options.GetBoolean( 'tag_display_maintenance_during_active' ) )
        
        self._tag_display_processing_work_time_idle.SetValue( HydrusTime.SecondiseMSFloat( self._new_options.GetInteger( 'tag_display_processing_work_time_ms_idle' ) ) )
        self._tag_display_processing_rest_percentage_idle.setValue( self._new_options.GetInteger( 'tag_display_processing_rest_percentage_idle' ) )
        
        self._tag_display_processing_work_time_normal.SetValue( HydrusTime.SecondiseMSFloat( self._new_options.GetInteger( 'tag_display_processing_work_time_ms_normal' ) ) )
        self._tag_display_processing_rest_percentage_normal.setValue( self._new_options.GetInteger( 'tag_display_processing_rest_percentage_normal' ) )
        
        self._tag_display_processing_work_time_work_hard.SetValue( HydrusTime.SecondiseMSFloat( self._new_options.GetInteger( 'tag_display_processing_work_time_ms_work_hard' ) ) )
        self._tag_display_processing_rest_percentage_work_hard.setValue( self._new_options.GetInteger( 'tag_display_processing_rest_percentage_work_hard' ) )
        
        self._maintain_similar_files_duplicate_pairs_during_idle.setChecked( self._new_options.GetBoolean( 'maintain_similar_files_duplicate_pairs_during_idle' ) )
        self._maintain_similar_files_duplicate_pairs_during_active.setChecked( self._new_options.GetBoolean( 'maintain_similar_files_duplicate_pairs_during_active' ) )
        
        self._potential_duplicates_search_work_time_idle.SetValue( HydrusTime.SecondiseMSFloat( self._new_options.GetInteger( 'potential_duplicates_search_work_time_ms_idle' ) ) )
        self._potential_duplicates_search_rest_percentage_idle.setValue( self._new_options.GetInteger( 'potential_duplicates_search_rest_percentage_idle' ) )
        self._potential_duplicates_search_work_time_active.SetValue( HydrusTime.SecondiseMSFloat( self._new_options.GetInteger( 'potential_duplicates_search_work_time_ms_active' ) ) )
        self._potential_duplicates_search_rest_percentage_active.setValue( self._new_options.GetInteger( 'potential_duplicates_search_rest_percentage_active' ) )
        
        self._duplicates_auto_resolution_during_idle.setChecked( self._new_options.GetBoolean( 'duplicates_auto_resolution_during_idle' ) )
        self._duplicates_auto_resolution_during_active.setChecked( self._new_options.GetBoolean( 'duplicates_auto_resolution_during_active' ) )
        
        self._duplicates_auto_resolution_work_time_idle.SetValue( HydrusTime.SecondiseMSFloat( self._new_options.GetInteger( 'duplicates_auto_resolution_work_time_ms_idle' ) ) )
        self._duplicates_auto_resolution_rest_percentage_idle.setValue( self._new_options.GetInteger( 'duplicates_auto_resolution_rest_percentage_idle' ) )
        self._duplicates_auto_resolution_work_time_active.SetValue( HydrusTime.SecondiseMSFloat( self._new_options.GetInteger( 'duplicates_auto_resolution_work_time_ms_active' ) ) )
        self._duplicates_auto_resolution_rest_percentage_active.setValue( self._new_options.GetInteger( 'duplicates_auto_resolution_rest_percentage_active' ) )
        
        self._deferred_table_delete_work_time_idle.SetValue( HydrusTime.SecondiseMSFloat( self._new_options.GetInteger( 'deferred_table_delete_work_time_ms_idle' ) ) )
        self._deferred_table_delete_rest_percentage_idle.setValue( self._new_options.GetInteger( 'deferred_table_delete_rest_percentage_idle' ) )
        
        self._deferred_table_delete_work_time_normal.SetValue( HydrusTime.SecondiseMSFloat( self._new_options.GetInteger( 'deferred_table_delete_work_time_ms_normal' ) ) )
        self._deferred_table_delete_rest_percentage_normal.setValue( self._new_options.GetInteger( 'deferred_table_delete_rest_percentage_normal' ) )
        
        self._deferred_table_delete_work_time_work_hard.SetValue( HydrusTime.SecondiseMSFloat( self._new_options.GetInteger( 'deferred_table_delete_work_time_ms_work_hard' ) ) )
        self._deferred_table_delete_rest_percentage_work_hard.setValue( self._new_options.GetInteger( 'deferred_table_delete_rest_percentage_work_hard' ) )
        
        #
        
        rows = []
        
        rows.append( ( 'Run maintenance jobs when the client is idle and the system is not otherwise busy: ', self._idle_normal ) )
        rows.append( ( 'Permit idle mode if no general browsing activity has occurred in the past: ', self._idle_period ) )
        rows.append( ( 'Permit idle mode if your mouse cursor has not been moved in the past: ', self._idle_mouse_period ) )
        rows.append( ( 'Permit idle mode if no Client API requests in the past: ', self._idle_mode_client_api_timeout ) )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._system_busy_cpu_percent, CC.FLAGS_CENTER )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText( self._idle_panel, label = '% on ' ), CC.FLAGS_CENTER )
        QP.AddToLayout( hbox, self._system_busy_cpu_count, CC.FLAGS_CENTER )
        
        if HydrusPSUtil.PSUTIL_OK:
            
            num_cores = HydrusPSUtil.psutil.cpu_count()
            
            label = f'(you appear to have {num_cores} cores)'
            
        else:
            
            label = 'You do not have the psutil library, so I do not believe any of these CPU checks will work!'
            
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText( self._idle_panel, label = label ), CC.FLAGS_CENTER )
        
        rows.append( ( 'Consider the system busy if CPU usage is above: ', hbox ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._idle_panel, rows )
        
        self._idle_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        rows = []
        
        rows.append( ( 'Run jobs on shutdown: ', self._idle_shutdown ) )
        rows.append( ( 'Only run shutdown jobs once per: ', self._shutdown_work_period ) )
        rows.append( ( 'Max number of minutes to run shutdown jobs: ', self._idle_shutdown_max_minutes ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._shutdown_panel, rows )
        
        self._shutdown_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        text = '***'
        text += '\n'
        text +='If you are a new user or do not completely understand these options, please do not touch them! Do not set the client to be idle all the time unless you know what you are doing or are testing something and are prepared for potential problems!'
        text += '\n'
        text += '***'
        text += '\n' * 2
        text += 'Sometimes, the client needs to do some heavy maintenance. This could be reformatting the database to keep it running fast or processing a large number of tags from a repository. Typically, these jobs will not allow you to use the gui while they run, and on slower computers--or those with not much memory--they can take a long time to complete.'
        text += '\n' * 2
        text += 'You can set these jobs to run only when the client is idle, or only during shutdown, or neither, or both. If you leave the client on all the time in the background, focusing on \'idle time\' processing is often ideal. If you have a slow computer, relying on \'shutdown\' processing (which you can manually start when convenient), is often better.'
        text += '\n' * 2
        text += 'If the client switches from idle to not idle during a job, it will try to abandon it and give you back control. This is not always possible, and even when it is, it will sometimes take several minutes, particularly on slower machines or those on HDDs rather than SSDs.'
        text += '\n' * 2
        text += 'If the client believes the system is busy, it will generally not start jobs.'
        
        st = ClientGUICommon.BetterStaticText( self._jobs_panel, label = text )
        st.setWordWrap( True )
        
        self._jobs_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._jobs_panel.Add( self._idle_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._jobs_panel.Add( self._shutdown_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        message = 'Scheduled jobs such as reparsing file metadata and regenerating thumbnails are performed in the background.'
        
        self._file_maintenance_panel.Add( ClientGUICommon.BetterStaticText( self._file_maintenance_panel, label = message ), CC.FLAGS_EXPAND_PERPENDICULAR )
        
        rows = []
        
        rows.append( ( 'Run file maintenance during idle time: ', self._file_maintenance_during_idle ) )
        rows.append( ( 'Idle throttle: ', self._file_maintenance_idle_throttle_velocity ) )
        rows.append( ( 'Run file maintenance during normal time: ', self._file_maintenance_during_active ) )
        rows.append( ( 'Normal throttle: ', self._file_maintenance_active_throttle_velocity ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._file_maintenance_panel, rows )
        
        self._file_maintenance_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        message = 'Repository processing takes a lot of CPU and works best when it can rip for long periods in idle time.'
        
        self._repository_processing_panel.Add( ClientGUICommon.BetterStaticText( self._repository_processing_panel, label = message ), CC.FLAGS_EXPAND_PERPENDICULAR )
        
        rows = []
        
        rows.append( ( '"Very idle" ideal work packet time: ', self._repository_processing_work_time_very_idle ) )
        rows.append( ( '"Very idle" rest time percentage: ', self._repository_processing_rest_percentage_very_idle ) )
        rows.append( ( '"Idle" ideal work packet time: ', self._repository_processing_work_time_idle ) )
        rows.append( ( '"Idle" rest time percentage: ', self._repository_processing_rest_percentage_idle ) )
        rows.append( ( '"Normal" ideal work packet time: ', self._repository_processing_work_time_normal ) )
        rows.append( ( '"Normal" rest time percentage: ', self._repository_processing_rest_percentage_normal ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._repository_processing_panel, rows )
        
        self._repository_processing_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        message = 'The database compiles sibling and parent implication calculations in the background. This can use a LOT of CPU in big bumps.'
        
        self._tag_display_processing_panel.Add( ClientGUICommon.BetterStaticText( self._tag_display_processing_panel, label = message ), CC.FLAGS_EXPAND_PERPENDICULAR )
        
        rows = []
        
        rows.append( ( 'Do work in "idle" time: ', self._tag_display_maintenance_during_idle ) )
        rows.append( ( '"Idle" ideal work packet time: ', self._tag_display_processing_work_time_idle ) )
        rows.append( ( '"Idle" rest time percentage: ', self._tag_display_processing_rest_percentage_idle ) )
        rows.append( ( 'Do work in "normal" time: ', self._tag_display_maintenance_during_active ) )
        rows.append( ( '"Normal" ideal work packet time: ', self._tag_display_processing_work_time_normal ) )
        rows.append( ( '"Normal" rest time percentage: ', self._tag_display_processing_rest_percentage_normal ) )
        rows.append( ( '"Work hard" ideal work packet time: ', self._tag_display_processing_work_time_work_hard ) )
        rows.append( ( '"Work hard" rest time percentage: ', self._tag_display_processing_rest_percentage_work_hard ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._tag_display_processing_panel, rows )
        
        self._tag_display_processing_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        message = 'The discovery of new potential duplicate file pairs (as on the duplicates page, preparation tab) can run automatically.'
        
        self._potential_duplicates_panel.Add( ClientGUICommon.BetterStaticText( self._potential_duplicates_panel, label = message ), CC.FLAGS_EXPAND_PERPENDICULAR )
        
        rows = []
        
        rows.append( ( 'Search for potential duplicates in "idle" time: ', self._maintain_similar_files_duplicate_pairs_during_idle ) )
        rows.append( ( '"Idle" ideal work packet time: ', self._potential_duplicates_search_work_time_idle ) )
        rows.append( ( '"Idle" rest time percentage: ', self._potential_duplicates_search_rest_percentage_idle ) )
        rows.append( ( 'Search for potential duplicates in "normal" time: ', self._maintain_similar_files_duplicate_pairs_during_active ) )
        rows.append( ( '"Normal" ideal work packet time: ', self._potential_duplicates_search_work_time_active ) )
        rows.append( ( '"Normal" rest time percentage: ', self._potential_duplicates_search_rest_percentage_active ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._potential_duplicates_panel, rows )
        
        self._potential_duplicates_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        message = 'The search, testing, and resolution work of duplicates auto-resolution rules (as on the duplicates page, auto-resolution tab) runs automatically in the background.'
        
        self._duplicates_auto_resolution_panel.Add( ClientGUICommon.BetterStaticText( self._duplicates_auto_resolution_panel, label = message ), CC.FLAGS_EXPAND_PERPENDICULAR )
        
        rows = []
        
        rows.append( ( 'Work duplicates auto-resolution in "idle" time: ', self._duplicates_auto_resolution_during_idle ) )
        rows.append( ( '"Idle" ideal work packet time: ', self._duplicates_auto_resolution_work_time_idle ) )
        rows.append( ( '"Idle" rest time percentage: ', self._duplicates_auto_resolution_rest_percentage_idle ) )
        rows.append( ( 'Work duplicates auto-resolution in "normal" time: ', self._duplicates_auto_resolution_during_active ) )
        rows.append( ( '"Normal" ideal work packet time: ', self._duplicates_auto_resolution_work_time_active ) )
        rows.append( ( '"Normal" rest time percentage: ', self._duplicates_auto_resolution_rest_percentage_active ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._duplicates_auto_resolution_panel, rows )
        
        self._duplicates_auto_resolution_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        message = 'The database deletes old data in the background.'
        
        self._deferred_table_delete_panel.Add( ClientGUICommon.BetterStaticText( self._deferred_table_delete_panel, label = message ), CC.FLAGS_EXPAND_PERPENDICULAR )
        
        rows = []
        
        rows.append( ( '"Idle" ideal work packet time: ', self._deferred_table_delete_work_time_idle ) )
        rows.append( ( '"Idle" rest time percentage: ', self._deferred_table_delete_rest_percentage_idle ) )
        rows.append( ( '"Normal" ideal work packet time: ', self._deferred_table_delete_work_time_normal ) )
        rows.append( ( '"Normal" rest time percentage: ', self._deferred_table_delete_rest_percentage_normal ) )
        rows.append( ( '"Work hard" ideal work packet time: ', self._deferred_table_delete_work_time_work_hard ) )
        rows.append( ( '"Work hard" rest time percentage: ', self._deferred_table_delete_rest_percentage_work_hard ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._deferred_table_delete_panel, rows )
        
        self._deferred_table_delete_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._jobs_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._file_maintenance_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._repository_processing_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._tag_display_processing_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._potential_duplicates_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._duplicates_auto_resolution_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._deferred_table_delete_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.addStretch( 0 )
        
        self.setLayout( vbox )
        
        self._EnableDisableIdleNormal()
        self._EnableDisableIdleShutdown()
        
        self._system_busy_cpu_count.valueChanged.connect( self._EnableDisableCPUPercent )
        
    
    def _EnableDisableCPUPercent( self ):
        
        enabled = self._system_busy_cpu_count.isEnabled() and self._system_busy_cpu_count.GetValue() is not None
        
        self._system_busy_cpu_percent.setEnabled( enabled )
        
    
    def _EnableDisableIdleNormal( self ):
        
        enabled = self._idle_normal.isChecked()
        
        self._idle_period.setEnabled( enabled )
        self._idle_mouse_period.setEnabled( enabled )
        self._idle_mode_client_api_timeout.setEnabled( enabled )
        self._system_busy_cpu_count.setEnabled( enabled )
        
        self._EnableDisableCPUPercent()
        
    
    def _EnableDisableIdleShutdown( self ):
        
        enabled = self._idle_shutdown.GetValue() != CC.IDLE_NOT_ON_SHUTDOWN
        
        self._shutdown_work_period.setEnabled( enabled )
        self._idle_shutdown_max_minutes.setEnabled( enabled )
        
    
    def UpdateOptions( self ):
        
        HC.options[ 'idle_normal' ] = self._idle_normal.isChecked()
        
        HC.options[ 'idle_period' ] = self._idle_period.GetValue()
        HC.options[ 'idle_mouse_period' ] = self._idle_mouse_period.GetValue()
        self._new_options.SetNoneableInteger( 'idle_mode_client_api_timeout', self._idle_mode_client_api_timeout.GetValue() )
        
        self._new_options.SetInteger( 'system_busy_cpu_percent', self._system_busy_cpu_percent.value() )
        self._new_options.SetNoneableInteger( 'system_busy_cpu_count', self._system_busy_cpu_count.GetValue() )
        
        HC.options[ 'idle_shutdown' ] = self._idle_shutdown.GetValue()
        HC.options[ 'idle_shutdown_max_minutes' ] = self._idle_shutdown_max_minutes.value()
        
        self._new_options.SetInteger( 'shutdown_work_period', self._shutdown_work_period.GetValue() )
        
        self._new_options.SetBoolean( 'file_maintenance_during_idle', self._file_maintenance_during_idle.isChecked() )
        
        file_maintenance_idle_throttle_velocity = self._file_maintenance_idle_throttle_velocity.GetValue()
        
        ( file_maintenance_idle_throttle_files, file_maintenance_idle_throttle_time_delta ) = file_maintenance_idle_throttle_velocity
        
        self._new_options.SetInteger( 'file_maintenance_idle_throttle_files', file_maintenance_idle_throttle_files )
        self._new_options.SetInteger( 'file_maintenance_idle_throttle_time_delta', file_maintenance_idle_throttle_time_delta )
        
        self._new_options.SetBoolean( 'file_maintenance_during_active', self._file_maintenance_during_active.isChecked() )
        
        file_maintenance_active_throttle_velocity = self._file_maintenance_active_throttle_velocity.GetValue()
        
        ( file_maintenance_active_throttle_files, file_maintenance_active_throttle_time_delta ) = file_maintenance_active_throttle_velocity
        
        self._new_options.SetInteger( 'file_maintenance_active_throttle_files', file_maintenance_active_throttle_files )
        self._new_options.SetInteger( 'file_maintenance_active_throttle_time_delta', file_maintenance_active_throttle_time_delta )
        
        self._new_options.SetInteger( 'repository_processing_work_time_ms_very_idle', HydrusTime.MillisecondiseS( self._repository_processing_work_time_very_idle.GetValue() ) )
        self._new_options.SetInteger( 'repository_processing_rest_percentage_very_idle', self._repository_processing_rest_percentage_very_idle.value() )
        
        self._new_options.SetInteger( 'repository_processing_work_time_ms_idle', HydrusTime.MillisecondiseS( self._repository_processing_work_time_idle.GetValue() ) )
        self._new_options.SetInteger( 'repository_processing_rest_percentage_idle', self._repository_processing_rest_percentage_idle.value() )
        
        self._new_options.SetInteger( 'repository_processing_work_time_ms_normal', HydrusTime.MillisecondiseS( self._repository_processing_work_time_normal.GetValue() ) )
        self._new_options.SetInteger( 'repository_processing_rest_percentage_normal', self._repository_processing_rest_percentage_normal.value() )
        
        self._new_options.SetBoolean( 'tag_display_maintenance_during_idle', self._tag_display_maintenance_during_idle.isChecked() )
        self._new_options.SetBoolean( 'tag_display_maintenance_during_active', self._tag_display_maintenance_during_active.isChecked() )
        
        self._new_options.SetInteger( 'tag_display_processing_work_time_ms_idle', HydrusTime.MillisecondiseS( self._tag_display_processing_work_time_idle.GetValue() ) )
        self._new_options.SetInteger( 'tag_display_processing_rest_percentage_idle', self._tag_display_processing_rest_percentage_idle.value() )
        
        self._new_options.SetInteger( 'tag_display_processing_work_time_ms_normal', HydrusTime.MillisecondiseS( self._tag_display_processing_work_time_normal.GetValue() ) )
        self._new_options.SetInteger( 'tag_display_processing_rest_percentage_normal', self._tag_display_processing_rest_percentage_normal.value() )
        
        self._new_options.SetInteger( 'tag_display_processing_work_time_ms_work_hard', HydrusTime.MillisecondiseS( self._tag_display_processing_work_time_work_hard.GetValue() ) )
        self._new_options.SetInteger( 'tag_display_processing_rest_percentage_work_hard', self._tag_display_processing_rest_percentage_work_hard.value() )
        
        self._new_options.SetBoolean( 'maintain_similar_files_duplicate_pairs_during_idle', self._maintain_similar_files_duplicate_pairs_during_idle.isChecked() )
        self._new_options.SetInteger( 'potential_duplicates_search_work_time_ms_idle', HydrusTime.MillisecondiseS( self._potential_duplicates_search_work_time_idle.GetValue() ) )
        self._new_options.SetInteger( 'potential_duplicates_search_rest_percentage_idle', self._potential_duplicates_search_rest_percentage_idle.value() )
        self._new_options.SetBoolean( 'maintain_similar_files_duplicate_pairs_during_active', self._maintain_similar_files_duplicate_pairs_during_active.isChecked() )
        self._new_options.SetInteger( 'potential_duplicates_search_work_time_ms_active', HydrusTime.MillisecondiseS( self._potential_duplicates_search_work_time_active.GetValue() ) )
        self._new_options.SetInteger( 'potential_duplicates_search_rest_percentage_active', self._potential_duplicates_search_rest_percentage_active.value() )
        
        self._new_options.SetBoolean( 'duplicates_auto_resolution_during_idle', self._duplicates_auto_resolution_during_idle.isChecked() )
        self._new_options.SetInteger( 'duplicates_auto_resolution_work_time_ms_idle', HydrusTime.MillisecondiseS( self._duplicates_auto_resolution_work_time_idle.GetValue() ) )
        self._new_options.SetInteger( 'duplicates_auto_resolution_rest_percentage_idle', self._duplicates_auto_resolution_rest_percentage_idle.value() )
        self._new_options.SetBoolean( 'duplicates_auto_resolution_during_active', self._duplicates_auto_resolution_during_active.isChecked() )
        self._new_options.SetInteger( 'duplicates_auto_resolution_work_time_ms_active', HydrusTime.MillisecondiseS( self._duplicates_auto_resolution_work_time_active.GetValue() ) )
        self._new_options.SetInteger( 'duplicates_auto_resolution_rest_percentage_active', self._duplicates_auto_resolution_rest_percentage_active.value() )
        
        self._new_options.SetInteger( 'deferred_table_delete_work_time_ms_idle', HydrusTime.MillisecondiseS( self._deferred_table_delete_work_time_idle.GetValue() ) )
        self._new_options.SetInteger( 'deferred_table_delete_rest_percentage_idle', self._deferred_table_delete_rest_percentage_idle.value() )
        
        self._new_options.SetInteger( 'deferred_table_delete_work_time_ms_normal', HydrusTime.MillisecondiseS( self._deferred_table_delete_work_time_normal.GetValue() ) )
        self._new_options.SetInteger( 'deferred_table_delete_rest_percentage_normal', self._deferred_table_delete_rest_percentage_normal.value() )
        
        self._new_options.SetInteger( 'deferred_table_delete_work_time_ms_work_hard', HydrusTime.MillisecondiseS( self._deferred_table_delete_work_time_work_hard.GetValue() ) )
        self._new_options.SetInteger( 'deferred_table_delete_rest_percentage_work_hard', self._deferred_table_delete_rest_percentage_work_hard.value() )
        
    
