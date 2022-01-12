import collections
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTags

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientSearch
from hydrus.client.gui.search import ClientGUISearch
from hydrus.client.media import ClientMedia
from hydrus.client.metadata import ClientTags

class ListBoxItem( object ):
    
    def __init__( self ):
        
        pass
        
    
    def __eq__( self, other ):
        
        if isinstance( other, ListBoxItem ):
            
            return self.__hash__() == other.__hash__()
            
        
        return NotImplemented
        
    
    def __hash__( self ):
        
        raise NotImplementedError()
        
    
    def __lt__( self, other ):
        
        if isinstance( other, ListBoxItem ):
            
            return self.GetCopyableText() < other.GetCopyableText()
            
        
        return NotImplemented
        
    
    def GetCopyableText( self, with_counts: bool = False ) -> str:
        
        raise NotImplementedError()
        
    
    def GetSearchPredicates( self ) -> typing.List[ ClientSearch.Predicate ]:
        
        raise NotImplementedError()
        
    
    def GetRowsOfPresentationTextsWithNamespaces( self, render_for_user: bool, sibling_decoration_allowed: bool, child_rows_allowed: bool ) -> typing.List[ typing.List[ typing.Tuple[ str, str ] ] ]:
        
        raise NotImplementedError()
        
    
    def GetRowCount( self, child_rows_allowed: bool ):
        
        return 1
        
    
    def GetTags( self ) -> typing.Set[ str ]:
        
        raise NotImplementedError()
        
    
class ListBoxItemTagSlice( ListBoxItem ):
    
    def __init__( self, tag_slice: str ):
        
        ListBoxItem.__init__( self )
        
        self._tag_slice = tag_slice
        
    
    def __hash__( self ):
        
        return self._tag_slice.__hash__()
        
    
    def GetCopyableText( self, with_counts: bool = False ) -> str:
        
        return HydrusTags.ConvertTagSliceToString( self._tag_slice )
        
    
    def GetSearchPredicates( self ) -> typing.List[ ClientSearch.Predicate ]:
        
        return []
        
    
    def GetRowsOfPresentationTextsWithNamespaces( self, render_for_user: bool, sibling_decoration_allowed: bool, child_rows_allowed: bool ) -> typing.List[ typing.Tuple[ str, str ] ]:
        
        presentation_text = self.GetCopyableText()
        
        if self._tag_slice in ( '', ':' ):
            
            namespace = ''
            
        else:
            
            ( namespace, subtag ) = HydrusTags.SplitTag( self._tag_slice )
            
        
        return [ [ ( presentation_text, namespace ) ] ]
        
    
    def GetTags( self ) -> typing.Set[ str ]:
        
        return set()
        
    
    def GetTagSlice( self ):
        
        return self._tag_slice
        
    
class ListBoxItemNamespaceColour( ListBoxItem ):
    
    def __init__( self, namespace: str, colour: typing.Tuple[ int, int, int ] ):
        
        ListBoxItem.__init__( self )
        
        self._namespace = namespace
        self._colour = colour
        
    
    def __hash__( self ):
        
        return self._namespace.__hash__()
        
    
    def GetCopyableText( self, with_counts: bool = False ) -> str:
        
        if self._namespace is None:
            
            return HydrusTags.ConvertTagSliceToString( ':' )
            
        elif self._namespace == '':
            
            return HydrusTags.ConvertTagSliceToString( '' )
            
        else:
            
            return HydrusTags.ConvertTagSliceToString( '{}:'.format( self._namespace ) )
            
        
    
    def GetNamespace( self ):
        
        return self._namespace
        
    
    def GetNamespaceAndColour( self ):
        
        return ( self._namespace, self._colour )
        
    
    def GetSearchPredicates( self ) -> typing.List[ ClientSearch.Predicate ]:
        
        return []
        
    
    def GetRowsOfPresentationTextsWithNamespaces( self, render_for_user: bool, sibling_decoration_allowed: bool, child_rows_allowed: bool ) -> typing.List[ typing.List[ typing.Tuple[ str, str ] ] ]:
        
        return [ [ ( self.GetCopyableText(), self._namespace ) ] ]
        
    
    def GetTags( self ) -> typing.Set[ str ]:
        
        return set()
        
    
