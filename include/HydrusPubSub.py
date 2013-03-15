import Queue
import threading
import traceback
import weakref
import wx
import wx.lib.newevent

( PubSubEvent, EVT_PUBSUB ) = wx.lib.newevent.NewEvent()

class HydrusPubSub():
    
    def __init__( self ):
        
        self._pubsubs = Queue.Queue()
        
        self._lock = threading.Lock()
        
        self._topics_to_objects = {}
        self._topics_to_method_names = {}
        
    
    def GetQueue( self ): return self._pubsubs
    
    def pub( self, topic, *args, **kwargs ):
        
        with self._lock:
            
            if topic in self._topics_to_objects:
                
                try:
                    
                    objects = self._topics_to_objects[ topic ]
                    
                    for object in objects:
                        
                        method_names = self._topics_to_method_names[ topic ]
                        
                        for method_name in method_names:
                            
                            if hasattr( object, method_name ):
                                
                                try:
                                    
                                    self._pubsubs.put( ( getattr( object, method_name ), args, kwargs ) )
                                    
                                    wx.PostEvent( wx.GetApp(), PubSubEvent() )
                                    
                                except wx.PyDeadObjectError: pass
                                except: print( topic + ' for ' + str( object ) + ' bound to ' + method_name + os.linesep + traceback.format_exc() )
                                
                            
                        
                    
                except: pass
                
            
        
    
    def pubimmediate( self, topic, *args, **kwargs ):
        
        with self._lock:
            
            if topic in self._topics_to_objects:
                
                try:
                    
                    objects = self._topics_to_objects[ topic ]
                    
                    for object in objects:
                        
                        method_names = self._topics_to_method_names[ topic ]
                        
                        for method_name in method_names:
                            
                            if hasattr( object, method_name ):
                                
                                try: getattr( object, method_name )( *args, **kwargs )
                                except wx.PyDeadObjectError: pass
                                except: print( topic + ' for ' + str( object ) + ' bound to ' + method_name + os.linesep + traceback.format_exc() )
                                
                            
                        
                    
                except RuntimeError: pass # sometimes the set changes size during iteration, which is a bug I haven't tracked down
                except wx.PyDeadObjectError: pass
                except TypeError: pass
                except: print( traceback.format_exc() )
                
            
        
    
    def sub( self, object, method_name, topic ):
        
        with self._lock:
            
            if topic not in self._topics_to_objects: self._topics_to_objects[ topic ] = weakref.WeakSet()
            if topic not in self._topics_to_method_names: self._topics_to_method_names[ topic ] = set()
            
            self._topics_to_objects[ topic ].add( object )
            self._topics_to_method_names[ topic ].add( method_name )
            
        
    