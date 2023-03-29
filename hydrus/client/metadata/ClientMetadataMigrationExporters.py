import json
import os
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTags

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientStrings
from hydrus.client.importing.options import NoteImportOptions
from hydrus.client.metadata import ClientMetadataMigrationCore

class SingleFileMetadataExporter( ClientMetadataMigrationCore.ImporterExporterNode ):
    
    def Export( self, *args, **kwargs ):
        
        raise NotImplementedError()
        
    
    def ToString( self ) -> str:
        
        raise NotImplementedError()
        
    

class SingleFileMetadataExporterMedia( SingleFileMetadataExporter ):
    
    def Export( self, hash: bytes, rows: typing.Collection[ str ] ):
        
        raise NotImplementedError()
        
    
    def ToString( self ) -> str:
        
        raise NotImplementedError()
        
    

class SingleFileMetadataExporterSidecar( SingleFileMetadataExporter, ClientMetadataMigrationCore.SidecarNode ):
    
    def __init__( self, remove_actual_filename_ext: bool, suffix: str, filename_string_converter: ClientStrings.StringConverter ):
        
        ClientMetadataMigrationCore.SidecarNode.__init__( self, remove_actual_filename_ext, suffix, filename_string_converter )
        SingleFileMetadataExporter.__init__( self )
        
    
    def Export( self, actual_file_path: str, rows: typing.Collection[ str ] ):
        
        raise NotImplementedError()
        
    
    def ToString( self ) -> str:
        
        raise NotImplementedError()
        
    

class SingleFileMetadataExporterMediaNotes( HydrusSerialisable.SerialisableBase, SingleFileMetadataExporterMedia ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_METADATA_SINGLE_FILE_EXPORTER_MEDIA_NOTES
    SERIALISABLE_NAME = 'Metadata Single File Exporter Media Notes'
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        SingleFileMetadataExporterMedia.__init__( self )
        
    
    def _GetSerialisableInfo( self ):
        
        return list()
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        gumpf = serialisable_info
        
    
    def Export( self, hash: bytes, rows: typing.Collection[ str ] ):
        
        if len( rows ) == 0:
            
            return
            
        
        names_and_notes = []
        
        for row in rows:
            
            if ClientMetadataMigrationCore.NOTE_CONNECTOR_STRING not in row:
                
                continue
                
            
            ( name, text ) = row.split( ClientMetadataMigrationCore.NOTE_CONNECTOR_STRING, 1 )
            
            if name == '' or text == '':
                
                continue
                
            
            name = name.replace( ClientMetadataMigrationCore.NOTE_NAME_ESCAPE_STRING, ClientMetadataMigrationCore.NOTE_CONNECTOR_STRING )
            
            names_and_notes.append( ( name, text ) )
            
        
        media_result = HG.client_controller.Read( 'media_result', hash )
        
        note_import_options = NoteImportOptions.NoteImportOptions()
        
        note_import_options.SetIsDefault( False )
        note_import_options.SetExtendExistingNoteIfPossible( True )
        note_import_options.SetConflictResolution( NoteImportOptions.NOTE_IMPORT_CONFLICT_RENAME )
        
        service_keys_to_content_updates = note_import_options.GetServiceKeysToContentUpdates( media_result, names_and_notes )
        
        if len( service_keys_to_content_updates ) > 0:
            
            HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
            
        
    
    def GetExampleStrings( self ):
        
        examples = [
            'Artist Commentary: This work is one of my favourites.',
            'Translation: "What a nice day!"'
        ]
        
        return examples
        
    
    def ToString( self ) -> str:
        
        return 'notes to media'
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_METADATA_SINGLE_FILE_EXPORTER_MEDIA_NOTES ] = SingleFileMetadataExporterMediaNotes

class SingleFileMetadataExporterMediaTags( HydrusSerialisable.SerialisableBase, SingleFileMetadataExporterMedia ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_METADATA_SINGLE_FILE_EXPORTER_MEDIA_TAGS
    SERIALISABLE_NAME = 'Metadata Single File Exporter Media Tags'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, service_key = None ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        SingleFileMetadataExporterMedia.__init__( self )
        
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
        
    
    def Export( self, hash: bytes, rows: typing.Collection[ str ] ):
        
        if len( rows ) == 0:
            
            return
            
        
        if HG.client_controller.services_manager.GetServiceType( self._service_key ) == HC.LOCAL_TAG:
            
            add_content_action = HC.CONTENT_UPDATE_ADD
            
        else:
            
            add_content_action = HC.CONTENT_UPDATE_PEND
            
        
        hashes = { hash }
        
        tags = HydrusTags.CleanTags( rows )
        
        if len( tags ) > 0:
            
            content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, add_content_action, ( tag, hashes ) ) for tag in tags ]
            
            HG.client_controller.WriteSynchronous( 'content_updates', { self._service_key : content_updates } )
            
        
    
    def SetServiceKey( self, service_key: bytes ):
        
        self._service_key = service_key
        
    
    def ToString( self ) -> str:
        
        try:
            
            name = HG.client_controller.services_manager.GetName( self._service_key )
            
        except:
            
            name = 'unknown service'
            
        
        return 'tags to media, on "{}"'.format( name )
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_METADATA_SINGLE_FILE_EXPORTER_MEDIA_TAGS ] = SingleFileMetadataExporterMediaTags

