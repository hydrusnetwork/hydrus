import BaseHTTPServer
import ClientConstants as CC
import Cookie
import hashlib
import httplib
import HydrusAudioHandling
import HydrusConstants as HC
import HydrusDocumentHandling
import HydrusExceptions
import HydrusFileHandling
import HydrusFlashHandling
import HydrusImageHandling
import HydrusServerAMP
import HydrusServerResources
import HydrusVideoHandling
import os
import random
import ServerConstants as SC
import SocketServer
import traceback
import urllib
import wx
import yaml
from twisted.internet import reactor, defer
from twisted.internet.protocol import ServerFactory
from twisted.internet.threads import deferToThread
from twisted.protocols import amp
from twisted.web.server import Request, Site, NOT_DONE_YET
from twisted.web.resource import Resource
from twisted.web.static import File as FileResource, NoRangeStaticProducer

eris = '''<html><head><title>hydrus</title></head><body><pre>
                         <font color="red">8888  8888888</font>
                  <font color="red">888888888888888888888888</font>
               <font color="red">8888</font>:::<font color="red">8888888888888888888888888</font>
             <font color="red">8888</font>::::::<font color="red">8888888888888888888888888888</font>
            <font color="red">88</font>::::::::<font color="red">888</font>:::<font color="red">8888888888888888888888888</font>
          <font color="red">88888888</font>::::<font color="red">8</font>:::::::::::<font color="red">88888888888888888888</font>
        <font color="red">888 8</font>::<font color="red">888888</font>::::::::::::::::::<font color="red">88888888888   888</font>
           <font color="red">88</font>::::<font color="red">88888888</font>::::<font color="gray">m</font>::::::::::<font color="red">88888888888    8</font>
         <font color="red">888888888888888888</font>:<font color="gray">M</font>:::::::::::<font color="red">8888888888888</font>
        <font color="red">88888888888888888888</font>::::::::::::<font color="gray">M</font><font color="red">88888888888888</font>
        <font color="red">8888888888888888888888</font>:::::::::<font color="gray">M</font><font color="red">8888888888888888</font>
         <font color="red">8888888888888888888888</font>:::::::<font color="gray">M</font><font color="red">888888888888888888</font>
        <font color="red">8888888888888888</font>::<font color="red">88888</font>::::::<font color="gray">M</font><font color="red">88888888888888888888</font>
      <font color="red">88888888888888888</font>:::<font color="red">88888</font>:::::<font color="gray">M</font><font color="red">888888888888888   8888</font>
     <font color="red">88888888888888888</font>:::<font color="red">88888</font>::::<font color="gray">M</font>::<font color="black">;o</font><font color="maroon">*</font><font color="green">M</font><font color="maroon">*</font><font color="black">o;</font><font color="red">888888888    88</font>
    <font color="red">88888888888888888</font>:::<font color="red">8888</font>:::::<font color="gray">M</font>:::::::::::<font color="red">88888888    8</font>
   <font color="red">88888888888888888</font>::::<font color="red">88</font>::::::<font color="gray">M</font>:<font color="gray">;</font>:::::::::::<font color="red">888888888</font>
  <font color="red">8888888888888888888</font>:::<font color="red">8</font>::::::<font color="gray">M</font>::<font color="gray">aAa</font>::::::::<font color="gray">M</font><font color="red">8888888888       8</font>
  <font color="red">88   8888888888</font>::<font color="red">88</font>::::<font color="red">8</font>::::<font color="gray">M</font>:::::::::::::<font color="red">888888888888888 8888</font>
 <font color="red">88  88888888888</font>:::<font color="red">8</font>:::::::::<font color="gray">M</font>::::::::::;::<font color="red">88</font><font color="black">:</font><font color="red">88888888888888888</font>
 <font color="red">8  8888888888888</font>:::::::::::<font color="gray">M</font>::<font color="violet">&quot;@@@@@@@&quot;</font>::::<font color="red">8</font><font color="gray">w</font><font color="red">8888888888888888</font>
  <font color="red">88888888888</font>:<font color="red">888</font>::::::::::<font color="gray">M</font>:::::<font color="violet">&quot;@a@&quot;</font>:::::<font color="gray">M</font><font color="red">8</font><font color="gray">i</font><font color="red">888888888888888</font>
 <font color="red">8888888888</font>::::<font color="red">88</font>:::::::::<font color="gray">M</font><font color="red">88</font>:::::::::::::<font color="gray">M</font><font color="red">88</font><font color="gray">z</font><font color="red">88888888888888888</font>
<font color="red">8888888888</font>:::::<font color="red">8</font>:::::::::<font color="gray">M</font><font color="red">88888</font>:::::::::<font color="gray">MM</font><font color="red">888</font><font color="gray">!</font><font color="red">888888888888888888</font>
<font color="red">888888888</font>:::::<font color="red">8</font>:::::::::<font color="gray">M</font><font color="red">8888888</font><font color="gray">MAmmmAMVMM</font><font color="red">888</font><font color="gray">*</font><font color="red">88888888   88888888</font>
<font color="red">888888</font> <font color="gray">M</font>:::::::::::::::<font color="gray">M</font><font color="red">888888888</font>:::::::<font color="gray">MM</font><font color="red">88888888888888   8888888</font>
<font color="red">8888</font>   <font color="gray">M</font>::::::::::::::<font color="gray">M</font><font color="red">88888888888</font>::::::<font color="gray">MM</font><font color="red">888888888888888    88888</font>
 <font color="red">888</font>   <font color="gray">M</font>:::::::::::::<font color="gray">M</font><font color="red">8888888888888</font><font color="gray">M</font>:::::<font color="gray">mM</font><font color="red">888888888888888    8888</font>
  <font color="red">888</font>  <font color="gray">M</font>::::::::::::<font color="gray">M</font><font color="red">8888</font>:<font color="red">888888888888</font>::::<font color="gray">m</font>::<font color="gray">Mm</font><font color="red">88888 888888   8888</font>
   <font color="red">88</font>  <font color="gray">M</font>::::::::::::<font color="red">8888</font>:<font color="red">88888888888888888</font>::::::<font color="gray">Mm</font><font color="red">8   88888   888</font>
   <font color="red">88</font>  <font color="gray">M</font>::::::::::<font color="red">8888</font><font color="gray">M</font>::<font color="red">88888</font>::<font color="red">888888888888</font>:::::::<font color="gray">Mm</font><font color="red">88888    88</font>
   <font color="red">8</font>   <font color="gray">MM</font>::::::::<font color="red">8888</font><font color="gray">M</font>:::<font color="red">8888</font>:::::<font color="red">888888888888</font>::::::::<font color="gray">Mm</font><font color="red">8     4</font>
       <font color="red">8</font><font color="gray">M</font>:::::::<font color="red">8888</font><font color="gray">M</font>:::::<font color="red">888</font>:::::::<font color="red">88</font>:::<font color="red">8888888</font>::::::::<font color="gray">Mm</font>    <font color="red">2</font>
      <font color="red">88</font><font color="gray">MM</font>:::::<font color="red">8888</font><font color="gray">M</font>:::::::<font color="red">88</font>::::::::<font color="red">8</font>:::::<font color="red">888888</font>:::<font color="gray">M</font>:::::<font color="gray">M</font>
     <font color="red">8888</font><font color="gray">M</font>:::::<font color="red">888</font><font color="gray">MM</font>::::::::<font color="red">8</font>:::::::::::<font color="gray">M</font>::::<font color="red">8888</font>::::<font color="gray">M</font>::::<font color="gray">M</font>
    <font color="red">88888</font><font color="gray">M</font>:::::<font color="red">88</font>:<font color="gray">M</font>::::::::::<font color="red">8</font>:::::::::::<font color="gray">M</font>:::<font color="red">8888</font>::::::<font color="gray">M</font>::<font color="gray">M</font>
   <font color="red">88 888</font><font color="gray">MM</font>:::<font color="red">888</font>:<font color="gray">M</font>:::::::::::::::::::::::<font color="gray">M</font>:<font color="red">8888</font>:::::::::<font color="gray">M</font>:
   <font color="red">8 88888</font><font color="gray">M</font>:::<font color="red">88</font>::<font color="gray">M</font>:::::::::::::::::::::::<font color="gray">MM</font>:<font color="red">88</font>::::::::::::<font color="gray">M</font>
     <font color="red">88888</font><font color="gray">M</font>:::<font color="red">88</font>::<font color="gray">M</font>::::::::::<font color="thistle">*88*</font>::::::::::<font color="gray">M</font>:<font color="red">88</font>::::::::::::::<font color="gray">M</font>
    <font color="red">888888</font><font color="gray">M</font>:::<font color="red">88</font>::<font color="gray">M</font>:::::::::<font color="thistle">88@@88</font>:::::::::<font color="gray">M</font>::<font color="red">88</font>::::::::::::::<font color="gray">M</font>
    <font color="red">888888</font><font color="gray">MM</font>::<font color="red">88</font>::<font color="gray">MM</font>::::::::<font color="thistle">88@@88</font>:::::::::<font color="gray">M</font>:::<font color="red">8</font>::::::::::::::<font color="thistle">*8</font>
    <font color="red">88888</font>  <font color="gray">M</font>:::<font color="red">8</font>::<font color="gray">MM</font>:::::::::<font color="thistle">*88*</font>::::::::::<font color="gray">M</font>:::::::::::::::::<font color="thistle">88@@</font>
    <font color="red">8888</font>   <font color="gray">MM</font>::::::<font color="gray">MM</font>:::::::::::::::::::::<font color="gray">MM</font>:::::::::::::::::<font color="thistle">88@@</font>
     <font color="red">888</font>    <font color="gray">M</font>:::::::<font color="gray">MM</font>:::::::::::::::::::<font color="gray">MM</font>::<font color="gray">M</font>::::::::::::::::<font color="thistle">*8</font>
     <font color="red">888</font>    <font color="gray">MM</font>:::::::<font color="gray">MMM</font>::::::::::::::::<font color="gray">MM</font>:::<font color="gray">MM</font>:::::::::::::::<font color="gray">M</font>
      <font color="red">88</font>     <font color="gray">M</font>::::::::<font color="gray">MMMM</font>:::::::::::<font color="gray">MMMM</font>:::::<font color="gray">MM</font>::::::::::::<font color="gray">MM</font>
       <font color="red">88</font>    <font color="gray">MM</font>:::::::::<font color="gray">MMMMMMMMMMMMMMM</font>::::::::<font color="gray">MMM</font>::::::::<font color="gray">MMM</font>
        <font color="red">88</font>    <font color="gray">MM</font>::::::::::::<font color="gray">MMMMMMM</font>::::::::::::::<font color="gray">MMMMMMMMMM</font>
         <font color="red">88   8</font><font color="gray">MM</font>::::::::::::::::::::::::::::::::::<font color="gray">MMMMMM</font>
          <font color="red">8   88</font><font color="gray">MM</font>::::::::::::::::::::::<font color="gray">M</font>:::<font color="gray">M</font>::::::::<font color="gray">MM</font>
              <font color="red">888</font><font color="gray">MM</font>::::::::::::::::::<font color="gray">MM</font>::::::<font color="gray">MM</font>::::::<font color="gray">MM</font>
             <font color="red">88888</font><font color="gray">MM</font>:::::::::::::::<font color="gray">MMM</font>:::::::<font color="gray">mM</font>:::::<font color="gray">MM</font>
             <font color="red">888888</font><font color="gray">MM</font>:::::::::::::<font color="gray">MMM</font>:::::::::<font color="gray">MMM</font>:::<font color="gray">M</font>
            <font color="red">88888888</font><font color="gray">MM</font>:::::::::::<font color="gray">MMM</font>:::::::::::<font color="gray">MM</font>:::<font color="gray">M</font>
           <font color="red">88 8888888</font><font color="gray">M</font>:::::::::<font color="gray">MMM</font>::::::::::::::<font color="gray">M</font>:::<font color="gray">M</font>
           <font color="red">8  888888</font> <font color="gray">M</font>:::::::<font color="gray">MM</font>:::::::::::::::::<font color="gray">M</font>:::<font color="gray">M</font>:
              <font color="red">888888</font> <font color="gray">M</font>::::::<font color="gray">M</font>:::::::::::::::::::<font color="gray">M</font>:::<font color="gray">MM</font>
             <font color="red">888888</font>  <font color="gray">M</font>:::::<font color="gray">M</font>::::::::::::::::::::::::<font color="gray">M</font>:<font color="gray">M</font>
             <font color="red">888888</font>  <font color="gray">M</font>:::::<font color="gray">M</font>:::::::::<font color="gray">@</font>::::::::::::::<font color="gray">M</font>::<font color="gray">M</font>
             <font color="red">88888</font>   <font color="gray">M</font>::::::::::::::<font color="gray">@@</font>:::::::::::::::<font color="gray">M</font>::<font color="gray">M</font>
            <font color="red">88888</font>   <font color="gray">M</font>::::::::::::::<font color="gray">@@@</font>::::::::::::::::<font color="gray">M</font>::<font color="gray">M</font>
           <font color="red">88888</font>   <font color="gray">M</font>:::::::::::::::<font color="gray">@@</font>::::::::::::::::::<font color="gray">M</font>::<font color="gray">M</font>
          <font color="red">88888</font>   <font color="gray">M</font>:::::<font color="gray">m</font>::::::::::<font color="gray">@</font>::::::::::<font color="gray">Mm</font>:::::::<font color="gray">M</font>:::<font color="gray">M</font>
          <font color="red">8888</font>   <font color="gray">M</font>:::::<font color="gray">M</font>:::::::::::::::::::::::<font color="gray">MM</font>:::::::<font color="gray">M</font>:::<font color="gray">M</font>
         <font color="red">8888</font>   <font color="gray">M</font>:::::<font color="gray">M</font>:::::::::::::::::::::::<font color="gray">MMM</font>::::::::<font color="gray">M</font>:::<font color="gray">M</font>
        <font color="red">888</font>    <font color="gray">M</font>:::::<font color="gray">Mm</font>::::::::::::::::::::::<font color="gray">MMM</font>:::::::::<font color="gray">M</font>::::<font color="gray">M</font>
      <font color="red">8888</font>    <font color="gray">MM</font>::::<font color="gray">Mm</font>:::::::::::::::::::::<font color="gray">MMMM</font>:::::::::<font color="gray">m</font>::<font color="gray">m</font>:::<font color="gray">M</font>
     <font color="red">888</font>      <font color="gray">M</font>:::::<font color="gray">M</font>::::::::::::::::::::<font color="gray">MMM</font>::::::::::::<font color="gray">M</font>::<font color="gray">mm</font>:::<font color="gray">M</font>
  <font color="red">8888</font>       <font color="gray">MM</font>:::::::::::::::::::::::::<font color="gray">MM</font>:::::::::::::<font color="gray">mM</font>::<font color="gray">MM</font>:::<font color="gray">M</font>:
             <font color="gray">M</font>:::::::::::::::::::::::::<font color="gray">M</font>:::::::::::::::<font color="gray">mM</font>::<font color="gray">MM</font>:::<font color="gray">Mm</font>
            <font color="gray">MM</font>::::::<font color="gray">m</font>:::::::::::::::::::::::::::::::::::<font color="gray">M</font>::<font color="gray">MM</font>:::<font color="gray">MM</font>
            <font color="gray">M</font>::::::::<font color="gray">M</font>:::::::::::::::::::::::::::::::::::<font color="gray">M</font>::<font color="gray">M</font>:::<font color="gray">MM</font>
           <font color="gray">MM</font>:::::::::<font color="gray">M</font>:::::::::::::<font color="gray">M</font>:::::::::::::::::::::<font color="gray">M</font>:<font color="gray">M</font>:::<font color="gray">MM</font>
           <font color="gray">M</font>:::::::::::<font color="gray">M</font><font color="maroon">88</font>:::::::::<font color="gray">M</font>:::::::::::::::::::::::<font color="gray">MM</font>::<font color="gray">MMM</font> 
           <font color="gray">M</font>::::::::::::<font color="maroon">8888888888</font><font color="gray">M</font>::::::::::::::::::::::::<font color="gray">MM</font>::<font color="gray">MM</font> 
           <font color="gray">M</font>:::::::::::::<font color="maroon">88888888</font><font color="gray">M</font>:::::::::::::::::::::::::<font color="gray">M</font>::<font color="gray">MM</font>
           <font color="gray">M</font>::::::::::::::<font color="maroon">888888</font><font color="gray">M</font>:::::::::::::::::::::::::<font color="gray">M</font>::<font color="gray">MM</font>
           <font color="gray">M</font>:::::::::::::::<font color="maroon">88888</font><font color="gray">M</font>:::::::::::::::::::::::::<font color="gray">M</font>:<font color="gray">MM</font>
           <font color="gray">M</font>:::::::::::::::::<font color="maroon">88</font><font color="gray">M</font>::::::::::::::::::::::::::<font color="gray">MMM</font>
           <font color="gray">M</font>:::::::::::::::::::<font color="gray">M</font>::::::::::::::::::::::::::<font color="gray">MMM</font>
           <font color="gray">MM</font>:::::::::::::::::<font color="gray">M</font>::::::::::::::::::::::::::<font color="gray">MMM</font>
            <font color="gray">M</font>:::::::::::::::::<font color="gray">M</font>::::::::::::::::::::::::::<font color="gray">MMM</font>
            <font color="gray">MM</font>:::::::::::::::<font color="gray">M</font>::::::::::::::::::::::::::<font color="gray">MMM</font>
             <font color="gray">M</font>:::::::::::::::<font color="gray">M</font>:::::::::::::::::::::::::<font color="gray">MMM</font>
             <font color="gray">MM</font>:::::::::::::<font color="gray">M</font>:::::::::::::::::::::::::<font color="gray">MMM</font>
              <font color="gray">M</font>:::::::::::::<font color="gray">M</font>::::::::::::::::::::::::<font color="gray">MMM</font>
              <font color="gray">MM</font>:::::::::::<font color="gray">M</font>::::::::::::::::::::::::<font color="gray">MMM</font>
               <font color="gray">M</font>:::::::::::<font color="gray">M</font>:::::::::::::::::::::::<font color="gray">MMM</font>
               <font color="gray">MM</font>:::::::::<font color="gray">M</font>:::::::::::::::::::::::<font color="gray">MMM</font>
                <font color="gray">M</font>:::::::::<font color="gray">M</font>::::::::::::::::::::::<font color="gray">MMM</font>
                <font color="gray">MM</font>:::::::<font color="gray">M</font>::::::::::::::::::::::<font color="gray">MMM</font>
                 <font color="gray">MM</font>::::::<font color="gray">M</font>:::::::::::::::::::::<font color="gray">MMM</font>
                 <font color="gray">MM</font>:::::<font color="gray">M</font>:::::::::::::::::::::<font color="gray">MMM</font>
                  <font color="gray">MM</font>::::<font color="gray">M</font>::::::::::::::::::::<font color="gray">MMM</font> 
                  <font color="gray">MM</font>:::<font color="gray">M</font>::::::::::::::::::::<font color="gray">MMM</font>
                   <font color="gray">MM</font>::<font color="gray">M</font>:::::::::::::::::::<font color="gray">MMM</font>              THIS IS THE HYDRUS SERVER ADMIN SERVICE, VERSION ''' + HC.u( HC.SOFTWARE_VERSION ) + '''
                   <font color="gray">MM</font>:<font color="gray">M</font>:::::::::::::::::::<font color="gray">MMM</font>
                    <font color="gray">MMM</font>::::::::::::::::::<font color="gray">MMM</font>
                    <font color="gray">MM</font>::::::::::::::::::<font color="gray">MMM</font>
                     <font color="gray">M</font>:::::::::::::::::<font color="gray">MMM</font>
                    <font color="gray">MM</font>::::::::::::::::<font color="gray">MMM</font>
                    <font color="gray">MM</font>:::::::::::::::<font color="gray">MMM</font>
                    <font color="gray">MM</font>::::<font color="gray">M</font>:::::::::<font color="gray">MMM</font>:
                    <font color="gray">mMM</font>::::<font color="gray">MM</font>:::::::<font color="gray">MMMM</font>
                     <font color="gray">MMM</font>:::::::::::<font color="gray">MMM</font>:<font color="gray">M</font>
                     <font color="gray">mMM</font>:::<font color="gray">M</font>:::::::<font color="gray">M</font>:<font color="gray">M</font>:<font color="gray">M</font>
                      <font color="gray">MM</font>::<font color="gray">MMMM</font>:::::::<font color="gray">M</font>:<font color="gray">M</font>
                      <font color="gray">MM</font>::<font color="gray">MMM</font>::::::::<font color="gray">M</font>:<font color="gray">M</font>
                      <font color="gray">mMM</font>::<font color="gray">MM</font>::::::::<font color="gray">M</font>:<font color="gray">M</font>
                       <font color="gray">MM</font>::<font color="gray">MM</font>:::::::::<font color="gray">M</font>:<font color="gray">M</font>
                       <font color="gray">MM</font>::<font color="gray">MM</font>::::::::::<font color="gray">M</font>:<font color="gray">m</font>
                       <font color="gray">MM</font>:::<font color="gray">M</font>:::::::::::<font color="gray">MM</font>
                       <font color="gray">MMM</font>:::::::::::::::<font color="gray">M</font>:
                       <font color="gray">MMM</font>:::::::::::::::<font color="gray">M</font>:
                       <font color="gray">MMM</font>::::::::::::::::<font color="gray">M</font>
                       <font color="gray">MMM</font>::::::::::::::::<font color="gray">M</font>
                       <font color="gray">MMM</font>::::::::::::::::<font color="gray">Mm</font>
                        <font color="gray">MM</font>::::::::::::::::<font color="gray">MM</font>
                        <font color="gray">MMM</font>:::::::::::::::<font color="gray">MM</font>
                        <font color="gray">MMM</font>:::::::::::::::<font color="gray">MM</font>
                        <font color="gray">MMM</font>:::::::::::::::<font color="gray">MM</font>
                        <font color="gray">MMM</font>:::::::::::::::<font color="gray">MM</font>
                         <font color="gray">MM</font>::::::::::::::<font color="gray">MMM</font>
                         <font color="gray">MMM</font>:::::::::::::<font color="gray">MM</font>
                         <font color="gray">MMM</font>:::::::::::::<font color="gray">MM</font>
                         <font color="gray">MMM</font>::::::::::::<font color="gray">MM</font>
                          <font color="gray">MM</font>::::::::::::<font color="gray">MM</font>
                          <font color="gray">MM</font>::::::::::::<font color="gray">MM</font>
                          <font color="gray">MM</font>:::::::::::<font color="gray">MM</font>
                          <font color="gray">MMM</font>::::::::::<font color="gray">MM</font>
                          <font color="gray">MMM</font>::::::::::<font color="gray">MM</font>
                           <font color="gray">MM</font>:::::::::<font color="gray">MM</font>
                           <font color="gray">MMM</font>::::::::<font color="gray">MM</font>
                           <font color="gray">MMM</font>::::::::<font color="gray">MM</font>
                            <font color="gray">MM</font>::::::::<font color="gray">MM</font>
                            <font color="gray">MMM</font>::::::<font color="gray">MM</font>
                            <font color="gray">MMM</font>::::::<font color="gray">MM</font>
                             <font color="gray">MM</font>::::::<font color="gray">MM</font>
                             <font color="gray">MM</font>::::::<font color="gray">MM</font>
                              <font color="gray">MM</font>:::::<font color="gray">MM</font>
                              <font color="gray">MM</font>:::::<font color="gray">MM</font>:
                              <font color="gray">MM</font>:::::<font color="gray">M</font>:<font color="gray">M</font>
                              <font color="gray">MM</font>:::::<font color="gray">M</font>:<font color="gray">M</font>
                              :<font color="gray">M</font>::::::<font color="gray">M</font>:
                             <font color="gray">M</font>:<font color="gray">M</font>:::::::<font color="gray">M</font>
                            <font color="gray">M</font>:::<font color="gray">M</font>::::::<font color="gray">M</font>
                           <font color="gray">M</font>::::<font color="gray">M</font>::::::<font color="gray">M</font>
                          <font color="gray">M</font>:::::<font color="gray">M</font>:::::::<font color="gray">M</font>
                         <font color="gray">M</font>::::::<font color="gray">MM</font>:::::::<font color="gray">M</font>
                         <font color="gray">M</font>:::::::<font color="gray">M</font>::::::::<font color="gray">M</font>
                         <font color="gray">M;</font>:<font color="gray">;</font>::::<font color="gray">M</font>:::::::::<font color="gray">M</font>
                         <font color="gray">M</font>:<font color="gray">m</font>:<font color="gray">;</font>:::<font color="gray">M</font>::::::::::<font color="gray">M</font>
                         <font color="gray">MM</font>:<font color="gray">m</font>:<font color="gray">m</font>::<font color="gray">M</font>::::::::<font color="gray">;</font>:<font color="gray">M</font>
                          <font color="gray">MM</font>:<font color="gray">m</font>::<font color="gray">MM</font>:::::::<font color="gray">;</font>:<font color="gray">;M</font>
                           <font color="gray">MM</font>::<font color="gray">MMM</font>::::::<font color="gray">;</font>:<font color="gray">m</font>:<font color="gray">M</font>
                            <font color="gray">MMMM MM</font>::::<font color="gray">m</font>:<font color="gray">m</font>:<font color="gray">MM</font>
                                  <font color="gray">MM</font>::::<font color="gray">m</font>:<font color="gray">MM</font>
                                   <font color="gray">MM</font>::::<font color="gray">MM</font>
                                    <font color="gray">MM</font>::<font color="gray">MM</font>
                                     <font color="gray">MMMM</font>
</pre></body></html>'''

