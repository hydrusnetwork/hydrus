import ClientConstants as CC
import HydrusConstants as HC
import HydrusData
import string
import wx

class PanelPredicateSystem( wx.Panel ):
    
    SYSTEM_PREDICATE_TYPE = None
    
    def GetInfo( self ):
        
        raise NotImplementedError()
        
    
    def GetPredicate( self ):
        
        info = self.GetInfo()
        
        predicate = HydrusData.Predicate( HC.PREDICATE_TYPE_SYSTEM, ( self.SYSTEM_PREDICATE_TYPE, info ) )
        
        return predicate
        
    
class PanelPredicateSystemAge( PanelPredicateSystem ):
    
    SYSTEM_PREDICATE_TYPE = HC.SYSTEM_PREDICATE_TYPE_AGE
    
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
    
    SYSTEM_PREDICATE_TYPE = HC.SYSTEM_PREDICATE_TYPE_DURATION
    
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
    
    SYSTEM_PREDICATE_TYPE = HC.SYSTEM_PREDICATE_TYPE_FILE_SERVICE
    
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
        
        services = wx.GetApp().GetManager( 'services' ).GetServices( ( HC.FILE_REPOSITORY, HC.LOCAL_FILE ) )
        
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
    
    SYSTEM_PREDICATE_TYPE = HC.SYSTEM_PREDICATE_TYPE_HASH
    
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
    
    SYSTEM_PREDICATE_TYPE = HC.SYSTEM_PREDICATE_TYPE_HEIGHT
    
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
    
    SYSTEM_PREDICATE_TYPE = HC.SYSTEM_PREDICATE_TYPE_LIMIT
    
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
    
    SYSTEM_PREDICATE_TYPE = HC.SYSTEM_PREDICATE_TYPE_MIME
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._mime_media = wx.Choice( self, choices = [ 'image', 'application', 'audio', 'video' ] )
        self._mime_media.Bind( wx.EVT_CHOICE, self.EventMime )
        
        self._mime_type = wx.Choice( self, choices = [], size = ( 120, -1 ) )
        
        system_predicates = HC.options[ 'file_system_predicates' ]
        
        mime = system_predicates[ 'mime' ]
        
        self.SetMime( mime )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.AddF( wx.StaticText( self, label = 'system:mime' ), CC.FLAGS_MIXED )
        hbox.AddF( self._mime_media, CC.FLAGS_MIXED )
        hbox.AddF( wx.StaticText( self, label = '/' ), CC.FLAGS_MIXED )
        hbox.AddF( self._mime_type, CC.FLAGS_MIXED )
        
        self.SetSizer( hbox )
        
        wx.CallAfter( self._mime_media.SetFocus )
        
    
    def EventMime( self, event ):
        
        media = self._mime_media.GetStringSelection()
        
        self._mime_type.Clear()
        
        if media == 'image':
            
            self._mime_type.Append( 'any', HC.IMAGES )
            self._mime_type.Append( 'gif', HC.IMAGE_GIF )
            self._mime_type.Append( 'jpeg', HC.IMAGE_JPEG )
            self._mime_type.Append( 'png', HC.IMAGE_PNG )
            
        elif media == 'application':
            
            self._mime_type.Append( 'any', HC.APPLICATIONS )
            self._mime_type.Append( 'pdf', HC.APPLICATION_PDF )
            self._mime_type.Append( 'x-shockwave-flash', HC.APPLICATION_FLASH )
            
        elif media == 'audio':
            
            self._mime_type.Append( 'any', HC.AUDIO )
            self._mime_type.Append( 'flac', HC.AUDIO_FLAC )
            self._mime_type.Append( 'mp3', HC.AUDIO_MP3 )
            self._mime_type.Append( 'ogg', HC.AUDIO_OGG )
            self._mime_type.Append( 'x-ms-wma', HC.AUDIO_WMA )
            
        elif media == 'video':
            
            self._mime_type.Append( 'any', HC.VIDEO )
            self._mime_type.Append( 'mp4', HC.VIDEO_MP4 )
            self._mime_type.Append( 'webm', HC.VIDEO_WEBM )
            self._mime_type.Append( 'x-matroska', HC.VIDEO_MKV )
            self._mime_type.Append( 'x-ms-wmv', HC.VIDEO_WMV )
            self._mime_type.Append( 'x-flv', HC.VIDEO_FLV )
            
        
        self._mime_type.SetSelection( 0 )
        
    
    def GetInfo( self ):
        
        info = self._mime_type.GetClientData( self._mime_type.GetSelection() )
        
        return info
        
    
    def SetMime( self, mime ):
        
        if mime == HC.IMAGES or mime in HC.IMAGES:
            
            self._mime_media.SetSelection( 0 )
            
        elif mime == HC.APPLICATIONS or mime in HC.APPLICATIONS:
            
            self._mime_media.SetSelection( 1 )
            
        elif mime == HC.AUDIO or mime in HC.AUDIO:
            
            self._mime_media.SetSelection( 2 )
            
        elif mime == HC.VIDEO or mime in HC.VIDEO:
            
            self._mime_media.SetSelection( 3 )
            
        
        self.EventMime( None )
        
        for i in range( self._mime_type.GetCount() ):
            
            client_data = self._mime_type.GetClientData( i )
            
            if client_data == mime:
                
                self._mime_type.SetSelection( i )
                
                break
                
            
        
    
