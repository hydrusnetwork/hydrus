from qtpy import QtCore as QC
from qtpy import QtGui as QG
from qtpy import QtWidgets as QW

from hydrus.core import HydrusExceptions
from hydrus.core import HydrusNumbers

from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientConstants as CC
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui import ClientGUIExceptionHandling
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.gui.widgets import ClientGUIPainterShapes
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

default_incdec_colours = {}

default_incdec_colours[ ClientRatings.LIKE ] = ( ( 0, 0, 0 ), ( 80, 200, 120 ) )
default_incdec_colours[ ClientRatings.DISLIKE ] = ( ( 0, 0, 0 ), ( 255, 255, 255 ) )
default_incdec_colours[ ClientRatings.NULL ] = ( ( 0, 0, 0 ), ( 191, 191, 191 ) )
default_incdec_colours[ ClientRatings.MIXED ] = ( ( 0, 0, 0 ), ( 95, 95, 95 ) )

# -> QC.QSize
#These are used as defaults for the Rating* classes icon sizes if not called with a size, e.g. for the standalone popup Manage Ratings panel 
INCDEC_SIZE = ClientGUIPainterShapes.INCDEC_BACKGROUND_SIZE
STAR_SIZE = ClientGUIPainterShapes.SIZE
STAR_PAD  = ClientGUIPainterShapes.PAD
PAD_PX = round( ClientGUIPainterShapes.PAD_PX )

def DrawIncDec( painter: QG.QPainter, x, y, service_key, rating_state, rating, size: QC.QSize = INCDEC_SIZE, pad_size: QC.QSize = None ):
    
    painter.save()
    
    try:
        
        if rating is None:
            
            rating = 0
            
        if pad_size is None:
            
            pad_size = QC.QSize( int( min( size.width() / PAD_PX, PAD_PX ) ), PAD_PX ) #allow X pad to go smaller, Y pad as normal
            
        
        text = HydrusNumbers.ToHumanInt( rating )
        
        original_font = painter.font()
        
        incdec_font = painter.font()
        
        incdec_font.setPixelSize( int( size.height() - 1 ) if size.height() > 8 else int( size.height() ) )
        
        incdec_font.setStyleHint( QG.QFont.StyleHint.Monospace )
        
        painter.setFont( incdec_font )
        
        if rating_state == ClientRatings.SET:
            
            colour_rating_state = ClientRatings.LIKE
            
        else:
            
            colour_rating_state = ClientRatings.MIXED
            
        
        ( pen_colour, brush_colour ) = GetPenAndBrushColours( service_key, colour_rating_state )
        
        painter.setPen( pen_colour )
        painter.setBrush( brush_colour )
        
        painter.setRenderHint( QG.QPainter.RenderHint.Antialiasing, False )
        
        # star_type = ClientRatings.StarType( ClientRatings.SQUARE, None )
        # ClientGUIPainterShapes.DrawShape( painter, star_type, x, y, size.width(), size.height() )
        
        #switch back to qt rect draw to avoid extra overhead and bypass some pads since we don't customize these yet
        painter.drawRect( QC.QRect( x, y, size.width(), size.height() ) )
        
        #
        text_pos = QC.QPoint( x - 1, y + 1 )
        
        if incdec_font.pixelSize() > 8:
            
            painter.setRenderHint( QG.QPainter.RenderHint.Antialiasing, True )
            
            text_pos = QC.QPoint( x - 1, y )
            
        
        text_rect = QC.QRect( text_pos, size - QC.QSize( 1, 1 ) )
        
        painter.drawText( text_rect, QC.Qt.AlignmentFlag.AlignRight | QC.Qt.AlignmentFlag.AlignVCenter, text )
        
        painter.setFont( original_font )
        
    finally:
        
        painter.restore()
        
    

def DrawLike( painter: QG.QPainter, x, y, service_key, rating_state, size: QC.QSize = STAR_SIZE ):
    
    painter.save()
    
    try:
        
        painter.setRenderHint( QG.QPainter.RenderHint.Antialiasing, True )
        
        star_type = ClientRatings.GetStarType( service_key )
        
        ( pen_colour, brush_colour ) = GetPenAndBrushColours( service_key, rating_state )
        
        painter.setPen( QG.QPen( pen_colour ) )
        painter.setBrush( QG.QBrush( brush_colour ) )
        
        ClientGUIPainterShapes.DrawShape( painter, star_type, x, y, size.width(), size.height() )
        
    finally:
        
        painter.restore()
        
    

