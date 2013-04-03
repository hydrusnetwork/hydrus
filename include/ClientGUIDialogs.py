import Crypto.PublicKey.RSA
import HydrusConstants as HC
import HydrusMessageHandling
import ClientConstants as CC
import ClientConstantsMessages
import ClientGUICommon
import collections
import os
import random
import re
import subprocess
import time
import traceback
import urllib
import wx
import yaml

# Option Enums

ID_NULL = wx.NewId()

ID_TIMER_UPDATE = wx.NewId()

# Hue is generally 200, Sat and Lum changes based on need

COLOUR_SELECTED = wx.Colour( 217, 242, 255 )
COLOUR_SELECTED_DARK = wx.Colour( 1, 17, 26 )
COLOUR_UNSELECTED = wx.Colour( 223, 227, 230 )

# Sizer Flags

FLAGS_NONE = wx.SizerFlags( 0 )

FLAGS_SMALL_INDENT = wx.SizerFlags( 0 ).Border( wx.ALL, 2 )
FLAGS_BIG_INDENT = wx.SizerFlags( 0 ).Border( wx.ALL, 8 )

FLAGS_EXPAND_PERPENDICULAR = wx.SizerFlags( 0 ).Border( wx.ALL, 2 ).Expand()
FLAGS_EXPAND_BOTH_WAYS = wx.SizerFlags( 2 ).Border( wx.ALL, 2 ).Expand()
FLAGS_EXPAND_DEPTH_ONLY = wx.SizerFlags( 2 ).Border( wx.ALL, 2 ).Align( wx.ALIGN_CENTER_VERTICAL )

FLAGS_EXPAND_SIZER_PERPENDICULAR = wx.SizerFlags( 0 ).Expand()
FLAGS_EXPAND_SIZER_BOTH_WAYS = wx.SizerFlags( 2 ).Expand()
FLAGS_EXPAND_SIZER_DEPTH_ONLY = wx.SizerFlags( 2 ).Align( wx.ALIGN_CENTER_VERTICAL )

FLAGS_BUTTON_SIZERS = wx.SizerFlags( 0 ).Align( wx.ALIGN_RIGHT )
FLAGS_LONE_BUTTON = wx.SizerFlags( 0 ).Border( wx.ALL, 2 ).Align( wx.ALIGN_RIGHT )

FLAGS_MIXED = wx.SizerFlags( 0 ).Border( wx.ALL, 2 ).Align( wx.ALIGN_CENTER_VERTICAL )

