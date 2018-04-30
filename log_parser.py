# -*- coding: utf-8 -*-
"""
Created on Fri Nov 17 13:48:02 2017

@author: babraham
"""
import numpy as np
import pandas as pd
import time
import re
import multiprocessing as mp
from tqdm import tqdm
import os
import pickle
from BroDataConverter import *
#######################Sample Usage#############################
#for small-medium sized files, use parse_log to get dataframe
    #smtp_df = parse_log(smtp.test.log)
#for large files (i.e. conn logs, on order of Gigs), use split_and_parse
    #conn_log = split_and_parse(conn.test.df, n=10) where n = # of splits
####################Notes#######################################
    #1. This class has many dependencies. Make sure to install them w/ pip.
    #2. Make sure that this file is in the same directory as BroDataConverter
#######################Global Variables#########################
bdc = BroDataConverter() #custom class that maps bro data types to python datatypes
#directory where all the bro logs are stored. Normally this is <path-to-bro>/logs
samp_log = "conn.16:00:00-17:00:00.log.gz"
lf = "conn.12:00:00-13:00:00.log"
#os.chdir('/Users/babraham/Downloads/em2_logs_03-25')
#####################################

#splits log into smaller subfiles, reads them in, and combines to make a DF
def split_and_parse(logfile, n=None, l=None, logDir=""):
    assert l or n
    _split(logfile, l,n)
    res_df = parse_log_by_subfile(logfile,logDir)
    return res_df

#reads log's subfiles in and combines them. Assumes subfiles are already made.
def parse_log_by_subfile(logfile, logDir=None, typ=None, export=True):
    if logDir: dire = logDir
    else: dire = '.'
    files = os.listdir(dire)
    fpat = re.sub('\.log', '', logfile)
    subfiles = re.findall('({}_.*?)#'.format(fpat), '#'.join(files))
    subfiles = sorted(subfiles, key=lambda x: int(re.findall('[0-9]+',x)[0]))
    comb_df = parse_log(subfiles[0])
    for subfile in subfiles[1:]:
        sub_df = parse_log(subfile, export=False)
        comb_df = pd.concat([comb_df,sub_df])
    if export:
        fname = re.sub('\.log', '.csv', logfile)
        comb_df.to_csv(fname)
    return comb_df

#Bro log parser that currently supports conn,http,dns,smtp,and ssl    
def parse_log(logfile, outputDir=".", typ=None, export=False):
    global bdc
    #try to infer log type from file name
    if typ: typ = typ.strip().lower()
    else:
        typ = ""
        for t in bdc.fields.keys():
            if t in logfile.lower(): typ = t                   
    with open(logfile, 'r') as f:
        lines = f.readlines()
    #capture field names, data types
    fieldList, broTypes, pyTypes = [],[], []
    for l in lines[1:10]:
        if '#fields' in l: fieldList = l.strip().split('\t')[1:]
        elif '#types' in l: broTypes = l.strip().split('\t')[1:]
    pyTypes = [bdc.type_mapper.get(t,bdc.type_mapper['unknown']) for t in broTypes]
    
    #create a dictionary for field data types
    field_types = dict(zip(fieldList,pyTypes))
    all_fields = {fieldList[i].strip():i for i in range(len(fieldList))}

    #if known log type, only keep important fields. Otherwise, keep all of them.
    try: imp_fields = bdc.fields[typ]
    except: imp_fields = all_fields
    imp_inds = [all_fields[fi] for fi in imp_fields]
    recs = []
    for l in tqdm(lines[8:len(lines)-2]):
        values = l.split('\t')
        for i,(field,val) in enumerate(zip(fieldList,values)):
            if val == '-':
                broTyp = broTypes[i]
                values[i] = bdc.dash_mapper.get(broTyp, '-')
            else:
                mapping = field_types.get(field)
                if callable(mapping): values[i] = mapping(val)
                else: values[i] = mapping   
        values = [values[i] for i in imp_inds] #only include important fields
        rec = dict(zip(imp_fields, values)) 
        if typ == 'conn':
            if rec['proto'] != 'icmp':
                rec['hash'] = ','.join([rec['id.orig_h'],rec['id.resp_h'],rec['id.resp_p'],rec['proto']])
                flags = _parse_history(rec['history'], keys=True)
                rec.update(flags)
        recs.append(rec)
    fieldNames = recs[0].keys()
    print('creating dataframe...')
    df = pd.DataFrame(recs, columns=fieldNames)
    #always call timestamp column ts, not time
    if 'time' in df.columns: 
        df = df.rename(columns={'time':'ts'})
    if export:
        fname = re.sub('\.log', '.csv', logfile)
        df.to_csv(fname)
    return df

