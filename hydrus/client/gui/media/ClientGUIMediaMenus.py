import collections
import collections.abc
import random

from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusData
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusSerialisable
from hydrus.core.files.images import HydrusImageHandling

from hydrus.client import ClientApplicationCommand as CAC
from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientLocation
from hydrus.client import ClientPaths
from hydrus.client.gui import ClientGUIAsync
from hydrus.client.gui import ClientGUIMenus
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.media import ClientGUIMediaModalActions
from hydrus.client.gui.media import ClientGUIMediaSimpleActions
from hydrus.client.media import ClientMedia
from hydrus.client.media import ClientMediaManagers
from hydrus.client.media import ClientMediaResult
from hydrus.client.media import ClientMediaResultPrettyInfoObjects
from hydrus.client.networking import ClientNetworkingFunctions
from hydrus.client.search import ClientSearchPredicate

def AddDuplicatesMenu( win: QW.QWidget, command_processor: CAC.ApplicationCommandProcessorMixin, menu: QW.QMenu, location_context: ClientLocation.LocationContext, focus_media_result: ClientMediaResult.MediaResult, num_selected: int, collections_selected: bool ):
    
    # TODO: I am hesitating making this async since we'll have duplicate relations available in the MediaResult soon enough
    # it would be great to have it in the Canvas though, hence the refactoring. needs a bit more reworking for that, but a good step forward
    
    multiple_selected = num_selected > 1
    
    duplicates_menu = ClientGUIMenus.GenerateMenu( menu )
    
    focused_hash = focus_media_result.GetHash()
    
    combined_local_location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY )
    
    if CG.client_controller.DBCurrentlyDoingJob():
        
        file_duplicate_info = {}
        hydrus_local_file_storage_file_duplicate_info = {}
        
    else:
        
        file_duplicate_info = CG.client_controller.Read( 'file_duplicate_info', location_context, focused_hash )
        
        if location_context.current_service_keys.isdisjoint( CG.client_controller.services_manager.GetServiceKeys( HC.SPECIFIC_LOCAL_FILE_SERVICES ) ):
            
            hydrus_local_file_storage_file_duplicate_info = {}
            
        else:
            
            hydrus_local_file_storage_file_duplicate_info = CG.client_controller.Read( 'file_duplicate_info', combined_local_location_context, focused_hash )
            
        
    
    focus_is_in_duplicate_group = False
    focus_is_in_alternate_group = False
    focus_has_fps = False
    focus_has_potentials = False
    focus_can_be_searched = focus_media_result.GetMime() in HC.FILES_THAT_HAVE_PERCEPTUAL_HASH
    
    if len( file_duplicate_info ) == 0:
        
        ClientGUIMenus.AppendMenuLabel( duplicates_menu, 'could not fetch file\'s duplicates (db currently locked)' )
        
    else:
        
        view_duplicate_relations_jobs = []
        
        if len( file_duplicate_info[ 'counts' ] ) > 0:
            
            view_duplicate_relations_jobs.append( ( location_context, file_duplicate_info ) )
            
        
        if len( hydrus_local_file_storage_file_duplicate_info ) > 0 and len( hydrus_local_file_storage_file_duplicate_info[ 'counts' ] ) > 0 and hydrus_local_file_storage_file_duplicate_info != file_duplicate_info:
            
            view_duplicate_relations_jobs.append( ( combined_local_location_context, hydrus_local_file_storage_file_duplicate_info ) )
            
        
        for ( job_location_context, job_duplicate_info ) in view_duplicate_relations_jobs:
            
            file_duplicate_types_to_counts = job_duplicate_info[ 'counts' ]
            
            ClientGUIMenus.AppendSeparator( duplicates_menu )
            
            if len( view_duplicate_relations_jobs ) > 1:
                
                label = '-for {}-'.format( job_location_context.ToString( CG.client_controller.services_manager.GetName ) )
                
                ClientGUIMenus.AppendMenuLabel( duplicates_menu, label )
                
            
            if HC.DUPLICATE_MEMBER in file_duplicate_types_to_counts:
                
                ClientGUIMenus.AppendMenuLabel( duplicates_menu, 'this file is in a duplicate file group' )
                
                if job_duplicate_info[ 'is_king' ]:
                    
                    ClientGUIMenus.AppendMenuLabel( duplicates_menu, 'this is the best quality file of its group' )
                    
                else:
                    
                    num_other_dupe_members_in_this_domain = file_duplicate_types_to_counts[ HC.DUPLICATE_MEMBER ]
                    
                    if num_other_dupe_members_in_this_domain == 0:
                        
                        ClientGUIMenus.AppendMenuLabel( duplicates_menu, 'cannot show the best quality file of this file\'s group here, it is not in this domain', 'The king of this group has probably been deleted from this domain.' )
                        
                    else:
                        
                        ClientGUIMenus.AppendMenuItem( duplicates_menu, 'show the best quality file of this file\'s group', 'Load up a new search with this file\'s best quality duplicate.', ClientGUIMediaSimpleActions.ShowDuplicatesInNewPage, job_location_context, focused_hash, HC.DUPLICATE_KING )
                        
                    
                
                ClientGUIMenus.AppendSeparator( duplicates_menu )
                
            
            for duplicate_type in ( HC.DUPLICATE_MEMBER, HC.DUPLICATE_ALTERNATE, HC.DUPLICATE_FALSE_POSITIVE, HC.DUPLICATE_POTENTIAL ):
                
                if duplicate_type in file_duplicate_types_to_counts:
                    
                    count = file_duplicate_types_to_counts[ duplicate_type ]
                    
                    if count > 0:
                        
                        label = 'view {} {}'.format( HydrusNumbers.ToHumanInt( count ), HC.duplicate_type_string_lookup[ duplicate_type ] )
                        
                        ClientGUIMenus.AppendMenuItem( duplicates_menu, label, 'Show these duplicates in a new page.', ClientGUIMediaSimpleActions.ShowDuplicatesInNewPage, job_location_context, focused_hash, duplicate_type )
                        
                        if duplicate_type == HC.DUPLICATE_MEMBER:
                            
                            focus_is_in_duplicate_group = True
                            
                        elif duplicate_type == HC.DUPLICATE_ALTERNATE:
                            
                            focus_is_in_alternate_group = True
                            
                        elif duplicate_type == HC.DUPLICATE_FALSE_POSITIVE:
                            
                            focus_has_fps = True
                            
                        elif duplicate_type == HC.DUPLICATE_POTENTIAL:
                            
                            focus_has_potentials = True
                            
                        
                    
                
            
        
    
    if len( duplicates_menu.actions() ) == 0:
        
        ClientGUIMenus.AppendMenuLabel( duplicates_menu, 'this file has no duplicate relationships' )
        
    
    ClientGUIMenus.AppendSeparator( duplicates_menu )
    
    focus_is_definitely_king = len( file_duplicate_info ) > 0 and file_duplicate_info[ 'is_king' ]
    
    dissolution_actions_available = focus_can_be_searched or focus_is_in_duplicate_group or focus_is_in_alternate_group or focus_has_fps
    
    single_action_available = dissolution_actions_available or not focus_is_definitely_king
    
    if multiple_selected or single_action_available:
        
        if len( file_duplicate_info ) == 0:
            
            ClientGUIMenus.AppendMenuLabel( duplicates_menu, 'could not fetch info to check for available file actions (db currently locked)' )
            
        else:
            
            if not focus_is_definitely_king:
                
                ClientGUIMenus.AppendMenuItem( duplicates_menu, 'set this file as the best quality of its group', 'Set the focused media to be the King of its group.', command_processor.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_MEDIA_SET_FOCUSED_KING ) )
                
            
        
        ClientGUIMenus.AppendSeparator( duplicates_menu )
        
        if multiple_selected:
            
            label = 'set this file as better than the ' + HydrusNumbers.ToHumanInt( num_selected - 1 ) + ' other selected'
            
            ClientGUIMenus.AppendMenuItem( duplicates_menu, label, 'Set the focused media to be better than the other selected files.', command_processor.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_MEDIA_SET_FOCUSED_BETTER ) )
            
            ClientGUIMenus.AppendMenuItem( duplicates_menu, 'set all selected as same quality duplicates', 'Set all the selected files as same quality duplicates.', command_processor.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_MEDIA_SET_SAME_QUALITY ) )
            
            ClientGUIMenus.AppendSeparator( duplicates_menu )
            
            ClientGUIMenus.AppendMenuItem( duplicates_menu, 'set all selected as alternates', 'Set all the selected files as alternates.', command_processor.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_MEDIA_SET_ALTERNATE ) )
            
            ClientGUIMenus.AppendMenuItem( duplicates_menu, 'set a relationship with custom metadata merge options', 'Choose which duplicates status to set to this selection and customise non-default duplicate metadata merge options.', command_processor.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_MEDIA_SET_CUSTOM ) )
            
            if collections_selected:
                
                ClientGUIMenus.AppendSeparator( duplicates_menu )
                
                ClientGUIMenus.AppendMenuItem( duplicates_menu, 'set selected collections as groups of alternates', 'Set files in the selection which are collected together as alternates.', command_processor.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_MEDIA_SET_ALTERNATE_COLLECTIONS ) )
                
            
            #
            
            ClientGUIMenus.AppendSeparator( duplicates_menu )
            
            duplicates_edit_action_submenu = ClientGUIMenus.GenerateMenu( duplicates_menu )
            
            for duplicate_type in ( HC.DUPLICATE_BETTER, HC.DUPLICATE_SAME_QUALITY ):
                
                ClientGUIMenus.AppendMenuItem( duplicates_edit_action_submenu, 'for ' + HC.duplicate_type_string_lookup[duplicate_type], 'Edit what happens when you set this status.', ClientGUIMediaModalActions.EditDuplicateContentMergeOptions, win, duplicate_type )
                
            
            if CG.client_controller.new_options.GetBoolean( 'advanced_mode' ):
                
                ClientGUIMenus.AppendMenuItem( duplicates_edit_action_submenu, 'for ' + HC.duplicate_type_string_lookup[HC.DUPLICATE_ALTERNATE] + ' (advanced!)', 'Edit what happens when you set this status.', ClientGUIMediaModalActions.EditDuplicateContentMergeOptions, win, HC.DUPLICATE_ALTERNATE )
                
            
            ClientGUIMenus.AppendMenu( duplicates_menu, duplicates_edit_action_submenu, 'edit default duplicate metadata merge options' )
            
            #
            
            ClientGUIMenus.AppendSeparator( duplicates_menu )
            
            ClientGUIMenus.AppendMenuItem( duplicates_menu, 'set all possible pair combinations as \'potential\' duplicates for the duplicates filter.', 'Queue all these files up in the duplicates filter.', command_processor.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_MEDIA_SET_POTENTIAL ) )
            
        
        ClientGUIMenus.AppendSeparator( duplicates_menu )
        
        remove_actions_available = ( focus_is_in_duplicate_group and not focus_is_definitely_king ) or focus_is_in_alternate_group
        
        if remove_actions_available:
            
            duplicates_single_remove_menu = ClientGUIMenus.GenerateMenu( duplicates_menu )
            
            if focus_is_in_duplicate_group and not focus_is_definitely_king:
                
                ClientGUIMenus.AppendMenuItem( duplicates_single_remove_menu, 'remove this file from its duplicate group', 'Extract this file from its duplicate group and reset its search status.', command_processor.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_MEDIA_REMOVE_FOCUSED_FROM_DUPLICATE_GROUP ) )
                
            
            if focus_is_in_alternate_group:
                
                ClientGUIMenus.AppendMenuItem( duplicates_single_remove_menu, 'remove this file\'s duplicate group from its alternate group', 'Extract this file\'s duplicate group from its alternate group and reset the duplicate group\'s search status.', command_processor.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_MEDIA_REMOVE_FOCUSED_FROM_ALTERNATE_GROUP ) )
                
            
            ClientGUIMenus.AppendMenu( duplicates_menu, duplicates_single_remove_menu, 'remove for this file' )
            
        
        if dissolution_actions_available:
            
            ClientGUIMenus.AppendSeparator( duplicates_menu )
            
            duplicates_single_dissolution_menu = ClientGUIMenus.GenerateMenu( duplicates_menu )
            
            if focus_is_in_duplicate_group:
                
                ClientGUIMenus.AppendMenuItem( duplicates_single_dissolution_menu, 'DUPLICATE WIPE: dissolve this file\'s duplicate group', 'Completely eliminate this file\'s duplicate group and reset all files\' search status.', command_processor.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_MEDIA_DISSOLVE_FOCUSED_DUPLICATE_GROUP ) )
                
            
            if focus_is_in_alternate_group:
                
                ClientGUIMenus.AppendMenuItem( duplicates_single_dissolution_menu, 'EVEN BIGGER WIPE: dissolve this file\'s alternate group', 'Completely eliminate this file\'s alternate group, undoing all alternate decisions. This resets search status for all involved files.', command_processor.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_MEDIA_DISSOLVE_FOCUSED_ALTERNATE_GROUP ) )
                
            
            if focus_has_fps:
                
                ClientGUIMenus.AppendMenuItem( duplicates_single_dissolution_menu, 'delete all false-positive relationships this file\'s alternate group has with other groups', 'Clear out all false-positive relationships this file\'s alternates group has with other groups and resets search status.', command_processor.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_MEDIA_CLEAR_ALL_FOCUSED_FALSE_POSITIVES ) )
                
            
            ClientGUIMenus.AppendSeparator( duplicates_single_dissolution_menu )
            
            if focus_can_be_searched:
                
                ClientGUIMenus.AppendMenuItem( duplicates_single_dissolution_menu, 'schedule this file to be searched for potentials again', 'Queue this file for another potentials search. Will not remove any existing potentials.', command_processor.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_MEDIA_RESET_FOCUSED_POTENTIAL_SEARCH ) )
                
            
            if focus_has_potentials:
                
                ClientGUIMenus.AppendMenuItem( duplicates_single_dissolution_menu, 'delete all this file\'s potential relationships', 'Clear out this file\'s potential relationships.', command_processor.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_MEDIA_REMOVE_FOCUSED_POTENTIALS ) )
                
            
            ClientGUIMenus.AppendMenu( duplicates_menu, duplicates_single_dissolution_menu, 'reset for this file' )
            
        
        if multiple_selected:
            
            duplicates_multiple_remove_menu = ClientGUIMenus.GenerateMenu( duplicates_menu )
            
            ClientGUIMenus.AppendMenuItem( duplicates_multiple_remove_menu, 'delete all false-positive relationships these files\' alternate groups have between each other', 'Clear out all false-positive relationships these files\' alternates groups have with each other and reset search status.', command_processor.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_MEDIA_CLEAR_INTERNAL_FALSE_POSITIVES ) )
            
            ClientGUIMenus.AppendMenu( duplicates_menu, duplicates_multiple_remove_menu, 'remove for all selected' )
            
            #
            
            duplicates_multiple_dissolution_menu = ClientGUIMenus.GenerateMenu( duplicates_menu )
            
            ClientGUIMenus.AppendMenuItem( duplicates_multiple_dissolution_menu, 'DUPLICATE WIPE: completely dissolve these files\' duplicate groups', 'Completely eliminate these files\' duplicate groups and reset all files\' search status.', command_processor.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_MEDIA_DISSOLVE_DUPLICATE_GROUP ) )
            ClientGUIMenus.AppendMenuItem( duplicates_multiple_dissolution_menu, 'EVEN BIGGER WIPE: completely dissolve these files\' alternate groups', 'Completely eliminate these files\' alternate groups, undoing all alternate decisions. This resets search status for all involved files.', command_processor.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_MEDIA_DISSOLVE_ALTERNATE_GROUP ) )
            ClientGUIMenus.AppendSeparator( duplicates_multiple_dissolution_menu )
            ClientGUIMenus.AppendMenuItem( duplicates_multiple_dissolution_menu, 'delete all false-positive relationships these files\' alternate groups have with other groups', 'Clear out all false-positive relationships these files\' alternates groups has with other groups and reset search status.', command_processor.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_MEDIA_CLEAR_ALL_FALSE_POSITIVES ) )
            ClientGUIMenus.AppendSeparator( duplicates_multiple_dissolution_menu )
            ClientGUIMenus.AppendMenuItem( duplicates_multiple_dissolution_menu, 'schedule these files to be searched for potentials again', 'Queue these files for another potentials search. Will not remove any existing potentials or real duplicate relationships.', command_processor.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_MEDIA_RESET_POTENTIAL_SEARCH ) )
            ClientGUIMenus.AppendMenuItem( duplicates_multiple_dissolution_menu, 'delete these files\' potential relationships', 'Clear out these files\' potential relationships.', command_processor.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_MEDIA_REMOVE_POTENTIALS ) )
            
            ClientGUIMenus.AppendMenu( duplicates_menu, duplicates_multiple_dissolution_menu, 'advanced: reset for all selected' )
            
        
    
    if len( duplicates_menu.actions() ) == 0:
        
        ClientGUIMenus.AppendMenuLabel( duplicates_menu, 'no file relationships or actions available for this file at present' )
        
    
    ClientGUIMenus.AppendMenu( menu, duplicates_menu, 'file relationships' )
    

