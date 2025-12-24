import collections
import collections.abc
import threading
import time

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusLists
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTags
from hydrus.core import HydrusTime
from hydrus.core.networking import HydrusNetworking

UPDATE_CHECKING_PERIOD = 240
MIN_UPDATE_PERIOD = 600
MAX_UPDATE_PERIOD = 100000 * 100 # three months or so jej

MIN_NULLIFICATION_PERIOD = 86400
MAX_NULLIFICATION_PERIOD = 86400 * 365 * 5

def GenerateDefaultServiceDictionary( service_type ):
    
    # don't store bytes key/value data here until ~version 537
    # the server kicks out a patched version 1 of serialisabledict, so it can't handle byte gubbins, lad
    
    dictionary = HydrusSerialisable.SerialisableDictionary()
    
    dictionary[ 'upnp_port' ] = None
    dictionary[ 'bandwidth_tracker' ] = HydrusNetworking.BandwidthTracker()
    
    if service_type in HC.RESTRICTED_SERVICES:
        
        dictionary[ 'bandwidth_rules' ] = HydrusNetworking.BandwidthRules()
        dictionary[ 'service_options' ] = HydrusSerialisable.SerialisableDictionary()
        
        dictionary[ 'service_options' ][ 'server_message' ] = 'Welcome to the server!'
        
        if service_type in HC.REPOSITORIES:
            
            update_period = 100000
            
            dictionary[ 'service_options' ][ 'update_period' ] = update_period
            dictionary[ 'service_options' ][ 'nullification_period' ] = 90 * 86400
            
            dictionary[ 'next_nullification_update_index' ] = 0
            
            metadata = Metadata()
            
            now = HydrusTime.GetNow()
            
            update_hashes = []
            begin = 0
            end = now
            next_update_due = now + update_period
            
            metadata.AppendUpdate( update_hashes, begin, end, next_update_due )
            
            dictionary[ 'metadata' ] = metadata
            
            if service_type == HC.FILE_REPOSITORY:
                
                dictionary[ 'log_uploader_ips' ] = False
                dictionary[ 'max_storage' ] = None
                
            
            if service_type == HC.TAG_REPOSITORY:
                
                dictionary[ 'service_options' ][ 'tag_filter' ] = HydrusTags.TagFilter()
                
            
        
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
    
def GenerateServiceFromSerialisableTuple( serialisable_info ):
    
    ( service_key_encoded, service_type, name, port, dictionary_string ) = serialisable_info
    
    try:
        
        service_key = bytes.fromhex( service_key_encoded )
        
    except TypeError:
        
        raise HydrusExceptions.BadRequestException( 'Could not decode that service key!' )
        
    
    dictionary = HydrusSerialisable.CreateFromString( dictionary_string )
    
    return GenerateService( service_key, service_type, name, port, dictionary )
    
def GetPossiblePermissions( service_type ):
    
    permissions = []
    
    permissions.append( ( HC.CONTENT_TYPE_ACCOUNTS, [ None, HC.PERMISSION_ACTION_CREATE, HC.PERMISSION_ACTION_MODERATE ] ) )
    permissions.append( ( HC.CONTENT_TYPE_ACCOUNT_TYPES, [ None, HC.PERMISSION_ACTION_MODERATE ] ) )
    permissions.append( ( HC.CONTENT_TYPE_OPTIONS, [ None, HC.PERMISSION_ACTION_MODERATE ] ) )
    
    if service_type == HC.FILE_REPOSITORY:
        
        permissions.append( ( HC.CONTENT_TYPE_FILES, [ None, HC.PERMISSION_ACTION_PETITION, HC.PERMISSION_ACTION_CREATE, HC.PERMISSION_ACTION_MODERATE ] ) )
        
    elif service_type == HC.TAG_REPOSITORY:
        
        permissions.append( ( HC.CONTENT_TYPE_MAPPINGS, [ None, HC.PERMISSION_ACTION_PETITION, HC.PERMISSION_ACTION_CREATE, HC.PERMISSION_ACTION_MODERATE ] ) )
        permissions.append( ( HC.CONTENT_TYPE_TAG_PARENTS, [ None, HC.PERMISSION_ACTION_PETITION, HC.PERMISSION_ACTION_MODERATE ] ) )
        permissions.append( ( HC.CONTENT_TYPE_TAG_SIBLINGS, [ None, HC.PERMISSION_ACTION_PETITION, HC.PERMISSION_ACTION_MODERATE ] ) )
        
    elif service_type == HC.SERVER_ADMIN:
        
        permissions.append( ( HC.CONTENT_TYPE_SERVICES, [ None, HC.PERMISSION_ACTION_MODERATE ] ) )
        
    
    return permissions
    
