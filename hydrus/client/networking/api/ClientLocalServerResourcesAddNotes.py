from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusExceptions
from hydrus.core.networking import HydrusServerRequest
from hydrus.core.networking import HydrusServerResources

from hydrus.client import ClientAPI
from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.metadata import ClientContentUpdates
from hydrus.client.networking.api import ClientLocalServerCore
from hydrus.client.networking.api import ClientLocalServerResources

class HydrusResourceClientAPIRestrictedAddNotes( ClientLocalServerResources.HydrusResourceClientAPIRestricted ):
    
    def _CheckAPIPermissions( self, request: HydrusServerRequest.HydrusRequest ):
        
        request.client_api_permissions.CheckPermission( ClientAPI.CLIENT_API_PERMISSION_ADD_NOTES )
        
    

class HydrusResourceClientAPIRestrictedAddNotesSetNotes( HydrusResourceClientAPIRestrictedAddNotes ):
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        hashes = set( ClientLocalServerCore.ParseHashes( request ) )
        
        if len( hashes ) == 1:
            
            hash = list( hashes )[0]
            
        else:
            
            raise HydrusExceptions.BadRequestException( 'There was no file identifier or hash given!' )
            
        
        new_names_to_notes = request.parsed_request_args.GetValue( 'notes', dict, expected_dict_types = ( str, str ) )
        
        merge_cleverly = request.parsed_request_args.GetValue( 'merge_cleverly', bool, default_value = False )
        
        if merge_cleverly:
            
            from hydrus.client.importing.options import NoteImportOptions
            
            extend_existing_note_if_possible = request.parsed_request_args.GetValue( 'extend_existing_note_if_possible', bool, default_value = True )
            conflict_resolution = request.parsed_request_args.GetValue( 'conflict_resolution', int, default_value = NoteImportOptions.NOTE_IMPORT_CONFLICT_RENAME )
            
            if conflict_resolution not in NoteImportOptions.note_import_conflict_str_lookup:
                
                raise HydrusExceptions.BadRequestException( 'The given conflict resolution type was not in the allowed range!' )
                
            
            note_import_options = NoteImportOptions.NoteImportOptions()
            
            note_import_options.SetIsDefault( False )
            note_import_options.SetExtendExistingNoteIfPossible( extend_existing_note_if_possible )
            note_import_options.SetConflictResolution( conflict_resolution )
            
            media_result = CG.client_controller.Read( 'media_result', hash )
            
            existing_names_to_notes = media_result.GetNotesManager().GetNamesToNotes()
            
            names_and_notes = list( new_names_to_notes.items() )
            
            new_names_to_notes = note_import_options.GetUpdateeNamesToNotes( existing_names_to_notes, names_and_notes )
            
        
        content_updates = [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_NOTES, HC.CONTENT_UPDATE_SET, ( hash, name, note ) ) for ( name, note ) in new_names_to_notes.items() ]
        
        if len( content_updates ) > 0:
            
            content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( CC.LOCAL_NOTES_SERVICE_KEY, content_updates )
            
            CG.client_controller.WriteSynchronous( 'content_updates', content_update_package )
            
        
        body_dict = {
            'notes': new_names_to_notes
        }
        
        body = ClientLocalServerCore.Dumps( body_dict, request.preferred_mime )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = request.preferred_mime, body = body )
        
        return response_context
        
    

class HydrusResourceClientAPIRestrictedAddNotesDeleteNotes( HydrusResourceClientAPIRestrictedAddNotes ):
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        hashes = set( ClientLocalServerCore.ParseHashes( request ) )
        
        if len( hashes ) == 1:
            
            hash = list( hashes )[0]
            
        else:
            
            raise HydrusExceptions.BadRequestException( 'There was no file identifier or hash given!' )
            
        
        note_names = request.parsed_request_args.GetValue( 'note_names', list, expected_list_type = str )
        
        content_updates = [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_NOTES, HC.CONTENT_UPDATE_DELETE, ( hash, name ) ) for name in note_names ]
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( CC.LOCAL_NOTES_SERVICE_KEY, content_updates )
        
        CG.client_controller.WriteSynchronous( 'content_updates', content_update_package )
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    
