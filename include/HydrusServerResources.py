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
import HydrusNATPunch
import HydrusImageHandling
import os
import random
import ServerConstants as SC
import SocketServer
import threading
import traceback
import urllib
import wx
import yaml
from twisted.internet import reactor, defer
from twisted.internet.threads import deferToThread
from twisted.web.server import Request, Site, NOT_DONE_YET
from twisted.web.resource import Resource
from twisted.web.static import File as FileResource, NoRangeStaticProducer
from twisted.python import log

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

def ParseFileArguments( path ):
    
    HydrusImageHandling.ConvertToPngIfBmp( path )
    
    hash = HydrusFileHandling.GetHashFromPath( path )
    
    try: ( size, mime, width, height, duration, num_frames, num_words ) = HydrusFileHandling.GetFileInfo( path, hash )
    except HydrusExceptions.SizeException: raise HydrusExceptions.ForbiddenException( 'File is of zero length!' )
    except HydrusExceptions.MimeException: raise HydrusExceptions.ForbiddenException( 'Filetype is not permitted!' )
    except Exception as e: raise HydrusExceptions.ForbiddenException( HC.u( e ) )
    
    args = {}
    
    args[ 'path' ] = path
    args[ 'hash' ] = hash
    args[ 'size' ] = size
    args[ 'mime' ] = mime
    
    if width is not None: args[ 'width' ] = width
    if height is not None: args[ 'height' ] = height
    if duration is not None: args[ 'duration' ] = duration
    if num_frames is not None: args[ 'num_frames' ] = num_frames
    if num_words is not None: args[ 'num_words' ] = num_words
    
    if mime in HC.IMAGES:
        
        try: thumbnail = HydrusFileHandling.GenerateThumbnail( path )
        except: raise HydrusExceptions.ForbiddenException( 'Could not generate thumbnail from that file.' )
        
        args[ 'thumbnail' ] = thumbnail
        
    
    return args
    
hydrus_favicon = FileResource( HC.STATIC_DIR + os.path.sep + 'hydrus.ico', defaultType = HC.IMAGE_ICON )

class HydrusResourceWelcome( Resource ):
    
    def __init__( self, service_identifier, message ):
        
        Resource.__init__( self )
        
        service_type = service_identifier.GetType()
        
        if service_type == HC.LOCAL_FILE: body = CLIENT_ROOT_MESSAGE
        else: body = ROOT_MESSAGE_BEGIN + message + ROOT_MESSAGE_END
        
        self._body = body.encode( 'utf-8' )
        
        self._server_version_string = HC.service_string_lookup[ service_type ] + '/' + str( HC.NETWORK_VERSION )
        

    def render_GET( self, request ):
        
        request.setHeader( 'Server', self._server_version_string )
        
        return self._body
        
    
