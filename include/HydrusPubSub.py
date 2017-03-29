import HydrusConstants as HC
import HydrusData
import HydrusExceptions
import Queue
import threading
import traceback
import weakref
import HydrusGlobals

class HydrusPubSub( object ):
    
    def __init__( self, controller, binding_errors_to_ignore = None ):
        
        if binding_errors_to_ignore is None:
            
            binding_errors_to_ignore = []
            
        
        self._controller = controller
        self._binding_errors_to_ignore = binding_errors_to_ignore
        
        self._pubsubs = []
        
        self._lock = threading.Lock()
        
        self._topics_to_objects = {}
        self._topics_to_method_names = {}
        
    
    def _GetCallables( self, topic ):
        
        callables = []
        
        if topic in self._topics_to_objects:
            
            try:
                
                objects = self._topics_to_objects[ topic ]
                
                for object in objects:
                    
                    method_names = self._topics_to_method_names[ topic ]
                    
                    for method_name in method_names:
                        
                        if hasattr( object, method_name ):
                            
                            try:
                                
                                callable = getattr( object, method_name )
                                
                                callables.append( callable )
                                
                            except TypeError as e:
                                
                                if '_wxPyDeadObject' not in HydrusData.ToUnicode( e ): raise
                                
                            except Exception as e:
                                
                                if not isinstance( e, self._binding_errors_to_ignore ):
                                    
                                    raise
                                    
                                
                            
                        
                    
                
            except: pass
            
        
        return callables
        
    
    def NoJobsQueued( self ):
        
        with self._lock:
            
            return len( self._pubsubs ) == 0
            
        
    
    def Process( self ):
        
        # only do one list of callables at a time
        # we don't want to map a topic to its callables until the previous topic's callables have been fully executed
        # e.g. when we start a message with a pubsub, it'll take a while (in independant thread-time) for wx to create
        # the dialog and hence map the new callable to the topic. this was leading to messages not being updated
        # because the (short) processing thread finished and entirely pubsubbed before wx had a chance to boot the
        # message.
        
        callables = []
        
        with self._lock:
            
            if len( self._pubsubs ) > 0:
                
                ( topic, args, kwargs ) = self._pubsubs.pop( 0 )
                
                callables = self._GetCallables( topic )
                
            
        
        # do this _outside_ the lock, lol
        
        for callable in callables:
            
            if HydrusGlobals.pubsub_profile_mode:
                
                summary = 'Profiling ' + topic + ': ' + repr( callable )
                
                if topic == 'message':
                    
                    HydrusData.Print( summary )
                    
                else:
                    
                    HydrusData.ShowText( summary )
                    
                
                HydrusData.Profile( summary, 'callable( *args, **kwargs )', globals(), locals() )
                
            else:
                
                try:
                    
                    callable( *args, **kwargs )
                    
                except HydrusExceptions.ShutdownException:
                    
                    return
                    
                
            
        
    
    def pub( self, topic, *args, **kwargs ):
        
        with self._lock:
            
            self._pubsubs.append( ( topic, args, kwargs ) )
            
        
        self._controller.NotifyPubSubs()
        
    
    def pubimmediate( self, topic, *args, **kwargs ):
        
        with self._lock:
            
            callables = self._GetCallables( topic )
            
        
        for callable in callables: callable( *args, **kwargs )
        
    
    def sub( self, object, method_name, topic ):
        
        with self._lock:
            
            if topic not in self._topics_to_objects: self._topics_to_objects[ topic ] = weakref.WeakSet()
            if topic not in self._topics_to_method_names: self._topics_to_method_names[ topic ] = set()
            
            self._topics_to_objects[ topic ].add( object )
            self._topics_to_method_names[ topic ].add( method_name )
            
        
    
