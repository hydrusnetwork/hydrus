import json
import os
import time

import twisted.internet.error
from twisted.internet import reactor, defer
from twisted.internet.threads import deferToThread
from twisted.web.server import NOT_DONE_YET
from twisted.web.resource import Resource
from twisted.web.static import NoRangeStaticProducer, SingleRangeStaticProducer

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusProfiling
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTemp
from hydrus.core.networking import HydrusServerRequest

def GetServerSummaryTexts( service ):
    
    name = service.GetName()
    service_type = service.GetServiceType()
    
    allows_non_local_connections = service.AllowsNonLocalConnections()
    
    welcome_text_1 = 'This is <b>' + name + '</b>,'
    welcome_text_2 = 'a ' + HC.service_string_lookup[ service_type ] + '.'
    welcome_text_3 = 'Software version ' + str( HC.SOFTWARE_VERSION )
    
    if service_type == HC.CLIENT_API_SERVICE:
        
        welcome_text_4 = 'API version ' + str( HC.CLIENT_API_VERSION )
        
    else:
        
        welcome_text_4 = 'Network version ' + str( HC.NETWORK_VERSION )
        
    
    if allows_non_local_connections:
        
        welcome_text_5 = 'It responds to requests from any host.'
        
    else:
        
        welcome_text_5 = 'It only responds to requests from localhost.'
        
    
    return (
        welcome_text_1,
        welcome_text_2,
        welcome_text_3,
        welcome_text_4,
        welcome_text_5
    )
    
def GenerateEris( service ):
    
    if hasattr( service, 'UseNormieEris' ) and service.UseNormieEris():
        
        return GenerateNormieEris( service )
        
    name = service.GetName()
    
    server_summary_texts = GetServerSummaryTexts( service )
    
    return '''<html><head><title>{}</title></head><body><pre>
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
   <font color="red">8</font>   <font color="gray">MM</font>::::::::<font color="red">8888</font><font color="gray">M</font>:::<font color="red">8888</font>:::::<font color="red">888888888888</font>::::::::<font color="gray">Mm</font><font color="red">8     4</font>              {}
       <font color="red">8</font><font color="gray">M</font>:::::::<font color="red">8888</font><font color="gray">M</font>:::::<font color="red">888</font>:::::::<font color="red">88</font>:::<font color="red">8888888</font>::::::::<font color="gray">Mm</font>    <font color="red">2</font>              {}
      <font color="red">88</font><font color="gray">MM</font>:::::<font color="red">8888</font><font color="gray">M</font>:::::::<font color="red">88</font>::::::::<font color="red">8</font>:::::<font color="red">888888</font>:::<font color="gray">M</font>:::::<font color="gray">M</font>
     <font color="red">8888</font><font color="gray">M</font>:::::<font color="red">888</font><font color="gray">MM</font>::::::::<font color="red">8</font>:::::::::::<font color="gray">M</font>::::<font color="red">8888</font>::::<font color="gray">M</font>::::<font color="gray">M</font>                  {}
    <font color="red">88888</font><font color="gray">M</font>:::::<font color="red">88</font>:<font color="gray">M</font>::::::::::<font color="red">8</font>:::::::::::<font color="gray">M</font>:::<font color="red">8888</font>::::::<font color="gray">M</font>::<font color="gray">M</font>                  {}
   <font color="red">88 888</font><font color="gray">MM</font>:::<font color="red">888</font>:<font color="gray">M</font>:::::::::::::::::::::::<font color="gray">M</font>:<font color="red">8888</font>:::::::::<font color="gray">M</font>:
   <font color="red">8 88888</font><font color="gray">M</font>:::<font color="red">88</font>::<font color="gray">M</font>:::::::::::::::::::::::<font color="gray">MM</font>:<font color="red">88</font>::::::::::::<font color="gray">M</font>                 {}
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
                   <font color="gray">MM</font>::<font color="gray">M</font>:::::::::::::::::::<font color="gray">MMM</font>
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
</pre></body></html>'''.format(
        name,
        server_summary_texts[0],
        server_summary_texts[1],
        server_summary_texts[2],
        server_summary_texts[3],
        server_summary_texts[4]
    )
    