def AddFileViewingStatsMenu( menu, medias: collections.abc.Collection[ ClientMedia.Media ] ):
    
    if len( medias ) == 0:
        
        return
        
        
    
    desired_canvas_types = CG.client_controller.new_options.GetIntegerList( 'file_viewing_stats_interesting_canvas_types' )
    
    if len( desired_canvas_types ) == 0:
        
        return
        
    
    if len( medias ) == 1:
        
        ( media, ) = medias
        
        fvsm = media.GetFileViewingStatsManager()
        
    else:
        
        fvsm = ClientMediaManagers.FileViewingStatsManager.STATICGenerateCombinedManager( [ media.GetFileViewingStatsManager() for media in medias ] )
        
    
    canvas_types_with_views = [ canvas_type for canvas_type in desired_canvas_types if fvsm.HasViews( canvas_type ) ]
    
    sum_appropriate = len( canvas_types_with_views ) > 1
    
    lines = [ fvsm.GetPrettyViewsLine( ( canvas_type, ) ) for canvas_type in canvas_types_with_views ]
    
    view_style = CG.client_controller.new_options.GetInteger( 'file_viewing_stats_menu_display' )
    
    if view_style == CC.FILE_VIEWING_STATS_MENU_DISPLAY_SUMMED_AND_THEN_SUBMENU and sum_appropriate:
        
        submenu = ClientGUIMenus.GenerateMenu( menu )
        
        for line in lines:
            
            ClientGUIMenus.AppendMenuLabel( submenu, line )
            
        
        summed_submenu_line = fvsm.GetPrettyViewsLine( canvas_types_with_views )
        
        ClientGUIMenus.AppendMenu( menu, submenu, summed_submenu_line )
        
    else:
        
        for line in lines:
            
            ClientGUIMenus.AppendMenuLabel( menu, line )
            
        
    
    

