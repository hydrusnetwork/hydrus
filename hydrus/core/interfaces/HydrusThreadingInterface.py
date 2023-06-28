
class SchedulableJobInterface( object ):
    
    PRETTY_CLASS_NAME = 'job base interface'
    
    def Cancel( self ) -> None:
        
        raise NotImplementedError()
        
    
    def CurrentlyWorking( self ) -> bool:
        
        raise NotImplementedError()
        
    
    def Delay( self, delay ) -> None:
        
        raise NotImplementedError()
        
    
    def GetDueString( self ) -> str:
        
        raise NotImplementedError()
        
    
    def GetNextWorkTime( self ):
        
        raise NotImplementedError()
        
    
    def GetPrettyJob( self ):
        
        raise NotImplementedError()
        
    
    def GetTimeDeltaUntilDue( self ):
        
        raise NotImplementedError()
        
    
    def IsCancelled( self ) -> bool:
        
        raise NotImplementedError()
        
    
    def IsDead( self ) -> bool:
        
        raise NotImplementedError()
        
    
    def IsDue( self ) -> bool:
        
        raise NotImplementedError()
        
    
    def PubSubWake( self, *args, **kwargs ) -> None:
        
        raise NotImplementedError()
        
    
    def SetThreadSlotType( self, thread_type ) -> None:
        
        raise NotImplementedError()
        
    
    def ShouldDelayOnWakeup( self, value ) -> None:
        
        raise NotImplementedError()
        
    
    def SlotOK( self ) -> bool:
        
        raise NotImplementedError()
        
    
    def StartWork( self ) -> None:
        
        raise NotImplementedError()
        
    
    def Wake( self, next_work_time = None ) -> None:
        
        raise NotImplementedError()
        
    
    def WakeOnPubSub( self, topic ) -> None:
        
        raise NotImplementedError()
        
    
    def WaitingOnWorkSlot( self ):
        
        raise NotImplementedError()
        
    
    def Work( self ) -> None:
        
        raise NotImplementedError()
        
    
