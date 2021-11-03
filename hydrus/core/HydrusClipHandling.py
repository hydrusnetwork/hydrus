import sqlite3

from hydrus.core import HydrusExceptions
from hydrus.core import HydrusTemp

def ExtractDBPNGToPath( path, temp_path ):
    
    ( os_file_handle, sqlite_temp_path ) = HydrusTemp.GetTempPath()
    
    db = None
    c = None
    
    try:
        
        ( db, c ) = GetSQLiteDB( path, sqlite_temp_path )
        
        ( png_bytes, ) = c.execute( 'SELECT ImageData FROM CanvasPreview;' ).fetchone()
        
        with open( temp_path, 'wb' ) as f:
            
            f.write( png_bytes )
            
        
    finally:
        
        if c is not None:
            
            c.close()
            
        
        if db is not None:
            
            db.close()
            
        
        HydrusTemp.CleanUpTempPath( os_file_handle, sqlite_temp_path )
        
    
def GetResolution( path ):
    
    ( os_file_handle, sqlite_temp_path ) = HydrusTemp.GetTempPath()
    
    db = None
    c = None
    
    try:
        
        ( db, c ) = GetSQLiteDB( path, sqlite_temp_path )
        
        ( width_float, height_float ) = c.execute( 'SELECT CanvasWidth, CanvasHeight FROM Canvas;' ).fetchone()
        
    finally:
        
        if c is not None:
            
            c.close()
            
        
        if db is not None:
            
            db.close()
            
        
        HydrusTemp.CleanUpTempPath( os_file_handle, sqlite_temp_path )
        
    
    return ( int( width_float ), int( height_float ) )
    
def GetSQLiteDB( path, sqlite_temp_path ):
    
    with open( path, 'rb' ) as f:
        
        clip_bytes = f.read()
        
    
    SQLITE_START = b'SQLite format 3'
    
    try:
        
        i = clip_bytes.index( SQLITE_START )
        
    except IndexError:
        
        raise HydrusExceptions.DamagedOrUnusualFileException( 'This clip file had no internal SQLite file, so no PNG thumb could be extracted!' )
        
    
    sqlite_bytes = clip_bytes[ i : ]
    
    with open( sqlite_temp_path, 'wb' ) as f:
        
        f.write( sqlite_bytes )
        
    
    try:
        
        db = sqlite3.connect( sqlite_temp_path, isolation_level = None, detect_types = sqlite3.PARSE_DECLTYPES )
        
        c = db.cursor()
        
    except:
        
        raise HydrusExceptions.DamagedOrUnusualFileException( 'This clip file seemed to have an invalid internal SQLite file!' )
        
    
    return ( db, c )
    
