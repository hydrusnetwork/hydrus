import HydrusConstants as HC
import ClientConstants as CC
import ClientGUICommon
import ClientGUIDialogs
import ClientGUIDialogsManage
import ClientGUICanvas
import ClientGUIMixins
import collections
import itertools
import os
import random
import threading
import time
import traceback
import wx
import yaml

# Option Enums

ID_TIMER_ANIMATION = wx.NewId()

# Sizer Flags

FLAGS_NONE = wx.SizerFlags( 0 )

FLAGS_SMALL_INDENT = wx.SizerFlags( 0 ).Border( wx.ALL, 2 )

FLAGS_EXPAND_PERPENDICULAR = wx.SizerFlags( 0 ).Border( wx.ALL, 2 ).Expand()
FLAGS_EXPAND_BOTH_WAYS = wx.SizerFlags( 2 ).Border( wx.ALL, 2 ).Expand()
FLAGS_EXPAND_DEPTH_ONLY = wx.SizerFlags( 2 ).Border( wx.ALL, 2 ).Align( wx.ALIGN_CENTER_VERTICAL )

FLAGS_EXPAND_SIZER_PERPENDICULAR = wx.SizerFlags( 0 ).Expand()
FLAGS_EXPAND_SIZER_BOTH_WAYS = wx.SizerFlags( 2 ).Expand()
FLAGS_EXPAND_SIZER_DEPTH_ONLY = wx.SizerFlags( 2 ).Align( wx.ALIGN_CENTER_VERTICAL )

FLAGS_BUTTON_SIZERS = wx.SizerFlags( 0 ).Align( wx.ALIGN_RIGHT )
FLAGS_LONE_BUTTON = wx.SizerFlags( 0 ).Border( wx.ALL, 2 ).Align( wx.ALIGN_RIGHT )

FLAGS_MIXED = wx.SizerFlags( 0 ).Border( wx.ALL, 2 ).Align( wx.ALIGN_CENTER_VERTICAL )

def AddFileServiceIdentifiersToMenu( menu, file_service_identifiers, phrase, action ):
    
    if len( file_service_identifiers ) == 1:
        
        ( s_i, ) = file_service_identifiers
        
        if action == CC.ID_NULL: id = CC.ID_NULL
        else: id = CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( action, s_i )
        
        menu.Append( id, phrase + ' ' + s_i.GetName() )
        
    else:
        
        submenu = wx.Menu()
        
        for s_i in file_service_identifiers: 
            
            if action == CC.ID_NULL: id = CC.ID_NULL
            else: id = CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( action, s_i )
            
            submenu.Append( id, s_i.GetName() )
            
        
        menu.AppendMenu( CC.ID_NULL, phrase + u'\u2026', submenu )
        
    
