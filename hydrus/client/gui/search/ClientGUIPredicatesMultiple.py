import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusGlobals as HG

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientSearch
from hydrus.client.gui import ClientGUIRatings
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.search import ClientGUIPredicatesSingle
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.metadata import ClientRatings

class PredicateSystemRatingIncDecControl( QW.QWidget ):
    
    def __init__( self, parent: QW.QWidget, service_key: bytes, predicate: typing.Optional[ ClientSearch.Predicate ] ):
        
        QW.QWidget.__init__( self, parent )
        
        self._service_key = service_key
        
        service = HG.client_controller.services_manager.GetService( self._service_key )
        
        name = service.GetName()
        
        name_st = ClientGUICommon.BetterStaticText( self, name )
        
        name_st.setAlignment( QC.Qt.AlignLeft | QC.Qt.AlignVCenter )
        
        choices = [
            ( 'more than', '>' ),
            ( 'less than', '<' ),
            ( 'is', '=' ),
            ( 'is about', CC.UNICODE_ALMOST_EQUAL_TO ),
            ( 'do not search', '' )
        ]
        
        self._choice = QP.DataRadioBox( self, choices, vertical = True )
        
        self._rating_value = ClientGUICommon.BetterSpinBox( self, initial = 0, min = 0, max = 1000000 )
        
        self._choice.SetValue( '' )
        
        #
        
        if predicate is not None:
            
            value = predicate.GetValue()
            
            if value is not None:
                
                ( operator, rating, service_key ) = value
                
                self._choice.SetValue( operator )
                
                self._rating_value.setValue( rating )
                
            
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, name_st, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, self._choice, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._rating_value, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self.setLayout( hbox )
        
        self._choice.radioBoxChanged.connect( self._UpdateControls )
        
        self._UpdateControls()
        
    
    def _UpdateControls( self ):
        
        choice = self._choice.GetValue()
        
        spinctrl_matters = choice != ''
        
        self._rating_value.setEnabled( spinctrl_matters )
        
    
    def GetPredicates( self ):
        
        choice = self._choice.GetValue()
        
        if choice == '':
            
            return []
            
        
        operator = choice
        
        rating = self._rating_value.value()
        
        predicate = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_RATING, ( operator, rating, self._service_key ) )
        
        return [ predicate ]
        
    
class PredicateSystemRatingLikeControl( QW.QWidget ):
    
    def __init__( self, parent: QW.QWidget, service_key: bytes, predicate: typing.Optional[ ClientSearch.Predicate ] ):
        
        QW.QWidget.__init__( self, parent )
        
        self._service_key = service_key
        
        service = HG.client_controller.services_manager.GetService( self._service_key )
        
        name = service.GetName()
        
        name_st = ClientGUICommon.BetterStaticText( self, name )
        
        name_st.setAlignment( QC.Qt.AlignLeft | QC.Qt.AlignVCenter )
        
        choices = [
            ( 'has rating', 'rated' ),
            ( 'is', '=' ),
            ( 'do not search', '' )
        ]
        
        self._choice = QP.DataRadioBox( self, choices, vertical = True )
        
        self._rating_control = ClientGUIRatings.RatingLikeDialog( self, service_key )
        
        #
        
        self._choice.SetValue( '' )
        
        if predicate is not None:
            
            value = predicate.GetValue()
            
            if value is not None:
                
                ( operator, rating, service_key ) = value
                
                if rating == 'rated':
                    
                    self._choice.SetValue( 'rated' )
                    
                else:
                    
                    self._choice.SetValue( '=' )
                    
                    if rating == 'not rated':
                        
                        self._rating_control.SetRatingState( ClientRatings.NULL )
                        
                    elif rating == 0:
                        
                        self._rating_control.SetRatingState( ClientRatings.DISLIKE )
                        
                    else:
                        
                        self._rating_control.SetRatingState( ClientRatings.LIKE )
                        
                    
                
            
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, name_st, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, self._choice, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._rating_control, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self.setLayout( hbox )
        
        self._choice.radioBoxChanged.connect( self._UpdateControls )
        self._rating_control.valueChanged.connect( self._RatingChanged )
        
        self._UpdateControls()
        
    
    def _RatingChanged( self ):
        
        if self._choice.GetValue() in ( 'rated', '' ):
            
            self._choice.SetValue( '=' )
            
        
    
    def _UpdateControls( self ):
        
        choice = self._choice.GetValue()
        
        if choice in ( 'rated', '' ):
            
            self._rating_control.blockSignals( True )
            self._rating_control.SetRatingState( ClientRatings.NULL )
            self._rating_control.blockSignals( False )
            
        
    
    def GetPredicates( self ):
        
        choice = self._choice.GetValue()
        
        if choice == '':
            
            return []
            
        
        if choice == 'rated':
            
            rating = 'rated'
            
        else:
            
            rating_state = self._rating_control.GetRatingState()
            
            if rating_state == ClientRatings.LIKE:
                
                rating = 1
                
            elif rating_state == ClientRatings.DISLIKE:
                
                rating = 0
                
            else:
                
                rating = 'not rated'
                
            
        
        predicate = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_RATING, ( '=', rating, self._service_key ) )
        
        return [ predicate ]
        
    