class ListBoxItemTextTag( ListBoxItem ):
    
    def __init__( self, tag: str ):
        
        ListBoxItem.__init__( self )
        
        self._tag = tag
        self._ideal_tag = None
        self._parent_tags = None
        
    
    def __hash__( self ):
        
        return self._tag.__hash__()
        
    
    def _AppendIdealTagTextWithNamespace( self, texts_with_namespaces, render_for_user ):
        
        ( namespace, subtag ) = HydrusTags.SplitTag( self._ideal_tag )
        
        ideal_text = ' (displays as {})'.format( ClientTags.RenderTag( self._ideal_tag, render_for_user ) )
        
        texts_with_namespaces.append( ( ideal_text, namespace ) )
        
    
    def _AppendParentsTextWithNamespaces( self, rows_of_texts_with_namespaces, render_for_user ):
        
        indent = '    '
        
        for parent in self._parent_tags:
            
            ( namespace, subtag ) = HydrusTags.SplitTag( parent )
            
            tag_text = ClientTags.RenderTag( parent, render_for_user )
            
            texts_with_namespaces = [ ( indent + tag_text, namespace ) ]
            
            rows_of_texts_with_namespaces.append( texts_with_namespaces )
            
        
    
    def _AppendParentSuffixTagTextWithNamespace( self, texts_with_namespaces ):
        
        parents_text = ' ({} parents)'.format( HydrusData.ToHumanInt( len( self._parent_tags ) ) )
        
        texts_with_namespaces.append( ( parents_text, '' ) )
        
    
    def GetBestTag( self ) -> str:
        
        if self._ideal_tag is None:
            
            return self._tag
            
        
        return self._ideal_tag
        
    
    def GetCopyableText( self, with_counts: bool = False ) -> str:
        
        return self._tag
        
    
    def GetSearchPredicates( self ) -> typing.List[ ClientSearch.Predicate ]:
        
        return [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, value = self._tag ) ]
        
    
    def GetRowCount( self, child_rows_allowed: bool ):
        
        if self._parent_tags is None or not child_rows_allowed:
            
            return 1
            
        else:
            
            return 1 + len( self._parent_tags )
            
        
    
    def GetRowsOfPresentationTextsWithNamespaces( self, render_for_user: bool, sibling_decoration_allowed: bool, child_rows_allowed: bool ) -> typing.List[ typing.List[ typing.Tuple[ str, str ] ] ]:
        
        # this should be with counts or whatever, but we need to think about this more lad
        
        ( namespace, subtag ) = HydrusTags.SplitTag( self._tag )
        
        tag_text = ClientTags.RenderTag( self._tag, render_for_user )
        
        first_row_of_texts_with_namespaces = [ ( tag_text, namespace ) ]
        
        if sibling_decoration_allowed and self._ideal_tag is not None:
            
            self._AppendIdealTagTextWithNamespace( first_row_of_texts_with_namespaces, render_for_user )
            
        
        rows_of_texts_with_namespaces = [ first_row_of_texts_with_namespaces ]
        
        if self._parent_tags is not None:
            
            if child_rows_allowed:
                
                self._AppendParentsTextWithNamespaces( rows_of_texts_with_namespaces, render_for_user )
                
            elif sibling_decoration_allowed:
                
                self._AppendParentSuffixTagTextWithNamespace( first_row_of_texts_with_namespaces )
                
            
        
        return rows_of_texts_with_namespaces
        
    
    def GetSimpleSortText( self ) -> typing.Set[ str ]:
        
        pass
        
    
    def GetTag( self ) -> str:
        
        return self._tag
        
    
    def GetTags( self ) -> typing.Set[ str ]:
        
        return { self._tag }
        
    
    def SetIdealTag( self, ideal_tag ):
        
        self._ideal_tag = ideal_tag
        
    
    def SetParents( self, parents ):
        
        self._parent_tags = parents
        
    
class ListBoxItemTextTagWithCounts( ListBoxItemTextTag ):
    
    def __init__( self, tag: str, current_count: int, deleted_count: int, pending_count: int, petitioned_count: int, include_actual_counts: bool ):
        
        # some have deleted and petitioned as well, so think about this
        
        ListBoxItemTextTag.__init__( self, tag )
        
        self._current_count = current_count
        self._deleted_count = deleted_count
        self._pending_count = pending_count
        self._petitioned_count = petitioned_count
        self._include_actual_counts = include_actual_counts
        
    
    def __hash__( self ):
        
        return self._tag.__hash__()
        
    
    def GetCopyableText( self, with_counts: bool = False ) -> str:
        
        if with_counts:
            
            return ''.join( ( text for ( text, namespace ) in self.GetRowsOfPresentationTextsWithNamespaces( False, False, False )[0] ) )
            
        else:
            
            return self._tag
            
        
    
    def GetSearchPredicates( self ) -> typing.List[ ClientSearch.Predicate ]:
        
        # with counts? or just merge this into texttag???
        
        return [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, value = self._tag ) ]
        
    
    def GetRowsOfPresentationTextsWithNamespaces( self, render_for_user: bool, sibling_decoration_allowed: bool, child_rows_allowed: bool ) -> typing.List[ typing.List[ typing.Tuple[ str, str ] ] ]:
        
        # this should be with counts or whatever, but we need to think about this more lad
        
        ( namespace, subtag ) = HydrusTags.SplitTag( self._tag )
        
        tag_text = ClientTags.RenderTag( self._tag, render_for_user )
        
        if self._include_actual_counts:
            
            if self._current_count > 0:
                
                tag_text += ' ({})'.format( HydrusData.ToHumanInt( self._current_count ) )
                
            
            if self._pending_count > 0:
                
                tag_text += ' (+{})'.format( HydrusData.ToHumanInt( self._pending_count ) )
                
            
            if self._petitioned_count > 0:
                
                tag_text += ' (-{})'.format( HydrusData.ToHumanInt( self._petitioned_count ) )
                
            
            if self._deleted_count > 0:
                
                tag_text += ' (X{})'.format( HydrusData.ToHumanInt( self._deleted_count ) )
                
            
        else:
            
            if self._pending_count > 0:
                
                tag_text += ' (+)'
                
            
            if self._petitioned_count > 0:
                
                tag_text += ' (-)'
                
            
            if self._deleted_count > 0:
                
                tag_text += ' (X)'
                
            
        
        first_row_of_texts_with_namespaces = [ ( tag_text, namespace ) ]
        
        if sibling_decoration_allowed and self._ideal_tag is not None:
            
            self._AppendIdealTagTextWithNamespace( first_row_of_texts_with_namespaces, render_for_user )
            
        
        rows_of_texts_with_namespaces = [ first_row_of_texts_with_namespaces ]
        
        if self._parent_tags is not None:
            
            if child_rows_allowed:
                
                self._AppendParentsTextWithNamespaces( rows_of_texts_with_namespaces, render_for_user )
                
            elif sibling_decoration_allowed:
                
                self._AppendParentSuffixTagTextWithNamespace( first_row_of_texts_with_namespaces )
                
            
        
        return rows_of_texts_with_namespaces
        
    
