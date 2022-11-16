import os
import random
import typing

from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusData
from hydrus.core import HydrusGlobals as HG

from hydrus.client import ClientApplicationCommand as CAC
from hydrus.client import ClientConstants as CC
from hydrus.client import ClientLocation
from hydrus.client import ClientPaths
from hydrus.client.gui import ClientGUIMedia
from hydrus.client.gui import ClientGUIMenus
from hydrus.client.media import ClientMedia
from hydrus.client.media import ClientMediaManagers

def AddDuplicatesMenu( win: QW.QWidget, menu: QW.QMenu, location_context: ClientLocation.LocationContext, focus_singleton: ClientMedia.Media, num_selected: int, collections_selected: bool ):
    
    # TODO: I am hesitating making this async since we'll have duplicate relations available in the MediaResult soon enough
    # it would be great to have it in the Canvas though, hence the refactoring. needs a bit more reworking for that, but a good step forward
    
    multiple_selected = num_selected > 1
    
    duplicates_menu = QW.QMenu( menu )
    
    focused_hash = focus_singleton.GetHash()
    
    combined_local_location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_FILE_SERVICE_KEY )
    
    if HG.client_controller.DBCurrentlyDoingJob():
        
        file_duplicate_info = {}
        all_local_files_file_duplicate_info = {}
        
    else:
        
        file_duplicate_info = HG.client_controller.Read( 'file_duplicate_info', location_context, focused_hash )
        
        if location_context.current_service_keys.isdisjoint( HG.client_controller.services_manager.GetServiceKeys( HC.SPECIFIC_LOCAL_FILE_SERVICES ) ):
            
            all_local_files_file_duplicate_info = {}
            
        else:
            
            all_local_files_file_duplicate_info = HG.client_controller.Read( 'file_duplicate_info', combined_local_location_context, focused_hash )
            
        
    
    focus_is_in_duplicate_group = False
    focus_is_in_alternate_group = False
    focus_has_fps = False
    focus_has_potentials = False
    focus_can_be_searched = focus_singleton.GetMime() in HC.FILES_THAT_HAVE_PERCEPTUAL_HASH
    
    if len( file_duplicate_info ) == 0:
        
        ClientGUIMenus.AppendMenuLabel( duplicates_menu, 'could not fetch file\'s duplicates (db currently locked)' )
        
    else:
        
        view_duplicate_relations_jobs = []
        
        if len( file_duplicate_info[ 'counts' ] ) > 0:
            
            view_duplicate_relations_jobs.append( ( location_context, file_duplicate_info ) )
            
        
        if len( all_local_files_file_duplicate_info ) > 0 and len( all_local_files_file_duplicate_info[ 'counts' ] ) > 0 and all_local_files_file_duplicate_info != file_duplicate_info:
            
            view_duplicate_relations_jobs.append( ( combined_local_location_context, all_local_files_file_duplicate_info ) )
            
        
        for ( job_location_context, job_duplicate_info ) in view_duplicate_relations_jobs:
            
            file_duplicate_types_to_counts = job_duplicate_info[ 'counts' ]
            
            ClientGUIMenus.AppendSeparator( duplicates_menu )
            
            label = 'view this file\'s relations'
            
            if job_location_context is combined_local_location_context:
                
                label = '{} ({})'.format( label, HG.client_controller.services_manager.GetName( CC.COMBINED_LOCAL_FILE_SERVICE_KEY ) )
                
            
            ClientGUIMenus.AppendMenuLabel( duplicates_menu, label, label )
            
            if HC.DUPLICATE_MEMBER in file_duplicate_types_to_counts:
                
                if job_duplicate_info[ 'is_king' ]:
                    
                    ClientGUIMenus.AppendMenuLabel( duplicates_menu, 'this is the best quality file of its group' )
                    
                else:
                    
                    ClientGUIMenus.AppendMenuItem( duplicates_menu, 'show the best quality file of this file\'s group', 'Load up a new search with this file\'s best quality duplicate.', ClientGUIMedia.ShowDuplicatesInNewPage, job_location_context, focused_hash, HC.DUPLICATE_KING )
                    
                
                ClientGUIMenus.AppendSeparator( duplicates_menu )
                
            
            for duplicate_type in ( HC.DUPLICATE_MEMBER, HC.DUPLICATE_ALTERNATE, HC.DUPLICATE_FALSE_POSITIVE, HC.DUPLICATE_POTENTIAL ):
                
                if duplicate_type in file_duplicate_types_to_counts:
                    
                    count = file_duplicate_types_to_counts[ duplicate_type ]
                    
                    if count > 0:
                        
                        label = HydrusData.ToHumanInt( count ) + ' ' + HC.duplicate_type_string_lookup[ duplicate_type ]
                        
                        ClientGUIMenus.AppendMenuItem( duplicates_menu, label, 'Show these duplicates in a new page.', ClientGUIMedia.ShowDuplicatesInNewPage, job_location_context, focused_hash, duplicate_type )
                        
                        if duplicate_type == HC.DUPLICATE_MEMBER:
                            
                            focus_is_in_duplicate_group = True
                            
                        elif duplicate_type == HC.DUPLICATE_ALTERNATE:
                            
                            focus_is_in_alternate_group = True
                            
                        elif duplicate_type == HC.DUPLICATE_FALSE_POSITIVE:
                            
                            focus_has_fps = True
                            
                        elif duplicate_type == HC.DUPLICATE_POTENTIAL:
                            
                            focus_has_potentials = True
                            
                        
                    
                
            
        
    
    ClientGUIMenus.AppendSeparator( duplicates_menu )
    
    focus_is_definitely_king = len( file_duplicate_info ) > 0 and file_duplicate_info[ 'is_king' ]
    
    dissolution_actions_available = focus_can_be_searched or focus_is_in_duplicate_group or focus_is_in_alternate_group or focus_has_fps
    
    single_action_available = dissolution_actions_available or not focus_is_definitely_king
    
    if multiple_selected or single_action_available:
        
        duplicates_action_submenu = QW.QMenu( duplicates_menu )
        
        if len( file_duplicate_info ) == 0:
            
            ClientGUIMenus.AppendMenuLabel( duplicates_action_submenu, 'could not fetch info to check for available file actions (db currently locked)' )
            
        else:
            
            if not focus_is_definitely_king:
                
                ClientGUIMenus.AppendMenuItem( duplicates_action_submenu, 'set this file as the best quality of its group', 'Set the focused media to be the King of its group.', win.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_MEDIA_SET_FOCUSED_KING ) )
                
            
        
        ClientGUIMenus.AppendSeparator( duplicates_action_submenu )
        
        if multiple_selected:
            
            label = 'set this file as better than the ' + HydrusData.ToHumanInt( num_selected - 1 ) + ' other selected'
            
            ClientGUIMenus.AppendMenuItem( duplicates_action_submenu, label, 'Set the focused media to be better than the other selected files.', win.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_MEDIA_SET_FOCUSED_BETTER ) )
            
            num_pairs = num_selected * ( num_selected - 1 ) / 2 # com // ations -- n!/2(n-2)!
            
            num_pairs_text = HydrusData.ToHumanInt( num_pairs ) + ' pairs'
            
            ClientGUIMenus.AppendMenuItem( duplicates_action_submenu, 'set all selected as same quality duplicates', 'Set all the selected files as same quality duplicates.', win.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_MEDIA_SET_SAME_QUALITY ) )
            
            ClientGUIMenus.AppendSeparator( duplicates_action_submenu )
            
            ClientGUIMenus.AppendMenuItem( duplicates_action_submenu, 'set all selected as alternates', 'Set all the selected files as alternates.', win.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_MEDIA_SET_ALTERNATE ) )
            
            ClientGUIMenus.AppendMenuItem( duplicates_action_submenu, 'set a relationship with custom metadata merge options', 'Choose which duplicates status to set to this selection and customise non-default duplicate metadata merge options.', win.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_MEDIA_SET_CUSTOM ) )
            
            if collections_selected:
                
                ClientGUIMenus.AppendSeparator( duplicates_action_submenu )
                
                ClientGUIMenus.AppendMenuItem( duplicates_action_submenu, 'set selected collections as groups of alternates', 'Set files in the selection which are collected together as alternates.', win.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_MEDIA_SET_ALTERNATE_COLLECTIONS ) )
                
            
            #
            
            ClientGUIMenus.AppendSeparator( duplicates_action_submenu )
            
            duplicates_edit_action_submenu = QW.QMenu( duplicates_action_submenu )
            
            for duplicate_type in ( HC.DUPLICATE_BETTER, HC.DUPLICATE_SAME_QUALITY ):
                
                ClientGUIMenus.AppendMenuItem( duplicates_edit_action_submenu, 'for ' + HC.duplicate_type_string_lookup[duplicate_type], 'Edit what happens when you set this status.', ClientGUIMedia.EditDuplicateActionOptions, win, duplicate_type )
                
            
            if HG.client_controller.new_options.GetBoolean( 'advanced_mode' ):
                
                ClientGUIMenus.AppendMenuItem( duplicates_edit_action_submenu, 'for ' + HC.duplicate_type_string_lookup[HC.DUPLICATE_ALTERNATE] + ' (advanced!)', 'Edit what happens when you set this status.', ClientGUIMedia.EditDuplicateActionOptions, win, HC.DUPLICATE_ALTERNATE )
                
            
            ClientGUIMenus.AppendMenu( duplicates_action_submenu, duplicates_edit_action_submenu, 'edit default duplicate metadata merge options' )
            
            #
            
            ClientGUIMenus.AppendSeparator( duplicates_action_submenu )
            
            ClientGUIMenus.AppendMenuItem( duplicates_action_submenu, 'set all possible pair combinations as \'potential\' duplicates for the duplicates filter.', 'Queue all these files up in the duplicates filter.', win.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_MEDIA_SET_POTENTIAL ) )
            
        
        if dissolution_actions_available:
            
            ClientGUIMenus.AppendSeparator( duplicates_action_submenu )
            
            duplicates_single_dissolution_menu = QW.QMenu( duplicates_action_submenu )
            
            if focus_can_be_searched:
                
                ClientGUIMenus.AppendMenuItem( duplicates_single_dissolution_menu, 'schedule this file to be searched for potentials again', 'Queue this file for another potentials search. Will not remove any existing potentials.', win.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_MEDIA_RESET_FOCUSED_POTENTIAL_SEARCH ) )
                
            
            if focus_has_potentials:
                
                ClientGUIMenus.AppendMenuItem( duplicates_single_dissolution_menu, 'remove this file\'s potential relationships', 'Clear out this file\'s potential relationships.', win.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_MEDIA_REMOVE_FOCUSED_POTENTIALS ) )
                
            
            if focus_is_in_duplicate_group:
                
                if not focus_is_definitely_king:
                    
                    ClientGUIMenus.AppendMenuItem( duplicates_single_dissolution_menu, 'remove this file from its duplicate group', 'Extract this file from its duplicate group and reset its search status.', win.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_MEDIA_REMOVE_FOCUSED_FROM_DUPLICATE_GROUP ) )
                    
                
                ClientGUIMenus.AppendMenuItem( duplicates_single_dissolution_menu, 'dissolve this file\'s duplicate group completely', 'Completely eliminate this file\'s duplicate group and reset all files\' search status.', win.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_MEDIA_DISSOLVE_FOCUSED_DUPLICATE_GROUP ) )
                
            
            if focus_is_in_alternate_group:
                
                ClientGUIMenus.AppendMenuItem( duplicates_single_dissolution_menu, 'remove this file from its alternate group', 'Extract this file\'s duplicate group from its alternate group and reset the duplicate group\'s search status.', win.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_MEDIA_REMOVE_FOCUSED_FROM_ALTERNATE_GROUP ) )
                
                ClientGUIMenus.AppendMenuItem( duplicates_single_dissolution_menu, 'dissolve this file\'s alternate group completely', 'Completely eliminate this file\'s alternate group and all duplicate group members. This resets search status for all involved files.', win.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_MEDIA_DISSOLVE_FOCUSED_ALTERNATE_GROUP ) )
                
            
            if focus_has_fps:
                
                ClientGUIMenus.AppendMenuItem( duplicates_single_dissolution_menu, 'delete all false-positive relationships this file\'s alternate group has with other groups', 'Clear out all false-positive relationships this file\'s alternates group has with other groups and resets search status.', win.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_MEDIA_CLEAR_FOCUSED_FALSE_POSITIVES ) )
                
            
            ClientGUIMenus.AppendMenu( duplicates_action_submenu, duplicates_single_dissolution_menu, 'remove/reset for this file' )
            
        
        if multiple_selected:
            
            if HG.client_controller.new_options.GetBoolean( 'advanced_mode' ):
                
                duplicates_multiple_dissolution_menu = QW.QMenu( duplicates_action_submenu )
                
                ClientGUIMenus.AppendMenuItem( duplicates_multiple_dissolution_menu, 'schedule these files to be searched for potentials again', 'Queue these files for another potentials search. Will not remove any existing potentials.', win.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_MEDIA_RESET_POTENTIAL_SEARCH ) )
                ClientGUIMenus.AppendMenuItem( duplicates_multiple_dissolution_menu, 'remove these files\' potential relationships', 'Clear out these files\' potential relationships.', win.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_MEDIA_REMOVE_POTENTIALS ) )
                ClientGUIMenus.AppendMenuItem( duplicates_multiple_dissolution_menu, 'dissolve these files\' duplicate groups completely', 'Completely eliminate these files\' duplicate groups and reset all files\' search status.', win.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_MEDIA_DISSOLVE_DUPLICATE_GROUP ) )
                ClientGUIMenus.AppendMenuItem( duplicates_multiple_dissolution_menu, 'dissolve these files\' alternate groups completely', 'Completely eliminate these files\' alternate groups and all duplicate group members. This resets search status for all involved files.', win.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_MEDIA_DISSOLVE_ALTERNATE_GROUP ) )
                ClientGUIMenus.AppendMenuItem( duplicates_multiple_dissolution_menu, 'delete all false-positive relationships these files\' alternate groups have with other groups', 'Clear out all false-positive relationships these files\' alternates groups has with other groups and resets search status.', win.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_MEDIA_CLEAR_FALSE_POSITIVES ) )
                
                ClientGUIMenus.AppendMenu( duplicates_action_submenu, duplicates_multiple_dissolution_menu, 'remove/reset for all selected' )
                
            
        
        ClientGUIMenus.AppendMenu( duplicates_menu, duplicates_action_submenu, 'set relationship' )
        
    
    if len( duplicates_menu.actions() ) == 0:
        
        ClientGUIMenus.AppendMenuLabel( duplicates_menu, 'no file relationships or actions available for this file at present' )
        
    
    ClientGUIMenus.AppendMenu( menu, duplicates_menu, 'file relationships' )
    