def _split(logfile, l=None, n=None, delOld=True, logDir="."):
    assert l or n
    #by default, delete old splits if they exist. Can be set to false w/ delOld.
    if delOld:
        logpat = re.sub('.log','',logfile)
        filestr = "#".join(os.listdir(logDir))
        subfiles = re.findall('({}_.*?)#'.format(logpat),filestr)
        if len(subfiles) > 0:
            rmCmd = 'rm ' + logpat + '_*'
            os.system(rmCmd)
    print('counting lines...')
    with open(logfile, 'r') as f:
        for i,l in enumerate(f): pass
        tot_lines = (i+1)
    if n: sub_lc = tot_lines / n      
    else:
        sub_lc = l
        n = tot_lines / sub_lc
    sub_idx = 0
    subname = re.sub('\.log', '_{}.log'.format(sub_idx),logfile)
    out = open(subname, 'w')
    metadata = []
    with open(logfile, 'r') as f:
        for i,l in enumerate(f):
            if i < 8:
                metadata.append(l)
            if (i+1) % sub_lc == 0 and sub_idx < n:
                out.close()
                sub_idx +=1
                subname = re.sub('\.log', '_{}.log'.format(sub_idx),logfile)
                out = open(subname, 'w')
                out.write(''.join(metadata))
            out.write(l)
            
#####################Trace and Feature Extraction##########################
def getFeatures(date="2018-02-08", startHour="2", log_type = "conn", log_dir = ".", algo="v2", export=False):
    tdict = {"unzip":0, "log_parsing":0, "feature_extraction":0}
    log_dir_path = "/".join([log_dir, date])
    all_logs = os.listdir(log_dir_path)
    if len(startHour) ==1: startHour = "0"+startHour
    logpat = log_type + "." + startHour + ".*?\.log.*?"
    try:
        log_file = re.findall("(" + logpat+")\%", "%".join(all_logs))[0]
    except:
        print("Could not find any results for regex ptn " + logpat)
        return
    #unzip log file if necessary
    os.chdir(log_dir_path)
    if "gz" in log_file:
        ti = time.time()
        print("unzipping file...")
        os.system("gunzip " + log_file)   
        #remove .gz at end of log filename
        log_file = re.sub('\.gz', '', log_file)
        tdict['unzip'] = time.time()-ti
    log_file="samp.log"
    #parse log (assumes conn log for now)
    print("Parsing log...")
    ti = time.time()
    logs = parse_log(log_file )
    tdict['log_parsing'] = time.time()-ti
    
    #create traces and extract features
    ti = time.time()
    if algo=="v2":res = getTraces_serial(lf=log_file, logdata=logs)
    else: res = getTraces_parallel( logdata=logs)
    tdict['feature_extraction'] = time.time()-ti
    
    #export as a csv if necessary
    if export:
        print("exporting file...")
        fname = re.sub('log', 'csv', log_file)
        res.to_csv(fname)
    print("Total time: " + str(time.time()-ti))
    print tdict.items()
    return res           

#optimized feature extraction using pandas dataframes    
def getTraces_serial(lf, logdata = None, fromStr=False, export_file = None):
    global bdc
    ti = time.time()
    if not logdata:
        cols, data = parse_log(lf, fromStr=fromStr)
    else:
        cols, data = logdata[0], logdata[1]
        
    df = pd.DataFrame(data, columns=cols)
    for n in bdc.num_cols:
        df.ix[:,[n]] = df.ix[:,[n]].astype('float64')
    hashes = df.hash.unique()
    recs = list()
    for h in tqdm(hashes):
        rec = dict()
        df_sub = df[(df.hash == h)]
        df_sub = df_sub.sort_values(by='ts')
        df_sub = df_sub.reset_index()
        rec['flow_ct'] = df_sub.shape[0]
        for k in bdc.id_cols: rec[k] = df_sub.ix[0,[k]].values[0]
        for n in bdc.num_cols:
            if n is not 'ts':
                rec['mean_'+n] = df_sub.ix[:,[n]].mean().values[0]
                rec['med_'+n] = df_sub.ix[:,[n]].median().values[0]
                rec['std_'+n] = df_sub.ix[:,[n]].std().values[0]
        rec['ts'] = df_sub.ix[:,['ts']].min().values[0]
        ts1 = df_sub.ix[:,['ts']]
        intvls = np.subtract(ts1[1:], ts1[:-1])
        rec['mean_intvl'] = np.mean(intvls).values[0]
        rec['std_intvl'] = np.std(intvls).values[0]
        for fk in bdc.fkeys:
            rec[fk] = df_sub.ix[:,[fk]].sum().values[0]
        recs.append(rec)
    print "total time: " + str(time.time()-ti) + " secs"    
    df =  pd.DataFrame(recs, columns=recs[0].keys())
    ordered_cols = _get_col_order()
    df = df.ix[:,ordered_cols]
    if export_file is not None:
        if not export_file.endswith('.csv'):export_file +='.csv'
        df.to_csv(export_file)
    return df    
   
