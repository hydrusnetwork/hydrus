import typing

from qtpy import QtCore as QC
from qtpy import QtGui as QG
from qtpy import QtWidgets as QW

from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG

from hydrus.client.gui import QtPorting as QP
from hydrus.client.metadata import ClientRatings

default_like_colours = {}

default_like_colours[ ClientRatings.LIKE ] = ( ( 0, 0, 0 ), ( 80, 200, 120 ) )
default_like_colours[ ClientRatings.DISLIKE ] = ( ( 0, 0, 0 ), ( 200, 80, 120 ) )
default_like_colours[ ClientRatings.NULL ] = ( ( 0, 0, 0 ), ( 191, 191, 191 ) )
default_like_colours[ ClientRatings.MIXED ] = ( ( 0, 0, 0 ), ( 95, 95, 95 ) )

default_numerical_colours = {}

default_numerical_colours[ ClientRatings.LIKE ] = ( ( 0, 0, 0 ), ( 80, 200, 120 ) )
default_numerical_colours[ ClientRatings.DISLIKE ] = ( ( 0, 0, 0 ), ( 255, 255, 255 ) )
default_numerical_colours[ ClientRatings.NULL ] = ( ( 0, 0, 0 ), ( 191, 191, 191 ) )
default_numerical_colours[ ClientRatings.MIXED ] = ( ( 0, 0, 0 ), ( 95, 95, 95 ) )

PENTAGRAM_STAR_COORDS = [
    QC.QPointF( 6, 0 ), # top
    QC.QPointF( 7.5, 4.5 ),
    QC.QPointF( 12, 4.5 ), # right
    QC.QPointF( 8.3, 7.2 ),
    QC.QPointF( 9.8, 12 ), # bottom right
    QC.QPointF( 6, 9 ),
    QC.QPointF( 2.2, 12 ), # bottom left
    QC.QPointF( 3.7, 7.2 ),
    QC.QPointF( 0, 4.5 ), # left
    QC.QPointF( 4.5, 4.5 )
]

FAT_STAR_COORDS = [
    QC.QPointF( 6, 0 ), # top
    QC.QPointF( 7.8, 4.1 ),
    QC.QPointF( 12, 4.6 ), # right
    QC.QPointF( 8.9, 7.6 ),
    QC.QPointF( 9.8, 12 ), # bottom right
    QC.QPointF( 6, 9.8 ),
    QC.QPointF( 2.2, 12 ), # bottom left
    QC.QPointF( 3.1, 7.6 ),
    QC.QPointF( 0, 4.5 ), # left
    QC.QPointF( 4.2, 4.1 )
]

def DrawLike( painter, x, y, service_key, rating_state ):
    
    painter.setRenderHint( QG.QPainter.Antialiasing, True )
    
    shape = ClientRatings.GetShape( service_key )
    
    ( pen_colour, brush_colour ) = GetPenAndBrushColours( service_key, rating_state )
    
    painter.setPen( QG.QPen( pen_colour ) )
    painter.setBrush( QG.QBrush( brush_colour ) )
    
    if shape == ClientRatings.CIRCLE:
        
        painter.drawEllipse( QC.QPointF( x+7, y+7 ), 6, 6 )
        
    elif shape == ClientRatings.SQUARE:
        
        painter.drawRect( x+2, y+2, 12, 12 )
        
    elif shape in ( ClientRatings.FAT_STAR, ClientRatings.PENTAGRAM_STAR ):
        
        offset = QC.QPoint( x + 1, y + 1 )
        
        painter.translate( offset )
        
        coords = FAT_STAR_COORDS if shape == ClientRatings.FAT_STAR else PENTAGRAM_STAR_COORDS
        
        painter.drawPolygon( QG.QPolygonF( coords ) )
        
        painter.translate( -offset )
        
    
