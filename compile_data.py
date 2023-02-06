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

# genesis fixed 1 year energy plus contract rates
daily_chg = (60 / 100) * 1.15
off_peak_chg = (12.85 / 100) * 1.15
peak_chg = (30.51 / 100) * 1.15

# genesis fixed 1 year basic contract rates
# daily_chg = (30 / 100) * 1.15
# off_peak_chg = (12 / 100) * 1.15
# peak_chg = (28 / 100) * 1.15

# new Frank rates
# daily_chg = (60 / 100) * 1.15
# off_peak_chg = (16.50 / 100) * 1.15
# peak_chg = (27.10 / 100) * 1.15

# current Frank rates
# daily_chg = (30 / 100) * 1.15
# off_peak_chg = (11.71 / 100) * 1.15
# peak_chg = (26.73 / 100) * 1.15

# working dir
working_dir = os.path.dirname(__file__)
# outputs dir
outputs_dir = os.path.join(working_dir, 'outputs')

# get all files and compile into single pandas df
print('Compiling data...')
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
start_ts = all_data.date.iloc[0]
end_ts = all_data.date.iloc[-1]
ts_index = pd.date_range(start=start_ts, end=end_ts, freq='H', name='timestamp')
# add date parts
all_data['day'] = all_data['date'].apply(lambda ts: ts.day)
all_data['month'] = all_data['date'].apply(lambda ts: ts.month)
all_data['year'] = all_data['date'].apply(lambda ts: ts.year)
all_data['day_of_year'] = all_data['date'].apply(lambda ts: ts.dayofyear)
# add column for night 9pm-7am/weekend times
all_data['night'] = all_data['date'].apply(lambda ts: (ts.hour < 7) or (ts.hour >= 21))
all_data['weekend'] = all_data['date'].apply(lambda ts: ts.dayofweek >= 5)
all_data['off-peak'] = all_data['night'] | all_data['weekend']
# add rates
all_data['rate'] = all_data['off-peak'].apply(lambda off_pk: off_peak_chg if off_pk else peak_chg)
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
# calculate daily charge based on number of hourly timesteps associated with each day - should be 24, but during daylight savings switchover can be 23 or 25
for i, row in all_data.iterrows():
    num_hrs = all_data.loc[(all_data['day_of_year'] == row['day_of_year']) & (all_data['year'] == row['year'])].shape[0]
    all_data['daily_charge'] = daily_chg / num_hrs
all_data['total_charge'] = all_data['usage_charge'] + all_data['daily_charge']
# add ts index and check for gaps
all_data = pd.DataFrame(index=ts_index).join(all_data.set_index('date'))
missing = all_data.loc[all_data.isna().all(axis=1)]
dups = all_data.loc[all_data.index.duplicated('first') | all_data.index.duplicated('last')]
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

# write output CSV
mthly_totals.to_csv('mthly_totals.csv')
daily_totals.to_csv('daily_totals.csv')
all_data.to_csv('all_data.csv')
print('Wrote compiled data csv files!')

print('Missing data for the following timestamps:')
for ts, data in missing.iterrows():
    print('\t{:%Y-%m-%d %H:%M}'.format(ts))

print('Duplicated data for the following timestamps:')
for ts, data in dups.iterrows():
    print('\t{:%Y-%m-%d %H:%M} | {}'.format(ts, data.usage))

# billing period to check - note billing period will end at the end of the day on the last day
bill_start = pd.to_datetime('20/01/2023', dayfirst=True) + pd.Timedelta(hours=1) # total for first hour of the billing period is at 1am
bill_end = pd.to_datetime('18/02/2023', dayfirst=True) + pd.Timedelta(hours=24) # total for last hour of the billing period is at midnight on the day after
bill_ts = all_data.loc[bill_start:bill_end].index
bill_days = bill_ts[-1] - bill_ts[0]
if bill_days.components.hours == 23:
    # timeseries ends at 23:00 because no subsequent data available
    bill_days += pd.Timedelta(hours=1)
days_bill_period = (bill_end - bill_start + pd.Timedelta(hours=1)).days # add hour because of starting with 1am on first billing day
days_current = bill_days.days
days_remaining_bill_period = days_bill_period - days_current
bill_data = all_data.loc[bill_start:bill_end, cols].sum()
avg_daily_charge = all_data.loc[bill_start:bill_end, ['day_of_year', 'total_charge']].groupby('day_of_year').sum().mean()[0]
# add percentages
bill_data['night_perc'] = 100 * bill_data['night_kWh'] / bill_data['usage_kWh']
bill_data['weekend_perc'] = 100 * bill_data['weekend_kWh'] / bill_data['usage_kWh']
bill_data['weekday_perc'] = 100 * bill_data['weekday_kWh'] / bill_data['usage_kWh']
bill_data['off_peak_perc'] = 100 * (bill_data['night_kWh'] + bill_data['weekend_kWh']) / bill_data['usage_kWh']
print('Over billing period from {:%d/%m/%y %H:%M} to {:%d/%m/%y %H:%M}:'.format(bill_start, bill_end))
print('\t{:8d}/{:2d} days complete'.format(days_current, days_bill_period))
print('\t{:11d} days remaining'.format(days_remaining_bill_period))
print('\t{:10.2f}% night use'.format(bill_data['night_perc']))
print('\t{:10.2f}% weekend use'.format(bill_data['weekend_perc']))
print('\t{:10.2f}% weekday use'.format(bill_data['weekday_perc']))
print('\t{:10.2f}% off-peak use'.format(bill_data['off_peak_perc']))
print('\t{:10.2f}  kWh night use'.format(bill_data['night_kWh']))
print('\t{:10.2f}  kWh weekend use'.format(bill_data['weekend_kWh']))
print('\t{:10.2f}  kWh weekday use'.format(bill_data['weekday_kWh']))
print('\t{:10.2f}  kWh off-peak use'.format(bill_data['night_kWh'] + bill_data['weekend_kWh']))
print('\t{:10.2f}  kWh total use'.format(bill_data['usage_kWh']))
print('\t{:10.2f}  NZD charged'.format(bill_data['total_charge']))
print('\t{:10.2f}  NZD average daily charge over bill period'.format(avg_daily_charge))
print('\t{:10.2f}  NZD estimated total bill'.format(avg_daily_charge*days_remaining_bill_period + bill_data['total_charge']))

print('DONE!')
