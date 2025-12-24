from hydrus.core import HydrusNumbers
from hydrus.core import HydrusTags
from hydrus.core import HydrusText

from hydrus.client.metadata import ClientTags
from hydrus.client.search import ClientSearchPredicate

class ListBoxItem( object ):
    
    def __eq__( self, other ):
        
        if isinstance( other, ListBoxItem ):
            
            return self.__hash__() == other.__hash__()
            
        
        return NotImplemented
        
    
    def __hash__( self ):
        
        raise NotImplementedError()
        
    
    def __lt__( self, other ):
        
        if isinstance( other, ListBoxItem ):
            
            return self.GetCopyableTexts()[0] < other.GetCopyableTexts()[0]
            
        
        return NotImplemented
        
    
    def CanFadeColours( self ):
        
        return False
        
    
    def GetCopyableTexts( self, with_counts: bool = False, include_parents = False, collapse_ors = False ) -> list[ str ]:
        
        raise NotImplementedError()
        
    
    def GetSearchPredicates( self ) -> list[ ClientSearchPredicate.Predicate ]:
        
        raise NotImplementedError()
        
    
    def GetRowsOfPresentationTextsWithNamespaces( self, render_for_user: bool, sibling_decoration_allowed: bool, sibling_connector_string: str, sibling_connector_namespace: str | None, parent_decoration_allowed: bool, show_parent_rows: bool ) -> list[ list[ tuple[ str, str, str ] ] ]:
        
        raise NotImplementedError()
        
    
    def GetRowCount( self, show_parent_rows: bool ):
        
        return 1
        
    
    def GetTags( self ) -> set[ str ]:
        
        raise NotImplementedError()
        
    
    def UpdateFromOtherTerm( self, term: "ListBoxItem" ):
        
        pass
        
    
class ListBoxItemTagSlice( ListBoxItem ):
    
    def __init__( self, tag_slice: str ):
        
        super().__init__()
        
        self._tag_slice = tag_slice
        
    
    def __hash__( self ):
        
        return self._tag_slice.__hash__()
        
    
    def GetCopyableTexts( self, with_counts: bool = False, include_parents = False, collapse_ors = False ) -> list[ str ]:
        
        return [ self._tag_slice ]
        
    
    def GetSearchPredicates( self ) -> list[ ClientSearchPredicate.Predicate ]:
        
        return []
        
    
    def GetRowsOfPresentationTextsWithNamespaces( self, render_for_user: bool, sibling_decoration_allowed: bool, sibling_connector_string: str, sibling_connector_namespace: str | None, parent_decoration_allowed: bool, show_parent_rows: bool ) -> list[ list[ tuple[ str, str, str ] ] ]:
        
        presentation_text = HydrusTags.ConvertTagSliceToPrettyString( self._tag_slice )
        
        if self._tag_slice in ( '', ':' ):
            
            namespace = ''
            
        else:
            
            ( namespace, subtag ) = HydrusTags.SplitTag( self._tag_slice )
            
        
        return [ [ ( presentation_text, 'namespace', namespace ) ] ]
        
    
    def GetTags( self ) -> set[ str ]:
        
        return set()
        
    
    def GetTagSlice( self ):
        
        return self._tag_slice
        
    

