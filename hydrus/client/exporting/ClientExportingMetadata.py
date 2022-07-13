import os
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTags
from hydrus.core import HydrusText

from hydrus.client import ClientStrings
from hydrus.client.media import ClientMediaResult
from hydrus.client.metadata import ClientTags

def GetSidecarPath( actual_file_path: str, suffix: str, file_extension: str ):
    
    path_components = [ actual_file_path ]
    
    if suffix != '':
        
        path_components.append( suffix )
        
    
    path_components.append( file_extension )
    
    return '.'.join( path_components )
    

class SingleFileMetadataExporterMedia( object ):
    
    def Export( self, hash: bytes, rows: typing.Collection[ str ] ):
        
        raise NotImplementedError()
        
    

class SingleFileMetadataImporterMedia( object ):
    
    def Import( self, media_result: ClientMediaResult.MediaResult ):
        
        raise NotImplementedError()
        
    

class SingleFileMetadataExporterSidecar( object ):
    
    def Export( self, actual_file_path: str, rows: typing.Collection[ str ] ):
        
        raise NotImplementedError()
        
    

class SingleFileMetadataImporterSidecar( object ):
    
    def Import( self, actual_file_path: str ):
        
        raise NotImplementedError()
        
    

# TODO: add ToString and any other stuff here so this can all show itself prettily in a listbox
# 'I grab a .reversotags.txt sidecar and reverse the text and then send it as tags to my tags'

class SingleFileMetadataRouter( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_METADATA_SINGLE_FILE_ROUTER
    SERIALISABLE_NAME = 'Metadata Single File Converter'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, importers = None, string_processor = None, exporter = None ):
        
        if importers is None:
            
            importers = []
            
        
        if string_processor is None:
            
            string_processor = ClientStrings.StringProcessor()
            
        
        if exporter is None:
            
            exporter = SingleFileMetadataImporterExporterTXT()
            
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._importers = HydrusSerialisable.SerialisableList( importers )
        self._string_processor = string_processor
        self._exporter = exporter
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_importers = self._importers.GetSerialisableTuple()
        serialisable_string_processor = self._string_processor.GetSerialisableTuple()
        serialisable_exporter = self._exporter.GetSerialisableTuple()
        
        return ( serialisable_importers, serialisable_string_processor, serialisable_exporter )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_importers, serialisable_string_processor, serialisable_exporter ) = serialisable_info
        
        self._importers = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_importers )
        self._string_processor = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_string_processor )
        self._exporter = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_exporter )
        
    
    def GetExporter( self ):
        
        return self._exporter
        
    
    def GetImportedSidecarTexts( self, file_path: str, and_process_them = True ):
        
        rows = set()
        
        for importer in self._importers:
            
            if isinstance( importer, SingleFileMetadataImporterSidecar ):
                
                rows.update( importer.Import( file_path ) )
                
            else:
                
                raise Exception( 'This convertor does not import from a sidecar!' )
                
            
        
        rows = sorted( rows, key = HydrusTags.ConvertTagToSortable )
        
        if and_process_them:
            
            rows = self._string_processor.ProcessStrings( starting_strings = rows )
            
        
        return rows
        
    
    def GetImporters( self ):
        
        return self._importers
        
    
    def Work( self, media_result: ClientMediaResult.MediaResult, file_path: str ):
        
        rows = set()
        
        for importer in self._importers:
            
            if isinstance( importer, SingleFileMetadataImporterSidecar ):
                
                rows.update( importer.Import( file_path ) )
                
            elif isinstance( importer, SingleFileMetadataImporterMedia ):
                
                rows.update( importer.Import( media_result ) )
                
            else:
                
                raise Exception( 'Problem with importer object!' )
                
            
        
        rows = sorted( rows, key = HydrusTags.ConvertTagToSortable )
        
        rows = self._string_processor.ProcessStrings( starting_strings = rows )
        
        if len( rows ) == 0:
            
            return
            
        
        if isinstance( self._exporter, SingleFileMetadataExporterSidecar ):
            
            self._exporter.Export( file_path, rows )
            
        elif isinstance( self._exporter, SingleFileMetadataExporterMedia ):
            
            self._exporter.Export( media_result.GetHash(), rows )
            
        else:
            
            raise Exception( 'Problem with exporter object!' )
            
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_METADATA_SINGLE_FILE_ROUTER ] = SingleFileMetadataRouter