def AddKnownURLsViewCopyMenu( win: QW.QWidget, command_processor: CAC.ApplicationCommandProcessorMixin, menu, focus_media, num_files_selected: int, selected_media = None ):
    
    # figure out which urls this focused file has
    
    focus_urls = []
    
    if focus_media is not None:
        
        if focus_media.IsCollection():
            
            focus_media = focus_media.GetDisplayMedia()
            
        
        focus_urls = focus_media.GetLocationsManager().GetURLs()
        
    
    focus_media_url_classes = set()
    focus_matched_labels_and_urls = []
    focus_unmatched_urls = []
    focus_labels_and_urls = []
    
    if len( focus_urls ) > 0:
        
        for url in focus_urls:
            
            try:
                
                url_class = CG.client_controller.network_engine.domain_manager.GetURLClass( url )
                
            except HydrusExceptions.URLClassException:
                
                continue
                
            
            if url_class is None:
                
                focus_unmatched_urls.append( url )
                
            else:
                
                label = url_class.GetName() + ': ' + ClientNetworkingFunctions.ConvertURLToHumanString( url )
                
                focus_matched_labels_and_urls.append( ( label, url ) )
                
                focus_media_url_classes.add( url_class )
                
            
        
        focus_matched_labels_and_urls.sort()
        focus_unmatched_urls.sort()
        
        focus_labels_and_urls = list( focus_matched_labels_and_urls )
        
        focus_labels_and_urls.extend( ( ( ClientNetworkingFunctions.ConvertURLToHumanString( url ), url ) for url in focus_unmatched_urls ) )
        
    
    # figure out which urls these selected files have
    
    selected_media_url_classes = set()
    multiple_or_unmatching_selection_url_classes = False
    
    if selected_media is not None:
        
        selected_media = ClientMedia.FlattenMedia( selected_media )
        
        if len( selected_media ) > 0:
            
            SAMPLE_SIZE = 256
            
            if len( selected_media ) > SAMPLE_SIZE:
                
                selected_media_sample = random.sample( selected_media, SAMPLE_SIZE )
                
            else:
                
                selected_media_sample = selected_media
                
            
            for media in selected_media_sample:
                
                media_urls = media.GetLocationsManager().GetURLs()
                
                for url in media_urls:
                    
                    try:
                        
                        url_class = CG.client_controller.network_engine.domain_manager.GetURLClass( url )
                        
                    except HydrusExceptions.URLClassException:
                        
                        continue
                        
                    
                    if url_class is None:
                        
                        multiple_or_unmatching_selection_url_classes = True
                        
                    else:
                        
                        selected_media_url_classes.add( url_class )
                        
                    
                
            
            if len( selected_media_url_classes ) > 1:
                
                multiple_or_unmatching_selection_url_classes = True
                
            
        
    
    urls_menu = ClientGUIMenus.GenerateMenu( menu )
    
    if num_files_selected > 1:
        
        description = 'Edit which URLs these files have.'
        
    else:
        
        description = 'Edit which URLs this file has.'
        
    
    ClientGUIMenus.AppendMenuItem( urls_menu, 'manage', description, command_processor.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_MANAGE_FILE_URLS ) )
    
    if len( focus_labels_and_urls ) > 0 or len( selected_media_url_classes ) > 0 or multiple_or_unmatching_selection_url_classes:
        
        urls_visit_menu = ClientGUIMenus.GenerateMenu( urls_menu )
        urls_copy_menu = ClientGUIMenus.GenerateMenu( urls_menu )
        urls_force_refetch_menu = ClientGUIMenus.GenerateMenu( urls_menu )
        
        if len( focus_labels_and_urls ) > 0:
            
            urls_open_page_menu = ClientGUIMenus.GenerateMenu( urls_menu )
            
            # copy each this file's urls (of a particular type)
            
            MAX_TO_SHOW = 15
            
            description = 'Open this url in your web browser.'
            
            ClientGUIMenus.SpamItems( urls_visit_menu, [ ( label, description, HydrusData.Call( ClientPaths.LaunchURLInWebBrowser, url ) ) for ( label, url ) in focus_labels_and_urls ], MAX_TO_SHOW )
            ClientGUIMenus.SpamLabels( urls_copy_menu, focus_labels_and_urls, MAX_TO_SHOW )
            
            description = 'Open a new page with the files that have this url.'
            
            def call_generator( u ):
                
                location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY )
                predicates = [ ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_KNOWN_URLS, value = ( True, 'exact_match', u, f'has url {u}' ) ) ]
                
                page_name = 'url search'
                activate_window = False
                
                c = HydrusData.Call( CG.client_controller.pub, 'new_page_query', location_context, initial_predicates = predicates, page_name = page_name, activate_window = activate_window )
                
                return c
                
            
            ClientGUIMenus.SpamItems( urls_open_page_menu, [ ( f'files with {label}', description, call_generator( url ) ) for ( label, url ) in focus_labels_and_urls ], MAX_TO_SHOW )
            
            if len( focus_labels_and_urls ) > 1:
                
                ClientGUIMenus.AppendSeparator( urls_open_page_menu )
                
                location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY )
                
                url_preds = [ ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_KNOWN_URLS, value = ( True, 'exact_match', url, f'has url {url}' ) ) for ( label, url ) in focus_labels_and_urls ]
                
                predicates = [ ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_OR_CONTAINER, value = url_preds ) ]
                
                page_name = 'url search'
                activate_window = False
                
                c = HydrusData.Call( CG.client_controller.pub, 'new_page_query', location_context, initial_predicates = predicates, page_name = page_name, activate_window = activate_window )
                
                ClientGUIMenus.AppendMenuItem( urls_open_page_menu, 'files with any of the above', 'Open a new page with the files that share any of this file\'s urls.', c )
                
            
        
        if len( focus_media_url_classes ) > 0:
            
            focus_media_url_classes = list( focus_media_url_classes )
            
            focus_media_url_classes.sort( key = lambda url_class: url_class.GetName() )
            
            for url_class in focus_media_url_classes:
                
                label = 'this file\'s ' + url_class.GetName() + ' urls'
                
                ClientGUIMenus.AppendMenuItem( urls_force_refetch_menu, label, 'Re-download these URLs with forced metadata re-fetch enabled.', ClientGUIMediaModalActions.RedownloadURLClassURLsForceRefetch, win, { focus_media }, url_class )
                
            
        
        # copy this file's urls
        
        there_are_focus_url_classes_to_action = len( focus_matched_labels_and_urls ) > 1
        multiple_or_unmatching_focus_url_classes = len( focus_unmatched_urls ) > 0 and len( focus_labels_and_urls ) > 1 # if there are unmatched urls and more than one thing total
        
        if there_are_focus_url_classes_to_action or multiple_or_unmatching_focus_url_classes:
            
            ClientGUIMenus.AppendSeparator( urls_visit_menu )
            ClientGUIMenus.AppendSeparator( urls_copy_menu )
            
        
        if there_are_focus_url_classes_to_action:
            
            urls = [ url for ( label, url ) in focus_matched_labels_and_urls ]
            
            label = 'this file\'s ' + HydrusNumbers.ToHumanInt( len( urls ) ) + ' recognised urls'
            
            ClientGUIMenus.AppendMenuItem( urls_visit_menu, label, 'Open these urls in your web browser.', ClientGUIMediaModalActions.OpenURLs, win, urls )
            
            urls_string = '\n'.join( urls )
            
            ClientGUIMenus.AppendMenuItem( urls_copy_menu, label, 'Copy these urls to your clipboard.', CG.client_controller.pub, 'clipboard', 'text', urls_string )
            
        
        if multiple_or_unmatching_focus_url_classes:
            
            urls = [ url for ( label, url ) in focus_labels_and_urls ]
            
            label = 'this file\'s ' + HydrusNumbers.ToHumanInt( len( urls ) ) + ' urls'
            
            ClientGUIMenus.AppendMenuItem( urls_visit_menu, label, 'Open these urls in your web browser.', ClientGUIMediaModalActions.OpenURLs, win, urls )
            
            urls_string = '\n'.join( urls )
            
            ClientGUIMenus.AppendMenuItem( urls_copy_menu, label, 'Copy this url to your clipboard.', CG.client_controller.pub, 'clipboard', 'text', urls_string )
            
        
        # now by url match type
        
        there_are_selection_url_classes_to_action = len( selected_media_url_classes ) > 0
        
        if there_are_selection_url_classes_to_action or multiple_or_unmatching_selection_url_classes:
            
            ClientGUIMenus.AppendSeparator( urls_visit_menu )
            ClientGUIMenus.AppendSeparator( urls_copy_menu )
            ClientGUIMenus.AppendSeparator( urls_force_refetch_menu )
            
        
        if there_are_selection_url_classes_to_action:
            
            selected_media_url_classes = list( selected_media_url_classes )
            
            selected_media_url_classes.sort( key = lambda url_class: url_class.GetName() )
            
            for url_class in selected_media_url_classes:
                
                label = 'these files\' ' + url_class.GetName() + ' urls'
                
                ClientGUIMenus.AppendMenuItem( urls_visit_menu, label, 'Open this url class in your web browser for all files.', ClientGUIMediaModalActions.OpenMediaURLClassURLs, win, selected_media, url_class )
                
                ClientGUIMenus.AppendMenuItem( urls_copy_menu, label, 'Copy this url class for all files.', ClientGUIMediaSimpleActions.CopyMediaURLClassURLs, selected_media, url_class )
                
                if len( selected_media ) > 1:
                    
                    ClientGUIMenus.AppendMenuItem( urls_force_refetch_menu, label, 'Re-download these URLs with forced metadata re-fetch enabled.', ClientGUIMediaModalActions.RedownloadURLClassURLsForceRefetch, win, selected_media, url_class )
                    
                
            
        
        # now everything
        
        if multiple_or_unmatching_selection_url_classes:
            
            label = 'all these files\' urls'
            
            ClientGUIMenus.AppendMenuItem( urls_visit_menu, label, 'Open all files\' urls in your web browser.', ClientGUIMediaModalActions.OpenMediaURLs, win, selected_media )
            
            label = 'all these files\' urls'
            
            ClientGUIMenus.AppendMenuItem( urls_copy_menu, label, 'Copy all files\' urls.', ClientGUIMediaSimpleActions.CopyMediaURLs, selected_media )
            
        
        #
        
        ClientGUIMenus.AppendMenu( urls_menu, urls_visit_menu, 'open in browser' )
        
        if len( focus_labels_and_urls ) > 0:
            
            ClientGUIMenus.AppendMenu( urls_menu, urls_open_page_menu, 'open in a new page' )
            
        
        ClientGUIMenus.AppendMenu( urls_menu, urls_copy_menu, 'copy' )
        
        ClientGUIMenus.AppendSeparator( urls_menu )
        
        ClientGUIMenus.AppendMenu( urls_menu, urls_force_refetch_menu, 'force metadata refetch' )
        
    
    ClientGUIMenus.AppendMenu( menu, urls_menu, 'urls' )
    

