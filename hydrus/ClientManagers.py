from . import ClientConstants as CC
from . import ClientData
from . import ClientSearch
from . import ClientServices
from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusExceptions
from . import HydrusGlobals as HG
from . import HydrusTags
import random
import threading
import collections
import traceback
import typing
from qtpy import QtGui as QG

# now let's fill out grandparents
def BuildServiceKeysToChildrenToParents( service_keys_to_simple_children_to_parents ):
    
    # important thing here, and reason why it is recursive, is because we want to preserve the parent-grandparent interleaving in list order
    def AddParentsAndGrandparents( simple_children_to_parents, this_childs_parents, parents ):
        
        for parent in parents:
            
            if parent not in this_childs_parents:
                
                this_childs_parents.append( parent )
                
            
            # this parent has its own parents, so the child should get those as well
            if parent in simple_children_to_parents:
                
                grandparents = simple_children_to_parents[ parent ]
                
                AddParentsAndGrandparents( simple_children_to_parents, this_childs_parents, grandparents )
                
            
        
    
    service_keys_to_children_to_parents = collections.defaultdict( HydrusData.default_dict_list )
    
    for ( service_key, simple_children_to_parents ) in service_keys_to_simple_children_to_parents.items():
        
        children_to_parents = service_keys_to_children_to_parents[ service_key ]
        
        for ( child, parents ) in list( simple_children_to_parents.items() ):
            
            this_childs_parents = children_to_parents[ child ]
            
            AddParentsAndGrandparents( simple_children_to_parents, this_childs_parents, parents )
            
        
    
    return service_keys_to_children_to_parents
    
def BuildServiceKeysToSimpleChildrenToParents( service_keys_to_pairs_flat ):
    
    service_keys_to_simple_children_to_parents = collections.defaultdict( HydrusData.default_dict_set )
    
    for ( service_key, pairs ) in service_keys_to_pairs_flat.items():
        
        service_keys_to_simple_children_to_parents[ service_key ] = BuildSimpleChildrenToParents( pairs )
        
    
    return service_keys_to_simple_children_to_parents
    
# take pairs, make dict of child -> parents while excluding loops
# no grandparents here
def BuildSimpleChildrenToParents( pairs ):
    
    simple_children_to_parents = HydrusData.default_dict_set()
    
    for ( child, parent ) in pairs:
        
        if child == parent:
            
            continue
            
        
        if parent in simple_children_to_parents and LoopInSimpleChildrenToParents( simple_children_to_parents, child, parent ):
            
            continue
            
        
        simple_children_to_parents[ child ].add( parent )
        
    
    return simple_children_to_parents
    
def CollapseTagSiblingPairs( groups_of_pairs ):
    
    # This now takes 'groups' of pairs in descending order of precedence
    
    # This allows us to mandate that local tags take precedence
    
    # a pair is invalid if:
    # it causes a loop (a->b, b->c, c->a)
    # there is already a relationship for the 'bad' sibling (a->b, a->c)
    
    valid_chains = {}
    
    for pairs in groups_of_pairs:
        
        pairs = list( pairs )
        
        pairs.sort()
        
        for ( bad, good ) in pairs:
            
            if bad == good:
                
                # a->a is a loop!
                
                continue
                
            
            if bad not in valid_chains:
                
                we_have_a_loop = False
                
                current_best = good
                
                while current_best in valid_chains:
                    
                    current_best = valid_chains[ current_best ]
                    
                    if current_best == bad:
                        
                        we_have_a_loop = True
                        
                        break
                        
                    
                
                if not we_have_a_loop:
                    
                    valid_chains[ bad ] = good
                    
                
            
        
    
    # now we collapse the chains, turning:
    # a->b, b->c ... e->f
    # into
    # a->f, b->f ... e->f
    
    siblings = {}
    
    for ( bad, good ) in list( valid_chains.items() ):
        
        # given a->b, want to find f
        
        if good in siblings:
            
            # f already calculated and added
            
            best = siblings[ good ]
            
        else:
            
            # we don't know f for this chain, so let's figure it out
            
            current_best = good
            
            while current_best in valid_chains:
                
                current_best = valid_chains[ current_best ] # pursue endpoint f
                
            
            best = current_best
            
        
        # add a->f
        siblings[ bad ] = best
        
    
    return siblings
    
def DeLoopTagSiblingPairs( groups_of_pairs ):
    
    pass
    
