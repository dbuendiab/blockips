# -*- coding: utf-8 -*-

""" Utilidad de línea de comandos para comprobar el tráfico de la web nolo.be
    En modo standalone, hay que cargar el entorno virtual con 

    pyenv activate envws

    estando con el usuario root en el directorio /home/clouding/blockips.

    El uso interactivo recomendado es

    from main import *
    sql = app.sql
    menu = app.menu


    """

import logging
import sqlite3
import re
import glob
import os.path
import time
import datetime
import gzip
import prettytable

## Gestión del menú interactivo (basado en el fichero menu.yaml) ----
import menu

DIAS_FILTRO = 7
RUTA_LOG_FILES = "/var/log/nginx/access.log*"
RUTA_BLOCKIPS_CONF = "/etc/nginx/conf.d/blockips.conf"

class Setup:
    """ Esta clase descarga los ficheros de logs de DIAS_FILTRO días y los analiza,
        convirtiéndolos en registros de una base de datos Sqlite3 creada en memoria.
        Actualmente falta, entre otras cosas:

        * Guardar el fichero blockips.conf en la tabla blocked (ver notebook en portátil)
        * Añadir un mecanismo más ágil para las consultas (¿leerlas de un fichero de texto?)
        * Añadir facilidades de edición: historial de comandos, edición multilínea, guardado
          de consultas al fichero de texto
        * Actualización del fichero blockips.conf a partir de la tabla blocked actual
        * TODO: Un preprocesador de consultas SQL para escribir menos (SELECT *- agent, refe ...)

        Atributos públicos
        lineas: int = Número de líneas adquiridas correctamente
        info: list = Lista de errores

        Funciones públicas
        sql(frase, datos={}, param="tabla"): Ejecutor de consultas SQL
        menu(): Menú interactivo
        """

    ## Comando para la inserción de registros de log en la tabla access ---- 
    __sql_insert = '''
        INSERT INTO access 
        VALUES (:ipaddress, :user, :dateandtime, :method, :url, :statuscode, :bytessent, :referer, :useragent, :encoded)
        '''

    ## Crea la base de datos y carga los datos de los archivos de log en la tabla ----
    def __init__(self):
        logging.basicConfig(level=logging.DEBUG, filename="main.log", 
            format='%(asctime)s  %(levelname)s: %(message)s')
        logging.info("==========================================================")
        logging.info("------------------- INICIO SESIÓN ------------------------")
        logging.info("==========================================================")
        self.__create_database()
        self.__set_patterns()
        self.__tratamiento_ficheros()
        self.__set_pattern_blockips_conf()
        self.__carga_blockips_conf()

## ------------------------------------------------------------------
    def __create_database(self):
        """ Construye las tablas de la base de datos y guarda los atributos
            self.__conexion y self.__cursor, que se usarán luego para insertar
            registros y hacer consultas.
        """
        logging.info("Creando base de detos...")
        types = {
            'ipaddress': 'text',
            'user': 'text',
            'dateandtime': 'datetime',
            'method': 'text',
            'url': 'text',
            'statuscode': 'integer',
            'bytessent': 'integer',
            'referer': 'text',
            'useragent': 'text',
            'encoded': 'integer'
        }

        ## Tabla access ----
        sql = "CREATE TABLE access ("
        for key in ('ipaddress', 'user', 'dateandtime', 'method', 'url', 'statuscode', 'bytessent', 'referer', 'useragent', 'encoded'):
            sql += '\n' + key + ' ' + types[key] + ','
        sql = sql[:-1]
        sql += ')'

        ## Tabla blocked ----
        sql2 = "CREATE TABLE blocked (ipaddress text PRIMARY KEY)"

        ## Creación propiamente dicha ----
        con = sqlite3.connect(':memory:')
        cur = con.cursor()
        con.execute(sql)
        con.execute(sql2)
        con.commit()

        ## Creación de los atributos (privados) de acceso a la B.D. ----
        self.__conexion = con
        self.__cursor = cur

