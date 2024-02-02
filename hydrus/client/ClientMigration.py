import os

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusLists
from hydrus.core import HydrusTagArchive
from hydrus.core import HydrusTime

from hydrus.client import ClientThreading
from hydrus.client import ClientLocation
from hydrus.client.metadata import ClientContentUpdates

pair_types_to_content_types = {}

pair_types_to_content_types[ HydrusTagArchive.TAG_PAIR_TYPE_PARENTS ] = HC.CONTENT_TYPE_TAG_PARENTS
pair_types_to_content_types[ HydrusTagArchive.TAG_PAIR_TYPE_SIBLINGS ] = HC.CONTENT_TYPE_TAG_SIBLINGS

content_types_to_pair_types = {}

content_types_to_pair_types[ HC.CONTENT_TYPE_TAG_PARENTS ] = HydrusTagArchive.TAG_PAIR_TYPE_PARENTS
content_types_to_pair_types[ HC.CONTENT_TYPE_TAG_SIBLINGS ] = HydrusTagArchive.TAG_PAIR_TYPE_SIBLINGS

def GetBasicSpeedStatement( num_done, time_started_precise ):
    
    if num_done == 0:
        
        rows_s = 0
        
    else:
        
        time_taken = HydrusTime.GetNowPrecise() - time_started_precise
        
        rows_s = int( num_done / time_taken )
        
    
    return '{} rows/s'.format( rows_s )
    
class MigrationDestination( object ):
    
    def __init__( self, controller, name ):
        
        self._controller = controller
        self._name = name
        
    
    def GetName( self ):
        
        return self._name
        
    
    def CleanUp( self ):
        
        pass
        
    
    def DoSomeWork( self, source ):
        
        raise NotImplementedError()
        
    
    def Prepare( self ):
        
        pass
        
    
class MigrationDestinationHTA( MigrationDestination ):
    
    def __init__( self, controller, path, desired_hash_type ):
        
        name = os.path.basename( path )
        
        MigrationDestination.__init__( self, controller, name )
        
        self._path = path
        self._desired_hash_type = desired_hash_type
        
        self._time_started = 0
        
        self._hta = None
        
    
    def CleanUp( self ):
        
        self._hta.CommitBigJob()
        
        if HydrusTime.TimeHasPassed( self._time_started + 120 ):
            
            self._hta.Optimise()
            
        
        self._hta.Close()
        
        self._hta = None
        
    
    def DoSomeWork( self, source ):
        
        time_started_precise = HydrusTime.GetNowPrecise()
        
        num_done = 0
        
        data = source.GetSomeData()
        
        for ( hash, tags ) in data:
            
            self._hta.AddMappings( hash, tags )
            
            num_done += len( tags )
            
        
        return GetBasicSpeedStatement( num_done, time_started_precise )
        
    
    def Prepare( self ):
        
        self._time_started = HydrusTime.GetNow()
        
        self._hta = HydrusTagArchive.HydrusTagArchive( self._path )
        
        hta_hash_type = HydrusTagArchive.hash_str_to_type_lookup[ self._desired_hash_type ]
        
        self._hta.SetHashType( hta_hash_type )
        
        self._hta.BeginBigJob()
        
    
class MigrationDestinationHTPA( MigrationDestination ):
    
    def __init__( self, controller, path, content_type ):
        
        name = os.path.basename( path )
        
        MigrationDestination.__init__( self, controller, name )
        
        self._path = path
        self._content_type = content_type
        
        self._time_started = 0
        
        self._htpa = None
        
    
    def CleanUp( self ):
        
        self._htpa.CommitBigJob()
        
        if HydrusTime.TimeHasPassed( self._time_started + 120 ):
            
            self._htpa.Optimise()
            
        
        self._htpa.Close()
        
        self._htpa = None
        
    
    def DoSomeWork( self, source ):
        
        time_started_precise = HydrusTime.GetNowPrecise()
        
        data = source.GetSomeData()
        
        self._htpa.AddPairs( data )
        
        num_done = len( data )
        
        return GetBasicSpeedStatement( num_done, time_started_precise )
        
    
    def Prepare( self ):
        
        self._time_started = HydrusTime.GetNow()
        
        self._htpa = HydrusTagArchive.HydrusTagPairArchive( self._path )
        
        pair_type = content_types_to_pair_types[ self._content_type ]
        
        self._htpa.SetPairType( pair_type )
        
        self._htpa.BeginBigJob()
        
    
class MigrationDestinationList( MigrationDestination ):
    
    def __init__( self, controller ):
        
        name = 'simple list destination'
        
        MigrationDestination.__init__( self, controller, name )
        
        self._data_received = []
        
        self._time_started = 0
        
    
    def DoSomeWork( self, source ):
        
        raise NotImplementedError()
        
    
    def GetDataReceived( self ):
        
        return self._data_received
        
    
