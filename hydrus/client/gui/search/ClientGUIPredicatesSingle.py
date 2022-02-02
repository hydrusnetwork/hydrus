import os
import re
import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusText

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientSearch
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIOptionsPanels
from hydrus.client.gui import ClientGUITime
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.gui.widgets import ClientGUIControls

class StaticSystemPredicateButton( QW.QPushButton ):
    
    def __init__( self, parent, ok_panel, predicates, forced_label = None ):
        
        QW.QPushButton.__init__( self, parent )
        
        self._ok_panel = ok_panel
        self._predicates = predicates
        self._forced_label = forced_label
        
        if forced_label is None:
            
            label = ', '.join( ( predicate.ToString() for predicate in self._predicates ) )
            
        else:
            
            label = forced_label
            
        
        self.setText( label )
        
        self.clicked.connect( self.DoOK )
        
    
    def DoOK( self ):
        
        self._ok_panel.SubPanelOK( self._predicates )
        
    
class InvertiblePredicateButton( ClientGUICommon.BetterButton ):
    
    def __init__( self, parent: QW.QWidget, predicate: ClientSearch.Predicate ):
        
        self._predicate = predicate
        
        ClientGUICommon.BetterButton.__init__( self, parent, 'predicate', self._ButtonHit )
        
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
        
    
class PanelPredicateSystem( QW.QWidget ):
    
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
    
    def _GetPredicateToInitialisePanelWith( self, predicate: ClientSearch.Predicate ) -> ClientSearch.Predicate:
        
        default_predicate = self.GetDefaultPredicate()
        
        if predicate.IsUIEditable( default_predicate ):
            
            return predicate
            
        
        custom_defaults = HG.client_controller.new_options.GetCustomDefaultSystemPredicates( comparable_predicate = default_predicate )
        
        if len( custom_defaults ) > 0:
            
            return list( custom_defaults )[0]
            
        
        return default_predicate
        
    
    def ClearCustomDefault( self ):
        
        default_predicate = self.GetDefaultPredicate()
        
        HG.client_controller.new_options.ClearCustomDefaultSystemPredicates( comparable_predicate = default_predicate )
        
    
    def GetDefaultPredicate( self ) -> ClientSearch.Predicate:
        
        raise NotImplementedError()
        
    
    def GetPredicates( self ):
        
        raise NotImplementedError()
        
    
    def SaveCustomDefault( self ):
        
        predicates = self.GetPredicates()
        
        HG.client_controller.new_options.SetCustomDefaultSystemPredicates( comparable_predicates = predicates )
        
    
    def UsesCustomDefault( self ) -> bool:
        
        default_predicate = self.GetDefaultPredicate()
        
        custom_defaults = HG.client_controller.new_options.GetCustomDefaultSystemPredicates( comparable_predicate = default_predicate )
        
        return len( custom_defaults ) > 0
        
    
class PanelPredicateSystemAgeDate( PanelPredicateSystemSingle ):
    
    def __init__( self, parent, predicate ):
        
        PanelPredicateSystemSingle.__init__( self, parent )
        
        self._sign = QP.RadioBox( self, choices=['<',CC.UNICODE_ALMOST_EQUAL_TO,'=','>'] )
        
        self._date = QW.QCalendarWidget( self )
        
        #
        
        predicate = self._GetPredicateToInitialisePanelWith( predicate )
        
        ( sign, age_type, ( years, months, days ) ) = predicate.GetValue()
        
        self._sign.SetStringSelection( sign )
        
        qt_dt = QC.QDate( years, months, days )
        
        self._date.setSelectedDate( qt_dt )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:import time'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._date, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetDefaultPredicate( self ) -> ClientSearch.Predicate:
        
        qt_dt = QC.QDate.currentDate()
        
        qt_dt.addDays( -7 )
        
        year = qt_dt.year()
        month = qt_dt.month()
        day = qt_dt.day()
        
        return ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_AGE, ( '>', 'date', ( year, month, day ) ) )
        
    
    def GetPredicates( self ):
        
        qt_dt = self._date.selectedDate()
        
        year = qt_dt.year()
        month = qt_dt.month()
        day = qt_dt.day()
        
        predicates = ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_AGE, ( self._sign.GetStringSelection(), 'date', ( year, month, day ) ) ), )
        
        return predicates
        
    
class PanelPredicateSystemAgeDelta( PanelPredicateSystemSingle ):
    
    def __init__( self, parent, predicate ):
        
        PanelPredicateSystemSingle.__init__( self, parent )
        
        self._sign = QP.RadioBox( self, choices=['<',CC.UNICODE_ALMOST_EQUAL_TO,'>'] )
        
        self._years = QP.MakeQSpinBox( self, max=30, width = 60 )
        self._months = QP.MakeQSpinBox( self, max=60, width = 60 )
        self._days = QP.MakeQSpinBox( self, max=90, width = 60 )
        self._hours = QP.MakeQSpinBox( self, max=24, width = 60 )
        
        #
        
        predicate = self._GetPredicateToInitialisePanelWith( predicate )
        
        ( sign, age_type, ( years, months, days, hours ) ) = predicate.GetValue()
        
        self._sign.SetStringSelection( sign )
        
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
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'hours'), CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetDefaultPredicate( self ):
        
        return ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_AGE, ( '<', 'delta', ( 0, 0, 7, 0 ) ) )
        
    
    def GetPredicates( self ):
        
        predicates = ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_AGE, ( self._sign.GetStringSelection(), 'delta', (self._years.value(), self._months.value(), self._days.value(), self._hours.value() ) ) ), )
        
        return predicates
        
    