def DrawNumerical( painter, x, y, service_key, rating_state, rating ):
    
    painter.setRenderHint( QG.QPainter.Antialiasing, True )
    
    ( shape, stars ) = GetStars( service_key, rating_state, rating )
    
    x_delta = 0
    x_step = 12
    
    for ( num_stars, pen_colour, brush_colour ) in stars:
        
        painter.setPen( QG.QPen( pen_colour ) )
        painter.setBrush( QG.QBrush( brush_colour ) )
        
        for i in range( num_stars ):
            
            if shape == ClientRatings.CIRCLE:
                
                painter.drawEllipse( QC.QPointF( x + 7 + x_delta, y + 7 ), 6, 6 )
                
            elif shape == ClientRatings.SQUARE:
                
                painter.drawRect( x + 2 + x_delta, y + 2, 12, 12 )
                
            elif shape in ( ClientRatings.FAT_STAR, ClientRatings.PENTAGRAM_STAR ):
                
                offset = QC.QPoint( x + 1 + x_delta, y + 1 )
                
                painter.translate( offset )
                
                coords = FAT_STAR_COORDS if shape == ClientRatings.FAT_STAR else PENTAGRAM_STAR_COORDS
                
                painter.drawPolygon( QG.QPolygonF( coords ) )
                
                painter.translate( -offset )
                
            
            x_delta += x_step
            
        
    
def GetNumericalWidth( service_key ):
    
    try:
        
        service = HG.client_controller.services_manager.GetService( service_key )
        
        num_stars = service.GetNumStars()
        
    except HydrusExceptions.DataMissing:
        
        num_stars = 1
        
    
    return 4 + 12 * num_stars
    
def GetPenAndBrushColours( service_key, rating_state ):
    
    try:
        
        service = HG.client_controller.services_manager.GetService( service_key )
        
        colour = service.GetColour( rating_state )
        
    except HydrusExceptions.DataMissing:
        
        colour = ( ( 0, 0, 0 ), ( 0, 0, 0 ) )
        
    
    ( pen_rgb, brush_rgb ) = colour
    
    pen_colour = QG.QColor( *pen_rgb )
    brush_colour = QG.QColor( *brush_rgb )
    
    return ( pen_colour, brush_colour )
    
def GetStars( service_key, rating_state, rating ):
    
    try:
        
        service = HG.client_controller.services_manager.GetService( service_key )
        
    except HydrusExceptions.DataMissing:
        
        return ( ClientRatings.FAT_STAR, 0 )
        
    
    shape = service.GetShape()
    
    num_stars = service.GetNumStars()
    
    stars = []
    
    if rating_state in ( ClientRatings.NULL, ClientRatings.MIXED ):
        
        ( pen_colour, brush_colour ) = GetPenAndBrushColours( service_key, rating_state )
        
        stars.append( ( num_stars, pen_colour, brush_colour ) )
        
    else:
        
        num_stars_on = service.ConvertRatingToStars( rating )
        
        num_stars_off = num_stars - num_stars_on
        
        ( pen_colour, brush_colour ) = GetPenAndBrushColours( service_key, ClientRatings.LIKE )
        
        stars.append( ( num_stars_on, pen_colour, brush_colour ) )
        
        ( pen_colour, brush_colour ) = GetPenAndBrushColours( service_key, ClientRatings.DISLIKE )
        
        stars.append( ( num_stars_off, pen_colour, brush_colour ) )
        
    
    return ( shape, stars )
    

class RatingLike( QW.QWidget ):
    
    valueChanged = QC.Signal()
    
    def __init__( self, parent, service_key ):
        
        QW.QWidget.__init__( self, parent )
        
        self._service_key = service_key
        
        self._rating_state = ClientRatings.NULL
        
        self._widget_event_filter = QP.WidgetEventFilter( self )
        
        self._widget_event_filter.EVT_LEFT_DOWN( self.EventLeftDown )
        self._widget_event_filter.EVT_LEFT_DCLICK( self.EventLeftDown )
        self._widget_event_filter.EVT_RIGHT_DOWN( self.EventRightDown )
        self._widget_event_filter.EVT_RIGHT_DCLICK( self.EventRightDown )
        
        self.setMinimumSize( QC.QSize( 16, 16 ) )
        
        self._dirty = True
        
        self._UpdateTooltip()
        
    
    def _Draw( self, painter ):
        
        raise NotImplementedError()
        
    
    def _SetRating( self, rating: typing.Optional[ float ] ):
        
        self._rating_state = rating
        
        self._UpdateTooltip()
        
        self.valueChanged.emit()
        
    
    def _UpdateTooltip( self ):
        
        if self.isEnabled():
            
            text = HG.client_controller.services_manager.GetName( self._service_key )
            
            try:
                
                service = HG.client_controller.services_manager.GetService( self._service_key )
                
                tt = '{} - {}'.format( service.GetName(), service.ConvertRatingStateToString( self._rating_state ) )
                
            except HydrusExceptions.DataMissing:
                
                tt = 'service missing'
                
            
        else:
            
            tt = ''
            
        
        self.setToolTip( tt )
        
    
    def EventLeftDown( self, event ):
        
        raise NotImplementedError()
        
    
    def paintEvent( self, event ):
        
        painter = QG.QPainter( self )
        
        self._Draw( painter )
        
    
    def EventRightDown( self, event ):
        
        raise NotImplementedError()
        
    
    def GetRatingState( self ):
        
        return self._rating_state
        
    
    def GetServiceKey( self ):
        
        return self._service_key
        
    
    def setEnabled( self, value: bool ):
        
        QW.QWidget.setEnabled( self, value )
        
        self._dirty = True
        
        self.update()
        
        self._UpdateTooltip()
        
    

