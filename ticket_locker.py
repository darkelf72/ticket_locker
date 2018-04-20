#https://stackoverflow.com/questions/33876657/how-to-install-python-any-version-in-windows-when-youve-no-admin-priviledges
import requests
from lxml import html
import os
import datetime
import time
import re

#Для подавления сообщения "InsecureRequestWarning: Unverified HTTPS request is being made. Adding certificate verification is strongly advised."
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

url = 'http://itagent.otkritie.ru'
#Параметры для авторизации в ОТРС
payload = {}
payload['Action'] = 'Login'
payload['User'] = 'srodionov'
payload['Password'] = ''

#Список наименований шаблонов поиска ОТРС, по которым будем искать и лочить заявки
otrs_profiles = []
otrs_profiles.append('ticket_locker_test')   
#otrs_profiles.append('ticket_locker_test2')
#otrs_profiles.append('ticket_locker_test3')

try:
    s = requests.Session()
    r = s.post(url, verify=False, params=payload)
    if r.status_code != requests.codes.ok:
        raise http_error    
except:
    print(r.status_code) 
    raise SystemExit 

#ChallengeToken необходим для того, чтобы посылть POST запросы на изменение чего-либо в ОТРС
tree = html.fromstring(r.text)
ChallengeToken = tree.xpath('//input[@name = "ChallengeToken"]/@value')[0]
print(ChallengeToken)
'''
#Вид отображения возвращаемых страниц. Small наиболее компактный, поэтому страницы меньше весят, ОТРС нагружается меньше
#в Preview есть тело заявки - он может понадобиться для более сложных критериев поиска заявок с парсингом по телу, но ОТРС будет нагружаться сильнее, так как страница будет больше весить
View = 'Small'
#View = 'Medium'
#View = 'Preview'

#Настройки для вида страниц в ОТРС и максимального количества заявок, которые вернет ОТРС 
payload = {}
payload['ChallengeToken'] = ChallengeToken
payload['Action'] = 'AgentPreferences'
payload['Subaction'] = 'Update'
payload['Group'] = 'TicketOverview' + View + 'PageShown'
payload['UserTicketOverview' + View + 'PageShown'] = '10'

r = s.post(url, verify=False, params=payload)
'''
#Параметры POST для применения шаблона поиска
search_params = {}
search_params['Action'] = 'AgentTicketSearch'
search_params['Subaction'] = 'LoadProfile'
search_params['SearchTemplate'] = 'Поиск'

#Параметры POST для блокировки заявки
lock_params = {}
lock_params['ChallengeToken'] = ChallengeToken
lock_params['Action'] = 'AgentTicketLock'
lock_params['Subaction'] = 'Lock'

#Папка с файлами логов создается в каталоге, откуда запущен скрипт
file_path = os.getcwd()+'/log'
if not os.path.exists(file_path):
    os.makedirs(file_path)
now = datetime.datetime.now()
file_name = now.strftime("%Y-%m-%d")+'.log'
file_name = file_path+'/'+file_name

#Цикл будет работать только в рабочее время (чтобы не привлекать внимание постоянными запросами ночью или в воскресенье)
while now.time() > datetime.time(8) and now.time() < datetime.time(18) and now.isoweekday() < 7: 
    for Profile in otrs_profiles:
        log_file = open(file_name,'a')
        now = datetime.datetime.now()
        print(now.strftime("%Y-%m-%d %H:%M:%S"))
        log_file.write(now.strftime("%Y-%m-%d %H:%M:%S")+'\n')
        print('Шаблон поиска: '+Profile)
        log_file.write('Шаблон поиска: '+Profile+'\n')
        search_params['Profile'] = Profile

        r = s.post(url, verify=False, params=search_params)
        #print(r.url)
        #log_file.write(r.url+'\n')

        tree = html.fromstring(r.text)

        #Если будет найдена только одна заявка, то otrs сделает redirect на Action=AgentTicketZoom;TicketID=
        result = re.search('TicketID=(\d+)',r.url)
        if result != None:
            TicketID = result.group(1)

            TicketNumber = tree.xpath('//head/title/text()')[0]
            result = re.search('^(\d+)',TicketNumber)
            TicketNumber = result.group(1)
            print(TicketNumber)
            log_file.write(TicketNumber+'\n')

            #Лочим заявку
            lock_params['TicketID'] = TicketID
            r = s.post(url, verify=False, params=lock_params)
            print(r.url)
            log_file.write(r.url+'\n')

        #Если не было редиректа на Action=AgentTicketZoom;TicketID= то заявок 0 или больше 1
        else:
            tickets = tree.xpath('//*[starts-with(@id,"TicketID_") and starts-with(@class,"MasterAction")]')
            tlen = str(len(tickets)) or '0'
            print('Количество заявок: '+tlen)
            log_file.write('Количество заявок: '+tlen+'\n')
            for ticket in tickets:                
                result = re.search('TicketID_(\d+)',ticket.xpath('./@id')[0])
                TicketID = result.group(1)

                TicketNumber = ticket.xpath('.//a[@class = "MasterActionLink"]/text()')[0]
                print('Заявка №: '+TicketNumber)
                log_file.write('Заявка №: '+TicketNumber+'\n')

                #Лочим заявку
                lock_params['TicketID'] = TicketID            
                r = s.post(url, verify=False, params=lock_params)
                print(r.url)
                log_file.write(r.url+'\n')

        print(         '--------------------')
        log_file.write('--------------------\n')
        log_file.close()
        time.sleep(8)