def LoopInSimpleChildrenToParents( simple_children_to_parents, child, parent ):
    
    potential_loop_paths = { parent }
    
    while True:
        
        new_potential_loop_paths = set()
        
        for potential_loop_path in potential_loop_paths:
            
            if potential_loop_path in simple_children_to_parents:
                
                new_potential_loop_paths.update( simple_children_to_parents[ potential_loop_path ] )
                
            
        
        potential_loop_paths = new_potential_loop_paths
        
        if child in potential_loop_paths:
            
            return True
            
        elif len( potential_loop_paths ) == 0:
            
            return False
            
        
    
class BitmapManager( object ):
    
    MAX_MEMORY_ALLOWANCE = 512 * 1024 * 1024
    
    def __init__( self, controller ):
        
        self._controller = controller
        
        self._media_background_pixmap_path = None
        self._media_background_pixmap = None
        
    
    def _GetQtImageFormat( self, depth ):
        
        if depth == 24:
            
            return QG.QImage.Format_RGB888
            
        elif depth == 32:

            return QG.QImage.Format_RGBA8888
            
        
    
    def GetQtImage( self, width, height, depth = 24 ):
        
        if width < 0:
            
            width = 20
            
        
        if height < 0:
            
            height = 20
            
        
        qt_image_format = self._GetQtImageFormat( depth )
        
        return QG.QImage( width, height, qt_image_format )
        
    
    def GetQtPixmap( self, width, height ):
        
        if width < 0:
            
            width = 20
            
        
        if height < 0:
            
            height = 20
            
        
        key = ( width, height )
        
        return QG.QPixmap( width, height )
        
    
    def GetQtImageFromBuffer( self, width, height, depth, data ):
        
        qt_image_format = self._GetQtImageFormat( depth )
        
        bytes_per_line = ( depth / 8 ) * width
        
        # no copy here
        qt_image = QG.QImage( data, width, height, bytes_per_line, qt_image_format )
        
        # cheeky solution here
        # the QImage init does not take python ownership of the data, so if it gets garbage collected, we crash
        # so, add a beardy python ref to it, no problem :^)
        # other anwser here is to do a .copy, but this can be a _little_ expensive and eats memory
        qt_image.python_data_reference = data
        
        return qt_image
        
    
    def GetQtPixmapFromBuffer( self, width, height, depth, data ):
        
        qt_image_format = self._GetQtImageFormat( depth )
        
        bytes_per_line = ( depth / 8 ) * width
        
        # no copy, no new data allocated
        qt_image = QG.QImage( data, width, height, bytes_per_line, qt_image_format )
        
        # _should_ be a safe copy of the hot data
        pixmap = QG.QPixmap.fromImage( qt_image )
        
        return pixmap
        
    
    def GetMediaBackgroundPixmap( self ):
        
        pixmap_path = self._controller.new_options.GetNoneableString( 'media_background_bmp_path' )
        
        if pixmap_path != self._media_background_pixmap_path:
            
            self._media_background_pixmap_path = pixmap_path
            
            try:
                
                self._media_background_pixmap = QG.QPixmap( self._media_background_pixmap_path )
                
            except Exception as e:
                
                self._media_background_pixmap = None
                
                HydrusData.ShowText( 'Loading a bmp caused an error!' )
                
                HydrusData.ShowException( e )
                
                return None
                
            
        
        return self._media_background_pixmap
        
    
