from qtpy import QtWidgets as QW

from hydrus.core import HydrusData

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.panels.options import ClientGUIOptionsPanelBase
from hydrus.client.gui.widgets import ClientGUICommon

class MediaViewerPanel( ClientGUIOptionsPanelBase.OptionsPagePanel ):
    
    def __init__( self, parent ):
        
        super().__init__( parent )
        
        self._new_options = CG.client_controller.new_options
        
        #
        
        focus_panel = ClientGUICommon.StaticBox( self, 'closing focus' )
        
        self._focus_media_tab_on_viewer_close_if_possible = QW.QCheckBox( focus_panel )
        self._focus_media_tab_on_viewer_close_if_possible.setToolTip( ClientGUIFunctions.WrapToolTip( 'If the search page you opened a media viewer from is still open, navigate back to it upon media viewer close. Useful if you use multiple media viewers launched from different pages. There is also a shortcut action to perform this on an individual basis.' ) )
        
        self._focus_media_thumb_on_viewer_close = QW.QCheckBox( focus_panel )
        self._focus_media_thumb_on_viewer_close.setToolTip( ClientGUIFunctions.WrapToolTip( 'When you close a Media Viewer, it normally tells the original search page to change the current thumbnail selection to whatever you closed the media viewer on. If you prefer this not to happen, uncheck this!' ) )
        
        self._activate_main_gui_on_focusing_viewer_close = QW.QCheckBox( focus_panel )
        self._activate_main_gui_on_focusing_viewer_close.setToolTip( ClientGUIFunctions.WrapToolTip( 'This will "activate" the Main GUI Window when any Media Viewer closes with with a "focusing" action, either because you set the options above, or, more importantly, if they are set off above but you do it using a shortcut. This will bring the Main GUI to the front and give it keyboard focus. Try this if you regularly use multiple viewers and need fine control over the focus stack.' ) )
        
        self._activate_main_gui_on_viewer_close = QW.QCheckBox( focus_panel )
        self._activate_main_gui_on_viewer_close.setToolTip( ClientGUIFunctions.WrapToolTip( 'This will "activate" the Main GUI Window when any Media Viewer closes, which should bring it to the front and give it keyboard focus. Try this if your OS is playing funny games with focus when a media viewer closes.' ) )
        
        #
        
        mouse_panel = ClientGUICommon.StaticBox( self, 'mouse behaviour' )
        
        self._media_viewer_cursor_autohide_time_ms = ClientGUICommon.NoneableSpinCtrl( mouse_panel, 700, none_phrase = 'do not autohide', min = 100, max = 100000, unit = 'ms' )
        
        self._disallow_media_drags_on_duration_media = QW.QCheckBox( mouse_panel )
        
        self._anchor_and_hide_canvas_drags = QW.QCheckBox( mouse_panel )
        self._touchscreen_canvas_drags_unanchor = QW.QCheckBox( mouse_panel )
        
        #
        
        seek_bar_panel = ClientGUICommon.StaticBox( self, 'animation/audio seek bar' )
        
        self._animated_scanbar_height = ClientGUICommon.BetterSpinBox( seek_bar_panel, min=1, max=255 )
        self._animated_scanbar_hide_height = ClientGUICommon.NoneableSpinCtrl( seek_bar_panel, 5, none_phrase = 'no, hide it completely', min = 1, max = 255, unit = 'px' )
        self._animated_scanbar_pop_in_requires_focus = QW.QCheckBox( seek_bar_panel )
        self._animated_scanbar_nub_width = ClientGUICommon.BetterSpinBox( seek_bar_panel, min=1, max=63 )
        
        #
        
        slideshow_panel = ClientGUICommon.StaticBox( self, 'slideshows' )
        
        self._slideshow_durations = QW.QLineEdit( slideshow_panel )
        self._slideshow_durations.setToolTip( ClientGUIFunctions.WrapToolTip( 'This is a bit hacky, but whatever you have here, in comma-separated floats, will end up in the slideshow menu in the media viewer.' ) )
        self._slideshow_durations.textChanged.connect( self.EventSlideshowChanged )
        
        self._slideshow_always_play_duration_media_once_through = QW.QCheckBox( slideshow_panel )
        self._slideshow_always_play_duration_media_once_through.setToolTip( ClientGUIFunctions.WrapToolTip( 'If this is on, then a slideshow will not move on until the current duration-having media has played once through.' ) )
        self._slideshow_always_play_duration_media_once_through.clicked.connect( self.EventSlideshowChanged )
        
        self._slideshow_short_duration_loop_seconds = ClientGUICommon.NoneableSpinCtrl( slideshow_panel, 10, none_phrase = 'do not use', min = 1, max = 86400, unit = 's' )
        tt = '(Ensures very short loops play for a bit, but not five minutes) A slideshow will move on early if the current duration-having media has a duration less than this many seconds (and this is less than the overall slideshow period).'
        self._slideshow_short_duration_loop_seconds.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._slideshow_short_duration_loop_percentage = ClientGUICommon.NoneableSpinCtrl( slideshow_panel, 20, none_phrase = 'do not use', min = 1, max = 99, unit = '%' )
        tt = '(Ensures short videos play for a bit, but not twenty minutes) A slideshow will move on early if the current duration-having media has a duration less than this percentage of the overall slideshow period.'
        self._slideshow_short_duration_loop_percentage.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._slideshow_short_duration_cutoff_percentage = ClientGUICommon.NoneableSpinCtrl( slideshow_panel, 75, none_phrase = 'do not use', min = 1, max = 99, unit = '%' )
        tt = '(Ensures that slightly shorter videos move the slideshow cleanly along as soon as they are done) A slideshow will move on early if the current duration-having media will have played exactly once through between this many percent and 100% of the slideshow period.'
        self._slideshow_short_duration_cutoff_percentage.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._slideshow_long_duration_overspill_percentage = ClientGUICommon.NoneableSpinCtrl( slideshow_panel, 50, none_phrase = 'do not use', min = 1, max = 500, unit = '%' )
        tt = '(Ensures slightly longer videos will not get cut off right at the end) A slideshow will delay moving on if playing the current duration-having media would stretch the overall slideshow period less than this amount.'
        self._slideshow_long_duration_overspill_percentage.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        #
        
        self._focus_media_tab_on_viewer_close_if_possible.setChecked( self._new_options.GetBoolean( 'focus_media_tab_on_viewer_close_if_possible' ) )
        self._focus_media_thumb_on_viewer_close.setChecked( self._new_options.GetBoolean( 'focus_media_thumb_on_viewer_close' ) )
        self._activate_main_gui_on_focusing_viewer_close.setChecked( self._new_options.GetBoolean( 'activate_main_gui_on_focusing_viewer_close' ) )
        self._activate_main_gui_on_viewer_close.setChecked( self._new_options.GetBoolean( 'activate_main_gui_on_viewer_close' ) )
        
        self._animated_scanbar_height.setValue( self._new_options.GetInteger( 'animated_scanbar_height' ) )
        self._animated_scanbar_nub_width.setValue( self._new_options.GetInteger( 'animated_scanbar_nub_width' ) )
        
        self._animated_scanbar_hide_height.SetValue( 5 )
        self._animated_scanbar_hide_height.SetValue( self._new_options.GetNoneableInteger( 'animated_scanbar_hide_height' ) )
        
        self._animated_scanbar_pop_in_requires_focus.setChecked( self._new_options.GetBoolean( 'animated_scanbar_pop_in_requires_focus' ) )
        
        self._media_viewer_cursor_autohide_time_ms.SetValue( self._new_options.GetNoneableInteger( 'media_viewer_cursor_autohide_time_ms' ) )
        self._disallow_media_drags_on_duration_media.setChecked( self._new_options.GetBoolean( 'disallow_media_drags_on_duration_media' ) )
        self._anchor_and_hide_canvas_drags.setChecked( self._new_options.GetBoolean( 'anchor_and_hide_canvas_drags' ) )
        self._touchscreen_canvas_drags_unanchor.setChecked( self._new_options.GetBoolean( 'touchscreen_canvas_drags_unanchor' ) )
        
        slideshow_durations = self._new_options.GetSlideshowDurations()
        
        self._slideshow_durations.setText( ','.join( ( str( slideshow_duration ) for slideshow_duration in slideshow_durations ) ) )
        
        self._slideshow_always_play_duration_media_once_through.setChecked( self._new_options.GetBoolean( 'slideshow_always_play_duration_media_once_through' ) )
        self._slideshow_short_duration_loop_seconds.SetValue( self._new_options.GetNoneableInteger( 'slideshow_short_duration_loop_seconds' ) )
        self._slideshow_short_duration_loop_percentage.SetValue( self._new_options.GetNoneableInteger( 'slideshow_short_duration_loop_percentage' ) )
        self._slideshow_short_duration_cutoff_percentage.SetValue( self._new_options.GetNoneableInteger( 'slideshow_short_duration_cutoff_percentage' ) )
        self._slideshow_long_duration_overspill_percentage.SetValue( self._new_options.GetNoneableInteger( 'slideshow_long_duration_overspill_percentage' ) )
        
        #
        
        rows = []
        
        rows.append( ( 'When closing the media viewer, re-select original search page: ', self._focus_media_tab_on_viewer_close_if_possible ) )
        rows.append( ( 'When closing the media viewer, tell original search page to select exit media: ', self._focus_media_thumb_on_viewer_close ) )
        rows.append( ( 'ADVANCED: When closing the media viewer with the above focusing options, activate Main GUI: ', self._activate_main_gui_on_focusing_viewer_close ) )
        rows.append( ( 'DEBUG: When closing the media viewer at any time, activate Main GUI: ', self._activate_main_gui_on_viewer_close ) )
        
        gridbox = ClientGUICommon.WrapInGrid( focus_panel, rows )
        
        focus_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        rows = []
        
        rows.append( ( 'Time until mouse cursor autohides on media viewer:', self._media_viewer_cursor_autohide_time_ms ) )
        rows.append( ( 'Do not allow mouse media drag-panning when the media has duration:', self._disallow_media_drags_on_duration_media ) )
        rows.append( ( 'RECOMMEND WINDOWS ONLY: Hide and anchor mouse cursor on media viewer drags:', self._anchor_and_hide_canvas_drags ) )
        rows.append( ( 'RECOMMEND WINDOWS ONLY: If set to hide and anchor, undo on apparent touchscreen drag:', self._touchscreen_canvas_drags_unanchor ) )
        
        mouse_gridbox = ClientGUICommon.WrapInGrid( mouse_panel, rows )
        
        mouse_panel.Add( mouse_gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        rows = []
        
        rows.append( ( 'Seek bar height:', self._animated_scanbar_height ) )
        rows.append( ( 'Seek bar height when mouse away:', self._animated_scanbar_hide_height ) )
        rows.append( ( 'Seek bar full-height pop-in requires window focus:', self._animated_scanbar_pop_in_requires_focus ) )
        rows.append( ( 'Seek bar nub width:', self._animated_scanbar_nub_width ) )
        
        seek_bar_gridbox = ClientGUICommon.WrapInGrid( seek_bar_panel, rows )
        
        seek_bar_panel.Add( seek_bar_gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        rows = []
        
        rows.append( ( 'Slideshow durations:', self._slideshow_durations ) )
        rows.append( ( 'Always play media once through before moving on:', self._slideshow_always_play_duration_media_once_through ) )
        rows.append( ( 'Slideshow short-media skip seconds threshold:', self._slideshow_short_duration_loop_seconds ) )
        rows.append( ( 'Slideshow short-media skip percentage threshold:', self._slideshow_short_duration_loop_percentage ) )
        rows.append( ( 'Slideshow shorter-media cutoff percentage threshold:', self._slideshow_short_duration_cutoff_percentage ) )
        rows.append( ( 'Slideshow long-media allowed delay percentage threshold:', self._slideshow_long_duration_overspill_percentage ) )
        
        slideshow_gridbox = ClientGUICommon.WrapInGrid( slideshow_panel, rows )
        
        slideshow_panel.Add( slideshow_gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, mouse_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, seek_bar_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, slideshow_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, focus_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.addStretch( 0 )
        
        self.setLayout( vbox )
        
    
    def EventSlideshowChanged( self, text ):
        
        try:
            
            slideshow_durations = [ float( slideshow_duration ) for slideshow_duration in self._slideshow_durations.text().split( ',' ) ]
            
            self._slideshow_durations.setObjectName( '' )
            
        except ValueError:
            
            self._slideshow_durations.setObjectName( 'HydrusInvalid' )
            
        
        self._slideshow_durations.style().polish( self._slideshow_durations )
        
        self._slideshow_durations.update()
        
        always_once_through = self._slideshow_always_play_duration_media_once_through.isChecked()
        
        self._slideshow_long_duration_overspill_percentage.setEnabled( not always_once_through )
        
    
    def UpdateOptions( self ):
        
        self._new_options.SetBoolean( 'focus_media_tab_on_viewer_close_if_possible', self._focus_media_tab_on_viewer_close_if_possible.isChecked() )
        self._new_options.SetBoolean( 'focus_media_thumb_on_viewer_close', self._focus_media_thumb_on_viewer_close.isChecked() )
        self._new_options.SetBoolean( 'activate_main_gui_on_focusing_viewer_close', self._activate_main_gui_on_focusing_viewer_close.isChecked() )
        self._new_options.SetBoolean( 'activate_main_gui_on_viewer_close', self._activate_main_gui_on_viewer_close.isChecked() )
        
        self._new_options.SetBoolean( 'disallow_media_drags_on_duration_media', self._disallow_media_drags_on_duration_media.isChecked() )
        self._new_options.SetBoolean( 'anchor_and_hide_canvas_drags', self._anchor_and_hide_canvas_drags.isChecked() )
        self._new_options.SetBoolean( 'touchscreen_canvas_drags_unanchor', self._touchscreen_canvas_drags_unanchor.isChecked() )
        
        self._new_options.SetNoneableInteger( 'media_viewer_cursor_autohide_time_ms', self._media_viewer_cursor_autohide_time_ms.GetValue() )
        
        self._new_options.SetInteger( 'animated_scanbar_height', self._animated_scanbar_height.value() )
        self._new_options.SetInteger( 'animated_scanbar_nub_width', self._animated_scanbar_nub_width.value() )
        
        self._new_options.SetNoneableInteger( 'animated_scanbar_hide_height', self._animated_scanbar_hide_height.GetValue() )
        
        self._new_options.SetBoolean( 'animated_scanbar_pop_in_requires_focus', self._animated_scanbar_pop_in_requires_focus.isChecked() )
        
        try:
            
            slideshow_durations = [ float( slideshow_duration ) for slideshow_duration in self._slideshow_durations.text().split( ',' ) ]
            
            slideshow_durations = [ slideshow_duration for slideshow_duration in slideshow_durations if slideshow_duration > 0.0 ]
            
            if len( slideshow_durations ) > 0:
                
                self._new_options.SetSlideshowDurations( slideshow_durations )
                
            
        except ValueError:
            
            HydrusData.ShowText( 'Could not parse those slideshow durations, so they were not saved!' )
            
        
        self._new_options.SetBoolean( 'slideshow_always_play_duration_media_once_through', self._slideshow_always_play_duration_media_once_through.isChecked() )
        self._new_options.SetNoneableInteger( 'slideshow_short_duration_loop_percentage', self._slideshow_short_duration_loop_percentage.GetValue() )
        self._new_options.SetNoneableInteger( 'slideshow_short_duration_loop_seconds', self._slideshow_short_duration_loop_seconds.GetValue() )
        self._new_options.SetNoneableInteger( 'slideshow_short_duration_cutoff_percentage', self._slideshow_short_duration_cutoff_percentage.GetValue() )
        self._new_options.SetNoneableInteger( 'slideshow_long_duration_overspill_percentage', self._slideshow_long_duration_overspill_percentage.GetValue() )
        
    
