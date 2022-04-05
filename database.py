import sqlite3
import datetime
import logging

RUTA_DB = "/home/clouding/blockips/blockips.db"

sql1 = """
CREATE TABLE IF NOT EXISTS access (
    ipaddress text,
    user text,
    dateandtime datetime,
    method text,
    url text,
    statuscode integer,
    bytessent integer,
    referer text,
    useragent text,
    encoded integer,
    PRIMARY KEY (ipaddress, dateandtime, method, url)
)
"""

sql2 = """
CREATE TABLE IF NOT EXISTS blocked (
    ipaddress text PRIMARY KEY,
    url text,
    date datetime
)
"""

sql1insert = """
INSERT OR REPLACE INTO access 
VALUES (:ipaddress, :user, :dateandtime, :method, :url, :statuscode, :bytessent, :referer, :useragent, :encoded)
"""

sql2insert = """
INSERT OR REPLACE INTO blocked
VALUES (:ipaddress, :url, :date)
"""

def apachelog2dt(t):
    "Convierte una fecha de log '07/Sep/2020:06:52:03 +0000' en datetime descontando el offset"
    offset = int(t[-5:])
    delta = datetime.timedelta(hours = offset / 100)
    fmt = "%d/%b/%Y:%H:%M:%S"
    dt1 = datetime.datetime.strptime(t[:-6], fmt)
    dt1 -= delta
    return dt1

class DB:
    "Operaciones DE INSERCION DE REGISTROS con la base de datos de accesos y bloqueos"

    def __init__(self, database=RUTA_DB):
        "Abre la base de datos y crea las tablas access y blocked, si no existen"

        logging.info("Abriendo base de datos %s...", database)
        self.con = sqlite3.connect(database)
        self.con.execute(sql1)
        self.con.execute(sql2)
        self.con.commit()

        ## Esta variable servirá para consultar los registros de hoy ----
        self.start_time = datetime.date.today()

        logging.info("Base de datos abierta")

    def insert_log(self, lista_accesos):
        "Procesa la lista de diccionarios, insertando cada uno en un registro de la base de datos"

        logging.info("Insertando diccionario de accesos en base de datos...")
        num_good = 0
        for reg in lista_accesos:
            try:
                reg['ilin']        = int(reg['ilin'])
                ## reg['ipaddress']   = reg['ipaddress']
                ## reg['user'] 
                reg['dateandtime'] = apachelog2dt(reg['dateandtime'])
                reg['statuscode'] = int(reg['statuscode'])
                reg['bytessent']   = int(reg['bytessent'])

                if 'encoded' in reg.keys():
                    reg['method'] ='----'
                    reg['url'] = reg['encoded'][:20] + '...'
                    reg['encoded'] = True
                else:
                    reg['encoded'] = False
                    #reg['method'] =''      ## Ya viene bien y no hay que modificarlo
                    #reg['url'] = ''

                self.con.execute(sql1insert, reg)
                self.con.commit()
                num_good += 1

            except Exception as e:
                logging.error("Registro erróneo")
                logging.info(reg)
                logging.error("Información del error")
                logging.info(repr(e))

        logging.info("Registrados %s accesos", num_good)

    def insert_block(self, lista_ips):
        "Procesa una lista de ips para bloquear"

        logging.info("Insertando lista de ips a bloquear en la base de datos...")
        #lista_con_fecha = list(zip(lista_ips, str(datetime.date.today()*len(lista_ips))))
        self.con.executemany(sql2insert, lista_ips)
        self.con.commit()

    def clear_access(self):
        "Borrado de access. En principio, solo durante el desarrollo"
        self.con.execute("DELETE FROM access")
        self.con.commit()


if __name__ == "__main__":
    db = DB("blockips.db")
    print(apachelog2dt('07/Sep/2020:06:52:03 +0000'))
    