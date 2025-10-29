from hydrus.core import HydrusExceptions
from hydrus.core import HydrusText

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUITagSorting
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListBoxes
from hydrus.client.gui.panels.options import ClientGUIOptionsPanelBase
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.metadata import ClientTags

class TagSortPanel( ClientGUIOptionsPanelBase.OptionsPagePanel ):
    
    def __init__( self, parent, new_options ):
        
        super().__init__( parent )
        
        self._new_options = new_options
        
        self._tag_sort_panel = ClientGUICommon.StaticBox( self, 'tag sort' )
        
        self._default_tag_sort_search_page = ClientGUITagSorting.TagSortControl( self._tag_sort_panel, self._new_options.GetDefaultTagSort( CC.TAG_PRESENTATION_SEARCH_PAGE ) )
        self._default_tag_sort_search_page_manage_tags = ClientGUITagSorting.TagSortControl( self._tag_sort_panel, self._new_options.GetDefaultTagSort( CC.TAG_PRESENTATION_SEARCH_PAGE_MANAGE_TAGS ), show_siblings = True )
        self._default_tag_sort_media_viewer = ClientGUITagSorting.TagSortControl( self._tag_sort_panel, self._new_options.GetDefaultTagSort( CC.TAG_PRESENTATION_MEDIA_VIEWER ) )
        self._default_tag_sort_media_viewer_manage_tags = ClientGUITagSorting.TagSortControl( self._tag_sort_panel, self._new_options.GetDefaultTagSort( CC.TAG_PRESENTATION_MEDIA_VIEWER_MANAGE_TAGS ), show_siblings = True )
        
        #
        
        user_namespace_group_by_sort_box = ClientGUICommon.StaticBox( self._tag_sort_panel, 'namespace grouping sort' )
        
        self._user_namespace_group_by_sort = ClientGUIListBoxes.QueueListBox( user_namespace_group_by_sort_box, 8, ClientTags.RenderNamespaceForUser, add_callable = self._AddNamespaceGroupBySort, edit_callable = self._EditNamespaceGroupBySort, paste_callable = self._PasteNamespaceGroupBySort )
        
        #
        
        self._user_namespace_group_by_sort.AddDatas( CG.client_controller.new_options.GetStringList( 'user_namespace_group_by_sort' ) )
        
        #
        
        group_by_sort_text = 'You can manage the custom "(user)" namespace grouping sort here. This lets you put, say, "creator" tags above any other namespace in a tag sort.'
        group_by_sort_text += '\n'
        group_by_sort_text += 'Any namespaces not listed here will be listed afterwards in a-z format, with unnamespaced following, just like the normal (a-z) namespace grouping.'
        
        user_namespace_group_by_sort_box.Add( ClientGUICommon.BetterStaticText( user_namespace_group_by_sort_box, group_by_sort_text ), CC.FLAGS_EXPAND_PERPENDICULAR )
        user_namespace_group_by_sort_box.Add( self._user_namespace_group_by_sort, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        rows = []
        
        rows.append( ( 'Default tag sort in search pages: ', self._default_tag_sort_search_page ) )
        rows.append( ( 'Default tag sort in search page manage tags dialogs: ', self._default_tag_sort_search_page_manage_tags ) )
        rows.append( ( 'Default tag sort in the media viewer: ', self._default_tag_sort_media_viewer ) )
        rows.append( ( 'Default tag sort in media viewer manage tags dialogs: ', self._default_tag_sort_media_viewer_manage_tags ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._tag_sort_panel, rows )
        
        self._tag_sort_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._tag_sort_panel.Add( user_namespace_group_by_sort_box, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._tag_sort_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.setLayout( vbox )
        
    
    def _AddNamespaceGroupBySort( self ):
        
        default = 'namespace'
        
        return self._EditNamespaceGroupBySort( default )
        
    
    def _EditNamespaceGroupBySort( self, namespace ):
        
        message = 'Enter the namespace. Leave blank for unnamespaced tags, use ":" for all unspecified namespaced tags.'
        
        try:
            
            edited_namespace = ClientGUIDialogsQuick.EnterText( self, message, default = namespace, allow_blank = True )
            
        except HydrusExceptions.CancelledException:
            
            raise
            
        
        return edited_namespace
        
    
    def _PasteNamespaceGroupBySort( self ):
        
        try:
            
            text = CG.client_controller.GetClipboardText()
            
        except Exception as e:
            
            raise HydrusExceptions.VetoException()
            
        
        namespaces = HydrusText.DeserialiseNewlinedTexts( text )
        
        return namespaces
        
    
    def UpdateOptions( self ):
        
        self._new_options.SetDefaultTagSort( CC.TAG_PRESENTATION_SEARCH_PAGE, self._default_tag_sort_search_page.GetValue() )
        self._new_options.SetDefaultTagSort( CC.TAG_PRESENTATION_SEARCH_PAGE_MANAGE_TAGS, self._default_tag_sort_search_page_manage_tags.GetValue() )
        self._new_options.SetDefaultTagSort( CC.TAG_PRESENTATION_MEDIA_VIEWER, self._default_tag_sort_media_viewer.GetValue() )
        self._new_options.SetDefaultTagSort( CC.TAG_PRESENTATION_MEDIA_VIEWER_MANAGE_TAGS, self._default_tag_sort_media_viewer_manage_tags.GetValue() )
        
        user_namespace_group_by_sort = self._user_namespace_group_by_sort.GetData()
        
        self._new_options.SetStringList( 'user_namespace_group_by_sort', user_namespace_group_by_sort )
        
    