silly_responses = []
silly_responses.append( u'\ufeff\u25d5 \u203f\u203f \u25d5' )
silly_responses.append( u"The disco. We go to disco. My body's sweaty from the MDMA inside it. I like to dance with you. You grab my ponytail. It is greasy with Germanic juices that I put inside my hair. Disco, we are the disco. I have a mesh shirt. My leather pants show off my sausage inside it. I grind your body, then we eat ecstasy and have Special K inside of the bathroom. It's a men's bathroom, but no one cares that you come inside because they know that inside it we do lots of drugs. And I will share them if the bouncer lets me go into the bathroom with you, and then we go home. We have efficient sex. And then I realize you're not that hot anymore because I've blown a load and I don't have ecstasy inside of my bloodstream. So I make sandwich. It has hazelnuts, bread, and some jelly that I got from the supermarket. It tastes pretty good, but it probably tastes better because my taste buds have ecstasy inside them. And then I go up to the bathroom, and you're wearing one of my shirts; that isn't cool. You didn't even ask. I met you earlier the evening; you're not my girlfriend, you're just girl that I have sex with. We probably won't do this again because I realize that your hair is frazzled and it probably has extensions. It's not your real hair, and that's kind of gross 'cause who knows where it came from." )
silly_responses.append( u'\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\n\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2588\u2588\u2588\u2588\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2588\u2588\u2588\u2588\u2591\u2591\u2591\u2591\u2591\u2591\u2591\n\u2591\u2591\u2591\u2591\u2591\u2588\u2588\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2588\u2588\u2591\u2591\u2591\u2591\u2591\n\u2591\u2591\u2591\u2588\u2588\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2588\u2588\u2591\u2591\u2591\n\u2591\u2591\u2588\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2588\u2591\u2591\n\u2591\u2588\u2591\u2591\u2588\u2588\u2588\u2588\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2588\u2588\u2588\u2588\u2588\u2588\u2591\u2591\u2591\u2591\u2591\u2588\u2591\n\u2588\u2591\u2591\u2588\u2591\u2591\u2591\u2588\u2588\u2591\u2591\u2591\u2591\u2591\u2591\u2588\u2591\u2591\u2591\u2591\u2588\u2588\u2588\u2591\u2591\u2591\u2591\u2591\u2588\n\u2588\u2591\u2588\u2591\u2591\u2591\u2591\u2591\u2591\u2588\u2591\u2591\u2591\u2591\u2591\u2588\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2588\u2591\u2591\u2591\u2591\u2588\n\u2588\u2591\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2591\u2591\u2591\u2591\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2591\u2591\u2591\u2591\u2588\n\u2588\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2588\n\u2588\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2588\n\u2588\u2591\u2591\u2591\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2591\u2591\u2591\u2591\u2588\n\u2591\u2588\u2591\u2591\u2591\u2588\u2593\u2593\u2593\u2593\u2593\u2593\u2593\u2593\u2588\u2588\u2588\u2588\u2588\u2593\u2593\u2593\u2588\u2591\u2591\u2591\u2591\u2588\u2591\n\u2591\u2588\u2591\u2591\u2591\u2591\u2588\u2593\u2593\u2593\u2593\u2593\u2588\u2588\u2591\u2591\u2591\u2591\u2588\u2588\u2593\u2588\u2588\u2591\u2591\u2591\u2591\u2588\u2591\n\u2591\u2591\u2588\u2591\u2591\u2591\u2591\u2588\u2588\u2593\u2593\u2588\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2592\u2588\u2588\u2591\u2591\u2591\u2591\u2588\u2591\u2591\n\u2591\u2591\u2591\u2588\u2588\u2591\u2591\u2591\u2591\u2588\u2588\u2591\u2591\u2591\u2591\u2591\u2591\u2592\u2588\u2588\u2591\u2591\u2591\u2591\u2588\u2588\u2591\u2591\u2591\n\u2591\u2591\u2591\u2591\u2591\u2588\u2588\u2591\u2591\u2591\u2591\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2591\u2591\u2591\u2591\u2588\u2588\u2591\u2591\u2591\u2591\u2591\n\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2588\u2588\u2588\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2588\u2588\u2588\u2591\u2591\u2591\u2591\u2591\u2591\u2591\n\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591' )
silly_responses.append( u' (\u25cb\u220b\u25cb)\n\u250f(  \u7537 )\u251b\n  \uff0f    \u2513\nA mystery' )
silly_responses.append( u'\u25b2\n\u25b2 \u25b2' )
silly_responses.append( u'\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2584\u2584\u2584\u2584\u2584\u2584\u2584\u2584\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\n\u2591\u2591\u2591\u2591\u2591\u2584\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2584\u2591\u2591\u2591\u2591\u2591\n\u2591\u2591\u2584\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2584\u2591\u2591\u2591\n\u2591\u2591\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2584\u2591\u2591\n\u2591\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2591\u2591\n\u2591\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2591\u2591\n\u2591\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2591\u2591\n\u2591\u2591\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2580\u2580\u2580\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2591\u2591\n\u2591\u2591\u2580\u2588\u2588\u2588\u2588\u2588\u2580\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2580\u2588\u2588\u2588\u2588\u2588\u2591\u2591\u2591\n\u2591\u2591\u2591\u2580\u2580\u2588\u2588\u2588\u2591\u2591\u2588\u2591\u2591\u2591\u2588\u2591\u2591\u2588\u2588\u2588\u2580\u2591\u2591\u2591\u2591\n\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2588\u2591\u2591\u2591\u2591\u2580\u2591\u2591\u2591\u2591\u2588\u2591\u2591\u2591\u2591\u2591\u2591\u2591\n\u2591\u2591\u2591\u2591\u2591\u2591\u2584\u2588\u2588\u2584\u2591\u2591\u2580\u2580\u2591\u2584\u2588\u2580\u2584\u2591\u2591\u2591\u2591\u2591\u2591\n\u2591\u2591\u2591\u2591\u2584\u2580\u2591\u2580\u2584\u2580\u2580\u2588\u2588\u2588\u2580\u2580\u2584\u2580\u2591\u2580\u2584\u2591\u2591\u2591\u2591\n\u2591\u2591\u2591\u2591\u2588\u2591\u2591\u2591\u2591\u2580\u2584\u2580\u2591\u2580\u2584\u2580\u2591\u2584\u2591\u2591\u2588\u2591\u2591\u2591\u2591\n\u2591\u2591\u2591\u2591\u2588\u2591\u2588\u2591\u2591\u2591\u2588\u2591\u2591\u2591\u2588\u2591\u2591\u2588\u2591\u2591\u2588\u2591\u2591\u2591\u2591\n\u2591\u2591\u2591\u2591\u2588\u2591\u2588\u2591\u2591\u2591\u2591\u2580\u2584\u2580\u2580\u2580\u2580\u2588\u2591\u2591\u2588\u2591\u2591\u2591\u2591\n\u2591\u2591\u2591\u2591\u2588\u2591\u2588\u2591\u2591\u2591\u2591\u2591\u2584\u2591\u2591\u2584\u2588\u2588\u2584\u2584\u2580\u2591\u2591\u2591\u2591\n\u2591\u2591\u2591\u2591\u2588\u2591\u2588\u2591\u2591\u2591\u2591\u2591\u2584\u2591\u2591\u2588\u2588\u2588\u2588\u2591\u2591\u2591\u2591\u2591\u2591\n\u2591\u2591\u2591\u2591\u2588\u2588\u2588\u2584\u2591\u2591\u2591\u2584\u2584\u2584\u2591\u2591\u2591\u2584\u2580\u2591\u2591\u2591\u2591\u2591\u2591\n\u2591\u2591\u2591\u2591\u2591\u2580\u2580\u2588\u2580\u2580\u2580\u2591\u2584\u2591\u2580\u2580\u2580\u2588\u2591\u2591\u2591\u2591\u2591\u2591\u2591\n\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2588\u2591\u2591\u2591\u2591\u2588\u2591\u2591\u2591\u2591\u2588\u2591\u2591\u2591\u2591\u2591\u2591\u2591\n\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2588\u2591\u2591\u2591\u2591\u2588\u2591\u2591\u2591\u2591\u2588\u2591\u2591\u2591\u2591\u2591\u2591\u2591\n\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2588\u2584\u2584\u2584\u2584\u2588\u2584\u2584\u2584\u2584\u2588\u2591\u2591\u2591\u2591\u2591\u2591\u2591\n\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2588\u2588\u2588\u2588\u2588\u2588\u2584\u2584\u2584\u2584\u2580\u2591\u2591\u2591\u2591\u2591\u2591\u2591\n\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2580\u2580\u2580\u2580\u2580\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591' )
silly_responses.append( u'\u0ca0_\u0ca0' )
silly_responses.append( u'(\xb4_\u309d`)' )
silly_responses.append( u'\u3000\u3000\u3000\u3000\u3000\u3000\u3000\u3000\u3000\uff0f\u2312\u30fd\n\u3000\u3000\u3000\u2282\u4e8c\u4e8c\u4e8c\uff08\u3000\uff3e\u03c9\uff3e\uff09\u4e8c\u2283\n\u3000\u3000\u3000\u3000\u3000\u3000\u3000\u3000|\u3000\u3000\u3000 / \u3000\u3000\u3000\u3000\u3000\u3000BU-N\n\u3000\u3000\u3000\u3000 \u3000\u3000\u3000 \uff08\u3000\u30fd\u30ce\n\u3000\u3000\u3000\u3000\u3000\u3000\u3000\u3000 \u30ce>\u30ce\u3000\n\u3000\u3000\u3000\u3000 \u4e09\u3000\u3000\u30ec\u30ec' )
silly_responses.append( u'Gen.\n\nThis is wheat.\n\nA blue bud is put out at the cruel\nwinter, it is stepped many times, it\nexpands strongly and straight, and it becomes\nwheat that bears the fruit.' )
silly_responses.append( u'I\'m a hardcore fan with FF8, so many times I would even try to escape reality with lucid dreaming, I would be in Balamb Garden where I would often train with Zell in the training center and help Selphie with the Garden Festival, but one day as I was talking to Selphie, we went to my dormitory for a private talk. She immediately said, "You know you could live with us forever.." I gave her a confused look and she continued, "We understand that you live on earth and you REALLY wish to live here". I then said "How..How did you know?" She then giggled and said "Because we\'ve been watching you, silly!" This was a dream come true and I almost cried right there. She then said, "I talked with Headmaster Cid and he agreed that you would be PERFECT for SeeD, you just have to do...one thing". She then held my hand and looked deep into my eyes and said "...You have to kill yourself for the transfer to work correctly." I then gave her some questions, "How long do I have before the deal expires?" She then said "Cid said 3 months.." I added by saying "What\'s the most painless way?..." She giggled again, "Suicide will require pain buuut...if you want it quick...Get a gun and a nice shot to the head works, but make sure you put the gun in your mouth for better accuracy, If you can\'t afford a gun, jump off a very VERY tall building, I wouldn\'t recommend pills because it\'s not a guaranteed method of dying, you could just get really really sick and be hospitalized." I then agreed and she gave me a kiss on the forehead, "I know this will be tough but once it\'s over and done, you\'ll get to live here!" I then woke up and this was last week and purchased a gun (I\'ll even post the gun with receipt, if you want) But Friday I might actually kill myself because that dream just felt too fucking real to be fake and my life isn\'t doing so grand.' )
silly_responses.append( u'Consider this: A pack of wild Niggers.\nSavage, slavering Niggers nearing your white home. Trampling your white lawn. Raping your white daughter.\nAnd you can\'t do shit since they\'re savages. The Nigger leader grabs your wife and fucks her with his shaman stick.\nThe primal Niggers finally dominate your household. They watch barbaric shows on TV and you are forced to be their slave.\nSuch is the downfall of White Man.' )
silly_responses.append( u'\uFF37\uFF2F\uFF35\uFF2C\uFF24 \uFF39\uFF2F\uFF35 \uFF2C\uFF29\uFF2B\uFF25 \uFF34\uFF2F \uFF22\uFF25 \uFF2D\uFF21\uFF2B\uFF29\uFF2E\uFF27 \uFF26\uFF35\uFF23\uFF2B' )
silly_responses.append( u'Israelis expect that thousands  http://www.canadagooses.co.uk/kensington-parka-c-15.html of missiles might be fired at their cities by Iran\u2019s  http://www.monclersole.com/moncler-jackets-womens-c-3.html clients in Lebanon and the Gaza Strip, while U.S. forces might be attacked in Afghanistan, Iraq or in the Persian http://www.monclersnorge.com Gulf. But China has proven to be a continuous http://www.monclerfactoryoutlets.com  complication. On trade, Mr. Obama has repeatedly pressured China to  http://www.monclerstyle2011.comallow its currency to http://www.doudounemoncleralpin.com  appreciate, only to be told by Beijing that China is doing enough. On national security, China http://www.canadagooseexpedition.ca   is extending its claims in the region, worrying U.S. partners and allies who both depend on China for trade but fear it  http://www.imonclerdoudoune.com  may exercise its power in more forceful ways. Toomey acknowledged http://www.monclerfronline.com   that both sides have \u201Ca ways to go\u201D in reaching an http://www.monclersole.com/  agreement, but told Fox News: \u201CI am not giving up on getting something done. I think we http://www.monclerdoudounepascher2011.com/   still can, and http://www.monclerdoudounepascher2011.com  I am going to do everything to achieve that.\u201DAlso appearing on the program  http://www.canadiangoosejacket.ca was Representative James Clyburn, a South Carolina  http://www.canadagooseolinestore.com Democrat, who said he remained \u201Cvery hopeful\u201D that both sides will http://www.moncler2u.co.uk   reach a compromise before their deadline, now  http://www.monclerbransondoudoune.fr  less than two weeks away.' )
silly_responses.append( u'i am a heron. i haev a long neck and i pick fish out of the water w/ my beak. if you dont repost this comment on 10 other pages i will fly into your kitchen tonight and make a mess of your pots and pans' )
silly_responses.append( u'The maritine avains  lack order and are wrought with decent among their kind .\r\n to promote forms of good tidings , appeasement and fair boon . \r\n\r\n One tender note in sequence of two or \r\n a a golden coin tender in sequence of one .\r\n\r\n Forfeiting and abandoning of these are signs of the above mentioned.' )
silly_responses.append( u'It is the VIPPER beatdown!\r\n Kick that dokyun around!\r\n Bury him six feet under the ground!\r\n Ain\'t no QUALITY but VIP QUALITY in this town.' )
silly_responses.append( u'IAmA heron. i ahev a long neck and i pick fish out of the water w/ my beak. if you dont repost this comment on 10 other pages i will fly into your kitchen tonight and make a mess of your pots and pans' )

