import os

from hydrus.core import HydrusData

def DumpEnv( env = None ):
    
    if env is None:
        
        env = os.environ.copy()
        
    
    rows = []
    
    for ( key, value ) in sorted( env.items() ):
        
        if ( 'PATH' in key or 'DIRS' in key ) and os.pathsep in value:
            
            rows.append( f'{key}:' )
            
            sub_values = value.split( os.pathsep )
            
            for sub_value in sub_values:
                
                rows.append( f'    {sub_value}' )
                
            
        else:
            
            rows.append( f'{key}: {value}' )
            
        
    
    HydrusData.ShowText( 'Full environment:\n' + '\n'.join( rows ) )
    
