import threading

controller = None
client_controller = None
server_controller = None
test_controller = None
view_shutdown = False
model_shutdown = False

no_daemons = False
no_wal = False
no_db_temp_files = False

import_folders_running = False
export_folders_running = False
subscriptions_running = False

callto_report_mode = False
db_report_mode = False
db_profile_mode = False
file_report_mode = False
media_load_report_mode = False
gui_report_mode = False
shortcut_report_mode = False
subprocess_report_mode = False
subscription_report_mode = False
hover_window_report_mode = False
file_import_report_mode = False
phash_generation_report_mode = False
menu_profile_mode = False
network_report_mode = False
pubsub_report_mode = False
pubsub_profile_mode = False
ui_timer_profile_mode = False
daemon_report_mode = False
force_idle_mode = False
no_page_limit_mode = False
thumbnail_debug_mode = False
server_busy = False
currently_uploading_pending = False

shutting_down_due_to_already_running = False

do_idle_shutdown_work = False
shutdown_complete = False
restart = False
emergency_exit = False

twisted_is_broke = False

do_not_catch_char_hook = False

dirty_object_lock = threading.Lock()
