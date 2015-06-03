import HydrusConstants as HC
import HydrusAudioHandling
import ClientDownloading
import HydrusExceptions
import HydrusFileHandling
import HydrusImageHandling
import HydrusNetworking
import HydrusThreading
import ClientConstants as CC
import ClientData
import ClientCaches
import ClientFiles
import ClientGUICollapsible
import ClientGUICommon
import ClientGUIDialogs
import ClientGUIMedia
import ClientMedia
import json
import os
import threading
import time
import traceback
import urllib
import urlparse
import wx
import wx.lib.scrolledpanel
import HydrusData
import ClientSearch
import HydrusGlobals

CAPTCHA_FETCH_EVENT_TYPE = wx.NewEventType()
CAPTCHA_FETCH_EVENT = wx.PyEventBinder( CAPTCHA_FETCH_EVENT_TYPE )

ID_TIMER_CAPTCHA = wx.NewId()
ID_TIMER_DUMP = wx.NewId()
ID_TIMER_UPDATE = wx.NewId()

class CaptchaControl( wx.Panel ):
    
    def __init__( self, parent, captcha_type, default ):
        
        wx.Panel.__init__( self, parent )
        
        self._captcha_key = default
        
        self._captcha_challenge = None
        self._captcha_runs_out = 0
        self._bitmap = wx.EmptyBitmap( 0, 0, 24 )
        
        self._timer = wx.Timer( self, ID_TIMER_CAPTCHA )
        self.Bind( wx.EVT_TIMER, self.TIMEREvent, id = ID_TIMER_CAPTCHA )
        
        self._captcha_box_panel = ClientGUICommon.StaticBox( self, 'recaptcha' )
        
        self._captcha_panel = ClientGUICommon.BufferedWindow( self._captcha_box_panel, size = ( 300, 57 ) )
        
        self._refresh_button = wx.Button( self._captcha_box_panel, label = '' )
        self._refresh_button.Bind( wx.EVT_BUTTON, self.EventRefreshCaptcha )
        self._refresh_button.Disable()
        
        self._captcha_time_left = wx.StaticText( self._captcha_box_panel )
        
        self._captcha_entry = wx.TextCtrl( self._captcha_box_panel, style = wx.TE_PROCESS_ENTER )
        self._captcha_entry.Bind( wx.EVT_KEY_DOWN, self.EventKeyDown )
        
        self._ready_button = wx.Button( self._captcha_box_panel, label = '' )
        self._ready_button.Bind( wx.EVT_BUTTON, self.EventReady )
        
        sub_vbox = wx.BoxSizer( wx.VERTICAL )
        
        sub_vbox.AddF( self._refresh_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        sub_vbox.AddF( self._captcha_time_left, CC.FLAGS_SMALL_INDENT )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.AddF( self._captcha_panel, CC.FLAGS_NONE )
        hbox.AddF( sub_vbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        hbox2 = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox2.AddF( self._captcha_entry, CC.FLAGS_EXPAND_BOTH_WAYS )
        hbox2.AddF( self._ready_button, CC.FLAGS_MIXED )
        
        self._captcha_box_panel.AddF( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._captcha_box_panel.AddF( hbox2, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._captcha_box_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
        self.Disable()
        
    
    def _DrawEntry( self, entry = None ):
        
        if entry is None:
            
            self._captcha_entry.SetValue( '' )
            self._captcha_entry.Disable()
            
        else: self._captcha_entry.SetValue( entry )
        
    
    def _DrawMain( self ):
        
        dc = self._captcha_panel.GetDC()
        
        if self._captcha_challenge is None:
            
            dc.SetBackground( wx.Brush( wx.WHITE ) )
            
            dc.Clear()
            
            self._refresh_button.SetLabel( '' )
            self._refresh_button.Disable()
            
            self._captcha_time_left.SetLabel( '' )
            
        elif self._captcha_challenge == '':
            
            dc.SetBackground( wx.Brush( wx.WHITE ) )
            
            dc.Clear()
            
            event = wx.NotifyEvent( CAPTCHA_FETCH_EVENT_TYPE )
            
            self.ProcessEvent( event )
            
            if event.IsAllowed():
                
                self._refresh_button.SetLabel( 'get captcha' )
                self._refresh_button.Enable()
                
            else:
                
                self._refresh_button.SetLabel( 'not yet' )
                self._refresh_button.Disable()
                
            
            self._captcha_time_left.SetLabel( '' )
            
        else:
            
            wx_bmp = self._bitmap.GetWxBitmap()
            
            dc.DrawBitmap( wx_bmp, 0, 0 )
            
            wx.CallAfter( wx_bmp.Destroy )
            
            self._refresh_button.SetLabel( 'get new captcha' )
            self._refresh_button.Enable()
            
            self._captcha_time_left.SetLabel( HydrusData.ConvertTimestampToPrettyExpires( self._captcha_runs_out ) )
            
        
        del dc
        
    
    def _DrawReady( self, ready = None ):
        
        if ready is None:
            
            self._ready_button.SetLabel( '' )
            self._ready_button.Disable()
            
        else:
            
            if ready:
                
                self._captcha_entry.Disable()
                self._ready_button.SetLabel( 'edit' )
                
            else:
                
                self._captcha_entry.Enable()
                self._ready_button.SetLabel( 'ready' )
                
            
            self._ready_button.Enable()
            
        
    
    def Disable( self ):
        
        self._captcha_challenge = None
        self._captcha_runs_out = 0
        self._bitmap = wx.EmptyBitmap( 0, 0, 24 )
        
        self._DrawMain()
        self._DrawEntry()
        self._DrawReady()
        
        self._timer.Stop()
        
    
    def Enable( self ):
        
        self._captcha_challenge = ''
        self._captcha_runs_out = 0
        self._bitmap = wx.EmptyBitmap( 0, 0, 24 )
        
        self._DrawMain()
        self._DrawEntry()
        self._DrawReady()
        
        self._timer.Start( 1000, wx.TIMER_CONTINUOUS )
        
    
    def EnableWithValues( self, challenge, bitmap, captcha_runs_out, entry, ready ):
        
        if HydrusData.GetNow() > captcha_runs_out: self.Enable()
        else:
            
            self._captcha_challenge = challenge
            self._captcha_runs_out = captcha_runs_out
            self._bitmap = bitmap
            
            self._DrawMain()
            self._DrawEntry( entry )
            self._DrawReady( ready )
            
            self._timer.Start( 1000, wx.TIMER_CONTINUOUS )
            
        
    
    def EventKeyDown( self, event ):
        
        if event.KeyCode in ( wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER ): self.EventReady( None )
        else: event.Skip()
        
    
    def EventReady( self, event ): self._DrawReady( not self._ready_button.GetLabel() == 'edit' )
    
    def EventRefreshCaptcha( self, event ):
        
        javascript_string = wx.GetApp().DoHTTP( HC.GET, 'http://www.google.com/recaptcha/api/challenge?k=' + self._captcha_key )
        
        ( trash, rest ) = javascript_string.split( 'challenge : \'', 1 )
        
        ( self._captcha_challenge, trash ) = rest.split( '\'', 1 )
        
        jpeg = wx.GetApp().DoHTTP( HC.GET, 'http://www.google.com/recaptcha/api/image?c=' + self._captcha_challenge )
        
        ( os_file_handle, temp_path ) = HydrusFileHandling.GetTempPath()
        
        try:
            
            with open( temp_path, 'wb' ) as f: f.write( jpeg )
            
            self._bitmap = HydrusImageHandling.GenerateHydrusBitmap( temp_path )
            
        finally:
            
            HydrusFileHandling.CleanUpTempPath( os_file_handle, temp_path )
            
        
        self._captcha_runs_out = HydrusData.GetNow() + 5 * 60 - 15
        
        self._DrawMain()
        self._DrawEntry( '' )
        self._DrawReady( False )
        
        self._timer.Start( 1000, wx.TIMER_CONTINUOUS )
        
    
    # change this to hold (current challenge, bmp, timestamp it runs out, value, whethere ready to post)
    def GetValues( self ): return ( self._captcha_challenge, self._bitmap, self._captcha_runs_out, self._captcha_entry.GetValue(), self._ready_button.GetLabel() == 'edit' )
    
    def TIMEREvent( self, event ):
        
        if HydrusData.GetNow() > self._captcha_runs_out: self.Enable()
        else: self._DrawMain()
        
    
class Comment( wx.Panel ):
    
    def __init__( self, parent ):
        
        wx.Panel.__init__( self, parent )
        
        self._initial_comment = ''
        
        self._comment_panel = ClientGUICommon.StaticBox( self, 'comment' )
        
        self._comment = wx.TextCtrl( self._comment_panel, value = '', style = wx.TE_MULTILINE | wx.TE_READONLY, size = ( -1, 120 ) )
        
        self._comment_append = wx.TextCtrl( self._comment_panel, value = '', style = wx.TE_MULTILINE | wx.TE_PROCESS_ENTER, size = ( -1, 120 ) )
        self._comment_append.Bind( wx.EVT_KEY_UP, self.EventKeyDown )
        
        self._comment_panel.AddF( self._comment, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._comment_panel.AddF( self._comment_append, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._comment_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
    
    def _SetComment( self ):
        
        append = self._comment_append.GetValue()
        
        if self._initial_comment != '' and append != '': comment = self._initial_comment + os.linesep * 2 + append
        else: comment = self._initial_comment + append
        
        self._comment.SetValue( comment )
        
    
    def Disable( self ):
        
        self._initial_comment = ''
        
        self._comment_append.SetValue( '' )
        self._comment_append.Disable()
        
        self._SetComment()
        
    
    def EnableWithValues( self, initial, append ):
        
        self._initial_comment = initial
        
        self._comment_append.SetValue( append )
        self._comment_append.Enable()
        
        self._SetComment()
        
    
    def GetValues( self ): return ( self._initial_comment, self._comment_append.GetValue() )
    
    def EventKeyDown( self, event ):
        
        self._SetComment()
        
        event.Skip()
        
    
class ManagementPanel( wx.lib.scrolledpanel.ScrolledPanel ):
    
    def __init__( self, parent, page, page_key, file_service_key = CC.LOCAL_FILE_SERVICE_KEY, starting_from_session = False ):
        
        wx.lib.scrolledpanel.ScrolledPanel.__init__( self, parent, style = wx.BORDER_NONE | wx.VSCROLL )
        
        self.SetupScrolling()
        
        #self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
        self.SetBackgroundColour( wx.WHITE )
        
        self._page = page
        self._page_key = page_key
        self._file_service_key = file_service_key
        self._tag_service_key = CC.COMBINED_TAG_SERVICE_KEY
        self._starting_from_session = starting_from_session
        
        self._paused = False
        
        HydrusGlobals.pubsub.sub( self, 'SetSearchFocus', 'set_search_focus' )
        HydrusGlobals.pubsub.sub( self, 'Pause', 'pause' )
        HydrusGlobals.pubsub.sub( self, 'Resume', 'resume' )
        
    
    def _MakeCollect( self, sizer ):
        
        self._collect_by = ClientGUICommon.CheckboxCollect( self, self._page_key )
        
        sizer.AddF( self._collect_by, CC.FLAGS_EXPAND_PERPENDICULAR )
        
    
    def _MakeCurrentSelectionTagsBox( self, sizer ):
        
        tags_box = ClientGUICommon.StaticBoxSorterForListBoxTags( self, 'selection tags' )
        
        t = ClientGUICommon.ListBoxTagsSelectionManagementPanel( tags_box, self._page_key )
        
        tags_box.SetTagsBox( t )
        
        sizer.AddF( tags_box, CC.FLAGS_EXPAND_BOTH_WAYS )
        
    
    def _MakeSort( self, sizer ):
        
        self._sort_by = ClientGUICommon.ChoiceSort( self, self._page_key )
        
        sizer.AddF( self._sort_by, CC.FLAGS_EXPAND_PERPENDICULAR )
        
    
    def CleanBeforeDestroy( self ): pass
    
    def Pause( self, page_key ):
        
        if page_key == self._page_key: self._paused = True
        
    
    def Resume( self, page_key ):
        
        if page_key == self._page_key: self._paused = False
        
    
    def SetSearchFocus( self, page_key ): pass
    
    def TestAbleToClose( self ): pass
    
class ManagementPanelDumper( ManagementPanel ):
    
    def __init__( self, parent, page, page_key, imageboard, media_results, starting_from_session = False ):
        
        ManagementPanel.__init__( self, parent, page, page_key, starting_from_session = starting_from_session )
        
        ( self._4chan_token, pin, timeout ) = wx.GetApp().Read( '4chan_pass' )
        
        self._have_4chan_pass = timeout > HydrusData.GetNow()
        
        self._imageboard = imageboard
        
        self._current_hash = None
        
        self._dumping = False
        self._actually_dumping = False
        self._num_dumped = 0
        self._next_dump_index = 0
        self._next_dump_time = 0
        
        self._file_post_name = 'upfile'
        
        self._timer = wx.Timer( self, ID_TIMER_DUMP )
        self.Bind( wx.EVT_TIMER, self.TIMEREvent, id = ID_TIMER_DUMP )
        
        ( self._post_url, self._flood_time, self._form_fields, self._restrictions ) = self._imageboard.GetBoardInfo()
        
        # progress
        
        self._import_queue_panel = ClientGUICommon.StaticBox( self, 'import queue' )
        
        self._progress_info = wx.StaticText( self._import_queue_panel )
        
        self._progress_gauge = ClientGUICommon.Gauge( self._import_queue_panel )
        self._progress_gauge.SetRange( len( media_results ) )
        
        self._start_button = wx.Button( self._import_queue_panel, label = 'start' )
        self._start_button.Bind( wx.EVT_BUTTON, self.EventStartButton )
        
        self._import_queue_panel.AddF( self._progress_info, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._import_queue_panel.AddF( self._progress_gauge, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._import_queue_panel.AddF( self._start_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        # thread options
        
        self._thread_panel = ClientGUICommon.StaticBox( self, 'thread options' )
        
        self._thread_fields = {}
        
        gridbox = wx.FlexGridSizer( 0, 2 )
        
        gridbox.AddGrowableCol( 1, 1 )
        
        for ( name, field_type, default, editable ) in self._form_fields:
            
            if field_type in ( CC.FIELD_TEXT, CC.FIELD_THREAD_ID ): field = wx.TextCtrl( self._thread_panel, value = default )
            elif field_type == CC.FIELD_PASSWORD: field = wx.TextCtrl( self._thread_panel, value = default, style = wx.TE_PASSWORD )
            else: continue
            
            self._thread_fields[ name ] = ( field_type, field )
            
            if editable:
                
                gridbox.AddF( wx.StaticText( self._thread_panel, label = name + ':' ), CC.FLAGS_MIXED )
                gridbox.AddF( field, CC.FLAGS_EXPAND_BOTH_WAYS )
                
            else: field.Hide()
            
        
        self._thread_panel.AddF( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        # post options
        
        self._post_panel = ClientGUICommon.StaticBox( self, 'post options' )
        
        self._post_fields = {}
        
        postbox = wx.BoxSizer( wx.VERTICAL )
        
        self._post_info = wx.StaticText( self._post_panel, label = 'no file selected', style = wx.ALIGN_CENTER | wx.ST_NO_AUTORESIZE )
        
        for ( name, field_type, default, editable ) in self._form_fields:
            
            if field_type == CC.FIELD_VERIFICATION_RECAPTCHA:
                
                if self._have_4chan_pass: continue
                
                field = CaptchaControl( self._post_panel, field_type, default )
                field.Bind( CAPTCHA_FETCH_EVENT, self.EventCaptchaRefresh )
                
            elif field_type == CC.FIELD_COMMENT: field = Comment( self._post_panel )
            else: continue
            
            self._post_fields[ name ] = ( field_type, field, default )
            
            postbox.AddF( field, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        gridbox = wx.FlexGridSizer( 0, 2 )
        
        gridbox.AddGrowableCol( 1, 1 )
        
        for ( name, field_type, default, editable ) in self._form_fields:
            
            if field_type == CC.FIELD_CHECKBOX:
                
                field = wx.CheckBox( self._post_panel )
                
                field.SetValue( default == 'True' )
                
            else: continue
            
            self._post_fields[ name ] = ( field_type, field, default )
            
            gridbox.AddF( wx.StaticText( self._post_panel, label = name + ':' ), CC.FLAGS_MIXED )
            gridbox.AddF( field, CC.FLAGS_EXPAND_BOTH_WAYS )
            
        
        for ( name, field_type, default, editable ) in self._form_fields:
            
            if field_type == CC.FIELD_FILE: self._file_post_name = name
            
        
        self._post_panel.AddF( self._post_info, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._post_panel.AddF( postbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._post_panel.AddF( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        # misc
        
        self._advanced_tag_options = ClientGUICollapsible.CollapsibleOptionsTags( self, namespaces = [ 'creator', 'series', 'title', 'volume', 'chapter', 'page', 'character', 'person', 'all others' ] )
        
        # arrange stuff
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        self._MakeSort( vbox )
        
        vbox.AddF( self._import_queue_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._thread_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._post_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._advanced_tag_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._MakeCurrentSelectionTagsBox( vbox )
        
        self.SetSizer( vbox )
        
        HydrusGlobals.pubsub.sub( self, 'FocusChanged', 'focus_changed' )
        HydrusGlobals.pubsub.sub( self, 'SortedMediaPulse', 'sorted_media_pulse' )
        
        self._sorted_media_hashes = [ media_result.GetHash() for media_result in media_results ]
        
        self._hashes_to_media = { media_result.GetHash() : ClientMedia.MediaSingleton( media_result ) for media_result in media_results }
        
        self._hashes_to_dump_info = {}
        
        for ( hash, media ) in self._hashes_to_media.items():
            
            dump_status_enum = CC.DUMPER_NOT_DUMPED
            
            dump_status_string = 'not yet dumped'
            
            post_field_info = []
            
            for ( name, ( field_type, field, default ) ) in self._post_fields.items():
                
                if field_type == CC.FIELD_COMMENT:
                    
                    post_field_info.append( ( name, field_type, ( self._GetInitialComment( media ), '' ) ) )
                    
                elif field_type == CC.FIELD_CHECKBOX: post_field_info.append( ( name, field_type, default == 'True' ) )
                elif field_type == CC.FIELD_VERIFICATION_RECAPTCHA: post_field_info.append( ( name, field_type, None ) )
                
            
            self._hashes_to_dump_info[ hash ] = ( dump_status_enum, dump_status_string, post_field_info )
            
        
        self.Bind( wx.EVT_MENU, self.EventMenu )
        
        self._timer.Start( 1000, wx.TIMER_CONTINUOUS )
        
    
    def _THREADDoDump( self, hash, post_field_info, headers, body ):
        
        try:
            
            response = wx.GetApp().DoHTTP( HC.POST, self._post_url, request_headers = headers, body = body )
            
            ( status, phrase ) = ClientDownloading.Parse4chanPostScreen( response )
            
        except Exception as e:
            
            ( status, phrase ) = ( 'big error', HydrusData.ToString( e ) )
            
        
        wx.CallAfter( self.CALLBACKDoneDump, hash, post_field_info, status, phrase )
        
    
    def _FreezeCurrentMediaPostInfo( self ):
        
        ( dump_status_enum, dump_status_string, post_field_info ) = self._hashes_to_dump_info[ self._current_hash ]
        
        post_field_info = []
        
        for ( name, ( field_type, field, default ) ) in self._post_fields.items():
            
            if field_type == CC.FIELD_COMMENT: post_field_info.append( ( name, field_type, field.GetValues() ) )
            elif field_type == CC.FIELD_CHECKBOX: post_field_info.append( ( name, field_type, field.GetValue() ) )
            elif field_type == CC.FIELD_VERIFICATION_RECAPTCHA: post_field_info.append( ( name, field_type, field.GetValues() ) )
            
        
        self._hashes_to_dump_info[ self._current_hash ] = ( dump_status_enum, dump_status_string, post_field_info )
        
    
    def _GetInitialComment( self, media ):
        
        hash = media.GetHash()
        
        try: index = self._sorted_media_hashes.index( hash )
        except: return 'media removed'
        
        num_files = len( self._sorted_media_hashes )
        
        if index == 0:
            
            total_size = sum( [ m.GetSize() for m in self._hashes_to_media.values() ] )
            
            initial = 'Hydrus Network Client is starting a dump of ' + HydrusData.ToString( num_files ) + ' files, totalling ' + HydrusData.ConvertIntToBytes( total_size ) + ':' + os.linesep * 2
            
        else: initial = ''
        
        initial += HydrusData.ToString( index + 1 ) + '/' + HydrusData.ToString( num_files )
        
        advanced_tag_options = self._advanced_tag_options.GetInfo()
        
        for ( service_key, namespaces ) in advanced_tag_options.items():
            
            tags_manager = media.GetTagsManager()
            
            try: service = wx.GetApp().GetManager( 'services' ).GetService( service_key )
            except HydrusExceptions.NotFoundException: continue
            
            service_key = service.GetServiceKey()
            
            current = tags_manager.GetCurrent( service_key )
            pending = tags_manager.GetPending( service_key )
            
            tags = current.union( pending )
            
            tags_to_include = []
            
            for namespace in namespaces:
                
                if namespace == 'all others': tags_to_include.extend( [ tag for tag in tags if not True in ( tag.startswith( n ) for n in namespaces if n != 'all others' ) ] )
                else: tags_to_include.extend( [ tag for tag in tags if tag.startswith( namespace + ':' ) ] )
                
            
            initial += os.linesep * 2 + ', '.join( tags_to_include )
            
        
        return initial
        
    
    def _ShowCurrentMedia( self ):
        
        if self._current_hash is None:
            
            self._post_info.SetLabel( 'no file selected' )
            
            for ( name, ( field_type, field, default ) ) in self._post_fields.items():
                
                if field_type == CC.FIELD_CHECKBOX: field.SetValue( False )
                
                field.Disable()
                
            
        else:
            
            num_files = len( self._sorted_media_hashes )
            
            ( dump_status_enum, dump_status_string, post_field_info ) = self._hashes_to_dump_info[ self._current_hash ]
            
            index = self._sorted_media_hashes.index( self._current_hash )
            
            self._post_info.SetLabel( HydrusData.ToString( index + 1 ) + '/' + HydrusData.ToString( num_files ) + ': ' + dump_status_string )
            
            for ( name, field_type, value ) in post_field_info:
                
                ( field_type, field, default ) = self._post_fields[ name ]
                
                if field_type == CC.FIELD_COMMENT:
                    
                    ( initial, append ) = value
                    
                    field.EnableWithValues( initial, append )
                    
                elif field_type == CC.FIELD_CHECKBOX:
                    
                    field.SetValue( value )
                    field.Enable()
                    
                elif field_type == CC.FIELD_VERIFICATION_RECAPTCHA:
                    
                    if value is None: field.Enable()
                    else:
                        
                        ( challenge, bitmap, captcha_runs_out, entry, ready ) = value
                        
                        field.EnableWithValues( challenge, bitmap, captcha_runs_out, entry, ready )
                        
                    
                
            
            if dump_status_enum in ( CC.DUMPER_DUMPED_OK, CC.DUMPER_UNRECOVERABLE_ERROR ):
                
                for ( name, ( field_type, field, default ) ) in self._post_fields.items():
                    
                    if field_type == CC.FIELD_CHECKBOX: field.SetValue( False )
                    
                    field.Disable()
                    
                
            
        
    
    def _UpdatePendingInitialComments( self ):
        
        hashes_to_dump = self._sorted_media_hashes[ self._next_dump_index : ]
        
        for hash in hashes_to_dump:
            
            if hash == self._current_hash: self._FreezeCurrentMediaPostInfo()
            
            ( dump_status_enum, dump_status_string, post_field_info ) = self._hashes_to_dump_info[ hash ]
            
            new_post_field_info = []
            
            for ( name, field_type, value ) in post_field_info:
                
                if field_type == CC.FIELD_COMMENT:
                    
                    ( initial, append ) = value
                    
                    media = self._hashes_to_media[ hash ]
                    
                    initial = self._GetInitialComment( media )
                    
                    new_post_field_info.append( ( name, field_type, ( initial, append ) ) )
                    
                else: new_post_field_info.append( ( name, field_type, value ) )
                
            
            self._hashes_to_dump_info[ hash ] = ( dump_status_enum, dump_status_string, new_post_field_info )
            
            if hash == self._current_hash: self._ShowCurrentMedia()
            
        
    
    def CALLBACKDoneDump( self, hash, post_field_info, status, phrase ):
        
        self._actually_dumping = False
        
        if HC.options[ 'play_dumper_noises' ]:
            
            if status == 'success': HydrusAudioHandling.PlayNoise( 'success' )
            else: HydrusAudioHandling.PlayNoise( 'error' )
            
        
        if status == 'success':
            
            dump_status_enum = CC.DUMPER_DUMPED_OK
            dump_status_string = 'dumped ok'
            
            if hash == self._current_hash: HydrusGlobals.pubsub.pub( 'set_focus', self._page_key, None )
            
            self._next_dump_time = HydrusData.GetNow() + self._flood_time
            
            self._num_dumped += 1
            
            self._progress_gauge.SetValue( self._num_dumped )
            
            self._next_dump_index += 1
            
        elif status == 'captcha':
            
            dump_status_enum = CC.DUMPER_RECOVERABLE_ERROR
            dump_status_string = 'captcha was incorrect'
            
            self._next_dump_time = HydrusData.GetNow() + 10
            
            new_post_field_info = []
            
            for ( name, field_type, value ) in post_field_info:
                
                if field_type == CC.FIELD_VERIFICATION_RECAPTCHA: new_post_field_info.append( ( name, field_type, None ) )
                else: new_post_field_info.append( ( name, field_type, value ) )
                
                if hash == self._current_hash:
                    
                    ( field_type, field, default ) = self._post_fields[ name ]
                    
                    field.Enable()
                    
                
            
            post_field_info = new_post_field_info
            
        elif status == 'too quick':
            
            dump_status_enum = CC.DUMPER_RECOVERABLE_ERROR
            dump_status_string = ''
            
            self._progress_info.SetLabel( 'Flood limit hit, retrying.' )
            
            self._next_dump_time = HydrusData.GetNow() + self._flood_time
            
        elif status == 'big error':
            
            dump_status_enum = CC.DUMPER_UNRECOVERABLE_ERROR
            dump_status_string = ''
            
            HydrusData.ShowText( phrase )
            
            self._progress_info.SetLabel( 'error: ' + phrase )
            
            self._start_button.Disable()
            
            self._timer.Stop()
            
        elif 'Thread specified does not exist' in phrase:
            
            dump_status_enum = CC.DUMPER_UNRECOVERABLE_ERROR
            dump_status_string = ''
            
            self._progress_info.SetLabel( 'thread specified does not exist!' )
            
            self._start_button.Disable()
            
            self._timer.Stop()
            
        else:
            
            dump_status_enum = CC.DUMPER_UNRECOVERABLE_ERROR
            dump_status_string = phrase
            
            if hash == self._current_hash: HydrusGlobals.pubsub.pub( 'set_focus', self._page_key, None )
            
            self._next_dump_time = HydrusData.GetNow() + self._flood_time
            
            self._next_dump_index += 1
            
        
        self._hashes_to_dump_info[ hash ] = ( dump_status_enum, dump_status_string, post_field_info )
        
        HydrusGlobals.pubsub.pub( 'file_dumped', self._page_key, hash, dump_status_enum )
        
        if self._next_dump_index == len( self._sorted_media_hashes ):
            
            self._progress_info.SetLabel( 'done - ' + HydrusData.ToString( self._num_dumped ) + ' dumped' )
            
            self._start_button.Disable()
            
            self._timer.Stop()
            
            self._dumping = False
            
        
    
    def EventCaptchaRefresh( self, event ):
        
        try:
            
            index = self._sorted_media_hashes.index( self._current_hash )
            
            if ( ( index + 1 ) - self._next_dump_index ) * ( self._flood_time + 10 ) > 5 * 60: event.Veto()
            
        except: event.Veto()
        
    
    def EventMenu( self, event ):
        
        action = ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetAction( event.GetId() )
        
        if action is not None:
            
            ( command, data ) = action
            
            if command == 'advanced_tag_options_changed': self._UpdatePendingInitialComments()
            else: event.Skip()
            
        
    
    def EventStartButton( self, event ):
        
        if self._start_button.GetLabel() in ( 'start', 'continue' ):
            
            for ( name, ( field_type, field ) ) in self._thread_fields.items():
                
                if field_type == CC.FIELD_THREAD_ID:
                    
                    try: int( field.GetValue() )
                    except:
                        
                        # let's assume they put the url in
                        
                        value = field.GetValue()
                        
                        thread_id = value.split( '/' )[ -1 ]
                        
                        try: int( thread_id )
                        except:
                            
                            self._progress_info.SetLabel( 'set thread_id field first' )
                            
                            return
                            
                        
                        field.SetValue( thread_id )
                        
                    
                
            
            for ( field_type, field ) in self._thread_fields.values(): field.Disable()
            
            self._dumping = True
            self._start_button.SetLabel( 'pause' )
            
            if self._next_dump_time == 0: self._next_dump_time = HydrusData.GetNow() + 5
            
            # disable thread fields here
            
        else:
            
            for ( field_type, field ) in self._thread_fields.values(): field.Enable()
            
            self._dumping = False
            
            if self._num_dumped == 0: self._start_button.SetLabel( 'start' )
            else: self._start_button.SetLabel( 'continue' )
            
        
    
    def FocusChanged( self, page_key, media ):
        
        if page_key == self._page_key:
            
            if media is None: hash = None
            else: hash = media.GetHash()
            
            if hash != self._current_hash:
                
                old_hash = self._current_hash
                
                if old_hash is not None: self._FreezeCurrentMediaPostInfo()
                
                self._current_hash = hash
                
                self._ShowCurrentMedia()
                
            
        
    
    def SortedMediaPulse( self, page_key, sorted_media ):
        
        if page_key == self._page_key:
            
            self._sorted_media_hashes = [ media.GetHash() for media in sorted_media ]
            
            self._hashes_to_media = { hash : self._hashes_to_media[ hash ] for hash in self._sorted_media_hashes }
            
            new_hashes_to_dump_info = {}
            
            for ( hash, ( dump_status_enum, dump_status_string, post_field_info ) ) in self._hashes_to_dump_info.items():
                
                if hash not in self._sorted_media_hashes: continue
                
                new_post_field_info = []
                
                for ( name, field_type, value ) in post_field_info:
                    
                    if field_type == CC.FIELD_COMMENT:
                        
                        ( initial, append ) = value
                        
                        media = self._hashes_to_media[ hash ]
                        
                        initial = self._GetInitialComment( media )
                        
                        value = ( initial, append )
                        
                    
                    new_post_field_info.append( ( name, field_type, value ) )
                    
                
                new_hashes_to_dump_info[ hash ] = ( dump_status_enum, dump_status_string, new_post_field_info )
                
            
            self._hashes_to_dump_info = new_hashes_to_dump_info
            
            self._ShowCurrentMedia()
            
            if self._current_hash is None and len( self._sorted_media_hashes ) > 0:
                
                hash_to_select = self._sorted_media_hashes[0]
                
                media_to_select = self._hashes_to_media[ hash_to_select ]
                
                HydrusGlobals.pubsub.pub( 'set_focus', self._page_key, media_to_select )
                
            
        
    
    def TestAbleToClose( self ):
        
        if self._dumping:
            
            with ClientGUIDialogs.DialogYesNo( self, 'This page is still dumping. Are you sure you want to close it?' ) as dlg:
                
                if dlg.ShowModal() == wx.ID_NO: raise Exception()
                
            
        
    
    def TIMEREvent( self, event ):
        
        if self._paused: return
        
        if self._actually_dumping: return
        
        if self._dumping:
            
            time_left = self._next_dump_time - HydrusData.GetNow()
            
            if time_left < 1:
                
                try:
                    
                    hash = self._sorted_media_hashes[ self._next_dump_index ]
                    
                    wait = False
                    
                    if hash == self._current_hash: self._FreezeCurrentMediaPostInfo()
                    
                    ( dump_status_enum, dump_status_string, post_field_info ) = self._hashes_to_dump_info[ hash ]
                    
                    for ( name, field_type, value ) in post_field_info:
                        
                        if field_type == CC.FIELD_VERIFICATION_RECAPTCHA:
                            
                            if value is None:
                                
                                wait = True
                                
                                break
                                
                            else:
                                
                                ( challenge, bitmap, captcha_runs_out, entry, ready ) = value
                                
                                if HydrusData.GetNow() > captcha_runs_out or not ready:
                                    
                                    wait = True
                                    
                                    break
                                    
                                
                            
                        
                    
                    if wait: self._progress_info.SetLabel( 'waiting for captcha' )
                    else:
                        
                        self._progress_info.SetLabel( 'dumping' ) # 100% cpu time here - may or may not be desirable
                        
                        post_fields = []
                        
                        for ( name, ( field_type, field ) ) in self._thread_fields.items():
                            
                            post_fields.append( ( name, field_type, field.GetValue() ) )
                            
                        
                        for ( name, field_type, value ) in post_field_info:
                            
                            if field_type == CC.FIELD_VERIFICATION_RECAPTCHA:
                                
                                ( challenge, bitmap, captcha_runs_out, entry, ready ) = value
                                
                                post_fields.append( ( 'recaptcha_challenge_field', field_type, challenge ) )
                                post_fields.append( ( 'recaptcha_response_field', field_type, entry ) )
                                
                            elif field_type == CC.FIELD_COMMENT:
                                
                                ( initial, append ) = value
                                
                                comment = initial
                                
                                if len( append ) > 0: comment += os.linesep * 2 + append
                                
                                post_fields.append( ( name, field_type, comment ) )
                                
                            else: post_fields.append( ( name, field_type, value ) )
                            
                        
                        media = self._hashes_to_media[ hash ]
                        
                        mime = media.GetMime()
                        
                        path = ClientFiles.GetFilePath( hash, mime )
                        
                        with open( path, 'rb' ) as f: file = f.read()
                        
                        post_fields.append( ( self._file_post_name, CC.FIELD_FILE, ( hash, mime, file ) ) )
                        
                        ( ct, body ) = HydrusNetworking.GenerateDumpMultipartFormDataCTAndBody( post_fields )
                        
                        headers = {}
                        headers[ 'Content-Type' ] = ct
                        if self._have_4chan_pass: headers[ 'Cookie' ] = 'pass_enabled=1; pass_id=' + self._4chan_token
                        
                        self._actually_dumping = True
                        
                        HydrusThreading.CallToThread( self._THREADDoDump, hash, post_field_info, headers, body )
                        
                    
                except Exception as e:
                    
                    ( status, phrase ) = ( 'big error', HydrusData.ToString( e ) )
                    
                    wx.CallAfter( self.CALLBACKDoneDump, hash, post_field_info, status, phrase )
                    
                
            else: self._progress_info.SetLabel( 'dumping next file in ' + HydrusData.ToString( time_left ) + ' seconds' )
            
        else:
            
            if self._num_dumped == 0: self._progress_info.SetLabel( 'will dump to ' + self._imageboard.GetName() )
            else: self._progress_info.SetLabel( 'paused after ' + HydrusData.ToString( self._num_dumped ) + ' files dumped' )
            
        
    
class ManagementPanelImport( ManagementPanel ):
    
    def __init__( self, parent, page, page_key, starting_from_session = False ):
        
        ManagementPanel.__init__( self, parent, page, page_key, starting_from_session = starting_from_session )
        
        self._InitController()
        
        self._import_panel = ClientGUICommon.StaticBox( self, 'current file' )
        
        self._import_current_info = wx.StaticText( self._import_panel )
        self._import_gauge = ClientGUICommon.Gauge( self._import_panel )
        
        self._import_queue_panel = ClientGUICommon.StaticBox( self, 'import queue' )
        
        self._import_overall_info = wx.StaticText( self._import_queue_panel )
        self._import_queue_info = wx.StaticText( self._import_queue_panel )
        self._import_queue_gauge = ClientGUICommon.Gauge( self._import_queue_panel )
        
        self._import_pause_button = wx.Button( self._import_queue_panel, label = 'pause' )
        self._import_pause_button.Bind( wx.EVT_BUTTON, self.EventPauseImportQueue )
        self._import_pause_button.Disable()
        
        self._import_cancel_button = wx.Button( self._import_queue_panel, label = 'that\'s enough' )
        self._import_cancel_button.Bind( wx.EVT_BUTTON, self.EventCancelImportQueue )
        self._import_cancel_button.SetForegroundColour( ( 128, 0, 0 ) )
        self._import_cancel_button.Disable()
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        self._MakeSort( vbox )
        
        self._import_panel.AddF( self._import_current_info, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._import_panel.AddF( self._import_gauge, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        vbox.AddF( self._import_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        c_p_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        c_p_hbox.AddF( self._import_pause_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        c_p_hbox.AddF( self._import_cancel_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self._import_queue_panel.AddF( self._import_overall_info, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._import_queue_panel.AddF( self._import_queue_info, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._import_queue_panel.AddF( self._import_queue_gauge, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._import_queue_panel.AddF( c_p_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        vbox.AddF( self._import_queue_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._InitExtraVboxElements( vbox )
        
        self._MakeCurrentSelectionTagsBox( vbox )
        
        self.SetSizer( vbox )
        
        #
        
        self.Bind( wx.EVT_TIMER, self.TIMEREventUpdate, id = ID_TIMER_UPDATE )
        
        self._timer_update = wx.Timer( self, id = ID_TIMER_UPDATE )
        self._timer_update.Start( 100, wx.TIMER_CONTINUOUS )
        
    
    def _GenerateImportArgsGeneratorFactory( self ):
        
        raise NotImplementedError()
        
    
    def _GenerateImportQueueBuilderFactory( self ):
        
        def factory( job_key, item ):
            
            return ClientDownloading.ImportQueueBuilder( job_key, item )
            
        
        return factory
        
    
    def _InitController( self ):
        
        import_args_generator_factory = self._GenerateImportArgsGeneratorFactory()
        import_queue_builder_factory = self._GenerateImportQueueBuilderFactory()
        
        self._import_controller = ClientDownloading.ImportController( import_args_generator_factory, import_queue_builder_factory, page_key = self._page_key )
        
        self._import_controller.StartDaemon()
        
    
    def _InitExtraVboxElements( self, vbox ):
        
        pass
        
    
    def _UpdateGUI( self ):
        
        import_controller_job_key = self._import_controller.GetJobKey( 'controller' )
        import_job_key = self._import_controller.GetJobKey( 'import' )
        import_queue_job_key = self._import_controller.GetJobKey( 'import_queue' )
        import_queue_builder_job_key = self._import_controller.GetJobKey( 'import_queue_builder' )
        
        # info
        
        status_strings = []
        
        result_counts = import_controller_job_key.GetVariable( 'result_counts' )
        
        num_successful = result_counts[ CC.STATUS_SUCCESSFUL ]
        num_failed = result_counts[ CC.STATUS_FAILED ]
        num_deleted = result_counts[ CC.STATUS_DELETED ]
        num_redundant = result_counts[ CC.STATUS_REDUNDANT ]
        
        if num_successful > 0: status_strings.append( HydrusData.ToString( num_successful ) + ' successful' )
        if num_failed > 0: status_strings.append( HydrusData.ToString( num_failed ) + ' failed' )
        if num_deleted > 0: status_strings.append( HydrusData.ToString( num_deleted ) + ' already deleted' )
        if num_redundant > 0: status_strings.append( HydrusData.ToString( num_redundant ) + ' already in db' )
        
        overall_info = ', '.join( status_strings )
        
        if overall_info != self._import_overall_info.GetLabel(): self._import_overall_info.SetLabel( overall_info )
        
        import_status = import_job_key.GetVariable( 'status' )
        
        if import_status != self._import_current_info.GetLabel(): self._import_current_info.SetLabel( import_status )
        
        import_queue_status = import_queue_job_key.GetVariable( 'status' )
        
        if import_queue_status != self._import_queue_info.GetLabel(): self._import_queue_info.SetLabel( import_queue_status )
        
        # buttons
        
        if import_queue_job_key.IsPaused():
            
            if self._import_pause_button.GetLabel() != 'resume':
                
                self._import_pause_button.SetLabel( 'resume' )
                self._import_pause_button.SetForegroundColour( ( 0, 128, 0 ) )
                
            
        else:
            
            if self._import_pause_button.GetLabel() != 'pause':
                
                self._import_pause_button.SetLabel( 'pause' )
                self._import_pause_button.SetForegroundColour( ( 0, 0, 0 ) )
                
            
        
        if import_queue_job_key.IsWorking() and not import_queue_job_key.IsCancelled():
            
            self._import_pause_button.Enable()
            self._import_cancel_button.Enable()
            
        else:
            
            self._import_pause_button.Disable()
            self._import_cancel_button.Disable()
            
        
        # gauges
        
        gauge_range = import_job_key.GetVariable( 'range' )
        
        if gauge_range is None: self._import_gauge.Pulse()
        else:
            
            gauge_value = import_job_key.GetVariable( 'value' )
            
            self._import_gauge.SetRange( gauge_range )
            self._import_gauge.SetValue( gauge_value )
            
        
        queue = import_queue_builder_job_key.GetVariable( 'queue' )
        
        if len( queue ) == 0:
            
            if import_queue_builder_job_key.IsWorking(): self._import_queue_gauge.Pulse()
            else:
                
                self._import_queue_gauge.SetRange( 1 )
                self._import_queue_gauge.SetValue( 0 )
                
            
        else:
            
            queue_position = import_queue_job_key.GetVariable( 'queue_position' )
            
            self._import_queue_gauge.SetRange( len( queue ) )
            self._import_queue_gauge.SetValue( queue_position )
            
        
    
    def CleanBeforeDestroy( self ):
        
        ManagementPanel.CleanBeforeDestroy( self )
        
        self._import_controller.CleanBeforeDestroy()
        
    
    def EventCancelImportQueue( self, event ):
        
        import_queue_job_key = self._import_controller.GetJobKey( 'import_queue' )
        import_queue_builder_job_key = self._import_controller.GetJobKey( 'import_queue_builder' )
        
        import_queue_job_key.Cancel()
        import_queue_builder_job_key.Cancel()
        
        self._UpdateGUI()
        
    
    def EventPauseImportQueue( self, event ):
        
        import_queue_job_key = self._import_controller.GetJobKey( 'import_queue' )    
        
        import_queue_job_key.PauseResume()
        
        self._UpdateGUI()
        
    
    def Pause( self, page_key ):
        
        ManagementPanel.Pause( self, page_key )
        
        if page_key == self._page_key:
            
            controller_job_key = self._import_controller.GetJobKey( 'controller' )
            
            controller_job_key.Pause()
            
        
    
    def Resume( self, page_key ):
        
        ManagementPanel.Resume( self, page_key )
        
        if page_key == self._page_key:
            
            controller_job_key = self._import_controller.GetJobKey( 'controller' )
            
            controller_job_key.Resume()
            
        
    
    def TIMEREventUpdate( self, event ): self._UpdateGUI()
    
    def TestAbleToClose( self ):
        
        import_queue_job_key = self._import_controller.GetJobKey( 'import_queue' )
        
        if import_queue_job_key.IsWorking() and not import_queue_job_key.IsPaused():
            
            with ClientGUIDialogs.DialogYesNo( self, 'This page is still importing. Are you sure you want to close it?' ) as dlg:
                
                if dlg.ShowModal() == wx.ID_NO: raise Exception()
                
            
        
    
class ManagementPanelImports( ManagementPanelImport ):
    
    def _InitExtraVboxElements( self, vbox ):
        
        ManagementPanelImport._InitExtraVboxElements( self, vbox )
        
        #
        
        self._building_import_queue_panel = ClientGUICommon.StaticBox( self, 'building import queue' )
        
        self._building_import_queue_info = wx.StaticText( self._building_import_queue_panel )
        
        self._building_import_queue_pause_button = wx.Button( self._building_import_queue_panel, label = 'pause' )
        self._building_import_queue_pause_button.Bind( wx.EVT_BUTTON, self.EventPauseImportQueueBuilder )
        self._building_import_queue_pause_button.Disable()
        
        self._building_import_queue_cancel_button = wx.Button( self._building_import_queue_panel, label = 'that\'s enough' )
        self._building_import_queue_cancel_button.Bind( wx.EVT_BUTTON, self.EventCancelImportQueueBuilder )
        self._building_import_queue_cancel_button.SetForegroundColour( ( 128, 0, 0 ) )
        self._building_import_queue_cancel_button.Disable()
        
        queue_pause_buttons_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        queue_pause_buttons_hbox.AddF( self._building_import_queue_pause_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        queue_pause_buttons_hbox.AddF( self._building_import_queue_cancel_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self._building_import_queue_panel.AddF( self._building_import_queue_info, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._building_import_queue_panel.AddF( queue_pause_buttons_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        vbox.AddF( self._building_import_queue_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        self._pending_import_queues_panel = ClientGUICommon.StaticBox( self, 'pending imports' )
        
        self._pending_import_queues_listbox = wx.ListBox( self._pending_import_queues_panel, size = ( -1, 200 ) )
        
        self._up = wx.Button( self._pending_import_queues_panel, label = u'\u2191' )
        self._up.Bind( wx.EVT_BUTTON, self.EventUp )
        
        self._remove = wx.Button( self._pending_import_queues_panel, label = 'X' )
        self._remove.Bind( wx.EVT_BUTTON, self.EventRemove )
        
        self._down = wx.Button( self._pending_import_queues_panel, label = u'\u2193' )
        self._down.Bind( wx.EVT_BUTTON, self.EventDown )
        
        self._new_queue_input = wx.TextCtrl( self._pending_import_queues_panel, style = wx.TE_PROCESS_ENTER )
        self._new_queue_input.Bind( wx.EVT_KEY_DOWN, self.EventKeyDown )
        
        self._get_tags_if_redundant = wx.CheckBox( self._pending_import_queues_panel, label = 'get tags even if file already in db' )
        self._get_tags_if_redundant.SetValue( False )
        self._get_tags_if_redundant.Hide()
        
        self._file_limit = ClientGUICommon.NoneableSpinCtrl( self._pending_import_queues_panel, 'file limit', none_phrase = 'no limit', min = 1, max = 1000000 )
        self._file_limit.SetValue( 500 )
        
        queue_buttons_vbox = wx.BoxSizer( wx.VERTICAL )
        
        queue_buttons_vbox.AddF( self._up, CC.FLAGS_MIXED )
        queue_buttons_vbox.AddF( self._remove, CC.FLAGS_MIXED )
        queue_buttons_vbox.AddF( self._down, CC.FLAGS_MIXED )
        
        queue_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        queue_hbox.AddF( self._pending_import_queues_listbox, CC.FLAGS_EXPAND_BOTH_WAYS )
        queue_hbox.AddF( queue_buttons_vbox, CC.FLAGS_MIXED )
        
        self._pending_import_queues_panel.AddF( queue_hbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        self._pending_import_queues_panel.AddF( self._new_queue_input, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._pending_import_queues_panel.AddF( self._get_tags_if_redundant, CC.FLAGS_CENTER )
        self._pending_import_queues_panel.AddF( self._file_limit, CC.FLAGS_CENTER )
        
        vbox.AddF( self._pending_import_queues_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self._advanced_import_options = ClientGUICollapsible.CollapsibleOptionsImportFiles( self )
        
        vbox.AddF( self._advanced_import_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        wx.CallAfter( self._new_queue_input.SelectAll )
        
    
    def _UpdateGUI( self ):
        
        ManagementPanelImport._UpdateGUI( self )
        
        import_job_key = self._import_controller.GetJobKey( 'import' )
        import_queue_job_key = self._import_controller.GetJobKey( 'import_queue' )
        import_queue_builder_job_key = self._import_controller.GetJobKey( 'import_queue_builder' )
        
        # info
        
        import_queue_builder_status = import_queue_builder_job_key.GetVariable( 'status' )
        
        if import_queue_builder_status != self._building_import_queue_info.GetLabel(): self._building_import_queue_info.SetLabel( import_queue_builder_status )
        
        # buttons
        
        #
        
        if import_queue_builder_job_key.IsPaused():
            
            if self._building_import_queue_pause_button.GetLabel() != 'resume':
                
                self._building_import_queue_pause_button.SetLabel( 'resume' )
                self._building_import_queue_pause_button.SetForegroundColour( ( 0, 128, 0 ) )
                
            
        else:
            
            if self._building_import_queue_pause_button.GetLabel() != 'pause':
                
                self._building_import_queue_pause_button.SetLabel( 'pause' )
                self._building_import_queue_pause_button.SetForegroundColour( ( 0, 0, 0 ) )
                
            
        
        if import_queue_builder_job_key.IsWorking() and not import_queue_job_key.IsCancelled():
            
            self._building_import_queue_pause_button.Enable()
            self._building_import_queue_cancel_button.Enable()
            
        else:
            
            self._building_import_queue_pause_button.Disable()
            self._building_import_queue_cancel_button.Disable()
            
        
        # gauge
        
        gauge_range = import_job_key.GetVariable( 'range' )
        
        if gauge_range is None: self._import_gauge.Pulse()
        else:
            
            gauge_value = import_job_key.GetVariable( 'value' )
            
            self._import_gauge.SetRange( gauge_range )
            self._import_gauge.SetValue( gauge_value )
            
        
        # pending import queues
        
        pending_import_queue_jobs = self._import_controller.GetPendingImportQueueJobs()
        
        if pending_import_queue_jobs != self._pending_import_queues_listbox.GetItems():
            
            pending_import_queue_strings = [ query for ( query, get_tags_if_redundant, file_limit ) in pending_import_queue_jobs ]
            
            self._pending_import_queues_listbox.SetItems( pending_import_queue_strings )
            
        
    
    def GetAdvancedImportOptions( self ): return self._advanced_import_options.GetInfo()
    
    def EventCancelImportQueueBuilder( self, event ):
        
        import_queue_builder_job_key = self._import_controller.GetJobKey( 'import_queue_builder' )
        
        import_queue_builder_job_key.Cancel()
        
        self._UpdateGUI()
        
    
    def EventKeyDown( self, event ):
        
        if event.KeyCode in ( wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER ):
            
            s = self._new_queue_input.GetValue()
            
            if s != '':
                
                get_tags_if_redundant = self._get_tags_if_redundant.GetValue()
                file_limit = self._file_limit.GetValue()
                
                self._import_controller.PendImportQueueJob( ( s, get_tags_if_redundant, file_limit ) )
                
                self._UpdateGUI()
                
                self._new_queue_input.SetValue( '' )
                
            
        else: event.Skip()
        
    
    def EventPauseImportQueueBuilder( self, event ):
        
        import_queue_builder_job_key = self._import_controller.GetJobKey( 'import_queue_builder' )
        
        import_queue_builder_job_key.PauseResume()
        
        self._UpdateGUI()
        
    
    def EventUp( self, event ):
        
        selection = self._pending_import_queues_listbox.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            if selection > 0:
                
                s = self._pending_import_queues_listbox.GetString( selection )
                
                self._import_controller.MovePendingImportQueueJobUp( s )
                
                self._UpdateGUI()
                
                self._pending_import_queues_listbox.Select( selection - 1 )
                
            
        
    
    def EventRemove( self, event ):
        
        selection = self._pending_import_queues_listbox.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            s = self._pending_import_queues_listbox.GetString( selection )
            
            self._import_controller.RemovePendingImportQueueJob( s )
            
            self._UpdateGUI()
            
        
    
    def EventDown( self, event ):
        
        selection = self._pending_import_queues_listbox.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            if selection + 1 < self._pending_import_queues_listbox.GetCount():
                
                s = self._pending_import_queues_listbox.GetString( selection )
                
                self._import_controller.MovePendingImportQueueJobDown( s )
                
                self._UpdateGUI()
                
                self._pending_import_queues_listbox.Select( selection + 1 )
                
            
        
    
    def SetSearchFocus( self, page_key ):
        
        if page_key == self._page_key: self._new_queue_input.SetFocus()
        
    
class ManagementPanelImportsGallery( ManagementPanelImports ):
    
    def __init__( self, parent, page, page_key, site_type, gallery_type, starting_from_session = False ):
        
        self._site_type = site_type
        self._gallery_type = gallery_type
        
        ManagementPanelImports.__init__( self, parent, page, page_key, starting_from_session = starting_from_session )
        
    
    def _GenerateImportArgsGeneratorFactory( self ):
        
        def factory( job_key, item ):
            
            advanced_import_options = HydrusThreading.CallBlockingToWx( self.GetAdvancedImportOptions )
            
            advanced_tag_options = HydrusThreading.CallBlockingToWx( self.GetAdvancedTagOptions )
            
            gallery_parsers_factory = self._GetGalleryParsersFactory()
            
            return ClientDownloading.ImportArgsGeneratorGallery( job_key, item, advanced_import_options, advanced_tag_options, gallery_parsers_factory )
            
        
        return factory
        
    
    def _GenerateImportQueueBuilderFactory( self ):
        
        def factory( job_key, item ):
            
            gallery_parsers_factory = self._GetGalleryParsersFactory()
            
            return ClientDownloading.ImportQueueBuilderGallery( job_key, item, gallery_parsers_factory )
            
        
        return factory
        
    
    def _GetGalleryParsersFactory( self ):
        
        if self._site_type == HC.SITE_TYPE_BOORU:
            
            def gallery_parsers_factory( raw_tags ):
                
                booru = self._gallery_type
                tags = raw_tags.split( ' ' )
                
                return ( ClientDownloading.GalleryParserBooru( booru, tags ), )
                
            
        elif self._site_type == HC.SITE_TYPE_DEVIANT_ART:
            
            if self._gallery_type == 'artist':
                
                def gallery_parsers_factory( artist ):
                    
                    return ( ClientDownloading.GalleryParserDeviantArt( artist ), )
                    
                
            
        elif self._site_type == HC.SITE_TYPE_GIPHY:
            
            def gallery_parsers_factory( tag ):
                
                return ( ClientDownloading.GalleryParserGiphy( tag ), )
                
            
        elif self._site_type == HC.SITE_TYPE_HENTAI_FOUNDRY:
            
            if self._gallery_type == 'artist':
                
                def gallery_parsers_factory( artist ):
                    
                    advanced_hentai_foundry_options = HydrusThreading.CallBlockingToWx( self.GetAdvancedHentaiFoundryOptions )
                    
                    pictures_gallery_parser = ClientDownloading.GalleryParserHentaiFoundry( 'artist pictures', artist, advanced_hentai_foundry_options )
                    scraps_gallery_parser = ClientDownloading.GalleryParserHentaiFoundry( 'artist scraps', artist, advanced_hentai_foundry_options )
                    
                    return ( pictures_gallery_parser, scraps_gallery_parser )
                    
                
            elif self._gallery_type == 'tags':
                
                def gallery_parsers_factory( raw_tags ):
                    
                    advanced_hentai_foundry_options = HydrusThreading.CallBlockingToWx( self.GetAdvancedHentaiFoundryOptions )
                    
                    tags = raw_tags.split( ' ' )
                    
                    return ( ClientDownloading.GalleryParserHentaiFoundry( 'tags', tags, advanced_hentai_foundry_options ), )
                    
                
            
        elif self._site_type == HC.SITE_TYPE_NEWGROUNDS:
            
            def gallery_parsers_factory( artist ):
                
                return ( ClientDownloading.GalleryParserNewgrounds( artist ), )
                
            
        elif self._site_type == HC.SITE_TYPE_PIXIV:
            
            if self._gallery_type in ( 'artist', 'artist_id' ):
                
                def gallery_parsers_factory( artist_id ):
                    
                    return ( ClientDownloading.GalleryParserPixiv( 'artist_id', artist_id ), )
                    
                
            elif self._gallery_type == 'tag':
                
                def gallery_parsers_factory( tag ):
                    
                    return ( ClientDownloading.GalleryParserPixiv( 'tags', tag ), )
                    
                
            
        elif self._site_type == HC.SITE_TYPE_TUMBLR:
            
            def gallery_parsers_factory( username ):
                
                return ( ClientDownloading.GalleryParserTumblr( username ), )
                
            
        
        return gallery_parsers_factory
        
    
    def _InitExtraVboxElements( self, vbox ):
        
        ManagementPanelImports._InitExtraVboxElements( self, vbox )
        
        #
        
        if self._site_type == HC.SITE_TYPE_BOORU:
            
            booru = self._gallery_type
            
            name = booru.GetName()
            
            namespaces = booru.GetNamespaces()
            initial_search_value = 'search tags'
            
            ato = ClientData.GetDefaultAdvancedTagOptions( ( HC.SITE_TYPE_BOORU, name ) )
            
        elif self._site_type == HC.SITE_TYPE_DEVIANT_ART:
            
            if self._gallery_type == 'artist':
                
                namespaces = [ 'creator', 'title' ]
                initial_search_value = 'artist username'
                
            
            ato = ClientData.GetDefaultAdvancedTagOptions( HC.SITE_TYPE_DEVIANT_ART )
            
        elif self._site_type == HC.SITE_TYPE_GIPHY:
            
            namespaces = [ '' ]
    
            initial_search_value = 'search tag'
            
            ato = ClientData.GetDefaultAdvancedTagOptions( HC.SITE_TYPE_GIPHY )
            
        elif self._site_type == HC.SITE_TYPE_HENTAI_FOUNDRY:
            
            namespaces = [ 'creator', 'title', '' ]
            
            if self._gallery_type == 'artist': initial_search_value = 'artist username'
            elif self._gallery_type == 'tags': initial_search_value = 'search tags'
            
            ato = ClientData.GetDefaultAdvancedTagOptions( HC.SITE_TYPE_HENTAI_FOUNDRY )
            
        elif self._site_type == HC.SITE_TYPE_NEWGROUNDS:
            
            namespaces = [ 'creator', 'title', '' ]
            initial_search_value = 'artist username'
            
            ato = ClientData.GetDefaultAdvancedTagOptions( HC.SITE_TYPE_NEWGROUNDS )
            
        elif self._site_type == HC.SITE_TYPE_PIXIV:
            
            namespaces = [ 'creator', 'title', '' ]
            
            if self._gallery_type in ( 'artist', 'artist_id' ): initial_search_value = 'numerical artist id'
            elif self._gallery_type == 'tag': initial_search_value = 'search tag'
            
            ato = ClientData.GetDefaultAdvancedTagOptions( HC.SITE_TYPE_PIXIV )
            
        elif self._site_type == HC.SITE_TYPE_TUMBLR:
            
            namespaces = [ '' ]
            initial_search_value = 'username'
            
            ato = ClientData.GetDefaultAdvancedTagOptions( HC.SITE_TYPE_TUMBLR )
            
        
        self._new_queue_input.SetValue( initial_search_value )
        
        #
        
        self._advanced_tag_options = ClientGUICollapsible.CollapsibleOptionsTags( self, namespaces )
        self._advanced_tag_options.SetInfo( ato )
        
        if self._site_type == HC.SITE_TYPE_HENTAI_FOUNDRY:
            
            self._advanced_hentai_foundry_options = ClientGUICollapsible.CollapsibleOptionsHentaiFoundry( self )
            
            vbox.AddF( self._advanced_hentai_foundry_options, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        vbox.AddF( self._advanced_tag_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        
    
    def GetAdvancedHentaiFoundryOptions( self ): return self._advanced_hentai_foundry_options.GetInfo()
    
    def GetAdvancedTagOptions( self ): return self._advanced_tag_options.GetInfo()
    
class ManagementPanelImportsURL( ManagementPanelImports ):
    
    def _GenerateImportArgsGeneratorFactory( self ):
        
        def factory( job_key, item ):
            
            advanced_import_options = HydrusThreading.CallBlockingToWx( self.GetAdvancedImportOptions )
            
            return ClientDownloading.ImportArgsGeneratorURLs( job_key, item, advanced_import_options )
            
        
        return factory
        
    
    def _GenerateImportQueueBuilderFactory( self ):
        
        def factory( job_key, item ):
            
            return ClientDownloading.ImportQueueBuilderURLs( job_key, item )
            
        
        return factory
        
    
    def _InitExtraVboxElements( self, vbox ):
        
        ManagementPanelImports._InitExtraVboxElements( self, vbox )
        
        self._building_import_queue_pause_button.Hide()
        self._building_import_queue_cancel_button.Hide()
        self._get_tags_if_redundant.Hide()
        self._file_limit.Hide()
        
    
class ManagementPanelImportHDD( ManagementPanelImport ):
    
    def __init__( self, parent, page, page_key, paths_info, advanced_import_options, paths_to_tags, delete_after_success, starting_from_session = False ):
        
        self._paths_info = paths_info
        self._advanced_import_options = advanced_import_options
        self._paths_to_tags = paths_to_tags
        self._delete_after_success = delete_after_success
        
        ManagementPanelImport.__init__( self, parent, page, page_key, starting_from_session = starting_from_session )
        
        self._import_controller.PendImportQueueJob( self._paths_info )
        
    
    def _GenerateImportArgsGeneratorFactory( self ):
        
        def factory( job_key, item ):
            
            return ClientDownloading.ImportArgsGeneratorHDD( job_key, item, self._advanced_import_options, self._paths_to_tags, self._delete_after_success )
            
        
        return factory
        
    
    def _InitExtraVboxElements( self, vbox ):
        
        ManagementPanelImport._InitExtraVboxElements( self, vbox )
        
        self._import_gauge.Hide()
        self._import_cancel_button.Hide()
        
    
class ManagementPanelImportThreadWatcher( ManagementPanelImport ):
    
    def _GenerateImportArgsGeneratorFactory( self ):
        
        def factory( job_key, item ):
            
            advanced_import_options = HydrusThreading.CallBlockingToWx( self.GetAdvancedImportOptions )
            advanced_tag_options = HydrusThreading.CallBlockingToWx( self.GetAdvancedTagOptions )
            
            # fourchan_board should be on the job_key or whatever. it is stuck on initial queue generation
            # we should not be getting it from the management_panel
            # we should have access to this info from the job_key or w/e
            
            return ClientDownloading.ImportArgsGeneratorThread( job_key, item, advanced_import_options, advanced_tag_options )
            
        
        return factory
        
    
    def _GenerateImportQueueBuilderFactory( self ):
        
        def factory( job_key, item ):
            
            return ClientDownloading.ImportQueueBuilderThread( job_key, item )
            
        
        return factory
        
    
    def _InitExtraVboxElements( self, vbox ):
        
        ManagementPanelImport._InitExtraVboxElements( self, vbox )
        
        self._import_cancel_button.Hide()
        
        #
        
        self._thread_panel = ClientGUICommon.StaticBox( self, 'thread checker' )
        
        self._thread_info = wx.StaticText( self._thread_panel, label = 'enter a 4chan thread url' )
        
        ( times_to_check, check_period ) = HC.options[ 'thread_checker_timings' ]
        
        self._thread_times_to_check = wx.SpinCtrl( self._thread_panel, size = ( 60, -1 ), min = 0, max = 100 )
        self._thread_times_to_check.SetValue( times_to_check )
        self._thread_times_to_check.Bind( wx.EVT_SPINCTRL, self.EventThreadVariable )
        
        self._thread_check_period = wx.SpinCtrl( self._thread_panel, size = ( 100, -1 ), min = 30, max = 86400 )
        self._thread_check_period.SetValue( check_period )
        self._thread_check_period.Bind( wx.EVT_SPINCTRL, self.EventThreadVariable )
        
        self._thread_input = wx.TextCtrl( self._thread_panel, style = wx.TE_PROCESS_ENTER )
        self._thread_input.Bind( wx.EVT_KEY_DOWN, self.EventKeyDown )
        
        self._thread_pause_button = wx.Button( self._thread_panel, label = 'pause' )
        self._thread_pause_button.Bind( wx.EVT_BUTTON, self.EventPauseImportQueueBuilder )
        
        self._thread_manual_refresh_button = wx.Button( self._thread_panel, label = 'check now' )
        self._thread_manual_refresh_button.Bind( wx.EVT_BUTTON, self.EventManualRefresh )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.AddF( wx.StaticText( self._thread_panel, label = 'check ' ), CC.FLAGS_MIXED )
        hbox.AddF( self._thread_times_to_check, CC.FLAGS_MIXED )
        hbox.AddF( wx.StaticText( self._thread_panel, label = ' more times, every ' ), CC.FLAGS_MIXED )
        hbox.AddF( self._thread_check_period, CC.FLAGS_MIXED )
        hbox.AddF( wx.StaticText( self._thread_panel, label = ' seconds' ), CC.FLAGS_MIXED )
        
        button_box = wx.BoxSizer( wx.HORIZONTAL )
        
        button_box.AddF( self._thread_pause_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        button_box.AddF( self._thread_manual_refresh_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self._thread_panel.AddF( self._thread_info, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._thread_panel.AddF( self._thread_input, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._thread_panel.AddF( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._thread_panel.AddF( button_box, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        vbox.AddF( self._thread_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        self._advanced_tag_options = ClientGUICollapsible.CollapsibleOptionsTags( self, namespaces = [ 'filename' ] )
        
        vbox.AddF( self._advanced_tag_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._advanced_import_options = ClientGUICollapsible.CollapsibleOptionsImportFiles( self )
        
        vbox.AddF( self._advanced_import_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        
    
    def _SetThreadVariables( self ):
        
        import_queue_builder_job_key = self._import_controller.GetJobKey( 'import_queue_builder' )
        
        thread_time = self._thread_check_period.GetValue()
        thread_times_to_check = self._thread_times_to_check.GetValue()
        
        import_queue_builder_job_key.SetVariable( 'manual_refresh', False )
        import_queue_builder_job_key.SetVariable( 'thread_time', thread_time )
        import_queue_builder_job_key.SetVariable( 'thread_times_to_check', thread_times_to_check )
        
    
    def _UpdateGUI( self ):
        
        ManagementPanelImport._UpdateGUI( self )
        
        import_job_key = self._import_controller.GetJobKey( 'import' )
        import_queue_builder_job_key = self._import_controller.GetJobKey( 'import_queue_builder' )
        
        # thread_info
        
        status = import_queue_builder_job_key.GetVariable( 'status' )
        
        if status != self._thread_info.GetLabel(): self._thread_info.SetLabel( status )
        
        # button
        
        if import_queue_builder_job_key.IsWorking():
            
            self._thread_pause_button.Enable()
            
            if import_queue_builder_job_key.IsPaused():
                
                self._thread_pause_button.SetLabel( 'resume' )
                self._thread_pause_button.SetForegroundColour( ( 0, 128, 0 ) )
                
            else:
                
                self._thread_pause_button.SetLabel( 'pause' )
                self._thread_pause_button.SetForegroundColour( ( 0, 0, 0 ) )
                
            
        else: self._thread_pause_button.Disable()
        
        # times to check
        
        try:
            
            thread_times_to_check = import_queue_builder_job_key.GetVariable( 'thread_times_to_check' )
            
            self._thread_times_to_check.SetValue( thread_times_to_check )
            
        except: self._SetThreadVariables()
        
        try:
            
            manual_refresh = import_queue_builder_job_key.GetVariable( 'manual_refresh' )
            
            if not import_queue_builder_job_key.IsWorking() or manual_refresh: self._thread_manual_refresh_button.Disable()
            else: self._thread_manual_refresh_button.Enable()
            
        except: self._SetThreadVariables()
        
    
    def EventKeyDown( self, event ):
        
        if event.KeyCode in ( wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER ):
            
            self._SetThreadVariables()
            
            url = self._thread_input.GetValue()
            
            if url == '': return
            
            try:
                
                try:
                    
                    parse_result = urlparse.urlparse( url )
                    
                    host = parse_result.hostname
                    
                    request = parse_result.path
                    
                    if host is None or request is None: raise Exception()
                    
                except: raise Exception ( 'Could not understand that url!' )
                
                is_4chan = '4chan.org' in host
                is_8chan = '8chan.co' in host or '8ch.net' in host
                
                if not ( is_4chan or is_8chan ): raise Exception( 'This only works for 4chan and 8chan right now!' )
                
                try:
                    
                    # 4chan
                    # /asp/thread/382059/post-your-favourite-martial-arts-video-if-martin
                    # http://a.4cdn.org/asp/thread/382059.json
                    # http://i.4cdn.org/asp/ for images
                    
                    # 8chan
                    # /v/res/406061.html
                    # http://8chan.co/v/res/406061.json
                    # http://8chan.co/v/src/ for images
                    
                    if is_4chan:
                        
                        ( board, rest_of_request ) = request[1:].split( '/thread/', 1 )
                        
                        if '/' in rest_of_request: ( thread_id, gumpf ) = rest_of_request.split( '/' )
                        else: thread_id = rest_of_request
                        
                        json_url = 'http://a.4cdn.org/' + board + '/thread/' + thread_id + '.json'
                        image_base = 'http://i.4cdn.org/' + board + '/'
                        
                    elif is_8chan:
                        
                        ( board, rest_of_request ) = request[1:].split( '/res/', 1 )
                        
                        json_url = url[:-4] + 'json'
                        image_base = 'http://8ch.net/' + board + '/src/'
                        
                    
                except: raise Exception( 'Could not understand the board or thread id!' )
                
            except Exception as e:
                
                import_queue_builder_job_key = self._import_controller.GetJobKey( 'import_queue_builder' )
                
                import_queue_builder_job_key.SetVariable( 'status', HydrusData.ToString( e ) )
                
                HydrusData.ShowException( e )
                
                return
                
            
            self._thread_input.Disable()
            
            self._SetThreadVariables()
            
            self._import_controller.PendImportQueueJob( ( json_url, image_base ) )
            
        else: event.Skip()
        
    
    def EventManualRefresh( self, event ):
        
        import_queue_builder_job_key = self._import_controller.GetJobKey( 'import_queue_builder' )
        
        import_queue_builder_job_key.SetVariable( 'manual_refresh', True )
        
        self._thread_manual_refresh_button.Disable()
        
    
    def EventPauseImportQueueBuilder( self, event ):
        
        import_queue_builder_job_key = self._import_controller.GetJobKey( 'import_queue_builder' )
        
        import_queue_builder_job_key.PauseResume()
        
        self._UpdateGUI()
        
    
    def EventThreadVariable( self, event ): self._SetThreadVariables()
    
    def GetAdvancedImportOptions( self ): return self._advanced_import_options.GetInfo()
    
    def GetAdvancedTagOptions( self ): return self._advanced_tag_options.GetInfo()
    
    def SetSearchFocus( self, page_key ):
        
        if page_key == self._page_key: self._thread_input.SetFocus()
        
    
    def TestAbleToClose( self ):
        
        import_queue_builder_position_job_key = self._import_controller.GetJobKey( 'import_queue_builder' )
        
        if self._thread_times_to_check.GetValue() > 0 and import_queue_builder_position_job_key.IsWorking() and not import_queue_builder_position_job_key.IsPaused():
            
            with ClientGUIDialogs.DialogYesNo( self, 'This page is still importing. Are you sure you want to close it?' ) as dlg:
                
                if dlg.ShowModal() == wx.ID_NO: raise Exception()
                
            
        
    
class ManagementPanelPetitions( ManagementPanel ):
    
    def __init__( self, parent, page, page_key, file_service_key, petition_service_key, starting_from_session = False ):
        
        self._petition_service_key = petition_service_key
        
        ManagementPanel.__init__( self, parent, page, page_key, file_service_key, starting_from_session = starting_from_session )
        
        self._service = wx.GetApp().GetManager( 'services' ).GetService( self._petition_service_key )
        self._can_ban = self._service.GetInfo( 'account' ).HasPermission( HC.MANAGE_USERS )
        
        self._num_petitions = None
        self._current_petition = None
        
        self._petitions_info_panel = ClientGUICommon.StaticBox( self, 'petitions info' )
        
        self._num_petitions_text = wx.StaticText( self._petitions_info_panel )
        
        refresh_num_petitions = wx.Button( self._petitions_info_panel, label = 'refresh' )
        refresh_num_petitions.Bind( wx.EVT_BUTTON, self.EventRefreshNumPetitions )
        
        self._get_petition = wx.Button( self._petitions_info_panel, label = 'get petition' )
        self._get_petition.Bind( wx.EVT_BUTTON, self.EventGetPetition )
        self._get_petition.Disable()
        
        self._petition_panel = ClientGUICommon.StaticBox( self, 'petition' )
        
        self._petition_info_text_ctrl = wx.TextCtrl( self._petition_panel, style = wx.TE_READONLY | wx.TE_MULTILINE )
        
        self._approve = wx.Button( self._petition_panel, label = 'approve' )
        self._approve.Bind( wx.EVT_BUTTON, self.EventApprove )
        self._approve.SetForegroundColour( ( 0, 128, 0 ) )
        self._approve.Disable()
        
        self._deny = wx.Button( self._petition_panel, label = 'deny' )
        self._deny.Bind( wx.EVT_BUTTON, self.EventDeny )
        self._deny.SetForegroundColour( ( 128, 0, 0 ) )
        self._deny.Disable()
        
        self._modify_petitioner = wx.Button( self._petition_panel, label = 'modify petitioner' )
        self._modify_petitioner.Bind( wx.EVT_BUTTON, self.EventModifyPetitioner )
        self._modify_petitioner.Disable()
        if not self._can_ban: self._modify_petitioner.Hide()
        
        num_petitions_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        num_petitions_hbox.AddF( self._num_petitions_text, CC.FLAGS_EXPAND_BOTH_WAYS )
        num_petitions_hbox.AddF( refresh_num_petitions, CC.FLAGS_MIXED )
        
        self._petitions_info_panel.AddF( num_petitions_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._petitions_info_panel.AddF( self._get_petition, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        p_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        p_hbox.AddF( self._approve, CC.FLAGS_EXPAND_BOTH_WAYS )
        p_hbox.AddF( self._deny, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self._petition_panel.AddF( self._petition_info_text_ctrl, CC.FLAGS_EXPAND_BOTH_WAYS )
        self._petition_panel.AddF( p_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._petition_panel.AddF( self._modify_petitioner, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        self._MakeSort( vbox )
        self._MakeCollect( vbox )
        
        vbox.AddF( self._petitions_info_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._petition_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self._MakeCurrentSelectionTagsBox( vbox )
        
        self.SetSizer( vbox )
        
        wx.CallAfter( self.EventRefreshNumPetitions, None )
        
        HydrusGlobals.pubsub.sub( self, 'RefreshQuery', 'refresh_query' )
        
    
    def _DrawCurrentPetition( self ):
        
        if self._current_petition is None:
            
            self._petition_info_text_ctrl.SetValue( '' )
            self._approve.Disable()
            self._deny.Disable()
            
            if self._can_ban: self._modify_petitioner.Disable()
            
            panel = ClientGUIMedia.MediaPanelNoQuery( self._page, self._page_key, self._file_service_key )
            
        else:
            
            self._petition_info_text_ctrl.SetValue( self._current_petition.GetPetitionString() )
            self._approve.Enable()
            self._deny.Enable()
            
            if self._can_ban: self._modify_petitioner.Enable()
            
            with wx.BusyCursor(): media_results = wx.GetApp().Read( 'media_results', self._file_service_key, self._current_petition.GetHashes() )
            
            panel = ClientGUIMedia.MediaPanelThumbnails( self._page, self._page_key, self._file_service_key, media_results )
            
            panel.Collect( self._page_key, self._collect_by.GetChoice() )
            
            panel.Sort( self._page_key, self._sort_by.GetChoice() )
            
        
        HydrusGlobals.pubsub.pub( 'swap_media_panel', self._page_key, panel )
        
    
    def _DrawNumPetitions( self ):
        
        self._num_petitions_text.SetLabel( HydrusData.ConvertIntToPrettyString( self._num_petitions ) + ' petitions' )
        
        if self._num_petitions > 0: self._get_petition.Enable()
        else: self._get_petition.Disable()
        
    
    def EventApprove( self, event ):
        
        update = self._current_petition.GetApproval()
        
        self._service.Request( HC.POST, 'content_update_package', { 'update' : update } )
        
        wx.GetApp().Write( 'content_updates', { self._petition_service_key : update.GetContentUpdates( for_client = True ) } )
        
        self._current_petition = None
        
        self._DrawCurrentPetition()
        
        self.EventRefreshNumPetitions( event )
        
    
    def EventDeny( self, event ):
        
        update = self._current_petition.GetDenial()
        
        self._service.Request( HC.POST, 'content_update_package', { 'update' : update } )
        
        self._current_petition = None
        
        self._DrawCurrentPetition()
        
        self.EventRefreshNumPetitions( event )
        
    
    def EventGetPetition( self, event ):
        
        try:
            
            response = self._service.Request( HC.GET, 'petition' )
            
            self._current_petition = response[ 'petition' ]
            
            self._DrawCurrentPetition()
            
        except:
            
            wx.MessageBox( traceback.format_exc() )
            
            self._current_petition = None
            
            self._DrawCurrentPetition()
            
        
    
    def EventModifyPetitioner( self, event ):
        
        with ClientGUIDialogs.DialogModifyAccounts( self, self._petition_service_key, ( self._current_petition.GetPetitionerIdentifier(), ) ) as dlg: dlg.ShowModal()
        
    
    def EventRefreshNumPetitions( self, event ):
        
        self._num_petitions_text.SetLabel( u'Fetching\u2026' )
        
        try:
            
            response = self._service.Request( HC.GET, 'num_petitions' )
            
            self._num_petitions = response[ 'num_petitions' ]
            
            self._DrawNumPetitions()
            
            if self._num_petitions > 0: self.EventGetPetition( event )
            
        except Exception as e:
            
            self._num_petitions_text.SetLabel( HydrusData.ToString( e ) )
            
        
    
    def RefreshQuery( self, page_key ):
        
        if page_key == self._page_key: self._DrawCurrentPetition()
        
    
class ManagementPanelQuery( ManagementPanel ):
    
    def __init__( self, parent, page, page_key, file_service_key, show_search = True, initial_predicates = None, starting_from_session = False ):
        
        if initial_predicates is None: initial_predicates = []
        
        ManagementPanel.__init__( self, parent, page, page_key, file_service_key, starting_from_session = starting_from_session )
        
        self._query_key = HydrusData.JobKey( cancellable = True )
        self._synchronised = True
        self._include_current_tags = True
        self._include_pending_tags = True
        
        self._show_search = show_search
        
        if self._show_search:
            
            self._search_panel = ClientGUICommon.StaticBox( self, 'search' )
            
            self._current_predicates_box = ClientGUICommon.ListBoxTagsPredicates( self._search_panel, self._page_key, initial_predicates )
            
            self._searchbox = ClientGUICommon.AutoCompleteDropdownTagsRead( self._search_panel, self._page_key, self._file_service_key, CC.COMBINED_TAG_SERVICE_KEY, self._page.GetMedia )
            
            self._search_panel.AddF( self._current_predicates_box, CC.FLAGS_EXPAND_PERPENDICULAR )
            self._search_panel.AddF( self._searchbox, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        self._MakeSort( vbox )
        self._MakeCollect( vbox )
        
        if self._show_search: vbox.AddF( self._search_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._MakeCurrentSelectionTagsBox( vbox )
        
        self.SetSizer( vbox )
        
        if len( initial_predicates ) > 0 and not starting_from_session: wx.CallAfter( self._DoQuery )
        
        HydrusGlobals.pubsub.sub( self, 'AddMediaResultsFromQuery', 'add_media_results_from_query' )
        HydrusGlobals.pubsub.sub( self, 'AddPredicate', 'add_predicate' )
        HydrusGlobals.pubsub.sub( self, 'ChangeFileRepositoryPubsub', 'change_file_repository' )
        HydrusGlobals.pubsub.sub( self, 'ChangeTagRepositoryPubsub', 'change_tag_repository' )
        HydrusGlobals.pubsub.sub( self, 'IncludeCurrent', 'notify_include_current' )
        HydrusGlobals.pubsub.sub( self, 'IncludePending', 'notify_include_pending' )
        HydrusGlobals.pubsub.sub( self, 'SearchImmediately', 'notify_search_immediately' )
        HydrusGlobals.pubsub.sub( self, 'ShowQuery', 'file_query_done' )
        HydrusGlobals.pubsub.sub( self, 'RefreshQuery', 'refresh_query' )
        HydrusGlobals.pubsub.sub( self, 'RemovePredicate', 'remove_predicate' )
        
    
    def _DoQuery( self ):
        
        self._query_key.Cancel()
        
        self._query_key = HydrusData.JobKey()
        
        if self._show_search and self._synchronised:
            
            try:
                
                current_predicates = self._current_predicates_box.GetPredicates()
                
                if len( current_predicates ) > 0:
                    
                    include_current = self._include_current_tags
                    include_pending = self._include_pending_tags
                    
                    search_context = ClientData.FileSearchContext( self._file_service_key, self._tag_service_key, include_current, include_pending, current_predicates )
                    
                    wx.GetApp().StartFileQuery( self._query_key, search_context )
                    
                    panel = ClientGUIMedia.MediaPanelLoading( self._page, self._page_key, self._file_service_key )
                    
                else: panel = ClientGUIMedia.MediaPanelNoQuery( self._page, self._page_key, self._file_service_key )
                
                HydrusGlobals.pubsub.pub( 'swap_media_panel', self._page_key, panel )
                
            except: wx.MessageBox( traceback.format_exc() )
            
        
    
    def AddMediaResultsFromQuery( self, query_key, media_results ):
        
        if query_key == self._query_key: HydrusGlobals.pubsub.pub( 'add_media_results', self._page_key, media_results, append = False )
        
    
    def AddPredicate( self, page_key, predicate ): 
        
        if self._show_search and page_key == self._page_key:
            
            if predicate is not None:
                
                ( predicate_type, value, inclusive ) = predicate.GetInfo()
                
                if predicate_type == HC.PREDICATE_TYPE_SYSTEM:
                    
                    ( system_predicate_type, info ) = value
                    
                    if system_predicate_type in [ HC.SYSTEM_PREDICATE_TYPE_NUM_TAGS, HC.SYSTEM_PREDICATE_TYPE_LIMIT, HC.SYSTEM_PREDICATE_TYPE_SIZE, HC.SYSTEM_PREDICATE_TYPE_DIMENSIONS, HC.SYSTEM_PREDICATE_TYPE_AGE, HC.SYSTEM_PREDICATE_TYPE_HASH, HC.SYSTEM_PREDICATE_TYPE_DURATION, HC.SYSTEM_PREDICATE_TYPE_NUM_WORDS, HC.SYSTEM_PREDICATE_TYPE_MIME, HC.SYSTEM_PREDICATE_TYPE_RATING, HC.SYSTEM_PREDICATE_TYPE_SIMILAR_TO, HC.SYSTEM_PREDICATE_TYPE_FILE_SERVICE ]:
                        
                        with ClientGUIDialogs.DialogInputFileSystemPredicate( self, system_predicate_type ) as dlg:
                            
                            if dlg.ShowModal() == wx.ID_OK: predicate = dlg.GetPredicate()
                            else: return
                            
                        
                    elif system_predicate_type == HC.SYSTEM_PREDICATE_TYPE_UNTAGGED: predicate = HydrusData.Predicate( HC.PREDICATE_TYPE_SYSTEM, ( HC.SYSTEM_PREDICATE_TYPE_NUM_TAGS, ( '=', 0 ) ) )
                    
                
                if self._current_predicates_box.HasPredicate( predicate ): self._current_predicates_box.RemovePredicate( predicate )
                else: self._current_predicates_box.AddPredicate( predicate )
                
            
            self._DoQuery()
            
        
    
    def ChangeFileRepositoryPubsub( self, page_key, service_key ):
        
        if page_key == self._page_key:
            
            self._file_service_key = service_key
            
            self._DoQuery()
            
        
    
    def ChangeTagRepositoryPubsub( self, page_key, service_key ):
        
        if page_key == self._page_key:
            
            self._tag_service_key = service_key
            
            self._DoQuery()
            
        
    
    def CleanBeforeDestroy( self ):
        
        ManagementPanel.CleanBeforeDestroy( self )
        
        self._query_key.Cancel()
        
    
    def GetPredicates( self ):
        
        if hasattr( self, '_current_predicates_box' ): return self._current_predicates_box.GetPredicates()
        else: return []
        
    
    def IncludeCurrent( self, page_key, value ):
        
        if page_key == self._page_key:
            
            self._include_current_tags = value
            
            self._DoQuery()
            
        
    
    def IncludePending( self, page_key, value ):
        
        if page_key == self._page_key:
            
            self._include_pending_tags = value
            
            self._DoQuery()
            
        
    
    def RefreshQuery( self, page_key ):
        
        if page_key == self._page_key: self._DoQuery()
        
    
    def RemovePredicate( self, page_key, predicate ):
        
        if page_key == self._page_key:
            
            if self._current_predicates_box.HasPredicate( predicate ):
                
                self._current_predicates_box.RemovePredicate( predicate )
                
                self._DoQuery()
                
            
        
    
    def SearchImmediately( self, page_key, value ):
        
        if page_key == self._page_key:
            
            self._synchronised = value
            
            self._DoQuery()
            
        
    
    def SetSearchFocus( self, page_key ):
        
        if page_key == self._page_key:
            
            try: self._searchbox.SetFocus() # there's a chance this doesn't exist!
            except: HydrusGlobals.pubsub.pub( 'set_media_focus' )
            
        
    
    def ShowQuery( self, query_key, media_results ):
        
        try:
            
            if query_key == self._query_key:
                
                current_predicates = self._current_predicates_box.GetPredicates()
                
                panel = ClientGUIMedia.MediaPanelThumbnails( self._page, self._page_key, self._file_service_key, media_results )
                
                panel.Collect( self._page_key, self._collect_by.GetChoice() )
                
                panel.Sort( self._page_key, self._sort_by.GetChoice() )
                
                HydrusGlobals.pubsub.pub( 'swap_media_panel', self._page_key, panel )
                
            
        except: wx.MessageBox( traceback.format_exc() )
        
    '''
class ManagementPanelMessages( wx.ScrolledWindow ):
    
    def __init__( self, parent, page_key, identity, starting_from_session = False ):
        
        wx.ScrolledWindow.__init__( self, parent, style = wx.BORDER_NONE | wx.HSCROLL | wx.VSCROLL )
        
        self.SetScrollRate( 0, 20 )
        
        self._page_key = page_key
        self._identity = identity
        self._starting_from_session = starting_from_session
        
        self._query_key = HydrusData.JobKey( cancellable = True )
        
        # sort out push-refresh later
        #self._refresh_inbox = wx.Button( self, label = 'refresh inbox' )
        #self._refresh_inbox.Bind( wx.EVT_BUTTON, self.EventRefreshInbox )
        #self._refresh_inbox.SetForegroundColour( ( 0, 128, 0 ) )
        
        self._actions_panel = ClientGUICommon.StaticBox( self, 'actions' )
        
        self._compose = wx.Button( self._actions_panel, label = 'compose' )
        self._compose.Bind( wx.EVT_BUTTON, self.EventCompose )
        self._compose.SetForegroundColour( ( 0, 128, 0 ) )
        
        self._actions_panel.AddF( self._compose, CC.FLAGS_EXPAND_PERPENDICULAR )
        #vbox.AddF( self._refresh_inbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._search_panel = ClientGUICommon.StaticBox( self, 'search' )
        
        self._current_predicates_box = ClientGUICommon.ListBoxMessagesPredicates( self._search_panel, self._page_key, [ 'system:inbox' ] )
        
        self._synchronised = ClientGUICommon.OnOffButton( self._search_panel, self._page_key, 'notify_search_immediately', on_label = 'searching immediately', off_label = 'waiting -- counts may be inaccurate' )
        self._synchronised.SetToolTipString( 'select whether to renew the search as soon as a new predicate is entered' )
        
        self._searchbox = ClientGUICommon.AutoCompleteDropdownMessageTerms( self._search_panel, self._page_key, self._identity )
        
        self._search_panel.AddF( self._current_predicates_box, CC.FLAGS_EXPAND_BOTH_WAYS )
        self._search_panel.AddF( self._synchronised, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._search_panel.AddF( self._searchbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._actions_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._search_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
        HydrusGlobals.pubsub.sub( self, 'AddPredicate', 'add_predicate' )
        HydrusGlobals.pubsub.sub( self, 'SearchImmediately', 'notify_search_immediately' )
        HydrusGlobals.pubsub.sub( self, 'ShowQuery', 'message_query_done' )
        HydrusGlobals.pubsub.sub( self, 'RefreshQuery', 'refresh_query' )
        HydrusGlobals.pubsub.sub( self, 'RemovePredicate', 'remove_predicate' )
        
        wx.CallAfter( self._DoQuery )
        
    
    def _DoQuery( self ):
        
        if self._synchronised.IsOn():
            
            try:
                
                current_predicates = self._current_predicates_box.GetPredicates()
                
                HydrusGlobals.pubsub.pub( 'set_conversations', self._page_key, [] )
                
                self._query_key.Cancel()
                
                self._query_key = HydrusData.JobKey( cancellable = True )
                
                if len( current_predicates ) > 0:
                    
                    search_context = ClientConstantsMessages.MessageSearchContext( self._identity, current_predicates )
                    
                    wx.GetApp().Read( 'do_message_query', self._query_key, search_context )
                    
                
            except: wx.MessageBox( traceback.format_exc() )
            
        
    
    def AddPredicate( self, page_key, predicate ): 
        
        if page_key == self._page_key:
            
            if predicate is not None:
                
                if predicate in ( 'system:started_by', 'system:from', 'system:to', 'system:age', 'system:numattachments' ):
                    
                    with ClientGUIDialogs.DialogInputMessageSystemPredicate( self, predicate ) as dlg:
                        
                        if dlg.ShowModal() == wx.ID_OK: predicate = dlg.GetString()
                        else: return
                        
                    
                elif predicate == 'system:unread': predicate = 'system:status=unread'
                elif predicate == 'system:drafts': predicate = 'system:draft'
                
                if self._current_predicates_box.HasPredicate( predicate ): self._current_predicates_box.RemovePredicate( predicate )
                else:
                    
                    if predicate in ( 'system:inbox', 'system:archive' ):
                        
                        if predicate == 'system:inbox': removee = 'system:archive'
                        elif predicate == 'system:archive': removee = 'system:inbox'
                        
                    else:
                        
                        if predicate.startswith( '-' ): removee = predicate[1:]
                        else: removee = '-' + predicate
                        
                    
                    if self._current_predicates_box.HasPredicate( removee ): self._current_predicates_box.RemovePredicate( removee )
                    
                    self._current_predicates_box.AddPredicate( predicate )
                    
                
            
            self._DoQuery()
            
        
    
    def EventCompose( self, event ): HydrusGlobals.pubsub.pub( 'new_compose_frame', self._identity )
    
    def EventRefreshInbox( self, event ):
        
        # tell db to do it, and that'll spam the appropriate pubsubs (which will tell this to just refresh query, I think is best)
        
        pass
        
    
    def RefreshQuery( self, page_key ):
        
        if page_key == self._page_key: self._DoQuery()
        
    
    def RemovePredicate( self, page_key, predicate ):
        
        if page_key == self._page_key:
            
            if self._current_predicates_box.HasPredicate( predicate ):
                
                self._current_predicates_box.RemovePredicate( predicate )
                
                self._DoQuery()
                
            
        
    
    def SearchImmediately( self, page_key, value ):
        
        if page_key == self._page_key and value: self._DoQuery()
        
    
    def SetSearchFocus( self, page_key ):
        
        if page_key == self._page_key: self._searchbox.SetFocus()
        
    
    def ShowQuery( self, query_key, conversations ):
        
        try:
            
            if query_key == self._query_key: HydrusGlobals.pubsub.pub( 'set_conversations', self._page_key, conversations )
            
        except: wx.MessageBox( traceback.format_exc() )
        
    
    def TestAbleToClose( self ):
        
        pass
        
        # if have a open draft, save it!
        
    '''