def DrawNumerical( painter: QG.QPainter, x: int, y: int, service_key, rating_state, rating, size: QC.QSize = STAR_SIZE, pad_px = None, draw_collapsed = False, text_pen_colour = None ):
    
    painter.save()
    
    try:
        
        try:
            
            service = CG.client_controller.services_manager.GetService( service_key )
            
            if pad_px is None:
                
                pad_px = service.GetCustomPad()
                
            
            draw_fractional_beside = service.GetShowFractionBesideStars()
            
        except HydrusExceptions.DataMissing:
            
            pad_px = ClientGUIPainterShapes.PAD_PX
            
            draw_fractional_beside = False
            
        
        painter.setRenderHint( QG.QPainter.RenderHint.Antialiasing, True )
        
        ( star_type, stars ) = GetStars( service_key, rating_state, rating )
        
        x_delta = 0
        x_step = size.width() + pad_px
        
        if draw_collapsed or draw_fractional_beside == ClientRatings.DRAW_ON_LEFT:
            
            painter.save()
            
            try:
                
                numeric_font = painter.font()
                
                numeric_font.setPixelSize( int( size.height() - 1 ) )
                
                painter.setFont( numeric_font )
                
                if text_pen_colour is not None:
                    
                    painter.setPen( QG.QPen( text_pen_colour ) )
                    
                
                text = GetNumericalFractionText( rating_state, stars )
                
                metrics = QG.QFontMetrics( numeric_font )
                text_size = metrics.size( 0, text )
                
                painter.drawText( QC.QRectF( round( x - ClientGUIPainterShapes.PAD_PX / 2 ), round( y - ClientGUIPainterShapes.PAD_PX ), text_size.width(), text_size.height() ), text )
                
                x_delta += text_size.width() + 1
                
            finally:
                
                painter.restore()
                
            
        
        #draw 1 'like' star in collapsed state
        if draw_collapsed:
            
            painter.setPen( QG.QPen( stars[0][1] ) )
            painter.setBrush( QG.QBrush( stars[0][2] ) )
            
            ClientGUIPainterShapes.DrawShape( painter, star_type, x + x_delta, y, size.width(), size.height() )
            
        else:
            
            painter.save()
            
            try:
                
                for ( num_stars, pen_colour, brush_colour ) in stars:
                    
                    painter.setPen( QG.QPen( pen_colour ) )
                    painter.setBrush( QG.QBrush( brush_colour ) )
                    
                    for i in range( num_stars ):
                        
                        ClientGUIPainterShapes.DrawShape( painter, star_type, x + x_delta, y, size.width(), size.height() )
                        
                        x_delta += x_step
                        
                    
                
            finally:
                
                painter.restore()
                
            
            if draw_fractional_beside == ClientRatings.DRAW_ON_RIGHT:
                
                painter.save()
                
                try:
                    
                    numeric_font = painter.font()
                    
                    numeric_font.setPixelSize( int( size.height() - 1 ) )
                    
                    painter.setFont( numeric_font )
                    
                    if text_pen_colour is not None:
                        
                        painter.setPen( QG.QPen( text_pen_colour ) )
                        
                    
                    text = GetNumericalFractionText( rating_state, stars )
                    
                    metrics = QG.QFontMetrics( numeric_font )
                    text_size = metrics.size( 0, text )
                    
                    painter.drawText( QC.QRectF( round( x + x_delta - pad_px + ClientGUIPainterShapes.PAD_PX / 2 ), round( y - ClientGUIPainterShapes.PAD_PX ), text_size.width(), text_size.height() ), text )
                    
                finally:
                    
                    painter.restore()
                    
                
            
        
    finally:
        
        painter.restore()
        
    

