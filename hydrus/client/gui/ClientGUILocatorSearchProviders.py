from hydrus.client.gui.QLocator import QAbstractLocatorSearchProvider, QCalculatorSearchProvider, QLocatorSearchResult
from hydrus.core import HydrusGlobals as HG
from qtpy import QtWidgets as QW
from html import escape


def highlight_result_text( result_text: str, query_text: str ):

    result_text = escape( result_text )
    
    if query_text:

        result_text = result_text.replace( escape( query_text ), '<b>' + escape( query_text ) + '</b>' )
    
    return result_text


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

        
class PagesSearchProvider( QAbstractLocatorSearchProvider ):
    
    def __init__( self, parent = None ):
        
        super().__init__( parent )
        
        self.result_id_counter = 0
        self.result_ids_to_pages = {}


    def title( self ):
        
        return "Pages"


    # How many preallocated result widgets should be created (so that we don't have to recreate the entire result list on each search)
    # Should be larger than the average expected result count
    def suggestedReservedItemCount( self ):
        
        return 32


    # Called when the user activates a result
    def resultSelected( self, resultID: int ):
        
        page = self.result_ids_to_pages.get( resultID, None )

        if page:

            HG.client_controller.gui._notebook.ShowPage( page )
            
            self.result_ids_to_pages = {}


    # Should generate a list of QLocatorSearchResults
    def processQuery( self, query: str, context, jobID: int ):
        
        self.result_ids_to_pages = {}
        
        if not HG.client_controller.gui or not HG.client_controller.gui._notebook:
            
            return
            
        
        tab_widget = HG.client_controller.gui._notebook
        
        # helper function to traverse tab tree and generate entries
        def get_child_tabs( tab_widget: QW.QTabWidget, parent_name: str ) -> list:
            
            result = []
            
            for i in range( tab_widget.count() ):
            
                widget = tab_widget.widget(i)
                
                if isinstance( widget, QW.QTabWidget ): # page of pages
            
                    result.extend( get_child_tabs( widget, widget.GetName() ) )
                    
                else:
                    
                    selectable_media_page = widget
                    
                    label = selectable_media_page.GetNameForMenu()
                    
                    if not query in label:
                        
                        continue
                        
                    
                    primary_text = highlight_result_text( label, query )
                    secondary_text = 'top level page' if not parent_name else  "child of '" + escape( parent_name ) + "'"
                    
                    result.append( QLocatorSearchResult( self.result_id_counter, 'thumbnails.png', 'thumbnails.png', True, [ primary_text, secondary_text ] ) )
                    
                    self.result_ids_to_pages[ self.result_id_counter ] = selectable_media_page
                    
                    self.result_id_counter += 1

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


class MainMenuSearchProvider( QAbstractLocatorSearchProvider ):
    
    def __init__( self, parent = None ):
        
        super().__init__( parent )
        
        self.result_id_counter = 0
        self.result_ids_to_actions = {}


    def title( self ):
        
        return "Main Menu"


    def suggestedReservedItemCount( self ):
        
        return 128


    def resultSelected( self, resultID: int ):
        
        action = self.result_ids_to_actions.get( resultID, None )

        if action:

            action.trigger()
            
            self.result_ids_to_actions = {}


    def processQuery( self, query: str, context, jobID: int ):
        
        if not HG.client_controller.new_options.GetBoolean( 'advanced_mode' ):
            
            return
            
        
        if len( query ) < 3:
            
            return
            
        self.result_ids_to_pages = {}
        
        if not HG.client_controller.gui or not HG.client_controller.gui._menubar:
            
            return
            
        menubar = HG.client_controller.gui._menubar
        
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
                    
                    if not query in action.text() and not query in actionText:
                        
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


class MediaMenuSearchProvider( QAbstractLocatorSearchProvider ):
    
    def __init__( self, parent = None ):
        
        super().__init__( parent )
        
        self.result_id_counter = 0
        self.result_ids_to_actions = {}
        self.menu = None


    def title( self ):
        
        return "Media"


    def suggestedReservedItemCount( self ):
        
        return 64


    def resultSelected( self, resultID: int ):
        
        action = self.result_ids_to_actions.get( resultID, None )

        if action:

            action.trigger()
            
            self.result_ids_to_actions = {}
            self.menu = None


    def processQuery( self, query: str, context, jobID: int ):
        
        if not HG.client_controller.new_options.GetBoolean( 'advanced_mode' ):
            
            return
            
        
        if len( query ) < 3:
            
            return
            
        self.result_ids_to_pages = {}
        self.menu = None
        
        if not HG.client_controller.gui or not HG.client_controller.gui._notebook:
            
            return
            
        media_page = HG.client_controller.gui._notebook.GetCurrentMediaPage()
        
        if not media_page or not media_page._media_panel:
            
            return
            
        self.menu = media_page._media_panel.ShowMenu( True )
        
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
                    
                    if not query in action.text() and not query in actionText:
                        
                        continue
                    
                    primary_text = highlight_result_text( actionText, query )
                    secondary_text = escape( parent_name )
                    
                    result.append( QLocatorSearchResult( self.result_id_counter, 'images.png', 'images.png', True, [ primary_text, secondary_text ] ) )
                    
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
 