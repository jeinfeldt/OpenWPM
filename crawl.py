#!/usr/bin/python
# -*- coding: utf-8 -*-
'''Starts crawls executing defined workload for measurement'''
import argparse
from crawler import AnalysisCrawler, DetectionCrawler, LoginCrawler

# constants
CRAWLTYPE_ERROR = "Crawltype unknown! Use analysis, detection, login"

# public
def load_websites(file_path):
    '''loads defined amount of pages from alexa file, websites are returned
       in format http://www.[domainname].[identifier]'''
    url_format = 'http://www.%s'
    with open(file_path, 'r') as data:
        sites = [line.strip() for line in data if "#" not in line]
        sites = [url_format %(line) for line in sites if line] # remove blank
        return [x.lower() for x in sites]

# private
def _init_crawler(browser_path, manager_path, crawltype, db_prefix):
    '''crawls given sites with given parameters'''
    if crawltype == 'analysis':
        return AnalysisCrawler(browser_path, manager_path, db_prefix)
    elif crawltype == 'detection':
        return DetectionCrawler(browser_path, manager_path, db_prefix)
    elif crawltype == 'login':
        return LoginCrawler(browser_path, manager_path, db_prefix)
    else:
        raise ValueError(CRAWLTYPE_ERROR)

def _process_args(args):
    '''Adjust all necessary entities based on script args'''
    bpath, mpath, spath = args.browserparams, args.managerparams, args.sites
    # load sites
    sites = load_websites(spath)
    if args.range is not None:
        start, end = tuple(args.range.split("-"))
        sites = sites[int(start)-1:int(end)]
    # fetch and adjust crawler
    crawler = _init_crawler(bpath, mpath, args.crawltype, args.output)
    # special behaviour in case of login flag
    if args.login is not None and args.crawltype == "login":
        crawler.set_loginsite(args.login)
    return (crawler, sites)

def _init():
    '''init argument parser'''
    parser = argparse.ArgumentParser(description='''Crawl sites following
    different behaviour and collecting various data.''')
    parser.add_argument('browserparams',
                        metavar='browserparam', type=str, help='json file for browser config')
    parser.add_argument('managerparams',
                        metavar='managerparam', type=str, help='json file for manager config')
    parser.add_argument('sites',
                        metavar='sites', type=str, help='site input file (alexa format)')
    hlp = 'crawl type (analysis, detection, login)'
    parser.add_argument('crawltype',
                        metavar='crawltype', type=str, help=hlp)
    hlp = 'name of the output sqlite file, otherwise generated'
    parser.add_argument('--output',
                        metavar='output', type=str, help=hlp)
    hlp = 'log into certain site before performing crawl'
    parser.add_argument('--login',
                        metavar='login', type=str, help=hlp)
    hlp = 'optional range (including start and end) for input sites, <start>-<end> e.g. 1-5'
    parser.add_argument('--range',
                        metavar='range', type=str, help=hlp)
    return parser

def _main():
    '''wrapper for main functionality'''
    parser = _init()
    args = parser.parse_args()
    # prepare crawl
    print 'Preparing crawl...'
    crawler, sites = _process_args(args)
    # perform crawl on given sitesa
    print 'Crawling...'
    crawler.crawl(sites)
    print 'Finished crawling, data written to: %s' %(crawler.get_dbname())

# main
if __name__ == "__main__":
    _main()