def GetIconSize( canvas_type, service_type = ClientGUICommon.HC.LOCAL_RATING_LIKE ):
    
    if canvas_type in CC.CANVAS_MEDIA_VIEWER_TYPES:
        
        rating_icon_size_px = CG.client_controller.new_options.GetFloat( 'media_viewer_rating_icon_size_px' )
        rating_incdec_height_px = CG.client_controller.new_options.GetFloat( 'media_viewer_rating_incdec_height_px' )
        
    elif canvas_type == CC.CANVAS_PREVIEW:
        
        rating_icon_size_px = CG.client_controller.new_options.GetFloat( 'preview_window_rating_icon_size_px' )
        rating_incdec_height_px = CG.client_controller.new_options.GetFloat( 'preview_window_rating_incdec_height_px' )
        
    elif canvas_type == CC.CANVAS_DIALOG:
        
        rating_icon_size_px = CG.client_controller.new_options.GetFloat( 'dialog_rating_icon_size_px' )
        rating_incdec_height_px = CG.client_controller.new_options.GetFloat( 'dialog_rating_incdec_height_px' )
        
    else:
        
        rating_icon_size_px = CG.client_controller.new_options.GetFloat( 'draw_thumbnail_rating_icon_size_px' )
        rating_incdec_height_px = CG.client_controller.new_options.GetFloat( 'thumbnail_rating_incdec_height_px' )
        
    
    if service_type == ClientGUICommon.HC.LOCAL_RATING_INCDEC:
        
        return QC.QSize( int( rating_incdec_height_px * 2 ), int( rating_incdec_height_px ) )
        
    else:
        
        return QC.QSize( int( rating_icon_size_px ), int( rating_icon_size_px ) )
        
    

def GetIncDecSize( box_height, rating_number ) -> QC.QSize:
    
    box_width = box_height * 2
    
    if rating_number is not None and rating_number > 0:
        
        digits = len( str( rating_number ) )
        
        if digits > 3:
            
            box_width += ( box_height - 1 ) * ( digits - ( 2 + ( digits / 3 ) ) ) 
            #the below increases the padding drastically with more digits, the above has a constant pad
            #more dramatic indent for bigger numbers seems sometimes better visually, but let's tend towards saving space
            #box_width += ( box_height - 1 ) * ( digits - 3 )
            
        
    return QC.QSize( int( box_width ), int( box_height ) )
    

def GetNumericalFractionText( rating_state, stars ):
    
    if len( stars ) == 1:
        
        frac_denominator = stars[0][0]
        
        if rating_state == ClientRatings.NULL:
            
            frac_numerator = '-'
            
        elif rating_state == ClientRatings.MIXED:
            
            frac_numerator = '~'
            
        else:
            
            frac_numerator = '0'
            
        
    else:
        
        frac_numerator = str( stars[0][0] )
        frac_denominator = stars[0][0] + stars[1][0]
        
    
    #Do not adjust whitespace within :> formatter.
    frac_numerator = f"{frac_numerator:>{ len( str( frac_denominator ) ) }}"
    text = '{}/{}'.format( frac_numerator, frac_denominator )
    
    return text
    

def GetNumericalWidth( service_key, star_width, pad_px = None, draw_collapsed = False, rating_state = ClientRatings.NULL, rating = None ):
    
    try:
        
        service = CG.client_controller.services_manager.GetService( service_key )
        
        num_stars = service.GetNumStars()
        
        draw_fractional_beside = service.GetShowFractionBesideStars()
        
        if draw_collapsed or draw_fractional_beside:
            
            if rating is None:
                
                rating = 1.0
                
            
            ( star_type, stars ) = GetStars( service_key, rating_state, rating )
            
            #calculate the width of the text to be added e.g. 10/10
            numeric_font = QG.QFont()
            
            numeric_font.setPixelSize( int( star_width - 1 ) )
            
            text = GetNumericalFractionText( rating_state, stars )
            
            metrics = QG.QFontMetrics( numeric_font )
            text_size = metrics.size( 0, text )
            text_size = text_size.width()
            
            if draw_collapsed:
                
                num_stars = 1
                
            
        else:
            
            text_size = 0
            
        
        if pad_px is None:
            
            try:
                
                pad_px = service.GetCustomPad()
                
            except HydrusExceptions.DataMissing: 
                
                pad_px = ClientGUIPainterShapes.PAD_PX
                
            
    except HydrusExceptions.DataMissing:
        
        num_stars = 1
        
    
    return text_size + ( star_width * num_stars) + ( pad_px * ( num_stars - 1 ) ) + ( ClientGUIPainterShapes.PAD_PX )
    ##return text_size + ( ( star_width + pad_px ) * num_stars - 1 ) + ( ClientGUIPainterShapes.PAD_PX ) - pad_px
    
    