CLIENT_ROOT_MESSAGE = '''<html>
    <head>
        <title>hydrus client</title>
    </head>
    <body>
        <p>This hydrus client uses software version ''' + HC.u( HC.SOFTWARE_VERSION ) + ''' and network version ''' + HC.u( HC.NETWORK_VERSION ) + '''.</p>
        <p>It only serves requests from 127.0.0.1.</p>
    </body>
</html>'''

ROOT_MESSAGE_BEGIN = '''<html>
    <head>
        <title>hydrus service</title>
    </head>
    <body>
        <p>This hydrus service uses software version ''' + HC.u( HC.SOFTWARE_VERSION ) + ''' and network version ''' + HC.u( HC.NETWORK_VERSION ) + '''.</p>
        <p>'''

ROOT_MESSAGE_END = '''</p>
    </body>
</html>'''
'''
    def do_OPTIONS( self ):
        
        service_type = self._service_identifier.GetType()
        
        if service_type == HC.LOCAL_FILE and ip != '127.0.0.1': raise HydrusExceptions.ForbiddenException( 'Only local access allowed!' )
        
        request = ParseHTTPRequest( self.path )
        
        allowed = [ 'OPTIONS' ]
        
        if ( service_type, HC.GET, request ) in HC.ALLOWED_REQUESTS: allowed.append( 'GET' )
        if ( service_type, HC.POST, request ) in HC.ALLOWED_REQUESTS: allowed.append( 'POST' )
        
        self.send_response( 200 )
        
        self.send_header( 'Allow', ','.join( allowed ) )
        self.end_headers()
        
    '''
