# -*- coding: utf-8 -*-
"""
Created on Sat Mar 24 13:54:16 2018

@author: babraham, jxm
"""

import datetime, glob, json, os, paramiko, re, sys, time

from bat.log_to_dataframe import LogToDataFrame

import datetime as dt   
import matplotlib.dates as md    
import matplotlib.pyplot as plt
import numpy as np    
import pandas as pd
from scp import SCPClient  
from ShellHandler import *


pd.set_option('display.max_columns', 500)

# load config file
raw_config = open('config.json').read()
config = json.loads(raw_config)
version_number = config['version_number']

# instantiate global variables
unique_traffic_stats_timestamps = set()
traffic_stats_headers = ['cpu','cpu00','cpu01','cpu10','cpu11','cpu12','cpu13','cpu14','cpu15','cpu16','cpu17','cpu18','cpu19','cpu02','cpu20','cpu21','cpu22','cpu23','cpu03','cpu04','cpu05','cpu06','cpu07','cpu08','cpu09','cumPacketLoss','device','ifconfig_drop_rate','mem_usage','packetLoss','packetRate','packetRateBro','packetSize','ts','utilization']

def follow_traffic_stats(shellHandler, callback, device="em2"):
    # get traffic stats path
    traffic_stats_filename = '/trafficStats_v{}_{}.txt'.format(version_number, device)
    traffic_stats_path = '/home/bea3ch/shared/trafficAnalysis' + traffic_stats_filename
    # follow file being edited on server
    file_tail_cmd = 'tail -n0 -f {}'.format(traffic_stats_path)
    print 'calling execute_and_wait'
    shellHandler.execute_and_wait(file_tail_cmd, lambda line: on_traffstats_line_written(line, callback))

def on_traffstats_line_written(line, callback):
    # confirm line is new
    line_cols = line.split(',')
    if len(line_cols) != 34: 
        return
    ts = line_cols[32]
    if ts in unique_traffic_stats_timestamps:
        return
    unique_traffic_stats_timestamps.add(ts)
    # detected new line
    callback(line_to_traffic_stats_obj(line_cols))

def line_to_traffic_stats_obj(line):
    assert(len(line) == len(traffic_stats_headers))
    _obj = {}
    for _i in xrange(len(traffic_stats_headers)):
        header = traffic_stats_headers[_i]
        _obj[header] = line[_i].strip()
    return _obj

