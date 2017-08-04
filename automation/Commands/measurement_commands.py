#!/usr/bin/python
# -*- coding: utf-8 -*-
'''Implementations regarding new commands for measurement: login to social media'''
from selenium.common.exceptions import NoSuchElementException
from utils.webdriver_extensions import wait_and_find
import json
import time

def login(webdriver, logindata):
    '''Login to page with data provided in logindata. logindata
       should be touple containing emailid, passid, email, password, submitid'''
    mailid, passid, email, password, submitid = json.loads(logindata)
    try:
        # enter email and password
        ele = webdriver.find_element_by_id(mailid)
        ele.send_keys(email)
        time.sleep(5)
        ele = webdriver.find_element_by_id(passid)
        ele.send_keys(password)
        time.sleep(5)
        # login
        ele = webdriver.find_element_by_id(submitid)
        ele.click()
    except NoSuchElementException:
        print "Could not log in!"
