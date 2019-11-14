from qtpy import QtCore as QC

try:
    
    from qtpy import QtCharts as QCh
    
    QT_CHARTS_OK = True
    
    class BarChartBandwidthHistory( QCh.QtCharts.QChartView ):
        
        def __init__( self, parent, monthly_usage ):
            
            QCh.QtCharts.QChartView.__init__( self, parent )
            
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
            
            ( month_strs, month_values ) = zip( *monthly_usage )
            
            bar_set = QCh.QtCharts.QBarSet( 'Bandwidth' )
            x_category_axis = QCh.QtCharts.QBarCategoryAxis()
            
            bar_set.append( month_values )
            x_category_axis.append( month_strs )
            
            y_value_axis = QCh.QtCharts.QValueAxis()
            
            y_value_axis.setRange( 0.0, ( highest_usage * 1.2 ) / line_divisor )
            
            y_value_axis.setTitleText( '({})'.format( unit ) )
            
            y_value_axis.applyNiceNumbers()
            
            bar_series = QCh.QtCharts.QBarSeries()
            
            bar_series.append( bar_set )
            
            chart = QCh.QtCharts.QChart()
            
            chart.addSeries( bar_series )
            chart.addAxis( x_category_axis, QC.Qt.AlignBottom )
            chart.addAxis( y_value_axis, QC.Qt.AlignLeft )
            
            chart.legend().setVisible( False )
            
            bar_series.attachAxis( x_category_axis )
            bar_series.attachAxis( y_value_axis )
            
            self.setChart( chart )
            
        
    
except:
    
    QT_CHARTS_OK = False
    
