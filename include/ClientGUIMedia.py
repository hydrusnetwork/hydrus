import HydrusConstants as HC
import ClientConstants as CC
import ClientCaches
import ClientData
import ClientFiles
import ClientGUICanvas
import ClientGUICommon
import ClientGUIDialogs
import ClientGUIDialogsManage
import ClientGUIMenus
import ClientGUIScrolledPanelsManagement
import ClientGUITopLevelWindows
import ClientMedia
import collections
import HydrusExceptions
import HydrusNetwork
import HydrusPaths
import HydrusSerialisable
import HydrusTags
import HydrusThreading
import itertools
import json
import os
import random
import threading
import time
import traceback
import wx
import yaml
import HydrusData
import HydrusGlobals

# Option Enums

ID_TIMER_ANIMATION = wx.NewId()

def AddServiceKeyLabelsToMenu( menu, service_keys, phrase ):
    
    services_manager = HydrusGlobals.client_controller.GetServicesManager()
    
    if len( service_keys ) == 1:
        
        ( service_key, ) = service_keys
        
        name = services_manager.GetName( service_key )
        
        label = phrase + ' ' + name
        
        ClientGUIMenus.AppendMenuLabel( menu, label )
        
    else:
        
        submenu = wx.Menu()
        
        for service_key in service_keys:
            
            name = services_manager.GetName( service_key )
            
            ClientGUIMenus.AppendMenuLabel( submenu, name )
            
        
        ClientGUIMenus.AppendMenu( menu, submenu, phrase + u'\u2026' )
        
    
def AddServiceKeysToMenu( event_handler, menu, service_keys, phrase, description, callable ):
    
    services_manager = HydrusGlobals.client_controller.GetServicesManager()
    
    if len( service_keys ) == 1:
        
        ( service_key, ) = service_keys
        
        name = services_manager.GetName( service_key )
        
        label = phrase + ' ' + name
        
        ClientGUIMenus.AppendMenuItem( event_handler, menu, label, description, callable, service_key )
        
    else:
        
        submenu = wx.Menu()
        
        for service_key in service_keys: 
            
            name = services_manager.GetName( service_key )
            
            ClientGUIMenus.AppendMenuItem( event_handler, submenu, name, description, callable, service_key )
            
        
        ClientGUIMenus.AppendMenu( menu, submenu, phrase + u'\u2026' )
        
    