class ListBoxItemNamespaceColour( ListBoxItem ):
    
    def __init__( self, namespace: str, colour: tuple[ int, int, int ] ):
        
        super().__init__()
        
        self._namespace = namespace
        self._colour = colour
        
    
    def __hash__( self ):
        
        return self._namespace.__hash__()
        
    
    def GetCopyableTexts( self, with_counts: bool = False, include_parents = False, collapse_ors = False ) -> list[ str ]:
        
        if self._namespace is None:
            
            return [ HydrusTags.ConvertTagSliceToPrettyString( ':' ) ]
            
        elif self._namespace == '':
            
            return [ HydrusTags.ConvertTagSliceToPrettyString( '' ) ]
            
        else:
            
            return [ HydrusTags.ConvertTagSliceToPrettyString( '{}:'.format( self._namespace ) ) ]
            
        
    
    def GetNamespace( self ):
        
        return self._namespace
        
    
    def GetNamespaceAndColour( self ):
        
        return ( self._namespace, self._colour )
        
    
    def GetSearchPredicates( self ) -> list[ ClientSearchPredicate.Predicate ]:
        
        return []
        
    
    def GetRowsOfPresentationTextsWithNamespaces( self, render_for_user: bool, sibling_decoration_allowed: bool, sibling_connector_string: str, sibling_connector_namespace: str | None, parent_decoration_allowed: bool, show_parent_rows: bool ) -> list[ list[ tuple[ str, str, str ] ] ]:
        
        return [ [ ( self.GetCopyableTexts()[0], 'namespace', self._namespace ) ] ]
        
    
    def GetTags( self ) -> set[ str ]:
        
        return set()
        
    
class ListBoxItemTextTag( ListBoxItem ):
    
    def __init__( self, tag: str ):
        
        super().__init__()
        
        self._tag = tag
        self._ideal_tag = None
        self._parent_tags = None
        
    
    def __hash__( self ):
        
        return self._tag.__hash__()
        
    
    def __lt__( self, other ):
        
        if isinstance( other, ListBoxItemTextTag ):
            
            return HydrusText.HumanTextSortKey( self.GetCopyableTexts()[0] ) < HydrusText.HumanTextSortKey( other.GetCopyableTexts()[0] )
            
        
        return NotImplemented
        
    
    def _AppendIdealTagTextWithNamespace( self, texts_with_namespaces, sibling_connector_string: str, sibling_connector_namespace: str | None, render_for_user ):
        
        ( namespace, subtag ) = HydrusTags.SplitTag( self._ideal_tag )
        
        if sibling_connector_namespace is None:
            
            sibling_connector_namespace = namespace
            
        
        texts_with_namespaces.append( ( sibling_connector_string, 'sibling_connector', sibling_connector_namespace ) )
        texts_with_namespaces.append( ( ClientTags.RenderTag( self._ideal_tag, render_for_user ), 'namespace', namespace ) )
        
    
    def _AppendParentsTextWithNamespaces( self, rows_of_texts_with_namespaces, render_for_user ):
        
        indent = '    '
        
        for parent in self._parent_tags:
            
            ( namespace, subtag ) = HydrusTags.SplitTag( parent )
            
            tag_text = ClientTags.RenderTag( parent, render_for_user )
            
            texts_with_namespaces = [ ( indent + tag_text, 'namespace', namespace ) ]
            
            rows_of_texts_with_namespaces.append( texts_with_namespaces )
            
        
    
    def _AppendParentSuffixTagTextWithNamespace( self, texts_with_namespaces ):
        
        parents_text = ' ({} parents)'.format( HydrusNumbers.ToHumanInt( len( self._parent_tags ) ) )
        
        texts_with_namespaces.append( ( parents_text, 'namespace', '' ) )
        
    
    def GetBestTag( self ) -> str:
        
        if self._ideal_tag is None:
            
            return self._tag
            
        
        return self._ideal_tag
        
    
    def GetCopyableTexts( self, with_counts: bool = False, include_parents = False, collapse_ors = False ) -> list[ str ]:
        
        rows = [ self._tag ]
        
        if include_parents and self._parent_tags is not None:
            
            rows.extend( self._parent_tags )
            
        
        return rows
        
    
    def GetSearchPredicates( self ) -> list[ ClientSearchPredicate.Predicate ]:
        
        return [ ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, value = self._tag ) ]
        
    
    def GetRowCount( self, show_parent_rows: bool ):
        
        if self._parent_tags is None or not show_parent_rows:
            
            return 1
            
        else:
            
            return 1 + len( self._parent_tags )
            
        
    
    def GetRowsOfPresentationTextsWithNamespaces( self, render_for_user: bool, sibling_decoration_allowed: bool, sibling_connector_string: str, sibling_connector_namespace: str | None, parent_decoration_allowed: bool, show_parent_rows: bool ) -> list[ list[ tuple[ str, str, str ] ] ]:
        
        # this should be with counts or whatever, but we need to think about this more lad
        
        ( namespace, subtag ) = HydrusTags.SplitTag( self._tag )
        
        tag_text = ClientTags.RenderTag( self._tag, render_for_user )
        
        first_row_of_texts_with_namespaces = [ ( tag_text, 'namespace', namespace ) ]
        
        if sibling_decoration_allowed and self._ideal_tag is not None:
            
            self._AppendIdealTagTextWithNamespace( first_row_of_texts_with_namespaces, sibling_connector_string, sibling_connector_namespace, render_for_user )
            
        
        rows_of_texts_with_namespaces = [ first_row_of_texts_with_namespaces ]
        
        if self._parent_tags is not None:
            
            if show_parent_rows:
                
                self._AppendParentsTextWithNamespaces( rows_of_texts_with_namespaces, render_for_user )
                
            elif parent_decoration_allowed:
                
                self._AppendParentSuffixTagTextWithNamespace( first_row_of_texts_with_namespaces )
                
            
        
        return rows_of_texts_with_namespaces
        
    
    def GetSimpleSortText( self ) -> set[ str ]:
        
        pass
        
    
    def GetTag( self ) -> str:
        
        return self._tag
        
    
    def GetTags( self ) -> set[ str ]:
        
        return { self._tag }
        
    
    def SetIdealTag( self, ideal_tag ):
        
        self._ideal_tag = ideal_tag
        
    
    def SetParents( self, parents ):
        
        self._parent_tags = parents
        
    

