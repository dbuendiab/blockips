"""MENÚ INTERACTIVO 

Features
1 - Entrada multilínea para comandos SQL y single para los numéricos
2 - Inicialización del menú mediante un diccionario o fichero

Enlaces de documentación sobre YAML:

https://pyyaml.org/wiki/PyYAMLDocumentation

Verificador de sintaxis YAML en línea:

http://www.yamllint.com/

"""

## TODO: Montar tests Unittest o algo para probar la entrada y la salida 

class Menu:
    def __init__(self):
        self.recargar_yaml()


    def recargar_yaml(self):
        import yaml  # type: ignore
        with open("menu.yaml", "rt") as fp:
            self.__sql_frases = yaml.safe_load(fp)
        self.__comandos = [str(x['clave']) for x in self.__sql_frases]


    def display(self):
        print()
        print("MENU CONSULTAS")
        print("==============")
        for elem in self.__sql_frases:
            print(str(elem["clave"]) + '. ' + elem["nombre"])
        print("-----------------------------------")
        print("Introduce comando o una frase SQL ", end="")
        self.recargar_yaml()
        

    def entrada(self):
        ## Hacemos la lectura de la primera línea ----
        opcion = input()

        ## Si no escribieron nada, leo las siguientes líneas ----
        if opcion.strip() == '':
            centinela = "" ## Fin de línea input multilínea ----
            sql = "\n".join(iter(input, centinela))
            return (sql, None)

        ## Si es [q]uit abandonamos ----
        if opcion[0] in 'qQ':
            return ".quit"

        ## Si es alguno de los comandos de la lista ----
        if opcion in self.__comandos:
            comando = list(filter(lambda x: x['clave'] == opcion, self.__sql_frases))[0]
            sql = comando['sql']
            params = comando.get('params', None)
            if params:
                params = self.input_param(params)
            return (sql, params)

        ## En todos los demas casos en que escriba algo, se entiende que será una frase SQL ----
        else:
            sql = opcion + "\n"
            centinela = "" ## Fin de línea input multilínea ----
            sql += "\n".join(iter(input, centinela))
            return (sql, None)

    def input_param(self, params: list):
        outp = {}
        for elem in params:
            value = input("Introduce " +elem + ": ")    ## TODO: bucle para validar esta entrada
            outp[elem] = value
        return outp

if __name__ == "__main__":
    x = Menu()
    while True:
        x.display()
        print("ATENCIÓN: Este menú es el de menu.py, no el final")
        opc = x.entrada()
        if opc == ".quit": break
        print(opc)