def GetPenAndBrushColours( service_key, rating_state ):
    
    try:
        
        service = CG.client_controller.services_manager.GetService( service_key )
        
        colour = service.GetColour( rating_state )
        
    except HydrusExceptions.DataMissing:
        
        colour = ( ( 0, 0, 0 ), ( 0, 0, 0 ) )
        
    
    ( pen_rgb, brush_rgb ) = colour
    
    pen_colour = QG.QColor( *pen_rgb )
    brush_colour = QG.QColor( *brush_rgb )
    
    return ( pen_colour, brush_colour )
    

def GetStars( service_key, rating_state, rating ):
    
    try:
        
        service = CG.client_controller.services_manager.GetService( service_key )
        
    except HydrusExceptions.DataMissing:
        
        return ( ClientRatings.FAT_STAR, 0 )
        
    
    star_type = service.GetStarType()
    
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
        
    
    return ( star_type, stars )
    

class RatingIncDec( QW.QWidget ):
    
    valueChanged = QC.Signal()
    
    def __init__( self, parent, service_key, canvas_type ):
        
        super().__init__( parent )
        
        self._canvas_type = canvas_type
        
        self._service_key = service_key
        
        self._service = CG.client_controller.services_manager.GetService( self._service_key )
        
        self._widget_event_filter = QP.WidgetEventFilter( self )
        
        # middle down too? brings up a dialog for manual entry, sounds good
        
        self._icon_size = GetIconSize( canvas_type, ClientGUICommon.HC.LOCAL_RATING_INCDEC )
        
        self._rating_state = ClientRatings.SET
        self._rating = 0
        
        self.valueChanged.connect( lambda: self.UpdateSize( self._icon_size ) )
        
    
    def _Draw( self, painter ):
        
        raise NotImplementedError()
        
    
    def _SetRating( self, rating ):
        
        self._rating_state = ClientRatings.SET
        self._rating = rating
        
        self.update()
        
        self._UpdateTooltip()
        
        self.valueChanged.emit()
        
    
    def _UpdateTooltip( self ):
        
        if self.isEnabled():
            
            text = CG.client_controller.services_manager.GetName( self._service_key )
            
            try:
                
                service = CG.client_controller.services_manager.GetService( self._service_key )
                
                tt = '{} - {}'.format( service.GetName(), service.ConvertRatingStateAndRatingToString( self._rating_state, self._rating ) )
                
            except HydrusExceptions.DataMissing:
                
                tt = 'service missing'
                
            
        else:
            
            tt = ''
            
        
        self.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
    
    def mouseDoubleClickEvent( self, event ):
        
        self.mousePressEvent( event )
        
    
    def mousePressEvent( self, event ):
        
        if self.isEnabled():
            
            button = event.button()
            
            if button == QC.Qt.MouseButton.LeftButton:
                
                self._SetRating( self._rating + 1 )
                
                event.accept()
                
                return
                
            elif button == QC.Qt.MouseButton.RightButton:
                
                if self._rating > 0:
                    
                    self._SetRating( self._rating - 1 )
                    
                    event.accept()
                    
                    return
                    
                
            elif button == QC.Qt.MouseButton.MiddleButton:
                
                from hydrus.client.gui import ClientGUITopLevelWindowsPanels
                from hydrus.client.gui.panels import ClientGUIScrolledPanels
                
                with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit value' ) as dlg:
                    
                    panel = ClientGUIScrolledPanels.EditSingleCtrlPanel( dlg )
                    
                    control = ClientGUICommon.BetterSpinBox( self, initial = self._rating, min = 0, max = 1000000 )
                    
                    panel.SetControl( control, perpendicular = True )
                    
                    dlg.SetPanel( panel )
                    
                    control.setFocus()
                    
                    if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                        
                        new_rating = control.value()
                        
                        self._SetRating( new_rating )
                        
                        event.accept()
                        
                        return
                        
                    
                
            
        
        QW.QWidget.mousePressEvent( self, event )
        
    
    def GetServiceKey( self ):
        
        return self._service_key
        
    
    def paintEvent( self, event ):
        
        try:
            
            painter = QG.QPainter( self )
            
            self._Draw( painter )
            
        except Exception as e:
            
            ClientGUIExceptionHandling.HandlePaintEventException( self, e )
            
        
    
    def setEnabled( self, value: bool ):
        
        QW.QWidget.setEnabled( self, value )
        
        self.update()
        
        self._UpdateTooltip()
        
    
    def sizeHint( self ):
        
        return QC.QSize( self._icon_size.width(), self._icon_size.height() + STAR_PAD.height() )
        
    
    def UpdateSize( self, size: QC.QSize = None ):
        
        if size is None:
            
            self._icon_size = GetIncDecSize( GetIconSize( self._canvas_type, ClientGUICommon.HC.LOCAL_RATING_INCDEC ).height(), self._rating )
            
        else: 
            
            self._icon_size = GetIncDecSize( size.height(), self._rating )
            
        
        self.updateGeometry()
        
        self.update()
        
    