def pull_data(uname, passwd, local_dir="./", device="em2"):
    server = config['server']
    user = uname
    password= passwd
    bro_dir = '/mnt/localraid/bro/logs'
    # 
    cdt = dt.datetime.fromtimestamp(time.time())
    datestr = '-'.join([str(cdt.year),str(cdt.month),str(cdt.day-1)])
    cur_date = '-'.join([str(cdt.year),str(cdt.month),str(cdt.day)])
    sh = ShellHandler(server, user, password)
    # remove local and rmeote tmp folder, if it exists
    tmp_folder = "./tmp_{}".format(cur_date)
    sh.execute('cd {}'.format(bro_dir))
    sh.execute('rm -rf {}'.format(tmp_folder))
    os.system('rm -rf {}'.format(tmp_folder))
    # create new empty tmp folder
    sh.execute('mkdir {}'.format(tmp_folder))
    # find stats and capture_loss files
    sh.execute('touch --date "{}" /tmp/start'.format(datestr))
    stats_cmd = 'find -type f -newer /tmp/start -name "*stats*"'
    _,stat_files,_ = sh.execute(stats_cmd)
    cap_loss_cmd = 'find -type f -newer /tmp/start -name "*capture_loss*"'
    _,cl_files,_ = sh.execute(cap_loss_cmd)
    all_files = cl_files + stat_files
    all_files = [bro_dir +f[1:].strip() for f in all_files if '.log' in f]
    all_files = [re.sub('\:', '\:', f) for f in all_files]
    # add dates to filenames if necessary to uniquely identify hours from different days
    dates = []
    for l in all_files:
        dates += re.findall('''([0-9]{4}-[0-9]{2}-[0-9]{2})\/''',l)
    new_files = []
    for date, f in zip(dates,all_files):
        f_tokens = f.split('/')
        new_filename = tmp_folder + '/' + date + '-' + f_tokens[-1]
        new_files.append(new_filename)
    cp_cmd = ';'.join([' cp {} {}'.format(old,new) for old,new in zip(all_files, new_files)])
    if len(cp_cmd) > 0: 
        sh.execute(cp_cmd)       
    current_files = ['/mnt/localraid/bro/logs/current/capture_loss.log', '/mnt/localraid/bro/logs/current/stats.log']
    for file in current_files:
        print 'cp {} {}'.format(file, tmp_folder)
        sh.execute('cp {} {}'.format(file, tmp_folder))
    traffic_stats_filename = '/trafficStats_v{}_{}.txt'.format(version_number, device)
    traffic_stats_path = '/home/bea3ch/shared/trafficAnalysis' + traffic_stats_filename
    sh.execute('cp {} {}'.format(traffic_stats_path, tmp_folder))
    # compress tmp folder into a tarball and copy to local
    sh.execute('tar -cvf tarball.tar {}'.format(tmp_folder))
    sh.scp.get(r'{}/tarball.tar'.format(bro_dir), r'./')
    # remove tarball on server
    sh.execute('rm -rf {} tarball.tar'.format(tmp_folder))    
    # unzip local tarball to get tmp folder
    os.system('tar -xvf ./tarball.tar')
    local_files = os.listdir('{}'.format(tmp_folder))
    # remove local tarball
    os.system('rm ./tarball.tar')
    # unzip any remaining gz files in tmp folder
    [os.system('gunzip {}'.format('/'.join([tmp_folder,f]))) for f in local_files if '.gz' in f]
    # remove any remaining .gz files
    os.system('rm {}/*.gz'.format(tmp_folder))
    # read in capture loss files
    capture_loss_files = glob.glob('{}/*capture_loss*log'.format(tmp_folder))
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
    stats_files = glob.glob('{}/*stats*log'.format(tmp_folder))
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
    traffic_stats_df = pd.read_csv(tmp_folder + traffic_stats_filename, index_col=False)
    unique_traffic_stats_timestamps.update(traffic_stats_df.ts.unique())
    # rename [cpu0 -> cpu00], [cpu1 -> cpu01], ..., [cpu9 -> cpu09]
    rename_keys = {}
    for i in xrange(10):
        rename_keys['cpu' + str(i)] = 'cpu0' + str(i)
    traffic_stats_df = traffic_stats_df.rename(columns=rename_keys)
    # return objs
    return sh, traffic_stats_df, capture_loss_df, stats_df

def createSSHClient(server, port, user, password):
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(server, port, user, password)
    return client

def data_frame_to_clean_json(df):
    df_json = json.dumps(df.to_dict('index'))
    df_json_clean = df_json.replace('NaN', '""')
    return df_json_clean

_seconds_per_minute = 60
def pull_minutes_of_data(minutes=60, sample_rate=None):
    # pandas settings
    pd.set_option('display.float_format', lambda x: '%.3f' % x)
    # get data from ivy
    username, password = config['username'], config['password']
    shellHandler, traffic_stats_data, capture_loss_data, stats_data = pull_data(username, password)
    # get last interval unix time
    interval_in_seconds = minutes * _seconds_per_minute
    current_unix_time = time.time()
    interval_ago_unix_time = current_unix_time - interval_in_seconds
    # trim to data since last interval
    traffic_stats_data = traffic_stats_data[traffic_stats_data.ts >= interval_ago_unix_time]
    capture_loss_data = capture_loss_data[capture_loss_data.ts >= interval_ago_unix_time]
    stats_data = stats_data[stats_data.ts >= interval_ago_unix_time]
    # sample data, if specified
    if sample_rate:
        print 'sampling'
        traffic_stats_data = traffic_stats_data.sample(frac=sample_rate)
        capture_loss_data = capture_loss_data.sample(frac=sample_rate)
        stats_data = stats_data.sample(frac=sample_rate)
    # convert to json with nice null values
    traffic_stats_json_data_clean = data_frame_to_clean_json(traffic_stats_data)
    capture_loss_json_data_clean = data_frame_to_clean_json(capture_loss_data)
    stats_json_data_clean = data_frame_to_clean_json(stats_data)
    # return objects
    print 'traffic_stats_data shape', traffic_stats_data.shape
    print 'cljdc', capture_loss_json_data_clean
    return shellHandler, traffic_stats_json_data_clean, capture_loss_json_data_clean, stats_json_data_clean

