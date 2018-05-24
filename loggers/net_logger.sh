PROG=/mnt/localraid/bro/bin/broctl

NETLOG=net_log.txt
CPULOG=cpu_log.txt
MEMLOG=mem_log.txt

touch $NETLOG
touch $CPULOG
touch $MEMLOG

while [ 1 ]
do
	date >> $NETLOG
	echo "##################" >> $NETLOG
	$PROG netstats >> $NETLOG
	echo "##################" >> $NETLOG
	date >> $NETLOG
	echo "##################" >> $NETLOG
	ifconfig em2 >> $NETLOG
	echo "##################" >> $NETLOG
	
	date >> $CPULOG
	echo "##################" >> $CPULOG
	cat /proc/stat >> $CPULOG
	echo "##################" >> $CPULOG


	date >> $MEMLOG
	echo "##################" >> $MEMLOG
	free >> $MEMLOG	
	echo "##################" >> $MEMLOG

	echo "Sleeping for 30 seconds ... "
	sleep 30
done
