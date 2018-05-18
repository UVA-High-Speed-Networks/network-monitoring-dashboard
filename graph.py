from parse.parse import parse_to_df, cleanup_df

import matplotlib.pyplot as plt
import matplotlib.dates as dates
import numpy as np
import pandas as pd

def main():
	tr, cap, stat = parse_to_df("../sample-stats")

	
	fig, ax1 = plt.subplots()

	color = 'tab:red'

	tr = tr[tr.packetLoss > 0]
	netstats_loss = tr.packetLoss.apply(pd.to_numeric, errors="coerce")
	
	
	x1 = dates.epoch2num(tr.ts)
	y1 = tr.utilization
	
	ax1.plot_date(x1, y1, fmt="-", color=color)
	ax1.set_ylabel("utilization", color=color)
	ax1.tick_params(axis='y', labelcolor=color)
	

	ax2 = ax1.twinx()
	color = 'tab:blue'

	x2 = dates.epoch2num(stat.ts)
	y2 = stat.pkts_dropped
	
	ax2.plot_date(x2, y2, fmt="-", color=color)
	ax2.set_ylabel("stats.log pkts_dropped", color=color)
	ax2.tick_params(axis="y", labelcolor=color)

	ax1.set_xlim([x2[0], x2[-1]])
	

	plt.show()

if __name__ == "__main__":
	main()