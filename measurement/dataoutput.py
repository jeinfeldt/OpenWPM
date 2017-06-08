#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
Handles reading results and formatted output to console and file
to get an overview regarding measured metrics
'''
import pprint
import pdfkit
from jinja2 import Environment, FileSystemLoader

ANALYSIS_TEMPLATE = "analysis-report.html"
DETECTION_TEMPLATE = "detection-report.html"
PDF_OPTIONS = {'quiet': ''}

def write_data(data, path):
    '''Writes all formatted results either to file or console'''
    if path is not None:
        context = _format_data(data)
        env = Environment(loader=FileSystemLoader('.'))
        temp = env.get_template(ANALYSIS_TEMPLATE)
        pdfkit.from_string(temp.render(context), path, options=PDF_OPTIONS)
    else:
        pprinter = pprint.PrettyPrinter(indent=4)
        pprinter.pprint(data)

def _format_data(data):
    '''Maps data to format required by tempalte engine'''
    context = {}
    context.update(_map_crawl_data(data['crawl']))
    context.update(_map_storage_data(data['storage']))
    context.update(_map_http_data(data['http']))
    context.update(_map_fingerprinting_data(data['fingerprinting']))
    return context

def _map_crawl_data(data):
    '''Maps crawl data for template'''
    context = {}
    context['num_pages'] = data['success']['num_pages']
    context['time'] = data['time']
    context['num_timeouts'] = data['success']['num_timeouts']
    context['rate_timeouts'] = data['success']['rate_timeouts']
    return context

def _map_storage_data(data):
    '''Maps storage data for template'''
    context = {}
    context['first_cookies'] = data['firstparty_cookies']['total_sum']
    context['third_cookies'] = data['thirdparty_cookies']['total_sum']
    context['flash_cookies'] = data['flash_cookies']['total_sum']
    context['localstorage'] = data['localstorage']['total_sum']
    # ranks
    context['cookie_domains'] = data["rank_cookie_domains"]
    context['cookie_keys'] = data["rank_cookie_keys"]
    return context

def _map_http_data(data):
    '''Maps http data for template'''
    context = {}
    context['count_requests'] = data['requests']['total_sum']
    context['avg_requests'] = data['requests']['request_avg']
    context['avg_pageload'] = data['loadingtime']['loadtime_avg']
    context['count_cookiesync'] = data['cookiesync']['total_sum']
    # ranks
    if 'rank_simple' in data:
        context['rank_prevalence'] = data['rank_simple']
    if 'rank_prominence' in data:
        context['rank_prominence'] = data['rank_prominence']
    # trackers
    context['count_trackers'] = data['trackingcontext']['total_sum']
    context['avg_trackers'] = data['trackingcontext']['tracker_avg']
    return context

def _map_fingerprinting_data(data):
    '''Maps fingerprinting data for template'''
    context = {}
    context['canvas_scripts'] = data['detected_canvas_js']
    context['font_scripts'] = data['detected_font_js']
    if 'fingerprint_matches' in data:
        context['count_fp_scripts'] = data['fingerprint_matches']['total_sum']
    return context
