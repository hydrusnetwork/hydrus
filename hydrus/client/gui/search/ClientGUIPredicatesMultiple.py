import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientSearch
from hydrus.client.gui import ClientGUIRatings
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.search import ClientGUIPredicatesSingle
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.metadata import ClientRatings

class PredicateSystemRatingLikeControl( QW.QWidget ):
    
    def __init__( self, parent: QW.QWidget, service_key: bytes, predicate: typing.Optional[ ClientSearch.Predicate ] ):
        
        QW.QWidget.__init__( self, parent )
        
        self._service_key = service_key
        
        service = HG.client_controller.services_manager.GetService( self._service_key )
        
        name = service.GetName()
        
        name_st = ClientGUICommon.BetterStaticText( self, name )
        
        name_st.setAlignment( QC.Qt.AlignLeft | QC.Qt.AlignVCenter )
        
        self._rated_checkbox = QW.QCheckBox( 'rated', self )
        self._not_rated_checkbox = QW.QCheckBox( 'not rated', self )
        self._rating_control = ClientGUIRatings.RatingLikeDialog( self, service_key )
        
        #
        
        if predicate is not None:
            
            value = predicate.GetValue()
            
            if value is not None:
                
                ( operator, rating, service_key ) = value
                
                if rating == 'rated':
                    
                    self._rated_checkbox.setChecked( True )
                    
                elif rating == 'not rated':
                    
                    self._not_rated_checkbox.setChecked( True )
                    
                else:
                    
                    if rating == 0:
                        
                        self._rating_control.SetRatingState( ClientRatings.DISLIKE )
                        
                    else:
                        
                        self._rating_control.SetRatingState( ClientRatings.LIKE )
                        
                    
                
            
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, name_st, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, self._rated_checkbox, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._not_rated_checkbox, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._rating_control, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self.setLayout( hbox )
        
    
    def GetPredicates( self ):
        
        rating = None
        
        if self._rated_checkbox.isChecked():
            
            rating = 'rated'
            
        elif self._not_rated_checkbox.isChecked():
            
            rating = 'not rated'
            
        else:
            
            rating_state = self._rating_control.GetRatingState()
            
            if rating_state == ClientRatings.LIKE:
                
                rating = 1
                
            elif rating_state == ClientRatings.DISLIKE:
                
                rating = 0
                
            
        
        if rating is None:
            
            return []
            
        else:
            
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
        
        self._rated_checkbox = QW.QCheckBox( 'rated', self )
        self._not_rated_checkbox = QW.QCheckBox( 'not rated', self )
        self._operator = QP.RadioBox( self, choices = [ '>', '<', '=', CC.UNICODE_ALMOST_EQUAL_TO ] )
        self._rating_control = ClientGUIRatings.RatingNumericalDialog( self, service_key )
        
        self._operator.Select( 2 )
        
        #
        
        if predicate is not None:
            
            value = predicate.GetValue()
            
            if value is not None:
                
                ( operator, rating, service_key ) = value
                
                if rating == 'rated':
                    
                    self._rated_checkbox.setChecked( True )
                    
                elif rating == 'not rated':
                    
                    self._not_rated_checkbox.setChecked( True )
                    
                else:
                    
                    self._operator.SetStringSelection( operator )
                    
                    self._rating_control.SetRating( rating )
                    
                
            
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, name_st, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, self._rated_checkbox, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._not_rated_checkbox, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._operator, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._rating_control, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self.setLayout( hbox )
        
    
    def GetPredicates( self ):
        
        rating = None
        
        if self._rated_checkbox.isChecked():
            
            operator = '='
            rating = 'rated'
            
        elif self._not_rated_checkbox.isChecked():
            
            operator = '='
            rating = 'not rated'
            
        elif self._rating_control.GetRatingState() != ClientRatings.NULL:
            
            operator = self._operator.GetStringSelection()
            
            rating = self._rating_control.GetRating()
            
        
        if rating is None:
            
            return []
            
        else:
            
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
        
    
    def SetPredicates( self, predicates: typing.Collection[ ClientSearch.Predicate ] ):
        
        raise NotImplementedError()
        
    
    def UsesCustomDefault( self ) -> bool:
        
        raise NotImplementedError()
        
    
class PanelPredicateSystemRating( PanelPredicateSystemMultiple ):
    
    def __init__( self, parent, predicates ):
        
        PanelPredicateSystemMultiple.__init__( self, parent )
        
        #
        
        local_like_service_keys = HG.client_controller.services_manager.GetServiceKeys( ( HC.LOCAL_RATING_LIKE, ) )
        
        self._like_checkboxes_to_info = {}
        
        self._like_rating_ctrls = []
        
        gridbox = QP.GridLayout( cols = 5 )
        
        gridbox.setColumnStretch( 0, 1 )
        
        predicates = self._GetPredicatesToInitialisePanelWith( predicates )
        
        service_keys_to_predicates = { predicate.GetValue()[2] : predicate for predicate in predicates }
        
        self._rating_panels = []
        
        for service_key in local_like_service_keys:
            
            if service_key in service_keys_to_predicates:
                
                predicate = service_keys_to_predicates[ service_key ]
                
            else:
                
                predicate = None
                
            
            panel = PredicateSystemRatingLikeControl( self, service_key, predicate )
            
            self._rating_panels.append( panel )
            
        
        #
        
        local_numerical_service_keys = HG.client_controller.services_manager.GetServiceKeys( ( HC.LOCAL_RATING_NUMERICAL, ) )
        
        self._numerical_checkboxes_to_info = {}
        
        self._numerical_rating_ctrls_to_info = {}
        
        for service_key in local_numerical_service_keys:
            
            if service_key in service_keys_to_predicates:
                
                predicate = service_keys_to_predicates[ service_key ]
                
            else:
                
                predicate = None
                
            
            panel = PredicateSystemRatingNumericalControl( self, service_key, predicate )
            
            self._rating_panels.append( panel )
            
        
        #
        
        vbox = QP.VBoxLayout()
        
        for panel in self._rating_panels:
            
            QP.AddToLayout( vbox, panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        self.setLayout( vbox )
        
    
    def _FilterWhatICanEdit( self, predicates: typing.Collection[ ClientSearch.Predicate ] ) -> typing.Collection[ ClientSearch.Predicate ]:
        
        local_rating_service_keys = HG.client_controller.services_manager.GetServiceKeys( ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ) )
        
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
        
    