class HydrusRequest( Request ):
    
    def __init__( self, *args, **kwargs ):
        
        Request.__init__( self, *args, **kwargs )
        
        self.is_hydrus_client = True
        self.hydrus_args = None
        self.hydrus_response_context = None
        self.hydrus_request_data_usage = 0
        
    
class HydrusRequestRestricted( HydrusRequest ):
    
    def __init__( self, *args, **kwargs ):
        
        HydrusRequest.__init__( self, *args, **kwargs )
        
        self.hydrus_account = None
        
    
class HydrusService( Site ):
    
    def __init__( self, service_identifier, message ):
        
        self._service_identifier = service_identifier
        self._message = message
        
        root = self._InitRoot()
        
        Site.__init__( self, root )
        
        self.requestFactory = HydrusRequest
        
    
    def _InitRoot( self ):
        
        root = Resource()
        
        root.putChild( '', HydrusServerResources.HydrusResourceWelcome( self._service_identifier, self._message ) )
        root.putChild( 'favicon.ico', HydrusServerResources.hydrus_favicon )
        
        return root
        

class HydrusServiceLocal( HydrusService ):
    
    def _InitRoot( self ):
        
        root = HydrusService._InitRoot( self )
        
        root.putChild( 'file', HydrusServerResources.HydrusResourceCommandFileLocal( self._service_identifier ) )
        root.putChild( 'thumbnail', HydrusServerResources.HydrusResourceCommandThumbnailLocal( self._service_identifier ) )
        
        return root
        
    
