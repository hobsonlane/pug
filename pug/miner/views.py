# -*- coding: utf-8 -*-
from django.shortcuts import render_to_response
#from django.http import HttpResponse
from django.views.generic import View  #, TemplateView
from django.template.response import TemplateResponse #, HttpResponse
from django.template.loader import get_template
from django.http import Http404
from django import http
from django.utils import simplejson as json

import os
from django.shortcuts import render
from forms import GetLagForm

# from forms import GetLagForm

from pug.nlp import parse
#from pug.nlp.util import normalize_scientific_notation
#from pug.nlp.character_subset import digits
from pug.nlp import util
from pug.nlp import db

from Returns import tv_lags

def explorer(request, graph_uri=None):
    """Explore the database (or any data provided by a REST service)"""
    #return HttpResponse('Looking for template in miner/explorer.html')
    return render_to_response('miner/explorer.html')

def home(request):
    """Explore the database (or any data provided by a REST service)"""
    return render_to_response('miner/home.html')


def connections(request, edges):
    """
    Plot a force-directed graph based on the edges provided
    """
    edge_list, node_list = parse.graph_definition(edges)
    data = {'nodes': json.dumps(node_list), 'edges': json.dumps(edge_list)}
    return render_to_response('miner/connections.html', data)

def stats(request, date_offset=0, fields=None, title_prefix=None, model='WikiItem'):
    """
    In addition to chart data in data['chart'], send statistics data to view in data['stats']
    """
    data = {}

    modified_chart_data = data['chart']['chartdata']
    if 'y2' in data['chart']['chartdata']:
        matrix = db.Columns([modified_chart_data['y1'], modified_chart_data['y2']], ddof=0, tall=True)
    else:
        fields = ['date/time'] + fields
        matrix = db.Columns([modified_chart_data['x'], modified_chart_data['y']], ddof=0, tall=True)
    if fields and len(fields) > 1:
        fields = fields[:2]
    else:
        fields = [
            data['chart']['chartdata'].get('name1') or 'time',
            data['chart']['chartdata'].get('name2') or data['chart']['chartdata'].get('name') or 'value',
            ]
    fields = util.pluralize_field_names(fields)
    data.update({
        'stats': {
            'fields': fields,
            'heading': 'Statistics',
            'cov': zip(fields, matrix.cov()),
            'R': zip(fields, matrix.rho),
            },
        })
    data['chart']['chartdata'] = modified_chart_data
    data['chart']['chart_title'] = 'Time Series'
    return render_to_response('miner/stats.html', data)


class StaticView(View):
    def get(self, request, *args, **kwargs):
        template_name = ''
        try:
            template_name += 'miner/staticview/' + kwargs.get('page', '') + '.html'
            get_template(template_name) 
        except:
            raise Http404()
        return TemplateResponse(request, template_name)


class JSONView(View):
    def get(self, request, *args, **kwargs):
        # print os.path.join('static', kwargs.get('page', '') + '.json')
        # print os.path.realpath(os.path.curdir)
        # print os.getcwd()
        # print os.path.dirname(os.path.realpath(os.path.curdir))
        try:
            path = os.path.join('static', kwargs.get('page', '') + '.json')
            # print path
            context = json.load(path)
        except:
            raise Http404()
        return self.render_to_response(context)

    def render_to_response(self, context):
        "Returns a JSON response containing 'context' as payload"
        return self.get_json_response(self.convert_context_to_json(context))

    def get_json_response(self, content, **httpresponse_kwargs):
        "Construct an `HttpResponse` object."
        return http.HttpResponse(content,
                                 content_type='application/json',
                                 **httpresponse_kwargs)

    def convert_context_to_json(self, context):
        "Convert the context dictionary into a JSON object"
        # Note: This is *EXTREMELY* naive; in reality, you'll need
        # to do much more complex handling to ensure that arbitrary
        # objects -- such as Django model instances or querysets
        # -- can be serialized as JSON.
        return json.dumps(context)


# testcele progress bar test

# #from django.shortcuts import render_to_response
# from django.template import RequestContext
# #from django.http import HttpResponse
# #from django.utils import simplejson as json
# from django.views.decorators.csrf import csrf_exempt

# from celery.result import AsyncResult

# from miner import tasks


# def testcele(request):
#     if 'task_id' in request.session.keys() and request.session['task_id']:
#         task_id = request.session['task_id']
#     return render_to_response('miner/testcele.html', locals(), context_instance=RequestContext(request))


