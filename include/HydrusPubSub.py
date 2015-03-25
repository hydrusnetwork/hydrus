import HydrusConstants as HC
import Queue
import threading
import traceback
import weakref
import wx
import wx.lib.newevent
import HydrusGlobals

( PubSubEvent, EVT_PUBSUB ) = wx.lib.newevent.NewEvent()

class HydrusPubSub( object ):
    
    def __init__( self ):
        
        self._pubsubs = []
        self._callables = []
        
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
                                
                            except wx.PyDeadObjectError: pass
                            except TypeError as e:
                                
                                if '_wxPyDeadObject' not in str( e ): raise
                                
                            
                        
                    
                
            except: pass
            
        
        return callables
        
    
    def NoJobsQueued( self ):
        
        with self._lock:
            
            return len( self._pubsubs ) == 0
            
        
    
    def WXProcessQueueItem( self ):
        
        # we don't want to map a topic to its callables until the previous topic's callables have been fully executed
        # e.g. when we start a message with a pubsub, it'll take a while (in independant thread-time) for wx to create
        # the dialog and hence map the new callable to the topic. this was leading to messages not being updated
        # because the (short) processing thread finished and entirely pubsubbed before wx had a chance to boot the
        # message.
        
        do_callable = False
        
        with self._lock:
            
            if len( self._callables ) > 0:
                
                ( callable, args, kwargs ) = self._callables.pop( 0 )
                
                do_callable = True
                
            else:
                
                ( topic, args, kwargs ) = self._pubsubs.pop( 0 )
                
                callables = self._GetCallables( topic )
                
                self._callables = [ ( callable, args, kwargs ) for callable in callables ]
                
                for i in range( len( self._callables ) ): wx.PostEvent( wx.GetApp(), PubSubEvent() )
                
            
        
        # do this _outside_ the lock, lol
        if do_callable: callable( *args, **kwargs )
        
    
    def pub( self, topic, *args, **kwargs ):
        
        with self._lock:
            
            self._pubsubs.append( ( topic, args, kwargs ) )
            
            wx.PostEvent( wx.GetApp(), PubSubEvent() )
            
        
    
    def sub( self, object, method_name, topic ):
        
        with self._lock:
            
            if topic not in self._topics_to_objects: self._topics_to_objects[ topic ] = weakref.WeakSet()
            if topic not in self._topics_to_method_names: self._topics_to_method_names[ topic ] = set()
            
            self._topics_to_objects[ topic ].add( object )
            self._topics_to_method_names[ topic ].add( method_name )
            
        
    
    def WXpubimmediate( self, topic, *args, **kwargs ):
        
        with self._lock:
            
            callables = self._GetCallables( topic )
            
            for callable in callables: callable( *args, **kwargs )
            
        
    