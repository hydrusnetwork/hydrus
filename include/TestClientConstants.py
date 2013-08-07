import ClientConstants as CC
import collections
import HydrusConstants as HC
import os
import TestConstants
import unittest

class TestFunctions( unittest.TestCase ):
    
    def test_multipart( self ):
        
        hash = '5a1ba880a043e6207dca5f5407089fb0a0b0a588c8a6cd6a2807d173f59223d9'.decode( 'hex' )
        
        fields = []
        
        fields.append( ( 'sub', CC.FIELD_TEXT, 'subject' ) )
        fields.append( ( 'com', CC.FIELD_COMMENT, u'\u269COP is a fag' ) )
        fields.append( ( 'pass', CC.FIELD_PASSWORD, '123456' ) )
        fields.append( ( 'recaptcha', CC.FIELD_VERIFICATION_RECAPTCHA, 'reticulating splines' ) )
        fields.append( ( 'resto', CC.FIELD_THREAD_ID, '1000000' ) )
        fields.append( ( 'spoiler/on', CC.FIELD_CHECKBOX, True ) )
        fields.append( ( 'upfile', CC.FIELD_FILE, ( hash, HC.IMAGE_GIF, TestConstants.tinest_gif ) ) )
        
        result = CC.GenerateDumpMultipartFormDataCTAndBody( fields )
        
        expected_result = ('multipart/form-data; boundary=----------AaB03x', '------------AaB03x\r\nContent-Type: application/octet-stream\r\nContent-Disposition: form-data; name="sub"\r\n\r\nsubject\r\n------------AaB03x\r\nContent-Type: application/octet-stream\r\nContent-Disposition: form-data; name="com"\r\n\r\n\xe2\x9a\x9cOP is a fag\r\n------------AaB03x\r\nContent-Type: application/octet-stream\r\nContent-Disposition: form-data; name="pass"\r\n\r\n123456\r\n------------AaB03x\r\nContent-Type: application/octet-stream\r\nContent-Disposition: form-data; name="recaptcha"\r\n\r\nreticulating splines\r\n------------AaB03x\r\nContent-Type: application/octet-stream\r\nContent-Disposition: form-data; name="resto"\r\n\r\n1000000\r\n------------AaB03x\r\nContent-Type: application/octet-stream\r\nContent-Disposition: form-data; name="spoiler"\r\n\r\non\r\n------------AaB03x\r\nContent-Type: image/gif\r\nContent-Disposition: form-data; name="upfile"; filename="5a1ba880a043e6207dca5f5407089fb0a0b0a588c8a6cd6a2807d173f59223d9.gif"\r\n\r\nGIF89a\x01\x00\x01\x00\x00\xff\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x00;\r\n------------AaB03x--\r\n')
        
        self.assertEqual( result, expected_result )
        
        #
        
        fields = {}
        
        fields[ 'act' ] = 'do_login'
        fields[ 'id' ] = 'token'
        fields[ 'pin' ] = 'pin'
        fields[ 'long_login' ] = 'yes'
        fields[ 'random_unicode' ] = u'\u269C'
        
        result = CC.GenerateMultipartFormDataCTAndBodyFromDict( fields )
        
        expected_result = ('multipart/form-data; boundary=----------AaB03x', '------------AaB03x\r\nContent-Type: application/octet-stream\r\nContent-Disposition: form-data; name="long_login"\r\n\r\nyes\r\n------------AaB03x\r\nContent-Type: application/octet-stream\r\nContent-Disposition: form-data; name="random_unicode"\r\n\r\n\xe2\x9a\x9c\r\n------------AaB03x\r\nContent-Type: application/octet-stream\r\nContent-Disposition: form-data; name="id"\r\n\r\ntoken\r\n------------AaB03x\r\nContent-Type: application/octet-stream\r\nContent-Disposition: form-data; name="pin"\r\n\r\npin\r\n------------AaB03x\r\nContent-Type: application/octet-stream\r\nContent-Disposition: form-data; name="act"\r\n\r\ndo_login\r\n------------AaB03x--\r\n')
        
        self.assertEqual( result, expected_result )
        
    