class ListBoxItemTextTagWithCounts( ListBoxItemTextTag ):
    
    def __init__( self, tag: str, current_count: int, deleted_count: int, pending_count: int, petitioned_count: int, include_actual_counts: bool ):
        
        # some have deleted and petitioned as well, so think about this
        
        super().__init__( tag )
        
        self._current_count = current_count
        self._deleted_count = deleted_count
        self._pending_count = pending_count
        self._petitioned_count = petitioned_count
        self._include_actual_counts = include_actual_counts
        
    
    def __hash__( self ):
        
        return self._tag.__hash__()
        
    
    def __lt__( self, other ):
        
        if isinstance( other, ListBoxItemTextTagWithCounts ):
            
            return HydrusText.HumanTextSortKey( self.GetCopyableTexts( with_counts = False )[0] ) < HydrusText.HumanTextSortKey( other.GetCopyableTexts( with_counts = False )[0] )
            
        
        return NotImplemented
        
    
    def GetCopyableTexts( self, with_counts: bool = False, include_parents = False, collapse_ors = False ) -> list[ str ]:
        
        if with_counts:
            
            sibling_connector_string = ''
            sibling_connector_namespace = ''
            
            rows = []
            
            for texts_with_namespaces in self.GetRowsOfPresentationTextsWithNamespaces( False, False, sibling_connector_string, sibling_connector_namespace, False, False ):
                
                rows.append( ''.join( ( text for ( text, colour_type, data ) in texts_with_namespaces ) ) )
                
            
            return rows
            
        else:
            
            rows = [ self._tag ]
            
            if include_parents and self._parent_tags is not None:
                
                rows.extend( self._parent_tags )
                
            
            return rows
            
        
    
    def GetSearchPredicates( self ) -> list[ ClientSearchPredicate.Predicate ]:
        
        # with counts? or just merge this into texttag???
        
        return [ ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, value = self._tag ) ]
        
    
    def GetRowsOfPresentationTextsWithNamespaces( self, render_for_user: bool, sibling_decoration_allowed: bool, sibling_connector_string: str, sibling_connector_namespace: str | None, parent_decoration_allowed: bool, show_parent_rows: bool ) -> list[ list[ tuple[ str, str, str ] ] ]:
        
        # this should be with counts or whatever, but we need to think about this more lad
        
        ( namespace, subtag ) = HydrusTags.SplitTag( self._tag )
        
        tag_text = ClientTags.RenderTag( self._tag, render_for_user )
        
        if self._include_actual_counts:
            
            if self._current_count > 0:
                
                tag_text += ' ({})'.format( HydrusNumbers.ToHumanInt( self._current_count ) )
                
            
            if self._pending_count > 0:
                
                tag_text += ' (+{})'.format( HydrusNumbers.ToHumanInt( self._pending_count ) )
                
            
            if self._petitioned_count > 0:
                
                tag_text += ' (-{})'.format( HydrusNumbers.ToHumanInt( self._petitioned_count ) )
                
            
            if self._deleted_count > 0:
                
                tag_text += ' (X{})'.format( HydrusNumbers.ToHumanInt( self._deleted_count ) )
                
            
        else:
            
            if self._pending_count > 0:
                
                tag_text += ' (+)'
                
            
            if self._petitioned_count > 0:
                
                tag_text += ' (-)'
                
            
            if self._deleted_count > 0:
                
                tag_text += ' (X)'
                
            
        
        first_row_of_texts_with_namespaces = [ ( tag_text, 'namespace', namespace ) ]
        
        if sibling_decoration_allowed and self._ideal_tag is not None:
            
            self._AppendIdealTagTextWithNamespace( first_row_of_texts_with_namespaces, sibling_connector_string, sibling_connector_namespace, render_for_user )
            
        
        rows_of_texts_with_namespaces = [ first_row_of_texts_with_namespaces ]
        
        if self._parent_tags is not None:
            
            if show_parent_rows:
                
                self._AppendParentsTextWithNamespaces( rows_of_texts_with_namespaces, render_for_user )
                
            elif parent_decoration_allowed:
                
                self._AppendParentSuffixTagTextWithNamespace( first_row_of_texts_with_namespaces )
                
            
        
        return rows_of_texts_with_namespaces
        
    
    def UpdateFromOtherTerm( self, term: "ListBoxItemTextTagWithCounts" ):
        
        self._current_count = term._current_count
        self._deleted_count = term._deleted_count
        self._pending_count = term._pending_count
        self._petitioned_count = term._petitioned_count
        self._include_actual_counts = term._include_actual_counts
        
    
