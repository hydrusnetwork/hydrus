import HydrusConstants as HC
import ClientConstants as CC
import ClientGUICommon
import ClientGUIDialogs
import ClientGUICanvas
import ClientGUIMixins
import itertools
import os
import random
import threading
import time
import traceback
import wx

# Option Enums

ID_TIMER_ANIMATION = wx.NewId()

# Sizer Flags

FLAGS_NONE = wx.SizerFlags( 0 )

FLAGS_SMALL_INDENT = wx.SizerFlags( 0 ).Border( wx.ALL, 2 )

FLAGS_EXPAND_PERPENDICULAR = wx.SizerFlags( 0 ).Border( wx.ALL, 2 ).Expand()
FLAGS_EXPAND_BOTH_WAYS = wx.SizerFlags( 2 ).Border( wx.ALL, 2 ).Expand()

FLAGS_EXPAND_SIZER_PERPENDICULAR = wx.SizerFlags( 0 ).Expand()
FLAGS_EXPAND_SIZER_BOTH_WAYS = wx.SizerFlags( 2 ).Expand()

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
    
    def __init__( self, parent, page_key, file_service_identifier, predicates, file_query_result ):
        
        wx.ScrolledWindow.__init__( self, parent, size = ( 0, 0 ), style = wx.BORDER_SUNKEN )
        ClientGUIMixins.ListeningMediaList.__init__( self, file_service_identifier, predicates, file_query_result )
        
        self.SetBackgroundColour( wx.WHITE )
        
        self.SetDoubleBuffered( True )
        
        self._options = wx.GetApp().Read( 'options' )
        
        self.SetScrollRate( 0, 50 )
        
        self._page_key = page_key
        
        self._focussed_media = None
        self._shift_focussed_media = None
        
        self._selected_media = set()
        
        HC.pubsub.sub( self, 'AddMediaResult', 'add_media_result' )
        HC.pubsub.sub( self, 'SetFocussedMedia', 'set_focus' )
        HC.pubsub.sub( self, 'PageHidden', 'page_hidden' )
        HC.pubsub.sub( self, 'PageShown', 'page_shown' )
        HC.pubsub.sub( self, 'Collect', 'collect_media' )
        HC.pubsub.sub( self, 'Sort', 'sort_media' )
        HC.pubsub.sub( self, 'FileDumped', 'file_dumped' )
        
        self._PublishSelectionChange()
        
    
    def _Archive( self ):
        
        hashes = self._GetSelectedHashes( CC.DISCRIMINANT_INBOX )
        
        if len( hashes ) > 0: wx.GetApp().Write( 'content_updates', { HC.LOCAL_FILE_SERVICE_IDENTIFIER : [ HC.ContentUpdate( HC.CONTENT_DATA_TYPE_FILES, HC.CONTENT_UPDATE_ARCHIVE, hashes ) ] } )
        
    
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
            
            data = wx.TextDataObject( 'http://127.0.0.1:45865/file?hash=' + self._focussed_media.GetDisplayMedia().GetHash().encode( 'hex' ) )
            
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
                    
                    try: ClientGUICanvas.CanvasFullscreenMediaListCustomFilter( self.GetTopLevelParent(), self._page_key, self._file_service_identifier, self._predicates, media_results, actions )
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
                        
                        try: wx.GetApp().Write( 'content_updates', { file_service_identifier : [ HC.ContentUpdate( HC.CONTENT_DATA_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, hashes ) ] } )
                        except: wx.MessageBox( traceback.format_exc() )
                        
                    
                
            
        else:
            
            hashes = self._GetSelectedHashes()
            
            content_update = HC.ContentUpdate( HC.CONTENT_DATA_TYPE_FILES, HC.CONTENT_UPDATE_PETITION, ( hashes, 'admin' ) )
            
            service_identifiers_to_content_updates = { file_service_identifier : ( content_update, ) }
            
            wx.GetApp().Write( 'content_updates', service_identifiers_to_content_updates )
            
        
    
    def _DeselectAll( self ):
        
        self._DeselectSelect( self._sorted_media, [] )
        
        self._SetFocussedMedia( None )
        self._shift_focussed_media = None
        
    
    def _DeselectSelect( self, media_to_deselect, media_to_select ):
        
        if len( media_to_deselect ) > 0:
            
            for m in media_to_deselect: m.Deselect()
            
            self._ReblitMedia( media_to_deselect )
            
            self._selected_media.difference_update( media_to_deselect )
            
        
        if len( media_to_select ) > 0:
            
            for m in media_to_select: m.Select()
            
            self._ReblitMedia( media_to_select )
            
            self._selected_media.update( media_to_select )
            
        
        self._PublishSelectionChange()
        
    
    def _FullScreen( self, first_media = None ):
        
        media_results = self.GenerateMediaResults( discriminant = CC.DISCRIMINANT_LOCAL )
        
        if len( media_results ) > 0:
            
            if first_media is None and self._focussed_media is not None: first_media = self._focussed_media
            
            if first_media is not None and first_media.GetFileServiceIdentifiersCDPP().HasLocal(): first_hash = first_media.GetDisplayMedia().GetHash()
            else: first_hash = None
            
            file_query_result = CC.FileQueryResult( self._file_service_identifier, self._predicates, media_results )
            
            ClientGUICanvas.CanvasFullscreenMediaListBrowser( self.GetTopLevelParent(), self._page_key, self._file_service_identifier, self._predicates, file_query_result, first_hash )
            
        
    
    def _Filter( self ):
        
        media_results = self.GenerateMediaResults( discriminant = CC.DISCRIMINANT_LOCAL, selected_media = set( self._selected_media ) )
        
        if len( media_results ) > 0:
            
            try: ClientGUICanvas.CanvasFullscreenMediaListFilter( self.GetTopLevelParent(), self._page_key, self._file_service_identifier, self._predicates, media_results )
            except: wx.MessageBox( traceback.format_exc() )
            
        
    
    def _GetNumSelected( self ): return sum( [ media.GetNumFiles() for media in self._selected_media ] )
    
    def _GetPrettyStatus( self ):
        
        num_files = sum( [ media.GetNumFiles() for media in self._sorted_media ] )
        
        num_selected = self._GetNumSelected()
        
        pretty_total_size = self._GetPrettyTotalSelectedSize()
        
        if num_selected == 0:
            
            if num_files == 1: return '1 file'
            else: return HC.ConvertIntToPrettyString( num_files ) + ' files'
            
        elif num_selected == 1: return '1 of ' + HC.ConvertIntToPrettyString( num_files ) + ' files selected, ' + pretty_total_size
        else: return HC.ConvertIntToPrettyString( num_selected ) + ' of ' + HC.ConvertIntToPrettyString( num_files ) + ' files selected, totalling ' + pretty_total_size
        
    
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
            
            if not ctrl and not shift: self._DeselectAll()
            
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
                
                start_index = self._sorted_media_to_indices[ self._shift_focussed_media ]
                
                end_index = self._sorted_media_to_indices[ media ]
                
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
        
        if len( hashes ) > 0: wx.GetApp().Write( 'content_updates', { HC.LOCAL_FILE_SERVICE_IDENTIFIER : [ HC.ContentUpdate( HC.CONTENT_DATA_TYPE_FILES, HC.CONTENT_UPDATE_INBOX, hashes ) ] } )
        
    
    def _ManageRatings( self ):
        
        if len( self._selected_media ) > 0:
            
            service_identifiers = wx.GetApp().Read( 'service_identifiers', HC.RATINGS_SERVICES )
            
            if len( service_identifiers ) > 0:
                
                try:
                    
                    flat_media = []
                    
                    for media in self._selected_media:
                        
                        if media.IsCollection(): flat_media.extend( media.GetFlatMedia() )
                        else: flat_media.append( media )
                        
                    
                    with ClientGUIDialogs.DialogManageRatings( None, flat_media ) as dlg: dlg.ShowModal()
                    
                    self.SetFocus()
                    
                except: wx.MessageBox( traceback.format_exc() )
                
            
        
    
    def _ManageTags( self ):
        
        if len( self._selected_media ) > 0:
            
            try:
                
                with ClientGUIDialogs.DialogManageTags( None, self._file_service_identifier, self._selected_media ) as dlg: dlg.ShowModal()
                
                self.SetFocus()
                
            except: wx.MessageBox( traceback.format_exc() )
            
        
    
    def _ModifyUploaders( self, file_service_identifier ):
        
        hashes = self._GetSelectedHashes()
        
        if hashes is not None and len( hashes ) > 0:   
            
            with ClientGUIDialogs.DialogModifyAccounts( self, file_service_identifier, [ HC.AccountIdentifier( hash = hash ) for hash in hashes ] ) as dlg: dlg.ShowModal()
            
            self.SetFocus()
            
        
    
    def _NewThreadDumper( self ):
        
        # can't do normal _getselectedhashes because we want to keep order!
        
        args = [ media.GetHashes( CC.DISCRIMINANT_LOCAL ) for media in self._sorted_media if media in self._selected_media ]
        
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
                    
                    wx.GetApp().Write( 'content_updates', service_identifiers_to_content_updates )
                    
                
            
            self.SetFocus()
            
        
    
    def _PublishSelectionChange( self ):
        
        if len( self._selected_media ) == 0: tags_media = self._sorted_media
        else: tags_media = self._selected_media
        
        HC.pubsub.pub( 'new_tags_selection', self._page_key, tags_media )
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
            
        
    
    def _ReblitMedia( self, media ): pass
    
    def _ReblitCanvas( self ): pass
    
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
        
        self._ReblitCanvas()
        
        self._PublishSelectionChange()
        
        HC.pubsub.pub( 'sorted_media_pulse', self._page_key, self.GenerateMediaResults() )
        
    
    def _ScrollEnd( self ):
        
        if len( self._sorted_media ) > 0:
            
            end_media = self._sorted_media[ -1 ]
            
            self._HitMedia( end_media, False, False )
            
            self._ScrollToMedia( end_media )
            
        
    
    def _ScrollHome( self ):
        
        if len( self._sorted_media ) > 0:
            
            home_media = self._sorted_media[ 0 ]
            
            self._HitMedia( home_media, False, False )
            
            self._ScrollToMedia( home_media )
            
        
    
    def _SelectAll( self ): self._DeselectSelect( [], self._sorted_media )
    
    def _SetFocussedMedia( self, media ):
        
        self._focussed_media = media
        
        HC.pubsub.pub( 'focus_changed', self._page_key, media )
        
    
    def _ShowSelectionInNewQueryPage( self ):
        
        hashes = self._GetSelectedHashes()
        
        if hashes is not None and len( hashes ) > 0:
            
            search_context = CC.FileSearchContext()
            
            unsorted_file_query_result = wx.GetApp().Read( 'media_results', search_context, hashes )
            
            hashes_to_media_results = { media_result.GetHash() : media_result for media_result in unsorted_file_query_result }
            
            sorted_media_results = [ hashes_to_media_results[ hash ] for hash in hashes ]
            
            HC.pubsub.pub( 'new_page_query', self._file_service_identifier, initial_media_results = sorted_media_results )
            
        
    
    def _UploadFiles( self, file_service_identifier ):
        
        hashes = self._GetSelectedHashes( not_uploaded_to = file_service_identifier )
        
        if hashes is not None and len( hashes ) > 0:   
            
            try: wx.GetApp().Write( 'content_updates', { file_service_identifier : [ HC.ContentUpdate( HC.CONTENT_DATA_TYPE_FILES, HC.CONTENT_UPDATE_PENDING, hashes ) ] } )
            except Exception as e: wx.MessageBox( unicode( e ) )
            
        
    
    def AddMediaResult( self, page_key, media_result ):
        
        if page_key == self._page_key: return ClientGUIMixins.ListeningMediaList.AddMediaResult( self, media_result )
        
    
    def Archive( self, hashes ):
        
        ClientGUIMixins.ListeningMediaList.Archive( self, hashes )
        
        affected_media = self._GetMedia( hashes )
        
        if len( affected_media ) > 0: self._ReblitMedia( affected_media )
        
        self._PublishSelectionChange()
        
        if self._focussed_media is not None: self._HitMedia( self._focussed_media, False, False )
        
    
    def Collect( self, page_key, collect_by ):
        
        if page_key == self._page_key:
            
            ClientGUIMixins.ListeningMediaList.Collect( self, collect_by )
            
            self._DeselectAll()
            
            self._RefitCanvas()
            
            # no refresh needed since the sort call that always comes after will do it
            
        
    
    def FileDumped( self, page_key, hash, status ):
        
        if page_key == self._page_key:
            
            media = self._GetMedia( { hash } )
            
            for m in media: m.Dumped( status )
            
            self._ReblitMedia( media )
            
        
    
    def PageHidden( self, page_key ):
        
        if page_key == self._page_key: HC.pubsub.pub( 'focus_changed', self._page_key, None )
        
    
    def PageShown( self, page_key ):
        
        if page_key == self._page_key:
            
            HC.pubsub.pub( 'focus_changed', self._page_key, self._focussed_media )
            
            self._PublishSelectionChange()
            
        
    
    def ProcessContentUpdates( self, service_identifiers_to_content_updates ):
        
        ClientGUIMixins.ListeningMediaList.ProcessContentUpdates( self, service_identifiers_to_content_updates )
        
        for ( service_identifier, content_updates ) in service_identifiers_to_content_updates.items():
            
            service_type = service_identifier.GetType()
            
            for content_update in content_updates:
                
                ( data_type, action, row ) = content_update.ToTuple()
                
                hashes = content_update.GetHashes()
                
                affected_media = self._GetMedia( hashes )
                
                if action == HC.CONTENT_UPDATE_DELETE and service_type in ( HC.FILE_REPOSITORY, HC.LOCAL_FILE ) and self._focussed_media in affected_media: self._SetFocussedMedia( None )
                
                if len( affected_media ) > 0: self._ReblitMedia( affected_media )
                
            
        
        self._PublishSelectionChange()
        
        if self._focussed_media is not None: self._HitMedia( self._focussed_media, False, False )
        
    
    def ProcessServiceUpdates( self, service_identifiers_to_service_updates ):
        
        ClientGUIMixins.ListeningMediaList.ProcessServiceUpdates( self, service_identifiers_to_service_updates )
        
        for ( service_identifier, service_updates ) in service_identifiers_to_service_updates.items():
            
            for service_update in service_updates:
                
                ( action, row ) = service_update.ToTuple()
                
                if action in ( HC.SERVICE_UPDATE_DELETE_PENDING, HC.SERVICE_UPDATE_RESET ): 
                    
                    self._RefitCanvas()
                    
                    self._ReblitCanvas()
                    
                
                self._PublishSelectionChange()
                
            
        
    
    def SetFocussedMedia( self, page_key, media ):
        
        if page_key == self._page_key:
            
            if media is None: self._SetFocussedMedia( None )
            else:
                
                try:
                    
                    my_media = self._GetMedia( media.GetHashes() )[0]
                    
                    self._HitMedia( my_media, False, False )
                    
                    self._ScrollToMedia( self._focussed_media )
                    
                except: pass
                
            
        
    
    def Sort( self, page_key, sort_by ):
        
        if page_key == self._page_key:
            
            ClientGUIMixins.ListeningMediaList.Sort( self, sort_by )
            
            self._ReblitCanvas()
            
        
        HC.pubsub.pub( 'sorted_media_pulse', self._page_key, self.GenerateMediaResults() )
        
    
