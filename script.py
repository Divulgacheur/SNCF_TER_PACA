#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Ce script sera lancé automatiquement à plusieurs moments de la journée afin de vérifier l'état des trains
import sys
import requests
import datetime
import locale
locale.setlocale(locale.LC_TIME, "fr_FR.UTF-8")
token = {'Authorization': "clé de l'API SNCF"}

nce_ville = 'stop_area:OCE:SA:87756056'		#Gare de Nice-Ville
nce_aug = 'stop_area%3AOCE%3ASA%3A87756254' #Gare de Nice-St-Augustin
cannes = 'stop_area%3AOCE%3ASA%3A87757625' #Gare de Cannes

def obtenir_disruption(voyage,disruptions):
	id_disrup_voyage =  voyage['sections'][1]['display_informations']['links'][0]['id']
	for i in disruptions:
		if i['disruption_id'] == id_disrup_voyage:
			return i
			

def trafic_trajet(gare_depart,gare_arrivee,horaire_depart):

	nom_gare_depart = requests.get('https://api.sncf.com/v1/coverage/sncf/stop_areas/'+gare_depart,headers=token).json()['stop_areas'][0]['name']
	nom_gare_arrivee = requests.get('https://api.sncf.com/v1/coverage/sncf/stop_areas/'+gare_arrivee,headers=token).json()['stop_areas'][0]['name']

	print('Trajets de',nom_gare_depart,'à',nom_gare_arrivee)

	rst = requests.get('https://api.sncf.com/v1/coverage/sncf/journeys?start_page=1&from='+gare_depart+'&to='+gare_arrivee+'&count=5&datetime='+horaire_depart+'&max_nb_transfers=0',headers=token)
	bilan_arrive = [] #tableau contenant l'état des 5 trains testés, si ok ou durée retard ou annulé
	
	print('Pour le',datetime.datetime.strptime(horaire_depart,'%Y%m%dT%H%M%S').strftime('%A %d %B %Y'))
	for voyage in rst.json()['journeys']:
		horaire = datetime.datetime.strptime(voyage['departure_date_time'],'%Y%m%dT%H%M%S')
		print(horaire.strftime('%Hh%M'),voyage['sections'][1]['display_informations']['commercial_mode'], voyage['sections'][1]['display_informations']['headsign'])
		
		if voyage['status'] == 'SIGNIFICANT_DELAYS': #si le train est en retard
		
			perturb_corres = obtenir_disruption(voyage,rst.json()['disruptions'])
		
			
		#On fait correspondre la perturbation du train avec l'ensemble des perturbations
			
				
			for arret in perturb_corres['impacted_objects'][0]['impacted_stops']: #On parcourt l'ensemble des arrets
				
				if arret['stop_point']['name'] == nom_gare_depart: #on balaye les arrêts jusqu'à trouver celui d'où l'on part
					print('Il y a du retard au départ, à : '+ datetime.datetime.strptime(arret['amended_departure_time'],'%H%M%S').strftime('%Hh%M'), 'à cause de','non-connu' if arret['cause']=='' else arret['cause'])
				
				elif arret['stop_point']['name'] == nom_gare_arrivee: #on balaye les arrets jusqu'à trouver celui où l'on arrive
				
					retard_arrive = datetime.datetime.strptime(arret['amended_arrival_time'] ,'%H%M%S') - datetime.datetime.strptime(arret['base_arrival_time'],'%H%M%S')
					bilan_arrive.append(int(retard_arrive.total_seconds())//60 ) #On enregistre la durée du retard dans le tableau bilan
					print('heure d\'arrivée',datetime.datetime.strptime(arret['amended_arrival_time'],'%H%M%S').strftime('%Hh%M'),'au lieu de',datetime.datetime.strptime(arret['base_arrival_time'],'%H%M%S').strftime('%Hh%M' ))
			
		elif voyage['status'] == 'REDUCED_SERVICE':		#si le train n'effectue pas tous ses arrêts (trajet modifié)
			id_perturb = voyage['sections'][1]['display_informations']['links'][0]['id']
			#print(id_perturb)
			for une_perturb in rst.json()['disruptions']: #On identifie la perturbation correspondante au train parmis l'ensemble
				if une_perturb['id'] == id_perturb:
					perturb_corres = une_perturb
					break
					
			ca_va = True
			for arret in perturb_corres['impacted_objects'][0]['impacted_stops']: #On parcourt l'ensemble des arrets
			
				if arret['stop_point']['name'] == nom_gare_depart:
					

					if arret['departure_status'] == 'deleted': # le train ne passera pas par le point de départ
						ca_va = False
						break
						
				elif arret['stop_point']['name'] == nom_gare_arrivee:
					if arret['arrival_status'] == 'unchanged': # it's ok
						h_arrive_reelle = h_arrive_origine = arret['amended_arrival_time']
					elif arret['arrival_status'] == 'delayed': # le train arrivera en retard
						h_arrive_reelle = arret['amended_arrival_time']
						h_arrive_origine = arret['base_arrival_time']
						
					elif arret['arrival_status'] == 'deleted': # le train ne passera pas par la gare d'arrivee
						ca_va = False
						break
						
			if ca_va == False :	
				print('Vos arrêts ne seront pas déservis => ne correspondra pas au trajet voulu')
				bilan_arrive.append(-1)
			elif ca_va == True:
				
				retard_arrive = datetime.datetime.strptime(h_arrive_reelle ,'%H%M%S') - datetime.datetime.strptime(h_arrive_origine,'%H%M%S')
				bilan_arrive.append(int(retard_arrive.total_seconds())//60)
				
			
		elif voyage['status'] == 'NO_SERVICE': #si le train est annulé
			perturb = (obtenir_disruption(voyage,rst.json()['disruptions']))
			
			raison = perturb['messages'][0]['text'] if 'messages' in perturb else perturb['cause']
			
			print('Ce train a été annulé, à cause de','non-connu' if raison=='' else raison )
			bilan_arrive.append(-1)
		else : bilan_arrive.append(0)
			
	print('\nBilan :',bilan_arrive,'\n\n')
	return bilan_arrive
	
aujourdhui = datetime.datetime.now().strftime('%Y%m%d')


trafic_trajet(cannes,nce_aug, aujourdhui+'T165000')

resultat = trafic_trajet(nce_aug,cannes, aujourdhui+'T073000')
		
print(sys.argv)
if len(sys.argv) not in {1,2}:
	print('mauvaise syntaxe')
if len(sys.argv) in {1}:
	print()
	
elif sys.argv[1] == 'all': #On interroge 
	if resultat.count(-1) > 3:		#Greve/Panne Générale
		requests.post('https://maker.ifttt.com/trigger/train_impacté/with/key/1i9MCqQR4TGQtO-OlsvoL')

elif sys.argv[1] == '08h07':
	if resultat[2] > 15 or resultat[2] == -1 : #Train de 8h07 en retard de plus de 15 minutes ou annulé
		requests.post('https://maker.ifttt.com/trigger/train_impacté/with/key/1i9MCqQR4TGQtO-OlsvoL')


#50 6 * * 1,2 ./TER_SNCF 08h07 #lundi,mardi, à 6h50 on vérifie si le train de 8h07 roule & retard < 15
#55 6 * * 1,2 ./TER_SNCF 08h07 #lundi,mardi, à 6h55 on vérifie si le train de 8h07 roule & retard < 15
#0 7 * * 1,2 ./TER_SNCF 08h07 #lundi,mardi, à 7h00 on vérifie si le train de 8h07 roule & retard < 15


#30 6 * * 1,2 ./TER_SNCF all #lundi,mardi, à 6h30 on vérifie si tous les trains roulent
#10 6 * * 1,2 ./TER_SNCF all #lundi,mardi, à 6h10 on vérifie si tous les trains roulent
	
	



# à 6h30 on vérifie si au moins un train roule
	#--> si aucun train : reveil

# à 6h50 on vérifie si train 8h07 n'as pas de retard >15m
	#--> alors reveil
# idem à 6h55 et à 7h00	