class PanelPredicateSystemLastViewedDate( PanelPredicateSystemSingle ):
    
    def __init__( self, parent, predicate ):
        
        PanelPredicateSystemSingle.__init__( self, parent )
        
        self._sign = QP.RadioBox( self, choices=['<',CC.UNICODE_ALMOST_EQUAL_TO,'=','>'] )
        
        self._date = QW.QCalendarWidget( self )
        
        #
        
        predicate = self._GetPredicateToInitialisePanelWith( predicate )
        
        ( sign, age_type, ( years, months, days ) ) = predicate.GetValue()
        
        self._sign.SetStringSelection( sign )
        
        qt_dt = QC.QDate( years, months, days )
        
        self._date.setSelectedDate( qt_dt )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:last viewed date'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._date, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetDefaultPredicate( self ) -> ClientSearch.Predicate:
        
        qt_dt = QC.QDate.currentDate()
        
        qt_dt.addDays( -7 )
        
        year = qt_dt.year()
        month = qt_dt.month()
        day = qt_dt.day()
        
        return ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_LAST_VIEWED_TIME, ( '>', 'date', ( year, month, day ) ) )
        
    
    def GetPredicates( self ):
        
        qt_dt = self._date.selectedDate()
        
        year = qt_dt.year()
        month = qt_dt.month()
        day = qt_dt.day()
        
        predicates = ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_LAST_VIEWED_TIME, ( self._sign.GetStringSelection(), 'date', ( year, month, day ) ) ), )
        
        return predicates
        
    
class PanelPredicateSystemLastViewedDelta( PanelPredicateSystemSingle ):
    
    def __init__( self, parent, predicate ):
        
        PanelPredicateSystemSingle.__init__( self, parent )
        
        self._sign = QP.RadioBox( self, choices=['<',CC.UNICODE_ALMOST_EQUAL_TO,'>'] )
        
        self._years = QP.MakeQSpinBox( self, max=30 )
        self._months = QP.MakeQSpinBox( self, max=60 )
        self._days = QP.MakeQSpinBox( self, max=90 )
        self._hours = QP.MakeQSpinBox( self, max=24 )
        
        #
        
        predicate = self._GetPredicateToInitialisePanelWith( predicate )
        
        ( sign, age_type, ( years, months, days, hours ) ) = predicate.GetValue()
        
        self._sign.SetStringSelection( sign )
        
        self._years.setValue( years )
        self._months.setValue( months )
        self._days.setValue( days )
        self._hours.setValue( hours )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:last viewed'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._years, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'years'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._months, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'months'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._days, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'days'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._hours, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'hours'), CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetDefaultPredicate( self ):
        
        return ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_LAST_VIEWED_TIME, ( '<', 'delta', ( 0, 0, 7, 0 ) ) )
        
    
    def GetPredicates( self ):
        
        predicates = ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_LAST_VIEWED_TIME, ( self._sign.GetStringSelection(), 'delta', ( self._years.value(), self._months.value(), self._days.value(), self._hours.value() ) ) ), )
        
        return predicates
        
    
class PanelPredicateSystemModifiedDate( PanelPredicateSystemSingle ):
    
    def __init__( self, parent, predicate ):
        
        PanelPredicateSystemSingle.__init__( self, parent )
        
        self._sign = QP.RadioBox( self, choices=['<',CC.UNICODE_ALMOST_EQUAL_TO,'=','>'] )
        
        self._date = QW.QCalendarWidget( self )
        
        #
        
        predicate = self._GetPredicateToInitialisePanelWith( predicate )
        
        ( sign, age_type, ( years, months, days ) ) = predicate.GetValue()
        
        self._sign.SetStringSelection( sign )
        
        qt_dt = QC.QDate( years, months, days )
        
        self._date.setSelectedDate( qt_dt )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:modified date'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._date, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetDefaultPredicate( self ) -> ClientSearch.Predicate:
        
        qt_dt = QC.QDate.currentDate()
        
        qt_dt.addDays( -7 )
        
        year = qt_dt.year()
        month = qt_dt.month()
        day = qt_dt.day()
        
        return ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_MODIFIED_TIME, ( '>', 'date', ( year, month, day ) ) )
        
    
    def GetPredicates( self ):
        
        qt_dt = self._date.selectedDate()
        
        year = qt_dt.year()
        month = qt_dt.month()
        day = qt_dt.day()
        
        predicates = ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_MODIFIED_TIME, ( self._sign.GetStringSelection(), 'date', ( year, month, day ) ) ), )
        
        return predicates
        
    
class PanelPredicateSystemModifiedDelta( PanelPredicateSystemSingle ):
    
    def __init__( self, parent, predicate ):
        
        PanelPredicateSystemSingle.__init__( self, parent )
        
        self._sign = QP.RadioBox( self, choices=['<',CC.UNICODE_ALMOST_EQUAL_TO,'>'] )
        
        self._years = QP.MakeQSpinBox( self, max=30 )
        self._months = QP.MakeQSpinBox( self, max=60 )
        self._days = QP.MakeQSpinBox( self, max=90 )
        self._hours = QP.MakeQSpinBox( self, max=24 )
        
        #
        
        predicate = self._GetPredicateToInitialisePanelWith( predicate )
        
        ( sign, age_type, ( years, months, days, hours ) ) = predicate.GetValue()
        
        self._sign.SetStringSelection( sign )
        
        self._years.setValue( years )
        self._months.setValue( months )
        self._days.setValue( days )
        self._hours.setValue( hours )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:modified date'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._years, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'years'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._months, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'months'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._days, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'days'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._hours, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'hours'), CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetDefaultPredicate( self ):
        
        return ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_MODIFIED_TIME, ( '<', 'delta', ( 0, 0, 7, 0 ) ) )
        
    
    def GetPredicates( self ):
        
        predicates = ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_MODIFIED_TIME, ( self._sign.GetStringSelection(), 'delta', ( self._years.value(), self._months.value(), self._days.value(), self._hours.value() ) ) ), )
        
        return predicates
        
    
