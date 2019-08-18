from . import ClientCaches
from . import ClientConstants as CC
from . import ClientData
from . import ClientDefaults
from . import ClientDownloading
from . import ClientDragDrop
from . import ClientExporting
from . import ClientFiles
from . import ClientGUIACDropdown
from . import ClientGUICommon
from . import ClientGUIListBoxes
from . import ClientGUIListCtrl
from . import ClientGUIDialogs
from . import ClientGUIImport
from . import ClientGUIOptionsPanels
from . import ClientGUIPredicates
from . import ClientGUIScrolledPanels
from . import ClientGUIScrolledPanelsEdit
from . import ClientGUIShortcuts
from . import ClientGUIFileSeedCache
from . import ClientGUITime
from . import ClientGUITopLevelWindows
from . import ClientImporting
from . import ClientImportLocal
from . import ClientImportOptions
from . import ClientMedia
from . import ClientRatings
from . import ClientSearch
from . import ClientServices
from . import ClientThreading
import collections
from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusExceptions
from . import HydrusGlobals as HG
from . import HydrusNATPunch
from . import HydrusNetwork
from . import HydrusPaths
from . import HydrusSerialisable
from . import HydrusTagArchive
from . import HydrusTags
from . import HydrusText
import itertools
import os
import random
import re
import string
import time
import traceback
import wx
import yaml

# Option Enums

ID_NULL = wx.NewId()

ID_TIMER_UPDATE = wx.NewId()

