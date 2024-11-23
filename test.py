import paho.mqtt.client as mqtt
import keyboard
import matplotlib.pyplot as plt
import pandas as pd
import pyvisa 
import time
from threading import Thread

received_messages = []
rm = pyvisa.ResourceManager()

print(rm.list_resources())


def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))
    # Prihlásenie na tópik pre príjem výsledkov merania
    client.subscribe("measurement/results")

def on_message(client, userdata, msg):
    print(f"Received message: {msg.payload.decode()} on topic {msg.topic}")
    msgs = msg.payload.decode().strip('()') # Opravený názov premennej z 'mesgs' na 'msgs'
    print(msgs)
    message_parts = msgs.split(',')  # Tu tiež opravený názov premennej
    if len(message_parts) == 2:  # Overenie, či správa obsahuje dve časti
        try:
            received_messages.append((float(message_parts[0]), message_parts[1]))
        except ValueError as e:
            print(f"Error converting message parts to floats: {e}")

def vykonaj_funkciuA():
	print("Tlačidlo 'A' bolo stlačené, funkcia vykonaná!")
	client.publish("measurement/a", "meraj")
	
	
def vykonaj_funkciuS():
	print("Tlačidlo 'S' bolo stlačené, funkcia vykonaná!")
	client.publish("measurement/s", "k")
	
def vykonaj_funkciuD():
	print("Tlačidlo 'D' bolo stlačené, funkcia vykonaná!")
	client.publish("measurement/d", "b1")
		
def vykresli_graf(): 
	global received_messages
	if received_messages:
		print(received_messages)
		formatted_messages = [(time, float(value.strip())) for time, value in received_messages]
		times, values = zip(*formatted_messages)  # Rozdelenie na časy a hodnoty
		print(type(values))
		plt.plot(times, values)
		plt.title('Prijaté správy')
		plt.xlabel('Čas alebo poradie')
		plt.ylabel('Hodnota')
		plt.show()
		df = pd.DataFrame(received_messages)
		df.to_csv('file4.csv', index=False)
	else:
		print("Žiadne dáta na vykreslenie.")
	received_messages=[]
# Nastavenie MQTT

def analyza_priebehu():
	new_data = prevod_dat()
	vysledky = analyzuj_encoder(new_data)
	print(vysledky)

def analyzuj_rychlost():
	new_data = prevod_dat()
	upravene_data = prirad_rychlost_a_korekciu(new_data)
	print(upravene_data)
	
	
def analyzuj_encoder(data):
    # Vypočítať rozdiely medzi po sebe idúcimi hodnotami
    data['Pulse_Difference'] = data['Encoder_Pulse'].diff().abs()
    
    # Identifikovať rozlíšenie a medzery
    normálny_rozdiel = data['Pulse_Difference'].median()  # Median ako odhad "normálneho" impulzu
    malý_rozdiel = normálny_rozdiel / 2
    veľký_rozdiel = normálny_rozdiel * 3

    # Identifikovať štarty otočiek na základe veľkých a malých medzier
    starty_otociek = []
    rozlíšenie = 0
    i = 0
    while i < len(data) - 1:
        if data.iloc[i]['Pulse_Difference'] >= veľký_rozdiel:
            # Ak najdeme veľkú medzeru, overiť, či nasleduje menšia medzera
            if data.iloc[i + 1]['Pulse_Difference'] >= malý_rozdiel and data.iloc[i + 1]['Pulse_Difference'] < veľký_rozdiel:
                starty_otociek.append(i)
                # Preskočiť na koniec aktuálnej otočky, predpokladajúc rozlíšenie 20
                i += 20
                rozlíšenie += 1
            else:
                i += 1
        else:
            i += 1

    return {
        'Štarty otočiek': starty_otociek,
        'Rozlíšenie': rozlíšenie,
        'Pulzy medzi štartmi': [data.iloc[starty_otociek[j]:starty_otociek[j+1]] for j in range(len(starty_otociek) - 1)]
    }

# Testovať funkciu s aktuálnymi údajmi

	# Testovať funkciu s aktuálnymi údajmi
def prevod_dat():
	import pandas as pd

	# Zadané dáta ako zoznam dvojíc
	global received_messages
	data_list = received_messages

	# Konvertovať zoznam na DataFrame
	data_frame = pd.DataFrame(data_list, columns=['Time_us', 'Encoder_Pulse'])

	# Prevedenie reťazcov na číselné hodnoty pre stĺpec Encoder_Pulse
	data_frame['Encoder_Pulse'] = data_frame['Encoder_Pulse'].str.strip().astype(int)
	print(data_frame)
	return data_frame

import matplotlib.pyplot as plt

def vykresli_graf_rychlosti(data):
    # Skontroluj, či potrebné stĺpce existujú v DataFrame
    if 'Time_us' in data.columns and 'Rychlost_Otacania' in data.columns:
        plt.figure(figsize=(10, 5))  # Nastavenie veľkosti grafu
        plt.plot(data['Time_us'], data['Rychlost_Otacania'], label='Rýchlosť Otáčania', color='blue')
        plt.title('Priebeh rýchlosti otáčania od času')
        plt.xlabel('Čas (mikrosekundy)')
        plt.ylabel('Rýchlosť otáčania')
        plt.legend()
        plt.grid(True)
        plt.show()
    else:
        raise ValueError("Dataframe musí obsahovať stĺpce 'Time_us' a 'Rychlost_Otacania'")