class PanelPredicateSystemDuplicateRelationships( PanelPredicateSystemSingle ):
    
    def __init__( self, parent, predicate ):
        
        PanelPredicateSystemSingle.__init__( self, parent )
        
        choices = [ '<', CC.UNICODE_ALMOST_EQUAL_TO, '=', '>' ]
        
        self._sign = QP.RadioBox( self, choices = choices )
        
        self._num = QP.MakeQSpinBox( self, min=0, max=65535 )
        
        choices = [ ( HC.duplicate_type_string_lookup[ status ], status ) for status in ( HC.DUPLICATE_MEMBER, HC.DUPLICATE_ALTERNATE, HC.DUPLICATE_FALSE_POSITIVE, HC.DUPLICATE_POTENTIAL ) ]
        
        self._dupe_type = ClientGUICommon.BetterRadioBox( self, choices = choices, vertical = True )
        
        #
        
        predicate = self._GetPredicateToInitialisePanelWith( predicate )
        
        ( sign, num, dupe_type ) = predicate.GetValue()
        
        self._sign.SetStringSelection( sign )
        self._num.setValue( num )
        self._dupe_type.SetValue( dupe_type )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:num file relationships'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._num, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._dupe_type, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetDefaultPredicate( self ):
        
        sign = '>'
        num = 0
        dupe_type = HC.DUPLICATE_MEMBER
        
        return ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_FILE_RELATIONSHIPS_COUNT, ( sign, num, dupe_type ) )
        
    
    def GetPredicates( self ):
        
        predicates = ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_FILE_RELATIONSHIPS_COUNT, ( self._sign.GetStringSelection(), self._num.value(), self._dupe_type.GetValue() ) ), )
        
        return predicates
        
    
class PanelPredicateSystemDuration( PanelPredicateSystemSingle ):
    
    def __init__( self, parent, predicate ):
        
        PanelPredicateSystemSingle.__init__( self, parent )
        
        choices = [ '<', CC.UNICODE_ALMOST_EQUAL_TO, '=', CC.UNICODE_NOT_EQUAL_TO, '>' ]
        
        self._sign = QP.RadioBox( self, choices = choices )
        
        self._duration_s = QP.MakeQSpinBox( self, max=3599, width = 60 )
        self._duration_ms = QP.MakeQSpinBox( self, max=999, width = 60 )
        
        #
        
        predicate = self._GetPredicateToInitialisePanelWith( predicate )
        
        ( sign, ms ) = predicate.GetValue()
        
        s = ms // 1000
        
        ms = ms % 1000
        
        self._sign.SetStringSelection( sign )
        
        self._duration_s.setValue( s )
        self._duration_ms.setValue( ms )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:duration'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._duration_s, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'s'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._duration_ms, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'ms'), CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetDefaultPredicate( self ):
        
        sign = '>'
        duration = 0
        
        return ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_DURATION, ( sign, duration ) )
        
    
    def GetPredicates( self ):
        
        predicates = ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_DURATION, ( self._sign.GetStringSelection(), self._duration_s.value() * 1000 + self._duration_ms.value() ) ), )
        
        return predicates
        
    
class PanelPredicateSystemFileService( PanelPredicateSystemSingle ):
    
    def __init__( self, parent, predicate ):
        
        PanelPredicateSystemSingle.__init__( self, parent )
        
        self._sign = ClientGUICommon.BetterRadioBox( self, choices = [ ( 'is', True ), ( 'is not', False ) ], vertical = True )
        
        choices = [
            ( 'currently in', HC.CONTENT_STATUS_CURRENT ),
            ( 'deleted from', HC.CONTENT_STATUS_DELETED ),
            ( 'pending to', HC.CONTENT_STATUS_PENDING ),
            ( 'petitioned from', HC.CONTENT_STATUS_PETITIONED )
        ]
        
        self._status = ClientGUICommon.BetterRadioBox( self, choices = choices, vertical = True )
        
        services = HG.client_controller.services_manager.GetServices( HC.FILE_SERVICES )
        
        choices = [ ( service.GetName(), service.GetServiceKey() ) for service in services ]
        
        self._file_service_key = ClientGUICommon.BetterRadioBox( self, choices = choices, vertical = True )
        
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
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetDefaultPredicate( self ):
        
        sign = True
        status = HC.CONTENT_STATUS_CURRENT
        file_service_key = bytes()
        
        return ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_FILE_SERVICE, ( sign, status, file_service_key ) )
        
    
    def GetPredicates( self ):
        
        predicates = ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_FILE_SERVICE, ( self._sign.GetValue(), self._status.GetValue(), self._file_service_key.GetValue() ) ), )
        
        return predicates
        
    