class HydrusResourceCommand( Resource ):
    
    local_only = False
    
    def __init__( self, service_identifier ):
        
        Resource.__init__( self )
        
        self._service_identifier = service_identifier
        
        service_type = self._service_identifier.GetType()
        
        self._server_version_string = HC.service_string_lookup[ service_type ] + '/' + str( HC.NETWORK_VERSION )
        
    
    def _callbackCheckRestrictions( self, request ):
        
        self._checkUserAgent( request )
        
        self._checkLocal( request )
        
        return request
        
    
    def _callbackParseGETArgs( self, request ):
        
        hydrus_args = {}
        
        for name in request.args:
            
            values = request.args[ name ]
            
            value = values[0]
            
            if name in ( 'begin', 'expiry', 'lifetime', 'num', 'subject_account_id', 'service_type', 'service_port', 'since', 'timespan' ):
                
                try: hydrus_args[ name ] = int( value )
                except: raise HydrusExceptions.ForbiddenException( 'I was expecting to parse \'' + name + '\' as an integer, but it failed.' )
                
            elif name in ( 'access_key', 'title', 'subject_access_key', 'contact_key', 'hash', 'subject_hash', 'subject_tag', 'message_key' ):
                
                try: hydrus_args[ name ] = value.decode( 'hex' )
                except: raise HydrusExceptions.ForbiddenException( 'I was expecting to parse \'' + name + '\' as a hex-encoded string, but it failed.' )
                
            
        
        if 'subject_account_id' in hydrus_args: hydrus_args[ 'subject_identifier' ] = HC.AccountIdentifier( account_id = hydrus_args[ 'subject_account_id' ] )
        elif 'subject_access_key' in hydrus_args: hydrus_args[ 'subject_identifier' ] = HC.AccountIdentifier( access_key = hydrus_args[ 'subject_access_key' ] )
        elif 'subject_hash' in hydrus_args:
            
            if 'subject_tag' in hydrus_args: hydrus_args[ 'subject_identifier' ] = HC.AccountIdentifier( tag = hydrus_args[ 'subject_tag' ], hash = hydrus_args[ 'subject_hash' ] )
            else: hydrus_args[ 'subject_identifier' ] = HC.AccountIdentifier( hash = hydrus_args[ 'subject_hash' ] )
            
        
        request.hydrus_args = hydrus_args
        
        return request
        
    
    def _callbackParsePOSTArgs( self, request ):
        
        request.content.seek( 0 )
        
        if not request.requestHeaders.hasHeader( 'Content-Type' ): raise HydrusExceptions.ForbiddenException( 'No Content-Type header found!' )
        
        content_types = request.requestHeaders.getRawHeaders( 'Content-Type' )
        
        content_type = content_types[0]
        
        try: mime = HC.mime_enum_lookup[ content_type ]
        except: raise HydrusExceptions.ForbiddenException( 'Did not recognise Content-Type header!' )
        
        if mime == HC.APPLICATION_YAML:
            
            yaml_string = request.content.read()
            
            request.hydrus_request_data_usage += len( yaml_string )
            
            hydrus_args = yaml.safe_load( yaml_string )
            
        else:
            
            temp_path = HC.GetTempPath()
            
            with open( temp_path, 'wb' ) as f:
                
                block_size = 65536
                
                while True:
                    
                    block = request.content.read( block_size )
                    
                    if block == '': break
                    
                    f.write( block )
                    
                    request.hydrus_request_data_usage += len( block )
                    
                
            
            hydrus_args = ParseFileArguments( temp_path )
            
        
        request.hydrus_args = hydrus_args
        
        return request
        
    
    def _callbackRenderResponseContext( self, request ):
        
        response_context = request.hydrus_response_context
        
        status_code = response_context.GetStatusCode()
        
        request.setResponseCode( status_code )
        
        for ( k, v, kwargs ) in response_context.GetCookies(): request.addCookie( k, v, **kwargs )
        
        do_finish = True
        
        if response_context.HasBody():
            
            ( mime, body ) = response_context.GetMimeBody()
            
            content_type = HC.mime_string_lookup[ mime ]
            
            content_length = len( body )
            
            request.setHeader( 'Content-Type', content_type )
            request.setHeader( 'Content-Length', str( content_length ) )
            
            if type( body ) == unicode: body = body.encode( 'utf-8' )
            
            request.write( body )
            
        elif response_context.HasPath():
            
            path = response_context.GetPath()
            
            info = os.lstat( path )
            
            size = info[6]
            
            if response_context.IsYAML():
                
                mime = HC.APPLICATION_YAML
                
                content_type = HC.mime_string_lookup[ mime ]
                
            else:
                
                mime = HydrusFileHandling.GetMime( path )
                
                ( base, filename ) = os.path.split( path )
                
                content_type = HC.mime_string_lookup[ mime ] + '; ' + filename
                
            
            content_length = size
            
            request.setHeader( 'Content-Type', content_type )
            request.setHeader( 'Content-Length', str( content_length ) )
            
            fileObject = open( path, 'rb' )
            
            producer = NoRangeStaticProducer( request, fileObject )
            
            producer.start()
            
            do_finish = False
            
        else:
            
            content_length = 0
            
            request.setHeader( 'Content-Length', str( content_length ) )
            
        
        request.hydrus_request_data_usage += content_length
        
        self._recordDataUsage( request )
        
        if do_finish: request.finish()
        
    
    def _callbackDoGETJob( self, request ):
        
        def wrap_thread_result( response_context ):
            
            request.hydrus_response_context = response_context
            
            return request
            
        
        d = deferToThread( self._threadDoGETJob, request )
        
        d.addCallback( wrap_thread_result )
        
        return d
        
    
    def _callbackDoPOSTJob( self, request ):
        
        def wrap_thread_result( response_context ):
            
            request.hydrus_response_context = response_context
            
            return request
            
        
        d = deferToThread( self._threadDoPOSTJob, request )
        
        d.addCallback( wrap_thread_result )
        
        return d
        
    
    def _checkLocal( self, request ):
        
        if self.local_only and request.getClientIP() != '127.0.0.1': raise HydrusExceptions.ForbiddenException( 'Only local access allowed!' )
        
    
    def _checkUserAgent( self, request ):
        
        request.is_hydrus_user_agent = False
        
        if request.requestHeaders.hasHeader( 'User-Agent' ):
            
            user_agent_texts = request.requestHeaders.getRawHeaders( 'User-Agent' )
            
            user_agent_text = user_agent_texts[0]
            
            try:
                
                user_agents = user_agent_text.split( ' ' )
                
            except: return # crazy user agent string, so just assume not a hydrus client
            
            for user_agent in user_agents:
                
                if '/' in user_agent:
                    
                    ( client, network_version ) = user_agent.split( '/', 1 )
                    
                    if client == 'hydrus':
                        
                        request.is_hydrus_user_agent = True
                        
                        network_version = int( network_version )
                        
                        if network_version == HC.NETWORK_VERSION: return
                        else:
                            
                            if network_version < HC.NETWORK_VERSION: message = 'Your client is out of date; please download the latest release.'
                            else: message = 'This server is out of date; please ask its admin to update to the latest release.'
                            
                            raise HydrusExceptions.NetworkVersionException( 'Network version mismatch! This server\'s network version is ' + HC.u( HC.NETWORK_VERSION ) + ', whereas your client\'s is ' + HC.u( network_version ) + '! ' + message )
                            
                        
                    
                
            
        
    
    def _errbackHandleEmergencyError( self, failure, request ):
        
        print( failure.getTraceback() )
        
        try: request.write( failure.getTraceback() )
        except: pass
        
        try: request.finish()
        except: pass
        
    
    def _errbackHandleProcessingError( self, failure, request ):
        
        do_yaml = True
        
        try:
            
            # the error may have occured before user agent was set up!
            if not request.is_hydrus_user_agent: do_yaml = False
            
        except: pass
        
        if do_yaml:
            
            default_mime = HC.APPLICATION_YAML
            default_encoding = lambda x: yaml.safe_dump( HC.u( x ) )
            
        else:
            
            default_mime = HC.TEXT_HTML
            default_encoding = lambda x: HC.u( x )
            
        
        if failure.type == KeyError: response_context = HC.ResponseContext( 403, mime = default_mime, body = default_encoding( 'It appears one or more parameters required for that request were missing:' + os.linesep + failure.getTraceback() ) )
        elif failure.type == HydrusExceptions.PermissionException: response_context = HC.ResponseContext( 401, mime = default_mime, body = default_encoding( failure.value ) )
        elif failure.type == HydrusExceptions.ForbiddenException: response_context = HC.ResponseContext( 403, mime = default_mime, body = default_encoding( failure.value ) )
        elif failure.type == HydrusExceptions.NotFoundException: response_context = HC.ResponseContext( 404, mime = default_mime, body = default_encoding( failure.value ) )
        elif failure.type == HydrusExceptions.NetworkVersionException: response_context = HC.ResponseContext( 426, mime = default_mime, body = default_encoding( failure.value ) )
        elif failure.type == HydrusExceptions.SessionException: response_context = HC.ResponseContext( 403, mime = default_mime, body = default_encoding( failure.value ) )
        else:
            
            print( failure.getTraceback() )
            
            response_context = HC.ResponseContext( 500, mime = default_mime, body = default_encoding( 'The repository encountered an error it could not handle! Here is a dump of what happened, which will also be written to your client.log file. If it persists, please forward it to hydrus.admin@gmail.com:' + os.linesep + os.linesep + failure.getTraceback() ) )
            
        
        request.hydrus_response_context = response_context
        
        return request
        
    
    def _parseAccessKey( self, request ):
        
        if not request.requestHeaders.hasHeader( 'Hydrus-Key' ): raise HydrusExceptions.PermissionException( 'No hydrus key header found!' )
        
        hex_keys = request.requestHeaders.getRawHeaders( 'Hydrus-Key' )
        
        hex_key = hex_keys[0]
        
        try: access_key = hex_key.decode( 'hex' )
        except: raise HydrusExceptions.ForbiddenException( 'Could not parse the hydrus key!' )
        
        return access_key
        
    
    def _recordDataUsage( self, request ): return request
    
    def _threadDoGETJob( self, request ): raise HydrusExceptions.NotFoundException( 'This service does not support that request!' )
    
    def _threadDoPOSTJob( self, request ): raise HydrusExceptions.NotFoundException( 'This service does not support that request!' )
    
    def render_GET( self, request ):
        
        request.setHeader( 'Server', self._server_version_string )
        
        d = defer.Deferred()
        
        d.addCallback( self._callbackCheckRestrictions )
        
        d.addCallback( self._callbackParseGETArgs )
        
        d.addCallback( self._callbackDoGETJob )
        
        d.addErrback( self._errbackHandleProcessingError, request )
        
        d.addCallback( self._callbackRenderResponseContext )
        
        d.addErrback( self._errbackHandleEmergencyError, request )
        
        reactor.callLater( 0, d.callback, request )
        
        return NOT_DONE_YET
        
    
    def render_POST( self, request ):
        
        request.setHeader( 'Server', self._server_version_string )
        
        d = defer.Deferred()
        
        d.addCallback( self._callbackCheckRestrictions )
        
        d.addCallback( self._callbackParsePOSTArgs )
        
        d.addCallback( self._callbackDoPOSTJob )
        
        d.addErrback( self._errbackHandleProcessingError, request )
        
        d.addCallback( self._callbackRenderResponseContext )
        
        d.addErrback( self._errbackHandleEmergencyError, request )
        
        reactor.callLater( 0, d.callback, request )
        
        return NOT_DONE_YET
        
    
