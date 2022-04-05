import logging
import re

patrones = [
    ## Línea normal (method-url)
r"""
(?P<ipaddress>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})    ## Una dirección IP
\ -\ (?P<user>.+)\                                   ## Tres espacios con guión y usuario (opcional: normalmente un guión)
\[(?P<dateandtime>.+)\]\                             ## Fecha [dd/mes/yyyy:hh:mm:ss +zzzz]
((\"(?P<method>\w+)\ )                               ## GET, POST, CONNECT, HEAD. Con espacio al final
(?P<url>.*)\ (http\/[12]\.[01]"))\                   ## Una URL (cualquier cosa) y el HTTP/1.1 o 2.0. Un espacio
                                                     ## En mi opinión, antes de HTTP vendría un espacio (igual se lo come el .+)
(?P<statuscode>\d{3})\                               ## Status code, tres dígitos. Espacio
(?P<bytessent>\d+)\                                  ## Bytes enviados, dígitos en general. Espacio
(["](?P<referer>(\-)|(.+))["])\                      ## Referer "lo que sea" o "-"
(["](?P<useragent>.+)["])                            ## User agent "lo que sea"

""",
    ## Línea ENCODED
r"""
(?P<ipaddress>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})    ## Una dirección IP
\ -\ (?P<user>.+)\                                   ## Tres espacios con guión y usuario (opcional: normalmente un guión)
\[(?P<dateandtime>.+)\]\                             ## Fecha [dd/mes/yyyy:hh:mm:ss +zzzz]
((["](?P<encoded>.*?))["])\                          ## Caso en que no hay method+url
                                                     ## puede ser un encoded o también ""
(?P<statuscode>\d{3})\                               ## Status code, tres dígitos. Espacio
(?P<bytessent>\d+)\                                  ## Bytes enviados, dígitos en general. Espacio
(["](?P<referer>(\-)|(.+))["])\                      ## Referer "lo que sea" o "-"
(["](?P<useragent>.+)["])                            ## User agent "lo que sea"

"""
]

RUTA_ACCESS_LOG = "/var/log/nginx/access.log"

class ParseLog():
    "Toma el fichero access.log y lo convierte en una lista de diccionarios"

    def __init__(self, log_file=RUTA_ACCESS_LOG):
        "Realiza todo el proceso. Parámetro opcional: la ruta del fichero de log"

        ## Registrar los patrones de línea ----
        logging.info("Registrando patrones...")
        self.regexs = []
        for patron in patrones:
            self.regexs.append(re.compile(patron, re.IGNORECASE | re.VERBOSE))
        logging.info("Patrones registrados: %s", len(patrones))

        ## Recoger las líneas del fichero de log ----
        logging.info("Leyendo fichero %s...", log_file)
        f_lines = open(log_file, "r").read().splitlines()
        logging.info("Recuperadas %s líneas", len(f_lines))

        ## Esto sería mejor si fuera una excepción ----
        assert len(f_lines) > 0, "No había líneas en " + log_file

        ## Procesar las líneas y crear diccionario de entradas ----
        logging.info("Generando lista de diccionarios...")
        self.acc_lines = []
        self.err_data = []
        for i, L in enumerate(f_lines):
            dicc, errores = self.parse_linea(i, L)
            self.acc_lines.append(dicc)
            if errores:
                self.err_data.append(errores)
        self.acc_lines = tuple(self.acc_lines)
        self.err_data = tuple(self.err_data)      
        logging.info("Generada lista de diccionarios (acc_lines) con %s entradas", len(self.acc_lines))
        if self.err_data:
            logging.warning("Encontrados %s errores (err_data)", len(self.err_data))
        else:
            logging.info("No encontrados errores")


    def parse_linea(self, i, L):
        "Función auxiliar para convertir una línea de log en un diccionario"

        ## Podría ser un bucle para cada patrón, pero tendría que escribir otra función específica
        ## y la lógica de ambos patrones es ligeramente distinta, depende el uno del otro.
        ## Por eso lo dejo como estaba originalmente, sabiendo que a más patrones quizás haya que 
        ## hacerlo de otra manera ----
        match1 = self.regexs[0].search(L)
        match2 = self.regexs[1].search(L)
        diccionario = {}
        diccionario['ilin'] = i
        diccionario['linea'] = L
        errores = []
        keys_bad = []
        hay_error = False
        for key in ('ipaddress', 'user', 'dateandtime', 'method', 'url', 'statuscode', 'bytessent', 'referer', 'useragent'):
            try:
                diccionario[key] = match1.group(key)
            except AttributeError:
                hay_error = True
                keys_bad.append(key)
        if hay_error:
            hay_error = False
            for key in ('ipaddress', 'user', 'dateandtime', 'encoded', 'statuscode', 'bytessent', 'referer', 'useragent'):
                try:
                    diccionario[key] = match2.group(key)
                except AttributeError:
                    hay_error = True
                    keys_bad.append(key)
        if hay_error:
            errores.append((i, L, keys_bad))
        return diccionario, errores


if __name__ == '__main__':
    f_lines = open(RUTA_ACCESS_LOG, "r").read().splitlines()
    PL = ParseLog()
    for i, linea in enumerate(f_lines):
        diccionario, errores = PL.parse_linea(i, linea)
        print(diccionario.keys())
        print()
        print(diccionario)
        print()
        print(errores)
        print()