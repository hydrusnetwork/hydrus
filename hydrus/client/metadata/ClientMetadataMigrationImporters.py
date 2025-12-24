import collections.abc
import os

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusLists
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusText
from hydrus.core import HydrusTime

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientStrings
from hydrus.client import ClientTime
from hydrus.client.media import ClientMediaResult
from hydrus.client.metadata import ClientMetadataMigrationCore
from hydrus.client.metadata import ClientTags
from hydrus.client.parsing import ClientParsing

# TODO: All importers should probably have a string processor

class SingleFileMetadataImporter( ClientMetadataMigrationCore.ImporterExporterNode ):
    
    def __init__( self, string_processor: ClientStrings.StringProcessor, *args, **kwargs ):
        
        self._string_processor = string_processor
        
        super().__init__( *args, **kwargs )
        
    
    def GetStringProcessor( self ) -> ClientStrings.StringProcessor:
        
        return self._string_processor
        
    
    def Import( self, *args, **kwargs ) -> list[ str ]:
        
        rows = self.ImportSansStringProcessing( *args, **kwargs )
        
        if self._string_processor.MakesChanges():
            
            rows = self._string_processor.ProcessStrings( rows )
            
        
        return rows
        
    
    def ImportSansStringProcessing( self, *args, **kwargs ) -> list[ str ]:
        
        raise NotImplementedError()
        
    
    def ToString( self ) -> str:
        
        raise NotImplementedError()
        
    

class SingleFileMetadataImporterMedia( SingleFileMetadataImporter ):
    
    def Import( self, media_result: ClientMediaResult.MediaResult ) -> list[ str ]:
        
        return super().Import( media_result )
        
    
    def ImportSansStringProcessing( self, media_result: ClientMediaResult.MediaResult ) -> list[ str ]:
        
        return super().ImportSansStringProcessing( media_result )
        
    
    def ToString( self ) -> str:
        
        raise NotImplementedError()
        
    

class SingleFileMetadataImporterMediaNotes( SingleFileMetadataImporterMedia, HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_METADATA_SINGLE_FILE_IMPORTER_MEDIA_NOTES
    SERIALISABLE_NAME = 'Metadata Single File Importer Media Notes'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, string_processor: ClientStrings.StringProcessor | None = None ):
        
        if string_processor is None:
            
            string_processor = ClientStrings.StringProcessor()
            
        
        super().__init__( string_processor )
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_string_processor = self._string_processor.GetSerialisableTuple()
        
        return serialisable_string_processor
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        serialisable_string_processor = serialisable_info
        
        self._string_processor = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_string_processor )
        
    
    def GetExampleStrings( self ):
        
        examples = [
            'Artist Commentary: This work is one of my favourites.',
            'Translation: "What a nice day!"'
        ]
        
        return examples
        
    
    def ImportSansStringProcessing( self, media_result: ClientMediaResult.MediaResult ) -> list[ str ]:
        
        names_to_notes = media_result.GetNotesManager().GetNamesToNotes()
        
        rows = [ '{}{}{}'.format( name.replace( ClientMetadataMigrationCore.NOTE_CONNECTOR_STRING, ClientMetadataMigrationCore.NOTE_NAME_ESCAPE_STRING ), ClientMetadataMigrationCore.NOTE_CONNECTOR_STRING, text ) for ( name, text ) in names_to_notes.items() ]
        
        return rows
        
    
    def ToString( self ) -> str:
        
        if self._string_processor.MakesChanges():
            
            full_munge_text = ', applying {}'.format( self._string_processor.ToString() )
            
        else:
            
            full_munge_text = ''
            
        
        return 'notes from media{}'.format( full_munge_text )
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_METADATA_SINGLE_FILE_IMPORTER_MEDIA_NOTES ] = SingleFileMetadataImporterMediaNotes

