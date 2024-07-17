try:
    
    import psutil
    
    PSUTIL_OK = True
    
except Exception as e:
    
    print( str( e ) )
    print( 'psutil failed to import! The program will boot, but several important capabilities will be disabled!' )
    
    PSUTIL_OK = False
    