def AddLocalFilesMoveAddToMenu( win: QW.QWidget, menu: QW.QMenu, local_file_service_keys: collections.Counter[ bytes ], local_duplicable_to_file_service_keys: collections.Counter[ bytes ], local_movable_from_and_to_file_service_keys: collections.Counter[ tuple[ bytes, bytes ] ], local_mergable_from_and_to_file_service_keys: collections.Counter[ tuple[ bytes, bytes ] ], multiple_selected: bool, process_application_command_call ):
    
    if len( local_file_service_keys ) > 0:
        
        menu_tuples = []
        
        for ( s_k, count ) in local_file_service_keys.items():
            
            label = f'{CG.client_controller.services_manager.GetName( s_k )} ({HydrusNumbers.ToHumanInt(count)} files)'
            description = label
            call = None
            
            menu_tuples.append( ( label, description, call ) )
            
        
        submenu_name = 'currently in'
        
        ClientGUIMenus.AppendMenuOrItem( menu, submenu_name, menu_tuples )
        
    
    if len( local_duplicable_to_file_service_keys ) > 0:
        
        menu_tuples = []
        
        for ( s_k, count ) in local_duplicable_to_file_service_keys.items():
            
            application_command = CAC.ApplicationCommand(
                command_type = CAC.APPLICATION_COMMAND_TYPE_CONTENT,
                data = ( s_k, HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ADD, None )
            )
            
            label = f'{CG.client_controller.services_manager.GetName( s_k )} ({HydrusNumbers.ToHumanInt(count)} files)'
            description = 'Duplicate the files to this local file domain.'
            call = HydrusData.Call( process_application_command_call, application_command )
            
            menu_tuples.append( ( label, description, call ) )
            
        
        submenu_name = 'add to'
        
        ClientGUIMenus.AppendMenuOrItem( menu, submenu_name, menu_tuples )
        
    
    if len( local_mergable_from_and_to_file_service_keys ) > 0:
        
        menu_tuples = []
        
        for ( ( source_s_k, dest_s_k ), count ) in local_mergable_from_and_to_file_service_keys.items():
            
            application_command = CAC.ApplicationCommand(
                command_type = CAC.APPLICATION_COMMAND_TYPE_CONTENT,
                data = ( dest_s_k, HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_MOVE_MERGE, source_s_k )
            )
            
            label = f'from {CG.client_controller.services_manager.GetName( source_s_k )} to {CG.client_controller.services_manager.GetName( dest_s_k )} ({HydrusNumbers.ToHumanInt(count)} files)'
            description = 'Add the files to the destination and delete from the source. Works when files are already in the destination.'
            call = HydrusData.Call( process_application_command_call, application_command )
            
            menu_tuples.append( ( label, description, call ) )
            
        
        submenu_name = 'move (merge)'
        
        ClientGUIMenus.AppendMenuOrItem( menu, submenu_name, menu_tuples )
        
    
    if len( local_movable_from_and_to_file_service_keys ) > 0:
        
        menu_tuples = []
        
        for ( ( source_s_k, dest_s_k ), count ) in local_movable_from_and_to_file_service_keys.items():
            
            application_command = CAC.ApplicationCommand(
                command_type = CAC.APPLICATION_COMMAND_TYPE_CONTENT,
                data = ( dest_s_k, HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_MOVE, source_s_k )
            )
            
            label = f'from {CG.client_controller.services_manager.GetName( source_s_k )} to {CG.client_controller.services_manager.GetName( dest_s_k )} ({HydrusNumbers.ToHumanInt(count)} files)'
            description = 'Add the files to the destination and delete from the source. Only works on files not already in the destination.'
            call = HydrusData.Call( process_application_command_call, application_command )
            
            menu_tuples.append( ( label, description, call ) )
            
        
        submenu_name = 'move (strict)'
        
        ClientGUIMenus.AppendMenuOrItem( menu, submenu_name, menu_tuples )
        
    

