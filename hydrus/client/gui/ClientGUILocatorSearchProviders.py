import typing

from hydrus.client.gui.QLocator import QAbstractLocatorSearchProvider, QCalculatorSearchProvider, QLocatorSearchResult

from html import escape

from qtpy import QtWidgets as QW

from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientConstants as CC
from hydrus.client.gui.pages import ClientGUIMediaResultsPanelLoading
from hydrus.core import HydrusNumbers

def GetSearchProvider( provider: int ) -> QAbstractLocatorSearchProvider | None:
    
    if provider == CC.COMMAND_PALETTE_PROVIDER_CALCULATOR:
        
        return CalculatorSearchProvider()
        
    if provider == CC.COMMAND_PALETTE_PROVIDER_MAIN_MENU:
        
        return MainMenuSearchProvider()
        
    if provider == CC.COMMAND_PALETTE_PROVIDER_MEDIA_MENU:
        
        return MediaMenuSearchProvider()
        
    if provider == CC.COMMAND_PALETTE_PROVIDER_PAGES:
        
        return PagesSearchProvider()
        
    if provider == CC.COMMAND_PALETTE_PROVIDER_PAGES_HISTORY:
        
        return PagesHistorySearchProvider()
        
    if provider == CC.COMMAND_PALETTE_PROVIDER_FAVOURITE_SEARCH:
        
        return FavSearchesSearchProvider()
        
    
    return None
    

def highlight_result_text( result_text: str, query_text: str, pass_through = False ):
    
    result_text = escape( result_text )
    
    original_result_text = result_text
    
    if query_text:
        
        query_text = escape( query_text )
        
        if query_text not in result_text:
            
            query_text = query_text.casefold()
            
        
        if query_text not in result_text:
            
            if pass_through: #no bold
                
                return escape( original_result_text )
                
            
            result_text = result_text.casefold() # last ditch attempt
            
        
        if query_text in result_text:
            
            return result_text.replace( query_text, '<b>' + query_text + '</b>' )
            
        
    
    return '<b>' + escape( original_result_text ) + '</b>'
    

# Subclass for customizing icon paths
class CalculatorSearchProvider( QCalculatorSearchProvider ):
    
    def __init__( self, parent = None ):
        
        super().__init__( parent )
        
        
    def titleIconPath( self ):
        
        return str()
        
    
    def selectedIconPath( self ):
        
        return str()
        
    
    def iconPath( self ):
        
        return str()
        
    

class HydrusSearchProvider( QAbstractLocatorSearchProvider ):
    
    def _UserHasTypedEnoughToSearch( self, query: str ) -> bool:
        
        query = query.strip()
        
        # if user has typed something, we are now in search mode and want to test against this
        if 0 < len( query ) < CG.client_controller.new_options.GetInteger( 'command_palette_num_chars_for_results_threshold' ):
            
            return False
            
        
        return True
        
    