class Account( object ):
    
    def __init__( self, account_key: bytes, account_type: "AccountType", created: int, expires: int | None ):
        
        super().__init__()
        
        self._lock = threading.Lock()
        
        self._account_key = account_key
        self._account_type = account_type
        self._created = created
        self._expires = expires
        
        self._message = ''
        self._message_created = 0
        
        self._banned_info = None
        self._bandwidth_tracker = HydrusNetworking.BandwidthTracker()
        
        self._dirty = False
        
    
    def __repr__( self ):
        
        return 'Account: ' + self._account_type.GetTitle()
        
    
    def __str__( self ):
        
        return self.__repr__()
        
    
    def _CheckBanned( self ):
        
        if self._IsBanned():
            
            raise HydrusExceptions.InsufficientCredentialsException( 'This account is banned: ' + self._GetBannedString() )
            
        
    
    def _CheckExpired( self ):
        
        if self._IsExpired():
            
            raise HydrusExceptions.InsufficientCredentialsException( 'This account is expired: ' + self._GetExpiresString() )
            
        
    
    def _CheckFunctional( self ):
        
        if self._created == 0:
            
            raise HydrusExceptions.ConflictException( 'account is unsynced' )
            
        
        if self._IsAdmin():
            
            # admins can do anything
            return
            
        
        self._CheckBanned()
        
        self._CheckExpired()
        
        if not self._account_type.BandwidthOK( self._bandwidth_tracker ):
            
            raise HydrusExceptions.BandwidthException( 'account has exceeded bandwidth' )
            
        
    
    def _GetBannedString( self ):
        
        if self._banned_info is None:
            
            return 'not banned'
            
        else:
            
            ( reason, created, expires ) = self._banned_info
            
            return 'banned ' + HydrusTime.TimestampToPrettyTimeDelta( created ) + ', ' + HydrusTime.TimestampToPrettyExpires( expires ) + ' because: ' + reason
            
        
    
    def _GetExpiresString( self ):
        
        return HydrusTime.TimestampToPrettyExpires( self._expires )
        
    
    def _IsAdmin( self ):
        
        return self._account_type.HasPermission( HC.CONTENT_TYPE_SERVICES, HC.PERMISSION_ACTION_MODERATE )
        
    
    def _IsBanned( self ):
        
        if self._banned_info is None:
            
            return False
            
        else:
            
            ( reason, created, expires ) = self._banned_info
            
            if expires is None:
                
                return True
                
            else:
                
                if HydrusTime.TimeHasPassed( expires ):
                    
                    self._banned_info = None
                    
                    return False
                    
                else:
                    
                    return True
                    
                
            
        
    
    def _IsExpired( self ):
        
        if self._expires is None:
            
            return False
            
        else:
            
            return HydrusTime.TimeHasPassed( self._expires )
            
        
    
    def _SetDirty( self ):
        
        self._dirty = True
        
    
    def Ban( self, reason, created, expires ):
        
        with self._lock:
            
            self._banned_info = ( reason, created, expires )
            
            self._SetDirty()
            
        
    
    def CheckAtLeastOnePermission( self, content_types_and_actions ):
        
        with self._lock:
            
            if True not in ( self._account_type.HasPermission( content_type, action ) for ( content_type, action ) in content_types_and_actions ):
                
                raise HydrusExceptions.InsufficientCredentialsException( 'You do not have permission to do that.' )
                
            
        
    
    def CheckFunctional( self ):
        
        with self._lock:
        
            self._CheckFunctional()
            
        
    
    def CheckPermission( self, content_type, action ):
        
        with self._lock:
            
            if self._IsAdmin():
                
                return
                
            
            self._CheckBanned()
            
            self._CheckExpired()
            
            if not self._account_type.HasPermission( content_type, action ):
                
                raise HydrusExceptions.InsufficientCredentialsException( 'You do not have permission to do that.' )
                
            
        
    
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
            
        
    
    def GetBandwidthTracker( self ):
        
        with self._lock:
            
            return self._bandwidth_tracker
            
        
    
    def GetBannedInfo( self ):
        
        with self._lock:
            
            return self._banned_info
            
        
    
    def GetCreated( self ):
        
        with self._lock:
            
            return self._created
            
        
    
    def GetExpires( self ):
        
        with self._lock:
            
            return self._expires
            
        
    
    def GetExpiresString( self ):
        
        with self._lock:
            
            if self._IsBanned():
                
                return self._GetBannedString()
                
            else:
                
                return self._GetExpiresString()
                
            
        
    
    def GetMessageAndTimestamp( self ):
        
        with self._lock:
            
            return ( self._message, self._message_created )
            
        
    
    def GetSingleLineTitle( self ):
        
        with self._lock:
            
            text = self._account_key.hex()
            
            text = '{}: {}'.format( self._account_type.GetTitle(), text )
            
            if self._IsExpired():
                
                text = 'Expired: {}'.format( text )
                
            
            if self._IsBanned():
                
                text = 'Banned: {}'.format( text )
                
            
            if self._account_type.IsNullAccount():
                
                text = 'THIS IS NULL ACCOUNT: {}'.format( text )
                
            
            return text
            
        
    
    def GetStatusInfo( self ) -> tuple[ bool, str ]:
        
        with self._lock:
            
            try:
                
                self._CheckFunctional()
                
                return ( True, 'account is functional' )
                
            except Exception as e:
                
                return ( False, str( e ) )
                
            
        
    
    def HasPermission( self, content_type, action ):
        
        with self._lock:
            
            if self._IsAdmin():
                
                return True
                
            
            if self._IsBanned() or self._IsExpired():
                
                return False
                
            
            return self._account_type.HasPermission( content_type, action )
            
        
    
    def IsBanned( self ):
        
        with self._lock:
            
            return self._IsBanned()
            
        
    
    def IsDirty( self ):
        
        with self._lock:
            
            return self._dirty
            
        
    
    def IsExpired( self ):
        
        with self._lock:
            
            return self._IsExpired()
            
        
    
    def IsFunctional( self ):
        
        with self._lock:
            
            try:
                
                self._CheckFunctional()
                
                return True
                
            except:
                
                return False
                
            
        
    
    def IsNullAccount( self ):
        
        with self._lock:
            
            return self._account_type.IsNullAccount()
            
        
    
    def IsUnknown( self ):
        
        with self._lock:
            
            return self._created == 0
            
        
    
    def ReportDataUsed( self, num_bytes ):
        
        with self._lock:
            
            self._bandwidth_tracker.ReportDataUsed( num_bytes )
            
            self._SetDirty()
            
        
    
    def ReportRequestUsed( self ):
        
        with self._lock:
            
            self._bandwidth_tracker.ReportRequestUsed()
            
            self._SetDirty()
            
        
    
    def SetBandwidthTracker( self, bandwidth_tracker: HydrusNetworking.BandwidthTracker ):
        
        with self._lock:
            
            self._bandwidth_tracker = bandwidth_tracker
            
            self._SetDirty()
            
        
    
    def SetClean( self ):
        
        with self._lock:
            
            self._dirty = False
            
        
    
    def SetExpires( self, expires: int | None ):
        
        with self._lock:
            
            self._expires = expires
            
            self._SetDirty()
            
        
    
    def SetMessage( self, message, created ):
        
        with self._lock:
            
            self._message = message
            self._message_created = created
            
            self._SetDirty()
            
        
    
    def ToString( self ):
        
        if self.IsNullAccount():
            
            return 'This is the NULL ACCOUNT. It takes possession of old content to anonymise it. It cannot be modified.'
            
        
        with self._lock:
            
            return self._account_type.GetTitle() + ' -- created ' + HydrusTime.TimestampToPrettyTimeDelta( self._created )
            
        
    
    def Unban( self ):
        
        with self._lock:
            
            self._banned_info = None
            
            self._SetDirty()
            
        
    
    @staticmethod
    def GenerateAccountFromSerialisableTuple( serialisable_info ):
        
        ( account_key_encoded, serialisable_account_type, created, expires, dictionary_string ) = serialisable_info
        
        account_key = bytes.fromhex( account_key_encoded )
        
        if isinstance( serialisable_account_type, list ) and isinstance( serialisable_account_type[0], str ):
            
            # this is a legacy account
            
            ( encoded_account_type_key, title, account_type_dictionary_string ) = serialisable_account_type
            
            account_type_key = bytes.fromhex( encoded_account_type_key )
            
            from hydrus.core.networking import HydrusNetworkLegacy
            
            account_type = HydrusNetworkLegacy.ConvertToNewAccountType( account_type_key, title, account_type_dictionary_string )
            
        else:
            
            account_type = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_account_type )
            
        
        dictionary = HydrusSerialisable.CreateFromString( dictionary_string )
        
        return Account.GenerateAccountFromTuple( ( account_key, account_type, created, expires, dictionary ) )
        
    
    @staticmethod
    def GenerateAccountFromTuple( serialisable_info ):
        
        ( account_key, account_type, created, expires, dictionary ) = serialisable_info
        
        if 'message' not in dictionary:
            
            dictionary[ 'message' ] = ''
            dictionary[ 'message_created' ] = 0
            
        
        banned_info = dictionary[ 'banned_info' ]
        bandwidth_tracker = dictionary[ 'bandwidth_tracker' ]
        
        account = Account( account_key, account_type, created, expires )
        
        account.SetBandwidthTracker( bandwidth_tracker )
        
        if banned_info is not None:
            
            ( reason, created, expires ) = banned_info
            
            account.Ban( reason, created, expires )
            
        
        message = dictionary[ 'message' ]
        message_created = dictionary[ 'message_created' ]
        
        account.SetMessage( message, message_created )
        
        account.SetClean()
        
        return account
        
    
    @staticmethod
    def GenerateSerialisableTupleFromAccount( account ):
        
        ( account_key, account_type, created, expires, dictionary ) = Account.GenerateTupleFromAccount( account )
        
        account_key_encoded = account_key.hex()
        
        serialisable_account_type = account_type.GetSerialisableTuple()
        
        dictionary_string = dictionary.DumpToString()
        
        return ( account_key_encoded, serialisable_account_type, created, expires, dictionary_string )
        
    
    @staticmethod
    def GenerateTupleFromAccount( account: "Account" ):
        
        account_key = account.GetAccountKey()
        account_type = account.GetAccountType()
        created = account.GetCreated()
        expires = account.GetExpires()
        
        banned_info = account.GetBannedInfo()
        bandwidth_tracker = account.GetBandwidthTracker()
        
        ( message, message_created ) = account.GetMessageAndTimestamp()
        
        dictionary = HydrusSerialisable.SerialisableDictionary()
        
        dictionary[ 'banned_info' ] = banned_info
        
        dictionary[ 'bandwidth_tracker' ] = bandwidth_tracker
        
        dictionary[ 'message' ] = message
        dictionary[ 'message_created' ] = message_created
        
        dictionary = dictionary.Duplicate()
        
        return ( account_key, account_type, created, expires, dictionary )
        
    
    @staticmethod
    def GenerateUnknownAccount( account_key = b'' ):
        
        account_type = AccountType.GenerateUnknownAccountType()
        created = 0
        expires = None
        
        unknown_account = Account( account_key, account_type, created, expires )
        
        return unknown_account
        
    