def AddManageFileViewingStatsMenu( win: QW.QWidget, menu: QW.QMenu, flat_medias: collections.abc.Collection[ ClientMedia.MediaSingleton ] ):
    
    # add test here for if media actually has stats, edit them, all that
    
    submenu = ClientGUIMenus.GenerateMenu( menu )
    
    ClientGUIMenus.AppendMenuItem( submenu, 'clear', 'Clear all the recorded file viewing stats for the selected files.', ClientGUIMediaModalActions.DoClearFileViewingStats, win, flat_medias )
    
    ClientGUIMenus.AppendMenu( menu, submenu, 'viewing stats' )
    

def AddOpenMenu( win: QW.QWidget, command_processor: CAC.ApplicationCommandProcessorMixin, menu: QW.QMenu, focused_media: ClientMedia.Media | None, selected_media: collections.abc.Collection[ ClientMedia.Media ] ):
    
    if len( selected_media ) == 0:
        
        return
        
    
    advanced_mode = CG.client_controller.new_options.GetBoolean( 'advanced_mode' )
    
    open_menu = ClientGUIMenus.GenerateMenu( menu )
    
    ClientGUIMenus.AppendMenuItem( open_menu, 'in a new page', 'Copy your current selection into a simple new page.', command_processor.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_OPEN_SELECTION_IN_NEW_PAGE ) )
    ClientGUIMenus.AppendMenuItem( open_menu, 'in a new duplicate filter page', 'Make a new duplicate filter page that searches for these files specifically.', command_processor.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_OPEN_SELECTION_IN_NEW_DUPLICATES_FILTER_PAGE ) )
    
    similar_menu = ClientGUIMenus.GenerateMenu( open_menu )
    
    if focused_media is not None:
        
        if focused_media.HasStaticImages():
            
            ClientGUIMenus.AppendSeparator( similar_menu )
            
            ClientGUIMenus.AppendMenuItem( similar_menu, 'exact match', 'Search the database for files that look precisely like those selected.', command_processor.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_OPEN_SIMILAR_LOOKING_FILES, simple_data = CC.HAMMING_EXACT_MATCH ) )
            ClientGUIMenus.AppendMenuItem( similar_menu, 'very similar', 'Search the database for files that look just like those selected.', command_processor.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_OPEN_SIMILAR_LOOKING_FILES, simple_data = CC.HAMMING_VERY_SIMILAR ) )
            ClientGUIMenus.AppendMenuItem( similar_menu, 'similar', 'Search the database for files that look generally like those selected.', command_processor.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_OPEN_SIMILAR_LOOKING_FILES, simple_data = CC.HAMMING_SIMILAR ) )
            ClientGUIMenus.AppendMenuItem( similar_menu, 'speculative', 'Search the database for files that probably look like those selected. This is sometimes useful for symbols with sharp edges or lines.', command_processor.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_OPEN_SIMILAR_LOOKING_FILES, simple_data = CC.HAMMING_SPECULATIVE ) )
            ClientGUIMenus.AppendSeparator( similar_menu )
            ClientGUIMenus.AppendMenuItem( similar_menu, 'custom', 'Search the database for files that probably look like those selected. This is sometimes useful for symbols with sharp edges or lines.', command_processor.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_OPEN_SIMILAR_LOOKING_FILES ) )
            
            ClientGUIMenus.AppendMenu( open_menu, similar_menu, 'similar files in a new page' )
            
        
        ClientGUIMenus.AppendSeparator( open_menu )
        
        if len( selected_media ) > 1:
            
            prefix = 'focused file '
            
        else:
            
            prefix = ''
            
        
        ClientGUIMenus.AppendMenuItem( open_menu, f'{prefix}in external program', 'Launch this file with your OS\'s default program for it.', command_processor.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_OPEN_FILE_IN_EXTERNAL_PROGRAM ) )
        ClientGUIMenus.AppendMenuItem( open_menu, f'{prefix}in web browser', 'Show this file in your OS\'s web browser.', command_processor.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_OPEN_FILE_IN_WEB_BROWSER ) )
        
        if focused_media.GetLocationsManager().IsLocal():
            
            show_windows_native_options = HC.PLATFORM_WINDOWS
            
            if show_windows_native_options:
                
                ClientGUIMenus.AppendMenuItem( open_menu, f'{prefix}in another program', 'Choose which program to open this file with.', command_processor.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_NATIVE_OPEN_FILE_WITH_DIALOG ) )
                
            
            show_open_in_explorer = advanced_mode and ClientPaths.CAN_OPEN_FILE_LOCATION
            
            if show_open_in_explorer:
                
                ClientGUIMenus.AppendMenuItem( open_menu, f'{prefix}in file browser', 'Show this file in your OS\'s file browser.', command_processor.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_OPEN_FILE_IN_FILE_EXPLORER ) )
                
            
            if show_windows_native_options:
                
                ClientGUIMenus.AppendMenuItem( open_menu, f'{prefix}properties', 'Open your OS\'s properties window for this file.', command_processor.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_NATIVE_OPEN_FILE_PROPERTIES ) )
                
            
        
    
    ClientGUIMenus.AppendMenu( menu, open_menu, 'open' )
    