class DialogManageRatings( ClientGUIDialogs.Dialog ):
    
    def __init__( self, parent, media ):
        
        self._hashes = set()
        
        for m in media: self._hashes.update( m.GetHashes() )
        
        ( remember, position ) = HC.options[ 'rating_dialog_position' ]
        
        if remember and position is not None:
            
            my_position = 'custom'
            
            wx.CallAfter( self.SetPosition, position )
            
        else:
            
            my_position = 'topleft'
            
        
        ClientGUIDialogs.Dialog.__init__( self, parent, 'manage ratings for ' + HydrusData.ToHumanInt( len( self._hashes ) ) + ' files', position = my_position )
        
        #
        
        like_services = HG.client_controller.services_manager.GetServices( ( HC.LOCAL_RATING_LIKE, ), randomised = False )
        numerical_services = HG.client_controller.services_manager.GetServices( ( HC.LOCAL_RATING_NUMERICAL, ), randomised = False )
        
        self._panels = []
        
        if len( like_services ) > 0:
            
            self._panels.append( self._LikePanel( self, like_services, media ) )
            
        
        if len( numerical_services ) > 0:
            
            self._panels.append( self._NumericalPanel( self, numerical_services, media ) )
            
        
        self._apply = wx.Button( self, id = wx.ID_OK, label = 'apply' )
        self._apply.Bind( wx.EVT_BUTTON, self.EventOK )
        self._apply.SetForegroundColour( ( 0, 128, 0 ) )
        
        self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'cancel' )
        self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
        
        #
        
        buttonbox = wx.BoxSizer( wx.HORIZONTAL )
        
        buttonbox.Add( self._apply, CC.FLAGS_VCENTER )
        buttonbox.Add( self._cancel, CC.FLAGS_VCENTER )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        for panel in self._panels:
            
            vbox.Add( panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        vbox.Add( buttonbox, CC.FLAGS_BUTTON_SIZER )
        
        self.SetSizer( vbox )
        
        ( x, y ) = self.GetEffectiveMinSize()
        
        self.SetInitialSize( ( x, y ) )
        
        #
        
        self._my_shortcut_handler = ClientGUIShortcuts.ShortcutsHandler( self, [ 'media' ] )
        
    
    def EventOK( self, event ):
        
        try:
            
            service_keys_to_content_updates = {}
            
            for panel in self._panels:
                
                sub_service_keys_to_content_updates = panel.GetContentUpdates()
                
                service_keys_to_content_updates.update( sub_service_keys_to_content_updates )
                
            
            if len( service_keys_to_content_updates ) > 0:
                
                HG.client_controller.Write( 'content_updates', service_keys_to_content_updates )
                
            
            ( remember, position ) = HC.options[ 'rating_dialog_position' ]
            
            current_position = self.GetPosition()
            
            if remember and position != current_position:
                
                HC.options[ 'rating_dialog_position' ] = ( remember, current_position )
                
                HG.client_controller.Write( 'save_options', HC.options )
                
            
        finally:
            
            self.EndModal( wx.ID_OK )
            
        
    
    def ProcessApplicationCommand( self, command ):
        
        command_processed = True
        
        command_type = command.GetCommandType()
        data = command.GetData()
        
        if command_type == CC.APPLICATION_COMMAND_TYPE_SIMPLE:
            
            action = data
            
            if action == 'manage_file_ratings':
                
                self.EventOK( None )
                
            else:
                
                command_processed = False
                
            
        else:
            
            command_processed = False
            
        
        return command_processed
        
    
    class _LikePanel( wx.Panel ):
        
        def __init__( self, parent, services, media ):
            
            wx.Panel.__init__( self, parent )
            
            self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
            
            self._services = services
            
            self._media = media
            
            self._service_keys_to_controls = {}
            self._service_keys_to_original_ratings_states = {}
            
            rows = []
            
            for service in self._services:
                
                name = service.GetName()
                
                service_key = service.GetServiceKey()
                
                rating_state = ClientRatings.GetLikeStateFromMedia( self._media, service_key )
                
                control = ClientGUICommon.RatingLikeDialog( self, service_key )
                
                control.SetRatingState( rating_state )
                
                self._service_keys_to_controls[ service_key ] = control
                self._service_keys_to_original_ratings_states[ service_key ] = rating_state
                
                rows.append( ( name + ': ', control ) )
                
            
            gridbox = ClientGUICommon.WrapInGrid( self, rows, expand_text = True )
            
            self.SetSizer( gridbox )
            
        
        def GetContentUpdates( self ):
            
            service_keys_to_content_updates = {}
            
            hashes = { hash for hash in itertools.chain.from_iterable( ( media.GetHashes() for media in self._media ) ) }
            
            for ( service_key, control ) in list(self._service_keys_to_controls.items()):
                
                original_rating_state = self._service_keys_to_original_ratings_states[ service_key ]
                
                rating_state = control.GetRatingState()
                
                if rating_state != original_rating_state:
                    
                    if rating_state == ClientRatings.LIKE: rating = 1
                    elif rating_state == ClientRatings.DISLIKE: rating = 0
                    else: rating = None
                    
                    content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( rating, hashes ) )
                    
                    service_keys_to_content_updates[ service_key ] = ( content_update, )
                    
                
            
            return service_keys_to_content_updates
            
        
    
    class _NumericalPanel( wx.Panel ):
        
        def __init__( self, parent, services, media ):
            
            wx.Panel.__init__( self, parent )
            
            self._services = services
            
            self._media = media
            
            self._service_keys_to_controls = {}
            self._service_keys_to_original_ratings_states = {}
            
            rows = []
            
            for service in self._services:
                
                name = service.GetName()
                
                service_key = service.GetServiceKey()
                
                ( rating_state, rating ) = ClientRatings.GetNumericalStateFromMedia( self._media, service_key )
                
                control = ClientGUICommon.RatingNumericalDialog( self, service_key )
                
                if rating_state != ClientRatings.SET:
                    
                    control.SetRatingState( rating_state )
                    
                else:
                    
                    control.SetRating( rating )
                    
                
                self._service_keys_to_controls[ service_key ] = control
                self._service_keys_to_original_ratings_states[ service_key ] = ( rating_state, rating )
                
                rows.append( ( name + ': ', control ) )
                
            
            gridbox = ClientGUICommon.WrapInGrid( self, rows, expand_text = True )
            
            self.SetSizer( gridbox )
            
        
        def GetContentUpdates( self ):
            
            service_keys_to_content_updates = {}
            
            hashes = { hash for hash in itertools.chain.from_iterable( ( media.GetHashes() for media in self._media ) ) }
            
            for ( service_key, control ) in list(self._service_keys_to_controls.items()):
                
                ( original_rating_state, original_rating ) = self._service_keys_to_original_ratings_states[ service_key ]
                
                rating_state = control.GetRatingState()
                
                if rating_state == ClientRatings.NULL:
                    
                    rating = None
                    
                else:
                    
                    rating = control.GetRating()
                    
                
                if rating != original_rating:
                    
                    content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( rating, hashes ) )
                    
                    service_keys_to_content_updates[ service_key ] = ( content_update, )
                    
                
            
            return service_keys_to_content_updates
            
        
    
