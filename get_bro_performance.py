# -*- coding: utf-8 -*-
"""
Created on Sat Mar 24 13:54:16 2018

@author: babraham, jxm
"""

import json, os, paramiko, re, sys, time

import datetime as dt   
from log_parser import parse_log
import matplotlib.dates as md    
import matplotlib.pyplot as plt
import numpy as np    
import pandas as pd
from scp import SCPClient  
from ShellHandler import *

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
    cdt = dt.datetime.fromtimestamp(time.time())
    datestr = '-'.join([str(cdt.year),str(cdt.month),str(cdt.day-1)])
    cur_date = '-'.join([str(cdt.year),str(cdt.month),str(cdt.day)])
    sh = ShellHandler(server, user, password)
    sh.execute('touch --date "{}" /tmp/start'.format(datestr))
    sh.execute('cd {}'.format(bro_dir))
    stats_cmd = 'find -type f -newer /tmp/start -name "*stats*"'
    _,stat_files,_ = sh.execute(stats_cmd)
    folder = "./tmp_{}".format(cur_date)
    cap_loss_cmd = 'find -type f -newer /tmp/start -name "*capture_loss*"'
    _,cl_files,_ = sh.execute(cap_loss_cmd)
    all_files = cl_files + stat_files
    all_files = [bro_dir +f[1:].strip() for f in all_files if '.log' in f]
    all_files = [re.sub('\:', '\:', f) for f in all_files]
    #add dates to filenames if necessary to prevent duplicate issue
    dates = [re.findall('''([0-9]{4}-[0-9]{2}-[0-9]{2})\/''',l)[0] for l in all_files]
    new_files = []
    for date, f in zip(dates,all_files):
        if date[2:] not in f:
            fsplit = re.split('[0-9]{4}-[0-9]{2}-[0-9]{2}\/',f)
            fsplit[0] += date + '/'
            fsplit[1] = date[2:]+'_'+fsplit[1]
            new_files.append(''.join(fsplit))
        else:
            new_files.append(f)
        
    mv_cmd = ';'.join(['mv {} {}'.format(old,new) for old,new in zip(all_files,new_files) if old != new ])
    if len(mv_cmd) > 0: sh.execute(mv_cmd)       
    fnames = ' '.join(new_files)
    #copy all relevant logs into tmp folder
    sh.execute('mkdir {}'.format(folder))
    sh.execute('cp {} {}'.format(fnames, folder))
    traffic_stats_filename = '/trafficStats_v{}_{}.txt'.format(version_number, device)
    traffic_stats_path = '/home/bea3ch/shared/trafficAnalysis' + traffic_stats_filename
    sh.execute('cp {} {}'.format(traffic_stats_path,folder))
    # compress tmp folder into a tarball and copy to local
    sh.execute('tar -cvf tarball.tar {}'.format(folder))
    sh.scp.get(r'{}/tarball.tar'.format(bro_dir), r'./')
    # remove tmp folder and tarball on server
    sh.execute('rm -rf {} tarball.tar'.format(folder))    
    # unzip local tarball to get tmp folder
    os.system('tar -xvf ./tarball.tar')
    local_files = os.listdir('{}'.format(folder))
    # remove local tarball
    os.system('rm ./tarball.tar')
    # unzip any remaining gz files in tmp folder
    [os.system('gunzip {}'.format('/'.join([folder,f]))) for f in local_files if '.gz' in f]
    # remove any remaining .gz files
    os.system('rm {}/*.gz'.format(folder))
    df = pd.read_csv(folder + traffic_stats_filename, usecols=xrange(len(traffic_stats_headers)), index_col=False)
    unique_traffic_stats_timestamps.update(df.ts.unique())
    # rename [cpu0 -> cpu00], [cpu1 -> cpu01], ..., [cpu9 -> cpu09]
    rename_keys = {}
    for i in xrange(10):
        rename_keys['cpu' + str(i)] = 'cpu0' + str(i)
    df = df.rename(columns=rename_keys)
    # return objs
    return sh, df

def build_dfs(dire='.', device="em2", join_key="minute"):
    assert(join_key in ['minute','hour','day'])
    files = os.listdir(dire)
    #make lists of capture loss and stat files
    statfiles, capfiles = [],[]
    for f in files:
        if f.endswith('.log'):
            if 'stats' in f: statfiles.append(f)
            elif 'cap' in f: capfiles.append(f)
    # create stat dataframe from stat list
    df_stats = build_df_from_list(statfiles, dire)
    # create stat dataframe from capture loss list
    df_cl = build_df_from_list(capfiles, dire)
    # get trafficStats
    df_dev = pd.read_csv(dire+'/trafficStats_v'+version_number+'_'+device+'.txt', index_col=False)
    if 'time' in df_dev.columns: df_dev = add_datetime(df_dev)
    df_dev = add_hashes(df_dev)
    df_comb = df_stats.set_index(join_key).join(df_cl.set_index(join_key),rsuffix="cl")
    df_comb = df_comb.join(df_dev.set_index(join_key),rsuffix="_dev")
    df_comb = df_comb.join(df_dev,rsuffix="_dev")
    return df_stats,df_cl,df_dev
    #return df_comb

def build_df_from_list(flist,dire='.'):
    df_comb = parse_log('/'.join([dire,flist[0]]))
    for i,s in enumerate(flist[1:]):
        try:
            df_new = parse_log('/'.join([dire,s]))
            df_comb = pd.concat([df_comb,df_new])
        except: 
            print('error merging stat df {}'.format(i))
    df_comb = df_comb.reset_index(drop=True)
    df_comb = add_hashes(df_comb)
    return df_comb

def add_datetime(df):
    if 'time' in df.columns:
        df = df.rename(columns={'time':'ts'})
        df['ts'] = df['ts'].apply(lambda x: dt.datetime.fromtimestamp(x))
    return df

def add_hashes(df):
    df['day'] = df['ts'].apply(lambda x: (x.year-1970)*365 +\
           x.month*30 + x.day)
    df['hour'] = df.apply(lambda row: row['day']*24 + row['ts'].hour, axis=1)
    df['minute'] = df.apply(lambda row: row['hour']*60 +\
           row['ts'].minute, axis=1)
    return df

def createSSHClient(server, port, user, password):
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(server, port, user, password)
    return client

_seconds_per_minute = 60
def pull_minutes_of_data(minutes=60, sample_rate=None):
    sys.stdout.write('test')
    # pandas settings
    pd.set_option('display.float_format', lambda x: '%.3f' % x)
    # get data from ivy
    username, password = config['username'], config['password']
    shellHandler, data = pull_data(username, password)
    # trim data to last [minutes]
    interval_in_seconds = minutes * _seconds_per_minute
    current_unix_time = time.time()
    interval_ago_unix_time = current_unix_time - interval_in_seconds
    time_span_data = data[data.ts >= interval_ago_unix_time]
    # sample data, if specified
    if sample_rate:
        print 'sampling'
        time_span_data = time_span_data.sample(frac=sample_rate)
    # convert to json with nice null values
    json_data = json.dumps(time_span_data.to_dict('index'))
    json_data_clean = json_data.replace('NaN', '""')
    #
    print 'time_span_data shape', time_span_data.shape
    #
    return shellHandler, json_data_clean

