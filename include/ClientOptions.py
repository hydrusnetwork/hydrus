from . import ClientConstants as CC
from . import ClientDefaults
from . import ClientDownloading
from . import ClientDuplicates
from . import ClientImporting
from . import HydrusConstants as HC
from . import HydrusGlobals as HG
from . import HydrusData
from . import HydrusPaths
from . import HydrusSerialisable
from . import HydrusTags
import os
import threading
import wx

class ClientOptions( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_CLIENT_OPTIONS
    SERIALISABLE_NAME = 'Client Options'
    SERIALISABLE_VERSION = 3
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._dictionary = HydrusSerialisable.SerialisableDictionary()
        
        self._lock = threading.Lock()
        
        self._InitialiseDefaults()
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_info = self._dictionary.GetSerialisableTuple()
        
        return serialisable_info
        
    
    def _InitialiseDefaults( self ):
        
        self._dictionary[ 'booleans' ] = {}
        
        self._dictionary[ 'booleans' ][ 'advanced_mode' ] = False
        
        self._dictionary[ 'booleans' ][ 'always_show_hover_windows' ] = False
        
        self._dictionary[ 'booleans' ][ 'apply_all_parents_to_all_services' ] = False
        self._dictionary[ 'booleans' ][ 'apply_all_siblings_to_all_services' ] = False
        self._dictionary[ 'booleans' ][ 'filter_inbox_and_archive_predicates' ] = False
        
        self._dictionary[ 'booleans' ][ 'discord_dnd_fix' ] = False
        self._dictionary[ 'booleans' ][ 'secret_discord_dnd_fix' ] = False
        
        self._dictionary[ 'booleans' ][ 'disable_cv_for_gifs' ] = False
        
        self._dictionary[ 'booleans' ][ 'set_search_focus_on_page_change' ] = False
        
        self._dictionary[ 'booleans' ][ 'allow_remove_on_manage_tags_input' ] = True
        self._dictionary[ 'booleans' ][ 'add_parents_on_manage_tags' ] = True
        self._dictionary[ 'booleans' ][ 'replace_siblings_on_manage_tags' ] = True
        self._dictionary[ 'booleans' ][ 'yes_no_on_remove_on_manage_tags' ] = True
        
        self._dictionary[ 'booleans' ][ 'show_related_tags' ] = False
        self._dictionary[ 'booleans' ][ 'show_file_lookup_script_tags' ] = False
        self._dictionary[ 'booleans' ][ 'hide_message_manager_on_gui_iconise' ] = HC.PLATFORM_OSX
        self._dictionary[ 'booleans' ][ 'hide_message_manager_on_gui_deactive' ] = False
        
        self._dictionary[ 'booleans' ][ 'load_images_with_pil' ] = False
        
        self._dictionary[ 'booleans' ][ 'use_system_ffmpeg' ] = False
        
        self._dictionary[ 'booleans' ][ 'maintain_similar_files_duplicate_pairs_during_idle' ] = False
        
        self._dictionary[ 'booleans' ][ 'show_namespaces' ] = True
        
        self._dictionary[ 'booleans' ][ 'verify_regular_https' ] = True
        
        self._dictionary[ 'booleans' ][ 'reverse_page_shift_drag_behaviour' ] = False
        
        self._dictionary[ 'booleans' ][ 'anchor_and_hide_canvas_drags' ] = HC.PLATFORM_WINDOWS
        self._dictionary[ 'booleans' ][ 'touchscreen_canvas_drags_unanchor' ] = False
        
        self._dictionary[ 'booleans' ][ 'thumbnail_fill' ] = False
        
        self._dictionary[ 'booleans' ][ 'import_page_progress_display' ] = True
        
        self._dictionary[ 'booleans' ][ 'process_subs_in_random_order' ] = True
        
        self._dictionary[ 'booleans' ][ 'ac_select_first_with_count' ] = False
        
        self._dictionary[ 'booleans' ][ 'saving_sash_positions_on_exit' ] = True
        
        self._dictionary[ 'booleans' ][ 'file_maintenance_on_shutdown' ] = True
        self._dictionary[ 'booleans' ][ 'file_maintenance_during_idle' ] = True
        
        self._dictionary[ 'booleans' ][ 'file_maintenance_throttle_enable' ] = True
        
        self._dictionary[ 'booleans' ][ 'save_page_sort_on_change' ] = False
        
        self._dictionary[ 'booleans' ][ 'pause_all_new_network_traffic' ] = False
        self._dictionary[ 'booleans' ][ 'pause_all_file_queues' ] = False
        self._dictionary[ 'booleans' ][ 'pause_all_watcher_checkers' ] = False
        self._dictionary[ 'booleans' ][ 'pause_all_gallery_searches' ] = False
        
        self._dictionary[ 'booleans' ][ 'notebook_tabs_on_left' ] = False
        
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
        
        self._dictionary[ 'booleans' ][ 'file_system_waits_on_wakeup' ] = False
        
        self._dictionary[ 'booleans' ][ 'always_show_system_everything' ] = False
        
        self._dictionary[ 'booleans' ][ 'watch_clipboard_for_watcher_urls' ] = False
        self._dictionary[ 'booleans' ][ 'watch_clipboard_for_other_recognised_urls' ] = False
        
        self._dictionary[ 'booleans' ][ 'autocomplete_results_fetch_automatically' ] = True
        
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
        self._dictionary[ 'colours' ][ 'darkmode' ][ CC.COLOUR_TAGS_BOX ] = ( 0, 0, 0 )
        
        #
        
        self._dictionary[ 'duplicate_action_options' ] = HydrusSerialisable.SerialisableDictionary()
        
        from . import ClientTags
        
        self._dictionary[ 'duplicate_action_options' ][ HC.DUPLICATE_BETTER ] = ClientDuplicates.DuplicateActionOptions( [ ( CC.LOCAL_TAG_SERVICE_KEY, HC.CONTENT_MERGE_ACTION_MOVE, ClientTags.TagFilter() ) ], [], sync_archive = True, sync_urls_action = HC.CONTENT_MERGE_ACTION_COPY )
        self._dictionary[ 'duplicate_action_options' ][ HC.DUPLICATE_SAME_QUALITY ] = ClientDuplicates.DuplicateActionOptions( [ ( CC.LOCAL_TAG_SERVICE_KEY, HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE, ClientTags.TagFilter() ) ], [], sync_archive = True, sync_urls_action = HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE )
        self._dictionary[ 'duplicate_action_options' ][ HC.DUPLICATE_ALTERNATE ] = ClientDuplicates.DuplicateActionOptions()
        
        #
        
        self._dictionary[ 'integers' ] = {}
        
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
        
        self._dictionary[ 'integers' ][ 'thumbnail_visibility_scroll_percent' ] = 75
        
        self._dictionary[ 'integers' ][ 'total_pages_warning' ] = 165
        
        self._dictionary[ 'integers' ][ 'last_session_save_period_minutes' ] = 5
        
        self._dictionary[ 'integers' ][ 'shutdown_work_period' ] = 86400
        
        self._dictionary[ 'integers' ][ 'max_network_jobs' ] = 15
        self._dictionary[ 'integers' ][ 'max_network_jobs_per_domain' ] = 3
        
        self._dictionary[ 'integers' ][ 'max_simultaneous_subscriptions' ] = 1
        
        self._dictionary[ 'integers' ][ 'gallery_page_wait_period_pages' ] = 15
        self._dictionary[ 'integers' ][ 'gallery_page_wait_period_subscriptions' ] = 5
        self._dictionary[ 'integers' ][ 'watcher_page_wait_period' ] = 5
        
        self._dictionary[ 'integers' ][ 'popup_message_character_width' ] = 56
        
        self._dictionary[ 'integers' ][ 'video_thumbnail_percentage_in' ] = 35
        
        self._dictionary[ 'integers' ][ 'duplicate_comparison_score_higher_jpeg_quality' ] = 10
        self._dictionary[ 'integers' ][ 'duplicate_comparison_score_much_higher_jpeg_quality' ] = 20
        self._dictionary[ 'integers' ][ 'duplicate_comparison_score_higher_filesize' ] = 10
        self._dictionary[ 'integers' ][ 'duplicate_comparison_score_much_higher_filesize' ] = 20
        self._dictionary[ 'integers' ][ 'duplicate_comparison_score_higher_resolution' ] = 20
        self._dictionary[ 'integers' ][ 'duplicate_comparison_score_much_higher_resolution' ] = 50
        self._dictionary[ 'integers' ][ 'duplicate_comparison_score_more_tags' ] = 8
        self._dictionary[ 'integers' ][ 'duplicate_comparison_score_older' ] = 4
        
        self._dictionary[ 'integers' ][ 'thumbnail_cache_timeout' ] = 86400
        self._dictionary[ 'integers' ][ 'image_cache_timeout' ] = 600
        
        self._dictionary[ 'integers' ][ 'thumbnail_border' ] = 1
        self._dictionary[ 'integers' ][ 'thumbnail_margin' ] = 2
        
        self._dictionary[ 'integers' ][ 'file_maintenance_throttle_files' ] = 200
        self._dictionary[ 'integers' ][ 'file_maintenance_throttle_time_delta' ] = 86400
        
        self._dictionary[ 'integers' ][ 'subscription_network_error_delay' ] = 12 * 3600
        self._dictionary[ 'integers' ][ 'subscription_other_error_delay' ] = 36 * 3600
        self._dictionary[ 'integers' ][ 'downloader_network_error_delay' ] = 90 * 60
        
        self._dictionary[ 'integers' ][ 'file_viewing_stats_menu_display' ] = CC.FILE_VIEWING_STATS_MENU_DISPLAY_MEDIA_AND_PREVIEW_IN_SUBMENU
        
        self._dictionary[ 'integers' ][ 'number_of_gui_session_backups' ] = 10
        
        #
        
        self._dictionary[ 'keys' ] = {}
        
        self._dictionary[ 'keys' ][ 'default_tag_service_search_page' ] = CC.COMBINED_TAG_SERVICE_KEY.hex()
        self._dictionary[ 'keys' ][ 'default_gug_key' ] = HydrusData.GenerateKey().hex()
        
        self._dictionary[ 'key_list' ] = {}
        
        self._dictionary[ 'key_list' ][ 'default_neighbouring_txt_tag_service_keys' ] = []
        
        #
        
        self._dictionary[ 'noneable_integers' ] = {}
        
        self._dictionary[ 'noneable_integers' ][ 'forced_search_limit' ] = None
        
        self._dictionary[ 'noneable_integers' ][ 'disk_cache_maintenance_mb' ] = 256
        self._dictionary[ 'noneable_integers' ][ 'disk_cache_init_period' ] = 4
        
        self._dictionary[ 'noneable_integers' ][ 'num_recent_tags' ] = 20
        
        self._dictionary[ 'noneable_integers' ][ 'maintenance_vacuum_period_days' ] = 30
        
        self._dictionary[ 'noneable_integers' ][ 'duplicate_background_switch_intensity' ] = 3
        
        self._dictionary[ 'noneable_integers' ][ 'last_review_bandwidth_search_distance' ] = 7 * 86400
        
        self._dictionary[ 'noneable_integers' ][ 'file_viewing_statistics_media_min_time' ] = 2
        self._dictionary[ 'noneable_integers' ][ 'file_viewing_statistics_media_max_time' ] = 600
        self._dictionary[ 'noneable_integers' ][ 'file_viewing_statistics_preview_min_time' ] = 5
        self._dictionary[ 'noneable_integers' ][ 'file_viewing_statistics_preview_max_time' ] = 60
        
        self._dictionary[ 'noneable_integers' ][ 'autocomplete_exact_match_threshold' ] = 2
        
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
        
        self._dictionary[ 'strings' ] = {}
        
        self._dictionary[ 'strings' ][ 'main_gui_title' ] = 'hydrus client'
        self._dictionary[ 'strings' ][ 'namespace_connector' ] = ':'
        self._dictionary[ 'strings' ][ 'export_phrase' ] = '{hash}'
        self._dictionary[ 'strings' ][ 'current_colourset' ] = 'default'
        self._dictionary[ 'strings' ][ 'favourite_simple_downloader_formula' ] = 'all files linked by images in page'
        self._dictionary[ 'strings' ][ 'thumbnail_scroll_rate' ] = '1.0'
        self._dictionary[ 'strings' ][ 'pause_character' ] = '\u23F8'
        self._dictionary[ 'strings' ][ 'stop_character' ] = '\u23F9'
        self._dictionary[ 'strings' ][ 'default_gug_name' ] = 'safebooru tag search'
        
        self._dictionary[ 'string_list' ] = {}
        
        self._dictionary[ 'string_list' ][ 'default_media_viewer_custom_shortcuts' ] = []
        self._dictionary[ 'string_list' ][ 'favourite_tags' ] = []
        self._dictionary[ 'string_list' ][ 'advanced_file_deletion_reasons' ] = [ 'I do not like it.', 'It is bad quality.', 'It is not appropriate for this client.', 'Temporary delete--I want to bring it back later.' ]
        
        #
        
        self._dictionary[ 'tag_summary_generators' ] = HydrusSerialisable.SerialisableDictionary()
        
        namespace_info = []
        
        namespace_info.append( ( 'creator', '', ', ' ) )
        namespace_info.append( ( 'series', '', ', ' ) )
        namespace_info.append( ( 'title', '', ', ' ) )
        
        separator = ' - '
        
        # the cleantags here converts to unicode, which is important!
        
        example_tags = HydrusTags.CleanTags( [ 'creator:creator', 'series:series', 'title:title' ] )
        
        from . import ClientGUITags
        
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
        allow_decompression_bombs = False
        min_size = None
        max_size = None
        max_gif_size = 32 * 1048576
        min_resolution = None
        max_resolution = None
        
        automatic_archive = False
        associate_source_urls = True
        
        present_new_files = True
        present_already_in_inbox_files = False
        present_already_in_archive_files = False
        
        from . import ClientImportOptions
        
        quiet_file_import_options = ClientImportOptions.FileImportOptions()
        
        quiet_file_import_options.SetPreImportOptions( exclude_deleted, do_not_check_known_urls_before_importing, do_not_check_hashes_before_importing, allow_decompression_bombs, min_size, max_size, max_gif_size, min_resolution, max_resolution )
        quiet_file_import_options.SetPostImportOptions( automatic_archive, associate_source_urls )
        quiet_file_import_options.SetPresentationOptions( present_new_files, present_already_in_inbox_files, present_already_in_archive_files )
        
        self._dictionary[ 'default_file_import_options' ][ 'quiet' ] = quiet_file_import_options
        
        present_new_files = True
        present_already_in_inbox_files = True
        present_already_in_archive_files = True
        
        loud_file_import_options = ClientImportOptions.FileImportOptions()
        
        loud_file_import_options.SetPreImportOptions( exclude_deleted, do_not_check_known_urls_before_importing, do_not_check_hashes_before_importing, allow_decompression_bombs, min_size, max_size, max_gif_size, min_resolution, max_resolution )
        loud_file_import_options.SetPostImportOptions( automatic_archive, associate_source_urls )
        loud_file_import_options.SetPresentationOptions( present_new_files, present_already_in_inbox_files, present_already_in_archive_files )
        
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
        
        self._dictionary[ 'media_view' ] = HydrusSerialisable.SerialisableDictionary() # integer keys, so got to be cleverer dict
        
        # media_show_action, preview_show_action, ( media_scale_up, media_scale_down, preview_scale_up, preview_scale_down, exact_zooms_only, scale_up_quality, scale_down_quality ) )
        
        image_zoom_info = ( CC.MEDIA_VIEWER_SCALE_TO_CANVAS, CC.MEDIA_VIEWER_SCALE_TO_CANVAS, CC.MEDIA_VIEWER_SCALE_TO_CANVAS, CC.MEDIA_VIEWER_SCALE_TO_CANVAS, False, CC.ZOOM_LANCZOS4, CC.ZOOM_AREA )
        gif_zoom_info = ( CC.MEDIA_VIEWER_SCALE_MAX_REGULAR, CC.MEDIA_VIEWER_SCALE_MAX_REGULAR, CC.MEDIA_VIEWER_SCALE_TO_CANVAS, CC.MEDIA_VIEWER_SCALE_TO_CANVAS, True, CC.ZOOM_LANCZOS4, CC.ZOOM_AREA )
        flash_zoom_info = ( CC.MEDIA_VIEWER_SCALE_TO_CANVAS, CC.MEDIA_VIEWER_SCALE_TO_CANVAS, CC.MEDIA_VIEWER_SCALE_TO_CANVAS, CC.MEDIA_VIEWER_SCALE_TO_CANVAS, False, CC.ZOOM_LINEAR, CC.ZOOM_LINEAR )
        video_zoom_info = ( CC.MEDIA_VIEWER_SCALE_100, CC.MEDIA_VIEWER_SCALE_MAX_REGULAR, CC.MEDIA_VIEWER_SCALE_TO_CANVAS, CC.MEDIA_VIEWER_SCALE_TO_CANVAS, True, CC.ZOOM_LANCZOS4, CC.ZOOM_AREA )
        null_zoom_info = ( CC.MEDIA_VIEWER_SCALE_100, CC.MEDIA_VIEWER_SCALE_100, CC.MEDIA_VIEWER_SCALE_100, CC.MEDIA_VIEWER_SCALE_100, False, CC.ZOOM_LINEAR, CC.ZOOM_LINEAR )
        
        self._dictionary[ 'media_view' ][ HC.IMAGE_JPEG ] = ( CC.MEDIA_VIEWER_ACTION_SHOW_AS_NORMAL, CC.MEDIA_VIEWER_ACTION_SHOW_AS_NORMAL, image_zoom_info )
        self._dictionary[ 'media_view' ][ HC.IMAGE_PNG ] = ( CC.MEDIA_VIEWER_ACTION_SHOW_AS_NORMAL, CC.MEDIA_VIEWER_ACTION_SHOW_AS_NORMAL, image_zoom_info )
        self._dictionary[ 'media_view' ][ HC.IMAGE_APNG ] = ( CC.MEDIA_VIEWER_ACTION_SHOW_AS_NORMAL, CC.MEDIA_VIEWER_ACTION_SHOW_AS_NORMAL, gif_zoom_info )
        self._dictionary[ 'media_view' ][ HC.IMAGE_GIF ] = ( CC.MEDIA_VIEWER_ACTION_SHOW_AS_NORMAL, CC.MEDIA_VIEWER_ACTION_SHOW_AS_NORMAL, gif_zoom_info )
        self._dictionary[ 'media_view' ][ HC.IMAGE_WEBP ] = ( CC.MEDIA_VIEWER_ACTION_SHOW_AS_NORMAL, CC.MEDIA_VIEWER_ACTION_SHOW_AS_NORMAL, image_zoom_info )
        self._dictionary[ 'media_view' ][ HC.IMAGE_TIFF ] = ( CC.MEDIA_VIEWER_ACTION_SHOW_AS_NORMAL, CC.MEDIA_VIEWER_ACTION_SHOW_AS_NORMAL, image_zoom_info )
        self._dictionary[ 'media_view' ][ HC.IMAGE_ICON ] = ( CC.MEDIA_VIEWER_ACTION_SHOW_AS_NORMAL, CC.MEDIA_VIEWER_ACTION_SHOW_AS_NORMAL, image_zoom_info )
        
        if HC.PLATFORM_WINDOWS:
            
            self._dictionary[ 'media_view' ][ HC.APPLICATION_FLASH ] = ( CC.MEDIA_VIEWER_ACTION_SHOW_BEHIND_EMBED, CC.MEDIA_VIEWER_ACTION_SHOW_BEHIND_EMBED, flash_zoom_info )
            
        else:
            
            self._dictionary[ 'media_view' ][ HC.APPLICATION_FLASH ] = ( CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON, CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON, null_zoom_info )
            
        
        self._dictionary[ 'media_view' ][ HC.APPLICATION_PDF ] = ( CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON, CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON, null_zoom_info )
        self._dictionary[ 'media_view' ][ HC.APPLICATION_PSD ] = ( CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON, CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON, null_zoom_info )
        self._dictionary[ 'media_view' ][ HC.APPLICATION_ZIP ] = ( CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON, CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON, null_zoom_info )
        self._dictionary[ 'media_view' ][ HC.APPLICATION_7Z ] = ( CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON, CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON, null_zoom_info )
        self._dictionary[ 'media_view' ][ HC.APPLICATION_RAR ] = ( CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON, CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON, null_zoom_info )
        self._dictionary[ 'media_view' ][ HC.APPLICATION_HYDRUS_UPDATE_CONTENT ] = ( CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW, CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW, null_zoom_info )
        self._dictionary[ 'media_view' ][ HC.APPLICATION_HYDRUS_UPDATE_DEFINITIONS ] = ( CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW, CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW, null_zoom_info )
        
        self._dictionary[ 'media_view' ][ HC.VIDEO_AVI ] = ( CC.MEDIA_VIEWER_ACTION_SHOW_AS_NORMAL, CC.MEDIA_VIEWER_ACTION_SHOW_AS_NORMAL, video_zoom_info )
        self._dictionary[ 'media_view' ][ HC.VIDEO_FLV ] = ( CC.MEDIA_VIEWER_ACTION_SHOW_AS_NORMAL, CC.MEDIA_VIEWER_ACTION_SHOW_AS_NORMAL, video_zoom_info )
        self._dictionary[ 'media_view' ][ HC.VIDEO_MOV ] = ( CC.MEDIA_VIEWER_ACTION_SHOW_AS_NORMAL, CC.MEDIA_VIEWER_ACTION_SHOW_AS_NORMAL, video_zoom_info )
        self._dictionary[ 'media_view' ][ HC.VIDEO_MP4 ] = ( CC.MEDIA_VIEWER_ACTION_SHOW_AS_NORMAL, CC.MEDIA_VIEWER_ACTION_SHOW_AS_NORMAL, video_zoom_info )
        self._dictionary[ 'media_view' ][ HC.VIDEO_MPEG ] = ( CC.MEDIA_VIEWER_ACTION_SHOW_AS_NORMAL, CC.MEDIA_VIEWER_ACTION_SHOW_AS_NORMAL, video_zoom_info )
        self._dictionary[ 'media_view' ][ HC.VIDEO_MKV ] = ( CC.MEDIA_VIEWER_ACTION_SHOW_AS_NORMAL, CC.MEDIA_VIEWER_ACTION_SHOW_AS_NORMAL, video_zoom_info )
        self._dictionary[ 'media_view' ][ HC.VIDEO_WEBM ] = ( CC.MEDIA_VIEWER_ACTION_SHOW_AS_NORMAL, CC.MEDIA_VIEWER_ACTION_SHOW_AS_NORMAL, video_zoom_info )
        self._dictionary[ 'media_view' ][ HC.VIDEO_WMV ] = ( CC.MEDIA_VIEWER_ACTION_SHOW_AS_NORMAL, CC.MEDIA_VIEWER_ACTION_SHOW_AS_NORMAL, video_zoom_info )
        self._dictionary[ 'media_view' ][ HC.AUDIO_MP3 ] = ( CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON, CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON, null_zoom_info )
        self._dictionary[ 'media_view' ][ HC.AUDIO_OGG ] = ( CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON, CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON, null_zoom_info )
        self._dictionary[ 'media_view' ][ HC.AUDIO_FLAC ] = ( CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON, CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON, null_zoom_info )
        self._dictionary[ 'media_view' ][ HC.AUDIO_WMA ] = ( CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON, CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON, null_zoom_info )
        
        self._dictionary[ 'media_zooms' ] = [ 0.01, 0.05, 0.1, 0.15, 0.2, 0.3, 0.5, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.5, 2.0, 3.0, 5.0, 10.0, 20.0 ]
        
        #
        
        self._dictionary[ 'misc' ] = HydrusSerialisable.SerialisableDictionary()
        
        self._dictionary[ 'misc' ][ 'default_thread_watcher_options' ] = ClientDefaults.GetDefaultCheckerOptions( 'thread' )
        self._dictionary[ 'misc' ][ 'default_subscription_checker_options' ] = ClientDefaults.GetDefaultCheckerOptions( 'artist subscription' )
        
        #
        
        self._dictionary[ 'suggested_tags' ] = HydrusSerialisable.SerialisableDictionary()
        
        self._dictionary[ 'suggested_tags' ][ 'favourites' ] = {}
        
        #
        
        from . import ClientMedia
        
        self._dictionary[ 'default_sort' ] = ClientMedia.MediaSort( ( 'system', CC.SORT_FILES_BY_FILESIZE ), CC.SORT_ASC )
        self._dictionary[ 'fallback_sort' ] = ClientMedia.MediaSort( ( 'system', CC.SORT_FILES_BY_IMPORT_TIME ), CC.SORT_ASC )
        
    
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
            
        
    
    def FlipBoolean( self, name ):
        
        with self._lock:
            
            self._dictionary[ 'booleans' ][ name ] = not self._dictionary[ 'booleans' ][ name ]
            
        
    
    def GetBoolean( self, name ):
        
        with self._lock:
            
            return self._dictionary[ 'booleans' ][ name ]
            
        
    
    def GetColour( self, colour_type, colourset = None ):
        
        with self._lock:
            
            if colourset is None:
                
                colourset = self._dictionary[ 'strings' ][ 'current_colourset' ]
                
            
            ( r, g, b ) = self._dictionary[ 'colours' ][ colourset ][ colour_type ]
            
            return wx.Colour( r, g, b )
            
        
    
    def GetDefaultFileImportOptions( self, options_type ):
        
        with self._lock:
            
            return self._dictionary[ 'default_file_import_options' ][ options_type ]
            
        
    
    def GetDefaultWatcherCheckerOptions( self ):
        
        with self._lock:
            
            return self._dictionary[ 'misc' ][ 'default_thread_watcher_options' ]
            
        
    
    def GetDefaultSort( self ):
        
        with self._lock:
            
            return self._dictionary[ 'default_sort' ]
            
        
    
    def GetDefaultSubscriptionCheckerOptions( self ):
        
        with self._lock:
            
            return self._dictionary[ 'misc' ][ 'default_subscription_checker_options' ]
            
        
    
    def GetDuplicateActionOptions( self, duplicate_type ):
        
        with self._lock:
            
            if duplicate_type in self._dictionary[ 'duplicate_action_options' ]:
                
                return self._dictionary[ 'duplicate_action_options' ][ duplicate_type ]
                
            else:
                
                return ClientDuplicates.DuplicateActionOptions( [], [] )
                
            
        
    
    def GetFallbackSort( self ):
        
        with self._lock:
            
            return self._dictionary[ 'fallback_sort' ]
            
        
    
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
            
            ( media_show_action, preview_show_action, zoom_info ) = self._dictionary[ 'media_view' ][ mime ]
            
            if media_show_action not in CC.media_viewer_capabilities[ mime ]:
                
                return CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON
                
            
            return media_show_action
            
        
    
    def GetMediaViewOptions( self, mime ):
        
        with self._lock:
            
            return self._dictionary[ 'media_view' ][ mime ]
            
        
    
    def GetMediaZoomOptions( self, mime ):
        
        with self._lock:
            
            ( media_show_action, preview_show_action, zoom_info ) = self._dictionary[ 'media_view' ][ mime ]
            
            return zoom_info
            
        
    
    def GetMediaZooms( self ):
        
        with self._lock:
            
            return list( self._dictionary[ 'media_zooms' ] )
            
        
    
    def GetMediaZoomQuality( self, mime ):
        
        with self._lock:
            
            ( media_show_action, preview_show_action, ( media_scale_up, media_scale_down, preview_scale_up, preview_scale_down, exact_zooms_only, scale_up_quality, scale_down_quality ) ) = self._dictionary[ 'media_view' ][ mime ]
            
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
            
            ( media_show_action, preview_show_action, zoom_info ) = self._dictionary[ 'media_view' ][ mime ]
            
            if preview_show_action not in CC.media_viewer_capabilities[ mime ]:
                
                return CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON
                
            
            return preview_show_action
            
        
    
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
            
        
    
    def SetBoolean( self, name, value ):
        
        with self._lock:
            
            self._dictionary[ 'booleans' ][ name ] = value
            
        
    
    def SetColour( self, colour_type, colourset, colour ):
        
        with self._lock:
            
            if isinstance( colour, wx.Colour ):
                
                ( r, g, b, a ) = colour.Get()
                
            else:
                
                ( r, g, b ) = colour
                
            
            self._dictionary[ 'colours' ][ colourset ][ colour_type ] = ( r, g, b )
            
        
    
    def SetDefaultWatcherCheckerOptions( self, checker_options ):
        
        with self._lock:
            
            self._dictionary[ 'misc' ][ 'default_thread_watcher_options' ] = checker_options
            
        
    
    def SetDefaultSort( self, media_sort ):
        
        with self._lock:
            
            self._dictionary[ 'default_sort' ] = media_sort
            
        
    
    def SetDefaultSubscriptionCheckerOptions( self, checker_options ):
        
        with self._lock:
            
            self._dictionary[ 'misc' ][ 'default_subscription_checker_options' ] = checker_options
            
        
    
    def SetDuplicateActionOptions( self, duplicate_type, duplicate_action_options ):
        
        with self._lock:
            
            self._dictionary[ 'duplicate_action_options' ][ duplicate_type ] = duplicate_action_options
            
        
    
    def SetFallbackSort( self, media_sort ):
        
        with self._lock:
            
            self._dictionary[ 'fallback_sort' ] = media_sort
            
        
    
    def SetDefaultFileImportOptions( self, options_type, file_import_options ):
        
        with self._lock:
            
            self._dictionary[ 'default_file_import_options' ][ options_type ] = file_import_options
            
        
    
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
            
        
    
    def SetMediaViewOptions( self, mime, value_tuple ):
        
        with self._lock:
            
            self._dictionary[ 'media_view' ][ mime ] = value_tuple
            
        
    
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
