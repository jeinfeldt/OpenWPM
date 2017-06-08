#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
Handles reading results and formatted output to console and file
to get an overview regarding measured metrics
'''
import pprint
import pdfkit
from jinja2 import Environment, FileSystemLoader

REPORT_TEMPLATE = "report.html"

def write_data(data, path):
    '''Writes all formatted results either to file or console'''
    if path is not None:
        context = _format_data(data)
        env = Environment(loader=FileSystemLoader('.'))
        temp = env.get_template(REPORT_TEMPLATE)
        pdfkit.from_string(temp.render(context), path)
    else:
        pprinter = pprint.PrettyPrinter(indent=4)
        pprinter.pprint(data)

def _format_data(data):
    '''Maps data to format required by tempalte engine'''
    context = {}
    # meta data
    context['num_pages'] = data['crawl']['success']['num_pages']
    context['time'] = data['crawl']['time']
    context['num_timeouts'] = data['crawl']['success']['num_timeouts']
    context['rate_timeouts'] = data['crawl']['success']['rate_timeouts']
    return context