class RatingLikeDialog( RatingLike ):
    
    def _Draw( self, painter ):
        
        painter.setBackground( QG.QBrush( QP.GetBackgroundColour( self.parentWidget() ) ) )
        
        painter.eraseRect( painter.viewport() )
        
        if self.isEnabled():
            
            DrawLike( painter, 0, 0, self._service_key, self._rating_state )
            
        else:
            
            DrawLike( painter, 0, 0, self._service_key, ClientRatings.NULL )
            
        
        self._dirty = False
        
    
    def EventLeftDown( self, event ):
        
        if not self.isEnabled():
            
            return
            
        
        if self._rating_state == ClientRatings.LIKE: self._SetRating( ClientRatings.NULL )
        else: self._SetRating( ClientRatings.LIKE )
        
        self._dirty = True
        
        self.update()
        
    
    def EventRightDown( self, event ):
        
        if not self.isEnabled():
            
            return
            
        
        if self._rating_state == ClientRatings.DISLIKE: self._SetRating( ClientRatings.NULL )
        else: self._SetRating( ClientRatings.DISLIKE )
        
        self._dirty = True
        
        self.update()
        
    
    def SetRatingState( self, rating_state ):
        
        self._SetRating( rating_state )
        
        self._dirty = True
        
        self.update()
        
    
