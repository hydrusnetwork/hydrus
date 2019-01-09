import wx

import matplotlib

matplotlib.use( 'WXagg' )

from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg
from matplotlib.figure import Figure

class BarChartBandwidthHistory( FigureCanvasWxAgg ):
    
    def __init__( self, parent, monthly_usage ):
        
        divisor = 1.0
        unit = 'B'
        
        highest_usage = max( ( m[1] for m in monthly_usage ) )
        
        lines = [ ( 1073741824.0, 'GB' ), ( 1048576.0, 'MB' ), ( 1024.0, 'KB' ) ]
        
        for ( line_divisor, line_unit ) in lines:
            
            if highest_usage > line_divisor:
                
                divisor = line_divisor
                unit = line_unit
                
                break
                
            
        
        monthly_usage = [ ( month_str, month_value / divisor ) for ( month_str, month_value ) in monthly_usage ]
        
        ( r, g, b, a ) = wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ).Get()
        
        facecolor = '#{:0>2x}{:0>2x}{:0>2x}'.format( r, g, b )
        
        figure = Figure( figsize = ( 6.4, 4.8 ), dpi = 80, facecolor = facecolor, edgecolor = facecolor )
        
        axes = figure.add_subplot( 111 )
        
        x_indices = list( range( len( monthly_usage ) ) )
        
        axes.bar( x_indices, [ i[1] for i in monthly_usage ] )
        
        axes.set_xticks( x_indices )
        axes.set_xticklabels( [ i[0] for i in monthly_usage ] )
        
        axes.grid( True )
        axes.set_axisbelow( True )
        
        axes.set_ylabel( '(' + unit + ')' )
        
        axes.set_title( 'historical usage' )
        
        FigureCanvasWxAgg.__init__( self, parent, -1, figure )
        
    