class HydrusResourceCommandAccessKey( HydrusResourceCommand ):
    
    def _threadDoGETJob( self, request ):
        
        registration_key = self._parseAccessKey( request )
        
        access_key = HC.app.Read( 'access_key', registration_key )
        
        body = yaml.safe_dump( { 'access_key' : access_key } )
        
        response_context = HC.ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceCommandAccessKeyVerification( HydrusResourceCommand ):
    
    def _threadDoGETJob( self, request ):
        
        access_key = self._parseAccessKey( request )
        
        account_identifier = HC.AccountIdentifier( access_key = access_key )
        
        try:
            
            account = HC.app.Read( 'account', self._service_identifier, account_identifier )
            
            verified = True
            
        except: verified = False
        
        body = yaml.safe_dump( { 'verified' : verified } )
        
        response_context = HC.ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceCommandFileLocal( HydrusResourceCommand ):
    
    local_only = True
    
    def _threadDoGETJob( self, request ):
        
        hash = request.hydrus_args[ 'hash' ]
        
        path = CC.GetFilePath( hash )
        
        response_context = HC.ResponseContext( 200, path = path )
        
        return response_context
        
    
class HydrusResourceCommandInit( HydrusResourceCommand ):
    
    def _threadDoGETJob( self, request ):
        
        access_key = HC.app.Read( 'init' )
        
        body = yaml.safe_dump( { 'access_key' : access_key } )
        
        response_context = HC.ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceCommandSessionKey( HydrusResourceCommand ):
    
    def _threadDoGETJob( self, request ):
        
        access_key = self._parseAccessKey( request )
        
        account_identifier = HC.AccountIdentifier( access_key = access_key )
        
        session_manager = HC.app.GetManager( 'restricted_services_sessions' )
        
        ( session_key, expiry ) = session_manager.AddSession( self._service_identifier, account_identifier )
        
        now = HC.GetNow()
        
        max_age = now - expiry
        
        cookies = [ ( 'session_key', session_key.encode( 'hex' ), { 'max_age' : max_age, 'path' : '/' } ) ]
        
        response_context = HC.ResponseContext( 200, cookies = cookies )
        
        return response_context
        
    
