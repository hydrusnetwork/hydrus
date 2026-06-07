from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
import math

import numpy as np
from qtpy import QtCore as QC

from hydrus.client import ClientApplicationCommand as CAC

class ScrollDirection( Enum ):
    VERTICAL = 0
    HORIZONTAL = 1
    
@dataclass( frozen = True )
class LayoutParams:
    viewport_width: int
    viewport_height: int
    thumb_width: int
    thumb_height: int
    thumb_content_width: int
    thumb_content_height: int
    thumb_margin_vertical: int
    thumb_margin_horizontal: int
    scene_margin_vertical: int
    scene_margin_horizontal: int
    scroll_direction: ScrollDirection
    content_alignment: QC.Qt.AlignmentFlag
    zoom: float
    

class ThumbnailLayout( ABC ):
    
    @abstractmethod
    def ArrangeThumbnails( self, thumbnails, params: LayoutParams ) -> QC.QRectF:
        """
        Sets positions and sizes for the given thumbnails.
        It is assumed that the thumbnail list passed here contains ALL thumbnails of the page (so index 0 is at row 0 and col 0, etc.).
        This is not ideal since we have to rearrange all thumbnails every time the layout changes,
        but in more complex layouts the positions of later thumbnails will depend on the positions/sizes of earlier ones,
        so in general we cannot easily recalculate starting from the Nth thumbnail only (but some clever optimizations might be possible).
        The layout parameters and calculation results are cached.
        All other functions of this class rely on the calculations done here, so this should be called first,
        and every time the order or number of thumbnails changes.
        This is because in complex layouts the other functions might need data calculated while
        arranging the thumbnails. If this function is not called first, the others can/will only return dummy values.
        For complex layouts with many thumbnails, this function is a performance bottleneck,
        take care to make it as fast as possible!
        Returns the new scene rect.
        """
        raise NotImplementedError()
        
    
    @abstractmethod
    def MoveFromIndex( self, original_index: int, direction: int ) -> int:
        """
        Returns the new media index after moving left, right, up, or down, starting from the original index.
        Does NOT clamp the result index to the range of valid media indices, that is the caller's responsibility!
        """
        raise NotImplementedError()
        
    
    @abstractmethod
    def JumpPage( self, scene_rect: QC.QRectF, media_index: int, direction: int, percent_visible: float ) -> int:
        """
        Returns the new media index if we jump one page worth,
        if starting from the given media and visible scene rect, in the given direction (-1 = backward, 1 = forward).
        Does NOT clamp the result index to the range of valid media indices, that is the caller's responsibility!
        """
        raise NotImplementedError()
        
    
    @abstractmethod
    def ThumbnailSpanDimensions( self, thumbnail ) -> tuple[int, int]:
        """
        Returns the size of the rect "belonging" to this thumbnail,
        including any thumbnail margins (so possibly larger than the bounding rect of the thumb).
        If passed None, it should return a "generic"/"average"/"fallback" size.
        """
        raise NotImplementedError()
        
    

