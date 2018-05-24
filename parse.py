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
    capture_loss_df = merge_logs(capture_loss_files)
    # convert datetimes to unix epochs
    #capture_loss_df.ts = capture_loss_df.ts.map(lambda x: x.timestamp())
    capture_loss_df.drop('ts_delta', axis=1, inplace=True)
    # read in bro stats files
    stats_files = glob.glob('{}/*stats*log'.format(logs_dir))
    stats_df = merge_logs(stats_files)
    # convert datetimes to unix epochs
    #stats_df.ts = stats_df.ts.map(lambda x: x.timestamp())
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
    # if you want to convert traffic_stats_df ts to datetime instead of unix timestamps:
    traffic_stats_df.ts = traffic_stats_df.ts.apply(datetime.datetime.fromtimestamp)

    # return objs
    return traffic_stats_df, capture_loss_df, stats_df

def merge_logs(files_list):
    """
    files_list: list of strings
    Merge a list of logs files into one dataframe
    """
    files_list.sort()
    # create LogToDataFrame from each log file
    # reset index will change the dataframe from being indexed by a datetime, to have the datetime as a column in it, 
    #  and indexed just by a int in a range

    # it may be incorrect to run reset_index here, it results in a dataframe that has indices like 
    #  [0, 1, ..., 23, 0, 1, .. 23, 0, 1, ..., 23] if there are 3 log files being merged and each log file has 24 entries
    #  it works for what we for simple things, but it may cause an error later
    bat_dfs = [LogToDataFrame(f).reset_index(level=0) for f in files_list]
    ######### WEIRD BUG ##############
    # We can't just concat all the LogToDataFrame's together, it gives a weird error
    # so we round about turn the LogToDataFrame's into normal DataFrame's then concat those
    #################################
    dfs = [pd.DataFrame(d.to_dict()) for d in bat_dfs]
    cat = pd.concat(dfs)
    return cat

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
