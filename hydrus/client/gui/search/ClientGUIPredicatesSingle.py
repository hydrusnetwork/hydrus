import os
import re

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusLists
from hydrus.core import HydrusTags
from hydrus.core import HydrusText
from hydrus.core.files import HydrusFileHandling
from hydrus.core.files.images import HydrusImageHandling

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientLocation
from hydrus.client import ClientServices
from hydrus.client.files.images import ClientImagePerceptualHashes
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIOptionsPanels
from hydrus.client.gui import ClientGUIRatings
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.metadata import ClientGUITime
from hydrus.client.gui.services import ClientGUIServiceSpecifier
from hydrus.client.gui.widgets import ClientGUIBytes
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.gui.widgets import ClientGUINumberTest
from hydrus.client.gui.widgets import ClientGUIRegex
from hydrus.client.metadata import ClientRatings
from hydrus.client.metadata import ClientTags
from hydrus.client.parsing import ClientParsing
from hydrus.client.search import ClientNumberTest
from hydrus.client.search import ClientSearchPredicate

class StaticSystemPredicateButton( QW.QWidget ):
    
    predicatesChosen = QC.Signal( QW.QWidget )
    predicatesRemoved = QC.Signal( QW.QWidget )
    
    def __init__( self, parent, predicates, forced_label = None, show_remove_button = True ):
        
        super().__init__( parent )
        
        self._predicates = predicates
        self._forced_label = forced_label
        
        if forced_label is None:
            
            label = ', '.join( ( predicate.ToString() for predicate in self._predicates ) )
            
        else:
            
            label = forced_label
            
        
        self._predicates_button = ClientGUICommon.BetterButton( self, label, self._DoPredicatesChoose )
        self._remove_button = ClientGUICommon.IconButton( self, CC.global_icons().trash_delete, self._DoPredicatesRemove )
        
        hbox = QP.HBoxLayout()
        
        if show_remove_button:
            
            flag = CC.FLAGS_EXPAND_BOTH_WAYS
            
        else:
            
            flag = CC.FLAGS_EXPAND_SIZER_BOTH_WAYS
            
            self._remove_button.hide()
            
        
        QP.AddToLayout( hbox, self._predicates_button, flag )
        QP.AddToLayout( hbox, self._remove_button, CC.FLAGS_CENTER )
        
        self.setFocusProxy( self._predicates_button )
        
        self.setLayout( hbox )
        
    
    def _DoPredicatesChoose( self ):
        
        self.predicatesChosen.emit( self )
        
    
    def _DoPredicatesRemove( self ):
        
        self.predicatesRemoved.emit( self )
        
    
    def GetPredicates( self ) -> list[ ClientSearchPredicate.Predicate ]:
        
        return self._predicates
        
    

class TimeDateOperator( ClientGUICommon.BetterRadioBox ):
    
    def __init__( self, parent ):
        
        choice_tuples = [
            ( 'before', '<' ),
            ( 'since', '>' ),
            ( 'the day of', '=' ),
            ( '+/- a month of', HC.UNICODE_APPROX_EQUAL )
        ]
        
        super().__init__( parent, choice_tuples, vertical = True )
        
    

class TimeDeltaOperator( ClientGUICommon.BetterRadioBox ):
    
    def __init__( self, parent ):
        
        choice_tuples = [
            ( 'before', '>' ),
            ( 'since', '<' ),
            ( '+/- 15% of', HC.UNICODE_APPROX_EQUAL )
        ]
        
        super().__init__( parent, choice_tuples, vertical = True )
        
    

class InvertiblePredicateButton( ClientGUICommon.BetterButton ):
    
    def __init__( self, parent: QW.QWidget, predicate: ClientSearchPredicate.Predicate ):
        
        self._predicate = predicate
        
        super().__init__( parent, 'predicate', self._ButtonHit )
        
        self._UpdateLabel()
        
    
    def _ButtonHit( self ):
        
        inverse_predicate = self._predicate.GetInverseCopy()
        
        if inverse_predicate is not None:
            
            self._predicate = inverse_predicate
            
            self._UpdateLabel()
            
        
    
    def _UpdateLabel( self ):
        
        s = self._predicate.ToString( with_count = False )
        
        self.setText( s )
        
    
    def GetPredicate( self ):
        
        return self._predicate
        
    

def GetPredicateFromSimpleTagText( simple_tag_text: str ):
    
    inclusive = True
    
    while simple_tag_text.startswith( '-' ):
        
        inclusive = False
        simple_tag_text = simple_tag_text[1:]
        
    
    if simple_tag_text == '':
        
        raise Exception( 'Please enter some tag, namespace, or wildcard text!' )
        
    
    if simple_tag_text.count( ':' ) == 1 and ( simple_tag_text.endswith( ':' ) or simple_tag_text.endswith( ':*' ) ):
        
        if simple_tag_text.endswith( ':' ):
            
            namespace = simple_tag_text[:-1]
            
        else:
            
            namespace = simple_tag_text[:-2]
            
        
        if namespace == '':
            
            raise Exception( 'Please enter some namespace text!' )
            
        
        return ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_NAMESPACE, namespace, inclusive = inclusive )
        
    elif '*' in simple_tag_text:
        
        wildcard = simple_tag_text
        
        return ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_WILDCARD, wildcard, inclusive = inclusive )
        
    else:
        
        tag = simple_tag_text
        
        return ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, tag, inclusive = inclusive )
        
    

class PanelPredicateSimpleTagTypes( QW.QWidget ):
    
    def __init__( self, parent: QW.QWidget, predicate: ClientSearchPredicate.Predicate ):
        
        super().__init__( parent )
        
        if predicate.GetType() not in ( ClientSearchPredicate.PREDICATE_TYPE_TAG, ClientSearchPredicate.PREDICATE_TYPE_NAMESPACE, ClientSearchPredicate.PREDICATE_TYPE_WILDCARD ):
            
            raise Exception( 'Launched a SimpleTextPredicateControl without a Tag, Namespace, or Wildcard Pred!' )
            
        
        self._simple_tag_text = QW.QLineEdit( self )
        
        inclusive = predicate.IsInclusive()
        
        if predicate.GetType() == ClientSearchPredicate.PREDICATE_TYPE_NAMESPACE:
            
            namespace = predicate.GetValue()
            
            text = '{}{}:*'.format( '' if inclusive else '-', namespace )
            
        else:
            
            inclusive = predicate.IsInclusive()
            wildcard_or_tag = predicate.GetValue()
            
            text = '{}{}'.format( '' if inclusive else '-', wildcard_or_tag )
            
        
        self._simple_tag_text.setText( text )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._simple_tag_text, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.setLayout( vbox )
        
        ClientGUIFunctions.SetFocusLater( self._simple_tag_text )
        
    
    def CheckValid( self ):
        
        try:
            
            predicates = self.GetPredicates()
            
        except Exception as e:
            
            raise HydrusExceptions.VetoException( str( e ) )
            
        
    
    def GetPredicates( self ):
        
        simple_tag_text = self._simple_tag_text.text()
        
        simple_tag_text_predicate = GetPredicateFromSimpleTagText( simple_tag_text )
        
        return [ simple_tag_text_predicate ]
        
    

class PanelPredicateSystem( QW.QWidget ):
    
    def __init__( self, parent ):
        
        super().__init__( parent )
        
    
    def CheckValid( self ):
        
        try:
            
            predicates = self.GetPredicates()
            
        except Exception as e:
            
            raise HydrusExceptions.VetoException( str( e ) )
            
        
    
    def ClearCustomDefault( self ):
        
        raise NotImplementedError()
        
    
    def GetPredicates( self ):
        
        raise NotImplementedError()
        
    
    def SaveCustomDefault( self ):
        
        raise NotImplementedError()
        
    
    def UsesCustomDefault( self ) -> bool:
        
        raise NotImplementedError()
        
    
class PanelPredicateSystemSingle( PanelPredicateSystem ):
    
    def _GetPredicateToInitialisePanelWith( self, predicate: ClientSearchPredicate.Predicate ) -> ClientSearchPredicate.Predicate:
        
        default_predicate = self.GetDefaultPredicate()
        
        if predicate.IsUIEditable( default_predicate ):
            
            return predicate
            
        
        custom_defaults = CG.client_controller.new_options.GetCustomDefaultSystemPredicates( comparable_predicate = default_predicate )
        
        if len( custom_defaults ) > 0:
            
            return list( custom_defaults )[0]
            
        
        return default_predicate
        
    
    def ClearCustomDefault( self ):
        
        default_predicate = self.GetDefaultPredicate()
        
        CG.client_controller.new_options.ClearCustomDefaultSystemPredicates( comparable_predicate = default_predicate )
        
    
    def GetDefaultPredicate( self ) -> ClientSearchPredicate.Predicate:
        
        raise NotImplementedError()
        
    
    def GetPredicates( self ):
        
        raise NotImplementedError()
        
    
    def SaveCustomDefault( self ):
        
        predicates = self.GetPredicates()
        
        CG.client_controller.new_options.SetCustomDefaultSystemPredicates( comparable_predicates = predicates )
        
    
    def UsesCustomDefault( self ) -> bool:
        
        default_predicate = self.GetDefaultPredicate()
        
        custom_defaults = CG.client_controller.new_options.GetCustomDefaultSystemPredicates( comparable_predicate = default_predicate )
        
        return len( custom_defaults ) > 0
        
    
class PanelPredicateSystemDate( PanelPredicateSystemSingle ):
    
    def __init__( self, parent, predicate ):
        
        super().__init__( parent )
        
        self._sign = TimeDateOperator( self )
        
        self._date = QW.QCalendarWidget( self )
        
        self._time = QW.QTimeEdit( self )
        
        #
        
        predicate = self._GetPredicateToInitialisePanelWith( predicate )
        
        ( sign, age_type, ( years, months, days, hours, minutes ) ) = predicate.GetValue()
        
        self._sign.SetValue( sign )
        
        qt_dt = QC.QDate( years, months, days )
        
        self._date.setSelectedDate( qt_dt )
        
        qt_t = QC.QTime( hours, minutes )
        
        self._time.setTime( qt_t )
        
        #
        
        hbox = QP.HBoxLayout()
        
        system_pred_label = self._GetSystemPredicateLabel()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText( self, system_pred_label ), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._date, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._time, CC.FLAGS_CENTER_PERPENDICULAR )
        hbox.addStretch( 0 )
        
        self.setLayout( hbox )
        
        self.setFocusProxy( self._sign )
        
    
    def _GetSystemPredicateLabel( self ) -> str:
        
        raise NotImplementedError()
        
    
    def _GetPredicateType( self ) -> int:
        
        raise NotImplementedError()
        
    
    def GetDefaultPredicate( self ) -> ClientSearchPredicate.Predicate:
        
        qt_dt = QC.QDate.currentDate()
        
        qt_dt.addDays( -7 )
        
        year = qt_dt.year()
        month = qt_dt.month()
        day = qt_dt.day()
        
        hour = 0
        minute = 0
        
        predicate_type = self._GetPredicateType()
        
        return ClientSearchPredicate.Predicate( predicate_type, ( '>', 'date', ( year, month, day, hour, minute ) ) )
        
    
    def GetPredicates( self ):
        
        qt_dt = self._date.selectedDate()
        
        year = qt_dt.year()
        month = qt_dt.month()
        day = qt_dt.day()
        
        qt_t = self._time.time()
        
        hour = qt_t.hour()
        minute = qt_t.minute()
        
        predicate_type = self._GetPredicateType()
        
        predicates = ( ClientSearchPredicate.Predicate( predicate_type, ( self._sign.GetValue(), 'date', ( year, month, day, hour, minute ) ) ), )
        
        return predicates
        
    

