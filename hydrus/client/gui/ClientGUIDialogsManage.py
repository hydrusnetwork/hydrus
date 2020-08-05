import itertools
import os
import traceback

from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusNATPunch

from hydrus.client import ClientApplicationCommand as CAC
from hydrus.client import ClientConstants as CC
from hydrus.client.gui import ClientGUICommon
from hydrus.client.gui import ClientGUIDialogs
from hydrus.client.gui import ClientGUIRatings
from hydrus.client.gui import ClientGUIShortcuts
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListConstants as CGLC
from hydrus.client.gui.lists import ClientGUIListCtrl
from hydrus.client.metadata import ClientRatings

# Option Enums

class DialogManageRatings( ClientGUIDialogs.Dialog ):
    
    def __init__( self, parent, media ):
        
        self._hashes = set()
        
        for m in media:
            
            self._hashes.update( m.GetHashes() )
            
        
        ClientGUIDialogs.Dialog.__init__( self, parent, 'manage ratings for ' + HydrusData.ToHumanInt( len( self._hashes ) ) + ' files', position = 'topleft' )
        
        #
        
        like_services = HG.client_controller.services_manager.GetServices( ( HC.LOCAL_RATING_LIKE, ) )
        numerical_services = HG.client_controller.services_manager.GetServices( ( HC.LOCAL_RATING_NUMERICAL, ) )
        
        self._panels = []
        
        if len( like_services ) > 0:
            
            self._panels.append( self._LikePanel( self, like_services, media ) )
            
        
        if len( numerical_services ) > 0:
            
            self._panels.append( self._NumericalPanel( self, numerical_services, media ) )
            
        
        self._apply = QW.QPushButton( 'apply', self )
        self._apply.clicked.connect( self.EventOK )
        self._apply.setObjectName( 'HydrusAccept' )
        
        self._cancel = QW.QPushButton( 'cancel', self )
        self._cancel.clicked.connect( self.reject )
        self._cancel.setObjectName( 'HydrusCancel' )
        
        #
        
        buttonbox = QP.HBoxLayout()
        
        QP.AddToLayout( buttonbox, self._apply, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( buttonbox, self._cancel, CC.FLAGS_CENTER_PERPENDICULAR )
        
        vbox = QP.VBoxLayout()
        
        for panel in self._panels:
            
            QP.AddToLayout( vbox, panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        QP.AddToLayout( vbox, buttonbox, CC.FLAGS_ON_RIGHT )
        
        self.setLayout( vbox )
        
        size_hint = self.sizeHint()
        
        QP.SetInitialSize( self, size_hint )
        
        #
        
        self._my_shortcut_handler = ClientGUIShortcuts.ShortcutsHandler( self, [ 'global', 'media' ] )
        
    
    def EventOK( self ):
        
        try:
            
            service_keys_to_content_updates = {}
            
            for panel in self._panels:
                
                sub_service_keys_to_content_updates = panel.GetContentUpdates()
                
                service_keys_to_content_updates.update( sub_service_keys_to_content_updates )
                
            
            if len( service_keys_to_content_updates ) > 0:
                
                HG.client_controller.Write( 'content_updates', service_keys_to_content_updates )
                
            
        finally:
            
            self.done( QW.QDialog.Accepted )
            
        
    
    def ProcessApplicationCommand( self, command: CAC.ApplicationCommand ):
        
        command_processed = True
        
        data = command.GetData()
        
        if command.IsSimpleCommand():
            
            action = data
            
            if action == CAC.SIMPLE_MANAGE_FILE_RATINGS:
                
                self.EventOK()
                
            else:
                
                command_processed = False
                
            
        else:
            
            command_processed = False
            
        
        return command_processed
        
    
    class _LikePanel( QW.QWidget ):
        
        def __init__( self, parent, services, media ):
            
            QW.QWidget.__init__( self, parent )
            
            self._services = services
            
            self._media = media
            
            self._service_keys_to_controls = {}
            self._service_keys_to_original_ratings_states = {}
            
            rows = []
            
            for service in self._services:
                
                name = service.GetName()
                
                service_key = service.GetServiceKey()
                
                rating_state = ClientRatings.GetLikeStateFromMedia( self._media, service_key )
                
                control = ClientGUIRatings.RatingLikeDialog( self, service_key )
                
                control.SetRatingState( rating_state )
                
                self._service_keys_to_controls[ service_key ] = control
                self._service_keys_to_original_ratings_states[ service_key ] = rating_state
                
                rows.append( ( name + ': ', control ) )
                
            
            gridbox = ClientGUICommon.WrapInGrid( self, rows, expand_text = True )
            
            self.setLayout( gridbox )
            
        
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
            
        
    
    class _NumericalPanel( QW.QWidget ):
        
        def __init__( self, parent, services, media ):
            
            QW.QWidget.__init__( self, parent )
            
            self._services = services
            
            self._media = media
            
            self._service_keys_to_controls = {}
            self._service_keys_to_original_ratings_states = {}
            
            rows = []
            
            for service in self._services:
                
                name = service.GetName()
                
                service_key = service.GetServiceKey()
                
                ( rating_state, rating ) = ClientRatings.GetNumericalStateFromMedia( self._media, service_key )
                
                control = ClientGUIRatings.RatingNumericalDialog( self, service_key )
                
                if rating_state != ClientRatings.SET:
                    
                    control.SetRatingState( rating_state )
                    
                else:
                    
                    control.SetRating( rating )
                    
                
                self._service_keys_to_controls[ service_key ] = control
                self._service_keys_to_original_ratings_states[ service_key ] = ( rating_state, rating )
                
                rows.append( ( name + ': ', control ) )
                
            
            gridbox = ClientGUICommon.WrapInGrid( self, rows, expand_text = True )
            
            self.setLayout( gridbox )
            
        
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
        
        self._mappings_list_ctrl = ClientGUIListCtrl.BetterListCtrl( listctrl_panel, CGLC.COLUMN_LIST_MANAGE_UPNP_MAPPINGS.ID, 12, self._ConvertDataToListCtrlTuples, delete_key_callback = self._Remove, activation_callback = self._Edit )
        
        listctrl_panel.SetListCtrl( self._mappings_list_ctrl )
        
        listctrl_panel.AddButton( 'add custom mapping', self._Add )
        listctrl_panel.AddButton( 'edit mapping', self._Edit, enabled_only_on_selection = True )
        listctrl_panel.AddButton( 'remove mapping', self._Remove, enabled_only_on_selection = True )
        
        self._ok = QW.QPushButton( 'ok', self )
        self._ok.clicked.connect( self.EventOK )
        self._ok.setObjectName( 'HydrusAccept' )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._status_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, self._ok, CC.FLAGS_ON_RIGHT )
        
        self.setLayout( vbox )
        
        size_hint = self.sizeHint()
        
        size_hint.setWidth( max( size_hint.width(), 760 ) )
        
        QP.SetInitialSize( self, size_hint )
        
        #
        
        self._mappings = []
        
        self._mappings_list_ctrl.Sort()
        
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
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                ( external_port, protocol, internal_port, description, duration ) = dlg.GetInfo()
                
                for ( existing_description, existing_internal_ip, existing_internal_port, existing_external_port, existing_protocol, existing_lease ) in self._mappings:
                    
                    if external_port == existing_external_port and protocol == existing_protocol:
                        
                        QW.QMessageBox.critical( self, 'Error', 'That external port already exists!' )
                        
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
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
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
        
        def qt_code( external_ip_text ):
            
            if not self or not QP.isValid( self ):
                
                return
                
            
            self._status_st.setText( external_ip_text )
            
        
        def THREADdo_it():
            
            try:
                
                external_ip = HydrusNATPunch.GetExternalIP()
                
                external_ip_text = 'External IP: {}'.format( external_ip )
                
            except Exception as e:
                
                external_ip_text = 'Error finding external IP: ' + str( e )
                
            
            QP.CallAfter( qt_code, external_ip_text )
            
        
        self._status_st.setText( 'Loading external IP\u2026' )
        
        HG.client_controller.CallToThread( THREADdo_it )
        
    
    def _RefreshMappings( self ):
        
        def qt_code( mappings ):
            
            if not self or not QP.isValid( self ):
                
                return
                
            
            self._mappings = mappings
            
            self._mappings_list_ctrl.SetData( self._mappings )
            
            self._status_st.setText( '' )
            
            if not self._started_external_ip_fetch:
                
                self._started_external_ip_fetch = True
                
                self._RefreshExternalIP()
                
            
        
        def THREADdo_it():
            
            try:
                
                mappings = HydrusNATPunch.GetUPnPMappings()
                
            except Exception as e:
                
                HydrusData.ShowException( e )
                
                QP.CallAfter( QW.QMessageBox.critical, self, 'Error', 'Could not load mappings:'+os.linesep*2+str(e) )
                
                return
                
            
            QP.CallAfter( qt_code, mappings )
            
        
        self._status_st.setText( 'Refreshing mappings--please wait\u2026' )
        
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
            
        
    
    def EventOK( self ):
        
        self.done( QW.QDialog.Accepted )
        
    
