# -*- coding: utf-8 -*-

"""
The OsScheduler class will hold all tasks that should run in the background (for now)
When it gets bit, let's split it into multiple files.

Naming:

Roughly stick to:
db_table.action.info_about_what_task_does

"""

import datetime
from gluon import *

class OsSchedulerTasks:

    def customers_subscriptions_create_invoices_for_month(self, year, month, description):
        """
            Actually create invoices for subscriptions for a given month
        """
        from general_helpers import get_last_day_month
        from os_invoice import Invoice

        T = current.T
        db = current.db
        DATE_FORMAT = current.DATE_FORMAT


        year = int(year)
        month = int(month)

        firstdaythismonth = datetime.date(year, month, 1)
        lastdaythismonth  = get_last_day_month(firstdaythismonth)

        csap = db.customers_subscriptions_alt_prices

        fields = [
            db.customers_subscriptions.id,
            db.customers_subscriptions.auth_customer_id,
            db.customers_subscriptions.school_subscriptions_id,
            db.customers_subscriptions.Startdate,
            db.customers_subscriptions.Enddate,
            db.customers_subscriptions.payment_methods_id,
            db.school_subscriptions.Name,
            db.school_subscriptions_price.Price,
            db.school_subscriptions_price.tax_rates_id,
            db.tax_rates.Percentage,
            db.customers_subscriptions_paused.id,
            db.invoices.id,
            csap.id,
            csap.Amount,
            csap.Description
        ]

        rows = db.executesql(
            """
                SELECT cs.id,
                       cs.auth_customer_id,
                       cs.school_subscriptions_id,
                       cs.Startdate,
                       cs.Enddate,
                       cs.payment_methods_id,
                       ssu.Name,
                       ssp.Price,
                       ssp.tax_rates_id,
                       tr.Percentage,
                       csp.id,
                       i.invoices_id,
                       csap.id,
                       csap.Amount,
                       csap.Description
                FROM customers_subscriptions cs
                LEFT JOIN auth_user au
                 ON au.id = cs.auth_customer_id
                LEFT JOIN school_subscriptions ssu
                 ON cs.school_subscriptions_id = ssu.id
                LEFT JOIN
                 (SELECT id,
                         school_subscriptions_id,
                         Startdate,
                         Enddate,
                         Price,
                         tax_rates_id
                  FROM school_subscriptions_price
                  WHERE Startdate <= '{firstdaythismonth}' AND
                        (Enddate >= '{firstdaythismonth}' OR Enddate IS NULL)) ssp
                 ON ssp.school_subscriptions_id = ssu.id
                LEFT JOIN tax_rates tr
                 ON ssp.tax_rates_id = tr.id
                LEFT JOIN
                 (SELECT id,
                         customers_subscriptions_id
                  FROM customers_subscriptions_paused
                  WHERE Startdate <= '{firstdaythismonth}' AND
                        (Enddate >= '{firstdaythismonth}' OR Enddate IS NULL)) csp
                 ON cs.id = csp.customers_subscriptions_id
                LEFT JOIN
                 (SELECT ics.id,
                         ics.invoices_id,
                         ics.customers_subscriptions_id
                  FROM invoices_customers_subscriptions ics
                  LEFT JOIN invoices on ics.invoices_id = invoices.id
                  WHERE invoices.SubscriptionYear = {year} AND invoices.SubscriptionMonth = {month}) i
                 ON i.customers_subscriptions_id = cs.id
                LEFT JOIN
                 (SELECT id,
                         customers_subscriptions_id,
                         Amount,
                         Description
                  FROM customers_subscriptions_alt_prices
                  WHERE SubscriptionYear = {year} AND SubscriptionMonth = {month}) csap
                 ON csap.customers_subscriptions_id = cs.id
                WHERE cs.Startdate <= '{lastdaythismonth}' AND
                      (cs.Enddate >= '{firstdaythismonth}' OR cs.Enddate IS NULL) AND
                      ssp.Price <> 0 AND
                      ssp.Price IS NOT NULL AND
                      au.trashed = 'F'
            """.format(firstdaythismonth=firstdaythismonth,
                       lastdaythismonth =lastdaythismonth,
                       year=year,
                       month=month),
          fields=fields)

        igpt = db.invoices_groups_product_types(ProductType = 'subscription')
        igID = igpt.invoices_groups_id

        invoices_created = 0

        # Alright, time to create some invoices
        for row in rows:
            if row.invoices.id:
                # an invoice already exists, do nothing
                continue
            if row.customers_subscriptions_paused.id:
                # the subscription is paused, don't create an invoice
                continue
            if row.customers_subscriptions_alt_prices.Amount == 0:
                # Don't create an invoice if there's an alt price for the subscription with amount 0.
                continue

            csID = row.customers_subscriptions.id
            cuID = row.customers_subscriptions.auth_customer_id
            pmID = row.customers_subscriptions.payment_methods_id

            subscr_name = row.school_subscriptions.Name

            if row.customers_subscriptions_alt_prices.Description:
                inv_description = row.customers_subscriptions_alt_prices.Description
            else:
                inv_description = description

            if row.customers_subscriptions.Startdate > firstdaythismonth:
                period_begin = row.customers_subscriptions.Startdate
            else:
                period_begin = firstdaythismonth

            period_end = lastdaythismonth
            if row.customers_subscriptions.Enddate:
                if row.customers_subscriptions.Enddate >= firstdaythismonth and \
                   row.customers_subscriptions.Enddate < lastdaythismonth:
                    period_end = row.customers_subscriptions.Enddate


            item_description = period_begin.strftime(DATE_FORMAT) + ' - ' + \
                               period_end.strftime(DATE_FORMAT)

            iID = db.invoices.insert(
                invoices_groups_id = igID,
                payment_methods_id = pmID,
                SubscriptionYear = year,
                SubscriptionMonth = month,
                Description = inv_description,
                Status = 'sent'
            )

            # create object to set Invoice# and due date
            invoice = Invoice(iID)
            invoice.link_to_customer(cuID)
            iiID = invoice.item_add_subscription(csID, year, month)
            invoice.link_item_to_customer_subscription(csID, iiID)
            invoice.set_amounts()

            invoices_created += 1

        ##
        # For scheduled tasks db connection has to be committed manually
        ##
        db.commit()

        return T("Invoices created") + ': ' + unicode(invoices_created)


    def customers_subscriptions_add_credits_for_month(self, year, month):
        """
        :param year: int
        :param month: int
        :return: Add customer subscription credits for month
        """
        from os_customers_subscriptions_credits import CustomersSubscriptionsCredits

        T = current.T
        db = current.db

        year = int(year)
        month = int(month)

        csch = CustomersSubscriptionsCredits()
        added = csch.add_credits(year, month)

        db.commit()

        return T("Subscriptions for which credits were added") + ': ' + unicode(added)


    def customers_memberships_renew_expired(self, year, month):
        """
            Checks if a subscription exceeds the expiration of a membership.
            If so it creates a new membership and an invoice for it for the customer
        """
        from general_helpers import get_last_day_month
        from datetime import timedelta
        from os_customer import Customer
        from os_invoice import Invoice
        from os_school_membership import SchoolMembership

        T = current.T
        db = current.db
        DATE_FORMAT = current.DATE_FORMAT

        year = int(year)
        month = int(month)

        firstdaythismonth = datetime.date(year, month, 1)
        lastdaythismonth  = get_last_day_month(firstdaythismonth)
        firstdaynextmonth = lastdaythismonth + datetime.timedelta(days=1)

        query = (db.customers_memberships.Enddate >= firstdaythismonth) & \
                (db.customers_memberships.Enddate <= lastdaythismonth)

        rows = db(query).select(
            db.customers_memberships.ALL
        )

        renewed = 0

        for row in rows:
            new_cm_start = row.Enddate + datetime.timedelta(days=1)

            # Check if a subscription will be active next month for customer
            # if so, add another membership
            customer = Customer(row.auth_customer_id)

            # Check if a new membership hasn't ben added already
            if customer.has_membership_on_date(new_cm_start):
                continue

            day_after_current_membership_end = row.Enddate + datetime.timedelta(days=1)
            # Ok all good, continue
            if customer.has_subscription_on_date(day_after_current_membership_end, from_cache=False):
                new_cm_start = row.Enddate + datetime.timedelta(days=1)

                school_membership = SchoolMembership(row.school_memberships_id)

                school_membership.sell_to_customer(
                    row.auth_customer_id,
                    new_cm_start,
                    note=T("Renewal for membership %s" % row.id),
                    invoice=True,
                    payment_methods_id=row.payment_methods_id
                )

                renewed += 1
            # else:
            #
            #     print 'no subscription'
            # print renewed

        ##
        # For scheduled tasks db connection has to be committed manually
        ##
        db.commit()

        return T("Memberships renewed") + ': ' + unicode(renewed)


    def exact_online_sync_invoices(self):
        """
        Due to a timeout in tokens, sometimes invoices don't sync immediately, as a API request
        seems to be used to aquire a new token. This function can be run every 15 minutes for
        example to sync all unsynced invoices
        :return: None
        """
        from tools import OsTools
        from os_invoice import Invoice

        T = current.T
        db = current.db

        count_synced = 0
        count_errors = 0

        os_tools = OsTools()
        eo_authorized = os_tools.get_sys_property('exact_online_authorized')


        if eo_authorized == 'True':
            from os_exact_online import OSExactOnline

            os_eo = OSExactOnline()

            query = (db.invoices.ExactOnlineSalesEntryID == None)
            rows = db(query).select(db.invoices.ALL)
            for row in rows:
                invoice = Invoice(row.id)

                if not invoice.invoice_group.JournalID:
                    os_eo._log_error(
                        'update',
                        'invoice',
                        invoice.invoices_id,
                        'No JournalID specified for invoice group'
                    )
                    count_errors += 1
                else:
                    error = os_eo.update_sales_entry(invoice)
                    if error:
                        count_errors += 1
                    else:
                        count_synced += 1

        return T("m_openstudio_os_scheduler_tasks_exact_online_sync_invoices_return") + ': (' + \
               unicode(count_synced) + ' / ' + \
               unicode(count_errors) + ')'
