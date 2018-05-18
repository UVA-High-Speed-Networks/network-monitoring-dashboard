from display.dashboard.dashboard import app, socketio, config

if __name__ == "__main__":
    # debug = True causes app reload on py file change
    # (instead of restarting Flask)
  app.debug = False
  socketio.run(app, port=config['port'])