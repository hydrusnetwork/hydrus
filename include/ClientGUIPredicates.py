from . import ClientConstants as CC
from . import ClientData
from . import ClientGUICommon
from . import ClientGUIControls
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
import re
import string
import wx
import wx.adv

class InputFileSystemPredicate( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, predicate_type ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._predicates = []
        
        pred_classes = []
        
        if predicate_type == HC.PREDICATE_TYPE_SYSTEM_AGE:
            
            pred_classes.append( PanelPredicateSystemAgeDelta )
            pred_classes.append( PanelPredicateSystemAgeDate )
            
        elif predicate_type == HC.PREDICATE_TYPE_SYSTEM_DIMENSIONS:
            
            pred_classes.append( PanelPredicateSystemHeight )
            pred_classes.append( PanelPredicateSystemWidth )
            pred_classes.append( PanelPredicateSystemRatio )
            pred_classes.append( PanelPredicateSystemNumPixels )
            
        elif predicate_type == HC.PREDICATE_TYPE_SYSTEM_DURATION:
            
            pred_classes.append( PanelPredicateSystemDuration )
            
        elif predicate_type == HC.PREDICATE_TYPE_SYSTEM_FILE_SERVICE:
            
            pred_classes.append( PanelPredicateSystemFileService )
            
        elif predicate_type == HC.PREDICATE_TYPE_SYSTEM_KNOWN_URLS:
            
            pred_classes.append( PanelPredicateSystemKnownURLsExactURL )
            pred_classes.append( PanelPredicateSystemKnownURLsDomain )
            pred_classes.append( PanelPredicateSystemKnownURLsRegex )
            pred_classes.append( PanelPredicateSystemKnownURLsURLClass )
            
        elif predicate_type == HC.PREDICATE_TYPE_SYSTEM_HASH:
            
            pred_classes.append( PanelPredicateSystemHash )
            
        elif predicate_type == HC.PREDICATE_TYPE_SYSTEM_LIMIT:
            
            pred_classes.append( PanelPredicateSystemLimit )
            
        elif predicate_type == HC.PREDICATE_TYPE_SYSTEM_MIME:
            
            pred_classes.append( PanelPredicateSystemMime )
            
        elif predicate_type == HC.PREDICATE_TYPE_SYSTEM_NUM_TAGS:
            
            pred_classes.append( PanelPredicateSystemNumTags )
            
        elif predicate_type == HC.PREDICATE_TYPE_SYSTEM_NUM_WORDS:
            
            pred_classes.append( PanelPredicateSystemNumWords )
            
        elif predicate_type == HC.PREDICATE_TYPE_SYSTEM_RATING:
            
            services_manager = HG.client_controller.services_manager
            
            ratings_services = services_manager.GetServices( ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ) )
            
            if len( ratings_services ) > 0:
                
                pred_classes.append( PanelPredicateSystemRating )
                
            
        elif predicate_type == HC.PREDICATE_TYPE_SYSTEM_SIMILAR_TO:
            
            pred_classes.append( PanelPredicateSystemSimilarTo )
            
        elif predicate_type == HC.PREDICATE_TYPE_SYSTEM_SIZE:
            
            pred_classes.append( PanelPredicateSystemSize )
            
        elif predicate_type == HC.PREDICATE_TYPE_SYSTEM_TAG_AS_NUMBER:
            
            pred_classes.append( PanelPredicateSystemTagAsNumber )
            
        elif predicate_type == HC.PREDICATE_TYPE_SYSTEM_DUPLICATE_RELATIONSHIP_COUNT:
            
            pred_classes.append( PanelPredicateSystemDuplicateRelationships )
            
        elif predicate_type == HC.PREDICATE_TYPE_SYSTEM_FILE_VIEWING_STATS:
            
            pred_classes.append( PanelPredicateSystemFileViewingStatsViews )
            pred_classes.append( PanelPredicateSystemFileViewingStatsViewtime )
            
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        for pred_class in pred_classes:
            
            panel = self._Panel( self, pred_class )
            
            vbox.Add( panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        self.SetSizer( vbox )
        
    
    def GetValue( self ):
        
        return self._predicates
        
    
    def SubPanelOK( self, predicates ):
        
        self._predicates = predicates
        
        self.GetParent().DoOK()
        
    
    class _Panel( wx.Panel ):
        
        def __init__( self, parent, predicate_class ):
            
            wx.Panel.__init__( self, parent )
            
            self._predicate_panel = predicate_class( self )
            
            self._ok = wx.Button( self, id = wx.ID_OK, label = 'OK' )
            self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
            self._ok.SetForegroundColour( ( 0, 128, 0 ) )
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.Add( self._predicate_panel, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            hbox.Add( self._ok, CC.FLAGS_VCENTER )
            
            self.SetSizer( hbox )
            
            self.Bind( wx.EVT_CHAR_HOOK, self.EventCharHook )
            
        
        def _DoOK( self ):
            
            predicates = self._predicate_panel.GetPredicates()
            
            self.GetParent().SubPanelOK( predicates )
            
        
        def EventCharHook( self, event ):
            
            ( modifier, key ) = ClientGUIShortcuts.ConvertKeyEventToSimpleTuple( event )
            
            if key in ( wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER ):
                
                self._DoOK()
                
            else:
                
                event.Skip()
                
            
        
        def EventOK( self, event ):
            
            self._DoOK()
            
        
    
class PanelPredicateSystem( wx.Panel ):
    
    PREDICATE_TYPE = None
    
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
        
        self._sign = wx.RadioBox( self, choices = [ '<', '\u2248', '=', '>' ] )
        
        self._date = wx.adv.CalendarCtrl( self )
        
        wx_dt = wx.DateTime.Today()
        
        wx_dt.Subtract( wx.TimeSpan( 24 * 7 ) )
        
        self._date.SetDate( wx_dt )
        
        self._sign.SetStringSelection( '>' )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( ClientGUICommon.BetterStaticText( self, 'system:time imported' ), CC.FLAGS_VCENTER )
        hbox.Add( self._sign, CC.FLAGS_VCENTER )
        hbox.Add( self._date, CC.FLAGS_VCENTER )
        
        self.SetSizer( hbox )
        
    
    def GetInfo( self ):
        
        wx_dt = self._date.GetDate()
        
        year = wx_dt.year
        month = wx_dt.month + 1 # month zero indexed, wew
        day = wx_dt.day
        
        info = ( self._sign.GetStringSelection(), 'date', ( year, month, day ) )
        
        return info
        
    
class PanelPredicateSystemAgeDelta( PanelPredicateSystem ):
    
    PREDICATE_TYPE = HC.PREDICATE_TYPE_SYSTEM_AGE
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._sign = wx.RadioBox( self, choices = [ '<', '\u2248', '>' ] )
        
        self._years = wx.SpinCtrl( self, max = 30, size = ( 60, -1 ) )
        self._months = wx.SpinCtrl( self, max = 60, size = ( 60, -1 ) )
        self._days = wx.SpinCtrl( self, max = 90, size = ( 60, -1 ) )
        self._hours = wx.SpinCtrl( self, max = 24, size = ( 60, -1 ) )
        
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
        
        self._years.SetValue( years )
        self._months.SetValue( months )
        self._days.SetValue( days )
        self._hours.SetValue( hours )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( ClientGUICommon.BetterStaticText( self, 'system:time imported' ), CC.FLAGS_VCENTER )
        hbox.Add( self._sign, CC.FLAGS_VCENTER )
        hbox.Add( self._years, CC.FLAGS_VCENTER )
        hbox.Add( ClientGUICommon.BetterStaticText( self, 'years' ), CC.FLAGS_VCENTER )
        hbox.Add( self._months, CC.FLAGS_VCENTER )
        hbox.Add( ClientGUICommon.BetterStaticText( self, 'months' ), CC.FLAGS_VCENTER )
        hbox.Add( self._days, CC.FLAGS_VCENTER )
        hbox.Add( ClientGUICommon.BetterStaticText( self, 'days' ), CC.FLAGS_VCENTER )
        hbox.Add( self._hours, CC.FLAGS_VCENTER )
        hbox.Add( ClientGUICommon.BetterStaticText( self, 'hours' ), CC.FLAGS_VCENTER )
        
        self.SetSizer( hbox )
        
        wx.CallAfter( self._days.SetFocus )
        
    
    def GetInfo( self ):
        
        info = ( self._sign.GetStringSelection(), 'delta', ( self._years.GetValue(), self._months.GetValue(), self._days.GetValue(), self._hours.GetValue() ) )
        
        return info
        
    
class PanelPredicateSystemDuplicateRelationships( PanelPredicateSystem ):
    
    PREDICATE_TYPE = HC.PREDICATE_TYPE_SYSTEM_DUPLICATE_RELATIONSHIP_COUNT
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        choices = [ '<', '\u2248', '=', '>' ]
        
        self._sign = wx.RadioBox( self, choices = choices, style = wx.RA_SPECIFY_COLS )
        
        self._num = wx.SpinCtrl( self, min = 0, max = 65535 )
        
        choices = [ ( HC.duplicate_type_string_lookup[ status ], status ) for status in ( HC.DUPLICATE_MEMBER, HC.DUPLICATE_ALTERNATE, HC.DUPLICATE_FALSE_POSITIVE, HC.DUPLICATE_POTENTIAL ) ]
        
        self._dupe_type = ClientGUICommon.BetterRadioBox( self, choices = choices, style = wx.RA_SPECIFY_ROWS )
        
        #
        
        self._sign.SetStringSelection( '>' )
        self._num.SetValue( 0 )
        
        #
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( ClientGUICommon.BetterStaticText( self, 'system:num duplicate relationships' ), CC.FLAGS_VCENTER )
        hbox.Add( self._sign, CC.FLAGS_VCENTER )
        hbox.Add( self._num, CC.FLAGS_VCENTER )
        hbox.Add( self._dupe_type, CC.FLAGS_VCENTER )
        
        self.SetSizer( hbox )
        
        wx.CallAfter( self._num.SetFocus )
        
    
    def GetInfo( self ):
        
        info = ( self._sign.GetStringSelection(), self._num.GetValue(), self._dupe_type.GetChoice() )
        
        return info
        
    
class PanelPredicateSystemDuration( PanelPredicateSystem ):
    
    PREDICATE_TYPE = HC.PREDICATE_TYPE_SYSTEM_DURATION
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        choices = [ '<', '\u2248', '=', '>' ]
        
        self._sign = wx.RadioBox( self, choices = choices, style = wx.RA_SPECIFY_COLS )
        
        self._duration_s = wx.SpinCtrl( self, max = 3599, size = ( 60, -1 ) )
        self._duration_ms = wx.SpinCtrl( self, max = 999, size = ( 60, -1 ) )
        
        system_predicates = HC.options[ 'file_system_predicates' ]
        
        ( sign, ms ) = system_predicates[ 'duration' ]
        
        s = ms // 1000
        
        ms = ms % 1000
        
        self._sign.SetStringSelection( sign )
        
        self._duration_s.SetValue( s )
        self._duration_ms.SetValue( ms )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( ClientGUICommon.BetterStaticText( self, 'system:duration' ), CC.FLAGS_VCENTER )
        hbox.Add( self._sign, CC.FLAGS_VCENTER )
        hbox.Add( self._duration_s, CC.FLAGS_VCENTER )
        hbox.Add( ClientGUICommon.BetterStaticText( self, 's' ), CC.FLAGS_VCENTER )
        hbox.Add( self._duration_ms, CC.FLAGS_VCENTER )
        hbox.Add( ClientGUICommon.BetterStaticText( self, 'ms' ), CC.FLAGS_VCENTER )
        
        self.SetSizer( hbox )
        
        wx.CallAfter( self._duration_s.SetFocus )
        
    
    def GetInfo( self ):
        
        info = ( self._sign.GetStringSelection(), self._duration_s.GetValue() * 1000 + self._duration_ms.GetValue() )
        
        return info
        
    
class PanelPredicateSystemFileService( PanelPredicateSystem ):
    
    PREDICATE_TYPE = HC.PREDICATE_TYPE_SYSTEM_FILE_SERVICE
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._sign = ClientGUICommon.BetterRadioBox( self, choices = [ ( 'is', True ), ( 'is not', False ) ], style = wx.RA_SPECIFY_ROWS )
        
        self._current_pending = ClientGUICommon.BetterRadioBox( self, choices = [ ( 'currently in', HC.CONTENT_STATUS_CURRENT ), ( 'pending to', HC.CONTENT_STATUS_PENDING ) ], style = wx.RA_SPECIFY_ROWS )
        
        services = HG.client_controller.services_manager.GetServices( HC.FILE_SERVICES )
        
        choices = [ ( service.GetName(), service.GetServiceKey() ) for service in services ]
        
        self._file_service_key = ClientGUICommon.BetterRadioBox( self, choices = choices, style = wx.RA_SPECIFY_ROWS )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( ClientGUICommon.BetterStaticText( self, 'system:file service:' ), CC.FLAGS_VCENTER )
        hbox.Add( self._sign, CC.FLAGS_VCENTER )
        hbox.Add( self._current_pending, CC.FLAGS_VCENTER )
        hbox.Add( self._file_service_key, CC.FLAGS_VCENTER )
        
        self.SetSizer( hbox )
        
        wx.CallAfter( self._sign.SetFocus )
        
    
    def GetInfo( self ):
        
        info = ( self._sign.GetChoice(), self._current_pending.GetChoice(), self._file_service_key.GetChoice() )
        
        return info
        
    
class PanelPredicateSystemFileViewingStatsViews( PanelPredicateSystem ):
    
    PREDICATE_TYPE = HC.PREDICATE_TYPE_SYSTEM_FILE_VIEWING_STATS
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._viewing_locations = ClientGUICommon.BetterCheckListBox( self )
        
        self._viewing_locations.Append( 'media views', 'media' )
        self._viewing_locations.Append( 'preview views', 'preview' )
        
        self._sign = wx.RadioBox( self, choices = [ '<', '\u2248', '=', '>' ] )
        
        self._value = wx.SpinCtrl( self, min = 0, max = 1000000 )
        
        #
        
        self._viewing_locations.Check( 0 )
        
        self._sign.Select( 3 )
        
        self._value.SetValue( 10 )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( ClientGUICommon.BetterStaticText( self, 'system:' ), CC.FLAGS_VCENTER )
        hbox.Add( self._viewing_locations, CC.FLAGS_VCENTER )
        hbox.Add( self._sign, CC.FLAGS_VCENTER )
        hbox.Add( self._value, CC.FLAGS_VCENTER )
        
        self.SetSizer( hbox )
        
    
    def GetInfo( self ):
        
        viewing_locations = self._viewing_locations.GetChecked()
        
        if len( viewing_locations ) == 0:
            
            viewing_locations = [ 'media' ]
            
        
        sign = self._sign.GetStringSelection()
        
        value = self._value.GetValue()
        
        info = ( 'views', tuple( viewing_locations ), sign, value )
        
        return info
        
    
class PanelPredicateSystemFileViewingStatsViewtime( PanelPredicateSystem ):
    
    PREDICATE_TYPE = HC.PREDICATE_TYPE_SYSTEM_FILE_VIEWING_STATS
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._viewing_locations = ClientGUICommon.BetterCheckListBox( self )
        
        self._viewing_locations.Append( 'media viewtime', 'media' )
        self._viewing_locations.Append( 'preview viewtime', 'preview' )
        
        self._sign = wx.RadioBox( self, choices = [ '<', '\u2248', '=', '>' ] )
        
        self._time_delta = ClientGUITime.TimeDeltaCtrl( self, min = 0, days = True, hours = True, minutes = True, seconds = True )
        
        #
        
        self._viewing_locations.Check( 0 )
        
        self._sign.Select( 3 )
        
        self._time_delta.SetValue( 600 )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( ClientGUICommon.BetterStaticText( self, 'system:' ), CC.FLAGS_VCENTER )
        hbox.Add( self._viewing_locations, CC.FLAGS_VCENTER )
        hbox.Add( self._sign, CC.FLAGS_VCENTER )
        hbox.Add( self._time_delta, CC.FLAGS_VCENTER )
        
        self.SetSizer( hbox )
        
    
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
        
        self.SetToolTip( 'As this can only ever return one result, it overrules the active file domain and any other active predicate.' )
        
        self._hash = wx.TextCtrl( self, size = ( 200, -1 ) )
        
        choices = [ 'sha256', 'md5', 'sha1', 'sha512' ]
        
        self._hash_type = wx.RadioBox( self, choices = choices, style = wx.RA_SPECIFY_COLS )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( ClientGUICommon.BetterStaticText( self, 'system:hash=' ), CC.FLAGS_VCENTER )
        hbox.Add( self._hash, CC.FLAGS_VCENTER )
        hbox.Add( self._hash_type, CC.FLAGS_VCENTER )
        
        self.SetSizer( hbox )
        
        wx.CallAfter( self._hash.SetFocus )
        
    
    def GetInfo( self ):
        
        hex_hash = self._hash.GetValue().lower()
        
        hex_hash = HydrusText.HexFilter( hex_hash )
        
        if len( hex_hash ) == 0:
            
            hex_hash = '00'
            
        elif len( hex_hash ) % 2 == 1:
            
            hex_hash += '0' # since we are later decoding to byte
            
        
        hash = bytes.fromhex( hex_hash )
        
        hash_type = self._hash_type.GetStringSelection()
        
        return ( hash, hash_type )
        
    
class PanelPredicateSystemHeight( PanelPredicateSystem ):
    
    PREDICATE_TYPE = HC.PREDICATE_TYPE_SYSTEM_HEIGHT
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._sign = wx.RadioBox( self, choices = [ '<', '\u2248', '=', '>' ] )
        
        self._height = wx.SpinCtrl( self, max = 200000, size = ( 60, -1 ) )
        
        system_predicates = HC.options[ 'file_system_predicates' ]
        
        ( sign, height ) = system_predicates[ 'height' ]
        
        self._sign.SetStringSelection( sign )
        
        self._height.SetValue( height )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( ClientGUICommon.BetterStaticText( self, 'system:height' ), CC.FLAGS_VCENTER )
        hbox.Add( self._sign, CC.FLAGS_VCENTER )
        hbox.Add( self._height, CC.FLAGS_VCENTER )
        
        self.SetSizer( hbox )
        
        wx.CallAfter( self._height.SetFocus )
        
    
    def GetInfo( self ):
        
        info = ( self._sign.GetStringSelection(), self._height.GetValue() )
        
        return info
        
    
class PanelPredicateSystemKnownURLsExactURL( PanelPredicateSystem ):
    
    PREDICATE_TYPE = HC.PREDICATE_TYPE_SYSTEM_KNOWN_URLS
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._operator = ClientGUICommon.BetterChoice( self )
        
        self._operator.Append( 'has', True )
        self._operator.Append( 'does not have', False )
        
        self._exact_url = wx.TextCtrl( self, size = ( 250, -1 ) )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( ClientGUICommon.BetterStaticText( self, 'system:known url' ), CC.FLAGS_VCENTER )
        hbox.Add( self._operator, CC.FLAGS_VCENTER )
        hbox.Add( ClientGUICommon.BetterStaticText( self, 'exact url:' ), CC.FLAGS_VCENTER )
        hbox.Add( self._exact_url, CC.FLAGS_VCENTER )
        
        self.SetSizer( hbox )
        
    
    def GetInfo( self ):
        
        operator = self._operator.GetChoice()
        
        if operator:
            
            operator_description = 'has this url: '
            
        else:
            
            operator_description = 'does not have this url: '
            
        
        rule_type = 'regex'
        
        exact_url = self._exact_url.GetValue()
        
        rule = re.escape( exact_url )
        
        description = operator_description + exact_url
        
        return ( operator, rule_type, rule, description )
        
    
class PanelPredicateSystemKnownURLsDomain( PanelPredicateSystem ):
    
    PREDICATE_TYPE = HC.PREDICATE_TYPE_SYSTEM_KNOWN_URLS
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._operator = ClientGUICommon.BetterChoice( self )
        
        self._operator.Append( 'has', True )
        self._operator.Append( 'does not have', False )
        
        self._domain = wx.TextCtrl( self, size = ( 250, -1 ) )
        
        self._domain.SetValue( 'example.com' )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( ClientGUICommon.BetterStaticText( self, 'system:known url' ), CC.FLAGS_VCENTER )
        hbox.Add( self._operator, CC.FLAGS_VCENTER )
        hbox.Add( ClientGUICommon.BetterStaticText( self, 'a url with domain:' ), CC.FLAGS_VCENTER )
        hbox.Add( self._domain, CC.FLAGS_VCENTER )
        
        self.SetSizer( hbox )
        
    
    def GetInfo( self ):
        
        operator = self._operator.GetChoice()
        
        if operator:
            
            operator_description = 'has a url with domain: '
            
        else:
            
            operator_description = 'does not have a url with domain: '
            
        
        rule_type = 'regex'
        
        domain = self._domain.GetValue()
        
        rule = r'^https?\:\/\/(www[^\.]*\.)?' + re.escape( domain ) + r'\/.*'
        
        description = operator_description + domain
        
        return ( operator, rule_type, rule, description )
        
    
class PanelPredicateSystemKnownURLsRegex( PanelPredicateSystem ):
    
    PREDICATE_TYPE = HC.PREDICATE_TYPE_SYSTEM_KNOWN_URLS
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._operator = ClientGUICommon.BetterChoice( self )
        
        self._operator.Append( 'has', True )
        self._operator.Append( 'does not have', False )
        
        self._regex = wx.TextCtrl( self, size = ( 250, -1 ) )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( ClientGUICommon.BetterStaticText( self, 'system:known url' ), CC.FLAGS_VCENTER )
        hbox.Add( self._operator, CC.FLAGS_VCENTER )
        hbox.Add( ClientGUICommon.BetterStaticText( self, 'a url that matches this regex:' ), CC.FLAGS_VCENTER )
        hbox.Add( self._regex, CC.FLAGS_VCENTER )
        
        self.SetSizer( hbox )
        
    
    def GetInfo( self ):
        
        operator = self._operator.GetChoice()
        
        if operator:
            
            operator_description = 'has a url matching regex: '
            
        else:
            
            operator_description = 'does not have a url matching regex: '
            
        
        rule_type = 'regex'
        
        regex = self._regex.GetValue()
        
        rule = regex
        
        description = operator_description + regex
        
        return ( operator, rule_type, rule, description )
        
    
class PanelPredicateSystemKnownURLsURLClass( PanelPredicateSystem ):
    
    PREDICATE_TYPE = HC.PREDICATE_TYPE_SYSTEM_KNOWN_URLS
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._operator = ClientGUICommon.BetterChoice( self )
        
        self._operator.Append( 'has', True )
        self._operator.Append( 'does not have', False )
        
        self._url_classes = ClientGUICommon.BetterChoice( self )
        
        for url_class in HG.client_controller.network_engine.domain_manager.GetURLClasses():
            
            if url_class.ShouldAssociateWithFiles():
                
                self._url_classes.Append( url_class.GetName(), url_class )
                
            
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( ClientGUICommon.BetterStaticText( self, 'system:known url' ), CC.FLAGS_VCENTER )
        hbox.Add( self._operator, CC.FLAGS_VCENTER )
        hbox.Add( ClientGUICommon.BetterStaticText( self, 'url matching this class:' ), CC.FLAGS_VCENTER )
        hbox.Add( self._url_classes, CC.FLAGS_VCENTER )
        
        self.SetSizer( hbox )
        
    
    def GetInfo( self ):
        
        operator = self._operator.GetChoice()
        
        if operator:
            
            operator_description = 'has '
            
        else:
            
            operator_description = 'does not have '
            
        
        rule_type = 'url_class'
        
        url_class = self._url_classes.GetChoice()
        
        rule = url_class
        
        description = operator_description + url_class.GetName() + ' url'
        
        return ( operator, rule_type, rule, description )
        
    
class PanelPredicateSystemLimit( PanelPredicateSystem ):
    
    PREDICATE_TYPE = HC.PREDICATE_TYPE_SYSTEM_LIMIT
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._limit = wx.SpinCtrl( self, max = 1000000, size = ( 60, -1 ) )
        
        system_predicates = HC.options[ 'file_system_predicates' ]
        
        limit = system_predicates[ 'limit' ]
        
        self._limit.SetValue( limit )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( ClientGUICommon.BetterStaticText( self, 'system:limit=' ), CC.FLAGS_VCENTER )
        hbox.Add( self._limit, CC.FLAGS_VCENTER )
        
        self.SetSizer( hbox )
        
        wx.CallAfter( self._limit.SetFocus )
        
    
    def GetInfo( self ):
        
        info = self._limit.GetValue()
        
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
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( ClientGUICommon.BetterStaticText( self, 'system:filetype' ), CC.FLAGS_VCENTER )
        hbox.Add( self._mimes, CC.FLAGS_VCENTER )
        
        self.SetSizer( hbox )
        
    
    def GetInfo( self ):
        
        mimes = self._mimes.GetValue()
        
        return mimes
        
    
class PanelPredicateSystemNumPixels( PanelPredicateSystem ):
    
    PREDICATE_TYPE = HC.PREDICATE_TYPE_SYSTEM_NUM_PIXELS
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._sign = wx.RadioBox( self, choices = [ '<', '\u2248', '=', '>' ] )
        
        self._num_pixels = wx.SpinCtrl( self, max = 1048576, size = ( 60, -1 ) )
        
        self._unit = wx.RadioBox( self, choices = [ 'pixels', 'kilopixels', 'megapixels' ] )
        
        system_predicates = HC.options[ 'file_system_predicates' ]
        
        ( sign, num_pixels, unit ) = system_predicates[ 'num_pixels' ]
        
        self._sign.SetStringSelection( sign )
        
        self._num_pixels.SetValue( num_pixels )
        
        self._unit.SetStringSelection( HydrusData.ConvertIntToPixels( unit ) )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( ClientGUICommon.BetterStaticText( self, 'system:num_pixels' ), CC.FLAGS_VCENTER )
        hbox.Add( self._sign, CC.FLAGS_VCENTER )
        hbox.Add( self._num_pixels, CC.FLAGS_VCENTER )
        hbox.Add( self._unit, CC.FLAGS_VCENTER )
        
        self.SetSizer( hbox )
        
        wx.CallAfter( self._num_pixels.SetFocus )
        
    
    def GetInfo( self ):
        
        info = ( self._sign.GetStringSelection(), self._num_pixels.GetValue(), HydrusData.ConvertPixelsToInt( self._unit.GetStringSelection() ) )
        
        return info
        
    
class PanelPredicateSystemNumTags( PanelPredicateSystem ):
    
    PREDICATE_TYPE = HC.PREDICATE_TYPE_SYSTEM_NUM_TAGS
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._sign = wx.RadioBox( self, choices = [ '<', '\u2248', '=', '>' ] )
        
        self._num_tags = wx.SpinCtrl( self, max = 2000, size = ( 60, -1 ) )
        
        system_predicates = HC.options[ 'file_system_predicates' ]
        
        ( sign, num_tags ) = system_predicates[ 'num_tags' ]
        
        self._sign.SetStringSelection( sign )
        
        self._num_tags.SetValue( num_tags )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( ClientGUICommon.BetterStaticText( self, 'system:num_tags' ), CC.FLAGS_VCENTER )
        hbox.Add( self._sign, CC.FLAGS_VCENTER )
        hbox.Add( self._num_tags, CC.FLAGS_VCENTER )
        
        self.SetSizer( hbox )
        
        wx.CallAfter( self._num_tags.SetFocus )
        
    
    def GetInfo( self ):
        
        info = ( self._sign.GetStringSelection(), self._num_tags.GetValue() )
        
        return info
        
    
class PanelPredicateSystemNumWords( PanelPredicateSystem ):
    
    PREDICATE_TYPE = HC.PREDICATE_TYPE_SYSTEM_NUM_WORDS
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._sign = wx.RadioBox( self, choices = [ '<', '\u2248', '=', '>' ] )
        
        self._num_words = wx.SpinCtrl( self, max = 1000000, size = ( 60, -1 ) )
        
        system_predicates = HC.options[ 'file_system_predicates' ]
        
        ( sign, num_words ) = system_predicates[ 'num_words' ]
        
        self._sign.SetStringSelection( sign )
        
        self._num_words.SetValue( num_words )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( ClientGUICommon.BetterStaticText( self, 'system:num_words' ), CC.FLAGS_VCENTER )
        hbox.Add( self._sign, CC.FLAGS_VCENTER )
        hbox.Add( self._num_words, CC.FLAGS_VCENTER )
        
        self.SetSizer( hbox )
        
        wx.CallAfter( self._num_words.SetFocus )
        
    
    def GetInfo( self ):
        
        info = ( self._sign.GetStringSelection(), self._num_words.GetValue() )
        
        return info
        
    
class PanelPredicateSystemRating( PanelPredicateSystem ):
    
    PREDICATE_TYPE = HC.PREDICATE_TYPE_SYSTEM_RATING
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        #
        
        local_like_services = HG.client_controller.services_manager.GetServices( ( HC.LOCAL_RATING_LIKE, ), randomised = False )
        
        self._like_checkboxes_to_info = {}
        
        self._like_rating_ctrls = []
        
        gridbox = wx.FlexGridSizer( 5 )
        
        gridbox.AddGrowableCol( 0, 1 )
        
        for service in local_like_services:
            
            name = service.GetName()
            service_key = service.GetServiceKey()
            
            rated_checkbox = wx.CheckBox( self, label = 'rated' )
            not_rated_checkbox = wx.CheckBox( self, label = 'not rated' )
            rating_ctrl = ClientGUICommon.RatingLikeDialog( self, service_key )
            
            self._like_checkboxes_to_info[ rated_checkbox ] = ( service_key, ClientRatings.SET )
            self._like_checkboxes_to_info[ not_rated_checkbox ] = ( service_key, ClientRatings.NULL )
            self._like_rating_ctrls.append( rating_ctrl )
            
            gridbox.Add( ClientGUICommon.BetterStaticText( self, name ), CC.FLAGS_VCENTER )
            gridbox.Add( rated_checkbox, CC.FLAGS_VCENTER )
            gridbox.Add( not_rated_checkbox, CC.FLAGS_VCENTER )
            gridbox.Add( ( 20, 20 ), CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            gridbox.Add( rating_ctrl, CC.FLAGS_VCENTER )
            
        
        #
        
        local_numerical_services = HG.client_controller.services_manager.GetServices( ( HC.LOCAL_RATING_NUMERICAL, ), randomised = False )
        
        self._numerical_checkboxes_to_info = {}
        
        self._numerical_rating_ctrls_to_info = {}
        
        for service in local_numerical_services:
            
            name = service.GetName()
            service_key = service.GetServiceKey()
            
            rated_checkbox = wx.CheckBox( self, label = 'rated' )
            not_rated_checkbox = wx.CheckBox( self, label = 'not rated' )
            choice = wx.RadioBox( self, choices = [ '>', '<', '=', '\u2248' ] )
            rating_ctrl = ClientGUICommon.RatingNumericalDialog( self, service_key )
            
            choice.SetSelection( 2 )
            
            self._numerical_checkboxes_to_info[ rated_checkbox ] = ( service_key, ClientRatings.SET )
            self._numerical_checkboxes_to_info[ not_rated_checkbox ] = ( service_key, ClientRatings.NULL )
            self._numerical_rating_ctrls_to_info[ rating_ctrl ] = choice
            
            gridbox.Add( ClientGUICommon.BetterStaticText( self, name ), CC.FLAGS_VCENTER )
            gridbox.Add( rated_checkbox, CC.FLAGS_VCENTER )
            gridbox.Add( not_rated_checkbox, CC.FLAGS_VCENTER )
            gridbox.Add( choice, CC.FLAGS_VCENTER )
            gridbox.Add( rating_ctrl, CC.FLAGS_VCENTER )
            
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( gridbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
    
    def GetInfo( self ):
        
        infos = []
        
        #
        
        for ( checkbox, ( service_key, rating_state ) ) in list(self._like_checkboxes_to_info.items()):
            
            if checkbox.GetValue() == True:
                
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
            
            if checkbox.GetValue() == True:
                
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
        
        self._sign = wx.RadioBox( self, choices = [ '=', 'wider than', 'taller than', '\u2248' ] )
        
        self._width = wx.SpinCtrl( self, max = 50000, size = ( 60, -1 ) )
        
        self._height = wx.SpinCtrl( self, max = 50000, size = ( 60, -1 ) )
        
        system_predicates = HC.options[ 'file_system_predicates' ]
        
        ( sign, width, height ) = system_predicates[ 'ratio' ]
        
        self._sign.SetStringSelection( sign )
        
        self._width.SetValue( width )
        
        self._height.SetValue( height )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( ClientGUICommon.BetterStaticText( self, 'system:ratio' ), CC.FLAGS_VCENTER )
        hbox.Add( self._sign, CC.FLAGS_VCENTER )
        hbox.Add( self._width, CC.FLAGS_VCENTER )
        hbox.Add( ClientGUICommon.BetterStaticText( self, ':' ), CC.FLAGS_VCENTER )
        hbox.Add( self._height, CC.FLAGS_VCENTER )
        
        self.SetSizer( hbox )
        
        wx.CallAfter( self._sign.SetFocus )
        
    
    def GetInfo( self ):
        
        info = ( self._sign.GetStringSelection(), self._width.GetValue(), self._height.GetValue() )
        
        return info
        
    
class PanelPredicateSystemSimilarTo( PanelPredicateSystem ):
    
    PREDICATE_TYPE = HC.PREDICATE_TYPE_SYSTEM_SIMILAR_TO
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._hash = wx.TextCtrl( self )
        
        self._max_hamming = wx.SpinCtrl( self, max = 256, size = ( 60, -1 ) )
        
        system_predicates = HC.options[ 'file_system_predicates' ]
        
        self._hash.SetValue( 'enter hash' )
        
        hamming_distance = system_predicates[ 'hamming_distance' ]
        
        self._max_hamming.SetValue( hamming_distance )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( ClientGUICommon.BetterStaticText( self, 'system:similar_to' ), CC.FLAGS_VCENTER )
        hbox.Add( self._hash, CC.FLAGS_VCENTER )
        hbox.Add( wx.StaticText( self, label='\u2248' ), CC.FLAGS_VCENTER )
        hbox.Add( self._max_hamming, CC.FLAGS_VCENTER )
        
        self.SetSizer( hbox )
        
        wx.CallAfter( self._hash.SetFocus )
        
    
    def GetInfo( self ):
        
        hex_hash = self._hash.GetValue()
        
        hex_hash = HydrusText.HexFilter( hex_hash )
        
        if len( hex_hash ) == 0:
            
            hex_hash = '00'
            
        elif len( hex_hash ) % 2 == 1:
            
            hex_hash += '0' # since we are later decoding to byte
            
        
        info = ( bytes.fromhex( hex_hash ), self._max_hamming.GetValue() )
        
        return info
        
    
class PanelPredicateSystemSize( PanelPredicateSystem ):
    
    PREDICATE_TYPE = HC.PREDICATE_TYPE_SYSTEM_SIZE
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._sign = wx.RadioBox( self, choices = [ '<', '\u2248', '=', '>' ] )
        
        self._bytes = ClientGUIControls.BytesControl( self )
        
        system_predicates = HC.options[ 'file_system_predicates' ]
        
        ( sign, size, unit ) = system_predicates[ 'size' ]
        
        self._sign.SetStringSelection( sign )
        
        self._bytes.SetSeparatedValue( size, unit )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( ClientGUICommon.BetterStaticText( self, 'system:size' ), CC.FLAGS_VCENTER )
        hbox.Add( self._sign, CC.FLAGS_VCENTER )
        hbox.Add( self._bytes, CC.FLAGS_VCENTER )
        
        self.SetSizer( hbox )
        
        wx.CallAfter( self._bytes.SetFocus )
        
    
    def GetInfo( self ):
        
        ( size, unit ) = self._bytes.GetSeparatedValue()
        
        info = ( self._sign.GetStringSelection(), size, unit )
        
        return info
        
    
class PanelPredicateSystemTagAsNumber( PanelPredicateSystem ):
    
    PREDICATE_TYPE = HC.PREDICATE_TYPE_SYSTEM_TAG_AS_NUMBER
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._namespace = wx.TextCtrl( self )
        
        choices = [ '<', '\u2248', '>' ]
        
        self._sign = wx.RadioBox( self, choices = choices, style = wx.RA_SPECIFY_COLS )
        
        self._num = wx.SpinCtrl( self, min = -99999999, max = 99999999 )
        
        #
        
        self._namespace.SetValue( 'page' )
        self._sign.SetStringSelection( '>' )
        self._num.SetValue( 0 )
        
        #
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( ClientGUICommon.BetterStaticText( self, 'system:tag as number' ), CC.FLAGS_VCENTER )
        hbox.Add( self._namespace, CC.FLAGS_VCENTER )
        hbox.Add( self._sign, CC.FLAGS_VCENTER )
        hbox.Add( self._num, CC.FLAGS_VCENTER )
        
        self.SetSizer( hbox )
        
        wx.CallAfter( self._num.SetFocus )
        
    
    def GetInfo( self ):
        
        info = ( self._namespace.GetValue(), self._sign.GetStringSelection(), self._num.GetValue() )
        
        return info
        
    
class PanelPredicateSystemWidth( PanelPredicateSystem ):
    
    PREDICATE_TYPE = HC.PREDICATE_TYPE_SYSTEM_WIDTH
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._sign = wx.RadioBox( self, choices = [ '<', '\u2248', '=', '>' ] )
        
        self._width = wx.SpinCtrl( self, max = 200000, size = ( 60, -1 ) )
        
        system_predicates = HC.options[ 'file_system_predicates' ]
        
        ( sign, width ) = system_predicates[ 'width' ]
        
        self._sign.SetStringSelection( sign )
        
        self._width.SetValue( width )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( ClientGUICommon.BetterStaticText( self, 'system:width' ), CC.FLAGS_VCENTER )
        hbox.Add( self._sign, CC.FLAGS_VCENTER )
        hbox.Add( self._width, CC.FLAGS_VCENTER )
        
        self.SetSizer( hbox )
        
        wx.CallAfter( self._width.SetFocus )
        
    
    def GetInfo( self ):
        
        info = ( self._sign.GetStringSelection(), self._width.GetValue() )
        
        return info
        
    
