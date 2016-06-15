# -*- coding: utf-8 -*-
# Copyright 2015 Objectif Libre
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
# @author: Stéphane Albert
#
import copy
import decimal

import six

from cloudkitty import utils as ck_utils

TENANT = 'f266f30b11f246b589fd266f85eeec39'
INITIAL_TIMESTAMP = 1420070400
FIRST_PERIOD_BEGIN = INITIAL_TIMESTAMP
FIRST_PERIOD_BEGIN_ISO = ck_utils.ts2iso(FIRST_PERIOD_BEGIN)
FIRST_PERIOD_END = FIRST_PERIOD_BEGIN + 3600
FIRST_PERIOD_END_ISO = ck_utils.ts2iso(FIRST_PERIOD_END)
SECOND_PERIOD_BEGIN = FIRST_PERIOD_END
SECOND_PERIOD_BEGIN_ISO = ck_utils.ts2iso(SECOND_PERIOD_BEGIN)
SECOND_PERIOD_END = SECOND_PERIOD_BEGIN + 3600
SECOND_PERIOD_END_ISO = ck_utils.ts2iso(SECOND_PERIOD_END)
DEMO_TENANT = '1456f30b11f2414789fd266f855ee894'

COMPUTE_METADATA = {
    'availability_zone': 'nova',
    'flavor': 'm1.nano',
    'image_id': 'f5600101-8fa2-4864-899e-ebcb7ed6b568',
    'instance_id': '26c084e1-b8f1-4cbc-a7ec-e8b356788a17',
    'memory': '64',
    'metadata': {
        'farm': 'prod'
    },
    'name': 'prod1',
    'project_id': 'f266f30b11f246b589fd266f85eeec39',
    'user_id': '55b3379b949243009ee96972fbf51ed1',
    'vcpus': '1'}

IMAGE_METADATA = {
    'checksum': '836c69cbcd1dc4f225daedbab6edc7c7',
    'container_format': 'aki',
    'created_at': '2014-06-04T16:26:01',
    'deleted': 'False',
    'deleted_at': 'None',
    'disk_format': 'aki',
    'is_public': 'True',
    'min_disk': '0',
    'min_ram': '0',
    'name': 'cirros-0.3.2-x86_64-uec-kernel',
    'protected': 'False',
    'size': '4969360',
    'status': 'active',
    'updated_at': '2014-06-04T16:26:02'}

FIRST_PERIOD = {
    'begin': FIRST_PERIOD_BEGIN,
    'end': FIRST_PERIOD_END}

SECOND_PERIOD = {
    'begin': SECOND_PERIOD_BEGIN,
    'end': SECOND_PERIOD_END}

COLLECTED_DATA = [{
    'period': FIRST_PERIOD,
    'usage': {
        'compute': [{
            'desc': COMPUTE_METADATA,
            'vol': {
                'qty': decimal.Decimal(1.0),
                'unit': 'instance'}}],
        'image': [{
            'desc': IMAGE_METADATA,
            'vol': {
                'qty': decimal.Decimal(1.0),
                'unit': 'image'}}]
    }}, {
    'period': SECOND_PERIOD,
    'usage': {
        'compute': [{
            'desc': COMPUTE_METADATA,
            'vol': {
                'qty': decimal.Decimal(1.0),
                'unit': 'instance'}}]
    }}]

# data input for invoice
# demo user data
INVOICE_DATA_DEMO = [{
    'id': '1',
    'invoice_date': FIRST_PERIOD_BEGIN,
    'invoice_period_from': FIRST_PERIOD_BEGIN,
    'invoice_period_to': FIRST_PERIOD_END,
    'invoice_id': 'demo-5-2016',
    'total_cost': '6.64',
    'paid_cost': '0.11',
    'balance_cost': '6.53',
    'invoice_data': {
		'dict_all_cost_total': '6.64',
		'dict_cloud_storage': '4.00',
		'dict_volume': '2.64'},
    'tenant_id': DEMO_TENANT,
    'payment_status': '0',
    'tenant_name': 'demo'
    }]

