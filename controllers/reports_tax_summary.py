# -*- coding: utf-8 -*-

# from general_helpers import datestr_to_python
# from general_helpers import get_label
# from general_helpers import get_submenu
# from general_helpers import get_months_list
# from general_helpers import get_last_day_month
# from general_helpers import get_classname
# from general_helpers import User_helpers
# from general_helpers import Memo_links
# from general_helpers import class_get_teachers
# from general_helpers import max_string_length
# from general_helpers import iso_to_gregorian
# from general_helpers import classes_get_status
# from general_helpers import set_form_id_and_get_submit_button
#
# from gluon.tools import prettydate
#
# from openstudio.os_classcards_helper import ClasscardsHelper
# from openstudio.os_class import Class
# from openstudio.os_class_schedule import ClassSchedule
# from openstudio.os_attendance_helper import AttendanceHelper
# from openstudio.os_reports import Reports
# from openstudio.os_invoice import Invoice
# from openstudio.os_invoices import Invoices
# from openstudio.os_school_subscription import SchoolSubscription
# from openstudio.os_customer_classcard import CustomerClasscard
#
# import datetime
# import operator
# import cStringIO
# import openpyxl


@auth.requires(auth.has_membership(group_id='Admins') or \
               auth.has_permission('read', 'reports_tax_summary'))
def index():
    """
        Main page for reports tax summary controller
    """
    from openstudio.os_reports import Reports

    index_process_request_vars()

    reports = Reports()

    data = reports.get_tax_summary_rows(
        session.reports_tax_summary_index_date_from,
        session.reports_tax_summary_index_date_until
    )

    print data

    rows = data['rows']
    sum_subtotal = data['sum_subtotal']
    sum_vat = data['sum_vat']
    sum_total = data['sum_total']

    header = THEAD(TR(
        TH("Tax rate"),
        TH("Revenue"),
        TH("Taxes"),
        TH()
    ))

    content = TABLE(
        header,
        _class='table table-striped table-hover'
    )

    for i, row in enumerate(rows):
        repr_row = list(rows[i:i + 1].render())[0]

        print repr_row

        content.append(TR(
            TD(repr_row.invoices_items.tax_rates_id or "Not specified"),
            TD(represent_float_as_amount(row[sum_total])),
            TD(represent_float_as_amount(row[sum_vat])),
            TD()
        ))


    result = index_get_form(
        session.reports_tax_summary_index_date_from,
        session.reports_tax_summary_index_date_until,
    )
    form = result['form']

    show_current_month = A(
        T("Current month"),
        _href=URL('index_show_current_month'),
        _class='btn btn-default'
    )

    header_tools = SPAN(
        show_current_month
    )

    return dict(
        form=result['form_display'],
        content=content,
        submit=result['submit'],
        header_tools=header_tools
    )


def index_process_request_vars(var=None):
    """
        This function takes the request.vars as a argument and
    """
    from general_helpers import get_last_day_month
    from general_helpers import datestr_to_python

    today = TODAY_LOCAL
    if 'date_from' in request.vars:
        date_from = datestr_to_python(DATE_FORMAT, request.vars['date_from'])
    elif not session.reports_tax_summary_index_date_from is None:
        date_from = session.reports_tax_summary_index_date_from
    else:
        date_from = datetime.date(
            today.year,
            today.month,
            1
        )
    session.reports_tax_summary_index_date_from = date_from

    if 'date_until' in request.vars:
        date_until = datestr_to_python(DATE_FORMAT, request.vars['date_until'])
    elif not session.reports_tax_summary_index_date_until is None:
        date_until = session.reports_tax_summary_index_date_until
    else:
        date_until = get_last_day_month(today)
    session.reports_tax_summary_index_date_until = date_until

    # if 'school_locations_id' in request.vars:
    #     slID = request.vars['school_locations_id']
    # elif not session.reports_tax_summary_index_school_locations_id is None:
    #     slID = session.reports_tax_summary_index_school_locations_id
    # else:
    #     slID = None
    # session.reports_tax_summary_index_school_locations_id = slID

    # session.reports_tax_summary_index = request.function


def index_get_form(date_from, date_until):
    """
    Get month chooser form for index
    """
    from general_helpers import get_months_list
    from general_helpers import set_form_id_and_get_submit_button

    months = get_months_list()

    form = SQLFORM.factory(
        Field('date_from', 'date', required=True,
            default=date_from,
            requires=IS_DATE_IN_RANGE(format=DATE_FORMAT,
                                      minimum=datetime.date(1900,1,1),
                                      maximum=datetime.date(2999,1,1)),
            represent=represent_date,
            label=T("From date"),
            widget=os_datepicker_widget),
        Field('date_until', 'date', required=True,
            default=date_until,
            requires=IS_DATE_IN_RANGE(format=DATE_FORMAT,
                                      minimum=datetime.date(1900,1,1),
                                      maximum=datetime.date(2999,1,1)),
            represent=represent_date,
            label=T("Until date"),
            widget=os_datepicker_widget),
        # Field('school_locations_id', db.school_locations,
        #       requires=IS_IN_DB(db(loc_query),
        #                         'school_locations.id',
        #                         '%(Name)s',
        #                         zero=T("All locations")),
        #       default=session.reports_tax_summary_index_school_locations_id,
        #       represent=lambda value, row: locations_dict.get(value, T("No location")),
        #       label=T("Location")),
        formstyle='bootstrap3_stacked',
        submit_button=T("Run report")
    )

    result = set_form_id_and_get_submit_button(form, 'MainForm')
    form = result['form']
    submit = result['submit']

    form_display = DIV(
        XML('<form id="MainForm" action="#" enctype="multipart/form-data" method="post">'),
        DIV(LABEL(form.custom.label.date_from),
            form.custom.widget.date_from,
            _class='col-md-6'
        ),
        DIV(LABEL(form.custom.label.date_until),
            form.custom.widget.date_until,
            _class='col-md-6'
        ),
        form.custom.end,
        _class='row'
    )

    return dict(
        form=result['form'],
        submit=result['submit'],
        form_display=form_display
    )

# helpers start

# def subscriptions_get_menu(page=None):
#     pages = [
#         (['subscriptions_overview', T('Subscriptions overview'), URL('reports',"subscriptions_overview")]),
#         (['subscriptions_new', T('New subscriptions'), URL('reports',"subscriptions_new")]),
#         (['subscriptions_stopped', T('Stopped subscriptions'), URL('reports',"subscriptions_stopped")]),
#         (['subscriptions_paused', T('Paused subscriptions'), URL('reports',"subscriptions_paused")]),
#         (['subscriptions_alt_prices', T('Alt. prices'), URL('reports',"subscriptions_alt_prices")]),
#         ]
#
#     horizontal = True
#     if request.user_agent()['is_mobile']:
#         horizontal = False
#
#     return os_gui.get_submenu(pages,
#                               page,
#                               horizontal=horizontal,
#                               htype='tabs')
#
