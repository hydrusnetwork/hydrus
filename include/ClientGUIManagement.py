import HydrusConstants as HC
import HydrusImageHandling
import ClientConstants as CC
import ClientConstantsMessages
import ClientGUICommon
import ClientGUIDialogs
import ClientGUIMedia
import ClientGUIMixins
import ClientParsers
import json
import os
import threading
import time
import traceback
import urllib
import urlparse
import wx
import wx.lib.scrolledpanel

CAPTCHA_FETCH_EVENT_TYPE = wx.NewEventType()
CAPTCHA_FETCH_EVENT = wx.PyEventBinder( CAPTCHA_FETCH_EVENT_TYPE )

ID_TIMER_CAPTCHA = wx.NewId()
ID_TIMER_DUMP = wx.NewId()
ID_TIMER_PROCESS_IMPORT_QUEUE = wx.NewId()
ID_TIMER_PROCESS_OUTER_QUEUE = wx.NewId()

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

class CaptchaControl( wx.Panel ):
    
    def __init__( self, parent, type, default ):
        
        wx.Panel.__init__( self, parent )
        
        self._captcha_key = default
        
        self._captcha_challenge = None
        self._captcha_runs_out = 0
        self._bitmap = wx.EmptyBitmap( 0, 0, 24 )
        
        self._timer = wx.Timer( self, ID_TIMER_CAPTCHA )
        self.Bind( wx.EVT_TIMER, self.EventTimer, id = ID_TIMER_CAPTCHA )
        
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
        
        sub_vbox.AddF( self._refresh_button, FLAGS_EXPAND_BOTH_WAYS )
        sub_vbox.AddF( self._captcha_time_left, FLAGS_SMALL_INDENT )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.AddF( self._captcha_panel, FLAGS_NONE )
        hbox.AddF( sub_vbox, FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        hbox2 = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox2.AddF( self._captcha_entry, FLAGS_EXPAND_BOTH_WAYS )
        hbox2.AddF( self._ready_button, FLAGS_MIXED )
        
        self._captcha_box_panel.AddF( hbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._captcha_box_panel.AddF( hbox2, FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._captcha_box_panel, FLAGS_EXPAND_BOTH_WAYS )
        
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
            
            hydrus_bmp = self._bitmap.CreateWxBmp()
            
            dc.DrawBitmap( hydrus_bmp, 0, 0 )
            
            hydrus_bmp.Destroy()
            
            self._refresh_button.SetLabel( 'get new captcha' )
            self._refresh_button.Enable()
            
            self._captcha_time_left.SetLabel( HC.ConvertTimestampToPrettyExpires( self._captcha_runs_out ) )
            
        
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
        
        if int( time.time() ) > captcha_runs_out: self.Enable()
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
        
        try:
            
            connection = CC.AdvancedHTTPConnection( scheme = 'http', host = 'www.google.com', port = 80 )
            
            javascript_string = connection.request( 'GET', '/recaptcha/api/challenge?k=' + self._captcha_key )
            
            ( trash, rest ) = javascript_string.split( 'challenge : \'', 1 )
            
            ( self._captcha_challenge, trash ) = rest.split( '\'', 1 )
            
            jpeg = connection.request( 'GET', '/recaptcha/api/image?c=' + self._captcha_challenge )
            
            self._bitmap = HydrusImageHandling.GenerateHydrusBitmapFromFile( jpeg )
            
            self._captcha_runs_out = int( time.time() ) + 5 * 60 - 15
            
            self._DrawMain()
            self._DrawEntry( '' )
            self._DrawReady( False )
            
            self._timer.Start( 1000, wx.TIMER_CONTINUOUS )
            
        except:
            
            wx.MessageBox( traceback.format_exc() )
            
        
    
    def EventTimer( self, event ):
        
        if int( time.time() ) > self._captcha_runs_out: self.Enable()
        else: self._DrawMain()
        
    
    # change this to hold (current challenge, bmp, timestamp it runs out, value, whethere ready to post)
    def GetValues( self ): return ( self._captcha_challenge, self._bitmap, self._captcha_runs_out, self._captcha_entry.GetValue(), self._ready_button.GetLabel() == 'edit' )
    
class Comment( wx.Panel ):
    
    def __init__( self, parent ):
        
        wx.Panel.__init__( self, parent )
        
        self._initial_comment = ''
        
        self._comment_panel = ClientGUICommon.StaticBox( self, 'comment' )
        
        self._comment = wx.TextCtrl( self._comment_panel, value = '', style = wx.TE_MULTILINE | wx.TE_READONLY, size = ( -1, 120 ) )
        self._comment.Disable()
        
        self._comment_append = wx.TextCtrl( self._comment_panel, value = '', style = wx.TE_MULTILINE | wx.TE_PROCESS_ENTER, size = ( -1, 120 ) )
        self._comment_append.Bind( wx.EVT_KEY_UP, self.EventKeyDown )
        
        self._comment_panel.AddF( self._comment, FLAGS_EXPAND_PERPENDICULAR )
        self._comment_panel.AddF( self._comment_append, FLAGS_EXPAND_PERPENDICULAR )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._comment_panel, FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
    
    def _SetComment( self ):
        
        append = self._comment_append.GetValue()
        
        if self._initial_comment != '' and append != '': comment = self._initial_comment + os.linesep + os.linesep + append
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
    
    def __init__( self, parent, page, page_key, file_service_identifier = CC.LOCAL_FILE_SERVICE_IDENTIFIER ):
        
        wx.lib.scrolledpanel.ScrolledPanel.__init__( self, parent, style = wx.BORDER_NONE | wx.VSCROLL )
        
        self.SetupScrolling()
        
        #self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
        self.SetBackgroundColour( wx.WHITE )
        
        self._page = page
        self._page_key = page_key
        self._file_service_identifier = file_service_identifier
        self._tag_service_identifier = CC.NULL_SERVICE_IDENTIFIER
        
        HC.pubsub.sub( self, 'SetSearchFocus', 'set_search_focus' )
        
    
    def _MakeCollect( self, sizer ):
        
        self._collect_by = ClientGUICommon.CheckboxCollect( self, self._page_key )
        
        sizer.AddF( self._collect_by, FLAGS_EXPAND_PERPENDICULAR )
        
    
    def _MakeCurrentSelectionTagsBox( self, sizer ):
        
        tags_box = ClientGUICommon.TagsBoxCPPWithSorter( self, self._page_key )
        
        sizer.AddF( tags_box, FLAGS_EXPAND_BOTH_WAYS )
        
    
    def _MakeSort( self, sizer ):
        
        self._sort_by = ClientGUICommon.ChoiceSort( self, self._page_key )
        
        sizer.AddF( self._sort_by, FLAGS_EXPAND_PERPENDICULAR )
        
    
    def SetSearchFocus( self, page_key ): pass
    
    def TryToClose( self ): pass
    
class ManagementPanelDumper( ManagementPanel ):
    
    def __init__( self, parent, page, page_key, imageboard, media_results ):
        
        ManagementPanel.__init__( self, parent, page, page_key )
        
        ( self._4chan_token, pin, timeout ) = wx.GetApp().Read( '4chan_pass' )
        
        self._have_4chan_pass = timeout > int( time.time() )
        
        self._imageboard = imageboard
        
        self._media_list = ClientGUIMixins.ListeningMediaList( CC.LOCAL_FILE_SERVICE_IDENTIFIER, [], media_results )
        
        self._current_media = None
        
        self._dumping = False
        self._actually_dumping = False
        self._num_dumped = 0
        self._next_dump_index = 0
        self._next_dump_time = 0
        
        self._file_post_name = 'upfile'
        
        self._timer = wx.Timer( self, ID_TIMER_DUMP )
        self.Bind( wx.EVT_TIMER, self.EventTimer, id = ID_TIMER_DUMP )
        
        ( post_url, self._flood_time, self._form_fields, self._restrictions ) = self._imageboard.GetBoardInfo()
        
        o = urlparse.urlparse( post_url )
        
        self._post_scheme = o.scheme
        self._post_host = o.hostname
        self._post_port = o.port
        self._post_request = o.path
        
        # progress
        
        self._processing_panel = ClientGUICommon.StaticBox( self, 'processing' )
        
        self._progress_info = wx.StaticText( self._processing_panel )
        
        self._progress_gauge = ClientGUICommon.Gauge( self._processing_panel )
        self._progress_gauge.SetRange( len( media_results ) )
        
        self._start_button = wx.Button( self._processing_panel, label = 'start' )
        self._start_button.Bind( wx.EVT_BUTTON, self.EventStartButton )
        
        self._processing_panel.AddF( self._progress_info, FLAGS_EXPAND_PERPENDICULAR )
        self._processing_panel.AddF( self._progress_gauge, FLAGS_EXPAND_PERPENDICULAR )
        self._processing_panel.AddF( self._start_button, FLAGS_EXPAND_PERPENDICULAR )
        
        # thread options
        
        self._thread_panel = ClientGUICommon.StaticBox( self, 'thread options' )
        
        self._thread_fields = {}
        
        gridbox = wx.FlexGridSizer( 0, 2 )
        
        gridbox.AddGrowableCol( 1, 1 )
        
        for ( name, type, default, editable ) in self._form_fields:
            
            if type in ( CC.FIELD_TEXT, CC.FIELD_THREAD_ID ): field = wx.TextCtrl( self._thread_panel, value = default )
            elif type == CC.FIELD_PASSWORD: field = wx.TextCtrl( self._thread_panel, value = default, style = wx.TE_PASSWORD )
            else: continue
            
            self._thread_fields[ name ] = ( type, field )
            
            if editable:
                
                gridbox.AddF( wx.StaticText( self._thread_panel, label = name + ':' ), FLAGS_MIXED )
                gridbox.AddF( field, FLAGS_EXPAND_BOTH_WAYS )
                
            else: field.Hide()
            
        
        self._thread_panel.AddF( gridbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        # post options
        
        self._post_panel = ClientGUICommon.StaticBox( self, 'post options' )
        
        self._post_fields = {}
        
        postbox = wx.BoxSizer( wx.VERTICAL )
        
        self._post_info = wx.StaticText( self._post_panel, label = 'no file selected', style = wx.ALIGN_CENTER | wx.ST_NO_AUTORESIZE )
        
        for ( name, type, default, editable ) in self._form_fields:
            
            if type == CC.FIELD_VERIFICATION_RECAPTCHA:
                
                if self._have_4chan_pass: continue
                
                field = CaptchaControl( self._post_panel, type, default )
                field.Bind( CAPTCHA_FETCH_EVENT, self.EventCaptchaRefresh )
                
            elif type == CC.FIELD_COMMENT: field = Comment( self._post_panel )
            else: continue
            
            self._post_fields[ name ] = ( type, field, default )
            
            postbox.AddF( field, FLAGS_EXPAND_PERPENDICULAR )
            
        
        gridbox = wx.FlexGridSizer( 0, 2 )
        
        gridbox.AddGrowableCol( 1, 1 )
        
        for ( name, type, default, editable ) in self._form_fields:
            
            if type == CC.FIELD_CHECKBOX:
                
                field = wx.CheckBox( self._post_panel )
                
                field.SetValue( default == 'True' )
                
            else: continue
            
            self._post_fields[ name ] = ( type, field, default )
            
            gridbox.AddF( wx.StaticText( self._post_panel, label = name + ':' ), FLAGS_MIXED )
            gridbox.AddF( field, FLAGS_EXPAND_BOTH_WAYS )
            
        
        for ( name, type, default, editable ) in self._form_fields:
            
            if type == CC.FIELD_FILE: self._file_post_name = name
            
        
        self._post_panel.AddF( self._post_info, FLAGS_EXPAND_PERPENDICULAR )
        self._post_panel.AddF( postbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._post_panel.AddF( gridbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        # misc
        
        self._advanced_tag_options = ClientGUICommon.AdvancedTagOptions( self, 'include tags from', namespaces = [ 'creator', 'series', 'title', 'volume', 'chapter', 'page', 'character', 'person', 'all others' ] )
        
        # arrange stuff
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        self._MakeSort( vbox )
        
        vbox.AddF( self._processing_panel, FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._thread_panel, FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._post_panel, FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._advanced_tag_options, FLAGS_EXPAND_PERPENDICULAR )
        
        self._MakeCurrentSelectionTagsBox( vbox )
        
        self.SetSizer( vbox )
        
        HC.pubsub.sub( self, 'FocusChanged', 'focus_changed' )
        HC.pubsub.sub( self, 'SortedMediaPulse', 'sorted_media_pulse' )
        
        self._media_to_dump_info = {}
        
        for media in self._media_list.GetSortedMedia():
            
            dump_status_enum = CC.DUMPER_NOT_DUMPED
            
            dump_status_string = 'not yet dumped'
            
            post_field_info = []
            
            for ( name, ( type, field, default ) ) in self._post_fields.items():
                
                if type == CC.FIELD_COMMENT:
                    
                    post_field_info.append( ( name, type, ( self._GetInitialComment( media ), '' ) ) )
                    
                elif type == CC.FIELD_CHECKBOX: post_field_info.append( ( name, type, default == 'True' ) )
                elif type == CC.FIELD_VERIFICATION_RECAPTCHA: post_field_info.append( ( name, type, None ) )
                
            
            self._media_to_dump_info[ media ] = ( dump_status_enum, dump_status_string, post_field_info )
            
        
        self.Bind( wx.EVT_MENU, self.EventMenu )
        
        self._timer.Start( 1000, wx.TIMER_CONTINUOUS )
        
    
    def _THREADDoDump( self, media_to_dump, post_field_info, headers, body ):
        
        try:
            
            connection = CC.AdvancedHTTPConnection( scheme = self._post_scheme, host = self._post_host, port = self._post_port )
            
            data = connection.request( 'POST', self._post_request, headers = headers, body = body )
            
            ( status, phrase ) = ClientParsers.Parse4chanPostScreen( data )
            
        except Exception as e: ( status, phrase ) = ( 'big error', unicode( e ) )
        
        wx.CallAfter( self.CALLBACKDoneDump, media_to_dump, post_field_info, status, phrase )
        
    
    def _FreezeCurrentMediaPostInfo( self ):
        
        ( dump_status_enum, dump_status_string, post_field_info ) = self._media_to_dump_info[ self._current_media ]
        
        post_field_info = []
        
        for ( name, ( type, field, default ) ) in self._post_fields.items():
            
            if type == CC.FIELD_COMMENT: post_field_info.append( ( name, type, field.GetValues() ) )
            elif type == CC.FIELD_CHECKBOX: post_field_info.append( ( name, type, field.GetValue() ) )
            elif type == CC.FIELD_VERIFICATION_RECAPTCHA: post_field_info.append( ( name, type, field.GetValues() ) )
            
        
        self._media_to_dump_info[ self._current_media ] = ( dump_status_enum, dump_status_string, post_field_info )
        
    
    def _GetInitialComment( self, media ):
        
        try: index = self._media_list.GetMediaIndex( media )
        except: return 'media removed'
        
        num_files = len( self._media_list.GetSortedMedia() )
        
        if index == 0:
            
            total_size = sum( [ m.GetSize() for m in self._media_list.GetSortedMedia() ] )
            
            initial = 'Hydrus Network Client is starting a dump of ' + str( num_files ) + ' files, totalling ' + HC.ConvertIntToBytes( total_size ) + ':' + os.linesep + os.linesep
            
        else: initial = ''
        
        initial += str( index + 1 ) + '/' + str( num_files )
        
        info = self._advanced_tag_options.GetInfo()
        
        for ( service_identifier, namespaces ) in info:
            
            ( current, deleted, pending, petitioned ) = media.GetTags().GetCDPP( service_identifier )
            
            tags = current.union( pending )
            
            tags_to_include = []
            
            for namespace in namespaces:
                
                if namespace == 'all others': tags_to_include.extend( [ tag for tag in tags if not True in ( tag.startswith( n ) for n in namespaces if n != 'all others' ) ] )
                else: tags_to_include.extend( [ tag for tag in tags if tag.startswith( namespace + ':' ) ] )
                
            
            initial += os.linesep + os.linesep + ', '.join( tags_to_include )
            
        
        return initial
        
    
    def _ShowCurrentMedia( self ):
        
        if self._current_media is None:
            
            self._post_info.SetLabel( 'no file selected' )
            
            for ( name, ( type, field, default ) ) in self._post_fields.items():
                
                if type == CC.FIELD_CHECKBOX: field.SetValue( False )
                
                field.Disable()
                
            
        else:
            
            num_files = len( self._media_list.GetSortedMedia() )
            
            ( dump_status_enum, dump_status_string, post_field_info ) = self._media_to_dump_info[ self._current_media ]
            
            index = self._media_list.GetMediaIndex( self._current_media )
            
            self._post_info.SetLabel( str( index + 1 ) + '/' + str( num_files ) + ': ' + dump_status_string )
            
            for ( name, type, value ) in post_field_info:
                
                ( type, field, default ) = self._post_fields[ name ]
                
                if type == CC.FIELD_COMMENT:
                    
                    ( initial, append ) = value
                    
                    field.EnableWithValues( initial, append )
                    
                elif type == CC.FIELD_CHECKBOX:
                    
                    field.SetValue( value )
                    field.Enable()
                    
                elif type == CC.FIELD_VERIFICATION_RECAPTCHA:
                    
                    if value is None: field.Enable()
                    else:
                        
                        ( challenge, bitmap, captcha_runs_out, entry, ready ) = value
                        
                        field.EnableWithValues( challenge, bitmap, captcha_runs_out, entry, ready )
                        
                    
                
            
            if dump_status_enum in ( CC.DUMPER_DUMPED_OK, CC.DUMPER_UNRECOVERABLE_ERROR ):
                
                for ( name, ( type, field, default ) ) in self._post_fields.items():
                    
                    if type == CC.FIELD_CHECKBOX: field.SetValue( False )
                    
                    field.Disable()
                    
                
            
        
    
    def _UpdatePendingInitialComments( self ):
        
        all_media_to_dump = self._media_list.GetSortedMedia()[ self._next_dump_index : ]
        
        for media_to_dump in all_media_to_dump:
            
            if self._current_media == media_to_dump: self._FreezeCurrentMediaPostInfo()
            
            ( dump_status_enum, dump_status_string, post_field_info ) = self._media_to_dump_info[ media_to_dump ]
            
            new_post_field_info = []
            
            for ( name, type, value ) in post_field_info:
                
                if type == CC.FIELD_COMMENT:
                    
                    ( initial, append ) = value
                    
                    initial = self._GetInitialComment( media_to_dump )
                    
                    new_post_field_info.append( ( name, type, ( initial, append ) ) )
                    
                else: new_post_field_info.append( ( name, type, value ) )
                
            
            self._media_to_dump_info[ media_to_dump ] = ( dump_status_enum, dump_status_string, new_post_field_info )
            
            if self._current_media == media_to_dump: self._ShowCurrentMedia()
            
        
    
    def CALLBACKDoneDump( self, media_to_dump, post_field_info, status, phrase ):
        
        self._actually_dumping = False
        
        if status == 'success':
            
            dump_status_enum = CC.DUMPER_DUMPED_OK
            dump_status_string = 'dumped ok'
            
            if self._current_media == media_to_dump: HC.pubsub.pub( 'set_focus', self._page_key, None )
            
            self._next_dump_time = int( time.time() ) + self._flood_time
            
            self._num_dumped += 1
            
            self._progress_gauge.SetValue( self._num_dumped )
            
            self._next_dump_index += 1
            
        elif status == 'captcha':
            
            dump_status_enum = CC.DUMPER_RECOVERABLE_ERROR
            dump_status_string = 'captcha was incorrect'
            
            self._next_dump_time = int( time.time() ) + 10
            
            new_post_field_info = []
            
            for ( name, type, value ) in post_field_info:
                
                if type == CC.FIELD_VERIFICATION_RECAPTCHA: new_post_field_info.append( ( name, type, None ) )
                else: new_post_field_info.append( ( name, type, value ) )
                
                if media_to_dump == self._current_media:
                    
                    ( type, field, default ) = self._post_fields[ name ]
                    
                    field.Enable()
                    
                
            
            post_field_info = new_post_field_info
            
        elif status == 'too quick':
            
            dump_status_enum = CC.DUMPER_RECOVERABLE_ERROR
            dump_status_string = ''
            
            self._progress_info.SetLabel( 'Flood limit hit, retrying.' )
            
            self._next_dump_time = int( time.time() ) + self._flood_time
            
        elif status == 'big error':
            
            dump_status_enum = CC.DUMPER_UNRECOVERABLE_ERROR
            dump_status_string = ''
            
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
            
            if self._current_media == media_to_dump: HC.pubsub.pub( 'set_focus', self._page_key, None )
            
            self._next_dump_time = int( time.time() ) + self._flood_time
            
            self._next_dump_index += 1
            
        
        self._media_to_dump_info[ media_to_dump ] = ( dump_status_enum, dump_status_string, post_field_info )
        
        ( hash, ) = media_to_dump.GetDisplayMedia().GetHashes()
        
        HC.pubsub.pub( 'file_dumped', self._page_key, hash, dump_status_enum )
        
        if self._next_dump_index == len( self._media_list.GetSortedMedia() ):
            
            self._progress_info.SetLabel( 'done - ' + str( self._num_dumped ) + ' dumped' )
            
            self._start_button.Disable()
            
            self._timer.Stop()
            
        
    
    def EventCaptchaRefresh( self, event ):
        
        try:
            
            index = self._media_list.GetMediaIndex( self._current_media )
            
            if ( ( index + 1 ) - self._next_dump_index ) * ( self._flood_time + 10 ) > 5 * 60: event.Veto()
            
        except: event.Veto()
        
    
    def EventMenu( self, event ):
        
        action = CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetAction( event.GetId() )
        
        if action is not None:
            
            try:
                
                ( command, data ) = action
                
                if command == 'advanced_tag_options_changed': self._UpdatePendingInitialComments()
                else: event.Skip()
                
            except Exception as e:
                
                wx.MessageBox( unicode( e ) )
                
            
        
    
    def EventStartButton( self, event ):
        
        if self._start_button.GetLabel() in ( 'start', 'continue' ):
            
            for ( name, ( type, field ) ) in self._thread_fields.items():
                
                if type == CC.FIELD_THREAD_ID:
                    
                    try: int( field.GetValue() )
                    except:
                        
                        self._progress_info.SetLabel( 'set thread_id field first' )
                        
                        return
                        
                    
                
            
            for ( type, field ) in self._thread_fields.values(): field.Disable()
            
            self._dumping = True
            self._start_button.SetLabel( 'pause' )
            
            if self._next_dump_time == 0: self._next_dump_time = int( time.time() ) + 5
            
            # disable thread fields here
            
        else:
            
            for ( type, field ) in self._thread_fields.values(): field.Enable()
            
            self._dumping = False
            
            if self._num_dumped == 0: self._start_button.SetLabel( 'start' )
            else: self._start_button.SetLabel( 'continue' )
            
        
    
    def EventTimer( self, event ):
        
        if self._actually_dumping: return
        
        if self._dumping:
            
            time_left = self._next_dump_time - int( time.time() )
            
            if time_left < 1:
                
                media_to_dump = self._media_list.GetSortedMedia()[ self._next_dump_index ]
                
                wait = False
                
                if self._current_media == media_to_dump: self._FreezeCurrentMediaPostInfo()
                
                ( dump_status_enum, dump_status_string, post_field_info ) = self._media_to_dump_info[ media_to_dump ]
                
                for ( name, type, value ) in post_field_info:
                    
                    if type == CC.FIELD_VERIFICATION_RECAPTCHA:
                        
                        if value is None:
                            
                            wait = True
                            
                            break
                            
                        else:
                            
                            ( challenge, bitmap, captcha_runs_out, entry, ready ) = value
                            
                            if int( time.time() ) > captcha_runs_out or not ready:
                                
                                wait = True
                                
                                break
                                
                            
                        
                    
                
                if wait: self._progress_info.SetLabel( 'waiting for captcha' )
                else:
                    
                    self._progress_info.SetLabel( 'dumping' ) # 100% cpu time here - may or may not be desirable
                    
                    post_fields = []
                    
                    for ( name, ( type, field ) ) in self._thread_fields.items():
                        
                        post_fields.append( ( name, type, field.GetValue() ) )
                        
                    
                    for ( name, type, value ) in post_field_info:
                        
                        if type == CC.FIELD_VERIFICATION_RECAPTCHA:
                            
                            ( challenge, bitmap, captcha_runs_out, entry, ready ) = value
                            
                            post_fields.append( ( 'recaptcha_challenge_field', type, challenge ) )
                            post_fields.append( ( 'recaptcha_response_field', type, entry ) )
                            
                        elif type == CC.FIELD_COMMENT:
                            
                            ( initial, append ) = value
                            
                            comment = initial
                            
                            if len( append ) > 0: comment += os.linesep + os.linesep + append
                            
                            post_fields.append( ( name, type, comment ) )
                            
                        else: post_fields.append( ( name, type, value ) )
                        
                    
                    ( hash, ) = media_to_dump.GetDisplayMedia().GetHashes()
                    
                    file = wx.GetApp().Read( 'file', hash )
                    
                    post_fields.append( ( self._file_post_name, CC.FIELD_FILE, ( hash, HC.GetMimeFromString( file ), file ) ) )
                    
                    ( ct, body ) = CC.GenerateDumpMultipartFormDataCTAndBody( post_fields )
                    
                    headers = {}
                    headers[ 'Content-Type' ] = ct
                    if self._have_4chan_pass: headers[ 'Cookie' ] = 'pass_enabled=1; pass_id=' + self._4chan_token
                    
                    self._actually_dumping = True
                    
                    threading.Thread( target = self._THREADDoDump, args = ( media_to_dump, post_field_info, headers, body ) ).start()
                    
                
            else: self._progress_info.SetLabel( 'dumping next file in ' + str( time_left ) + ' seconds' )
            
        else:
            
            if self._num_dumped == 0: self._progress_info.SetLabel( 'will dump to ' + self._imageboard.GetName() )
            else: self._progress_info.SetLabel( 'paused after ' + str( self._num_dumped ) + ' files dumped' )
            
        
    
    def FocusChanged( self, page_key, media ):
        
        if page_key == self._page_key and media != self._current_media:
            
            old_media = self._current_media
            
            if old_media is not None: self._FreezeCurrentMediaPostInfo()
            
            self._current_media = media
            
            self._ShowCurrentMedia()
            
        
    
    def SortedMediaPulse( self, page_key, media_results ):
        
        if page_key == self._page_key:
            
            self._media_list = ClientGUIMixins.ListeningMediaList( CC.LOCAL_FILE_SERVICE_IDENTIFIER, [], media_results )
            
            new_media_to_dump_info = {}
            
            for ( media, ( dump_status_enum, dump_status_string, post_field_info ) ) in self._media_to_dump_info.items():
                
                new_post_field_info = []
                
                for ( name, type, value ) in post_field_info:
                    
                    if type == CC.FIELD_COMMENT:
                        
                        ( initial, append ) = value
                        
                        initial = self._GetInitialComment( media )
                        
                        value = ( initial, append )
                        
                    
                    new_post_field_info.append( ( name, type, value ) )
                    
                
                new_media_to_dump_info[ media ] = ( dump_status_enum, dump_status_string, new_post_field_info )
                
            
            self._media_to_dump_info = new_media_to_dump_info
            
            self._ShowCurrentMedia()
            
            if self._current_media is None and len( self._media_list.GetSortedMedia() ) > 0: HC.pubsub.pub( 'set_focus', self._page_key, self._media_list.GetSortedMedia()[0] )
            
        
    
    def TryToClose( self ):
        
        if self._dumping:
            
            with ClientGUIDialogs.DialogYesNo( self, 'This page is still dumping. Are you sure you want to close it?' ) as dlg:
                
                if dlg.ShowModal() == wx.ID_NO: raise Exception()
                
            
        
    
class ManagementPanelImport( ManagementPanel ):
    
    def __init__( self, parent, page, page_key ):
        
        ManagementPanel.__init__( self, parent, page, page_key )
        
        self._successful = 0
        self._failed = 0
        self._deleted = 0
        self._redundant = 0
        
        self._import_queue = []
        self._import_queue_position = 0
        
        self._pause_import = False
        self._cancel_import_queue = threading.Event()
        self._pause_outer_queue = False
        self._cancel_outer_queue = threading.Event()
        
        self._currently_importing = False
        self._currently_processing_import_queue = False
        self._currently_processing_outer_queue = False
        
        self._processing_panel = ClientGUICommon.StaticBox( self, 'progress' )
        
        self._import_overall_info = wx.StaticText( self._processing_panel )
        self._import_current_info = wx.StaticText( self._processing_panel )
        self._import_gauge = ClientGUICommon.Gauge( self._processing_panel )
        
        self._import_pause_button = wx.Button( self._processing_panel, label = 'pause' )
        self._import_pause_button.Bind( wx.EVT_BUTTON, self.EventPauseImport )
        self._import_pause_button.Disable()
        
        self._timer_process_import_queue = wx.Timer( self, id = ID_TIMER_PROCESS_IMPORT_QUEUE )
        
        self.Bind( wx.EVT_TIMER, self.EventProcessImportQueue, id = ID_TIMER_PROCESS_IMPORT_QUEUE )
        
        self._timer_process_import_queue.Start( 1000, wx.TIMER_ONE_SHOT )
        
        HC.pubsub.sub( self, 'ImportDone', 'import_done' )
        HC.pubsub.sub( self, 'SetImportInfo', 'set_import_info' )
        HC.pubsub.sub( self, 'DoneAddingToImportQueue', 'done_adding_to_import_queue' )
        
    
    def _GetPreimportStatus( self ):
        
        status = 'importing ' + str( self._import_queue_position + 1 ) + '/' + str( len( self._import_queue ) )
        
        return status
        
    
    def _GetPreprocessStatus( self ): pass
    
    def _GetStatusStrings( self ):
        
        strs = []
        
        if self._successful > 0: strs.append( str( self._successful ) + ' successful' )
        if self._failed > 0: strs.append( str( self._failed ) + ' failed' )
        if self._deleted > 0: strs.append( str( self._deleted ) + ' already deleted' )
        if self._redundant > 0: strs.append( str( self._redundant ) + ' already in db' )
        
        return strs
        
    
    def _SetButtons( self ):
        
        if self._currently_processing_import_queue: self._import_pause_button.Enable()
        else: self._import_pause_button.Disable()
        
    
    def CALLBACKAddToImportQueue( self, items ):
        
        if self._currently_processing_import_queue: self._import_queue.extend( items )
        else:
            
            self._import_queue = items
            self._import_queue_position = 0
            
            self._timer_process_import_queue.Start( 10, wx.TIMER_ONE_SHOT )
            
            self._currently_processing_import_queue = True
            
            self._SetButtons()
            
        
        self._import_gauge.SetRange( len( self._import_queue ) )
        
    
    def CALLBACKImportArgs( self, file, advanced_import_options, service_identifiers_to_tags, url = None, exception = None ):
        
        if exception is None:
            
            self._import_current_info.SetLabel( self._GetPreimportStatus() )
            
            wx.GetApp().WriteLowPriority( 'import_file_from_page', self._page_key, file, advanced_import_options = advanced_import_options, service_identifiers_to_tags = service_identifiers_to_tags, url = url )
            
        else:
            
            self._currently_importing = False
            self._import_current_info.SetLabel( unicode( exception ) )
            self._import_gauge.SetValue( self._import_queue_position + 1 )
            self._import_queue_position += 1
            
            self._timer_process_import_queue.Start( 2000, wx.TIMER_ONE_SHOT )
            
        
    
    def DoneAddingToImportQueue( self, page_key ):
        
        if self._page_key == page_key:
            
            self._currently_processing_outer_queue = False
            
            self._SetButtons()
            
        
    
    def EventPauseImport( self, event ):
        
        if self._pause_import:
            
            self._pause_import = False
            
            self._import_pause_button.SetLabel( 'pause' )
            self._import_pause_button.SetForegroundColour( ( 0, 0, 0 ) )
            
        else:
            
            self._pause_import = True
            
            self._import_pause_button.SetLabel( 'resume' )
            self._import_pause_button.SetForegroundColour( ( 0, 128, 0 ) )
            
        
    
    def EventProcessImportQueue( self, event ):
        
        status_strings = self._GetStatusStrings()
        
        self._import_overall_info.SetLabel( ', '.join( status_strings ) )
        
        if self._pause_import: self._import_current_info.SetLabel( 'paused' )
        else:
            
            if self._cancel_import_queue.is_set(): self._import_queue = self._import_queue[ : self._import_queue_position ] # cut excess queue
            
            if len( self._import_queue ) == 0: self._import_current_info.SetLabel( '' )
            else:
                
                if not self._currently_importing:
                    
                    if self._import_queue_position < len( self._import_queue ):
                        
                        self._currently_importing = True
                        
                        self._import_current_info.SetLabel( self._GetPreprocessStatus() )
                        
                        item = self._import_queue[ self._import_queue_position ]
                        
                        threading.Thread( target = self._THREADGetImportArgs, args = ( item, ), name = 'Generate Import Args' ).start()
                        
                    else:
                        
                        if self._currently_processing_outer_queue: self._import_current_info.SetLabel( 'waiting for more items' )
                        else:
                            
                            if len( status_strings ) > 0: status = 'import done'
                            else: status = 'import abandoned'
                            
                            self._import_current_info.SetLabel( status )
                            
                            self._currently_processing_import_queue = False
                            
                            self._cancel_import_queue = threading.Event()
                            self._cancel_outer_queue = threading.Event()
                            
                            self._SetButtons()
                            
                        
                    
                
            
        
        self._timer_process_import_queue.Start( 1000, wx.TIMER_ONE_SHOT )
        
    
    def ImportDone( self, page_key, result, exception = None ):
        
        if page_key == self._page_key:
            
            if result == 'successful': self._successful += 1
            elif result == 'failed': self._failed += 1
            elif result == 'deleted': self._deleted += 1
            elif result == 'redundant': self._redundant += 1
            
            self._currently_importing = False
            self._import_gauge.SetValue( self._import_queue_position + 1 )
            self._import_queue_position += 1
            
            if exception is None: self._timer_process_import_queue.Start( 10, wx.TIMER_ONE_SHOT )
            else:
                
                print( os.linesep + 'Had trouble importing ' + str( self._import_queue[ self._import_queue_position - 1 ] ) + ':' + os.linesep + unicode( exception ) )
                
                self._import_current_info.SetLabel( unicode( exception ) )
                
                self._timer_process_import_queue.Start( 2000, wx.TIMER_ONE_SHOT )
                
            
        
    
    def SetImportInfo( self, page_key, info ):
        
        if self._page_key == page_key: self._import_current_info.SetLabel( info )
        
    
    def TryToClose( self ):
        
        if self._currently_processing_import_queue and not self._pause_import:
            
            with ClientGUIDialogs.DialogYesNo( self, 'This page is still importing. Are you sure you want to close it?' ) as dlg:
                
                if dlg.ShowModal() == wx.ID_NO: raise Exception()
                
            
        
    
class ManagementPanelImportHDD( ManagementPanelImport ):
    
    def __init__( self, parent, page, page_key, paths, advanced_import_options = {}, paths_to_tags = {} ):
        
        self._advanced_import_options = advanced_import_options
        self._paths_to_tags = paths_to_tags
        
        ManagementPanelImport.__init__( self, parent, page, page_key )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        self._MakeSort( vbox )
        
        self._processing_panel.AddF( self._import_overall_info, FLAGS_EXPAND_PERPENDICULAR )
        self._processing_panel.AddF( self._import_current_info, FLAGS_EXPAND_PERPENDICULAR )
        self._processing_panel.AddF( self._import_gauge, FLAGS_EXPAND_PERPENDICULAR )
        self._processing_panel.AddF( self._import_pause_button, FLAGS_EXPAND_PERPENDICULAR )
        
        vbox.AddF( self._processing_panel, FLAGS_EXPAND_PERPENDICULAR )
        
        self._MakeCurrentSelectionTagsBox( vbox )
        
        self.SetSizer( vbox )
        
        self.CALLBACKAddToImportQueue( paths )
        
    
    def _THREADGetImportArgs( self, queue_object ):
        
        try:
            
            path = queue_object
            
            with open( path, 'rb' ) as f: file = f.read()
            
            if path in self._paths_to_tags: service_identifiers_to_tags = self._paths_to_tags[ path ]
            else: service_identifiers_to_tags = {}
            
            wx.CallAfter( self.CALLBACKImportArgs, file, self._advanced_import_options, service_identifiers_to_tags )
            
        except Exception as e:
            print( traceback.format_exc() )
            wx.CallAfter( self.CALLBACKImportArgs, '', {}, {}, exception = e )
        
    
    def _GetPreprocessStatus( self ):
        
        status = 'reading ' + str( self._import_queue_position + 1 ) + '/' + str( len( self._import_queue ) )
        
        return status
        
    
class ManagementPanelImportWithQueue( ManagementPanelImport ):
    
    def __init__( self, parent, page, page_key ):
        
        ManagementPanelImport.__init__( self, parent, page, page_key )
        
        self._connections = {}
        
        self._import_cancel_button = wx.Button( self._processing_panel, label = 'that\'s enough' )
        self._import_cancel_button.Bind( wx.EVT_BUTTON, self.EventCancelImport )
        self._import_cancel_button.SetForegroundColour( ( 128, 0, 0 ) )
        self._import_cancel_button.Disable()
        
        self._outer_queue_panel = ClientGUICommon.StaticBox( self, 'queue' )
        
        self._outer_queue_info = wx.StaticText( self._outer_queue_panel )
        
        self._outer_queue = wx.ListBox( self._outer_queue_panel, size = ( -1, 200 ) )
        
        self._new_queue_input = wx.TextCtrl( self._outer_queue_panel, style=wx.TE_PROCESS_ENTER )
        self._new_queue_input.Bind( wx.EVT_KEY_DOWN, self.EventKeyDown )
        
        self._up = wx.Button( self._outer_queue_panel, label = u'\u2191' )
        self._up.Bind( wx.EVT_BUTTON, self.EventUp )
        
        self._remove = wx.Button( self._outer_queue_panel, label = 'X' )
        self._remove.Bind( wx.EVT_BUTTON, self.EventRemove )
        
        self._down = wx.Button( self._outer_queue_panel, label = u'\u2193' )
        self._down.Bind( wx.EVT_BUTTON, self.EventDown )
        
        self._advanced_import_options = ClientGUICommon.AdvancedImportOptions( self )
        
        self._outer_queue_timer = wx.Timer( self, id = ID_TIMER_PROCESS_OUTER_QUEUE )
        
        self.Bind( wx.EVT_TIMER, self.EventProcessOuterQueue, id = ID_TIMER_PROCESS_OUTER_QUEUE )
        
        self._outer_queue_timer.Start( 1000, wx.TIMER_ONE_SHOT )
        
        HC.pubsub.sub( self, 'SetOuterQueueInfo', 'set_outer_queue_info' )
        
    
    def _GetPreprocessStatus( self ):
        
        status = 'checking url status ' + str( self._import_queue_position + 1 ) + '/' + str( len( self._import_queue ) )
        
        return status
        
    
    def _SetButtons( self ):
        
        if self._currently_processing_import_queue:
            
            self._import_pause_button.Enable()
            self._import_cancel_button.Enable()
            
        else:
            
            self._import_pause_button.Disable()
            self._import_cancel_button.Disable()
            
        
    
    def EventCancelImport( self, event ):
        
        self._cancel_import_queue.set()
        self._cancel_outer_queue.set()
        
        if self._pause_import: self.EventPauseImport( event )
        if self._pause_outer_queue: self.EventPauseOuterQueue( event )
        
    
    def EventPauseOuterQueue( self, event ): pass
    
    def EventKeyDown( self, event ):
        
        if event.KeyCode in ( wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER ):
            
            url = self._new_queue_input.GetValue()
            
            if url != '':
                
                self._outer_queue.Append( url, url )
                
                self._outer_queue_timer.Start( 10, wx.TIMER_ONE_SHOT )
                
                self._new_queue_input.SetValue( '' )
                
            
        else: event.Skip()
        
    
    def EventUp( self, event ):
        
        selection = self._outer_queue.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            if selection > 0:
                
                url = self._outer_queue.GetClientData( selection )
                
                self._outer_queue.Delete( selection )
                
                self._outer_queue.Insert( url, selection - 1, url )
                
                self._outer_queue.Select( selection - 1 )
                
            
        
    
    def EventProcessOuterQueue( self, event ):
        
        if self._pause_outer_queue: self._outer_queue_info.SetLabel( 'paused' )
        else:
            
            if self._outer_queue.GetCount() > 0 and not self._currently_processing_import_queue and not self._currently_processing_outer_queue:
                
                self._currently_processing_outer_queue = True
                
                item = self._outer_queue.GetClientData( 0 )
                
                self._outer_queue.Delete( 0 )
                
                threading.Thread( target = self._THREADDownloadImportItems, args = ( item, ), name = 'Generate Import Items' ).start()
                
            
        
        self._outer_queue_timer.Start( 1000, wx.TIMER_ONE_SHOT )
        
    
    def EventRemove( self, event ):
        
        selection = self._outer_queue.GetSelection()
        
        if selection != wx.NOT_FOUND: self._outer_queue.Delete( selection )
        
    
    def EventDown( self, event ):
        
        selection = self._outer_queue.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            if selection + 1 < self._outer_queue.GetCount():
                
                url = self._outer_queue.GetClientData( selection )
                
                self._outer_queue.Delete( selection )
                
                self._outer_queue.Insert( url, selection + 1, url )
                
                self._outer_queue.Select( selection + 1 )
                
            
        
    
    def SetOuterQueueInfo( self, page_key, info ):
        
        if self._page_key == page_key: self._outer_queue_info.SetLabel( info )
        
    
    def SetImportInfo( self, page_key, info ):
        
        if self._page_key == page_key: self._import_current_info.SetLabel( info )
        
    
    def SetSearchFocus( self, page_key ):
        
        if page_key == self._page_key: self._new_queue_input.SetFocus()
        
    
class ManagementPanelImportWithQueueAdvanced( ManagementPanelImportWithQueue ):
    
    def __init__( self, parent, page, page_key, name, namespaces ):
        
        ManagementPanelImportWithQueue.__init__( self, parent, page, page_key )
        
        self._advanced_tag_options = ClientGUICommon.AdvancedTagOptions( self, 'send ' + name + ' tags to ', namespaces )
        
        self._outer_queue_pause_button = wx.Button( self._outer_queue_panel, label = 'pause' )
        self._outer_queue_pause_button.Bind( wx.EVT_BUTTON, self.EventPauseOuterQueue )
        self._outer_queue_pause_button.Disable()
        
        self._outer_queue_cancel_button = wx.Button( self._outer_queue_panel, label = 'that\'s enough' )
        self._outer_queue_cancel_button.Bind( wx.EVT_BUTTON, self.EventCancelOuterQueue )
        self._outer_queue_cancel_button.SetForegroundColour( ( 128, 0, 0 ) )
        self._outer_queue_cancel_button.Disable()
        
        c_p_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        c_p_hbox.AddF( self._import_pause_button, FLAGS_EXPAND_BOTH_WAYS )
        c_p_hbox.AddF( self._import_cancel_button, FLAGS_EXPAND_BOTH_WAYS )
        
        self._processing_panel.AddF( self._import_overall_info, FLAGS_EXPAND_PERPENDICULAR )
        self._processing_panel.AddF( self._import_current_info, FLAGS_EXPAND_PERPENDICULAR )
        self._processing_panel.AddF( self._import_gauge, FLAGS_EXPAND_PERPENDICULAR )
        self._processing_panel.AddF( c_p_hbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        queue_buttons_vbox = wx.BoxSizer( wx.VERTICAL )
        
        queue_buttons_vbox.AddF( self._up, FLAGS_MIXED )
        queue_buttons_vbox.AddF( self._remove, FLAGS_MIXED )
        queue_buttons_vbox.AddF( self._down, FLAGS_MIXED )
        
        queue_pause_buttons_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        queue_pause_buttons_hbox.AddF( self._outer_queue_pause_button, FLAGS_EXPAND_BOTH_WAYS )
        queue_pause_buttons_hbox.AddF( self._outer_queue_cancel_button, FLAGS_EXPAND_BOTH_WAYS )
        
        queue_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        queue_hbox.AddF( self._outer_queue, FLAGS_EXPAND_BOTH_WAYS )
        queue_hbox.AddF( queue_buttons_vbox, FLAGS_MIXED )
        
        self._outer_queue_panel.AddF( queue_pause_buttons_hbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._outer_queue_panel.AddF( self._outer_queue_info, FLAGS_EXPAND_PERPENDICULAR )
        self._outer_queue_panel.AddF( queue_hbox, FLAGS_EXPAND_SIZER_BOTH_WAYS )
        self._outer_queue_panel.AddF( self._new_queue_input, FLAGS_EXPAND_PERPENDICULAR )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        self._MakeSort( vbox )
        
        vbox.AddF( self._processing_panel, FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._outer_queue_panel, FLAGS_EXPAND_BOTH_WAYS )
        self._InitExtraVboxElements( vbox )
        vbox.AddF( self._advanced_import_options, FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._advanced_tag_options, FLAGS_EXPAND_PERPENDICULAR )
        
        self._MakeCurrentSelectionTagsBox( vbox )
        
        self.SetSizer( vbox )
        
    
    # this could be in the advanced_tag_options class
    def _DoRedundantTagContentUpdates( self, hash, tags ):
        
        tag_import_info = self._advanced_tag_options.GetInfo()
        
        if len( tag_import_info ) > 0:
            
            content_updates = []
            
            for ( service_identifier, namespaces ) in tag_import_info:
                
                if len( namespaces ) > 0:
                    
                    tags_to_add_here = []
                    
                    for namespace in namespaces:
                        
                        if namespace == '': tags_to_add_here.extend( [ HC.CleanTag( tag ) for tag in tags if not ':' in tag ] )
                        else: tags_to_add_here.extend( [ HC.CleanTag( tag ) for tag in tags if tag.startswith( namespace + ':' ) ] )
                        
                    
                    if len( tags_to_add_here ) > 0:
                        
                        if service_identifier == CC.LOCAL_TAG_SERVICE_IDENTIFIER: action = CC.CONTENT_UPDATE_ADD
                        else: action = CC.CONTENT_UPDATE_PENDING
                        
                        edit_log = [ ( action, tag ) for tag in tags_to_add_here ]
                        
                        content_updates.append( HC.ContentUpdate( CC.CONTENT_UPDATE_EDIT_LOG, service_identifier, ( hash, ), info = edit_log ) )
                        
                    
                
            
            if len( content_updates ) > 0: wx.GetApp().Write( 'content_updates', content_updates )
            
        
    
    # this should probably be in the advanced_tag_options class
    def _GetServiceIdentifiersToTags( self, tags ):
        
        tags = [ tag for tag in tags if tag is not None ]
        
        service_identifiers_to_tags = {}
        
        for ( service_identifier, namespaces ) in self._advanced_tag_options.GetInfo():
            
            if len( namespaces ) > 0:
                
                tags_to_add_here = []
                
                for namespace in namespaces:
                    
                    if namespace == '': tags_to_add_here.extend( [ HC.CleanTag( tag ) for tag in tags if not ':' in tag ] )
                    else: tags_to_add_here.extend( [ HC.CleanTag( tag ) for tag in tags if tag.startswith( namespace + ':' ) ] )
                    
                
                if len( tags_to_add_here ) > 0: service_identifiers_to_tags[ service_identifier ] = tags_to_add_here
                
            
        
        return service_identifiers_to_tags
        
    
    def _InitExtraVboxElements( self, vbox ): pass
    
    def _SetButtons( self ):
        
        if self._currently_processing_import_queue:
            
            self._import_pause_button.Enable()
            self._import_cancel_button.Enable()
            
        else:
            
            self._import_pause_button.Disable()
            self._import_cancel_button.Disable()
            
        
        if self._currently_processing_outer_queue:
            
            self._outer_queue_pause_button.Enable()
            self._outer_queue_cancel_button.Enable()
            
        else:
            
            self._outer_queue_pause_button.Disable()
            self._outer_queue_cancel_button.Disable()
            
        
    
    def EventCancelOuterQueue( self, event ):
        
        self._cancel_outer_queue.set()
        
        if self._pause_outer_queue: self.EventPauseOuterQueue( event )
        
    
    def EventPauseOuterQueue( self, event ):
        
        if self._pause_outer_queue:
            
            self._pause_outer_queue = False
            
            self._outer_queue_pause_button.SetLabel( 'pause' )
            self._outer_queue_pause_button.SetForegroundColour( ( 0, 0, 0 ) )
            
        else:
            
            self._pause_outer_queue = True
            
            self._outer_queue_pause_button.SetLabel( 'resume' )
            self._outer_queue_pause_button.SetForegroundColour( ( 0, 128, 0 ) )
            
        
    
class ManagementPanelImportWithQueueAdvancedBooru( ManagementPanelImportWithQueueAdvanced ):
    
    def __init__( self, parent, page, page_key, booru ):
        
        self._booru = booru
        
        name = self._booru.GetName()
        namespaces = booru.GetNamespaces()
        
        ManagementPanelImportWithQueueAdvanced.__init__( self, parent, page, page_key, name, namespaces )
        
    
    def _GetImageUrlAndTags( self, html, url ):
        
        ( search_url, search_separator, gallery_advance_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces ) = self._booru.GetData()
        
        ( image_url, tags ) = ClientParsers.ParseBooruPage( html, url, tag_classnames_to_namespaces, image_id = image_id, image_data = image_data )
        
        return ( image_url, tags )
        
    
    def _THREADGetImportArgs( self, queue_object ):
        
        try:
            
            url = queue_object
            
            ( status, hash ) = wx.GetApp().Read( 'url_status', url )
            
            if status == 'deleted' and 'exclude_deleted_files' not in self._advanced_import_options.GetInfo(): status = 'new'
            
            if status == 'deleted': HC.pubsub.pub( 'import_done', self._page_key, 'deleted' )
            elif status == 'redundant':
                
                ( media_result, ) = wx.GetApp().Read( 'media_results', CC.FileSearchContext(), ( hash, ) )
                
                HC.pubsub.pub( 'add_media_result', self._page_key, media_result )
                
                tag_import_info = self._advanced_tag_options.GetInfo()
                
                if len( tag_import_info ) > 0:
                    
                    parse_result = urlparse.urlparse( url )
                    
                    ( scheme, host, port ) = ( parse_result.scheme, parse_result.hostname, parse_result.port )
                    
                    if ( scheme, host, port ) not in self._connections: self._connections[ ( scheme, host, port ) ] = CC.AdvancedHTTPConnection( scheme = scheme, host = host, port = port )
                    
                    connection = self._connections[ ( scheme, host, port ) ]
                    
                    html = connection.geturl( url )
                    
                    ( image_url, tags ) = self._GetImageUrlAndTags( html, url )
                    
                    self._DoRedundantTagContentUpdates( hash, tags )
                    
                
                HC.pubsub.pub( 'import_done', self._page_key, 'redundant' )
                
            else:
                
                HC.pubsub.pub( 'set_import_info', self._page_key, 'downloading ' + str( self._import_queue_position + 1 ) + '/' + str( len( self._import_queue ) ) )
                
                parse_result = urlparse.urlparse( url )
                
                ( scheme, host, port ) = ( parse_result.scheme, parse_result.hostname, parse_result.port )
                
                if ( scheme, host, port ) not in self._connections: self._connections[ ( scheme, host, port ) ] = CC.AdvancedHTTPConnection( scheme = scheme, host = host, port = port )
                
                connection = self._connections[ ( scheme, host, port ) ]
                
                html = connection.geturl( url )
                
                ( image_url, tags ) = self._GetImageUrlAndTags( html, url )
                
                parse_result = urlparse.urlparse( image_url )
                
                ( scheme, host, port ) = ( parse_result.scheme, parse_result.hostname, parse_result.port )
                
                if ( scheme, host, port ) not in self._connections: self._connections[ ( scheme, host, port ) ] = CC.AdvancedHTTPConnection( scheme = scheme, host = host, port = port )
                
                connection = self._connections[ ( scheme, host, port ) ]
                
                file = connection.geturl( image_url )
                
                service_identifiers_to_tags = self._GetServiceIdentifiersToTags( tags )
                
                advanced_import_options = self._advanced_import_options.GetInfo()
                
                wx.CallAfter( self.CALLBACKImportArgs, file, advanced_import_options, service_identifiers_to_tags, url = url )
                
            
        except Exception as e:
            print( traceback.format_exc() )
            wx.CallAfter( self.CALLBACKImportArgs, self._page_key, '', {}, {}, exception = e )
        
    
    def _THREADDownloadImportItems( self, tags_string ):
        
        # this is important, because we'll instantiate new objects in the eventcancel
        
        cancel_import = self._cancel_import_queue
        cancel_download = self._cancel_outer_queue
        
        try:
            
            tags = tags_string.split( ' ' )
            
            ( search_url, gallery_advance_num, search_separator, thumb_classname ) = self._booru.GetGalleryParsingInfo()
            
            urls = []
            
            example_url = search_url.replace( '%tags%', search_separator.join( tags ) ).replace( '%index%', '0' )
            
            connection = CC.AdvancedHTTPConnection( url = example_url )
            
            if gallery_advance_num == 1: i = 1 # page 1, 2, 3
            else: i = 0 # index 0, 25, 50
            
            total_urls_found = 0
            
            while True:
                
                HC.pubsub.pub( 'set_outer_queue_info', self._page_key, 'found ' + str( total_urls_found ) + ' urls' )
                
                while self._pause_outer_queue: time.sleep( 1 )
                
                if cancel_import.is_set(): break
                if cancel_download.is_set(): break
                
                current_url = search_url.replace( '%tags%', search_separator.join( tags ) ).replace( '%index%', str( i * gallery_advance_num ) )
                
                html = connection.geturl( current_url )
                
                urls = ClientParsers.ParseBooruGallery( html, current_url, thumb_classname )
                
                total_urls_found += len( urls )
                
                if len( urls ) == 0: break
                else: wx.CallAfter( self.CALLBACKAddToImportQueue, urls )
                
                i += 1
                
            
            HC.pubsub.pub( 'set_outer_queue_info', self._page_key, '' )
            
        except HC.NotFoundException: pass
        except Exception as e:
            print( traceback.format_exc() )
            HC.pubsub.pub( 'set_outer_queue_info', self._page_key, unicode( e ) )
        
        HC.pubsub.pub( 'done_adding_to_import_queue', self._page_key )
        
    
class ManagementPanelImportWithQueueAdvancedDeviantArt( ManagementPanelImportWithQueueAdvanced ):
    
    def __init__( self, parent, page, page_key ):
        
        name = 'deviant art'
        namespaces = [ 'creator', 'title', '' ]
        
        ManagementPanelImportWithQueueAdvanced.__init__( self, parent, page, page_key, name, namespaces )
        
        self._new_queue_input.SetValue( 'artist username' )
        
    
    def _THREADGetImportArgs( self, queue_object ):
        
        try:
            
            ( url, tags ) = queue_object
            
            ( status, hash ) = wx.GetApp().Read( 'url_status', url )
            
            if status == 'deleted' and 'exclude_deleted_files' not in self._advanced_import_options.GetInfo(): status = 'new'
            
            if status == 'deleted': HC.pubsub.pub( 'import_done', self._page_key, 'deleted' )
            elif status == 'redundant':
                
                ( media_result, ) = wx.GetApp().Read( 'media_results', CC.FileSearchContext(), ( hash, ) )
                
                HC.pubsub.pub( 'add_media_result', self._page_key, media_result )
                
                self._DoRedundantTagContentUpdates( hash, tags )
                
                HC.pubsub.pub( 'import_done', self._page_key, 'redundant' )
                
            else:
                
                HC.pubsub.pub( 'set_import_info', self._page_key, 'downloading ' + str( self._import_queue_position + 1 ) + '/' + str( len( self._import_queue ) ) )
                
                parse_result = urlparse.urlparse( url )
                
                ( scheme, host, port ) = ( parse_result.scheme, parse_result.hostname, parse_result.port )
                
                if ( scheme, host, port ) not in self._connections: self._connections[ ( scheme, host, port ) ] = CC.AdvancedHTTPConnection( scheme = scheme, host = host, port = port )
                
                connection = self._connections[ ( scheme, host, port ) ]
                
                file = connection.geturl( url )
                
                service_identifiers_to_tags = self._GetServiceIdentifiersToTags( tags )
                
                advanced_import_options = self._advanced_import_options.GetInfo()
                
                wx.CallAfter( self.CALLBACKImportArgs, file, advanced_import_options, service_identifiers_to_tags, url = url )
                
            
        except HC.NotFoundException: wx.CallAfter( self.CALLBACKImportArgs, '', {}, {}, exception = Exception( 'Cannot download full image.' ) )
        except Exception as e:
            print( traceback.format_exc() )
            wx.CallAfter( self.CALLBACKImportArgs, '', {}, {}, exception = e )
        
    
    def _THREADDownloadImportItems( self, artist ):
        
        # this is important, because we'll instantiate new objects in the eventcancel
        
        cancel_import = self._cancel_import_queue
        cancel_download = self._cancel_outer_queue
        
        try:
            
            gallery_url = 'http://' + artist + '.deviantart.com/gallery/?catpath=/&offset='
            
            example_url = gallery_url + '0'
            
            connection = CC.AdvancedHTTPConnection( url = example_url )
            
            i = 0
            
            total_results_found = 0
            
            while True:
                
                HC.pubsub.pub( 'set_outer_queue_info', self._page_key, 'found ' + str( total_results_found ) + ' urls' )
                
                while self._pause_outer_queue: time.sleep( 1 )
                
                if cancel_import.is_set(): break
                if cancel_download.is_set(): break
                
                current_url = gallery_url + str( i )
                
                html = connection.geturl( current_url )
                
                results = ClientParsers.ParseDeviantArtGallery( html )
                
                total_results_found += len( results )
                
                if len( results ) == 0: break
                else: wx.CallAfter( self.CALLBACKAddToImportQueue, results )
                
                i += 24
                
            
            HC.pubsub.pub( 'set_outer_queue_info', self._page_key, '' )
            
        except Exception as e:
            print( traceback.format_exc() )
            HC.pubsub.pub( 'set_outer_queue_info', self._page_key, unicode( e ) )
        
        HC.pubsub.pub( 'done_adding_to_import_queue', self._page_key )
        
    
class ManagementPanelImportWithQueueAdvancedGiphy( ManagementPanelImportWithQueueAdvanced ):
    
    def __init__( self, parent, page, page_key ):
        
        name = 'giphy'
        namespaces = [ '' ]
        
        ManagementPanelImportWithQueueAdvanced.__init__( self, parent, page, page_key, name, namespaces )
        
        self._new_queue_input.SetValue( 'tag' )
        
    
    def _GetAndParseTags( self, id, timestamp ):
        
        url = 'http://giphy.com/api/gifs/' + str( id ) + '?ds=' + str( timestamp )
        
        parse_result = urlparse.urlparse( url )
        
        ( scheme, host, port ) = ( parse_result.scheme, parse_result.hostname, parse_result.port )
        
        if ( scheme, host, port ) not in self._connections: self._connections[ ( scheme, host, port ) ] = CC.AdvancedHTTPConnection( scheme = scheme, host = host, port = port )
        
        connection = self._connections[ ( scheme, host, port ) ]
        
        try:
            
            raw_json = connection.geturl( url )
            
            json_dict = json.loads( raw_json )
            
            tags_data = json_dict[ 'data' ][ 'tags' ]
            
            tags = [ tag_data[ 'name' ] for tag_data in tags_data ]
            
        except:
            
            print( traceback.format_exc() )
            
            tags = []
            
        
        return tags
        
    
    def _THREADGetImportArgs( self, queue_object ):
        
        try:
            
            ( url, id, timestamp ) = queue_object
            
            ( status, hash ) = wx.GetApp().Read( 'url_status', url )
            
            if status == 'deleted' and 'exclude_deleted_files' not in self._advanced_import_options.GetInfo(): status = 'new'
            
            if status == 'deleted': HC.pubsub.pub( 'import_done', self._page_key, 'deleted' )
            elif status == 'redundant':
                
                ( media_result, ) = wx.GetApp().Read( 'media_results', CC.FileSearchContext(), ( hash, ) )
                
                HC.pubsub.pub( 'add_media_result', self._page_key, media_result )
                
                tag_import_info = self._advanced_tag_options.GetInfo()
                
                if len( tag_import_info ) > 0:
                    
                    try:
                        
                        tags = self._GetAndParseTags( id, timestamp )
                        
                        self._DoRedundantTagContentUpdates( hash, tags )
                        
                    except: pass
                    
                
                HC.pubsub.pub( 'import_done', self._page_key, 'redundant' )
                
            else:
                
                HC.pubsub.pub( 'set_import_info', self._page_key, 'downloading ' + str( self._import_queue_position + 1 ) + '/' + str( len( self._import_queue ) ) )
                
                parse_result = urlparse.urlparse( url )
                
                ( scheme, host, port ) = ( parse_result.scheme, parse_result.hostname, parse_result.port )
                
                if ( scheme, host, port ) not in self._connections: self._connections[ ( scheme, host, port ) ] = CC.AdvancedHTTPConnection( scheme = scheme, host = host, port = port )
                
                connection = self._connections[ ( scheme, host, port ) ]
                
                file = connection.geturl( url )
                
                tags = self._GetAndParseTags( id, timestamp )
                
                service_identifiers_to_tags = self._GetServiceIdentifiersToTags( tags )
                
                advanced_import_options = self._advanced_import_options.GetInfo()
                
                wx.CallAfter( self.CALLBACKImportArgs, file, advanced_import_options, service_identifiers_to_tags, url = url )
                
            
        except HC.NotFoundException: wx.CallAfter( self.CALLBACKImportArgs, '', {}, {}, exception = Exception( 'Cannot download full image.' ) )
        except Exception as e:
            print( traceback.format_exc() )
            wx.CallAfter( self.CALLBACKImportArgs, '', {}, {}, exception = e )
        
    
    def _THREADDownloadImportItems( self, tag ):
        
        # this is important, because we'll instantiate new objects in the eventcancel
        
        cancel_import = self._cancel_import_queue
        cancel_download = self._cancel_outer_queue
        
        try:
            
            gallery_url = 'http://giphy.com/api/gifs?tag=' + tag.replace( ' ', '+' ) + '&page='
            
            example_url = gallery_url + '0'
            
            connection = CC.AdvancedHTTPConnection( url = example_url )
            
            i = 0
            
            total_results_found = 0
            
            while True:
                
                HC.pubsub.pub( 'set_outer_queue_info', self._page_key, 'found ' + str( total_results_found ) + ' urls' )
                
                while self._pause_outer_queue: time.sleep( 1 )
                
                if cancel_import.is_set(): break
                if cancel_download.is_set(): break
                
                current_url = gallery_url + str( i )
                
                raw_json = connection.geturl( current_url )
                
                json_dict = json.loads( raw_json )
                
                if 'data' in json_dict:
                    
                    json_data = json_dict[ 'data' ]
                    
                    results = [ ( d[ 'original_url' ], d[ 'id' ], d[ 'timestamp' ] ) for d in json_data ]
                    
                    total_results_found += len( results )
                    
                    wx.CallAfter( self.CALLBACKAddToImportQueue, results )
                    
                else: break
                
                i += 1
                
            
            HC.pubsub.pub( 'set_outer_queue_info', self._page_key, '' )
            
        except Exception as e:
            print( traceback.format_exc() )
            HC.pubsub.pub( 'set_outer_queue_info', self._page_key, unicode( e ) )
        
        HC.pubsub.pub( 'done_adding_to_import_queue', self._page_key )
        
    
class ManagementPanelImportWithQueueAdvancedHentaiFoundry( ManagementPanelImportWithQueueAdvanced ):
    
    def __init__( self, parent, page, page_key ):
        
        name = 'hentai foundry'
        namespaces = [ 'creator', 'title', '' ]
        
        ManagementPanelImportWithQueueAdvanced.__init__( self, parent, page, page_key, name, namespaces )
        
        self._session_established = False
        
        self._new_queue_input.Disable()
        
        HC.pubsub.sub( self, 'SessionEstablished', 'import_session_established' )
        
        threading.Thread( target = self._THREADEstablishSession, name = 'HF Session Thread' ).start()
        
    
    def _InitExtraVboxElements( self, vbox ):
        
        self._advanced_hentai_foundry_options = ClientGUICommon.AdvancedHentaiFoundryOptions( self )
        
        vbox.AddF( self._advanced_hentai_foundry_options, FLAGS_EXPAND_PERPENDICULAR )
        
    
    def _SetFilter( self ):
        
        filter = self._advanced_hentai_foundry_options.GetInfo()
        
        cookies = self._search_connection.GetCookies()
        
        raw_csrf = cookies[ 'YII_CSRF_TOKEN' ] # YII_CSRF_TOKEN=19b05b536885ec60b8b37650a32f8deb11c08cd1s%3A40%3A%222917dcfbfbf2eda2c1fbe43f4d4c4ec4b6902b32%22%3B
        
        processed_csrf = urllib.unquote( raw_csrf ) # 19b05b536885ec60b8b37650a32f8deb11c08cd1s:40:"2917dcfbfbf2eda2c1fbe43f4d4c4ec4b6902b32";
        
        csrf_token = processed_csrf.split( '"' )[1] # the 2917... bit
        
        filter[ 'YII_CSRF_TOKEN' ] = csrf_token
        
        body = urllib.urlencode( filter )
        
        headers = {}
        headers[ 'Content-Type' ] = 'application/x-www-form-urlencoded'
        
        self._search_connection.request( 'POST', '/site/filters', headers = headers, body = body )
        
    
    def _THREADGetImportArgs( self, queue_object ):
        
        try:
            
            url = queue_object
            
            ( status, hash ) = wx.GetApp().Read( 'url_status', url )
            
            if status == 'deleted' and 'exclude_deleted_files' not in self._advanced_import_options.GetInfo(): status = 'new'
            
            if status == 'deleted': HC.pubsub.pub( 'import_done', self._page_key, 'deleted' )
            elif status == 'redundant':
                
                ( media_result, ) = wx.GetApp().Read( 'media_results', CC.FileSearchContext(), ( hash, ) )
                
                HC.pubsub.pub( 'add_media_result', self._page_key, media_result )
                
                tag_import_info = self._advanced_tag_options.GetInfo()
                
                if len( tag_import_info ) > 0:
                    
                    html = self._page_connection.geturl( url )
                    
                    ( image_url, tags ) = ClientParsers.ParseHentaiFoundryPage( html )
                    
                    self._DoRedundantTagContentUpdates( hash, tags )
                    
                
                HC.pubsub.pub( 'import_done', self._page_key, 'redundant' )
                
            else:
                
                HC.pubsub.pub( 'set_import_info', self._page_key, 'downloading ' + str( self._import_queue_position + 1 ) + '/' + str( len( self._import_queue ) ) )
                
                html = self._page_connection.geturl( url )
                
                ( image_url, tags ) = ClientParsers.ParseHentaiFoundryPage( html )
                
                parse_result = urlparse.urlparse( image_url )
                
                ( scheme, host, port ) = ( parse_result.scheme, parse_result.hostname, parse_result.port )
                
                if ( scheme, host, port ) not in self._connections: self._connections[ ( scheme, host, port ) ] = CC.AdvancedHTTPConnection( scheme = scheme, host = host, port = port )
                
                connection = self._connections[ ( scheme, host, port ) ]
                
                file = connection.geturl( image_url )
                
                service_identifiers_to_tags = self._GetServiceIdentifiersToTags( tags )
                
                advanced_import_options = self._advanced_import_options.GetInfo()
                
                wx.CallAfter( self.CALLBACKImportArgs, file, advanced_import_options, service_identifiers_to_tags, url = url )
                
            
        except HC.NotFoundException: wx.CallAfter( self.CALLBACKImportArgs, '', {}, {}, exception = Exception( 'Cannot download full image.' ) )
        except Exception as e:
            print( traceback.format_exc() )
            wx.CallAfter( self.CALLBACKImportArgs, '', {}, {}, exception = e )
        
    
    def _THREADEstablishSession( self ):
        
        try:
            
            self._search_connection = CC.AdvancedHTTPConnection( url = 'http://www.hentai-foundry.com', accept_cookies = True )
            self._page_connection = CC.AdvancedHTTPConnection( url = 'http://www.hentai-foundry.com', accept_cookies = True )
            
            HC.pubsub.pub( 'set_outer_queue_info', self._page_key, 'establishing session with hentai foundry' )
            
            # this establishes the php session cookie, the csrf cookie, and tells hf that we are 18 years of age
            self._search_connection.request( 'GET', '/?enterAgree=1' )
            
            cookies = self._search_connection.GetCookies()
            
            for ( key, value ) in cookies.items(): self._page_connection.SetCookie( key, value )
            
            HC.pubsub.pub( 'set_outer_queue_info', self._page_key, 'session established' )
            
            time.sleep( 0.5 )
            
            HC.pubsub.pub( 'import_session_established', self._page_key )
            
        except Exception as e:
            print( traceback.format_exc() )
            HC.pubsub.pub( 'set_outer_queue_info', self._page_key, unicode( e ) )
        
    
    def SessionEstablished( self, page_key ):
        
        self._new_queue_input.Enable()
        
        self._session_established = True
        
        HC.pubsub.pub( 'set_outer_queue_info', self._page_key, 'session established - ready to download' )
        
    
class ManagementPanelImportWithQueueAdvancedHentaiFoundryArtist( ManagementPanelImportWithQueueAdvancedHentaiFoundry ):
    
    def __init__( self, parent, page, page_key ):
        
        ManagementPanelImportWithQueueAdvancedHentaiFoundry.__init__( self, parent, page, page_key )
        
        self._new_queue_input.SetValue( 'artist username' )
        
    
    def _THREADDownloadImportItems( self, artist ):
        
        # this is important, because we'll instantiate new objects in the eventcancel
        
        cancel_import = self._cancel_import_queue
        cancel_download = self._cancel_outer_queue
        
        try:
            
            self._SetFilter()
            
            pictures_done = False
            scraps_done = False
            
            currently_doing = 'pictures'
            
            total_results_found = 0
            
            i = 1
            
            while True:
                
                HC.pubsub.pub( 'set_outer_queue_info', self._page_key, 'found ' + str( total_results_found ) + ' urls' )
                
                while self._pause_outer_queue: time.sleep( 1 )
                
                if cancel_import.is_set(): break
                if cancel_download.is_set(): break
                
                if currently_doing == 'pictures': gallery_url = 'http://www.hentai-foundry.com/pictures/user/' + artist
                else: gallery_url = 'http://www.hentai-foundry.com/pictures/user/' + artist + '/scraps'
                
                current_url = gallery_url + '/page/' + str( i )
                
                html = self._search_connection.geturl( current_url )
                
                urls = ClientParsers.ParseHentaiFoundryGallery( html )
                
                total_results_found += len( urls )
                
                wx.CallAfter( self.CALLBACKAddToImportQueue, urls )
                
                if 'class="next"' not in html:
                    
                    if currently_doing == 'pictures': pictures_done = True
                    else: scraps_done = True
                    
                
                if pictures_done and scraps_done: break
                
                if currently_doing == 'pictures':
                    
                    if scraps_done: i += 1
                    else: currently_doing = 'scraps'
                    
                else:
                    
                    if not pictures_done: currently_doing = 'pictures'
                    
                    i += 1
                    
                
            
            HC.pubsub.pub( 'set_outer_queue_info', self._page_key, '' )
            
        except HC.NotFoundException:
            
            HC.pubsub.pub( 'set_outer_queue_info', self._page_key, '404 - artist not found!' )
            
        except Exception as e:
            print( traceback.format_exc() )
            HC.pubsub.pub( 'set_outer_queue_info', self._page_key, unicode( e ) )
        
        HC.pubsub.pub( 'done_adding_to_import_queue', self._page_key )
        
    
class ManagementPanelImportWithQueueAdvancedHentaiFoundryTags( ManagementPanelImportWithQueueAdvancedHentaiFoundry ):
    
    def __init__( self, parent, page, page_key ):
        
        ManagementPanelImportWithQueueAdvancedHentaiFoundry.__init__( self, parent, page, page_key )
        
        self._new_queue_input.SetValue( 'search tags' )
        
    
    def _THREADDownloadImportItems( self, tags_string ):
        
        # this is important, because we'll instantiate new objects in the eventcancel
        
        cancel_import = self._cancel_import_queue
        cancel_download = self._cancel_outer_queue
        
        try:
            
            self._SetFilter()
            
            tags = tags_string.split( ' ' )
            
            gallery_url = 'http://www.hentai-foundry.com/search/pictures?query=' + '+'.join( tags ) + '&search_in=all&scraps=-1&page='
                # scraps = 0 hide
                # -1 means show both
                # 1 means scraps only. wetf
            
            total_results_found = 0
            
            i = 1
            
            while True:
                
                HC.pubsub.pub( 'set_outer_queue_info', self._page_key, 'found ' + str( total_results_found ) + ' urls' )
                
                while self._pause_outer_queue: time.sleep( 1 )
                
                if cancel_import.is_set(): break
                if cancel_download.is_set(): break
                
                current_url = gallery_url + str( i )
                
                html = self._search_connection.geturl( current_url )
                
                urls = ClientParsers.ParseHentaiFoundryGallery( html )
                
                total_results_found += len( urls )
                
                if 'class="next"' not in html: break
                else: wx.CallAfter( self.CALLBACKAddToImportQueue, urls )
                
                i += 1
                
            
            HC.pubsub.pub( 'set_outer_queue_info', self._page_key, '' )
            
        except Exception as e:
            print( traceback.format_exc() )
            HC.pubsub.pub( 'set_outer_queue_info', self._page_key, unicode( e ) )
        
        HC.pubsub.pub( 'done_adding_to_import_queue', self._page_key )
        
    
class ManagementPanelImportWithQueueAdvancedPixiv( ManagementPanelImportWithQueueAdvanced ):
    
    def __init__( self, parent, page, page_key ):
        
        name = 'pixiv'
        namespaces = [ 'creator', 'title', '' ]
        
        ManagementPanelImportWithQueueAdvanced.__init__( self, parent, page, page_key, name, namespaces )
        
        self._session_established = False
        
        self._new_queue_input.Disable()
        
        HC.pubsub.sub( self, 'SessionEstablished', 'import_session_established' )
        
        threading.Thread( target = self._THREADEstablishSession, name = 'Pixiv Session Thread' ).start()
        
    
    def _THREADGetImportArgs( self, queue_object ):
        
        try:
            
            ( url, image_url_reference_url, image_url ) = queue_object
            
            ( status, hash ) = wx.GetApp().Read( 'url_status', url )
            
            if status == 'deleted' and 'exclude_deleted_files' not in self._advanced_import_options.GetInfo(): status = 'new'
            
            if status == 'deleted': HC.pubsub.pub( 'import_done', self._page_key, 'deleted' )
            elif status == 'redundant':
                
                ( media_result, ) = wx.GetApp().Read( 'media_results', CC.FileSearchContext(), ( hash, ) )
                
                HC.pubsub.pub( 'add_media_result', self._page_key, media_result )
                
                tag_import_info = self._advanced_tag_options.GetInfo()
                
                if len( tag_import_info ) > 0:
                    
                    html = self._page_connection.geturl( url )
                    
                    tags = ClientParsers.ParsePixivPage( image_url, html )
                    
                    self._DoRedundantTagContentUpdates( hash, tags )
                    
                
                HC.pubsub.pub( 'import_done', self._page_key, 'redundant' )
                
            else:
                
                HC.pubsub.pub( 'set_import_info', self._page_key, 'downloading ' + str( self._import_queue_position + 1 ) + '/' + str( len( self._import_queue ) ) )
                
                tag_import_info = self._advanced_tag_options.GetInfo()
                
                if len( tag_import_info ) > 0:
                    
                    html = self._page_connection.geturl( url )
                    
                    tags = ClientParsers.ParsePixivPage( image_url, html )
                    
                else: tags = []
                
                parse_result = urlparse.urlparse( image_url )
                
                ( scheme, host, port ) = ( parse_result.scheme, parse_result.hostname, parse_result.port )
                
                if ( scheme, host, port ) not in self._connections: self._connections[ ( scheme, host, port ) ] = CC.AdvancedHTTPConnection( scheme = scheme, host = host, port = port )
                
                connection = self._connections[ ( scheme, host, port ) ]
                
                headers = { 'Referer' : image_url_reference_url }
                
                file = connection.geturl( image_url, headers = headers )
                
                service_identifiers_to_tags = self._GetServiceIdentifiersToTags( tags )
                
                advanced_import_options = self._advanced_import_options.GetInfo()
                
                wx.CallAfter( self.CALLBACKImportArgs, file, advanced_import_options, service_identifiers_to_tags, url = url )
                
            
        except HC.NotFoundException:
            wx.CallAfter( self.CALLBACKImportArgs, '', {}, {}, exception = Exception( 'Cannot download full image - it is probably a manga collection.' ) )
        except Exception as e:
            print( traceback.format_exc() )
            wx.CallAfter( self.CALLBACKImportArgs, '', {}, {}, exception = e )
        
    
    def _THREADEstablishSession( self ):
        
        try:
            
            ( id, password ) = wx.GetApp().Read( 'pixiv_account' )
            
            if id == '' and password == '':
                
                HC.pubsub.pub( 'set_outer_queue_info', self._page_key, 'You need to set up your pixiv credentials in services->manage pixiv account.' )
                
                return
                
            
            self._search_connection = CC.AdvancedHTTPConnection( url = 'http://www.pixiv.net', accept_cookies = True )
            self._page_connection = CC.AdvancedHTTPConnection( url = 'http://www.pixiv.net', accept_cookies = True )
            
            HC.pubsub.pub( 'set_outer_queue_info', self._page_key, 'establishing session with pixiv' )
            
            form_fields = {}
            
            form_fields[ 'mode' ] = 'login'
            form_fields[ 'pixiv_id' ] = id
            form_fields[ 'pass' ] = password
            
            body = urllib.urlencode( form_fields )
            
            headers = {}
            headers[ 'Content-Type' ] = 'application/x-www-form-urlencoded'
            
            # this logs in and establishes the php session cookie
            response = self._search_connection.request( 'POST', '/login.php', headers = headers, body = body, follow_redirects = False )
            
            cookies = self._search_connection.GetCookies()
            
            # _ only given to logged in php sessions
            if 'PHPSESSID' not in cookies or '_' not in cookies[ 'PHPSESSID' ]: raise Exception( 'Login credentials not accepted!' )
            
            for ( key, value ) in cookies.items(): self._page_connection.SetCookie( key, value )
            
            HC.pubsub.pub( 'set_outer_queue_info', self._page_key, 'session established' )
            
            time.sleep( 0.5 )
            
            HC.pubsub.pub( 'import_session_established', self._page_key )
            
        except Exception as e:
            print( traceback.format_exc() )
            HC.pubsub.pub( 'set_outer_queue_info', self._page_key, unicode( e ) )
        
    
    def SessionEstablished( self, page_key ):
        
        self._new_queue_input.Enable()
        
        self._session_established = True
        
        HC.pubsub.pub( 'set_outer_queue_info', self._page_key, 'session established - ready to download' )
        
    
class ManagementPanelImportWithQueueAdvancedPixivArtist( ManagementPanelImportWithQueueAdvancedPixiv ):
    
    def __init__( self, parent, page, page_key ):
        
        ManagementPanelImportWithQueueAdvancedPixiv.__init__( self, parent, page, page_key )
        
        self._new_queue_input.SetValue( 'artist id number' )
        
    
    def _THREADDownloadImportItems( self, artist_id ):
        
        # this is important, because we'll instantiate new objects in the eventcancel
        
        cancel_import = self._cancel_import_queue
        cancel_download = self._cancel_outer_queue
        
        try:
            
            total_results_found = 0
            
            i = 1
            
            while True:
                
                HC.pubsub.pub( 'set_outer_queue_info', self._page_key, 'found ' + str( total_results_found ) + ' urls' )
                
                while self._pause_outer_queue: time.sleep( 1 )
                
                if cancel_import.is_set(): break
                if cancel_download.is_set(): break
                
                gallery_url = 'http://www.pixiv.net/member_illust.php?id=' + str( artist_id )
                
                current_url = gallery_url + '&p=' + str( i )
                
                html = self._search_connection.geturl( current_url )
                
                results = ClientParsers.ParsePixivGallery( html, current_url )
                
                total_results_found += len( results )
                
                wx.CallAfter( self.CALLBACKAddToImportQueue, results )
                
                if len( results ) == 0: break
                
                i += 1
                
            
            HC.pubsub.pub( 'set_outer_queue_info', self._page_key, '' )
            
        except HC.NotFoundException:
            
            HC.pubsub.pub( 'set_outer_queue_info', self._page_key, '404 - artist not found!' )
            
        except Exception as e:
            print( traceback.format_exc() )
            HC.pubsub.pub( 'set_outer_queue_info', self._page_key, unicode( e ) )
        
        HC.pubsub.pub( 'done_adding_to_import_queue', self._page_key )
        
    
class ManagementPanelImportWithQueueAdvancedPixivTags( ManagementPanelImportWithQueueAdvancedPixiv ):
    
    def __init__( self, parent, page, page_key ):
        
        ManagementPanelImportWithQueueAdvancedPixiv.__init__( self, parent, page, page_key )
        
        self._new_queue_input.SetValue( 'search tag' )
        
    
    def _THREADDownloadImportItems( self, tag ):
        
        # this is important, because we'll instantiate new objects in the eventcancel
        
        cancel_import = self._cancel_import_queue
        cancel_download = self._cancel_outer_queue
        
        try:
            
            tag = urllib.quote( tag.encode( 'utf-8' ) )
            
            gallery_url = 'http://www.pixiv.net/search.php?word=' + tag + '&s_mode=s_tag_full&order=date_d'
            
            total_results_found = 0
            
            i = 1
            
            while True:
                
                HC.pubsub.pub( 'set_outer_queue_info', self._page_key, 'found ' + str( total_results_found ) + ' urls' )
                
                while self._pause_outer_queue: time.sleep( 1 )
                
                if cancel_import.is_set(): break
                if cancel_download.is_set(): break
                
                current_url = gallery_url + '&p=' + str( i )
                
                html = self._search_connection.geturl( current_url )
                
                results = ClientParsers.ParsePixivGallery( html, current_url )
                
                total_results_found += len( results )
                
                wx.CallAfter( self.CALLBACKAddToImportQueue, results )
                
                if len( results ) == 0: break
                
                i += 1
                
            
            HC.pubsub.pub( 'set_outer_queue_info', self._page_key, '' )
            
        except Exception as e:
            print( traceback.format_exc() )
            HC.pubsub.pub( 'set_outer_queue_info', self._page_key, unicode( e ) )
        
        HC.pubsub.pub( 'done_adding_to_import_queue', self._page_key )
        
    
class ManagementPanelImportWithQueueAdvancedTumblr( ManagementPanelImportWithQueueAdvanced ):
    
    def __init__( self, parent, page, page_key ):
        
        name = 'tumblr'
        namespaces = [ '' ]
        
        ManagementPanelImportWithQueueAdvanced.__init__( self, parent, page, page_key, name, namespaces )
        
        self._new_queue_input.SetValue( 'username' )
        
    
    def _ParseJSON( self, raw_json ):
        
        processed_raw_json = raw_json.split( 'var tumblr_api_read = ' )[1][:-2] # -2 takes a couple newline chars off at the end
        
        json_object = json.loads( processed_raw_json )
        
        results = []
        
        if 'posts' in json_object:
            
            for post in json_object[ 'posts' ]:
                
                if 'tags' in post: tags = post[ 'tags' ]
                else: tags = []
                
                post_type = post[ 'type' ]
                
                if post_type == 'photo':
                    
                    if len( post[ 'photos' ] ) == 0:
                        
                        try: results.append( ( post[ 'photo-url-1280' ], tags ) )
                        except: pass
                        
                    else:
                        
                        for photo in post[ 'photos' ]:
                            
                            try: results.append( ( photo[ 'photo-url-1280' ], tags ) )
                            except: pass
                            
                        
                    
                
            
        
        return results
        
    
    def _THREADGetImportArgs( self, queue_object ):
        
        try:
            
            ( url, tags ) = queue_object
            
            ( status, hash ) = wx.GetApp().Read( 'url_status', url )
            
            if status == 'deleted' and 'exclude_deleted_files' not in self._advanced_import_options.GetInfo(): status = 'new'
            
            if status == 'deleted': HC.pubsub.pub( 'import_done', self._page_key, 'deleted' )
            elif status == 'redundant':
                
                ( media_result, ) = wx.GetApp().Read( 'media_results', CC.FileSearchContext(), ( hash, ) )
                
                HC.pubsub.pub( 'add_media_result', self._page_key, media_result )
                
                tag_import_info = self._advanced_tag_options.GetInfo()
                
                if len( tag_import_info ) > 0: self._DoRedundantTagContentUpdates( hash, tags )
                
                HC.pubsub.pub( 'import_done', self._page_key, 'redundant' )
                
            else:
                
                HC.pubsub.pub( 'set_import_info', self._page_key, 'downloading ' + str( self._import_queue_position + 1 ) + '/' + str( len( self._import_queue ) ) )
                
                parse_result = urlparse.urlparse( url )
                
                ( scheme, host, port ) = ( parse_result.scheme, parse_result.hostname, parse_result.port )
                
                if ( scheme, host, port ) not in self._connections: self._connections[ ( scheme, host, port ) ] = CC.AdvancedHTTPConnection( scheme = scheme, host = host, port = port )
                
                connection = self._connections[ ( scheme, host, port ) ]
                
                file = connection.geturl( url )
                
                service_identifiers_to_tags = self._GetServiceIdentifiersToTags( tags )
                
                advanced_import_options = self._advanced_import_options.GetInfo()
                
                wx.CallAfter( self.CALLBACKImportArgs, file, advanced_import_options, service_identifiers_to_tags, url = url )
                
            
        except Exception as e:
            print( traceback.format_exc() )
            wx.CallAfter( self.CALLBACKImportArgs, self._page_key, '', {}, {}, exception = e )
        
    
    def _THREADDownloadImportItems( self, username ):
        
        # this is important, because we'll instantiate new objects in the eventcancel
        
        cancel_import = self._cancel_import_queue
        cancel_download = self._cancel_outer_queue
        
        try:
            
            search_url = 'http://' + username + '.tumblr.com/api/read/json?start=%start%&num=50'
            
            results = []
            
            example_url = search_url.replace( '%start%', '0' )
            
            connection = CC.AdvancedHTTPConnection( url = example_url )
            
            i = 0
            
            total_results_found = 0
            
            while True:
                
                HC.pubsub.pub( 'set_outer_queue_info', self._page_key, 'found ' + str( total_results_found ) + ' urls' )
                
                while self._pause_outer_queue: time.sleep( 1 )
                
                if cancel_import.is_set(): break
                if cancel_download.is_set(): break
                
                current_url = search_url.replace( '%start%', str( i ) )
                
                raw_json = connection.geturl( current_url )
                
                results = self._ParseJSON( raw_json )
                
                total_results_found += len( results )
                
                if len( results ) == 0: break
                else: wx.CallAfter( self.CALLBACKAddToImportQueue, results )
                
                i += 50
                
            
            HC.pubsub.pub( 'set_outer_queue_info', self._page_key, '' )
            
        except HC.NotFoundException: pass
        except Exception as e:
            print( traceback.format_exc() )
            HC.pubsub.pub( 'set_outer_queue_info', self._page_key, unicode( e ) )
        
        HC.pubsub.pub( 'done_adding_to_import_queue', self._page_key )
        
    
class ManagementPanelImportWithQueueURL( ManagementPanelImportWithQueue ):
    
    def __init__( self, parent, page, page_key ):
        
        ManagementPanelImportWithQueue.__init__( self, parent, page, page_key )
        
        c_p_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        c_p_hbox.AddF( self._import_pause_button, FLAGS_EXPAND_BOTH_WAYS )
        c_p_hbox.AddF( self._import_cancel_button, FLAGS_EXPAND_BOTH_WAYS )
        
        self._processing_panel.AddF( self._import_overall_info, FLAGS_EXPAND_PERPENDICULAR )
        self._processing_panel.AddF( self._import_current_info, FLAGS_EXPAND_PERPENDICULAR )
        self._processing_panel.AddF( self._import_gauge, FLAGS_EXPAND_PERPENDICULAR )
        self._processing_panel.AddF( c_p_hbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        queue_buttons_vbox = wx.BoxSizer( wx.VERTICAL )
        
        queue_buttons_vbox.AddF( self._up, FLAGS_MIXED )
        queue_buttons_vbox.AddF( self._remove, FLAGS_MIXED )
        queue_buttons_vbox.AddF( self._down, FLAGS_MIXED )
        
        queue_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        queue_hbox.AddF( self._outer_queue, FLAGS_EXPAND_BOTH_WAYS )
        queue_hbox.AddF( queue_buttons_vbox, FLAGS_MIXED )
        
        self._outer_queue_panel.AddF( self._outer_queue_info, FLAGS_EXPAND_PERPENDICULAR )
        self._outer_queue_panel.AddF( queue_hbox, FLAGS_EXPAND_SIZER_BOTH_WAYS )
        self._outer_queue_panel.AddF( self._new_queue_input, FLAGS_EXPAND_PERPENDICULAR )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        self._MakeSort( vbox )
        
        vbox.AddF( self._processing_panel, FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._outer_queue_panel, FLAGS_EXPAND_BOTH_WAYS )
        vbox.AddF( self._advanced_import_options, FLAGS_EXPAND_PERPENDICULAR )
        
        self._MakeCurrentSelectionTagsBox( vbox )
        
        self.SetSizer( vbox )
        
    
    def _THREADGetImportArgs( self, queue_object ):
        
        try:
            
            url = queue_object
            
            ( status, hash ) = wx.GetApp().Read( 'url_status', url )
            
            if status == 'deleted' and 'exclude_deleted_files' not in self._advanced_import_options.GetInfo(): status = 'new'
            
            if status == 'deleted': HC.pubsub.pub( 'import_done', self._page_key, 'deleted' )
            elif status == 'redundant':
                
                ( media_result, ) = wx.GetApp().Read( 'media_results', CC.FileSearchContext(), ( hash, ) )
                
                HC.pubsub.pub( 'add_media_result', self._page_key, media_result )
                HC.pubsub.pub( 'import_done', self._page_key, 'redundant' )
                
            else:
                
                HC.pubsub.pub( 'set_import_info', self._page_key, 'downloading ' + str( self._import_queue_position + 1 ) + '/' + str( len( self._import_queue ) ) )
                
                parse_result = urlparse.urlparse( url )
                
                ( scheme, host, port ) = ( parse_result.scheme, parse_result.hostname, parse_result.port )
                
                if ( scheme, host, port ) not in self._connections: self._connections[ ( scheme, host, port ) ] = CC.AdvancedHTTPConnection( scheme = scheme, host = host, port = port )
                
                connection = self._connections[ ( scheme, host, port ) ]
                
                file = connection.geturl( url )
                
                advanced_import_options = self._advanced_import_options.GetInfo()
                
                service_identifiers_to_tags = {}
                
                wx.CallAfter( self.CALLBACKImportArgs, file, advanced_import_options, service_identifiers_to_tags, url = url )
                
            
        except Exception as e:
            print( traceback.format_exc() )
            wx.CallAfter( self.CALLBACKImportArgs, '', {}, {}, exception = e )
        
    
    def _THREADDownloadImportItems( self, url ):
        
        try:
            
            HC.pubsub.pub( 'set_outer_queue_info', self._page_key, 'parsing url' )
            
            try:
                
                parse_result = urlparse.urlparse( url )
                
                ( scheme, host, port ) = ( parse_result.scheme, parse_result.hostname, parse_result.port )
                
            except: raise Exception( 'Could not parse that URL' )
            
            HC.pubsub.pub( 'set_outer_queue_info', self._page_key, 'Connecting to address' )
            
            try: connection = CC.AdvancedHTTPConnection( scheme = scheme, host = host, port = port )
            except: raise Exception( 'Could not connect to server' )
            
            try: html = connection.geturl( url )
            except: raise Exception( 'Could not download that url' )
            
            HC.pubsub.pub( 'set_outer_queue_info', self._page_key, 'parsing html' )
            
            try: urls = ClientParsers.ParsePage( html, url )
            except: raise Exception( 'Could not parse that URL\'s html' )
            
            wx.CallAfter( self.CALLBACKAddToImportQueue, urls )
            
        except Exception as e: HC.pubsub.pub( 'set_outer_queue_info', self._page_key, unicode( e ) )
        
        HC.pubsub.pub( 'done_adding_to_import_queue', self._page_key )
        
    
class ManagementPanelImportThreadWatcher( ManagementPanelImport ):
    
    def __init__( self, parent, page, page_key ):
        
        ManagementPanelImport.__init__( self, parent, page, page_key )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        self._connections = {}
        
        self._MakeSort( vbox )
        
        self._processing_panel.AddF( self._import_overall_info, FLAGS_EXPAND_PERPENDICULAR )
        self._processing_panel.AddF( self._import_current_info, FLAGS_EXPAND_PERPENDICULAR )
        self._processing_panel.AddF( self._import_gauge, FLAGS_EXPAND_PERPENDICULAR )
        self._processing_panel.AddF( self._import_pause_button, FLAGS_EXPAND_PERPENDICULAR )
        
        self._thread_panel = ClientGUICommon.StaticBox( self, 'thread checker' )
        
        self._thread_info = wx.StaticText( self._thread_panel, label = '' )
        
        self._thread_time = wx.SpinCtrl( self._thread_panel, min = 30, max = 1800 )
        self._thread_time.SetValue( 180 )
        
        self._thread_input = wx.TextCtrl( self._thread_panel, style = wx.TE_PROCESS_ENTER )
        self._thread_input.Bind( wx.EVT_KEY_DOWN, self.EventKeyDown )
        
        self._thread_pause_button = wx.Button( self._thread_panel, label = 'pause' )
        self._thread_pause_button.Bind( wx.EVT_BUTTON, self.EventPauseChecker )
        self._thread_pause_button.SetForegroundColour( ( 128, 0, 0 ) )
        self._thread_pause_button.Disable()
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.AddF( wx.StaticText( self._thread_panel, label = 'check every ' ), FLAGS_MIXED )
        hbox.AddF( self._thread_time, FLAGS_MIXED )
        hbox.AddF( wx.StaticText( self._thread_panel, label = ' seconds' ), FLAGS_MIXED )
        
        self._thread_panel.AddF( self._thread_info, FLAGS_EXPAND_PERPENDICULAR )
        self._thread_panel.AddF( self._thread_input, FLAGS_EXPAND_PERPENDICULAR )
        self._thread_panel.AddF( hbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._thread_panel.AddF( self._thread_pause_button, FLAGS_EXPAND_PERPENDICULAR )
        
        self._advanced_import_options = ClientGUICommon.AdvancedImportOptions( self )
        
        vbox.AddF( self._processing_panel, FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._thread_panel, FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.AddF( self._advanced_import_options, FLAGS_EXPAND_PERPENDICULAR )
        
        self._MakeCurrentSelectionTagsBox( vbox )
        
        self.SetSizer( vbox )
        
        self._last_thread_check = None
        self._4chan_board = None
        self._thread_id = None
        self._currently_checking_thread = False
        self._currently_paused = False
        self._image_infos_already_added = set()
        
        self._outer_queue_timer = wx.Timer( self, id = ID_TIMER_PROCESS_OUTER_QUEUE )
        
        self.Bind( wx.EVT_TIMER, self.EventProcessOuterQueue, id = ID_TIMER_PROCESS_OUTER_QUEUE )
        
        self._outer_queue_timer.Start( 1000, wx.TIMER_ONE_SHOT )
        
        HC.pubsub.sub( self, 'SetThreadInfo', 'set_thread_info' )
        
    
    def _THREADFetchThread( self ):
        
        HC.pubsub.pub( 'set_thread_info', self._page_key, 'checking thread' )
        
        url = 'http://api.4chan.org/' + self._4chan_board + '/res/' + self._thread_id + '.json'
        
        try:
            
            connection = CC.AdvancedHTTPConnection( url = url )
            
            raw_json = connection.geturl( url )
            
            json_dict = json.loads( raw_json )
            
            posts_list = json_dict[ 'posts' ]
            
            image_infos = [ ( post[ 'md5' ].decode( 'base64' ), str( post[ 'tim' ] ), post[ 'ext' ] ) for post in posts_list if 'md5' in post ]
            
            image_infos_i_can_add = [ image_info for image_info in image_infos if image_info not in self._image_infos_already_added ]
            
            self._image_infos_already_added.update( image_infos_i_can_add )
            
            if len( image_infos_i_can_add ) > 0: wx.CallAfter( self.CALLBACKAddToImportQueue, image_infos_i_can_add )
            
        except HC.NotFoundException:
            
            HC.pubsub.pub( 'set_thread_info', self._page_key, 'Thread 404' )
            
            wx.CallAfter( self._thread_pause_button.Disable )
            
            return
            
        except Exception as e:
            
            HC.pubsub.pub( 'set_thread_info', self._page_key, unicode( e ) )
            
            wx.CallAfter( self._thread_pause_button.Disable )
            
            return
            
        
        self._last_thread_check = int( time.time() )
        
        self._currently_checking_thread = False
        
    
    def _THREADGetImportArgs( self, queue_object ):
        
        try:
            
            ( md5, image_name, ext ) = queue_object
            
            ( status, hash ) = wx.GetApp().Read( 'md5_status', md5 )
            
            if status == 'deleted' and 'exclude_deleted_files' not in self._advanced_import_options.GetInfo(): status = 'new'
            
            if status == 'deleted': HC.pubsub.pub( 'import_done', self._page_key, 'deleted' )
            elif status == 'redundant':
                
                ( media_result, ) = wx.GetApp().Read( 'media_results', CC.FileSearchContext(), ( hash, ) )
                
                HC.pubsub.pub( 'add_media_result', self._page_key, media_result )
                HC.pubsub.pub( 'import_done', self._page_key, 'redundant' )
                
            else:
                
                url = 'http://images.4chan.org/' + self._4chan_board + '/src/' + image_name + ext
                
                ( status, hash ) = wx.GetApp().Read( 'url_status', url )
                
                if status == 'deleted' and 'exclude_deleted_files' not in self._advanced_import_options.GetInfo(): status = 'new'
                
                if status == 'deleted': HC.pubsub.pub( 'import_done', self._page_key, 'deleted' )
                elif status == 'redundant':
                    
                    ( media_result, ) = wx.GetApp().Read( 'media_results', CC.FileSearchContext(), ( hash, ) )
                    
                    HC.pubsub.pub( 'add_media_result', self._page_key, media_result )
                    HC.pubsub.pub( 'import_done', self._page_key, 'redundant' )
                    
                else:
                    
                    HC.pubsub.pub( 'set_import_info', self._page_key, 'downloading ' + str( self._import_queue_position + 1 ) + '/' + str( len( self._import_queue ) ) )
                    
                    parse_result = urlparse.urlparse( url )
                    
                    ( scheme, host, port ) = ( parse_result.scheme, parse_result.hostname, parse_result.port )
                    
                    if ( scheme, host, port ) not in self._connections: self._connections[ ( scheme, host, port ) ] = CC.AdvancedHTTPConnection( scheme = scheme, host = host, port = port )
                    
                    connection = self._connections[ ( scheme, host, port ) ]
                    
                    file = connection.geturl( url )
                    
                    advanced_import_options = self._advanced_import_options.GetInfo()
                    
                    service_identifiers_to_tags = {}
                    
                    wx.CallAfter( self.CALLBACKImportArgs, file, advanced_import_options, service_identifiers_to_tags, url = url )
                    
                
            
        except Exception as e:
            print( traceback.format_exc() )
            wx.CallAfter( self.CALLBACKImportArgs, '', {}, {}, exception = e )
        
    
    def _GetPreprocessStatus( self ):
        
        status = 'checking url/hash status ' + str( self._import_queue_position + 1 ) + '/' + str( len( self._import_queue ) )
        
        return status
        
    
    def EventKeyDown( self, event ):
        
        if event.KeyCode in ( wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER ):
            
            url = self._thread_input.GetValue()
            
            if url == '': return
            
            try:
                
                try:
                    
                    parse_result = urlparse.urlparse( url )
                    
                    host = parse_result.hostname
                    
                    request = parse_result.path
                    
                    if host is None or request is None: raise Exception()
                    
                except: raise Exception ( 'Could not understand that url!' )
                
                if host is None or '4chan.org' not in host: raise Exception( 'This only works for 4chan right now!' )
                
                try: ( nothing, board, res, thread_id ) = request.split( '/' )
                except: raise Exception( 'Could not understand the board or thread id!' )
                
            except Exception as e:
                
                self._thread_info.SetLabel( unicode( e ) )
                
                return
                
            
            self._4chan_board = board
            self._thread_id = thread_id
            
            self._last_thread_check = 0
            
            self._thread_input.Disable()
            self._thread_pause_button.Enable()
            
        else: event.Skip()
        
    
    def EventProcessOuterQueue( self, event ):
        
        if self._4chan_board is None: self._thread_info.SetLabel( 'enter a 4chan thread url' )
        elif self._currently_paused: self._thread_info.SetLabel( 'paused' )
        elif not self._currently_checking_thread:
            
            thread_time = self._thread_time.GetValue()
            
            if thread_time < 30: thread_time = 30
            
            next_thread_check = self._last_thread_check + thread_time
            
            if next_thread_check < int( time.time() ):
                
                self._currently_checking_thread = True
                
                threading.Thread( target = self._THREADFetchThread, name = 'Fetch Thread' ).start()
                
            else: self._thread_info.SetLabel( 'rechecking thread ' + HC.ConvertTimestampToPrettyPending( next_thread_check ) )
            
        
        self._outer_queue_timer.Start( 1000, wx.TIMER_ONE_SHOT )
        
    
    def EventPauseChecker( self, event ):
        
        if self._currently_paused:
            
            self._currently_paused = False
            
            self._thread_pause_button.SetLabel( 'pause' )
            self._thread_pause_button.SetForegroundColour( ( 0, 0, 0 ) )
            
        else:
            
            self._currently_paused = True
            
            self._thread_pause_button.SetLabel( 'resume' )
            self._thread_pause_button.SetForegroundColour( ( 0, 128, 0 ) )
            
        
    
    def SetSearchFocus( self, page_key ):
        
        if page_key == self._page_key: self._thread_input.SetFocus()
        
    
    def SetThreadInfo( self, page_key, info ):
        
        if self._page_key == page_key: self._thread_info.SetLabel( info )
        
    
class ManagementPanelPetitions( ManagementPanel ):
    
    def __init__( self, parent, page, page_key, file_service_identifier ):
        
        ManagementPanel.__init__( self, parent, page, page_key, file_service_identifier )
        
        self._service = wx.GetApp().Read( 'service', file_service_identifier )
        self._can_ban = self._service.GetAccount().HasPermission( HC.MANAGE_USERS )
        
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
        
        num_petitions_hbox.AddF( self._num_petitions_text, FLAGS_EXPAND_BOTH_WAYS )
        num_petitions_hbox.AddF( refresh_num_petitions, FLAGS_MIXED )
        
        self._petitions_info_panel.AddF( num_petitions_hbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._petitions_info_panel.AddF( self._get_petition, FLAGS_EXPAND_PERPENDICULAR )
        
        p_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        p_hbox.AddF( self._approve, FLAGS_EXPAND_BOTH_WAYS )
        p_hbox.AddF( self._deny, FLAGS_EXPAND_BOTH_WAYS )
        
        self._petition_panel.AddF( self._petition_info_text_ctrl, FLAGS_EXPAND_BOTH_WAYS )
        self._petition_panel.AddF( p_hbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._petition_panel.AddF( self._modify_petitioner, FLAGS_EXPAND_PERPENDICULAR )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        self._MakeSort( vbox )
        self._MakeCollect( vbox )
        
        vbox.AddF( self._petitions_info_panel, FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._petition_panel, FLAGS_EXPAND_BOTH_WAYS )
        
        self._MakeCurrentSelectionTagsBox( vbox )
        
        self.SetSizer( vbox )
        
        wx.CallAfter( self.EventRefreshNumPetitions, None )
        
        HC.pubsub.sub( self, 'RefreshQuery', 'refresh_query' )
        
    
    def _DrawCurrentPetition( self ):
        
        if self._current_petition is None:
            
            self._petition_info_text_ctrl.SetValue( '' )
            self._approve.Disable()
            self._deny.Disable()
            
            if self._can_ban: self._modify_petitioner.Disable()
            
            panel = ClientGUIMedia.MediaPanelNoQuery( self._page, self._page_key, self._file_service_identifier )
            
        else:
            
            self._petition_info_text_ctrl.SetValue( self._current_petition.GetPetitionString() )
            self._approve.Enable()
            self._deny.Enable()
            
            if self._can_ban: self._modify_petitioner.Enable()
            
            search_context = CC.FileSearchContext( self._file_service_identifier )
            
            with wx.BusyCursor(): file_query_result = wx.GetApp().Read( 'media_results', search_context, self._current_petition.GetPetitionHashes() )
            
            panel = ClientGUIMedia.MediaPanelThumbnails( self._page, self._page_key, self._file_service_identifier, [], file_query_result )
            
            panel.Collect( self._page_key, self._collect_by.GetChoice() )
            
            panel.Sort( self._page_key, self._sort_by.GetChoice() )
            
        
        HC.pubsub.pub( 'swap_media_panel', self._page_key, panel )
        
    
    def _DrawNumPetitions( self ):
        
        self._num_petitions_text.SetLabel( HC.ConvertIntToPrettyString( self._num_petitions ) + ' petitions' )
        
        if self._num_petitions > 0: self._get_petition.Enable()
        else: self._get_petition.Disable()
        
    
    def EventApprove( self, event ):
        
        connection = self._service.GetConnection()
        
        petition_object = self._current_petition.GetClientPetition()
        
        connection.Post( 'petitions', petitions = petition_object )
        
        if isinstance( self._current_petition, HC.ServerFilePetition ):
            
            hashes = self._current_petition.GetPetitionHashes()
            
            content_updates = [ HC.ContentUpdate( CC.CONTENT_UPDATE_DELETE, self._file_service_identifier, hashes ) ]
            
        elif isinstance( self._current_petition, HC.ServerMappingPetition ):
            
            ( reason, tag, hashes ) = self._current_petition.GetPetitionInfo()
            
            content_updates = [ HC.ContentUpdate( CC.CONTENT_UPDATE_DELETE, self._file_service_identifier, hashes, tag ) ]
            
        
        wx.GetApp().Write( 'content_updates', content_updates )
        
        self._current_petition = None
        
        self._DrawCurrentPetition()
        
        self.EventRefreshNumPetitions( event )
        
    
    def EventDeny( self, event ):
        
        connection = self._service.GetConnection()
        
        petition_object = self._current_petition.GetClientPetitionDenial()
        
        # needs work
        connection.Post( 'petition_denial', petition_denial = petition_object )
        
        self._current_petition = None
        
        self._DrawCurrentPetition()
        
        self.EventRefreshNumPetitions( event )
        
    
    def EventGetPetition( self, event ):
        
        try:
            
            connection = self._service.GetConnection()
            
            self._current_petition = connection.Get( 'petition' )
            
            self._DrawCurrentPetition()
            
        except:
            
            wx.MessageBox( traceback.format_exc() )
            
            self._current_petition = None
            
            self._DrawCurrentPetition()
            
        
    
    def EventModifyPetitioner( self, event ):
        
        with ClientGUIDialogs.DialogModifyAccounts( self, self._file_service_identifier, ( self._current_petition.GetPetitionerIdentifier(), ) ) as dlg: dlg.ShowModal()
        
    
    def EventRefreshNumPetitions( self, event ):
        
        self._num_petitions_text.SetLabel( u'Fetching\u2026' )
        
        try:
            
            connection = self._service.GetConnection()
            
            self._num_petitions = connection.Get( 'num_petitions' )
            
            self._DrawNumPetitions()
            
            if self._num_petitions > 0: self.EventGetPetition( event )
            
        except Exception as e: self._num_petitions_text.SetLabel( unicode( e ) )
        
    
    def RefreshQuery( self, page_key ):
        
        if page_key == self._page_key: self._DrawCurrentPetition()
        
    
class ManagementPanelQuery( ManagementPanel ):
    
    def __init__( self, parent, page, page_key, file_service_identifier, initial_predicates = [] ):
        
        ManagementPanel.__init__( self, parent, page, page_key, file_service_identifier )
        
        self._query_key = os.urandom( 32 )
        self._synchronised = True
        self._include_current_tags = True
        self._include_pending_tags = True
        
        self._search_panel = ClientGUICommon.StaticBox( self, 'search' )
        
        self._current_predicates_box = ClientGUICommon.TagsBoxPredicates( self._search_panel, self._page_key, initial_predicates )
        
        self._searchbox = ClientGUICommon.AutoCompleteDropdownTagsRead( self._search_panel, self._page_key, self._file_service_identifier, CC.NULL_SERVICE_IDENTIFIER, self._page.GetMedia )
        
        self._search_panel.AddF( self._current_predicates_box, FLAGS_EXPAND_PERPENDICULAR )
        self._search_panel.AddF( self._searchbox, FLAGS_EXPAND_PERPENDICULAR )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        self._MakeSort( vbox )
        self._MakeCollect( vbox )
        
        vbox.AddF( self._search_panel, FLAGS_EXPAND_PERPENDICULAR )
        
        self._MakeCurrentSelectionTagsBox( vbox )
        
        self.SetSizer( vbox )
        
        if len( initial_predicates ) > 0: wx.CallAfter( self._DoQuery )
        
        HC.pubsub.sub( self, 'AddPredicate', 'add_predicate' )
        HC.pubsub.sub( self, 'ChangeFileRepository', 'change_file_repository' )
        HC.pubsub.sub( self, 'ChangeTagRepository', 'change_tag_repository' )
        HC.pubsub.sub( self, 'IncludeCurrent', 'notify_include_current' )
        HC.pubsub.sub( self, 'IncludePending', 'notify_include_pending' )
        HC.pubsub.sub( self, 'SearchImmediately', 'notify_search_immediately' )
        HC.pubsub.sub( self, 'ShowQuery', 'file_query_done' )
        HC.pubsub.sub( self, 'RefreshQuery', 'refresh_query' )
        HC.pubsub.sub( self, 'RemovePredicate', 'remove_predicate' )
        
    
    def _DoQuery( self ):
        
        if self._synchronised:
            
            try:
                
                current_predicates = self._current_predicates_box.GetPredicates()
                
                if len( current_predicates ) > 0:
                    
                    self._query_key = os.urandom( 32 )
                    
                    include_current = self._include_current_tags
                    include_pending = self._include_pending_tags
                    
                    search_context = CC.FileSearchContext( self._file_service_identifier, self._tag_service_identifier, include_current, include_pending, current_predicates )
                    
                    wx.GetApp().Read( 'do_file_query', self._query_key, search_context )
                    
                    panel = ClientGUIMedia.MediaPanelLoading( self._page, self._page_key, self._file_service_identifier )
                    
                else: panel = ClientGUIMedia.MediaPanelNoQuery( self._page, self._page_key, self._file_service_identifier )
                
                HC.pubsub.pub( 'swap_media_panel', self._page_key, panel )
                
            except: wx.MessageBox( traceback.format_exc() )
            
        
    
    def AddPredicate( self, page_key, predicate ): 
        
        if page_key == self._page_key:
            
            if predicate is not None:
                
                if predicate in ( 'system:size', 'system:age', 'system:hash', 'system:limit', 'system:numtags', 'system:width', 'system:height', 'system:ratio', 'system:duration', u'system:mime', u'system:rating', u'system:similar_to' ):
                    
                    with ClientGUIDialogs.DialogInputFileSystemPredicate( self, predicate ) as dlg:
                        
                        if dlg.ShowModal() == wx.ID_OK: predicate = dlg.GetString()
                        else: return
                        
                    
                elif predicate == 'system:untagged': predicate = 'system:numtags=0'
                
                if self._current_predicates_box.HasPredicate( predicate ): self._current_predicates_box.RemovePredicate( predicate )
                else:
                    
                    if predicate in ( 'system:inbox', 'system:archive', 'system:local', 'system:not local' ):
                        
                        if predicate == 'system:inbox': removee = 'system:archive'
                        elif predicate == 'system:archive': removee = 'system:inbox'
                        elif predicate == 'system:local': removee = 'system:not local'
                        elif predicate == 'system:not local': removee = 'system:local'
                        
                    else:
                        
                        if predicate.startswith( '-' ): removee = predicate[1:]
                        else: removee = '-' + predicate
                        
                    
                    if self._current_predicates_box.HasPredicate( removee ): self._current_predicates_box.RemovePredicate( removee )
                    
                    self._current_predicates_box.AddPredicate( predicate )
                    
                
            
            self._DoQuery()
            
        
    
    def ChangeFileRepository( self, page_key, service_identifier ):
        
        if page_key == self._page_key:
            
            self._file_service_identifier = service_identifier
            
            self._DoQuery()
            
        
    
    def ChangeTagRepository( self, page_key, service_identifier ):
        
        if page_key == self._page_key:
            
            self._tag_service_identifier = service_identifier
            
            current_predicates = self._current_predicates_box.GetPredicates()
            
            # if we are basing the search on the tag service or there are any regular tags...
            if self._file_service_identifier == CC.NULL_SERVICE_IDENTIFIER or False in ( pred.startswith( 'system:' ) for pred in current_predicates ): self._DoQuery()
            
        
    
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
        
        if page_key == self._page_key: self._searchbox.SetFocus()
        
    
    def ShowQuery( self, query_key, file_query_result ):
        
        try:
            
            if query_key == self._query_key:
                
                current_predicates = self._current_predicates_box.GetPredicates()
                
                panel = ClientGUIMedia.MediaPanelThumbnails( self._page, self._page_key, self._file_service_identifier, current_predicates, file_query_result )
                
                panel.Collect( self._page_key, self._collect_by.GetChoice() )
                
                panel.Sort( self._page_key, self._sort_by.GetChoice() )
                
                HC.pubsub.pub( 'swap_media_panel', self._page_key, panel )
                
            
        except: wx.MessageBox( traceback.format_exc() )
        
    
class ManagementPanelMessages( wx.ScrolledWindow ):
    
    def __init__( self, parent, page_key, identity ):
        
        wx.ScrolledWindow.__init__( self, parent, style = wx.BORDER_NONE | wx.HSCROLL | wx.VSCROLL )
        
        self.SetScrollRate( 0, 20 )
        
        self._page_key = page_key
        self._identity = identity
        
        self._query_key = os.urandom( 32 )
        
        # sort out push-refresh later
        #self._refresh_inbox = wx.Button( self, label = 'refresh inbox' )
        #self._refresh_inbox.Bind( wx.EVT_BUTTON, self.EventRefreshInbox )
        #self._refresh_inbox.SetForegroundColour( ( 0, 128, 0 ) )
        
        self._actions_panel = ClientGUICommon.StaticBox( self, 'actions' )
        
        self._compose = wx.Button( self._actions_panel, label = 'compose' )
        self._compose.Bind( wx.EVT_BUTTON, self.EventCompose )
        self._compose.SetForegroundColour( ( 0, 128, 0 ) )
        
        self._actions_panel.AddF( self._compose, FLAGS_EXPAND_PERPENDICULAR )
        #vbox.AddF( self._refresh_inbox, FLAGS_EXPAND_PERPENDICULAR )
        
        self._search_panel = ClientGUICommon.StaticBox( self, 'search' )
        
        self._current_predicates_box = ClientGUICommon.ListBoxMessagesPredicates( self._search_panel, self._page_key, [ 'system:inbox' ] )
        
        self._synchronised = ClientGUICommon.OnOffButton( self._search_panel, self._page_key, 'notify_search_immediately', on_label = 'searching immediately', off_label = 'waiting' )
        self._synchronised.SetToolTipString( 'select whether to renew the search as soon as a new predicate is entered' )
        
        self._searchbox = ClientGUICommon.AutoCompleteDropdownMessageTerms( self._search_panel, self._page_key, self._identity )
        
        self._search_panel.AddF( self._current_predicates_box, FLAGS_EXPAND_BOTH_WAYS )
        self._search_panel.AddF( self._synchronised, FLAGS_EXPAND_PERPENDICULAR )
        self._search_panel.AddF( self._searchbox, FLAGS_EXPAND_PERPENDICULAR )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._actions_panel, FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._search_panel, FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
        HC.pubsub.sub( self, 'AddPredicate', 'add_predicate' )
        HC.pubsub.sub( self, 'SearchImmediately', 'notify_search_immediately' )
        HC.pubsub.sub( self, 'ShowQuery', 'message_query_done' )
        HC.pubsub.sub( self, 'RefreshQuery', 'refresh_query' )
        HC.pubsub.sub( self, 'RemovePredicate', 'remove_predicate' )
        
        wx.CallAfter( self._DoQuery )
        
    
    def _DoQuery( self ):
        
        if self._synchronised.IsOn():
            
            try:
                
                current_predicates = self._current_predicates_box.GetPredicates()
                
                HC.pubsub.pub( 'set_conversations', self._page_key, [] )
                
                if len( current_predicates ) > 0:
                    
                    self._query_key = os.urandom( 32 )
                    
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
            
        
    
    def EventCompose( self, event ): HC.pubsub.pub( 'new_compose_frame', self._identity )
    
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
            
            if query_key == self._query_key: HC.pubsub.pub( 'set_conversations', self._page_key, conversations )
            
        except: wx.MessageBox( traceback.format_exc() )
        
    
    def TryToClose( self ):
        
        pass
        
        # if have a open draft, save it!
        
    