class MediaPanel( ClientGUIMixins.ListeningMediaList, wx.ScrolledWindow ):
    
    def __init__( self, parent, page_key, file_service_identifier, media_results ):
        
        wx.ScrolledWindow.__init__( self, parent, size = ( 0, 0 ), style = wx.BORDER_SUNKEN )
        ClientGUIMixins.ListeningMediaList.__init__( self, file_service_identifier, media_results )
        
        self.SetBackgroundColour( wx.WHITE )
        
        self.SetDoubleBuffered( True )
        
        self.SetScrollRate( 0, 50 )
        
        self._page_key = page_key
        
        self._focussed_media = None
        self._shift_focussed_media = None
        
        self._selected_media = set()
        
        HC.pubsub.sub( self, 'AddMediaResults', 'add_media_results' )
        HC.pubsub.sub( self, 'SetFocussedMedia', 'set_focus' )
        HC.pubsub.sub( self, 'PageHidden', 'page_hidden' )
        HC.pubsub.sub( self, 'PageShown', 'page_shown' )
        HC.pubsub.sub( self, 'Collect', 'collect_media' )
        HC.pubsub.sub( self, 'Sort', 'sort_media' )
        HC.pubsub.sub( self, 'FileDumped', 'file_dumped' )
        
        self._PublishSelectionChange()
        
    
    def _Archive( self ):
        
        hashes = self._GetSelectedHashes( CC.DISCRIMINANT_INBOX )
        
        if len( hashes ) > 0:
            
            if len( hashes ) > 1:
                
                message = 'Archive ' + HC.ConvertIntToPrettyString( len( hashes ) ) + ' files?'
                
                with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
                    
                    if dlg.ShowModal() != wx.ID_YES: return
                    
                
            
            HC.app.Write( 'content_updates', { HC.LOCAL_FILE_SERVICE_IDENTIFIER : [ HC.ContentUpdate( HC.CONTENT_DATA_TYPE_FILES, HC.CONTENT_UPDATE_ARCHIVE, hashes ) ] } )
            
        
    
    def _CopyHashToClipboard( self ):
        
        if wx.TheClipboard.Open():
            
            data = wx.TextDataObject( self._focussed_media.GetDisplayMedia().GetHash().encode( 'hex' ) )
            
            wx.TheClipboard.SetData( data )
            
            wx.TheClipboard.Close()
            
        else: wx.MessageBox( 'I could not get permission to access the clipboard.' )
        
    
    def _CopyHashesToClipboard( self ):
        
        if wx.TheClipboard.Open():
            
            data = wx.TextDataObject( os.linesep.join( [ hash.encode( 'hex' ) for hash in self._GetSelectedHashes() ] ) )
            
            wx.TheClipboard.SetData( data )
            
            wx.TheClipboard.Close()
            
        else: wx.MessageBox( 'I could not get permission to access the clipboard.' )
        
    
    def _CopyLocalUrlToClipboard( self ):
        
        if wx.TheClipboard.Open():
            
            data = wx.TextDataObject( 'http://127.0.0.1:' + str( HC.options[ 'local_port' ] ) + '/file?hash=' + self._focussed_media.GetDisplayMedia().GetHash().encode( 'hex' ) )
            
            wx.TheClipboard.SetData( data )
            
            wx.TheClipboard.Close()
            
        else: wx.MessageBox( 'I could not get permission to access the clipboard.' )
        
    
    def _CopyPathToClipboard( self ):
        
        if wx.TheClipboard.Open():
            
            display_media = self._focussed_media.GetDisplayMedia()
            
            data = wx.TextDataObject( CC.GetFilePath( display_media.GetHash(), display_media.GetMime() ) )
            
            wx.TheClipboard.SetData( data )
            
            wx.TheClipboard.Close()
            
        else: wx.MessageBox( 'I could not get permission to access the clipboard.' )
        
    
    def _CustomFilter( self ):
        
        with ClientGUIDialogs.DialogSetupCustomFilterActions( self ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                actions = dlg.GetActions()
                
                media_results = self.GenerateMediaResults( discriminant = CC.DISCRIMINANT_LOCAL, selected_media = set( self._selected_media ) )
                
                if len( media_results ) > 0:
                    
                    try: ClientGUICanvas.CanvasFullscreenMediaListCustomFilter( self.GetTopLevelParent(), self._page_key, self._file_service_identifier, media_results, actions )
                    except: wx.MessageBox( traceback.format_exc() )
                    
                
            
        
    
    def _Delete( self, file_service_identifier ):
        
        if file_service_identifier.GetType() == HC.LOCAL_FILE:
            
            hashes = self._GetSelectedHashes( CC.DISCRIMINANT_LOCAL )
            
            num_to_delete = len( hashes )
            
            if num_to_delete:
                
                if num_to_delete == 1: message = 'Are you sure you want to delete this file?'
                else: message = 'Are you sure you want to delete these ' + HC.ConvertIntToPrettyString( num_to_delete ) + ' files?'
                
                with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_YES:
                        
                        self.SetFocussedMedia( self._page_key, None )
                        
                        try: HC.app.Write( 'content_updates', { file_service_identifier : [ HC.ContentUpdate( HC.CONTENT_DATA_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, hashes ) ] } )
                        except: wx.MessageBox( traceback.format_exc() )
                        
                    
                
            
        else:
            
            hashes = self._GetSelectedHashes()
            
            content_update = HC.ContentUpdate( HC.CONTENT_DATA_TYPE_FILES, HC.CONTENT_UPDATE_PETITION, ( hashes, 'admin' ) )
            
            service_identifiers_to_content_updates = { file_service_identifier : ( content_update, ) }
            
            HC.app.Write( 'content_updates', service_identifiers_to_content_updates )
            
        
    
    def _DeselectSelect( self, media_to_deselect, media_to_select ):
        
        if len( media_to_deselect ) > 0:
            
            for m in media_to_deselect: m.Deselect()
            
            self._RedrawMediaIfLoaded( media_to_deselect )
            
            self._selected_media.difference_update( media_to_deselect )
            
        
        if len( media_to_select ) > 0:
            
            for m in media_to_select: m.Select()
            
            self._RedrawMediaIfLoaded( media_to_select )
            
            self._selected_media.update( media_to_select )
            
        
        self._PublishSelectionChange()
        
    
    def _FullScreen( self, first_media = None ):
        
        media_results = self.GenerateMediaResults( discriminant = CC.DISCRIMINANT_LOCAL )
        
        if len( media_results ) > 0:
            
            if first_media is None and self._focussed_media is not None: first_media = self._focussed_media
            
            if first_media is not None and first_media.GetFileServiceIdentifiersCDPP().HasLocal(): first_hash = first_media.GetDisplayMedia().GetHash()
            else: first_hash = None
            
            ClientGUICanvas.CanvasFullscreenMediaListBrowser( self.GetTopLevelParent(), self._page_key, self._file_service_identifier, media_results, first_hash )
            
        
    
    def _Filter( self ):
        
        media_results = self.GenerateMediaResults( discriminant = CC.DISCRIMINANT_LOCAL, selected_media = set( self._selected_media ) )
        
        if len( media_results ) > 0:
            
            try: ClientGUICanvas.CanvasFullscreenMediaListFilterInbox( self.GetTopLevelParent(), self._page_key, self._file_service_identifier, media_results )
            except: wx.MessageBox( traceback.format_exc() )
            
        
    
    def _GetNumSelected( self ): return sum( [ media.GetNumFiles() for media in self._selected_media ] )
    
    def _GetPrettyStatus( self ):
        
        num_files = sum( [ media.GetNumFiles() for media in self._sorted_media ] )
        
        num_selected = self._GetNumSelected()
        
        pretty_total_size = self._GetPrettyTotalSelectedSize()
        
        if num_selected == 0:
            
            if num_files == 1: s = '1 file'
            else: s = HC.ConvertIntToPrettyString( num_files ) + ' files'
            
        elif num_selected == 1: s = '1 of ' + HC.ConvertIntToPrettyString( num_files ) + ' files selected, ' + pretty_total_size
        else: s = HC.ConvertIntToPrettyString( num_selected ) + ' of ' + HC.ConvertIntToPrettyString( num_files ) + ' files selected, totalling ' + pretty_total_size
        
        return s
        
    
    def _GetPrettyTotalSelectedSize( self ):
        
        total_size = sum( [ media.GetSize() for media in self._selected_media ] )
        
        unknown_size = False in ( media.IsSizeDefinite() for media in self._selected_media )
        
        if total_size == 0:
            
            if unknown_size: return 'unknown size'
            else: return HC.ConvertIntToBytes( 0 )
            
        else:
            
            if unknown_size: return HC.ConvertIntToBytes( total_size ) + ' + some unknown size'
            else: return HC.ConvertIntToBytes( total_size )
            
        
    
    def _GetSelectedHashes( self, discriminant = None, not_uploaded_to = None ):
        
        result = set()
        
        for media in self._selected_media: result.update( media.GetHashes( discriminant, not_uploaded_to ) )
        
        return result
        
    
    def _GetSimilarTo( self ):
        
        if self._focussed_media is not None:
            
            hash = self._focussed_media.GetDisplayMedia().GetHash()
            
            HC.pubsub.pub( 'new_similar_to', self._file_service_identifier, hash )
            
        
    
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
                    
                    if self._focussed_media == media: self._SetFocussedMedia( None )
                    
                else:
                    
                    self._DeselectSelect( (), ( media, ) )
                    
                    if self._focussed_media is None: self._SetFocussedMedia( media )
                    
                
                self._shift_focussed_media = None
                
            elif shift and self._focussed_media is not None:
                
                if self._shift_focussed_media is None: self._shift_focussed_media = self._focussed_media
                
                start_index = self._sorted_media.index( self._shift_focussed_media )
                
                end_index = self._sorted_media.index( media )
                
                if start_index < end_index: media_i_want_selected_at_the_end = set( self._sorted_media[ start_index : end_index + 1 ] )
                else: media_i_want_selected_at_the_end = set( self._sorted_media[ end_index : start_index + 1 ] )
                
                self._DeselectSelect( self._selected_media - media_i_want_selected_at_the_end, media_i_want_selected_at_the_end - self._selected_media )
                
                self._SetFocussedMedia( media )
                
            else:
                
                if not media.IsSelected(): self._DeselectSelect( self._selected_media, ( media, ) )
                else: self._PublishSelectionChange()
                
                self._SetFocussedMedia( media )
                self._shift_focussed_media = None
                
            
        
    
    def _Inbox( self ):
        
        hashes = self._GetSelectedHashes( CC.DISCRIMINANT_ARCHIVE )
        
        if len( hashes ) > 0:
            
            if len( hashes ) > 1:
                
                message = 'Send ' + HC.ConvertIntToPrettyString( len( hashes ) ) + ' files to inbox?'
                
                with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
                    
                    if dlg.ShowModal() != wx.ID_YES: return
                    
                
            
            HC.app.Write( 'content_updates', { HC.LOCAL_FILE_SERVICE_IDENTIFIER : [ HC.ContentUpdate( HC.CONTENT_DATA_TYPE_FILES, HC.CONTENT_UPDATE_INBOX, hashes ) ] } )
            
        
    
    def _ManageRatings( self ):
        
        if len( self._selected_media ) > 0:
            
            service_identifiers = HC.app.Read( 'service_identifiers', HC.RATINGS_SERVICES )
            
            if len( service_identifiers ) > 0:
                
                try:
                    
                    flat_media = []
                    
                    for media in self._selected_media:
                        
                        if media.IsCollection(): flat_media.extend( media.GetFlatMedia() )
                        else: flat_media.append( media )
                        
                    
                    with ClientGUIDialogsManage.DialogManageRatings( None, flat_media ) as dlg: dlg.ShowModal()
                    
                    self.SetFocus()
                    
                except: wx.MessageBox( traceback.format_exc() )
                
            
        
    
    def _ManageTags( self ):
        
        if len( self._selected_media ) > 0:
            
            try:
                
                with ClientGUIDialogsManage.DialogManageTags( None, self._file_service_identifier, self._selected_media ) as dlg: dlg.ShowModal()
                
                self.SetFocus()
                
            except: wx.MessageBox( traceback.format_exc() )
            
        
    
    def _ModifyUploaders( self, file_service_identifier ):
        
        hashes = self._GetSelectedHashes()
        
        if hashes is not None and len( hashes ) > 0:   
            
            with ClientGUIDialogs.DialogModifyAccounts( self, file_service_identifier, [ HC.AccountIdentifier( hash = hash ) for hash in hashes ] ) as dlg: dlg.ShowModal()
            
            self.SetFocus()
            
        
    
    def _NewThreadDumper( self ):
        
        # can't do normal _getselectedhashes because we want to keep order!
        
        args = [ media.GetHashes( CC.DISCRIMINANT_LOCAL ) for media in self._selected_media ]
        
        hashes = [ h for h in itertools.chain( *args ) ]
        
        if len( hashes ) > 0: HC.pubsub.pub( 'new_thread_dumper', hashes )
        
    
    def _PetitionFiles( self, file_service_identifier ):
        
        hashes = self._GetSelectedHashes()
        
        if hashes is not None and len( hashes ) > 0:
            
            if len( hashes ) == 1: message = 'Enter a reason for this file to be removed from ' + file_service_identifier.GetName() + '.'
            else: message = 'Enter a reason for these ' + HC.ConvertIntToPrettyString( len( hashes ) ) + ' files to be removed from ' + file_service_identifier.GetName() + '.'
            
            with wx.TextEntryDialog( self, message ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    content_update = HC.ContentUpdate( HC.CONTENT_DATA_TYPE_FILES, HC.CONTENT_UPDATE_PETITION, ( hashes, dlg.GetValue() ) )
                    
                    service_identifiers_to_content_updates = { file_service_identifier : ( content_update, ) }
                    
                    HC.app.Write( 'content_updates', service_identifiers_to_content_updates )
                    
                
            
            self.SetFocus()
            
        
    
    def _PublishSelectionChange( self, force_reload = False ):
        
        if len( self._selected_media ) == 0: tags_media = self._sorted_media
        else: tags_media = self._selected_media
        
        HC.pubsub.pub( 'new_tags_selection', self._page_key, tags_media, force_reload = force_reload )
        HC.pubsub.pub( 'new_page_status', self._page_key, self._GetPrettyStatus() )
        
    
    def _RatingsFilter( self, service_identifier ):
        
        if service_identifier is None:
            
            service_identifier = ClientGUIDialogs.SelectServiceIdentifier( service_types = ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ) )
            
            if service_identifier is None: return
            
        
        media_results = self.GenerateMediaResults( discriminant = CC.DISCRIMINANT_LOCAL, selected_media = set( self._selected_media ), unrated = service_identifier )
        
        if len( media_results ) > 0:
            
            try:
                
                if service_identifier.GetType() == HC.LOCAL_RATING_LIKE: ClientGUICanvas.RatingsFilterFrameLike( self.GetTopLevelParent(), self._page_key, service_identifier, media_results )
                elif service_identifier.GetType() == HC.LOCAL_RATING_NUMERICAL: ClientGUICanvas.RatingsFilterFrameNumerical( self.GetTopLevelParent(), self._page_key, service_identifier, media_results )
                
            except: wx.MessageBox( traceback.format_exc() )
            
        
    
    def _RedrawCanvas( self ): pass
    
    def _RedrawMediaIfLoaded( self, media ): pass
    
    def _RefitCanvas( self ): pass
    
    def _Remove( self ):
        
        singletons = [ media for media in self._selected_media if not media.IsCollection() ]
        
        collections = [ media for media in self._selected_media if media.IsCollection() ]
        
        self._RemoveMedia( singletons, collections )
        
    
    def _RemoveMedia( self, singleton_media, collected_media ):
        
        ClientGUIMixins.ListeningMediaList._RemoveMedia( self, singleton_media, collected_media )
        
        self._selected_media.difference_update( singleton_media )
        self._selected_media.difference_update( collected_media )
        
        if self._focussed_media not in self._selected_media: self._SetFocussedMedia( None )
        
        self._shift_focussed_media = None
        
        self._RefitCanvas()
        
        self._RedrawCanvas()
        
        self._PublishSelectionChange()
        
        HC.pubsub.pub( 'sorted_media_pulse', self._page_key, self._sorted_media )
        
    
    def _RescindPetitionFiles( self, file_service_identifier ):
        
        hashes = self._GetSelectedHashes()
        
        if hashes is not None and len( hashes ) > 0:   
            
            HC.app.Write( 'content_updates', { file_service_identifier : [ HC.ContentUpdate( HC.CONTENT_DATA_TYPE_FILES, HC.CONTENT_UPDATE_RESCIND_PETITION, hashes ) ] } )
            
        
    
    def _RescindUploadFiles( self, file_service_identifier ):
        
        hashes = self._GetSelectedHashes()
        
        if hashes is not None and len( hashes ) > 0:   
            
            HC.app.Write( 'content_updates', { file_service_identifier : [ HC.ContentUpdate( HC.CONTENT_DATA_TYPE_FILES, HC.CONTENT_UPDATE_RESCIND_PENDING, hashes ) ] } )
            
        
    
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
            
        
    
    def _Select( self, select_type ):
        
        self._RedrawCanvas()
        
        if select_type == 'all': self._DeselectSelect( [], self._sorted_media )
        else:
            
            if select_type == 'none': ( media_to_deselect, media_to_select ) = ( self._selected_media, [] )
            else:
                
                inbox_media = { m for m in self._sorted_media if m.HasInbox() }
                archive_media = { m for m in self._sorted_media if m not in inbox_media }
                
                if select_type == 'inbox':
                    
                    media_to_deselect = [ m for m in archive_media if m in self._selected_media ]
                    media_to_select = [ m for m in inbox_media if m not in self._selected_media ]
                    
                elif select_type == 'archive':
                    
                    media_to_deselect = [ m for m in inbox_media if m in self._selected_media ]
                    media_to_select = [ m for m in archive_media if m not in self._selected_media ]
                    
                
            
            if self._focussed_media in media_to_deselect: self._SetFocussedMedia( None )
            
            self._DeselectSelect( media_to_deselect, media_to_select )
            
            self._shift_focussed_media = None
            
        
    
    def _SetFocussedMedia( self, media ):
        
        self._focussed_media = media
        
        HC.pubsub.pub( 'focus_changed', self._page_key, media )
        
    
    def _ShowSelectionInNewQueryPage( self ):
        
        hashes = self._GetSelectedHashes()
        
        if hashes is not None and len( hashes ) > 0:
            
            media_results = HC.app.Read( 'media_results', self._file_service_identifier, hashes )
            
            hashes_to_media_results = { media_result.GetHash() : media_result for media_result in media_results }
            
            sorted_flat_media = self.GetFlatMedia()
            
            sorted_media_results = [ hashes_to_media_results[ media.GetHash() ] for media in sorted_flat_media if media.GetHash() in hashes_to_media_results ]
            
            HC.pubsub.pub( 'new_page_query', self._file_service_identifier, initial_media_results = sorted_media_results )
            
        
    
    def _UploadFiles( self, file_service_identifier ):
        
        hashes = self._GetSelectedHashes( not_uploaded_to = file_service_identifier )
        
        if hashes is not None and len( hashes ) > 0:   
            
            HC.app.Write( 'content_updates', { file_service_identifier : [ HC.ContentUpdate( HC.CONTENT_DATA_TYPE_FILES, HC.CONTENT_UPDATE_PENDING, hashes ) ] } )
            
        
    
    def AddMediaResults( self, page_key, media_results, append = True ):
        
        if page_key == self._page_key: return ClientGUIMixins.ListeningMediaList.AddMediaResults( self, media_results, append = append )
        
    
    def Archive( self, hashes ):
        
        ClientGUIMixins.ListeningMediaList.Archive( self, hashes )
        
        affected_media = self._GetMedia( hashes )
        
        if len( affected_media ) > 0: self._RedrawMediaIfLoaded( affected_media )
        
        self._PublishSelectionChange()
        
        if self._focussed_media is not None: self._HitMedia( self._focussed_media, False, False )
        
    
    def Collect( self, page_key, collect_by = -1 ):
        
        if page_key == self._page_key:
            
            self._Select( 'none' )
            
            ClientGUIMixins.ListeningMediaList.Collect( self, collect_by )
            
            self._RefitCanvas()
            
            # no refresh needed since the sort call that always comes after will do it
            
        
    
    def FileDumped( self, page_key, hash, status ):
        
        if page_key == self._page_key:
            
            media = self._GetMedia( { hash } )
            
            for m in media: m.Dumped( status )
            
            self._RedrawMediaIfLoaded( media )
            
        
    
    def PageHidden( self, page_key ):
        
        if page_key == self._page_key: HC.pubsub.pub( 'focus_changed', self._page_key, None )
        
    
    def PageShown( self, page_key ):
        
        if page_key == self._page_key:
            
            HC.pubsub.pub( 'focus_changed', self._page_key, self._focussed_media )
            
            self._PublishSelectionChange()
            
        
    
    def ProcessContentUpdates( self, service_identifiers_to_content_updates ):
        
        ClientGUIMixins.ListeningMediaList.ProcessContentUpdates( self, service_identifiers_to_content_updates )
        
        force_reload = False
        
        for ( service_identifier, content_updates ) in service_identifiers_to_content_updates.items():
            
            service_type = service_identifier.GetType()
            
            for content_update in content_updates:
                
                ( data_type, action, row ) = content_update.ToTuple()
                
                hashes = content_update.GetHashes()
                
                affected_media = self._GetMedia( hashes )
                
                if len( affected_media ) > 0:
                    
                    self._RedrawMediaIfLoaded( affected_media )
                    
                    force_reload = True
                    
                
            
        
        self._PublishSelectionChange( force_reload = force_reload )
        
        if self._focussed_media is not None: self._HitMedia( self._focussed_media, False, False )
        
    
    def ProcessServiceUpdates( self, service_identifiers_to_service_updates ):
        
        ClientGUIMixins.ListeningMediaList.ProcessServiceUpdates( self, service_identifiers_to_service_updates )
        
        for ( service_identifier, service_updates ) in service_identifiers_to_service_updates.items():
            
            for service_update in service_updates:
                
                ( action, row ) = service_update.ToTuple()
                
                if action in ( HC.SERVICE_UPDATE_DELETE_PENDING, HC.SERVICE_UPDATE_RESET ): self._RefitCanvas()
                
                self._PublishSelectionChange( force_reload = True )
                
            
        
    
    def SetFocussedMedia( self, page_key, media ):
        
        if page_key == self._page_key:
            
            if media is None: self._SetFocussedMedia( None )
            else:
                
                try:
                    
                    my_media = self._GetMedia( media.GetHashes() )[0]
                    
                    self._HitMedia( my_media, False, False )
                    
                    self._ScrollToMedia( self._focussed_media )
                    
                except: pass
                
            
        
    
    def Sort( self, page_key, sort_by = None ):
        
        if page_key == self._page_key:
            
            ClientGUIMixins.ListeningMediaList.Sort( self, sort_by )
            
            self._RedrawCanvas()
            
        
        HC.pubsub.pub( 'sorted_media_pulse', self._page_key, self._sorted_media )
        
    
class MediaPanelNoQuery( MediaPanel ):
    
    def __init__( self, parent, page_key, file_service_identifier ): MediaPanel.__init__( self, parent, page_key, file_service_identifier, [] )
    
    def _GetPrettyStatus( self ): return 'No query'
    
    def GetSortedMedia( self ): return None
    
class MediaPanelLoading( MediaPanel ):
    
    def __init__( self, parent, page_key, file_service_identifier ):
        
        self._current = None
        self._max = None
        
        MediaPanel.__init__( self, parent, page_key, file_service_identifier, [] )
        
        HC.pubsub.sub( self, 'SetNumQueryResults', 'set_num_query_results' )
        
    
    def _GetPrettyStatus( self ):
        
        s = u'Loading\u2026'
        
        if self._current is not None:
            
            s += ' ' + HC.ConvertIntToPrettyString( self._current )
            
            if self._max is not None:
                
                s += ' of ' + HC.ConvertIntToPrettyString( self._max )
                
            
        
        return s
        
    
    def GetSortedMedia( self ): return None
    
    def SetNumQueryResults( self, current, max ):
        
        self._current = current
        
        self._max = max
        
        self._PublishSelectionChange()
        
    
class MediaPanelThumbnails( MediaPanel ):
    
    def __init__( self, parent, page_key, file_service_identifier, media_results, refreshable = True ):
        
        MediaPanel.__init__( self, parent, page_key, file_service_identifier, media_results )
        
        self._refreshable = refreshable
        
        self._num_columns = 1
        self._num_rows_in_client_height = 0
        self._drawn_index_bounds = None
        
        self._timer_animation = wx.Timer( self, ID_TIMER_ANIMATION )
        self._thumbnails_being_faded_in = {}
        
        self._current_y_offset = 0
        
        self._thumbnail_span_dimensions = CC.AddPaddingToDimensions( HC.options[ 'thumbnail_dimensions' ], ( CC.THUMBNAIL_BORDER + CC.THUMBNAIL_MARGIN ) * 2 )
        
        ( thumbnail_span_width, thumbnail_span_height ) = self._thumbnail_span_dimensions
        
        self.SetScrollRate( 0, thumbnail_span_height )
        
        self._canvas_bmp = wx.EmptyBitmap( 0, 0 )
        
        self.Bind( wx.EVT_SCROLLWIN, self.EventScroll )
        self.Bind( wx.EVT_LEFT_DOWN, self.EventSelection )
        self.Bind( wx.EVT_RIGHT_DOWN, self.EventShowMenu )
        self.Bind( wx.EVT_LEFT_DCLICK, self.EventMouseFullScreen )
        self.Bind( wx.EVT_MIDDLE_DOWN, self.EventMouseFullScreen )
        self.Bind( wx.EVT_PAINT, self.EventPaint )
        self.Bind( wx.EVT_SIZE, self.EventResize )
        self.Bind( wx.EVT_TIMER, self.TIMEREventAnimation, id = ID_TIMER_ANIMATION )
        
        self.Bind( wx.EVT_KEY_DOWN, self.EventKeyDown )
        
        self.Bind( wx.EVT_MENU, self.EventMenu )
        
        self.RefreshAcceleratorTable()
        
        HC.pubsub.sub( self, 'NewThumbnails', 'new_thumbnails' )
        HC.pubsub.sub( self, 'ThumbnailsResized', 'thumbnail_resize' )
        HC.pubsub.sub( self, 'RefreshAcceleratorTable', 'options_updated' )
        HC.pubsub.sub( self, 'WaterfallThumbnail', 'waterfall_thumbnail' )
        
    
    def _CalculateCanvasNumRows( self ):
        
        ( canvas_width, canvas_height ) = self._canvas_bmp.GetSize()
        
        ( thumbnail_span_width, thumbnail_span_height ) = self._thumbnail_span_dimensions
        
        num_rows = canvas_height / thumbnail_span_height
        
        if canvas_height % thumbnail_span_height > 0: num_rows += 1
        
        return num_rows
        
    
    def _CalculateCurrentIndexBounds( self ):
        
        NUM_ROWS_TO_DRAW_AHEAD = 0 # this is buggy
        
        ( xUnit, yUnit ) = self.GetScrollPixelsPerUnit()
        
        y_start = self._GetYStart()
        
        earliest_y = y_start * yUnit
        
        ( my_client_width, my_client_height ) = self.GetClientSize()
        
        last_y = earliest_y + my_client_height
        
        ( thumbnail_span_width, thumbnail_span_height ) = self._thumbnail_span_dimensions
        
        #
        
        earliest_row = earliest_y / thumbnail_span_height
        
        earliest_index = max( 0, ( earliest_row - NUM_ROWS_TO_DRAW_AHEAD ) * self._num_columns )
        
        #
        
        last_row = last_y / thumbnail_span_height
        
        if last_y % thumbnail_span_height > 0: last_row += 1
        
        virtual_last_index = ( ( last_row + 1 + NUM_ROWS_TO_DRAW_AHEAD ) * self._num_columns ) - 1
        
        last_index = min( virtual_last_index, len( self._sorted_media ) - 1 )
        
        return ( earliest_index, last_index )
        
    
    def _CalculateLastVisibleRow( self ):
        
        ( xUnit, yUnit ) = self.GetScrollPixelsPerUnit()
        
        y_start = self._GetYStart()
        
        y_offset = y_start * yUnit
        
        ( my_client_width, my_client_height ) = self.GetClientSize()
        
        total_visible_y = y_offset + my_client_height
        
        ( thumbnail_span_width, thumbnail_span_height ) = self._thumbnail_span_dimensions
        
        max_last_visible_row = total_visible_y / thumbnail_span_height
        
        if total_visible_y % thumbnail_span_height > 0: max_last_visible_row += 1
        
        actual_last_visible_row = min( self._CalculateNumRows(), max_last_visible_row )
        
        return actual_last_visible_row
        
    
    def _CalculateNumRows( self ):
        
        num_media = len( self._sorted_media )
        
        num_rows = num_media / self._num_columns
        
        if num_media % self._num_columns > 0: num_rows += 1
        
        return num_rows
        
    
    def _CleanCanvas( self ):
        
        ( earliest_index, last_index ) = self._CalculateCurrentIndexBounds()
        
        if self._drawn_index_bounds is None: self._DrawIndices( earliest_index, last_index )
        else:
            
            ( drawn_from_index, drawn_to_index ) = self._drawn_index_bounds
            
            if earliest_index < drawn_from_index: self._DrawIndices( earliest_index, drawn_from_index - 1 )
            
            if drawn_to_index < last_index: self._DrawIndices( drawn_to_index + 1, last_index )
            
        
    
    def _DrawIndices( self, from_index, to_index ):
        
        ( my_width, my_height ) = self._canvas_bmp.GetSize()
        
        ( thumbnail_span_width, thumbnail_span_height ) = self._thumbnail_span_dimensions
        
        from_row = from_index / self._num_columns
        to_row = to_index / self._num_columns
        
        begin_white_from_row = from_row
        
        if from_index % self._num_columns > 0: begin_white_from_row += 1
        
        begin_white_y = begin_white_from_row * thumbnail_span_height
        
        # i.e. if we are drawing the last thumb, so have to fill in the rest of any space with white
        if to_index == len( self._sorted_media ) - 1: end_white_y = max( ( to_row + 1 ) * thumbnail_span_height, my_height )
        else: end_white_y = ( to_row + 1 ) * thumbnail_span_height
        
        height_white_y = end_white_y - begin_white_y
        
        dc = self._GetScrolledDC()
        
        dc.SetBrush( wx.WHITE_BRUSH )
        
        dc.SetPen( wx.TRANSPARENT_PEN )
        
        dc.DrawRectangle( 0, begin_white_y, my_width, height_white_y )
        
        #
        
        thumbnails_to_render_later = []
        
        for i in range( from_index, to_index + 1 ): # + 1 means we include to_index
            
            thumbnail = self._sorted_media[ i ]
            
            hash = thumbnail.GetDisplayMedia().GetHash()
            
            if hash in self._thumbnails_being_faded_in:
                
                ( original_bmp, alpha_bmp, canvas_bmp, x, y, num_frames_rendered ) = self._thumbnails_being_faded_in[ hash ]
            
                current_row = i / self._num_columns
                
                current_col = i % self._num_columns
                
                x = current_col * thumbnail_span_width + CC.THUMBNAIL_MARGIN
                y = current_row * thumbnail_span_height + CC.THUMBNAIL_MARGIN
                
                self._thumbnails_being_faded_in[ hash ] = ( original_bmp, alpha_bmp, canvas_bmp, x, y, num_frames_rendered )
                
            else:
                
                if thumbnail.IsLoaded():
                    
                    current_row = i / self._num_columns
                    
                    current_col = i % self._num_columns
                    
                    dc.DrawBitmap( thumbnail.GetBmp(), current_col * thumbnail_span_width + CC.THUMBNAIL_MARGIN, current_row * thumbnail_span_height + CC.THUMBNAIL_MARGIN )
                    
                else: thumbnails_to_render_later.append( thumbnail )
                
            
        
        HC.app.GetThumbnailCache().Waterfall( self._page_key, thumbnails_to_render_later )
        
        if self._drawn_index_bounds is None: self._drawn_index_bounds = ( from_index, to_index )
        else:
            
            ( drawn_from_index, drawn_to_index ) = self._drawn_index_bounds
            
            drawn_from_index = min( from_index, drawn_from_index )
            drawn_to_index = max( to_index, drawn_to_index )
            
            self._drawn_index_bounds = ( drawn_from_index, drawn_to_index )
            
        
    
    def _ExportFiles( self ):
        
        if len( self._selected_media ) > 0:
            
            try:
                
                flat_media = []
                
                for media in self._sorted_media:
                    
                    if media in self._selected_media:
                        
                        if media.IsCollection(): flat_media.extend( media.GetFlatMedia() )
                        else: flat_media.append( media )
                        
                    
                
                with ClientGUIDialogs.DialogSetupExport( None, flat_media ) as dlg: dlg.ShowModal()
                
                self.SetFocus()
                
            except: wx.MessageBox( traceback.format_exc() )
            
        
    
    def _ExportTags( self ):
        
        if len( self._selected_media ) > 0:
            
            try:
                
                flat_media = []
                
                for media in self._sorted_media:
                    
                    if media in self._selected_media:
                        
                        if media.IsCollection(): flat_media.extend( media.GetFlatMedia() )
                        else: flat_media.append( media )
                        
                    
                
                service_identifiers = HC.app.Read( 'service_identifiers', ( HC.LOCAL_TAG, HC.TAG_REPOSITORY ) )
                
                service_identifiers.add( HC.COMBINED_TAG_SERVICE_IDENTIFIER )
                
                service_identifier = ClientGUIDialogs.SelectServiceIdentifier( service_identifiers = service_identifiers )
                
                if service_identifier is not None:
                    
                    with wx.FileDialog( self, style = wx.FD_SAVE, defaultFile = 'tag_update.yaml' ) as dlg:
                        
                        if dlg.ShowModal() == wx.ID_OK:
                            
                            hash_ids_to_hashes = dict( enumerate( ( m.GetHash() for m in flat_media ) ) )
                            hashes_to_hash_ids = { hash : hash_id for ( hash_id, hash ) in hash_ids_to_hashes.items() }
                            
                            tags_to_hash_ids = collections.defaultdict( list )
                            
                            for m in flat_media:
                                
                                hash = m.GetHash()
                                hash_id = hashes_to_hash_ids[ hash ]
                                
                                tags_manager = m.GetTagsManager()
                                
                                current_tags = tags_manager.GetCurrent()
                                
                                for tag in current_tags: tags_to_hash_ids[ tag ].append( hash_id )
                                
                            
                            #
                            
                            service_data = {}
                            content_data = HC.GetEmptyDataDict()
                            
                            mappings = tags_to_hash_ids.items()
                            
                            content_data[ HC.CONTENT_DATA_TYPE_MAPPINGS ][ HC.CONTENT_UPDATE_ADD ] = mappings
                            
                            update = HC.ServerToClientUpdate( service_data, content_data, hash_ids_to_hashes )
                            
                            yaml_text = yaml.safe_dump( update )
                            
                            with open( dlg.GetPath(), 'wb' ) as f: f.write( yaml_text )
                            
                        
                    
                
                self.SetFocus()
                
            except: wx.MessageBox( traceback.format_exc() )
            
        
    
    def _FadeThumbnail( self, thumbnail ):
        
        ( x, y ) = self._GetMediaCoordinates( thumbnail )
        
        if ( x, y ) != ( -1, -1 ):
            
            bmp = thumbnail.GetBmp()
            
            hash = thumbnail.GetDisplayMedia().GetHash()
            
            canvas_bmp = None
            '''
            ( thumbnail_span_width, thumbnail_span_height ) = self._thumbnail_span_dimensions
            
            canvas_bmp = wx.EmptyBitmap( thumbnail_span_width, thumbnail_span_height, 24 )
            
            canvas_bmp_dc = wx.MemoryDC( canvas_bmp )
            
            index = self._sorted_media.index( thumbnail )
            
            ( from_index, to_index ) = self._drawn_index_bounds
            
            if from_index <= index and index <= to_index:
                
                big_canvas_bmp_dc = wx.MemoryDC( self._canvas_bmp )
                
                canvas_bmp_dc.Blit( 0, 0, thumbnail_span_width, thumbnail_span_height, big_canvas_bmp_dc, x, y )
                
            else:
                
                canvas_bmp_dc.SetBrush( wx.WHITE_BRUSH )
                
                canvas_bmp_dc.Clear()
                
            '''
            self._thumbnails_being_faded_in[ hash ] = ( bmp, None, canvas_bmp, x, y, 0 )
            
            if not self._timer_animation.IsRunning(): self._timer_animation.Start( 1, wx.TIMER_ONE_SHOT )
            
        
    
    def _FilterViewableMedia( self, thumbnails ):
        
        if self._drawn_index_bounds is None: return []
        else:
            
            ( earliest_index, last_index ) = self._drawn_index_bounds
            
            indices = [ ( self._sorted_media.index( t ), t ) for t in thumbnails ]
            
            return [ t for ( index, t ) in indices if earliest_index <= index and index <= last_index ]
            
        
        
    
    def _GenerateMediaCollection( self, media_results ): return ThumbnailMediaCollection( self._file_service_identifier, media_results )
    
    def _GenerateMediaSingleton( self, media_result ): return ThumbnailMediaSingleton( self._file_service_identifier, media_result )
    
    def _GetMediaCoordinates( self, media ):
        
        try: index = self._sorted_media.index( media )
        except: return ( -1, -1 )
        
        row = index / self._num_columns
        column = index % self._num_columns
        
        ( thumbnail_span_width, thumbnail_span_height ) = self._thumbnail_span_dimensions
        
        ( x, y ) = ( column * thumbnail_span_width + CC.THUMBNAIL_MARGIN, row * thumbnail_span_height + CC.THUMBNAIL_MARGIN )
        
        return ( x, y )
        
    
    def _GetScrolledDC( self ):
        
        cdc = wx.ClientDC( self )
        
        self.DoPrepareDC( cdc ) # because this is a scrolled window
        
        return wx.BufferedDC( cdc, self._canvas_bmp )
        
    
    def _GetThumbnailUnderMouse( self, mouse_event ):
        
        ( xUnit, yUnit ) = self.GetScrollPixelsPerUnit()
        
        ( x_scroll, y_scroll ) = self.GetViewStart()
        
        y_offset = y_scroll * yUnit
        
        x = mouse_event.GetX()
        y = mouse_event.GetY() + y_offset
        
        ( t_span_x, t_span_y ) = self._thumbnail_span_dimensions
        
        x_mod = x % t_span_x
        y_mod = y % t_span_y
        
        if x_mod <= CC.THUMBNAIL_MARGIN or y_mod <= CC.THUMBNAIL_MARGIN or x_mod > t_span_x - CC.THUMBNAIL_MARGIN or y_mod > t_span_y - CC.THUMBNAIL_MARGIN: return None
        
        column_index = ( x / t_span_x )
        row_index = ( y / t_span_y )
        
        if column_index >= self._num_columns: return None
        
        thumbnail_index = self._num_columns * row_index + column_index
        
        if thumbnail_index >= len( self._sorted_media ): return None
        
        return self._sorted_media[ thumbnail_index ]
        
    
    def _GetYStart( self ):
        
        ( my_virtual_width, my_virtual_height ) = self.GetVirtualSize()
        
        ( my_width, my_height ) = self.GetClientSize()
        
        ( xUnit, yUnit ) = self.GetScrollPixelsPerUnit()
        
        max_y = ( my_virtual_height - my_height ) / yUnit
        
        if ( my_virtual_height - my_height ) % yUnit > 0: max_y += 1
        
        ( x, y ) = self.GetViewStart()
        
        y += self._current_y_offset
        
        y = max( 0, y )
        
        y = min( y, max_y )
        
        return y
        
    
    def _MoveFocussedThumbnail( self, rows, columns, shift ):
        
        if self._focussed_media is not None:
            
            current_position = self._sorted_media.index( self._focussed_media )
            
            new_position = current_position + columns + ( self._num_columns * rows )
            
            if new_position < 0: new_position = 0
            elif new_position > len( self._sorted_media ) - 1: new_position = len( self._sorted_media ) - 1
            
            self._HitMedia( self._sorted_media[ new_position ], False, shift )
            
            self._ScrollToMedia( self._focussed_media )
            
        
    
    def _RedrawCanvas( self ):
        
        self._drawn_index_bounds = None
        
        self._thumbnails_being_faded_in = {}
        
        self._CleanCanvas()
        
    
    def _RedrawMediaIfLoaded( self, thumbnails ):
        
        thumbnails = self._FilterViewableMedia( thumbnails )
        
        for t in thumbnails:
            
            if t.IsLoaded(): self._FadeThumbnail( t )
            
        
    
    def _RefitCanvas( self ):
        
        ( client_width, client_height ) = self.GetClientSize()
        
        if client_width > 0 and client_height > 0:
            
            ( thumbnail_span_width, thumbnail_span_height ) = self._thumbnail_span_dimensions
            
            virtual_num_rows = self._CalculateNumRows()
            
            #
            
            virtual_width = client_width
            
            virtual_height = max( virtual_num_rows * thumbnail_span_height, client_height )
            
            if ( virtual_width, virtual_height ) != self.GetVirtualSize(): self.SetVirtualSize( ( virtual_width, virtual_height ) )
            
            #
            
            current_canvas_num_rows = self._CalculateCanvasNumRows()
            
            last_visible_row = self._CalculateLastVisibleRow()
            
            if last_visible_row > current_canvas_num_rows / 2:
                
                if current_canvas_num_rows == 0: new_canvas_num_rows = min( last_visible_row, virtual_num_rows ) + 1
                else:
                    
                    how_far_we_want_to_extend_to = max( int( current_canvas_num_rows * 2.5 ), last_visible_row )
                    
                    new_canvas_num_rows = min( how_far_we_want_to_extend_to, virtual_num_rows ) + 1
                    
                
                # +1 to cover gap
                
            else: new_canvas_num_rows = current_canvas_num_rows
            
            new_canvas_width = ( self._num_columns + 1 ) * thumbnail_span_width # +1 to fill in any gap
            
            new_canvas_height = max( new_canvas_num_rows * thumbnail_span_height, client_height )
            
            ( old_canvas_width, old_canvas_height ) = self._canvas_bmp.GetSize()
            
            if ( new_canvas_width, new_canvas_height ) != ( old_canvas_width, old_canvas_height ):
                
                old_canvas_bmp = self._canvas_bmp
                
                self._canvas_bmp = wx.EmptyBitmap( new_canvas_width, new_canvas_height, 24 )
                
                if new_canvas_width == old_canvas_width:
                    
                    dc = wx.MemoryDC( self._canvas_bmp )
                    
                    dc.DrawBitmap( old_canvas_bmp, 0, 0 )
                    
                    del dc
                    
                else: self._RedrawCanvas()
                
                old_canvas_bmp.Destroy()
                
            
            self._CleanCanvas()
            
        
    
    def _RemoveMedia( self, singleton_media, collected_media ):
        
        self._drawn_index_bounds = None
        
        MediaPanel._RemoveMedia( self, singleton_media, collected_media )
        
    
    def _ScrollToMedia( self, media ):
        
        if media is not None:
            
            ( x, y ) = self._GetMediaCoordinates( media )
            
            ( start_x, start_y ) = self.GetViewStart()
            
            ( x_unit, y_unit ) = self.GetScrollPixelsPerUnit()
            
            ( width, height ) = self.GetClientSize()
            
            ( thumbnail_span_width, thumbnail_span_height ) = self._thumbnail_span_dimensions
            
            if y < start_y * y_unit:
                
                y_to_scroll_to = y / y_unit
                
                self.Scroll( -1, y_to_scroll_to )
                
                wx.PostEvent( self, wx.ScrollWinEvent( wx.wxEVT_SCROLLWIN_THUMBRELEASE, pos = y_to_scroll_to ) )
                
            elif y > ( start_y * y_unit ) + height - thumbnail_span_height:
                
                y_to_scroll_to = ( y - height ) / y_unit
                
                self.Scroll( -1, y_to_scroll_to + 2 )
                
                wx.PostEvent( self, wx.ScrollWinEvent( wx.wxEVT_SCROLLWIN_THUMBRELEASE, pos = y_to_scroll_to + 2 ) )
                
            
        
    
    def AddMediaResults( self, page_key, media_results, append = True ):
        
        if page_key == self._page_key:
            
            old_num_rows = self._CalculateNumRows()
            
            media = MediaPanel.AddMediaResults( self, page_key, media_results, append = append )
            
            new_num_rows = self._CalculateNumRows()
            
            self._RefitCanvas()
            
            if not append: self._RedrawCanvas()
            
            self._PublishSelectionChange()
            
        
    
    def EventKeyDown( self, event ):
        
        # accelerator tables can't handle escape key in windows, gg
        
        if event.GetKeyCode() == wx.WXK_ESCAPE: self._Select( 'none' )
        else: event.Skip()
        
    
    def EventMenu( self, event ):
        
        action = CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetAction( event.GetId() )
        
        if action is not None:
            
            ( command, data ) = action
            
            if command == 'archive': self._Archive()
            elif command == 'copy_files':
                with wx.BusyCursor(): HC.app.Write( 'copy_files', self._GetSelectedHashes( CC.DISCRIMINANT_LOCAL ) )
            elif command == 'copy_hash': self._CopyHashToClipboard()
            elif command == 'copy_hashes': self._CopyHashesToClipboard()
            elif command == 'copy_local_url': self._CopyLocalUrlToClipboard()
            elif command == 'copy_path': self._CopyPathToClipboard()
            elif command == 'ctrl-space':
                
                if self._focussed_media is not None: self._HitMedia( self._focussed_media, True, False )
                
            elif command == 'custom_filter': self._CustomFilter()
            elif command == 'delete': self._Delete( data )
            elif command == 'download': HC.app.Write( 'content_updates', { HC.LOCAL_FILE_SERVICE_IDENTIFIER : [ HC.ContentUpdate( HC.CONTENT_DATA_TYPE_FILES, HC.CONTENT_UPDATE_PENDING, self._GetSelectedHashes( CC.DISCRIMINANT_NOT_LOCAL ) ) ] } )
            elif command == 'export_files': self._ExportFiles()
            elif command == 'export_tags': self._ExportTags()
            elif command == 'filter': self._Filter()
            elif command == 'fullscreen': self._FullScreen()
            elif command == 'get_similar_to': self._GetSimilarTo()
            elif command == 'inbox': self._Inbox()
            elif command == 'manage_ratings': self._ManageRatings()
            elif command == 'manage_tags': self._ManageTags()
            elif command == 'modify_account': self._ModifyUploaders( data )
            elif command == 'new_thread_dumper': self._NewThreadDumper()
            elif command == 'petition': self._PetitionFiles( data )
            elif command == 'ratings_filter': self._RatingsFilter( data )
            elif command == 'remove': self._Remove()
            elif command == 'rescind_petition': self._RescindPetitionFiles( data )
            elif command == 'rescind_upload': self._RescindUploadFiles( data )
            elif command == 'scroll_end': self._ScrollEnd( False )
            elif command == 'scroll_home': self._ScrollHome( False )
            elif command == 'shift_scroll_end': self._ScrollEnd( True )
            elif command == 'shift_scroll_home': self._ScrollHome( True )
            elif command == 'select': self._Select( data )
            elif command == 'show_selection_in_new_query_page': self._ShowSelectionInNewQueryPage()
            elif command == 'upload': self._UploadFiles( data )
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
            
            cdpp = t.GetFileServiceIdentifiersCDPP()
            
            if cdpp.HasLocal(): self._FullScreen( t )
            elif self._file_service_identifier != HC.COMBINED_FILE_SERVICE_IDENTIFIER:
                
                if len( cdpp.GetCurrentRemote() ) > 0:
                    
                    HC.app.Write( 'content_updates', { HC.LOCAL_FILE_SERVICE_IDENTIFIER : [ HC.ContentUpdate( HC.CONTENT_DATA_TYPE_FILES, HC.CONTENT_UPDATE_PENDING, t.GetHashes() ) ] } )
                    
                
            
        
    
    def EventPaint( self, event ): wx.BufferedPaintDC( self, self._canvas_bmp, wx.BUFFER_VIRTUAL_AREA )
    
    def EventResize( self, event ):
        
        ( client_width, client_height ) = self.GetClientSize()
        
        ( thumbnail_span_width, thumbnail_span_height ) = self._thumbnail_span_dimensions
        
        self._num_columns = client_width / thumbnail_span_width
        
        if self._num_columns == 0: self._num_columns = 1
        
        self._RefitCanvas()
        
        self.Refresh() # in case of small resizes where a dc isn't created, I think, where we get tiny black lines
        
    
    def EventSelection( self, event ):
        
        self._HitMedia( self._GetThumbnailUnderMouse( event ), event.CmdDown(), event.ShiftDown() )
        
        if not ( event.CmdDown() or event.ShiftDown() ): self._ScrollToMedia( self._focussed_media )
        
        event.Skip()
        
    
    def EventShowMenu( self, event ):
        
        thumbnail = self._GetThumbnailUnderMouse( event )
        
        if thumbnail is not None: self._HitMedia( thumbnail, event.CmdDown(), event.ShiftDown() )
        
        all_service_identifiers = [ media.GetFileServiceIdentifiersCDPP() for media in self._selected_media ]
        
        selection_has_local = True in ( s_is.HasLocal() for s_is in all_service_identifiers )
        selection_has_inbox = True in ( media.HasInbox() for media in self._selected_media )
        selection_has_archive = True in ( media.HasArchive() for media in self._selected_media )
        
        menu = wx.Menu()
        
        if thumbnail is None:
            
            if self._refreshable:
                
                menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'refresh' ), 'refresh' )
                
            
            if len( self._sorted_media ) > 0:
                
                if menu.GetMenuItemCount() > 0: menu.AppendSeparator()
                
                select_menu = wx.Menu()
                
                select_menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'select', 'all' ), 'all' )
                
                if selection_has_archive and selection_has_inbox:
                    
                    select_menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'select', 'inbox' ), 'inbox' )
                    select_menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'select', 'archive' ), 'archive' )
                    
                
                select_menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'select', 'none' ), 'none' )
                
                menu.AppendMenu( CC.ID_NULL, 'select', select_menu )
                
            
        else:
            
            if self._focussed_media is not None:
                
                # variables
                
                num_selected = self._GetNumSelected()
                
                multiple_selected = num_selected > 1
                
                services = HC.app.Read( 'services' )
                
                tag_repositories = [ service for service in services if service.GetServiceIdentifier().GetType() == HC.TAG_REPOSITORY ]
                
                file_repositories = [ service for service in services if service.GetServiceIdentifier().GetType() == HC.FILE_REPOSITORY ]
                
                local_ratings_services = [ service for service in services if service.GetServiceIdentifier().GetType() in ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ) ]
                
                i_can_post_ratings = len( local_ratings_services ) > 0
                
                downloadable_file_service_identifiers = { repository.GetServiceIdentifier() for repository in file_repositories if repository.GetAccount().HasPermission( HC.GET_DATA ) }
                uploadable_file_service_identifiers = { repository.GetServiceIdentifier() for repository in file_repositories if repository.GetAccount().HasPermission( HC.POST_DATA ) }
                petition_resolvable_file_service_identifiers = { repository.GetServiceIdentifier() for repository in file_repositories if repository.GetAccount().HasPermission( HC.RESOLVE_PETITIONS ) }
                petitionable_file_service_identifiers = { repository.GetServiceIdentifier() for repository in file_repositories if repository.GetAccount().HasPermission( HC.POST_PETITIONS ) } - petition_resolvable_file_service_identifiers
                user_manageable_file_service_identifiers = { repository.GetServiceIdentifier() for repository in file_repositories if repository.GetAccount().HasPermission( HC.MANAGE_USERS ) }
                admin_file_service_identifiers = { repository.GetServiceIdentifier() for repository in file_repositories if repository.GetAccount().HasPermission( HC.GENERAL_ADMIN ) }
                
                if multiple_selected:
                    
                    uploaded_phrase = 'all uploaded to'
                    pending_phrase = 'all pending to'
                    petitioned_phrase = 'all petitioned from'
                    deleted_phrase = 'all deleted from'
                    
                    download_phrase = 'download all possible'
                    upload_phrase = 'upload all possible to'
                    rescind_upload_phrase = 'rescind pending uploads to'
                    petition_phrase = 'petition all possible for removal from'
                    rescind_petition_phrase = 'rescind petitions for'
                    remote_delete_phrase = 'delete all possible from'
                    modify_account_phrase = 'modify the accounts that uploaded these to'
                    
                    manage_tags_phrase = 'files\' tags'
                    manage_ratings_phrase = 'files\' ratings'
                    
                    archive_phrase = 'archive all'
                    inbox_phrase = 'return all to inbox'
                    remove_phrase = 'remove all'
                    local_delete_phrase = 'delete all'
                    dump_phrase = 'dump all'
                    export_phrase = 'files'
                    copy_phrase = 'files'
                    
                else:
                    
                    uploaded_phrase = 'uploaded to'
                    pending_phrase = 'pending to'
                    petitioned_phrase = 'petitioned from'
                    deleted_phrase = 'deleted from'
                    
                    download_phrase = 'download'
                    upload_phrase = 'upload to'
                    rescind_upload_phrase = 'rescind pending upload to'
                    petition_phrase = 'petition for removal from'
                    rescind_petition_phrase = 'rescind petition for'
                    remote_delete_phrase = 'delete from'
                    modify_account_phrase = 'modify the account that uploaded this to'
                    
                    manage_tags_phrase = 'file\'s tags'
                    manage_ratings_phrase = 'file\'s ratings'
                    
                    archive_phrase = 'archive'
                    inbox_phrase = 'return to inbox'
                    remove_phrase = 'remove'
                    local_delete_phrase = 'delete'
                    dump_phrase = 'dump'
                    export_phrase = 'file'
                    copy_phrase = 'file'
                    
                
                # info about the files
                
                def MassUnion( lists ): return { item for item in itertools.chain.from_iterable( lists ) }
                
                all_current_file_service_identifiers = [ service_identifiers.GetCurrentRemote() for service_identifiers in all_service_identifiers ]
                
                current_file_service_identifiers = HC.IntelligentMassIntersect( all_current_file_service_identifiers )
                
                some_current_file_service_identifiers = MassUnion( all_current_file_service_identifiers ) - current_file_service_identifiers
                
                all_pending_file_service_identifiers = [ service_identifiers.GetPendingRemote() for service_identifiers in all_service_identifiers ]
                
                pending_file_service_identifiers = HC.IntelligentMassIntersect( all_pending_file_service_identifiers )
                
                some_pending_file_service_identifiers = MassUnion( all_pending_file_service_identifiers ) - pending_file_service_identifiers
                
                selection_uploaded_file_service_identifiers = some_pending_file_service_identifiers.union( pending_file_service_identifiers )
                
                all_petitioned_file_service_identifiers = [ service_identifiers.GetPetitionedRemote() for service_identifiers in all_service_identifiers ]
                
                petitioned_file_service_identifiers = HC.IntelligentMassIntersect( all_petitioned_file_service_identifiers )
                
                some_petitioned_file_service_identifiers = MassUnion( all_petitioned_file_service_identifiers ) - petitioned_file_service_identifiers
                
                selection_petitioned_file_service_identifiers = some_petitioned_file_service_identifiers.union( petitioned_file_service_identifiers )
                
                all_deleted_file_service_identifiers = [ service_identifiers.GetDeletedRemote() for service_identifiers in all_service_identifiers ]
                
                deleted_file_service_identifiers = HC.IntelligentMassIntersect( all_deleted_file_service_identifiers )
                
                some_deleted_file_service_identifiers = MassUnion( all_deleted_file_service_identifiers ) - deleted_file_service_identifiers
                
                # valid commands for the files
                
                selection_uploadable_file_service_identifiers = set()
                
                for s_is in all_service_identifiers:
                    
                    # we can upload (set pending) to a repo_id when we have permission, a file is local, not current, not pending, and either ( not deleted or admin )
                    
                    if s_is.HasLocal(): selection_uploadable_file_service_identifiers.update( uploadable_file_service_identifiers - s_is.GetCurrentRemote() - s_is.GetPendingRemote() - ( s_is.GetDeletedRemote() - admin_file_service_identifiers ) )
                    
                
                selection_downloadable_file_service_identifiers = set()
                
                for s_is in all_service_identifiers:
                    
                    # we can download (set pending to local) when we have permission, a file is not local and not already downloading and current
                    
                    if not s_is.HasLocal() and not s_is.HasDownloading(): selection_downloadable_file_service_identifiers.update( downloadable_file_service_identifiers & s_is.GetCurrentRemote() )
                    
                
                selection_petitionable_file_service_identifiers = set()
                
                for s_is in all_service_identifiers:
                    
                    # we can petition when we have permission and a file is current
                    # we can re-petition an already petitioned file
                    
                    selection_petitionable_file_service_identifiers.update( petitionable_file_service_identifiers & s_is.GetCurrentRemote() )
                    
                
                selection_deletable_file_service_identifiers = set()
                
                for s_is in all_service_identifiers:
                    
                    # we can delete remote when we have permission and a file is current and it is not already petitioned
                    
                    selection_deletable_file_service_identifiers.update( ( petition_resolvable_file_service_identifiers & s_is.GetCurrentRemote() ) - s_is.GetPetitionedRemote() )
                    
                
                selection_modifyable_file_service_identifiers = set()
                
                for s_is in all_service_identifiers:
                    
                    # we can modify users when we have permission and the file is current or deleted
                    
                    selection_modifyable_file_service_identifiers.update( user_manageable_file_service_identifiers & ( s_is.GetCurrentRemote() | s_is.GetDeletedRemote() ) )
                    
                
                # do the actual menu
                
                if multiple_selected: menu.Append( CC.ID_NULL, HC.ConvertIntToPrettyString( num_selected ) + ' files, ' + self._GetPrettyTotalSelectedSize() )
                else:
                    
                    menu.Append( CC.ID_NULL, thumbnail.GetPrettyInfo() )
                    menu.Append( CC.ID_NULL, thumbnail.GetPrettyAge() )
                    
                
                if len( some_current_file_service_identifiers ) > 0: AddFileServiceIdentifiersToMenu( menu, some_current_file_service_identifiers, 'some uploaded to', CC.ID_NULL )
                
                if len( current_file_service_identifiers ) > 0: AddFileServiceIdentifiersToMenu( menu, current_file_service_identifiers, uploaded_phrase, CC.ID_NULL )
                
                if len( some_pending_file_service_identifiers ) > 0: AddFileServiceIdentifiersToMenu( menu, some_pending_file_service_identifiers, 'some pending to', CC.ID_NULL )
                
                if len( pending_file_service_identifiers ) > 0: AddFileServiceIdentifiersToMenu( menu, pending_file_service_identifiers, pending_phrase, CC.ID_NULL )
                
                if len( some_petitioned_file_service_identifiers ) > 0: AddFileServiceIdentifiersToMenu( menu, some_petitioned_file_service_identifiers, 'some petitioned from', CC.ID_NULL )
                
                if len( petitioned_file_service_identifiers ) > 0: AddFileServiceIdentifiersToMenu( menu, petitioned_file_service_identifiers, petitioned_phrase, CC.ID_NULL )
                
                if len( some_deleted_file_service_identifiers ) > 0: AddFileServiceIdentifiersToMenu( menu, some_deleted_file_service_identifiers, 'some deleted from', CC.ID_NULL )
                
                if len( deleted_file_service_identifiers ) > 0: AddFileServiceIdentifiersToMenu( menu, deleted_file_service_identifiers, deleted_phrase, CC.ID_NULL )
                
                menu.AppendSeparator()
                
                #
                
                len_interesting_file_service_identifiers = 0
                
                len_interesting_file_service_identifiers += len( selection_downloadable_file_service_identifiers )
                len_interesting_file_service_identifiers += len( selection_uploadable_file_service_identifiers )
                len_interesting_file_service_identifiers += len( selection_uploaded_file_service_identifiers )
                len_interesting_file_service_identifiers += len( selection_petitionable_file_service_identifiers )
                len_interesting_file_service_identifiers += len( selection_petitioned_file_service_identifiers )
                len_interesting_file_service_identifiers += len( selection_deletable_file_service_identifiers )
                len_interesting_file_service_identifiers += len( selection_modifyable_file_service_identifiers )
                
                if len_interesting_file_service_identifiers > 0:
                    
                    file_repo_menu = wx.Menu()
                    
                    if len( selection_downloadable_file_service_identifiers ) > 0: file_repo_menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'download' ), download_phrase )
                    
                    if len( selection_uploadable_file_service_identifiers ) > 0: AddFileServiceIdentifiersToMenu( file_repo_menu, selection_uploadable_file_service_identifiers, upload_phrase, 'upload' )
                    
                    if len( selection_uploaded_file_service_identifiers ) > 0: AddFileServiceIdentifiersToMenu( file_repo_menu, selection_uploaded_file_service_identifiers, rescind_upload_phrase, 'rescind_upload' )
                    
                    if len( selection_petitionable_file_service_identifiers ) > 0: AddFileServiceIdentifiersToMenu( file_repo_menu, selection_petitionable_file_service_identifiers, petition_phrase, 'petition' )
                    
                    if len( selection_petitioned_file_service_identifiers ) > 0: AddFileServiceIdentifiersToMenu( file_repo_menu, selection_petitioned_file_service_identifiers, rescind_petition_phrase, 'rescind_petition' )
                    
                    if len( selection_deletable_file_service_identifiers ) > 0: AddFileServiceIdentifiersToMenu( file_repo_menu, selection_deletable_file_service_identifiers, remote_delete_phrase, 'delete' )
                    
                    if len( selection_modifyable_file_service_identifiers ) > 0: AddFileServiceIdentifiersToMenu( file_repo_menu, selection_modifyable_file_service_identifiers, modify_account_phrase, 'modify_account' )
                    
                    menu.AppendMenu( CC.ID_NULL, 'file repositories', file_repo_menu )
                    
                
                #
                
                manage_menu = wx.Menu()
                
                manage_menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'manage_tags' ), manage_tags_phrase )
                
                if i_can_post_ratings: manage_menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'manage_ratings' ), manage_ratings_phrase )
                
                menu.AppendMenu( CC.ID_NULL, 'manage', manage_menu )
                
                #
                
                if selection_has_local:
                    
                    if multiple_selected or i_can_post_ratings: 
                        
                        filter_menu = wx.Menu()
                        
                        if multiple_selected: filter_menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'filter' ), 'archive/delete' )
                        
                        if i_can_post_ratings:
                            
                            ratings_filter_menu = wx.Menu()
                            
                            for service in local_ratings_services: ratings_filter_menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'ratings_filter', service.GetServiceIdentifier() ), service.GetServiceIdentifier().GetName() )
                            
                            filter_menu.AppendMenu( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'ratings_filter' ), 'ratings filter', ratings_filter_menu )
                            
                        
                        if multiple_selected: filter_menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'custom_filter' ), 'custom filter' )
                        
                        menu.AppendMenu( CC.ID_NULL, 'filter', filter_menu )
                        
                    
                
                menu.AppendSeparator()
                
                if selection_has_local:
                    
                    if selection_has_inbox: menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'archive' ), archive_phrase )
                    if selection_has_archive: menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'inbox' ), inbox_phrase )
                    
                    menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'remove' ), remove_phrase )
                    menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'delete', HC.LOCAL_FILE_SERVICE_IDENTIFIER ), local_delete_phrase )
                    
                
                #
                
                export_menu  = wx.Menu()
                
                export_menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'export_files' ), export_phrase )
                export_menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'export_tags' ), 'tags' )
                
                menu.AppendMenu( CC.ID_NULL, 'export', export_menu )
                
                #
                
                menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'new_thread_dumper' ), dump_phrase )
                
                #
                
                copy_menu = wx.Menu()
                
                copy_menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'copy_files' ), copy_phrase )
                copy_menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'copy_hash' ) , 'hash' )
                if multiple_selected: copy_menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'copy_hashes' ) , 'hashes' )
                copy_menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'copy_path' ) , 'path' )
                copy_menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'copy_local_url' ) , 'local url' )
                
                menu.AppendMenu( CC.ID_NULL, 'copy', copy_menu )
                
                #
                
                if self._refreshable:
                    
                    menu.AppendSeparator()
                    
                    menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'refresh' ), 'refresh' )
                    
                
                if len( self._sorted_media ) > 0:
                    
                    menu.AppendSeparator()
                    
                    select_menu = wx.Menu()
                    
                    select_menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'select', 'all' ), 'all' )
                    
                    if selection_has_archive and selection_has_inbox:
                        
                        select_menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'select', 'inbox' ), 'inbox' )
                        select_menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'select', 'archive' ), 'archive' )
                        
                    
                    select_menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'select', 'none' ), 'none' )
                    
                    menu.AppendMenu( CC.ID_NULL, 'select', select_menu )
                    
                
                menu.AppendSeparator()
                
                menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'show_selection_in_new_query_page' ), 'open selection in a new page' )
                
                if self._focussed_media.HasImages():
                    
                    menu.AppendSeparator()
                    
                    menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'get_similar_to' ) , 'find very similar images' )
                    
                
            
        
        if menu.GetMenuItemCount() > 0: self.PopupMenu( menu )
        
        menu.Destroy()
        
        event.Skip()
        
    
    def EventScroll( self, event ):
        
        # it seems that some scroll events happen after the viewstart has changed, some happen before
        # so I have to keep track of a manual current_y_start
        
        ( my_width, my_height ) = self.GetClientSize()
        
        ( xUnit, yUnit ) = self.GetScrollPixelsPerUnit()
        
        page_of_y_units = my_height / yUnit
        
        event_type = event.GetEventType()
        
        if event_type == wx.wxEVT_SCROLLWIN_LINEUP: self._current_y_offset = -1
        elif event_type == wx.wxEVT_SCROLLWIN_LINEDOWN: self._current_y_offset = 1
        elif event_type == wx.wxEVT_SCROLLWIN_THUMBTRACK: self._current_y_offset = 0
        elif event_type == wx.wxEVT_SCROLLWIN_THUMBRELEASE: self._current_y_offset = 0
        elif event_type == wx.wxEVT_SCROLLWIN_PAGEUP: self._current_y_offset = - page_of_y_units
        elif event_type == wx.wxEVT_SCROLLWIN_PAGEDOWN: self._current_y_offset = page_of_y_units
        
        self._RefitCanvas()
        
        self._current_y_offset = 0
        
        event.Skip()
        
    
    def NewThumbnails( self, hashes ):
        
        affected_thumbnails = self._GetMedia( hashes )
        
        if len( affected_thumbnails ) > 0:
            
            for t in affected_thumbnails: t.ReloadFromDB()
            
            self._RedrawMediaIfLoaded( affected_thumbnails )
            
        
    
    def RefreshAcceleratorTable( self ):
        
        entries = [
        ( wx.ACCEL_NORMAL, wx.WXK_HOME, CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'scroll_home' ) ),
        ( wx.ACCEL_NORMAL, wx.WXK_NUMPAD_HOME, CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'scroll_home' ) ),
        ( wx.ACCEL_NORMAL, wx.WXK_END, CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'scroll_end' ) ),
        ( wx.ACCEL_NORMAL, wx.WXK_NUMPAD_END, CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'scroll_end' ) ),
        ( wx.ACCEL_NORMAL, wx.WXK_DELETE, CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'delete', HC.LOCAL_FILE_SERVICE_IDENTIFIER ) ),
        ( wx.ACCEL_NORMAL, wx.WXK_NUMPAD_DELETE, CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'delete', HC.LOCAL_FILE_SERVICE_IDENTIFIER ) ),
        ( wx.ACCEL_NORMAL, wx.WXK_RETURN, CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'fullscreen' ) ),
        ( wx.ACCEL_NORMAL, wx.WXK_NUMPAD_ENTER, CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'fullscreen' ) ),
        ( wx.ACCEL_NORMAL, wx.WXK_UP, CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'key_up' ) ),
        ( wx.ACCEL_NORMAL, wx.WXK_NUMPAD_UP, CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'key_up' ) ),
        ( wx.ACCEL_NORMAL, wx.WXK_DOWN, CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'key_down' ) ),
        ( wx.ACCEL_NORMAL, wx.WXK_NUMPAD_DOWN, CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'key_down' ) ),
        ( wx.ACCEL_NORMAL, wx.WXK_LEFT, CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'key_left' ) ),
        ( wx.ACCEL_NORMAL, wx.WXK_NUMPAD_LEFT, CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'key_left' ) ),
        ( wx.ACCEL_NORMAL, wx.WXK_RIGHT, CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'key_right' ) ),
        ( wx.ACCEL_NORMAL, wx.WXK_NUMPAD_RIGHT, CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'key_right' ) ),
        ( wx.ACCEL_SHIFT, wx.WXK_HOME, CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'shift_scroll_home' ) ),
        ( wx.ACCEL_SHIFT, wx.WXK_NUMPAD_HOME, CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'shift_scroll_home' ) ),
        ( wx.ACCEL_SHIFT, wx.WXK_END, CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'shift_scroll_end' ) ),
        ( wx.ACCEL_SHIFT, wx.WXK_NUMPAD_END, CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'shift_scroll_end' ) ),
        ( wx.ACCEL_SHIFT, wx.WXK_UP, CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'key_shift_up' ) ),
        ( wx.ACCEL_SHIFT, wx.WXK_NUMPAD_UP, CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'key_shift_up' ) ),
        ( wx.ACCEL_SHIFT, wx.WXK_DOWN, CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'key_shift_down' ) ),
        ( wx.ACCEL_SHIFT, wx.WXK_NUMPAD_DOWN, CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'key_shift_down' ) ),
        ( wx.ACCEL_SHIFT, wx.WXK_LEFT, CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'key_shift_left' ) ),
        ( wx.ACCEL_SHIFT, wx.WXK_NUMPAD_LEFT, CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'key_shift_left' ) ),
        ( wx.ACCEL_SHIFT, wx.WXK_RIGHT, CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'key_shift_right' ) ),
        ( wx.ACCEL_SHIFT, wx.WXK_NUMPAD_RIGHT, CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'key_shift_right' ) ),
        ( wx.ACCEL_CTRL, ord( 'A' ), CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'select', 'all' ) ),
        ( wx.ACCEL_CTRL, ord( 'c' ), CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'copy_files' )  ),
        ( wx.ACCEL_CTRL, wx.WXK_SPACE, CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'ctrl-space' )  )
        ]
        
        for ( modifier, key_dict ) in HC.options[ 'shortcuts' ].items(): entries.extend( [ ( modifier, key, CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( action ) ) for ( key, action ) in key_dict.items() ] )
        
        self.SetAcceleratorTable( wx.AcceleratorTable( entries ) )
        
    
    def Sort( self, page_key, sort_by = None ):
        
        MediaPanel.Sort( self, page_key, sort_by )
        
        for thumbnail in self._collected_media:
            
            thumbnail.ReloadFromDB()
            
        
        self._RedrawMediaIfLoaded( self._collected_media )
        
    
    def ThumbnailsResized( self ):
        
        self._thumbnail_span_dimensions = CC.AddPaddingToDimensions( HC.options[ 'thumbnail_dimensions' ], ( CC.THUMBNAIL_BORDER + CC.THUMBNAIL_MARGIN ) * 2 )
        
        ( thumbnail_span_width, thumbnail_span_height ) = self._thumbnail_span_dimensions
        
        ( client_width, client_height ) = self.GetClientSize()
        
        self._num_columns = client_width / thumbnail_span_width
        
        if self._num_columns == 0: self._num_columns = 1
        
        self.SetScrollRate( 0, thumbnail_span_height )
        
        for t in self._sorted_media: t.ReloadFromDBLater()
        
        self._RefitCanvas()
        
        self._RedrawCanvas() # to force redraw
        
    
    def TIMEREventAnimation( self, event ):
        
        started = time.clock()
        
        ( thumbnail_span_width, thumbnail_span_height ) = self._thumbnail_span_dimensions
        
        ( start_x, start_y ) = self.GetViewStart()
        
        ( x_unit, y_unit ) = self.GetScrollPixelsPerUnit()
        
        ( width, height ) = self.GetClientSize()
        
        min_y = ( start_y * y_unit ) - thumbnail_span_height
        max_y = ( start_y * y_unit ) + height + thumbnail_span_height
        
        dc = self._GetScrolledDC()
        
        all_info = self._thumbnails_being_faded_in.items()
        
        for ( hash, ( original_bmp, alpha_bmp, canvas_bmp, x, y, num_frames_rendered ) ) in all_info:
            
            if num_frames_rendered == 0:
                
                image = original_bmp.ConvertToImage()
                
                try: image.InitAlpha()
                except: pass
                
                image = image.AdjustChannels( 1, 1, 1, 0.25 )
                
                alpha_bmp = wx.BitmapFromImage( image, 32 )
                
            
            num_frames_rendered += 1
            
            self._thumbnails_being_faded_in[ hash ] = ( original_bmp, alpha_bmp, canvas_bmp, x, y, num_frames_rendered )
            
            if y < min_y or y > max_y or num_frames_rendered == 9:
                
                bmp_to_use = original_bmp
                
                del self._thumbnails_being_faded_in[ hash ]
                
            else:
                
                #canvas_dc = wx.MemoryDC( canvas_bmp )
                
                #canvas_dc.DrawBitmap( alpha_bmp, 0, 0, True )
                
                #del canvas_dc
                
                bmp_to_use = alpha_bmp
                
            
            dc.DrawBitmap( bmp_to_use, x, y, True )
            
            if time.clock() - started > 0.016: break
            
        
        finished = time.clock()
        
        if len( self._thumbnails_being_faded_in ) > 0:
            
            time_this_took_in_ms = ( finished - started ) * 1000
            
            ms = max( 1, int( round( 16.7 - time_this_took_in_ms ) ) )
            
            self._timer_animation.Start( ms, wx.TIMER_ONE_SHOT )
            
        
    
    def WaterfallThumbnail( self, page_key, thumbnail, thumbnail_bmp ):
        
        if self._page_key == page_key:
            
            thumbnail.SetBmp( thumbnail_bmp )
            
            self._FadeThumbnail( thumbnail )
            
        
    