class FileViewingStatsManager( object ):
    
    def __init__( self, controller ):
        
        self._controller = controller
        
        self._lock = threading.Lock()
        
        self._pending_updates = {}
        
        self._last_update = HydrusData.GetNow()
        
        self._my_flush_job = self._controller.CallRepeating( 5, 60, self.REPEATINGFlush )
        
    
    def _GenerateViewsRow( self, viewtype, viewtime_delta ):
        
        new_options = HG.client_controller.new_options
        
        preview_views_delta = 0
        preview_viewtime_delta = 0
        media_views_delta = 0
        media_viewtime_delta = 0
        
        if viewtype == 'preview':
            
            preview_min = new_options.GetNoneableInteger( 'file_viewing_statistics_preview_min_time' )
            preview_max = new_options.GetNoneableInteger( 'file_viewing_statistics_preview_max_time' )
            
            if preview_max is not None:
                
                viewtime_delta = min( viewtime_delta, preview_max )
                
            
            if preview_min is None or viewtime_delta >= preview_min:
                
                preview_views_delta = 1
                preview_viewtime_delta = viewtime_delta
                
            
        elif viewtype in ( 'media', 'media_duplicates_filter' ):
            
            do_it = True
            
            if viewtime_delta == 'media_duplicates_filter' and not new_options.GetBoolean( 'file_viewing_statistics_active_on_dupe_filter' ):
                
                do_it = False
                
            
            if do_it:
                
                media_min = new_options.GetNoneableInteger( 'file_viewing_statistics_media_min_time' )
                media_max = new_options.GetNoneableInteger( 'file_viewing_statistics_media_max_time' )
                
                if media_max is not None:
                    
                    viewtime_delta = min( viewtime_delta, media_max )
                    
                
                if media_min is None or viewtime_delta >= media_min:
                    
                    media_views_delta = 1
                    media_viewtime_delta = viewtime_delta
                    
                
            
        
        return ( preview_views_delta, preview_viewtime_delta, media_views_delta, media_viewtime_delta )
        
    
    def _PubSubRow( self, hash, row ):
        
        ( preview_views_delta, preview_viewtime_delta, media_views_delta, media_viewtime_delta ) = row
        
        pubsub_row = ( hash, preview_views_delta, preview_viewtime_delta, media_views_delta, media_viewtime_delta )
        
        content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILE_VIEWING_STATS, HC.CONTENT_UPDATE_ADD, pubsub_row )
        
        service_keys_to_content_updates = { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : [ content_update ] }
        
        HG.client_controller.pub( 'content_updates_data', service_keys_to_content_updates )
        HG.client_controller.pub( 'content_updates_gui', service_keys_to_content_updates )
        
    
    def REPEATINGFlush( self ):
        
        self.Flush()
        
    
    def Flush( self ):
        
        with self._lock:
            
            if len( self._pending_updates ) > 0:
                
                content_updates = []
                
                for ( hash, ( preview_views_delta, preview_viewtime_delta, media_views_delta, media_viewtime_delta ) ) in self._pending_updates.items():
                    
                    row = ( hash, preview_views_delta, preview_viewtime_delta, media_views_delta, media_viewtime_delta )
                    
                    content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILE_VIEWING_STATS, HC.CONTENT_UPDATE_ADD, row )
                    
                    content_updates.append( content_update )
                    
                
                service_keys_to_content_updates = { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : content_updates }
                
                # non-synchronous
                self._controller.Write( 'content_updates', service_keys_to_content_updates, do_pubsubs = False )
                
                self._pending_updates = {}
                
            
        
    
    def FinishViewing( self, viewtype, hash, viewtime_delta ):
        
        if not HG.client_controller.new_options.GetBoolean( 'file_viewing_statistics_active' ):
            
            return
            
        
        with self._lock:
            
            row = self._GenerateViewsRow( viewtype, viewtime_delta )
            
            if hash not in self._pending_updates:
                
                self._pending_updates[ hash ] = row
                
            else:
                
                ( preview_views_delta, preview_viewtime_delta, media_views_delta, media_viewtime_delta ) = row
                
                ( existing_preview_views_delta, existing_preview_viewtime_delta, existing_media_views_delta, existing_media_viewtime_delta ) = self._pending_updates[ hash ]
                
                self._pending_updates[ hash ] = ( existing_preview_views_delta + preview_views_delta, existing_preview_viewtime_delta + preview_viewtime_delta, existing_media_views_delta + media_views_delta, existing_media_viewtime_delta + media_viewtime_delta )
                
            
        
        self._PubSubRow( hash, row )
        