class PanelPredicateSystemFileViewingStatsViews( PanelPredicateSystemSingle ):
    
    def __init__( self, parent, predicate ):
        
        PanelPredicateSystemSingle.__init__( self, parent )
        
        self._viewing_locations = ClientGUICommon.BetterCheckBoxList( self )
        
        self._viewing_locations.Append( 'media views', 'media' )
        self._viewing_locations.Append( 'preview views', 'preview' )
        
        self._sign = QP.RadioBox( self, choices=['<',CC.UNICODE_ALMOST_EQUAL_TO,'=','>'] )
        
        self._num = QP.MakeQSpinBox( self, min=0, max=1000000 )
        
        #
        
        predicate = self._GetPredicateToInitialisePanelWith( predicate )
        
        ( view_type, viewing_locations, sign, num ) = predicate.GetValue()
        
        self._viewing_locations.SetValue( viewing_locations )
        
        ( width, height ) = ClientGUIFunctions.ConvertTextToPixels( self._viewing_locations, ( 10, 3 ) )
        
        self._viewing_locations.setMaximumHeight( height )
        
        self._sign.SetStringSelection( sign )
        
        self._num.setValue( num )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._viewing_locations, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._num, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetDefaultPredicate( self ):
        
        viewing_locations = ( 'media', )
        sign = '>'
        num = 10
        
        return ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_FILE_VIEWING_STATS, ( 'views', tuple( viewing_locations ), sign, num ) )
        
    
    def GetPredicates( self ):
        
        viewing_locations = self._viewing_locations.GetValue()
        
        if len( viewing_locations ) == 0:
            
            viewing_locations = [ 'media' ]
            
        
        sign = self._sign.GetStringSelection()
        
        num = self._num.value()
        
        predicates = ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_FILE_VIEWING_STATS, ( 'views', tuple( viewing_locations ), sign, num ) ), )
        
        return predicates
        
    
class PanelPredicateSystemFileViewingStatsViewtime( PanelPredicateSystemSingle ):
    
    def __init__( self, parent, predicate ):
        
        PanelPredicateSystemSingle.__init__( self, parent )
        
        self._viewing_locations = ClientGUICommon.BetterCheckBoxList( self )
        
        self._viewing_locations.Append( 'media viewtime', 'media' )
        self._viewing_locations.Append( 'preview viewtime', 'preview' )
        
        self._sign = QP.RadioBox( self, choices=['<',CC.UNICODE_ALMOST_EQUAL_TO,'=','>'] )
        
        self._time_delta = ClientGUITime.TimeDeltaCtrl( self, min = 0, days = True, hours = True, minutes = True, seconds = True )
        
        #
        
        predicate = self._GetPredicateToInitialisePanelWith( predicate )
        
        ( view_type, viewing_locations, sign, time_delta ) = predicate.GetValue()
        
        self._viewing_locations.SetValue( viewing_locations )
        
        ( width, height ) = ClientGUIFunctions.ConvertTextToPixels( self._viewing_locations, ( 10, 3 ) )
        
        self._viewing_locations.setMaximumHeight( height )
        
        self._sign.SetStringSelection( sign )
        
        self._time_delta.SetValue( time_delta )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._viewing_locations, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._time_delta, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetDefaultPredicate( self ):
        
        viewing_locations = ( 'media', )
        sign = '>'
        time_delta = 600
        
        return ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_FILE_VIEWING_STATS, ( 'viewtime', tuple( viewing_locations ), sign, time_delta ) )
        
    
    def GetPredicates( self ):
        
        viewing_locations = self._viewing_locations.GetValue()
        
        if len( viewing_locations ) == 0:
            
            viewing_locations = [ 'media' ]
            
        
        sign = self._sign.GetStringSelection()
        
        time_delta = self._time_delta.GetValue()
        
        predicates = ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_FILE_VIEWING_STATS, ( 'viewtime', tuple( viewing_locations ), sign, time_delta ) ), )
        
        return predicates
        
    
class PanelPredicateSystemFramerate( PanelPredicateSystemSingle ):
    
    def __init__( self, parent, predicate ):
        
        PanelPredicateSystemSingle.__init__( self, parent )
        
        choices = [ '<', '=', CC.UNICODE_NOT_EQUAL_TO, '>' ]
        
        self._sign = QP.RadioBox( self, choices = choices )
        
        self._framerate = QP.MakeQSpinBox( self, min = 1, max = 3600, width = 60 )
        
        #
        
        predicate = self._GetPredicateToInitialisePanelWith( predicate )
        
        ( sign, framerate ) = predicate.GetValue()
        
        self._sign.SetStringSelection( sign )
        self._framerate.setValue( framerate )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText( self, 'system:framerate' ), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._framerate, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText( self, 'fps' ), CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 1 )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, ClientGUICommon.BetterStaticText( 'All framerate searches are +/- 5%. Exactly searching for 29.97 is not currently possible.' ), CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self.setLayout( vbox )
        
    
    def GetDefaultPredicate( self ):
        
        sign = '='
        framerate = 60
        
        return ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_FRAMERATE, ( sign, framerate ) )
        
    
    def GetPredicates( self ):
        
        predicates = ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_FRAMERATE, ( self._sign.GetStringSelection(), self._framerate.value() ) ), )
        
        return predicates
        
    
class PanelPredicateSystemHash( PanelPredicateSystemSingle ):
    
    def __init__( self, parent, predicate ):
        
        PanelPredicateSystemSingle.__init__( self, parent )
        
        self._hashes = QW.QPlainTextEdit( self )
        
        ( init_width, init_height ) = ClientGUIFunctions.ConvertTextToPixels( self._hashes, ( 66, 10 ) )
        
        self._hashes.setMinimumSize( QC.QSize( init_width, init_height ) )
        
        choices = [ 'sha256', 'md5', 'sha1', 'sha512' ]
        
        self._hash_type = QP.RadioBox( self, choices = choices, vertical = True )
        
        self._hashes.setPlaceholderText( 'enter hash (paste newline-separated for multiple hashes)' )
        
        #
        
        predicate = self._GetPredicateToInitialisePanelWith( predicate )
        
        ( hashes, hash_type ) = predicate.GetValue()
        
        hashes_text = os.linesep.join( [ hash.hex() for hash in hashes ] )
        
        self._hashes.setPlainText( hashes_text )
        
        self._hash_type.SetStringSelection( hash_type )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:hash='), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._hashes, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._hash_type, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetDefaultPredicate( self ):
        
        hashes = tuple()
        hash_type = 'sha256'
        
        return ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_HASH, ( hashes, hash_type ) )
        
    
    def GetPredicates( self ):
        
        hash_type = self._hash_type.GetStringSelection()
        
        hex_hashes_raw = self._hashes.toPlainText()
        
        hashes = HydrusData.ParseHashesFromRawHexText( hash_type, hex_hashes_raw )
        
        predicates = ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_HASH, ( hashes, hash_type ) ), )
        
        return predicates
        
    
