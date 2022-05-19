### Hi there 👋

<!--
**pepeherr/pvpc** is a ✨ _special_ ✨ repository because its `README.md` (this file) appears on your GitHub profile.

Here are some ideas to get you started:

- 🔭 I’m currently working on ...
- 🌱 I’m currently learning ...
- 👯 I’m looking to collaborate on ...
- 🤔 I’m looking for help with ...
- 💬 Ask me about ...
- 📫 How to reach me: ...
- 😄 Pronouns: ...
- ⚡ Fun fact: ...
-->
# pvpc
Obtiene precios de energia a traves de la API de REE definida en el sitio
https://www.ree.es/es/apidatos
Obtendremos el PVPC: Precio horario del término de energía que se aplican en la factura eléctrica
de los consumidores con una potencia contratada no superior a 10 kW y que estén acogidos
al PVPC (Precio Voluntario para el Pequeño Consumidor).Incluye el término de energía de
los peajes de acceso (Orden IET/107/2014, 31 de enero), los cargos y el coste de producción.
No incluye impuestos.

Para ello usaremos un enlace semejante al que sigue, como ejemplo:
https://apidatos.ree.es/es/datos/mercados/precios-mercados-tiempo-real?start_date=2021-11-20T00:00&end_date=2021-11-22T23:59&time_trunc=hour&geo_limit=peninsular&geo_id=4

El formato en el que se obtiene es json y lo transformamos e incluimos en un dataframe
para posteriormente analizar los horarios mas baratos para el consumo electrico.

Red Eléctrica de España publica cada día a las 20.15 horas los precios horarios para el día siguiente, sin embargo cada vez que ejecutamos el comando /start se produce una actualización de los precios desde la hora actual hasta la hora en que los datos han sido publicados para analizar cuales son, dentro de ese periodo los periodos más baratos

Es un pequeño programa escrito en Python que fue diseñado inicialmente para crear variables de estado para HomeAssistant y poder establecer el arranque de equipos (termo eléctrico, lavadora, lavavajillas, ...) en los periodos más baratos.
Posteriormente fue transformado en un bot de Telegram que podeis ver funcionando en aqui: @PVPC_Horario_bot
