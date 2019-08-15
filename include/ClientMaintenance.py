from . import ClientConstants as CC
from . import ClientThreading
from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusExceptions
from . import HydrusFileHandling
from . import HydrusGlobals as HG
from . import HydrusImageHandling
from . import HydrusNetworking
from . import HydrusPaths
from . import HydrusThreading
import os
import random
import threading
import time

class GlobalMaintenanceJobInterface( object ):
    
    def GetName( self ):
        
        raise NotImplementedError()
        
    
    def GetSummary( self ):
        
        raise NotImplementedError()
        
    
GLOBAL_MAINTENANCE_RUN_ON_SHUTDOWN = 0
GLOBAL_MAINTENANCE_RUN_ON_IDLE = 1
GLOBAL_MAINTENANCE_RUN_FOREGROUND = 2

# make serialisable too
class GlobalMaintenanceJobScheduler( object ):
    
    def __init__( self, period = None, paused = None, times_can_run = None, max_running_time = None ):
        
        if period is None:
            
            period = 3600
            
        
        if paused is None:
            
            paused = False
            
        
        if times_can_run is None:
            
            times_can_run = [ GLOBAL_MAINTENANCE_RUN_ON_SHUTDOWN, GLOBAL_MAINTENANCE_RUN_ON_IDLE ]
            
        
        if max_running_time is None:
            
            max_running_time = ( 600, 86400 )
            
        
        self._next_run_time = 0
        self._no_work_until_time = 0
        self._no_work_until_reason = ''
        
        self._period = period
        self._paused = paused
        self._times_can_run = times_can_run
        
        # convert max running time into a time-based bandwidth rule or whatever
        # and have bw tracker and rules
        
    
    def CanRun( self ):
        
        if not HydrusData.TimeHasPassed( self._no_work_until_time ):
            
            return False
            
        
        # check shutdown, idle, foreground status
        
        if not HydrusData.TimeHasPassed( self._next_run_time ):
            
            return False
            
        
        return True
        
    
    def GetNextRunTime( self ):
        
        return self._next_run_time
        
    
    def Paused( self ):
        
        return self._paused
        
    
    def WorkCompleted( self ):
        
        self._next_run_time = HydrusData.GetNow() + self._period
        
    
# make this serialisable. it'll save like domain manager
class GlobalMaintenanceManager( object ):
    
    def __init__( self, controller ):
        
        self._controller = controller
        
        self._maintenance_lock = threading.Lock()
        self._lock = threading.Lock()
        
    
    # something like files maintenance manager. it'll also run itself, always checking on jobs, and will catch 'runnow' events too
    # instead of storing in db, we'll store here in the object since small number of complicated jobs
    
