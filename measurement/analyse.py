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

def _init_evaluation(eva, db_path):
    '''Creates dict with all evaluation functions and corresponding metric'''
    data = {}
    # analysis scripts and detection scripts differ
    if "analysis" in db_path:
        data = {"crawl": [("success", eva.eval_crawlsuccess),
                          ("time", eva.calc_execution_time)],
                "storage": [("firstparty_cookies", eva.eval_first_party_cookies),
                            ("thirdparty_cookies", eva.eval_third_party_cookies),
                            ("flash_cookies", eva.eval_flash_cookies),
                            ("localstorage", eva.eval_localstorage_usage),
                            ("rank_cookie_domains", eva.rank_third_party_cookie_domains),
                            ("rank_cookie_keys", eva.rank_third_party_cookie_keys)],
                "http": [("requests", eva.eval_requests),
                         #("trackingcontext", eva.eval_tracking_context), # needs parameter
                         #("loadingtime", eva.calc_pageload),
                         #("cookiesync", eva.detect_cookie_syncing),
                         #("prominence_rank", eva.rank_third_party_prominence),
                         #("simple_rank", eva.rank_third_party_domains)
                         ],
                "fingerprinting": [
                                   #("fingerprint_matches", eva.eval_fingerprint_scripts), # needs parameter
                                   #("detected_canvas_js", eva.detect_canvas_fingerprinting),
                                   #("detected_font_js", eva.detect_font_fingerprinting)
                                   ]}
    else:
        data = {"crawl":  [("success", eva.eval_crawlsuccess),
                           ("time", eva.calc_execution_time)],
                "storage": [],
                "http": [("detect_trackers", eva.detect_trackers)],
                "fingerprinting": []}
    return data

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

def evaluate(evaluation_dict):
    '''Runs defined evaluation and fetches all results in single dict'''
    data = {}
    # perform evaluation defined by dict
    for evaltype, evalfuncs in evaluation_dict.items():
        data[evaltype] = {}
        for tup in evalfuncs:
            name, func = tup
            if name == "trackingcontext":
                result = func(_load_json(BLOCKLIST))
            elif name == "fingerprint_matches":
                result = func(_load_json(FINGERPRINT_BLACKLIST))
            else:
                result = func()
            data[evaltype][name] = result
    return data

def _main():
    '''wrapper for main functionality'''
    db_path, output = _init()
    evaluator = DataEvaluator(db_path)
    print "Starting analysis..."
    evaluation = _init_evaluation(evaluator, db_path)
    data = evaluate(evaluation)
    _write_data(data, output)
    evaluator.close()

#main
if __name__ == "__main__":
    _main()