class ListBoxItemPredicate( ListBoxItem ):
    
    def __init__( self, predicate: ClientSearch.Predicate ):
        
        ListBoxItem.__init__( self )
        
        self._predicate = predicate
        self._i_am_an_or_under_construction = False
        
    
    def __hash__( self ):
        
        return self._predicate.__hash__()
        
    
    def GetCopyableText( self, with_counts: bool = False ) -> str:
        
        if self._predicate.GetType() == ClientSearch.PREDICATE_TYPE_NAMESPACE:
            
            namespace = self._predicate.GetValue()
            
            # this is useful for workflow
            text = '{}:*'.format( namespace )
            
        elif self._predicate.GetType() == ClientSearch.PREDICATE_TYPE_PARENT:
            
            text = HydrusTags.CleanTag( self._predicate.GetValue() )
            
        else:
            
            text = self._predicate.ToString( with_count = with_counts )
            
        
        return text
        
    
    def GetSearchPredicates( self ) -> typing.List[ ClientSearch.Predicate ]:
        
        if self._predicate.GetType() in ( ClientSearch.PREDICATE_TYPE_LABEL, ClientSearch.PREDICATE_TYPE_PARENT ):
            
            return []
            
        else:
            
            return [ self._predicate ]
            
        
    
    def GetRowCount( self, child_rows_allowed: bool ):
        
        if child_rows_allowed:
            
            return 1 + len( self._predicate.GetParentPredicates() )
            
        else:
            
            return 1
            
        
    
    def GetRowsOfPresentationTextsWithNamespaces( self, render_for_user: bool, sibling_decoration_allowed: bool, child_rows_allowed: bool ) -> typing.List[ typing.List[ typing.Tuple[ str, str ] ] ]:
        
        rows_of_texts_and_namespaces = []
        
        first_row_of_texts_and_namespaces = self._predicate.GetTextsAndNamespaces( render_for_user, or_under_construction = self._i_am_an_or_under_construction )
        
        if sibling_decoration_allowed and self._predicate.HasIdealSibling():
            
            ideal_sibling = self._predicate.GetIdealSibling()
            
            ( ideal_namespace, ideal_subtag ) = HydrusTags.SplitTag( ideal_sibling )
            
            ideal_text = ' (displays as {})'.format( ClientTags.RenderTag( ideal_sibling, render_for_user ) )
            
            first_row_of_texts_and_namespaces.append( ( ideal_text, ideal_namespace ) )
            
        
        rows_of_texts_and_namespaces.append( first_row_of_texts_and_namespaces )
        
        parent_preds = self._predicate.GetParentPredicates()
        
        if len( parent_preds ) > 0:
            
            if child_rows_allowed:
                
                for parent_pred in self._predicate.GetParentPredicates():
                    
                    rows_of_texts_and_namespaces.append( parent_pred.GetTextsAndNamespaces( render_for_user ) )
                    
                
            elif sibling_decoration_allowed:
                
                parents_text = ' ({} parents)'.format( HydrusData.ToHumanInt( len( parent_preds ) ) )
                
                first_row_of_texts_and_namespaces.append( ( parents_text, '' ) )
                
            
        
        return rows_of_texts_and_namespaces
        
    
    def GetTags( self ) -> typing.Set[ str ]:
        
        if self._predicate.GetType() == ClientSearch.PREDICATE_TYPE_TAG:
            
            tag = self._predicate.GetValue()
            
        else:
            
            return set()
            
        
        return { tag }
        
    
    def SetORUnderConstruction( self, value: bool ):
        
        self._i_am_an_or_under_construction = value
        
