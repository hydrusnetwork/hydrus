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
    

controller: typing.Optional[ "HydrusController.HydrusController" ] = None

# TODO: move the client, server, and any test-specific garbage to the new module Globals mate, and/or the controller objects themselves

started_shutdown = False
view_shutdown = False
model_shutdown = False

server_action = 'start'

db_journal_mode = 'WAL'
no_db_temp_files = False

boot_debug = False

db_cache_size = 256
db_transaction_commit_period = 30

# if this is set to 1, transactions are not immediately synced to the journal so multiple can be undone following a power-loss
# if set to 2, all transactions are synced, so once a new one starts you know the last one is on disk
# corruption cannot occur either way, but since we have multiple ATTACH dbs with diff journals, let's not mess around when power-cut during heavy file import or w/e
db_synchronous = 2

import_folders_running = False
export_folders_running = False

boot_with_network_traffic_paused_command_line = False

db_profile_min_job_time_ms = 16
callto_profile_min_job_time_ms = 10
server_profile_min_job_time_ms = 10
menu_profile_min_job_time_ms = 16
pubsub_profile_min_job_time_ms = 5
ui_timer_profile_min_job_time_ms = 5

macos_antiflicker_test = False

canvas_tile_outline_mode = False

db_ui_hang_relief_mode = False
callto_report_mode = False
db_report_mode = False
file_report_mode = False
file_sort_report_mode = False
media_load_report_mode = False
gui_report_mode = False
shortcut_report_mode = False
cache_report_mode = False
subprocess_report_mode = False
subscription_report_mode = False
hover_window_report_mode = False
file_import_report_mode = False
phash_generation_report_mode = False
network_report_mode = False
network_report_mode_silent = False
pubsub_report_mode = False
daemon_report_mode = False
mpv_report_mode = False

fake_petition_mode = False

force_idle_mode = False
thumbnail_debug_mode = False
autocomplete_delay_mode = False

blurhash_mode = False

do_idle_shutdown_work = False
shutdown_complete = False
restart = False

twisted_is_broke = False
twisted_is_broke_exception = None

last_mouse_click_button = None

dirty_object_lock = threading.Lock()
client_busy = threading.Lock()
server_busy = threading.Lock()