## ------------------------------------------------------------------
    def __set_patterns(self):
        """ Crea dos patrones de línea, uno para las líneas comunes y otro para
            lo que son líneas codificadas (que vienen con SSL, aunque yo no tenga
            habilitado el https). El tercer patrón, comentado, era para las líneas
            que vienen con el campo user, que dan error con estos patrones. Como no
            voy a guardar ese campo para un caso poco frecuente, dejo que sigan 
            entrando como errores.
            """
        logging.info("Estableciendo patrones regex...")
        patron1 = r"""
            (?P<ipaddress>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})    ## Una dirección IP
            \ -\ -\                                              ## Tres espacios con guiones intercalados
            \[(?P<dateandtime>.+)\]\                             ## Fecha [dd/mes/yyyy:hh:mm:ss +zzzz]
            ((\"(?P<method>\w+)\ )                               ## GET, POST, CONNECT, HEAD. Con espacio al final
            (?P<url>.*)\ (http\/[12]\.[01]"))\                   ## Una URL (cualquier cosa) y el HTTP/1.1 o 2.0. Un espacio
                                                                 ## En mi opinión, antes de HTTP vendría un espacio (igual se lo come el .+)
            (?P<statuscode>\d{3})\                               ## Status code, tres dígitos. Espacio
            (?P<bytessent>\d+)\                                  ## Bytes enviados, dígitos en general. Espacio
            (["](?P<referer>(\-)|(.+))["])\                      ## Referer "lo que sea" o "-"
            (["](?P<useragent>.+)["])                            ## User agent "lo que sea"
            """
        patron2 = r"""
            (?P<ipaddress>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})    ## Una dirección IP
            \ -\ -\                                              ## Tres espacios con guiones intercalados
            \[(?P<dateandtime>.+)\]\                             ## Fecha [dd/mes/yyyy:hh:mm:ss +zzzz]
            ((["](?P<encoded>.*?))["])\                          ## Caso en que no hay method+url
                                                                 ## puede ser un encoded o también ""
            (?P<statuscode>\d{3})\                               ## Status code, tres dígitos. Espacio
            (?P<bytessent>\d+)\                                  ## Bytes enviados, dígitos en general. Espacio
            (["](?P<referer>(\-)|(.+))["])\                      ## Referer "lo que sea" o "-"
            (["](?P<useragent>.+)["])                            ## User agent "lo que sea"
            """
        patron3 = r"""
            (?P<ipaddress>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})    ## Una dirección IP
            \ -\ (?P<user>.+)\                                   ## Tres espacios con guión y usuario
            \[(?P<dateandtime>.+)\]\                             ## Fecha [dd/mes/yyyy:hh:mm:ss +zzzz]
            ((["](?P<encoded>.*?))["])\                          ## Caso en que no hay method+url
                                                                 ## puede ser un encoded o también ""
            (?P<statuscode>\d{3})\                               ## Status code, tres dígitos. Espacio
            (?P<bytessent>\d+)\                                  ## Bytes enviados, dígitos en general. Espacio
            (["](?P<referer>(\-)|(.+))["])\                      ## Referer "lo que sea" o "-"
            (["](?P<useragent>.+)["])                            ## User agent "lo que sea"
            """
        
        ## Función interna para compilar patrones. Sólo se usa aquí, por eso la hago interna ----
        def __create_pattern(regex_str):
            return re.compile(regex_str, re.IGNORECASE | re.VERBOSE)

        ## Los atributos que se usarán en el tratamiento de líneas se guardan aquí ----
        self.__patron1 = __create_pattern(patron1)
        self.__patron2 = __create_pattern(patron2)
        self.__patron3 = __create_pattern(patron3)

