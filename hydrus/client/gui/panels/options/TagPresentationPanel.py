import random

from qtpy import QtGui as QG
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusTags

from hydrus.client import ClientConstants as CC
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListBoxes
from hydrus.client.gui.metadata import ClientGUITagSummaryGenerator
from hydrus.client.gui.panels.options import ClientGUIOptionsPanelBase
from hydrus.client.gui.widgets import ClientGUIColourPicker
from hydrus.client.gui.widgets import ClientGUICommon

class TagPresentationPanel( ClientGUIOptionsPanelBase.OptionsPagePanel ):
    
    def __init__( self, parent, new_options ):
        
        super().__init__( parent )
        
        self._new_options = new_options
        
        #
        
        self._tag_banners_panel = ClientGUICommon.StaticBox( self, 'tag banners' )
        
        tag_summary_generator = self._new_options.GetTagSummaryGenerator( 'thumbnail_top' )
        
        self._thumbnail_top = ClientGUITagSummaryGenerator.TagSummaryGeneratorButton( self._tag_banners_panel, tag_summary_generator )
        
        tag_summary_generator = self._new_options.GetTagSummaryGenerator( 'thumbnail_bottom_right' )
        
        self._thumbnail_bottom_right = ClientGUITagSummaryGenerator.TagSummaryGeneratorButton( self._tag_banners_panel, tag_summary_generator )
        
        tag_summary_generator = self._new_options.GetTagSummaryGenerator( 'media_viewer_top' )
        
        self._media_viewer_top = ClientGUITagSummaryGenerator.TagSummaryGeneratorButton( self._tag_banners_panel, tag_summary_generator )
        
        #
        
        self._selection_tags_panel = ClientGUICommon.StaticBox( self, 'selection tags' )
        
        self._number_of_unselected_medias_to_present_tags_for = ClientGUICommon.NoneableSpinCtrl( self._selection_tags_panel, 4096, max = 10000000 )
        
        #
        
        namespace_rendering_panel = ClientGUICommon.StaticBox( self, 'namespace rendering' )
        
        render_st = ClientGUICommon.BetterStaticText( namespace_rendering_panel, label = 'Namespaced tags are stored and directly edited in hydrus as "namespace:subtag", but most presentation windows can display them differently.' )
        
        self._show_namespaces = QW.QCheckBox( namespace_rendering_panel )
        self._show_number_namespaces = QW.QCheckBox( namespace_rendering_panel )
        self._show_number_namespaces.setToolTip( ClientGUIFunctions.WrapToolTip( 'This lets unnamespaced "16:9" show as that, not hiding the "16".' ) )
        self._show_subtag_number_namespaces = QW.QCheckBox( namespace_rendering_panel )
        self._show_subtag_number_namespaces.setToolTip( ClientGUIFunctions.WrapToolTip( 'This lets unnamespaced "page:3" show as that, not hiding the "page" where it can get mixed with chapter etc...' ) )
        self._namespace_connector = QW.QLineEdit( namespace_rendering_panel )
        
        #
        
        other_rendering_panel = ClientGUICommon.StaticBox( self, 'other rendering' )
        
        self._sibling_connector = QW.QLineEdit( other_rendering_panel )
        
        self._fade_sibling_connector = QW.QCheckBox( other_rendering_panel )
        tt = 'If set, then if the sibling goes from one namespace to another, that colour will fade across the distance of the sibling connector. Just a bit of fun.'
        self._fade_sibling_connector.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._sibling_connector_custom_namespace_colour = ClientGUICommon.NoneableTextCtrl( other_rendering_panel, 'system', none_phrase = 'use ideal tag colour' )
        tt = 'The sibling connector can use a particular namespace\'s colour.'
        self._sibling_connector_custom_namespace_colour.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._or_connector = QW.QLineEdit( other_rendering_panel )
        tt = 'When an OR predicate is rendered on one line, it splits the components by this text.'
        self._or_connector.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._or_connector_custom_namespace_colour = QW.QLineEdit( other_rendering_panel )
        tt = 'The "OR:" row can use a particular namespace\'s colour.'
        self._or_connector_custom_namespace_colour.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._replace_tag_underscores_with_spaces = QW.QCheckBox( other_rendering_panel )
        self._replace_tag_underscores_with_spaces.setToolTip( ClientGUIFunctions.WrapToolTip( 'This does not logically merge tags or change behaviour in any way, it only changes tag rendering in UI.' ) )
        
        self._replace_tag_emojis_with_boxes = QW.QCheckBox( other_rendering_panel )
        self._replace_tag_emojis_with_boxes.setToolTip( ClientGUIFunctions.WrapToolTip( 'This will replace emojis and weird symbols with □ in front-facing user views, in case you are getting crazy rendering. It may break some CJK punctuation.' ) )
        
        #
        
        namespace_colours_panel = ClientGUICommon.StaticBox( self, 'namespace colours' )
        
        self._namespace_colours = ClientGUIListBoxes.ListBoxTagsColourOptions( namespace_colours_panel, HC.options[ 'namespace_colours' ] )
        
        self._add_namespace_colour = ClientGUICommon.BetterButton( self, 'add', self._AddNamespaceColour )
        self._edit_namespace_colour = ClientGUICommon.BetterButton( self, 'edit', self._EditNamespaceColour )
        self._delete_namespace_colour = ClientGUICommon.BetterButton( self, 'delete', self._DeleteNamespaceColour )
        
        #
        
        self._number_of_unselected_medias_to_present_tags_for.SetValue( self._new_options.GetNoneableInteger( 'number_of_unselected_medias_to_present_tags_for' ) )
        self._number_of_unselected_medias_to_present_tags_for.setToolTip( ClientGUIFunctions.WrapToolTip( 'The "selection tags" box on any search page will show the tags for all files when none are selected. To save CPU, very large pages will cap out and not try to generate (and regenerate on any changes) for everything.') )
        
        self._show_namespaces.setChecked( new_options.GetBoolean( 'show_namespaces' ) )
        self._show_number_namespaces.setChecked( new_options.GetBoolean( 'show_number_namespaces' ) )
        self._show_subtag_number_namespaces.setChecked( new_options.GetBoolean( 'show_subtag_number_namespaces' ) )
        self._namespace_connector.setText( new_options.GetString( 'namespace_connector' ) )
        self._replace_tag_underscores_with_spaces.setChecked( new_options.GetBoolean( 'replace_tag_underscores_with_spaces' ) )
        self._replace_tag_emojis_with_boxes.setChecked( new_options.GetBoolean( 'replace_tag_emojis_with_boxes' ) )
        self._sibling_connector.setText( new_options.GetString( 'sibling_connector' ) )
        self._fade_sibling_connector.setChecked( new_options.GetBoolean( 'fade_sibling_connector' ) )
        self._sibling_connector_custom_namespace_colour.SetValue( new_options.GetNoneableString( 'sibling_connector_custom_namespace_colour' ) )
        self._or_connector.setText( new_options.GetString( 'or_connector' ) )
        self._or_connector_custom_namespace_colour.setText( new_options.GetNoneableString( 'or_connector_custom_namespace_colour' ) )
        
        #
        
        rows = []
        
        rows.append( ( 'Max number of thumbnails to compute tags for when none are selected: ', self._number_of_unselected_medias_to_present_tags_for ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._selection_tags_panel, rows )
        
        self._selection_tags_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        namespace_colours_panel.Add( self._namespace_colours, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._add_namespace_colour, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, self._edit_namespace_colour, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, self._delete_namespace_colour, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        namespace_colours_panel.Add( hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        vbox = QP.VBoxLayout()
        
        #
        
        rows = []
        
        rows.append( ( 'On thumbnail top:', self._thumbnail_top ) )
        rows.append( ( 'On thumbnail bottom-right:', self._thumbnail_bottom_right ) )
        rows.append( ( 'On media viewer top:', self._media_viewer_top ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        self._tag_banners_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        rows = []
        
        rows.append( ( 'Show namespaces: ', self._show_namespaces ) )
        rows.append( ( 'Show namespace if it is a number: ', self._show_number_namespaces ) )
        rows.append( ( 'Show namespace if subtag is a number: ', self._show_subtag_number_namespaces ) )
        rows.append( ( 'If shown, namespace connecting string: ', self._namespace_connector ) )
        
        gridbox = ClientGUICommon.WrapInGrid( namespace_rendering_panel, rows )
        
        namespace_rendering_panel.Add( render_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        namespace_rendering_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        rows = []
        
        rows.append( ( 'Sibling connecting string: ', self._sibling_connector ) )
        rows.append( ( 'Fade the colour of the sibling connector string on Qt6: ', self._fade_sibling_connector ) )
        rows.append( ( 'Namespace for the colour of the sibling connecting string: ', self._sibling_connector_custom_namespace_colour ) )
        rows.append( ( 'OR connecting string (on one line): ', self._or_connector ) )
        rows.append( ( 'Namespace for the OR top row: ', self._or_connector_custom_namespace_colour ) )
        rows.append( ( 'EXPERIMENTAL: Replace all underscores with spaces: ', self._replace_tag_underscores_with_spaces ) )
        rows.append( ( 'EXPERIMENTAL: Replace all emojis with □: ', self._replace_tag_emojis_with_boxes ) )
        
        gridbox = ClientGUICommon.WrapInGrid( other_rendering_panel, rows )
        
        other_rendering_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        QP.AddToLayout( vbox, self._tag_banners_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._selection_tags_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, namespace_rendering_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, other_rendering_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, namespace_colours_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        self._NamespacesUpdated()
        self._SiblingColourStuffClicked()
        
        self._show_namespaces.clicked.connect( self._NamespacesUpdated )
        self._fade_sibling_connector.clicked.connect( self._SiblingColourStuffClicked )
        
        self.setLayout( vbox )
        
    
    def _AddNamespaceColour( self ):
        
        try:
            
            namespace = ClientGUIDialogsQuick.EnterText( self, 'Enter the namespace.' )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        namespace = namespace.lower().strip()
        
        if namespace in ( '', ':' ):
            
            ClientGUIDialogsMessage.ShowWarning( self, 'Sorry, that namespace means unnamespaced/default namespaced, which are already listed.' )
            
            return
            
        
        while namespace.endswith( ':' ):
            
            namespace = namespace[:-1]
            
        
        if namespace != 'system':
            
            namespace = HydrusTags.StripTagTextOfGumpf( namespace )
            
        
        existing_namespaces = self._namespace_colours.GetNamespaceColours().keys()
        
        if namespace in existing_namespaces:
            
            ClientGUIDialogsMessage.ShowWarning( self, 'Sorry, that namespace is already listed!' )
            
            return
            
        
        self._namespace_colours.SetNamespaceColour( namespace, QG.QColor( random.randint(0,255), random.randint(0,255), random.randint(0,255) ) )
        
    
    def _DeleteNamespaceColour( self ):
        
        self._namespace_colours.DeleteSelected()
        
    
    def _EditNamespaceColour( self ):
        
        results = self._namespace_colours.GetSelectedNamespaceColours()
        
        for ( namespace, ( r, g, b ) ) in list( results.items() ):
            
            colour = QG.QColor( r, g, b )
            
            colour = ClientGUIColourPicker.EditColour( self, colour )
            
            self._namespace_colours.SetNamespaceColour( namespace, colour )
            
        
    
    def _SiblingColourStuffClicked( self ):
        
        choice_available = not self._fade_sibling_connector.isChecked()
        
        self._sibling_connector_custom_namespace_colour.setEnabled( choice_available )
        
    
    def _NamespacesUpdated( self ):
        
        self._show_number_namespaces.setEnabled( not self._show_namespaces.isChecked() )
        self._show_subtag_number_namespaces.setEnabled( not self._show_namespaces.isChecked() )
        
    
    def UpdateOptions( self ):
        
        self._new_options.SetNoneableInteger( 'number_of_unselected_medias_to_present_tags_for', self._number_of_unselected_medias_to_present_tags_for.GetValue() )
        
        self._new_options.SetTagSummaryGenerator( 'thumbnail_top', self._thumbnail_top.GetValue() )
        self._new_options.SetTagSummaryGenerator( 'thumbnail_bottom_right', self._thumbnail_bottom_right.GetValue() )
        self._new_options.SetTagSummaryGenerator( 'media_viewer_top', self._media_viewer_top.GetValue() )
        
        self._new_options.SetBoolean( 'show_namespaces', self._show_namespaces.isChecked() )
        self._new_options.SetBoolean( 'show_number_namespaces', self._show_number_namespaces.isChecked() )
        self._new_options.SetBoolean( 'show_subtag_number_namespaces', self._show_subtag_number_namespaces.isChecked() )
        self._new_options.SetString( 'namespace_connector', self._namespace_connector.text() )
        self._new_options.SetBoolean( 'replace_tag_underscores_with_spaces', self._replace_tag_underscores_with_spaces.isChecked() )
        self._new_options.SetBoolean( 'replace_tag_emojis_with_boxes', self._replace_tag_emojis_with_boxes.isChecked() )
        self._new_options.SetString( 'sibling_connector', self._sibling_connector.text() )
        self._new_options.SetBoolean( 'fade_sibling_connector', self._fade_sibling_connector.isChecked() )
        
        self._new_options.SetNoneableString( 'sibling_connector_custom_namespace_colour', self._sibling_connector_custom_namespace_colour.GetValue() )
        
        self._new_options.SetString( 'or_connector', self._or_connector.text() )
        self._new_options.SetNoneableString( 'or_connector_custom_namespace_colour', self._or_connector_custom_namespace_colour.text() )
        
        HC.options[ 'namespace_colours' ] = self._namespace_colours.GetNamespaceColours()
        
    