class MediaPanel( ClientMedia.ListeningMediaList, wx.ScrolledWindow ):
    
    def __init__( self, parent, page_key, file_service_key, media_results ):
        
        wx.ScrolledWindow.__init__( self, parent, size = ( 0, 0 ), style = wx.BORDER_SUNKEN )
        ClientMedia.ListeningMediaList.__init__( self, file_service_key, media_results )
        
        self.SetDoubleBuffered( True ) # This seems to stop some bad scroll draw logic, where top/bottom row is auto-drawn undrawn and then paint event called
        
        self.SetBackgroundColour( wx.Colour( *HC.options[ 'gui_colours' ][ 'thumbgrid_background' ] ) )
        
        self.SetScrollRate( 0, 50 )
        
        self._page_key = page_key
        
        self._focussed_media = None
        self._next_best_media_after_focussed_media_removed = None
        self._shift_focussed_media = None
        
        self._selected_media = set()
        
        HydrusGlobals.client_controller.sub( self, 'AddMediaResults', 'add_media_results' )
        HydrusGlobals.client_controller.sub( self, 'SetFocussedMedia', 'set_focus' )
        HydrusGlobals.client_controller.sub( self, 'PageHidden', 'page_hidden' )
        HydrusGlobals.client_controller.sub( self, 'PageShown', 'page_shown' )
        HydrusGlobals.client_controller.sub( self, 'Collect', 'collect_media' )
        HydrusGlobals.client_controller.sub( self, 'Sort', 'sort_media' )
        HydrusGlobals.client_controller.sub( self, 'FileDumped', 'file_dumped' )
        HydrusGlobals.client_controller.sub( self, 'RemoveMedia', 'remove_media' )
        
        self._PublishSelectionChange()
        
    
    def _Archive( self ):
        
        hashes = self._GetSelectedHashes( discriminant = CC.DISCRIMINANT_INBOX )
        
        if len( hashes ) > 0:
            
            if HC.options[ 'confirm_archive' ]:
                
                if len( hashes ) > 1:
                    
                    message = 'Archive ' + HydrusData.ConvertIntToPrettyString( len( hashes ) ) + ' files?'
                    
                    with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
                        
                        if dlg.ShowModal() != wx.ID_YES: return
                        
                    
                
            
            HydrusGlobals.client_controller.Write( 'content_updates', { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ARCHIVE, hashes ) ] } )
            
        
    
    def _CopyBMPToClipboard( self ):
        
        media = self._focussed_media.GetDisplayMedia()
        
        HydrusGlobals.client_controller.pub( 'clipboard', 'bmp', media )
        
    
    def _CopyFilesToClipboard( self ):
        
        client_files_manager = HydrusGlobals.client_controller.GetClientFilesManager()
        
        hashes = self._GetSelectedHashes( discriminant = CC.DISCRIMINANT_LOCAL, ordered = True )
        
        paths = [ client_files_manager.GetFilePath( hash ) for hash in hashes ]
        
        HydrusGlobals.client_controller.pub( 'clipboard', 'paths', paths )
        
    
    def _CopyHashToClipboard( self, hash_type ):
        
        display_media = self._focussed_media.GetDisplayMedia()
        
        sha256_hash = display_media.GetHash()
        
        if hash_type == 'sha256':
            
            hex_hash = sha256_hash.encode( 'hex' )
            
        else:
            
            if display_media.GetLocationsManager().IsLocal():
                
                ( other_hash, ) = HydrusGlobals.client_controller.Read( 'file_hashes', ( sha256_hash, ), 'sha256', hash_type )
                
                hex_hash = other_hash.encode( 'hex' )
                
            else:
                
                wx.MessageBox( 'Unfortunately, you do not have that file in your database, so its non-sha256 hashes are unknown.' )
                
                return
                
            
        
        HydrusGlobals.client_controller.pub( 'clipboard', 'text', hex_hash )
        
    
    def _CopyHashesToClipboard( self, hash_type ):
        
        if hash_type == 'sha256':
            
            hex_hashes = os.linesep.join( [ hash.encode( 'hex' ) for hash in self._GetSelectedHashes( ordered = True ) ] )
            
        else:
            
            sha256_hashes = self._GetSelectedHashes( discriminant = CC.DISCRIMINANT_LOCAL, ordered = True )
            
            if len( sha256_hashes ) > 0:
                
                other_hashes = HydrusGlobals.client_controller.Read( 'file_hashes', sha256_hashes, 'sha256', hash_type )
                
                hex_hashes = os.linesep.join( [ other_hash.encode( 'hex' ) for other_hash in other_hashes ] )
                
            else:
                
                wx.MessageBox( 'Unfortunately, none of those files are in your database, so their non-sha256 hashes are unknown.' )
                
                return
                
            
        
        HydrusGlobals.client_controller.pub( 'clipboard', 'text', hex_hashes )
        
    
    def _CopyKnownURLsToClipboard( self ):
        
        hash = self._focussed_media.GetDisplayMedia().GetHash()
        
        known_urls = HydrusGlobals.client_controller.Read( 'known_urls', hash )
        
        if len( known_urls ) == 0:
            
            HydrusData.ShowText( 'No known urls!' )
            
        else:
            
            text = os.linesep.join( known_urls )
            
            HydrusGlobals.client_controller.pub( 'clipboard', 'text', text )
            
        
    
    def _CopyPathToClipboard( self ):
        
        display_media = self._focussed_media.GetDisplayMedia()
        
        client_files_manager = HydrusGlobals.client_controller.GetClientFilesManager()
        
        path = client_files_manager.GetFilePath( display_media.GetHash(), display_media.GetMime() )
        
        HydrusGlobals.client_controller.pub( 'clipboard', 'text', path )
        
    
    def _CopyPathsToClipboard( self ):
        
        media_results = self.GenerateMediaResults( discriminant = CC.DISCRIMINANT_LOCAL, selected_media = set( self._selected_media ) )
        
        client_files_manager = HydrusGlobals.client_controller.GetClientFilesManager()
        
        paths = []
        
        for media_result in media_results:
            
            paths.append( client_files_manager.GetFilePath( media_result.GetHash(), media_result.GetMime() ) )
            
        
        text = os.linesep.join( paths )
        
        HydrusGlobals.client_controller.pub( 'clipboard', 'text', text )
        
    
    def _CopyServiceFilenameToClipboard( self, service_key ):
        
        display_media = self._focussed_media.GetDisplayMedia()
        
        hash = display_media.GetHash()
        
        ( filename, ) = HydrusGlobals.client_controller.Read( 'service_filenames', service_key, { hash } )
        
        service = HydrusGlobals.client_controller.GetServicesManager().GetService( service_key )
        
        if service.GetServiceType() == HC.IPFS:
            
            multihash_prefix = service.GetMultihashPrefix()
            
            filename = multihash_prefix + filename
            
        
        HydrusGlobals.client_controller.pub( 'clipboard', 'text', filename )
        
    
    def _CopyServiceFilenamesToClipboard( self, service_key ):
        
        prefix = ''
        
        service = HydrusGlobals.client_controller.GetServicesManager().GetService( service_key )
        
        if service.GetServiceType() == HC.IPFS:
            
            prefix = service.GetMultihashPrefix()
            
        
        hashes = self._GetSelectedHashes( has_location = service_key )
        
        if len( hashes ) > 0:
            
            filenames = [ prefix + filename for filename in HydrusGlobals.client_controller.Read( 'service_filenames', service_key, hashes ) ]
            
            if len( filenames ) > 0:
                
                copy_string = os.linesep.join( filenames )
                
                HydrusGlobals.client_controller.pub( 'clipboard', 'text', copy_string )
                
            else:
                
                HydrusData.ShowText( 'Could not find any service filenames for that selection!' )
                
            
        else:
            
            HydrusData.ShowText( 'Could not find any files with the requested service!' )
            
        
    
    def _CustomFilter( self, shortcuts_name = None ):
        
        shortcuts = None
        
        if shortcuts_name is not None:
            
            shortcuts = HydrusGlobals.client_controller.Read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_SHORTCUTS, shortcuts_name )
            
        else:
            
            with ClientGUIDialogs.DialogShortcuts( self ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    shortcuts = dlg.GetShortcuts()
                    
                
            
        
        if shortcuts is not None:
    
            media_results = self.GenerateMediaResults( discriminant = CC.DISCRIMINANT_LOCAL, selected_media = set( self._selected_media ), for_media_viewer = True )
            
            if len( media_results ) > 0:
                
                canvas_frame = ClientGUICanvas.CanvasFrame( self.GetTopLevelParent() )
                
                canvas_window = ClientGUICanvas.CanvasMediaListCustomFilter( canvas_frame, self._page_key, media_results, shortcuts )
                
                canvas_frame.SetCanvas( canvas_window )
                
            
        
    
    def _Delete( self, file_service_key = None ):
        
        if file_service_key is None:
            
            has_local = True in ( CC.LOCAL_FILE_SERVICE_KEY in media.GetLocationsManager().GetCurrent() for media in self._selected_media )
            
            has_trash = True in ( CC.TRASH_SERVICE_KEY in media.GetLocationsManager().GetCurrent() for media in self._selected_media )
            
            if has_local:
                
                file_service_key = CC.LOCAL_FILE_SERVICE_KEY
                
            elif has_trash:
                
                file_service_key = CC.TRASH_SERVICE_KEY
                
            else:
                
                return
                
            
        
        hashes = self._GetSelectedHashes( has_location = file_service_key )
        
        num_to_delete = len( hashes )
        
        if num_to_delete > 0:
            
            do_it = False
            
            if file_service_key == CC.LOCAL_FILE_SERVICE_KEY:
                
                if not HC.options[ 'confirm_trash' ]:
                    
                    do_it = True
                    
                
                if num_to_delete == 1: text = 'Send this file to the trash?'
                else: text = 'Send these ' + HydrusData.ConvertIntToPrettyString( num_to_delete ) + ' files to the trash?'
                
            elif file_service_key == CC.TRASH_SERVICE_KEY:
                
                if num_to_delete == 1: text = 'Permanently delete this file?'
                else: text = 'Permanently delete these ' + HydrusData.ConvertIntToPrettyString( num_to_delete ) + ' files?'
                
            else:
                
                if num_to_delete == 1: text = 'Admin-delete this file?'
                else: text = 'Admin-delete these ' + HydrusData.ConvertIntToPrettyString( num_to_delete ) + ' files?'
                
            
            if not do_it:
                
                with ClientGUIDialogs.DialogYesNo( self, text ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_YES:
                        
                        do_it = True
                        
                    
                
            
            if do_it:
                
                def process_in_thread( service_key, content_updates ):
                    
                    for content_update in content_updates:
                        
                        HydrusGlobals.client_controller.WriteSynchronous( 'content_updates', { service_key : [ content_update ] } )
                        
                    
                
                local_file_services = ( CC.LOCAL_FILE_SERVICE_KEY, CC.TRASH_SERVICE_KEY )
                
                if file_service_key in local_file_services:
                    
                    # we want currently animating files (i.e. currently open files) to be unloaded before the delete call goes through
                    
                    if file_service_key == CC.TRASH_SERVICE_KEY:
                        
                        self._SetFocussedMedia( None )
                        
                    
                    # split them into bits so we don't hang the gui with a huge delete transaction
                    
                    chunks_of_hashes = HydrusData.SplitListIntoChunks( hashes, 64 )
                    
                    content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, chunk_of_hashes ) for chunk_of_hashes in chunks_of_hashes ]
                    
                else:
                    
                    content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_PETITION, ( hashes, 'admin' ) ) ]
                    
                
                HydrusGlobals.client_controller.CallToThread( process_in_thread, file_service_key, content_updates )
                
            
        
    
    def _DeselectSelect( self, media_to_deselect, media_to_select ):
        
        if len( media_to_deselect ) > 0:
            
            for m in media_to_deselect: m.Deselect()
            
            self._RedrawMedia( media_to_deselect )
            
            self._selected_media.difference_update( media_to_deselect )
            
        
        if len( media_to_select ) > 0:
            
            for m in media_to_select: m.Select()
            
            self._RedrawMedia( media_to_select )
            
            self._selected_media.update( media_to_select )
            
        
        self._PublishSelectionChange()
        
    
    def _DownloadSelected( self ):
        
        hashes = self._GetSelectedHashes( discriminant = CC.DISCRIMINANT_NOT_LOCAL )
        
        self._DownloadHashes( hashes )
        
    
    def _DownloadHashes( self, hashes ):
        
        HydrusGlobals.client_controller.Write( 'content_updates', { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_PEND, hashes ) ] } )
        
    
    def _FullScreen( self, first_media = None ):
        
        if self._focussed_media is not None:
            
            display_media = self._focussed_media.GetDisplayMedia()
            
            new_options = HydrusGlobals.client_controller.GetNewOptions()
            
            media_show_action = new_options.GetMediaShowAction( display_media.GetMime() )
            
            if media_show_action == CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW_ON_ACTIVATION_OPEN_EXTERNALLY:
                
                hash = display_media.GetHash()
                mime = display_media.GetMime()
                
                client_files_manager = HydrusGlobals.client_controller.GetClientFilesManager()
                
                path = client_files_manager.GetFilePath( hash, mime )
                
                HydrusPaths.LaunchFile( path )
                
                return
                
            elif media_show_action == CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW:
                
                return
                
            
        
        media_results = self.GenerateMediaResults( discriminant = CC.DISCRIMINANT_LOCAL, for_media_viewer = True )
        
        if len( media_results ) > 0:
            
            if first_media is None and self._focussed_media is not None: first_media = self._focussed_media
            
            if first_media is not None and first_media.GetLocationsManager().IsLocal(): first_hash = first_media.GetDisplayMedia().GetHash()
            else: first_hash = None
            
            canvas_frame = ClientGUICanvas.CanvasFrame( self.GetTopLevelParent() )
            
            canvas_window = ClientGUICanvas.CanvasMediaListBrowser( canvas_frame, self._page_key, media_results, first_hash )
            
            canvas_frame.SetCanvas( canvas_window )
            
        
    
    def _Filter( self ):
        
        media_results = self.GenerateMediaResults( discriminant = CC.DISCRIMINANT_LOCAL_BUT_NOT_IN_TRASH, selected_media = set( self._selected_media ), for_media_viewer = True )
        
        if len( media_results ) > 0:
            
            canvas_frame = ClientGUICanvas.CanvasFrame( self.GetTopLevelParent() )
            
            canvas_window = ClientGUICanvas.CanvasMediaListFilterInbox( canvas_frame, self._page_key, media_results )
            
            canvas_frame.SetCanvas( canvas_window )
            
        
    
    def _GetNumSelected( self ): return sum( [ media.GetNumFiles() for media in self._selected_media ] )
    
    def _GetPrettyStatus( self ):
        
        num_files = len( self._hashes )
        
        num_selected = self._GetNumSelected()
        
        ( sorted_mime_classes, selected_mime_classes ) = self._GetSortedSelectedMimeClasses()
        
        if sorted_mime_classes == set( [ 'image' ] ):
            
            num_files_descriptor = 'image'
            
        elif sorted_mime_classes == set( [ 'video' ] ):
            
            num_files_descriptor = 'video'
            
        else:
            
            num_files_descriptor = 'file'
            
        
        if selected_mime_classes == set( [ 'image' ] ):
            
            selected_files_descriptor = 'image'
            
        elif selected_mime_classes == set( [ 'video' ] ):
            
            selected_files_descriptor = 'video'
            
        else:
            
            selected_files_descriptor = 'file'
            
        
        
        if num_files == 1:
            
            num_files_string = '1 ' + num_files_descriptor
            
        else:
            
            num_files_string = HydrusData.ConvertIntToPrettyString( num_files ) + ' ' + num_files_descriptor + 's'
            
        
        if selected_files_descriptor == num_files_descriptor:
            
            selected_files_string = HydrusData.ConvertIntToPrettyString( num_selected )
            
        else:
            
            if num_selected == 1:
                
                selected_files_string = '1 ' + selected_files_descriptor
                
            else:
                
                selected_files_string = HydrusData.ConvertIntToPrettyString( num_selected ) + ' ' + selected_files_descriptor + 's'
                
            
        
        s = num_files_string # 23 files
        
        if num_selected > 0:
            
            s += ' - '
            
            if num_selected == 1: # 23 files - 1 video selected, file_info
                
                ( selected_media, ) = self._selected_media
                
                s += selected_files_string + ' selected, ' + ', '.join( selected_media.GetPrettyInfoLines() )
                
            else: # 23 files - 5 selected, selection_info
                
                num_inbox = sum( ( media.GetNumInbox() for media in self._selected_media ) )
                
                if num_inbox == num_selected: inbox_phrase = 'all in inbox, '
                elif num_inbox == 0: inbox_phrase = 'all archived, '
                else: inbox_phrase = HydrusData.ConvertIntToPrettyString( num_inbox ) + ' in inbox and ' + HydrusData.ConvertIntToPrettyString( num_selected - num_inbox ) + ' archived, '
                
                pretty_total_size = self._GetPrettyTotalSelectedSize()
                
                s += selected_files_string + ' selected, ' + inbox_phrase + 'totalling ' + pretty_total_size
                
            
        
        return s
        
    
    def _GetPrettyTotalSelectedSize( self ):
        
        total_size = sum( [ media.GetSize() for media in self._selected_media ] )
        
        unknown_size = False in ( media.IsSizeDefinite() for media in self._selected_media )
        
        if total_size == 0:
            
            if unknown_size: return 'unknown size'
            else: return HydrusData.ConvertIntToBytes( 0 )
            
        else:
            
            if unknown_size: return HydrusData.ConvertIntToBytes( total_size ) + ' + some unknown size'
            else: return HydrusData.ConvertIntToBytes( total_size )
            
        
    
    def _GetSelectedHashes( self, has_location = None, discriminant = None, not_uploaded_to = None, ordered = False ):
        
        if ordered:
            
            result = []
            
            for media in self._sorted_media:
                
                if media in self._selected_media:
                    
                    result.extend( media.GetHashes( has_location, discriminant, not_uploaded_to, ordered ) )
                    
                
            
        else:
            
            result = set()
            
            for media in self._selected_media:
                
                result.update( media.GetHashes( has_location, discriminant, not_uploaded_to, ordered ) )
                
            
        
        return result
        
    
    def _GetSimilarTo( self, max_hamming ):
        
        if self._focussed_media is not None:
            
            hash = self._focussed_media.GetDisplayMedia().GetHash()
            
            HydrusGlobals.client_controller.pub( 'new_similar_to', CC.COMBINED_LOCAL_FILE_SERVICE_KEY, hash, max_hamming )
            
        
    
    def _GetSortedSelectedMimeClasses( self ):
        
        sorted_mimes = set()
        
        for media in self._sorted_media:
            
            mime = media.GetMime()
            
            if mime in HC.IMAGES:
                
                sorted_mimes.add( 'image' )
                
            elif mime in HC.VIDEO:
                
                sorted_mimes.add( 'video' )
                
            elif mime in HC.AUDIO:
                
                sorted_mimes.add( 'audio' )
                
            else:
                
                sorted_mimes.add( 'misc' )
                
            
        
        selected_mimes = set()
        
        for media in self._selected_media:
            
            mime = media.GetMime()
            
            if mime in HC.IMAGES:
                
                selected_mimes.add( 'image' )
                
            elif mime in HC.VIDEO:
                
                selected_mimes.add( 'video' )
                
            elif mime in HC.AUDIO:
                
                selected_mimes.add( 'audio' )
                
            else:
                
                selected_mimes.add( 'misc' )
                
            
        
        return ( sorted_mimes, selected_mimes )
        
    
    def _HitMedia( self, media, ctrl, shift ):
        
        if media is None:
            
            if not ctrl and not shift:
                
                self._Select( 'none' )
                self._SetFocussedMedia( None )
                self._shift_focussed_media = None
                
            
        else:
            
            if ctrl:
                
                if media.IsSelected():
                    
                    self._DeselectSelect( ( media, ), () )
                    
                    if self._focussed_media == media:
                        
                        self._SetFocussedMedia( None )
                        
                    
                    self._shift_focussed_media = None
                    
                else:
                    
                    self._DeselectSelect( (), ( media, ) )
                    
                    if self._focussed_media is None: self._SetFocussedMedia( media )
                    
                    self._shift_focussed_media = media
                    
                
            elif shift and self._shift_focussed_media is not None:
                
                start_index = self._sorted_media.index( self._shift_focussed_media )
                
                end_index = self._sorted_media.index( media )
                
                if start_index < end_index: media_to_select = set( self._sorted_media[ start_index : end_index + 1 ] )
                else: media_to_select = set( self._sorted_media[ end_index : start_index + 1 ] )
                
                self._DeselectSelect( (), media_to_select )
                
                self._SetFocussedMedia( media )
                
                self._shift_focussed_media = media
                
            else:
                
                if not media.IsSelected():
                    
                    self._DeselectSelect( self._selected_media, ( media, ) )
                    
                else:
                    
                    self._PublishSelectionChange()
                    
                
                self._SetFocussedMedia( media )
                self._shift_focussed_media = media
                
            
        
    
    def _Inbox( self ):
        
        hashes = self._GetSelectedHashes( discriminant = CC.DISCRIMINANT_ARCHIVE )
        
        if len( hashes ) > 0:
            
            if HC.options[ 'confirm_archive' ]:
                
                if len( hashes ) > 1:
                    
                    message = 'Send ' + HydrusData.ConvertIntToPrettyString( len( hashes ) ) + ' files to inbox?'
                    
                    with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
                        
                        if dlg.ShowModal() != wx.ID_YES: return
                        
                    
                
            
            HydrusGlobals.client_controller.Write( 'content_updates', { CC.COMBINED_LOCAL_FILE_SERVICE_KEY: [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_INBOX, hashes ) ] } )
            
        
    
    def _ManageRatings( self ):
        
        if len( self._selected_media ) > 0:
            
            if len( HydrusGlobals.client_controller.GetServicesManager().GetServices( HC.RATINGS_SERVICES ) ) > 0:
                
                flat_media = []
                
                for media in self._selected_media:
                    
                    if media.IsCollection(): flat_media.extend( media.GetFlatMedia() )
                    else: flat_media.append( media )
                    
                
                with ClientGUIDialogsManage.DialogManageRatings( None, flat_media ) as dlg: dlg.ShowModal()
                
                self.SetFocus()
                
            
        
    
    def _ManageTags( self ):
        
        if len( self._selected_media ) > 0:
            
            num_files = self._GetNumSelected()
            
            title = 'manage tags for ' + HydrusData.ConvertIntToPrettyString( num_files ) + ' files'
            frame_key = 'manage_tags_dialog'
            
            with ClientGUITopLevelWindows.DialogManage( self, title, frame_key ) as dlg:
                
                panel = ClientGUIScrolledPanelsManagement.ManageTagsPanel( dlg, self._file_service_key, self._selected_media )
                
                dlg.SetPanel( panel )
                
                dlg.ShowModal()
                
            
            self.SetFocus()
            
        
    
    def _ModifyUploaders( self, file_service_key ):
        
        wx.MessageBox( 'this does not work yet!' )
        
        return
        
        hashes = self._GetSelectedHashes()
        
        if hashes is not None and len( hashes ) > 0:   
            
            contents = [ HydrusNetwork.Content( HC.CONTENT_TYPE_FILES, [ hash ] ) for hash in hashes ]
            
            subject_accounts = 'blah' # fetch subjects from server with the contents
            
            with ClientGUIDialogs.DialogModifyAccounts( self, file_service_key, subject_accounts ) as dlg: dlg.ShowModal()
            
            self.SetFocus()
            
        
    
    def _OpenExternally( self ):
        
        if self._focussed_media is not None:
            
            if self._focussed_media.GetLocationsManager().IsLocal():
                
                hash = self._focussed_media.GetHash()
                mime = self._focussed_media.GetMime()
                
                client_files_manager = HydrusGlobals.client_controller.GetClientFilesManager()
                
                path = client_files_manager.GetFilePath( hash, mime )
                
                self._SetFocussedMedia( None )
                
                HydrusPaths.LaunchFile( path )
                
            
        
    
    def _PetitionFiles( self, remote_service_key ):
        
        hashes = self._GetSelectedHashes()
        
        if hashes is not None and len( hashes ) > 0:
            
            remote_service = HydrusGlobals.client_controller.GetServicesManager().GetService( remote_service_key )
            
            service_type = remote_service.GetServiceType()
            
            if service_type == HC.FILE_REPOSITORY:
                
                if len( hashes ) == 1:
                    
                    message = 'Enter a reason for this file to be removed from ' + remote_service.GetName() + '.'
                    
                else:
                    
                    message = 'Enter a reason for these ' + HydrusData.ConvertIntToPrettyString( len( hashes ) ) + ' files to be removed from ' + remote_service.GetName() + '.'
                    
                
                with ClientGUIDialogs.DialogTextEntry( self, message ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_PETITION, ( hashes, dlg.GetValue() ) )
                        
                        service_keys_to_content_updates = { remote_service_key : ( content_update, ) }
                        
                        HydrusGlobals.client_controller.Write( 'content_updates', service_keys_to_content_updates )
                        
                    
                
                self.SetFocus()
                
            elif service_type == HC.IPFS:
                
                content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_PETITION, ( hashes, 'ipfs' ) )
                
                service_keys_to_content_updates = { remote_service_key : ( content_update, ) }
                
                HydrusGlobals.client_controller.Write( 'content_updates', service_keys_to_content_updates )
                
            
        
    
    def _PublishSelectionChange( self, force_reload = False ):
        
        if len( self._selected_media ) == 0:
            
            tags_media = self._sorted_media
            
        else:
            
            tags_media = self._selected_media
            
        
        HydrusGlobals.client_controller.pub( 'new_tags_selection', self._page_key, tags_media, force_reload = force_reload )
        HydrusGlobals.client_controller.pub( 'new_page_status', self._page_key, self._GetPrettyStatus() )
        
    
    def _PublishSelectionIncrement( self, medias ):
        
        HydrusGlobals.client_controller.pub( 'increment_tags_selection', self._page_key, medias )
        HydrusGlobals.client_controller.pub( 'new_page_status', self._page_key, self._GetPrettyStatus() )
        
    
    def _RecalculateVirtualSize( self ): pass
    
    def _RedrawMedia( self, media ): pass
    
    def _RescindDownloadSelected( self ):
        
        hashes = self._GetSelectedHashes( discriminant = CC.DISCRIMINANT_NOT_LOCAL )
        
        HydrusGlobals.client_controller.Write( 'content_updates', { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_RESCIND_PEND, hashes ) ] } )
        
    
    def _RescindPetitionFiles( self, file_service_key ):
        
        hashes = self._GetSelectedHashes()
        
        if hashes is not None and len( hashes ) > 0:   
            
            HydrusGlobals.client_controller.Write( 'content_updates', { file_service_key : [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_RESCIND_PETITION, hashes ) ] } )
            
        
    
    def _RescindUploadFiles( self, file_service_key ):
        
        hashes = self._GetSelectedHashes()
        
        if hashes is not None and len( hashes ) > 0:   
            
            HydrusGlobals.client_controller.Write( 'content_updates', { file_service_key : [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_RESCIND_PEND, hashes ) ] } )
            
        
    
    def _Select( self, select_type, extra_info = None ):
        
        if select_type == 'all':
            
            self._DeselectSelect( [], self._sorted_media )
            
        else:
            
            if select_type == 'invert':
                
                ( media_to_deselect, media_to_select ) = ( self._selected_media, { m for m in self._sorted_media if m not in self._selected_media } )
                
            elif select_type == 'none':
                
                ( media_to_deselect, media_to_select ) = ( self._selected_media, [] )
                
            elif select_type in ( 'inbox', 'archive' ):
                
                inbox_media = { m for m in self._sorted_media if m.HasInbox() }
                archive_media = { m for m in self._sorted_media if m not in inbox_media }
                
                if select_type == 'inbox':
                    
                    media_to_deselect = [ m for m in archive_media if m in self._selected_media ]
                    media_to_select = [ m for m in inbox_media if m not in self._selected_media ]
                    
                elif select_type == 'archive':
                    
                    media_to_deselect = [ m for m in inbox_media if m in self._selected_media ]
                    media_to_select = [ m for m in archive_media if m not in self._selected_media ]
                    
                
            elif select_type == 'file_service':
                
                file_service_key = extra_info
                
                media_to_deselect = [ m for m in self._selected_media if file_service_key not in m.GetLocationsManager().GetCurrent() ]
                media_to_select = [ m for m in self._sorted_media if m not in self._selected_media and file_service_key in m.GetLocationsManager().GetCurrent() ]
                
            
            if self._focussed_media in media_to_deselect: self._SetFocussedMedia( None )
            
            self._DeselectSelect( media_to_deselect, media_to_select )
            
            self._shift_focussed_media = None
            
        
    
    def _SetFocussedMedia( self, media ):
        
        if media is None and self._focussed_media is not None:
            
            next_best_media = self._focussed_media
            
            i = self._sorted_media.index( next_best_media )
            
            while next_best_media in self._selected_media:
                
                if i == 0:
                    
                    next_best_media = None
                    
                    break
                    
                
                i -= 1
                
                next_best_media = self._sorted_media[ i ]
                
            
            self._next_best_media_after_focussed_media_removed = next_best_media
            
        else:
            
            self._next_best_media_after_focussed_media_removed = None
            
        
        self._focussed_media = media
        
        HydrusGlobals.client_controller.pub( 'focus_changed', self._page_key, media )
        
    
    def _ShareOnLocalBooru( self ):
        
        if len( self._selected_media ) > 0:
            
            share_key = HydrusData.GenerateKey()
            
            name = ''
            text = ''
            timeout = HydrusData.GetNow() + 60 * 60 * 24
            hashes = self._GetSelectedHashes()
            
            with ClientGUIDialogs.DialogInputLocalBooruShare( self, share_key, name, text, timeout, hashes, new_share = True ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    ( share_key, name, text, timeout, hashes ) = dlg.GetInfo()
                    
                    info = {}
                    
                    info[ 'name' ] = name
                    info[ 'text' ] = text
                    info[ 'timeout' ] = timeout
                    info[ 'hashes' ] = hashes
                    
                    HydrusGlobals.client_controller.Write( 'local_booru_share', share_key, info )
                    
                
            
            self.SetFocus()
            
        
    
    def _ShowSelectionInNewQueryPage( self ):
        
        hashes = self._GetSelectedHashes()
        
        if hashes is not None and len( hashes ) > 0:
            
            media_results = HydrusGlobals.client_controller.Read( 'media_results', hashes )
            
            hashes_to_media_results = { media_result.GetHash() : media_result for media_result in media_results }
            
            sorted_flat_media = self.GetFlatMedia()
            
            sorted_media_results = [ hashes_to_media_results[ media.GetHash() ] for media in sorted_flat_media if media.GetHash() in hashes_to_media_results ]
            
            HydrusGlobals.client_controller.pub( 'new_page_query', self._file_service_key, initial_media_results = sorted_media_results )
            
        
    
    def _Undelete( self ):
        
        hashes = self._GetSelectedHashes( has_location = CC.TRASH_SERVICE_KEY )
        
        num_to_undelete = len( hashes )
        
        if num_to_undelete > 0:
            
            do_it = False
            
            if not HC.options[ 'confirm_trash' ]:
                
                do_it = True
                
            else:
                
                if num_to_undelete == 1: text = 'Are you sure you want to undelete this file?'
                else: text = 'Are you sure you want to undelete these ' + HydrusData.ConvertIntToPrettyString( num_to_undelete ) + ' files?'
                
                with ClientGUIDialogs.DialogYesNo( self, text ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_YES:
                        
                        do_it = True
                        
                    
                
            
            if do_it:
                
                HydrusGlobals.client_controller.Write( 'content_updates', { CC.TRASH_SERVICE_KEY : [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_UNDELETE, hashes ) ] } )
                
            
        
    
    def _UploadDirectory( self, file_service_key ):
        
        hashes = self._GetSelectedHashes()
        
        if hashes is not None and len( hashes ) > 0:
            
            ipfs_service = HydrusGlobals.client_controller.GetServicesManager().GetService( file_service_key )
            
        
        with ClientGUIDialogs.DialogTextEntry( self, 'Enter a note to describe this directory.' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                note = dlg.GetValue()
                
                HydrusGlobals.client_controller.CallToThread( ipfs_service.PinDirectory, hashes, note )
                
            
        
    
    def _UploadFiles( self, file_service_key ):
        
        hashes = self._GetSelectedHashes( not_uploaded_to = file_service_key )
        
        if hashes is not None and len( hashes ) > 0:   
            
            HydrusGlobals.client_controller.Write( 'content_updates', { file_service_key : [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_PEND, hashes ) ] } )
            
        
    
    def AddMediaResults( self, page_key, media_results, append = True ):
        
        if page_key == self._page_key:
            
            return ClientMedia.ListeningMediaList.AddMediaResults( self, media_results, append = append )
            
        
    
    def Archive( self, hashes ):
        
        affected_media = self._GetMedia( hashes )
        
        if len( affected_media ) > 0: self._RedrawMedia( affected_media )
        
        self._PublishSelectionChange()
        
        if self._focussed_media is not None: self._HitMedia( self._focussed_media, False, False )
        
    
    def Collect( self, page_key, collect_by = -1 ):
        
        if page_key == self._page_key:
            
            self._Select( 'none' )
            
            ClientMedia.ListeningMediaList.Collect( self, collect_by )
            
            self._RecalculateVirtualSize()
            
            # no refresh needed since the sort call that always comes after will do it
            
        
    
    def FileDumped( self, page_key, hash, status ):
        
        if page_key == self._page_key:
            
            media = self._GetMedia( { hash } )
            
            for m in media: m.Dumped( status )
            
            self._RedrawMedia( media )
            
        
    
    def PageHidden( self, page_key ):
        
        if page_key == self._page_key: HydrusGlobals.client_controller.pub( 'focus_changed', self._page_key, None )
        
    
    def PageShown( self, page_key ):
        
        if page_key == self._page_key:
            
            HydrusGlobals.client_controller.pub( 'focus_changed', self._page_key, self._focussed_media )
            
            self._PublishSelectionChange()
            
        
    
    def ProcessContentUpdates( self, service_keys_to_content_updates ):
        
        ClientMedia.ListeningMediaList.ProcessContentUpdates( self, service_keys_to_content_updates )
        
        force_reload = False
        
        for ( service_key, content_updates ) in service_keys_to_content_updates.items():
            
            for content_update in content_updates:
                
                ( data_type, action, row ) = content_update.ToTuple()
                
                hashes = content_update.GetHashes()
                
                affected_media = self._GetMedia( hashes )
                
                if len( affected_media ) > 0:
                    
                    self._RedrawMedia( affected_media )
                    
                    force_reload = True
                    
                
            
        
        self._PublishSelectionChange( force_reload = force_reload )
        
        if self._focussed_media is not None:
            
            self._HitMedia( self._focussed_media, False, False )
            
        
    
    def ProcessServiceUpdates( self, service_keys_to_service_updates ):
        
        ClientMedia.ListeningMediaList.ProcessServiceUpdates( self, service_keys_to_service_updates )
        
        for ( service_key, service_updates ) in service_keys_to_service_updates.items():
            
            for service_update in service_updates:
                
                ( action, row ) = service_update.ToTuple()
                
                if action in ( HC.SERVICE_UPDATE_DELETE_PENDING, HC.SERVICE_UPDATE_RESET ):
                    
                    self._RecalculateVirtualSize()
                    
                
                self._PublishSelectionChange( force_reload = True )
                
            
        
    
    def RemoveMedia( self, page_key, hashes ):
        
        if page_key == self._page_key:
            
            media = self._GetMedia( hashes )
            
            self._RemoveMedia( media, {} )
            
        
    
    def SetFocussedMedia( self, page_key, media ): pass
    
    def Sort( self, page_key, sort_by = None ):
        
        if page_key == self._page_key: ClientMedia.ListeningMediaList.Sort( self, sort_by )
        
        HydrusGlobals.client_controller.pub( 'sorted_media_pulse', self._page_key, self._sorted_media )
        
    
class MediaPanelLoading( MediaPanel ):
    
    def __init__( self, parent, page_key, file_service_key ):
        
        self._current = None
        self._max = None
        
        MediaPanel.__init__( self, parent, page_key, file_service_key, [] )
        
        HydrusGlobals.client_controller.sub( self, 'SetNumQueryResults', 'set_num_query_results' )
        
    
    def _GetPrettyStatus( self ):
        
        s = u'Loading\u2026'
        
        if self._current is not None:
            
            s += u' ' + HydrusData.ConvertIntToPrettyString( self._current )
            
            if self._max is not None:
                
                s += u' of ' + HydrusData.ConvertIntToPrettyString( self._max )
                
            
        
        return s
        
    
    def GetSortedMedia( self ): return []
    
    def SetNumQueryResults( self, current, max ):
        
        self._current = current
        
        self._max = max
        
        self._PublishSelectionChange()
        
    
class MediaPanelThumbnails( MediaPanel ):
    
    def __init__( self, parent, page_key, file_service_key, media_results ):
        
        MediaPanel.__init__( self, parent, page_key, file_service_key, media_results )
        
        self._last_client_size = ( 0, 0 )
        self._num_columns = 1
        
        self._drag_init_coordinates = None
        self._client_bmp = wx.EmptyBitmap( 20, 20, 24 )
        self._clean_canvas_pages = {}
        self._dirty_canvas_pages = []
        self._num_rows_per_canvas_page = 1
        
        self._timer_animation = wx.Timer( self, ID_TIMER_ANIMATION )
        self._thumbnails_being_faded_in = {}
        self._hashes_faded = set()
        
        ( thumbnail_span_width, thumbnail_span_height ) = self._GetThumbnailSpanDimensions()
        
        self.SetScrollRate( 0, thumbnail_span_height )
        
        self.Bind( wx.EVT_LEFT_DOWN, self.EventSelection )
        self.Bind( wx.EVT_MOTION, self.EventDragTest )
        self.Bind( wx.EVT_RIGHT_DOWN, self.EventShowMenu )
        self.Bind( wx.EVT_LEFT_DCLICK, self.EventMouseFullScreen )
        self.Bind( wx.EVT_MIDDLE_DOWN, self.EventMouseFullScreen )
        self.Bind( wx.EVT_PAINT, self.EventPaint )
        self.Bind( wx.EVT_SIZE, self.EventResize )
        self.Bind( wx.EVT_TIMER, self.TIMEREventAnimation, id = ID_TIMER_ANIMATION )
        self.Bind( wx.EVT_ERASE_BACKGROUND, self.EventEraseBackground )
        
        self.Bind( wx.EVT_KEY_DOWN, self.EventKeyDown )
        
        self.Bind( wx.EVT_MENU, self.EventMenu )
        
        self.RefreshAcceleratorTable()
        
        HydrusGlobals.client_controller.sub( self, 'NewThumbnails', 'new_thumbnails' )
        HydrusGlobals.client_controller.sub( self, 'ThumbnailsResized', 'thumbnail_resize' )
        HydrusGlobals.client_controller.sub( self, 'RefreshAcceleratorTable', 'notify_new_options' )
        HydrusGlobals.client_controller.sub( self, 'WaterfallThumbnail', 'waterfall_thumbnail' )
        
    
    def _CalculateVisiblePageIndices( self ):
        
        y_start = self._GetYStart()
        
        page_indices = set()
        
        page_indices.add( y_start / self._num_rows_per_canvas_page )
        
        if y_start % self._num_rows_per_canvas_page > 0:
            
            page_indices.add( ( y_start / self._num_rows_per_canvas_page ) + 1 )
            
        
        page_indices = list( page_indices )
        
        page_indices.sort()
        
        return page_indices
        
    
    def _CreateNewDirtyPage( self ):
        
        ( client_width, client_height ) = self.GetClientSize()
        
        ( thumbnail_span_width, thumbnail_span_height ) = self._GetThumbnailSpanDimensions()
        
        self._dirty_canvas_pages.append( wx.EmptyBitmap( client_width, self._num_rows_per_canvas_page * thumbnail_span_height, 24 ) )
        
    
    def _DirtyAllPages( self ):
        
        clean_indices = self._clean_canvas_pages.keys()
        
        for clean_index in clean_indices:
            
            self._DirtyPage( clean_index )
            
        
        self.Refresh()
        
    
    def _DirtyPage( self, clean_index ):

        bmp = self._clean_canvas_pages[ clean_index ]
        
        del self._clean_canvas_pages[ clean_index ]
        
        thumbnails = [ thumbnail for ( thumbnail_index, thumbnail ) in self._GetThumbnailsFromPageIndex( clean_index ) ]
        
        HydrusGlobals.client_controller.GetCache( 'thumbnail' ).CancelWaterfall( self._page_key, thumbnails )
        
        self._dirty_canvas_pages.append( bmp )
        
    
    def _DrawCanvasPage( self, page_index, bmp ):
        
        ( bmp_width, bmp_height ) = bmp.GetSize()
        
        dc = wx.MemoryDC( bmp )
        
        dc.SetBackground( wx.Brush( wx.Colour( *HC.options[ 'gui_colours' ][ 'thumbgrid_background' ] ) ) )
        
        dc.SetPen( wx.TRANSPARENT_PEN )
        
        dc.Clear()
        
        #
        
        page_thumbnails = self._GetThumbnailsFromPageIndex( page_index )
        
        ( thumbnail_span_width, thumbnail_span_height ) = self._GetThumbnailSpanDimensions()
        
        thumbnails_to_render_later = []
        
        thumbnail_cache = HydrusGlobals.client_controller.GetCache( 'thumbnail' )
        
        for ( thumbnail_index, thumbnail ) in page_thumbnails:
            
            hash = thumbnail.GetDisplayMedia().GetHash()
            
            self._StopFading( hash )
            
            if hash in self._hashes_faded and thumbnail_cache.HasThumbnailCached( thumbnail ):
                
                thumbnail_col = thumbnail_index % self._num_columns
                
                thumbnail_row = thumbnail_index / self._num_columns
                
                x = thumbnail_col * thumbnail_span_width + CC.THUMBNAIL_MARGIN
                
                y = ( thumbnail_row - ( page_index * self._num_rows_per_canvas_page ) ) * thumbnail_span_height + CC.THUMBNAIL_MARGIN
                
                dc.DrawBitmap( thumbnail.GetBmp(), x, y )
                
            else:
                
                thumbnails_to_render_later.append( thumbnail )
                
            
        
        HydrusGlobals.client_controller.GetCache( 'thumbnail' ).Waterfall( self._page_key, thumbnails_to_render_later )
        
    
    def _ExportFiles( self ):
        
        if len( self._selected_media ) > 0:
            
            flat_media = []
            
            for media in self._sorted_media:
                
                if media in self._selected_media:
                    
                    if media.IsCollection(): flat_media.extend( media.GetFlatMedia() )
                    else: flat_media.append( media )
                    
                
            
            with ClientGUIDialogs.DialogSetupExport( None, flat_media ) as dlg: dlg.ShowModal()
            
            self.SetFocus()
            
        
    
    def _ExportTags( self ):
        
        if len( self._selected_media ) > 0:
            
            services = HydrusGlobals.client_controller.GetServicesManager().GetServices( ( HC.LOCAL_TAG, HC.TAG_REPOSITORY, HC.COMBINED_TAG ) )
            
            service_keys = [ service.GetServiceKey() for service in services ]
            
            service_key = ClientGUIDialogs.SelectServiceKey( service_keys = service_keys )
            
            hashes = self._GetSelectedHashes()
            
            if service_key is not None:
                
                ClientGUIDialogs.ExportToHTA( self, service_key, hashes )
                
            
        
    
    def _FadeThumbnail( self, thumbnail ):
        
        try:
            
            thumbnail_index = self._sorted_media.index( thumbnail )
            
        except HydrusExceptions.DataMissing:
            
            # probably means a collect happened during an ongoing waterfall or whatever
            
            return
            
        
        if self._GetPageIndexFromThumbnailIndex( thumbnail_index ) not in self._clean_canvas_pages:
            
            return
            
        
        hash = thumbnail.GetDisplayMedia().GetHash()
        
        self._hashes_faded.add( hash )
        
        self._StopFading( hash )
        
        bmp = thumbnail.GetBmp()
        
        image = bmp.ConvertToImage()
        
        try: image.InitAlpha()
        except: pass
        
        image = image.AdjustChannels( 1, 1, 1, 0.25 )
        
        alpha_bmp = wx.BitmapFromImage( image, 32 )
        
        image.Destroy()
        
        self._thumbnails_being_faded_in[ hash ] = ( bmp, alpha_bmp, thumbnail_index, thumbnail, 0 )
        
        if not self._timer_animation.IsRunning(): self._timer_animation.Start( 1, wx.TIMER_ONE_SHOT )
        
    
    def _GenerateMediaCollection( self, media_results ): return ThumbnailMediaCollection( self._file_service_key, media_results )
    
    def _GenerateMediaSingleton( self, media_result ): return ThumbnailMediaSingleton( self._file_service_key, media_result )
    
    def _GetMediaCoordinates( self, media ):
        
        try: index = self._sorted_media.index( media )
        except: return ( -1, -1 )
        
        row = index / self._num_columns
        column = index % self._num_columns
        
        ( thumbnail_span_width, thumbnail_span_height ) = self._GetThumbnailSpanDimensions()
        
        ( x, y ) = ( column * thumbnail_span_width + CC.THUMBNAIL_MARGIN, row * thumbnail_span_height + CC.THUMBNAIL_MARGIN )
        
        return ( x, y )
        
    
    def _GetPageIndexFromThumbnailIndex( self, thumbnail_index ):
        
        thumbnails_per_page = self._num_columns * self._num_rows_per_canvas_page
        
        page_index = thumbnail_index / thumbnails_per_page
        
        return page_index
        
    
    def _GetThumbnailSpanDimensions( self ):
        
        return ClientData.AddPaddingToDimensions( HC.options[ 'thumbnail_dimensions' ], ( CC.THUMBNAIL_BORDER + CC.THUMBNAIL_MARGIN ) * 2 )
        
    
    def _GetThumbnailUnderMouse( self, mouse_event ):
        
        ( xUnit, yUnit ) = self.GetScrollPixelsPerUnit()
        
        ( x_scroll, y_scroll ) = self.GetViewStart()
        
        y_offset = y_scroll * yUnit
        
        x = mouse_event.GetX()
        y = mouse_event.GetY() + y_offset
        
        ( t_span_x, t_span_y ) = self._GetThumbnailSpanDimensions()
        
        x_mod = x % t_span_x
        y_mod = y % t_span_y
        
        if x_mod <= CC.THUMBNAIL_MARGIN or y_mod <= CC.THUMBNAIL_MARGIN or x_mod > t_span_x - CC.THUMBNAIL_MARGIN or y_mod > t_span_y - CC.THUMBNAIL_MARGIN: return None
        
        column_index = ( x / t_span_x )
        row_index = ( y / t_span_y )
        
        if column_index >= self._num_columns: return None
        
        thumbnail_index = self._num_columns * row_index + column_index
        
        if thumbnail_index >= len( self._sorted_media ): return None
        
        return self._sorted_media[ thumbnail_index ]
        
    
    def _GetThumbnailsFromPageIndex( self, page_index ):
        
        num_thumbnails_per_page = self._num_columns * self._num_rows_per_canvas_page
        
        start_index = num_thumbnails_per_page * page_index
        
        if start_index <= len( self._sorted_media ):
            
            end_index = min( len( self._sorted_media ), start_index + num_thumbnails_per_page )
            
            thumbnails = [ ( index, self._sorted_media[ index ] ) for index in range( start_index, end_index ) ]
            
        else:
            
            thumbnails = []
            
        
        return thumbnails
        
    
    def _GetYStart( self ):
        
        ( my_virtual_width, my_virtual_height ) = self.GetVirtualSize()
        
        ( my_width, my_height ) = self.GetClientSize()
        
        ( xUnit, yUnit ) = self.GetScrollPixelsPerUnit()
        
        max_y = ( my_virtual_height - my_height ) / yUnit
        
        if ( my_virtual_height - my_height ) % yUnit > 0:
            
            max_y += 1
            
        
        ( x, y ) = self.GetViewStart()
        
        y = max( 0, y )
        
        y = min( y, max_y )
        
        return y
        
    
    def _MoveFocussedThumbnail( self, rows, columns, shift ):
        
        if self._focussed_media is not None:
            
            media_to_use = self._focussed_media
            
        elif self._next_best_media_after_focussed_media_removed is not None:
            
            media_to_use = self._next_best_media_after_focussed_media_removed
            
            if columns == -1: # treat it as if the focussed area is between this and the next
                
                columns = 0
                
            
        elif len( self._sorted_media ) > 0:
            
            media_to_use = self._sorted_media[ 0 ]
            
        else:
            
            media_to_use = None
            
        
        if media_to_use is not None:
            
            current_position = self._sorted_media.index( media_to_use )
            
            new_position = current_position + columns + ( self._num_columns * rows )
            
            if new_position < 0: new_position = 0
            elif new_position > len( self._sorted_media ) - 1: new_position = len( self._sorted_media ) - 1
            
            self._HitMedia( self._sorted_media[ new_position ], False, shift )
            
            self._ScrollToMedia( media_to_use )
            
        
        
    
    def _RecalculateVirtualSize( self ):
        
        ( client_width, client_height ) = self.GetClientSize()
        
        if client_width > 0 and client_height > 0:
            
            ( thumbnail_span_width, thumbnail_span_height ) = self._GetThumbnailSpanDimensions()
            
            num_media = len( self._sorted_media )
            
            num_rows = max( 1, num_media / self._num_columns )
            
            if num_media % self._num_columns > 0: num_rows += 1
            
            virtual_width = client_width
            
            virtual_height = max( num_rows * thumbnail_span_height, client_height )
            
            if ( virtual_width, virtual_height ) != self.GetVirtualSize():
                
                self.SetVirtualSize( ( virtual_width, virtual_height ) )
                
            
        
    
    def _RedrawMedia( self, thumbnails ):
        
        visible_thumbnails = [ thumbnail for thumbnail in thumbnails if self._ThumbnailIsVisible( thumbnail ) ]
        
        thumbnail_cache = HydrusGlobals.client_controller.GetCache( 'thumbnail' )
        
        thumbnails_to_render_later = []
        
        for thumbnail in visible_thumbnails:
            
            if thumbnail_cache.HasThumbnailCached( thumbnail ):
                
                self._FadeThumbnail( thumbnail )
                
            else:
                
                thumbnails_to_render_later.append( thumbnail )
                
            
        
        if len( thumbnails_to_render_later ) > 0:
            
            HydrusGlobals.client_controller.GetCache( 'thumbnail' ).Waterfall( self._page_key, thumbnails_to_render_later )
            
        
    
    def _ReinitialisePageCacheIfNeeded( self ):
        
        old_num_rows = self._num_rows_per_canvas_page
        old_num_columns = self._num_columns
        
        ( old_client_width, old_client_height ) = self._last_client_size
        
        ( client_width, client_height ) = self.GetClientSize()
        
        ( thumbnail_span_width, thumbnail_span_height ) = self._GetThumbnailSpanDimensions()
        
        num_rows = client_height / thumbnail_span_height
        
        if client_height % thumbnail_span_height > 0:
            
            num_rows += 1
            
        
        self._num_rows_per_canvas_page = max( 1, num_rows )
        
        self._num_columns = max( 1, client_width / thumbnail_span_width )
        
        client_dimensions_changed = old_client_width != client_width or old_client_height != client_height
        thumb_layout_changed = old_num_columns != self._num_columns or old_num_rows != self._num_rows_per_canvas_page
        
        if client_dimensions_changed or thumb_layout_changed:
            
            self._client_bmp = wx.EmptyBitmap( client_width, client_height, 24 )
            
            width_got_bigger = old_client_width < client_width
            
            if thumb_layout_changed or width_got_bigger:
                
                clean_indices = self._clean_canvas_pages.keys()
                
                for clean_index in clean_indices:
                
                    self._DirtyPage( clean_index )
                    
                
                for bmp in self._dirty_canvas_pages:
                    
                    bmp.Destroy()
                    
                
                self._dirty_canvas_pages = []
                
            
            self.Refresh()
            
        
    
    def _Remove( self ):
        
        singletons = [ media for media in self._selected_media if not media.IsCollection() ]
        
        collections = [ media for media in self._selected_media if media.IsCollection() ]
        
        self._RemoveMedia( singletons, collections )
        
    
    def _RemoveMedia( self, singleton_media, collected_media ):
        
        if self._focussed_media is not None:
            
            if self._focussed_media in singleton_media or self._focussed_media in collected_media:
                
                self._SetFocussedMedia( None )
                
            
        
        MediaPanel._RemoveMedia( self, singleton_media, collected_media )
        
        self._selected_media.difference_update( singleton_media )
        self._selected_media.difference_update( collected_media )
        
        self._shift_focussed_media = None
        
        self._RecalculateVirtualSize()
        
        self._DirtyAllPages()
        
        self._PublishSelectionChange()
        
        HydrusGlobals.client_controller.pub( 'sorted_media_pulse', self._page_key, self._sorted_media )
        
    
    def _ScrollEnd( self, shift = False ):
        
        if len( self._sorted_media ) > 0:
            
            end_media = self._sorted_media[ -1 ]
            
            self._HitMedia( end_media, False, shift )
            
            self._ScrollToMedia( end_media )
            
        
    
    def _ScrollHome( self, shift = False ):
        
        if len( self._sorted_media ) > 0:
            
            home_media = self._sorted_media[ 0 ]
            
            self._HitMedia( home_media, False, shift )
            
            self._ScrollToMedia( home_media )
            
        
    
    def _ScrollToMedia( self, media ):
        
        if media is not None:
            
            ( x, y ) = self._GetMediaCoordinates( media )
            
            ( start_x, start_y ) = self.GetViewStart()
            
            ( x_unit, y_unit ) = self.GetScrollPixelsPerUnit()
            
            ( width, height ) = self.GetClientSize()
            
            ( thumbnail_span_width, thumbnail_span_height ) = self._GetThumbnailSpanDimensions()
            
            if y < start_y * y_unit:
                
                y_to_scroll_to = y / y_unit
                
                self.Scroll( -1, y_to_scroll_to )
                
                wx.PostEvent( self, wx.ScrollWinEvent( wx.wxEVT_SCROLLWIN_THUMBRELEASE, pos = y_to_scroll_to ) )
                
            elif y > ( start_y * y_unit ) + height - thumbnail_span_height:
                
                y_to_scroll_to = ( y - height ) / y_unit
                
                self.Scroll( -1, y_to_scroll_to + 2 )
                
                wx.PostEvent( self, wx.ScrollWinEvent( wx.wxEVT_SCROLLWIN_THUMBRELEASE, pos = y_to_scroll_to + 2 ) )
                
            
        
    
    def _StopFading( self, hash ):
        
        if hash in self._thumbnails_being_faded_in:
            
            ( bmp, alpha_bmp, thumbnail_index, thumbnail, num_frames ) = self._thumbnails_being_faded_in[ hash ]
            
            del self._thumbnails_being_faded_in[ hash ]
            
            bmp.Destroy()
            alpha_bmp.Destroy()
            
        
    
    def _ThumbnailIsVisible( self, thumbnail ):
        
        try:
            
            index = self._sorted_media.index( thumbnail )
            
        except HydrusExceptions.DataMissing:
            
            return False
            
        
        if self._GetPageIndexFromThumbnailIndex( index ) in self._clean_canvas_pages:
            
            return True
            
        else:
            
            return False
            
        
    
    def AddMediaResults( self, page_key, media_results, append = True ):
        
        if page_key == self._page_key:
            
            thumbnails = MediaPanel.AddMediaResults( self, page_key, media_results, append = append )
            
            self._RecalculateVirtualSize()
            
            for thumbnail in thumbnails:
                
                self._FadeThumbnail( thumbnail )
                
            
            if len( self._selected_media ) == 0:
                
                self._PublishSelectionIncrement( thumbnails )
                
            
        
    
    def EventDragTest( self, event ):
        
        if event.LeftIsDown() and self._drag_init_coordinates is not None:
            
            ( old_x, old_y ) = self._drag_init_coordinates
            
            ( x, y ) = event.GetPosition()
            
            ( delta_x, delta_y ) = ( x - old_x, y - old_y )
            
            if abs( delta_x ) > 5 or abs( delta_y ) > 5:
                
                hashes = self._GetSelectedHashes( discriminant = CC.DISCRIMINANT_LOCAL, ordered = True )
                
                if len( hashes ) > 0:
                    
                    drop_source = wx.DropSource( self )
                    
                    data_object = wx.DataObjectComposite()
                    
                    #
                    
                    hydrus_media_data_object = wx.CustomDataObject( 'application/hydrus-media' )
                    
                    data = json.dumps( [ hash.encode( 'hex' ) for hash in hashes ] )
                    
                    hydrus_media_data_object.SetData( data )
                    
                    data_object.Add( hydrus_media_data_object, True )
                    
                    #
                    
                    file_data_object = wx.FileDataObject()
                    
                    client_files_manager = HydrusGlobals.client_controller.GetClientFilesManager()
                    
                    for hash in hashes:
                        
                        path = client_files_manager.GetFilePath( hash )
                        
                        file_data_object.AddFile( path )
                        
                    
                    data_object.Add( file_data_object )
                    
                    #
                    
                    drop_source.SetData( data_object )
                    
                    drop_source.DoDragDrop()
                    
                
                self._drag_init_coordinates = None
                
            
        
    
    def EventEraseBackground( self, event ): pass
    
    def EventKeyDown( self, event ):
        
        # accelerator tables can't handle escape key in windows, gg
        
        if event.GetKeyCode() == wx.WXK_ESCAPE: self._Select( 'none' )
        if event.GetKeyCode() in ( wx.WXK_PAGEUP, wx.WXK_PAGEDOWN ):
            
            if event.GetKeyCode() == wx.WXK_PAGEUP:
                
                direction = -1
                
            elif event.GetKeyCode() == wx.WXK_PAGEDOWN:
                
                direction = 1
                
            
            shift = event.ShiftDown()
            
            self._MoveFocussedThumbnail( self._num_rows_per_canvas_page * direction, 0, shift )
            
        else: event.Skip()
        
    
    def EventMenu( self, event ):
        
        action = ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetAction( event.GetId() )
        
        if action is not None:
            
            ( command, data ) = action
            
            if command == 'archive': self._Archive()
            elif command == 'copy_bmp': self._CopyBMPToClipboard()
            elif command == 'copy_files': self._CopyFilesToClipboard()
            elif command == 'copy_hash': self._CopyHashToClipboard( data )
            elif command == 'copy_hashes': self._CopyHashesToClipboard( data )
            elif command == 'copy_known_urls': self._CopyKnownURLsToClipboard()
            elif command == 'copy_hashes': self._CopyHashesToClipboard( data )
            elif command == 'copy_service_filename': self._CopyServiceFilenameToClipboard( data )
            elif command == 'copy_service_filenames': self._CopyServiceFilenamesToClipboard( data )
            elif command == 'copy_path': self._CopyPathToClipboard()
            elif command == 'copy_paths': self._CopyPathsToClipboard()
            elif command == 'ctrl-space':
                
                if self._focussed_media is not None: self._HitMedia( self._focussed_media, True, False )
                
            elif command == 'custom_filter':
                
                self._CustomFilter( data )
                
            elif command == 'delete':
                
                if data is None:
                    
                    self._Delete()
                    
                else:
                    
                    self._Delete( data )
                    
                
            elif command == 'export_files': self._ExportFiles()
            elif command == 'export_tags': self._ExportTags()
            elif command == 'filter': self._Filter()
            elif command == 'fullscreen': self._FullScreen()
            elif command == 'inbox': self._Inbox()
            elif command == 'manage_ratings': self._ManageRatings()
            elif command == 'manage_tags': self._ManageTags()
            elif command == 'modify_account': self._ModifyUploaders( data )
            elif command == 'open_externally': self._OpenExternally()
            elif command == 'petition': self._PetitionFiles( data )
            elif command == 'remove': self._Remove()
            elif command == 'rescind_petition': self._RescindPetitionFiles( data )
            elif command == 'rescind_upload': self._RescindUploadFiles( data )
            elif command == 'scroll_end': self._ScrollEnd( False )
            elif command == 'scroll_home': self._ScrollHome( False )
            elif command == 'shift_scroll_end': self._ScrollEnd( True )
            elif command == 'shift_scroll_home': self._ScrollHome( True )
            elif command == 'select': self._Select( data )
            elif command == 'share_on_local_booru': self._ShareOnLocalBooru()
            elif command == 'show_selection_in_new_query_page': self._ShowSelectionInNewQueryPage()
            elif command == 'undelete': self._Undelete()
            elif command == 'upload': self._UploadFiles( data )
            elif command == 'upload_directory': self._UploadDirectory( data )
            elif command == 'key_up': self._MoveFocussedThumbnail( -1, 0, False )
            elif command == 'key_down': self._MoveFocussedThumbnail( 1, 0, False )
            elif command == 'key_left': self._MoveFocussedThumbnail( 0, -1, False )
            elif command == 'key_right': self._MoveFocussedThumbnail( 0, 1, False )
            elif command == 'key_shift_up': self._MoveFocussedThumbnail( -1, 0, True )
            elif command == 'key_shift_down': self._MoveFocussedThumbnail( 1, 0, True )
            elif command == 'key_shift_left': self._MoveFocussedThumbnail( 0, -1, True )
            elif command == 'key_shift_right': self._MoveFocussedThumbnail( 0, 1, True )
            else: event.Skip()
            
        
    
    def EventMouseFullScreen( self, event ):
        
        t = self._GetThumbnailUnderMouse( event )
        
        if t is not None:
            
            locations_manager = t.GetLocationsManager()
            
            if locations_manager.IsLocal(): self._FullScreen( t )
            elif self._file_service_key != CC.COMBINED_FILE_SERVICE_KEY:
                
                if len( locations_manager.GetCurrentRemote() ) > 0:
                    
                    self._DownloadHashes( t.GetHashes() )
                    
                
            
        
    
    def EventPaint( self, event ):
        
        dc = wx.BufferedPaintDC( self, self._client_bmp )
        
        ( client_x, client_y ) = self.GetClientSize()
        
        ( thumbnail_span_width, thumbnail_span_height ) = self._GetThumbnailSpanDimensions()
        
        page_height = self._num_rows_per_canvas_page * thumbnail_span_height
        
        page_indices_to_display = self._CalculateVisiblePageIndices()
        
        earliest_page_index_to_display = min( page_indices_to_display )
        last_page_index_to_display = max( page_indices_to_display )
        
        page_indices_to_draw = list( page_indices_to_display )
        
        if earliest_page_index_to_display > 0:
            
            page_indices_to_draw.append( earliest_page_index_to_display - 1 )
            
        
        page_indices_to_draw.append( last_page_index_to_display + 1 )
        
        page_indices_to_draw.sort()
        
        potential_clean_indices_to_steal = [ page_index for page_index in self._clean_canvas_pages.keys() if page_index not in page_indices_to_draw ]
        
        random.shuffle( potential_clean_indices_to_steal )
        
        ( xUnit, yUnit ) = self.GetScrollPixelsPerUnit()
        
        y_start = self._GetYStart()
        
        earliest_y = y_start * yUnit
        
        for page_index in page_indices_to_draw:
            
            if page_index not in self._clean_canvas_pages:
                
                if len( self._dirty_canvas_pages ) == 0:
                    
                    if len( potential_clean_indices_to_steal ) > 0:
                        
                        index_to_steal = potential_clean_indices_to_steal.pop( 0 )
                        
                        self._DirtyPage( index_to_steal )
                        
                    else:
                        
                        self._CreateNewDirtyPage()
                        
                    
                
                bmp = self._dirty_canvas_pages.pop( 0 )
                
                self._DrawCanvasPage( page_index, bmp )
                
                self._clean_canvas_pages[ page_index ] = bmp
                
            
            if page_index in page_indices_to_display:
                
                bmp = self._clean_canvas_pages[ page_index ]
                
                page_virtual_y = page_height * page_index
                
                page_client_y = page_virtual_y - earliest_y
                
                dc.DrawBitmap( bmp, 0, page_client_y )
                
            
        
    
    def EventResize( self, event ):
        
        self._ReinitialisePageCacheIfNeeded()
        
        self._RecalculateVirtualSize()
        
        self._last_client_size = self.GetClientSize()
        
    
    def EventSelection( self, event ):
        
        self._drag_init_coordinates = event.GetPosition()
        
        self._HitMedia( self._GetThumbnailUnderMouse( event ), event.CmdDown(), event.ShiftDown() )
        
        if not ( event.CmdDown() or event.ShiftDown() ):
            
            self._ScrollToMedia( self._focussed_media )
            
        
        event.Skip()
        
    
    def EventShowMenu( self, event ):
        
        services_manager = HydrusGlobals.client_controller.GetServicesManager()
        
        thumbnail = self._GetThumbnailUnderMouse( event )
        
        if thumbnail is not None: self._HitMedia( thumbnail, event.CmdDown(), event.ShiftDown() )
        
        all_locations_managers = [ media.GetLocationsManager() for media in self._sorted_media ]
        selected_locations_managers = [ media.GetLocationsManager() for media in self._selected_media ]
        
        selection_has_local = True in ( locations_manager.IsLocal() for locations_manager in selected_locations_managers )
        selection_has_local_file_domain = True in ( CC.LOCAL_FILE_SERVICE_KEY in locations_manager.GetCurrent() for locations_manager in selected_locations_managers )
        selection_has_trash = True in ( CC.TRASH_SERVICE_KEY in locations_manager.GetCurrent() for locations_manager in selected_locations_managers )
        selection_has_inbox = True in ( media.HasInbox() for media in self._selected_media )
        selection_has_archive = True in ( media.HasArchive() for media in self._selected_media )
        
        all_file_domains = HydrusData.MassUnion( locations_manager.GetCurrent() for locations_manager in all_locations_managers )
        all_specific_file_domains = all_file_domains.difference( { CC.COMBINED_FILE_SERVICE_KEY, CC.COMBINED_LOCAL_FILE_SERVICE_KEY } )
        all_local_file_domains = services_manager.Filter( all_specific_file_domains, ( HC.LOCAL_FILE_DOMAIN, ) )
        all_file_repos = services_manager.Filter( all_specific_file_domains, ( HC.FILE_REPOSITORY, ) )
        
        media_has_inbox = True in ( media.HasInbox() for media in self._sorted_media )
        media_has_archive = True in ( media.HasArchive() for media in self._sorted_media )
        
        menu = wx.Menu()
        
        if thumbnail is None:
            
            ClientGUIMenus.AppendMenuItem( self, menu, 'refresh', 'Refresh the current search.', HydrusGlobals.client_controller.pub, 'refresh_query', self._page_key )
            
            if len( self._sorted_media ) > 0:
                
                ClientGUIMenus.AppendSeparator( menu )
                
                select_menu = wx.Menu()
                
                if len( self._selected_media ) < len( self._sorted_media ):
                    
                    ClientGUIMenus.AppendMenuItem( self, select_menu, 'all', 'Select everything.', self._Select, 'all' )
                    
                
                ClientGUIMenus.AppendMenuItem( self, select_menu, 'invert', 'Swap what is and is not selected.', self._Select, 'invert' )
                
                if media_has_archive and media_has_inbox:
                    
                    ClientGUIMenus.AppendMenuItem( self, select_menu, 'inbox', 'Select everything in the inbox.', self._Select, 'inbox' )
                    ClientGUIMenus.AppendMenuItem( self, select_menu, 'archive', 'Select everything that is archived.', self._Select, 'archive' )
                    
                
                if len( all_specific_file_domains ) > 1:
                    
                    selectable_file_domains = list( all_local_file_domains )
                    
                    if CC.TRASH_SERVICE_KEY in all_specific_file_domains:
                        
                        selectable_file_domains.append( CC.TRASH_SERVICE_KEY )
                        
                    
                    selectable_file_domains.extend( all_file_repos )
                    
                    for service_key in selectable_file_domains:
                        
                        name = services_manager.GetName( service_key )
                        
                        ClientGUIMenus.AppendMenuItem( self, select_menu, name, 'Select everything in ' + name + '.', self._Select, 'file_service', service_key )
                        
                    
                
                if len( self._selected_media ) > 0:
                    
                    ClientGUIMenus.AppendMenuItem( self, select_menu, 'none', 'Deselect everything.', self._Select, 'none' )
                    
                
                ClientGUIMenus.AppendMenu( menu, select_menu, 'select' )
                
            
        else:
            
            if self._focussed_media is not None:
                
                # variables
                
                num_selected = self._GetNumSelected()
                
                multiple_selected = num_selected > 1
                
                services_manager = HydrusGlobals.client_controller.GetServicesManager()
                
                services = services_manager.GetServices()
                
                service_keys_to_names = { service.GetServiceKey() : service.GetName() for service in services }
                
                tag_repositories = [ service for service in services if service.GetServiceType() == HC.TAG_REPOSITORY ]
                
                file_repositories = [ service for service in services if service.GetServiceType() == HC.FILE_REPOSITORY ]
                
                ipfs_services = [ service for service in services if service.GetServiceType() == HC.IPFS ]
                
                local_ratings_services = [ service for service in services if service.GetServiceType() in ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ) ]
                
                local_booru_service = [ service for service in services if service.GetServiceType() == HC.LOCAL_BOORU ][0]
                
                local_booru_is_running = local_booru_service.GetPort() is not None
                
                i_can_post_ratings = len( local_ratings_services ) > 0
                
                focussed_is_local = CC.LOCAL_FILE_SERVICE_KEY in self._focussed_media.GetLocationsManager().GetCurrent()
                
                file_service_keys = { repository.GetServiceKey() for repository in file_repositories }
                upload_permission_file_service_keys = { repository.GetServiceKey() for repository in file_repositories if repository.HasPermission( HC.CONTENT_TYPE_FILES, HC.PERMISSION_ACTION_CREATE ) }
                petition_resolve_permission_file_service_keys = { repository.GetServiceKey() for repository in file_repositories if repository.HasPermission( HC.CONTENT_TYPE_FILES, HC.PERMISSION_ACTION_OVERRULE ) }
                petition_permission_file_service_keys = { repository.GetServiceKey() for repository in file_repositories if repository.HasPermission( HC.CONTENT_TYPE_FILES, HC.PERMISSION_ACTION_PETITION ) } - petition_resolve_permission_file_service_keys
                user_manage_permission_file_service_keys = { repository.GetServiceKey() for repository in file_repositories if repository.HasPermission( HC.CONTENT_TYPE_ACCOUNTS, HC.PERMISSION_ACTION_OVERRULE ) }
                ipfs_service_keys = { service.GetServiceKey() for service in ipfs_services }
                
                focussed_is_ipfs = True in ( service_key in ipfs_service_keys for service_key in self._focussed_media.GetLocationsManager().GetCurrentRemote() )
                
                if multiple_selected:
                    
                    download_phrase = 'download all possible selected'
                    rescind_download_phrase = 'cancel downloads for all possible selected'
                    upload_phrase = 'upload all possible selected to'
                    rescind_upload_phrase = 'rescind pending selected uploads to'
                    petition_phrase = 'petition all possible selected for removal from'
                    rescind_petition_phrase = 'rescind selected petitions for'
                    remote_delete_phrase = 'delete all possible selected from'
                    modify_account_phrase = 'modify the accounts that uploaded selected to'
                    
                    pin_phrase = 'pin all to'
                    rescind_pin_phrase = 'rescind pin to'
                    unpin_phrase = 'unpin all from'
                    rescind_unpin_phrase = 'rescind unpin from'
                    
                    manage_tags_phrase = 'selected files\' tags'
                    manage_ratings_phrase = 'selected files\' ratings'
                    
                    archive_phrase = 'archive selected'
                    inbox_phrase = 'return selected to inbox'
                    remove_phrase = 'remove selected'
                    local_delete_phrase = 'delete selected'
                    trash_delete_phrase = 'delete selected from trash now'
                    undelete_phrase = 'undelete selected'
                    dump_phrase = 'dump selected to 4chan'
                    export_phrase = 'files'
                    copy_phrase = 'files'
                    
                else:
                    
                    download_phrase = 'download'
                    rescind_download_phrase = 'cancel download'
                    upload_phrase = 'upload to'
                    rescind_upload_phrase = 'rescind pending upload to'
                    petition_phrase = 'petition for removal from'
                    rescind_petition_phrase = 'rescind petition for'
                    remote_delete_phrase = 'delete from'
                    modify_account_phrase = 'modify the account that uploaded this to'
                    
                    pin_phrase = 'pin to'
                    rescind_pin_phrase = 'rescind pin to'
                    unpin_phrase = 'unpin from'
                    rescind_unpin_phrase = 'rescind unpin from'
                    
                    manage_tags_phrase = 'file\'s tags'
                    manage_ratings_phrase = 'file\'s ratings'
                    
                    archive_phrase = 'archive'
                    inbox_phrase = 'return to inbox'
                    remove_phrase = 'remove'
                    local_delete_phrase = 'delete'
                    trash_delete_phrase = 'delete from trash now'
                    undelete_phrase = 'undelete'
                    dump_phrase = 'dump to 4chan'
                    export_phrase = 'file'
                    copy_phrase = 'file'
                    
                
                # info about the files
                
                groups_of_current_remote_service_keys = [ locations_manager.GetCurrentRemote() for locations_manager in selected_locations_managers ]
                groups_of_pending_remote_service_keys = [ locations_manager.GetPendingRemote() for locations_manager in selected_locations_managers ]
                groups_of_petitioned_remote_service_keys = [ locations_manager.GetPetitionedRemote() for locations_manager in selected_locations_managers ]
                groups_of_deleted_remote_service_keys = [ locations_manager.GetDeletedRemote() for locations_manager in selected_locations_managers ]
                
                current_remote_service_keys = HydrusData.MassUnion( groups_of_current_remote_service_keys )
                pending_remote_service_keys = HydrusData.MassUnion( groups_of_pending_remote_service_keys )
                petitioned_remote_service_keys = HydrusData.MassUnion( groups_of_petitioned_remote_service_keys )
                deleted_remote_service_keys = HydrusData.MassUnion( groups_of_deleted_remote_service_keys )
                
                common_current_remote_service_keys = HydrusData.IntelligentMassIntersect( groups_of_current_remote_service_keys )
                common_pending_remote_service_keys = HydrusData.IntelligentMassIntersect( groups_of_pending_remote_service_keys )
                common_petitioned_remote_service_keys = HydrusData.IntelligentMassIntersect( groups_of_petitioned_remote_service_keys )
                common_deleted_remote_service_keys = HydrusData.IntelligentMassIntersect( groups_of_deleted_remote_service_keys )
                
                disparate_current_remote_service_keys = current_remote_service_keys - common_current_remote_service_keys
                disparate_pending_remote_service_keys = pending_remote_service_keys - common_pending_remote_service_keys
                disparate_petitioned_remote_service_keys = petitioned_remote_service_keys - common_petitioned_remote_service_keys
                disparate_deleted_remote_service_keys = deleted_remote_service_keys - common_deleted_remote_service_keys
                
                some_downloading = True in ( locations_manager.IsDownloading() for locations_manager in selected_locations_managers )
                
                pending_file_service_keys = pending_remote_service_keys.intersection( file_service_keys )
                petitioned_file_service_keys = petitioned_remote_service_keys.intersection( file_service_keys )
                
                common_current_file_service_keys = common_current_remote_service_keys.intersection( file_service_keys )
                common_pending_file_service_keys = common_pending_remote_service_keys.intersection( file_service_keys )
                common_petitioned_file_service_keys = common_petitioned_remote_service_keys.intersection( file_service_keys )
                common_deleted_file_service_keys = common_deleted_remote_service_keys.intersection( file_service_keys )
                
                disparate_current_file_service_keys = disparate_current_remote_service_keys.intersection( file_service_keys )
                disparate_pending_file_service_keys = disparate_pending_remote_service_keys.intersection( file_service_keys )
                disparate_petitioned_file_service_keys = disparate_petitioned_remote_service_keys.intersection( file_service_keys )
                disparate_deleted_file_service_keys = disparate_deleted_remote_service_keys.intersection( file_service_keys )
                
                pending_ipfs_service_keys = pending_remote_service_keys.intersection( ipfs_service_keys )
                petitioned_ipfs_service_keys = petitioned_remote_service_keys.intersection( ipfs_service_keys )
                
                common_current_ipfs_service_keys = common_current_remote_service_keys.intersection( ipfs_service_keys )
                common_pending_ipfs_service_keys = common_pending_file_service_keys.intersection( ipfs_service_keys )
                common_petitioned_ipfs_service_keys = common_petitioned_remote_service_keys.intersection( ipfs_service_keys )
                
                disparate_current_ipfs_service_keys = disparate_current_remote_service_keys.intersection( ipfs_service_keys )
                disparate_pending_ipfs_service_keys = disparate_pending_remote_service_keys.intersection( ipfs_service_keys )
                disparate_petitioned_ipfs_service_keys = disparate_petitioned_remote_service_keys.intersection( ipfs_service_keys )
                
                # valid commands for the files
                
                uploadable_file_service_keys = set()
                
                downloadable_file_service_keys = set()
                
                petitionable_file_service_keys = set()
                
                deletable_file_service_keys = set()
                
                modifyable_file_service_keys = set()
                
                pinnable_ipfs_service_keys = set()
                
                unpinnable_ipfs_service_keys = set()
                
                for locations_manager in selected_locations_managers:
                    
                    # FILE REPOS
                    
                    # we can upload (set pending) to a repo_id when we have permission, a file is local, not current, not pending, and either ( not deleted or we_can_overrule )
                    
                    if locations_manager.IsLocal():
                        
                        uploadable_file_service_keys.update( upload_permission_file_service_keys - locations_manager.GetCurrentRemote() - locations_manager.GetPendingRemote() - ( locations_manager.GetDeletedRemote() - petition_resolve_permission_file_service_keys ) )
                        
                    
                    # we can download (set pending to local) when we have permission, a file is not local and not already downloading and current
                    
                    if not locations_manager.IsLocal() and not locations_manager.IsDownloading():
                        
                        downloadable_file_service_keys.update( file_service_keys & locations_manager.GetCurrentRemote() )
                        
                    
                    # we can petition when we have permission and a file is current and it is not already petitioned
                    
                    petitionable_file_service_keys.update( ( petition_permission_file_service_keys & locations_manager.GetCurrentRemote() ) - locations_manager.GetPetitionedRemote() )
                    
                    # we can delete remote when we have permission and a file is current and it is not already petitioned
                    
                    deletable_file_service_keys.update( ( petition_resolve_permission_file_service_keys & locations_manager.GetCurrentRemote() ) - locations_manager.GetPetitionedRemote() )
                    
                    # we can modify users when we have permission and the file is current or deleted
                    
                    modifyable_file_service_keys.update( user_manage_permission_file_service_keys & ( locations_manager.GetCurrentRemote() | locations_manager.GetDeletedRemote() ) )
                    
                    # IPFS
                    
                    # we can pin if a file is local, not current, not pending
                    
                    if locations_manager.IsLocal():
                        
                        pinnable_ipfs_service_keys.update( ipfs_service_keys - locations_manager.GetCurrentRemote() - locations_manager.GetPendingRemote() )
                        
                    
                    # we can unpin a file if it is current and not petitioned
                    
                    unpinnable_ipfs_service_keys.update( ( ipfs_service_keys & locations_manager.GetCurrentRemote() ) - locations_manager.GetPetitionedRemote() )
                    
                
                # do the actual menu
                
                if multiple_selected:
                    
                    ClientGUIMenus.AppendMenuLabel( menu, HydrusData.ConvertIntToPrettyString( num_selected ) + ' files, ' + self._GetPrettyTotalSelectedSize() )
                    
                else:
                    
                    for line in thumbnail.GetPrettyInfoLines():
                        
                        ClientGUIMenus.AppendMenuLabel( menu, line )
                        
                    
                
                if len( disparate_current_file_service_keys ) > 0:
                    
                    AddServiceKeyLabelsToMenu( menu, disparate_current_file_service_keys, 'some uploaded to' )
                    
                
                if multiple_selected and len( common_current_file_service_keys ) > 0:
                    
                    AddServiceKeyLabelsToMenu( menu, common_current_file_service_keys, 'selected uploaded to' )
                    
                
                if len( disparate_pending_file_service_keys ) > 0:
                    
                    AddServiceKeyLabelsToMenu( menu, disparate_pending_file_service_keys, 'some pending to' )
                    
                
                if len( common_pending_file_service_keys ) > 0:
                    
                    AddServiceKeyLabelsToMenu( menu, common_pending_file_service_keys, 'pending to' )
                    
                
                if len( disparate_petitioned_file_service_keys ) > 0:
                    
                    AddServiceKeyLabelsToMenu( menu, disparate_petitioned_file_service_keys, 'some petitioned from' )
                    
                
                if len( common_petitioned_file_service_keys ) > 0:
                    
                    AddServiceKeyLabelsToMenu( menu, common_petitioned_file_service_keys, 'petitioned from' )
                    
                
                if len( disparate_deleted_file_service_keys ) > 0:
                    
                    AddServiceKeyLabelsToMenu( menu, disparate_deleted_file_service_keys, 'some deleted from' )
                    
                
                if len( common_deleted_file_service_keys ) > 0:
                    
                    AddServiceKeyLabelsToMenu( menu, common_deleted_file_service_keys, 'deleted from' )
                    
                
                if len( disparate_current_ipfs_service_keys ) > 0:
                    
                    AddServiceKeyLabelsToMenu( menu, disparate_current_ipfs_service_keys, 'some pinned to' )
                    
                
                if multiple_selected and len( common_current_ipfs_service_keys ) > 0:
                    
                    AddServiceKeyLabelsToMenu( menu, common_current_ipfs_service_keys, 'selected pinned to' )
                    
                
                if len( disparate_pending_ipfs_service_keys ) > 0:
                    
                    AddServiceKeyLabelsToMenu( menu, disparate_pending_ipfs_service_keys, 'some to be pinned to' )
                    
                
                if len( common_pending_ipfs_service_keys ) > 0:
                    
                    AddServiceKeyLabelsToMenu( menu, common_pending_ipfs_service_keys, 'to be pinned to' )
                    
                
                if len( disparate_petitioned_ipfs_service_keys ) > 0:
                    
                    AddServiceKeyLabelsToMenu( menu, disparate_petitioned_ipfs_service_keys, 'some to be unpinned from' )
                    
                
                if len( common_petitioned_ipfs_service_keys ) > 0:
                    
                    AddServiceKeyLabelsToMenu( menu, common_petitioned_ipfs_service_keys, unpin_phrase )
                    
                
                ClientGUIMenus.AppendSeparator( menu )
                
                #
                
                len_interesting_remote_service_keys = 0
                
                len_interesting_remote_service_keys += len( downloadable_file_service_keys )
                len_interesting_remote_service_keys += len( uploadable_file_service_keys )
                len_interesting_remote_service_keys += len( pending_file_service_keys )
                len_interesting_remote_service_keys += len( petitionable_file_service_keys )
                len_interesting_remote_service_keys += len( petitioned_file_service_keys )
                len_interesting_remote_service_keys += len( deletable_file_service_keys )
                len_interesting_remote_service_keys += len( modifyable_file_service_keys )
                len_interesting_remote_service_keys += len( pinnable_ipfs_service_keys )
                len_interesting_remote_service_keys += len( pending_ipfs_service_keys )
                len_interesting_remote_service_keys += len( unpinnable_ipfs_service_keys )
                len_interesting_remote_service_keys += len( petitioned_ipfs_service_keys )
                
                if multiple_selected:
                    
                    len_interesting_remote_service_keys += len( ipfs_service_keys )
                    
                
                if len_interesting_remote_service_keys > 0:
                    
                    remote_action_menu = wx.Menu()
                    
                    if len( downloadable_file_service_keys ) > 0:
                        
                        ClientGUIMenus.AppendMenuItem( self, remote_action_menu, download_phrase, 'Download all possible selected files.', self._DownloadSelected )
                        
                    
                    if some_downloading:
                        
                        ClientGUIMenus.AppendMenuItem( self, remote_action_menu, rescind_download_phrase, 'Stop downloading any of the selected files.', self._RescindDownloadSelected )
                        
                    
                    if len( uploadable_file_service_keys ) > 0:
                        
                        AddServiceKeysToMenu( self, remote_action_menu, uploadable_file_service_keys, upload_phrase, 'Upload all selected files to the file repository.', self._UploadFiles )
                        
                    
                    if len( pending_file_service_keys ) > 0:
                        
                        AddServiceKeysToMenu( self, remote_action_menu, pending_file_service_keys, rescind_upload_phrase, 'Rescind the pending upload to the file repository.', self._RescindUploadFiles )
                        
                    
                    if len( petitionable_file_service_keys ) > 0:
                        
                        AddServiceKeysToMenu( self, remote_action_menu, petitionable_file_service_keys, petition_phrase, 'Petition these files for deletion from the file repository.', self._PetitionFiles )
                        
                    
                    if len( petitioned_file_service_keys ) > 0:
                        
                        AddServiceKeysToMenu( self, remote_action_menu, petitioned_file_service_keys, rescind_petition_phrase, 'Rescind the petition to delete these files from the file repository.', self._RescindPetitionFiles )
                        
                    
                    if len( deletable_file_service_keys ) > 0:
                        
                        AddServiceKeysToMenu( self, remote_action_menu, deletable_file_service_keys, remote_delete_phrase, 'Delete these files from the file repository.', self._Delete )
                        
                    
                    if len( modifyable_file_service_keys ) > 0:
                        
                        AddServiceKeysToMenu( self, remote_action_menu, modifyable_file_service_keys, modify_account_phrase, 'Modify the account(s) that uploaded these files to the file repository.', self._ModifyUploaders )
                        
                    
                    if len( pinnable_ipfs_service_keys ) > 0:
                        
                        AddServiceKeysToMenu( self, remote_action_menu, pinnable_ipfs_service_keys, pin_phrase, 'Pin these files to the ipfs service.', self._UploadFiles )
                        
                    
                    if len( pending_ipfs_service_keys ) > 0:
                        
                        AddServiceKeysToMenu( self, remote_action_menu, pending_ipfs_service_keys, rescind_pin_phrase, 'Rescind the pending pin to the ipfs service.', self._RescindUploadFiles )
                        
                    
                    if len( unpinnable_ipfs_service_keys ) > 0:
                        
                        AddServiceKeysToMenu( self, remote_action_menu, unpinnable_ipfs_service_keys, unpin_phrase, 'Unpin these files from the ipfs service.', self._PetitionFiles )
                        
                    
                    if len( petitioned_ipfs_service_keys ) > 0:
                        
                        AddServiceKeysToMenu( self, remote_action_menu, petitioned_ipfs_service_keys, rescind_unpin_phrase, 'Rescind the pending unpin from the ipfs service.', self._RescindPetitionFiles )
                        
                    
                    if multiple_selected and len( ipfs_service_keys ) > 0:
                        
                        AddServiceKeysToMenu( self, remote_action_menu, ipfs_service_keys, 'pin new directory to', 'Pin these files as a directory to the ipfs service.', self._UploadDirectory )
                        
                    
                    ClientGUIMenus.AppendMenu( menu, remote_action_menu, 'remote services' )
                    
                
                #
                
                if i_can_post_ratings:
                    
                    manage_menu = wx.Menu()
                    
                    ClientGUIMenus.AppendMenuItem( self, manage_menu, manage_tags_phrase, 'Manage tags for the selected files.', self._ManageTags )
                    ClientGUIMenus.AppendMenuItem( self, manage_menu, manage_ratings_phrase, 'Manage ratings for the selected files.', self._ManageRatings )
                    
                    ClientGUIMenus.AppendMenu( menu, manage_menu, 'manage' )
                    
                else:
                    
                    if multiple_selected:
                        
                        phrase = 'manage files\' tags'
                        
                    else:
                        
                        phrase = 'manage file\'s tags'
                        
                    
                    ClientGUIMenus.AppendMenuItem( self, menu, phrase, 'Manage tags for the selected files.', self._ManageTags )
                    
                
                #
                
                if selection_has_local and multiple_selected:
                    
                    filter_menu = wx.Menu()
                    
                    if selection_has_local_file_domain:
                        
                        ClientGUIMenus.AppendMenuItem( self, filter_menu, 'archive/delete', 'Launch a special media viewer that will quickly archive (left-click) and delete (right-click) the selected media.', self._Filter )
                        
                    
                    shortcut_names = HydrusGlobals.client_controller.Read( 'serialisable_names', HydrusSerialisable.SERIALISABLE_TYPE_SHORTCUTS )
                    
                    if len( shortcut_names ) > 0:
                        
                        custom_shortcuts_menu = wx.Menu()
                        
                        ClientGUIMenus.AppendMenuItem( self, custom_shortcuts_menu, 'manage', 'Manage your different custom filters and their shortcuts.', self._CustomFilter )
                        
                        ClientGUIMenus.AppendSeparator( custom_shortcuts_menu )
                        
                        for shortcut_name in shortcut_names:
                            
                            ClientGUIMenus.AppendMenuItem( self, custom_shortcuts_menu, shortcut_name, 'Open the ' + shortcut_name + ' custom filter.', self._CustomFilter, shortcut_name )
                            
                        
                        ClientGUIMenus.AppendMenu( filter_menu, custom_shortcuts_menu, 'custom filters' )
                        
                    else:
                        
                        ClientGUIMenus.AppendMenuItem( self, filter_menu, 'create a custom filter', 'Create a custom filter that uses non-default shortcuts.', self._CustomFilter )
                        
                    
                    ClientGUIMenus.AppendMenu( menu, filter_menu, 'filter' )
                    
                
                ClientGUIMenus.AppendSeparator( menu )
                
                if selection_has_inbox:
                    
                    ClientGUIMenus.AppendMenuItem( self, menu, archive_phrase, 'Archive the selected files.', self._Archive )
                    
                
                if selection_has_archive:
                    
                    ClientGUIMenus.AppendMenuItem( self, menu, inbox_phrase, 'Put the selected files back in the inbox.', self._Inbox )
                    
                
                ClientGUIMenus.AppendMenuItem( self, menu, remove_phrase, 'Remove the selected files from the current view.', self._Remove )
                
                if selection_has_local_file_domain:
                    
                    ClientGUIMenus.AppendMenuItem( self, menu, local_delete_phrase, 'Delete the selected files from \'my files\'.', self._Delete, CC.LOCAL_FILE_SERVICE_KEY )
                    
                
                if selection_has_trash:
                    
                    ClientGUIMenus.AppendMenuItem( self, menu, trash_delete_phrase, 'Delete the selected files from the trash, forcing an immediate physical delete from your hard drive.', self._Delete, CC.TRASH_SERVICE_KEY )
                    ClientGUIMenus.AppendMenuItem( self, menu, undelete_phrase, 'Restore the selected files back to \'my files\'.', self._Undelete )
                    
                
                # share
                
                ClientGUIMenus.AppendSeparator( menu )
                
                if selection_has_local:
                    
                    ClientGUIMenus.AppendMenuItem( self, menu, 'open externally', 'Launch this file with your OS\'s default program for it.', self._OpenExternally )
                    
                
                share_menu = wx.Menu()
                
                #
                
                copy_menu = wx.Menu()
                
                if selection_has_local:
                    
                    ClientGUIMenus.AppendMenuItem( self, copy_menu, copy_phrase, 'Copy the selected files to the clipboard.', self._CopyFilesToClipboard )
                    
                    copy_hash_menu = wx.Menu()
                    
                    ClientGUIMenus.AppendMenuItem( self, copy_hash_menu, 'sha256 (hydrus default)', 'Copy the selected file\'s SHA256 hash to the clipboard.', self._CopyHashToClipboard, 'sha256' )
                    ClientGUIMenus.AppendMenuItem( self, copy_hash_menu, 'md5', 'Copy the selected file\'s MD5 hash to the clipboard.', self._CopyHashToClipboard, 'md5' )
                    ClientGUIMenus.AppendMenuItem( self, copy_hash_menu, 'sha1', 'Copy the selected file\'s SHA1 hash to the clipboard.', self._CopyHashToClipboard, 'sha1' )
                    ClientGUIMenus.AppendMenuItem( self, copy_hash_menu, 'sha512', 'Copy the selected file\'s SHA512 hash to the clipboard.', self._CopyHashToClipboard, 'sha512' )
                    
                    ClientGUIMenus.AppendMenu( copy_menu, copy_hash_menu, 'hash' )
                    
                    if multiple_selected:
                        
                        copy_hash_menu = wx.Menu()
                        
                        ClientGUIMenus.AppendMenuItem( self, copy_hash_menu, 'sha256 (hydrus default)', 'Copy the selected files\' SHA256 hashes to the clipboard.', self._CopyHashesToClipboard, 'sha256' )
                        ClientGUIMenus.AppendMenuItem( self, copy_hash_menu, 'md5', 'Copy the selected files\' MD5 hashes to the clipboard.', self._CopyHashesToClipboard, 'md5' )
                        ClientGUIMenus.AppendMenuItem( self, copy_hash_menu, 'sha1', 'Copy the selected files\' SHA1 hashes to the clipboard.', self._CopyHashesToClipboard, 'sha1' )
                        ClientGUIMenus.AppendMenuItem( self, copy_hash_menu, 'sha512', 'Copy the selected files\' SHA512 hashes to the clipboard.', self._CopyHashesToClipboard, 'sha512' )
                        
                        ClientGUIMenus.AppendMenu( copy_menu, copy_hash_menu, 'hashes' )
                        
                    
                else:
                    
                    ClientGUIMenus.AppendMenuItem( self, copy_menu, 'sha256 hash', 'Copy the selected file\'s SHA256 hash to the clipboard.', self._CopyHashToClipboard, 'sha256' )
                    
                    if multiple_selected:
                        
                        ClientGUIMenus.AppendMenuItem( self, copy_menu, 'sha256 hashes', 'Copy the selected files\' SHA256 hash to the clipboard.', self._CopyHashesToClipboard, 'sha256' )
                        
                    
                
                for ipfs_service_key in self._focussed_media.GetLocationsManager().GetCurrentRemote().intersection( ipfs_service_keys ):
                    
                    name = service_keys_to_names[ ipfs_service_key ]
                    
                    ClientGUIMenus.AppendMenuItem( self, copy_menu, name + ' multihash', 'Copy the selected file\'s multihash to the clipboard.', self._CopyServiceFilenameToClipboard, ipfs_service_key )
                    
                
                if multiple_selected:
                    
                    for ipfs_service_key in disparate_current_ipfs_service_keys.union( common_current_ipfs_service_keys ):
                        
                        name = service_keys_to_names[ ipfs_service_key ]
                        
                        ClientGUIMenus.AppendMenuItem( self, copy_menu, name + ' multihashes', 'Copy the selected files\' multihashes to the clipboard.', self._CopyServiceFilenamesToClipboard, ipfs_service_key )
                        
                    
                
                if focussed_is_local:
                    
                    if self._focussed_media.GetMime() in HC.IMAGES and self._focussed_media.GetDuration() is None:
                        
                        ClientGUIMenus.AppendMenuItem( self, copy_menu, 'image', 'Copy the selected file\'s image data to the clipboard (as a bmp).', self._CopyBMPToClipboard )
                        
                    
                    ClientGUIMenus.AppendMenuItem( self, copy_menu, 'path', 'Copy the selected file\'s path to the clipboard.', self._CopyPathToClipboard )
                    
                
                if multiple_selected and selection_has_local:
                    
                    ClientGUIMenus.AppendMenuItem( self, copy_menu, 'paths', 'Copy the selected files\' paths to the clipboard.', self._CopyPathsToClipboard )
                    
                
                ClientGUIMenus.AppendMenuItem( self, copy_menu, 'known urls (prototype)', 'Copy the selected file\'s known urls to the clipboard.', self._CopyKnownURLsToClipboard )
                
                ClientGUIMenus.AppendMenu( share_menu, copy_menu, 'copy' )
                
                #
                
                export_menu  = wx.Menu()
                
                ClientGUIMenus.AppendMenuItem( self, export_menu, export_phrase, 'Export the selected files to an external folder.', self._ExportFiles )
                ClientGUIMenus.AppendMenuItem( self, export_menu, 'tags', 'Export the selected files\' tags to an external database.', self._ExportTags )
                
                share_menu.AppendMenu( CC.ID_NULL, 'export', export_menu )
                
                #
                
                if local_booru_is_running:
                    
                    ClientGUIMenus.AppendMenuItem( self, share_menu, 'on local booru', 'Share the selected files on your client\'s local booru.', self._ShareOnLocalBooru )
                    
                
                #
                
                ClientGUIMenus.AppendMenu( menu, share_menu, 'share' )
                
                #
                
                ClientGUIMenus.AppendSeparator( menu )
                
                ClientGUIMenus.AppendMenuItem( self, menu, 'refresh', 'Refresh the current search.', HydrusGlobals.client_controller.pub, 'refresh_query', self._page_key )
                
                ClientGUIMenus.AppendSeparator( menu )
                
                if len( self._sorted_media ) > 0:
                    
                    select_menu = wx.Menu()
                    
                    if len( self._selected_media ) < len( self._sorted_media ):
                        
                        ClientGUIMenus.AppendMenuItem( self, select_menu, 'all', 'Select everything.', self._Select, 'all' )
                        
                    
                    ClientGUIMenus.AppendMenuItem( self, select_menu, 'invert', 'Swap what is and is not selected.', self._Select, 'invert' )
                    
                    if media_has_archive and media_has_inbox:
                        
                        ClientGUIMenus.AppendMenuItem( self, select_menu, 'inbox', 'Select everything in the inbox.', self._Select, 'inbox' )
                        ClientGUIMenus.AppendMenuItem( self, select_menu, 'archive', 'Select everything that is archived.', self._Select, 'archive' )
                        
                    
                    if len( all_specific_file_domains ) > 1:
                        
                        selectable_file_domains = list( all_local_file_domains )
                        
                        if CC.TRASH_SERVICE_KEY in all_specific_file_domains:
                            
                            selectable_file_domains.append( CC.TRASH_SERVICE_KEY )
                            
                        
                        selectable_file_domains.extend( all_file_repos )
                        
                        for service_key in selectable_file_domains:
                            
                            name = services_manager.GetName( service_key )
                            
                            ClientGUIMenus.AppendMenuItem( self, select_menu, name, 'Select everything in ' + name + '.', self._Select, 'file_service', service_key )
                            
                        
                    
                    if len( self._selected_media ) > 0:
                        
                        ClientGUIMenus.AppendMenuItem( self, select_menu, 'none', 'Deselect everything.', self._Select, 'none' )
                        
                    
                    ClientGUIMenus.AppendMenu( menu, select_menu, 'select' )
                    
                
                ClientGUIMenus.AppendSeparator( menu )
                
                ClientGUIMenus.AppendMenuItem( self, menu, 'open selection in a new page', 'Copy your current selection into a simple new page.', self._ShowSelectionInNewQueryPage )
                
                if self._focussed_media.HasImages():
                    
                    ClientGUIMenus.AppendSeparator( menu )
                    
                    similar_menu = wx.Menu()
                    
                    ClientGUIMenus.AppendMenuItem( self, similar_menu, 'exact match', 'Search the database for files that look precisely like this one.', self._GetSimilarTo, HC.HAMMING_EXACT_MATCH )
                    ClientGUIMenus.AppendMenuItem( self, similar_menu, 'very similar', 'Search the database for files that look just like this one.', self._GetSimilarTo, HC.HAMMING_VERY_SIMILAR )
                    ClientGUIMenus.AppendMenuItem( self, similar_menu, 'similar', 'Search the database for files that look generally like this one.', self._GetSimilarTo, HC.HAMMING_SIMILAR )
                    ClientGUIMenus.AppendMenuItem( self, similar_menu, 'speculative', 'Search the database for files that probably look like this one. This is sometimes useful for symbols with sharp edges or lines.', self._GetSimilarTo, HC.HAMMING_SPECULATIVE )
                    
                    ClientGUIMenus.AppendMenu( menu, similar_menu, 'find similar files' )
                    
                
            
        
        HydrusGlobals.client_controller.PopupMenu( self, menu )
        
        event.Skip()
        
    
    def NewThumbnails( self, hashes ):
        
        affected_thumbnails = self._GetMedia( hashes )
        
        if len( affected_thumbnails ) > 0:
            
            self._RedrawMedia( affected_thumbnails )
            
        
    
    def RefreshAcceleratorTable( self ):
        
        entries = [
        ( wx.ACCEL_NORMAL, wx.WXK_HOME, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'scroll_home' ) ),
        ( wx.ACCEL_NORMAL, wx.WXK_NUMPAD_HOME, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'scroll_home' ) ),
        ( wx.ACCEL_NORMAL, wx.WXK_END, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'scroll_end' ) ),
        ( wx.ACCEL_NORMAL, wx.WXK_NUMPAD_END, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'scroll_end' ) ),
        ( wx.ACCEL_NORMAL, wx.WXK_DELETE, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'delete' ) ),
        ( wx.ACCEL_NORMAL, wx.WXK_NUMPAD_DELETE, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'delete' ) ),
        ( wx.ACCEL_NORMAL, wx.WXK_RETURN, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'fullscreen' ) ),
        ( wx.ACCEL_NORMAL, wx.WXK_NUMPAD_ENTER, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'fullscreen' ) ),
        ( wx.ACCEL_NORMAL, wx.WXK_UP, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'key_up' ) ),
        ( wx.ACCEL_NORMAL, wx.WXK_NUMPAD_UP, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'key_up' ) ),
        ( wx.ACCEL_NORMAL, wx.WXK_DOWN, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'key_down' ) ),
        ( wx.ACCEL_NORMAL, wx.WXK_NUMPAD_DOWN, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'key_down' ) ),
        ( wx.ACCEL_NORMAL, wx.WXK_LEFT, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'key_left' ) ),
        ( wx.ACCEL_NORMAL, wx.WXK_NUMPAD_LEFT, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'key_left' ) ),
        ( wx.ACCEL_NORMAL, wx.WXK_RIGHT, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'key_right' ) ),
        ( wx.ACCEL_NORMAL, wx.WXK_NUMPAD_RIGHT, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'key_right' ) ),
        ( wx.ACCEL_SHIFT, wx.WXK_HOME, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'shift_scroll_home' ) ),
        ( wx.ACCEL_SHIFT, wx.WXK_NUMPAD_HOME, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'shift_scroll_home' ) ),
        ( wx.ACCEL_SHIFT, wx.WXK_END, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'shift_scroll_end' ) ),
        ( wx.ACCEL_SHIFT, wx.WXK_NUMPAD_END, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'shift_scroll_end' ) ),
        ( wx.ACCEL_SHIFT, wx.WXK_DELETE, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'undelete' ) ),
        ( wx.ACCEL_SHIFT, wx.WXK_NUMPAD_DELETE, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'undelete' ) ),
        ( wx.ACCEL_SHIFT, wx.WXK_UP, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'key_shift_up' ) ),
        ( wx.ACCEL_SHIFT, wx.WXK_NUMPAD_UP, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'key_shift_up' ) ),
        ( wx.ACCEL_SHIFT, wx.WXK_DOWN, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'key_shift_down' ) ),
        ( wx.ACCEL_SHIFT, wx.WXK_NUMPAD_DOWN, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'key_shift_down' ) ),
        ( wx.ACCEL_SHIFT, wx.WXK_LEFT, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'key_shift_left' ) ),
        ( wx.ACCEL_SHIFT, wx.WXK_NUMPAD_LEFT, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'key_shift_left' ) ),
        ( wx.ACCEL_SHIFT, wx.WXK_RIGHT, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'key_shift_right' ) ),
        ( wx.ACCEL_SHIFT, wx.WXK_NUMPAD_RIGHT, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'key_shift_right' ) ),
        ( wx.ACCEL_CTRL, ord( 'A' ), ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'select', 'all' ) ),
        ( wx.ACCEL_CTRL, ord( 'c' ), ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'copy_files' )  ),
        ( wx.ACCEL_CTRL, wx.WXK_SPACE, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'ctrl-space' )  )
        ]
        
        if HC.PLATFORM_OSX:
            
            entries.append( ( wx.ACCEL_NORMAL, wx.WXK_BACK, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'delete' ) ) )
            entries.append( ( wx.ACCEL_SHIFT, wx.WXK_BACK, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'undelete' ) ) )
            
        
        for ( modifier, key_dict ) in HC.options[ 'shortcuts' ].items(): entries.extend( [ ( modifier, key, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( action ) ) for ( key, action ) in key_dict.items() if action not in ( 'previous', 'next' ) 	] )
        
        self.SetAcceleratorTable( wx.AcceleratorTable( entries ) )
        
    
    def SetFocussedMedia( self, page_key, media ):
        
        MediaPanel.SetFocussedMedia( self, page_key, media )
        
        if page_key == self._page_key:
            
            if media is None: self._SetFocussedMedia( None )
            else:
                
                try:
                    
                    my_media = self._GetMedia( media.GetHashes() )[0]
                    
                    self._HitMedia( my_media, False, False )
                    
                    self._ScrollToMedia( self._focussed_media )
                    
                except: pass
                
            
        
    
    def Sort( self, page_key, sort_by = None ):
        
        MediaPanel.Sort( self, page_key, sort_by )
        
        self._DirtyAllPages()
        
    
    def ThumbnailsResized( self ):
        
        ( thumbnail_span_width, thumbnail_span_height ) = self._GetThumbnailSpanDimensions()
        
        self._ReinitialisePageCacheIfNeeded()
        
        self._RecalculateVirtualSize()
        
        self.SetScrollRate( 0, thumbnail_span_height )
        
        self._DirtyAllPages()
        
    
    def TIMEREventAnimation( self, event ):
        
        try:
            
            started = HydrusData.GetNowPrecise()
            
            ( thumbnail_span_width, thumbnail_span_height ) = self._GetThumbnailSpanDimensions()
            
            hashes = list( self._thumbnails_being_faded_in.keys() )
            
            random.shuffle( hashes )
            
            dcs = {}
            
            for hash in hashes:
                
                ( original_bmp, alpha_bmp, thumbnail_index, thumbnail, num_frames_rendered ) = self._thumbnails_being_faded_in[ hash ]
                
                num_frames_rendered += 1
                
                page_index = self._GetPageIndexFromThumbnailIndex( thumbnail_index )
                
                delete_entry = False
                
                try: expected_thumbnail = self._sorted_media[ thumbnail_index ]
                except: expected_thumbnail = None
                
                if expected_thumbnail != thumbnail:
                    
                    delete_entry = True
                    
                elif page_index not in self._clean_canvas_pages:
                    
                    delete_entry = True
                    
                else:
                    
                    if num_frames_rendered >= 9:
                        
                        bmp_to_use = original_bmp
                        
                        delete_entry = True
                        
                    else:
                        
                        bmp_to_use = alpha_bmp
                        
                        self._thumbnails_being_faded_in[ hash ] = ( original_bmp, alpha_bmp, thumbnail_index, thumbnail, num_frames_rendered )
                        
                    
                    thumbnail_col = thumbnail_index % self._num_columns
                    
                    thumbnail_row = thumbnail_index / self._num_columns
                    
                    x = thumbnail_col * thumbnail_span_width + CC.THUMBNAIL_MARGIN
                    
                    y = ( thumbnail_row - ( page_index * self._num_rows_per_canvas_page ) ) * thumbnail_span_height + CC.THUMBNAIL_MARGIN
                    
                    if page_index not in dcs:
                        
                        canvas_bmp = self._clean_canvas_pages[ page_index ]
                        
                        dc = wx.MemoryDC( canvas_bmp )
                        
                        dcs[ page_index ] = dc
                        
                    
                    dc = dcs[ page_index ]
                    
                    dc.DrawBitmap( bmp_to_use, x, y, True )
                    
                
                if delete_entry:
                    
                    del self._thumbnails_being_faded_in[ hash ]
                    
                    original_bmp.Destroy()
                    alpha_bmp.Destroy()
                    
                
                if HydrusData.TimeHasPassedPrecise( started + 0.016 ):
                    
                    break
                    
                
            
            if len( self._thumbnails_being_faded_in ) > 0:
                
                finished = HydrusData.GetNowPrecise()
                
                time_this_took_in_ms = ( finished - started ) * 1000
                
                ms_to_wait = int( round( 16.7 - time_this_took_in_ms ) )
                
                ms_to_wait = max( 1, ms_to_wait )
                
                self._timer_animation.Start( ms_to_wait, wx.TIMER_ONE_SHOT )
                
            
            self.Refresh()
            
        except wx.PyDeadObjectError:
            
            self._timer_animation.Stop()
            
        except:
            
            self._timer_animation.Stop()
            
            raise
            
        
    
    def WaterfallThumbnail( self, page_key, thumbnail ):
        
        if self._page_key == page_key:
            
            self._FadeThumbnail( thumbnail )
            
        
    