class Selectable():
    
    def __init__( self ): self._selected = False
    
    def Deselect( self ): self._selected = False
    
    def IsLoaded( self ): return False
    
    def IsSelected( self ): return self._selected
    
    def Select( self ): self._selected = True
    
# keep this around, just for reference
class ThumbGridSizer( wx.PySizer ):
    
    def __init__( self, parent_container ):
        
        wx.PySizer.__init__( self )
        
        self._parent_container = parent_container
        
        self._thumbnails = []
        
    
    def _GetThumbnailDimensions( self ): return CC.AddPaddingToDimensions( HC.options[ 'thumbnail_dimensions' ], ( CC.THUMBNAIL_MARGIN + CC.THUMBNAIL_BORDER ) * 2 )
    
    def AddThumbnail( self, thumbnail ): self._thumbnails.append( thumbnail )
    
    def CalcMin( self ):
        
        ( width, height ) = self._parent_container.GetClientSize()
        
        ( thumbnail_span_width, thumbnail_span_height ) = self._GetThumbnailDimensions()
        
        self._num_columns = width / thumbnail_span_width
        
        if self._num_columns == 0: self._num_columns = 1
        
        num_items = len( self._parent_container )
        
        my_min_height = num_items / self._num_columns
        
        if num_items % self._num_columns > 0: my_min_height += 1
        
        my_min_height *= thumbnail_span_height
        
        return wx.Size( width, my_min_height )
        
    
    def RecalcSizes( self ):
        
        w = self.GetContainingWindow()
        
        ( xUnit, yUnit ) = w.GetScrollPixelsPerUnit()
        
        ( x, y ) = w.GetViewStart()
        
        y_offset = y * yUnit
        
        ( thumbnail_span_width, thumbnail_span_height ) = self._GetThumbnailDimensions()
        
        for ( index, thumbnail ) in enumerate( self.GetChildren() ):
            
            current_col = index % self._num_columns
            current_row = index / self._num_columns
            
            thumbnail.SetDimension( ( current_col * thumbnail_span_width, current_row * thumbnail_span_height - y_offset ), ( thumbnail_span_width, thumbnail_span_height ) )
            
        
    