def SelectServiceIdentifier( permission = None, service_types = HC.ALL_SERVICES, service_identifiers = None, unallowed = None ):
    
    if service_identifiers is None:
        
        services = wx.GetApp().Read( 'services', service_types )
        
        if permission is not None: services = [ service for service in services if service.GetAccount().HasPermission( permission ) ]
        
        service_identifiers = [ service.GetServiceIdentifier() for service in services ]
        
    
    if unallowed is not None: service_identifiers.difference_update( unallowed )
    
    if len( service_identifiers ) == 0: return None
    elif len( service_identifiers ) == 1:
        
        ( service_identifier, ) = service_identifiers
        
        return service_identifier
        
    else:
        
        names_to_service_identifiers = { service_identifier.GetName() : service_identifier for service_identifier in service_identifiers }
        
        with DialogSelectFromListOfStrings( wx.GetApp().GetGUI(), 'select service', [ service_identifier.GetName() for service_identifier in service_identifiers ] ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK: return names_to_service_identifiers[ dlg.GetString() ]
            else: return None
            
        
    
def ShowMessage( parent, message ):
    
    with DialogMessage( parent, message ) as dlg: dlg.ShowModal()
    
class Dialog( wx.Dialog ):
    
    def __init__( self, parent, title, style = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER, position = 'topleft' ):
        
        self._options = wx.GetApp().Read( 'options' )
        
        if position == 'topleft':
            
            ( pos_x, pos_y ) = wx.GetApp().GetGUI().GetPositionTuple()
            
            pos = ( pos_x + 50, pos_y + 100 )
            
        else: pos = ( -1, -1 )
        
        wx.Dialog.__init__( self, parent, title = title, style = style, pos = pos )
        
        self.SetDoubleBuffered( True )
        
        self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
        
        self.SetIcon( wx.Icon( HC.STATIC_DIR + os.path.sep + 'hydrus.ico', wx.BITMAP_TYPE_ICO ) )
        
        if position == 'center': wx.CallAfter( self.Center )
        
    
class DialogChooseNewServiceMethod( Dialog ):
    
    def __init__( self, parent ):
        
        def InitialiseControls():
            
            register_message = 'I want to set up a new account. I have a registration key (a key starting with \'r\').'
            
            self._register = wx.Button( self, id = wx.ID_OK, label = register_message )
            self._register.Bind( wx.EVT_BUTTON, self.EventRegister )
            
            setup_message = 'The account is already set up; I just want to add it to this client. I have a normal access key.'
            
            self._setup = wx.Button( self, id = wx.ID_OK, label = setup_message )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'cancel', size = ( 0, 0 ) )
            
        
        def InitialisePanel():
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( self._register, FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( wx.StaticText( self, label = '-or-', style = wx.ALIGN_CENTER ), FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._setup, FLAGS_EXPAND_PERPENDICULAR )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
        
        Dialog.__init__( self, parent, 'how to set up the account?', position = 'center' )
        
        InitialiseControls()
        
        InitialisePanel()
        
        self._register = False
        
    
    def EventRegister( self, event ):
        
        self._register = True
        
        self.EndModal( wx.ID_OK )
        
    
    def GetRegister( self ): return self._register
    
class DialogFinishFiltering( Dialog ):
    
    def __init__( self, parent, num_kept, num_deleted, keep = 'Keep', delete = 'delete' ):
        
        def InitialiseControls():
            
            self._commit = wx.Button( self, label = 'commit' )
            self._commit.Bind( wx.EVT_BUTTON, self.EventCommit )
            self._commit.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._forget = wx.Button( self, label = 'forget' )
            self._forget.Bind( wx.EVT_BUTTON, self.EventForget )
            self._forget.SetForegroundColour( ( 128, 0, 0 ) )
            
            self._back = wx.Button( self, id = wx.ID_CANCEL, label = 'back to filtering' )
            self._back.Bind( wx.EVT_BUTTON, self.EventBack )
            
        
        def InitialisePanel():
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( self._commit, FLAGS_EXPAND_BOTH_WAYS )
            hbox.AddF( self._forget, FLAGS_EXPAND_BOTH_WAYS )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            label = keep + ' ' + HC.ConvertIntToPrettyString( num_kept ) + ' and ' + delete + ' ' + HC.ConvertIntToPrettyString( num_deleted ) + ' files?'
            
            vbox.AddF( wx.StaticText( self, label = label, style = wx.ALIGN_CENTER ), FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( hbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
            vbox.AddF( wx.StaticText( self, label = '-or-', style = wx.ALIGN_CENTER ), FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._back, FLAGS_EXPAND_PERPENDICULAR )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
        
        Dialog.__init__( self, parent, 'are you sure?', position = 'center' )
        
        InitialiseControls()
        
        InitialisePanel()
        
    
    def EventBack( self, event ): self.EndModal( wx.ID_CANCEL )
    
    def EventCommit( self, event ): self.EndModal( wx.ID_YES )
    
    def EventForget( self, event ): self.EndModal( wx.ID_NO )
    
class DialogFinishRatingFiltering( Dialog ):
    
    def __init__( self, parent, num_certain_ratings, num_uncertain_ratings ):
        
        def InitialiseControls():
            
            self._commit = wx.Button( self, label = 'commit' )
            self._commit.Bind( wx.EVT_BUTTON, self.EventCommit )
            self._commit.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._forget = wx.Button( self, label = 'forget' )
            self._forget.Bind( wx.EVT_BUTTON, self.EventForget )
            self._forget.SetForegroundColour( ( 128, 0, 0 ) )
            
            self._back = wx.Button( self, id = wx.ID_CANCEL, label = 'back to filtering' )
            self._back.Bind( wx.EVT_BUTTON, self.EventBack )
            
        
        def InitialisePanel():
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( self._commit, FLAGS_EXPAND_BOTH_WAYS )
            hbox.AddF( self._forget, FLAGS_EXPAND_BOTH_WAYS )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            info_strings = []
            
            if num_certain_ratings > 0: info_strings.append( HC.ConvertIntToPrettyString( num_certain_ratings ) + ' ratings' )
            if num_uncertain_ratings > 0: info_strings.append( HC.ConvertIntToPrettyString( num_uncertain_ratings ) + ' uncertain changes' )
            
            label = 'Apply ' + ' and '.join( info_strings ) + '?'
            
            vbox.AddF( wx.StaticText( self, label = label, style = wx.ALIGN_CENTER ), FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( hbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
            vbox.AddF( wx.StaticText( self, label = '-or-', style = wx.ALIGN_CENTER ), FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._back, FLAGS_EXPAND_PERPENDICULAR )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
        
        Dialog.__init__( self, parent, 'are you sure?', position = 'center' )
        
        InitialiseControls()
        
        InitialisePanel()
        
    
    def EventBack( self, event ): self.EndModal( wx.ID_CANCEL )
    
    def EventCommit( self, event ): self.EndModal( wx.ID_YES )
    
    def EventForget( self, event ): self.EndModal( wx.ID_NO )
    
class DialogFirstStart( Dialog ):
    
    def __init__( self, parent ):
        
        def InitialiseControls():
            
            self._ok = wx.Button( self, id = wx.ID_OK, label = 'ok!' )
            self._ok.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'cancel', size = ( 0, 0 ) )
            
        
        def InitialisePanel():
            
            message1 = 'Hi, this looks like the first time you have started the hydrus client. Don\'t forget to check out the'
            link = wx.HyperlinkCtrl( self, id = -1, label = 'help', url = 'file://' + HC.BASE_DIR + '/help/index.html' )
            message2 = 'if you haven\'t already.'
            message3 = 'When you close this dialog, the client will start its local http server. You will probably get a firewall warning.'
            message4 = 'You can block it if you like, or you can allow it. It doesn\'t phone home, or expose your files to your network; it just provides another way to locally export your files.'
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( wx.StaticText( self, label = message1 ), FLAGS_MIXED )
            hbox.AddF( link, FLAGS_MIXED )
            hbox.AddF( wx.StaticText( self, label = message2 ), FLAGS_MIXED )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( hbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            vbox.AddF( wx.StaticText( self, label = message3 ), FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( wx.StaticText( self, label = message4 ), FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._ok, FLAGS_LONE_BUTTON )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
        
        Dialog.__init__( self, parent, 'First start', position = 'center' )
        
        InitialiseControls()
        
        InitialisePanel()
        
    
class DialogInputCustomFilterAction( Dialog ):
    
    def __init__( self, parent, modifier = wx.ACCEL_NORMAL, key = wx.WXK_F7, service_identifier = None, action = 'archive' ):
        
        self._service_identifier = service_identifier
        self._action = action
        
        self._current_ratings_like_service = None
        self._current_ratings_numerical_service = None
        
        def InitialiseControls():
            
            service_identifiers = wx.GetApp().Read( 'service_identifiers', ( HC.LOCAL_TAG, HC.TAG_REPOSITORY, HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ) )
            
            self._shortcut_panel = ClientGUICommon.StaticBox( self, 'shortcut' )
            
            self._shortcut = ClientGUICommon.Shortcut( self._shortcut_panel, modifier, key )
            
            self._none_panel = ClientGUICommon.StaticBox( self, 'non-service actions' )
            
            self._none_actions = wx.Choice( self._none_panel, choices = [ 'manage_tags', 'manage_ratings', 'archive', 'inbox', 'delete', 'fullscreen_switch', 'frame_back', 'frame_next', 'previous', 'next', 'first', 'last' ] )
            
            self._ok_none = wx.Button( self._none_panel, label = 'ok' )
            self._ok_none.Bind( wx.EVT_BUTTON, self.EventOKNone )
            self._ok_none.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._tag_panel = ClientGUICommon.StaticBox( self, 'tag service actions' )
            
            self._tag_service_identifiers = wx.Choice( self._tag_panel )
            self._tag_value = wx.TextCtrl( self._tag_panel, style = wx.TE_READONLY )
            self._tag_input = ClientGUICommon.AutoCompleteDropdownTagsWrite( self._tag_panel, self.SetTag, CC.LOCAL_FILE_SERVICE_IDENTIFIER, CC.NULL_SERVICE_IDENTIFIER )
            
            self._ok_tag = wx.Button( self._tag_panel, label = 'ok' )
            self._ok_tag.Bind( wx.EVT_BUTTON, self.EventOKTag )
            self._ok_tag.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._ratings_like_panel = ClientGUICommon.StaticBox( self, 'ratings like service actions' )
            
            self._ratings_like_service_identifiers = wx.Choice( self._ratings_like_panel )
            self._ratings_like_service_identifiers.Bind( wx.EVT_CHOICE, self.EventRecalcActions )
            self._ratings_like_like = wx.RadioButton( self._ratings_like_panel, style = wx.RB_GROUP, label = 'like' )
            self._ratings_like_dislike = wx.RadioButton( self._ratings_like_panel, label = 'dislike' )
            self._ratings_like_remove = wx.RadioButton( self._ratings_like_panel, label = 'remove rating' )
            
            self._ok_ratings_like = wx.Button( self._ratings_like_panel, label = 'ok' )
            self._ok_ratings_like.Bind( wx.EVT_BUTTON, self.EventOKRatingsLike )
            self._ok_ratings_like.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._ratings_numerical_panel = ClientGUICommon.StaticBox( self, 'ratings numerical service actions' )
            
            self._ratings_numerical_service_identifiers = wx.Choice( self._ratings_numerical_panel )
            self._ratings_numerical_service_identifiers.Bind( wx.EVT_CHOICE, self.EventRecalcActions )
            self._ratings_numerical_slider = wx.Slider( self._ratings_numerical_panel, style = wx.SL_AUTOTICKS | wx.SL_LABELS )
            self._ratings_numerical_remove = wx.CheckBox( self._ratings_numerical_panel, label = 'remove rating' )
            
            self._ok_ratings_numerical = wx.Button( self._ratings_numerical_panel, label = 'ok' )
            self._ok_ratings_numerical.Bind( wx.EVT_BUTTON, self.EventOKRatingsNumerical )
            self._ok_ratings_numerical.SetForegroundColour( ( 0, 128, 0 ) )
            
            for service_identifier in service_identifiers:
                
                service_type = service_identifier.GetType()
                
                if service_type in ( HC.LOCAL_TAG, HC.TAG_REPOSITORY ): choice = self._tag_service_identifiers
                elif service_type == HC.LOCAL_RATING_LIKE: choice = self._ratings_like_service_identifiers
                elif service_type == HC.LOCAL_RATING_NUMERICAL: choice = self._ratings_numerical_service_identifiers
                
                choice.Append( service_identifier.GetName(), service_identifier )
                
            
            self._SetActions()
            
            if self._service_identifier is None:
                
                self._none_actions.SetStringSelection( self._action )
                
            else:
                
                service_name = self._service_identifier.GetName()
                service_type = self._service_identifier.GetType()
                
                if service_type in ( HC.LOCAL_TAG, HC.TAG_REPOSITORY ):
                    
                    self._tag_service_identifiers.SetStringSelection( service_name )
                    
                    self._tag_value.SetValue( self._action )
                    
                elif service_type == HC.LOCAL_RATING_LIKE:
                    
                    self._ratings_like_service_identifiers.SetStringSelection( service_name )
                    
                    self._SetActions()
                    
                    if self._action is None: self._ratings_like_remove.SetValue( True )
                    elif self._action == True: self._ratings_like_like.SetValue( True )
                    elif self._action == False: self._ratings_like_dislike.SetValue( True )
                    
                elif service_type == HC.LOCAL_RATING_NUMERICAL:
                    
                    self._ratings_numerical_service_identifiers.SetStringSelection( service_name )
                    
                    self._SetActions()
                    
                    if self._action is None: self._ratings_numerical_remove.SetValue( True )
                    else:
                        
                        ( lower, upper ) = self._current_ratings_numerical_service.GetExtraInfo()
                        
                        slider_value = int( self._action * ( upper - lower ) ) + lower
                        
                        self._ratings_numerical_slider.SetValue( slider_value )
                        
                    
                
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label='cancel' )
            self._cancel.Bind( wx.EVT_BUTTON, self.EventCancel )
            self._cancel.SetSize( ( 0, 0 ) )
            
        
        def InitialisePanel():
            
            self._shortcut_panel.AddF( self._shortcut, FLAGS_EXPAND_PERPENDICULAR )
            
            none_hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            none_hbox.AddF( self._none_actions, FLAGS_EXPAND_DEPTH_ONLY )
            none_hbox.AddF( self._ok_none, FLAGS_MIXED )
            
            self._none_panel.AddF( none_hbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            tag_sub_vbox = wx.BoxSizer( wx.VERTICAL )
            
            tag_sub_vbox.AddF( self._tag_value, FLAGS_EXPAND_BOTH_WAYS )
            tag_sub_vbox.AddF( self._tag_input, FLAGS_EXPAND_BOTH_WAYS )
            
            tag_hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            tag_hbox.AddF( self._tag_service_identifiers, FLAGS_EXPAND_DEPTH_ONLY )
            tag_hbox.AddF( tag_sub_vbox, FLAGS_EXPAND_SIZER_BOTH_WAYS )
            tag_hbox.AddF( self._ok_tag, FLAGS_MIXED )
            
            self._tag_panel.AddF( tag_hbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            ratings_like_hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            ratings_like_hbox.AddF( self._ratings_like_service_identifiers, FLAGS_EXPAND_DEPTH_ONLY )
            ratings_like_hbox.AddF( self._ratings_like_like, FLAGS_MIXED )
            ratings_like_hbox.AddF( self._ratings_like_dislike, FLAGS_MIXED )
            ratings_like_hbox.AddF( self._ratings_like_remove, FLAGS_MIXED )
            ratings_like_hbox.AddF( self._ok_ratings_like, FLAGS_MIXED )
            
            self._ratings_like_panel.AddF( ratings_like_hbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            ratings_numerical_hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            ratings_numerical_hbox.AddF( self._ratings_numerical_service_identifiers, FLAGS_EXPAND_DEPTH_ONLY )
            ratings_numerical_hbox.AddF( self._ratings_numerical_slider, FLAGS_MIXED )
            ratings_numerical_hbox.AddF( self._ratings_numerical_remove, FLAGS_MIXED )
            ratings_numerical_hbox.AddF( self._ok_ratings_numerical, FLAGS_MIXED )
            
            self._ratings_numerical_panel.AddF( ratings_numerical_hbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( self._none_panel, FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._tag_panel, FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._ratings_like_panel, FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._ratings_numerical_panel, FLAGS_EXPAND_PERPENDICULAR )
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( self._shortcut_panel, FLAGS_MIXED )
            hbox.AddF( wx.StaticText( self, label = u'\u2192' ), FLAGS_MIXED )
            hbox.AddF( vbox, FLAGS_EXPAND_SIZER_BOTH_WAYS )
            
            self.SetSizer( hbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( 680, y ) )
            
        
        Dialog.__init__( self, parent, 'input custom filter action' )
        
        InitialiseControls()
        
        InitialisePanel()
        
    
    def _SetActions( self ):
        
        if self._ratings_like_service_identifiers.GetCount() > 0:
            
            selection = self._ratings_like_service_identifiers.GetSelection()
            
            if selection != wx.NOT_FOUND:
                
                service_identifier = self._ratings_like_service_identifiers.GetClientData( selection )
                
                service = wx.GetApp().Read( 'service', service_identifier )
                
                self._current_ratings_like_service = service
                
                ( like, dislike ) = service.GetExtraInfo()
                
                self._ratings_like_like.SetLabel( like )
                self._ratings_like_dislike.SetLabel( dislike )
                
            else:
                
                self._ratings_like_like.SetLabel( 'like' )
                self._ratings_like_dislike.SetLabel( 'dislike' )
                
            
        
        if self._ratings_numerical_service_identifiers.GetCount() > 0:
            
            selection = self._ratings_numerical_service_identifiers.GetSelection()
            
            if selection != wx.NOT_FOUND:
                
                service_identifier = self._ratings_numerical_service_identifiers.GetClientData( selection )
                
                service = wx.GetApp().Read( 'service', service_identifier )
                
                self._current_ratings_numerical_service = service
                
                ( lower, upper ) = service.GetExtraInfo()
                
                self._ratings_numerical_slider.SetRange( lower, upper )
                
            else: self._ratings_numerical_slider.SetRange( 0, 5 )
            
        
    
    def EventCancel( self, event ): self.EndModal( wx.ID_CANCEL )
    
    def EventOKNone( self, event ):
        
        self._service_identifier = None
        self._action = self._none_actions.GetStringSelection()
        self._pretty_action = self._action
        
        self.EndModal( wx.ID_OK )
        
    
    def EventOKRatingsLike( self, event ):
        
        selection = self._ratings_like_service_identifiers.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            self._service_identifier = self._ratings_like_service_identifiers.GetClientData( selection )
            
            ( like, dislike ) = self._current_ratings_like_service.GetExtraInfo()
            
            if self._ratings_like_like.GetValue():
                
                self._action = 1.0
                self._pretty_action = like
                
            elif self._ratings_like_dislike.GetValue():
                
                self._action = 0.0
                self._pretty_action = dislike
                
            else:
                
                self._action = None
                self._pretty_action = 'remove'
                
            
            self.EndModal( wx.ID_OK )
            
        else: self.EndModal( wx.ID_CANCEL )
        
    
    def EventOKRatingsNumerical( self, event ):
        
        selection = self._ratings_numerical_service_identifiers.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            self._service_identifier = self._ratings_numerical_service_identifiers.GetClientData( selection )
            
            if self._ratings_numerical_remove.GetValue():
                
                self._action = None
                self._pretty_action = 'remove'
                
            else:
                
                self._pretty_action = str( self._ratings_numerical_slider.GetValue() )
                
                ( lower, upper ) = self._current_ratings_numerical_service.GetExtraInfo()
                
                self._action = ( float( self._pretty_action ) - float( lower ) ) / ( upper - lower )
                
            
            self.EndModal( wx.ID_OK )
            
        else: self.EndModal( wx.ID_CANCEL )
        
    
    def EventOKTag( self, event ):
        
        selection = self._tag_service_identifiers.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            self._service_identifier = self._tag_service_identifiers.GetClientData( selection )
            
            self._action = self._tag_value.GetValue()
            self._pretty_action = self._action
            
            self.EndModal( wx.ID_OK )
            
        else: self.EndModal( wx.ID_CANCEL )
        
    
    def EventRecalcActions( self, event ):
        
        self._SetActions()
        
        event.Skip()
        
    
    def GetInfo( self ):
        
        ( modifier, key ) = self._shortcut.GetValue()
        
        if self._service_identifier is None: pretty_service_identifier = ''
        else: pretty_service_identifier = self._service_identifier.GetName()
        
        # ignore this pretty_action
        ( pretty_modifier, pretty_key, pretty_action ) = HC.ConvertShortcutToPrettyShortcut( modifier, key, self._action )
        
        return ( ( pretty_modifier, pretty_key, pretty_service_identifier, self._pretty_action ), ( modifier, key, self._service_identifier, self._action ) )
        
    
    def SetTag( self, tag ): self._tag_value.SetValue( tag )
    
class DialogInputNewAccounts( Dialog ):
    
    def __init__( self, parent, service_identifier ):
        
        def InitialiseControls():
            
            self._num = wx.SpinCtrl( self, min=1, max=10000 )
            self._num.SetValue( 1 )
            
            service = wx.GetApp().Read( 'service', service_identifier )
            
            connection = service.GetConnection()
            
            account_types = connection.Get( 'account_types' )
            
            self._account_types = wx.Choice( self, size = ( 400, -1 ) )
            
            for account_type in account_types: self._account_types.Append( account_type.ConvertToString(), account_type )
            
            self._account_types.SetSelection( 0 ) # admin
            
            self._expiration = wx.Choice( self )
            for ( str, value ) in HC.expirations: self._expiration.Append( str, value )
            self._expiration.SetSelection( 3 ) # one year
            
            self._ok = wx.Button( self, label='Ok' )
            self._ok.Bind( wx.EVT_BUTTON, self.EventOk )
            self._ok.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label='Cancel' )
            self._cancel.Bind( wx.EVT_BUTTON, self.EventCancel )        
            self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
            
        
        def InitialisePanel():
            
            ctrl_box = wx.BoxSizer( wx.HORIZONTAL )
            ctrl_box.AddF( self._num, FLAGS_SMALL_INDENT )
            ctrl_box.AddF( self._account_types, FLAGS_SMALL_INDENT )
            ctrl_box.AddF( self._expiration, FLAGS_SMALL_INDENT )
            
            b_box = wx.BoxSizer( wx.HORIZONTAL )
            b_box.AddF( self._ok, FLAGS_MIXED )
            b_box.AddF( self._cancel, FLAGS_MIXED )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( ctrl_box, FLAGS_EXPAND_SIZER_PERPENDICULAR )
            vbox.AddF( b_box, FLAGS_BUTTON_SIZERS )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
        
        Dialog.__init__( self, parent, 'configure new accounts' )
        
        self._service_identifier = service_identifier
        
        InitialiseControls()
        
        InitialisePanel()
        
    
    def EventCancel( self, event ): self.EndModal( wx.ID_CANCEL )
    
    def EventOk( self, event ):
        
        num = self._num.GetValue()
        
        account_type = self._account_types.GetClientData( self._account_types.GetSelection() )
        
        title = account_type.GetTitle()
        
        expiration = self._expiration.GetClientData( self._expiration.GetSelection() )
        
        service = wx.GetApp().Read( 'service', self._service_identifier )
        
        try:
            
            connection = service.GetConnection()
            
            if expiration is None: access_keys = connection.Get( 'registration_keys', num = num, title = title )
            else: access_keys = connection.Get( 'registration_keys', num = num, title = title, expiration = expiration )
            
        except Exception as e: wx.MessageBox( unicode( e ) )
        
        self.EndModal( wx.ID_OK )
        
    
class DialogInputNewAccountType( Dialog ):
    
    def __init__( self, parent, account_type = None ):
        
        def InitialiseControls():
            
            self._title = wx.TextCtrl( self, value = title )
            
            self._permissions_panel = ClientGUICommon.StaticBox( self, 'permissions' )
            
            self._permissions = wx.ListBox( self._permissions_panel )
            
            for permission in permissions: self._permissions.Append( HC.permissions_string_lookup[ permission ], permission )
            
            self._permission_choice = wx.Choice( self._permissions_panel )
            
            for permission in HC.CREATABLE_PERMISSIONS: self._permission_choice.Append( HC.permissions_string_lookup[ permission ], permission )
            
            self._permission_choice.SetSelection( 0 )
            
            self._add_permission = wx.Button( self._permissions_panel, label = 'add' )
            self._add_permission.Bind( wx.EVT_BUTTON, self.EventAddPermission )
            
            self._remove_permission = wx.Button( self._permissions_panel, label = 'remove' )
            self._remove_permission.Bind( wx.EVT_BUTTON, self.EventRemovePermission )
            
            self._max_num_mb = ClientGUICommon.NoneableSpinCtrl( self, 'max monthly data (MB)', max_num_bytes, multiplier = 1048576 )
            self._max_num_requests = ClientGUICommon.NoneableSpinCtrl( self, 'max monthly requests', max_num_requests )
            
            self._apply = wx.Button( self, label='apply' )
            self._apply.Bind( wx.EVT_BUTTON, self.EventOk )
            self._apply.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label='cancel' )
            self._cancel.Bind( wx.EVT_BUTTON, self.EventCancel )        
            self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
            
        
        def InitialisePanel():
            
            t_box = wx.BoxSizer( wx.HORIZONTAL )
            
            t_box.AddF( wx.StaticText( self, label = 'title: ' ), FLAGS_SMALL_INDENT )
            t_box.AddF( self._title, FLAGS_EXPAND_BOTH_WAYS )
            
            perm_buttons_box = wx.BoxSizer( wx.HORIZONTAL )
            
            perm_buttons_box.AddF( self._permission_choice, FLAGS_MIXED )
            perm_buttons_box.AddF( self._add_permission, FLAGS_MIXED )
            perm_buttons_box.AddF( self._remove_permission, FLAGS_MIXED )
            
            self._permissions_panel.AddF( self._permissions, FLAGS_EXPAND_BOTH_WAYS )
            self._permissions_panel.AddF( perm_buttons_box, FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            b_box = wx.BoxSizer( wx.HORIZONTAL )
            
            b_box.AddF( self._apply, FLAGS_MIXED )
            b_box.AddF( self._cancel, FLAGS_MIXED )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( t_box, FLAGS_EXPAND_SIZER_PERPENDICULAR )
            vbox.AddF( self._permissions_panel, FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._max_num_mb, FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._max_num_requests, FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( b_box, FLAGS_BUTTON_SIZERS )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( 800, y ) )
            
        
        if account_type is None:
            
            title = ''
            permissions = [ HC.GET_DATA ]
            max_num_bytes = 104857600
            max_num_requests = 1000
            
        else:
            
            title = account_type.GetTitle()
            permissions = account_type.GetPermissions()
            ( max_num_bytes, max_num_requests ) = account_type.GetMaxMonthlyData()
            
        
        Dialog.__init__( self, parent, 'edit account type' )
        
        InitialiseControls()
        
        InitialisePanel()
        
    
    def EventAddPermission( self, event ):
        
        selection = self._permission_choice.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            permission = self._permission_choice.GetClientData( selection )
            
            existing_permissions = [ self._permissions.GetClientData( i ) for i in range( self._permissions.GetCount() ) ]
            
            if permission not in existing_permissions: self._permissions.Append( HC.permissions_string_lookup[ permission ], permission )
            
        
    
    def EventCancel( self, event ): self.EndModal( wx.ID_CANCEL )
    
    def EventCheckBox( self, event ):
        
        if self._max_num_requests_checkbox.GetValue(): self._max_num_requests.Disable()
        else: self._max_num_requests.Enable()
        
    
    def EventOk( self, event ): self.EndModal( wx.ID_OK )
    
    def EventRemovePermission( self, event ):
        
        selection = self._permissions.GetSelection()
        
        if selection != wx.NOT_FOUND: self._permissions.Delete( selection )
        
    
    def GetAccountType( self ):
        
        title = self._title.GetValue()
        
        permissions = [ self._permissions.GetClientData( i ) for i in range( self._permissions.GetCount() ) ]
        
        max_num_bytes = self._max_num_mb.GetValue()
        
        max_num_requests = self._max_num_requests.GetValue()
        
        return HC.AccountType( title, permissions, ( max_num_bytes, max_num_requests ) )
        
    
class DialogInputNewFormField( Dialog ):
    
    def __init__( self, parent, form_field = None ):
        
        if form_field is None: ( name, type, default, editable ) = ( '', CC.FIELD_TEXT, '', True )
        else: ( name, type, default, editable ) = form_field
        
        def InitialiseControls():
            
            self._name = wx.TextCtrl( self, value = name )
            
            self._type = wx.Choice( self )
            
            for temp_type in CC.FIELDS: self._type.Append( CC.field_string_lookup[ temp_type ], temp_type )
            
            self._type.Select( type )
            
            self._default = wx.TextCtrl( self, value = default )
            
            self._editable = wx.CheckBox( self )
            
            self._editable.SetValue( editable )
            
            self._ok = wx.Button( self, label='Ok' )
            self._ok.Bind( wx.EVT_BUTTON, self.EventOk )
            self._ok.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label='Cancel' )
            self._cancel.Bind( wx.EVT_BUTTON, self.EventCancel )        
            self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
            
        
        def InitialisePanel():
            
            gridbox = wx.FlexGridSizer( 0, 2 )
            
            gridbox.AddGrowableCol( 1, 1 )
            
            gridbox.AddF( wx.StaticText( self, label='name' ), FLAGS_MIXED )
            gridbox.AddF( self._name, FLAGS_EXPAND_BOTH_WAYS )
            gridbox.AddF( wx.StaticText( self, label='type' ), FLAGS_MIXED )
            gridbox.AddF( self._type, FLAGS_EXPAND_BOTH_WAYS )
            gridbox.AddF( wx.StaticText( self, label='default' ), FLAGS_MIXED )
            gridbox.AddF( self._default, FLAGS_EXPAND_BOTH_WAYS )
            gridbox.AddF( wx.StaticText( self, label='editable' ), FLAGS_MIXED )
            gridbox.AddF( self._editable, FLAGS_EXPAND_BOTH_WAYS )
            
            b_box = wx.BoxSizer( wx.HORIZONTAL )
            b_box.AddF( self._ok, FLAGS_MIXED )
            b_box.AddF( self._cancel, FLAGS_MIXED )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( gridbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
            vbox.AddF( b_box, FLAGS_BUTTON_SIZERS )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
        
        Dialog.__init__( self, parent, 'configure form field' )
        
        InitialiseControls()
        
        InitialisePanel()
        
    
    def EventCancel( self, event ): self.EndModal( wx.ID_CANCEL )
    
    def EventOk( self, event ): self.EndModal( wx.ID_OK )
    
    def GetFormField( self ):
        
        name = self._name.GetValue()
        
        type = self._type.GetClientData( self._type.GetSelection() )
        
        default = self._default.GetValue()
        
        editable = self._editable.GetValue()
        
        return ( name, type, default, editable )
        
    
class DialogInputFileSystemPredicate( Dialog ):
    
    def __init__( self, parent, type ):
        
        def Age():
            
            def InitialiseControls():
                
                ( sign, years, months, days ) = system_predicates[ 'age' ]
                
                self._sign = wx.Choice( self, choices=[ '<', u'\u2248', '>' ] )
                self._sign.SetSelection( sign )
                
                self._years = wx.SpinCtrl( self, max = 30 )
                self._years.SetValue( years )
                self._months = wx.SpinCtrl( self, max = 60 )
                self._months.SetValue( months )
                self._days = wx.SpinCtrl( self, max = 90 )
                self._days.SetValue( days )
                
                self._ok = wx.Button( self, label='Ok' )
                self._ok.Bind( wx.EVT_BUTTON, self.EventOk )
                self._ok.SetForegroundColour( ( 0, 128, 0 ) )
                
            
            def InitialisePanel():
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( wx.StaticText( self, label='system:age' ), FLAGS_MIXED )
                hbox.AddF( self._sign, FLAGS_MIXED )
                hbox.AddF( self._years, FLAGS_MIXED )
                hbox.AddF( wx.StaticText( self, label='years' ), FLAGS_MIXED )
                hbox.AddF( self._months, FLAGS_MIXED )
                hbox.AddF( wx.StaticText( self, label='months' ), FLAGS_MIXED )
                hbox.AddF( self._days, FLAGS_MIXED )
                hbox.AddF( wx.StaticText( self, label='days' ), FLAGS_MIXED )
                hbox.AddF( self._ok, FLAGS_MIXED )
                
                self.SetSizer( hbox )
                
                ( x, y ) = self.GetEffectiveMinSize()
                
                self.SetInitialSize( ( x, y ) )
                
            
            Dialog.__init__( self, parent, 'enter age predicate' )
            
            InitialiseControls()
            
            InitialisePanel()
            
        
        def Duration():
            
            def InitialiseControls():
                
                ( sign, s, ms ) = system_predicates[ 'duration' ]
                
                self._sign = wx.Choice( self, choices=[ '<', u'\u2248', '=', '>' ] )
                self._sign.SetSelection( sign )
                
                self._duration_s = wx.SpinCtrl( self, max = 3599 )
                self._duration_s.SetValue( s )
                self._duration_ms = wx.SpinCtrl( self, max = 999 )
                self._duration_ms.SetValue( ms )
                
                self._ok = wx.Button( self, label='Ok' )
                self._ok.Bind( wx.EVT_BUTTON, self.EventOk )
                self._ok.SetForegroundColour( ( 0, 128, 0 ) )
                
            
            def InitialisePanel():
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( wx.StaticText( self, label='system:duration' ), FLAGS_MIXED )
                hbox.AddF( self._sign, FLAGS_MIXED )
                hbox.AddF( self._duration_s, FLAGS_MIXED )
                hbox.AddF( wx.StaticText( self, label='s' ), FLAGS_MIXED )
                hbox.AddF( self._duration_ms, FLAGS_MIXED )
                hbox.AddF( wx.StaticText( self, label='ms' ), FLAGS_MIXED )
                hbox.AddF( self._ok, FLAGS_MIXED )
                
                self.SetSizer( hbox )
                
                ( x, y ) = self.GetEffectiveMinSize()
                
                self.SetInitialSize( ( x, y ) )
                
            
            Dialog.__init__( self, parent, 'enter duration predicate' )
            
            InitialiseControls()
            
            InitialisePanel()
            
        
        def FileService():
            
            def InitialiseControls():
                
                self._sign = wx.Choice( self )
                self._sign.Append( 'is', True )
                self._sign.Append( 'is not', False )
                self._sign.SetSelection( 0 )
                
                self._current_pending = wx.Choice( self )
                self._current_pending.Append( 'currently in', HC.CURRENT )
                self._current_pending.Append( 'pending to', HC.PENDING )
                self._current_pending.SetSelection( 0 )
                
                service_identifiers = wx.GetApp().Read( 'service_identifiers', ( HC.FILE_REPOSITORY, HC.LOCAL_FILE ) )
                
                self._file_service_identifier = wx.Choice( self )
                for service_identifier in service_identifiers: self._file_service_identifier.Append( service_identifier.GetName(), service_identifier )
                self._file_service_identifier.SetSelection( 0 )
                
                self._ok = wx.Button( self, label='Ok' )
                self._ok.Bind( wx.EVT_BUTTON, self.EventOk )
                self._ok.SetForegroundColour( ( 0, 128, 0 ) )
                
            
            def InitialisePanel():
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( wx.StaticText( self, label='system:file service:' ), FLAGS_MIXED )
                hbox.AddF( self._sign, FLAGS_MIXED )
                hbox.AddF( self._current_pending, FLAGS_MIXED )
                hbox.AddF( self._file_service_identifier, FLAGS_MIXED )
                hbox.AddF( self._ok, FLAGS_MIXED )
                
                self.SetSizer( hbox )
                
                ( x, y ) = self.GetEffectiveMinSize()
                
                self.SetInitialSize( ( x, y ) )
                
            
            Dialog.__init__( self, parent, 'enter file service predicate' )
            
            InitialiseControls()
            
            InitialisePanel()
            
        
        def Hash():
            
            def InitialiseControls():
                
                self._hash = wx.TextCtrl( self )
                
                self._ok = wx.Button( self, label='Ok' )
                self._ok.Bind( wx.EVT_BUTTON, self.EventOk )
                self._ok.SetForegroundColour( ( 0, 128, 0 ) )
                
            
            def InitialisePanel():
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( wx.StaticText( self, label='system:hash=' ), FLAGS_MIXED )
                hbox.AddF( self._hash, FLAGS_MIXED )
                hbox.AddF( self._ok, FLAGS_MIXED )
                
                self.SetSizer( hbox )
                
                ( x, y ) = self.GetEffectiveMinSize()
                
                self.SetInitialSize( ( x, y ) )
                
            
            Dialog.__init__( self, parent, 'enter hash predicate' )
            
            InitialiseControls()
            
            InitialisePanel()
            
        
        def Height():
            
            def InitialiseControls():
                
                ( sign, height ) = system_predicates[ 'height' ]
                
                self._sign = wx.Choice( self, choices=[ '<', u'\u2248', '=', '>' ] )
                self._sign.SetSelection( sign )
                
                self._height = wx.SpinCtrl( self, max = 200000 )
                self._height.SetValue( height )
                
                self._ok = wx.Button( self, label='Ok' )
                self._ok.Bind( wx.EVT_BUTTON, self.EventOk )
                self._ok.SetForegroundColour( ( 0, 128, 0 ) )
                
            
            def InitialisePanel():
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( wx.StaticText( self, label='system:height' ), FLAGS_MIXED )
                hbox.AddF( self._sign, FLAGS_MIXED )
                hbox.AddF( self._height, FLAGS_MIXED )
                hbox.AddF( self._ok, FLAGS_MIXED )
                
                self.SetSizer( hbox )
                
                ( x, y ) = self.GetEffectiveMinSize()
                
                self.SetInitialSize( ( x, y ) )
                
            
            Dialog.__init__( self, parent, 'enter height predicate' )
            
            InitialiseControls()
            
            InitialisePanel()
            
        
        def Limit():
            
            def InitialiseControls():
                
                limit = system_predicates[ 'limit' ]
                
                self._limit = wx.SpinCtrl( self, max = 1000000 )
                self._limit.SetValue( limit )
                
                self._ok = wx.Button( self, label='Ok' )
                self._ok.Bind( wx.EVT_BUTTON, self.EventOk )
                self._ok.SetForegroundColour( ( 0, 128, 0 ) )
                
            
            def InitialisePanel():
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( wx.StaticText( self, label='system:limit=' ), FLAGS_MIXED )
                hbox.AddF( self._limit, FLAGS_MIXED )
                hbox.AddF( self._ok, FLAGS_MIXED )
                
                self.SetSizer( hbox )
                
                ( x, y ) = self.GetEffectiveMinSize()
                
                self.SetInitialSize( ( x, y ) )
                
            
            Dialog.__init__( self, parent, 'enter limit predicate' )
            
            InitialiseControls()
            
            InitialisePanel()
            
        
        def Mime():
            
            def InitialiseControls():
                
                ( media, type ) = system_predicates[ 'mime' ]
                
                self._mime_media = wx.Choice( self, choices=[ 'image', 'application', 'video' ] )
                self._mime_media.SetSelection( media )
                self._mime_media.Bind( wx.EVT_CHOICE, self.EventMime )
                
                self._mime_type = wx.Choice( self, choices=[], size = ( 120, -1 ) )
                
                self.EventMime( None )
                
                self._mime_type.SetSelection( type )
                
                self._ok = wx.Button( self, label='Ok' )
                self._ok.Bind( wx.EVT_BUTTON, self.EventOk )
                self._ok.SetForegroundColour( ( 0, 128, 0 ) )
                
            
            def InitialisePanel():
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( wx.StaticText( self, label='system:mime' ), FLAGS_MIXED )
                hbox.AddF( self._mime_media, FLAGS_MIXED )
                hbox.AddF( wx.StaticText( self, label='/' ), FLAGS_MIXED )
                hbox.AddF( self._mime_type, FLAGS_MIXED )
                hbox.AddF( self._ok, FLAGS_MIXED )
                
                self.SetSizer( hbox )
                
                ( x, y ) = self.GetEffectiveMinSize()
                
                self.SetInitialSize( ( x, y ) )
                
            
            Dialog.__init__( self, parent, 'enter mime predicate' )
            
            InitialiseControls()
            
            InitialisePanel()
            
        
        def NumTags():
            
            def InitialiseControls():
                
                ( sign, num_tags ) = system_predicates[ 'num_tags' ]
                
                self._sign = wx.Choice( self, choices=[ '<', u'\u2248', '=', '>' ] )
                self._sign.SetSelection( sign )
                
                self._num_tags = wx.SpinCtrl( self, max = 2000 )
                self._num_tags.SetValue( num_tags )
                
                self._ok = wx.Button( self, label='Ok' )
                self._ok.Bind( wx.EVT_BUTTON, self.EventOk )
                self._ok.SetForegroundColour( ( 0, 128, 0 ) )
                
            
            def InitialisePanel():
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( wx.StaticText( self, label='system:num_tags' ), FLAGS_MIXED )
                hbox.AddF( self._sign, FLAGS_MIXED )
                hbox.AddF( self._num_tags, FLAGS_MIXED )
                hbox.AddF( self._ok, FLAGS_MIXED )
                
                self.SetSizer( hbox )
                
                ( x, y ) = self.GetEffectiveMinSize()
                
                self.SetInitialSize( ( x, y ) )
                
            
            Dialog.__init__( self, parent, 'enter number of tags predicate' )
            
            InitialiseControls()
            
            InitialisePanel()
            
        
        def NumWords():
            
            def InitialiseControls():
                
                ( sign, num_words ) = system_predicates[ 'num_words' ]
                
                self._sign = wx.Choice( self, choices=[ '<', u'\u2248', '=', '>' ] )
                self._sign.SetSelection( sign )
                
                self._num_words = wx.SpinCtrl( self, max = 1000000 )
                self._num_words.SetValue( num_words )
                
                self._ok = wx.Button( self, label='Ok' )
                self._ok.Bind( wx.EVT_BUTTON, self.EventOk )
                self._ok.SetForegroundColour( ( 0, 128, 0 ) )
                
            
            def InitialisePanel():
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( wx.StaticText( self, label='system:num_words' ), FLAGS_MIXED )
                hbox.AddF( self._sign, FLAGS_MIXED )
                hbox.AddF( self._num_words, FLAGS_MIXED )
                hbox.AddF( self._ok, FLAGS_MIXED )
                
                self.SetSizer( hbox )
                
                ( x, y ) = self.GetEffectiveMinSize()
                
                self.SetInitialSize( ( x, y ) )
                
            
            Dialog.__init__( self, parent, 'enter number of words predicate' )
            
            InitialiseControls()
            
            InitialisePanel()
            
        
        def Rating():
            
            def InitialiseControls():
                
                self._service_numerical = wx.Choice( self )
                for service in self._local_numericals: self._service_numerical.Append( service.GetServiceIdentifier().GetName(), service )
                self._service_numerical.Bind( wx.EVT_CHOICE, self.EventRatingsService )
                
                ( sign, value ) = system_predicates[ 'local_rating_numerical' ]
                
                self._sign_numerical = wx.Choice( self, choices=[ '>', '<', '=', u'\u2248', '=rated', '=not rated', '=uncertain' ] )
                self._sign_numerical.SetSelection( sign )
                
                self._value_numerical = wx.SpinCtrl( self, min = 0, max = 50000 ) # set bounds based on current service
                self._value_numerical.SetValue( value )
                
                self._first_ok = wx.Button( self, label='Ok', id = HC.LOCAL_RATING_NUMERICAL )
                self._first_ok.Bind( wx.EVT_BUTTON, self.EventOk )
                self._first_ok.SetForegroundColour( ( 0, 128, 0 ) )
                
                self._service_like = wx.Choice( self )
                for service in self._local_likes: self._service_like.Append( service.GetServiceIdentifier().GetName(), service )
                self._service_like.Bind( wx.EVT_CHOICE, self.EventRatingsService )
                
                value = system_predicates[ 'local_rating_like' ]
                
                self._value_like = wx.Choice( self, choices=[ 'like', 'dislike', 'rated', 'not rated' ] ) # set words based on current service
                self._value_like.SetSelection( value )
                
                self._second_ok = wx.Button( self, label='Ok', id = HC.LOCAL_RATING_LIKE )
                self._second_ok.Bind( wx.EVT_BUTTON, self.EventOk )
                self._second_ok.SetForegroundColour( ( 0, 128, 0 ) )
                
                if len( self._local_numericals ) > 0: self._service_numerical.SetSelection( 0 )
                if len( self._local_likes ) > 0: self._service_like.SetSelection( 0 )
                
                self.EventRatingsService( None )
                
            
            def InitialisePanel():
                
                vbox = wx.BoxSizer( wx.VERTICAL )
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( wx.StaticText( self, label='system:rating:' ), FLAGS_MIXED )
                hbox.AddF( self._service_numerical, FLAGS_MIXED )
                hbox.AddF( self._sign_numerical, FLAGS_MIXED )
                hbox.AddF( self._value_numerical, FLAGS_MIXED )
                hbox.AddF( self._first_ok, FLAGS_MIXED )
                
                vbox.AddF( hbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( wx.StaticText( self, label='system:rating:' ), FLAGS_MIXED )
                hbox.AddF( self._service_like, FLAGS_MIXED )
                hbox.AddF( wx.StaticText( self, label='=' ), FLAGS_MIXED )
                hbox.AddF( self._value_like, FLAGS_MIXED )
                hbox.AddF( self._second_ok, FLAGS_MIXED )
                
                vbox.AddF( hbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
                
                self.SetSizer( vbox )
                
                ( x, y ) = self.GetEffectiveMinSize()
                
                self.SetInitialSize( ( x, y ) )
                
            
            Dialog.__init__( self, parent, 'enter rating predicate' )
            
            self._local_numericals = wx.GetApp().Read( 'services', ( HC.LOCAL_RATING_NUMERICAL, ) )
            self._local_likes = wx.GetApp().Read( 'services', ( HC.LOCAL_RATING_LIKE, ) )
            
            InitialiseControls()
            
            InitialisePanel()
            
        
        def Ratio():
            
            def InitialiseControls():
                
                ( sign, width, height ) = system_predicates[ 'ratio' ]
                
                self._sign = wx.Choice( self, choices=[ '=', u'\u2248' ] )
                self._sign.SetSelection( sign )
                
                self._width = wx.SpinCtrl( self, max = 50000 )
                self._width.SetValue( width )
                
                self._height = wx.SpinCtrl( self, max = 50000 )
                self._height.SetValue( height )
                
                self._ok = wx.Button( self, label='Ok' )
                self._ok.Bind( wx.EVT_BUTTON, self.EventOk )
                self._ok.SetForegroundColour( ( 0, 128, 0 ) )
                
            
            def InitialisePanel():
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( wx.StaticText( self, label='system:ratio' ), FLAGS_MIXED )
                hbox.AddF( self._sign, FLAGS_MIXED )
                hbox.AddF( self._width, FLAGS_MIXED )
                hbox.AddF( wx.StaticText( self, label=':' ), FLAGS_MIXED )
                hbox.AddF( self._height, FLAGS_MIXED )
                hbox.AddF( self._ok, FLAGS_MIXED )
                
                self.SetSizer( hbox )
                
                ( x, y ) = self.GetEffectiveMinSize()
                
                self.SetInitialSize( ( x, y ) )
                
            
            Dialog.__init__( self, parent, 'enter ratio predicate' )
            
            InitialiseControls()
            
            InitialisePanel()
            
        
        def Size():
            
            def InitialiseControls():
                
                ( sign, size, unit ) = system_predicates[ 'size' ]
                
                self._sign = wx.Choice( self, choices=[ '<', u'\u2248', '=', '>' ] )
                self._sign.SetSelection( sign )
                
                self._size = wx.SpinCtrl( self, max = 1048576 )
                self._size.SetValue( size )
                
                self._unit = wx.Choice( self, choices=[ 'B', 'KB', 'MB', 'GB' ] )
                self._unit.SetSelection( unit )
                
                self._ok = wx.Button( self, label='Ok' )
                self._ok.Bind( wx.EVT_BUTTON, self.EventOk )
                self._ok.SetForegroundColour( ( 0, 128, 0 ) )
                
            
            def InitialisePanel():
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( wx.StaticText( self, label='system:size' ), FLAGS_MIXED )
                hbox.AddF( self._sign, FLAGS_MIXED )
                hbox.AddF( self._size, FLAGS_MIXED )
                hbox.AddF( self._unit, FLAGS_MIXED )
                hbox.AddF( self._ok, FLAGS_MIXED )
                
                self.SetSizer( hbox )
                
                ( x, y ) = self.GetEffectiveMinSize()
                
                self.SetInitialSize( ( x, y ) )
                
            
            Dialog.__init__( self, parent, 'enter size predicate' )
            
            InitialiseControls()
            
            InitialisePanel()
            
        
        def Width():
            
            def InitialiseControls():
                
                ( sign, width ) = system_predicates[ 'width' ]
                
                self._sign = wx.Choice( self, choices=[ '<', u'\u2248', '=', '>' ] )
                self._sign.SetSelection( sign )
                
                self._width = wx.SpinCtrl( self, max = 200000 )
                self._width.SetValue( width )
                
                self._ok = wx.Button( self, label='Ok' )
                self._ok.Bind( wx.EVT_BUTTON, self.EventOk )
                self._ok.SetForegroundColour( ( 0, 128, 0 ) )
                
            
            def InitialisePanel():
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( wx.StaticText( self, label='system:width' ), FLAGS_MIXED )
                hbox.AddF( self._sign, FLAGS_MIXED )
                hbox.AddF( self._width, FLAGS_MIXED )
                hbox.AddF( self._ok, FLAGS_MIXED )
                
                self.SetSizer( hbox )
                
                ( x, y ) = self.GetEffectiveMinSize()
                
                self.SetInitialSize( ( x, y ) )
                
            
            Dialog.__init__( self, parent, 'enter width predicate' )
            
            InitialiseControls()
            
            InitialisePanel()
            
        
        def SimilarTo():
            
            def InitialiseControls():
                
                self._hash = wx.TextCtrl( self )
                self._hash.SetValue( 'enter hash' )
                
                self._max_hamming = wx.SpinCtrl( self, initial = 5, max = 256 )
                
                self._ok = wx.Button( self, label='Ok' )
                self._ok.Bind( wx.EVT_BUTTON, self.EventOk )
                self._ok.SetForegroundColour( ( 0, 128, 0 ) )
                
            
            def InitialisePanel():
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( wx.StaticText( self, label='system:similar_to' ), FLAGS_MIXED )
                hbox.AddF( self._hash, FLAGS_MIXED )
                hbox.AddF( wx.StaticText( self, label=u'\u2248' ), FLAGS_MIXED )
                hbox.AddF( self._max_hamming, FLAGS_MIXED )
                hbox.AddF( self._ok, FLAGS_MIXED )
                
                self.SetSizer( hbox )
                
                ( x, y ) = self.GetEffectiveMinSize()
                
                self.SetInitialSize( ( x, y ) )
                
            
            Dialog.__init__( self, parent, 'enter similar to predicate' )
            
            InitialiseControls()
            
            InitialisePanel()
            
        
        options = wx.GetApp().Read( 'options' )
        
        system_predicates = options[ 'file_system_predicates' ]
        
        self._type = type
        
        if self._type == HC.SYSTEM_PREDICATE_TYPE_AGE: Age()
        elif self._type == HC.SYSTEM_PREDICATE_TYPE_DURATION: Duration()
        elif self._type == HC.SYSTEM_PREDICATE_TYPE_HASH: Hash()
        elif self._type == HC.SYSTEM_PREDICATE_TYPE_HEIGHT: Height()
        elif self._type == HC.SYSTEM_PREDICATE_TYPE_LIMIT: Limit()
        elif self._type == HC.SYSTEM_PREDICATE_TYPE_MIME: Mime()
        elif self._type == HC.SYSTEM_PREDICATE_TYPE_NUM_TAGS: NumTags()
        elif self._type == HC.SYSTEM_PREDICATE_TYPE_RATING: Rating()
        elif self._type == HC.SYSTEM_PREDICATE_TYPE_RATIO: Ratio()
        elif self._type == HC.SYSTEM_PREDICATE_TYPE_SIZE: Size()
        elif self._type == HC.SYSTEM_PREDICATE_TYPE_WIDTH: Width()
        elif self._type == HC.SYSTEM_PREDICATE_TYPE_SIMILAR_TO: SimilarTo()
        elif self._type == HC.SYSTEM_PREDICATE_TYPE_NUM_WORDS: NumWords()
        elif self._type == HC.SYSTEM_PREDICATE_TYPE_FILE_SERVICE: FileService()
        
        self._hidden_cancel_button = wx.Button( self, id = wx.ID_CANCEL, label = 'cancel', size = ( 0, 0 ) )
        self._hidden_cancel_button.Bind( wx.EVT_BUTTON, self.EventCancel )
        # hide doesn't keep the escape hotkey, so say size = ( 0, 0 )
        # self._hidden_cancel_button.Hide()
        
    
    def EventCancel( self, event ): self.EndModal( wx.ID_CANCEL )
    
    def EventMime( self, event ):
        
        media = self._mime_media.GetStringSelection()
        
        self._mime_type.Clear()
        
        if media == 'image':
            
            self._mime_type.Append( 'any', HC.IMAGES )
            self._mime_type.Append( 'jpeg', HC.IMAGE_JPEG )
            self._mime_type.Append( 'png', HC.IMAGE_PNG )
            self._mime_type.Append( 'gif', HC.IMAGE_GIF )
            
        elif media == 'application':
            
            self._mime_type.Append( 'any', HC.APPLICATIONS )
            self._mime_type.Append( 'pdf', HC.APPLICATION_PDF )
            self._mime_type.Append( 'x-shockwave-flash', HC.APPLICATION_FLASH )
            
        elif media == 'video':
            
            self._mime_type.Append( 'x-flv', HC.VIDEO_FLV )
            
        
        self._mime_type.SetSelection( 0 )
        
    
    def EventOk( self, event ):
        
        if self._type == HC.SYSTEM_PREDICATE_TYPE_AGE: info = ( self._sign.GetStringSelection(), self._years.GetValue(), self._months.GetValue(), self._days.GetValue() )
        elif self._type == HC.SYSTEM_PREDICATE_TYPE_DURATION: info = ( self._sign.GetStringSelection(), self._duration_s.GetValue() * 1000 + self._duration_ms.GetValue() )
        elif self._type == HC.SYSTEM_PREDICATE_TYPE_HASH:
            
            hex_filter = lambda c: c in '0123456789abcdef'
            
            hash = filter( hex_filter, self._hash.GetValue() )
            
            if len( hash ) == 0: hash == '00'
            elif len( hash ) % 2 == 1: hash += '0' # since we are later decoding to byte
            
            info = hash.decode( 'hex' )
            
        elif self._type == HC.SYSTEM_PREDICATE_TYPE_HEIGHT: info = ( self._sign.GetStringSelection(), self._height.GetValue() )
        elif self._type == HC.SYSTEM_PREDICATE_TYPE_LIMIT: info = self._limit.GetValue()
        elif self._type == HC.SYSTEM_PREDICATE_TYPE_MIME: info = self._mime_type.GetClientData( self._mime_type.GetSelection() )
        elif self._type == HC.SYSTEM_PREDICATE_TYPE_NUM_TAGS: info = ( self._sign.GetStringSelection(), self._num_tags.GetValue() )
        elif self._type == HC.SYSTEM_PREDICATE_TYPE_NUM_WORDS: info = ( self._sign.GetStringSelection(), self._num_words.GetValue() )
        elif self._type == HC.SYSTEM_PREDICATE_TYPE_RATING:
            
            id = event.GetId()
            
            if id == HC.LOCAL_RATING_LIKE:
                
                service_identifier = self._service_like.GetClientData( self._service_like.GetSelection() ).GetServiceIdentifier()
                
                operator = '='
                
                selection = self._value_like.GetSelection()
                
                if selection == 0: value = '1'
                elif selection == 1: value = '0'
                elif selection == 2: value = 'rated'
                elif selection == 3: value = 'not rated'
                
                info = ( service_identifier, operator, value )
                
            elif id == HC.LOCAL_RATING_NUMERICAL:
                
                service = self._service_numerical.GetClientData( self._service_numerical.GetSelection() )
                
                service_identifier = service.GetServiceIdentifier()
                
                operator = self._sign_numerical.GetStringSelection()
                
                if operator in ( '=rated', '=not rated', '=uncertain' ):
                    
                    value = operator[1:]
                    
                    operator = '='
                    
                else:
                    
                    ( lower, upper ) = service.GetExtraInfo()
                    
                    value_raw = self._value_numerical.GetValue()
                    
                    value = float( value_raw - lower ) / float( upper - lower )
                    
                
                info = ( service_identifier, operator, value )
                
            
        elif self._type == HC.SYSTEM_PREDICATE_TYPE_RATIO: info = ( self._sign.GetStringSelection(), float( ( self._width.GetValue() ) / float( self._height.GetValue() ) ) )
        elif self._type == HC.SYSTEM_PREDICATE_TYPE_SIZE: info = ( self._sign.GetStringSelection(), self._size.GetValue(), HC.ConvertUnitToInteger( self._unit.GetStringSelection() ) )
        elif self._type == HC.SYSTEM_PREDICATE_TYPE_WIDTH: info = ( self._sign.GetStringSelection(), self._width.GetValue() )
        elif self._type == HC.SYSTEM_PREDICATE_TYPE_SIMILAR_TO:
            
            hex_filter = lambda c: c in '0123456789abcdef'
            
            hash = filter( hex_filter, self._hash.GetValue() )
            
            if len( hash ) == 0: hash == '00'
            elif len( hash ) % 2 == 1: hash += '0' # since we are later decoding to byte
            
            info = ( hash.decode( 'hex' ), self._max_hamming.GetValue() )
            
        elif self._type == HC.SYSTEM_PREDICATE_TYPE_FILE_SERVICE: info = ( self._sign.GetClientData( self._sign.GetSelection() ), self._current_pending.GetClientData( self._current_pending.GetSelection() ), self._file_service_identifier.GetClientData( self._file_service_identifier.GetSelection() ) )
        
        self._predicate = HC.Predicate( HC.PREDICATE_TYPE_SYSTEM, ( self._type, info ), None )
        
        self.EndModal( wx.ID_OK )
        
    
    def EventRatingsService( self, event ):
        
        try:
            
            service = self._service_numerical.GetClientData( self._service_numerical.GetSelection() )
            
            ( min, max ) = service.GetExtraInfo()
            
            self._value_numerical.SetRange( min, max )
            
            service = self._service_like.GetClientData( self._service_like.GetSelection() )
            
        except: pass
        
        try:
            
            ( like, dislike ) = service.GetExtraInfo()
            
            selection = self._value_like.GetSelection()
            
            self._value_like.SetString( 0, like )
            self._value_like.SetString( 1, dislike )
            
            self._value_like.SetSelection( selection )
            
        except: pass
        
    
    def GetPredicate( self ): return self._predicate
    
class DialogInputMessageSystemPredicate( Dialog ):
    
    def __init__( self, parent, type ):
        
        def Age():
            
            def InitialiseControls():
                
                self._sign = wx.Choice( self, choices=[ '<', u'\u2248', '>' ] )
                self._sign.SetSelection( 0 )
                
                self._years = wx.SpinCtrl( self, initial = 0, max = 30 )
                self._months = wx.SpinCtrl( self, initial = 0, max = 60 )
                self._days = wx.SpinCtrl( self, initial = 7, max = 90 )
                
                self._ok = wx.Button( self, label='Ok' )
                self._ok.Bind( wx.EVT_BUTTON, self.EventOk )
                self._ok.SetForegroundColour( ( 0, 128, 0 ) )
                
            
            def InitialisePanel():
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( wx.StaticText( self, label='system:age' ), FLAGS_MIXED )
                hbox.AddF( self._sign, FLAGS_MIXED )
                hbox.AddF( self._years, FLAGS_MIXED )
                hbox.AddF( wx.StaticText( self, label='years' ), FLAGS_MIXED )
                hbox.AddF( self._months, FLAGS_MIXED )
                hbox.AddF( wx.StaticText( self, label='months' ), FLAGS_MIXED )
                hbox.AddF( self._days, FLAGS_MIXED )
                hbox.AddF( wx.StaticText( self, label='days' ), FLAGS_MIXED )
                hbox.AddF( self._ok, FLAGS_MIXED )
                
                self.SetSizer( hbox )
                
                ( x, y ) = self.GetEffectiveMinSize()
                
                self.SetInitialSize( ( x, y ) )
                
            
            Dialog.__init__( self, parent, 'enter age predicate' )
            
            InitialiseControls()
            
            InitialisePanel()
            
        
        def From():
            
            def InitialiseControls():
                
                contact_names = wx.GetApp().Read( 'contact_names' )
                
                self._contact = wx.Choice( self, choices=contact_names )
                self._contact.SetSelection( 0 )
                
                self._ok = wx.Button( self, label='Ok' )
                self._ok.Bind( wx.EVT_BUTTON, self.EventOk )
                self._ok.SetForegroundColour( ( 0, 128, 0 ) )
                
            
            def InitialisePanel():
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( wx.StaticText( self, label='system:from' ), FLAGS_MIXED )
                hbox.AddF( self._contact, FLAGS_MIXED )
                hbox.AddF( self._ok, FLAGS_MIXED )
                
                self.SetSizer( hbox )
                
                ( x, y ) = self.GetEffectiveMinSize()
                
                self.SetInitialSize( ( x, y ) )
                
            
            Dialog.__init__( self, parent, 'enter from predicate' )
            
            InitialiseControls()
            
            InitialisePanel()
            
        
        def StartedBy():
            
            def InitialiseControls():
                
                contact_names = wx.GetApp().Read( 'contact_names' )
                
                self._contact = wx.Choice( self, choices=contact_names )
                self._contact.SetSelection( 0 )
                
                self._ok = wx.Button( self, label='Ok' )
                self._ok.Bind( wx.EVT_BUTTON, self.EventOk )
                self._ok.SetForegroundColour( ( 0, 128, 0 ) )
                
            
            def InitialisePanel():
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( wx.StaticText( self, label='system:started_by' ), FLAGS_MIXED )
                hbox.AddF( self._contact, FLAGS_MIXED )
                hbox.AddF( self._ok, FLAGS_MIXED )
                
                self.SetSizer( hbox )
                
                ( x, y ) = self.GetEffectiveMinSize()
                
                self.SetInitialSize( ( x, y ) )
                
            
            Dialog.__init__( self, parent, 'enter started by predicate' )
            
            InitialiseControls()
            
            InitialisePanel()
            
        
        def To():
            
            def InitialiseControls():
                
                contact_names = [ name for name in wx.GetApp().Read( 'contact_names' ) if name != 'Anonymous' ]
                
                self._contact = wx.Choice( self, choices=contact_names )
                self._contact.SetSelection( 0 )
                
                self._ok = wx.Button( self, label='Ok' )
                self._ok.Bind( wx.EVT_BUTTON, self.EventOk )
                self._ok.SetForegroundColour( ( 0, 128, 0 ) )
                
            
            def InitialisePanel():
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( wx.StaticText( self, label='system:to' ), FLAGS_MIXED )
                hbox.AddF( self._contact, FLAGS_MIXED )
                hbox.AddF( self._ok, FLAGS_MIXED )
                
                self.SetSizer( hbox )
                
                ( x, y ) = self.GetEffectiveMinSize()
                
                self.SetInitialSize( ( x, y ) )
                
            
            Dialog.__init__( self, parent, 'enter to predicate' )
            
            InitialiseControls()
            
            InitialisePanel()
            
        
        def NumAttachments():
            
            def InitialiseControls():
                
                self._sign = wx.Choice( self, choices=[ '<', '=', '>' ] )
                self._sign.SetSelection( 0 )
                
                self._num_attachments = wx.SpinCtrl( self, initial = 4, max = 2000 )
                
                self._ok = wx.Button( self, label='Ok' )
                self._ok.Bind( wx.EVT_BUTTON, self.EventOk )
                self._ok.SetForegroundColour( ( 0, 128, 0 ) )
                
            
            def InitialisePanel():
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( wx.StaticText( self, label='system:numattachments' ), FLAGS_MIXED )
                hbox.AddF( self._sign, FLAGS_MIXED )
                hbox.AddF( self._num_attachments, FLAGS_MIXED )
                hbox.AddF( self._ok, FLAGS_MIXED )
                
                self.SetSizer( hbox )
                
                ( x, y ) = self.GetEffectiveMinSize()
                
                self.SetInitialSize( ( x, y ) )
                
            
            Dialog.__init__( self, parent, 'enter number of attachments predicate' )
            
            InitialiseControls()
            
            InitialisePanel()
            
        
        self._type = type
        
        if self._type == 'system:age': Age()
        elif self._type == 'system:started_by': StartedBy()
        elif self._type == 'system:from': From()
        elif self._type == 'system:to': To()
        elif self._type == 'system:numattachments': NumAttachments()
        
        self._hidden_cancel_button = wx.Button( self, id = wx.ID_CANCEL, label = 'cancel', size = ( 0, 0 ) )
        self._hidden_cancel_button.Bind( wx.EVT_BUTTON, self.EventCancel )
        # hide doesn't keep the escape hotkey, so say size = ( 0, 0 )
        # self._hidden_cancel_button.Hide()
        
    
    def EventCancel( self, event ): self.EndModal( wx.ID_CANCEL )
    
    def EventOk( self, event ): self.EndModal( wx.ID_OK )
    
    def GetString( self ):
        
        if self._type == 'system:age': return 'system:age' + self._sign.GetStringSelection() + str( self._years.GetValue() ) + 'y' + str( self._months.GetValue() ) + 'm' + str( self._days.GetValue() ) + 'd'
        elif self._type == 'system:started_by': return 'system:started_by=' + self._contact.GetStringSelection()
        elif self._type == 'system:from': return 'system:from=' + self._contact.GetStringSelection()
        elif self._type == 'system:to': return 'system:to=' + self._contact.GetStringSelection()
        elif self._type == 'system:numattachments': return 'system:numattachments' + self._sign.GetStringSelection() + str( self._num_attachments.GetValue() )
        
    
class DialogInputShortcut( Dialog ):
    
    def __init__( self, parent, modifier = wx.ACCEL_NORMAL, key = wx.WXK_F7, action = 'new_page' ):
        
        self._action = action
        
        def InitialiseControls():
            
            self._shortcut = ClientGUICommon.Shortcut( self, modifier, key )
            
            self._actions = wx.Choice( self, choices = [ 'archive', 'inbox', 'close_page', 'filter', 'fullscreen_switch', 'ratings_filter', 'frame_back', 'frame_next', 'manage_ratings', 'manage_tags', 'new_page', 'refresh', 'set_search_focus', 'show_hide_splitters', 'synchronised_wait_switch', 'previous', 'next', 'first', 'last' ] )
            self._actions.SetSelection( self._actions.FindString( action ) )
            
            self._ok = wx.Button( self, label='Ok' )
            self._ok.Bind( wx.EVT_BUTTON, self.EventOk )
            self._ok.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label='Cancel' )
            self._cancel.Bind( wx.EVT_BUTTON, self.EventCancel )        
            self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
            
        
        def InitialisePanel():
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( self._shortcut, FLAGS_MIXED )
            hbox.AddF( self._actions, FLAGS_EXPAND_PERPENDICULAR )
            
            b_box = wx.BoxSizer( wx.HORIZONTAL )
            b_box.AddF( self._ok, FLAGS_MIXED )
            b_box.AddF( self._cancel, FLAGS_MIXED )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( hbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
            vbox.AddF( b_box, FLAGS_BUTTON_SIZERS )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
        
        Dialog.__init__( self, parent, 'configure shortcut' )
        
        InitialiseControls()
        
        InitialisePanel()
        
    
    def EventCancel( self, event ): self.EndModal( wx.ID_CANCEL )
    
    def EventOk( self, event ): self.EndModal( wx.ID_OK )
    
    def GetInfo( self ):
        
        ( modifier, key ) = self._shortcut.GetValue()
        
        return ( modifier, key, self._actions.GetStringSelection() )
        
    
class DialogManageAccountTypes( Dialog ):
    
    def __init__( self, parent, service_identifier ):
        
        def InitialiseControls():
            
            service = wx.GetApp().Read( 'service', service_identifier )
            
            connection = service.GetConnection()
            
            account_types = connection.Get( 'account_types' )
            
            self._titles_to_account_types = {}
            
            self._account_types_panel = ClientGUICommon.StaticBox( self, 'account types' )
            
            self._ctrl_account_types = ClientGUICommon.SaneListCtrl( self._account_types_panel, 350, [ ( 'title', 120 ), ( 'permissions', -1 ), ( 'max monthly bytes', 120 ), ( 'max monthly requests', 120 ) ] )
            
            for account_type in account_types:
                
                title = account_type.GetTitle()
                
                self._titles_to_account_types[ title ] = account_type
                
                permissions = account_type.GetPermissions()
                
                permissions_string = ', '.join( [ HC.permissions_string_lookup[ permission ] for permission in permissions ] )
                
                ( max_num_bytes, max_num_requests ) = account_type.GetMaxMonthlyData()
                
                ( max_num_bytes_string, max_num_requests_string ) = account_type.GetMaxMonthlyDataString()
                
                self._ctrl_account_types.Append( ( title, permissions_string, max_num_bytes_string, max_num_requests_string ), ( title, len( permissions ), max_num_bytes, max_num_requests ) )
                
            
            self._add = wx.Button( self._account_types_panel, label='add' )
            self._add.Bind( wx.EVT_BUTTON, self.EventAdd )
            
            self._edit = wx.Button( self._account_types_panel, label='edit' )
            self._edit.Bind( wx.EVT_BUTTON, self.EventEdit )
            
            self._delete = wx.Button( self._account_types_panel, label='delete' )
            self._delete.Bind( wx.EVT_BUTTON, self.EventDelete )
            
            self._apply = wx.Button( self, label='apply' )
            self._apply.Bind( wx.EVT_BUTTON, self.EventOk )
            self._apply.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label='cancel' )
            self._cancel.Bind( wx.EVT_BUTTON, self.EventCancel )        
            self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
            
        
        def InitialisePanel():
            
            h_b_box = wx.BoxSizer( wx.HORIZONTAL )
            
            h_b_box.AddF( self._add, FLAGS_MIXED )
            h_b_box.AddF( self._edit, FLAGS_MIXED )
            h_b_box.AddF( self._delete, FLAGS_MIXED )
            
            self._account_types_panel.AddF( self._ctrl_account_types, FLAGS_EXPAND_BOTH_WAYS )
            self._account_types_panel.AddF( h_b_box, FLAGS_BUTTON_SIZERS )
            
            b_box = wx.BoxSizer( wx.HORIZONTAL )
            b_box.AddF( self._apply, FLAGS_MIXED )
            b_box.AddF( self._cancel, FLAGS_MIXED )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            vbox.AddF( self._account_types_panel, FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( b_box, FLAGS_BUTTON_SIZERS )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( 980, y ) )
            
        
        Dialog.__init__( self, parent, 'manage account types' )
        
        self._service_identifier = service_identifier
        
        self._edit_log = []
        
        try:
            
            InitialiseControls()
            
            InitialisePanel()
            
        except: raise
        
    
    def EventAdd( self, event ):
        
        try:
            
            with DialogInputNewAccountType( self ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    account_type = dlg.GetAccountType()
                    
                    title = account_type.GetTitle()
                    
                    permissions = account_type.GetPermissions()
                    
                    permissions_string = ', '.join( [ HC.permissions_string_lookup[ permission ] for permission in permissions ] )
                    
                    ( max_num_bytes, max_num_requests ) = account_type.GetMaxMonthlyData()
                    
                    ( max_num_bytes_string, max_num_requests_string ) = account_type.GetMaxMonthlyDataString()
                    
                    if title in self._titles_to_account_types: raise Exception( 'You already have an account type called ' + title + '; delete or edit that one first' )
                    
                    self._titles_to_account_types[ title ] = account_type
                    
                    self._edit_log.append( ( 'add', account_type ) )
                    
                    self._ctrl_account_types.Append( ( title, permissions_string, max_num_bytes_string, max_num_requests_string ), ( title, len( permissions ), max_num_bytes, max_num_requests ) )
                    
                
            
        except Exception as e: wx.MessageBox( unicode( e ) )
        
    
    def EventCancel( self, event ): self.EndModal( wx.ID_CANCEL )
    
    def EventDelete( self, event ):
        
        indices = self._ctrl_account_types.GetAllSelected()
        
        titles_about_to_delete = { self._ctrl_account_types.GetClientData( index )[0] for index in indices }
        
        all_titles = set( self._titles_to_account_types.keys() )
        
        titles_can_move_to = list( all_titles - titles_about_to_delete )
        
        if len( titles_can_move_to ) == 0:
            
            wx.MessageBox( 'You cannot delete every account type!' )
            
            return
            
        
        for title in titles_about_to_delete:
            
            with DialogSelectFromListOfStrings( self, 'what should deleted ' + title + ' accounts become?', titles_can_move_to ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK: title_to_move_to = dlg.GetString()
                else: return
                
            
            self._edit_log.append( ( 'delete', ( title, title_to_move_to ) ) )
            
        
        self._ctrl_account_types.RemoveAllSelected()
        
    
    def EventEdit( self, event ):
        
        indices = self._ctrl_account_types.GetAllSelected()
        
        for index in indices:
            
            title = self._ctrl_account_types.GetClientData( index )[0]
            
            account_type = self._titles_to_account_types[ title ]
            
            try:
                
                with DialogInputNewAccountType( self, account_type ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        old_title = title
                        
                        account_type = dlg.GetAccountType()
                        
                        title = account_type.GetTitle()
                        
                        permissions = account_type.GetPermissions()
                        
                        permissions_string = ', '.join( [ HC.permissions_string_lookup[ permission ] for permission in permissions ] )
                        
                        ( max_num_bytes, max_num_requests ) = account_type.GetMaxMonthlyData()
                        
                        ( max_num_bytes_string, max_num_requests_string ) = account_type.GetMaxMonthlyDataString()
                        
                        if old_title != title:
                            
                            if title in self._titles_to_account_types: raise Exception( 'You already have an account type called ' + title + '; delete or edit that one first' )
                            
                            del self._titles_to_account_types[ old_title ]
                            
                        
                        self._titles_to_account_types[ title ] = account_type
                        
                        self._edit_log.append( ( 'edit', ( old_title, account_type ) ) )
                        
                        self._ctrl_account_types.UpdateRow( index, ( title, permissions_string, max_num_bytes_string, max_num_requests_string ), ( title, len( permissions ), max_num_bytes, max_num_requests ) )
                        
                    
                
            except Exception as e: wx.MessageBox( unicode( e ) )
            
        
    
    def EventOk( self, event ):
        
        try:
            
            service = wx.GetApp().Read( 'service', self._service_identifier )
            
            connection = service.GetConnection()
            
            connection.Post( 'account_types_modification', edit_log = self._edit_log )
            
        except Exception as e: wx.MessageBox( unicode( e ) )
        
        self.EndModal( wx.ID_OK )
        
    
class DialogManageBoorus( Dialog ):
    
    def __init__( self, parent ):
        
        def InitialiseControls():
            
            self._edit_log = []
            
            self._boorus = ClientGUICommon.ListBook( self )
            
            boorus = wx.GetApp().Read( 'boorus' )
            
            for booru in boorus:
                
                name = booru.GetName()
                
                page_info = ( self._Panel, ( self._boorus, booru ), {} )
                
                self._boorus.AddPage( page_info, name )
                
            
            self._add = wx.Button( self, label='add' )
            self._add.Bind( wx.EVT_BUTTON, self.EventAdd )
            self._add.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._remove = wx.Button( self, label='remove' )
            self._remove.Bind( wx.EVT_BUTTON, self.EventRemove )
            self._remove.SetForegroundColour( ( 128, 0, 0 ) )
            
            self._export = wx.Button( self, label='export' )
            self._export.Bind( wx.EVT_BUTTON, self.EventExport )
            
            self._ok = wx.Button( self, label='ok' )
            self._ok.Bind( wx.EVT_BUTTON, self.EventOk )
            self._ok.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label='cancel' )
            self._cancel.Bind( wx.EVT_BUTTON, self.EventCancel )
            self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
            
        
        def InitialisePanel():
            
            add_remove_hbox = wx.BoxSizer( wx.HORIZONTAL )
            add_remove_hbox.AddF( self._add, FLAGS_MIXED )
            add_remove_hbox.AddF( self._remove, FLAGS_MIXED )
            add_remove_hbox.AddF( self._export, FLAGS_MIXED )
            
            ok_hbox = wx.BoxSizer( wx.HORIZONTAL )
            ok_hbox.AddF( self._ok, FLAGS_MIXED )
            ok_hbox.AddF( self._cancel, FLAGS_MIXED )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            vbox.AddF( self._boorus, FLAGS_EXPAND_BOTH_WAYS )
            vbox.AddF( add_remove_hbox, FLAGS_SMALL_INDENT )
            vbox.AddF( ok_hbox, FLAGS_BUTTON_SIZERS )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( 980, y ) )
            
        
        Dialog.__init__( self, parent, 'manage boorus' )
        
        InitialiseControls()
        
        InitialisePanel()
        
        self.SetDropTarget( ClientGUICommon.FileDropTarget( self.Import ) )
        
    
    def EventAdd( self, event ):
        
        with wx.TextEntryDialog( self, 'Enter new booru\'s name' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                try:
                    
                    name = dlg.GetValue()
                    
                    if self._boorus.NameExists( name ): raise Exception( 'That name is already in use!' )
                    
                    if name == '': raise Exception( 'Please enter a nickname for the service.' )
                    
                    booru = CC.Booru( name, 'search_url', '+', 1, 'thumbnail', '', 'original image', {} )
                    
                    self._edit_log.append( ( 'add', name ) )
                    
                    page = self._Panel( self._boorus, booru )
                    
                    self._boorus.AddPage( page, name, select = True )
                    
                except Exception as e:
                    
                    wx.MessageBox( unicode( e ) )
                    
                    self.EventAdd( event )
                    
                
            
        
    
    def EventCancel( self, event ): self.EndModal( wx.ID_CANCEL )
    
    def EventExport( self, event ):
        
        booru_panel = self._boorus.GetCurrentPage()
        
        if booru_panel is not None:
            
            name = self._boorus.GetCurrentName()
            
            booru = booru_panel.GetBooru()
            
            with wx.FileDialog( self, 'select where to export booru', defaultFile = 'booru.yaml', style = wx.FD_SAVE ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    with open( dlg.GetPath(), 'wb' ) as f: f.write( yaml.safe_dump( booru ) )
                    
                
            
        
    
    def EventOk( self, event ):
        
        for ( name, page ) in self._boorus.GetNameToPageDict().items():
            
            if page.HasChanges(): self._edit_log.append( ( 'edit', ( name, page.GetBooru() ) ) )
            
        
        try:
            
            if len( self._edit_log ) > 0: wx.GetApp().Write( 'update_boorus', self._edit_log )
            
        except Exception as e: wx.MessageBox( 'Saving boorus to DB raised this error: ' + unicode( e ) )
        
        self.EndModal( wx.ID_OK )
        
    
    def EventRemove( self, event ):
        
        booru_panel = self._boorus.GetCurrentPage()
        
        if booru_panel is not None:
            
            name = self._boorus.GetCurrentName()
            
            self._edit_log.append( ( 'delete', name ) )
            
            self._boorus.DeleteCurrentPage()
            
        
    
    def Import( self, paths ):
        
        for path in paths:
            
            try:
                
                with open( path, 'rb' ) as f: file = f.read()
                
                thing = yaml.safe_load( file )
                
                if type( thing ) == CC.Booru:
                    
                    booru = thing
                    
                    name = booru.GetName()
                    
                    if not self._boorus.NameExists( name ):
                        
                        new_booru = CC.Booru( name, 'search_url', '+', 1, 'thumbnail', '', 'original image', {} )
                        
                        self._edit_log.append( ( 'add', name ) )
                        
                        page = self._Panel( self._boorus, new_booru )
                        
                        self._boorus.AddPage( page, name, select = True )
                        
                    
                    page = self._boorus.GetNameToPageDict()[ name ]
                    
                    page.Update( booru )
                    
                
            except:
                
                wx.MessageBox( traceback.format_exc() )
                
            
        
    
    class _Panel( wx.Panel ):
        
        def __init__( self, parent, booru ):
            
            wx.Panel.__init__( self, parent )
            
            self._booru = booru
            
            ( search_url, search_separator, gallery_advance_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces ) = booru.GetData()
            
            def InitialiseControls():
                
                self._booru_panel = ClientGUICommon.StaticBox( self, 'booru' )
                
                #
                
                self._search_panel = ClientGUICommon.StaticBox( self._booru_panel, 'search' )
                
                self._search_url = wx.TextCtrl( self._search_panel, value = search_url )
                self._search_url.Bind( wx.EVT_TEXT, self.EventHTML )
                
                self._search_separator = wx.Choice( self._search_panel, choices = [ '+', '&', '%20' ] )
                self._search_separator.Select( self._search_separator.FindString( search_separator ) )
                self._search_separator.Bind( wx.EVT_CHOICE, self.EventHTML )
                
                self._gallery_advance_num = wx.SpinCtrl( self._search_panel, min = 1, max = 1000 )
                self._gallery_advance_num.SetValue( gallery_advance_num )
                self._gallery_advance_num.Bind( wx.EVT_SPIN, self.EventHTML )
                
                self._thumb_classname = wx.TextCtrl( self._search_panel, value = thumb_classname )
                self._thumb_classname.Bind( wx.EVT_TEXT, self.EventHTML )
                
                self._example_html_search = wx.StaticText( self._search_panel, style = wx.ST_NO_AUTORESIZE )
                
                #
                
                self._image_panel = ClientGUICommon.StaticBox( self._booru_panel, 'image' )
                
                self._image_info = wx.TextCtrl( self._image_panel )
                self._image_info.Bind( wx.EVT_TEXT, self.EventHTML )
                
                self._image_id = wx.RadioButton( self._image_panel, style = wx.RB_GROUP )
                self._image_id.Bind( wx.EVT_RADIOBUTTON, self.EventHTML )
                
                self._image_data = wx.RadioButton( self._image_panel )
                self._image_data.Bind( wx.EVT_RADIOBUTTON, self.EventHTML )
                
                if image_id is None:
                    
                    self._image_info.SetValue( image_data )
                    self._image_data.SetValue( True )
                    
                else:
                    
                    self._image_info.SetValue( image_id )
                    self._image_id.SetValue( True )
                    
                
                self._example_html_image = wx.StaticText( self._image_panel, style = wx.ST_NO_AUTORESIZE )
                
                #
                
                self._tag_panel = ClientGUICommon.StaticBox( self._booru_panel, 'tags' )
                
                self._tag_classnames_to_namespaces = wx.ListBox( self._tag_panel, style = wx.LB_SORT )
                self._tag_classnames_to_namespaces.Bind( wx.EVT_LEFT_DCLICK, self.EventRemove )
                
                for ( tag_classname, namespace ) in tag_classnames_to_namespaces.items(): self._tag_classnames_to_namespaces.Append( tag_classname + ' : ' + namespace, ( tag_classname, namespace ) )
                
                self._tag_classname = wx.TextCtrl( self._tag_panel )
                self._namespace = wx.TextCtrl( self._tag_panel )
                
                self._add = wx.Button( self._tag_panel, label = 'add' )
                self._add.Bind( wx.EVT_BUTTON, self.EventAdd )
                
                self._example_html_tags = wx.StaticText( self._tag_panel, style = wx.ST_NO_AUTORESIZE )
                
            
            def InitialisePanel():
                
                self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
                
                gridbox = wx.FlexGridSizer( 0, 2 )
                
                gridbox.AddGrowableCol( 1, 1 )
                
                gridbox.AddF( wx.StaticText( self._search_panel, label='search url' ), FLAGS_MIXED )
                gridbox.AddF( self._search_url, FLAGS_EXPAND_BOTH_WAYS )
                gridbox.AddF( wx.StaticText( self._search_panel, label='search tag separator' ), FLAGS_MIXED )
                gridbox.AddF( self._search_separator, FLAGS_EXPAND_BOTH_WAYS )
                gridbox.AddF( wx.StaticText( self._search_panel, label='gallery page advance' ), FLAGS_MIXED )
                gridbox.AddF( self._gallery_advance_num, FLAGS_EXPAND_BOTH_WAYS )
                gridbox.AddF( wx.StaticText( self._search_panel, label='thumbnail classname' ), FLAGS_MIXED )
                gridbox.AddF( self._thumb_classname, FLAGS_EXPAND_BOTH_WAYS )
                
                self._search_panel.AddF( gridbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
                self._search_panel.AddF( self._example_html_search, FLAGS_EXPAND_PERPENDICULAR )
                
                #
                
                gridbox = wx.FlexGridSizer( 0, 2 )
                
                gridbox.AddGrowableCol( 1, 1 )
                
                gridbox.AddF( wx.StaticText( self._image_panel, label='text' ), FLAGS_MIXED )
                gridbox.AddF( self._image_info, FLAGS_EXPAND_BOTH_WAYS )
                gridbox.AddF( wx.StaticText( self._image_panel, label='id of <img>' ), FLAGS_MIXED )
                gridbox.AddF( self._image_id, FLAGS_EXPAND_BOTH_WAYS )
                gridbox.AddF( wx.StaticText( self._image_panel, label='text of <a>' ), FLAGS_MIXED )
                gridbox.AddF( self._image_data, FLAGS_EXPAND_BOTH_WAYS )
                
                self._image_panel.AddF( gridbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
                self._image_panel.AddF( self._example_html_image, FLAGS_EXPAND_PERPENDICULAR )
                
                #
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( self._tag_classname, FLAGS_MIXED )
                hbox.AddF( self._namespace, FLAGS_MIXED )
                hbox.AddF( self._add, FLAGS_MIXED )
                
                self._tag_panel.AddF( self._tag_classnames_to_namespaces, FLAGS_EXPAND_BOTH_WAYS )
                self._tag_panel.AddF( hbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
                self._tag_panel.AddF( self._example_html_tags, FLAGS_EXPAND_PERPENDICULAR )
                
                #
                
                self._booru_panel.AddF( self._search_panel, FLAGS_EXPAND_PERPENDICULAR )
                self._booru_panel.AddF( self._image_panel, FLAGS_EXPAND_PERPENDICULAR )
                self._booru_panel.AddF( self._tag_panel, FLAGS_EXPAND_BOTH_WAYS )
                
                vbox = wx.BoxSizer( wx.VERTICAL )
                
                vbox.AddF( self._booru_panel, FLAGS_EXPAND_BOTH_WAYS )
                
                self.SetSizer( vbox )
                
            
            InitialiseControls()
            
            InitialisePanel()
            
        
        def _GetInfo( self ):
            
            booru_name = self._booru.GetName()
            
            search_url = self._search_url.GetValue()
            
            search_separator = self._search_separator.GetStringSelection()
            
            gallery_advance_num = self._gallery_advance_num.GetValue()
            
            thumb_classname = self._thumb_classname.GetValue()
            
            if self._image_id.GetValue():
                
                image_id = self._image_info.GetValue()
                image_data = None
                
            else:
                
                image_id = None
                image_data = self._image_info.GetValue()
                
            
            tag_classnames_to_namespaces = { tag_classname : namespace for ( tag_classname, namespace ) in [ self._tag_classnames_to_namespaces.GetClientData( i ) for i in range( self._tag_classnames_to_namespaces.GetCount() ) ] }
            
            return ( booru_name, search_url, search_separator, gallery_advance_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces )
            
        
        def EventAdd( self, event ):
            
            tag_classname = self._tag_classname.GetValue()
            namespace = self._namespace.GetValue()
            
            if tag_classname != '':
                
                self._tag_classnames_to_namespaces.Append( tag_classname + ' : ' + namespace, ( tag_classname, namespace ) )
                
                self._tag_classname.SetValue( '' )
                self._namespace.SetValue( '' )
                
                self.EventHTML( event )
                
            
        
        def EventHTML( self, event ):
            
            pass
            
        
        def EventRemove( self, event ):
            
            selection = self._tag_classnames_to_namespaces.GetSelection()
            
            if selection != wx.NOT_FOUND:
                
                self._tag_classnames_to_namespaces.Delete( selection )
                
                self.EventHTML( event )
                
            
        
        def GetBooru( self ):
            
            ( booru_name, search_url, search_separator, gallery_advance_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces ) = self._GetInfo()
            
            return CC.Booru( booru_name, search_url, search_separator, gallery_advance_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces )
            
        
        def HasChanges( self ):
            
            ( booru_name, my_search_url, my_search_separator, my_gallery_advance_num, my_thumb_classname, my_image_id, my_image_data, my_tag_classnames_to_namespaces ) = self._GetInfo()
            
            ( search_url, search_separator, gallery_advance_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces ) = self._booru.GetData()
            
            if search_url != my_search_url: return True
            
            if search_separator != my_search_separator: return True
            
            if gallery_advance_num != my_gallery_advance_num: return True
            
            if thumb_classname != my_thumb_classname: return True
            
            if image_id != my_image_id: return True
            
            if image_data != my_image_data: return True
            
            if tag_classnames_to_namespaces != my_tag_classnames_to_namespaces: return True
            
            return False
            
        
        def Update( self, booru ):
            
            ( search_url, search_separator, gallery_advance_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces ) = booru.GetData()
            
            self._search_url.SetValue( search_url )
            
            self._search_separator.Select( self._search_separator.FindString( search_separator ) )
            
            self._gallery_advance_num.SetValue( gallery_advance_num )
            
            self._thumb_classname.SetValue( thumb_classname )
            
            if image_id is None:
                
                self._image_info.SetValue( image_data )
                self._image_data.SetValue( True )
                
            else:
                
                self._image_info.SetValue( image_id )
                self._image_id.SetValue( True )
                
            
            self._tag_classnames_to_namespaces.Clear()
            
            for ( tag_classname, namespace ) in tag_classnames_to_namespaces.items(): self._tag_classnames_to_namespaces.Append( tag_classname + ' : ' + namespace, ( tag_classname, namespace ) )
            
        
    
class DialogManageContacts( Dialog ):
    
    def __init__( self, parent ):
        
        def InitialiseControls():
            
            self._edit_log = []
            
            self._contacts = ClientGUICommon.ListBook( self )
            
            ( identities, contacts, deletable_names ) = wx.GetApp().Read( 'identities_and_contacts' )
            
            self._deletable_names = deletable_names
            
            for identity in identities:
                
                name = identity.GetName()
                
                page_info = ( self._Panel, ( self._contacts, identity ), { 'is_identity' : True } )
                
                self._contacts.AddPage( page_info, ' identity - ' + name )
                
            
            for contact in contacts:
                
                name = contact.GetName()
                
                page_info = ( self._Panel, ( self._contacts, contact ), { 'is_identity' : False } )
                
                self._contacts.AddPage( page_info, name )
                
            
            # bind events after population
            self._contacts.Bind( wx.EVT_NOTEBOOK_PAGE_CHANGING, self.EventContactChanging )
            self._contacts.Bind( wx.EVT_NOTEBOOK_PAGE_CHANGED, self.EventContactChanged )
            
            self._add_contact_address = wx.Button( self, label='add by contact address' )
            self._add_contact_address.Bind( wx.EVT_BUTTON, self.EventAddByContactAddress )
            self._add_contact_address.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._add_manually = wx.Button( self, label='add manually' )
            self._add_manually.Bind( wx.EVT_BUTTON, self.EventAddManually )
            self._add_manually.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._remove = wx.Button( self, label='remove' )
            self._remove.Bind( wx.EVT_BUTTON, self.EventRemove )
            self._remove.SetForegroundColour( ( 128, 0, 0 ) )
            
            self._export = wx.Button( self, label='export' )
            self._export.Bind( wx.EVT_BUTTON, self.EventExport )
            
            self._ok = wx.Button( self, label='ok' )
            self._ok.Bind( wx.EVT_BUTTON, self.EventOk )
            self._ok.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label='cancel' )
            self._cancel.Bind( wx.EVT_BUTTON, self.EventCancel )
            self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
            
        
        def InitialisePanel():
            
            add_remove_hbox = wx.BoxSizer( wx.HORIZONTAL )
            add_remove_hbox.AddF( self._add_manually, FLAGS_MIXED )
            add_remove_hbox.AddF( self._add_contact_address, FLAGS_MIXED )
            add_remove_hbox.AddF( self._remove, FLAGS_MIXED )
            add_remove_hbox.AddF( self._export, FLAGS_MIXED )
            
            ok_hbox = wx.BoxSizer( wx.HORIZONTAL )
            ok_hbox.AddF( self._ok, FLAGS_MIXED )
            ok_hbox.AddF( self._cancel, FLAGS_MIXED )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            vbox.AddF( self._contacts, FLAGS_EXPAND_BOTH_WAYS )
            vbox.AddF( add_remove_hbox, FLAGS_SMALL_INDENT )
            vbox.AddF( ok_hbox, FLAGS_BUTTON_SIZERS )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( 980, y ) )
            
        
        Dialog.__init__( self, parent, 'manage contacts' )
        
        InitialiseControls()
        
        InitialisePanel()
        
        self.SetDropTarget( ClientGUICommon.FileDropTarget( self.Import ) )
        
        self.EventContactChanged( None )
        
    
    def _CheckCurrentContactIsValid( self ):
        
        contact_panel = self._contacts.GetCurrentPage()
        
        if contact_panel is not None:
            
            contact = contact_panel.GetContact()
            
            old_name = self._contacts.GetCurrentName()
            name = contact.GetName()
            
            if name != old_name and ' identity - ' + name != old_name:
                
                if self._contacts.NameExists( name ) or self._contacts.NameExists( ' identity - ' + name ) or name == 'Anonymous': raise Exception( 'That name is already in use!' )
                
                if old_name.startswith( ' identity - ' ): self._contacts.RenamePage( old_name, ' identity - ' + name )
                else: self._contacts.RenamePage( old_name, name )
                
            
        
    
    def EventAddByContactAddress( self, event ):
        
        try: self._CheckCurrentContactIsValid()
        except Exception as e:
            
            wx.MessageBox( unicode( e ) )
            
            return
            
        
        with wx.TextEntryDialog( self, 'Enter contact\'s address in the form contact_key@hostname:port' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                try:
                    
                    contact_address = dlg.GetValue()
                    
                    try:
                        
                        ( contact_key_encoded, address ) = contact_address.split( '@' )
                        
                        contact_key = contact_key_encoded.decode( 'hex' )
                        
                        ( host, port ) = address.split( ':' )
                        
                        port = int( port )
                        
                    except: raise Exception( 'Could not parse the address!' )
                    
                    name = contact_key_encoded
                    
                    contact = ClientConstantsMessages.Contact( None, name, host, port )
                    
                    try:
                        
                        connection = contact.GetConnection()
                        
                        public_key = connection.Get( 'public_key', contact_key = contact_key.encode( 'hex' ) )
                        
                    except: raise Exception( 'Could not fetch the contact\'s public key from the address:' + os.linesep + traceback.format_exc() )
                    
                    contact = ClientConstantsMessages.Contact( public_key, name, host, port )
                    
                    self._edit_log.append( ( 'add', contact ) )
                    
                    page = self._Panel( self._contacts, contact, is_identity = False )
                    
                    self._deletable_names.add( name )
                    
                    self._contacts.AddPage( page, name, select = True )
                    
                except Exception as e:
                    
                    wx.MessageBox( unicode( e ) )
                    
                    self.EventAddByContactAddress( event )
                    
                
            
        
    
    def EventAddManually( self, event ):
        
        try: self._CheckCurrentContactIsValid()
        except Exception as e:
            
            wx.MessageBox( unicode( e ) )
            
            return
            
        
        with wx.TextEntryDialog( self, 'Enter new contact\'s name' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                try:
                    
                    name = dlg.GetValue()
                    
                    if self._contacts.NameExists( name ) or self._contacts.NameExists( ' identity - ' + name ) or name == 'Anonymous': raise Exception( 'That name is already in use!' )
                    
                    if name == '': raise Exception( 'Please enter a nickname for the service.' )
                    
                    public_key = None
                    host = 'hostname'
                    port = 45871
                    
                    contact = ClientConstantsMessages.Contact( public_key, name, host, port )
                    
                    self._edit_log.append( ( 'add', contact ) )
                    
                    page = self._Panel( self._contacts, contact, is_identity = False )
                    
                    self._deletable_names.add( name )
                    
                    self._contacts.AddPage( page, name, select = True )
                    
                except Exception as e:
                    
                    wx.MessageBox( unicode( e ) )
                    
                    self.EventAddManually( event )
                    
                
            
        
    
    def EventCancel( self, event ): self.EndModal( wx.ID_CANCEL )
    
    def EventContactChanged( self, event ):
        
        contact_panel = self._contacts.GetCurrentPage()
        
        if contact_panel is not None:
            
            old_name = contact_panel.GetOriginalName()
            
            if old_name in self._deletable_names: self._remove.Enable()
            else: self._remove.Disable()
            
        
    
    def EventContactChanging( self, event ):
        
        try: self._CheckCurrentContactIsValid()
        except Exception as e:
            
            wx.MessageBox( unicode( e ) )
            
            event.Veto()
            
        
    
    def EventExport( self, event ):
        
        contact_panel = self._contacts.GetCurrentPage()
        
        if contact_panel is not None:
            
            name = self._contacts.GetCurrentName()
            
            contact = contact_panel.GetContact()
            
            try:
                
                with wx.FileDialog( self, 'select where to export contact', defaultFile = name + '.yaml', style = wx.FD_SAVE ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        with open( dlg.GetPath(), 'wb' ) as f: f.write( yaml.safe_dump( contact ) )
                        
                    
                
            except:
                
                with wx.FileDialog( self, 'select where to export contact', defaultFile = 'contact.yaml', style = wx.FD_SAVE ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        with open( dlg.GetPath(), 'wb' ) as f: f.write( yaml.safe_dump( contact ) )
                        
                    
                
            
        
    
    def EventOk( self, event ):
        
        try: self._CheckCurrentContactIsValid()
        except Exception as e:
            
            wx.MessageBox( unicode( e ) )
            
            return
            
        
        for ( name, page ) in self._contacts.GetNameToPageDict().items():
            
            if page.HasChanges(): self._edit_log.append( ( 'edit', ( page.GetOriginalName(), page.GetContact() ) ) )
            
        
        try:
            
            if len( self._edit_log ) > 0: wx.GetApp().Write( 'update_contacts', self._edit_log )
            
        except Exception as e: wx.MessageBox( 'Saving contacts to DB raised this error: ' + unicode( e ) )
        
        self.EndModal( wx.ID_OK )
        
    
    # this isn't used yet!
    def EventRemove( self, event ):
        
        contact_panel = self._contacts.GetCurrentPage()
        
        if contact_panel is not None:
            
            name = contact_panel.GetOriginalName()
            
            self._edit_log.append( ( 'delete', name ) )
            
            self._contacts.DeleteCurrentPage()
            
            self._deletable_names.discard( name )
            
        
    
    def Import( self, paths ):
        
        try: self._CheckCurrentContactIsValid()
        except Exception as e:
            
            wx.MessageBox( unicode( e ) )
            
            return
            
        
        for path in paths:
            
            try:
                
                with open( path, 'rb' ) as f: file = f.read()
                
                obj = yaml.safe_load( file )
                
                if type( obj ) == ClientConstantsMessages.Contact:
                    
                    contact = obj
                    
                    name = contact.GetName()
                    
                    if self._contacts.NameExists( name ) or self._contacts.NameExists( ' identities - ' + name ) or name == 'Anonymous':
                        
                        message = 'There already exists a contact or identity with the name ' + name + '. Do you want to overwrite, or make a new contact?'
                        
                        with DialogYesNo( self, message, yes_label = 'overwrite', no_label = 'make new' ) as dlg:
                            
                            if True:
                                
                                name_to_page_dict = self._contacts.GetNameToPageDict()
                                
                                if name in name_to_page_dict: page = name_to_page_dict[ name ]
                                else: page = name_to_page_dict[ ' identities - ' + name ]
                                
                                page.Update( contact )
                                
                            else:
                                
                                while self._contacts.NameExists( name ) or self._contacts.NameExists( ' identities - ' + name ) or name == 'Anonymous': name = name + str( random.randint( 0, 9 ) )
                                
                                ( public_key, old_name, host, port ) = contact.GetInfo()
                                
                                new_contact = ClientConstantsMessages.Contact( public_key, name, host, port )
                                
                                self._edit_log.append( ( 'add', contact ) )
                                
                                self._deletable_names.add( name )
                                
                                page = self._Panel( self._contacts, contact, False )
                                
                                self._contacts.AddPage( page, name, select = True )
                                
                            
                        
                    else:
                        
                        ( public_key, old_name, host, port ) = contact.GetInfo()
                        
                        new_contact = ClientConstantsMessages.Contact( public_key, name, host, port )
                        
                        self._edit_log.append( ( 'add', contact ) )
                        
                        self._deletable_names.add( name )
                        
                        page = self._Panel( self._contacts, contact, False )
                        
                        self._contacts.AddPage( page, name, select = True )
                        
                    
                
            except:
                
                wx.MessageBox( traceback.format_exc() )
                
            
        
    
    class _Panel( wx.Panel ):
        
        def __init__( self, parent, contact, is_identity ):
            
            wx.Panel.__init__( self, parent )
            
            self._contact = contact
            self._is_identity = is_identity
            
            ( public_key, name, host, port ) = contact.GetInfo()
            
            contact_key = contact.GetContactKey()
            
            def InitialiseControls():
                
                self._contact_panel = ClientGUICommon.StaticBox( self, 'contact' )
                
                self._name = wx.TextCtrl( self._contact_panel, value = name )
                
                contact_address = host + ':' + str( port )
                
                if contact_key is not None: contact_address = contact_key.encode( 'hex' ) + '@' + contact_address
                
                self._contact_address = wx.TextCtrl( self._contact_panel, value = contact_address )
                
                self._public_key = wx.TextCtrl( self._contact_panel, style = wx.TE_MULTILINE )
                
                if public_key is not None: self._public_key.SetValue( public_key )
                
            
            def InitialisePanel():
                
                self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
                
                gridbox = wx.FlexGridSizer( 0, 2 )
                
                gridbox.AddGrowableCol( 1, 1 )
                
                gridbox.AddF( wx.StaticText( self._contact_panel, label='name' ), FLAGS_MIXED )
                gridbox.AddF( self._name, FLAGS_EXPAND_BOTH_WAYS )
                gridbox.AddF( wx.StaticText( self._contact_panel, label='contact address' ), FLAGS_MIXED )
                gridbox.AddF( self._contact_address, FLAGS_EXPAND_BOTH_WAYS )
                gridbox.AddF( wx.StaticText( self._contact_panel, label = 'public key' ), FLAGS_MIXED )
                gridbox.AddF( self._public_key, FLAGS_EXPAND_BOTH_WAYS )
                
                self._contact_panel.AddF( gridbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
                
                vbox = wx.BoxSizer( wx.VERTICAL )
                
                vbox.AddF( self._contact_panel, FLAGS_EXPAND_BOTH_WAYS )
                
                self.SetSizer( vbox )
                
            
            InitialiseControls()
            
            InitialisePanel()
            
        
        def _GetInfo( self ):
            
            public_key = self._public_key.GetValue()
            
            if public_key == '': public_key = None
            
            name = self._name.GetValue()
            
            contact_address = self._contact_address.GetValue()
            
            try:
                
                if '@' in contact_address: ( contact_key, address ) = contact_address.split( '@' )
                else: address = contact_address
                
                ( host, port ) = address.split( ':' )
                
                try: port = int( port )
                except:
                    
                    port = 45871
                    
                    wx.MessageBox( 'Could not parse the port!' )
                    
                
            except:
                
                host = 'hostname'
                port = 45871
                
                wx.MessageBox( 'Could not parse the contact\'s address!' )
                
            
            return [ public_key, name, host, port ]
            
        
        def GetContact( self ):
            
            [ public_key, name, host, port ] = self._GetInfo()
            
            return ClientConstantsMessages.Contact( public_key, name, host, port )
            
        
        def GetOriginalName( self ): return self._contact.GetName()
        
        def HasChanges( self ):
            
            [ my_public_key, my_name, my_host, my_port ] = self._GetInfo()
            
            [ public_key, name, host, port ] = self._contact.GetInfo()
            
            if my_public_key != public_key: return True
            
            if my_name != name: return True
            
            if my_host != host: return True
            
            if my_port != port: return True
            
            return False
            
        
        def Update( self, contact ):
            
            ( public_key, name, host, port ) = contact.GetInfo()
            
            contact_key = contact.GetContactKey()
            
            self._name.SetValue( name )
            
            contact_address = host + ':' + str( port )
            
            if contact_key is not None: contact_address = contact_key.encode( 'hex' ) + '@' + contact_address
            
            self._contact_address.SetValue( contact_address )
            
            if public_key is None: public_key = ''
            
            self._public_key.SetValue( public_key )
            
        
    
class DialogManage4chanPass( Dialog ):
    
    def __init__( self, parent ):
        
        def InitialiseControls():
            
            self._token = wx.TextCtrl( self, value = token )
            self._pin = wx.TextCtrl( self, value = pin )
            
            self._status = wx.StaticText( self )
            
            self._SetStatus()
            
            self._reauthenticate = wx.Button( self, label = 'reauthenticate' )
            self._reauthenticate.Bind( wx.EVT_BUTTON, self.EventReauthenticate )
            
            self._ok = wx.Button( self, label='Ok' )
            self._ok.Bind( wx.EVT_BUTTON, self.EventOk )
            self._ok.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label='Cancel' )
            self._cancel.Bind( wx.EVT_BUTTON, self.EventCancel )        
            self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
            
        
        def InitialisePanel():
            
            gridbox = wx.FlexGridSizer( 0, 2 )
            
            gridbox.AddGrowableCol( 1, 1 )
            
            gridbox.AddF( wx.StaticText( self, label='token' ), FLAGS_MIXED )
            gridbox.AddF( self._token, FLAGS_EXPAND_BOTH_WAYS )
            gridbox.AddF( wx.StaticText( self, label='pin' ), FLAGS_MIXED )
            gridbox.AddF( self._pin, FLAGS_EXPAND_BOTH_WAYS )
            
            b_box = wx.BoxSizer( wx.HORIZONTAL )
            b_box.AddF( self._ok, FLAGS_MIXED )
            b_box.AddF( self._cancel, FLAGS_MIXED )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( gridbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
            vbox.AddF( self._status, FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._reauthenticate, FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( b_box, FLAGS_BUTTON_SIZERS )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            x = max( x, 240 )
            
            self.SetInitialSize( ( x, y ) )
            
        
        Dialog.__init__( self, parent, 'manage 4chan pass' )
        
        ( token, pin, self._timeout ) = wx.GetApp().Read( '4chan_pass' )
        
        InitialiseControls()
        
        InitialisePanel()
        
    
    def _SetStatus( self ):
        
        if self._timeout == 0: label = 'not authenticated'
        elif self._timeout < int( time.time() ): label = 'timed out'
        else: label = 'authenticated - ' + HC.ConvertTimestampToPrettyExpires( self._timeout )
        
        self._status.SetLabel( label )
        
    
    def EventCancel( self, event ): self.EndModal( wx.ID_CANCEL )
    
    def EventOk( self, event ):
        
        token = self._token.GetValue()
        pin = self._pin.GetValue()
        
        wx.GetApp().Write( '4chan_pass', token, pin, self._timeout )
        
        self.EndModal( wx.ID_OK )
        
    
    def EventReauthenticate( self, event ):
        
        try:
            
            token = self._token.GetValue()
            pin = self._pin.GetValue()
            
            form_fields = {}
            
            form_fields[ 'act' ] = 'do_login'
            form_fields[ 'id' ] = token
            form_fields[ 'pin' ] = pin
            form_fields[ 'long_login' ] = 'yes'
            
            ( ct, body ) = CC.GenerateMultipartFormDataCTAndBodyFromDict( form_fields )
            
            headers = {}
            headers[ 'Content-Type' ] = ct
            
            connection = CC.AdvancedHTTPConnection( url = 'https://sys.4chan.org/', accept_cookies = True )
            
            response = connection.request( 'POST', '/auth', headers = headers, body = body )
            
            self._timeout = int( time.time() ) + 365 * 24 * 3600
            
            wx.GetApp().Write( '4chan_pass', token, pin, self._timeout )
            
            self._SetStatus()
            
        except Exception as e:
            wx.MessageBox( traceback.format_exc() )
            wx.MessageBox( unicode( e ) )
        
    
class DialogManageImageboards( Dialog ):
    
    def __init__( self, parent ):
        
        def InitialiseControls():
            
            self._edit_log = []
            
            self._sites = ClientGUICommon.ListBook( self )
            
            sites = wx.GetApp().Read( 'imageboards' )
            
            for ( name, imageboards ) in sites:
                
                page_info = ( self._Panel, ( self._sites, imageboards ), {} )
                
                self._sites.AddPage( page_info, name )
                
            
            self._add = wx.Button( self, label='add' )
            self._add.Bind( wx.EVT_BUTTON, self.EventAdd )
            self._add.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._remove = wx.Button( self, label='remove' )
            self._remove.Bind( wx.EVT_BUTTON, self.EventRemove )
            self._remove.SetForegroundColour( ( 128, 0, 0 ) )
            
            self._export = wx.Button( self, label='export' )
            self._export.Bind( wx.EVT_BUTTON, self.EventExport )
            
            self._ok = wx.Button( self, label='ok' )
            self._ok.Bind( wx.EVT_BUTTON, self.EventOk )
            self._ok.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label='cancel' )
            self._cancel.Bind( wx.EVT_BUTTON, self.EventCancel )
            self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
            
        
        def InitialisePanel():
            
            add_remove_hbox = wx.BoxSizer( wx.HORIZONTAL )
            add_remove_hbox.AddF( self._add, FLAGS_MIXED )
            add_remove_hbox.AddF( self._remove, FLAGS_MIXED )
            add_remove_hbox.AddF( self._export, FLAGS_MIXED )
            
            ok_hbox = wx.BoxSizer( wx.HORIZONTAL )
            ok_hbox.AddF( self._ok, FLAGS_MIXED )
            ok_hbox.AddF( self._cancel, FLAGS_MIXED )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            vbox.AddF( self._sites, FLAGS_EXPAND_BOTH_WAYS )
            vbox.AddF( add_remove_hbox, FLAGS_SMALL_INDENT )
            vbox.AddF( ok_hbox, FLAGS_BUTTON_SIZERS )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( 980, y ) )
            
        
        Dialog.__init__( self, parent, 'manage imageboards' )
        
        InitialiseControls()
        
        InitialisePanel()
        
        self.SetDropTarget( ClientGUICommon.FileDropTarget( self.Import ) )
        
    
    def EventAdd( self, event ):
        
        with wx.TextEntryDialog( self, 'Enter new site\'s name' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                try:
                    
                    name = dlg.GetValue()
                    
                    if self._sites.NameExists( name ): raise Exception( 'That name is already in use!' )
                    
                    if name == '': raise Exception( 'Please enter a nickname for the service.' )
                    
                    self._edit_log.append( ( 'add', name ) )
                    
                    page = self._Panel( self._sites, [] )
                    
                    self._sites.AddPage( page, name, select = True )
                    
                except Exception as e:
                    
                    wx.MessageBox( unicode( e ) )
                    
                    self.EventAdd( event )
                    
                
            
        
    
    def EventCancel( self, event ): self.EndModal( wx.ID_CANCEL )
    
    def EventExport( self, event ):
        
        site_panel = self._sites.GetCurrentPage()
        
        if site_panel is not None:
            
            name = self._sites.GetCurrentName()
            
            imageboards = site_panel.GetImageboards()
            
            dict = { name : imageboards }
            
            with wx.FileDialog( self, 'select where to export site', defaultFile = 'site.yaml', style = wx.FD_SAVE ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    with open( dlg.GetPath(), 'wb' ) as f: f.write( yaml.safe_dump( dict ) )
                    
                
            
        
    
    def EventOk( self, event ):
        
        for ( name, page ) in self._sites.GetNameToPageDict().items():
            
            if page.HasChanges(): self._edit_log.append( ( 'edit', ( name, page.GetChanges() ) ) )
            
        
        try:
            
            if len( self._edit_log ) > 0: wx.GetApp().Write( 'update_imageboards', self._edit_log )
            
        except Exception as e: wx.MessageBox( 'Saving imageboards to DB raised this error: ' + unicode( e ) )
        
        self.EndModal( wx.ID_OK )
        
    
    def EventRemove( self, event ):
        
        site_panel = self._sites.GetCurrentPage()
        
        if site_panel is not None:
            
            name = self._sites.GetCurrentName()
            
            self._edit_log.append( ( 'delete', name ) )
            
            self._sites.DeleteCurrentPage()
            
        
    
    def Import( self, paths ):
        
        for path in paths:
            
            try:
                
                with open( path, 'rb' ) as f: file = f.read()
                
                thing = yaml.safe_load( file )
                
                if type( thing ) == dict:
                    
                    ( name, imageboards ) = thing.items()[0]
                    
                    if not self._sites.NameExists( name ):
                        
                        self._edit_log.append( ( 'add', name ) )
                        
                        page = self._Panel( self._sites, [] )
                        
                        self._sites.AddPage( page, name, select = True )
                        
                    
                    page = self._sites.GetNameToPageDict()[ name ]
                    
                    for imageboard in imageboards:
                        
                        if type( imageboard ) == CC.Imageboard: page.UpdateImageboard( imageboard )
                        
                    
                elif type( thing ) == CC.Imageboard:
                    
                    imageboard = thing
                    
                    page = self._sites.GetCurrentPage()
                    
                    page.UpdateImageboard( imageboard )
                    
                
            except:
                
                wx.MessageBox( traceback.format_exc() )
                
            
        
    
    class _Panel( wx.Panel ):
        
        def __init__( self, parent, imageboards ):
            
            wx.Panel.__init__( self, parent )
            
            def InitialiseControls():
                
                self._edit_log = []
                
                self._site_panel = ClientGUICommon.StaticBox( self, 'site' )
                
                self._imageboards = ClientGUICommon.ListBook( self._site_panel )
                
                for imageboard in imageboards:
                    
                    name = imageboard.GetName()
                    
                    page_info = ( self._Panel, ( self._imageboards, imageboard ), {} )
                    
                    self._imageboards.AddPage( page_info, name )
                    
                
                self._add = wx.Button( self._site_panel, label='add' )
                self._add.Bind( wx.EVT_BUTTON, self.EventAdd )
                self._add.SetForegroundColour( ( 0, 128, 0 ) )
                
                self._remove = wx.Button( self._site_panel, label='remove' )
                self._remove.Bind( wx.EVT_BUTTON, self.EventRemove )
                self._remove.SetForegroundColour( ( 128, 0, 0 ) )
                
                self._export = wx.Button( self._site_panel, label='export' )
                self._export.Bind( wx.EVT_BUTTON, self.EventExport )
                
            
            def InitialisePanel():
                
                add_remove_hbox = wx.BoxSizer( wx.HORIZONTAL )
                add_remove_hbox.AddF( self._add, FLAGS_MIXED )
                add_remove_hbox.AddF( self._remove, FLAGS_MIXED )
                add_remove_hbox.AddF( self._export, FLAGS_MIXED )
                
                self._site_panel.AddF( self._imageboards, FLAGS_EXPAND_BOTH_WAYS )
                self._site_panel.AddF( add_remove_hbox, FLAGS_SMALL_INDENT )
                
                vbox = wx.BoxSizer( wx.VERTICAL )
                
                vbox.AddF( self._site_panel, FLAGS_EXPAND_BOTH_WAYS )
                
                self.SetSizer( vbox )
                
                ( x, y ) = self.GetEffectiveMinSize()
                
                self.SetInitialSize( ( 980, y ) )
                
            
            InitialiseControls()
            
            InitialisePanel()
            
        
        def EventAdd( self, event ):
            
            with wx.TextEntryDialog( self, 'Enter new imageboard\'s name' ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    try:
                        
                        name = dlg.GetValue()
                        
                        if self._imageboards.NameExists( name ): raise Exception( 'That name is already in use!' )
                        
                        if name == '': raise Exception( 'Please enter a nickname for the service.' )
                        
                        imageboard = CC.Imageboard( name, '', 60, [], {} )
                        
                        self._edit_log.append( ( 'add', name ) )
                        
                        page = self._Panel( self._imageboards, imageboard )
                        
                        self._imageboards.AddPage( page, name, select = True )
                        
                    except Exception as e:
                        
                        wx.MessageBox( unicode( e ) )
                        
                        self.EventAdd( event )
                        
                    
                
            
        
        def EventExport( self, event ):
            
            imageboard_panel = self._imageboards.GetCurrentPage()
            
            if imageboard_panel is not None:
                
                imageboard = imageboard_panel.GetImageboard()
                
                with wx.FileDialog( self, 'select where to export imageboard', defaultFile = 'imageboard.yaml', style = wx.FD_SAVE ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        with open( dlg.GetPath(), 'wb' ) as f: f.write( yaml.safe_dump( imageboard ) )
                        
                    
                
            
        
        def EventRemove( self, event ):
            
            imageboard_panel = self._imageboards.GetCurrentPage()
            
            if imageboard_panel is not None:
                
                name = self._imageboards.GetCurrentName()
                
                self._edit_log.append( ( 'delete', name ) )
                
                self._imageboards.DeleteCurrentPage()
                
            
        
        def GetChanges( self ):
            
            for page in self._imageboards.GetNameToPageDict().values():
                
                if page.HasChanges(): self._edit_log.append( ( 'edit', page.GetImageboard() ) )
                
            
            return self._edit_log
            
        
        def GetImageboards( self ): return [ page.GetImageboard() for page in self._imageboards.GetNameToPageDict().values() ]
        
        def HasChanges( self ): return len( self._edit_log ) > 0 or True in ( page.HasChanges() for page in self._imageboards.GetNameToPageDict().values() )
        
        def UpdateImageboard( self, imageboard ):
            
            name = imageboard.GetName()
            
            if not self._imageboards.NameExists( name ):
                
                new_imageboard = CC.Imageboard( name, '', 60, [], {} )
                
                self._edit_log.append( ( 'add', name ) )
                
                page = self._Panel( self._imageboards, new_imageboard )
                
                self._imageboards.AddPage( page, name, select = True )
                
            
            page = self._imageboards.GetNameToPageDict()[ name ]
            
            page.Update( imageboard )
            
        
        class _Panel( wx.Panel ):
            
            def __init__( self, parent, imageboard ):
                
                wx.Panel.__init__( self, parent )
                
                self._imageboard = imageboard
                
                ( post_url, flood_time, form_fields, restrictions ) = self._imageboard.GetBoardInfo()
                
                def InitialiseControls():
                    
                    self._imageboard_panel = ClientGUICommon.StaticBox( self, 'imageboard' )
                    
                    #
                    
                    self._basic_info_panel = ClientGUICommon.StaticBox( self._imageboard_panel, 'basic info' )
                    
                    self._post_url = wx.TextCtrl( self._basic_info_panel, value = post_url )
                    
                    self._flood_time = wx.SpinCtrl( self._basic_info_panel, min = 5, max = 1200 )
                    self._flood_time.SetValue( flood_time )
                    
                    #
                    
                    self._form_fields_panel = ClientGUICommon.StaticBox( self._imageboard_panel, 'form fields' )
                    
                    self._form_fields = ClientGUICommon.SaneListCtrl( self._form_fields_panel, 350, [ ( 'name', 120 ), ( 'type', 120 ), ( 'default', -1 ), ( 'editable', 120 ) ] )
                    
                    for ( name, type, default, editable ) in form_fields:
                        
                        self._form_fields.Append( ( name, CC.field_string_lookup[ type ], str( default ), str( editable ) ), ( name, type, default, editable ) )
                        
                    
                    self._add = wx.Button( self._form_fields_panel, label='add' )
                    self._add.Bind( wx.EVT_BUTTON, self.EventAdd )
                    
                    self._edit = wx.Button( self._form_fields_panel, label='edit' )
                    self._edit.Bind( wx.EVT_BUTTON, self.EventEdit )
                    
                    self._delete = wx.Button( self._form_fields_panel, label='delete' )
                    self._delete.Bind( wx.EVT_BUTTON, self.EventDelete )
                    
                    #
                    
                    self._restrictions_panel = ClientGUICommon.StaticBox( self._imageboard_panel, 'restrictions' )
                    
                    if CC.RESTRICTION_MIN_RESOLUTION in restrictions: value = restrictions[ CC.RESTRICTION_MIN_RESOLUTION ]
                    else: value = None
                    
                    self._min_resolution = ClientGUICommon.NoneableSpinCtrl( self._restrictions_panel, 'min resolution', value, num_dimensions = 2 )
                    
                    if CC.RESTRICTION_MAX_RESOLUTION in restrictions: value = restrictions[ CC.RESTRICTION_MAX_RESOLUTION ]
                    else: value = None
                    
                    self._max_resolution = ClientGUICommon.NoneableSpinCtrl( self._restrictions_panel, 'max resolution', value, num_dimensions = 2 )
                    
                    if CC.RESTRICTION_MAX_FILE_SIZE in restrictions: value = restrictions[ CC.RESTRICTION_MAX_FILE_SIZE ]
                    else: value = None
                    
                    self._max_file_size = ClientGUICommon.NoneableSpinCtrl( self._restrictions_panel, 'max file size (KB)', value, multiplier = 1024 )
                    
                    self._allowed_mimes_panel = ClientGUICommon.StaticBox( self._restrictions_panel, 'allowed mimes' )
                    
                    self._mimes = wx.ListBox( self._allowed_mimes_panel )
                    
                    if CC.RESTRICTION_ALLOWED_MIMES in restrictions: mimes = restrictions[ CC.RESTRICTION_ALLOWED_MIMES ]
                    else: mimes = []
                    
                    for mime in mimes: self._mimes.Append( HC.mime_string_lookup[ mime ], mime )
                    
                    self._mime_choice = wx.Choice( self._allowed_mimes_panel )
                    
                    for mime in HC.ALLOWED_MIMES: self._mime_choice.Append( HC.mime_string_lookup[ mime ], mime )
                    
                    self._mime_choice.SetSelection( 0 )
                    
                    self._add_mime = wx.Button( self._allowed_mimes_panel, label = 'add' )
                    self._add_mime.Bind( wx.EVT_BUTTON, self.EventAddMime )
                    
                    self._remove_mime = wx.Button( self._allowed_mimes_panel, label = 'remove' )
                    self._remove_mime.Bind( wx.EVT_BUTTON, self.EventRemoveMime )
                    
                
                def InitialisePanel():
                    
                    self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
                    
                    #
                    
                    gridbox = wx.FlexGridSizer( 0, 2 )
                    
                    gridbox.AddGrowableCol( 1, 1 )
                    
                    gridbox.AddF( wx.StaticText( self._basic_info_panel, label='POST URL' ), FLAGS_MIXED )
                    gridbox.AddF( self._post_url, FLAGS_EXPAND_BOTH_WAYS )
                    gridbox.AddF( wx.StaticText( self._basic_info_panel, label='flood time' ), FLAGS_MIXED )
                    gridbox.AddF( self._flood_time, FLAGS_EXPAND_BOTH_WAYS )
                    
                    self._basic_info_panel.AddF( gridbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
                    
                    #
                    
                    h_b_box = wx.BoxSizer( wx.HORIZONTAL )
                    h_b_box.AddF( self._add, FLAGS_MIXED )
                    h_b_box.AddF( self._edit, FLAGS_MIXED )
                    h_b_box.AddF( self._delete, FLAGS_MIXED )
                    
                    self._form_fields_panel.AddF( self._form_fields, FLAGS_EXPAND_BOTH_WAYS )
                    self._form_fields_panel.AddF( h_b_box, FLAGS_BUTTON_SIZERS )
                    
                    #
                    
                    mime_buttons_box = wx.BoxSizer( wx.HORIZONTAL )
                    mime_buttons_box.AddF( self._mime_choice, FLAGS_MIXED )
                    mime_buttons_box.AddF( self._add_mime, FLAGS_MIXED )
                    mime_buttons_box.AddF( self._remove_mime, FLAGS_MIXED )
                    
                    self._allowed_mimes_panel.AddF( self._mimes, FLAGS_EXPAND_BOTH_WAYS )
                    self._allowed_mimes_panel.AddF( mime_buttons_box, FLAGS_EXPAND_SIZER_PERPENDICULAR )
                    
                    self._restrictions_panel.AddF( self._min_resolution, FLAGS_EXPAND_PERPENDICULAR )
                    self._restrictions_panel.AddF( self._max_resolution, FLAGS_EXPAND_PERPENDICULAR )
                    self._restrictions_panel.AddF( self._max_file_size, FLAGS_EXPAND_PERPENDICULAR )
                    self._restrictions_panel.AddF( self._allowed_mimes_panel, FLAGS_EXPAND_BOTH_WAYS )
                    
                    #
                    
                    self._imageboard_panel.AddF( self._basic_info_panel, FLAGS_EXPAND_PERPENDICULAR )
                    self._imageboard_panel.AddF( self._form_fields_panel, FLAGS_EXPAND_BOTH_WAYS )
                    self._imageboard_panel.AddF( self._restrictions_panel, FLAGS_EXPAND_PERPENDICULAR )
                    
                    vbox = wx.BoxSizer( wx.VERTICAL )
                    
                    vbox.AddF( self._imageboard_panel, FLAGS_EXPAND_BOTH_WAYS )
                    
                    self.SetSizer( vbox )
                    
                
                InitialiseControls()
                
                InitialisePanel()
                
            
            def _GetInfo( self ):
                
                imageboard_name = self._imageboard.GetName()
                
                post_url = self._post_url.GetValue()
                
                flood_time = self._flood_time.GetValue()
                
                # list instead of tumple cause of yaml comparisons
                form_fields = self._form_fields.GetClientData()
                
                restrictions = {}
                
                # yaml list again
                value = self._min_resolution.GetValue()
                if value is not None: restrictions[ CC.RESTRICTION_MIN_RESOLUTION ] = list( value )
                
                # yaml list again
                value = self._max_resolution.GetValue()
                if value is not None: restrictions[ CC.RESTRICTION_MAX_RESOLUTION ] = list( value )
                
                value = self._max_file_size.GetValue()
                if value is not None: restrictions[ CC.RESTRICTION_MAX_FILE_SIZE ] = value
                
                mimes = [ self._mimes.GetClientData( i ) for i in range( self._mimes.GetCount() ) ]
                
                if len( mimes ) > 0: restrictions[ CC.RESTRICTION_ALLOWED_MIMES ] = mimes
                
                return ( imageboard_name, post_url, flood_time, form_fields, restrictions )
                
            
            def EventAdd( self, event ):
                
                try:
                    
                    with DialogInputNewFormField( self ) as dlg:
                        
                        if dlg.ShowModal() == wx.ID_OK:
                            
                            ( name, type, default, editable ) = dlg.GetFormField()
                            
                            if name in [ form_field[0] for form_field in self._form_fields.GetClientData() ]:
                                
                                wx.MessageBox( 'There is already a field named ' + name )
                                
                                self.EventAdd( event )
                                
                                return
                                
                            
                            self._form_fields.Append( ( name, CC.field_string_lookup[ type ], str( default ), str( editable ) ), ( name, type, default, editable ) )
                            
                        
                    
                except Exception as e: wx.MessageBox( unicode( e ) )
                
            
            def EventAddMime( self, event ):
                
                selection = self._mime_choice.GetSelection()
                
                if selection != wx.NOT_FOUND:
                    
                    mime = self._mime_choice.GetClientData( selection )
                    
                    existing_mimes = [ self._mimes.GetClientData( i ) for i in range( self._mimes.GetCount() ) ]
                    
                    if mime not in existing_mimes: self._mimes.Append( HC.mime_string_lookup[ mime ], mime )
                    
                
            
            def EventDelete( self, event ): self._form_fields.RemoveAllSelected()
            
            def EventRemoveMime( self, event ):
                
                selection = self._mimes.GetSelection()
                
                if selection != wx.NOT_FOUND: self._mimes.Delete( selection )
                
            
            def EventEdit( self, event ):
                
                indices = self._form_fields.GetAllSelected()
                
                for index in indices:
                    
                    ( name, type, default, editable ) = self._form_fields.GetClientData( index )
                    
                    form_field = ( name, type, default, editable )
                    
                    try:
                        
                        with DialogInputNewFormField( self, form_field ) as dlg:
                            
                            if dlg.ShowModal() == wx.ID_OK:
                                
                                old_name = name
                                
                                ( name, type, default, editable ) = dlg.GetFormField()
                                
                                if old_name != name:
                                    
                                    if name in [ form_field[0] for form_field in self._form_fields.GetClientData() ]: raise Exception( 'You already have a form field called ' + name + '; delete or edit that one first' )
                                    
                                
                                self._form_fields.UpdateRow( index, ( name, CC.field_string_lookup[ type ], str( default ), str( editable ) ), ( name, type, default, editable ) )
                                
                            
                        
                    except Exception as e: wx.MessageBox( unicode( e ) )
                    
                
            
            def GetImageboard( self ):
                
                ( name, post_url, flood_time, form_fields, restrictions ) = self._GetInfo()
                
                return CC.Imageboard( name, post_url, flood_time, form_fields, restrictions )
                
            
            def HasChanges( self ):
                
                ( my_name, my_post_url, my_flood_time, my_form_fields, my_restrictions ) = self._GetInfo()
                
                ( post_url, flood_time, form_fields, restrictions ) = self._imageboard.GetBoardInfo()
                
                if post_url != my_post_url: return True
                
                if flood_time != my_flood_time: return True
                
                if set( [ tuple( item ) for item in form_fields ] ) != set( [ tuple( item ) for item in my_form_fields ] ): return True
                
                if restrictions != my_restrictions: return True
                
                return False
                
            
            def Update( self, imageboard ):
                
                ( post_url, flood_time, form_fields, restrictions ) = imageboard.GetBoardInfo()
                
                self._post_url.SetValue( post_url )
                self._flood_time.SetValue( flood_time )
                
                self._form_fields.ClearAll()
                
                self._form_fields.InsertColumn( 0, 'name', width = 120 )
                self._form_fields.InsertColumn( 1, 'type', width = 120 )
                self._form_fields.InsertColumn( 2, 'default' )
                self._form_fields.InsertColumn( 3, 'editable', width = 120 )
                
                self._form_fields.setResizeColumn( 3 ) # default
                
                for ( name, type, default, editable ) in form_fields:
                    
                    self._form_fields.Append( ( name, CC.field_string_lookup[ type ], str( default ), str( editable ) ), ( name, type, default, editable ) )
                    
                
                if CC.RESTRICTION_MIN_RESOLUTION in restrictions: value = restrictions[ CC.RESTRICTION_MIN_RESOLUTION ]
                else: value = None
                
                self._min_resolution.SetValue( value )
                
                if CC.RESTRICTION_MAX_RESOLUTION in restrictions: value = restrictions[ CC.RESTRICTION_MAX_RESOLUTION ]
                else: value = None
                
                self._max_resolution.SetValue( value )
                
                if CC.RESTRICTION_MAX_FILE_SIZE in restrictions: value = restrictions[ CC.RESTRICTION_MAX_FILE_SIZE ]
                else: value = None
                
                self._max_file_size.SetValue( value )
                
                self._mimes.Clear()
                
                if CC.RESTRICTION_ALLOWED_MIMES in restrictions: mimes = restrictions[ CC.RESTRICTION_ALLOWED_MIMES ]
                else: mimes = []
                
                for mime in mimes: self._mimes.Append( HC.mime_string_lookup[ mime ], mime )
                
            
        
    
class DialogManageOptionsFileRepository( Dialog ):
    
    def __init__( self, parent, service_identifier ):
        
        def InitialiseControls():
            
            self._file_repository_panel = ClientGUICommon.StaticBox( self, 'file repository' )
            
            self._max_monthly_data = ClientGUICommon.NoneableSpinCtrl( self._file_repository_panel, 'max monthly data (MB)', options[ 'max_monthly_data' ], multiplier = 1048576 )
            self._max_storage = ClientGUICommon.NoneableSpinCtrl( self._file_repository_panel, 'max storage (MB)', options[ 'max_monthly_data' ], multiplier = 1048576 )
            
            self._log_uploader_ips = wx.CheckBox( self._file_repository_panel, label='' )
            self._log_uploader_ips.SetValue( options[ 'log_uploader_ips' ] )
            
            self._message = wx.TextCtrl( self._file_repository_panel, value = options[ 'message' ] )
            
            self._save_button = wx.Button( self, label='Save' )
            self._save_button.Bind( wx.EVT_BUTTON, self.EventOK )
            self._save_button.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._close_button = wx.Button( self, id = wx.ID_CANCEL, label='Cancel' )
            self._close_button.Bind( wx.EVT_BUTTON, self.EventCancel )
            self._close_button.SetForegroundColour( ( 128, 0, 0 ) )
            
        
        def InitialisePanel():
            
            gridbox = wx.FlexGridSizer( 0, 2 )
            
            gridbox.AddGrowableCol( 1, 1 )
            
            gridbox.AddF( wx.StaticText( self._file_repository_panel, label='Log uploader ips?' ), FLAGS_MIXED )
            gridbox.AddF( self._log_uploader_ips, FLAGS_MIXED )
            gridbox.AddF( wx.StaticText( self._file_repository_panel, label='Message' ), FLAGS_MIXED )
            gridbox.AddF( self._message, FLAGS_MIXED )
            
            self._file_repository_panel.AddF( self._max_monthly_data, FLAGS_EXPAND_PERPENDICULAR )
            self._file_repository_panel.AddF( self._max_storage, FLAGS_EXPAND_PERPENDICULAR )
            self._file_repository_panel.AddF( gridbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            buttons = wx.BoxSizer( wx.HORIZONTAL )
            
            buttons.AddF( self._save_button, FLAGS_SMALL_INDENT )
            buttons.AddF( self._close_button, FLAGS_SMALL_INDENT )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( self._file_repository_panel, FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( buttons, FLAGS_BUTTON_SIZERS )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x + 80, y ) )
            
        
        Dialog.__init__( self, parent, service_identifier.GetName() + ' options' )
        
        self._service_identifier = service_identifier
        
        self._service = wx.GetApp().Read( 'service', service_identifier )
        
        connection = self._service.GetConnection()
        
        options = connection.Get( 'options' )
        
        InitialiseControls()
        
        InitialisePanel()
        
    
    def EventCancel( self, event ): self.EndModal( wx.ID_CANCEL )
    
    def EventOK( self, event ):
        
        options = {}
        
        options[ 'max_monthly_data' ] = self._max_monthly_data.GetValue()
        
        options[ 'max_storage' ] = self._max_storage.GetValue()
        
        options[ 'log_uploader_ips' ] = self._log_uploader_ips.GetValue()
        
        options[ 'message' ] = self._message.GetValue()
        
        try:
            
            connection = self._service.GetConnection()
            
            connection.Post( 'options', options = options )
            
        except Exception as e: wx.MessageBox( 'Something went wrong when trying to send the options to the file repository: ' + unicode( e ) )
        
        self.EndModal( wx.ID_OK )
        
    
class DialogManageOptionsLocal( Dialog ):
    
    def __init__( self, parent ):
        
        def InitialiseControls():
            
            self._listbook = ClientGUICommon.ListBook( self )
            
            # files and memory
            
            self._file_page = wx.Panel( self._listbook )
            self._file_page.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
            
            self._export_location = wx.DirPickerCtrl( self._file_page, style = wx.DIRP_USE_TEXTCTRL )
            
            if self._options[ 'export_path' ] is not None: self._export_location.SetPath( HC.ConvertPortablePathToAbsPath( self._options[ 'export_path' ] ) )
            
            self._exclude_deleted_files = wx.CheckBox( self._file_page, label='' )
            self._exclude_deleted_files.SetValue( self._options[ 'exclude_deleted_files' ] )
            
            self._thumbnail_cache_size = wx.SpinCtrl( self._file_page, min = 10, max = 3000 )
            self._thumbnail_cache_size.SetValue( int( self._options[ 'thumbnail_cache_size' ] / 1048576 ) )
            self._thumbnail_cache_size.Bind( wx.EVT_SPINCTRL, self.EventThumbnailsUpdate )
            
            self._estimated_number_thumbnails = wx.StaticText( self._file_page, label = '' )
            
            self._preview_cache_size = wx.SpinCtrl( self._file_page, min = 20, max = 3000 )
            self._preview_cache_size.SetValue( int( self._options[ 'preview_cache_size' ] / 1048576 ) )
            self._preview_cache_size.Bind( wx.EVT_SPINCTRL, self.EventPreviewsUpdate )
            
            self._estimated_number_previews = wx.StaticText( self._file_page, label = '' )
            
            self._fullscreen_cache_size = wx.SpinCtrl( self._file_page, min = 100, max = 3000 )
            self._fullscreen_cache_size.SetValue( int( self._options[ 'fullscreen_cache_size' ] / 1048576 ) )
            self._fullscreen_cache_size.Bind( wx.EVT_SPINCTRL, self.EventFullscreensUpdate )
            
            self._estimated_number_fullscreens = wx.StaticText( self._file_page, label = '' )
            
            ( thumbnail_width, thumbnail_height ) = self._options[ 'thumbnail_dimensions' ]
            
            self._thumbnail_width = wx.SpinCtrl( self._file_page, min=20, max=200 )
            self._thumbnail_width.SetValue( thumbnail_width )
            self._thumbnail_width.Bind( wx.EVT_SPINCTRL, self.EventThumbnailsUpdate )
            
            self._thumbnail_height = wx.SpinCtrl( self._file_page, min=20, max=200 )
            self._thumbnail_height.SetValue( thumbnail_height )
            self._thumbnail_height.Bind( wx.EVT_SPINCTRL, self.EventThumbnailsUpdate )
            
            self._num_autocomplete_chars = wx.SpinCtrl( self._file_page, min = 1, max = 100 )
            self._num_autocomplete_chars.SetValue( self._options[ 'num_autocomplete_chars' ] )
            self._num_autocomplete_chars.SetToolTipString( 'how many characters you enter before the gui fetches autocomplete results from the db' + os.linesep + 'increase this if you find autocomplete results are slow' )
            
            self._listbook.AddPage( self._file_page, 'files and memory' )
            
            # gui
            
            self._gui_page = wx.Panel( self._listbook )
            self._gui_page.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
            
            self._gui_capitalisation = wx.CheckBox( self._gui_page )
            self._gui_capitalisation.SetValue( self._options[ 'gui_capitalisation' ] )
            
            self._gui_show_all_tags_in_autocomplete = wx.CheckBox( self._gui_page )
            self._gui_show_all_tags_in_autocomplete.SetValue( self._options[ 'show_all_tags_in_autocomplete' ] )
            
            self._default_tag_sort = wx.Choice( self._gui_page )
            
            self._default_tag_sort.Append( 'lexicographic (a-z)', CC.SORT_BY_LEXICOGRAPHIC_ASC )
            self._default_tag_sort.Append( 'lexicographic (z-a)', CC.SORT_BY_LEXICOGRAPHIC_DESC )
            self._default_tag_sort.Append( 'incidence (desc)', CC.SORT_BY_INCIDENCE_DESC )
            self._default_tag_sort.Append( 'incidence (asc)', CC.SORT_BY_INCIDENCE_ASC )
            
            if self._options[ 'default_tag_sort' ] == CC.SORT_BY_LEXICOGRAPHIC_ASC: self._default_tag_sort.Select( 0 )
            elif self._options[ 'default_tag_sort' ] == CC.SORT_BY_LEXICOGRAPHIC_DESC: self._default_tag_sort.Select( 1 )
            elif self._options[ 'default_tag_sort' ] == CC.SORT_BY_INCIDENCE_DESC: self._default_tag_sort.Select( 2 )
            elif self._options[ 'default_tag_sort' ] == CC.SORT_BY_INCIDENCE_ASC: self._default_tag_sort.Select( 3 )
            
            service_identifiers = wx.GetApp().Read( 'service_identifiers', ( HC.LOCAL_TAG, HC.TAG_REPOSITORY ) )
            
            self._default_tag_repository = wx.Choice( self._gui_page )
            for service_identifier in service_identifiers: self._default_tag_repository.Append( service_identifier.GetName(), service_identifier )
            
            self._default_tag_repository.SetStringSelection( self._options[ 'default_tag_repository' ].GetName() )
            
            self._fullscreen_borderless = wx.CheckBox( self._gui_page )
            self._fullscreen_borderless.SetValue( self._options[ 'fullscreen_borderless' ] )
            
            self._listbook.AddPage( self._gui_page, 'gui' )
            
            # default file system predicates
            
            system_predicates = self._options[ 'file_system_predicates' ]
            
            self._file_system_predicates_page = wx.Panel( self._listbook )
            self._file_system_predicates_page.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
            
            ( sign, years, months, days ) = system_predicates[ 'age' ]
            
            self._file_system_predicate_age_sign = wx.Choice( self._file_system_predicates_page, choices=[ '<', u'\u2248', '>' ] )
            self._file_system_predicate_age_sign.SetSelection( sign )
            
            self._file_system_predicate_age_years = wx.SpinCtrl( self._file_system_predicates_page, max = 30 )
            self._file_system_predicate_age_years.SetValue( years )
            self._file_system_predicate_age_months = wx.SpinCtrl( self._file_system_predicates_page, max = 60 )
            self._file_system_predicate_age_months.SetValue( months )
            self._file_system_predicate_age_days = wx.SpinCtrl( self._file_system_predicates_page, max = 90 )
            self._file_system_predicate_age_days.SetValue( days )
            
            ( sign, s, ms ) = system_predicates[ 'duration' ]
            
            self._file_system_predicate_duration_sign = wx.Choice( self._file_system_predicates_page, choices=[ '<', u'\u2248', '=', '>' ] )
            self._file_system_predicate_duration_sign.SetSelection( sign )
            
            self._file_system_predicate_duration_s = wx.SpinCtrl( self._file_system_predicates_page, max = 3599 )
            self._file_system_predicate_duration_s.SetValue( s )
            self._file_system_predicate_duration_ms = wx.SpinCtrl( self._file_system_predicates_page, max = 999 )
            self._file_system_predicate_duration_ms.SetValue( ms )
            
            ( sign, height ) = system_predicates[ 'height' ]
            
            self._file_system_predicate_height_sign = wx.Choice( self._file_system_predicates_page, choices=[ '<', u'\u2248', '=', '>' ] )
            self._file_system_predicate_height_sign.SetSelection( sign )
            
            self._file_system_predicate_height = wx.SpinCtrl( self._file_system_predicates_page, max = 200000 )
            self._file_system_predicate_height.SetValue( height )
            
            limit = system_predicates[ 'limit' ]
            
            self._file_system_predicate_limit = wx.SpinCtrl( self._file_system_predicates_page, max = 1000000 )
            self._file_system_predicate_limit.SetValue( limit )
            
            ( media, type ) = system_predicates[ 'mime' ]
            
            self._file_system_predicate_mime_media = wx.Choice( self._file_system_predicates_page, choices=[ 'image', 'application' ] )
            self._file_system_predicate_mime_media.SetSelection( media )
            self._file_system_predicate_mime_media.Bind( wx.EVT_CHOICE, self.EventFileSystemPredicateMime )
            
            self._file_system_predicate_mime_type = wx.Choice( self._file_system_predicates_page, choices=[], size = ( 120, -1 ) )
            
            self.EventFileSystemPredicateMime( None )
            
            self._file_system_predicate_mime_type.SetSelection( type )
            
            ( sign, num_tags ) = system_predicates[ 'num_tags' ]
            
            self._file_system_predicate_num_tags_sign = wx.Choice( self._file_system_predicates_page, choices=[ '<', '=', '>' ] )
            self._file_system_predicate_num_tags_sign.SetSelection( sign )
            
            self._file_system_predicate_num_tags = wx.SpinCtrl( self._file_system_predicates_page, max = 2000 )
            self._file_system_predicate_num_tags.SetValue( num_tags )
            
            ( sign, value ) = system_predicates[ 'local_rating_numerical' ]
            
            self._file_system_predicate_local_rating_numerical_sign = wx.Choice( self._file_system_predicates_page, choices=[ '>', '<', '=', u'\u2248', '=rated', '=not rated', '=uncertain' ] )
            self._file_system_predicate_local_rating_numerical_sign.SetSelection( sign )
            
            self._file_system_predicate_local_rating_numerical_value = wx.SpinCtrl( self._file_system_predicates_page, min = 0, max = 50000 )
            self._file_system_predicate_local_rating_numerical_value.SetValue( value )
            
            value = system_predicates[ 'local_rating_like' ]
            
            self._file_system_predicate_local_rating_like_value = wx.Choice( self._file_system_predicates_page, choices=[ 'like', 'dislike', 'rated', 'not rated' ] )
            self._file_system_predicate_local_rating_like_value.SetSelection( value )
            
            ( sign, width, height ) = system_predicates[ 'ratio' ]
            
            self._file_system_predicate_ratio_sign = wx.Choice( self._file_system_predicates_page, choices=[ '=', u'\u2248' ] )
            self._file_system_predicate_ratio_sign.SetSelection( sign )
            
            self._file_system_predicate_ratio_width = wx.SpinCtrl( self._file_system_predicates_page, max = 50000 )
            self._file_system_predicate_ratio_width.SetValue( width )
            self._file_system_predicate_ratio_height = wx.SpinCtrl( self._file_system_predicates_page, max = 50000 )
            self._file_system_predicate_ratio_height.SetValue( height )
            
            ( sign, size, unit ) = system_predicates[ 'size' ]
            
            self._file_system_predicate_size_sign = wx.Choice( self._file_system_predicates_page, choices=[ '<', u'\u2248', '=', '>' ] )
            self._file_system_predicate_size_sign.SetSelection( sign )
            
            self._file_system_predicate_size = wx.SpinCtrl( self._file_system_predicates_page, max = 1048576 )
            self._file_system_predicate_size.SetValue( size )
            
            self._file_system_predicate_size_unit = wx.Choice( self._file_system_predicates_page, choices=[ 'B', 'KB', 'MB', 'GB' ] )
            self._file_system_predicate_size_unit.SetSelection( unit )
            
            ( sign, width ) = system_predicates[ 'width' ]
            
            self._file_system_predicate_width_sign = wx.Choice( self._file_system_predicates_page, choices=[ '<', u'\u2248', '=', '>' ] )
            self._file_system_predicate_width_sign.SetSelection( sign )
            
            self._file_system_predicate_width = wx.SpinCtrl( self._file_system_predicates_page, max = 200000 )
            self._file_system_predicate_width.SetValue( width )
            
            ( sign, num_words ) = system_predicates[ 'num_words' ]
            
            self._file_system_predicate_num_words_sign = wx.Choice( self._file_system_predicates_page, choices=[ '<', u'\u2248', '=', '>' ] )
            self._file_system_predicate_num_words_sign.SetSelection( sign )
            
            self._file_system_predicate_num_words = wx.SpinCtrl( self._file_system_predicates_page, max = 1000000 )
            self._file_system_predicate_num_words.SetValue( num_words )
            
            self._listbook.AddPage( self._file_system_predicates_page, 'default file system predicates' )
            
            # colours
            
            self._colour_page = wx.Panel( self._listbook )
            self._colour_page.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
            
            self._namespace_colours = ClientGUICommon.TagsBoxOptions( self._colour_page, self._options[ 'namespace_colours' ] )
            
            self._edit_namespace_colour = wx.Button( self._colour_page, label = 'edit selected' )
            self._edit_namespace_colour.Bind( wx.EVT_BUTTON, self.EventEditNamespaceColour )
            
            self._new_namespace_colour = wx.TextCtrl( self._colour_page, style = wx.TE_PROCESS_ENTER )
            self._new_namespace_colour.Bind( wx.EVT_KEY_DOWN, self.EventKeyDownNamespace )
            
            self._listbook.AddPage( self._colour_page, 'colours' )
            
            # sort/collect
            
            self._sort_by_page = wx.Panel( self._listbook )
            self._sort_by_page.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
            
            self._default_sort = ClientGUICommon.ChoiceSort( self._sort_by_page, sort_by = self._options[ 'sort_by' ] )
            
            self._default_collect = ClientGUICommon.CheckboxCollect( self._sort_by_page )
            
            self._sort_by = wx.ListBox( self._sort_by_page )
            self._sort_by.Bind( wx.EVT_LEFT_DCLICK, self.EventRemoveSortBy )
            for ( sort_by_type, sort_by ) in self._options[ 'sort_by' ]: self._sort_by.Append( '-'.join( sort_by ), sort_by )
            
            self._new_sort_by = wx.TextCtrl( self._sort_by_page, style = wx.TE_PROCESS_ENTER )
            self._new_sort_by.Bind( wx.EVT_KEY_DOWN, self.EventKeyDownSortBy )
            
            self._listbook.AddPage( self._sort_by_page, 'sort/collect' )
            
            # shortcuts
            
            self._shortcuts_page = wx.Panel( self._listbook )
            self._shortcuts_page.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
            
            self._shortcuts = ClientGUICommon.SaneListCtrl( self._shortcuts_page, 480, [ ( 'modifier', 120 ), ( 'key', 120 ), ( 'action', -1 ) ] )
            
            for ( modifier, key_dict ) in self._options[ 'shortcuts' ].items():
                
                for ( key, action ) in key_dict.items():
                    
                    ( pretty_modifier, pretty_key, pretty_action ) = HC.ConvertShortcutToPrettyShortcut( modifier, key, action )
                    
                    self._shortcuts.Append( ( pretty_modifier, pretty_key, pretty_action ), ( modifier, key, action ) )
                    
                
            
            self._SortListCtrl()
            
            self._shortcuts_add = wx.Button( self._shortcuts_page, label = 'add' )
            self._shortcuts_add.Bind( wx.EVT_BUTTON, self.EventShortcutsAdd )
            
            self._shortcuts_edit = wx.Button( self._shortcuts_page, label = 'edit' )
            self._shortcuts_edit.Bind( wx.EVT_BUTTON, self.EventShortcutsEdit )
            
            self._shortcuts_delete = wx.Button( self._shortcuts_page, label = 'delete' )
            self._shortcuts_delete.Bind( wx.EVT_BUTTON, self.EventShortcutsDelete )
            
            self._listbook.AddPage( self._shortcuts_page, 'shortcuts' )
            
            #
            
            self._save_button = wx.Button( self, label='Save' )
            self._save_button.Bind( wx.EVT_BUTTON, self.EventOK )
            self._save_button.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._close_button = wx.Button( self, id = wx.ID_CANCEL, label='Cancel' )
            self._close_button.Bind( wx.EVT_BUTTON, self.EventCancel )
            self._close_button.SetForegroundColour( ( 128, 0, 0 ) )
            
        
        def InitialisePanel():
            
            thumbnails_sizer = wx.BoxSizer( wx.HORIZONTAL )
            
            thumbnails_sizer.AddF( self._thumbnail_cache_size, FLAGS_MIXED )
            thumbnails_sizer.AddF( self._estimated_number_thumbnails, FLAGS_MIXED )
            
            previews_sizer = wx.BoxSizer( wx.HORIZONTAL )
            
            previews_sizer.AddF( self._preview_cache_size, FLAGS_MIXED )
            previews_sizer.AddF( self._estimated_number_previews, FLAGS_MIXED )
            
            fullscreens_sizer = wx.BoxSizer( wx.HORIZONTAL )
            
            fullscreens_sizer.AddF( self._fullscreen_cache_size, FLAGS_MIXED )
            fullscreens_sizer.AddF( self._estimated_number_fullscreens, FLAGS_MIXED )
            
            gridbox = wx.FlexGridSizer( 0, 2 )
            
            gridbox.AddGrowableCol( 1, 1 )
            
            gridbox.AddF( wx.StaticText( self._file_page, label='Default export directory: ' ), FLAGS_MIXED )
            gridbox.AddF( self._export_location, FLAGS_EXPAND_BOTH_WAYS )
            gridbox.AddF( wx.StaticText( self._file_page, label='Exclude deleted files from new imports and remote searches: ' ), FLAGS_MIXED )
            gridbox.AddF( self._exclude_deleted_files, FLAGS_MIXED )
            gridbox.AddF( wx.StaticText( self._file_page, label='MB memory reserved for thumbnail cache: ' ), FLAGS_MIXED )
            gridbox.AddF( thumbnails_sizer, FLAGS_NONE )
            gridbox.AddF( wx.StaticText( self._file_page, label='MB memory reserved for preview cache: ' ), FLAGS_MIXED )
            gridbox.AddF( previews_sizer, FLAGS_NONE )
            gridbox.AddF( wx.StaticText( self._file_page, label='MB memory reserved for fullscreen cache: ' ), FLAGS_MIXED )
            gridbox.AddF( fullscreens_sizer, FLAGS_NONE )
            gridbox.AddF( wx.StaticText( self._file_page, label='Thumbnail width: ' ), FLAGS_MIXED )
            gridbox.AddF( self._thumbnail_width, FLAGS_MIXED )
            gridbox.AddF( wx.StaticText( self._file_page, label='Thumbnail height: ' ), FLAGS_MIXED )
            gridbox.AddF( self._thumbnail_height, FLAGS_MIXED )
            gridbox.AddF( wx.StaticText( self._file_page, label='Autocomplete character threshold: ' ), FLAGS_MIXED )
            gridbox.AddF( self._num_autocomplete_chars, FLAGS_MIXED )
            
            self._file_page.SetSizer( gridbox )
            
            #
            
            gridbox = wx.FlexGridSizer( 0, 2 )
            
            gridbox.AddGrowableCol( 1, 1 )
            
            gridbox.AddF( wx.StaticText( self._gui_page, label = 'Default tag service in manage tag dialogs:' ), FLAGS_MIXED )
            gridbox.AddF( self._default_tag_repository, FLAGS_MIXED )
            
            gridbox.AddF( wx.StaticText( self._gui_page, label = 'Default tag sort on management panel:' ), FLAGS_MIXED )
            gridbox.AddF( self._default_tag_sort, FLAGS_MIXED )
            
            gridbox.AddF( wx.StaticText( self._gui_page, label='Capitalise gui: ' ), FLAGS_MIXED )
            gridbox.AddF( self._gui_capitalisation, FLAGS_MIXED )
            
            gridbox.AddF( wx.StaticText( self._gui_page, label='By default, search non-local tags in write-autocomplete: ' ), FLAGS_MIXED )
            gridbox.AddF( self._gui_show_all_tags_in_autocomplete, FLAGS_MIXED )
            
            gridbox.AddF( wx.StaticText( self._gui_page, label='By default, show fullscreen without borders: ' ), FLAGS_MIXED )
            gridbox.AddF( self._fullscreen_borderless, FLAGS_MIXED )
            
            self._gui_page.SetSizer( gridbox )
            
            #
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( wx.StaticText( self._file_system_predicates_page, label='system:age' ), FLAGS_MIXED )
            hbox.AddF( self._file_system_predicate_age_sign, FLAGS_MIXED )
            hbox.AddF( self._file_system_predicate_age_years, FLAGS_MIXED )
            hbox.AddF( wx.StaticText( self._file_system_predicates_page, label='years' ), FLAGS_MIXED )
            hbox.AddF( self._file_system_predicate_age_months, FLAGS_MIXED )
            hbox.AddF( wx.StaticText( self._file_system_predicates_page, label='months' ), FLAGS_MIXED )
            hbox.AddF( self._file_system_predicate_age_days, FLAGS_MIXED )
            hbox.AddF( wx.StaticText( self._file_system_predicates_page, label='days' ), FLAGS_MIXED )
            
            vbox.AddF( hbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( wx.StaticText( self._file_system_predicates_page, label='system:duration' ), FLAGS_MIXED )
            hbox.AddF( self._file_system_predicate_duration_sign, FLAGS_MIXED )
            hbox.AddF( self._file_system_predicate_duration_s, FLAGS_MIXED )
            hbox.AddF( wx.StaticText( self._file_system_predicates_page, label='s' ), FLAGS_MIXED )
            hbox.AddF( self._file_system_predicate_duration_ms, FLAGS_MIXED )
            hbox.AddF( wx.StaticText( self._file_system_predicates_page, label='ms' ), FLAGS_MIXED )
            
            vbox.AddF( hbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( wx.StaticText( self._file_system_predicates_page, label='system:height' ), FLAGS_MIXED )
            hbox.AddF( self._file_system_predicate_height_sign, FLAGS_MIXED )
            hbox.AddF( self._file_system_predicate_height, FLAGS_MIXED )
            
            vbox.AddF( hbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( wx.StaticText( self._file_system_predicates_page, label='system:limit=' ), FLAGS_MIXED )
            hbox.AddF( self._file_system_predicate_limit, FLAGS_MIXED )
            
            vbox.AddF( hbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( wx.StaticText( self._file_system_predicates_page, label='system:mime' ), FLAGS_MIXED )
            hbox.AddF( self._file_system_predicate_mime_media, FLAGS_MIXED )
            hbox.AddF( wx.StaticText( self._file_system_predicates_page, label='/' ), FLAGS_MIXED )
            hbox.AddF( self._file_system_predicate_mime_type, FLAGS_MIXED )
            
            vbox.AddF( hbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( wx.StaticText( self._file_system_predicates_page, label='system:num_tags' ), FLAGS_MIXED )
            hbox.AddF( self._file_system_predicate_num_tags_sign, FLAGS_MIXED )
            hbox.AddF( self._file_system_predicate_num_tags, FLAGS_MIXED )
            
            vbox.AddF( hbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( wx.StaticText( self._file_system_predicates_page, label='system:local_rating_like' ), FLAGS_MIXED )
            hbox.AddF( self._file_system_predicate_local_rating_like_value, FLAGS_MIXED )
            
            vbox.AddF( hbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( wx.StaticText( self._file_system_predicates_page, label='system:local_rating_numerical' ), FLAGS_MIXED )
            hbox.AddF( self._file_system_predicate_local_rating_numerical_sign, FLAGS_MIXED )
            hbox.AddF( self._file_system_predicate_local_rating_numerical_value, FLAGS_MIXED )
            
            vbox.AddF( hbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( wx.StaticText( self._file_system_predicates_page, label='system:ratio' ), FLAGS_MIXED )
            hbox.AddF( self._file_system_predicate_ratio_sign, FLAGS_MIXED )
            hbox.AddF( self._file_system_predicate_ratio_width, FLAGS_MIXED )
            hbox.AddF( wx.StaticText( self._file_system_predicates_page, label=':' ), FLAGS_MIXED )
            hbox.AddF( self._file_system_predicate_ratio_height, FLAGS_MIXED )
            
            vbox.AddF( hbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( wx.StaticText( self._file_system_predicates_page, label='system:size' ), FLAGS_MIXED )
            hbox.AddF( self._file_system_predicate_size_sign, FLAGS_MIXED )
            hbox.AddF( self._file_system_predicate_size, FLAGS_MIXED )
            hbox.AddF( self._file_system_predicate_size_unit, FLAGS_MIXED )
            
            vbox.AddF( hbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( wx.StaticText( self._file_system_predicates_page, label='system:width' ), FLAGS_MIXED )
            hbox.AddF( self._file_system_predicate_width_sign, FLAGS_MIXED )
            hbox.AddF( self._file_system_predicate_width, FLAGS_MIXED )
            
            vbox.AddF( hbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( wx.StaticText( self._file_system_predicates_page, label='system:num_words' ), FLAGS_MIXED )
            hbox.AddF( self._file_system_predicate_num_words_sign, FLAGS_MIXED )
            hbox.AddF( self._file_system_predicate_num_words, FLAGS_MIXED )
            
            vbox.AddF( hbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            self._file_system_predicates_page.SetSizer( vbox )
            
            #
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( self._namespace_colours, FLAGS_EXPAND_BOTH_WAYS )
            vbox.AddF( self._new_namespace_colour, FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._edit_namespace_colour, FLAGS_EXPAND_PERPENDICULAR )
            
            self._colour_page.SetSizer( vbox )
            
            #
            
            gridbox = wx.FlexGridSizer( 0, 2 )
            
            gridbox.AddGrowableCol( 1, 1 )
            
            gridbox.AddF( wx.StaticText( self._sort_by_page, label='Default sort: ' ), FLAGS_MIXED )
            gridbox.AddF( self._default_sort, FLAGS_EXPAND_BOTH_WAYS )
            gridbox.AddF( wx.StaticText( self._sort_by_page, label='Default collect: ' ), FLAGS_MIXED )
            gridbox.AddF( self._default_collect, FLAGS_EXPAND_BOTH_WAYS )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( gridbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
            vbox.AddF( self._sort_by, FLAGS_EXPAND_BOTH_WAYS )
            vbox.AddF( self._new_sort_by, FLAGS_EXPAND_PERPENDICULAR )
            
            self._sort_by_page.SetSizer( vbox )
            
            #
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( wx.StaticText( self._shortcuts_page, label = 'These shortcuts are global to the main gui! You probably want to stick to function keys or ctrl + something!' ), FLAGS_MIXED )
            vbox.AddF( self._shortcuts, FLAGS_EXPAND_BOTH_WAYS )
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( self._shortcuts_add, FLAGS_BUTTON_SIZERS )
            hbox.AddF( self._shortcuts_edit, FLAGS_BUTTON_SIZERS )
            hbox.AddF( self._shortcuts_delete, FLAGS_BUTTON_SIZERS )
            
            vbox.AddF( hbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            self._shortcuts_page.SetSizer( vbox )
            
            #
            
            buttons = wx.BoxSizer( wx.HORIZONTAL )
            
            buttons.AddF( self._save_button, FLAGS_SMALL_INDENT )
            buttons.AddF( self._close_button, FLAGS_SMALL_INDENT )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( self._listbook, FLAGS_EXPAND_BOTH_WAYS )
            vbox.AddF( buttons, FLAGS_BUTTON_SIZERS )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            if x < 800: x = 800
            if y < 600: y = 600
            
            self.SetInitialSize( ( x, y ) )
            
        
        Dialog.__init__( self, parent, 'hydrus client options' )
        
        InitialiseControls()
        
        InitialisePanel()
        
        self.EventFullscreensUpdate( None )
        self.EventPreviewsUpdate( None )
        self.EventThumbnailsUpdate( None )
        
        wx.CallAfter( self._file_page.Layout ) # draws the static texts correctly
        
    
    def _SortListCtrl( self ): self._shortcuts.SortListItems( 2 )
    
    def EventCancel( self, event ): self.EndModal( wx.ID_CANCEL )
    
    def EventEditNamespaceColour( self, event ):
        
        result = self._namespace_colours.GetSelectedNamespaceColour()
        
        if result is not None:
            
            ( namespace, colour ) = result
            
            colour_data = wx.ColourData()
            
            colour_data.SetColour( colour )
            colour_data.SetChooseFull( True )
            
            with wx.ColourDialog( self, data = colour_data ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    colour_data = dlg.GetColourData()
                    
                    colour = colour_data.GetColour()
                    
                    self._namespace_colours.SetNamespaceColour( namespace, colour )
                    
                
            
        
    
    def EventFileSystemPredicateMime( self, event ):
        
        media = self._file_system_predicate_mime_media.GetStringSelection()
        
        self._file_system_predicate_mime_type.Clear()
        
        if media == 'image':
            
            self._file_system_predicate_mime_type.Append( 'any', HC.IMAGES )
            self._file_system_predicate_mime_type.Append( 'jpeg', HC.IMAGE_JPEG )
            self._file_system_predicate_mime_type.Append( 'png', HC.IMAGE_PNG )
            self._file_system_predicate_mime_type.Append( 'gif', HC.IMAGE_GIF )
            
        elif media == 'application':
            
            self._file_system_predicate_mime_type.Append( 'any', HC.APPLICATIONS )
            self._file_system_predicate_mime_type.Append( 'pdf', HC.APPLICATION_PDF )
            self._file_system_predicate_mime_type.Append( 'x-shockwave-flash', HC.APPLICATION_FLASH )
            
        elif media == 'video':
            
            self._file_system_predicate_mime_type.Append( 'x-flv', HC.VIDEO_FLV )
            
        
        self._file_system_predicate_mime_type.SetSelection( 0 )
        
    
    def EventFullscreensUpdate( self, event ):
        
        ( width, height ) = wx.GetDisplaySize()
        
        estimated_bytes_per_fullscreen = 3 * width * height
        
        self._estimated_number_fullscreens.SetLabel( '(about ' + HC.ConvertIntToPrettyString( ( self._fullscreen_cache_size.GetValue() * 1048576 ) / estimated_bytes_per_fullscreen ) + '-' + HC.ConvertIntToPrettyString( ( self._fullscreen_cache_size.GetValue() * 1048576 ) / ( estimated_bytes_per_fullscreen / 4 ) ) + ' images)' )
        
    
    def EventKeyDownNamespace( self, event ):
        
        if event.KeyCode in ( wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER ):
            
            namespace = self._new_namespace_colour.GetValue()
            
            if namespace != '':
                
                self._namespace_colours.SetNamespaceColour( namespace, wx.Colour( random.randint( 0, 255 ), random.randint( 0, 255 ), random.randint( 0, 255 ) ) )
                
                self._new_namespace_colour.SetValue( '' )
                
            
        else: event.Skip()
        
    
    def EventKeyDownSortBy( self, event ):
        
        if event.KeyCode in ( wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER ):
            
            sort_by_string = self._new_sort_by.GetValue()
            
            if sort_by_string != '':
                
                try: sort_by = sort_by_string.split( '-' )
                except:
                    
                    wx.MessageBox( 'Could not parse that sort by string!' )
                    
                    return
                    
                
                self._sort_by.Append( sort_by_string, sort_by )
                
                self._new_sort_by.SetValue( '' )
                
            
        else: event.Skip()
        
    
    def EventOK( self, event ):
        
        self._options[ 'gui_capitalisation' ] = self._gui_capitalisation.GetValue()
        self._options[ 'show_all_tags_in_autocomplete' ] = self._gui_show_all_tags_in_autocomplete.GetValue()
        self._options[ 'fullscreen_borderless' ] = self._fullscreen_borderless.GetValue()
        
        self._options[ 'export_path' ] = HC.ConvertAbsPathToPortablePath( self._export_location.GetPath() )
        self._options[ 'default_sort' ] = self._default_sort.GetSelection() 
        self._options[ 'default_collect' ] = self._default_collect.GetChoice()
        
        self._options[ 'exclude_deleted_files' ] = self._exclude_deleted_files.GetValue()
        
        self._options[ 'thumbnail_cache_size' ] = self._thumbnail_cache_size.GetValue() * 1048576
        self._options[ 'preview_cache_size' ] = self._preview_cache_size.GetValue() * 1048576
        self._options[ 'fullscreen_cache_size' ] = self._fullscreen_cache_size.GetValue() * 1048576
        
        self._options[ 'thumbnail_dimensions' ] = [ self._thumbnail_width.GetValue(), self._thumbnail_height.GetValue() ]
        
        self._options[ 'num_autocomplete_chars' ] = self._num_autocomplete_chars.GetValue()
        
        self._options[ 'namespace_colours' ] = self._namespace_colours.GetNamespaceColours()
        
        sort_by_choices = []
        
        for sort_by in [ self._sort_by.GetClientData( i ) for i in range( self._sort_by.GetCount() ) ]: sort_by_choices.append( ( 'namespaces', sort_by ) )
        
        self._options[ 'sort_by' ] = sort_by_choices
        
        system_predicates = {}
        
        system_predicates[ 'age' ] = ( self._file_system_predicate_age_sign.GetSelection(), self._file_system_predicate_age_years.GetValue(), self._file_system_predicate_age_months.GetValue(), self._file_system_predicate_age_days.GetValue() )
        system_predicates[ 'duration' ] = ( self._file_system_predicate_duration_sign.GetSelection(), self._file_system_predicate_duration_s.GetValue(), self._file_system_predicate_duration_ms.GetValue() )
        system_predicates[ 'height' ] = ( self._file_system_predicate_height_sign.GetSelection(), self._file_system_predicate_height.GetValue() )
        system_predicates[ 'limit' ] = self._file_system_predicate_limit.GetValue()
        system_predicates[ 'mime' ] = ( self._file_system_predicate_mime_media.GetSelection(), self._file_system_predicate_mime_type.GetSelection() )
        system_predicates[ 'num_tags' ] = ( self._file_system_predicate_num_tags_sign.GetSelection(), self._file_system_predicate_num_tags.GetValue() )
        system_predicates[ 'local_rating_like' ] = self._file_system_predicate_local_rating_like_value.GetSelection()
        system_predicates[ 'local_rating_numerical' ] = ( self._file_system_predicate_local_rating_numerical_sign.GetSelection(), self._file_system_predicate_local_rating_numerical_value.GetValue() )
        system_predicates[ 'ratio' ] = ( self._file_system_predicate_ratio_sign.GetSelection(), self._file_system_predicate_ratio_width.GetValue(), self._file_system_predicate_ratio_height.GetValue() )
        system_predicates[ 'size' ] = ( self._file_system_predicate_size_sign.GetSelection(), self._file_system_predicate_size.GetValue(), self._file_system_predicate_size_unit.GetSelection() )
        system_predicates[ 'width' ] = ( self._file_system_predicate_width_sign.GetSelection(), self._file_system_predicate_width.GetValue() )
        system_predicates[ 'num_words' ] = ( self._file_system_predicate_num_words_sign.GetSelection(), self._file_system_predicate_num_words.GetValue() )
        
        self._options[ 'file_system_predicates' ] = system_predicates
        
        shortcuts = {}
        
        shortcuts[ wx.ACCEL_NORMAL ] = {}
        shortcuts[ wx.ACCEL_CTRL ] = {}
        shortcuts[ wx.ACCEL_ALT ] = {}
        shortcuts[ wx.ACCEL_SHIFT ] = {}
        
        for ( modifier, key, action ) in self._shortcuts.GetClientData(): shortcuts[ modifier ][ key ] = action
        
        self._options[ 'shortcuts' ] = shortcuts
        
        self._options[ 'default_tag_repository' ] = self._default_tag_repository.GetClientData( self._default_tag_repository.GetSelection() )
        self._options[ 'default_tag_sort' ] = self._default_tag_sort.GetClientData( self._default_tag_sort.GetSelection() )
        
        try: wx.GetApp().Write( 'save_options' )
        except: wx.MessageBox( traceback.format_exc() )
        
        self.EndModal( wx.ID_OK )
        
    
    def EventRemoveSortBy( self, event ):
        
        selection = self._sort_by.GetSelection()
        
        if selection != wx.NOT_FOUND: self._sort_by.Delete( selection )
        
    
    def EventPreviewsUpdate( self, event ):
        
        estimated_bytes_per_preview = 3 * 400 * 400
        
        self._estimated_number_previews.SetLabel( '(about ' + HC.ConvertIntToPrettyString( ( self._preview_cache_size.GetValue() * 1048576 ) / estimated_bytes_per_preview ) + ' previews)' )
        
    
    def EventShortcutsAdd( self, event ):
        
        with DialogInputShortcut( self ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                ( modifier, key, action ) = dlg.GetInfo()
                
                ( pretty_modifier, pretty_key, pretty_action ) = HC.ConvertShortcutToPrettyShortcut( modifier, key, action )
                
                self._shortcuts.Append( ( pretty_modifier, pretty_key, pretty_action ), ( modifier, key, action ) )
                
                self._SortListCtrl()
                
            
        
    
    def EventShortcutsDelete( self, event ): self._shortcuts.RemoveAllSelected()
    
    def EventShortcutsEdit( self, event ):
        
        indices = self._shortcuts.GetAllSelected()
        
        for index in indices:
            
            ( modifier, key, action ) = self._shortcuts.GetClientData( index )
            
            try:
                
                with DialogInputShortcut( self, modifier, key, action ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        ( modifier, key, action ) = dlg.GetInfo()
                        
                        ( pretty_modifier, pretty_key, pretty_action ) = HC.ConvertShortcutToPrettyShortcut( modifier, key, action )
                        
                        self._shortcuts.UpdateRow( index, ( pretty_modifier, pretty_key, pretty_action ), ( modifier, key, action ) )
                        
                        self._SortListCtrl()
                        
                    
                
            except Exception as e: wx.MessageBox( unicode( e ) )
            
        
    
    def EventThumbnailsUpdate( self, event ):
        
        estimated_bytes_per_thumb = 3 * self._thumbnail_height.GetValue() * self._thumbnail_width.GetValue()
        
        self._estimated_number_thumbnails.SetLabel( '(about ' + HC.ConvertIntToPrettyString( ( self._thumbnail_cache_size.GetValue() * 1048576 ) / estimated_bytes_per_thumb ) + ' thumbnails)' )
        
    
class DialogManageOptionsServerAdmin( Dialog ):
    
    def __init__( self, parent, service_identifier ):
        
        def InitialiseControls():
            
            
            self._server_panel = ClientGUICommon.StaticBox( self, 'server' )
            
            self._max_monthly_data = ClientGUICommon.NoneableSpinCtrl( self._server_panel, 'max monthly data (MB)', options[ 'max_monthly_data' ], multiplier = 1048576 )
            
            self._max_storage = ClientGUICommon.NoneableSpinCtrl( self._server_panel, 'max storage (MB)', options[ 'max_monthly_data' ], multiplier = 1048576 )
            
            self._message = wx.TextCtrl( self._server_panel, value = options[ 'message' ] )
            
            self._save_button = wx.Button( self, label='Save' )
            self._save_button.Bind( wx.EVT_BUTTON, self.EventOK )
            self._save_button.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._close_button = wx.Button( self, id = wx.ID_CANCEL, label='Cancel' )
            self._close_button.Bind( wx.EVT_BUTTON, self.EventCancel )
            self._close_button.SetForegroundColour( ( 128, 0, 0 ) )
            
        
        def InitialisePanel():
            
            gridbox = wx.FlexGridSizer( 0, 2 )
            
            gridbox.AddGrowableCol( 1, 1 )
            
            gridbox.AddF( wx.StaticText( self._server_panel, label='Message' ), FLAGS_MIXED )
            gridbox.AddF( self._message, FLAGS_MIXED )
            
            self._server_panel.AddF( self._max_monthly_data, FLAGS_EXPAND_PERPENDICULAR )
            self._server_panel.AddF( self._max_storage, FLAGS_EXPAND_PERPENDICULAR )
            self._server_panel.AddF( gridbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            buttons = wx.BoxSizer( wx.HORIZONTAL )
            
            buttons.AddF( self._save_button, FLAGS_SMALL_INDENT )
            buttons.AddF( self._close_button, FLAGS_SMALL_INDENT )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( self._server_panel, FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( buttons, FLAGS_BUTTON_SIZERS )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x + 80, y ) )
            
        
        Dialog.__init__( self, parent, service_identifier.GetName() + ' options' )
        
        self._service_identifier = service_identifier
        
        self._service = wx.GetApp().Read( 'service', service_identifier )
        
        connection = self._service.GetConnection()
        
        options = connection.Get( 'options' )
        
        InitialiseControls()
        
        InitialisePanel()
        
    
    def EventCancel( self, event ): self.EndModal( wx.ID_CANCEL )
    
    def EventOK( self, event ):
        
        options = {}
        
        options[ 'max_monthly_data' ] = self._max_monthly_data.GetValue()
        
        options[ 'max_storage' ] = self._max_storage.GetValue()
        
        options[ 'message' ] = self._message.GetValue()
        
        try:
            
            connection = self._service.GetConnection()
            
            connection.Post( 'options', options = options )
            
        except Exception as e: wx.MessageBox( 'Something went wrong when trying to send the options to the server admin: ' + unicode( e ) )
        
        self.EndModal( wx.ID_OK )
        
    
class DialogManageOptionsTagRepository( Dialog ):
    
    def __init__( self, parent, service_identifier ):
        
        def InitialiseControls():
            
            self._tag_repository_panel = ClientGUICommon.StaticBox( self, 'tag repository' )
            
            self._max_monthly_data = ClientGUICommon.NoneableSpinCtrl( self._tag_repository_panel, 'max monthly data (MB)', options[ 'max_monthly_data' ], multiplier = 1048576 )
            
            self._message = wx.TextCtrl( self._tag_repository_panel, value = options[ 'message' ] )
            
            self._save_button = wx.Button( self, label='Save' )
            self._save_button.Bind( wx.EVT_BUTTON, self.EventOK )
            self._save_button.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._close_button = wx.Button( self, id = wx.ID_CANCEL, label='Cancel' )
            self._close_button.Bind( wx.EVT_BUTTON, self.EventCancel )
            self._close_button.SetForegroundColour( ( 128, 0, 0 ) )
            
        
        def InitialisePanel():
            
            gridbox = wx.FlexGridSizer( 0, 2 )
            
            gridbox.AddGrowableCol( 1, 1 )
            
            gridbox.AddF( wx.StaticText( self._tag_repository_panel, label='Message' ), FLAGS_MIXED )
            gridbox.AddF( self._message, FLAGS_MIXED )
            
            self._tag_repository_panel.AddF( self._max_monthly_data, FLAGS_EXPAND_PERPENDICULAR )
            self._tag_repository_panel.AddF( gridbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            buttons = wx.BoxSizer( wx.HORIZONTAL )
            
            buttons.AddF( self._save_button, FLAGS_SMALL_INDENT )
            buttons.AddF( self._close_button, FLAGS_SMALL_INDENT )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( self._tag_repository_panel, FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( buttons, FLAGS_BUTTON_SIZERS )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x + 80, y ) )
            
        
        Dialog.__init__( self, parent, service_identifier.GetName() + ' options' )
        
        self._service_identifier = service_identifier
        
        self._service = wx.GetApp().Read( 'service', service_identifier )
        
        connection = self._service.GetConnection()
        
        options = connection.Get( 'options' )
        
        InitialiseControls()
        
        InitialisePanel()
        
    
    def EventCancel( self, event ): self.EndModal( wx.ID_CANCEL )
    
    def EventOK( self, event ):
        
        options = {}
        
        options[ 'max_monthly_data' ] = self._max_monthly_data.GetValue()
        
        options[ 'message' ] = self._message.GetValue()
        
        try:
            
            connection = self._service.GetConnection()
            
            connection.Post( 'options', options = options )
            
        except Exception as e: wx.MessageBox( 'Something went wrong when trying to send the options to the tag repository: ' + unicode( e ) )
        
        self.EndModal( wx.ID_OK )
        
    
class DialogManagePixivAccount( Dialog ):
    
    def __init__( self, parent ):
        
        def InitialiseControls():
            
            self._id = wx.TextCtrl( self, value = id )
            self._password = wx.TextCtrl( self, value = password )
            
            self._status = wx.StaticText( self )
            
            self._test = wx.Button( self, label = 'test' )
            self._test.Bind( wx.EVT_BUTTON, self.EventTest )
            
            self._ok = wx.Button( self, label='Ok' )
            self._ok.Bind( wx.EVT_BUTTON, self.EventOk )
            self._ok.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label='Cancel' )
            self._cancel.Bind( wx.EVT_BUTTON, self.EventCancel )        
            self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
            
        
        def InitialisePanel():
            
            gridbox = wx.FlexGridSizer( 0, 2 )
            
            gridbox.AddGrowableCol( 1, 1 )
            
            gridbox.AddF( wx.StaticText( self, label='id/email' ), FLAGS_MIXED )
            gridbox.AddF( self._id, FLAGS_EXPAND_BOTH_WAYS )
            gridbox.AddF( wx.StaticText( self, label='password' ), FLAGS_MIXED )
            gridbox.AddF( self._password, FLAGS_EXPAND_BOTH_WAYS )
            
            b_box = wx.BoxSizer( wx.HORIZONTAL )
            b_box.AddF( self._ok, FLAGS_MIXED )
            b_box.AddF( self._cancel, FLAGS_MIXED )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( gridbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
            vbox.AddF( self._status, FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._test, FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( b_box, FLAGS_BUTTON_SIZERS )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            x = max( x, 240 )
            
            self.SetInitialSize( ( x, y ) )
            
        
        Dialog.__init__( self, parent, 'manage pixiv account' )
        
        ( id, password ) = wx.GetApp().Read( 'pixiv_account' )
        
        InitialiseControls()
        
        InitialisePanel()
        
    
    def EventCancel( self, event ): self.EndModal( wx.ID_CANCEL )
    
    def EventOk( self, event ):
        
        id = self._id.GetValue()
        password = self._password.GetValue()
        
        wx.GetApp().Write( 'pixiv_account', id, password )
        
        self.EndModal( wx.ID_OK )
        
    
    def EventTest( self, event ):
        
        try:
            
            id = self._id.GetValue()
            password = self._password.GetValue()
            
            form_fields = {}
            
            form_fields[ 'mode' ] = 'login'
            form_fields[ 'pixiv_id' ] = id
            form_fields[ 'pass' ] = password
            
            body = urllib.urlencode( form_fields )
            
            headers = {}
            headers[ 'Content-Type' ] = 'application/x-www-form-urlencoded'
            
            connection = CC.AdvancedHTTPConnection( url = 'http://www.pixiv.net/', accept_cookies = True )
            
            response = connection.request( 'POST', '/login.php', headers = headers, body = body, follow_redirects = False )
            
            cookies = connection.GetCookies()
            
            # _ only given to logged in php sessions
            if 'PHPSESSID' in cookies and '_' in cookies[ 'PHPSESSID' ]: self._status.SetLabel( 'OK!' )
            else: self._status.SetLabel( 'Did not work!' )
            
            wx.CallLater( 2000, self._status.SetLabel, '' )
            
        except Exception as e:
            wx.MessageBox( traceback.format_exc() )
            wx.MessageBox( unicode( e ) )
        
    
class DialogManageRatings( Dialog ):
    
    def __init__( self, parent, media ):
        
        def InitialiseControls():
            
            service_identifiers = wx.GetApp().Read( 'service_identifiers', HC.RATINGS_SERVICES )
            
            # sort according to local/remote, I guess
            # and maybe sub-sort according to name?
            # maybe just do two get s_i queries
            
            self._panels = []
            
            for service_identifier in service_identifiers: self._panels.append( self._Panel( self, service_identifier, media ) )
            
            self._apply = wx.Button( self, label='Apply' )
            self._apply.Bind( wx.EVT_BUTTON, self.EventOk )
            self._apply.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label='Cancel' )
            self._cancel.Bind( wx.EVT_BUTTON, self.EventCancel )
            self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
            
        
        def InitialisePanel():
            
            buttonbox = wx.BoxSizer( wx.HORIZONTAL )
            
            buttonbox.AddF( self._apply, FLAGS_MIXED )
            buttonbox.AddF( self._cancel, FLAGS_MIXED )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            for panel in self._panels: vbox.AddF( panel, FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( buttonbox, FLAGS_BUTTON_SIZERS )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x + 200, y ) )
            
        
        self._hashes = HC.IntelligentMassUnion( ( m.GetHashes() for m in media ) )
        
        Dialog.__init__( self, parent, 'manage ratings for ' + HC.ConvertIntToPrettyString( len( self._hashes ) ) + ' files' )
        
        InitialiseControls()
        
        InitialisePanel()
        
        self.Bind( wx.EVT_MENU, self.EventMenu )
        
        self.RefreshAcceleratorTable()
        
    
    def EventCancel( self, event ): self.EndModal( wx.ID_CANCEL )
    
    def EventMenu( self, event ):
        
        action = CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetAction( event.GetId() )
        
        if action is not None:
            
            ( command, data ) = action
            
            if command == 'manage_ratings': self.EventCancel( event )
            elif command == 'ok': self.EventOk( event )
            else: event.Skip()
            
        
    
    def EventOk( self, event ):
        
        try:
            
            content_updates = []
            
            for panel in self._panels:
                
                if panel.HasChanges():
                    
                    service_identifier = panel.GetServiceIdentifier()
                    
                    rating = panel.GetRating()
                    
                    content_updates.append( HC.ContentUpdate( CC.CONTENT_UPDATE_RATING, service_identifier, self._hashes, info = rating ) )
                    
                
            
            if len( content_updates ) > 0: wx.GetApp().Write( 'content_updates', content_updates )
            
        except Exception as e: wx.MessageBox( 'Saving pending mapping changes to DB raised this error: ' + unicode( e ) )
        
        self.EndModal( wx.ID_OK )
        
    
    def RefreshAcceleratorTable( self ):
        
        interested_actions = [ 'manage_ratings' ]
        
        entries = []
        
        for ( modifier, key_dict ) in self._options[ 'shortcuts' ].items(): entries.extend( [ ( modifier, key, CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( action ) ) for ( key, action ) in key_dict.items() if action in interested_actions ] )
        
        self.SetAcceleratorTable( wx.AcceleratorTable( entries ) )
        
    
    class _Panel( wx.Panel ):
        
        def __init__( self, parent, service_identifier, media ):
            
            wx.Panel.__init__( self, parent )
            
            self._service_identifier = service_identifier
            self._service = wx.GetApp().Read( 'service', service_identifier )
            
            extra_info = self._service.GetExtraInfo()
            
            self._media = media
            
            service_type = service_identifier.GetType()
            
            def InitialiseControls():
                
                self._ratings_panel = ClientGUICommon.StaticBox( self, self._service_identifier.GetName() )
                
                self._current_score = wx.StaticText( self._ratings_panel, style = wx.ALIGN_CENTER )
                
                score_font = self._GetScoreFont()
                
                self._current_score.SetFont( score_font )
                
                if service_type in ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ): all_rating_services = [ local_ratings for ( local_ratings, remote_ratings ) in [ media.GetRatings() for media in self._media ] ]
                elif service_type in ( HC.RATING_LIKE_REPOSITORY, HC.RATING_NUMERICAL_REPOSITORY ): all_rating_services = [ remote_ratings for ( local_ratings, remote_ratings ) in [ media.GetRatings() for media in self._media ] ]
                
                if service_type in ( HC.LOCAL_RATING_LIKE, HC.RATING_LIKE_REPOSITORY ):
                    
                    ( like, dislike ) = extra_info
                    
                    if service_type == HC.LOCAL_RATING_LIKE:
                        
                        ratings = [ rating_services.GetRating( self._service_identifier ) for rating_services in all_rating_services ]
                        
                        if all( ( i is None for i in ratings ) ):
                            
                            choices = [ like, dislike, 'make no changes' ]
                            
                            if len( self._media ) > 1: self._current_score.SetLabel( 'none rated' )
                            else: self._current_score.SetLabel( 'not rated' )
                            
                        elif None in ratings:
                            
                            choices = [ like, dislike, 'remove rating', 'make no changes' ]
                            
                            self._current_score.SetLabel( 'not all rated' )
                            
                        else:
                            
                            if all( ( i == 1 for i in ratings ) ):
                                
                                choices = [ dislike, 'remove rating', 'make no changes' ]
                                
                                if len( self._media ) > 1: self._current_score.SetLabel( 'all ' + like )
                                else: self._current_score.SetLabel( like )
                                
                            elif all( ( i == 0 for i in ratings ) ):
                                
                                choices = [ like, 'remove rating', 'make no changes' ]
                                
                                if len( self._media ) > 1: self._current_score.SetLabel( 'all ' + dislike )
                                else: self._current_score.SetLabel( dislike )
                                
                            else:
                                
                                choices = [ like, dislike, 'remove rating', 'make no changes' ]
                                
                            
                            overall_rating = float( sum( ratings ) ) / float( len( ratings ) )
                            
                            self._current_score.SetLabel( str( '%.2f' % overall_rating ) )
                            
                        
                        if len( self._media ) > 1:
                            
                            ratings_counter = collections.Counter( ratings )
                            
                            likes = ratings_counter[ 1 ]
                            dislikes = ratings_counter[ 0 ]
                            nones = ratings_counter[ None ]
                            
                            scores = []
                            
                            if likes > 0: scores.append( str( likes ) + ' likes' )
                            if dislikes > 0: scores.append( str( dislikes ) + ' dislikes' )
                            if nones > 0: scores.append( str( nones ) + ' not rated' )
                            
                            self._current_score.SetLabel( ', '.join( scores ) )
                            
                        else:
                            
                            ( rating, ) = ratings
                            
                            if rating is None: self._current_score.SetLabel( 'not rated' )
                            elif rating == 1: self._current_score.SetLabel( like )
                            elif rating == 0: self._current_score.SetLabel( dislike )
                            
                        
                    else:
                        
                        self._current_score.SetLabel( '23 ' + like + 's, 44 ' + dislike + 's' )
                        
                    
                elif service_type in ( HC.LOCAL_RATING_NUMERICAL, HC.RATING_NUMERICAL_REPOSITORY ):
                    
                    if service_type == HC.LOCAL_RATING_NUMERICAL:
                        
                        ( min, max ) = extra_info
                        
                        self._slider = wx.Slider( self._ratings_panel, minValue = min, maxValue = max, style = wx.SL_AUTOTICKS | wx.SL_LABELS )
                        self._slider.Bind( wx.EVT_SLIDER, self.EventSlider )
                        
                        ratings = [ rating_services.GetRating( self._service_identifier ) for rating_services in all_rating_services ]
                        
                        if all( ( i is None for i in ratings ) ):
                            
                            choices = [ 'set rating', 'make no changes' ]
                            
                            if len( self._media ) > 1: self._current_score.SetLabel( 'none rated' )
                            else: self._current_score.SetLabel( 'not rated' )
                            
                        elif None in ratings:
                            
                            choices = [ 'set rating', 'remove rating', 'make no changes' ]
                            
                            if len( self._media ) > 1: self._current_score.SetLabel( 'not all rated' )
                            else: self._current_score.SetLabel( 'not rated' )
                            
                        else:
                            
                            # you know what? this should really be a bargraph or something!
                            #                               *     
                            #                               *     
                            #                               *     
                            #                          *    *     
                            #    *      *              *    *     
                            #   None    0    1    2    3    4    5
                            # but we can't rely on integers, so just think about it
                            # some kind of sense of distribution would be helpful though
                            
                            choices = [ 'set rating', 'remove rating', 'make no changes' ]
                            
                            overall_rating = float( sum( ratings ) ) / float( len( ratings ) )
                            
                            overall_rating_converted = ( overall_rating * ( max - min ) ) + min
                            
                            self._slider.SetValue( int( overall_rating_converted + 0.5 ) )
                            
                            str_overall_rating = str( '%.2f' % overall_rating_converted )
                            
                            if min in ( 0, 1 ): str_overall_rating += '/' + str( '%.2f' % max )
                            
                            self._current_score.SetLabel( str_overall_rating )
                            
                        
                    else:
                        
                        self._current_score.SetLabel( '3.82/5' )
                        
                    
                
                if service_type in ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ):
                    
                    initial_index = choices.index( 'make no changes' )
                    
                    choice_pairs = [ ( choice, choice ) for choice in choices ]
                    
                    self._choices = ClientGUICommon.RadioBox( self._ratings_panel, 'actions', choice_pairs, initial_index )
                    
                
            
            def InitialisePanel():
                
                self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
                
                if service_type in ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ): label = 'local rating'
                elif service_type in ( HC.RATING_LIKE_REPOSITORY, HC.RATING_NUMERICAL_REPOSITORY ): label = 'remote rating'
                
                self._ratings_panel.AddF( self._current_score, FLAGS_EXPAND_PERPENDICULAR )
                
                if service_type in ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ):
                    
                    if service_type == HC.LOCAL_RATING_LIKE:
                        
                        self._ratings_panel.AddF( self._choices, FLAGS_EXPAND_PERPENDICULAR )
                        
                    elif service_type == HC.LOCAL_RATING_NUMERICAL:
                        
                        self._ratings_panel.AddF( self._slider, FLAGS_EXPAND_PERPENDICULAR )
                        self._ratings_panel.AddF( self._choices, FLAGS_EXPAND_PERPENDICULAR )
                        
                    
                
                vbox = wx.BoxSizer( wx.VERTICAL )
                
                vbox.AddF( self._ratings_panel, FLAGS_EXPAND_PERPENDICULAR )
                
                self.SetSizer( vbox )
                
            
            InitialiseControls()
            
            InitialisePanel()
            
        
        def _GetScoreFont( self ):
            
            normal_font = wx.SystemSettings.GetFont( wx.SYS_DEFAULT_GUI_FONT )
            
            normal_font_size = normal_font.GetPointSize()
            normal_font_family = normal_font.GetFamily()
            
            return wx.Font( normal_font_size * 2, normal_font_family, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD )
            
        
        def EventSlider( self, event ):
            
            rating = self._slider.GetValue()
            
            self._choices.SetSelection( 0 )
            
            self._choices.SetString( 0, 'set rating to ' + str( rating ) )
            
            event.Skip()
            
        
        def GetRating( self ):
            
            service_type = self._service_identifier.GetType()
            
            choice_text = self._choices.GetSelectedClientData()
            
            if choice_text == 'remove rating': return None
            else:
                
                if service_type == HC.LOCAL_RATING_LIKE:
                    
                    ( like, dislike ) = self._service.GetExtraInfo()
                    
                    if choice_text == like: rating = 1
                    elif choice_text == dislike: rating = 0
                    
                elif service_type == HC.LOCAL_RATING_NUMERICAL: rating = float( self._slider.GetValue() - self._slider.GetMin() ) / float( self._slider.GetMax() - self._slider.GetMin() )
                
            
            return rating
            
        
        def HasChanges( self ):
            
            choice_text = self._choices.GetSelectedClientData()
            
            if choice_text == 'make no changes': return False
            else: return True
            
        
        def GetServiceIdentifier( self ): return self._service_identifier
        
    
class DialogManageServer( Dialog ):
    
    def __init__( self, parent, service_identifier ):
        
        def InitialiseControls():
            
            self._edit_log = []
            
            self._services_listbook = ClientGUICommon.ListBook( self )
            self._services_listbook.Bind( wx.EVT_NOTEBOOK_PAGE_CHANGED, self.EventServiceChanged )
            self._services_listbook.Bind( wx.EVT_NOTEBOOK_PAGE_CHANGING, self.EventServiceChanging )
            
            self._service_types = wx.Choice( self )
            
            for service_type in [ HC.TAG_REPOSITORY, HC.FILE_REPOSITORY, HC.MESSAGE_DEPOT ]: self._service_types.Append( HC.service_string_lookup[ service_type ], service_type )
            
            self._service_types.SetSelection( 0 )
            
            self._add = wx.Button( self, label='add' )
            self._add.Bind( wx.EVT_BUTTON, self.EventAdd )
            self._add.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._remove = wx.Button( self, label='remove' )
            self._remove.Bind( wx.EVT_BUTTON, self.EventRemove )
            self._remove.SetForegroundColour( ( 128, 0, 0 ) )
            
            self._ok = wx.Button( self, label='ok' )
            self._ok.Bind( wx.EVT_BUTTON, self.EventOk )
            self._ok.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label='cancel' )
            self._cancel.Bind( wx.EVT_BUTTON, self.EventCancel )
            self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
            
            # goes after self._remove, because of events
            
            for service_identifier in self._service_identifiers:
                
                page = self._Panel( self._services_listbook, service_identifier )
                
                name = HC.service_string_lookup[ service_identifier.GetType() ]
                
                self._services_listbook.AddPage( page, name )
                
            
        
        def InitialisePanel():
            
            add_remove_hbox = wx.BoxSizer( wx.HORIZONTAL )
            add_remove_hbox.AddF( self._service_types, FLAGS_MIXED )
            add_remove_hbox.AddF( self._add, FLAGS_MIXED )
            add_remove_hbox.AddF( self._remove, FLAGS_MIXED )
            
            ok_hbox = wx.BoxSizer( wx.HORIZONTAL )
            ok_hbox.AddF( self._ok, FLAGS_MIXED )
            ok_hbox.AddF( self._cancel, FLAGS_MIXED )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            vbox.AddF( self._services_listbook, FLAGS_EXPAND_BOTH_WAYS )
            vbox.AddF( add_remove_hbox, FLAGS_SMALL_INDENT )
            vbox.AddF( ok_hbox, FLAGS_BUTTON_SIZERS )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            if y < 400: y = 400 # listbook's setsize ( -1, 400 ) is buggy
            
            self.SetInitialSize( ( 680, y ) )
            
        
        Dialog.__init__( self, parent, 'manage ' + service_identifier.GetName() + ' services' )
        
        self._service = wx.GetApp().Read( 'service', service_identifier )
        
        connection = self._service.GetConnection()
        
        self._service_identifiers = connection.Get( 'services' )
        
        InitialiseControls()
        
        InitialisePanel()
        
        current_page = self._services_listbook.GetCurrentPage()
        
        if current_page.GetOriginalServiceIdentifier().GetType() == HC.SERVER_ADMIN: self._remove.Disable()
        else: self._remove.Enable()
        
    
    def _CheckCurrentServiceIsValid( self ):
        
        service_panel = self._services_listbook.GetCurrentPage()
        
        if service_panel is not None:
            
            port = service_panel.GetInfo()
            
            for existing_port in [ page.GetInfo() for page in self._services_listbook.GetNameToPageDict().values() if page != service_panel ]:
                
                if port == existing_port: raise Exception( 'That port is already in use!' )
                
            
        
    
    def EventAdd( self, event ):
        
        try:
            
            self._CheckCurrentServiceIsValid()
            
            service_type = self._service_types.GetClientData( self._service_types.GetSelection() )
            
            existing_ports = [ page.GetInfo() for page in self._services_listbook.GetNameToPageDict().values() ]
            
            port = HC.DEFAULT_SERVICE_PORT
            
            while port in existing_ports: port += 1
            
            service_identifier = HC.ServerServiceIdentifier( service_type, port )
            
            self._edit_log.append( ( HC.ADD, service_identifier ) )
            
            page = self._Panel( self._services_listbook, service_identifier )
            
            name = HC.service_string_lookup[ service_type ]
            
            self._services_listbook.AddPage( page, name, select = True )
            
        except Exception as e: wx.MessageBox( unicode( e ) )
        
    
    def EventCancel( self, event ): self.EndModal( wx.ID_CANCEL )
    
    def EventOk( self, event ):
        
        try: self._CheckCurrentServiceIsValid()
        except Exception as e:
            
            wx.MessageBox( unicode( e ) )
            
            return
            
        
        for page in self._services_listbook.GetNameToPageDict().values():
            
            if page.HasChanges(): self._edit_log.append( ( HC.EDIT, ( page.GetOriginalServiceIdentifier(), page.GetInfo() ) ) )
            
        
        try:
            
            if len( self._edit_log ) > 0:
                
                connection = self._service.GetConnection()
                
                connection.Post( 'services_modification', edit_log = self._edit_log )
                
                wx.GetApp().Write( 'update_server_services', self._service.GetServiceIdentifier(), self._edit_log )
                
            
        except Exception as e: wx.MessageBox( 'Saving services to server raised this error: ' + unicode( e ) )
        
        self.EndModal( wx.ID_OK )
        
    
    def EventRemove( self, event ):
        
        service_panel = self._services_listbook.GetCurrentPage()
        
        if service_panel is not None:
            
            service_identifier = service_panel.GetOriginalServiceIdentifier()
            
            self._edit_log.append( ( HC.DELETE, service_identifier ) )
            
            self._services_listbook.DeleteCurrentPage()
            
        
    
    def EventServiceChanged( self, event ):
        
        page = self._services_listbook.GetCurrentPage()
        
        if page.GetOriginalServiceIdentifier().GetType() == HC.SERVER_ADMIN: self._remove.Disable()
        else: self._remove.Enable()
        
    
    def EventServiceChanging( self, event ):
        
        try: self._CheckCurrentServiceIsValid()
        except Exception as e:
            
            wx.MessageBox( unicode( e ) )
            
            event.Veto()
            
        
    
    class _Panel( wx.Panel ):
        
        def __init__( self, parent, service_identifier ):
            
            wx.Panel.__init__( self, parent )
            
            self._service_identifier = service_identifier
            
            service_type = service_identifier.GetType()
            
            def InitialiseControls():
                
                self._service_panel = ClientGUICommon.StaticBox( self, 'service' )
                
                self._service_port = wx.SpinCtrl( self._service_panel, min = 1, max = 65535 )
                self._service_port.SetValue( service_identifier.GetPort() )
                
            
            def InitialisePanel():
                
                self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
                
                vbox = wx.BoxSizer( wx.VERTICAL )
                
                gridbox = wx.FlexGridSizer( 0, 2 )
                
                gridbox.AddGrowableCol( 1, 1 )
                
                gridbox.AddF( wx.StaticText( self._service_panel, label='port' ), FLAGS_MIXED )
                gridbox.AddF( self._service_port, FLAGS_EXPAND_BOTH_WAYS )
                
                self._service_panel.AddF( gridbox, FLAGS_EXPAND_SIZER_BOTH_WAYS )
                
                vbox.AddF( self._service_panel, FLAGS_EXPAND_BOTH_WAYS )
                
                self.SetSizer( vbox )
                
            
            InitialiseControls()
            
            InitialisePanel()
            
        
        def GetInfo( self ):
            
            port = self._service_port.GetValue()
            
            return port
            
        
        def HasChanges( self ):
            
            port = self.GetInfo()
            
            if port != self._service_identifier.GetPort(): return True
            
            return False
            
        
        def GetOriginalServiceIdentifier( self ): return self._service_identifier
        
    
class DialogManageServices( Dialog ):
    
    def __init__( self, parent ):
        
        def InitialiseControls():
            
            self._edit_log = []
            
            self._listbook = ClientGUICommon.ListBook( self )
            self._listbook.Bind( wx.EVT_NOTEBOOK_PAGE_CHANGING, self.EventServiceChanging )
            
            self._local_ratings_like = ClientGUICommon.ListBook( self._listbook )
            self._local_ratings_like.Bind( wx.EVT_NOTEBOOK_PAGE_CHANGING, self.EventServiceChanging )
            
            self._local_ratings_numerical = ClientGUICommon.ListBook( self._listbook )
            self._local_ratings_numerical.Bind( wx.EVT_NOTEBOOK_PAGE_CHANGING, self.EventServiceChanging )
            
            self._tag_repositories = ClientGUICommon.ListBook( self._listbook )
            self._tag_repositories.Bind( wx.EVT_NOTEBOOK_PAGE_CHANGING, self.EventServiceChanging )
            
            self._file_repositories = ClientGUICommon.ListBook( self._listbook )
            self._file_repositories.Bind( wx.EVT_NOTEBOOK_PAGE_CHANGING, self.EventServiceChanging )
            
            self._message_depots = ClientGUICommon.ListBook( self._listbook )
            self._message_depots.Bind( wx.EVT_NOTEBOOK_PAGE_CHANGING, self.EventServiceChanging )
            
            self._servers_admin = ClientGUICommon.ListBook( self._listbook )
            self._servers_admin.Bind( wx.EVT_NOTEBOOK_PAGE_CHANGING, self.EventServiceChanging )
            
            services = wx.GetApp().Read( 'services', HC.RESTRICTED_SERVICES + [ HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ] )
            
            for service in services:
                
                service_identifier = service.GetServiceIdentifier()
                
                service_type = service_identifier.GetType()
                name = service_identifier.GetName()
                
                if service_type in HC.REMOTE_SERVICES: credentials = service.GetCredentials()
                else: credentials = None
                
                extra_info = service.GetExtraInfo()
                
                if service_type == HC.LOCAL_RATING_LIKE: listbook = self._local_ratings_like
                elif service_type == HC.LOCAL_RATING_NUMERICAL: listbook = self._local_ratings_numerical
                elif service_type == HC.TAG_REPOSITORY: listbook = self._tag_repositories
                elif service_type == HC.FILE_REPOSITORY: listbook = self._file_repositories
                elif service_type == HC.MESSAGE_DEPOT: listbook = self._message_depots
                elif service_type == HC.SERVER_ADMIN: listbook = self._servers_admin
                else: continue
                
                page_info = ( self._Panel, ( listbook, service_identifier, credentials, extra_info ), {} )
                
                listbook.AddPage( page_info, name )
                
            
            self._listbook.AddPage( self._local_ratings_like, 'local ratings like' )
            self._listbook.AddPage( self._local_ratings_numerical, 'local ratings numerical' )
            self._listbook.AddPage( self._tag_repositories, 'tags' )
            self._listbook.AddPage( self._file_repositories, 'files' )
            self._listbook.AddPage( self._message_depots, 'message depots' )
            self._listbook.AddPage( self._servers_admin, 'servers admin' )
            
            self._add = wx.Button( self, label='add' )
            self._add.Bind( wx.EVT_BUTTON, self.EventAdd )
            self._add.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._remove = wx.Button( self, label='remove' )
            self._remove.Bind( wx.EVT_BUTTON, self.EventRemove )
            self._remove.SetForegroundColour( ( 128, 0, 0 ) )
            
            self._export = wx.Button( self, label='export' )
            self._export.Bind( wx.EVT_BUTTON, self.EventExport )
            
            self._ok = wx.Button( self, label='ok' )
            self._ok.Bind( wx.EVT_BUTTON, self.EventOk )
            self._ok.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label='cancel' )
            self._cancel.Bind( wx.EVT_BUTTON, self.EventCancel )
            self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
            
            # these need to be below the addpages because they'd fire the events
            self._listbook.Bind( wx.EVT_NOTEBOOK_PAGE_CHANGING, self.EventPageChanging, source = self._listbook )
            
        
        def InitialisePanel():
            
            add_remove_hbox = wx.BoxSizer( wx.HORIZONTAL )
            add_remove_hbox.AddF( self._add, FLAGS_MIXED )
            add_remove_hbox.AddF( self._remove, FLAGS_MIXED )
            add_remove_hbox.AddF( self._export, FLAGS_MIXED )
            
            ok_hbox = wx.BoxSizer( wx.HORIZONTAL )
            ok_hbox.AddF( self._ok, FLAGS_MIXED )
            ok_hbox.AddF( self._cancel, FLAGS_MIXED )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            vbox.AddF( self._listbook, FLAGS_EXPAND_BOTH_WAYS )
            
            vbox.AddF( add_remove_hbox, FLAGS_SMALL_INDENT )
            vbox.AddF( ok_hbox, FLAGS_BUTTON_SIZERS )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( 880, y + 220 ) )
            
        
        Dialog.__init__( self, parent, 'manage services' )
        
        InitialiseControls()
        
        InitialisePanel()
        
        self.SetDropTarget( ClientGUICommon.FileDropTarget( self.Import ) )
        
    
    def _CheckCurrentServiceIsValid( self ):
        
        services_listbook = self._listbook.GetCurrentPage()
        
        if services_listbook is not None:
            
            service_panel = services_listbook.GetCurrentPage()
            
            if service_panel is not None:
                
                ( service_identifier, credentials, extra_info ) = service_panel.GetInfo()
                
                old_name = services_listbook.GetCurrentName()
                name = service_identifier.GetName()
                
                if old_name is not None and name != old_name:
                    
                    if services_listbook.NameExists( name ): raise Exception( 'That name is already in use!' )
                    
                    services_listbook.RenamePage( old_name, name )
                    
                
            
        
    
    def EventAdd( self, event ):
        
        with wx.TextEntryDialog( self, 'Enter new service\'s name' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                try:
                    
                    name = dlg.GetValue()
                    
                    services_listbook = self._listbook.GetCurrentPage()
                    
                    if services_listbook.NameExists( name ): raise Exception( 'That name is already in use!' )
                    
                    if name == '': raise Exception( 'Please enter a nickname for the service.' )
                    
                    if services_listbook == self._local_ratings_like: service_type = HC.LOCAL_RATING_LIKE
                    elif services_listbook == self._local_ratings_numerical: service_type = HC.LOCAL_RATING_NUMERICAL
                    elif services_listbook == self._tag_repositories: service_type = HC.TAG_REPOSITORY
                    elif services_listbook == self._file_repositories: service_type = HC.FILE_REPOSITORY
                    elif services_listbook == self._message_depots: service_type = HC.MESSAGE_DEPOT
                    elif services_listbook == self._servers_admin: service_type = HC.SERVER_ADMIN
                    
                    service_identifier = HC.ClientServiceIdentifier( os.urandom( 32 ), service_type, name )
                    
                    if service_type in HC.REMOTE_SERVICES:
                        
                        if service_type == HC.SERVER_ADMIN: credentials = CC.Credentials( 'hostname', 45870, '' )
                        elif service_type in HC.RESTRICTED_SERVICES:
                            
                            with DialogChooseNewServiceMethod( self ) as dlg:
                                
                                if dlg.ShowModal() != wx.ID_OK: return
                                
                                register = dlg.GetRegister()
                                
                                if register:
                                    
                                    with DialogRegisterService( self ) as dlg:
                                        
                                        if dlg.ShowModal() != wx.ID_OK: return
                                        
                                        credentials = dlg.GetCredentials()
                                        
                                    
                                else: credentials = CC.Credentials( 'hostname', 45871, '' )
                                
                            
                        else: credentials = CC.Credentials( 'hostname', 45871 )
                        
                    else: credentials = None
                    
                    if service_type == HC.MESSAGE_DEPOT:
                        
                        identity_name = 'identity@' + name
                        check_period = 180
                        private_key = HydrusMessageHandling.GenerateNewPrivateKey()
                        receive_anon = True
                        
                        extra_info = ( identity_name, check_period, private_key, receive_anon )
                        
                    elif service_type == HC.LOCAL_RATING_LIKE: extra_info = ( 'like', 'dislike' )
                    elif service_type == HC.LOCAL_RATING_NUMERICAL: extra_info = ( 0, 5 )
                    else: extra_info = None
                    
                    self._edit_log.append( ( 'add', ( service_identifier, credentials, extra_info ) ) )
                    
                    page = self._Panel( services_listbook, service_identifier, credentials, extra_info )
                    
                    services_listbook.AddPage( page, name, select = True )
                    
                except Exception as e:
                    
                    wx.MessageBox( unicode( e ) )
                    
                    self.EventAdd( event )
                    
                
            
        
    
    def EventCancel( self, event ): self.EndModal( wx.ID_CANCEL )
    
    def EventExport( self, event ):
        
        services_listbook = self._listbook.GetCurrentPage()
        
        if services_listbook is not None:
            
            service_panel = services_listbook.GetCurrentPage()
            
            if service_panel is not None:
                
                ( service_identifier, credentials, extra_info ) = service_panel.GetInfo()
                
                old_name = services_listbook.GetCurrentName()
                name = service_identifier.GetName()
                
                if old_name is not None and name != old_name:
                    
                    if services_listbook.NameExists( name ): raise Exception( 'That name is already in use!' )
                    
                    services_listbook.RenamePage( old_name, name )
                    
                
            
        
        services_listbook = self._listbook.GetCurrentPage()
        
        if services_listbook is not None:
            
            service_panel = services_listbook.GetCurrentPage()
            
            ( service_identifier, credentials, extra_info ) = service_panel.GetInfo()
            
            name = service_identifier.GetName()
            
            try:
                
                with wx.FileDialog( self, 'select where to export service', defaultFile = name + '.yaml', style = wx.FD_SAVE ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        with open( dlg.GetPath(), 'wb' ) as f: f.write( yaml.safe_dump( ( service_identifier, credentials, extra_info ) ) )
                        
                    
                
            except:
                
                with wx.FileDialog( self, 'select where to export service', defaultFile = 'service.yaml', style = wx.FD_SAVE ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        with open( dlg.GetPath(), 'wb' ) as f: f.write( yaml.safe_dump( ( service_identifier, credentials, extra_info ) ) )
                        
                    
                
            
        
    
    def EventOk( self, event ):
        
        try: self._CheckCurrentServiceIsValid()
        except Exception as e:
            
            wx.MessageBox( unicode( e ) )
            
            return
            
        
        all_pages = []
        
        all_pages.extend( self._local_ratings_like.GetNameToPageDict().values() )
        all_pages.extend( self._local_ratings_numerical.GetNameToPageDict().values() )
        all_pages.extend( self._tag_repositories.GetNameToPageDict().values() )
        all_pages.extend( self._file_repositories.GetNameToPageDict().values() )
        all_pages.extend( self._message_depots.GetNameToPageDict().values() )
        all_pages.extend( self._servers_admin.GetNameToPageDict().values() )
        
        for page in all_pages:
            
            if page.HasChanges(): self._edit_log.append( ( 'edit', ( page.GetOriginalServiceIdentifier(), page.GetInfo() ) ) )
            
        
        try:
            
            if len( self._edit_log ) > 0: wx.GetApp().Write( 'update_services', self._edit_log )
            
        except Exception as e: wx.MessageBox( 'Saving services to DB raised this error: ' + unicode( e ) )
        
        self.EndModal( wx.ID_OK )
        
    
    def EventPageChanging( self, event ):
        
        try: self._CheckCurrentServiceIsValid()
        except Exception as e:
            
            wx.MessageBox( unicode( e ) )
            
            event.Veto()
            
        
    
    def EventRemove( self, event ):
        
        services_listbook = self._listbook.GetCurrentPage()
        
        service_panel = services_listbook.GetCurrentPage()
        
        if service_panel is not None:
            
            service_identifier = service_panel.GetOriginalServiceIdentifier()
            
            self._edit_log.append( ( 'delete', service_identifier ) )
            
            services_listbook.DeleteCurrentPage()
            
        
    
    def EventServiceChanging( self, event ):
        
        try: self._CheckCurrentServiceIsValid()
        except Exception as e:
            
            wx.MessageBox( unicode( e ) )
            
            event.Veto()
            
        
    
    def Import( self, paths ):
        
        self._CheckCurrentServiceIsValid()
        
        for path in paths:
            
            try:
                
                with open( path, 'rb' ) as f: file = f.read()
                
                ( service_identifier, credentials, extra_info ) = yaml.safe_load( file )
                
                name = service_identifier.GetName()
                
                service_type = service_identifier.GetType()
                
                if service_type == HC.TAG_REPOSITORY: services_listbook = self._tag_repositories
                elif service_type == HC.FILE_REPOSITORY: services_listbook = self._file_repositories
                elif service_type == HC.MESSAGE_DEPOT: services_listbook = self._message_depots
                elif service_type == HC.SERVER_ADMIN: services_listbook = self._servers_admin
                
                self._listbook.SelectPage( services_listbook )
                
                if services_listbook.NameExists( name ):
                    
                    message = 'A service already exists with that name. Overwrite it?'
                    
                    with DialogYesNo( self, message ) as dlg:
                        
                        if dlg.ShowModal() == wx.ID_YES:
                            
                            page = services_listbook.GetNameToPageDict()[ name ]
                            
                            page.Update( service_identifier, credentials, extra_info )
                            
                        
                    
                else:
                    
                    self._edit_log.append( ( 'add', ( service_identifier, credentials, extra_info ) ) )
                    
                    page = self._Panel( services_listbook, service_identifier, credentials, extra_info )
                    
                    services_listbook.AddPage( page, name, select = True )
                    
                
            except:
                
                wx.MessageBox( traceback.format_exc() )
                
            
        
    
    class _Panel( wx.Panel ):
        
        def __init__( self, parent, service_identifier, credentials, extra_info ):
            
            wx.Panel.__init__( self, parent )
            
            self._service_identifier = service_identifier
            self._credentials = credentials
            self._extra_info = extra_info
            
            service_type = service_identifier.GetType()
            
            def InitialiseControls():
                
                self._service_panel = ClientGUICommon.StaticBox( self, 'service' )
                
                self._service_name = wx.TextCtrl( self._service_panel, value = self._service_identifier.GetName() )
                
                if service_type in HC.REMOTE_SERVICES: self._service_credentials = wx.TextCtrl( self._service_panel, value = self._credentials.GetConnectionString() )
                
                if service_type == HC.MESSAGE_DEPOT:
                    
                    ( identity_name, check_period, private_key, receive_anon ) = self._extra_info
                    
                    self._identity_name = wx.TextCtrl( self._service_panel, value = identity_name )
                    
                    self._check_period = wx.SpinCtrl( self._service_panel, min = 60, max = 86400 * 7 )
                    self._check_period.SetValue( check_period )
                    
                    self._private_key = wx.TextCtrl( self._service_panel, value = private_key, style = wx.TE_MULTILINE )
                    
                    self._receive_anon = wx.CheckBox( self._service_panel )
                    self._receive_anon.SetValue( receive_anon )
                    
                elif service_identifier.GetType() == HC.LOCAL_RATING_LIKE:
                    
                    ( like, dislike ) = self._extra_info
                    
                    self._like = wx.TextCtrl( self._service_panel, value = like )
                    self._dislike = wx.TextCtrl( self._service_panel, value = dislike )
                    
                elif service_identifier.GetType() == HC.LOCAL_RATING_NUMERICAL:
                    
                    ( lower, upper ) = self._extra_info
                    
                    self._lower = wx.SpinCtrl( self._service_panel, min = -2000, max = 2000 )
                    self._lower.SetValue( lower )
                    self._upper = wx.SpinCtrl( self._service_panel, min = -2000, max = 2000 )
                    self._upper.SetValue( upper )
                
            
            def InitialisePanel():
                
                self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
                
                vbox = wx.BoxSizer( wx.VERTICAL )
                
                gridbox = wx.FlexGridSizer( 0, 2 )
                
                gridbox.AddGrowableCol( 1, 1 )
                
                gridbox.AddF( wx.StaticText( self._service_panel, label='name' ), FLAGS_MIXED )
                gridbox.AddF( self._service_name, FLAGS_EXPAND_BOTH_WAYS )
                
                if service_type in HC.REMOTE_SERVICES:
                    
                    gridbox.AddF( wx.StaticText( self._service_panel, label='credentials' ), FLAGS_MIXED )
                    gridbox.AddF( self._service_credentials, FLAGS_EXPAND_BOTH_WAYS )
                    
                
                if service_type == HC.MESSAGE_DEPOT:
                    
                    gridbox.AddF( wx.StaticText( self._service_panel, label='identity name' ), FLAGS_MIXED )
                    gridbox.AddF( self._identity_name, FLAGS_EXPAND_BOTH_WAYS )
                    
                    gridbox.AddF( wx.StaticText( self._service_panel, label='update period' ), FLAGS_MIXED )
                    gridbox.AddF( self._check_period, FLAGS_EXPAND_BOTH_WAYS )
                    
                    gridbox.AddF( wx.StaticText( self._service_panel, label='private key' ), FLAGS_MIXED )
                    gridbox.AddF( self._private_key, FLAGS_EXPAND_BOTH_WAYS )
                    
                    gridbox.AddF( wx.StaticText( self._service_panel, label='receive messages from Anonymous?' ), FLAGS_MIXED )
                    gridbox.AddF( self._receive_anon, FLAGS_EXPAND_BOTH_WAYS )
                    
                elif service_identifier.GetType() == HC.LOCAL_RATING_LIKE:
                    
                    gridbox.AddF( wx.StaticText( self._service_panel, label='like' ), FLAGS_MIXED )
                    gridbox.AddF( self._like, FLAGS_EXPAND_BOTH_WAYS )
                    
                    gridbox.AddF( wx.StaticText( self._service_panel, label='dislike' ), FLAGS_MIXED )
                    gridbox.AddF( self._dislike, FLAGS_EXPAND_BOTH_WAYS )
                    
                elif service_identifier.GetType() == HC.LOCAL_RATING_NUMERICAL:
                    
                    gridbox.AddF( wx.StaticText( self._service_panel, label='lower limit' ), FLAGS_MIXED )
                    gridbox.AddF( self._lower, FLAGS_EXPAND_BOTH_WAYS )
                    
                    gridbox.AddF( wx.StaticText( self._service_panel, label='upper limit' ), FLAGS_MIXED )
                    gridbox.AddF( self._upper, FLAGS_EXPAND_BOTH_WAYS )
                    
                
                self._service_panel.AddF( gridbox, FLAGS_EXPAND_SIZER_BOTH_WAYS )
                
                vbox.AddF( self._service_panel, FLAGS_EXPAND_BOTH_WAYS )
                
                self.SetSizer( vbox )
                
            
            InitialiseControls()
            
            InitialisePanel()
            
        
        def GetInfo( self ):
            
            service_key = self._service_identifier.GetServiceKey()
            
            service_type = self._service_identifier.GetType()
            
            name = self._service_name.GetValue()
            
            if name == '': raise Exception( 'Please enter a name' )
            
            service_identifier = HC.ClientServiceIdentifier( service_key, service_type, name )
            
            if service_type in HC.REMOTE_SERVICES:
                
                connection_string = self._service_credentials.GetValue()
                
                if connection_string == '': raise Exception( 'Please enter some credentials' )
                
                if '@' in connection_string:
                    
                    try: ( access_key, address ) = connection_string.split( '@' )
                    except: raise Exception( 'Could not parse those credentials - no \'@\' symbol!' )
                    
                    try: access_key = access_key.decode( 'hex' )
                    except: raise Exception( 'Could not parse those credentials - could not understand access key!' )
                    
                    try: ( host, port ) = address.split( ':' )
                    except: raise Exception( 'Could not parse those credentials - no \':\' symbol!' )
                    
                    try: port = int( port )
                    except: raise Exception( 'Could not parse those credentials - could not understand the port!' )
                    
                    credentials = CC.Credentials( host, port, access_key )
                    
                else:
                    
                    try: ( host, port ) = connection_string.split( ':' )
                    except: raise Exception( 'Could not parse those credentials - no \':\' symbol!' )
                    
                    try: port = int( port )
                    except: raise Exception( 'Could not parse those credentials - could not understand the port!' )
                    
                    credentials = CC.Credentials( host, port )
                    
                
            else: credentials = None
            
            if service_type == HC.MESSAGE_DEPOT: extra_info = ( self._identity_name.GetValue(), self._check_period.GetValue(), self._private_key.GetValue(), self._receive_anon.GetValue() )
            elif service_type == HC.LOCAL_RATING_LIKE: extra_info = ( self._like.GetValue(), self._dislike.GetValue() )
            elif service_type == HC.LOCAL_RATING_NUMERICAL:
                
                ( lower, upper ) = ( self._lower.GetValue(), self._upper.GetValue() )
                
                if upper < lower: upper = lower + 1
                
                extra_info = ( lower, upper )
                
            else: extra_info = None
            
            return ( service_identifier, credentials, extra_info )
            
        
        def HasChanges( self ):
            
            ( service_identifier, credentials, extra_info ) = self.GetInfo()
            
            if service_identifier != self._service_identifier: return True
            
            if credentials != self._credentials: return True
            
            if extra_info != self._extra_info: return True
            
            return False
            
        
        def GetOriginalServiceIdentifier( self ): return self._service_identifier
        
        def Update( self, service_identifier, credentials, extra_info ):
            
            service_type = service_identifier.GetType()
            
            self._service_name.SetValue( service_identifier.GetName() )
            
            if service_type in HC.REMOTE_SERVICES: self._service_credentials.SetValue( credentials.GetConnectionString() )
            
            if service_type == HC.MESSAGE_DEPOT:
                
                if len( extra_info ) == 3:
                    ( identity_name, check_period, private_key ) = extra_info
                    receive_anon = True
                else: ( identity_name, check_period, private_key, receive_anon ) = extra_info
                
                self._identity_name.SetValue( identity_name )
                
                self._check_period.SetValue( check_period )
                
                self._private_key.SetValue( private_key )
                
                self._receive_anon.SetValue( receive_anon )
                
            elif service_type == HC.LOCAL_RATING_LIKE:
                
                ( like, dislike ) = extra_info
                
                self._like.SetValue( like )
                self._dislike.SetValue( dislike )
                
            elif service_type == HC.LOCAL_RATING_NUMERICAL:
                
                ( lower, upper ) = extra_info
                
                self._lower.SetValue( lower )
                self._upper.SetValue( upper )
                
            
        
    
class DialogManageTagServicePrecedence( Dialog ):
    
    def __init__( self, parent ):
        
        def InitialiseControls():
            
            message = 'When services dispute over a file\'s tags,' + os.linesep + 'higher services will overrule those below.'
            
            self._explain = wx.StaticText( self, label = message )
            
            self._tag_services = wx.ListBox( self )
            
            tag_service_precedence = wx.GetApp().Read( 'tag_service_precedence' )
            
            for service_identifier in tag_service_precedence:
                
                name = service_identifier.GetName()
                
                self._tag_services.Append( name, service_identifier )
                
            
            self._up = wx.Button( self, label = u'\u2191' )
            self._up.Bind( wx.EVT_BUTTON, self.EventUp )
            
            self._down = wx.Button( self, label = u'\u2193' )
            self._down.Bind( wx.EVT_BUTTON, self.EventDown )
            
            self._apply = wx.Button( self, label='apply' )
            self._apply.Bind( wx.EVT_BUTTON, self.EventOK )
            self._apply.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label='cancel' )
            self._cancel.Bind( wx.EVT_BUTTON, self.EventCancel )
            self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
            
        
        def InitialisePanel():
            
            updown_vbox = wx.BoxSizer( wx.VERTICAL )
            
            updown_vbox.AddF( self._up, FLAGS_MIXED )
            updown_vbox.AddF( self._down, FLAGS_MIXED )
            
            main_hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            main_hbox.AddF( self._tag_services, FLAGS_EXPAND_BOTH_WAYS )
            main_hbox.AddF( updown_vbox, FLAGS_MIXED )
            
            buttons = wx.BoxSizer( wx.HORIZONTAL )
            
            buttons.AddF( self._apply, FLAGS_SMALL_INDENT )
            buttons.AddF( self._cancel, FLAGS_SMALL_INDENT )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( self._explain, FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( main_hbox, FLAGS_EXPAND_SIZER_BOTH_WAYS )
            vbox.AddF( buttons, FLAGS_BUTTON_SIZERS )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            if y < 400: y = 400
            
            self.SetInitialSize( ( x, y ) )
            
        
        Dialog.__init__( self, parent, 'manage tag service precedence' )
        
        InitialiseControls()
        
        InitialisePanel()
        
    
    def EventCancel( self, event ): self.EndModal( wx.ID_CANCEL )
    
    def EventOK( self, event ):
        
        try:
            
            service_identifiers = [ self._tag_services.GetClientData( i ) for i in range( self._tag_services.GetCount() ) ]
            
            wx.GetApp().Write( 'set_tag_service_precedence', service_identifiers )
            
        except Exception as e: wx.MessageBox( 'Something went wrong when trying to save tag service precedence to the database: ' + unicode( e ) )
        
        self.EndModal( wx.ID_OK )
        
    
    def EventUp( self, event ):
        
        selection = self._tag_services.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            if selection > 0:
                
                service_identifier = self._tag_services.GetClientData( selection )
                
                name = service_identifier.GetName()
                
                self._tag_services.Delete( selection )
                
                self._tag_services.Insert( name, selection - 1, service_identifier )
                
                self._tag_services.Select( selection - 1 )
                
            
        
    
    def EventDown( self, event ):
        
        selection = self._tag_services.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            if selection + 1 < self._tag_services.GetCount():
                
                service_identifier = self._tag_services.GetClientData( selection )
                
                name = service_identifier.GetName()
                
                self._tag_services.Delete( selection )
                
                self._tag_services.Insert( name, selection + 1, service_identifier )
                
                self._tag_services.Select( selection + 1 )
                
            
        
    
class DialogManageTags( Dialog ):
    
    def __init__( self, parent, file_service_identifier, media ):
        
        def InitialiseControls():
            
            self._tag_repositories = ClientGUICommon.ListBook( self )
            self._tag_repositories.Bind( wx.EVT_NOTEBOOK_PAGE_CHANGED, self.EventServiceChanged )
            
            service_identifiers = wx.GetApp().Read( 'service_identifiers', ( HC.TAG_REPOSITORY, ) )
            
            for service_identifier in list( service_identifiers ) + [ CC.LOCAL_TAG_SERVICE_IDENTIFIER ]:
                
                service_type = service_identifier.GetType()
                
                page_info = ( self._Panel, ( self._tag_repositories, self._file_service_identifier, service_identifier, media ), {} )
                
                name = service_identifier.GetName()
                
                self._tag_repositories.AddPage( page_info, name )
                
            
            default_tag_repository = self._options[ 'default_tag_repository' ]
            
            self._tag_repositories.Select( default_tag_repository.GetName() )
            
            self._apply = wx.Button( self, label='Apply' )
            self._apply.Bind( wx.EVT_BUTTON, self.EventOk )
            self._apply.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label='Cancel' )
            self._cancel.Bind( wx.EVT_BUTTON, self.EventCancel )
            self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
            
        
        def InitialisePanel():
            
            buttonbox = wx.BoxSizer( wx.HORIZONTAL )
            
            buttonbox.AddF( self._apply, FLAGS_MIXED )
            buttonbox.AddF( self._cancel, FLAGS_MIXED )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( self._tag_repositories, FLAGS_EXPAND_BOTH_WAYS )
            vbox.AddF( buttonbox, FLAGS_BUTTON_SIZERS )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x + 200, 500 ) )
            
        
        self._file_service_identifier = file_service_identifier
        self._hashes = HC.IntelligentMassUnion( ( m.GetHashes() for m in media ) )
        
        Dialog.__init__( self, parent, 'manage tags for ' + HC.ConvertIntToPrettyString( len( self._hashes ) ) + ' files' )
        
        InitialiseControls()
        
        InitialisePanel()
        
        self.Bind( wx.EVT_MENU, self.EventMenu )
        
        self.RefreshAcceleratorTable()
        
    
    def _SetSearchFocus( self ):
        
        page = self._tag_repositories.GetCurrentPage()
        
        page.SetTagBoxFocus()
        
    
    def EventCancel( self, event ): self.EndModal( wx.ID_CANCEL )
    
    def EventMenu( self, event ):
        
        action = CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetAction( event.GetId() )
        
        if action is not None:
            
            ( command, data ) = action
            
            if command == 'manage_tags': self.EventCancel( event )
            elif command == 'set_search_focus': self._SetSearchFocus()
            elif command == 'ok': self.EventOk( event )
            else: event.Skip()
            
        
    
    def EventOk( self, event ):
        
        try:
            
            content_updates = []
            
            for page in self._tag_repositories.GetNameToPageDict().values():
                
                if page.HasChanges():
                    
                    service_identifier = page.GetServiceIdentifier()
                    
                    edit_log = page.GetEditLog()
                    
                    content_updates.append( HC.ContentUpdate( CC.CONTENT_UPDATE_EDIT_LOG, service_identifier, self._hashes, info = edit_log ) )
                    
                
            
            if len( content_updates ) > 0: wx.GetApp().Write( 'content_updates', content_updates )
            
        except Exception as e: wx.MessageBox( 'Saving pending mapping changes to DB raised this error: ' + unicode( e ) )
        
        self.EndModal( wx.ID_OK )
        
    
    def EventServiceChanged( self, event ):
        
        page = self._tag_repositories.GetCurrentPage()
        
        wx.CallAfter( page.SetTagBoxFocus )
        
    
    def RefreshAcceleratorTable( self ):
        
        interested_actions = [ 'manage_tags', 'set_search_focus' ]
        
        entries = []
        
        for ( modifier, key_dict ) in self._options[ 'shortcuts' ].items(): entries.extend( [ ( modifier, key, CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( action ) ) for ( key, action ) in key_dict.items() if action in interested_actions ] )
        
        self.SetAcceleratorTable( wx.AcceleratorTable( entries ) )
        
    
    class _Panel( wx.Panel ):
        
        def __init__( self, parent, file_service_identifier, tag_service_identifier, media ):
            
            def InitialiseControls():
                
                self._tags_box = ClientGUICommon.TagsBoxManage( self, self.AddTag, self._current_tags, self._deleted_tags, self._pending_tags, self._petitioned_tags )
                
                self._add_tag_box = ClientGUICommon.AutoCompleteDropdownTagsWrite( self, self.AddTag, self._file_service_identifier, self._tag_service_identifier )
                
                self._show_deleted_tags = wx.CheckBox( self, label='Show deleted tags' )
                self._show_deleted_tags.Bind( wx.EVT_CHECKBOX, self.EventShowDeletedTags )
                
                self._modify_mappers = wx.Button( self, label='Modify mappers' )
                self._modify_mappers.Bind( wx.EVT_BUTTON, self.EventModify )
                
                self._copy_tags = wx.Button( self, label = 'copy tags' )
                self._copy_tags.Bind( wx.EVT_BUTTON, self.EventCopyTags )
                
                self._paste_tags = wx.Button( self, label = 'paste tags' )
                self._paste_tags.Bind( wx.EVT_BUTTON, self.EventPasteTags )
                
                if self._i_am_local_tag_service:
                    
                    self._show_deleted_tags.Hide()
                    self._modify_mappers.Hide()
                    
                else:
                    
                    if not self._account.HasPermission( HC.POST_DATA ): self._add_tag_box.Hide()
                    if not self._account.HasPermission( HC.MANAGE_USERS ): self._modify_mappers.Hide()
                    
                
            
            def InitialisePanel():
                
                self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
                
                special_hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                special_hbox.AddF( self._show_deleted_tags, FLAGS_MIXED )
                special_hbox.AddF( self._modify_mappers, FLAGS_MIXED )
                
                copy_paste_hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                copy_paste_hbox.AddF( self._copy_tags, FLAGS_MIXED )
                copy_paste_hbox.AddF( self._paste_tags, FLAGS_MIXED )
                
                vbox = wx.BoxSizer( wx.VERTICAL )
                
                vbox.AddF( self._tags_box, FLAGS_EXPAND_BOTH_WAYS )
                vbox.AddF( self._add_tag_box, FLAGS_EXPAND_PERPENDICULAR )
                vbox.AddF( copy_paste_hbox, FLAGS_BUTTON_SIZERS )
                vbox.AddF( special_hbox, FLAGS_BUTTON_SIZERS )
                
                self.SetSizer( vbox )
                
            
            wx.Panel.__init__( self, parent )
            
            self._file_service_identifier = file_service_identifier
            self._tag_service_identifier = tag_service_identifier
            
            self._i_am_local_tag_service = self._tag_service_identifier.GetType() == HC.LOCAL_TAG
            
            self._edit_log = []
            
            if not self._i_am_local_tag_service:
                
                service = wx.GetApp().Read( 'service', tag_service_identifier )
                
                self._account = service.GetAccount()
                
            
            ( self._current_tags, self._deleted_tags, self._pending_tags, self._petitioned_tags ) = CC.MediaIntersectCDPPTagServiceIdentifiers( media, tag_service_identifier )
            
            self._current_tags.sort()
            self._pending_tags.sort()
            
            InitialiseControls()
            
            InitialisePanel()
            
        
        def AddTag( self, tag ):
            
            if tag is None: wx.PostEvent( self, wx.CommandEvent( commandType = wx.wxEVT_COMMAND_MENU_SELECTED, winid = CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'ok' ) ) )
            else:
                
                if self._i_am_local_tag_service:
                    
                    if tag in self._pending_tags:
                        
                        self._pending_tags.remove( tag )
                        
                        self._tags_box.RescindPend( tag )
                        
                    elif tag in self._petitioned_tags:
                        
                        self._petitioned_tags.remove( tag )
                        
                        self._tags_box.RescindPetition( tag )
                        
                    elif tag in self._current_tags:
                        
                        self._petitioned_tags.append( tag )
                        
                        self._tags_box.PetitionTag( tag )
                        
                    else:
                        
                        self._pending_tags.append( tag )
                        
                        self._tags_box.PendTag( tag )
                        
                    
                    self._edit_log = []
                    
                    self._edit_log.extend( [ ( CC.CONTENT_UPDATE_ADD, tag ) for tag in self._pending_tags ] )
                    self._edit_log.extend( [ ( CC.CONTENT_UPDATE_DELETE, tag ) for tag in self._petitioned_tags ] )
                    
                else:
                    
                    if tag in self._pending_tags:
                        
                        self._pending_tags.remove( tag )
                        
                        self._tags_box.RescindPend( tag )
                        
                        self._edit_log.append( ( CC.CONTENT_UPDATE_RESCIND_PENDING, tag ) )
                        
                    elif tag in self._petitioned_tags:
                        
                        self._petitioned_tags.remove( tag )
                        
                        self._tags_box.RescindPetition( tag )
                        
                        self._edit_log.append( ( CC.CONTENT_UPDATE_RESCIND_PETITION, tag ) )
                        
                    elif tag in self._current_tags:
                        
                        if self._account.HasPermission( HC.RESOLVE_PETITIONS ):
                            
                            self._edit_log.append( ( CC.CONTENT_UPDATE_PETITION, ( tag, 'admin' ) ) )
                            
                            self._petitioned_tags.append( tag )
                            
                            self._tags_box.PetitionTag( tag )
                            
                        elif self._account.HasPermission( HC.POST_PETITIONS ):
                            
                            message = 'Enter a reason for this tag to be removed. A janitor will review your petition.'
                            
                            with wx.TextEntryDialog( self, message ) as dlg:
                                
                                if dlg.ShowModal() == wx.ID_OK:
                                    
                                    self._edit_log.append( ( CC.CONTENT_UPDATE_PETITION, ( tag, dlg.GetValue() ) ) )
                                    
                                    self._petitioned_tags.append( tag )
                                    
                                    self._tags_box.PetitionTag( tag )
                                    
                                
                            
                        
                    elif tag in self._deleted_tags:
                        
                        if self._account.HasPermission( HC.RESOLVE_PETITIONS ):
                            
                            self._edit_log.append( ( CC.CONTENT_UPDATE_PENDING, tag ) )
                            
                            self._pending_tags.append( tag )
                            
                            self._tags_box.PendTag( tag )
                            
                        
                    else:
                        
                        self._edit_log.append( ( CC.CONTENT_UPDATE_PENDING, tag ) )
                        
                        self._pending_tags.append( tag )
                        
                        self._tags_box.PendTag( tag )
                        
                    
                
            
        
        def EventCopyTags( self, event ):
            
            if wx.TheClipboard.Open():
                
                tags = self._current_tags + self._pending_tags
                
                text = yaml.safe_dump( tags )
                
                data = wx.TextDataObject( text )
                
                wx.TheClipboard.SetData( data )
                
                wx.TheClipboard.Close()
                
            else: wx.MessageBox( 'I could not get permission to access the clipboard.' )
            
        
        def EventModify( self, event ):
            
            tag = self._tags_box.GetSelectedTag()
            
            if tag is not None and tag in self._current_tags or tag in self._petitioned_tags:
                
                subject_identifiers = [ HC.AccountIdentifier( hash = hash, tag = tag ) for hash in self._hashes ]
                
                try:
                    
                    with DialogModifyAccounts( self, self._tag_service_identifier, subject_identifiers ) as dlg: dlg.ShowModal()
                    
                except Exception as e: wx.MessageBox( unicode( e ) )
                
            
        
        def EventPasteTags( self, event ):
            
            if wx.TheClipboard.Open():
                
                data = wx.TextDataObject()
                
                wx.TheClipboard.GetData( data )
                
                wx.TheClipboard.Close()
                
                text = data.GetText()
                
                try:
                    
                    tags = yaml.safe_load( text )
                    
                    tags = [ tag for tag in tags if tag not in self._current_tags and tag not in self._pending_tags ]
                    
                    for tag in tags: self.AddTag( tag )
                    
                except: wx.MessageBox( 'I could not understand what was in the clipboard' )
                
            else: wx.MessageBox( 'I could not get permission to access the clipboard.' )
            
        
        def EventShowDeletedTags( self, event ): self._tags_box.SetShowDeletedTags( self._show_deleted_tags.GetValue() )
        
        def EventTagsBoxAction( self, event ):
            
            tag = self._tags_box.GetSelectedTag()
            
            if tag is not None: self.AddTag( tag )
            
        
        def GetEditLog( self ): return self._edit_log
        
        def GetServiceIdentifier( self ): return self._tag_service_identifier
        
        def HasChanges( self ): return len( self._edit_log ) > 0
        
        def SetTagBoxFocus( self ):
            
            if self._i_am_local_tag_service or self._account.HasPermission( HC.POST_DATA ): self._add_tag_box.SetFocus()
            
        
    
class DialogMessage( Dialog ):
    
    def __init__( self, parent, message, ok_label = 'ok' ):
        
        def InitialiseControls():
            
            self._ok = wx.Button( self, id = wx.ID_CANCEL, label = ok_label )
            self._ok.Bind( wx.EVT_BUTTON, self.EventOk )
            self._ok.SetForegroundColour( ( 0, 128, 0 ) )
            
        
        def InitialisePanel():
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            text = wx.StaticText( self, label = str( message ) )
            
            text.Wrap( 480 )
            
            vbox.AddF( text, FLAGS_BIG_INDENT )
            vbox.AddF( self._ok, FLAGS_BUTTON_SIZERS )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
        
        Dialog.__init__( self, parent, 'message', position = 'center' )
        
        InitialiseControls()
        
        InitialisePanel()
        
    
    def EventOk( self, event ): self.EndModal( wx.ID_OK )
    
class DialogModifyAccounts( Dialog ):
    
    def __init__( self, parent, service_identifier, subject_identifiers ):
        
        def InitialiseControls():
            
            connection = self._service.GetConnection()
            
            if len( self._subject_identifiers ) == 1:
                
                ( subject_identifier, ) = self._subject_identifiers
                
                subject_string = connection.Get( 'account_info', subject_identifier = subject_identifier )
                
            else: subject_string = 'modifying ' + HC.ConvertIntToPrettyString( len( self._subject_identifiers ) ) + ' accounts'
            
            self._account_info_panel = ClientGUICommon.StaticBox( self, 'account info' )
            
            self._subject_text = wx.StaticText( self._account_info_panel, label = str( subject_string ) )
            
            account_types = connection.Get( 'account_types' )
            
            self._account_types_panel = ClientGUICommon.StaticBox( self, 'account types' )
            
            self._account_types = wx.Choice( self._account_types_panel )
            
            for account_type in account_types: self._account_types.Append( account_type.ConvertToString(), account_type )
            
            self._account_types.SetSelection( 0 )
            
            self._account_types_ok = wx.Button( self._account_types_panel, label = 'Ok' )
            self._account_types_ok.Bind( wx.EVT_BUTTON, self.EventChangeAccountType )
            
            self._expiration_panel = ClientGUICommon.StaticBox( self, 'change expiration' )
            
            self._add_to_expires = wx.Choice( self._expiration_panel )
            
            for ( string, value ) in HC.expirations:
                
                if value is not None: self._add_to_expires.Append( string, value ) # don't want 'add no limit'
                
            self._add_to_expires.SetSelection( 1 ) # three months
            
            self._add_to_expires_ok = wx.Button( self._expiration_panel, label = 'Ok' )
            self._add_to_expires_ok.Bind( wx.EVT_BUTTON, self.EventAddToExpires )
            
            self._set_expires = wx.Choice( self._expiration_panel )
            for ( string, value ) in HC.expirations: self._set_expires.Append( string, value )
            self._set_expires.SetSelection( 1 ) # three months
            
            self._set_expires_ok = wx.Button( self._expiration_panel, label = 'Ok' )
            self._set_expires_ok.Bind( wx.EVT_BUTTON, self.EventSetExpires )
            
            self._ban_panel = ClientGUICommon.StaticBox( self, 'bans' )
            
            self._ban = wx.Button( self._ban_panel, label = 'ban user' )
            self._ban.Bind( wx.EVT_BUTTON, self.EventBan )        
            self._ban.SetBackgroundColour( ( 255, 0, 0 ) )
            self._ban.SetForegroundColour( ( 255, 255, 0 ) )
            
            self._superban = wx.Button( self._ban_panel, label = 'ban user and delete every contribution they have ever made' )
            self._superban.Bind( wx.EVT_BUTTON, self.EventSuperban )        
            self._superban.SetBackgroundColour( ( 255, 0, 0 ) )
            self._superban.SetForegroundColour( ( 255, 255, 0 ) )
            
            self._exit = wx.Button( self, id = wx.ID_CANCEL, label='Exit' )
            self._exit.Bind( wx.EVT_BUTTON, lambda event: self.EndModal( wx.ID_OK ) )
            
            if not self._service.GetAccount().HasPermission( HC.GENERAL_ADMIN ):
                
                self._account_types_ok.Disable()
                self._add_to_expires_ok.Disable()
                self._set_expires_ok.Disable()
                
            
        
        def InitialisePanel():
            
            self._account_info_panel.AddF( self._subject_text, FLAGS_EXPAND_PERPENDICULAR )
            
            account_types_hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            account_types_hbox.AddF( self._account_types, FLAGS_MIXED )
            account_types_hbox.AddF( self._account_types_ok, FLAGS_MIXED )
            
            self._account_types_panel.AddF( account_types_hbox, FLAGS_EXPAND_PERPENDICULAR )
            
            add_to_expires_box = wx.BoxSizer( wx.HORIZONTAL )
            
            add_to_expires_box.AddF( wx.StaticText( self._expiration_panel, label = 'add to expires: ' ), FLAGS_MIXED )
            add_to_expires_box.AddF( self._add_to_expires, FLAGS_EXPAND_BOTH_WAYS )
            add_to_expires_box.AddF( self._add_to_expires_ok, FLAGS_MIXED )
            
            set_expires_box = wx.BoxSizer( wx.HORIZONTAL )
            
            set_expires_box.AddF( wx.StaticText( self._expiration_panel, label = 'set expires to: ' ), FLAGS_MIXED )
            set_expires_box.AddF( self._set_expires, FLAGS_EXPAND_BOTH_WAYS )
            set_expires_box.AddF( self._set_expires_ok, FLAGS_MIXED )
            
            self._expiration_panel.AddF( add_to_expires_box, FLAGS_EXPAND_PERPENDICULAR )
            self._expiration_panel.AddF( set_expires_box, FLAGS_EXPAND_PERPENDICULAR )
            
            self._ban_panel.AddF( self._ban, FLAGS_EXPAND_PERPENDICULAR )
            self._ban_panel.AddF( self._superban, FLAGS_EXPAND_PERPENDICULAR )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            vbox.AddF( self._account_info_panel, FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._account_types_panel, FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._expiration_panel, FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._ban_panel, FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._exit, FLAGS_BUTTON_SIZERS )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
        
        Dialog.__init__( self, parent, 'modify account' )
        
        self._service = wx.GetApp().Read( 'service', service_identifier )
        self._subject_identifiers = set( subject_identifiers )
        
        InitialiseControls()
        
        InitialisePanel()
        
    
    def _DoModification( self, action, **kwargs ):
        
        try:
            
            connection = self._service.GetConnection()
            
            kwargs[ 'subject_identifiers' ] = list( self._subject_identifiers )
            kwargs[ 'action' ] = action
            
            connection.Post( 'account_modification', **kwargs )
            
            if len( self._subject_identifiers ) == 1:
                
                ( subject_identifier, ) = self._subject_identifiers
                
                self._subject_text.SetLabel( str( connection.Get( 'account_info', subject_identifier = subject_identifier ) ) )
                
            
        except Exception as e: wx.MessageBox( unicode( e ) )
        
        if len( self._subject_identifiers ) > 1: wx.MessageBox( 'Done!' )
        
    
    def EventAddToExpires( self, event ): self._DoModification( HC.ADD_TO_EXPIRES, expiration = self._add_to_expires.GetClientData( self._add_to_expires.GetSelection() ) )
    
    def EventBan( self, event ):
        
        with wx.TextEntryDialog( self, 'Enter reason for the ban' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK: self._DoModification( HC.BAN, reason = dlg.GetValue() )
            
        
    
    def EventChangeAccountType( self, event ): self._DoModification( HC.CHANGE_ACCOUNT_TYPE, title = self._account_types.GetClientData( self._account_types.GetSelection() ).GetTitle() )
    
    def EventSetExpires( self, event ): self._DoModification( HC.SET_EXPIRES, expiry = int( time.time() ) + self._set_expires.GetClientData( self._set_expires.GetSelection() ) )
    
    def EventSuperban( self, event ):
        
        with wx.TextEntryDialog( self, 'Enter reason for the superban' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK: self._DoModification( HC.SUPERBAN, reason = dlg.GetValue() )
            
        
    
class DialogNews( Dialog ):
    
    def __init__( self, parent, service_identifier ):
        
        def InitialiseControls():
            
            self._news = wx.TextCtrl( self, style=wx.TE_READONLY | wx.TE_MULTILINE )
            
            self._previous = wx.Button( self, label='<' )
            self._previous.Bind( wx.EVT_BUTTON, self.EventPrevious )
            
            self._news_position = wx.TextCtrl( self )
            
            self._next = wx.Button( self, label='>' )
            self._next.Bind( wx.EVT_BUTTON, self.EventNext )
            
            self._done = wx.Button( self, id = wx.ID_CANCEL, label='Done' )
            self._done.Bind( wx.EVT_BUTTON, self.EventOk )
            
        
        def InitialisePanel():
            
            self._newslist = wx.GetApp().Read( 'news', service_identifier )
            
            self._current_news_position = len( self._newslist )
            
            self._ShowNews()
            
            buttonbox = wx.BoxSizer( wx.HORIZONTAL )
            
            buttonbox.AddF( self._previous, FLAGS_MIXED )
            buttonbox.AddF( self._news_position, FLAGS_MIXED )
            buttonbox.AddF( self._next, FLAGS_MIXED )
            
            donebox = wx.BoxSizer( wx.HORIZONTAL )
            
            donebox.AddF( self._done, FLAGS_MIXED )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( self._news, FLAGS_EXPAND_BOTH_WAYS )
            vbox.AddF( buttonbox, FLAGS_BUTTON_SIZERS )
            vbox.AddF( donebox, FLAGS_BUTTON_SIZERS )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x + 200, 580 ) )
            
        
        Dialog.__init__( self, parent, 'news' )
        
        InitialiseControls()
        
        InitialisePanel()
        
    
    def _ShowNews( self ):
        
        if self._current_news_position == 0:
            
            self._news.SetValue( '' )
            
            self._news_position.SetValue( 'No News' )
            
        else:
            
            ( news, timestamp ) = self._newslist[ self._current_news_position - 1 ]
            
            self._news.SetValue( time.ctime( timestamp ) + ':' + os.linesep + os.linesep + news )
            
            self._news_position.SetValue( HC.ConvertIntToPrettyString( self._current_news_position ) + ' / ' + HC.ConvertIntToPrettyString( len( self._newslist ) ) )
            
        
    
    def EventNext( self, event ):
        
        if self._current_news_position < len( self._newslist ): self._current_news_position += 1
        
        self._ShowNews()
        
    
    def EventOk( self, event ): self.EndModal( wx.ID_OK )
    
    def EventPrevious( self, event ):
        
        if self._current_news_position > 1: self._current_news_position -= 1
        
        self._ShowNews()
        
    
class DialogPathsToTagsRegex( Dialog ):
    
    def __init__( self, parent, paths ):
        
        def InitialiseControls():
            
            self._tag_repositories = ClientGUICommon.ListBook( self )
            self._tag_repositories.Bind( wx.EVT_NOTEBOOK_PAGE_CHANGED, self.EventServiceChanged )
            
            services = wx.GetApp().Read( 'services', ( HC.TAG_REPOSITORY, ) )
            
            for service in services:
                
                account = service.GetAccount()
                
                if account.HasPermission( HC.POST_DATA ):
                    
                    service_identifier = service.GetServiceIdentifier()
                    
                    page_info = ( self._Panel, ( self._tag_repositories, service_identifier, paths ), {} )
                    
                    name = service_identifier.GetName()
                    
                    self._tag_repositories.AddPage( page_info, name )
                    
                
            
            page = self._Panel( self._tag_repositories, CC.LOCAL_TAG_SERVICE_IDENTIFIER, paths )
            
            name = CC.LOCAL_TAG_SERVICE_IDENTIFIER.GetName()
            
            self._tag_repositories.AddPage( page, name )
            
            default_tag_repository = self._options[ 'default_tag_repository' ]
            
            self._tag_repositories.Select( default_tag_repository.GetName() )
            
            self._add_button = wx.Button( self, label='Import Files' )
            self._add_button.Bind( wx.EVT_BUTTON, self.EventOK )
            self._add_button.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._close_button = wx.Button( self, id = wx.ID_CANCEL, label='Back to File Selection' )
            self._close_button.Bind( wx.EVT_BUTTON, self.EventCancel )
            self._close_button.SetForegroundColour( ( 128, 0, 0 ) )
            
        
        def InitialisePanel():
            
            buttons = wx.BoxSizer( wx.HORIZONTAL )
            
            buttons.AddF( self._add_button, FLAGS_SMALL_INDENT )
            buttons.AddF( self._close_button, FLAGS_SMALL_INDENT )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( self._tag_repositories, FLAGS_EXPAND_BOTH_WAYS )
            vbox.AddF( buttons, FLAGS_BUTTON_SIZERS )
            
            self.SetSizer( vbox )
            
            self.SetInitialSize( ( 980, 680 ) )
            
        
        Dialog.__init__( self, parent, 'path tagging' )
        
        self._paths = paths
        
        InitialiseControls()
        
        InitialisePanel()
        
        interested_actions = [ 'set_search_focus' ]
        
        entries = []
        
        for ( modifier, key_dict ) in self._options[ 'shortcuts' ].items(): entries.extend( [ ( modifier, key, CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( action ) ) for ( key, action ) in key_dict.items() if action in interested_actions ] )
        
        self.SetAcceleratorTable( wx.AcceleratorTable( entries ) )
        
        self.Bind( wx.EVT_MENU, self.EventMenu )
        
    
    def _SetSearchFocus( self ):
        
        page = self._tag_repositories.GetCurrentPage()
        
        page.SetTagBoxFocus()
        
    
    def EventCancel( self, event ): self.EndModal( wx.ID_CANCEL )
    
    def EventMenu( self, event ):
        
        action = CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetAction( event.GetId() )
        
        if action is not None:
            
            try:
                
                ( command, data ) = action
                
                if command == 'set_search_focus': self._SetSearchFocus()
                else: event.Skip()
                
            except Exception as e:
                
                wx.MessageBox( unicode( e ) )
                wx.MessageBox( traceback.format_exc() )
                
            
        
    
    def EventOK( self, event ): self.EndModal( wx.ID_OK )
    
    def EventServiceChanged( self, event ):
        
        page = self._tag_repositories.GetCurrentPage()
        
        wx.CallAfter( page.SetTagBoxFocus )
        
    
    def GetInfo( self ):
        
        paths_to_tags = {}
        
        try:
            
            for path in self._paths:
                
                all_tags = {}
                
                for page in self._tag_repositories.GetNameToPageDict().values():
                    
                    tags = page.GetTags( path )
                    
                    if len( tags ) > 0:
                        
                        service_identifier = page.GetServiceIdentifier()
                        
                        all_tags[ service_identifier ] = tags
                        
                    
                
                if len( all_tags ) > 0: paths_to_tags[ path ] = all_tags
                
            
        except Exception as e: wx.MessageBox( 'Saving pending mapping changes to DB raised this error: ' + unicode( e ) )
        
        return paths_to_tags
        
    
    class _Panel( wx.Panel ):
        
        ID_REGEX_WHITESPACE = 0
        ID_REGEX_NUMBER = 1
        ID_REGEX_ALPHANUMERIC = 2
        ID_REGEX_ANY = 3
        ID_REGEX_BEGINNING = 4
        ID_REGEX_END = 5
        ID_REGEX_0_OR_MORE_GREEDY = 6
        ID_REGEX_1_OR_MORE_GREEDY = 7
        ID_REGEX_0_OR_1_GREEDY = 8
        ID_REGEX_0_OR_MORE_MINIMAL = 9
        ID_REGEX_1_OR_MORE_MINIMAL = 10
        ID_REGEX_0_OR_1_MINIMAL = 11
        ID_REGEX_EXACTLY_M = 12
        ID_REGEX_M_TO_N_GREEDY = 13
        ID_REGEX_M_TO_N_MINIMAL = 14
        ID_REGEX_LOOKAHEAD = 15
        ID_REGEX_NEGATIVE_LOOKAHEAD = 16
        ID_REGEX_LOOKBEHIND = 17
        ID_REGEX_NEGATIVE_LOOKBEHIND = 18
        ID_REGEX_NUMBER_WITHOUT_ZEROES = 19
        ID_REGEX_NUMBER_EXT = 20
        ID_REGEX_AUTHOR = 21
        ID_REGEX_BACKSPACE = 22
        ID_REGEX_SET = 23
        ID_REGEX_NOT_SET = 24
        
        def __init__( self, parent, service_identifier, paths ):
            
            def InitialiseControls():
                
                self._paths_list = ClientGUICommon.SaneListCtrl( self, 300, [ ( 'path', 400 ), ( 'tags', -1 ) ] )
                
                self._paths_list.Bind( wx.EVT_LIST_ITEM_SELECTED, self.EventItemSelected )
                self._paths_list.Bind( wx.EVT_LIST_ITEM_DESELECTED, self.EventItemSelected )
                
                #
                
                self._quick_namespaces_panel = ClientGUICommon.StaticBox( self, 'quick namespaces' )
                
                self._page_regex = wx.TextCtrl( self._quick_namespaces_panel )
                self._chapter_regex = wx.TextCtrl( self._quick_namespaces_panel )
                self._volume_regex = wx.TextCtrl( self._quick_namespaces_panel )
                self._title_regex = wx.TextCtrl( self._quick_namespaces_panel )
                self._series_regex = wx.TextCtrl( self._quick_namespaces_panel )
                self._creator_regex = wx.TextCtrl( self._quick_namespaces_panel )
                
                self._update_button = wx.Button( self._quick_namespaces_panel, label='update' )
                self._update_button.Bind( wx.EVT_BUTTON, self.EventUpdate )
                
                self._regex_shortcuts = wx.Button( self._quick_namespaces_panel, label = 'regex shortcuts' )
                self._regex_shortcuts.Bind( wx.EVT_BUTTON, self.EventRegexShortcuts )
                
                self._regex_link = wx.HyperlinkCtrl( self._quick_namespaces_panel, id = -1, label = 'a good regex introduction', url = 'http://www.aivosto.com/vbtips/regex.html' )
                
                #
                
                self._regexes_panel = ClientGUICommon.StaticBox( self, 'regexes' )
                
                self._regexes = wx.ListBox( self._regexes_panel )
                self._regexes.Bind( wx.EVT_LISTBOX_DCLICK, self.EventRemoveRegex )
                
                self._regex_box = wx.TextCtrl( self._regexes_panel, style=wx.TE_PROCESS_ENTER )
                self._regex_box.Bind( wx.EVT_TEXT_ENTER, self.EventAddRegex )
                
                #
                
                self._tags_panel = ClientGUICommon.StaticBox( self, 'tags for all' )
                
                self._tags = ClientGUICommon.TagsBoxFlat( self._tags_panel, self.TagRemoved )
                
                self._tag_box = ClientGUICommon.AutoCompleteDropdownTagsWrite( self._tags_panel, self.AddTag, CC.LOCAL_FILE_SERVICE_IDENTIFIER, service_identifier )
                
                #
                
                self._single_tags_panel = ClientGUICommon.StaticBox( self, 'tags just for this file' )
                
                self._paths_to_single_tags = collections.defaultdict( list )
                
                self._single_tags = ClientGUICommon.TagsBoxFlat( self._single_tags_panel, self.SingleTagRemoved )
                
                self._single_tag_box = ClientGUICommon.AutoCompleteDropdownTagsWrite( self._single_tags_panel, self.AddTagSingle, CC.LOCAL_FILE_SERVICE_IDENTIFIER, service_identifier )
                self._single_tag_box.Disable()
                
                for path in self._paths:
                    
                    tags = self._GetTags( path )
                    
                    tags_string = ', '.join( tags )
                    
                    self._paths_list.Append( ( path, tags_string ), ( path, tags ) )
                    
                
            
            def InitialisePanel():
                
                gridbox = wx.FlexGridSizer( 0, 2 )
                
                gridbox.AddGrowableCol( 1, 1 )
                
                gridbox.AddF( wx.StaticText( self._quick_namespaces_panel, label='Page regex ' ), FLAGS_MIXED )
                gridbox.AddF( self._page_regex, FLAGS_EXPAND_BOTH_WAYS )
                gridbox.AddF( wx.StaticText( self._quick_namespaces_panel, label='Chapter regex ' ), FLAGS_MIXED )
                gridbox.AddF( self._chapter_regex, FLAGS_EXPAND_BOTH_WAYS )
                gridbox.AddF( wx.StaticText( self._quick_namespaces_panel, label='Volume regex ' ), FLAGS_MIXED )
                gridbox.AddF( self._volume_regex, FLAGS_EXPAND_BOTH_WAYS )
                gridbox.AddF( wx.StaticText( self._quick_namespaces_panel, label='Title regex ' ), FLAGS_MIXED )
                gridbox.AddF( self._title_regex, FLAGS_EXPAND_BOTH_WAYS )
                gridbox.AddF( wx.StaticText( self._quick_namespaces_panel, label='Series regex ' ), FLAGS_MIXED )
                gridbox.AddF( self._series_regex, FLAGS_EXPAND_BOTH_WAYS )
                gridbox.AddF( wx.StaticText( self._quick_namespaces_panel, label='Creator regex ' ), FLAGS_MIXED )
                gridbox.AddF( self._creator_regex, FLAGS_EXPAND_BOTH_WAYS )
                
                self._quick_namespaces_panel.AddF( gridbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
                self._quick_namespaces_panel.AddF( self._update_button, FLAGS_LONE_BUTTON )
                self._quick_namespaces_panel.AddF( self._regex_shortcuts, FLAGS_LONE_BUTTON )
                self._quick_namespaces_panel.AddF( self._regex_link, FLAGS_LONE_BUTTON )
                
                self._regexes_panel.AddF( self._regexes, FLAGS_EXPAND_BOTH_WAYS )
                self._regexes_panel.AddF( self._regex_box, FLAGS_EXPAND_PERPENDICULAR )
                
                self._tags_panel.AddF( self._tags, FLAGS_EXPAND_BOTH_WAYS )
                self._tags_panel.AddF( self._tag_box, FLAGS_EXPAND_PERPENDICULAR )
                
                self._single_tags_panel.AddF( self._single_tags, FLAGS_EXPAND_BOTH_WAYS )
                self._single_tags_panel.AddF( self._single_tag_box, FLAGS_EXPAND_PERPENDICULAR )
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( self._quick_namespaces_panel, FLAGS_EXPAND_BOTH_WAYS )
                hbox.AddF( self._regexes_panel, FLAGS_EXPAND_BOTH_WAYS )
                hbox.AddF( self._tags_panel, FLAGS_EXPAND_BOTH_WAYS )
                hbox.AddF( self._single_tags_panel, FLAGS_EXPAND_BOTH_WAYS )
                
                vbox = wx.BoxSizer( wx.VERTICAL )
                
                vbox.AddF( self._paths_list, FLAGS_EXPAND_BOTH_WAYS )
                vbox.AddF( hbox, FLAGS_EXPAND_SIZER_BOTH_WAYS )
                
                self.SetSizer( vbox )
                
            
            wx.Panel.__init__( self, parent )
            
            self._service_identifier = service_identifier
            self._paths = paths
            
            InitialiseControls()
            
            InitialisePanel()
            
            self.Bind( wx.EVT_MENU, self.EventMenu )
            
        
        
        def _GetTags( self, path ):
            
            tags = []
            
            tags.extend( self._tags.GetTags() )
            
            for regex in self._regexes.GetStrings():
                
                try:
                    
                    m = re.search( regex, path )
                    
                    if m is not None:
                        
                        match = m.group()
                        
                        if len( match ) > 0: tags.append( match )
                        
                    
                except: pass
                
            
            namespaced_regexes = []
            
            namespaced_regexes.append( ( self._page_regex, 'page:' ) )
            namespaced_regexes.append( ( self._chapter_regex, 'chapter:' ) )
            namespaced_regexes.append( ( self._volume_regex, 'volume:' ) )
            namespaced_regexes.append( ( self._title_regex, 'title:' ) )
            namespaced_regexes.append( ( self._series_regex, 'series:' ) )
            namespaced_regexes.append( ( self._creator_regex, 'creator:' ) )
            
            for ( control, prefix ) in namespaced_regexes:
                
                try:
                    
                    m = re.search( control.GetValue(), path )
                    
                    if m is not None:
                        
                        match = m.group()
                        
                        if len( match ) > 0: tags.append( prefix + match )
                        
                    
                except: pass
                
            
            if path in self._paths_to_single_tags: tags.extend( self._paths_to_single_tags[ path ] )
            
            tags = [ HC.CleanTag( tag ) for tag in tags ]
            
            return tags
            
        
        def _RefreshFileList( self ):
            
            for ( index, ( path, old_tags ) ) in enumerate( self._paths_list.GetClientData() ):
                
                # when doing regexes, make sure not to include '' results, same for system: and - started tags.
                
                tags = self._GetTags( path )
                
                if tags != old_tags:
                    
                    tags_string = ', '.join( tags )
                    
                    self._paths_list.UpdateRow( index, ( path, tags_string ), ( path, tags ) )
                    
                
            
        
        def AddTag( self, tag ):
            
            if tag is not None:
                
                self._tags.AddTag( tag )
                
                self._tag_box.Clear()
                
                self._RefreshFileList()
                
            
        
        def AddTagSingle( self, tag ):
            
            if tag is not None:
                
                self._single_tags.AddTag( tag )
                
                self._single_tag_box.Clear()
                
                indices = self._paths_list.GetAllSelected()
                
                for index in indices:
                    
                    ( path, old_tags ) = self._paths_list.GetClientData( index )
                    
                    if tag not in self._paths_to_single_tags[ path ]: self._paths_to_single_tags[ path ].append( tag )
                    
                
                self._RefreshFileList() # make this more clever
                
            
        
        def EventAddRegex( self, event ):
            
            regex = self._regex_box.GetValue()
            
            if regex != '':
                
                self._regexes.Append( regex )
                
                self._regex_box.Clear()
                
                self._RefreshFileList()
                
            
        
        def EventItemSelected( self, event ):
            
            single_tags = set()
            
            indices = self._paths_list.GetAllSelected()
            
            if len( indices ) > 0:
                
                for index in indices:
                    
                    path = self._paths_list.GetClientData( index )[0]
                    
                    if path in self._paths_to_single_tags: single_tags.update( self._paths_to_single_tags[ path ] )
                    
                
                self._single_tag_box.Enable()
                
            else: self._single_tag_box.Disable()
            
            single_tags = list( single_tags )
            
            single_tags.sort()
            
            self._single_tags.SetTags( single_tags )
            
        
        def EventMenu( self, event ):
            
            id = event.GetId()
            
            phrase = None
            
            if id == self.ID_REGEX_WHITESPACE: phrase = r'\s'
            elif id == self.ID_REGEX_NUMBER: phrase = r'\d'
            elif id == self.ID_REGEX_ALPHANUMERIC: phrase = r'\w'
            elif id == self.ID_REGEX_ANY: phrase = r'.'
            elif id == self.ID_REGEX_BACKSPACE: phrase = r'\\'
            elif id == self.ID_REGEX_BEGINNING: phrase = r'^'
            elif id == self.ID_REGEX_END: phrase = r'$'
            elif id == self.ID_REGEX_SET: phrase = r'[...]'
            elif id == self.ID_REGEX_NOT_SET: phrase = r'[^...]'
            elif id == self.ID_REGEX_0_OR_MORE_GREEDY: phrase = r'*'
            elif id == self.ID_REGEX_1_OR_MORE_GREEDY: phrase = r'+'
            elif id == self.ID_REGEX_0_OR_1_GREEDY: phrase = r'?'
            elif id == self.ID_REGEX_0_OR_MORE_MINIMAL: phrase = r'*?'
            elif id == self.ID_REGEX_1_OR_MORE_MINIMAL: phrase = r'+?'
            elif id == self.ID_REGEX_0_OR_1_MINIMAL: phrase = r'*'
            elif id == self.ID_REGEX_EXACTLY_M: phrase = r'{m}'
            elif id == self.ID_REGEX_M_TO_N_GREEDY: phrase = r'{m,n}'
            elif id == self.ID_REGEX_M_TO_N_MINIMAL: phrase = r'{m,n}?'
            elif id == self.ID_REGEX_LOOKAHEAD: phrase = r'(?=...)'
            elif id == self.ID_REGEX_NEGATIVE_LOOKAHEAD: phrase = r'(?!...)'
            elif id == self.ID_REGEX_LOOKBEHIND: phrase = r'(?<=...)'
            elif id == self.ID_REGEX_NEGATIVE_LOOKBEHIND: phrase = r'(?<!...)'
            elif id == self.ID_REGEX_NUMBER_WITHOUT_ZEROES: phrase = r'[1-9]+\d*'
            elif id == self.ID_REGEX_NUMBER_EXT: phrase = r'[1-9]+\d*(?=.{4}$)'
            elif id == self.ID_REGEX_AUTHOR: phrase = r'[^\\][\w\s]*(?=\s-)'
            else: event.Skip()
            
            if phrase is not None:
                
                if wx.TheClipboard.Open():
                    
                    data = wx.TextDataObject( phrase )
                    
                    wx.TheClipboard.SetData( data )
                    
                    wx.TheClipboard.Close()
                    
                else: wx.MessageBox( 'I could not get permission to access the clipboard.' )
                
            
        
        def EventRegexShortcuts( self, event ):
            
            menu = wx.Menu()
            
            menu.Append( -1, 'click on a phrase to copy to clipboard' )
            
            menu.AppendSeparator()
            
            menu.Append( self.ID_REGEX_WHITESPACE, r'whitespace character - \s' )
            menu.Append( self.ID_REGEX_NUMBER, r'number character - \d' )
            menu.Append( self.ID_REGEX_ALPHANUMERIC, r'alphanumeric or backspace character - \w' )
            menu.Append( self.ID_REGEX_ANY, r'any character - .' )
            menu.Append( self.ID_REGEX_BACKSPACE, r'backspace character - \\' )
            menu.Append( self.ID_REGEX_BEGINNING, r'beginning of line - ^' )
            menu.Append( self.ID_REGEX_END, r'end of line - $' )
            menu.Append( self.ID_REGEX_SET, r'any of these - [...]' )
            menu.Append( self.ID_REGEX_NOT_SET, r'anything other than these - [^...]' )
            
            menu.AppendSeparator()
            
            menu.Append( self.ID_REGEX_0_OR_MORE_GREEDY, r'0 or more matches, consuming as many as possible - *' )
            menu.Append( self.ID_REGEX_1_OR_MORE_GREEDY, r'1 or more matches, consuming as many as possible - +' )
            menu.Append( self.ID_REGEX_0_OR_1_GREEDY, r'0 or 1 matches, preferring 1 - ?' )
            menu.Append( self.ID_REGEX_0_OR_MORE_MINIMAL, r'0 or more matches, consuming as few as possible - *?' )
            menu.Append( self.ID_REGEX_1_OR_MORE_MINIMAL, r'1 or more matches, consuming as few as possible - +?' )
            menu.Append( self.ID_REGEX_0_OR_1_MINIMAL, r'0 or 1 matches, preferring 0 - *' )
            menu.Append( self.ID_REGEX_EXACTLY_M, r'exactly m matches - {m}' )
            menu.Append( self.ID_REGEX_M_TO_N_GREEDY, r'm to n matches, consuming as many as possible - {m,n}' )
            menu.Append( self.ID_REGEX_M_TO_N_MINIMAL, r'm to n matches, consuming as few as possible - {m,n}?' )
            
            menu.AppendSeparator()
            
            menu.Append( self.ID_REGEX_LOOKAHEAD, r'the next characters are: (non-consuming) - (?=...)' )
            menu.Append( self.ID_REGEX_NEGATIVE_LOOKAHEAD, r'the next characters are not: (non-consuming) - (?!...)' )
            menu.Append( self.ID_REGEX_LOOKBEHIND, r'the previous characters are: (non-consuming) - (?<=...)' )
            menu.Append( self.ID_REGEX_NEGATIVE_LOOKBEHIND, r'the previous characters are not: (non-consuming) - (?<!...)' )
            
            menu.AppendSeparator()
            
            menu.Append( self.ID_REGEX_NUMBER_WITHOUT_ZEROES, r'0074 -> 74 - [1-9]+\d*' )
            menu.Append( self.ID_REGEX_NUMBER_EXT, r'...0074.jpg -> 74 - [1-9]+\d*(?=.{4}$)' )
            menu.Append( self.ID_REGEX_AUTHOR, r'E:\my collection\author name - v4c1p0074.jpg -> author name - [^\\][\w\s]*(?=\s-)' )
            
            self.PopupMenu( menu )
            
            menu.Destroy()
            
        
        def EventRemoveRegex( self, event ):
            
            selection = self._regexes.GetSelection()
            
            if selection != wx.NOT_FOUND:
                
                if len( self._regex_box.GetValue() ) == 0: self._regex_box.SetValue( self._regexes.GetString( selection ) )
                
                self._regexes.Delete( selection )
                
                self._RefreshFileList()
                
            
        
        def EventUpdate( self, event ): self._RefreshFileList()
        
        def GetServiceIdentifier( self ): return self._service_identifier
        
        # this prob needs to be made cleverer if I do the extra column
        def GetTags( self, path ): return self._GetTags( path )
        
        def SetTagBoxFocus( self ): self._tag_box.SetFocus()
        
        def SingleTagRemoved( self, tag ):
            
            indices = self._paths_list.GetAllSelected()
            
            for index in indices:
                
                ( path, old_tags ) = self._paths_list.GetClientData( index )
                
                if tag in self._paths_to_single_tags[ path ]: self._paths_to_single_tags[ path ].remove( tag )
                
            
            self._RefreshFileList()
            
        
        def TagRemoved( self, tag ): self._RefreshFileList()
        
    
class DialogProgress( Dialog ):
    
    def __init__( self, parent, job_key, cancel_event = None ):
        
        def InitialiseControls():
            
            self._status = wx.StaticText( self, label = 'initialising', style = wx.ALIGN_CENTER | wx.ST_NO_AUTORESIZE )
            self._gauge = ClientGUICommon.Gauge( self, range = 100 )
            self._time_taken_so_far = wx.StaticText( self, label = 'initialising', style = wx.ALIGN_CENTER | wx.ST_NO_AUTORESIZE )
            self._time_left = wx.StaticText( self, label = 'initialising', style = wx.ALIGN_CENTER | wx.ST_NO_AUTORESIZE )
            
            if cancel_event is not None:
                
                self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'cancel' )
                self._cancel.Bind( wx.EVT_BUTTON, self.EventCancel )
                
            
            self._time_started = None
            
        
        def InitialisePanel():
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( self._status, FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._gauge, FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._time_taken_so_far, FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._time_left, FLAGS_EXPAND_PERPENDICULAR )
            
            if cancel_event is not None: vbox.AddF( self._cancel, FLAGS_LONE_BUTTON )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            if x < 640: x = 640
            
            self.SetInitialSize( ( x, y ) )
            
        
        Dialog.__init__( self, parent, 'progress', style = wx.SYSTEM_MENU | wx.CAPTION | wx.RESIZE_BORDER, position = 'center' )
        
        self._job_key = job_key
        
        self._cancel_event = cancel_event
        
        InitialiseControls()
        
        InitialisePanel()
        
        self.Bind( wx.EVT_TIMER, self.EventTimer, id = ID_TIMER_UPDATE )
        
        self._timer = wx.Timer( self, id = ID_TIMER_UPDATE )
        
        self._timer.Start( 1000, wx.TIMER_CONTINUOUS )
        
        HC.pubsub.sub( self, 'Update', 'progress_update' )
        
    
    def _DisplayTimes( self ):
        
        value = self._gauge.GetValue()
        range = self._gauge.GetRange()
        
        if self._time_started is not None:
            
            time_taken_so_far = time.clock() - self._time_started
            
            if value > 1: time_left = HC.ConvertTimeToPrettyTime( time_taken_so_far * ( float( range - value ) / float( value ) ) )
            else: time_left = 'unknown'
            
            self._time_taken_so_far.SetLabel( 'elapsed: ' + HC.ConvertTimeToPrettyTime( time_taken_so_far ) )
            
            self._time_left.SetLabel( 'remaining: ' + time_left )
            
        
    
    def EventCancel( self, event ):
        
        self._cancel.Disable()
        self._cancel_event.set()
        
    
    def EventTimer( self, event ):
        
        value = self._gauge.GetValue()
        range = self._gauge.GetRange()
        
        if value == range: self.EndModal( wx.OK )
        else: self._DisplayTimes()
        
    
    def Update( self, job_key, index, range, status ):
        
        if job_key == self._job_key:
            
            if self._time_started is None: self._time_started = time.clock()
            
            if range != self._gauge.GetRange(): self._gauge.SetRange( range )
            
            self._gauge.SetValue( index )
            
            self._status.SetLabel( status )
            
            self._DisplayTimes()
            
        
    
class DialogRegisterService( Dialog ):
    
    def __init__( self, parent ):
        
        def InitialiseControls():
            
            self._address = wx.TextCtrl( self, value = 'hostname:port' )
            self._registration_key = wx.TextCtrl( self, value = 'r0000000000000000000000000000000000000000000000000000000000000000' )
            
            self._register = wx.Button( self, label = 'register' )
            self._register.Bind( wx.EVT_BUTTON, self.EventRegister )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'cancel' )
            
        
        def InitialisePanel():
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( wx.StaticText( self, label = 'Please fill out the forms with the appropriate information for your service.' ), FLAGS_EXPAND_PERPENDICULAR )
            
            gridbox = wx.FlexGridSizer( 0, 2 )
            
            gridbox.AddGrowableCol( 1, 1 )
            
            gridbox.AddF( wx.StaticText( self, label='address' ), FLAGS_MIXED )
            gridbox.AddF( self._address, FLAGS_EXPAND_BOTH_WAYS )
            
            gridbox.AddF( wx.StaticText( self, label='registration key' ), FLAGS_MIXED )
            gridbox.AddF( self._registration_key, FLAGS_EXPAND_BOTH_WAYS )
            
            vbox.AddF( gridbox, FLAGS_EXPAND_SIZER_BOTH_WAYS )
            
            buttonbox = wx.BoxSizer( wx.HORIZONTAL )
            
            buttonbox.AddF( self._register, FLAGS_MIXED )
            buttonbox.AddF( self._cancel, FLAGS_MIXED )
            
            vbox.AddF( buttonbox, FLAGS_BUTTON_SIZERS )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
        
        Dialog.__init__( self, parent, 'register account', position = 'center' )
        
        InitialiseControls()
        
        InitialisePanel()
        
        self._register = False
        
    
    def EventRegister( self, event ):
        
        address = self._address.GetValue()
        
        try:
            
            ( host, port ) = address.split( ':' )
            
            port = int( port )
            
        except:
            
            wx.MessageBox( 'Could not parse that address!' )
            
            return
            
        
        registration_key_encoded = self._registration_key.GetValue()
        
        if registration_key_encoded[0] == 'r': registration_key_encoded = registration_key_encoded[1:]
        
        try: registration_key = registration_key_encoded.decode( 'hex' )
        except:
            
            wx.MessageBox( 'Could not parse that registration key!' )
            
            return
            
        
        connection = CC.AdvancedHTTPConnection( host = host, port = port )
        
        headers = {}
        
        headers[ 'Authorization' ] = 'hydrus_network ' + registration_key.encode( 'hex' )
        
        try: access_key = connection.request( 'GET', '/access_key', headers = headers )
        except Exception as e:
            
            wx.MessageBox( unicode( e ) )
            
            return
            
        
        self._credentials = CC.Credentials( host, port, access_key )
        
        self.EndModal( wx.ID_OK )
        
    
    def GetCredentials( self ): return self._credentials
    
class DialogSelectBooru( Dialog ):
    
    def __init__( self, parent ):
        
        def InitialiseControls():
            
            boorus = wx.GetApp().Read( 'boorus' )
            
            self._boorus = wx.ListBox( self, style = wx.LB_SORT )
            self._boorus.Bind( wx.EVT_LISTBOX_DCLICK, self.EventSelect )
            self._boorus.Bind( wx.EVT_KEY_DOWN, self.EventKeyDown )
            
            for booru in boorus: self._boorus.Append( booru.GetName(), booru )
            
        
        def InitialisePanel():
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( self._boorus, FLAGS_EXPAND_PERPENDICULAR )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            if x < 320: x = 320
            
            self.SetInitialSize( ( x, y ) )
            
        
        Dialog.__init__( self, parent, 'select booru' )
        
        InitialiseControls()
        
        InitialisePanel()
        
    
    def EventKeyDown( self, event ):
        
        if event.KeyCode == wx.WXK_SPACE:
            
            selection = self._boorus.GetSelection()
            
            if selection != wx.NOT_FOUND: self.EndModal( wx.ID_OK )
            
        elif event.KeyCode == wx.WXK_ESCAPE: self.EndModal( wx.ID_CANCEL )
        else: event.Skip()
        
    
    def EventSelect( self, event ): self.EndModal( wx.ID_OK )
    
    def GetBooru( self ): return self._boorus.GetClientData( self._boorus.GetSelection() )
    
class DialogSelectImageboard( Dialog ):
    
    def __init__( self, parent ):
        
        def InitialiseControls():
            
            self._tree = wx.TreeCtrl( self )
            self._tree.Bind( wx.EVT_TREE_ITEM_ACTIVATED, self.EventSelect )
            
            all_imageboards = wx.GetApp().Read( 'imageboards' )
            
            root_item = self._tree.AddRoot( 'all sites' )
            
            for ( site, imageboards ) in all_imageboards:
                
                site_item = self._tree.AppendItem( root_item, site )
                
                for imageboard in imageboards:
                    
                    name = imageboard.GetName()
                    
                    self._tree.AppendItem( site_item, name, data = wx.TreeItemData( imageboard ) )
                    
                
            
            self._tree.Expand( root_item )
            
        
        def InitialisePanel():
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( self._tree, FLAGS_EXPAND_BOTH_WAYS )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            if x < 320: x = 320
            if y < 640: y = 640
            
            self.SetInitialSize( ( x, y ) )
            
        
        Dialog.__init__( self, parent, 'select imageboard' )
        
        InitialiseControls()
        
        InitialisePanel()
        
    
    def EventSelect( self, event ):
        
        item = self._tree.GetSelection()
        
        data_object = self._tree.GetItemData( item )
        
        if data_object is None: self._tree.Toggle( item )
        else: self.EndModal( wx.ID_OK )
        
    
    def GetImageboard( self ): return self._tree.GetItemData( self._tree.GetSelection() ).GetData()
    
class DialogSelectFromListOfStrings( Dialog ):
    
    def __init__( self, parent, title, list_of_strings ):
        
        def InitialiseControls():
            
            self._strings = wx.ListBox( self, choices = list_of_strings )
            self._strings.Bind( wx.EVT_KEY_DOWN, self.EventKeyDown )
            self._strings.Bind( wx.EVT_LISTBOX_DCLICK, self.EventSelect )
            
        
        def InitialisePanel():
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( self._strings, FLAGS_EXPAND_PERPENDICULAR )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            if x < 320: x = 320
            
            self.SetInitialSize( ( x, y ) )
            
        
        Dialog.__init__( self, parent, title )
        
        InitialiseControls()
        
        InitialisePanel()
        
    
    def EventKeyDown( self, event ):
        
        if event.KeyCode == wx.WXK_SPACE:
            
            selection = self._strings.GetSelection()
            
            if selection != wx.NOT_FOUND: self.EndModal( wx.ID_OK )
            
        elif event.KeyCode == wx.WXK_ESCAPE: self.EndModal( wx.ID_CANCEL )
        else: event.Skip()
        
    
    def EventSelect( self, event ): self.EndModal( wx.ID_OK )
    
    def GetString( self ): return self._strings.GetStringSelection()
    
class DialogSelectLocalFiles( Dialog ):
    
    def __init__( self, parent, paths = [] ):
        
        def InitialiseControls():
            
            self._paths_list = ClientGUICommon.SaneListCtrl( self, 480, [ ( 'path', -1 ), ( 'guessed mime', 110 ), ( 'size', 60 ) ] )
            
            self._paths_list.SetMinSize( ( 780, 360 ) )
            
            self._add_button = wx.Button( self, label='Import now' )
            self._add_button.Bind( wx.EVT_BUTTON, self.EventOK )
            self._add_button.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._tag_button = wx.Button( self, label = 'Add tags before importing' )
            self._tag_button.Bind( wx.EVT_BUTTON, self.EventTags )
            self._tag_button.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._close_button = wx.Button( self, id = wx.ID_CANCEL, label='Cancel' )
            self._close_button.Bind( wx.EVT_BUTTON, self.EventCancel )
            self._close_button.SetForegroundColour( ( 128, 0, 0 ) )
            
            self._advanced_import_options = ClientGUICommon.AdvancedImportOptions( self )
            
            self._add_files_button = wx.Button( self, label='Add Files' )
            self._add_files_button.Bind( wx.EVT_BUTTON, self.EventAddPaths )
            
            self._add_folder_button = wx.Button( self, label='Add Folder' )
            self._add_folder_button.Bind( wx.EVT_BUTTON, self.EventAddFolder )
            
            self._remove_files_button = wx.Button( self, label='Remove Files' )
            self._remove_files_button.Bind( wx.EVT_BUTTON, self.EventRemovePaths )
            
        
        def InitialisePanel():
            
            file_buttons = wx.BoxSizer( wx.HORIZONTAL )
            
            file_buttons.AddF( ( 20, 0 ), FLAGS_NONE )
            file_buttons.AddF( self._add_files_button, FLAGS_MIXED )
            file_buttons.AddF( self._add_folder_button, FLAGS_MIXED )
            file_buttons.AddF( self._remove_files_button, FLAGS_MIXED )
            
            buttons = wx.BoxSizer( wx.HORIZONTAL )
            
            buttons.AddF( self._add_button, FLAGS_MIXED )
            buttons.AddF( self._tag_button, FLAGS_MIXED )
            buttons.AddF( self._close_button, FLAGS_MIXED )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( self._paths_list, FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( file_buttons, FLAGS_BUTTON_SIZERS )
            vbox.AddF( self._advanced_import_options, FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( ( 0, 5 ), FLAGS_NONE )
            vbox.AddF( buttons, FLAGS_BUTTON_SIZERS )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
        
        Dialog.__init__( self, parent, 'importing files' )
        
        self.SetDropTarget( ClientGUICommon.FileDropTarget( self._AddPathsToList ) )
        
        InitialiseControls()
        
        InitialisePanel()
        
        self._AddPathsToList( paths )
        
    
    
    def _AddPathsToList( self, paths ):
        
        good_paths = CC.ParseImportablePaths( paths )
        
        odd_paths = False
        
        for path in good_paths:
            
            mime = HC.GetMimeFromPath( path )
            
            if mime in HC.ALLOWED_MIMES:
                
                info = os.lstat( path )
                
                size = info[6]
                
                if size > 0:
                    
                    pretty_size = HC.ConvertIntToBytes( size )
                    
                    self._paths_list.Append( ( path, HC.mime_string_lookup[ mime ], pretty_size ), ( path, HC.mime_string_lookup[ mime ], size ) )
                    
                
            else: odd_paths = True
            
        
        if odd_paths: wx.MessageBox( 'At present hydrus can handle only jpegs, pngs, bmps, gifs, swfs, flvs and pdfs. The other files have not been added.' )
        
    
    def _GetPaths( self ): return [ row[0] for row in self._paths_list.GetClientData() ]
    
    def EventAddPaths( self, event ):
        
        with wx.FileDialog( self, 'Select the files to add.', style=wx.FD_MULTIPLE ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                paths = dlg.GetPaths()
                
                self._AddPathsToList( paths )
                
            
        
    
    def EventAddFolder( self, event ):
        
        with wx.DirDialog( self, 'Select a folder to add.', style=wx.DD_DIR_MUST_EXIST ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                path = dlg.GetPath()
                
                self._AddPathsToList( ( path, ) )
                
            
        
    
    def EventCancel( self, event ): self.EndModal( wx.ID_CANCEL )
    
    def EventOK( self, event ):
        
        paths = self._GetPaths()
        
        if len( paths ) > 0:
            
            advanced_import_options = self._advanced_import_options.GetInfo()
            
            HC.pubsub.pub( 'new_hdd_import', paths, advanced_import_options = advanced_import_options )
            
            self.EndModal( wx.ID_OK )
            
        
    
    def EventRemovePaths( self, event ): self._paths_list.RemoveAllSelected()
    
    def EventTags( self, event ):
        
        try:
            
            paths = self._GetPaths()
            
            if len( paths ) > 0:
                
                advanced_import_options = self._advanced_import_options.GetInfo()
                
                with DialogPathsToTagsRegex( self, paths ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        paths_to_tags = dlg.GetInfo()
                        
                        HC.pubsub.pub( 'new_hdd_import', paths, advanced_import_options = advanced_import_options, paths_to_tags = paths_to_tags )
                        
                        self.EndModal( wx.ID_OK )
                        
                    
                
            
        except: wx.MessageBox( traceback.format_exc() )
        
    
class DialogSetupCustomFilterActions( Dialog ):
    
    def __init__( self, parent ):
        
        def InitialiseControls():
            
            self._actions = ClientGUICommon.SaneListCtrl( self, 480, [ ( 'modifier', 150 ), ( 'key', 150 ), ( 'service', -1 ), ( 'action', 250 ) ] )
            
            self._actions.SetMinSize( ( 780, 360 ) )
            
            self._favourites = wx.ListBox( self )
            
            self._favourites.Bind( wx.EVT_LISTBOX, self.EventSelectFavourite )
            
            self._save_favourite = wx.Button( self, label = 'save' )
            self._save_favourite.Bind( wx.EVT_BUTTON, self.EventSaveFavourite )
            
            self._save_new_favourite = wx.Button( self, label = 'save as' )
            self._save_new_favourite.Bind( wx.EVT_BUTTON, self.EventSaveNewFavourite )
            
            self._delete_favourite = wx.Button( self, label = 'delete' )
            self._delete_favourite.Bind( wx.EVT_BUTTON, self.EventDeleteFavourite )
            
            self._current_actions_selection = wx.NOT_FOUND
            
            default_actions = self._GetDefaultActions()
            
            self._favourites.Append( 'default', default_actions )
            
            favourites = wx.GetApp().Read( 'favourite_custom_filter_actions' )
            
            if 'previous' in favourites: self._favourites.Append( 'previous', favourites[ 'previous' ] )
            else: self._favourites.Append( 'previous', default_actions )
            
            for ( name, actions ) in favourites.items():
                
                if name != 'previous': self._favourites.Append( name, actions )
                
            
            self._favourites.Select( 1 ) # previous
            
            self._add = wx.Button( self, label='add' )
            self._add.Bind( wx.EVT_BUTTON, self.EventAdd )
            self._add.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._edit = wx.Button( self, label='edit' )
            self._edit.Bind( wx.EVT_BUTTON, self.EventEdit )
            
            self._remove = wx.Button( self, label='remove' )
            self._remove.Bind( wx.EVT_BUTTON, self.EventRemove )
            self._remove.SetForegroundColour( ( 128, 0, 0 ) )
            
            self._ok = wx.Button( self, label = 'ok' )
            self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
            self._ok.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label='cancel' )
            self._cancel.Bind( wx.EVT_BUTTON, self.EventCancel )
            self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
            
        
        def InitialisePanel():
            
            action_buttons = wx.BoxSizer( wx.HORIZONTAL )
            
            action_buttons.AddF( self._add, FLAGS_MIXED )
            action_buttons.AddF( self._edit, FLAGS_MIXED )
            action_buttons.AddF( self._remove, FLAGS_MIXED )
            
            buttons = wx.BoxSizer( wx.HORIZONTAL )
            
            buttons.AddF( self._ok, FLAGS_MIXED )
            buttons.AddF( self._cancel, FLAGS_MIXED )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( self._actions, FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( action_buttons, FLAGS_BUTTON_SIZERS )
            vbox.AddF( buttons, FLAGS_BUTTON_SIZERS )
            
            button_hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            button_hbox.AddF( self._save_favourite, FLAGS_MIXED )
            button_hbox.AddF( self._save_new_favourite, FLAGS_MIXED )
            button_hbox.AddF( self._delete_favourite, FLAGS_MIXED )
            
            f_vbox = wx.BoxSizer( wx.VERTICAL )
            
            f_vbox.AddF( self._favourites, FLAGS_EXPAND_BOTH_WAYS )
            f_vbox.AddF( button_hbox, FLAGS_BUTTON_SIZERS )
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( f_vbox, FLAGS_EXPAND_PERPENDICULAR )
            hbox.AddF( vbox, FLAGS_EXPAND_BOTH_WAYS )
            
            self.SetSizer( hbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
        
        Dialog.__init__( self, parent, 'setup custom filter' )
        
        InitialiseControls()
        
        InitialisePanel()
        
        wx.CallAfter( self.EventSelectFavourite, None )
        
    
    def _GetDefaultActions( self ):
        
        default_actions = []
        
        for ( modifier, key_dict ) in self._options[ 'shortcuts' ].items():
            
            for ( key, action ) in key_dict.items():
                
                if action in ( 'manage_tags', 'manage_ratings', 'archive', 'inbox', 'fullscreen_switch', 'frame_back', 'frame_next', 'previous', 'next', 'first', 'last', 'pan_up', 'pan_down', 'pan_left', 'pan_right' ):
                    
                    service_identifier = None
                    
                    default_actions.append( ( modifier, key, service_identifier, action ) )
                    
                
            
        
        ( modifier, key, service_identifier, action ) = ( wx.ACCEL_NORMAL, wx.WXK_DELETE, None, 'delete' )
        
        default_actions.append( ( modifier, key, service_identifier, action ) )
        
        return default_actions
        
    
    def _IsUntouchableFavouriteSelection( self, selection ):
        
        name = self._favourites.GetString( selection )
        
        if name in ( 'previous', 'default' ): return True
        else: return False
        
    
    def _SortListCtrl( self ): self._actions.SortListItems( 3 )
    
    def EventAdd( self, event ):
        
        with DialogInputCustomFilterAction( self ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                ( pretty_tuple, data_tuple ) = dlg.GetInfo()
                
                self._actions.Append( pretty_tuple, data_tuple )
                
                self._SortListCtrl()
                
            
        
    
    def EventCancel( self, event ): self.EndModal( wx.ID_CANCEL )
    
    def EventDeleteFavourite( self, event ):
        
        selection = self._favourites.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            if not self._IsUntouchableFavouriteSelection( selection ):
                
                self._favourites.Delete( selection )
                
            
        
    
    def EventEdit( self, event ):
        
        for index in self._actions.GetAllSelected():
            
            ( modifier, key, service_identifier, action ) = self._actions.GetClientData( index )
            
            with DialogInputCustomFilterAction( self, modifier = modifier, key = key, service_identifier = service_identifier, action = action ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    ( pretty_tuple, data_tuple ) = dlg.GetInfo()
                    
                    self._actions.UpdateRow( index, pretty_tuple, data_tuple )
                    
                    self._SortListCtrl()
                    
                
            
        
    
    def EventOK( self, event ):
        
        favourites = {}
        
        for i in range( self._favourites.GetCount() ):
            
            name = self._favourites.GetString( i )
            
            if name == 'default': continue
            
            actions = self._favourites.GetClientData( i )
            
            favourites[ name ] = actions
            
        
        favourites[ 'previous' ] = self._actions.GetClientData() # overwrite
        
        wx.GetApp().Write( 'favourite_custom_filter_actions', favourites )
        
        self.EndModal( wx.ID_OK )
        
    
    def EventRemove( self, event ): self._actions.RemoveAllSelected()
    
    def EventSaveFavourite( self, event ):
        
        selection = self._favourites.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            if not self._IsUntouchableFavouriteSelection( selection ):
                
                actions = self._actions.GetClientData()
                
                self._favourites.SetClientData( selection, actions )
                
            
        
    
    def EventSaveNewFavourite( self, event ):
        
        existing_names = { self._favourites.GetString( i ) for i in range( self._favourites.GetCount() ) }
        
        with wx.TextEntryDialog( self, 'Enter name for these favourite actions' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                name = dlg.GetValue()
                
                if name == '': return
                
                while name in existing_names: name += str( random.randint( 0, 9 ) )
                
                actions = self._actions.GetClientData()
                
                self._favourites.Append( name, actions )
                
            
        
    
    def EventSelectFavourite( self, event ):
        
        selection = self._favourites.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            if selection != self._current_actions_selection:
                
                self._actions.DeleteAllItems()
                
                name = self._favourites.GetString( selection )
                
                if name in ( 'default', 'previous' ):
                    
                    self._save_favourite.Disable()
                    self._delete_favourite.Disable()
                    
                else:
                    
                    self._save_favourite.Enable()
                    self._delete_favourite.Enable()
                    
                
                actions = self._favourites.GetClientData( selection )
                
                for ( modifier, key, service_identifier, action ) in actions:
                    
                    ( pretty_modifier, pretty_key, pretty_action ) = HC.ConvertShortcutToPrettyShortcut( modifier, key, action )
                    
                    if service_identifier is None: pretty_service_identifier = ''
                    else: pretty_service_identifier = service_identifier.GetName()
                    
                    self._actions.Append( ( pretty_modifier, pretty_key, pretty_service_identifier, pretty_action ), ( modifier, key, service_identifier, action ) )
                    
                
                self._SortListCtrl()
                
            
        
    
    def GetActions( self ):
        
        raw_data = self._actions.GetClientData()
        
        actions = collections.defaultdict( dict )
        
        for ( modifier, key, service_identifier, action ) in raw_data: actions[ modifier ][ key ] = ( service_identifier, action )
        
        return actions
        
    
class DialogSetupExport( Dialog ):
    
    ID_HASH = 0
    ID_TAGS = 1
    ID_NN_TAGS = 2
    ID_NAMESPACE = 3
    ID_TAG = 4
    
    def __init__( self, parent, flat_media ):
        
        def InitialiseControls():
            
            self._tags_box = ClientGUICommon.TagsBoxCPPWithSorter( self, self._page_key )
            self._tags_box.SetMinSize( ( 220, 300 ) )
            
            self._paths = ClientGUICommon.SaneListCtrl( self, 480, [ ( 'number', 60 ), ( 'mime', 70 ), ( 'path', -1 ) ] )
            self._paths.Bind( wx.EVT_LIST_ITEM_SELECTED, self.EventSelectPath )
            self._paths.Bind( wx.EVT_LIST_ITEM_DESELECTED, self.EventSelectPath )
            self._paths.SetMinSize( ( 740, 360 ) )
            
            for ( i, media ) in enumerate( flat_media ):
                
                mime = media.GetMime()
                
                pretty_tuple = ( str( i + 1 ), HC.mime_string_lookup[ mime ], '' )
                data_tuple = ( ( i, media ), mime, '' )
                
                self._paths.Append( pretty_tuple, data_tuple )
                
            
            self._directory_picker = wx.DirPickerCtrl( self )
            if self._options[ 'export_path' ] is not None: self._directory_picker.SetPath( HC.ConvertPortablePathToAbsPath( self._options[ 'export_path' ] ) )
            self._directory_picker.Bind( wx.EVT_DIRPICKER_CHANGED, self.EventRecalcPaths )
            
            self._open_location = wx.Button( self, label = 'open this location' )
            self._open_location.Bind( wx.EVT_BUTTON, self.EventOpenLocation )
            
            self._pattern = wx.TextCtrl( self )
            self._pattern.SetValue( '{hash}' )
            
            self._update = wx.Button( self, label = 'update' )
            self._update.Bind( wx.EVT_BUTTON, self.EventRecalcPaths )
            
            self._examples = wx.Button( self, label = 'pattern shortcuts' )
            self._examples.Bind( wx.EVT_BUTTON, self.EventPatternShortcuts )
            
            self._export = wx.Button( self, label = 'export' )
            self._export.Bind( wx.EVT_BUTTON, self.EventExport )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label='close' )
            
        
        def InitialisePanel():
            
            top_hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            top_hbox.AddF( self._tags_box, FLAGS_EXPAND_PERPENDICULAR )
            top_hbox.AddF( self._paths, FLAGS_EXPAND_BOTH_WAYS )
            
            destination_hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            destination_hbox.AddF( self._directory_picker, FLAGS_EXPAND_BOTH_WAYS )
            destination_hbox.AddF( self._open_location, FLAGS_MIXED )
            
            pattern_hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            pattern_hbox.AddF( self._pattern, FLAGS_EXPAND_BOTH_WAYS )
            pattern_hbox.AddF( self._update, FLAGS_MIXED )
            pattern_hbox.AddF( self._examples, FLAGS_MIXED )
            pattern_hbox.AddF( self._export, FLAGS_MIXED )
            
            button_hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( top_hbox, FLAGS_EXPAND_SIZER_BOTH_WAYS )
            vbox.AddF( destination_hbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
            vbox.AddF( pattern_hbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
            vbox.AddF( self._cancel, FLAGS_LONE_BUTTON )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
        
        Dialog.__init__( self, parent, 'setup export' )
        
        self._page_key = os.urandom( 32 )
        
        InitialiseControls()
        
        InitialisePanel()
        
        wx.CallAfter( self.EventSelectPath, None )
        wx.CallAfter( self.EventRecalcPaths, None )
        
        self.Bind( wx.EVT_MENU, self.EventMenu )
        
    
    def _GetPath( self, media, terms ):
        
        directory = self._directory_picker.GetPath()
        
        filename = ''
        
        for ( term_type, term ) in terms:
            
            tags = media.GetTags()
            
            if term_type == 'string': filename += term
            elif term_type == 'namespace':
                
                tags = tags.GetNamespaceSlice( ( term, ) )
                
                filename += ', '.join( [ tag.split( ':' )[1] for tag in tags ] )
                
            elif term_type == 'predicate':
                
                if term in ( 'tags', 'nn tags' ):
                    
                    ( current, deleted, pending, petitioned ) = tags.GetUnionCDPP()
                    
                    tags = list( current.union( pending ) )
                    
                    if term == 'nn tags': tags = [ tag for tag in tags if ':' not in tag ]
                    else: tags = [ tag if ':' not in tag else tag.split( ':' )[1] for tag in tags ]
                    
                    tags.sort()
                    
                    filename += ', '.join( tags )
                    
                elif term == 'hash':
                    
                    hash = media.GetHash()
                    
                    filename += hash.encode( 'hex' )
                    
                
            elif term_type == 'tag':
                
                if ':' in term: term = term.split( ':' )[1]
                
                if tags.HasTag( term ): filename += term
                
            
        
        mime = media.GetMime()
        
        ext = HC.mime_ext_lookup[ mime ]
        
        return directory + os.path.sep + filename + ext
        
    
    def _RecalcPaths( self ):
        
        pattern = self._pattern.GetValue()
        
        try:
            
            terms = [ ( 'string', pattern ) ]
            
            new_terms = []
            
            for ( term_type, term ) in terms:
                
                if term_type == 'string':
                    
                    while '[' in term:
                        
                        ( pre, term ) = term.split( '[', 1 )
                        
                        ( namespace, term ) = term.split( ']', 1 )
                        
                        new_terms.append( ( 'string', pre ) )
                        new_terms.append( ( 'namespace', namespace ) )
                        
                    
                
                new_terms.append( ( term_type, term ) )
                
            
            terms = new_terms
            
            new_terms = []
            
            for ( term_type, term ) in terms:
                
                if term_type == 'string':
                    
                    while '{' in term:
                        
                        ( pre, term ) = term.split( '{', 1 )
                        
                        ( predicate, term ) = term.split( '}', 1 )
                        
                        new_terms.append( ( 'string', pre ) )
                        new_terms.append( ( 'predicate', predicate ) )
                        
                    
                
                new_terms.append( ( term_type, term ) )
                
            
            terms = new_terms
            
            new_terms = []
            
            for ( term_type, term ) in terms:
                
                if term_type == 'string':
                    
                    while '(' in term:
                        
                        ( pre, term ) = term.split( '(', 1 )
                        
                        ( tag, term ) = term.split( ')', 1 )
                        
                        new_terms.append( ( 'string', pre ) )
                        new_terms.append( ( 'tag', tag ) )
                        
                    
                
                new_terms.append( ( term_type, term ) )
                
            
            terms = new_terms
            
        except: raise Exception( 'Could not parse that pattern!' )
        
        all_paths = set()
        
        for ( index, ( ( ordering_index, media ), mime, old_path ) ) in enumerate( self._paths.GetClientData() ):
            
            path = self._GetPath( media, terms )
            
            if path in all_paths:
                
                i = 1
                
                while self._GetPath( media, terms + [ ( 'string', str( i ) ) ] ) in all_paths: i += 1
                
                path = self._GetPath( media, terms + [ ( 'string', str( i ) ) ] )
                
            
            all_paths.add( path )
            
            if path != old_path:
                
                mime = media.GetMime()
                
                self._paths.UpdateRow( index, ( str( ordering_index + 1 ), HC.mime_string_lookup[ mime ], path ), ( ( ordering_index, media ), mime, path ) )
                
            
        
    
    def EventExport( self, event ):
        
        try: self._RecalcPaths()
        except Exception as e:
            
            wx.MessageBox( unicode( e ) )
            
            return
            
        
        for ( ( ordering_index, media ), mime, path ) in self._paths.GetClientData():
            
            try:
                
                hash = media.GetHash()
                
                file = wx.GetApp().Read( 'file', hash )
                
                with open( path, 'wb' ) as f: f.write( file )
                
            except:
                
                wx.MessageBox( 'Encountered a problem while attempting to export file with index ' + str( ordering_index + 1 ) + '.' + os.linesep + + os.linesep + traceback.format_exc() )
                
                break
                
            
        
    
    def EventMenu( self, event ):
        
        id = event.GetId()
        
        phrase = None
        
        if id == self.ID_HASH: phrase = r'{hash}'
        if id == self.ID_TAGS: phrase = r'{tags}'
        if id == self.ID_NN_TAGS: phrase = r'{nn tags}'
        if id == self.ID_NAMESPACE: phrase = r'[...]'
        if id == self.ID_TAG: phrase = r'(...)'
        else: event.Skip()
        
        if phrase is not None:
            
            if wx.TheClipboard.Open():
                
                data = wx.TextDataObject( phrase )
                
                wx.TheClipboard.SetData( data )
                
                wx.TheClipboard.Close()
                
            else: wx.MessageBox( 'I could not get permission to access the clipboard.' )
            
        
    
    def EventPatternShortcuts( self, event ):
        
        menu = wx.Menu()
        
        menu.Append( -1, 'click on a phrase to copy to clipboard' )
        
        menu.AppendSeparator()
        
        menu.Append( self.ID_HASH, r'the file\'s hash - {hash}' )
        menu.Append( self.ID_TAGS, r'all the file\'s tags - {tags}' )
        menu.Append( self.ID_NN_TAGS, r'all the file\'s non-namespaced tags - {nn tags}' )
        
        menu.AppendSeparator()
        
        menu.Append( self.ID_NAMESPACE, r'all instances of a particular namespace - [...]' )
        
        menu.AppendSeparator()
        
        menu.Append( self.ID_TAG, r'a particular tag, if the file has it - (...)' )
        
        self.PopupMenu( menu )
        
        menu.Destroy()
        
    
    def EventOpenLocation( self, event ):
        
        directory = self._directory_picker.GetPath()
        
        if directory is not None and directory != '':
            
            try:
                
                if 'Windows' in os.environ.get( 'os' ): subprocess.Popen( [ 'explorer', directory ] )
                else: subprocess.Popen( [ 'explorer', directory ] )
                
            except: wx.MessageBox( 'Could not open that location!' )
        
    
    def EventRecalcPaths( self, event ):
        
        try: self._RecalcPaths()
        except Exception as e: wx.MessageBox( unicode( e ) )
        
    
    def EventSelectPath( self, event ):
        
        indices = self._paths.GetAllSelected()
        
        if len( indices ) == 0:
            
            all_media = [ media for ( ( ordering_index, media ), mime, old_path ) in self._paths.GetClientData() ]
            
        else:
            
            all_media = [ media for ( ( ordering_index, media ), mime, old_path ) in [ self._paths.GetClientData( index ) for index in indices ] ]
            
        
        HC.pubsub.pub( 'new_tags_selection', self._page_key, all_media )
        
    
class DialogYesNo( Dialog ):
    
    def __init__( self, parent, message, yes_label = 'yes', no_label = 'no' ):
        
        def InitialiseControls():
            
            self._yes = wx.Button( self, label = yes_label )
            self._yes.Bind( wx.EVT_BUTTON, self.EventYes )
            self._yes.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._no = wx.Button( self, id = wx.ID_CANCEL, label = no_label )
            self._no.Bind( wx.EVT_BUTTON, self.EventNo )
            self._no.SetForegroundColour( ( 128, 0, 0 ) )
            
        
        def InitialisePanel():
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( self._yes, FLAGS_SMALL_INDENT )
            hbox.AddF( self._no, FLAGS_SMALL_INDENT )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            text = wx.StaticText( self, label = message )
            
            text.Wrap( 480 )
            
            vbox.AddF( text, FLAGS_BIG_INDENT )
            vbox.AddF( hbox, FLAGS_BUTTON_SIZERS )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
        
        Dialog.__init__( self, parent, 'are you sure?', position = 'center' )
        
        InitialiseControls()
        
        InitialisePanel()
        
        self.Bind( wx.EVT_CHAR_HOOK, self.EventCharHook )
        
    
    def EventCharHook( self, event ):
        
        if event.KeyCode == wx.WXK_ESCAPE: self.EndModal( wx.ID_NO )
        else: event.Skip()
        
    
    def EventNo( self, event ): self.EndModal( wx.ID_NO )
    
    def EventYes( self, event ): self.EndModal( wx.ID_YES )
    