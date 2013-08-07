import Crypto.PublicKey.RSA
import HydrusConstants as HC
import HydrusEncryption
import HydrusTags
import ClientConstants as CC
import ClientGUICommon
import collections
import itertools
import os
import random
import re
import string
import subprocess
import time
import traceback
import urllib
import wx
import yaml
import zipfile

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
        
        services = HC.app.Read( 'services', service_types )
        
        if permission is not None: services = [ service for service in services if service.GetAccount().HasPermission( permission ) ]
        
        service_identifiers = [ service.GetServiceIdentifier() for service in services ]
        
    
    if unallowed is not None: service_identifiers.difference_update( unallowed )
    
    if len( service_identifiers ) == 0: return None
    elif len( service_identifiers ) == 1:
        
        ( service_identifier, ) = service_identifiers
        
        return service_identifier
        
    else:
        
        names_to_service_identifiers = { service_identifier.GetName() : service_identifier for service_identifier in service_identifiers }
        
        with DialogSelectFromListOfStrings( HC.app.GetGUI(), 'select service', [ service_identifier.GetName() for service_identifier in service_identifiers ] ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK: return names_to_service_identifiers[ dlg.GetString() ]
            else: return None
            
        
    
def ShowMessage( parent, message ):
    
    with DialogMessage( parent, message ) as dlg: dlg.ShowModal()
    
class Dialog( wx.Dialog ):
    
    def __init__( self, parent, title, style = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER, position = 'topleft' ):
        
        if parent is not None and position == 'topleft':
            
            ( pos_x, pos_y ) = HC.app.GetGUI().GetPositionTuple()
            
            pos = ( pos_x + 50, pos_y + 100 )
            
        else: pos = ( -1, -1 )
        
        wx.Dialog.__init__( self, parent, title = title, style = style, pos = pos )
        
        self._options = HC.app.Read( 'options' )
        
        self.SetDoubleBuffered( True )
        
        self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
        
        self.SetIcon( wx.Icon( HC.STATIC_DIR + os.path.sep + 'hydrus.ico', wx.BITMAP_TYPE_ICO ) )
        
        self._dialog_cancel_button = wx.Button( self, id = wx.ID_CANCEL, size = ( 0, 0 ) )
        
        if position == 'center': wx.CallAfter( self.Center )
        
        self.Bind( wx.EVT_BUTTON, self.EventDialogButton )
        
    
    def EventDialogButton( self, event ): self.EndModal( event.GetId() )
    
class DialogChooseNewServiceMethod( Dialog ):
    
    def __init__( self, parent ):
        
        def InitialiseControls():
            
            register_message = 'I want to set up a new account. I have a registration key (a key starting with \'r\').'
            
            self._register = wx.Button( self, id = wx.ID_OK, label = register_message )
            self._register.Bind( wx.EVT_BUTTON, self.EventRegister )
            
            setup_message = 'The account is already set up; I just want to add it to this client. I have a normal access key.'
            
            self._setup = wx.Button( self, id = wx.ID_OK, label = setup_message )
            
        
        def PopulateControls():
            
            pass
            
        
        def ArrangeControls():
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( self._register, FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( wx.StaticText( self, label = '-or-', style = wx.ALIGN_CENTER ), FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._setup, FLAGS_EXPAND_PERPENDICULAR )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
        
        Dialog.__init__( self, parent, 'how to set up the account?', position = 'center' )
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
        self._should_register = False
        
        wx.CallAfter( self._register.SetFocus )
        
    
    def EventRegister( self, event ):
        
        self._should_register = True
        
        self.EndModal( wx.ID_OK )
        
    
    def GetRegister( self ): return self._should_register
    
class DialogFinishFiltering( Dialog ):
    
    def __init__( self, parent, num_kept, num_deleted, keep = 'keep', delete = 'delete' ):
        
        def InitialiseControls():
            
            self._commit = wx.Button( self, id = wx.ID_YES, label = 'commit' )
            self._commit.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._forget = wx.Button( self, id = wx.ID_NO, label = 'forget' )
            self._forget.SetForegroundColour( ( 128, 0, 0 ) )
            
            self._back = wx.Button( self, id = wx.ID_CANCEL, label = 'back to filtering' )
            
        
        def PopulateControls():
            
            pass
            
        
        def ArrangeControls():
            
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
        
        PopulateControls()
        
        ArrangeControls()
        
        wx.CallAfter( self._commit.SetFocus )
        
    
class DialogFinishRatingFiltering( Dialog ):
    
    def __init__( self, parent, num_certain_ratings, num_uncertain_ratings ):
        
        def InitialiseControls():
            
            self._commit = wx.Button( self, id = wx.ID_YES, label = 'commit' )
            self._commit.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._forget = wx.Button( self, id = wx.ID_NO, label = 'forget' )
            self._forget.SetForegroundColour( ( 128, 0, 0 ) )
            
            self._back = wx.Button( self, id = wx.ID_CANCEL, label = 'back to filtering' )
            
        
        def PopulateControls():
            
            pass
            
        
        def ArrangeControls():
            
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
        
        PopulateControls()
        
        ArrangeControls()
        
        wx.CallAfter( self._commit.SetFocus )
        
    
class DialogFirstStart( Dialog ):
    
    def __init__( self, parent ):
        
        def InitialiseControls():
            
            self._ok = wx.Button( self, id = wx.ID_OK, label = 'ok!' )
            self._ok.SetForegroundColour( ( 0, 128, 0 ) )
            
        
        def PopulateControls():
            
            pass
            
        
        def ArrangeControls():
            
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
        
        PopulateControls()
        
        ArrangeControls()
        
        wx.CallAfter( self._ok.SetFocus )
        
    
class DialogInputCustomFilterAction( Dialog ):
    
    def __init__( self, parent, modifier = wx.ACCEL_NORMAL, key = wx.WXK_F7, service_identifier = None, action = 'archive' ):
        
        def InitialiseControls():
            
            service_identifiers = HC.app.Read( 'service_identifiers', ( HC.LOCAL_TAG, HC.TAG_REPOSITORY, HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ) )
            
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
            self._tag_input = ClientGUICommon.AutoCompleteDropdownTagsWrite( self._tag_panel, self.SetTag, HC.LOCAL_FILE_SERVICE_IDENTIFIER, HC.COMBINED_TAG_SERVICE_IDENTIFIER )
            
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
                        
                    
                
            
        
        def PopulateControls():
            
            pass
            
        
        def ArrangeControls():
            
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
        
        self._service_identifier = service_identifier
        self._action = action
        
        self._current_ratings_like_service = None
        self._current_ratings_numerical_service = None
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
        wx.CallAfter( self._ok_none.SetFocus )
        
    
    def _SetActions( self ):
        
        if self._ratings_like_service_identifiers.GetCount() > 0:
            
            selection = self._ratings_like_service_identifiers.GetSelection()
            
            if selection != wx.NOT_FOUND:
                
                service_identifier = self._ratings_like_service_identifiers.GetClientData( selection )
                
                service = HC.app.Read( 'service', service_identifier )
                
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
                
                service = HC.app.Read( 'service', service_identifier )
                
                self._current_ratings_numerical_service = service
                
                ( lower, upper ) = service.GetExtraInfo()
                
                self._ratings_numerical_slider.SetRange( lower, upper )
                
            else: self._ratings_numerical_slider.SetRange( 0, 5 )
            
        
    
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
                
                self._pretty_action = HC.u( self._ratings_numerical_slider.GetValue() )
                
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
        
    
    def SetTag( self, tag, parents = [] ): self._tag_value.SetValue( tag )
    
class DialogInputFileSystemPredicate( Dialog ):
    
    def __init__( self, parent, type ):
        
        def Age():
            
            def InitialiseControls():
                
                self._sign = wx.Choice( self, choices=[ '<', u'\u2248', '>' ] )
                
                self._years = wx.SpinCtrl( self, max = 30 )
                self._months = wx.SpinCtrl( self, max = 60 )
                self._days = wx.SpinCtrl( self, max = 90 )
                self._hours = wx.SpinCtrl( self, max = 24 )
                
                self._ok = wx.Button( self, id = wx.ID_OK, label='Ok' )
                self._ok.SetDefault()
                self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
                self._ok.SetForegroundColour( ( 0, 128, 0 ) )
                
            
            def PopulateControls():
                
                ( sign, years, months, days ) = system_predicates[ 'age' ]
                
                self._sign.SetSelection( sign )
                
                self._years.SetValue( years )
                self._months.SetValue( months )
                self._days.SetValue( days )
                self._hours.SetValue( 0 )
                
            
            def ArrangeControls():
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( wx.StaticText( self, label='system:age' ), FLAGS_MIXED )
                hbox.AddF( self._sign, FLAGS_MIXED )
                hbox.AddF( self._years, FLAGS_MIXED )
                hbox.AddF( wx.StaticText( self, label='years' ), FLAGS_MIXED )
                hbox.AddF( self._months, FLAGS_MIXED )
                hbox.AddF( wx.StaticText( self, label='months' ), FLAGS_MIXED )
                hbox.AddF( self._days, FLAGS_MIXED )
                hbox.AddF( wx.StaticText( self, label='days' ), FLAGS_MIXED )
                hbox.AddF( self._hours, FLAGS_MIXED )
                hbox.AddF( wx.StaticText( self, label='hours' ), FLAGS_MIXED )
                hbox.AddF( self._ok, FLAGS_MIXED )
                
                self.SetSizer( hbox )
                
            
            Dialog.__init__( self, parent, 'enter age predicate' )
            
            InitialiseControls()
            
            PopulateControls()
            
            ArrangeControls()
        
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
            wx.CallAfter( self._ok.SetFocus )
            
        
        def Duration():
            
            def InitialiseControls():
                
                self._sign = wx.Choice( self, choices=[ '<', u'\u2248', '=', '>' ] )
                
                self._duration_s = wx.SpinCtrl( self, max = 3599 )
                self._duration_ms = wx.SpinCtrl( self, max = 999 )
                
                self._ok = wx.Button( self, id = wx.ID_OK, label='Ok' )
                self._ok.SetDefault()
                self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
                self._ok.SetForegroundColour( ( 0, 128, 0 ) )
                
            
            def PopulateControls():
                
                ( sign, s, ms ) = system_predicates[ 'duration' ]
                
                self._sign.SetSelection( sign )
                
                self._duration_s.SetValue( s )
                self._duration_ms.SetValue( ms )
                
            
            def ArrangeControls():
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( wx.StaticText( self, label='system:duration' ), FLAGS_MIXED )
                hbox.AddF( self._sign, FLAGS_MIXED )
                hbox.AddF( self._duration_s, FLAGS_MIXED )
                hbox.AddF( wx.StaticText( self, label='s' ), FLAGS_MIXED )
                hbox.AddF( self._duration_ms, FLAGS_MIXED )
                hbox.AddF( wx.StaticText( self, label='ms' ), FLAGS_MIXED )
                hbox.AddF( self._ok, FLAGS_MIXED )
                
                self.SetSizer( hbox )
                
            
            Dialog.__init__( self, parent, 'enter duration predicate' )
            
            InitialiseControls()
            
            PopulateControls()
            
            ArrangeControls()
        
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
            wx.CallAfter( self._ok.SetFocus )
            
        
        def FileService():
            
            def InitialiseControls():
                
                self._sign = wx.Choice( self )
                self._sign.Append( 'is', True )
                self._sign.Append( 'is not', False )
                
                self._current_pending = wx.Choice( self )
                self._current_pending.Append( 'currently in', HC.CURRENT )
                self._current_pending.Append( 'pending to', HC.PENDING )
                
                self._file_service_identifier = wx.Choice( self )
                
                self._ok = wx.Button( self, id = wx.ID_OK, label='Ok' )
                self._ok.SetDefault()
                self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
                self._ok.SetForegroundColour( ( 0, 128, 0 ) )
                
            
            def PopulateControls():
                
                self._sign.SetSelection( 0 )
                self._current_pending.SetSelection( 0 )
                
                service_identifiers = HC.app.Read( 'service_identifiers', ( HC.FILE_REPOSITORY, HC.LOCAL_FILE ) )
                
                for service_identifier in service_identifiers: self._file_service_identifier.Append( service_identifier.GetName(), service_identifier )
                self._file_service_identifier.SetSelection( 0 )
                
            
            def ArrangeControls():
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( wx.StaticText( self, label='system:file service:' ), FLAGS_MIXED )
                hbox.AddF( self._sign, FLAGS_MIXED )
                hbox.AddF( self._current_pending, FLAGS_MIXED )
                hbox.AddF( self._file_service_identifier, FLAGS_MIXED )
                hbox.AddF( self._ok, FLAGS_MIXED )
                
                self.SetSizer( hbox )
                
            
            Dialog.__init__( self, parent, 'enter file service predicate' )
            
            InitialiseControls()
            
            PopulateControls()
            
            ArrangeControls()
        
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
            wx.CallAfter( self._ok.SetFocus )
            
        
        def Hash():
            
            def InitialiseControls():
                
                self._hash = wx.TextCtrl( self )
                
                self._ok = wx.Button( self, id = wx.ID_OK, label='Ok' )
                self._ok.SetDefault()
                self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
                self._ok.SetForegroundColour( ( 0, 128, 0 ) )
                
            
            def PopulateControls():
                
                pass
                
            
            def ArrangeControls():
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( wx.StaticText( self, label='system:hash=' ), FLAGS_MIXED )
                hbox.AddF( self._hash, FLAGS_MIXED )
                hbox.AddF( self._ok, FLAGS_MIXED )
                
                self.SetSizer( hbox )
                
            
            Dialog.__init__( self, parent, 'enter hash predicate' )
            
            InitialiseControls()
            
            PopulateControls()
            
            ArrangeControls()
        
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
            wx.CallAfter( self._ok.SetFocus )
            
        
        def Height():
            
            def InitialiseControls():
                
                self._sign = wx.Choice( self, choices=[ '<', u'\u2248', '=', '>' ] )
                
                self._height = wx.SpinCtrl( self, max = 200000 )
                
                self._ok = wx.Button( self, id = wx.ID_OK, label='Ok' )
                self._ok.SetDefault()
                self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
                self._ok.SetForegroundColour( ( 0, 128, 0 ) )
                
            
            def PopulateControls():
                
                ( sign, height ) = system_predicates[ 'height' ]
                
                self._sign.SetSelection( sign )
                
                self._height.SetValue( height )
                
            
            def ArrangeControls():
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( wx.StaticText( self, label='system:height' ), FLAGS_MIXED )
                hbox.AddF( self._sign, FLAGS_MIXED )
                hbox.AddF( self._height, FLAGS_MIXED )
                hbox.AddF( self._ok, FLAGS_MIXED )
                
                self.SetSizer( hbox )
                
            
            Dialog.__init__( self, parent, 'enter height predicate' )
            
            InitialiseControls()
            
            PopulateControls()
            
            ArrangeControls()
        
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
            wx.CallAfter( self._ok.SetFocus )
            
        
        def Limit():
            
            def InitialiseControls():
                
                self._limit = wx.SpinCtrl( self, max = 1000000 )
                
                self._ok = wx.Button( self, id = wx.ID_OK, label='Ok' )
                self._ok.SetDefault()
                self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
                self._ok.SetForegroundColour( ( 0, 128, 0 ) )
                
            
            def PopulateControls():
                
                limit = system_predicates[ 'limit' ]
                
                self._limit.SetValue( limit )
                
            
            def ArrangeControls():
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( wx.StaticText( self, label='system:limit=' ), FLAGS_MIXED )
                hbox.AddF( self._limit, FLAGS_MIXED )
                hbox.AddF( self._ok, FLAGS_MIXED )
                
                self.SetSizer( hbox )
                
            
            Dialog.__init__( self, parent, 'enter limit predicate' )
            
            InitialiseControls()
            
            PopulateControls()
            
            ArrangeControls()
        
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
            wx.CallAfter( self._ok.SetFocus )
            
        
        def Mime():
            
            def InitialiseControls():
                
                self._mime_media = wx.Choice( self, choices = [ 'image', 'application', 'audio', 'video' ] )
                self._mime_media.Bind( wx.EVT_CHOICE, self.EventMime )
                
                self._mime_type = wx.Choice( self, choices = [], size = ( 120, -1 ) )
                
                self._ok = wx.Button( self, id = wx.ID_OK, label='Ok' )
                self._ok.SetDefault()
                self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
                self._ok.SetForegroundColour( ( 0, 128, 0 ) )
                
            
            def PopulateControls():
                
                ( media, type ) = system_predicates[ 'mime' ]
                
                self._mime_media.SetSelection( media )
                
                self.EventMime( None )
                
                self._mime_type.SetSelection( type )
                
            
            def ArrangeControls():
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( wx.StaticText( self, label='system:mime' ), FLAGS_MIXED )
                hbox.AddF( self._mime_media, FLAGS_MIXED )
                hbox.AddF( wx.StaticText( self, label='/' ), FLAGS_MIXED )
                hbox.AddF( self._mime_type, FLAGS_MIXED )
                hbox.AddF( self._ok, FLAGS_MIXED )
                
                self.SetSizer( hbox )
                
            
            Dialog.__init__( self, parent, 'enter mime predicate' )
            
            InitialiseControls()
            
            PopulateControls()
            
            ArrangeControls()
        
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
            wx.CallAfter( self._ok.SetFocus )
            
        
        def NumTags():
            
            def InitialiseControls():
                
                self._sign = wx.Choice( self, choices=[ '<', u'\u2248', '=', '>' ] )
                
                self._num_tags = wx.SpinCtrl( self, max = 2000 )
                
                self._ok = wx.Button( self, id = wx.ID_OK, label='Ok' )
                self._ok.SetDefault()
                self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
                self._ok.SetForegroundColour( ( 0, 128, 0 ) )
                
            
            def PopulateControls():
                
                ( sign, num_tags ) = system_predicates[ 'num_tags' ]
                
                self._sign.SetSelection( sign )
                
                self._num_tags.SetValue( num_tags )
                
            
            def ArrangeControls():
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( wx.StaticText( self, label='system:num_tags' ), FLAGS_MIXED )
                hbox.AddF( self._sign, FLAGS_MIXED )
                hbox.AddF( self._num_tags, FLAGS_MIXED )
                hbox.AddF( self._ok, FLAGS_MIXED )
                
                self.SetSizer( hbox )
                
            
            Dialog.__init__( self, parent, 'enter number of tags predicate' )
            
            InitialiseControls()
            
            PopulateControls()
            
            ArrangeControls()
        
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
            wx.CallAfter( self._ok.SetFocus )
            
        
        def NumWords():
            
            def InitialiseControls():
                
                self._sign = wx.Choice( self, choices=[ '<', u'\u2248', '=', '>' ] )
                
                self._num_words = wx.SpinCtrl( self, max = 1000000 )
                
                self._ok = wx.Button( self, id = wx.ID_OK, label='Ok' )
                self._ok.SetDefault()
                self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
                self._ok.SetForegroundColour( ( 0, 128, 0 ) )
                
            
            def PopulateControls():
                
                ( sign, num_words ) = system_predicates[ 'num_words' ]
                
                self._sign.SetSelection( sign )
                
                self._num_words.SetValue( num_words )
                
            
            def ArrangeControls():
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( wx.StaticText( self, label='system:num_words' ), FLAGS_MIXED )
                hbox.AddF( self._sign, FLAGS_MIXED )
                hbox.AddF( self._num_words, FLAGS_MIXED )
                hbox.AddF( self._ok, FLAGS_MIXED )
                
                self.SetSizer( hbox )
                
            
            Dialog.__init__( self, parent, 'enter number of words predicate' )
            
            InitialiseControls()
            
            PopulateControls()
            
            ArrangeControls()
        
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
            wx.CallAfter( self._ok.SetFocus )
            
        
        def Rating():
            
            def InitialiseControls():
                
                self._service_numerical = wx.Choice( self )
                self._service_numerical.Bind( wx.EVT_CHOICE, self.EventRatingsService )
                
                self._sign_numerical = wx.Choice( self, choices=[ '>', '<', '=', u'\u2248', '=rated', '=not rated', '=uncertain' ] )
                
                self._value_numerical = wx.SpinCtrl( self, min = 0, max = 50000 ) # set bounds based on current service
                
                self._first_ok = wx.Button( self, label='Ok', id = HC.LOCAL_RATING_NUMERICAL )
                self._first_ok.Bind( wx.EVT_BUTTON, self.EventOK )
                self._first_ok.SetForegroundColour( ( 0, 128, 0 ) )
                
                self._service_like = wx.Choice( self )
                self._service_like.Bind( wx.EVT_CHOICE, self.EventRatingsService )
                
                self._value_like = wx.Choice( self, choices=[ 'like', 'dislike', 'rated', 'not rated' ] ) # set words based on current service
                
                self._second_ok = wx.Button( self, label='Ok', id = HC.LOCAL_RATING_LIKE )
                self._second_ok.Bind( wx.EVT_BUTTON, self.EventOK )
                self._second_ok.SetForegroundColour( ( 0, 128, 0 ) )
                
            
            def PopulateControls():
                
                self._local_numericals = HC.app.Read( 'services', ( HC.LOCAL_RATING_NUMERICAL, ) )
                self._local_likes = HC.app.Read( 'services', ( HC.LOCAL_RATING_LIKE, ) )
                
                for service in self._local_numericals: self._service_numerical.Append( service.GetServiceIdentifier().GetName(), service )
                
                ( sign, value ) = system_predicates[ 'local_rating_numerical' ]
                
                self._sign_numerical.SetSelection( sign )
                
                self._value_numerical.SetValue( value )
                
                for service in self._local_likes: self._service_like.Append( service.GetServiceIdentifier().GetName(), service )
                
                value = system_predicates[ 'local_rating_like' ]
                
                self._value_like.SetSelection( value )
                
                if len( self._local_numericals ) > 0: self._service_numerical.SetSelection( 0 )
                if len( self._local_likes ) > 0: self._service_like.SetSelection( 0 )
                
                self.EventRatingsService( None )
                
            
            def ArrangeControls():
                
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
                
            
            Dialog.__init__( self, parent, 'enter rating predicate' )
            
            InitialiseControls()
            
            PopulateControls()
            
            ArrangeControls()
        
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
            wx.CallAfter( self._first_ok.SetFocus )
            
        
        def Ratio():
            
            def InitialiseControls():
                
                self._sign = wx.Choice( self, choices = [ '=', u'\u2248' ] )
                
                self._width = wx.SpinCtrl( self, max = 50000 )
                
                self._height = wx.SpinCtrl( self, max = 50000 )
                
                self._ok = wx.Button( self, id = wx.ID_OK, label='Ok' )
                self._ok.SetDefault()
                self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
                self._ok.SetForegroundColour( ( 0, 128, 0 ) )
                
            
            def PopulateControls():
                
                ( sign, width, height ) = system_predicates[ 'ratio' ]
                
                self._sign.SetSelection( sign )
                
                self._width.SetValue( width )
                
                self._height.SetValue( height )
                
            
            def ArrangeControls():
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( wx.StaticText( self, label = 'system:ratio' ), FLAGS_MIXED )
                hbox.AddF( self._sign, FLAGS_MIXED )
                hbox.AddF( self._width, FLAGS_MIXED )
                hbox.AddF( wx.StaticText( self, label = ':' ), FLAGS_MIXED )
                hbox.AddF( self._height, FLAGS_MIXED )
                hbox.AddF( self._ok, FLAGS_MIXED )
                
                self.SetSizer( hbox )
                
            
            Dialog.__init__( self, parent, 'enter ratio predicate' )
            
            InitialiseControls()
            
            PopulateControls()
            
            ArrangeControls()
        
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
            wx.CallAfter( self._ok.SetFocus )
            
        
        def Size():
            
            def InitialiseControls():
                
                self._sign = wx.Choice( self, choices = [ '<', u'\u2248', '=', '>' ] )
                
                self._size = wx.SpinCtrl( self, max = 1048576 )
                
                self._unit = wx.Choice( self, choices = [ 'B', 'KB', 'MB', 'GB' ] )
                
                self._ok = wx.Button( self, id = wx.ID_OK, label='Ok' )
                self._ok.SetDefault()
                self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
                self._ok.SetForegroundColour( ( 0, 128, 0 ) )
                
            
            def PopulateControls():
                
                ( sign, size, unit ) = system_predicates[ 'size' ]
                
                self._sign.SetSelection( sign )
                
                self._size.SetValue( size )
                
                self._unit.SetSelection( unit )
                
            
            def ArrangeControls():
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( wx.StaticText( self, label='system:size' ), FLAGS_MIXED )
                hbox.AddF( self._sign, FLAGS_MIXED )
                hbox.AddF( self._size, FLAGS_MIXED )
                hbox.AddF( self._unit, FLAGS_MIXED )
                hbox.AddF( self._ok, FLAGS_MIXED )
                
                self.SetSizer( hbox )
                
            
            Dialog.__init__( self, parent, 'enter size predicate' )
            
            InitialiseControls()
            
            PopulateControls()
            
            ArrangeControls()
        
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
            wx.CallAfter( self._ok.SetFocus )
            
        
        def Width():
            
            def InitialiseControls():
                
                self._sign = wx.Choice( self, choices = [ '<', u'\u2248', '=', '>' ] )
                
                self._width = wx.SpinCtrl( self, max = 200000 )
                
                self._ok = wx.Button( self, id = wx.ID_OK, label='Ok' )
                self._ok.SetDefault()
                self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
                self._ok.SetForegroundColour( ( 0, 128, 0 ) )
                
            
            def PopulateControls():
                
                ( sign, width ) = system_predicates[ 'width' ]
                
                self._sign.SetSelection( sign )
                
                self._width.SetValue( width )
                
            
            def ArrangeControls():
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( wx.StaticText( self, label='system:width' ), FLAGS_MIXED )
                hbox.AddF( self._sign, FLAGS_MIXED )
                hbox.AddF( self._width, FLAGS_MIXED )
                hbox.AddF( self._ok, FLAGS_MIXED )
                
                self.SetSizer( hbox )
                
            
            Dialog.__init__( self, parent, 'enter width predicate' )
            
            InitialiseControls()
            
            PopulateControls()
            
            ArrangeControls()
        
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
            wx.CallAfter( self._ok.SetFocus )
            
        
        def SimilarTo():
            
            def InitialiseControls():
                
                self._hash = wx.TextCtrl( self )
                
                self._max_hamming = wx.SpinCtrl( self, max = 256 )
                
                self._ok = wx.Button( self, id = wx.ID_OK, label='Ok' )
                self._ok.SetDefault()
                self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
                self._ok.SetForegroundColour( ( 0, 128, 0 ) )
                
            
            def PopulateControls():
                
                self._hash.SetValue( 'enter hash' )
                
                self._max_hamming.SetValue( 5 )
                
            
            def ArrangeControls():
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( wx.StaticText( self, label='system:similar_to' ), FLAGS_MIXED )
                hbox.AddF( self._hash, FLAGS_MIXED )
                hbox.AddF( wx.StaticText( self, label=u'\u2248' ), FLAGS_MIXED )
                hbox.AddF( self._max_hamming, FLAGS_MIXED )
                hbox.AddF( self._ok, FLAGS_MIXED )
                
                self.SetSizer( hbox )
                
            
            Dialog.__init__( self, parent, 'enter similar to predicate' )
            
            InitialiseControls()
            
            PopulateControls()
            
            ArrangeControls()
        
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
            wx.CallAfter( self._ok.SetFocus )
            
        
        options = HC.app.Read( 'options' ) # have to do this, since dialog.__init__ hasn't fired yet
        
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
            
        elif media == 'audio':
            
            self._mime_type.Append( 'any', HC.AUDIO )
            self._mime_type.Append( 'mp3', HC.AUDIO_MP3 )
            self._mime_type.Append( 'ogg', HC.AUDIO_OGG )
            self._mime_type.Append( 'flac', HC.AUDIO_FLAC )
            
        elif media == 'video':
            
            self._mime_type.Append( 'x-flv', HC.VIDEO_FLV )
            
        
        self._mime_type.SetSelection( 0 )
        
    
    def EventOK( self, event ):
        
        if self._type == HC.SYSTEM_PREDICATE_TYPE_AGE: info = ( self._sign.GetStringSelection(), self._years.GetValue(), self._months.GetValue(), self._days.GetValue(), self._hours.GetValue() )
        elif self._type == HC.SYSTEM_PREDICATE_TYPE_DURATION: info = ( self._sign.GetStringSelection(), self._duration_s.GetValue() * 1000 + self._duration_ms.GetValue() )
        elif self._type == HC.SYSTEM_PREDICATE_TYPE_HASH:
            
            hex_filter = lambda c: c in string.hexdigits
            
            hash = filter( hex_filter, self._hash.GetValue().lower() )
            
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
            
            hex_filter = lambda c: c in string.hexdigits
            
            hash = filter( hex_filter, lower( self._hash.GetValue() ) )
            
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
                
                self._years = wx.SpinCtrl( self, max = 30 )
                self._months = wx.SpinCtrl( self, max = 60 )
                self._days = wx.SpinCtrl( self, max = 90 )
                
                self._ok = wx.Button( self, label='Ok' )
                self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
                self._ok.SetForegroundColour( ( 0, 128, 0 ) )
                
            
            def PopulateControls():
                
                self._sign.SetSelection( 0 )
                
                self._years.SetValue( 0 )
                self._months.SetValue( 0 )
                self._days.SetValue( 7 )
                
            
            def ArrangeControls():
                
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
                
            
            Dialog.__init__( self, parent, 'enter age predicate' )
            
            InitialiseControls()
            
            ArrangeControls()
        
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
            wx.CallAfter( self._ok.SetFocus )
            
        
        def From():
            
            def InitialiseControls():
                
                contact_names = HC.app.Read( 'contact_names' )
                
                self._contact = wx.Choice( self, choices=contact_names )
                
                self._ok = wx.Button( self, label='Ok' )
                self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
                self._ok.SetForegroundColour( ( 0, 128, 0 ) )
                
            
            def PopulateControls():
                
                self._contact.SetSelection( 0 )
                
            
            def ArrangeControls():
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( wx.StaticText( self, label='system:from' ), FLAGS_MIXED )
                hbox.AddF( self._contact, FLAGS_MIXED )
                hbox.AddF( self._ok, FLAGS_MIXED )
                
                self.SetSizer( hbox )
                
            
            Dialog.__init__( self, parent, 'enter from predicate' )
            
            InitialiseControls()
            
            ArrangeControls()
        
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
            wx.CallAfter( self._ok.SetFocus )
            
        
        def StartedBy():
            
            def InitialiseControls():
                
                contact_names = HC.app.Read( 'contact_names' )
                
                self._contact = wx.Choice( self, choices = contact_names )
                
                self._ok = wx.Button( self, label='Ok' )
                self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
                self._ok.SetForegroundColour( ( 0, 128, 0 ) )
                
            
            def PopulateControls():
                
                self._contact.SetSelection( 0 )
                
            
            def ArrangeControls():
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( wx.StaticText( self, label='system:started_by' ), FLAGS_MIXED )
                hbox.AddF( self._contact, FLAGS_MIXED )
                hbox.AddF( self._ok, FLAGS_MIXED )
                
                self.SetSizer( hbox )
                
            
            Dialog.__init__( self, parent, 'enter started by predicate' )
            
            InitialiseControls()
            
            ArrangeControls()
        
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
            wx.CallAfter( self._ok.SetFocus )
            
        
        def To():
            
            def InitialiseControls():
                
                contact_names = [ name for name in HC.app.Read( 'contact_names' ) if name != 'Anonymous' ]
                
                self._contact = wx.Choice( self, choices = contact_names )
                
                self._ok = wx.Button( self, label='Ok' )
                self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
                self._ok.SetForegroundColour( ( 0, 128, 0 ) )
                
            
            def PopulateControls():
                
                self._contact.SetSelection( 0 )
                
            
            def ArrangeControls():
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( wx.StaticText( self, label='system:to' ), FLAGS_MIXED )
                hbox.AddF( self._contact, FLAGS_MIXED )
                hbox.AddF( self._ok, FLAGS_MIXED )
                
                self.SetSizer( hbox )
                
            
            Dialog.__init__( self, parent, 'enter to predicate' )
            
            InitialiseControls()
            
            ArrangeControls()
        
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
            wx.CallAfter( self._ok.SetFocus )
            
        
        def NumAttachments():
            
            def InitialiseControls():
                
                self._sign = wx.Choice( self, choices=[ '<', '=', '>' ] )
                
                self._num_attachments = wx.SpinCtrl( self, max = 2000 )
                
                self._ok = wx.Button( self, label='Ok' )
                self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
                self._ok.SetForegroundColour( ( 0, 128, 0 ) )
                
            
            def PopulateControls():
                
                self._sign.SetSelection( 0 )
                
                self._num_attachments.SetValue( 4 )
                
            
            def ArrangeControls():
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( wx.StaticText( self, label='system:numattachments' ), FLAGS_MIXED )
                hbox.AddF( self._sign, FLAGS_MIXED )
                hbox.AddF( self._num_attachments, FLAGS_MIXED )
                hbox.AddF( self._ok, FLAGS_MIXED )
                
                self.SetSizer( hbox )
                
            
            Dialog.__init__( self, parent, 'enter number of attachments predicate' )
            
            InitialiseControls()
            
            PopulateControls()
            
            ArrangeControls()
        
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
            wx.CallAfter( self._ok.SetFocus )
            
        
        self._type = type
        
        if self._type == 'system:age': Age()
        elif self._type == 'system:started_by': StartedBy()
        elif self._type == 'system:from': From()
        elif self._type == 'system:to': To()
        elif self._type == 'system:numattachments': NumAttachments()
        
    
    def EventOK( self, event ): self.EndModal( wx.ID_OK )
    
    def GetString( self ):
        
        if self._type == 'system:age': return 'system:age' + self._sign.GetStringSelection() + HC.u( self._years.GetValue() ) + 'y' + HC.u( self._months.GetValue() ) + 'm' + HC.u( self._days.GetValue() ) + 'd'
        elif self._type == 'system:started_by': return 'system:started_by=' + self._contact.GetStringSelection()
        elif self._type == 'system:from': return 'system:from=' + self._contact.GetStringSelection()
        elif self._type == 'system:to': return 'system:to=' + self._contact.GetStringSelection()
        elif self._type == 'system:numattachments': return 'system:numattachments' + self._sign.GetStringSelection() + HC.u( self._num_attachments.GetValue() )
        
    
class DialogInputNamespaceRegex( Dialog ):
    
    def __init__( self, parent, namespace = '', regex = '' ):
        
        def InitialiseControls():
            
            self._namespace = wx.TextCtrl( self )
            
            self._regex = wx.TextCtrl( self )
            
            self._shortcuts = ClientGUICommon.RegexButton( self )
            
            self._ok = wx.Button( self, label='Ok' )
            self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
            self._ok.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label='Cancel' )
            self._cancel.Bind( wx.EVT_BUTTON, self.EventCancel )        
            self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
            
        
        def PopulateControls():
            
            self._namespace.SetValue( namespace )
            self._regex.SetValue( regex )
            
        
        def ArrangeControls():
            
            control_box = wx.BoxSizer( wx.HORIZONTAL )
            
            control_box.AddF( self._namespace, FLAGS_EXPAND_BOTH_WAYS )
            control_box.AddF( wx.StaticText( self, label = ':' ), FLAGS_MIXED )
            control_box.AddF( self._regex, FLAGS_EXPAND_BOTH_WAYS )
            
            b_box = wx.BoxSizer( wx.HORIZONTAL )
            b_box.AddF( self._ok, FLAGS_MIXED )
            b_box.AddF( self._cancel, FLAGS_MIXED )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( control_box, FLAGS_EXPAND_SIZER_PERPENDICULAR )
            vbox.AddF( self._shortcuts, FLAGS_LONE_BUTTON )
            vbox.AddF( b_box, FLAGS_BUTTON_SIZERS )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
        
        Dialog.__init__( self, parent, 'configure quick namespace' )
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
        wx.CallAfter( self._ok.SetFocus )
        
    
    def EventCancel( self, event ): self.EndModal( wx.ID_CANCEL )
    
    def EventOK( self, event ): self.EndModal( wx.ID_OK )
    
    def GetInfo( self ):
        
        namespace = self._namespace.GetValue()
        
        regex = self._regex.GetValue()
        
        return ( namespace, regex )
        
    
class DialogInputNewAccounts( Dialog ):
    
    def __init__( self, parent, service_identifier ):
        
        def InitialiseControls():
            
            self._num = wx.SpinCtrl( self, min=1, max=10000 )
            
            self._account_types = wx.Choice( self, size = ( 400, -1 ) )
            
            self._expiration = wx.Choice( self )
            
            self._ok = wx.Button( self, label='Ok' )
            self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
            self._ok.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label='Cancel' )
            self._cancel.Bind( wx.EVT_BUTTON, self.EventCancel )        
            self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
            
        
        def PopulateControls():
            
            self._num.SetValue( 1 )
            
            service = HC.app.Read( 'service', service_identifier )
            
            connection = service.GetConnection()
            
            account_types = connection.Get( 'account_types' )
            
            for account_type in account_types: self._account_types.Append( account_type.ConvertToString(), account_type )
            self._account_types.SetSelection( 0 ) # admin
            
            for ( str, value ) in HC.expirations: self._expiration.Append( str, value )
            self._expiration.SetSelection( 3 ) # one year
            
        
        def ArrangeControls():
            
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
        
        PopulateControls()
        
        ArrangeControls()
        
        wx.CallAfter( self._ok.SetFocus )
        
    
    def EventCancel( self, event ): self.EndModal( wx.ID_CANCEL )
    
    def EventOK( self, event ):
        
        num = self._num.GetValue()
        
        account_type = self._account_types.GetClientData( self._account_types.GetSelection() )
        
        title = account_type.GetTitle()
        
        expiration = self._expiration.GetClientData( self._expiration.GetSelection() )
        
        service = HC.app.Read( 'service', self._service_identifier )
        
        try:
            
            connection = service.GetConnection()
            
            if expiration is None: access_keys = connection.Get( 'registration_keys', num = num, title = title )
            else: access_keys = connection.Get( 'registration_keys', num = num, title = title, expiration = expiration )
            
        except Exception as e: wx.MessageBox( HC.u( e ) )
        
        self.EndModal( wx.ID_OK )
        
    
