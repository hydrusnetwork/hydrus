import os
import re

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientPaths
from hydrus.client.gui import ClientGUICore as CGC
from hydrus.client.gui import ClientGUIMenus
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui.widgets import ClientGUICommon

class RegexButton( ClientGUICommon.BetterButton ):
    
    def __init__( self, parent, show_group_menu = False, show_manage_favourites_menu = True ):
        
        super().__init__( parent, '.*', self._ShowMenu )
        
        self._show_group_menu = show_group_menu
        self._show_manage_favourites_menu = show_manage_favourites_menu
        
        width = ClientGUIFunctions.ConvertTextToPixelWidth( self, 4 )
        
        self.setFixedWidth( width )
        
    
    def _ShowMenu( self ):
        
        menu = ClientGUIMenus.GenerateMenu( self )
        
        submenu = ClientGUIMenus.GenerateMenu( menu )
        
        ClientGUIMenus.AppendMenuItem( submenu, 'a good regex introduction', 'If you have never heard of regex before, hit this!', ClientPaths.LaunchURLInWebBrowser, 'https://www.regular-expressions.info/index.html' )
        ClientGUIMenus.AppendMenuItem( submenu, 'a full interactive tutorial', 'If you want to work through a full lesson with problem solving on your end, hit this!', ClientPaths.LaunchURLInWebBrowser, 'https://www.regexone.com/' )
        ClientGUIMenus.AppendMenuItem( submenu, 'regex sandbox', 'You can play around here before you do something for real.', ClientPaths.LaunchURLInWebBrowser, 'https://regexr.com/3cvmf' )
        
        ClientGUIMenus.AppendMenu( menu, submenu, 'regex help' )
        
        #
        
        ClientGUIMenus.AppendSeparator( menu )
        
        #
        
        submenu = ClientGUIMenus.GenerateMenu( menu )
        
        ClientGUIMenus.AppendMenuLabel( submenu, 'click below to copy to clipboard', no_copy = True, make_it_bold = True )
        
        ClientGUIMenus.AppendSeparator( submenu )
        
        copy_desc = 'copy this phrase to the clipboard'
        
        ClientGUIMenus.AppendMenuItem( submenu, r'whitespace character - \s', copy_desc, CG.client_controller.pub, 'clipboard', 'text', r'\s' )
        ClientGUIMenus.AppendMenuItem( submenu, r'number character - \d', copy_desc, CG.client_controller.pub, 'clipboard', 'text', r'\d' )
        ClientGUIMenus.AppendMenuItem( submenu, r'alphanumeric or underscore character - \w', copy_desc, CG.client_controller.pub, 'clipboard', 'text', r'\w' )
        ClientGUIMenus.AppendMenuItem( submenu, r'any character - .', copy_desc, CG.client_controller.pub, 'clipboard', 'text', r'.' )
        ClientGUIMenus.AppendMenuItem( submenu, r'backslash character - \\', copy_desc, CG.client_controller.pub, 'clipboard', 'text', r'\\' )
        ClientGUIMenus.AppendMenuItem( submenu, r'beginning of line - ^', copy_desc, CG.client_controller.pub, 'clipboard', 'text', r'^' )
        ClientGUIMenus.AppendMenuItem( submenu, r'end of line - $', copy_desc, CG.client_controller.pub, 'clipboard', 'text', r'$' )
        ClientGUIMenus.AppendMenuItem( submenu, f'any of these - [{HC.UNICODE_ELLIPSIS}]', copy_desc, CG.client_controller.pub, 'clipboard', f'text', '[{HC.UNICODE_ELLIPSIS}]' )
        ClientGUIMenus.AppendMenuItem( submenu, f'anything other than these - [^{HC.UNICODE_ELLIPSIS}]', copy_desc, CG.client_controller.pub, 'clipboard', 'text', f'[^{HC.UNICODE_ELLIPSIS}]' )
        
        ClientGUIMenus.AppendSeparator( submenu )
        
        ClientGUIMenus.AppendMenuItem( submenu, r'0 or more matches, consuming as many as possible - *', copy_desc, CG.client_controller.pub, 'clipboard', 'text', r'*' )
        ClientGUIMenus.AppendMenuItem( submenu, r'1 or more matches, consuming as many as possible - +', copy_desc, CG.client_controller.pub, 'clipboard', 'text', r'+' )
        ClientGUIMenus.AppendMenuItem( submenu, r'0 or 1 matches, preferring 1 - ?', copy_desc, CG.client_controller.pub, 'clipboard', 'text', r'?' )
        ClientGUIMenus.AppendMenuItem( submenu, r'0 or more matches, consuming as few as possible - *?', copy_desc, CG.client_controller.pub, 'clipboard', 'text', r'*?' )
        ClientGUIMenus.AppendMenuItem( submenu, r'1 or more matches, consuming as few as possible - +?', copy_desc, CG.client_controller.pub, 'clipboard', 'text', r'+?' )
        ClientGUIMenus.AppendMenuItem( submenu, r'0 or 1 matches, preferring 0 - ??', copy_desc, CG.client_controller.pub, 'clipboard', 'text', r'??' )
        ClientGUIMenus.AppendMenuItem( submenu, r'exactly m matches - {m}', copy_desc, CG.client_controller.pub, 'clipboard', 'text', r'{m}' )
        ClientGUIMenus.AppendMenuItem( submenu, r'm to n matches, consuming as many as possible - {m,n}', copy_desc, CG.client_controller.pub, 'clipboard', 'text', r'{m,n}' )
        ClientGUIMenus.AppendMenuItem( submenu, r'm to n matches, consuming as few as possible - {m,n}?', copy_desc, CG.client_controller.pub, 'clipboard', 'text', r'{m,n}?' )
        
        ClientGUIMenus.AppendSeparator( submenu )
        
        ClientGUIMenus.AppendMenuItem( submenu, f'the next characters are: (non-consuming) - (?={HC.UNICODE_ELLIPSIS})', copy_desc, CG.client_controller.pub, 'clipboard', 'text', f'(?={HC.UNICODE_ELLIPSIS})' )
        ClientGUIMenus.AppendMenuItem( submenu, f'the next characters are not: (non-consuming) - (?!{HC.UNICODE_ELLIPSIS})', copy_desc, CG.client_controller.pub, 'clipboard', 'text', f'(?!{HC.UNICODE_ELLIPSIS})' )
        ClientGUIMenus.AppendMenuItem( submenu, f'the previous characters are: (non-consuming) - (?<={HC.UNICODE_ELLIPSIS})', copy_desc, CG.client_controller.pub, 'clipboard', 'text', f'(?<={HC.UNICODE_ELLIPSIS})' )
        ClientGUIMenus.AppendMenuItem( submenu, f'the previous characters are not: (non-consuming) - (?<!{HC.UNICODE_ELLIPSIS})', copy_desc, CG.client_controller.pub, 'clipboard', 'text', f'(?<!{HC.UNICODE_ELLIPSIS})' )
        
        ClientGUIMenus.AppendSeparator( submenu )
        
        ClientGUIMenus.AppendMenuItem( submenu, r'0074 -> 74 - [1-9]+\d*', copy_desc, CG.client_controller.pub, 'clipboard', 'text', r'[1-9]+\d*' )
        ClientGUIMenus.AppendMenuItem( submenu, r'filename - (?<=' + re.escape( os.path.sep ) + r')[^' + re.escape( os.path.sep ) + r']*?(?=\..*$)', copy_desc, CG.client_controller.pub, 'clipboard', 'text', '(?<=' + re.escape( os.path.sep ) + r')[^' + re.escape( os.path.sep ) + r']*?(?=\..*$)' )
        
        ClientGUIMenus.AppendMenu( menu, submenu, 'regex components' )
        
        #
        
        if self._show_group_menu:
            
            submenu = ClientGUIMenus.GenerateMenu( menu )
            
            ClientGUIMenus.AppendMenuLabel( submenu, 'click below to copy to clipboard', no_copy = True, make_it_bold = True )
            
            ClientGUIMenus.AppendSeparator( submenu )
            
            copy_desc = 'copy this phrase to the clipboard'
            
            ClientGUIMenus.AppendMenuLabel( submenu, '-in the pattern-', no_copy = True )
            
            ClientGUIMenus.AppendMenuItem( submenu, f'unnamed group - ({HC.UNICODE_ELLIPSIS})', copy_desc, CG.client_controller.pub, 'clipboard', 'text', f'({HC.UNICODE_ELLIPSIS})' )
            ClientGUIMenus.AppendMenuItem( submenu, f'named group - (?P<name>{HC.UNICODE_ELLIPSIS})', copy_desc, CG.client_controller.pub, 'clipboard', 'text', f'(?P<name>{HC.UNICODE_ELLIPSIS})' )
            
            ClientGUIMenus.AppendSeparator( submenu )
            
            ClientGUIMenus.AppendMenuLabel( submenu, '-in the replacement-', no_copy = True )
            
            ClientGUIMenus.AppendMenuItem( submenu, r'reference nth unnamed group - \1', copy_desc, CG.client_controller.pub, 'clipboard', 'text', r'\1' )
            ClientGUIMenus.AppendMenuItem( submenu, r'reference named group - \g<name>', copy_desc, CG.client_controller.pub, 'clipboard', 'text', r'\g<name>' )
            
            ClientGUIMenus.AppendMenu( menu, submenu, 'regex replacement groups' )
            
        
        #
        
        submenu = ClientGUIMenus.GenerateMenu( menu )
        
        if self._show_manage_favourites_menu:
            
            ClientGUIMenus.AppendMenuItem( submenu, 'manage favourites', 'manage some custom favourite phrases', self._ManageFavourites )
            
            ClientGUIMenus.AppendSeparator( submenu )
            
        
        ClientGUIMenus.AppendMenuLabel( submenu, 'click below to copy to clipboard', no_copy = True, make_it_bold = True )
        
        ClientGUIMenus.AppendSeparator( submenu )
        
        for ( regex_phrase, description ) in HC.options[ 'regex_favourites' ]:
            
            ClientGUIMenus.AppendMenuItem( submenu, description, copy_desc, CG.client_controller.pub, 'clipboard', 'text', regex_phrase )
            
        
        ClientGUIMenus.AppendMenu( menu, submenu, 'favourites' )
        
        CGC.core().PopupMenu( self, menu )
        
    
    def _ManageFavourites( self ):
        
        regex_favourites = HC.options[ 'regex_favourites' ]
        
        from hydrus.client.gui import ClientGUITopLevelWindowsPanels
        from hydrus.client.gui.panels import ClientGUIScrolledPanelsEditRegexFavourites
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'manage regex favourites' ) as dlg:
            
            panel = ClientGUIScrolledPanelsEditRegexFavourites.EditRegexFavourites( dlg, regex_favourites )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                regex_favourites = panel.GetValue()
                
                HC.options[ 'regex_favourites' ] = regex_favourites
                
                CG.client_controller.Write( 'save_options', HC.options )
                
            
        
    

