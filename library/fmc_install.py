#!/usr/bin/python

# Copyright (c) 2019 Cisco and/or its affiliates.
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.
#

from __future__ import absolute_import, division, print_function

__metaclass__ = type

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'network'}

DOCUMENTATION = """
---
module: ftd_install
short_description: Installs FTD pkg image on the firewall
description:
  - Provisioning module for FTD devices that installs ROMMON image (if needed) and
    FTD pkg image on the firewall.
  - Can be used with `httpapi` and `local` connection types. The `httpapi` is preferred,
    the `local` connection should be used only when the device cannot be accessed via
    REST API.
version_added: "2.8"
requirements: [ "python >= 3.5", "kick" ]
author: "Cisco Systems, Inc."
options:
  device_hostname:
    description:
      - Hostname of the device as appears in the prompt (e.g., 'firepower-5516').
    required: true
    type: string
  device_username:
    description:
      - Username to login on the device.
      - Defaulted to 'admin' if not specified.
    required: false
    type: string
    default: admin
  device_password:
    description:
      - Password to login on the device.
    required: true
    type: string
  device_sudo_password:
    description:
      - Root password for the device. If not specified, `device_password` is used.
    required: false
    type: string
  device_new_password:
    description:
      - New device password to set after image installation.
      - If not specified, current password from `device_password` property is reused.
      - Not applicable for ASA5500-X series devices.
    required: false
    type: string
  device_ip:
    description:
      - Device IP address of management interface.
      - If not specified and connection is 'httpapi`, the module tries to fetch the existing value via REST API.
      - For 'local' connection type, this parameter is mandatory.
    required: false
    type: string
  device_gateway:
    description:
      - Device gateway of management interface.
      - If not specified and connection is 'httpapi`, the module tries to fetch the existing value via REST API.
      - For 'local' connection type, this parameter is mandatory.
    required: false
    type: string
  device_netmask:
    description:
      - Device netmask of management interface.
      - If not specified and connection is 'httpapi`, the module tries to fetch the existing value via REST API.
      - For 'local' connection type, this parameter is mandatory.
    required: false
    type: string
  device_model:
    description:
      - Platform model of the device (e.g., 'Cisco ASA5506-X Threat Defense').
      - If not specified and connection is 'httpapi`, the module tries to fetch the device model via REST API.
      - For 'local' connection type, this parameter is mandatory.
    required: false
    type: string
  dns_server:
    description:
      - DNS IP address of management interface.
      - If not specified and connection is 'httpapi`, the module tries to fetch the existing value via REST API.
      - For 'local' connection type, this parameter is mandatory.
    required: false
    type: string
  console_ip:
    description:
      - IP address of a terminal server.
      - Used to set up an SSH connection with device's console port through the terminal server.
    required: true
    type: string
  console_port:
    description:
      - Device's port on a terminal server.
    required: true
    type: string
  console_username:
    description:
      - Username to login on a terminal server.
    required: true
    type: string
  console_password:
    description:
      - Password to login on a terminal server.
    required: true
    type: string
  rommon_file_location:
    description:
      - Path to the boot (ROMMON) image on TFTP server.
      - Only TFTP is supported.
    required: true
    type: string
  image_file_location:
    description:
      - Path to the FTD pkg image on the server to be downloaded.
      - FTP, SCP, SFTP, TFTP, or HTTP protocols are usually supported, but may depend on the device model.
    required: true
    type: string
  image_version:
    description:
      - Version of FTD image to be installed.
      - Helps to compare target and current FTD versions to prevent unnecessary reinstalls.
    required: true
    type: string
  force_install:
    description:
      - Forces the FTD image to be installed even when the same version is already installed on the firewall.
      - By default, the module stops execution when the target version is installed in the device.
    required: false
    type: boolean
    default: false
  search_domains:
    description:
      - Search domains delimited by comma.
      - Defaulted to 'cisco.com' if not specified.
    required: false
    type: string
    default: cisco.com
"""

EXAMPLES = """
  - name: Install image v6.3.0 on FTD 5516
    ftd_install:
      device_hostname: firepower
      device_password: pass
      device_ip: 192.168.0.1
      device_netmask: 255.255.255.0
      device_gateway: 192.168.0.254
      dns_server: 8.8.8.8

      console_ip: 10.89.0.0
      console_port: 2004
      console_username: console_user
      console_password: console_pass

      rommon_file_location: 'tftp://10.89.0.11/installers/ftd-boot-9.10.1.3.lfbff'
      image_file_location: 'https://10.89.0.11/installers/ftd-6.3.0-83.pkg'
      image_version: 6.3.0-83
"""

RETURN = """
msg:
    description: The message saying whether the image was installed or explaining why the installation failed.
    returned: always
    type: string
"""
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.connection import Connection
from enum import Enum
from six import iteritems

# try:
#     from ansible.module_utils.configuration import BaseConfigurationResource, ParamName, PATH_PARAMS_FOR_DEFAULT_OBJ
#     from ansible.module_utils.device import HAS_KICK, FtdPlatformFactory, FtdModel
# except ImportError:
#     from module_utils.configuration import BaseConfigurationResource, ParamName, PATH_PARAMS_FOR_DEFAULT_OBJ
#     from module_utils.device import HAS_KICK, FtdPlatformFactory, FtdModel
from module_utils.configuration import BaseConfigurationResource, ParamName, PATH_PARAMS_FOR_DEFAULT_OBJ
from module_utils.device import HAS_KICK, FtdPlatformFactory, FtdModel

