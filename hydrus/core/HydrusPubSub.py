import threading
import weakref

from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusProfiling

class HydrusPubSub( object ):
    
    def __init__( self, valid_callable ):
        
        self._valid_callable = valid_callable
        
        self._doing_work = False
        
        self._pubsubs = []
        
        self._received_job_event = threading.Event()
        self._finished_job_event = threading.Event()
        
        self._lock = threading.Lock()
        
        self._topics_to_objects = {}
        self._topics_to_method_names = {}
        
    
    def _GetCallableTuples( self, topic ):
        
        # this now does the obj as well so we have a strong direct ref to it throughout procesing
        
        callable_tuples = []
        
        if topic in self._topics_to_objects:
            
            try:
                
                objects = self._topics_to_objects[ topic ]
                
                for obj in objects:
                    
                    if obj is None or not self._valid_callable( obj ):
                        
                        continue
                        
                    
                    method_names = self._topics_to_method_names[ topic ]
                    
                    for method_name in method_names:
                        
                        if hasattr( obj, method_name ):
                            
                            callable = getattr( obj, method_name )
                            
                            callable_tuples.append( ( obj, callable ) )
                            
                        
                    
                
            except:
                
                pass
                
            
        
        return callable_tuples
        
    
    def DoingWork( self ):
        
        return self._doing_work
        
    
    def Process( self ):
        
        # only do one list of callables at a time
        # we don't want to map a topic to its callables until the previous topic's callables have been fully executed
        # e.g. when we start a message with a pubsub, it'll take a while (in independant thread-time) for Qt to create
        # the dialog and hence map the new callable to the topic. this was leading to messages not being updated
        # because the (short) processing thread finished and entirely pubsubbed before Qt had a chance to boot the
        # message.
        
        self._doing_work = True
        
        try:
            
            with self._lock:
                
                if len( self._pubsubs ) == 0:
                    
                    return
                    
                
                pubsubs = self._pubsubs
                
                self._pubsubs = []
                
            
            for ( topic, args, kwargs ) in pubsubs:
                
                try:
                    
                    # do all this _outside_ the lock, lol
                    
                    callable_tuples = self._GetCallableTuples( topic )
                    
                    # don't want to report the showtext we just send here!
                    not_a_report = topic != 'message'
                    
                    if HG.pubsub_report_mode and not_a_report:
                        
                        HydrusData.ShowText( ( topic, args, kwargs, callable_tuples ) )
                        
                    
                    if HydrusProfiling.IsProfileMode( 'ui' ) and not_a_report:
                        
                        summary = 'Profiling pubsub: {}'.format( topic )
                        
                        for ( obj, callable ) in callable_tuples:
                            
                            try:
                                
                                HydrusProfiling.Profile( summary, HydrusData.Call( callable, *args, **kwargs ), min_duration_ms = HG.pubsub_profile_min_job_time_ms )
                                
                            except HydrusExceptions.ShutdownException:
                                
                                return False
                                
                            
                        
                    else:
                        
                        for ( obj, callable ) in callable_tuples:
                            
                            try:
                                
                                callable( *args, **kwargs )
                                
                            except HydrusExceptions.ShutdownException:
                                
                                return False
                                
                            
                        
                    
                except Exception as e:
                    
                    HydrusData.ShowException( e )
                    
                
            
        finally:
            
            self._doing_work = False
            
            self._finished_job_event.set()
            
        
    
    def pub( self, topic, *args, **kwargs ):
        
        with self._lock:
            
            self._pubsubs.append( ( topic, args, kwargs ) )
            
        
        self._received_job_event.set()
        
    
    def pubimmediate( self, topic, *args, **kwargs ):
        
        with self._lock:
            
            callable_tuples = self._GetCallableTuples( topic )
            
        
        for ( obj, callable ) in callable_tuples:
            
            callable( *args, **kwargs )
            
        
    
    def sub( self, object, method_name, topic ):
        
        with self._lock:
            
            if topic not in self._topics_to_objects: self._topics_to_objects[ topic ] = weakref.WeakSet()
            if topic not in self._topics_to_method_names: self._topics_to_method_names[ topic ] = set()
            
            self._topics_to_objects[ topic ].add( object )
            self._topics_to_method_names[ topic ].add( method_name )
            
        
    
    def WaitOnPub( self ):
        
        self._received_job_event.wait( 0.5 )
        
        self._received_job_event.clear()
        
    
    def Wake( self ):
        
        self._received_job_event.set()
        
    
    def WaitUntilFree( self ):
        
        while True:
            
            if HG.model_shutdown:
                
                raise HydrusExceptions.ShutdownException( 'Application shutting down!' )
                
            elif not ( self.WorkToDo() or self.DoingWork() ):
                
                return
                
            else:
                
                self._finished_job_event.wait( 0.5 )
                self._finished_job_event.clear()
                
            
        
    
    def WorkToDo( self ):
        
        with self._lock:
            
            return len( self._pubsubs ) > 0
            
        
    
