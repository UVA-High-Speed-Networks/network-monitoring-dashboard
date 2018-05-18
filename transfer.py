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

class TransferData():
    def __init__(self):
        self.config = self.read_config()
        self.sh = ShellHandler(self.config["server"], self.config["username"], self.config["password"])

        cdt = dt.datetime.fromtimestamp(time.time())
        datestr = '-'.join([str(cdt.year),str(cdt.month),str(cdt.day-1)])
        cur_date = '-'.join([str(cdt.year),str(cdt.month),str(cdt.day)])

        self.server_temp_dir = "./tmp_{}".format(cur_date)
        self.local_temp_dir = "./tmp_{}".format(cur_date)

    def read_config(self):
        raw_config = open("config.json").read()
        config = json.loads(raw_config)
        return config

    def consolidate(self, version_number="2", device="em2"):
        """
        Gather the data on the server into one directory that we can compress (so that its easy to copy over scp)
        device: string
        """ 
        # 

        sh = ShellHandler(server, user, password)
        # remove remote tmp folder, if it exists
        sh.execute('cd {}'.format(bro_dir))
        sh.execute('rm -rf {}'.format(self.server_temp_dir))
        # create new empty tmp folder
        sh.execute('mkdir {}'.format(self.server_temp_dir))
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
            new_filename = self.server_temp_dir + '/' + date + '-' + f_tokens[-1]
            new_files.append(new_filename)
        cp_cmd = ';'.join([' cp {} {}'.format(old,new) for old,new in zip(all_files, new_files)])
        if len(cp_cmd) > 0: 
            sh.execute(cp_cmd)       
        current_files = ['/mnt/localraid/bro/logs/current/capture_loss.log', '/mnt/localraid/bro/logs/current/stats.log']
        for file in current_files:
            print 'cp {} {}'.format(file, self.server_temp_dir)
            sh.execute('cp {} {}'.format(file, self.server_temp_dir))
        traffic_stats_filename = '/trafficStats_v{}_{}.txt'.format(version_number, device)
        traffic_stats_path = '/home/bea3ch/shared/trafficAnalysis' + traffic_stats_filename
        sh.execute('cp {} {}'.format(traffic_stats_path, self.server_temp_dir))
        # compress tmp folder into a tarball
        sh.execute('tar -cvf tarball.tar {}'.format(server_temp_dir))

    def transfer(self):
        """
        Transfer the compressed data on the server (that was created in conslidate() ) to the local machine
        and extract all the data
        """
        # remove local temp folder (if it exists, it contains old info)
        os.system('rm -rf {}'.format(self.local_temp_dir))
        sh.scp.get(r'{}/tarball.tar'.format(bro_dir), r'./')
    
        # unzip local tarball to get tmp folder
        os.system('tar -xvf ./tarball.tar')
        local_files = os.listdir('{}'.format(self.local_temp_dir))
    
        # unzip any remaining gz files in tmp folder
        [os.system('gunzip {}'.format('/'.join([self.local_temp_dir,f]))) for f in local_files if '.gz' in f]


    def cleanup(self):
        """
        Clean up temp stuff on server and local
        """
        # remove tarball on server
        sh.execute('rm -rf {} tarball.tar'.format(self.server_temp_dir))    
        # remove local tarball
        os.system('rm ./tarball.tar')
        # remove any remaining .gz files
        os.system('rm {}/*.gz'.format(self.local_temp_dir))