class HydrusResourceCommandThumbnailLocal( HydrusResourceCommand ):
    
    local_only = True
    
    def _threadDoGETJob( self, request ):
        
        hash = request.hydrus_args[ 'hash' ]
        
        path = CC.GetThumbnailPath( hash )
        
        response_context = HC.ResponseContext( 200, path = path )
        
        return response_context
        
    
class HydrusResourceCommandRestricted( HydrusResourceCommand ):
    
    GET_PERMISSION = HC.GENERAL_ADMIN
    POST_PERMISSION = HC.GENERAL_ADMIN
    RECORD_GET_DATA_USAGE = False
    RECORD_POST_DATA_USAGE = False
    
    def _callbackCheckRestrictions( self, request ):
        
        self._checkUserAgent( request )
        
        self._checkLocal( request )
        
        self._checkSession( request )
        
        self._checkPermission( request )
        
        return request
        
    
    def _checkPermission( self, request ):
        
        account = request.hydrus_account
        
        method = request.method
        
        if method == 'GET': permission = self.GET_PERMISSION
        elif method == 'POST': permission = self.POST_PERMISSION
        
        if permission is not None: account.CheckPermission( permission )
        
        return request
        
    
    def _checkSession( self, request ):
        
        if not request.requestHeaders.hasHeader( 'Cookie' ): raise HydrusExceptions.PermissionException( 'No cookies found!' )
        
        cookie_texts = request.requestHeaders.getRawHeaders( 'Cookie' )
        
        cookie_text = cookie_texts[0]
        
        try:
            
            cookies = Cookie.SimpleCookie( cookie_text )
            
            if 'session_key' not in cookies: session_key = None
            else: session_key = cookies[ 'session_key' ].value.decode( 'hex' )
            
        except: raise Exception( 'Problem parsing cookies!' )
        
        session_manager = HC.app.GetManager( 'restricted_services_sessions' )
        
        account = session_manager.GetAccount( self._service_identifier, session_key )
        
        request.hydrus_account = account
        
        return request
        
    
    def _recordDataUsage( self, request ):
        
        p1 = request.method == 'GET' and self.RECORD_GET_DATA_USAGE
        p2 = request.method == 'POST' and self.RECORD_POST_DATA_USAGE
        
        if p1 or p2:
            
            account = request.hydrus_account
            
            if account is not None:
                
                num_bytes = request.hydrus_request_data_usage
                
                account.RequestMade( num_bytes )
                
                HC.pubsub.pub( 'request_made', ( self._service_identifier, account, num_bytes ) )
                
            
        
    