REQUIRED_PARAMS_FOR_LOCAL_CONNECTION = ['device_ip', 'device_netmask', 'device_gateway', 'device_model', 'dns_server']


class FmcOperations(Enum):
    GET_SYSTEM_INFO = 'getSystemInformation'
    GET_MANAGEMENT_IP_LIST = 'getManagementIPList'
    GET_DNS_SETTING_LIST = 'getDeviceDNSSettingsList'
    GET_DNS_SERVER_GROUP = 'getDNSServerGroup'


def main():
    fields = dict(
        device_hostname=dict(type='str', required=True),
        device_username=dict(type='str', required=False, default='admin'),
        device_password=dict(type='str', required=True, no_log=True),
        device_sudo_password=dict(type='str', required=False, no_log=True),
        device_new_password=dict(type='str', required=False, no_log=True),
        device_ip=dict(type='str', required=False),
        device_netmask=dict(type='str', required=False),
        device_gateway=dict(type='str', required=False),
        device_model=dict(type='str', required=False, choices=[e.value for e in FtdModel]),
        dns_server=dict(type='str', required=False),
        search_domains=dict(type='str', required=False, default='cisco.com'),

        console_ip=dict(type='str', required=True),
        console_port=dict(type='str', required=True),
        console_username=dict(type='str', required=True),
        console_password=dict(type='str', required=True, no_log=True),

        rommon_file_location=dict(type='str', required=True),
        image_file_location=dict(type='str', required=True),
        image_version=dict(type='str', required=True),
        force_reinstall=dict(type='bool', required=False, default=False)
    )
    module = AnsibleModule(argument_spec=fields)
    if not HAS_KICK:
        module.fail_json(msg='Kick Python module is required to run this module. '
                             'Please, install it with `pip install kick` command and run the playbook again.')

    use_local_connection = module._socket_path is None
    if use_local_connection:
        check_required_params_for_local_connection(module, module.params)
        platform_model = module.params['device_model']
        check_that_model_is_supported(module, platform_model)
    else:
        connection = Connection(module._socket_path)
        resource = BaseConfigurationResource(connection, module.check_mode)
        system_info = get_system_info(resource)

        platform_model = module.params['device_model'] or system_info['platformModel']
        check_that_model_is_supported(module, platform_model)
        check_that_update_is_needed(module, system_info)
        check_management_and_dns_params(resource, module.params)

    fmc_platform = FtdPlatformFactory.create(platform_model, module.params)
    fmc_platform.install_fmc_image(module.params)

    module.exit_json(changed=True,
                     msg='Successfully installed FTD image %s on the firewall device.' % module.params["image_version"])


def check_required_params_for_local_connection(module, params):
    missing_params = [k for k, v in iteritems(params) if k in REQUIRED_PARAMS_FOR_LOCAL_CONNECTION and v is None]
    if missing_params:
        message = "The following parameters are mandatory when the module is used with 'local' connection: %s." %\
                  ', '.join(sorted(missing_params))
        module.fail_json(msg=message)


def get_system_info(resource):
    path_params = {ParamName.PATH_PARAMS: PATH_PARAMS_FOR_DEFAULT_OBJ}
    system_info = resource.execute_operation(FmcOperations.GET_SYSTEM_INFO.value, path_params)
    return system_info


def check_that_model_is_supported(module, platform_model):
    if not FtdModel.has_value(platform_model):
        module.fail_json(msg="Platform model '%s' is not supported by this module." % platform_model)


def check_that_update_is_needed(module, system_info):
    target_ftd_version = module.params["image_version"]
    if not module.params["force_reinstall"] and target_ftd_version == system_info['softwareVersion']:
        module.exit_json(changed=False, msg="FTD already has %s version of software installed." % target_ftd_version)


def check_management_and_dns_params(resource, params):
    if not all([params['device_ip'], params['device_netmask'], params['device_gateway']]):
        management_ip = resource.execute_operation(FmcOperations.GET_MANAGEMENT_IP_LIST.value, {})['items'][0]
        params['device_ip'] = params['device_ip'] or management_ip['ipv4Address']
        params['device_netmask'] = params['device_netmask'] or management_ip['ipv4NetMask']
        params['device_gateway'] = params['device_gateway'] or management_ip['ipv4Gateway']
    if not params['dns_server']:
        dns_setting = resource.execute_operation(FmcOperations.GET_DNS_SETTING_LIST.value, {})['items'][0]
        dns_server_group_id = dns_setting['dnsServerGroup']['id']
        dns_server_group = resource.execute_operation(FmcOperations.GET_DNS_SERVER_GROUP.value,
                                                      {ParamName.PATH_PARAMS: {'objId': dns_server_group_id}})
        params['dns_server'] = dns_server_group['dnsServers'][0]['ipAddress']


if __name__ == '__main__':
    main()
