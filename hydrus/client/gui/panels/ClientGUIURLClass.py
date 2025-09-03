import collections.abc
import typing
import urllib.parse

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusSerialisable

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientDefaults
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientStrings
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIStringControls
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListBoxes
from hydrus.client.gui.lists import ClientGUIListConstants as CGLC
from hydrus.client.gui.lists import ClientGUIListCtrl
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.gui.widgets import ClientGUIMenuButton
from hydrus.client.gui.widgets import ClientGUIRegex
from hydrus.client.networking import ClientNetworkingDomain
from hydrus.client.networking import ClientNetworkingFunctions
from hydrus.client.networking import ClientNetworkingURLClass
from hydrus.client.parsing import ClientParsing

class EditURLClassComponentPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, string_match: ClientStrings.StringMatch, default_value: typing.Optional[ str ] ):
        
        super().__init__( parent )
        
        from hydrus.client.gui import ClientGUIStringPanels
        
        string_match_panel = ClientGUICommon.StaticBox( self, 'value test' )
        
        # TODO: this guy sizes crazy because he is a scrolling panel not a normal widget
        # the layout of this panel was whack, better now but revisit it (add a vbox.addStretch( 0 )?) once this guy is a widget
        self._string_match = ClientGUIStringPanels.EditStringMatchPanel( string_match_panel, string_match )
        self._string_match.setToolTip( ClientGUIFunctions.WrapToolTip( 'If the encoded value of the component matches this, the URL Class matches!' ) )
        
        self._pretty_default_value = ClientGUICommon.NoneableTextCtrl( self, '' )
        self._pretty_default_value.setToolTip( ClientGUIFunctions.WrapToolTip( 'If the URL is missing this component, you can add it here, and the URL Class will still match and will normalise by adding this default value. This can be useful if you need to add a /art or similar to a URL that ends with either /username or /username/art--sometimes it is better to make that stuff explicit in all cases.' ) )
        
        self._default_value = ClientGUICommon.NoneableTextCtrl( self, '' )
        self._default_value.setToolTip( ClientGUIFunctions.WrapToolTip( 'What actual value will be embedded into the URL sent to the server.' ) )
        
        #
        
        self.SetValue( string_match, default_value )
        
        #
        
        st = ClientGUICommon.BetterStaticText( string_match_panel, label = 'The String Match here will test against the value in the normalised, %-encoded URL. If you have "post%20images", test for that, not "post images".' )
        st.setWordWrap( True )
        
        string_match_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
        string_match_panel.Add( self._string_match, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        rows = []
        
        rows.append( ( 'default value: ', self._pretty_default_value ) )
        rows.append( ( 'default value, %-encoded: ', self._default_value ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, string_match_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self.widget().setLayout( vbox )
        
        self._pretty_default_value.valueChanged.connect( self._PrettyDefaultValueChanged )
        self._default_value.valueChanged.connect( self._DefaultValueChanged )
        
    
    def _DefaultValueChanged( self ):
        
        default_value = self._default_value.GetValue()
        
        pretty_default_value = default_value if default_value is None else urllib.parse.unquote( default_value )
        
        self._pretty_default_value.blockSignals( True )
        
        self._pretty_default_value.SetValue( pretty_default_value )
        
        self._pretty_default_value.blockSignals( False )
        
    
    def _GetValue( self ):
        
        string_match = self._string_match.GetValue()
        default_value = self._default_value.GetValue()
        
        return ( string_match, default_value )
        
    
    def _PrettyDefaultValueChanged( self ):
        
        pretty_default_value = self._pretty_default_value.GetValue()
        
        default_value = pretty_default_value if pretty_default_value is None else ClientNetworkingFunctions.ensure_path_component_is_encoded( pretty_default_value )
        
        self._default_value.blockSignals( True )
        
        self._default_value.SetValue( default_value )
        
        self._default_value.blockSignals( False )
        
    
    def GetValue( self ):
        
        ( string_match, default_value ) = self._GetValue()
        
        if default_value is not None and not string_match.Matches( default_value ):
            
            raise HydrusExceptions.VetoException( 'That default value does not match the rule!' )
            
        
        return ( string_match, default_value )
        
    
    def SetValue( self, string_match: ClientStrings.StringMatch, default_value: typing.Optional[ str ] ):
        
        self._default_value.blockSignals( True )
        
        if default_value is None:
            
            self._default_value.SetValue( default_value )
            
        else:
            
            try:
                
                self._default_value.SetValue( default_value )
                
            except:
                
                self._default_value.SetValue( default_value )
                
            
        
        self._default_value.blockSignals( False )
        
        self._DefaultValueChanged()
        
        self._string_match.SetValue( string_match )
        
    

class EditURLClassParameterFixedNamePanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, parameter: ClientNetworkingURLClass.URLClassParameterFixedName, dupe_names ):
        
        # maybe graduate this guy to a 'any type of parameter' panel and have a dropdown and show/hide fixed name etc..
        
        super().__init__( parent )
        
        self._dupe_names = dupe_names
        
        self._pretty_name = QW.QLineEdit( self )
        self._pretty_name.setToolTip( ClientGUIFunctions.WrapToolTip( 'The "key" of the key=value pair.' ) )
        
        self._name = QW.QLineEdit( self )
        self._name.setToolTip( ClientGUIFunctions.WrapToolTip( 'The "key" of the key=value pair. This encoded form is what is actually sent to the server!' ) )
        
        value_string_match_panel = ClientGUICommon.StaticBox( self, 'value test' )
        
        from hydrus.client.gui import ClientGUIStringPanels
        
        self._value_string_match = ClientGUIStringPanels.EditStringMatchPanel( value_string_match_panel, parameter.GetValueStringMatch() )
        self._value_string_match.setToolTip( ClientGUIFunctions.WrapToolTip( 'If the encoded value of the key=value pair matches this, the URL Class matches!' ) )
        
        self._is_ephemeral = QW.QCheckBox( self )
        tt = 'THIS IS ADVANCED, DO NOT SET IF YOU ARE UNSURE! If this parameter is a one-time token or similar needed for the server request but not something you want to keep or use to compare, you can define it here.'
        tt += '\n' * 2
        tt += 'These tokens are also allowed _en masse_ in the main URL Class by setting "allow extra parameters for server", BUT if you need a whitelist, you will want to define them here. Also, if you need to pass this token on to an API/redirect converter, you have to define it here!'
        self._is_ephemeral.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._pretty_default_value = ClientGUICommon.NoneableTextCtrl( self, '' )
        self._pretty_default_value.setToolTip( ClientGUIFunctions.WrapToolTip( 'If the URL is missing this key=value pair, you can add it here, and the URL Class will still match and will normalise with this default value. This can be useful for gallery URLs that have an implicit page=1 or index=0 for their first result--sometimes it is better to make that stuff explicit in all cases.' ) )
        
        self._default_value = ClientGUICommon.NoneableTextCtrl( self, '' )
        self._default_value.setToolTip( ClientGUIFunctions.WrapToolTip( 'What actual value will be embedded into the URL sent to the server.' ) )
        
        self._default_value_string_processor = ClientGUIStringControls.StringProcessorWidget( self, parameter.GetDefaultValueStringProcessor(), self._GetTestData )
        tt = 'WARNING WARNING: Extremely Big Brain'
        tt += '\n' * 2
        tt += 'You can apply the parsing system\'s normal String Processor steps to your fixed default value here. For instance, you could append/replace the default value with random hex or today\'s date. This is obviously super advanced, so be careful.'
        self._default_value_string_processor.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        #
        
        self.SetValue( parameter )
        
        #
        
        st = ClientGUICommon.BetterStaticText( value_string_match_panel, label = 'The String Match here will test against the value in the normalised, %-encoded URL. If you have "type=%E3%83%9D%E3%82%B9%E3%83%88", test for that, not "ポスト".' )
        st.setWordWrap( True )
        
        value_string_match_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
        value_string_match_panel.Add( self._value_string_match, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        rows = []
        
        rows.append( ( 'name: ', self._pretty_name ) )
        rows.append( ( 'name, %-encoded: ', self._name ) )
        rows.append( value_string_match_panel )
        rows.append( ( 'is ephemeral token?: ', self._is_ephemeral ) )
        rows.append( ( 'default value: ', self._pretty_default_value ) )
        rows.append( ( 'default value, %-encoded: ', self._default_value ) )
        rows.append( ( 'default value string processor: ', self._default_value_string_processor ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows, expand_single_widgets = True )
        
        vbox = QP.VBoxLayout()
        
        # TODO: set this to perpendicular and the addstretch when stringmatch is not a panel
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        #vbox.addStretch( 0 )
        
        self.widget().setLayout( vbox )
        
        self._pretty_name.textChanged.connect( self._PrettyNameChanged )
        self._name.textChanged.connect( self._NameChanged )
        self._pretty_default_value.valueChanged.connect( self._PrettyDefaultValueChanged )
        self._default_value.valueChanged.connect( self._DefaultValueChanged )
        
        self._is_ephemeral.clicked.connect( self._UpdateProcessorEnabled )
        self._pretty_default_value.valueChanged.connect( self._UpdateProcessorEnabled )
        self._default_value.valueChanged.connect( self._UpdateProcessorEnabled )
        
    
    def _UpdateProcessorEnabled( self ):
        
        we_out_here = self._is_ephemeral.isChecked() and self._default_value.GetValue() is not None
        
        self._default_value_string_processor.setEnabled( we_out_here )
        
    
    def _DefaultValueChanged( self ):
        
        default_value = self._default_value.GetValue()
        
        pretty_default_value = default_value if default_value is None else urllib.parse.unquote( default_value )
        
        self._pretty_default_value.blockSignals( True )
        
        self._pretty_default_value.SetValue( pretty_default_value )
        
        self._pretty_default_value.blockSignals( False )
        
    
    def _GetTestData( self ) -> ClientParsing.ParsingTestData:
        
        default_value = self._default_value.GetValue()
        
        if default_value is None:
            
            default_value = 'test'
            
        
        return ClientParsing.ParsingTestData( {}, texts = [ default_value ] )
        
    
    def _GetValue( self ):
        
        name = self._name.text()
        
        value_string_match = self._value_string_match.GetValue()
        
        parameter = ClientNetworkingURLClass.URLClassParameterFixedName(
            name = name,
            value_string_match = value_string_match
        )
        
        is_ephemeral = self._is_ephemeral.isChecked()
        parameter.SetIsEphemeral( is_ephemeral )
        
        default_value = self._default_value.GetValue()
        parameter.SetDefaultValue( default_value )
        
        if is_ephemeral and default_value is not None:
            
            default_value_string_processor = self._default_value_string_processor.GetValue()
            parameter.SetDefaultValueStringProcessor( default_value_string_processor )
            
        
        return parameter
        
    
    def _NameChanged( self ):
        
        name = self._name.text()
        
        pretty_name = name if name is None else urllib.parse.unquote( name )
        
        self._pretty_name.blockSignals( True )
        
        self._pretty_name.setText( pretty_name )
        
        self._pretty_name.blockSignals( False )
        
    
    def _PrettyDefaultValueChanged( self ):
        
        pretty_default_value = self._pretty_default_value.GetValue()
        
        default_value = pretty_default_value if pretty_default_value is None else ClientNetworkingFunctions.ensure_param_component_is_encoded( pretty_default_value )
        
        self._default_value.blockSignals( True )
        
        self._default_value.SetValue( default_value )
        
        self._default_value.blockSignals( False )
        
    
    def _PrettyNameChanged( self ):
        
        pretty_name = self._pretty_name.text()
        
        name = pretty_name if pretty_name is None else ClientNetworkingFunctions.ensure_param_component_is_encoded( pretty_name )
        
        self._name.blockSignals( True )
        
        self._name.setText( name )
        
        self._name.blockSignals( False )
        
    
    def GetValue( self ):
        
        parameter = self._GetValue()
        
        name = parameter.GetName()
        
        if name == '':
            
            raise HydrusExceptions.VetoException( 'Sorry, you have to set a key/name!' )
            
        
        if name in self._dupe_names:
            
            raise HydrusExceptions.VetoException( 'Sorry, your key/name already exists, pick something else!' )
            
        
        return parameter
        
    
    def SetValue( self, parameter: ClientNetworkingURLClass.URLClassParameterFixedName ):
        
        self._name.blockSignals( True )
        
        try:
            
            self._name.setText( parameter.GetName() )
            
        except:
            
            self._name.setText( parameter.GetName() )
            
        
        self._name.blockSignals( False )
        
        self._NameChanged()
        
        default_value = parameter.GetDefaultValue()
        
        self._default_value.blockSignals( True )
        
        if default_value is None:
            
            self._default_value.SetValue( default_value )
            
        else:
            
            try:
                
                self._default_value.SetValue( default_value )
                
            except:
                
                self._default_value.SetValue( default_value )
                
            
        
        self._default_value.blockSignals( False )
        
        self._DefaultValueChanged()
        
        self._value_string_match.SetValue( parameter.GetValueStringMatch() )
        
        self._is_ephemeral.setChecked( parameter.IsEphemeralToken() )
        
        self._default_value_string_processor.SetValue( parameter.GetDefaultValueStringProcessor() )
        
        self._UpdateProcessorEnabled()
        
    

class EditURLClassPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, url_class: ClientNetworkingURLClass.URLClass ):
        
        super().__init__( parent )
        
        self._update_already_in_progress = False # Used to avoid infinite recursion on control updates.
        
        self._original_url_class = url_class
        
        self._name = QW.QLineEdit( self )
        
        self._url_type = ClientGUICommon.BetterChoice( self )
        
        for u_t in ( HC.URL_TYPE_POST, HC.URL_TYPE_GALLERY, HC.URL_TYPE_WATCHABLE, HC.URL_TYPE_FILE ):
            
            self._url_type.addItem( HC.url_type_string_lookup[ u_t ], u_t )
            
        
        url_type = url_class.GetURLType()
        preferred_scheme = url_class.GetPreferredScheme()
        url_domain_mask = url_class.GetURLDomainMask()
        path_components = url_class.GetPathComponents()
        parameters = url_class.GetParameters()
        api_lookup_converter = url_class.GetAPILookupConverter()
        ( send_referral_url, referral_url_converter ) = url_class.GetReferralURLInfo()
        example_url = url_class.GetExampleURL( encoded = False )
        
        self._notebook = ClientGUICommon.BetterNotebook( self )
        
        #
        
        self._matching_panel = ClientGUICommon.StaticBox( self._notebook, 'matching' )
        
        #
        
        self._preferred_scheme = ClientGUICommon.BetterChoice( self._matching_panel )
        
        self._preferred_scheme.addItem( 'http', 'http' )
        self._preferred_scheme.addItem( 'https', 'https' )
        
        self._url_domain_mask = EditURLDomainMaskWidget( self, url_domain_mask )
        
        try:
            
            example_domain = ClientNetworkingFunctions.ConvertURLIntoDomain( example_url )
            
            self._url_domain_mask.SetExampleDomain( example_domain )
            
        except:
            
            pass
            
        
        #
        
        path_components_panel = ClientGUICommon.StaticBox( self._matching_panel, 'path components', can_expand = True, start_expanded = True )
        
        self._path_components = ClientGUIListBoxes.QueueListBox( path_components_panel, 6, self._ConvertPathComponentRowToString, self._AddPathComponent, self._EditPathComponent )
        
        #
        
        parameters_panel = ClientGUICommon.StaticBox( self._matching_panel, 'parameters', can_expand = True, start_expanded = True )
        
        parameters_listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( parameters_panel )
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_URL_CLASS_PARAMETERS.ID, self._ConvertParameterToDisplayTuple, self._ConvertParameterToSortTuple )
        
        self._parameters = ClientGUIListCtrl.BetterListCtrlTreeView( parameters_listctrl_panel, 5, model, delete_key_callback = self._DeleteParameters, activation_callback = self._EditParameters )
        
        parameters_listctrl_panel.SetListCtrl( self._parameters )
        
        parameters_listctrl_panel.AddButton( 'add', self._AddParameters )
        parameters_listctrl_panel.AddButton( 'edit', self._EditParameters, enabled_only_on_single_selection = True )
        parameters_listctrl_panel.AddDeleteButton()
        
        #
        
        ( has_single_value_parameters, single_value_parameters_string_match ) = url_class.GetSingleValueParameterData()
        
        self._has_single_value_parameters = QW.QCheckBox( self._matching_panel )
        
        tt = 'Some URLs have parameters with just a key or a value, not a "key=value" pair. Normally these are removed on normalisation, but if you turn this on, then this URL will keep them and require at least one.'
        
        self._has_single_value_parameters.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._has_single_value_parameters.setChecked( has_single_value_parameters )
        
        self._single_value_parameters_string_match = ClientGUIStringControls.StringMatchButton( self._matching_panel, single_value_parameters_string_match )
        
        tt = 'All single-value parameters must match this!'
        
        #
        
        self._notebook.addTab( self._matching_panel, 'match rules' )
        
        #
        
        self._options_panel = ClientGUICommon.StaticBox( self._notebook, 'options' )
        
        #
        
        self._alphabetise_get_parameters = QW.QCheckBox( self._options_panel )
        
        tt = 'Normally, to ensure the same URLs are merged, hydrus will alphabetise GET parameters as part of the normalisation process.'
        tt += '\n' * 2
        tt += 'Almost all servers support GET params in any order. One or two do not. Uncheck this if you know there is a problem.'
        tt += '\n\n'
        tt += 'Be careful mixing this with an API or Referral URL Converter that converts parameter data, since now you have unordered parameter data to think about.'
        
        self._alphabetise_get_parameters.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._no_more_path_components_than_this = QW.QCheckBox( self._options_panel )
        
        tt = 'Normally, hydrus will match a URL that has a longer path than is defined here. site.com/index/123456/cool-pic-by-artist will match a URL class that looks for site.com/index/123456, and it will remove that extra cruft on normalisation.'
        tt += '\n' * 2
        tt += 'Checking this turns that behaviour off. It will only match if the given URL satisfies all defined path component tests, and no more. If you have multiple URL Classes matching on different levels of a tree, and hydrus is having difficulty matching them up in the right order (neighbouring Gallery/Post URLs can do this), try this.'
        
        self._no_more_path_components_than_this.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._no_more_parameters_than_this = QW.QCheckBox( self._options_panel )
        
        tt = 'Normally, hydrus will match a URL that has more parameters than is defined here. site.com/index?p=123456&orig_tags=skirt will match a URL class that looks for site.com/index?p=123456. Post URLs will remove that extra cruft on normalisation.'
        tt += '\n' * 2
        tt += 'Checking this turns that behaviour off. It will only match if the given URL satisfies all defined parameter tests, and no more. If you have multiple URL Classes matching on the same base URL path but with different query params, and hydrus is having difficulty matching them up in the right order (neighbouring Gallery/Post URLs can do this), try this.'
        
        self._no_more_parameters_than_this.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._keep_extra_parameters_for_server = QW.QCheckBox( self._options_panel )
        tt = 'If checked, the URL not strip out undefined parameters in the normalisation process that occurs before a URL is sent to the server. In general, you probably want to keep this on, since these extra parameters can include temporary tokens and so on. Undefined parameters are removed when URLs are compared to each other (to detect dupes) or saved to the "known urls" storage in the database.'
        tt += '\n\n'
        tt += 'Be careful mixing this with an API or Referral URL Converter that converts parameter data, since now you have optional parameter data to think about.'
        self._keep_extra_parameters_for_server.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._can_produce_multiple_files = QW.QCheckBox( self._options_panel )
        
        tt = 'If checked, the client will not rely on instances of this URL class to predetermine \'already in db\' or \'previously deleted\' outcomes. This is important for post types like pixiv pages (which can ultimately be manga, and represent many pages) and tweets (which can have multiple images).'
        tt += '\n' * 2
        tt += 'Most booru-type Post URLs only produce one file per URL and should not have this checked. Checking this avoids some bad logic where the client would falsely think it if it had seen one file at the URL, it had seen them all, but it then means the client has to download those pages\' content again whenever it sees them (so it can check against the direct File URLs, which are always considered one-file each).'
        
        self._can_produce_multiple_files.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._should_be_associated_with_files = QW.QCheckBox( self._options_panel )
        
        tt = 'If checked, the client will try to remember this url with any files it ends up importing. It will present this url in \'known urls\' ui across the program.'
        tt += '\n' * 2
        tt += 'If this URL is a File or Post URL and the client comes across it after having already downloaded it once, it can skip the redundant download since it knows it already has (or has already deleted) the file once before.'
        tt += '\n' * 2
        tt += 'Turning this on is only useful if the URL is non-ephemeral (i.e. the URL will produce the exact same file(s) in six months\' time). It is usually not appropriate for booru gallery or thread urls, which alter regularly, but is for static Post URLs or some fixed doujin galleries.'
        
        self._should_be_associated_with_files.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._keep_fragment = QW.QCheckBox( self._options_panel )
        
        tt = 'If checked, fragment text will be kept. This is the component sometimes after an URL that starts with a "#", such as "#kwGFb3xhA3k8B".'
        tt += '\n' * 2
        tt += 'This data is never sent to a server, so in normal cases should never be kept, but for some clever services such as Mega, with complicated javascript navigation, it may contain unique clientside navigation data if you open the URL in your browser.'
        tt += '\n' * 2
        tt += 'Only turn this on if you know it is needed. For almost all sites, it only hurts the normalisation process.'
        
        self._keep_fragment.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        #
        
        self._referral_url_panel = ClientGUICommon.StaticBox( self._options_panel, 'referral url' )
        
        self._send_referral_url = ClientGUICommon.BetterChoice( self._referral_url_panel )
        
        for s_r_u_t in ClientNetworkingURLClass.SEND_REFERRAL_URL_TYPES:
            
            self._send_referral_url.addItem( ClientNetworkingURLClass.send_referral_url_string_lookup[ s_r_u_t ], s_r_u_t )
            
        
        tt = 'Do not change this unless you know you need to. It fixes complicated problems.'
        
        self._send_referral_url.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._referral_url_converter = ClientGUIStringControls.StringConverterButton( self._referral_url_panel, referral_url_converter )
        
        tt = 'This will generate a referral URL from the original URL. If the URL needs a referral URL, and you can infer what that would be from just this URL, this will let hydrus download this URL without having to previously visit the referral URL (e.g. letting the user drag-and-drop import). It also lets you set up alternate referral URLs for perculiar situations.'
        
        self._referral_url_converter.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._referral_url = QW.QLineEdit( self._referral_url_panel )
        self._referral_url.setReadOnly( True )
        
        #
        
        self._api_url_panel = ClientGUICommon.StaticBox( self._options_panel, 'api url' )
        
        self._api_lookup_converter = ClientGUIStringControls.StringConverterButton( self._api_url_panel, api_lookup_converter )
        
        tt = 'This will let you generate an alternate URL for the client to use for the actual download whenever it encounters a URL in this class. You must have a separate URL class to match the API type (which will link to parsers).'
        
        self._api_lookup_converter.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._api_url = QW.QLineEdit( self._api_url_panel )
        self._api_url.setReadOnly( True )
        
        #
        
        self._next_gallery_page_panel = ClientGUICommon.StaticBox( self._options_panel, 'next gallery page' )
        
        self._next_gallery_page_choice = ClientGUICommon.BetterChoice( self._next_gallery_page_panel )
        
        self._next_gallery_page_delta = ClientGUICommon.BetterSpinBox( self._next_gallery_page_panel, min=1, max=65536 )
        
        self._next_gallery_page_url = QW.QLineEdit( self._next_gallery_page_panel )
        self._next_gallery_page_url.setReadOnly( True )
        
        #
        
        headers_panel = ClientGUICommon.StaticBox( self._options_panel, 'header overrides' )
        
        header_overrides = url_class.GetHeaderOverrides()
        
        self._header_overrides = ClientGUIStringControls.StringToStringDictControl( headers_panel, header_overrides, min_height = 4 )
        
        #
        
        self._notebook.addTab( self._options_panel, 'options' )
        
        #
        
        self._example_url = QW.QLineEdit( self )
        
        self._example_url_classes = ClientGUICommon.BetterStaticText( self )
        
        self._for_server_normalised_url = QW.QLineEdit( self )
        self._for_server_normalised_url.setReadOnly( True )
        
        tt = 'This is what should actually be sent to the server. It has some elements of full normalisation, but depending on your options, there may be additional, "ephemeral" data included. If you use an API/redirect, it will be that.'
        
        self._for_server_normalised_url.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._normalised_url = QW.QLineEdit( self )
        self._normalised_url.setReadOnly( True )
        
        tt = 'This is the fully normalised URL, which is what is saved to the database. It is used to compare to other URLs.'
        tt += '\n' * 2
        tt += 'We want to normalise to a single reliable URL because the same URL can be expressed in different ways. The parameters can be reordered, and descriptive \'sugar\' like "/123456/bodysuit-samus_aran" can be altered at a later date, say to "/123456/bodysuit-green_eyes-samus_aran". In order to collapse all the different expressions of a url down to a single comparable form, we remove any cruft and "normalise" things. The preferred scheme (http/https) will be switched to, and, typically, parameters will be alphabetised and non-defined elements will be removed.'
        
        self._normalised_url.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        #
        
        name = url_class.GetName()
        
        self._name.setText( name )
        
        self._url_type.SetValue( url_type )
        
        self._preferred_scheme.SetValue( preferred_scheme )
        
        ( alphabetise_get_parameters, can_produce_multiple_files, should_be_associated_with_files, keep_fragment ) = url_class.GetURLBooleans()
        
        self._alphabetise_get_parameters.setChecked( alphabetise_get_parameters )
        self._can_produce_multiple_files.setChecked( can_produce_multiple_files )
        self._should_be_associated_with_files.setChecked( should_be_associated_with_files )
        self._keep_fragment.setChecked( keep_fragment )
        
        self._no_more_path_components_than_this.setChecked( url_class.NoMorePathComponentsThanThis() )
        self._no_more_parameters_than_this.setChecked( url_class.NoMoreParametersThanThis() )
        
        self._keep_extra_parameters_for_server.setChecked( url_class.KeepExtraParametersForServer() )
        
        self._path_components.AddDatas( path_components )
        
        self._parameters.AddDatas( parameters )
        
        self._parameters.Sort()
        
        self._example_url.setText( example_url )
        
        example_url_width = ClientGUIFunctions.ConvertTextToPixelWidth( self._example_url, 75 )
        
        self._example_url.setMinimumWidth( example_url_width )
        
        self._send_referral_url.SetValue( send_referral_url )
        
        ( gallery_index_type, gallery_index_identifier, gallery_index_delta ) = url_class.GetGalleryIndexValues()
        
        # this preps it for the upcoming update
        self._next_gallery_page_choice.addItem( 'initialisation', ( gallery_index_type, gallery_index_identifier ) )
        self._next_gallery_page_choice.setCurrentIndex( 0 )
        
        self._next_gallery_page_delta.setValue( gallery_index_delta )
        
        self._UpdateControls()
        
        #
        
        path_components_panel.Add( self._path_components, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        parameters_panel.Add( parameters_listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        headers_panel.Add( self._header_overrides, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        rows = []
        
        rows.append( ( 'preferred scheme: ', self._preferred_scheme ) )
        
        gridbox_1 = ClientGUICommon.WrapInGrid( self._matching_panel, rows )
        
        rows = []
        
        rows.append( ( 'has single-value parameter(s): ', self._has_single_value_parameters ) )
        rows.append( ( 'string match for single-value parameters: ', self._single_value_parameters_string_match ) )
        
        gridbox_2 = ClientGUICommon.WrapInGrid( self._matching_panel, rows )
        
        self._matching_panel.Add( gridbox_1, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._matching_panel.Add( self._url_domain_mask, CC.FLAGS_EXPAND_BOTH_WAYS )
        self._matching_panel.Add( path_components_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        self._matching_panel.Add( parameters_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        self._matching_panel.Add( gridbox_2, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self._url_domain_mask.UpdateSizePolicyGubbins()
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._next_gallery_page_choice, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, self._next_gallery_page_delta, CC.FLAGS_CENTER_PERPENDICULAR )
        
        rows = []
        
        rows.append( ( 'next gallery page url: ', self._next_gallery_page_url ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._next_gallery_page_panel, rows )
        
        self._next_gallery_page_panel.Add( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._next_gallery_page_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        rows = []
        
        rows.append( ( 'send referral url?: ', self._send_referral_url ) )
        rows.append( ( 'optional referral url converter: ', self._referral_url_converter ) )
        rows.append( ( 'referral url: ', self._referral_url ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._referral_url_panel, rows )
        
        self._referral_url_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        rows = []
        
        rows.append( ( 'optional api/redirect url converter: ', self._api_lookup_converter ) )
        rows.append( ( 'api/redirect url: ', self._api_url ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._api_url_panel, rows )
        
        self._api_url_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        rows = []
        
        rows.append( ( 'alphabetise GET parameters when normalising: ', self._alphabetise_get_parameters ) )
        rows.append( ( 'disallow match on any extra path components: ', self._no_more_path_components_than_this ) )
        rows.append( ( 'disallow match on any extra parameters: ', self._no_more_parameters_than_this ) )
        rows.append( ( 'keep extra parameters for server: ', self._keep_extra_parameters_for_server ) )
        rows.append( ( 'keep fragment when normalising: ', self._keep_fragment ) )
        rows.append( ( 'post page can produce multiple files: ', self._can_produce_multiple_files ) )
        rows.append( ( 'associate a \'known url\' with resulting files: ', self._should_be_associated_with_files ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._options_panel, rows )
        
        self._options_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._options_panel.Add( self._api_url_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._options_panel.Add( self._referral_url_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._options_panel.Add( self._next_gallery_page_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._options_panel.Add( headers_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        rows = []
        
        rows.append( ( 'name: ', self._name ) )
        rows.append( ( 'url type: ', self._url_type ) )
        
        gridbox_1 = ClientGUICommon.WrapInGrid( self, rows )
        
        rows = []
        
        rows.append( ( 'example url: ', self._example_url ) )
        rows.append( ( 'request url: ', self._for_server_normalised_url ) )
        rows.append( ( 'normalised url: ', self._normalised_url ) )
        
        gridbox_2 = ClientGUICommon.WrapInGrid( self, rows )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, gridbox_1, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, self._notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, self._example_url_classes, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, gridbox_2, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self.widget().setLayout( vbox )
        
        #
        
        self._preferred_scheme.currentIndexChanged.connect( self._UpdateControls )
        self._url_domain_mask.valueChanged.connect( self._UpdateControls )
        self._alphabetise_get_parameters.clicked.connect( self._UpdateControls )
        self._no_more_path_components_than_this.clicked.connect( self._UpdateControls )
        self._no_more_parameters_than_this.clicked.connect( self._UpdateControls )
        self._keep_extra_parameters_for_server.clicked.connect( self._UpdateControls )
        self._keep_fragment.clicked.connect( self._UpdateControls )
        self._can_produce_multiple_files.clicked.connect( self._UpdateControls )
        self._next_gallery_page_choice.currentIndexChanged.connect( self._UpdateControls )
        self._next_gallery_page_delta.valueChanged.connect( self._UpdateControls )
        self._example_url.textChanged.connect( self._UpdateControls )
        self._path_components.listBoxChanged.connect( self._UpdateControls )
        self._url_type.currentIndexChanged.connect( self.EventURLTypeUpdate )
        self._send_referral_url.currentIndexChanged.connect( self._UpdateControls )
        self._referral_url_converter.valueChanged.connect( self._UpdateControls )
        self._api_lookup_converter.valueChanged.connect( self._UpdateControls )
        self._has_single_value_parameters.clicked.connect( self._UpdateControls )
        self._single_value_parameters_string_match.valueChanged.connect( self._UpdateControls )
        
        self._should_be_associated_with_files.clicked.connect( self.EventAssociationUpdate )
        
    
    def _AddParameters( self ):
        
        existing_names = self._GetExistingParameterNames()
        
        parameter = ClientNetworkingURLClass.URLClassParameterFixedName()
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit parameter' ) as dlg:
            
            panel = EditURLClassParameterFixedNamePanel( dlg, parameter, existing_names )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                parameter = panel.GetValue()
                
                self._parameters.AddData( parameter, select_sort_and_scroll = True )
                
                self._UpdateControls()
                
            else:
                
                return
                
            
        
    
    def _AddPathComponent( self ):
        
        string_match = ClientStrings.StringMatch()
        default = None
        
        return self._EditPathComponent( ( string_match, default ) )
        
    
    def _ConvertParameterToDisplayTuple( self, parameter: ClientNetworkingURLClass.URLClassParameterFixedName ):
        
        name = parameter.GetName()
        value_string_match = parameter.GetValueStringMatch()
        
        pretty_name = urllib.parse.unquote( name )
        pretty_value_string_match = value_string_match.ToString()
        
        if parameter.HasDefaultValue():
            
            pretty_value_string_match += f' (default "{urllib.parse.unquote(parameter.GetDefaultValue( with_processing = True ))}")'
            
        
        if parameter.IsEphemeralToken():
            
            pretty_value_string_match += ' (is ephemeral)'
            
        
        return ( pretty_name, pretty_value_string_match )
        
    
    _ConvertParameterToSortTuple = _ConvertParameterToDisplayTuple
    
    def _ConvertPathComponentRowToString( self, row ):
        
        ( string_match, default ) = row
        
        s = string_match.ToString()
        
        if default is not None:
            
            s += ' (default "' + default + '")'
            
        
        return s
        
    
    def _DeleteParameters( self ):
        
        self._parameters.ShowDeleteSelectedDialog()
        
        self._UpdateControls()
        
    
    def _EditParameters( self ):
        
        selected_parameter = self._parameters.GetTopSelectedData()
        
        if selected_parameter is None:
            
            return
            
        
        existing_names = set( self._GetExistingParameterNames() )
        
        existing_names.discard( selected_parameter.GetName() )
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit value' ) as dlg:
            
            panel = EditURLClassParameterFixedNamePanel( self, selected_parameter, existing_names )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                edited_parameter = panel.GetValue()
                
                self._parameters.ReplaceData( selected_parameter, edited_parameter, sort_and_scroll = True )
                
            
        
        self._UpdateControls()
        
    
    def _EditPathComponent( self, row ):
        
        ( string_match, default_value ) = row
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit path component' ) as dlg:
            
            panel = EditURLClassComponentPanel( dlg, string_match, default_value )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                ( new_string_match, new_default_value ) = panel.GetValue()
                
                CG.client_controller.CallAfter( self, self._UpdateControls ) # seems sometimes this doesn't kick in naturally
                
                new_row = ( new_string_match, new_default_value )
                
                return new_row
                
            
            raise HydrusExceptions.VetoException()
            
        
    
    def _GetExistingParameterNames( self ) -> set[ str ]:
        
        parameters = self._parameters.GetData()
        
        fixed_names = { parameter.GetName() for parameter in parameters if isinstance( parameter, ClientNetworkingURLClass.URLClassParameterFixedName ) }
        
        return fixed_names
        
    
    def _GetValue( self ):
        
        url_class_key = self._original_url_class.GetClassKey()
        name = self._name.text()
        url_type = self._url_type.GetValue()
        preferred_scheme = self._preferred_scheme.GetValue()
        
        url_domain_mask = self._url_domain_mask.GetValue()
        
        path_components = self._path_components.GetData()
        parameters = self._parameters.GetData()
        has_single_value_parameters = self._has_single_value_parameters.isChecked()
        single_value_parameters_string_match = self._single_value_parameters_string_match.GetValue()
        header_overrides = self._header_overrides.GetValue()
        api_lookup_converter = self._api_lookup_converter.GetValue()
        send_referral_url = self._send_referral_url.GetValue()
        referral_url_converter = self._referral_url_converter.GetValue()
        
        ( gallery_index_type, gallery_index_identifier ) = self._next_gallery_page_choice.GetValue()
        gallery_index_delta = self._next_gallery_page_delta.value()
        
        example_url = self._example_url.text()
        
        url_class = ClientNetworkingURLClass.URLClass(
            name,
            url_class_key = url_class_key,
            url_type = url_type,
            preferred_scheme = preferred_scheme,
            url_domain_mask = url_domain_mask,
            path_components = path_components,
            parameters = parameters,
            has_single_value_parameters = has_single_value_parameters,
            single_value_parameters_string_match = single_value_parameters_string_match,
            header_overrides = header_overrides,
            api_lookup_converter = api_lookup_converter,
            send_referral_url = send_referral_url,
            referral_url_converter = referral_url_converter,
            gallery_index_type = gallery_index_type,
            gallery_index_identifier = gallery_index_identifier,
            gallery_index_delta = gallery_index_delta,
            example_url = example_url
        )
        
        alphabetise_get_parameters = self._alphabetise_get_parameters.isChecked()
        can_produce_multiple_files = self._can_produce_multiple_files.isChecked()
        should_be_associated_with_files = self._should_be_associated_with_files.isChecked()
        keep_fragment = self._keep_fragment.isChecked()
        
        url_class.SetURLBooleans(
            alphabetise_get_parameters,
            can_produce_multiple_files,
            should_be_associated_with_files,
            keep_fragment
        )
        
        no_more = self._no_more_path_components_than_this.isChecked()
        
        url_class.SetNoMorePathComponentsThanThis( no_more )
        
        no_more = self._no_more_parameters_than_this.isChecked()
        
        url_class.SetNoMoreParametersThanThis( no_more )
        
        keep_extra_parameters_for_server = self._keep_extra_parameters_for_server.isChecked()
        
        url_class.SetKeepExtraParametersForServer( keep_extra_parameters_for_server )
        
        return url_class
        
    
    def _UpdateControls( self ):
        
        # we need to regen possible next gallery page choices before we fetch current value and update everything else
        
        if self._update_already_in_progress:
            
            return # Could use blockSignals but this way I don't have to block signals on individual controls
            # 2025-03 edit: what
            
        
        self._update_already_in_progress = True
        
        if self._url_type.GetValue() == HC.URL_TYPE_GALLERY:
            
            self._next_gallery_page_panel.setEnabled( True )
            
            choices = [ ( 'no next gallery page info set', ( None, None ) ) ]
            
            for ( index, ( string_match, default ) ) in enumerate( self._path_components.GetData() ):
                
                if True in ( string_match.Matches( n ) for n in ( '0', '1', '10', '100', '42' ) ):
                    
                    choices.append( ( HydrusNumbers.IntToPrettyOrdinalString( index + 1 ) + ' path component', ( ClientNetworkingURLClass.GALLERY_INDEX_TYPE_PATH_COMPONENT, index ) ) )
                    
                
            
            for parameter in self._parameters.GetData():
                
                if isinstance( parameter, ClientNetworkingURLClass.URLClassParameterFixedName ):
                    
                    if True in ( parameter.MatchesValue( n ) for n in ( '0', '1', '10', '100', '42' ) ):
                        
                        name = parameter.GetName()
                        
                        choices.append( ( f'{name} parameter', ( ClientNetworkingURLClass.GALLERY_INDEX_TYPE_PARAMETER, name ) ) )
                        
                    
                
            
            existing_choice = self._next_gallery_page_choice.GetValue()
            
            self._next_gallery_page_choice.clear()
            
            for ( name, data ) in choices:
                
                self._next_gallery_page_choice.addItem( name, data )
                
            
            self._next_gallery_page_choice.SetValue( existing_choice ) # this should fail to ( None, None )
            
            ( gallery_index_type, gallery_index_identifier ) = self._next_gallery_page_choice.GetValue() # what was actually set?
            
            if gallery_index_type is None:
                
                self._next_gallery_page_delta.setEnabled( False )
                
            else:
                
                self._next_gallery_page_delta.setEnabled( True )
                
            
        else:
            
            self._next_gallery_page_panel.setEnabled( False )
            
        
        self._single_value_parameters_string_match.setEnabled( self._has_single_value_parameters.isChecked() )
        
        nuke_keep_extra_params = self._no_more_parameters_than_this.isChecked()
        
        if nuke_keep_extra_params:
            
            self._keep_extra_parameters_for_server.setChecked( False )
            self._keep_extra_parameters_for_server.setEnabled( False )
            
        else:
            
            self._keep_extra_parameters_for_server.setEnabled( True )
            
        
        #
        
        url_class = self._GetValue()
        
        url_type = url_class.GetURLType()
        
        if url_type == HC.URL_TYPE_POST:
            
            self._can_produce_multiple_files.setEnabled( True )
            
        else:
            
            self._can_produce_multiple_files.setEnabled( False )
            
        
        try:
            
            example_url = self._example_url.text()
            
            example_url = ClientNetworkingFunctions.EnsureURLIsEncoded( example_url )
            
            url_class.Test( example_url )
            
            self._example_url_classes.setText( 'Example matches ok!' )
            self._example_url_classes.setObjectName( 'HydrusValid' )
            
            for_server_normalised = url_class.Normalise( example_url, for_server = True )
            
            self._for_server_normalised_url.setText( for_server_normalised )
            
            normalised = url_class.Normalise( example_url )
            
            self._normalised_url.setText( normalised )
            
            self._referral_url_converter.SetExampleString( for_server_normalised )
            self._api_lookup_converter.SetExampleString( for_server_normalised )
            
            if url_class.UsesAPIURL():
                
                self._send_referral_url.setEnabled( False )
                self._referral_url_converter.setEnabled( False )
                
                self._referral_url.setText( 'Not used, as API converter will redirect.' )
                
            else:
                
                self._send_referral_url.setEnabled( True )
                self._referral_url_converter.setEnabled( True )
                
                send_referral_url = self._send_referral_url.GetValue()
                
                if send_referral_url in ( ClientNetworkingURLClass.SEND_REFERRAL_URL_ONLY_IF_PROVIDED, ClientNetworkingURLClass.SEND_REFERRAL_URL_NEVER ):
                    
                    self._referral_url_converter.setEnabled( False )
                    
                else:
                    
                    self._referral_url_converter.setEnabled( True )
                    
                
                if send_referral_url == ClientNetworkingURLClass.SEND_REFERRAL_URL_CONVERTER_IF_NONE_PROVIDED:
                    
                    referral_url = url_class.GetReferralURL( normalised, None )
                    
                    referral_url = 'normal referral url -or- {}'.format( referral_url )
                    
                else:
                    
                    referral_url = url_class.GetReferralURL( normalised, 'normal referral url' )
                    
                
                if referral_url is None:
                    
                    self._referral_url.setText( 'None' )
                    
                else:
                    
                    self._referral_url.setText( referral_url )
                    
                
            
            try:
                
                if url_class.UsesAPIURL():
                    
                    api_lookup_url = url_class.GetAPIURL( example_url )
                    
                    if url_class.Matches( api_lookup_url ):
                        
                        self._example_url_classes.setText( 'Matches own API/Redirect URL!' )
                        self._example_url_classes.setObjectName( 'HydrusInvalid' )
                        
                    
                    self._for_server_normalised_url.setText( api_lookup_url )
                    
                else:
                    
                    api_lookup_url = 'none set'
                    
                
                self._api_url.setText( api_lookup_url )
                
            except HydrusExceptions.StringConvertException as e:
                
                reason = str( e )
                
                self._api_url.setText( 'Could not convert - ' + reason )
                
                self._example_url_classes.setText( 'API/Redirect URL Problem!' )
                self._example_url_classes.setObjectName( 'HydrusInvalid' )
                
            
            try:
                
                if url_class.CanGenerateNextGalleryPage():
                    
                    next_gallery_page_url = url_class.GetNextGalleryPage( normalised )
                    
                else:
                    
                    next_gallery_page_url = 'none set'
                    
                
                self._next_gallery_page_url.setText( next_gallery_page_url )
                
            except Exception as e:
                
                reason = str( e )
                
                self._next_gallery_page_url.setText( 'Could not convert - ' + reason )
                
            
        except HydrusExceptions.URLClassException as e:
            
            reason = str( e )
            
            self._example_url_classes.setText( 'Example does not match - '+reason )
            self._example_url_classes.setObjectName( 'HydrusInvalid' )
            
            self._for_server_normalised_url.clear()
            self._normalised_url.clear()
            self._api_url.clear()
            
        
        self._example_url_classes.style().polish( self._example_url_classes )
        
        self._update_already_in_progress = False
        
    
    def EventAssociationUpdate( self ):
        
        if self._should_be_associated_with_files.isChecked():
            
            if self._url_type.GetValue() in ( HC.URL_TYPE_GALLERY, HC.URL_TYPE_WATCHABLE ):
                
                message = 'Please note that it is only appropriate to associate a Gallery or Watchable URL with a file if that URL is non-ephemeral. It is only appropriate if the exact same URL will definitely give the same files in six months\' time (like a fixed doujin chapter gallery).'
                message += '\n' * 2
                message += 'If you are not sure what this means, turn this back off.'
                
                ClientGUIDialogsMessage.ShowInformation( self, message )
                
            
        else:
            
            if self._url_type.GetValue() in ( HC.URL_TYPE_FILE, HC.URL_TYPE_POST ):
                
                message = 'Hydrus uses these file associations to make sure not to re-download the same file when it comes across the same URL in future. It is only appropriate to not associate a file or post url with a file if that url is particularly ephemeral, such as if the URL includes a non-removable random key that becomes invalid after a few minutes.'
                message += '\n' * 2
                message += 'If you are not sure what this means, turn this back on.'
                
                ClientGUIDialogsMessage.ShowInformation( self, message )
            
        
    
    def EventURLTypeUpdate( self, event ):
        
        url_type = self._url_type.GetValue()
        
        if url_type in ( HC.URL_TYPE_FILE, HC.URL_TYPE_POST ):
            
            self._should_be_associated_with_files.setChecked( True )
            
        else:
            
            self._should_be_associated_with_files.setChecked( False )
            
        
        self._UpdateControls()
        
    
    def GetValue( self ) -> ClientNetworkingURLClass.URLClass:
        
        url_class = self._GetValue()
        
        example_url = self._example_url.text()
        
        try:
            
            url_class.Test( example_url )
            
        except HydrusExceptions.URLClassException:
            
            raise HydrusExceptions.VetoException( 'Please enter an example url that matches the given rules!' )
            
        
        if url_class.UsesAPIURL():
            
            try:
                
                api_lookup_url = url_class.GetAPIURL( example_url )
                
            except HydrusExceptions.StringConvertException as e:
                
                raise HydrusExceptions.VetoException( 'Problem making API/Redirect URL!' )
                
            
        
        return url_class
        
    
    def UserIsOKToOK( self ):
        
        url_class = self._GetValue()
        
        example_url = self._example_url.text()
        
        if url_class.UsesAPIURL():
            
            try:
                
                api_lookup_url = url_class.GetAPIURL( example_url )
                
            except HydrusExceptions.StringConvertException as e:
                
                return True
                
            
            if url_class.Matches( api_lookup_url ):
                
                message = 'This URL class matches its own API/Redirect URL! This can break a downloader unless there is a more specific URL Class the matches the API URL before this. I recommend you fix this here, but you do not have to. Exit now?'
                
                result = ClientGUIDialogsQuick.GetYesNo( self, message )
                
                if result != QW.QDialog.DialogCode.Accepted:
                    
                    return False
                    
                
            
        
        return True
        
    

class EditURLClassesPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, url_classes: collections.abc.Iterable[ ClientNetworkingURLClass.URLClass ] ):
        
        super().__init__( parent )
        
        self._fake_domain_manager_for_url_class_tests = None
        
        menu_template_items = []
        
        call = HydrusData.Call( ClientGUIDialogsQuick.OpenDocumentation, self, HC.DOCUMENTATION_DOWNLOADER_URL_CLASSES )
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'open the url classes help', 'Open the help page for url classes in your web browser.', call ) )
        
        help_button = ClientGUIMenuButton.MenuIconButton( self, CC.global_icons().help, menu_template_items )
        
        help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help for this panel -->', object_name = 'HydrusIndeterminate' )
        
        self._url_class_checker = QW.QLineEdit( self )
        self._url_class_checker.textChanged.connect( self.EventURLClassCheckerText )
        
        self._url_class_checker_st = ClientGUICommon.BetterStaticText( self )
        
        self._list_ctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_URL_CLASSES.ID, self._ConvertDataToDisplayTuple, self._ConvertDataToSortTuple )
        
        self._list_ctrl = ClientGUIListCtrl.BetterListCtrlTreeView( self._list_ctrl_panel, 15, model, use_simple_delete = True, activation_callback = self._Edit )
        
        self._list_ctrl_panel.SetListCtrl( self._list_ctrl )
        
        self._list_ctrl_panel.AddButton( 'add', self._Add )
        self._list_ctrl_panel.AddButton( 'edit', self._Edit, enabled_only_on_single_selection = True )
        self._list_ctrl_panel.AddDeleteButton()
        self._list_ctrl_panel.AddSeparator()
        self._list_ctrl_panel.AddImportExportButtons( ( ClientNetworkingURLClass.URLClass, ), self._AddURLClass )
        self._list_ctrl_panel.AddSeparator()
        self._list_ctrl_panel.AddDefaultsButton( ClientDefaults.GetDefaultURLClasses, self._AddURLClass )
        
        #
        
        self._list_ctrl.SetData( url_classes )
        
        #
        
        url_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( url_hbox, self._url_class_checker, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( url_hbox, self._url_class_checker_st, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, help_hbox, CC.FLAGS_ON_RIGHT )
        QP.AddToLayout( vbox, url_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._list_ctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
        #
        
        self._UpdateURLClassCheckerText()
        
        self._changes_made = False
        
    
    def _Add( self ):
        
        url_class = ClientNetworkingURLClass.URLClass( 'new url class' )
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit url class' ) as dlg:
            
            panel = EditURLClassPanel( dlg, url_class )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                url_class = panel.GetValue()
                
                self._AddURLClass( url_class, select_sort_and_scroll = True )
                
                self._list_ctrl.Sort()
                
            
        
    
    def _AddURLClass( self, url_class, select_sort_and_scroll = False ):
        
        HydrusSerialisable.SetNonDupeName( url_class, self._GetExistingNames() )
        
        url_class.RegenerateClassKey()
        
        self._list_ctrl.AddData( url_class, select_sort_and_scroll = select_sort_and_scroll )
        
        self._fake_domain_manager_for_url_class_tests = None
        
        self._changes_made = True
        
    
    def _ConvertDataToDisplayTuple( self, url_class ):
        
        name = url_class.GetName()
        url_type = url_class.GetURLType()
        
        try:
            
            example_url = url_class.Normalise( url_class.GetExampleURL() )
            
        except:
            
            example_url = 'DOES NOT MATCH OWN EXAMPLE URL!! ' + url_class.GetExampleURL()
            
        
        pretty_name = name
        pretty_url_type = HC.url_type_string_lookup[ url_type ]
        pretty_example_url = example_url
        
        return ( pretty_name, pretty_url_type, pretty_example_url )
        
    
    _ConvertDataToSortTuple = _ConvertDataToDisplayTuple
    
    def _Edit( self ):
        
        data = self._list_ctrl.GetTopSelectedData()
        
        if data is None:
            
            return
            
        
        url_class = data
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit url class' ) as dlg:
            
            panel = EditURLClassPanel( dlg, url_class )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                existing_names = self._GetExistingNames()
                existing_names.discard( url_class.GetName() )
                
                edited_url_class = panel.GetValue()
                
                HydrusSerialisable.SetNonDupeName( edited_url_class, existing_names )
                
                self._list_ctrl.ReplaceData( url_class, edited_url_class, sort_and_scroll = True )
                
                self._fake_domain_manager_for_url_class_tests = None
                
                self._changes_made = True
                
            
        
    
    def _GetExistingNames( self ):
        
        url_classes = self._list_ctrl.GetData()
        
        names = { url_class.GetName() for url_class in url_classes }
        
        return names
        
    
    def _InitialiseFakeDomainManager( self ):
        
        self._fake_domain_manager_for_url_class_tests = ClientNetworkingDomain.NetworkDomainManager()
        
        self._fake_domain_manager_for_url_class_tests.Initialise()
        
        url_classes = self.GetValue()
        
        self._fake_domain_manager_for_url_class_tests.SetURLClasses( url_classes )
        
    
    def _UpdateURLClassCheckerText( self ):
        
        unclean_url = self._url_class_checker.text()
        
        if unclean_url == '':
            
            text = '<-- Enter a URL here to see which url class it currently matches!'
            
        else:
            
            url = ClientNetworkingFunctions.EnsureURLIsEncoded( unclean_url )
            
            try:
                
                if self._fake_domain_manager_for_url_class_tests is None:
                    
                    self._InitialiseFakeDomainManager()
                    
                
                url_class = self._fake_domain_manager_for_url_class_tests.GetURLClass( url )
                
                if url_class is None:
                    
                    text = 'No match!'
                    
                else:
                    
                    text = 'Matches "' + url_class.GetName() + '"'
                    
                    self._list_ctrl.SelectDatas( ( url_class, ), deselect_others = True )
                    self._list_ctrl.ScrollToData( url_class, do_focus = False )
                    
                
            except HydrusExceptions.URLClassException as e:
                
                text = str( e )
                
            
        
        self._url_class_checker_st.setText( text )
        
    
    def EventURLClassCheckerText( self, text ):
        
        self._UpdateURLClassCheckerText()
        
    
    def GetValue( self ) -> list[ ClientNetworkingURLClass.URLClass ]:
        
        url_classes = self._list_ctrl.GetData()
        
        return url_classes
        
    
    def UserIsOKToCancel( self ):
        
        if self._changes_made or self._list_ctrl.HasDoneDeletes():
            
            message = 'You have made changes. Sure you are ok to cancel?'
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message )
            
            if result != QW.QDialog.DialogCode.Accepted:
                
                return False
                
            
        
        return True
        
    

URL_DOMAIN_MASK_WIDGET_SIMPLE = 0
URL_DOMAIN_MASK_WIDGET_FULL = 1

class EditURLDomainMaskWidget( ClientGUICommon.StaticBox ):
    
    valueChanged = QC.Signal()
    
    def __init__( self, parent, url_domain_mask: ClientNetworkingURLClass.URLDomainMask ):
        
        super().__init__( parent, 'domain', can_expand = True, start_expanded = True )
        
        self._widget_mode = ClientGUICommon.BetterChoice( self )
        
        self._widget_mode.addItem( 'simple - just one fixed domain', URL_DOMAIN_MASK_WIDGET_SIMPLE )
        self._widget_mode.addItem( 'full - multiple fixed domains and/or regex domain patterns', URL_DOMAIN_MASK_WIDGET_FULL )
        
        self._raw_domain_text_input = QW.QLineEdit( self )
        self._raw_domain_add_remove_list = ClientGUIListBoxes.AddEditDeleteListBox( self, 5, str, self._AddRawDomain, self._EditRawDomain )
        self._domain_regex_add_remove_list = ClientGUIListBoxes.AddEditDeleteListBox( self, 5, str, self._AddDomainRegex, self._EditDomainRegex )
        
        self._match_subdomains = QW.QCheckBox( self )
        
        tt = 'Should this class apply to subdomains as well?'
        tt += '\n' * 2
        tt += 'For instance, if this url class has domain \'example.com\', should it match a url with \'boards.example.com\' or \'artistname.example.com\'?'
        tt += '\n' * 2
        tt += 'Any subdomain starting with \'www\' is automatically matched, so do not worry about having to account for that.'
        tt += '\n' * 2
        tt += 'Also, if you have \'example.com\' here, but another URL class exists for \'api.example.com\', if an URL comes in with a domain of \'api.example.com\', that more specific URL Class one will always be tested before this one.'
        
        self._match_subdomains.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._keep_matched_subdomains = QW.QCheckBox( self )
        
        tt = 'Should this url keep its matched subdomains when it is normalised?'
        tt += '\n' * 2
        tt += 'This is typically useful for direct file links that are often served on a numbered CDN subdomain like \'img3.example.com\' but are also valid on the neater main domain.'
        
        self._keep_matched_subdomains.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._test_st = ClientGUICommon.BetterStaticText( self )
        
        self._test_input = QW.QLineEdit( self )
        self._test_input.setPlaceholderText( 'Enter a domain here to test if it matches.' )
        
        self._normalised_domain = QW.QLineEdit( self )
        self._normalised_domain.setReadOnly( True )
        
        self.SetValue( url_domain_mask )
        
        #
        
        hbox_full = QP.HBoxLayout()
        
        QP.AddToLayout( hbox_full, self._raw_domain_add_remove_list, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox_full, self._domain_regex_add_remove_list, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        rows = []
        
        rows.append( ( 'match subdomains: ', self._match_subdomains ) )
        rows.append( ( 'keep matched subdomains: ', self._keep_matched_subdomains ) )
        rows.append( self._test_st )
        rows.append( ( 'test domain: ', self._test_input ) )
        rows.append( ( 'normalised domain: ', self._normalised_domain ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        self.Add( self._widget_mode, CC.FLAGS_EXPAND_PERPENDICULAR )
        self.Add( self._raw_domain_text_input, CC.FLAGS_EXPAND_PERPENDICULAR )
        self.Add( hbox_full, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        self.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        self._widget_mode.currentIndexChanged.connect( self._UpdateWidgetMode )
        
        self._raw_domain_text_input.textChanged.connect( self._UpdateAfterSimpleChange )
        self._raw_domain_add_remove_list.listBoxChanged.connect( self._UpdateAfterFullChange )
        self._domain_regex_add_remove_list.listBoxChanged.connect( self._UpdateAfterFullChange )
        
        self._match_subdomains.clicked.connect( self._UpdateAfterChange )
        self._keep_matched_subdomains.clicked.connect( self._UpdateAfterChange )
        
        self._test_input.textChanged.connect( self._UpdateAfterChange )
        
    
    def _AddDomainRegex( self ):
        
        domain_regex = ''
        
        return self._EditDomainRegex( domain_regex )
        
    
    def _AddRawDomain( self ):
        
        raw_domain = ''
        
        return self._EditRawDomain( raw_domain )
        
    
    def _EditDomainRegex( self, domain_regex ):
        
        title = 'Enter domain regex.'
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, title, frame_key = 'regular_center_dialog' ) as dlg:
            
            panel = ClientGUIScrolledPanels.EditSingleCtrlPanel( dlg )
            
            control = ClientGUIRegex.RegexInput(
                panel,
                show_group_menu = False,
                show_manage_favourites_menu = True
            )
            
            control.SetValue( domain_regex )
            
            width = ClientGUIFunctions.ConvertTextToPixelWidth( control, 36 )
            
            control.setMinimumWidth( width )
            
            panel.SetControl( control )
            
            ClientGUIFunctions.SetFocusLater( control )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                domain_regex = control.GetValue()
                
                domain_regex = domain_regex.strip()
                
                if domain_regex == '':
                    
                    raise HydrusExceptions.CancelledException( 'You cannot enter an empty regex!' )
                    
                
                return domain_regex
                
            else:
                
                raise HydrusExceptions.CancelledException( 'Dialog cancelled.' )
                
            
        
    
    def _EditRawDomain( self, raw_domain ):
        
        message = 'Enter domain.'
        
        try:
            
            url = ClientGUIDialogsQuick.EnterText( self, message, default = raw_domain, placeholder = 'example.com' )
            
        except HydrusExceptions.CancelledException:
            
            raise
            
        
        url = url.strip()
        
        if url == '':
            
            raise HydrusExceptions.CancelledException( 'You cannot enter an empty URL!' )
            
        
        return url
        
    
    def _UpdateAfterChange( self ):
        
        url_domain_mask = self.GetValue()
        
        is_single_raw_domain = url_domain_mask.IsSingleRawDomain()
        
        self._widget_mode.setEnabled( is_single_raw_domain )
        
        self._keep_matched_subdomains.setEnabled( self._match_subdomains.isChecked() )
        
        #
        
        example_domain = self._test_input.text().strip()
        
        test_text = ''
        object_name = 'HydrusInvalid'
        normalised_domain = ''
        
        try:
            
            if example_domain != '':
                
                if url_domain_mask.Matches( example_domain ):
                    
                    test_text = 'Matches!'
                    object_name = 'HydrusValid'
                    
                    normalised_domain = url_domain_mask.Normalise( example_domain )
                    
                else:
                    
                    test_text = 'Does not match.'
                    
                
            
        except Exception as e:
            
            normalised_domain = f'Error: {e}'
            
        
        self._test_st.setText( test_text )
        self._test_st.setObjectName( object_name )
        self._test_st.style().polish( self._test_st )
        
        self._normalised_domain.setText( normalised_domain )
        
        self.valueChanged.emit()
        
    
    def _UpdateAfterFullChange( self ):
        
        domains = self._raw_domain_add_remove_list.GetData()
        
        if len( domains ) == 1:
            
            domain = domains[0]
            
            self._raw_domain_text_input.blockSignals( True )
            
            self._raw_domain_text_input.setText( domain )
            
            self._raw_domain_text_input.blockSignals( False )
            
        
        value = self.GetValue()
        
        self._widget_mode.setEnabled( value.IsSingleRawDomain() )
        
        self._UpdateAfterChange()
        
    
    def _UpdateAfterSimpleChange( self ):
        
        domain = self._raw_domain_text_input.text()
        
        self._raw_domain_add_remove_list.blockSignals( True )
        
        self._raw_domain_add_remove_list.Clear()
        self._raw_domain_add_remove_list.AddDatas( [ domain ] )
        
        self._raw_domain_add_remove_list.blockSignals( False )
        
        self._UpdateAfterChange()
        
    
    def _UpdateSizePolicy( self ):
        
        if self.IsExpanded():
            
            widget_mode = self._widget_mode.GetValue()
            
            simple_mode = widget_mode == URL_DOMAIN_MASK_WIDGET_SIMPLE
            
            if simple_mode:
                
                new_vert_policy = QW.QSizePolicy.Policy.Fixed
                
            else:
                
                new_vert_policy = QW.QSizePolicy.Policy.Expanding
                
            
            size_policy = self.sizePolicy()
            
            self.setSizePolicy( size_policy.horizontalPolicy(), new_vert_policy )
            
        
    
    def _UpdateWidgetMode( self ):
        
        widget_mode = self._widget_mode.GetValue()
        
        simple_mode = widget_mode == URL_DOMAIN_MASK_WIDGET_SIMPLE
        
        self._raw_domain_text_input.setVisible( simple_mode )
        
        self._raw_domain_add_remove_list.setVisible( not simple_mode )
        self._domain_regex_add_remove_list.setVisible( not simple_mode )
        
        self._UpdateSizePolicy()
        
        self._UpdateAfterChange()
        
    
    def GetValue( self ) -> ClientNetworkingURLClass.URLDomainMask:
        
        raw_domains = self._raw_domain_add_remove_list.GetData()
        domain_regexes = self._domain_regex_add_remove_list.GetData()
        match_subdomains = self._match_subdomains.isChecked()
        keep_matched_subdomains = self._keep_matched_subdomains.isChecked()
        
        url_domain_mask = ClientNetworkingURLClass.URLDomainMask(
            raw_domains = raw_domains,
            domain_regexes = domain_regexes,
            match_subdomains = match_subdomains,
            keep_matched_subdomains = keep_matched_subdomains
        )
        
        return url_domain_mask
        
    
    def SetExampleDomain( self, example_domain: str ):
        
        self._test_input.setText( example_domain )
        
        self._UpdateAfterChange()
        
    
    def SetValue( self, url_domain_mask: ClientNetworkingURLClass.URLDomainMask ):
        
        self._widget_mode.blockSignals( True )
        self._raw_domain_text_input.blockSignals( True )
        self._raw_domain_add_remove_list.blockSignals( True )
        self._domain_regex_add_remove_list.blockSignals( True )
        
        if url_domain_mask.IsSingleRawDomain():
            
            self._widget_mode.SetValue( URL_DOMAIN_MASK_WIDGET_SIMPLE )
            
            domain = url_domain_mask.GetRawDomains()[0]
            
            self._raw_domain_text_input.setText( domain )
            
        else:
            
            self._widget_mode.SetValue( URL_DOMAIN_MASK_WIDGET_FULL )
            
        
        domains = url_domain_mask.GetRawDomains()
        
        self._raw_domain_add_remove_list.Clear()
        self._raw_domain_add_remove_list.AddDatas( domains )
        
        domain_regexes = url_domain_mask.GetDomainRegexes()
        
        self._domain_regex_add_remove_list.Clear()
        self._domain_regex_add_remove_list.AddDatas( domain_regexes )
        
        self._match_subdomains.setChecked( url_domain_mask.match_subdomains )
        self._keep_matched_subdomains.setChecked( url_domain_mask.keep_matched_subdomains )
        
        self._widget_mode.blockSignals( False )
        self._raw_domain_text_input.blockSignals( False )
        self._raw_domain_add_remove_list.blockSignals( False )
        self._domain_regex_add_remove_list.blockSignals( False )
        
        self._UpdateWidgetMode()
        
    
    def UpdateSizePolicyGubbins( self ):
        
        self._UpdateSizePolicy()
        
    
