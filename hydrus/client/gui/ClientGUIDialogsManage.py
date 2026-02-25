import itertools
import json

from qtpy import QtWidgets as QW
from qtpy import QtCore as QC

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusNumbers

from hydrus.client import ClientApplicationCommand as CAC
from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUIDialogs
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIRatings
from hydrus.client.gui import ClientGUIShortcuts
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.metadata import ClientContentUpdates
from hydrus.client.metadata import ClientRatings

class DialogManageRatings( CAC.ApplicationCommandProcessorMixin, ClientGUIDialogs.Dialog ):
    
    def __init__( self, parent, media ):
        
        self._hashes = set()
        
        for m in media:
            
            self._hashes.update( m.GetHashes() )
            
        
        super().__init__( parent, 'manage ratings for ' + HydrusNumbers.ToHumanInt( len( self._hashes ) ) + ' files', position = 'topleft' )
        
        #
        
        like_services = CG.client_controller.services_manager.GetServices( ( HC.LOCAL_RATING_LIKE, ) )
        numerical_services = CG.client_controller.services_manager.GetServices( ( HC.LOCAL_RATING_NUMERICAL, ) )
        incdec_services = CG.client_controller.services_manager.GetServices( ( HC.LOCAL_RATING_INCDEC, ) )
        
        self._panels = []
        
        if len( like_services ) > 0:
            
            self._panels.append( self._LikePanel( self, like_services, media ) )
            
        
        if len( numerical_services ) > 0:
            
            self._panels.append( self._NumericalPanel( self, numerical_services, media ) )
            
        
        if len( incdec_services ) > 0:
            
            self._panels.append( self._IncDecPanel( self, incdec_services, media ) )
            
        
        self._copy_button = ClientGUICommon.IconButton( self, CC.global_icons().copy, self._Copy )
        self._copy_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'Copy ratings to the clipboard.' ) )
        
        self._paste_button = ClientGUICommon.IconButton( self, CC.global_icons().paste, self._Paste )
        self._paste_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'Paste ratings from the clipboard.' ) )
        
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
        
        vbox.addStretch( 0 )
        
        QP.AddToLayout( vbox, buttonbox, CC.FLAGS_ON_RIGHT )
        
        self.setLayout( vbox )
        
        size_hint = self.sizeHint()
        
        QP.SetInitialSize( self, size_hint )
        
        #
        
        self._my_shortcut_handler = ClientGUIShortcuts.ShortcutsHandler( self, self, [ 'global', 'media' ] )
        
    
    def _Copy( self ):
        
        rating_clipboard_pairs = []
        
        for panel in self._panels:
            
            rating_clipboard_pairs.extend( panel.GetRatingClipboardPairs() )
            
        
        text = json.dumps( [ ( service_key.hex(), rating ) for ( service_key, rating ) in rating_clipboard_pairs ] )
        
        CG.client_controller.pub( 'clipboard', 'text', text )
        
    
    def _Paste( self ):
        
        try:
            
            raw_text = CG.client_controller.GetClipboardText()
            
        except HydrusExceptions.DataMissing as e:
            
            ClientGUIDialogsMessage.ShowCritical( self, 'Error', str( e ) )
            
            return
            
        
        try:
            
            rating_clipboard_pairs_encoded = json.loads( raw_text )
            
            rating_clipboard_pairs = [ ( bytes.fromhex( service_key_encoded ), rating ) for ( service_key_encoded, rating ) in rating_clipboard_pairs_encoded ]
            
        except Exception as e:
            
            ClientGUIDialogsQuick.PresentClipboardParseError( self, raw_text, 'JSON pairs of service keys and rating values', e )
            
            return
            
        
        for panel in self._panels:
            
            panel.SetRatingClipboardPairs( rating_clipboard_pairs )
            
        
    
    def EventOK( self ):
        
        try:
            
            content_update_package = ClientContentUpdates.ContentUpdatePackage()
            
            for panel in self._panels:
                
                content_update_package.AddContentUpdatePackage( panel.GetContentUpdatePackage() )
                
            
            if content_update_package.HasContent():
                
                CG.client_controller.Write( 'content_updates', content_update_package )
                
            
        finally:
            
            self.done( QW.QDialog.DialogCode.Accepted )
            
        
    
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
        
    
    class _IncDecPanel( QW.QWidget ):
        
        def __init__( self, parent, services, media ):
            
            super().__init__( parent )
            
            self._services = services
            
            self._media = media
            
            self._service_keys_to_controls = {}
            self._service_keys_to_original_ratings_states = {}
            
            rows = []
            
            for service in self._services:
                
                name = service.GetName()
                
                service_key = service.GetServiceKey()
                
                ( rating_state, rating ) = ClientRatings.GetIncDecStateFromMedia( self._media, service_key )
                
                control = ClientGUIRatings.RatingIncDecDialog( self, service_key, CC.CANVAS_DIALOG )
                
                if rating_state != ClientRatings.SET:
                    
                    control.SetRatingState( rating_state, rating )
                    
                else:
                    
                    control.SetRating( rating )
                    
                
                self._service_keys_to_controls[ service_key ] = control
                self._service_keys_to_original_ratings_states[ service_key ] = ( rating_state, rating )
                
                rows.append( ( name + ': ', control ) )
                
            
            gridbox = ClientGUICommon.WrapInGrid( self, rows, expand_text = True )
            
            self.setLayout( gridbox )
            
        
        def GetContentUpdatePackage( self ):
            
            content_update_package = ClientContentUpdates.ContentUpdatePackage()
            
            hashes = { hash for hash in itertools.chain.from_iterable( ( media.GetHashes() for media in self._media ) ) }
            
            for ( service_key, control ) in self._service_keys_to_controls.items():
                
                ( original_rating_state, original_rating ) = self._service_keys_to_original_ratings_states[ service_key ]
                
                rating_state = control.GetRatingState()
                
                if rating_state == ClientRatings.MIXED:
                    
                    continue
                    
                else:
                    
                    rating = control.GetRating()
                    
                
                if rating != original_rating:
                    
                    content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( rating, hashes ) )
                    
                    content_update_package.AddContentUpdate( service_key, content_update )
                    
                
            
            return content_update_package
            
        
        def GetRatingClipboardPairs( self ):
            
            rating_clipboard_pairs = []
            
            for ( service_key, control ) in self._service_keys_to_controls.items():
                
                rating_state = control.GetRatingState()
                
                if rating_state == ClientRatings.SET:
                    
                    rating = control.GetRating()
                    
                else:
                    
                    continue
                    
                
                rating_clipboard_pairs.append( ( service_key, rating ) )
                
            
            return rating_clipboard_pairs
            
        
        def SetRatingClipboardPairs( self, rating_clipboard_pairs ):
            
            for ( service_key, rating ) in rating_clipboard_pairs:
                
                if service_key in self._service_keys_to_controls:
                    
                    control = self._service_keys_to_controls[ service_key ]
                    
                    if isinstance( rating, ( int, float ) ):
                        
                        control.SetRating( rating )
                        
                    
                
            
        
        def UpdateControlSizes( self ):
            
            for control in self._service_keys_to_controls.values():
                
                control.UpdateSize()
                
            
        
    
    class _LikePanel( QW.QWidget ):
        
        def __init__( self, parent, services, media ):
            
            super().__init__( parent )
            
            self._services = services
            
            self._media = media
            
            self._service_keys_to_controls = {}
            self._service_keys_to_original_ratings_states = {}
            
            rows = []
            
            for service in self._services:
                
                name = service.GetName()
                
                service_key = service.GetServiceKey()
                
                rating_state = ClientRatings.GetLikeStateFromMedia( self._media, service_key )
                
                control = ClientGUIRatings.RatingLikeDialog( self, service_key, CC.CANVAS_DIALOG )
                
                control.SetRatingState( rating_state )
                
                self._service_keys_to_controls[ service_key ] = control
                self._service_keys_to_original_ratings_states[ service_key ] = rating_state
                
                rows.append( ( name + ': ', control ) )
                
            
            gridbox = ClientGUICommon.WrapInGrid( self, rows, expand_text = True )
            
            self.setLayout( gridbox )
            
        
        def GetContentUpdatePackage( self ):
            
            content_update_package = ClientContentUpdates.ContentUpdatePackage()
            
            hashes = { hash for hash in itertools.chain.from_iterable( ( media.GetHashes() for media in self._media ) ) }
            
            for ( service_key, control ) in list(self._service_keys_to_controls.items()):
                
                original_rating_state = self._service_keys_to_original_ratings_states[ service_key ]
                
                rating_state = control.GetRatingState()
                
                if rating_state != original_rating_state:
                    
                    if rating_state == ClientRatings.MIXED:
                        
                        continue
                        
                    elif rating_state == ClientRatings.LIKE:
                        
                        rating = 1
                        
                    elif rating_state == ClientRatings.DISLIKE:
                        
                        rating = 0
                        
                    else:
                        
                        rating = None
                        
                    
                    content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( rating, hashes ) )
                    
                    content_update_package.AddContentUpdate( service_key, content_update )
                    
                
            
            return content_update_package
            
        
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
                    
                
            
        def UpdateControlSizes( self ):
            
            for control in self._service_keys_to_controls.values():
                
                control.UpdateSize()
                
            
        
    

    class _NumericalPanel( QW.QWidget ):
        
        def __init__( self, parent, services, media ):
            
            super().__init__( parent )
            
            self._services = services
            
            self._media = media
            
            self._service_keys_to_controls = {}
            self._service_keys_to_original_ratings_states = {}
            
            rows = []
            
            for service in self._services:
                
                name = service.GetName()
                
                service_key = service.GetServiceKey()
                
                ( rating_state, rating ) = ClientRatings.GetNumericalStateFromMedia( self._media, service_key )
                
                control = ClientGUIRatings.RatingNumericalDialog( self, service_key, CC.CANVAS_DIALOG )
                
                control.setSizePolicy( QW.QSizePolicy.Policy.Fixed, QW.QSizePolicy.Policy.Fixed )
                
                if rating_state != ClientRatings.SET:
                    
                    control.SetRatingState( rating_state )
                    
                else:
                    
                    control.SetRating( rating )
                    
                
                self._service_keys_to_controls[ service_key ] = control
                self._service_keys_to_original_ratings_states[ service_key ] = ( rating_state, rating )
                
                rows.append( ( name + ': ', control ) )
                
            
            gridbox = ClientGUICommon.WrapInGrid( self, rows, expand_text = True )
            gridbox.setColumnStretch( 1, 0 )
            
            for control in self._service_keys_to_controls.values():
                
                gridbox.setAlignment( control, QC.Qt.AlignmentFlag.AlignRight | QC.Qt.AlignmentFlag.AlignVCenter )
                
            
            self.setLayout( gridbox )
            
        
        def GetContentUpdatePackage( self ):
            
            content_update_package = ClientContentUpdates.ContentUpdatePackage()
            
            hashes = { hash for hash in itertools.chain.from_iterable( ( media.GetHashes() for media in self._media ) ) }
            
            for ( service_key, control ) in list(self._service_keys_to_controls.items()):
                
                ( original_rating_state, original_rating ) = self._service_keys_to_original_ratings_states[ service_key ]
                
                rating_state = control.GetRatingState()
                
                if rating_state == ClientRatings.MIXED:
                    
                    continue
                    
                elif rating_state == ClientRatings.NULL:
                    
                    rating = None
                    
                else:
                    
                    rating = control.GetRating()
                    
                
                if rating != original_rating:
                    
                    content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( rating, hashes ) )
                    
                    content_update_package.AddContentUpdate( service_key, content_update )
                    
                
            
            return content_update_package
            
        
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
                        
                    
                
            
        def UpdateControlSizes( self ):
            
            for control in self._service_keys_to_controls.values():
                
                control.UpdateSize()
                
            
        
    