def GenerateNormieEris( service ):
    
    name = service.GetName()
    
    server_summary_texts = GetServerSummaryTexts( service )
    
    style_block_full_of_braces = '''<style type="text/css">
<!--
#ascgen-image pre {
    font-family: "Lucida Console", monospace;
    font-size: 9pt;
    background-color: #FFFFFF;
    color: #000000;
    float: left;
    line-height: 12px;
    border: 1px solid #000000;
}

.c0 { color: #000000; }
.c1 { color: #002B00; }
.c2 { color: #330000; }
.c3 { color: #332B33; }
.c4 { color: #662B33; }
.c5 { color: #335533; }
.c6 { color: #332B00; }
.c7 { color: #665533; }
.c8 { color: #665566; }
.c9 { color: #995533; }
.c10 { color: #998033; }
.c11 { color: #CC8033; }
.c12 { color: #CC8000; }
.c13 { color: #665500; }
.c14 { color: #995500; }
.c15 { color: #CCAA33; }
.c16 { color: #995566; }
.c17 { color: #CCAA00; }
.c18 { color: #FFAA33; }
.c19 { color: #CCAA99; }
.c20 { color: #FFAA00; }
.c21 { color: #660033; }
.c22 { color: #CCAA66; }
.c23 { color: #998099; }
.c24 { color: #662B00; }
.c25 { color: #998066; }
.c26 { color: #FFD5CC; }
.c27 { color: #CCD5CC; }
.c28 { color: #FFAA66; }
.c29 { color: #CC8066; }
.c30 { color: #330033; }
.c31 { color: #FFD599; }
.c32 { color: #FFFFCC; }
.c33 { color: #CCD599; }
.c34 { color: #998000; }
.c35 { color: #FFAACC; }
.c36 { color: #99AA66; }
.c37 { color: #99AA99; }
.c38 { color: #668000; }
.c39 { color: #660000; }
.c40 { color: #FFFF99; }
.c41 { color: #FF8033; }
.c42 { color: #FFAA99; }
.c43 { color: #FF8000; }
.c44 { color: #FFD566; }
.c45 { color: #CCD566; }
.c46 { color: #FFFF66; }
.c47 { color: #000033; }
.c48 { color: #CCD533; }
.c49 { color: #FFD533; }
.c50 { color: #CC5500; }
-->
</style>'''
    
    return '''<html><head><title>{}</title>
{}
</head><body>
<div id="ascgen-image">
<pre><span class="c0">█████████████████████████████████</span><span class="c1">█</span><span class="c2">█</span><span class="c3">██▓</span><span class="c4">▓</span><span class="c5">▓</span><span class="c4">▓</span><span class="c5">▓</span><span class="c4">▓</span><span class="c3">▓█</span><span class="c6">█</span><span class="c3">█</span><span class="c0">█████████████████████████████████
████████████████████████████</span><span class="c3">█▓</span><span class="c4">▓</span><span class="c7">▓▓</span><span class="c8">▓</span><span class="c7">▓</span><span class="c9">▒▒</span><span class="c10">▒</span><span class="c9">▒▒▒▒▒</span><span class="c7">▓</span><span class="c9">▓</span><span class="c8">▓</span><span class="c7">▓▓▓</span><span class="c4">▓</span><span class="c3">▓█</span><span class="c6">█</span><span class="c0">███████████████████████████
████████████████████████</span><span class="c3">█</span><span class="c4">▓</span><span class="c7">▓▓</span><span class="c9">▓</span><span class="c7">▓</span><span class="c9">▓▒▒</span><span class="c11">░</span><span class="c12">░</span><span class="c9">▒</span><span class="c13">▓</span><span class="c9">▒</span><span class="c6">█▓</span><span class="c14">▓</span><span class="c13">▓</span><span class="c14">▓</span><span class="c15">▒</span><span class="c12">▒</span><span class="c11">▒</span><span class="c12">▒</span><span class="c11">▒</span><span class="c10">▒</span><span class="c9">▒</span><span class="c10">▒</span><span class="c9">▒▓</span><span class="c8">▓</span><span class="c7">▓</span><span class="c4">▓</span><span class="c3">█</span><span class="c0">███████████████████████
█████████████████████</span><span class="c7">▓▓</span><span class="c16">▓</span><span class="c7">▓</span><span class="c9">▓</span><span class="c10">▒</span><span class="c11">▒</span><span class="c12">▒</span><span class="c17">▒</span><span class="c18">░</span><span class="c17">░</span><span class="c18"> </span><span class="c12">░</span><span class="c6">█</span><span class="c0">█</span><span class="c2">████</span><span class="c0">█</span><span class="c8">▓</span><span class="c19">░</span><span class="c15">░</span><span class="c20">░</span><span class="c15">░</span><span class="c18">░</span><span class="c12">░</span><span class="c18">░</span><span class="c15">░</span><span class="c9">▒</span><span class="c15">▒</span><span class="c10">▒</span><span class="c12">▒</span><span class="c10">▒</span><span class="c9">▒</span><span class="c10">▒</span><span class="c7">▒▓</span><span class="c3">▓</span><span class="c2">█</span><span class="c0">███████████████████
██████████████████</span><span class="c3">▓</span><span class="c7">▒</span><span class="c8">▒</span><span class="c9">▒▓</span><span class="c10">▒</span><span class="c12">▒</span><span class="c17">░</span><span class="c18">░</span><span class="c17">░</span><span class="c18">▒</span><span class="c11">░</span><span class="c17">▒</span><span class="c18">░</span><span class="c15">░</span><span class="c2">█</span><span class="c0">█</span><span class="c21">█</span><span class="c6">█</span><span class="c2">██</span><span class="c4">█</span><span class="c22">░</span><span class="c19"> ░░</span><span class="c22">░</span><span class="c12">▒</span><span class="c15">▒</span><span class="c18">░</span><span class="c12">▒</span><span class="c22">▒</span><span class="c23">▒</span><span class="c16">▒</span><span class="c15">░░</span><span class="c14">▒▒▒</span><span class="c11">░</span><span class="c10">▒</span><span class="c9">▒</span><span class="c8">▓</span><span class="c7">▓</span><span class="c3">▓</span><span class="c0">█████████████████
████████████████</span><span class="c7">▓</span><span class="c16">▒</span><span class="c9">▒</span><span class="c10">▒</span><span class="c12">▒</span><span class="c15"> </span><span class="c20"> </span><span class="c18">░</span><span class="c15">░</span><span class="c18">▒</span><span class="c11">▒</span><span class="c18">▒</span><span class="c15">▒</span><span class="c18">░░ </span><span class="c10">▒</span><span class="c2">█</span><span class="c24">█</span><span class="c19">  </span><span class="c25">▓</span><span class="c19"> </span><span class="c26"> </span><span class="c19">░</span><span class="c25">▓</span><span class="c4">█</span><span class="c27"> </span><span class="c26"> </span><span class="c28">░</span><span class="c15">▒▒░</span><span class="c29">▒</span><span class="c25">▓</span><span class="c7">▓</span><span class="c16">▒</span><span class="c2">██</span><span class="c0">█</span><span class="c2">█</span><span class="c24">▓</span><span class="c14">▒</span><span class="c15">░</span><span class="c12">▒</span><span class="c9">▒▒</span><span class="c8">▒</span><span class="c7">▓</span><span class="c0">███████████████
██████████████</span><span class="c7">▓</span><span class="c16">▒</span><span class="c9">▒</span><span class="c10">▒</span><span class="c14">▓</span><span class="c2">▓</span><span class="c24">█▓</span><span class="c12">░</span><span class="c15"> </span><span class="c18">░</span><span class="c20">░</span><span class="c15">░</span><span class="c18">░</span><span class="c15">░</span><span class="c18"> </span><span class="c15">░</span><span class="c7">▓</span><span class="c24">█</span><span class="c30">█</span><span class="c2">█</span><span class="c7">▒</span><span class="c19"> </span><span class="c31"> </span><span class="c32"> </span><span class="c31"> </span><span class="c26"> </span><span class="c33"> </span><span class="c31">  </span><span class="c19">░</span><span class="c22">▒</span><span class="c15">▒</span><span class="c18">▒</span><span class="c19">░</span><span class="c22"> </span><span class="c25">▒▓</span><span class="c19">░</span><span class="c25">▒</span><span class="c2">█████</span><span class="c6">█</span><span class="c11">░</span><span class="c20"> </span><span class="c15">▒</span><span class="c14">▓</span><span class="c7">▓</span><span class="c16">▒</span><span class="c7">▓</span><span class="c0">█████████████
████████████</span><span class="c7">▓</span><span class="c16">▒</span><span class="c7">▓</span><span class="c34">▒</span><span class="c12">░</span><span class="c24">▓</span><span class="c0">█</span><span class="c2">██</span><span class="c0">█</span><span class="c2">█</span><span class="c24">█</span><span class="c10">▒</span><span class="c18">   </span><span class="c15">░</span><span class="c9">▓</span><span class="c2">█████</span><span class="c7">█</span><span class="c19"> </span><span class="c31"> </span><span class="c35"> </span><span class="c31">  </span><span class="c26">  </span><span class="c19"> </span><span class="c22">▒</span><span class="c18">░</span><span class="c28"> </span><span class="c18"> </span><span class="c15"> </span><span class="c29">▒</span><span class="c33"> </span><span class="c32"> </span><span class="c26"> </span><span class="c32"> </span><span class="c4">█</span><span class="c0">█</span><span class="c2">████</span><span class="c0">█</span><span class="c24">▓</span><span class="c15"> </span><span class="c18"> </span><span class="c12">▒</span><span class="c9">▓</span><span class="c7">▓</span><span class="c16">▒</span><span class="c3">▓</span><span class="c0">███████████
██████████</span><span class="c1">█</span><span class="c16">▒</span><span class="c7">▓</span><span class="c9">▓</span><span class="c12">░</span><span class="c15"> </span><span class="c24">█</span><span class="c0">█</span><span class="c2">████████</span><span class="c7">▓</span><span class="c10">▒</span><span class="c24">▓</span><span class="c2">█</span><span class="c0">█</span><span class="c2">███</span><span class="c0">█</span><span class="c16">▒</span><span class="c33"> </span><span class="c31"> </span><span class="c33"> </span><span class="c26">  </span><span class="c33"> </span><span class="c28">░</span><span class="c31"> </span><span class="c28"> </span><span class="c15"> ░</span><span class="c9">▒</span><span class="c24">█</span><span class="c0">█</span><span class="c21">█</span><span class="c25">░</span><span class="c31"> </span><span class="c26"> </span><span class="c29">░</span><span class="c0">█</span><span class="c2">█</span><span class="c0">█</span><span class="c2">█████</span><span class="c14">▒</span><span class="c18"> </span><span class="c20"> </span><span class="c17">▒</span><span class="c7">▓</span><span class="c9">▒</span><span class="c16">▒</span><span class="c0">██████████
█████████</span><span class="c4">▓</span><span class="c16">▒</span><span class="c7">▓</span><span class="c34">▒</span><span class="c18"> </span><span class="c15"> </span><span class="c2">██████</span><span class="c0">█</span><span class="c2">█</span><span class="c0">█</span><span class="c2">██</span><span class="c4">█</span><span class="c2">█</span><span class="c6">█</span><span class="c9">▒</span><span class="c24">█</span><span class="c0">█</span><span class="c2">██</span><span class="c4">▓</span><span class="c19"> ░░░</span><span class="c22">▒</span><span class="c19">▒</span><span class="c22">▒░</span><span class="c15">▒</span><span class="c9">▓</span><span class="c6">█</span><span class="c2">█</span><span class="c0">██</span><span class="c2">██</span><span class="c0">█</span><span class="c4">█</span><span class="c36">░</span><span class="c19"> </span><span class="c9">▓</span><span class="c2">████</span><span class="c0">█</span><span class="c2">██</span><span class="c0">█</span><span class="c13">▓</span><span class="c15">░</span><span class="c18"> </span><span class="c20">░</span><span class="c34">▒</span><span class="c7">▓</span><span class="c25">▒</span><span class="c4">▓</span><span class="c0">████████
████████</span><span class="c7">▒</span><span class="c16">▒</span><span class="c13">▓</span><span class="c11">░</span><span class="c20">░</span><span class="c18"> </span><span class="c24">▓</span><span class="c2">████</span><span class="c0">█</span><span class="c2">██</span><span class="c16">▓</span><span class="c25">▒</span><span class="c19"> </span><span class="c31">  </span><span class="c26"> </span><span class="c31"> </span><span class="c25">▒</span><span class="c2">█</span><span class="c4">▓</span><span class="c7">▓</span><span class="c2">█</span><span class="c7">▒</span><span class="c9">▒</span><span class="c16">▒</span><span class="c25">▒▒</span><span class="c19">░</span><span class="c25">░</span><span class="c19">  </span><span class="c7">▓</span><span class="c4">█</span><span class="c7">▓</span><span class="c24">▓</span><span class="c4">▓</span><span class="c24">█</span><span class="c2">████</span><span class="c4">█</span><span class="c31"> </span><span class="c19"> </span><span class="c37">▒</span><span class="c4">▓</span><span class="c0">█</span><span class="c2">███████</span><span class="c12">░</span><span class="c15"> </span><span class="c18">░</span><span class="c11">▒</span><span class="c13">▓</span><span class="c16">▒</span><span class="c7">▓</span><span class="c0">███████
███████</span><span class="c16">▒</span><span class="c9">▓</span><span class="c38">▓</span><span class="c18">░</span><span class="c20">░</span><span class="c15"> </span><span class="c14">▒</span><span class="c0">█</span><span class="c2">███</span><span class="c0">█</span><span class="c4">█</span><span class="c36">▒</span><span class="c26"> </span><span class="c32"> </span><span class="c26">  </span><span class="c31"> </span><span class="c26"> </span><span class="c31"> </span><span class="c19"> </span><span class="c2">█</span><span class="c6">█</span><span class="c9">▒</span><span class="c2">█</span><span class="c4">▓</span><span class="c2">██</span><span class="c0">█</span><span class="c2">██████████</span><span class="c7">▓▒▓</span><span class="c2">██</span><span class="c0">█</span><span class="c2">█</span><span class="c19"> </span><span class="c32"> </span><span class="c31"> </span><span class="c26"> </span><span class="c25">▒</span><span class="c2">████████</span><span class="c11">▒</span><span class="c20"> </span><span class="c15">░</span><span class="c20">░</span><span class="c7">▓</span><span class="c9">▒</span><span class="c8">▒</span><span class="c0">██████
██████</span><span class="c25">▒</span><span class="c7">▓</span><span class="c9">▓</span><span class="c20">░</span><span class="c11">░</span><span class="c18">░</span><span class="c15">░</span><span class="c2">███</span><span class="c0">█</span><span class="c2">█</span><span class="c16">▒</span><span class="c26">  </span><span class="c31">    </span><span class="c26"> </span><span class="c32"> </span><span class="c31"> </span><span class="c4">█</span><span class="c2">█</span><span class="c4">▓</span><span class="c2">█</span><span class="c4">▓</span><span class="c2">▓</span><span class="c4">▓▓</span><span class="c3">█</span><span class="c39">█</span><span class="c4">▓</span><span class="c2">██</span><span class="c21">▓</span><span class="c4">▓</span><span class="c2">█</span><span class="c21">▓</span><span class="c4">▓</span><span class="c2">█</span><span class="c21">█</span><span class="c39">█</span><span class="c10">▒</span><span class="c2">█████</span><span class="c19"> </span><span class="c26"> </span><span class="c31"> </span><span class="c32"> </span><span class="c19">░</span><span class="c2">██</span><span class="c0">█</span><span class="c2">████</span><span class="c0">█</span><span class="c14">▒</span><span class="c18"> </span><span class="c15">░</span><span class="c20">░</span><span class="c7">▓</span><span class="c9">▓▒</span><span class="c0">█████
█████</span><span class="c16">▒</span><span class="c7">▓</span><span class="c14">▓</span><span class="c18">░</span><span class="c15">▒</span><span class="c17">░</span><span class="c18"> </span><span class="c24">▓</span><span class="c0">█</span><span class="c2">██</span><span class="c3">█</span><span class="c19"> </span><span class="c40"> </span><span class="c31">  </span><span class="c26"> </span><span class="c33"> </span><span class="c26"> </span><span class="c19"> ▒</span><span class="c9">▓</span><span class="c3">█</span><span class="c2">█</span><span class="c4">▓</span><span class="c39">▓</span><span class="c4">▓</span><span class="c2">██</span><span class="c21">▓</span><span class="c2">███</span><span class="c4">▓</span><span class="c2">██</span><span class="c4">▓</span><span class="c2">██</span><span class="c4">▓</span><span class="c2">▓█</span><span class="c4">▓</span><span class="c3">█</span><span class="c11">▒</span><span class="c37">░</span><span class="c19"> </span><span class="c33"> </span><span class="c19">░</span><span class="c25">▓</span><span class="c29">▒</span><span class="c31"> </span><span class="c26"> </span><span class="c31"> </span><span class="c26"> </span><span class="c25">▒</span><span class="c2">█</span><span class="c24">▓</span><span class="c2">█</span><span class="c0">█</span><span class="c2">████</span><span class="c11">▒</span><span class="c20"> </span><span class="c11">░</span><span class="c20">░</span><span class="c7">▓</span><span class="c16">▒</span><span class="c7">▒</span><span class="c0">████
████</span><span class="c7">▓</span><span class="c16">▒</span><span class="c13">▓</span><span class="c18">░</span><span class="c17">▒</span><span class="c41">░</span><span class="c15">░</span><span class="c11">▒</span><span class="c2">███</span><span class="c3">▓</span><span class="c31"> </span><span class="c32"> </span><span class="c26"> </span><span class="c31"> </span><span class="c27"> </span><span class="c31"> </span><span class="c26"> </span><span class="c31"> </span><span class="c19">░</span><span class="c25">▓</span><span class="c4">█</span><span class="c2">█</span><span class="c4">█</span><span class="c2">█</span><span class="c4">▓</span><span class="c30">█</span><span class="c2">██</span><span class="c24">█</span><span class="c2">███</span><span class="c30">▓</span><span class="c2">██</span><span class="c4">▓</span><span class="c6">█</span><span class="c2">█</span><span class="c39">▓</span><span class="c3">▓</span><span class="c2">███</span><span class="c22">░</span><span class="c26"> </span><span class="c31"> </span><span class="c26"> </span><span class="c31"> </span><span class="c32"> </span><span class="c31"> </span><span class="c26"> </span><span class="c33"> </span><span class="c31">  </span><span class="c32"> </span><span class="c16">▒</span><span class="c6">▓</span><span class="c7">▓</span><span class="c4">▓</span><span class="c2">███</span><span class="c0">█</span><span class="c2">█</span><span class="c14">▒</span><span class="c18"> </span><span class="c15">░</span><span class="c20">░</span><span class="c13">▓</span><span class="c16">▒</span><span class="c7">▓</span><span class="c0">███
███</span><span class="c3">▓</span><span class="c25">▒</span><span class="c13">█</span><span class="c18">░</span><span class="c12">▒</span><span class="c15">▒</span><span class="c18">▒ </span><span class="c13">▓</span><span class="c2">███</span><span class="c4">█</span><span class="c25">░</span><span class="c19"> </span><span class="c42"> </span><span class="c26"> </span><span class="c31"> </span><span class="c26"> </span><span class="c31"> </span><span class="c32"> </span><span class="c26"> </span><span class="c40"> </span><span class="c26"> </span><span class="c31"> </span><span class="c25">░</span><span class="c4">█</span><span class="c24">█</span><span class="c3">█</span><span class="c4">█</span><span class="c7">▓</span><span class="c4">███</span><span class="c6">█</span><span class="c39">█</span><span class="c6">█</span><span class="c30">█</span><span class="c2">██</span><span class="c3">█</span><span class="c2">█</span><span class="c6">█</span><span class="c21">█</span><span class="c6">█</span><span class="c2">█</span><span class="c29">▒</span><span class="c31"> </span><span class="c26"> </span><span class="c31"> </span><span class="c26"> </span><span class="c42"> </span><span class="c26"> </span><span class="c32"> </span><span class="c26">  </span><span class="c31"> </span><span class="c33"> </span><span class="c16">▒</span><span class="c2">██</span><span class="c24">▓</span><span class="c3">▓</span><span class="c6">▓</span><span class="c2">███</span><span class="c0">█</span><span class="c10">▒</span><span class="c20"> </span><span class="c15">░░</span><span class="c13">█</span><span class="c16">▒</span><span class="c3">█</span><span class="c0">██
███</span><span class="c9">▒</span><span class="c4">▓</span><span class="c10">▒</span><span class="c43">░</span><span class="c15">▒</span><span class="c20">▒</span><span class="c15">░</span><span class="c11">░</span><span class="c6">█</span><span class="c2">███████</span><span class="c4">█</span><span class="c7">▓</span><span class="c8">▓</span><span class="c29">▒</span><span class="c25">░</span><span class="c22">░</span><span class="c19">░░</span><span class="c23">▒</span><span class="c22">▒</span><span class="c19">▒ </span><span class="c26"> </span><span class="c31"> </span><span class="c26">  </span><span class="c33"> </span><span class="c25">▒</span><span class="c16">▒</span><span class="c25">▒</span><span class="c4">▓</span><span class="c39">█</span><span class="c3">█</span><span class="c39">▓</span><span class="c21">▓</span><span class="c6">▓</span><span class="c21">▓</span><span class="c2">▓</span><span class="c4">█</span><span class="c9">▒</span><span class="c31"> </span><span class="c44"> </span><span class="c45"> </span><span class="c31">░</span><span class="c22">░</span><span class="c33">░</span><span class="c29">▒</span><span class="c7">▓▓▓</span><span class="c4">█</span><span class="c2">█</span><span class="c6">█</span><span class="c2">██████████</span><span class="c9">▒</span><span class="c18"> </span><span class="c43">░</span><span class="c10">▒</span><span class="c7">▓</span><span class="c9">▒</span><span class="c0">██
██</span><span class="c7">▓</span><span class="c16">▒</span><span class="c13">▓</span><span class="c20">░</span><span class="c15">▒▒</span><span class="c41">░</span><span class="c18"> </span><span class="c13">▓</span><span class="c2">████</span><span class="c6">█▓</span><span class="c2">██</span><span class="c0">█</span><span class="c2">█</span><span class="c24">█</span><span class="c0">█</span><span class="c2">█</span><span class="c0">█</span><span class="c9">█</span><span class="c22">░</span><span class="c10">▓</span><span class="c7">▓</span><span class="c9">▓</span><span class="c36">▒</span><span class="c31"> </span><span class="c32"> </span><span class="c31"> </span><span class="c26"> </span><span class="c31"> </span><span class="c19">░</span><span class="c7">▓</span><span class="c2">██</span><span class="c4">▓</span><span class="c2">█</span><span class="c6">▓</span><span class="c4">▓</span><span class="c2">██</span><span class="c4">▓</span><span class="c39">▓</span><span class="c7">▓</span><span class="c9">▒</span><span class="c29">░</span><span class="c22">░</span><span class="c28"> </span><span class="c44"> </span><span class="c46"> </span><span class="c44"> </span><span class="c24">█</span><span class="c0">█</span><span class="c2">█</span><span class="c0">█</span><span class="c2">███</span><span class="c6">█</span><span class="c2">████████</span><span class="c24">█</span><span class="c15">░</span><span class="c18"> </span><span class="c20">░</span><span class="c7">▓</span><span class="c16">▒</span><span class="c5">▓</span><span class="c0">█
██</span><span class="c16">▒</span><span class="c7">▓</span><span class="c11">▒</span><span class="c18">░</span><span class="c12">▒</span><span class="c18">▒</span><span class="c15">░</span><span class="c18"> </span><span class="c30">█</span><span class="c2">█</span><span class="c24">▓</span><span class="c3">▓</span><span class="c2">██████</span><span class="c7">▓</span><span class="c2">▓███</span><span class="c22"> </span><span class="c44">  </span><span class="c31"> </span><span class="c44">   </span><span class="c25">▒</span><span class="c9">▓</span><span class="c23">░</span><span class="c22">░</span><span class="c25">░</span><span class="c19"> </span><span class="c9">▓</span><span class="c3">█</span><span class="c24">▓</span><span class="c30">█</span><span class="c39">▓</span><span class="c4">▓</span><span class="c2">██</span><span class="c4">▓</span><span class="c3">█</span><span class="c2">██</span><span class="c21">█</span><span class="c2">█</span><span class="c6">█</span><span class="c4">█</span><span class="c9">▓</span><span class="c36">░</span><span class="c28"> </span><span class="c7">▒</span><span class="c2">███████</span><span class="c6">▓</span><span class="c2">█</span><span class="c30">█</span><span class="c6">█</span><span class="c2">█████</span><span class="c12">░</span><span class="c15"> </span><span class="c12">▒</span><span class="c7">▓</span><span class="c9">▒</span><span class="c0">█</span> {}
<span class="c0">█</span><span class="c3">▓</span><span class="c10">▒</span><span class="c13">▓</span><span class="c15">░</span><span class="c17">▒</span><span class="c41">▒</span><span class="c15">▒</span><span class="c18">░</span><span class="c11">░</span><span class="c2">█</span><span class="c6">█</span><span class="c3">▓</span><span class="c2">███</span><span class="c6">█</span><span class="c30">█</span><span class="c6">█</span><span class="c24">▓</span><span class="c2">▓███</span><span class="c7">█</span><span class="c44">  </span><span class="c31"> </span><span class="c44"> </span><span class="c31"> </span><span class="c44"> </span><span class="c7">▓</span><span class="c2">██</span><span class="c39">█</span><span class="c3">█</span><span class="c4">▓▓</span><span class="c3">▓</span><span class="c21">▓</span><span class="c2">▓██</span><span class="c4">▓</span><span class="c2">██</span><span class="c39">▓</span><span class="c2">███</span><span class="c4">▓</span><span class="c2">██████</span><span class="c7">▓</span><span class="c9">▒</span><span class="c7">▒</span><span class="c2">████████▓</span><span class="c3">▓</span><span class="c2">█</span><span class="c6">█</span><span class="c2">█</span><span class="c0">█</span><span class="c24">█</span><span class="c18"> </span><span class="c12"> </span><span class="c7">▓</span><span class="c16">▒</span><span class="c3">█</span> {}
<span class="c0">█</span><span class="c7">▓</span><span class="c8">▓</span><span class="c14">▓</span><span class="c18">░</span><span class="c43">▒</span><span class="c15">▒░</span><span class="c18"> </span><span class="c13">▓</span><span class="c2">██████▓</span><span class="c7">▓</span><span class="c2">█████</span><span class="c6">█</span><span class="c10">▒</span><span class="c31"> </span><span class="c44">    </span><span class="c4">█</span><span class="c2">██</span><span class="c4">▓▓</span><span class="c2">█</span><span class="c21">▓</span><span class="c2">██</span><span class="c24">▓</span><span class="c4">▓</span><span class="c3">█</span><span class="c2">█</span><span class="c4">▓▓</span><span class="c2">█</span><span class="c3">█</span><span class="c4">▓</span><span class="c3">█</span><span class="c2">█</span><span class="c24">▓</span><span class="c4">▓</span><span class="c2">██</span><span class="c4">▓</span><span class="c21">█</span><span class="c2">██</span><span class="c39">█</span><span class="c4">▓</span><span class="c0">█</span><span class="c7">▒</span><span class="c6">▓</span><span class="c30">█</span><span class="c2">████████</span><span class="c6">▓</span><span class="c2">██</span><span class="c13">▓</span><span class="c18"> </span><span class="c14">▓</span><span class="c7">▓▓
</span><span class="c0">█</span><span class="c16">▒</span><span class="c7">▓</span><span class="c12">▒</span><span class="c15">░▒</span><span class="c18">▒</span><span class="c20">░</span><span class="c15">░</span><span class="c2">████</span><span class="c6">█</span><span class="c4">▓</span><span class="c6">▓▓</span><span class="c2">█████</span><span class="c3">█</span><span class="c4">█</span><span class="c44">  </span><span class="c31"> </span><span class="c44"> </span><span class="c40"> </span><span class="c9">▓</span><span class="c2">███</span><span class="c30">▓</span><span class="c2">▓█</span><span class="c6">█</span><span class="c21">█</span><span class="c2">██</span><span class="c21">▓</span><span class="c2">██▓</span><span class="c39">▓</span><span class="c2">██</span><span class="c4">▓</span><span class="c2">██</span><span class="c21">▓</span><span class="c2">███</span><span class="c4">▓</span><span class="c2">███</span><span class="c3">▓</span><span class="c39">█</span><span class="c2">█</span><span class="c4">▓</span><span class="c7">▓</span><span class="c24">█</span><span class="c3">▓</span><span class="c2">██</span><span class="c6">█</span><span class="c2">████████</span><span class="c11">░</span><span class="c34">▒</span><span class="c8">▓</span><span class="c9">▓</span> {}
<span class="c47">█</span><span class="c9">▒</span><span class="c7">▓</span><span class="c12">▒</span><span class="c11">▒</span><span class="c20">▒</span><span class="c11">▒</span><span class="c15"> </span><span class="c11">▒</span><span class="c0">█</span><span class="c2">█</span><span class="c4">▓</span><span class="c6">█</span><span class="c2">███████</span><span class="c6">█</span><span class="c4">▓</span><span class="c7">▓</span><span class="c15">░</span><span class="c31"> </span><span class="c44"> ░</span><span class="c28"> </span><span class="c40"> </span><span class="c7">▓</span><span class="c30">█</span><span class="c2">█</span><span class="c30">█</span><span class="c24">▓</span><span class="c4">▓</span><span class="c6">█</span><span class="c21">▓</span><span class="c24">▓</span><span class="c3">█</span><span class="c2">▓</span><span class="c4">▓</span><span class="c6">█</span><span class="c2">█</span><span class="c4">▓▓</span><span class="c30">█</span><span class="c2">█</span><span class="c24">▓</span><span class="c21">█</span><span class="c2">█</span><span class="c6">▓</span><span class="c4">▓</span><span class="c3">█</span><span class="c2">█</span><span class="c4">▓</span><span class="c2">▓</span><span class="c3">█</span><span class="c2">█</span><span class="c21">▓</span><span class="c4">▓</span><span class="c2">███</span><span class="c22"> </span><span class="c11">▒</span><span class="c15">░</span><span class="c7">█</span><span class="c2">█</span><span class="c24">█</span><span class="c3">█</span><span class="c2">█████</span><span class="c0">█</span><span class="c24">█</span><span class="c11">░</span><span class="c7">▓</span><span class="c9">▒</span> {}
<span class="c1">█</span><span class="c16">▒</span><span class="c7">▓</span><span class="c12">▒</span><span class="c18">░</span><span class="c15">▒</span><span class="c18">░ </span><span class="c24">▓</span><span class="c2">█</span><span class="c6">▓▓</span><span class="c2">██████</span><span class="c0">█</span><span class="c4">▓▓</span><span class="c24">█</span><span class="c22">░</span><span class="c44">  </span><span class="c31">░</span><span class="c44"> </span><span class="c31"> </span><span class="c44"> </span><span class="c22">▒</span><span class="c2">████</span><span class="c21">▓</span><span class="c2">██</span><span class="c4">▓</span><span class="c2">██</span><span class="c4">▓</span><span class="c2">███</span><span class="c24">▓</span><span class="c2">██</span><span class="c4">▓</span><span class="c2">██</span><span class="c30">█</span><span class="c39">▓</span><span class="c2">██</span><span class="c4">▓</span><span class="c2">███</span><span class="c6">▓</span><span class="c2">▓██</span><span class="c4">█</span><span class="c44">  </span><span class="c28"> </span><span class="c15"> </span><span class="c7">▓▓</span><span class="c14">▓</span><span class="c7">▓</span><span class="c6">█</span><span class="c4">█</span><span class="c24">█</span><span class="c2">█</span><span class="c6">█</span><span class="c2">█</span><span class="c14">▓</span><span class="c7">▓</span><span class="c16">▒
</span><span class="c1">█</span><span class="c16">▒</span><span class="c7">▓</span><span class="c12">░</span><span class="c15">▒</span><span class="c12">░</span><span class="c15">░</span><span class="c11">░</span><span class="c6">█</span><span class="c2">████████</span><span class="c4">▓</span><span class="c6">█</span><span class="c7">▓</span><span class="c9">▒</span><span class="c15">▒</span><span class="c44"> </span><span class="c31"> </span><span class="c44">░ ░  </span><span class="c31"> </span><span class="c10">▓</span><span class="c2">██</span><span class="c6">▓</span><span class="c4">▓</span><span class="c2">██</span><span class="c4">▓</span><span class="c21">▓</span><span class="c2">█</span><span class="c24">▓</span><span class="c21">▓</span><span class="c6">█</span><span class="c21">▓</span><span class="c4">▓</span><span class="c30">█</span><span class="c2">▓</span><span class="c4">▓</span><span class="c30">█</span><span class="c6">▓</span><span class="c39">▓</span><span class="c4">▓</span><span class="c6">█</span><span class="c2">█</span><span class="c21">▓</span><span class="c6">▓</span><span class="c21">█</span><span class="c2">█</span><span class="c4">▓</span><span class="c24">▓</span><span class="c30">█</span><span class="c2">█</span><span class="c13">▓</span><span class="c44"> ░</span><span class="c18">░</span><span class="c44"> </span><span class="c18"> </span><span class="c28">░</span><span class="c18"> </span><span class="c15">░</span><span class="c11">▒▒</span><span class="c10">▒</span><span class="c9">▓</span><span class="c11">▒</span><span class="c9">▓</span><span class="c14">▒</span><span class="c7">▓</span><span class="c9">▒</span> {}
<span class="c0">█</span><span class="c16">▒</span><span class="c7">▓</span><span class="c12">▒</span><span class="c18">░▒ </span><span class="c13">▓</span><span class="c2">████</span><span class="c0">█</span><span class="c2">██</span><span class="c3">█</span><span class="c24">▓</span><span class="c9">▒</span><span class="c7">▓</span><span class="c10">▒</span><span class="c22">░</span><span class="c44">  </span><span class="c28">░</span><span class="c44">░</span><span class="c31">░</span><span class="c44"> </span><span class="c31">░</span><span class="c44"> </span><span class="c40"> </span><span class="c9">▓</span><span class="c0">█</span><span class="c2">██</span><span class="c4">▓</span><span class="c2">██</span><span class="c6">▓</span><span class="c2">██</span><span class="c30">█</span><span class="c6">█</span><span class="c2">██</span><span class="c24">▓</span><span class="c2">██</span><span class="c24">▓</span><span class="c2">███</span><span class="c4">▓</span><span class="c2">██</span><span class="c4">▓</span><span class="c2">███</span><span class="c4">▓</span><span class="c2">███</span><span class="c10">▒</span><span class="c28"> ░</span><span class="c48">░</span><span class="c28">░</span><span class="c18">░</span><span class="c15">░</span><span class="c28">░</span><span class="c18">░░</span><span class="c15">░</span><span class="c18">░</span><span class="c20">░</span><span class="c15">░</span><span class="c20">░</span><span class="c15">▒</span><span class="c7">▓</span><span class="c16">▒
</span><span class="c47">█</span><span class="c9">▒</span><span class="c7">▓</span><span class="c12">▒</span><span class="c11">░</span><span class="c17">░</span><span class="c15">░</span><span class="c39">█</span><span class="c0">█</span><span class="c2">████</span><span class="c4">▓</span><span class="c24">▓</span><span class="c9">▓</span><span class="c13">█</span><span class="c22">░</span><span class="c11">▒</span><span class="c44">  </span><span class="c28">░</span><span class="c44">░░░ ░ </span><span class="c31"> </span><span class="c44"> </span><span class="c4">█</span><span class="c2">█</span><span class="c21">█</span><span class="c2">▓</span><span class="c4">▓</span><span class="c30">▓</span><span class="c2">█</span><span class="c4">▓</span><span class="c21">▓</span><span class="c6">█</span><span class="c21">▓</span><span class="c4">▓</span><span class="c2">█</span><span class="c30">▓</span><span class="c4">▓</span><span class="c2">█</span><span class="c30">█</span><span class="c4">▓</span><span class="c39">█</span><span class="c30">▓</span><span class="c2">▓</span><span class="c4">▓</span><span class="c30">█</span><span class="c2">▓</span><span class="c4">▓</span><span class="c21">▓</span><span class="c6">█</span><span class="c2">▓</span><span class="c4">▓</span><span class="c21">▓</span><span class="c4">▓</span><span class="c21">█</span><span class="c22">░</span><span class="c44">  </span><span class="c28"> </span><span class="c49"> </span><span class="c44">  </span><span class="c18"> </span><span class="c15">░</span><span class="c18">░</span><span class="c15">▒</span><span class="c18">░</span><span class="c15">▒░</span><span class="c18">░</span><span class="c14">▒</span><span class="c7">▓▓
</span><span class="c0">█</span><span class="c7">▓</span><span class="c8">▓</span><span class="c14">▓</span><span class="c18">░░</span><span class="c14">▓</span><span class="c4">█</span><span class="c6">█</span><span class="c4">▓</span><span class="c7">▓</span><span class="c9">▓</span><span class="c13">▓</span><span class="c9">▓</span><span class="c7">▓</span><span class="c15">░</span><span class="c22">░</span><span class="c28"> </span><span class="c44"> </span><span class="c28">░</span><span class="c44">░░</span><span class="c28">░</span><span class="c45">░</span><span class="c42">░</span><span class="c44">░</span><span class="c31">░</span><span class="c44">░ </span><span class="c22">▒</span><span class="c0">█</span><span class="c2">███</span><span class="c24">▓</span><span class="c2">███</span><span class="c24">▓</span><span class="c2">██</span><span class="c4">▓</span><span class="c2">██</span><span class="c4">▓</span><span class="c2">██</span><span class="c6">▓</span><span class="c2">███</span><span class="c4">▓</span><span class="c2">██</span><span class="c24">▓</span><span class="c2">██</span><span class="c21">▓</span><span class="c24">▓</span><span class="c6">▓</span><span class="c2">█</span><span class="c6">█</span><span class="c28"> </span><span class="c49"> </span><span class="c11">░</span><span class="c9">▓</span><span class="c7">▓</span><span class="c13">▓</span><span class="c9">▒</span><span class="c15">░</span><span class="c18"> </span><span class="c15">░</span><span class="c18">░</span><span class="c15">▒</span><span class="c43">▒</span><span class="c15">▒</span><span class="c20">░</span><span class="c7">▓</span><span class="c9">▒</span><span class="c4">▓
</span><span class="c0">█</span><span class="c3">▓</span><span class="c9">▒</span><span class="c7">▓</span><span class="c20">░</span><span class="c15">░</span><span class="c24">█</span><span class="c13">▓</span><span class="c14">▓</span><span class="c9">▓</span><span class="c34">▓</span><span class="c9">▓</span><span class="c15">░</span><span class="c28">░</span><span class="c18">░</span><span class="c44"> </span><span class="c18">░</span><span class="c44">░</span><span class="c18">░</span><span class="c44">░</span><span class="c45">░</span><span class="c28">░</span><span class="c44">░░░░░ </span><span class="c31"> </span><span class="c22">▒</span><span class="c2">██</span><span class="c4">█</span><span class="c2">▓</span><span class="c4">▓▓</span><span class="c2">█</span><span class="c4">▓▓</span><span class="c2">██</span><span class="c4">▓</span><span class="c2">██</span><span class="c4">▓</span><span class="c2">██</span><span class="c4">▓</span><span class="c21">▓</span><span class="c3">█</span><span class="c2">█</span><span class="c4">▓</span><span class="c2">██</span><span class="c3">▓</span><span class="c21">▓</span><span class="c4">▓</span><span class="c6">▓</span><span class="c21">▓</span><span class="c30">█</span><span class="c6">█</span><span class="c4">▓</span><span class="c22"> </span><span class="c6">█</span><span class="c2">█</span><span class="c0">██</span><span class="c2">█</span><span class="c0">█</span><span class="c2">█</span><span class="c7">▓</span><span class="c15">░</span><span class="c18">░</span><span class="c11">▒</span><span class="c15">▒</span><span class="c20">▒</span><span class="c11">░</span><span class="c13">▓</span><span class="c16">▒</span><span class="c3">█
</span><span class="c0">██</span><span class="c25">▒</span><span class="c4">▓</span><span class="c12">▒</span><span class="c15">░</span><span class="c11">▒</span><span class="c18">░</span><span class="c15">░</span><span class="c18">░</span><span class="c15">░</span><span class="c18">░░</span><span class="c15">░</span><span class="c44">░</span><span class="c15">░</span><span class="c28">░</span><span class="c44"> </span><span class="c28"> </span><span class="c44">░</span><span class="c28">░</span><span class="c44">░</span><span class="c28">░</span><span class="c44">░</span><span class="c28">░</span><span class="c44">░░░ </span><span class="c22">░</span><span class="c2">████</span><span class="c30">▓</span><span class="c2">██</span><span class="c4">▓</span><span class="c2">██</span><span class="c30">█</span><span class="c24">▓</span><span class="c2">█</span><span class="c4">█</span><span class="c24">▓</span><span class="c2">██</span><span class="c4">▓</span><span class="c2">▓██</span><span class="c4">▓</span><span class="c2">██</span><span class="c4">▓</span><span class="c24">▓</span><span class="c30">▓</span><span class="c39">▓</span><span class="c2">██</span><span class="c24">▓</span><span class="c2">██</span><span class="c24">█</span><span class="c7">▓</span><span class="c11">▒▒</span><span class="c13">▓</span><span class="c2">██</span><span class="c0">█</span><span class="c24">█</span><span class="c18">░</span><span class="c15">▒</span><span class="c20">▒</span><span class="c11">░</span><span class="c12">▒</span><span class="c7">▓</span><span class="c16">▒</span><span class="c0">█
██</span><span class="c3">▓</span><span class="c9">▒</span><span class="c7">▓</span><span class="c20">░</span><span class="c18">░</span><span class="c12">░</span><span class="c15">▒</span><span class="c18">░</span><span class="c15">░</span><span class="c18">░</span><span class="c22">░</span><span class="c18">░░</span><span class="c44"> </span><span class="c18"> </span><span class="c15">░</span><span class="c22">░</span><span class="c49"> </span><span class="c44">   </span><span class="c45"> </span><span class="c44">  </span><span class="c31"> </span><span class="c28"> </span><span class="c44"> </span><span class="c40"> </span><span class="c9">▓</span><span class="c2">█</span><span class="c30">█</span><span class="c2">█</span><span class="c24">▓</span><span class="c4">▓</span><span class="c2">█</span><span class="c39">▓</span><span class="c4">▓</span><span class="c30">█</span><span class="c24">█</span><span class="c4">▓</span><span class="c2">█▓</span><span class="c21">▓</span><span class="c3">█</span><span class="c2">█</span><span class="c39">▓</span><span class="c4">▓</span><span class="c6">█</span><span class="c2">█</span><span class="c39">▓</span><span class="c4">█</span><span class="c2">█</span><span class="c4">▓</span><span class="c21">▓</span><span class="c6">█</span><span class="c2">█</span><span class="c3">▓</span><span class="c6">█</span><span class="c2">██</span><span class="c4">▓</span><span class="c44">  </span><span class="c49"> </span><span class="c28"> </span><span class="c44"> </span><span class="c2">██</span><span class="c0">█</span><span class="c24">█</span><span class="c18">░</span><span class="c15">░</span><span class="c11">▒</span><span class="c20">░</span><span class="c7">▓</span><span class="c9">▒</span><span class="c3">▓</span><span class="c0">█
███</span><span class="c25">▒</span><span class="c7">▓</span><span class="c14">▒</span><span class="c18">░</span><span class="c15">▒</span><span class="c41">▒</span><span class="c15">▒</span><span class="c18">░</span><span class="c15">░</span><span class="c18">░</span><span class="c49"> </span><span class="c28"> </span><span class="c10">▒</span><span class="c6">█</span><span class="c2">██</span><span class="c9">▓</span><span class="c10">▒</span><span class="c15">▒</span><span class="c22">░</span><span class="c28">  </span><span class="c45"> </span><span class="c44">  </span><span class="c28"> </span><span class="c44"> </span><span class="c22"> </span><span class="c6">█</span><span class="c2">██</span><span class="c4">▓</span><span class="c2">██</span><span class="c3">▓</span><span class="c39">▓</span><span class="c2">██</span><span class="c4">▓</span><span class="c2">██</span><span class="c4">▓</span><span class="c2">██</span><span class="c3">▓</span><span class="c39">▓</span><span class="c2">█</span><span class="c30">█</span><span class="c4">▓</span><span class="c2">▓</span><span class="c4">▓</span><span class="c24">▓</span><span class="c2">██</span><span class="c4">▓</span><span class="c10">▒</span><span class="c2">██</span><span class="c0">█</span><span class="c9">▒</span><span class="c49"> </span><span class="c28"> </span><span class="c18">░</span><span class="c15">▒</span><span class="c24">█</span><span class="c2">██</span><span class="c6">█</span><span class="c11">▒</span><span class="c15">░</span><span class="c43">▒</span><span class="c18">░</span><span class="c14">▒</span><span class="c7">▓</span><span class="c16">▒</span><span class="c0">██
███</span><span class="c30">▓</span><span class="c25">▒</span><span class="c4">▓</span><span class="c20">░</span><span class="c12">░</span><span class="c15">▒</span><span class="c20">▒</span><span class="c15">░</span><span class="c18">░</span><span class="c11">▒</span><span class="c7">▓</span><span class="c6">█</span><span class="c2">██████</span><span class="c21">█</span><span class="c6">█</span><span class="c2">██</span><span class="c4">▓</span><span class="c9">▓</span><span class="c7">▓</span><span class="c4">█▓</span><span class="c9">▓</span><span class="c30">▓</span><span class="c24">█</span><span class="c2">█</span><span class="c4">▓</span><span class="c30">█</span><span class="c2">█</span><span class="c4">▓</span><span class="c24">▓</span><span class="c30">█</span><span class="c6">█</span><span class="c21">▓</span><span class="c4">█</span><span class="c2">█</span><span class="c4">▓▓</span><span class="c2">█</span><span class="c4">▓</span><span class="c21">▓</span><span class="c3">█</span><span class="c2">█</span><span class="c24">▓</span><span class="c4">▓▓</span><span class="c2">█</span><span class="c0">█</span><span class="c9">▓</span><span class="c45"> </span><span class="c28"> </span><span class="c6">█</span><span class="c2">█</span><span class="c0">█</span><span class="c2">█</span><span class="c10">▒</span><span class="c44"> </span><span class="c18">░</span><span class="c15">▒</span><span class="c10">▒▒</span><span class="c11">▒</span><span class="c18">░</span><span class="c15">░</span><span class="c20">▒</span><span class="c15">░</span><span class="c12">▒</span><span class="c7">▓</span><span class="c25">▒</span><span class="c3">█</span><span class="c0">██
████</span><span class="c7">▓</span><span class="c9">▒</span><span class="c7">▓</span><span class="c20">░</span><span class="c11">░</span><span class="c18">░</span><span class="c14">▒</span><span class="c7">█</span><span class="c24">█</span><span class="c13">█</span><span class="c9">▓</span><span class="c11">▒</span><span class="c15">░░</span><span class="c22"> </span><span class="c15">░</span><span class="c24">█</span><span class="c0">█</span><span class="c7">▓</span><span class="c2">██</span><span class="c0">█</span><span class="c2">█</span><span class="c21">█</span><span class="c2">█</span><span class="c4">█</span><span class="c2">███</span><span class="c30">█</span><span class="c24">▓</span><span class="c2">██</span><span class="c4">▓</span><span class="c2">███</span><span class="c4">▓</span><span class="c2">██</span><span class="c4">▓</span><span class="c2">███</span><span class="c24">▓</span><span class="c2">█</span><span class="c4">▓</span><span class="c21">▓</span><span class="c2">▓██</span><span class="c9">▓</span><span class="c44"> </span><span class="c18"> </span><span class="c44"> </span><span class="c28"> </span><span class="c15">░</span><span class="c7">▓</span><span class="c2">█</span><span class="c0">█</span><span class="c11">▒</span><span class="c18"> ░░ </span><span class="c15">░</span><span class="c18">░</span><span class="c12">▒</span><span class="c15">░</span><span class="c43">░</span><span class="c7">▓</span><span class="c9">▒</span><span class="c3">▓</span><span class="c0">███
█████</span><span class="c8">▒</span><span class="c9">▓</span><span class="c7">▓</span><span class="c20">░</span><span class="c11">▒</span><span class="c14">▓</span><span class="c15">▒</span><span class="c18">░  </span><span class="c49"> </span><span class="c28"> </span><span class="c18"> </span><span class="c49"> </span><span class="c28"> </span><span class="c44"> </span><span class="c2">██</span><span class="c11">░</span><span class="c10">▒</span><span class="c24">█</span><span class="c0">█</span><span class="c2">█</span><span class="c21">█</span><span class="c6">▓</span><span class="c21">▓</span><span class="c4">▓</span><span class="c24">▓</span><span class="c4">▓▓</span><span class="c2">█</span><span class="c6">█</span><span class="c21">▓</span><span class="c4">█</span><span class="c2">██</span><span class="c4">▓</span><span class="c2">██</span><span class="c4">▓</span><span class="c2">█</span><span class="c6">█</span><span class="c21">▓</span><span class="c4">▓</span><span class="c6">▓</span><span class="c21">▓</span><span class="c6">█</span><span class="c2">██</span><span class="c9">▒</span><span class="c44">  </span><span class="c28">░</span><span class="c22">░</span><span class="c49"> </span><span class="c28"> </span><span class="c18"> </span><span class="c15">▒</span><span class="c24">█</span><span class="c2">█</span><span class="c7">▓</span><span class="c15">░</span><span class="c18"> </span><span class="c15">░</span><span class="c18">░</span><span class="c12">▒</span><span class="c15">░</span><span class="c18">░</span><span class="c13">▓</span><span class="c16">▒</span><span class="c7">▒</span><span class="c0">████
██████</span><span class="c9">▒</span><span class="c8">▓</span><span class="c14">▓</span><span class="c15">░</span><span class="c20">░</span><span class="c18">░</span><span class="c15">░</span><span class="c18">░</span><span class="c15">░</span><span class="c24">█</span><span class="c15">░</span><span class="c18"> </span><span class="c28"> </span><span class="c49"> </span><span class="c10">▒</span><span class="c2">██</span><span class="c7">▓</span><span class="c44"> </span><span class="c28"> </span><span class="c10">▒</span><span class="c24">█</span><span class="c0">█</span><span class="c2">██</span><span class="c4">█</span><span class="c21">▓</span><span class="c6">▓</span><span class="c21">▓</span><span class="c2">█</span><span class="c4">▓</span><span class="c24">▓</span><span class="c2">██</span><span class="c4">█▓</span><span class="c2">█</span><span class="c4">█</span><span class="c21">▓</span><span class="c39">█</span><span class="c3">▓</span><span class="c39">▓</span><span class="c4">▓</span><span class="c39">█</span><span class="c2">█</span><span class="c0">█</span><span class="c4">█</span><span class="c15">░</span><span class="c44"> </span><span class="c28"> </span><span class="c48"> </span><span class="c18">░░</span><span class="c22">░</span><span class="c18">░</span><span class="c28">░</span><span class="c18"> </span><span class="c44"> </span><span class="c11">▒</span><span class="c13">█</span><span class="c7">█</span><span class="c14">▓</span><span class="c11">▒</span><span class="c15">▒</span><span class="c20">░</span><span class="c41">░</span><span class="c13">▓</span><span class="c16">▓</span><span class="c7">▒</span><span class="c0">█████
██████</span><span class="c1">█</span><span class="c9">▒</span><span class="c7">▓</span><span class="c9">▓</span><span class="c12">░</span><span class="c15">░</span><span class="c43">▒</span><span class="c15">░</span><span class="c14">▓</span><span class="c0">█</span><span class="c3">█</span><span class="c14">▒</span><span class="c10">▒▒</span><span class="c4">█</span><span class="c6">█</span><span class="c2">█</span><span class="c13">▓</span><span class="c44"> </span><span class="c18"> </span><span class="c44">  </span><span class="c10">▓</span><span class="c24">█</span><span class="c0">█</span><span class="c2">██</span><span class="c30">█</span><span class="c39">█</span><span class="c4">▓▓</span><span class="c21">▓</span><span class="c4">▓▓</span><span class="c39">▓</span><span class="c4">▓</span><span class="c21">▓</span><span class="c24">▓</span><span class="c4">▓▓█</span><span class="c2">██</span><span class="c0">█</span><span class="c3">█</span><span class="c10">▓</span><span class="c18"> </span><span class="c44"> </span><span class="c22">░</span><span class="c18">░</span><span class="c15">▒</span><span class="c44"> </span><span class="c28">░</span><span class="c49">░</span><span class="c15">░</span><span class="c18">░</span><span class="c15">░░</span><span class="c18">░ ▒</span><span class="c34">▓</span><span class="c11">▒</span><span class="c43">░</span><span class="c15">░</span><span class="c13">▓</span><span class="c16">▒</span><span class="c7">▒</span><span class="c0">██████
███████</span><span class="c47">█</span><span class="c7">▓</span><span class="c16">▒</span><span class="c7">▓</span><span class="c12">▒</span><span class="c18">░</span><span class="c15">░</span><span class="c50">▒</span><span class="c2">█</span><span class="c0">█</span><span class="c2">█</span><span class="c0">█</span><span class="c2">██</span><span class="c0">█</span><span class="c39">█</span><span class="c22">░</span><span class="c18"> </span><span class="c22">░</span><span class="c18">░</span><span class="c28">░</span><span class="c44"> </span><span class="c28"> </span><span class="c15">░</span><span class="c10">▒</span><span class="c24">█</span><span class="c2">█</span><span class="c0">█</span><span class="c2">█████</span><span class="c30">█</span><span class="c6">█</span><span class="c2">███</span><span class="c0">█</span><span class="c2">██</span><span class="c4">█</span><span class="c10">▒</span><span class="c18"> </span><span class="c44"> </span><span class="c28"> </span><span class="c18">░</span><span class="c49">░</span><span class="c22">░</span><span class="c24">██</span><span class="c15">▒</span><span class="c18">░</span><span class="c15">░</span><span class="c18">▒</span><span class="c15">▒</span><span class="c18">▒</span><span class="c15">▒▒</span><span class="c11">░</span><span class="c18">░</span><span class="c20">░</span><span class="c10">▒</span><span class="c7">▓</span><span class="c9">▒</span><span class="c7">▓</span><span class="c0">███████
█████████</span><span class="c24">▓</span><span class="c25">▒</span><span class="c7">▓</span><span class="c14">▓</span><span class="c17">░</span><span class="c18"> </span><span class="c15">░</span><span class="c9">▓</span><span class="c24">█</span><span class="c2">██</span><span class="c24">█</span><span class="c10">▒</span><span class="c15">░</span><span class="c18"> ░</span><span class="c49">░</span><span class="c15">░</span><span class="c18">░</span><span class="c15">░</span><span class="c28"> </span><span class="c49"> </span><span class="c28"> </span><span class="c44"> </span><span class="c22"> </span><span class="c15">▒</span><span class="c9">▓</span><span class="c7">▓</span><span class="c24">█</span><span class="c3">█</span><span class="c6">█</span><span class="c24">█</span><span class="c2">█</span><span class="c24">█</span><span class="c4">▓</span><span class="c13">▓</span><span class="c9">▓</span><span class="c10">▒</span><span class="c15">░</span><span class="c18"> </span><span class="c44"> </span><span class="c28"> </span><span class="c15">░</span><span class="c44">░</span><span class="c15">░</span><span class="c28">░</span><span class="c15">░</span><span class="c18">░</span><span class="c9">▓</span><span class="c11">▒</span><span class="c15">░</span><span class="c18">▒</span><span class="c15">▒</span><span class="c18">▒</span><span class="c15">▒</span><span class="c20">▒</span><span class="c11">░</span><span class="c20">░</span><span class="c15">░</span><span class="c14">▓</span><span class="c9">▓</span><span class="c16">▒</span><span class="c3">▓</span><span class="c0">████████
██████████</span><span class="c47">█</span><span class="c9">▒</span><span class="c16">▒</span><span class="c9">▓</span><span class="c12">▒</span><span class="c20">░</span><span class="c18"> </span><span class="c15">░</span><span class="c18">░░  ░</span><span class="c15">░░</span><span class="c28">▒</span><span class="c18">░</span><span class="c22">░</span><span class="c18">░</span><span class="c15">░</span><span class="c18">░</span><span class="c22">░</span><span class="c18">░</span><span class="c49"> </span><span class="c28"> </span><span class="c49"> </span><span class="c28"> </span><span class="c18"> </span><span class="c28"> </span><span class="c18"> </span><span class="c28"> </span><span class="c45"> </span><span class="c28"> </span><span class="c49"> </span><span class="c44"> </span><span class="c28"> </span><span class="c49"> </span><span class="c28"> </span><span class="c44"> </span><span class="c10">▓</span><span class="c11">▒</span><span class="c18">░░</span><span class="c15">░</span><span class="c18">░░</span><span class="c15">░</span><span class="c18">░</span><span class="c15">░</span><span class="c18">▒</span><span class="c15">▒</span><span class="c18">▒</span><span class="c11">▒</span><span class="c15">▒</span><span class="c41">░</span><span class="c17">░</span><span class="c12">▒</span><span class="c7">▓</span><span class="c9">▒</span><span class="c7">▒</span><span class="c1">█</span><span class="c0">█████████
████████████</span><span class="c5">▓</span><span class="c16">▒</span><span class="c7">▓▓</span><span class="c12">▒</span><span class="c17">░</span><span class="c18">░</span><span class="c17">░</span><span class="c15">░░▒▒</span><span class="c18">▒</span><span class="c15">▒</span><span class="c18">▒</span><span class="c15">░</span><span class="c18">▒</span><span class="c28">░</span><span class="c15">░</span><span class="c18">░░</span><span class="c15">▒</span><span class="c7">█</span><span class="c11">▒</span><span class="c49">░</span><span class="c15">░</span><span class="c44">░</span><span class="c15">░</span><span class="c44">░</span><span class="c18"> </span><span class="c14">▓</span><span class="c3">█</span><span class="c11">▒</span><span class="c18"> </span><span class="c28">░</span><span class="c15">░</span><span class="c18">░</span><span class="c12">▓</span><span class="c9">█</span><span class="c49">░</span><span class="c22">▒</span><span class="c18">░</span><span class="c15">▒░</span><span class="c18">▒</span><span class="c15">▒</span><span class="c18">▒</span><span class="c15">▒</span><span class="c18">▒</span><span class="c12">▒</span><span class="c15">░</span><span class="c20">░</span><span class="c12">▒</span><span class="c9">▓</span><span class="c7">▓</span><span class="c16">▒</span><span class="c3">▓</span><span class="c0">███████████
██████████████</span><span class="c7">▓</span><span class="c16">▒</span><span class="c7">▓</span><span class="c9">▓</span><span class="c12">▒</span><span class="c11">░</span><span class="c20">░</span><span class="c18">░</span><span class="c11">▒</span><span class="c18">▒</span><span class="c15">▒</span><span class="c18">▒</span><span class="c15">▒</span><span class="c18">▒</span><span class="c15">▒▒</span><span class="c18">░</span><span class="c15">░</span><span class="c18"> </span><span class="c4">█</span><span class="c6">█</span><span class="c15">▒</span><span class="c18">░░</span><span class="c15">░</span><span class="c18">░</span><span class="c15">░</span><span class="c28"> </span><span class="c13">█</span><span class="c24">█</span><span class="c15">▒</span><span class="c18">░</span><span class="c15">░</span><span class="c18">▒</span><span class="c15">░░░</span><span class="c18">▒</span><span class="c15">░</span><span class="c18">▒</span><span class="c15">▒</span><span class="c18">▒</span><span class="c15">▒▒</span><span class="c11">▒</span><span class="c20">▒</span><span class="c15">░</span><span class="c43">░</span><span class="c11">▒</span><span class="c7">▓</span><span class="c9">▓</span><span class="c8">▒</span><span class="c7">▓</span><span class="c0">█████████████
████████████████</span><span class="c5">▓</span><span class="c16">▒</span><span class="c7">▓</span><span class="c9">▓▒</span><span class="c12">▒</span><span class="c17">░</span><span class="c20">░</span><span class="c11">▒</span><span class="c17">░</span><span class="c41">▒</span><span class="c17">▒</span><span class="c15">▒</span><span class="c18">▒</span><span class="c15">▒</span><span class="c18">▒</span><span class="c15">░</span><span class="c11">▓▒</span><span class="c18">░</span><span class="c15">▒</span><span class="c18">▒</span><span class="c15">▒</span><span class="c18">▒</span><span class="c15">▒</span><span class="c18">░</span><span class="c15">▒</span><span class="c18">░</span><span class="c15">░</span><span class="c18">░</span><span class="c15">▒</span><span class="c18">▒</span><span class="c15">▒</span><span class="c18">░▒</span><span class="c15">▒</span><span class="c18">▒</span><span class="c11">▒</span><span class="c15">▒</span><span class="c18">▒</span><span class="c11">░</span><span class="c20">░</span><span class="c18">░</span><span class="c12">▒</span><span class="c9">▒▓</span><span class="c7">▓</span><span class="c9">▒</span><span class="c5">▓</span><span class="c0">███████████████
██████████████████</span><span class="c3">▓</span><span class="c7">▓▒</span><span class="c9">▓▒</span><span class="c10">▒</span><span class="c12">▒</span><span class="c15">░</span><span class="c20">░</span><span class="c15">░</span><span class="c41">░</span><span class="c17">▒</span><span class="c18">▒</span><span class="c15">▒░</span><span class="c20">░</span><span class="c15">░▒</span><span class="c18">▒</span><span class="c15">▒</span><span class="c18">▒</span><span class="c15">▒</span><span class="c18">▒</span><span class="c15">▒</span><span class="c18">░</span><span class="c15">░</span><span class="c18">░</span><span class="c15">▒</span><span class="c18">▒</span><span class="c15">▒</span><span class="c18">▒</span><span class="c11">▒</span><span class="c17">▒</span><span class="c41">▒</span><span class="c17">░</span><span class="c18">░</span><span class="c20">░</span><span class="c12">▒▒</span><span class="c9">▒▓</span><span class="c7">▓▒▓</span><span class="c3">▓</span><span class="c0">█████████████████
████████████████████</span><span class="c2">█</span><span class="c3">▓</span><span class="c8">▓</span><span class="c7">▓</span><span class="c9">▓▒▒</span><span class="c10">▒</span><span class="c12">▒</span><span class="c11">▒</span><span class="c17">▒</span><span class="c12">░</span><span class="c18">░</span><span class="c43">░</span><span class="c18">░</span><span class="c15">░</span><span class="c43">░</span><span class="c15">░</span><span class="c11">▒</span><span class="c20">░</span><span class="c11">▒</span><span class="c18">░</span><span class="c12">▒</span><span class="c18">░</span><span class="c11">░</span><span class="c20">░</span><span class="c11">░</span><span class="c20">░</span><span class="c11">░</span><span class="c20">░</span><span class="c15">░</span><span class="c12">▒</span><span class="c11">▒</span><span class="c34">▒</span><span class="c9">▓</span><span class="c7">▓</span><span class="c9">▓</span><span class="c7">▓▓</span><span class="c5">▓</span><span class="c47">█</span><span class="c0">███████████████████
████████████████████████</span><span class="c3">█▓</span><span class="c7">▓▓</span><span class="c9">▓</span><span class="c7">▓</span><span class="c9">▓▓</span><span class="c10">▒▒</span><span class="c14">▒</span><span class="c11">▒</span><span class="c12">▒</span><span class="c11">▒</span><span class="c12">▒</span><span class="c11">▒</span><span class="c12">▒▒</span><span class="c11">▒</span><span class="c12">▒</span><span class="c11">▒</span><span class="c34">▒</span><span class="c11">▒</span><span class="c10">▒</span><span class="c14">▒</span><span class="c9">▓▓</span><span class="c7">▓▓</span><span class="c8">▓</span><span class="c7">▓</span><span class="c4">▓</span><span class="c3">█</span><span class="c0">███████████████████████
████████████████████████████</span><span class="c30">█</span><span class="c3">██</span><span class="c7">▓</span><span class="c4">▓</span><span class="c7">▓▓▓▓▓</span><span class="c9">▓</span><span class="c7">▓</span><span class="c8">▓</span><span class="c9">▓</span><span class="c7">▓▓▓▓▓▓▓</span><span class="c4">▓</span><span class="c5">█</span><span class="c3">█</span><span class="c30">█</span><span class="c0">███████████████████████████</span></pre>
</div>
</body></html>'''.format(
        name,
        style_block_full_of_braces,
        server_summary_texts[0],
        server_summary_texts[1],
        server_summary_texts[2],
        server_summary_texts[3],
        server_summary_texts[4]
    )
    