class HydrusResourceCommandRestrictedAccount( HydrusResourceCommandRestricted ):
    
    GET_PERMISSION = None
    POST_PERMISSION = HC.MANAGE_USERS
    
    def _threadDoGETJob( self, request ):
        
        account = request.hydrus_account
        
        body = yaml.safe_dump( { 'account' : account } )
        
        response_context = HC.ResponseContext( 200, body = body )
        
        return response_context
        
    
    def _threadDoPOSTJob( self, request ):
        
        admin_account = request.hydrus_account
        
        action = request.hydrus_args[ 'action' ]
        
        subject_identifiers = request.hydrus_args[ 'subject_identifiers' ]
        
        kwargs = request.hydrus_args # for things like expiry, title, and so on
        
        HC.app.Write( 'account', self._service_identifier, admin_account, action, subject_identifiers, kwargs )
        
        session_manager = HC.app.GetManager( 'restricted_services_sessions' )
        
        session_manager.RefreshAccounts( self._service_identifier, subject_identifiers )
        
        response_context = HC.ResponseContext( 200 )
        
        return response_context
        
    
class HydrusResourceCommandRestrictedAccountInfo( HydrusResourceCommandRestricted ):
    
    GET_PERMISSION = HC.GENERAL_ADMIN
    
    def _threadDoGETJob( self, request ):
        
        subject_identifier = request.hydrus_args[ 'subject_identifier' ]
        
        account_info = HC.app.Read( 'account_info', self._service_identifier, subject_identifier )
        
        body = yaml.safe_dump( { 'account_info' : account_info } )
        
        response_context = HC.ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceCommandRestrictedAccountTypes( HydrusResourceCommandRestricted ):
    
    GET_PERMISSION = HC.GENERAL_ADMIN
    POST_PERMISSION = HC.GENERAL_ADMIN
    
    def _threadDoGETJob( self, request ):
        
        account_types = HC.app.Read( 'account_types', self._service_identifier )
        
        body = yaml.safe_dump( { 'account_types' : account_types } )
        
        response_context = HC.ResponseContext( 200, body = body )
        
        return response_context
        
    
    def _threadDoPOSTJob( self, request ):
        
        edit_log = request.hydrus_args[ 'edit_log' ]
        
        HC.app.Write( 'account_types', self._service_identifier, edit_log )
        
        response_context = HC.ResponseContext( 200 )
        
        return response_context
        
    
