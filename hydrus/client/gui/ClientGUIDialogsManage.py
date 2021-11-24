import itertools
import json
import os

from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core.networking import HydrusNATPunch

from hydrus.client import ClientApplicationCommand as CAC
from hydrus.client import ClientConstants as CC
from hydrus.client.gui import ClientGUIAsync
from hydrus.client.gui import ClientGUIDialogs
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIRatings
from hydrus.client.gui import ClientGUIShortcuts
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListConstants as CGLC
from hydrus.client.gui.lists import ClientGUIListCtrl
from hydrus.client.gui.widgets import ClientGUICommon
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
            
        
        self._copy_button = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().copy, self._Copy )
        self._copy_button.setToolTip( 'Copy ratings to the clipboard.' )
        
        self._paste_button = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().paste, self._Paste )
        self._paste_button.setToolTip( 'Paste ratings from the clipboard.' )
        
        self._apply = QW.QPushButton( 'apply', self )
        self._apply.clicked.connect( self.EventOK )
        self._apply.setObjectName( 'HydrusAccept' )
        
        self._cancel = QW.QPushButton( 'cancel', self )
        self._cancel.clicked.connect( self.reject )
        self._cancel.setObjectName( 'HydrusCancel' )
        
        #
        
        vbox = QP.VBoxLayout()
        
        for panel in self._panels:
            
            QP.AddToLayout( vbox, panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        buttonbox = QP.HBoxLayout()
        
        QP.AddToLayout( buttonbox, self._copy_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( buttonbox, self._paste_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        QP.AddToLayout( vbox, buttonbox, CC.FLAGS_ON_RIGHT )
        
        buttonbox = QP.HBoxLayout()
        
        QP.AddToLayout( buttonbox, self._apply, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( buttonbox, self._cancel, CC.FLAGS_CENTER_PERPENDICULAR )
        
        QP.AddToLayout( vbox, buttonbox, CC.FLAGS_ON_RIGHT )
        
        self.setLayout( vbox )
        
        size_hint = self.sizeHint()
        
        QP.SetInitialSize( self, size_hint )
        
        #
        
        self._my_shortcut_handler = ClientGUIShortcuts.ShortcutsHandler( self, [ 'global', 'media' ] )
        
    
    def _Copy( self ):
        
        rating_clipboard_pairs = []
        
        for panel in self._panels:
            
            rating_clipboard_pairs.extend( panel.GetRatingClipboardPairs() )
            
        
        text = json.dumps( [ ( service_key.hex(), rating ) for ( service_key, rating ) in rating_clipboard_pairs ] )
        
        HG.client_controller.pub( 'clipboard', 'text', text )
        
    
    def _Paste( self ):
        
        try:
            
            raw_text = HG.client_controller.GetClipboardText()
            
        except HydrusExceptions.DataMissing as e:
            
            QW.QMessageBox.critical( self, 'Error', str(e) )
            
            return
            
        
        try:
            
            rating_clipboard_pairs_encoded = json.loads( raw_text )
            
            rating_clipboard_pairs = [ ( bytes.fromhex( service_key_encoded ), rating ) for ( service_key_encoded, rating ) in rating_clipboard_pairs_encoded ]
            
        except:
            
            QW.QMessageBox.critical( self, 'Error', 'Did not understand what was in the clipboard!' )
            
            return
            
        
        for panel in self._panels:
            
            panel.SetRatingClipboardPairs( rating_clipboard_pairs )
            
        
    
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
        
        if command.IsSimpleCommand():
            
            action = command.GetSimpleAction()
            
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
            
        
        def GetRatingClipboardPairs( self ):
            
            rating_clipboard_pairs = []
            
            for ( service_key, control ) in self._service_keys_to_controls.items():
                
                rating_state = control.GetRatingState()
                
                if rating_state == ClientRatings.LIKE:
                    
                    rating = 1
                    
                elif rating_state == ClientRatings.DISLIKE:
                    
                    rating = 0
                    
                elif rating_state == ClientRatings.NULL:
                    
                    rating = None
                    
                else:
                    
                    continue
                    
                
                rating_clipboard_pairs.append( ( service_key, rating ) )
                
            
            return rating_clipboard_pairs
            
        
        def SetRatingClipboardPairs( self, rating_clipboard_pairs ):
            
            for ( service_key, rating ) in rating_clipboard_pairs:
                
                if rating == 1:
                    
                    rating_state = ClientRatings.LIKE
                    
                elif rating == 0:
                    
                    rating_state = ClientRatings.DISLIKE
                    
                elif rating is None:
                    
                    rating_state = ClientRatings.NULL
                    
                else:
                    
                    continue
                    
                
                if service_key in self._service_keys_to_controls:
                    
                    control = self._service_keys_to_controls[ service_key ]
                    
                    control.SetRatingState( rating_state )
                    
                
            
        
    
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
            
        
        def GetRatingClipboardPairs( self ):
            
            rating_clipboard_pairs = []
            
            for ( service_key, control ) in self._service_keys_to_controls.items():
                
                rating_state = control.GetRatingState()
                
                if rating_state == ClientRatings.NULL:
                    
                    rating = None
                    
                elif rating_state == ClientRatings.SET:
                    
                    rating = control.GetRating()
                    
                else:
                    
                    continue
                    
                
                rating_clipboard_pairs.append( ( service_key, rating ) )
                
            
            return rating_clipboard_pairs
            
        
        def SetRatingClipboardPairs( self, rating_clipboard_pairs ):
            
            for ( service_key, rating ) in rating_clipboard_pairs:
                
                if service_key in self._service_keys_to_controls:
                    
                    control = self._service_keys_to_controls[ service_key ]
                    
                    if rating is None:
                        
                        control.SetRatingState( ClientRatings.NULL )
                        
                    elif isinstance( rating, ( int, float ) ) and 0 <= rating <= 1:
                        
                        control.SetRating( rating )
                        
                    
                
            
        
    
class DialogManageUPnP( ClientGUIDialogs.Dialog ):
    
    def __init__( self, parent ):
        
        title = 'manage local upnp'
        
        ClientGUIDialogs.Dialog.__init__( self, parent, title )
        
        self._status_st = ClientGUICommon.BetterStaticText( self )
        
        self._mappings_listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        self._mappings_list = ClientGUIListCtrl.BetterListCtrl( self._mappings_listctrl_panel, CGLC.COLUMN_LIST_MANAGE_UPNP_MAPPINGS.ID, 12, self._ConvertDataToListCtrlTuples, delete_key_callback = self._Remove, activation_callback = self._Edit )
        
        self._mappings_listctrl_panel.SetListCtrl( self._mappings_list )
        
        self._mappings_listctrl_panel.AddButton( 'add custom mapping', self._Add )
        self._mappings_listctrl_panel.AddButton( 'edit mapping', self._Edit, enabled_only_on_single_selection = True )
        self._mappings_listctrl_panel.AddButton( 'remove mapping', self._Remove, enabled_only_on_selection = True )
        
        self._ok = QW.QPushButton( 'ok', self )
        self._ok.clicked.connect( self.EventOK )
        self._ok.setObjectName( 'HydrusAccept' )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._status_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._mappings_listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, self._ok, CC.FLAGS_ON_RIGHT )
        
        self.setLayout( vbox )
        
        size_hint = self.sizeHint()
        
        size_hint.setWidth( max( size_hint.width(), 760 ) )
        
        QP.SetInitialSize( self, size_hint )
        
        #
        
        self._mappings_lookup = set()
        
        self._mappings_list.Sort()
        
        self._external_ip = None
        
        self._started_external_ip_fetch = False
        
        self._RefreshMappings()
        
    
    def _Add( self ):
        
        external_port = HC.DEFAULT_SERVICE_PORT
        protocol = 'TCP'
        internal_port = HC.DEFAULT_SERVICE_PORT
        description = 'hydrus service'
        duration = 0
        
        with ClientGUIDialogs.DialogInputUPnPMapping( self, external_port, protocol, internal_port, description, duration ) as dlg:
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                ( external_port, protocol, internal_port, description, duration ) = dlg.GetInfo()
                
                remove_existing = False
                
                if self._MappingExists( external_port, protocol ):
                    
                    remove_existing = True
                    
                    text = '{}:({}) is already mapped! Ok to overwrite whatever it currently is?'
                    
                    result = ClientGUIDialogsQuick.GetYesNo( self, text, yes_label = 'do it', no_label = 'forget it' )
                    
                    if result != QW.QDialog.Accepted:
                        
                        return
                        
                    
                
                def work_callable():
                    
                    if remove_existing:
                        
                        HydrusNATPunch.RemoveUPnPMapping( external_port, protocol )
                        
                    
                    internal_client = HydrusNATPunch.GetLocalIP()
                    
                    HydrusNATPunch.AddUPnPMapping( internal_client, internal_port, external_port, protocol, description, duration = duration )
                    
                    return True
                    
                
                def publish_callable( result ):
                    
                    self._mappings_listctrl_panel.setEnabled( True )
                    
                    self._RefreshMappings()
                    
                
                self._mappings_listctrl_panel.setEnabled( False )
                
                async_job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
                
                async_job.start()
                
            
        
    
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
        
        selected_mappings = self._mappings_list.GetData( only_selected = True )
        
        if len( selected_mappings ) > 0:
            
            selected_mapping = selected_mappings[0]
            
            ( description, internal_ip, internal_port, old_external_port, old_protocol, duration ) = selected_mapping
            
            with ClientGUIDialogs.DialogInputUPnPMapping( self, old_external_port, old_protocol, internal_port, description, duration ) as dlg:
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    ( external_port, protocol, internal_port, description, duration ) = dlg.GetInfo()
                    
                    remove_old = self._MappingExists( old_external_port, old_protocol )
                    remove_existing = ( old_external_port != external_port or old_protocol != protocol ) and self._MappingExists( external_port, protocol )
                    
                    def work_callable():
                        
                        if remove_old:
                            
                            HydrusNATPunch.RemoveUPnPMapping( old_external_port, old_protocol )
                            
                        
                        if remove_existing:
                            
                            HydrusNATPunch.RemoveUPnPMapping( external_port, protocol )
                            
                        
                        internal_client = HydrusNATPunch.GetLocalIP()
                        
                        HydrusNATPunch.AddUPnPMapping( internal_client, internal_port, external_port, protocol, description, duration = duration )
                        
                        return True
                        
                    
                    def publish_callable( result ):
                        
                        self._mappings_listctrl_panel.setEnabled( True )
                        
                        self._RefreshMappings()
                        
                    
                    self._mappings_listctrl_panel.setEnabled( False )
                    
                    async_job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
                    
                    async_job.start()
                    
                
            
        
    
    def _MappingExists( self, external_port, protocol ):
        
        return ( external_port, protocol ) in self._mappings_lookup
        
    
    def _RefreshExternalIP( self ):
        
        def work_callable():
            
            try:
                
                external_ip = HydrusNATPunch.GetExternalIP()
                
                external_ip_text = 'External IP: {}'.format( external_ip )
                
            except Exception as e:
                
                external_ip_text = 'Error finding external IP: ' + str( e )
                
            
            return external_ip_text
            
        
        def publish_callable( external_ip_text ):
            
            self._external_ip = external_ip_text
            
            self._status_st.setText( self._external_ip )
            
        
        self._status_st.setText( 'Loading external IP\u2026' )
        
        async_job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
        
        async_job.start()
        
    
    def _RefreshMappings( self ):
        
        def work_callable():
            
            try:
                
                mappings = HydrusNATPunch.GetUPnPMappings()
                
            except Exception as e:
                
                HydrusData.ShowException( e )
                
                return e
                
            
            return mappings
            
        
        def publish_callable( result ):
            
            if isinstance( result, Exception ):
                
                e = result
                
                QP.CallAfter( QW.QMessageBox.critical, self, 'Error', 'Could not load mappings:'+os.linesep*2+str(e) )
                
                self._status_st.setText( str( e ) )
                
                return
                
            
            self._mappings_listctrl_panel.setEnabled( True )
            
            mappings = result
            
            self._mappings_lookup = { ( external_port, protocol ) for ( description, internal_ip, internal_port, external_port, protocol, duration ) in mappings }
            
            self._mappings_list.SetData( mappings )
            
            self._status_st.clear()
            
            if self._external_ip is not None:
                
                self._status_st.setText( self._external_ip )
                
            elif not self._started_external_ip_fetch:
                
                self._started_external_ip_fetch = True
                
                self._RefreshExternalIP()
                
            
        
        self._status_st.setText( 'Refreshing mappings--please wait\u2026' )
        
        self._mappings_list.SetData( [] )
        
        self._mappings_listctrl_panel.setEnabled( False )
        
        async_job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
        
        async_job.start()
        
    
    def _Remove( self ):
        
        text = 'Remove these port mappings?'
        text += os.linesep * 2
        text += 'If a mapping does not disappear after a remove, it may be hard-added in the router\'s settings interface. In this case, you will have to go there to fix it.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, text, yes_label = 'do it', no_label = 'forget it' )
        
        if result != QW.QDialog.Accepted:
            
            return
            
        
        selected_mappings = self._mappings_list.GetData( only_selected = True )
        
        def work_callable():
            
            for selected_mapping in selected_mappings:
                
                ( description, internal_ip, internal_port, external_port, protocol, duration ) = selected_mapping
                
                HydrusNATPunch.RemoveUPnPMapping( external_port, protocol )
                
            
            return True
            
        
        def publish_callable( result ):
            
            self._mappings_listctrl_panel.setEnabled( True )
            
            self._RefreshMappings()
            
        
        self._mappings_listctrl_panel.setEnabled( False )
        
        async_job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
        
        async_job.start()
        
    
    def EventOK( self ):
        
        self.done( QW.QDialog.Accepted )
        
    
