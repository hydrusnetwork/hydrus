import os
import sqlite3

from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusPaths
from hydrus.core.files import HydrusFilesPhysicalStorage

from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientThreading
from hydrus.client.db import ClientDBModule
from hydrus.client.files import ClientFilesPhysical

class ClientDBFilesPhysicalStorage( ClientDBModule.ClientDBModule ):
    
    def __init__(
        self,
        cursor: sqlite3.Cursor,
        db_dir: str
    ):
        
        super().__init__( 'client files physical storage', cursor )
        
        self._db_dir = db_dir
        
    
    def _GetCurrentGranularity( self ) -> int:
        
        result = self._Execute( 'SELECT granularity FROM current_storage_granularity;' ).fetchone()
        
        if result is None:
            
            raise Exception( 'This database has no client file storage granularity value! This is a serious error that probably needs hydev to figure out!' )
            
        
        ( granularity, ) = result
        
        return granularity
        
    
    def _GetInitialTableGenerationDict( self ) -> dict:
        
        return {
            'main.current_client_files_locations' : ( 'CREATE TABLE IF NOT EXISTS {} ( location_id INTEGER PRIMARY KEY, location TEXT UNIQUE );', 660 ),
            'main.client_files_subfolders' : ( 'CREATE TABLE IF NOT EXISTS {} ( prefix TEXT, location_id INTEGER, PRIMARY KEY ( prefix, location_id ) );', 660 ),
            'main.ideal_client_files_locations' : ( 'CREATE TABLE IF NOT EXISTS {} ( location_id INTEGER PRIMARY KEY, weight INTEGER, max_num_bytes INTEGER );', 660 ),
            'main.ideal_thumbnail_override_location' : ( 'CREATE TABLE IF NOT EXISTS {} ( location_id INTEGER );', 660 ),
            'main.current_storage_granularity' : ( 'CREATE TABLE IF NOT EXISTS {} ( granularity INTEGER );', 660 ),
        }
        
    
    def GetClientFilesSubfolders( self ):
        
        ( media_base_locations, ideal_thumbnail_override_base_location ) = self.GetIdealClientFilesLocations()
        
        paths_to_base_locations = { base_location.path : base_location for base_location in media_base_locations }
        
        subfolders = set()
        
        location_ids_to_locations = {}
        
        current_granularity = self._GetCurrentGranularity()
        
        for ( prefix, location_id ) in self._Execute( 'SELECT prefix, location_id FROM client_files_subfolders;' ).fetchall():
            
            if len( prefix ) != current_granularity + 1: # len( 'f34' ) = 2 + 1
                
                raise Exception( f'Problem loading your client file storage subfolders! This client is supposed to have storage granularity of {current_granularity}, but the loaded prefix "{prefix}" has a different length! This is a serious error that probably needs hydev to figure out!' )
                
            
            if location_id not in location_ids_to_locations:
                
                location = self.GetLocation( location_id )
                
                location_ids_to_locations[ location_id ] = location
                
            
            location = location_ids_to_locations[ location_id ]
            
            if prefix.startswith( 't' ) and ideal_thumbnail_override_base_location is not None and location == ideal_thumbnail_override_base_location.path:
                
                base_location = ideal_thumbnail_override_base_location
                
            else:
                
                if location not in paths_to_base_locations:
                    
                    paths_to_base_locations[ location ] = ClientFilesPhysical.FilesStorageBaseLocation( location, 0 )
                    
                
                base_location = paths_to_base_locations[ location ]
                
            
            subfolders.add( ClientFilesPhysical.FilesStorageSubfolder( prefix, base_location ) )
            
        
        all_prefixes = { subfolder.prefix for subfolder in subfolders }
        
        missing_prefixes_f = HydrusFilesPhysicalStorage.GetMissingPrefixes( 'f', all_prefixes, current_granularity )
        missing_prefixes_t = HydrusFilesPhysicalStorage.GetMissingPrefixes( 't', all_prefixes, current_granularity )
        
        if len( missing_prefixes_f ) > 0 or len( missing_prefixes_t ) > 0:
            
            message = 'When fetching the directories where your files are stored, the database discovered that some entries were missing! If you did not fiddle with the database yourself, this probably happened due to database corruption.'
            message += '\n' * 2
            message += 'Default values will now be inserted. If you have previously migrated your files or thumbnails, and assuming this is occuring on boot, you will next be presented with a dialog to remap them to the correct location.'
            message += '\n' * 2
            message += 'If this is not happening on client boot, you should kill the hydrus process right now, as a serious hard drive fault has likely recently occurred.'
            
            self._DisplayCatastrophicError( message )
            
            client_files_default = os.path.join( self._db_dir, 'client_files' )
            
            HydrusPaths.MakeSureDirectoryExists( client_files_default )
            
            location_id = self.GetLocationId( client_files_default )
            
            for missing_prefix in missing_prefixes_f:
                
                self._Execute( 'INSERT OR IGNORE INTO client_files_subfolders ( prefix, location_id ) VALUES ( ?, ? );', ( missing_prefix, location_id ) )
                
            
            for missing_prefix in missing_prefixes_t:
                
                self._Execute( 'INSERT OR IGNORE INTO client_files_subfolders ( prefix, location_id ) VALUES ( ?, ? );', ( missing_prefix, location_id ) )
                
            
            return self.GetClientFilesSubfolders()
            
        
        return ( current_granularity, subfolders )
        
    
    def GetIdealClientFilesLocations( self ):
        
        media_base_locations = set()
        
        for ( location_id, ideal_weight, max_num_bytes ) in self._Execute( 'SELECT location_id, weight, max_num_bytes FROM ideal_client_files_locations;' ).fetchall():
            
            location = self.GetLocation( location_id )
            
            media_base_locations.add( ClientFilesPhysical.FilesStorageBaseLocation( location, ideal_weight, max_num_bytes = max_num_bytes ) )
            
        
        result = self._Execute( 'SELECT location_id FROM ideal_thumbnail_override_location;' ).fetchone()
        
        if result is None:
            
            thumbnail_override_base_location = None
            
        else:
            
            ( location_id, ) = result
            
            location = self.GetLocation( location_id )
            
            thumbnail_override_base_location = ClientFilesPhysical.FilesStorageBaseLocation( location, 1 )
            
        
        return ( media_base_locations, thumbnail_override_base_location )
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> list[ tuple[ str, str ] ]:
        
        tables_and_columns = []
        
        return tables_and_columns
        
    
    def GetLocation( self, location_id: int ) -> str:
        
        # TODO: rewrite this guy to return a pathlib Path and propagate the whole gubbins out from there, bottom to top
        
        result = self._Execute( 'SELECT location FROM current_client_files_locations WHERE location_id = ?;', ( location_id, ) ).fetchone()
        
        if result is None:
            
            raise HydrusExceptions.DataMissing( 'Location lookup error in database! This is a serious error that probably needs hydev to figure out!' )
            
        
        ( portable_location, ) = result
        
        absolute_location = HydrusPaths.ConvertPortablePathToAbsPath( portable_location )
        
        return absolute_location
        
    
    def GetLocationId( self, absolute_location: str ):
        
        # TODO: we may need to have some clever alternate call or bool here that says 'hey I need you to check every possible conjugation of this location', which will read all locations and absolute normalise them somehow
        # this would be just to catch the wrong slashes coming in (C:\ vs C:/) and so on, although we don't want this to be normal behaviour perhaps, certainly at least if it can write back any 'corrections' 
        
        portable_location = HydrusPaths.ConvertAbsPathToPortablePath( absolute_location )
        
        result = self._Execute( 'SELECT location_id FROM current_client_files_locations WHERE location = ?;', ( portable_location, ) ).fetchone()
        
        if result is None:
            
            self._Execute( 'INSERT INTO current_client_files_locations ( location ) VALUES ( ? );', ( portable_location, ) )
            
            location_id = self._GetLastRowId()
            
        else:
            
            ( location_id, ) = result
            
        
        return location_id
        
    
    def Granularise2To3( self, job_status: ClientThreading.JobStatus ):
        
        location_ids = self._STL( self._Execute( 'SELECT DISTINCT location_id FROM client_files_subfolders;' ) )
        
        locations = sorted( [ self.GetLocation( location_id ) for location_id in location_ids ] )
        
        try:
            
            granularise_result = ClientFilesPhysical.RegranulariseBaseLocation( locations, [ 'f', 't' ], 2, 3, job_status )
            
        except HydrusExceptions.CancelledException:
            
            message = 'You just cancelled the regranularisation process! I will now attempt to undo it. The status window will move to the bottom-right of the main gui window. Just wait it out please.'
            
            CG.client_controller.BlockingSafeShowMessage( message )
            
            job_status = ClientThreading.JobStatus( pausable = True )
            
            job_status.SetStatusTitle( 'Undoing granularisation.' )
            
            CG.client_controller.pub( 'message', job_status )
            
            ClientFilesPhysical.RegranulariseBaseLocation( locations, [ 'f', 't' ], 3, 2, job_status )
            
            raise
            
        except Exception as e:
            
            HydrusData.PrintException( e, do_wait = False )
            
            message = 'Granularisation failed!! I am paused now, but when this dialog is closed, I will attempt to undo and return to granularisation 2. If you do not want to attempt to repair the damage, kill the hydrus process now. The status window will move to the bottom-right of the main gui window. Just wait it out please.'
            message += '\n\n'
            message += 'The error, which has been logged in more detail and will be repeated later, is:'
            message += '\n\n'
            message += str( e )
            
            CG.client_controller.BlockingSafeShowCriticalMessage( 'Problem with granularisation!', message )
            
            job_status = ClientThreading.JobStatus( pausable = True )
            
            job_status.SetStatusTitle( 'Trying to recover from granularisation error.' )
            
            CG.client_controller.pub( 'message', job_status )
            
            ClientFilesPhysical.RegranulariseBaseLocation( locations, [ 'f', 't' ], 3, 2, job_status )
            
            raise
            
        
        hex_chars = '0123456789abcdef'
        
        old_data = self._Execute( 'SELECT prefix, location_id FROM client_files_subfolders;' ).fetchall()
        
        self._Execute( 'DELETE FROM client_files_subfolders;' )
        
        inserts = []
        
        for ( prefix, location_id ) in old_data:
            
            inserts.extend( [ ( prefix + hex_char, location_id ) for hex_char in hex_chars ] )
            
        
        self._ExecuteMany( 'INSERT OR IGNORE INTO client_files_subfolders ( prefix, location_id ) VALUES ( ?, ? );', inserts )
        
        self._Execute( 'DELETE FROM current_storage_granularity;' )
        
        self._Execute( 'INSERT INTO current_storage_granularity ( granularity ) VALUES ( ? );', ( 3, ) )
        
        return granularise_result
        
    
    def Initialise( self ):
        
        current_storage_granularity = HydrusFilesPhysicalStorage.DEFAULT_PREFIX_LENGTH
        
        self._Execute( 'INSERT INTO current_storage_granularity ( granularity ) VALUES ( ? );', ( current_storage_granularity, ) )
        
        default_client_files_path = os.path.join( self._db_dir, 'client_files' )
        
        HydrusPaths.MakeSureDirectoryExists( default_client_files_path )
        
        location_id = self.GetLocationId( default_client_files_path )
        
        for prefix in HydrusFilesPhysicalStorage.IteratePrefixes( 'f', current_storage_granularity ):
            
            self._Execute( 'INSERT INTO client_files_subfolders ( prefix, location_id ) VALUES ( ?, ? );', ( prefix, location_id ) )
            
        
        for prefix in HydrusFilesPhysicalStorage.IteratePrefixes( 't', current_storage_granularity ):
            
            self._Execute( 'INSERT INTO client_files_subfolders ( prefix, location_id ) VALUES ( ?, ? );', ( prefix, location_id ) )
            
        
        self._Execute( 'INSERT INTO ideal_client_files_locations ( location_id, weight, max_num_bytes ) VALUES ( ?, ?, ? );', ( location_id, 1, None ) )
        
    
    def PurgeOrphanLocations( self ):
        
        good_ids = set()
        
        good_ids.update( self._STS( self._Execute( 'SELECT location_id FROM current_client_files_locations;' ) ) )
        good_ids.update( self._STS( self._Execute( 'SELECT location_id FROM ideal_client_files_locations;' ) ) )
        good_ids.update( self._STS( self._Execute( 'SELECT location_id FROM ideal_thumbnail_override_location;' ) ) )
        
        existing_ids = self._STS( self._Execute( 'SELECT location_id FROM current_client_files_locations;' ) )
        
        orphan_ids = existing_ids.difference( good_ids )
        
        self._ExecuteMany( 'DELETE FROM current_client_files_locations WHERE location_id = ?;', ( ( location_id, ) for location_id in orphan_ids ) )
        
    
    def RelocateClientFiles( self, source_subfolder: ClientFilesPhysical.FilesStorageSubfolder, dest_subfolder: ClientFilesPhysical.FilesStorageSubfolder ):
        
        # TODO: this guy is going to be replaced with multiple potential locations and slow background migration
        # we'll have a complete rework, probably some extra table of current migration target/jobs or something, and regularly do bits of work to queue up work and then execute when files are not loaded etc..
        
        if source_subfolder.prefix != dest_subfolder.prefix:
            
            raise Exception( f'Was commanded to move "{source_subfolder}" to "{dest_subfolder}", but the prefixes were different!' )
            
        
        if not source_subfolder.PathExists():
            
            raise Exception( f'Was commanded to move "{source_subfolder}" to "{dest_subfolder}", but the source subfolder does not exist!' )
            
        
        if not dest_subfolder.base_location.PathExists():
            
            raise Exception( f'Was commanded to move "{source_subfolder}" to "{dest_subfolder}", but the base destination location does not exist!' )
            
        
        source_dir = source_subfolder.path
        dest_dir = dest_subfolder.path
        
        if source_dir == dest_dir: # don't do 'samefile' test here--that isn't strictly an error--just exact path
            
            raise Exception( f'Was commanded to move "{source_subfolder}" to "{dest_subfolder}", but they are the same location!' )
            
        
        prefix = source_subfolder.prefix
        
        self._Execute( 'DELETE FROM client_files_subfolders WHERE prefix = ?;', ( prefix, ) )
        
        # via symlinking etc... which means we are just updating a simple db record, not wanting to move any files
        they_are_secretly_the_same = os.path.samefile( source_subfolder.base_location.path, dest_subfolder.base_location.path )
        
        if not they_are_secretly_the_same:
            
            if os.path.exists( source_dir ):
                
                HydrusPaths.MergeTree( source_dir, dest_dir )
                
            else:
                
                if not os.path.exists( dest_dir ):
                    
                    HydrusPaths.MakeSureDirectoryExists( dest_dir )
                    
                
            
        
        dest_location_id = self.GetLocationId( dest_subfolder.base_location.path )
        
        self._Execute( 'INSERT OR IGNORE INTO client_files_subfolders ( prefix, location_id ) VALUES ( ?, ? );', ( prefix, dest_location_id ) )
        
        if not they_are_secretly_the_same:
            
            subdirs = source_subfolder.GetPrefixDirectoriesLongestFirst()
            
            for subdir in subdirs:
                
                if os.path.exists( subdir ) and len( os.listdir( subdir ) ) == 0:
                    
                    try:
                        
                        HydrusPaths.DeletePath( subdir )
                        
                    except Exception as e:
                        
                        pass
                        
                    
                
            
        
        self.PurgeOrphanLocations()
        
    
    def RepairClientFiles( self, correct_rows: list[ tuple[ ClientFilesPhysical.FilesStorageSubfolder, ClientFilesPhysical.FilesStorageSubfolder ] ] ):
        
        # TODO: as we move to multiple valid locations, this should probably become something else, or the things that feed it should have more sophisticated discovery of the correct 
        # tbh we should probably replace it with a 'set everything to this' call, like setideal but just an override to fix actual current understanding of file location
        
        for ( incorrect_subfolder, correct_subfolder ) in correct_rows:
            
            # it is possible these are actually the same, when we do the 'just regen my thumbs, no recovery', in which case we mostly just want to create the actual physical subfolder here
            
            if incorrect_subfolder.prefix != correct_subfolder.prefix:
                
                raise Exception( f'Was commanded to move "{incorrect_subfolder}" to "{correct_subfolder}", but the prefixes were different!' )
                
            
            correct_subfolder.MakeSureExists()
            
            prefix = incorrect_subfolder.prefix
            
            self._Execute( 'DELETE FROM client_files_subfolders WHERE prefix = ?;', ( prefix, ) )
            
            dest_location_id = self.GetLocationId( correct_subfolder.base_location.path )
            
            self._Execute( 'INSERT OR IGNORE INTO client_files_subfolders ( prefix, location_id ) VALUES ( ?, ? );', ( prefix, dest_location_id ) )
            
        
        self.PurgeOrphanLocations()
        
    
    def SetIdealClientFilesLocations( self, media_base_locations, thumbnail_override_base_location ):
        
        if len( media_base_locations ) == 0:
            
            raise Exception( 'No locations passed in ideal locations list!' )
            
        
        self._Execute( 'DELETE FROM ideal_client_files_locations;' )
        
        for base_location in media_base_locations:
            
            location_id = self.GetLocationId( base_location.path )
            ideal_weight = base_location.ideal_weight
            max_num_bytes = base_location.max_num_bytes
            
            self._Execute( 'INSERT INTO ideal_client_files_locations ( location_id, weight, max_num_bytes ) VALUES ( ?, ?, ? );', ( location_id, ideal_weight, max_num_bytes ) )
            
        
        self._Execute( 'DELETE FROM ideal_thumbnail_override_location;' )
        
        if thumbnail_override_base_location is not None:
            
            location_id = self.GetLocationId( thumbnail_override_base_location.path )
            
            self._Execute( 'INSERT INTO ideal_thumbnail_override_location ( location_id ) VALUES ( ? );', ( location_id, ) )
            
        
        self.PurgeOrphanLocations()
        
        CG.client_controller.pub( 'new_ideal_client_files_locations' )
        
    
