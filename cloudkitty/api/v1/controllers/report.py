# -*- coding: utf-8 -*-
# Copyright 2014 Objectif Libre
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
import datetime
import decimal
import six
import pecan
from pecan import rest
from wsme import types as wtypes
import wsmeext.pecan as wsme_pecan

from cloudkitty.common import policy


class ReportController(rest.RestController):
    """REST Controller managing the reporting.

    """

    _custom_actions = {
        'total': ['GET'],
        'tenants': ['GET'],
        'invoice': ['GET'],
        'list_invoice': ['GET'],
        'add_invoice': ['POST'],
        'update_invoice': ['PUT'],
        'show_invoice': ['GET'],
        'delete_invoice': ['DELETE'],
    }

    @wsme_pecan.wsexpose([wtypes.text],
                         datetime.datetime,
                         datetime.datetime)
    def tenants(self, begin=None, end=None):
        """Return the list of rated tenants.

        """
        policy.enforce(pecan.request.context, 'report:list_tenants', {})
        storage = pecan.request.storage_backend
        tenants = storage.get_tenants(begin, end)
        return tenants

    @wsme_pecan.wsexpose(decimal.Decimal,
                         datetime.datetime,
                         datetime.datetime,
                         wtypes.text,
                         wtypes.text,
                         wtypes.text)

    # Modified by Muralidharan.s for applying a logic for getting 
    # Total value based on Instance
    def total(self, begin=None, end=None, tenant_id=None, service=None, instance_id=None):
        """Return the amount to pay for a given period.

        """
        policy.enforce(pecan.request.context, 'report:get_total', {})
        storage = pecan.request.storage_backend
        # FIXME(sheeprine): We should filter on user id.
        # Use keystone token information by default but make it overridable and
        # enforce it by policy engine
        total = storage.get_total(begin, end, tenant_id, service, instance_id)
        return total if total else decimal.Decimal('0')

    # For getting the invoice for admin and non-admin tenants
    # Can get the invoice based on invoice-id , tenant-id, tenant-name and payment-status
    # tenant-name and tenant-id option available for admin tenants
    @wsme_pecan.wsexpose([wtypes.text],
                         wtypes.text,
                         wtypes.text,
                         wtypes.text,
                         wtypes.text)
    def invoice(self, tenant_id=None, tenant_name=None, invoice_id=None, payment_status=None):
        """Return the Invoice details.

        """

	# assigning a tenant_name to another variable tenant
	# We already have variable named tenant for making decision on type of user and actions
	# So assigning a new name as tenant
	tenant = tenant_name

        policy.enforce(pecan.request.context, 'report:invoice', {})
        storage = pecan.request.storage_backend

        # role of tenant
        roles = pecan.request.context.__dict__['roles']

        # fetch tenant name
        tenant_name = pecan.request.context.__dict__['tenant']

        # If tenant_id or invoice_id or payment_status exists
        if tenant_id or invoice_id or payment_status or tenant_name:

                # if admin role
                if 'admin' in roles:

			# added facility for fetch using tenant name from user input also
                        invoice = storage.get_invoice(tenant_id, tenant, invoice_id, payment_status)

                # for non-admin roles
                else:

                        # for restricting non-admin users to use tenant-name and tenant-id options
                        if not (tenant or tenant_id):

				# Added facility for fetch using tenant name too
                                invoice = storage.get_invoice_for_tenant(tenant_name, invoice_id, payment_status)

                        # for generating a warning message if tenant_id arg passed for non-admin
                        else:

                                pecan.abort(405, six.text_type())

        # for generating the warning message that invoice-get not supported
        else:

                pecan.abort(405, six.text_type())


        return invoice

    # For invoice-list 
    # Generate invoice-list results
    # admin and non-admin tenant can be able to get the result 
    # Only admin tenant can be able to use all-tenants arg
    @wsme_pecan.wsexpose([wtypes.text],
                         wtypes.text)
    def list_invoice(self, all_tenants=None):
        """Return the Invoice details.

        """
        policy.enforce(pecan.request.context, 'report:list_invoice', {})
        storage = pecan.request.storage_backend
        # Fetch the user role
        roles = pecan.request.context.__dict__['roles']

        # fetch tenant name
        tenant_name = pecan.request.context.__dict__['tenant']

        # for admin tenant
        if 'admin' in roles:
                invoice = storage.list_invoice(tenant_name, all_tenants)

        # For producing result for non-admin tenant if all-tenants arg not used
        elif 'admin' not in roles and all_tenants is None:
                invoice = storage.list_invoice(tenant_name, all_tenants)

        # For non-admin tenant to restrict the use of all-tenants arg
        elif 'admin' not in roles and all_tenants is not None:
                pecan.abort(403, six.text_type())

        return invoice


    # For invoice-show 
    # Generate invoice-show results
    # admin and non-admin tenant can be able to get the result
    # Will show the full details of invoice  
    @wsme_pecan.wsexpose([wtypes.text],
                         wtypes.text)
    def show_invoice(self, invoice_id):
        """Return the Invoice details.

        """
        policy.enforce(pecan.request.context, 'report:show_invoice', {})
        storage = pecan.request.storage_backend

        # Fetch the user role
        roles = pecan.request.context.__dict__['roles']

        # fetch tenant name
        tenant_name = pecan.request.context.__dict__['tenant']

        # for admin tenant
        if 'admin' in roles:
                invoice = storage.show_invoice(invoice_id)

        # For producing result for non-admin tenant
        elif 'admin' not in roles:
                invoice = storage.show_invoice_for_tenant(tenant_name, invoice_id)

        return invoice

    # adding the invoice
    @wsme_pecan.wsexpose(decimal.Decimal,
                         wtypes.text,
                         wtypes.text,
                         wtypes.text,
                         wtypes.text,
                         wtypes.text,
                         wtypes.text,
                         wtypes.text,
                         wtypes.text,
                         wtypes.text,
                         wtypes.text,
                         wtypes.text)
    def add_invoice(self, invoice_id, invoice_date, invoice_period_from, invoice_period_to, tenant_id, invoice_data, tenant_name, total_cost, paid_cost, balance_cost, payment_status ):
        """Add the Invoice details.
        """

        try:
            policy.enforce(pecan.request.context, 'report:add_invoice', {})
        except policy.PolicyNotAuthorized as e:
            pecan.abort(403, six.text_type(e))

        storage = pecan.request.storage_backend

        # Fetch the user role
        roles = pecan.request.context.__dict__['roles']

        # for admin tenant
        if 'admin' in roles:

                # invoice details
                invoice = storage.add_invoice(invoice_id, 
                                              invoice_date, 
                                              invoice_period_from, 
                                              invoice_period_to, 
                                              tenant_id, 
                                              invoice_data, 
                                              tenant_name, 
                                              total_cost, 
                                              paid_cost, 
                                              balance_cost, 
                                              payment_status)

    # Updating the invoice
    @wsme_pecan.wsexpose([wtypes.text],
                         wtypes.text,
                         wtypes.text,
                         wtypes.text,
                         wtypes.text,
                         wtypes.text)
    def update_invoice(self, invoice_id, total_cost=None, paid_cost=None, balance_cost=None, payment_status=None ):
        """
        update the invoice details
        """

        try:
            policy.enforce(pecan.request.context, 'report:update_invoice', {})
        except policy.PolicyNotAuthorized as e:
            pecan.abort(403, six.text_type(e))

        storage = pecan.request.storage_backend

        # Fetch the user role
        roles = pecan.request.context.__dict__['roles']

        # for admin tenant
        if 'admin' in roles:

                # invoice details
                invoice = storage.update_invoice(invoice_id,
                                              total_cost,
                                              paid_cost,
                                              balance_cost,
                                              payment_status)
        return invoice

    # Delete the Invoice
    @wsme_pecan.wsexpose([wtypes.text],
                         wtypes.text)
    def delete_invoice(self, invoice_id):
        """
        delete the invoice
        """

        try:
            policy.enforce(pecan.request.context, 'report:delete_invoice', {})
        except policy.PolicyNotAuthorized as e:
            pecan.abort(403, six.text_type(e))

        storage = pecan.request.storage_backend

        # Fetch the user role
        roles = pecan.request.context.__dict__['roles']

        # for admin tenant
        if 'admin' in roles:

                # invoice details
                invoice = storage.delete_invoice(invoice_id)
