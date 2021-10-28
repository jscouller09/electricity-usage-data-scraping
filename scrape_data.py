# ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# Name:         Electricity data web scrape
# Purpose:      Automatically scrape hourly electricity usage data from the web
#
# Author:       james.scouller
#
# Created:      28/10/2021
# ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# global imports
import os
import re
import math
import time
import functools
import traceback
import sys
import pandas as pd
from environs import Env
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException
# ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# custom module imports
# ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# main code

# make sure geoDriver starts hidden
flag = 0x08000000  # No-Window flag
# flag = 0x00000008  # Detached-Process flag, if first doesn't work
webdriver.common.service.subprocess.Popen = functools.partial(webdriver.common.service.subprocess.Popen, creationflags=flag)

def error_catcher(func):
    '''
    Error catcher decorator to handle closing down browser properly if an error is encountered
    '''
    def run_and_catch(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except TimeoutException:
            print('{} method timed out waiting for an element!'.format(func.__name__))
            traceback.print_exc()
        except NoSuchElementException:
            print('{} method could not find an element!'.format(func.__name__))
            traceback.print_exc()
        except Exception:
            print('{} method caused an unexpected error!'.format(func.__name__))
            traceback.print_exc()
        # make sure to close web browser instance after error handling if an error is encountered
        args[0].driver.close()

    return run_and_catch

@error_catcher
class AutoBrowser(object):
    '''
    Selenium driven instance of Firefox for automatically navigating webpages to scrape data

    :param env_filepath: Optional input specifying location of environment file with urls and login info
    :param timeout: Optional input specifying length of time to wait for element to appear in seconds
    :returns: None
    :raises TimeoutException: Raised when a target element does not appear after the configured timeout
    '''

    def __init__(self, env_filepath=None, timeout=10):
        # working dir
        self.working_dir = os.path.dirname(__file__)
        print('Starting Firefox...')
        self.driver = webdriver.Firefox()
        self.driver.implicitly_wait(1)
        # hide window off-screen if desired
        # driver.set_window_position(-10000, 0)
        # setup a waiter helper
        self.timeout = timeout
        self.wait = WebDriverWait(self.driver, self.timeout)
        # get data from env file
        env_filepath = env_filepath if env_filepath else os.path.join(self.working_dir, '.env')
        Env().read_env(env_filepath)
        # assume env file contains a login url and a second url that points towards page to scrape data from
        self.login_url = os.getenv('LOGIN_URL', 'https://www.google.com')
        self.data_url = os.getenv('DATA_URL', 'https://www.google.com')
        # assume env file contains login credentials
        self.username = os.getenv('WEB_USERNAME', 'username')
        self.password = os.getenv('WEB_PASSWORD', '1234')

        print('Initialised {}!'.format(self.__class__.__name__))

    @error_catcher
    def login(self, continue_btn_id, login_btn_id, username_fld_id, password_fld_id):
        # go to login page and wait for login button to appear
        print('Loading login page...')
        self.driver.get(self.login_url)
        # assume we have a front page that just asks for our username first
        msg = 'button element with id={} was not clickable within {}s'.format(continue_btn_id, self.timeout)
        elem_btn_continue = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button#{}'.format(continue_btn_id))), msg)
        elem_fld_username = self.driver.find_element_by_css_selector('input#{}'.format(username_fld_id))
        elem_fld_username.send_keys(self.username)
        elem_btn_continue.click()
        # now assume we are prompted for a password
        msg = 'button element with id={} was not clickable within {}s'.format(login_btn_id, self.timeout)
        elem_btn_login = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button#{}'.format(login_btn_id))), msg)
        elem_fld_password = self.driver.find_element_by_css_selector('input#{}'.format(password_fld_id))
        elem_fld_password.send_keys(self.password)
        elem_btn_login.click()
        print('Logging in...')


browser = AutoBrowser()
browser.login(continue_btn_id='continue', login_btn_id='next', username_fld_id='email', password_fld_id='password')
