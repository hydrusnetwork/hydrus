from hydrus.core import HydrusSerialisable

from hydrus.client import ClientConstants as CC
from hydrus.client.importing.options import ImportOptionsConstants as IOC

class ExternalProgramsImportOptionsSingleEntry( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_EXTERNAL_PROGRAMS_IMPORT_OPTIONS_SINGLE_ENTRY
    SERIALISABLE_NAME = 'External Programs Import Options - Single Entry'
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        # TODO: Add a metadata conditional to this guy! "Only add for vids" etc..
        
        super().__init__()
        
        self._id_and_name = HydrusSerialisable.IdAndName()
        
        self._do_it_on_new = True
        self._do_it_on_already_in = False
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_id_and_name = self._id_and_name.GetSerialisableTuple()
        
        return ( serialisable_id_and_name, self._do_it_on_new, self._do_it_on_already_in )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_id_and_name, self._do_it_on_new, self._do_it_on_already_in ) = serialisable_info
        
        self._id_and_name = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_id_and_name )
        
    
    def DoItOnAlreadyIn( self ) -> bool:
        
        return self._do_it_on_already_in
        
    
    def DoItOnNew( self ) -> bool:
        
        return self._do_it_on_new
        
    
    def GetIdAndName( self ) -> HydrusSerialisable.IdAndName:
        
        return self._id_and_name
        
    
    def GetSummary( self, import_options_caller_type: int ):
        
        if self._do_it_on_new and self._do_it_on_already_in:
            
            import_types_desc = 'all file imports'
            
        elif self._do_it_on_new:
            
            import_types_desc = 'all new file imports'
            
        elif self._do_it_on_already_in:
            
            import_types_desc = 'all "already in db" imports'
            
        else:
            
            import_types_desc = 'no imports (will do nothing!)'
            
        
        return f'call {self._id_and_name.name} on {import_types_desc}'
        
    
    def ShouldFire( self, import_status: int ) -> bool:
        
        if import_status == CC.STATUS_SUCCESSFUL_AND_NEW and self._do_it_on_new:
            
            return True
            
        elif import_status == CC.STATUS_SUCCESSFUL_BUT_REDUNDANT and self._do_it_on_already_in:
            
            return True
            
        
        return False
        
    
    def SetDoItOnAlreadyIn( self, do_it: bool ):
        
        self._do_it_on_already_in = do_it
        
    
    def SetDoItOnNew( self, do_it: bool ):
        
        self._do_it_on_new = do_it
        
    
    def SetIdAndName( self, id_and_name: HydrusSerialisable.IdAndName ):
        
        self._id_and_name = id_and_name
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_EXTERNAL_PROGRAMS_IMPORT_OPTIONS_SINGLE_ENTRY ] = ExternalProgramsImportOptionsSingleEntry

class ExternalProgramsImportOptions( IOC.ImportOptionsMetatype ):
    
    IMPORT_OPTIONS_TYPE = IOC.IMPORT_OPTIONS_TYPE_EXTERNAL_PROGRAMS
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_EXTERNAL_PROGRAMS_IMPORT_OPTIONS
    SERIALISABLE_NAME = 'External Programs Import Options'
    SERIALISABLE_VERSION = 1
    
    def __init__(
        self,
    ):
        
        super().__init__()
        
        self._entries: HydrusSerialisable.SerialisableList[ ExternalProgramsImportOptionsSingleEntry ] = HydrusSerialisable.SerialisableList()
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_entries = self._entries.GetSerialisableTuple()
        
        return serialisable_entries
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        serialisable_entries = serialisable_info
        
        self._entries = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_entries )
        
    
    def GetEntries( self ) -> list[ ExternalProgramsImportOptionsSingleEntry ]:
        
        return list( self._entries )
        
    
    def GetSummary( self, import_options_caller_type: int ):
        
        if len( self._entries ) == 0:
            
            return ''
            
        
        statements = sorted( [ entry.GetSummary( import_options_caller_type ) for entry in self._entries ] )
        
        summary = ', '.join( statements )
        
        return summary
        
    
    def SetEntries( self, entries: list[ ExternalProgramsImportOptionsSingleEntry ] ):
        
        self._entries = HydrusSerialisable.SerialisableList( entries )
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_EXTERNAL_PROGRAMS_IMPORT_OPTIONS ] = ExternalProgramsImportOptions
