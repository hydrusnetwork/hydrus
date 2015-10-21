import ClientConstants as CC
import ClientData
import ClientGUICommon
import ClientGUIOptionsPanels
import ClientRatings
import HydrusConstants as HC
import HydrusData
import HydrusGlobals
import string
import wx

class PanelPredicateSystem( wx.Panel ):
    
    PREDICATE_TYPE = None
    
    def GetInfo( self ):
        
        raise NotImplementedError()
        
    
    def GetPredicates( self ):
        
        info = self.GetInfo()
        
        predicates = ( ClientData.Predicate( self.PREDICATE_TYPE, info ), )
        
        return predicates
        
    
class PanelPredicateSystemAge( PanelPredicateSystem ):
    
    PREDICATE_TYPE = HC.PREDICATE_TYPE_SYSTEM_AGE
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._sign = wx.Choice( self, choices=[ '<', u'\u2248', '>' ] )
        
        self._years = wx.SpinCtrl( self, max = 30, size = ( 60, -1 ) )
        self._months = wx.SpinCtrl( self, max = 60, size = ( 60, -1 ) )
        self._days = wx.SpinCtrl( self, max = 90, size = ( 60, -1 ) )
        self._hours = wx.SpinCtrl( self, max = 24, size = ( 60, -1 ) )
        
        system_predicates = HC.options[ 'file_system_predicates' ]
        
        ( sign, years, months, days, hours ) = system_predicates[ 'age' ]
        
        self._sign.SetStringSelection( sign )
        
        self._years.SetValue( years )
        self._months.SetValue( months )
        self._days.SetValue( days )
        self._hours.SetValue( hours )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.AddF( wx.StaticText( self, label = 'system:age' ), CC.FLAGS_MIXED )
        hbox.AddF( self._sign, CC.FLAGS_MIXED )
        hbox.AddF( self._years, CC.FLAGS_MIXED )
        hbox.AddF( wx.StaticText( self, label = 'years' ), CC.FLAGS_MIXED )
        hbox.AddF( self._months, CC.FLAGS_MIXED )
        hbox.AddF( wx.StaticText( self, label = 'months' ), CC.FLAGS_MIXED )
        hbox.AddF( self._days, CC.FLAGS_MIXED )
        hbox.AddF( wx.StaticText( self, label = 'days' ), CC.FLAGS_MIXED )
        hbox.AddF( self._hours, CC.FLAGS_MIXED )
        hbox.AddF( wx.StaticText( self, label = 'hours' ), CC.FLAGS_MIXED )
        
        self.SetSizer( hbox )
        
        wx.CallAfter( self._days.SetFocus )
        
    
    def GetInfo( self ):
        
        info = ( self._sign.GetStringSelection(), self._years.GetValue(), self._months.GetValue(), self._days.GetValue(), self._hours.GetValue() )
        
        return info
        
    
class PanelPredicateSystemDuration( PanelPredicateSystem ):
    
    PREDICATE_TYPE = HC.PREDICATE_TYPE_SYSTEM_DURATION
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._sign = wx.Choice( self, choices=[ '<', u'\u2248', '=', '>' ] )
        
        self._duration_s = wx.SpinCtrl( self, max = 3599, size = ( 60, -1 ) )
        self._duration_ms = wx.SpinCtrl( self, max = 999, size = ( 60, -1 ) )
        
        system_predicates = HC.options[ 'file_system_predicates' ]
        
        ( sign, ms ) = system_predicates[ 'duration' ]
        
        s = ms / 1000
        
        ms = ms % 1000
        
        self._sign.SetStringSelection( sign )
        
        self._duration_s.SetValue( s )
        self._duration_ms.SetValue( ms )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.AddF( wx.StaticText( self, label = 'system:duration' ), CC.FLAGS_MIXED )
        hbox.AddF( self._sign, CC.FLAGS_MIXED )
        hbox.AddF( self._duration_s, CC.FLAGS_MIXED )
        hbox.AddF( wx.StaticText( self, label = 's' ), CC.FLAGS_MIXED )
        hbox.AddF( self._duration_ms, CC.FLAGS_MIXED )
        hbox.AddF( wx.StaticText( self, label = 'ms' ), CC.FLAGS_MIXED )
        
        self.SetSizer( hbox )
        
        wx.CallAfter( self._duration_s.SetFocus )
        
    
    def GetInfo( self ):
        
        info = ( self._sign.GetStringSelection(), self._duration_s.GetValue() * 1000 + self._duration_ms.GetValue() )
        
        return info
        
    
