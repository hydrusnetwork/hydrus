import os
import threading
import time

from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusThreading
from hydrus.core import HydrusTime

from hydrus.client import ClientGlobals as CG
from hydrus.client.interfaces import ClientControllerInterface

class DatabaseMaintenanceManager( object ):
    
    def __init__( self, controller: ClientControllerInterface.ClientControllerInterface ):
        
        self._controller = controller
        
        self._lock = threading.Lock()
        
        self._serious_error_encountered = False
        
        self._wake_event = threading.Event()
        self._shutdown = False
        self._is_working_hard = False
        
        self._controller.sub( self, 'Shutdown', 'shutdown' )
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
        
    
    def _GetWaitPeriod( self, work_period: float, time_it_took: float, still_work_to_do: bool ):
        
        if not still_work_to_do:
            
            return 600
            
        
        if self._is_working_hard:
            
            rest_ratio = CG.client_controller.new_options.GetInteger( 'deferred_table_delete_rest_percentage_work_hard' ) / 100
            
        elif CG.client_controller.CurrentlyIdle():
            
            rest_ratio = CG.client_controller.new_options.GetInteger( 'deferred_table_delete_rest_percentage_idle' ) / 100
            
        else:
            
            rest_ratio = CG.client_controller.new_options.GetInteger( 'deferred_table_delete_rest_percentage_normal' ) / 100
            
        
        reasonable_work_time = min( 5 * work_period, time_it_took )
        
        return reasonable_work_time * rest_ratio
        
    
    def _GetWorkPeriod( self ):
        
        if self._is_working_hard:
            
            return CG.client_controller.new_options.GetInteger( 'deferred_table_delete_work_time_ms_work_hard' ) / 1000
            
        elif CG.client_controller.CurrentlyIdle():
            
            return CG.client_controller.new_options.GetInteger( 'deferred_table_delete_work_time_ms_idle' ) / 1000
            
        else:
            
            return CG.client_controller.new_options.GetInteger( 'deferred_table_delete_work_time_ms_normal' ) / 1000
            
        
    
    def MainLoopBackgroundWork( self ):
        
        def check_shutdown():
            
            if HydrusThreading.IsThreadShuttingDown() or self._shutdown or self._serious_error_encountered:
                
                raise HydrusExceptions.ShutdownException()
                
            
        
        try:
            
            time_to_start = HydrusTime.GetNow() + 15
            
            while not HydrusTime.TimeHasPassed( time_to_start ):
                
                check_shutdown()
                
                time.sleep( 1 )
                
            
            while True:
                
                still_work_to_do = False
                
                check_shutdown()
                
                self._controller.WaitUntilViewFree()
                
                with self._lock:
                    
                    able_to_work = self._AbleToDoBackgroundMaintenance()
                    work_period = self._GetWorkPeriod()
                    
                
                time_it_took = 1.0
                
                if able_to_work:
                    
                    time_to_stop = HydrusTime.GetNowFloat() + work_period
                    
                    start_time = HydrusTime.GetNowFloat()
                    
                    try:
                        
                        still_work_to_do = CG.client_controller.WriteSynchronous( 'do_deferred_table_delete_work', time_to_stop )
                        
                    except Exception as e:
                        
                        self._serious_error_encountered = True
                        
                        HydrusData.PrintException( e )
                        
                        message = 'There was an unexpected problem during deferred table delete database maintenance work! This maintenance system will not run again this boot. A full traceback of this error should be written to the log.'
                        message += os.linesep * 2
                        message += str( e )
                        
                        HydrusData.ShowText( message )
                        
                    finally:
                        
                        self._controller.pub( 'notify_deferred_delete_database_maintenance_work_complete' )
                        
                    
                    time_it_took = HydrusTime.GetNowFloat() - start_time
                    
                
                with self._lock:
                    
                    wait_period = self._GetWaitPeriod( work_period, time_it_took, still_work_to_do )
                    
                
                self._wake_event.wait( wait_period )
                
                self._wake_event.clear()
                
            
        except HydrusExceptions.ShutdownException:
            
            pass
            
        
    
    def FlipWorkingHard( self ):
        
        with self._lock:
            
            self._is_working_hard = not self._is_working_hard
            
        
        self._controller.pub( 'notify_deferred_delete_database_maintenance_state_change' )
        
        self.Wake()
        
    
    def IsWorkingHard( self ) -> bool:
        
        with self._lock:
            
            return self._is_working_hard
            
        
    
    def Shutdown( self ):
        
        with self._lock:
            
            self._shutdown = True
            
        
        self.Wake()
        
        
    
    def Start( self ):
        
        self._controller.CallToThreadLongRunning( self.MainLoopBackgroundWork )
        
    
    def Wake( self ):
        
        self._wake_event.set()
        
    
