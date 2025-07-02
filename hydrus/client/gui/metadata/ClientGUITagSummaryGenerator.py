import collections
import collections.abc

from qtpy import QtWidgets as QW
from qtpy import QtGui as QG

from hydrus.core import HydrusExceptions
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTags
from hydrus.core import HydrusText

from hydrus.client import ClientConstants as CC
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListBoxes
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.gui.widgets import ClientGUIColourPicker
from hydrus.client.metadata import ClientTags

class TagSummaryGenerator( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_TAG_SUMMARY_GENERATOR
    SERIALISABLE_NAME = 'Tag Summary Generator'
    SERIALISABLE_VERSION = 2
    
    def __init__( self, background_colour = None, text_colour = None, namespace_info = None, separator = None, example_tags = None, show = True ):
        
        if background_colour is None:
            
            background_colour = QG.QColor( 223, 227, 230, 255 )
            
        
        if text_colour is None:
            
            text_colour = QG.QColor( 1, 17, 26, 255 )
            
        
        if namespace_info is None:
            
            namespace_info = []
            
            namespace_info.append( ( 'creator', '', ', ' ) )
            namespace_info.append( ( 'series', '', ', ' ) )
            namespace_info.append( ( 'title', '', ', ' ) )
            
        
        if separator is None:
            
            separator = ' - '
            
        
        if example_tags is None:
            
            example_tags = []
            
        
        self._background_colour = background_colour
        self._text_colour = text_colour
        self._namespace_info = namespace_info
        self._separator = separator
        self._example_tags = list( example_tags )
        self._show = show
        
        self._UpdateNamespaceLookup()
        
    
    def _GetSerialisableInfo( self ):
        
        bc = self._background_colour
        
        background_colour_rgba = [ bc.red(), bc.green(), bc.blue(), bc.alpha() ]
        
        tc = self._text_colour
        
        text_colour_rgba = [ tc.red(), tc.green(), tc.blue(), tc.alpha() ]
        
        return ( background_colour_rgba, text_colour_rgba, self._namespace_info, self._separator, self._example_tags, self._show )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( background_rgba, text_rgba, self._namespace_info, self._separator, self._example_tags, self._show ) = serialisable_info
        
        ( r, g, b, a ) = background_rgba
        
        self._background_colour = QG.QColor( r, g, b, a )
        
        ( r, g, b, a ) = text_rgba
        
        self._text_colour = QG.QColor( r, g, b, a )
        
        self._namespace_info = [ tuple( row ) for row in self._namespace_info ]
        
        self._UpdateNamespaceLookup()
        
    
    def _UpdateNamespaceLookup( self ):
        
        self._interesting_namespaces = { namespace for ( namespace, prefix, separator ) in self._namespace_info }
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( namespace_info, separator, example_tags ) = old_serialisable_info
            
            background_rgba = ( 223, 227, 230, 255 )
            text_rgba = ( 1, 17, 26, 255 )
            show = True
            
            new_serialisable_info = ( background_rgba, text_rgba, namespace_info, separator, example_tags, show )
            
            return ( 2, new_serialisable_info )
            
        
    
    def GenerateExampleSummary( self ):
        
        if not self._show:
            
            return 'not showing'
            
        else:
            
            return self.GenerateSummary( self._example_tags )
            
        
    
    def GenerateSummary( self, tags, max_length = None ):
        
        if not self._show:
            
            return ''
            
        
        namespaces_to_subtags = collections.defaultdict( list )
        
        for tag in tags:
            
            ( namespace, subtag ) = HydrusTags.SplitTag( tag )
            
            if namespace in self._interesting_namespaces:
                
                subtag = ClientTags.RenderTag( subtag, render_for_user = True )
                
                namespaces_to_subtags[ namespace ].append( subtag )
                
            
        
        for ( namespace, unsorted_l ) in list( namespaces_to_subtags.items() ):
            
            sorted_l = HydrusTags.SortNumericTags( unsorted_l )
            
            sorted_l = HydrusTags.CollapseMultipleSortedNumericTagsToMinMax( sorted_l )
            
            namespaces_to_subtags[ namespace ] = sorted_l
            
        
        namespace_texts = []
        
        for ( namespace, prefix, separator ) in self._namespace_info:
            
            subtags = namespaces_to_subtags[ namespace ]
            
            if len( subtags ) > 0:
                
                namespace_text = prefix + separator.join( namespaces_to_subtags[ namespace ] )
                
                namespace_texts.append( namespace_text )
                
            
        
        summary = self._separator.join( namespace_texts )
        
        if max_length is not None:
            
            summary = summary[:max_length]
            
        
        return summary
        
    
    def GetBackgroundColour( self ):
        
        return self._background_colour
        
    
    def GetTextColour( self ):
        
        return self._text_colour
        
    
    def ToTuple( self ):
        
        return ( self._background_colour, self._text_colour, self._namespace_info, self._separator, self._example_tags, self._show )
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_TAG_SUMMARY_GENERATOR ] = TagSummaryGenerator

class EditTagSummaryGeneratorPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, tag_summary_generator: TagSummaryGenerator ):
        
        super().__init__( parent )
        
        show_panel = ClientGUICommon.StaticBox( self, 'shows' )
        
        self._show = QW.QCheckBox( show_panel )
        
        edit_panel = ClientGUICommon.StaticBox( self, 'edit' )
        
        self._background_colour = ClientGUIColourPicker.AlphaColourControl( edit_panel )
        self._text_colour = ClientGUIColourPicker.AlphaColourControl( edit_panel )
        
        self._namespaces_listbox = ClientGUIListBoxes.QueueListBox( edit_panel, 8, self._ConvertNamespaceToListBoxString, self._AddNamespaceInfo, self._EditNamespaceInfo )
        
        self._separator = QW.QLineEdit( edit_panel )
        
        example_panel = ClientGUICommon.StaticBox( self, 'example' )
        
        self._example_tags = QW.QPlainTextEdit( example_panel )
        
        self._test_result = QW.QLineEdit( example_panel )
        self._test_result.setReadOnly( True )
        
        #
        
        ( background_colour, text_colour, namespace_info, separator, example_tags, show ) = tag_summary_generator.ToTuple()
        
        self._show.setChecked( show )
        
        self._background_colour.SetValue( background_colour )
        self._text_colour.SetValue( text_colour )
        self._namespaces_listbox.AddDatas( namespace_info )
        self._separator.setText( separator )
        self._example_tags.setPlainText( '\n'.join( example_tags ) )
        
        self._UpdateTest()
        
        #
        
        rows = []
        
        rows.append( ( 'currently shows (turn off to hide): ', self._show ) )
        
        gridbox = ClientGUICommon.WrapInGrid( show_panel, rows )
        
        show_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        rows = []
        
        rows.append( ( 'background colour: ', self._background_colour ) )
        rows.append( ( 'text colour: ', self._text_colour ) )
        
        gridbox = ClientGUICommon.WrapInGrid( edit_panel, rows )
        
        edit_panel.Add( ClientGUICommon.BetterStaticText( edit_panel, 'The colours only work for the thumbnails right now!' ), CC.FLAGS_EXPAND_PERPENDICULAR )
        edit_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        edit_panel.Add( self._namespaces_listbox, CC.FLAGS_EXPAND_BOTH_WAYS )
        edit_panel.Add( ClientGUICommon.WrapInText( self._separator, edit_panel, 'separator' ), CC.FLAGS_EXPAND_PERPENDICULAR )
        
        example_panel.Add( ClientGUICommon.BetterStaticText( example_panel, 'Enter some newline-separated tags here to see what your current object would generate.' ), CC.FLAGS_EXPAND_PERPENDICULAR )
        example_panel.Add( self._example_tags, CC.FLAGS_EXPAND_BOTH_WAYS )
        example_panel.Add( self._test_result, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, show_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, edit_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, example_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
        #
        
        self._show.clicked.connect( self._UpdateTest )
        self._separator.textChanged.connect( self._UpdateTest )
        self._example_tags.textChanged.connect( self._UpdateTest )
        self._namespaces_listbox.listBoxChanged.connect( self._UpdateTest )
        
    
    def _AddNamespaceInfo( self ):
        
        namespace = ''
        prefix = ''
        separator = ', '
        
        namespace_info = ( namespace, prefix, separator )
        
        return self._EditNamespaceInfo( namespace_info )
        
    
    def _ConvertNamespaceToListBoxString( self, namespace_info ):
        
        ( namespace, prefix, separator ) = namespace_info
        
        if namespace == '':
            
            pretty_namespace = 'unnamespaced'
            
        else:
            
            pretty_namespace = namespace
            
        
        pretty_prefix = prefix
        pretty_separator = separator
        
        return pretty_namespace + ' | prefix: "' + pretty_prefix + '" | separator: "' + pretty_separator + '"'
        
    
    def _EditNamespaceInfo( self, namespace_info ):
        
        ( namespace, prefix, separator ) = namespace_info
        
        message = 'Edit namespace.'
        
        try:
            
            namespace = ClientGUIDialogsQuick.EnterText( self, message, default = namespace, allow_blank = True )
            
        except HydrusExceptions.CancelledException:
            
            raise
            
        
        message = 'Edit prefix.'
        
        try:
            
            prefix = ClientGUIDialogsQuick.EnterText( self, message, default = prefix, allow_blank = True )
            
        except HydrusExceptions.CancelledException:
            
            raise
            
        
        message = 'Edit separator.'
        
        try:
            
            separator = ClientGUIDialogsQuick.EnterText( self, message, default = separator, allow_blank = True )
            
        except HydrusExceptions.CancelledException:
            
            raise
            
        
        namespace_info = ( namespace, prefix, separator )
        
        return namespace_info
        
    
    def _UpdateTest( self ):
        
        tag_summary_generator = self.GetValue()
        
        self._test_result.setText( tag_summary_generator.GenerateExampleSummary() )
        
    
    def GetValue( self ) -> TagSummaryGenerator:
        
        show = self._show.isChecked()
        
        background_colour = self._background_colour.GetValue()
        text_colour = self._text_colour.GetValue()
        namespace_info = self._namespaces_listbox.GetData()
        separator = self._separator.text()
        example_tags = HydrusTags.CleanTags( HydrusText.DeserialiseNewlinedTexts( self._example_tags.toPlainText() ) )
        
        return TagSummaryGenerator( background_colour, text_colour, namespace_info, separator, example_tags, show )
        
    

class TagSummaryGeneratorButton( ClientGUICommon.BetterButton ):
    
    def __init__( self, parent: QW.QWidget, tag_summary_generator: TagSummaryGenerator ):
        
        label = tag_summary_generator.GenerateExampleSummary()
        
        super().__init__( parent, label, self._Edit )
        
        self._tag_summary_generator = tag_summary_generator
        
    
    def _Edit( self ):
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit tag summary' ) as dlg:
            
            panel = EditTagSummaryGeneratorPanel( dlg, self._tag_summary_generator )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                self._tag_summary_generator = panel.GetValue()
                
                self.setText( self._tag_summary_generator.GenerateExampleSummary() )
                
            
        
    
    def GetValue( self ) -> TagSummaryGenerator:
        
        return self._tag_summary_generator
        
    