class RatingIncDecControl( RatingIncDec ):
    
    def GetRating( self ):
        
        return self._rating
        
    
    def GetRatingState( self ):
        
        return self._rating_state
        
    
    def SetRating( self, rating ):
        
        self._SetRating( rating )
        
        self.UpdateSize()
        
    
    def SetRatingState( self, rating_state, rating ):
        
        self._rating_state = rating_state
        self._rating = rating
        
        self.update()
        
        self._UpdateTooltip()
        
        self.UpdateSize()
        
    

class RatingIncDecDialog( RatingIncDecControl ):
    
    def _Draw( self, painter ):
        
        painter.setBackground( QG.QBrush( QP.GetBackgroundColour( self.parentWidget() ) ) )
        
        painter.eraseRect( painter.viewport() )
        
        if self.isEnabled():
            
            DrawIncDec( painter, 0, 0, self._service_key, self._rating_state, self._rating, self._icon_size - QC.QSize( 1, 0 ) )
            
        else:
            
            DrawIncDec( painter, 0, 0, self._service_key, ClientRatings.NULL, 0, self._icon_size - QC.QSize( 1, 0 ) )
            
        
    

class RatingIncDecExample( RatingIncDecControl ):
    
    def _Draw( self, painter ):
        
        painter.setBackground( QG.QBrush( QP.GetBackgroundColour( self.parentWidget() ) ) )
        
        painter.eraseRect( painter.viewport() )
        
        if self.isEnabled():
            
            DrawIncDec( painter, 0, 0, self._service_key, self._rating_state, self._rating, self._icon_size - QC.QSize( 1, 0 ) )
            
        else:
            
            DrawIncDec( painter, 0, 0, self._service_key, ClientRatings.NULL, 0, self._icon_size - QC.QSize( 1, 0 ) )
            
        
    

class RatingLike( QW.QWidget ):
    
    valueChanged = QC.Signal()
    
    def __init__( self, parent, service_key, canvas_type ):
        
        super().__init__( parent )
        
        self._canvas_type = canvas_type
        self._service_key = service_key
        
        self._rating_state = ClientRatings.NULL
        
        self._widget_event_filter = QP.WidgetEventFilter( self )
        
        self._widget_event_filter.EVT_LEFT_DOWN( self.EventLeftDown )
        self._widget_event_filter.EVT_LEFT_DCLICK( self.EventLeftDown )
        self._widget_event_filter.EVT_RIGHT_DOWN( self.EventRightDown )
        self._widget_event_filter.EVT_RIGHT_DCLICK( self.EventRightDown )
        
        self._icon_size = GetIconSize( self._canvas_type, ClientGUICommon.HC.LOCAL_RATING_LIKE )
        self.setMinimumSize( self._icon_size + STAR_PAD )
        
        self._UpdateTooltip()
        
    
    def _Draw( self, painter ):
        
        raise NotImplementedError()
        
    
    def _SetRating( self, rating: float | None ):
        
        self._rating_state = rating
        
        self._UpdateTooltip()
        
        self.valueChanged.emit()
        
    
    def _UpdateTooltip( self ):
        
        if self.isEnabled():
            
            try:
                
                service = CG.client_controller.services_manager.GetService( self._service_key )
                
                tt = '{} - {}'.format( service.GetName(), service.ConvertRatingStateToString( self._rating_state ) )
                
            except HydrusExceptions.DataMissing:
                
                tt = 'service missing'
                
            
        else:
            
            tt = ''
            
        
        self.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
    
    def EventLeftDown( self, event ):
        
        raise NotImplementedError()
        
    
    def paintEvent( self, event ):
        
        try:
            
            painter = QG.QPainter( self )
            
            self._Draw( painter )
            
        except Exception as e:
            
            ClientGUIExceptionHandling.HandlePaintEventException( self, e )
            
        
    
    def EventRightDown( self, event ):
        
        raise NotImplementedError()
        
    
    def GetRatingState( self ):
        
        return self._rating_state
        
    
    def GetServiceKey( self ):
        
        return self._service_key
        
    
    def setEnabled( self, value: bool ):
        
        QW.QWidget.setEnabled( self, value )
        
        self.update()
        
        self._UpdateTooltip()
        
    
    def UpdateSize( self, size: QC.QSize = None ):
        
        if size is None:
            
            self._icon_size = GetIconSize( self._canvas_type, ClientGUICommon.HC.LOCAL_RATING_LIKE )
            
        else: 
            
            self._icon_size = size
            
        
        self.setMinimumSize( QC.QSize( self._icon_size.width() + STAR_PAD.width(), self._icon_size.height() + STAR_PAD.height() ) )
        
        self.update()
        
    

