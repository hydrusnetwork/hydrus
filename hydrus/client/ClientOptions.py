import os
import threading

from qtpy import QtGui as QG

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusData
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTags

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientDefaults
from hydrus.client import ClientDuplicates

class ClientOptions( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_CLIENT_OPTIONS
    SERIALISABLE_NAME = 'Client Options'
    SERIALISABLE_VERSION = 4
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._dictionary = HydrusSerialisable.SerialisableDictionary()
        
        self._lock = threading.Lock()
        
        self._InitialiseDefaults()
        
    
    def _GetDefaultMediaViewOptions( self ):
        
        media_view = HydrusSerialisable.SerialisableDictionary() # integer keys, so got to be cleverer dict
        
        # media_show_action, media_start_paused, media_start_with_embed, preview_show_action, preview_start_paused, preview_start_with_embed, ( media_scale_up, media_scale_down, preview_scale_up, preview_scale_down, exact_zooms_only, scale_up_quality, scale_down_quality ) )
        
        from hydrus.client.gui import ClientGUIMPV
        
        if ClientGUIMPV.MPV_IS_AVAILABLE:
            
            video_action = CC.MEDIA_VIEWER_ACTION_SHOW_WITH_MPV
            audio_action = CC.MEDIA_VIEWER_ACTION_SHOW_WITH_MPV
            
            video_zoom_info = ( CC.MEDIA_VIEWER_SCALE_TO_CANVAS, CC.MEDIA_VIEWER_SCALE_TO_CANVAS, CC.MEDIA_VIEWER_SCALE_TO_CANVAS, CC.MEDIA_VIEWER_SCALE_TO_CANVAS, False, CC.ZOOM_LANCZOS4, CC.ZOOM_AREA )
            
        else:
            
            video_action = CC.MEDIA_VIEWER_ACTION_SHOW_WITH_NATIVE
            audio_action = CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON
            
            video_zoom_info = ( CC.MEDIA_VIEWER_SCALE_100, CC.MEDIA_VIEWER_SCALE_TO_CANVAS, CC.MEDIA_VIEWER_SCALE_TO_CANVAS, CC.MEDIA_VIEWER_SCALE_TO_CANVAS, True, CC.ZOOM_LANCZOS4, CC.ZOOM_AREA )
            
        
        image_zoom_info = ( CC.MEDIA_VIEWER_SCALE_TO_CANVAS, CC.MEDIA_VIEWER_SCALE_TO_CANVAS, CC.MEDIA_VIEWER_SCALE_TO_CANVAS, CC.MEDIA_VIEWER_SCALE_TO_CANVAS, False, CC.ZOOM_LANCZOS4, CC.ZOOM_AREA )
        gif_zoom_info = ( CC.MEDIA_VIEWER_SCALE_TO_CANVAS, CC.MEDIA_VIEWER_SCALE_TO_CANVAS, CC.MEDIA_VIEWER_SCALE_TO_CANVAS, CC.MEDIA_VIEWER_SCALE_TO_CANVAS, False, CC.ZOOM_LANCZOS4, CC.ZOOM_AREA )
        flash_zoom_info = ( CC.MEDIA_VIEWER_SCALE_TO_CANVAS, CC.MEDIA_VIEWER_SCALE_TO_CANVAS, CC.MEDIA_VIEWER_SCALE_TO_CANVAS, CC.MEDIA_VIEWER_SCALE_TO_CANVAS, False, CC.ZOOM_LINEAR, CC.ZOOM_LINEAR )
        
        null_zoom_info = ( CC.MEDIA_VIEWER_SCALE_100, CC.MEDIA_VIEWER_SCALE_100, CC.MEDIA_VIEWER_SCALE_100, CC.MEDIA_VIEWER_SCALE_100, False, CC.ZOOM_LINEAR, CC.ZOOM_LINEAR )
        
        media_start_paused = False
        media_start_with_embed = False
        preview_start_paused = False
        preview_start_with_embed = False
        
        media_view[ HC.GENERAL_IMAGE ] = ( CC.MEDIA_VIEWER_ACTION_SHOW_WITH_NATIVE, media_start_paused, media_start_with_embed, CC.MEDIA_VIEWER_ACTION_SHOW_WITH_NATIVE, preview_start_paused, preview_start_with_embed, image_zoom_info )
        
        media_view[ HC.GENERAL_ANIMATION ] = ( video_action, media_start_paused, media_start_with_embed, video_action, preview_start_paused, preview_start_with_embed, gif_zoom_info )
        
        media_view[ HC.GENERAL_VIDEO ] = ( video_action, media_start_paused, media_start_with_embed, video_action, preview_start_paused, preview_start_with_embed, video_zoom_info )
        
        media_view[ HC.GENERAL_AUDIO ] = ( audio_action, media_start_paused, media_start_with_embed, audio_action, preview_start_paused, preview_start_with_embed, null_zoom_info )
        
        media_view[ HC.GENERAL_APPLICATION ] = ( CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON, media_start_paused, media_start_with_embed, CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON, preview_start_paused, preview_start_with_embed, null_zoom_info )
        
        return media_view
        
    
    def _GetMediaViewOptions( self, mime ):
        
        if mime in self._dictionary[ 'media_view' ]:
            
            return self._dictionary[ 'media_view' ][ mime ]
            
        else:
            
            if mime not in HC.mimes_to_general_mimetypes:
                
                null_result = ( CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW, False, False, CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW, False, False, ( CC.MEDIA_VIEWER_SCALE_100, CC.MEDIA_VIEWER_SCALE_100, CC.MEDIA_VIEWER_SCALE_100, CC.MEDIA_VIEWER_SCALE_100, False, CC.ZOOM_LINEAR, CC.ZOOM_LINEAR ) )
                
                return null_result
                
            
            general_mime_type = HC.mimes_to_general_mimetypes[ mime ]
            
            if general_mime_type not in self._dictionary[ 'media_view' ]:
                
                self._dictionary[ 'media_view' ] = self._GetDefaultMediaViewOptions()
                
            
            return self._dictionary[ 'media_view' ][ general_mime_type ]
            
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_info = self._dictionary.GetSerialisableTuple()
        
        return serialisable_info
        
    
    def _InitialiseDefaults( self ):
        
        self._dictionary[ 'booleans' ] = {}
        
        self._dictionary[ 'booleans' ][ 'advanced_mode' ] = False
        
        self._dictionary[ 'booleans' ][ 'filter_inbox_and_archive_predicates' ] = False
        
        self._dictionary[ 'booleans' ][ 'discord_dnd_fix' ] = False
        self._dictionary[ 'booleans' ][ 'secret_discord_dnd_fix' ] = False
        
        self._dictionary[ 'booleans' ][ 'disable_cv_for_gifs' ] = False
        
        self._dictionary[ 'booleans' ][ 'show_unmatched_urls_in_media_viewer' ] = False
        
        self._dictionary[ 'booleans' ][ 'set_search_focus_on_page_change' ] = False
        
        self._dictionary[ 'booleans' ][ 'allow_remove_on_manage_tags_input' ] = True
        self._dictionary[ 'booleans' ][ 'yes_no_on_remove_on_manage_tags' ] = True
        
        self._dictionary[ 'booleans' ][ 'activate_window_on_tag_search_page_activation' ] = False
        
        self._dictionary[ 'booleans' ][ 'show_related_tags' ] = False
        self._dictionary[ 'booleans' ][ 'show_file_lookup_script_tags' ] = False
        
        self._dictionary[ 'booleans' ][ 'hide_message_manager_on_gui_iconise' ] = HC.PLATFORM_MACOS
        self._dictionary[ 'booleans' ][ 'hide_message_manager_on_gui_deactive' ] = False
        self._dictionary[ 'booleans' ][ 'freeze_message_manager_when_mouse_on_other_monitor' ] = False
        self._dictionary[ 'booleans' ][ 'freeze_message_manager_when_main_gui_minimised' ] = False
        
        self._dictionary[ 'booleans' ][ 'load_images_with_pil' ] = False
        
        self._dictionary[ 'booleans' ][ 'use_system_ffmpeg' ] = False
        
        self._dictionary[ 'booleans' ][ 'elide_page_tab_names' ] = True
        
        self._dictionary[ 'booleans' ][ 'maintain_similar_files_duplicate_pairs_during_idle' ] = False
        
        self._dictionary[ 'booleans' ][ 'show_namespaces' ] = True
        self._dictionary[ 'booleans' ][ 'replace_tag_underscores_with_spaces' ] = False
        
        self._dictionary[ 'booleans' ][ 'verify_regular_https' ] = True
        
        self._dictionary[ 'booleans' ][ 'reverse_page_shift_drag_behaviour' ] = False
        
        self._dictionary[ 'booleans' ][ 'anchor_and_hide_canvas_drags' ] = HC.PLATFORM_WINDOWS
        self._dictionary[ 'booleans' ][ 'touchscreen_canvas_drags_unanchor' ] = False
        
        self._dictionary[ 'booleans' ][ 'import_page_progress_display' ] = True
        
        self._dictionary[ 'booleans' ][ 'process_subs_in_random_order' ] = True
        
        self._dictionary[ 'booleans' ][ 'ac_select_first_with_count' ] = False
        
        self._dictionary[ 'booleans' ][ 'saving_sash_positions_on_exit' ] = True
        
        self._dictionary[ 'booleans' ][ 'file_maintenance_during_idle' ] = True
        self._dictionary[ 'booleans' ][ 'file_maintenance_during_active' ] = True
        
        self._dictionary[ 'booleans' ][ 'tag_display_maintenance_during_idle' ] = True
        self._dictionary[ 'booleans' ][ 'tag_display_maintenance_during_active' ] = True
        
        self._dictionary[ 'booleans' ][ 'save_page_sort_on_change' ] = False
        
        self._dictionary[ 'booleans' ][ 'pause_all_new_network_traffic' ] = False
        self._dictionary[ 'booleans' ][ 'boot_with_network_traffic_paused' ] = False
        self._dictionary[ 'booleans' ][ 'pause_all_file_queues' ] = False
        self._dictionary[ 'booleans' ][ 'pause_all_watcher_checkers' ] = False
        self._dictionary[ 'booleans' ][ 'pause_all_gallery_searches' ] = False
        
        self._dictionary[ 'booleans' ][ 'popup_message_force_min_width' ] = False
        
        self._dictionary[ 'booleans' ][ 'always_show_iso_time' ] = False
        
        self._dictionary[ 'booleans' ][ 'use_advanced_file_deletion_dialog' ] = False
        
        self._dictionary[ 'booleans' ][ 'show_new_on_file_seed_short_summary' ] = False
        self._dictionary[ 'booleans' ][ 'show_deleted_on_file_seed_short_summary' ] = False
        
        self._dictionary[ 'booleans' ][ 'only_save_last_session_during_idle' ] = False
        
        self._dictionary[ 'booleans' ][ 'do_human_sort_on_hdd_file_import_paths' ] = True
        
        self._dictionary[ 'booleans' ][ 'highlight_new_watcher' ] = True
        self._dictionary[ 'booleans' ][ 'highlight_new_query' ] = True
        
        self._dictionary[ 'booleans' ][ 'delete_files_after_export' ] = False
        
        self._dictionary[ 'booleans' ][ 'file_viewing_statistics_active' ] = True
        self._dictionary[ 'booleans' ][ 'file_viewing_statistics_active_on_dupe_filter' ] = False
        
        self._dictionary[ 'booleans' ][ 'prefix_hash_when_copying' ] = False
        self._dictionary[ 'booleans' ][ 'file_system_waits_on_wakeup' ] = False
        
        self._dictionary[ 'booleans' ][ 'always_show_system_everything' ] = False
        
        self._dictionary[ 'booleans' ][ 'watch_clipboard_for_watcher_urls' ] = False
        self._dictionary[ 'booleans' ][ 'watch_clipboard_for_other_recognised_urls' ] = False
        
        self._dictionary[ 'booleans' ][ 'default_search_synchronised' ] = True
        self._dictionary[ 'booleans' ][ 'autocomplete_float_main_gui' ] = True
        self._dictionary[ 'booleans' ][ 'autocomplete_float_frames' ] = False
        
        self._dictionary[ 'booleans' ][ 'global_audio_mute' ] = False
        self._dictionary[ 'booleans' ][ 'media_viewer_audio_mute' ] = False
        self._dictionary[ 'booleans' ][ 'media_viewer_uses_its_own_audio_volume' ] = False
        self._dictionary[ 'booleans' ][ 'preview_audio_mute' ] = False
        self._dictionary[ 'booleans' ][ 'preview_uses_its_own_audio_volume' ] = True
        
        self._dictionary[ 'booleans' ][ 'always_loop_gifs' ] = True
        
        self._dictionary[ 'booleans' ][ 'always_show_system_tray_icon' ] = False
        self._dictionary[ 'booleans' ][ 'minimise_client_to_system_tray' ] = False
        self._dictionary[ 'booleans' ][ 'close_client_to_system_tray' ] = False
        self._dictionary[ 'booleans' ][ 'start_client_in_system_tray' ] = False
        
        self._dictionary[ 'booleans' ][ 'use_qt_file_dialogs' ] = False
        
        self._dictionary[ 'booleans' ][ 'notify_client_api_cookies' ] = False
        
        self._dictionary[ 'booleans' ][ 'expand_parents_on_storage_taglists' ] = True
        self._dictionary[ 'booleans' ][ 'expand_parents_on_storage_autocomplete_taglists' ] = True
        
        self._dictionary[ 'booleans' ][ 'show_session_size_warnings' ] = True
        
        self._dictionary[ 'booleans' ][ 'delete_lock_for_archived_files' ] = False
        
        self._dictionary[ 'booleans' ][ 'remember_last_advanced_file_deletion_reason' ] = True
        self._dictionary[ 'booleans' ][ 'remember_last_advanced_file_deletion_special_action' ] = False
        
        self._dictionary[ 'booleans' ][ 'do_macos_debug_dialog_menus' ] = True
        
        self._dictionary[ 'booleans' ][ 'save_default_tag_service_tab_on_change' ] = True
        
        self._dictionary[ 'booleans' ][ 'force_animation_scanbar_show' ] = False
        
        #
        
        self._dictionary[ 'colours' ] = HydrusSerialisable.SerialisableDictionary()
        
        self._dictionary[ 'colours' ][ 'default' ] = HydrusSerialisable.SerialisableDictionary()
        
        self._dictionary[ 'colours' ][ 'default' ][ CC.COLOUR_THUMB_BACKGROUND ] = ( 255, 255, 255 )
        self._dictionary[ 'colours' ][ 'default' ][ CC.COLOUR_THUMB_BACKGROUND_SELECTED ] = ( 217, 242, 255 ) # light blue
        self._dictionary[ 'colours' ][ 'default' ][ CC.COLOUR_THUMB_BACKGROUND_REMOTE ] = ( 32, 32, 36 ) # 50% Payne's Gray
        self._dictionary[ 'colours' ][ 'default' ][ CC.COLOUR_THUMB_BACKGROUND_REMOTE_SELECTED ] = ( 64, 64, 72 ) # Payne's Gray
        self._dictionary[ 'colours' ][ 'default' ][ CC.COLOUR_THUMB_BORDER ] = ( 223, 227, 230 ) # light grey
        self._dictionary[ 'colours' ][ 'default' ][ CC.COLOUR_THUMB_BORDER_SELECTED ] = ( 1, 17, 26 ) # dark grey
        self._dictionary[ 'colours' ][ 'default' ][ CC.COLOUR_THUMB_BORDER_REMOTE ] = ( 248, 208, 204 ) # 25% Vermillion, 75% White
        self._dictionary[ 'colours' ][ 'default' ][ CC.COLOUR_THUMB_BORDER_REMOTE_SELECTED ] = ( 227, 66, 52 ) # Vermillion, lol
        self._dictionary[ 'colours' ][ 'default' ][ CC.COLOUR_THUMBGRID_BACKGROUND ] = ( 255, 255, 255 )
        self._dictionary[ 'colours' ][ 'default' ][ CC.COLOUR_AUTOCOMPLETE_BACKGROUND ] = ( 235, 248, 255 ) # very light blue
        self._dictionary[ 'colours' ][ 'default' ][ CC.COLOUR_MEDIA_BACKGROUND ] = ( 255, 255, 255 )
        self._dictionary[ 'colours' ][ 'default' ][ CC.COLOUR_MEDIA_TEXT ] = ( 0, 0, 0 )
        self._dictionary[ 'colours' ][ 'default' ][ CC.COLOUR_TAGS_BOX ] = ( 255, 255, 255 )
        
        self._dictionary[ 'colours' ][ 'darkmode' ] = HydrusSerialisable.SerialisableDictionary()
        
        self._dictionary[ 'colours' ][ 'darkmode' ][ CC.COLOUR_THUMB_BACKGROUND ] = ( 64, 64, 72 ) # Payne's Gray
        self._dictionary[ 'colours' ][ 'darkmode' ][ CC.COLOUR_THUMB_BACKGROUND_SELECTED ] = ( 112, 128, 144 ) # Slate Gray
        self._dictionary[ 'colours' ][ 'darkmode' ][ CC.COLOUR_THUMB_BACKGROUND_REMOTE ] = ( 64, 13, 2 ) # Black Bean
        self._dictionary[ 'colours' ][ 'darkmode' ][ CC.COLOUR_THUMB_BACKGROUND_REMOTE_SELECTED ] = ( 171, 39, 79 ) # Amaranth Purple
        self._dictionary[ 'colours' ][ 'darkmode' ][ CC.COLOUR_THUMB_BORDER ] = ( 145, 163, 176 ) # Cadet Grey
        self._dictionary[ 'colours' ][ 'darkmode' ][ CC.COLOUR_THUMB_BORDER_SELECTED ] = ( 223, 227, 230 ) # light grey
        self._dictionary[ 'colours' ][ 'darkmode' ][ CC.COLOUR_THUMB_BORDER_REMOTE ] = ( 248, 208, 204 ) # 25% Vermillion, 75% White
        self._dictionary[ 'colours' ][ 'darkmode' ][ CC.COLOUR_THUMB_BORDER_REMOTE_SELECTED ] = ( 227, 66, 52 ) # Vermillion, lol
        self._dictionary[ 'colours' ][ 'darkmode' ][ CC.COLOUR_THUMBGRID_BACKGROUND ] = ( 52, 52, 52 ) # 20% flat gray
        self._dictionary[ 'colours' ][ 'darkmode' ][ CC.COLOUR_AUTOCOMPLETE_BACKGROUND ] = ( 83, 98, 103 ) # Gunmetal
        self._dictionary[ 'colours' ][ 'darkmode' ][ CC.COLOUR_MEDIA_BACKGROUND ] = ( 52, 52, 52 ) # 20% flat gray
        self._dictionary[ 'colours' ][ 'darkmode' ][ CC.COLOUR_MEDIA_TEXT ] = ( 112, 128, 144 ) # Slate Gray
        self._dictionary[ 'colours' ][ 'darkmode' ][ CC.COLOUR_TAGS_BOX ] = ( 35, 38, 41 )
        
        #
        
        self._dictionary[ 'duplicate_action_options' ] = HydrusSerialisable.SerialisableDictionary()
        
        from hydrus.client.metadata import ClientTags
        
        self._dictionary[ 'duplicate_action_options' ][ HC.DUPLICATE_BETTER ] = ClientDuplicates.DuplicateActionOptions( [ ( CC.DEFAULT_LOCAL_TAG_SERVICE_KEY, HC.CONTENT_MERGE_ACTION_MOVE, HydrusTags.TagFilter() ), ( CC.DEFAULT_LOCAL_DOWNLOADER_TAG_SERVICE_KEY, HC.CONTENT_MERGE_ACTION_MOVE, HydrusTags.TagFilter() ) ], [ ( CC.DEFAULT_FAVOURITES_RATING_SERVICE_KEY, HC.CONTENT_MERGE_ACTION_MOVE ) ], sync_archive = True, sync_urls_action = HC.CONTENT_MERGE_ACTION_COPY )
        self._dictionary[ 'duplicate_action_options' ][ HC.DUPLICATE_SAME_QUALITY ] = ClientDuplicates.DuplicateActionOptions( [ ( CC.DEFAULT_LOCAL_TAG_SERVICE_KEY, HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE, HydrusTags.TagFilter() ), ( CC.DEFAULT_LOCAL_DOWNLOADER_TAG_SERVICE_KEY, HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE, HydrusTags.TagFilter() ) ], [ ( CC.DEFAULT_FAVOURITES_RATING_SERVICE_KEY, HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE ) ], sync_archive = True, sync_urls_action = HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE )
        self._dictionary[ 'duplicate_action_options' ][ HC.DUPLICATE_ALTERNATE ] = ClientDuplicates.DuplicateActionOptions()
        
        #
        
        self._dictionary[ 'integers' ] = {}
        
        self._dictionary[ 'integers' ][ 'notebook_tab_alignment' ] = CC.DIRECTION_UP
        
        self._dictionary[ 'integers' ][ 'video_buffer_size_mb' ] = 96
        
        self._dictionary[ 'integers' ][ 'related_tags_search_1_duration_ms' ] = 250
        self._dictionary[ 'integers' ][ 'related_tags_search_2_duration_ms' ] = 2000
        self._dictionary[ 'integers' ][ 'related_tags_search_3_duration_ms' ] = 6000
        
        self._dictionary[ 'integers' ][ 'suggested_tags_width' ] = 300
        
        self._dictionary[ 'integers' ][ 'similar_files_duplicate_pairs_search_distance' ] = 0
        
        self._dictionary[ 'integers' ][ 'default_new_page_goes' ] = CC.NEW_PAGE_GOES_FAR_RIGHT
        
        self._dictionary[ 'integers' ][ 'max_page_name_chars' ] = 20
        self._dictionary[ 'integers' ][ 'page_file_count_display' ] = CC.PAGE_FILE_COUNT_DISPLAY_ALL
        
        self._dictionary[ 'integers' ][ 'network_timeout' ] = 10
        self._dictionary[ 'integers' ][ 'connection_error_wait_time' ] = 15
        self._dictionary[ 'integers' ][ 'serverside_bandwidth_wait_time' ] = 60
        
        self._dictionary[ 'integers' ][ 'thumbnail_visibility_scroll_percent' ] = 75
        self._dictionary[ 'integers' ][ 'ideal_tile_dimension' ] = 768
        
        self._dictionary[ 'integers' ][ 'total_pages_warning' ] = 165
        
        self._dictionary[ 'integers' ][ 'wake_delay_period' ] = 15
        
        from hydrus.client.gui.canvas import ClientGUICanvas
        
        self._dictionary[ 'integers' ][ 'media_viewer_zoom_center' ] = ClientGUICanvas.ZOOM_CENTERPOINT_MOUSE
        
        self._dictionary[ 'integers' ][ 'last_session_save_period_minutes' ] = 5
        
        self._dictionary[ 'integers' ][ 'shutdown_work_period' ] = 86400
        
        self._dictionary[ 'integers' ][ 'max_network_jobs' ] = 15
        self._dictionary[ 'integers' ][ 'max_network_jobs_per_domain' ] = 3
        
        from hydrus.core import HydrusImageHandling
        
        self._dictionary[ 'integers' ][ 'thumbnail_scale_type' ] = HydrusImageHandling.THUMBNAIL_SCALE_DOWN_ONLY
        
        self._dictionary[ 'integers' ][ 'max_simultaneous_subscriptions' ] = 1
        
        self._dictionary[ 'integers' ][ 'gallery_page_wait_period_pages' ] = 15
        self._dictionary[ 'integers' ][ 'gallery_page_wait_period_subscriptions' ] = 5
        self._dictionary[ 'integers' ][ 'watcher_page_wait_period' ] = 5
        
        self._dictionary[ 'integers' ][ 'popup_message_character_width' ] = 56
        
        self._dictionary[ 'integers' ][ 'duplicate_filter_max_batch_size' ] = 250
        
        self._dictionary[ 'integers' ][ 'video_thumbnail_percentage_in' ] = 35
        
        self._dictionary[ 'integers' ][ 'global_audio_volume' ] = 70
        self._dictionary[ 'integers' ][ 'media_viewer_audio_volume' ] = 70
        self._dictionary[ 'integers' ][ 'preview_audio_volume' ] = 70
        
        self._dictionary[ 'integers' ][ 'duplicate_comparison_score_higher_jpeg_quality' ] = 10
        self._dictionary[ 'integers' ][ 'duplicate_comparison_score_much_higher_jpeg_quality' ] = 20
        self._dictionary[ 'integers' ][ 'duplicate_comparison_score_higher_filesize' ] = 10
        self._dictionary[ 'integers' ][ 'duplicate_comparison_score_much_higher_filesize' ] = 20
        self._dictionary[ 'integers' ][ 'duplicate_comparison_score_higher_resolution' ] = 20
        self._dictionary[ 'integers' ][ 'duplicate_comparison_score_much_higher_resolution' ] = 50
        self._dictionary[ 'integers' ][ 'duplicate_comparison_score_more_tags' ] = 8
        self._dictionary[ 'integers' ][ 'duplicate_comparison_score_older' ] = 4
        self._dictionary[ 'integers' ][ 'duplicate_comparison_score_nicer_ratio' ] = 10
        
        self._dictionary[ 'integers' ][ 'image_tile_cache_size' ] = 1024 * 1024 * 256
        
        self._dictionary[ 'integers' ][ 'thumbnail_cache_timeout' ] = 86400
        self._dictionary[ 'integers' ][ 'image_cache_timeout' ] = 600
        self._dictionary[ 'integers' ][ 'image_tile_cache_timeout' ] = 300
        
        self._dictionary[ 'integers' ][ 'image_cache_storage_limit_percentage' ] = 25
        self._dictionary[ 'integers' ][ 'image_cache_prefetch_limit_percentage' ] = 10
        
        self._dictionary[ 'integers' ][ 'media_viewer_prefetch_delay_base_ms' ] = 100
        self._dictionary[ 'integers' ][ 'media_viewer_prefetch_num_previous' ] = 2
        self._dictionary[ 'integers' ][ 'media_viewer_prefetch_num_next' ] = 3
        
        self._dictionary[ 'integers' ][ 'thumbnail_border' ] = 1
        self._dictionary[ 'integers' ][ 'thumbnail_margin' ] = 2
        
        self._dictionary[ 'integers' ][ 'file_maintenance_idle_throttle_files' ] = 1
        self._dictionary[ 'integers' ][ 'file_maintenance_idle_throttle_time_delta' ] = 2
        
        self._dictionary[ 'integers' ][ 'file_maintenance_active_throttle_files' ] = 1
        self._dictionary[ 'integers' ][ 'file_maintenance_active_throttle_time_delta' ] = 20
        
        self._dictionary[ 'integers' ][ 'subscription_network_error_delay' ] = 12 * 3600
        self._dictionary[ 'integers' ][ 'subscription_other_error_delay' ] = 36 * 3600
        self._dictionary[ 'integers' ][ 'downloader_network_error_delay' ] = 90 * 60
        
        self._dictionary[ 'integers' ][ 'file_viewing_stats_menu_display' ] = CC.FILE_VIEWING_STATS_MENU_DISPLAY_MEDIA_AND_PREVIEW_IN_SUBMENU
        
        self._dictionary[ 'integers' ][ 'number_of_gui_session_backups' ] = 10
        
        self._dictionary[ 'integers' ][ 'animated_scanbar_height' ] = 20
        self._dictionary[ 'integers' ][ 'animated_scanbar_nub_width' ] = 10
        
        self._dictionary[ 'integers' ][ 'domain_network_infrastructure_error_number' ] = 3
        self._dictionary[ 'integers' ][ 'domain_network_infrastructure_error_time_delta' ] = 600
        
        self._dictionary[ 'integers' ][ 'ac_read_list_height_num_chars' ] = 19
        self._dictionary[ 'integers' ][ 'ac_write_list_height_num_chars' ] = 11
        
        self._dictionary[ 'integers' ][ 'system_busy_cpu_percent' ] = 50
        
        self._dictionary[ 'integers' ][ 'human_bytes_sig_figs' ] = 3
        
        #
        
        self._dictionary[ 'keys' ] = {}
        
        self._dictionary[ 'keys' ][ 'default_tag_service_tab' ] = CC.DEFAULT_LOCAL_TAG_SERVICE_KEY.hex()
        self._dictionary[ 'keys' ][ 'default_tag_service_search_page' ] = CC.COMBINED_TAG_SERVICE_KEY.hex()
        self._dictionary[ 'keys' ][ 'default_gug_key' ] = HydrusData.GenerateKey().hex()
        
        self._dictionary[ 'key_list' ] = {}
        
        self._dictionary[ 'key_list' ][ 'default_neighbouring_txt_tag_service_keys' ] = []
        
        #
        
        self._dictionary[ 'noneable_integers' ] = {}
        
        self._dictionary[ 'noneable_integers' ][ 'forced_search_limit' ] = None
        
        self._dictionary[ 'noneable_integers' ][ 'num_recent_tags' ] = 20
        
        self._dictionary[ 'noneable_integers' ][ 'duplicate_background_switch_intensity' ] = 3
        
        self._dictionary[ 'noneable_integers' ][ 'last_review_bandwidth_search_distance' ] = 7 * 86400
        
        self._dictionary[ 'noneable_integers' ][ 'file_viewing_statistics_media_min_time' ] = 2
        self._dictionary[ 'noneable_integers' ][ 'file_viewing_statistics_media_max_time' ] = 600
        self._dictionary[ 'noneable_integers' ][ 'file_viewing_statistics_preview_min_time' ] = 5
        self._dictionary[ 'noneable_integers' ][ 'file_viewing_statistics_preview_max_time' ] = 60
        
        self._dictionary[ 'noneable_integers' ][ 'subscription_file_error_cancel_threshold' ] = 5
        
        self._dictionary[ 'noneable_integers' ][ 'media_viewer_cursor_autohide_time_ms' ] = 700
        
        self._dictionary[ 'noneable_integers' ][ 'idle_mode_client_api_timeout' ] = None
        
        self._dictionary[ 'noneable_integers' ][ 'system_busy_cpu_count' ] = 1
        
        #
        
        self._dictionary[ 'simple_downloader_formulae' ] = HydrusSerialisable.SerialisableList()
        
        #
        
        self._dictionary[ 'noneable_strings' ] = {}
        
        self._dictionary[ 'noneable_strings' ][ 'favourite_file_lookup_script' ] = 'gelbooru md5'
        self._dictionary[ 'noneable_strings' ][ 'suggested_tags_layout' ] = 'notebook'
        self._dictionary[ 'noneable_strings' ][ 'backup_path' ] = None
        self._dictionary[ 'noneable_strings' ][ 'web_browser_path' ] = None
        self._dictionary[ 'noneable_strings' ][ 'last_png_export_dir' ] = None
        self._dictionary[ 'noneable_strings' ][ 'media_background_bmp_path' ] = None
        self._dictionary[ 'noneable_strings' ][ 'http_proxy' ] = None
        self._dictionary[ 'noneable_strings' ][ 'https_proxy' ] = None
        self._dictionary[ 'noneable_strings' ][ 'no_proxy' ] = '127.0.0.1'
        self._dictionary[ 'noneable_strings' ][ 'qt_style_name' ] = None
        self._dictionary[ 'noneable_strings' ][ 'qt_stylesheet_name' ] = None
        self._dictionary[ 'noneable_strings' ][ 'last_advanced_file_deletion_reason' ] = None
        self._dictionary[ 'noneable_strings' ][ 'last_advanced_file_deletion_special_action' ] = None
        
        self._dictionary[ 'strings' ] = {}
        
        self._dictionary[ 'strings' ][ 'app_display_name' ] = 'hydrus client'
        self._dictionary[ 'strings' ][ 'namespace_connector' ] = ':'
        self._dictionary[ 'strings' ][ 'export_phrase' ] = '{hash}'
        self._dictionary[ 'strings' ][ 'current_colourset' ] = 'default'
        self._dictionary[ 'strings' ][ 'favourite_simple_downloader_formula' ] = 'all files linked by images in page'
        self._dictionary[ 'strings' ][ 'thumbnail_scroll_rate' ] = '1.0'
        self._dictionary[ 'strings' ][ 'pause_character' ] = '\u23F8'
        self._dictionary[ 'strings' ][ 'stop_character' ] = '\u23F9'
        self._dictionary[ 'strings' ][ 'default_gug_name' ] = 'safebooru tag search'
        self._dictionary[ 'strings' ][ 'has_audio_label' ] = '\U0001F50A'
        self._dictionary[ 'strings' ][ 'has_duration_label' ] = ' \u23F5 '
        self._dictionary[ 'strings' ][ 'discord_dnd_filename_pattern' ] = '{hash}'
        
        self._dictionary[ 'string_list' ] = {}
        
        self._dictionary[ 'string_list' ][ 'default_media_viewer_custom_shortcuts' ] = []
        self._dictionary[ 'string_list' ][ 'favourite_tags' ] = []
        self._dictionary[ 'string_list' ][ 'advanced_file_deletion_reasons' ] = [ 'I do not like it.', 'It is bad quality.', 'It is not appropriate for this client.', 'Temporary delete--I want to bring it back later.' ]
        
        #
        
        self._dictionary[ 'custom_default_predicates' ] = HydrusSerialisable.SerialisableList()
        
        self._dictionary[ 'predicate_types_to_recent_predicates' ] = HydrusSerialisable.SerialisableDictionary()
        
        #
        
        self._dictionary[ 'favourite_tag_filters' ] = HydrusSerialisable.SerialisableDictionary()
        
        #
        
        from hydrus.client.media import ClientMedia
        from hydrus.client.metadata import ClientTags
        
        default_namespace_sorts = HydrusSerialisable.SerialisableList()
        
        default_namespace_sorts.append( ClientMedia.MediaSort( sort_type = ( 'namespaces', ( ( 'series', 'creator', 'title', 'volume', 'chapter', 'page' ), ClientTags.TAG_DISPLAY_ACTUAL ) ) ) )
        default_namespace_sorts.append( ClientMedia.MediaSort( sort_type = ( 'namespaces', ( ( 'creator', 'series', 'title', 'volume', 'chapter', 'page' ), ClientTags.TAG_DISPLAY_ACTUAL ) ) ) )
        
        self._dictionary[ 'default_namespace_sorts' ] = default_namespace_sorts
        
        #
        
        self._dictionary[ 'tag_summary_generators' ] = HydrusSerialisable.SerialisableDictionary()
        
        namespace_info = []
        
        namespace_info.append( ( 'creator', '', ', ' ) )
        namespace_info.append( ( 'series', '', ', ' ) )
        namespace_info.append( ( 'title', '', ', ' ) )
        
        separator = ' - '
        
        # the cleantags here converts to unicode, which is important!
        
        example_tags = HydrusTags.CleanTags( [ 'creator:creator', 'series:series', 'title:title' ] )
        
        from hydrus.client.gui import ClientGUITags
        
        tsg = ClientGUITags.TagSummaryGenerator( namespace_info = namespace_info, separator = separator, example_tags = example_tags )
        
        self._dictionary[ 'tag_summary_generators' ][ 'thumbnail_top' ] = tsg
        
        namespace_info = []
        
        namespace_info.append( ( 'volume', 'v', '-' ) )
        namespace_info.append( ( 'chapter', 'c', '-' ) )
        namespace_info.append( ( 'page', 'p', '-' ) )
        
        separator = '-'
        
        example_tags = HydrusTags.CleanTags( [ 'volume:3', 'chapter:10', 'page:330', 'page:331' ] )
        
        tsg = ClientGUITags.TagSummaryGenerator( namespace_info = namespace_info, separator = separator, example_tags = example_tags )
        
        self._dictionary[ 'tag_summary_generators' ][ 'thumbnail_bottom_right' ] = tsg
        
        namespace_info = []
        
        namespace_info.append( ( 'creator', '', ', ' ) )
        namespace_info.append( ( 'series', '', ', ' ) )
        namespace_info.append( ( 'title', '', ', ' ) )
        namespace_info.append( ( 'volume', 'v', '-' ) )
        namespace_info.append( ( 'chapter', 'c', '-' ) )
        namespace_info.append( ( 'page', 'p', '-' ) )
        
        separator = ' - '
        
        example_tags = HydrusTags.CleanTags( [ 'creator:creator', 'series:series', 'title:title', 'volume:1', 'chapter:1', 'page:1' ] )
        
        tsg = ClientGUITags.TagSummaryGenerator( namespace_info = namespace_info, separator = separator, example_tags = example_tags )
        
        self._dictionary[ 'tag_summary_generators' ][ 'media_viewer_top' ] = tsg
        
        #
        
        self._dictionary[ 'default_file_import_options' ] = HydrusSerialisable.SerialisableDictionary()
        
        exclude_deleted = True
        do_not_check_known_urls_before_importing = False
        do_not_check_hashes_before_importing = False
        allow_decompression_bombs = True
        min_size = None
        max_size = None
        max_gif_size = 32 * 1048576
        min_resolution = None
        max_resolution = None
        
        automatic_archive = False
        associate_primary_urls = True
        associate_source_urls = True
        
        from hydrus.client.importing.options import PresentationImportOptions
        
        presentation_import_options = PresentationImportOptions.PresentationImportOptions()
        
        presentation_import_options.SetPresentationStatus( PresentationImportOptions.PRESENTATION_STATUS_NEW_ONLY )
        
        from hydrus.client.importing.options import FileImportOptions
        
        quiet_file_import_options = FileImportOptions.FileImportOptions()
        
        quiet_file_import_options.SetPreImportOptions( exclude_deleted, do_not_check_known_urls_before_importing, do_not_check_hashes_before_importing, allow_decompression_bombs, min_size, max_size, max_gif_size, min_resolution, max_resolution )
        quiet_file_import_options.SetPostImportOptions( automatic_archive, associate_primary_urls, associate_source_urls )
        quiet_file_import_options.SetPresentationImportOptions( presentation_import_options )
        
        self._dictionary[ 'default_file_import_options' ][ 'quiet' ] = quiet_file_import_options
        
        loud_file_import_options = FileImportOptions.FileImportOptions()
        
        loud_file_import_options.SetPreImportOptions( exclude_deleted, do_not_check_known_urls_before_importing, do_not_check_hashes_before_importing, allow_decompression_bombs, min_size, max_size, max_gif_size, min_resolution, max_resolution )
        loud_file_import_options.SetPostImportOptions( automatic_archive, associate_primary_urls, associate_source_urls )
        
        self._dictionary[ 'default_file_import_options' ][ 'loud' ] = loud_file_import_options
        
        #
        
        self._dictionary[ 'frame_locations' ] = {}
        
        # remember size, remember position, last_size, last_pos, default gravity, default position, maximised, fullscreen
        self._dictionary[ 'frame_locations' ][ 'file_import_status' ] = ( True, True, None, None, ( -1, -1 ), 'topleft', False, False )
        self._dictionary[ 'frame_locations' ][ 'gallery_import_log' ] = ( True, True, None, None, ( -1, -1 ), 'topleft', False, False )
        self._dictionary[ 'frame_locations' ][ 'local_import_filename_tagging' ] = ( True, False, None, None, ( -1, -1 ), 'topleft', False, False )
        self._dictionary[ 'frame_locations' ][ 'main_gui' ] = ( True, True, ( 800, 600 ), ( 20, 20 ), ( -1, -1 ), 'topleft', True, False )
        self._dictionary[ 'frame_locations' ][ 'manage_options_dialog' ] = ( False, False, None, None, ( -1, -1 ), 'topleft', False, False )
        self._dictionary[ 'frame_locations' ][ 'manage_subscriptions_dialog' ] = ( True, True, None, None, ( 1, -1 ), 'topleft', False, False )
        self._dictionary[ 'frame_locations' ][ 'edit_subscription_dialog' ] = ( True, True, None, None, ( 1, -1 ), 'topleft', False, False )
        self._dictionary[ 'frame_locations' ][ 'manage_tags_dialog' ] = ( False, False, None, None, ( -1, 1 ), 'topleft', False, False )
        self._dictionary[ 'frame_locations' ][ 'manage_tags_frame' ] = ( False, False, None, None, ( -1, 1 ), 'topleft', False, False )
        self._dictionary[ 'frame_locations' ][ 'media_viewer' ] = ( True, True, ( 640, 480 ), ( 70, 70 ), ( -1, -1 ), 'topleft', True, True )
        self._dictionary[ 'frame_locations' ][ 'regular_dialog' ] = ( False, False, None, None, ( -1, -1 ), 'topleft', False, False )
        self._dictionary[ 'frame_locations' ][ 'review_services' ] = ( False, True, None, None, ( -1, -1 ), 'topleft', False, False )
        self._dictionary[ 'frame_locations' ][ 'deeply_nested_dialog' ] = ( False, False, None, None, ( -1, -1 ), 'topleft', False, False )
        self._dictionary[ 'frame_locations' ][ 'regular_center_dialog' ] = ( False, False, None, None, ( -1, -1 ), 'center', False, False )
        
        #
        
        self._dictionary[ 'media_launch' ] = HydrusSerialisable.SerialisableDictionary() # integer keys, so got to be cleverer dict
        
        for mime in HC.SEARCHABLE_MIMES:
            
            self._dictionary[ 'media_launch' ][ mime ] = None
            
        
        #
        
        self._dictionary[ 'media_view' ] = self._GetDefaultMediaViewOptions()
        
        self._dictionary[ 'media_zooms' ] = [ 0.01, 0.05, 0.1, 0.15, 0.2, 0.3, 0.5, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.5, 2.0, 3.0, 5.0, 10.0, 20.0 ]
        
        #
        
        self._dictionary[ 'misc' ] = HydrusSerialisable.SerialisableDictionary()
        
        self._dictionary[ 'misc' ][ 'default_thread_watcher_options' ] = ClientDefaults.GetDefaultCheckerOptions( 'thread' )
        self._dictionary[ 'misc' ][ 'default_subscription_checker_options' ] = ClientDefaults.GetDefaultCheckerOptions( 'artist subscription' )
        
        #
        
        self._dictionary[ 'suggested_tags' ] = HydrusSerialisable.SerialisableDictionary()
        
        self._dictionary[ 'suggested_tags' ][ 'favourites' ] = {}
        
        #
        
        from hydrus.client.media import ClientMedia
        
        self._dictionary[ 'default_sort' ] = ClientMedia.MediaSort( ( 'system', CC.SORT_FILES_BY_FILESIZE ), CC.SORT_ASC )
        self._dictionary[ 'fallback_sort' ] = ClientMedia.MediaSort( ( 'system', CC.SORT_FILES_BY_IMPORT_TIME ), CC.SORT_ASC )
        
        self._dictionary[ 'default_collect' ] = ClientMedia.MediaCollect()
        
        #
        
        from hydrus.client.metadata import ClientTagSorting
        
        self._dictionary[ 'default_tag_sort' ] = ClientTagSorting.TagSort.STATICGetTextASCDefault()
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        loaded_dictionary = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_info )
        
        for ( key, value ) in list(loaded_dictionary.items()):
            
            if key in self._dictionary and isinstance( self._dictionary[ key ], dict ) and isinstance( value, dict ):
                
                self._dictionary[ key ].update( value )
                
            else:
                
                self._dictionary[ key ] = value
                
            
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            loaded_dictionary = HydrusSerialisable.CreateFromSerialisableTuple( old_serialisable_info )
            
            if 'media_view' in loaded_dictionary:
                
                mimes = list(loaded_dictionary[ 'media_view' ].keys())
                
                for mime in mimes:
                    
                    if mime in self._dictionary[ 'media_view' ]:
                        
                        ( default_media_show_action, default_preview_show_action, default_zoom_info ) = self._dictionary[ 'media_view' ][ mime ]
                        
                        ( media_show_action, preview_show_action, zoom_in_to_fit, exact_zooms_only, scale_up_quality, scale_down_quality ) = loaded_dictionary[ 'media_view' ][ mime ]
                        
                        loaded_dictionary[ 'media_view' ][ mime ] = ( media_show_action, preview_show_action, default_zoom_info )
                        
                    else:
                        
                        # while devving this, I discovered some u'20' stringified keys had snuck in and hung around. let's nuke them here, in case anyone else got similar
                        
                        del loaded_dictionary[ 'media_view' ][ mime ]
                        
                    
                
            
            new_serialisable_info = loaded_dictionary.GetSerialisableTuple()
            
            return ( 2, new_serialisable_info )
            
        
        if version == 2:
            
            # as db_dir is now moveable, let's move portable base from base_dir to db_dir
            
            def update_portable_path( p ):
                
                if p is None:
                    
                    return p
                    
                
                p = os.path.normpath( p ) # collapses .. stuff and converts / to \\ for windows only
                
                if os.path.isabs( p ):
                    
                    a_p = p
                    
                else:
                    
                    a_p = os.path.normpath( os.path.join( HC.BASE_DIR, p ) )
                    
                
                if not HC.PLATFORM_WINDOWS and not os.path.exists( a_p ):
                    
                    a_p = a_p.replace( '\\', '/' )
                    
                
                try:
                    
                    db_dir = HG.controller.GetDBDir()
                    
                    p = os.path.relpath( a_p, db_dir )
                    
                    if p.startswith( '..' ):
                        
                        p = a_p
                        
                    
                except:
                    
                    p = a_p
                    
                
                if HC.PLATFORM_WINDOWS:
                    
                    p = p.replace( '\\', '/' ) # store seps as /, to maintain multiplatform uniformity
                    
                
                return p
                
            
            loaded_dictionary = HydrusSerialisable.CreateFromSerialisableTuple( old_serialisable_info )
            
            if 'client_files_locations_ideal_weights' in loaded_dictionary:
                
                updated_cfliw = []
                
                for ( old_portable_path, weight ) in loaded_dictionary[ 'client_files_locations_ideal_weights' ]:
                    
                    new_portable_path = update_portable_path( old_portable_path )
                    
                    updated_cfliw.append( ( new_portable_path, weight ) )
                    
                
                loaded_dictionary[ 'client_files_locations_ideal_weights' ] = updated_cfliw
                
            
            if 'client_files_locations_resized_thumbnail_override' in loaded_dictionary:
                
                loaded_dictionary[ 'client_files_locations_resized_thumbnail_override' ] = update_portable_path( loaded_dictionary[ 'client_files_locations_resized_thumbnail_override' ] )
                
            
            if 'client_files_locations_full_size_thumbnail_override' in loaded_dictionary:
                
                loaded_dictionary[ 'client_files_locations_full_size_thumbnail_override' ] = update_portable_path( loaded_dictionary[ 'client_files_locations_full_size_thumbnail_override' ] )
                
            
            new_serialisable_info = loaded_dictionary.GetSerialisableTuple()
            
            return ( 3, new_serialisable_info )
            
        
        if version == 3:
            
            loaded_dictionary = HydrusSerialisable.CreateFromSerialisableTuple( old_serialisable_info )
            
            if 'media_view' in loaded_dictionary:
                
                def convert_show_action( show_action ):
                    
                    start_paused = show_action in ( CC.MEDIA_VIEWER_ACTION_SHOW_BEHIND_EMBED_PAUSED, CC.MEDIA_VIEWER_ACTION_SHOW_WITH_NATIVE_PAUSED )
                    start_with_embed = show_action in ( CC.MEDIA_VIEWER_ACTION_SHOW_BEHIND_EMBED, CC.MEDIA_VIEWER_ACTION_SHOW_BEHIND_EMBED_PAUSED )
                    
                    if start_paused or start_with_embed:
                        
                        show_action = CC.MEDIA_VIEWER_ACTION_SHOW_WITH_NATIVE
                        
                    
                    return ( show_action, start_paused, start_with_embed )
                    
                
                for ( mime, ( media_show_action, preview_show_action, zoom_info ) ) in list( loaded_dictionary[ 'media_view' ].items() ):
                    
                    ( media_show_action, media_start_paused, media_start_with_embed ) = convert_show_action( media_show_action )
                    ( preview_show_action, preview_start_paused, preview_start_with_embed ) = convert_show_action( preview_show_action )
                    
                    loaded_dictionary[ 'media_view' ][ mime ] = ( media_show_action, media_start_paused, media_start_with_embed, preview_show_action, preview_start_paused, preview_start_with_embed, zoom_info )
                    
                
            
            new_serialisable_info = loaded_dictionary.GetSerialisableTuple()
            
            return ( 4, new_serialisable_info )
            
        
    
    def ClearCustomDefaultSystemPredicates( self, predicate_type = None, comparable_predicate = None ):
        
        with self._lock:
            
            custom_default_predicates = self._dictionary[ 'custom_default_predicates' ]
            
            if predicate_type is not None:
                
                new_custom_default_predicates = HydrusSerialisable.SerialisableList( [ pred for pred in custom_default_predicates if pred.GetType() != predicate_type ] )
                
                self._dictionary[ 'custom_default_predicates' ] = new_custom_default_predicates
                
                return
                
            
            if comparable_predicate is not None:
                
                new_custom_default_predicates = HydrusSerialisable.SerialisableList( [ pred for pred in custom_default_predicates if not pred.IsUIEditable( comparable_predicate ) ] )
                
                self._dictionary[ 'custom_default_predicates' ] = new_custom_default_predicates
                
                return
                
            
        
    
    def FlipBoolean( self, name ):
        
        with self._lock:
            
            self._dictionary[ 'booleans' ][ name ] = not self._dictionary[ 'booleans' ][ name ]
            
        
    
    def GetBoolean( self, name ):
        
        with self._lock:
            
            return self._dictionary[ 'booleans' ][ name ]
            
        
    
    def GetDefaultCollect( self ):
        
        with self._lock:
            
            return self._dictionary[ 'default_collect' ]
            
        
    
    def GetColour( self, colour_type, colourset = None ):
        
        with self._lock:
            
            if colourset is None:
                
                colourset = self._dictionary[ 'strings' ][ 'current_colourset' ]
                
            
            ( r, g, b ) = self._dictionary[ 'colours' ][ colourset ][ colour_type ]
            
            return QG.QColor( r, g, b )
            
        
    
    def GetCustomDefaultSystemPredicates( self, predicate_type = None, comparable_predicate = None ):
        
        with self._lock:
            
            custom_default_predicates = self._dictionary[ 'custom_default_predicates' ]
            
            if predicate_type is not None:
                
                return [ pred for pred in custom_default_predicates if pred.GetType() == predicate_type ]
                
            
            if comparable_predicate is not None:
                
                return [ pred for pred in custom_default_predicates if pred.IsUIEditable( comparable_predicate ) ]
                
            
            return []
            
        
    
    def GetDefaultFileImportOptions( self, options_type ):
        
        with self._lock:
            
            return self._dictionary[ 'default_file_import_options' ][ options_type ]
            
        
    
    def GetDefaultMediaViewOptions( self ):
        
        with self._lock:
            
            return self._GetDefaultMediaViewOptions()
            
        
    
    def GetDefaultNamespaceSorts( self ):
        
        with self._lock:
            
            return list( self._dictionary[ 'default_namespace_sorts' ] )
            
        
    
    def GetDefaultSort( self ):
        
        with self._lock:
            
            return self._dictionary[ 'default_sort' ]
            
        
    
    def GetDefaultSubscriptionCheckerOptions( self ):
        
        with self._lock:
            
            return self._dictionary[ 'misc' ][ 'default_subscription_checker_options' ]
            
        
    
    def GetDefaultTagSort( self ):
        
        with self._lock:
            
            return self._dictionary[ 'default_tag_sort' ]
            
        
    
    def GetDefaultWatcherCheckerOptions( self ):
        
        with self._lock:
            
            return self._dictionary[ 'misc' ][ 'default_thread_watcher_options' ]
            
        
    
    def GetDuplicateActionOptions( self, duplicate_type ):
        
        with self._lock:
            
            if duplicate_type in self._dictionary[ 'duplicate_action_options' ]:
                
                return self._dictionary[ 'duplicate_action_options' ][ duplicate_type ]
                
            else:
                
                return ClientDuplicates.DuplicateActionOptions( [], [] )
                
            
        
    
    def GetFallbackSort( self ):
        
        with self._lock:
            
            return self._dictionary[ 'fallback_sort' ]
            
        
    
    def GetFavouriteTagFilters( self ):
        
        with self._lock:
            
            return dict( self._dictionary[ 'favourite_tag_filters' ] )
            
        
    
    def GetFrameLocation( self, frame_key ):
        
        with self._lock:
            
            return self._dictionary[ 'frame_locations' ][ frame_key ]
            
        
    
    def GetFrameLocations( self ):
        
        with self._lock:
            
            return list(self._dictionary[ 'frame_locations' ].items())
            
        
    
    def GetInteger( self, name ):
        
        with self._lock:
            
            return self._dictionary[ 'integers' ][ name ]
            
        
    
    def GetKey( self, name ):
        
        with self._lock:
            
            return bytes.fromhex( self._dictionary[ 'keys' ][ name ] )
            
        
    
    def GetKeyList( self, name ):
        
        with self._lock:
            
            return [ bytes.fromhex( hex_key ) for hex_key in self._dictionary[ 'key_list' ][ name ] ]
            
        
    
    def GetMediaShowAction( self, mime ):
        
        with self._lock:
            
            ( media_show_action, media_start_paused, media_start_with_embed, preview_show_action, preview_start_paused, preview_start_with_embed, zoom_info ) = self._GetMediaViewOptions( mime )
            
            ( possible_show_actions, can_start_paused, can_start_with_embed ) = CC.media_viewer_capabilities[ mime ]
            
            if media_show_action not in possible_show_actions:
                
                return ( CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON, False, False )
                
            
            return ( media_show_action, media_start_paused, media_start_with_embed )
            
        
    
    def GetMediaViewOptions( self ):
        
        with self._lock:
            
            return dict( self._dictionary[ 'media_view' ] )
            
        
    
    def GetMediaZoomOptions( self, mime ):
        
        with self._lock:
            
            ( media_show_action, media_start_paused, media_start_with_embed, preview_show_action, preview_start_paused, preview_start_with_embed, zoom_info ) = self._GetMediaViewOptions( mime )
            
            return zoom_info
            
        
    
    def GetMediaZooms( self ):
        
        with self._lock:
            
            return list( self._dictionary[ 'media_zooms' ] )
            
        
    
    def GetMediaZoomQuality( self, mime ):
        
        with self._lock:
            
            ( media_show_action, media_start_paused, media_start_with_embed, preview_show_action, preview_start_paused, preview_start_with_embed, zoom_info ) = self._GetMediaViewOptions( mime )
            
            ( media_scale_up, media_scale_down, preview_scale_up, preview_scale_down, exact_zooms_only, scale_up_quality, scale_down_quality ) = zoom_info
            
            return ( scale_up_quality, scale_down_quality )
            
        
    
    def GetMimeLaunch( self, mime ):
        
        with self._lock:
            
            if mime not in self._dictionary[ 'media_launch' ]:
                
                self._dictionary[ 'media_launch' ][ mime ] = None
                
            
            return self._dictionary[ 'media_launch' ][ mime ]
            
        
    
    def GetNoneableInteger( self, name ):
        
        with self._lock:
            
            return self._dictionary[ 'noneable_integers' ][ name ]
            
        
    
    def GetNoneableString( self, name ):
        
        with self._lock:
            
            return self._dictionary[ 'noneable_strings' ][ name ]
            
        
    
    def GetPreviewShowAction( self, mime ):
        
        with self._lock:
            
            ( media_show_action, media_start_paused, media_start_with_embed, preview_show_action, preview_start_paused, preview_start_with_embed, zoom_info ) = self._GetMediaViewOptions( mime )
            
            ( possible_show_actions, can_start_paused, can_start_with_embed ) = CC.media_viewer_capabilities[ mime ]
            
            if preview_show_action not in possible_show_actions:
                
                return ( CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON, False, False )
                
            
            return ( preview_show_action, preview_start_paused, preview_start_with_embed )
            
        
    
    def GetRecentPredicates( self, predicate_types ):
        
        with self._lock:
            
            result = []
            
            predicate_types_to_recent_predicates = self._dictionary[ 'predicate_types_to_recent_predicates' ]
            
            for predicate_type in predicate_types:
                
                if predicate_type in predicate_types_to_recent_predicates:
                    
                    result.extend( predicate_types_to_recent_predicates[ predicate_type ] )
                    
                
            
            return result
            
        
    
    def GetSimpleDownloaderFormulae( self ):
        
        with self._lock:
            
            return self._dictionary[ 'simple_downloader_formulae' ]
            
        
    
    def GetString( self, name ):
        
        with self._lock:
            
            return self._dictionary[ 'strings' ][ name ]
            
        
    
    def GetStringList( self, name ):
        
        with self._lock:
            
            return self._dictionary[ 'string_list' ][ name ]
            
        
    
    def GetSuggestedTagsFavourites( self, service_key ):
        
        with self._lock:
            
            service_key_hex = service_key.hex()
            
            stf = self._dictionary[ 'suggested_tags' ][ 'favourites' ]
            
            if service_key_hex in stf:
                
                return set( stf[ service_key_hex ] )
                
            else:
                
                return set()
                
            
        
    
    def GetTagSummaryGenerator( self, name ):
        
        with self._lock:
            
            return self._dictionary[ 'tag_summary_generators' ][ name ]
            
        
    
    def InvertBoolean( self, name ):
        
        with self._lock:
            
            self._dictionary[ 'booleans' ][ name ] = not self._dictionary[ 'booleans' ][ name ]
            
        
    
    def PushRecentPredicates( self, predicates ):
        
        with self._lock:
            
            predicate_types_to_recent_predicates = self._dictionary[ 'predicate_types_to_recent_predicates' ]
            
            for predicate in predicates:
                
                predicate_type = predicate.GetType()
                
                if predicate_type not in predicate_types_to_recent_predicates:
                    
                    predicate_types_to_recent_predicates[ predicate_type ] = HydrusSerialisable.SerialisableList()
                    
                
                recent_predicates = predicate_types_to_recent_predicates[ predicate_type ]
                
                if predicate in recent_predicates:
                    
                    recent_predicates.remove( predicate )
                    
                
                recent_predicates.insert( 0, predicate )
                
                while len( recent_predicates ) > 5:
                    
                    recent_predicates.pop( 5 )
                    
                
            
        
    
    def SetBoolean( self, name, value ):
        
        with self._lock:
            
            self._dictionary[ 'booleans' ][ name ] = value
            
        
    
    def SetDefaultCollect( self, media_collect ):
        
        with self._lock:
            
            self._dictionary[ 'default_collect' ] = media_collect
            
        
    
    def SetColour( self, colour_type, colourset, colour ):
        
        with self._lock:
            
            if isinstance( colour, QG.QColor ):
                
                c = colour
                
                ( r, g, b ) = ( c.red(), c.green(), c.blue() )
                
            else:
                
                ( r, g, b ) = colour
                
            
            self._dictionary[ 'colours' ][ colourset ][ colour_type ] = ( r, g, b )
            
        
    
    def SetCustomDefaultSystemPredicates( self, predicate_type = None, predicates = None, comparable_predicates = None ):
        
        with self._lock:
            
            custom_default_predicates = self._dictionary[ 'custom_default_predicates' ]
            
            if predicate_type is not None and predicates is not None:
                
                new_custom_default_predicates = HydrusSerialisable.SerialisableList( [ pred for pred in custom_default_predicates if pred.GetType() != predicate_type ] )
                
                new_custom_default_predicates.extend( predicates )
                
                self._dictionary[ 'custom_default_predicates' ] = new_custom_default_predicates
                
                return
                
            
            if comparable_predicates is not None:
                
                new_custom_default_predicates = HydrusSerialisable.SerialisableList()
                
                for pred in custom_default_predicates:
                    
                    if True not in ( pred.IsUIEditable( comparable_predicate ) for comparable_predicate in comparable_predicates ):
                        
                        new_custom_default_predicates.append( pred )
                        
                    
                
                new_custom_default_predicates.extend( comparable_predicates )
                
                self._dictionary[ 'custom_default_predicates' ] = new_custom_default_predicates
                
                return
                
            
        
    
    def SetDefaultFileImportOptions( self, options_type, file_import_options ):
        
        with self._lock:
            
            self._dictionary[ 'default_file_import_options' ][ options_type ] = file_import_options
            
        
    
    def SetDefaultSort( self, media_sort ):
        
        with self._lock:
            
            self._dictionary[ 'default_sort' ] = media_sort
            
        
    
    def SetDefaultSubscriptionCheckerOptions( self, checker_options ):
        
        with self._lock:
            
            self._dictionary[ 'misc' ][ 'default_subscription_checker_options' ] = checker_options
            
        
    
    def SetDefaultNamespaceSorts( self, namespace_sorts ):
        
        with self._lock:
            
            default_namespace_sorts = HydrusSerialisable.SerialisableList()
            
            for namespace_sort in namespace_sorts:
                
                default_namespace_sorts.append( namespace_sort )
                
            
            self._dictionary[ 'default_namespace_sorts' ] = default_namespace_sorts
            
        
    
    def SetDefaultTagSort( self, tag_sort ):
        
        with self._lock:
            
            self._dictionary[ 'default_tag_sort' ] = tag_sort
            
        
    
    def SetDefaultWatcherCheckerOptions( self, checker_options ):
        
        with self._lock:
            
            self._dictionary[ 'misc' ][ 'default_thread_watcher_options' ] = checker_options
            
        
    
    def SetDuplicateActionOptions( self, duplicate_type, duplicate_action_options ):
        
        with self._lock:
            
            self._dictionary[ 'duplicate_action_options' ][ duplicate_type ] = duplicate_action_options
            
        
    
    def SetFallbackSort( self, media_sort ):
        
        with self._lock:
            
            self._dictionary[ 'fallback_sort' ] = media_sort
            
        
    
    def SetFavouriteTagFilters( self, names_to_tag_filters ):
        
        with self._lock:
            
            self._dictionary[ 'favourite_tag_filters' ] = HydrusSerialisable.SerialisableDictionary( names_to_tag_filters )
            
        
    
    def SetFrameLocation( self, frame_key, remember_size, remember_position, last_size, last_position, default_gravity, default_position, maximised, fullscreen ):
        
        with self._lock:
            
            self._dictionary[ 'frame_locations' ][ frame_key ] = ( remember_size, remember_position, last_size, last_position, default_gravity, default_position, maximised, fullscreen )
            
        
    
    def SetInteger( self, name, value ):
        
        with self._lock:
            
            self._dictionary[ 'integers' ][ name ] = value
            
        
    
    def SetKey( self, name, value ):
        
        with self._lock:
            
            self._dictionary[ 'keys' ][ name ] = value.hex()
            
        
    
    def SetKeyList( self, name, value ):
        
        with self._lock:
            
            self._dictionary[ 'key_list' ][ name ] = [ key.hex() for key in value ]
            
        
    
    def SetMediaViewOptions( self, mimes_to_media_view_options ):
        
        with self._lock:
            
            self._dictionary[ 'media_view' ] = HydrusSerialisable.SerialisableDictionary( mimes_to_media_view_options )
            
        
    
    def SetMediaZooms( self, zooms ):
        
        with self._lock:
            
            self._dictionary[ 'media_zooms' ] = zooms
            
        
    
    def SetMimeLaunch( self, mime, launch_path ):
        
        with self._lock:
            
            self._dictionary[ 'media_launch' ][ mime ] = launch_path
            
        
    
    def SetNoneableInteger( self, name, value ):
        
        with self._lock:
            
            self._dictionary[ 'noneable_integers' ][ name ] = value
            
        
    
    def SetNoneableString( self, name, value ):
        
        with self._lock:
            
            self._dictionary[ 'noneable_strings' ][ name ] = value
            
        
    
    def SetSimpleDownloaderFormulae( self, simple_downloader_formulae ):
        
        with self._lock:
            
            self._dictionary[ 'simple_downloader_formulae' ] = HydrusSerialisable.SerialisableList( simple_downloader_formulae )
            
        
    
    def SetString( self, name, value ):
        
        with self._lock:
            
            it_changed = False
            
            if value is not None and value != '':
                
                if self._dictionary[ 'strings' ][ name ] != value:
                    
                    self._dictionary[ 'strings' ][ name ] = value
                    
                    it_changed = True
                    
                
            
        
    
    def SetStringList( self, name, value ):
        
        with self._lock:
            
            self._dictionary[ 'string_list' ][ name ] = list( value )
            
        
    
    def SetSuggestedTagsFavourites( self, service_key, tags ):
        
        with self._lock:
            
            service_key_hex = service_key.hex()
            
            self._dictionary[ 'suggested_tags' ][ 'favourites' ][ service_key_hex ] = list( tags )
            
        
    
    def SetTagSummaryGenerator( self, name, tag_summary_generator ):
        
        with self._lock:
            
            self._dictionary[ 'tag_summary_generators' ][ name ] = tag_summary_generator
            
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_CLIENT_OPTIONS ] = ClientOptions