class AccountIdentifier( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_ACCOUNT_IDENTIFIER
    SERIALISABLE_NAME = 'Account Identifier'
    SERIALISABLE_VERSION = 1
    
    TYPE_ACCOUNT_KEY = 1
    TYPE_CONTENT = 2
    
    def __init__( self, account_key = None, content = None ):
        
        super().__init__()
        
        if account_key is not None:
            
            self._type = self.TYPE_ACCOUNT_KEY
            self._data = account_key
            
        elif content is not None:
            
            self._type = self.TYPE_CONTENT
            self._data = content
            
        
    
    def __eq__( self, other ):
        
        if isinstance( other, AccountIdentifier ):
            
            return self.__hash__() == other.__hash__()
            
        
        return NotImplemented
        
    
    def __hash__( self ): return ( self._type, self._data ).__hash__()
    
    def __repr__( self ): return 'Account Identifier: ' + str( ( self._type, self._data ) )
    
    def _GetSerialisableInfo( self ):
        
        if self._type == self.TYPE_ACCOUNT_KEY:
            
            serialisable_data = self._data.hex()
            
        elif self._type == self.TYPE_CONTENT:
            
            serialisable_data = self._data.GetSerialisableTuple()
            
        
        return ( self._type, serialisable_data )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._type, serialisable_data ) = serialisable_info
        
        if self._type == self.TYPE_ACCOUNT_KEY:
            
            self._data = bytes.fromhex( serialisable_data )
            
        elif self._type == self.TYPE_CONTENT:
            
            self._data = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_data )
            
        
    
    def GetAccountKey( self ) -> bytes:
        
        if not self.HasAccountKey():
            
            raise Exception( 'This Account Identifier does not have an account id!' )
            
        
        return self._data
        
    
    def GetContent( self ) -> "Content":
        
        if not self.HasContent():
            
            raise Exception( 'This Account Identifier does not have content!' )
            
        
        return self._data
        
    
    def GetData( self ):
        
        return self._data
        
    
    def HasAccountKey( self ):
        
        return self._type == self.TYPE_ACCOUNT_KEY
        
    
    def HasContent( self ):
        
        return self._type == self.TYPE_CONTENT
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_ACCOUNT_IDENTIFIER ] = AccountIdentifier

class AccountType( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_ACCOUNT_TYPE
    SERIALISABLE_NAME = 'Account Type'
    SERIALISABLE_VERSION = 2
    
    def __init__(
        self,
        account_type_key = None,
        title = None,
        permissions = None,
        bandwidth_rules = None,
        auto_creation_velocity = None,
        auto_creation_history = None
        ):
        
        super().__init__()
        
        if account_type_key is None:
            
            account_type_key = HydrusData.GenerateKey()
            
        
        if title is None:
            
            title = 'standard user'
            
        
        if permissions is None:
            
            permissions = {}
            
        
        if bandwidth_rules is None:
            
            bandwidth_rules = HydrusNetworking.BandwidthRules()
            
        
        if auto_creation_velocity is None:
            
            auto_creation_velocity = ( 0, 86400 )
            
        
        if auto_creation_history is None:
            
            auto_creation_history = HydrusNetworking.BandwidthTracker()
            
        
        self._account_type_key = account_type_key
        self._title = title
        self._permissions = permissions
        self._bandwidth_rules = bandwidth_rules
        self._auto_creation_velocity = auto_creation_velocity
        self._auto_creation_history = auto_creation_history
        
    
    def __repr__( self ):
        
        return 'AccountType: ' + self._title
        
    
    def __str__( self ):
        
        return self.__repr__()
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_account_type_key = self._account_type_key.hex()
        serialisable_permissions = list( self._permissions.items() )
        serialisable_bandwidth_rules = self._bandwidth_rules.GetSerialisableTuple()
        serialisable_auto_creation_history = self._auto_creation_history.GetSerialisableTuple()
        
        return ( serialisable_account_type_key, self._title, serialisable_permissions, serialisable_bandwidth_rules, self._auto_creation_velocity, serialisable_auto_creation_history )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_account_type_key, self._title, serialisable_permissions, serialisable_bandwidth_rules, self._auto_creation_velocity, serialisable_auto_creation_history ) = serialisable_info
        
        self._account_type_key = bytes.fromhex( serialisable_account_type_key )
        self._permissions = dict( serialisable_permissions )
        self._bandwidth_rules = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_bandwidth_rules )
        self._auto_creation_history = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_auto_creation_history )
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( serialisable_account_type_key, title, serialisable_permissions, serialisable_bandwidth_rules, auto_creation_velocity, serialisable_auto_creation_history ) = old_serialisable_info
            
            permissions = dict( serialisable_permissions )
            
            # admins can do options
            if HC.CONTENT_TYPE_ACCOUNT_TYPES in permissions and permissions[ HC.CONTENT_TYPE_ACCOUNT_TYPES ] == HC.PERMISSION_ACTION_MODERATE:
                
                permissions[ HC.CONTENT_TYPE_OPTIONS ] = HC.PERMISSION_ACTION_MODERATE
                
            
            serialisable_permissions = list( permissions.items() )
            
            new_serialisable_info = ( serialisable_account_type_key, title, serialisable_permissions, serialisable_bandwidth_rules, auto_creation_velocity, serialisable_auto_creation_history )
            
            return ( 2, new_serialisable_info )
            
        
    
    def BandwidthOK( self, bandwidth_tracker ):
        
        return self._bandwidth_rules.CanStartRequest( bandwidth_tracker )
        
    
    def CanAutoCreateAccountNow( self ):
        
        if not self.SupportsAutoCreateAccount():
            
            return False
            
        
        ( num_accounts_per_time_delta, time_delta ) = self._auto_creation_velocity
        
        num_created = self._auto_creation_history.GetUsage( HC.BANDWIDTH_TYPE_DATA, time_delta )
        
        return num_created < num_accounts_per_time_delta
        
    
    def GetAutoCreateAccountHistory( self ) -> HydrusNetworking.BandwidthTracker:
        
        return self._auto_creation_history
        
    
    def GetAutoCreateAccountVelocity( self ):
        
        return self._auto_creation_velocity
        
    
    def GetBandwidthRules( self ):
        
        return self._bandwidth_rules
        
    
    def GetBandwidthStringsAndGaugeTuples( self, bandwidth_tracker ):
        
        return self._bandwidth_rules.GetBandwidthStringsAndGaugeTuples( bandwidth_tracker )
        
    
    def GetAccountTypeKey( self ):
        
        return self._account_type_key
        
    
    def GetPermissions( self ):
        
        return { k : v for ( k, v ) in self._permissions.items() if k != 'null' }
        
    
    def GetPermissionStrings( self ):
        
        if self.IsNullAccount():
            
            return [ 'is null account, cannot do anything' ]
            
        
        s = []
        
        for ( content_type, action ) in self.GetPermissions().items():
            
            s.append( HC.permission_pair_string_lookup[ ( content_type, action ) ] )
            
        
        return s
        
    
    def GetTitle( self ):
        
        return self._title
        
    
    def HasPermission( self, content_type, permission ):
        
        if self.IsNullAccount():
            
            return False
            
        
        if content_type not in self._permissions:
            
            return False
            
        
        my_permission = self._permissions[ content_type ]
        
        if permission == HC.PERMISSION_ACTION_MODERATE:
            
            return my_permission == HC.PERMISSION_ACTION_MODERATE
            
        elif permission == HC.PERMISSION_ACTION_CREATE:
            
            return my_permission in ( HC.PERMISSION_ACTION_CREATE, HC.PERMISSION_ACTION_MODERATE )
            
        elif permission == HC.PERMISSION_ACTION_PETITION:
            
            return my_permission in ( HC.PERMISSION_ACTION_PETITION, HC.PERMISSION_ACTION_CREATE, HC.PERMISSION_ACTION_MODERATE )
            
        
        return False
        
    
    def IsNullAccount( self ):
        
        # I had to tuck this in permissions dict because this was not during a network version update and I couldn't update the serialised object. bleargh
        # ideally though, we move this sometime to a self._is_null_account boolean
        
        return 'null' in self._permissions
        
    
    def ReportAutoCreateAccount( self ):
        
        self._auto_creation_history.ReportRequestUsed()
        
    
    def SetToNullAccount( self ):
        
        # I had to tuck this in permissions dict because this was not during a network version update and I couldn't update the serialised object. bleargh
        # ideally though, we move this sometime to a self._is_null_account boolean
        
        self._permissions[ 'null' ] = True
        
    
    def SupportsAutoCreateAccount( self ):
        
        if self.IsNullAccount():
            
            return False
            
        
        ( num_accounts_per_time_delta, time_delta ) = self._auto_creation_velocity
        
        return num_accounts_per_time_delta > 0
        
    
    @staticmethod
    def GenerateAdminAccountType( service_type ):
        
        bandwidth_rules = HydrusNetworking.BandwidthRules()
        
        permissions = {}
        
        permissions[ HC.CONTENT_TYPE_ACCOUNTS ] = HC.PERMISSION_ACTION_MODERATE
        permissions[ HC.CONTENT_TYPE_ACCOUNT_TYPES ] = HC.PERMISSION_ACTION_MODERATE
        permissions[ HC.CONTENT_TYPE_OPTIONS ] = HC.PERMISSION_ACTION_MODERATE
        
        if service_type in HC.REPOSITORIES:
            
            for content_type in HC.SERVICE_TYPES_TO_CONTENT_TYPES[ service_type ]:
                
                permissions[ content_type ] = HC.PERMISSION_ACTION_MODERATE
                
            
        elif service_type == HC.SERVER_ADMIN:
            
            permissions[ HC.CONTENT_TYPE_SERVICES ] = HC.PERMISSION_ACTION_MODERATE
            
        else:
            
            raise NotImplementedError( 'Do not have a default admin account type set up for this service yet!' )
            
        
        account_type = AccountType.GenerateNewAccountType( 'administrator', permissions, bandwidth_rules )
        
        return account_type
        
    
    @staticmethod
    def GenerateNewAccountType( title, permissions, bandwidth_rules ):
        
        account_type_key = HydrusData.GenerateKey()
        
        return AccountType( account_type_key = account_type_key, title = title, permissions = permissions, bandwidth_rules = bandwidth_rules )
        
    
    @staticmethod
    def GenerateNullAccountType():
        
        account_type_key = HydrusData.GenerateKey()
        
        title = 'null account'
        permissions = {}
        bandwidth_rules = HydrusNetworking.BandwidthRules()
        
        at = AccountType( account_type_key = account_type_key, title = title, permissions = permissions, bandwidth_rules = bandwidth_rules )
        
        at.SetToNullAccount()
        
        return at
        
    
    @staticmethod
    def GenerateUnknownAccountType():
        
        title = 'unknown account'
        
        permissions = {}
        
        bandwidth_rules = HydrusNetworking.BandwidthRules()
        bandwidth_rules.AddRule( HC.BANDWIDTH_TYPE_REQUESTS, None, 0 )
        
        unknown_account_type = AccountType.GenerateNewAccountType( title, permissions, bandwidth_rules )
        
        return unknown_account_type
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_ACCOUNT_TYPE ] = AccountType

