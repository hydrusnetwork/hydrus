import collections
import HydrusConstants as HC
import HydrusData
import HydrusExceptions
import HydrusGlobals
import HydrusNetworking
import HydrusSerialisable
import threading

INT_PARAMS = { 'expires', 'num', 'since', 'content_type', 'action', 'status' }
BYTE_PARAMS = { 'access_key', 'account_type_key', 'subject_account_key', 'hash', 'registration_key', 'subject_hash', 'subject_tag', 'share_key', 'update_hash' }

def GenerateDefaultServiceDictionary( service_type ):
    
    dictionary = HydrusSerialisable.SerialisableDictionary()
    
    dictionary[ 'upnp_port' ] = None
    dictionary[ 'bandwidth_tracker' ] = HydrusNetworking.BandwidthTracker()
    
    if service_type in HC.RESTRICTED_SERVICES:
        
        dictionary[ 'bandwidth_rules' ] = HydrusNetworking.BandwidthRules()
        
        if service_type in HC.REPOSITORIES:
            
            metadata = Metadata()
            
            now = HydrusData.GetNow()
            
            update_hashes = []
            begin = 0
            end = now
            next_update_due = now + HC.UPDATE_DURATION
            
            metadata.AppendUpdate( update_hashes, begin, end, next_update_due )
            
            dictionary[ 'metadata' ] = metadata
            
            if service_type == HC.FILE_REPOSITORY:
                
                dictionary[ 'log_uploader_ips' ] = False
                dictionary[ 'max_storage' ] = None
                
            
        
        if service_type == HC.SERVER_ADMIN:
            
            dictionary[ 'server_bandwidth_tracker' ] = HydrusNetworking.BandwidthTracker()
            dictionary[ 'server_bandwidth_rules' ] = HydrusNetworking.BandwidthRules()
            
        
    
    return dictionary
    
def GenerateService( service_key, service_type, name, port, dictionary = None ):
    
    if dictionary is None:
        
        dictionary = GenerateDefaultServiceDictionary( service_type )
        
    
    if service_type == HC.SERVER_ADMIN:
        
        cl = ServerServiceAdmin
        
    elif service_type == HC.TAG_REPOSITORY:
        
        cl = ServerServiceRepositoryTag
        
    elif service_type == HC.FILE_REPOSITORY:
        
        cl = ServerServiceRepositoryFile
        
    
    return cl( service_key, service_type, name, port, dictionary )
    
def GenerateServiceFromSerialisableTuple( ( service_key_encoded, service_type, name, port, dictionary_string ) ):
    
    try:
        
        service_key = service_key_encoded.decode( 'hex' )
        
    except TypeError:
        
        raise HydrusExceptions.ForbiddenException( 'Could not decode that service key!' )
        
    
    dictionary = HydrusSerialisable.CreateFromString( dictionary_string )
    
    return GenerateService( service_key, service_type, name, port, dictionary )
    
def GetPossiblePermissions( service_type ):
    
    permissions = []
    
    permissions.append( ( HC.CONTENT_TYPE_ACCOUNTS, [ None, HC.PERMISSION_ACTION_CREATE, HC.PERMISSION_ACTION_OVERRULE ] ) )
    permissions.append( ( HC.CONTENT_TYPE_ACCOUNT_TYPES, [ None, HC.PERMISSION_ACTION_OVERRULE ] ) )
    
    if service_type == HC.FILE_REPOSITORY:
        
        permissions.append( ( HC.CONTENT_TYPE_FILES, [ None, HC.PERMISSION_ACTION_PETITION, HC.PERMISSION_ACTION_CREATE, HC.PERMISSION_ACTION_OVERRULE ] ) )
        
    elif service_type == HC.TAG_REPOSITORY:
        
        permissions.append( ( HC.CONTENT_TYPE_MAPPINGS, [ None, HC.PERMISSION_ACTION_PETITION, HC.PERMISSION_ACTION_CREATE, HC.PERMISSION_ACTION_OVERRULE ] ) )
        permissions.append( ( HC.CONTENT_TYPE_TAG_PARENTS, [ None, HC.PERMISSION_ACTION_PETITION, HC.PERMISSION_ACTION_OVERRULE ] ) )
        permissions.append( ( HC.CONTENT_TYPE_TAG_SIBLINGS, [ None, HC.PERMISSION_ACTION_PETITION, HC.PERMISSION_ACTION_OVERRULE ] ) )
        
    elif service_type == HC.SERVER_ADMIN:
        
        permissions.append( ( HC.CONTENT_TYPE_SERVICES, [ None, HC.PERMISSION_ACTION_OVERRULE ] ) )
        
    
    return permissions
    
def DumpToBodyString( args ):
    
    if not isinstance( args, HydrusSerialisable.SerialisableBase ):
        
        args = HydrusSerialisable.SerialisableDictionary( args )
        
    
    if 'access_key' in args:
        
        args[ 'access_key' ] = args[ 'access_key' ].encode( 'hex' )
        
    
    if 'account' in args:
        
        args[ 'account' ] = Account.GenerateSerialisableTupleFromAccount( args[ 'account' ] )
        
    
    if 'accounts' in args:
        
        args[ 'accounts' ] = map( Account.GenerateSerialisableTupleFromAccount, args[ 'accounts' ] )
        
    
    if 'account_types' in args:
        
        args[ 'account_types' ] = [ account_type.ToSerialisableTuple() for account_type in args[ 'account_types' ] ]
        
    
    if 'registration_keys' in args:
        
        args[ 'registration_keys' ] = [ registration_key.encode( 'hex' ) for registration_key in args[ 'registration_keys' ] ]
        
    
    if 'service_keys_to_access_keys' in args:
        
        args[ 'service_keys_to_access_keys' ] = [ ( service_key.encode( 'hex' ), access_key.encode( 'hex' ) ) for ( service_key, access_key ) in args[ 'service_keys_to_access_keys' ].items() ]
        
    
    if 'services' in args:
        
        args[ 'services' ] = [ service.ToSerialisableTuple() for service in args[ 'services' ] ]
        
    
    body = args.DumpToNetworkString()
    
    return body
    
def DumpToGETQuery( args ):
    
    if 'subject_identifier' in args:
        
        subject_identifier = args[ 'subject_identifier' ]
        
        del args[ 'subject_identifier' ]
        
        if subject_identifier.HasAccountKey():
            
            account_key = subject_identifier.GetData()
            
            args[ 'subject_account_key' ] = account_key
            
        elif subject_identifier.HasContent():
            
            content = subject_identifier.GetData()
            
            content_type = content.GetContentType()
            content_data = content.GetContentData()
            
            if content_type == HC.CONTENT_TYPE_FILES:
                
                hash = content_data[0]
                
                args[ 'subject_hash' ] = hash
                
            elif content_type == HC.CONTENT_TYPE_MAPPING:
                
                ( tag, hash ) = content_data
                
                args[ 'subject_hash' ] = hash
                args[ 'subject_tag' ] = tag
                
            
        
    
    for name in BYTE_PARAMS:
        
        if name in args:
            
            args[ name ] = args[ name ].encode( 'hex' )
            
        
    
    query = '&'.join( [ key + '=' + HydrusData.ToByteString( value ) for ( key, value ) in args.items() ] )
    
    return query
    