class SingleFileMetadataImporterMediaTags( SingleFileMetadataImporterMedia, HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_METADATA_SINGLE_FILE_IMPORTER_MEDIA_TAGS
    SERIALISABLE_NAME = 'Metadata Single File Importer Media Tags'
    SERIALISABLE_VERSION = 3
    
    def __init__( self, string_processor = None, service_key = None, tag_display_type = None ):
        
        if string_processor is None:
            
            string_processor = ClientStrings.StringProcessor()
            
        
        super().__init__( string_processor )
        
        if service_key is None:
            
            service_key = CC.COMBINED_TAG_SERVICE_KEY
            
        
        if tag_display_type is None:
            
            tag_display_type = ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL
            
        
        self._tag_display_type = tag_display_type
        self._service_key = service_key
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_string_processor = self._string_processor.GetSerialisableTuple()
        serialisable_service_key = self._service_key.hex()
        
        return ( serialisable_string_processor, serialisable_service_key, self._tag_display_type )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_string_processor, serialisable_service_key, self._tag_display_type ) = serialisable_info
        
        self._string_processor = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_string_processor )
        self._service_key = bytes.fromhex( serialisable_service_key )
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            serialisable_service_key = old_serialisable_info
            
            string_processor = ClientStrings.StringProcessor()
            
            serialisable_string_processor = string_processor.GetSerialisableTuple()
            
            new_serialisable_info = ( serialisable_string_processor, serialisable_service_key )
            
            return ( 2, new_serialisable_info )
            
        
        if version == 2:
            
            ( serialisable_string_processor, serialisable_service_key ) = old_serialisable_info
            
            tag_display_type = ClientTags.TAG_DISPLAY_STORAGE
            
            new_serialisable_info = ( serialisable_string_processor, serialisable_service_key, tag_display_type )
            
            return ( 3, new_serialisable_info )
            
        
    
    def GetExampleStrings( self ):
        
        examples = [
            'blue eyes',
            'blonde hair',
            'skirt',
            'character:jane smith',
            'creator:some guy'
        ]
        
        if self._tag_display_type == ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL:
            
            examples.append( 'series:jane smith adventures' )
            
        
        return examples
        
    
    def GetServiceKey( self ) -> bytes:
        
        return self._service_key
        
    
    def GetTagDisplayType( self ) -> int:
        
        return self._tag_display_type
        
    
    def ImportSansStringProcessing( self, media_result: ClientMediaResult.MediaResult ) -> list[ str ]:
        
        tags = media_result.GetTagsManager().GetCurrent( self._service_key, self._tag_display_type )
        
        # turning ::) into :)
        tags = [ HydrusText.re_leading_double_colon.sub( ':', tag ) for tag in tags ]
        
        tags = HydrusLists.DedupeList( tags )
        
        HydrusText.HumanTextSort( tags )
        
        return tags
        
    
    def SetServiceKey( self, service_key: bytes ):
        
        self._service_key = service_key
        
    
    def ToString( self ) -> str:
        
        try:
            
            name = CG.client_controller.services_manager.GetName( self._service_key )
            
        except:
            
            name = 'unknown service'
            
        
        if self._string_processor.MakesChanges():
            
            full_munge_text = ', applying {}'.format( self._string_processor.ToString() )
            
        else:
            
            full_munge_text = ''
            
        
        return f'"{name}" {ClientTags.tag_display_str_lookup[ self._tag_display_type ]}{full_munge_text}'
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_METADATA_SINGLE_FILE_IMPORTER_MEDIA_TAGS ] = SingleFileMetadataImporterMediaTags

class SingleFileMetadataImporterMediaTimestamps( SingleFileMetadataImporterMedia, HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_METADATA_SINGLE_FILE_IMPORTER_MEDIA_TIMESTAMPS
    SERIALISABLE_NAME = 'Metadata Single File Importer Media Timestamps'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, string_processor = None, timestamp_data_stub = None ):
        
        if string_processor is None:
            
            string_processor = ClientStrings.StringProcessor()
            
        
        super().__init__( string_processor )
        
        if timestamp_data_stub is None:
            
            timestamp_data_stub = ClientTime.TimestampData.STATICSimpleStub( HC.TIMESTAMP_TYPE_ARCHIVED )
            
        
        self._timestamp_data_stub = timestamp_data_stub
        
    
    def _GetSerialisableInfo( self ):
    
        serialisable_string_processor = self._string_processor.GetSerialisableTuple()
        serialisable_timestamp_data_stub = self._timestamp_data_stub.GetSerialisableTuple()
        
        return ( serialisable_string_processor, serialisable_timestamp_data_stub )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_string_processor, serialisable_timestamp_data_stub ) = serialisable_info
        
        self._string_processor = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_string_processor )
        self._timestamp_data_stub = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_timestamp_data_stub )
        
    
    def GetExampleStrings( self ):
        
        examples = [
            '1681682717'
        ]
        
        return examples
        
    
    def GetTimestampDataStub( self ) -> ClientTime.TimestampData:
        
        return self._timestamp_data_stub
        
    
    def ImportSansStringProcessing( self, media_result: ClientMediaResult.MediaResult ) -> list[ str ]:
        
        rows = []
        
        timestamp = HydrusTime.SecondiseMS( media_result.GetTimesManager().GetTimestampMSFromStub( self._timestamp_data_stub ) )
        
        if timestamp is not None:
            
            rows.append( str( timestamp ) )
            
        
        return rows
        
    
    def SetTimestampDataStub( self, timestamp_data_stub: ClientTime.TimestampData ):
        
        self._timestamp_data_stub = timestamp_data_stub
        
    
    def ToString( self ) -> str:
        
        if self._string_processor.MakesChanges():
            
            full_munge_text = ', applying {}'.format( self._string_processor.ToString() )
            
        else:
            
            full_munge_text = ''
            
        
        return '{} from media{}'.format( self._timestamp_data_stub, full_munge_text )
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_METADATA_SINGLE_FILE_IMPORTER_MEDIA_TIMESTAMPS ] = SingleFileMetadataImporterMediaTimestamps