class ClientToServerUpdate( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_CLIENT_TO_SERVER_UPDATE
    SERIALISABLE_NAME = 'Client To Server Update'
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        super().__init__()
        
        self._actions_to_contents_and_reasons = collections.defaultdict( list )
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_info = []
        
        for ( action, contents_and_reasons ) in list(self._actions_to_contents_and_reasons.items()):
            
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
        
    
    def ApplyTagFilterToPendingMappings( self, tag_filter: HydrusTags.TagFilter ):
        
        if HC.CONTENT_UPDATE_PEND in self._actions_to_contents_and_reasons:
            
            contents_and_reasons = self._actions_to_contents_and_reasons[ HC.CONTENT_UPDATE_PEND ]
            
            new_contents_and_reasons = []
            
            for ( content, reason ) in contents_and_reasons:
                
                if content.GetContentType() == HC.CONTENT_TYPE_MAPPINGS:
                    
                    ( tag, hashes ) = content.GetContentData()
                    
                    if not tag_filter.TagOK( tag ):
                        
                        continue
                        
                    
                
                new_contents_and_reasons.append( ( content, reason ) )
                
            
            self._actions_to_contents_and_reasons[ HC.CONTENT_UPDATE_PEND ] = new_contents_and_reasons
            
        
    
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
        
    
    def IterateAllActionsAndContentsAndReasons( self ):
        
        for ( action, contents_and_reasons ) in self._actions_to_contents_and_reasons.items():
            
            for ( content, reason ) in contents_and_reasons:
                
                yield ( action, content, reason )
                
            
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_CLIENT_TO_SERVER_UPDATE ] = ClientToServerUpdate