class PanelPredicateSystemAgeDate( PanelPredicateSystemDate ):
    
    def _GetSystemPredicateLabel( self ) -> str:
        
        return 'system:import time'
        
    
    def _GetPredicateType( self ) -> int:
        
        return ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_IMPORT_TIME
        
    
    def GetDefaultPredicate( self ) -> ClientSearchPredicate.Predicate:
        
        qt_dt = QC.QDate.currentDate()
        
        qt_dt.addDays( -7 )
        
        year = qt_dt.year()
        month = qt_dt.month()
        day = qt_dt.day()
        
        hour = 0
        minute = 0
        
        predicate_type = self._GetPredicateType()
        
        return ClientSearchPredicate.Predicate( predicate_type, ( '<', 'date', ( year, month, day, hour, minute ) ) )
        
    

class PanelPredicateSystemLastViewedDate( PanelPredicateSystemDate ):
    
    def _GetSystemPredicateLabel( self ) -> str:
        
        return 'system:last viewed time'
        
    
    def _GetPredicateType( self ) -> int:
        
        return ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_LAST_VIEWED_TIME
        
    

class PanelPredicateSystemArchivedDate( PanelPredicateSystemDate ):
    
    def _GetSystemPredicateLabel( self ) -> str:
        
        return 'system:archived time'
        
    
    def _GetPredicateType( self ) -> int:
        
        return ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_ARCHIVED_TIME
        
    

class PanelPredicateSystemModifiedDate( PanelPredicateSystemDate ):
    
    def _GetSystemPredicateLabel( self ) -> str:
        
        return 'system:modified time'
        
    
    def _GetPredicateType( self ) -> int:
        
        return ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MODIFIED_TIME
        
    

class PanelPredicateSystemAgeDelta( PanelPredicateSystemSingle ):
    
    def __init__( self, parent, predicate ):
        
        super().__init__( parent )
        
        self._sign = TimeDeltaOperator( self )
        
        self._years = ClientGUICommon.BetterSpinBox( self, max = 50000 )
        self._months = ClientGUICommon.BetterSpinBox( self, max = 1000 )
        self._days = ClientGUICommon.BetterSpinBox( self, max = 1000 )
        self._hours = ClientGUICommon.BetterSpinBox( self, max = 10000 )
        
        #
        
        predicate = self._GetPredicateToInitialisePanelWith( predicate )
        
        ( sign, age_type, ( years, months, days, hours ) ) = predicate.GetValue()
        
        self._sign.SetValue( sign )
        
        self._years.setValue( years )
        self._months.setValue( months )
        self._days.setValue( days )
        self._hours.setValue( hours )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:import time'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._years, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'years'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._months, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'months'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._days, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'days'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._hours, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'hours ago'), CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 0 )
        
        self.setLayout( hbox )
        
        self.setFocusProxy( self._sign )
        
    
    def GetDefaultPredicate( self ):
        
        return ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_IMPORT_TIME, ( '<', 'delta', ( 0, 0, 7, 0 ) ) )
        
    
    def GetPredicates( self ):
        
        predicates = ( ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_IMPORT_TIME, ( self._sign.GetValue(), 'delta', (self._years.value(), self._months.value(), self._days.value(), self._hours.value() ) ) ), )
        
        return predicates
        
    

# TODO: Merge all this gubbins together, like date above
class PanelPredicateSystemLastViewedDelta( PanelPredicateSystemSingle ):
    
    def __init__( self, parent, predicate ):
        
        super().__init__( parent )
        
        self._sign = TimeDeltaOperator( self )
        
        self._years = ClientGUICommon.BetterSpinBox( self, max = 50000 )
        self._months = ClientGUICommon.BetterSpinBox( self, max = 1000 )
        self._days = ClientGUICommon.BetterSpinBox( self, max = 1000 )
        self._hours = ClientGUICommon.BetterSpinBox( self, max = 10000 )
        
        #
        
        predicate = self._GetPredicateToInitialisePanelWith( predicate )
        
        ( sign, age_type, ( years, months, days, hours ) ) = predicate.GetValue()
        
        self._sign.SetValue( sign )
        
        self._years.setValue( years )
        self._months.setValue( months )
        self._days.setValue( days )
        self._hours.setValue( hours )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:last viewed time'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._years, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'years'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._months, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'months'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._days, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'days'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._hours, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'hours ago'), CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 0 )
        
        self.setLayout( hbox )
        
    
    def GetDefaultPredicate( self ):
        
        return ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_LAST_VIEWED_TIME, ( '<', 'delta', ( 0, 0, 7, 0 ) ) )
        
    
    def GetPredicates( self ):
        
        predicates = ( ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_LAST_VIEWED_TIME, ( self._sign.GetValue(), 'delta', ( self._years.value(), self._months.value(), self._days.value(), self._hours.value() ) ) ), )
        
        return predicates
        
    

class PanelPredicateSystemArchivedDelta( PanelPredicateSystemSingle ):
    
    def __init__( self, parent, predicate ):
        
        super().__init__( parent )
        
        self._sign = TimeDeltaOperator( self )
        
        self._years = ClientGUICommon.BetterSpinBox( self, max = 50000 )
        self._months = ClientGUICommon.BetterSpinBox( self, max = 1000 )
        self._days = ClientGUICommon.BetterSpinBox( self, max = 1000 )
        self._hours = ClientGUICommon.BetterSpinBox( self, max = 10000 )
        
        #
        
        predicate = self._GetPredicateToInitialisePanelWith( predicate )
        
        ( sign, age_type, ( years, months, days, hours ) ) = predicate.GetValue()
        
        self._sign.SetValue( sign )
        
        self._years.setValue( years )
        self._months.setValue( months )
        self._days.setValue( days )
        self._hours.setValue( hours )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:archived time'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._years, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'years'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._months, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'months'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._days, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'days'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._hours, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'hours ago'), CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 0 )
        
        self.setLayout( hbox )
        
    
    def GetDefaultPredicate( self ):
        
        return ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_ARCHIVED_TIME, ( '<', 'delta', ( 0, 0, 7, 0 ) ) )
        
    
    def GetPredicates( self ):
        
        predicates = ( ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_ARCHIVED_TIME, ( self._sign.GetValue(), 'delta', ( self._years.value(), self._months.value(), self._days.value(), self._hours.value() ) ) ), )
        
        return predicates
        
    

class PanelPredicateSystemModifiedDelta( PanelPredicateSystemSingle ):
    
    def __init__( self, parent, predicate ):
        
        super().__init__( parent )
        
        self._sign = TimeDeltaOperator( self )
        
        self._years = ClientGUICommon.BetterSpinBox( self, max = 50000 )
        self._months = ClientGUICommon.BetterSpinBox( self, max = 1000 )
        self._days = ClientGUICommon.BetterSpinBox( self, max = 1000 )
        self._hours = ClientGUICommon.BetterSpinBox( self, max = 10000 )
        
        #
        
        predicate = self._GetPredicateToInitialisePanelWith( predicate )
        
        ( sign, age_type, ( years, months, days, hours ) ) = predicate.GetValue()
        
        self._sign.SetValue( sign )
        
        self._years.setValue( years )
        self._months.setValue( months )
        self._days.setValue( days )
        self._hours.setValue( hours )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:modified time'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._years, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'years'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._months, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'months'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._days, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'days'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._hours, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'hours ago'), CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 0 )
        
        self.setLayout( hbox )
        
    
    def GetDefaultPredicate( self ):
        
        return ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MODIFIED_TIME, ( '<', 'delta', ( 0, 0, 7, 0 ) ) )
        
    
    def GetPredicates( self ):
        
        predicates = ( ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MODIFIED_TIME, ( self._sign.GetValue(), 'delta', ( self._years.value(), self._months.value(), self._days.value(), self._hours.value() ) ) ), )
        
        return predicates
        
    
class PanelPredicateSystemDuplicateRelationships( PanelPredicateSystemSingle ):
    
    def __init__( self, parent, predicate ):
        
        super().__init__( parent )
        
        choices = [ '<', HC.UNICODE_APPROX_EQUAL, '=', '>' ]
        
        self._sign = ClientGUICommon.BetterRadioBox( self, [ ( c, c ) for c in choices ] )
        
        self._num = ClientGUICommon.BetterSpinBox( self, min=0, max=65535 )
        
        choice_tuples = [ ( HC.duplicate_type_string_lookup[ status ], status ) for status in ( HC.DUPLICATE_MEMBER, HC.DUPLICATE_ALTERNATE, HC.DUPLICATE_FALSE_POSITIVE, HC.DUPLICATE_POTENTIAL ) ]
        
        self._dupe_type = ClientGUICommon.BetterRadioBox( self, choice_tuples, vertical = True )
        
        #
        
        predicate = self._GetPredicateToInitialisePanelWith( predicate )
        
        ( sign, num, dupe_type ) = predicate.GetValue()
        
        self._sign.SetValue( sign )
        self._num.setValue( num )
        self._dupe_type.SetValue( dupe_type )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:num file relationships'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._num, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._dupe_type, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 0 )
        
        self.setLayout( hbox )
        
        self.setFocusProxy( self._sign )
        
    
    def GetDefaultPredicate( self ):
        
        sign = '>'
        num = 0
        dupe_type = HC.DUPLICATE_MEMBER
        
        return ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_FILE_RELATIONSHIPS_COUNT, ( sign, num, dupe_type ) )
        
    
    def GetPredicates( self ):
        
        predicates = ( ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_FILE_RELATIONSHIPS_COUNT, ( self._sign.GetValue(), self._num.value(), self._dupe_type.GetValue() ) ), )
        
        return predicates
        
    
class PanelPredicateSystemDuration( PanelPredicateSystemSingle ):
    
    def __init__( self, parent, predicate ):
        
        super().__init__( parent )
        
        allowed_operators = [
            ClientNumberTest.NUMBER_TEST_OPERATOR_LESS_THAN,
            ClientNumberTest.NUMBER_TEST_OPERATOR_LESS_THAN_OR_EQUAL_TO,
            ClientNumberTest.NUMBER_TEST_OPERATOR_APPROXIMATE_ABSOLUTE,
            ClientNumberTest.NUMBER_TEST_OPERATOR_APPROXIMATE_PERCENT,
            ClientNumberTest.NUMBER_TEST_OPERATOR_EQUAL,
            ClientNumberTest.NUMBER_TEST_OPERATOR_NOT_EQUAL,
            ClientNumberTest.NUMBER_TEST_OPERATOR_GREATER_THAN,
            ClientNumberTest.NUMBER_TEST_OPERATOR_GREATER_THAN_OR_EQUAL_TO
        ]
        
        self._number_test = ClientGUITime.NumberTestWidgetDuration( self, allowed_operators = allowed_operators, appropriate_absolute_plus_or_minus_default = 30000, appropriate_percentage_plus_or_minus_default = 5 )
        
        #
        
        predicate = self._GetPredicateToInitialisePanelWith( predicate )
        
        number_test = predicate.GetValue()
        
        self._number_test.SetValue( number_test )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:duration'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._number_test, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 0 )
        
        self.setLayout( hbox )
        
        self.setFocusProxy( self._number_test )
        
    
    def GetDefaultPredicate( self ):
        
        number_test = ClientNumberTest.NumberTest( operator = ClientNumberTest.NUMBER_TEST_OPERATOR_GREATER_THAN, value = 0 )
        
        return ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_DURATION, number_test )
        
    
    def GetPredicates( self ):
        
        number_test = self._number_test.GetValue()
        
        predicates = ( ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_DURATION, number_test ), )
        
        return predicates
        
    

