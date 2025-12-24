import collections.abc
import json
import os

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTags
from hydrus.core import HydrusTime

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientStrings
from hydrus.client import ClientTime
from hydrus.client.importing.options import NoteImportOptions
from hydrus.client.metadata import ClientContentUpdates
from hydrus.client.metadata import ClientMetadataMigrationCore
from hydrus.client.networking import ClientNetworkingFunctions

class SingleFileMetadataExporter( ClientMetadataMigrationCore.ImporterExporterNode ):
    
    def Export( self, *args, **kwargs ):
        
        raise NotImplementedError()
        
    
    def ToString( self ) -> str:
        
        raise NotImplementedError()
        
    

class SingleFileMetadataExporterMedia( SingleFileMetadataExporter ):
    
    def Export( self, hash: bytes, rows: collections.abc.Collection[ str ] ):
        
        raise NotImplementedError()
        
    
    def ToString( self ) -> str:
        
        raise NotImplementedError()
        
    

class SingleFileMetadataExporterMediaNotes( SingleFileMetadataExporterMedia, HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_METADATA_SINGLE_FILE_EXPORTER_MEDIA_NOTES
    SERIALISABLE_NAME = 'Metadata Single File Exporter Media Notes'
    SERIALISABLE_VERSION = 2
    
    def __init__( self, forced_name = None ):
        
        super().__init__()
        
        self._forced_name = forced_name
        
    
    def _GetSerialisableInfo( self ):
        
        return self._forced_name
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        self._forced_name = serialisable_info
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            gumpf = old_serialisable_info
            
            forced_name = None
            
            new_serialisable_info = forced_name
            
            return ( 2, new_serialisable_info )
            
        
    
    def Export( self, hash: bytes, rows: collections.abc.Collection[ str ] ):
        
        if len( rows ) == 0:
            
            return
            
        
        names_and_notes = []
        
        for row in rows:
            
            if self._forced_name is None:
                
                if ClientMetadataMigrationCore.NOTE_CONNECTOR_STRING not in row:
                    
                    continue
                    
                
                ( name, text ) = row.split( ClientMetadataMigrationCore.NOTE_CONNECTOR_STRING, 1 )
                
            else:
                
                name = self._forced_name
                text = row
                
            
            if name == '' or text == '':
                
                continue
                
            
            name = name.replace( ClientMetadataMigrationCore.NOTE_NAME_ESCAPE_STRING, ClientMetadataMigrationCore.NOTE_CONNECTOR_STRING )
            
            names_and_notes.append( ( name, text ) )
            
        
        media_result = CG.client_controller.Read( 'media_result', hash )
        
        note_import_options = NoteImportOptions.NoteImportOptions()
        
        note_import_options.SetIsDefault( False )
        note_import_options.SetExtendExistingNoteIfPossible( True )
        note_import_options.SetConflictResolution( NoteImportOptions.NOTE_IMPORT_CONFLICT_RENAME )
        
        content_update_package = note_import_options.GetContentUpdatePackage( media_result, names_and_notes )
        
        if content_update_package.HasContent():
            
            CG.client_controller.WriteSynchronous( 'content_updates', content_update_package )
            
        
    
    def GetExampleStrings( self ):
        
        examples = [
            'Artist Commentary: This work is one of my favourites.',
            'Translation: "What a nice day!"'
        ]
        
        return examples
        
    
    def GetForcedName( self ) -> str | None:
        
        return self._forced_name
        
    
    def SetForcedName( self, forced_name: str | None ):
        
        self._forced_name = forced_name
        
    
    def ToString( self ) -> str:
        
        return 'notes to media'
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_METADATA_SINGLE_FILE_EXPORTER_MEDIA_NOTES ] = SingleFileMetadataExporterMediaNotes