def ParseBodyString( json_string ):
    
    args = HydrusSerialisable.CreateFromNetworkString( json_string )
    
    if 'access_key' in args:
        
        args[ 'access_key' ] = args[ 'access_key' ].decode( 'hex' )
        
    
    if 'account' in args:
        
        args[ 'account' ] = Account.GenerateAccountFromSerialisableTuple( args[ 'account' ] )
        
    
    if 'accounts' in args:
        
        account_tuples = args[ 'accounts' ]
        
        args[ 'accounts' ] = map( Account.GenerateAccountFromSerialisableTuple, account_tuples )
        
    
    if 'account_types' in args:
        
        account_type_tuples = args[ 'account_types' ]
        
        args[ 'account_types' ] = map( AccountType.GenerateAccountTypeFromSerialisableTuple, account_type_tuples )
        
    
    if 'registration_keys' in args:
        
        args[ 'registration_keys' ] = [ encoded_registration_key.decode( 'hex' ) for encoded_registration_key in args[ 'registration_keys' ] ]
        
    
    if 'service_keys_to_access_keys' in args:
        
        args[ 'service_keys_to_access_keys' ] = { encoded_service_key.decode( 'hex' ) : encoded_access_key.decode( 'hex' ) for ( encoded_service_key, encoded_access_key ) in args[ 'service_keys_to_access_keys' ] }
        
    
    if 'services' in args:
        
        service_tuples = args[ 'services' ]
        
        args[ 'services' ] = map( GenerateServiceFromSerialisableTuple, service_tuples )
        
    
    return args
    
def ParseGETArgs( requests_args ):
    
    args = {}
    
    for name in requests_args:
        
        values = requests_args[ name ]
        
        value = values[0]
        
        if name in INT_PARAMS:
            
            try:
                
                args[ name ] = int( value )
                
            except:
                
                raise HydrusExceptions.ForbiddenException( 'I was expecting to parse \'' + name + '\' as an integer, but it failed.' )
                
            
        elif name in BYTE_PARAMS:
            
            try:
                
                args[ name ] = value.decode( 'hex' )
                
            except:
                
                raise HydrusExceptions.ForbiddenException( 'I was expecting to parse \'' + name + '\' as a hex-encoded string, but it failed.' )
                
            
        
    
    if 'subject_account_key' in args:
        
        args[ 'subject_identifier' ] = HydrusData.AccountIdentifier( account_key = args[ 'subject_account_key' ] )
        
    elif 'subject_hash' in args:
        
        hash = args[ 'subject_hash' ]
        
        if 'subject_tag' in args:
            
            tag = args[ 'subject_tag' ]
            
            content = Content( HC.CONTENT_TYPE_MAPPING, ( tag, hash ) )
            
        else:
            
            content = Content( HC.CONTENT_TYPE_FILES, [ hash ] )
            
        
        args[ 'subject_identifier' ] = HydrusData.AccountIdentifier( content = content )
        
    
    return args
    
