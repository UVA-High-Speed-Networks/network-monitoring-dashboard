## Bro Dashboard

### Setup 

To set up the dashboard, use `pip` to install:
- flask
- flask_socketio
- matplotlib
- numpy
- pandas
- scp
- paramiko

(I might be forgetting something, but the console will yell at you.)

To run, first create a configuration file called `config.json` that looks something like this:

```
{
	"username": "your-username",
	"password": "your-password,
	"port": 8080,
	"server": "remote.server.url.edu",
	"version_number": "2",
	"debug": true
}
```

### Screenshot

![screenshot](https://raw.githubusercontent.com/UVA-High-Speed-Networks/network-monitoring-dashboard/master/dashboard-screenshot.png)