class ServicesManager( object ):
    
    def __init__( self, controller ):
        
        self._controller = controller
        
        self._lock = threading.Lock()
        self._keys_to_services: typing.Dict[ bytes, ClientServices.Service ] = {}
        self._services_sorted: typing.List( ClientServices.Service ) = []
        
        self.RefreshServices()
        
        self._controller.sub( self, 'RefreshServices', 'notify_new_services_data' )
        
    
    def _GetService( self, service_key: bytes ):
        
        try:
            
            return self._keys_to_services[ service_key ]
            
        except KeyError:
            
            raise HydrusExceptions.DataMissing( 'That service was not found!' )
            
        
    
    def _SetServices( self, services: typing.List[ ClientServices.Service ] ):
        
        self._keys_to_services = { service.GetServiceKey() : service for service in services }
        
        self._keys_to_services[ CC.TEST_SERVICE_KEY ] = ClientServices.GenerateService( CC.TEST_SERVICE_KEY, HC.TEST_SERVICE, 'test service' )
        
        key = lambda s: s.GetName()
        
        self._services_sorted = list( services )
        self._services_sorted.sort( key = key )
        
    
    def Filter( self, service_keys: typing.List[ bytes ], desired_types: typing.List[ int ] ):
        
        with self._lock:
            
            filtered_service_keys = [ service_key for service_key in service_keys if service_key in self._keys_to_services and self._keys_to_services[ service_key ].GetServiceType() in desired_types ]
            
            return filtered_service_keys
            
        
    
    def FilterValidServiceKeys( self, service_keys: typing.List[ bytes ] ):
        
        with self._lock:
            
            filtered_service_keys = [ service_key for service_key in service_keys if service_key in self._keys_to_services ]
            
            return filtered_service_keys
            
        
    
    def GetName( self, service_key: bytes ):
        
        with self._lock:
            
            service = self._GetService( service_key )
            
            return service.GetName()
            
        
    
    def GetService( self, service_key: bytes ):
        
        with self._lock:
            
            return self._GetService( service_key )
            
        
    
    def GetServiceType( self, service_key: bytes ):
        
        with self._lock:
            
            return self._GetService( service_key ).GetServiceType()
            
        
    
    def GetServiceKeyFromName( self, allowed_types: typing.List[ int ], service_name: str ):
        
        with self._lock:
            
            for service in self._services_sorted:
                
                if service.GetServiceType() in allowed_types and service.GetName() == service_name:
                    
                    return service.GetServiceKey()
                    
                
            
            raise HydrusExceptions.DataMissing()
            
        
    
    def GetServiceKeys( self, desired_types: typing.List[ int ] = HC.ALL_SERVICES ):
        
        with self._lock:
            
            filtered_service_keys = [ service_key for ( service_key, service ) in self._keys_to_services.items() if service.GetServiceType() in desired_types ]
            
            return filtered_service_keys
            
        
    
    def GetServices( self, desired_types: typing.List[ int ] = HC.ALL_SERVICES, randomised: bool = False ):
        
        with self._lock:
            
            services = []
            
            for desired_type in desired_types:
                
                services.extend( [ service for service in self._services_sorted if service.GetServiceType() == desired_type ] )
                
            
            if randomised:
                
                random.shuffle( services )
                
            
            return services
            
        
    
    def RefreshServices( self ):
        
        with self._lock:
            
            services = self._controller.Read( 'services' )
            
            self._SetServices( services )
            
        
    
    def ServiceExists( self, service_key: bytes ):
        
        with self._lock:
            
            return service_key in self._keys_to_services
            
        
    
class TagParentsManager( object ):
    
    def __init__( self, controller ):
        
        self._controller = controller
        
        self._dirty = False
        self._refresh_job = None
        
        self._service_keys_to_children_to_parents = collections.defaultdict( HydrusData.default_dict_list )
        
        self._RefreshParents()
        
        self._lock = threading.Lock()
        
        self._controller.sub( self, 'NotifyNewParents', 'notify_new_parents' )
        
    
    def _RefreshParents( self ):
        
        service_keys_to_statuses_to_pairs = self._controller.Read( 'tag_parents' )
        
        # first collapse siblings
        
        siblings_manager = self._controller.tag_siblings_manager
        
        collapsed_service_keys_to_statuses_to_pairs = collections.defaultdict( HydrusData.default_dict_set )
        
        for ( service_key, statuses_to_pairs ) in service_keys_to_statuses_to_pairs.items():
            
            if service_key == CC.COMBINED_TAG_SERVICE_KEY:
                
                continue
                
            
            for ( status, pairs ) in statuses_to_pairs.items():
                
                pairs = siblings_manager.CollapsePairs( service_key, pairs )
                
                collapsed_service_keys_to_statuses_to_pairs[ service_key ][ status ] = pairs
                
            
        
        # now collapse current and pending
        
        service_keys_to_pairs_flat = HydrusData.default_dict_set()
        
        for ( service_key, statuses_to_pairs ) in collapsed_service_keys_to_statuses_to_pairs.items():
            
            pairs_flat = statuses_to_pairs[ HC.CONTENT_STATUS_CURRENT ].union( statuses_to_pairs[ HC.CONTENT_STATUS_PENDING ] )
            
            service_keys_to_pairs_flat[ service_key ] = pairs_flat
            
        
        # now create the combined tag service
        
        combined_pairs_flat = set()
        
        for pairs_flat in service_keys_to_pairs_flat.values():
            
            combined_pairs_flat.update( pairs_flat )
            
        
        service_keys_to_pairs_flat[ CC.COMBINED_TAG_SERVICE_KEY ] = combined_pairs_flat
        
        #
        
        service_keys_to_simple_children_to_parents = BuildServiceKeysToSimpleChildrenToParents( service_keys_to_pairs_flat )
        
        self._service_keys_to_children_to_parents = BuildServiceKeysToChildrenToParents( service_keys_to_simple_children_to_parents )
        
    
    def ExpandPredicates( self, service_key, predicates, service_strict = False ):
        
        if not service_strict and self._controller.new_options.GetBoolean( 'apply_all_parents_to_all_services' ):
            
            service_key = CC.COMBINED_TAG_SERVICE_KEY
            
        
        results = []
        
        with self._lock:
            
            for predicate in predicates:
                
                results.append( predicate )
                
                if predicate.GetType() == ClientSearch.PREDICATE_TYPE_TAG:
                    
                    tag = predicate.GetValue()
                    
                    parents = self._service_keys_to_children_to_parents[ service_key ][ tag ]
                    
                    for parent in parents:
                        
                        parent_predicate = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_PARENT, parent )
                        
                        results.append( parent_predicate )
                        
                    
                
            
            return results
            
        
    
    def ExpandTags( self, service_key, tags, service_strict = False ):
        
        if not service_strict and self._controller.new_options.GetBoolean( 'apply_all_parents_to_all_services' ):
            
            service_key = CC.COMBINED_TAG_SERVICE_KEY
            
        
        with self._lock:
            
            tags_results = set( tags )
            
            for tag in tags:
                
                tags_results.update( self._service_keys_to_children_to_parents[ service_key ][ tag ] )
                
            
            return tags_results
            
        
    
    def GetParents( self, service_key, tag, service_strict = False ):
        
        if not service_strict and self._controller.new_options.GetBoolean( 'apply_all_parents_to_all_services' ):
            
            service_key = CC.COMBINED_TAG_SERVICE_KEY
            
        
        with self._lock:
            
            return self._service_keys_to_children_to_parents[ service_key ][ tag ]
            
        
    
    def NotifyNewParents( self ):
        
        with self._lock:
            
            self._dirty = True
            
            if self._refresh_job is not None:
                
                self._refresh_job.Cancel()
                
            
            self._refresh_job = self._controller.CallLater( 8.0, self.RefreshParentsIfDirty )
            
        
    
    def RefreshParentsIfDirty( self ):
        
        with self._lock:
            
            if self._dirty:
                
                self._RefreshParents()
                
                self._dirty = False
                
            
        
    
