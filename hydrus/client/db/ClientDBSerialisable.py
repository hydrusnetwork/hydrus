import json
import os
import sqlite3
import time
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusDB
from hydrus.core import HydrusDBModule
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusSerialisable

from hydrus.client import ClientConstants as CC
from hydrus.client.db import ClientDBServices

YAML_DUMP_ID_SINGLE = 0
YAML_DUMP_ID_REMOTE_BOORU = 1
YAML_DUMP_ID_FAVOURITE_CUSTOM_FILTER_ACTIONS = 2
YAML_DUMP_ID_GUI_SESSION = 3
YAML_DUMP_ID_IMAGEBOARD = 4
YAML_DUMP_ID_IMPORT_FOLDER = 5
YAML_DUMP_ID_EXPORT_FOLDER = 6
YAML_DUMP_ID_SUBSCRIPTION = 7
YAML_DUMP_ID_LOCAL_BOORU = 8

def DealWithBrokenJSONDump( db_dir, dump, dump_descriptor ):
    
    timestamp_string = time.strftime( '%Y-%m-%d %H-%M-%S' )
    hex_chars = os.urandom( 4 ).hex()
    
    filename = '({}) at {} {}.json'.format( dump_descriptor, timestamp_string, hex_chars )
    
    path = os.path.join( db_dir, filename )
    
    with open( path, 'wb' ) as f:
        
        if isinstance( dump, str ):
            
            dump = bytes( dump, 'utf-8', errors = 'replace' )
            
        
        f.write( dump )
        
    
    message = 'A serialised object failed to load! Its description is "{}".'.format( dump_descriptor )
    message += os.linesep * 2
    message += 'This error could be due to several factors, but is most likely a hard drive fault (perhaps your computer recently had a bad power cut?).'
    message += os.linesep * 2
    message += 'The database has attempted to delete the broken object, errors have been written to the log, and the object\'s dump written to {}. Depending on the object, your client may no longer be able to boot, or it may have lost something like a session or a subscription.'.format( path )
    message += os.linesep * 2
    message += 'Please review the \'help my db is broke.txt\' file in your install_dir/db directory as background reading, and if the situation or fix here is not obvious, please contact hydrus dev.'
    
    HydrusData.ShowText( message )
    
    raise HydrusExceptions.SerialisationException( message )
    
def GenerateBigSQLiteDumpBuffer( dump ):
    
    try:
        
        dump_bytes = bytes( dump, 'utf-8' )
        
    except Exception as e:
        
        HydrusData.PrintException( e )
        
        raise Exception( 'While trying to save data to the database, it could not be decoded from UTF-8 to bytes! This could indicate an encoding error, such as Shift JIS sneaking into a downloader page! Please let hydrus dev know about this! Full error was written to the log!' )
        
    
    if len( dump_bytes ) >= 1000000000: # 1 billion, not 1GB https://sqlite.org/limits.html
        
        raise Exception( 'A data object could not save to the database because it was bigger than a buffer limit of 1,000,000,000 bytes! If your session has millions of files/URLs, close some pages NOW or you will lose data! Otherwise, please report this to hydrus dev!' )
        
    
    try:
        
        dump_buffer = sqlite3.Binary( dump_bytes )
        
    except Exception as e:
        
        HydrusData.PrintException( e )
        
        raise Exception( 'While trying to save data to the database, it would not form into a buffer! Please let hydrus dev know about this! Full error was written to the log!' )
        
    
    return dump_buffer
    