class DialogManageUPnP( ClientGUIDialogs.Dialog ):
    
    def __init__( self, parent ):
        
        title = 'manage local upnp'
        
        ClientGUIDialogs.Dialog.__init__( self, parent, title )
        
        self._status_st = ClientGUICommon.BetterStaticText( self )
        
        listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        columns = [ ( 'description', -1 ), ( 'internal ip', 17 ), ( 'internal port', 7 ), ( 'external port', 7 ), ( 'prototcol', 5 ), ( 'lease', 12 ) ]
        
        self._mappings_list_ctrl = ClientGUIListCtrl.BetterListCtrl( listctrl_panel, 'manage_upnp_mappings', 12, 36, columns, self._ConvertDataToListCtrlTuples, delete_key_callback = self._Remove, activation_callback = self._Edit )
        
        listctrl_panel.SetListCtrl( self._mappings_list_ctrl )
        
        listctrl_panel.AddButton( 'add custom mapping', self._Add )
        listctrl_panel.AddButton( 'edit mapping', self._Edit, enabled_only_on_selection = True )
        listctrl_panel.AddButton( 'remove mapping', self._Remove, enabled_only_on_selection = True )
        
        self._ok = wx.Button( self, id = wx.ID_OK, label = 'ok' )
        self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
        self._ok.SetForegroundColour( ( 0, 128, 0 ) )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( self._status_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.Add( self._ok, CC.FLAGS_LONE_BUTTON )
        
        self.SetSizer( vbox )
        
        ( x, y ) = self.GetEffectiveMinSize()
        
        x = max( x, 760 )
        
        self.SetInitialSize( ( x, y ) )
        
        #
        
        self._mappings = []
        
        self._mappings_list_ctrl.Sort( 0 )
        
        self._started_external_ip_fetch = False
        
        self._RefreshMappings()
        
    
    def _Add( self ):
        
        do_refresh = False
        
        external_port = HC.DEFAULT_SERVICE_PORT
        protocol = 'TCP'
        internal_port = HC.DEFAULT_SERVICE_PORT
        description = 'hydrus service'
        duration = 0
        
        with ClientGUIDialogs.DialogInputUPnPMapping( self, external_port, protocol, internal_port, description, duration ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                ( external_port, protocol, internal_port, description, duration ) = dlg.GetInfo()
                
                for ( existing_description, existing_internal_ip, existing_internal_port, existing_external_port, existing_protocol, existing_lease ) in self._mappings:
                    
                    if external_port == existing_external_port and protocol == existing_protocol:
                        
                        wx.MessageBox( 'That external port already exists!' )
                        
                        return
                        
                    
                
                internal_client = HydrusNATPunch.GetLocalIP()
                
                HydrusNATPunch.AddUPnPMapping( internal_client, internal_port, external_port, protocol, description, duration = duration )
                
                do_refresh = True
                
            
        
        if do_refresh:
            
            self._RefreshMappings()
            
        
    
    def _ConvertDataToListCtrlTuples( self, mapping ):
        
        ( description, internal_ip, internal_port, external_port, protocol, duration ) = mapping
        
        if duration == 0:
            
            pretty_duration = 'indefinite'
            
        else:
            
            pretty_duration = HydrusData.TimeDeltaToPrettyTimeDelta( duration )
            
        
        display_tuple = ( description, internal_ip, str( internal_port ), str( external_port ), protocol, pretty_duration )
        sort_tuple = mapping
        
        return ( display_tuple, sort_tuple )
        
    
    def _Edit( self ):
        
        do_refresh = False
        
        selected_mappings = self._mappings_list_ctrl.GetData( only_selected = True )
        
        for selected_mapping in selected_mappings:
            
            ( description, internal_ip, internal_port, external_port, protocol, duration ) = selected_mapping
            
            with ClientGUIDialogs.DialogInputUPnPMapping( self, external_port, protocol, internal_port, description, duration ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    ( external_port, protocol, internal_port, description, duration ) = dlg.GetInfo()
                    
                    HydrusNATPunch.RemoveUPnPMapping( external_port, protocol )
                    
                    internal_client = HydrusNATPunch.GetLocalIP()
                    
                    HydrusNATPunch.AddUPnPMapping( internal_client, internal_port, external_port, protocol, description, duration = duration )
                    
                    do_refresh = True
                    
                else:
                    
                    break
                    
                
            
        
        if do_refresh:
            
            self._RefreshMappings()
            
        
    
    def _RefreshExternalIP( self ):
        
        def wx_code( external_ip_text ):
            
            if not self:
                
                return
                
            
            self._status_st.SetLabelText( external_ip_text )
            
        
        def THREADdo_it():
            
            try:
                
                external_ip = HydrusNATPunch.GetExternalIP()
                
                external_ip_text = 'External IP: {}'.format( external_ip )
                
            except Exception as e:
                
                external_ip_text = 'Error finding external IP: ' + str( e )
                
                return
                
            
            wx.CallAfter( wx_code, external_ip_text )
            
        
        self._status_st.SetLabelText( 'Loading external IP\u2026' )
        
        HG.client_controller.CallToThread( THREADdo_it )
        
    
    def _RefreshMappings( self ):
        
        def wx_code( mappings ):
            
            if not self:
                
                return
                
            
            self._mappings = mappings
            
            self._mappings_list_ctrl.SetData( self._mappings )
            
            self._status_st.SetLabelText( '' )
            
            if not self._started_external_ip_fetch:
                
                self._started_external_ip_fetch = True
                
                self._RefreshExternalIP()
                
            
        
        def THREADdo_it():
            
            try:
                
                mappings = HydrusNATPunch.GetUPnPMappings()
                
            except Exception as e:
                
                HydrusData.ShowException( e )
                
                wx.CallAfter( wx.MessageBox, 'Could not load mappings:' + os.linesep * 2 + str( e ) )
                
                return
                
            
            wx.CallAfter( wx_code, mappings )
            
        
        self._status_st.SetLabelText( 'Refreshing mappings--please wait\u2026' )
        
        self._mappings_list_ctrl.SetData( [] )
        
        HG.client_controller.CallToThread( THREADdo_it )
        
    
    def _Remove( self ):
        
        do_refresh = False
        
        selected_mappings = self._mappings_list_ctrl.GetData( only_selected = True )
        
        for selected_mapping in selected_mappings:
            
            ( description, internal_ip, internal_port, external_port, protocol, duration ) = selected_mapping
            
            HydrusNATPunch.RemoveUPnPMapping( external_port, protocol )
            
            do_refresh = True
            
        
        if do_refresh:
            
            self._RefreshMappings()
            
        
    
    def EventOK( self, event ):
        
        self.EndModal( wx.ID_OK )
        
    
