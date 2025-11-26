from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusTime

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientData
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.metadata import ClientGUITime
from hydrus.client.gui.panels.options import ClientGUIOptionsPanelBase
from hydrus.client.gui.widgets import ClientGUIBytes
from hydrus.client.gui.widgets import ClientGUICommon

class SpeedAndMemoryPanel( ClientGUIOptionsPanelBase.OptionsPagePanel ):
    
    def __init__( self, parent, new_options ):
        
        super().__init__( parent )
        
        self._new_options = new_options
        
        #
        
        thumbnail_cache_panel = ClientGUICommon.StaticBox( self, 'thumbnail cache', can_expand = True, start_expanded = False )
        
        self._thumbnail_cache_size = ClientGUIBytes.BytesControl( thumbnail_cache_panel )
        self._thumbnail_cache_size.valueChanged.connect( self.EventThumbnailsUpdate )
        
        tt = 'When thumbnails are loaded from disk, their bitmaps are saved for a while in memory so near-future access is super fast. If the total store of thumbnails exceeds this size setting, the least-recent-to-be-accessed will be discarded until the total size is less than it again.'
        tt += '\n' * 2
        tt += 'Most thumbnails are RGB, which means their size here is roughly [width x height x 3].'
        
        self._thumbnail_cache_size.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._estimated_number_thumbnails = QW.QLabel( '', thumbnail_cache_panel )
        
        self._thumbnail_cache_timeout = ClientGUITime.TimeDeltaButton( thumbnail_cache_panel, min = 300, days = True, hours = True, minutes = True )
        
        tt = 'The amount of not-accessed time after which a thumbnail will naturally be removed from the cache.'
        
        self._thumbnail_cache_timeout.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        image_cache_panel = ClientGUICommon.StaticBox( self, 'image cache', can_expand = True, start_expanded = False )
        
        self._image_cache_size = ClientGUIBytes.BytesControl( image_cache_panel )
        self._image_cache_size.valueChanged.connect( self.EventImageCacheUpdate )
        
        tt = 'When images are loaded from disk, their 100% zoom renders are saved for a while in memory so near-future access is super fast. If the total store of images exceeds this size setting, the least-recent-to-be-accessed will be discarded until the total size is less than it again.'
        tt += '\n' * 2
        tt += 'Most images are RGB, which means their size here is roughly [width x height x 3], with those dimensions being at 100% zoom.'
        
        self._image_cache_size.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._estimated_number_fullscreens = QW.QLabel( '', image_cache_panel )
        
        self._image_cache_timeout = ClientGUITime.TimeDeltaButton( image_cache_panel, min = 300, days = True, hours = True, minutes = True )
        
        tt = 'The amount of not-accessed time after which a rendered image will naturally be removed from the cache.'
        
        self._image_cache_timeout.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._image_cache_storage_limit_percentage = ClientGUICommon.BetterSpinBox( image_cache_panel, min = 10, max = 50 )
        
        tt = 'This option sets how much of the cache can go towards one image. If an image\'s total size (usually width x height x 3) is too large compared to the cache, it should not be cached or it will just flush everything else out in one stroke.'
        
        self._image_cache_storage_limit_percentage.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._image_cache_storage_limit_percentage_st = ClientGUICommon.BetterStaticText( image_cache_panel, label = '' )
        
        tt = 'This represents the typical size we are talking about at this percentage level. Could be wider or taller, but overall should have the same number of pixels. Anything smaller will be saved in the cache after load, anything larger will be loaded on demand and forgotten as soon as you navigate away. If you want to have persistent fast access to images bigger than this, increase the total image cache size and/or the max % value permitted.'
        
        self._image_cache_storage_limit_percentage_st.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._image_cache_prefetch_limit_percentage = ClientGUICommon.BetterSpinBox( image_cache_panel, min = 10, max = 50 )
        
        tt = 'If you are browsing many big files and have large previous/next values to prefetch, this option caps the amount that will actually be prefetched, stopping the prefetcher from overloading and churning your cache by loading up seven or more gigantic images that each competitively flush each other out and need to be re-rendered over and over. For each media viewer, the prefetcher will only schedule this estimated amount of memory to be pre-rendered, and no further.'
        
        self._image_cache_prefetch_limit_percentage.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._image_cache_prefetch_limit_percentage_st = ClientGUICommon.BetterStaticText( image_cache_panel, label = '' )
        
        tt = 'This represents the overall prefetch we can accomodate at this percentage level. Files could be wider or taller, but any total prefetch (e.g. 3 back, 5 forward) will be capped to this amount (say 1 back, 2 forward). A particularly large file will block any prefetch, so check the max size too.'
        
        self._image_cache_prefetch_limit_percentage_st.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        prefetch_panel = ClientGUICommon.StaticBox( self, 'image prefetch', can_expand = True, start_expanded = False )
        
        self._media_viewer_prefetch_num_previous = ClientGUICommon.BetterSpinBox( prefetch_panel, min = 0, max = 50 )
        self._media_viewer_prefetch_num_next = ClientGUICommon.BetterSpinBox( prefetch_panel, min = 0, max = 50 )
        
        self._duplicate_filter_prefetch_num_pairs = ClientGUICommon.BetterSpinBox( prefetch_panel, min = 0, max = 25 )
        
        self._prefetch_label_warning = ClientGUICommon.BetterStaticText( prefetch_panel )
        self._prefetch_label_warning.setToolTip( ClientGUIFunctions.WrapToolTip( 'If you boost the prefetch numbers, make sure your image cache is big enough to handle it! Doubly so if you frequently load images that at 100% are far larger than your screen size. You really don\'t want to be prefetching more than your cache can hold!' ) )
        
        image_tile_cache_panel = ClientGUICommon.StaticBox( self, 'image tile cache', can_expand = True, start_expanded = False )
        
        self._image_tile_cache_size = ClientGUIBytes.BytesControl( image_tile_cache_panel )
        self._image_tile_cache_size.valueChanged.connect( self.EventImageTilesUpdate )
        
        tt = 'Zooming and displaying an image is expensive. When an image is rendered to screen at a particular zoom, the client breaks the virtual canvas into tiles and only scales and draws the image onto the viewable ones. As you pan around, new tiles may be needed and old ones discarded. It is all cached so you can pan and zoom over the same areas quickly.'
        
        self._image_tile_cache_size.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._estimated_number_image_tiles = QW.QLabel( '', image_tile_cache_panel )
        
        tt = 'You do not need to go crazy here unless you do a huge amount of zooming and really need multiple zoom levels cached for 10+ files you are comparing with each other.'
        
        self._estimated_number_image_tiles.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._image_tile_cache_timeout = ClientGUITime.TimeDeltaButton( image_tile_cache_panel, min = 300, hours = True, minutes = True )
        
        tt = 'The amount of not-accessed time after which a rendered tile will naturally be removed from the cache.'
        
        self._image_tile_cache_timeout.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._ideal_tile_dimension = ClientGUICommon.BetterSpinBox( image_tile_cache_panel, min = 256, max = 4096 )
        
        tt = 'This is the screen-visible square size the system will aim for. Smaller tiles are more memory efficient but prone to warping and other artifacts. Extreme values may waste CPU.'
        
        self._ideal_tile_dimension.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        #
        
        pages_panel = ClientGUICommon.StaticBox( self, 'download pages update', can_expand = True, start_expanded = False )
        
        self._gallery_page_status_update_time_minimum = ClientGUITime.TimeDeltaWidget( pages_panel, min = 0.25, seconds = True, milliseconds = True )
        self._gallery_page_status_update_time_ratio_denominator = ClientGUICommon.BetterSpinBox( pages_panel, min = 1 )
        
        self._watcher_page_status_update_time_minimum = ClientGUITime.TimeDeltaWidget( pages_panel, min = 0.25, seconds = True, milliseconds = True )
        self._watcher_page_status_update_time_ratio_denominator = ClientGUICommon.BetterSpinBox( pages_panel, min = 1 )
        
        #
        
        buffer_panel = ClientGUICommon.StaticBox( self, 'video buffer', can_expand = True, start_expanded = False )
        
        self._video_buffer_size = ClientGUIBytes.BytesControl( buffer_panel )
        self._video_buffer_size.valueChanged.connect( self.EventVideoBufferUpdate )
        
        self._estimated_number_video_frames = QW.QLabel( '', buffer_panel )
        
        #
        
        self._thumbnail_cache_size.SetValue( self._new_options.GetInteger( 'thumbnail_cache_size' ) )
        self._image_cache_size.SetValue( self._new_options.GetInteger( 'image_cache_size' ) )
        self._image_tile_cache_size.SetValue( self._new_options.GetInteger( 'image_tile_cache_size' ) )
        
        self._thumbnail_cache_timeout.SetValue( self._new_options.GetInteger( 'thumbnail_cache_timeout' ) )
        self._image_cache_timeout.SetValue( self._new_options.GetInteger( 'image_cache_timeout' ) )
        self._image_tile_cache_timeout.SetValue( self._new_options.GetInteger( 'image_tile_cache_timeout' ) )
        
        self._ideal_tile_dimension.setValue( self._new_options.GetInteger( 'ideal_tile_dimension' ) )
        
        self._gallery_page_status_update_time_minimum.SetValue( HydrusTime.SecondiseMSFloat( self._new_options.GetInteger( 'gallery_page_status_update_time_minimum_ms' ) ) )
        self._gallery_page_status_update_time_ratio_denominator.setValue( self._new_options.GetInteger( 'gallery_page_status_update_time_ratio_denominator' ) )
        
        self._watcher_page_status_update_time_minimum.SetValue( HydrusTime.SecondiseMSFloat( self._new_options.GetInteger( 'watcher_page_status_update_time_minimum_ms' ) ) )
        self._watcher_page_status_update_time_ratio_denominator.setValue( self._new_options.GetInteger( 'watcher_page_status_update_time_ratio_denominator' ) )
        
        self._video_buffer_size.SetValue( self._new_options.GetInteger( 'video_buffer_size' ) )
        
        self._media_viewer_prefetch_num_previous.setValue( self._new_options.GetInteger( 'media_viewer_prefetch_num_previous' ) )
        self._media_viewer_prefetch_num_next.setValue( self._new_options.GetInteger( 'media_viewer_prefetch_num_next' ) )
        self._duplicate_filter_prefetch_num_pairs.setValue( self._new_options.GetInteger( 'duplicate_filter_prefetch_num_pairs' ) )
        
        self._image_cache_storage_limit_percentage.setValue( self._new_options.GetInteger( 'image_cache_storage_limit_percentage' ) )
        self._image_cache_prefetch_limit_percentage.setValue( self._new_options.GetInteger( 'image_cache_prefetch_limit_percentage' ) )
        
        #
        
        vbox = QP.VBoxLayout()
        
        text = 'These options are advanced! PROTIP: Do not go crazy here.'
        
        st = ClientGUICommon.BetterStaticText( self, text )
        
        QP.AddToLayout( vbox, st, CC.FLAGS_CENTER )
        
        #
        
        thumbnails_sizer = QP.HBoxLayout()
        
        QP.AddToLayout( thumbnails_sizer, self._thumbnail_cache_size, CC.FLAGS_CENTER )
        QP.AddToLayout( thumbnails_sizer, self._estimated_number_thumbnails, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        fullscreens_sizer = QP.HBoxLayout()
        
        QP.AddToLayout( fullscreens_sizer, self._image_cache_size, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( fullscreens_sizer, self._estimated_number_fullscreens, CC.FLAGS_CENTER_PERPENDICULAR )
        
        image_tiles_sizer = QP.HBoxLayout()
        
        QP.AddToLayout( image_tiles_sizer, self._image_tile_cache_size, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( image_tiles_sizer, self._estimated_number_image_tiles, CC.FLAGS_CENTER_PERPENDICULAR )
        
        image_cache_storage_sizer = QP.HBoxLayout()
        
        QP.AddToLayout( image_cache_storage_sizer, self._image_cache_storage_limit_percentage, CC.FLAGS_EXPAND_BOTH_WAYS_SHY )
        QP.AddToLayout( image_cache_storage_sizer, self._image_cache_storage_limit_percentage_st, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        image_cache_prefetch_sizer = QP.HBoxLayout()
        
        QP.AddToLayout( image_cache_prefetch_sizer, self._image_cache_prefetch_limit_percentage, CC.FLAGS_EXPAND_BOTH_WAYS_SHY )
        QP.AddToLayout( image_cache_prefetch_sizer, self._image_cache_prefetch_limit_percentage_st, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        video_buffer_sizer = QP.HBoxLayout()
        
        QP.AddToLayout( video_buffer_sizer, self._video_buffer_size, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( video_buffer_sizer, self._estimated_number_video_frames, CC.FLAGS_CENTER_PERPENDICULAR )
        
        #
        
        text = 'Does not change much, thumbs are cheap.'
        
        st = ClientGUICommon.BetterStaticText( thumbnail_cache_panel, text )
        
        thumbnail_cache_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        rows = []
        
        rows.append( ( 'Memory reserved for thumbnail cache:', thumbnails_sizer ) )
        rows.append( ( 'Thumbnail cache timeout:', self._thumbnail_cache_timeout ) )
        
        gridbox = ClientGUICommon.WrapInGrid( thumbnail_cache_panel, rows )
        
        thumbnail_cache_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        QP.AddToLayout( vbox, thumbnail_cache_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        text = 'Important if you want smooth navigation between different images in the media viewer. If you deal with huge images, bump up cache size and max size that can be cached or prefetched, but be prepared to pay the memory price.'
        text += '\n' * 2
        text += 'Allowing more prefetch is great, but it needs CPU.'
        
        st = ClientGUICommon.BetterStaticText( image_cache_panel, text )
        
        st.setWordWrap( True )
        
        image_cache_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        rows = []
        
        rows.append( ( 'Memory reserved for image cache:', fullscreens_sizer ) )
        rows.append( ( 'Image cache timeout:', self._image_cache_timeout ) )
        rows.append( ( 'Maximum image size (in % of cache) that can be cached:', image_cache_storage_sizer ) )
        rows.append( ( 'Maximum % of cache that will be prefetched per media viewer:', image_cache_prefetch_sizer ) )
        
        gridbox = ClientGUICommon.WrapInGrid( image_cache_panel, rows )
        
        image_cache_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        QP.AddToLayout( vbox, image_cache_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        rows = []
        
        rows.append( ( 'Num previous to prefetch in Media Viewer:', self._media_viewer_prefetch_num_previous ) )
        rows.append( ( 'Num next to prefetch in Media Viewer:', self._media_viewer_prefetch_num_next ) )
        rows.append( ( 'Num pairs to prefetch in Duplicate Filter:', self._duplicate_filter_prefetch_num_pairs ) )
        rows.append( ( 'Prefetch numbers exceed cache prefetch limit?', self._prefetch_label_warning ) )
        
        gridbox = ClientGUICommon.WrapInGrid( prefetch_panel, rows )
        
        prefetch_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        QP.AddToLayout( vbox, prefetch_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        text = 'Important if you do a lot of zooming in and out on the same image or a small number of comparison images.'
        
        st = ClientGUICommon.BetterStaticText( image_tile_cache_panel, text )
        
        image_tile_cache_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        rows = []
        
        rows.append( ( 'Memory reserved for image tile cache:', image_tiles_sizer ) )
        rows.append( ( 'Image tile cache timeout:', self._image_tile_cache_timeout ) )
        rows.append( ( 'Ideal tile width/height px:', self._ideal_tile_dimension ) )
        
        gridbox = ClientGUICommon.WrapInGrid( image_tile_cache_panel, rows )
        
        image_tile_cache_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        QP.AddToLayout( vbox, image_tile_cache_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        text = 'EXPERIMENTAL, HYDEV ONLY, STAY AWAY!'
        
        st = ClientGUICommon.BetterStaticText( pages_panel, text )
        
        st.setWordWrap( True )
        
        pages_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        rows = []
        
        rows.append( ( 'EXPERIMENTAL: Minimum gallery importer update time:', self._gallery_page_status_update_time_minimum ) )
        rows.append( ( 'EXPERIMENTAL: Gallery importer magic update time denominator:', self._gallery_page_status_update_time_ratio_denominator ) )
        
        rows.append( ( 'EXPERIMENTAL: Minimum watcher importer update time:', self._watcher_page_status_update_time_minimum ) )
        rows.append( ( 'EXPERIMENTAL: Watcher importer magic update time denominator:', self._watcher_page_status_update_time_ratio_denominator ) )
        
        gridbox = ClientGUICommon.WrapInGrid( pages_panel, rows )
        
        pages_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        QP.AddToLayout( vbox, pages_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        text = 'This old option does not apply to mpv! It only applies to the native hydrus animation renderer!'
        text += '\n'
        text += 'Hydrus video rendering is CPU intensive.'
        text += '\n'
        text += 'If you have a lot of memory, you can set a generous potential video buffer to compensate.'
        text += '\n'
        text += 'If the video buffer can hold an entire video, it only needs to be rendered once and will play and loop very smoothly.'
        text += '\n'
        text += 'PROTIP: Do not go crazy here.'
        
        st = ClientGUICommon.BetterStaticText( buffer_panel, text )
        
        st.setWordWrap( True )
        
        buffer_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        rows = []
        
        rows.append( ( 'Memory for video buffer: ', video_buffer_sizer ) )
        
        gridbox = ClientGUICommon.WrapInGrid( buffer_panel, rows )
        
        buffer_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        QP.AddToLayout( vbox, buffer_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        vbox.addStretch( 0 )
        
        self.setLayout( vbox )
        
        #
        
        self._image_cache_storage_limit_percentage.valueChanged.connect( self.EventImageCacheUpdate )
        self._image_cache_prefetch_limit_percentage.valueChanged.connect( self.EventImageCacheUpdate )
        
        self._media_viewer_prefetch_num_previous.valueChanged.connect( self.EventImageCacheUpdate )
        self._media_viewer_prefetch_num_next.valueChanged.connect( self.EventImageCacheUpdate )
        self._duplicate_filter_prefetch_num_pairs.valueChanged.connect( self.EventImageCacheUpdate )
        
        self.EventImageCacheUpdate()
        self.EventThumbnailsUpdate()
        self.EventImageTilesUpdate()
        self.EventVideoBufferUpdate()
        
    
    def EventImageCacheUpdate( self ):
        
        cache_size = self._image_cache_size.GetValue()
        
        display_size = ClientGUIFunctions.GetDisplaySize( self )
        
        estimated_bytes_per_fullscreen = 3 * display_size.width() * display_size.height()
        
        image_cache_estimate = cache_size // estimated_bytes_per_fullscreen
        
        self._estimated_number_fullscreens.setText( '(about {}-{} images the size of your screen)'.format( HydrusNumbers.ToHumanInt( image_cache_estimate // 2 ), HydrusNumbers.ToHumanInt( image_cache_estimate * 2 ) ) )
        
        num_pixels = cache_size * ( self._image_cache_storage_limit_percentage.value() / 100 ) / 3
        
        unit_square = num_pixels / ( 16 * 9 )
        
        unit_length = unit_square ** 0.5
        
        resolution = ( int( 16 * unit_length ), int( 9 * unit_length ) )
        
        self._image_cache_storage_limit_percentage_st.setText( '% - {} pixels, or a ~{} image'.format( HydrusNumbers.ToHumanInt( num_pixels ), ClientData.ResolutionToPrettyString( resolution ) ) )
        
        num_pixels = cache_size * ( self._image_cache_prefetch_limit_percentage.value() / 100 ) / 3
        
        unit_square = num_pixels / ( 16 * 9 )
        
        unit_length = unit_square ** 0.5
        
        big_resolution = ( int( 16 * unit_length ), int( 9 * unit_length ) )
        
        unit_square = ( num_pixels / 4 ) / ( 16 * 9 )
        
        unit_length = unit_square ** 0.5
        
        small_resolution = ( int( 16 * unit_length ), int( 9 * unit_length ) )
        
        self._image_cache_prefetch_limit_percentage_st.setText( '% - {} pixels: 5x ~{}, max ~{}'.format( HydrusNumbers.ToHumanInt( num_pixels ), ClientData.ResolutionToPrettyString( small_resolution ), ClientData.ResolutionToPrettyString( big_resolution ) ) )
        
        #
        
        image_1080p = 1080 * 1920 * 3
        image_4k = 2160 * 3840 * 3
        
        available_prefetch_bytes = cache_size * ( self._image_cache_prefetch_limit_percentage.value() / 100 )
        
        num_prefetch_media_viewer = 1 + self._media_viewer_prefetch_num_previous.value() + self._media_viewer_prefetch_num_next.value()
        num_prefetch_duplicate_filter = 2 + ( self._duplicate_filter_prefetch_num_pairs.value() * 2 )
        
        if num_prefetch_media_viewer * image_1080p > available_prefetch_bytes:
            
            label = 'Yes! You could not prefetch this number of 1080p images in the media viewer!'
            object_name = 'HydrusWarning'
            
        elif num_prefetch_media_viewer * image_4k > available_prefetch_bytes:
            
            label = 'Somewhat--you could not prefetch this number of 4k images in the media viewer.'
            object_name = 'HydrusWarning'
            
        elif num_prefetch_duplicate_filter * image_1080p > available_prefetch_bytes:
            
            label = 'Yes! You could not prefetch this number of 1080p images in the duplicate filter.'
            object_name = 'HydrusWarning'
            
        elif num_prefetch_duplicate_filter * image_4k > available_prefetch_bytes:
            
            label = 'Somewhat--you could not prefetch this number of 4k images in the duplicate filter.'
            object_name = 'HydrusWarning'
            
        else:
            
            label = 'No, looks good!'
            object_name = ''
            
        
        self._prefetch_label_warning.setText( label )
        
        if object_name != self._prefetch_label_warning.objectName():
            
            self._prefetch_label_warning.setObjectName( object_name )
            
            self._prefetch_label_warning.style().polish( self._prefetch_label_warning )
            
        
    
    def EventImageTilesUpdate( self ):
        
        value = self._image_tile_cache_size.GetValue()
        
        display_size = ClientGUIFunctions.GetDisplaySize( self )
        
        estimated_bytes_per_fullscreen = 3 * display_size.width() * display_size.height()
        
        estimate = value // estimated_bytes_per_fullscreen
        
        self._estimated_number_image_tiles.setText( '(about {} fullscreens)'.format( HydrusNumbers.ToHumanInt( estimate ) ) )
        
    
    def EventThumbnailsUpdate( self ):
        
        value = self._thumbnail_cache_size.GetValue()
        
        ( thumbnail_width, thumbnail_height ) = HC.options[ 'thumbnail_dimensions' ]
        
        res_string = ClientData.ResolutionToPrettyString( ( thumbnail_width, thumbnail_height ) )
        
        estimated_bytes_per_thumb = 3 * thumbnail_width * thumbnail_height
        
        estimated_thumbs = value // estimated_bytes_per_thumb
        
        self._estimated_number_thumbnails.setText( '(at '+res_string+', about '+HydrusNumbers.ToHumanInt(estimated_thumbs)+' thumbnails)' )
        
    
    def EventVideoBufferUpdate( self ):
        
        value = self._video_buffer_size.GetValue()
        
        estimated_720p_frames = int( value // ( 1280 * 720 * 3 ) )
        
        self._estimated_number_video_frames.setText( '(about '+HydrusNumbers.ToHumanInt(estimated_720p_frames)+' frames of 720p video)' )
        
    
    def UpdateOptions( self ):
        
        self._new_options.SetInteger( 'thumbnail_cache_size', self._thumbnail_cache_size.GetValue() )
        self._new_options.SetInteger( 'image_cache_size', self._image_cache_size.GetValue() )
        self._new_options.SetInteger( 'image_tile_cache_size', self._image_tile_cache_size.GetValue() )
        
        self._new_options.SetInteger( 'thumbnail_cache_timeout', self._thumbnail_cache_timeout.GetValue() )
        self._new_options.SetInteger( 'image_cache_timeout', self._image_cache_timeout.GetValue() )
        self._new_options.SetInteger( 'image_tile_cache_timeout', self._image_tile_cache_timeout.GetValue() )
        
        self._new_options.SetInteger( 'ideal_tile_dimension', self._ideal_tile_dimension.value() )
        
        self._new_options.SetInteger( 'media_viewer_prefetch_num_previous', self._media_viewer_prefetch_num_previous.value() )
        self._new_options.SetInteger( 'media_viewer_prefetch_num_next', self._media_viewer_prefetch_num_next.value() )
        self._new_options.SetInteger( 'duplicate_filter_prefetch_num_pairs', self._duplicate_filter_prefetch_num_pairs.value() )
        
        self._new_options.SetInteger( 'image_cache_storage_limit_percentage', self._image_cache_storage_limit_percentage.value() )
        self._new_options.SetInteger( 'image_cache_prefetch_limit_percentage', self._image_cache_prefetch_limit_percentage.value() )
        
        self._new_options.SetInteger( 'gallery_page_status_update_time_minimum_ms', int( self._gallery_page_status_update_time_minimum.GetValue() * 1000 ) )
        self._new_options.SetInteger( 'gallery_page_status_update_time_ratio_denominator', self._gallery_page_status_update_time_ratio_denominator.value() )
        
        self._new_options.SetInteger( 'watcher_page_status_update_time_minimum_ms', int( self._watcher_page_status_update_time_minimum.GetValue() * 1000 ) )
        self._new_options.SetInteger( 'watcher_page_status_update_time_ratio_denominator', self._watcher_page_status_update_time_ratio_denominator.value() )
        
        self._new_options.SetInteger( 'video_buffer_size', self._video_buffer_size.GetValue() )
        
    
