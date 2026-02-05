from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusNumbers
from hydrus.core.files.images import HydrusImageHandling

from hydrus.client import ClientConstants as CC
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.panels.options import ClientGUIOptionsPanelBase
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.gui.widgets import ClientGUIPathWidgets

class ThumbnailsPanel( ClientGUIOptionsPanelBase.OptionsPagePanel ):
    
    def __init__( self, parent, new_options ):
        
        super().__init__( parent )
        
        self._new_options = new_options
        
        thumbnail_appearance_box = ClientGUICommon.StaticBox( self, 'appearance' )
        
        self._thumbnail_width = ClientGUICommon.BetterSpinBox( thumbnail_appearance_box, min=20, max=2048 )
        self._thumbnail_height = ClientGUICommon.BetterSpinBox( thumbnail_appearance_box, min=20, max=2048 )
        
        self._thumbnail_border = ClientGUICommon.BetterSpinBox( thumbnail_appearance_box, min=0, max=20 )
        self._thumbnail_margin = ClientGUICommon.BetterSpinBox( thumbnail_appearance_box, min=0, max=20 )
        
        self._thumbnail_scale_type = ClientGUICommon.BetterChoice( thumbnail_appearance_box )
        
        for t in ( HydrusImageHandling.THUMBNAIL_SCALE_DOWN_ONLY, HydrusImageHandling.THUMBNAIL_SCALE_TO_FIT, HydrusImageHandling.THUMBNAIL_SCALE_TO_FILL ):
            
            self._thumbnail_scale_type.addItem( HydrusImageHandling.thumbnail_scale_str_lookup[ t ], t )
            
        
        # I tried <100%, but Qt seems to cap it to 1.0. Sad!
        self._thumbnail_dpr_percentage = ClientGUICommon.BetterSpinBox( thumbnail_appearance_box, min = 100, max = 800 )
        tt = 'If your OS runs at an UI scale greater than 100%, mirror it here and your thumbnails will look crisp. If you have multiple monitors at different UI scales, or you change UI scale regularly, set it to the largest one you use.'
        tt += '\n' * 2
        tt += 'I believe the UI scale on the monitor this dialog opened on was {}'.format( HydrusNumbers.FloatToPercentage( self.devicePixelRatio() ) )
        self._thumbnail_dpr_percentage.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._video_thumbnail_percentage_in = ClientGUICommon.BetterSpinBox( thumbnail_appearance_box, min=0, max=100 )
        
        self._fade_thumbnails = QW.QCheckBox( thumbnail_appearance_box )
        tt = 'Whenever thumbnails change (appearing on a page, selecting, an icon or tag banner changes), they normally fade from the old to the new. If you would rather they change instantly, in one frame, uncheck this.'
        self._fade_thumbnails.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._allow_blurhash_fallback = QW.QCheckBox( thumbnail_appearance_box )
        tt = 'If hydrus does not have a thumbnail for a file (e.g. you are looking at a deleted file, or one unexpectedly missing), but it does know its blurhash, it will generate a blurry thumbnail based off that blurhash. Turning this behaviour off here will make it always show the default "hydrus" thumbnail.'
        self._allow_blurhash_fallback.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        #
        
        thumbnail_interaction_box = ClientGUICommon.StaticBox( self, 'interaction' )
        
        self._show_extended_single_file_info_in_status_bar = QW.QCheckBox( thumbnail_interaction_box )
        tt = 'This will show, any time you have a single thumbnail selected, the file info summary you normally see in the top hover window of the media viewer in the main gui status bar. Check the "media viewer hovers" options panel to edit what this summary includes.'
        self._show_extended_single_file_info_in_status_bar.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._focus_preview_on_ctrl_click = QW.QCheckBox( thumbnail_interaction_box )
        self._focus_preview_on_ctrl_click_only_static = QW.QCheckBox( thumbnail_interaction_box )
        self._focus_preview_on_shift_click = QW.QCheckBox( thumbnail_interaction_box )
        self._focus_preview_on_shift_click_only_static = QW.QCheckBox( thumbnail_interaction_box )
        
        self._thumbnail_visibility_scroll_percent = ClientGUICommon.BetterSpinBox( thumbnail_interaction_box, min=1, max=99 )
        self._thumbnail_visibility_scroll_percent.setToolTip( ClientGUIFunctions.WrapToolTip( 'Lower numbers will cause fewer scrolls, higher numbers more.' ) )
        
        self._thumbnail_scroll_rate = QW.QLineEdit( thumbnail_interaction_box )
        
        #
        
        thumbnail_misc_box = ClientGUICommon.StaticBox( self, 'media background' )
        
        self._media_background_bmp_path = ClientGUIPathWidgets.FilePickerCtrl( thumbnail_misc_box )
        
        #
        
        ( thumbnail_width, thumbnail_height ) = HC.options[ 'thumbnail_dimensions' ]
        
        self._thumbnail_width.setValue( thumbnail_width )
        self._thumbnail_height.setValue( thumbnail_height )
        
        self._thumbnail_border.setValue( self._new_options.GetInteger( 'thumbnail_border' ) )
        self._thumbnail_margin.setValue( self._new_options.GetInteger( 'thumbnail_margin' ) )
        
        self._thumbnail_scale_type.SetValue( self._new_options.GetInteger( 'thumbnail_scale_type' ) )
        self._thumbnail_dpr_percentage.setValue( self._new_options.GetInteger( 'thumbnail_dpr_percent' ) )
        
        self._video_thumbnail_percentage_in.setValue( self._new_options.GetInteger( 'video_thumbnail_percentage_in' ) )
        
        self._allow_blurhash_fallback.setChecked( self._new_options.GetBoolean( 'allow_blurhash_fallback' ) )
        
        self._fade_thumbnails.setChecked( self._new_options.GetBoolean( 'fade_thumbnails' ) )
        
        self._focus_preview_on_ctrl_click.setChecked( self._new_options.GetBoolean( 'focus_preview_on_ctrl_click' ) )
        self._focus_preview_on_ctrl_click_only_static.setChecked( self._new_options.GetBoolean( 'focus_preview_on_ctrl_click_only_static' ) )
        self._focus_preview_on_shift_click.setChecked( self._new_options.GetBoolean( 'focus_preview_on_shift_click' ) )
        self._focus_preview_on_shift_click_only_static.setChecked( self._new_options.GetBoolean( 'focus_preview_on_shift_click_only_static' ) )
        
        self._thumbnail_visibility_scroll_percent.setValue( self._new_options.GetInteger( 'thumbnail_visibility_scroll_percent' ) )
        
        self._thumbnail_scroll_rate.setText( self._new_options.GetString( 'thumbnail_scroll_rate' ) )
        
        media_background_bmp_path = self._new_options.GetNoneableString( 'media_background_bmp_path' )
        
        if media_background_bmp_path is not None:
            
            self._media_background_bmp_path.SetPath( media_background_bmp_path )
            
        
        self._show_extended_single_file_info_in_status_bar.setChecked( self._new_options.GetBoolean( 'show_extended_single_file_info_in_status_bar' ) )
        
        #
        
        rows = []
        
        rows.append( ( 'Thumbnail width: ', self._thumbnail_width ) )
        rows.append( ( 'Thumbnail height: ', self._thumbnail_height ) )
        rows.append( ( 'Thumbnail border: ', self._thumbnail_border ) )
        rows.append( ( 'Thumbnail margin: ', self._thumbnail_margin ) )
        rows.append( ( 'Thumbnail scaling: ', self._thumbnail_scale_type ) )
        rows.append( ( 'Thumbnail UI-scale supersampling %: ', self._thumbnail_dpr_percentage ) )
        rows.append( ( 'Generate video thumbnails this % in: ', self._video_thumbnail_percentage_in ) )
        rows.append( ( 'Fade thumbnails: ', self._fade_thumbnails ) )
        rows.append( ( 'Use blurhash missing thumbnail fallback: ', self._allow_blurhash_fallback ) )
        
        gridbox = ClientGUICommon.WrapInGrid( thumbnail_appearance_box, rows )
        
        thumbnail_appearance_box.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        rows = []
        
        rows.append( ( 'When a single thumbnail is selected, show the media viewer\'s normal top hover file text in the status bar: ', self._show_extended_single_file_info_in_status_bar ) )
        rows.append( ( 'On ctrl-click, focus thumbnails in the preview window: ', self._focus_preview_on_ctrl_click ) )
        rows.append( ( '  Only on files with no duration: ', self._focus_preview_on_ctrl_click_only_static ) )
        rows.append( ( 'On shift-click, focus thumbnails in the preview window: ', self._focus_preview_on_shift_click ) )
        rows.append( ( '  Only on files with no duration: ', self._focus_preview_on_shift_click_only_static ) )
        rows.append( ( 'Do not scroll down on key navigation if thumbnail at least this % visible: ', self._thumbnail_visibility_scroll_percent ) )
        rows.append( ( 'EXPERIMENTAL: Scroll thumbnails at this rate per scroll tick: ', self._thumbnail_scroll_rate ) )
        
        gridbox = ClientGUICommon.WrapInGrid( thumbnail_interaction_box, rows )
        
        thumbnail_interaction_box.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        rows = []
        
        rows.append( ( 'EXPERIMENTAL: Image path for thumbnail panel background image (set blank to clear): ', self._media_background_bmp_path ) )
        
        gridbox = ClientGUICommon.WrapInGrid( thumbnail_misc_box, rows )
        
        thumbnail_misc_box.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, thumbnail_appearance_box, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, thumbnail_interaction_box, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, thumbnail_misc_box, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.addStretch( 0 )
        
        self.setLayout( vbox )
        
        self._UpdatePreviewCheckboxes()
        
    
    def _UpdatePreviewCheckboxes( self ):
        
        self._focus_preview_on_ctrl_click_only_static.setEnabled( self._focus_preview_on_ctrl_click.isChecked() )
        self._focus_preview_on_shift_click_only_static.setEnabled( self._focus_preview_on_shift_click.isChecked() )
        
    
    def UpdateOptions( self ):
        
        new_thumbnail_dimensions = [self._thumbnail_width.value(), self._thumbnail_height.value()]
        
        HC.options[ 'thumbnail_dimensions' ] = new_thumbnail_dimensions
        
        self._new_options.SetInteger( 'thumbnail_border', self._thumbnail_border.value() )
        self._new_options.SetInteger( 'thumbnail_margin', self._thumbnail_margin.value() )
        
        self._new_options.SetInteger( 'thumbnail_scale_type', self._thumbnail_scale_type.GetValue() )
        self._new_options.SetInteger( 'thumbnail_dpr_percent', self._thumbnail_dpr_percentage.value() )
        
        self._new_options.SetInteger( 'video_thumbnail_percentage_in', self._video_thumbnail_percentage_in.value() )
        
        self._new_options.SetBoolean( 'focus_preview_on_ctrl_click', self._focus_preview_on_ctrl_click.isChecked() )
        self._new_options.SetBoolean( 'focus_preview_on_ctrl_click_only_static', self._focus_preview_on_ctrl_click_only_static.isChecked() )
        self._new_options.SetBoolean( 'focus_preview_on_shift_click', self._focus_preview_on_shift_click.isChecked() )
        self._new_options.SetBoolean( 'focus_preview_on_shift_click_only_static', self._focus_preview_on_shift_click_only_static.isChecked() )
        
        self._new_options.SetBoolean( 'allow_blurhash_fallback', self._allow_blurhash_fallback.isChecked() )
        
        self._new_options.SetBoolean( 'fade_thumbnails', self._fade_thumbnails.isChecked() )
        
        self._new_options.SetBoolean( 'show_extended_single_file_info_in_status_bar', self._show_extended_single_file_info_in_status_bar.isChecked() )
        
        try:
            
            thumbnail_scroll_rate = self._thumbnail_scroll_rate.text()
            
            float( thumbnail_scroll_rate )
            
            self._new_options.SetString( 'thumbnail_scroll_rate', thumbnail_scroll_rate )
            
        except Exception as e:
            
            pass
            
        
        self._new_options.SetInteger( 'thumbnail_visibility_scroll_percent', self._thumbnail_visibility_scroll_percent.value() )
        
        media_background_bmp_path = self._media_background_bmp_path.GetPath()
        
        if media_background_bmp_path == '':
            
            media_background_bmp_path = None
            
        
        self._new_options.SetNoneableString( 'media_background_bmp_path', media_background_bmp_path )
        
    