class SingleFileMetadataExporterMediaTags( SingleFileMetadataExporterMedia, HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_METADATA_SINGLE_FILE_EXPORTER_MEDIA_TAGS
    SERIALISABLE_NAME = 'Metadata Single File Exporter Media Tags'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, service_key = None ):
        
        super().__init__()
        
        if service_key is None:
            
            service_key = CC.DEFAULT_LOCAL_TAG_SERVICE_KEY
            
        
        self._service_key = service_key
        
    
    def _GetSerialisableInfo( self ):
        
        return self._service_key.hex()
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        serialisable_service_key = serialisable_info
        
        self._service_key = bytes.fromhex( serialisable_service_key )
        
    
    def GetExampleStrings( self ):
        
        examples = [
            'blue eyes',
            'blonde hair',
            'skirt',
            'character:jane smith',
            'series:jane smith adventures',
            'creator:some guy'
        ]
        
        return examples
        
    
    def GetServiceKey( self ) -> bytes:
        
        return self._service_key
        
    
    def Export( self, hash: bytes, rows: collections.abc.Collection[ str ] ):
        
        if len( rows ) == 0:
            
            return
            
        
        if CG.client_controller.services_manager.GetServiceType( self._service_key ) == HC.LOCAL_TAG:
            
            add_content_action = HC.CONTENT_UPDATE_ADD
            
        else:
            
            add_content_action = HC.CONTENT_UPDATE_PEND
            
        
        hashes = { hash }
        
        tags = HydrusTags.CleanTags( rows )
        
        if len( tags ) > 0:
            
            content_updates = [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, add_content_action, ( tag, hashes ) ) for tag in tags ]
            
            CG.client_controller.WriteSynchronous( 'content_updates', ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( self._service_key, content_updates ) )
            
        
    
    def SetServiceKey( self, service_key: bytes ):
        
        self._service_key = service_key
        
    
    def ToString( self ) -> str:
        
        try:
            
            name = CG.client_controller.services_manager.GetName( self._service_key )
            
        except:
            
            name = 'unknown service'
            
        
        return 'tags to media, on "{}"'.format( name )
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_METADATA_SINGLE_FILE_EXPORTER_MEDIA_TAGS ] = SingleFileMetadataExporterMediaTags

class SingleFileMetadataExporterMediaTimestamps( SingleFileMetadataExporterMedia, HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_METADATA_SINGLE_FILE_EXPORTER_MEDIA_TIMESTAMPS
    SERIALISABLE_NAME = 'Metadata Single File Exporter Media Timestamps'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, timestamp_data_stub: ClientTime.TimestampData | None = None ):
        
        super().__init__()
        
        if timestamp_data_stub is None:
            
            timestamp_data_stub = ClientTime.TimestampData.STATICSimpleStub( HC.TIMESTAMP_TYPE_ARCHIVED )
            
        
        self._timestamp_data_stub = timestamp_data_stub
        
    
    def _GetSerialisableInfo( self ):
        
        return self._timestamp_data_stub.GetSerialisableTuple()
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        serialisable_timestamp_data_stub = serialisable_info
        
        self._timestamp_data_stub = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_timestamp_data_stub )
        
    
    def Export( self, hash: bytes, rows: collections.abc.Collection[ str ] ):
        
        if len( rows ) == 0:
            
            return
            
        
        row = list( rows )[ 0 ]
        
        try:
            
            timestamp = int( row )
            
        except ValueError:
            
            return
            
        
        if timestamp > HydrusTime.GetNow():
            
            return
            
        
        timestamp_data = self._timestamp_data_stub.Duplicate()
        
        new_timestamp_data = ClientTime.TimestampData( timestamp_type = timestamp_data.timestamp_type, location = timestamp_data.location, timestamp_ms = HydrusTime.MillisecondiseS( timestamp ) )
        
        content_updates = [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_TIMESTAMP, HC.CONTENT_UPDATE_SET, ( ( hash, ), new_timestamp_data ) ) ]
        
        CG.client_controller.WriteSynchronous( 'content_updates', ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, content_updates ) )
        
    
    def GetExampleStrings( self ):
        
        examples = [
            '1681682717'
        ]
        
        return examples
        
    
    def GetTimestampDataStub( self ) -> ClientTime.TimestampData:
        
        return self._timestamp_data_stub
        
    
    def SetTimestampDataStub( self, timestamp_data_stub: ClientTime.TimestampData ):
        
        self._timestamp_data_stub = timestamp_data_stub
        
    
    def ToString( self ) -> str:
        
        return '{} to media'.format( self._timestamp_data_stub )
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_METADATA_SINGLE_FILE_EXPORTER_MEDIA_TIMESTAMPS ] = SingleFileMetadataExporterMediaTimestamps

