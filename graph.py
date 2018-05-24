from parse import parse_to_df

import matplotlib.pyplot as plt
import matplotlib.dates as dates
import pandas as pd
import numpy as np

def main():
	tr, cap, stat = parse_to_df("../af-flawed-stats", "1", "em1")
	#tr, cap, stat = parse_to_df("../pf-sample-stats")
	broctl(tr,stat)
	statslog(tr,stat)
	#ifconf(tr,stat)
	capture_loss(tr,cap)

def capture_loss(tr, cap):
	fig, ax1 = plt.subplots()

	fig.suptitle("Utilization, capture_loss percent_lost vs time")

	color = 'tab:red'

	x1 = dates.date2num(tr.ts)
	y1 = tr.utilization
	
	ax1.plot_date(x1, y1, fmt="-", color=color)
	ax1.set_ylabel("em1 utilization, GB/s", color=color)
	ax1.tick_params(axis='y', labelcolor=color)
	

	ax2 = ax1.twinx()
	color = 'tab:blue'

	x2 = dates.date2num(cap.ts)
	y2 = cap.percent_lost / 100
	
	ax2.plot_date(x2, y2, fmt="-", color=color)
	ax2.set_ylabel("capture_loss percent_loss", color=color)
	ax2.tick_params(axis="y", labelcolor=color)
	ax2.set_ylim(0, 1)

	ax1.set_xlim([x2[0], x2[-1]])

	plt.savefig("capture_loss.png")
def ifconf(tr, stat):
	fig, ax1 = plt.subplots()

	fig.suptitle("Utilization, ifconfig drop_rate vs time")

	color = 'tab:red'
	
	
	x1 = dates.date2num(tr.ts)
	y1 = tr.utilization
	
	ax1.plot_date(x1, y1, fmt="-", color=color)
	ax1.set_ylabel("em1 utilization, GB/s", color=color)
	ax1.tick_params(axis='y', labelcolor=color)
	

	ax2 = ax1.twinx()
	color = 'tab:blue'

	x2 = x1
	y2 = tr.ifconfig_drop_rate
	
	ax2.plot_date(x2, y2, fmt="-", color=color)
	ax2.set_ylabel("ifconfig drop_rate", color=color)
	ax2.tick_params(axis="y", labelcolor=color)
	ax2.set_ylim(0, 1)

	lim = dates.date2num(stat.ts)
	ax1.set_xlim([lim[0], lim[-1]])

	plt.savefig("ifconfig_drop.png")

def broctl(tr, stat):
	fig, ax1 = plt.subplots()

	fig.suptitle("Utilization, Broctl packetLoss vs time")

	color = 'tab:red'
	
	
	x1 = dates.date2num(tr.ts)
	y1 = tr.utilization
	
	ax1.plot_date(x1, y1, fmt="-", color=color)
	ax1.set_ylabel("em1 utilization, GB/s", color=color)
	ax1.tick_params(axis='y', labelcolor=color)
	

	ax2 = ax1.twinx()
	color = 'tab:blue'


	tr = tr[tr.packetLoss >= 0]
	netstats_loss = tr.packetLoss.apply(pd.to_numeric, errors="coerce")

	x2 = dates.date2num(tr.ts)
	y2 = netstats_loss

	ax2.plot_date(x2, y2, fmt="-", color=color)
	ax2.set_ylabel("broctl packetLoss", color=color)
	ax2.tick_params(axis="y", labelcolor=color)
	ax2.set_ylim(0, 1)

	lim = dates.date2num(stat.ts)
	ax1.set_xlim([lim[0], lim[-1]])

	plt.savefig("broctl_packetLoss.png")


def statslog(tr, stat):
	fig, ax1 = plt.subplots()

	fig.suptitle("Utilization, Stat.log drop rate vs time")

	color = 'tab:red'
	
	x1 = dates.date2num(tr.ts)
	y1 = tr.utilization
	
	ax1.plot_date(x1, y1, fmt="-", color=color)
	ax1.set_ylabel("em1 utilization, GB/s", color=color)
	ax1.tick_params(axis='y', labelcolor=color)
	

	ax2 = ax1.twinx()
	color = 'tab:blue'

	x2 = dates.date2num(stat.ts)
	y2 = stat.pkts_dropped / (stat.pkts_dropped + stat.pkts_proc)

	#y2 = test_series(len(stat))

	print("num nan: {}".format(y2.isnull().values.sum()))

	if y2.isnull().values.any():
		fmt = "_"
	else:
		fmt = "-"

	ax2.plot_date(x2, y2, fmt=fmt, color=color)
	ax2.set_ylabel("stats.log drop rate", color=color)
	ax2.tick_params(axis="y", labelcolor=color)
	ax2.set_ylim(0, 1)

	ax1.set_xlim([x2[0], x2[-1]])

	plt.savefig("statslog_pkts_dropped.png")

def test_series(le):
	"""
	make a test series with lots of NaN values
	to test graphing this type of series
	"""
	x = pd.Series()
	for i in range(le):
		if i % 10 in [7,8,9,6]:
			x.set_value(i, np.nan)
		else:
			x.set_value(i, 0)
	return x

if __name__ == "__main__":
	main()