class PredicateSystemRatingNumericalControl( QW.QWidget ):
    
    def __init__( self, parent: QW.QWidget, service_key: bytes, predicate: typing.Optional[ ClientSearch.Predicate ] ):
        
        QW.QWidget.__init__( self, parent )
        
        self._service_key = service_key
        
        service = HG.client_controller.services_manager.GetService( self._service_key )
        
        name = service.GetName()
        
        name_st = ClientGUICommon.BetterStaticText( self, name )
        
        name_st.setAlignment( QC.Qt.AlignLeft | QC.Qt.AlignVCenter )
        
        choices = [
            ( 'has rating', 'rated' ),
            ( 'more than', '>' ),
            ( 'less than', '<' ),
            ( 'is', '=' ),
            ( 'is about', CC.UNICODE_ALMOST_EQUAL_TO ),
            ( 'do not search', '' )
        ]
        
        self._choice = QP.DataRadioBox( self, choices, vertical = True )
        
        self._rating_control = ClientGUIRatings.RatingNumericalDialog( self, service_key )
        
        self._choice.SetValue( '' )
        
        #
        
        if predicate is not None:
            
            value = predicate.GetValue()
            
            if value is not None:
                
                ( operator, rating, service_key ) = value
                
                if rating == 'rated':
                    
                    self._choice.SetValue( 'rated' )
                    
                elif rating == 'not rated':
                    
                    self._choice.SetValue( '=' )
                    
                    self._rating_control.SetRating( None )
                    
                else:
                    
                    self._choice.SetValue( operator )
                    
                    self._rating_control.SetRating( rating )
                    
                
            
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, name_st, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, self._choice, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._rating_control, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self.setLayout( hbox )
        
        self._choice.radioBoxChanged.connect( self._UpdateControls )
        self._rating_control.valueChanged.connect( self._RatingChanged )
        
        self._UpdateControls()
        
    
    def _RatingChanged( self ):
        
        if self._choice.GetValue() in ( 'rated', '' ):
            
            self._choice.SetValue( '=' )
            
        
    
    def _UpdateControls( self ):
        
        choice = self._choice.GetValue()
        
        if choice in ( 'rated', '' ):
            
            self._rating_control.blockSignals( True )
            self._rating_control.SetRating( None )
            self._rating_control.blockSignals( False )
            
        
    
    def GetPredicates( self ):
        
        choice = self._choice.GetValue()
        
        if choice == '':
            
            return []
            
        
        operator = '='
        rating = None
        
        if choice == 'rated':
            
            operator = '='
            rating = 'rated'
            
        else:
            
            operator = choice
            
            if self._rating_control.GetRatingState() == ClientRatings.NULL:
                
                if operator != '=':
                    
                    return []
                    
                
                rating = 'not rated'
                
            else:
                
                rating = self._rating_control.GetRating()
                
            
        
        predicate = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_RATING, ( operator, rating, self._service_key ) )
        
        return [ predicate ]
        
    
class PanelPredicateSystemMultiple( ClientGUIPredicatesSingle.PanelPredicateSystem ):
    
    def _FilterWhatICanEdit( self, predicates: typing.Collection[ ClientSearch.Predicate ] ) -> typing.Collection[ ClientSearch.Predicate ]:
        
        raise NotImplementedError()
        
    
    def _GetPredicatesToInitialisePanelWith( self, predicates: typing.Collection[ ClientSearch.Predicate ] ) -> typing.Collection[ ClientSearch.Predicate ]:
        
        raise NotImplementedError()
        
    
    def ClearCustomDefault( self ):
        
        raise NotImplementedError()
        
    
    def GetDefaultPredicates( self ) -> typing.Collection[ ClientSearch.Predicate ]:
        
        raise NotImplementedError()
        
    
    def GetPredicates( self ):
        
        raise NotImplementedError()
        
    
    def SaveCustomDefault( self ):
        
        raise NotImplementedError()
        
    
    def UsesCustomDefault( self ) -> bool:
        
        raise NotImplementedError()
        
    