class PanelPredicateSystemFileService( PanelPredicateSystem ):
    
    PREDICATE_TYPE = HC.PREDICATE_TYPE_SYSTEM_FILE_SERVICE
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._sign = wx.Choice( self )
        self._sign.Append( 'is', True )
        self._sign.Append( 'is not', False )
        
        self._current_pending = wx.Choice( self )
        self._current_pending.Append( 'currently in', HC.CURRENT )
        self._current_pending.Append( 'pending to', HC.PENDING )
        
        self._file_service_key = wx.Choice( self )
        
        self._sign.SetSelection( 0 )
        self._current_pending.SetSelection( 0 )
        
        services = HydrusGlobals.client_controller.GetServicesManager().GetServices( ( HC.FILE_REPOSITORY, HC.LOCAL_FILE ) )
        
        for service in services: self._file_service_key.Append( service.GetName(), service.GetServiceKey() )
        self._file_service_key.SetSelection( 0 )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.AddF( wx.StaticText( self, label = 'system:file service:' ), CC.FLAGS_MIXED )
        hbox.AddF( self._sign, CC.FLAGS_MIXED )
        hbox.AddF( self._current_pending, CC.FLAGS_MIXED )
        hbox.AddF( self._file_service_key, CC.FLAGS_MIXED )
        
        self.SetSizer( hbox )
        
        wx.CallAfter( self._sign.SetFocus )
        
    
    def GetInfo( self ):
        
        info = ( self._sign.GetClientData( self._sign.GetSelection() ), self._current_pending.GetClientData( self._current_pending.GetSelection() ), self._file_service_key.GetClientData( self._file_service_key.GetSelection() ) )
        return info
        
    
class PanelPredicateSystemHash( PanelPredicateSystem ):
    
    PREDICATE_TYPE = HC.PREDICATE_TYPE_SYSTEM_HASH
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._hash = wx.TextCtrl( self )
        
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.AddF( wx.StaticText( self, label = 'system:hash=' ), CC.FLAGS_MIXED )
        hbox.AddF( self._hash, CC.FLAGS_MIXED )
        
        self.SetSizer( hbox )
        
        wx.CallAfter( self._hash.SetFocus )
        
    
    def GetInfo( self ):
        
        hex_filter = lambda c: c in string.hexdigits
        
        hash = filter( hex_filter, self._hash.GetValue().lower() )
        
        if len( hash ) == 0: hash = '00'
        elif len( hash ) % 2 == 1: hash += '0' # since we are later decoding to byte
        
        info = hash.decode( 'hex' )
        
        return info
        
    
class PanelPredicateSystemHeight( PanelPredicateSystem ):
    
    PREDICATE_TYPE = HC.PREDICATE_TYPE_SYSTEM_HEIGHT
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._sign = wx.Choice( self, choices=[ '<', u'\u2248', '=', '>' ] )
        
        self._height = wx.SpinCtrl( self, max = 200000, size = ( 60, -1 ) )
        
        system_predicates = HC.options[ 'file_system_predicates' ]
        
        ( sign, height ) = system_predicates[ 'height' ]
        
        self._sign.SetStringSelection( sign )
        
        self._height.SetValue( height )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.AddF( wx.StaticText( self, label = 'system:height' ), CC.FLAGS_MIXED )
        hbox.AddF( self._sign, CC.FLAGS_MIXED )
        hbox.AddF( self._height, CC.FLAGS_MIXED )
        
        self.SetSizer( hbox )
        
        wx.CallAfter( self._height.SetFocus )
        
    
    def GetInfo( self ):
        
        info = ( self._sign.GetStringSelection(), self._height.GetValue() )
        
        return info
        
    
class PanelPredicateSystemLimit( PanelPredicateSystem ):
    
    PREDICATE_TYPE = HC.PREDICATE_TYPE_SYSTEM_LIMIT
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._limit = wx.SpinCtrl( self, max = 1000000, size = ( 60, -1 ) )
        
        system_predicates = HC.options[ 'file_system_predicates' ]
        
        limit = system_predicates[ 'limit' ]
        
        self._limit.SetValue( limit )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.AddF( wx.StaticText( self, label = 'system:limit=' ), CC.FLAGS_MIXED )
        hbox.AddF( self._limit, CC.FLAGS_MIXED )
        
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
        
        if type( mimes ) == int:
            
            mimes = ( mimes, )
            
        
        self._mimes.SetInfo( mimes )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.AddF( wx.StaticText( self, label = 'system:mime' ), CC.FLAGS_MIXED )
        hbox.AddF( self._mimes, CC.FLAGS_MIXED )
        
        self.SetSizer( hbox )
        
    
    def GetInfo( self ):
        
        mimes = self._mimes.GetInfo()
        
        return mimes
        
    