class HydrusResourceCommandRestrictedBackup( HydrusResourceCommandRestricted ):
    
    POST_PERMISSION = HC.GENERAL_ADMIN
    
    def _threadDoPOSTJob( self, request ):
        
        #threading.Thread( target = HC.app.Write, args = ( 'backup', ), name = 'Backup Thread' ).start()
        
        HC.app.Write( 'backup' )
        
        response_context = HC.ResponseContext( 200 )
        
        return response_context
        
    
class HydrusResourceCommandRestrictedFileRepository( HydrusResourceCommandRestricted ):
    
    GET_PERMISSION = HC.GET_DATA
    POST_PERMISSION = HC.POST_DATA
    RECORD_GET_DATA_USAGE = True
    RECORD_POST_DATA_USAGE = True
    
    def _threadDoGETJob( self, request ):
        
        hash = request.hydrus_args[ 'hash' ]
        
        # don't I need to check that we aren't stealing the file from another service?
        
        path = SC.GetPath( 'file', hash )
        
        response_context = HC.ResponseContext( 200, path = path )
        
        return response_context
        
    
    def _threadDoPOSTJob( self, request ):
        
        account = request.hydrus_account
        
        file_dict = request.hydrus_args
        
        file_dict[ 'ip' ] = request.getClientIP()
        
        HC.app.Write( 'file', self._service_identifier, account, file_dict )
        
        response_context = HC.ResponseContext( 200 )
        
        return response_context
        
    
class HydrusResourceCommandRestrictedIP( HydrusResourceCommandRestricted ):
    
    GET_PERMISSION = HC.GENERAL_ADMIN
    
    def _threadDoGETJob( self, request ):
        
        hash = request.hydrus_args[ 'hash' ]
        
        ( ip, timestamp ) = HC.app.Read( 'ip', self._service_identifier, hash )
        
        body = yaml.safe_dump( { 'ip' : ip, 'timestamp' : timestamp } )
        
        response_context = HC.ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceCommandRestrictedNews( HydrusResourceCommandRestricted ):
    
    POST_PERMISSION = HC.GENERAL_ADMIN
    
    def _threadDoPOSTJob( self, request ):
        
        news = request.hydrus_args[ 'news' ]
        
        HC.app.Write( 'news', self._service_identifier, news )
        
        response_context = HC.ResponseContext( 200 )
        
        return response_context
        
    