class RatingLikeControl( RatingLike ):
    
    def EventLeftDown( self, event ):
        
        if not self.isEnabled():
            
            return
            
        
        if self._rating_state == ClientRatings.LIKE: self._SetRating( ClientRatings.NULL )
        else: self._SetRating( ClientRatings.LIKE )
        
        self.update()
        
    
    def EventRightDown( self, event ):
        
        if not self.isEnabled():
            
            return
            
        
        if self._rating_state == ClientRatings.DISLIKE: self._SetRating( ClientRatings.NULL )
        else: self._SetRating( ClientRatings.DISLIKE )
        
        self.update()
        
    
    def SetRatingState( self, rating_state ):
        
        self._SetRating( rating_state )
        
        self.update()
        
    

class RatingLikeDialog( RatingLikeControl ):
    
    def _Draw( self, painter ):
        
        painter.setBackground( QG.QBrush( QP.GetBackgroundColour( self.parentWidget() ) ) )
        
        painter.eraseRect( painter.viewport() )
        
        if self.isEnabled():
            
            DrawLike( painter, round( PAD_PX / 2 ), 1, self._service_key, self._rating_state, self._icon_size )
            
        else:
            
            DrawLike( painter, round( PAD_PX / 2 ), 1, self._service_key, ClientRatings.NULL, self._icon_size)
            
        
    
class RatingLikeExample( RatingLikeControl ):
    
    def _Draw( self, painter ):
        
        painter.setBackground( QG.QBrush( QP.GetBackgroundColour( self.parentWidget() ) ) )
        
        painter.eraseRect( painter.viewport() )
        
        if self.isEnabled():
            
            DrawLike( painter, round( PAD_PX / 2 ), round( PAD_PX / 2 ), self._service_key, self._rating_state, self._icon_size )
            
        else:
            
            DrawLike( painter, round( PAD_PX / 2 ), round( PAD_PX / 2 ), self._service_key, ClientRatings.NULL, self._icon_size)
            
        