class SingleFileMetadataExporterMediaURLs( HydrusSerialisable.SerialisableBase, SingleFileMetadataExporterMedia ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_METADATA_SINGLE_FILE_EXPORTER_MEDIA_URLS
    SERIALISABLE_NAME = 'Metadata Single File Exporter Media URLs'
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        SingleFileMetadataExporterMedia.__init__( self )
        
    
    def _GetSerialisableInfo( self ):
        
        return list()
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        gumpf = serialisable_info
        
    
    def Export( self, hash: bytes, rows: typing.Collection[ str ] ):
        
        if len( rows ) == 0:
            
            return
            
        
        urls = []
        
        for row in rows:
            
            try:
                
                url = HG.client_controller.network_engine.domain_manager.NormaliseURL( row )
                
                urls.append( url )
                
            except HydrusExceptions.URLClassException:
                
                continue
                
            except:
                
                continue
                
            
        
        hashes = { hash }
        
        content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_URLS, HC.CONTENT_UPDATE_ADD, ( urls, hashes ) ) ]
        
        HG.client_controller.WriteSynchronous( 'content_updates', { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : content_updates } )
        
    
    def GetExampleStrings( self ):
        
        examples = [
            'https://example.com/gallery/index.php?post=123456&page=show',
            'https://cdn3.expl.com/files/file_id?id=123456&token=0123456789abcdef'
        ]
        
        return examples
        
    
    def ToString( self ) -> str:
        
        return 'urls to media'
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_METADATA_SINGLE_FILE_EXPORTER_MEDIA_URLS ] = SingleFileMetadataExporterMediaURLs

class SingleFileMetadataExporterJSON( HydrusSerialisable.SerialisableBase, SingleFileMetadataExporterSidecar ):
    
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
            
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        SingleFileMetadataExporterSidecar.__init__( self, remove_actual_filename_ext, suffix, filename_string_converter )
        
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
            
        
    
    def Export( self, actual_file_path: str, rows: typing.Collection[ str ] ):
        
        if len( rows ) == 0:
            
            return
            
        
        path = ClientMetadataMigrationCore.GetSidecarPath( actual_file_path, self._remove_actual_filename_ext, self._suffix, self._filename_string_converter, 'json' )
        
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
                    raise Exception( 'Could not read the existing JSON at {}!{}{}'.format( path, os.linesep, e ) )
                    
                
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
            
        
    
    def GetNestedObjectNames( self ) -> typing.List[ str ]:
        
        return list( self._nested_object_names )
        
    
    def SetNestedObjectNames( self, nested_object_names: typing.List[ str ] ):
        
        self._nested_object_names = list( nested_object_names )
        
    
    def ToString( self ) -> str:
        
        suffix_s = '' if self._suffix == '' else '.{}'.format( self._suffix )
        
        non_s = '' if len( self._nested_object_names ) == 0 else ' ({})'.format( '>'.join( self._nested_object_names ) )
        
        return 'to {}.json sidecar{}'.format( suffix_s, non_s )
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_METADATA_SINGLE_FILE_EXPORTER_JSON ] = SingleFileMetadataExporterJSON

class SingleFileMetadataExporterTXT( HydrusSerialisable.SerialisableBase, SingleFileMetadataExporterSidecar ):
    
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
            
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        SingleFileMetadataExporterSidecar.__init__( self, remove_actual_filename_ext, suffix, filename_string_converter )
        
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
            
        
    
    def Export( self, actual_file_path: str, rows: typing.Collection[ str ] ):
        
        if len( rows ) == 0:
            
            return
            
        
        path = ClientMetadataMigrationCore.GetSidecarPath( actual_file_path, self._remove_actual_filename_ext, self._suffix, self._filename_string_converter, 'txt' )
        
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
