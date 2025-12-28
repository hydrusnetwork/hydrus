from qtpy import QtWidgets as QW

from hydrus.core import HydrusLists
from hydrus.core import HydrusExceptions

from hydrus.client import ClientApplicationCommand as CAC
from hydrus.client import ClientLocation
from hydrus.client.gui import ClientGUIMenus
from hydrus.client.media import ClientMedia
from hydrus.client.media import ClientMediaFileFilter
from hydrus.client.gui.pages import ClientGUIMediaResultsPanel

def AddRearrangeMenu( win: ClientGUIMediaResultsPanel.MediaResultsPanel, menu: QW.QMenu, selected_media: set[ ClientMedia.Media ], sorted_media: HydrusLists.FastIndexUniqueList, focused_media: ClientMedia.Media | None, selection_is_contiguous: bool, earliest_index: int ):
    
    if len( selected_media ) == 0 or len( selected_media ) == len( sorted_media ):
        
        return
        
    
    rearrange_menu = ClientGUIMenus.GenerateMenu( menu )
    
    if earliest_index > 0:
        
        ClientGUIMenus.AppendMenuItem(
            rearrange_menu,
            'to start',
            'Move the selected thumbnails to the start of the media list.',
            win.ProcessApplicationCommand,
            CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_REARRANGE_THUMBNAILS, ( CAC.REARRANGE_THUMBNAILS_TYPE_COMMAND, CAC.MOVE_HOME ) )
        )
        
        ClientGUIMenus.AppendMenuItem(
            rearrange_menu,
            'back one',
            'Move the selected thumbnails back one position.',
            win.ProcessApplicationCommand,
            CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_REARRANGE_THUMBNAILS, ( CAC.REARRANGE_THUMBNAILS_TYPE_COMMAND, CAC.MOVE_LEFT ) )
        )
        
    
    if focused_media is not None:
        
        try:
            
            focused_index = sorted_media.index( focused_media )
            
            if focused_index != earliest_index or not selection_is_contiguous:
                
                ClientGUIMenus.AppendMenuItem(
                    rearrange_menu,
                    'to here',
                    'Move the selected thumbnails to the focused position (most likely the one you clicked on).',
                    win.ProcessApplicationCommand,
                    CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_REARRANGE_THUMBNAILS, ( CAC.REARRANGE_THUMBNAILS_TYPE_COMMAND, CAC.MOVE_TO_FOCUS ) )
                )
                
            
        except HydrusExceptions.DataMissing:
            
            pass
            
        
    
    if earliest_index + len( selected_media ) < len( sorted_media ):
        
        ClientGUIMenus.AppendMenuItem(
            rearrange_menu,
            'forward one',
            'Move the selected thumbnails forward one position.',
            win.ProcessApplicationCommand,
            CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_REARRANGE_THUMBNAILS, ( CAC.REARRANGE_THUMBNAILS_TYPE_COMMAND, CAC.MOVE_RIGHT ) )
        )
        
        ClientGUIMenus.AppendMenuItem(
            rearrange_menu,
            'to end',
            'Move the selected thumbnails to the end of the media list.',
            win.ProcessApplicationCommand,
            CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_REARRANGE_THUMBNAILS, ( CAC.REARRANGE_THUMBNAILS_TYPE_COMMAND, CAC.MOVE_END ) )
        )
        
    
    ClientGUIMenus.AppendMenu( menu, rearrange_menu, 'rearrange' )
    