# @csrf_exempt
# def do_task(request):
#     """ A view the call the task and write the task id to the session """
#     data = 'Fail'
#     if request.is_ajax():
#         job = tasks.create_models.delay()
#         request.session['task_id'] = job.id
#         data = job.id
#     else:
#         data = 'This is not an ajax request!'

#     json_data = json.dumps(data)

#     return HttpResponse(json_data, mimetype='application/json')


# @csrf_exempt
# def poll_state(request):
#     """ A view to report the progress to the user """
#     data = 'Fail'
#     if request.is_ajax():
#         if 'task_id' in request.POST.keys() and request.POST['task_id']:
#            task_id = request.POST['task_id']
#            task = AsyncResult(task_id)
#            data = task.result or task.state
#         else:
#             data = 'No task_id in the request'
#     else:
#         data = 'This is not an ajax request'
#     json_data = json.dumps(data)
#     return HttpResponse(json_data, mimetype='application/json')



def submit_lag_form(request, f, context, *args):
    '''Line chart with zoom and pan and "focus area" at bottom like google analytics.
    
    Data takes a long time to load, so you better use this to increase the timeout
    python gunicorn bigdata.wsgi:application --bind bigdata.enet.sharplabs.com:8000 --graceful-timeout=60 --timeout=60
    '''
    context['form'] = f

    model_numbers = [s.strip() for s in f.cleaned_data['model'].split(',')]
    fiscal_years = request.GET.getlist('fiscal_years')

    hist_formats = ['hist', 'pmf', 'cdf', 'cmf']
    hist_format = 'cmf'
    if args and len(str(args[0])):
        hist_format_str = str(args[0]).lower().strip()
    if hist_format_str in hist_formats:
        hist_format = hist_format_str

    reasons = request.GET.get('r', 'R').split(',') or ['R']
    account_numbers = request.GET.get('an', '').split(',') or ['']

    params = {
        'FY': fiscal_years,
        'Reason': reasons,
        'Account #': account_numbers,
        'Model #': model_numbers,
        }

    # print params
    lags = tv_lags.explore_lags(fiscal_years=fiscal_years, model_numbers=model_numbers, reasons=reasons, account_numbers=account_numbers, verbosity=1)
    hist = lags[hist_formats.index(hist_format)+1]

    #print hist_formats.index(hist_format)
    #print [max([y[1] for y in x]) for x in lags[1:]]

    hist_t=[[],[],[],[]]
    names, xdata, ydata = [], [], []
    if hist and len(hist) > 1:
        hist_t = util.transposed_matrix(hist[1:])

        if hist[0]:
            # print hist[0]
            names = hist[0][1:]
            #print names
            xdata = hist_t[0]
            ydata = hist_t[1:]
    # print names

    #tooltip_date = "%d %b %Y %H:%M:%S %p"
    extra_series = {"tooltip": {"y_start": " ", "y_end": " returns"},
                   #"date_format": tooltip_date
                   }

    chartdata = { 'x': xdata }

    for i, name in enumerate(names):
        chartdata['name%d' % (i + 1)] = name
        chartdata['y%d' % (i + 1)] = ydata[i]
        chartdata['extra%d' % (i + 1)] = extra_series

    subtitle = []

    for k, v in params.iteritems():
        if len(v) == 1 and v[0] and len(str(v[0])):
            subtitle += [str(k) + ': ' + str(v[0])] 

    context.update({'data': {
        'title': 'Returns Lag <font color="gray">' + hist_format.upper() + '</font>',
        'subtitle': ', '.join(subtitle),
        'charttype': "lineWithFocusChart",
        'chartdata': chartdata,
        'chartcontainer': 'linewithfocuschart_container',
        'extra': {
            'x_is_date': False,
            'x_axis_format': ',.0f', # %b %Y %H',
            'y_axis_format': ',.0f', # "%d %b %Y"
            'tag_script_js': True,
            'jquery_on_ready': True,
            },
        'form': {},
        }})
    print context
    return render(request, 'miner/lag.html', context)


def lag(request, *args):
    # print 'lag with form'
    context = {}
    f = GetLagForm()

    if request.method == 'POST':
        f = GetLagForm(request.POST)

    elif request.method == 'GET':
        model = request.GET.get('mn', "") or request.GET.get('model', "")
        initial = {'submit': 'Submit', 'model': model}
        f = GetLagForm(data=initial) #, initial=initial)

    context['form'] = f
    context['form_is_valid'] = f.is_valid()
    return submit_lag_form(request, f, context, *args)