class SingleFileMetadataImporterExporterMediaTags( HydrusSerialisable.SerialisableBase, SingleFileMetadataExporterMedia, SingleFileMetadataImporterMedia ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_METADATA_SINGLE_FILE_IMPORTER_EXPORTER_MEDIA_TAGS
    SERIALISABLE_NAME = 'Metadata Single File Importer Exporter Media Tags'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, service_key = None ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        SingleFileMetadataExporterMedia.__init__( self )
        SingleFileMetadataImporterMedia.__init__( self )
        
        self._service_key = service_key
        
    
    def _GetSerialisableInfo( self ):
        
        return self._service_key.hex()
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        serialisable_service_key = serialisable_info
        
        self._service_key = bytes.fromhex( serialisable_service_key )
        
    
    def GetServiceKey( self ) -> bytes:
        
        return self._service_key
        
    
    def Import( self, media_result: ClientMediaResult.MediaResult ):
        
        tags = media_result.GetTagsManager().GetCurrent( self._service_key, ClientTags.TAG_DISPLAY_STORAGE )
        
        return tags
        
    
    def Export( self, hash: bytes, rows: typing.Collection[ str ] ):
        
        if HG.client_controller.services_manager.GetServiceType( self._service_key ) == HC.LOCAL_TAG:
            
            add_content_action = HC.CONTENT_UPDATE_ADD
            
        else:
            
            add_content_action = HC.CONTENT_UPDATE_PEND
            
        
        hashes = { hash }
        
        content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, add_content_action, ( tag, hashes ) ) for tag in rows ]
        
        HG.client_controller.WriteSynchronous( 'content_updates', { self._service_key : content_updates } )
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_METADATA_SINGLE_FILE_IMPORTER_EXPORTER_MEDIA_TAGS ] = SingleFileMetadataImporterExporterMediaTags

class SingleFileMetadataImporterExporterTXT( HydrusSerialisable.SerialisableBase, SingleFileMetadataExporterSidecar, SingleFileMetadataImporterSidecar ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_METADATA_SINGLE_FILE_IMPORTER_EXPORTER_TXT
    SERIALISABLE_NAME = 'Metadata Single File Importer Exporter TXT'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, suffix = None ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        SingleFileMetadataExporterSidecar.__init__( self )
        SingleFileMetadataImporterSidecar.__init__( self )
        
        if suffix is None:
            
            suffix = ''
            
        
        self._suffix = suffix
        
    
    def _GetSerialisableInfo( self ):
        
        return self._suffix
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        self._suffix = serialisable_info
        
    
    def Export( self, actual_file_path: str, rows: typing.Collection[ str ] ):
        
        path = GetSidecarPath( actual_file_path, self._suffix, 'txt' )
        
        with open( path, 'w', encoding = 'utf-8' ) as f:
            
            f.write( '\n'.join( rows ) )
            
        
    
    def Import( self, actual_file_path: str ) -> typing.Collection[ str ]:
        
        path = GetSidecarPath( actual_file_path, self._suffix, 'txt' )
        
        if not os.path.exists( path ):
            
            return []
            
        
        try:
            
            with open( path, 'r', encoding = 'utf-8' ) as f:
                
                raw_text = f.read()
                
            
        except Exception as e:
            
            raise Exception( 'Could not import from {}: {}'.format( path, str( e ) ) )
            
        
        rows = HydrusText.DeserialiseNewlinedTexts( raw_text )
        
        return rows
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_METADATA_SINGLE_FILE_IMPORTER_EXPORTER_TXT ] = SingleFileMetadataImporterExporterTXT
