from hydrus.core import HydrusSerialisable

from hydrus.client.importing.options import NoteImportOptions

class NoteImportOptionsLegacy( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_NOTE_IMPORT_OPTIONS_LEGACY
    SERIALISABLE_NAME = 'Note Import Options (Legacy)'
    SERIALISABLE_VERSION = 2
    
    def __init__( self ):
        
        super().__init__()
        
        self._note_import_options = NoteImportOptions.NoteImportOptions()
        
        self._is_default = False
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_note_import_options = self._note_import_options.GetSerialisableTuple()
        
        return ( serialisable_note_import_options, self._is_default )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_note_import_options, self._is_default ) = serialisable_info
        
        self._note_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_note_import_options )
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        # this is a little silly, but we want to be clean with the migration so we'll hop skip and jump as we did with files and tags to get rid of 'is default'
        
        if version == 1:
            
            ( get_notes, extend_existing_note_if_possible, conflict_resolution, name_whitelist, all_name_override, names_and_name_overrides, is_default ) = old_serialisable_info
            
            names_to_name_overrides = dict( names_and_name_overrides )
            
            note_import_options = NoteImportOptions.NoteImportOptions()
            
            note_import_options.SetAllNameOverride( all_name_override )
            note_import_options.SetConflictResolution( conflict_resolution )
            note_import_options.SetExtendExistingNoteIfPossible( extend_existing_note_if_possible )
            note_import_options.SetGetNotes( get_notes )
            note_import_options.SetNamesToNameOverrides( names_to_name_overrides )
            note_import_options.SetNameWhitelist( name_whitelist )
            
            serialisable_note_import_options = note_import_options.GetSerialisableTuple()
            
            new_serialisable_info = ( serialisable_note_import_options, is_default )
            
            return ( 2, new_serialisable_info )
            
        
    
    def GetNoteImportOptions( self ) -> NoteImportOptions.NoteImportOptions:
        
        return self._note_import_options
        
    
    def GetSummary( self, show_downloader_options: bool = True ):
        
        if self._is_default:
            
            return 'Using whatever the default note import options is at at time of import.'
            
        
        return self._note_import_options.GetSummary( show_downloader_options = show_downloader_options )
        
    
    def IsDefault( self ):
        
        return self._is_default
        
    
    def SetIsDefault( self, value: bool ):
        
        self._is_default = value
        
    
    def SetNoteImportOptions( self, note_import_options: NoteImportOptions.NoteImportOptions ):
        
        self._note_import_options = note_import_options
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_NOTE_IMPORT_OPTIONS_LEGACY ] = NoteImportOptionsLegacy
