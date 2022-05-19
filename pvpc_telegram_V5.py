#!/usr/bin/python3
#_*_ coding: utf-8 _*_

"""
Obtiene precios de energia a traves de la API de REE definida en el sitio
https://www.ree.es/es/apidatos
Obtendremos el PVPC: Precio horario del término de energía que se aplican en la factura eléctrica
de los consumidores con una potencia contratada no superior a 10 kW y que estén acogidos
al PVPC (Precio Voluntario para el Pequeño Consumidor).Incluye el término de energía de
los peajes de acceso (Orden IET/107/2014, 31 de enero), los cargos y el coste de producción.
No incluye impuestos.

Para ello usaremos, como ejemplo, la siguiente url:
https://apidatos.ree.es/es/datos/mercados/precios-mercados-tiempo-real?
start_date=2021-11-20T00:00&end_date=2021-11-22T23:59&time_trunc=hour&geo_limit=peninsular
&geo_id=4

Red Eléctrica de España publica cada día a las 20.15 horas los precios horarios para el día 
siguiente

El formato en el que se obtiene es json y lo transformamos e incluimos en un dataframe
para posteriormente analizar los horarios mas baratos para el consumo electrico.
"""
import pandas as pd
#import numpy as np
import matplotlib.pyplot as plt
#import math
from datetime import datetime
from datetime import timedelta
#import datetime
import requests
import json
#import csv
#from IPython.display import HTML
#Lo que sigue para Telegram
#from bs4 import BeautifulSoup  #del módulo bs4, necesitamos BeautifulSoup
#import requests
import schedule

import os
import time

from config.auth import bot_token, bot_chatID

import logging