class HydrusDomain( object ):
    
    def __init__( self, local_only ):
        
        self._local_only = local_only
        
    
    def CheckValid( self, client_ip ):
        
        # >::ffff:127.0.0.1
        #▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓█▓▓▓▓█████▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
        #▒▓▓▓▒▒▒▓▓▓▓▓▓▓▒▒▓▓▓▓▒▒░░░░  ░░▒▒▒▒▒▓▓▓▓▓▓▓▒▒▓▓▓▓▓▓▓▒▒▒▓▓▓
        #▓▓▓▓▓▓▓▒▓▓▓▓▓▓▓▓▒▒░░ ░░░░░       ░▒▒▓▓▓▓▓▓▓▓▒▓▓▓▓▓▒▓▓▓▒▓▓
        #▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒▒░▒▒▒▒▓▓▓▒▒▒▒▒▒▒▒▒▓▓▓▓▓▒▓▓▓▓▓▓▒▓▓▓▓▓▓▓▓▒▒
        #▒▒▓▓▓▓▓▓▓▒▒▓▓▒▒▒░░░░░▒▒▒▒▒▒▓▓▓▓█▓▓▓█▓▓▓▓▓▓▓▓▓▓▓▒▓▓▓▓▓▓▓▓▒
        #▓▓▓▓▓▓▓▓▓▓▓▒▓▓░         ░░░░▓▓█▓█▓▓▓█▓▓▓▓▓▓▓▓▓▓▓▓▒▓▓▓▓▓▒▓
        #▓▓▓▓▒▓▓▓▓▓▓▓▓░     ░        ▒▓██▓█▓▓▓▓▓▓█▓▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓
        #▓▓▓▓▓▒▓▓▓▓▓█▒   ░ ░░░         ▓████▓▓▓▓▓█▓▒▒▓▓▓▓▓▓▓▒▒▓▓▓▓
        #▓▓▓▓▓▓▓▒▓██▓  ░░░░░░░░░░░░ ░   ▒▓█▓▓▓▓▓▓▓█▓▓▒▓▓▓▓▓▒▓▓▓▒▓▓
        #▒▓▓▓▓▓▓▓▓██░ ░▒▒▒░▒░░░░░░░░░░░  ░▓█▓▓▓███▓█▓▓▓▒▓▓▓▓▓▓▓▓▒▒
        #▒▒▓▓▓▓▓▓▓█▓ ░▒░▒▒▒▒▒░░░░░░░░░░░░ ▒▓█▓█▓███▓▓▓▓▓▒▓▓▓▓▓▓▓▓▒
        #▓▓▓▒▓▓▓▓▓█▓░▒▒▒▒▒▒▒░▒░░░▒░░░░░░░░░▒▓▓▓▓▓█▒ ░▒▓▓▓▓▒▓▓▓▓▓▒▓
        #▓▓▓▓▒▓▓▓▓█▓░▒▓▒▒▒▒▒▒▒▒▒▒▒▒░░░░░░░░░░▒▓▓█▓░░▒▒▓▓▓▓▓▒▓▓▓▓▓▓
        #▓▓▓▓▓▒▓▓▓█▓░▒▒▒▒▒▒▒▒▒▒▒░░░░░░░░░░░░  ▒██▒▒▒░░▓▓▓▓▓▓▒▒▓▓▓▓
        #▓▓▓▓▓▓▓▒▒█▓░░▒▒▒▒▒▒▒▒▒▒▒  ░░░░░░░▒░░ ░█▓ ░▒▒░▓▓▓▓▓▒▓▓▓▒▓▓
        #▒▓▓▓▓▓▓▓▓▓▓▒▒▓▒▒▓▓▓▒▒▒▓▓▓▓▓▒▒▒▒▒▒▒▒░░▒█▓ ▒▒ ▒▓▓▓▓▓▓▓▓▓▓▒▓
        #▒▒▓▓▓▓▓▓▓▓▓▒▒▓▓█▓▓▓▓▓▒▒▓▓██▓▓▓▒▒▒▒░░░░░░░░░░░▓▓▓▓▓▓▓▓▓▓▓▒
        #▓▓▓▒▓▓▓▓▓░ ▓▒▓▓▓▓▓▓▒▓▒▒▒▒▒▒▒▒▒▒▒▒░░░░░░░░░▒▒  ▒█▓▓▓▓▓▓▓▒▓
        #▓▓▓▓▒▓▓▓▓▓▒▓▒▒▒▒▓▓▓▓▒░▒▒░░░▒▒▒░░░░░░░░░░░░░▒     ░▓▓████▓
        #▓▓▓▓▓▒▓▓▓▓▓▓▒▒▒▒▒▒▓▓░░░▒▒▒▒▒▒▒░░░░▒▒▒▒░░▒░░░          ▒▒▓
        #▓▓▓▓▓▓▓▒▒▓▓▓▓▒▒▒▒▓▓▒░░░░▒▒▒▒▒▓▒▒▒▒▒▒▒▒░░▒▒▒░   ░         
        #▒▓▓▓▓▓▓▓▓▒▓▓▓▓▓▓▓▓▓▓▓▒▒▒▒▒░░▒▓▓▓▒░▒▒▒▒▒▒▒▒▒   ▒░         
        #▒▒▓▓▓▓▓▓▓▓▒▓▓▓▓▓▓▓▓▓▓▓▒▒▒▒▒▒▒▓▓▓▒▒▒▒▒▒▒▒▒▒   ░▒░   ░░░░  
        #▓▓▓▒▓▓▓▓▓▓▓▓▒▓▓▓▓▓▓▓▓▓▓▓▓▓▒▒▒▒▒▒▒▒▒▒▒▒▓▓▒   ░▓░  ░░░░    
        #▓▓▓▓▓▒▓▓▓▓▓▓▓▓▓▓█▓▓▓▓▓▓▓▒▒▒▒░▒▒▒▒▒▒▒▒▓▓▒ ░ ░▓▒   ░░░░    
        #▓▓▓▓▓▒▒▓▓▓▓▓██▓▒░ ▒▓▓▓▓▒▓▒▒▒▒░░▒▒▒▒▓▓▒░░░ ▒▒▓░       ░▒  
        #▒▓▓▓▓▓▓▓▒▓▓█▓░     ▒▓▓▒▒▒▒░░▒▒▒▒▒▓▓▓▒░░░ ▒▒▒▒░░░░░░░▒▒░  
        #▒▒▓▓▓▓▓▓█▓▒░   ░ ░ ░▒▓▓▓▒▒▒▒▒▒▓▓█▓▒░░░░ ▒▒▒▒ ░░░▒▒░▒▒░░  
        #▒▒▒▓▓▓▓█▓░    ░ ░░ ▒░▒▒▒▒▓██████▓░░░░  ▒▒▒▒░ ░ ▒▒░▒▒░░   
        
        if self._local_only and client_ip not in ( '127.0.0.1', '::1', '::ffff:127.0.0.1' ):
            
            raise HydrusExceptions.InsufficientCredentialsException( 'Only local access allowed!' )
            
        
    
    def IsLocal( self ):
        
        return self._local_only
        
    