class HydrusResourceCommandRestrictedNumPetitions( HydrusResourceCommandRestricted ):
    
    GET_PERMISSION = HC.RESOLVE_PETITIONS
    
    def _threadDoGETJob( self, request ):
        
        num_petitions = HC.app.Read( 'num_petitions', self._service_identifier )
        
        body = yaml.safe_dump( { 'num_petitions' : num_petitions } )
        
        response_context = HC.ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceCommandRestrictedPetition( HydrusResourceCommandRestricted ):
    
    GET_PERMISSION = HC.RESOLVE_PETITIONS
    
    def _threadDoGETJob( self, request ):
        
        petition = HC.app.Read( 'petition', self._service_identifier )
        
        body = yaml.safe_dump( { 'petition' : petition } )
        
        response_context = HC.ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceCommandRestrictedRegistrationKeys( HydrusResourceCommandRestricted ):
    
    GET_PERMISSION = HC.GENERAL_ADMIN
    
    def _threadDoGETJob( self, request ):
        
        num = request.hydrus_args[ 'num' ]
        title = request.hydrus_args[ 'title' ]
        
        if 'lifetime' in request.hydrus_args: lifetime = request.hydrus_args[ 'lifetime' ]
        else: lifetime = None
        
        registration_keys = HC.app.Read( 'registration_keys', self._service_identifier, num, title, lifetime )
        
        body = yaml.safe_dump( { 'registration_keys' : registration_keys } )
        
        response_context = HC.ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceCommandRestrictedServices( HydrusResourceCommandRestricted ):
    
    GET_PERMISSION = HC.GENERAL_ADMIN
    POST_PERMISSION = HC.GENERAL_ADMIN
    
    def _threadDoGETJob( self, request ):
        
        services_info = HC.app.Read( 'services' )
        
        body = yaml.safe_dump( { 'services_info' : services_info } )
        
        response_context = HC.ResponseContext( 200, body = body )
        
        return response_context
        
    
    def _threadDoPOSTJob( self, request ):
        
        account = request.hydrus_account
        
        edit_log = request.hydrus_args[ 'edit_log' ]
        
        service_identifiers_to_access_keys = HC.app.Write( 'services', account, edit_log )
        
        body = yaml.safe_dump( { 'service_identifiers_to_access_keys' : service_identifiers_to_access_keys } )
        
        response_context = HC.ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceCommandRestrictedStats( HydrusResourceCommandRestricted ):
    
    GET_PERMISSION = HC.GENERAL_ADMIN
    
    def _threadDoGETJob( self, request ):
        
        stats = HC.app.Read( 'stats', self._service_identifier )
        
        body = yaml.safe_dump( { 'stats' : stats } )
        
        response_context = HC.ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceCommandRestrictedThumbnailRepository( HydrusResourceCommandRestricted ):
    
    GET_PERMISSION = HC.GET_DATA
    RECORD_GET_DATA_USAGE = True
    
    def _threadDoGETJob( self, request ):
        
        hash = request.hydrus_args[ 'hash' ]
        
        # don't I need to check that we aren't stealing the file from another service?
        
        path = SC.GetPath( 'thumbnail', hash )
        
        response_context = HC.ResponseContext( 200, path = path )
        
        return response_context
        
    
class HydrusResourceCommandRestrictedUpdate( HydrusResourceCommandRestricted ):
    
    GET_PERMISSION = HC.GET_DATA
    POST_PERMISSION = HC.POST_DATA
    RECORD_GET_DATA_USAGE = True
    RECORD_POST_DATA_USAGE = True
    
    def _threadDoGETJob( self, request ):
        
        begin = request.hydrus_args[ 'begin' ]
        
        path = SC.GetUpdatePath( self._service_identifier, begin )
        
        response_context = HC.ResponseContext( 200, path = path, is_yaml = True )
        
        return response_context
        
    
    def _threadDoPOSTJob( self, request ):
        
        account = request.hydrus_account
        
        update = request.hydrus_args[ 'update' ]
        
        HC.app.Write( 'update', self._service_identifier, account, update )
        
        response_context = HC.ResponseContext( 200 )
        
        return response_context
        
    