def AddFileViewingStatsMenu( menu, medias: typing.Collection[ ClientMedia.Media ] ):
    
    if len( medias ) == 0:
        
        return
        
    
    view_style = HG.client_controller.new_options.GetInteger( 'file_viewing_stats_menu_display' )
    
    if view_style == CC.FILE_VIEWING_STATS_MENU_DISPLAY_NONE:
        
        return
        
    
    if len( medias ) == 1:
        
        ( media, ) = medias
        
        fvsm = media.GetFileViewingStatsManager()
        
    else:
        
        fvsm = ClientMediaManagers.FileViewingStatsManager.STATICGenerateCombinedManager( [ media.GetFileViewingStatsManager() for media in medias ] )
        
    
    if view_style == CC.FILE_VIEWING_STATS_MENU_DISPLAY_MEDIA_AND_PREVIEW_SUMMED:
        
        combined_line = fvsm.GetPrettyViewsLine( ( CC.CANVAS_MEDIA_VIEWER, CC.CANVAS_PREVIEW ) )
        
        ClientGUIMenus.AppendMenuLabel( menu, combined_line )
        
    else:
        
        media_line = fvsm.GetPrettyViewsLine( ( CC.CANVAS_MEDIA_VIEWER, ) )
        preview_line = fvsm.GetPrettyViewsLine( ( CC.CANVAS_PREVIEW, ) )
        
        if view_style == CC.FILE_VIEWING_STATS_MENU_DISPLAY_MEDIA_ONLY:
            
            ClientGUIMenus.AppendMenuLabel( menu, media_line )
            
        elif view_style == CC.FILE_VIEWING_STATS_MENU_DISPLAY_MEDIA_AND_PREVIEW_IN_SUBMENU:
            
            submenu = QW.QMenu( menu )
            
            ClientGUIMenus.AppendMenuLabel( submenu, preview_line )
            
            ClientGUIMenus.AppendMenu( menu, submenu, media_line )
            
        elif view_style == CC.FILE_VIEWING_STATS_MENU_DISPLAY_MEDIA_AND_PREVIEW_STACKED:
            
            ClientGUIMenus.AppendMenuLabel( menu, media_line )
            ClientGUIMenus.AppendMenuLabel( menu, preview_line )
            
        
    

