import collections
import collections.abc

from PIL import ExifTags

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG

from hydrus.core import HydrusCompression
from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusStaticDir
from hydrus.core import HydrusText
from hydrus.core import HydrusTime
from hydrus.core.processes import HydrusThreading

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientData
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientLocation
from hydrus.client import ClientRendering
from hydrus.client import ClientSerialisable
from hydrus.client import ClientThreading
from hydrus.client.files import ClientFilesMaintenance
from hydrus.client.gui import ClientGUIAsync
from hydrus.client.gui import ClientGUICharts
from hydrus.client.gui import ClientGUIDialogsFiles
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIDragDrop
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListConstants as CGLC
from hydrus.client.gui.lists import ClientGUIListCtrl
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.search import ClientGUIACDropdown
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.gui.widgets import ClientGUIMenuButton
from hydrus.client.networking import ClientNetworkingContexts
from hydrus.client.networking import ClientNetworkingDomain
from hydrus.client.networking import ClientNetworkingGUG
from hydrus.client.networking import ClientNetworkingLogin
from hydrus.client.networking import ClientNetworkingURLClass
from hydrus.client.parsing import ClientParsing
from hydrus.client.search import ClientSearchFileSearchContext

class AboutPanel( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent, name, version, description_versions, description_availability, license_text, developers, site ):
        
        super().__init__( parent )
        
        icon_label = ClientGUICommon.BetterStaticText( self )
        icon_label.setPixmap( CC.global_icons().hydrus_frame.pixmap( 32, 32 ) )
        
        name_label = ClientGUICommon.BetterStaticText( self, name )
        name_label_font = name_label.font()
        name_label_font.setBold( True )
        name_label.setFont( name_label_font )
        
        version_label = ClientGUICommon.BetterStaticText( self, version )
        
        url_label = ClientGUICommon.BetterHyperLink( self, site, site )
        
        tabwidget = QW.QTabWidget( self )
        
        #
        
        desc_label = ClientGUICommon.BetterStaticText( self, description_versions )
        desc_label.setAlignment( QC.Qt.AlignmentFlag.AlignHCenter | QC.Qt.AlignmentFlag.AlignVCenter )
        desc_label.setWordWrap( True )
        
        #
        
        availability_label = ClientGUICommon.BetterStaticText( self, description_availability )
        availability_label.setAlignment( QC.Qt.AlignmentFlag.AlignHCenter | QC.Qt.AlignmentFlag.AlignVCenter )
        availability_label.setWordWrap( True )
        
        #
        
        credits = QW.QTextEdit( self )
        credits.setPlainText( 'Created by ' + ', '.join( developers ) )
        credits.setReadOnly( True )
        credits.setAlignment( QC.Qt.AlignmentFlag.AlignHCenter )
        
        license_textedit = QW.QTextEdit( self )
        license_textedit.setPlainText( license_text )
        license_textedit.setReadOnly( True )
        
        text_width = ClientGUIFunctions.ConvertTextToPixelWidth( license_textedit, 64 )
        
        license_textedit.setFixedWidth( text_width )
        
        tabwidget.addTab( desc_label, 'Description' )
        tabwidget.addTab( availability_label, 'Optional Libraries' )
        tabwidget.addTab( credits, 'Credits' )
        tabwidget.addTab( license_textedit, 'License' )
        tabwidget.setCurrentIndex( 0 )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, icon_label, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( vbox, name_label, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( vbox, version_label, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( vbox, url_label, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( vbox, tabwidget, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self.widget().setLayout( vbox )
        
    

class ReviewDownloaderImport( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent, network_engine ):
        
        super().__init__( parent )
        
        self._network_engine = network_engine
        
        vbox = QP.VBoxLayout()
        
        menu_template_items = []
        
        page_func = HydrusData.Call( ClientGUIDialogsQuick.OpenDocumentation, self, HC.DOCUMENTATION_ADDING_NEW_DOWNLOADERS )
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'open the easy downloader import help', 'Open the help page for easily importing downloaders in your web browser.', page_func ) )
        
        help_button = ClientGUIMenuButton.MenuIconButton( self, CC.global_icons().help, menu_template_items )
        
        help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help -->', object_name = 'HydrusIndeterminate' )
        
        self._repo_link = ClientGUICommon.BetterHyperLink( self, 'get user-made downloaders here', 'https://github.com/CuddleBear92/Hydrus-Presets-and-Scripts/tree/master/Downloaders' )
        
        self._paste_button = ClientGUICommon.IconButton( self, CC.global_icons().paste, self._Paste )
        self._paste_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'Paste paths/bitmaps/JSON from clipboard!' ) )
        
        st = ClientGUICommon.BetterStaticText( self, label = 'To import, drag-and-drop hydrus\'s special downloader-encoded pngs onto Lain. Or click her to open a file selection dialog, or copy the png bitmap, file path, or raw downloader JSON to your clipboard and hit the paste button.' )
        
        st.setWordWrap( True )
        st.setAlignment( QC.Qt.AlignmentFlag.AlignCenter )
        
        lain_path = HydrusStaticDir.GetStaticPath( 'lain.jpg' )
        
        lain_qt_pixmap = ClientRendering.GenerateHydrusBitmap( lain_path, HC.IMAGE_JPEG ).GetQtPixmap()
        
        win = QW.QLabel( self, pixmap = lain_qt_pixmap )
        
        win.setCursor( QG.QCursor( QC.Qt.CursorShape.PointingHandCursor ) )
        
        self._select_from_list = QW.QCheckBox( self )
        self._select_from_list.setToolTip( ClientGUIFunctions.WrapToolTip( 'If the payload includes multiple objects (most do), select what you want to import.' ) )
        
        if CG.client_controller.new_options.GetBoolean( 'advanced_mode' ):
            
            self._select_from_list.setChecked( True )
            
        
        QP.AddToLayout( vbox, help_hbox, CC.FLAGS_ON_RIGHT )
        QP.AddToLayout( vbox, self._repo_link, CC.FLAGS_CENTER )
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._paste_button, CC.FLAGS_ON_RIGHT )
        QP.AddToLayout( vbox, win, CC.FLAGS_CENTER )
        QP.AddToLayout( vbox, ClientGUICommon.WrapInText( self._select_from_list, self, 'select objects from list' ), CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self.widget().setLayout( vbox )
        
        #
        
        win.installEventFilter( ClientGUIDragDrop.FileDropTarget( win, filenames_callable = self.ImportFromDragDrop ) )
        
        self._lain_event_filter = QP.WidgetEventFilter( win )
        self._lain_event_filter.EVT_LEFT_DOWN( self.EventLainClick )
        
    
    def _ImportPaths( self, paths ):
        
        payloads = []
        
        for path in paths:
            
            try:
                
                payload = ClientSerialisable.LoadFromPNG( path )
                
            except Exception as e:
                
                HydrusData.PrintException( e )
                
                ClientGUIDialogsMessage.ShowCritical( self, 'Problem loading PNG!', str(e) )
                
                return
                
            
            payloads.append( ( 'file "{}"'.format( path ), payload ) )
            
        
        self._ImportPayloads( payloads )
        
    
    def _ImportPayloads( self, payloads ):
        
        have_shown_load_error = False
        
        gugs = []
        url_classes = []
        parsers = []
        domain_metadatas = []
        login_scripts = []
        
        num_misc_objects = 0
        
        bandwidth_manager = self._network_engine.bandwidth_manager
        domain_manager = self._network_engine.domain_manager
        login_manager = self._network_engine.login_manager
        
        for ( payload_description, payload ) in payloads:
            
            try:
                
                obj_list = HydrusSerialisable.CreateFromNetworkBytes( payload, raise_error_on_future_version = True )
                
            except HydrusExceptions.SerialisationException as e:
                
                if not have_shown_load_error:
                    
                    message = str( e )
                    
                    if len( payloads ) > 1:
                        
                        message += '\n' * 2
                        message += 'If there are more unloadable objects in this import, they will be skipped silently.'
                        
                    
                    ClientGUIDialogsMessage.ShowCritical( self, 'Serialisation Object Load Error!', message )
                    
                    have_shown_load_error = True
                    
                
                continue
                
            except Exception as e:
                
                HydrusData.PrintException( e )
                
                ClientGUIDialogsMessage.ShowCritical( self, 'Error', 'I could not understand what was encoded in {}!'.format( payload_description ) )
                
                continue
                
            
            if isinstance( obj_list, ( ClientNetworkingGUG.GalleryURLGenerator, ClientNetworkingGUG.NestedGalleryURLGenerator, ClientNetworkingURLClass.URLClass, ClientParsing.PageParser, ClientNetworkingDomain.DomainMetadataPackage, ClientNetworkingLogin.LoginScriptDomain ) ):
                
                obj_list = HydrusSerialisable.SerialisableList( [ obj_list ] )
                
            
            if not isinstance( obj_list, HydrusSerialisable.SerialisableList ):
                
                ClientGUIDialogsMessage.ShowWarning( self, 'Unfortunately, {} did not look like a package of download data! Instead, it looked like: {}'.format( payload_description, obj_list.SERIALISABLE_NAME ) )
                
                continue
                
            
            for obj in obj_list:
                
                if isinstance( obj, ( ClientNetworkingGUG.GalleryURLGenerator, ClientNetworkingGUG.NestedGalleryURLGenerator ) ):
                    
                    gugs.append( obj )
                    
                elif isinstance( obj, ClientNetworkingURLClass.URLClass ):
                    
                    url_classes.append( obj )
                    
                elif isinstance( obj, ClientParsing.PageParser ):
                    
                    parsers.append( obj )
                    
                elif isinstance( obj, ClientNetworkingDomain.DomainMetadataPackage ):
                    
                    domain_metadatas.append( obj )
                    
                elif isinstance( obj, ClientNetworkingLogin.LoginScriptDomain ):
                    
                    login_scripts.append( obj )
                    
                else:
                    
                    num_misc_objects += 1
                    
                
            
        
        if len( gugs ) + len( url_classes ) + len( parsers ) + len( domain_metadatas ) + len( login_scripts ) == 0:
            
            if num_misc_objects > 0:
                
                ClientGUIDialogsMessage.ShowWarning( self, 'I found '+HydrusNumbers.ToHumanInt(num_misc_objects)+' misc objects in that png, but nothing downloader related.' )
                
            
            return
            
        
        # url matches first
        
        url_class_names_seen = set()
        
        dupe_url_classes = []
        num_exact_dupe_url_classes = 0
        new_url_classes = []
        
        for url_class in url_classes:
            
            if url_class.GetName() in url_class_names_seen:
                
                continue
                
            
            if domain_manager.AlreadyHaveExactlyThisURLClass( url_class ):
                
                dupe_url_classes.append( url_class )
                num_exact_dupe_url_classes += 1
                
            else:
                
                new_url_classes.append( url_class )
                
                url_class_names_seen.add( url_class.GetName() )
                
            
        
        # now gugs
        
        gug_names_seen = set()
        
        num_exact_dupe_gugs = 0
        new_gugs = []
        
        for gug in gugs:
            
            if gug.GetName() in gug_names_seen:
                
                continue
                
            
            if domain_manager.AlreadyHaveExactlyThisGUG( gug ):
                
                num_exact_dupe_gugs += 1
                
            else:
                
                new_gugs.append( gug )
                
                gug_names_seen.add( gug.GetName() )
                
            
        
        # now parsers
        
        parser_names_seen = set()
        
        num_exact_dupe_parsers = 0
        new_parsers = []
        
        for parser in parsers:
            
            if parser.GetName() in parser_names_seen:
                
                continue
                
            
            if domain_manager.AlreadyHaveExactlyThisParser( parser ):
                
                num_exact_dupe_parsers += 1
                
            else:
                
                new_parsers.append( parser )
                
                parser_names_seen.add( parser.GetName() )
                
            
        
        # now login scripts
        
        login_script_names_seen = set()
        
        num_exact_dupe_login_scripts = 0
        new_login_scripts = []
        
        for login_script in login_scripts:
            
            if login_script.GetName() in login_script_names_seen:
                
                continue
                
            
            if login_manager.AlreadyHaveExactlyThisLoginScript( login_script ):
                
                num_exact_dupe_login_scripts += 1
                
            else:
                
                new_login_scripts.append( login_script )
                
                login_script_names_seen.add( login_script.GetName() )
                
            
        
        # now domain metadata
        
        domains_seen = set()
        
        num_exact_dupe_domain_metadatas = 0
        new_domain_metadatas = []
        
        for domain_metadata in domain_metadatas:
            
            # check if the headers or rules are new, discarding any dupe content
            
            domain = domain_metadata.GetDomain()
            headers_list = None
            bandwidth_rules = None
            
            if domain in domains_seen:
                
                continue
                
            
            nc = ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_DOMAIN, domain )
            
            if domain_metadata.HasHeaders():
                
                headers_list = domain_metadata.GetHeaders()
                
                if domain_manager.AlreadyHaveExactlyTheseHeaders( nc, headers_list ):
                    
                    headers_list = None
                    
                
            
            if domain_metadata.HasBandwidthRules():
                
                bandwidth_rules = domain_metadata.GetBandwidthRules()
                
                if bandwidth_manager.AlreadyHaveExactlyTheseBandwidthRules( nc, bandwidth_rules ):
                    
                    bandwidth_rules = None
                    
                
            
            if headers_list is None and bandwidth_rules is None:
                
                num_exact_dupe_domain_metadatas += 1
                
            else:
                
                new_dm = ClientNetworkingDomain.DomainMetadataPackage( domain = domain, headers_list = headers_list, bandwidth_rules = bandwidth_rules )
                
                new_domain_metadatas.append( new_dm )
                
                domains_seen.add( domain )
                
            
        
        #
        
        total_num_dupes = num_exact_dupe_gugs + num_exact_dupe_url_classes + num_exact_dupe_parsers + num_exact_dupe_domain_metadatas + num_exact_dupe_login_scripts
        
        if len( new_gugs ) + len( new_url_classes ) + len( new_parsers ) + len( new_domain_metadatas ) + len( new_login_scripts ) == 0:
            
            ClientGUIDialogsMessage.ShowInformation( self, f'All {HydrusNumbers.ToHumanInt( total_num_dupes )} downloader objects in that package appeared to already be in the client, so nothing need be added.' )
            
            return
            
        
        # let's start selecting what we want
        
        if self._select_from_list.isChecked():
            
            choice_tuples = []
            choice_tuples.extend( [ ( 'GUG: ' + gug.GetName(), gug, True ) for gug in new_gugs ] )
            choice_tuples.extend( [ ( 'URL Class: ' + url_class.GetName(), url_class, True ) for url_class in new_url_classes ] )
            choice_tuples.extend( [ ( 'Parser: ' + parser.GetName(), parser, True ) for parser in new_parsers ] )
            choice_tuples.extend( [ ( 'Login Script: ' + login_script.GetName(), login_script, True ) for login_script in new_login_scripts ] )
            choice_tuples.extend( [ ( 'Domain Metadata: ' + domain_metadata.GetDomain(), domain_metadata, True ) for domain_metadata in new_domain_metadatas ] )
            
            try:
                
                new_objects = ClientGUIDialogsQuick.SelectMultipleFromList( self, 'select objects to add', choice_tuples )
                
            except HydrusExceptions.CancelledException:
                
                return
                
            
            new_gugs = [ obj for obj in new_objects if isinstance( obj, ( ClientNetworkingGUG.GalleryURLGenerator, ClientNetworkingGUG.NestedGalleryURLGenerator ) ) ]
            new_url_classes = [ obj for obj in new_objects if isinstance( obj, ClientNetworkingURLClass.URLClass ) ]
            new_parsers = [ obj for obj in new_objects if isinstance( obj, ClientParsing.PageParser ) ]
            new_login_scripts = [ obj for obj in new_objects if isinstance( obj, ClientNetworkingLogin.LoginScriptDomain ) ]
            new_domain_metadatas = [ obj for obj in new_objects if isinstance( obj, ClientNetworkingDomain.DomainMetadataPackage ) ]
            
        
        # final ask
        
        new_gugs.sort( key = lambda o: o.GetName() )
        new_url_classes.sort( key = lambda o: o.GetName() )
        new_parsers.sort( key = lambda o: o.GetName() )
        new_login_scripts.sort( key = lambda o: o.GetName() )
        new_domain_metadatas.sort( key = lambda o: o.GetDomain() )
        
        if len( new_domain_metadatas ) > 0:
            
            message = 'Before the final import confirmation, I will now show the domain metadata in detail. Give it a cursory look just to check it seems good. If not, click no on the final dialog!'
            
            TOO_MANY_DM = 8
            
            if len( new_domain_metadatas ) > TOO_MANY_DM:
                
                message += '\n' * 2
                message += 'There are more than ' + HydrusNumbers.ToHumanInt( TOO_MANY_DM ) + ' domain metadata objects. So I do not give you dozens of preview windows, I will only show you these first ' + HydrusNumbers.ToHumanInt( TOO_MANY_DM ) + '.'
                
            
            new_domain_metadatas_to_show = new_domain_metadatas[:TOO_MANY_DM]
            
            for new_dm in new_domain_metadatas_to_show:
                
                ClientGUIDialogsMessage.ShowInformation( self, new_dm.GetDetailedSafeSummary() )
                
            
        
        all_to_add = list( new_gugs )
        all_to_add.extend( new_url_classes )
        all_to_add.extend( new_parsers )
        all_to_add.extend( new_login_scripts )
        all_to_add.extend( new_domain_metadatas )
        
        message = 'The client is about to add and link these objects:'
        message += '\n' * 2
        message += '\n'.join( ( obj.GetSafeSummary() for obj in all_to_add[:20] ) )
        
        if len( all_to_add ) > 20:
            
            message += '\n'
            message += '(and ' + HydrusNumbers.ToHumanInt( len( all_to_add ) - 20 ) + ' others)'
            
        
        message += '\n' * 2
        message += 'Does that sound good?'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result != QW.QDialog.DialogCode.Accepted:
            
            return
            
        
        # ok, do it
        
        if len( new_gugs ) > 0:
            
            for gug in new_gugs:
                
                gug.RegenerateGUGKey()
                
            
            domain_manager.AddGUGs( new_gugs )
            
        
        domain_manager.AutoAddURLClassesAndParsers( new_url_classes, dupe_url_classes, new_parsers )
        
        bandwidth_manager.AutoAddDomainMetadatas( new_domain_metadatas )
        domain_manager.AutoAddDomainMetadatas( new_domain_metadatas, approved = ClientNetworkingDomain.VALID_APPROVED )
        login_manager.AutoAddLoginScripts( new_login_scripts )
        
        num_new_gugs = len( new_gugs )
        num_aux = len( new_url_classes ) + len( new_parsers ) + len( new_login_scripts ) + len( new_domain_metadatas )
        
        final_message = 'Successfully added ' + HydrusNumbers.ToHumanInt( num_new_gugs ) + ' new downloaders and ' + HydrusNumbers.ToHumanInt( num_aux ) + ' auxiliary objects.'
        
        if total_num_dupes > 0:
            
            final_message += ' ' + HydrusNumbers.ToHumanInt( total_num_dupes ) + ' duplicate objects were not added (but some additional metadata may have been merged).'
            
        
        ClientGUIDialogsMessage.ShowInformation( self, final_message )
        
    
    def _Paste( self ):
        
        if CG.client_controller.ClipboardHasImage():
            
            try:
                
                qt_image = CG.client_controller.GetClipboardImage()
                
                payload_description = 'clipboard image data'
                payload = ClientSerialisable.LoadFromQtImage( qt_image )
                
            except Exception as e:
                
                ClientGUIDialogsMessage.ShowCritical( self, 'Problem pasting image!', f'Sorry, seemed to be a problem: {e}' )
                
                return
                
            
        elif CG.client_controller.ClipboardHasLocalPaths():
            
            try:
                
                paths = CG.client_controller.GetClipboardLocalPaths()
                
                self._ImportPaths( paths )
                
                return
                
            except HydrusExceptions.DataMissing as e:
                
                ClientGUIDialogsMessage.ShowCritical( self, 'Problem pasting paths!', f'Sorry, seemed to be a problem: {e}' )
                
                return
                
            
        else:
            
            try:
                
                raw_text = CG.client_controller.GetClipboardText()
                
                payload_description = 'clipboard text data'
                payload = HydrusCompression.CompressStringToBytes( raw_text )
                
            except HydrusExceptions.DataMissing as e:
                
                ClientGUIDialogsMessage.ShowCritical( self, 'Problem pasting text!', f'Sorry, seemed to be a problem: {e}' )
                
                return
                
            
        
        payloads = [ ( payload_description, payload ) ]
        
        self._ImportPayloads( payloads )
        
    
    def EventLainClick( self, event ):
        
        with ClientGUIDialogsFiles.FileDialog( self, 'Select the pngs to add.', acceptMode = QW.QFileDialog.AcceptMode.AcceptOpen, fileMode = QW.QFileDialog.FileMode.ExistingFiles, wildcard = 'PNG (*.png)' ) as dlg:
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                paths = dlg.GetPaths()
                
                self._ImportPaths( paths )
                
            
        
    
    def ImportFromDragDrop( self, paths ):
        
        self._ImportPaths( paths )
        
    