def getTraces_parallel(logdata, export_file = None, num_cores = 4):
    print("parsing log file...")
    cols, data = logdata[0], logdata[1]
    df = pd.DataFrame(data, columns=cols)
    for n in bdc.num_cols:
        df.ix[:,[n]] = df.ix[:,[n]].astype('float64')
    print("making hash lists...")
    hashes = df.hash.unique().tolist()
    np.random.shuffle(hashes)
    print "num hashes: " + str(len(hashes))
    #split hashes into 4 equal lists
    hashlists = []
    intvl = len(hashes) / num_cores
    for i in range(num_cores):
        if i == num_cores-1:  sub = hashes[i*intvl:]
        else: sub = hashes[i*intvl:(i+1)*intvl]
        hashlists.append(sub)
    print "Starting pool processes..."
    pool = mp.Pool(processes=num_cores)
    recs = [pool.apply_async(_get_hash_trace, args=(hashlists[i], df)) for i in range(num_cores)]
    recs = [r.get() for r in recs]    
    recs_coll = []
    for c in range(len(recs)):
        recs_coll += recs[c]
    df =  pd.DataFrame(recs_coll, columns=recs_coll[0].keys())
    ordered_cols = _get_col_order()
    df = df.ix[:,ordered_cols]
    if export_file is not None:
        if not export_file.endswith('.csv'):export_file +='.csv'
        df.to_csv(export_file)    
    return df

    
#helper method to get all flows for a certain hash (four-tuple)
def _get_hash_trace(hlist, data):
    print("starting _get_hash_traces()...")
    num_cols = ['resp_bytes', 'duration', 'resp_pkts', 'orig_pkts','ts']
    id_cols = ['id.orig_h', 'id.resp_h', 'id.orig_p', 'id.resp_p', 'proto']
    print "num hashes: " + str(len(hlist))
    recs = []
    for hsh in tqdm(hlist):
        hash_data = data[data['hash']==hsh]
        hash_data = hash_data.reset_index()
        rec = dict()
        rec['flow_ct'] = hash_data.shape[0]
        for k in id_cols: rec[k] = hash_data.ix[0,[k]].values[0]
        for n in num_cols:
            if n is not 'ts':
                rec['mean_'+n] = hash_data.ix[:,[n]].mean().values[0]
                rec['med_'+n] = hash_data.ix[:,[n]].median().values[0]
                rec['std_'+n] = hash_data.ix[:,[n]].std().values[0]
        rec['startTime'] = hash_data.ix[:,['ts']].min().values[0]
        ts1 = hash_data.ix[:,['ts']]
        intvls = np.subtract(ts1[1:], ts1[:-1])
        rec['mean_intvl'] = np.mean(intvls).values[0]
        rec['std_intvl'] = np.std(intvls).values[0]
        rec['ts'] = hash_data.ix[:,['ts']].min().values[0]
        for fk in bdc.fkeys:  rec[fk] = hash_data.ix[:,[fk]].sum().values[0]
        recs.append(rec)
    return recs

#return 
def _get_col_order():
    nc = bdc.num_cols[:-1] + ['intvl']
    startTime = bdc.num_cols[-1]
    flowct = bdc.calc_cols[1]
    mec, mdc, sc = ['mean_'+k for k in nc], ['med_'+k for k in nc], ['std_'+k for k in nc]
    #ADD MDC BACK IN LATER
    tups = zip(mec, sc)
    met_cols = []
    for rec in tups:
        for r in rec: met_cols.append(r)
    #met_cols.remove('med_intvl')
    cm_file = open('/Users/babraham/Desktop/col_mapping.csv','r')
    cm_lines = cm_file.readlines()
    splits = [l.strip().split(',') for l in cm_lines]
    ds_cols = [s[1] for s in splits]
    col_map = {s[1]:s[0] for s in splits}
    final_cols = [col_map[ds_col] for ds_col in ds_cols]
    return final_cols
    
#parses flag history field and returns dictionary of flag counts

work_dir = '/Users/babraham/Box Sync/1-CyberSecurity-Project/BEA-Work'
def _parse_history(hist, keys=False):
    fd = bdc.empty_flags
    for h in hist: fd[h] = 1
    if keys: return fd
    else: return [fd[k] for k in sorted(fd.keys())]
    
def save_obj(obj, name ):
    if name + '.pkl' not in os.listdir('.'):
        os.system("touch " + name + '.pkl')
    with open(name + '.pkl', 'wb') as f:
        pickle.dump(obj, f, protocol = 0)

def load_obj(name ):
    with open(name + '.pkl', 'rb') as f:
        return pickle.load(f)    