class ListBoxItemPredicate( ListBoxItem ):
    
    def __init__( self, predicate: ClientSearchPredicate.Predicate ):
        
        super().__init__()
        
        self._predicate = predicate
        self._i_am_an_or_under_construction = False
        
    
    def __hash__( self ):
        
        return self._predicate.__hash__()
        
    
    def __lt__( self, other ):
        
        if isinstance( other, ListBoxItem ):
            
            return HydrusText.HumanTextSortKey( self.GetCopyableTexts()[0] ) < HydrusText.HumanTextSortKey( other.GetCopyableTexts()[0] )
            
        
        return NotImplemented
        
    
    def CanFadeColours( self ):
        
        return not self._predicate.IsORPredicate()
        
    
    def GetCopyableTexts( self, with_counts: bool = False, include_parents = False, collapse_ors = False ) -> list[ str ]:
        
        if self._predicate.IsORPredicate():
            
            if collapse_ors:
                
                texts = [ self._predicate.ToString( for_parsable_export = True ) ]
                
            else:
                
                texts = [ sub_pred.ToString() for sub_pred in self._predicate.GetValue() ]
                
            
        elif self._predicate.GetType() == ClientSearchPredicate.PREDICATE_TYPE_NAMESPACE:
            
            namespace = self._predicate.GetValue()
            
            # this is useful for workflow
            texts = [ '{}:*'.format( namespace ) ]
            
        elif self._predicate.GetType() == ClientSearchPredicate.PREDICATE_TYPE_PARENT:
            
            texts = [ HydrusTags.CleanTag( self._predicate.GetValue() ) ]
            
        elif self._predicate.GetType() == ClientSearchPredicate.PREDICATE_TYPE_WILDCARD:
            
            wildcard = self._predicate.GetValue()
            
            texts = [ wildcard ]
            
        else:
            
            texts = [ self._predicate.ToString( with_count = with_counts, for_parsable_export = True ) ]
            
            if include_parents and self._predicate.HasParentPredicates():
                
                texts.extend( [ parent.ToString( with_count = with_counts, for_parsable_export = True ) for parent in self._predicate.GetParentPredicates() ] )
                
            
        
        return texts
        
    
    def GetPredicate( self ) -> ClientSearchPredicate.Predicate:
        
        return self._predicate
        
    
    def GetRowCount( self, show_parent_rows: bool ):
        
        if self._predicate.IsORPredicate():
            
            return 1 + len( self._predicate.GetORPredicates() )
            
        elif show_parent_rows:
            
            return 1 + len( self._predicate.GetParentPredicates() )
            
        else:
            
            return 1
            
        
    
    def GetRowsOfPresentationTextsWithNamespaces( self, render_for_user: bool, sibling_decoration_allowed: bool, sibling_connector_string: str, sibling_connector_namespace: str | None, parent_decoration_allowed: bool, show_parent_rows: bool ) -> list[ list[ tuple[ str, str, str ] ] ]:
        
        rows_of_texts_and_namespaces = []
        
        first_row_of_texts_and_namespaces = self._predicate.GetTextsAndNamespaces( render_for_user, or_under_construction = self._i_am_an_or_under_construction )
        
        rows_of_texts_and_namespaces.append( first_row_of_texts_and_namespaces )
        
        if self._predicate.IsORPredicate():
            
            for sub_pred in self._predicate.GetORPredicates():
                
                rows_of_texts_and_namespaces.append( sub_pred.GetTextsAndNamespaces( render_for_user, prefix = '    ' ) )
                
            
        
        if sibling_decoration_allowed and self._predicate.HasIdealSibling():
            
            ideal_sibling = self._predicate.GetIdealSibling()
            
            ( ideal_namespace, ideal_subtag ) = HydrusTags.SplitTag( ideal_sibling )
            
            if sibling_connector_namespace is None:
                
                sibling_connector_namespace = ideal_namespace
                
            
            first_row_of_texts_and_namespaces.append( ( sibling_connector_string, 'sibling_connector', sibling_connector_namespace ) )
            first_row_of_texts_and_namespaces.append( ( ClientTags.RenderTag( ideal_sibling, render_for_user ), 'namespace', ideal_namespace ) )
            
        
        parent_preds = self._predicate.GetParentPredicates()
        
        if len( parent_preds ) > 0:
            
            if show_parent_rows:
                
                for parent_pred in self._predicate.GetParentPredicates():
                    
                    rows_of_texts_and_namespaces.append( parent_pred.GetTextsAndNamespaces( render_for_user ) )
                    
                
            elif parent_decoration_allowed:
                
                parents_text = ' ({} parents)'.format( HydrusNumbers.ToHumanInt( len( parent_preds ) ) )
                
                first_row_of_texts_and_namespaces.append( ( parents_text, 'namespace', '' ) )
                
            
        
        return rows_of_texts_and_namespaces
        
    
    def GetSearchPredicates( self ) -> list[ ClientSearchPredicate.Predicate ]:
        
        if self._predicate.GetType() in ( ClientSearchPredicate.PREDICATE_TYPE_LABEL, ClientSearchPredicate.PREDICATE_TYPE_PARENT ):
            
            return []
            
        else:
            
            return [ self._predicate ]
            
        
    
    def GetTags( self ) -> set[ str ]:
        
        if self._predicate.GetType() == ClientSearchPredicate.PREDICATE_TYPE_TAG:
            
            tag = self._predicate.GetValue()
            
        else:
            
            return set()
            
        
        return { tag }
        
    
    def SetORUnderConstruction( self, value: bool ):
        
        self._i_am_an_or_under_construction = value
        
    