class Thumbnail( Selectable ):
    
    def __init__( self, file_service_identifier ):
        
        Selectable.__init__( self )
        
        self._dump_status = CC.DUMPER_NOT_DUMPED
        self._hydrus_bmp = None
        self._file_service_identifier = file_service_identifier
        
        self._my_dimensions = CC.AddPaddingToDimensions( HC.options[ 'thumbnail_dimensions' ], CC.THUMBNAIL_BORDER * 2 )
        
    
    def _LoadFromDB( self ): self._hydrus_bmp = HC.app.GetThumbnailCache().GetThumbnail( self )
    
    def Dumped( self, dump_status ): self._dump_status = dump_status
    
    def GetBmp( self ):
        
        inbox = self.HasInbox()
        
        local = self.GetFileServiceIdentifiersCDPP().HasLocal()
        
        namespaces = self.GetTagsManager().GetCombinedNamespaces( ( 'creator', 'series', 'title', 'volume', 'chapter', 'page' ) )
        
        creators = namespaces[ 'creator' ]
        series = namespaces[ 'series' ]
        titles = namespaces[ 'title' ]
        volumes = namespaces[ 'volume' ]
        chapters = namespaces[ 'chapter' ]
        pages = namespaces[ 'page' ]
        
        if self._hydrus_bmp is None: self._LoadFromDB()
        
        ( width, height ) = self._my_dimensions
        
        bmp = wx.EmptyBitmap( width, height, 24 )
        
        dc = wx.MemoryDC( bmp )
        
        if not local:
            
            if self._selected: dc.SetBackground( wx.Brush( wx.Colour( 64, 64, 72 ) ) ) # Payne's Gray
            else: dc.SetBackground( wx.Brush( wx.Colour( 32, 32, 36 ) ) ) # 50% Payne's Gray
            
        else:
            
            if self._selected: dc.SetBackground( wx.Brush( CC.COLOUR_SELECTED ) )
            else: dc.SetBackground( wx.Brush( wx.WHITE ) )
            
        
        dc.Clear()
        
        ( thumb_width, thumb_height ) = self._hydrus_bmp.GetSize()
        
        x_offset = ( width - thumb_width ) / 2
        
        y_offset = ( height - thumb_height ) / 2
        
        hydrus_bmp = self._hydrus_bmp.CreateWxBmp()
        
        dc.DrawBitmap( hydrus_bmp, x_offset, y_offset )
        
        hydrus_bmp.Destroy()
        
        collections_string = ''
        
        if len( volumes ) > 0:
            
            if len( volumes ) == 1:
                
                ( volume, ) = volumes
                
                collections_string = 'v' + HC.u( volume )
                
            else: collections_string = 'v' + HC.u( min( volumes ) ) + '-' + HC.u( max( volumes ) )
            
        
        if len( chapters ) > 0:
            
            if len( chapters ) == 1:
                
                ( chapter, ) = chapters
                
                collections_string_append = 'c' + HC.u( chapter )
                
            else: collections_string_append = 'c' + HC.u( min( chapters ) ) + '-' + HC.u( max( chapters ) )
            
            if len( collections_string ) > 0: collections_string += '-' + collections_string_append
            else: collections_string = collections_string_append
            
        
        if len( pages ) > 0:
            
            if len( pages ) == 1:
                
                ( page, ) = pages
                
                collections_string_append = 'p' + HC.u( page )
                
            else: collections_string_append = 'p' + HC.u( min( pages ) ) + '-' + HC.u( max( pages ) )
            
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
            
        
        siblings_manager = HC.app.GetManager( 'tag_siblings' )
        
        upper_info_string = ''
        
        if len( creators ) > 0:
            
            creators = siblings_manager.CollapseNamespacedTags( 'creator', creators )
            
            upper_info_string = ', '.join( creators )
            
            if len( series ) > 0 or len( titles ) > 0: upper_info_string += ' - '
            
        
        if len( series ) > 0:
            
            series = siblings_manager.CollapseNamespacedTags( 'series', series )
            
            upper_info_string += ', '.join( series )
            
        elif len( titles ) > 0:
            
            titles = siblings_manager.CollapseNamespacedTags( 'title', titles )
            
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
            
            if self._selected: colour = wx.Colour( 227, 66, 52 ) # Vermillion, lol
            else: colour = wx.Colour( 248, 208, 204 ) # 25% Vermillion, 75% White
            
        else:
            
            if self._selected: colour = CC.COLOUR_SELECTED_DARK
            else: colour = CC.COLOUR_UNSELECTED
            
        
        dc.SetPen( wx.Pen( colour, style=wx.SOLID ) )
        
        dc.DrawRectangle( 0, 0, width, height )
        
        file_service_identifiers = self.GetFileServiceIdentifiersCDPP()
        
        if inbox: dc.DrawBitmap( CC.GlobalBMPs.inbox_bmp, width - 18, 0 )
        elif HC.LOCAL_FILE_SERVICE_IDENTIFIER in file_service_identifiers.GetPending(): dc.DrawBitmap( CC.GlobalBMPs.downloading_bmp, width - 18, 0 )
        
        if self._dump_status == CC.DUMPER_DUMPED_OK: dc.DrawBitmap( CC.GlobalBMPs.dump_ok, width - 18, 18 )
        elif self._dump_status == CC.DUMPER_RECOVERABLE_ERROR: dc.DrawBitmap( CC.GlobalBMPs.dump_recoverable, width - 18, 18 )
        elif self._dump_status == CC.DUMPER_UNRECOVERABLE_ERROR: dc.DrawBitmap( CC.GlobalBMPs.dump_fail, width - 18, 18 )
        
        if self.IsCollection():
            
            dc.DrawBitmap( CC.GlobalBMPs.collection_bmp, 1, height - 17 )
            
            num_files_str = HC.u( len( self._hashes ) )
            
            dc.SetFont( wx.SystemSettings.GetFont( wx.SYS_DEFAULT_GUI_FONT ) )
            
            ( text_x, text_y ) = dc.GetTextExtent( num_files_str )
            
            dc.SetBrush( wx.Brush( CC.COLOUR_UNSELECTED ) )
            
            dc.SetTextForeground( CC.COLOUR_SELECTED_DARK )
            
            dc.SetPen( wx.TRANSPARENT_PEN )
            
            dc.DrawRectangle( 17, height - text_y - 3, text_x + 2, text_y + 2 )
            
            dc.DrawText( num_files_str, 18, height - text_y - 2 )
            
        
        if self._file_service_identifier.GetType() == HC.LOCAL_FILE:
            
            if len( file_service_identifiers.GetPendingRemote() ) > 0: dc.DrawBitmap( CC.GlobalBMPs.file_repository_pending_bmp, 0, 0 )
            elif len( file_service_identifiers.GetCurrentRemote() ) > 0: dc.DrawBitmap( CC.GlobalBMPs.file_repository_bmp, 0, 0 )
            
        elif self._file_service_identifier in file_service_identifiers.GetCurrentRemote():
            
            if self._file_service_identifier in file_service_identifiers.GetPetitionedRemote(): dc.DrawBitmap( CC.GlobalBMPs.file_repository_petitioned_bmp, 0, 0 )
            
        
        return bmp
        
    
    def IsLoaded( self ): return self._hydrus_bmp is not None
    
    def ReloadFromDB( self ):
        
        self._my_dimensions = CC.AddPaddingToDimensions( HC.options[ 'thumbnail_dimensions' ], CC.THUMBNAIL_BORDER * 2 )
        
        if self._hydrus_bmp is not None: self._LoadFromDB()
        
    
    def ReloadFromDBLater( self ):
        
        self._my_dimensions = CC.AddPaddingToDimensions( HC.options[ 'thumbnail_dimensions' ], CC.THUMBNAIL_BORDER * 2 )
        
        self._hydrus_bmp = None
        
    
    def SetBmp( self, bmp ): self._hydrus_bmp = bmp
    
