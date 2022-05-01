## Imports
from Clases import *
from f_SignalProcFuncLibs import *
import numpy as np
import Funciones as fn
from pyOpenBCI import OpenBCICyton
import random
import scipy.signal as sig
import cv2
import time

#Definir la señal a ejecutar

Tipo_Señal = input('Indique el tipo de señal (EOG o EMG)')
mode = input(('Indique el tipo de experimento')) #train/test

## Constantes

s_SRate = 250 # Hertz
window = 1 # segundos
act = 0.25 # segundos

# Configuración de la board

board = OpenBCICyton(port='COM3')
uVolts_per_count = (4500000)/24/(2**23-1) #uV/count

# Filtros

filt_FiltSOS_eog = f_GetIIRFilter(s_SRate, [0.015, 10], [0.01, 12])
filt_FiltSOS_emg = f_GetIIRFilter(s_SRate, [20, 57], [15, 59])

# Lista inicial
inc_data = []

# Cargar umbrales previamente calculados en calibracion

if Tipo_Señal == "EOG":
    U_Parpadeo = np.array(np.loadtxt('U_Parpadeo.txt'))
    U_Derecha_EOG = np.array(np.loadtxt('U_Derecha_EOG.txt'))
    U_Izquierda_EOG = np.array(np.loadtxt('U_Izquierda_EOG.txt'))

elif Tipo_Señal == "EMG":

    U_Arriba = np.array(np.loadtxt('U_Arriba.txt'))
    U_Arriba = U_Arriba[0]

    U_Izquierda_EMG = np.array(np.loadtxt('U_Izquierda_EMG.txt'))
    U_Izquierda_EMG = U_Izquierda_EMG[0]

    U_Derecha_EMG = np.array(np.loadtxt('U_Derecha_EMG.txt'))
    U_Derecha_EMG = U_Derecha_EMG[0]

#
def adquisicion(sample):
    inc_data.append(np.array(sample.channels_data) * uVolts_per_count)

    if len(inc_data) == int(s_SRate * act):
        ventana.refresh(inc_data)
        procesamiento(ventana.data)
        inc_data.clear()

def procesamiento(data):
    sig_arr_emg = sig.detrend(data[:, 0])
    sig_der_emg = sig.detrend(data[:, 1])
    sig_izq_emg = sig.detrend(data[:, 2])
    sig_der_eog = sig.detrend(data[:, 4])
    sig_izq_eog = sig.detrend(data[:, 5])

    # Filtro

    sig_izq_emg = signal.sosfiltfilt(filt_FiltSOS_emg, sig_izq_emg)
    sig_der_emg = signal.sosfiltfilt(filt_FiltSOS_emg, sig_der_emg)
    sig_arr_emg = signal.sosfiltfilt(filt_FiltSOS_emg, sig_arr_emg)
    sig_izq_eog = signal.sosfiltfilt(filt_FiltSOS_eog, sig_izq_eog)
    sig_der_eog = signal.sosfiltfilt(filt_FiltSOS_eog, sig_der_eog)

    # Artefactos en los bordes
    sig_arr_emg = sig_arr_emg[int(0.1 * window * s_SRate):-int(0.1 * window * s_SRate)]
    sig_der_emg = sig_der_emg[int(0.1 * window * s_SRate):-int(0.1 * window * s_SRate)]
    sig_izq_emg = sig_izq_emg[int(0.1 * window * s_SRate):-int(0.1 * window * s_SRate)]
    sig_der_eog = sig_der_eog[int(0.1 * window * s_SRate):-int(0.1 * window * s_SRate)]
    sig_izq_eog = sig_izq_eog[int(0.1 * window * s_SRate):-int(0.1 * window * s_SRate)]

    # Suavizado
    sig_izq_eog_avg = fn.f_AvFlt(sig_izq_eog, s_SRate, 0.08)
    sig_der_eog_avg = fn.f_AvFlt(sig_der_eog, s_SRate, 0.08)

    # Primera derivada

    diff_izq_eog = np.diff(sig_izq_eog_avg)
    diff_der_eog = np.diff(sig_der_eog_avg)

    # Suavizado 2

    diff_izq_eog_avg = fn.f_AvFlt(diff_izq_eog, s_SRate, 0.08)
    diff_der_eog_avg = fn.f_AvFlt(diff_der_eog, s_SRate, 0.08)

    # Maximo de ventana

    diff_izq_emg_avg = np.max(sig_izq_emg)
    diff_der_emg_avg = np.max(sig_der_emg)
    diff_arr_emg_avg = np.max(sig_arr_emg)

    # Movimiento EOG

    mov = fn.identificar_movimiento(diff_der_eog_avg, diff_izq_eog_avg, U_Derecha_EOG, U_Izquierda_EOG)
    print(mov)
    Movimiento.actualizar(mov, mode=mode, sig_type= Tipo_Señal)

    # Movimiento EMG

    if diff_arr_emg_avg > U_Arriba and not diff_der_emg_avg > U_Derecha_EMG and not diff_izq_emg_avg > U_Izquierda_EMG:
        mov_emg = 'MF'
        print(mov_emg)
        Movimiento.actualizar(mov, mode=mode, sig_type= Tipo_Señal)

    elif diff_der_emg_avg > U_Derecha_EMG and not diff_izq_emg_avg > U_Izquierda_EMG and not diff_arr_emg_avg > U_Arriba:
        mov_emg = 'CD'
        print(mov_emg)
        Movimiento.actualizar(mov, mode=mode, sig_type= Tipo_Señal)

    elif diff_izq_emg_avg > U_Izquierda_EMG and not diff_der_emg_avg > U_Derecha_EMG and not diff_arr_emg_avg > U_Arriba:
        mov_emg = 'CI'
        print(mov_emg)
        Movimiento.actualizar(mov, mode=mode, sig_type= Tipo_Señal)

    elif diff_izq_emg_avg > U_Izquierda_EMG and diff_der_emg_avg > U_Derecha_EMG and not diff_arr_emg_avg > U_Arriba:
        mov_emg = 'C'
        print(mov_emg)
        Movimiento.actualizar(mov, mode=mode, sig_type= Tipo_Señal)

    else:
        mov_emg = 'Nada'



## Definición de diccionarios

dic_EMG = {'Mov1': 'MF', 'Mov2': 'CI', 'Mov3': 'CD', 'Mov4': 'C'}
dic_EOG = {'Mov1': 'P', 'Mov2': 'PP', 'Mov3': 'PI', 'Mov4': 'PD',
           'Mov5': 'IP', 'Mov6': 'DP', 'Mov7': 'I', 'Mov8': 'D'}

##

if mode == 'test':
    if Tipo_Señal == "EOG":
        movs_list = fn.mov_list(mode=mode, **dic_EOG)
        np.savetxt('EOG_Real_Moves.txt', movs_list)

    elif Tipo_Señal == "EMG" :
        movs_list = fn.mov_list(mode=mode, **dic_EMG)
        np.savetxt('EMG_Real_Moves.txt', movs_list)

for mov in movs_list:

    pygame.mixer.init()
    pygame.mixer.music.load("mp3//demo.mp3")
    pygame.mixer.music.play()

    fn.play_vid(mov)

    time.sleep(0.5)

    pygame.mixer.music.load("mp3//prep.mp3")
    pygame.mixer.music.play()


    ventana = proc_wind(8, int(s_SRate * window), int(act * s_SRate))
    Movimiento = pre_wind()
    board.start_stream(adquisicion)
    #falta parar el stream en adquisicion

# Inicio de toma de datos