class PanelPredicateSystemNumPixels( PanelPredicateSystem ):
    
    PREDICATE_TYPE = HC.PREDICATE_TYPE_SYSTEM_NUM_PIXELS
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._sign = wx.Choice( self, choices = [ '<', u'\u2248', '=', '>' ] )
        
        self._num_pixels = wx.SpinCtrl( self, max = 1048576, size = ( 60, -1 ) )
        
        self._unit = wx.Choice( self, choices = [ 'pixels', 'kilopixels', 'megapixels' ] )
        
        system_predicates = HC.options[ 'file_system_predicates' ]
        
        ( sign, num_pixels, unit ) = system_predicates[ 'num_pixels' ]
        
        self._sign.SetStringSelection( sign )
        
        self._num_pixels.SetValue( num_pixels )
        
        self._unit.SetStringSelection( HydrusData.ConvertIntToPixels( unit ) )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.AddF( wx.StaticText( self, label = 'system:num_pixels' ), CC.FLAGS_MIXED )
        hbox.AddF( self._sign, CC.FLAGS_MIXED )
        hbox.AddF( self._num_pixels, CC.FLAGS_MIXED )
        hbox.AddF( self._unit, CC.FLAGS_MIXED )
        
        self.SetSizer( hbox )
        
        wx.CallAfter( self._num_pixels.SetFocus )
        
    
    def GetInfo( self ):
        
        info = ( self._sign.GetStringSelection(), self._num_pixels.GetValue(), HydrusData.ConvertPixelsToInt( self._unit.GetStringSelection() ) )
        
        return info
        
    
class PanelPredicateSystemNumTags( PanelPredicateSystem ):
    
    PREDICATE_TYPE = HC.PREDICATE_TYPE_SYSTEM_NUM_TAGS
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._sign = wx.Choice( self, choices=[ '<', u'\u2248', '=', '>' ] )
        
        self._num_tags = wx.SpinCtrl( self, max = 2000, size = ( 60, -1 ) )
        
        system_predicates = HC.options[ 'file_system_predicates' ]
        
        ( sign, num_tags ) = system_predicates[ 'num_tags' ]
        
        self._sign.SetStringSelection( sign )
        
        self._num_tags.SetValue( num_tags )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.AddF( wx.StaticText( self, label = 'system:num_tags' ), CC.FLAGS_MIXED )
        hbox.AddF( self._sign, CC.FLAGS_MIXED )
        hbox.AddF( self._num_tags, CC.FLAGS_MIXED )
        
        self.SetSizer( hbox )
        
        wx.CallAfter( self._num_tags.SetFocus )
        
    
    def GetInfo( self ):
        
        info = ( self._sign.GetStringSelection(), self._num_tags.GetValue() )
        
        return info
        
    
