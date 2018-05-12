# -*- coding: utf-8 -*-
"""
@author: babraham, jxmorris12
"""

import subprocess, time

netstats_version = 3
prev_recorded_stats = {}

def cap_output(cmd):
	try: 
	    output = subprocess.Popen(cmd, stdout=subprocess.PIPE ).communicate()[0]
	    return output
	except Exception as e: 
	    print("couldn't run command", e)
	    return None


# gets all all statistics, outputs running averages, 
# and updates prev_recorded_stats
def get_all_stats(out_file):

def monitor(device, time_gap=30):
    ti = time.time()
    tf,dt = 0,0
    if not fname: 
    	fname = 'trafficStats_v{}_{}.txt'.format(netstats_version, device.lower())
  	if os.path.isfile(fname):
      out_file = open(fname, 'a')
    else:
      out_file = open(fname, 'w')
      out_file.write(','.join([r[0] for r in res])+'\n')
  	t = Timer(time_gap, get_all_stats, args = [out_file])
  	t.start()

  	# -- old code (remove!) --
    if device and totalTime:
      res = getAllStats(totalTime, device)
      else: res = getUtilization(totalTime, device)
      res['ts'] = time.time()
      for k in res.keys(): res[k] = str(res[k])
      res = sorted(res.items(), key=lambda x: x[0])
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
    # -- end old code --
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