class Content( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_CONTENT
    SERIALISABLE_NAME = 'Content'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, content_type = None, content_data = None ):
        
        super().__init__()
        
        self._content_type = content_type
        self._content_data = content_data
        
    
    def __eq__( self, other ):
        
        if isinstance( other, Content ):
            
            return self.__hash__() == other.__hash__()
            
        
        return NotImplemented
        
    
    def __hash__( self ): return ( self._content_type, self._content_data ).__hash__()
    
    def __repr__( self ): return 'Content: ' + self.ToString()
    
    def _GetSerialisableInfo( self ):
        
        def EncodeHashes( hs ):
            
            return [ h.hex() for h in hs ]
            
        
        if self._content_type == HC.CONTENT_TYPE_FILES:
            
            hashes = self._content_data
            
            serialisable_content = EncodeHashes( hashes )
            
        elif self._content_type == HC.CONTENT_TYPE_MAPPING:
            
            ( tag, hash ) = self._content_data
            
            serialisable_content = ( tag, hash.hex() )
            
        elif self._content_type == HC.CONTENT_TYPE_MAPPINGS:
            
            ( tag, hashes ) = self._content_data
            
            serialisable_content = ( tag, EncodeHashes( hashes ) )
            
        elif self._content_type in ( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_TYPE_TAG_SIBLINGS ):
            
            ( old_tag, new_tag ) = self._content_data
            
            serialisable_content = ( old_tag, new_tag )
            
        
        return ( self._content_type, serialisable_content )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        def DecodeHashes( hs ):
            
            return [ bytes.fromhex( h ) for h in hs ]
            
        
        ( self._content_type, serialisable_content ) = serialisable_info
        
        if self._content_type == HC.CONTENT_TYPE_FILES:
            
            serialisable_hashes = serialisable_content
            
            self._content_data = DecodeHashes( serialisable_hashes )
            
        elif self._content_type == HC.CONTENT_TYPE_MAPPING:
            
            ( tag, serialisable_hash ) = serialisable_content
            
            self._content_data = ( tag, bytes.fromhex( serialisable_hash ) )
            
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
        
    
    def GetActualWeight( self ):
        
        if self._content_type in ( HC.CONTENT_TYPE_FILES, HC.CONTENT_TYPE_MAPPINGS ):
            
            return len( self.GetHashes() )
            
        else:
            
            return 1
            
        
    
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
        
    
    def IterateUploadableChunks( self ):
        
        if self._content_type == HC.CONTENT_TYPE_FILES:
            
            hashes = self._content_data
            
            for chunk_of_hashes in HydrusLists.SplitListIntoChunks( hashes, 100 ):
                
                content = Content( content_type = self._content_type, content_data = chunk_of_hashes )
                
                yield content
                
            
        elif self._content_type == HC.CONTENT_TYPE_MAPPINGS:
            
            ( tag, hashes ) = self._content_data
            
            for chunk_of_hashes in HydrusLists.SplitListIntoChunks( hashes, 500 ):
                
                content = Content( content_type = self._content_type, content_data = ( tag, chunk_of_hashes ) )
                
                yield content
                
            
        else:
            
            yield self
            
        
    
    def ToString( self ):
        
        if self._content_type == HC.CONTENT_TYPE_FILES:
            
            hashes = self._content_data
            
            text = 'FILES: ' + HydrusNumbers.ToHumanInt( len( hashes ) ) + ' files'
            
        elif self._content_type == HC.CONTENT_TYPE_MAPPING:
            
            ( tag, hash ) = self._content_data
            
            text = 'MAPPING: ' + tag + ' for ' + hash.hex()
            
        elif self._content_type == HC.CONTENT_TYPE_MAPPINGS:
            
            ( tag, hashes ) = self._content_data
            
            text = 'MAPPINGS: ' + tag + ' for ' + HydrusNumbers.ToHumanInt( len( hashes ) ) + ' files'
            
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
    SERIALISABLE_NAME = 'Content Update'
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        super().__init__()
        
        self._content_data = {}
        
    
    def _GetContent( self, content_type, action ):
        
        if content_type in self._content_data:
            
            if action in self._content_data[ content_type ]:
                
                return self._content_data[ content_type ][ action ]
                
            
        
        return []
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_info = []
        
        for ( content_type, actions_to_datas ) in list(self._content_data.items()):
            
            serialisable_actions_to_datas = list(actions_to_datas.items())
            
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
        
    
    def GetNumRows( self, content_types_to_count = None ):
        
        num = 0
        
        for content_type in self._content_data:
            
            if content_types_to_count is not None and content_type not in content_types_to_count:
                
                continue
                
            
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
    SERIALISABLE_NAME = 'Credentials'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, host = None, port = None, access_key = None ):
        
        super().__init__()
        
        self._host = host
        self._port = port
        self._access_key = access_key
        
    
    def __eq__( self, other ):
        
        if isinstance( other, Credentials ):
            
            return self.__hash__() == other.__hash__()
            
        
        return NotImplemented
        
    
    def __hash__( self ):
        
        return ( self._host, self._port, self._access_key ).__hash__()
        
    
    def __repr__( self ):
        
        if self._access_key is None:
            
            access_key_str = 'no access key'
            
        else:
            
            access_key_str = self._access_key.hex()
            
        
        return 'Credentials: ' + str( ( self._host, self._port, access_key_str ) )
        
    
    def _GetSerialisableInfo( self ):
        
        if self._access_key is None:
            
            serialisable_access_key = self._access_key
            
        else:
            
            serialisable_access_key = self._access_key.hex()
            
        
        return ( self._host, self._port, serialisable_access_key )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._host, self._port, serialisable_access_key ) = serialisable_info
        
        if serialisable_access_key is None:
            
            self._access_key = serialisable_access_key
            
        else:
            
            self._access_key = bytes.fromhex( serialisable_access_key )
            
        
    
    def GetAccessKey( self ):
        
        return self._access_key
        
    
    def GetAddress( self ):
        
        return ( self._host, self._port )
        
    
    def GetConnectionString( self ):
        
        connection_string = ''
        
        if self.HasAccessKey():
            
            connection_string += self._access_key.hex() + '@'
            
        
        connection_string += self._host + ':' + str( self._port )
        
        return connection_string
        
    
    def GetPortedAddress( self ):
        
        if self._host.endswith( '/' ):
            
            host = self._host[:-1]
            
        else:
            
            host = self._host
            
        
        if '/' in host:
            
            ( actual_host, gubbins ) = self._host.split( '/', 1 )
            
            address = '{}:{}/{}'.format( actual_host, self._port, gubbins )
            
        else:
            
            address = '{}:{}'.format( self._host, self._port )
            
        
        return address
        
    
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
                
                access_key = bytes.fromhex( access_key_encoded )
                
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
    SERIALISABLE_NAME = 'Definitions Update'
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        super().__init__()
        
        self._hash_ids_to_hashes = {}
        self._tag_ids_to_tags = {}
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_info = []
        
        if len( self._hash_ids_to_hashes ) > 0:
            
            serialisable_info.append( ( HC.DEFINITIONS_TYPE_HASHES, [ ( hash_id, hash.hex() ) for ( hash_id, hash ) in list(self._hash_ids_to_hashes.items()) ] ) )
            
        
        if len( self._tag_ids_to_tags ) > 0:
            
            serialisable_info.append( ( HC.DEFINITIONS_TYPE_TAGS, list(self._tag_ids_to_tags.items()) ) )
            
        
        return serialisable_info
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        for ( definition_type, definitions ) in serialisable_info:
            
            if definition_type == HC.DEFINITIONS_TYPE_HASHES:
                
                self._hash_ids_to_hashes = { hash_id : bytes.fromhex( encoded_hash ) for ( hash_id, encoded_hash ) in definitions }
                
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
    SERIALISABLE_NAME = 'Metadata'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, metadata = None, next_update_due = None ):
        
        if metadata is None:
            
            metadata = {}
            
        
        if next_update_due is None:
            
            next_update_due = 0
            
        
        super().__init__()
        
        self._lock = threading.Lock()
        
        now = HydrusTime.GetNow()
        
        self._metadata = metadata
        self._next_update_due = next_update_due
        
        self._update_hashes = set()
        self._update_hashes_ordered = []
        
        self._biggest_end = self._CalculateBiggestEnd()
        
    
    def _CalculateBiggestEnd( self ):
        
        if len( self._metadata ) == 0:
            
            return None
            
        else:
            
            biggest_index = max( self._metadata.keys() )
            
            ( update_hashes, begin, end ) = self._GetUpdate( biggest_index )
            
            return end
            
        
    
    def _GetNextUpdateDueTime( self, from_client = False ):
        
        delay = 10
        
        if from_client:
            
            delay = UPDATE_CHECKING_PERIOD * 2
            
        
        return self._next_update_due + delay
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_metadata = [ ( update_index, [ update_hash.hex() for update_hash in update_hashes ], begin, end ) for ( update_index, ( update_hashes, begin, end ) ) in list(self._metadata.items()) ]
        
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
            
            update_hashes = [ bytes.fromhex( encoded_update_hash ) for encoded_update_hash in encoded_update_hashes ]
            
            self._metadata[ update_index ] = ( update_hashes, begin, end )
            
        
        self._RecalcHashes()
        
        self._biggest_end = self._CalculateBiggestEnd()
        
    
    def _RecalcHashes( self ):
        
        self._update_hashes = set()
        self._update_hashes_ordered = []
        
        for ( update_index, ( update_hashes, begin, end ) ) in sorted( self._metadata.items() ):
            
            self._update_hashes.update( update_hashes )
            self._update_hashes_ordered.extend( update_hashes )
            
        
    
    def AppendUpdate( self, update_hashes, begin, end, next_update_due ):
        
        with self._lock:
            
            update_index = len( self._metadata )
            
            self._metadata[ update_index ] = ( update_hashes, begin, end )
            
            self._update_hashes.update( update_hashes )
            self._update_hashes_ordered.extend( update_hashes )
            
            self._next_update_due = next_update_due
            
            self._biggest_end = end
            
        
    
    def CalculateNewNextUpdateDue( self, update_period ):
        
        with self._lock:
            
            if self._biggest_end is None:
                
                self._next_update_due = 0
                
            else:
                
                self._next_update_due = self._biggest_end + update_period
                
            
        
    
    def GetEarliestTimestampForTheseHashes( self, hashes ):
        
        hashes = set( hashes )
        
        with self._lock:
            
            for ( update_index, ( update_hashes, begin, end ) ) in sorted( self._metadata.items() ):
                
                if HydrusLists.SetsIntersect( hashes, update_hashes ):
                    
                    return end
                    
                
            
        
        return 0
        
    
    def GetNextUpdateIndex( self ):
        
        with self._lock:
            
            return len( self._metadata )
            
        
    
    def GetNextUpdateBegin( self ):
        
        with self._lock:
            
            if self._biggest_end is None:
                
                return HydrusTime.GetNow()
                
            else:
                
                return self._biggest_end + 1
                
            
        
    
    def GetNextUpdateDueString( self, from_client = False ):
        
        with self._lock:
            
            if self._next_update_due == 0:
                
                return 'have not yet synced metadata'
                
            elif self._biggest_end is None:
                
                return 'the metadata appears to be uninitialised'
                
            else:
                
                update_due = self._GetNextUpdateDueTime( from_client )
                
                if HydrusTime.TimeHasPassed( update_due ):
                    
                    s = 'checking for updates imminently'
                    
                else:
                    
                    s = 'checking for updates {}'.format( HydrusTime.TimestampToPrettyTimeDelta( update_due ) )
                    
                
                return 'metadata synced up to {}, {}'.format( HydrusTime.TimestampToPrettyTimeDelta( self._biggest_end ), s )
                
            
        
    
    def GetNumUpdateHashes( self ):
        
        with self._lock:
            
            return len( self._update_hashes )
            
        
    
    def GetSlice( self, from_update_index ):
        
        with self._lock:
            
            metadata = { update_index : row for ( update_index, row ) in self._metadata.items() if update_index >= from_update_index }
            
            return Metadata( metadata, self._next_update_due )
            
        
    
    def GetUpdateHashes( self, update_index = None ):
        
        with self._lock:
            
            if update_index is None:
                
                return set( self._update_hashes )
                
            else:
                
                return set( self._GetUpdateHashes( update_index ) )
                
            
        
    
    def GetUpdateIndexBeginAndEnd( self, update_index ):
        
        with self._lock:
            
            if update_index in self._metadata:
                
                ( update_hashes, begin, end ) = self._metadata[ update_index ]
                
                return ( begin, end )
                
            
            raise HydrusExceptions.DataMissing( 'That update index does not seem to exist!' )
            
        
    
    def GetUpdateIndicesAndTimes( self ):
        
        with self._lock:
            
            result = []
            
            for ( update_index, ( update_hashes, begin, end ) ) in self._metadata.items():
                
                result.append( ( update_index, begin, end ) )
                
            
            return result
            
        
    
    def GetUpdateIndicesAndHashes( self ):
        
        with self._lock:
            
            result = []
            
            for ( update_index, ( update_hashes, begin, end ) ) in self._metadata.items():
                
                result.append( ( update_index, update_hashes ) )
                
            
            return result
            
        
    
    def HasDoneInitialSync( self ):
        
        with self._lock:
            
            return self._next_update_due != 0
            
        
    
    def HasUpdateHash( self, update_hash ):
        
        with self._lock:
            
            return update_hash in self._update_hashes
            
        
    
    def SortContentHashesAndContentTypes( self, content_hashes_and_content_types ):
        
        with self._lock:
            
            content_hashes_to_content_types = dict( content_hashes_and_content_types )
            
            content_hashes_and_content_types = [ ( update_hash, content_hashes_to_content_types[ update_hash ] ) for update_hash in self._update_hashes_ordered if update_hash in content_hashes_to_content_types ]
            
            return content_hashes_and_content_types
            
        
    
    def UpdateASAP( self ):
        
        with self._lock:
            
            # not 0, that's reserved
            self._next_update_due = 1
            
        
    
    def UpdateDue( self, from_client = False ):
        
        with self._lock:
            
            next_update_due_time = self._GetNextUpdateDueTime( from_client )
            
            return HydrusTime.TimeHasPassed( next_update_due_time )
            
        
    
    def UpdateFromSlice( self, metadata_slice: "Metadata" ):
        
        with self._lock:
            
            self._metadata.update( metadata_slice._metadata )
            
            new_next_update_due = metadata_slice._next_update_due
            
            if HydrusTime.TimeHasPassed( new_next_update_due ):
                
                new_next_update_due = HydrusTime.GetNow() + 100000
                
            
            self._next_update_due = new_next_update_due
            self._biggest_end = self._CalculateBiggestEnd()
            
            self._RecalcHashes()
            
        
    
    def UpdateIsEmpty( self, update_index ):
        
        with self._lock:
            
            return len( self._GetUpdateHashes( update_index ) ) == 0
            
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_METADATA ] = Metadata

