from parse import parse_to_df

import matplotlib.pyplot as plt
import matplotlib.dates as dates
import pandas as pd
import numpy as np
import datetime

def main():
    tr, cap, stat = parse_to_df("../af-week", "3", "em1")
    four_loss(tr, cap, stat)
    #capture_loss(tr,cap)
    #ifconf(tr,stat)
    #statslog(tr,stat)
    #broctl(tr,stat)

def ifconfig_broctl_drop(tr):
    fig, ax1 = plt.subplots()

    tr = tr[tr.packetLoss >= 0]

    x1 = dates.date2num(tr.ts)

    y1 = tr.utilization
    y2 = tr.ic_drop_rt
    y3 = tr.packetLoss.apply(pd.to_numeric, errors="coerce")

    ax1.plot_date(x1, y1, fmt="-", label="link utilization")
    ax1.set_ylabel("em1 utilization, Gbps")

    ax2 = ax1.twinx()

    ax2.plot_date(x1, y2, fmt="-", label="ifconfig drop rate")
    ax2.plot_date(x1, y3, fmt="-", label="bro drop rate")

    ax2.set_ylim([-.1, 1])
    ax2.legend()
    fig.autofmt_xdate()

    plt.savefig("if_bro_drop.png")

def four_loss(tr, cap, stat):
    fig, ax1 = plt.subplots()

    tr2 = tr[tr.packetLoss >= 0]

    x1 = dates.date2num(tr.ts)
    x2 = dates.date2num(tr2.ts)
    x3 = dates.date2num(cap.ts)
    x4 = dates.date2num(stat.ts)

    y1 = cap.percent_lost / 100

    y2 = tr2.packetLoss.apply(pd.to_numeric, errors="coerce")

    dropped = stat.pkts_dropped
    proc = stat.pkts_proc
    y3 = dropped / (dropped + proc)

    y4 = tr.ic_drop_rt

    fig.suptitle("Loss/drop rates vs time")

    ax1.plot_date(x3, y1, fmt="-", label="capture loss rate")
    ax1.plot_date(x2, y2, fmt="-", label="broctl packetLoss")
    ax1.plot_date(x4, y3, fmt="-", label="stat.log drop rate")
    ax1.plot_date(x1, y4, fmt="-", label="ifconfig drop rate")

    ax1.set_ylabel("Loss/drop rate")

    ax1.legend()

    x_start = dates.date2num(datetime.datetime(2018,5,31,13))
    x_end = dates.date2num(datetime.datetime(2018,5,31,13,30))
    
    ax1.set_xlim([x_start, x_end])
    ax1.set_ylim([0, .1])

    fig.autofmt_xdate()

    plt.savefig("four_loss.png")

def capture_loss(tr,cap):
    fig, ax1 = plt.subplots()

    fig.suptitle("Utilization, capture loss rate vs time")

    color = 'tab:blue'

    x1 = tr.ts

    x1 = dates.date2num(x1)
    y1 = tr.utilization
    
    ax1.plot_date(x1, y1, fmt="-", color=color)
    ax1.set_ylabel("em1 utilization, Gbps", color=color)
    ax1.tick_params(axis='y', labelcolor=color)
    

    ax2 = ax1.twinx()
    color = 'tab:red'

    x2 = cap.ts
    x2 = dates.date2num(x2)

    y2 = cap.percent_lost
    y2 = y2 / 100
    
    ax2.plot_date(x2, y2, fmt="-", color=color)
    ax2.set_ylabel("capture loss rate", color=color)
    ax2.tick_params(axis="y", labelcolor=color)
    ax2.set_ylim(0, 1)

    ax1.set_xlim([x2[0], x2[-1]])

    fig.autofmt_xdate()

    plt.savefig("capture_loss.png")
def ifconf(tr, stat):
    fig, ax1 = plt.subplots()

    fig.suptitle("Utilization, ifconfig drop rate vs time")

    color = 'tab:blue'
    
    
    x1 = dates.date2num(tr.ts)
    y1 = tr.utilization
    
    ax1.plot_date(x1, y1, fmt="-", color=color)
    ax1.set_ylabel("em1 utilization, Gbps", color=color)
    ax1.tick_params(axis='y', labelcolor=color)
    

    ax2 = ax1.twinx()
    color = 'tab:red'

    x2 = x1
    y2 = tr.ic_drop_rt
    
    ax2.plot_date(x2, y2, fmt="-", color=color)
    ax2.set_ylabel("ifconfig drop rate", color=color)
    ax2.tick_params(axis="y", labelcolor=color)
    ax2.set_ylim(0, 1)

    lim = dates.date2num(stat.ts)
    ax1.set_xlim([x2[0], x2[-1]])

    fig.autofmt_xdate()

    plt.savefig("ifconfig_drop.png")

def broctl(tr,stat):
    fig, ax1 = plt.subplots()

    fig.suptitle("Utilization, Broctl packetLoss vs time")

    color = 'tab:red'
    
    x1 = tr.ts

    x1 = dates.date2num(x1)
    y1 = tr.utilization

    
    ax1.plot_date(x1, y1, fmt="-", color=color)
    ax1.set_ylabel("em1 utilization, Gbps", color=color)
    ax1.tick_params(axis='y', labelcolor=color)
    

    ax2 = ax1.twinx()
    color = 'tab:blue'


    tr = tr[tr.packetLoss >= 0]
    netstats_loss1 = tr.packetLoss.apply(pd.to_numeric, errors="coerce")


    x2 = x1
    y2 = netstats_loss1

    ax2.plot_date(x2, y2, fmt="-", color=color)
    ax2.set_ylabel("broctl packetLoss", color=color)
    ax2.tick_params(axis="y", labelcolor=color)
    ax2.set_ylim(0, 1)

    ax1.set_xlim([x2[0], x2[-1]])

    lim = dates.date2num(stat.ts)
    ax1.set_xlim([x2[0], x2[-1]])

    fig.autofmt_xdate()

    plt.savefig("broctl_packetLoss.png")


def statslog(tr,stat):
    fig, ax1 = plt.subplots()

    fig.suptitle("Utilization, Stat.log drop rate vs time")

    color = 'tab:red'
    
    x1 = tr.ts

    x1 = dates.date2num(x1)
    y1 = tr.utilization

    
    ax1.plot_date(x1, y1, fmt="-", color=color)
    ax1.set_ylabel("em1 utilization, Gbps", color=color)
    ax1.tick_params(axis='y', labelcolor=color)
    

    ax2 = ax1.twinx()
    color = 'tab:blue'

    x2 = stat.ts
    x2 = dates.date2num(x2)
    dropped = stat.pkts_dropped
    proc = stat.pkts_proc
    y2 = dropped / (dropped + proc)

    #y2 = test_series(len(stat))

    print("num nan: {}".format(y2.isnull().values.sum()))

    if y2.isnull().values.any():
        fmt = "-"
    else:
        fmt = "-"

    ax2.plot_date(x2, y2, fmt=fmt, color=color)
    ax2.set_ylabel("stats.log drop rate", color=color)
    ax2.tick_params(axis="y", labelcolor=color)
    ax2.set_ylim(0, 1)

    ax1.set_xlim([x2[0], x2[-1]])

    fig.autofmt_xdate()

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