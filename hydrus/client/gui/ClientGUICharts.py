import itertools

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
            x_category_axis.setLabelsAngle( 90 )
            
            y_value_axis = QCh.QtCharts.QValueAxis()
            
            y_value_axis.setRange( 0.0, ( highest_usage * 1.2 ) / line_divisor )
            
            y_value_axis.setLabelFormat( '%i{}'.format( unit ) )
            
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
            
        
    
    class FileHistory( QCh.QtCharts.QChartView ):
        
        def __init__( self, parent, file_history: dict ):
            
            QCh.QtCharts.QChartView.__init__( self, parent )
            
            # this lad takes ms timestamp, not s, so * 1000
            # note you have to give this floats for the ms or it throws a type problem of big number to C long
            
            current_files_series = QCh.QtCharts.QLineSeries()
            
            current_files_series.setName( 'files in storage' )
            
            max_num_files = 0
            
            for ( timestamp, num_files ) in file_history[ 'current' ]:
                
                current_files_series.append( timestamp * 1000.0, num_files )
                
                max_num_files = max( max_num_files, num_files )
                
            
            deleted_files_series = QCh.QtCharts.QLineSeries()
            
            deleted_files_series.setName( 'deleted' )
            
            for ( timestamp, num_files ) in file_history[ 'deleted' ]:
                
                deleted_files_series.append( timestamp * 1000.0, num_files )
                
                max_num_files = max( max_num_files, num_files )
                
            
            inbox_files_series = QCh.QtCharts.QLineSeries()
            
            inbox_files_series.setName( 'inbox' )
            
            for ( timestamp, num_files ) in file_history[ 'inbox' ]:
                
                inbox_files_series.append( timestamp * 1000.0, num_files )
                
                max_num_files = max( max_num_files, num_files )
                
            
            # takes ms since epoch
            x_datetime_axis = QCh.QtCharts.QDateTimeAxis()
            
            x_datetime_axis.setTickCount( 25 )
            x_datetime_axis.setLabelsAngle( 90 )
            
            x_datetime_axis.setFormat( 'yyyy-MM-dd' )
            
            y_value_axis = QCh.QtCharts.QValueAxis()
            
            y_value_axis.setLabelFormat( '%\'i' )
            
            chart = QCh.QtCharts.QChart()
            
            chart.addSeries( current_files_series )
            chart.addSeries( inbox_files_series )
            chart.addSeries( deleted_files_series )
            
            chart.addAxis( x_datetime_axis, QC.Qt.AlignBottom )
            chart.addAxis( y_value_axis, QC.Qt.AlignLeft )
            
            current_files_series.attachAxis( x_datetime_axis )
            current_files_series.attachAxis( y_value_axis )
            
            deleted_files_series.attachAxis( x_datetime_axis )
            deleted_files_series.attachAxis( y_value_axis )
            
            inbox_files_series.attachAxis( x_datetime_axis )
            inbox_files_series.attachAxis( y_value_axis )
            
            y_value_axis.setRange( 0, max_num_files )
            
            y_value_axis.applyNiceNumbers()
            
            self.setChart( chart )
            
        
    
except:
    
    QT_CHARTS_OK = False
    
