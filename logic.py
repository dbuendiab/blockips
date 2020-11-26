import logging
import database

class Logic:
    "Operaciones para el bloqueo de direcciones IP a partir de la base de datos"

    def __init__(self, db: database.DB, ruta_blockips_conf):
        "Recibe como parámetro la base de datos (previamente abierta) y ren"
        logging.info("Abriendo módulo de lógica...")
        self.db = db
        self.rbc = ruta_blockips_conf
        self.start_time = db.start_time
        self.ex = db.con.execute        ## Abreviatura de la función ----
        self.cursor = db.con.cursor()   ## Objeto cursor ----
        self.commit = db.con.commit     ## Abreviatura de la función ----

    def bloquear_4xx(self, start_time=None):
        logging.info("IPs con statuscode 4xx")
        if not start_time:
            start_time = self.start_time
        rs = self.ex("""
            SELECT ipaddress, MAX(url) AS url, DATE(MAX(dateandtime)) AS date 
            FROM access 
            WHERE statuscode IN (400, 403, 404, 499) AND dateandtime > ?
            GROUP BY ipaddress
            ORDER BY date
        """, (start_time,))
        lista_ips = rs.fetchall()
        for r in lista_ips:
            logging.info("%s con URL tipo %s", r[0], r[1])
        logging.info("Insertando %s IPs en la tabla blocked...", len(lista_ips))
        self.db.insert_block(lista_ips)
        logging.info("Tabla blocked actualizada")

    def actualizar_blockips_conf(self):
        "Recrea el fichero de bloqueos en función de lo encontrado en el fichero access.log"
        rs = self.ex("SELECT ipaddress, url, date FROM blocked").fetchall()
        logging.info("Actualizando el fichero blockips.conf con %s entradas", len(rs))
        s = ""
        for x in rs:

            ## Parche para evitar que me bloquee la máquina actual (8/11/2020)
            #  (porque he probado una de las URL malas y me ha anotado en la blacklist)
            #  Pasados unos días dejará de tenerme en los logs, pero entretanto cada vez
            #  que se actualiza la lista se jode la marrana.
            if x[0] == '31.4.207.198':
                continue

            s += "deny " + x[0].rjust(15) + "; ## " + x[2] + " - " + x[1][:80] + ("..." if len(x[1]) > 80 else "") + '\n'

        ## He preferido recrear el fichero cada vez ----
        open(self.rbc, "w").write(s)
        logging.info("Fichero blockips.conf actualizado")