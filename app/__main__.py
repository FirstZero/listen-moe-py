from threading import Thread
from time import sleep
from PyQt5.Qt import QApplication, QSystemTrayIcon, QMenu, QAction, QIcon, QStyle, QEvent, QThread, pyqtSignal, QWaitCondition, QMutex, QUrl
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent

import sys, websocket, json

class WebStreamPlayer:
    pass

class InfoSocketNotification(QThread):
    def __init__(self, tray_icon):
        QThread.__init__(self);
        self.tray_icon = tray_icon
        self.mutex = QMutex()
    def __del__(self):
        self.wait()


    def _send_ws(self, wsapp, data):
        json_data = json.dumps(data)
        wsapp.send(json_data)

    def _send_pings(self, wsapp, interval=30):
        while True:
            sleep(30)
            print('sent ping')
            msg = { 'op': 9 }
            self._send_ws(wsapp, msg)

    def _on_message(self, wsapp, msg):
            data = json.loads(msg)
            if data['op'] == 0:
                print('0')
                heartbeat = data['d']['heartbeat'] / 1000
                thread = Thread(target=self._send_pings, args=(wsapp, heartbeat))
                thread.daemon = True
                thread.start()
            elif data['op'] == 1:
                print('1')
                self.tray_icon.new_song_notification_sent.emit(data)
    def run(self):
        self.mutex.lock()
        wss = websocket.WebSocketApp('wss://listen.moe/gateway_v2', on_message=self._on_message)
        wss.run_forever()
        self.mutex.unlock()

class TrayIcon(QSystemTrayIcon):
    new_song_notification_sent = pyqtSignal([dict])
    player_state_changed = pyqtSignal()

    def __init__(self, icon, parent=None):
        QSystemTrayIcon.__init__(self, icon, parent)
        self.notificationWaitCondition = QWaitCondition()
        self.player = QMediaPlayer()
        self.notification = InfoSocketNotification(self)
        self.notification.start()
        self.isPlaying = False

        self.player.setMedia(QMediaContent(QUrl('https://listen.moe/fallback')))
        self.player.setVolume(20)
        self.player.play()

        self.menu = QMenu(parent)
        playAction = self.menu.addAction('Play')
        stopAction = self.menu.addAction('Stop')
        exitAction = self.menu.addAction('Exit')
        self.setContextMenu(self.menu)

        playAction.triggered.connect(self.handle_on_play_action_triggered)
        stopAction.triggered.connect(self.handle_on_stop_action_triggered)
        exitAction.triggered.connect(sys.exit)
        self.player_state_changed.connect(self.handle_player_state_changed)
        self.activated.connect(self.handle_on_icon_click)

        self.new_song_notification_sent.connect(self.handle_new_song_notification_sent)

    def handle_player_state_changed(self):
        if self.isPlaying:
            self.player.play()
            self.notificationWaitCondition.wakeAll()
        else:
            self.player.stop()

    def handle_on_play_action_triggered(self):
        self.isPlaying = True
        self.player_state_changed.emit()

    def handle_on_stop_action_triggered(self):
        self.isPlaying = False
        self.player_state_changed.emit()

    def handle_on_icon_click(self, reason):
        if reason == self.Trigger:
            self.isPlaying = not self.isPlaying
            self.player_state_changed.emit()

    def handle_new_song_notification_sent(self, info):
        song_name = info['d']['song']['title']
        artist_name = 'Artist: ' + info['d']['song']['artists'][0]['name']
        #anime_name = '\nAnime: ' + info['anime_name']
        info_body = artist_name;
        #if info['anime_name'] != '': info_body = info_body
        self.showMessage(song_name, info_body, QSystemTrayIcon.Information, 5000)



def main():
    app = QApplication(sys.argv)
    style = app.style()

    icon = QIcon(style.standardPixmap(QStyle.SP_MediaPlay))
    tray_icon = TrayIcon(icon)

    tray_icon.show()
    app.exec_()

if __name__ == '__main__':
    main()
