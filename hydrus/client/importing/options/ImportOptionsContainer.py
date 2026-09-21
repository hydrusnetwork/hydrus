import threading
import typing

from hydrus.core import HydrusSerialisable

from hydrus.client import ClientConstants as CC
from hydrus.client.importing.options import ExternalProgramsImportOptions
from hydrus.client.importing.options import FileFilteringImportOptions
from hydrus.client.importing.options import ImportOptionsConstants as IOC
from hydrus.client.importing.options import LocationImportOptions
from hydrus.client.importing.options import NoteImportOptions
from hydrus.client.importing.options import PrefetchImportOptions
from hydrus.client.importing.options import PresentationImportOptions
from hydrus.client.importing.options import TagFilteringImportOptions
from hydrus.client.importing.options import TagImportOptions

def WeShouldWriteContentUpdatesToThisImport( status: int ):
    
    # add a user option here to prohibit on 'previously deleted'
    
    return status in CC.SUCCESSFUL_IMPORT_STATES or status == CC.STATUS_DELETED
    

class ImportOptionsContainer( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_IMPORT_OPTIONS_CONTAINER
    SERIALISABLE_NAME = 'Import Options Container'
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        super().__init__()
        
        self._import_options_types_to_import_options = HydrusSerialisable.SerialisableDictionary()
        
        self._import_option_types_to_source_labels = {}
        
        self._lock = threading.Lock()
        
    
    def _GetImportOptions( self, import_options_type: int ) -> IOC.ImportOptionsMetatype | None:
        
        result = self._import_options_types_to_import_options.get( import_options_type, None )
        
        return result
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_import_options = self._import_options_types_to_import_options.GetSerialisableTuple()
        
        return serialisable_import_options
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        serialisable_import_options = serialisable_info
        
        self._import_options_types_to_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_import_options )
        
    
    def _SetImportOptions( self, import_options: IOC.ImportOptionsMetatype, source_label: str | None = None ):
        
        import_options_type = import_options.IMPORT_OPTIONS_TYPE
        
        self._import_options_types_to_import_options[ import_options_type ] = import_options.Duplicate()
        
        if source_label is None:
            
            if import_options_type in self._import_option_types_to_source_labels:
                
                del self._import_option_types_to_source_labels[ import_options_type ]
                
            
        else:
            
            self._import_option_types_to_source_labels[ import_options_type ] = source_label
            
        
    
    def DeleteImportOptions( self, import_options_type: int ):
        
        with self._lock:
            
            if import_options_type in self._import_options_types_to_import_options:
                
                del self._import_options_types_to_import_options[ import_options_type ]
                
            
            if import_options_type in self._import_option_types_to_source_labels:
                
                del self._import_option_types_to_source_labels[ import_options_type ]
                
            
        
    
    def FillInWithThisSlice( self, import_options_container_slice: "ImportOptionsContainer", source_label: str | None = None ):
        
        with self._lock:
            
            if import_options_container_slice.IsEmpty():
                
                return
                
            
            for import_options_type in IOC.IMPORT_OPTIONS_TYPES_CANONICAL_ORDER:
                
                if self._GetImportOptions( import_options_type ) is None:
                    
                    import_options = import_options_container_slice.GetImportOptions( import_options_type )
                    
                    if import_options is not None:
                        
                        self._SetImportOptions( import_options, source_label = source_label )
                        
                    
                
            
        
    
    def OverwriteWithThisSlice( self, import_options_container_slice: "ImportOptionsContainer", source_label: str | None = None ):
        
        if import_options_container_slice.IsEmpty():
            
            return
            
        
        for import_options_type in IOC.IMPORT_OPTIONS_TYPES_CANONICAL_ORDER:
            
            import_options = import_options_container_slice.GetImportOptions( import_options_type )
            
            if import_options is not None:
                
                self._SetImportOptions( import_options, source_label = source_label )
                
            
        
    
    def GetDuplicateWithJustTheseOptionTypes( self, import_options_types: list[ int ] ):
        
        with self._lock:
            
            new_import_options_container = ImportOptionsContainer()
            
            for import_options_type in import_options_types:
                
                import_options = self._GetImportOptions( import_options_type )
                
                if import_options is not None:
                    
                    source_label = self._import_option_types_to_source_labels.get( import_options_type, None )
                    
                    new_import_options_container.SetImportOptions( import_options, source_label = source_label )
                    
                
            
        
        return new_import_options_container
        
    
    def GetExternalProgramsImportOptions( self ) -> ExternalProgramsImportOptions.ExternalProgramsImportOptions:
        
        return typing.cast( ExternalProgramsImportOptions.ExternalProgramsImportOptions, self.GetImportOptions( IOC.IMPORT_OPTIONS_TYPE_EXTERNAL_PROGRAMS ) )
        
    
    def GetFileFilteringImportOptions( self ) -> FileFilteringImportOptions.FileFilteringImportOptions:
        
        return typing.cast( FileFilteringImportOptions.FileFilteringImportOptions, self.GetImportOptions( IOC.IMPORT_OPTIONS_TYPE_FILE_FILTERING ) )
        
    
    def GetImportOptions( self, import_options_type: int ) -> IOC.ImportOptionsMetatype | None:
        
        with self._lock:
            
            return self._GetImportOptions( import_options_type )
            
        
    
    def GetLocationImportOptions( self ) -> LocationImportOptions.LocationImportOptions:
        
        return typing.cast( LocationImportOptions.LocationImportOptions, self.GetImportOptions( IOC.IMPORT_OPTIONS_TYPE_LOCATIONS ) )
        
    
    def GetNoteImportOptions( self ) -> NoteImportOptions.NoteImportOptions:
        
        return typing.cast( NoteImportOptions.NoteImportOptions, self.GetImportOptions( IOC.IMPORT_OPTIONS_TYPE_NOTES ) )
        
    
    def GetPrefetchImportOptions( self ) -> PrefetchImportOptions.PrefetchImportOptions:
        
        return typing.cast( PrefetchImportOptions.PrefetchImportOptions, self.GetImportOptions( IOC.IMPORT_OPTIONS_TYPE_PREFETCH ) )
        
    
    def GetPresentationImportOptions( self ) -> PresentationImportOptions.PresentationImportOptions:
        
        return typing.cast( PresentationImportOptions.PresentationImportOptions, self.GetImportOptions( IOC.IMPORT_OPTIONS_TYPE_PRESENTATION ) )
        
    
    def GetSourceLabel( self, import_options_type: int ) -> str:
        
        with self._lock:
            
            default_label = 'global'
            
            return self._import_option_types_to_source_labels.get( import_options_type, default_label )
            
        
    
    def GetSummary( self, import_options_caller_type: int ):
        
        with self._lock:
            
            short_summary_components = []
            long_summary_components = []
            
            for import_options_type in IOC.IMPORT_OPTIONS_TYPES_CANONICAL_ORDER:
                
                if import_options_type in self._import_options_types_to_import_options:
                    
                    short_summary_components.append( IOC.import_options_type_str_lookup[ import_options_type ] )
                    long_summary_components.append( self._import_options_types_to_import_options[ import_options_type ].GetSummary( import_options_caller_type ) )
                    
                
            
        
        long_summary_components = [ item for item in long_summary_components if item != '' ]
        
        if len( short_summary_components ) == 0:
            
            return ''
            
        else:
            
            if len( short_summary_components ) <= 2 and 1 <= len( long_summary_components ) <= 2:
                
                return ', '.join( short_summary_components ) + ': ' + ' | '.join( long_summary_components )
                
            else:
                
                return ', '.join( short_summary_components )
                
            
        
    
    def GetTagFilteringImportOptions( self ) -> TagFilteringImportOptions.TagFilteringImportOptions:
        
        return typing.cast( TagFilteringImportOptions.TagFilteringImportOptions, self.GetImportOptions( IOC.IMPORT_OPTIONS_TYPE_TAG_FILTERING ) )
        
    
    def GetTagImportOptions( self ) -> TagImportOptions.TagImportOptions:
        
        return typing.cast( TagImportOptions.TagImportOptions, self.GetImportOptions( IOC.IMPORT_OPTIONS_TYPE_TAGS ) )
        
    
    def HasImportOptions( self, import_options_type: int ):
        
        with self._lock:
            
            return import_options_type in self._import_options_types_to_import_options
            
        
    
    def ImportOptionsDiffer( self, other_import_options_container: "ImportOptionsContainer", import_options_type: int ):
        
        my_import_options = self.GetImportOptions( import_options_type )
        other_import_options = other_import_options_container.GetImportOptions( import_options_type )
        
        if my_import_options is None or other_import_options is None:
            
            if my_import_options is not None or other_import_options is not None:
                
                return True
                
            
        else:
            
            if my_import_options.DumpToString() != other_import_options.DumpToString():
                
                return True
                
            
        
        return False
        
    
    def IsEmpty( self ):
        
        with self._lock:
            
            return len( self._import_options_types_to_import_options ) == 0
            
        
    
    def IsFull( self ):
        
        with self._lock:
            
            return len( self._import_options_types_to_import_options ) == len( IOC.IMPORT_OPTIONS_TYPES_CANONICAL_ORDER )
            
        
    
    def SetImportOptions( self, import_options: IOC.ImportOptionsMetatype, source_label: str | None = None ):
        
        with self._lock:
            
            self._SetImportOptions( import_options, source_label = source_label )
            
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_IMPORT_OPTIONS_CONTAINER ] = ImportOptionsContainer