class SingleFileMetadataImporterMediaURLs( SingleFileMetadataImporterMedia, HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_METADATA_SINGLE_FILE_IMPORTER_MEDIA_URLS
    SERIALISABLE_NAME = 'Metadata Single File Importer Media URLs'
    SERIALISABLE_VERSION = 2
    
    def __init__( self, string_processor = None ):
        
        if string_processor is None:
            
            string_processor = ClientStrings.StringProcessor()
            
        
        super().__init__( string_processor )
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_string_processor = self._string_processor.GetSerialisableTuple()
        
        return serialisable_string_processor
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        serialisable_string_processor = serialisable_info
        
        self._string_processor = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_string_processor )
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            gumpf = old_serialisable_info
            
            string_processor = ClientStrings.StringProcessor()
            
            serialisable_string_processor = string_processor.GetSerialisableTuple()
            
            new_serialisable_info = serialisable_string_processor
            
            return ( 2, new_serialisable_info )
            
        
    
    def GetExampleStrings( self ):
        
        examples = [
            'https://example.com/gallery/index.php?post=123456&page=show',
            'https://cdn3.expl.com/files/file_id?id=123456&token=0123456789abcdef'
        ]
        
        return examples
        
    
    def ImportSansStringProcessing( self, media_result: ClientMediaResult.MediaResult ) -> list[ str ]:
        
        urls = sorted( media_result.GetLocationsManager().GetURLs() )
        
        return urls
        
    
    def ToString( self ) -> str:
        
        if self._string_processor.MakesChanges():
            
            full_munge_text = ', applying {}'.format( self._string_processor.ToString() )
            
        else:
            
            full_munge_text = ''
            
        
        return 'urls from media{}'.format( full_munge_text )
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_METADATA_SINGLE_FILE_IMPORTER_MEDIA_URLS ] = SingleFileMetadataImporterMediaURLs

class SingleFileMetadataImporterSidecar( SingleFileMetadataImporter, ClientMetadataMigrationCore.SidecarNode ):
    
    def __init__( self, string_processor: ClientStrings.StringProcessor, remove_actual_filename_ext: bool, suffix: str, filename_string_converter: ClientStrings.StringConverter ):
        
        super().__init__( string_processor, remove_actual_filename_ext, suffix, filename_string_converter )
        
    
    def GetPossibleSidecarPaths( self, path: str ) -> collections.abc.Collection[ str ]:
        
        raise NotImplementedError()
        
    
    def GetSidecarPath( self, actual_file_path ) -> str | None:
        
        possible_paths = self.GetPossibleSidecarPaths( actual_file_path )
        
        for path in possible_paths:
            
            if os.path.exists( path ):
                
                return path
                
            
        
        return None
        
    
    def Import( self, actual_file_path: str ) -> list[ str ]:
        
        return super().Import( actual_file_path )
        
    
    def ImportSansStringProcessing( self, actual_file_path: str ) -> list[ str ]:
        
        return super().ImportSansStringProcessing( actual_file_path )
        
    
    def ToString( self ) -> str:
        
        raise NotImplementedError()
        
    