class FavSearchesSearchProvider( HydrusSearchProvider ):
    
    def __init__( self, parent = None ):
        
        super().__init__( parent )
        
        self.result_id_counter = 0
        self.result_ids_to_fav_searches = {}
        
    
    def title( self ):
        
        return "Favourite Searches"
        
    
    def suggestedReservedItemCount( self ):
        
        return 32
        
    
    def resultSelected( self, resultID: int ):
        
        fav_search = self.result_ids_to_fav_searches.get( resultID, None )
        
        if fav_search:
            
            ( folder, name, fsc, sync, sort, collect ) = fav_search
            
            if CG.client_controller.new_options.GetBoolean( 'command_palette_fav_searches_open_new_page' ):
                
                CG.client_controller.gui.NewPageQueryFileSearchContext( 
                    fsc,
                    initial_sort = sort,
                    initial_collect = collect,
                    page_name = name,
                    do_sort = True
                )
                
            
            current_media_page = CG.client_controller.gui.GetNotebookCurrentPage()
            
            if current_media_page is not None:
                
                current_media_page.ActivateFavouriteSearch( ( folder, name ) )
                
                self.result_ids_to_fav_searches = {}
                
            
        
    
    def processQuery( self, query: str, context, jobID: int ):
        
        query_casefold = query.casefold()
        
        self.result_ids_to_fav_searches = {}
        
        if not CG.client_controller.gui or not CG.client_controller.gui.GetTopLevelNotebook():
            
            return
            
        
        if query == "" and not CG.client_controller.new_options.GetBoolean( 'command_palette_initially_show_favourite_searches' ):
            
            return
            
        
        if not self._UserHasTypedEnoughToSearch( query_casefold ):
            
            return
            
        
        fav_searches = CG.client_controller.favourite_search_manager.GetFavouriteSearchRows()
        
        result = []
        
        for ( folder, name, file_search_context, synchronised, media_sort, media_collect ) in fav_searches:
            
            looks_good_a = folder is not None and query_casefold in folder.casefold()
            looks_good_b = query_casefold in name.casefold()
            
            if looks_good_a or looks_good_b:
                
                primary_text = highlight_result_text( name, query, pass_through = True )
                
                if folder is not None:
                    
                    secondary_text = highlight_result_text( folder, query, pass_through = True ) + ' - <i>favourite search</i>'
                    
                else:
                    
                    secondary_text = ''
                    
                
                icon_filename = 'search.png'
                
                result.append( QLocatorSearchResult( self.result_id_counter, icon_filename, icon_filename, True, [ primary_text, secondary_text ] ) )
                
                self.result_ids_to_fav_searches[ self.result_id_counter ] = ( folder, name, file_search_context, synchronised, media_sort, media_collect )
                
                self.result_id_counter += 1
                
            
        
        if result:
            
            if CG.client_controller.new_options.GetNoneableInteger( 'command_palette_limit_favourite_searches_results' ) is not None:
                
                result = result[ : CG.client_controller.new_options.GetNoneableInteger( 'command_palette_limit_favourite_searches_results' ) ]
                
            
            self.resultsAvailable.emit( jobID, result )
            
        
    
    def stopJobs( self, jobs: list ):
        
        self.result_ids_to_pages = {}
        
    
    def hideTitle( self ):
        
        return False
        
        
    def titleIconPath( self ):
        
        return str()
        
    

