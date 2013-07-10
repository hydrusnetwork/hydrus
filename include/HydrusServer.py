import BaseHTTPServer
import Cookie
import hashlib
import httplib
import HydrusAudioHandling
import HydrusConstants as HC
import HydrusDocumentHandling
import HydrusFlashHandling
import HydrusImageHandling
import HydrusVideoHandling
import os
import SocketServer
import traceback
import urllib
import wx
import yaml

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
                   <font color="gray">MM</font>::<font color="gray">M</font>:::::::::::::::::::<font color="gray">MMM</font>              THIS IS THE HYDRUS SERVER ADMIN SERVICE, VERSION ''' + str( HC.SOFTWARE_VERSION ) + '''
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
        <p>This hydrus client uses software version ''' + str( HC.SOFTWARE_VERSION ) + ''' and network version ''' + str( HC.NETWORK_VERSION ) + '''.</p>
        <p>It only serves requests from 127.0.0.1.</p>
    </body>
</html>'''

ROOT_MESSAGE_BEGIN = '''<html>
    <head>
        <title>hydrus service</title>
    </head>
    <body>
        <p>This hydrus service uses software version ''' + str( HC.SOFTWARE_VERSION ) + ''' and network version ''' + str( HC.NETWORK_VERSION ) + '''.</p>
        <p>'''

ROOT_MESSAGE_END = '''</p>
    </body>