class Petition( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_PETITION
    SERIALISABLE_NAME = 'Petition'
    SERIALISABLE_VERSION = 3
    
    def __init__( self, petitioner_account = None, petition_header = None, actions_and_contents = None ):
        
        if actions_and_contents is None:
            
            actions_and_contents = []
            
        
        super().__init__()
        
        self._petitioner_account = petitioner_account
        self._petition_header = petition_header
        self._actions_and_contents = [ ( action, HydrusSerialisable.SerialisableList( contents ) ) for ( action, contents ) in actions_and_contents ]
        
        self._completed_actions_to_contents = collections.defaultdict( list )
        
    
    def __eq__( self, other ):
        
        if isinstance( other, Petition ):
            
            return self.__hash__() == other.__hash__()
            
        
        return NotImplemented
        
    
    def __hash__( self ):
        
        return self._petition_header.__hash__()
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_petitioner_account = Account.GenerateSerialisableTupleFromAccount( self._petitioner_account )
        serialisable_petition_header = self._petition_header.GetSerialisableTuple()
        serialisable_actions_and_contents = [ ( action, contents.GetSerialisableTuple() ) for ( action, contents ) in self._actions_and_contents ]
        
        return ( serialisable_petitioner_account, serialisable_petition_header, serialisable_actions_and_contents )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_petitioner_account, serialisable_petition_header, serialisable_actions_and_contents ) = serialisable_info
        
        self._petitioner_account = Account.GenerateAccountFromSerialisableTuple( serialisable_petitioner_account )
        self._petition_header = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_petition_header )
        self._actions_and_contents = [ ( action, HydrusSerialisable.CreateFromSerialisableTuple( serialisable_contents ) ) for ( action, serialisable_contents ) in serialisable_actions_and_contents ]
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( action, serialisable_petitioner_account, reason, serialisable_contents ) = old_serialisable_info
            
            contents = [ HydrusSerialisable.CreateFromSerialisableTuple( serialisable_content ) for serialisable_content in serialisable_contents ]
            
            actions_and_contents = [ ( action, HydrusSerialisable.SerialisableList( contents ) ) ]
            
            serialisable_actions_and_contents = [ ( action, contents.GetSerialisableTuple() ) for ( action, contents ) in actions_and_contents ]
            
            new_serialisable_info = ( serialisable_petitioner_account, reason, serialisable_actions_and_contents )
            
            return ( 2, new_serialisable_info )
            
        
        if version == 3:
            
            # we'll dump out, since this code should never be reached. a new client won't be receiving old petitions since an old server won't have the calls
            # it is appropriate to update the version though--that lets an old client talking to a new server get a nicer 'version from the future' error
            
            raise NotImplementedError()
            
        
    
    def Approve( self, action, content ):
        
        self._completed_actions_to_contents[ action ].append( content )
        
    
    def ApproveAll( self ):
        
        for ( action, contents ) in self._actions_and_contents:
            
            for content in contents:
                
                self.Approve( action, content )
                
            
        
    
    def Deny( self, action, content ):
        
        if action == HC.CONTENT_UPDATE_PEND:
            
            denial_action = HC.CONTENT_UPDATE_DENY_PEND
            
        elif action == HC.CONTENT_UPDATE_PETITION:
            
            denial_action = HC.CONTENT_UPDATE_DENY_PETITION
            
        else:
            
            raise Exception( 'Petition came with unexpected action: {}'.format( action ) )
            
        
        self._completed_actions_to_contents[ denial_action ].append( content )
        
    
    def DenyAll( self ):
        
        for ( action, contents ) in self._actions_and_contents:
            
            for content in contents:
                
                self.Deny( action, content )
                
            
        
    
    def GetCompletedUploadableClientToServerUpdates( self ):
        
        def break_contents_into_chunks( some_contents ):
            
            chunks_of_some_contents = []
            chunk_of_some_contents = []
            
            weight_of_current_chunk = 0
            
            for content in some_contents:
                
                for content_chunk in content.IterateUploadableChunks(): # break 20K-strong mappings petitions into smaller bits to POST back
                    
                    chunk_of_some_contents.append( content_chunk )
                    
                    weight_of_current_chunk += content.GetVirtualWeight()
                    
                    if weight_of_current_chunk > 50:
                        
                        chunks_of_some_contents.append( chunk_of_some_contents )
                        
                        chunk_of_some_contents = []
                        
                        weight_of_current_chunk = 0
                        
                    
                
            
            if len( chunk_of_some_contents ) > 0:
                
                chunks_of_some_contents.append( chunk_of_some_contents )
                
            
            return chunks_of_some_contents
            
        
        updates = []
        
        # make sure you delete before you add
        for action in ( HC.CONTENT_UPDATE_DENY_PETITION, HC.CONTENT_UPDATE_DENY_PEND, HC.CONTENT_UPDATE_PETITION, HC.CONTENT_UPDATE_PEND ):
            
            contents = self._completed_actions_to_contents[ action ]
            
            if len( contents ) == 0:
                
                continue
                
            
            chunks_of_contents = break_contents_into_chunks( contents )
            
            for chunk_of_contents in chunks_of_contents:
                
                update = ClientToServerUpdate()
                
                for content in chunk_of_contents:
                    
                    update.AddContent( action, content, self._petition_header.reason )
                    
                
                updates.append( update )
                
            
        
        return updates
        
    
    def GetContents( self, action ):
        
        actions_to_contents = dict( self._actions_and_contents )
        
        if action in actions_to_contents:
            
            return actions_to_contents[ action ]
            
        else:
            
            return []
            
        
    
    def GetActionsAndContents( self ):
        
        return self._actions_and_contents
        
    
    def GetPetitionerAccount( self ):
        
        return self._petitioner_account
        
    
    def GetPetitionHeader( self ) -> "PetitionHeader":
        
        return self._petition_header
        
    
    def GetReason( self ):
        
        return self._petition_header.reason
        
    
    def GetActualContentWeight( self ) -> int:
        
        total_weight = 0
        
        for ( action, contents ) in self._actions_and_contents:
            
            for content in contents:
                
                total_weight += content.GetActualWeight()
                
            
        
        return total_weight
        
    
    def GetContentSummary( self ) -> str:
        
        num_sub_petitions = sum( ( len( contents ) for ( action, contents ) in self._actions_and_contents ) )
        
        if self._petition_header.content_type == HC.CONTENT_TYPE_MAPPINGS and num_sub_petitions > 1:
            
            return '{} mappings in {} petitions'.format( HydrusNumbers.ToHumanInt( self.GetActualContentWeight() ), HydrusNumbers.ToHumanInt( num_sub_petitions ) )
            
        else:
            
            return '{} {}'.format( HydrusNumbers.ToHumanInt( self.GetActualContentWeight() ), HC.content_type_string_lookup[ self._petition_header.content_type ] )
            
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_PETITION ] = Petition

