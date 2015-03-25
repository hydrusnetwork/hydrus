import HydrusNetworking
import HydrusPubSub

http = HydrusNetworking.HTTPConnectionManager()
shutdown = False

pubsub = HydrusPubSub.HydrusPubSub()

is_first_start = False
is_db_updated = False

repos_changed = False
subs_changed = False
