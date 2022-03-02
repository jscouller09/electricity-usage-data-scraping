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
# add column for night 9pm-7am/weekend times
all_data['night'] = all_data['date'].apply(lambda ts: (ts.hour < 7) or (ts.hour >= 21))
all_data['weekend'] = all_data['date'].apply(lambda ts: ts.dayofweek >= 5)
all_data['off-peak'] = all_data['night'] | all_data['weekend']
# add rates
all_data['rate'] = all_data['off-peak'].apply(lambda off_pk: 0.1347 if off_pk else 0.3074)
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
# add ts index and check for gaps
all_data = pd.DataFrame(index=ts_index).join(all_data.set_index('date'))
missing = all_data.loc[all_data.isna().all(axis=1)]
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

# billing period to check
bill_start = pd.to_datetime('07/02/2022', dayfirst=True)
bill_end = pd.to_datetime('07/03/2022', dayfirst=True)
bill_ts = all_data.loc[bill_start:bill_end].index
bill_days = bill_ts[-1] - bill_ts[0] + pd.Timedelta(hours=1)
bill_data = all_data.loc[bill_start:bill_end, cols].sum()
# add percentages
bill_data['night_perc'] = 100 * bill_data['night_kWh'] / bill_data['usage_kWh']
bill_data['weekend_perc'] = 100 * bill_data['weekend_kWh'] / bill_data['usage_kWh']
bill_data['weekday_perc'] = 100 * bill_data['weekday_kWh'] / bill_data['usage_kWh']
bill_data['off_peak_perc'] = 100 * (bill_data['night_kWh'] + bill_data['weekend_kWh']) / bill_data['usage_kWh']
print('Over billing period from {:%d/%m/%y} to {:%d/%m/%y}:'.format(bill_start, bill_end))
print('\t{:10d}  days'.format(bill_days.days))
print('\t{:10.2f}% night use'.format(bill_data['night_perc']))
print('\t{:10.2f}% weekend use'.format(bill_data['weekend_perc']))
print('\t{:10.2f}% weekday use'.format(bill_data['weekday_perc']))
print('\t{:10.2f}% off-peak use'.format(bill_data['off_peak_perc']))
print('\t{:10.2f}  kWh night use'.format(bill_data['night_kWh']))
print('\t{:10.2f}  kWh weekend use'.format(bill_data['weekend_kWh']))
print('\t{:10.2f}  kWh weekday use'.format(bill_data['weekday_kWh']))
print('\t{:10.2f}  kWh off-peak use'.format(bill_data['night_kWh'] + bill_data['weekend_kWh']))
print('\t{:10.2f}  kWh total use'.format(bill_data['usage_kWh']))
print('\t{:10.2f}  NZD charge'.format(bill_data['total_charge']))

print('DONE!')
