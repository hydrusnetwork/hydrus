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
from hydrus.client import ClientGlobals as CG
from hydrus.client.duplicates import ClientDuplicates
from hydrus.client.importing.options import FileImportOptions

class ClientOptions( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_CLIENT_OPTIONS
    SERIALISABLE_NAME = 'Client Options'
    SERIALISABLE_VERSION = 6
    
    def __init__( self ):
        
        super().__init__()
        
        self._dictionary = HydrusSerialisable.SerialisableDictionary()
        
        self._lock = threading.Lock()
        
        self._InitialiseDefaults()
        
    
    def _GetDefaultMediaViewOptions( self ):
        
        media_view = HydrusSerialisable.SerialisableDictionary() # integer keys, so got to be cleverer dict
        
        # media_show_action, media_start_paused, media_start_with_embed, preview_show_action, preview_start_paused, preview_start_with_embed, ( media_scale_up, media_scale_down, preview_scale_up, preview_scale_down, exact_zooms_only, scale_up_quality, scale_down_quality ) )
        
        from hydrus.client.gui.canvas import ClientGUIMPV
        
        # we may permit mpv testing in macOS, but we won't default to it even if it seems ok
        if ClientGUIMPV.MPV_IS_AVAILABLE and not HC.PLATFORM_MACOS:
            
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
        
        media_view[ HC.GENERAL_APPLICATION_ARCHIVE ] = ( CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON, media_start_paused, media_start_with_embed, CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON, preview_start_paused, preview_start_with_embed, null_zoom_info )
        
        media_view[ HC.GENERAL_IMAGE_PROJECT ] = ( CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON, media_start_paused, media_start_with_embed, CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON, preview_start_paused, preview_start_with_embed, null_zoom_info )
        
        media_view[ HC.APPLICATION_PSD ] = ( CC.MEDIA_VIEWER_ACTION_SHOW_WITH_NATIVE, media_start_paused, media_start_with_embed, CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON, preview_start_paused, preview_start_with_embed, image_zoom_info )

        media_view[ HC.APPLICATION_KRITA ] = ( CC.MEDIA_VIEWER_ACTION_SHOW_WITH_NATIVE, media_start_paused, media_start_with_embed, CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON, preview_start_paused, preview_start_with_embed, image_zoom_info )
        
        media_view[ HC.ANIMATION_WEBP ] = ( CC.MEDIA_VIEWER_ACTION_SHOW_WITH_NATIVE, media_start_paused, media_start_with_embed, CC.MEDIA_VIEWER_ACTION_SHOW_WITH_NATIVE, preview_start_paused, preview_start_with_embed, gif_zoom_info )
        
        media_view[ HC.ANIMATION_UGOIRA ] = ( CC.MEDIA_VIEWER_ACTION_SHOW_WITH_NATIVE, media_start_paused, media_start_with_embed, CC.MEDIA_VIEWER_ACTION_SHOW_WITH_NATIVE, preview_start_paused, preview_start_with_embed, gif_zoom_info )
        
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
        
        from hydrus.client.gui.canvas import ClientGUIMPV
        
        self._dictionary[ 'booleans' ] = {
            'advanced_mode' : False,
            'remove_filtered_files_even_when_skipped' : False,
            'discord_dnd_fix' : False,
            'secret_discord_dnd_fix' : False,
            'show_unmatched_urls_in_media_viewer' : False,
            'set_search_focus_on_page_change' : False,
            'allow_remove_on_manage_tags_input' : False,
            'yes_no_on_remove_on_manage_tags' : True,
            'activate_window_on_tag_search_page_activation' : False,
            'show_related_tags' : True,
            'show_file_lookup_script_tags' : False,
            'use_native_menubar' : HC.PLATFORM_MACOS,
            'shortcuts_merge_non_number_numpad' : True,
            'disable_get_safe_position_test' : False,
            'save_window_size_and_position_on_close' : False,
            'freeze_message_manager_when_mouse_on_other_monitor' : False,
            'freeze_message_manager_when_main_gui_minimised' : False,
            'load_images_with_pil' : True,
            'only_show_delete_from_all_local_domains_when_filtering' : False,
            'use_system_ffmpeg' : False,
            'elide_page_tab_names' : True,
            'maintain_similar_files_duplicate_pairs_during_active' : False,
            'maintain_similar_files_duplicate_pairs_during_idle' : True,
            'show_namespaces' : True,
            'show_number_namespaces' : True,
            'show_subtag_number_namespaces' : True,
            'replace_tag_underscores_with_spaces' : False,
            'replace_tag_emojis_with_boxes' : False,
            'verify_regular_https' : True,
            'page_drop_chase_normally' : True,
            'page_drop_chase_with_shift' : False,
            'page_drag_change_tab_normally' : True,
            'page_drag_change_tab_with_shift' : True,
            'wheel_scrolls_tab_bar' : False,
            'remove_local_domain_moved_files' : False,
            'anchor_and_hide_canvas_drags' : HC.PLATFORM_WINDOWS,
            'touchscreen_canvas_drags_unanchor' : False,
            'import_page_progress_display' : True,
            'rename_page_of_pages_on_pick_new' : False,
            'rename_page_of_pages_on_send' : False,
            'process_subs_in_random_order' : True,
            'ac_select_first_with_count' : False,
            'saving_sash_positions_on_exit' : True,
            'database_deferred_delete_maintenance_during_idle' : True,
            'database_deferred_delete_maintenance_during_active' : True,
            'duplicates_auto_resolution_during_idle' : True,
            'duplicates_auto_resolution_during_active' : True,
            'file_maintenance_during_idle' : True,
            'file_maintenance_during_active' : True,
            'tag_display_maintenance_during_idle' : True,
            'tag_display_maintenance_during_active' : True,
            'save_page_sort_on_change' : False,
            'disable_page_tab_dnd' : False,
            'force_hide_page_signal_on_new_page' : False,
            'pause_export_folders_sync' : False,
            'pause_import_folders_sync' : False,
            'pause_repo_sync' : False,
            'pause_subs_sync' : False,
            'pause_all_new_network_traffic' : False,
            'boot_with_network_traffic_paused' : False,
            'pause_all_file_queues' : False,
            'pause_all_watcher_checkers' : False,
            'pause_all_gallery_searches' : False,
            'popup_message_force_min_width' : False,
            'always_show_iso_time' : False,
            'do_not_do_chmod_mode' : False,
            'confirm_multiple_local_file_services_move' : True,
            'confirm_multiple_local_file_services_copy' : True,
            'use_advanced_file_deletion_dialog' : False,
            'show_new_on_file_seed_short_summary' : False,
            'show_deleted_on_file_seed_short_summary' : False,
            'only_save_last_session_during_idle' : False,
            'do_human_sort_on_hdd_file_import_paths' : True,
            'highlight_new_watcher' : True,
            'highlight_new_query' : True,
            'delete_files_after_export' : False,
            'file_viewing_statistics_active' : True,
            'file_viewing_statistics_active_on_archive_delete_filter' : True,
            'file_viewing_statistics_active_on_dupe_filter' : False,
            'prefix_hash_when_copying' : False,
            'file_system_waits_on_wakeup' : False,
            'show_system_everything' : True,
            'watch_clipboard_for_watcher_urls' : False,
            'watch_clipboard_for_other_recognised_urls' : False,
            'default_search_synchronised' : True,
            'autocomplete_float_main_gui' : True,
            'global_audio_mute' : False,
            'media_viewer_audio_mute' : False,
            'media_viewer_uses_its_own_audio_volume' : False,
            'preview_audio_mute' : False,
            'preview_uses_its_own_audio_volume' : True,
            'always_loop_gifs' : True,
            'always_show_system_tray_icon' : False,
            'minimise_client_to_system_tray' : False,
            'close_client_to_system_tray' : False,
            'start_client_in_system_tray' : False,
            'use_qt_file_dialogs' : False,
            'notify_client_api_cookies' : False,
            'expand_parents_on_storage_taglists' : True,
            'expand_parents_on_storage_autocomplete_taglists' : True,
            'show_parent_decorators_on_storage_taglists' : True,
            'show_parent_decorators_on_storage_autocomplete_taglists' : True,
            'show_sibling_decorators_on_storage_taglists' : True,
            'show_sibling_decorators_on_storage_autocomplete_taglists' : True,
            'show_session_size_warnings' : True,
            'delete_lock_for_archived_files' : False,
            'delete_lock_reinbox_deletees_after_archive_delete' : False,
            'delete_lock_reinbox_deletees_after_duplicate_filter' : False,
            'delete_lock_reinbox_deletees_in_auto_resolution' : False,
            'remember_last_advanced_file_deletion_reason' : True,
            'remember_last_advanced_file_deletion_special_action' : False,
            'do_macos_debug_dialog_menus' : False,
            'save_default_tag_service_tab_on_change' : True,
            'force_animation_scanbar_show' : False,
            'call_mouse_buttons_primary_secondary' : False,
            'start_note_editing_at_end' : True,
            'draw_transparency_checkerboard_media_canvas' : False,
            'draw_transparency_checkerboard_media_canvas_duplicates' : True,
            'menu_choice_buttons_can_mouse_scroll' : True,
            'remember_options_window_panel' : True,
            'focus_preview_on_ctrl_click' : False,
            'focus_preview_on_ctrl_click_only_static' : False,
            'focus_preview_on_shift_click' : False,
            'focus_preview_on_shift_click_only_static' : False,
            'focus_media_tab_on_viewer_close_if_possible' : False,
            'fade_sibling_connector' : True,
            'use_custom_sibling_connector_colour' : False,
            'hide_uninteresting_modified_time' : True,
            'draw_tags_hover_in_media_viewer_background' : True,
            'draw_top_hover_in_media_viewer_background' : True,
            'draw_top_right_hover_in_media_viewer_background' : True,
            'draw_top_right_hover_in_preview_window_background' : True,
            'preview_window_hover_top_right_shows_popup' : True,
            'draw_notes_hover_in_media_viewer_background' : True,
            'draw_bottom_right_index_in_media_viewer_background' : True,
            'disable_tags_hover_in_media_viewer': False,
            'disable_top_right_hover_in_media_viewer': False,
            'media_viewer_window_always_on_top': False,
            'media_viewer_lock_current_zoom_type': False,
            'media_viewer_lock_current_zoom': False,
            'media_viewer_lock_current_pan': False,
            'allow_blurhash_fallback' : True,
            'fade_thumbnails' : True,
            'slideshow_always_play_duration_media_once_through' : False,
            'enable_truncated_images_pil' : True,
            'do_icc_profile_normalisation' : True,
            'mpv_available_at_start' : ClientGUIMPV.MPV_IS_AVAILABLE,
            'do_sleep_check' : True,
            'override_stylesheet_colours' : False,
            'command_palette_show_page_of_pages' : False,
            'command_palette_show_main_menu' : False,
            'command_palette_show_media_menu' : False,
            'disallow_media_drags_on_duration_media' : False,
            'show_all_my_files_on_page_chooser' : True,
            'show_all_my_files_on_page_chooser_at_top' : False,
            'show_local_files_on_page_chooser' : False,
            'show_local_files_on_page_chooser_at_top' : False,
            'use_nice_resolution_strings' : True,
            'use_listbook_for_tag_service_panels' : False,
            'open_files_to_duplicate_filter_uses_all_my_files' : True,
            'show_extended_single_file_info_in_status_bar' : True,
            'hide_duplicates_needs_work_message_when_reasonably_caught_up' : True,
            'file_info_line_consider_archived_interesting' : True,
            'file_info_line_consider_archived_time_interesting' : True,
            'file_info_line_consider_file_services_interesting' : False,
            'file_info_line_consider_file_services_import_times_interesting' : False,
            'file_info_line_consider_trash_time_interesting' : False,
            'file_info_line_consider_trash_reason_interesting' : False,
            'set_requests_ca_bundle_env' : False,
            'mpv_loop_playlist_instead_of_file' : False,
            'draw_thumbnail_rating_background' : True,
            'draw_thumbnail_numerical_ratings_collapsed_always' : False,
            'show_destination_page_when_dnd_url' : True,
            'confirm_non_empty_downloader_page_close' : True,
            'confirm_all_page_closes' : False,
            'refresh_search_page_on_system_limited_sort_changed' : True,
            'do_not_setgeometry_on_an_mpv' : False,
            'focus_media_thumb_on_viewer_close' : True,
            'skip_yesno_on_write_autocomplete_multiline_paste' : False,
            'activate_main_gui_on_viewer_close' : False,
            'activate_main_gui_on_focusing_viewer_close' : False,
            'override_bandwidth_on_file_urls_from_post_urls' : True,
            'remove_leading_url_double_slashes' : False,
            'always_apply_ntfs_export_filename_rules' : False,
            'replace_percent_twenty_with_space_in_gug_input' : False,
        }
        
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
        
        self._dictionary[ 'recent_petition_reasons' ] = HydrusSerialisable.SerialisableDictionary()
        
        #
        
        self._dictionary[ 'duplicate_action_options' ] = HydrusSerialisable.SerialisableDictionary()
        
        duplicate_content_merge_options = ClientDuplicates.DuplicateContentMergeOptions()
        
        duplicate_content_merge_options.SetTagServiceActions( [ ( CC.DEFAULT_LOCAL_TAG_SERVICE_KEY, HC.CONTENT_MERGE_ACTION_MOVE, HydrusTags.TagFilter() ), ( CC.DEFAULT_LOCAL_DOWNLOADER_TAG_SERVICE_KEY, HC.CONTENT_MERGE_ACTION_MOVE, HydrusTags.TagFilter() ) ] )
        duplicate_content_merge_options.SetRatingServiceActions( [ ( CC.DEFAULT_FAVOURITES_RATING_SERVICE_KEY, HC.CONTENT_MERGE_ACTION_MOVE ) ] )
        duplicate_content_merge_options.SetSyncArchiveAction( ClientDuplicates.SYNC_ARCHIVE_DO_BOTH_REGARDLESS )
        duplicate_content_merge_options.SetSyncURLsAction( HC.CONTENT_MERGE_ACTION_COPY )
        duplicate_content_merge_options.SetSyncFileModifiedDateAction( HC.CONTENT_MERGE_ACTION_COPY )
        duplicate_content_merge_options.SetSyncNotesAction( HC.CONTENT_MERGE_ACTION_COPY )
        
        from hydrus.client.importing.options import NoteImportOptions
        
        note_import_options = NoteImportOptions.NoteImportOptions()
        
        note_import_options.SetIsDefault( False )
        note_import_options.SetGetNotes( True )
        note_import_options.SetExtendExistingNoteIfPossible( True )
        note_import_options.SetConflictResolution( NoteImportOptions.NOTE_IMPORT_CONFLICT_RENAME )
        
        duplicate_content_merge_options.SetSyncNoteImportOptions( note_import_options )
        
        self._dictionary[ 'duplicate_action_options' ][ HC.DUPLICATE_BETTER ] = duplicate_content_merge_options
        
        duplicate_content_merge_options = ClientDuplicates.DuplicateContentMergeOptions()
        
        duplicate_content_merge_options.SetTagServiceActions( [ ( CC.DEFAULT_LOCAL_TAG_SERVICE_KEY, HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE, HydrusTags.TagFilter() ), ( CC.DEFAULT_LOCAL_DOWNLOADER_TAG_SERVICE_KEY, HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE, HydrusTags.TagFilter() ) ] )
        duplicate_content_merge_options.SetRatingServiceActions( [ ( CC.DEFAULT_FAVOURITES_RATING_SERVICE_KEY, HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE ) ] )
        duplicate_content_merge_options.SetSyncArchiveAction( ClientDuplicates.SYNC_ARCHIVE_DO_BOTH_REGARDLESS )
        duplicate_content_merge_options.SetSyncURLsAction( HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE )
        duplicate_content_merge_options.SetSyncFileModifiedDateAction( HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE )
        duplicate_content_merge_options.SetSyncNotesAction( HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE )
        
        note_import_options = NoteImportOptions.NoteImportOptions()
        
        note_import_options.SetIsDefault( False )
        note_import_options.SetGetNotes( True )
        note_import_options.SetExtendExistingNoteIfPossible( True )
        note_import_options.SetConflictResolution( NoteImportOptions.NOTE_IMPORT_CONFLICT_RENAME )
        
        duplicate_content_merge_options.SetSyncNoteImportOptions( note_import_options )
        
        self._dictionary[ 'duplicate_action_options' ][ HC.DUPLICATE_SAME_QUALITY ] = duplicate_content_merge_options
        
        duplicate_content_merge_options = ClientDuplicates.DuplicateContentMergeOptions()
        
        self._dictionary[ 'duplicate_action_options' ][ HC.DUPLICATE_ALTERNATE ] = duplicate_content_merge_options
        
        #
        
        from hydrus.client.gui.canvas import ClientGUICanvasMedia
        from hydrus.client.gui.widgets import ClientGUIPainterShapes
        from hydrus.core.files.images import HydrusImageHandling
        
        self._dictionary[ 'integers' ] = {
            'notebook_tab_alignment' : CC.DIRECTION_UP,
            'video_buffer_size' : 96 * 1024 * 1024,
            'related_tags_search_1_duration_ms' : 250,
            'related_tags_search_2_duration_ms' : 2000,
            'related_tags_search_3_duration_ms' : 6000,
            'related_tags_concurrence_threshold_percent' : 6,
            'suggested_tags_width' : 300,
            'similar_files_duplicate_pairs_search_distance' : 0,
            'default_new_page_goes' : CC.NEW_PAGE_GOES_FAR_RIGHT,
            'close_page_focus_goes' : CC.CLOSED_PAGE_FOCUS_GOES_RIGHT,
            'num_recent_petition_reasons' : 5,
            'max_page_name_chars' : 20,
            'page_file_count_display' : CC.PAGE_FILE_COUNT_DISPLAY_ALL_BUT_ONLY_IF_GREATER_THAN_ZERO,
            'network_timeout' : 10,
            'connection_error_wait_time' : 15,
            'serverside_bandwidth_wait_time' : 60,
            'thumbnail_visibility_scroll_percent' : 75,
            'ideal_tile_dimension' : 768,
            'wake_delay_period' : 15,
            'media_viewer_zoom_center' : ClientGUICanvasMedia.ZOOM_CENTERPOINT_MOUSE,
            'last_session_save_period_minutes' : 5,
            'shutdown_work_period' : 86400,
            'max_network_jobs' : 15,
            'max_network_jobs_per_domain' : 3,
            'max_connection_attempts_allowed' : 5,
            'max_request_attempts_allowed_get' : 5,
            'thumbnail_scale_type' : HydrusImageHandling.THUMBNAIL_SCALE_DOWN_ONLY,
            'max_simultaneous_subscriptions' : 1,
            'gallery_page_wait_period_pages' : 15,
            'gallery_page_wait_period_subscriptions' : 5,
            'watcher_page_wait_period' : 5,
            'popup_message_character_width' : 56,
            'duplicate_filter_max_batch_size' : 100,
            'video_thumbnail_percentage_in' : 35,
            'global_audio_volume' : 70,
            'media_viewer_audio_volume' : 70,
            'preview_audio_volume' : 70,
            'duplicate_comparison_score_higher_jpeg_quality' : 10,
            'duplicate_comparison_score_much_higher_jpeg_quality' : 20,
            'duplicate_comparison_score_higher_filesize' : 10,
            'duplicate_comparison_score_much_higher_filesize' : 20,
            'duplicate_comparison_score_higher_resolution' : 20,
            'duplicate_comparison_score_much_higher_resolution' : 50,
            'duplicate_comparison_score_more_tags' : 8,
            'duplicate_comparison_score_older' : 4,
            'duplicate_comparison_score_nicer_ratio' : 10,
            'duplicate_comparison_score_has_audio' : 20,
            'thumbnail_cache_size' : 1024 * 1024 * 32,
            'image_cache_size' : 1024 * 1024 * 1024,
            'image_tile_cache_size' : 1024 * 1024 * 256,
            'thumbnail_cache_timeout' : 86400,
            'image_cache_timeout' : 600,
            'image_tile_cache_timeout' : 300,
            'image_cache_storage_limit_percentage' : 25,
            'image_cache_prefetch_limit_percentage' : 15,
            'media_viewer_prefetch_delay_base_ms' : 100,
            'media_viewer_prefetch_num_previous' : 2,
            'media_viewer_prefetch_num_next' : 3,
            'duplicate_filter_prefetch_num_pairs' : 5,
            'thumbnail_border' : 1,
            'thumbnail_margin' : 2,
            'thumbnail_dpr_percent' : 100,
            'file_maintenance_idle_throttle_files' : 1,
            'file_maintenance_idle_throttle_time_delta' : 2,
            'file_maintenance_active_throttle_files' : 1,
            'file_maintenance_active_throttle_time_delta' : 20,
            'subscription_network_error_delay' : 12 * 3600,
            'subscription_other_error_delay' : 36 * 3600,
            'downloader_network_error_delay' : 90 * 60,
            'file_viewing_stats_menu_display' : CC.FILE_VIEWING_STATS_MENU_DISPLAY_SUMMED_AND_THEN_SUBMENU,
            'number_of_gui_session_backups' : 10,
            'animated_scanbar_height' : 20,
            'animated_scanbar_nub_width' : 10,
            'domain_network_infrastructure_error_number' : 3,
            'domain_network_infrastructure_error_time_delta' : 600,
            'ac_read_list_height_num_chars' : 21,
            'ac_write_list_height_num_chars' : 11,
            'system_busy_cpu_percent' : 50,
            'human_bytes_sig_figs' : 3,
            'ms_to_wait_between_physical_file_deletes' : 600,
            'potential_duplicates_search_work_time_ms_active' : 100,
            'potential_duplicates_search_work_time_ms_idle' : 5000,
            'potential_duplicates_search_rest_percentage_active' : 1900,
            'potential_duplicates_search_rest_percentage_idle' : 50,
            'duplicates_auto_resolution_work_time_ms_active' : 100,
            'duplicates_auto_resolution_work_time_ms_idle' : 1000,
            'duplicates_auto_resolution_rest_percentage_active' : 900,
            'duplicates_auto_resolution_rest_percentage_idle' : 100,
            'repository_processing_work_time_ms_very_idle' : 30000,
            'repository_processing_rest_percentage_very_idle' : 3,
            'repository_processing_work_time_ms_idle' : 10000,
            'repository_processing_rest_percentage_idle' : 5,
            'repository_processing_work_time_ms_normal' : 500,
            'repository_processing_rest_percentage_normal' : 10,
            'tag_display_processing_work_time_ms_idle' : 15000,
            'tag_display_processing_rest_percentage_idle' : 3,
            'tag_display_processing_work_time_ms_normal' : 100,
            'tag_display_processing_rest_percentage_normal' : 9900,
            'tag_display_processing_work_time_ms_work_hard' : 5000,
            'tag_display_processing_rest_percentage_work_hard' : 5,
            'deferred_table_delete_work_time_ms_idle' : 20000,
            'deferred_table_delete_rest_percentage_idle' : 10,
            'deferred_table_delete_work_time_ms_normal' : 250,
            'deferred_table_delete_rest_percentage_normal' : 1000,
            'deferred_table_delete_work_time_ms_work_hard' : 5000,
            'deferred_table_delete_rest_percentage_work_hard' : 10,
            'gallery_page_status_update_time_minimum_ms' : 1000,
            'gallery_page_status_update_time_ratio_denominator' : 30,
            'watcher_page_status_update_time_minimum_ms' : 1000,
            'watcher_page_status_update_time_ratio_denominator' : 30,
            'media_viewer_default_zoom_type_override' : ClientGUICanvasMedia.MEDIA_VIEWER_ZOOM_TYPE_DEFAULT_FOR_FILETYPE,
            'preview_default_zoom_type_override' : ClientGUICanvasMedia.MEDIA_VIEWER_ZOOM_TYPE_DEFAULT_FOR_FILETYPE,
            'export_filename_character_limit' : 220
        }
        
        self._dictionary[ 'floats' ] = {
            'draw_thumbnail_rating_icon_size_px' : ClientGUIPainterShapes.SIZE.width(),
            'thumbnail_rating_incdec_width_px' : ClientGUIPainterShapes.SIZE.width() * 2, #deprecated
            'thumbnail_rating_incdec_height_px' : ClientGUIPainterShapes.SIZE.height(),
            'media_viewer_rating_icon_size_px' : ClientGUIPainterShapes.SIZE.width(),
            'media_viewer_rating_incdec_width_px' : ClientGUIPainterShapes.SIZE.width() * 2, #deprecated
            'media_viewer_rating_incdec_height_px' : ClientGUIPainterShapes.SIZE.height(),
            'preview_window_rating_icon_size_px' : ClientGUIPainterShapes.SIZE.width(),
            'preview_window_rating_incdec_width_px' : ClientGUIPainterShapes.SIZE.width() * 2, #deprecated
            'preview_window_rating_incdec_height_px' : ClientGUIPainterShapes.SIZE.height(),
            'dialog_rating_icon_size_px' : ClientGUIPainterShapes.SIZE.width(),
            'dialog_rating_incdec_width_px' : ClientGUIPainterShapes.SIZE.width() * 2, #deprecated
            'dialog_rating_incdec_height_px' : ClientGUIPainterShapes.SIZE.height(),
        }
        
        #
        
        self._dictionary[ 'keys' ] = {
            'default_tag_service_tab' : CC.DEFAULT_LOCAL_TAG_SERVICE_KEY.hex(),
            'default_tag_service_search_page' : CC.COMBINED_TAG_SERVICE_KEY.hex(),
            'default_gug_key' : HydrusData.GenerateKey().hex()
        }
        
        self._dictionary[ 'key_list' ] = {}
        
        #
        
        self._dictionary[ 'noneable_integers' ] = {
            'forced_search_limit' : None,
            'num_recent_tags' : 20,
            'duplicate_background_switch_intensity_a' : 0,
            'duplicate_background_switch_intensity_b' : 3,
            'duplicate_filter_auto_commit_batch_size' : 1,
            'last_review_bandwidth_search_distance' : 7 * 86400,
            'file_viewing_statistics_media_min_time_ms' : 2 * 1000,
            'file_viewing_statistics_media_max_time_ms' : 600 * 1000,
            'file_viewing_statistics_preview_min_time_ms' : 5 * 1000,
            'file_viewing_statistics_preview_max_time_ms' : 60 * 1000,
            'subscription_file_error_cancel_threshold' : 5,
            'media_viewer_cursor_autohide_time_ms' : 700,
            'idle_mode_client_api_timeout' : None,
            'system_busy_cpu_count' : 1,
            'animated_scanbar_hide_height' : 5,
            'last_backup_time' : None,
            'slideshow_short_duration_loop_percentage' : 20,
            'slideshow_short_duration_loop_seconds' : 10,
            'slideshow_short_duration_cutoff_percentage' : 75,
            'slideshow_long_duration_overspill_percentage' : 50,
            'num_to_show_in_ac_dropdown_children_tab' : 40,
            'number_of_unselected_medias_to_present_tags_for' : 4096,
            'export_path_character_limit' : None,
            'export_dirname_character_limit' : None,
        }
        
        #
        
        self._dictionary[ 'simple_downloader_formulae' ] = HydrusSerialisable.SerialisableList()
        
        #
        
        self._dictionary[ 'noneable_strings' ] = {
            'favourite_file_lookup_script' : 'gelbooru md5',
            'suggested_tags_layout' : 'notebook',
            'backup_path' : None,
            'web_browser_path' : None,
            'last_png_export_dir' : None,
            'media_background_bmp_path' : None,
            'http_proxy' : None,
            'https_proxy' : None,
            'no_proxy' : '127.0.0.1',
            'qt_style_name' : None,
            'qt_stylesheet_name' : None,
            'last_advanced_file_deletion_reason' : None,
            'last_advanced_file_deletion_special_action' : None,
            'sibling_connector_custom_namespace_colour' : 'system',
            'or_connector_custom_namespace_colour' : 'system'
        }
        
        self._dictionary[ 'strings' ] = {
            'app_display_name' : 'hydrus client',
            'namespace_connector' : ':',
            'sibling_connector' : ' \u2192 ',
            'or_connector' : ' OR ',
            'export_phrase' : '{hash}',
            'current_colourset' : 'default',
            'favourite_simple_downloader_formula' : 'all files linked by images in page',
            'thumbnail_scroll_rate' : '1.0',
            'pause_character' : '\u23F8',
            'stop_character' : '\u23F9',
            'default_gug_name' : 'safebooru tag search',
            'has_audio_label' : '\U0001F50A',
            'has_duration_label' : ' \u23F5 ',
            'discord_dnd_filename_pattern' : '{hash}',
            'default_suggested_tags_notebook_page' : 'related',
            'last_incremental_tagging_namespace' : 'page',
            'last_incremental_tagging_prefix' : '',
            'last_incremental_tagging_suffix' : '',
            'last_options_window_panel' : 'gui'
        }
        
        self._dictionary[ 'string_list' ] = {
            'default_media_viewer_custom_shortcuts' : [],
            'favourite_tags' : [],
            'advanced_file_deletion_reasons' : [ 'I do not like it.', 'It is bad quality.', 'It is not appropriate for this client.', 'Temporary delete--I want to bring it back later.' ],
            'user_namespace_group_by_sort' : [ 'creator', 'series', 'character', 'species', '', 'meta' ]
        }
        
        self._dictionary[ 'integer_list' ] = {
            'file_viewing_stats_interesting_canvas_types' : [ CC.CANVAS_MEDIA_VIEWER, CC.CANVAS_CLIENT_API ]
        }
        
        #
        
        from hydrus.client import ClientStrings
        
        self._dictionary[ 'last_used_string_conversion_step' ] = ClientStrings.StringConverter( [ ( ClientStrings.STRING_CONVERSION_APPEND_TEXT, 'extra text' ) ] )
        
        self._dictionary[ 'custom_default_predicates' ] = HydrusSerialisable.SerialisableList()
        
        self._dictionary[ 'predicate_types_to_recent_predicates' ] = HydrusSerialisable.SerialisableDictionary()
        
        from hydrus.client import ClientLocation
        
        self._dictionary[ 'default_local_location_context' ] = ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY )
        
        #
        
        self._dictionary[ 'favourite_tag_filters' ] = HydrusSerialisable.SerialisableDictionary()
        
        #
        
        from hydrus.client.media import ClientMedia
        from hydrus.client.metadata import ClientTags
        
        default_namespace_sorts = HydrusSerialisable.SerialisableList()
        
        default_namespace_sorts.append( ClientMedia.MediaSort( sort_type = ( 'namespaces', ( ( 'series', 'creator', 'title', 'volume', 'chapter', 'page' ), ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL ) ) ) )
        default_namespace_sorts.append( ClientMedia.MediaSort( sort_type = ( 'namespaces', ( ( 'creator', 'series', 'title', 'volume', 'chapter', 'page' ), ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL ) ) ) )
        
        self._dictionary[ 'default_namespace_sorts' ] = default_namespace_sorts
        
        #
        
        self._dictionary[ 'related_tags_search_tag_slices_weight_percent' ] = HydrusSerialisable.SerialisableList( [
            [ '', 10 ],
            [ ':', 100 ],
            [ 'character:', 300 ],
            [ 'creator:', 300 ],
            [ 'series:', 300 ],
            [ 'filename:', 0 ],
            [ 'page:', 0 ],
            [ 'chapter:', 0 ],
            [ 'volume:', 0 ],
            [ 'title:', 0 ]
        ] )
        
        self._dictionary[ 'related_tags_result_tag_slices_weight_percent' ] = HydrusSerialisable.SerialisableList( [
            [ '', 50 ],
            [ ':', 100 ],
            [ 'character:', 400 ],
            [ 'creator:', 200 ],
            [ 'series:', 200 ],
            [ 'filename:', 0 ],
            [ 'page:', 0 ],
            [ 'chapter:', 0 ],
            [ 'volume:', 0 ],
            [ 'title:', 0 ]
        ] )
        
        #
        
        self._dictionary[ 'tag_summary_generators' ] = HydrusSerialisable.SerialisableDictionary()
        
        namespace_info = []
        
        namespace_info.append( ( 'creator', '', ', ' ) )
        namespace_info.append( ( 'series', '', ', ' ) )
        namespace_info.append( ( 'title', '', ', ' ) )
        
        separator = ' - '
        
        # the cleantags here converts to unicode, which is important!
        
        example_tags = HydrusTags.CleanTags( [ 'creator:creator', 'series:series', 'title:title' ] )
        
        from hydrus.client.gui.metadata import ClientGUITagSummaryGenerator
        
        tsg = ClientGUITagSummaryGenerator.TagSummaryGenerator( namespace_info = namespace_info, separator = separator, example_tags = example_tags )
        
        self._dictionary[ 'tag_summary_generators' ][ 'thumbnail_top' ] = tsg
        
        namespace_info = []
        
        namespace_info.append( ( 'volume', 'v', '-' ) )
        namespace_info.append( ( 'chapter', 'c', '-' ) )
        namespace_info.append( ( 'page', 'p', '-' ) )
        
        separator = '-'
        
        example_tags = HydrusTags.CleanTags( [ 'volume:3', 'chapter:10', 'page:330', 'page:331' ] )
        
        tsg = ClientGUITagSummaryGenerator.TagSummaryGenerator( namespace_info = namespace_info, separator = separator, example_tags = example_tags )
        
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
        
        tsg = ClientGUITagSummaryGenerator.TagSummaryGenerator( namespace_info = namespace_info, separator = separator, example_tags = example_tags )
        
        self._dictionary[ 'tag_summary_generators' ][ 'media_viewer_top' ] = tsg
        
        #
        
        self._dictionary[ 'default_file_import_options' ] = HydrusSerialisable.SerialisableDictionary()
        
        from hydrus.client.importing.options import FileImportOptions
        
        exclude_deleted = True
        preimport_hash_check_type = FileImportOptions.DO_CHECK_AND_MATCHES_ARE_DISPOSITIVE
        preimport_url_check_type = FileImportOptions.DO_CHECK
        preimport_url_check_looks_for_neighbour_spam = True
        allow_decompression_bombs = True
        min_size = None
        max_size = None
        max_gif_size = None
        min_resolution = None
        max_resolution = None
        
        automatic_archive = False
        associate_primary_urls = True
        associate_source_urls = True
        
        from hydrus.client.importing.options import PresentationImportOptions
        
        presentation_import_options = PresentationImportOptions.PresentationImportOptions()
        
        presentation_import_options.SetPresentationStatus( PresentationImportOptions.PRESENTATION_STATUS_NEW_ONLY )
        
        quiet_file_import_options = FileImportOptions.FileImportOptions()
        
        quiet_file_import_options.SetPreImportOptions( exclude_deleted, preimport_hash_check_type, preimport_url_check_type, allow_decompression_bombs, min_size, max_size, max_gif_size, min_resolution, max_resolution )
        quiet_file_import_options.SetPreImportURLCheckLooksForNeighbourSpam( preimport_url_check_looks_for_neighbour_spam )
        quiet_file_import_options.SetPostImportOptions( automatic_archive, associate_primary_urls, associate_source_urls )
        quiet_file_import_options.SetPresentationImportOptions( presentation_import_options )
        quiet_file_import_options.SetDestinationLocationContext( ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ) )
        
        self._dictionary[ 'default_file_import_options' ][ 'quiet' ] = quiet_file_import_options
        
        loud_file_import_options = FileImportOptions.FileImportOptions()
        
        loud_file_import_options.SetPreImportOptions( exclude_deleted, preimport_hash_check_type, preimport_url_check_type, allow_decompression_bombs, min_size, max_size, max_gif_size, min_resolution, max_resolution )
        loud_file_import_options.SetPreImportURLCheckLooksForNeighbourSpam( preimport_url_check_looks_for_neighbour_spam )
        loud_file_import_options.SetPostImportOptions( automatic_archive, associate_primary_urls, associate_source_urls )
        loud_file_import_options.SetDestinationLocationContext( ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ) )
        
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
        self._dictionary[ 'frame_locations' ][ 'file_history_chart' ] = ( True, True, ( 960, 720 ), None, ( -1, -1 ), 'topleft', False, False )
        self._dictionary[ 'frame_locations' ][ 'mr_bones' ] = ( True, True, None, None, ( -1, -1 ), 'topleft', False, False )
        self._dictionary[ 'frame_locations' ][ 'manage_urls_dialog' ] = ( True, True, None, None, ( -1, -1 ), 'topleft', False, False )
        self._dictionary[ 'frame_locations' ][ 'manage_times_dialog' ] = ( True, True, None, None, ( -1, -1 ), 'topleft', False, False )
        self._dictionary[ 'frame_locations' ][ 'manage_notes_dialog' ] = ( True, True, None, None, ( -1, -1 ), 'topleft', False, False )
        self._dictionary[ 'frame_locations' ][ 'export_files_frame' ] = ( True, True, None, None, ( -1, -1 ), 'topleft', False, False )
        
        #
        
        self._dictionary[ 'media_launch' ] = HydrusSerialisable.SerialisableDictionary() # integer keys, so got to be cleverer dict
        
        for mime in HC.SEARCHABLE_MIMES:
            
            self._dictionary[ 'media_launch' ][ mime ] = None
            
        
        #
        
        self._dictionary[ 'media_view' ] = self._GetDefaultMediaViewOptions()
        
        self._dictionary[ 'media_zooms' ] = [ 0.01, 0.05, 0.1, 0.15, 0.2, 0.3, 0.5, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.5, 2.0, 3.0, 5.0, 10.0, 20.0 ]
        
        self._dictionary[ 'slideshow_durations' ] = [ 1.0, 5.0, 10.0, 30.0, 60.0 ]
        
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
        
        self._dictionary[ 'default_tag_sorts' ] = HydrusSerialisable.SerialisableDictionary()
        
        self._dictionary[ 'default_tag_sorts' ][ CC.TAG_PRESENTATION_SEARCH_PAGE ] = ClientTagSorting.TagSort.STATICGetTextASCUserGroupedDefault()
        self._dictionary[ 'default_tag_sorts' ][ CC.TAG_PRESENTATION_SEARCH_PAGE_MANAGE_TAGS ] = ClientTagSorting.TagSort.STATICGetTextASCUserGroupedDefault()
        self._dictionary[ 'default_tag_sorts' ][ CC.TAG_PRESENTATION_MEDIA_VIEWER ] = ClientTagSorting.TagSort.STATICGetTextASCUserGroupedDefault()
        self._dictionary[ 'default_tag_sorts' ][ CC.TAG_PRESENTATION_MEDIA_VIEWER_MANAGE_TAGS ] = ClientTagSorting.TagSort.STATICGetTextASCUserGroupedDefault()
        
        #
        
        self._dictionary[ 'default_export_files_metadata_routers' ] = HydrusSerialisable.SerialisableList()
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        loaded_dictionary = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_info )
        
        for ( key, value ) in loaded_dictionary.items():
            
            if key in self._dictionary and isinstance( self._dictionary[ key ], dict ) and isinstance( value, dict ):
                
                self._dictionary[ key ].update( value )
                
            else:
                
                self._dictionary[ key ] = value
                
            
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            loaded_dictionary = HydrusSerialisable.CreateFromSerialisableTuple( old_serialisable_info )
            
            if 'media_view' in loaded_dictionary:
                
                mimes = list( loaded_dictionary[ 'media_view' ].keys() )
                
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
            
        
        if version == 4:
            
            serialisable_dictionary = old_serialisable_info
            
            loaded_dictionary = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_dictionary )
            
            if 'key_list' in loaded_dictionary and 'default_neighbouring_txt_tag_service_keys' in loaded_dictionary[ 'key_list' ]:
                
                encoded_default_neighbouring_txt_tag_service_keys = loaded_dictionary[ 'key_list' ][ 'default_neighbouring_txt_tag_service_keys' ]
                
                default_neighbouring_txt_tag_service_keys = [ bytes.fromhex( hex_key ) for hex_key in encoded_default_neighbouring_txt_tag_service_keys ]
                
                from hydrus.client.metadata import ClientMetadataMigration
                from hydrus.client.metadata import ClientMetadataMigrationExporters
                from hydrus.client.metadata import ClientMetadataMigrationImporters
                
                importers = [ ClientMetadataMigrationImporters.SingleFileMetadataImporterMediaTags( service_key = service_key ) for service_key in default_neighbouring_txt_tag_service_keys ]
                exporter = ClientMetadataMigrationExporters.SingleFileMetadataExporterTXT()
                
                metadata_router = ClientMetadataMigration.SingleFileMetadataRouter( importers = importers, exporter = exporter )
                
                metadata_routers = [ metadata_router ]
                
                loaded_dictionary[ 'default_export_files_metadata_routers' ] = HydrusSerialisable.SerialisableList( metadata_routers )
                
                del loaded_dictionary[ 'key_list' ][ 'default_neighbouring_txt_tag_service_keys' ]
                
            
            new_serialisable_info = loaded_dictionary.GetSerialisableTuple()
            
            return ( 5, new_serialisable_info )
            
        
        if version == 5:
            
            serialisable_dictionary = old_serialisable_info
            
            loaded_dictionary = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_dictionary )
            
            if 'default_tag_sort' in loaded_dictionary:
                
                from hydrus.client.metadata import ClientTagSorting
                
                loaded_dictionary[ 'default_tag_sorts' ] = HydrusSerialisable.SerialisableDictionary()
                
                loaded_dictionary[ 'default_tag_sorts' ][ CC.TAG_PRESENTATION_SEARCH_PAGE ] = loaded_dictionary[ 'default_tag_sort' ]
                loaded_dictionary[ 'default_tag_sorts' ][ CC.TAG_PRESENTATION_SEARCH_PAGE_MANAGE_TAGS ] = ClientTagSorting.TagSort.STATICGetTextASCUserGroupedDefault()
                loaded_dictionary[ 'default_tag_sorts' ][ CC.TAG_PRESENTATION_MEDIA_VIEWER ] = ClientTagSorting.TagSort.STATICGetTextASCUserGroupedDefault()
                loaded_dictionary[ 'default_tag_sorts' ][ CC.TAG_PRESENTATION_MEDIA_VIEWER_MANAGE_TAGS ] = ClientTagSorting.TagSort.STATICGetTextASCUserGroupedDefault()
                
                del loaded_dictionary[ 'default_tag_sort' ]
                
            
            new_serialisable_info = loaded_dictionary.GetSerialisableTuple()
            
            return ( 6, new_serialisable_info )
            
        
    
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
            
            return self._dictionary[ 'booleans' ][ name ]
            
        
    
    def GetBoolean( self, name ):
        
        with self._lock:
            
            return self._dictionary[ 'booleans' ][ name ]
            
        
    
    def GetAllBooleans( self ):
        
        with self._lock:
            
            return self._dictionary[ 'booleans' ]
            
        
    
    def GetDefaultCollect( self ):
        
        with self._lock:
            
            return self._dictionary[ 'default_collect' ]
            
        
    
    def GetColour( self, colour_type, colourset = None ):
        
        with self._lock:
            
            if colourset is None:
                
                colourset = self._dictionary[ 'strings' ][ 'current_colourset' ]
                
            
            ( r, g, b ) = self._dictionary[ 'colours' ][ colourset ][ colour_type ]
            
            return QG.QColor( r, g, b )
            
        
    
    def GetAllColours( self ):
        
        with self._lock:
            
            return self._dictionary[ 'colours' ]
            
        
    
    def GetCustomDefaultSystemPredicates( self, predicate_type = None, comparable_predicate = None ):
        
        with self._lock:
            
            custom_default_predicates = self._dictionary[ 'custom_default_predicates' ]
            
            if predicate_type is not None:
                
                return [ pred for pred in custom_default_predicates if pred.GetType() == predicate_type ]
                
            
            if comparable_predicate is not None:
                
                return [ pred for pred in custom_default_predicates if pred.IsUIEditable( comparable_predicate ) ]
                
            
            return []
            
        
    
    def GetDefaultExportFilesMetadataRouters( self ):
        
        with self._lock:
            
            return list( self._dictionary[ 'default_export_files_metadata_routers' ] )
            
        
    
    def GetDefaultFileImportOptions( self, options_type ) -> FileImportOptions.FileImportOptions:
        
        with self._lock:
            
            if options_type == FileImportOptions.IMPORT_TYPE_LOUD:
                
                key = 'loud'
                
            else:
                
                key = 'quiet'
                
                
            
            return self._dictionary[ 'default_file_import_options' ][ key ]
            
        
    
    def GetDefaultLocalLocationContext( self ):
        
        with self._lock:
            
            location_context = self._dictionary[ 'default_local_location_context' ]
            
            try:
                
                location_context.FixMissingServices( CG.client_controller.services_manager.FilterValidServiceKeys )
                
                if location_context.IsEmpty():
                    
                    from hydrus.client import ClientLocation
                    
                    location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY )
                    
                
            except:
                
                pass
                
            
            return location_context
            
        
    
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
            
        
    
    def GetDefaultTagSort( self, tag_presentation_location: int ):
        
        with self._lock:
            
            return self._dictionary[ 'default_tag_sorts' ][ tag_presentation_location ]
            
        
    
    def GetDefaultWatcherCheckerOptions( self ):
        
        with self._lock:
            
            return self._dictionary[ 'misc' ][ 'default_thread_watcher_options' ]
            
        
    
    def GetDuplicateContentMergeOptions( self, duplicate_type ) -> ClientDuplicates.DuplicateContentMergeOptions:
        
        with self._lock:
            
            if duplicate_type in self._dictionary[ 'duplicate_action_options' ]:
                
                return self._dictionary[ 'duplicate_action_options' ][ duplicate_type ]
                
            else:
                
                return ClientDuplicates.DuplicateContentMergeOptions()
                
            
        
    
    def GetFallbackSort( self ):
        
        with self._lock:
            
            return self._dictionary[ 'fallback_sort' ]
            
        
    
    def GetFavouriteTagFilters( self ):
        
        with self._lock:
            
            return dict( self._dictionary[ 'favourite_tag_filters' ] )
            
        
    
    def GetFloat( self, name: str ):
        
        with self._lock:
            
            return self._dictionary[ 'floats' ][ name ]
            
        
    
    def GetFrameLocation( self, frame_key ):
        
        with self._lock:
            
            d = self._dictionary[ 'frame_locations' ]
            
            if frame_key in d:
                
                return d[ frame_key ]
                
            else:
                
                HydrusData.Print( f'Could not find {frame_key} in the frame locations options!' )
                
                return ( False, False, None, None, ( -1, -1 ), 'topleft', False, False )
                
            
        
    
    def GetFrameLocations( self ):
        
        with self._lock:
            
            return list(self._dictionary[ 'frame_locations' ].items())
            
        
    
    def GetInteger( self, name ):
        
        with self._lock:
            
            return self._dictionary[ 'integers' ][ name ]
            
        
    
    def GetIntegerList( self, name: str ) -> list[ int ]:
        
        with self._lock:
            
            return self._dictionary[ 'integer_list' ][ name ]
            
        
    
    def GetAllIntegers( self):
        
        with self._lock:
            
            return self._dictionary[ 'integers' ]

        
    
    def GetKeyHex( self, name ):
        
        with self._lock:
            
            return self._dictionary[ 'keys' ][ name ]
            
        
    
    def GetKey( self, name ):
        
        return bytes.fromhex( self.GetKeyHex( name ) )
        
    
    def GetAllKeysHex( self ):
        
        with self._lock:
            
            return self._dictionary[ 'keys' ]
            
        
    
    def GetKeyList( self, name ):
        
        with self._lock:
            
            return [ bytes.fromhex( hex_key ) for hex_key in self._dictionary[ 'key_list' ][ name ] ]
            
        
    
    def GetMediaShowAction( self, mime ):
        
        with self._lock:
            
            if mime == HC.APPLICATION_UNKNOWN:
                
                return ( CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW, False, False )
                
            
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
            
        
    
    def GetAllNoneableIntegers( self ):
        
        with self._lock:
            
            return self._dictionary[ 'noneable_integers' ]
            
        
    
    def GetNoneableString( self, name ):
        
        with self._lock:
            
            return self._dictionary[ 'noneable_strings' ][ name ]
            
        
    
    def GetAllNoneableStrings( self ):
        
        with self._lock:
            
            return self._dictionary[ 'noneable_strings' ]
            
        
    
    def GetPreviewShowAction( self, mime ):
        
        with self._lock:
            
            if mime == HC.APPLICATION_UNKNOWN:
                
                return ( CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW, False, False )
                
            
            ( media_show_action, media_start_paused, media_start_with_embed, preview_show_action, preview_start_paused, preview_start_with_embed, zoom_info ) = self._GetMediaViewOptions( mime )
            
            ( possible_show_actions, can_start_paused, can_start_with_embed ) = CC.media_viewer_capabilities[ mime ]
            
            if preview_show_action not in possible_show_actions:
                
                return ( CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON, False, False )
                
            
            return ( preview_show_action, preview_start_paused, preview_start_with_embed )
            
        
    
    def GetRawSerialisable( self, name ):
        
        with self._lock:
            
            return self._dictionary[ name ]
        
    
    def GetRecentPetitionReasons( self, content_type, action ):
        
        with self._lock:
            
            return list( self._dictionary[ 'recent_petition_reasons' ].get( ( content_type, action ), [] ) )[ : self._dictionary[ 'integers' ][ 'num_recent_petition_reasons' ] ]
            
        
    
    def GetRecentPredicates( self, predicate_types ):
        
        with self._lock:
            
            result = []
            
            predicate_types_to_recent_predicates = self._dictionary[ 'predicate_types_to_recent_predicates' ]
            
            for predicate_type in predicate_types:
                
                if predicate_type in predicate_types_to_recent_predicates:
                    
                    result.extend( predicate_types_to_recent_predicates[ predicate_type ] )
                    
                
            
            return result
            
        
    
    def GetRelatedTagsTagSliceWeights( self ):
        
        with self._lock:
            
            return (
                [ tuple( row ) for row in self._dictionary[ 'related_tags_search_tag_slices_weight_percent' ] ],
                [ tuple( row ) for row in self._dictionary[ 'related_tags_result_tag_slices_weight_percent' ] ]
            )
            
        
    
    def GetSimpleDownloaderFormulae( self ):
        
        with self._lock:
            
            return self._dictionary[ 'simple_downloader_formulae' ]
            
        
    
    def GetSlideshowDurations( self ):
        
        with self._lock:
            
            return list( self._dictionary[ 'slideshow_durations' ] )
            
        
    
    def GetString( self, name ):
        
        with self._lock:
            
            return self._dictionary[ 'strings' ][ name ]
            
        
    
    def GetAllStrings( self ):
        
        with self._lock:
            
            return self._dictionary[ 'strings' ]
            
        
    
    def GetStringList( self, name: str ) -> list[ str ]:
        
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
                
            
        
    
    def GetAllSuggestedTagsFavourites( self ):
        
        with self._lock:
            
            return self._dictionary[ 'suggested_tags' ][ 'favourites' ]
                
            
        
    
    def GetTagSummaryGenerator( self, name ):
        
        with self._lock:
            
            return self._dictionary[ 'tag_summary_generators' ][ name ]
            
        
    
    def InvertBoolean( self, name ):
        
        with self._lock:
            
            self._dictionary[ 'booleans' ][ name ] = not self._dictionary[ 'booleans' ][ name ]
            
        
    
    def PushRecentPetitionReason( self, content_type, action, reason ):
        
        with self._lock:
            
            key = ( content_type, action )
            
            if key not in self._dictionary[ 'recent_petition_reasons' ]:
                
                self._dictionary[ 'recent_petition_reasons' ][ key ] = []
                
            
            reasons = self._dictionary[ 'recent_petition_reasons' ][ key ]
            
            if reason in reasons:
                
                reasons.remove( reason )
                
            
            reasons.insert( 0, reason )
            
            self._dictionary[ 'recent_petition_reasons' ][ key ] = reasons[ : self._dictionary[ 'integers' ][ 'num_recent_petition_reasons' ] ]
            
        
    
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
                    
                
            
        
    
    def RemoveRecentPredicate( self, predicate ):
        
        with self._lock:
            
            predicate_types_to_recent_predicates = self._dictionary[ 'predicate_types_to_recent_predicates' ]
            
            for recent_predicates in predicate_types_to_recent_predicates.values():
                
                if predicate in recent_predicates:
                    
                    recent_predicates.remove( predicate )
                    
                    return
                    
                
            
        
    
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
                
            
        
    
    def SetDefaultExportFilesMetadataRouters( self, metadata_routers ):
        
        with self._lock:
            
            self._dictionary[ 'default_export_files_metadata_routers' ] = HydrusSerialisable.SerialisableList( metadata_routers )
            
        
    
    def SetDefaultFileImportOptions( self, options_type, file_import_options ):
        
        with self._lock:
            
            if options_type == FileImportOptions.IMPORT_TYPE_LOUD:
                
                key = 'loud'
                
            else:
                
                key = 'quiet'
                
            
            self._dictionary[ 'default_file_import_options' ][ key ] = file_import_options
            
        
    
    def SetDefaultLocalLocationContext( self, location_context ):
        
        with self._lock:
            
            self._dictionary[ 'default_local_location_context' ] = location_context
            
        
    
    def SetDefaultNamespaceSorts( self, namespace_sorts ):
        
        with self._lock:
            
            default_namespace_sorts = HydrusSerialisable.SerialisableList()
            
            for namespace_sort in namespace_sorts:
                
                default_namespace_sorts.append( namespace_sort )
                
            
            self._dictionary[ 'default_namespace_sorts' ] = default_namespace_sorts
            
        
    
    def SetDefaultTagSort( self, tag_presentation_location, tag_sort ):
        
        with self._lock:
            
            self._dictionary[ 'default_tag_sorts' ][ tag_presentation_location ] = tag_sort
            
        
    
    def SetDefaultSort( self, media_sort ):
        
        with self._lock:
            
            self._dictionary[ 'default_sort' ] = media_sort
            
        
    
    def SetDefaultSubscriptionCheckerOptions( self, checker_options ):
        
        with self._lock:
            
            self._dictionary[ 'misc' ][ 'default_subscription_checker_options' ] = checker_options
            
        
    
    def SetDefaultWatcherCheckerOptions( self, checker_options ):
        
        with self._lock:
            
            self._dictionary[ 'misc' ][ 'default_thread_watcher_options' ] = checker_options
            
        
    
    def SetDuplicateContentMergeOptions( self, duplicate_type, duplicate_content_merge_options ):
        
        with self._lock:
            
            self._dictionary[ 'duplicate_action_options' ][ duplicate_type ] = duplicate_content_merge_options
            
        
    
    def SetFallbackSort( self, media_sort ):
        
        with self._lock:
            
            self._dictionary[ 'fallback_sort' ] = media_sort
            
        
    
    def SetFavouriteTagFilters( self, names_to_tag_filters ):
        
        with self._lock:
            
            self._dictionary[ 'favourite_tag_filters' ] = HydrusSerialisable.SerialisableDictionary( names_to_tag_filters )
            
        
    
    def SetFloat( self, name: str, value: float ):
        
        with self._lock:
            
            self._dictionary[ 'floats' ][ name ] = value
            
        
    
    def SetFrameLocation( self, frame_key, remember_size, remember_position, last_size, last_position, default_gravity, default_position, maximised, fullscreen ):
        
        with self._lock:
            
            self._dictionary[ 'frame_locations' ][ frame_key ] = ( remember_size, remember_position, last_size, last_position, default_gravity, default_position, maximised, fullscreen )
            
        
    
    def SetInteger( self, name, value ):
        
        with self._lock:
            
            self._dictionary[ 'integers' ][ name ] = value
            
        
    
    def SetIntegerList( self, name: str, value: list[ int ] ):
        
        with self._lock:
            
            self._dictionary[ 'integer_list' ][ name ] = list( value )
            
        
    
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
            
        
    
    def SetRawSerialisable( self, name, value ):
        
        with self._lock:
            
            self._dictionary[ name ] = value
            
        
    
    def SetRelatedTagsTagSliceWeights( self, related_tags_search_tag_slices_weight_percent, related_tags_result_tag_slices_weight_percent ):
        
        with self._lock:
            
            self._dictionary[ 'related_tags_search_tag_slices_weight_percent' ] = HydrusSerialisable.SerialisableList( related_tags_search_tag_slices_weight_percent )
            self._dictionary[ 'related_tags_result_tag_slices_weight_percent' ] = HydrusSerialisable.SerialisableList( related_tags_result_tag_slices_weight_percent )
            
        
    
    def SetSimpleDownloaderFormulae( self, simple_downloader_formulae ):
        
        with self._lock:
            
            self._dictionary[ 'simple_downloader_formulae' ] = HydrusSerialisable.SerialisableList( simple_downloader_formulae )
            
        
    
    def SetSlideshowDurations( self, slideshow_durations ):
        
        with self._lock:
            
            self._dictionary[ 'slideshow_durations' ] = slideshow_durations
            
        
    
    def SetString( self, name, value ):
        
        if value is None:
            
            value = ''
            
        
        with self._lock:
            
            if self._dictionary[ 'strings' ][ name ] != value:
                
                self._dictionary[ 'strings' ][ name ] = value
                
            
        
    
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