def AddPrettyMediaResultInfoLines( menu: QW.QMenu, pretty_info_lines: list[ ClientMediaResultPrettyInfoObjects.PrettyMediaResultInfoLine ] ):
    
    def add_pretty_info_str( m: QW.QMenu, line: ClientMediaResultPrettyInfoObjects.PrettyMediaResultInfoLine ):
        
        tt = line.tooltip if line.tooltip != line.text else ''
        
        ClientGUIMenus.AppendMenuLabel( m, line.text, description = tt )
        
    
    def add_pretty_info_rows( m: QW.QMenu, lines ):
        
        for line in lines:
            
            if isinstance( line, ClientMediaResultPrettyInfoObjects.PrettyMediaResultInfoLinesSubmenu ):
                
                submenu_label = line.text
                
                sublines = line.sublines
                
                lines_submenu = ClientGUIMenus.GenerateMenu( m )
                
                add_pretty_info_rows( lines_submenu, sublines )
                
                ClientGUIMenus.AppendMenu( m, lines_submenu, submenu_label )
                
            else:
                
                add_pretty_info_str( m, line )
                
            
        
    
    add_pretty_info_rows( menu, pretty_info_lines )
    

def AddServiceKeyLabelsToMenu( menu, service_keys, phrase ):
    
    services_manager = CG.client_controller.services_manager
    
    if len( service_keys ) == 1:
        
        ( service_key, ) = service_keys
        
        name = services_manager.GetName( service_key )
        
        label = phrase + ' ' + name
        
        ClientGUIMenus.AppendMenuLabel( menu, label )
        
    else:
        
        submenu = ClientGUIMenus.GenerateMenu( menu )
        
        for service_key in service_keys:
            
            name = services_manager.GetName( service_key )
            
            ClientGUIMenus.AppendMenuLabel( submenu, name )
            
        
        ClientGUIMenus.AppendMenu( menu, submenu, phrase + HC.UNICODE_ELLIPSIS )
        
    

def AddServiceKeysToMenu( menu, service_keys, submenu_name, description, bare_call ):
    
    menu_tuples = []
    
    services_manager = CG.client_controller.services_manager
    
    for service_key in service_keys:
        
        label = services_manager.GetName( service_key )
        
        this_call = HydrusData.Call( bare_call, service_key )
        
        menu_tuples.append( ( label, description, this_call ) )
        
    
    ClientGUIMenus.AppendMenuOrItem( menu, submenu_name, menu_tuples )
    