class Selectable( object ):
    
    def __init__( self ): self._selected = False
    
    def Deselect( self ): self._selected = False
    
    def IsSelected( self ): return self._selected
    
    def Select( self ): self._selected = True
    
class Thumbnail( Selectable ):
    
    def __init__( self, file_service_key ):
        
        Selectable.__init__( self )
        
        self._dump_status = CC.DUMPER_NOT_DUMPED
        self._file_service_key = file_service_key
        
    
    def Dumped( self, dump_status ): self._dump_status = dump_status
    
    def GetBmp( self ):
        
        inbox = self.HasInbox()
        
        local = self.GetLocationsManager().IsLocal()
        
        thumbnail_hydrus_bmp = HydrusGlobals.client_controller.GetCache( 'thumbnail' ).GetThumbnail( self )
        
        ( width, height ) = ClientData.AddPaddingToDimensions( HC.options[ 'thumbnail_dimensions' ], CC.THUMBNAIL_BORDER * 2 )
        
        bmp = wx.EmptyBitmap( width, height, 24 )
        
        dc = wx.MemoryDC( bmp )
        
        if not local:
            
            if self._selected: rgb = HC.options[ 'gui_colours' ][ 'thumb_background_remote_selected' ]
            else: rgb = HC.options[ 'gui_colours' ][ 'thumb_background_remote' ]
            
        else:
            
            if self._selected: rgb = HC.options[ 'gui_colours' ][ 'thumb_background_selected' ]
            else: rgb = HC.options[ 'gui_colours' ][ 'thumb_background' ]
            
        
        dc.SetBackground( wx.Brush( wx.Colour( *rgb ) ) )
        
        dc.Clear()
        
        ( thumb_width, thumb_height ) = thumbnail_hydrus_bmp.GetSize()
        
        x_offset = ( width - thumb_width ) / 2
        
        y_offset = ( height - thumb_height ) / 2
        
        wx_bmp = thumbnail_hydrus_bmp.GetWxBitmap()
        
        dc.DrawBitmap( wx_bmp, x_offset, y_offset )
        
        wx_bmp.Destroy()
        
        namespaces = self.GetTagsManager().GetCombinedNamespaces( ( 'creator', 'series', 'title', 'volume', 'chapter', 'page' ) )
        
        creators = namespaces[ 'creator' ]
        series = namespaces[ 'series' ]
        titles = namespaces[ 'title' ]
        volumes = namespaces[ 'volume' ]
        chapters = namespaces[ 'chapter' ]
        pages = namespaces[ 'page' ]
        
        new_options = HydrusGlobals.client_controller.GetNewOptions()
        
        if new_options.GetBoolean( 'show_thumbnail_page' ):
            
            collections_string = ''
            
            if len( volumes ) > 0:
                
                if len( volumes ) == 1:
                    
                    ( volume, ) = volumes
                    
                    collections_string = 'v' + str( volume )
                    
                else:
                    
                    volumes_sorted = HydrusTags.SortNumericTags( volumes )
                    
                    collections_string_append = 'v' + str( volumes_sorted[0] ) + '-' + str( volumes_sorted[-1] )
                    
                
            
            if len( chapters ) > 0:
                
                if len( chapters ) == 1:
                    
                    ( chapter, ) = chapters
                    
                    collections_string_append = 'c' + str( chapter )
                    
                else:
                    
                    chapters_sorted = HydrusTags.SortNumericTags( chapters )
                    
                    collections_string_append = 'c' + str( chapters_sorted[0] ) + '-' + str( chapters_sorted[-1] )
                    
                
                if len( collections_string ) > 0: collections_string += '-' + collections_string_append
                else: collections_string = collections_string_append
                
            
            if len( pages ) > 0:
                
                if len( pages ) == 1:
                    
                    ( page, ) = pages
                    
                    collections_string_append = 'p' + str( page )
                    
                else:
                    
                    pages_sorted = HydrusTags.SortNumericTags( pages )
                    
                    collections_string_append = 'p' + str( pages_sorted[0] ) + '-' + str( pages_sorted[-1] )
                    
                
                if len( collections_string ) > 0: collections_string += '-' + collections_string_append
                else: collections_string = collections_string_append
                
            
            if len( collections_string ) > 0:
                
                dc.SetFont( wx.SystemSettings.GetFont( wx.SYS_DEFAULT_GUI_FONT ) )
                
                ( text_x, text_y ) = dc.GetTextExtent( collections_string )
                
                top_left_x = width - text_x - CC.THUMBNAIL_BORDER
                top_left_y = height - text_y - CC.THUMBNAIL_BORDER
                
                dc.SetBrush( wx.Brush( CC.COLOUR_UNSELECTED ) )
                
                dc.SetTextForeground( CC.COLOUR_SELECTED_DARK )
                
                dc.SetPen( wx.TRANSPARENT_PEN )
                
                dc.DrawRectangle( top_left_x - 1, top_left_y - 1, text_x + 2, text_y + 2 )
                
                dc.DrawText( collections_string, top_left_x, top_left_y )
                
            
        
        if new_options.GetBoolean( 'show_thumbnail_title_banner' ):
            
            siblings_manager = HydrusGlobals.client_controller.GetManager( 'tag_siblings' )
            
            upper_info_string = ''
            
            if len( creators ) > 0:
                
                upper_info_string = ', '.join( creators )
                
                if len( series ) > 0 or len( titles ) > 0: upper_info_string += ' - '
                
            
            if len( series ) > 0:
                
                upper_info_string += ', '.join( series )
                
            elif len( titles ) > 0:
                
                upper_info_string += ', '.join( titles )
                
            
            if len( upper_info_string ) > 0:
                
                dc.SetFont( wx.SystemSettings.GetFont( wx.SYS_DEFAULT_GUI_FONT ) )
                
                ( text_x, text_y ) = dc.GetTextExtent( upper_info_string )
                
                top_left_x = int( ( width - text_x ) / 2 )
                top_left_y = CC.THUMBNAIL_BORDER
                
                dc.SetBrush( wx.Brush( CC.COLOUR_UNSELECTED ) )
                
                dc.SetTextForeground( CC.COLOUR_SELECTED_DARK )
                
                dc.SetPen( wx.TRANSPARENT_PEN )
                
                dc.DrawRectangle( 0, top_left_y - 1, width, text_y + 2 )
                
                dc.DrawText( upper_info_string, top_left_x, top_left_y )
                
            
        
        dc.SetBrush( wx.TRANSPARENT_BRUSH )
        
        if not local:
            
            if self._selected: rgb = HC.options[ 'gui_colours' ][ 'thumb_border_remote_selected' ]
            else: rgb = HC.options[ 'gui_colours' ][ 'thumb_border_remote' ]
            
        else:
            
            if self._selected: rgb = HC.options[ 'gui_colours' ][ 'thumb_border_selected' ]
            else: rgb = HC.options[ 'gui_colours' ][ 'thumb_border' ]
            
        
        dc.SetPen( wx.Pen( wx.Colour( *rgb ), style=wx.SOLID ) )
        
        dc.DrawRectangle( 0, 0, width, height )
        
        locations_manager = self.GetLocationsManager()
        
        icons_to_draw = []
        
        if locations_manager.IsDownloading():
            
            icons_to_draw.append( CC.GlobalBMPs.downloading )
            
        
        if CC.TRASH_SERVICE_KEY in locations_manager.GetCurrent():
            
            icons_to_draw.append( CC.GlobalBMPs.trash )
            
        
        if inbox:
            
            icons_to_draw.append( CC.GlobalBMPs.inbox )
            
        
        if len( icons_to_draw ) > 0:
            
            icon_x = 0
            
            for icon in icons_to_draw:
                
                dc.DrawBitmap( icon, width + icon_x - 18, 0 )
                
                icon_x -= 18
                
            
        
        if self._dump_status == CC.DUMPER_DUMPED_OK: dc.DrawBitmap( CC.GlobalBMPs.dump_ok, width - 18, 18 )
        elif self._dump_status == CC.DUMPER_RECOVERABLE_ERROR: dc.DrawBitmap( CC.GlobalBMPs.dump_recoverable, width - 18, 18 )
        elif self._dump_status == CC.DUMPER_UNRECOVERABLE_ERROR: dc.DrawBitmap( CC.GlobalBMPs.dump_fail, width - 18, 18 )
        
        if self.IsCollection():
            
            dc.DrawBitmap( CC.GlobalBMPs.collection, 1, height - 17 )
            
            num_files_str = str( len( self._hashes ) )
            
            dc.SetFont( wx.SystemSettings.GetFont( wx.SYS_DEFAULT_GUI_FONT ) )
            
            ( text_x, text_y ) = dc.GetTextExtent( num_files_str )
            
            dc.SetBrush( wx.Brush( CC.COLOUR_UNSELECTED ) )
            
            dc.SetTextForeground( CC.COLOUR_SELECTED_DARK )
            
            dc.SetPen( wx.TRANSPARENT_PEN )
            
            dc.DrawRectangle( 17, height - text_y - 3, text_x + 2, text_y + 2 )
            
            dc.DrawText( num_files_str, 18, height - text_y - 2 )
            
        
        # repo icons
        
        services_manager = HydrusGlobals.client_controller.GetServicesManager()
        
        repo_icon_x = 0
        
        current = locations_manager.GetCurrentRemote()
        pending = locations_manager.GetPendingRemote()
        petitioned = locations_manager.GetPetitionedRemote()
        
        current_to_display = current.difference( petitioned )
        
        #
        
        service_types = [ services_manager.GetService( service_key ).GetServiceType() for service_key in current_to_display ]
        
        if HC.FILE_REPOSITORY in service_types:
            
            dc.DrawBitmap( CC.GlobalBMPs.file_repository, repo_icon_x, 0 )
            
            repo_icon_x += 20
            
        
        if HC.IPFS in service_types:
            
            dc.DrawBitmap( CC.GlobalBMPs.ipfs, repo_icon_x, 0 )
            
            repo_icon_x += 20
            
        
        #
        
        service_types = [ services_manager.GetService( service_key ).GetServiceType() for service_key in pending ]
        
        if HC.FILE_REPOSITORY in service_types:
            
            dc.DrawBitmap( CC.GlobalBMPs.file_repository_pending, repo_icon_x, 0 )
            
            repo_icon_x += 20
            
        
        if HC.IPFS in service_types:
            
            dc.DrawBitmap( CC.GlobalBMPs.ipfs_pending, repo_icon_x, 0 )
            
            repo_icon_x += 20
            
        
        #
        
        service_types = [ services_manager.GetService( service_key ).GetServiceType() for service_key in petitioned ]
        
        if HC.FILE_REPOSITORY in service_types:
            
            dc.DrawBitmap( CC.GlobalBMPs.file_repository_petitioned, repo_icon_x, 0 )
            
            repo_icon_x += 20
            
        
        if HC.IPFS in service_types:
            
            dc.DrawBitmap( CC.GlobalBMPs.ipfs_petitioned, repo_icon_x, 0 )
            
            repo_icon_x += 20
            
        
        return bmp
        
    
class ThumbnailMediaCollection( Thumbnail, ClientMedia.MediaCollection ):
    
    def __init__( self, file_service_key, media_results ):
        
        ClientMedia.MediaCollection.__init__( self, file_service_key, media_results )
        Thumbnail.__init__( self, file_service_key )
        
    
class ThumbnailMediaSingleton( Thumbnail, ClientMedia.MediaSingleton ):
    
    def __init__( self, file_service_key, media_result ):
        
        ClientMedia.MediaSingleton.__init__( self, media_result )
        Thumbnail.__init__( self, file_service_key )
        
    
