#
Para correr este programa (main.py) hay que activar primero el entorno virtual *envws*

pyenv activate envws

He creado el script *m3* en /root/bin para poder invocarlo directamente según entramos vía SSH.

Quedan cosas por hacer (TODO) que están distribuidas por el código 
y también explicadas en el doc del principio del código de *main.py*

## HISTORIAL MODIFICACIONES

### 2020-11-27
* Cambio cadenas patrón añadiendo 'r' de raw para que no siga saliendo el error de todos los backslash en la expresión regular. La gracia es que sigue funcionando igual, pero ahora sin errores.