class RatingNumerical( QW.QWidget ):
    
    valueChanged = QC.Signal()
    
    def __init__( self, parent, service_key ):
        
        QW.QWidget.__init__( self, parent )
        
        self._service_key = service_key
        
        self._service = HG.client_controller.services_manager.GetService( self._service_key )
        
        self._num_stars = self._service.GetNumStars()
        self._allow_zero = self._service.AllowZero()
        
        my_width = GetNumericalWidth( self._service_key )
        
        self._widget_event_filter = QP.WidgetEventFilter( self )
        
        self._widget_event_filter.EVT_LEFT_DOWN( self.EventLeftDown )
        self._widget_event_filter.EVT_LEFT_DCLICK( self.EventLeftDown )
        self._widget_event_filter.EVT_RIGHT_DOWN( self.EventRightDown )
        self._widget_event_filter.EVT_RIGHT_DCLICK( self.EventRightDown )
        
        self.setMinimumSize( QC.QSize( my_width, 16 ) )
        
        self._rating_state = ClientRatings.NULL
        self._rating = 0.0
        
        self._dirty = True
        
    
    def _ClearRating( self ):
        
        self._rating_state = ClientRatings.NULL
        self._rating = 0.0
        
        self._UpdateTooltip()
        
        self.valueChanged.emit()
        
    
    def _Draw( self, painter ):
        
        raise NotImplementedError()
        
    
    def _GetRatingStateAndRatingFromClickEvent( self, event ):
        
        click_pos = event.position().toPoint()
        
        x = click_pos.x()
        
        BORDER = 1
        
        my_active_size = self.size() - QC.QSize( BORDER * 2, BORDER * 2 )
        
        adjusted_click_pos = click_pos - QC.QPoint( BORDER, BORDER )
        
        adjusted_click_pos.setY( BORDER + 1 )
        
        my_active_rect = QC.QRect( QC.QPoint( 0, 0 ), my_active_size )
        
        if my_active_rect.contains( adjusted_click_pos ):
            
            x_adjusted = x - BORDER
            
            proportion_filled = x_adjusted / my_active_size.width()
            
            if self._allow_zero:
                
                stars = round( proportion_filled * self._num_stars )
                
            else:
                
                stars = int( proportion_filled * self._num_stars ) 
                
                if proportion_filled <= 1.0:
                    
                    stars += 1
                    
                
            
            rating = self._service.ConvertStarsToRating( stars )
            
            return ( ClientRatings.SET, rating )
            
        
        return ( ClientRatings.NULL, 0.0 )
        
    
    def _SetRating( self, rating ):
        
        if rating is None:
            
            self._ClearRating()
            
        else:
            
            self._rating_state = ClientRatings.SET
            self._rating = rating
            
            self._UpdateTooltip()
            
        
        self.valueChanged.emit()
        
    
    def _UpdateTooltip( self ):
        
        if self.isEnabled():
            
            text = HG.client_controller.services_manager.GetName( self._service_key )
            
            try:
                
                service = HG.client_controller.services_manager.GetService( self._service_key )
                
                tt = '{} - {}'.format( service.GetName(), service.ConvertRatingStateAndRatingToString( self._rating_state, self._rating ) )
                
            except HydrusExceptions.DataMissing:
                
                tt = 'service missing'
                
            
        else:
            
            tt = ''
            
        
        self.setToolTip( tt )
        
    
    def EventLeftDown( self, event ):
        
        if not self.isEnabled():
            
            return
            
        
        ( rating_state, rating ) = self._GetRatingStateAndRatingFromClickEvent( event )
        
        if rating_state == ClientRatings.NULL:
            
            self._ClearRating()
            
        elif rating_state == ClientRatings.SET:
            
            self._SetRating( rating )
            
        
    
    def EventRightDown( self, event ):
        
        if not self.isEnabled():
            
            return
            
        
        self._ClearRating()
        
    
    def GetServiceKey( self ):
        
        return self._service_key
        
    
    def mouseMoveEvent( self, event ):
        
        if event.buttons() & QC.Qt.LeftButton:
            
            ( rating_state, rating ) = self._GetRatingStateAndRatingFromClickEvent( event )
            
            if rating_state != self._rating_state or rating != self._rating:
                
                if rating_state == ClientRatings.SET:
                    
                    self._SetRating( rating )
                    
                
            
        
    
    def paintEvent( self, event ):
        
        painter = QG.QPainter( self )
        
        self._Draw( painter )
        
    
    def setEnabled( self, value: bool ):
        
        QW.QWidget.setEnabled( self, value )
        
        self._dirty = True
        
        self.update()
        
        self._UpdateTooltip()
        
    
class RatingNumericalDialog( RatingNumerical ):
    
    def _ClearRating( self ):
        
        RatingNumerical._ClearRating( self )
        
        self._rating_state = ClientRatings.NULL
        
        self._dirty = True
        
        self.update()
        
    
    def _Draw( self, painter ):
        
        painter.setBackground( QG.QBrush( QP.GetBackgroundColour( self.parentWidget() ) ) )
        
        painter.eraseRect( painter.viewport() )
        
        if self.isEnabled():
            
            DrawNumerical( painter, 0, 0, self._service_key, self._rating_state, self._rating )
            
        else:
            
            DrawNumerical( painter, 0, 0, self._service_key, ClientRatings.NULL, 0.0 )
            
        
        self._dirty = False
        
    
    def _SetRating( self, rating ):
        
        RatingNumerical._SetRating( self, rating )
        
        if rating is None:
            
            self._ClearRating()
            
        else:
            
            self._rating_state = ClientRatings.SET
            
            self._rating = rating
            
            self._dirty = True
            
            self.update()
            
        
    
    def GetRating( self ):
        
        return self._rating
        
    
    def GetRatingState( self ):
        
        return self._rating_state
        
    
    def SetRating( self, rating ):
        
        self._SetRating( rating )
        
    
    def SetRatingState( self, rating_state ):
        
        self._rating_state = rating_state
        
        self._dirty = True
        
        self.update()
        
        self._UpdateTooltip()
        
    