class RegularGridLayout( ThumbnailLayout ):
    
    def __init__( self ):
        
        self._params = None
        
        self._viewport_width = 0
        self._viewport_height = 0
        self._col_width = 0
        self._row_height = 0
        self._thumbs_in_a_row = 1
        self._thumbs_in_a_col = 1
        self._extra_padding_on_top = 0
        self._extra_padding_on_left = 0
        
    
    def ArrangeThumbnails( self, thumbnails, params: LayoutParams ) -> QC.QRectF:
        
        self._params = params
        
        count = len( thumbnails )
        
        
        tw = round( params.thumb_width * params.zoom )
        th = round( params.thumb_height * params.zoom )
        self._viewport_width = params.viewport_width - 2 * params.scene_margin_horizontal
        self._viewport_height = params.viewport_height - 2 * params.scene_margin_vertical
        self._col_width = tw + 2 * params.thumb_margin_horizontal
        self._row_height = th + 2 * params.thumb_margin_vertical
        self._thumbs_in_a_row = max( 1, self._viewport_width // self._col_width )
        self._thumbs_in_a_col = max( 1, self._viewport_height // self._row_height )
        
        leftover_space_horizontal = self._viewport_width - self._thumbs_in_a_row * self._col_width
        leftover_space_vertical = self._viewport_height - self._thumbs_in_a_col * self._row_height
        self._extra_padding_on_left = 0
        self._extra_padding_on_top = 0
        
        if params.scroll_direction == ScrollDirection.VERTICAL:
            
            if params.content_alignment == QC.Qt.AlignmentFlag.AlignRight:
                
                self._extra_padding_on_left = leftover_space_horizontal
                
            elif params.content_alignment == QC.Qt.AlignmentFlag.AlignHCenter:
                
                self._extra_padding_on_left = leftover_space_horizontal / 2
                
            
        else:
        
            if params.content_alignment == QC.Qt.AlignmentFlag.AlignBottom:
                
                self._extra_padding_on_top = leftover_space_vertical
                
            elif params.content_alignment == QC.Qt.AlignmentFlag.AlignVCenter:
                
                self._extra_padding_on_top = leftover_space_vertical / 2
                
        
        row = 0
        col = 0
        i = 0
        for thumb in thumbnails:
            
            thumb._index = i
            thumb.width = tw
            thumb.height = th
            thumb.setPos( self._extra_padding_on_left + params.scene_margin_horizontal + col * self._col_width + params.thumb_margin_horizontal, self._extra_padding_on_top + params.scene_margin_vertical + row * self._row_height + params.thumb_margin_vertical )
            thumb.setVisible( True )
            
            if params.scroll_direction == ScrollDirection.VERTICAL:
                col += 1
                if col == self._thumbs_in_a_row:
                    col = 0
                    row += 1
            else:
                row += 1
                if row == self._thumbs_in_a_col:
                    row = 0
                    col += 1
                
            i += 1
            
        
        if params.scroll_direction == ScrollDirection.VERTICAL:
            
            return QC.QRectF( 0, 0, self._extra_padding_on_left + 2 * params.scene_margin_horizontal + self._thumbs_in_a_row * self._col_width, self._extra_padding_on_top + 2 * params.scene_margin_vertical + math.ceil( count / self._thumbs_in_a_row ) * self._row_height )
            
        else:
            
            return QC.QRectF( 0, 0, self._extra_padding_on_left + 2 * params.scene_margin_horizontal + math.ceil( count / self._thumbs_in_a_col ) * self._col_width, self._extra_padding_on_top + 2 * params.scene_margin_vertical + self._thumbs_in_a_col * self._row_height )
            
        
    def MoveFromIndex( self, original_index: int, direction: int ) -> int:
        
        rows_moved = 0
        cols_moved = 0
        
        if direction == CAC.MOVE_UP:
            
            rows_moved = -1
            
        elif direction == CAC.MOVE_DOWN:
            
            rows_moved = 1
            
        elif direction == CAC.MOVE_LEFT:
            
            cols_moved = -1
            
        elif direction == CAC.MOVE_RIGHT:
            
            cols_moved = 1
            
        else:
            
            raise NotImplementedError()
            
        if self._params is None or self._params.scroll_direction == ScrollDirection.VERTICAL:
            
            return original_index + rows_moved * self._thumbs_in_a_row + cols_moved
            
        else:
            
            return original_index + rows_moved + cols_moved * self._thumbs_in_a_col
            
        
    
    def JumpPage( self, scene_rect: QC.QRectF, media_index: int, direction: int, percent_visible: float ) -> int:
        
        return media_index + direction * self._thumbs_in_a_col * self._thumbs_in_a_row
        
    
    def ThumbnailSpanDimensions( self, thumbnail ) -> tuple[int, int]:
        
        # This is a regular grid so the result doesn't depend on the passed in thumbnail
        
        return self._col_width, self._row_height
        
    

# TODO: implement horizontal scrolling version (i.e. support scroll_direction HORIZONTAL, like in RegularGridLayout)
class MasonryLayout(ThumbnailLayout): # also known as Waterfall layout
    
    class VariableDimension(Enum):
        WIDTH = 0
        HEIGHT = 1
        
    
    def __init__( self, variable_dimension: VariableDimension ):
        
        self._variable_dimension = variable_dimension
        
        self._params = None
        
        self._viewport_width = 0
        self._viewport_height = 0
        self._col_width = 0
        self._row_height = 0
        self._thumbs_in_a_row = 1
        self._thumbs_in_a_col = 1
        self._col_heights = np.array( [], dtype=np.int64 )
        self._col_indices = np.array( [], dtype=np.int32 ) # _col_indices and _thumb_heights are only needed for the jump page implementation, would be nice to remove somehow
        self._thumb_heights = np.array( [], dtype=np.int32 )
        self._extra_padding_on_left = 0
        
    
    def ArrangeThumbnails( self, thumbnails, params: LayoutParams ) -> QC.QRectF:
        
        self._params = params
        
        count = len( thumbnails )
        
        
        tw = round( params.thumb_width * params.zoom )
        th = round( params.thumb_height * params.zoom )
        tcw = params.thumb_content_width * params.zoom
        tch = params.thumb_content_height * params.zoom
        self._viewport_width = params.viewport_width - 2 * params.scene_margin_horizontal
        self._viewport_height = params.viewport_height - 2 * params.scene_margin_vertical
        self._col_width = tw + 2 * params.thumb_margin_horizontal
        self._row_height = th  + 2 * params.thumb_margin_vertical
        self._thumbs_in_a_row = int( max( 1, self._viewport_width // self._col_width ) )
        self._thumbs_in_a_col = int( max( 1, self._viewport_height // self._row_height ))
        self._col_heights = np.full( self._thumbs_in_a_row, params.scene_margin_vertical, dtype=np.int64 )
        self._col_indices = np.full( count, -1, dtype=np.int32 )
        self._thumb_heights = np.full( count, 0, dtype=np.int32 )
        
        if self._variable_dimension == MasonryLayout.VariableDimension.HEIGHT:
        
            leftover_space_horizontal = self._viewport_width - self._thumbs_in_a_row * self._col_width
            if count < self._thumbs_in_a_row: # handle the case where the thumbs don't even fill a single row

                leftover_space_horizontal += self._col_width * ( self._thumbs_in_a_row - count )
            self._extra_padding_on_left = 0
            
            if params.content_alignment == QC.Qt.AlignmentFlag.AlignRight:
                
                self._extra_padding_on_left = leftover_space_horizontal
                
            elif params.content_alignment == QC.Qt.AlignmentFlag.AlignHCenter:
                
                self._extra_padding_on_left = leftover_space_horizontal / 2
            
        
        thumb_padding_hor = tw - tcw
        thumb_padding_ver = th - tch
        
        row = 0
        col = 0
        i = 0
        
        if self._variable_dimension == MasonryLayout.VariableDimension.HEIGHT:
            
            for thumb in thumbnails:
                
                self._col_heights[ col ] += params.thumb_margin_vertical
                
                thumb._index = i
                thumb.width = tw
                thumb.height = round( thumb_padding_ver + thumb.res_y * tcw / thumb.res_x ) # width/height MUST be integers
                thumb.setPos( self._extra_padding_on_left + params.scene_margin_horizontal + col * self._col_width + params.thumb_margin_horizontal, self._col_heights[ col ] )
                self._col_heights[ col ] += thumb.height + params.thumb_margin_vertical
                thumb.setVisible( True )
                
                self._col_indices[ i ] = col
                self._thumb_heights[ i ] = thumb.height
                
                col += 1
                if col == self._thumbs_in_a_row:
                    col = 0
                    row += 1
                    
                i += 1
                
            
        
        else:
            
            # we can only align horizontally the items in a row after a row is completed,
            # since we don't know the width all the items are taking up ahead of time due to the variable width items
            def set_row_alignment( row_items, current_col_pos ):
                
                row_extra_left_padding = 0
                if params.content_alignment == QC.Qt.AlignmentFlag.AlignRight:
                    
                    row_extra_left_padding = self._viewport_width - current_col_pos
                    
                elif params.content_alignment == QC.Qt.AlignmentFlag.AlignHCenter:
                    
                    row_extra_left_padding = ( self._viewport_width - current_col_pos ) / 2
                                    
                for item in row_items: item.setPos(item.pos().x() + row_extra_left_padding, item.pos().y())
                
            
            current_col_pos = 0
            max_row_width = 0
            row_items = []
            
            for thumb in thumbnails:
                
                current_col_pos += params.thumb_margin_horizontal
                thumb._index = i
                thumb.width = round( thumb_padding_hor + thumb.res_x * tch / thumb.res_y ) # width/height MUST be integers
                thumb.height = th
                
                self._col_indices[ i ] = len(row_items)
                self._thumb_heights[ i ] = th
                
                if current_col_pos + params.thumb_margin_horizontal + thumb.width > self._viewport_width:
                    
                    row += 1
                    
                    if current_col_pos > max_row_width: max_row_width = current_col_pos
                    
                    set_row_alignment( row_items, current_col_pos )
                    row_items = []
                    
                    current_col_pos = params.thumb_margin_horizontal
                    
                
                thumb.setPos( params.scene_margin_horizontal + current_col_pos, params.scene_margin_vertical + params.thumb_margin_vertical + row * self._row_height )
                row_items.append(thumb)
                thumb.setVisible( True )
                current_col_pos += params.thumb_margin_horizontal + thumb.width
                i += 1
                
            
            if row_items: set_row_alignment( row_items, current_col_pos ) # do not forget the last row!
            
        
        if self._variable_dimension == MasonryLayout.VariableDimension.HEIGHT:
            
            return QC.QRectF( 0, 0, self._extra_padding_on_left + 2 * params.scene_margin_horizontal + self._thumbs_in_a_row * self._col_width, params.scene_margin_vertical + self._col_heights.max() )
            
        else:
            
            return QC.QRectF( 0, 0, params.viewport_width, ( row + 1 ) * self._row_height + 2 * params.scene_margin_vertical )
            
        
    
    def MoveFromIndex( self, original_index: int, direction: int ) -> int:
        
        rows_moved = 0
        cols_moved = 0
        
        if direction == CAC.MOVE_UP:
            
            rows_moved = -1
            
        elif direction == CAC.MOVE_DOWN:
            
            rows_moved = 1
            
        elif direction == CAC.MOVE_LEFT:
            
            cols_moved = -1
            
        elif direction == CAC.MOVE_RIGHT:
            
            cols_moved = 1
            
        else:
            
            raise NotImplementedError()
            
        
        return original_index + rows_moved * self._thumbs_in_a_row + cols_moved
        
        
    
    def JumpPage( self, scene_rect: QC.QRectF, media_index: int, direction: int, percent_visible: float ) -> int:
        
        # Basic idea is to stay in the same column and move up/down 1 viewport height's worth
        
        idx = media_index + direction
        height_moved = 0 if direction == -1 else self._thumb_heights[ media_index ] # if moving up we start from the "top" of the current media, if moving down, we also have to jump over the height of the current media too
        
        while True:
            
            # keep stepping until we reach the thumb in the same column one row above/below us
            while 0 <= idx < len( self._col_indices ) and self._col_indices[ idx ] != self._col_indices[ media_index ]:
                
                idx += direction
                
            if direction == -1: # if we are going up, then at this point we've arrived at the top of the previous image in the same column, meaning we already moved its height (if we consider current position to be the selected image's top)
                
                height_moved += self._thumb_heights[ idx ]
                
            # if we moved enough height or reached the start/end, break
            if height_moved >= self._params.viewport_height or idx <= 0 or idx >= len(self._col_indices) - 1: break
            
            if direction == 1: # if we are moving down, then even though we've reached the next image in the same column by this point, we are at the top of that next image so we haven't moved its height down yet - so in the previous check that height should not appear and we are adding it only here after the check
                
                height_moved += self._thumb_heights[ idx ]
                
            idx += direction
            
        return idx
        
    
    def ThumbnailSpanDimensions( self, thumbnail ) -> tuple[int, int]:
        
        if self._params is None or thumbnail is None:
            
            return self._col_width, self._row_height
            
        # this requires that thumbnail borders are included in the thumbnail width/height (which is now true but should be kept in mind)
        return thumbnail.width + 2 * self._params.thumb_margin_horizontal, thumbnail.height + 2 * self._params.thumb_margin_vertical
        
    