class HydrusResource( Resource ):
    
    def __init__( self, service, domain ):
        
        super().__init__()
        
        self._service = service
        self._service_key = self._service.GetServiceKey()
        self._domain = domain
        
    
    def _callbackCheckAccountRestrictions( self, request: HydrusServerRequest.HydrusRequest ):
        
        return request
        
    
    def _callbackCheckServiceRestrictions( self, request: HydrusServerRequest.HydrusRequest ):
        
        self._domain.CheckValid( request.getClientIP() )
        
        self._checkService( request )
        
        self._checkUserAgent( request )
        
        return request
        
    
    def _callbackDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        def wrap_thread_result( response_context ):
            
            request.hydrus_response_context = response_context
            
            return request
            
        
        if HydrusProfiling.IsProfileMode( 'client_api' ):
            
            d = deferToThread( self._profileJob, self._threadDoGETJob, request )
            
        else:
            
            d = deferToThread( self._threadDoGETJob, request )
            
        
        d.addCallback( wrap_thread_result )
        
        return d
        
    
    def _callbackDoOPTIONSJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        def wrap_thread_result( response_context ):
            
            request.hydrus_response_context = response_context
            
            return request
            
        
        if HydrusProfiling.IsProfileMode( 'client_api' ):
            
            d = deferToThread( self._profileJob, self._threadDoOPTIONSJob, request )
            
        else:
            
            d = deferToThread( self._threadDoOPTIONSJob, request )
            
        
        d.addCallback( wrap_thread_result )
        
        return d
        
    
    def _callbackDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        def wrap_thread_result( response_context ):
            
            request.hydrus_response_context = response_context
            
            return request
            
        
        if HydrusProfiling.IsProfileMode( 'client_api' ):
            
            d = deferToThread( self._profileJob, self._threadDoPOSTJob, request )
            
        else:
            
            d = deferToThread( self._threadDoPOSTJob, request )
            
        
        d.addCallback( wrap_thread_result )
        
        return d
        
    
    def _callbackEstablishAccountFromHeader( self, request: HydrusServerRequest.HydrusRequest ):
        
        return request
        
    
    def _callbackEstablishAccountFromArgs( self, request: HydrusServerRequest.HydrusRequest ):
        
        return request
        
    
    def _callbackParseGETArgs( self, request: HydrusServerRequest.HydrusRequest ):
        
        return request
        
    
    def _callbackParsePOSTArgs( self, request: HydrusServerRequest.HydrusRequest ):
        
        return request
        
    
    def _callbackRenderResponseContext( self, request: HydrusServerRequest.HydrusRequest ):
        
        self._CleanUpTempFile( request )
        
        if request.channel is None:
            
            # Connection was lost, it seems.
            # no need for request.finish
            
            return
            
        
        if request.requestHeaders.hasHeader( 'Origin' ):
            
            if self._service.SupportsCORS():
                
                request.setHeader( 'Access-Control-Allow-Origin', '*' )
                
            
        
        response_context: ResponseContext = request.hydrus_response_context
        
        if response_context.HasPath():
            
            path = response_context.GetPath()
            
            if not os.path.exists( path ):
                
                raise HydrusExceptions.NotFoundException( 'File not found. This was discovered later than expected, so hydev might like to know about this.' )
                
            
            filesize = os.path.getsize( path )
            
            offset_and_block_size_pairs = self._parseRangeHeader( request, filesize )
            
        else:
            
            offset_and_block_size_pairs = []
            
        
        status_code = response_context.GetStatusCode()
        
        if status_code == 200 and response_context.HasPath() and len( offset_and_block_size_pairs ) > 0:
            
            status_code = 206
            
        
        request.setResponseCode( status_code )
        
        for ( k, v, kwargs ) in response_context.GetCookies():
            
            request.addCookie( k, v, **kwargs )
            
        
        do_finish = True
        
        if response_context.IsAttachmentDownload():
            
            content_disposition_type = 'attachment'
            
        else:
            
            content_disposition_type = 'inline'
            
        
        max_age = response_context.GetMaxAge()

        if max_age is not None:
            
            request.setHeader( 'Expires', time.strftime( '%a, %d %b %Y %H:%M:%S GMT', time.gmtime( time.time() + max_age ) ) )
            
            request.setHeader( 'Cache-Control', 'max-age={}'.format( max_age ) )
            
        if response_context.HasPath():
            
            path = response_context.GetPath()
            
            filesize = os.path.getsize( path )
            
            mime = response_context.GetMime()
            
            content_type = HC.mime_mimetype_string_lookup[ mime ]
            
            ( base, filename ) = os.path.split( path )
            
            fileObject = open( path, 'rb' )
            
            content_disposition = f'{content_disposition_type}; filename="{filename}"'
            
            request.setHeader( 'Content-Disposition', str( content_disposition ) )
            
            if len( offset_and_block_size_pairs ) <= 1:
                
                request.setHeader( 'Content-Type', str( content_type ) )
                
                if len( offset_and_block_size_pairs ) == 0:
                    
                    content_length = filesize
                    
                    request.setHeader( 'Content-Length', str( content_length ) )
                    
                    producer = NoRangeStaticProducer( request, fileObject )
                    
                else:
                    
                    ( range_start, range_end, offset, block_size ) = offset_and_block_size_pairs[0]
                    
                    header_range_end = filesize - 1 if range_end is None else range_end
                    
                    content_length = block_size
                    
                    request.setHeader( 'Accept-Ranges', 'bytes' )
                    request.setHeader( 'Content-Range', 'bytes {}-{}/{}'.format( offset, header_range_end, filesize ) )
                    request.setHeader( 'Content-Length', str( content_length ) )
                    
                    producer = SingleRangeStaticProducer( request, fileObject, offset, block_size )
                    
                
            else:
                
                # hey, what a surprise, an http data transmission standard turned out to be a massive PITA
                # MultipleRangeStaticProducer is the lad to use, but you have to figure out your own separation bits, which have even more finicky rules. more than I can deal with with the current time I have
                # if/when you want to do this, check out the FileResource, it does it in its internal gubbins
                
                raise HydrusExceptions.RangeNotSatisfiableException( 'Can only support Single Range requests at the moment!' )
                
            
            producer.start()
            
            do_finish = False
            
        elif response_context.HasBody():
            
            mime = response_context.GetMime()
            
            body_bytes = response_context.GetBodyBytes()
            
            content_type = HC.mime_mimetype_string_lookup[ mime ]
            
            if mime == HC.TEXT_HTML:
                
                content_type += '; charset=UTF-8'
                
            
            content_length = len( body_bytes )
            
            content_disposition = content_disposition_type
            
            request.setHeader( 'Content-Type', content_type )
            request.setHeader( 'Content-Length', str( content_length ) )
            request.setHeader( 'Content-Disposition', content_disposition )

            request.write( body_bytes )
            
        else:
            
            content_length = 0
            
            if status_code != 204: # 204 is No Content
                
                request.setHeader( 'Content-Length', str( content_length ) )
                
            
        
        self._reportDataUsed( request, content_length )
        self._reportRequestUsed( request )
        
        if do_finish:
            
            request.finish()
            
        
    
    def _checkService( self, request: HydrusServerRequest.HydrusRequest ):
        
        return request
        
    
    def _checkUserAgent( self, request: HydrusServerRequest.HydrusRequest ):
        
        request.is_hydrus_user_agent = False
        
        if request.requestHeaders.hasHeader( 'User-Agent' ):
            
            user_agent_texts = request.requestHeaders.getRawHeaders( 'User-Agent' )
            
            user_agent_text = user_agent_texts[0]
            
            try:
                
                user_agents = user_agent_text.split( ' ' )
                
            except Exception as e:
                
                return # crazy user agent string, so just assume not a hydrus client
                
            
            for user_agent in user_agents:
                
                if '/' in user_agent:
                    
                    ( client, network_version ) = user_agent.split( '/', 1 )
                    
                    if client == 'hydrus':
                        
                        if ' ' in network_version:
                            
                            ( network_version, software_version_gumpf ) = network_version.split( ' ', 1 )
                            
                        
                        request.is_hydrus_user_agent = True
                        
                        network_version = int( network_version )
                        
                        if network_version == HC.NETWORK_VERSION:
                            
                            return
                            
                        else:
                            
                            if network_version < HC.NETWORK_VERSION: message = 'Your client is out of date; please download the latest release.'
                            else: message = 'This server is out of date; please ask its admin to update to the latest release.'
                            
                            raise HydrusExceptions.NetworkVersionException( 'Network version mismatch! This server\'s network version is ' + str( HC.NETWORK_VERSION ) + ', whereas your client\'s is ' + str( network_version ) + '! ' + message )
                            
                        
                    
                
            
        
    
    def _profileJob( self, call, request: HydrusServerRequest.HydrusRequest ):
        
        def do_it():
            
            request.profile_result = call( request )
            
        
        summary = 'Profiling {}: {}'.format( self._service.GetName(), request.path )
        
        HydrusProfiling.Profile( summary, do_it, min_duration_ms = HG.server_profile_min_job_time_ms )
        
        return request.profile_result
        
    
    def _DecompressionBombsOK( self, request: HydrusServerRequest.HydrusRequest ):
        
        return False
        
    
    def _errbackDisconnected( self, failure, request: HydrusServerRequest.HydrusRequest, request_deferred: defer.Deferred ):
        
        request_deferred.cancel()
        
        try:
            
            # this is a streaming file download etc.., we'll tell it to clean itself up
            if request.producer is not None:
                
                request.producer.stopProducing()
                
            
        except Exception as e:
            
            pass
            
        
        request.disconnected = True
        
        for c in request.disconnect_callables:
            
            try:
                
                c()
                
            except Exception as e:
                
                pass
                
            
        
    
    def _errbackHandleProcessingError( self, failure, request: HydrusServerRequest.HydrusRequest ):
        
        try:
            
            e = failure.value
            
            if isinstance( e, twisted.internet.defer.CancelledError ):
                
                # the connection disconnected and further deferred processing was cancelled
                
                return request
                
            
            if isinstance( e, HydrusExceptions.DBException ):
                
                e = e.db_e # could well be a DataException, which we want to promote
                
            
            try:
                
                self._CleanUpTempFile( request )
                
            except Exception as e:
                
                pass
                
            
            error_summary = str( e )
            
            if isinstance( e, HydrusExceptions.BadRequestException ):
                
                status_code = 400
                
            elif isinstance( e, ( HydrusExceptions.MissingCredentialsException, HydrusExceptions.DoesNotSupportCORSException ) ):
                
                status_code = 401
                
            elif isinstance( e, HydrusExceptions.InsufficientCredentialsException ):
                
                status_code = 403
                
            elif isinstance( e, ( HydrusExceptions.NotFoundException, HydrusExceptions.DataMissing, HydrusExceptions.FileMissingException ) ):
                
                status_code = 404
                
            elif isinstance( e, HydrusExceptions.NotAcceptable ):
                
                status_code = 406
                
            elif isinstance( e, HydrusExceptions.ConflictException ):
                
                status_code = 409
                
            elif isinstance( e, HydrusExceptions.RangeNotSatisfiableException ):
                
                status_code = 416
                
            elif isinstance( e, HydrusExceptions.SessionException ):
                
                status_code = 419
                
            elif isinstance( e, HydrusExceptions.UnprocessableEntity ):
                
                status_code = 422
                
            elif isinstance( e, HydrusExceptions.NetworkVersionException ):
                
                status_code = 426
                
            elif isinstance( e, ( HydrusExceptions.ServerBusyException, HydrusExceptions.ShutdownException ) ):
                
                status_code = 503
                
            elif isinstance( e, HydrusExceptions.BandwidthException ):
                
                status_code = 509
                
            elif isinstance( e, HydrusExceptions.ServerException ):
                
                status_code = 500
                
            else:
                
                status_code = 500
                
                HydrusData.DebugPrint( failure.getTraceback() )
                
                error_summary = f'The "{self._service.GetName()}" encountered an error it could not handle!\n\nHere is a full traceback of what happened. If you are using the hydrus client, it will be saved to your log. Please forward it to hydrus_dev@proton.me:\n\n' + failure.getTraceback()
                
            
            # TODO: maybe pull the cbor stuff down to hydrus core here and respond with Dumps( blah, requested_mime ) instead
            
            default_mime = HC.APPLICATION_JSON
            
            body_dict = {
                'error' : error_summary,
                'exception_type' : str( type( e ).__name__ ),
                'status_code' : status_code,
                'version' : HC.CLIENT_API_VERSION,
                'hydrus_version' : HC.SOFTWARE_VERSION
            }
            
            body = json.dumps( body_dict )
            
            response_context = ResponseContext( status_code, mime = default_mime, body = body )
            
            request.hydrus_response_context = response_context
            
            self._callbackRenderResponseContext( request )
            
        except Exception as e:
            
            try:
                
                HydrusData.DebugPrint( failure.getTraceback() )
                
            except Exception as e:
                
                pass
                
            
            if hasattr( request, 'channel' ) and request.channel is not None:
                
                try:
                    
                    request.setResponseCode( 500 )
                    
                except Exception as e:
                    
                    pass
                    
                
                try:
                    
                    request.write( failure.getTraceback() )
                    
                except Exception as e:
                    
                    pass
                    
                
            
            if not request.finished:
                
                try:
                    
                    request.finish()
                    
                except Exception as e:
                    
                    pass
                    
                
            
        
        return request
        
    
    def _parseHydrusNetworkAccessKey( self, request, key_required = True ):
        
        if not request.requestHeaders.hasHeader( 'Hydrus-Key' ):
            
            if key_required:
                
                raise HydrusExceptions.MissingCredentialsException( 'No hydrus key header found!' )
                
            else:
                
                return None
                
            
        
        hex_keys = request.requestHeaders.getRawHeaders( 'Hydrus-Key' )
        
        hex_key = hex_keys[0]
        
        try:
            
            access_key = bytes.fromhex( hex_key )
            
        except Exception as e:
            
            raise HydrusExceptions.BadRequestException( 'Could not parse the hydrus key!' )
            
        
        return access_key
        
    
    def _parseRangeHeader( self, request, filesize ):
        
        offset_and_block_size_pairs = []
        
        if request.requestHeaders.hasHeader( 'Range' ):
            
            range_headers = request.requestHeaders.getRawHeaders( 'Range' )
            
            range_header = range_headers[0]
            
            if '=' not in range_header:
                
                raise HydrusExceptions.BadRequestException( 'Did not understand range header!' )
                
            
            ( unit_gumpf, range_pairs_string ) = range_header.split( '=', 1 )
            
            if unit_gumpf != 'bytes':
                
                raise HydrusExceptions.RangeNotSatisfiableException( 'Do not support anything other than bytes in Range header!' )
                
            
            range_pair_strings = range_pairs_string.split( ',' )
            
            if True in ( '-' not in range_pair_string for range_pair_string in range_pair_strings ):
                
                raise HydrusExceptions.RangeNotSatisfiableException( 'Did not understand the Range header\'s range pair(s)!' )
                
            
            range_pairs = [ range_pair_string.strip().split( '-' ) for range_pair_string in range_pair_strings ]
            
            offset_and_block_size_pairs = []
            
            for ( range_start, range_end ) in range_pairs:
                
                if range_start == '':
                    
                    if range_end == '':
                        
                        raise HydrusExceptions.RangeNotSatisfiableException( 'Undefined Range header pair given!' )
                        
                    
                    range_start = None
                    
                else:
                    
                    range_start = abs( int( range_start ) )
                    
                
                if range_end == '':
                    
                    range_end = None
                    
                else:
                    
                    range_end = abs( int( range_end ) )
                    
                
                if range_start is not None and range_end is not None and range_start > range_end:
                    
                    raise HydrusExceptions.RangeNotSatisfiableException( 'The Range header had an invalid pair!' )
                    
                
                if range_start is None:
                    
                    offset = filesize - range_end
                    block_size = range_end
                    
                elif range_end is None:
                    
                    offset = range_start
                    block_size = filesize - range_start
                    
                else:
                    
                    if range_start > filesize:
                        
                        offset_and_block_size_pairs = []
                        
                        break
                        
                    
                    if range_end > filesize:
                        
                        range_end = filesize - 1
                        
                    
                    offset = range_start
                    block_size = ( range_end + 1 ) - range_start
                    
                
                offset_and_block_size_pairs.append( ( range_start, range_end, offset, block_size ) )
                
            
        
        return offset_and_block_size_pairs
        
    
    def _reportDataUsed( self, request, num_bytes ):
        
        self._service.ReportDataUsed( num_bytes )
        
        HG.controller.ReportDataUsed( num_bytes )
        
    
    def _reportRequestStarted( self, request: HydrusServerRequest.HydrusRequest ):
        
        pass
        
    
    def _reportRequestUsed( self, request: HydrusServerRequest.HydrusRequest ):
        
        self._service.ReportRequestUsed()
        
        HG.controller.ReportRequestUsed()
        
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        raise HydrusExceptions.NotFoundException( 'This service does not support that request!' )
        
    
    def _threadDoOPTIONSJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        allowed_methods = []
        
        if self.__class__._threadDoGETJob is not HydrusResource._threadDoGETJob:
            
            allowed_methods.append( 'GET' )
            
        
        if self.__class__._threadDoPOSTJob is not HydrusResource._threadDoPOSTJob:
            
            allowed_methods.append( 'POST' )
            
        
        allowed_methods_string = ', '.join( allowed_methods )
        
        if request.requestHeaders.hasHeader( 'Origin' ):
            
            # this is a CORS request
            
            if self._service.SupportsCORS():
                
                request.setHeader( 'Access-Control-Allow-Headers', '*' )
                request.setHeader( 'Access-Control-Allow-Origin', '*' )
                request.setHeader( 'Access-Control-Allow-Methods', allowed_methods_string )
                request.setHeader( 'Access-Control-Max-Age', "86400" )
                
            else:
                
                # 401
                raise HydrusExceptions.DoesNotSupportCORSException( 'This service does not support CORS.' )
                
            
        else:
            
            # regular OPTIONS request
            
            request.setHeader( 'Allow', allowed_methods_string )
            
        
        # 204 No Content
        response_context = ResponseContext( 200, mime = HC.TEXT_PLAIN )
        
        return response_context
        
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        raise HydrusExceptions.NotFoundException( 'This service does not support that request!' )
        
    
    def _CleanUpTempFile( self, request: HydrusServerRequest.HydrusRequest ):
        
        if hasattr( request, 'temp_file_info' ):
            
            ( os_file_handle, temp_path ) = request.temp_file_info
            
            HydrusTemp.CleanUpTempPath( os_file_handle, temp_path )
            
            del request.temp_file_info
            
        
    
    def render_GET( self, request: HydrusServerRequest.HydrusRequest ):
        
        self._reportRequestStarted( request )
        
        d = defer.Deferred()
        
        d.addCallback( self._callbackCheckServiceRestrictions )
        
        d.addCallback( self._callbackEstablishAccountFromHeader )
        
        d.addCallback( self._callbackParseGETArgs )
        
        d.addCallback( self._callbackEstablishAccountFromArgs )
        
        d.addCallback( self._callbackCheckAccountRestrictions )
        
        d.addCallback( self._callbackDoGETJob )
        
        d.addCallback( self._callbackRenderResponseContext )
        
        d.addErrback( self._errbackHandleProcessingError, request )
        
        request.notifyFinish().addErrback( self._errbackDisconnected, request, d )
        
        reactor.callLater( 0, d.callback, request )
        
        return NOT_DONE_YET
        
    
    def render_OPTIONS( self, request: HydrusServerRequest.HydrusRequest ):
        
        self._reportRequestStarted( request )
        
        d = defer.Deferred()
        
        d.addCallback( self._callbackCheckServiceRestrictions )
        
        d.addCallback( self._callbackDoOPTIONSJob )
        
        d.addCallback( self._callbackRenderResponseContext )
        
        d.addErrback( self._errbackHandleProcessingError, request )
        
        request.notifyFinish().addErrback( self._errbackDisconnected, request, d )
        
        reactor.callLater( 0, d.callback, request )
        
        return NOT_DONE_YET
        
    
    def render_POST( self, request: HydrusServerRequest.HydrusRequest ):
        
        self._reportRequestStarted( request )
        
        d = defer.Deferred()
        
        d.addCallback( self._callbackCheckServiceRestrictions )
        
        d.addCallback( self._callbackEstablishAccountFromHeader )
        
        d.addCallback( self._callbackParsePOSTArgs )
        
        d.addCallback( self._callbackEstablishAccountFromArgs )
        
        d.addCallback( self._callbackCheckAccountRestrictions )
        
        d.addCallback( self._callbackDoPOSTJob )
        
        d.addCallback( self._callbackRenderResponseContext )
        
        d.addErrback( self._errbackHandleProcessingError, request )
        
        request.notifyFinish().addErrback( self._errbackDisconnected, request, d )
        
        reactor.callLater( 0, d.callback, request )
        
        return NOT_DONE_YET
        
    
