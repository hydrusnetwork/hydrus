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

class DAEMON( threading.Thread ):
    
    def __init__( self, name, period = 1200 ):
        
        threading.Thread.__init__( self, name = name )
        
        self._name = name
        
        self._event = threading.Event()
        
        HC.pubsub.sub( self, 'shutdown', 'shutdown' )
        
    
    def shutdown( self ): self._event.set()
    
class DAEMONQueue( DAEMON ):
    
    def __init__( self, name, callable, queue_topic, period = 10 ):
        
        DAEMON.__init__( self, name )
        
        self._callable = callable
        self._queue = Queue.Queue()
        self._queue_topic = queue_topic
        self._period = period
        
        HC.pubsub.sub( self, 'put', queue_topic )
        
        self.start()
        
    
    def put( self, data ): self._queue.put( data )
    
    def run( self ):
        
        time.sleep( 3 )
        
        while True:
            
            while self._queue.empty():
                
                if HC.shutdown: return
                
                self._event.wait( self._period )
                
                self._event.clear()
                
            
            while HC.app.JustWokeFromSleep():
                
                if HC.shutdown: return
                
                time.sleep( 10 )
                
            
            items = []
            
            while not self._queue.empty(): items.append( self._queue.get() )
            
            try:
                
                self._callable( items )
                
            except Exception as e:
                
                HC.ShowException( e )
                
            
        
    
class DAEMONWorker( DAEMON ):
    
    def __init__( self, name, callable, topics = [], period = 1200, init_wait = 3, pre_callable_wait = 3 ):
        
        DAEMON.__init__( self, name )
        
        self._callable = callable
        self._topics = topics
        self._period = period
        self._init_wait = init_wait
        self._pre_callable_wait = pre_callable_wait
        
        for topic in topics: HC.pubsub.sub( self, 'set', topic )
        
        self.start()
        
    
    def run( self ):
        
        self._event.wait( self._init_wait )
        
        while True:
            
            if HC.shutdown: return
            
            time.sleep( self._pre_callable_wait )
            
            while HC.app.JustWokeFromSleep():
                
                if HC.shutdown: return
                
                time.sleep( 10 )
                
            
            try: self._callable()
            except Exception as e:
                
                HC.ShowText( 'Daemon ' + self._name + ' encountered an exception:' )
                
                HC.ShowException( e )
                
            
            if HC.shutdown: return
            
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
                
                if HC.shutdown: return
                
                self._event.wait( 1200 )
                
                self._event.clear()
                
            
            try:
                
                ( callable, args, kwargs ) = self._queue.get()
                
                callable( *args, **kwargs )
                
                del callable
                
            except Exception as e:
                
                HC.ShowException( e )
                
            
            time.sleep( 0.00001 )
            
        
    
call_to_threads = [ DAEMONCallToThread() for i in range( 10 ) ]

def CallToThread( callable, *args, **kwargs ):
    
    call_to_thread = random.choice( call_to_threads )
    
    while call_to_thread == threading.current_thread: call_to_thread = random.choice( call_to_threads )
    
    call_to_thread.put( callable, *args, **kwargs )
    