import collections
import collections.abc

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusNumbers
from hydrus.core.networking import HydrusNetwork

from hydrus.client import ClientGlobals as CG
def ConvertClientToServerUpdateToContentUpdates( client_to_server_update: HydrusNetwork.ClientToServerUpdate ):
    
    content_updates = []
    
    for ( action, content, reason ) in client_to_server_update.IterateAllActionsAndContentsAndReasons():
        
        content_type = content.GetContentType()
        
        if action == HC.CONTENT_UPDATE_PEND:
            
            content_update_action = HC.CONTENT_UPDATE_ADD
            
        elif action == HC.CONTENT_UPDATE_PETITION:
            
            content_update_action = HC.CONTENT_UPDATE_DELETE
            
        else:
            
            continue
            
        
        row = content.GetContentData()
        
        content_update = ContentUpdate( content_type, content_update_action, row, reason = reason )
        
        content_updates.append( content_update )
        
    
    return content_updates
    

class ContentUpdate( object ):
    
    # TODO: for all content types, we should have the ability to gauge weight (or a similar "processing weight" for the content type) and split into smaller update batches
    # rather than doing it all at the level of GetContentUpdatesForAppliedContentApplicationCommandRatingsIncDec and friends, we should be able to make a gonk content update wherever and then break it up here, agnostic of content type
    
    def __init__( self, data_type, action, row, reason = None ):
        
        self._data_type = data_type
        self._action = action
        self._row = row
        self._reason = reason
        self._hashes = None
        
    
    def __eq__( self, other ):
        
        if isinstance( other, ContentUpdate ):
            
            return self.__hash__() == other.__hash__()
            
        
        return NotImplemented
        
    
    def __hash__( self ):
        
        # TODO: this doesn't work great, it turns out, since the hash set can be in different orders when 'repr'd
        # when we move to a ContentUpdateAction and so on, with separated hashes, I think we'll be on the road to fixing this
        return hash( ( self._data_type, self._action, repr( self._row ) ) )
        
    
    def __repr__( self ):
        
        return 'Content Update: ' + str( ( self._data_type, self._action, self._row, self._reason ) )
        
    
    def GetAction( self ):
        
        return self._action
        
    
    def GetDataType( self ):
        
        return self._data_type
        
    
    def GetHashes( self ):
        
        if self._hashes is not None:
            
            return self._hashes
            
        
        hashes = set()
        
        if self._data_type == HC.CONTENT_TYPE_FILES:
            
            if self._action == HC.CONTENT_UPDATE_ADD:
                
                ( file_info_manager, timestamp_ms ) = self._row
                
                hashes = { file_info_manager.hash }
                
            else:
                
                hashes = self._row
                
                if hashes is None:
                    
                    hashes = set()
                    
                
            
        elif self._data_type == HC.CONTENT_TYPE_DIRECTORIES:
            
            hashes = set()
            
        elif self._data_type == HC.CONTENT_TYPE_URLS:
            
            ( urls, hashes ) = self._row
            
        elif self._data_type == HC.CONTENT_TYPE_TIMESTAMP:
            
            ( hashes, timestamp_data ) = self._row
            
            hashes = set( hashes )
            
        elif self._data_type == HC.CONTENT_TYPE_MAPPINGS:
            
            if self._action == HC.CONTENT_UPDATE_ADVANCED:
                
                hashes = set()
                
            else:
                
                ( tag, hashes ) = self._row
                
            
        elif self._data_type in ( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_TYPE_TAG_SIBLINGS ):
            
            hashes = set()
            
        elif self._data_type == HC.CONTENT_TYPE_RATINGS:
            
            if self._action == HC.CONTENT_UPDATE_ADD:
                
                ( rating, hashes ) = self._row
                
            
        elif self._data_type == HC.CONTENT_TYPE_NOTES:
            
            if self._action == HC.CONTENT_UPDATE_SET:
                
                ( hash, name, note ) = self._row
                
                hashes = { hash }
                
            elif self._action == HC.CONTENT_UPDATE_DELETE:
                
                ( hash, name ) = self._row
                
                hashes = { hash }
                
            
        elif self._data_type == HC.CONTENT_TYPE_FILE_VIEWING_STATS:
            
            if self._action == HC.CONTENT_UPDATE_ADD:
                
                ( hash, canvas_type, view_timestamp_ms, views_delta, viewtime_delta_ms ) = self._row
                
                hashes = { hash }
                
            elif self._action == HC.CONTENT_UPDATE_SET:
                
                ( hash, canvas_type, view_timestamp_ms, views, viewtime_ms ) = self._row
                
                hashes = { hash }
                
            elif self._action == HC.CONTENT_UPDATE_DELETE:
                
                hashes = self._row
                
            
        
        if not isinstance( hashes, set ):
            
            hashes = set( hashes )
            
        
        self._hashes = hashes
        
        return hashes
        
    
    def GetReason( self ):
        
        if self._reason is None:
            
            return 'No reason given.'
            
        else:
            
            return self._reason
            
        
    
    def GetRow( self ):
        
        return self._row
        
    
    def GetWeight( self ):
        
        return len( self.GetHashes() )
        
    
    def HasReason( self ):
        
        return self._reason is not None
        
    
    def IsInboxRelated( self ):
        
        return self._action in ( HC.CONTENT_UPDATE_ARCHIVE, HC.CONTENT_UPDATE_INBOX )
        
    
    def SetReason( self, reason: str ):
        
        self._reason = reason
        
    
    def SetRow( self, row ):
        
        self._row = row
        
        self._hashes = None
        
    
    def ToActionSummary( self ):
        
        value_string = ''
        
        if self._data_type == HC.CONTENT_TYPE_URLS:
            
            ( urls, hashes ) = self._row
            
            value_string = ', '.join( urls )
            
        elif self._data_type == HC.CONTENT_TYPE_TIMESTAMP:
            
            ( hashes, timestamp_data ) = self._row
            
            value_string = timestamp_data.ToString()
            
        elif self._data_type == HC.CONTENT_TYPE_MAPPINGS:
            
            if self._action == HC.CONTENT_UPDATE_ADVANCED:
                
                value_string = 'advanced'
                
            else:
                
                ( tag, hashes ) = self._row
                
                value_string = tag
                
            
        elif self._data_type == HC.CONTENT_TYPE_RATINGS:
            
            if self._action == HC.CONTENT_UPDATE_ADD:
                
                ( rating, hashes ) = self._row
                
                value_string = str( rating )
                
            
        elif self._data_type == HC.CONTENT_TYPE_NOTES:
            
            if self._action == HC.CONTENT_UPDATE_SET:
                
                ( hash, name, note ) = self._row
                
                value_string = name
                
            elif self._action == HC.CONTENT_UPDATE_DELETE:
                
                ( hash, name ) = self._row
                
                value_string = name
                
            
        
        if value_string != '':
            
            value_string = ': ' + value_string
            
        
        try:
            
            return f'{HC.content_update_string_lookup[ self._action ]} {HC.content_type_string_lookup[ self._data_type ]}{value_string}'
            
        except Exception as e:
            
            return 'could not parse this content update!'
            
        
    
    def ToTuple( self ):
        
        return ( self._data_type, self._action, self._row )
        
    

