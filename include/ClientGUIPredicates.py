from . import ClientConstants as CC
from . import ClientData
from . import ClientGUICommon
from . import ClientGUIControls
from . import ClientGUIFunctions
from . import ClientGUIOptionsPanels
from . import ClientGUIScrolledPanels
from . import ClientGUIShortcuts
from . import ClientGUITime
from . import ClientRatings
from . import ClientSearch
import datetime
from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusGlobals as HG
from . import HydrusText
import os
import re
import string
from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG
from . import QtPorting as QP

class InputFileSystemPredicate( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, predicate_type ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._predicates = []
        
        label = None
        editable_pred_panel_classes = []
        static_pred_buttons = []
        
        if predicate_type == HC.PREDICATE_TYPE_SYSTEM_AGE:
            
            editable_pred_panel_classes.append( PanelPredicateSystemAgeDelta )
            editable_pred_panel_classes.append( PanelPredicateSystemAgeDate )
            
        elif predicate_type == HC.PREDICATE_TYPE_SYSTEM_MODIFIED_TIME:
            
            editable_pred_panel_classes.append( PanelPredicateSystemModifiedDelta )
            editable_pred_panel_classes.append( PanelPredicateSystemModifiedDate )
            
        elif predicate_type == HC.PREDICATE_TYPE_SYSTEM_DIMENSIONS:
            
            editable_pred_panel_classes.append( PanelPredicateSystemHeight )
            editable_pred_panel_classes.append( PanelPredicateSystemWidth )
            editable_pred_panel_classes.append( PanelPredicateSystemRatio )
            editable_pred_panel_classes.append( PanelPredicateSystemNumPixels )
            
        elif predicate_type == HC.PREDICATE_TYPE_SYSTEM_DURATION:
            
            static_pred_buttons.append( StaticSystemPredicateButton( self, ( ClientSearch.Predicate( HC.PREDICATE_TYPE_SYSTEM_DURATION, ( '>', 0 ) ), ) ) )
            static_pred_buttons.append( StaticSystemPredicateButton( self, ( ClientSearch.Predicate( HC.PREDICATE_TYPE_SYSTEM_DURATION, ( '=', 0 ) ), ) ) )
            
            editable_pred_panel_classes.append( PanelPredicateSystemDuration )
            
        elif predicate_type == HC.PREDICATE_TYPE_SYSTEM_FILE_SERVICE:
            
            editable_pred_panel_classes.append( PanelPredicateSystemFileService )
            
        elif predicate_type == HC.PREDICATE_TYPE_SYSTEM_KNOWN_URLS:
            
            editable_pred_panel_classes.append( PanelPredicateSystemKnownURLsExactURL )
            editable_pred_panel_classes.append( PanelPredicateSystemKnownURLsDomain )
            editable_pred_panel_classes.append( PanelPredicateSystemKnownURLsRegex )
            editable_pred_panel_classes.append( PanelPredicateSystemKnownURLsURLClass )
            
        elif predicate_type == HC.PREDICATE_TYPE_SYSTEM_HAS_AUDIO:
            
            static_pred_buttons.append( StaticSystemPredicateButton( self, ( ClientSearch.Predicate( HC.PREDICATE_TYPE_SYSTEM_HAS_AUDIO, True ), ) ) )
            static_pred_buttons.append( StaticSystemPredicateButton( self, ( ClientSearch.Predicate( HC.PREDICATE_TYPE_SYSTEM_HAS_AUDIO, False ), ) ) )
            
        elif predicate_type == HC.PREDICATE_TYPE_SYSTEM_HASH:
            
            editable_pred_panel_classes.append( PanelPredicateSystemHash )
            
        elif predicate_type == HC.PREDICATE_TYPE_SYSTEM_LIMIT:
            
            label = 'system:limit clips a large search result down to the given number of files. It is very useful for processing in smaller batches.'
            label += os.linesep * 2
            label += 'For all the simpler sorts (filesize, duration, etc...), it will select the n largest/smallest in the result set appropriate for that sort. For complicated sorts like tags, it will sample randomly.'
            
            static_pred_buttons.append( StaticSystemPredicateButton( self, ( ClientSearch.Predicate( HC.PREDICATE_TYPE_SYSTEM_LIMIT, 64 ), ) ) )
            static_pred_buttons.append( StaticSystemPredicateButton( self, ( ClientSearch.Predicate( HC.PREDICATE_TYPE_SYSTEM_LIMIT, 256 ), ) ) )
            static_pred_buttons.append( StaticSystemPredicateButton( self, ( ClientSearch.Predicate( HC.PREDICATE_TYPE_SYSTEM_LIMIT, 1024 ), ) ) )
            
            editable_pred_panel_classes.append( PanelPredicateSystemLimit )
            
        elif predicate_type == HC.PREDICATE_TYPE_SYSTEM_MIME:
            
            editable_pred_panel_classes.append( PanelPredicateSystemMime )
            
        elif predicate_type == HC.PREDICATE_TYPE_SYSTEM_NUM_TAGS:
            
            static_pred_buttons.append( StaticSystemPredicateButton( self, ( ClientSearch.Predicate( HC.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( '>', 0 ) ), ) ) )
            static_pred_buttons.append( StaticSystemPredicateButton( self, ( ClientSearch.Predicate( HC.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( '=', 0 ) ), ) ) )
            
            editable_pred_panel_classes.append( PanelPredicateSystemNumTags )
            
        elif predicate_type == HC.PREDICATE_TYPE_SYSTEM_NUM_WORDS:
            
            editable_pred_panel_classes.append( PanelPredicateSystemNumWords )
            
        elif predicate_type == HC.PREDICATE_TYPE_SYSTEM_RATING:
            
            services_manager = HG.client_controller.services_manager
            
            ratings_services = services_manager.GetServices( ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ) )
            
            if len( ratings_services ) > 0:
                
                editable_pred_panel_classes.append( PanelPredicateSystemRating )
                
            
        elif predicate_type == HC.PREDICATE_TYPE_SYSTEM_SIMILAR_TO:
            
            editable_pred_panel_classes.append( PanelPredicateSystemSimilarTo )
            
        elif predicate_type == HC.PREDICATE_TYPE_SYSTEM_SIZE:
            
            editable_pred_panel_classes.append( PanelPredicateSystemSize )
            
        elif predicate_type == HC.PREDICATE_TYPE_SYSTEM_TAG_AS_NUMBER:
            
            editable_pred_panel_classes.append( PanelPredicateSystemTagAsNumber )
            
        elif predicate_type == HC.PREDICATE_TYPE_SYSTEM_FILE_RELATIONSHIPS:
            
            editable_pred_panel_classes.append( PanelPredicateSystemDuplicateRelationships )
            editable_pred_panel_classes.append( PanelPredicateSystemDuplicateKing )
            
        elif predicate_type == HC.PREDICATE_TYPE_SYSTEM_FILE_VIEWING_STATS:
            
            editable_pred_panel_classes.append( PanelPredicateSystemFileViewingStatsViews )
            editable_pred_panel_classes.append( PanelPredicateSystemFileViewingStatsViewtime )
            
        
        vbox = QP.VBoxLayout()
        
        if label is not None:
            
            st = ClientGUICommon.BetterStaticText( self, label = label )
            
            st.setWordWrap( True )
            
            QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        for button in static_pred_buttons:
            
            QP.AddToLayout( vbox, button, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        for pred_class in editable_pred_panel_classes:
            
            panel = self._EditablePredPanel( self, pred_class )
            
            QP.AddToLayout( vbox, panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        if len( static_pred_buttons ) > 0 and len( editable_pred_panel_classes ) == 0:
            
            QP.CallAfter( static_pred_buttons[0].setFocus, QC.Qt.OtherFocusReason )
            
        
        self.widget().setLayout( vbox )
        
    
    def GetValue( self ):
        
        return self._predicates
        
    
    def SubPanelOK( self, predicates ):
        
        self._predicates = predicates
        
        self.parentWidget().DoOK()
        
    
    class _EditablePredPanel( QW.QWidget ):
        
        def __init__( self, parent, predicate_class ):
            
            QW.QWidget.__init__( self, parent )
            
            self._predicate_panel = predicate_class( self )
            self._parent = parent
            
            self._ok = QW.QPushButton( 'ok', self )
            self._ok.clicked.connect( self._DoOK )
            self._ok.setObjectName( 'HydrusAccept' )
            
            hbox = QP.HBoxLayout()
            
            QP.AddToLayout( hbox, self._predicate_panel, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            QP.AddToLayout( hbox, self._ok, CC.FLAGS_VCENTER )
            
            self.setLayout( hbox )
            
            QP.CallAfter( self._ok.setFocus, QC.Qt.OtherFocusReason )
            
        
        def _DoOK( self ):
            
            try:
                
                self._predicate_panel.CheckCanOK()
                
            except Exception as e:
                
                message = 'Cannot OK: {}'.format( e )
                
                QW.QMessageBox.warning( self, 'Warning', message )
                
                return
                
            
            predicates = self._predicate_panel.GetPredicates()
            
            self._parent.SubPanelOK( predicates )
            
        
        def keyPressEvent( self, event ):
            
            ( modifier, key ) = ClientGUIShortcuts.ConvertKeyEventToSimpleTuple( event )
            
            if key in ( QC.Qt.Key_Enter, QC.Qt.Key_Return ):
                
                self._DoOK()
                
            else:
                
                event.ignore()
                
            
        
    
class StaticSystemPredicateButton( QW.QPushButton ):
    
    def __init__( self, parent, predicates ):
        
        QW.QPushButton.__init__( self, parent )
        
        self._parent = parent
        self._predicates = predicates
        
        label = ', '.join( ( predicate.ToString() for predicate in self._predicates ) )
        
        self.setText( label )
        
        self.clicked.connect( self.DoOK )
        
    
    def DoOK( self ):
        
        self._parent.SubPanelOK( self._predicates )
        
    
class PanelPredicateSystem( QW.QWidget ):
    
    PREDICATE_TYPE = None
    
    def CheckCanOK( self ):
        
        pass
        
    
    def GetInfo( self ):
        
        raise NotImplementedError()
        
    
    def GetPredicates( self ):
        
        info = self.GetInfo()
        
        predicates = ( ClientSearch.Predicate( self.PREDICATE_TYPE, info ), )
        
        return predicates
        

class PanelPredicateSystemAgeDate( PanelPredicateSystem ):
    
    PREDICATE_TYPE = HC.PREDICATE_TYPE_SYSTEM_AGE
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._sign = QP.RadioBox( self, choices=['<','\u2248','=','>'] )
        
        self._date = QW.QCalendarWidget( self )
        
        qt_dt = QC.QDate.currentDate()
        
        qt_dt.addDays( -7 )
        
        self._date.setSelectedDate( qt_dt )
        
        self._sign.SetStringSelection( '>' )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:time imported'), CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._date, CC.FLAGS_VCENTER )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetInfo( self ):
        
        qt_dt = self._date.selectedDate()
        
        year = qt_dt.year()
        month = qt_dt.month()
        day = qt_dt.day()
        
        info = ( self._sign.GetStringSelection(), 'date', ( year, month, day ) )
        
        return info
        
    
class PanelPredicateSystemAgeDelta( PanelPredicateSystem ):
    
    PREDICATE_TYPE = HC.PREDICATE_TYPE_SYSTEM_AGE
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._sign = QP.RadioBox( self, choices=['<','\u2248','>'] )
        
        self._years = QP.MakeQSpinBox( self, max=30, width = 60 )
        self._months = QP.MakeQSpinBox( self, max=60, width = 60 )
        self._days = QP.MakeQSpinBox( self, max=90, width = 60 )
        self._hours = QP.MakeQSpinBox( self, max=24, width = 60 )
        
        system_predicates = HC.options[ 'file_system_predicates' ]
        
        try:
            
            ( sign, age_type, ( years, months, days, hours ) ) = system_predicates[ 'age' ]
            
        except:
            
            # wew lad. replace this all with proper system pred saving on new_options in future
            sign = '<'
            
            years = 0
            months = 0
            days = 7
            hours = 0
            
        
        self._sign.SetStringSelection( sign )
        
        self._years.setValue( years )
        self._months.setValue( months )
        self._days.setValue( days )
        self._hours.setValue( hours )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:time imported'), CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._years, CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'years'), CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._months, CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'months'), CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._days, CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'days'), CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._hours, CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'hours'), CC.FLAGS_VCENTER )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetInfo( self ):
        
        info = ( self._sign.GetStringSelection(), 'delta', (self._years.value(), self._months.value(), self._days.value(), self._hours.value()))
        
        return info
        
    
class PanelPredicateSystemModifiedDate( PanelPredicateSystem ):
    
    PREDICATE_TYPE = HC.PREDICATE_TYPE_SYSTEM_MODIFIED_TIME
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._sign = QP.RadioBox( self, choices=['<','\u2248','=','>'] )
        
        self._date = QW.QCalendarWidget( self )
        
        qt_dt = QC.QDate.currentDate()
        
        qt_dt.addDays( -7 )
        
        self._date.setSelectedDate( qt_dt )
        
        self._sign.SetStringSelection( '>' )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:modified date'), CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._date, CC.FLAGS_VCENTER )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetInfo( self ):
        
        qt_dt = self._date.selectedDate()
        
        year = qt_dt.year()
        month = qt_dt.month()
        day = qt_dt.day()
        
        info = ( self._sign.GetStringSelection(), 'date', ( year, month, day ) )
        
        return info
        
    
class PanelPredicateSystemModifiedDelta( PanelPredicateSystem ):
    
    PREDICATE_TYPE = HC.PREDICATE_TYPE_SYSTEM_MODIFIED_TIME
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._sign = QP.RadioBox( self, choices=['<','\u2248','>'] )
        
        self._years = QP.MakeQSpinBox( self, max=30 )
        self._months = QP.MakeQSpinBox( self, max=60 )
        self._days = QP.MakeQSpinBox( self, max=90 )
        self._hours = QP.MakeQSpinBox( self, max=24 )
        
        # wew lad. replace this all with proper system pred saving on new_options in future
        sign = '<'
        
        years = 0
        months = 0
        days = 7
        hours = 0
        
        self._sign.SetStringSelection( sign )
        
        self._years.setValue( years )
        self._months.setValue( months )
        self._days.setValue( days )
        self._hours.setValue( hours )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:modified date'), CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._years, CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'years'), CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._months, CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'months'), CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._days, CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'days'), CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._hours, CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'hours'), CC.FLAGS_VCENTER )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetInfo( self ):
        
        info = ( self._sign.GetStringSelection(), 'delta', ( self._years.value(), self._months.value(), self._days.value(), self._hours.value() ) )
        
        return info
        
    
class PanelPredicateSystemDuplicateKing( PanelPredicateSystem ):
    
    PREDICATE_TYPE = HC.PREDICATE_TYPE_SYSTEM_FILE_RELATIONSHIPS_KING
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        choices = [ 'is the best quality file of its group', 'is not the best quality file of its group' ]
        
        self._king = QP.RadioBox( self, choices = choices, vertical = True )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:'), CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._king, CC.FLAGS_VCENTER )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetInfo( self ):
        
        king_str = self._king.GetStringSelection()
        
        king = 'is the' in king_str
        
        info = king
        
        return info
        
    
class PanelPredicateSystemDuplicateRelationships( PanelPredicateSystem ):
    
    PREDICATE_TYPE = HC.PREDICATE_TYPE_SYSTEM_FILE_RELATIONSHIPS_COUNT
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        choices = [ '<', '\u2248', '=', '>' ]
        
        self._sign = QP.RadioBox( self, choices = choices )
        
        self._num = QP.MakeQSpinBox( self, min=0, max=65535 )
        
        choices = [ ( HC.duplicate_type_string_lookup[ status ], status ) for status in ( HC.DUPLICATE_MEMBER, HC.DUPLICATE_ALTERNATE, HC.DUPLICATE_FALSE_POSITIVE, HC.DUPLICATE_POTENTIAL ) ]
        
        self._dupe_type = ClientGUICommon.BetterRadioBox( self, choices = choices, vertical = True )
        
        #
        
        self._sign.SetStringSelection( '>' )
        self._num.setValue( 0 )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:num file relationships'), CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._num, CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._dupe_type, CC.FLAGS_VCENTER )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetInfo( self ):
        
        info = (self._sign.GetStringSelection(), self._num.value(), self._dupe_type.GetValue())
        
        return info
        
    
class PanelPredicateSystemDuration( PanelPredicateSystem ):
    
    PREDICATE_TYPE = HC.PREDICATE_TYPE_SYSTEM_DURATION
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        choices = [ '<', '\u2248', '=', '>' ]
        
        self._sign = QP.RadioBox( self, choices = choices )
        
        self._duration_s = QP.MakeQSpinBox( self, max=3599, width = 60 )
        self._duration_ms = QP.MakeQSpinBox( self, max=999, width = 60 )
        
        system_predicates = HC.options[ 'file_system_predicates' ]
        
        ( sign, ms ) = system_predicates[ 'duration' ]
        
        s = ms // 1000
        
        ms = ms % 1000
        
        self._sign.SetStringSelection( sign )
        
        self._duration_s.setValue( s )
        self._duration_ms.setValue( ms )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:duration'), CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._duration_s, CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'s'), CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._duration_ms, CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'ms'), CC.FLAGS_VCENTER )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetInfo( self ):
        
        info = (self._sign.GetStringSelection(), self._duration_s.value() * 1000 + self._duration_ms.value())
        
        return info
        
    
class PanelPredicateSystemFileService( PanelPredicateSystem ):
    
    PREDICATE_TYPE = HC.PREDICATE_TYPE_SYSTEM_FILE_SERVICE
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._sign = ClientGUICommon.BetterRadioBox( self, choices = [ ( 'is', True ), ( 'is not', False ) ], vertical = True )
        
        self._current_pending = ClientGUICommon.BetterRadioBox( self, choices = [ ( 'currently in', HC.CONTENT_STATUS_CURRENT ), ( 'pending to', HC.CONTENT_STATUS_PENDING ) ], vertical = True )
        
        services = HG.client_controller.services_manager.GetServices( HC.FILE_SERVICES )
        
        choices = [ ( service.GetName(), service.GetServiceKey() ) for service in services ]
        
        self._file_service_key = ClientGUICommon.BetterRadioBox( self, choices = choices, vertical = True )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:file service:'), CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._current_pending, CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._file_service_key, CC.FLAGS_VCENTER )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetInfo( self ):
        
        info = ( self._sign.GetValue(), self._current_pending.GetValue(), self._file_service_key.GetValue() )
        
        return info
        
    
class PanelPredicateSystemFileViewingStatsViews( PanelPredicateSystem ):
    
    PREDICATE_TYPE = HC.PREDICATE_TYPE_SYSTEM_FILE_VIEWING_STATS
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._viewing_locations = QP.CheckListBox( self )
        
        self._viewing_locations.Append( 'media views', 'media' )
        self._viewing_locations.Append( 'preview views', 'preview' )
        
        self._sign = QP.RadioBox( self, choices=['<','\u2248','=','>'] )
        
        self._value = QP.MakeQSpinBox( self, min=0, max=1000000 )
        
        #
        
        self._viewing_locations.Check( 0 )
        
        self._sign.Select( 3 )
        
        self._value.setValue( 10 )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:'), CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._viewing_locations, CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._value, CC.FLAGS_VCENTER )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetInfo( self ):
        
        viewing_locations = self._viewing_locations.GetChecked()
        
        if len( viewing_locations ) == 0:
            
            viewing_locations = [ 'media' ]
            
        
        sign = self._sign.GetStringSelection()
        
        value = self._value.value()
        
        info = ( 'views', tuple( viewing_locations ), sign, value )
        
        return info
        
    
class PanelPredicateSystemFileViewingStatsViewtime( PanelPredicateSystem ):
    
    PREDICATE_TYPE = HC.PREDICATE_TYPE_SYSTEM_FILE_VIEWING_STATS
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._viewing_locations = QP.CheckListBox( self )
        
        self._viewing_locations.Append( 'media viewtime', 'media' )
        self._viewing_locations.Append( 'preview viewtime', 'preview' )
        
        self._sign = QP.RadioBox( self, choices=['<','\u2248','=','>'] )
        
        self._time_delta = ClientGUITime.TimeDeltaCtrl( self, min = 0, days = True, hours = True, minutes = True, seconds = True )
        
        #
        
        self._viewing_locations.Check( 0 )
        
        self._sign.Select( 3 )
        
        self._time_delta.SetValue( 600 )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:'), CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._viewing_locations, CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._time_delta, CC.FLAGS_VCENTER )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetInfo( self ):
        
        viewing_locations = self._viewing_locations.GetChecked()
        
        if len( viewing_locations ) == 0:
            
            viewing_locations = [ 'media' ]
            
        
        sign = self._sign.GetStringSelection()
        
        time_delta = self._time_delta.GetValue()
        
        info = ( 'viewtime', tuple( viewing_locations ), sign, time_delta )
        
        return info
        
    
class PanelPredicateSystemHash( PanelPredicateSystem ):
    
    PREDICATE_TYPE = HC.PREDICATE_TYPE_SYSTEM_HASH
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._hashes = QW.QPlainTextEdit( self )
        
        ( init_width, init_height ) = ClientGUIFunctions.ConvertTextToPixels( self._hashes, ( 66, 10 ) )
        
        self._hashes.setMinimumSize( QC.QSize( init_width, init_height ) )
        
        choices = [ 'sha256', 'md5', 'sha1', 'sha512' ]
        
        self._hash_type = QP.RadioBox( self, choices = choices, vertical = True )
        
        self._hashes.setPlaceholderText( 'enter hash (paste newline-separated for multiple hashes)' )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:hash='), CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._hashes, CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._hash_type, CC.FLAGS_VCENTER )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetInfo( self ):
        
        hex_hashes_raw = self._hashes.toPlainText()
        
        hex_hashes = HydrusText.DeserialiseNewlinedTexts( hex_hashes_raw )
        
        hex_hashes = [ HydrusText.HexFilter( hex_hash ) for hex_hash in hex_hashes ]
        
        hex_hashes = HydrusData.DedupeList( hex_hashes )
        
        hashes = tuple( [ bytes.fromhex( hex_hash ) for hex_hash in hex_hashes ] )
        
        hash_type = self._hash_type.GetStringSelection()
        
        return ( hashes, hash_type )
        
    
class PanelPredicateSystemHeight( PanelPredicateSystem ):
    
    PREDICATE_TYPE = HC.PREDICATE_TYPE_SYSTEM_HEIGHT
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._sign = QP.RadioBox( self, choices=['<','\u2248','=','>'] )
        
        self._height = QP.MakeQSpinBox( self, max=200000, width = 60 )
        
        system_predicates = HC.options[ 'file_system_predicates' ]
        
        ( sign, height ) = system_predicates[ 'height' ]
        
        self._sign.SetStringSelection( sign )
        
        self._height.setValue( height )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:height'), CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._height, CC.FLAGS_VCENTER )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetInfo( self ):
        
        info = ( self._sign.GetStringSelection(), self._height.value())
        
        return info
        
    
class PanelPredicateSystemKnownURLsExactURL( PanelPredicateSystem ):
    
    PREDICATE_TYPE = HC.PREDICATE_TYPE_SYSTEM_KNOWN_URLS
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._operator = ClientGUICommon.BetterChoice( self )
        
        self._operator.addItem( 'has', True )
        self._operator.addItem( 'does not have', False )
        
        self._exact_url = QW.QLineEdit( self )
        self._exact_url.setFixedWidth( 250 )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:known url'), CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._operator, CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'exact url:'), CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._exact_url, CC.FLAGS_VCENTER )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetInfo( self ):
        
        operator = self._operator.GetValue()
        
        if operator:
            
            operator_description = 'has url: '
            
        else:
            
            operator_description = 'does not have url: '
            
        
        rule_type = 'exact_match'
        
        exact_url = self._exact_url.text()
        
        rule = exact_url
        
        description = operator_description + exact_url
        
        return ( operator, rule_type, rule, description )
        
    
class PanelPredicateSystemKnownURLsDomain( PanelPredicateSystem ):
    
    PREDICATE_TYPE = HC.PREDICATE_TYPE_SYSTEM_KNOWN_URLS
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._operator = ClientGUICommon.BetterChoice( self )
        
        self._operator.addItem( 'has', True )
        self._operator.addItem( 'does not have', False )
        
        self._domain = QW.QLineEdit( self )
        self._domain.setFixedWidth( 250 )
        
        self._domain.setPlaceholderText( 'example.com' )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:known url'), CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._operator, CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'a url with domain:'), CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._domain, CC.FLAGS_VCENTER )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetInfo( self ):
        
        operator = self._operator.GetValue()
        
        if operator:
            
            operator_description = 'has a url with domain: '
            
        else:
            
            operator_description = 'does not have a url with domain: '
            
        
        rule_type = 'domain'
        
        domain = self._domain.text()
        
        rule = domain
        
        description = operator_description + domain
        
        return ( operator, rule_type, rule, description )
        
    
class PanelPredicateSystemKnownURLsRegex( PanelPredicateSystem ):
    
    PREDICATE_TYPE = HC.PREDICATE_TYPE_SYSTEM_KNOWN_URLS
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._operator = ClientGUICommon.BetterChoice( self )
        
        self._operator.addItem( 'has', True )
        self._operator.addItem( 'does not have', False )
        
        self._regex = QW.QLineEdit( self )
        self._regex.setFixedWidth( 250 )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:known url'), CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._operator, CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'a url that matches this regex:'), CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._regex, CC.FLAGS_VCENTER )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def CheckCanOK( self ):
        
        regex = self._regex.text()
        
        try:
            
            re.compile( regex )
            
        except Exception as e:
            
            raise Exception( 'Cannot compile that regex: {}'.format( e ) )
            
        
    
    def GetInfo( self ):
        
        operator = self._operator.GetValue()
        
        if operator:
            
            operator_description = 'has a url matching regex: '
            
        else:
            
            operator_description = 'does not have a url matching regex: '
            
        
        rule_type = 'regex'
        
        regex = self._regex.text()
        
        rule = regex
        
        description = operator_description + regex
        
        return ( operator, rule_type, rule, description )
        
    
class PanelPredicateSystemKnownURLsURLClass( PanelPredicateSystem ):
    
    PREDICATE_TYPE = HC.PREDICATE_TYPE_SYSTEM_KNOWN_URLS
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._operator = ClientGUICommon.BetterChoice( self )
        
        self._operator.addItem( 'has', True )
        self._operator.addItem( 'does not have', False )
        
        self._url_classes = ClientGUICommon.BetterChoice( self )
        
        for url_class in HG.client_controller.network_engine.domain_manager.GetURLClasses():
            
            if url_class.ShouldAssociateWithFiles():
                
                self._url_classes.addItem( url_class.GetName(), url_class )
                
            
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:known url'), CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._operator, CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'url matching this class:'), CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._url_classes, CC.FLAGS_VCENTER )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetInfo( self ):
        
        operator = self._operator.GetValue()
        
        if operator:
            
            operator_description = 'has '
            
        else:
            
            operator_description = 'does not have '
            
        
        rule_type = 'url_class'
        
        url_class = self._url_classes.GetValue()
        
        rule = url_class
        
        description = operator_description + url_class.GetName() + ' url'
        
        return ( operator, rule_type, rule, description )
        
    
class PanelPredicateSystemLimit( PanelPredicateSystem ):
    
    PREDICATE_TYPE = HC.PREDICATE_TYPE_SYSTEM_LIMIT
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._limit = QP.MakeQSpinBox( self, max=1000000, width = 60 )
        
        system_predicates = HC.options[ 'file_system_predicates' ]
        
        limit = system_predicates[ 'limit' ]
        
        self._limit.setValue( limit )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:limit='), CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._limit, CC.FLAGS_VCENTER )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetInfo( self ):
        
        info = self._limit.value()
        
        return info
        
    
class PanelPredicateSystemMime( PanelPredicateSystem ):
    
    PREDICATE_TYPE = HC.PREDICATE_TYPE_SYSTEM_MIME
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._mimes = ClientGUIOptionsPanels.OptionsPanelMimes( self, HC.SEARCHABLE_MIMES )
        
        system_predicates = HC.options[ 'file_system_predicates' ]
        
        mimes = system_predicates[ 'mime' ]
        
        if isinstance( mimes, int ):
            
            mimes = ( mimes, )
            
        
        self._mimes.SetValue( mimes )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText( self, 'system:filetype' ), CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._mimes, CC.FLAGS_VCENTER )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetInfo( self ):
        
        mimes = self._mimes.GetValue()
        
        return mimes
        
    
class PanelPredicateSystemNumPixels( PanelPredicateSystem ):
    
    PREDICATE_TYPE = HC.PREDICATE_TYPE_SYSTEM_NUM_PIXELS
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._sign = QP.RadioBox( self, choices=['<','\u2248','=','>'] )
        
        self._num_pixels = QP.MakeQSpinBox( self, max=1048576, width = 60 )
        
        self._unit = QP.RadioBox( self, choices=['pixels','kilopixels','megapixels'] )
        
        system_predicates = HC.options[ 'file_system_predicates' ]
        
        ( sign, num_pixels, unit ) = system_predicates[ 'num_pixels' ]
        
        self._sign.SetStringSelection( sign )
        
        self._num_pixels.setValue( num_pixels )
        
        self._unit.SetStringSelection( HydrusData.ConvertIntToPixels( unit ) )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:num_pixels'), CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._num_pixels, CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._unit, CC.FLAGS_VCENTER )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetInfo( self ):
        
        info = (self._sign.GetStringSelection(), self._num_pixels.value(), HydrusData.ConvertPixelsToInt( self._unit.GetStringSelection() ))
        
        return info
        
    
class PanelPredicateSystemNumTags( PanelPredicateSystem ):
    
    PREDICATE_TYPE = HC.PREDICATE_TYPE_SYSTEM_NUM_TAGS
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._sign = QP.RadioBox( self, choices=['<','\u2248','=','>'] )
        
        self._num_tags = QP.MakeQSpinBox( self, max=2000, width = 60 )
        
        system_predicates = HC.options[ 'file_system_predicates' ]
        
        ( sign, num_tags ) = system_predicates[ 'num_tags' ]
        
        self._sign.SetStringSelection( sign )
        
        self._num_tags.setValue( num_tags )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:num_tags'), CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._num_tags, CC.FLAGS_VCENTER )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetInfo( self ):
        
        info = ( self._sign.GetStringSelection(), self._num_tags.value())
        
        return info
        
    
class PanelPredicateSystemNumWords( PanelPredicateSystem ):
    
    PREDICATE_TYPE = HC.PREDICATE_TYPE_SYSTEM_NUM_WORDS
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._sign = QP.RadioBox( self, choices=['<','\u2248','=','>'] )
        
        self._num_words = QP.MakeQSpinBox( self, max=1000000, width = 60 )
        
        system_predicates = HC.options[ 'file_system_predicates' ]
        
        ( sign, num_words ) = system_predicates[ 'num_words' ]
        
        self._sign.SetStringSelection( sign )
        
        self._num_words.setValue( num_words )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:num_words'), CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._num_words, CC.FLAGS_VCENTER )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetInfo( self ):
        
        info = ( self._sign.GetStringSelection(), self._num_words.value())
        
        return info
        
    
class PanelPredicateSystemRating( PanelPredicateSystem ):
    
    PREDICATE_TYPE = HC.PREDICATE_TYPE_SYSTEM_RATING
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        #
        
        local_like_services = HG.client_controller.services_manager.GetServices( ( HC.LOCAL_RATING_LIKE, ), randomised = False )
        
        self._like_checkboxes_to_info = {}
        
        self._like_rating_ctrls = []
        
        gridbox = QP.GridLayout( cols = 5 )
        
        gridbox.setColumnStretch( 0, 1 )
        
        for service in local_like_services:
            
            name = service.GetName()
            service_key = service.GetServiceKey()
            
            rated_checkbox = QW.QCheckBox( 'rated', self )
            not_rated_checkbox = QW.QCheckBox( 'not rated', self )
            rating_ctrl = ClientGUICommon.RatingLikeDialog( self, service_key )
            
            self._like_checkboxes_to_info[ rated_checkbox ] = ( service_key, ClientRatings.SET )
            self._like_checkboxes_to_info[ not_rated_checkbox ] = ( service_key, ClientRatings.NULL )
            self._like_rating_ctrls.append( rating_ctrl )
            
            QP.AddToLayout( gridbox, ClientGUICommon.BetterStaticText(self,name), CC.FLAGS_VCENTER )
            QP.AddToLayout( gridbox, rated_checkbox, CC.FLAGS_VCENTER )
            QP.AddToLayout( gridbox, not_rated_checkbox, CC.FLAGS_VCENTER )
            QP.AddToLayout( gridbox, (20,20), CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            QP.AddToLayout( gridbox, rating_ctrl, CC.FLAGS_VCENTER )
            
        
        #
        
        local_numerical_services = HG.client_controller.services_manager.GetServices( ( HC.LOCAL_RATING_NUMERICAL, ), randomised = False )
        
        self._numerical_checkboxes_to_info = {}
        
        self._numerical_rating_ctrls_to_info = {}
        
        for service in local_numerical_services:
            
            name = service.GetName()
            service_key = service.GetServiceKey()
            
            rated_checkbox = QW.QCheckBox( 'rated', self )
            not_rated_checkbox = QW.QCheckBox( 'not rated', self )
            choice = QP.RadioBox( self, choices=['>','<','=','\u2248'] )
            rating_ctrl = ClientGUICommon.RatingNumericalDialog( self, service_key )
            
            choice.Select( 2 )
            
            self._numerical_checkboxes_to_info[ rated_checkbox ] = ( service_key, ClientRatings.SET )
            self._numerical_checkboxes_to_info[ not_rated_checkbox ] = ( service_key, ClientRatings.NULL )
            self._numerical_rating_ctrls_to_info[ rating_ctrl ] = choice
            
            QP.AddToLayout( gridbox, ClientGUICommon.BetterStaticText(self,name), CC.FLAGS_VCENTER )
            QP.AddToLayout( gridbox, rated_checkbox, CC.FLAGS_VCENTER )
            QP.AddToLayout( gridbox, not_rated_checkbox, CC.FLAGS_VCENTER )
            QP.AddToLayout( gridbox, choice, CC.FLAGS_VCENTER )
            QP.AddToLayout( gridbox, rating_ctrl, CC.FLAGS_VCENTER )
            
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.setLayout( vbox )
        
    
    def GetInfo( self ):
        
        infos = []
        
        #
        
        for ( checkbox, ( service_key, rating_state ) ) in list(self._like_checkboxes_to_info.items()):
            
            if checkbox.isChecked():
                
                if rating_state == ClientRatings.SET:
                    
                    value = 'rated'
                    
                elif rating_state == ClientRatings.NULL:
                    
                    value = 'not rated'
                    
                
                infos.append( ( '=', value, service_key ) )
                
            
        
        for ctrl in self._like_rating_ctrls:
            
            rating_state = ctrl.GetRatingState()
            
            if rating_state in ( ClientRatings.LIKE, ClientRatings.DISLIKE ):
                
                if rating_state == ClientRatings.LIKE:
                    
                    value = 1
                    
                elif rating_state == ClientRatings.DISLIKE:
                    
                    value = 0
                    
                
                service_key = ctrl.GetServiceKey()
                
                infos.append( ( '=', value, service_key ) )
                
            
        
        #
        
        for ( checkbox, ( service_key, rating_state ) ) in list(self._numerical_checkboxes_to_info.items()):
            
            if checkbox.isChecked():
                
                if rating_state == ClientRatings.SET:
                    
                    value = 'rated'
                    
                elif rating_state == ClientRatings.NULL:
                    
                    value = 'not rated'
                    
                
                infos.append( ( '=', value, service_key ) )
                
            
        
        for ( ctrl, choice ) in list(self._numerical_rating_ctrls_to_info.items()):
            
            rating_state = ctrl.GetRatingState()
            
            if rating_state == ClientRatings.SET:
                
                operator = choice.GetStringSelection()
                
                value = ctrl.GetRating()
                
                service_key = ctrl.GetServiceKey()
                
                infos.append( ( operator, value, service_key ) )
                
            
        
        #
        
        return infos
        
    
    def GetPredicates( self ):
        
        infos = self.GetInfo()
        
        predicates = [ ClientSearch.Predicate( self.PREDICATE_TYPE, info ) for info in infos ]
        
        return predicates
        
    
class PanelPredicateSystemRatio( PanelPredicateSystem ):
    
    PREDICATE_TYPE = HC.PREDICATE_TYPE_SYSTEM_RATIO
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._sign = QP.RadioBox( self, choices=['=','wider than','taller than','\u2248'] )
        
        self._width = QP.MakeQSpinBox( self, max=50000, width = 60 )
        
        self._height = QP.MakeQSpinBox( self, max=50000, width = 60 )
        
        system_predicates = HC.options[ 'file_system_predicates' ]
        
        ( sign, width, height ) = system_predicates[ 'ratio' ]
        
        self._sign.SetStringSelection( sign )
        
        self._width.setValue( width )
        
        self._height.setValue( height )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:ratio'), CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._width, CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,':'), CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._height, CC.FLAGS_VCENTER )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetInfo( self ):
        
        info = (self._sign.GetStringSelection(), self._width.value(), self._height.value())
        
        return info
        
    
class PanelPredicateSystemSimilarTo( PanelPredicateSystem ):
    
    PREDICATE_TYPE = HC.PREDICATE_TYPE_SYSTEM_SIMILAR_TO
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._hashes = QW.QPlainTextEdit( self )
        
        ( init_width, init_height ) = ClientGUIFunctions.ConvertTextToPixels( self._hashes, ( 66, 10 ) )
        
        self._hashes.setMinimumSize( QC.QSize( init_width, init_height ) )
        
        self._max_hamming = QP.MakeQSpinBox( self, max=256, width = 60 )
        
        system_predicates = HC.options[ 'file_system_predicates' ]
        
        self._hashes.setPlaceholderText( 'enter hash (paste newline-separated for multiple hashes)' )
        
        hamming_distance = system_predicates[ 'hamming_distance' ]
        
        self._max_hamming.setValue( hamming_distance )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:similar_to'), CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._hashes, CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, QW.QLabel( '\u2248', self ), CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._max_hamming, CC.FLAGS_VCENTER )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetInfo( self ):
        
        hex_hashes_raw = self._hashes.toPlainText()
        
        hex_hashes = HydrusText.DeserialiseNewlinedTexts( hex_hashes_raw )
        
        hex_hashes = [ HydrusText.HexFilter( hex_hash ) for hex_hash in hex_hashes ]
        
        hex_hashes = HydrusData.DedupeList( hex_hashes )
        
        hashes = tuple( [ bytes.fromhex( hex_hash ) for hex_hash in hex_hashes ] )
        
        info = ( hashes, self._max_hamming.value())
        
        return info
        
    
class PanelPredicateSystemSize( PanelPredicateSystem ):
    
    PREDICATE_TYPE = HC.PREDICATE_TYPE_SYSTEM_SIZE
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._sign = QP.RadioBox( self, choices=['<','\u2248','=','>'] )
        
        self._bytes = ClientGUIControls.BytesControl( self )
        
        system_predicates = HC.options[ 'file_system_predicates' ]
        
        ( sign, size, unit ) = system_predicates[ 'size' ]
        
        self._sign.SetStringSelection( sign )
        
        self._bytes.SetSeparatedValue( size, unit )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:filesize'), CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._bytes, CC.FLAGS_VCENTER )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetInfo( self ):
        
        ( size, unit ) = self._bytes.GetSeparatedValue()
        
        info = ( self._sign.GetStringSelection(), size, unit )
        
        return info
        
    
class PanelPredicateSystemTagAsNumber( PanelPredicateSystem ):
    
    PREDICATE_TYPE = HC.PREDICATE_TYPE_SYSTEM_TAG_AS_NUMBER
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._namespace = QW.QLineEdit( self )
        
        choices = [ '<', '\u2248', '>' ]
        
        self._sign = QP.RadioBox( self, choices = choices )
        
        self._num = QP.MakeQSpinBox( self, min=-99999999, max=99999999 )
        
        #
        
        self._namespace.setText( 'page' )
        self._sign.SetStringSelection( '>' )
        self._num.setValue( 0 )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:tag as number'), CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._namespace, CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._num, CC.FLAGS_VCENTER )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetInfo( self ):
        
        info = ( self._namespace.text(), self._sign.GetStringSelection(), self._num.value())
        
        return info
        
    
class PanelPredicateSystemWidth( PanelPredicateSystem ):
    
    PREDICATE_TYPE = HC.PREDICATE_TYPE_SYSTEM_WIDTH
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._sign = QP.RadioBox( self, choices=['<','\u2248','=','>'] )
        
        self._width = QP.MakeQSpinBox( self, max=200000, width = 60 )
        
        system_predicates = HC.options[ 'file_system_predicates' ]
        
        ( sign, width ) = system_predicates[ 'width' ]
        
        self._sign.SetStringSelection( sign )
        
        self._width.setValue( width )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:width'), CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._width, CC.FLAGS_VCENTER )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetInfo( self ):
        
        info = ( self._sign.GetStringSelection(), self._width.value())
        
        return info
        
    