class PanelPredicateSystemFileService( PanelPredicateSystemSingle ):
    
    def __init__( self, parent, predicate ):
        
        super().__init__( parent )
        
        self._sign = ClientGUICommon.BetterRadioBox( self, [ ( 'is', True ), ( 'is not', False ) ], vertical = True )
        
        choice_tuples = [
            ( 'currently in', HC.CONTENT_STATUS_CURRENT ),
            ( 'deleted from', HC.CONTENT_STATUS_DELETED ),
            ( 'pending to', HC.CONTENT_STATUS_PENDING ),
            ( 'petitioned from', HC.CONTENT_STATUS_PETITIONED )
        ]
        
        self._status = ClientGUICommon.BetterRadioBox( self, choice_tuples, vertical = True )
        
        services = CG.client_controller.services_manager.GetServices( HC.REAL_FILE_SERVICES )
        
        choice_tuples = [ ( service.GetName(), service.GetServiceKey() ) for service in services ]
        
        self._file_service_key = ClientGUICommon.BetterRadioBox( self, choice_tuples, vertical = True )
        
        #
        
        predicate = self._GetPredicateToInitialisePanelWith( predicate )
        
        ( sign, current_pending, file_service_key ) = predicate.GetValue()
        
        self._sign.SetValue( sign )
        self._status.SetValue( current_pending )
        self._file_service_key.SetValue( file_service_key )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:file service:'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._status, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._file_service_key, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 0 )
        
        self.setLayout( hbox )
        
        self.setFocusProxy( self._sign )
        
    
    def GetDefaultPredicate( self ):
        
        sign = True
        status = HC.CONTENT_STATUS_CURRENT
        file_service_key = bytes()
        
        return ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_FILE_SERVICE, ( sign, status, file_service_key ) )
        
    
    def GetPredicates( self ):
        
        predicates = ( ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_FILE_SERVICE, ( self._sign.GetValue(), self._status.GetValue(), self._file_service_key.GetValue() ) ), )
        
        return predicates
        
    
class PanelPredicateSystemFileViewingStatsViews( PanelPredicateSystemSingle ):
    
    def __init__( self, parent, predicate ):
        
        super().__init__( parent )
        
        self._viewing_locations = ClientGUICommon.BetterCheckBoxList( self )
        
        self._viewing_locations.Append( 'media views', 'media' )
        self._viewing_locations.Append( 'preview views', 'preview' )
        self._viewing_locations.Append( 'client api views', 'client api' )
        
        choices = ['<',HC.UNICODE_APPROX_EQUAL,'=','>']
        
        self._sign = ClientGUICommon.BetterRadioBox( self, [ ( c, c ) for c in choices ] )
        
        self._num = ClientGUICommon.BetterSpinBox( self, min=0, max=1000000 )
        
        #
        
        predicate = self._GetPredicateToInitialisePanelWith( predicate )
        
        ( view_type, viewing_locations, sign, num ) = predicate.GetValue()
        
        self._viewing_locations.SetValue( viewing_locations )
        
        self._viewing_locations.SetHeightBasedOnContents()
        
        self._sign.SetValue( sign )
        
        self._num.setValue( num )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._viewing_locations, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._num, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 0 )
        
        self.setLayout( hbox )
        
        self.setFocusProxy( self._sign )
        
    
    def GetDefaultPredicate( self ):
        
        viewing_locations = ( 'media', )
        sign = '>'
        num = 10
        
        return ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_FILE_VIEWING_STATS, ( 'views', tuple( viewing_locations ), sign, num ) )
        
    
    def GetPredicates( self ):
        
        viewing_locations = self._viewing_locations.GetValue()
        
        if len( viewing_locations ) == 0:
            
            viewing_locations = [ 'media' ]
            
        
        sign = self._sign.GetValue()
        
        num = self._num.value()
        
        predicates = ( ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_FILE_VIEWING_STATS, ( 'views', tuple( viewing_locations ), sign, num ) ), )
        
        return predicates
        
    
class PanelPredicateSystemFileViewingStatsViewtime( PanelPredicateSystemSingle ):
    
    def __init__( self, parent, predicate ):
        
        super().__init__( parent )
        
        self._viewing_locations = ClientGUICommon.BetterCheckBoxList( self )
        
        self._viewing_locations.Append( 'media viewtime', 'media' )
        self._viewing_locations.Append( 'preview viewtime', 'preview' )
        self._viewing_locations.Append( 'client api viewtime', 'client api' )
        
        choices = ['<',HC.UNICODE_APPROX_EQUAL,'=','>']
        
        self._sign = ClientGUICommon.BetterRadioBox( self, [ ( c, c ) for c in choices ] )
        
        self._time_delta = ClientGUITime.TimeDeltaWidget( self, min = 0, days = True, hours = True, minutes = True, seconds = True, milliseconds = True )
        
        #
        
        predicate = self._GetPredicateToInitialisePanelWith( predicate )
        
        ( view_type, viewing_locations, sign, time_delta ) = predicate.GetValue()
        
        self._viewing_locations.SetValue( viewing_locations )
        
        self._viewing_locations.SetHeightBasedOnContents()
        
        self._sign.SetValue( sign )
        
        self._time_delta.SetValue( time_delta )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._viewing_locations, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._time_delta, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 0 )
        
        self.setLayout( hbox )
        
        self.setFocusProxy( self._sign )
        
    
    def GetDefaultPredicate( self ):
        
        viewing_locations = ( 'media', )
        sign = '>'
        time_delta = 600.0
        
        return ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_FILE_VIEWING_STATS, ( 'viewtime', tuple( viewing_locations ), sign, time_delta ) )
        
    
    def GetPredicates( self ):
        
        viewing_locations = self._viewing_locations.GetValue()
        
        if len( viewing_locations ) == 0:
            
            viewing_locations = [ 'media' ]
            
        
        sign = self._sign.GetValue()
        
        time_delta = self._time_delta.GetValue()
        
        predicates = ( ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_FILE_VIEWING_STATS, ( 'viewtime', tuple( viewing_locations ), sign, time_delta ) ), )
        
        return predicates
        
    
class PanelPredicateSystemFramerate( PanelPredicateSystemSingle ):
    
    def __init__( self, parent, predicate ):
        
        super().__init__( parent )
        
        allowed_operators = [
            ClientNumberTest.NUMBER_TEST_OPERATOR_LESS_THAN,
            ClientNumberTest.NUMBER_TEST_OPERATOR_APPROXIMATE_ABSOLUTE,
            ClientNumberTest.NUMBER_TEST_OPERATOR_APPROXIMATE_PERCENT,
            ClientNumberTest.NUMBER_TEST_OPERATOR_GREATER_THAN
        ]
        
        self._number_test = ClientGUINumberTest.NumberTestWidget( self, allowed_operators = allowed_operators, max = 1000000, unit_string = 'fps', appropriate_absolute_plus_or_minus_default = 1, appropriate_percentage_plus_or_minus_default = 5 )
        
        #
        
        predicate = self._GetPredicateToInitialisePanelWith( predicate )
        
        number_test = predicate.GetValue()
        
        self._number_test.SetValue( number_test )
        
        #
        
        vbox = QP.VBoxLayout()
        
        label = 'Framerate is approximate. A "30fps" file may actually be 30.005fps internally.\nIf you use < or >, include some padding: "> 59", not "> 60".'
        
        st = ClientGUICommon.BetterStaticText( self, label = label )
        st.setWordWrap( True )
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText( self, 'system:framerate' ), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._number_test, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 0 )
        
        QP.AddToLayout( vbox, hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.setLayout( vbox )
        
        self.setFocusProxy( self._number_test )
        
    
    def GetDefaultPredicate( self ):
        
        number_test = ClientNumberTest.NumberTest( operator = ClientNumberTest.NUMBER_TEST_OPERATOR_APPROXIMATE_PERCENT, value = 60, extra_value = 0.05 )
        
        return ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_FRAMERATE, number_test )
        
    
    def GetPredicates( self ):
        
        number_test = self._number_test.GetValue()
        
        predicates = ( ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_FRAMERATE, number_test ), )
        
        return predicates
        
    

class PanelPredicateSystemHash( PanelPredicateSystemSingle ):
    
    def __init__( self, parent, predicate ):
        
        super().__init__( parent )
        
        self._sign = ClientGUICommon.BetterRadioBox( self, [ ( 'is', True ), ( 'is not', False ) ], vertical = True )
        
        choices = [ 'sha256', 'md5', 'sha1', 'sha512' ]
        
        self._hash_type = ClientGUICommon.BetterRadioBox( self, [ ( c, c ) for c in choices ], vertical = True )
        
        self._hashes = QW.QPlainTextEdit( self )
        
        self._hashes.setPlaceholderText( 'enter hash (paste newline-separated for multiple hashes)' )
        
        ( init_width, init_height ) = ClientGUIFunctions.ConvertTextToPixels( self._hashes, ( 66, 10 ) )
        
        self._hashes.setMinimumSize( QC.QSize( init_width, init_height ) )
        
        #
        
        predicate = self._GetPredicateToInitialisePanelWith( predicate )
        
        ( hashes, hash_type ) = predicate.GetValue()
        
        self._sign.SetValue( predicate.IsInclusive() )
        
        hashes_text = '\n'.join( [ hash.hex() for hash in hashes ] )
        
        self._hashes.setPlainText( hashes_text )
        
        self._hash_type.SetValue( hash_type )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:hash'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._hashes, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, self._hash_type, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 0 )
        
        self.setLayout( hbox )
        
        self.setFocusProxy( self._sign )
        
        self._hashes.textChanged.connect( self._StripOffPrefixes )
        
    
    def _StripOffPrefixes( self ):
        
        # it would be nice to generalise this into a 'hashes' widget that had the hash type and provided an ongoing (red text) commentary into the validity of the hashes entered
        
        hashes_text = self._hashes.toPlainText()
        
        hashes_lines = HydrusText.DeserialiseNewlinedTexts( hashes_text )
        
        seen_prefixes = set()
        stripped_hashes = []
        
        we_split_some = False
        
        for line in hashes_lines:
            
            if ':' in line:
                
                ( prefix, hash ) = line.split( ':', 1 )
                
                if prefix in [ 'sha256', 'md5', 'sha1', 'sha512' ]:
                    
                    seen_prefixes.add( prefix )
                    
                    if len( seen_prefixes ) == 2:
                        
                        return
                        
                    
                else:
                    
                    return
                    
                
                stripped_hashes.append( hash )
                
                we_split_some = True
                
            
        
        if we_split_some and len( seen_prefixes ) == 1:
            
            self._hashes.setPlainText( '\n'.join( stripped_hashes ) )
            
            if len( seen_prefixes ) == 1:
                
                prefix = list( seen_prefixes )[0]
                
                if prefix in [ 'sha256', 'md5', 'sha1', 'sha512' ]:
                    
                    self._hash_type.SetValue( prefix )
                    
                
            
        
    
    def GetDefaultPredicate( self ):
        
        hashes = tuple()
        hash_type = 'sha256'
        
        return ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HASH, ( hashes, hash_type ) )
        
    
    def GetPredicates( self ):
        
        inclusive = self._sign.GetValue()
        
        hash_type = self._hash_type.GetValue()
        
        hex_hashes_raw = self._hashes.toPlainText()
        
        hashes = ClientParsing.ParseHashesFromRawHexText( hash_type, hex_hashes_raw )
        
        predicates = ( ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HASH, ( hashes, hash_type ), inclusive = inclusive ), )
        
        return predicates
        
    

