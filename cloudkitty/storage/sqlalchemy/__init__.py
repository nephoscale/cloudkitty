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
try: import simplejson as json
except ImportError: import json
import decimal
from collections import defaultdict
from sqlalchemy import and_

from oslo_db.sqlalchemy import utils
import sqlalchemy

from cloudkitty import db
from cloudkitty import storage
from cloudkitty.storage.sqlalchemy import migration
from cloudkitty.storage.sqlalchemy import models
from cloudkitty import utils as ck_utils

import sqlalchemy.ext.declarative
import sqlalchemy.orm.interfaces
import sqlalchemy.exc
import datetime
import ast

# Added for including domain filter functionality
import ConfigParser
from keystoneauth1 import session as ksession
from keystoneauth1.identity import v3
from keystoneclient.v3 import client as kclient

config = ConfigParser.ConfigParser()
config.read('/etc/cloudkitty/cloudkitty.conf')
connection = dict(config.items('keystone_fetcher'))

def get_keystone_client():
    # Connecting to keystone
    auth = v3.Password(
        user_domain_id    = connection['user_domain_id'],
        username          = connection['admin_username'],
        password          = connection['admin_password'],
        project_domain_id = connection['project_domain_id'],
        project_name      = connection['admin_project_name'],
        auth_url          = connection['auth_url']
    )
    # Fetching the project list under that domain
    sess     = ksession.Session(auth=auth)
    keystone = kclient.Client(session=sess)
    return keystone

def get_domain_project_list(domain_id):
    # Fetch all projects under a given domain
    project_list = [item.name for item in get_keystone_client().projects.list(domain=domain_id)]
    return project_list


def get_domain_user_role_list(domain_id, user_id):
    # Fetch all roles assigned for a user in a domain
    role_list = get_keystone_client().role_assignments.list(domain = domain_id, user=user_id)
    users_roles = defaultdict(list)
    roles_ids = []
    if role_list:
        for role_assignment in role_list:
            if not hasattr(role_assignment, 'user'):
                continue
            user_id = role_assignment.user['id']
            role_id = role_assignment.role['id']

            # filter by domain_id
            if ('domain' in role_assignment.scope and
                    role_assignment.scope['domain']['id'] == domain_id):
                users_roles[user_id].append(role_id)

        for user_id in users_roles:
            roles_ids = users_roles[user_id]
    return roles_ids

def get_role_id(role_name_to_check):
    # Fetch the role id corresponding to a role name
    roles = get_keystone_client().roles.list()
    for role in roles:
        role_name = role.name
        if role_name == role_name_to_check:
            role_id = role.id
            break
    return role_id

def get_project_domain_id(project_name):
    # Get the domain id corresponding to a project
    project_list = get_keystone_client().projects.list()
    for project in project_list:
        if project.name == project_name:
            project_domain_id = project.domain_id
            break
    return project_domain_id

def get_user_id(user_name):
    # Get the userid corresponding to a user name
    user_details = get_keystone_client().users.list()
    for user in user_details:
        if user.name == user_name:
            user_id = user.id
            break
    return user_id

def get_billing_user_domain(dom_name):
    # Get the domain id of domain where billing-admin role has been asigned
    domains = get_keystone_client().domains.list()
    billing_user_domain = None
    for domain in domains:
        if domain.name == dom_name:
            billing_user_domain = domain.id
            break
    return billing_user_domain