class MediaPanelNoQuery( MediaPanel ):
    
    def __init__( self, parent, page_key, file_service_identifier ): MediaPanel.__init__( self, parent, page_key, file_service_identifier, [], CC.FileQueryResult( file_service_identifier, [], [] ) )
    
    def _GetPrettyStatus( self ): return 'No query'
    
    def GetSortedMedia( self ): return None
    
class MediaPanelLoading( MediaPanel ):
    
    def __init__( self, parent, page_key, file_service_identifier ): MediaPanel.__init__( self, parent, page_key, file_service_identifier, [], CC.FileQueryResult( file_service_identifier, [], [] ) )
    
    def _GetPrettyStatus( self ): return u'Loading\u2026'
    
    def GetSortedMedia( self ): return None
    
class MediaPanelThumbnails( MediaPanel ):
    
    def __init__( self, parent, page_key, file_service_identifier, predicates, file_query_result ):
        
        MediaPanel.__init__( self, parent, page_key, file_service_identifier, predicates, file_query_result )
        
        self._num_columns = 1
        self._num_rows_in_client_height = 0
        self._last_visible_row = 0
        
        self._timer_animation = wx.Timer( self, ID_TIMER_ANIMATION )
        self._thumbnails_being_faded_in = {}
        
        self._drawn_up_to = 0
        
        self._thumbnail_span_dimensions = CC.AddPaddingToDimensions( wx.GetApp().Read( 'options' )[ 'thumbnail_dimensions' ], ( CC.THUMBNAIL_BORDER + CC.THUMBNAIL_MARGIN ) * 2 )
        
        ( thumbnail_span_width, thumbnail_span_height ) = self._thumbnail_span_dimensions
        
        self.SetScrollRate( 0, thumbnail_span_height )
        
        self._canvas_bmp = wx.EmptyBitmap( 0, 0 )
        
        self.Bind( wx.EVT_SCROLLWIN, self.EventScroll )
        self.Bind( wx.EVT_LEFT_DOWN, self.EventSelection )
        self.Bind( wx.EVT_RIGHT_UP, self.EventShowMenu )
        self.Bind( wx.EVT_LEFT_DCLICK, self.EventMouseFullScreen )
        self.Bind( wx.EVT_MIDDLE_DOWN, self.EventMouseFullScreen )
        self.Bind( wx.EVT_PAINT, self.EventPaint )
        self.Bind( wx.EVT_SIZE, self.EventResize )
        self.Bind( wx.EVT_TIMER, self.EventTimerAnimation, id = ID_TIMER_ANIMATION )
        
        self.Bind( wx.EVT_KEY_DOWN, self.EventKeyDown )
        
        self.Bind( wx.EVT_MENU, self.EventMenu )
        
        self.RefreshAcceleratorTable()
        
        HC.pubsub.sub( self, 'NewThumbnails', 'new_thumbnails' )
        HC.pubsub.sub( self, 'ThumbnailsResized', 'thumbnail_resize' )
        HC.pubsub.sub( self, 'RefreshAcceleratorTable', 'options_updated' )
        HC.pubsub.sub( self, 'WaterfallThumbnail', 'waterfall_thumbnail' )
        
    
    def _BlitThumbnail( self, thumbnail ):
        
        ( x, y ) = self._GetMediaCoordinates( thumbnail )
        
        if ( x, y ) != ( -1, -1 ):
            
            bmp = thumbnail.GetBmp()
            
            self._thumbnails_being_faded_in[ ( bmp, x, y ) ] = ( bmp, 0 )
            
            if not self._timer_animation.IsRunning(): self._timer_animation.Start( 0, wx.TIMER_ONE_SHOT )
            
        
    
    def _CalculateLastVisibleRow( self ):
        
        ( x, y ) = self.GetViewStart()
        
        ( xUnit, yUnit ) = self.GetScrollPixelsPerUnit()
        
        y_offset = y * yUnit
        
        ( my_client_width, my_client_height ) = self.GetClientSize()
        
        y_end = y_offset + my_client_height
        
        ( thumbnail_span_width, thumbnail_span_height ) = self._thumbnail_span_dimensions
        
        total_rows_to_end = ( y_end / thumbnail_span_height )
        
        return total_rows_to_end
        
    
    def _ExportFiles( self ):
        
        job_key = os.urandom( 32 )
        
        cancel_event = threading.Event()
        
        with ClientGUIDialogs.DialogProgress( self, job_key, cancel_event ) as dlg:
            
            wx.GetApp().Write( 'export_files', job_key, self._GetSelectedHashes( CC.DISCRIMINANT_LOCAL ), cancel_event )
            
            dlg.ShowModal()
            
        
    
    def _ExportFilesSpecial( self ):
        
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
            
        
    
    def _GenerateMediaCollection( self, media_results ): return ThumbnailMediaCollection( self._file_service_identifier, self._predicates, media_results )
    
    def _GenerateMediaSingleton( self, media_result ): return ThumbnailMediaSingleton( self._file_service_identifier, media_result )
    
    def _GetMediaCoordinates( self, media ):
        
        try: index = self._sorted_media_to_indices[ media ]
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
        
    
    def _MoveFocussedThumbnail( self, rows, columns, shift ):
        
        if self._focussed_media is not None:
            
            current_position = self._sorted_media_to_indices[ self._focussed_media ]
            
            new_position = current_position + columns + ( self._num_columns * rows )
            
            if new_position < 0: new_position = 0
            elif new_position > len( self._sorted_media ) - 1: new_position = len( self._sorted_media ) - 1
            
            self._HitMedia( self._sorted_media[ new_position ], False, shift )
            
            self._ScrollToMedia( self._focussed_media )
            
        
    
    def _ReblitMedia( self, thumbnails ): [ self._BlitThumbnail( t ) for t in thumbnails if t.IsLoaded() ]
    
    def _ReblitCanvas( self ):
        
        ( canvas_width, canvas_height ) = self._canvas_bmp.GetSize()
        
        ( thumbnail_width, thumbnail_height ) = self._thumbnail_span_dimensions
        
        to_row = canvas_height / thumbnail_height
        
        if to_row > 0:
            
            dc = self._GetScrolledDC()
            
            from_row = 0
            
            num_rows_to_draw = ( to_row - from_row ) + 1 # +1 because caller assumes it is inclusive
            
            ( thumbnail_span_width, thumbnail_span_height ) = self._thumbnail_span_dimensions
            
            ( my_width, my_height ) = self._canvas_bmp.GetSize()
            
            dc.SetBrush( wx.Brush( wx.WHITE ) )
            
            dc.SetPen( wx.TRANSPARENT_PEN )
            
            begin_white_y = ( from_row ) * ( thumbnail_span_height + CC.THUMBNAIL_MARGIN )
            height_white_y = num_rows_to_draw * ( thumbnail_span_height + CC.THUMBNAIL_MARGIN )
            
            dc.DrawRectangle( 0, begin_white_y, my_width, height_white_y ) # this incremental clear is so we don't have to do a potentially _very_ expensive (0.4s or more!) dc.Clear()
            
            thumbnails_to_render_later = []
            
            first_index = from_row * self._num_columns
            
            last_index = first_index + ( num_rows_to_draw * self._num_columns )
            
            for ( sub_index, thumbnail ) in enumerate( self._sorted_media[ first_index : last_index ] ):
                
                current_row = from_row + ( sub_index / self._num_columns )
                
                current_col = sub_index % self._num_columns
                
                if thumbnail.IsLoaded(): dc.DrawBitmap( thumbnail.GetBmp(), current_col * thumbnail_span_width + CC.THUMBNAIL_MARGIN, current_row * thumbnail_span_height + CC.THUMBNAIL_MARGIN )
                else: thumbnails_to_render_later.append( thumbnail )
                
            
            self._last_visible_row = to_row
            
            self._thumbnails_being_faded_in = {}
            
            wx.GetApp().GetThumbnailCache().Waterfall( self._page_key, thumbnails_to_render_later )
            
        
    
    def _RefitCanvas( self ):
        
        ( client_width, client_height ) = self.GetClientSize()
        
        if client_width > 0 and client_height > 0:
            
            ( thumbnail_width, thumbnail_height ) = self._thumbnail_span_dimensions
            
            num_media = len( self._sorted_media )
            
            num_rows = num_media / self._num_columns
            
            if num_media % self._num_columns > 0: num_rows += 1
            
            last_visible_row = min( int( self._CalculateLastVisibleRow() * 3.0 ), num_rows ) #+ 5 # plus a bunch to make the canvas bigger than we need
            
            canvas_width = client_width + thumbnail_width # plus a width to fill in any gap
            
            canvas_height = max( last_visible_row * thumbnail_height, client_height )
            
            if ( canvas_width, canvas_height ) != self._canvas_bmp.GetSize(): self._canvas_bmp = wx.EmptyBitmap( canvas_width, canvas_height, 24 )
            
            virtual_width = client_width
            
            virtual_height = max( num_rows * thumbnail_height, client_height )
            
            if ( virtual_width, virtual_height ) != self.GetVirtualSize(): self.SetVirtualSize( ( virtual_width, virtual_height ) )
            
        
    
    def _ScrollToMedia( self, media ):
        
        if media is not None:
            
            ( x, y ) = self._GetMediaCoordinates( media )
            
            ( start_x, start_y ) = self.GetViewStart()
            
            ( x_unit, y_unit ) = self.GetScrollPixelsPerUnit()
            
            ( width, height ) = self.GetClientSize()
            
            ( thumbnail_width, thumbnail_height ) = self._thumbnail_span_dimensions
            
            if y < start_y * y_unit:
                
                y_to_scroll_to = y / y_unit
                
                self.Scroll( -1, y_to_scroll_to )
                
                wx.PostEvent( self, wx.ScrollWinEvent( wx.wxEVT_SCROLLWIN_THUMBRELEASE ) )
                
            elif y > ( start_y * y_unit ) + height - thumbnail_height:
                
                y_to_scroll_to = ( y - height ) / y_unit
                
                self.Scroll( -1, y_to_scroll_to + 2 )
                
                wx.PostEvent( self, wx.ScrollWinEvent( wx.wxEVT_SCROLLWIN_THUMBRELEASE ) )
                
            
        
    
    def AddMediaResult( self, page_key, media_result ):
        
        if page_key == self._page_key:
            
            num_media = len( self._sorted_media )
            
            old_num_rows = num_media / self._num_columns
            
            if num_media % self._num_columns > 0: old_num_rows += 1
            
            media = MediaPanel.AddMediaResult( self, page_key, media_result )
            
            num_media = len( self._sorted_media )
            
            num_rows = num_media / self._num_columns
            
            if num_media % self._num_columns > 0: num_rows += 1
            
            if old_num_rows != num_rows:
                
                self._RefitCanvas()
                
                self._ReblitCanvas()
                
            
            self._BlitThumbnail( media )
            
            self._PublishSelectionChange()
            
        
    
    def EventKeyDown( self, event ):
        
        # accelerator tables can't handle escape key in windows, gg
        
        if event.GetKeyCode() == wx.WXK_ESCAPE: self._DeselectAll()
        else: event.Skip()
        
    
    def EventMenu( self, event ):
        
        action = CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetAction( event.GetId() )
        
        if action is not None:
            
            try:
                
                ( command, data ) = action
                
                if command == 'archive': self._Archive()
                elif command == 'copy_files':
                    with wx.BusyCursor(): wx.GetApp().Write( 'copy_files', self._GetSelectedHashes( CC.DISCRIMINANT_LOCAL ) )
                elif command == 'copy_hash': self._CopyHashToClipboard()
                elif command == 'copy_hashes': self._CopyHashesToClipboard()
                elif command == 'copy_local_url': self._CopyLocalUrlToClipboard()
                elif command == 'copy_path': self._CopyPathToClipboard()
                elif command == 'ctrl-space':
                    
                    if self._focussed_media is not None: self._HitMedia( self._focussed_media, True, False )
                    
                elif command == 'custom_filter': self._CustomFilter()
                elif command == 'delete': self._Delete( data )
                elif command == 'deselect': self._DeselectAll()
                elif command == 'download': wx.GetApp().Write( 'content_updates', { HC.LOCAL_FILE_SERVICE_IDENTIFIER : [ HC.ContentUpdate( HC.CONTENT_DATA_TYPE_FILES, HC.CONTENT_UPDATE_PENDING, self._GetSelectedHashes( CC.DISCRIMINANT_NOT_LOCAL ) ) ] } )
                elif command == 'export': self._ExportFiles()
                elif command == 'export special': self._ExportFilesSpecial()
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
                elif command == 'scroll_end': self._ScrollEnd()
                elif command == 'scroll_home': self._ScrollHome()
                elif command == 'select_all': self._SelectAll()
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
                
            except Exception as e:
                
                wx.MessageBox( unicode( e ) )
                
            
        
    
    def EventMouseFullScreen( self, event ):
        
        t = self._GetThumbnailUnderMouse( event )
        
        if t is not None:
            
            if t.GetFileServiceIdentifiersCDPP().HasLocal(): self._FullScreen( t )
            elif self._file_service_identifier != HC.COMBINED_FILE_SERVICE_IDENTIFIER: wx.GetApp().Write( 'content_updates', { HC.LOCAL_FILE_SERVICE_IDENTIFIER : [ HC.ContentUpdate( HC.CONTENT_DATA_TYPE_FILES, HC.CONTENT_UPDATE_PENDING, t.GetHashes() ) ] } )
            
        
    
    def EventPaint( self, event ): wx.BufferedPaintDC( self, self._canvas_bmp, wx.BUFFER_VIRTUAL_AREA )
    
    def EventResize( self, event ):
        
        old_numcols = self._num_columns
        old_numclientrows = self._num_rows_in_client_height
        
        ( client_width, client_height ) = self.GetClientSize()
        
        ( thumbnail_width, thumbnail_height ) = self._thumbnail_span_dimensions
        
        self._num_columns = client_width / thumbnail_width
        
        if self._num_columns == 0: self._num_columns = 1
        
        num_media = len( self._sorted_media )
        
        num_rows = num_media / self._num_columns
        
        if num_media % self._num_columns > 0: num_rows += 1
        
        if self._num_columns != old_numcols:
            
            self._RefitCanvas()
            
            self._ReblitCanvas()
            
        else:
            
            # the client is the actual window, remember, not the scrollable virtual bmp
            
            self._num_rows_in_client_height = client_height / thumbnail_height
            
            if client_height % thumbnail_height > 0: self._num_rows_in_client_height += 1
            
            if self._num_rows_in_client_height > old_numclientrows:
                
                self._ReblitCanvas()
                
            
        
    
    def EventSelection( self, event ):
        
        self._HitMedia( self._GetThumbnailUnderMouse( event ), event.CmdDown(), event.ShiftDown() )
        
        if not ( event.CmdDown() or event.ShiftDown() ): self._ScrollToMedia( self._focussed_media )
        
        event.Skip()
        
    
    def EventShowMenu( self, event ):
        
        thumbnail = self._GetThumbnailUnderMouse( event )
        
        menu = wx.Menu()
        
        if thumbnail is None: menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'select_all' ), 'select all' )
        else:
            
            self._HitMedia( thumbnail, event.CmdDown(), event.ShiftDown() )
            
            if self._focussed_media is not None:
                
                # variables
                
                num_selected = self._GetNumSelected()
                
                multiple_selected = num_selected > 1
                
                services = wx.GetApp().Read( 'services' )
                
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
                
                all_service_identifiers = [ media.GetFileServiceIdentifiersCDPP() for media in self._selected_media ]
                
                selection_has_local = True in ( s_is.HasLocal() for s_is in all_service_identifiers )
                selection_has_inbox = True in ( media.HasInbox() for media in self._selected_media )
                selection_has_archive = True in ( media.HasArchive() for media in self._selected_media )
                
                if multiple_selected:
                    
                    uploaded_phrase = 'all uploaded to'
                    pending_phrase = 'all pending to'
                    petitioned_phrase = 'all petitioned from'
                    deleted_phrase = 'all deleted from'
                    
                    download_phrase = 'download all possible'
                    upload_phrase = 'upload all possible to'
                    petition_phrase = 'petition all possible for removal from'
                    remote_delete_phrase = 'delete all possible from'
                    modify_account_phrase = 'modify the accounts that uploaded these to'
                    
                    manage_tags_phrase = 'manage tags for all'
                    manage_ratings_phrase = 'manage ratings for all'
                    
                    archive_phrase = 'archive all'
                    inbox_phrase = 'return all to inbox'
                    remove_phrase = 'remove all'
                    local_delete_phrase = 'delete all'
                    dump_phrase = 'dump all'
                    export_phrase = 'export all'
                    export_special_phrase = 'advanced export all'
                    copy_phrase = 'files'
                    
                else:
                    
                    uploaded_phrase = 'uploaded to'
                    pending_phrase = 'pending to'
                    petitioned_phrase = 'petitioned from'
                    deleted_phrase = 'deleted from'
                    
                    download_phrase = 'download'
                    upload_phrase = 'upload to'
                    petition_phrase = 'petition for removal from'
                    remote_delete_phrase = 'delete from'
                    modify_account_phrase = 'modify the account that uploaded this to'
                    
                    manage_tags_phrase = 'manage tags'
                    manage_ratings_phrase = 'manage ratings'
                    
                    archive_phrase = 'archive'
                    inbox_phrase = 'return to inbox'
                    remove_phrase = 'remove'
                    local_delete_phrase = 'delete'
                    dump_phrase = 'dump'
                    export_phrase = 'export'
                    export_special_phrase = 'advanced export'
                    copy_phrase = 'file'
                    
                
                # info about the files
                
                def MassUnion( lists ): return { item for item in itertools.chain.from_iterable( lists ) }
                
                all_current_file_service_identifiers = [ service_identifiers.GetCurrentRemote() for service_identifiers in all_service_identifiers ]
                
                current_file_service_identifiers = HC.IntelligentMassIntersect( all_current_file_service_identifiers )
                
                some_current_file_service_identifiers = MassUnion( all_current_file_service_identifiers ) - current_file_service_identifiers
                
                all_pending_file_service_identifiers = [ service_identifiers.GetPendingRemote() for service_identifiers in all_service_identifiers ]
                
                pending_file_service_identifiers = HC.IntelligentMassIntersect( all_pending_file_service_identifiers )
                
                some_pending_file_service_identifiers = MassUnion( all_pending_file_service_identifiers ) - pending_file_service_identifiers
                
                all_petitioned_file_service_identifiers = [ service_identifiers.GetPetitionedRemote() for service_identifiers in all_service_identifiers ]
                
                petitioned_file_service_identifiers = HC.IntelligentMassIntersect( all_petitioned_file_service_identifiers )
                
                some_petitioned_file_service_identifiers = MassUnion( all_petitioned_file_service_identifiers ) - petitioned_file_service_identifiers
                
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
                
                if len( selection_downloadable_file_service_identifiers ) > 0 or len( selection_uploadable_file_service_identifiers ) > 0 or len( selection_petitionable_file_service_identifiers ) > 0 or len( selection_deletable_file_service_identifiers ) > 0 or len( selection_modifyable_file_service_identifiers ) > 0:
                    
                    if len( selection_downloadable_file_service_identifiers ) > 0: menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'download' ), download_phrase )
                    
                    if len( selection_uploadable_file_service_identifiers ) > 0: AddFileServiceIdentifiersToMenu( menu, selection_uploadable_file_service_identifiers, upload_phrase, 'upload' )
                    
                    if len( selection_petitionable_file_service_identifiers ) > 0: AddFileServiceIdentifiersToMenu( menu, selection_petitionable_file_service_identifiers, petition_phrase, 'petition' )
                    
                    if len( selection_deletable_file_service_identifiers ) > 0: AddFileServiceIdentifiersToMenu( menu, selection_deletable_file_service_identifiers, remote_delete_phrase, 'delete' )
                    
                    if len( selection_modifyable_file_service_identifiers ) > 0: AddFileServiceIdentifiersToMenu( menu, selection_modifyable_file_service_identifiers, modify_account_phrase, 'modify_account' )
                    
                    menu.AppendSeparator()
                    
                
                menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'manage_tags' ), manage_tags_phrase )
                
                if i_can_post_ratings: menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'manage_ratings' ), manage_ratings_phrase )
                
                menu.AppendSeparator()
                
                if selection_has_local:
                    
                    if multiple_selected or i_can_post_ratings: 
                        
                        if multiple_selected: menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'filter' ), 'filter' )
                        
                        if i_can_post_ratings:
                            
                            ratings_filter_menu = wx.Menu()
                            
                            for service in local_ratings_services: ratings_filter_menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'ratings_filter', service.GetServiceIdentifier() ), service.GetServiceIdentifier().GetName() )
                            
                            menu.AppendMenu( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'ratings_filter' ), 'ratings filter', ratings_filter_menu )
                            
                        
                        if multiple_selected: menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'custom_filter' ), 'custom filter' )
                        
                        menu.AppendSeparator()
                        
                    
                    if selection_has_inbox: menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'archive' ), archive_phrase )
                    if selection_has_archive: menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'inbox' ), inbox_phrase )
                    
                    menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'remove' ), remove_phrase )
                    menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'delete', HC.LOCAL_FILE_SERVICE_IDENTIFIER ), local_delete_phrase )
                    
                
                menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'export special' ), export_phrase )
                menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'new_thread_dumper' ), dump_phrase )
                
                menu.AppendSeparator()
                
                menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'show_selection_in_new_query_page' ), 'open selection in a new page' )
                
                menu.AppendSeparator()
                
                copy_menu = wx.Menu()
                
                copy_menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'copy_files' ), copy_phrase )
                copy_menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'copy_hash' ) , 'hash' )
                if multiple_selected: copy_menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'copy_hashes' ) , 'hashes' )
                copy_menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'copy_path' ) , 'path' )
                copy_menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'copy_local_url' ) , 'local url' )
                
                menu.AppendMenu( CC.ID_NULL, 'copy', copy_menu )
                
                if self._focussed_media.HasImages():
                    
                    menu.AppendSeparator()
                    
                    menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'get_similar_to' ) , 'find very similar images' )
                    
                
            
        
        self.PopupMenu( menu )
        
        menu.Destroy()
        
        event.Skip()
        
    
    def EventScroll( self, event ):
        
        num_media = len( self._sorted_media )
        
        num_rows = num_media / self._num_columns
        
        if num_media % self._num_columns > 0: num_rows += 1
        
        current_last_visible_row = self._CalculateLastVisibleRow()
        
        if self._last_visible_row < num_rows and current_last_visible_row > int( self._last_visible_row * 0.75 ):
            
            self._RefitCanvas()
            
            self._ReblitCanvas()
            
        
        event.Skip()
        
    
    def EventTimerAnimation( self, event ):
        
        started = time.clock()
        
        ( thumbnail_width, thumbnail_height ) = self._thumbnail_span_dimensions
        
        ( start_x, start_y ) = self.GetViewStart()
        
        ( x_unit, y_unit ) = self.GetScrollPixelsPerUnit()
        
        ( width, height ) = self.GetClientSize()
        
        min_y = ( start_y * y_unit ) - thumbnail_height
        max_y = ( start_y * y_unit ) + height + thumbnail_height
        
        dc = self._GetScrolledDC()
        
        all_info = self._thumbnails_being_faded_in.items()
        
        for ( key, ( alpha_bmp, num_frames_rendered ) ) in all_info:
            
            ( bmp, x, y ) = key
            
            if num_frames_rendered == 0:
                
                image = bmp.ConvertToImage()
                
                image.InitAlpha()
                
                image = image.AdjustChannels( 1, 1, 1, 0.25 )
                
                alpha_bmp = wx.BitmapFromImage( image, 32 )
                
            
            num_frames_rendered += 1
            
            self._thumbnails_being_faded_in[ key ] = ( alpha_bmp, num_frames_rendered )
            
            if y < min_y or y > max_y or num_frames_rendered == 9:
                
                bmp_to_use = bmp
                
                del self._thumbnails_being_faded_in[ key ]
                
            else:
                
                bmp_to_use = alpha_bmp
                
            
            dc.DrawBitmap( bmp_to_use, x, y, True )
            
            if time.clock() - started > 0.016: break
            
        
        finished = time.clock()
        
        if len( self._thumbnails_being_faded_in ) > 0:
            
            time_this_took_in_ms = ( finished - started ) * 1000
            
            ms = max( 1, int( round( 16.7 - time_this_took_in_ms ) ) )
            
            self._timer_animation.Start( ms, wx.TIMER_ONE_SHOT )
            
        
    
    def NewThumbnails( self, hashes ):
        
        affected_thumbnails = self._GetMedia( hashes )
        
        if len( affected_thumbnails ) > 0:
            
            for t in affected_thumbnails: t.ReloadFromDB()
            
            self._ReblitMedia( affected_thumbnails )
            
        
    
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
        ( wx.ACCEL_SHIFT, wx.WXK_UP, CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'key_shift_up' ) ),
        ( wx.ACCEL_SHIFT, wx.WXK_NUMPAD_UP, CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'key_shift_up' ) ),
        ( wx.ACCEL_SHIFT, wx.WXK_DOWN, CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'key_shift_down' ) ),
        ( wx.ACCEL_SHIFT, wx.WXK_NUMPAD_DOWN, CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'key_shift_down' ) ),
        ( wx.ACCEL_SHIFT, wx.WXK_LEFT, CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'key_shift_left' ) ),
        ( wx.ACCEL_SHIFT, wx.WXK_NUMPAD_LEFT, CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'key_shift_left' ) ),
        ( wx.ACCEL_SHIFT, wx.WXK_RIGHT, CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'key_shift_right' ) ),
        ( wx.ACCEL_SHIFT, wx.WXK_NUMPAD_RIGHT, CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'key_shift_right' ) ),
        ( wx.ACCEL_CMD, ord( 'A' ), CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'select_all' ) ),
        ( wx.ACCEL_CTRL, ord( 'c' ), CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'copy_files' )  ),
        ( wx.ACCEL_CTRL, wx.WXK_SPACE, CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'ctrl-space' )  )
        ]
        
        for ( modifier, key_dict ) in self._options[ 'shortcuts' ].items(): entries.extend( [ ( modifier, key, CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( action ) ) for ( key, action ) in key_dict.items() ] )
        
        self.SetAcceleratorTable( wx.AcceleratorTable( entries ) )
        
    
    def Sort( self, page_key, sort_by ):
        
        MediaPanel.Sort( self, page_key, sort_by )
        
        for thumbnail in self._collected_media:
            
            thumbnail.ReloadFromDB()
            
        
        self._ReblitMedia( self._collected_media )
        
    
    def ThumbnailsResized( self ):
        
        self._thumbnail_span_dimensions = CC.AddPaddingToDimensions( wx.GetApp().Read( 'options' )[ 'thumbnail_dimensions' ], ( CC.THUMBNAIL_BORDER + CC.THUMBNAIL_MARGIN ) * 2 )
        
        ( thumbnail_span_width, thumbnail_span_height ) = self._thumbnail_span_dimensions
        
        ( client_width, client_height ) = self.GetClientSize()
        
        self._num_columns = client_width / thumbnail_span_width
        
        if self._num_columns == 0: self._num_columns = 1
        
        self.SetScrollRate( 0, thumbnail_span_height )
        
        for t in self._sorted_media: t.ReloadFromDBLater()
        
        self._RefitCanvas()
        
        self._ReblitCanvas()
        
    
    def WaterfallThumbnail( self, page_key, thumbnail, thumbnail_bmp ):
        
        thumbnail.SetBmp( thumbnail_bmp )
        
        self._BlitThumbnail( thumbnail )
        
    
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
        
        self._options = wx.GetApp().Read( 'options' )
        
    
    def _GetThumbnailDimensions( self ): return CC.AddPaddingToDimensions( self._options[ 'thumbnail_dimensions' ], ( CC.THUMBNAIL_MARGIN + CC.THUMBNAIL_BORDER ) * 2 )
    
    def AddThumbnail( self, thumbnail ): self._thumbnails.append( thumbnail )
    
    def CalcMin( self ):
        
        ( width, height ) = self._parent_container.GetClientSize()
        
        ( thumbnail_width, thumbnail_height ) = self._GetThumbnailDimensions()
        
        self._num_columns = width / thumbnail_width
        
        if self._num_columns == 0: self._num_columns = 1
        
        num_items = len( self._parent_container )
        
        my_min_height = num_items / self._num_columns
        
        if num_items % self._num_columns > 0: my_min_height += 1
        
        my_min_height *= thumbnail_height
        
        return wx.Size( width, my_min_height )
        
    
    def RecalcSizes( self ):
        
        w = self.GetContainingWindow()
        
        ( xUnit, yUnit ) = w.GetScrollPixelsPerUnit()
        
        ( x, y ) = w.GetViewStart()
        
        y_offset = y * yUnit
        
        ( thumbnail_width, thumbnail_height ) = self._GetThumbnailDimensions()
        
        for ( index, thumbnail ) in enumerate( self.GetChildren() ):
            
            current_col = index % self._num_columns
            current_row = index / self._num_columns
            
            thumbnail.SetDimension( ( current_col * thumbnail_width, current_row * thumbnail_height - y_offset ), ( thumbnail_width, thumbnail_height ) )
            
        
    