class PanelPredicateSystemRating( PanelPredicateSystemMultiple ):
    
    def __init__( self, parent, predicates ):
        
        PanelPredicateSystemMultiple.__init__( self, parent )
        
        #
        
        local_like_services = HG.client_controller.services_manager.GetServices( ( HC.LOCAL_RATING_LIKE, ) )
        
        gridbox = QP.GridLayout( cols = 5 )
        
        gridbox.setColumnStretch( 0, 1 )
        
        predicates = self._GetPredicatesToInitialisePanelWith( predicates )
        
        service_keys_to_predicates = { predicate.GetValue()[2] : predicate for predicate in predicates }
        
        self._rating_panels = []
        
        for service in local_like_services:
            
            service_key = service.GetServiceKey()
            
            if service_key in service_keys_to_predicates:
                
                predicate = service_keys_to_predicates[ service_key ]
                
            else:
                
                predicate = None
                
            
            panel = PredicateSystemRatingLikeControl( self, service_key, predicate )
            
            self._rating_panels.append( panel )
            
        
        #
        
        local_numerical_services = HG.client_controller.services_manager.GetServices( ( HC.LOCAL_RATING_NUMERICAL, ) )
        
        for service in local_numerical_services:
            
            service_key = service.GetServiceKey()
            
            if service_key in service_keys_to_predicates:
                
                predicate = service_keys_to_predicates[ service_key ]
                
            else:
                
                predicate = None
                
            
            panel = PredicateSystemRatingNumericalControl( self, service_key, predicate )
            
            self._rating_panels.append( panel )
            
        
        #
        
        local_incdec_services = HG.client_controller.services_manager.GetServices( ( HC.LOCAL_RATING_INCDEC, ) )
        
        for service in local_incdec_services:
            
            service_key = service.GetServiceKey()
            
            if service_key in service_keys_to_predicates:
                
                predicate = service_keys_to_predicates[ service_key ]
                
            else:
                
                predicate = None
                
            
            panel = PredicateSystemRatingIncDecControl( self, service_key, predicate )
            
            self._rating_panels.append( panel )
            
        
        #
        
        vbox = QP.VBoxLayout()
        
        for panel in self._rating_panels:
            
            QP.AddToLayout( vbox, panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        self.setLayout( vbox )
        
    
    def _FilterWhatICanEdit( self, predicates: typing.Collection[ ClientSearch.Predicate ] ) -> typing.Collection[ ClientSearch.Predicate ]:
        
        local_rating_service_keys = HG.client_controller.services_manager.GetServiceKeys( HC.RATINGS_SERVICES )
        
        good_predicates = []
        
        for predicate in predicates:
            
            value = predicate.GetValue()
            
            if value is not None:
                
                ( operator, rating, service_key ) = value
                
                if service_key in local_rating_service_keys:
                    
                    good_predicates.append( predicate )
                    
                
            
        
        return good_predicates
        
    
    def _GetPredicatesToInitialisePanelWith( self, predicates: typing.Collection[ ClientSearch.Predicate ] ) -> typing.Collection[ ClientSearch.Predicate ]:
        
        predicates = self._FilterWhatICanEdit( predicates )
        
        if len( predicates ) > 0:
            
            return predicates
            
        
        custom_default_predicates = HG.client_controller.new_options.GetCustomDefaultSystemPredicates( predicate_type = ClientSearch.PREDICATE_TYPE_SYSTEM_RATING )
        
        custom_default_predicates = self._FilterWhatICanEdit( custom_default_predicates )
        
        if len( custom_default_predicates ) > 0:
            
            return custom_default_predicates
            
        
        default_predicates = self.GetDefaultPredicates()
        
        return default_predicates
        
    
    def ClearCustomDefault( self ):
        
        HG.client_controller.new_options.ClearCustomDefaultSystemPredicates( predicate_type = ClientSearch.PREDICATE_TYPE_SYSTEM_RATING )
        
    
    def GetDefaultPredicates( self ):
        
        return []
        
    
    def GetPredicates( self ):
        
        predicates = []
        
        for panel in self._rating_panels:
            
            predicates.extend( panel.GetPredicates() )
            
        
        return predicates
        
    
    def SaveCustomDefault( self ):
        
        predicates = self.GetPredicates()
        
        HG.client_controller.new_options.SetCustomDefaultSystemPredicates( predicate_type = ClientSearch.PREDICATE_TYPE_SYSTEM_RATING, predicates = predicates )
        
    
    def UsesCustomDefault( self ) -> bool:
        
        custom_default_predicates = HG.client_controller.new_options.GetCustomDefaultSystemPredicates( predicate_type = ClientSearch.PREDICATE_TYPE_SYSTEM_RATING )
        
        custom_default_predicates = self._FilterWhatICanEdit( custom_default_predicates )
        
        return len( custom_default_predicates ) > 0
        
    
