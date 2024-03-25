# Main.py y Blockips.py

Son dos programas distintos pero que hacen cosas parecidas.

**MAIN** es un programa interactivo que genera una base de datos SQLite en memoria con los logs de los últimos 7 días,
y presenta un menú interactivo de consultas.

Para correr este programa (main.py) hay que activar primero el entorno virtual *envws*

pyenv activate envws

He creado el script *m3* en /root/bin para poder invocarlo directamente según entramos vía SSH.

**BLOCKIPS** es un programa que corre mediante *crontab* (cada minuto) y que monitoriza cambios instantáneos, 
usando para ello el criterio de detectar URLs maliciosas

## main.py

Ficheros implicados: 

* **main.py**: programa principal
* **menu.py**: gestión menú interactivo
* **menu.yaml**: lista menú interactivo (consultas SQL predefinidas)
* **main.log**: traza del programa

Recupera datos de los ficheros **/var/log/nginx/access.log\*** (log de nginx del sistema) y **/etc/nginx/conf.d/blockips.conf**.
Estos ficheros son de solo lectura, por lo tanto, en el caso del segundo, debe alimentarse mediante el otro programa **blockips.conf**

Crea una base de datos SQLite en **memoria**, con las tablas *access* y *blocked* (basados en los dos ficheros citados)

A partir de aquí, el programa sirve para hacer consultas SQL configuradas en **menu.yaml**

## blockips.py

Ficheros implicados:

* **blockips.py**: programa principal
* **parselog.py**: toma el fichero *access.log* y lo convierte en una lista de diccionarios
* **database.py**: gestiona la inserción de diccionarios en *access* y *blocked*
* **logic.py**: genera el fichero *blockips.conf* en base a la tabla *blocked* y los criterios que se establecen aquí
* **watcher.py**: tiene el método *hay_cambios()* para ver si hay nuevas entradas en *access.log*

* **blockips.db**: base de datos SQLite con las tablas *access*, *blocked* y *access_unique* (que no parece usarse en el programa, debe de ser algo creado de forma interactiva)
* **watch.info**: fichero que contiene la fecha de la última actualización de *access.log*

### Para detener temporalmente el programa de bloqueo

`crontab -e`

Desabilitar la línea:

`* * * * * /root/.pyenv/shims/python /home/clouding/blockips/blockips.py`

Esto detiene la supervisión del log, pero acto seguido hay que vaciar el fichero  de configuración
de nginx y reiniciar el servicio:

rm /etc/nginx/conf.d/blockips.conf
touch /etc/nginx/conf.d/blockips.conf
systemctl restart nginx

## COSAS PENDIENTES
* Mecanismo **flush()** o algo así para limpiar el buffer antes de escribir y evitar así artefactos raros.
* Guardar una historia de comandos para poder recuperar el anterior y editarlo antes de volver a ejecutar.
* Un editor multilínea apañao para poder editar con más comodidad
* Tests input-output para el menú. 

Quedan cosas por hacer (TODO) que están distribuidas por el código 
y también explicadas en el doc del principio del código de *main.py*

## HISTORIAL MODIFICACIONES

### 2024-03-25
* Paso a borrar blockips.log semanalmente, para poder detectar qué pasó en casos como el de las 9000 peticiones no interceptadas. Sin el log no es posible saber nada al respecto. Con el log, ya veremos. Para que un crontab se ejecute el domingo, hay que poner el 5º campo a 0:
```
    # Paso a borrar el log semanalmente
    # El 0 en el 5º campo representa el DOMINGO
    55 23 * * 0 rm /home/clouding/blockips/blockips.log
```

### 2024-03-07
* Cambio en opción 3 de menu.yaml para incluir el número de peticiones 4xx


### 2024-02-22
* Cambio en logic.py para volver a incluir los 4xx, a raíz del envío de 7000 peticiones en 2 horas por parte de una máquina probando urls chungas. Con el cambio, 50 errores 4xx conllevan bloqueo.

### 2022-04-05
* Cambio en logic.py para bloquear por url en vez de por 404

### 2020-12-02
* Cambiado el sistema crontab: monitorizo el access.log cada minuto. Si hay cambios, procede a analizar el fichero para descubrir las IPs de los malos. Caso de que haya novedades, actualizo el fichero blockips.conf y reinicio el servidor Nginx

### 2020-11-30
* Añadir la opción params a las consultas vía YAML.

### 2020-11-29
* Carga de los datos de IPs bloqueadas del fichero blockips.conf a la tabla blocked de la base de datos.
* Añadidos los ficheros independientes para gestión del menú.
