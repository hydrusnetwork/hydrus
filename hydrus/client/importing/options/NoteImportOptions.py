import collections.abc

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusSerialisable

from hydrus.client import ClientConstants as CC
from hydrus.client.media import ClientMediaResult
from hydrus.client.metadata import ClientContentUpdates

NOTE_IMPORT_CONFLICT_REPLACE = 0
NOTE_IMPORT_CONFLICT_IGNORE = 1
NOTE_IMPORT_CONFLICT_APPEND = 2
NOTE_IMPORT_CONFLICT_RENAME = 3

note_import_conflict_str_lookup = {
    NOTE_IMPORT_CONFLICT_REPLACE : 'replace the existing note',
    NOTE_IMPORT_CONFLICT_IGNORE : 'do not add the new note',
    NOTE_IMPORT_CONFLICT_APPEND : 'append the new note to the end of the existing note',
    NOTE_IMPORT_CONFLICT_RENAME : 'add the new note under a new name',
}

class NoteImportOptions( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_NOTE_IMPORT_OPTIONS
    SERIALISABLE_NAME = 'Note Import Options'
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        super().__init__()
        
        self._get_notes = True
        self._extend_existing_note_if_possible = True
        self._conflict_resolution = NOTE_IMPORT_CONFLICT_RENAME
        self._name_whitelist = set()
        self._all_name_override = None
        self._names_to_name_overrides = dict()
        self._is_default = False
        
    
    def _GetSerialisableInfo( self ):
        
        name_whitelist = list( self._name_whitelist )
        names_and_name_overrides = list( self._names_to_name_overrides.items() )
        
        return ( self._get_notes, self._extend_existing_note_if_possible, self._conflict_resolution, name_whitelist, self._all_name_override, names_and_name_overrides, self._is_default )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._get_notes, self._extend_existing_note_if_possible, self._conflict_resolution, name_whitelist, self._all_name_override, names_and_name_overrides, self._is_default ) = serialisable_info
        
        self._name_whitelist = set( name_whitelist )
        self._names_to_name_overrides = dict( names_and_name_overrides )
        
    
    def GetAllNameOverride( self ) -> str | None:
        
        return self._all_name_override
        
    
    def GetConflictResolution( self ) -> int:
        
        return self._conflict_resolution
        
    
    def GetExtendExistingNoteIfPossible( self ) -> bool:
        
        return self._extend_existing_note_if_possible
        
    
    def GetGetNotes( self ) -> bool:
        
        return self._get_notes
        
    
    def GetNamesToNameOverrides( self ) -> dict[ str, str ]:
        
        return dict( self._names_to_name_overrides )
        
    
    def GetNameWhitelist( self ):
        
        return set( self._name_whitelist )
        
    
    def GetContentUpdatePackage( self, media_result: ClientMediaResult.MediaResult, names_and_notes: collections.abc.Collection[ tuple[ str, str ] ] ) -> ClientContentUpdates.ContentUpdatePackage:
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage()
        
        if self._get_notes:
            
            hash = media_result.GetHash()
            
            notes_manager = media_result.GetNotesManager()
            
            existing_names_to_notes = dict( notes_manager.GetNamesToNotes() )
            
            updatee_names_to_notes = self.GetUpdateeNamesToNotes( existing_names_to_notes, names_and_notes )
            
            content_updates = [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_NOTES, HC.CONTENT_UPDATE_SET, ( hash, name, note ) ) for ( name, note ) in updatee_names_to_notes.items() ]
            
            if len( content_updates ) > 0:
                
                content_update_package.AddContentUpdates( CC.LOCAL_NOTES_SERVICE_KEY, content_updates )
                
            
        
        return content_update_package
        
    
    def GetSummary( self ):
        
        if self._is_default:
            
            return 'Using whatever the default note import options is at at time of import.'
            
        
        statements = []
        
        if self._get_notes:
            
            statements.append( 'adding notes' )
            
            if self._extend_existing_note_if_possible:
                
                statements.append( 'extending where possible' )
                
            
            statements.append( 'with conflict resolution: {}'.format( note_import_conflict_str_lookup[ self._conflict_resolution ] ) )
            
            if self._all_name_override is not None or len( self._names_to_name_overrides ) > 0:
                
                statements.append( 'with renames' )
                
            
        else:
            
            statements.append( 'not adding notes' )
            
        
        summary = ', '.join( statements )
        
        return summary
        
    
    def GetUpdateeNamesToNotes( self, existing_names_to_notes, names_and_notes ):
        
        updatee_names_to_notes = {}
        
        if not self._get_notes:
            
            return updatee_names_to_notes
            
        
        # TODO: Add options to noteimportoptions to say whether we discard dupes in names_to_notes and empty notes and any other complex logic here
        # we can have a complex-ish default, but someone is going to want different, so add options
        
        existing_names_to_notes = dict( existing_names_to_notes )
        names_and_notes = sorted( names_and_notes )
        
        for ( name, note ) in names_and_notes:
            
            if len( self._name_whitelist ) > 0 and name not in self._name_whitelist:
                
                continue
                
            
            if name in self._names_to_name_overrides:
                
                name = self._names_to_name_overrides[ name ]
                
            elif self._all_name_override is not None:
                
                name = self._all_name_override
                
            
            if name in existing_names_to_notes:
                
                name_exists = True
                
                existing_note = existing_names_to_notes[ name ]
                
                name_and_note_exists = existing_note == note
                
                name_and_note_exists_but_is_an_extension = len( note ) > len( existing_note ) and existing_note in note
                
            else:
                
                name_exists = False
                name_and_note_exists = False
                name_and_note_exists_but_is_an_extension = False
                
            
            exists_under_different_name = False
            exists_under_different_name_name = ''
            exists_under_different_name_but_is_an_extension = False
            
            # we no longer allow a note if its text straight up exists anywhere already
            for ( existing_name, existing_note ) in sorted( existing_names_to_notes.items() ):
                
                if note == existing_note:
                    
                    exists_under_different_name = True
                    exists_under_different_name_name = existing_name
                    
                    break
                    
                
            
            if not exists_under_different_name:
                
                similar_matching_names_to_notes = { na : no for ( na, no ) in existing_names_to_notes.items() if na != name and ( na.startswith( name ) or no == note ) }
                
                # here we deal with the situation with iterative renames
                # imagine file has note 'abc' = '123'
                # new site adds 'abc' = '789'. this causes 'abc (1)' = '789'
                # any future parse of 'abc' = '789' will check against the original 'abc' = '123' and cause 'abc (2+)' = '789' unless we check other prefix-matching note names!
                for ( existing_name, existing_note ) in sorted( similar_matching_names_to_notes.items() ):
                    
                    if note == existing_note:
                        
                        exists_under_different_name = True
                        exists_under_different_name_name = existing_name
                        
                        break
                        
                    
                    if len( note ) > len( existing_note ) and existing_note in note:
                        
                        exists_under_different_name_name = existing_name
                        exists_under_different_name_but_is_an_extension = True
                        
                        break
                        
                    
                
            
            do_it = True
            
            if name_and_note_exists:
                
                do_it = False
                
            elif exists_under_different_name:
                
                do_it = False # same note text exists under different name, no action needed
                
            elif name_exists:
                
                # ok a note exists under this name already, and it differs to what we want to add. what are we going to do about the conflict?
                
                if name_and_note_exists_but_is_an_extension and self._extend_existing_note_if_possible:
                    
                    pass # yes let's do it with current name and note
                    
                elif exists_under_different_name_but_is_an_extension and self._extend_existing_note_if_possible:
                    
                    name = exists_under_different_name_name # yes let's do it with the changed name
                    
                else:
                    
                    if self._conflict_resolution == NOTE_IMPORT_CONFLICT_IGNORE:
                        
                        do_it = False
                        
                    elif self._conflict_resolution == NOTE_IMPORT_CONFLICT_RENAME:
                        
                        existing_names = set( existing_names_to_notes.keys() )
                        
                        name = HydrusData.GetNonDupeName( name, existing_names )
                        
                    elif self._conflict_resolution == NOTE_IMPORT_CONFLICT_APPEND:
                        
                        existing_note = existing_names_to_notes[ name ]
                        
                        existing_note_already_includes_note = len( existing_note ) > len( note ) and note in existing_note
                        
                        if existing_note_already_includes_note:
                            
                            do_it = False
                            
                        else:
                            
                            sep = '\n' * 2
                            
                            note = sep.join( ( existing_note, note ) )
                            
                        
                    elif self._conflict_resolution == NOTE_IMPORT_CONFLICT_REPLACE:
                        
                        pass # yes, just do it, overwrite
                        
                    
                
            
            if do_it:
                
                updatee_names_to_notes[ name ] = note
                existing_names_to_notes[ name ] = note
                
            
        
        return updatee_names_to_notes
        
    
    def IsDefault( self ):
        
        return self._is_default
        
    
    def SetAllNameOverride( self, all_name_override: str | None ):
        
        self._all_name_override = all_name_override
        
    
    def SetConflictResolution( self, conflict_resolution: int ):
        
        self._conflict_resolution = conflict_resolution
        
    
    def SetExtendExistingNoteIfPossible( self, extend_existing_note_if_possible: bool ):
        
        self._extend_existing_note_if_possible = extend_existing_note_if_possible
        
    
    def SetGetNotes( self, get_notes: bool ):
        
        self._get_notes = get_notes
        
    
    def SetIsDefault( self, value: bool ):
        
        self._is_default = value
        
    
    def SetNamesToNameOverrides( self, names_to_name_overrides: dict[ str, str ] ):
        
        self._names_to_name_overrides = names_to_name_overrides
        
    
    def SetNameWhitelist( self, name_whitelist: collections.abc.Collection[ str ] ):
        
        self._name_whitelist = set( name_whitelist )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_NOTE_IMPORT_OPTIONS ] = NoteImportOptions
