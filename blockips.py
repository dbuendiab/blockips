"""
Proyecto de control de acceso a la web mediante seguimiento del fichero access.log
La idea es examinar el fichero cada X minutos (vía crontab: entre 1 y 5 minutos) y
actualizar la lista de IPs bloqueadas en el fichero /etc/nginx/conf.d/blockips.conf

Próxima gran modificación: mecanismo de seguimiento de la fecha de access.log y
blockip.conf. Sólo entrar al proceso si cambió la fecha del access.log, y solo
reiniciar el servidor si cambió el fichero blockip.conf.

El reinicio se hace con un crontab programado para el momento actual
"""
import logging
import os
import sys

import parselog
import database
import logic
import watcher

RUTA_ACCESS_LOG = "/var/log/nginx/access.log"
RUTA_BLOCKIPS_CONF = "/etc/nginx/conf.d/blockips.conf"

RUTA_DB = "/home/clouding/blockips/blockips.db"
RUTA_LOG = "/home/clouding/blockips/blockips.log"

def init_log():
    ## Configuración de logging ----
    logging.basicConfig(filename=RUTA_LOG, 
                        level=logging.INFO, 
                        format='%(asctime)s %(levelname)s:  %(message)s', datefmt='%d/%m/%Y %H:%M:%S')
    logging.info("=" * 80)

PL = None
db = None
L  = None

def init_objects():
    global PL, db, L
    ## Definición global de objetos: vale tanto en import como en ejecución independiente ----
    PL = parselog.ParseLog(RUTA_ACCESS_LOG)
    db = database.DB(RUTA_DB)
    L = logic.Logic(db, RUTA_BLOCKIPS_CONF)

def load_log_data():

    ## Despiezar la linea del fichero de log y guardarla en una base de datos ----
    acc_lines = PL.acc_lines
    #err_data = PL.err_data

    ## Guardar las entradas en una tabla (para comparar con las previas) ----
    db.insert_log(acc_lines)

    ## Una vez guardados los registros, se necesita implementar un módulo de inteligencia
    ## para procesar las entradas, haciendo los distintos procesos y escribiendo en blockips.conf ----
    L.bloquear_4xx('2000-01-01')    ## La fecha es un problema - igual hay que redefinir todo (hacer tablas temporales para comparar antes de insert)
    hay_cambios_en_blockips_conf = L.actualizar_blockips_conf()

    ## Si hubo cambios, reiniciar el servidor ----
    if hay_cambios_en_blockips_conf:
        logging.info("Reiniciando servidor Nginx...")
        os.system("/usr/sbin/nginx -s reload")


    logging.info("Fin de la ejecución")

    ## Por si quiero hacer más operaciones con la DB después de acabar ----
    return db

def s(sql):
    "Visor de consultas (modo interactivo)"
    cursor = L.ex(sql)
    for x in cursor.fetchall():
        print(x)


def salir(s: str):
    logging.info(s)
    sys.exit(0)

if __name__ == '__main__':
    w = watcher.Watcher(RUTA_ACCESS_LOG)
    init_log()
    if not w.hay_cambios():
        salir("Sin cambios en access.log")
    init_objects()
    load_log_data()
else:
    init_objects()
    #s("SELECT COUNT(*) FROM access")
