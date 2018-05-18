import datetime
import time
import glob
import json
import pandas as pd

from bat.log_to_dataframe import LogToDataFrame


def parse_to_df(logs_dir, version_number="2", device="em2"):
    """
    logs_dir: string - a path to the folder containing all of the logs and statistics transfered from ivy-bulwark
    Parse all the logs in logs_dir into pandas dataframes
    """
    # read in capture loss files
    capture_loss_files = glob.glob('{}/*capture_loss*log'.format(logs_dir))
    capture_loss_files.sort()
    capture_loss_df = LogToDataFrame(capture_loss_files.pop())
    for file in capture_loss_files:
        try:
            capture_loss_df.merge(LogToDataFrame(file))
        except Exception as e: 
            print 'Error loading', file + ':', e
    # reset index and convert datetimes to unix epochs
    capture_loss_df.reset_index(level=0, inplace=True)
    capture_loss_df.ts = capture_loss_df.ts.map(lambda x: (x-datetime.datetime(1970,1,1)).total_seconds())
    capture_loss_df.drop('ts_delta', axis=1, inplace=True)
    # read in bro stats files
    stats_files = glob.glob('{}/*stats*log'.format(logs_dir))
    stats_files.sort()
    stats_df = LogToDataFrame(stats_files.pop())
    for file in stats_files:
        try:
            stats_df.merge(LogToDataFrame(file))
        except Exception as e: 
            print 'Error loading', file + ':', e
    # reset index and convert datetimes to unix epochs
    stats_df.reset_index(level=0, inplace=True)
    stats_df.ts = stats_df.ts.map(lambda x: (x-datetime.datetime(1970,1,1)).total_seconds())
    stats_df.pkt_lag = str(stats_df.pkt_lag)
    print stats_df.head()
    # read in trafficStats csv
    traffic_stats_filename = '/trafficStats_v{}_{}.txt'.format(version_number, device)
    traffic_stats_df = pd.read_csv(logs_dir + traffic_stats_filename, index_col=False)
    # rename [cpu0 -> cpu00], [cpu1 -> cpu01], ..., [cpu9 -> cpu09]
    rename_keys = {}
    for i in xrange(10):
        rename_keys['cpu' + str(i)] = 'cpu0' + str(i)
    traffic_stats_df = traffic_stats_df.rename(columns=rename_keys)
    # return objs
    return traffic_stats_df, capture_loss_df, stats_df

def cleanup_df(df_list, interval, convert_to_json=True, sample_rate=None):
    """
    df_list: list of dataframes to process (from parse_to_df() )
    interval: int - an integer of number of seconds to grab from the data
    sample_rate: float - optional, Fraction of data points to return
    """
    # get last interval unix time
    current_unix_time = time.time()
    interval_ago_unix_time = current_unix_time - interval
    # trim to data since last interval
    df_list = [df[df.ts >= interval_ago_unix_time] for df in df_list]
    # sample data, if specified
    if sample_rate is not None:
        df_list = [df.sample(frac=sample_rate) for df in df_list]
    # convert to json with nice null values
    if convert_to_json:
        df_list = [data_frame_to_clean_json(df) for df in df_list]
    # return objects
    return df_list

def data_frame_to_clean_json(df):
    """
    df: pandas dataframe
    Convert a dataframe to a json string with the string ("") for NaN
    """
    df_json = json.dumps(df.to_dict('index'))
    df_json_clean = df_json.replace('NaN', '""')
    return df_json_clean
