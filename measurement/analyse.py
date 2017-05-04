#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
Performs analysis based on data captured by crawls in order to answer
questions formulated in thesis
'''
import sys, json, os
from evaluation import DataEvaluator

#constants
HELP = '''Scripts needs to be executed with the following parameters:
1. path to crawl-data (sqlite)\n(2. name for outputfile)'''

def _write_result(data, output_path):
    '''writes all results to file'''
    pass

def _print_result(data):
    '''writes all results to console'''
    pass

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
    #data = evaluator.eval_first_party_cookies()
    #data = evaluator.eval_third_party_cookies()
    data = evaluator.rank_third_party_domains()
    if output is not None:
        print "Finished analysis, data written to %s" %(output)
    else:
        print "Finished analysis, here is the data:"
    evaluator.close()

#main
if __name__ == "__main__":
    _main()
