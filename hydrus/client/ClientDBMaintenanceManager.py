import time

from hydrus.core import HydrusData
from hydrus.core import HydrusTime

from hydrus.client import ClientDaemons
from hydrus.client import ClientGlobals as CG

class DatabaseMaintenanceManager( ClientDaemons.ManagerWithMainLoop ):
    
    def __init__( self, controller: "CG.ClientController.Controller" ):
        
        super().__init__( controller, 15 )
        
        self._is_working_hard = False
        
        self._controller.sub( self, 'Wake', 'checkbox_manager_inverted' )
        self._controller.sub( self, 'Wake', 'notify_deferred_delete_database_maintenance_new_work' )
        
    
    def _AbleToDoBackgroundMaintenance( self ):
        
        if self._is_working_hard:
            
            return True
            
        
        if CG.client_controller.CurrentlyIdle():
            
            if not self._controller.new_options.GetBoolean( 'database_deferred_delete_maintenance_during_idle' ):
                
                return False
                
            
            if not self._controller.GoodTimeToStartBackgroundWork():
                
                return False
                
            
        else:
            
            if not self._controller.new_options.GetBoolean( 'database_deferred_delete_maintenance_during_active' ):
                
                return False
                
            
        
        return True
        
    
    def _GetWaitPeriod( self, expected_work_period: float, actual_work_period: float, still_work_to_do: bool ):
        
        if not still_work_to_do:
            
            return 600
            
        
        if self._is_working_hard:
            
            rest_ratio = CG.client_controller.new_options.GetInteger( 'deferred_table_delete_rest_percentage_work_hard' ) / 100
            
        elif CG.client_controller.CurrentlyIdle():
            
            rest_ratio = CG.client_controller.new_options.GetInteger( 'deferred_table_delete_rest_percentage_idle' ) / 100
            
        else:
            
            rest_ratio = CG.client_controller.new_options.GetInteger( 'deferred_table_delete_rest_percentage_normal' ) / 100
            
        
        reasonable_work_period = min( 5 * expected_work_period, actual_work_period )
        
        return reasonable_work_period * rest_ratio
        
    
    def _GetWorkPeriod( self ):
        
        if self._is_working_hard:
            
            return HydrusTime.SecondiseMSFloat( CG.client_controller.new_options.GetInteger( 'deferred_table_delete_work_time_ms_work_hard' ) )
            
        elif CG.client_controller.CurrentlyIdle():
            
            return HydrusTime.SecondiseMSFloat( CG.client_controller.new_options.GetInteger( 'deferred_table_delete_work_time_ms_idle' ) )
            
        else:
            
            return HydrusTime.SecondiseMSFloat( CG.client_controller.new_options.GetInteger( 'deferred_table_delete_work_time_ms_normal' ) )
            
        
    
    def FlipWorkingHard( self ):
        
        with self._lock:
            
            self._is_working_hard = not self._is_working_hard
            
        
        self._controller.pub( 'notify_deferred_delete_database_maintenance_state_change' )
        
        self.Wake()
        
    
    def GetName( self ) -> str:
        
        return 'db maintenance'
        
    
    def IsWorkingHard( self ) -> bool:
        
        with self._lock:
            
            return self._is_working_hard
            
        
    
    def _DoMainLoop( self ):
        
        while True:
            
            still_work_to_do = False
            
            with self._lock:
                
                self._CheckShutdown()
                
            
            self._controller.WaitUntilViewFree()
            
            with self._lock:
                
                able_to_work = self._AbleToDoBackgroundMaintenance()
                expected_work_period = self._GetWorkPeriod()
                
            
            if able_to_work:
                
                time_to_stop = HydrusTime.GetNowFloat() + expected_work_period
                
                start_time = HydrusTime.GetNowFloat()
                
                try:
                    
                    still_work_to_do = CG.client_controller.WriteSynchronous( 'do_deferred_table_delete_work', time_to_stop )
                    
                except Exception as e:
                    
                    self._serious_error_encountered = True
                    
                    HydrusData.PrintException( e )
                    
                    message = 'There was an unexpected problem during deferred table delete database maintenance work! This maintenance system will not run again this boot. A full traceback of this error should be written to the log.'
                    message += '\n' * 2
                    message += str( e )
                    
                    HydrusData.ShowText( message )
                    
                finally:
                    
                    self._controller.pub( 'notify_deferred_delete_database_maintenance_work_complete' )
                    
                
                actual_work_period = HydrusTime.GetNowFloat() - start_time
                
                with self._lock:
                    
                    wait_period = self._GetWaitPeriod( expected_work_period, actual_work_period, still_work_to_do )
                    
                
            else:
                
                wait_period = 600
                
            
            FORCED_WAIT_PERIOD = 0.25
            
            if wait_period > FORCED_WAIT_PERIOD:
                
                # forced wait when lots going on
                time.sleep( FORCED_WAIT_PERIOD )
                
                wait_period -= FORCED_WAIT_PERIOD
                
            
            self._wake_event.wait( wait_period )
            
            self._wake_event.clear()
            
        
    