class MigrationDestinationListMappings( MigrationDestinationList ):
    
    def DoSomeWork( self, source ):
        
        time_started_precise = HydrusTime.GetNowPrecise()
        
        num_done = 0
        
        data = source.GetSomeData()
        
        for ( hash, tags ) in data:
            
            self._data_received.append( ( hash, tags ) )
            
            num_done += len( tags )
            
        
        return GetBasicSpeedStatement( num_done, time_started_precise )
        
    
class MigrationDestinationListPairs( MigrationDestinationList ):
    
    def DoSomeWork( self, source ):
        
        time_started_precise = HydrusTime.GetNowPrecise()
        
        data = source.GetSomeData()
        
        self._data_received.extend( data )
        
        num_done = len( data )
        
        return GetBasicSpeedStatement( num_done, time_started_precise )
        
    
class MigrationDestinationTagService( MigrationDestination ):
    
    def __init__( self, controller, tag_service_key, content_action ):
        
        name = controller.services_manager.GetName( tag_service_key )
        
        MigrationDestination.__init__( self, controller, name )
        
        self._tag_service_key = tag_service_key
        
        service = self._controller.services_manager.GetService( tag_service_key )
        
        self._tag_service_type = service.GetServiceType()
        self._content_action = content_action
        
    
    def DoSomeWork( self, source ):
        
        raise NotImplementedError()
        
    
class MigrationDestinationTagServiceMappings( MigrationDestinationTagService ):
    
    def DoSomeWork( self, source ):
        
        time_started_precise = HydrusTime.GetNowPrecise()
        
        data = source.GetSomeData()
        
        content_updates = []
        
        pairs = []
        
        for ( hash, tags ) in data:
            
            pairs.extend( ( ( tag, hash ) for tag in tags ) )
            
        
        num_done = len( pairs )
        
        tags_to_hashes = HydrusData.BuildKeyToListDict( pairs )
        
        if self._content_action == HC.CONTENT_UPDATE_PETITION:
            
            reason = 'Mass Migration Job'
            
        else:
            
            reason = None
            
        
        for ( tag, hashes ) in tags_to_hashes.items():
            
            content_updates.append( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, self._content_action, ( tag, hashes ), reason = reason ) )
            
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( self._tag_service_key, content_updates )
        
        self._controller.WriteSynchronous( 'content_updates', content_update_package )
        
        return GetBasicSpeedStatement( num_done, time_started_precise )
        
    
class MigrationDestinationTagServicePairs( MigrationDestinationTagService ):
    
    def __init__( self, controller, tag_service_key, content_action, content_type ):
        
        MigrationDestinationTagService.__init__( self, controller, tag_service_key, content_action )
        
        self._content_type = content_type
        
    
    def DoSomeWork( self, source ):
        
        time_started_precise = HydrusTime.GetNowPrecise()
        
        data = source.GetSomeData()
        
        content_updates = []
        
        if self._content_action in ( HC.CONTENT_UPDATE_PETITION, HC.CONTENT_UPDATE_PEND ):
            
            reason = 'Mass Migration Job'
            
        else:
            
            reason = None
            
        
        content_updates = [ ClientContentUpdates.ContentUpdate( self._content_type, self._content_action, tag_pair, reason = reason ) for tag_pair in data ]
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( self._tag_service_key, content_updates )
        
        self._controller.WriteSynchronous( 'content_updates', content_update_package )
        
        num_done = len( data )
        
        return GetBasicSpeedStatement( num_done, time_started_precise )
        
    
class MigrationJob( object ):
    
    def __init__( self, controller, title, source, destination ):
        
        self._controller = controller
        self._title = title
        self._source = source
        self._destination = destination
        
    
    def Run( self ):
        
        job_status = ClientThreading.JobStatus( pausable = True, cancellable = True )
        
        job_status.SetStatusTitle( self._title )
        
        self._controller.pub( 'message', job_status )
        
        job_status.SetStatusText( 'preparing source' )
        
        self._source.Prepare()
        
        job_status.SetStatusText( 'preparing destination' )
        
        self._destination.Prepare()
        
        job_status.SetStatusText( 'beginning work' )
        
        try:
            
            while self._source.StillWorkToDo():
                
                progress_statement = self._destination.DoSomeWork( self._source )
                
                job_status.SetStatusText( progress_statement )
                
                job_status.WaitIfNeeded()
                
                if job_status.IsCancelled():
                    
                    break
                    
                
            
        finally:
            
            job_status.SetStatusText( 'done, cleaning up source' )
            
            self._source.CleanUp()
            
            job_status.SetStatusText( 'done, cleaning up destination' )
            
            self._destination.CleanUp()
            
            job_status.SetStatusText( 'done!' )
            
            job_status.FinishAndDismiss( 3 )
            
        
    