class ReviewFileEmbeddedMetadata( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent, mime: int, top_line_text: str, exif_dict: dict | None, file_text: str | None, extra_rows: list[ tuple[ str, str ] ] ):
        
        super().__init__( parent )
        
        #
        
        top_line_panel = ClientGUICommon.StaticBox( self, 'basics' )
        
        self._top_line_str = ClientGUICommon.BetterStaticText( top_line_panel, top_line_text )
        
        top_line_panel.Add( self._top_line_str, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        exif_panel = ClientGUICommon.StaticBox( self, 'EXIF' )
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_EXIF_DATA.ID, self._ConvertEXIFToDataTuple, self._ConvertEXIFToSortTuple )
        
        self._exif_listctrl = ClientGUIListCtrl.BetterListCtrlTreeView( exif_panel, 16, model, activation_callback = self._CopyRow )
        
        label = 'Double-click a row to copy its value to clipboard.'
        
        if mime == HC.IMAGE_PNG:
            
            label += '\n'
            label += 'Note that while PNGs can store EXIF data, it is not a well-defined standard. Hydrus does not apply EXIF Orientation (rotation) metadata to PNGs.'
            
        
        st = ClientGUICommon.BetterStaticText( exif_panel, label = label )
        
        st.setWordWrap( True )
        st.setAlignment( QC.Qt.AlignmentFlag.AlignCenter )
        
        exif_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
        exif_panel.Add( self._exif_listctrl, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        text_panel = ClientGUICommon.StaticBox( self, 'embedded text' )
        
        self._text = QW.QPlainTextEdit( text_panel )
        self._text.setReadOnly( True )
        
        text_panel.Add( self._text, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        extra_rows_panel = ClientGUICommon.StaticBox( self, 'extra info' )
        
        rows = [ ( f'{key}: ', ClientGUICommon.BetterStaticText( extra_rows_panel, label = value ) ) for ( key, value ) in extra_rows ]
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        extra_rows_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        if exif_dict is None:
            
            exif_panel.setVisible( False )
            
        else:
            
            datas = []
            
            for ( exif_id, value ) in exif_dict.items():
                
                if isinstance( value, dict ):
                    
                    datas.extend( value.items() )
                    
                else:
                    
                    datas.append( ( exif_id, value ) )
                    
                
            
            self._exif_listctrl.AddDatas( datas )
            
        
        if file_text is None:
            
            text_panel.setVisible( False )
            
        else:
            
            self._text.setPlainText( file_text )
            
        
        if len( extra_rows ) == 0:
            
            extra_rows_panel.setVisible( False )
            
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, top_line_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, exif_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, text_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, extra_rows_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.widget().setLayout( vbox )
        
    
    def _ConvertEXIFToDataTuple( self, exif_tuple ):
        
        ( exif_id, raw_value ) = exif_tuple
        
        if exif_id in ExifTags.TAGS:
            
            label = ExifTags.TAGS[ exif_id ]
            pretty_label = label
            
        elif exif_id in ExifTags.GPSTAGS:
            
            label = ExifTags.GPSTAGS[ exif_id ]
            pretty_label = label
            
        else:
            
            pretty_label = 'Unknown'
            
        
        pretty_id = str( exif_id )
        
        if isinstance( raw_value, bytes ):
            
            value = raw_value.hex()
            pretty_value = '{}: {}'.format( HydrusData.ToHumanBytes( len( raw_value ) ), value )
            
        else:
            
            value = str( raw_value )
            
            if HydrusText.NULL_CHARACTER in value:
                
                value = value.replace( HydrusText.NULL_CHARACTER, '[null]' )
                
            
            pretty_value = value
            
        
        display_tuple = ( pretty_id, pretty_label, pretty_value )
        
        return display_tuple
        
    
    def _ConvertEXIFToSortTuple( self, exif_tuple ):
        
        ( exif_id, raw_value ) = exif_tuple
        
        if exif_id in ExifTags.TAGS:
            
            label = ExifTags.TAGS[ exif_id ]
            
        elif exif_id in ExifTags.GPSTAGS:
            
            label = ExifTags.GPSTAGS[ exif_id ]
            
        else:
            
            label = 'zzz'
            
        
        if isinstance( raw_value, bytes ):
            
            value = raw_value.hex()
            
        else:
            
            value = str( raw_value )
            
            if HydrusText.NULL_CHARACTER in value:
                
                value = value.replace( HydrusText.NULL_CHARACTER, '[null]' )
                
            
        
        sort_tuple = ( exif_id, label, value )
        
        return sort_tuple
        
    
    def _CopyRow( self ):
        
        selected_exif_tuples = self._exif_listctrl.GetData( only_selected = True )
        
        if len( selected_exif_tuples ) == 0:
            
            return
            
        
        ( first_row_id, first_row_value ) = selected_exif_tuples[0]
        
        if isinstance( first_row_value, bytes ):
            
            copy_text = first_row_value.hex()
            
        else:
            
            copy_text = str( first_row_value )
            
        
        CG.client_controller.pub( 'clipboard', 'text', copy_text )
        
    
class ReviewFileHistory( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent ):
        
        super().__init__( parent )
        
        self._job_status = ClientThreading.JobStatus()
        
        #
        
        self._have_initialised_x_axis = False
        
        self._search_panel = QW.QWidget( self )
        
        # TODO: ok add 'num_steps' as a control, and a date range
        
        panel_vbox = QP.VBoxLayout()
        
        file_search_context = ClientSearchFileSearchContext.FileSearchContext(
            location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY )
        )
        
        page_key = b'mr bones placeholder'
        
        self._tag_autocomplete = ClientGUIACDropdown.AutoCompleteDropdownTagsRead(
            self._search_panel,
            page_key,
            file_search_context,
            allow_all_known_files = False,
            force_system_everything = True,
            fixed_results_list_height = 8
        )
        
        self._loading_text = ClientGUICommon.BetterStaticText( self._search_panel )
        self._loading_text.setAlignment( QC.Qt.AlignmentFlag.AlignVCenter | QC.Qt.AlignmentFlag.AlignRight )
        
        self._cancel_button = ClientGUICommon.IconButton( self._search_panel, CC.global_icons().stop, self._CancelCurrentSearch )
        self._refresh_button = ClientGUICommon.IconButton( self._search_panel, CC.global_icons().refresh, self._RefreshSearch )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._loading_text, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH )
        QP.AddToLayout( hbox, self._cancel_button, CC.FLAGS_CENTER )
        QP.AddToLayout( hbox, self._refresh_button, CC.FLAGS_CENTER )
        
        QP.AddToLayout( panel_vbox, self._tag_autocomplete, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( panel_vbox, hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self._search_panel.setLayout( panel_vbox )
        
        #
        
        self._rightmost_panel = QW.QWidget( self )
        
        self._status_st = ClientGUICommon.BetterStaticText( self._rightmost_panel, label = f'loading{HC.UNICODE_ELLIPSIS}' )
        
        self._file_history_chart_panel = QW.QWidget( self._rightmost_panel )
        
        self._show_current = QW.QCheckBox( 'show all', self._file_history_chart_panel )
        self._show_inbox = QW.QCheckBox( 'show inbox', self._file_history_chart_panel )
        self._show_archive = QW.QCheckBox( 'show archive', self._file_history_chart_panel )
        self._show_deleted = QW.QCheckBox( 'show deleted', self._file_history_chart_panel )
        
        empty_file_history = {
            'current' : [],
            'deleted' : [],
            'inbox' : [],
            'archive' : [],
        }
        
        self._file_history_chart = ClientGUICharts.FileHistory( self._file_history_chart_panel, empty_file_history, True, True, True, True )
        
        self._file_history_chart.setMinimumSize( 720, 480 )
        
        self._start_date = QW.QDateEdit( self )
        self._end_date = QW.QDateEdit( self )
        self._auto_x_range = ClientGUICommon.BetterButton( self, 'refit x axis', self._AutoXRange )
        self._auto_x_range.setToolTip( ClientGUIFunctions.WrapToolTip( 'Recalculate an x axis range based on the current data that is in view.' ) )
        
        self._show_current.setChecked( True )
        self._show_inbox.setChecked( True )
        self._show_archive.setChecked( True )
        self._show_deleted.setChecked( True )
        
        button_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( button_hbox, self._show_current, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( button_hbox, self._show_inbox, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( button_hbox, self._show_archive, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( button_hbox, self._show_deleted, CC.FLAGS_CENTER_PERPENDICULAR )
        
        start_end_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( start_end_hbox, self._start_date, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( start_end_hbox, self._end_date, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( start_end_hbox, self._auto_x_range, CC.FLAGS_CENTER )
        
        file_history_vbox = QP.VBoxLayout()
        
        QP.AddToLayout( file_history_vbox, button_hbox, CC.FLAGS_CENTER )
        QP.AddToLayout( file_history_vbox, self._file_history_chart, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( file_history_vbox, start_end_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._file_history_chart_panel.setLayout( file_history_vbox )
        
        rightmost_vbox = QP.VBoxLayout()
        
        QP.AddToLayout( rightmost_vbox, self._status_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( rightmost_vbox, self._file_history_chart_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        rightmost_vbox.addStretch( 0 )
        
        self._rightmost_panel.setLayout( rightmost_vbox )
        
        #
        
        self._hbox = QP.HBoxLayout()
        
        QP.AddToLayout( self._hbox, self._search_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( self._hbox, self._rightmost_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( self._hbox )
        
        self._tag_autocomplete.searchChanged.connect( self._RefreshSearch )
        
        self._RefreshSearch()
        
        self._show_current.clicked.connect( self._file_history_chart.FlipAllVisible )
        self._show_inbox.clicked.connect( self._file_history_chart.FlipInboxVisible )
        self._show_archive.clicked.connect( self._file_history_chart.FlipArchiveVisible )
        self._show_deleted.clicked.connect( self._file_history_chart.FlipDeletedVisible )
        
        self._start_date.dateChanged.connect( self._UpdateXRange )
        self._end_date.dateChanged.connect( self._UpdateXRange )
        
    
    def _AutoXRange( self ):
        
        self._file_history_chart.AutoSetXRange()
        
        self._start_date.blockSignals( True )
        self._end_date.blockSignals( True )
        
        self._start_date.setDate( self._file_history_chart.GetStartDate() )
        self._end_date.setDate( self._file_history_chart.GetEndDate() )
        
        self._start_date.blockSignals( False )
        self._end_date.blockSignals( False )
        
    
    def _CancelCurrentSearch( self ):
        
        self._job_status.Cancel()
        
        self._cancel_button.setEnabled( False )
        
    
    def _RefreshSearch( self ):
        
        def work_callable():
            
            try:
                
                file_history = CG.client_controller.Read( 'file_history', num_steps, file_search_context = file_search_context, job_status = job_status )
                
            except HydrusExceptions.DBException as e:
                
                if isinstance( e.db_e, HydrusExceptions.TooComplicatedM8 ):
                    
                    return -1
                    
                
                raise
                
            
            return file_history
            
        
        def publish_callable( file_history ):
            
            try:
                
                if file_history == -1:
                    
                    self._status_st.setText( 'Sorry, this domain is too complicated to calculate for now, try something simpler!' )
                    
                    return
                    
                elif job_status.IsCancelled():
                    
                    self._status_st.setText( 'Cancelled!' )
                    
                    return
                    
                
                self._file_history_chart.SetFileHistory( file_history )
                
                if not self._have_initialised_x_axis:
                    
                    self._have_initialised_x_axis = True
                    
                    self._AutoXRange()
                    
                else:
                    
                    self._UpdateXRange()
                    
                
                self._status_st.setVisible( False )
                
                self._file_history_chart_panel.setVisible( True )
                
            finally:
                
                self._cancel_button.setEnabled( False )
                self._refresh_button.setEnabled( True )
                
            
        
        if not self._tag_autocomplete.IsSynchronised():
            
            self._refresh_button.setEnabled( False )
            
            return
            
        
        file_search_context = self._tag_autocomplete.GetFileSearchContext()
        
        num_steps = 7680
        
        self._cancel_button.setEnabled( True )
        self._refresh_button.setEnabled( False )
        
        self._status_st.setText( 'loading' + HC.UNICODE_ELLIPSIS )
        self._status_st.setVisible( True )
        
        self._file_history_chart_panel.setVisible( False )
        
        self._job_status.Cancel()
        
        job_status = ClientThreading.JobStatus()
        
        self._job_status = job_status
        
        self._update_job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
        
        self._update_job.start()
        
    
    def _UpdateXRange( self ):
        
        self._file_history_chart.SetXRange( self._start_date.dateTime(), self._end_date.dateTime() )
        
    
class ReviewFileMaintenance( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent, stats ):
        
        super().__init__( parent )
        
        self._hash_ids = None
        self._job_types_to_due_counts = {}
        self._job_types_to_not_due_counts = {}
        
        self._notebook = ClientGUICommon.BetterNotebook( self )
        
        #
        
        self._current_work_panel = QW.QWidget( self._notebook )
        
        jobs_listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self._current_work_panel )
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_FILE_MAINTENANCE_JOBS.ID, self._ConvertJobTypeToDisplayTuple, self._ConvertJobTypeToSortTuple )
        
        self._jobs_listctrl = ClientGUIListCtrl.BetterListCtrlTreeView( jobs_listctrl_panel, 8, model )
        
        jobs_listctrl_panel.SetListCtrl( self._jobs_listctrl )
        
        jobs_listctrl_panel.AddButton( 'clear', self._DeleteWork, enabled_only_on_selection = True )
        jobs_listctrl_panel.AddButton( 'do work', self._DoWork, enabled_check_func = self._WorkToDoOnSelection )
        jobs_listctrl_panel.AddButton( 'do all work', self._DoAllWork, enabled_check_func = self._WorkToDo )
        jobs_listctrl_panel.AddButton( 'refresh', self._RefreshWorkDue )
        
        vbox = QP.VBoxLayout()
        
        text = 'Here is the outstanding file maintenance work. This will be slowly completed in the background, usually a file every few seconds (you can edit this under _options->maintenance and processing_). Although you can rush work if you want to, it is best to generally leave it alone.'
        
        st = ClientGUICommon.BetterStaticText( self._current_work_panel, text )
        st.setWordWrap( True )
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, jobs_listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self._current_work_panel.setLayout( vbox )
        
        #
        
        self._new_work_panel = QW.QWidget( self._notebook )
        
        #
        
        self._search_panel = ClientGUICommon.StaticBox( self._new_work_panel, 'select files by search' )
        
        page_key = HydrusData.GenerateKey()
        
        default_location_context = CG.client_controller.new_options.GetDefaultLocalLocationContext()
        
        file_search_context = ClientSearchFileSearchContext.FileSearchContext( location_context = default_location_context )
        
        self._tag_autocomplete = ClientGUIACDropdown.AutoCompleteDropdownTagsRead( self._search_panel, page_key, file_search_context, allow_all_known_files = False, force_system_everything = True )
        
        self._run_search_st = ClientGUICommon.BetterStaticText( self._search_panel, label = 'no results yet' )
        
        self._run_search = ClientGUICommon.BetterButton( self._search_panel, 'run this search', self._RunSearch )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._run_search_st, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, self._run_search, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self._search_panel.Add( self._tag_autocomplete, CC.FLAGS_EXPAND_BOTH_WAYS )
        self._search_panel.Add( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        self._button_panel = ClientGUICommon.StaticBox( self._new_work_panel, 'easy select' )
        
        self._select_all_media_files = ClientGUICommon.BetterButton( self._button_panel, 'all media files', self._SelectAllMediaFiles )
        self._select_repo_files = ClientGUICommon.BetterButton( self._button_panel, 'all repository update files', self._SelectRepoUpdateFiles )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._select_all_media_files, CC.FLAGS_CENTER )
        QP.AddToLayout( hbox, self._select_repo_files, CC.FLAGS_CENTER )
        
        self._button_panel.Add( hbox, CC.FLAGS_ON_RIGHT )
        
        #
        
        self._action_panel = ClientGUICommon.StaticBox( self._new_work_panel, 'add job' )
        
        self._selected_files_st = ClientGUICommon.BetterStaticText( self._action_panel, label = 'no files selected yet' )
        
        self._action_selector = ClientGUICommon.BetterChoice( self._action_panel )
        
        for job_type in ClientFilesMaintenance.ALL_REGEN_JOBS_IN_HUMAN_ORDER:
            
            self._action_selector.addItem( ClientFilesMaintenance.regen_file_enum_to_str_lookup[ job_type ], job_type )
            
        
        self._description_button = ClientGUICommon.BetterButton( self._action_panel, 'see description', self._SeeDescription )
        
        self._add_new_job = ClientGUICommon.BetterButton( self._action_panel, 'add job', self._AddJob )
        
        self._add_new_job.setEnabled( False )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._selected_files_st, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, self._action_selector, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._description_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._add_new_job, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self._action_panel.Add( hbox, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        vbox = QP.VBoxLayout()
        
        label = 'Here you can queue up new file maintenance work. You determine the files to run a job on by loading a normal file search.'
        label += '\n' * 2
        label += 'Once your search is set, you need to hit \'run this search\' to actually load up the files. Then select the job type to apply and click \'add job\'. Click \'see description\' for more information on the job.'
        label += '\n' * 2
        label += 'Be cautious--do not queue up an integrity scan for all your files on a whim! If you don\'t know what a job does, do not add it!'
        
        st = ClientGUICommon.BetterStaticText( self._new_work_panel, label )
        st.setWordWrap( True )
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._search_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, self._button_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._action_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._new_work_panel.setLayout( vbox )
        
        #
        
        self._notebook.addTab( self._current_work_panel, 'scheduled work' )
        self._notebook.addTab( self._new_work_panel, 'add new work' )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
        self._RefreshWorkDue()
        
        CG.client_controller.sub( self, '_RefreshWorkDue', 'notify_files_maintenance_done' )
        
    
    def _AddJob( self ):
        
        hash_ids = self._hash_ids
        job_type = self._action_selector.GetValue()
        
        if len( hash_ids ) > 1000:
            
            message = 'Are you sure you want to schedule "{}" on {} files?'.format( ClientFilesMaintenance.regen_file_enum_to_str_lookup[ job_type ], HydrusNumbers.ToHumanInt( len( hash_ids ) ) )
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message, yes_label = 'do it', no_label = 'forget it' )
            
            if result != QW.QDialog.DialogCode.Accepted:
                
                return
                
            
        
        self._add_new_job.setEnabled( False )
        
        def work_callable():
            
            CG.client_controller.files_maintenance_manager.ScheduleJobHashIds( hash_ids, job_type )
            
            return True
            
        
        def publish_callable( result ):
            
            ClientGUIDialogsMessage.ShowInformation( self, 'Jobs added!' )
            
            self._add_new_job.setEnabled( True )
            
            self._RefreshWorkDue()
            
        
        job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
        
        job.start()
        
    
    def _ConvertJobTypeToDisplayTuple( self, job_type ):
        
        pretty_job_type = ClientFilesMaintenance.regen_file_enum_to_str_lookup[ job_type ]
        
        if job_type in self._job_types_to_due_counts:
            
            num_to_do = self._job_types_to_due_counts[ job_type ]
            
        else:
            
            num_to_do = 0
            
        
        pretty_num_to_do = HydrusNumbers.ToHumanInt( num_to_do )
        
        not_due_num_to_do = self._job_types_to_not_due_counts[ job_type ]
        
        if not_due_num_to_do > 0:
            
            pretty_num_to_do = '{} ({} is not yet due)'.format( pretty_num_to_do, HydrusNumbers.ToHumanInt( not_due_num_to_do ) )
            
        
        display_tuple = ( pretty_job_type, pretty_num_to_do )
        
        return display_tuple
        
    
    def _ConvertJobTypeToSortTuple( self, job_type ):
        
        pretty_job_type = ClientFilesMaintenance.regen_file_enum_to_str_lookup[ job_type ]
        sort_job_type = pretty_job_type
        
        if job_type in self._job_types_to_due_counts:
            
            num_to_do = self._job_types_to_due_counts[ job_type ]
            
        else:
            
            num_to_do = 0
            
        
        sort_tuple = ( sort_job_type, num_to_do )
        
        return sort_tuple
        
    
    def _DeleteWork( self ):
        
        message = 'Clear all the selected scheduled work?'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result != QW.QDialog.DialogCode.Accepted:
            
            return
            
        
        job_types = self._jobs_listctrl.GetData( only_selected = True )
        
        def work_callable():
            
            for job_type in job_types:
                
                CG.client_controller.files_maintenance_manager.CancelJobs( job_type )
                
            
            return True
            
        
        def publish_callable( result ):
            
            self._RefreshWorkDue()
            
        
        job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
        
        job.start()
        
    
    def _DoAllWork( self ):
        
        CG.client_controller.CallToThread( CG.client_controller.files_maintenance_manager.ForceMaintenance )
        
    
    def _DoWork( self ):
        
        job_types = self._jobs_listctrl.GetData( only_selected = True )
        
        if len( job_types ) == 0:
            
            return
            
        
        CG.client_controller.CallToThread( CG.client_controller.files_maintenance_manager.ForceMaintenance, mandated_job_types = job_types )
        
    
    def _RefreshWorkDue( self ):
        
        def work_callable():
            
            job_types_to_counts = CG.client_controller.Read( 'file_maintenance_get_job_counts' )
            
            return job_types_to_counts
            
        
        def publish_callable( job_types_to_counts ):
            
            job_types = set()
            self._job_types_to_due_counts = collections.Counter()
            self._job_types_to_not_due_counts = collections.Counter()
            
            for ( job_type, ( due_count, not_due_count ) ) in job_types_to_counts.items():
                
                job_types.add( job_type )
                self._job_types_to_due_counts[ job_type ] = due_count
                self._job_types_to_not_due_counts[ job_type ] = not_due_count
                
            
            self._jobs_listctrl.SetData( job_types )
            
        
        job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
        
        job.start()
        
    
    def _RunSearch( self ):
        
        self._run_search_st.setText( 'loading' + HC.UNICODE_ELLIPSIS )
        
        self._run_search.setEnabled( False )
        
        file_search_context = self._tag_autocomplete.GetFileSearchContext()
        
        def work_callable():
            
            query_hash_ids = CG.client_controller.Read( 'file_query_ids', file_search_context, apply_implicit_limit = False )
            
            return query_hash_ids
            
        
        def publish_callable( hash_ids ):
            
            self._run_search_st.setText( '{} files found'.format( HydrusNumbers.ToHumanInt( len( hash_ids ) ) ) )
            
            self._run_search.setEnabled( True )
            
            self._SetHashIds( hash_ids )
            
        
        job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
        
        job.start()
        
    
    def _SeeDescription( self ):
        
        job_type = self._action_selector.GetValue()
        
        message = ClientFilesMaintenance.regen_file_enum_to_description_lookup[ job_type ]
        message += '\n' * 2
        message += 'This job has weight {}, where a normalised unit of file work has value {}.'.format( HydrusNumbers.ToHumanInt( ClientFilesMaintenance.regen_file_enum_to_job_weight_lookup[ job_type ] ), HydrusNumbers.ToHumanInt( ClientFilesMaintenance.NORMALISED_BIG_JOB_WEIGHT ) )
        
        ClientGUIDialogsMessage.ShowInformation( self, message )
        
    
    def _SelectAllMediaFiles( self ):
        
        self._select_all_media_files.setEnabled( False )
        
        location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY )
        
        file_search_context = ClientSearchFileSearchContext.FileSearchContext( location_context = location_context )
        
        def work_callable():
            
            query_hash_ids = CG.client_controller.Read( 'file_query_ids', file_search_context, apply_implicit_limit = False )
            
            return query_hash_ids
            
        
        def publish_callable( hash_ids ):
            
            self._select_all_media_files.setEnabled( True )
            
            self._SetHashIds( hash_ids )
            
        
        job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
        
        job.start()
        
    
    def _SelectRepoUpdateFiles( self ):
        
        self._select_repo_files.setEnabled( False )
        
        location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_UPDATE_SERVICE_KEY )
        
        file_search_context = ClientSearchFileSearchContext.FileSearchContext( location_context = location_context )
        
        def work_callable():
            
            query_hash_ids = CG.client_controller.Read( 'file_query_ids', file_search_context, apply_implicit_limit = False )
            
            return query_hash_ids
            
        
        def publish_callable( hash_ids ):
            
            self._select_repo_files.setEnabled( True )
            
            self._SetHashIds( hash_ids )
            
        
        job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
        
        job.start()
        
    
    def _SetHashIds( self, hash_ids ):
        
        if hash_ids is None:
            
            hash_ids = set()
            
        
        self._hash_ids = hash_ids
        
        self._selected_files_st.setText( '{} files selected'.format(HydrusNumbers.ToHumanInt(len(hash_ids))) )
        
        if len( hash_ids ) == 0:
            
            self._add_new_job.setEnabled( False )
            
        else:
            
            self._add_new_job.setEnabled( True )
            
        
    
    def _WorkToDo( self ):
        
        return sum( self._job_types_to_due_counts.values() ) > 0
        
    
    def _WorkToDoOnSelection( self ):
        
        job_types = self._jobs_listctrl.GetData( only_selected = True )
        
        for job_type in job_types:
            
            if self._job_types_to_due_counts[ job_type ] > 0:
                
                return True
                
            
        
        return False
        
    

class ReviewHowBonedAmI( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent ):
        
        super().__init__( parent )
        
        self._update_job = None
        self._job_status = ClientThreading.JobStatus()
        
        vbox = QP.VBoxLayout()
        
        self._mr_bones_text = ClientGUICommon.BetterStaticText( self )
        
        boned_path = HydrusStaticDir.GetStaticPath( 'boned.jpg' )
        
        boned_qt_pixmap = ClientRendering.GenerateHydrusBitmap( boned_path, HC.IMAGE_JPEG ).GetQtPixmap()
        
        self._mr_bones_image = QW.QLabel( self, pixmap = boned_qt_pixmap )
        
        QP.AddToLayout( vbox, self._mr_bones_image, CC.FLAGS_CENTER )
        QP.AddToLayout( vbox, self._mr_bones_text, CC.FLAGS_CENTER )
        
        self._notebook = ClientGUICommon.BetterNotebook( self )
        
        #
        
        self._search_panel = QW.QWidget( self )
        
        self._files_panel = QW.QWidget( self._notebook )
        self._views_panel = QW.QWidget( self._notebook )
        self._duplicates_panel = QW.QWidget( self._notebook )
        
        self._notebook.addTab( self._files_panel, 'files' )
        self._notebook.addTab( self._views_panel, 'views' )
        self._notebook.addTab( self._duplicates_panel, 'duplicates' )
        
        #
        
        self._files_content_panel = QW.QWidget( self._files_panel )
        
        self._files_content_vbox = QP.VBoxLayout( margin = 0, spacing = 0 )
        
        QP.AddToLayout( self._files_content_vbox, self._files_content_panel, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self._files_panel.setLayout( self._files_content_vbox )
        
        #
        
        panel_vbox = QP.VBoxLayout()
        
        self._media_views_st = ClientGUICommon.BetterStaticText( self._views_panel )
        self._media_views_st.setAlignment( QC.Qt.AlignmentFlag.AlignCenter )
        
        self._preview_views_st = ClientGUICommon.BetterStaticText( self._views_panel )
        self._preview_views_st.setAlignment( QC.Qt.AlignmentFlag.AlignCenter )
        
        QP.AddToLayout( panel_vbox, self._media_views_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( panel_vbox, self._preview_views_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        panel_vbox.addStretch( 0 )
        
        self._views_panel.setLayout( panel_vbox )
        
        #
        
        panel_vbox = QP.VBoxLayout()
        
        self._potentials_st = ClientGUICommon.BetterStaticText( self._duplicates_panel )
        self._potentials_st.setAlignment( QC.Qt.AlignmentFlag.AlignCenter )
        self._duplicates_st = ClientGUICommon.BetterStaticText( self._duplicates_panel )
        self._duplicates_st.setAlignment( QC.Qt.AlignmentFlag.AlignCenter )
        self._alternates_st = ClientGUICommon.BetterStaticText( self._duplicates_panel )
        self._alternates_st.setAlignment( QC.Qt.AlignmentFlag.AlignCenter )
        
        st = ClientGUICommon.BetterStaticText( self._duplicates_panel, label = 'Since many duplicate files get deleted, this will not give nice "all-time" numbers unless you change the file domain to "all files ever imported or deleted".' )
        st.setWordWrap( True )
        st.setAlignment( QC.Qt.AlignmentFlag.AlignCenter )
        
        QP.AddToLayout( panel_vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( panel_vbox, self._potentials_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( panel_vbox, self._duplicates_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( panel_vbox, self._alternates_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        panel_vbox.addStretch( 0 )
        
        self._duplicates_panel.setLayout( panel_vbox )
        
        #
        
        panel_vbox = QP.VBoxLayout()
        
        file_search_context = ClientSearchFileSearchContext.FileSearchContext(
            location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY )
        )
        
        page_key = b'mr bones placeholder'
        
        self._tag_autocomplete = ClientGUIACDropdown.AutoCompleteDropdownTagsRead(
            self._search_panel,
            page_key,
            file_search_context,
            allow_all_known_files = False,
            force_system_everything = True,
            fixed_results_list_height = 8
        )
        
        self._loading_text = ClientGUICommon.BetterStaticText( self._search_panel )
        self._loading_text.setAlignment( QC.Qt.AlignmentFlag.AlignVCenter | QC.Qt.AlignmentFlag.AlignRight )
        
        self._cancel_button = ClientGUICommon.IconButton( self._search_panel, CC.global_icons().stop, self._CancelCurrentSearch )
        self._refresh_button = ClientGUICommon.IconButton( self._search_panel, CC.global_icons().refresh, self._RefreshSearch )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._loading_text, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, self._cancel_button, CC.FLAGS_CENTER )
        QP.AddToLayout( hbox, self._refresh_button, CC.FLAGS_CENTER )
        
        QP.AddToLayout( panel_vbox, self._tag_autocomplete, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( panel_vbox, hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self._search_panel.setLayout( panel_vbox )
        
        #
        
        QP.AddToLayout( vbox, self._notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        big_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( big_hbox, self._search_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( big_hbox, vbox, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( big_hbox )
        
        self._tag_autocomplete.searchChanged.connect( self._RefreshSearch )
        
        self._RefreshSearch()
        
    
    def _CancelCurrentSearch( self ):
        
        self._job_status.Cancel()
        
        self._cancel_button.setEnabled( False )
        
    
    def _RefreshSearch( self ):
        
        def work_callable():
            
            boned_stats = CG.client_controller.Read( 'boned_stats', file_search_context = file_search_context, job_status = job_status )
            
            return boned_stats
            
        
        def publish_callable( boned_stats ):
            
            if job_status.IsCancelled():
                
                self._SetCancelled()
                
            else:
                
                self._SetBones( boned_stats )
                
                self._loading_text.setText( '' )
                
            
            self._cancel_button.setEnabled( False )
            self._refresh_button.setEnabled( True )
            
        
        if not self._tag_autocomplete.IsSynchronised():
            
            self._refresh_button.setEnabled( False )
            
            return
            
        
        file_search_context = self._tag_autocomplete.GetFileSearchContext()
        
        self._SetToLoading()
        
        self._job_status.Cancel()
        
        job_status = ClientThreading.JobStatus()
        
        self._job_status = job_status
        
        self._update_job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
        
        self._update_job.start()
        
    
    def _SetBones( self, boned_stats: dict ):
        
        self._SetTheMasterOfCeremonies( boned_stats )
        self._SetFilesPanel( boned_stats )
        self._SetViewsPanel( boned_stats )
        self._SetDuplicatesPanel( boned_stats )
        
    
    def _SetCancelled( self ):
        
        self._loading_text.setText( 'cancelled!' )
        
    
    def _SetDuplicatesPanel( self, boned_stats: dict ):
        
        total_alternate_files = boned_stats[ 'total_alternate_files' ]
        total_alternate_groups = boned_stats[ 'total_alternate_groups' ]
        total_duplicate_files = boned_stats[ 'total_duplicate_files' ]
        #total_potential_pairs = boned_stats[ 'total_potential_pairs' ]
        
        #potentials_label = f'Total duplicate potential pairs: {HydrusNumbers.ToHumanInt( total_potential_pairs )}'
        potentials_label = f'Total potential duplicate pairs: disabled for now'
        duplicates_label = f'Total files in duplicate groups: {HydrusNumbers.ToHumanInt( total_duplicate_files )}'
        alternates_label = f'Total files in alternate groups: {HydrusNumbers.ToHumanInt( total_alternate_files )} ({HydrusNumbers.ToHumanInt( total_alternate_groups )} groups)'
        
        self._potentials_st.setText( potentials_label )
        self._duplicates_st.setText( duplicates_label )
        self._alternates_st.setText( alternates_label )
        
    
    def _SetFilesPanel( self, boned_stats: dict ):
        
        self._files_content_vbox.removeWidget( self._files_content_panel )
        
        self._files_content_panel.deleteLater()
        
        self._files_content_panel = QW.QWidget( self._files_panel )
        
        num_inbox = boned_stats[ 'num_inbox' ]
        num_archive = boned_stats[ 'num_archive' ]
        size_inbox = boned_stats[ 'size_inbox' ]
        size_archive = boned_stats[ 'size_archive' ]
        
        num_total = num_archive + num_inbox
        size_total = size_archive + size_inbox
        
        panel_vbox = QP.VBoxLayout()
        
        if num_total == 0 or size_total == 0:
            
            divide_by_zero_m8 = ClientGUICommon.BetterStaticText( self._files_content_panel, label = 'No files!' )
            
            QP.AddToLayout( panel_vbox, divide_by_zero_m8, CC.FLAGS_CENTER )
            
        else:
            
            current_average_filesize = size_total // num_total
            
            inbox_num_percent = num_inbox / num_total
            inbox_size_percent = size_inbox / size_total
            
            if num_inbox > 0:
                
                inbox_average_filesize = size_inbox // num_inbox
                
            else:
                
                inbox_average_filesize = 0
                
            
            archive_num_percent = num_archive / num_total
            archive_size_percent = size_archive / size_total
            
            if num_archive > 0:
                
                archive_average_filesize = size_archive // num_archive
                
            else:
                
                archive_average_filesize = 0
                
            
            if 'num_deleted' in boned_stats:
                
                num_deleted = boned_stats[ 'num_deleted' ]
                size_deleted = boned_stats[ 'size_deleted' ]
                
                num_supertotal = num_total + num_deleted
                size_supertotal = size_total + size_deleted
                
                supertotal_average_filesize = size_supertotal // num_supertotal
                
                current_num_percent = num_total / num_supertotal
                current_size_percent = size_total / size_supertotal
                
                deleted_num_percent = num_deleted / num_supertotal
                deleted_size_percent = size_deleted / size_supertotal
                
                if num_deleted > 0:
                    
                    deleted_average_filesize = size_deleted // num_deleted
                    
                else:
                    
                    deleted_average_filesize = 0
                    
                
                # spacing=0 to make the weird unicode characters join up neater
                text_table_layout = QP.GridLayout( cols = 6, spacing = 0 )
                
                text_table_layout.setHorizontalSpacing( ClientGUIFunctions.ConvertTextToPixelWidth( self, 2 ) )
                
                text_table_layout.setColumnStretch( 0, 1 )
                
                #
                
                QP.AddToLayout( text_table_layout, QW.QWidget( self._files_content_panel ), CC.FLAGS_ON_LEFT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = 'Files' ), CC.FLAGS_CENTER )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = '%' ), CC.FLAGS_CENTER )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = 'Size' ), CC.FLAGS_CENTER )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = '%' ), CC.FLAGS_CENTER )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = 'Average' ), CC.FLAGS_CENTER )
                
                #
                
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = 'Total Ever Imported:' ), CC.FLAGS_ON_LEFT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = HydrusNumbers.ToHumanInt( num_supertotal ) ), CC.FLAGS_ON_RIGHT )
                QP.AddToLayout( text_table_layout, QW.QWidget( self._files_content_panel ), CC.FLAGS_ON_LEFT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = HydrusData.ToHumanBytes( size_supertotal ) ), CC.FLAGS_ON_RIGHT )
                QP.AddToLayout( text_table_layout, QW.QWidget( self._files_content_panel ), CC.FLAGS_ON_LEFT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = HydrusData.ToHumanBytes( supertotal_average_filesize ) ), CC.FLAGS_ON_RIGHT )
                
                #
                
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = '' ), CC.FLAGS_ON_LEFT )
                QP.AddToLayout( text_table_layout, QW.QWidget( self._files_content_panel ), CC.FLAGS_ON_LEFT )
                QP.AddToLayout( text_table_layout, QW.QWidget( self._files_content_panel ), CC.FLAGS_ON_LEFT )
                QP.AddToLayout( text_table_layout, QW.QWidget( self._files_content_panel ), CC.FLAGS_ON_LEFT )
                QP.AddToLayout( text_table_layout, QW.QWidget( self._files_content_panel ), CC.FLAGS_ON_LEFT )
                QP.AddToLayout( text_table_layout, QW.QWidget( self._files_content_panel ), CC.FLAGS_ON_LEFT )
                
                #
                
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = 'Current:' ), CC.FLAGS_ON_LEFT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = HydrusNumbers.ToHumanInt( num_total ) ), CC.FLAGS_ON_RIGHT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = ClientData.ConvertZoomToPercentage( current_num_percent ) ), CC.FLAGS_ON_RIGHT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = HydrusData.ToHumanBytes( size_total ) ), CC.FLAGS_ON_RIGHT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = ClientData.ConvertZoomToPercentage( current_size_percent ) ), CC.FLAGS_ON_RIGHT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = HydrusData.ToHumanBytes( current_average_filesize ) ), CC.FLAGS_ON_RIGHT )
                
                #
                
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = 'Deleted:' ), CC.FLAGS_ON_LEFT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = HydrusNumbers.ToHumanInt( num_deleted ) ), CC.FLAGS_ON_RIGHT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = ClientData.ConvertZoomToPercentage( deleted_num_percent ) ), CC.FLAGS_ON_RIGHT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = HydrusData.ToHumanBytes( size_deleted ) ), CC.FLAGS_ON_RIGHT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = ClientData.ConvertZoomToPercentage( deleted_size_percent ) ), CC.FLAGS_ON_RIGHT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = HydrusData.ToHumanBytes( deleted_average_filesize ) ), CC.FLAGS_ON_RIGHT )
                
                #
                
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = '' ), CC.FLAGS_ON_LEFT )
                QP.AddToLayout( text_table_layout, QW.QWidget( self._files_content_panel ), CC.FLAGS_ON_LEFT )
                QP.AddToLayout( text_table_layout, QW.QWidget( self._files_content_panel ), CC.FLAGS_ON_LEFT )
                QP.AddToLayout( text_table_layout, QW.QWidget( self._files_content_panel ), CC.FLAGS_ON_LEFT )
                QP.AddToLayout( text_table_layout, QW.QWidget( self._files_content_panel ), CC.FLAGS_ON_LEFT )
                QP.AddToLayout( text_table_layout, QW.QWidget( self._files_content_panel ), CC.FLAGS_ON_LEFT )
                
                #
                
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = 'Inbox:' ), CC.FLAGS_ON_LEFT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = HydrusNumbers.ToHumanInt( num_inbox ) ), CC.FLAGS_ON_RIGHT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = ClientData.ConvertZoomToPercentage( inbox_num_percent ) ), CC.FLAGS_ON_RIGHT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = HydrusData.ToHumanBytes( size_inbox ) ), CC.FLAGS_ON_RIGHT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = ClientData.ConvertZoomToPercentage( inbox_size_percent ) ), CC.FLAGS_ON_RIGHT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = HydrusData.ToHumanBytes( inbox_average_filesize ) ), CC.FLAGS_ON_RIGHT )
                
                #
                
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = 'Archive:' ), CC.FLAGS_ON_LEFT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = HydrusNumbers.ToHumanInt( num_archive ) ), CC.FLAGS_ON_RIGHT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = ClientData.ConvertZoomToPercentage( archive_num_percent ) ), CC.FLAGS_ON_RIGHT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = HydrusData.ToHumanBytes( size_archive ) ), CC.FLAGS_ON_RIGHT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = ClientData.ConvertZoomToPercentage( archive_size_percent ) ), CC.FLAGS_ON_RIGHT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = HydrusData.ToHumanBytes( archive_average_filesize ) ), CC.FLAGS_ON_RIGHT )
                
            else:
                
                panel_vbox = QP.VBoxLayout()
                
                # spacing=0 to make the weird unicode characters join up neater
                text_table_layout = QP.GridLayout( cols = 6, spacing = 0 )
                
                text_table_layout.setHorizontalSpacing( ClientGUIFunctions.ConvertTextToPixelWidth( self, 2 ) )
                
                text_table_layout.setColumnStretch( 0, 1 )
                
                #
                
                QP.AddToLayout( text_table_layout, QW.QWidget( self._files_content_panel ), CC.FLAGS_ON_LEFT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = 'Files' ), CC.FLAGS_CENTER )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = '%' ), CC.FLAGS_CENTER )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = 'Size' ), CC.FLAGS_CENTER )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = '%' ), CC.FLAGS_CENTER )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = 'Average' ), CC.FLAGS_CENTER )
                
                #
                
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = 'Current:' ), CC.FLAGS_ON_LEFT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = HydrusNumbers.ToHumanInt( num_total ) ), CC.FLAGS_ON_RIGHT )
                QP.AddToLayout( text_table_layout, QW.QWidget( self._files_content_panel ), CC.FLAGS_ON_LEFT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = HydrusData.ToHumanBytes( size_total ) ), CC.FLAGS_ON_RIGHT )
                QP.AddToLayout( text_table_layout, QW.QWidget( self._files_content_panel ), CC.FLAGS_ON_LEFT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = HydrusData.ToHumanBytes( current_average_filesize ) ), CC.FLAGS_ON_RIGHT )
                
                #
                
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = '' ), CC.FLAGS_ON_LEFT )
                QP.AddToLayout( text_table_layout, QW.QWidget( self._files_content_panel ), CC.FLAGS_ON_LEFT )
                QP.AddToLayout( text_table_layout, QW.QWidget( self._files_content_panel ), CC.FLAGS_ON_LEFT )
                QP.AddToLayout( text_table_layout, QW.QWidget( self._files_content_panel ), CC.FLAGS_ON_LEFT )
                QP.AddToLayout( text_table_layout, QW.QWidget( self._files_content_panel ), CC.FLAGS_ON_LEFT )
                QP.AddToLayout( text_table_layout, QW.QWidget( self._files_content_panel ), CC.FLAGS_ON_LEFT )
                
                #
                
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = 'Inbox:' ), CC.FLAGS_ON_LEFT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = HydrusNumbers.ToHumanInt( num_inbox ) ), CC.FLAGS_ON_RIGHT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = ClientData.ConvertZoomToPercentage( inbox_num_percent ) ), CC.FLAGS_ON_RIGHT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = HydrusData.ToHumanBytes( size_inbox ) ), CC.FLAGS_ON_RIGHT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = ClientData.ConvertZoomToPercentage( inbox_size_percent ) ), CC.FLAGS_ON_RIGHT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = HydrusData.ToHumanBytes( inbox_average_filesize ) ), CC.FLAGS_ON_RIGHT )
                
                #
                
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = 'Archive:' ), CC.FLAGS_ON_LEFT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = HydrusNumbers.ToHumanInt( num_archive ) ), CC.FLAGS_ON_RIGHT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = ClientData.ConvertZoomToPercentage( archive_num_percent ) ), CC.FLAGS_ON_RIGHT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = HydrusData.ToHumanBytes( size_archive ) ), CC.FLAGS_ON_RIGHT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = ClientData.ConvertZoomToPercentage( archive_size_percent ) ), CC.FLAGS_ON_RIGHT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = HydrusData.ToHumanBytes( archive_average_filesize ) ), CC.FLAGS_ON_RIGHT )
                
            
            #
            
            QP.AddToLayout( panel_vbox, text_table_layout, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            if 'earliest_import_time' in boned_stats:
                
                panel_vbox.addSpacing( ClientGUIFunctions.ConvertTextToPixelWidth( self, 2 ) )
                
                eit_timestamp = boned_stats[ 'earliest_import_time' ]
                
                eit_label = 'Earliest file import: {} ({})'.format( HydrusTime.TimestampToPrettyTime( eit_timestamp ), HydrusTime.TimestampToPrettyTimeDelta( eit_timestamp ) )
                
                eit_st = ClientGUICommon.BetterStaticText( self._files_content_panel, label = eit_label )
                
                QP.AddToLayout( panel_vbox, eit_st, CC.FLAGS_CENTER )
                
            
        
        panel_vbox.addStretch( 0 )
        
        self._files_content_panel.setLayout( panel_vbox )
        
        QP.AddToLayout( self._files_content_vbox, self._files_content_panel, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
    
    def _SetTheMasterOfCeremonies( self, boned_stats: dict ):
        
        num_inbox = boned_stats[ 'num_inbox' ]
        num_archive = boned_stats[ 'num_archive' ]
        
        num_total = num_archive + num_inbox
        
        special_message = None
        
        num_deleted = boned_stats.get( 'num_deleted', 0 )
        
        current_fsc = self._tag_autocomplete.GetFileSearchContext()
        
        special_message_is_appropriate = len( current_fsc.GetPredicates() ) == 0 and current_fsc.GetLocationContext() == ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY )
        
        if special_message_is_appropriate:
            
            if num_total == 0 and num_deleted == 0:
                
                special_message = 'You have yet to board the ride.'
                
            elif num_total + num_deleted < 1000:
                
                special_message = 'I hope you enjoy my software. You might like to check out the downloaders! :^)'
                
            elif num_inbox <= num_archive / 99:
                
                special_message = 'CONGRATULATIONS. YOU APPEAR TO BE UNBONED--BUT REMAIN EVER VIGILANT'
                
            
        
        if special_message is None:
            
            self._mr_bones_text.setVisible( False )
            
            self._mr_bones_image.setVisible( True )
            
        else:
            
            self._mr_bones_image.setVisible( False )
            
            self._mr_bones_text.setVisible( True )
            self._mr_bones_text.setText( special_message )
            
        
    
    def _SetToLoading( self ):
        
        self._loading_text.setText( 'loading' + HC.UNICODE_ELLIPSIS )
        
        self._files_content_vbox.removeWidget( self._files_content_panel )
        
        self._files_content_panel.deleteLater()
        
        self._files_content_panel = QW.QWidget( self._files_panel )
        
        QP.AddToLayout( self._files_content_vbox, self._files_content_panel, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self._potentials_st.setText( '' )
        self._duplicates_st.setText( '' )
        self._alternates_st.setText( '' )
        
        self._media_views_st.setText( '' )
        self._preview_views_st.setText( '' )
        
        self._refresh_button.setEnabled( False )
        self._cancel_button.setEnabled( True )
        
    
    def _SetViewsPanel( self, boned_stats: dict ):
        
        total_viewtime = boned_stats[ 'total_viewtime' ]
        
        ( media_views, media_viewtime, preview_views, preview_viewtime ) = total_viewtime
        
        media_label = 'Total media views: ' + HydrusNumbers.ToHumanInt( media_views ) + ', totalling ' + HydrusTime.TimeDeltaToPrettyTimeDelta( media_viewtime )
        
        preview_label = 'Total preview views: ' + HydrusNumbers.ToHumanInt( preview_views ) + ', totalling ' + HydrusTime.TimeDeltaToPrettyTimeDelta( preview_viewtime )
        
        self._media_views_st.setText( media_label )
        self._preview_views_st.setText( preview_label )
        
    

class JobSchedulerPanel( QW.QWidget ):
    
    def __init__( self, parent: QW.QWidget, controller: "CG.ClientController.Controller", scheduler_name ):
        
        self._controller = controller
        self._scheduler_name = scheduler_name
        
        super().__init__( parent )
        
        self._list_ctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_JOB_SCHEDULER_REVIEW.ID, self._ConvertDataToDisplayTuple, self._ConvertDataToSortTuple )
        
        self._list_ctrl = ClientGUIListCtrl.BetterListCtrlTreeView( self._list_ctrl_panel, 20, model )
        
        self._list_ctrl_panel.SetListCtrl( self._list_ctrl )
        
        # maybe some buttons to control behaviour here for debug
        
        self._list_ctrl_panel.AddButton( 'refresh snapshot', self._RefreshSnapshot )
        
        #
        
        self._list_ctrl.Sort()
        
        self._RefreshSnapshot()
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._list_ctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.setLayout( vbox )
        
    
    def _ConvertDataToDisplayTuple( self, job: HydrusThreading.SchedulableJob ):
        
        job_type = job.PRETTY_CLASS_NAME
        job_call = job.GetPrettyJob()
        
        pretty_job_type = job_type
        pretty_job_call = job_call
        pretty_due = job.GetDueString()
        
        display_tuple = ( pretty_job_type, pretty_job_call, pretty_due )
        
        return display_tuple
        
    
    def _ConvertDataToSortTuple( self, job: HydrusThreading.SchedulableJob ):
        
        job_type = job.PRETTY_CLASS_NAME
        job_call = job.GetPrettyJob()
        due = job.GetNextWorkTime()
        
        sort_tuple = ( job_type, job_call, due )
        
        return sort_tuple
        
    
    def _RefreshSnapshot( self ):
        
        jobs = self._controller.GetJobSchedulerSnapshot( self._scheduler_name )
        
        self._list_ctrl.SetData( jobs )
        
    
class ThreadsPanel( QW.QWidget ):
    
    def __init__( self, parent: QW.QWidget, controller: "CG.ClientController.Controller" ):
        
        self._controller = controller
        
        super().__init__( parent )
        
        self._list_ctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_THREADS_REVIEW.ID, self._ConvertDataToDisplayTuple, self._ConvertDataToSortTuple )
        
        self._list_ctrl = ClientGUIListCtrl.BetterListCtrlTreeView( self._list_ctrl_panel, 20, model )
        
        self._list_ctrl_panel.SetListCtrl( self._list_ctrl )
        
        # maybe some buttons to control behaviour here for debug
        
        self._list_ctrl_panel.AddButton( 'refresh snapshot', self._RefreshSnapshot )
        
        #
        
        self._list_ctrl.Sort()
        
        self._RefreshSnapshot()
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._list_ctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.setLayout( vbox )
        
    
    def _ConvertDataToDisplayTuple( self, thread ):
        
        name = thread.GetName()
        thread_type = repr( type( thread ) )
        current_job = repr( thread.GetCurrentJobSummary() )
        
        pretty_name = name
        pretty_thread_type = thread_type
        pretty_current_job = current_job
        
        display_tuple = ( pretty_name, pretty_thread_type, pretty_current_job )
        
        return display_tuple
        
    
    def _ConvertDataToSortTuple( self, thread ):
        
        name = thread.GetName()
        thread_type = repr( type( thread ) )
        current_job = repr( thread.GetCurrentJobSummary() )
        
        sort_tuple = ( name, thread_type, current_job )
        
        return sort_tuple
        
    
    def _RefreshSnapshot( self ):
        
        threads = self._controller.GetThreadsSnapshot()
        
        self._list_ctrl.SetData( threads )
        
    