</html>'''

def ParseAccessKey( authorisation_text ):
    
    if authorisation_text is None: access_key = None
    else:
        
        ( format, access_key_encoded ) = authorisation_text.split( ' ' )
        
        if format != 'hydrus_network': raise HC.ForbiddenException( 'Authorisation format error!' )
        
        try: access_key = access_key_encoded.decode( 'hex' )
        except: raise HC.ForbiddenException( 'Attempted to parse access key, but could not understand it.' )
        
    
    return access_key
    
def ParseFileArguments( file ):
    
    args = {}
    
    file = HydrusImageHandling.ConvertToPngIfBmp( file )
    
    args[ 'file' ] = file
    
    size = len( file )
    
    if size == 0: raise HC.ForbiddenException( 'Not interested in files of zero length' )
    
    mime = HC.GetMimeFromString( file )
    
    if mime not in HC.ALLOWED_MIMES: raise HC.ForbiddenException( 'Currently, only jpg, gif, bmp, png, swf, pdf, flv and mp3 are supported.' )
    
    hash = hashlib.sha256( file ).digest()
    
    args[ 'hash' ] = hash
    args[ 'size' ] = size
    args[ 'mime' ] = mime
    
    if mime in HC.IMAGES:
        
        try: image_container = HydrusImageHandling.RenderImageFromFile( file, hash )
        except: raise HC.ForbiddenException( 'Could not load that file as an image.' )
        
        ( width, height ) = image_container.GetSize()
        
        args[ 'width' ] = width
        args[ 'height' ] = height
        
        if image_container.IsAnimated():
            
            duration = image_container.GetTotalDuration()
            num_frames = image_container.GetNumFrames()
            
            args[ 'duration' ] = duration
            args[ 'num_frames' ] = num_frames
            
        
        try: thumbnail = HydrusImageHandling.GenerateThumbnailFileFromFile( file, HC.UNSCALED_THUMBNAIL_DIMENSIONS )
        except: raise HC.ForbiddenException( 'Could not generate thumbnail from that file.' )
        
        args[ 'thumbnail' ] = thumbnail
        
    elif mime == HC.APPLICATION_FLASH:
        
        ( ( width, height ), duration, num_frames ) = HydrusFlashHandling.GetFlashProperties( file )
        
        args[ 'width' ] = width
        args[ 'height' ] = height
        args[ 'duration' ] = duration
        args[ 'num_frames' ] = num_frames
        
    elif mime == HC.VIDEO_FLV:
        
        ( ( width, height ), duration, num_frames ) = HydrusVideoHandling.GetFLVProperties( file )
        
        args[ 'width' ] = width
        args[ 'height' ] = height
        args[ 'duration' ] = duration
        args[ 'num_frames' ] = num_frames
        
    elif mime == HC.APPLICATION_PDF:
        
        num_words = HydrusDocumentHandling.GetPDFNumWords( file )
        
        args[ 'num_words' ] = num_words
        
    elif mime == HC.AUDIO_MP3:
        
        args[ 'duration' ] = HydrusAudioHandling.GetMP3Duration( file )
        
    
    return args
    
def ParseHTTPGETArguments( path ):
    
    path = urllib.unquote( path )
    
    arguments = {}
    
    if '?' in path:
        
        raw_arguments = path.split( '?', 1 )[1]
        
        for raw_argument in raw_arguments.split( '&' ):
            
            if '=' in raw_argument:
                
                [ name, value ] = raw_argument.split( '=', 1 )
                
                if name in ( 'begin', 'num', 'expiration', 'subject_account_id', 'service_type', 'service_port', 'since' ):
                    
                    try: arguments[ name ] = int( value )
                    except: raise HC.ForbiddenException( 'I was expecting to parse ' + name + ' as an integer, but it failed.' )
                    
                elif name in ( 'access_key', 'title', 'subject_access_key', 'contact_key', 'hash', 'subject_hash', 'subject_tag', 'message_key' ):
                    
                    try: arguments[ name ] = value.decode( 'hex' )
                    except: raise HC.ForbiddenException( 'I was expecting to parse ' + name + ' as a hex-encoded string, but it failed.' )
                    
                
            
        
        if 'subject_account_id' in arguments: arguments[ 'subject_identifier' ] = HC.AccountIdentifier( access_key = arguments[ 'subject_account_id' ] )
        elif 'subject_access_key' in arguments: arguments[ 'subject_identifier' ] = HC.AccountIdentifier( access_key = arguments[ 'subject_access_key' ] )
        elif 'subject_tag' in arguments and 'subject_hash' in arguments: arguments[ 'subject_identifier' ] = HC.AccountIdentifier( tag = arguments[ 'subject_tag' ], hash = arguments[ 'subject_hash' ] )
        elif 'subject_hash' in arguments: arguments[ 'subject_identifier' ] = HC.AccountIdentifier( hash = arguments[ 'subject_hash' ] )
        
    
    return arguments
    
def ParseHTTPPOSTArguments( request, body ):
    
    if request == 'file': args = ParseFileArguments( body )
    else:
        
        if body == '': args = ()
        else: args = yaml.safe_load( body )
        
    
    return args
    
def ParseHTTPRequest( path ):
    
    path = urllib.unquote( path )
    
    if not path.startswith( '/' ): return ''
    
    after_slash = path.split( '/', 1 )[1]
    
    return after_slash.split( '?', 1 )[0]
    
def ParseSessionKey( cookie_text ):
    
    if cookie_text is None: session_key = None
    else:
        
        try:
            
            cookies = Cookie.SimpleCookie( cookie_text )
            
            if 'session_key' not in cookies: session_key = None
            else: session_key = cookies[ 'session_key' ].value.decode( 'hex' )
            
        except: raise Exception( 'Problem parsing cookie!' )
        
    
    return session_key
    
class HydrusHTTPServer( SocketServer.ThreadingMixIn, BaseHTTPServer.HTTPServer ):
    
    def __init__( self, service_identifier, message = '' ):
        
        #self.daemon_threads = True
        
        self._service_identifier = service_identifier
        self._message = message
        
        port = service_identifier.GetPort()
        
        BaseHTTPServer.HTTPServer.__init__( self, ( '', port ), HydrusHTTPRequestHandler )
        
        HC.pubsub.sub( self, 'shutdown', 'shutdown' )
        
    
    def GetServiceIdentifier( self ): return self._service_identifier
    
    def GetMessage( self ): return self._message
    
    def SetMessage( self, message ): self._message = message
    
class HydrusHTTPRequestHandler( BaseHTTPServer.BaseHTTPRequestHandler ):
    
    server_version = 'hydrus/' + str( HC.NETWORK_VERSION )
    protocol_version = 'HTTP/1.1'
    
    with open( HC.STATIC_DIR + os.path.sep + 'hydrus.ico', 'rb' ) as f: _favicon = f.read()
    
    def __init__( self, request, client_address, server ):
        
        self._service_identifier = server.GetServiceIdentifier()
        
        try: BaseHTTPServer.BaseHTTPRequestHandler.__init__( self, request, client_address, server )
        except: self.log_string( 'Connection reset by peer' )
        
    
    def _ProcessRequest( self, request_type ):
        
        try:
            
            try:
                
                default_mime = HC.TEXT_HTML
                default_encoding = lambda x: unicode( x )
                
                user_agent_text = self.headers.getheader( 'User-Agent' )
                
                if user_agent_text is not None:
                    
                    user_agents = user_agent_text.split( ' ' )
                    
                    for user_agent in user_agents:
                        
                        if '/' in user_agent:
                            
                            ( client, network_version ) = user_agent.split( '/', 1 )
                            
                            if client == 'hydrus':
                                
                                default_mime = HC.APPLICATION_YAML
                                default_encoding = lambda x: yaml.safe_dump( unicode( x ) )
                                
                                network_version = int( network_version )
                                
                                if network_version != HC.NETWORK_VERSION:
                                    
                                    if network_version < HC.NETWORK_VERSION: message = 'Please download the latest release.'
                                    else: message = 'Please ask this server\'s admin to update to the latest release.'
                                    
                                    raise HC.NetworkVersionException( 'Network version mismatch! This server\'s network version is ' + str( HC.NETWORK_VERSION ) + ', whereas your client\'s is ' + str( network_version ) + '! ' + message )
                                    
                                
                            
                        
                    
                
                ( ip, port ) = self.client_address
                
                service_type = self._service_identifier.GetType()
                
                if service_type == HC.LOCAL_FILE and ip != '127.0.0.1': raise HC.ForbiddenException( 'Only local access allowed!' )
                
                request = ParseHTTPRequest( self.path )
                
                if ( service_type, request_type, request ) not in HC.ALLOWED_REQUESTS: raise HC.ForbiddenException( 'This service does not support that request.' )
                
                if request_type == HC.GET:
                    
                    request_args = ParseHTTPGETArguments( self.path )
                    request_length = 0
                    
                elif request_type == HC.POST:
                    
                    body = self.rfile.read( int( self.headers.getheader( 'Content-Length', default = 0 ) ) )
                    
                    request_args = ParseHTTPPOSTArguments( request, body )
                    request_length = len( body )
                    
                
                if request == '':
                    
                    if service_type == HC.LOCAL_FILE: body = CLIENT_ROOT_MESSAGE
                    else:
                        
                        message = self.server.GetMessage()
                        
                        body = ROOT_MESSAGE_BEGIN + message + ROOT_MESSAGE_END
                        
                    
                    response_context = HC.ResponseContext( 200, mime = HC.TEXT_HTML, body = body )
                    
                elif request == 'favicon.ico': response_context = HC.ResponseContext( 200, mime = HC.IMAGE_ICON, body = self._favicon, filename = 'favicon.ico' )
                else:
                    
                    if service_type == HC.LOCAL_FILE: response_context = HC.app.ProcessServerRequest( request_type, request, request_args )
                    else:
                        
                        session_key = ParseSessionKey( self.headers.getheader( 'Cookie' ) )
                        access_key = ParseAccessKey( self.headers.getheader( 'Authorization' ) )
                        
                        response_context = HC.app.GetDB().AddJobServer( self._service_identifier, access_key, session_key, ip, request_type, request, request_args, request_length )
                        
                    
                
            except:
                
                # wx.MessageBox( traceback.format_exc() )
                
                raise
                
            
        except KeyError: response_context = HC.ResponseContext( 403, mime = default_mime, body = default_encoding( 'It appears one or more parameters required for that request were missing.' ) )
        except HC.PermissionException as e: response_context = HC.ResponseContext( 401, mime = default_mime, body = default_encoding( e ) )
        except HC.ForbiddenException as e: response_context = HC.ResponseContext( 403, mime = default_mime, body = default_encoding( e ) )
        except HC.NotFoundException as e:response_context = HC.ResponseContext( 404, mime = default_mime, body = default_encoding( e ) )
        except HC.NetworkVersionException as e: response_context = HC.ResponseContext( 426, mime = default_mime, body = default_encoding( e ) )
        except HC.SessionException as e: response_context = HC.ResponseContext( 403, mime = default_mime, body = default_encoding( 'Session not found!' ) )
        except Exception as e:
            
            self.log_string( traceback.format_exc() )
            
            response_context = HC.ResponseContext( 500, mime = default_mime, body = default_encoding( 'The repository encountered an error it could not handle! Here is a dump of what happened, which will also be written to your client.log file. If it persists, please forward it to hydrus.admin@gmail.com:' + os.linesep + os.linesep + traceback.format_exc() ) )
            
        
        try: self._Respond( response_context )
        except: pass # wx.MessageBox( traceback.format_exc() )
        
    
    def _Respond( self, response_context ):
        
        status_code = response_context.GetStatusCode()
        
        self.send_response( status_code )
        
        for cookie in response_context.GetCookies(): self.send_header( 'Set-Cookie', cookie )
        
        if response_context.HasBody():
            
            ( mime, body ) = response_context.GetMimeBody()
            
            content_type = HC.mime_string_lookup[ mime ]
            
            if response_context.HasFilename():
                
                filename = response_context.GetFilename()
                
                content_type += '; ' + filename
                
            
            self.send_header( 'Content-Type', content_type )
            self.send_header( 'Content-Length', len( body ) )
            
            self.end_headers()
            
            self.wfile.write( body )
            
        else:
            
            self.send_header( 'Content-Length', '0' )
            self.end_headers()
            
        
    
    def do_GET( self ): self._ProcessRequest( HC.GET )
    
    def do_OPTIONS( self ):
        
        service_type = self._service_identifier.GetType()
        
        if service_type == HC.LOCAL_FILE and ip != '127.0.0.1': raise HC.ForbiddenException( 'Only local access allowed!' )
        
        request = ParseHTTPRequest( self.path )
        
        allowed = [ 'OPTIONS' ]
        
        if ( service_type, HC.GET, request ) in HC.ALLOWED_REQUESTS: allowed.append( 'GET' )
        if ( service_type, HC.POST, request ) in HC.ALLOWED_REQUESTS: allowed.append( 'POST' )
        
        self.send_response( 200 )
        
        self.send_header( 'Allow', ','.join( allowed ) )
        self.end_headers()
        
    
    def do_POST( self ): self._ProcessRequest( HC.POST )
    
    def log_message( self, format, *args ): print( "[%s] %s%s" % ( self.log_date_time_string(), format%args, os.linesep ) )
    
    def log_request( self, *args ): pass # to start logging a little about every request, just delete this def. the default pushes to log_message
    
    def log_string( self, message ): print( message )
    
    # this overrides the base method to no longer use the class variable server_version
    def version_string( self ):
        
        service_type = self._service_identifier.GetType()
        
        server_version = HC.service_string_lookup[ service_type ] + '/' + str( HC.NETWORK_VERSION )
        
        return server_version + ' ' + self.sys_version
        