class ContentUpdatePackage( object ):
    
    def __init__( self ):
        
        self._service_keys_to_content_updates = collections.defaultdict( list )
        
    
    def AddContentUpdate( self, service_key: bytes, content_update: ContentUpdate ):
        
        self.AddContentUpdates( service_key, ( content_update, ) )
        
    
    def AddContentUpdatePackage( self, content_update_package: "ContentUpdatePackage" ):
        
        for ( service_key, content_updates ) in content_update_package.IterateContentUpdates():
            
            self.AddContentUpdates( service_key, content_updates )
            
        
    
    def AddContentUpdates( self, service_key: bytes, content_updates: collections.abc.Collection[ ContentUpdate ] ):
        
        self._service_keys_to_content_updates[ service_key ].extend( content_updates )
        
    
    def AddServiceKeysToTags( self, hashes, service_keys_to_tags ):
        
        for ( service_key, tags ) in service_keys_to_tags.items():
            
            if len( tags ) == 0:
                
                continue
                
            
            try:
                
                service = CG.client_controller.services_manager.GetService( service_key )
                
            except HydrusExceptions.DataMissing:
                
                continue
                
            
            if service.GetServiceType() == HC.LOCAL_TAG:
                
                action = HC.CONTENT_UPDATE_ADD
                
            else:
                
                action = HC.CONTENT_UPDATE_PEND
                
            
            content_updates = [ ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, action, ( tag, hashes ) ) for tag in tags ]
            
            self.AddContentUpdates( service_key, content_updates )
            
        
    
    def FilterToHashes( self, hashes: collections.abc.Collection[ bytes ] ) -> "ContentUpdatePackage":
        
        filtered_content_update_package = ContentUpdatePackage()
        
        if not isinstance( hashes, set ):
            
            hashes = set( hashes )
            
        
        for ( service_key, content_updates ) in self.IterateContentUpdates():
            
            filtered_content_updates = [ content_update for content_update in content_updates if not hashes.isdisjoint( content_update.GetHashes() ) ]
            
            filtered_content_update_package.AddContentUpdates( service_key, filtered_content_updates )
            
        
        return filtered_content_update_package
        
    
    def GetContentUpdates( self, service_key ) -> list[ ContentUpdate ]:
        
        return self._service_keys_to_content_updates[ service_key ]
        
    
    def HasContent( self ) -> bool:
        
        return sum( [ len( content_updates ) for content_updates in self._service_keys_to_content_updates.values() ] ) > 0
        
    
    def HasContentForServiceKey( self, service_key: bytes ):
        
        if service_key in self._service_keys_to_content_updates and len( self._service_keys_to_content_updates[ service_key ] ) > 0:
            
            return True
            
        
        return False
        
    
    def IterateContentUpdates( self ) -> collections.abc.Iterator[ tuple[ bytes, list[ ContentUpdate ] ] ]:
        
        for ( service_key, content_updates ) in self._service_keys_to_content_updates.items():
            
            if len( content_updates ) > 0:
                
                yield ( service_key, content_updates )
                
            
        
    
    def ToString( self ) -> str:
        
        num_files = 0
        actions = set()
        locations = set()
        
        extra_words = ''
        
        for ( service_key, content_updates ) in self._service_keys_to_content_updates.items():
            
            if len( content_updates ) > 0:
                
                name = CG.client_controller.services_manager.GetName( service_key )
                
                locations.add( name )
                
            
            for content_update in content_updates:
                
                ( data_type, action, row ) = content_update.ToTuple()
                
                if data_type == HC.CONTENT_TYPE_MAPPINGS:
                    
                    extra_words = ' tags for'
                    
                
                actions.add( HC.content_update_string_lookup[ action ] )
                
                if action in ( HC.CONTENT_UPDATE_ARCHIVE, HC.CONTENT_UPDATE_INBOX ):
                    
                    locations = set()
                    
                
                num_files += len( content_update.GetHashes() )
                
            
        
        s = ''
        
        if len( locations ) > 0:
            
            s += ', '.join( locations ) + '->'
            
        
        s += ', '.join( actions ) + extra_words + ' ' + HydrusNumbers.ToHumanInt( num_files ) + ' files'
        
        return s
        
    
    @staticmethod
    def STATICCreateFromContentUpdate( service_key, content_update ) -> "ContentUpdatePackage":
        
        content_update_package = ContentUpdatePackage()
        
        content_update_package.AddContentUpdate( service_key, content_update )
        
        return content_update_package
        
    
    @staticmethod
    def STATICCreateFromContentUpdates( service_key, content_updates ) -> "ContentUpdatePackage":
        
        content_update_package = ContentUpdatePackage()
        
        content_update_package.AddContentUpdates( service_key, content_updates )
        
        return content_update_package
        
    
    @staticmethod
    def STATICCreateFromServiceKeysToTags( hashes, service_keys_to_tags ) -> "ContentUpdatePackage":
        
        content_update_package = ContentUpdatePackage()
        
        content_update_package.AddServiceKeysToTags( hashes, service_keys_to_tags )
        
        return content_update_package
        

    
