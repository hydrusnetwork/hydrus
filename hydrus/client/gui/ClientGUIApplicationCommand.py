import typing

from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG

from hydrus.client import ClientApplicationCommand as CAC
from hydrus.client import ClientConstants as CC
from hydrus.client.gui import ClientGUIScrolledPanels
from hydrus.client.gui import ClientGUIShortcuts
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.search import ClientGUIACDropdown
from hydrus.client.gui.widgets import ClientGUICommon
    
class RatingLikeSubPanel( QW.QWidget ):
    
    def __init__( self, parent: QW.QWidget ):
        
        QW.QWidget.__init__( self, parent )
        
        self._flip_or_set_action = ClientGUICommon.BetterChoice( self )
        
        self._flip_or_set_action.addItem( 'set', HC.CONTENT_UPDATE_SET )
        self._flip_or_set_action.addItem( 'flip on and off', HC.CONTENT_UPDATE_FLIP )
        
        self._flip_or_set_action.SetValue( HC.CONTENT_UPDATE_SET )
        
        self._service_keys = ClientGUICommon.BetterChoice( self )
        self._ratings_like_like = QW.QRadioButton( 'like', self )
        self._ratings_like_dislike = QW.QRadioButton( 'dislike', self )
        self._ratings_like_remove = QW.QRadioButton( 'remove rating', self )
        
        #
        
        services = HG.client_controller.services_manager.GetServices( ( HC.LOCAL_RATING_LIKE, ) )
        
        if len( services ) == 0:
            
            self._service_keys.addItem( 'you have no like/dislike rating services', None )
            
        else:
            
            for service in services:
                
                service_name = service.GetName()
                service_key = service.GetServiceKey()
                
                self._service_keys.addItem( service_name, service_key )
                
            
        
        self._ratings_like_like.setChecked( True )
        
        #
        
        vbox = QP.VBoxLayout()
        
        ratings_like_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( ratings_like_hbox, self._service_keys, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( ratings_like_hbox, self._ratings_like_like, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( ratings_like_hbox, self._ratings_like_dislike, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( ratings_like_hbox, self._ratings_like_remove, CC.FLAGS_CENTER_PERPENDICULAR )
        
        QP.AddToLayout( vbox, self._flip_or_set_action, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, ratings_like_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.setLayout( vbox )
        
        self._ratings_like_remove.toggled.connect( self._UpdateFlipAllowed )
        
    
    def _UpdateFlipAllowed( self ):
        
        if self._ratings_like_remove.isChecked():
            
            self._flip_or_set_action.SetValue( HC.CONTENT_UPDATE_SET )
            self._flip_or_set_action.setEnabled( False )
            
        else:
            
            self._flip_or_set_action.setEnabled( True )
            
        
    
    def GetValue( self ):
        
        service_key = self._service_keys.GetValue()
        
        if service_key is None:
            
            raise HydrusExceptions.VetoException( 'Please select a rating service!' )
            
        
        action = self._flip_or_set_action.GetValue()
        
        if self._ratings_like_like.isChecked():
            
            value = 1.0
            
        elif self._ratings_like_dislike.isChecked():
            
            value = 0.0
            
        else:
            
            value = None
            
        
        return CAC.ApplicationCommand( CAC.APPLICATION_COMMAND_TYPE_CONTENT, ( service_key, HC.CONTENT_TYPE_RATINGS, action, value ) )
        
    
    def SetValue( self, action: int, service_key: bytes, rating: typing.Optional[ float ] ):
        
        self._flip_or_set_action.SetValue( action )
        
        self._service_keys.SetValue( service_key )
        
        self._ratings_like_remove.setChecked( rating is None )
        self._ratings_like_like.setChecked( rating == 1.0 )
        self._ratings_like_dislike.setChecked( rating == 0.0 )
        
    
class RatingNumericalSubPanel( QW.QWidget ):
    
    def __init__( self, parent: QW.QWidget ):
        
        QW.QWidget.__init__( self, parent )
        
        self._current_ratings_numerical_service = None
        
        self._flip_or_set_action = ClientGUICommon.BetterChoice( self )
        
        self._flip_or_set_action.addItem( 'set', HC.CONTENT_UPDATE_SET )
        self._flip_or_set_action.addItem( 'flip on and off', HC.CONTENT_UPDATE_FLIP )
        
        self._flip_or_set_action.SetValue( HC.CONTENT_UPDATE_SET )
        
        self._service_keys = ClientGUICommon.BetterChoice( self )
        self._service_keys.currentIndexChanged.connect( self._UpdateSliderRange )
        self._ratings_numerical_slider = QP.LabelledSlider( self )
        self._ratings_numerical_remove = QW.QCheckBox( 'remove rating', self )
        
        #
        
        services = HG.client_controller.services_manager.GetServices( ( HC.LOCAL_RATING_NUMERICAL, ) )
        
        if len( services ) == 0:
            
            self._service_keys.addItem( 'you have no numerical rating services', None )
            
        else:
            
            for service in services:
                
                service_name = service.GetName()
                service_key = service.GetServiceKey()
                
                self._service_keys.addItem( service_name, service_key )
                
            
        
        self._UpdateSliderRange()
        
        #
        
        vbox = QP.VBoxLayout()
        
        ratings_numerical_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( ratings_numerical_hbox, self._service_keys, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH )
        QP.AddToLayout( ratings_numerical_hbox, self._ratings_numerical_slider, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( ratings_numerical_hbox, self._ratings_numerical_remove, CC.FLAGS_CENTER_PERPENDICULAR )
        
        QP.AddToLayout( vbox, self._flip_or_set_action, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, ratings_numerical_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.setLayout( vbox )
        
        self._ratings_numerical_remove.toggled.connect( self._UpdateFlipAllowed )
        
    
    def _UpdateFlipAllowed( self ):
        
        remove_on = self._ratings_numerical_remove.isChecked()
        
        if remove_on:
            
            self._flip_or_set_action.SetValue( HC.CONTENT_UPDATE_SET )
            
        
        self._flip_or_set_action.setEnabled( not remove_on )
        self._ratings_numerical_slider.setEnabled( not remove_on )
        
    
    def _UpdateSliderRange( self ):
        
        service_key = self._service_keys.GetValue()
        
        if service_key is not None:
            
            service = HG.client_controller.services_manager.GetService( service_key )
            
            self._current_ratings_numerical_service = service
            
            num_stars = service.GetNumStars()
            
            allow_zero = service.AllowZero()
            
            if allow_zero:
                
                minimum = 0
                
            else:
                
                minimum = 1
                
            
            self._ratings_numerical_slider.SetRange( minimum, num_stars )
            
        
    
    def GetValue( self ):
        
        service_key = self._service_keys.GetValue()
        
        if service_key is None:
            
            raise HydrusExceptions.VetoException( 'Please select a rating service!' )
            
        
        action = self._flip_or_set_action.GetValue()
        
        if self._ratings_numerical_remove.isChecked():
            
            rating = None
            
        else:
            
            value = self._ratings_numerical_slider.GetValue()
            
            rating = self._current_ratings_numerical_service.ConvertStarsToRating( value )
            
        
        return CAC.ApplicationCommand( CAC.APPLICATION_COMMAND_TYPE_CONTENT, ( service_key, HC.CONTENT_TYPE_RATINGS, action, rating ) )
        
    
    def SetValue( self, action: int, service_key: bytes, rating: typing.Optional[ float ] ):
        
        self._flip_or_set_action.SetValue( action )
        
        self._service_keys.SetValue( service_key )
        
        self._UpdateSliderRange()
        
        if rating is None:
            
            self._ratings_numerical_remove.setChecked( True )
            
        else:
            
            slider_value = self._current_ratings_numerical_service.ConvertRatingToStars( rating )
            
            self._ratings_numerical_slider.SetValue( slider_value )
            
        
    
class RatingNumericalIncDecSubPanel( QW.QWidget ):
    
    def __init__( self, parent: QW.QWidget ):
        
        QW.QWidget.__init__( self, parent )
        
        self._service_keys = ClientGUICommon.BetterChoice( self )
        
        self._ratings_numerical_incdec = ClientGUICommon.BetterChoice( self )
        
        self._ratings_numerical_incdec.addItem( HC.content_update_string_lookup[ HC.CONTENT_UPDATE_INCREMENT ], HC.CONTENT_UPDATE_INCREMENT )
        self._ratings_numerical_incdec.addItem( HC.content_update_string_lookup[ HC.CONTENT_UPDATE_DECREMENT ], HC.CONTENT_UPDATE_DECREMENT )
        
        #
        
        services = HG.client_controller.services_manager.GetServices( ( HC.LOCAL_RATING_NUMERICAL, ) )
        
        if len( services ) == 0:
            
            self._service_keys.addItem( 'you have no numerical rating services', None )
            
        else:
            
            for service in services:
                
                service_name = service.GetName()
                service_key = service.GetServiceKey()
                
                self._service_keys.addItem( service_name, service_key )
                
            
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._service_keys, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH )
        QP.AddToLayout( hbox, self._ratings_numerical_incdec, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self.setLayout( hbox )
        
    
    def GetValue( self ):
        
        service_key = self._service_keys.GetValue()
        
        if service_key is None:
            
            raise HydrusExceptions.VetoException( 'Please select a rating service!' )
            
        
        action = self._ratings_numerical_incdec.GetValue()
        
        distance = 1
        
        return CAC.ApplicationCommand( CAC.APPLICATION_COMMAND_TYPE_CONTENT, ( service_key, HC.CONTENT_TYPE_RATINGS, action, distance ) )
        
    
    def SetValue( self, action: int, service_key: bytes, distance: int ):
        
        self._service_keys.SetValue( service_key )
        
        self._ratings_numerical_incdec.SetValue( action )
        
    
class SimpleSubPanel( QW.QWidget ):
    
    def __init__( self, parent: QW.QWidget, shortcuts_name: str ):
        
        QW.QWidget.__init__( self, parent )
        
        if shortcuts_name in ClientGUIShortcuts.SHORTCUTS_RESERVED_NAMES:
            
            simple_types = ClientGUIShortcuts.simple_shortcut_name_to_action_lookup[ shortcuts_name ]
            
        else:
            
            simple_types = ClientGUIShortcuts.simple_shortcut_name_to_action_lookup[ 'custom' ]
            
        
        choices = sorted( [ ( CAC.simple_enum_to_str_lookup[ simple_type ], simple_type ) for simple_type in simple_types ] )
        
        self._simple_actions = ClientGUICommon.BetterChoice( self )
        
        for ( display_string, data ) in choices:
            
            self._simple_actions.addItem( display_string, data )
            
        
        self._seek_panel = QW.QWidget( self )
        
        choices = [
            ( 'back', -1 ),
            ( 'forwards', 1 )
        ]
        
        self._seek_direction = ClientGUICommon.BetterRadioBox( self._seek_panel, choices = choices )
        
        self._seek_duration_s = QP.MakeQSpinBox( self._seek_panel, max=3599, width = 60 )
        self._seek_duration_ms = QP.MakeQSpinBox( self._seek_panel, max=999, width = 60 )
        
        #
        
        self._seek_duration_s.setValue( 5 )
        self._seek_duration_ms.setValue( 0 )
        
        self._seek_duration_s.value() * 1000 + self._seek_duration_ms.value()
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._seek_direction, CC.FLAGS_CENTER )
        QP.AddToLayout( hbox, self._seek_duration_s, CC.FLAGS_CENTER )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText( self._seek_panel, label = 's' ), CC.FLAGS_CENTER )
        QP.AddToLayout( hbox, self._seek_duration_ms, CC.FLAGS_CENTER )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText( self._seek_panel, label = 'ms' ), CC.FLAGS_CENTER )
        hbox.addStretch( 1 )
        
        self._seek_panel.setLayout( hbox )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._simple_actions, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        QP.AddToLayout( vbox, self._seek_panel, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.setLayout( vbox )
        
        self._simple_actions.currentIndexChanged.connect( self._UpdateControls )
        
        self._UpdateControls()
        
    
    def _UpdateControls( self ):
        
        action = self._simple_actions.GetValue()
        
        self._seek_panel.setVisible( action == CAC.SIMPLE_MEDIA_SEEK_DELTA )
        
    
    def GetValue( self ):
        
        action = self._simple_actions.GetValue()
        
        if action == '':
            
            raise HydrusExceptions.VetoException( 'Please select an action!' )
            
        else:
            
            if action == CAC.SIMPLE_MEDIA_SEEK_DELTA:
                
                direction = self._seek_direction.GetValue()
                
                s = self._seek_duration_s.value()
                ms = self._seek_duration_ms.value() + ( 1000 * s )
                
                simple_data = ( direction, ms )
                
            else:
                
                simple_data = None
                
            
            return CAC.ApplicationCommand.STATICCreateSimpleCommand( action, simple_data = simple_data )
            
        
    
    def SetValue( self, command: CAC.ApplicationCommand ):
        
        action = command.GetSimpleAction()
        
        self._simple_actions.SetValue( action )
        
        if action == CAC.SIMPLE_MEDIA_SEEK_DELTA:
            
            ( direction, ms ) = command.GetSimpleData()
            
            self._seek_direction.SetValue( direction )
            
            s = ms // 1000
            
            ms = ms % 1000
            
            self._seek_duration_s.setValue( s )
            self._seek_duration_ms.setValue( ms )
            
        
        self._UpdateControls()
        
    
class TagSubPanel( QW.QWidget ):
    
    def __init__( self, parent: QW.QWidget ):
        
        QW.QWidget.__init__( self, parent )
        
        self._flip_or_set_action = ClientGUICommon.BetterChoice( self )
        
        self._flip_or_set_action.addItem( 'set', HC.CONTENT_UPDATE_SET )
        self._flip_or_set_action.addItem( 'flip on and off', HC.CONTENT_UPDATE_FLIP )
        
        self._flip_or_set_action.SetValue( HC.CONTENT_UPDATE_SET )
        
        self._service_keys = ClientGUICommon.BetterChoice( self )
        
        self._tag_value = QW.QLineEdit( self )
        self._tag_value.setReadOnly( True )
        
        default_location_context = HG.client_controller.services_manager.GetDefaultLocationContext()
        
        self._tag_input = ClientGUIACDropdown.AutoCompleteDropdownTagsWrite( self, self.SetTags, default_location_context, CC.COMBINED_TAG_SERVICE_KEY )
        
        #
        
        services = HG.client_controller.services_manager.GetServices( ( HC.LOCAL_TAG, HC.TAG_REPOSITORY ) )
        
        for service in services:
            
            service_name = service.GetName()
            service_key = service.GetServiceKey()
            
            self._service_keys.addItem( service_name, service_key )
            
        
        self._tag_input.SetTagServiceKey( self._service_keys.GetValue() )
        
        #
        
        vbox = QP.VBoxLayout()
        
        tag_sub_vbox = QP.VBoxLayout()
        
        QP.AddToLayout( tag_sub_vbox, self._tag_value, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( tag_sub_vbox, self._tag_input, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        tag_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( tag_hbox, self._service_keys, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH )
        QP.AddToLayout( tag_hbox, tag_sub_vbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        QP.AddToLayout( vbox, self._flip_or_set_action, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, tag_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self.setLayout( vbox )
        
        #
        
        self._service_keys.currentIndexChanged.connect( self._NewServiceKey )
        
    
    def _NewServiceKey( self ):
        
        self._tag_input.SetTagServiceKey( self._service_keys.GetValue() )
        
    
    def GetValue( self ):
        
        service_key = self._service_keys.GetValue()
        
        if service_key is None:
            
            raise HydrusExceptions.VetoException( 'Please select a tag service!' )
            
        
        action = self._flip_or_set_action.GetValue()
        
        tag = self._tag_value.text()
        
        if tag == '':
            
            raise HydrusExceptions.VetoException( 'Please enter a tag!' )
            
        
        return CAC.ApplicationCommand( CAC.APPLICATION_COMMAND_TYPE_CONTENT, ( service_key, HC.CONTENT_TYPE_MAPPINGS, action, tag ) )
        
    
    def SetTags( self, tags ):
        
        if len( tags ) > 0:
            
            tag = list( tags )[0]
            
            self._tag_value.setText( tag )
            
        
    
    def SetValue( self, action: int, service_key: bytes, tag: str ):
        
        self._flip_or_set_action.SetValue( action )
        
        self._service_keys.SetValue( service_key )
        
        self._tag_value.setText( tag )
        
    
class ApplicationCommandWidget( ClientGUIScrolledPanels.EditPanel ):
    
    PANEL_SIMPLE = 0
    PANEL_TAG = 1
    PANEL_RATING_LIKE = 2
    PANEL_RATING_NUMERICAL = 3
    PANEL_RATING_NUMERICAL_INCDEC = 4
    
    def __init__( self, parent: QW.QWidget, command: CAC.ApplicationCommand, shortcuts_name: str ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        #
        
        is_custom_or_media = shortcuts_name not in ClientGUIShortcuts.SHORTCUTS_RESERVED_NAMES or shortcuts_name == 'media'
        
        self._panel_choice = ClientGUICommon.BetterChoice( self )
        
        self._panel_choice.addItem( 'simple command', self.PANEL_SIMPLE )
        
        if is_custom_or_media:
            
            self._panel_choice.addItem( 'tag command', self.PANEL_TAG )
            self._panel_choice.addItem( 'like/dislike rating command', self.PANEL_RATING_LIKE )
            self._panel_choice.addItem( 'numerical rating command', self.PANEL_RATING_NUMERICAL )
            self._panel_choice.addItem( 'numerical rating increment/decrement command', self.PANEL_RATING_NUMERICAL_INCDEC )
            
        else:
            
            self._panel_choice.hide()
            
        
        self._simple_sub_panel = SimpleSubPanel( self, shortcuts_name )
        
        self._tag_sub_panel = TagSubPanel( self )
        
        self._rating_like_sub_panel = RatingLikeSubPanel( self )
        
        self._rating_numerical_sub_panel = RatingNumericalSubPanel( self )
        
        self._rating_numerical_inc_dec_sub_panel = RatingNumericalIncDecSubPanel( self )
        
        #
        
        if command.IsSimpleCommand():
            
            self._simple_sub_panel.SetValue( command )
            
            self._panel_choice.SetValue( self.PANEL_SIMPLE )
            
        elif command.IsContentCommand():
            
            service_key = command.GetContentServiceKey()
            
            if HG.client_controller.services_manager.ServiceExists( service_key ):
                
                service = HG.client_controller.services_manager.GetService( service_key )
                
                action = command.GetContentAction()
                value = command.GetContentValue()
                
            else:
                
                QW.QMessageBox.warning( self, 'Warning', 'The service that this command relies upon no longer exists! This command will reset to a default form.' )
                
                local_tag_services = list( HG.client_controller.services_manager.GetServices( ( HC.LOCAL_TAG, ) ) )
                
                service = local_tag_services[0]
                
                service_key = service.GetServiceKey()
                action = HC.CONTENT_UPDATE_SET
                value = 'tag'
                
            
            service_type = service.GetServiceType()
            
            if service_type in HC.REAL_TAG_SERVICES:
                
                tag = value
                
                self._tag_sub_panel.SetValue( action, service_key, tag )
                
                self._panel_choice.SetValue( self.PANEL_TAG )
                
            elif service_type == HC.LOCAL_RATING_LIKE:
                
                rating = value
                
                self._rating_like_sub_panel.SetValue( action, service_key, rating )
                
                self._panel_choice.SetValue( self.PANEL_RATING_LIKE )
                
            elif service_type == HC.LOCAL_RATING_NUMERICAL:
                
                if action in ( HC.CONTENT_UPDATE_SET, HC.CONTENT_UPDATE_FLIP ):
                    
                    rating = value
                    
                    self._rating_numerical_sub_panel.SetValue( action, service_key, rating )
                    
                    self._panel_choice.SetValue( self.PANEL_RATING_NUMERICAL )
                    
                elif action in ( HC.CONTENT_UPDATE_INCREMENT, HC.CONTENT_UPDATE_DECREMENT ):
                    
                    distance = 1
                    
                    self._rating_numerical_inc_dec_sub_panel.SetValue( action, service_key, distance )
                    
                    self._panel_choice.SetValue( self.PANEL_RATING_NUMERICAL_INCDEC )
                    
                
            
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._panel_choice, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._simple_sub_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._tag_sub_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, self._rating_like_sub_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, self._rating_numerical_sub_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, self._rating_numerical_inc_dec_sub_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.addStretch( 1 )
        
        self.widget().setLayout( vbox )
        
        self._UpdateVisibleControls()
        
        #
        
        self._panel_choice.currentIndexChanged.connect( self._UpdateVisibleControls )
        
    
    def _UpdateVisibleControls( self ):
        
        panel_type = self._panel_choice.GetValue()
        
        self._simple_sub_panel.setVisible( panel_type == self.PANEL_SIMPLE )
        self._tag_sub_panel.setVisible( panel_type == self.PANEL_TAG )
        self._rating_like_sub_panel.setVisible( panel_type == self.PANEL_RATING_LIKE )
        self._rating_numerical_sub_panel.setVisible( panel_type == self.PANEL_RATING_NUMERICAL )
        self._rating_numerical_inc_dec_sub_panel.setVisible( panel_type == self.PANEL_RATING_NUMERICAL_INCDEC )
        
    
    def GetValue( self ):
        
        panel_type = self._panel_choice.GetValue()
        
        if panel_type == self.PANEL_SIMPLE:
            
            return self._simple_sub_panel.GetValue()
            
        elif panel_type == self.PANEL_TAG:
            
            return self._tag_sub_panel.GetValue()
            
        elif panel_type == self.PANEL_RATING_LIKE:
            
            return self._rating_like_sub_panel.GetValue()
            
        elif panel_type == self.PANEL_RATING_NUMERICAL:
            
            return self._rating_numerical_sub_panel.GetValue()
            
        elif panel_type == self.PANEL_RATING_NUMERICAL_INCDEC:
            
            return self._rating_numerical_inc_dec_sub_panel.GetValue()
            
        
    