class SingleFileMetadataExporterMediaURLs( SingleFileMetadataExporterMedia, HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_METADATA_SINGLE_FILE_EXPORTER_MEDIA_URLS
    SERIALISABLE_NAME = 'Metadata Single File Exporter Media URLs'
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        super().__init__()
        
    
    def _GetSerialisableInfo( self ):
        
        return list()
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        gumpf = serialisable_info
        
    
    def Export( self, hash: bytes, rows: collections.abc.Collection[ str ] ):
        
        if len( rows ) == 0:
            
            return
            
        
        urls = []
        
        for row in rows:
            
            try:
                
                url = ClientNetworkingFunctions.EnsureURLIsEncoded( row )
                
                url = CG.client_controller.network_engine.domain_manager.NormaliseURL( url )
                
                urls.append( url )
                
            except HydrusExceptions.URLClassException:
                
                continue
                
            except:
                
                continue
                
            
        
        hashes = { hash }
        
        content_updates = [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_URLS, HC.CONTENT_UPDATE_ADD, ( urls, hashes ) ) ]
        
        CG.client_controller.WriteSynchronous( 'content_updates', ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, content_updates ) )
        
    
    def GetExampleStrings( self ):
        
        examples = [
            'https://example.com/gallery/index.php?post=123456&page=show',
            'https://cdn3.expl.com/files/file_id?id=123456&token=0123456789abcdef'
        ]
        
        return examples
        
    
    def ToString( self ) -> str:
        
        return 'urls to media'
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_METADATA_SINGLE_FILE_EXPORTER_MEDIA_URLS ] = SingleFileMetadataExporterMediaURLs

class SingleFileMetadataExporterSidecar( SingleFileMetadataExporter, ClientMetadataMigrationCore.SidecarNode ):
    
    def __init__( self, remove_actual_filename_ext: bool, suffix: str, filename_string_converter: ClientStrings.StringConverter, sidecar_file_extension: str ):
        
        self._sidecar_file_extension = sidecar_file_extension
        
        super().__init__( remove_actual_filename_ext, suffix, filename_string_converter )
        
    
    def _GetExportPath( self, actual_file_path: str ) -> str:
        
        return ClientMetadataMigrationCore.GetSidecarPath( actual_file_path, self._remove_actual_filename_ext, self._suffix, self._filename_string_converter, self._sidecar_file_extension )
        
    
    def Export( self, actual_file_path: str, rows: collections.abc.Collection[ str ] ):
        
        raise NotImplementedError()
        
    
    def GetExportPath( self, actual_file_path: str ) -> str:
        
        return self._GetExportPath( actual_file_path )
        
    
    def ToString( self ) -> str:
        
        raise NotImplementedError()
        
    

class SingleFileMetadataExporterJSON( SingleFileMetadataExporterSidecar, HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_METADATA_SINGLE_FILE_EXPORTER_JSON
    SERIALISABLE_NAME = 'Metadata Single File Exporter JSON'
    SERIALISABLE_VERSION = 2
    
    def __init__( self, remove_actual_filename_ext = None, suffix = None, filename_string_converter = None, nested_object_names = None ):
        
        if remove_actual_filename_ext is None:
            
            remove_actual_filename_ext = False
            
        
        if suffix is None:
            
            suffix = ''
            
        
        if filename_string_converter is None:
            
            filename_string_converter = ClientStrings.StringConverter( example_string = '0123456789abcdef.jpg.json' )
            
        
        super().__init__( remove_actual_filename_ext, suffix, filename_string_converter, 'json' )
        
        if nested_object_names is None:
            
            nested_object_names = []
            
        
        self._nested_object_names = nested_object_names
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_filename_string_converter = self._filename_string_converter.GetSerialisableTuple()
        
        return ( self._remove_actual_filename_ext, self._suffix, serialisable_filename_string_converter, self._nested_object_names )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._remove_actual_filename_ext, self._suffix, serialisable_filename_string_converter, self._nested_object_names ) = serialisable_info
        
        self._filename_string_converter = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_filename_string_converter )
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( suffix, nested_object_names ) = old_serialisable_info
            
            remove_actual_filename_ext = False
            filename_string_converter = ClientStrings.StringConverter( example_string = '0123456789abcdef.jpg.json' )
            
            serialisable_filename_string_converter = filename_string_converter.GetSerialisableTuple()
            
            new_serialisable_info = ( remove_actual_filename_ext, suffix, serialisable_filename_string_converter, nested_object_names )
            
            return ( 2, new_serialisable_info )
            
        
    
    def Export( self, actual_file_path: str, rows: collections.abc.Collection[ str ] ):
        
        if len( rows ) == 0:
            
            return
            
        
        path = self._GetExportPath( actual_file_path )
        
        if len( self._nested_object_names ) > 0:
            
            if os.path.exists( path ):
                
                with open( path, 'r', encoding = 'utf-8') as f:
                    
                    existing_raw_json = f.read()
                    
                
                try:
                    
                    json_dict = json.loads( existing_raw_json )
                    
                    if len( self._nested_object_names ) > 0 and not isinstance( json_dict, dict ):
                        
                        raise Exception( 'The existing JSON file was not a JSON Object!' )
                        
                    
                except Exception as e:
                    
                    # TODO: we probably want custom importer/exporter exceptions here
                    raise Exception( 'Could not read the existing JSON at {}!{}{}'.format( path, '\n', e ) )
                    
                
            else:
                
                json_dict = dict()
                
            
            node = json_dict
            
            for ( i, name ) in enumerate( self._nested_object_names ):
                
                if i == len( self._nested_object_names ) - 1:
                    
                    node[ name ] = list( rows )
                    
                else:
                    
                    if name not in node:
                        
                        node[ name ] = dict()
                        
                    
                    node = node[ name ]
                    
                
            
            json_to_write = json_dict
            
        else:
            
            json_to_write = list( rows )
            
        
        raw_json_to_write = json.dumps( json_to_write )
        
        with open( path, 'w', encoding = 'utf-8' ) as f:
            
            f.write( raw_json_to_write )
            
        
    
    def GetNestedObjectNames( self ) -> list[ str ]:
        
        return list( self._nested_object_names )
        
    
    def SetNestedObjectNames( self, nested_object_names: list[ str ] ):
        
        self._nested_object_names = list( nested_object_names )
        
    
    def ToString( self ) -> str:
        
        suffix_s = '' if self._suffix == '' else '.{}'.format( self._suffix )
        
        non_s = '' if len( self._nested_object_names ) == 0 else ' ({})'.format( '>'.join( self._nested_object_names ) )
        
        return 'to {}.json sidecar{}'.format( suffix_s, non_s )
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_METADATA_SINGLE_FILE_EXPORTER_JSON ] = SingleFileMetadataExporterJSON

