from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

# this stuff results generally in the 'Expanding' policy, which means:
    # we can go to min size if there is competition
    # otherwise we want normal size plus a share of any spare
# shrinkable is basically a polite version of fixed:
    # we can go to min size if there is competition
    # otherwise we want normal size
FLAGS_EXPAND_PERPENDICULAR = 0
FLAGS_EXPAND_DEPTH = 1
FLAGS_EXPAND_BOTH_WAYS = 2
FLAGS_EXPAND_SHRINKABLE = 3
FLAGS_EXPAND_BOTH_WAYS_DEPTH_NON_SHRINKABLE = 2

EXPAND_FLAGS_TO_POLICIES = {
    FLAGS_EXPAND_PERPENDICULAR : (
        QW.QSizePolicy.Policy.Expanding, # perpendicular
        QW.QSizePolicy.Policy.Fixed # depth
    ),
    FLAGS_EXPAND_DEPTH : (
        QW.QSizePolicy.Policy.Fixed,
        QW.QSizePolicy.Policy.Expanding
    ),
    FLAGS_EXPAND_BOTH_WAYS : (
        QW.QSizePolicy.Policy.Expanding,
        QW.QSizePolicy.Policy.Expanding
    ),
    FLAGS_EXPAND_BOTH_WAYS_DEPTH_NON_SHRINKABLE : (
        QW.QSizePolicy.Policy.Expanding,
        QW.QSizePolicy.Policy.MinimumExpanding # sizeHint is now minsize. will expand to take extra
    ),
    FLAGS_EXPAND_SHRINKABLE : (
        QW.QSizePolicy.Policy.Maximum,
        QW.QSizePolicy.Policy.Maximum
    ),
}

FLAGS_ALIGN_CENTER = 0
FLAGS_ALIGN_RIGHT = 1
FLAGS_ALIGN_CENTER_PERPENDICULAR = 2

# TODO: The objective of this file is to replace the ancient QP.AddToLayout with a cleaner and more Qt-native thing
# we are collapsing the number of flags flying around and differentiating widgets from layouts
# one big difference between wx and Qt, which I never got around to cleaning up, is that QLayouts don't have expand policy. many 'expand perp' things were bodged. we fix this here with different calls
# I still have to do some gridbox stuff. there's tuple hacks in there; we'll try and clean it up

# old gubbins
'''
FLAGS_NONE = 0

FLAGS_CENTER = 3

FLAGS_EXPAND_PERPENDICULAR = 4
FLAGS_EXPAND_BOTH_WAYS = 5
FLAGS_EXPAND_PERPENDICULAR_BUT_BOTH_WAYS_LATER = 6

FLAGS_EXPAND_BOTH_WAYS_POLITE = 7
FLAGS_EXPAND_BOTH_WAYS_SHY = 8

FLAGS_EXPAND_SIZER_PERPENDICULAR = 10
FLAGS_EXPAND_SIZER_BOTH_WAYS = 11

FLAGS_ON_LEFT = 12
FLAGS_ON_RIGHT = 13

FLAGS_CENTER_PERPENDICULAR = 15 # TODO: Collapse all this into something meaningful. We use this guy like 260+ times and it is basically a useless stub let's go
FLAGS_SIZER_CENTER = 16
FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH = 17
'''

def AddLayoutToLayout( layout: QW.QBoxLayout | QW.QGridLayout, sub_layout: QW.QBoxLayout | QW.QGridLayout, align_flag: int | None = None ):
    
    sub_layout.setContentsMargins( 0, 0, 0, 0 )
    
    layout.addLayout( sub_layout )
    
    if align_flag is not None:
        
        DoAlign( layout, sub_layout, align_flag )
        
    

def AddWidgetToLayout( layout: QW.QBoxLayout | QW.QGridLayout, widget: QW.QWidget, expand_flag: int, align_flag: int | None = None ):
    
    ( perpendicular_policy, depth_policy ) = EXPAND_FLAGS_TO_POLICIES[ expand_flag ]
    
    if isinstance( layout, QW.QHBoxLayout ):
        
        widget.setSizePolicy( depth_policy, perpendicular_policy )
        
    else:
        
        widget.setSizePolicy( perpendicular_policy, depth_policy )
        
    
    layout.addWidget( widget )
    
    if align_flag is not None:
        
        DoAlign( layout, widget, align_flag )
        
    

def DoAlign( layout: QW.QLayout, item: QW.QLayout | QW.QWidget, align_flag: int ):
    
        if align_flag == FLAGS_ALIGN_CENTER:
            
            layout.setAlignment( item, QC.Qt.AlignmentFlag.AlignCenter )
            
        elif align_flag == FLAGS_ALIGN_RIGHT:
            
            layout.setAlignment( item, QC.Qt.AlignmentFlag.AlignRight )
            
        elif align_flag == FLAGS_ALIGN_CENTER_PERPENDICULAR:
            
            if isinstance( layout, QW.QHBoxLayout ):
                
                layout.setAlignment( item, QC.Qt.AlignmentFlag.AlignVCenter )
                
            else:
                
                layout.setAlignment( item, QC.Qt.AlignmentFlag.AlignHCenter )
                
            
        
    