def AddKnownURLsViewCopyMenu( win, menu, focus_media, selected_media = None ):
    
    # figure out which urls this focused file has
    
    focus_urls = focus_media.GetLocationsManager().GetURLs()
    
    focus_matched_labels_and_urls = []
    focus_unmatched_urls = []
    focus_labels_and_urls = []
    
    if len( focus_urls ) > 0:
        
        for url in focus_urls:
            
            try:
                
                url_class = HG.client_controller.network_engine.domain_manager.GetURLClass( url )
                
            except HydrusExceptions.URLClassException:
                
                continue
                
            
            if url_class is None:
                
                focus_unmatched_urls.append( url )
                
            else:
                
                label = url_class.GetName() + ': ' + url
                
                focus_matched_labels_and_urls.append( ( label, url ) )
                
            
        
        focus_matched_labels_and_urls.sort()
        focus_unmatched_urls.sort()
        
        focus_labels_and_urls = list( focus_matched_labels_and_urls )
        
        focus_labels_and_urls.extend( ( ( url, url ) for url in focus_unmatched_urls ) )
        
    
    # figure out which urls these selected files have
    
    selected_media_url_classes = set()
    multiple_or_unmatching_selection_url_classes = False
    
    if selected_media is not None and len( selected_media ) > 1:
        
        selected_media = ClientMedia.FlattenMedia( selected_media )
        
        SAMPLE_SIZE = 256
        
        if len( selected_media ) > SAMPLE_SIZE:
            
            selected_media_sample = random.sample( selected_media, SAMPLE_SIZE )
            
        else:
            
            selected_media_sample = selected_media
            
        
        for media in selected_media_sample:
            
            media_urls = media.GetLocationsManager().GetURLs()
            
            for url in media_urls:
                
                try:
                    
                    url_class = HG.client_controller.network_engine.domain_manager.GetURLClass( url )
                    
                except HydrusExceptions.URLClassException:
                    
                    continue
                    
                
                if url_class is None:
                    
                    multiple_or_unmatching_selection_url_classes = True
                    
                else:
                    
                    selected_media_url_classes.add( url_class )
                    
                
            
        
        if len( selected_media_url_classes ) > 1:
            
            multiple_or_unmatching_selection_url_classes = True
            
        
    
    if len( focus_labels_and_urls ) > 0 or len( selected_media_url_classes ) > 0 or multiple_or_unmatching_selection_url_classes:
        
        urls_menu = QW.QMenu( menu )
        
        urls_visit_menu = QW.QMenu( urls_menu )
        urls_copy_menu = QW.QMenu( urls_menu )
        
        # copy each this file's urls (of a particular type)
        
        if len( focus_labels_and_urls ) > 0:
            
            for ( label, url ) in focus_labels_and_urls:
                
                ClientGUIMenus.AppendMenuItem( urls_visit_menu, label, 'Open this url in your web browser.', ClientPaths.LaunchURLInWebBrowser, url )
                ClientGUIMenus.AppendMenuItem( urls_copy_menu, label, 'Copy this url to your clipboard.', HG.client_controller.pub, 'clipboard', 'text', url )
                
            
        
        # copy this file's urls
        
        there_are_focus_url_classes_to_action = len( focus_matched_labels_and_urls ) > 1
        multiple_or_unmatching_focus_url_classes = len( focus_unmatched_urls ) > 0 and len( focus_labels_and_urls ) > 1 # if there are unmatched urls and more than one thing total
        
        if there_are_focus_url_classes_to_action or multiple_or_unmatching_focus_url_classes:
            
            ClientGUIMenus.AppendSeparator( urls_visit_menu )
            ClientGUIMenus.AppendSeparator( urls_copy_menu )
            
        
        if there_are_focus_url_classes_to_action:
            
            urls = [ url for ( label, url ) in focus_matched_labels_and_urls ]
            
            label = 'open this file\'s ' + HydrusData.ToHumanInt( len( urls ) ) + ' recognised urls in your web browser'
            
            ClientGUIMenus.AppendMenuItem( urls_visit_menu, label, 'Open these urls in your web browser.', ClientGUIMedia.OpenURLs, urls )
            
            urls_string = os.linesep.join( urls )
            
            label = 'copy this file\'s ' + HydrusData.ToHumanInt( len( urls ) ) + ' recognised urls to your clipboard'
            
            ClientGUIMenus.AppendMenuItem( urls_copy_menu, label, 'Copy these urls to your clipboard.', HG.client_controller.pub, 'clipboard', 'text', urls_string )
            
        
        if multiple_or_unmatching_focus_url_classes:
            
            urls = [ url for ( label, url ) in focus_labels_and_urls ]
            
            label = 'open this file\'s ' + HydrusData.ToHumanInt( len( urls ) ) + ' urls in your web browser'
            
            ClientGUIMenus.AppendMenuItem( urls_visit_menu, label, 'Open these urls in your web browser.', ClientGUIMedia.OpenURLs, urls )
            
            urls_string = os.linesep.join( urls )
            
            label = 'copy this file\'s ' + HydrusData.ToHumanInt( len( urls ) ) + ' urls to your clipboard'
            
            ClientGUIMenus.AppendMenuItem( urls_copy_menu, label, 'Copy this url to your clipboard.', HG.client_controller.pub, 'clipboard', 'text', urls_string )
            
        
        # now by url match type
        
        there_are_selection_url_classes_to_action = len( selected_media_url_classes ) > 0
        
        if there_are_selection_url_classes_to_action or multiple_or_unmatching_selection_url_classes:
            
            ClientGUIMenus.AppendSeparator( urls_visit_menu )
            ClientGUIMenus.AppendSeparator( urls_copy_menu )
            
        
        if there_are_selection_url_classes_to_action:
            
            selected_media_url_classes = list( selected_media_url_classes )
            
            selected_media_url_classes.sort( key = lambda url_class: url_class.GetName() )
            
            for url_class in selected_media_url_classes:
                
                label = 'open files\' ' + url_class.GetName() + ' urls in your web browser'
                
                ClientGUIMenus.AppendMenuItem( urls_visit_menu, label, 'Open this url class in your web browser for all files.', ClientGUIMedia.OpenMediaURLClassURLs, selected_media, url_class )
                
                label = 'copy files\' ' + url_class.GetName() + ' urls'
                
                ClientGUIMenus.AppendMenuItem( urls_copy_menu, label, 'Copy this url class for all files.', ClientGUIMedia.CopyMediaURLClassURLs, selected_media, url_class )
                
            
        
        # now everything
        
        if multiple_or_unmatching_selection_url_classes:
            
            label = 'open all files\' urls'
            
            ClientGUIMenus.AppendMenuItem( urls_visit_menu, label, 'Open urls in your web browser for all files.', ClientGUIMedia.OpenMediaURLs, selected_media )
            
            label = 'copy all files\' urls'
            
            ClientGUIMenus.AppendMenuItem( urls_copy_menu, label, 'Copy urls for all files.', ClientGUIMedia.CopyMediaURLs, selected_media )
            
        
        #
        
        ClientGUIMenus.AppendMenu( urls_menu, urls_visit_menu, 'open' )
        ClientGUIMenus.AppendMenu( urls_menu, urls_copy_menu, 'copy' )
        
        ClientGUIMenus.AppendMenu( menu, urls_menu, 'known urls' )
        
    