class Account( object ):
    
    def __init__( self, account_key, account_type, created, expires, banned_info = None, bandwidth_tracker = None ):
        
        if banned_info is None:
            
            banned_info = None # stupid, but keep it in case we change this
            
        
        if bandwidth_tracker is None:
            
            bandwidth_tracker = HydrusNetworking.BandwidthTracker()
            
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._lock = threading.Lock()
        
        self._account_key = account_key
        self._account_type = account_type
        self._created = created
        self._expires = expires
        self._banned_info = banned_info
        self._bandwidth_tracker = bandwidth_tracker
        
        self._dirty = False
        
    
    def __repr__( self ):
        
        return 'Account: ' + self._account_type.GetTitle()
        
    
    def __str__( self ):
        
        return self.__repr__()
        
    
    def _GetBannedString( self ):
        
        if self._banned_info is None:
            
            return 'not banned'
            
        else:
            
            ( reason, created, expires ) = self._banned_info
            
            return 'banned ' + HydrusData.ConvertTimestampToPrettyAge( created ) + ', ' + HydrusData.ConvertTimestampToPrettyExpires( expires ) + ' because: ' + reason
            
        
    
    def _GetExpiresString( self ):
        
        return HydrusData.ConvertTimestampToPrettyExpires( self._expires )
        
    
    def _GetFunctionalStatus( self ):
        
        if self._created == 0:
            
            return ( False, 'account is unsynced' )
            
        
        if self._account_type.HasPermission( HC.CONTENT_TYPE_SERVICES, HC.PERMISSION_ACTION_OVERRULE ):
            
            return ( True, 'admin: can do anything' )
            
        
        if self._IsBanned():
            
            return ( False, self._GetBannedString() )
        
        if self._IsExpired():
            
            return ( False, self._GetExpiresString() )
            
        
        if not self._account_type.BandwidthOk( self._bandwidth_tracker ):
            
            return ( False, 'account has exceeded bandwidth' )
            
        
        return ( True, 'account is functional' )
        
    
    def _IsBanned( self ):
        
        if self._banned_info is None:
            
            return False
            
        else:
            
            ( reason, created, expires ) = self._banned_info
            
            if expires is None:
                
                return True
                
            else:
                
                if HydrusData.TimeHasPassed( expires ):
                    
                    self._banned_info = None
                    
                else:
                    
                    return True
                    
                
            
        
    
    def _IsExpired( self ):
        
        if self._expires is None:
            
            return False
            
        else:
            
            return HydrusData.TimeHasPassed( self._expires )
            
        
    
    def _SetDirty( self ):
        
        self._dirty = True
        
    
    def Ban( self, reason, created, expires ):
        
        with self._lock:
            
            self._banned_info = ( reason, created, expires )
            
            self._SetDirty()
            
        
    
    def CheckFunctional( self ):
        
        with self._lock:
        
            if self._IsBanned():
                
                banned_string = self._GetBannedString()
                
                raise HydrusExceptions.PermissionException( 'This account is banned: ' + banned_string )
                
            
            if self._IsExpired():
                
                raise HydrusExceptions.PermissionException( 'This account has expired.' )
                
            
            if not self._account_type.BandwidthOk( self._bandwidth_tracker ):
                
                raise HydrusExceptions.PermissionException( 'This account has no remaining bandwidth.' )
                
            
        
    
    def CheckPermission( self, content_type, action ):
        
        with self._lock:
            
            if not self._account_type.HasPermission( content_type, action ):
                
                raise HydrusExceptions.PermissionException( 'You do not have permission to do that.' )
                
            
        
    
    def GetAccountKey( self ):
        
        with self._lock:
            
            return self._account_key
            
        
    
    def GetAccountType( self ):
        
        with self._lock:
            
            return self._account_type
            
        
    
    def GetBandwidthCurrentMonthSummary( self ):
        
        with self._lock:
            
            return self._bandwidth_tracker.GetCurrentMonthSummary()
            
        
    
    def GetBandwidthStringsAndGaugeTuples( self ):
        
        with self._lock:
            
            return self._account_type.GetBandwidthStringsAndGaugeTuples( self._bandwidth_tracker )
            
        
    
    def GetExpiresString( self ):
        
        with self._lock:
            
            if self._IsBanned():
                
                return self._GetBannedString()
                
            else:
                
                return self._GetExpiresString()
                
            
        
    
    def GetStatusString( self ):
        
        with self._lock:
            
            ( functional, status ) = self._GetFunctionalStatus()
            
            if functional:
                
                return status
                
            else:
                
                return 'account not functional: ' + status
                
            
        
    
    def HasPermission( self, content_type, action ):
        
        with self._lock:
            
            return self._account_type.HasPermission( content_type, action )
            
        
    
    def IsDirty( self ):
        
        with self._lock:
            
            return self._dirty
            
        
    
    def IsFunctional( self ):
        
        with self._lock:
            
            ( functional, status ) = self._GetFunctionalStatus()
            
            return functional
            
        
    
    def RequestMade( self, num_bytes ):
        
        with self._lock:
            
            self._bandwidth_tracker.RequestMade( num_bytes )
            
            self._SetDirty()
            
        
    
    def SetClean( self ):
        
        with self._lock:
            
            self._dirty = False
            
        
    
    def SetExpires( self, expires ):
        
        with self._lock:
            
            self._expires = expires
            
            self._SetDirty()
            
        
    
    def ToString( self ):
        
        with self._lock:
            
            return HydrusData.ConvertTimestampToPrettyAge( self._created ) + ' ' + self._account_type.GetTitle()
            
        
    
    def ToTuple( self ):
        
        with self._lock:
            
            return ( self._account_key, self._account_type, self._created, self._expires, self._banned_info, self._bandwidth_tracker )
            
        
    
    def Unban( self ):
        
        with self._lock:
            
            self._banned_info = None
            
            self._SetDirty()
            
        
    
    @staticmethod
    def GenerateAccountFromSerialisableTuple( ( account_key_encoded, account_type_serialisable_tuple, created, expires, dictionary_string ) ):
        
        account_key = account_key_encoded.decode( 'hex' )
        account_type = AccountType.GenerateAccountTypeFromSerialisableTuple( account_type_serialisable_tuple )
        dictionary = HydrusSerialisable.CreateFromString( dictionary_string )
        
        return Account.GenerateAccountFromTuple( ( account_key, account_type, created, expires, dictionary ) )
        
    
    @staticmethod
    def GenerateAccountFromTuple( ( account_key, account_type, created, expires, dictionary ) ):
        
        banned_info = dictionary[ 'banned_info' ]
        bandwidth_tracker = dictionary[ 'bandwidth_tracker' ]
        
        return Account( account_key, account_type, created, expires, banned_info, bandwidth_tracker )
        
    
    @staticmethod
    def GenerateSerialisableTupleFromAccount( account ):
        
        ( account_key, account_type, created, expires, dictionary ) = Account.GenerateTupleFromAccount( account )
        
        account_key_encoded = account_key.encode( 'hex' )
        
        serialisable_account_type = account_type.ToSerialisableTuple()
        
        dictionary_string = dictionary.DumpToString()
        
        return ( account_key_encoded, serialisable_account_type, created, expires, dictionary_string )
        
    
    @staticmethod
    def GenerateTupleFromAccount( account ):
        
        ( account_key, account_type, created, expires, banned_info, bandwidth_tracker ) = account.ToTuple()
        
        dictionary = HydrusSerialisable.SerialisableDictionary()
        
        dictionary[ 'banned_info' ] = banned_info
        
        dictionary[ 'bandwidth_tracker' ] = bandwidth_tracker
        
        return ( account_key, account_type, created, expires, dictionary )
        
    
    @staticmethod
    def GenerateUnknownAccount( account_key = '' ):
        
        account_type = AccountType.GenerateUnknownAccountType()
        created = 0
        expires = None
        
        unknown_account = Account( account_key, account_type, created, expires )
        
        return unknown_account
        
    