class ClientDBSerialisable( HydrusDBModule.HydrusDBModule ):
    
    def __init__( self, cursor: sqlite3.Cursor, db_dir, cursor_transaction_wrapper: HydrusDB.DBCursorTransactionWrapper, modules_services: ClientDBServices.ClientDBMasterServices ):
        
        HydrusDBModule.HydrusDBModule.__init__( self, 'client serialisable', cursor )
        
        self._db_dir = db_dir
        self._cursor_transaction_wrapper = cursor_transaction_wrapper
        self.modules_services = modules_services
        
    
    def _GetInitialIndexGenerationTuples( self ):
        
        index_generation_tuples = []
        
        return index_generation_tuples
        
    
    def CreateInitialTables( self ):
        
        self._c.execute( 'CREATE TABLE json_dict ( name TEXT PRIMARY KEY, dump BLOB_BYTES );' )
        self._c.execute( 'CREATE TABLE json_dumps ( dump_type INTEGER PRIMARY KEY, version INTEGER, dump BLOB_BYTES );' )
        self._c.execute( 'CREATE TABLE json_dumps_named ( dump_type INTEGER, dump_name TEXT, version INTEGER, timestamp INTEGER, dump BLOB_BYTES, PRIMARY KEY ( dump_type, dump_name, timestamp ) );' )
        
        self._c.execute( 'CREATE TABLE yaml_dumps ( dump_type INTEGER, dump_name TEXT, dump TEXT_YAML, PRIMARY KEY ( dump_type, dump_name ) );' )
        
    
    def DeleteJSONDump( self, dump_type ):
        
        self._c.execute( 'DELETE FROM json_dumps WHERE dump_type = ?;', ( dump_type, ) )
        
    
    def DeleteJSONDumpNamed( self, dump_type, dump_name = None, timestamp = None ):
        
        if dump_name is None:
            
            self._c.execute( 'DELETE FROM json_dumps_named WHERE dump_type = ?;', ( dump_type, ) )
            
        elif timestamp is None:
            
            self._c.execute( 'DELETE FROM json_dumps_named WHERE dump_type = ? AND dump_name = ?;', ( dump_type, dump_name ) )
            
        else:
            
            self._c.execute( 'DELETE FROM json_dumps_named WHERE dump_type = ? AND dump_name = ? AND timestamp = ?;', ( dump_type, dump_name, timestamp ) )
            
        
    
    def DeleteYAMLDump( self, dump_type, dump_name = None ):
        
        if dump_name is None:
            
            self._c.execute( 'DELETE FROM yaml_dumps WHERE dump_type = ?;', ( dump_type, ) )
            
        else:
            
            if dump_type == YAML_DUMP_ID_LOCAL_BOORU: dump_name = dump_name.hex()
            
            self._c.execute( 'DELETE FROM yaml_dumps WHERE dump_type = ? AND dump_name = ?;', ( dump_type, dump_name ) )
            
        
        if dump_type == YAML_DUMP_ID_LOCAL_BOORU:
            
            service_id = self.modules_services.GetServiceId( CC.LOCAL_BOORU_SERVICE_KEY )
            
            self._c.execute( 'DELETE FROM service_info WHERE service_id = ? AND info_type = ?;', ( service_id, HC.SERVICE_INFO_NUM_SHARES ) )
            
            HG.client_controller.pub( 'refresh_local_booru_shares' )
            
        
    
    def GetExpectedTableNames( self ) -> typing.Collection[ str ]:
        
        expected_table_names = [
            'json_dict',
            'json_dumps',
            'json_dumps_named',
            'yaml_dumps'
        ]
        
        return expected_table_names
        
    
    def GetJSONDump( self, dump_type ):
        
        result = self._c.execute( 'SELECT version, dump FROM json_dumps WHERE dump_type = ?;', ( dump_type, ) ).fetchone()
        
        if result is None:
            
            return result
            
        else:
            
            ( version, dump ) = result
            
            try:
                
                if isinstance( dump, bytes ):
                    
                    dump = str( dump, 'utf-8' )
                    
                
                serialisable_info = json.loads( dump )
                
            except:
                
                self._c.execute( 'DELETE FROM json_dumps WHERE dump_type = ?;', ( dump_type, ) )
                
                self._cursor_transaction_wrapper.CommitAndBegin()
                
                DealWithBrokenJSONDump( self._db_dir, dump, 'dump_type {}'.format( dump_type ) )
                
            
            obj = HydrusSerialisable.CreateFromSerialisableTuple( ( dump_type, version, serialisable_info ) )
            
            if dump_type == HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_SESSION_MANAGER:
                
                session_containers = self.GetJSONDumpNamed( HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_SESSION_MANAGER_SESSION_CONTAINER )
                
                obj.SetSessionContainers( session_containers )
                
            elif dump_type == HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_BANDWIDTH_MANAGER:
                
                tracker_containers = self.GetJSONDumpNamed( HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_BANDWIDTH_MANAGER_TRACKER_CONTAINER )
                
                obj.SetTrackerContainers( tracker_containers )
                
            
            return obj
            
        
    
    def GetJSONDumpNamed( self, dump_type, dump_name = None, timestamp = None ):
        
        if dump_name is None:
            
            results = self._c.execute( 'SELECT dump_name, version, dump, timestamp FROM json_dumps_named WHERE dump_type = ?;', ( dump_type, ) ).fetchall()
            
            objs = []
            
            for ( dump_name, version, dump, object_timestamp ) in results:
                
                try:
                    
                    if isinstance( dump, bytes ):
                        
                        dump = str( dump, 'utf-8' )
                        
                    
                    serialisable_info = json.loads( dump )
                    
                    objs.append( HydrusSerialisable.CreateFromSerialisableTuple( ( dump_type, dump_name, version, serialisable_info ) ) )
                    
                except:
                    
                    self._c.execute( 'DELETE FROM json_dumps_named WHERE dump_type = ? AND dump_name = ? AND timestamp = ?;', ( dump_type, dump_name, object_timestamp ) )
                    
                    self._cursor_transaction_wrapper.CommitAndBegin()
                    
                    DealWithBrokenJSONDump( self._db_dir, dump, 'dump_type {} dump_name {} timestamp {}'.format( dump_type, dump_name[:10], timestamp ) )
                    
                
            
            return objs
            
        else:
            
            if timestamp is None:
                
                result = self._c.execute( 'SELECT version, dump, timestamp FROM json_dumps_named WHERE dump_type = ? AND dump_name = ? ORDER BY timestamp DESC;', ( dump_type, dump_name ) ).fetchone()
                
            else:
                
                result = self._c.execute( 'SELECT version, dump, timestamp FROM json_dumps_named WHERE dump_type = ? AND dump_name = ? AND timestamp = ?;', ( dump_type, dump_name, timestamp ) ).fetchone()
                
            
            if result is None:
                
                raise HydrusExceptions.DataMissing( 'Could not find the object of type "{}" and name "{}" and timestamp "{}".'.format( dump_type, dump_name, str( timestamp ) ) )
                
            
            ( version, dump, object_timestamp ) = result
            
            try:
                
                if isinstance( dump, bytes ):
                    
                    dump = str( dump, 'utf-8' )
                    
                
                serialisable_info = json.loads( dump )
                
            except:
                
                self._c.execute( 'DELETE FROM json_dumps_named WHERE dump_type = ? AND dump_name = ? AND timestamp = ?;', ( dump_type, dump_name, object_timestamp ) )
                
                self._cursor_transaction_wrapper.CommitAndBegin()
                
                DealWithBrokenJSONDump( self._db_dir, dump, 'dump_type {} dump_name {} timestamp {}'.format( dump_type, dump_name[:10], object_timestamp ) )
                
            
            return HydrusSerialisable.CreateFromSerialisableTuple( ( dump_type, dump_name, version, serialisable_info ) )
            
        
    
    def GetJSONDumpNames( self, dump_type ):
        
        names = [ name for ( name, ) in self._c.execute( 'SELECT DISTINCT dump_name FROM json_dumps_named WHERE dump_type = ?;', ( dump_type, ) ) ]
        
        return names
        
    
    def GetJSONDumpNamesToBackupTimestamps( self, dump_type ):
        
        names_to_backup_timestamps = HydrusData.BuildKeyToListDict( self._c.execute( 'SELECT dump_name, timestamp FROM json_dumps_named WHERE dump_type = ? ORDER BY timestamp ASC;', ( dump_type, ) ) )
        
        for ( name, timestamp_list ) in list( names_to_backup_timestamps.items() ):
            
            timestamp_list.pop( -1 ) # remove the non backup timestamp
            
            if len( timestamp_list ) == 0:
                
                del names_to_backup_timestamps[ name ]
                
            
        
        return names_to_backup_timestamps
        
    
    def GetJSONSimple( self, name ):
        
        result = self._c.execute( 'SELECT dump FROM json_dict WHERE name = ?;', ( name, ) ).fetchone()
        
        if result is None:
            
            return None
            
        
        ( dump, ) = result
        
        if isinstance( dump, bytes ):
            
            dump = str( dump, 'utf-8' )
            
        
        value = json.loads( dump )
        
        return value
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> typing.List[ typing.Tuple[ str, str ] ]:
        
        return []
        
    
    def GetYAMLDump( self, dump_type, dump_name = None ):
        
        if dump_name is None:
            
            result = { dump_name : data for ( dump_name, data ) in self._c.execute( 'SELECT dump_name, dump FROM yaml_dumps WHERE dump_type = ?;', ( dump_type, ) ) }
            
            if dump_type == YAML_DUMP_ID_LOCAL_BOORU:
                
                result = { bytes.fromhex( dump_name ) : data for ( dump_name, data ) in list(result.items()) }
                
            
        else:
            
            if dump_type == YAML_DUMP_ID_LOCAL_BOORU: dump_name = dump_name.hex()
            
            result = self._c.execute( 'SELECT dump FROM yaml_dumps WHERE dump_type = ? AND dump_name = ?;', ( dump_type, dump_name ) ).fetchone()
            
            if result is None:
                
                if result is None:
                    
                    raise HydrusExceptions.DataMissing( dump_name + ' was not found!' )
                    
                
            else:
                
                ( result, ) = result
                
            
        
        return result
        
    
    def GetYAMLDumpNames( self, dump_type ):
        
        names = [ name for ( name, ) in self._c.execute( 'SELECT dump_name FROM yaml_dumps WHERE dump_type = ?;', ( dump_type, ) ) ]
        
        if dump_type == YAML_DUMP_ID_LOCAL_BOORU:
            
            names = [ bytes.fromhex( name ) for name in names ]
            
        
        return names
        
    
    def OverwriteJSONDumps( self, dump_types, objs ):
        
        for dump_type in dump_types:
            
            self.DeleteJSONDumpNamed( dump_type )
            
        
        for obj in objs:
            
            self.SetJSONDump( obj )
            
        
    
    def SetJSONDump( self, obj ):
        
        if isinstance( obj, HydrusSerialisable.SerialisableBaseNamed ):
            
            ( dump_type, dump_name, version, serialisable_info ) = obj.GetSerialisableTuple()
            
            try:
                
                dump = json.dumps( serialisable_info )
                
            except Exception as e:
                
                HydrusData.ShowException( e )
                HydrusData.Print( obj )
                HydrusData.Print( serialisable_info )
                
                raise Exception( 'Trying to json dump the object ' + str( obj ) + ' with name ' + dump_name + ' caused an error. Its serialisable info has been dumped to the log.' )
                
            
            store_backups = False
            
            if dump_type == HydrusSerialisable.SERIALISABLE_TYPE_GUI_SESSION:
                
                store_backups = True
                backup_depth = HG.client_controller.new_options.GetInteger( 'number_of_gui_session_backups' )
                
            
            object_timestamp = HydrusData.GetNow()
            
            if store_backups:
                
                existing_timestamps = sorted( self._STI( self._c.execute( 'SELECT timestamp FROM json_dumps_named WHERE dump_type = ? AND dump_name = ?;', ( dump_type, dump_name ) ) ) )
                
                if len( existing_timestamps ) > 0:
                    
                    # the user has changed their system clock, so let's make sure the new timestamp is larger at least
                    
                    largest_existing_timestamp = max( existing_timestamps )
                    
                    if largest_existing_timestamp > object_timestamp:
                        
                        object_timestamp = largest_existing_timestamp + 1
                        
                    
                
                deletee_timestamps = existing_timestamps[ : - backup_depth ] # keep highest n values
                
                deletee_timestamps.append( object_timestamp ) # if save gets spammed twice in one second, we'll overwrite
                
                self._c.executemany( 'DELETE FROM json_dumps_named WHERE dump_type = ? AND dump_name = ? AND timestamp = ?;', [ ( dump_type, dump_name, timestamp ) for timestamp in deletee_timestamps ] )
                
            else:
                
                self._c.execute( 'DELETE FROM json_dumps_named WHERE dump_type = ? AND dump_name = ?;', ( dump_type, dump_name ) )
                
            
            dump_buffer = GenerateBigSQLiteDumpBuffer( dump )
            
            try:
                
                self._c.execute( 'INSERT INTO json_dumps_named ( dump_type, dump_name, version, timestamp, dump ) VALUES ( ?, ?, ?, ?, ? );', ( dump_type, dump_name, version, object_timestamp, dump_buffer ) )
                
            except:
                
                if dump_type == HydrusSerialisable.SERIALISABLE_TYPE_GUI_SESSION:
                    
                    HydrusData.ShowText( 'A gui session could not be saved! This could be because it is too large. If your session is big, please try to trim it down now, or you will lose changes!' )
                    
                else:
                    
                    HydrusData.DebugPrint( dump )
                    HydrusData.ShowText( 'Had a problem saving a JSON object. The dump has been printed to the log.' )
                    
                
                try:
                    
                    HydrusData.Print( 'Dump was {}!'.format( HydrusData.ToHumanBytes( len( dump_buffer ) ) ) )
                    
                except:
                    
                    pass
                    
                
                raise
                
            
        else:
            
            ( dump_type, version, serialisable_info ) = obj.GetSerialisableTuple()
            
            if dump_type == HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_SESSION_MANAGER:
                
                deletee_session_names = obj.GetDeleteeSessionNames()
                dirty_session_containers = obj.GetDirtySessionContainers()
                
                if len( deletee_session_names ) > 0:
                    
                    for deletee_session_name in deletee_session_names:
                        
                        self.DeleteJSONDumpNamed( HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_SESSION_MANAGER_SESSION_CONTAINER, dump_name = deletee_session_name )
                        
                    
                
                if len( dirty_session_containers ) > 0:
                    
                    for dirty_session_container in dirty_session_containers:
                        
                        self.SetJSONDump( dirty_session_container )
                        
                    
                
                if not obj.IsDirty():
                    
                    return
                    
                
            elif dump_type == HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_BANDWIDTH_MANAGER:
                
                deletee_tracker_names = obj.GetDeleteeTrackerNames()
                dirty_tracker_containers = obj.GetDirtyTrackerContainers()
                
                if len( deletee_tracker_names ) > 0:
                    
                    for deletee_tracker_name in deletee_tracker_names:
                        
                        self.DeleteJSONDumpNamed( HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_BANDWIDTH_MANAGER_TRACKER_CONTAINER, dump_name = deletee_tracker_name )
                        
                    
                
                if len( dirty_tracker_containers ) > 0:
                    
                    for dirty_tracker_container in dirty_tracker_containers:
                        
                        self.SetJSONDump( dirty_tracker_container )
                        
                    
                
                if not obj.IsDirty():
                    
                    return
                    
                
            
            try:
                
                dump = json.dumps( serialisable_info )
                
            except Exception as e:
                
                HydrusData.ShowException( e )
                HydrusData.Print( obj )
                HydrusData.Print( serialisable_info )
                
                raise Exception( 'Trying to json dump the object ' + str( obj ) + ' caused an error. Its serialisable info has been dumped to the log.' )
                
            
            self._c.execute( 'DELETE FROM json_dumps WHERE dump_type = ?;', ( dump_type, ) )
            
            dump_buffer = GenerateBigSQLiteDumpBuffer( dump )
            
            try:
                
                self._c.execute( 'INSERT INTO json_dumps ( dump_type, version, dump ) VALUES ( ?, ?, ? );', ( dump_type, version, dump_buffer ) )
                
            except:
                
                HydrusData.DebugPrint( dump )
                HydrusData.ShowText( 'Had a problem saving a JSON object. The dump has been printed to the log.' )
                
                raise
                
            
        
    
    def SetJSONComplex( self,
        overwrite_types_and_objs: typing.Optional[ typing.Tuple[ typing.Iterable[ int ], typing.Iterable[ HydrusSerialisable.SerialisableBase ] ] ] = None,
        set_objs: typing.Optional[ typing.List[ HydrusSerialisable.SerialisableBase ] ] = None,
        deletee_types_to_names: typing.Optional[ typing.Dict[ int, typing.Iterable[ str ] ] ] = None
    ):
        
        if overwrite_types_and_objs is not None:
            
            ( dump_types, objs ) = overwrite_types_and_objs
            
            self.OverwriteJSONDumps( dump_types, objs )
            
        
        if set_objs is not None:
            
            for obj in set_objs:
                
                self.SetJSONDump( obj )
                
            
        
        if deletee_types_to_names is not None:
            
            for ( dump_type, names ) in deletee_types_to_names.items():
                
                for name in names:
                    
                    self.DeleteJSONDumpNamed( dump_type, dump_name = name )
                    
                
            
        
    
    def SetJSONSimple( self, name, value ):
        
        if value is None:
            
            self._c.execute( 'DELETE FROM json_dict WHERE name = ?;', ( name, ) )
            
        else:
            
            dump = json.dumps( value )
            
            dump_buffer = GenerateBigSQLiteDumpBuffer( dump )
            
            try:
                
                self._c.execute( 'REPLACE INTO json_dict ( name, dump ) VALUES ( ?, ? );', ( name, dump_buffer ) )
                
            except:
                
                HydrusData.DebugPrint( dump )
                HydrusData.ShowText( 'Had a problem saving a JSON object. The dump has been printed to the log.' )
                
                raise
                
            
        
    
    def SetYAMLDump( self, dump_type, dump_name, data ):
        
        if dump_type == YAML_DUMP_ID_LOCAL_BOORU:
            
            dump_name = dump_name.hex()
            
        
        self._c.execute( 'DELETE FROM yaml_dumps WHERE dump_type = ? AND dump_name = ?;', ( dump_type, dump_name ) )
        
        try:
            
            self._c.execute( 'INSERT INTO yaml_dumps ( dump_type, dump_name, dump ) VALUES ( ?, ?, ? );', ( dump_type, dump_name, data ) )
            
        except:
            
            HydrusData.Print( ( dump_type, dump_name, data ) )
            
            raise
            
        
        if dump_type == YAML_DUMP_ID_LOCAL_BOORU:
            
            service_id = self.modules_services.GetServiceId( CC.LOCAL_BOORU_SERVICE_KEY )
            
            self._c.execute( 'DELETE FROM service_info WHERE service_id = ? AND info_type = ?;', ( service_id, HC.SERVICE_INFO_NUM_SHARES ) )
            
            HG.client_controller.pub( 'refresh_local_booru_shares' )
            
        
    
