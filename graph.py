from parse import parse_to_df, cleanup_df

import matplotlib.pyplot as plt
import matplotlib.dates as dates
import numpy as np
import pandas as pd

def main():
	tr, cap, stat = parse_to_df("../sample-stats")
	broctl(tr,stat)
	statslog(tr,stat)
	ifconf(tr,stat)
	capture_loss(tr,cap)

def capture_loss(tr, cap):
	fig, ax1 = plt.subplots()

	fig.suptitle("Utilization, capture_loss percent_lost vs time")

	color = 'tab:red'

	x1 = dates.epoch2num(tr.ts)
	y1 = tr.utilization
	
	ax1.plot_date(x1, y1, fmt="-", color=color)
	ax1.set_ylabel("utilization", color=color)
	ax1.tick_params(axis='y', labelcolor=color)
	

	ax2 = ax1.twinx()
	color = 'tab:blue'

	x2 = dates.epoch2num(cap.ts)
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
	
	
	x1 = dates.epoch2num(tr.ts)
	y1 = tr.utilization
	
	ax1.plot_date(x1, y1, fmt="-", color=color)
	ax1.set_ylabel("utilization", color=color)
	ax1.tick_params(axis='y', labelcolor=color)
	

	ax2 = ax1.twinx()
	color = 'tab:blue'

	x2 = x1
	y2 = tr.ifconfig_drop_rate
	
	ax2.plot_date(x2, y2, fmt="-", color=color)
	ax2.set_ylabel("ifconfig drop_rate", color=color)
	ax2.tick_params(axis="y", labelcolor=color)
	ax2.set_ylim(0, 1)

	lim = dates.epoch2num(stat.ts)
	ax1.set_xlim([lim[0], lim[-1]])

	plt.savefig("ifconfig_drop.png")

def broctl(tr, stat):
	fig, ax1 = plt.subplots()

	fig.suptitle("Utilization, Broctl packetLoss vs time")

	color = 'tab:red'
	
	
	x1 = dates.epoch2num(tr.ts)
	y1 = tr.utilization
	
	ax1.plot_date(x1, y1, fmt="-", color=color)
	ax1.set_ylabel("utilization", color=color)
	ax1.tick_params(axis='y', labelcolor=color)
	

	ax2 = ax1.twinx()
	color = 'tab:blue'


	tr = tr[tr.packetLoss > 0]
	netstats_loss = tr.packetLoss.apply(pd.to_numeric, errors="coerce")

	x2 = dates.epoch2num(tr.ts)
	y2 = netstats_loss
	
	ax2.plot_date(x2, y2, fmt="-", color=color)
	ax2.set_ylabel("broctl packetLoss", color=color)
	ax2.tick_params(axis="y", labelcolor=color)
	ax2.set_ylim(0, 1)

	lim = dates.epoch2num(stat.ts)
	ax1.set_xlim([lim[0], lim[-1]])

	plt.savefig("broctl_packetLoss.png")


def statslog(tr, stat):
	fig, ax1 = plt.subplots()

	fig.suptitle("Utilization, Stat.log drop rate vs time")

	color = 'tab:red'
	
	x1 = dates.epoch2num(tr.ts)
	y1 = tr.utilization
	
	ax1.plot_date(x1, y1, fmt="-", color=color)
	ax1.set_ylabel("utilization", color=color)
	ax1.tick_params(axis='y', labelcolor=color)
	

	ax2 = ax1.twinx()
	color = 'tab:blue'

	x2 = dates.epoch2num(stat.ts)
	y2 = stat.pkts_dropped / (stat.pkts_dropped + stat.pkts_proc)
	
	ax2.plot_date(x2, y2, fmt="-", color=color)
	ax2.set_ylabel("stats.log drop rate", color=color)
	ax2.tick_params(axis="y", labelcolor=color)
	ax2.set_ylim(0, 1)

	ax1.set_xlim([x2[0], x2[-1]])

	plt.savefig("statslog_pkts_dropped.png")


if __name__ == "__main__":
	main()