def AddLocalFilesMoveAddToMenu( win: QW.QWidget, menu: QW.QMenu, local_duplicable_to_file_service_keys: typing.Collection[ bytes ], local_moveable_from_and_to_file_service_keys: typing.Collection[ typing.Tuple[ bytes, bytes ] ], multiple_selected: bool, process_application_command_call ):
    
    if len( local_duplicable_to_file_service_keys ) == 0 and len( local_moveable_from_and_to_file_service_keys ) == 0:
        
        return
        
    
    local_action_menu = QW.QMenu( menu )
    
    if len( local_duplicable_to_file_service_keys ) > 0:
        
        menu_tuples = []
        
        for s_k in local_duplicable_to_file_service_keys:
            
            application_command = CAC.ApplicationCommand(
                command_type = CAC.APPLICATION_COMMAND_TYPE_CONTENT,
                data = ( s_k, HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ADD, None )
            )
            
            label = HG.client_controller.services_manager.GetName( s_k )
            description = 'Duplicate the files to this local file service.'
            call = HydrusData.Call( process_application_command_call, application_command )
            
            menu_tuples.append( ( label, description, call ) )
            
        
        if multiple_selected:
            
            submenu_name = 'add selected to'
            
        else:
            
            submenu_name = 'add to'
            
        
        ClientGUIMenus.AppendMenuOrItem( local_action_menu, submenu_name, menu_tuples )
        
    
    if len( local_moveable_from_and_to_file_service_keys ) > 0:
        
        menu_tuples = []
        
        for ( source_s_k, dest_s_k ) in local_moveable_from_and_to_file_service_keys:
            
            application_command = CAC.ApplicationCommand(
                command_type = CAC.APPLICATION_COMMAND_TYPE_CONTENT,
                data = ( dest_s_k, HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_MOVE, source_s_k )
            )
            
            label = 'from {} to {}'.format( HG.client_controller.services_manager.GetName( source_s_k ), HG.client_controller.services_manager.GetName( dest_s_k ) )
            description = 'Add the files to the destination and delete from the source.'
            call = HydrusData.Call( process_application_command_call, application_command )
            
            menu_tuples.append( ( label, description, call ) )
            
        
        if multiple_selected:
            
            submenu_name = 'move selected'
            
        else:
            
            submenu_name = 'move'
            
        
        ClientGUIMenus.AppendMenuOrItem( local_action_menu, submenu_name, menu_tuples )
        
    
    ClientGUIMenus.AppendMenu( menu, local_action_menu, 'local services' )
    