# Predpokladá sa, že 'upravene_data' je DataFrame vytvorený a aktualizovaný z predchádzajúcich krokov
# Napríklad:
# upravene_data = prirad_rychlost_a_korekciu(data)

# Vykreslenie grafu



def prirad_rychlost_a_korekciu(data):
    # Skontroluj, či stĺpec 'Encoder_Pulse' existuje a vytvor 'Pulse_Difference'
    if 'Encoder_Pulse' in data.columns:
        data['Pulse_Difference'] = data['Encoder_Pulse'].diff().abs()
    else:
        raise ValueError("Stĺpec 'Encoder_Pulse' neexistuje v dátach.")
    
    # Výpočet rýchlosti otáčania
    if 'Pulse_Difference' in data.columns:
        threshold = data['Pulse_Difference'].max() * 0.8
        otocky_start_indices = data.index[data['Pulse_Difference'] >= threshold].tolist()
        rychlosti = []
        for i in range(len(otocky_start_indices) - 1):
            start = otocky_start_indices[i]
            end = otocky_start_indices[i + 1]
            casova_dlzka_us = data.loc[end, 'Time_us'] - data.loc[start, 'Time_us']
            if casova_dlzka_us > 0:  # Aby sme predišli deleniu nulou
                rychlost_otacania = 60_000_000 / casova_dlzka_us
                rychlosti.extend([rychlost_otacania] * (end - start))
        
        data['Rychlost_Otacania'] = pd.Series(rychlosti, index=data.index[:len(rychlosti)])
        
        # Korekcia hodnôt na základe rýchlosti otáčania
        korekcny_faktor = 1.05  # Príklad korekčného faktora, ktorý môžete zmeniť
        data['Korigovany_Pulse'] = data['Encoder_Pulse'] * data['Rychlost_Otacania'].apply(lambda x: korekcny_faktor if x > threshold else 1)
        vykresli_graf_rychlosti(data)
        return data
    else:
        raise ValueError("Stĺpec 'Pulse_Difference' nebol vytvorený.")
        
# Predpokladá sa, že 'data' je DataFrame s potrebnými stĺpcami
# Aplikujte túto funkciu na svoje dáta:
#upravene_data = prirad_rychlost_a_korekciu(data_frame)
	
broker = 'localhost'
port = 1883
topic = 'measurement/start'
client_id = 'python_client'

# Vytvorenie klienta a nastavenie callback funkcií
client = mqtt.Client(client_id)
client.on_connect = on_connect
client.on_message = on_message

# Pripojenie k MQTT brokerovi
client.connect(broker, port)

# Spustenie smyčky
client.loop_start()

# Odoslanie správy na spustenie merania
# Formát správy: "frekvencia_vzorkovania,cas_merania"
message = "100,3"
client.publish(topic, message)
print(f"Správa '{message}' bola odoslaná na tópik '{topic}'")


keyboard.add_hotkey('a', vykonaj_funkciuA)
keyboard.add_hotkey('s', vykonaj_funkciuS)
keyboard.add_hotkey('d', vykonaj_funkciuD)
keyboard.add_hotkey('f', vykresli_graf)
keyboard.add_hotkey('g', analyza_priebehu)
keyboard.add_hotkey('h', analyzuj_rychlost)
# Ponechanie klienta bežať v nekonečnej smyčke
# Tento riadok môžete zakomentovať, ak chcete skript ukončiť iným spôsobom

#'USB0::0x1AB1::0x0C94::DM3O182100444::0::INSTR'
# Ampermeter = 'USB0::0x1AB1::0x0C94::DM3O210400079::INSTR' 
#dmm = rm.open_resource('USB0::0x1AB1::0x0C94::DM3O182100444::0::INSTR')
#amm = rm.open_resource('USB0::0x1AB1::0x0C94::DM3O210400079::INSTR')

#setp digital meter
#dmm.write(':FUNCtion:VOLTage:DC')
#amm.write(':FUNCtion:CURRent:DC')

t = Thread(client.loop_stop())
t.run()

try:
	#for x in range(10):
	#	vmeas = float(dmm.query(':MEASure:VOLTage:DC?'))
	#	print(vmeas)
	#	print(x)
	#	while not (x < vmeas  < x +0.1):
	#		vmeas = float(dmm.query(':MEASure:VOLTage:DC?'))
	#		print(vmeas)
	#		time.sleep(1)
	#	mer = vmeas 
	#	print(x)
	while 1:
		pass
except KeyboardInterrupt:
    print("Skript bol prerušený manuálne")
    

 # Zastavenie loopu po ukončení skriptu
client.loop_stop()
client.disconnect() 

 # Odpojenie od MQTT brokera
 