class TagSiblingsManager( object ):
    
    def __init__( self, controller ):
        
        self._controller = controller
        
        self._dirty = False
        self._refresh_job = None
        
        self._service_keys_to_siblings = collections.defaultdict( dict )
        self._service_keys_to_reverse_lookup = collections.defaultdict( dict )
        
        self._RefreshSiblings()
        
        self._lock = threading.Lock()
        
        self._controller.sub( self, 'NotifyNewSiblings', 'notify_new_siblings_data' )
        
    
    def _CollapseTags( self, service_key, tags ):
    
        siblings = self._service_keys_to_siblings[ service_key ]
        
        return { siblings[ tag ] if tag in siblings else tag for tag in tags }
        
    
    def _RefreshSiblings( self ):
        
        self._service_keys_to_siblings = collections.defaultdict( dict )
        self._service_keys_to_reverse_lookup = collections.defaultdict( dict )
        
        local_tags_pairs = set()
        
        tag_repo_pairs = set()
        
        service_keys_to_statuses_to_pairs = self._controller.Read( 'tag_siblings' )
        
        for ( service_key, statuses_to_pairs ) in service_keys_to_statuses_to_pairs.items():
            
            all_pairs = statuses_to_pairs[ HC.CONTENT_STATUS_CURRENT ].union( statuses_to_pairs[ HC.CONTENT_STATUS_PENDING ] )
            
            service = self._controller.services_manager.GetService( service_key )
            
            if service.GetServiceType() == HC.LOCAL_TAG:
                
                local_tags_pairs = set( all_pairs )
                
            else:
                
                tag_repo_pairs.update( all_pairs )
                
            
            siblings = CollapseTagSiblingPairs( [ all_pairs ] )
            
            self._service_keys_to_siblings[ service_key ] = siblings
            
            reverse_lookup = collections.defaultdict( list )
            
            for ( bad, good ) in siblings.items():
                
                reverse_lookup[ good ].append( bad )
                
            
            self._service_keys_to_reverse_lookup[ service_key ] = reverse_lookup
            
        
        combined_siblings = CollapseTagSiblingPairs( [ local_tags_pairs, tag_repo_pairs ] )
        
        self._service_keys_to_siblings[ CC.COMBINED_TAG_SERVICE_KEY ] = combined_siblings
        
        combined_reverse_lookup = collections.defaultdict( list )
        
        for ( bad, good ) in combined_siblings.items():
            
            combined_reverse_lookup[ good ].append( bad )
            
        
        self._service_keys_to_reverse_lookup[ CC.COMBINED_TAG_SERVICE_KEY ] = combined_reverse_lookup
        
    
    def CollapsePredicates( self, service_key, predicates, service_strict = False ):
        
        if not service_strict and self._controller.new_options.GetBoolean( 'apply_all_siblings_to_all_services' ):
            
            service_key = CC.COMBINED_TAG_SERVICE_KEY
            
        
        with self._lock:
            
            siblings = self._service_keys_to_siblings[ service_key ]
            
            results = [ predicate for predicate in predicates if predicate.GetType() != ClientSearch.PREDICATE_TYPE_TAG ]
            
            tag_predicates = [ predicate for predicate in predicates if predicate.GetType() == ClientSearch.PREDICATE_TYPE_TAG ]
            
            tags_to_predicates = {predicate.GetValue() : predicate for predicate in predicates if predicate.GetType() == ClientSearch.PREDICATE_TYPE_TAG}
            
            tags = list( tags_to_predicates.keys() )
            
            tags_to_include_in_results = set()
            
            for tag in tags:
                
                if tag in siblings:
                    
                    old_tag = tag
                    old_predicate = tags_to_predicates[ old_tag ]
                    
                    new_tag = siblings[ old_tag ]
                    
                    if new_tag not in tags_to_predicates:
                        
                        ( old_pred_type, old_value, old_inclusive ) = old_predicate.GetInfo()
                        
                        new_predicate = ClientSearch.Predicate( old_pred_type, new_tag, old_inclusive )
                        
                        tags_to_predicates[ new_tag ] = new_predicate
                        
                        tags_to_include_in_results.add( new_tag )
                        
                    
                    new_predicate = tags_to_predicates[ new_tag ]
                    
                    new_predicate.AddCounts( old_predicate )
                    
                else:
                    
                    tags_to_include_in_results.add( tag )
                    
                
            
            results.extend( [ tags_to_predicates[ tag ] for tag in tags_to_include_in_results ] )
            
            return results
            
        
    
    def CollapsePairs( self, service_key, pairs, service_strict = False ):
        
        if not service_strict and self._controller.new_options.GetBoolean( 'apply_all_siblings_to_all_services' ):
            
            service_key = CC.COMBINED_TAG_SERVICE_KEY
            
        
        with self._lock:
            
            siblings = self._service_keys_to_siblings[ service_key ]
            
            result = set()
            
            for ( a, b ) in pairs:
                
                if a in siblings:
                    
                    a = siblings[ a ]
                    
                
                if b in siblings:
                    
                    b = siblings[ b ]
                    
                
                result.add( ( a, b ) )
                
            
            return result
            
        
    
    def CollapseStatusesToTags( self, service_key, statuses_to_tags, service_strict = False ):
        
        if not service_strict and self._controller.new_options.GetBoolean( 'apply_all_siblings_to_all_services' ):
            
            service_key = CC.COMBINED_TAG_SERVICE_KEY
            
        
        with self._lock:
            
            new_statuses_to_tags = HydrusData.default_dict_set()
            
            for ( status, tags ) in statuses_to_tags.items():
                
                new_statuses_to_tags[ status ] = self._CollapseTags( service_key, tags )
                
            
            return new_statuses_to_tags
            
        
    
    def CollapseTag( self, service_key, tag, service_strict = False ):
        
        if not service_strict and self._controller.new_options.GetBoolean( 'apply_all_siblings_to_all_services' ):
            
            service_key = CC.COMBINED_TAG_SERVICE_KEY
            
        
        with self._lock:
            
            siblings = self._service_keys_to_siblings[ service_key ]
            
            if tag in siblings:
                
                return siblings[ tag ]
                
            else:
                
                return tag
                
            
        
    
    def CollapseTags( self, service_key, tags, service_strict = False ):
        
        if not service_strict and self._controller.new_options.GetBoolean( 'apply_all_siblings_to_all_services' ):
            
            service_key = CC.COMBINED_TAG_SERVICE_KEY
            
        
        with self._lock:
            
            return self._CollapseTags( service_key, tags )
            
        
    
    def CollapseTagsToCount( self, service_key, tags_to_count, service_strict = False ):
        
        if not service_strict and self._controller.new_options.GetBoolean( 'apply_all_siblings_to_all_services' ):
            
            service_key = CC.COMBINED_TAG_SERVICE_KEY
            
        
        with self._lock:
            
            siblings = self._service_keys_to_siblings[ service_key ]
            
            results = collections.Counter()
            
            for ( tag, count ) in tags_to_count.items():
                
                if tag in siblings:
                    
                    tag = siblings[ tag ]
                    
                
                results[ tag ] += count
                
            
            return results
            
        
    
    def GetSibling( self, service_key, tag, service_strict = False ):
        
        if not service_strict and self._controller.new_options.GetBoolean( 'apply_all_siblings_to_all_services' ):
            
            service_key = CC.COMBINED_TAG_SERVICE_KEY
            
        
        with self._lock:
            
            siblings = self._service_keys_to_siblings[ service_key ]
            
            if tag in siblings:
                
                return siblings[ tag ]
                
            else:
                
                return None
                
            
        
    
    def GetAllSiblings( self, service_key, tag, service_strict = False ):
        
        if not service_strict and self._controller.new_options.GetBoolean( 'apply_all_siblings_to_all_services' ):
            
            service_key = CC.COMBINED_TAG_SERVICE_KEY
            
        
        with self._lock:
            
            siblings = self._service_keys_to_siblings[ service_key ]
            reverse_lookup = self._service_keys_to_reverse_lookup[ service_key ]
            
            if tag in siblings:
                
                best_tag = siblings[ tag ]
                
            elif tag in reverse_lookup:
                
                best_tag = tag
                
            else:
                
                return [ tag ]
                
            
            all_siblings = list( reverse_lookup[ best_tag ] )
            
            all_siblings.append( best_tag )
            
            return all_siblings
            
        
    
    def NotifyNewSiblings( self ):
        
        with self._lock:
            
            self._dirty = True
            
            if self._refresh_job is not None:
                
                self._refresh_job.Cancel()
                
            
            self._refresh_job = self._controller.CallLater( 8.0, self.RefreshSiblingsIfDirty )
            
        
    
    def RefreshSiblingsIfDirty( self ):
        
        with self._lock:
            
            if self._dirty:
                
                self._RefreshSiblings()
                
                self._dirty = False
                
                self._controller.pub( 'notify_new_tag_display_rules' )
                
            
        
    
