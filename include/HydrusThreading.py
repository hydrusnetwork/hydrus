import collections
import HydrusConstants as HC
import itertools
import os
import Queue
import random
import threading
import time
import traceback
import wx
import HydrusData
import HydrusGlobals

class DAEMON( threading.Thread ):
    
    def __init__( self, name, period = 1200 ):
        
        threading.Thread.__init__( self, name = name )
        
        self._name = name
        
        self._event = threading.Event()
        
        HydrusGlobals.pubsub.sub( self, 'shutdown', 'shutdown' )
        
    
    def shutdown( self ): self._event.set()
    
class DAEMONQueue( DAEMON ):
    
    def __init__( self, name, callable, queue_topic, period = 10 ):
        
        DAEMON.__init__( self, name )
        
        self._callable = callable
        self._queue = Queue.Queue()
        self._queue_topic = queue_topic
        self._period = period
        
        HydrusGlobals.pubsub.sub( self, 'put', queue_topic )
        
        self.start()
        
    
    def put( self, data ): self._queue.put( data )
    
    def run( self ):
        
        time.sleep( 3 )
        
        while True:
            
            while self._queue.empty():
                
                if HydrusGlobals.shutdown: return
                
                self._event.wait( self._period )
                
                self._event.clear()
                
            
            while wx.GetApp().JustWokeFromSleep():
                
                if HydrusGlobals.shutdown: return
                
                time.sleep( 10 )
                
            
            items = []
            
            while not self._queue.empty(): items.append( self._queue.get() )
            
            try:
                
                self._callable( items )
                
            except Exception as e:
                
                HydrusData.ShowException( e )
                
            
        
    
class DAEMONWorker( DAEMON ):
    
    def __init__( self, name, callable, topics = None, period = 1200, init_wait = 3, pre_callable_wait = 3 ):
        
        if topics is None: topics = []
        
        DAEMON.__init__( self, name )
        
        self._callable = callable
        self._topics = topics
        self._period = period
        self._init_wait = init_wait
        self._pre_callable_wait = pre_callable_wait
        
        for topic in topics: HydrusGlobals.pubsub.sub( self, 'set', topic )
        
        self.start()
        
    
    def run( self ):
        
        self._event.wait( self._init_wait )
        
        while True:
            
            if HydrusGlobals.shutdown: return
            
            time.sleep( self._pre_callable_wait )
            
            while wx.GetApp().JustWokeFromSleep():
                
                if HydrusGlobals.shutdown: return
                
                time.sleep( 10 )
                
            
            try: self._callable()
            except Exception as e:
                
                HydrusData.ShowText( 'Daemon ' + self._name + ' encountered an exception:' )
                
                HydrusData.ShowException( e )
                
            
            if HydrusGlobals.shutdown: return
            
            self._event.wait( self._period )
            
            self._event.clear()
            
        
    
    def set( self, *args, **kwargs ): self._event.set()
    
class DAEMONCallToThread( DAEMON ):
    
    def __init__( self ):
        
        DAEMON.__init__( self, 'CallToThread' )
        
        self._queue = Queue.Queue()
        
        self.start()
        
    
    def put( self, callable, *args, **kwargs ):
        
        self._queue.put( ( callable, args, kwargs ) )
        
        self._event.set()
        
    
    def run( self ):
        
        while True:
            
            while self._queue.empty():
                
                if HydrusGlobals.shutdown: return
                
                self._event.wait( 1200 )
                
                self._event.clear()
                
            
            try:
                
                ( callable, args, kwargs ) = self._queue.get()
                
                callable( *args, **kwargs )
                
                del callable
                
            except Exception as e:
                
                HydrusData.ShowException( e )
                
            
            time.sleep( 0.00001 )
            
        
    
call_to_threads = [ DAEMONCallToThread() for i in range( 10 ) ]

def CallToThread( callable, *args, **kwargs ):
    
    call_to_thread = random.choice( call_to_threads )
    
    while call_to_thread == threading.current_thread: call_to_thread = random.choice( call_to_threads )
    
    call_to_thread.put( callable, *args, **kwargs )
    
def CallBlockingToWx( callable, *args, **kwargs ):
    
    def wx_code( job_key ):
        
        try:
            
            result = callable( *args, **kwargs )
            
            job_key.SetVariable( 'result', result )
            
        except Exception as e:
            
            print( 'CallBlockingToWx just caught this error:' )
            print( traceback.format_exc() )
            
            job_key.SetVariable( 'error', e )
            
        finally: job_key.Finish()
        
    
    job_key = HydrusData.JobKey()
    
    job_key.Begin()
    
    wx.CallAfter( wx_code, job_key )
    
    while not job_key.IsDone():
        
        if HydrusGlobals.shutdown: return
        
        time.sleep( 0.05 )
        
    
    if job_key.HasVariable( 'result' ): return job_key.GetVariable( 'result' )
    else: raise job_key.GetVariable( 'error' )
    