class DialogInputNewAccountType( Dialog ):
    
    def __init__( self, parent, account_type = None ):
        
        def InitialiseControls():
            
            self._title = wx.TextCtrl( self )
            
            self._permissions_panel = ClientGUICommon.StaticBox( self, 'permissions' )
            
            self._permissions = wx.ListBox( self._permissions_panel )
            
            self._permission_choice = wx.Choice( self._permissions_panel )
            
            self._add_permission = wx.Button( self._permissions_panel, label = 'add' )
            self._add_permission.Bind( wx.EVT_BUTTON, self.EventAddPermission )
            
            self._remove_permission = wx.Button( self._permissions_panel, label = 'remove' )
            self._remove_permission.Bind( wx.EVT_BUTTON, self.EventRemovePermission )
            
            self._max_num_mb = ClientGUICommon.NoneableSpinCtrl( self, 'max monthly data (MB)', multiplier = 1048576 )
            self._max_num_mb.SetValue( max_num_bytes )
            
            self._max_num_requests = ClientGUICommon.NoneableSpinCtrl( self, 'max monthly requests' )
            self._max_num_requests.SetValue( max_num_requests )
            
            self._apply = wx.Button( self, label='apply' )
            self._apply.Bind( wx.EVT_BUTTON, self.EventOK )
            self._apply.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label='cancel' )
            self._cancel.Bind( wx.EVT_BUTTON, self.EventCancel )        
            self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
            
        
        def PopulateControls():
            
            self._title.SetValue( title )
            
            for permission in permissions: self._permissions.Append( HC.permissions_string_lookup[ permission ], permission )
            
            for permission in HC.CREATABLE_PERMISSIONS: self._permission_choice.Append( HC.permissions_string_lookup[ permission ], permission )
            self._permission_choice.SetSelection( 0 )
            
        
        def ArrangeControls():
            
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
        
        PopulateControls()
        
        ArrangeControls()
        
        wx.CallAfter( self._apply.SetFocus )
        
    
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
        
    
    def EventOK( self, event ): self.EndModal( wx.ID_OK )
    
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
        
        def InitialiseControls():
            
            self._name = wx.TextCtrl( self )
            
            self._type = wx.Choice( self )
            
            self._default = wx.TextCtrl( self )
            
            self._editable = wx.CheckBox( self )
            
            self._ok = wx.Button( self, label='Ok' )
            self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
            self._ok.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label='Cancel' )
            self._cancel.Bind( wx.EVT_BUTTON, self.EventCancel )        
            self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
            
        
        def PopulateControls():
            
            self._name.SetValue( name )
            
            for temp_type in CC.FIELDS: self._type.Append( CC.field_string_lookup[ temp_type ], temp_type )
            self._type.Select( type )
            
            self._default.SetValue( default )
            
            self._editable.SetValue( editable )
            
        
        def ArrangeControls():
            
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
        
        if form_field is None: ( name, type, default, editable ) = ( '', CC.FIELD_TEXT, '', True )
        else: ( name, type, default, editable ) = form_field
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
        wx.CallAfter( self._ok.SetFocus )
        
    
    def EventCancel( self, event ): self.EndModal( wx.ID_CANCEL )
    
    def EventOK( self, event ): self.EndModal( wx.ID_OK )
    
    def GetFormField( self ):
        
        name = self._name.GetValue()
        
        type = self._type.GetClientData( self._type.GetSelection() )
        
        default = self._default.GetValue()
        
        editable = self._editable.GetValue()
        
        return ( name, type, default, editable )
        
    
