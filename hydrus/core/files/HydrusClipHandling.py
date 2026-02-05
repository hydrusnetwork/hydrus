import sqlite3

from hydrus.core import HydrusExceptions
from hydrus.core import HydrusTemp

def ExtractDBPNGToPath( path, temp_path ):
    
    ( os_file_handle, sqlite_temp_path ) = HydrusTemp.GetTempPath()
    
    try:
        
        ( db, c ) = GetSQLiteDB( path, sqlite_temp_path )
        
        try:
            
            ( png_bytes, ) = c.execute( 'SELECT ImageData FROM CanvasPreview;' ).fetchone()
            
            with open( temp_path, 'wb' ) as f:
                
                f.write( png_bytes )
                
            
        finally:
            
            c.close()
            
            db.close()
            
        
    except Exception as e:
        
        raise HydrusExceptions.NoThumbnailFileException()
        
    finally:
        
        HydrusTemp.CleanUpTempPath( os_file_handle, sqlite_temp_path )
        
    

def GetClipProperties( path ):
    
    ( os_file_handle, sqlite_temp_path ) = HydrusTemp.GetTempPath()
    
    num_frames = None
    duration_ms = None
    
    try:
        
        ( db, c ) = GetSQLiteDB( path, sqlite_temp_path )
        
        try:
            
            ( width_float, height_float, canvas_unit, canvas_dpi_float ) = c.execute( 'SELECT CanvasWidth, CanvasHeight, CanvasUnit, CanvasResolution FROM Canvas;' ).fetchone()
            
            if c.execute( 'SELECT 1 FROM sqlite_master WHERE name = "TimeLine";' ).fetchone() is not None:
                
                try:
                    
                    result = c.execute( 'SELECT StartFrame, FrameRate, EndFrame from TimeLine;' ).fetchone()
                    
                    if result is not None:
                        
                        ( start_frame_float, framerate_float, end_frame_float ) = result
                        
                        num_frames = int( end_frame_float - start_frame_float )
                        
                        if framerate_float == 0:
                            
                            framerate_float = 24.0
                            
                        
                        duration_s = num_frames / framerate_float
                        
                        duration_ms = duration_s * 1000
                        
                    
                except Exception as e:
                    
                    pass
                    
                
            
        finally:
            
            c.close()
            
            db.close()
            
        
    finally:
        
        HydrusTemp.CleanUpTempPath( os_file_handle, sqlite_temp_path )
        
    
    # ok the deal here is that width and height is in the canvas units, which might be mm or inches instead of pixels
    # the 'resolution' however is always in DPI lmaaaoooooo, so to get pixels we just have to normalise to that
    
    unit_conversion_multiplier = 1
    
    if canvas_unit == 0:
        
        # width and height are in pixels
        
        unit_conversion_multiplier = 1
        
    elif canvas_unit == 1:
        
        # cm
        cm_in_an_inch = 2.54
        
        unit_conversion_multiplier = canvas_dpcm_float = canvas_dpi_float / cm_in_an_inch
        
    elif canvas_unit == 2:
        
        # mm
        mm_in_an_inch = 25.4
        
        unit_conversion_multiplier = canvas_dpmm_float = canvas_dpi_float / mm_in_an_inch
        
    elif canvas_unit == 3:
        
        # inches
        
        unit_conversion_multiplier = canvas_dpi_float
        
    elif canvas_unit == 5:
        
        # pt, lmao
        points_in_an_inch = 72
        
        unit_conversion_multiplier = canvas_dpp_float = canvas_dpi_float / points_in_an_inch
        
    
    return ( ( round( width_float * unit_conversion_multiplier ), round( height_float * unit_conversion_multiplier ) ), duration_ms, num_frames )
    

def GetSQLiteDB( path, sqlite_temp_path ):
    
    with open( path, 'rb' ) as f:
        
        clip_bytes = f.read()
        
    
    SQLITE_START = b'SQLite format 3'
    
    try:
        
        i = clip_bytes.index( SQLITE_START )
        
    except IndexError:
        
        raise HydrusExceptions.DamagedOrUnusualFileException( 'This clip file had no internal SQLite file!' )
        
    
    sqlite_bytes = clip_bytes[ i : ]
    
    with open( sqlite_temp_path, 'wb' ) as f:
        
        f.write( sqlite_bytes )
        
    
    try:
        
        db = sqlite3.connect( sqlite_temp_path, isolation_level = None, detect_types = sqlite3.PARSE_DECLTYPES )
        
        c = db.cursor()
        
    except Exception as e:
        
        raise HydrusExceptions.DamagedOrUnusualFileException( 'This clip file seemed to have an invalid internal SQLite file!' )
        
    
    return ( db, c )
    
