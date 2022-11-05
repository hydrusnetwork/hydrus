import os
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusSerialisable

from hydrus.client import ClientConstants as CC
from hydrus.client.media import ClientMediaResult

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
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
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
        
    
    def GetAllNameOverride( self ) -> typing.Optional[ str ]:
        
        return self._all_name_override
        
    
    def GetConflictResolution( self ) -> int:
        
        return self._conflict_resolution
        
    
    def GetExtendExistingNoteIfPossible( self ) -> bool:
        
        return self._extend_existing_note_if_possible
        
    
    def GetGetNotes( self ) -> bool:
        
        return self._get_notes
        
    
    def GetNamesToNameOverrides( self ) -> typing.Dict[ str, str ]:
        
        return dict( self._names_to_name_overrides )
        
    
    def GetNameWhitelist( self ):
        
        return set( self._name_whitelist )
        
    
    def GetServiceKeysToContentUpdates( self, media_result: ClientMediaResult.MediaResult, names_and_notes: typing.Collection[ typing.Tuple[ str, str ] ] ):
        
        content_updates = []
        
        if self._get_notes:
            
            hash = media_result.GetHash()
            
            notes_manager = media_result.GetNotesManager()
            
            existing_names_to_notes = dict( notes_manager.GetNamesToNotes() )
            
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
                    
                    new_note_is_an_extension = len( note ) > len( existing_note ) and existing_note in note
                    
                    
                else:
                    
                    name_exists = False
                    name_and_note_exists = False
                    new_note_is_an_extension = False
                    
                
                do_it = True
                
                if name_and_note_exists:
                    
                    do_it = False
                    
                elif name_exists:
                    
                    if new_note_is_an_extension and self._extend_existing_note_if_possible:
                        
                        pass # yes let's do it with current name and note
                        
                    else:
                        
                        if self._conflict_resolution == NOTE_IMPORT_CONFLICT_IGNORE:
                            
                            do_it = False
                            
                        elif self._conflict_resolution == NOTE_IMPORT_CONFLICT_RENAME:
                            
                            note_already_exists_under_different_name = note in existing_names_to_notes.values()
                            
                            if note_already_exists_under_different_name:
                                
                                do_it = False
                                
                            else:
                                
                                existing_names = set( existing_names_to_notes.keys() )
                                
                                name = HydrusData.GetNonDupeName( name, existing_names )
                                
                            
                        elif self._conflict_resolution == NOTE_IMPORT_CONFLICT_APPEND:
                            
                            existing_note = existing_names_to_notes[ name ]
                            
                            existing_note_already_includes_note = len( existing_note ) > len( note ) and note in existing_note
                            
                            if existing_note_already_includes_note:
                                
                                do_it = False
                                
                            else:
                                
                                sep = os.linesep * 2
                                
                                note = sep.join( ( existing_note, note ) )
                                
                            
                        elif self._conflict_resolution == NOTE_IMPORT_CONFLICT_REPLACE:
                            
                            pass # yes, just do it
                            
                        
                    
                
                if do_it:
                    
                    existing_names_to_notes[ name ] = note
                    
                    content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_NOTES, HC.CONTENT_UPDATE_SET, ( hash, name, note ) ) )
                    
                
            
        
        service_keys_to_content_updates = {}
        
        if len( content_updates ) > 0:
            
            service_keys_to_content_updates[ CC.LOCAL_NOTES_SERVICE_KEY ] = content_updates
            
        
        return service_keys_to_content_updates
        
    
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
        
    
    def IsDefault( self ):
        
        return self._is_default
        
    
    def SetAllNameOverride( self, all_name_override: typing.Optional[ str ] ):
        
        self._all_name_override = all_name_override
        
    
    def SetConflictResolution( self, conflict_resolution: int ):
        
        self._conflict_resolution = conflict_resolution
        
    
    def SetExtendExistingNoteIfPossible( self, extend_existing_note_if_possible: bool ):
        
        self._extend_existing_note_if_possible = extend_existing_note_if_possible
        
    
    def SetGetNotes( self, get_notes: bool ):
        
        self._get_notes = get_notes
        
    
    def SetIsDefault( self, value: bool ):
        
        self._is_default = value
        
    
    def SetNamesToNameOverrides( self, names_to_name_overrides: typing.Dict[ str, str ] ):
        
        self._names_to_name_overrides = names_to_name_overrides
        
    
    def SetNameWhitelist( self, name_whitelist: typing.Collection[ str ] ):
        
        self._name_whitelist = set( name_whitelist )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_NOTE_IMPORT_OPTIONS ] = NoteImportOptions
