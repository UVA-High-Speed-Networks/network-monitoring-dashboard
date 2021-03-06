# -*- coding: utf-8 -*-
"""
Created on Wed Mar 14 18:14:17 2018

@author: babraham, jxmorris12
"""

import subprocess
import re
import pandas as pd
import time
import math
import os
import sys
import datetime


def capOutput(cmd):
    try: 
        output = subprocess.Popen(cmd, stdout=subprocess.PIPE ).communicate()[0]
        return output
    except Exception as e: 
        print("couldn't run command", e)
        return None

def getPacketLoss(waitTime=10):
    cmd = ['broctl', 'netstats']
    plDict = { k: None for k in ['packetLoss','packetRateBro', 'cumPacketLoss'] }
    try:
        ti = time.time()
        startOuptut = capOutput(cmd)
        di = parseNetstatOutput(startOuptut)
        endOutput = capOutput(cmd)
        dt = time.time()- ti
        time.sleep(waitTime)
        df = parseNetstatOutput(endOutput)
        total = df.total.sum() - di.total.sum()
        lost = df.dropped.sum() - di.dropped.sum()
        plDict['packetLoss'] = float(lost) / float(total)
        plDict['cumPacketLoss'] = float(df.dropped.sum()) / (df.dropped.sum() + df.total.sum())
        plDict['packetRateBro'] = total  / float(dt)
        print('lost: {}, total: {}'.format(lost,total))
    except: print "error getting packet loss of bro workers."
    return plDict
    
def parseNetstatOutput(output):
    rx = re.findall('recvd=([0-9]+)', output)
    dropped = re.findall('dropped=([0-9]+)', output)
    total = re.findall('link=([0-9]+)', output)
    df = pd.DataFrame(zip(rx,dropped,total), columns=['received','dropped','total'])
    df = df.apply(pd.to_numeric, axis=0)
    return df
    
def parseProcOutput(output, device = "em1"):
    lines = output.split("\n")
    for i,l in enumerate(lines):
        if device.lower() in l:
            stats = re.findall(' [0-9]+', l)
            byts = int(stats[0].strip())
            pkts = int(stats[1].strip())
            return {'device':device,'bytes':byts, 'packets':pkts}
    return None

###Changed throughput to Utilization###
def getUtilization(waitTime = 10, device="em1", units="Gbps"):
    cmd = ['cat', '/proc/net/dev']
    utilDict = {k:None for k in ['device', 'utilization', 'packetRate', 'packetSize']}
    try:
        startOutput = capOutput(cmd)
        startDict = parseProcOutput(startOutput, device)      
        time.sleep(waitTime)
        endOutput = capOutput(cmd)
        endDict = parseProcOutput(endOutput, device)
        totalbytes = int(endDict['bytes'] - startDict['bytes'])
        if units.lower() == "gbps": thruput = totalbytes * 8 / math.pow(10,9)
        utilDict['device'] = device
        utilDict['utilization'] = thruput / waitTime
        totPkts = int(endDict['packets'] - startDict['packets'])
        utilDict['packetSize'] = totalbytes / totPkts
        utilDict['packetRate'] = totPkts / waitTime
        print('Utilization: {} Gbps'.format(utilDict['utilization']))
    except: print('error getting utilization.')
    return utilDict

def parseStatOutput(output):
    res = re.findall('cpu.*?\n',output)
    res = [r.strip().split(' ') for r in res]
    names = [r[0] for r in res]
    if 'cpu' in names:
        cpu_idx = names.index('cpu')
        res[cpu_idx].remove('')
        res[cpu_idx][0] = 'cpu_all'      
    res = [[float(n) for n in r[1:]] for r in res]
    return names, res

def getCPU(waitTime=5):
    cpuDict = {'cpu'+str(i):None for i in range(0,24)}
    cpuDict['cpu'] = None
    cmd = ['cat', '/proc/stat']
    res1 = capOutput(cmd)
    names, stats1 = parseStatOutput(res1)
    time.sleep(waitTime)
    res2 = capOutput(cmd)
    names, stats2 = parseStatOutput(res2)
    for i,(cpu,s1,s2) in enumerate(zip(names,stats1,stats2)):
        try:
            idle_diff = float(s2[3] - s1[3])
            total_diff = float(sum(s2[1:6]) - sum(s1[1:6]))
            util = 1- idle_diff / total_diff
            cpuDict[cpu] = util
        except:
            print('error calculating cpu usage for cpu {}'.format(cpu))
            print('idle diff: {}, total diff: {}'.format(idle_diff,total_diff))
    return dict(cpuDict)

def getMemUsage():
    output = capOutput(['free'])
    nums = re.findall('[0-9]+',output)
    return float(nums[1])/float(nums[0])

def getIfconfigPacketDrops():
    ifconfig_output = capOutput(['ifconfig', 'em2']).split('\n')
    output_line_with_drops = ifconfig_output[4]
    output_tokens = [x for x in output_line_with_drops.split(' ') if len(x) > 0]
    packet_loss_ct = int(output_tokens[4])
    return packet_loss_ct