class PagesSearchProvider( HydrusSearchProvider ):
    
    def __init__( self, parent = None ):
        
        super().__init__( parent )
        
        from hydrus.client.gui.pages import ClientGUIPages
        
        self.result_id_counter = 0
        self.result_ids_to_pages: dict[ int, ClientGUIPages.Page | ClientGUIPages.PagesNotebook ] = {}
        
    
    def title( self ):
        
        return "Pages"
        
    
    # How many preallocated result widgets should be created (so that we don't have to recreate the entire result list on each search)
    # Should be larger than the average expected result count
    def suggestedReservedItemCount( self ):
        
        return 512
        
    
    # Called when the user activates a result
    def resultSelected( self, resultID: int ):
        
        page = self.result_ids_to_pages.get( resultID, None )
        
        if page is not None:
            
            page_key = page.GetPageKey()
            
            CG.client_controller.gui.ShowPage( page_key )
            
            self.result_ids_to_pages = {}
            
        
    # Should generate a list of QLocatorSearchResults
    def processQuery( self, query: str, context, jobID: int ):
        
        query_casefold = query.casefold()
        
        self.result_ids_to_pages = {}
        
        if not CG.client_controller.gui or not CG.client_controller.gui.GetTopLevelNotebook():
            
            return
            
        
        if query == "" and not CG.client_controller.new_options.GetBoolean( 'command_palette_initially_show_all_pages' ):
            
            return
            
        
        if not self._UserHasTypedEnoughToSearch( query_casefold ):
            
            return
            
        
        tab_widget = CG.client_controller.gui.GetTopLevelNotebook()
        
        # helper function to traverse tab tree and generate entries
        def get_child_tabs( tab_widget: QW.QTabWidget, parent_name: str ) -> list:
            
            result = []
            
            from hydrus.client.gui.pages import ClientGUIPages
            
            for i in range( tab_widget.count() ):
                
                widget = tab_widget.widget(i)
                
                is_page_of_pages = isinstance( widget, QW.QTabWidget )
                
                if is_page_of_pages:
                    
                    widget = typing.cast( ClientGUIPages.PagesNotebook, widget )
                    
                else:
                    
                    widget = typing.cast( ClientGUIPages.Page, widget )
                    
                
                if not is_page_of_pages or CG.client_controller.new_options.GetBoolean( 'command_palette_show_page_of_pages' ):
                    
                    selectable_media_page = widget
                    
                    page_name = selectable_media_page.GetNameForMenu( elide = False ) # I tried having the raw name, no '- 1 files', but it is better to be able to type what you see
                    
                    if query_casefold in page_name.casefold():
                        
                        primary_text = highlight_result_text( page_name, query )
                        secondary_text = 'top level page' if not parent_name else  "child of '" + escape( parent_name ) + "'"
                        
                        if is_page_of_pages:
                            
                            icon_filename = 'page_of_pages.png'
                            
                        else:
                            
                            icon_filename = 'thumbnails.png'
                            
                        
                        result.append( QLocatorSearchResult( self.result_id_counter, icon_filename, icon_filename, True, [ primary_text, secondary_text ] ) )
                        
                        self.result_ids_to_pages[ self.result_id_counter ] = selectable_media_page
                        
                        self.result_id_counter += 1
                        
                    
                
                if is_page_of_pages:
                    
                    result.extend( get_child_tabs( widget, widget.GetName() ) )
                    
                
            
            if CG.client_controller.new_options.GetNoneableInteger( 'command_palette_limit_page_results' ) is not None:
                
                result = result[ : CG.client_controller.new_options.GetNoneableInteger( 'command_palette_limit_page_results' ) ]
                
            
            return result
            
        
        tab_data = get_child_tabs( tab_widget, '' )
        
        if tab_data:
            
            self.resultsAvailable.emit( jobID, tab_data )
            
        

    # When this is called, it means that the Locator/LocatorWidget is done with these jobs and no results will be activated either
    # So if any still-in-progress search can be stopped and any resources associated with these jobs can be freed
    def stopJobs( self, jobs: list ):
        
        self.result_ids_to_pages = {}
        
        
    # Should the title item be visible in the result list
    def hideTitle( self ):
        
        return False
        
        
    def titleIconPath( self ):
        
        return str() #TODO fill this in
        
    
class PagesHistorySearchProvider( HydrusSearchProvider ):
    
    def __init__( self, parent = None ):
        
        super().__init__( parent )
        
        self.result_id_counter = 0
        self.result_ids_to_page_keys = {}
        
    
    def title( self ):
        
        return "Recent Tab History"
        
    
    # How many preallocated result widgets should be created (so that we don't have to recreate the entire result list on each search)
    # Should be larger than the average expected result count
    def suggestedReservedItemCount( self ):
        
        return 32
        
    
    def resultSelected( self, resultID: int ):
        
        page_key = self.result_ids_to_page_keys.get( resultID, None )
        
        if page_key:
            
            CG.client_controller.gui.ShowPage( page_key )
            
            self.result_ids_to_page_keys = {}
            
        
    # Should generate a list of QLocatorSearchResults
    def processQuery( self, query: str, context, jobID: int ):
        
        query_casefold = query.casefold()
        
        self.result_ids_to_page_keys = {}
        self.result_id_counter = 0
        
        if not CG.client_controller.gui or not CG.client_controller.gui.GetPagesHistory():
            
            return
            
        
        if query == "" and not CG.client_controller.new_options.GetBoolean( 'command_palette_initially_show_history' ):
            
            return
            
        
        if not self._UserHasTypedEnoughToSearch( query_casefold ):
            
            return
            
        
        history_data = CG.client_controller.gui.GetPagesHistory()
        
        def get_history_tabs( history_data: list ):
            
            result = []
            
            for i in range( len( history_data ) - 1, -1, -1 ):
                
                page_key, page_name = history_data[ i ]
                
                if query_casefold in page_name.casefold():
                    
                    primary_text = highlight_result_text( page_name, query )
                    secondary_text =  HydrusNumbers.IntToPrettyOrdinalString( self.result_id_counter + 1 ) + ' result in history'
                    
                    icon_filename = 'thumbnails.png'
                    
                    result.append( QLocatorSearchResult( self.result_id_counter, icon_filename, icon_filename, True, [ primary_text, secondary_text ] ) )
                    
                    self.result_ids_to_page_keys[ self.result_id_counter ] = page_key
                    
                    self.result_id_counter += 1
                    
                
            
            if CG.client_controller.new_options.GetNoneableInteger( 'command_palette_limit_history_results' ) is not None:
                
                result = result[ : CG.client_controller.new_options.GetNoneableInteger( 'command_palette_limit_history_results' ) ]
                
            
            return result
            
        
        tab_data = get_history_tabs( history_data )
        
        if tab_data:
            
            self.resultsAvailable.emit( jobID, tab_data )
            
        
    
    def stopJobs( self, jobs: list ):
        
        self.result_ids_to_page_keys = {}
        
        
    # Should the title item be visible in the result list
    def hideTitle( self ):
        
        return False
        
        
    def titleIconPath( self ):
        
        return str() #TODO fill this in
        
    