class PanelPredicateSystemHasNoteName( PanelPredicateSystemSingle ):
    
    def __init__( self, parent, predicate ):
        
        PanelPredicateSystemSingle.__init__( self, parent )
        
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
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetDefaultPredicate( self ):
        
        operator = True
        name = ''
        
        return ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_HAS_NOTE_NAME, ( operator, name ) )
        
    
    def GetPredicates( self ):
        
        name = self._name.text()
        
        if name == '':
            
            name = 'notes'
            
        
        predicates = ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_HAS_NOTE_NAME, ( self._operator.GetValue(), name ) ), )
        
        return predicates
        
    
class PanelPredicateSystemHeight( PanelPredicateSystemSingle ):
    
    def __init__( self, parent, predicate ):
        
        PanelPredicateSystemSingle.__init__( self, parent )
        
        self._sign = QP.RadioBox( self, choices=['<',CC.UNICODE_ALMOST_EQUAL_TO,'=',CC.UNICODE_NOT_EQUAL_TO,'>'] )
        
        self._height = QP.MakeQSpinBox( self, max=200000, width = 60 )
        
        #
        
        predicate = self._GetPredicateToInitialisePanelWith( predicate )
        
        ( sign, height ) = predicate.GetValue()
        
        self._sign.SetStringSelection( sign )
        
        self._height.setValue( height )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:height'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._height, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetDefaultPredicate( self ):
        
        sign = '='
        height = 1080
        
        return ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_HEIGHT, ( sign, height ) )
        
    
    def GetPredicates( self ):
        
        predicates = ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_HEIGHT, ( self._sign.GetStringSelection(), self._height.value() ) ), )
        
        return predicates
        
    
class PanelPredicateSystemKnownURLsExactURL( PanelPredicateSystemSingle ):
    
    def __init__( self, parent, predicate ):
        
        PanelPredicateSystemSingle.__init__( self, parent )
        
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
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:known url'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._operator, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'exact url:'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._exact_url, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.setLayout( hbox )
        
    
    def GetDefaultPredicate( self ):
        
        operator = True
        rule_type = 'exact_match'
        rule = ''
        description = ''
        
        return ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_KNOWN_URLS, ( operator, rule_type, rule, description ) )
        
    
    def GetPredicates( self ):
        
        operator = self._operator.GetValue()
        
        if operator:
            
            operator_description = 'has url: '
            
        else:
            
            operator_description = 'does not have url: '
            
        
        rule_type = 'exact_match'
        
        exact_url = self._exact_url.text()
        
        rule = exact_url
        
        description = operator_description + exact_url
        
        predicates = ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_KNOWN_URLS, ( operator, rule_type, rule, description ) ), )
        
        return predicates
        
    
class PanelPredicateSystemKnownURLsDomain( PanelPredicateSystemSingle ):
    
    def __init__( self, parent, predicate ):
        
        PanelPredicateSystemSingle.__init__( self, parent )
        
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
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:known url'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._operator, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'a url with domain:'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._domain, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.setLayout( hbox )
        
    
    def GetDefaultPredicate( self ):
        
        operator = True
        rule_type = 'domain'
        rule = ''
        description = ''
        
        return ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_KNOWN_URLS, ( operator, rule_type, rule, description ) )
        
    
    def GetPredicates( self ):
        
        operator = self._operator.GetValue()
        
        if operator:
            
            operator_description = 'has a url with domain: '
            
        else:
            
            operator_description = 'does not have a url with domain: '
            
        
        rule_type = 'domain'
        
        domain = self._domain.text()
        
        rule = domain
        
        description = operator_description + domain
        
        predicates = ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_KNOWN_URLS, ( operator, rule_type, rule, description ) ), )
        
        return predicates
        
    
class PanelPredicateSystemKnownURLsRegex( PanelPredicateSystemSingle ):
    
    def __init__( self, parent, predicate ):
        
        PanelPredicateSystemSingle.__init__( self, parent )
        
        self._operator = ClientGUICommon.BetterChoice( self )
        
        self._operator.addItem( 'has', True )
        self._operator.addItem( 'does not have', False )
        
        self._regex = QW.QLineEdit( self )
        
        #
        
        predicate = self._GetPredicateToInitialisePanelWith( predicate )
        
        ( operator, rule_type, rule, description ) = predicate.GetValue()
        
        self._operator.SetValue( operator )
        self._regex.setText( rule )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:known url'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._operator, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'a url that matches this regex:'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._regex, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.setLayout( hbox )
        
    
    def GetDefaultPredicate( self ):
        
        operator = True
        rule_type = 'regex'
        rule = ''
        description = ''
        
        return ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_KNOWN_URLS, ( operator, rule_type, rule, description ) )
        
    
    def CheckValid( self ):
        
        regex = self._regex.text()
        
        try:
            
            re.compile( regex )
            
        except Exception as e:
            
            raise Exception( 'Cannot compile that regex: {}'.format( e ) )
            
        
    
    def GetPredicates( self ):
        
        operator = self._operator.GetValue()
        
        if operator:
            
            operator_description = 'has a url matching regex: '
            
        else:
            
            operator_description = 'does not have a url matching regex: '
            
        
        rule_type = 'regex'
        
        regex = self._regex.text()
        
        rule = regex
        
        description = operator_description + regex
        
        predicates = ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_KNOWN_URLS, ( operator, rule_type, rule, description ) ), )
        
        return predicates
        
    