class DialogInputShortcut( Dialog ):
    
    def __init__( self, parent, modifier = wx.ACCEL_NORMAL, key = wx.WXK_F7, action = 'new_page' ):
        
        self._action = action
        
        def InitialiseControls():
            
            self._shortcut = ClientGUICommon.Shortcut( self, modifier, key )
            
            self._actions = wx.Choice( self, choices = [ 'archive', 'inbox', 'close_page', 'filter', 'fullscreen_switch', 'ratings_filter', 'frame_back', 'frame_next', 'manage_ratings', 'manage_tags', 'new_page', 'refresh', 'set_search_focus', 'show_hide_splitters', 'synchronised_wait_switch', 'previous', 'next', 'first', 'last' ] )
            
            self._ok = wx.Button( self, label='Ok' )
            self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
            self._ok.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label='Cancel' )
            self._cancel.Bind( wx.EVT_BUTTON, self.EventCancel )        
            self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
            
    
        def PopulateControls():
            
            self._actions.SetSelection( self._actions.FindString( action ) )
            
        
        def ArrangeControls():
            
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
        
        PopulateControls()
        
        ArrangeControls()
        
        wx.CallAfter( self._ok.SetFocus )
        
    
    def EventCancel( self, event ): self.EndModal( wx.ID_CANCEL )
    
    def EventOK( self, event ): self.EndModal( wx.ID_OK )
    
    def GetInfo( self ):
        
        ( modifier, key ) = self._shortcut.GetValue()
        
        return ( modifier, key, self._actions.GetStringSelection() )
        
    
