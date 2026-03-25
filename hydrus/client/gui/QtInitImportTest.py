import traceback

# this is separate to help out some linting since we are spamming imports here

def get_qt_library_str_status():
    
    infos = []
    
    try:
        
        # noinspection PyUnresolvedReferences
        import PyQt6
        
        infos.append( 'PyQt6 imported ok' )
        
    except Exception as e:
        
        infos.append( 'PyQt6 did not import ok:\n{}'.format( traceback.format_exc() ) )
        
    
    try:
        
        import PySide6
        
        infos.append( 'PySide6 imported ok' )
        
    except Exception as e:
        
        infos.append( 'PySide6 did not import ok:\n{}'.format( traceback.format_exc() ) )
        
    
    return '\n'.join( infos )
    
