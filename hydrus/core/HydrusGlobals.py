# Couldn't think where else to put this, but I want a record:
# If you are setting up a new IDE, here are hydev's current ignore rules for PyUnresolvedReferences:
#
# connect # it sucks, but for qtpy Qt Signals gubbins
# emit # it sucks a little, but for qtpy Qt Signals gubbins
# twisted.internet.reactor.*
# PySide6.QtWidgets.QStyle.*
#

import threading
import typing

if typing.TYPE_CHECKING:
    
    from hydrus.core import HydrusController
    

controller: "HydrusController.HydrusController" = None

# TODO: move the client, server, and any test-specific garbage to the new module Globals mate, and/or the controller objects themselves

started_shutdown: bool = False
view_shutdown: bool = False
model_shutdown: bool = False

server_action = 'start'

db_journal_mode = 'WAL'
no_db_temp_files: bool = False

non_interactive_update: bool = False

boot_debug: bool = False

db_cache_size = 256
db_transaction_commit_period = 30

# if this is set to 1, transactions are not immediately synced to the journal so multiple can be undone following a power-loss
# if set to 2, all transactions are synced, so once a new one starts you know the last one is on disk
# corruption cannot occur either way, but since we have multiple ATTACH dbs with diff journals, let's not mess around when power-cut during heavy file import or w/e
db_synchronous = 2

import_folders_running: bool = False
export_folders_running: bool = False

boot_with_network_traffic_paused_command_line: bool = False

db_profile_min_job_time_ms = 16
callto_profile_min_job_time_ms = 10
server_profile_min_job_time_ms = 10
menu_profile_min_job_time_ms = 16
pubsub_profile_min_job_time_ms = 5
ui_timer_profile_min_job_time_ms = 5

macos_antiflicker_test: bool = False

canvas_tile_outline_mode: bool = False

callto_report_mode: bool = False
db_report_mode: bool = False
file_report_mode: bool = False
file_sort_report_mode: bool = False
media_load_report_mode: bool = False
gui_report_mode: bool = False
shortcut_report_mode: bool = False
cache_report_mode: bool = False
idle_report_mode: bool = False
subprocess_report_mode: bool = False
subscription_report_mode: bool = False
hover_window_report_mode: bool = False
file_import_report_mode: bool = False
phash_generation_report_mode: bool = False
network_report_mode: bool = False
network_report_mode_silent: bool = False
pubsub_report_mode: bool = False
daemon_report_mode: bool = False
mpv_report_mode: bool = False
potential_duplicates_report_mode: bool = False
thumbnail_graphics_view_report_mode: bool = False

# just to note for this guy, we are looking at:
    # MainLoop: quick downloader
    # MainLoop: duplicates auto-resolution
    # MainLoop: import folders
    # MainLoop: potential duplicates search
    # MainLoop: file maintenance
    # MainLoop: db maintenance
    # MainLoop: tag display sync
    # MainLoop: subscriptions
    # 10+ CallToThread
    # 2 Job Scheduler
    # ~10 CallToThreadLongRunning
shutdown_report_mode: bool = False

mpv_allow_crashy_files: bool = False
mpv_allow_crashy_files_silently: bool = False

fake_petition_mode: bool = False

force_idle_mode: bool = False
thumbnail_debug_mode: bool = False
autocomplete_delay_mode: bool = False

blurhash_mode: bool = False

shutdown_complete: bool = False
restart: bool = False

twisted_is_broke: bool = False
twisted_is_broke_exception = None

dirty_object_lock = threading.Lock()
client_busy = threading.Lock()
server_busy = threading.Lock()