## ------------------------------------------------------------------
    def __tratamiento_ficheros(self):
        """ Función que selecciona los ficheros de log, los procesa uno a uno
            y para cada uno hace también el procesado de las líneas, usando para
            ello un par de patrones regex. De esta función cuelgan las cuatro 
            siguientes (__get_log_files, __get_file_lines, __tratamiento_linea, 
            __insert_line), de tal manera que podrían estar incluidas como 
            funciones internas de esta.
            """
        ## ------------------------------------------------------------------
        def __get_log_files(dias_filtro: int, ruta: str):
            """ Esta función filtra los ficheros de log en función de su fecha.
            Para ello, en vez de un bucle, usa la función de orden superior
            map(), pasándole una función interna de filtro que es la que calcula
            los días de cada fichero.
            """ 
            ahora = datetime.datetime.now()
            log_files = glob.glob(ruta)

            ## Función interna a __get_log_files ----
            def func_filtro(file):
                file_time_modif = datetime.datetime.fromtimestamp((os.path.getmtime(file)))
                elapsed_days = (ahora - file_time_modif).days
                return elapsed_days <= dias_filtro
            
            ## Aquí se usa la función que acabamos de crear ----
            return filter(func_filtro, log_files)
        ## ··································································
        ## ------------------------------------------------------------------
        def __get_file_lines(f: str) -> list:
            """ Es un iterador que devuelve una línea cada vez.
                Resuelve el tema de los ficheros comprimidos
                """
            if f.endswith(".gz"):
                with gzip.open(f,'rt') as f:
                    for line in f:
                        yield line
            else:
                with open(f, 'rt') as f:
                    for line in f:
                        yield line 
        ## ··································································
        ## ------------------------------------------------------------------
        def __tratamiento_linea(i: int, L: str) -> 'tuple(dict, list)':
            """ Para cada línea, hace la captura de campos vía patrones regex
                y devuelve un diccionario con todos ellos y una lista de líneas
                erróneas.
                """
            match1 = self.__patron1.search(L)
            match2 = self.__patron2.search(L)
            match3 = self.__patron3.search(L)
            output = {}
            output['ilin'] = i
            output['linea'] = L
            errores = []
            keys_bad = []
            hay_error = False
            for key in ('ipaddress', 'dateandtime', 'method', 'url', 'statuscode', 'bytessent', 'referer', 'useragent'):
                try:
                    output[key] = match1.group(key)
                except AttributeError as _:
                    hay_error = True
                    keys_bad.append(key)
            if hay_error:
                hay_error = False
                for key in ('ipaddress', 'dateandtime', 'encoded', 'statuscode', 'bytessent', 'referer', 'useragent'):
                    try:
                        output[key] = match2.group(key)
                    except AttributeError as _:
                        hay_error = True
                        keys_bad.append(key)
            if hay_error:
                hay_error = False
                for key in ('ipaddress', 'user', 'dateandtime', 'method', 'url', 'statuscode', 'bytessent', 'referer', 'useragent'):
                    try:
                        output[key] = match3.group(key)
                    except AttributeError as _:
                        hay_error = True
                        keys_bad.append(key)

            if hay_error:
                errores.append((L, list(set(keys_bad))))  ## Eliminar duplicados en lista bad keys en main.log
            return output, errores
        ## ··································································
        ## ------------------------------------------------------------------
        def __insert_line(reg: dict):
            """Inserta el diccionario de campos obtenido de una línea
                dentro de la tabla access, adaptando algunos campos
                para su mejor procesamiento
                """

            ## Función interna a __insert_line ----
            ## Observa que no lleva self (no es atributo del objeto)
            ## ni los "dunder" (el doble subrayado, por lo mismo: el 
            ## doble subrayado+self se sustituye internamente por un nombre
            ## autogenerado: _Setup__apachelog2dt)
            ## NOTA POSTERIOR: El doble subrayado funciona, si no hay self por medio
            ## Lo dejo ahí porque me ayuda a visualizar que son funciones privadas ----
            def __apachelog2dt(t):
                import datetime
                offset = int(t[-5:])
                delta = datetime.timedelta(hours = offset / 100)
                fmt = "%d/%b/%Y:%H:%M:%S"
                dt1 = datetime.datetime.strptime(t[:-6], fmt)
                dt1 -= delta
                return dt1

            ## ATENCIÓN: ESTO NO PUEDE EJECUTARSE DOS VECES SEGUIDAS SIN RECREAR acc_lines ANTES
            ## PUESTO QUE EN EL PROCESO RETOCAMOS LOS DICCIONARIOS DE ESA LISTA Y LA SEGUNDA VEZ
            ## YA NO RECONOCE EL CONTENIDO. SI QUIERES QUE SEA REPLICABLE, CREA UNA LISTA DE SALIDA NUEVA

            try:
                reg['ilin']        = int(reg['ilin'])
                reg['dateandtime'] = __apachelog2dt(reg['dateandtime'])
                reg['bytessent']   = int(reg['bytessent'])
                reg['statuscode'] = int(reg['statuscode'])

                if 'user' not in reg.keys():
                    reg['user'] ='-'

                if 'encoded' in reg.keys():
                    reg['method'] ='----'
                    reg['url'] = reg['encoded'][:20] + '...'
                    reg['encoded'] = True
                else:
                    reg['encoded'] = False
                    #reg['method'] =''      ## Ya viene bien y no hay que modificarlo
                    #reg['url'] = ''

                self.__cursor.execute(self.__sql_insert, reg)
                self.__conexion.commit()
            ## Este error es cuando hay una línea errónea y falla un campo. No debe abortar ----
            except KeyError as e:
                logging.error(repr(e))

            ## El resto de errores si son de morirse (creo) ----
            except Exception as e:
                ## TODO: Esto debe dejar un aviso en el menú interactivo (y salir)
                logging.error(repr(e))
                # raise e ## ¿Servirá esto?
        ## ··································································
        ## ··································································
        ## ··································································

        logging.info("Recuperando ficheros de log...")
        self.lineas = 0
        self.info = []
        ## Aquí usamos __get_log_files ----
        for f in __get_log_files(DIAS_FILTRO, RUTA_LOG_FILES):
            countf = 0
            count_err = 0
            logging.info(f"Fichero: {f}")
            ## Aquí usamos __get_file_lines ----
            for i, l in enumerate(__get_file_lines(f)):
                ## Aquí el __tratamiento_linea ----
                dicci, lista = __tratamiento_linea(i, l)
                ## La lista viene si hay errores en la línea ----
                if lista: 
                    count_err += 1
                    logging.error("Línea mal formada")
                    for error in lista:
                        logging.error(error)
                ## Aquí la inserción __insert_line ----
                __insert_line(dicci)
                self.lineas += 1
                countf += 1
            self.info.append({ 'fichero': f, 'filas': self.lineas, 'errores': count_err})
            logging.info(f"{countf} líneas en fichero {f}")
        logging.info(f"Total líneas: {self.lineas}")