class HydrusSearchProviderCrazyLaggy( HydrusSearchProvider ):
    
    # why is a search result with like 120 items so slow? ~it is a mystery~
    
    def _UserHasTypedEnoughToSearch( self, query: str ) -> bool:
        
        if not super()._UserHasTypedEnoughToSearch( query ):
            
            return False
            
        
        if len( query ) < 3:
            
            return False
            
        
        return True
        
    

class MainMenuSearchProvider( HydrusSearchProviderCrazyLaggy ):
    
    def __init__( self, parent = None ):
        
        super().__init__( parent )
        
        self.result_id_counter = 0
        self.result_ids_to_actions: dict[ int, QW.QAction ] = {}
        

    def title( self ):
        
        return "Main Menu"
        

    def suggestedReservedItemCount( self ):
        
        return 128


    def resultSelected( self, resultID: int ):
        
        action = self.result_ids_to_actions.get( resultID, None )

        if action is not None:
            
            action.trigger()
            
            self.result_ids_to_actions = {}
            
        

    def processQuery( self, query: str, context, jobID: int ):
        
        query_casefold = query.casefold()
        
        self.result_ids_to_pages = {}
        
        if not CG.client_controller.gui or not CG.client_controller.gui.GetPagesHistory():
            
            return
            
        
        if not CG.client_controller.new_options.GetBoolean( 'command_palette_show_main_menu' ):
            
            return
            
        
        if not self._UserHasTypedEnoughToSearch( query_casefold ):
            
            return
            
        
        menubar = CG.client_controller.gui._menubar
        
        # helper function to traverse menu and generate entries
        # TODO: need to filter out menu items not suitable for display in locator
        # (probably best to mark them when they are created and just check a property here)
        # TODO: need special icon or secondary text for toggle-able items to see toggle state
        def get_menu_items( menu: QW.QWidget, parent_name: str ) -> list:
            
            result = []
            
            for action in menu.actions():
                
                actionText = action.text().replace( "&", "" )
                
                if action.menu():
                    
                    new_parent_name = parent_name + " | " + actionText if parent_name else actionText
                    
                    result.extend( get_menu_items( action.menu(), new_parent_name ) )
                    
                else:
                    
                    if query_casefold not in action.text().casefold() and query_casefold not in actionText.casefold():
                        
                        continue
                        
                    
                    primary_text = highlight_result_text( actionText, query )
                    secondary_text = escape( parent_name )
                    
                    normal_png = 'lightning.png'
                    toggled = False
                    toggled_png = 'lightning.png'
                    
                    if action.isCheckable():
                        
                        toggled = action.isChecked()
                        
                        normal_png = 'lightning_unchecked.png'
                        toggled_png = 'lightning_checked.png'
                        
                    
                    result.append( QLocatorSearchResult( self.result_id_counter, normal_png, normal_png, True, [ primary_text, secondary_text ], toggled, toggled_png, toggled_png ) )
                    
                    self.result_ids_to_actions[ self.result_id_counter ] = action
                    
                    self.result_id_counter += 1
                    
                

            return result
            
        
        menu_data = get_menu_items( menubar, '' )
        
        if menu_data:
            
            self.resultsAvailable.emit( jobID, menu_data )
            
        


    def stopJobs( self, jobs ):
        
        self.result_ids_to_actions = {}
        
    
    def hideTitle( self ):
        
        return False
        
    
    def titleIconPath( self ):
        
        return str() #TODO fill this in
        
    