from telegram import (
    Poll,
    ParseMode,
    KeyboardButton,
    KeyboardButtonPollType,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
import telegram
from telegram.ext import (
    Updater,
    CommandHandler,
    PollAnswerHandler,
    PollHandler,
    MessageHandler,
    Filters,
    CallbackContext,
)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


#Creamos la tupla de los dias de la semana con ambito global
dia_semana=('Lunes,','Martes,','Miercoles,','Jueves,','Viernes,','Sábado,','Domingo,')
# Otras variables globales:
api_url = 'https://api.telegram.org/bot' + bot_token
solicitudes_ayuda = 0
solicitudes_actualizacion = 0

def compone_enlace():
    '''
    Componemos el elace completo y obtenemos
    un json que denominamos datos con todos los resultados
    '''
    #Creamos una lista para después concatenar en enlace_completo
    #y construir la url con las fechas apropiadas que necesitamos para la API de REE
    enlace=["https://apidatos.ree.es/es/datos/mercados/precios-mercados-tiempo-real?start_date="]
    
	# tengo que modificar la siguiente línea pues no sé porque dentro de
    #pyscript la hora es una hora menos	  
    hace_una_hora=datetime.now()-timedelta(hours=1)
    # la cambio por esta:
    #hace_una_hora=ahora

    hace_una_hora_iso=hace_una_hora.isoformat()
    enlace.append(hace_una_hora_iso)
    enlace.append("&end_date=")
    mañana=datetime.now()+timedelta(days=2)
    mañana_iso=mañana.isoformat()
    enlace.append(mañana_iso)
    enlace.append("&time_trunc=hour&geo_limit=peninsular&geo_id=4")
    enlace_completo=""

    #enlace es una lista de la que tenemos que unir todos sus elementos para formar
    #la variable de tipo string denominada enlace_completo
    for word in enlace:
        enlace_completo +=str(word)

    #accedemos a la url de la REE y nos la llevamos a la variable texto
    # La siguiente línea la comento. Funciona bien en python3 pero es necesario modificarla:
    url=requests.get(enlace_completo)
    #Ver https://hacs-pyscript.readthedocs.io/en/latest/reference.html
    #Lo cambio por la sentencia correcta dentro de pyscript y home assistant:
    #url= task.executor(requests.get, enlace_completo)
    texto=url.text
    # del siguiente print obtuve la estructura de los datos del json generado por REE
    #print(texto)
    # se trata de un diccionario de diccionarios y listas
    #ahora convertimos texto en el diccionario de datos (formato json)
    datos=json.loads(texto)
    return(datos)

def prox_pvpc( ud, telegram, figura):
    # argumento ud define las unidades en la que se expresarán los precios:
    # si es K serán €/Kwh
    # si es M u otro serán €/Mwh
    factor = 1
    redondeo = 2
    if ud == 'K':
        factor=1000
        redondeo = 5
    #el día de la semana como un número entero, donde el lunes es 0 y el domingo es 6
    n_dia_semana=datetime.weekday(datetime.now())
    t_dia_semana=dia_semana[n_dia_semana]
    
    datos = compone_enlace()
    
    #Transformar la fecha y hora en formato ISO dada por REE en una mejor legible:
    a=datetime.strptime(datos['data']['attributes']['last-update'][0:10],"%Y-%m-%d")
    b=datetime.strptime(datos['data']['attributes']['last-update'][11:15],"%H:%M")
    u_actualización= a.strftime("%d/%m/%Y")+" a las "+ b.strftime("%H:%M")
    del a, b
    
    t_ahora=datetime.now().strftime("%d/%m/%Y %H:%M")

    #Obtener una lista con fechas y horas y otra con PVPC
    #para después crear un dataframe
    #included[0] es el PVPC
    #included[1] es el mercado spot
    #included es una lista:
    included=datos['included']
    unidades=included[0]['attributes']['title'][6:11]
    if ud == 'K':
        unidades = '€/Kwh'
    #creo listas vacias para las fechas,las horas, los PVPC, el desvio con respecto a la media,
    # el promedio de cada dos horas consecutivas y el prmedio de cada tres consecutivas
    fechas=[]
    horas=[]
    pvpcs=[]
    desvio=[]
    pares=[]
    trios=[]

    for y in range(len(included[0]['attributes']['values'])):
        fecha_texto=included[0]['attributes']['values'][y]['datetime'][0:10]
        fecha_fecha=datetime.strptime(fecha_texto,"%Y-%m-%d")
        fechas.append(datetime.strftime(fecha_fecha,"%d/%m/%Y"))
        hora_texto=included[0]['attributes']['values'][y]['datetime'][11:15]
        hora_hora=datetime.strptime(hora_texto,"%H:%M")
        horas.append(datetime.strftime(hora_hora,"%H:%M"))
        pvpcs.append(included[0]['attributes']['values'][y]['value']/factor)   
    
    #Unimos en una lista las tres columnas con zip
    fechas_precios=list(zip(fechas, horas,pvpcs))

    #Lo convertimos en un panda dataframe
    proximos=pd.DataFrame(fechas_precios,columns=['Fecha','Hora',unidades])
    #print('datos',proximos.iloc[:,2].count()) # Cuidado con ese .iloc: no funciona, cambio por:
    precio_medio=round(proximos[unidades].sum()/proximos[unidades].count(),redondeo)
    for x in range(len(pvpcs)):
        #calcula desvios con respecto a la media
        desvio.append(proximos.iloc[x,2]-precio_medio)
        if x+1 < len(pvpcs):
            pares.append(round((proximos.iloc[x,2]+proximos.iloc[x+1,2])/2,redondeo))
        else:
            pares.append(None)
        if x+2 < len(pvpcs):
            trios.append(round((proximos.iloc[x,2]+proximos.iloc[x+1,2]+proximos.iloc[x+2,2])/3,redondeo))
        else:
            trios.append(None)
    proximos['PVPC-Media']=desvio
    proximos['PVPC_2h']=pares
    proximos['PVPC_3h']=trios
    precio_actual = round(proximos.iloc[0,2],redondeo)
    # precio más bajo del periodo
    precio_mas_bajo = round(proximos[unidades].min(),redondeo)
    precio_mas_bajo_2h = proximos['PVPC_2h'].min()
    precio_mas_bajo_3h = proximos['PVPC_3h'].min()
    # indice del precio más bajo
    indice_precio_mas_bajo = proximos[unidades].idxmin()
    indice_precio_mas_bajo_2h = proximos['PVPC_2h'].idxmin()
    indice_precio_mas_bajo_3h = proximos['PVPC_3h'].idxmin()
    # vemos cual es la hora de más bajo precio
    hora_mas_barata = proximos['Hora'][indice_precio_mas_bajo]
    #determinar las dos horas y las tres horas consecutivas más baratas 
    dos_horas_mas_baratas = proximos['Hora'][indice_precio_mas_bajo_2h]
    tres_horas_mas_baratas = proximos['Hora'][indice_precio_mas_bajo_3h]
    dia_mas_barato = proximos['Fecha'][indice_precio_mas_bajo]
    fecha_dos_horas = proximos['Fecha'][indice_precio_mas_bajo_2h]
    tres_horas_mas_baratas = proximos['Hora'][indice_precio_mas_bajo_3h]
    fecha_tres_horas = proximos['Fecha'][indice_precio_mas_bajo_3h]
    if telegram:
        texto = t_dia_semana + t_ahora + '\n' + 'Última actualización del PVPC realizada por REE el ' + u_actualización + '\n' \
              + '- Precio actual ' + str(precio_actual) + ' ' + unidades + '\n' \
              + '- Precio medio del periodo: ' + str(precio_medio) + ' ' + unidades + '\n' \
              + '- El precio más bajo es ' + str(precio_mas_bajo) + ' ' + unidades + ' a las ' \
              + hora_mas_barata + 'h del ' + dia_mas_barato + '\n' \
              + '- El par de horas consecutivas más baratas tienen un precio de ' \
              + str(precio_mas_bajo_2h) + ' ' + unidades + ' y comienzan a las ' + dos_horas_mas_baratas + 'h del ' + fecha_dos_horas + '\n' \
              + '- Las tres horas consecutivas más baratas tienen un precio de ' \
              + str(precio_mas_bajo_3h) + ' ' + unidades + ' y comienzan a las ' + tres_horas_mas_baratas + 'h del ' + fecha_tres_horas + '\n'
        tabla_pvpc=proximos[proximos.columns[0:4]].to_string(col_space = 7, index = False, justify="center", header=["__  Fecha   ", \
                                                                                            "___    Hora    __", unidades, "_ Dif Med"])
    else:
        print(f"{t_dia_semana}{t_ahora}")
        print(f"Última actualización del PVPC realizada por REE el {u_actualización}")
        print()
        print(f'· Precio actual {precio_actual} {unidades}')
        print(f"· Precio medio del periodo es {precio_medio} {unidades}")
        print(f'· El precio más bajo es de {precio_mas_bajo} {unidades} a las {hora_mas_barata}h del {dia_mas_barato}')
        print(f'· El par de horas consecutivas más baratas (PVPC_2h) tienen un precio de {precio_mas_bajo_2h} {unidades} y comienzan a las {dos_horas_mas_baratas}h del {fecha_dos_horas}')
        print(f'· Las tres horas consecutivas más baratas (PVPC_3h) tienen un precio de {precio_mas_bajo_3h} {unidades} y comienzan a las {tres_horas_mas_baratas}h del {fecha_tres_horas}')
        print()
        print(44*'*')
        print(proximos[proximos.columns[0:4]].to_string(col_space = 7, index = False))
        print(44*'*')

    if figura:
        #Gráfico
        x = proximos['Fecha'] + ' ' + proximos['Hora'] 
        y=proximos.iloc[:,2]
        parametros={'axes.labelsize':5,'axes.titlesize':5, 'figure.titlesize':65,
            'xtick.labelsize':5, 'ytick.labelsize':5, 'figure.figsize':(4,4) }
        fig = plt.figure(figsize=(10,5))
        plt.rcParams.update(parametros)
        fig, ax = plt.subplots(1)
        fig.autofmt_xdate()
        plt.plot(x,y,marker='o')
        plt.title('Evolución del PVPC', fontsize=10)
        plt.ylabel('€/Mwh')
        plt.grid(axis='y',linestyle='dashed')
        
        #Para publicar el gráfico en telegran, primero creamos un archivo de imagen img_temp.png
        if telegram:
            imagen='./img_temp.png'
            fig.savefig(imagen, bbox_inches=None, dpi=150)
        else:
            plt.show()
    return(texto, tabla_pvpc)

def verif_actualizacion():
    actualizado = True
    datos = compone_enlace()
    ultima_actualizacion=datetime.strptime(datos["data"]['attributes']['last-update'][0:10],"%Y-%m-%d")
    ahora = datetime.now()
    if ultima_actualizacion < ahora:
        actualizado = False
        time.sleep(5*60)
        print (datetime.now().strftime("%d/%m/%Y %H:%M"))
        verif_actualizacion()
    else:
        prox_pvpc(ud='M', telegram=False, figura=True)
        actualizado=True
    return (actualizado)

def start(update=Update, context=CallbackContext) -> None:
    #c_id = get_chat_id(update, context)
    fn_usuario = str(update.message.chat.first_name)
    un_usuario = str(update.message.chat.username)
    #chat_id = str(bot.bot_chatID)
    logger.info('He recibido un comando /start de ' + fn_usuario + ' username ' + un_usuario)
    #bot.send_message('Recibida solicitud')
    #bot.send_message(chat_id=update.message.chat_id, text="Recibida solicitud de actualización")
    update.message.reply_text('Hola ' + fn_usuario + ', actualizo el PVPC')
    resultado=prox_pvpc(ud='M', telegram=True, figura=True)
    update.message.reply_text(resultado[0] + '\n' + resultado[1], parse_mode='HTML')
    # Incluye gráfico y después elimina el archivo
    imagen="img_temp.png"
    update.message.reply_photo(open(imagen, 'rb'))
    os.remove(imagen)
    
def ayuda(update=Update, context=CallbackContext) -> None:
    mensaje= "<b>Ayuda:</b>\n El bot obtiene precios de energia a traves de la API de REE para posteriormente mostrar:\n \
    · Análisis de los horarios mas baratos para el consumo electrico.\n \
    · Tabla con fecha, hora, PVPC y diferencias con el precio medio del periodo\n \
    · Gráfico de evolución del PVPC en las próximas horas.\n \n \
    El <b>PVPC</b> <i>(Precio Voluntario para el Pequeño Consumidor)</i> incluye\
    el término de energía de los peajes de acceso (Orden IET/107/2014, 31 de enero), los cargos y el coste de producción.\
    No incluye impuestos.\n \n "
    mensaje= mensaje + "Los comandos dsponibles son los siguientes: \n"
    mensaje = mensaje +"/start -> Actualización de PVPC\'s \n"
    mensaje = mensaje + "/help -> Muestra este mensaje de ayuda"
    update.message.reply_text(mensaje, parse_mode='HTML')

def main():
    updater = Updater(token=bot_token, use_context=True)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('help', ayuda))
    updater.start_polling(drop_pending_updates=True)
    updater.idle()

# Ahora comienza todo ....
print('Inicio ...')

if __name__ == '__main__':
    main()

# primer argumento ud 'K' para €/Kwh y 'M' para €/Mwh
# segundo argumento telegram True o False para enviar mensajes al bot de telegram o mediante un print
# argumento inicio (hora de inicio a partir de la cual se requiere precio más bajo
# argumento ciclo (horas de marcha del equipo)
#df=prox_pvpc(ud='M', telegram=False, figura=True)