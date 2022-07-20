import os
import sqlite3
import typing

from hydrus.core import HydrusData
from hydrus.core import HydrusPaths

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
            'main.client_files_locations' : ( 'CREATE TABLE IF NOT EXISTS {} ( prefix TEXT, location TEXT );', 400 ),
            'main.ideal_client_files_locations' : ( 'CREATE TABLE IF NOT EXISTS {} ( location TEXT, weight INTEGER );', 400 ),
            'main.ideal_thumbnail_override_location' : ( 'CREATE TABLE IF NOT EXISTS {} ( location TEXT );', 400 )
        }
        
    
    def GetClientFilesLocations( self ):
        
        result = { prefix : HydrusPaths.ConvertPortablePathToAbsPath( portable_location ) for ( prefix, portable_location ) in self._Execute( 'SELECT prefix, location FROM client_files_locations;' ) }
        
        if len( result ) < 512:
            
            message = 'When fetching the directories where your files are stored, the database discovered some entries were missing!'
            message += os.linesep * 2
            message += 'Default values will now be inserted. If you have previously migrated your files or thumbnails, and assuming this is occuring on boot, you will next be presented with a dialog to remap them to the correct location.'
            message += os.linesep * 2
            message += 'If this is not happening on client boot, you should kill the hydrus process right now, as a serious hard drive fault has likely recently occurred.'
            
            self._DisplayCatastrophicError( message )
            
            client_files_default = os.path.join( self._db_dir, 'client_files' )
            
            HydrusPaths.MakeSureDirectoryExists( client_files_default )
            
            portable_path = HydrusPaths.ConvertAbsPathToPortablePath( client_files_default )
            
            for hex_prefix in HydrusData.IterateHexPrefixes():
                
                if 'f' + hex_prefix not in result:
                    
                    self._Execute( 'INSERT OR IGNORE INTO client_files_locations ( prefix, location ) VALUES ( ?, ? );', ( 'f' + hex_prefix, portable_path ) )
                    
                
                if 't' + hex_prefix not in result:
                    
                    self._Execute( 'INSERT OR IGNORE INTO client_files_locations ( prefix, location ) VALUES ( ?, ? );', ( 't' + hex_prefix, portable_path ) )
                    
                
            
            result = { prefix : HydrusPaths.ConvertPortablePathToAbsPath( portable_location ) for ( prefix, portable_location ) in self._Execute( 'SELECT prefix, location FROM client_files_locations;' ) }
            
        
        return result
        
    
    def GetIdealClientFilesLocations( self ):
        
        abs_locations_to_ideal_weights = {}
        
        for ( portable_location, weight ) in self._Execute( 'SELECT location, weight FROM ideal_client_files_locations;' ):
            
            abs_location = HydrusPaths.ConvertPortablePathToAbsPath( portable_location )
            
            abs_locations_to_ideal_weights[ abs_location ] = weight
            
        
        result = self._Execute( 'SELECT location FROM ideal_thumbnail_override_location;' ).fetchone()
        
        if result is None:
            
            abs_ideal_thumbnail_override_location = None
            
        else:
            
            ( portable_ideal_thumbnail_override_location, ) = result
            
            abs_ideal_thumbnail_override_location = HydrusPaths.ConvertPortablePathToAbsPath( portable_ideal_thumbnail_override_location )
            
        
        return ( abs_locations_to_ideal_weights, abs_ideal_thumbnail_override_location )
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> typing.List[ typing.Tuple[ str, str ] ]:
        
        tables_and_columns = []
        
        return tables_and_columns
        
    
    def Initialise( self ):
        
        default_abs_path = os.path.join( self._db_dir, 'client_files' )
        
        HydrusPaths.MakeSureDirectoryExists( default_abs_path )
        
        portable_path = HydrusPaths.ConvertAbsPathToPortablePath( default_abs_path )
        
        for hex_prefix in HydrusData.IterateHexPrefixes():
            
            self._Execute( 'INSERT INTO client_files_locations ( prefix, location ) VALUES ( ?, ? );', ( 'f' + hex_prefix, portable_path ) )
            self._Execute( 'INSERT INTO client_files_locations ( prefix, location ) VALUES ( ?, ? );', ( 't' + hex_prefix, portable_path ) )
            
        
        self._Execute( 'INSERT INTO ideal_client_files_locations ( location, weight ) VALUES ( ?, ? );', ( portable_path, 1 ) )
        
    
    def RelocateClientFiles( self, prefix, abs_source, abs_dest ):
        
        if not os.path.exists( abs_dest ):
            
            raise Exception( 'Was commanded to move prefix "{}" from "{}" to "{}", but that destination does not exist!'.format( prefix, abs_source, abs_dest ) )
            
        
        full_source = os.path.join( abs_source, prefix )
        full_dest = os.path.join( abs_dest, prefix )
        
        if os.path.exists( full_source ):
            
            HydrusPaths.MergeTree( full_source, full_dest )
            
        elif not os.path.exists( full_dest ):
            
            HydrusPaths.MakeSureDirectoryExists( full_dest )
            
        
        portable_dest = HydrusPaths.ConvertAbsPathToPortablePath( abs_dest )
        
        self._Execute( 'UPDATE client_files_locations SET location = ? WHERE prefix = ?;', ( portable_dest, prefix ) )
        
        if os.path.exists( full_source ):
            
            try: HydrusPaths.RecyclePath( full_source )
            except: pass
            
        
    
    def RepairClientFiles( self, correct_rows ):
        
        for ( prefix, abs_correct_location ) in correct_rows:
            
            full_abs_correct_location = os.path.join( abs_correct_location, prefix )
            
            HydrusPaths.MakeSureDirectoryExists( full_abs_correct_location )
            
            portable_correct_location = HydrusPaths.ConvertAbsPathToPortablePath( abs_correct_location )
            
            self._Execute( 'UPDATE client_files_locations SET location = ? WHERE prefix = ?;', ( portable_correct_location, prefix ) )
            
        
    
    def SetIdealClientFilesLocations( self, abs_locations_to_ideal_weights, abs_ideal_thumbnail_override_location ):
        
        if len( abs_locations_to_ideal_weights ) == 0:
            
            raise Exception( 'No locations passed in ideal locations list!' )
            
        
        self._Execute( 'DELETE FROM ideal_client_files_locations;' )
        
        for ( abs_location, weight ) in abs_locations_to_ideal_weights.items():
            
            portable_location = HydrusPaths.ConvertAbsPathToPortablePath( abs_location )
            
            self._Execute( 'INSERT INTO ideal_client_files_locations ( location, weight ) VALUES ( ?, ? );', ( portable_location, weight ) )
            
        
        self._Execute( 'DELETE FROM ideal_thumbnail_override_location;' )
        
        if abs_ideal_thumbnail_override_location is not None:
            
            portable_ideal_thumbnail_override_location = HydrusPaths.ConvertAbsPathToPortablePath( abs_ideal_thumbnail_override_location )
            
            self._Execute( 'INSERT INTO ideal_thumbnail_override_location ( location ) VALUES ( ? );', ( portable_ideal_thumbnail_override_location, ) )
            
        
    
