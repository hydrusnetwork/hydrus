import HydrusPubSub

shutdown = False

pubsub = HydrusPubSub.HydrusPubSub()

is_first_start = False
is_db_updated = False

repos_changed = False
subs_changed = False
currently_processing_updates = False

db_profile_mode = False
