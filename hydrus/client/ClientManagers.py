import collections
import threading
import typing

from qtpy import QtGui as QG

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusGlobals as HG

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientData

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
            
        
        return QG.QPixmap( width, height )
        
    
    def GetQtImageFromBuffer( self, width, height, depth, data ):
        
        if isinstance( data, memoryview ) and not data.c_contiguous:
            
            data = data.copy()
            
        
        qt_image_format = self._GetQtImageFormat( depth )
        
        bytes_per_line = ( depth // 8 ) * width
        
        # no copy here
        qt_image = QG.QImage( data, width, height, bytes_per_line, qt_image_format )
        
        # cheeky solution here
        # the QImage init does not take python ownership of the data, so if it gets garbage collected, we crash
        # so, add a beardy python ref to it, no problem :^)
        # other anwser here is to do a .copy, but this can be a _little_ expensive and eats memory
        qt_image.python_data_reference = data
        
        return qt_image
        
    
    def GetQtPixmapFromBuffer( self, width, height, depth, data ):
        
        if isinstance( data, memoryview ) and not data.c_contiguous:
            
            data = data.copy()
            
        
        qt_image_format = self._GetQtImageFormat( depth )
        
        bytes_per_line = ( depth // 8 ) * width
        
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
        
    
    def _GenerateViewsRow( self, canvas_type, view_timestamp, viewtime_delta ):
        
        new_options = HG.client_controller.new_options
        
        result_views_delta = 0
        result_viewtime_delta = 0
        
        do_it = True
        
        if canvas_type == CC.CANVAS_PREVIEW:
            
            viewtime_min = new_options.GetNoneableInteger( 'file_viewing_statistics_preview_min_time' )
            viewtime_max = new_options.GetNoneableInteger( 'file_viewing_statistics_preview_max_time' )
            
        elif canvas_type in CC.CANVAS_MEDIA_VIEWER_TYPES:
            
            viewtime_min = new_options.GetNoneableInteger( 'file_viewing_statistics_media_min_time' )
            viewtime_max = new_options.GetNoneableInteger( 'file_viewing_statistics_media_max_time' )
            
            if canvas_type == CC.CANVAS_MEDIA_VIEWER_DUPLICATES and not new_options.GetBoolean( 'file_viewing_statistics_active_on_dupe_filter' ):
                
                canvas_type = CC.CANVAS_MEDIA_VIEWER
                
                do_it = False
                
            
        
        if do_it:
            
            # if a cap on max viewtime, cap it
            if viewtime_max is not None:
                
                viewtime_delta = min( viewtime_delta, viewtime_max )
                
            
            # if a min on viewtime, then maybe don't do anything
            if viewtime_min is None or viewtime_delta >= viewtime_min:
                
                result_views_delta = 1
                result_viewtime_delta = viewtime_delta
                
            
        
        return ( canvas_type, ( view_timestamp, result_views_delta, result_viewtime_delta ) )
        
    
    def _RowMakesChanges( self, row ):
        
        ( view_timestamp, views_delta, viewtime_delta ) = row
        
        return views_delta != 0 or viewtime_delta != 0
        
    
    def _PubSubRow( self, hash, canvas_type, row ):
        
        ( view_timestamp, views_delta, viewtime_delta ) = row
        
        pubsub_row = ( hash, canvas_type, view_timestamp, views_delta, viewtime_delta )
        
        content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILE_VIEWING_STATS, HC.CONTENT_UPDATE_ADD, pubsub_row )
        
        service_keys_to_content_updates = { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : [ content_update ] }
        
        HG.client_controller.pub( 'content_updates_data', service_keys_to_content_updates )
        HG.client_controller.pub( 'content_updates_gui', service_keys_to_content_updates )
        
    
    def Flush( self ):
        
        with self._lock:
            
            if len( self._pending_updates ) > 0:
                
                content_updates = []
                
                for ( ( hash, canvas_type ), ( view_timestamp, views_delta, viewtime_delta ) ) in self._pending_updates.items():
                    
                    row = ( hash, canvas_type, view_timestamp, views_delta, viewtime_delta )
                    
                    content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILE_VIEWING_STATS, HC.CONTENT_UPDATE_ADD, row )
                    
                    content_updates.append( content_update )
                    
                
                service_keys_to_content_updates = { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : content_updates }
                
                # non-synchronous, non-publishing
                self._controller.Write( 'content_updates', service_keys_to_content_updates, publish_content_updates = False )
                
                self._pending_updates = {}
                
            
        
    
    def FinishViewing( self, hash, canvas_type, view_timestamp, viewtime_delta ):
        
        if not HG.client_controller.new_options.GetBoolean( 'file_viewing_statistics_active' ):
            
            return
            
        
        with self._lock:
            
            ( canvas_type, row ) = self._GenerateViewsRow( canvas_type, view_timestamp, viewtime_delta )
            
            if not self._RowMakesChanges( row ):
                
                return
                
            
            key = ( hash, canvas_type )
            
            if key not in self._pending_updates:
                
                self._pending_updates[ key ] = row
                
            else:
                
                ( view_timestamp, views_delta, viewtime_delta ) = row
                
                ( existing_view_timestamp, existing_views_delta, existing_viewtime_delta ) = self._pending_updates[ key ]
                
                self._pending_updates[ key ] = ( max( view_timestamp, existing_view_timestamp ), existing_views_delta + views_delta, existing_viewtime_delta + viewtime_delta )
                
            
        
        self._PubSubRow( hash, canvas_type, row )
        
    
    def REPEATINGFlush( self ):
        
        self.Flush()
        
    
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
            
        
    
