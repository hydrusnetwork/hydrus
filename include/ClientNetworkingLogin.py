import ClientConstants as CC
import HydrusConstants as HC
import HydrusGlobals as HG
import HydrusData
import HydrusExceptions

VALIDITY_VALID = 0
VALIDITY_UNTESTED = 1
VALIDITY_INVALID = 2

# make this serialisable
class LoginCredentials( object ):
    
    def __init__( self ):
        
        self._credentials = {} # user-facing name (unique) : string
        
    
    # get current values
    
    # test current values, including fail for not having enough/having too many

# make this serialisable
class LoginScript( object ):
    
    def __init__( self ):
        
        self._network_context = None
        self._login_steps = []
        self._validity = VALIDITY_UNTESTED
        
        self._temp_variables = {}
        
    
    def Start( self, controller, credentials ):
        
        # this maybe takes some job_key or something so it can present to the user login process status
        # this will be needed in the dialog where we test this. we need good feedback on how it is going
        
        for step in self._login_steps:
            
            try:
                
                step.Start( controller, credentials, self._temp_variables )
                
            except HydrusExceptions.VetoException: # or something--invalidscript exception?
                
                # also figure out a way to deal with connection errors and so on which will want a haderror time delay before giving it another go
                
                self._validity = VALIDITY_INVALID
                
                return False
                
            
        
        return True
        
    
    def GetRequiredCredentials( self ):
        
        required_creds = []
        
        for step in self._login_steps:
            
            required_creds.extend( step.GetRequiredCredentials() ) # user facing name : string match
            
        
        return required_creds
        
    
LOGIN_PARAMETER_TYPE_PARAMETER = 0
LOGIN_PARAMETER_TYPE_COOKIE = 1
LOGIN_PARAMETER_TYPE_HEADER = 2

# make this serialisable
class LoginStep( object ):
    
    def __init__( self ):
        
        self._method = None # get/post
        self._url = 'blah' # maybe this should be split up more?
        
        self._statics = [] # type | arg name | string
        
        self._credentials = [] # type | user-facing name (unique) | arg name | string match
        
        self._temps = [] # type | arg name
        
        self._expected_cookies = [] # name | string match
        
        self._veto_scripts = [] # list of scripts that can veto
        
        self._temp_variable_scripts = [] # name | script that produces a single bit of text or vetoes
        
    
    def Start( self, controller, credentials, temp_variables ):
        
        # construct the url, failing if creds or temps missing
        
        # hit the url, failing on connection fault or whatever
        
        # throw the response at veto parsing gubbins, failing appropriately
        
        # throw the response at variable parsing gubbins, failing appropriately
        
        pass
        
    