class PanelPredicateSystemKnownURLsURLClass( PanelPredicateSystemSingle ):
    
    def __init__( self, parent, predicate ):
        
        PanelPredicateSystemSingle.__init__( self, parent )
        
        self._operator = ClientGUICommon.BetterChoice( self )
        
        self._operator.addItem( 'has', True )
        self._operator.addItem( 'does not have', False )
        
        self._url_classes = ClientGUICommon.BetterChoice( self )
        
        for url_class in HG.client_controller.network_engine.domain_manager.GetURLClasses():
            
            if url_class.ShouldAssociateWithFiles():
                
                self._url_classes.addItem( url_class.GetName(), url_class )
                
            
        
        #
        
        predicate = self._GetPredicateToInitialisePanelWith( predicate )
        
        ( operator, rule_type, rule, description ) = predicate.GetValue()
        
        self._operator.SetValue( operator )
        self._url_classes.SetValue( rule )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:known url'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._operator, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'url matching this class:'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._url_classes, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.setLayout( hbox )
        
    
    def GetDefaultPredicate( self ):
        
        operator = True
        rule_type = 'regex'
        rule = None
        description = ''
        
        return ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_KNOWN_URLS, ( operator, rule_type, rule, description ) )
        
    
    def GetPredicates( self ):
        
        operator = self._operator.GetValue()
        
        if operator:
            
            operator_description = 'has '
            
        else:
            
            operator_description = 'does not have '
            
        
        rule_type = 'url_class'
        
        url_class = self._url_classes.GetValue()
        
        rule = url_class
        
        description = operator_description + url_class.GetName() + ' url'
        
        predicates = ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_KNOWN_URLS, ( operator, rule_type, rule, description ) ), )
        
        return predicates
        
    
class PanelPredicateSystemLimit( PanelPredicateSystemSingle ):
    
    def __init__( self, parent, predicate ):
        
        PanelPredicateSystemSingle.__init__( self, parent )
        
        self._limit = QP.MakeQSpinBox( self, max=1000000, width = 60 )
        
        #
        
        predicate = self._GetPredicateToInitialisePanelWith( predicate )
        
        limit = predicate.GetValue()
        
        self._limit.setValue( limit )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:limit='), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._limit, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetDefaultPredicate( self ):
        
        limit = 256
        
        return ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_LIMIT, limit )
        
    
    def GetPredicates( self ):
        
        predicates = ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_LIMIT, self._limit.value() ), )
        
        return predicates
        
    
class PanelPredicateSystemMime( PanelPredicateSystemSingle ):
    
    def __init__( self, parent, predicate ):
        
        PanelPredicateSystemSingle.__init__( self, parent )
        
        self._mimes = ClientGUIOptionsPanels.OptionsPanelMimes( self, HC.SEARCHABLE_MIMES )
        
        #
        
        predicate = self._GetPredicateToInitialisePanelWith( predicate )
        
        mimes = predicate.GetValue()
        
        if isinstance( mimes, int ):
            
            mimes = ( mimes, )
            
        
        self._mimes.SetValue( mimes )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText( self, 'system:filetype' ), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._mimes, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetDefaultPredicate( self ):
        
        mimes = tuple()
        
        return ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_MIME, mimes )
        
    
    def GetPredicates( self ):
        
        mimes = self._mimes.GetValue()
        
        predicates = ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_MIME, mimes ), )
        
        return predicates
        
    
class PanelPredicateSystemNumPixels( PanelPredicateSystemSingle ):
    
    def __init__( self, parent, predicate ):
        
        PanelPredicateSystemSingle.__init__( self, parent )
        
        self._sign = QP.RadioBox( self, choices=[ '<', CC.UNICODE_ALMOST_EQUAL_TO, '=', CC.UNICODE_NOT_EQUAL_TO, '>' ] )
        
        self._num_pixels = QP.MakeQSpinBox( self, max=1048576, width = 60 )
        
        self._unit = QP.RadioBox( self, choices=['pixels','kilopixels','megapixels'] )
        
        #
        
        predicate = self._GetPredicateToInitialisePanelWith( predicate )
        
        ( sign, num_pixels, unit ) = predicate.GetValue()
        
        self._sign.SetStringSelection( sign )
        
        self._num_pixels.setValue( num_pixels )
        
        self._unit.SetStringSelection( HydrusData.ConvertIntToPixels( unit ) )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:num_pixels'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._num_pixels, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._unit, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetDefaultPredicate( self ):
        
        sign = CC.UNICODE_ALMOST_EQUAL_TO
        num_pixels = 2
        unit = 1000000
        
        return ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_PIXELS, ( sign, num_pixels, unit ) )
        
    
    def GetPredicates( self ):
        
        predicates = ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_PIXELS, ( self._sign.GetStringSelection(), self._num_pixels.value(), HydrusData.ConvertPixelsToInt( self._unit.GetStringSelection() ) ) ), )
        
        return predicates
        
    
