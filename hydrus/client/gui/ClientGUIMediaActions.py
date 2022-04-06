import collections
import typing

from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG

from hydrus.client import ClientApplicationCommand as CAC
from hydrus.client import ClientConstants as CC
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIScrolledPanelsEdit
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.media import ClientMedia
from hydrus.client.metadata import ClientTags

def ApplyContentApplicationCommandToMedia( parent: QW.QWidget, command: CAC.ApplicationCommand, media: typing.Collection[ ClientMedia.Media ] ):
    
    if not command.IsContentCommand():
        
        return
        
    
    service_key = command.GetContentServiceKey()
    action = command.GetContentAction()
    value = command.GetContentValue()
    
    try:
        
        service = HG.client_controller.services_manager.GetService( service_key )
        
    except HydrusExceptions.DataMissing:
        
        command_processed = False
        
        return command_processed
        
    
    service_type = service.GetServiceType()
    
    hashes = set()
    
    for m in media:
        
        hashes.add( m.GetHash() )
        
    
    if service_type in HC.REAL_TAG_SERVICES:
        
        tag = value
        
        rows = [ ( tag, hashes ) ]
        
        can_add = False
        can_pend = False
        can_delete = False
        can_petition = True
        can_rescind_pend = False
        can_rescind_petition = False
        
        for m in media:
            
            tags_manager = m.GetTagsManager()
            
            current = tags_manager.GetCurrent( service_key, ClientTags.TAG_DISPLAY_STORAGE )
            pending = tags_manager.GetPending( service_key, ClientTags.TAG_DISPLAY_STORAGE )
            petitioned = tags_manager.GetPetitioned( service_key, ClientTags.TAG_DISPLAY_STORAGE )
            
            if tag not in current:
                
                can_add = True
                
            
            if tag not in current and tag not in pending:
                
                can_pend = True
                
            
            if tag in current and action == HC.CONTENT_UPDATE_FLIP:
                
                can_delete = True
                
            
            if tag in current and tag not in petitioned and action == HC.CONTENT_UPDATE_FLIP:
                
                can_petition = True
                
            
            if tag in pending and action == HC.CONTENT_UPDATE_FLIP:
                
                can_rescind_pend = True
                
            
            if tag in petitioned:
                
                can_rescind_petition = True
                
            
        
        reason = None
        
        if service_type == HC.LOCAL_TAG:
            
            if can_add:
                
                content_update_action = HC.CONTENT_UPDATE_ADD
                
            elif can_delete:
                
                content_update_action = HC.CONTENT_UPDATE_DELETE
                
            else:
                
                return True
                
            
        else:
            
            if can_rescind_petition:
                
                content_update_action = HC.CONTENT_UPDATE_RESCIND_PETITION
                
            elif can_pend:
                
                content_update_action = HC.CONTENT_UPDATE_PEND
                
            elif can_rescind_pend:
                
                content_update_action = HC.CONTENT_UPDATE_RESCIND_PEND
                
            elif can_petition:
                
                message = 'Enter a reason for this tag to be removed. A janitor will review your petition.'
                
                from hydrus.client.gui import ClientGUIDialogs
                
                with ClientGUIDialogs.DialogTextEntry( parent, message ) as dlg:
                    
                    if dlg.exec() == QW.QDialog.Accepted:
                        
                        content_update_action = HC.CONTENT_UPDATE_PETITION
                        
                        reason = dlg.GetValue()
                        
                    else:
                        
                        return True
                        
                    
                
            else:
                
                return True
                
            
        
        content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, content_update_action, row, reason = reason ) for row in rows ]
        
    elif service_type in ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ):
        
        if action in ( HC.CONTENT_UPDATE_SET, HC.CONTENT_UPDATE_FLIP ):
            
            rating = value
            
            can_set = False
            can_unset = False
            
            for m in media:
                
                ratings_manager = m.GetRatingsManager()
                
                current_rating = ratings_manager.GetRating( service_key )
                
                if current_rating == rating and action == HC.CONTENT_UPDATE_FLIP:
                    
                    can_unset = True
                    
                else:
                    
                    can_set = True
                    
                
            
            if can_set:
                
                row = ( rating, hashes )
                
            elif can_unset:
                
                row = ( None, hashes )
                
            else:
                
                return True
                
            
            content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, row ) ]
            
        elif action in ( HC.CONTENT_UPDATE_INCREMENT, HC.CONTENT_UPDATE_DECREMENT ):
            
            if service_type == HC.LOCAL_RATING_NUMERICAL:
                
                if action == HC.CONTENT_UPDATE_INCREMENT:
                    
                    direction = 1
                    initialisation_rating = 0.0
                    
                elif action == HC.CONTENT_UPDATE_DECREMENT:
                    
                    direction = -1
                    initialisation_rating = 1.0
                    
                
                one_star_value = service.GetOneStarValue()
                
                ratings_to_hashes = collections.defaultdict( set )
                
                for m in media:
                    
                    ratings_manager = m.GetRatingsManager()
                    
                    current_rating = ratings_manager.GetRating( service_key )
                    
                    if current_rating is None:
                        
                        new_rating = initialisation_rating
                        
                    else:
                        
                        new_rating = current_rating + ( one_star_value * direction )
                        
                        new_rating = max( min( new_rating, 1.0 ), 0.0 )
                        
                    
                    if current_rating != new_rating:
                        
                        ratings_to_hashes[ new_rating ].add( m.GetHash() )
                        
                    
                
                content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( rating, hashes ) ) for ( rating, hashes ) in ratings_to_hashes.items() ]
                
            else:
                
                return True
                
            
        
    else:
        
        return False
        
    
    if len( content_updates ) > 0:
        
        HG.client_controller.Write( 'content_updates', { service_key : content_updates } )
        
    
    return True
    
