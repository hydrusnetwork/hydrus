import threading

from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTime
from hydrus.core.processes import HydrusThreading

from hydrus.client import ClientGlobals as CG

def DAEMONCheckExportFolders():
    
    controller = CG.client_controller
    
    if not controller.new_options.GetBoolean( 'pause_export_folders_sync' ):
        
        HG.export_folders_running = True
        
        try:
            
            export_folder_names = controller.Read( 'serialisable_names', HydrusSerialisable.SERIALISABLE_TYPE_EXPORT_FOLDER )
            
            for name in export_folder_names:
                
                export_folder = controller.Read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_EXPORT_FOLDER, name )
                
                if controller.new_options.GetBoolean( 'pause_export_folders_sync' ) or HydrusThreading.IsThreadShuttingDown():
                    
                    break
                    
                
                export_folder.DoWork()
                
            
        finally:
            
            HG.export_folders_running = False
            
        
    

class ManagerWithMainLoop( object ):
    
    def __init__( self, controller: "CG.ClientController.Controller", pre_loop_wait_time: int ):
        
        # TODO: move work_time/rest_time into this superclass
        # maybe some methods that can be overridden to get current rest time ratio and stuff in the subclasses
        # but otherwise this guy should take more responsibility for the mainloop code, and the subclasses should basically only implement 'dojob()' for the loop proper
        # one logical implementation!
        
        # when doing this, also make sure we do anti-CPU-thrash tech on wake_from_work/idle_sleep_event. those guys should not be referred to outside of here
        # and then we should move to a wait(), no timeout, on them
        # and along with that, a complete revamp of manager wait and wake tech. if we want to wake every twenty mins, let's have JobScheduler or one of those guys wake us
        # maybe premainloopwait can do it, yeah, but not in the mainloop
        
        # I think we want one master self._Wait command that takes time took and work_still_to_do/work_done, which is what a work packet should return to our mainloop
        # that sleep guy decides which sleep to do and such
        
        # note it looks like we'll need a 'CleanUpAfterMainLoop' guy in a finally, so Subs at least can clean up
        
        self._controller = controller
        
        self._pre_loop_wait_time = pre_loop_wait_time
        
        self._lock = threading.Lock()
        
        self._wake_from_work_sleep_event = threading.Event()
        self._wake_from_idle_sleep_event = threading.Event()
        self._shutdown = False
        self._mainloop_is_finished = False
        self._serious_error_encountered = False
        
        self._controller.sub( self, 'Shutdown', 'shutdown' )
        self._controller.sub( self, 'Wake', 'wake_daemons' )
        
    
    def __str__( self ):
        
        return f'MainLoop: {self.GetName()}'
        
    
    def _CheckShutdown( self ):
        
        if HydrusThreading.IsThreadShuttingDown() or self._shutdown or self._serious_error_encountered:
            
            raise HydrusExceptions.ShutdownException()
            
        
    
    def _DoPostMainLoopShutdown( self ):
        
        pass
        
    
    def _DoSingleLoop( self ):
        
        raise NotImplementedError()
        
    
    def DoPreMainLoopWait( self ):
        
        with self._lock:
            
            time_to_start = HydrusTime.GetNowFloat() + self._pre_loop_wait_time
            
        
        # stupid wait here because we are in init and a failure to launch may not trigger nice wake signals as things are unwound
        while not HydrusTime.TimeHasPassedFloat( time_to_start ):
            
            with self._lock:
                
                self._CheckShutdown()
                
            
            self._wake_from_idle_sleep_event.wait( 1 )
            
            if self._wake_from_idle_sleep_event.is_set():
                
                break
                
            
        
    
    def GetName( self ) -> str:
        
        raise NotImplementedError()
        
    
    def MainLoop( self ):
        
        try:
            
            self.DoPreMainLoopWait()
            
            while True:
                
                self._DoSingleLoop()
                
            
            # ok I moved from DoMainLoop to DoSingleLoop. now we can pull common parts out no here
            # we want to push towards:
            # have work to do?
            # can work?
            # still work to do = do work()
            # if shutting down, dump out
            # get a wait period( still work to do )
            # do a wait
            
        except HydrusExceptions.ShutdownException:
            
            if HG.shutdown_report_mode:
                
                HydrusData.DebugPrint( f'MainLoop Manager "{self}" caught a Shutdown exception in its mainloop.' )
                
            
            pass
            
        finally:
            
            if HG.shutdown_report_mode:
                
                HydrusData.DebugPrint( f'MainLoop Manager "{self}" is shut down!' )
                
            
            self._DoPostMainLoopShutdown()
            
            self._mainloop_is_finished = True
            
        
    
    def IsShutdown( self ):
        
        return self._mainloop_is_finished
        
    
    def Shutdown( self ):
        
        with self._lock:
            
            self._shutdown = True
            
        
        self.Wake()
        
    
    def Start( self ):
        
        self._controller.CallToThreadLongRunning( self.MainLoop )
        
    
    def Wake( self ):
        
        self._wake_from_work_sleep_event.set()
        self._wake_from_idle_sleep_event.set()
        
    
    def WakeIfNotWorking( self ):
        
        self._wake_from_idle_sleep_event.set()
        
    