class ReviewDeferredDeleteTableData( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent: QW.QWidget, controller: "CG.ClientController.Controller" ):
        
        super().__init__( parent )
        
        self._controller = controller
        
        #
        
        info_message = '''When large database objects are no longer needed, they are not deleted immediately, but incrementally shrunk in the background over time. This is the queue of pending deferred delete database tables and approximate sizes.'''
        
        st = ClientGUICommon.BetterStaticText( self, label = info_message )
        
        st.setWordWrap( True )
        
        deferred_delete_listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        self._names_to_num_rows = {}
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_DEFERRED_DELETE_TABLE_DATA.ID, self._ConvertRowToDisplayTuple, self._ConvertRowToSortTuple )
        
        self._deferred_delete_listctrl = ClientGUIListCtrl.BetterListCtrlTreeView( deferred_delete_listctrl_panel, 24, model )
        
        deferred_delete_listctrl_panel.SetListCtrl( self._deferred_delete_listctrl )
        
        self._refresh_button = ClientGUICommon.IconButton( self, CC.global_icons().refresh, self._RefreshData )
        self._work_hard_button = ClientGUICommon.BetterButton( self,'work hard now', self._FlipWorkingHard )
        
        #
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, deferred_delete_listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._refresh_button, CC.FLAGS_CENTER )
        QP.AddToLayout( hbox, self._work_hard_button, CC.FLAGS_CENTER )
        
        QP.AddToLayout( vbox, hbox, CC.FLAGS_ON_RIGHT )
        
        self.widget().setLayout( vbox )
        
        self._updater = self._InitialiseUpdater()
        
        self._RefreshData()
        self._UpdateButtonLabel()
        
        self._controller.sub( self, 'NotifyRefresh', 'notify_deferred_delete_database_maintenance_work_complete' )
        self._controller.sub( self, 'NotifyStateChange', 'notify_deferred_delete_database_maintenance_state_change' )
        self._controller.sub( self, 'NotifyRefresh', 'notify_deferred_delete_database_maintenance_new_work' )
        
    
    def _ConvertRowToDisplayTuple( self, name ):
        
        num_rows = self._names_to_num_rows.get( name, None )
        
        pretty_name = name
        
        if num_rows is None:
            
            pretty_num_rows = 'unknown'
            
        else:
            
            sort_num_rows = num_rows
            pretty_num_rows = HydrusNumbers.ToHumanInt( sort_num_rows )
            
        
        display_tuple = ( pretty_name, pretty_num_rows )
        
        return display_tuple
        
    
    def _ConvertRowToSortTuple( self, name ):
        
        num_rows = self._names_to_num_rows.get( name, None )
        
        sort_name = name
        
        if num_rows is None:
            
            sort_num_rows = -1
            
        else:
            
            sort_num_rows = num_rows
            
        
        sort_tuple = ( sort_name, sort_num_rows )
        
        return sort_tuple
        
    
    def _FlipWorkingHard( self ):
        
        self._controller.database_maintenance_manager.FlipWorkingHard()
        
        self._UpdateButtonLabel()
        
    
    def _InitialiseUpdater( self ) -> ClientGUIAsync.AsyncQtUpdater:
        
        def loading_callable():
            
            self._refresh_button.setEnabled( False )
            
        
        def work_callable( args ):
            
            deferred_delete_data = self._controller.Read( 'deferred_delete_data' )
            
            return deferred_delete_data
            
        
        def publish_callable( deferred_delete_data ):
            
            self._names_to_num_rows = dict( deferred_delete_data )
            
            self._deferred_delete_listctrl.SetData( list( self._names_to_num_rows.keys() ) )
            
            self._deferred_delete_listctrl.Sort()
            
            self._refresh_button.setEnabled( True )
            
            self._UpdateButtonLabel()
            
        
        return ClientGUIAsync.AsyncQtUpdater( 'review deferred delete table data fetch', self, loading_callable, work_callable, publish_callable )
        
    
    def _RefreshData( self ):
        
        self._updater.update()
        
    
    def _UpdateButtonLabel( self ):
        
        if self._controller.database_maintenance_manager.IsWorkingHard():
            
            label = 'slow down'
            enabled = True
            
        else:
            
            work_to_do = len( self._deferred_delete_listctrl.GetData() ) > 0
            
            if work_to_do:
                
                label = 'work hard'
                
            else:
                
                label = 'all work done!'
                
            
            enabled = work_to_do
            
        
        self._work_hard_button.setText( label )
        
        self._work_hard_button.setEnabled( enabled )
        
    
    def NotifyRefresh( self ):
        
        self._RefreshData()
        
    
    def NotifyStateChange( self ):
        
        self._UpdateButtonLabel()
        
    

