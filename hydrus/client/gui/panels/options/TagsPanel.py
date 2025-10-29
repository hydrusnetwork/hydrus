from hydrus.core import HydrusText

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListBoxes
from hydrus.client.gui.panels.options import ClientGUIOptionsPanelBase
from hydrus.client.gui.search import ClientGUIACDropdown
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.metadata import ClientTags

class TagsPanel( ClientGUIOptionsPanelBase.OptionsPagePanel ):
    
    def __init__( self, parent, new_options ):
        
        super().__init__( parent )
        
        self._new_options = new_options
        
        #
        
        favourites_panel = ClientGUICommon.StaticBox( self, 'favourite tags' )
        
        desc = 'These tags will appear in every tag autocomplete results dropdown, under the \'favourites\' tab.'
        
        favourites_st = ClientGUICommon.BetterStaticText( favourites_panel, desc )
        favourites_st.setWordWrap( True )
        
        default_location_context = CG.client_controller.new_options.GetDefaultLocalLocationContext()
        
        self._favourites = ClientGUIListBoxes.ListBoxTagsStringsAddRemove( favourites_panel, CC.COMBINED_TAG_SERVICE_KEY, tag_display_type = ClientTags.TAG_DISPLAY_STORAGE )
        self._favourites_input = ClientGUIACDropdown.AutoCompleteDropdownTagsWrite( favourites_panel, self._favourites.AddTags, default_location_context, CC.COMBINED_TAG_SERVICE_KEY, show_paste_button = True )
        
        self._favourites.tagsChanged.connect( self._favourites_input.SetContextTags )
        
        self._favourites_input.externalCopyKeyPressEvent.connect( self._favourites.keyPressEvent )
        
        
        #
        
        children_panel = ClientGUICommon.StaticBox( self, 'children tags' )
        
        self._num_to_show_in_ac_dropdown_children_tab = ClientGUICommon.NoneableSpinCtrl( children_panel, 40, none_phrase = 'show all', min = 1 )
        tt = 'The "children" tab will show children of the current tag context (usually the list of tags above the autocomplete), ordered by file count. This can quickly get spammy, so I recommend you cull it to a reasonable size.'
        self._num_to_show_in_ac_dropdown_children_tab.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        self._num_to_show_in_ac_dropdown_children_tab.SetValue( 40 ) # init default
        
        #
        
        self._favourites.SetTags( self._new_options.GetStringList( 'favourite_tags' ) )
        
        #
        
        self._num_to_show_in_ac_dropdown_children_tab.SetValue( self._new_options.GetNoneableInteger( 'num_to_show_in_ac_dropdown_children_tab' ) )
        
        #
        
        favourites_panel.Add( favourites_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        favourites_panel.Add( self._favourites, CC.FLAGS_EXPAND_BOTH_WAYS )
        favourites_panel.Add( self._favourites_input )
        
        #
        
        rows = []
        
        rows.append( ( 'How many tags to show in the children tab: ', self._num_to_show_in_ac_dropdown_children_tab ) )
        
        gridbox = ClientGUICommon.WrapInGrid( children_panel, rows )
        
        children_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, children_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, favourites_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.setLayout( vbox )
        
        #
        
        self._favourites_input.tagsPasted.connect( self.AddTagsOnlyAdd )
        
    
    def AddTagsOnlyAdd( self, tags ):
        
        current_tags = self._favourites.GetTags()
        
        tags = { tag for tag in tags if tag not in current_tags }
        
        if len( tags ) > 0:
            
            self._favourites.AddTags( tags )
            
        
    
    def UpdateOptions( self ):
        
        self._new_options.SetStringList( 'favourite_tags', sorted( self._favourites.GetTags(), key = HydrusText.HumanTextSortKey ) )
        
        #
        
        self._new_options.SetNoneableInteger( 'num_to_show_in_ac_dropdown_children_tab', self._num_to_show_in_ac_dropdown_children_tab.GetValue() )
        
    