class RatingNumerical( QW.QWidget ):
    
    valueChanged = QC.Signal()
    
    def __init__( self, parent, service_key, canvas_type = None ):
        
        super().__init__( parent )
        
        self._service_key = service_key
        
        try:
            
            service = CG.client_controller.services_manager.GetService( self._service_key )
            
            self._num_stars = service.GetNumStars()
            self._allow_zero = service.AllowZero()
            self._custom_pad = service.GetCustomPad()
            self._draw_fraction = service.GetShowFractionBesideStars()
            
        except HydrusExceptions.DataMissing:
            
            self._num_stars = 5
            self._allow_zero = False
            self._custom_pad = ClientGUIPainterShapes.PAD_PX
            self._draw_fraction = ClientRatings.DRAW_NO
            
        
        self._canvas_type = canvas_type
        self._icon_size = GetIconSize( canvas_type, ClientGUICommon.HC.LOCAL_RATING_NUMERICAL )
        
        self._widget_event_filter = QP.WidgetEventFilter( self )
        
        self._widget_event_filter.EVT_LEFT_DOWN( self.EventLeftDown )
        self._widget_event_filter.EVT_LEFT_DCLICK( self.EventLeftDown )
        self._widget_event_filter.EVT_RIGHT_DOWN( self.EventRightDown )
        self._widget_event_filter.EVT_RIGHT_DCLICK( self.EventRightDown )
        
        self._rating_state = ClientRatings.NULL
        self._rating = 0.0
        
        self.UpdateSize()
        
    
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
            
            width = my_active_size.width()
            
            if self._draw_fraction == ClientRatings.DRAW_ON_LEFT: #if we drew the fraction on the left of the stars, adjust clicky area from the left side
                
                x_min = ( self._icon_size.width() - 1 ) * len( GetNumericalFractionText( ClientRatings.SET, [ [ self._num_stars ] ] ) ) / 2
                x_clamped = max(x_adjusted, x_min)
                proportion_filled = (x_clamped - x_min) / (width - x_min)
                
            elif self._draw_fraction == ClientRatings.DRAW_ON_RIGHT: #or if we drew if on the right, adjust from the right side
                
                x_max = width - ( self._icon_size.width() - 1 ) * len( GetNumericalFractionText( ClientRatings.SET, [ [ self._num_stars ] ] ) ) / 2
                x_clamped = min(x_adjusted, x_max)
                proportion_filled = x_clamped / x_max
                
            else:
                
                proportion_filled = x_adjusted / width
                
            
            if self._allow_zero:
                
                stars = round( proportion_filled * self._num_stars )
                
            else:
                
                stars = int( proportion_filled * self._num_stars ) 
                
                if proportion_filled <= 1.0:
                    
                    stars += 1
                    
                
            
            rating = ClientRatings.ConvertStarsToRating( self._num_stars, self._allow_zero, stars )
            
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
            
            text = CG.client_controller.services_manager.GetName( self._service_key )
            
            try:
                
                service = CG.client_controller.services_manager.GetService( self._service_key )
                
                tt = '{} - {}'.format( service.GetName(), service.ConvertRatingStateAndRatingToString( self._rating_state, self._rating ) )
                
            except HydrusExceptions.DataMissing:
                
                tt = 'service missing'
                
            
        else:
            
            tt = ''
            
        
        self.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
    
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
        
        if event.buttons() & QC.Qt.MouseButton.LeftButton:
            
            ( rating_state, rating ) = self._GetRatingStateAndRatingFromClickEvent( event )
            
            if rating_state != self._rating_state or rating != self._rating:
                
                if rating_state == ClientRatings.SET:
                    
                    self._SetRating( rating )
                    
                
            
        
    
    def paintEvent( self, event ):
        
        try:
            
            painter = QG.QPainter( self )
            
            self._Draw( painter )
            
        except Exception as e:
            
            ClientGUIExceptionHandling.HandlePaintEventException( self, e )
            
        
    
    def setEnabled( self, value: bool ):
        
        QW.QWidget.setEnabled( self, value )
        
        self.update()
        
        self._UpdateTooltip()
        
    
    def UpdateSize( self, size: QC.QSize = None ):
        
        if size is None:
            
            self._icon_size = GetIconSize( self._canvas_type, ClientGUICommon.HC.LOCAL_RATING_NUMERICAL )
            
        else: 
            
            self._icon_size = size
            self._custom_pad = CG.client_controller.services_manager.GetService( self._service_key ).GetCustomPad()
            self._num_stars = CG.client_controller.services_manager.GetService( self._service_key ).GetNumStars()
            self._draw_fraction = CG.client_controller.services_manager.GetService( self._service_key ).GetShowFractionBesideStars()
            
        
        my_width = GetNumericalWidth( self._service_key, self._icon_size.width(), self._custom_pad, False, self._rating_state, self._rating )
        
        self.setMinimumSize( QC.QSize( my_width, self._icon_size.height() + STAR_PAD.height() ) )
        
        self.update()
        
    

class RatingNumericalControl( RatingNumerical ):
    
    def _ClearRating( self ):
        
        RatingNumerical._ClearRating( self )
        
        self._rating_state = ClientRatings.NULL
        
        self.update()
        
    
    def _SetRating( self, rating ):
        
        RatingNumerical._SetRating( self, rating )
        
        if rating is None:
            
            self._ClearRating()
            
        else:
            
            self._rating_state = ClientRatings.SET
            
            self._rating = rating
            
            self.update()
            
        
    
    def GetRating( self ):
        
        return self._rating
        
    
    def GetRatingState( self ):
        
        return self._rating_state
        
    
    def SetRating( self, rating ):
        
        self._SetRating( rating )
        
    
    def SetRatingState( self, rating_state ):
        
        self._rating_state = rating_state
        
        self.update()
        
        self._UpdateTooltip()
        
    