class SingleFileMetadataImporterJSON( SingleFileMetadataImporterSidecar, HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_METADATA_SINGLE_FILE_IMPORTER_JSON
    SERIALISABLE_NAME = 'Metadata Single File Importer JSON'
    SERIALISABLE_VERSION = 3
    
    def __init__( self, string_processor = None, remove_actual_filename_ext = None, suffix = None, filename_string_converter = None, json_parsing_formula = None ):
        
        if remove_actual_filename_ext is None:
            
            remove_actual_filename_ext = False
            
        
        if suffix is None:
            
            suffix = ''
            
        
        if filename_string_converter is None:
            
            filename_string_converter = ClientStrings.StringConverter( example_string = 'my_image.jpg.json' )
            
        
        if string_processor is None:
            
            string_processor = ClientStrings.StringProcessor()
            
        
        super().__init__( string_processor, remove_actual_filename_ext, suffix, filename_string_converter )
        
        if json_parsing_formula is None:
            
            parse_rules = [ ( ClientParsing.JSON_PARSE_RULE_TYPE_ALL_ITEMS, None ) ]
            
            json_parsing_formula = ClientParsing.ParseFormulaJSON( parse_rules = parse_rules, content_to_fetch = ClientParsing.JSON_CONTENT_STRING )
            
        
        self._json_parsing_formula = json_parsing_formula
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_string_processor = self._string_processor.GetSerialisableTuple()
        serialisable_filename_string_converter = self._filename_string_converter.GetSerialisableTuple()
        serialisable_json_parsing_formula = self._json_parsing_formula.GetSerialisableTuple()
        
        return ( serialisable_string_processor, self._remove_actual_filename_ext, self._suffix, serialisable_filename_string_converter, serialisable_json_parsing_formula )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
    
        ( serialisable_string_processor, self._remove_actual_filename_ext, self._suffix, serialisable_filename_string_converter, serialisable_json_parsing_formula ) = serialisable_info
        
        self._string_processor = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_string_processor )
        self._filename_string_converter = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_filename_string_converter )
        self._json_parsing_formula = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_json_parsing_formula )
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( suffix, serialisable_json_parsing_formula ) = old_serialisable_info
            
            string_processor = ClientStrings.StringProcessor()
            
            serialisable_string_processor = string_processor.GetSerialisableTuple()
            
            new_serialisable_info = ( serialisable_string_processor, suffix, serialisable_json_parsing_formula )
            
            return ( 2, new_serialisable_info )
            
        
        if version == 2:
            
            ( serialisable_string_processor, suffix, serialisable_json_parsing_formula ) = old_serialisable_info
            
            remove_actual_filename_ext = False
            filename_string_converter = ClientStrings.StringConverter( example_string = 'my_image.jpg.json' )
            
            serialisable_filename_string_converter = filename_string_converter.GetSerialisableTuple()
            
            new_serialisable_info = ( serialisable_string_processor, remove_actual_filename_ext, suffix, serialisable_filename_string_converter, serialisable_json_parsing_formula )
            
            return ( 3, new_serialisable_info )
            
        
    
    def GetPossibleSidecarPaths( self, actual_file_path: str ) -> collections.abc.Collection[ str ]:
        
        return [
            ClientMetadataMigrationCore.GetSidecarPath( actual_file_path, self._remove_actual_filename_ext, self._suffix, self._filename_string_converter, 'json' ),
            ClientMetadataMigrationCore.GetSidecarPath( actual_file_path, self._remove_actual_filename_ext, self._suffix, self._filename_string_converter, 'JSON' )
        ]
        
    
    def GetJSONParsingFormula( self ) -> ClientParsing.ParseFormulaJSON:
        
        return self._json_parsing_formula
        
    
    def ImportSansStringProcessing( self, actual_file_path: str ) -> list[ str ]:
        
        path = self.GetSidecarPath( actual_file_path )
        
        if path is None:
            
            return []
            
        
        try:
            
            with open( path, 'r', encoding = 'utf-8' ) as f:
                
                read_raw_json = f.read()
                
            
        except Exception as e:
            
            raise Exception( f'Could not import from {path} (from file path {actual_file_path}: {e}' )
            
        
        parsing_context = {}
        collapse_newlines = False
        
        rows = self._json_parsing_formula.Parse( parsing_context, read_raw_json, collapse_newlines )
        
        return rows
        
    
    def SetJSONParsingFormula( self, json_parsing_formula: ClientParsing.ParseFormulaJSON ):
        
        self._json_parsing_formula = json_parsing_formula
        
    
    def ToString( self ) -> str:
        
        if self._string_processor.MakesChanges():
            
            full_munge_text = ', applying {}'.format( self._string_processor.ToString() )
            
        else:
            
            full_munge_text = ''
            
        
        return 'from JSON sidecar{}'.format( full_munge_text )
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_METADATA_SINGLE_FILE_IMPORTER_JSON ] = SingleFileMetadataImporterJSON

