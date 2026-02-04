import os

from hydrus.core import HydrusData

def SetRequestsCABundleEnv( pem_path = None ):
    
    # TODO: we could initialise this with a custom pem in launch args pretty easy if we wanted to!
    # but tbh the user can already set it in the launch env anyway so maybe whatever
    
    if pem_path is None:
        
        try:
            
            import certifi
            
            pem_path = certifi.where()
            
        except Exception as e:
            
            pass
            
        
    
    env_var_name = 'REQUESTS_CA_BUNDLE'
    
    if env_var_name in os.environ:
        
        if pem_path is None or os.environ[ env_var_name ] != pem_path:
            
            HydrusData.Print( f'Custom REQUESTS_CA_BUNDLE: {os.environ[env_var_name]}')
            
        
        return
        
    
    # could say "If CURL_CA_BUNDLE exists, use that instead of certifi"
    
    if pem_path is None:
        
        HydrusData.Print( 'No certifi, so cannot set REQUESTS_CA_BUNDLE.' )
        
        return
        
    
    if os.path.exists( pem_path ):
        
        os.environ[ env_var_name ] = pem_path
        
    else:
        
        HydrusData.Print( f'The given CA Bundle at "{pem_path}" does not exist, so cannot set REQUESTS_CA_BUNDLE!' )
        
    