class MigrationSource( object ):
    
    def __init__( self, controller, name ):
        
        self._controller = controller
        self._name = name
        
        self._work_to_do = True
        
    
    def GetName( self ):
        
        return self._name
        
    
    def GetSomeData( self ):
        
        raise NotImplementedError()
        
    
    def CleanUp( self ):
        
        pass
        
    
    def Prepare( self ):
        
        pass
        
    
    def StillWorkToDo( self ):
        
        return self._work_to_do
        
    
class MigrationSourceHTA( MigrationSource ):
    
    def __init__( self, controller, path, location_context: ClientLocation.LocationContext, desired_hash_type, hashes, tag_filter ):
        
        name = os.path.basename( path )
        
        MigrationSource.__init__( self, controller, name )
        
        self._path = path
        self._location_context = location_context
        self._desired_hash_type = desired_hash_type
        self._hashes = hashes
        self._tag_filter = tag_filter
        
        self._hta = None
        self._source_hash_type = None
        self._iterator = None
        
    
    def _ConvertHashes( self, source_hash_type, desired_hash_type, data ):
        
        if source_hash_type != desired_hash_type:
            
            fixed_data = []
            
            for ( hash, tags ) in data:
                
                source_to_desired = self._controller.Read( 'file_hashes', ( hash, ), source_hash_type, desired_hash_type )
                
                if len( source_to_desired ) == 0:
                    
                    continue
                    
                
                desired_hash = list( source_to_desired.values() )[0]
                
                fixed_data.append( ( desired_hash, tags ) )
                
            
            data = fixed_data
            
        
        return data
        
    
    def _FilterSHA256Hashes( self, data ):
        
        if self._hashes is not None:
            
            data = [ ( hash, tags ) for ( hash, tags ) in data if hash in self._hashes ]
            
        
        if not self._location_context.IsAllKnownFiles():
            
            filtered_data = []
            
            all_hashes = [ hash for ( hash, tags ) in data ]
            
            hashes_to_media_results = { media_result.GetHash() : media_result for media_result in self._controller.Read( 'media_results', all_hashes ) }
            
            for ( hash, tags ) in data:
                
                if hash in hashes_to_media_results:
                    
                    media_result = hashes_to_media_results[ hash ]
                    
                    if not media_result.GetLocationsManager().IsInLocationContext( self._location_context ):
                        
                        continue
                        
                    
                    filtered_data.append( ( hash, tags ) )
                    
                
            
            data = filtered_data
            
        
        return data
        
    
    def _SHA256FilteringNeeded( self ):
        
        return self._hashes is not None or not self._location_context.IsAllKnownFiles()
        
    
    def CleanUp( self ):
        
        self._hta.CommitBigJob()
        
        self._hta.Close()
        
        self._hta = None
        self._iterator = None
        
    
    def GetSomeData( self ):
        
        data = HydrusLists.PullNFromIterator( self._iterator, 256 )
        
        if len( data ) == 0:
            
            self._work_to_do = False
            
            return data
            
        
        if not self._tag_filter.AllowsEverything():
            
            filtered_data = []
            
            for ( hash, tags ) in data:
                
                tags = self._tag_filter.Filter( tags )
                
                if len( tags ) > 0:
                    
                    filtered_data.append( ( hash, tags ) )
                    
                
            
            data = filtered_data
            
        
        if self._SHA256FilteringNeeded():
            
            if self._source_hash_type == 'sha256':
                
                data = self._FilterSHA256Hashes( data )
                
                data = self._ConvertHashes( self._source_hash_type, self._desired_hash_type, data )
                
            elif self._desired_hash_type == 'sha256':
                
                data = self._ConvertHashes( self._source_hash_type, self._desired_hash_type, data )
                
                data = self._FilterSHA256Hashes( data )
                
            else:
                
                data = self._ConvertHashes( self._source_hash_type, 'sha256', data )
                
                data = self._FilterSHA256Hashes( data )
                
                data = self._ConvertHashes( 'sha256', self._desired_hash_type, data )
                
            
        else:
            
            data = self._ConvertHashes( self._source_hash_type, self._desired_hash_type, data )
            
        
        return data
        
    
    def Prepare( self ):
        
        self._hta = HydrusTagArchive.HydrusTagArchive( self._path )
        
        self._hta.BeginBigJob()
        
        self._source_hash_type = HydrusTagArchive.hash_type_to_str_lookup[ self._hta.GetHashType() ]
        
        self._iterator = self._hta.IterateMappings()
        
    