class SingleFileMetadataExporterTXT( SingleFileMetadataExporterSidecar, HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_METADATA_SINGLE_FILE_EXPORTER_TXT
    SERIALISABLE_NAME = 'Metadata Single File Exporter TXT'
    SERIALISABLE_VERSION = 3
    
    def __init__( self, remove_actual_filename_ext = None, suffix = None, filename_string_converter = None, separator = None ):
        
        if remove_actual_filename_ext is None:
            
            remove_actual_filename_ext = False
            
        
        if suffix is None:
            
            suffix = ''
            
        
        if filename_string_converter is None:
            
            filename_string_converter = ClientStrings.StringConverter( example_string = '0123456789abcdef.jpg.txt' )
            
        
        if separator is None:
            
            separator = '\n'
            
        
        super().__init__( remove_actual_filename_ext, suffix, filename_string_converter, 'txt' )
        
        self._separator = separator
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_filename_string_converter = self._filename_string_converter.GetSerialisableTuple()
        
        return ( self._remove_actual_filename_ext, self._suffix, serialisable_filename_string_converter, self._separator )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._remove_actual_filename_ext, self._suffix, serialisable_filename_string_converter, self._separator ) = serialisable_info
        
        self._filename_string_converter = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_filename_string_converter )
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            suffix = old_serialisable_info
            
            remove_actual_filename_ext = False
            filename_string_converter = ClientStrings.StringConverter( example_string = '0123456789abcdef.jpg.txt' )
            
            serialisable_filename_string_converter = filename_string_converter.GetSerialisableTuple()
            
            new_serialisable_info = ( remove_actual_filename_ext, suffix, serialisable_filename_string_converter )
            
            return ( 2, new_serialisable_info )
            
        
        if version == 2:
            
            ( remove_actual_filename_ext, suffix, serialisable_filename_string_converter ) = old_serialisable_info
            
            separator = '\n'
            
            new_serialisable_info = ( remove_actual_filename_ext, suffix, serialisable_filename_string_converter, separator )
            
            return ( 3, new_serialisable_info )
            
        
    
    def Export( self, actual_file_path: str, rows: collections.abc.Collection[ str ] ):
        
        if len( rows ) == 0:
            
            return
            
        
        path = self._GetExportPath( actual_file_path )
        
        with open( path, 'w', encoding = 'utf-8' ) as f:
            
            f.write( self._separator.join( rows ) )
            
        
    
    def GetSeparator( self ) -> str:
        
        return self._separator
        
    
    def SetSeparator( self, separator: str ):
        
        self._separator = separator
        
    
    def ToString( self ) -> str:
        
        suffix_s = '' if self._suffix == '' else '.{}'.format( self._suffix )
        
        return 'to {}.txt sidecar'.format( suffix_s )
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_METADATA_SINGLE_FILE_EXPORTER_TXT ] = SingleFileMetadataExporterTXT