def AddManageFileViewingStatsMenu( win: QW.QWidget, menu: QW.QMenu, flat_medias: typing.Collection[ ClientMedia.MediaSingleton ] ):
    
    # add test here for if media actually has stats, edit them, all that
    
    submenu = QW.QMenu( menu )
    
    ClientGUIMenus.AppendMenuItem( submenu, 'clear', 'Clear all the recorded file viewing stats for the selected files.', ClientGUIMedia.DoClearFileViewingStats, win, flat_medias )
    
    ClientGUIMenus.AppendMenu( menu, submenu, 'viewing stats' )
    

def AddPrettyInfoLines( menu, pretty_info_lines ):
    
    def add_pretty_info_str( m, line ):
        
        ClientGUIMenus.AppendMenuLabel( m, line, line )
        
    
    def add_pretty_info_rows( m, rows ):
        
        for row in rows:
            
            if isinstance( row, str ):
                
                add_pretty_info_str( m, row )
                
            else:
                
                try:
                    
                    ( submenu_label, rows ) = row
                    
                except:
                    
                    add_pretty_info_str( m, 'unknown submenu' )
                    
                    continue
                    
                
                lines_submenu = QW.QMenu( m )
                
                add_pretty_info_rows( lines_submenu, rows )
                
                ClientGUIMenus.AppendMenu( m, lines_submenu, submenu_label )
                
            
        
    
    add_pretty_info_rows( menu, pretty_info_lines )
    

def AddServiceKeyLabelsToMenu( menu, service_keys, phrase ):
    
    services_manager = HG.client_controller.services_manager
    
    if len( service_keys ) == 1:
        
        ( service_key, ) = service_keys
        
        name = services_manager.GetName( service_key )
        
        label = phrase + ' ' + name
        
        ClientGUIMenus.AppendMenuLabel( menu, label )
        
    else:
        
        submenu = QW.QMenu( menu )
        
        for service_key in service_keys:
            
            name = services_manager.GetName( service_key )
            
            ClientGUIMenus.AppendMenuLabel( submenu, name )
            
        
        ClientGUIMenus.AppendMenu( menu, submenu, phrase + '\u2026' )
        
    

def AddServiceKeysToMenu( menu, service_keys, submenu_name, description, bare_call ):
    
    menu_tuples = []
    
    services_manager = HG.client_controller.services_manager
    
    for service_key in service_keys:
        
        label = services_manager.GetName( service_key )
        
        this_call = HydrusData.Call( bare_call, service_key )
        
        menu_tuples.append( ( label, description, this_call ) )
        
    
    ClientGUIMenus.AppendMenuOrItem( menu, submenu_name, menu_tuples )
    