def EditFileNotes( win: QW.QWidget, media: ClientMedia.Media, name_to_start_on = typing.Optional[ str ] ):
    
    names_to_notes = media.GetNotesManager().GetNamesToNotes()
    
    title = 'manage notes'
    
    with ClientGUITopLevelWindowsPanels.DialogEdit( win, title ) as dlg:
        
        panel = ClientGUIScrolledPanelsEdit.EditFileNotesPanel( dlg, names_to_notes, name_to_start_on = name_to_start_on )
        
        dlg.SetPanel( panel )
        
        if dlg.exec() == QW.QDialog.Accepted:
            
            hash = media.GetHash()
            
            ( names_to_notes, deletee_names ) = panel.GetValue()
            
            content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_NOTES, HC.CONTENT_UPDATE_SET, ( hash, name, note ) ) for ( name, note ) in names_to_notes.items() ]
            content_updates.extend( [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_NOTES, HC.CONTENT_UPDATE_DELETE, ( hash, name ) ) for name in deletee_names ] )
            
            service_keys_to_content_updates = { CC.LOCAL_NOTES_SERVICE_KEY : content_updates }
            
            HG.client_controller.Write( 'content_updates', service_keys_to_content_updates )
            
        
    
def UndeleteFiles( hashes ):
    
    local_file_service_keys = HG.client_controller.services_manager.GetServiceKeys( ( HC.LOCAL_FILE_DOMAIN, ) )
    
    for chunk_of_hashes in HydrusData.SplitIteratorIntoChunks( hashes, 64 ):
        
        media_results = HG.client_controller.Read( 'media_results', chunk_of_hashes )
        
        service_keys_to_hashes = collections.defaultdict( list )
        
        for media_result in media_results:
            
            locations_manager = media_result.GetLocationsManager()
            
            if CC.TRASH_SERVICE_KEY not in locations_manager.GetCurrent():
                
                continue
                
            
            hash = media_result.GetHash()
            
            for service_key in locations_manager.GetDeleted().intersection( local_file_service_keys ):
                
                service_keys_to_hashes[ service_key ].append( hash )
                
            
        
        for ( service_key, service_hashes ) in service_keys_to_hashes.items():
            
            content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_UNDELETE, service_hashes )
            
            service_keys_to_content_updates = { service_key : [ content_update ] }
            
            HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
            
        
    
def UndeleteMedia( win, media ):
    
    media_deleted_service_keys = HydrusData.MassUnion( ( m.GetLocationsManager().GetDeleted() for m in media ) )
    
    local_file_services = HG.client_controller.services_manager.GetServices( ( HC.LOCAL_FILE_DOMAIN, ) )
    
    undeletable_services = [ local_file_service for local_file_service in local_file_services if local_file_service.GetServiceKey() in media_deleted_service_keys ]
    
    if len( undeletable_services ) > 0:
        
        do_it = False
        
        if len( undeletable_services ) > 1:
            
            choice_tuples = []
            
            for ( i, service ) in enumerate( undeletable_services ):
                
                choice_tuples.append( ( service.GetName(), service, i == 0 ) )
                
            
            try:
                
                undelete_services = ClientGUIDialogsQuick.SelectMultipleFromList( win, 'Undelete for?', choice_tuples )
                
                do_it = True
                
            except HydrusExceptions.CancelledException:
                
                return
                
            
        else:
            
            undelete_services = undeletable_services
            
            if HC.options[ 'confirm_trash' ]:
                
                result = ClientGUIDialogsQuick.GetYesNo( win, 'Undelete this file back to {}?'.format( undelete_services[0].GetName() ) )
                
                if result == QW.QDialog.Accepted:
                    
                    do_it = True
                    
                
            else:
                
                do_it = True
                
            
        
        if do_it:
            
            for chunk_of_media in HydrusData.SplitIteratorIntoChunks( media, 64 ):
                
                service_keys_to_content_updates = collections.defaultdict( list )
                
                for service in undelete_services:
                    
                    service_key = service.GetServiceKey()
                    
                    undeletee_hashes = [ m.GetHash() for m in chunk_of_media if service_key in m.GetLocationsManager().GetDeleted() ]
                    
                    service_keys_to_content_updates[ service_key ] = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_UNDELETE, undeletee_hashes ) ]
                    
                
                HG.client_controller.Write( 'content_updates', service_keys_to_content_updates )
                
            
        
    