def AddRemoveMenu( win: ClientGUIMediaResultsPanel.MediaResultsPanel, menu: QW.QMenu, filter_counts, all_specific_file_domains, has_local_and_remote ):
    
    file_filter_all = ClientMediaFileFilter.FileFilter( ClientMediaFileFilter.FILE_FILTER_ALL )
    
    if file_filter_all.GetCount( win, filter_counts ) > 0:
        
        remove_menu = ClientGUIMenus.GenerateMenu( menu )
        
        #
        
        file_filter_selected = ClientMediaFileFilter.FileFilter( ClientMediaFileFilter.FILE_FILTER_SELECTED )
        
        file_filter_inbox = ClientMediaFileFilter.FileFilter( ClientMediaFileFilter.FILE_FILTER_INBOX )
        
        file_filter_archive = ClientMediaFileFilter.FileFilter( ClientMediaFileFilter.FILE_FILTER_ARCHIVE )
        
        file_filter_not_selected = ClientMediaFileFilter.FileFilter( ClientMediaFileFilter.FILE_FILTER_NOT_SELECTED )
        
        #
        
        selected_count = file_filter_selected.GetCount( win, filter_counts )
        
        if 0 < selected_count < file_filter_all.GetCount( win, filter_counts ):
            
            ClientGUIMenus.AppendMenuItem( remove_menu, file_filter_selected.ToStringWithCount( win, filter_counts ), 'Remove all the selected files from the current view.', win._Remove, file_filter_selected )
            
        
        if file_filter_all.GetCount( win, filter_counts ) > 0:
            
            ClientGUIMenus.AppendSeparator( remove_menu )
            
            ClientGUIMenus.AppendMenuItem( remove_menu, file_filter_all.ToStringWithCount( win, filter_counts ), 'Remove all the files from the current view.', win._Remove, file_filter_all )
            
        
        if file_filter_inbox.GetCount( win, filter_counts ) > 0 and file_filter_archive.GetCount( win, filter_counts ) > 0:
            
            ClientGUIMenus.AppendSeparator( remove_menu )
            
            ClientGUIMenus.AppendMenuItem( remove_menu, file_filter_inbox.ToStringWithCount( win, filter_counts ), 'Remove all the inbox files from the current view.', win._Remove, file_filter_inbox )
            
            ClientGUIMenus.AppendMenuItem( remove_menu, file_filter_archive.ToStringWithCount( win, filter_counts ), 'Remove all the archived files from the current view.', win._Remove, file_filter_archive )
            
        
        if len( all_specific_file_domains ) > 1:
            
            ClientGUIMenus.AppendSeparator( remove_menu )
            
            all_specific_file_domains = ClientLocation.SortFileServiceKeysNicely( all_specific_file_domains )
            
            all_specific_file_domains = ClientLocation.FilterOutRedundantMetaServices( all_specific_file_domains )
            
            for file_service_key in all_specific_file_domains:
                
                file_filter = ClientMediaFileFilter.FileFilter( ClientMediaFileFilter.FILE_FILTER_FILE_SERVICE, file_service_key )
                
                ClientGUIMenus.AppendMenuItem( remove_menu, file_filter.ToStringWithCount( win, filter_counts ), 'Remove all the files that are in this file domain.', win._Remove, file_filter )
                
            
        
        if has_local_and_remote:
            
            file_filter_local = ClientMediaFileFilter.FileFilter( ClientMediaFileFilter.FILE_FILTER_LOCAL )
            file_filter_remote = ClientMediaFileFilter.FileFilter( ClientMediaFileFilter.FILE_FILTER_REMOTE )
            
            ClientGUIMenus.AppendSeparator( remove_menu )
            
            ClientGUIMenus.AppendMenuItem( remove_menu, file_filter_local.ToStringWithCount( win, filter_counts ), 'Remove all the files that are in this client.', win._Remove, file_filter_local )
            ClientGUIMenus.AppendMenuItem( remove_menu, file_filter_remote.ToStringWithCount( win, filter_counts ), 'Remove all the files that are not in this client.', win._Remove, file_filter_remote )
            
        
        not_selected_count = file_filter_not_selected.GetCount( win, filter_counts )
        
        if not_selected_count > 0 and selected_count > 0:
            
            ClientGUIMenus.AppendSeparator( remove_menu )
            
            ClientGUIMenus.AppendMenuItem( remove_menu, file_filter_not_selected.ToStringWithCount( win, filter_counts ), 'Remove all the not selected files from the current view.', win._Remove, file_filter_not_selected )
            
        
        ClientGUIMenus.AppendMenu( menu, remove_menu, 'remove' )
        
    

