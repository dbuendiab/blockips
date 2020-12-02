import logging
import os

RUTA_WATCHER = "watch.info"

class Watcher:
    def __init__(self, path_access_log):
        self.path_access_log = path_access_log
        self.fecha_ultima = 0

    def hay_cambios(self) -> bool:
        ## Lee la última hora registrada en el watcher 
        if os.path.exists(RUTA_WATCHER):
            self.fecha_ultima = float(open(RUTA_WATCHER, "r").read())
        ## La fecha actual de access.log
        self.fecha_actual = os.stat(self.path_access_log).st_mtime
        ## Si hay cambios se registran en el watcher y se devuelve el bool
        self.cambios = False
        if self.fecha_actual > self.fecha_ultima:
            self.cambios = True
            open(RUTA_WATCHER,"w").write(str(self.fecha_actual))
        return self.cambios

if __name__ == "__main__":
    import time
    w = Watcher("prueba.txt")
    while True:
        if w.hay_cambios():
            print("Hay cambios!")
        else:
            print("Sin cambios")
        time.sleep(1)
