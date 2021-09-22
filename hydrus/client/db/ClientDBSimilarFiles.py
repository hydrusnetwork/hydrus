import collections
import random
import sqlite3
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusDBBase
from hydrus.core import HydrusGlobals as HG

from hydrus.client import ClientThreading
from hydrus.client.db import ClientDBFilesStorage
from hydrus.client.db import ClientDBModule
from hydrus.client.db import ClientDBServices

class ClientDBSimilarFiles( ClientDBModule.ClientDBModule ):
    
    def __init__( self, cursor: sqlite3.Cursor, modules_services: ClientDBServices.ClientDBMasterServices, modules_files_storage: ClientDBFilesStorage.ClientDBFilesStorage ):
        
        self.modules_services = modules_services
        self.modules_files_storage = modules_files_storage
        
        ClientDBModule.ClientDBModule.__init__( self, 'client similar files', cursor )
        
    
    def _AddLeaf( self, phash_id, phash ):
        
        result = self._Execute( 'SELECT phash_id FROM shape_vptree WHERE parent_id IS NULL;' ).fetchone()
        
        if result is None:
            
            parent_id = None
            
        else:
            
            ( root_node_phash_id, ) = result
            
            ancestors_we_are_inside = []
            ancestors_we_are_outside = []
            
            an_ancestor_is_unbalanced = False
            
            next_ancestor_id = root_node_phash_id
            
            while next_ancestor_id is not None:
                
                ancestor_id = next_ancestor_id
                
                ( ancestor_phash, ancestor_radius, ancestor_inner_id, ancestor_inner_population, ancestor_outer_id, ancestor_outer_population ) = self._Execute( 'SELECT phash, radius, inner_id, inner_population, outer_id, outer_population FROM shape_perceptual_hashes NATURAL JOIN shape_vptree WHERE phash_id = ?;', ( ancestor_id, ) ).fetchone()
                
                distance_to_ancestor = HydrusData.Get64BitHammingDistance( phash, ancestor_phash )
                
                if ancestor_radius is None or distance_to_ancestor <= ancestor_radius:
                    
                    ancestors_we_are_inside.append( ancestor_id )
                    ancestor_inner_population += 1
                    next_ancestor_id = ancestor_inner_id
                    
                    if ancestor_inner_id is None:
                        
                        self._Execute( 'UPDATE shape_vptree SET inner_id = ?, radius = ? WHERE phash_id = ?;', ( phash_id, distance_to_ancestor, ancestor_id ) )
                        
                        parent_id = ancestor_id
                        
                    
                else:
                    
                    ancestors_we_are_outside.append( ancestor_id )
                    ancestor_outer_population += 1
                    next_ancestor_id = ancestor_outer_id
                    
                    if ancestor_outer_id is None:
                        
                        self._Execute( 'UPDATE shape_vptree SET outer_id = ? WHERE phash_id = ?;', ( phash_id, ancestor_id ) )
                        
                        parent_id = ancestor_id
                        
                    
                
                if not an_ancestor_is_unbalanced and ancestor_inner_population + ancestor_outer_population > 16:
                    
                    larger = max( ancestor_inner_population, ancestor_outer_population )
                    smaller = min( ancestor_inner_population, ancestor_outer_population )
                    
                    if smaller / larger < 0.5:
                        
                        self._Execute( 'INSERT OR IGNORE INTO shape_maintenance_branch_regen ( phash_id ) VALUES ( ? );', ( ancestor_id, ) )
                        
                        # we only do this for the eldest ancestor, as the eventual rebalancing will affect all children
                        
                        an_ancestor_is_unbalanced = True
                        
                    
                
            
            self._ExecuteMany( 'UPDATE shape_vptree SET inner_population = inner_population + 1 WHERE phash_id = ?;', ( ( ancestor_id, ) for ancestor_id in ancestors_we_are_inside ) )
            self._ExecuteMany( 'UPDATE shape_vptree SET outer_population = outer_population + 1 WHERE phash_id = ?;', ( ( ancestor_id, ) for ancestor_id in ancestors_we_are_outside ) )
            
        
        radius = None
        inner_id = None
        inner_population = 0
        outer_id = None
        outer_population = 0
        
        self._Execute( 'INSERT OR REPLACE INTO shape_vptree ( phash_id, parent_id, radius, inner_id, inner_population, outer_id, outer_population ) VALUES ( ?, ?, ?, ?, ?, ?, ? );', ( phash_id, parent_id, radius, inner_id, inner_population, outer_id, outer_population ) )
        
    
    def _GenerateBranch( self, job_key, parent_id, phash_id, phash, children ):
        
        process_queue = collections.deque()
        
        process_queue.append( ( parent_id, phash_id, phash, children ) )
        
        insert_rows = []
        
        num_done = 0
        num_to_do = len( children ) + 1
        
        while len( process_queue ) > 0:
            
            job_key.SetVariable( 'popup_text_2', 'generating new branch -- ' + HydrusData.ConvertValueRangeToPrettyString( num_done, num_to_do ) )
            
            ( parent_id, phash_id, phash, children ) = process_queue.popleft()
            
            if len( children ) == 0:
                
                inner_id = None
                inner_population = 0
                
                outer_id = None
                outer_population = 0
                
                radius = None
                
            else:
                
                children = sorted( ( ( HydrusData.Get64BitHammingDistance( phash, child_phash ), child_id, child_phash ) for ( child_id, child_phash ) in children ) )
                
                median_index = len( children ) // 2
                
                median_radius = children[ median_index ][0]
                
                inner_children = [ ( child_id, child_phash ) for ( distance, child_id, child_phash ) in children if distance < median_radius ]
                radius_children = [ ( child_id, child_phash ) for ( distance, child_id, child_phash ) in children if distance == median_radius ]
                outer_children = [ ( child_id, child_phash ) for ( distance, child_id, child_phash ) in children if distance > median_radius ]
                
                if len( inner_children ) <= len( outer_children ):
                    
                    radius = median_radius
                    
                    inner_children.extend( radius_children )
                    
                else:
                    
                    radius = median_radius - 1
                    
                    outer_children.extend( radius_children )
                    
                
                inner_population = len( inner_children )
                outer_population = len( outer_children )
                
                ( inner_id, inner_phash ) = self._PopBestRootNode( inner_children ) #HydrusData.MedianPop( inner_children )
                
                if len( outer_children ) == 0:
                    
                    outer_id = None
                    
                else:
                    
                    ( outer_id, outer_phash ) = self._PopBestRootNode( outer_children ) #HydrusData.MedianPop( outer_children )
                    
                
            
            insert_rows.append( ( phash_id, parent_id, radius, inner_id, inner_population, outer_id, outer_population ) )
            
            if inner_id is not None:
                
                process_queue.append( ( phash_id, inner_id, inner_phash, inner_children ) )
                
            
            if outer_id is not None:
                
                process_queue.append( ( phash_id, outer_id, outer_phash, outer_children ) )
                
            
            num_done += 1
            
        
        job_key.SetVariable( 'popup_text_2', 'branch constructed, now committing' )
        
        self._ExecuteMany( 'INSERT OR REPLACE INTO shape_vptree ( phash_id, parent_id, radius, inner_id, inner_population, outer_id, outer_population ) VALUES ( ?, ?, ?, ?, ?, ?, ? );', insert_rows )
        
    
    def _GetInitialIndexGenerationDict( self ) -> dict:
        
        index_generation_dict = {}
        
        index_generation_dict[ 'external_master.shape_perceptual_hash_map' ] = [
            ( [ 'hash_id' ], False, 451 )
        ]
        
        index_generation_dict[ 'external_caches.shape_vptree' ] = [
            ( [ 'parent_id' ], False, 400 )
        ]
        
        return index_generation_dict
        
    
    def _GetInitialTableGenerationDict( self ) -> dict:
        
        return {
            'external_master.shape_perceptual_hashes' : ( 'CREATE TABLE IF NOT EXISTS {} ( phash_id INTEGER PRIMARY KEY, phash BLOB_BYTES UNIQUE );', 451 ),
            'external_master.shape_perceptual_hash_map' : ( 'CREATE TABLE IF NOT EXISTS {} ( phash_id INTEGER, hash_id INTEGER, PRIMARY KEY ( phash_id, hash_id ) );', 451 ),
            'external_caches.shape_vptree' : ( 'CREATE TABLE IF NOT EXISTS {} ( phash_id INTEGER PRIMARY KEY, parent_id INTEGER, radius INTEGER, inner_id INTEGER, inner_population INTEGER, outer_id INTEGER, outer_population INTEGER );', 400 ),
            'external_caches.shape_maintenance_branch_regen' : ( 'CREATE TABLE IF NOT EXISTS {} ( phash_id INTEGER PRIMARY KEY );', 400 ),
            'main.shape_search_cache' : ( 'CREATE TABLE IF NOT EXISTS {} ( hash_id INTEGER PRIMARY KEY, searched_distance INTEGER );', 451 )
        }
        
    
    def _GetPHashId( self, phash ):
        
        result = self._Execute( 'SELECT phash_id FROM shape_perceptual_hashes WHERE phash = ?;', ( sqlite3.Binary( phash ), ) ).fetchone()
        
        if result is None:
            
            self._Execute( 'INSERT INTO shape_perceptual_hashes ( phash ) VALUES ( ? );', ( sqlite3.Binary( phash ), ) )
            
            phash_id = self._GetLastRowId()
            
            self._AddLeaf( phash_id, phash )
            
        else:
            
            ( phash_id, ) = result
            
        
        return phash_id
        
    
    def _PopBestRootNode( self, node_rows ):
        
        if len( node_rows ) == 1:
            
            root_row = node_rows.pop()
            
            return root_row
            
        
        MAX_VIEWPOINTS = 256
        MAX_SAMPLE = 64
        
        if len( node_rows ) > MAX_VIEWPOINTS:
            
            viewpoints = random.sample( node_rows, MAX_VIEWPOINTS )
            
        else:
            
            viewpoints = node_rows
            
        
        if len( node_rows ) > MAX_SAMPLE:
            
            sample = random.sample( node_rows, MAX_SAMPLE )
            
        else:
            
            sample = node_rows
            
        
        final_scores = []
        
        for ( v_id, v_phash ) in viewpoints:
            
            views = sorted( ( HydrusData.Get64BitHammingDistance( v_phash, s_phash ) for ( s_id, s_phash ) in sample if v_id != s_id ) )
            
            # let's figure out the ratio of left_children to right_children, preferring 1:1, and convert it to a discrete integer score
            
            median_index = len( views ) // 2
            
            radius = views[ median_index ]
            
            num_left = len( [ 1 for view in views if view < radius ] )
            num_radius = len( [ 1 for view in views if view == radius ] )
            num_right = len( [ 1 for view in views if view > radius ] )
            
            if num_left <= num_right:
                
                num_left += num_radius
                
            else:
                
                num_right += num_radius
                
            
            smaller = min( num_left, num_right )
            larger = max( num_left, num_right )
            
            ratio = smaller / larger
            
            ratio_score = int( ratio * MAX_SAMPLE / 2 )
            
            # now let's calc the standard deviation--larger sd tends to mean less sphere overlap when searching
            
            mean_view = sum( views ) / len( views )
            squared_diffs = [ ( view - mean_view  ) ** 2 for view in views ]
            sd = ( sum( squared_diffs ) / len( squared_diffs ) ) ** 0.5
            
            final_scores.append( ( ratio_score, sd, v_id ) )
            
        
        final_scores.sort()
        
        # we now have a list like [ ( 11, 4.0, [id] ), ( 15, 3.7, [id] ), ( 15, 4.3, [id] ) ]
        
        ( ratio_gumpf, sd_gumpf, root_id ) = final_scores.pop()
        
        for ( i, ( v_id, v_phash ) ) in enumerate( node_rows ):
            
            if v_id == root_id:
                
                root_row = node_rows.pop( i )
                
                return root_row
                
            
        
    
    def _RegenerateBranch( self, job_key, phash_id ):
        
        job_key.SetVariable( 'popup_text_2', 'reviewing existing branch' )
        
        # grab everything in the branch
        
        ( parent_id, ) = self._Execute( 'SELECT parent_id FROM shape_vptree WHERE phash_id = ?;', ( phash_id, ) ).fetchone()
        
        cte_table_name = 'branch ( branch_phash_id )'
        initial_select = 'SELECT ?'
        recursive_select = 'SELECT phash_id FROM shape_vptree, branch ON parent_id = branch_phash_id'
        
        with_clause = 'WITH RECURSIVE ' + cte_table_name + ' AS ( ' + initial_select + ' UNION ALL ' +  recursive_select +  ')'
        
        unbalanced_nodes = self._Execute( with_clause + ' SELECT branch_phash_id, phash FROM branch, shape_perceptual_hashes ON phash_id = branch_phash_id;', ( phash_id, ) ).fetchall()
        
        # removal of old branch, maintenance schedule, and orphan phashes
        
        job_key.SetVariable( 'popup_text_2', HydrusData.ToHumanInt( len( unbalanced_nodes ) ) + ' leaves found--now clearing out old branch' )
        
        unbalanced_phash_ids = { p_id for ( p_id, p_h ) in unbalanced_nodes }
        
        self._ExecuteMany( 'DELETE FROM shape_vptree WHERE phash_id = ?;', ( ( p_id, ) for p_id in unbalanced_phash_ids ) )
        
        self._ExecuteMany( 'DELETE FROM shape_maintenance_branch_regen WHERE phash_id = ?;', ( ( p_id, ) for p_id in unbalanced_phash_ids ) )
        
        with self._MakeTemporaryIntegerTable( unbalanced_phash_ids, 'phash_id' ) as temp_phash_ids_table_name:
            
            useful_phash_ids = self._STS( self._Execute( 'SELECT phash_id FROM {} CROSS JOIN shape_perceptual_hash_map USING ( phash_id );'.format( temp_phash_ids_table_name ) ) )
            
        
        orphan_phash_ids = unbalanced_phash_ids.difference( useful_phash_ids )
        
        self._ExecuteMany( 'DELETE FROM shape_perceptual_hashes WHERE phash_id = ?;', ( ( p_id, ) for p_id in orphan_phash_ids ) )
        
        useful_nodes = [ row for row in unbalanced_nodes if row[0] in useful_phash_ids ]
        
        useful_population = len( useful_nodes )
        
        # now create the new branch, starting by choosing a new root and updating the parent's left/right reference to that
        
        if useful_population > 0:
            
            ( new_phash_id, new_phash ) = self._PopBestRootNode( useful_nodes ) #HydrusData.RandomPop( useful_nodes )
            
        else:
            
            new_phash_id = None
            
        
        if parent_id is not None:
            
            ( parent_inner_id, ) = self._Execute( 'SELECT inner_id FROM shape_vptree WHERE phash_id = ?;', ( parent_id, ) ).fetchone()
            
            if parent_inner_id == phash_id:
                
                query = 'UPDATE shape_vptree SET inner_id = ?, inner_population = ? WHERE phash_id = ?;'
                
            else:
                
                query = 'UPDATE shape_vptree SET outer_id = ?, outer_population = ? WHERE phash_id = ?;'
                
            
            self._Execute( query, ( new_phash_id, useful_population, parent_id ) )
            
        
        if useful_population > 0:
            
            self._GenerateBranch( job_key, parent_id, new_phash_id, new_phash, useful_nodes )
            
        
    
    def _RepairRepopulateTables( self, repopulate_table_names, cursor_transaction_wrapper: HydrusDBBase.DBCursorTransactionWrapper ):
        
        if 'external_caches.shape_vptree' in repopulate_table_names or 'external_caches.shape_maintenance_branch_regen' in repopulate_table_names:
            
            self.RegenerateTree()
            
        
    
    def AssociatePHashes( self, hash_id, phashes ):
        
        phash_ids = set()
        
        for phash in phashes:
            
            phash_id = self._GetPHashId( phash )
            
            phash_ids.add( phash_id )
            
        
        self._ExecuteMany( 'INSERT OR IGNORE INTO shape_perceptual_hash_map ( phash_id, hash_id ) VALUES ( ?, ? );', ( ( phash_id, hash_id ) for phash_id in phash_ids ) )
        
        if self._GetRowCount() > 0:
            
            self._Execute( 'REPLACE INTO shape_search_cache ( hash_id, searched_distance ) VALUES ( ?, ? );', ( hash_id, None ) )
            
        
        return phash_ids
        
    
    def DisassociatePHashes( self, hash_id, phash_ids ):
        
        self._ExecuteMany( 'DELETE FROM shape_perceptual_hash_map WHERE phash_id = ? AND hash_id = ?;', ( ( phash_id, hash_id ) for phash_id in phash_ids ) )
        
        useful_phash_ids = { phash for ( phash, ) in self._Execute( 'SELECT phash_id FROM shape_perceptual_hash_map WHERE phash_id IN ' + HydrusData.SplayListForDB( phash_ids ) + ';' ) }
        
        useless_phash_ids = phash_ids.difference( useful_phash_ids )
        
        self._ExecuteMany( 'INSERT OR IGNORE INTO shape_maintenance_branch_regen ( phash_id ) VALUES ( ? );', ( ( phash_id, ) for phash_id in useless_phash_ids ) )
        
    
    def FileIsInSystem( self, hash_id ):
        
        result = self._Execute( 'SELECT 1 FROM shape_search_cache WHERE hash_id = ?;', ( hash_id, ) ).fetchone()
        
        return result is not None
        
    
    def GetMaintenanceStatus( self ):
        
        searched_distances_to_count = collections.Counter( dict( self._Execute( 'SELECT searched_distance, COUNT( * ) FROM shape_search_cache GROUP BY searched_distance;' ) ) )
        
        return searched_distances_to_count
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> typing.List[ typing.Tuple[ str, str ] ]:
        
        if HC.CONTENT_TYPE_HASH:
            
            return [
                ( 'shape_perceptual_hash_map', 'hash_id' ),
                ( 'shape_search_cache', 'hash_id' )
            ]
            
        
        return []
        
    
    def MaintainTree( self, maintenance_mode = HC.MAINTENANCE_FORCED, job_key = None, stop_time = None ):
        
        time_started = HydrusData.GetNow()
        pub_job_key = False
        job_key_pubbed = False
        
        if job_key is None:
            
            job_key = ClientThreading.JobKey( cancellable = True )
            
            pub_job_key = True
            
        
        try:
            
            job_key.SetStatusTitle( 'similar files metadata maintenance' )
            
            rebalance_phash_ids = self._STL( self._Execute( 'SELECT phash_id FROM shape_maintenance_branch_regen;' ) )
            
            num_to_do = len( rebalance_phash_ids )
            
            while len( rebalance_phash_ids ) > 0:
                
                if pub_job_key and not job_key_pubbed and HydrusData.TimeHasPassed( time_started + 5 ):
                    
                    HG.client_controller.pub( 'modal_message', job_key )
                    
                    job_key_pubbed = True
                    
                
                ( i_paused, should_quit ) = job_key.WaitIfNeeded()
                
                should_stop = HG.client_controller.ShouldStopThisWork( maintenance_mode, stop_time = stop_time )
                
                if should_quit or should_stop:
                    
                    return
                    
                
                num_done = num_to_do - len( rebalance_phash_ids )
                
                text = 'rebalancing similar file metadata - ' + HydrusData.ConvertValueRangeToPrettyString( num_done, num_to_do )
                
                HG.client_controller.frame_splash_status.SetSubtext( text )
                job_key.SetVariable( 'popup_text_1', text )
                job_key.SetVariable( 'popup_gauge_1', ( num_done, num_to_do ) )
                
                with self._MakeTemporaryIntegerTable( rebalance_phash_ids, 'phash_id' ) as temp_table_name:
                    
                    # temp phashes to tree
                    ( biggest_phash_id, ) = self._Execute( 'SELECT phash_id FROM {} CROSS JOIN shape_vptree USING ( phash_id ) ORDER BY inner_population + outer_population DESC;'.format( temp_table_name ) ).fetchone()
                    
                
                self._RegenerateBranch( job_key, biggest_phash_id )
                
                rebalance_phash_ids = self._STL( self._Execute( 'SELECT phash_id FROM shape_maintenance_branch_regen;' ) )
                
            
        finally:
            
            job_key.SetVariable( 'popup_text_1', 'done!' )
            job_key.DeleteVariable( 'popup_gauge_1' )
            job_key.DeleteVariable( 'popup_text_2' ) # used in the regenbranch call
            
            job_key.Finish()
            
            job_key.Delete( 5 )
            
        
    
    def MaintenanceDue( self ):
        
        new_options = HG.client_controller.new_options
        
        if new_options.GetBoolean( 'maintain_similar_files_duplicate_pairs_during_idle' ):
            
            search_distance = new_options.GetInteger( 'similar_files_duplicate_pairs_search_distance' )
            
            ( count, ) = self._Execute( 'SELECT COUNT( * ) FROM ( SELECT 1 FROM shape_search_cache WHERE searched_distance IS NULL or searched_distance < ? LIMIT 100 );', ( search_distance, ) ).fetchone()
            
            if count >= 100:
                
                return True
                
            
        
        return False
        
    
    def RegenerateTree( self ):
        
        job_key = ClientThreading.JobKey()
        
        try:
            
            job_key.SetStatusTitle( 'regenerating similar file search data' )
            
            HG.client_controller.pub( 'modal_message', job_key )
            
            job_key.SetVariable( 'popup_text_1', 'purging search info of orphans' )
            
            ( current_files_table_name, deleted_files_table_name, pending_files_table_name, petitioned_files_table_name ) = ClientDBFilesStorage.GenerateFilesTableNames( self.modules_services.combined_local_file_service_id )
            
            self._Execute( 'DELETE FROM shape_perceptual_hash_map WHERE hash_id NOT IN ( SELECT hash_id FROM {} );'.format( current_files_table_name ) )
            
            job_key.SetVariable( 'popup_text_1', 'gathering all leaves' )
            
            self._Execute( 'DELETE FROM shape_vptree;' )
            
            all_nodes = self._Execute( 'SELECT phash_id, phash FROM shape_perceptual_hashes;' ).fetchall()
            
            job_key.SetVariable( 'popup_text_1', HydrusData.ToHumanInt( len( all_nodes ) ) + ' leaves found, now regenerating' )
            
            ( root_id, root_phash ) = self._PopBestRootNode( all_nodes ) #HydrusData.RandomPop( all_nodes )
            
            self._GenerateBranch( job_key, None, root_id, root_phash, all_nodes )
            
        finally:
            
            job_key.SetVariable( 'popup_text_1', 'done!' )
            job_key.DeleteVariable( 'popup_text_2' )
            
            job_key.Finish()
            
            job_key.Delete( 5 )
            
        
    
    def ResetSearch( self, hash_ids ):
        
        self._ExecuteMany( 'UPDATE shape_search_cache SET searched_distance = NULL WHERE hash_id = ?;', ( ( hash_id, ) for hash_id in hash_ids ) )
        
    
    def Search( self, hash_id, max_hamming_distance ):
        
        if max_hamming_distance == 0:
            
            similar_hash_ids = self._STL( self._Execute( 'SELECT hash_id FROM shape_perceptual_hash_map WHERE phash_id IN ( SELECT phash_id FROM shape_perceptual_hash_map WHERE hash_id = ? );', ( hash_id, ) ) )
            
            similar_hash_ids_and_distances = [ ( similar_hash_id, 0 ) for similar_hash_id in similar_hash_ids ]
            
        else:
            
            search_radius = max_hamming_distance
            
            top_node_result = self._Execute( 'SELECT phash_id FROM shape_vptree WHERE parent_id IS NULL;' ).fetchone()
            
            if top_node_result is None:
                
                return []
                
            
            ( root_node_phash_id, ) = top_node_result
            
            search = self._STL( self._Execute( 'SELECT phash FROM shape_perceptual_hashes NATURAL JOIN shape_perceptual_hash_map WHERE hash_id = ?;', ( hash_id, ) ) )
            
            if len( search ) == 0:
                
                return []
                
            
            similar_phash_ids_to_distances = {}
            
            num_cycles = 0
            total_nodes_searched = 0
            
            for search_phash in search:
                
                next_potentials = [ root_node_phash_id ]
                
                while len( next_potentials ) > 0:
                    
                    current_potentials = next_potentials
                    next_potentials = []
                    
                    num_cycles += 1
                    total_nodes_searched += len( current_potentials )
                    
                    for group_of_current_potentials in HydrusData.SplitListIntoChunks( current_potentials, 10000 ):
                        
                        # this is split into fixed lists of results of subgroups because as an iterable it was causing crashes on linux!!
                        # after investigation, it seemed to be SQLite having a problem with part of Get64BitHammingDistance touching phashes it presumably was still hanging on to
                        # the crash was in sqlite code, again presumably on subsequent fetch
                        # adding a delay in seemed to fix it as well. guess it was some memory maintenance buffer/bytes thing
                        # anyway, we now just get the whole lot of results first and then work on the whole lot
                        '''
                        #old method
                        select_statement = 'SELECT phash_id, phash, radius, inner_id, outer_id FROM shape_perceptual_hashes NATURAL JOIN shape_vptree WHERE phash_id = ?;'
                        
                        results = list( self._ExecuteManySelectSingleParam( select_statement, group_of_current_potentials ) )
                        '''
                        
                        with self._MakeTemporaryIntegerTable( group_of_current_potentials, 'phash_id' ) as temp_table_name:
                            
                            # temp phash_ids to actual phashes and tree info
                            results = self._Execute( 'SELECT phash_id, phash, radius, inner_id, outer_id FROM {} CROSS JOIN shape_perceptual_hashes USING ( phash_id ) CROSS JOIN shape_vptree USING ( phash_id );'.format( temp_table_name ) ).fetchall()
                            
                        
                        for ( node_phash_id, node_phash, node_radius, inner_phash_id, outer_phash_id ) in results:
                            
                            # first check the node itself--is it similar?
                            
                            node_hamming_distance = HydrusData.Get64BitHammingDistance( search_phash, node_phash )
                            
                            if node_hamming_distance <= search_radius:
                                
                                if node_phash_id in similar_phash_ids_to_distances:
                                    
                                    current_distance = similar_phash_ids_to_distances[ node_phash_id ]
                                    
                                    similar_phash_ids_to_distances[ node_phash_id ] = min( node_hamming_distance, current_distance )
                                    
                                else:
                                    
                                    similar_phash_ids_to_distances[ node_phash_id ] = node_hamming_distance
                                    
                                
                            
                            # now how about its children?
                            
                            if node_radius is not None:
                                
                                # we have two spheres--node and search--their centers separated by node_hamming_distance
                                # we want to search inside/outside the node_sphere if the search_sphere intersects with those spaces
                                # there are four possibles:
                                # (----N----)-(--S--)    intersects with outer only - distance between N and S > their radii
                                # (----N---(-)-S--)      intersects with both
                                # (----N-(--S-)-)        intersects with both
                                # (---(-N-S--)-)         intersects with inner only - distance between N and S + radius_S does not exceed radius_N
                                
                                if inner_phash_id is not None:
                                    
                                    spheres_disjoint = node_hamming_distance > ( node_radius + search_radius )
                                    
                                    if not spheres_disjoint: # i.e. they intersect at some point
                                        
                                        next_potentials.append( inner_phash_id )
                                        
                                    
                                
                                if outer_phash_id is not None:
                                    
                                    search_sphere_subset_of_node_sphere = ( node_hamming_distance + search_radius ) <= node_radius
                                    
                                    if not search_sphere_subset_of_node_sphere: # i.e. search sphere intersects with non-node sphere space at some point
                                        
                                        next_potentials.append( outer_phash_id )
                                        
                                    
                                
                            
                        
                    
                
            
            if HG.db_report_mode:
                
                HydrusData.ShowText( 'Similar file search touched {} nodes over {} cycles.'.format( HydrusData.ToHumanInt( total_nodes_searched ), HydrusData.ToHumanInt( num_cycles ) ) )
                
            
            # so, now we have phash_ids and distances. let's map that to actual files.
            # files can have multiple phashes, and phashes can refer to multiple files, so let's make sure we are setting the smallest distance we found
            
            similar_phash_ids = list( similar_phash_ids_to_distances.keys() )
            
            with self._MakeTemporaryIntegerTable( similar_phash_ids, 'phash_id' ) as temp_table_name:
                
                # temp phashes to hash map
                similar_phash_ids_to_hash_ids = HydrusData.BuildKeyToListDict( self._Execute( 'SELECT phash_id, hash_id FROM {} CROSS JOIN shape_perceptual_hash_map USING ( phash_id );'.format( temp_table_name ) ) )
                
            
            similar_hash_ids_to_distances = {}
            
            for ( phash_id, hash_ids ) in similar_phash_ids_to_hash_ids.items():
                
                distance = similar_phash_ids_to_distances[ phash_id ]
                
                for hash_id in hash_ids:
                    
                    if hash_id not in similar_hash_ids_to_distances:
                        
                        similar_hash_ids_to_distances[ hash_id ] = distance
                        
                    else:
                        
                        current_distance = similar_hash_ids_to_distances[ hash_id ]
                        
                        if distance < current_distance:
                            
                            similar_hash_ids_to_distances[ hash_id ] = distance
                            
                        
                    
                
            
            similar_hash_ids_and_distances = list( similar_hash_ids_to_distances.items() )
            
        
        return similar_hash_ids_and_distances
        
    
    def SetPHashes( self, hash_id, phashes ):
        
        current_phash_ids = self._STS( self._Execute( 'SELECT phash_id FROM shape_perceptual_hash_map WHERE hash_id = ?;', ( hash_id, ) ) )
        
        if len( current_phash_ids ) > 0:
            
            self.DisassociatePHashes( hash_id, current_phash_ids )
            
        
        if len( phashes ) > 0:
            
            self.AssociatePHashes( hash_id, phashes )
            
        
    
    def StopSearchingFile( self, hash_id ):
        
        phash_ids = self._STS( self._Execute( 'SELECT phash_id FROM shape_perceptual_hash_map WHERE hash_id = ?;', ( hash_id, ) ) )
        
        self.DisassociatePHashes( hash_id, phash_ids )
        
        self._Execute( 'DELETE FROM shape_search_cache WHERE hash_id = ?;', ( hash_id, ) )
        
    