class RatingNumericalDialog( RatingNumericalControl ):
    
    def _Draw( self, painter ):
        
        painter.setBackground( QG.QBrush( QP.GetBackgroundColour( self.parentWidget() ) ) )
        
        painter.eraseRect( painter.viewport() )
        
        if self.isEnabled():
            
            DrawNumerical( painter, 1, round( PAD_PX / 2 ), self._service_key, self._rating_state, self._rating, size = self._icon_size )
            
        else:
            
            DrawNumerical( painter, 1, round( PAD_PX / 2 ), self._service_key, ClientRatings.NULL, 0.0, size = self._icon_size )
            
        
        self.updateGeometry()
        
    

class RatingNumericalExample( RatingNumericalControl ):
    
    def _Draw( self, painter ):
        
        painter.setBackground( QG.QBrush( QP.GetBackgroundColour( self.parentWidget() ) ) )
        
        painter.eraseRect( painter.viewport() )
        
        if self.isEnabled():
            
            DrawNumerical( painter, round( PAD_PX / 2 ), round( PAD_PX / 2 ), self._service_key, self._rating_state, self._rating, size = self._icon_size )
            
        else:
            
            DrawNumerical( painter, round( PAD_PX / 2 ), round( PAD_PX / 2 ), self._service_key, ClientRatings.NULL, 0.0, size = self._icon_size )
            
        
        self.updateGeometry()
        
    
    
class RatingPreviewServiceWrapper:
    
    def __init__( self, original_service_key: bytes, test_service_key: bytes = CC.PREVIEW_RATINGS_SERVICE_KEY, service_type = None, dictionary = None ):
        
        self._original_service_key = original_service_key
        self._service_key = test_service_key
        self._service_type = service_type
        
        self._test_service = None
        self._modifiable_dict = dictionary
        
        if not CG.client_controller.services_manager.ServiceExists( self._original_service_key ):
            
            self._original_service_key = CC.PREVIEW_RATINGS_SERVICE_KEY
            
        self._CloneFromOriginal()
        
    
    def _CloneColours( self, service_key: bytes ):
        
        colours = CG.client_controller.services_manager.GetService( service_key ).GetColours()
        
        self._modifiable_dict[ 'colours' ] = colours
        
    
    def _CloneShape( self, service_key: bytes ):
        
        star_type = ClientRatings.GetStarType( service_key )
        
        self._modifiable_dict[ 'shape' ] = star_type.GetShape()
        self._modifiable_dict[ 'rating_svg' ] = star_type.GetRatingSVG()
        
    
    def _CloneFromOriginal( self ):
        
        rating_service = CG.client_controller.services_manager.GetService( self._original_service_key )
        
        self._service_type = rating_service.GetServiceType() if self._service_type is None else self._service_type
        
        self._service_name = 'example service templated from ' + rating_service.GetName()
        
        self._modifiable_dict = rating_service.GetSerialisableDictionary() if self._modifiable_dict is None else self._modifiable_dict
        
        self._ReloadExampleService()
        
    
    def _ReloadExampleService( self ):
        
        self._test_service = CG.client_controller.services_manager.SetTestServiceData( self._service_key, self._service_type, self._modifiable_dict, self._service_name )
        
    
    def GetServiceKey( self ):
        
        return self._service_key
        
    
    def GetWidget( self, canvas_type = CC.CANVAS_DIALOG, parent = None ) -> RatingIncDecExample | RatingLikeExample | RatingNumericalExample:
        
        if self._service_type == ClientGUICommon.HC.LOCAL_RATING_INCDEC:
            
            return RatingIncDecExample( parent, self._service_key, canvas_type )
            
        elif self._service_type == ClientGUICommon.HC.LOCAL_RATING_LIKE:
            
            return RatingLikeExample( parent, self._service_key, canvas_type )
            
        elif self._service_type == ClientGUICommon.HC.LOCAL_RATING_NUMERICAL:
            
            return RatingNumericalExample( parent, self._service_key, canvas_type )
            
        else:
            
            raise Exception( 'Unknown rating service type!' )
            
        
    
    def SetLiveData( self, k, v ):
        
        self._modifiable_dict[ k ] = v
        
        self._ReloadExampleService()
        
    
    def SetServiceTemplate( self, service_key: bytes ):
        
        CG.client_controller.new_options.SetKey( 'options_ratings_panel_template_service_key' , service_key )
        
        self._CloneColours( service_key )
        self._CloneShape( service_key )
        
        self._ReloadExampleService()
        
    