class RegexInput( QW.QWidget ):
    
    textChanged = QC.Signal()
    
    def __init__( self, parent: QW.QWidget, show_group_menu = False, show_manage_favourites_menu = True ):
        
        super().__init__( parent )
        
        self._allow_enter_key_to_propagate_outside = True
        
        self._regex_text = QW.QLineEdit( self )
        self._regex_text.setPlaceholderText( 'regex' )
        
        self._regex_button = RegexButton( self, show_group_menu = show_group_menu, show_manage_favourites_menu = show_manage_favourites_menu )
        
        hbox = QP.HBoxLayout( margin = 0 )
        
        QP.AddToLayout( hbox, self._regex_text, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, self._regex_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self.setLayout( hbox )
        
        self.setFocusProxy( self._regex_text )
        self.setFocusPolicy( QC.Qt.FocusPolicy.StrongFocus )
        
        self._regex_text.textChanged.connect( self.textChanged )
        self._regex_text.textChanged.connect( self._UpdateValidityStyle )
        
        self._UpdateValidityStyle()
        
    
    def _UpdateValidityStyle( self ):
        
        try:
            
            re.compile( self._regex_text.text() )
            
            self._regex_text.setObjectName( 'HydrusValid' )
            
        except:
            
            self._regex_text.setObjectName( 'HydrusInvalid' )
            
        
        self._regex_text.style().polish( self._regex_text )
        
    
    def SetEnterCallable( self, c ):
        
        # note that this guy stops further processing of Enter presses so this guy now won't trigger dialog ok!
        self._regex_text.installEventFilter( ClientGUICommon.TextCatchEnterEventFilter( self, c ) )
        
    
    def GetValue( self ) -> str:
        
        return self._regex_text.text()
        
    
    def SetValue( self, regex: str ):
        
        self._regex_text.setText( regex )
        
    
