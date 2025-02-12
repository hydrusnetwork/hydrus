from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusNumbers

from hydrus.client import ClientGlobals as CG
from hydrus.client.gui.pages import ClientGUIPageManager
from hydrus.client.gui.pages import ClientGUIMediaResultsPanel

class MediaResultsPanelLoading( ClientGUIMediaResultsPanel.MediaResultsPanel ):
    
    def __init__( self, parent, page_key, page_manager: ClientGUIPageManager.PageManager ):
        
        self._current = None
        self._max = None
        
        super().__init__( parent, page_key, page_manager, [] )
        
        CG.client_controller.sub( self, 'SetNumQueryResults', 'set_num_query_results' )
        
    
    def _GetPrettyStatusForStatusBar( self ):
        
        s = 'Loading' + HC.UNICODE_ELLIPSIS
        
        if self._current is not None:
            
            s += ' ' + HydrusNumbers.ToHumanInt( self._current )
            
            if self._max is not None:
                
                s += ' of ' + HydrusNumbers.ToHumanInt( self._max )
                
            
        
        return s
        
    
    def GetSortedMedia( self ):
        
        return []
        
    
    def SetNumQueryResults( self, page_key, num_current, num_max ):
        
        if page_key == self._page_key:
            
            self._current = num_current
            
            self._max = num_max
            
            self._PublishSelectionChange()
            
        
    
