import wx

class FileDropTarget( wx.PyDropTarget ):
    
    def __init__( self, filenames_callable ):
        
        wx.PyDropTarget.__init__( self )
        
        self._receiving_data_object = wx.DataObjectComposite()
        
        self._hydrus_media_data_object = wx.CustomDataObject( 'application/hydrus-media' )
        self._file_data_object = wx.FileDataObject()
        
        self._receiving_data_object.Add( self._hydrus_media_data_object, True )
        self._receiving_data_object.Add( self._file_data_object )
        
        self.SetDataObject( self._receiving_data_object )
        
        self._filenames_callable = filenames_callable
        
    
    def OnData( self, x, y, result ):
        
        if self.GetData():
            
            received_format = self._receiving_data_object.GetReceivedFormat()
            
            if received_format.GetType() == wx.DF_FILENAME:
                
                paths = self._file_data_object.GetFilenames()
                
                wx.CallAfter( self._filenames_callable, paths )
                
            else:
                
                try:
                    
                    format_id = received_format.GetId()
                    
                except:
                    
                    format_id = None
                    
                
                if format_id == 'application/hydrus-media':
                    
                    pass
                    
                
            
        
        return result
        
    
    def OnDragOver( self, x, y, result ):
        
        return wx.DragCopy
        
    