class MigrationSourceHTPA( MigrationSource ):
    
    def __init__( self, controller, path, left_tag_filter, right_tag_filter ):
        
        name = os.path.basename( path )
        
        MigrationSource.__init__( self, controller, name )
        
        self._path = path
        self._left_tag_filter = left_tag_filter
        self._right_tag_filter = right_tag_filter
        
        self._htpa = None
        self._iterator = None
        
    
    def CleanUp( self ):
        
        self._htpa.CommitBigJob()
        
        self._htpa.Close()
        
        self._htpa = None
        self._iterator = None
        
    
    def GetSomeData( self ):
        
        data = HydrusLists.PullNFromIterator( self._iterator, 256 )
        
        if len( data ) == 0:
            
            self._work_to_do = False
            
            return data
            
        
        if not ( self._left_tag_filter.AllowsEverything() and self._right_tag_filter.AllowsEverything() ):
            
            data = [ ( left_tag, right_tag ) for ( left_tag, right_tag ) in data if self._left_tag_filter.TagOK( left_tag ) and self._right_tag_filter.TagOK( right_tag ) ]
            
        
        return data
        
    
    def Prepare( self ):
        
        self._htpa = HydrusTagArchive.HydrusTagPairArchive( self._path )
        
        self._htpa.BeginBigJob()
        
        self._iterator = self._htpa.IteratePairs()
        
    
class MigrationSourceList( MigrationSource ):
    
    def __init__( self, controller, data ):
        
        name = 'simple list source'
        
        MigrationSource.__init__( self, controller, name )
        
        self._data = data
        self._iterator = None
        
    
    def GetSomeData( self ):
        
        some_data = HydrusLists.PullNFromIterator( self._iterator, 5 )
        
        if len( some_data ) == 0:
            
            self._work_to_do = False
            
        
        return some_data
        
    
    def Prepare( self ):
        
        self._iterator = iter( self._data )
        
    
class MigrationSourceTagServiceMappings( MigrationSource ):
    
    def __init__( self, controller, tag_service_key, location_context, desired_hash_type, hashes, tag_filter, content_statuses ):
        
        name = controller.services_manager.GetName( tag_service_key )
        
        MigrationSource.__init__( self, controller, name )
        
        self._location_context = location_context
        self._tag_service_key = tag_service_key
        self._desired_hash_type = desired_hash_type
        self._hashes = hashes
        self._tag_filter = tag_filter
        self._content_statuses = content_statuses
        
        self._database_temp_job_name = 'migrate_{}'.format( os.urandom( 16 ).hex() )
        
    
    def CleanUp( self ):
        
        self._controller.WriteSynchronous( 'migration_clear_job', self._database_temp_job_name )
        
    
    def GetSomeData( self ):
        
        data = self._controller.Read( 'migration_get_mappings', self._database_temp_job_name, self._location_context, self._tag_service_key, self._desired_hash_type, self._tag_filter, self._content_statuses )
        
        if len( data ) == 0:
            
            self._work_to_do = False
            
        
        return data
        
    
    def Prepare( self ):
        
        # later can spread this out into bunch of small jobs, a start and a continue, based on tag filter subsets
        
        self._controller.WriteSynchronous( 'migration_start_mappings_job', self._database_temp_job_name, self._location_context, self._tag_service_key, self._hashes, self._content_statuses )
        
    
class MigrationSourceTagServicePairs( MigrationSource ):
    
    def __init__( self, controller, tag_service_key, content_type, left_tag_filter, right_tag_filter, content_statuses ):
        
        name = controller.services_manager.GetName( tag_service_key )
        
        MigrationSource.__init__( self, controller, name )
        
        self._tag_service_key = tag_service_key
        self._content_type = content_type
        self._left_tag_filter = left_tag_filter
        self._right_tag_filter = right_tag_filter
        self._content_statuses = content_statuses
        
        self._database_temp_job_name = 'migrate_{}'.format( os.urandom( 16 ).hex() )
        
    
    def CleanUp( self ):
        
        self._controller.WriteSynchronous( 'migration_clear_job', self._database_temp_job_name )
        
    
    def GetSomeData( self ):
        
        data = self._controller.Read( 'migration_get_pairs', self._database_temp_job_name, self._left_tag_filter, self._right_tag_filter )
        
        if len( data ) == 0:
            
            self._work_to_do = False
            
        
        return data
        
    
    def Prepare( self ):
        
        self._controller.WriteSynchronous( 'migration_start_pairs_job', self._database_temp_job_name, self._tag_service_key, self._content_type, self._content_statuses )
        
    