class PanelPredicateSystemNumFrames( PanelPredicateSystemSingle ):
    
    def __init__( self, parent, predicate ):
        
        PanelPredicateSystemSingle.__init__( self, parent )
        
        choices = [ '<', CC.UNICODE_ALMOST_EQUAL_TO, '=', CC.UNICODE_NOT_EQUAL_TO, '>' ]
        
        self._sign = QP.RadioBox( self, choices = choices )
        
        self._num_frames = QP.MakeQSpinBox( self, min = 0, max = 1000000, width = 80 )
        
        #
        
        predicate = self._GetPredicateToInitialisePanelWith( predicate )
        
        ( sign, num_frames ) = predicate.GetValue()
        
        self._sign.SetStringSelection( sign )
        self._num_frames.setValue( num_frames )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText( self, 'system:number of frames' ), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._num_frames, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetDefaultPredicate( self ):
        
        sign = '>'
        num_frames = 600
        
        return ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_FRAMES, ( sign, num_frames ) )
        
    
    def GetPredicates( self ):
        
        predicates = ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_FRAMES, ( self._sign.GetStringSelection(), self._num_frames.value() ) ), )
        
        return predicates
        
    
class PanelPredicateSystemNumTags( PanelPredicateSystemSingle ):
    
    def __init__( self, parent, predicate ):
        
        PanelPredicateSystemSingle.__init__( self, parent )
        
        self._namespace = ClientGUICommon.NoneableTextCtrl( self, none_phrase = 'all tags' )
        self._namespace.setToolTip( 'Enable but leave blank for unnamespaced tags.' )
        
        self._sign = QP.RadioBox( self, choices=['<',CC.UNICODE_ALMOST_EQUAL_TO,'=','>'] )
        
        self._num_tags = QP.MakeQSpinBox( self, max=2000, width = 60 )
        
        #
        
        predicate = self._GetPredicateToInitialisePanelWith( predicate )
        
        ( namespace, sign, num_tags ) = predicate.GetValue()
        
        self._namespace.SetValue( namespace )
        
        self._sign.SetStringSelection( sign )
        
        self._num_tags.setValue( num_tags )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:number of tags: namespace:'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._namespace, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._num_tags, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetDefaultPredicate( self ):
        
        namespace = None
        sign = '>'
        num_tags = 4
        
        return ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( namespace, sign, num_tags ) )
        
    
    def GetPredicates( self ):
        
        ( namespace, operator, value ) = ( self._namespace.GetValue(), self._sign.GetStringSelection(), self._num_tags.value() )
        
        predicate = None
        
        if namespace is not None:
            
            number_test = ClientSearch.NumberTest.STATICCreateFromCharacters( operator, value )
            
            if number_test.IsZero():
                
                predicate = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_NAMESPACE, namespace, inclusive = False )
                
            elif number_test.IsAnythingButZero():
                
                predicate = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_NAMESPACE, namespace )
                
            
        
        if predicate is None:
            
            predicate = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( namespace, operator, value ) )
            
        
        predicates = ( predicate, )
        
        return predicates
        
    
class PanelPredicateSystemNumNotes( PanelPredicateSystemSingle ):
    
    def __init__( self, parent, predicate ):
        
        PanelPredicateSystemSingle.__init__( self, parent )
        
        self._sign = QP.RadioBox( self, choices = [ '<', '=', '>' ] )
        
        self._num_notes = QP.MakeQSpinBox( self, max = 256, width = 60 )
        
        #
        
        predicate = self._GetPredicateToInitialisePanelWith( predicate )
        
        ( sign, num_notes ) = predicate.GetValue()
        
        self._sign.SetStringSelection( sign )
        
        self._num_notes.setValue( num_notes )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:number of notes'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._num_notes, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetDefaultPredicate( self ):
        
        sign = '='
        num_notes = 1
        
        return ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_NOTES, ( sign, num_notes ) )
        
    
    def GetPredicates( self ):
        
        predicates = ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_NOTES, ( self._sign.GetStringSelection(), self._num_notes.value() ) ), )
        
        return predicates
        
    
class PanelPredicateSystemNumWords( PanelPredicateSystemSingle ):
    
    def __init__( self, parent, predicate ):
        
        PanelPredicateSystemSingle.__init__( self, parent )
        
        self._sign = QP.RadioBox( self, choices=['<',CC.UNICODE_ALMOST_EQUAL_TO,'=',CC.UNICODE_NOT_EQUAL_TO,'>'] )
        
        self._num_words = QP.MakeQSpinBox( self, max=1000000, width = 60 )
        
        #
        
        predicate = self._GetPredicateToInitialisePanelWith( predicate )
        
        ( sign, num_words ) = predicate.GetValue()
        
        self._sign.SetStringSelection( sign )
        
        self._num_words.setValue( num_words )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:number of words'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._num_words, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetDefaultPredicate( self ):
        
        sign = '<'
        num_words = 30000
        
        return ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_WORDS, ( sign, num_words ) )
        
    
    def GetPredicates( self ):
        
        predicates = ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_WORDS, ( self._sign.GetStringSelection(), self._num_words.value() ) ), )
        
        return predicates
        
    
class PanelPredicateSystemRatio( PanelPredicateSystemSingle ):
    
    def __init__( self, parent, predicate ):
        
        PanelPredicateSystemSingle.__init__( self, parent )
        
        self._sign = QP.RadioBox( self, choices=['=','wider than','taller than',CC.UNICODE_ALMOST_EQUAL_TO,CC.UNICODE_NOT_EQUAL_TO] )
        
        self._width = QP.MakeQSpinBox( self, max=50000, width = 60 )
        
        self._height = QP.MakeQSpinBox( self, max=50000, width = 60 )
        
        #
        
        predicate = self._GetPredicateToInitialisePanelWith( predicate )
        
        ( sign, width, height ) = predicate.GetValue()
        
        self._sign.SetStringSelection( sign )
        
        self._width.setValue( width )
        
        self._height.setValue( height )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:ratio'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._width, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,':'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._height, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetDefaultPredicate( self ):
        
        sign = 'wider than'
        width = 16
        height = 9
        
        return ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_RATIO, ( sign, width, height ) )
        
    
    def GetPredicates( self ):
        
        predicates = ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_RATIO, ( self._sign.GetStringSelection(), self._width.value(), self._height.value() ) ), )
        
        return predicates
        
    
