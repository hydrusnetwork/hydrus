import collections.abc

from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientServices
from hydrus.client import ClientThreading
from hydrus.client.gui import ClientGUIAsync
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui.metadata import ClientGUITagFilter

def ManageServiceOptionsTagFilter(
    win: QW.QWidget,
    service_key: bytes,
    new_tags_to_block: collections.abc.Collection[ str ] | None = None,
    new_tags_to_allow: collections.abc.Collection[ str ] | None = None
):
    
    service: ClientServices.ServiceRepository = CG.client_controller.services_manager.GetService( service_key )
    
    tag_filter = service.GetTagFilter().Duplicate()
    
    if new_tags_to_block is not None:
        
        tag_filter.SetRules( new_tags_to_block, HC.FILTER_BLACKLIST )
        
    
    if new_tags_to_allow is not None:
        
        tag_filter.SetRules( new_tags_to_allow, HC.FILTER_WHITELIST )
        
    
    with ClientGUITopLevelWindowsPanels.DialogEdit( win, 'edit tag repository tag filter' ) as dlg:
        
        namespaces = CG.client_controller.network_engine.domain_manager.GetParserNamespaces()
        
        message = 'The repository will apply this to all new pending tags that are uploaded to it. Anything that does not pass is silently discarded.'
        
        panel = ClientGUITagFilter.EditTagFilterPanel( dlg, tag_filter, message = message, namespaces = namespaces )
        
        dlg.SetPanel( panel )
        
        if dlg.exec() == QW.QDialog.DialogCode.Accepted:
            
            tag_filter = panel.GetValue()
            
            job_status = ClientThreading.JobStatus()
            
            job_status.SetStatusTitle( 'setting tag filter' )
            job_status.SetStatusText( 'uploading' + HC.UNICODE_ELLIPSIS )
            
            CG.client_controller.pub( 'message', job_status )
            
            def work_callable():
                
                service.Request( HC.POST, 'tag_filter', { 'tag_filter' : tag_filter } )
                
                return 1
                
            
            def publish_callable( gumpf ):
                
                job_status.SetStatusText( 'done!' )
                
                job_status.FinishAndDismiss( 5 )
                
                service.SetAccountRefreshDueNow()
                
            
            def errback_ui_cleanup_callable():
                
                job_status.SetStatusText( 'error!' )
                
                job_status.Finish()
                
            
            job = ClientGUIAsync.AsyncQtJob( win, work_callable, publish_callable, errback_ui_cleanup_callable = errback_ui_cleanup_callable )
            
            job.start()
            
        
    
