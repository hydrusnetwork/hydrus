import ClientGUICommon
import HydrusGlobals as HG
import json
import wx

class FileDropTarget( wx.DropTarget ):
    
    def __init__( self, parent, filenames_callable = None, url_callable = None, media_callable = None, page_callable = None ):
        
        wx.DropTarget.__init__( self )
        
        self._parent = parent
        
        self._filenames_callable = filenames_callable
        self._url_callable = url_callable
        self._media_callable = media_callable
        self._page_callable = page_callable
        
        self._receiving_data_object = wx.DataObjectComposite()
        
        self._hydrus_media_data_object = wx.CustomDataObject( 'application/hydrus-media' )
        self._hydrus_page_tab_data_object = wx.CustomDataObject( 'application/hydrus-page-tab' )
        self._file_data_object = wx.FileDataObject()
        self._text_data_object = wx.TextDataObject()
        
        self._receiving_data_object.Add( self._hydrus_media_data_object, True )
        self._receiving_data_object.Add( self._hydrus_page_tab_data_object )
        self._receiving_data_object.Add( self._file_data_object )
        self._receiving_data_object.Add( self._text_data_object )
        
        self.SetDataObject( self._receiving_data_object )
        
    
    def OnData( self, x, y, result ):
        
        if self.GetData():
            
            received_format = self._receiving_data_object.GetReceivedFormat()
            
            received_format_type = received_format.GetType()
            
            if received_format_type == wx.DF_FILENAME and self._filenames_callable is not None:
                
                paths = self._file_data_object.GetFilenames()
                
                wx.CallAfter( self._filenames_callable, paths ) # callafter to terminate dnd event now
                
                result = wx.DragNone
                
            elif received_format_type in ( wx.DF_TEXT, wx.DF_UNICODETEXT ) and self._url_callable is not None:
                
                text = self._text_data_object.GetText()
                
                wx.CallAfter( self._url_callable, text ) # callafter to terminate dnd event now
                
                result = wx.DragCopy
                
            else:
                
                try:
                    
                    format_id = received_format.GetId()
                    
                except:
                    
                    format_id = None
                    
                
                if format_id == 'application/hydrus-media' and self._media_callable is not None:
                    
                    mview = self._hydrus_media_data_object.GetData()
                    
                    data = mview.tobytes()
                    
                    ( encoded_page_key, encoded_hashes ) = json.loads( data )
                    
                    page_key = encoded_page_key.decode( 'hex' )
                    hashes = [ encoded_hash.decode( 'hex' ) for encoded_hash in encoded_hashes ]
                    
                    wx.CallAfter( self._media_callable, page_key, hashes ) # callafter so we can terminate dnd event now
                    
                    result = wx.DragMove
                    
                
                if format_id == 'application/hydrus-page-tab' and self._page_callable is not None:
                    
                    mview = self._hydrus_page_tab_data_object.GetData()
                    
                    page_key = mview.tobytes()
                    
                    wx.CallAfter( self._page_callable, page_key ) # callafter so we can terminate dnd event now
                    
                    result = wx.DragMove
                    
                
            
        
        return result
        
    
    def OnDrop( self, x, y ):
        
        screen_position = self._parent.ClientToScreen( ( x, y ) )
        
        drop_tlp = ClientGUICommon.GetXYTopTLP( screen_position )
        my_tlp = ClientGUICommon.GetTLP( self._parent )
        
        if drop_tlp == my_tlp:
            
            return True
            
        else:
            
            return False
            
        
    
    # setting OnDragOver to return copy gives Linux trouble with page tab drops with shift held down