class UndoManager( object ):
    
    def __init__( self, controller ):
        
        self._controller = controller
        
        self._commands = []
        self._inverted_commands = []
        self._current_index = 0
        
        self._lock = threading.Lock()
        
        self._controller.sub( self, 'Undo', 'undo' )
        self._controller.sub( self, 'Redo', 'redo' )
        
    
    def _FilterServiceKeysToContentUpdates( self, service_keys_to_content_updates ):
        
        filtered_service_keys_to_content_updates = {}
        
        for ( service_key, content_updates ) in service_keys_to_content_updates.items():
            
            filtered_content_updates = []
            
            for content_update in content_updates:
                
                ( data_type, action, row ) = content_update.ToTuple()
                
                if data_type == HC.CONTENT_TYPE_FILES:
                    
                    if action in ( HC.CONTENT_UPDATE_ADD, HC.CONTENT_UPDATE_DELETE, HC.CONTENT_UPDATE_UNDELETE, HC.CONTENT_UPDATE_RESCIND_PETITION, HC.CONTENT_UPDATE_ADVANCED ):
                        
                        continue
                        
                    
                elif data_type == HC.CONTENT_TYPE_MAPPINGS:
                    
                    if action in ( HC.CONTENT_UPDATE_RESCIND_PETITION, HC.CONTENT_UPDATE_ADVANCED ):
                        
                        continue
                        
                    
                else:
                    
                    continue
                    
                
                filtered_content_update = HydrusData.ContentUpdate( data_type, action, row )
                
                filtered_content_updates.append( filtered_content_update )
                
            
            if len( filtered_content_updates ) > 0:
                
                filtered_service_keys_to_content_updates[ service_key ] = filtered_content_updates
                
            
        
        return filtered_service_keys_to_content_updates
        
    
    def _InvertServiceKeysToContentUpdates( self, service_keys_to_content_updates ):
        
        inverted_service_keys_to_content_updates = {}
        
        for ( service_key, content_updates ) in service_keys_to_content_updates.items():
            
            inverted_content_updates = []
            
            for content_update in content_updates:
                
                ( data_type, action, row ) = content_update.ToTuple()
                
                inverted_row = row
                
                if data_type == HC.CONTENT_TYPE_FILES:
                    
                    if action == HC.CONTENT_UPDATE_ARCHIVE: inverted_action = HC.CONTENT_UPDATE_INBOX
                    elif action == HC.CONTENT_UPDATE_INBOX: inverted_action = HC.CONTENT_UPDATE_ARCHIVE
                    elif action == HC.CONTENT_UPDATE_PEND: inverted_action = HC.CONTENT_UPDATE_RESCIND_PEND
                    elif action == HC.CONTENT_UPDATE_RESCIND_PEND: inverted_action = HC.CONTENT_UPDATE_PEND
                    elif action == HC.CONTENT_UPDATE_PETITION: inverted_action = HC.CONTENT_UPDATE_RESCIND_PETITION
                    
                elif data_type == HC.CONTENT_TYPE_MAPPINGS:
                    
                    if action == HC.CONTENT_UPDATE_ADD: inverted_action = HC.CONTENT_UPDATE_DELETE
                    elif action == HC.CONTENT_UPDATE_DELETE: inverted_action = HC.CONTENT_UPDATE_ADD
                    elif action == HC.CONTENT_UPDATE_PEND: inverted_action = HC.CONTENT_UPDATE_RESCIND_PEND
                    elif action == HC.CONTENT_UPDATE_RESCIND_PEND: inverted_action = HC.CONTENT_UPDATE_PEND
                    elif action == HC.CONTENT_UPDATE_PETITION: inverted_action = HC.CONTENT_UPDATE_RESCIND_PETITION
                    
                
                inverted_content_update = HydrusData.ContentUpdate( data_type, inverted_action, inverted_row )
                
                inverted_content_updates.append( inverted_content_update )
                
            
            inverted_service_keys_to_content_updates[ service_key ] = inverted_content_updates
            
        
        return inverted_service_keys_to_content_updates
        
    
    def AddCommand( self, action, *args, **kwargs ):
        
        with self._lock:
            
            inverted_action = action
            inverted_args = args
            inverted_kwargs = kwargs
            
            if action == 'content_updates':
                
                ( service_keys_to_content_updates, ) = args
                
                service_keys_to_content_updates = self._FilterServiceKeysToContentUpdates( service_keys_to_content_updates )
                
                if len( service_keys_to_content_updates ) == 0: return
                
                inverted_service_keys_to_content_updates = self._InvertServiceKeysToContentUpdates( service_keys_to_content_updates )
                
                if len( inverted_service_keys_to_content_updates ) == 0: return
                
                inverted_args = ( inverted_service_keys_to_content_updates, )
                
            else: return
            
            self._commands = self._commands[ : self._current_index ]
            self._inverted_commands = self._inverted_commands[ : self._current_index ]
            
            self._commands.append( ( action, args, kwargs ) )
            
            self._inverted_commands.append( ( inverted_action, inverted_args, inverted_kwargs ) )
            
            self._current_index += 1
            
            self._controller.pub( 'notify_new_undo' )
            
        
    
    def GetUndoRedoStrings( self ):
        
        with self._lock:
            
            ( undo_string, redo_string ) = ( None, None )
            
            if self._current_index > 0:
                
                undo_index = self._current_index - 1
                
                ( action, args, kwargs ) = self._commands[ undo_index ]
                
                if action == 'content_updates':
                    
                    ( service_keys_to_content_updates, ) = args
                    
                    undo_string = 'undo ' + ClientData.ConvertServiceKeysToContentUpdatesToPrettyString( service_keys_to_content_updates )
                    
                
            
            if len( self._commands ) > 0 and self._current_index < len( self._commands ):
                
                redo_index = self._current_index
                
                ( action, args, kwargs ) = self._commands[ redo_index ]
                
                if action == 'content_updates':
                    
                    ( service_keys_to_content_updates, ) = args
                    
                    redo_string = 'redo ' + ClientData.ConvertServiceKeysToContentUpdatesToPrettyString( service_keys_to_content_updates )
                    
                
            
            return ( undo_string, redo_string )
            
        
    
    def Undo( self ):
        
        action = None
        
        with self._lock:
            
            if self._current_index > 0:
                
                self._current_index -= 1
                
                ( action, args, kwargs ) = self._inverted_commands[ self._current_index ]
                
        
        if action is not None:
            
            self._controller.WriteSynchronous( action, *args, **kwargs )
            
            self._controller.pub( 'notify_new_undo' )
            
        
    
    def Redo( self ):
        
        action = None
        
        with self._lock:
            
            if len( self._commands ) > 0 and self._current_index < len( self._commands ):
                
                ( action, args, kwargs ) = self._commands[ self._current_index ]
                
                self._current_index += 1
                
            
        
        if action is not None:
            
            self._controller.WriteSynchronous( action, *args, **kwargs )
            
            self._controller.pub( 'notify_new_undo' )
            
        
    