class PetitionHeader( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_PETITION_HEADER
    SERIALISABLE_NAME = 'Petitions Header'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, content_type = None, status = None, account_key = None, reason = None ):
        
        if content_type is None:
            
            content_type = HC.CONTENT_TYPE_MAPPINGS
            
        
        if status is None:
            
            status = HC.CONTENT_STATUS_PETITIONED
            
        
        if account_key is None:
            
            account_key = b''
            
        
        if reason is None:
            
            reason = ''
            
        
        super().__init__()
        
        self.content_type = content_type
        self.status = status
        self.account_key = account_key
        self.reason = reason
        
    
    def __eq__( self, other ):
        
        if isinstance( other, PetitionHeader ):
            
            return self.__hash__() == other.__hash__()
            
        
        return NotImplemented
        
    
    def __hash__( self ):
        
        return ( self.content_type, self.status, self.account_key, self.reason ).__hash__()
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_account_key = self.account_key.hex()
        
        return ( self.content_type, self.status, serialisable_account_key, self.reason )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self.content_type, self.status, serialisable_account_key, self.reason ) = serialisable_info
        
        self.account_key = bytes.fromhex( serialisable_account_key )
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_PETITION_HEADER ] = PetitionHeader

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
        
    
    def AllowsNonLocalConnections( self ):
        
        with self._lock:
            
            return True
            
        
    
    def BandwidthOK( self ):
        
        with self._lock:
            
            return True
            
        
    
    def Duplicate( self ):
        
        with self._lock:
            
            dictionary = self._GetSerialisableDictionary()
            
            dictionary = dictionary.Duplicate()
            
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
            
        
    
    def LogsRequests( self ):
        
        return True
        
    
    def ReportDataUsed( self, num_bytes ):
        
        with self._lock:
            
            self._bandwidth_tracker.ReportDataUsed( num_bytes )
            
            self._SetDirty()
            
        
    
    def ReportRequestUsed( self ):
        
        with self._lock:
            
            self._bandwidth_tracker.ReportRequestUsed()
            
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
            
        
    
    def SupportsCORS( self ):
        
        return False
        
    
    def ToSerialisableTuple( self ):
        
        with self._lock:
            
            dictionary = self._GetSerialisableDictionary()
            
            dictionary_string = dictionary.DumpToString()
            
            return ( self._service_key.hex(), self._service_type, self._name, self._port, dictionary_string )
            
        
    
    def ToTuple( self ):
        
        with self._lock:
            
            dictionary = self._GetSerialisableDictionary()
            
            dictionary = dictionary.Duplicate()
            
            return ( self._service_key, self._service_type, self._name, self._port, dictionary )
            
        
    
    def UseNormieEris( self ):
        
        with self._lock:
            
            return False
            
        
    
class ServerServiceRestricted( ServerService ):
    
    def _GetSerialisableDictionary( self ):
        
        dictionary = ServerService._GetSerialisableDictionary( self )
        
        dictionary[ 'bandwidth_rules' ] = self._bandwidth_rules
        
        dictionary[ 'service_options' ] = self._service_options
        
        dictionary[ 'server_message' ] = self._server_message
        
        return dictionary
        
    
    def _LoadFromDictionary( self, dictionary ):
        
        ServerService._LoadFromDictionary( self, dictionary )
        
        if 'service_options' not in dictionary:
            
            dictionary[ 'service_options' ] = HydrusSerialisable.SerialisableDictionary()
            
        
        self._service_options = HydrusSerialisable.SerialisableDictionary( dictionary[ 'service_options' ] )
        
        if 'server_message' not in self._service_options:
            
            self._service_options[ 'server_message' ] = ''
            
        
        self._server_message = self._service_options[ 'server_message' ]
        
        self._bandwidth_rules = dictionary[ 'bandwidth_rules' ]
        
    
    def BandwidthOK( self ):
        
        with self._lock:
            
            return self._bandwidth_rules.CanStartRequest( self._bandwidth_tracker )
            
        
    