## ------------------------------------------------------------------
## ------------------------------------------------------------------
    def __set_pattern_blockips_conf(self):
        self.__pattern_blockips_conf = re.compile(r'\s+')

## ------------------------------------------------------------------
## ------------------------------------------------------------------
    def __carga_blockips_conf(self):
        """ Función para recuperar el contenido del fichero de IPs bloqueadas
            /etc/nginx/conf.d/blockips.conf 
            TODO: un mecanismo de lectura de la fecha de la última actualización
            para impedir la recarga si no ha habido cambios en el fichero
            TODO: lo mismo para los ficheros de log
            """
        logging.info("Recuperando fichero blockips.conf...")
        with open(RUTA_BLOCKIPS_CONF, "r") as fp:
            lineas = fp.readlines()

        blocked_ips = [
            self.__pattern_blockips_conf.split(L)[1].replace(';','') 
            for L in lineas 
            if L.startswith('deny')
        ]
        
        ## Es posible que alguna IP esté repetida, así que uso set() para eliminarla y luego vuelvo a la list() ----
        blocked_ips = list(set(blocked_ips))
        logging.info("Encontradas {} IPs en blockips.conf".format(len(blocked_ips)))
        
        ## Vaciado de la tabla ----
        sql_delete = "DELETE FROM blocked"
        self.__cursor.execute(sql_delete)
        self.__conexion.commit()

        ## Insertar las IPs nuevas ---
        sql_insert_block = '''

        INSERT INTO blocked 
        VALUES (?)

        '''
        contador = 0
        for bip in blocked_ips:
            try:
                self.__cursor.execute(sql_insert_block, (bip,))
                self.__conexion.commit()
                contador += 1
            except Exception as e:
                logging.error(f"Error insertando IP {bip} en tabla 'blocked': {e}")
        logging.info("Insertadas {} IPs".format(contador))

## ------------------------------------------------------------------
## ------------------------------------------------------------------
    ## TODO: habilitar una forma de introducir el parámetro "data",
    ## aunque esto solo sería de utilidad si las frases SQL fueran
    ## consultas parametrizables ----
    def sql(self, cell: str, data: dict= {}, line: str="tabla"):
        """ Utilidad para ejecutar comandos SQL. Obtenida de una
            magic cell del notebook, aquí los parámetros están 
            invertidos (cell, line) y, en principio, no tiene sentido
            su uso devolviendo un recordset, ya que el plan es que 
            esta herramienta sea interactiva
            """
        
        parametros = line.split(' ')
        imprime = 'tabla' in parametros
        leftalign = 'lalign' in parametros
    
        if data:
            self.__cursor.execute(cell, data)
        else:
            self.__cursor.execute(cell)
        if self.__cursor:
            if imprime:
                x = prettytable.from_db_cursor(self.__cursor)
                if leftalign:
                    for fld in x.field_names:
                        x.align[fld] = 'l'
                print(x)
            else:
                return self.__cursor.fetchall()

## ------------------------------------------------------------------
## ------------------------------------------------------------------
    ## Menú interactivo:
    ## * Se genera a partir de un fichero YAML
    ## * Se recargue en cada iteración (así se actualizar sobre la marcha)
    def menu(self):
        main_menu = menu.Menu()

        while True:
            self.__carga_blockips_conf()
            main_menu.recargar_yaml()
            main_menu.display()
            opcion = main_menu.entrada()

            if opcion == '.quit': 
                break
            else:
                frase, data = opcion
                try:
                    self.sql(frase, data)
                except Exception as e:
                    error = f"Error en SQL: {e}"
                    print(error)
                    logging.error(error)
    
## ------------------------------------------------------------------

## La aplicación se ejecuta siempre, ya sea via import o en standalone
## Posiblemente estaría bien hacer 
##
## from main import *
## sql = app.sql
## menu = app.menu
## 
## para usar los dos comando cómodamente en el menú interactivo
app = Setup()

if __name__ == "__main__":
    app.menu()