import cProfile
import io
import os
import pstats

from hydrus.core import HydrusData
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusTime

def Profile( summary, code, global_vars, local_vars, min_duration_ms = 20, show_summary = False ):
    
    profile = cProfile.Profile()
    
    started = HydrusTime.GetNowPrecise()
    
    profile.runctx( code, global_vars, local_vars )
    
    finished = HydrusTime.GetNowPrecise()
    
    time_took = finished - started
    time_took_ms = HydrusTime.MillisecondiseS( time_took )
    
    if time_took_ms > min_duration_ms:
        
        output = io.StringIO()
        
        stats = pstats.Stats( profile, stream = output )
        
        stats.strip_dirs()
        
        stats.sort_stats( 'tottime' )
        
        output.write( 'Stats' )
        output.write( os.linesep * 2 )
        
        stats.print_stats()
        
        output.write( 'Callers' )
        output.write( os.linesep * 2 )
        
        stats.print_callers()
        
        output.seek( 0 )
        
        profile_text = output.read()
        
        with HG.profile_counter_lock:
            
            HG.profile_slow_count += 1
            
        
        if show_summary:
            
            HydrusData.ShowText( summary )
            
        
        HG.controller.PrintProfile( summary, profile_text = profile_text )
        
    else:
        
        with HG.profile_counter_lock:
            
            HG.profile_fast_count += 1
            
        
        if show_summary:
            
            HG.controller.PrintProfile( summary )
            
        
    
