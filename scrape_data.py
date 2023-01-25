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
import functools
import traceback
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from selenium.webdriver import Firefox
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
# ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# custom module imports
# ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# main code


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
        exit()

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
        # outputs dir
        self.outputs_dir = os.path.join(self.working_dir, 'outputs')
        if not os.path.exists(self.outputs_dir):
            os.makedirs(self.outputs_dir)
        # setup downloads location
        options = Options()
        options.set_preference('browser.download.folderList', 2)
        options.set_preference('browser.download.manager.showWhenStarting', False)
        options.set_preference('browser.download.dir', self.outputs_dir)
        options.set_preference('browser.download.useDownloadDir', True)
        options.set_preference('browser.download.manager.useWindow', False)
        options.set_preference('browser.helperApps.neverAsk.saveToDisk', 'text/plain')
        service = Service(os.path.join(self.working_dir, 'geckodriver.exe'))
        # start browser
        print('Starting Firefox...')
        self.driver = Firefox(service=service, options=options)
        self.driver.implicitly_wait(1)
        # hide window off-screen if desired
        # driver.set_window_position(-10000, 0)
        # setup a waiter helper
        self.timeout = timeout
        self.wait = WebDriverWait(self.driver, self.timeout)
        # get data from env file
        env_filepath = env_filepath if env_filepath else os.path.join(self.working_dir, '.env')
        load_dotenv(env_filepath)
        # assume env file contains a login url
        self.login_url = os.getenv('LOGIN_URL', 'https://www.google.com')
        # assume env file contains login credentials
        self.username = os.getenv('WEB_USERNAME', 'username')
        self.password = os.getenv('WEB_PASSWORD', '1234')

        print('Initialised {}!'.format(self.__class__.__name__))

    @error_catcher
    def login(self, continue_btn_id, login_btn_id, username_fld_id, password_fld_id, load_invisible_id=None, success_visible_cls=None, success_invisible_cls=None):
        # go to login page and wait for login button to appear
        print('Loading login page...')
        self.driver.implicitly_wait(1)
        self.driver.get(self.login_url)
        # assume we have a front page that just asks for our username first
        msg = 'button element with id={} was not clickable within {}s'.format(continue_btn_id, self.timeout)
        elem_btn_continue = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button#{}'.format(continue_btn_id))), msg)
        elem_fld_username = self.driver.find_element(by=By.CSS_SELECTOR, value='input#{}'.format(username_fld_id))
        elem_fld_username.send_keys(self.username)
        elem_btn_continue.click()
        print('Clicked button {}'.format(elem_btn_continue.text))
        # wait for page to load - target a particular element dissappearing such as splash screen
        if load_invisible_id:
            msg = 'element with class={} was not invisible within {}s'.format(load_invisible_id, self.timeout)
            self.wait.until(EC.invisibility_of_element_located((By.ID, load_invisible_id)))
        # now assume we are prompted for a password
        msg = 'button element with id={} was not clickable within {}s'.format(login_btn_id, self.timeout)
        elem_btn_login = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button#{}'.format(login_btn_id))), msg)
        elem_fld_password = self.driver.find_element(by=By.CSS_SELECTOR, value='input#{}'.format(password_fld_id))
        elem_fld_password.send_keys(self.password)
        elem_btn_login.click()
        print('Clicked button {}'.format(elem_btn_login.text))
        print('Logging in...')
        if success_visible_cls:
            # wait for page to load - target a particular element such as a welcome message
            msg = 'element with class={} was not visible within {}s'.format(success_visible_cls, self.timeout)
            self.wait.until(EC.visibility_of_all_elements_located((By.CLASS_NAME, success_visible_cls)), msg)
        if success_invisible_cls:
            # wait for page to load - target a particular element disappearing such as a splash screen
            msg = 'element with class={} was not invisible within {}s'.format(success_invisible_cls, self.timeout)
            self.wait.until(EC.invisibility_of_element_located((By.CLASS_NAME, success_invisible_cls)))
        print('Logged in!')

    @error_catcher
    def click_button(self, data_btn_css, hiding_elem_css='wave-portal', i=0):
        # first make sure hiding element has gone
        msg = 'element with class={} was not invisible within {}s'.format(hiding_elem_css, self.timeout)
        self.wait.until(EC.invisibility_of_element_located((By.CLASS_NAME, hiding_elem_css)), msg)
        # wait for a button on the data page to load then click it
        print('Waiting for button to be clickable...')
        msg = 'button element targeted by CSS selector={} was not clickable within {}s'.format(data_btn_css, self.timeout)
        if i==0:
            # only expecting 1 match, so response will just be the element
            elem_btn_data = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, data_btn_css)), msg)
        else:
            # expecting multiple matches - wait till all visible then select particular one
            elem_btns = self.wait.until(EC.visibility_of_all_elements_located((By.CSS_SELECTOR, data_btn_css)), msg)
            elem_btn_data = elem_btns[i]
        btn_name = elem_btn_data.text
        elem_btn_data.click()
        print('Clicked button {}'.format(btn_name))

    @error_catcher
    def extract_data(self, toggle_btn_css, previous_btn_css, no_data_css, data_css, download_btn_css):
        # first wait for the toggle button selecting days to appear
        msg = 'button element targeted by CSS selector={} was not clickable within {}s'.format(toggle_btn_css, self.timeout)
        elem_btn_toggle = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, toggle_btn_css)), msg)

        # now check if the no-data element is shown, if so we need to click the back button to go back 1 or 2 days
        data_found = False
        while not data_found:
            try:
                self.driver.find_element(by=By.CSS_SELECTOR, value=no_data_css)
                # click the back button to get data from previous day
                self.click_button(previous_btn_css)
            except NoSuchElementException:
                # check if we now have data showing
                self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, data_css)))
                data_found = True

        # check if data already exists in the output folder for this day - only download new data
        cur_date = pd.to_datetime(elem_btn_toggle.text)
        downloaded_dates = [pd.to_datetime(f.split(' to 11 59PM ')[1][:-4]) for f in os.listdir(self.outputs_dir) if os.path.isfile(os.path.join(self.outputs_dir, f))]
        if cur_date not in downloaded_dates:
            # now to download data for the current day
            self.click_button(download_btn_css)
            print('Downloaded data for {:%Y-%m-%d}'.format(cur_date))
        else:
            print('Skipped downloading data for {:%Y-%m-%d}'.format(cur_date))

        # then navigate back 1 day
        self.click_button(previous_btn_css)

        return cur_date


# initialise browser
browser = AutoBrowser()
# do login
browser.login(continue_btn_id='continue', login_btn_id='next', username_fld_id='email', password_fld_id='password', load_invisible_id='loader', success_visible_cls='account-switcher-button-name', success_invisible_cls='loading-portal')
# navigate to usage page
print('Navigating to usage page...')
browser.click_button('div.header-tabs-top-link', hiding_elem_css='loading-portal', i=0)
browser.click_button('a[href="/account/products/consumption"]', hiding_elem_css='loading-portal')
# click the 3rd match for the button class, which is the hourly data button
browser.click_button('button.electricity-historical-tabs', hiding_elem_css='loading-portal', i=2)
# extract data
stop_date = pd.to_datetime('2023-01-22')
cur_date = datetime.now()
while cur_date > stop_date:
    cur_date = browser.extract_data(toggle_btn_css='button.toggle', previous_btn_css='button.previous', no_data_css='div.error-text', data_css='div.chart-container.HOURLY.electricity-chart', download_btn_css='button.download-usage-excel')

# finish
browser.driver.quit()