class PanelPredicateSystemNumPixels( PanelPredicateSystem ):
    
    SYSTEM_PREDICATE_TYPE = HC.SYSTEM_PREDICATE_TYPE_NUM_PIXELS
    
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
    
    SYSTEM_PREDICATE_TYPE = HC.SYSTEM_PREDICATE_TYPE_NUM_TAGS
    
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
    
    SYSTEM_PREDICATE_TYPE = HC.SYSTEM_PREDICATE_TYPE_NUM_WORDS
    
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
        
    
class PanelPredicateSystemRatingLike( PanelPredicateSystem ):
    
    SYSTEM_PREDICATE_TYPE = HC.SYSTEM_PREDICATE_TYPE_RATING
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._service_like = wx.Choice( self )
        
        self._value_like = wx.Choice( self, choices=[ 'like', 'dislike', 'rated', 'not rated' ] ) # set words based on current service
        
        self._local_likes = wx.GetApp().GetManager( 'services' ).GetServices( ( HC.LOCAL_RATING_LIKE, ) )
        
        for service in self._local_likes: self._service_like.Append( service.GetName(), service.GetServiceKey() )
        
        self._value_like.SetSelection( 0 )
        
        if len( self._local_likes ) > 0: self._service_like.SetSelection( 0 )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.AddF( wx.StaticText( self, label = 'system:rating:' ), CC.FLAGS_MIXED )
        hbox.AddF( self._service_like, CC.FLAGS_MIXED )
        hbox.AddF( wx.StaticText( self, label = '=' ), CC.FLAGS_MIXED )
        hbox.AddF( self._value_like, CC.FLAGS_MIXED )
        
        self.SetSizer( hbox )
        
        wx.CallAfter( self._value_like.SetFocus )
        
    
    def GetInfo( self ):
        
        service_key = self._service_like.GetClientData( self._service_like.GetSelection() )
        
        operator = '='
        
        selection = self._value_like.GetSelection()
        
        if selection == 0: value = '1'
        elif selection == 1: value = '0'
        elif selection == 2: value = 'rated'
        elif selection == 3: value = 'not rated'
        
        info = ( service_key, operator, value )
        
        return info
        
    
class PanelPredicateSystemRatingNumerical( PanelPredicateSystem ):
    
    SYSTEM_PREDICATE_TYPE = HC.SYSTEM_PREDICATE_TYPE_RATING
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._service_numerical = wx.Choice( self )
        self._service_numerical.Bind( wx.EVT_CHOICE, self.EventRatingsService )
        
        self._sign_numerical = wx.Choice( self, choices=[ '>', '<', '=', u'\u2248', '=rated', '=not rated', '=uncertain' ] )
        
        self._value_numerical = wx.SpinCtrl( self, min = 0, max = 50000, size = ( 60, -1 ) ) # set bounds based on current service
        
        self._local_numericals = wx.GetApp().GetManager( 'services' ).GetServices( ( HC.LOCAL_RATING_NUMERICAL, ) )
        
        for service in self._local_numericals: self._service_numerical.Append( service.GetName(), service )
        
        self._sign_numerical.SetSelection( 0 )
        
        self._value_numerical.SetValue( 0 )
        
        if len( self._local_numericals ) > 0: self._service_numerical.SetSelection( 0 )
        
        self.EventRatingsService( None )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.AddF( wx.StaticText( self, label = 'system:rating:' ), CC.FLAGS_MIXED )
        hbox.AddF( self._service_numerical, CC.FLAGS_MIXED )
        hbox.AddF( self._sign_numerical, CC.FLAGS_MIXED )
        hbox.AddF( self._value_numerical, CC.FLAGS_MIXED )
        
        self.SetSizer( hbox )
        
        wx.CallAfter( self._value_numerical.SetFocus )
        
    
    def EventRatingsService( self, event ):
        
        service = self._service_numerical.GetClientData( self._service_numerical.GetSelection() )
        
        num_stars = service.GetInfo( 'num_stars' )
        
        self._value_numerical.SetRange( 0, num_stars )
        
    
    def GetInfo( self ):
        
        service = self._service_numerical.GetClientData( self._service_numerical.GetSelection() )
        
        operator = self._sign_numerical.GetStringSelection()
        
        if operator in ( '=rated', '=not rated', '=uncertain' ):
            
            value = operator[1:]
            
            operator = '='
            
        else:
            
            num_stars = service.GetInfo( 'num_stars' )
            
            value_raw = self._value_numerical.GetValue()
            
            value = float( value_raw ) / num_stars
            
        
        service_key = service.GetServiceKey()
        
        info = ( service_key, operator, value )
        
        return info
        
    
class PanelPredicateSystemRatio( PanelPredicateSystem ):
    
    SYSTEM_PREDICATE_TYPE = HC.SYSTEM_PREDICATE_TYPE_RATIO
    
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
    
    SYSTEM_PREDICATE_TYPE = HC.SYSTEM_PREDICATE_TYPE_SIMILAR_TO
    
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
    
    SYSTEM_PREDICATE_TYPE = HC.SYSTEM_PREDICATE_TYPE_SIZE
    
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
    
    SYSTEM_PREDICATE_TYPE = HC.SYSTEM_PREDICATE_TYPE_WIDTH
    
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
        
    