def StartOtherHashMenuFetch( win: QW.QWidget, media: ClientMedia.MediaSingleton, menu_item: QW.QAction, hash_type: str ):
    
    hash = media.GetHash()
    
    def work_callable():
        
        hashes_to_other_hashes = CG.client_controller.Read( 'file_hashes', ( hash, ), 'sha256', hash_type )
        
        return hashes_to_other_hashes
        
    
    def publish_callable( hashes_to_other_hashes: dict[ bytes, bytes ] ):
        
        if not QP.isValid( menu_item ):
            
            return
            
        
        if hash in hashes_to_other_hashes:
            
            desired_hash = hashes_to_other_hashes[ hash ]
            
            menu_item.setText( f'{hash_type} ({desired_hash.hex()})' )
            
        else:
            
            menu_item.setText( f'{hash_type} (unknown)' )
            
        
    
    job = ClientGUIAsync.AsyncQtJob( win, work_callable, publish_callable )
    
    job.start()
    

def AddShareMenu( win: QW.QWidget, command_processor: CAC.ApplicationCommandProcessorMixin, menu: QW.QMenu, focused_media: ClientMedia.Media | None, selected_media: collections.abc.Collection[ ClientMedia.Media ] ):
    
    if focused_media is not None:
        
        focused_media = focused_media.GetDisplayMedia()
        
    
    ipfs_service_keys = set( CG.client_controller.services_manager.GetServiceKeys( ( HC.IPFS, ) ) )
    
    selected_media = ClientMedia.FlattenMedia( selected_media )
    
    focused_is_local = focused_media is not None and focused_media.GetLocationsManager().IsLocal()
    
    # i.e. we aren't just clicked one one guy
    selection_verbs_are_appropriate = len( selected_media ) > 0 and not ( len( selected_media ) == 1 and focused_media in selected_media )
    
    local_selection = [ m for m in selected_media if m.GetLocationsManager().IsLocal() ]
    
    # i.e. we aren't just clicked one one local guy
    local_selection_verbs_are_appropriate = len( local_selection ) > 0 and not ( len( local_selection ) == 1 and focused_media in local_selection )
    
    share_menu = ClientGUIMenus.GenerateMenu( menu )
    
    if len( local_selection ) > 0:
        
        ClientGUIMenus.AppendMenuItem( share_menu, 'export files', 'Export the selected files to an external folder.', command_processor.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_EXPORT_FILES ) )
        
        ClientGUIMenus.AppendSeparator( share_menu )
        
    
    if local_selection_verbs_are_appropriate:
        
        ClientGUIMenus.AppendMenuItem( share_menu, 'copy files', 'Copy these files to your clipboard.', command_processor.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_COPY_FILES, simple_data = CAC.FILE_COMMAND_TARGET_SELECTED_FILES ) )
        
        ClientGUIMenus.AppendMenuItem( share_menu, 'copy paths', 'Copy these files\' paths to your clipboard, just as raw text.', command_processor.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_COPY_FILE_PATHS, simple_data = CAC.FILE_COMMAND_TARGET_SELECTED_FILES ) )
        
    
    if selection_verbs_are_appropriate:
        
        ipfs_service_keys_to_num_filenames = collections.Counter()
        
        for media in selected_media:
            
            ipfs_service_keys_to_num_filenames.update( ipfs_service_keys.intersection( media.GetLocationsManager().GetCurrent() ) )
            
        
        ipfs_service_keys_in_order = sorted( ipfs_service_keys_to_num_filenames.keys(), key = CG.client_controller.services_manager.GetName )
        
        for ipfs_service_key in ipfs_service_keys_in_order:
            
            name = CG.client_controller.services_manager.GetName( ipfs_service_key )
            
            hacky_ipfs_dict = HydrusSerialisable.SerialisableDictionary()
            
            hacky_ipfs_dict[ 'file_command_target' ] = CAC.FILE_COMMAND_TARGET_SELECTED_FILES
            hacky_ipfs_dict[ 'ipfs_service_key' ] = ipfs_service_key
            
            application_command = CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_COPY_FILE_SERVICE_FILENAMES, simple_data = hacky_ipfs_dict )
            
            ClientGUIMenus.AppendMenuItem( share_menu, f'copy {name} multihashes ({HydrusNumbers.ToHumanInt(ipfs_service_keys_to_num_filenames[ipfs_service_key])} hashes)', 'Copy the selected files\' multihashes to the clipboard.', command_processor.ProcessApplicationCommand, application_command )
            
        
        copy_hashes_menu = ClientGUIMenus.GenerateMenu( share_menu )
        
        ClientGUIMenus.AppendMenuItem( copy_hashes_menu, 'sha256', 'Copy these files\' SHA256 hashes to your clipboard.', command_processor.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_COPY_FILE_HASHES, simple_data = ( CAC.FILE_COMMAND_TARGET_SELECTED_FILES, 'sha256' ) ) )
        ClientGUIMenus.AppendMenuItem( copy_hashes_menu, 'md5', 'Copy these files\' MD5 hashes to your clipboard. Your client may not know all of these.', command_processor.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_COPY_FILE_HASHES, simple_data = ( CAC.FILE_COMMAND_TARGET_SELECTED_FILES, 'md5' ) ) )
        ClientGUIMenus.AppendMenuItem( copy_hashes_menu, 'sha1', 'Copy these files\' SHA1 hashes to your clipboard. Your client may not know all of these.', command_processor.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_COPY_FILE_HASHES, simple_data = ( CAC.FILE_COMMAND_TARGET_SELECTED_FILES, 'sha1' ) ) )
        ClientGUIMenus.AppendMenuItem( copy_hashes_menu, 'sha512', 'Copy these files\' SHA512 hashes to your clipboard. Your client may not know all of these.', command_processor.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_COPY_FILE_HASHES, simple_data = ( CAC.FILE_COMMAND_TARGET_SELECTED_FILES, 'sha512' ) ) )
        
        blurhashes = [ media.GetFileInfoManager().blurhash for media in selected_media ]
        blurhashes = [ b for b in blurhashes if b is not None ]
        
        if len( blurhashes ) > 0:
            
            ClientGUIMenus.AppendMenuItem( copy_hashes_menu, f'blurhash ({HydrusNumbers.ToHumanInt(len(blurhashes))} hashes)', 'Copy these files\' blurhashes.', command_processor.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_COPY_FILE_HASHES, simple_data = ( CAC.FILE_COMMAND_TARGET_SELECTED_FILES, 'blurhash' ) ) )
            
        
        pixel_hashes = [ media.GetFileInfoManager().pixel_hash for media in selected_media ]
        pixel_hashes = [ p for p in pixel_hashes if p is not None ]
        
        if len( pixel_hashes ):
            
            ClientGUIMenus.AppendMenuItem( copy_hashes_menu, f'pixel hashes ({HydrusNumbers.ToHumanInt(len(pixel_hashes))} hashes)', 'Copy these files\' pixel hashes.', command_processor.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_COPY_FILE_HASHES, simple_data = ( CAC.FILE_COMMAND_TARGET_SELECTED_FILES, 'pixel_hash' ) ) )
            
        
        ClientGUIMenus.AppendMenu( share_menu, copy_hashes_menu, 'copy hashes' )
        
        ClientGUIMenus.AppendMenuItem( share_menu, 'copy file ids', 'Copy these files\' internal file/hash_ids.', command_processor.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_COPY_FILE_ID, simple_data = CAC.FILE_COMMAND_TARGET_SELECTED_FILES ) )
        
        ClientGUIMenus.AppendSeparator( share_menu )
        
    
    if focused_is_local:
        
        ClientGUIMenus.AppendMenuItem( share_menu, 'copy file', 'Copy this file to your clipboard.', command_processor.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_COPY_FILES, simple_data = CAC.FILE_COMMAND_TARGET_FOCUSED_FILE ) )
        
        ClientGUIMenus.AppendMenuItem( share_menu, 'copy path', 'Copy this file\'s path to your clipboard, just as raw text.', command_processor.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_COPY_FILE_PATHS, simple_data = CAC.FILE_COMMAND_TARGET_FOCUSED_FILE ) )
        
    
    if focused_media is not None:
        
        for ipfs_service_key in ipfs_service_keys.intersection( focused_media.GetLocationsManager().GetCurrent() ):
            
            name = CG.client_controller.services_manager.GetName( ipfs_service_key )
            
            multihash = focused_media.GetLocationsManager().GetServiceFilename( ipfs_service_key )
            
            hacky_ipfs_dict = HydrusSerialisable.SerialisableDictionary()
            
            hacky_ipfs_dict[ 'file_command_target' ] = CAC.FILE_COMMAND_TARGET_FOCUSED_FILE
            hacky_ipfs_dict[ 'ipfs_service_key' ] = ipfs_service_key
            
            application_command = CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_COPY_FILE_SERVICE_FILENAMES, simple_data = hacky_ipfs_dict )
            
            ClientGUIMenus.AppendMenuItem( share_menu, f'copy {name} multihash ({multihash})', 'Copy the selected file\'s multihash to the clipboard.', command_processor.ProcessApplicationCommand, application_command )
            
        
        copy_hash_menu = ClientGUIMenus.GenerateMenu( share_menu )
        
        ClientGUIMenus.AppendMenuItem( copy_hash_menu, 'sha256 ({})'.format( focused_media.GetHash().hex() ), 'Copy this file\'s SHA256 hash to your clipboard.', command_processor.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_COPY_FILE_HASHES, simple_data = ( CAC.FILE_COMMAND_TARGET_FOCUSED_FILE, 'sha256' ) ) )
        md5_menu_item = ClientGUIMenus.AppendMenuItem( copy_hash_menu, 'md5', 'Copy this file\'s MD5 hash to your clipboard. Your client may not know this.', command_processor.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_COPY_FILE_HASHES, simple_data = ( CAC.FILE_COMMAND_TARGET_FOCUSED_FILE, 'md5' ) ) )
        sha1_menu_item = ClientGUIMenus.AppendMenuItem( copy_hash_menu, 'sha1', 'Copy this file\'s SHA1 hash to your clipboard. Your client may not know this.', command_processor.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_COPY_FILE_HASHES, simple_data = ( CAC.FILE_COMMAND_TARGET_FOCUSED_FILE, 'sha1' ) ) )
        sha512_menu_item = ClientGUIMenus.AppendMenuItem( copy_hash_menu, 'sha512', 'Copy this file\'s SHA512 hash to your clipboard. Your client may not know this.', command_processor.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_COPY_FILE_HASHES, simple_data = ( CAC.FILE_COMMAND_TARGET_FOCUSED_FILE, 'sha512' ) ) )
        
        StartOtherHashMenuFetch( copy_hash_menu, focused_media, md5_menu_item, 'md5' )
        StartOtherHashMenuFetch( copy_hash_menu, focused_media, sha1_menu_item, 'sha1' )
        StartOtherHashMenuFetch( copy_hash_menu, focused_media, sha512_menu_item, 'sha512' )
        
        file_info_manager = focused_media.GetMediaResult().GetFileInfoManager()
        
        if file_info_manager.blurhash is not None:
            
            ClientGUIMenus.AppendMenuItem( copy_hash_menu, f'blurhash ({file_info_manager.blurhash})', 'Copy this file\'s blurhash.', command_processor.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_COPY_FILE_HASHES, simple_data = ( CAC.FILE_COMMAND_TARGET_FOCUSED_FILE, 'blurhash' ) ) )
            
        
        if file_info_manager.pixel_hash is not None:
            
            ClientGUIMenus.AppendMenuItem( copy_hash_menu, f'pixel hash ({file_info_manager.pixel_hash.hex()})', 'Copy this file\'s pixel hash.', command_processor.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_COPY_FILE_HASHES, simple_data = ( CAC.FILE_COMMAND_TARGET_FOCUSED_FILE, 'pixel_hash' ) ) )
            
        
        ClientGUIMenus.AppendMenu( share_menu, copy_hash_menu, 'copy hash' )
        
        hash_id_str = HydrusNumbers.ToHumanInt( focused_media.GetHashId() )
        
        ClientGUIMenus.AppendMenuItem( share_menu, 'copy file id ({})'.format( hash_id_str ), 'Copy this file\'s internal file/hash_id.', command_processor.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_COPY_FILE_ID, simple_data = CAC.FILE_COMMAND_TARGET_FOCUSED_FILE ) )
        
    
    if focused_is_local:
        
        if focused_media.IsStaticImage():
            
            ClientGUIMenus.AppendMenuItem( share_menu, 'copy bitmap', 'Copy this file\'s bitmap.', command_processor.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_COPY_FILE_BITMAP, simple_data = CAC.BITMAP_TYPE_FULL ) )
            
            ( width, height ) = focused_media.GetResolution()
            
            if width is not None and height is not None and ( width > 1024 or height > 1024 ):
                
                target_resolution = HydrusImageHandling.GetThumbnailResolution( focused_media.GetResolution(), ( 1024, 1024 ), HydrusImageHandling.THUMBNAIL_SCALE_TO_FIT, 100 )
                
                ClientGUIMenus.AppendMenuItem( share_menu, 'copy source lookup bitmap ({}x{})'.format( target_resolution[0], target_resolution[1] ), 'Copy a smaller bitmap of this file, for quicker lookup on source-finding websites.', command_processor.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_COPY_FILE_BITMAP, simple_data = CAC.BITMAP_TYPE_SOURCE_LOOKUPS ) )
                
            
        
        if focused_media.GetMime() in HC.MIMES_WITH_THUMBNAILS:
            
            ClientGUIMenus.AppendMenuItem( share_menu, 'copy thumbnail bitmap', 'Copy this file\'s thumbnail\'s bitmap.', command_processor.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_COPY_FILE_BITMAP, simple_data = CAC.BITMAP_TYPE_THUMBNAIL ) )
            
        
    
    #
    
    ClientGUIMenus.AppendMenu( menu, share_menu, 'share' )
    