class AccountType( object ):
    
    def __init__( self, account_type_key, title, dictionary ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._account_type_key = account_type_key
        self._title = title
        
        self._LoadFromDictionary( dictionary )
        
    
    def __repr__( self ):
        
        return 'AccountType: ' + self._title
        
    
    def __str__( self ):
        
        return self.__repr__()
        
    
    def _GetSerialisableDictionary( self ):
        
        dictionary = HydrusSerialisable.SerialisableDictionary()
        
        dictionary[ 'permissions' ] = self._permissions.items()
        
        dictionary[ 'bandwidth_rules' ] = self._bandwidth_rules
        
        return dictionary
        
    
    def _LoadFromDictionary( self, dictionary ):
        
        self._permissions = dict( dictionary[ 'permissions' ] )
        
        self._bandwidth_rules = dictionary[ 'bandwidth_rules' ]
        
    
    def BandwidthOk( self, bandwidth_tracker ):
        
        return self._bandwidth_rules.Ok( bandwidth_tracker )
        
    
    def HasPermission( self, content_type, permission ):
        
        if content_type not in self._permissions:
            
            return False
            
        
        my_permission = self._permissions[ content_type ]
        
        if permission == HC.PERMISSION_ACTION_OVERRULE:
            
            return my_permission == HC.PERMISSION_ACTION_OVERRULE
            
        elif permission == HC.PERMISSION_ACTION_CREATE:
            
            return my_permission in ( HC.PERMISSION_ACTION_CREATE, HC.PERMISSION_ACTION_OVERRULE )
            
        elif permission == HC.PERMISSION_ACTION_PETITION:
            
            return my_permission in ( HC.PERMISSION_ACTION_PETITION, HC.PERMISSION_ACTION_CREATE, HC.PERMISSION_ACTION_OVERRULE )
            
        
        return False
        
    
    def GetBandwidthStringsAndGaugeTuples( self, bandwidth_tracker ):
        
        return self._bandwidth_rules.GetUsageStringsAndGaugeTuples( bandwidth_tracker )
        
    
    def GetAccountTypeKey( self ):
        
        return self._account_type_key
        
    
    def GetPermissionStrings( self ):
        
        s = []
        
        for ( content_type, action ) in self._permissions.items():
            
            s.append( HC.permission_pair_string_lookup[ ( content_type, action ) ] )
            
        
        return s
        
    
    def GetTitle( self ):
        
        return self._title
        
    
    def ToDictionaryTuple( self ):
        
        dictionary = self._GetSerialisableDictionary()
        
        return ( self._account_type_key, self._title, dictionary )
        
    
    def ToSerialisableTuple( self ):
        
        dictionary = self._GetSerialisableDictionary()
        
        dictionary_string = dictionary.DumpToString()
        
        return ( self._account_type_key.encode( 'hex' ), self._title, dictionary_string )
        
    
    def ToTuple( self ):
        
        return ( self._account_type_key, self._title, self._permissions, self._bandwidth_rules )
        
    
    @staticmethod
    def GenerateAccountTypeFromParameters( account_type_key, title, permissions, bandwidth_rules ):
        
        dictionary = HydrusSerialisable.SerialisableDictionary()
        
        dictionary[ 'permissions' ] = permissions.items()
        dictionary[ 'bandwidth_rules' ] = bandwidth_rules
        
        return AccountType( account_type_key, title, dictionary )
        
    
    @staticmethod
    def GenerateAccountTypeFromSerialisableTuple( ( account_type_key_encoded, title, dictionary_string ) ):
        
        try:
            
            account_type_key = account_type_key_encoded.decode( 'hex' )
            
        except TypeError:
            
            raise HydrusExceptions.ForbiddenException( 'Could not decode that account type key!' )
            
        
        dictionary = HydrusSerialisable.CreateFromString( dictionary_string )
        
        return AccountType( account_type_key, title, dictionary )
        
    
    @staticmethod
    def GenerateAdminAccountType( service_type ):
        
        bandwidth_rules = HydrusNetworking.BandwidthRules()
        
        permissions = {}
        
        permissions[ HC.CONTENT_TYPE_ACCOUNTS ] = HC.PERMISSION_ACTION_OVERRULE
        permissions[ HC.CONTENT_TYPE_ACCOUNT_TYPES ] = HC.PERMISSION_ACTION_OVERRULE
        
        if service_type in HC.REPOSITORIES:
            
            for content_type in HC.REPOSITORY_CONTENT_TYPES:
                
                permissions[ content_type ] = HC.PERMISSION_ACTION_OVERRULE
                
            
        elif service_type == HC.SERVER_ADMIN:
            
            permissions[ HC.CONTENT_TYPE_SERVICES ] = HC.PERMISSION_ACTION_OVERRULE
            
        else:
            
            raise NotImplementedError( 'Do not have a default admin account type set up for this service yet!' )
            
        
        account_type = AccountType.GenerateNewAccountTypeFromParameters( 'administrator', permissions, bandwidth_rules )
        
        return account_type
        
    
    @staticmethod
    def GenerateNewAccountTypeFromParameters( title, permissions, bandwidth_rules ):
        
        account_type_key = HydrusData.GenerateKey()
        
        return AccountType.GenerateAccountTypeFromParameters( account_type_key, title, permissions, bandwidth_rules )
        
    
    @staticmethod
    def GenerateUnknownAccountType():
        
        title = 'unknown account'
        permissions = {}
        
        bandwidth_rules = HydrusNetworking.BandwidthRules()
        bandwidth_rules.AddRule( HC.BANDWIDTH_TYPE_REQUESTS, None, 0 )
        
        unknown_account_type = AccountType.GenerateNewAccountTypeFromParameters( title, permissions, bandwidth_rules )
        
        return unknown_account_type
        
    
class ClientToServerUpdate( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_CLIENT_TO_SERVER_UPDATE
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._actions_to_contents_and_reasons = collections.defaultdict( list )
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_info = []
        
        for ( action, contents_and_reasons ) in self._actions_to_contents_and_reasons.items():
            
            serialisable_contents_and_reasons = [ ( content.GetSerialisableTuple(), reason ) for ( content, reason ) in contents_and_reasons ]
            
            serialisable_info.append( ( action, serialisable_contents_and_reasons ) )
            
        
        return serialisable_info
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        for ( action, serialisable_contents_and_reasons ) in serialisable_info:
            
            contents_and_reasons = [ ( HydrusSerialisable.CreateFromSerialisableTuple( serialisable_content ), reason ) for ( serialisable_content, reason ) in serialisable_contents_and_reasons ]
            
            self._actions_to_contents_and_reasons[ action ] = contents_and_reasons
            
        
    
    def AddContent( self, action, content, reason = None ):
        
        if reason is None:
            
            reason = ''
            
        
        self._actions_to_contents_and_reasons[ action ].append( ( content, reason ) )
        
    
    def GetClientsideContentUpdates( self ):
        
        content_updates = []
        
        for ( action, clientside_action ) in ( ( HC.CONTENT_UPDATE_PEND, HC.CONTENT_UPDATE_ADD ), ( HC.CONTENT_UPDATE_PETITION, HC.CONTENT_UPDATE_DELETE ) ):
            
            for ( content, reason ) in self._actions_to_contents_and_reasons[ action ]:
                
                content_type = content.GetContentType()
                content_data = content.GetContentData()
                
                content_update = HydrusData.ContentUpdate( content_type, clientside_action, content_data )
                
                content_updates.append( content_update )
                
            
        
        return content_updates
        
    
    def GetContentDataIterator( self, content_type, action ):
        
        contents_and_reasons = self._actions_to_contents_and_reasons[ action ]
        
        for ( content, reason ) in contents_and_reasons:
            
            if content.GetContentType() == content_type:
                
                yield ( content.GetContentData(), reason )
                
            
        
    
    def GetHashes( self ):
        
        hashes = set()
        
        for contents_and_reasons in self._actions_to_contents_and_reasons.values():
            
            for ( content, reason ) in contents_and_reasons:
                
                hashes.update( content.GetHashes() )
                
            
        
        return hashes
        
    
    def HasContent( self ):
        
        return len( self._actions_to_contents_and_reasons ) > 0
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_CLIENT_TO_SERVER_UPDATE ] = ClientToServerUpdate

class Content( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_CONTENT
    SERIALISABLE_VERSION = 1
    
    def __init__( self, content_type = None, content_data = None ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._content_type = content_type
        self._content_data = content_data
        
    
    def __eq__( self, other ): return self.__hash__() == other.__hash__()
    
    def __hash__( self ): return ( self._content_type, self._content_data ).__hash__()
    
    def __ne__( self, other ): return self.__hash__() != other.__hash__()
    
    def __repr__( self ): return 'Content: ' + self.ToString()
    
    def _GetSerialisableInfo( self ):
        
        def EncodeHashes( hs ):
            
            return [ h.encode( 'hex' ) for h in hs ]
            
        
        if self._content_type == HC.CONTENT_TYPE_FILES:
            
            hashes = self._content_data
            
            serialisable_content = EncodeHashes( hashes )
            
        elif self._content_type == HC.CONTENT_TYPE_MAPPING:
            
            ( tag, hash ) = self._content_data
            
            serialisable_content = ( tag, hash.encode( 'hex' ) )
            
        elif self._content_type == HC.CONTENT_TYPE_MAPPINGS:
            
            ( tag, hashes ) = self._content_data
            
            serialisable_content = ( tag, EncodeHashes( hashes ) )
            
        elif self._content_type in ( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_TYPE_TAG_SIBLINGS ):
            
            ( old_tag, new_tag ) = self._content_data
            
            serialisable_content = ( old_tag, new_tag )
            
        
        return ( self._content_type, serialisable_content )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        def DecodeHashes( hs ):
            
            return [ h.decode( 'hex' ) for h in hs ]
            
        
        ( self._content_type, serialisable_content ) = serialisable_info
        
        if self._content_type == HC.CONTENT_TYPE_FILES:
            
            serialisable_hashes = serialisable_content
            
            self._content_data = DecodeHashes( serialisable_hashes )
            
        elif self._content_type == HC.CONTENT_TYPE_MAPPING:
            
            ( tag, serialisable_hash ) = serialisable_content
            
            self._content_data = ( tag, serialisable_hash.decode( 'hex' ) )
            
        elif self._content_type == HC.CONTENT_TYPE_MAPPINGS:
            
            ( tag, serialisable_hashes ) = serialisable_content
            
            self._content_data = ( tag, DecodeHashes( serialisable_hashes ) )
            
        elif self._content_type in ( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_TYPE_TAG_SIBLINGS ):
            
            ( old_tag, new_tag ) = serialisable_content
            
            self._content_data = ( old_tag, new_tag )
            
        
    
    def GetContentData( self ):
        
        return self._content_data
        
    
    def GetContentType( self ):
        
        return self._content_type
        
    
    def GetHashes( self ):
        
        if self._content_type == HC.CONTENT_TYPE_FILES:
            
            hashes = self._content_data
            
        elif self._content_type == HC.CONTENT_TYPE_MAPPING:
            
            ( tag, hash ) = self._content_data
            
            return [ hash ]
            
        elif self._content_type == HC.CONTENT_TYPE_MAPPINGS:
            
            ( tag, hashes ) = self._content_data
            
        else:
            
            hashes = []
            
        
        return hashes
        
    
    def GetVirtualWeight( self ):
        
        if self._content_type in ( HC.CONTENT_TYPE_FILES, HC.CONTENT_TYPE_MAPPINGS ):
            
            return len( self.GetHashes() )
            
        elif self._content_type == HC.CONTENT_TYPE_TAG_PARENTS:
            
            return 5000
            
        elif self._content_type == HC.CONTENT_TYPE_TAG_SIBLINGS:
            
            return 5
            
        elif self._content_type == HC.CONTENT_TYPE_MAPPING:
            
            return 1
            
        
    
    def HasHashes( self ):
        
        return self._content_type in ( HC.CONTENT_TYPE_FILES, HC.CONTENT_TYPE_MAPPING, HC.CONTENT_TYPE_MAPPINGS )
        
    
    def ToString( self ):
        
        if self._content_type == HC.CONTENT_TYPE_FILES:
            
            hashes = self._content_data
            
            text = 'FILES: ' + HydrusData.ConvertIntToPrettyString( len( hashes ) ) + ' files'
            
        elif self._content_type == HC.CONTENT_TYPE_MAPPING:
            
            ( tag, hash ) = self._content_data
            
            text = 'MAPPING: ' + tag + ' for ' + hash.encode( 'hex' )
            
        elif self._content_type == HC.CONTENT_TYPE_MAPPINGS:
            
            ( tag, hashes ) = self._content_data
            
            text = 'MAPPINGS: ' + tag + ' for ' + HydrusData.ConvertIntToPrettyString( len( hashes ) ) + ' files'
            
        elif self._content_type == HC.CONTENT_TYPE_TAG_PARENTS:
            
            ( child, parent ) = self._content_data
            
            text = 'PARENT: ' '"' + child + '" -> "' + parent + '"'
            
        elif self._content_type == HC.CONTENT_TYPE_TAG_SIBLINGS:
            
            ( old_tag, new_tag ) = self._content_data
            
            text = 'SIBLING: ' + '"' + old_tag + '" -> "' + new_tag + '"'
            
        
        return text
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_CONTENT ] = Content

class ContentUpdate( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_CONTENT_UPDATE
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._content_data = {}
        
    
    def _GetContent( self, content_type, action ):
        
        if content_type in self._content_data:
            
            if action in self._content_data[ content_type ]:
                
                return self._content_data[ content_type ][ action ]
                
            
        
        return []
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_info = []
        
        for ( content_type, actions_to_datas ) in self._content_data.items():
            
            serialisable_actions_to_datas = actions_to_datas.items()
            
            serialisable_info.append( ( content_type, serialisable_actions_to_datas ) )
            
        
        return serialisable_info
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        for ( content_type, serialisable_actions_to_datas ) in serialisable_info:
            
            actions_to_datas = dict( serialisable_actions_to_datas )
            
            self._content_data[ content_type ] = actions_to_datas
            
        
    
    def AddRow( self, row ):
        
        ( content_type, action, data ) = row
        
        if content_type not in self._content_data:
            
            self._content_data[ content_type ] = {}
            
        
        if action not in self._content_data[ content_type ]:
            
            self._content_data[ content_type ][ action ] = []
            
        
        self._content_data[ content_type ][ action ].append( data )
        
    
    def GetDeletedFiles( self ):
        
        return self._GetContent( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE )
        
    
    def GetDeletedMappings( self ):
        
        return self._GetContent( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_DELETE )
        
    
    def GetDeletedTagParents( self ):
        
        return self._GetContent( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_UPDATE_DELETE )
        
    
    def GetDeletedTagSiblings( self ):
        
        return self._GetContent( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_DELETE )
        
    
    def GetNewFiles( self ):
        
        return self._GetContent( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ADD )
        
    
    def GetNewMappings( self ):
        
        return self._GetContent( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD )
        
    
    def GetNewTagParents( self ):
        
        return self._GetContent( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_UPDATE_ADD )
        
    
    def GetNewTagSiblings( self ):
        
        return self._GetContent( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_ADD )
        
    
    def GetNumRows( self ):
        
        num = 0
        
        for content_type in self._content_data:
            
            for action in self._content_data[ content_type ]:
                
                data = self._content_data[ content_type ][ action ]
                
                if content_type == HC.CONTENT_TYPE_MAPPINGS:
                    
                    num_rows = sum( ( len( hash_ids ) for ( tag_id, hash_ids ) in data ) )
                    
                else:
                    
                    num_rows = len( data )
                    
                
                num += num_rows
                
            
        
        return num
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_CONTENT_UPDATE ] = ContentUpdate

class Credentials( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_CREDENTIALS
    SERIALISABLE_VERSION = 1
    
    def __init__( self, host = None, port = None, access_key = None ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._host = host
        self._port = port
        self._access_key = access_key
        
    
    def __eq__( self, other ):
        
        return self.__hash__() == other.__hash__()
        
    
    def __hash__( self ):
        
        return ( self._host, self._port, self._access_key ).__hash__()
        
    
    def __ne__( self, other ):
        
        return self.__hash__() != other.__hash__()
        
    
    def __repr__( self ):
        
        return 'Credentials: ' + HydrusData.ToUnicode( ( self._host, self._port, self._access_key.encode( 'hex' ) ) )
        
    
    def _GetSerialisableInfo( self ):
        
        if self._access_key is None:
            
            serialisable_access_key = self._access_key
            
        else:
            
            serialisable_access_key = self._access_key.encode( 'hex' )
            
        
        return ( self._host, self._port, serialisable_access_key )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._host, self._port, serialisable_access_key ) = serialisable_info
        
        if serialisable_access_key is None:
            
            self._access_key = serialisable_access_key
            
        else:
            
            self._access_key = serialisable_access_key.decode( 'hex' )
            
        
    
    def GetAccessKey( self ):
        
        return self._access_key
        
    
    def GetAddress( self ):
        
        return ( self._host, self._port )
        
    
    def GetConnectionString( self ):
        
        connection_string = ''
        
        if self.HasAccessKey():
            
            connection_string += self._access_key.encode( 'hex' ) + '@'
            
        
        connection_string += self._host + ':' + str( self._port )
        
        return connection_string
        
    
    def HasAccessKey( self ):
        
        return self._access_key is not None
        
    
    def SetAccessKey( self, access_key ):
        
        if access_key == '':
            
            access_key = None
            
        
        self._access_key = access_key
        
    
    def SetAddress( self, host, port ):
        
        self._host = host
        self._port = port
        
    
    @staticmethod
    def GenerateCredentialsFromConnectionString( connection_string ):
        
        ( host, port, access_key ) = Credentials.ParseConnectionString( connection_string )
        
        return Credentials( host, port, access_key )
        
    
    @staticmethod
    def ParseConnectionString( connection_string ):
        
        if connection_string is None:
            
            return ( 'hostname', 80, None )
            
        
        if '@' in connection_string:
            
            ( access_key_encoded, address ) = connection_string.split( '@', 1 )
            
            try:
                
                access_key = access_key_encoded.decode( 'hex' )
                
            except TypeError:
                
                raise HydrusExceptions.DataMissing( 'Could not parse that access key! It should be a 64 character hexadecimal string!' )
                
            
            if access_key == '':
                
                access_key = None
                
            
        else:
            
            access_key = None
            
        
        if ':' in connection_string:
            
            ( host, port ) = connection_string.split( ':', 1 )
            
            try:
                
                port = int( port )
                
                if port < 0 or port > 65535:
                    
                    raise ValueError()
                    
                
            except ValueError:
                
                raise HydrusExceptions.DataMissing( 'Could not parse that port! It should be an integer between 0 and 65535!' )
                
            
        
        if host == 'localhost':
            
            host = '127.0.0.1'
            
        
        return ( host, port, access_key )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_CREDENTIALS ] = Credentials

class DefinitionsUpdate( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_DEFINITIONS_UPDATE
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._hash_ids_to_hashes = {}
        self._tag_ids_to_tags = {}
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_info = []
        
        if len( self._hash_ids_to_hashes ) > 0:
            
            serialisable_info.append( ( HC.DEFINITIONS_TYPE_HASHES, [ ( hash_id, hash.encode( 'hex' ) ) for ( hash_id, hash ) in self._hash_ids_to_hashes.items() ] ) )
            
        
        if len( self._tag_ids_to_tags ) > 0:
            
            serialisable_info.append( ( HC.DEFINITIONS_TYPE_TAGS, self._tag_ids_to_tags.items() ) )
            
        
        return serialisable_info
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        for ( definition_type, definitions ) in serialisable_info:
            
            if definition_type == HC.DEFINITIONS_TYPE_HASHES:
                
                self._hash_ids_to_hashes = { hash_id : encoded_hash.decode( 'hex' ) for ( hash_id, encoded_hash ) in definitions }
                
            elif definition_type == HC.DEFINITIONS_TYPE_TAGS:
                
                self._tag_ids_to_tags = { tag_id : tag for ( tag_id, tag ) in definitions }
                
            
        
    
    def AddRow( self, row ):
        
        ( definitions_type, key, value ) = row
        
        if definitions_type == HC.DEFINITIONS_TYPE_HASHES:
            
            self._hash_ids_to_hashes[ key ] = value
            
        elif definitions_type == HC.DEFINITIONS_TYPE_TAGS:
            
            self._tag_ids_to_tags[ key ] = value
            
        
    
    def GetHashIdsToHashes( self ):
        
        return self._hash_ids_to_hashes
        
    
    def GetNumRows( self ):
        
        return len( self._hash_ids_to_hashes ) + len( self._tag_ids_to_tags )
        
    
    def GetTagIdsToTags( self ):
        
        return self._tag_ids_to_tags
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_DEFINITIONS_UPDATE ] = DefinitionsUpdate

class Metadata( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_METADATA
    SERIALISABLE_VERSION = 1
    
    CLIENT_DELAY = 20 * 60
    
    def __init__( self, metadata = None, next_update_due = None ):
        
        if metadata is None:
            
            metadata = {}
            
        
        if next_update_due is None:
            
            next_update_due = 0
            
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._lock = threading.Lock()
        
        now = HydrusData.GetNow()
        
        self._metadata = metadata
        self._next_update_due = next_update_due
        
        self._update_hashes = set()
        
    
    def _GetNextUpdateDueTime( self, from_client = False ):
        
        delay = 0
        
        if from_client:
            
            delay = self.CLIENT_DELAY
            
        
        return self._next_update_due + delay
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_metadata = [ ( update_index, [ update_hash.encode( 'hex' ) for update_hash in update_hashes ], begin, end ) for ( update_index, ( update_hashes, begin, end ) ) in self._metadata.items() ]
        
        return ( serialisable_metadata, self._next_update_due )
        
    
    def _GetUpdateHashes( self, update_index ):
        
        ( update_hashes, begin, end ) = self._GetUpdate( update_index )
        
        return update_hashes
        
    
    def _GetUpdate( self, update_index ):
        
        if update_index not in self._metadata:
            
            raise HydrusExceptions.DataMissing( 'That update does not exist!' )
            
        
        return self._metadata[ update_index ]
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_metadata, self._next_update_due ) = serialisable_info
        
        self._metadata = {}
        
        for ( update_index, encoded_update_hashes, begin, end ) in serialisable_metadata:
            
            update_hashes = [ encoded_update_hash.decode( 'hex' ) for encoded_update_hash in encoded_update_hashes ]
            
            self._metadata[ update_index ] = ( update_hashes, begin, end )
            
            self._update_hashes.update( update_hashes )
            
        
    
    def AppendUpdate( self, update_hashes, begin, end, next_update_due ):
        
        with self._lock:
            
            update_index = len( self._metadata )
            
            self._metadata[ update_index ] = ( update_hashes, begin, end )
            
            self._update_hashes.update( update_hashes )
            
            self._next_update_due = next_update_due
            
        
    
    def GetNextUpdateIndex( self ):
        
        with self._lock:
            
            return len( self._metadata )
            
        
    
    def GetNextUpdateBegin( self ):
        
        with self._lock:
            
            largest_update_index = max( self._metadata.keys() )
            
            ( update_hashes, begin, end ) = self._GetUpdate( largest_update_index )
            
            return end + 1
            
        
    
    def GetNextUpdateDueString( self, from_client = False ):
        
        with self._lock:
            
            if self._next_update_due == 0:
                
                return 'have not yet synced metadata'
                
            else:
                
                update_due = self._GetNextUpdateDueTime( from_client )
                
                return 'next update due ' + HydrusData.ConvertTimestampToPrettyPending( update_due )
                
            
        
    
    def GetNumUpdateHashes( self ):
        
        with self._lock:
            
            num_update_hashes = sum( ( len( update_hashes ) for ( update_hashes, begin, end ) in self._metadata.values() ) )
            
            return num_update_hashes
            
        
    
    def GetSlice( self, from_update_index ):
        
        with self._lock:
            
            metadata = { update_index : row for ( update_index, row ) in self._metadata.items() if update_index >= from_update_index }
            
            return Metadata( metadata, self._next_update_due )
            
        
    
    def GetUpdateHashes( self, update_index = None ):
        
        with self._lock:
            
            if update_index is None:
                
                all_update_hashes = set()
                
                for ( update_hashes, begin, end ) in self._metadata.values():
                    
                    all_update_hashes.update( update_hashes )
                    
                
                return all_update_hashes
                
            else:
                
                update_hashes = self._GetUpdateHashes( update_index )
                
                return update_hashes
                
            
        
    
    def GetUpdateInfo( self, from_client = False ):
        
        with self._lock:
            
            num_update_hashes = sum( ( len( update_hashes ) for ( update_hashes, begin, end ) in self._metadata.values() ) )
            
            if len( self._metadata ) == 0:
                
                status = 'have not yet synchronised'
                
            else:
                
                biggest_end = max( ( end for ( update_hashes, begin, end ) in self._metadata.values() ) )
                
                delay = 0
                
                if from_client:
                    
                    delay = self.CLIENT_DELAY
                    
                
                next_update_time = self._next_update_due + delay
                
                status = 'metadata synchronised up to ' + HydrusData.ConvertTimestampToPrettyAgo( biggest_end ) + ', next update due ' + HydrusData.ConvertTimestampToPrettyPending( next_update_time )
                
            
            return ( num_update_hashes, status )
            
        
    
    def GetUpdateTimestamps( self, update_index ):
        
        with self._lock:
            
            update_timestamps = [ ( update_index, begin, end ) for ( update_index, ( update_hashes, begin, end ) ) in self._metadata.items() ]
            
            return update_timestamps
            
        
    
    def HasUpdateHash( self, update_hash ):
        
        with self._lock:
            
            return update_hash in self._update_hashes
            
        
    
    def IterateUpdateIndicesAndHashes( self ):
        
        with self._lock:
            
            for ( update_index, ( update_hashes, begin, end ) ) in self._metadata.items():
                
                yield ( update_index, update_hashes )
                
            
        
    
    def UpdateDue( self, from_client = False ):
        
        with self._lock:
            
            next_update_due_time = self._GetNextUpdateDueTime( from_client )
            
            return HydrusData.TimeHasPassed( next_update_due_time )
            
        
    
    def UpdateFromSlice( self, metadata_slice ):
        
        with self._lock:
            
            self._metadata.update( metadata_slice._metadata )
            
            self._next_update_due = metadata_slice._next_update_due
            
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_METADATA ] = Metadata

class Petition( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_PETITION
    SERIALISABLE_VERSION = 1
    
    def __init__( self, action = None, petitioner_account = None, reason = None, contents = None ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._action = action
        self._petitioner_account = petitioner_account
        self._reason = reason
        self._contents = contents
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_petitioner_account = Account.GenerateSerialisableTupleFromAccount( self._petitioner_account )
        serialisable_contents = [ content.GetSerialisableTuple() for content in self._contents ]
        
        return ( self._action, serialisable_petitioner_account, self._reason, serialisable_contents )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._action, serialisable_petitioner_account, self._reason, serialisable_contents ) = serialisable_info
        
        self._petitioner_account = Account.GenerateAccountFromSerialisableTuple( serialisable_petitioner_account )
        self._contents = [ HydrusSerialisable.CreateFromSerialisableTuple( serialisable_content ) for serialisable_content in serialisable_contents ]
        
    
    def GetActionTextAndColour( self ):
        
        action_text = ''
        
        if self._action == HC.CONTENT_UPDATE_PEND:
            
            action_text += 'ADD'
            action_colour = ( 127, 255, 127 )
            
        elif self._action == HC.CONTENT_UPDATE_PETITION:
            
            action_text += 'DELETE'
            action_colour = ( 255, 127, 127 )
            
        
        return ( action_text, action_colour )
        
    
    def GetApproval( self, contents ):
        
        if self._action == HC.CONTENT_UPDATE_PEND:
            
            content_update_action = HC.CONTENT_UPDATE_ADD
            
        elif self._action == HC.CONTENT_UPDATE_PETITION:
            
            content_update_action = HC.CONTENT_UPDATE_DELETE
            
        
        update = ClientToServerUpdate()
        content_updates = []
        
        for content in contents:
            
            update.AddContent( self._action, content, self._reason )
            
            content_type = content.GetContentType()
            
            row = content.GetContentData()
            
            content_update = HydrusData.ContentUpdate( content_type, content_update_action, row )
            
            content_updates.append( content_update )
            
        
        return ( update, content_updates )
        
    
    def GetContents( self ):
        
        return self._contents
        
    
    def GetDenial( self, contents ):
        
        if self._action == HC.CONTENT_UPDATE_PEND:
            
            denial_action = HC.CONTENT_UPDATE_DENY_PEND
            
        elif self._action == HC.CONTENT_UPDATE_PETITION:
            
            denial_action = HC.CONTENT_UPDATE_DENY_PETITION
            
        
        update = ClientToServerUpdate()
        
        for content in contents:
            
            update.AddContent( denial_action, content, self._reason )
            
        
        return update
        
    
    def GetPetitionerAccount( self ):
        
        return self._petitioner_account
        
    
    def GetReason( self ):
        
        return self._reason
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_PETITION ] = Petition

class ServerService( object ):
    
    def __init__( self, service_key, service_type, name, port, dictionary ):
        
        self._service_key = service_key
        self._service_type = service_type
        self._name = name
        self._port = port
        
        self._lock = threading.Lock()
        
        self._LoadFromDictionary( dictionary )
        
        self._dirty = False
        
    
    def _GetSerialisableDictionary( self ):
        
        dictionary = HydrusSerialisable.SerialisableDictionary()
        
        dictionary[ 'upnp_port' ] = self._upnp_port
        dictionary[ 'bandwidth_tracker' ] = self._bandwidth_tracker
        
        return dictionary
        
    
    def _LoadFromDictionary( self, dictionary ):
        
        self._upnp_port = dictionary[ 'upnp_port' ]
        self._bandwidth_tracker = dictionary[ 'bandwidth_tracker' ]
        
    
    def _SetDirty( self ):
        
        self._dirty = True
        
    
    def Duplicate( self ):
        
        with self._lock:
            
            dictionary = self._GetSerialisableDictionary()
            
            duplicate = GenerateService( self._service_key, self._service_type, self._name, self._port, dictionary )
            
            return duplicate
            
        
    
    def GetName( self ):
        
        with self._lock:
            
            return self._name
            
        
    
    def GetPort( self ):
        
        with self._lock:
            
            return self._port
            
        
    
    def GetUPnPPort( self ):
        
        with self._lock:
            
            return self._upnp_port
            
        
    
    def GetServiceKey( self ):
        
        with self._lock:
            
            return self._service_key
            
        
    
    def GetServiceType( self ):
        
        with self._lock:
            
            return self._service_type
            
        
    
    def IsDirty( self ):
        
        with self._lock:
            
            return self._dirty
            
        
    
    def BandwidthOk( self ):
        
        with self._lock:
            
            return True
            
        
    
    def RequestMade( self, num_bytes ):
        
        with self._lock:
            
            self._bandwidth_tracker.RequestMade( num_bytes )
            
            self._SetDirty()
            
        
    
    def SetClean( self ):
        
        with self._lock:
            
            self._dirty = False
            
        
    
    def SetName( self, name ):
        
        with self._lock:
            
            self._name = name
            
            self._SetDirty()
            
        
    
    def SetPort( self, port ):
        
        with self._lock:
            
            self._port = port
            
            self._SetDirty()
            
        
    
    def ToSerialisableTuple( self ):
        
        with self._lock:
            
            dictionary = self._GetSerialisableDictionary()
            
            dictionary_string = dictionary.DumpToString()
            
            return ( self._service_key.encode( 'hex' ), self._service_type, self._name, self._port, dictionary_string )
            
        
    
    def ToTuple( self ):
        
        with self._lock:
            
            dictionary = self._GetSerialisableDictionary()
            
            return ( self._service_key, self._service_type, self._name, self._port, dictionary )
            
        
    
class ServerServiceRestricted( ServerService ):
    
    def _GetSerialisableDictionary( self ):
        
        dictionary = ServerService._GetSerialisableDictionary( self )
        
        dictionary[ 'bandwidth_rules' ] = self._bandwidth_rules
        
        return dictionary
        
    
    def _LoadFromDictionary( self, dictionary ):
        
        ServerService._LoadFromDictionary( self, dictionary )
        
        self._bandwidth_rules = dictionary[ 'bandwidth_rules' ]
        
    
    def BandwidthOk( self ):
        
        with self._lock:
            
            return self._bandwidth_rules.Ok( self._bandwidth_tracker )
            
        
    
class ServerServiceRepository( ServerServiceRestricted ):
    
    def _GetSerialisableDictionary( self ):
        
        dictionary = ServerServiceRestricted._GetSerialisableDictionary( self )
        
        dictionary[ 'metadata' ] = self._metadata
        
        return dictionary
        
    
    def _LoadFromDictionary( self, dictionary ):
        
        ServerServiceRestricted._LoadFromDictionary( self, dictionary )
        
        self._metadata = dictionary[ 'metadata' ]
        
    
    def GetMetadataSlice( self, from_update_index ):
        
        with self._lock:
            
            return self._metadata.GetSlice( from_update_index )
            
        
    
    def HasUpdateHash( self, update_hash ):
        
        with self._lock:
            
            return self._metadata.HasUpdateHash( update_hash )
            
        
    
    def Sync( self ):
        
        with self._lock:
            
            update_due = self._metadata.UpdateDue()
            
        
        if update_due:
            
            HydrusGlobals.server_busy = True
            
            while update_due:
                
                with self._lock:
                    
                    service_key = self._service_key
                    
                    begin = self._metadata.GetNextUpdateBegin()
                    
                
                end = begin + HC.UPDATE_DURATION
                
                update_hashes = HydrusGlobals.server_controller.WriteSynchronous( 'create_update', service_key, begin, end )
                
                next_update_due = end + HC.UPDATE_DURATION + 1
                
                with self._lock:
                    
                    self._metadata.AppendUpdate( update_hashes, begin, end, next_update_due )
                    
                    update_due = self._metadata.UpdateDue()
                    
                
            
            HydrusGlobals.server_busy = False
            
            with self._lock:
                
                self._SetDirty()
                
            
        
        
    
class ServerServiceRepositoryTag( ServerServiceRepository ):
    
    pass
    
class ServerServiceRepositoryFile( ServerServiceRepository ):
    
    def _GetSerialisableDictionary( self ):
        
        dictionary = ServerServiceRepository._GetSerialisableDictionary( self )
        
        dictionary[ 'log_uploader_ips' ] = self._log_uploader_ips
        dictionary[ 'max_storage' ] = self._max_storage
        
        return dictionary
        
    
    def _LoadFromDictionary( self, dictionary ):
        
        ServerServiceRepository._LoadFromDictionary( self, dictionary )
        
        self._log_uploader_ips = dictionary[ 'log_uploader_ips' ]
        self._max_storage = dictionary[ 'max_storage' ]
        
    
    def LogUploaderIPs( self ):
        
        with self._lock:
            
            return self._log_uploader_ips
            
        
    
    def GetMaxStorage( self ):
        
        with self._lock:
            
            return self._max_storage
            
        
    
class ServerServiceAdmin( ServerServiceRestricted ):
    
    def _GetSerialisableDictionary( self ):
        
        dictionary = ServerServiceRestricted._GetSerialisableDictionary( self )
        
        dictionary[ 'server_bandwidth_tracker' ] = self._server_bandwidth_tracker
        dictionary[ 'server_bandwidth_rules' ] = self._server_bandwidth_rules
        
        return dictionary
        
    
    def _LoadFromDictionary( self, dictionary ):
        
        ServerServiceRestricted._LoadFromDictionary( self, dictionary )
        
        self._server_bandwidth_tracker = dictionary[ 'server_bandwidth_tracker' ]
        self._server_bandwidth_rules = dictionary[ 'server_bandwidth_rules' ]
        
    
    def ServerBandwidthOk( self ):
        
        with self._lock:
            
            return self._server_bandwidth_rules.Ok( self._server_bandwidth_tracker )
            
        
    
    def ServerRequestMade( self, num_bytes ):
        
        with self._lock:
            
            self._server_bandwidth_tracker.RequestMade( num_bytes )
            
            self._SetDirty()
            
        
    
class UpdateBuilder( object ):
    
    def __init__( self, update_class, max_rows ):
        
        self._update_class = update_class
        self._max_rows = max_rows
        
        self._updates = []
        
        self._current_update = self._update_class()
        self._current_num_rows = 0
        
    
    def AddRow( self, row, row_weight = 1 ):
        
        self._current_update.AddRow( row )
        self._current_num_rows += row_weight
        
        if self._current_num_rows > self._max_rows:
            
            self._updates.append( self._current_update )
            
            self._current_update = self._update_class()
            self._current_num_rows = 0
            
        
    
    def Finish( self ):
        
        if self._current_update.GetNumRows() > 0:
            
            self._updates.append( self._current_update )
            
        
        self._current_update = None
        
    
    def GetUpdates( self ):
        
        return self._updates
        
    
