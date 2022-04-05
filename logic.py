import logging
import database

class Logic:
    "Operaciones para el bloqueo de direcciones IP a partir de la base de datos"

    def __init__(self, db: database.DB, ruta_blockips_conf: str) -> bool:
        """Recibe como parámetro la base de datos (previamente abierta) 
        y la ruta del fichero de bloqueo, que se actualiza aquí en base
        a los datos de la tabla blocked."""

        logging.info("Abriendo módulo de lógica...")
        self.db = db
        self.rbc = ruta_blockips_conf
        self.start_time = db.start_time
        self.ex = db.con.execute        ## Abreviatura de la función ----
        self.cursor = db.con.cursor()   ## Objeto cursor ----
        self.commit = db.con.commit     ## Abreviatura de la función ----

    ## TODO: eliminar este bloqueo por código HTTP y sustituirlo por URLs maliciosas
    def bloquear_4xx(self, start_time=None):
        logging.info("IPs con statuscode 4xx")
        if not start_time:
            start_time = self.start_time
        rs = self.ex("""
            SELECT ipaddress, MAX(url) AS url, DATE(MAX(dateandtime)) AS date 
            FROM access 
            -- WHERE statuscode IN (400, 403, 404, 499) AND dateandtime > ?
            WHERE url LIKE '%wp-admin%' 
                OR url LIKE '/.env%' 
                OR url = '/boaform/admin/formLogin'
                OR url LIKE '/config/getuser%'
                OR url LIKE '/wp-login.php'
                OR url LIKE '/phpmyAdmin%'
            GROUP BY ipaddress
            ORDER BY date
        """, (start_time,))
        lista_ips = rs.fetchall()
        ## Suprimo esta salida por el exceso de salida en el log
        #for r in lista_ips:
        #    logging.info("%s con URL tipo %s", r[0], r[1])
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
            if x[0].startswith('31.4.') or x[0].startswith('77.211.'):
                continue

            s += "deny " + x[0].rjust(15) + "; ## " + x[2] + " - " + x[1][:80] + ("..." if len(x[1]) > 80 else "") + '\n'

        ## He preferido recrear el fichero cada vez ----
        with open(self.rbc, "r") as fp:
            s_old = fp.read()
        if s != s_old:
            open(self.rbc, "w").write(s)
            logging.info("Fichero blockips.conf actualizado")
            return True
        else:
            logging.info("Fichero blockips.conf no tuvo cambios")
            return False
