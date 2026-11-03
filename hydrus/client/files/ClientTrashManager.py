import time

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusTime

from hydrus.client import ClientGlobals as CG

from hydrus.client import ClientDaemons

class TrashMaintenanceManager( ClientDaemons.ManagerWithMainLoop ):
    
    def __init__( self, controller: "CG.ClientController.Controller" ):
        
        super().__init__( controller, 15 )
        
        self._last_file_non_physically_deleted_time = 0
        
        self._controller.sub( self, 'NotifyFileNonPhysicallyDeleted', 'notify_file_non_physically_deleted' )
        
    
    def _DoSingleLoop( self ):
        
        still_work_to_do = False
        wait_period = 600
        
        with self._lock:
            
            self._CheckShutdown()
            
        
        controller = CG.client_controller
        
        able_to_work = True
        
        if not HC.options[ 'trash_max_size' ] is not None and not HC.options[ 'trash_max_age' ] is not None:
            
            able_to_work = False
            
        
        if not controller.CurrentlyIdle() and not controller.new_options.GetBoolean( 'maintain_trash_in_normal_time' ):
            
            able_to_work = False
            
        
        with self._lock:
            
            # TODO: This is cool but needs to be migrated to the mainloop so we can get better feedback on it in review mainloops UI
            # 'deferring work x seconds since most recent (label) event' kind of thing
            # any file delete, not just trashed, but NOT a physical delete lol otherwise we block ourselves. this is KISS and careful
            safe_time_to_action_recent_deletes = self._last_file_non_physically_deleted_time + 60
            
            if not HydrusTime.TimeHasPassedFloat( safe_time_to_action_recent_deletes ):
                
                able_to_work = False
                
                wait_period = max( HydrusTime.TimeUntil( safe_time_to_action_recent_deletes ) + 1, 5 )
                
            
        
        expected_work_period = 0.5
        
        if able_to_work:
            
            start_time = HydrusTime.GetNowFloat()
            
            still_work_to_do = controller.WriteSynchronous( 'maintain_trash', expected_work_period )
            
            actual_work_period = HydrusTime.GetNowFloat() - start_time
            
            if still_work_to_do:
                
                wait_period = 0.5
                
            
            if still_work_to_do:
                
                wake_event = self._wake_from_work_sleep_event
                
            else:
                
                wake_event = self._wake_from_idle_sleep_event
                
            
        else:
            
            wake_event = self._wake_from_idle_sleep_event
            
        
        FORCED_WAIT_PERIOD = 0.25
        
        if wait_period > FORCED_WAIT_PERIOD:
            
            # forced wait when lots going on
            time.sleep( FORCED_WAIT_PERIOD )
            
            wait_period -= FORCED_WAIT_PERIOD
            
        
        wake_event.wait( wait_period )
        
        self._wake_from_work_sleep_event.clear()
        self._wake_from_idle_sleep_event.clear()
        
    
    def GetName( self ) -> str:
        
        return 'trash maintenance'
        
    
    def NotifyFileNonPhysicallyDeleted( self ):
        
        with self._lock:
            
            self._last_file_non_physically_deleted_time = HydrusTime.GetNowFloat()
            
        
    