class PanelPredicateSystemHasNoteName( PanelPredicateSystemSingle ):
    
    def __init__( self, parent, predicate ):
        
        super().__init__( parent )
        
        self._operator = ClientGUICommon.BetterChoice( self )
        
        self._operator.addItem( 'has note with name ', True )
        self._operator.addItem( 'does not have note with name', False )
        
        self._name = QW.QLineEdit( self )
        
        #
        
        predicate = self._GetPredicateToInitialisePanelWith( predicate )
        
        ( operator, name ) = predicate.GetValue()
        
        self._operator.SetValue( operator )
        self._name.setText( name )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:note name'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._operator, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._name, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 0 )
        
        self.setLayout( hbox )
        
        self.setFocusProxy( self._operator )
        
    
    def GetDefaultPredicate( self ):
        
        operator = True
        name = ''
        
        return ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HAS_NOTE_NAME, ( operator, name ) )
        
    
    def GetPredicates( self ):
        
        name = self._name.text()
        
        if name == '':
            
            name = 'notes'
            
        
        predicates = ( ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HAS_NOTE_NAME, ( self._operator.GetValue(), name ) ), )
        
        return predicates
        
    
class PanelPredicateSystemHeight( PanelPredicateSystemSingle ):
    
    def __init__( self, parent, predicate ):
        
        super().__init__( parent )
        
        allowed_operators = [
            ClientNumberTest.NUMBER_TEST_OPERATOR_LESS_THAN,
            ClientNumberTest.NUMBER_TEST_OPERATOR_LESS_THAN_OR_EQUAL_TO,
            ClientNumberTest.NUMBER_TEST_OPERATOR_APPROXIMATE_ABSOLUTE,
            ClientNumberTest.NUMBER_TEST_OPERATOR_APPROXIMATE_PERCENT,
            ClientNumberTest.NUMBER_TEST_OPERATOR_EQUAL,
            ClientNumberTest.NUMBER_TEST_OPERATOR_NOT_EQUAL,
            ClientNumberTest.NUMBER_TEST_OPERATOR_GREATER_THAN,
            ClientNumberTest.NUMBER_TEST_OPERATOR_GREATER_THAN_OR_EQUAL_TO
        ]
        
        self._number_test = ClientGUINumberTest.NumberTestWidget( self, allowed_operators = allowed_operators, unit_string = 'px', appropriate_absolute_plus_or_minus_default = 200 )
        
        #
        
        predicate = self._GetPredicateToInitialisePanelWith( predicate )
        
        number_test = predicate.GetValue()
        
        self._number_test.SetValue( number_test )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:height'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._number_test, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 0 )
        
        self.setLayout( hbox )
        
        self.setFocusProxy( self._number_test )
        
    
    def GetDefaultPredicate( self ):
        
        number_test = ClientNumberTest.NumberTest( operator = ClientNumberTest.NUMBER_TEST_OPERATOR_EQUAL, value = 1080 )
        
        return ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HEIGHT, number_test )
        
    
    def GetPredicates( self ):
        
        number_test = self._number_test.GetValue()
        
        predicates = ( ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HEIGHT, number_test ), )
        
        return predicates
        
    
class PanelPredicateSystemKnownURLsExactURL( PanelPredicateSystemSingle ):
    
    def __init__( self, parent, predicate ):
        
        super().__init__( parent )
        
        self._operator = ClientGUICommon.BetterChoice( self )
        
        self._operator.addItem( 'has', True )
        self._operator.addItem( 'does not have', False )
        
        self._exact_url = QW.QLineEdit( self )
        
        #
        
        predicate = self._GetPredicateToInitialisePanelWith( predicate )
        
        ( operator, rule_type, rule, description ) = predicate.GetValue()
        
        self._operator.SetValue( operator )
        self._exact_url.setText( rule )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._operator, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,' url '), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._exact_url, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.setLayout( hbox )
        
        self.setFocusProxy( self._operator )
        
    
    def GetDefaultPredicate( self ):
        
        operator = True
        rule_type = 'exact_match'
        rule = ''
        description = ''
        
        return ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_KNOWN_URLS, ( operator, rule_type, rule, description ) )
        
    
    def GetPredicates( self ):
        
        operator = self._operator.GetValue()
        
        if operator:
            
            operator_description = 'has url '
            
        else:
            
            operator_description = 'does not have url '
            
        
        rule_type = 'exact_match'
        
        exact_url = self._exact_url.text()
        
        rule = exact_url
        
        description = operator_description + exact_url
        
        predicates = ( ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_KNOWN_URLS, ( operator, rule_type, rule, description ) ), )
        
        return predicates
        
    
class PanelPredicateSystemKnownURLsDomain( PanelPredicateSystemSingle ):
    
    def __init__( self, parent, predicate ):
        
        super().__init__( parent )
        
        self._operator = ClientGUICommon.BetterChoice( self )
        
        self._operator.addItem( 'has', True )
        self._operator.addItem( 'does not have', False )
        
        self._domain = QW.QLineEdit( self )
        
        self._domain.setPlaceholderText( 'example.com' )
        
        #
        
        predicate = self._GetPredicateToInitialisePanelWith( predicate )
        
        ( operator, rule_type, rule, description ) = predicate.GetValue()
        
        self._operator.SetValue( operator )
        self._domain.setText( rule )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._operator, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,' url with domain '), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._domain, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.setLayout( hbox )
        
        self.setFocusProxy( self._operator )
        
    
    def GetDefaultPredicate( self ):
        
        operator = True
        rule_type = 'domain'
        rule = ''
        description = ''
        
        return ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_KNOWN_URLS, ( operator, rule_type, rule, description ) )
        
    
    def GetPredicates( self ):
        
        operator = self._operator.GetValue()
        
        if operator:
            
            operator_description = 'has url with domain '
            
        else:
            
            operator_description = 'does not have url with domain '
            
        
        rule_type = 'domain'
        
        domain = self._domain.text()
        
        rule = domain
        
        description = operator_description + domain
        
        predicates = ( ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_KNOWN_URLS, ( operator, rule_type, rule, description ) ), )
        
        return predicates
        
    
class PanelPredicateSystemKnownURLsRegex( PanelPredicateSystemSingle ):
    
    def __init__( self, parent, predicate ):
        
        super().__init__( parent )
        
        self._operator = ClientGUICommon.BetterChoice( self )
        
        self._operator.addItem( 'has', True )
        self._operator.addItem( 'does not have', False )
        
        self._regex = ClientGUIRegex.RegexInput( self )
        
        #
        
        predicate = self._GetPredicateToInitialisePanelWith( predicate )
        
        ( operator, rule_type, rule, description ) = predicate.GetValue()
        
        self._operator.SetValue( operator )
        self._regex.SetValue( rule )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._operator, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,' url that matches regex '), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._regex, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.setLayout( hbox )
        
        self.setFocusProxy( self._operator )
        
    
    def GetDefaultPredicate( self ):
        
        operator = True
        rule_type = 'regex'
        rule = ''
        description = ''
        
        return ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_KNOWN_URLS, ( operator, rule_type, rule, description ) )
        
    
    def CheckValid( self ):
        
        regex = self._regex.GetValue()
        
        try:
            
            re.compile( regex )
            
        except Exception as e:
            
            raise HydrusExceptions.VetoException( 'Cannot compile that regex: {}'.format( e ) )
            
        
    
    def GetPredicates( self ):
        
        operator = self._operator.GetValue()
        
        if operator:
            
            operator_description = 'has url matching regex '
            
        else:
            
            operator_description = 'does not have url matching regex '
            
        
        rule_type = 'regex'
        
        regex = self._regex.GetValue()
        
        rule = regex
        
        description = operator_description + regex
        
        predicates = ( ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_KNOWN_URLS, ( operator, rule_type, rule, description ) ), )
        
        return predicates
        
    
class PanelPredicateSystemKnownURLsURLClass( PanelPredicateSystemSingle ):
    
    def __init__( self, parent, predicate ):
        
        super().__init__( parent )
        
        self._operator = ClientGUICommon.BetterChoice( self )
        
        self._operator.addItem( 'has', True )
        self._operator.addItem( 'does not have', False )
        
        self._url_classes = ClientGUICommon.BetterChoice( self )
        
        for url_class in CG.client_controller.network_engine.domain_manager.GetURLClasses():
            
            if url_class.ShouldAssociateWithFiles():
                
                self._url_classes.addItem( url_class.GetName(), url_class )
                
            
        
        #
        
        predicate = self._GetPredicateToInitialisePanelWith( predicate )
        
        ( operator, rule_type, rule, description ) = predicate.GetValue()
        
        self._operator.SetValue( operator )
        self._url_classes.SetValue( rule )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._operator, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,' url matching class '), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._url_classes, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.setLayout( hbox )
        
        self.setFocusProxy( self._operator )
        
    
    def GetDefaultPredicate( self ):
        
        from hydrus.client.networking import ClientNetworkingURLClass
        
        operator = True
        rule_type = 'url_class'
        rule = ClientNetworkingURLClass.URLClass(
            name = 'safebooru post url'
        )
        description = ''
        
        return ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_KNOWN_URLS, ( operator, rule_type, rule, description ) )
        
    
    def GetPredicates( self ):
        
        operator = self._operator.GetValue()
        
        rule_type = 'url_class'
        
        url_class = self._url_classes.GetValue()
        
        rule = url_class
        
        url_class_name = url_class.GetName()
        
        description = f'has url with class {url_class_name}' if operator else f'does not have url with class {url_class_name}'
        
        predicates = ( ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_KNOWN_URLS, ( operator, rule_type, rule, description ) ), )
        
        return predicates
        
    
class PanelPredicateSystemLimit( PanelPredicateSystemSingle ):
    
    def __init__( self, parent, predicate ):
        
        super().__init__( parent )
        
        self._limit = ClientGUICommon.BetterSpinBox( self, min = 1, max=1000000, width = 60 )
        
        #
        
        predicate = self._GetPredicateToInitialisePanelWith( predicate )
        
        limit = predicate.GetValue()
        
        self._limit.setValue( limit )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:limit='), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._limit, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 0 )
        
        self.setLayout( hbox )
        
        self.setFocusProxy( self._limit )
        
    
    def GetDefaultPredicate( self ):
        
        limit = 256
        
        return ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_LIMIT, limit )
        
    
    def GetPredicates( self ):
        
        predicates = ( ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_LIMIT, self._limit.value() ), )
        
        return predicates
        
    
class PanelPredicateSystemMime( PanelPredicateSystemSingle ):
    
    def __init__( self, parent, predicate ):
        
        super().__init__( parent )
        
        self._mimes = ClientGUIOptionsPanels.OptionsPanelMimesTree( self, HC.SEARCHABLE_MIMES )
        
        #
        
        predicate = self._GetPredicateToInitialisePanelWith( predicate )
        
        choice_tuples = [
            ( 'is', True ),
            ( 'is not', False )
        ]
        
        self._inclusive = ClientGUICommon.BetterRadioBox( self, choice_tuples, vertical = True )
        
        summary_mimes = predicate.GetValue()
        
        if isinstance( summary_mimes, int ):
            
            summary_mimes = ( summary_mimes, )
            
        
        specific_mimes = ClientSearchPredicate.ConvertSummaryFiletypesToSpecific( summary_mimes )
        
        self._mimes.SetValue( specific_mimes )
        
        self._inclusive.SetValue( predicate.IsInclusive() )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText( self, 'system:filetype' ), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._inclusive, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._mimes, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.setLayout( hbox )
        
        self.setFocusProxy( self._mimes )
        
    
    def GetDefaultPredicate( self ):
        
        specific_mimes = tuple()
        
        return ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MIME, specific_mimes )
        
    
    def GetPredicates( self ):
        
        specific_mimes = self._mimes.GetValue()
        
        predicates = ( ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MIME, specific_mimes, inclusive = self._inclusive.GetValue() ), )
        
        return predicates
        
    
