# noinspection PyUnresolvedReferences
import objc
# noinspection PyUnresolvedReferences
from Foundation import NSObject, NSURL
# noinspection PyUnresolvedReferences
from Quartz import QLPreviewPanel

QLPreviewPanelDataSource = objc.protocolNamed('QLPreviewPanelDataSource')

class HydrusQLDataSource(NSObject, protocols=[QLPreviewPanelDataSource]):
    def initWithCurrentlyLooking_(self, currently_showing):
        self = objc.super(HydrusQLDataSource, self).init()
        if self is None: return None
        
        self.currently_showing = currently_showing
        
        return self
        
    def numberOfPreviewItemsInPreviewPanel_(self, panel):
        return 1 if self.currently_showing is not None else 0
        
    def previewPanel_previewItemAtIndex_(self, panel, index):
        return NSURL.fileURLWithPath_(self.currently_showing)  # or whatever
    
def show_quicklook_for_path( path ):
    
    hydrus_data_source = HydrusQLDataSource.alloc().initWithCurrentlyLooking_(path)
    
    panel = QLPreviewPanel.sharedPreviewPanel()
    panel.setDataSource_(hydrus_data_source)
    panel.makeKeyAndOrderFront_(None)
