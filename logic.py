import logging
import database
import datetime

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

    def bloquear_urls(self, days_ago=7):
        '''
        Esta función consulta la tabla access de blockips.db (sqlite) para obtener ips
        que contengan URLs maliciosas, por un lado, e ips con un número alto de errores 
        http 4xx. El número de errores está hardwired a 50 dentro de la consulta SQL, se
        puede extraer como parámetro pero no creo que merezca la pena
        '''
        logging.info("IPs con URLs maliciosas y códigos 4xx")
        ## Una semana por defecto
        start_time = datetime.datetime.today() - datetime.timedelta(days=days_ago)
        if not days_ago:
            start_time = self.start_time

        # Esta es la versión previa de la consulta, que no incluía la parte http
        # Se deja comentada por claridad a la hora de entender los cambios
        '''
        rs = self.ex("""
            SELECT ipaddress, MAX(url) AS url, DATE(MAX(dateandtime)) AS date 
            FROM access 
            WHERE (url LIKE '%wp-admin%' 
                OR url LIKE '/.env%' 
                OR url = '/boaform/admin/formLogin'
                OR url LIKE '/Autodiscover%'
                OR url LIKE '/config/getuser%'
                OR url LIKE '/wp-login.php%'
                OR url LIKE '/phpmyAdmin%')
                 AND dateandtime > ?
            GROUP BY ipaddress
            ORDER BY date
        """, (start_time,))
        '''

        # La nueva consulta incluye la anterior unida a la que cuenta códigos http
        # Podría mejorarse haciendo una UNION sólo de las ipaddress, y en todo caso
        # usar esta lista para obtener los campos url y date (ahora puede darse el
        # caso de tener una ip repetida porque salga en las dos consultas, pero no sé
        # si eso será un problema, creo que no)
        rs = self.ex("""
            SELECT ipaddress, MAX(url) AS url, DATE(MAX(dateandtime)) AS date 
            FROM access 
            WHERE (url LIKE '%wp-admin%' 
                OR url LIKE '/.env%' 
                OR url = '/boaform/admin/formLogin'
                OR url LIKE '/Autodiscover%'
                OR url LIKE '/config/getuser%'
                OR url LIKE '/wp-login.php%'
                OR url LIKE '/phpmyAdmin%'
                     )
                 AND dateandtime > ?
            GROUP BY ipaddress

            UNION

            SELECT ipaddress, MAX(url) AS url, DATE(MAX(dateandtime)) AS date 
            FROM access 
            WHERE dateandtime > ?
            GROUP BY ipaddress
            HAVING SUM(CASE WHEN statuscode >=400 AND statuscode <= 499 THEN 1 ELSE 0 END) > 50

            ORDER BY date
        """, (start_time, start_time,))

        
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
