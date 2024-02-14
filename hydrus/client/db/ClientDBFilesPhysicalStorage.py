import os
import sqlite3
import typing

from hydrus.core import HydrusData
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusPaths

from hydrus.client import ClientFilesPhysical
from hydrus.client import ClientGlobals as CG
from hydrus.client.db import ClientDBModule

class ClientDBFilesPhysicalStorage( ClientDBModule.ClientDBModule ):
    
    def __init__(
        self,
        cursor: sqlite3.Cursor,
        db_dir: str
    ):
        
        ClientDBModule.ClientDBModule.__init__( self, 'client files physical storage', cursor )
        
        self._db_dir = db_dir
        
    
    def _GetInitialTableGenerationDict( self ) -> dict:
        
        return {
            'main.client_files_subfolders' : ( 'CREATE TABLE IF NOT EXISTS {} ( prefix TEXT, location TEXT, purge INTEGER_BOOLEAN, PRIMARY KEY ( prefix, location ) );', 541 ),
            'main.ideal_client_files_locations' : ( 'CREATE TABLE IF NOT EXISTS {} ( location TEXT, weight INTEGER, max_num_bytes INTEGER );', 400 ),
            'main.ideal_thumbnail_override_location' : ( 'CREATE TABLE IF NOT EXISTS {} ( location TEXT );', 400 )
        }
        
    
    def GetClientFilesSubfolders( self ):
        
        ( media_base_locations, ideal_thumbnail_override_base_location ) = self.GetIdealClientFilesLocations()
        
        paths_to_base_locations = { base_location.path : base_location for base_location in media_base_locations }
        
        if ideal_thumbnail_override_base_location is not None:
            
            paths_to_base_locations[ ideal_thumbnail_override_base_location.path ] = ideal_thumbnail_override_base_location
            
        
        subfolders = set()
        
        for ( prefix, portable_location_path, purge ) in self._Execute( 'SELECT prefix, location, purge FROM client_files_subfolders;' ):
            
            path = HydrusPaths.ConvertPortablePathToAbsPath( portable_location_path )
            
            base_location = paths_to_base_locations.get( path, ClientFilesPhysical.FilesStorageBaseLocation( path, 0 ) )
            
            subfolders.add( ClientFilesPhysical.FilesStorageSubfolder( prefix, base_location, purge ) )
            
        
        all_prefixes = { subfolder.prefix for subfolder in subfolders }
        
        missing_prefixes_f = ClientFilesPhysical.GetMissingPrefixes( 'f', all_prefixes )
        missing_prefixes_t = ClientFilesPhysical.GetMissingPrefixes( 't', all_prefixes )
        
        if len( missing_prefixes_f ) > 0 or len( missing_prefixes_t ) > 0:
            
            message = 'When fetching the directories where your files are stored, the database discovered that some entries were missing! If you did not fiddle with the database yourself, this probably happened due to database corruption.'
            message += os.linesep * 2
            message += 'Default values will now be inserted. If you have previously migrated your files or thumbnails, and assuming this is occuring on boot, you will next be presented with a dialog to remap them to the correct location.'
            message += os.linesep * 2
            message += 'If this is not happening on client boot, you should kill the hydrus process right now, as a serious hard drive fault has likely recently occurred.'
            
            self._DisplayCatastrophicError( message )
            
            client_files_default = os.path.join( self._db_dir, 'client_files' )
            
            HydrusPaths.MakeSureDirectoryExists( client_files_default )
            
            portable_path = HydrusPaths.ConvertAbsPathToPortablePath( client_files_default )
            
            for missing_prefix in missing_prefixes_f:
                
                self._Execute( 'INSERT OR IGNORE INTO client_files_subfolders ( prefix, location, purge ) VALUES ( ?, ?, ? );', ( missing_prefix, portable_path, False ) )
                
            
            for missing_prefix in missing_prefixes_t:
                
                self._Execute( 'INSERT OR IGNORE INTO client_files_subfolders ( prefix, location, purge ) VALUES ( ?, ?, ? );', ( missing_prefix, portable_path, False ) )
                
            
            for ( prefix, portable_location_path, purge ) in self._Execute( 'SELECT prefix, location, purge FROM client_files_subfolders;' ):
                
                base_location = paths_to_base_locations.get( portable_location_path, ClientFilesPhysical.FilesStorageBaseLocation( portable_location_path, 0 ) )
                
                subfolders.add( ClientFilesPhysical.FilesStorageSubfolder( prefix, base_location, purge ) )
                
            
        
        return subfolders
        
    
    def GetIdealClientFilesLocations( self ):
        
        media_base_locations = set()
        
        for ( portable_path, ideal_weight, max_num_bytes ) in self._Execute( 'SELECT location, weight, max_num_bytes FROM ideal_client_files_locations;' ):
            
            abs_path = HydrusPaths.ConvertPortablePathToAbsPath( portable_path )
            
            media_base_locations.add( ClientFilesPhysical.FilesStorageBaseLocation( abs_path, ideal_weight, max_num_bytes = max_num_bytes ) )
            
        
        result = self._Execute( 'SELECT location FROM ideal_thumbnail_override_location;' ).fetchone()
        
        if result is None:
            
            thumbnail_override_base_location = None
            
        else:
            
            ( portable_ideal_thumbnail_override_path, ) = result
            
            abs_ideal_thumbnail_override_path = HydrusPaths.ConvertPortablePathToAbsPath( portable_ideal_thumbnail_override_path )
            
            thumbnail_override_base_location = ClientFilesPhysical.FilesStorageBaseLocation( abs_ideal_thumbnail_override_path, 1 )
            
        
        return ( media_base_locations, thumbnail_override_base_location )
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> typing.List[ typing.Tuple[ str, str ] ]:
        
        tables_and_columns = []
        
        return tables_and_columns
        
    
    def Initialise( self ):
        
        default_abs_path = os.path.join( self._db_dir, 'client_files' )
        
        HydrusPaths.MakeSureDirectoryExists( default_abs_path )
        
        portable_path = HydrusPaths.ConvertAbsPathToPortablePath( default_abs_path )
        
        for hex_prefix in HydrusData.IterateHexPrefixes():
            
            self._Execute( 'INSERT INTO client_files_subfolders ( prefix, location, purge ) VALUES ( ?, ?, ? );', ( 'f' + hex_prefix, portable_path, False ) )
            self._Execute( 'INSERT INTO client_files_subfolders ( prefix, location, purge ) VALUES ( ?, ?, ? );', ( 't' + hex_prefix, portable_path, False ) )
            
        
        self._Execute( 'INSERT INTO ideal_client_files_locations ( location, weight, max_num_bytes ) VALUES ( ?, ?, ? );', ( portable_path, 1, None ) )
        
    
    def RelocateClientFiles( self, source_subfolder: ClientFilesPhysical.FilesStorageSubfolder, dest_subfolder: ClientFilesPhysical.FilesStorageSubfolder ):
        
        # TODO: so this guy is going to be replaces with slow migration, which will be something like:
        # Add a new valid subfolder
        # Set dupe subfolder to purge = True
        # Ask database for valid purge paths
        # once a source is fully purged, remove the now purged subfolder
        
        if source_subfolder.prefix != dest_subfolder.prefix:
            
            raise Exception( f'Was commanded to move "{source_subfolder}" to "{dest_subfolder}", but the prefixes were different!' )
            
        
        if not source_subfolder.PathExists():
            
            raise Exception( f'Was commanded to move "{source_subfolder}" to "{dest_subfolder}", but the source does not exist!' )
            
        
        if not dest_subfolder.base_location.PathExists():
            
            raise Exception( f'Was commanded to move "{source_subfolder}" to "{dest_subfolder}", but the base destination location does not exist!' )
            
        
        source_dir = source_subfolder.path
        dest_dir = dest_subfolder.path
        
        if source_dir == dest_dir:
            
            raise Exception( f'Was commanded to move "{source_subfolder}" to "{dest_subfolder}", but they are the same location!' )
            
        
        # via symlinking etc... which means we are just updating a simple db record, not wanting to move any files
        they_are_secretly_the_same = os.path.samefile( source_subfolder.base_location.path, dest_subfolder.base_location.path )
        
        if not they_are_secretly_the_same:
            
            if os.path.exists( source_dir ):
                
                HydrusPaths.MergeTree( source_dir, dest_dir )
                
            else:
                
                if not os.path.exists( dest_dir ):
                    
                    HydrusPaths.MakeSureDirectoryExists( dest_dir )
                    
                
            
        
        prefix = source_subfolder.prefix
        
        portable_source_base_location = source_subfolder.base_location.GetPortablePath()
        portable_dest_base_location = dest_subfolder.base_location.GetPortablePath()
        
        self._Execute( 'DELETE FROM client_files_subfolders WHERE prefix = ? AND location = ?;', ( prefix, portable_source_base_location ) )
        self._Execute( 'INSERT OR IGNORE INTO client_files_subfolders ( prefix, location, purge ) VALUES ( ?, ?, ? );', ( prefix, portable_dest_base_location, False ) )
        
        if not they_are_secretly_the_same:
            
            if os.path.exists( source_dir ) and len( os.listdir( source_dir ) ) == 0:
                
                try: HydrusPaths.RecyclePath( source_dir )
                except: pass
                
            
        
    
    def RepairClientFiles( self, correct_rows ):
        
        # TODO: as we move to multiple valid locations, this should probably become something else, or the things that feed it should have more sophisticated discovery of the correct 
        # tbh we should probably replace it with a 'set everything to this' call, like setideal but just an override to fix actual current understanding of file location
        
        for ( incorrect_subfolder, correct_subfolder ) in correct_rows:
            
            if incorrect_subfolder.prefix != correct_subfolder.prefix:
                
                raise Exception( f'Was commanded to move "{incorrect_subfolder}" to "{correct_subfolder}", but the prefixes were different!' )
                
            
            correct_subfolder.MakeSureExists()
            
            prefix = incorrect_subfolder.prefix
            
            # it is possible these are actually the same, when we do the 'just regen my thumbs, no recovery'
            portable_incorrect_base_location = incorrect_subfolder.base_location.GetPortablePath()
            portable_correct_base_location = correct_subfolder.base_location.GetPortablePath()
            
            if portable_incorrect_base_location != portable_correct_base_location:
                
                self._Execute( 'DELETE FROM client_files_subfolders WHERE prefix = ? AND location = ?;', ( prefix, portable_incorrect_base_location ) )
                self._Execute( 'INSERT OR IGNORE INTO client_files_subfolders ( prefix, location, purge ) VALUES ( ?, ?, ? );', ( prefix, portable_correct_base_location, False ) )
                
            
        
    
    def SetIdealClientFilesLocations( self, media_base_locations, thumbnail_override_base_location ):
        
        if len( media_base_locations ) == 0:
            
            raise Exception( 'No locations passed in ideal locations list!' )
            
        
        self._Execute( 'DELETE FROM ideal_client_files_locations;' )
        
        for base_location in media_base_locations:
            
            portable_path = HydrusPaths.ConvertAbsPathToPortablePath( base_location.path )
            ideal_weight = base_location.ideal_weight
            max_num_bytes = base_location.max_num_bytes
            
            self._Execute( 'INSERT INTO ideal_client_files_locations ( location, weight, max_num_bytes ) VALUES ( ?, ?, ? );', ( portable_path, ideal_weight, max_num_bytes ) )
            
        
        self._Execute( 'DELETE FROM ideal_thumbnail_override_location;' )
        
        if thumbnail_override_base_location is not None:
            
            portable_path = HydrusPaths.ConvertAbsPathToPortablePath( thumbnail_override_base_location.path )
            
            self._Execute( 'INSERT INTO ideal_thumbnail_override_location ( location ) VALUES ( ? );', ( portable_path, ) )
            
        
        CG.client_controller.pub( 'new_ideal_client_files_locations' )
        
    
