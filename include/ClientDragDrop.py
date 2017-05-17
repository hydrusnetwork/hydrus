import HydrusGlobals as HG
import wx

class FileDropTarget( wx.PyDropTarget ):
    
    def __init__( self, filenames_callable = None, url_callable = None ):
        
        wx.PyDropTarget.__init__( self )
        
        self._filenames_callable = filenames_callable
        self._url_callable = url_callable
        
        self._receiving_data_object = wx.DataObjectComposite()
        
        self._hydrus_media_data_object = wx.CustomDataObject( 'application/hydrus-media' )
        self._file_data_object = wx.FileDataObject()
        self._text_data_object = wx.TextDataObject()
        
        self._receiving_data_object.Add( self._hydrus_media_data_object, True )
        self._receiving_data_object.Add( self._file_data_object )
        self._receiving_data_object.Add( self._text_data_object )
        
        self.SetDataObject( self._receiving_data_object )
        
    
    def OnData( self, x, y, result ):
        
        if self.GetData():
            
            received_format = self._receiving_data_object.GetReceivedFormat()
            
            received_format_type = received_format.GetType()
            
            if received_format_type == wx.DF_FILENAME and self._filenames_callable is not None:
                
                paths = self._file_data_object.GetFilenames()
                
                wx.CallAfter( self._filenames_callable, paths )
                
            elif received_format_type in ( wx.DF_TEXT, wx.DF_UNICODETEXT ) and self._url_callable is not None:
                
                text = self._text_data_object.GetText()
                
                self._url_callable( text )
                
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
        
    