class HydrusResourceRobotsTXT( HydrusResource ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        body = '''User-agent: *
Disallow: /'''
        
        response_context = ResponseContext( 200, mime = HC.TEXT_PLAIN, body = body )
        
        return response_context
        
    
class HydrusResourceWelcome( HydrusResource ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        body = GenerateEris( self._service )
        
        response_context = ResponseContext( 200, mime = HC.TEXT_HTML, body = body )
        
        return response_context
        
    
class ResponseContext( object ):
    
    def __init__( self, status_code, mime = HC.APPLICATION_JSON, body = None, path = None, cookies = None, is_attachment = False, max_age = None ):
        
        if body is None:
            
            body_bytes = None
            
        elif isinstance( body, HydrusSerialisable.SerialisableBase ):
            
            body_bytes = body.DumpToNetworkBytes()
            
        elif isinstance( body, str ):
            
            body_bytes = bytes( body, 'utf-8' )
            
        elif isinstance( body, bytes ):
            
            body_bytes = body
            
        else:
            
            raise Exception( 'Was given an incompatible object to respond with: ' + repr( body ) )
            
        
        if cookies is None:
            
            cookies = []
            
        
        if max_age is None:
            
            if body is not None:
                
                max_age = 4
                
            elif path is not None:
                
                max_age = 86400 * 365
                
            
        
        self._status_code = status_code
        self._mime = mime
        self._body_bytes = body_bytes
        self._path = path
        self._cookies = cookies
        self._is_attachment = is_attachment
        self._max_age = max_age
        
    
    def GetBodyBytes( self ):
        
        return self._body_bytes
        
    
    def GetCookies( self ):
        
        return self._cookies
        
    
    def GetMime( self ):
        
        return self._mime
        
    
    def GetPath( self ):
        
        return self._path
        
    
    def GetStatusCode( self ):
        
        return self._status_code
        

    def GetMaxAge( self ):
        
        return self._max_age
        
    
    def SetMaxAge( self, age ):
        
        self._max_age = age
        
    
    def HasBody( self ):
        
        return self._body_bytes is not None
        
    
    def HasPath( self ):
        
        return self._path is not None
        
    
    def IsAttachmentDownload( self ):
        
        return self._is_attachment
        
    
