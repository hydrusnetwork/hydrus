from qtpy import QtCore as QC

from hydrus.core import HydrusNumbers

my_qt_locale = QC.QLocale()

# TODO: Doing this in a fake `fr_FR` locale (space separator, maybe unicode?) seems to mess up some autocomplete dropdown taglist spacing stuff and breaks system predicate parsing

def ToHumanInt( num ):
    
    try:
        
        num = int( num )
        
    except Exception as e:
        
        return 'unknown'
        
    
    # remember we cannot trust process-wide C-based 'locale', which mpv stomps on
    
    text = my_qt_locale.toString( num )
    
    return text
    

def engage_locale_hook( do_it: bool ):
    
    if do_it:
        
        HydrusNumbers.ToHumanInt = ToHumanInt
        
    else:
        
        HydrusNumbers.ToHumanInt = HydrusNumbers.BaseToHumanInt
        
    