class HydrusServiceRestricted( HydrusService ):
    
    def __init__( self, service_identifier, message ):
        
        HydrusService.__init__( self, service_identifier, message )
        
        self.requestFactory = HydrusRequestRestricted
        
    
    def _InitRoot( self ):
        
        root = HydrusService._InitRoot( self )
        
        root.putChild( 'access_key', HydrusServerResources.HydrusResourceCommandAccessKey( self._service_identifier ) )
        root.putChild( 'session_key', HydrusServerResources.HydrusResourceCommandSessionKey( self._service_identifier ) )
        
        root.putChild( 'account', HydrusServerResources.HydrusResourceCommandRestrictedAccount( self._service_identifier ) )
        root.putChild( 'account_info', HydrusServerResources.HydrusResourceCommandRestrictedAccountInfo( self._service_identifier ) )
        root.putChild( 'account_types', HydrusServerResources.HydrusResourceCommandRestrictedAccountTypes( self._service_identifier ) )
        root.putChild( 'registration_keys', HydrusServerResources.HydrusResourceCommandRestrictedRegistrationKeys( self._service_identifier ) )
        root.putChild( 'stats', HydrusServerResources.HydrusResourceCommandRestrictedStats( self._service_identifier ) )
        
        return root
        
    
class HydrusServiceAdmin( HydrusServiceRestricted ):
    
    def _InitRoot( self ):
        
        root = HydrusServiceRestricted._InitRoot( self )
        
        root.putChild( 'backup', HydrusServerResources.HydrusResourceCommandRestrictedBackup( self._service_identifier ) )
        root.putChild( 'init', HydrusServerResources.HydrusResourceCommandInit( self._service_identifier ) )
        root.putChild( 'services', HydrusServerResources.HydrusResourceCommandRestrictedServices( self._service_identifier ) )
        
        return root
        
    
