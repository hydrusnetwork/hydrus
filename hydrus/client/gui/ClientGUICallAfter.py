from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusData
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusProfiling

from hydrus.client.gui import QtPorting as QP

CallAfterEventType = QP.registerEventType()

class CallAfterEvent( QC.QEvent ):
    
    def __init__( self, qobject, call: HydrusData.Call ):
        
        super().__init__( CallAfterEventType )
        
        self._qobject = qobject
        self._call = call
        
    
    def Execute( self ):
        
        if self._qobject is None or not QP.isValid( self._qobject ):
            
            return
            
        
        self._call()
        
    
    def GetCall( self ) -> HydrusData.Call:
        
        return self._call
        
    

# ok _potential_ next step is to wrap the QObject in a guy that creates a queue and can deliver that queue to the asking thread
# we put the job on the queue and if the QObject is not pending a wake, we send a wake event and set wake pending instead
# the QObject is now processing a queue of gubbins all in one go
# however I think we should only do this if we have good evidence that this thing is running bad, because processing all that in one Qt event might have some unexpected surprises

class CallAfterEventCatcher( QC.QObject ):
    
    def __init__( self, parent ):
        
        super().__init__( parent )
        
    
    def event( self, event ):
        
        try:
            
            if event.type() == CallAfterEventType and isinstance( event, CallAfterEvent ):
                
                if HydrusProfiling.IsProfileMode( 'ui' ):
                    
                    summary = 'Profiling CallAfter Event: {}'.format( event.GetCall() )
                    
                    HydrusProfiling.Profile( summary, HydrusData.Call( event.Execute ), min_duration_ms = HG.callto_profile_min_job_time_ms )
                    
                else:
                    
                    event.Execute()
                    
                
                event.accept()
                
                return True
                
            else:
                
                return super().event( event )
                
            
        except Exception as e:
            
            HydrusData.ShowException( e )
            
            return True
            
        
    

def CallAfter( call_after_catcher: QC.QObject, qobject: QC.QObject, func, *args, **kwargs ):
    
    call = HydrusData.Call( func, *args, **kwargs )
    
    QW.QApplication.postEvent( call_after_catcher, CallAfterEvent( qobject, call ) )
    
    # it appears this is redundant and for Arch from the Ubuntu-built release apparently eventDispatcher() was None
    # QW.QApplication.instance().eventDispatcher().wakeUp()
    
