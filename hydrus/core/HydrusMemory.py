from hydrus.core import HydrusData

try:
    
    import pympler
    
    from pympler import asizeof
    from pympler import muppy
    from pympler import summary
    from pympler import classtracker
    from pympler import tracker
    
    PYMPLER_OK = True
    
except Exception as e:
    
    PYMPLER_OK = False
    

CURRENT_TRACKER = None

# good examples here:
# https://pympler.readthedocs.io/en/latest/muppy.html#muppy
# this can do other stuff, class tracking and even charts with matplotlib

# pretty sure the Client should only ever call this stuff on the GUI thread of course, since it'll be touching Qt stuff

def CheckPymplerOK():
    
    if not PYMPLER_OK:
        
        raise Exception( 'Pympler is not available!' )
        
    

def PrintCurrentMemoryUse( classes_to_track = None ):
    
    CheckPymplerOK()
    
    HydrusData.Print( '---printing memory use to log---' )
    
    all_objects = muppy.get_objects()
    
    sm = summary.summarize( all_objects )
    
    summary.print_( sm, limit = 500 )
    
    HydrusData.DebugPrint( '----memory-use snapshot done----' )
    
    if classes_to_track is None:
        
        return
        
    
    HydrusData.Print( '----printing class use to log---' )
    
    ct = classtracker.ClassTracker()
    
    for o in all_objects:
        
        if isinstance( o, classes_to_track ):
            
            ct.track_object( o )
            
        
    
    ct.create_snapshot()
    
    ct.stats.print_summary()
    
    HydrusData.DebugPrint( '-----class-use snapshot done----' )
    

def PrintSnapshotDiff():
    
    CheckPymplerOK()
    
    global CURRENT_TRACKER
    
    if CURRENT_TRACKER is None:
        
        TakeMemoryUseSnapshot()
        
    
    HydrusData.Print( '---printing memory diff to log--' )
    
    # noinspection PyUnresolvedReferences
    diff = CURRENT_TRACKER.diff()
    
    summary.print_( diff, limit = 500 )
    
    HydrusData.DebugPrint( '----memory-use snapshot done----' )
    

def TakeMemoryUseSnapshot():
    
    global CURRENT_TRACKER
    
    CURRENT_TRACKER = tracker.SummaryTracker()
    
