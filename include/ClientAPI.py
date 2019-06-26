from . import ClientTags
from . import HydrusData
from . import HydrusExceptions
from . import HydrusGlobals as HG
from . import HydrusSerialisable
import os
import threading

CLIENT_API_PERMISSION_ADD_URLS = 0
CLIENT_API_PERMISSION_ADD_FILES = 1
CLIENT_API_PERMISSION_ADD_TAGS = 2
CLIENT_API_PERMISSION_SEARCH_FILES = 3
CLIENT_API_PERMISSION_MANAGE_PAGES = 4

ALLOWED_PERMISSIONS = ( CLIENT_API_PERMISSION_ADD_FILES, CLIENT_API_PERMISSION_ADD_TAGS, CLIENT_API_PERMISSION_ADD_URLS, CLIENT_API_PERMISSION_SEARCH_FILES, CLIENT_API_PERMISSION_MANAGE_PAGES )

basic_permission_to_str_lookup = {}

basic_permission_to_str_lookup[ CLIENT_API_PERMISSION_ADD_URLS ] = 'add urls for processing'
basic_permission_to_str_lookup[ CLIENT_API_PERMISSION_ADD_FILES ] = 'import files'
basic_permission_to_str_lookup[ CLIENT_API_PERMISSION_ADD_TAGS ] = 'add tags to files'
basic_permission_to_str_lookup[ CLIENT_API_PERMISSION_SEARCH_FILES ] = 'search for files'
basic_permission_to_str_lookup[ CLIENT_API_PERMISSION_MANAGE_PAGES ] = 'manage pages'

SEARCH_RESULTS_CACHE_TIMEOUT = 4 * 3600

SESSION_EXPIRY = 86400

api_request_dialog_open = False
last_api_permissions_request = None

class APIManager( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_CLIENT_API_MANAGER
    SERIALISABLE_NAME = 'Client API Manager'
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._dirty = False
        
        self._access_keys_to_permissions = {}
        
        self._session_keys_to_access_keys_and_expirys = {}
        
        self._lock = threading.Lock()
        
        HG.client_controller.sub( self, 'MaintainMemory', 'memory_maintenance_pulse' )
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_api_permissions_objects = [ api_permissions.GetSerialisableTuple() for api_permissions in self._access_keys_to_permissions.values() ]
        
        return serialisable_api_permissions_objects
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        serialisable_api_permissions_objects = serialisable_info
        
        api_permissions_objects = [ HydrusSerialisable.CreateFromSerialisableTuple( serialisable_api_permissions ) for serialisable_api_permissions in serialisable_api_permissions_objects ]
        
        self._access_keys_to_permissions = { api_permissions.GetAccessKey() : api_permissions for api_permissions in api_permissions_objects }
        
    
    def _SetDirty( self ):
        
        self._dirty = True
        
    
    def AddAccess( self, api_permissions ):
        
        with self._lock:
            
            self._access_keys_to_permissions[ api_permissions.GetAccessKey() ] = api_permissions
            
            self._SetDirty()
            
        
    
    def DeleteAccess( self, access_keys ):
        
        with self._lock:
            
            for access_key in access_keys:
                
                if access_key in self._access_keys_to_permissions:
                    
                    del self._access_keys_to_permissions[ access_key ]
                    
                
            
            self._SetDirty()
            
        
    
    def GenerateSessionKey( self, access_key ):
        
        session_key = HydrusData.GenerateKey()
        
        with self._lock:
            
            self._session_keys_to_access_keys_and_expirys[ session_key ] = ( access_key, HydrusData.GetNow() + SESSION_EXPIRY )
            
        
        return session_key
        
    
    def GetAccessKey( self, session_key ):
        
        with self._lock:
            
            if session_key not in self._session_keys_to_access_keys_and_expirys:
                
                raise HydrusExceptions.DataMissing( 'Did not find an entry for that session key!' )
                
            
            ( access_key, session_expiry ) = self._session_keys_to_access_keys_and_expirys[ session_key ]
            
            if HydrusData.TimeHasPassed( session_expiry ):
                
                del self._session_keys_to_access_keys_and_expirys[ session_expiry ]
                
                raise HydrusExceptions.SessionException( 'That session key has expired!' )
                
            
            self._session_keys_to_access_keys_and_expirys[ session_key ] = ( access_key, HydrusData.GetNow() + SESSION_EXPIRY )
            
        
        return access_key
        
    
    def GetAllPermissions( self ):
        
        return list( self._access_keys_to_permissions.values() )
        
    
    def GetPermissions( self, access_key ):
        
        with self._lock:
            
            if access_key not in self._access_keys_to_permissions:
                
                raise HydrusExceptions.DataMissing( 'Did not find an entry for that access key!' )
                
            
            return self._access_keys_to_permissions[ access_key ]
            
        
    
    def IsDirty( self ):
        
        with self._lock:
            
            return self._dirty
            
        
    
    def MaintainMemory( self ):
        
        with self._lock:
            
            for api_permissions in self._access_keys_to_permissions.values():
                
                api_permissions.MaintainMemory()
                
            
        
    
    def OverwriteAccess( self, api_permissions ):
        
        self.AddAccess( api_permissions )
        
    
    def SetClean( self ):
        
        with self._lock:
            
            self._dirty = False
            
        
    
    def SetPermissions( self, api_permissions_objects ):
        
        with self._lock:
            
            self._access_keys_to_permissions = { api_permissions.GetAccessKey() : api_permissions for api_permissions in api_permissions_objects }
            
            self._SetDirty()
            
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_CLIENT_API_MANAGER ] = APIManager