class PanelPredicateSystemNumPixels( PanelPredicateSystemSingle ):
    
    def __init__( self, parent, predicate ):
        
        super().__init__( parent )
        
        choices = [ '<', HC.UNICODE_APPROX_EQUAL, '=', HC.UNICODE_NOT_EQUAL, '>' ]
        
        self._sign = ClientGUICommon.BetterRadioBox( self, [ ( c, c ) for c in choices ] )
        
        self._num_pixels = ClientGUICommon.BetterSpinBox( self, max=1048576, width = 60 )
        
        choice_tuples = [ ( 'pixels', 1 ), ( 'kilopixels', 1000 ), ( 'megapixels', 1000000 ) ]
        
        self._unit = ClientGUICommon.BetterRadioBox( self, choice_tuples )
        
        #
        
        predicate = self._GetPredicateToInitialisePanelWith( predicate )
        
        ( sign, num_pixels, unit ) = predicate.GetValue()
        
        self._sign.SetValue( sign )
        
        self._num_pixels.setValue( num_pixels )
        
        self._unit.SetValue( unit )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:number of pixels'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._num_pixels, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._unit, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 0 )
        
        self.setLayout( hbox )
        
        self.setFocusProxy( self._sign )
        
    
    def GetDefaultPredicate( self ):
        
        sign = HC.UNICODE_APPROX_EQUAL
        num_pixels = 2
        unit = 1000000
        
        return ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_PIXELS, ( sign, num_pixels, unit ) )
        
    
    def GetPredicates( self ):
        
        predicates = ( ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_PIXELS, ( self._sign.GetValue(), self._num_pixels.value(), self._unit.GetValue() ) ), )
        
        return predicates
        
    
class PanelPredicateSystemNumFrames( PanelPredicateSystemSingle ):
    
    def __init__( self, parent, predicate ):
        
        super().__init__( parent )
        
        allowed_operators = [
            ClientNumberTest.NUMBER_TEST_OPERATOR_LESS_THAN,
            ClientNumberTest.NUMBER_TEST_OPERATOR_LESS_THAN_OR_EQUAL_TO,
            ClientNumberTest.NUMBER_TEST_OPERATOR_APPROXIMATE_ABSOLUTE,
            ClientNumberTest.NUMBER_TEST_OPERATOR_APPROXIMATE_PERCENT,
            ClientNumberTest.NUMBER_TEST_OPERATOR_EQUAL,
            ClientNumberTest.NUMBER_TEST_OPERATOR_NOT_EQUAL,
            ClientNumberTest.NUMBER_TEST_OPERATOR_GREATER_THAN,
            ClientNumberTest.NUMBER_TEST_OPERATOR_GREATER_THAN_OR_EQUAL_TO
        ]
        
        self._number_test = ClientGUINumberTest.NumberTestWidget( self, allowed_operators = allowed_operators, max = 1000000, appropriate_absolute_plus_or_minus_default = 300 )
        
        #
        
        predicate = self._GetPredicateToInitialisePanelWith( predicate )
        
        number_test = predicate.GetValue()
        
        self._number_test.SetValue( number_test )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText( self, 'system:number of frames' ), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._number_test, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 0 )
        
        self.setLayout( hbox )
        
        self.setFocusProxy( self._number_test )
        
    
    def GetDefaultPredicate( self ):
        
        number_test = ClientNumberTest.NumberTest( operator = ClientNumberTest.NUMBER_TEST_OPERATOR_GREATER_THAN, value = 600 )
        
        return ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_FRAMES, number_test )
        
    
    def GetPredicates( self ):
        
        number_test = self._number_test.GetValue()
        
        predicates = ( ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_FRAMES, number_test ), )
        
        return predicates
        
    
class PanelPredicateSystemNumTags( PanelPredicateSystemSingle ):
    
    def __init__( self, parent, predicate ):
        
        super().__init__( parent )
        
        self._namespace = ClientGUICommon.NamespaceWidget( self )
        
        choices = ['<',HC.UNICODE_APPROX_EQUAL,'=','>']
        
        self._sign = ClientGUICommon.BetterRadioBox( self, [ ( c, c ) for c in choices ] )
        
        self._num_tags = ClientGUICommon.BetterSpinBox( self, max=2000, width = 60 )
        
        #
        
        predicate = self._GetPredicateToInitialisePanelWith( predicate )
        
        ( namespace, sign, num_tags ) = predicate.GetValue()
        
        if namespace is None:
            
            namespace = '*'
            
        
        self._namespace.SetValue( namespace )
        
        self._sign.SetValue( sign )
        
        self._num_tags.setValue( num_tags )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:number of tags: namespace:'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._namespace, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._num_tags, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 0 )
        
        self.setLayout( hbox )
        
        self.setFocusProxy( self._sign )
        
    
    def GetDefaultPredicate( self ):
        
        namespace = '*'
        sign = '>'
        num_tags = 4
        
        return ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( namespace, sign, num_tags ) )
        
    
    def GetPredicates( self ):
        
        ( namespace, operator, value ) = ( self._namespace.GetValue(), self._sign.GetValue(), self._num_tags.value() )
        
        predicate = None
        
        # swap num character tags > 0 with character:*anything*
        if namespace != '*':
            
            number_test = ClientNumberTest.NumberTest.STATICCreateFromCharacters( operator, value )
            
            if number_test.IsZero():
                
                predicate = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_NAMESPACE, namespace, inclusive = False )
                
            elif number_test.IsAnythingButZero():
                
                predicate = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_NAMESPACE, namespace )
                
            
        
        if predicate is None:
            
            predicate = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( namespace, operator, value ) )
            
        
        predicates = ( predicate, )
        
        return predicates
        
    

class PanelPredicateSystemNumNotes( PanelPredicateSystemSingle ):
    
    def __init__( self, parent, predicate ):
        
        super().__init__( parent )
        
        allowed_operators = [
            ClientNumberTest.NUMBER_TEST_OPERATOR_LESS_THAN,
            ClientNumberTest.NUMBER_TEST_OPERATOR_LESS_THAN_OR_EQUAL_TO,
            ClientNumberTest.NUMBER_TEST_OPERATOR_EQUAL,
            ClientNumberTest.NUMBER_TEST_OPERATOR_NOT_EQUAL,
            ClientNumberTest.NUMBER_TEST_OPERATOR_GREATER_THAN,
            ClientNumberTest.NUMBER_TEST_OPERATOR_GREATER_THAN_OR_EQUAL_TO
        ]
        
        self._number_test = ClientGUINumberTest.NumberTestWidget( self, allowed_operators = allowed_operators )
        
        #
        
        predicate = self._GetPredicateToInitialisePanelWith( predicate )
        
        number_test = predicate.GetValue()
        
        self._number_test.SetValue( number_test )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText( self,'system:number of notes' ), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._number_test, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 0 )
        
        self.setLayout( hbox )
        
        self.setFocusProxy( self._number_test )
        
    
    def GetDefaultPredicate( self ):
        
        number_test = ClientNumberTest.NumberTest( operator = ClientNumberTest.NUMBER_TEST_OPERATOR_EQUAL, value = 2 )
        
        return ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_NOTES, number_test )
        
    
    def GetPredicates( self ):
        
        number_test = self._number_test.GetValue()
        
        predicates = ( ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_NOTES, number_test ), )
        
        return predicates
        
    

class PanelPredicateSystemNumURLs( PanelPredicateSystemSingle ):
    
    def __init__( self, parent, predicate ):
        
        super().__init__( parent )
        
        allowed_operators = [
            ClientNumberTest.NUMBER_TEST_OPERATOR_LESS_THAN,
            ClientNumberTest.NUMBER_TEST_OPERATOR_LESS_THAN_OR_EQUAL_TO,
            ClientNumberTest.NUMBER_TEST_OPERATOR_EQUAL,
            ClientNumberTest.NUMBER_TEST_OPERATOR_NOT_EQUAL,
            ClientNumberTest.NUMBER_TEST_OPERATOR_GREATER_THAN,
            ClientNumberTest.NUMBER_TEST_OPERATOR_GREATER_THAN_OR_EQUAL_TO
        ]
        
        self._number_test = ClientGUINumberTest.NumberTestWidget( self, allowed_operators = allowed_operators )
        
        #
        
        predicate = self._GetPredicateToInitialisePanelWith( predicate )
        
        number_test = predicate.GetValue()
        
        self._number_test.SetValue( number_test )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText( self,'system:number of urls' ), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._number_test, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 0 )
        
        self.setLayout( hbox )
        
        self.setFocusProxy( self._number_test )
        
    
    def GetDefaultPredicate( self ):
        
        number_test = ClientNumberTest.NumberTest( operator = ClientNumberTest.NUMBER_TEST_OPERATOR_GREATER_THAN, value = 0 )
        
        return ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_URLS, number_test )
        
    
    def GetPredicates( self ):
        
        number_test = self._number_test.GetValue()
        
        predicates = ( ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_URLS, number_test ), )
        
        return predicates
        
    

class PanelPredicateSystemNumWords( PanelPredicateSystemSingle ):
    
    def __init__( self, parent, predicate ):
        
        super().__init__( parent )
        
        allowed_operators = [
            ClientNumberTest.NUMBER_TEST_OPERATOR_LESS_THAN,
            ClientNumberTest.NUMBER_TEST_OPERATOR_LESS_THAN_OR_EQUAL_TO,
            ClientNumberTest.NUMBER_TEST_OPERATOR_APPROXIMATE_ABSOLUTE,
            ClientNumberTest.NUMBER_TEST_OPERATOR_APPROXIMATE_PERCENT,
            ClientNumberTest.NUMBER_TEST_OPERATOR_EQUAL,
            ClientNumberTest.NUMBER_TEST_OPERATOR_NOT_EQUAL,
            ClientNumberTest.NUMBER_TEST_OPERATOR_GREATER_THAN,
            ClientNumberTest.NUMBER_TEST_OPERATOR_GREATER_THAN_OR_EQUAL_TO
        ]
        
        self._number_test = ClientGUINumberTest.NumberTestWidget( self, allowed_operators = allowed_operators, max = 100000000, appropriate_absolute_plus_or_minus_default = 5000 )
        
        #
        
        predicate = self._GetPredicateToInitialisePanelWith( predicate )
        
        number_test = predicate.GetValue()
        
        self._number_test.SetValue( number_test )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:number of words'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._number_test, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 0 )
        
        self.setLayout( hbox )
        
        self.setFocusProxy( self._number_test )
        
    
    def GetDefaultPredicate( self ):
        
        number_test = ClientNumberTest.NumberTest( operator = ClientNumberTest.NUMBER_TEST_OPERATOR_LESS_THAN, value = 30000 )
        
        return ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_WORDS, number_test )
        
    
    def GetPredicates( self ):
        
        number_test = self._number_test.GetValue()
        
        predicates = ( ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_WORDS, number_test ), )
        
        return predicates
        
    

