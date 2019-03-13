from . import ClientConstants as CC
from . import ClientDefaults
from . import ClientGUIListBoxes
import collections
from . import HydrusConstants as HC
import os
import random
from . import TestController
import time
import unittest
import wx
from . import HydrusGlobals as HG

def DoClick( click, panel, do_delayed_ok_afterwards = False ):
    
    wx.QueueEvent( panel, click )
    
    if do_delayed_ok_afterwards:
        
        HG.test_controller.CallLaterWXSafe( panel, 1, PressKeyOnFocusedWindow, wx.WXK_RETURN )
        
    
    wx.YieldIfNeeded()
    
    time.sleep( 0.1 )
    
def GetAllClickableIndices( panel ):
    
    click = wx.MouseEvent( wx.wxEVT_LEFT_DOWN )
    
    current_y = 5
    
    click.SetX( 10 )
    click.SetY( current_y )
    
    all_clickable_indices = {}
    
    while panel._GetIndexUnderMouse( click ) is not None:
        
        index = panel._GetIndexUnderMouse( click )
        
        if index not in all_clickable_indices:
            
            all_clickable_indices[ index ] = current_y
            
        
        current_y += 5
        
        click.SetY( current_y )
        
    
    return all_clickable_indices
    
def PressKey( window, key ):
    
    window.SetFocus()
    
    uias = wx.UIActionSimulator()
    
    uias.Char( key )
    
def PressKeyOnFocusedWindow( key ):
    
    uias = wx.UIActionSimulator()
    
    uias.Char( key )
    
class TestListBoxes( unittest.TestCase ):
    
    def test_listbox_colour_options( self ):
        
        def wx_code():
            
            frame = TestController.TestFrame()
            
            try:
                
                initial_namespace_colours = { 'series' : ( 153, 101, 21 ), '' : ( 0, 111, 250 ), None : ( 114, 160, 193 ), 'creator' : ( 170, 0, 0 ) }
                
                panel = ClientGUIListBoxes.ListBoxTagsColourOptions( frame, initial_namespace_colours )
                
                frame.SetPanel( panel )
                
                self.assertEqual( panel.GetNamespaceColours(), initial_namespace_colours )
                
                #
                
                new_namespace_colours = dict( initial_namespace_colours )
                new_namespace_colours[ 'character' ] = ( 0, 170, 0 )
                
                colour = wx.Colour( 0, 170, 0 )
                
                panel.SetNamespaceColour( 'character', colour )
                
                self.assertEqual( panel.GetNamespaceColours(), new_namespace_colours )
                
                #
                
                terms = set( panel._terms )
                ordered_terms = list( panel._ordered_terms )
                
                self.assertEqual( len( terms ), len( ordered_terms ) )
                
                #
                
                all_clickable_indices = GetAllClickableIndices( panel )
                
                self.assertEqual( len( list(all_clickable_indices.keys()) ), len( terms ) )
                self.assertEqual( set( all_clickable_indices.keys() ), set( range( len( list(all_clickable_indices.keys()) ) ) ) )
                
                #
                
                for ( index, y ) in list(all_clickable_indices.items()):
                    
                    click = wx.MouseEvent( wx.wxEVT_LEFT_DOWN )
                    
                    click.SetX( 10 )
                    click.SetY( y )
                    
                    DoClick( click, panel )
                    
                    self.assertEqual( panel.GetSelectedNamespaceColours(), dict( [ ordered_terms[ index ] ] ) )
                    
                
                #
                
                current_y = 5
                
                click = wx.MouseEvent( wx.wxEVT_LEFT_DOWN )
                
                click.SetX( 10 )
                click.SetY( current_y )
                
                while panel._GetIndexUnderMouse( click ) is not None:
                    
                    current_y += 5
                    
                    click.SetY( current_y )
                    
                
                DoClick( click, panel )
                
                self.assertEqual( panel.GetSelectedNamespaceColours(), {} )
                
                #
                
                
                
                if len( list(all_clickable_indices.keys()) ) > 2:
                    
                    indices = random.sample( list(all_clickable_indices.keys()), len( list(all_clickable_indices.keys()) ) - 1 )
                    
                    for index in indices:
                        
                        click = wx.MouseEvent( wx.wxEVT_LEFT_DOWN )
                        
                        click.SetControlDown( True )
                        
                        click.SetX( 10 )
                        click.SetY( all_clickable_indices[ index ] )
                        
                        DoClick( click, panel )
                        
                    
                    expected_selected_terms = [ ordered_terms[ index ] for index in indices ]
                    
                    self.assertEqual( panel.GetSelectedNamespaceColours(), dict( expected_selected_terms ) )
                    
                
                #
                
                random_index = random.choice( list(all_clickable_indices.keys()) )
                
                while ordered_terms[ random_index ][0] in panel.PROTECTED_TERMS:
                    
                    random_index = random.choice( list(all_clickable_indices.keys()) )
                    
                
                del new_namespace_colours[ ordered_terms[ random_index ][0] ]
                
                # select nothing
                
                current_y = 5
                
                click = wx.MouseEvent( wx.wxEVT_LEFT_DOWN )
                
                click.SetX( 10 )
                click.SetY( current_y )
                
                while panel._GetIndexUnderMouse( click ) is not None:
                    
                    current_y += 5
                    
                    click.SetY( current_y )
                    
                
                DoClick( click, panel )
                
                # select the random index
                
                click = wx.MouseEvent( wx.wxEVT_LEFT_DOWN )
                
                click.SetX( 10 )
                click.SetY( all_clickable_indices[ random_index ] )
                
                DoClick( click, panel )
                
                # now double-click to activate and hence remove
                
                doubleclick = wx.MouseEvent( wx.wxEVT_LEFT_DCLICK )
                
                doubleclick.SetX( 5 )
                doubleclick.SetY( all_clickable_indices[ random_index ] )
                
                DoClick( doubleclick, panel, do_delayed_ok_afterwards = True )
                
                self.assertEqual( panel.GetNamespaceColours(), new_namespace_colours )
                
            finally:
                
                frame.DestroyLater()
                
            
        
        HG.test_controller.CallBlockingToWX( HG.test_controller.win, wx_code )
        
    
