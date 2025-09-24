import threading
import typing

from hydrus.core import HydrusTime

from hydrus.client import ClientDaemons
from hydrus.client import ClientGlobals as CG

class PotentialDuplicatesMaintenanceNumbersStore( object ):
    
    my_instance = None
    
    def __init__( self ):
        
        self._lock = threading.Lock()
        
        self._similar_files_maintenance_status: dict[ int, int ] = dict()
        
        self._need_new_maintenance_status = True
        
        CG.client_controller.sub( self, 'RefreshMaintenanceNumbers', 'notify_new_shape_search_cache_numbers' )
        
    
    @staticmethod
    def instance() -> 'PotentialDuplicatesMaintenanceNumbersStore':
        
        if PotentialDuplicatesMaintenanceNumbersStore.my_instance is None:
            
            PotentialDuplicatesMaintenanceNumbersStore.my_instance = PotentialDuplicatesMaintenanceNumbersStore()
            
        
        return PotentialDuplicatesMaintenanceNumbersStore.my_instance
        
    
    def GetMaintenanceNumbers( self ):
        
        with self._lock:
            
            if self._need_new_maintenance_status:
                
                self._similar_files_maintenance_status = typing.cast( dict[ int, int ], CG.client_controller.Read( 'similar_files_maintenance_status' ) )
                
                self._need_new_maintenance_status = False
                
            
            return dict( self._similar_files_maintenance_status )
            
        
    
    def RefreshMaintenanceNumbers( self ):
        
        self._need_new_maintenance_status = True
        
        # get anyone who cares to ask so it happens
        CG.client_controller.pub( 'new_similar_files_maintenance_numbers' )
        
    