class PredicateSystemRatingAdvanced( PanelPredicateSystemSingle ):
    
    def __init__( self, parent: QW.QWidget, predicate: ClientSearchPredicate.Predicate | None ):
        
        super().__init__( parent )
        
        predicate = self._GetPredicateToInitialisePanelWith( predicate )
        
        ( logical_operator, service_specifier_primary, service_specifier_secondary, rated ) = predicate.GetValue()
        
        choice_tuples = [
            ( 'all', HC.LOGICAL_OPERATOR_ALL ),
            ( 'any', HC.LOGICAL_OPERATOR_ANY ),
            ( 'only', HC.LOGICAL_OPERATOR_ONLY ),
        ]
        
        self._logical_choice = ClientGUICommon.BetterRadioBox( self, choice_tuples, vertical = True )
        tt = '"only" here means that all the ratings set on the left will be (rated/not rated) and all the remainder on the right will be (not rated/rated).\n\nUse it to do "find the files that are rated this way and no other way" without having to stack up two finicky competing "all x has/no rating" predicates.'
        self._logical_choice.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._service_specifier_primary = ClientGUIServiceSpecifier.ServiceSpecifierButton( self, service_specifier_primary, HC.LOCAL_RATINGS_SERVICES )
        
        self._secondary_panel = QW.QWidget( self )
        
        of_label = ClientGUICommon.BetterStaticText( self._secondary_panel, label = ' amongst ' )
        
        self._service_specifier_secondary = ClientGUIServiceSpecifier.ServiceSpecifierButton( self, service_specifier_secondary, HC.LOCAL_RATINGS_SERVICES )
        
        choice_tuples = [
            ( 'rated', True ),
            ( 'not rated', False ),
        ]
        
        self._rated_choice = ClientGUICommon.BetterRadioBox( self, choice_tuples, vertical = True )
        
        self._logical_choice.SetValue( logical_operator )
        self._rated_choice.SetValue( rated )
        
        #
        
        secondary_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( secondary_hbox, of_label, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( secondary_hbox, self._service_specifier_secondary, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self._secondary_panel.setLayout( secondary_hbox )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._logical_choice, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._service_specifier_primary, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, self._secondary_panel, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        QP.AddToLayout( hbox, self._rated_choice, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self.setLayout( hbox )
        
        self._logical_choice.radioBoxChanged.connect( self._UpdateControls )
        
        self._service_specifier_primary.valueChanged.connect( self._MakeSureSecondaryIsLargeEnough )
        self._service_specifier_secondary.valueChanged.connect( self._MakeSureSecondaryIsLargeEnough )
        
        self._UpdateControls()
        
    
    def _MakeSureSecondaryIsLargeEnough( self ):
        
        service_specifier_primary = self._service_specifier_primary.GetValue()
        service_specifier_secondary = self._service_specifier_secondary.GetValue()
        
        primary_keys = service_specifier_primary.GetSpecificKeys()
        secondary_keys = service_specifier_secondary.GetSpecificKeys()
        
        if not primary_keys.issubset( secondary_keys ):
            
            service_specifier_secondary = ClientServices.ServiceSpecifier( service_keys = secondary_keys.union( primary_keys ) )
            
            self._service_specifier_secondary.SetValue( service_specifier_secondary )
            
        
    
    def _UpdateControls( self ):
        
        self._secondary_panel.setVisible( self._logical_choice.GetValue() == HC.LOGICAL_OPERATOR_ONLY )
        
    
    def GetDefaultPredicate( self ):
        
        logical_operator = HC.LOGICAL_OPERATOR_ANY
        service_specifier_primary = ClientServices.ServiceSpecifier( service_types = set( HC.LOCAL_RATINGS_SERVICES ) )
        service_specifier_secondary = ClientServices.ServiceSpecifier( service_types = set( HC.LOCAL_RATINGS_SERVICES ) )
        rated = True
        
        return ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_RATING_ADVANCED, ( logical_operator, service_specifier_primary, service_specifier_secondary, rated ) )
        
    
    def GetPredicates( self ):
        
        logical_operator = self._logical_choice.GetValue()
        service_specifier_primary = self._service_specifier_primary.GetValue()
        service_specifier_secondary = self._service_specifier_secondary.GetValue()
        rated = self._rated_choice.GetValue()
        
        if logical_operator == HC.LOGICAL_OPERATOR_ONLY and service_specifier_primary == service_specifier_secondary:
            
            logical_operator = HC.LOGICAL_OPERATOR_ALL
            
        
        predicate = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_RATING_ADVANCED, ( logical_operator, service_specifier_primary, service_specifier_secondary, rated ) )
        
        return [ predicate ]
        
    

class PredicateSystemRatingIncDec( PanelPredicateSystemSingle ):
    
    def __init__( self, parent: QW.QWidget, service_key: bytes, predicate: ClientSearchPredicate.Predicate | None ):
        
        super().__init__( parent )
        
        self._service_key = service_key
        
        try:
            
            service = CG.client_controller.services_manager.GetService( self._service_key )
            
            name = service.GetName()
            
        except:
            
            name = 'unknown service'
            
        
        name_st = ClientGUICommon.BetterStaticText( self, name )
        
        name_st.setAlignment( QC.Qt.AlignmentFlag.AlignLeft | QC.Qt.AlignmentFlag.AlignVCenter )
        
        choice_tuples = [
            ( 'has count', 'has count' ),
            ( 'no count', 'no count' ),
            ( 'more than', '>' ),
            ( 'less than', '<' ),
            ( 'is', '=' ),
            ( 'is about', HC.UNICODE_APPROX_EQUAL )
        ]
        
        self._choice = ClientGUICommon.BetterRadioBox( self, choice_tuples, vertical = True )
        
        self._rating_value = ClientGUICommon.BetterSpinBox( self, initial = 0, min = 0, max = 1000000 )
        
        self._choice.SetValue( '' )
        
        #
        
        if predicate is not None:
            
            value = predicate.GetValue()
            
            if value is not None:
                
                ( operator, rating, service_key ) = value
                
                self._rating_value.setValue( 0 )
                
                if operator == '>' and rating == 0:
                    
                    self._choice.SetValue( 'has count' )
                    
                elif ( operator == '<' and rating == 1 ) or ( operator == '=' and rating == '0' ):
                    
                    self._choice.SetValue( 'no count' )
                    
                else:
                    
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
        
        spinctrl_matters = choice not in ( 'has count', 'no count' )
        
        self._rating_value.setEnabled( spinctrl_matters )
        
    
    def GetDefaultPredicate( self ):
        
        return ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_RATING, ( '>', 0, self._service_key ) )
        
    
    def GetPredicates( self ):
        
        choice = self._choice.GetValue()
        
        if choice == 'has count':
            
            operator = '>'
            rating = 0
            
        elif choice == 'no count':
            
            operator = '='
            rating = 0
            
        else:
            
            operator = choice
            
            rating = self._rating_value.value()
            
        
        predicate = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_RATING, ( operator, rating, self._service_key ) )
        
        return [ predicate ]
        
    

class PredicateSystemRatingLike( PanelPredicateSystemSingle ):
    
    def __init__( self, parent: QW.QWidget, service_key: bytes, predicate: ClientSearchPredicate.Predicate | None ):
        
        super().__init__( parent )
        
        self._service_key = service_key
        
        try:
            
            service = CG.client_controller.services_manager.GetService( self._service_key )
            
            name = service.GetName()
            
        except HydrusExceptions.DataMissing:
            
            name = 'unknown service'
            
        
        name_st = ClientGUICommon.BetterStaticText( self, name )
        
        name_st.setAlignment( QC.Qt.AlignmentFlag.AlignLeft | QC.Qt.AlignmentFlag.AlignVCenter )
        
        choice_tuples = [
            ( 'has rating', 'rated' ),
            ( 'no rating', 'not rated' ),
            ( 'is', '=' )
        ]
        
        self._choice = ClientGUICommon.BetterRadioBox( self, choice_tuples, vertical = True )
        
        self._rating_control = ClientGUIRatings.RatingLikeDialog( self, service_key, CC.CANVAS_DIALOG )
        
        #
        
        self._choice.SetValue( '' )
        
        if predicate is not None:
            
            value = predicate.GetValue()
            
            if value is not None:
                
                ( operator, rating, service_key ) = value
                
                self._rating_control.SetRatingState( ClientRatings.NULL )
                
                if rating == 'rated':
                    
                    self._choice.SetValue( 'rated' )
                    
                elif rating == 'not rated':
                    
                    self._choice.SetValue( 'not rated' )
                    
                else:
                    
                    self._choice.SetValue( '=' )
                    
                    if rating == 0:
                        
                        self._rating_control.SetRatingState( ClientRatings.DISLIKE )
                        
                    elif rating == 1:
                        
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
        
        if self._choice.GetValue() in ( 'rated', 'not rated' ):
            
            self._choice.SetValue( '=' )
            
        
    
    def _UpdateControls( self ):
        
        choice = self._choice.GetValue()
        
        if choice in ( 'rated', 'not rated' ):
            
            self._rating_control.blockSignals( True )
            self._rating_control.SetRatingState( ClientRatings.NULL )
            self._rating_control.blockSignals( False )
            
        
    
    def GetDefaultPredicate( self ):
        
        return ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_RATING, ( '=', 'rated', self._service_key ) )
        
    
    def GetPredicates( self ):
        
        choice = self._choice.GetValue()
        
        if choice == '':
            
            return []
            
        
        operator = '='
        
        if choice == 'rated':
            
            rating = 'rated'
            
        elif choice == 'not rated':
            
            rating = 'not rated'
            
        else:
            
            rating_state = self._rating_control.GetRatingState()
            
            if rating_state == ClientRatings.LIKE:
                
                rating = 1
                
            elif rating_state == ClientRatings.DISLIKE:
                
                rating = 0
                
            else:
                
                rating = 'not rated'
                
            
        
        predicate = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_RATING, ( operator, rating, self._service_key ) )
        
        return [ predicate ]
        
    

class PredicateSystemRatingNumerical( PanelPredicateSystemSingle ):
    
    def __init__( self, parent: QW.QWidget, service_key: bytes, predicate: ClientSearchPredicate.Predicate | None ):
        
        super().__init__( parent )
        
        self._service_key = service_key
        
        try:
            
            service = CG.client_controller.services_manager.GetService( self._service_key )
            
            name = service.GetName()
            
        except HydrusExceptions.DataMissing:
            
            name = 'unknown service'
            
        
        name_st = ClientGUICommon.BetterStaticText( self, name )
        
        name_st.setAlignment( QC.Qt.AlignmentFlag.AlignLeft | QC.Qt.AlignmentFlag.AlignVCenter )
        
        choice_tuples = [
            ( 'has rating', 'rated' ),
            ( 'no rating', 'not rated' ),
            ( 'more than', '>' ),
            ( 'less than', '<' ),
            ( 'is', '=' ),
            ( 'is about', HC.UNICODE_APPROX_EQUAL )
        ]
        
        self._choice = ClientGUICommon.BetterRadioBox( self, choice_tuples, vertical = True )
        
        self._rating_control = ClientGUIRatings.RatingNumericalDialog( self, service_key )
        
        self._choice.SetValue( '' )
        
        #
        
        if predicate is not None:
            
            value = predicate.GetValue()
            
            if value is not None:
                
                ( operator, rating, service_key ) = value
                
                self._rating_control.SetRating( None )
                
                if rating == 'rated':
                    
                    self._choice.SetValue( 'rated' )
                    
                elif rating == 'not rated':
                    
                    self._choice.SetValue( 'not rated' )
                    
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
        
        if self._choice.GetValue() in ( 'rated', 'not rated' ):
            
            self._choice.SetValue( '=' )
            
        
    
    def _UpdateControls( self ):
        
        choice = self._choice.GetValue()
        
        if choice in ( 'rated', 'not rated' ):
            
            self._rating_control.blockSignals( True )
            self._rating_control.SetRating( None )
            self._rating_control.blockSignals( False )
            
        
    
    def GetDefaultPredicate( self ):
        
        return ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_RATING, ( '=', 'rated', self._service_key ) )
        
    
    def GetPredicates( self ):
        
        choice = self._choice.GetValue()
        
        operator = '='
        rating = None
        
        if choice == 'rated':
            
            operator = '='
            rating = 'rated'
            
        elif choice == 'not rated':
            
            operator = '='
            rating = 'not rated'
            
        else:
            
            operator = choice
            
            if self._rating_control.GetRatingState() == ClientRatings.NULL:
                
                if operator != '=':
                    
                    return []
                    
                
                rating = 'not rated'
                
            else:
                
                rating = self._rating_control.GetRating()
                
            
        
        predicate = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_RATING, ( operator, rating, self._service_key ) )
        
        return [ predicate ]
        
    