class APIPermissions( HydrusSerialisable.SerialisableBaseNamed ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_CLIENT_API_PERMISSIONS
    SERIALISABLE_NAME = 'Client API Permissions'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, name = 'new api permissions', access_key = None, basic_permissions = None, search_tag_filter = None ):
        
        if access_key is None:
            
            access_key = HydrusData.GenerateKey()
            
        
        if basic_permissions is None:
            
            basic_permissions = set()
            
        
        if search_tag_filter is None:
            
            search_tag_filter = ClientTags.TagFilter()
            
        
        HydrusSerialisable.SerialisableBaseNamed.__init__( self, name )
        
        self._access_key = access_key
        
        self._basic_permissions = set( basic_permissions )
        self._search_tag_filter = search_tag_filter
        
        self._last_search_results = None
        self._search_results_timeout = 0
        
        self._lock = threading.Lock()
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_access_key = self._access_key.hex()
        
        serialisable_basic_permissions = list( self._basic_permissions )
        serialisable_search_tag_filter = self._search_tag_filter.GetSerialisableTuple()
        
        return ( serialisable_access_key, serialisable_basic_permissions, serialisable_search_tag_filter )
        
    
    def _HasPermission( self, permission ):
        
        return permission in self._basic_permissions
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_access_key, serialisable_basic_permissions, serialisable_search_tag_filter ) = serialisable_info
        
        self._access_key = bytes.fromhex( serialisable_access_key )
        
        self._basic_permissions = set( serialisable_basic_permissions )
        self._search_tag_filter = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_search_tag_filter )
        
    
    def CheckCanSearchTags( self, tags ):
        
        with self._lock:
            
            if self._search_tag_filter.AllowsEverything():
                
                return
                
            
            if len( tags ) > 0:
                
                filtered_tags = self._search_tag_filter.Filter( tags )
                
                if len( filtered_tags ) > 0:
                    
                    return
                    
                
            
            raise HydrusExceptions.InsufficientCredentialsException( 'You do not have permission to do this search. Your tag search permissions are: {}'.format( self._search_tag_filter.ToPermittedString() ) )
            
        
    
    def CheckCanSeeAllFiles( self ):
        
        with self._lock:
            
            if not ( self._HasPermission( CLIENT_API_PERMISSION_SEARCH_FILES ) and self._search_tag_filter.AllowsEverything() ):
                
                raise HydrusExceptions.InsufficientCredentialsException( 'You do not have permission to see all files, so you cannot do this.' )
                
            
        
    
    def CheckPermission( self, permission ):
        
        if not self.HasPermission( permission ):
            
            raise HydrusExceptions.InsufficientCredentialsException( 'You do not have permission to: {}'.format( basic_permission_to_str_lookup[ permission ] ) )
            
        
    
    def CheckPermissionToSeeFiles( self, hash_ids ):
        
        with self._lock:
            
            if self._search_tag_filter.AllowsEverything():
                
                return
                
            
            if self._last_search_results is None:
                
                raise HydrusExceptions.BadRequestException( 'It looks like those search results are no longer available--please run the search again!' )
                
            
            num_files_asked_for = len( hash_ids )
            num_files_allowed_to_see = len( self._last_search_results.intersection( hash_ids ) )
            
            if num_files_allowed_to_see != num_files_asked_for:
                
                error_text = 'You do not seem to have access to all those files! You asked to see {} files, but you were only authorised to see {} of them!'
                
                error_text = error_text.format( HydrusData.ToHumanInt( num_files_asked_for ), HydrusData.ToHumanInt( num_files_allowed_to_see ) )
                
                raise HydrusExceptions.InsufficientCredentialsException( error_text )
                
            
            self._search_results_timeout = HydrusData.GetNow() + SEARCH_RESULTS_CACHE_TIMEOUT
            
        
    
    def GenerateNewAccessKey( self ):
        
        with self._lock:
            
            self._access_key = HydrusData.GenerateKey()
            
        
    
    def GetAccessKey( self ):
        
        with self._lock:
            
            return self._access_key
            
        
    
    def GetAdvancedPermissionsString( self ):
        
        with self._lock:
            
            p_strings = []
            
            if self._HasPermission( CLIENT_API_PERMISSION_SEARCH_FILES ):
                
                p_strings.append( 'Can search: ' + self._search_tag_filter.ToPermittedString() )
                
            
            return ''.join( p_strings )
            
        
    
    def GetBasicPermissions( self ):
        
        with self._lock:
            
            return self._basic_permissions
            
        
    
    def GetBasicPermissionsString( self ):
        
        with self._lock:
            
            l = [ basic_permission_to_str_lookup[ p ] for p in self._basic_permissions ]
            
            l.sort()
            
            return ', '.join( l )
            
        
    
    def GetSearchTagFilter( self ):
        
        with self._lock:
            
            return self._search_tag_filter
            
        
    
    def HasPermission( self, permission ):
        
        with self._lock:
            
            return self._HasPermission( permission )
            
        
    
    def MaintainMemory( self ):
        
        with self._lock:
            
            if self._last_search_results is not None and HydrusData.TimeHasPassed( self._search_results_timeout ):
                
                self._last_search_results = None
                
            
        
    
    def SetLastSearchResults( self, hash_ids ):
        
        with self._lock:
            
            if self._search_tag_filter.AllowsEverything():
                
                return
                
            
            self._last_search_results = set( hash_ids )
            
            self._search_results_timeout = HydrusData.GetNow() + SEARCH_RESULTS_CACHE_TIMEOUT
            
        
    
    def SetSearchTagFilter( self, search_tag_filter ):
        
        with self._lock:
            
            self._search_tag_filter = search_tag_filter
            
        
    
    def ToHumanString( self ):
        
        s = 'API Permissions ({}): '.format( self._name )
        
        basic_string = self.GetBasicPermissionsString()
        advanced_string = self.GetAdvancedPermissionsString()
        
        if len( basic_string ) == '':
            
            s += 'does not have permission to do anything'
            
        else:
            
            s += basic_string
            
            if len( advanced_string ) > 0:
                
                s += ': ' + advanced_string
                
            
        
        return s
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_CLIENT_API_PERMISSIONS ] = APIPermissions
