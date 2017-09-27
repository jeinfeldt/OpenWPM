#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
Handles reading results and formatted output to console and file
to get an overview regarding measured metrics
'''
import pprint
import pdfkit
from jinja2 import Environment, FileSystemLoader

TEMPLATE = "assets/report.html"
PDF_OPTIONS = {'quiet': '', 'margin-top': '0.75in', 'margin-right': '0.75in',
               'margin-bottom': '0.75in', 'margin-left': '0.75in',}

def write_data(data, path):
    '''Writes all formatted results either to file or console'''
    if path is not None:
        context = _format_data(data)
        env = Environment(loader=FileSystemLoader('.'))
        temp = env.get_template(TEMPLATE)
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
    context['crawl_type'] = data['type']
    return context

def _map_storage_data(data):
    '''Maps storage data for template'''
    context = {}
    # first-party cookies
    context['first_cookies'] = data['firstparty_cookies']['total_sum']
    context['first_cookies_avg'] = data['firstparty_cookies']['cookie_avg']
    context['first_lifetime_avg'] = data['cookie_lifetime']['fp_expiry_avg']
    # third-party cookies
    context['third_cookies'] = data['thirdparty_cookies']['total_sum']
    context['third_cookies_avg'] = data['thirdparty_cookies']['cookie_avg']
    context['third_lifetime_avg'] = data['cookie_lifetime']['tp_expiry_avg']
    # other
    context['flash_cookies'] = data['flash_cookies']['total_sum']
    context['localstorage'] = data['localstorage']['total_sum']
    # tracking cookies
    context['tracking_cookies'] = data['tracking_cookies']['total_sum']
    context['tracking_cookies_avg'] = data['tracking_cookies']['tracking_cookie_avg']
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
    context['avg_resp_bytes'] = data['response_traffic']['byte_avg']
    # ranks
    if 'rank_requests' in data:
        context['rank_requests'] = data['rank_requests']
    if 'rank_prominence' in data:
        context['rank_prominence'] = data['rank_prominence']
    if 'rank_org' in data:
        context['rank_org'] = data['rank_org']
    if 'rank_simple' in data:
        context['rank_prevalence'] = data['rank_simple']
    # trackers
    if 'new_trackers' in data:
        context['new_trackers'] = data['detected_trackers']
    context['count_trackers'] = data['trackingcontext']['total_sum']
    context['avg_trackers'] = data['trackingcontext']['tracker_avg']
    context['count_unique'] = len(data['trackingcontext']['unique_trackers'])
    return context

def _map_fingerprinting_data(data):
    '''Maps fingerprinting data for template'''
    context = {}
    context['canvas_scripts'] = data['detected_canvas_js']
    context['font_scripts'] = data['detected_font_js']
    if 'fingerprint_matches' in data:
        context['count_fp_scripts'] = data['fingerprint_matches']['total_sum']
    return context