def AddSelectMenu( win: ClientGUIMediaResultsPanel.MediaResultsPanel, menu, filter_counts, all_specific_file_domains, has_local_and_remote ):
    
    file_filter_all = ClientMediaFileFilter.FileFilter( ClientMediaFileFilter.FILE_FILTER_ALL )
    
    if file_filter_all.GetCount( win, filter_counts ) > 0:
        
        select_menu = ClientGUIMenus.GenerateMenu( menu )
        
        #
        
        file_filter_inbox = ClientMediaFileFilter.FileFilter( ClientMediaFileFilter.FILE_FILTER_INBOX )
        
        file_filter_archive = ClientMediaFileFilter.FileFilter( ClientMediaFileFilter.FILE_FILTER_ARCHIVE )
        
        file_filter_not_selected = ClientMediaFileFilter.FileFilter( ClientMediaFileFilter.FILE_FILTER_NOT_SELECTED )
        
        file_filter_none = ClientMediaFileFilter.FileFilter( ClientMediaFileFilter.FILE_FILTER_NONE )
        
        #
        
        if file_filter_all.GetCount( win, filter_counts ) > 0:
            
            ClientGUIMenus.AppendSeparator( select_menu )
            
            ClientGUIMenus.AppendMenuItem( select_menu, file_filter_all.ToStringWithCount( win, filter_counts ), 'Select all the files in the current view.', win._Select, file_filter_all )
            
        
        if file_filter_inbox.GetCount( win, filter_counts ) > 0 and file_filter_archive.GetCount( win, filter_counts ) > 0:
            
            ClientGUIMenus.AppendSeparator( select_menu )
            
            ClientGUIMenus.AppendMenuItem( select_menu, file_filter_inbox.ToStringWithCount( win, filter_counts ), 'Select all the inbox files in the current view.', win._Select, file_filter_inbox )
            
            ClientGUIMenus.AppendMenuItem( select_menu, file_filter_archive.ToStringWithCount( win, filter_counts ), 'Select all the archived files in the current view.', win._Select, file_filter_archive )
            
        
        if len( all_specific_file_domains ) > 1:
            
            ClientGUIMenus.AppendSeparator( select_menu )
            
            all_specific_file_domains = ClientLocation.SortFileServiceKeysNicely( all_specific_file_domains )
            
            all_specific_file_domains = ClientLocation.FilterOutRedundantMetaServices( all_specific_file_domains )
            
            for file_service_key in all_specific_file_domains:
                
                file_filter = ClientMediaFileFilter.FileFilter( ClientMediaFileFilter.FILE_FILTER_FILE_SERVICE, file_service_key )
                
                ClientGUIMenus.AppendMenuItem( select_menu, file_filter.ToStringWithCount( win, filter_counts ), 'Select all the files in this file domain.', win._Select, file_filter )
                
            
        
        if has_local_and_remote:
            
            file_filter_local = ClientMediaFileFilter.FileFilter( ClientMediaFileFilter.FILE_FILTER_LOCAL )
            file_filter_remote = ClientMediaFileFilter.FileFilter( ClientMediaFileFilter.FILE_FILTER_REMOTE )
            
            ClientGUIMenus.AppendSeparator( select_menu )
            
            ClientGUIMenus.AppendMenuItem( select_menu, file_filter_local.ToStringWithCount( win, filter_counts ), 'Select all the files that are in this client.', win._Select, file_filter_local )
            ClientGUIMenus.AppendMenuItem( select_menu, file_filter_remote.ToStringWithCount( win, filter_counts ), 'Select all the files that are not in this client.', win._Select, file_filter_remote )
            
        
        file_filter_selected = ClientMediaFileFilter.FileFilter( ClientMediaFileFilter.FILE_FILTER_SELECTED )
        selected_count = file_filter_selected.GetCount( win, filter_counts )
        
        not_selected_count = file_filter_not_selected.GetCount( win, filter_counts )
        
        if selected_count > 0:
            
            if not_selected_count > 0:
                
                ClientGUIMenus.AppendSeparator( select_menu )
                
                ClientGUIMenus.AppendMenuItem( select_menu, file_filter_not_selected.ToStringWithCount( win, filter_counts ), 'Swap what is and is not selected.', win._Select, file_filter_not_selected )
                
            
            ClientGUIMenus.AppendSeparator( select_menu )
            
            ClientGUIMenus.AppendMenuItem( select_menu, file_filter_none.ToStringWithCount( win, filter_counts ), 'Deselect everything selected.', win._Select, file_filter_none )
            
        
        ClientGUIMenus.AppendMenu( menu, select_menu, 'select' )
        
    