# totalTime: The time interfal at which all stts are calculated. i.e. the 
# cumulative time it takes to run the script
def getAllStats(totalTime, device="em1", units = "Gbps", printTs = False):
    if totalTime < 30:
        print('totalTime is too short. For best results, sample at 30 seconds or more')
        sys.exit(0)
    waitTime = float(totalTime - 5.77) / 2.5  # see regression equation below. 
    startTime = time.time()
    pLossDict = getPacketLoss(waitTime)
    if printTs: print ('ploss time: {}'.format(time.time() - startTime))
    ct = time.time()
    thruputDict = getUtilization(waitTime, device, units)
    if printTs: print ('throughput time: {}'.format(time.time() - ct))
    ct = time.time()
    ifconfig_drops_1 = getIfconfigPacketDrops()
    get_cpu_wait_time = waitTime / 2
    cpu_dict = getCPU(get_cpu_wait_time)
    ifconfig_drops_2 = getIfconfigPacketDrops()
    ifconfig_packet_drop_rate = (ifconfig_drops_2 - ifconfig_drops_1) / float(get_cpu_wait_time)
    resDict = {k:v for k,v in thruputDict.items()}
    if printTs: print ('cpu time: {}'.format(time.time() - ct))
    for k,v in pLossDict.items(): resDict[k] = v
    for k,v in cpu_dict.items(): resDict[k] = v  
    resDict['mem_usage'] = getMemUsage()     
    resDict['ifconfig_drop_rate'] = ifconfig_packet_drop_rate
    if printTs: print('total time: {}'.format(time.time()- startTime))
    return resDict   

# =============================================================================
#Regression equation: totalTime = 2.5*waitTime + 5.77 (time to run netstats)
# # waitTime, totalTime
#      5          18.1
#      6          21
#      7          23  
#      8          26.13
#      9          28
#     10,        31.14
#      11         33    
# =============================================================================
def monitor(device,fname=None,totalTime=30,maxTime=None, hasBro=True):
    ti = time.time()
    tf,dt = 0,0
    if not fname: fname = 'trafficStats_v2_{}.txt'.format(device.lower())
    if not maxTime: maxTime = 60 * 60 * 24 * 21 # 21 days in seconds
    if device and totalTime:
        while dt < maxTime:
            if hasBro: res = getAllStats(totalTime, device)
            else: res = getUtilization(totalTime, device)
            res['ts'] = time.time()
            for k in res.keys(): res[k] = str(res[k])
            res = sorted(res.items(), key=lambda x:x[0])
            if os.path.isfile(fname):
                out = open(fname, 'a')
            else:
                out = open(fname, 'w')
                out.write(','.join([r[0] for r in res])+'\n')
            out.write(','.join([r[1] for r in res])+'\n')
            out.close()
            tf = time.time()
            dt += tf - ti
            ti = tf
    else:
        print('error parsing arguments')
        sys.exit(1)

def main():
    try:
        waitTime = int(sys.argv[1])
        device = sys.argv[2]
        hasBro=True
        if device == "em1":  hasBro=False
        fname = 'trafficStats_v1_{}.txt'.format(device)
    except:
        print("""usage: netstats.py --waitTime (secs) --device \n\nexample: netstats.py 10 em1""")
        sys.exit(1)        
    monitor(device, fname,waitTime,None,hasBro)
        
if __name__ == '__main__':
   main()
#  


          
test = """
cpu  721438593 12391128 87794678 31807433600 5081858 0 10279678 0 0 0
cpu0 24478817 607118 4348887 1261397893 3650964 0 8094909 0 0 0
cpu1 51701651 322793 6019246 1303138746 376937 0 98092 0 0 0
cpu2 59869892 319732 6256548 1294532386 82798 0 88321 0 0 0
cpu3 60322041 313199 5526065 1294813050 74173 0 83715 0 0 0
cpu4 57461280 326395 5317550 1297981049 60751 0 82691 0 0 0
cpu5 56633447 290500 5153691 1299130854 69713 0 82410 0 0 0
cpu6 57605769 311312 5291612 1297979710 64473 0 81561 0 0 0
cpu7 57060066 303720 5152027 1298699328 52723 0 81468 0 0 0
cpu8 61155703 303997 5346863 1294295247 51310 0 84232 0 0 0
cpu9 60470039 293826 5302396 1294920334 61727 0 83190 0 0 0
cpu10 60349928 311154 5332700 1295106733 68242 0 82930 0 0 0
cpu11 52587560 1559461 5748451 1301864731 63492 0 232270 0 0 0
cpu12 13336031 1153389 2678998 1346341826 83933 0 107121 0 0 0
cpu13 3735781 626665 2390127 1356999208 30478 0 153138 0 0 0
cpu14 3456937 514405 1994356 1357861254 24352 0 108707 0 0 0
cpu15 3440013 536187 2124562 1357721231 31710 0 106732 0 0 0
cpu16 2986820 461216 1713616 1358498087 57070 0 78595 0 0 0
cpu17 3237062 535881 1958313 1358105734 28489 0 96591 0 0 0
cpu18 3369589 514312 1803562 1358173277 19922 0 84306 0 0 0
cpu19 3549778 463745 1800787 1358042397 20280 0 84833 0 0 0
cpu20 3170317 532727 1687825 1358480002 19311 0 77741 0 0 0
cpu21 3339694 487115 1738036 1358276442 36767 0 84697 0 0 0
cpu22 3372593 438781 1698389 1358339441 31767 0 83222 0 0 0
cpu23 14747775 863486 1410063 1346734628 20466 0 38194 0 0 0
intr 42530130019 127 0 0 0 0 0 0 0 1 0 1049867384 0 0 0 0 0 0 0 69219427 0 0 0 0 0 0 0 0 0 0 0 0 0 0 13191224 1848798 0 2 0 2 2 2 2 2 2 2 1 79824619 11830297 12505557 15492801 14400800 14923175 12603242 16334930 1 47676359 16031758 15562722 11354665 11875781 12661880 13650420 16954414 3439497940 0 2280097507 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
ctxt 375732950197
btime 1508280417
processes 21544588
procs_running 1
procs_blocked 0
softirq 26895216304 11 1229516596 10726619 1480282521 15596547 0 144214145 1033786896 0 1506256489
""" 