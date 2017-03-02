import threading

controller = None
client_controller = None
server_controller = None
test_controller = None
view_shutdown = False
model_shutdown = False

db_report_mode = False
db_profile_mode = False
pubsub_profile_mode = False
force_idle_mode = False
server_busy = False

do_idle_shutdown_work = False
shutdown_complete = False
restart = False
emergency_exit = False

do_not_catch_char_hook = False

dirty_object_lock = threading.Lock()
