import collections
import typing

from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG

from hydrus.client import ClientApplicationCommand as CAC
from hydrus.client import ClientConstants as CC
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
            
            tags = [ tag ]
            
            if can_add:
                
                content_update_action = HC.CONTENT_UPDATE_ADD
                
                tag_parents_manager = HG.client_controller.tag_parents_manager
                
                parents = tag_parents_manager.GetParents( service_key, tag )
                
                tags.extend( parents )
                
            elif can_delete:
                
                content_update_action = HC.CONTENT_UPDATE_DELETE
                
            else:
                
                return True
                
            
            rows = [ ( tag, hashes ) for tag in tags ]
            
        else:
            
            if can_rescind_petition:
                
                content_update_action = HC.CONTENT_UPDATE_RESCIND_PETITION
                
                rows = [ ( tag, hashes ) ]
                
            elif can_pend:
                
                tags = [ tag ]
                
                content_update_action = HC.CONTENT_UPDATE_PEND
                
                tag_parents_manager = HG.client_controller.tag_parents_manager
                
                parents = tag_parents_manager.GetParents( service_key, tag )
                
                tags.extend( parents )
                
                rows = [ ( tag, hashes ) for tag in tags ]
                
            elif can_rescind_pend:
                
                content_update_action = HC.CONTENT_UPDATE_RESCIND_PEND
                
                rows = [ ( tag, hashes ) ]
                
            elif can_petition:
                
                message = 'Enter a reason for this tag to be removed. A janitor will review your petition.'
                
                from hydrus.client.gui import ClientGUIDialogs
                
                with ClientGUIDialogs.DialogTextEntry( parent, message ) as dlg:
                    
                    if dlg.exec() == QW.QDialog.Accepted:
                        
                        content_update_action = HC.CONTENT_UPDATE_PETITION
                        
                        reason = dlg.GetValue()
                        
                        rows = [ ( tag, hashes ) ]
                        
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
    
def EditFileNotes( win: QW.QWidget, media: ClientMedia.Media ):
    
    names_to_notes = media.GetNotesManager().GetNamesToNotes()
    
    title = 'manage notes'
    
    with ClientGUITopLevelWindowsPanels.DialogEdit( win, title ) as dlg:
        
        panel = ClientGUIScrolledPanelsEdit.EditFileNotesPanel( dlg, names_to_notes )
        
        dlg.SetPanel( panel )
        
        if dlg.exec() == QW.QDialog.Accepted:
            
            hash = media.GetHash()
            
            ( names_to_notes, deletee_names ) = panel.GetValue()
            
            content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_NOTES, HC.CONTENT_UPDATE_SET, ( hash, name, note ) ) for ( name, note ) in names_to_notes.items() ]
            content_updates.extend( [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_NOTES, HC.CONTENT_UPDATE_DELETE, ( hash, name ) ) for name in deletee_names ] )
            
            service_keys_to_content_updates = { CC.LOCAL_NOTES_SERVICE_KEY : content_updates }
            
            HG.client_controller.Write( 'content_updates', service_keys_to_content_updates )
            
        
    