class PanelPredicateSystemSimilarTo( PanelPredicateSystemSingle ):
    
    def __init__( self, parent, predicate ):
        
        PanelPredicateSystemSingle.__init__( self, parent )
        
        self._hashes = QW.QPlainTextEdit( self )
        
        ( init_width, init_height ) = ClientGUIFunctions.ConvertTextToPixels( self._hashes, ( 66, 10 ) )
        
        self._hashes.setMinimumSize( QC.QSize( init_width, init_height ) )
        
        self._max_hamming = QP.MakeQSpinBox( self, max=256, width = 60 )
        
        #
        
        predicate = self._GetPredicateToInitialisePanelWith( predicate )
        
        self._hashes.setPlaceholderText( 'enter hash (paste newline-separated for multiple hashes)' )
        
        ( hashes, hamming_distance ) = predicate.GetValue()
        
        hashes_text = os.linesep.join( [ hash.hex() for hash in hashes ] )
        
        self._hashes.setPlainText( hashes_text )
        
        self._max_hamming.setValue( hamming_distance )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:similar_to'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._hashes, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, QW.QLabel( CC.UNICODE_ALMOST_EQUAL_TO, self ), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._max_hamming, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetDefaultPredicate( self ):
        
        hashes = tuple()
        max_hamming = 4
        
        return ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_SIMILAR_TO, ( hashes, max_hamming ) )
        
    
    def GetPredicates( self ):
        
        hex_hashes_raw = self._hashes.toPlainText()
        
        hashes = HydrusData.ParseHashesFromRawHexText( 'sha256', hex_hashes_raw )
        
        predicates = ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_SIMILAR_TO, ( hashes, self._max_hamming.value() ) ), )
        
        return predicates
        
    
class PanelPredicateSystemSize( PanelPredicateSystemSingle ):
    
    def __init__( self, parent, predicate ):
        
        PanelPredicateSystemSingle.__init__( self, parent )
        
        self._sign = QP.RadioBox( self, choices=['<',CC.UNICODE_ALMOST_EQUAL_TO,'=',CC.UNICODE_NOT_EQUAL_TO,'>'] )
        
        self._bytes = ClientGUIControls.BytesControl( self )
        
        #
        
        predicate = self._GetPredicateToInitialisePanelWith( predicate )
        
        ( sign, size, unit ) = predicate.GetValue()
        
        self._sign.SetStringSelection( sign )
        
        self._bytes.SetSeparatedValue( size, unit )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:filesize'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._bytes, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetDefaultPredicate( self ):
        
        sign = '<'
        size = 200
        unit = 1024
        
        return ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_SIZE, ( sign, size, unit ) )
        
    
    def GetPredicates( self ):
        
        ( size, unit ) = self._bytes.GetSeparatedValue()
        
        predicates = ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_SIZE, ( self._sign.GetStringSelection(), size, unit ) ), )
        
        return predicates
        
    
class PanelPredicateSystemTagAsNumber( PanelPredicateSystemSingle ):
    
    def __init__( self, parent, predicate ):
        
        PanelPredicateSystemSingle.__init__( self, parent )
        
        self._namespace = QW.QLineEdit( self )
        
        choices = [ '<', CC.UNICODE_ALMOST_EQUAL_TO, '>' ]
        
        self._sign = QP.RadioBox( self, choices = choices )
        
        self._num = QP.MakeQSpinBox( self, min=-(2**31), max=(2**31)-1 )
        
        #
        
        predicate = self._GetPredicateToInitialisePanelWith( predicate )
        
        ( namespace, sign, num ) = predicate.GetValue()
        
        self._namespace.setText( namespace )
        self._sign.SetStringSelection( sign )
        self._num.setValue( num )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:tag as number'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._namespace, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._num, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetDefaultPredicate( self ):
        
        namespace = 'page'
        sign = '>'
        num = 0
        
        return ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_TAG_AS_NUMBER, ( namespace, sign, num ) )
        
    
    def GetPredicates( self ):
        
        predicates = ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_TAG_AS_NUMBER, ( self._namespace.text(), self._sign.GetStringSelection(), self._num.value() ) ), )
        
        return predicates
        
    
class PanelPredicateSystemWidth( PanelPredicateSystemSingle ):
    
    def __init__( self, parent, predicate ):
        
        PanelPredicateSystemSingle.__init__( self, parent )
        
        self._sign = QP.RadioBox( self, choices=['<',CC.UNICODE_ALMOST_EQUAL_TO,'=',CC.UNICODE_NOT_EQUAL_TO,'>'] )
        
        self._width = QP.MakeQSpinBox( self, max=200000, width = 60 )
        
        #
        
        predicate = self._GetPredicateToInitialisePanelWith( predicate )
        
        ( sign, width ) = predicate.GetValue()
        
        self._sign.SetStringSelection( sign )
        
        self._width.setValue( width )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:width'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._width, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetDefaultPredicate( self ):
        
        sign = '='
        width = 1920
        
        return ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_WIDTH, ( sign, width ) )
        
    
    def GetPredicates( self ):
        
        predicates = ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_WIDTH, ( self._sign.GetStringSelection(), self._width.value() ) ), )
        
        return predicates
        
    