class ReviewThreads( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent, controller ):
        
        super().__init__( parent )
        
        self._notebook = ClientGUICommon.BetterNotebook( self )
        
        self._thread_panel = ThreadsPanel( self._notebook, controller )
        
        self._fast_scheduler_panel = JobSchedulerPanel( self._notebook, controller, 'fast' )
        
        self._slow_scheduler_panel = JobSchedulerPanel( self._notebook, controller, 'slow' )
        
        self._notebook.addTab( self._thread_panel, 'threads' )
        self._notebook.addTab( self._fast_scheduler_panel, 'fast scheduler' )
        self._notebook.addTab( self._slow_scheduler_panel, 'slow scheduler' )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    

class ReviewVacuumData( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent: QW.QWidget, controller: "CG.ClientController.Controller", vacuum_data ):
        
        super().__init__( parent )
        
        self._controller = controller
        self._vacuum_data = vacuum_data
        
        self._currently_vacuuming = False
        
        #
        
        info_message = '''Vacuuming is essentially an aggressive defrag of a database file. The entire database is copied contiguously to a new file, which then has tightly packed pages and no empty 'free' pages. Note that even a database that currently has no free pages can still _sometimes_ be packed more efficiently, saving up to 40% of space, but there is no easy way to determine this ahead of time (in general, if it has been five years, you might save some space), and the database will bloat back up in time as more work happens.

Because the new database is tightly packed, it will generally be smaller than the original file. This is currently the only way to truncate a hydrus database file.

Vacuuming is an expensive operation. It creates one (temporary) copy of the database file in your db dir. Hydrus cannot operate while it is going on, and it tends to run quite slow, about 10-50MB/s. The main benefit is in truncating the database files after you delete a lot of data, so I recommend you only do it after you delete the PTR or similar. If the db file is more than 2GB and has less than 5% free pages, it is probably not worth doing.'''
        
        st = ClientGUICommon.BetterStaticText( self, label = info_message )
        
        st.setWordWrap( True )
        
        vacuum_listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_VACUUM_DATA.ID, self._ConvertNameToDisplayTuple, self._ConvertNameToSortTuple )
        
        self._vacuum_listctrl = ClientGUIListCtrl.BetterListCtrlTreeView( vacuum_listctrl_panel, 6, model )
        
        vacuum_listctrl_panel.SetListCtrl( self._vacuum_listctrl )
        
        vacuum_listctrl_panel.AddButton( 'vacuum', self._Vacuum, enabled_check_func = self._CanVacuum )
        
        #
        
        self._vacuum_listctrl.SetData( list( self._vacuum_data.keys() ) )
        
        self._vacuum_listctrl.Sort()
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, vacuum_listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
    def _CanVacuumName( self, name ):
        
        from hydrus.core import HydrusDB
        
        try:
            
            vacuum_dict = self._vacuum_data[ name ]
            
            path = vacuum_dict[ 'path' ]
            page_size = vacuum_dict[ 'page_size' ]
            page_count = vacuum_dict[ 'page_count' ]
            freelist_count = vacuum_dict[ 'freelist_count' ]
            
            HydrusDB.CheckCanVacuumIntoData( path, page_size, page_count, freelist_count )
            
        except Exception as e:
            
            return ( False, str( e ) )
            
        
        return ( True, 'yes!' )
        
    
    def _CanVacuum( self ):
        
        names = self._vacuum_listctrl.GetData( only_selected = True )
        
        if len( names ) == 0:
            
            return False
            
        
        for name in names:
            
            ( result, info ) = self._CanVacuumName( name )
            
            if not result:
                
                return False
                
            
        
        return True
        
    
    def _ConvertNameToDisplayTuple( self, name ):
        
        vacuum_dict = self._vacuum_data[ name ]
        
        page_size = vacuum_dict[ 'page_size' ]
        
        pretty_name = name
        
        sort_total_size = page_size * vacuum_dict[ 'page_count' ]
        pretty_total_size = HydrusData.ToHumanBytes( sort_total_size )
        
        sort_free_size = page_size * vacuum_dict[ 'freelist_count' ]
        pretty_free_size = HydrusData.ToHumanBytes( sort_free_size )
        
        if sort_total_size > 0:
            
            pretty_free_size = '{} ({})'.format( pretty_free_size, HydrusNumbers.FloatToPercentage( sort_free_size / sort_total_size ) )
            
        
        sort_last_vacuumed_ms = vacuum_dict[ 'last_vacuumed_ms' ]
        
        if sort_last_vacuumed_ms == 0 or sort_last_vacuumed_ms is None:
            
            pretty_last_vacuumed_ms = 'never done'
            
        else:
            
            pretty_last_vacuumed_ms = HydrusTime.TimestampToPrettyTimeDelta( HydrusTime.SecondiseMS( sort_last_vacuumed_ms ) )
            
        
        ( result, info ) = self._CanVacuumName( name )
        
        pretty_can_vacuum = info
        
        ( sort_vacuum_time_estimate, pretty_vacuum_time_estimate ) = self._GetVacuumTimeEstimate( sort_total_size )
        
        display_tuple = ( pretty_name, pretty_total_size, pretty_free_size, pretty_last_vacuumed_ms, pretty_can_vacuum, pretty_vacuum_time_estimate )
        
        return display_tuple
        
    
    def _ConvertNameToSortTuple( self, name ):
        
        vacuum_dict = self._vacuum_data[ name ]
        
        page_size = vacuum_dict[ 'page_size' ]
        
        sort_name = name
        
        sort_total_size = page_size * vacuum_dict[ 'page_count' ]
        
        sort_free_size = page_size * vacuum_dict[ 'freelist_count' ]
        
        sort_last_vacuumed_ms = vacuum_dict[ 'last_vacuumed_ms' ]
        
        if sort_last_vacuumed_ms == 0 or sort_last_vacuumed_ms is None:
            
            sort_last_vacuumed_ms = 0
            
        
        ( result, info ) = self._CanVacuumName( name )
        
        sort_can_vacuum = result
        
        ( sort_vacuum_time_estimate, pretty_vacuum_time_estimate ) = self._GetVacuumTimeEstimate( sort_total_size )
        
        sort_tuple = ( sort_name, sort_total_size, sort_free_size, sort_last_vacuumed_ms, sort_can_vacuum, sort_vacuum_time_estimate )
        
        return sort_tuple
        
    
    def _GetVacuumTimeEstimate( self, db_size ):
        
        from hydrus.core import HydrusDB
        
        vacuum_time_estimate = HydrusDB.GetApproxVacuumIntoDuration( db_size )
        
        pretty_vacuum_time_estimate = '{} to {}'.format( HydrusTime.TimeDeltaToPrettyTimeDelta( vacuum_time_estimate / 20 ), HydrusTime.TimeDeltaToPrettyTimeDelta( vacuum_time_estimate ) )
        
        return ( vacuum_time_estimate, pretty_vacuum_time_estimate )
        
    
    def _Vacuum( self ):
        
        names = list( self._vacuum_listctrl.GetData( only_selected = True ) )
        
        if len( names ) > 0:
            
            total_size = sum( ( vd[ 'page_size' ] * vd[ 'page_count' ] for vd in ( self._vacuum_data[ name ] for name in names ) ) )
            
            ( sort_time_estimate, pretty_time_estimate ) = self._GetVacuumTimeEstimate( total_size )
            
            message = 'Do vacuum now? Estimated time to vacuum is {}.'.format( pretty_time_estimate )
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message, yes_label = 'do it', no_label = 'forget it' )
            
            if result == QW.QDialog.DialogCode.Accepted:
                
                self._controller.Write( 'vacuum', names )
                
                self._OKParent()
                
            
        
    
