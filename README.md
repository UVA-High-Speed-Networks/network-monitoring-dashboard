## Bro Dashboard

### Setup 

It is recommended to install the dependencies in a virtual environment so as not to pollute your system wide installation of python

```
mkdir ~/.virtualenvs
virtualenv ~/.virtualenvs/netmon
source ~/.virtualenvs/netmon/bin/activate
pip install -r requirements.txt
```

If you don't want to use `virtualenv` then you can just run the last line:
`pip install -r requirements.txt`

### Graphing
Edit the first line in `main()` in `graph.py` so that the call to `parse_to_df` has the path to the folder containing the logs, and the interface, and netstats version.

Example: the stats.log and capture_loss.log and trafficStats_v3_em1.txt are in a folder called af-week, so the line is:
`tr, cap, stat = parse_to_df("../af-week", "3", "em1")`

If you need to graph multiple days worth of logs, you have to make sure that when their filenames are sorted in lexicographic order, they are also in chronological order. `rename.py` is a temporary solution I came up for this. Ideally it would be done upon transfer from bulwark.

### Dashboard

To run, first create a configuration file called `config.json` that looks something like this:

```
{
	"username": "your-username",
	"password": "your-password",
	"port": 8080,
	"server": "remote.server.url.edu",
	"version_number": "2",
	"debug": true
}
```

### Screenshot

![screenshot](https://raw.githubusercontent.com/UVA-High-Speed-Networks/network-monitoring-dashboard/master/dashboard-screenshot.png)