class ThumbnailMediaCollection( Thumbnail, ClientGUIMixins.MediaCollection ):
    
    def __init__( self, file_service_identifier, media_results ):
        
        ClientGUIMixins.MediaCollection.__init__( self, file_service_identifier, media_results )
        Thumbnail.__init__( self, file_service_identifier )
        
    
    def ProcessContentUpdate( self, service_identifier, content_update ):
        
        ClientGUIMixins.MediaCollection.ProcessContentUpdate( self, service_identifier, content_update )
        
        if service_identifier == HC.LOCAL_FILE_SERVICE_IDENTIFIER:
            
            ( data_type, action, row ) = content_update.ToTuple()
            
            if action == HC.CONTENT_UPDATE_ADD:
                
                hashes = row
                
                if self.GetDisplayMedia().GetHash() in hashes: self.ReloadFromDB()
                
            
        
    
class ThumbnailMediaSingleton( Thumbnail, ClientGUIMixins.MediaSingleton ):
    
    def __init__( self, file_service_identifier, media_result ):
        
        ClientGUIMixins.MediaSingleton.__init__( self, media_result )
        Thumbnail.__init__( self, file_service_identifier )
        
    
    def ProcessContentUpdate( self, servce_identifier, content_update ):
        
        ClientGUIMixins.MediaSingleton.ProcessContentUpdate( self, service_identifier, content_update )
        
        if service_identifier == HC.LOCAL_FILE_SERVICE_IDENTIFIER:
            
            ( data_type, action, row ) = content_update.ToTuple()
            
            if action == HC.CONTENT_UPDATE_ADD: self.ReloadFromDB()
            
        
    