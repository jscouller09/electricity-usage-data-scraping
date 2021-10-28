# ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# Name:         Electricity data analysis
# Purpose:      Compile scraped data and do analysis on hourly usage
#
# Author:       james.scouller
#
# Created:      28/10/2021
# ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# global imports
import os
import pandas as pd
from datetime import datetime
# ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# custom module imports
# ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# main code


# working dir
working_dir = os.path.dirname(__file__)
# outputs dir
outputs_dir = os.path.join(working_dir, 'outputs')

# get all files and compile into single pandas df
all_data = pd.DataFrame()
for f in os.listdir(outputs_dir):
    f_path = os.path.join(outputs_dir, f)
    if os.path.isfile(f_path):
        # read csv file
        new_data = pd.read_csv(f_path)
        # convert date col into datetime
        new_data['date'] = new_data['date'].apply(pd.to_datetime)
    all_data = pd.concat([all_data, new_data])

# sort by date
all_data.sort_values('date', inplace=True)
# add date parts
all_data['day'] = all_data['date'].apply(lambda ts: ts.day)
all_data['month'] = all_data['date'].apply(lambda ts: ts.month)
all_data['year'] = all_data['date'].apply(lambda ts: ts.year)
# add column for night 9pm-7am/weekend times
all_data['night'] = all_data['date'].apply(lambda ts: (ts.hour < 7) or (ts.hour >= 21))
all_data['weekend'] = all_data['date'].apply(lambda ts: ts.dayofweek >= 5)
all_data['off-peak'] = all_data['night'] | all_data['weekend']
# add rates
all_data['rate'] = all_data['off-peak'].apply(lambda off_pk: 0.1347 if off_pk else 0.2332)
# convert usage in kWh to number
all_data['usage_kWh'] = all_data['usage'].apply(lambda s: float(s[:-4]))
# sort out usage at different times
all_data['night_kWh'] = 0.0
all_data.loc[all_data['night'], 'night_kWh'] = all_data['usage_kWh'].loc[all_data['night']]
all_data['weekend_kWh'] = 0.0
all_data.loc[all_data['weekend'] & ~all_data['night'], 'weekend_kWh'] = all_data['usage_kWh'].loc[all_data['weekend'] & ~all_data['night']]
all_data['weekday_kWh'] = 0.0
all_data.loc[~all_data['off-peak'], 'weekday_kWh'] = all_data['usage_kWh'].loc[~all_data['off-peak']]
# calc charges per day and per kWh
all_data['usage_charge'] = all_data['rate'] * all_data['usage_kWh']
all_data['daily_charge'] = 0.3450 / 24
all_data['total_charge'] = all_data['usage_charge'] + all_data['daily_charge']
# calc total by day and month
index = ['year', 'month', 'day']
cols = ['usage_kWh', 'usage_charge', 'daily_charge', 'total_charge', 'weekend_kWh', 'night_kWh', 'weekday_kWh']
daily_totals = all_data.pivot_table(cols, index, aggfunc='sum')
mthly_totals = daily_totals.groupby(['year', 'month']).sum()
mthly_totals['days'] = daily_totals.groupby(['year', 'month']).size()
# add percentages
mthly_totals['night_perc'] = 100 * mthly_totals['night_kWh'] / mthly_totals['usage_kWh']
mthly_totals['weekend_perc'] = 100 * mthly_totals['weekend_kWh'] / mthly_totals['usage_kWh']
mthly_totals['weekday_perc'] = 100 * mthly_totals['weekday_kWh'] / mthly_totals['usage_kWh']
mthly_totals['off_peak_perc'] = 100 * (mthly_totals['night_kWh'] + mthly_totals['weekend_kWh']) / mthly_totals['usage_kWh']
# transpose
mthly_totals = mthly_totals.T
# add averages
mthly_totals['avg'] = mthly_totals.mean(axis=1)

mthly_totals.to_csv('mthly_totals.csv')
