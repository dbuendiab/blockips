#
Para correr este programa (main.py) hay que activar primero el entorno virtual *envws*

pyenv activate envws

He creado el script *m3* en /root/bin para poder invocarlo directamente según entramos vía SSH.

## COSAS PENDIENTES
* Mecanismo **flush()** o algo así para limpiar el buffer antes de escribir y evitar así artefactos raros.
* Guardar una historia de comandos para poder recuperar el anterior y editarlo antes de volver a ejecutar.
* Un editor multilínea apañao para poder editar con más comodidad
* Tests input-output para el menú. 

Quedan cosas por hacer (TODO) que están distribuidas por el código 
y también explicadas en el doc del principio del código de *main.py*

## HISTORIAL MODIFICACIONES

### 2020-11-27
* Cambio cadenas patrón añadiendo 'r' de raw para que no siga saliendo el error de todos los backslash en la expresión regular. La gracia es que sigue funcionando igual, pero ahora sin errores.
### 2020-11-29
* Carga de los datos de IPs bloqueadas del fichero blockips.conf a la tabla blocked de la base de datos.
* Añadidos los ficheros independientes para gestión del menú.
### 2020-11-30
* Añadir la opción **params** a las consultas vía YAML. 
### 2020-12-02
* Cambiado el sistema crontab: monitorizo el access.log cada minuto. Si hay cambios, procede a analizar el fichero para descubrir las IPs de los malos. Caso de que haya novedades, actualizo el fichero blockips.conf y reinicio el servidor Nginx.