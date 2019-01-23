from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusExceptions
import queue
import threading
import traceback
import weakref
from . import HydrusGlobals as HG

class HydrusPubSub( object ):
    
    def __init__( self, controller ):
        
        self._controller = controller
        
        self._doing_work = False
        
        self._pubsubs = []
        
        self._pub_event = threading.Event()
        
        self._lock = threading.Lock()
        
        self._topics_to_objects = {}
        self._topics_to_method_names = {}
        
    
    def _GetCallables( self, topic ):
        
        callables = []
        
        if topic in self._topics_to_objects:
            
            try:
                
                objects = self._topics_to_objects[ topic ]
                
                for object in objects:
                    
                    if not object:
                        
                        continue
                        
                    
                    method_names = self._topics_to_method_names[ topic ]
                    
                    for method_name in method_names:
                        
                        if hasattr( object, method_name ):
                            
                            callable = getattr( object, method_name )
                            
                            callables.append( callable )
                            
                        
                    
                
            except:
                
                pass
                
            
        
        return callables
        
    
    def DoingWork( self ):
        
        return self._doing_work
        
    
    def Process( self ):
        
        # only do one list of callables at a time
        # we don't want to map a topic to its callables until the previous topic's callables have been fully executed
        # e.g. when we start a message with a pubsub, it'll take a while (in independant thread-time) for wx to create
        # the dialog and hence map the new callable to the topic. this was leading to messages not being updated
        # because the (short) processing thread finished and entirely pubsubbed before wx had a chance to boot the
        # message.
        
        self._doing_work = True
        
        try:
            
            callables = []
            
            with self._lock:
                
                if len( self._pubsubs ) == 0:
                    
                    return
                    
                
                pubsubs = self._pubsubs
                
                self._pubsubs = []
                
            
            for ( topic, args, kwargs ) in pubsubs:
                
                try:
                    
                    # do all this _outside_ the lock, lol
                    
                    callables = self._GetCallables( topic )
                    
                    # don't want to report the showtext we just send here!
                    not_a_report = topic != 'message'
                    
                    if HG.pubsub_report_mode and not_a_report:
                        
                        HydrusData.ShowText( ( topic, args, kwargs, callables ) )
                        
                    
                    if HG.pubsub_profile_mode and not_a_report:
                        
                        summary = 'Profiling ' + HydrusData.ToHumanInt( len( callables ) ) + ' x ' + topic
                        
                        HydrusData.ShowText( summary )
                        
                        per_summary = 'Profiling ' + topic
                        
                        for callable in callables:
                            
                            try:
                                
                                HydrusData.Profile( per_summary, 'callable( *args, **kwargs )', globals(), locals() )
                                
                            except HydrusExceptions.ShutdownException:
                                
                                return False
                                
                            
                        
                    else:
                        
                        for callable in callables:
                            
                            try:
                                
                                callable( *args, **kwargs )
                                
                            except HydrusExceptions.ShutdownException:
                                
                                return False
                                
                            
                        
                    
                except Exception as e:
                    
                    HydrusData.ShowException( e )
                    
                
            
        finally:
            
            self._doing_work = False
            
        
    
    def pub( self, topic, *args, **kwargs ):
        
        with self._lock:
            
            self._pubsubs.append( ( topic, args, kwargs ) )
            
        
        self._pub_event.set()
        
    
    def pubimmediate( self, topic, *args, **kwargs ):
        
        with self._lock:
            
            callables = self._GetCallables( topic )
            
        
        for callable in callables:
            
            callable( *args, **kwargs )
            
        
    
    def sub( self, object, method_name, topic ):
        
        with self._lock:
            
            if topic not in self._topics_to_objects: self._topics_to_objects[ topic ] = weakref.WeakSet()
            if topic not in self._topics_to_method_names: self._topics_to_method_names[ topic ] = set()
            
            self._topics_to_objects[ topic ].add( object )
            self._topics_to_method_names[ topic ].add( method_name )
            
        
    
    def WaitOnPub( self ):
        
        self._pub_event.wait( 3 )
        
        self._pub_event.clear()
        
    
    def WorkToDo( self ):
        
        with self._lock:
            
            return len( self._pubsubs ) > 0
            
        