class PanelPredicateSystemRatio( PanelPredicateSystemSingle ):
    
    def __init__( self, parent, predicate ):
        
        super().__init__( parent )
        
        choices = ['=','wider than','taller than',HC.UNICODE_APPROX_EQUAL,HC.UNICODE_NOT_EQUAL]
        
        self._sign = ClientGUICommon.BetterRadioBox( self, [ ( c, c ) for c in choices ] )
        
        self._width = ClientGUICommon.BetterSpinBox( self, max=50000, width = 60 )
        
        self._height = ClientGUICommon.BetterSpinBox( self, max=50000, width = 60 )
        
        #
        
        predicate = self._GetPredicateToInitialisePanelWith( predicate )
        
        ( sign, width, height ) = predicate.GetValue()
        
        self._sign.SetValue( sign )
        
        self._width.setValue( width )
        
        self._height.setValue( height )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:ratio'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._width, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,':'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._height, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 0 )
        
        self.setLayout( hbox )
        
        self.setFocusProxy( self._sign )
        
    
    def GetDefaultPredicate( self ):
        
        sign = 'wider than'
        width = 16
        height = 9
        
        return ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_RATIO, ( sign, width, height ) )
        
    
    def GetPredicates( self ):
        
        predicates = ( ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_RATIO, ( self._sign.GetValue(), self._width.value(), self._height.value() ) ), )
        
        return predicates
        
    

class PanelPredicateSystemSimilarToData( PanelPredicateSystemSingle ):
    
    def __init__( self, parent, predicate ):
        
        super().__init__( parent )
        
        self._clear_button = ClientGUICommon.BetterButton( self, 'clear', self._Clear )
        
        self._paste_button = ClientGUICommon.IconButton( self, CC.global_icons().paste, self._Paste )
        self._paste_button.setText( 'Paste image!')
        
        self._pixel_hashes = QW.QPlainTextEdit( self )
        
        self._perceptual_hashes = QW.QPlainTextEdit( self )
        
        ( init_width, init_height ) = ClientGUIFunctions.ConvertTextToPixels( self._pixel_hashes, ( 66, 4 ) )
        
        self._pixel_hashes.setMinimumWidth( init_width )
        self._pixel_hashes.setMaximumHeight( init_height )
        
        self._perceptual_hashes.setMinimumWidth( init_width )
        self._perceptual_hashes.setMaximumHeight( init_height )
        
        self._max_hamming = ClientGUICommon.BetterSpinBox( self, max=256, width = 60 )
        self._max_hamming.setSingleStep( 2 )
        self._max_hamming.setToolTip( ClientGUIFunctions.WrapToolTip( 'The max "hamming distance" allowed in the search. The higher you go, the slower the search and the more false positives.' ) )
        
        #
        
        predicate = self._GetPredicateToInitialisePanelWith( predicate )
        
        self._pixel_hashes.setPlaceholderText( 'pixel hash (64 chars each, paste newline-separated for multiple)' )
        self._perceptual_hashes.setPlaceholderText( 'perceptual hash (16 chars each, paste newline-separated for multiple)' )
        
        ( pixel_hashes, perceptual_hashes, hamming_distance ) = predicate.GetValue()
        
        hashes_text = '\n'.join( [ hash.hex() for hash in pixel_hashes ] )
        
        self._pixel_hashes.setPlainText( hashes_text )
        
        hashes_text = '\n'.join( [ hash.hex() for hash in perceptual_hashes ] )
        
        self._perceptual_hashes.setPlainText( hashes_text )
        
        self._max_hamming.setValue( hamming_distance )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:similar to'), CC.FLAGS_CENTER_PERPENDICULAR )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._pixel_hashes, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, self._perceptual_hashes, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        QP.AddToLayout( hbox, vbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        QP.AddToLayout( hbox, QW.QLabel( HC.UNICODE_APPROX_EQUAL, self ), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._max_hamming, CC.FLAGS_CENTER_PERPENDICULAR )
        
        big_vbox = QP.VBoxLayout()
        
        label = 'Use this if you want to look up a file without needing to import it. Just copy its file path or image data to your clipboard and paste, and hydrus will figure out the search hash data.'
        label += '\n\n'
        label += 'You only need one hash, but allowing both is fine and will add files that match either. Pixel hash is very fast and always returns exact pixel matches. Perceptual hash is the same "looks similar to" system used in "potential duplicates" discovery and the "files" mode of this predicate and uses the 0/2/4/8 "search distance".'
        
        st = ClientGUICommon.BetterStaticText( self, label = label )
        
        st.setWordWrap( True )
        st.setAlignment( QC.Qt.AlignmentFlag.AlignCenter )
        
        QP.AddToLayout( big_vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        button_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( button_hbox, self._paste_button, CC.FLAGS_CENTER )
        QP.AddToLayout( button_hbox, self._clear_button, CC.FLAGS_CENTER )
        
        QP.AddToLayout( big_vbox, button_hbox, CC.FLAGS_CENTER )
        QP.AddToLayout( big_vbox, hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        big_vbox.addStretch( 0 )
        
        self.setLayout( big_vbox )
        
        self.setFocusProxy( self._pixel_hashes )
        
    
    def _Clear( self ):
        
        self._pixel_hashes.setPlainText( '' )
        self._perceptual_hashes.setPlainText( '' )
        
    
    def _Paste( self ):
        
        if CG.client_controller.ClipboardHasImage():
            
            try:
                
                qt_image = CG.client_controller.GetClipboardImage()
                
                numpy_image = ClientGUIFunctions.ConvertQtImageToNumPy( qt_image )
                
                pixel_hash = HydrusImageHandling.GetImagePixelHashNumPy( numpy_image )
                
                perceptual_hashes = ClientImagePerceptualHashes.GenerateUsefulShapePerceptualHashesNumPy( numpy_image )
                
            except Exception as e:
                
                HydrusData.PrintException( e )
                
                ClientGUIDialogsMessage.ShowCritical( self, 'Problem pasting!', f'Sorry, seemed to be a problem: {e}' )
                
                return
                
            
        else:
            
            if CG.client_controller.ClipboardHasLocalPaths():
                
                paths = CG.client_controller.GetClipboardLocalPaths()
                
                if len( paths ) == 0:
                    
                    ClientGUIDialogsMessage.ShowWarning( self, 'The clipboard seemed to have local paths on it, but when I asked for them I got nothing!' )
                    
                    return
                    
                
                path = list( paths )[0]
                
            else:
                
                try:
                    
                    raw_text = CG.client_controller.GetClipboardText()
                    
                except HydrusExceptions.DataMissing as e:
                    
                    ClientGUIDialogsMessage.ShowWarning( self, 'Did not see an image bitmap or a file path in the clipboard!' )
                    
                    return
                    
                
                path = raw_text
                
            
            try:
                
                if os.path.exists( path ) and os.path.isfile( path ):
                    
                    mime = HydrusFileHandling.GetMime( path )
                    
                    if mime in HC.FILES_THAT_HAVE_PERCEPTUAL_HASH:
                        
                        pixel_hash = HydrusImageHandling.GetImagePixelHash( path, mime )
                        
                        perceptual_hashes = ClientImagePerceptualHashes.GenerateUsefulShapePerceptualHashes( path, mime )
                        
                    else:
                        
                        ClientGUIDialogsMessage.ShowWarning( self, 'Sorry, "{}" files are not compatible with the similar file search system!'.format( HC.mime_string_lookup[ mime ] ) )
                        
                        return
                        
                    
                else:
                    
                    ClientGUIDialogsMessage.ShowWarning( self, 'Sorry, that clipboard text did not look like a valid file path!' )
                    
                    return
                    
                
            except Exception as e:
                
                HydrusData.PrintException( e )
                
                ClientGUIDialogsMessage.ShowCritical( self, 'Problem pasting!', f'Sorry, seemed to be a problem: {e}' )
                
                return
                
            
        
        new_text_lines = self._pixel_hashes.toPlainText().splitlines()
        
        new_text_lines.append( pixel_hash.hex() )
        
        new_text_lines = HydrusLists.DedupeList( new_text_lines )
        
        self._pixel_hashes.setPlainText( '\n'.join( new_text_lines ) )
        
        new_text_lines = self._perceptual_hashes.toPlainText().splitlines()
        
        new_text_lines.extend( [ perceptual_hash.hex() for perceptual_hash in perceptual_hashes ] )
        
        new_text_lines = HydrusLists.DedupeList( new_text_lines )
        
        self._perceptual_hashes.setPlainText( '\n'.join( new_text_lines ) )
        
    
    def GetDefaultPredicate( self ):
        
        pixel_hashes = tuple()
        perceptual_hashes = tuple()
        max_hamming = 8
        
        return ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_SIMILAR_TO_DATA, ( pixel_hashes, perceptual_hashes, max_hamming ) )
        
    
    def GetPredicates( self ):
        
        hex_pixel_hashes_raw = self._pixel_hashes.toPlainText()
        
        pixel_hashes = ClientParsing.ParseHashesFromRawHexText( 'pixel', hex_pixel_hashes_raw )
        
        hex_perceptual_hashes_raw = self._perceptual_hashes.toPlainText()
        
        perceptual_hashes = ClientParsing.ParseHashesFromRawHexText( 'perceptual', hex_perceptual_hashes_raw )
        
        predicates = ( ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_SIMILAR_TO_DATA, ( pixel_hashes, perceptual_hashes, self._max_hamming.value() ) ), )
        
        return predicates
        
    

