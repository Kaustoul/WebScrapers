from email.mime import audio
from fileinput import filename
import requests
from bs4 import BeautifulSoup as bs
import os
import subprocess
import wget
import csv
import shutil

champ = 'Yasuo'
url = "https://leagueoflegends.fandom.com/wiki/*-*/LoL/Audio"

seactionsBlacklist = ['AbilityCasting', 'Death']
skinBlacklist = ['Nightbringer']

print("Champion name")
inp = input()
if not inp == '':
    champ = inp

url = url.replace('*-*', champ)

request = requests.get(url)
if not request:
    print("Didnt get a response")
    exit()

html = bs(request.text, 'html.parser')

sections = request.text.split('<h2>')
h2s = html.findAll('h2')

i = 1
for h2 in h2s:
    h2 = h2.text.replace(' ', '')

    if i >= len(sections):
        continue

    if h2 in seactionsBlacklist:
        sections.pop(i)
        continue

    if i >= len(sections):
        break

    sections[i] = '<h2>' + sections[i]
    i += 1

html = bs("".join(sections), 'html.parser')

audios = {}

i = 1
for li in html.findAll('li'):
    # print(li.find(class_='audio-button'), not li.find(class_='audio=button'))
    if not li.find(class_='audio-button'):
        continue

    span = li.find('span')
    if span and not span['data-skin'] == 'Original':
        continue

    # print(span)

    source = li.find('source')
    if not source:
        continue

    source = source['src']
    text = li.find('i').text

    noSkin = True
    for skin in skinBlacklist:
        if champ + '_' + skin in source:
            noSkin = False

    if not noSkin:
        continue

    if not '"' in text:
        continue

    text = text.replace('"', '')

    audios[source] = text

    print(f"{i}. {text} - {source}")
    i += 1


download = True


def checkInput(print_=False):
    global download
    global audios
    if print_:
        i = 1
        for source, name in audios.items():
            print(f'{i}. {name} - {source}')
            i += 1

    print(
        f'\nTo download: {len(audios)} files\n------------------------------\n')
    print('Type numbers which you would like to remove from the download or hit enter to proceed.')
    remove = input()

    if remove == '':
        return

    if remove.startswith('skip'):
        download = False
        return

    if remove.startswith('max='):
        max = int(remove[4:])
        keys = list(audios.keys())

        if max >= len(keys):
            checkInput(True)
        else:
            tmp = {}
            for i in range(max):
                tmp[keys[i]] = audios[keys[i]]

            audios = tmp

    else:
        remove = sorted(remove.split(), key=int, reverse=True)

        for x in remove:
            audios.pop(list(audios.keys())[int(x) - 1])

    checkInput(True)


checkInput()

path = f'../LJSpeech-1.1/loltts/{champ}/'
tmpPath = path + 'tmp/'
savePath = path + 'wavs/'

os.makedirs(tmpPath, exist_ok=True)
os.makedirs(savePath, exist_ok=True)

num = 1
rows = []
wget.name = champ

for source, text in audios.items():
    fileName = champ + "-" + str(num).zfill(3)
    wget.number = num

    if download:
        wget.download(source, tmpPath + fileName + '.ogg')

        print(f'\nConverting {fileName}.ogg to {fileName}.wav...', end=' ')
        converter = subprocess.Popen(
            ['ffmpeg', '-i', f'{tmpPath + fileName}.ogg', '-ar', '22050', '-ac', '1', f'{savePath + fileName}.wav', '-y', '-loglevel', '0'], stdout=subprocess.PIPE)
        converter.communicate()[0]
        print(' COMPLETE')

    rows.append([f'{fileName}|{text}|{text}'])

    num += 1


num -= 1
if num < 105:
    missing = 105 - num
    for j in range(1, missing + 1):
        fileName = champ + '-' + str(num + j).zfill(3)
        print(fileName)
        shutil.copy(savePath + champ + '-' + str(j).zfill(3) + '.wav',
                    savePath + fileName + '.wav')
        key = list(audios.keys())[j]
        rows.append([f"{fileName}|'{audios[key]}'|'{audios[key]}'"])


csvFile = path + 'metadata.csv'
with open(csvFile, 'w') as f:
    writer = csv.writer(f)
    writer.writerows(rows)


for f in os.listdir(tmpPath):
    os.remove(os.path.join(tmpPath, f))
os.rmdir(tmpPath)
