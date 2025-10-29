from qtpy import QtWidgets as QW

from hydrus.client import ClientConstants as CC
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.panels.options import ClientGUIOptionsPanelBase
from hydrus.client.gui.widgets import ClientGUICommon

class DuplicatesPanel( ClientGUIOptionsPanelBase.OptionsPagePanel ):
    
    def __init__( self, parent, new_options ):
        
        super().__init__( parent )
        
        self._new_options = new_options
        
        #
        
        open_panel = ClientGUICommon.StaticBox( self, 'open in a new duplicates filter page' )
        
        self._open_files_to_duplicate_filter_uses_all_my_files = QW.QCheckBox( open_panel )
        self._open_files_to_duplicate_filter_uses_all_my_files.setToolTip( ClientGUIFunctions.WrapToolTip( 'Normally, when you open a selection of files into a new page, the current file domain is preserved. For duplicates filters, you usually want to search in "all my files", so this sticks that. If you need domain-specific duplicates pages and know what you are doing, you can turn this off.' ) )
        
        duplicates_filter_page_panel = ClientGUICommon.StaticBox( self, 'duplicates filter page' )
        
        self._hide_duplicates_needs_work_message_when_reasonably_caught_up = QW.QCheckBox( duplicates_filter_page_panel )
        self._hide_duplicates_needs_work_message_when_reasonably_caught_up.setToolTip( ClientGUIFunctions.WrapToolTip( 'By default, the duplicates filter page will not highlight that there is potential duplicates search work to do if you are 99% done. This saves you being notified by the normal background burble of regular file imports. If you want to know whenever any work is pending, uncheck this.' ) )
        
        weights_panel = ClientGUICommon.StaticBox( self, 'duplicate filter comparison score weights' )
        
        self._duplicate_comparison_score_higher_jpeg_quality = ClientGUICommon.BetterSpinBox( weights_panel, min=-100, max=100 )
        self._duplicate_comparison_score_much_higher_jpeg_quality = ClientGUICommon.BetterSpinBox( weights_panel, min=-100, max=100 )
        self._duplicate_comparison_score_higher_filesize = ClientGUICommon.BetterSpinBox( weights_panel, min=-100, max=100 )
        self._duplicate_comparison_score_much_higher_filesize = ClientGUICommon.BetterSpinBox( weights_panel, min=-100, max=100 )
        self._duplicate_comparison_score_higher_resolution = ClientGUICommon.BetterSpinBox( weights_panel, min=-100, max=100 )
        self._duplicate_comparison_score_much_higher_resolution = ClientGUICommon.BetterSpinBox( weights_panel, min=-100, max=100 )
        self._duplicate_comparison_score_more_tags = ClientGUICommon.BetterSpinBox( weights_panel, min=-100, max=100 )
        self._duplicate_comparison_score_older = ClientGUICommon.BetterSpinBox( weights_panel, min=-100, max=100 )
        self._duplicate_comparison_score_nicer_ratio = ClientGUICommon.BetterSpinBox( weights_panel, min=-100, max=100 )
        self._duplicate_comparison_score_has_audio = ClientGUICommon.BetterSpinBox( weights_panel, min=-100, max=100 )
        
        self._duplicate_comparison_score_nicer_ratio.setToolTip( ClientGUIFunctions.WrapToolTip( 'For instance, 16:9 vs 640:357.') )
        
        batches_panel = ClientGUICommon.StaticBox( self, 'duplicate filter batches' )
        
        self._duplicate_filter_max_batch_size = ClientGUICommon.BetterSpinBox( batches_panel, min = 5, max = 1024 )
        self._duplicate_filter_max_batch_size.setToolTip( ClientGUIFunctions.WrapToolTip( 'In group mode you always see the whole group, which in some cases can be 1,000+ items.' ) )
        
        self._duplicate_filter_auto_commit_batch_size = ClientGUICommon.NoneableSpinCtrl( batches_panel, 1, min = 1, max = 50, none_phrase = 'no, always confirm' )
        self._duplicate_filter_auto_commit_batch_size.setToolTip( ClientGUIFunctions.WrapToolTip( 'When you are dealing with numerous 1/1 size batches/groups, it can get annoying to click through the confirm every time. This will auto-confirm any batch with this many decisions of fewer, assuming no manual skips.' ) )
        
        colours_panel = ClientGUICommon.StaticBox( self, 'colours' )
        
        self._duplicate_background_switch_intensity_a = ClientGUICommon.NoneableSpinCtrl( colours_panel, 3, none_phrase = 'do not change', min = 1, max = 9 )
        self._duplicate_background_switch_intensity_a.setToolTip( ClientGUIFunctions.WrapToolTip( 'This changes the background colour when you are looking at A. If you have a pure white/black background and do not have transparent images to show with checkerboard, it helps to highlight transparency vs opaque white/black image background.' ) )
        
        self._duplicate_background_switch_intensity_b = ClientGUICommon.NoneableSpinCtrl( colours_panel, 3, none_phrase = 'do not change', min = 1, max = 9 )
        self._duplicate_background_switch_intensity_b.setToolTip( ClientGUIFunctions.WrapToolTip( 'This changes the background colour when you are looking at B. Making it different to the A value helps to highlight switches between the two.' ) )
        
        self._draw_transparency_checkerboard_media_canvas_duplicates = QW.QCheckBox( colours_panel )
        self._draw_transparency_checkerboard_media_canvas_duplicates.setToolTip( ClientGUIFunctions.WrapToolTip( 'Same as the setting in _media playback_, but only for the duplicate filter. Only applies if that _media_ setting is unchecked.' ) )
        
        #
        
        self._open_files_to_duplicate_filter_uses_all_my_files.setChecked( self._new_options.GetBoolean( 'open_files_to_duplicate_filter_uses_all_my_files' ) )
        
        self._hide_duplicates_needs_work_message_when_reasonably_caught_up.setChecked( self._new_options.GetBoolean( 'hide_duplicates_needs_work_message_when_reasonably_caught_up' ) )
        
        self._duplicate_comparison_score_higher_jpeg_quality.setValue( self._new_options.GetInteger( 'duplicate_comparison_score_higher_jpeg_quality' ) )
        self._duplicate_comparison_score_much_higher_jpeg_quality.setValue( self._new_options.GetInteger( 'duplicate_comparison_score_much_higher_jpeg_quality' ) )
        self._duplicate_comparison_score_higher_filesize.setValue( self._new_options.GetInteger( 'duplicate_comparison_score_higher_filesize' ) )
        self._duplicate_comparison_score_much_higher_filesize.setValue( self._new_options.GetInteger( 'duplicate_comparison_score_much_higher_filesize' ) )
        self._duplicate_comparison_score_higher_resolution.setValue( self._new_options.GetInteger( 'duplicate_comparison_score_higher_resolution' ) )
        self._duplicate_comparison_score_much_higher_resolution.setValue( self._new_options.GetInteger( 'duplicate_comparison_score_much_higher_resolution' ) )
        self._duplicate_comparison_score_more_tags.setValue( self._new_options.GetInteger( 'duplicate_comparison_score_more_tags' ) )
        self._duplicate_comparison_score_older.setValue( self._new_options.GetInteger( 'duplicate_comparison_score_older' ) )
        self._duplicate_comparison_score_nicer_ratio.setValue( self._new_options.GetInteger( 'duplicate_comparison_score_nicer_ratio' ) )
        self._duplicate_comparison_score_has_audio.setValue( self._new_options.GetInteger( 'duplicate_comparison_score_has_audio' ) )
        
        self._duplicate_filter_max_batch_size.setValue( self._new_options.GetInteger( 'duplicate_filter_max_batch_size' ) )
        self._duplicate_filter_auto_commit_batch_size.SetValue( self._new_options.GetNoneableInteger( 'duplicate_filter_auto_commit_batch_size' ) )
        
        self._duplicate_background_switch_intensity_a.SetValue( self._new_options.GetNoneableInteger( 'duplicate_background_switch_intensity_a' ) )
        self._duplicate_background_switch_intensity_b.SetValue( self._new_options.GetNoneableInteger( 'duplicate_background_switch_intensity_b' ) )
        self._draw_transparency_checkerboard_media_canvas_duplicates.setChecked( self._new_options.GetBoolean( 'draw_transparency_checkerboard_media_canvas_duplicates' ) )
        
        #
        
        rows = []
        
        rows.append( ( 'Set to "all my files" when hitting "Open files in a new duplicates filter page":', self._open_files_to_duplicate_filter_uses_all_my_files ) )
        
        gridbox = ClientGUICommon.WrapInGrid( open_panel, rows )
        
        open_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        rows = []
        
        rows.append( ( 'Hide the "x% done" notification on preparation tab when >99% searched:', self._hide_duplicates_needs_work_message_when_reasonably_caught_up ) )
        
        gridbox = ClientGUICommon.WrapInGrid( duplicates_filter_page_panel, rows )
        
        duplicates_filter_page_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        rows = []
        
        rows.append( ( 'Score for jpeg with non-trivially higher jpeg quality:', self._duplicate_comparison_score_higher_jpeg_quality ) )
        rows.append( ( 'Score for jpeg with significantly higher jpeg quality:', self._duplicate_comparison_score_much_higher_jpeg_quality ) )
        rows.append( ( 'Score for file with non-trivially higher filesize:', self._duplicate_comparison_score_higher_filesize ) )
        rows.append( ( 'Score for file with significantly higher filesize:', self._duplicate_comparison_score_much_higher_filesize ) )
        rows.append( ( 'Score for file with higher resolution (as num pixels):', self._duplicate_comparison_score_higher_resolution ) )
        rows.append( ( 'Score for file with significantly higher resolution (as num pixels):', self._duplicate_comparison_score_much_higher_resolution ) )
        rows.append( ( 'Score for file with more tags:', self._duplicate_comparison_score_more_tags ) )
        rows.append( ( 'Score for file with non-trivially earlier import time:', self._duplicate_comparison_score_older ) )
        rows.append( ( 'Score for file with \'nicer\' resolution ratio:', self._duplicate_comparison_score_nicer_ratio ) )
        rows.append( ( 'Score for file with audio:', self._duplicate_comparison_score_has_audio ) )
        
        gridbox = ClientGUICommon.WrapInGrid( weights_panel, rows )
        
        label = 'When processing potential duplicate pairs in the duplicate filter, the client tries to present the \'best\' file first. It judges the two files on a variety of potential differences, each with a score. The file with the greatest total score is presented first. Here you can tinker with these scores.'
        label += '\n' * 2
        label += 'I recommend you leave all these as positive numbers, but if you wish, you can set a negative number to reduce the score.'
        
        st = ClientGUICommon.BetterStaticText( weights_panel, label )
        st.setWordWrap( True )
        
        weights_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
        weights_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        rows = []
        
        rows.append( ( 'Max size of duplicate filter pair batches (in mixed mode):', self._duplicate_filter_max_batch_size ) )
        rows.append( ( 'Auto-commit completed batches of this size or smaller:', self._duplicate_filter_auto_commit_batch_size ) )
        
        gridbox = ClientGUICommon.WrapInGrid( batches_panel, rows )
        
        batches_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        st = ClientGUICommon.BetterStaticText( colours_panel, label = 'The duplicate filter can darken/lighten your normal background colour. This highlights the transitions between A and B and, if your background colour is normally pure white or black, can differentiate transparency vs white/black opaque image background.' )
        st.setWordWrap( True )
        
        colours_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        rows = []
        
        rows.append( ( 'background light/dark switch intensity for A:', self._duplicate_background_switch_intensity_a ) )
        rows.append( ( 'background light/dark switch intensity for B:', self._duplicate_background_switch_intensity_b ) )
        rows.append( ( 'draw image transparency as checkerboard in the duplicate filter:', self._draw_transparency_checkerboard_media_canvas_duplicates ) )
        
        gridbox = ClientGUICommon.WrapInGrid( colours_panel, rows )
        
        colours_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, open_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, duplicates_filter_page_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, batches_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, weights_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, colours_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.addStretch( 0 )
        
        self.setLayout( vbox )
        
    
    def UpdateOptions( self ):
        
        self._new_options.SetBoolean( 'open_files_to_duplicate_filter_uses_all_my_files', self._open_files_to_duplicate_filter_uses_all_my_files.isChecked() )
        
        self._new_options.SetBoolean( 'hide_duplicates_needs_work_message_when_reasonably_caught_up', self._hide_duplicates_needs_work_message_when_reasonably_caught_up.isChecked() )
        
        self._new_options.SetInteger( 'duplicate_comparison_score_higher_jpeg_quality', self._duplicate_comparison_score_higher_jpeg_quality.value() )
        self._new_options.SetInteger( 'duplicate_comparison_score_much_higher_jpeg_quality', self._duplicate_comparison_score_much_higher_jpeg_quality.value() )
        self._new_options.SetInteger( 'duplicate_comparison_score_higher_filesize', self._duplicate_comparison_score_higher_filesize.value() )
        self._new_options.SetInteger( 'duplicate_comparison_score_much_higher_filesize', self._duplicate_comparison_score_much_higher_filesize.value() )
        self._new_options.SetInteger( 'duplicate_comparison_score_higher_resolution', self._duplicate_comparison_score_higher_resolution.value() )
        self._new_options.SetInteger( 'duplicate_comparison_score_much_higher_resolution', self._duplicate_comparison_score_much_higher_resolution.value() )
        self._new_options.SetInteger( 'duplicate_comparison_score_more_tags', self._duplicate_comparison_score_more_tags.value() )
        self._new_options.SetInteger( 'duplicate_comparison_score_older', self._duplicate_comparison_score_older.value() )
        self._new_options.SetInteger( 'duplicate_comparison_score_nicer_ratio', self._duplicate_comparison_score_nicer_ratio.value() )
        self._new_options.SetInteger( 'duplicate_comparison_score_has_audio', self._duplicate_comparison_score_has_audio.value() )
        
        self._new_options.SetInteger( 'duplicate_filter_max_batch_size', self._duplicate_filter_max_batch_size.value() )
        
        self._new_options.SetNoneableInteger( 'duplicate_filter_auto_commit_batch_size', self._duplicate_filter_auto_commit_batch_size.GetValue() )
        
        self._new_options.SetNoneableInteger( 'duplicate_background_switch_intensity_a', self._duplicate_background_switch_intensity_a.GetValue() )
        self._new_options.SetNoneableInteger( 'duplicate_background_switch_intensity_b', self._duplicate_background_switch_intensity_b.GetValue() )
        self._new_options.SetBoolean( 'draw_transparency_checkerboard_media_canvas_duplicates', self._draw_transparency_checkerboard_media_canvas_duplicates.isChecked() )
        
    