# demo user data to compare
INVOICE_DATA_DEMO_COMPARE = [{
    'id': 1,
    'invoice_date': '2015-01-01T00:00:00Z',
    'invoice_period_from': '2015-01-01T00:00:00Z',
    'invoice_period_to': '2015-01-01T01:00:00Z',
    'invoice_id': u'demo-5-2016',
    'total_cost': '6.64',
    'paid_cost': '0.11',
    'balance_cost': '6.53',
    'invoice_data': {
                u'dict_all_cost_total': u'6.64',
                u'dict_cloud_storage': u'4.00',
                u'dict_volume': u'2.64'},
    'tenant_id': u'1456f30b11f2414789fd266f855ee894',
    'payment_status': 0,
    'tenant_name': u'demo'
    }]

# data input
# admin user data
INVOICE_DATA_ADMIN = [{
    'id': '2',
    'invoice_date': FIRST_PERIOD_BEGIN,
    'invoice_period_from': FIRST_PERIOD_BEGIN,
    'invoice_period_to': FIRST_PERIOD_END,
    'invoice_id': 'admin-5-2016',
    'total_cost': '1.64',
    'paid_cost': '0.11',
    'balance_cost': '1.53',
    'invoice_data': {
                'dict_all_cost_total': '1.64',
                'dict_cloud_storage': '0.64',
                'dict_volume': '1.00'},
    'tenant_id': TENANT,
    'payment_status': '1',
    'tenant_name': 'admin'
    }]

# admin user data to compare
INVOICE_DATA_ADMIN_COMPARE = [{
    'id': 2,
    'invoice_date': '2015-01-01T00:00:00Z',
    'invoice_period_from': '2015-01-01T00:00:00Z',
    'invoice_period_to': '2015-01-01T01:00:00Z',
    'invoice_id': u'admin-5-2016',
    'total_cost': '1.64',
    'paid_cost': '0.11',
    'balance_cost': '1.53',
    'invoice_data': {
                u'dict_all_cost_total': u'1.64',
                u'dict_cloud_storage': u'0.64',
                u'dict_volume': u'1.00'},
    'tenant_id': u'f266f30b11f246b589fd266f85eeec39',
    'payment_status': 1,
    'tenant_name': u'admin'
    }]

# all invoice data to compare
ALL_INVOICES = INVOICE_DATA_DEMO_COMPARE + INVOICE_DATA_ADMIN_COMPARE

# making the data as dict
def invoice_data(data):

    for invoice in data:

        invoice_dict = invoice

    return invoice_dict

# dict with invoice data 
INVOICE_DICT_DEMO = invoice_data(INVOICE_DATA_DEMO)
INVOICE_DICT_ADMIN = invoice_data(INVOICE_DATA_ADMIN)

RATED_DATA = copy.deepcopy(COLLECTED_DATA)
RATED_DATA[0]['usage']['compute'][0]['rating'] = {
    'price': decimal.Decimal('0.42')}
RATED_DATA[0]['usage']['image'][0]['rating'] = {
    'price': decimal.Decimal('0.1337')}
RATED_DATA[1]['usage']['compute'][0]['rating'] = {
    'price': decimal.Decimal('0.42')}


def split_storage_data(raw_data):

    final_data = []
    for frame in raw_data:
        frame['period']['begin'] = ck_utils.ts2iso(frame['period']['begin'])
        frame['period']['end'] = ck_utils.ts2iso(frame['period']['end'])
        usage_buffer = frame.pop('usage')
        # Sort to have a consistent result as we are converting it to a list
        for service, data in sorted(six.iteritems(usage_buffer)):
            new_frame = copy.deepcopy(frame)
            new_frame['usage'] = {service: data}
            new_frame['usage'][service][0]['tenant_id'] = TENANT
            final_data.append(new_frame)
    return final_data


# FIXME(sheeprine): storage is not using decimal for rates, we need to
# transition to decimal.
STORED_DATA = copy.deepcopy(COLLECTED_DATA)
STORED_DATA[0]['usage']['compute'][0]['rating'] = {
    'price': 0.42}
STORED_DATA[0]['usage']['image'][0]['rating'] = {
    'price': 0.1337}
STORED_DATA[1]['usage']['compute'][0]['rating'] = {
    'price': 0.42}

STORED_DATA = split_storage_data(STORED_DATA)