class Thumbnail( Selectable ):
    
    def __init__( self, file_service_identifier ):
        
        Selectable.__init__( self )
        
        self._dump_status = CC.DUMPER_NOT_DUMPED
        self._hydrus_bmp = None
        self._file_service_identifier = file_service_identifier
        
        self._my_dimensions = CC.AddPaddingToDimensions( wx.GetApp().Read( 'options' )[ 'thumbnail_dimensions' ], CC.THUMBNAIL_BORDER * 2 )
        
    
    def _LoadFromDB( self ): self._hydrus_bmp = wx.GetApp().GetThumbnailCache().GetThumbnail( self )
    
    def Dumped( self, dump_status ): self._dump_status = dump_status
    
    def GetBmp( self ):
        
        inbox = self.HasInbox()
        
        local = self.GetFileServiceIdentifiersCDPP().HasLocal()
        
        ( creators, series, titles, volumes, chapters, pages ) = self.GetTagsManager().GetCSTVCP()
        
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
                
                collections_string = 'v' + str( volume )
                
            else: collections_string = 'v' + str( min( volumes ) ) + '-' + str( max( volumes ) )
            
        
        if len( chapters ) > 0:
            
            if len( chapters ) == 1:
                
                ( chapter, ) = chapters
                
                collections_string_append = 'c' + str( chapter )
                
            else: collections_string_append = 'c' + str( min( chapters ) ) + '-' + str( max( chapters ) )
            
            if len( collections_string ) > 0: collections_string += '-' + collections_string_append
            else: collections_string = collections_string_append
            
        
        if len( pages ) > 0:
            
            if len( pages ) == 1:
                
                ( page, ) = pages
                
                collections_string_append = 'p' + str( page )
                
            else: collections_string_append = 'p' + str( min( pages ) ) + '-' + str( max( pages ) )
            
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
            
        
        if len( creators ) > 0: upper_info_string = ', '.join( creators )
        elif len( series ) > 0: upper_info_string = ', '.join( series )
        elif len( titles ) > 0: upper_info_string = ', '.join( titles )
        else: upper_info_string = ''
        
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
            
            num_files_str = str( len( self._hashes ) )
            
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
        
        self._my_dimensions = CC.AddPaddingToDimensions( wx.GetApp().Read( 'options' )[ 'thumbnail_dimensions' ], CC.THUMBNAIL_BORDER * 2 )
        
        if self._hydrus_bmp is not None: self._LoadFromDB()
        
    
    def ReloadFromDBLater( self ):
        
        self._my_dimensions = CC.AddPaddingToDimensions( wx.GetApp().Read( 'options' )[ 'thumbnail_dimensions' ], CC.THUMBNAIL_BORDER * 2 )
        
        self._hydrus_bmp = None
        
    
    def SetBmp( self, bmp ): self._hydrus_bmp = bmp
    
class ThumbnailMediaCollection( Thumbnail, ClientGUIMixins.MediaCollection ):
    
    def __init__( self, file_service_identifier, predicates, media_results ):
        
        ClientGUIMixins.MediaCollection.__init__( self, file_service_identifier, predicates, media_results )
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
            
        
    