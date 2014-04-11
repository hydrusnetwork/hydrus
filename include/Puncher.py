# Licensed under the MIT license
# http://opensource.org/licenses/mit-license.php

# Copyright 2010 Frank Scholz <coherence@beebits.net>

from twisted.internet import reactor

import warnings
warnings.simplefilter("ignore")
from coherence.base import Coherence
from coherence.upnp.devices.control_point import ControlPoint


class Puncher(object):

    def __init__(self,command,config):
        #print "command %r %r %r" %(command,config,config.subOptions)
        self.config = config
        self.locked = False
        if command == None:
            self.command = 'show-devices'
        else:
            self.command = command

        if self.command == 'show-devices':
            self.locked = None

        if self.command == 'add-mapping':
            if self.config.subOptions['internal-host'] == None:
                raise Exception("internal-host parameter missing")
            if self.config.subOptions['internal-port'] == None:
                raise Exception("internal-port parameter missing")
            if self.config.subOptions['protocol'].lower() not in ['tcp','udp']:
                raise Exception("protocol value invalid")
            if self.config.subOptions['active'].lower() in ['y','true','1','yes']:
                self.config.subOptions['active'] = True
            else:
                self.config.subOptions['active'] = False
            if self.config.subOptions['remote-host'].lower() in ['""','any']:
                self.config.subOptions['remote-host'] = ''
            if self.config.subOptions['external-port'] == None:
                self.config.subOptions['external-port'] = self.config.subOptions['internal-port']

        if self.command == 'delete-mapping':
            if self.config.subOptions['remote-host'] == None:
                raise Exception("remote-host parameter missing")
            if self.config.subOptions['external-port'] == None:
                raise Exception("external-port parameter missing")
            if self.config.subOptions['protocol'].lower() not in ['tcp','udp']:
                raise Exception("protocol value invalid")

        coherence_config = {}
        coherence_config['logmode'] = 'none'

        self.control_point = ControlPoint(Coherence(coherence_config),auto_client=['InternetGatewayDevice'])
        self.control_point.connect(self.igd_found, 'Coherence.UPnP.ControlPoint.InternetGatewayDevice.detected')
        self.control_point.connect(self.igd_removed, 'Coherence.UPnP.ControlPoint.InternetGatewayDevice.removed')

        self.timeout = reactor.callLater(int(self.config['timeout']),self.stop)
        self.devices = {}

        self.reports = {'show-devices': self.show_devices,
                        'show-mappings': self.show_mappings,
                        'info': self.show_info}


    def show_devices(self):
        for uuid in self.devices.keys():
            print "%s with uuid:%s" % (self.devices[uuid]['friendly_name'], uuid)

    def show_info(self):
        for uuid in self.devices.keys():
            print "%s with uuid:%s" % (self.devices[uuid]['friendly_name'], uuid)
        if len(self.devices) > 0:
            print "External IP address: ", self.external_ip_address
            print "Number of port-mappings: ", self.port_mapping_number_of_entries

    def show_mappings(self):
        for uuid in self.devices.keys():
            print "%s with uuid:%s" % (self.devices[uuid]['friendly_name'], uuid)
        mappings = self.devices[uuid].get('mappings',None)
        if mappings == None or len(mappings) == 0:
            print "no port-mappings found"
        else:
            print "Ext. Port | Remote Host    | Int. Port | Internal Host   | Prot. | active | duration | description"
            print "=" * 100
            for mapping in mappings:
                if mapping['NewLeaseDuration'] == '0':
                    mapping['NewLeaseDuration'] = 'infinite'
                else:
                    mapping['NewLeaseDuration'] += 'sec'
                if mapping['NewRemoteHost'] == '':
                    mapping['NewRemoteHost'] = 'any'
                if mapping['NewEnabled'] == '1':
                    mapping['NewEnabled'] = 'yes'
                else:
                    mapping['NewEnabled'] = 'no'
                print "    %05s | %-14s |     %05s | %-14s | %5s | %6s | %8s | %s" % (mapping['NewExternalPort'],
                                                                                   mapping['NewRemoteHost'],
                                                                                   mapping['NewInternalPort'],
                                                                                   mapping['NewInternalClient'],
                                                                                   mapping['NewProtocol'],
                                                                                   mapping['NewEnabled'],
                                                                                   mapping['NewLeaseDuration'],
                                                                                   mapping['NewPortMappingDescription'])
            print "=" * 100

    def stop(self,quiet=False):
        try:
            self.timeout.cancel()
        except:
            pass

        if quiet == False:
            if len(self.devices) == 0:
                print "no InternetGatewayDevice found"
            elif len(self.devices) == 1:
                print "1 InternetGatewayDevice found:"
            else:
                print "%d InternetGatewayDevices found:" % len(self.devices)
            self.reports.get(self.command,self.show_devices)()
        print ""
        reactor.stop()

    def append_mappings(self,mappings,device):
        device['mappings'] = mappings
        self.stop()

    def add_mapping_ok(self,result,device):
        print "port-mapping to %s added" %device['friendly_name']
        self.stop(quiet=True)

    def add_mapping_failed(self,result,device):
        print "failed to add port-mapping to %s" %device['friendly_name']
        self.stop(quiet=True)

    def delete_mapping_ok(self,result,device):
        print "port-mapping deleted from %s" %device['friendly_name']
        self.stop(quiet=True)

    def delete_mapping_failed(self,result,device):
        print "failed to delete port-mapping from %s" %device['friendly_name']
        self.stop(quiet=True)

    def igd_found(self,client,udn):
        #print "IGD found", client.device.get_friendly_name()
        if self.locked == True:
            return
        elif self.locked == False:
            self.locked = True
        if(self.config['uuid'] != None and
           client.device.get_uuid().endswith(self.config['uuid']) == False):
            return
        self.devices[client.device.get_uuid()] = {'friendly_name': client.device.get_friendly_name()}
        if self.locked == True:
            wan_ip_connection_service = client.wan_device.wan_connection_device.wan_ip_connection or \
                                        client.wan_device.wan_connection_device.wan_ppp_connection
            if self.command == 'show-mappings':
                dfr = wan_ip_connection_service.get_all_port_mapping_entries()
                dfr.addCallback(self.append_mappings,self.devices[client.device.get_uuid()])
            elif self.command == 'add-mapping':
                dfr = wan_ip_connection_service.add_port_mapping(remote_host=self.config.subOptions['remote-host'],
                             external_port=int(self.config.subOptions['external-port']),
                             protocol=self.config.subOptions['protocol'].upper(),
                             internal_port=int(self.config.subOptions['internal-port']),
                             internal_client=self.config.subOptions['internal-host'],
                             enabled=self.config.subOptions['active'],
                             port_mapping_description=self.config.subOptions['description'],
                             lease_duration=int(self.config.subOptions['lease-duration']))
                dfr.addCallback(self.add_mapping_ok,self.devices[client.device.get_uuid()])
                dfr.addErrback(self.add_mapping_failed,self.devices[client.device.get_uuid()])
            elif self.command == 'delete-mapping':
                dfr = wan_ip_connection_service.delete_port_mapping(remote_host=self.config.subOptions['remote-host'],
                             external_port=int(self.config.subOptions['external-port']),
                             protocol=self.config.subOptions['protocol'].upper())
                dfr.addCallback(self.delete_mapping_ok,self.devices[client.device.get_uuid()])
                dfr.addErrback(self.delete_mapping_failed,self.devices[client.device.get_uuid()])
            elif self.command == 'info':
                self.port_mapping_number_of_entries = None
                self.external_ip_address = None
                wan_ip_connection_service.subscribe_for_variable('PortMappingNumberOfEntries', callback=self.state_variable_change)
                wan_ip_connection_service.subscribe_for_variable('ExternalIPAddress', callback=self.state_variable_change)


    def igd_removed(self,udn):
        #print "IGD removed", udn
        pass

    def state_variable_change(self,variable):
        if variable.name == 'ExternalIPAddress':
            self.external_ip_address = variable.value
        elif variable.name == 'PortMappingNumberOfEntries':
            if variable.value != '':
                self.port_mapping_number_of_entries = int(variable.value)
            else:
                self.port_mapping_number_of_entries = 0
        if(self.port_mapping_number_of_entries != None and
           self.external_ip_address != None):
            self.stop()
