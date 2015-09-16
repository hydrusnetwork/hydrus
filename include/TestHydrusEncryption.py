import ClientConstants as CC
import ClientGUIDialogs
import collections
import HydrusConstants as HC
import HydrusData
import HydrusEncryption
import os
import potr
import TestConstants
import unittest
import HydrusGlobals

class Catcher():
    
    def __init__( self ):
        
        self._last_write = ''
        
    
    def GetLastWrite( self ):
        
        l_w = self._last_write
        
        self._last_write = ''
        
        return l_w
        
    
    def write( self, data ): self._last_write = data
    
class TestIM( unittest.TestCase ):
    
    def test_otr( self ):
        
        alice = HydrusData.GenerateKey().encode( 'hex' )
        bob = HydrusData.GenerateKey().encode( 'hex' )
        
        alice_privkey_hex = '0000000000808000000000000000944834d12b2ad788d34743102266aa9d87fc180577f977c2b201799a4149ca598819ff59591254cb312d1ad23d791a9355cd423c438cb0bc7000bb33377cf73be6fc900705c250d2bdba3287c8e545faf0653e44e66aefffda6e445947ff98cac7c02cb4911f9f527a6f25cf6b8aae4af2909b3c077b80bb00000014afb936c2487a867db906015d755f158e5bf38c1d00000080345d40c8fc329e254ef4be5efa7e1dc20484b982394d09fece366ef598db1a29f4b63160728de57058f405903ded01d6359242656f1e8c02a0b5c67f5d09496486f2f9f005abcec1470888bd7f31dbee8b0ce94b31ed36437dc2446b38829ba08927329bd1ecec0de1d2cd409f840ed2478cdf154a12f79815b29e75ea4a2e0f000000807731a186f55afcdebc34aba5a10130e5eafac0d0067c50f49be494a463271b34a657114c9b69c4fbe30302259feafe75f091b5c5670c7193e256bd7a5be2f3daee2d1a8bc4e04eec891cd6c4591edf40e5cbf8f3e1ca985a9b01d13768ea7160761af475b0097878376dbac6b1ce5b101fb1dd7da354e739791895caba52f14c000000146497dca1a62f1039a0ce8bfc99984de1cc5a9848'
        bob_privkey_hex = '00000000008080000000000000741dae82c8c9a55a7f2a5eb9e4db0b3e5990de5df5d7e2a0dab221a8e1e8b92d99f70387458088215836ed1c42c157640578da801120aa50c180c7d9b4e72205b863ecbd6f43e2efbca04d4c6b1b184fd57bda231445ad4a5e9b7ada27ddd9b24c2cfdba77858e76072b5e87a0a4eb91608ffea42ded252bd700000014ec380fdb62ad0248746142c58654403f665c9701000000806e1aaee6b00ee1a77927b5c7a28089eb9bc147e7688091aeeff7de7c3fa98498748d0744f328c230991e9d8031b704d9fc2a87206d62e2f3b1c30b3a370a237368b04dbe826978a232666be84db52c398700d8e2dbc4f5cabc8bd1270f429ea54247a087fdedfac723bf8b1aa4cfad664646a51d97f96a7dffaef0c24d90a5f5000000803dff456298b4fdc4a08599790341f274c8ea7685101cd2d42fb90a34034f71ca0b9b1f2074ec41e1282bd6a3b74d855c82fcea411485da83f784ca15deb3b5372b544ae84fa6f9a8cd470bc8ebd8e60135098e4a4b608d2aea395b2053311f0802a6db0836e25170ce8e5670579f63445688113b93f8597e88d28f03c020c77800000014a762254ce091c8abf6acd0945e32436abbc1b3f2'
        
        alice_privkey = HydrusEncryption.LoadOTRKey( alice_privkey_hex.decode( 'hex' ) )
        bob_privkey = HydrusEncryption.LoadOTRKey( bob_privkey_hex.decode( 'hex' ) )
        
        #alice_privkey = HydrusEncryption.GenerateOTRKey()
        #bob_privkey = HydrusEncryption.GenerateOTRKey()
        
        alice_account = HydrusEncryption.HydrusOTRAccount( alice, alice_privkey, {} )
        bob_account = HydrusEncryption.HydrusOTRAccount( bob, bob_privkey, {} )
        
        alice_context = HydrusEncryption.HydrusOTRContext( alice_account, bob )
        bob_context = HydrusEncryption.HydrusOTRContext( bob_account, alice )
        
        catcher = Catcher()
        
        #
        
        self.assertEqual( alice_context.state, potr.context.STATE_PLAINTEXT )
        self.assertEqual( bob_context.state, potr.context.STATE_PLAINTEXT )
        
        m = alice_context.sendMessage( potr.context.FRAGMENT_SEND_ALL, '' )
        
        res = bob_context.receiveMessage( m, catcher )
        
        m = catcher.GetLastWrite()
        
        res = alice_context.receiveMessage( m, catcher )
        
        m = catcher.GetLastWrite()
        
        res = bob_context.receiveMessage( m, catcher )
        
        m = catcher.GetLastWrite()
        
        res = alice_context.receiveMessage( m, catcher )
        
        m = catcher.GetLastWrite()
        
        res = bob_context.receiveMessage( m, catcher )
        
        self.assertEqual( alice_context.state, potr.context.STATE_ENCRYPTED )
        self.assertEqual( bob_context.state, potr.context.STATE_ENCRYPTED )
        
        self.assertEqual( bob_privkey.getPublicPayload(), alice_context.getCurrentKey().getPublicPayload() )
        self.assertEqual( alice_privkey.getPublicPayload(), bob_context.getCurrentKey().getPublicPayload() )
        
        #
        
        self.assertEqual( alice_context.getCurrentTrust(), None )
        
        alice_context.setCurrentTrust( 'verified' )
        
        self.assertEqual( alice_context.getCurrentTrust(), 'verified' )
        
        [ ( args, kwargs ) ] = HydrusGlobals.test_controller.GetWrite( 'otr_trusts' )
        
        self.assertEqual( args, ( alice, { bob : { alice_context.getCurrentKey().cfingerprint() : 'verified' } } ) )
        
        self.assertEqual( bob_context.getCurrentTrust(), None )
        
        bob_context.setCurrentTrust( 'verified' )
        
        self.assertEqual( bob_context.getCurrentTrust(), 'verified' )
        
        [ ( args, kwargs ) ] = HydrusGlobals.test_controller.GetWrite( 'otr_trusts' )
        
        self.assertEqual( args, ( bob, { alice : { bob_context.getCurrentKey().cfingerprint() : 'verified' } } ) )
        
        #
        
        m = alice_context.sendMessage( potr.context.FRAGMENT_SEND_ALL, 'hello bob', appdata = catcher )
        
        m = catcher.GetLastWrite()
        
        res = bob_context.receiveMessage( m, catcher )
        
        ( message, gumpf ) = res
        
        self.assertEqual( message, 'hello bob' )
        
        #
        
        m = bob_context.sendMessage( potr.context.FRAGMENT_SEND_ALL, 'hello alice', appdata = catcher )
        
        m = catcher.GetLastWrite()
        
        res = alice_context.receiveMessage( m, catcher )
        
        ( message, gumpf ) = res
        
        self.assertEqual( message, 'hello alice' )
        
