#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
Performs analysis based on data captured by crawls in order to answer
questions formulated in thesis
'''
import sys
import json
import pprint
from evaluation import DataEvaluator

#constants
HELP = '''Scripts needs to be executed with the following parameters:
1. path to crawl-data (sqlite)\n(2. name for outputfile)'''
FINGERPRINT_BLACKLIST = "fingerprinting_blacklist.json"
BLOCKLIST = "disconnect_blocklist.json"

def _load_json(path):
    '''Reads json file ignoring comments'''
    ignore = ["__comment", "license"]
    with open(path) as raw:
        data = json.load(raw)
        for ele in ignore:
            if ele in data:
                data.pop(ele)
    return data

def _write_data(data, output_path):
    '''writes all results either to file or console'''
    prettyp = pprint.PrettyPrinter(indent=4)
    if output_path is not None:
        print "Finished analysis, data written to %s" %(output_path)
    else:
        print "Finished analysis, here is the data:"
        prettyp.pprint(data)

def _init():
    '''guard clause and init for script'''
    args = sys.argv[1:]
    if len(args) < 1:
        print HELP
        sys.exit()
    if len(args) == 1:
        args = [args[0], None]
    return args

def _main():
    '''wrapper for main functionality'''
    db_path, output = _init()
    evaluator = DataEvaluator(db_path)
    print "Starting analysis..."
    data = {}
    #data = evaluator.eval_first_party_cookies()
    #data = evaluator.eval_third_party_cookies()
    #data = evaluator.rank_third_party_cookie_domains(10)
    #data = evaluator.rank_third_party_cookie_keys(10)
    #data = evaluator.eval_flash_cookies()
    #data = evaluator.calc_execution_time()
    #data = evaluator.eval_localstorage_usage()
    #data = evaluator.map_site_to_js()
    data = evaluator.eval_fingerprint_scripts(evaluator.detect_canvas_fingerprinting())
    #data = evaluator._map_js_to_symbol()
    #data = evaluator.detect_canvas_fingerprinting()
    #data = evaluator._map_site_to_request()
#    data = evaluator.rank_third_party_domains(10)
    #data = evaluator.eval_requests()
    #data = evaluator.eval_tracking_context(_load_json(BLOCKLIST))
    #data = evaluator.calc_pageload()
    #data = evaluator.calc_num_users()
    #data = evaluator.detect_trackers(3)
    #data = evaluator._prepare_detection_data()
    #data = evaluator._extract_http_pairs("https://consent.google.com/status?continue=https://www.google.de&pc=s&timestamp=149553886")
    #data = evaluator._map_site_to_rank()
    #data = evaluator.rank_third_party_prominence(15)
    #data = evaluator._is_domain_present_db(4, "doubleclick.net")
    _write_data(data, output)
    evaluator.close()

#main
if __name__ == "__main__":
    _main()