class ServerServiceRepository( ServerServiceRestricted ):
    
    def _GetSerialisableDictionary( self ):
        
        dictionary = ServerServiceRestricted._GetSerialisableDictionary( self )
        
        dictionary[ 'metadata' ] = self._metadata
        dictionary[ 'next_nullification_update_index' ] = self._next_nullification_update_index
        
        return dictionary
        
    
    def _LoadFromDictionary( self, dictionary ):
        
        ServerServiceRestricted._LoadFromDictionary( self, dictionary )
        
        if 'update_period' not in self._service_options:
            
            self._service_options[ 'update_period' ] = 100000
            
        
        if 'nullification_period' in dictionary:
            
            default_nullification_period = dictionary[ 'nullification_period' ]
            
            del dictionary[ 'nullification_period' ]
            
        else:
            
            default_nullification_period = 90 * 86400
            
        
        if 'nullification_period' not in self._service_options:
            
            self._service_options[ 'nullification_period' ] = default_nullification_period
            
        
        if 'next_nullification_update_index' not in dictionary:
            
            dictionary[ 'next_nullification_update_index' ] = 0
            
        
        self._next_nullification_update_index = dictionary[ 'next_nullification_update_index' ]
        
        self._metadata = dictionary[ 'metadata' ]
        
    
    def GetMetadata( self ):
        
        with self._lock:
            
            return self._metadata
            
        
    
    def GetMetadataSlice( self, from_update_index ):
        
        with self._lock:
            
            return self._metadata.GetSlice( from_update_index )
            
        
    
    def GetNullificationPeriod( self ) -> int:
        
        with self._lock:
            
            return self._service_options[ 'nullification_period' ]
            
        
    
    def GetUpdatePeriod( self ) -> int:
        
        with self._lock:
            
            return self._service_options[ 'update_period' ]
            
        
    
    def HasUpdateHash( self, update_hash ):
        
        with self._lock:
            
            return self._metadata.HasUpdateHash( update_hash )
            
        
    
    def NullifyHistory( self ):
        
        # when there is a huge amount to catch up on, we don't want to bosh the server for ages
        # instead we'll hammer the server for an hour and then break (for ~three hours, should be)
        
        MAX_WAIT_TIME_WHEN_HEAVY_UPDATES = 120
        
        time_started_nullifying = HydrusTime.GetNow()
        time_to_stop_nullifying = time_started_nullifying + 3600
        
        while not HG.started_shutdown:
            
            with self._lock:
                
                next_update_index = self._metadata.GetNextUpdateIndex()
                
                # we are caught up on a server with update times longer than nullification_period
                if self._next_nullification_update_index >= next_update_index:
                    
                    return
                    
                
                ( nullification_begin, nullification_end ) = self._metadata.GetUpdateIndexBeginAndEnd( self._next_nullification_update_index )
                
                nullification_period = self._service_options[ 'nullification_period' ]
                
                # it isn't time to do the next yet!
                if not HydrusTime.TimeHasPassed( nullification_end + nullification_period ):
                    
                    return
                    
                
                if self._metadata.UpdateIsEmpty( self._next_nullification_update_index ):
                    
                    HydrusData.Print( 'Account history for "{}" update {} was empty, so nothing to anonymise.'.format( self._name, self._next_nullification_update_index ) )
                    
                    self._next_nullification_update_index += 1
                    
                    self._SetDirty()
                    
                    continue
                    
                
                service_key = self._service_key
                
            
            locked = HG.server_busy.acquire( False ) # pylint: disable=E1111
            
            if not locked:
                
                return
                
            
            try:
                
                HydrusData.Print( 'Nullifying account history for "{}" update {}.'.format( self._name, self._next_nullification_update_index ) )
                
                update_started = HydrusTime.GetNowFloat()
                
                HG.controller.WriteSynchronous( 'nullify_history', service_key, nullification_begin, nullification_end )
                
                update_took = HydrusTime.GetNowFloat() - update_started
                
                with self._lock:
                    
                    HydrusData.Print( 'Account history for "{}" update {} was anonymised in {}.'.format( self._name, self._next_nullification_update_index, HydrusTime.TimeDeltaToPrettyTimeDelta( update_took ) ) )
                    
                    self._next_nullification_update_index += 1
                    
                    self._SetDirty()
                    
                
            finally:
                
                HG.server_busy.release()
                
            
            if HydrusTime.TimeHasPassed( time_to_stop_nullifying ):
                
                return
                
            
            if update_took < 0.5:
                
                continue
                
            
            time_to_wait = min( update_took, MAX_WAIT_TIME_WHEN_HEAVY_UPDATES )
            
            resume_timestamp = HydrusTime.GetNowFloat() + time_to_wait
            
            while not HG.started_shutdown and not HydrusTime.TimeHasPassedFloat( resume_timestamp ):
                
                time.sleep( 1 )
                
            
        
    
    def SetNullificationPeriod( self, nullification_period: int ):
        
        with self._lock:
            
            self._service_options[ 'nullification_period' ] = nullification_period
            
            self._SetDirty()
            
        
        HG.controller.pub( 'notify_new_nullification' )
        
    
    def SetUpdatePeriod( self, update_period: int ):
        
        with self._lock:
            
            self._service_options[ 'update_period' ] = update_period
            
            self._metadata.CalculateNewNextUpdateDue( update_period )
            
            self._SetDirty()
            
        
        HG.controller.pub( 'notify_new_repo_sync' )
        
    
    def Sync( self ):
        
        with self._lock:
            
            update_due = self._metadata.UpdateDue()
            
        
        update_created = False
        
        if update_due:
            
            locked = HG.server_busy.acquire( False ) # pylint: disable=E1111
            
            if not locked:
                
                return
                
            
            try:
                
                while update_due:
                    
                    with self._lock:
                        
                        service_key = self._service_key
                        
                        begin = self._metadata.GetNextUpdateBegin()
                        
                    
                    update_period = self._service_options[ 'update_period' ]
                    
                    end = begin + update_period
                    
                    update_hashes = HG.controller.WriteSynchronous( 'create_update', service_key, begin, end )
                    
                    update_created = True
                    
                    next_update_due = end + update_period
                    
                    with self._lock:
                        
                        self._metadata.AppendUpdate( update_hashes, begin, end, next_update_due )
                        
                        update_due = self._metadata.UpdateDue()
                        
                    
                
            finally:
                
                HG.server_busy.release()
                
                if update_created:
                    
                    HG.controller.pub( 'notify_update_created' )
                    
                
            
            with self._lock:
                
                self._SetDirty()
                
            
        
        
    
class ServerServiceRepositoryTag( ServerServiceRepository ):
    
    def _LoadFromDictionary( self, dictionary ):
        
        ServerServiceRepository._LoadFromDictionary( self, dictionary )
        
        if 'tag_filter' not in self._service_options:
            
            self._service_options[ 'tag_filter' ] = HydrusTags.TagFilter()
            
        
    
    def GetTagFilter( self ) -> HydrusTags.TagFilter:
        
        with self._lock:
            
            return self._service_options[ 'tag_filter' ]
            
        
    
    def SetTagFilter( self, tag_filter: HydrusTags.TagFilter ):
        
        with self._lock:
            
            self._service_options[ 'tag_filter' ] = tag_filter
            
            self._SetDirty()
            
        
    

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
        
    
    def ServerBandwidthOK( self ):
        
        with self._lock:
            
            return self._server_bandwidth_rules.CanStartRequest( self._server_bandwidth_tracker )
            
        
    
    def ServerReportDataUsed( self, num_bytes ):
        
        with self._lock:
            
            self._server_bandwidth_tracker.ReportDataUsed( num_bytes )
            
            self._SetDirty()
            
        
    
    def ServerReportRequestUsed( self ):
        
        with self._lock:
            
            self._server_bandwidth_tracker.ReportRequestUsed()
            
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
        
    