class DialogMessage( Dialog ):
    
    def __init__( self, parent, message, ok_label = 'ok' ):
        
        def InitialiseControls():
            
            self._ok = wx.Button( self, id = wx.ID_CANCEL, label = ok_label )
            self._ok.SetForegroundColour( ( 0, 128, 0 ) )
            
        
        def PopulateControls():
            
            pass
            
        
        def ArrangeControls():
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            text = wx.StaticText( self, label = HC.u( message ) )
            
            text.Wrap( 480 )
            
            vbox.AddF( text, FLAGS_BIG_INDENT )
            vbox.AddF( self._ok, FLAGS_BUTTON_SIZERS )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
        
        Dialog.__init__( self, parent, 'message', position = 'center' )
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
        wx.CallAfter( self._ok.SetFocus )
        
    
class DialogModifyAccounts( Dialog ):
    
    def __init__( self, parent, service_identifier, subject_identifiers ):
        
        def InitialiseControls():
            
            self._account_info_panel = ClientGUICommon.StaticBox( self, 'account info' )
            
            self._subject_text = wx.StaticText( self._account_info_panel )
            
            #
            
            self._account_types_panel = ClientGUICommon.StaticBox( self, 'account types' )
            
            self._account_types = wx.Choice( self._account_types_panel )
            
            self._account_types_ok = wx.Button( self._account_types_panel, label = 'Ok' )
            self._account_types_ok.Bind( wx.EVT_BUTTON, self.EventChangeAccountType )
            
            #
            
            self._expiration_panel = ClientGUICommon.StaticBox( self, 'change expiration' )
            
            self._add_to_expires = wx.Choice( self._expiration_panel )
            
            self._add_to_expires_ok = wx.Button( self._expiration_panel, label = 'Ok' )
            self._add_to_expires_ok.Bind( wx.EVT_BUTTON, self.EventAddToExpires )
            
            self._set_expires = wx.Choice( self._expiration_panel )
            
            self._set_expires_ok = wx.Button( self._expiration_panel, label = 'Ok' )
            self._set_expires_ok.Bind( wx.EVT_BUTTON, self.EventSetExpires )
            
            #
            
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
            
    
        def PopulateControls():
            
            connection = self._service.GetConnection()
            
            if len( self._subject_identifiers ) == 1:
                
                ( subject_identifier, ) = self._subject_identifiers
                
                subject_string = connection.Get( 'account_info', subject_identifier = subject_identifier )
                
            else: subject_string = 'modifying ' + HC.ConvertIntToPrettyString( len( self._subject_identifiers ) ) + ' accounts'
            
            self._subject_text.SetLabel( subject_string )
            
            #
            
            account_types = connection.Get( 'account_types' )
            
            for account_type in account_types: self._account_types.Append( account_type.ConvertToString(), account_type )
            
            self._account_types.SetSelection( 0 )
            
            #
            
            for ( string, value ) in HC.expirations:
                
                if value is not None: self._add_to_expires.Append( string, value ) # don't want 'add no limit'
                
            
            self._add_to_expires.SetSelection( 1 ) # three months
            
            for ( string, value ) in HC.expirations: self._set_expires.Append( string, value )
            self._set_expires.SetSelection( 1 ) # three months
            
            #
            
            if not self._service.GetAccount().HasPermission( HC.GENERAL_ADMIN ):
                
                self._account_types_ok.Disable()
                self._add_to_expires_ok.Disable()
                self._set_expires_ok.Disable()
                
            
        
        def ArrangeControls():
            
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
        
        self._service = HC.app.Read( 'service', service_identifier )
        self._subject_identifiers = set( subject_identifiers )
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
        wx.CallAfter( self._exit.SetFocus )
        
    
    def _DoModification( self, action, **kwargs ):
        
        try:
            
            connection = self._service.GetConnection()
            
            kwargs[ 'subject_identifiers' ] = list( self._subject_identifiers )
            kwargs[ 'action' ] = action
            
            connection.Post( 'account_modification', **kwargs )
            
            if len( self._subject_identifiers ) == 1:
                
                ( subject_identifier, ) = self._subject_identifiers
                
                self._subject_text.SetLabel( HC.u( connection.Get( 'account_info', subject_identifier = subject_identifier ) ) )
                
            
        except Exception as e: wx.MessageBox( HC.u( e ) )
        
        if len( self._subject_identifiers ) > 1: wx.MessageBox( 'Done!' )
        
    
    def EventAddToExpires( self, event ): self._DoModification( HC.ADD_TO_EXPIRES, expiration = self._add_to_expires.GetClientData( self._add_to_expires.GetSelection() ) )
    
    def EventBan( self, event ):
        
        with wx.TextEntryDialog( self, 'Enter reason for the ban' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK: self._DoModification( HC.BAN, reason = dlg.GetValue() )
            
        
    
    def EventChangeAccountType( self, event ): self._DoModification( HC.CHANGE_ACCOUNT_TYPE, title = self._account_types.GetClientData( self._account_types.GetSelection() ).GetTitle() )
    
    def EventSetExpires( self, event ):
        
        expires = self._set_expires.GetClientData( self._set_expires.GetSelection() )
        
        if expires is not None: expires += HC.GetNow()
        
        self._DoModification( HC.SET_EXPIRES, expiry = expires )
        
    
    def EventSuperban( self, event ):
        
        with wx.TextEntryDialog( self, 'Enter reason for the superban' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK: self._DoModification( HC.SUPERBAN, reason = dlg.GetValue() )
            
        
    
class DialogNews( Dialog ):
    
    def __init__( self, parent, service_identifier ):
        
        def InitialiseControls():
            
            self._news = wx.TextCtrl( self, style = wx.TE_READONLY | wx.TE_MULTILINE )
            
            self._previous = wx.Button( self, label = '<' )
            self._previous.Bind( wx.EVT_BUTTON, self.EventPrevious )
            
            self._news_position = wx.TextCtrl( self )
            
            self._next = wx.Button( self, label = '>' )
            self._next.Bind( wx.EVT_BUTTON, self.EventNext )
            
            self._done = wx.Button( self, id = wx.ID_CANCEL, label = 'Done' )
            self._done.Bind( wx.EVT_BUTTON, self.EventOK )
            
    
        def PopulateControls():
            
            self._newslist = HC.app.Read( 'news', service_identifier )
            
            self._current_news_position = len( self._newslist )
            
            self._ShowNews()
            
        
        def ArrangeControls():
            
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
        
        PopulateControls()
        
        ArrangeControls()
        
        wx.CallAfter( self._done.SetFocus )
        
    
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
        
    
    def EventOK( self, event ): self.EndModal( wx.ID_OK )
    
    def EventPrevious( self, event ):
        
        if self._current_news_position > 1: self._current_news_position -= 1
        
        self._ShowNews()
        
    
class DialogPathsToTagsRegex( Dialog ):
    
    def __init__( self, parent, paths ):
        
        def InitialiseControls():
            
            self._tag_repositories = ClientGUICommon.ListBook( self )
            self._tag_repositories.Bind( wx.EVT_NOTEBOOK_PAGE_CHANGED, self.EventServiceChanged )
            
            self._add_button = wx.Button( self, label='Import Files' )
            self._add_button.Bind( wx.EVT_BUTTON, self.EventOK )
            self._add_button.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label='Back to File Selection' )
            self._cancel.Bind( wx.EVT_BUTTON, self.EventCancel )
            self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
            
        
        def PopulateControls():
            
            services = HC.app.Read( 'services', ( HC.TAG_REPOSITORY, ) )
            
            for service in services:
                
                account = service.GetAccount()
                
                if account.HasPermission( HC.POST_DATA ):
                    
                    service_identifier = service.GetServiceIdentifier()
                    
                    page_info = ( self._Panel, ( self._tag_repositories, service_identifier, paths ), {} )
                    
                    name = service_identifier.GetName()
                    
                    self._tag_repositories.AddPage( page_info, name )
                    
                
            
            page = self._Panel( self._tag_repositories, HC.LOCAL_TAG_SERVICE_IDENTIFIER, paths )
            
            name = HC.LOCAL_TAG_SERVICE_IDENTIFIER.GetName()
            
            self._tag_repositories.AddPage( page, name )
            
            default_tag_repository = self._options[ 'default_tag_repository' ]
            
            self._tag_repositories.Select( default_tag_repository.GetName() )
            
        
        def ArrangeControls():
            
            buttons = wx.BoxSizer( wx.HORIZONTAL )
            
            buttons.AddF( self._add_button, FLAGS_SMALL_INDENT )
            buttons.AddF( self._cancel, FLAGS_SMALL_INDENT )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( self._tag_repositories, FLAGS_EXPAND_BOTH_WAYS )
            vbox.AddF( buttons, FLAGS_BUTTON_SIZERS )
            
            self.SetSizer( vbox )
            
            self.SetInitialSize( ( 980, 680 ) )
            
        
        Dialog.__init__( self, parent, 'path tagging' )
        
        self._paths = paths
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
        interested_actions = [ 'set_search_focus' ]
        
        entries = []
        
        for ( modifier, key_dict ) in self._options[ 'shortcuts' ].items(): entries.extend( [ ( modifier, key, CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( action ) ) for ( key, action ) in key_dict.items() if action in interested_actions ] )
        
        self.SetAcceleratorTable( wx.AcceleratorTable( entries ) )
        
        self.Bind( wx.EVT_MENU, self.EventMenu )
        
        wx.CallAfter( self._add_button.SetFocus )
        
    
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
                
                wx.MessageBox( HC.u( e ) )
                wx.MessageBox( traceback.format_exc() )
                
            
        
    
    def EventOK( self, event ): self.EndModal( wx.ID_OK )
    
    def EventServiceChanged( self, event ):
        
        page = self._tag_repositories.GetCurrentPage()
        
        wx.CallAfter( page.SetTagBoxFocus )
        
    
    def GetInfo( self ):
        
        paths_to_tags = collections.defaultdict( dict )
        
        try:
            
            for page in self._tag_repositories.GetNameToPageDict().values():
                
                page_of_paths_to_tags = page.GetInfo()
                
                service_identifier = page.GetServiceIdentifier()
                
                for ( path, tags ) in page_of_paths_to_tags.items(): paths_to_tags[ path ][ service_identifier ] = tags
                
            
        except Exception as e: wx.MessageBox( 'Saving regex tags to DB raised this error: ' + HC.u( e ) )
        
        return paths_to_tags
        
    
    class _Panel( wx.Panel ):
        
        def __init__( self, parent, service_identifier, paths ):
            
            def InitialiseControls():
                
                self._paths_list = ClientGUICommon.SaneListCtrl( self, 250, [ ( '#', 50 ), ( 'path', 400 ), ( 'tags', -1 ) ] )
                
                self._paths_list.Bind( wx.EVT_LIST_ITEM_SELECTED, self.EventItemSelected )
                self._paths_list.Bind( wx.EVT_LIST_ITEM_DESELECTED, self.EventItemSelected )
                
                #
                
                self._quick_namespaces_panel = ClientGUICommon.StaticBox( self, 'quick namespaces' )
                
                self._quick_namespaces_list = ClientGUICommon.SaneListCtrl( self._quick_namespaces_panel, 200, [ ( 'namespace', 80 ), ( 'regex', -1 ) ] )
                
                self._add_quick_namespace_button = wx.Button( self._quick_namespaces_panel, label = 'add' )
                self._add_quick_namespace_button.Bind( wx.EVT_BUTTON, self.EventAddQuickNamespace )
                
                self._edit_quick_namespace_button = wx.Button( self._quick_namespaces_panel, label = 'edit' )
                self._edit_quick_namespace_button.Bind( wx.EVT_BUTTON, self.EventEditQuickNamespace )
                
                self._delete_quick_namespace_button = wx.Button( self._quick_namespaces_panel, label = 'delete' )
                self._delete_quick_namespace_button.Bind( wx.EVT_BUTTON, self.EventDeleteQuickNamespace )
                
                self._regex_shortcuts = ClientGUICommon.RegexButton( self._quick_namespaces_panel )
                
                self._regex_link = wx.HyperlinkCtrl( self._quick_namespaces_panel, id = -1, label = 'a good regex introduction', url = 'http://www.aivosto.com/vbtips/regex.html' )
                
                #
                
                self._regexes_panel = ClientGUICommon.StaticBox( self, 'regexes' )
                
                self._regexes = wx.ListBox( self._regexes_panel )
                self._regexes.Bind( wx.EVT_LISTBOX_DCLICK, self.EventRemoveRegex )
                
                self._regex_box = wx.TextCtrl( self._regexes_panel, style=wx.TE_PROCESS_ENTER )
                self._regex_box.Bind( wx.EVT_TEXT_ENTER, self.EventAddRegex )
                
                #
                
                self._num_panel = ClientGUICommon.StaticBox( self, '#' )
                
                self._num_namespace = wx.TextCtrl( self._num_panel )
                self._num_namespace.Bind( wx.EVT_TEXT, self.EventNumNamespaceChanged )
                
                #
                
                self._tags_panel = ClientGUICommon.StaticBox( self, 'tags for all' )
                
                self._tags = ClientGUICommon.TagsBoxFlat( self._tags_panel, self.TagRemoved )
                
                self._tag_box = ClientGUICommon.AutoCompleteDropdownTagsWrite( self._tags_panel, self.AddTag, HC.LOCAL_FILE_SERVICE_IDENTIFIER, service_identifier )
                
                #
                
                self._single_tags_panel = ClientGUICommon.StaticBox( self, 'tags just for this file' )
                
                self._paths_to_single_tags = collections.defaultdict( list )
                
                self._single_tags = ClientGUICommon.TagsBoxFlat( self._single_tags_panel, self.SingleTagRemoved )
                
                self._single_tag_box = ClientGUICommon.AutoCompleteDropdownTagsWrite( self._single_tags_panel, self.AddTagSingle, HC.LOCAL_FILE_SERVICE_IDENTIFIER, service_identifier )
                
            
            def PopulateControls():
                
                for ( num, path ) in enumerate( self._paths, 1 ):
                    
                    pretty_num = HC.ConvertIntToPrettyString( num )
                    
                    tags = self._GetTags( num, path )
                    
                    tags_string = ', '.join( tags )
                    
                    self._paths_list.Append( ( pretty_num, path, tags_string ), ( num, path, tags ) )
                    
                
                self._single_tag_box.Disable()
                
            
            def ArrangeControls():
                
                button_box = wx.BoxSizer( wx.HORIZONTAL )
                
                button_box.AddF( self._add_quick_namespace_button, FLAGS_MIXED )
                button_box.AddF( self._edit_quick_namespace_button, FLAGS_MIXED )
                button_box.AddF( self._delete_quick_namespace_button, FLAGS_MIXED )
                
                self._quick_namespaces_panel.AddF( self._quick_namespaces_list, FLAGS_EXPAND_PERPENDICULAR )
                self._quick_namespaces_panel.AddF( button_box, FLAGS_BUTTON_SIZERS )
                self._quick_namespaces_panel.AddF( self._regex_shortcuts, FLAGS_LONE_BUTTON )
                self._quick_namespaces_panel.AddF( self._regex_link, FLAGS_LONE_BUTTON )
                
                #
                
                self._regexes_panel.AddF( self._regexes, FLAGS_EXPAND_BOTH_WAYS )
                self._regexes_panel.AddF( self._regex_box, FLAGS_EXPAND_PERPENDICULAR )
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( wx.StaticText( self._num_panel, label = '# namespace: ' ), FLAGS_MIXED )
                hbox.AddF( self._num_namespace, FLAGS_EXPAND_BOTH_WAYS )
                
                self._num_panel.AddF( hbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
                
                second_vbox = wx.BoxSizer( wx.VERTICAL )
                
                second_vbox.AddF( self._regexes_panel, FLAGS_EXPAND_BOTH_WAYS )
                second_vbox.AddF( self._num_panel, FLAGS_EXPAND_PERPENDICULAR )
                
                #
                
                self._tags_panel.AddF( self._tags, FLAGS_EXPAND_BOTH_WAYS )
                self._tags_panel.AddF( self._tag_box, FLAGS_EXPAND_PERPENDICULAR )
                
                self._single_tags_panel.AddF( self._single_tags, FLAGS_EXPAND_BOTH_WAYS )
                self._single_tags_panel.AddF( self._single_tag_box, FLAGS_EXPAND_PERPENDICULAR )
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( self._quick_namespaces_panel, FLAGS_EXPAND_BOTH_WAYS )
                hbox.AddF( second_vbox, FLAGS_EXPAND_SIZER_BOTH_WAYS )
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
            
            PopulateControls()
            
            ArrangeControls()
            
        
        
        def _GetTags( self, num, path ):
            
            tags = []
            
            tags.extend( self._tags.GetTags() )
            
            for regex in self._regexes.GetStrings():
                
                try:
                    
                    m = re.search( regex, path )
                    
                    if m is not None:
                        
                        match = m.group()
                        
                        if len( match ) > 0: tags.append( match )
                        
                    
                except: pass
                
            
            for ( namespace, regex ) in self._quick_namespaces_list.GetClientData():
                
                try:
                    
                    m = re.search( regex, path )
                    
                    if m is not None:
                        
                        match = m.group()
                        
                        if len( match ) > 0: tags.append( namespace + ':' + match )
                        
                    
                except: pass
                
            
            if path in self._paths_to_single_tags: tags.extend( self._paths_to_single_tags[ path ] )
            
            num_namespace = self._num_namespace.GetValue()
            
            if num_namespace != '':
                
                tags.append( num_namespace + ':' + HC.u( num ) )
                
            
            tags = [ HC.CleanTag( tag ) for tag in tags ]
            
            return tags
            
        
        def _RefreshFileList( self ):
            
            for ( index, ( num, path, old_tags ) ) in enumerate( self._paths_list.GetClientData() ):
                
                # when doing regexes, make sure not to include '' results, same for system: and - started tags.
                
                tags = self._GetTags( num, path )
                
                if tags != old_tags:
                    
                    pretty_num = HC.ConvertIntToPrettyString( num )
                    
                    tags_string = ', '.join( tags )
                    
                    self._paths_list.UpdateRow( index, ( pretty_num, path, tags_string ), ( num, path, tags ) )
                    
                
            
        
        def AddTag( self, tag, parents = [] ):
            
            if tag is not None:
                
                self._tags.AddTag( tag, parents )
                
                self._tag_box.Clear()
                
                self._RefreshFileList()
                
            
        
        def AddTagSingle( self, tag, parents = [] ):
            
            if tag is not None:
                
                self._single_tags.AddTag( tag, parents )
                
                self._single_tag_box.Clear()
                
                indices = self._paths_list.GetAllSelected()
                
                for index in indices:
                    
                    ( num, path, old_tags ) = self._paths_list.GetClientData( index )
                    
                    if tag not in self._paths_to_single_tags[ path ]: self._paths_to_single_tags[ path ].append( tag )
                    
                    for parent in parents:
                        
                        if parent not in self._paths_to_single_tags[ path ]: self._paths_to_single_tags[ path ].append( parent )
                        
                    
                
                self._RefreshFileList() # make this more clever
                
            
        
        def EventAddRegex( self, event ):
            
            regex = self._regex_box.GetValue()
            
            if regex != '':
                
                self._regexes.Append( regex )
                
                self._regex_box.Clear()
                
                self._RefreshFileList()
                
            
        
        def EventAddQuickNamespace( self, event ):
            
            with DialogInputNamespaceRegex( self ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    ( namespace, regex ) = dlg.GetInfo()
                    
                    self._quick_namespaces_list.Append( ( namespace, regex ), ( namespace, regex ) )
                    
                    self._RefreshFileList()
                    
                
            
        
        def EventDeleteQuickNamespace( self, event ):
            
            self._quick_namespaces_list.RemoveAllSelected()
            
            self._RefreshFileList()
            
        
        def EventEditQuickNamespace( self, event ):
            
            for index in self._quick_namespaces_list.GetAllSelected():
                
                ( namespace, regex ) = self._quick_namespaces_list.GetClientData( index = index )
                
                with DialogInputNamespaceRegex( self, namespace = namespace, regex = regex ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        ( namespace, regex ) = dlg.GetInfo()
                        
                        self._quick_namespaces_list.UpdateRow( index, ( namespace, regex ), ( namespace, regex ) )
                        
                    
                
            
            self._RefreshFileList()
            
        
        def EventItemSelected( self, event ):
            
            single_tags = set()
            
            indices = self._paths_list.GetAllSelected()
            
            if len( indices ) > 0:
                
                for index in indices:
                    
                    path = self._paths_list.GetClientData( index )[1]
                    
                    if path in self._paths_to_single_tags: single_tags.update( self._paths_to_single_tags[ path ] )
                    
                
                self._single_tag_box.Enable()
                
            else: self._single_tag_box.Disable()
            
            self._single_tags.SetTags( single_tags )
            
        
        def EventNumNamespaceChanged( self, event ): self._RefreshFileList()
        
        def EventRemoveRegex( self, event ):
            
            selection = self._regexes.GetSelection()
            
            if selection != wx.NOT_FOUND:
                
                if len( self._regex_box.GetValue() ) == 0: self._regex_box.SetValue( self._regexes.GetString( selection ) )
                
                self._regexes.Delete( selection )
                
                self._RefreshFileList()
                
            
        
        def GetInfo( self ): return { path : tags for ( num, path, tags ) in self._paths_list.GetClientData() }
        
        def GetServiceIdentifier( self ): return self._service_identifier
        
        def SetTagBoxFocus( self ): self._tag_box.SetFocus()
        
        def SingleTagRemoved( self, tag ):
            
            indices = self._paths_list.GetAllSelected()
            
            for index in indices:
                
                ( num, path, old_tags ) = self._paths_list.GetClientData( index )
                
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
            
        
        def PopulateControls():
            
            pass
            
        
        def ArrangeControls():
            
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
        
        PopulateControls()
        
        ArrangeControls()
        
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
            
            self._address = wx.TextCtrl( self )
            self._registration_key = wx.TextCtrl( self )
            
            self._register = wx.Button( self, label = 'register' )
            self._register.Bind( wx.EVT_BUTTON, self.EventRegister )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'cancel' )
            
        
        def PopulateControls():
            
            self._address.SetValue( 'hostname:port' )
            self._registration_key.SetValue( 'r0000000000000000000000000000000000000000000000000000000000000000' )
            
        
        def ArrangeControls():
            
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
        
        PopulateControls()
        
        ArrangeControls()
        
        self._register = False
        
        wx.CallAfter( self._register.SetFocus )
        
    
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
            
        
        connection = HC.get_connection( host = host, port = port )
        
        headers = {}
        
        headers[ 'Authorization' ] = 'hydrus_network ' + registration_key.encode( 'hex' )
        
        try: access_key = connection.request( 'GET', '/access_key', headers = headers )
        except Exception as e:
            
            wx.MessageBox( HC.u( e ) )
            
            return
            
        
        self._credentials = CC.Credentials( host, port, access_key )
        
        self.EndModal( wx.ID_OK )
        
    
    def GetCredentials( self ): return self._credentials
    
class DialogSelectBooru( Dialog ):
    
    def __init__( self, parent ):
        
        def InitialiseControls():
            
            self._boorus = wx.ListBox( self, style = wx.LB_SORT )
            self._boorus.Bind( wx.EVT_LISTBOX_DCLICK, self.EventDoubleClick )
            
            self._ok = wx.Button( self, id = wx.ID_OK, size = ( 0, 0 ) )
            self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
            self._ok.SetDefault()
            
    
        def PopulateControls():
            
            boorus = HC.app.Read( 'boorus' )
            
            for booru in boorus: self._boorus.Append( booru.GetName(), booru )
            
        
        def ArrangeControls():
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( self._boorus, FLAGS_EXPAND_PERPENDICULAR )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            if x < 320: x = 320
            
            self.SetInitialSize( ( x, y ) )
            
        
        Dialog.__init__( self, parent, 'select booru' )
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
        wx.CallAfter( self._ok.SetFocus )
        
    
    def EventDoubleClick( self, event ): self.EndModal( wx.ID_OK )
    
    def EventOK( self, event ):
    
        selection = self._boorus.GetSelection()
        
        if selection != wx.NOT_FOUND: self.EndModal( wx.ID_OK )
        
    
    def GetBooru( self ): return self._boorus.GetClientData( self._boorus.GetSelection() )
    
class DialogSelectImageboard( Dialog ):
    
    def __init__( self, parent ):
        
        def InitialiseControls():
            
            self._tree = wx.TreeCtrl( self )
            self._tree.Bind( wx.EVT_TREE_ITEM_ACTIVATED, self.EventSelect )
            
        
        def PopulateControls():
            
            all_imageboards = HC.app.Read( 'imageboards' )
            
            root_item = self._tree.AddRoot( 'all sites' )
            
            for ( site, imageboards ) in all_imageboards:
                
                site_item = self._tree.AppendItem( root_item, site )
                
                for imageboard in imageboards:
                    
                    name = imageboard.GetName()
                    
                    self._tree.AppendItem( site_item, name, data = wx.TreeItemData( imageboard ) )
                    
                
            
            self._tree.Expand( root_item )
            
        
        def ArrangeControls():
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( self._tree, FLAGS_EXPAND_BOTH_WAYS )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            if x < 320: x = 320
            if y < 640: y = 640
            
            self.SetInitialSize( ( x, y ) )
            
        
        Dialog.__init__( self, parent, 'select imageboard' )
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
    
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
            
            self._ok = wx.Button( self, id = wx.ID_OK, size = ( 0, 0 ) )
            self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
            self._ok.SetDefault()
            
    
        def PopulateControls():
            
            pass
            
        
        def ArrangeControls():
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( self._strings, FLAGS_EXPAND_PERPENDICULAR )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            if x < 320: x = 320
            
            self.SetInitialSize( ( x, y ) )
            
        
        Dialog.__init__( self, parent, title )
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
    
    def EventKeyDown( self, event ):
        
        if event.KeyCode == wx.WXK_SPACE:
            
            selection = self._strings.GetSelection()
            
            if selection != wx.NOT_FOUND: self.EndModal( wx.ID_OK )
            
        else: event.Skip()
        
    
    def EventOK( self, event ):
        
        selection = self._strings.GetSelection()
        
        if selection != wx.NOT_FOUND: self.EndModal( wx.ID_OK )
        
    
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
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label='Cancel' )
            self._cancel.Bind( wx.EVT_BUTTON, self.EventCancel )
            self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
            
            self._delete_after_success = wx.CheckBox( self, label = 'delete files after successful import' )
            
            self._advanced_import_options = ClientGUICommon.AdvancedImportOptions( self )
            
            self._add_files_button = wx.Button( self, label='Add Files' )
            self._add_files_button.Bind( wx.EVT_BUTTON, self.EventAddPaths )
            
            self._add_folder_button = wx.Button( self, label='Add Folder' )
            self._add_folder_button.Bind( wx.EVT_BUTTON, self.EventAddFolder )
            
            self._remove_files_button = wx.Button( self, label='Remove Files' )
            self._remove_files_button.Bind( wx.EVT_BUTTON, self.EventRemovePaths )
            
    
        def PopulateControls():
            
            pass
            
        
        def ArrangeControls():
            
            file_buttons = wx.BoxSizer( wx.HORIZONTAL )
            
            file_buttons.AddF( ( 20, 0 ), FLAGS_NONE )
            file_buttons.AddF( self._add_files_button, FLAGS_MIXED )
            file_buttons.AddF( self._add_folder_button, FLAGS_MIXED )
            file_buttons.AddF( self._remove_files_button, FLAGS_MIXED )
            
            buttons = wx.BoxSizer( wx.HORIZONTAL )
            
            buttons.AddF( self._add_button, FLAGS_MIXED )
            buttons.AddF( self._tag_button, FLAGS_MIXED )
            buttons.AddF( self._cancel, FLAGS_MIXED )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( self._paths_list, FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( file_buttons, FLAGS_BUTTON_SIZERS )
            vbox.AddF( self._advanced_import_options, FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._delete_after_success, FLAGS_LONE_BUTTON )
            vbox.AddF( ( 0, 5 ), FLAGS_NONE )
            vbox.AddF( buttons, FLAGS_BUTTON_SIZERS )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
        
        Dialog.__init__( self, parent, 'importing files' )
        
        self.SetDropTarget( ClientGUICommon.FileDropTarget( self._AddPathsToList ) )
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
        self._AddPathsToList( paths )
        
        wx.CallAfter( self._add_button.SetFocus )
        
    
    
    def _AddPathsToList( self, paths ):
        
        good_paths_info = CC.ParseImportablePaths( paths )
        
        odd_paths = False
        
        for ( path_type, mime, size, path_info ) in good_paths_info:
            
            pretty_size = HC.ConvertIntToBytes( size )
            
            if path_type == 'path': pretty_path = path_info
            elif path_type == 'zip':
                
                ( zip_path, name ) = path_info
                
                pretty_path = zip_path + os.path.sep + name
                
            
            self._paths_list.Append( ( pretty_path, HC.mime_string_lookup[ mime ], pretty_size ), ( ( path_type, path_info ), mime, size ) )
            
        
        if odd_paths: wx.MessageBox( HC.u( len( odd_paths ) ) + ' files could not be added.' )
        
    
    def _GetPathsInfo( self ): return [ row[0] for row in self._paths_list.GetClientData() ]
    
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
        
        paths_info = self._GetPathsInfo()
        
        if len( paths_info ) > 0:
            
            advanced_import_options = self._advanced_import_options.GetInfo()
            
            delete_after_success = self._delete_after_success.GetValue()
            
            HC.pubsub.pub( 'new_hdd_import', paths_info, advanced_import_options = advanced_import_options, delete_after_success = delete_after_success )
            
            self.EndModal( wx.ID_OK )
            
        
    
    def EventRemovePaths( self, event ): self._paths_list.RemoveAllSelected()
    
    def EventTags( self, event ):
        
        try:
            
            paths_info = self._GetPathsInfo()
            
            if len( paths_info ) > 0:
                
                advanced_import_options = self._advanced_import_options.GetInfo()
                
                paths_to_send_to_dialog = []
                
                for ( path_type, path_info ) in paths_info:
                    
                    if path_type == 'path': pretty_path = path_info
                    elif path_type == 'zip':
                        
                        ( zip_path, name ) = path_info
                        
                        pretty_path = zip_path + os.path.sep + name
                        
                    
                    paths_to_send_to_dialog.append( pretty_path )
                    
                
                with DialogPathsToTagsRegex( self, paths_to_send_to_dialog ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        delete_after_success = self._delete_after_success.GetValue()
                        
                        paths_to_tags = dlg.GetInfo()
                        
                        HC.pubsub.pub( 'new_hdd_import', paths_info, advanced_import_options = advanced_import_options, paths_to_tags = paths_to_tags, delete_after_success = delete_after_success )
                        
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
            
        
        def PopulateControls():
            
            default_actions = self._GetDefaultActions()
            
            self._favourites.Append( 'default', default_actions )
            
            favourites = HC.app.Read( 'favourite_custom_filter_actions' )
            
            if 'previous' in favourites: self._favourites.Append( 'previous', favourites[ 'previous' ] )
            else: self._favourites.Append( 'previous', default_actions )
            
            for ( name, actions ) in favourites.items():
                
                if name != 'previous': self._favourites.Append( name, actions )
                
            
            self._favourites.Select( 1 ) # previous
            
        
        def ArrangeControls():
            
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
        
        PopulateControls()
        
        ArrangeControls()
        
        wx.CallAfter( self.EventSelectFavourite, None )
        
        wx.CallAfter( self._ok.SetFocus )
        
    
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
        
        HC.app.Write( 'favourite_custom_filter_actions', favourites )
        
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
                
                while name in existing_names: name += HC.u( random.randint( 0, 9 ) )
                
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
            
            self._directory_picker = wx.DirPickerCtrl( self )
            self._directory_picker.Bind( wx.EVT_DIRPICKER_CHANGED, self.EventRecalcPaths )
            
            self._open_location = wx.Button( self, label = 'open this location' )
            self._open_location.Bind( wx.EVT_BUTTON, self.EventOpenLocation )
            
            self._zip_name = wx.TextCtrl( self )
            
            self._export_to_zip = wx.CheckBox( self, label = 'export to zip' )
            
            self._export_encrypted = wx.CheckBox( self, label = 'encrypt zip' )
            
            self._pattern = wx.TextCtrl( self )
            
            self._update = wx.Button( self, label = 'update' )
            self._update.Bind( wx.EVT_BUTTON, self.EventRecalcPaths )
            
            self._examples = wx.Button( self, label = 'pattern shortcuts' )
            self._examples.Bind( wx.EVT_BUTTON, self.EventPatternShortcuts )
            
            self._export = wx.Button( self, label = 'export' )
            self._export.Bind( wx.EVT_BUTTON, self.EventExport )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label='close' )
            
    
        def PopulateControls():
            
            for ( i, media ) in enumerate( flat_media ):
                
                mime = media.GetMime()
                
                pretty_tuple = ( HC.u( i + 1 ), HC.mime_string_lookup[ mime ], '' )
                data_tuple = ( ( i, media ), mime, '' )
                
                self._paths.Append( pretty_tuple, data_tuple )
                
            
            if self._options[ 'export_path' ] is not None: self._directory_picker.SetPath( HC.ConvertPortablePathToAbsPath( self._options[ 'export_path' ] ) )
            
            self._zip_name.SetValue( 'archive name.zip' )
            
            self._pattern.SetValue( '{hash}' )
            
        
        def ArrangeControls():
            
            top_hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            top_hbox.AddF( self._tags_box, FLAGS_EXPAND_PERPENDICULAR )
            top_hbox.AddF( self._paths, FLAGS_EXPAND_BOTH_WAYS )
            
            destination_hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            destination_hbox.AddF( self._directory_picker, FLAGS_EXPAND_BOTH_WAYS )
            destination_hbox.AddF( self._open_location, FLAGS_MIXED )
            
            zip_hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            zip_hbox.AddF( self._zip_name, FLAGS_EXPAND_BOTH_WAYS )
            zip_hbox.AddF( self._export_to_zip, FLAGS_MIXED )
            zip_hbox.AddF( self._export_encrypted, FLAGS_MIXED )
            
            pattern_hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            pattern_hbox.AddF( self._pattern, FLAGS_EXPAND_BOTH_WAYS )
            pattern_hbox.AddF( self._update, FLAGS_MIXED )
            pattern_hbox.AddF( self._examples, FLAGS_MIXED )
            pattern_hbox.AddF( self._export, FLAGS_MIXED )
            
            button_hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( top_hbox, FLAGS_EXPAND_SIZER_BOTH_WAYS )
            vbox.AddF( destination_hbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
            vbox.AddF( zip_hbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
            vbox.AddF( pattern_hbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
            vbox.AddF( self._cancel, FLAGS_LONE_BUTTON )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
        
        Dialog.__init__( self, parent, 'setup export' )
        
        self._page_key = os.urandom( 32 )
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
        wx.CallAfter( self.EventSelectPath, None )
        wx.CallAfter( self.EventRecalcPaths, None )
        
        self.Bind( wx.EVT_MENU, self.EventMenu )
        
        wx.CallAfter( self._export.SetFocus )
        
    
    def _GetPath( self, media, terms ):
        
        directory = self._directory_picker.GetPath()
        
        filename = ''
        
        for ( term_type, term ) in terms:
            
            tags_manager = media.GetTagsManager()
            
            if term_type == 'string': filename += term
            elif term_type == 'namespace':
                
                tags = tags_manager.GetNamespaceSlice( ( term, ) )
                
                filename += ', '.join( [ tag.split( ':' )[1] for tag in tags ] )
                
            elif term_type == 'predicate':
                
                if term in ( 'tags', 'nn tags' ):
                    
                    current = tags_manager.GetCurrent()
                    pending = tags_manager.GetPending()
                    
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
                
                if tags_manager.HasTag( term ): filename += term
                
            
        
        if self._export_to_zip.GetValue() == True: zip_path = self._zip_name.GetValue() + os.path.sep
        else: zip_path = ''
        
        mime = media.GetMime()
        
        ext = HC.mime_ext_lookup[ mime ]
        
        return directory + os.path.sep + zip_path + filename + ext
        
    
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
                
                while self._GetPath( media, terms + [ ( 'string', HC.u( i ) ) ] ) in all_paths: i += 1
                
                path = self._GetPath( media, terms + [ ( 'string', HC.u( i ) ) ] )
                
            
            all_paths.add( path )
            
            if path != old_path:
                
                mime = media.GetMime()
                
                self._paths.UpdateRow( index, ( HC.u( ordering_index + 1 ), HC.mime_string_lookup[ mime ], path ), ( ( ordering_index, media ), mime, path ) )
                
            
        
    
    def EventExport( self, event ):
        
        try: self._RecalcPaths()
        except Exception as e:
            
            wx.MessageBox( HC.u( e ) )
            
            return
            
        
        if self._export_to_zip.GetValue() == True:
            
            directory = self._directory_picker.GetPath()
            
            zip_path = directory + os.path.sep + self._zip_name.GetValue()
            
            with zipfile.ZipFile( zip_path, mode = 'w', compression = zipfile.ZIP_DEFLATED ) as z:
                
                for ( ( ordering_index, media ), mime, path ) in self._paths.GetClientData():
                    
                    try:
                        
                        hash = media.GetHash()
                        
                        file = HC.app.Read( 'file', hash )
                        
                        ( gumpf, filename ) = os.path.split( path )
                        
                        z.writestr( filename, file )
                        
                    except:
                        
                        wx.MessageBox( 'Encountered a problem while attempting to export file with index ' + HC.u( ordering_index + 1 ) + '.' + os.linesep + os.linesep + traceback.format_exc() )
                        
                        break
                        
                    
                
            
            if self._export_encrypted.GetValue() == True: HydrusEncryption.EncryptAESFile( zip_path, preface = 'hydrus encrypted zip' )
            
        else:
            
            for ( ( ordering_index, media ), mime, path ) in self._paths.GetClientData():
                
                try:
                    
                    hash = media.GetHash()
                    
                    file = HC.app.Read( 'file', hash )
                    
                    with HC.o( path, 'wb' ) as f: f.write( file )
                    
                except:
                    
                    wx.MessageBox( 'Encountered a problem while attempting to export file with index ' + HC.u( ordering_index + 1 ) + '.' + os.linesep + os.linesep + traceback.format_exc() )
                    
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
        except Exception as e: wx.MessageBox( HC.u( e ) )
        
    
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
            
    
        def PopulateControls():
            
            pass
            
        
        def ArrangeControls():
            
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
        
        PopulateControls()
        
        ArrangeControls()
        
        self.Bind( wx.EVT_CHAR_HOOK, self.EventCharHook )
        
        wx.CallAfter( self._yes.SetFocus )
        
    
    def EventCharHook( self, event ):
        
        if event.KeyCode == wx.WXK_ESCAPE: self.EndModal( wx.ID_NO )
        else: event.Skip()
        
    
    def EventNo( self, event ): self.EndModal( wx.ID_NO )
    
    def EventYes( self, event ): self.EndModal( wx.ID_YES )
    