class PanelPredicateSystemNumWords( PanelPredicateSystem ):
    
    PREDICATE_TYPE = HC.PREDICATE_TYPE_SYSTEM_NUM_WORDS
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._sign = wx.Choice( self, choices=[ '<', u'\u2248', '=', '>' ] )
        
        self._num_words = wx.SpinCtrl( self, max = 1000000, size = ( 60, -1 ) )
        
        system_predicates = HC.options[ 'file_system_predicates' ]
        
        ( sign, num_words ) = system_predicates[ 'num_words' ]
        
        self._sign.SetStringSelection( sign )
        
        self._num_words.SetValue( num_words )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.AddF( wx.StaticText( self, label = 'system:num_words' ), CC.FLAGS_MIXED )
        hbox.AddF( self._sign, CC.FLAGS_MIXED )
        hbox.AddF( self._num_words, CC.FLAGS_MIXED )
        
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
        
        local_like_services = HydrusGlobals.client_controller.GetServicesManager().GetServices( ( HC.LOCAL_RATING_LIKE, ) )
        
        self._like_checkboxes_to_info = {}
        
        self._like_rating_ctrls = []
        
        gridbox_like = wx.FlexGridSizer( 0, 4 )
        
        gridbox_like.AddGrowableCol( 0, 1 )
        
        for service in local_like_services:
            
            name = service.GetName()
            service_key = service.GetServiceKey()
            
            rated_checkbox = wx.CheckBox( self, label = 'rated' )
            not_rated_checkbox = wx.CheckBox( self, label = 'not rated' )
            rating_ctrl = ClientGUICommon.RatingLikeDialog( self, service_key )
            
            self._like_checkboxes_to_info[ rated_checkbox ] = ( service_key, ClientRatings.SET )
            self._like_checkboxes_to_info[ not_rated_checkbox ] = ( service_key, ClientRatings.NULL )
            self._like_rating_ctrls.append( rating_ctrl )
            
            gridbox_like.AddF( wx.StaticText( self, label = name ), CC.FLAGS_MIXED )
            gridbox_like.AddF( rated_checkbox, CC.FLAGS_MIXED )
            gridbox_like.AddF( not_rated_checkbox, CC.FLAGS_MIXED )
            gridbox_like.AddF( rating_ctrl, CC.FLAGS_MIXED )
            
        
        #
        
        local_numerical_services = HydrusGlobals.client_controller.GetServicesManager().GetServices( ( HC.LOCAL_RATING_NUMERICAL, ) )
        
        self._numerical_checkboxes_to_info = {}
        
        self._numerical_rating_ctrls_to_info = {}
        
        gridbox_numerical = wx.FlexGridSizer( 0, 5 )
        
        gridbox_numerical.AddGrowableCol( 0, 1 )
        
        for service in local_numerical_services:
            
            name = service.GetName()
            service_key = service.GetServiceKey()
            
            rated_checkbox = wx.CheckBox( self, label = 'rated' )
            not_rated_checkbox = wx.CheckBox( self, label = 'not rated' )
            choice = wx.Choice( self, choices=[ '>', '<', '=', u'\u2248' ] )
            rating_ctrl = ClientGUICommon.RatingNumericalDialog( self, service_key )
            
            choice.Select( 2 )
            
            self._numerical_checkboxes_to_info[ rated_checkbox ] = ( service_key, ClientRatings.SET )
            self._numerical_checkboxes_to_info[ not_rated_checkbox ] = ( service_key, ClientRatings.NULL )
            self._numerical_rating_ctrls_to_info[ rating_ctrl ] = choice
            
            gridbox_numerical.AddF( wx.StaticText( self, label = name ), CC.FLAGS_MIXED )
            gridbox_numerical.AddF( rated_checkbox, CC.FLAGS_MIXED )
            gridbox_numerical.AddF( not_rated_checkbox, CC.FLAGS_MIXED )
            gridbox_numerical.AddF( choice, CC.FLAGS_MIXED )
            gridbox_numerical.AddF( rating_ctrl, CC.FLAGS_MIXED )
            
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( gridbox_like, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        vbox.AddF( gridbox_numerical, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
    
    def GetInfo( self ):
        
        infos = []
        
        #
        
        for ( checkbox, ( service_key, rating_state ) ) in self._like_checkboxes_to_info.items():
            
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
                    
                    value = '1'
                    
                elif rating_state == ClientRatings.DISLIKE:
                    
                    value = '0'
                    
                
                service_key = ctrl.GetServiceKey()
                
                infos.append( ( '=', value, service_key ) )
                
            
        
        #
        
        for ( checkbox, ( service_key, rating_state ) ) in self._numerical_checkboxes_to_info.items():
            
            if checkbox.GetValue() == True:
                
                if rating_state == ClientRatings.SET:
                    
                    value = 'rated'
                    
                elif rating_state == ClientRatings.NULL:
                    
                    value = 'not rated'
                    
                
                infos.append( ( '=', value, service_key ) )
                
            
        
        for ( ctrl, choice ) in self._numerical_rating_ctrls_to_info.items():
            
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
        
        predicates = [ ClientData.Predicate( self.PREDICATE_TYPE, info ) for info in infos ]
        
        return predicates
        
    
class PanelPredicateSystemRatio( PanelPredicateSystem ):
    
    PREDICATE_TYPE = HC.PREDICATE_TYPE_SYSTEM_RATIO
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._sign = wx.Choice( self, choices = [ '=', u'\u2248' ] )
        
        self._width = wx.SpinCtrl( self, max = 50000, size = ( 60, -1 ) )
        
        self._height = wx.SpinCtrl( self, max = 50000, size = ( 60, -1 ) )
        
        system_predicates = HC.options[ 'file_system_predicates' ]
        
        ( sign, width, height ) = system_predicates[ 'ratio' ]
        
        self._sign.SetStringSelection( sign )
        
        self._width.SetValue( width )
        
        self._height.SetValue( height )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.AddF( wx.StaticText( self, label = 'system:ratio' ), CC.FLAGS_MIXED )
        hbox.AddF( self._sign, CC.FLAGS_MIXED )
        hbox.AddF( self._width, CC.FLAGS_MIXED )
        hbox.AddF( wx.StaticText( self, label = ':' ), CC.FLAGS_MIXED )
        hbox.AddF( self._height, CC.FLAGS_MIXED )
        
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
        
        hbox.AddF( wx.StaticText( self, label = 'system:similar_to' ), CC.FLAGS_MIXED )
        hbox.AddF( self._hash, CC.FLAGS_MIXED )
        hbox.AddF( wx.StaticText( self, label=u'\u2248' ), CC.FLAGS_MIXED )
        hbox.AddF( self._max_hamming, CC.FLAGS_MIXED )
        
        self.SetSizer( hbox )
        
        wx.CallAfter( self._hash.SetFocus )
        
    
    def GetInfo( self ):
        
        hex_filter = lambda c: c in string.hexdigits
        
        hash = filter( hex_filter, self._hash.GetValue().lower() )
        
        if len( hash ) == 0: hash = '00'
        elif len( hash ) % 2 == 1: hash += '0' # since we are later decoding to byte
        
        info = ( hash.decode( 'hex' ), self._max_hamming.GetValue() )
        
        return info
        
    
class PanelPredicateSystemSize( PanelPredicateSystem ):
    
    PREDICATE_TYPE = HC.PREDICATE_TYPE_SYSTEM_SIZE
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._sign = wx.Choice( self, choices = [ '<', u'\u2248', '=', '>' ] )
        
        self._size = wx.SpinCtrl( self, max = 1048576, size = ( 60, -1 ) )
        
        self._unit = wx.Choice( self, choices = [ 'B', 'KB', 'MB', 'GB' ] )
        
        system_predicates = HC.options[ 'file_system_predicates' ]
        
        ( sign, size, unit ) = system_predicates[ 'size' ]
        
        self._sign.SetStringSelection( sign )
        
        self._size.SetValue( size )
        
        self._unit.SetStringSelection( HydrusData.ConvertIntToUnit( unit ) )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.AddF( wx.StaticText( self, label = 'system:size' ), CC.FLAGS_MIXED )
        hbox.AddF( self._sign, CC.FLAGS_MIXED )
        hbox.AddF( self._size, CC.FLAGS_MIXED )
        hbox.AddF( self._unit, CC.FLAGS_MIXED )
        
        self.SetSizer( hbox )
        
        wx.CallAfter( self._size.SetFocus )
        
    
    def GetInfo( self ):
        
        info = ( self._sign.GetStringSelection(), self._size.GetValue(), HydrusData.ConvertUnitToInt( self._unit.GetStringSelection() ) )
        
        return info
        
    
class PanelPredicateSystemWidth( PanelPredicateSystem ):
    
    PREDICATE_TYPE = HC.PREDICATE_TYPE_SYSTEM_WIDTH
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._sign = wx.Choice( self, choices = [ '<', u'\u2248', '=', '>' ] )
        
        self._width = wx.SpinCtrl( self, max = 200000, size = ( 60, -1 ) )
        
        system_predicates = HC.options[ 'file_system_predicates' ]
        
        ( sign, width ) = system_predicates[ 'width' ]
        
        self._sign.SetStringSelection( sign )
        
        self._width.SetValue( width )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.AddF( wx.StaticText( self, label = 'system:width' ), CC.FLAGS_MIXED )
        hbox.AddF( self._sign, CC.FLAGS_MIXED )
        hbox.AddF( self._width, CC.FLAGS_MIXED )
        
        self.SetSizer( hbox )
        
        wx.CallAfter( self._width.SetFocus )
        
    
    def GetInfo( self ):
        
        info = ( self._sign.GetStringSelection(), self._width.GetValue() )
        
        return info
        
    