class HydrusServiceRepository( HydrusServiceRestricted ):
    
    def _InitRoot( self ):
        
        root = HydrusServiceRestricted._InitRoot( self )
        
        root.putChild( 'news', HydrusServerResources.HydrusResourceCommandRestrictedNews( self._service_identifier ) )
        root.putChild( 'num_petitions', HydrusServerResources.HydrusResourceCommandRestrictedNumPetitions( self._service_identifier ) )
        root.putChild( 'petition', HydrusServerResources.HydrusResourceCommandRestrictedPetition( self._service_identifier ) )
        root.putChild( 'update', HydrusServerResources.HydrusResourceCommandRestrictedUpdate( self._service_identifier ) )
        
        return root
        
    
class HydrusServiceRepositoryFile( HydrusServiceRepository ):
    
    def _InitRoot( self ):
        
        root = HydrusServiceRepository._InitRoot( self )
        
        root.putChild( 'file', HydrusServerResources.HydrusResourceCommandRestrictedFileRepository( self._service_identifier ) )
        root.putChild( 'ip', HydrusServerResources.HydrusResourceCommandRestrictedIP( self._service_identifier ) )
        root.putChild( 'thumbnail', HydrusServerResources.HydrusResourceCommandRestrictedThumbnailRepository( self._service_identifier ) )
        
        return root
        
    