class SingleFileMetadataImporterTXT( SingleFileMetadataImporterSidecar, HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_METADATA_SINGLE_FILE_IMPORTER_TXT
    SERIALISABLE_NAME = 'Metadata Single File Importer TXT'
    SERIALISABLE_VERSION = 4
    
    def __init__( self, string_processor = None, remove_actual_filename_ext = None, suffix = None, filename_string_converter = None, separator = None ):
        
        if remove_actual_filename_ext is None:
            
            remove_actual_filename_ext = False
            
        
        if suffix is None:
            
            suffix = ''
            
        
        if filename_string_converter is None:
            
            filename_string_converter = ClientStrings.StringConverter( example_string = 'my_image.jpg.txt' )
            
        
        if string_processor is None:
            
            string_processor = ClientStrings.StringProcessor()
            
        
        if separator is None:
            
            separator = '\n'
            
        
        super().__init__( string_processor, remove_actual_filename_ext, suffix, filename_string_converter )
        
        self._separator = separator
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_string_processor = self._string_processor.GetSerialisableTuple()
        serialisable_filename_string_converter = self._filename_string_converter.GetSerialisableTuple()
        
        return ( serialisable_string_processor, self._remove_actual_filename_ext, self._suffix, serialisable_filename_string_converter, self._separator )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
    
        ( serialisable_string_processor, self._remove_actual_filename_ext, self._suffix, serialisable_filename_string_converter, self._separator ) = serialisable_info
        
        self._string_processor = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_string_processor )
        self._filename_string_converter = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_filename_string_converter )
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            suffix = old_serialisable_info
            
            string_processor = ClientStrings.StringProcessor()
            
            serialisable_string_processor = string_processor.GetSerialisableTuple()
            
            new_serialisable_info = ( serialisable_string_processor, suffix )
            
            return ( 2, new_serialisable_info )
            
        
        if version == 2:
            
            ( serialisable_string_processor, suffix ) = old_serialisable_info
            
            remove_actual_filename_ext = False
            filename_string_converter = ClientStrings.StringConverter( example_string = 'my_image.jpg.txt' )
            
            serialisable_filename_string_converter = filename_string_converter.GetSerialisableTuple()
            
            new_serialisable_info = ( serialisable_string_processor, remove_actual_filename_ext, suffix, serialisable_filename_string_converter )
            
            return ( 3, new_serialisable_info )
            
        
        if version == 3:
            
            ( serialisable_string_processor, remove_actual_filename_ext, suffix, serialisable_filename_string_converter ) = old_serialisable_info
            
            separator = '\n'
            
            new_serialisable_info = ( serialisable_string_processor, remove_actual_filename_ext, suffix, serialisable_filename_string_converter, separator )
            
            return ( 4, new_serialisable_info )
            
        
    
    def GetPossibleSidecarPaths( self, actual_file_path: str ) -> collections.abc.Collection[ str ]:
        
        return [
            ClientMetadataMigrationCore.GetSidecarPath( actual_file_path, self._remove_actual_filename_ext, self._suffix, self._filename_string_converter, 'txt' ),
            ClientMetadataMigrationCore.GetSidecarPath( actual_file_path, self._remove_actual_filename_ext, self._suffix, self._filename_string_converter, 'TXT' )
        ]
        
    
    def GetSeparator( self ) -> str:
        
        return self._separator
        
    
    def ImportSansStringProcessing( self, actual_file_path: str ) -> list[ str ]:
        
        path = self.GetSidecarPath( actual_file_path )
        
        if path is None:
            
            return []
            
        
        try:
            
            with open( path, 'r', encoding = 'utf-8' ) as f:
                
                raw_text = f.read()
                
            
        except Exception as e:
            
            raise Exception( f'Could not import from {path} (from file path {actual_file_path}: {e}' )
            
        
        raw_text = HydrusText.CleanseImportText( raw_text )
        
        if self._separator == '\n':
            
            rows = raw_text.splitlines()
            
        else:
            
            rows = raw_text.split( self._separator )
            
        
        return rows
        
    
    def SetSeparator( self, separator: str ):
        
        self._separator = separator
        
    
    def ToString( self ) -> str:
        
        if self._string_processor.MakesChanges():
            
            full_munge_text = ', applying {}'.format( self._string_processor.ToString() )
            
        else:
            
            full_munge_text = ''
            
        
        return 'from .txt sidecar{}'.format( full_munge_text )
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_METADATA_SINGLE_FILE_IMPORTER_TXT ] = SingleFileMetadataImporterTXT
