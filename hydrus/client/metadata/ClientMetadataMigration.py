import collections.abc

from hydrus.core import HydrusLists
from hydrus.core import HydrusSerialisable

from hydrus.client import ClientStrings
from hydrus.client.media import ClientMediaResult
from hydrus.client.metadata import ClientMetadataMigrationExporters
from hydrus.client.metadata import ClientMetadataMigrationImporters

class SingleFileMetadataRouter( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_METADATA_SINGLE_FILE_ROUTER
    SERIALISABLE_NAME = 'Metadata Single File Router'
    SERIALISABLE_VERSION = 3
    
    def __init__(
        self,
        importers: collections.abc.Collection[ ClientMetadataMigrationImporters.SingleFileMetadataImporter ] | None = None,
        string_processor: ClientStrings.StringProcessor | None = None,
        exporter: ClientMetadataMigrationExporters.SingleFileMetadataExporter | None = None
    ):
        
        if importers is None:
            
            importers = []
            
        
        if string_processor is None:
            
            string_processor = ClientStrings.StringProcessor()
            
            string_processor.SetProcessingSteps(
                [
                    ClientStrings.StringSorter(
                        sort_type = ClientStrings.CONTENT_PARSER_SORT_TYPE_HUMAN_SORT,
                        asc = True
                    )
                ]
            )
            
        
        if exporter is None:
            
            exporter = ClientMetadataMigrationExporters.SingleFileMetadataExporterTXT()
            
        
        super().__init__()
        
        self._importers = HydrusSerialisable.SerialisableList( importers )
        self._string_processor = string_processor
        self._exporter = exporter
        
    
    def __str__( self ):
        
        return self.ToString()
        
    
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
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            # in this version, we are moving from importer/exporter combined classes to separate. the importer/exporters are becoming importers, so importer/exporters in export slot need to be remade
            
            ( serialisable_importers, serialisable_string_processor, serialisable_exporter ) = old_serialisable_info
            
            actually_an_importer = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_exporter )
            
            if isinstance( actually_an_importer, ClientMetadataMigrationImporters.SingleFileMetadataImporterTXT ):
                
                suffix = actually_an_importer.GetSuffix()
                
                exporter = ClientMetadataMigrationExporters.SingleFileMetadataExporterTXT( suffix = suffix )
                
            elif isinstance( actually_an_importer, ClientMetadataMigrationImporters.SingleFileMetadataImporterMediaTags ):
                
                service_key = actually_an_importer.GetServiceKey()
                
                exporter = ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaTags( service_key )
                
            else:
                
                exporter = ClientMetadataMigrationExporters.SingleFileMetadataExporterTXT()
                
            
            fixed_serialisable_exporter = exporter.GetSerialisableTuple()
            
            new_serialisable_info = ( serialisable_importers, serialisable_string_processor, fixed_serialisable_exporter )
            
            return ( 2, new_serialisable_info )
            
        
        if version == 2:
            
            # removing hardcoded sort in the Work call; now letting user handle it
            
            ( serialisable_importers, serialisable_string_processor, serialisable_exporter ) = old_serialisable_info
            
            string_processor = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_string_processor )
            
            string_processing_steps = string_processor.GetProcessingSteps()
            
            string_processing_steps.append(
                ClientStrings.StringSorter(
                    sort_type = ClientStrings.CONTENT_PARSER_SORT_TYPE_HUMAN_SORT,
                    asc = True
                )
            )
            
            string_processor.SetProcessingSteps( string_processing_steps )
            
            serialisable_string_processor = string_processor.GetSerialisableTuple()
            
            new_serialisable_info = ( serialisable_importers, serialisable_string_processor, serialisable_exporter )
            
            return ( 3, new_serialisable_info )
            
        
    
    def GetExporter( self ) -> ClientMetadataMigrationExporters.SingleFileMetadataExporter:
        
        return self._exporter
        
    
    def GetImporters( self ) -> list[ ClientMetadataMigrationImporters.SingleFileMetadataImporter ]:
        
        return list( self._importers )
        
    
    def GetPossibleImporterSidecarPaths( self, path ):
        
        sidecar_importers = [ importer for importer in self._importers if isinstance( importer, ClientMetadataMigrationImporters.SingleFileMetadataImporterSidecar ) ]
        
        possible_sidecar_paths = set()
        
        for importer in sidecar_importers:
            
            possible_sidecar_paths.update( importer.GetPossibleSidecarPaths( path ) )
            
        
        return possible_sidecar_paths
        
    
    def GetStringProcessor( self ) -> ClientStrings.StringProcessor:
        
        return self._string_processor
        
    
    def ToString( self, pretty = False ) -> str:
        
        if len( self._importers ) > 0:
            
            source_text = ', '.join( ( importer.ToString() for importer in self._importers ) )
            
        else:
            
            source_text = 'nothing'
            
        
        if self._string_processor.MakesChanges():
            
            full_munge_text = ', applying {}'.format( self._string_processor.ToString() )
            
        else:
            
            full_munge_text = ''
            
        
        dest_text = self._exporter.ToString()
        
        if pretty:
            
            header = ''
            
        else:
            
            header = 'Single File Metadata Router: '
            
        
        return '{}Taking {}{}, sending {}.'.format( header, source_text, full_munge_text, dest_text )
        
    
    def Work( self, media_result: ClientMediaResult.MediaResult, file_path: str ) -> bool:
        
        rows = []
        
        for importer in self._importers:
            
            if isinstance( importer, ClientMetadataMigrationImporters.SingleFileMetadataImporterSidecar ):
                
                rows.extend( importer.Import( file_path ) )
                
            elif isinstance( importer, ClientMetadataMigrationImporters.SingleFileMetadataImporterMedia ):
                
                rows.extend( importer.Import( media_result ) )
                
            else:
                
                raise Exception( 'Problem with importer object!' )
                
            
        
        rows = HydrusLists.DedupeList( rows )
        
        rows = self._string_processor.ProcessStrings( starting_strings = rows )
        
        if len( rows ) == 0:
            
            return False
            
        
        if isinstance( self._exporter, ClientMetadataMigrationExporters.SingleFileMetadataExporterSidecar ):
            
            self._exporter.Export( file_path, rows )
            
        elif isinstance( self._exporter, ClientMetadataMigrationExporters.SingleFileMetadataExporterMedia ):
            
            self._exporter.Export( media_result.GetHash(), rows )
            
        else:
            
            raise Exception( 'Problem with exporter object!' )
            
        
        return True
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_METADATA_SINGLE_FILE_ROUTER ] = SingleFileMetadataRouter