class HydrusServiceRepositoryTag( HydrusServiceRepository ): pass

class MessagingClientProtocol( amp.AMP ):
    
    def im_message( self, identifier_from, name_from, identifier_to, name_to, message ):
        
        # send these args on to the messaging manager, which will:
          # start a context, if needed
          # spawn a gui prompt/window to start a convo, if needed
          # queue the message through to the appropriate context
          # maybe the context should spam up to the ui, prob in a pubsub; whatever.
        
        # IT SHOULD DO NOTHING ELSE
        
        pass
        
    HydrusServerAMP.IMMessageClient.responder( im_message )
    
    def connectionLost( self, reason ):
        
        # report to ui that the connection is lost
        
        pass
        
    
class MessagingServiceProtocol( amp.AMP ):
    
    def __init__( self ):
        
        amp.AMP.__init__()
        
        self._identifier = None
        self._name = None
        
    
    def im_login_persistent( self, session_key ):
        
        ( identifier, name ) = session_manager.GetIdentity( session_key )
        
        self._identifier = identifier
        self._name = name
        
        self.factory.AddConnection( True, self._identifier, self._name, self )
        
        return {}
        
    HydrusServerAMP.IMLoginPersistent.responder( im_login_persistent )
    
    def im_login_temporary( self, identifier, name ):
        
        self._identifier = identifier
        self._name = name
        
        self.factory.AddConnection( False, self._identifier, self._name, self )
        
    HydrusServerAMP.IMLoginTemporary.responder( im_login_temporary )
    
    def im_message( self, identifier_to, name_to, message ):
        
        if self._identifier is None or self._name is None:
            
            raise Exception() # who the hell are you? pls temp login
            
        
        connection = self.factory.GetConnection( identifier_to, name_to )
        
        # get connection for identifier_to from larger, failing appropriately
        # if we fail, we should probably log the _to out, right?
        
        connection.callRemote( IMMessageClient, identifier_from = self._identifier, name_from = self._name, identifier_to = identifier_to, name_to = name_to, message = message )
        # this returns a deferred, so set up a 'return {}' deferred.
        
        return {}
        
    HydrusServerAMP.IMMessageServer.responder( im_message )
    
    def im_session_key( self, access_key, name ):
        
        # verify access_key
        # access_key should give identifier
        
        session_key = session_manager.AddSession( identifier, name )
        # this'll save to db, so make it deferred
        
        return { 'session_key' : session_key }
        
    HydrusServerAMP.IMSessionKey.responder( im_session_key )
    
    def m_public_key( self, identifier ):
        
        # this will not be useful until we have normal messaging sorted
        
        public_key = 'public key'
        
        return { 'public_key' : public_key }
        
    HydrusServerAMP.MPublicKey.responder( m_public_key )
    
    def connectionLost( self, reason ):
        
        if self._identifier is not None: self.factory.RemoveConnection( self._identifier, self._name )
        
    
class MessagingServiceFactory( ServerFactory ):
    
    protocol = MessagingServiceProtocol
    
    def __init__( self, service_identifier ):
        
        self._service_identifier = service_identifier
        
        self._persistent_connections = collections.defaultdict( dict )
        self._temporary_connections = collections.defaultdict( dict )
        
    
    def AddConnection( self, persistent, identifier, name, connection ):
        
        if persistent: self._persistent_connections[ identifier ][ name ] = connection
        else: self._temporary_connections[ identifier ][ name ] = connection
        
    
    def GetConnection( self, identifier, name ):
        
        if name in self._persistent_connections[ identifier ]: return self._persistent_connections[ identifier ][ name ]
        elif name in self._temporary_connections[ identifier ]: return self._temporary_connections[ identifier ][ name ]
        else:
            
            raise Exception() # make this better, obviously
            
        
    
    def GetOnlineNames( self, identifier ): return self._persistent_connections[ identifier ].keys()
    
    def RemoveConnection( self, identifier, name ):
        
        if name in self._temporary_connections[ identifier ]: del self._temporary_connections[ identifier ][ name ]
        elif name in self._persistent_connections[ identifier ]: del self._persistent_connections[ identifier ][ name ]
        