class MediaMenuSearchProvider( HydrusSearchProviderCrazyLaggy ):
    
    def __init__( self, parent = None ):
        
        super().__init__( parent )
        
        self.result_id_counter = 0
        self.result_ids_to_actions: dict[ int, QW.QAction ] = {}
        self.menu = None
        

    def title( self ):
        
        return "Media"
        

    def suggestedReservedItemCount( self ):
        
        return 64
        

    def resultSelected( self, resultID: int ):
        
        action = self.result_ids_to_actions.get( resultID, None )

        if action is not None:
            
            action.trigger()
            
            self.result_ids_to_actions = {}
            self.menu = None
            
        

    def processQuery( self, query: str, context, jobID: int ):
        
        query_casefold = query.casefold()
        
        self.result_ids_to_pages = {}
        self.menu = None
        
        if not CG.client_controller.gui or not CG.client_controller.gui.GetPagesHistory():
            
            return
            
        
        if not CG.client_controller.new_options.GetBoolean( 'command_palette_show_media_menu' ):
            
            return
            
        
        if not self._UserHasTypedEnoughToSearch( query_casefold ):
            
            return
            
        
        media_page = CG.client_controller.gui.GetNotebookCurrentPage()
        
        if not media_page or not media_page.GetMediaResultsPanel():
            
            return
            
        
        media_panel = media_page.GetMediaResultsPanel()
        
        if media_panel is None or isinstance( media_panel, ClientGUIMediaResultsPanelLoading.MediaResultsPanelLoading ):
            
            return 
            
        
        self.menu = media_panel.ShowMenu( True )
        
        # helper function to traverse menu and generate entries
        # TODO: need to filter out menu items not suitable for display in locator
        # (probably best to mark them when they are created and just check a property here)
        # TODO: need special icon or secondary text for toggle-able items to see toggle state
        def get_menu_items( menu: QW.QWidget, parent_name: str ) -> list:
            
            result = []
            
            for action in menu.actions():
                
                actionText = action.text().replace( "&", "" )
                
                if action.menu():
                
                    new_parent_name = parent_name + " | " + actionText if parent_name else actionText

                    result.extend( get_menu_items( action.menu(), new_parent_name ) )
                    
                else:
                    
                    if query_casefold not in action.text().casefold() and query_casefold not in actionText.casefold():
                        
                        continue
                    
                    primary_text = highlight_result_text( actionText, query )
                    secondary_text = escape( parent_name )
                    
                    result.append( QLocatorSearchResult( self.result_id_counter, 'images.svg', 'images.svg', True, [ primary_text, secondary_text ] ) )
                    
                    self.result_ids_to_actions[ self.result_id_counter ] = action
                    
                    self.result_id_counter += 1

            return result
        
        menu_data = get_menu_items( self.menu, '' )
        
        if menu_data:
        
            self.resultsAvailable.emit( jobID, menu_data )


    def stopJobs( self, jobs ):

        self.result_ids_to_actions = {}
        self.menu = {}
        
        
    def hideTitle( self ):
        
        return False
        
        
    def titleIconPath( self ):
        
        return str() #TODO fill this in
        
# TODO: provider for page tab right click menu actions?
