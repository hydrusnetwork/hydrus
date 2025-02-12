from hydrus.client.gui.pages import ClientGUIPageManager
from hydrus.client.gui.pages import ClientGUIPagesCore
from hydrus.client.gui.pages import ClientGUISidebarCore
from hydrus.client.gui.pages import ClientGUISidebarDuplicates
from hydrus.client.gui.pages import ClientGUISidebarImporters
from hydrus.client.gui.pages import ClientGUISidebarPetitions
from hydrus.client.gui.pages import ClientGUISidebarQuery

def CreateSidebar( parent, page, page_manager: ClientGUIPageManager.PageManager ) -> ClientGUISidebarCore.Sidebar:
    
    page_type = page_manager.GetType()
    
    if page_type == ClientGUIPagesCore.PAGE_TYPE_DUPLICATE_FILTER:
        
        return ClientGUISidebarDuplicates.SidebarDuplicateFilter( parent, page, page_manager )
        
    elif page_type == ClientGUIPagesCore.PAGE_TYPE_IMPORT_HDD:
        
        return ClientGUISidebarImporters.SidebarImporterHDD( parent, page, page_manager )
        
    elif page_type == ClientGUIPagesCore.PAGE_TYPE_IMPORT_MULTIPLE_GALLERY:
        
        return ClientGUISidebarImporters.SidebarImporterMultipleGallery( parent, page, page_manager )
        
    elif page_type == ClientGUIPagesCore.PAGE_TYPE_IMPORT_MULTIPLE_WATCHER:
        
        return ClientGUISidebarImporters.SidebarImporterMultipleWatcher( parent, page, page_manager )
        
    elif page_type == ClientGUIPagesCore.PAGE_TYPE_IMPORT_SIMPLE_DOWNLOADER:
        
        return ClientGUISidebarImporters.SidebarImporterSimpleDownloader( parent, page, page_manager )
        
    elif page_type == ClientGUIPagesCore.PAGE_TYPE_IMPORT_URLS:
        
        return ClientGUISidebarImporters.SidebarImporterURLs( parent, page, page_manager )
        
    elif page_type == ClientGUIPagesCore.PAGE_TYPE_PETITIONS:
        
        return ClientGUISidebarPetitions.SidebarPetitions( parent, page, page_manager )
        
    elif page_type == ClientGUIPagesCore.PAGE_TYPE_QUERY:
        
        return ClientGUISidebarQuery.SidebarQuery( parent, page, page_manager )
        
    else:
        
        raise NotImplementedError( 'Unknown sidebar type!' )
        
    