class SQLAlchemyStorage(storage.BaseStorage):
    """SQLAlchemy Storage Backend

    """
    frame_model = models.RatedDataFrame
    meter_model = models.MeterLabel

    def __init__(self, **kwargs):
        super(SQLAlchemyStorage, self).__init__(**kwargs)
        self._session = {}

    @staticmethod
    def init():
        migration.upgrade('head')

    def _pre_commit(self, tenant_id):
        self._check_session(tenant_id)
        if not self._has_data.get(tenant_id):
            empty_frame = {'vol': {'qty': 0, 'unit': 'None'},
                           'rating': {'price': 0}, 'desc': ''}
            self._append_time_frame('_NO_DATA_', empty_frame, tenant_id)

    def _commit(self, tenant_id):
        self._session[tenant_id].commit()

    def _post_commit(self, tenant_id):
        super(SQLAlchemyStorage, self)._post_commit(tenant_id)
        del self._session[tenant_id]

    def _check_session(self, tenant_id):
        session = self._session.get(tenant_id)
        if not session:
            self._session[tenant_id] = db.get_session()
            self._session[tenant_id].begin()

    def _dispatch(self, data, tenant_id):
        self._check_session(tenant_id)
        for service in data:
            for frame in data[service]:
                self._append_time_frame(service, frame, tenant_id)
                self._has_data[tenant_id] = True

    def get_state(self, tenant_id=None):
        session = db.get_session()
        q = utils.model_query(
            self.frame_model,
            session)
        if tenant_id:
            q = q.filter(
                self.frame_model.tenant_id == tenant_id)
        q = q.order_by(
            self.frame_model.begin.desc())
        r = q.first()
        if r:
            return ck_utils.dt2ts(r.begin)

    # Modified by Muralidharan.s for applying a logic for getting 
    # Total value based on Instance
    def get_total(self, begin=None, end=None, tenant_id=None, service=None, instance_id=None, volume_type_id=None):
        model = models.RatedDataFrame

        # Boundary calculation
        if not begin:
            begin = ck_utils.get_month_start()
        if not end:
            end = ck_utils.get_next_month()

        session = db.get_session()
        q = session.query(
            sqlalchemy.func.sum(model.rate).label('rate'))
        if tenant_id:
            q = q.filter(
                models.RatedDataFrame.tenant_id == tenant_id)
        if service:
            q = q.filter(
                models.RatedDataFrame.res_type == service)
        if instance_id:
            q = q.filter(
                models.RatedDataFrame.desc.like('%'+instance_id+'%'))

	# check for volume type id
	if volume_type_id:
	    q = q.filter(models.RatedDataFrame.desc.like('%' + volume_type_id + '%'))    

        q = q.filter(
            model.begin >= begin,
            model.end <= end)
        rate = q.scalar()
        return rate


    # For listing invoice
    # admin and non-admin tenant will be able to list the own invoice
    # only admin tenant will be able to get the invoice of all tenant (--all-tenants)
    def list_invoice(self, tenant_name, user_name, all_tenants=None):

        model = models.InvoiceDetails
        session = db.get_session()

        #Fetch the domain id and user id
        domain_id = get_project_domain_id(tenant_name)
        user_id   = get_user_id(user_name)

        # Fetching the project list under that domain
        try:
            project_list = get_domain_project_list(domain_id)
        except Exception as e:
            print '============='
            print(e)
            print '============='

        # Fetch the roles assigned for logged in user in the current domain
        roles_ids = get_domain_user_role_list(domain_id, user_id)
   
        # Fetch the role id corresponding to admin & billing-admin roles
        domain_admin_role_id = get_role_id('admin')
        billing_admin_role_id = get_role_id('billing-admin')
 
        # Fetch the id of domain to which billing-admin role has been assigned
        billing_user_domain = get_billing_user_domain('Nephoscale')
         
        # If user has billing-admin role for the current domain,
        # then full invoice list will be displayed irrespective of domain.
        # If user has admin role on the current domain, then all invoices 
        # under each project of that domain will be displayed.
        # For all other cases, only invoices within current project will be 
        # displayed. 
        #if billing_admin_role_id in roles_ids and domain_id == 'default':
        #if billing_admin_role_id in roles_ids:
        if billing_admin_role_id in roles_ids and domain_id == billing_user_domain:
            q = session.query(model).order_by(model.id)
        elif len(roles_ids) and domain_admin_role_id in roles_ids:
            q = session.query(model).order_by(model.id).filter(model.tenant_name.in_((project_list)))
        else:
            q = session.query(model).order_by(model.id).filter(model.tenant_name == tenant_name)

        # Fetch all the values
        r = q.all()
        return [entry.to_cloudkitty() for entry in r]

    # For getting a invoice details as needed
    # admin tenant section
    # can get invoice based on tenant id, tenant name, invoice id and payment status 
    def get_invoice(self, tenant_id=None, tenant=None, user_name = None, invoice_id=None, payment_status=None):

        model = models.InvoiceDetails
        session = db.get_session()

        #Fetch the domain id and user id
        #domain_id = get_project_domain_id(tenant)
        #user_id   = get_user_id(user_name)

        # Fetch the invoice using tenant ID
        if tenant_id:
                q = session.query(model).order_by(model.id).filter(model.tenant_id == tenant_id)
        # Fetch the invoices using tenant name input
        if tenant:
                q = session.query(model).order_by(model.id).filter(model.tenant_name == tenant)

        # Fetch the invoice using invoice ID
        if invoice_id:
                q = session.query(model).order_by(model.id).filter(model.invoice_id == invoice_id)

        # Fetch the invoice using Payment status
        if payment_status:
                q = session.query(model).order_by(model.id).filter(model.payment_status == payment_status)

        # Fetch all the values
        r = q.all()

        return [entry.to_cloudkitty() for entry in r]

    # Invoice for non-admin tenant
    # get the invoice for non-admin tenant
    # can be able to fetch using invoice-id and payment_status
    def get_invoice_for_tenant(self, tenant_name, user_name, invoice_id=None, payment_status=None):

        model = models.InvoiceDetails
        session = db.get_session()

        #Fetch the domain id and user id
        domain_id = get_project_domain_id(tenant_name)
        user_id   = get_user_id(user_name)

        # Fetch the roles assigned for logged in user in the current domain
        roles_ids = get_domain_user_role_list(domain_id, user_id)

        # Fetch the role id corresponding to admin & billing-admin roles
        domain_admin_role_id = get_role_id('admin')
        billing_admin_role_id = get_role_id('billing-admin')

        # Fetch the id of domain to which billing-admin role has been assigned
        billing_user_domain = get_billing_user_domain('Nephoscale')

        #if billing_admin_role_id in roles_ids:
        if billing_admin_role_id in roles_ids and domain_id == billing_user_domain:
            q = session.query(model).order_by(model.id).filter(model.invoice_id == invoice_id)
        elif roles_ids and domain_admin_role_id in roles_ids:
            q = session.query(model).order_by(model.id).filter(model.invoice_id == invoice_id)
        else:
            # Fetch the invoice using invoice ID
            if invoice_id:
                q = session.query(model).order_by(model.id).filter(and_(model.invoice_id == invoice_id, model.tenant_name == tenant_name))

            # Fetch the invoice using payment_status
            if payment_status:
                q = session.query(model).order_by(model.id).filter(and_(model.payment_status == payment_status, model.tenant_name == tenant_name))

        # Fetch all the values
        r = q.all()

        return [entry.to_cloudkitty() for entry in r]

    # For showing a invoice details as needed
    # admin tenant section
    def show_invoice_for_tenant(self, tenant_name, user_name, invoice_id):
        model = models.InvoiceDetails
        session = db.get_session()

        #Fetch the domain id and user id
        domain_id = get_project_domain_id(tenant_name)
        user_id   = get_user_id(user_name)

        roles_ids = get_domain_user_role_list(domain_id, user_id)
        domain_admin_role_id = get_role_id('admin')
        billing_admin_role_id = get_role_id('billing-admin')

        # Fetch the id of domain to which billing-admin role has been assigned
        billing_user_domain = get_billing_user_domain('Nephoscale')

        #if billing_admin_role_id in roles_ids:
        if billing_admin_role_id in roles_ids and domain_id == billing_user_domain:
            q = session.query(model).order_by(model.id).filter(model.invoice_id == invoice_id)
        elif roles_ids and domain_admin_role_id in roles_ids:
            q = session.query(model).order_by(model.id).filter(model.invoice_id == invoice_id)
        else:
            # Fetch the invoice using tenant ID
            if invoice_id:
                q = session.query(model).order_by(model.id).filter(and_(model.invoice_id == invoice_id, model.tenant_name == tenant_name))

        # Fetch all the values
        r = q.all()
        return [entry.to_cloudkitty() for entry in r]

    # For showing a invoice details as needed
    # non-admin tenant section
    def show_invoice(self, invoice_id, tenant_name, user_name):

        model = models.InvoiceDetails
        session = db.get_session()

        #Fetch the domain id and user id
        domain_id = get_project_domain_id(tenant_name)
        user_id   = get_user_id(user_name)
        
        # Fetch the invoice using tenant ID
        if invoice_id:
                q = session.query(model).order_by(model.id).filter(model.invoice_id == invoice_id)

        # Fetch all the values
        r = q.all()

        return [entry.to_cloudkitty() for entry in r]


    # add invoice to the table
    def add_invoice(self, invoice_id, invoice_date, invoice_period_from, invoice_period_to, tenant_id, invoice_data, tenant_name, total_cost, paid_cost, balance_cost, payment_status, vat_rate, total_cost_after_vat):
        """Create a new invoice entry.

        """

        session = db.get_session()

        # Add invoice details
        invoice = models.InvoiceDetails(
                                        invoice_date = invoice_date,
                                        invoice_period_from = invoice_period_from,
                                        invoice_period_to = invoice_period_to,
                                        tenant_id = tenant_id,
                                        invoice_id = invoice_id,
                                        invoice_data = invoice_data,
                                        tenant_name = tenant_name,
                                        total_cost = total_cost,
                                        paid_cost = paid_cost,
                                        balance_cost = balance_cost,
                                        payment_status = payment_status,
                                        vat_rate = vat_rate,
                                        total_cost_after_vat = total_cost_after_vat) 

        try:
            with session.begin():
                session.add(invoice)

        except sqlalchemy.exc.IntegrityError as exc:
                reason = exc.message

        return invoice

    # update invoice entried in table
    def update_invoice(self, invoice_id, total_cost, paid_cost, balance_cost, payment_status):
        """
        Update the invoice details
        """
        session = db.get_session()
        with session.begin():
            try:
                q = utils.model_query(
                    models.InvoiceDetails,
                    session)
                if invoice_id:
                        q = q.filter(models.InvoiceDetails.invoice_id == invoice_id)
                        q = q.with_lockmode('update')
                        invoice_details = q.one()
                        if total_cost:
                                invoice_details.total_cost = total_cost
                        if paid_cost:
                                invoice_details.paid_cost = paid_cost
                        if balance_cost:
                                invoice_details.balance_cost = balance_cost
                        if payment_status:
                                invoice_details.payment_status = payment_status

            except sqlalchemy.orm.exc.NoResultFound:
                invoice_details = None

        # invoice_details none
        if invoice_details is None:
           return invoice_details

        # invoice details not none
        # loop through invoice detail and return
        else:
           invoice_detail = {}
           #return [invoice_detail for invoice_detail in invoice_details
           if total_cost:
                invoice_detail['total_cost'] = invoice_details.total_cost
           if balance_cost:
                invoice_detail['balance_cost'] = invoice_details.balance_cost
           if paid_cost:
                invoice_detail['paid_cost'] = invoice_details.paid_cost
           if payment_status:
                invoice_detail['payment_status'] = invoice_details.payment_status 
           return invoice_detail

    # delete invoice entries in table
    def delete_invoice(self, invoice_id):
        """
        delete the invoice details
        """
        session = db.get_session()
        with session.begin():
            try:
                q = utils.model_query(
                    models.InvoiceDetails,
                    session)
                if invoice_id:
                        q = q.filter(models.InvoiceDetails.invoice_id == invoice_id).delete()

            except sqlalchemy.orm.exc.NoResultFound:
                invoice_deleted = None

    def get_tenants(self, begin=None, end=None):
        # Boundary calculation
        if not begin:
            begin = ck_utils.get_month_start()
        if not end:
            end = ck_utils.get_next_month()

        session = db.get_session()
        q = utils.model_query(
            self.frame_model,
            session)
        q = q.filter(
            self.frame_model.begin >= begin,
            self.frame_model.end <= end)
        tenants = q.distinct().values(
            self.frame_model.tenant_id)
        return [tenant.tenant_id for tenant in tenants]

    def add_time_frame_custom(self, **kwargs):
        """Create a new time frame custom .

        :param begin: Start of the dataframe.
        :param end: End of the dataframe.
        :param tenant_id: tenant_id of the dataframe owner.
        :param unit: Unit of the metric.
        :param qty: Quantity of the metric.
        :param res_type: Type of the resource.
        :param rate: Calculated rate for this dataframe.
        :param desc: Resource description (metadata).
        """

        session = db.get_session()

        # Add invoice details
        frame = models.RatedDataFrame(  
                                        begin = kwargs.get('begin'),
                                        end = kwargs.get('end'),
                                        tenant_id = kwargs.get('tenant_id'),
                                        unit = kwargs.get('unit'),
                                        qty = kwargs.get('qty'),
                                        res_type = kwargs.get('res_type'),
                                        rate = decimal.Decimal(kwargs.get('rate')),
                                        desc = json.dumps(kwargs.get('desc')))

        try:
            with session.begin():
                session.add(frame)

        except sqlalchemy.exc.IntegrityError as exc:
                reason = exc.message

    def get_time_frame(self, begin, end, **filters):
        session = db.get_session()
        q = utils.model_query(
            self.frame_model,
            session)
        q = q.filter(
            self.frame_model.begin >= ck_utils.ts2dt(begin),
            self.frame_model.end <= ck_utils.ts2dt(end))
        for filter_name, filter_value in filters.items():
            if filter_value:
                q = q.filter(
                    getattr(self.frame_model, filter_name) == filter_value)
        if not filters.get('res_type'):
            q = q.filter(self.frame_model.res_type != '_NO_DATA_')
        count = q.count()
        if not count:
            raise storage.NoTimeFrame()
        r = q.all()
        return [entry.to_cloudkitty(self._collector) for entry in r]

    def _append_time_frame(self, res_type, frame, tenant_id):
        vol_dict = frame['vol']
        qty = vol_dict['qty']
        unit = vol_dict['unit']
        rating_dict = frame.get('rating', {})
        rate = rating_dict.get('price')
        if not rate:
            rate = decimal.Decimal(0)
        desc = json.dumps(frame['desc'])
        self.add_time_frame(begin=self.usage_start_dt.get(tenant_id),
                            end=self.usage_end_dt.get(tenant_id),
                            tenant_id=tenant_id,
                            unit=unit,
                            qty=qty,
                            res_type=res_type,
                            rate=rate,
                            desc=desc)

    def add_time_frame(self, **kwargs):
        """Create a new time frame.

        :param begin: Start of the dataframe.
        :param end: End of the dataframe.
        :param tenant_id: tenant_id of the dataframe owner.
        :param unit: Unit of the metric.
        :param qty: Quantity of the metric.
        :param res_type: Type of the resource.
        :param rate: Calculated rate for this dataframe.
        :param desc: Resource description (metadata).
        """
        frame = self.frame_model(**kwargs)
        self._session[kwargs.get('tenant_id')].add(frame)
        
    def get_image_usage_count(self, begin, end):
        """
            function to get image usage
            :param begin: Start of the dataframe.
            :param end: End of the dataframe.
        """
        
        instance_id_dict = {}
        image_count_dict = {}
        
        try:
            session = db.get_session()
            q = utils.model_query(self.frame_model, session)
            q = q.filter(
                self.frame_model.begin >= begin,
                self.frame_model.end <= end,
                self.frame_model.res_type == 'compute')
            
            result_list = q.all()
            
            # Get the resource details and calculate the image id used
            for usage in result_list:
                
                usage_date = str(usage['begin'].date())
                
                try:
                    usage_resource_desc = ast.literal_eval(usage['desc'])
                except Exception as e:
                    print e
                    usage_resource_desc = {}
            
                # check whether data frames contains instance id
                if usage_resource_desc.has_key('instance_id'):
                    
                    # if no key set for the respective date
                    if not image_count_dict.has_key(usage_date):
                        image_count_dict[usage_date] = {}
                    
                    # if no key set for the respective date
                    if not instance_id_dict.has_key(usage_date):
                        instance_id_dict[usage_date] = {}
                    
                    instance_id = usage_resource_desc['instance_id']
                    
                    # if instance already checked for that day, skip further execution
                    if instance_id_dict[usage_date].has_key(instance_id):
                        continue
                    
                    instance_image_id = usage_resource_desc.get('image_id')
                    
                    # if image id is not empty
                    if instance_image_id and instance_image_id is not None:
                        
                        # Check for the image id key
                        if image_count_dict[usage_date].has_key(instance_image_id):
                            image_count_dict[usage_date][instance_image_id] += 1
                        else:
                            image_count_dict[usage_date][instance_image_id] = 1
                            
                        instance_id_dict[usage_date][instance_id] = 1
                    
        except Exception as e:
            print e
        
        return [image_count_dict]
    
    def get_meter_label_list(self, instance_id = None, tenant_id = None, status = None, label_id = None):
        """
            function to get meter label list
            :param instance_id: The id of the instance
            :param tenant_id: The id of the tenant
        """
        
        result_list = []
        
        try:
            session = db.get_session()
            q = utils.model_query(self.meter_model, session)
            
            # if label id is passed
            if label_id is not None:
                q = q.filter(self.meter_model.label_id == label_id)
            
            # if instance id is passed
            if instance_id is not None:
                q = q.filter(self.meter_model.instance_id == instance_id)
            
            # if tenant id is passed    
            if tenant_id is not None:
                q = q.filter(self.meter_model.tenant_id == tenant_id)
            
            # if status is passed
            if status is not None:
                q = q.filter(self.meter_model.status == status)
            
            result_list = q.all()
            return [entry.to_cloudkitty() for entry in result_list]
                                
        except Exception as e:
            print e
        
        return result_list
    
    def create_meter_label(self, label_id, interface_id, interface_ip, instance_id, tenant_id, creation_date):
        """
            Create a new meter label for instance interface
        """
        
        session = db.get_session()
        meter_label = self.meter_model(
                                       label_id = label_id,
                                       interface_id = interface_id,
                                       interface_ip = interface_ip,
                                       instance_id = instance_id,
                                       tenant_id = tenant_id,
                                       creation_date = creation_date,
                                       status = 1)
        try:
            with session.begin():
                session.add(meter_label)

        except sqlalchemy.exc.IntegrityError as exc:
                reason = exc.message

        return meter_label.to_cloudkitty()
    
    def update_meter_label(self, label_id, interface_id, interface_ip, status):
        """
            Update meter details
        """
        
        meter_label = None
        session = db.get_session()
        with session.begin():
            try:
                q = utils.model_query(self.meter_model, session)
                
                #if label id is passed
                if label_id:
                    
                    q = q.filter(self.meter_model.label_id == label_id)
                    q = q.with_lockmode('update')
                    meter_label = q.one()
                    
                    # if interface name exists
                    if interface_id is not None:
                            meter_label.interface_id = interface_id
                    # if interface ip is existing
                    if interface_ip is not None:
                            meter_label.interface_ip = interface_ip
                    
                    # if status is passed
                    if status is not None:
                            meter_label.status = status

            except sqlalchemy.orm.exc.NoResultFound:
                meter_label = None
                
        return meter_label.to_cloudkitty()

    def get_latest_meter_label(self):
        """
            function to get latest meter label
        """
        
        meter_label = {}
        
        try:
            session = db.get_session()
            q = utils.model_query(self.meter_model, session).order_by(self.meter_model.id.desc()).limit(1)
            result = q.one()
            meter_label = result.to_cloudkitty()                                
        except Exception as e:
            print e
        
        return meter_label
    