#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
Performs analysis based on data captured by crawls in order to answer
questions formulated in thesis
'''
import sys, json, os, sqlite3

#constants
HELP = '''Scripts needs to be executed with the following parameters:
1. path to crawl-data (sqlite)\n(2. name for outputfile)'''

def eval_first_party_cookies(connection):
    '''Evaluates prevalence of first party cookies based on crawl data.
       first-party: cookies set by top level domain'''
    data = {}
    qry = '''select site_url, baseDomain
            from site_visits natural join profile_cookies;'''
    cursor = connection.cursor()
    # perform analysis
    cursor.execute(qry)
    for site_url, base_domain in cursor.fetchall():
        main_domain = site_url.strip("http://www.")
        if main_domain == base_domain:
            amount = data.get(main_domain, 0)
            data[main_domain] = amount + 1
    data['total_sum'] = reduce(lambda x, y: x + y, data.values())
    return data

def eval_third_party_cookies(connection):
    '''Evaluates prevalence of third party cookies based on crawl data.
       third-party: cookies set outside of top level domain'''
    data = {}
    qry = '''select site_url, baseDomain
            from site_visits natural join profile_cookies;'''
    cursor = connection.cursor()
    # perform analysis
    cursor.execute(qry)
    for site_url, base_domain in cursor.fetchall():
        main_domain = site_url.strip("http://www.")
        if main_domain != base_domain:
            amount = data.get(main_domain, 0)
            data[main_domain] = amount + 1
    data['total_sum'] = reduce(lambda x, y: x + y, data.values())
    return data

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
    connection = sqlite3.connect(db_path)
    print "Starting analysis..."
    data = eval_first_party_cookies(connection)
    data = eval_third_party_cookies(connection)
    if output is not None:
        print "Finished analysis, data written to %s" %(output)
    else:
        print "Finished analysis, here is the data:"
        print data['total_sum']
    connection.close()
#main
if __name__ == "__main__":
    _main()
