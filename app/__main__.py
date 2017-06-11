import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstBase', '1.0')
from gi.repository import Gst, GstBase, GObject

from PyQt5.Qt import QApplication, QSystemTrayIcon, QMenu, QAction, QIcon, QStyle, QEvent, QThread, pyqtSignal, QWaitCondition, QMutex

import sys, websocket, json

class WebStreamPlayer:
    def __init__(self):
        Gst.init(None)

        self.url = 'https://listen.moe/stream'

        self.player = Gst.ElementFactory.make('playbin', 'player')
        self.player.set_property('uri', self.url)

        self.player.set_state(Gst.State.READY)

    def play(self):
        self.player.set_state(Gst.State.PLAYING)

    def stop(self):
        self.player.set_state(Gst.State.READY)

class InfoSocketNotification(QThread):
    def __init__(self, tray_icon):
        QThread.__init__(self);
        self.tray_icon = tray_icon
        self.mutex = QMutex()
    def __del__(self):
        self.wait()
    def run(self):
        wss = websocket.create_connection('wss://listen.moe/api/v2/socket')
        while True:
            self.mutex.lock()
            if not self.tray_icon.isPlaying: self.tray_icon.notificationWaitCondition.wait(self.mutex)
            data = wss.recv()
            if data != '':
                info = json.loads(data)
                self.tray_icon.new_song_notification_sent.emit(info)
            self.mutex.unlock()

class TrayIcon(QSystemTrayIcon):
    new_song_notification_sent = pyqtSignal([dict])
    player_state_changed = pyqtSignal()

    def __init__(self, icon, parent=None):
        QSystemTrayIcon.__init__(self, icon, parent)
        self.notificationWaitCondition = QWaitCondition()
        self.player = WebStreamPlayer()
        self.notification = InfoSocketNotification(self)
        self.notification.start()
        self.isPlaying = False

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
        song_name = info['song_name']
        artist_name = 'Artist: ' + info['artist_name']
        anime_name = '\nAnime: ' + info['anime_name']
        info_body = artist_name;
        if info['anime_name'] != '': info_body = info_body + anime_name
        self.showMessage(song_name, info_body,QSystemTrayIcon.Information, 5000)



def main():
    app = QApplication(sys.argv)
    style = app.style()

    icon = QIcon(style.standardPixmap(QStyle.SP_MediaPlay))
    tray_icon = TrayIcon(icon)

    tray_icon.show()
    app.exec_()

if __name__ == '__main__':
    main()