class PanelPredicateSystemSimilarToFiles( PanelPredicateSystemSingle ):
    
    def __init__( self, parent, predicate ):
        
        super().__init__( parent )
        
        # TODO: it would be nice if this guy supported any hash type, like system:hash, and then it would be nice to generalise a 'hashes' widget that has the hash_type selector and prefix stripping stuff
        
        self._hashes = QW.QPlainTextEdit( self )
        
        ( init_width, init_height ) = ClientGUIFunctions.ConvertTextToPixels( self._hashes, ( 66, 6 ) )
        
        self._hashes.setMinimumWidth( init_width )
        self._hashes.setMaximumHeight( init_height )
        
        self._max_hamming = ClientGUICommon.BetterSpinBox( self, max=256, width = 60 )
        self._max_hamming.setSingleStep( 2 )
        self._max_hamming.setToolTip( ClientGUIFunctions.WrapToolTip( 'The max "hamming distance" allowed in the search. The higher you go, the slower the search and the more false positives.' ) )
        
        #
        
        predicate = self._GetPredicateToInitialisePanelWith( predicate )
        
        self._hashes.setPlaceholderText( 'file sha-256 hashes (64 chars each, paste newline-separated for multiple)' )
        
        ( hashes, hamming_distance ) = predicate.GetValue()
        
        hashes_text = '\n'.join( [ hash.hex() for hash in hashes ] )
        
        self._hashes.setPlainText( hashes_text )
        
        self._max_hamming.setValue( hamming_distance )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:similar to'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._hashes, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, QW.QLabel( HC.UNICODE_APPROX_EQUAL, self ), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._max_hamming, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 0 )
        
        st = ClientGUICommon.BetterStaticText( self, label = 'This searches for files that look like each other within your database, just like in the duplicates system. It uses the SHA256 hash and will find all similar-looking files of any of the hashes you paste, regardless of whether they are currently set as potential duplicates, duplicates, alternates, or false positive.' )
        
        st.setWordWrap( True )
        st.setAlignment( QC.Qt.AlignmentFlag.AlignCenter )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, hbox, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.setLayout( vbox )
        
        self.setFocusProxy( self._hashes )
        
    
    def GetDefaultPredicate( self ):
        
        hashes = tuple()
        max_hamming = 4
        
        return ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_SIMILAR_TO_FILES, ( hashes, max_hamming ) )
        
    
    def GetPredicates( self ):
        
        hex_hashes_raw = self._hashes.toPlainText()
        
        hashes = ClientParsing.ParseHashesFromRawHexText( 'sha256', hex_hashes_raw )
        
        predicates = ( ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_SIMILAR_TO_FILES, ( hashes, self._max_hamming.value() ) ), )
        
        return predicates
        
    

class PanelPredicateSystemSize( PanelPredicateSystemSingle ):
    
    def __init__( self, parent, predicate ):
        
        super().__init__( parent )
        
        choices = ['<',HC.UNICODE_APPROX_EQUAL,'=',HC.UNICODE_NOT_EQUAL,'>']
        
        self._sign = ClientGUICommon.BetterRadioBox( self, [ ( c, c ) for c in choices ] )
        
        self._bytes = ClientGUIBytes.BytesControl( self )
        
        #
        
        predicate = self._GetPredicateToInitialisePanelWith( predicate )
        
        ( sign, size, unit ) = predicate.GetValue()
        
        self._sign.SetValue( sign )
        
        self._bytes.SetSeparatedValue( size, unit )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:filesize'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._bytes, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 0 )
        
        self.setLayout( hbox )
        
        self.setFocusProxy( self._sign )
        
    
    def GetDefaultPredicate( self ):
        
        sign = '<'
        size = 200
        unit = 1024
        
        return ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_SIZE, ( sign, size, unit ) )
        
    
    def GetPredicates( self ):
        
        ( size, unit ) = self._bytes.GetSeparatedValue()
        
        predicates = ( ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_SIZE, ( self._sign.GetValue(), size, unit ) ), )
        
        return predicates
        
    

class PanelPredicateSystemTagAdvanced( PanelPredicateSystemSingle ):
    
    def __init__( self, parent, predicate ):
        
        super().__init__( parent )
        
        self._inclusive = ClientGUICommon.BetterRadioBox( self, [ ( 'has tag', True ), ( 'does not have tag', False ) ], vertical = True )
        
        self._service_key_or_none = ClientGUICommon.BetterChoice( self )
        
        self._service_key_or_none.addItem( 'current tag domain', None )
        
        for service in CG.client_controller.services_manager.GetServices( HC.ALL_TAG_SERVICES ):
            
            self._service_key_or_none.addItem( service.GetName(), service.GetServiceKey() )
            
        
        self._tag_display_type = ClientGUICommon.BetterRadioBox(
            self,
            [
                ( 'including siblings/parents', ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL ),
                ( 'ignoring siblings/parents', ClientTags.TAG_DISPLAY_STORAGE )
            ],
            vertical = True
        )
        
        tt = 'Including siblings/parents will search on the "display" tag domain, which is what you see when normally searching for and browsing files. In "display", all siblings are merged to the ideal tag, and missing parents are filled in. Ignoring siblings/parents will search on the "storage" tag domain, which is what is actually recorded on disk (and what you see when editing tags).'
        
        self._tag_display_type.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._statuses = ClientGUICommon.BetterCheckBoxList( self )
        
        for status in (
            HC.CONTENT_STATUS_CURRENT,
            HC.CONTENT_STATUS_PENDING,
            HC.CONTENT_STATUS_DELETED,
            HC.CONTENT_STATUS_PETITIONED
        ):
            
            self._statuses.Append( HC.content_status_string_lookup[ status ], status )
            
        
        tt = 'Note that "deleted" and "petitioned" do not exist in the domain that computes siblings, so if you set to search these while "including siblings", you will get (slow!) results that have any deletion/petitioned record for any of the tags in the sibling group.'
        
        self._statuses.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._tag = QW.QLineEdit( self )
        
        self._tag.setPlaceholderText( 'tag' )
        
        from hydrus.client.gui.search import ClientGUIACDropdown
        
        self._tag_autocomplete = ClientGUIACDropdown.AutoCompleteDropdownTagsWrite(
            self,
            self._AutoCompleteEntersTags,
            ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY ),
            CC.COMBINED_TAG_SERVICE_KEY
        )
        
        #
        
        predicate = self._GetPredicateToInitialisePanelWith( predicate )
        
        ( service_key_or_none, tag_display_type, statuses, tag ) = predicate.GetValue()
        
        self._inclusive.SetValue( predicate.IsInclusive() )
        
        self._service_key_or_none.SetValue( service_key_or_none )
        
        self._tag_display_type.SetValue( tag_display_type )
        
        self._statuses.SetValue( statuses )
        
        self._statuses.SetHeightBasedOnContents()
        
        self._tag.setText( tag )
        
        width = ClientGUIFunctions.ConvertTextToPixelWidth( self._tag, 48 )
        
        self._tag.setMinimumWidth( width )
        
        tag_vbox = QP.VBoxLayout()
        
        QP.AddToLayout( tag_vbox, self._tag, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( tag_vbox, self._tag_autocomplete, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText( self,'system:' ), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._inclusive, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._service_key_or_none, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._tag_display_type, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._statuses, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, tag_vbox, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH )
        
        hbox.addStretch( 0 )
        
        self.setLayout( hbox )
        
        self.setFocusProxy( self._inclusive )
        
    
    def _AutoCompleteEntersTags( self, tags ):
        
        tags = list( tags )
        
        if len( tags ) > 0:
            
            tag = tags[0]
            
            self._tag.setText( tag )
            
        
    
    def GetDefaultPredicate( self ):
        
        service_key_or_none = None
        tag_display_type = ClientTags.TAG_DISPLAY_STORAGE
        statuses = ( HC.CONTENT_STATUS_CURRENT, HC.CONTENT_STATUS_PENDING )
        tag = ''
        
        return ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_TAG_ADVANCED, ( service_key_or_none, tag_display_type, statuses, tag ) )
        
    
    def GetPredicates( self ):
        
        inclusive = self._inclusive.GetValue()
        
        service_key_or_none = self._service_key_or_none.GetValue()
        tag_display_type = self._tag_display_type.GetValue()
        statuses = tuple( self._statuses.GetValue() )
        tag = self._tag.text()
        
        if len( statuses ) == 0:
            
            statuses = ( HC.CONTENT_STATUS_CURRENT, HC.CONTENT_STATUS_PENDING )
            
        
        try:
            
            tag = HydrusTags.CleanTag( tag )
            
            HydrusTags.CheckTagNotEmpty( tag )
            
        except:
            
            tag = 'invalid tag'
            
        
        predicates = ( ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_TAG_ADVANCED, ( service_key_or_none, tag_display_type, statuses, tag ), inclusive = inclusive ), )
        
        return predicates
        
    

class PanelPredicateSystemTagAsNumber( PanelPredicateSystemSingle ):
    
    def __init__( self, parent, predicate ):
        
        super().__init__( parent )
        
        self._namespace = ClientGUICommon.NamespaceWidget( self )
        
        choices = [ '<', HC.UNICODE_APPROX_EQUAL, '>' ]
        
        self._sign = ClientGUICommon.BetterRadioBox( self, [ ( c, c ) for c in choices ] )
        
        self._num = ClientGUICommon.BetterSpinBox( self, min=-(2 ** 31), max= (2 ** 31) - 1 )
        
        #
        
        predicate = self._GetPredicateToInitialisePanelWith( predicate )
        
        ( namespace, sign, num ) = predicate.GetValue()
        
        self._namespace.SetValue( namespace )
        self._sign.SetValue( sign )
        self._num.setValue( num )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:tag as number: '), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._namespace, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._num, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self.setLayout( hbox )
        
        self.setFocusProxy( self._sign )
        
    
    def GetDefaultPredicate( self ):
        
        namespace = 'page'
        sign = '>'
        num = 0
        
        return ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_TAG_AS_NUMBER, ( namespace, sign, num ) )
        
    
    def GetPredicates( self ):
        
        predicates = ( ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_TAG_AS_NUMBER, ( self._namespace.GetValue(), self._sign.GetValue(), self._num.value() ) ), )
        
        return predicates
        
    

class PanelPredicateSystemWidth( PanelPredicateSystemSingle ):
    
    def __init__( self, parent, predicate ):
        
        super().__init__( parent )
        
        allowed_operators = [
            ClientNumberTest.NUMBER_TEST_OPERATOR_LESS_THAN,
            ClientNumberTest.NUMBER_TEST_OPERATOR_LESS_THAN_OR_EQUAL_TO,
            ClientNumberTest.NUMBER_TEST_OPERATOR_APPROXIMATE_ABSOLUTE,
            ClientNumberTest.NUMBER_TEST_OPERATOR_APPROXIMATE_PERCENT,
            ClientNumberTest.NUMBER_TEST_OPERATOR_EQUAL,
            ClientNumberTest.NUMBER_TEST_OPERATOR_NOT_EQUAL,
            ClientNumberTest.NUMBER_TEST_OPERATOR_GREATER_THAN,
            ClientNumberTest.NUMBER_TEST_OPERATOR_GREATER_THAN_OR_EQUAL_TO
        ]
        
        self._number_test = ClientGUINumberTest.NumberTestWidget( self, allowed_operators = allowed_operators, unit_string = 'px',  appropriate_absolute_plus_or_minus_default = 200 )
        
        #
        
        predicate = self._GetPredicateToInitialisePanelWith( predicate )
        
        number_test = predicate.GetValue()
        
        self._number_test.SetValue( number_test )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:width'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._number_test, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 0 )
        
        self.setLayout( hbox )
        
        self.setFocusProxy( self._number_test )
        
    
    def GetDefaultPredicate( self ):
        
        number_test = ClientNumberTest.NumberTest( operator = ClientNumberTest.NUMBER_TEST_OPERATOR_EQUAL, value = 1920 )
        
        return ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_WIDTH, number_test )
        
    
    def GetPredicates( self ):
        
        number_test = self._number_test.GetValue()
        
        predicates = ( ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_WIDTH, number_test ), )
        
        return predicates
        
    