class PotentialDuplicatesMaintenanceManager( ClientDaemons.ManagerWithMainLoop ):
    
    def __init__( self, controller ):
        
        super().__init__( controller, 30 )
        
        self._work_hard = threading.Event()
        
        self._need_to_rebalance_tree = threading.Event()
        self._need_to_rebalance_tree.set()
        
        self._i_triggered_a_numbers_regen_last_cycle = False
        
        CG.client_controller.sub( self, 'NotifyNewBranchMaintenanceWork', 'notify_new_shape_search_branch_maintenance_work' )
        CG.client_controller.sub( self, 'NotifyNewFileImported', 'notify_new_file_imported' )
        
    
    def _DoMainLoop( self ):
        
        while True:
            
            with self._lock:
                
                self._CheckShutdown()
                
            
            self._controller.WaitUntilViewFree()
            
            if self._need_to_rebalance_tree.is_set():
                
                expected_work_period = 0.1
                
                still_maintenance_work_to_do = CG.client_controller.WriteSynchronous( 'maintain_similar_files_tree', work_period = expected_work_period )
                
                if not still_maintenance_work_to_do:
                    
                    self._need_to_rebalance_tree.clear()
                    
                
            
            work_permitted = self._WorkPermitted()
            work_to_do = self._WorkToDo()
            
            if work_permitted and not work_to_do:
                
                self._work_hard.clear()
                
            
            if work_permitted and work_to_do:
                
                expected_work_period = self._GetWorkPeriod()
                
                start_time = HydrusTime.GetNowPrecise()
                
                search_distance = CG.client_controller.new_options.GetInteger( 'similar_files_duplicate_pairs_search_distance' )
                
                ( still_search_work_to_do, num_done ) = CG.client_controller.WriteSynchronous( 'maintain_similar_files_search_for_potential_duplicates', search_distance, work_period = expected_work_period )
                
                total_time_took = HydrusTime.GetNowPrecise() - start_time
                
                wait_time = self._GetRestTime( expected_work_period, total_time_took )
                
                if num_done > 0:
                    
                    CG.client_controller.pub( 'new_similar_files_potentials_search_numbers' )
                    
                    PotentialDuplicatesMaintenanceNumbersStore.instance().RefreshMaintenanceNumbers()
                    
                    self._i_triggered_a_numbers_regen_last_cycle = False
                    
                else:
                    
                    if not still_search_work_to_do:
                        
                        if self._i_triggered_a_numbers_regen_last_cycle:
                            
                            # infinite loop, it seems, let's bail out
                            raise Exception( 'The similar files search daemon was informed it had work to do but then found nothing! It may be your search count numbers are incorrect--please regenerate them through the cog button on the preparation tab of a duplicates page and then restart the client. Let hydev know if that does not fix it!' )
                            
                        else:
                            
                            # it could be that a file got deleted or something in the moment before we did work
                            # it could be that the count is wrong
                            # let's fix it and see what happens next cycle
                            CG.client_controller.WriteSynchronous( 'regenerate_similar_files_search_count_numbers' )
                            
                            PotentialDuplicatesMaintenanceNumbersStore.instance().RefreshMaintenanceNumbers()
                            
                            self._i_triggered_a_numbers_regen_last_cycle = True
                            
                        
                    
                
            else:
                
                wait_time = 10
                
            
            with self._lock:
                
                self._CheckShutdown()
                
            
            self._wake_event.wait( wait_time )
            
            self._wake_event.clear()
            
        
    
    def _GetRestTime( self, expected_work_period, actual_work_period ):
        
        if self._work_hard.is_set():
            
            return 0.1
            
        
        if self._controller.CurrentlyIdle():
            
            rest_ratio = CG.client_controller.new_options.GetInteger( 'potential_duplicates_search_rest_percentage_idle' ) / 100
            
        else:
            
            rest_ratio = CG.client_controller.new_options.GetInteger( 'potential_duplicates_search_rest_percentage_active' ) / 100
            
        
        if actual_work_period > expected_work_period * 10:
            
            # if suddenly a job blats the user for ten seconds or _ten minutes_ during normal time, we are going to take a big break
            rest_ratio *= 30
            
        
        reasonable_work_period = min( 5 * expected_work_period, actual_work_period )
        
        return reasonable_work_period * rest_ratio
        
    
    def _GetWorkPeriod( self ):
        
        if self._work_hard.is_set():
            
            return 0.5
            
        
        if self._controller.CurrentlyIdle():
            
            return HydrusTime.SecondiseMSFloat( CG.client_controller.new_options.GetInteger( 'potential_duplicates_search_work_time_ms_idle' ) )
            
        else:
            
            return HydrusTime.SecondiseMSFloat( CG.client_controller.new_options.GetInteger( 'potential_duplicates_search_work_time_ms_active' ) )
            
        
    
    def _WorkPermitted( self ):
        
        if self._work_hard.is_set():
            
            return True
            
        
        if self._controller.CurrentlyIdle():
            
            if self._controller.new_options.GetBoolean( 'maintain_similar_files_duplicate_pairs_during_idle' ):
                
                return True
                
            
        else:
            
            if self._controller.new_options.GetBoolean( 'maintain_similar_files_duplicate_pairs_during_active' ):
                
                return True
                
            
        
        return False
        
    
    def _WorkToDo( self ):
        
        search_distance = CG.client_controller.new_options.GetInteger( 'similar_files_duplicate_pairs_search_distance' )
        
        similar_files_maintenance_status = PotentialDuplicatesMaintenanceNumbersStore.instance().GetMaintenanceNumbers()
        
        there_is_stuff_to_search = True in ( count > 0 for ( distance_searched_at, count ) in similar_files_maintenance_status.items() if distance_searched_at < search_distance )
        
        return there_is_stuff_to_search
        
    
    def GetName( self ) -> str:
        
        return 'potential duplicates search'
        
    
    def IsWorkingHard( self ) -> bool:
        
        return self._work_hard.is_set()
        
    
    def NotifyNewBranchMaintenanceWork( self ):
        
        self._need_to_rebalance_tree.set()
        
    
    def NotifyNewFileImported( self ):
        
        # right, we don't want to go crazy here and spam-wake the queue on any import
        # but if we can work now and there isn't a huge outstanding, let's stay up to date mate
        if self._WorkPermitted():
            
            search_distance = CG.client_controller.new_options.GetInteger( 'similar_files_duplicate_pairs_search_distance' )
            
            similar_files_maintenance_status = PotentialDuplicatesMaintenanceNumbersStore.instance().GetMaintenanceNumbers()
            
            total_outstanding = sum( ( count for ( distance_searched_at, count ) in similar_files_maintenance_status.items() if distance_searched_at < search_distance ) )
            
            if total_outstanding < 50:
                
                self.Wake()
                
            
        
    
    def SetWorkHard( self, work_hard: bool ):
        
        if work_hard:
            
            self._work_hard.set()
            
        else:
            
            self._work_hard.clear()
            
        
        self.Wake()
        
    
