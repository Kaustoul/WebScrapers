from concurrent.futures import process
import urllib.request as urllib2
from bs4 import BeautifulSoup, NavigableString, Tag
import json
import os.path
import re


def openFile(path):
    file = open(os.path.dirname(__file__) + path)
    return json.load(file)


def saveFile(path, jsonData):
    with open(os.path.dirname(__file__) + path, 'w') as outfile:
        outfile.write(json.dumps(jsonData, indent=4,
                      ensure_ascii=False).replace(" ", " "))


def getPage(page):
    try:
        c = urllib2.urlopen(page)
    except:
        print("Could not open %s" % page)

    return BeautifulSoup(c.read(), features="html.parser")


def getTextUntil(start, endTag):
    text = ""
    nextNode = start
    while True:
        nextNode = nextNode.nextSibling
        if nextNode is None:
            break
        if isinstance(nextNode, NavigableString):
            text += str(nextNode)
        if isinstance(nextNode, Tag):
            if nextNode.name == endTag:
                break
            text += str(nextNode)

    return BeautifulSoup(text, features="html.parser")


def races():
    races = {}
    blakclist = ["volba-rasy"]
    page = "http://dnd5esrd.d20.cz/prirucka-hrace/2-kapitola.html#hrdy-draci-rod"
    soup = getPage(page)

    # Look for races in h2
    for race in soup.findAll('h2'):
        id = race.get("id")
        if id in blakclist:
            continue

        text = getTextUntil(race, "h2")
        if text is None:
            continue

        # print(id)

        # Look for subraces in h3 - has to have "rysy"
        subrace = []
        for header in text.findAll("h4"):
            if header is None:
                continue
            if id == "clovek":
                continue

            subrace.append(header.contents[1])

        races[id] = {
            "name": race.contents[1],
            "subrace": subrace,
            "stats": {
                "speed": 6,
            },
            "languages": [],
        }
    return races


def spell_(url):
    spell = {}
    soup = getPage(url)
    content = soup.find(class_="main-content")
    spell['name'] = content.find(class_="page-title").find("span").contents[0]
    print(spell['name'])

    content = content.find(id="page-content")
    if content is None:
        print(f"No content for {spell['name']}!")
        return

    pars = content.findAll("p")
    for par in pars:
        if par.find("strong") is not None and par.find("strong").find("em") is not None and par.find("strong").find("em").contents[0].startswith("At Higher Levels"):
            spell['higherLvls'] = par.contents[1].strip()
            pars.remove(par)

    spell['source'] = pars[0].text.replace("Source: ", "").strip()

    split = pars[1].find("em").text.strip().split()
    match = re.search("[1-9]", split[0])
    if match:
        spell['lvl'] = match.group()
        spell['school'] = split[1].strip().lower()
    elif split[1] == "cantrip":
        spell['lvl'] = 0
        spell['school'] = split[0].strip().lower()
    else:
        print(f"Couldnt find level for spell {spell['name']}!")

    strong = pars[2].findAll("strong")
    spell['castTime'] = strong[0].nextSibling.strip()
    spell['range'] = strong[1].nextSibling.strip()
    spell['components'] = strong[2].nextSibling.strip().split()
    spell['duration'] = strong[3].nextSibling.strip()

    classArr = []
    classes = pars[len(pars) - 1].findAll("a")
    for class_ in classes:
        classArr.append(class_.contents[0].strip().lower())

    spell['class'] = classArr

    spell['description'] = ""
    for i in range(3, len(pars) - 1):
        spell['description'] += pars[i].text.strip() + "\n"

        lis = content.findAll("li")
        if lis is not None:
            for li in lis:
                spell['description'] += " - " + li.text + "\n"

    return spell


def spells():
    spells = {}
    page = "http://dnd5e.wikidot.com"
    soup = getPage(page + "/spells")

    for spell in soup.findAll("tr"):
        el = spell.find("a", href=True)
        if el is not None:
            spells[el['href'].replace(
                '-', '_').replace('/spell:', '')] = spell_(page + el['href'])

    return spells


def toNumber(str):
    num = ""
    for ch in str:
        if ch.isdigit():
            num += ch
    return int(num) if len(num) > 0 else "-"


def formatName(name):
    return name.replace(" (", "(").replace(" - ", "-").replace(" ", "_").replace("'", "").lower()


def itemSection(soup, sectionName, items, headers=None):
    if headers is None:
        headers = soup.findAll("th", colspan=False)
    count = 0
    blacklist = ["Common Item", "Equipment Pack", "Usable Items", "Clothes", "Arcane Focus", "Druidic Focus", "Holy Symbols",
                 "Containers", "Name", "Ammunition", "Property", "Simple Melee Weapons", "Martial Melee Weapons", "Simple Ranged Weapons",
                 "Martial Ranged Weapons", "Category", "Tool Set"]

    if sectionName not in items.keys():
        items[sectionName] = {}

    for row in soup.findAll("tr"):
        columns = row.findAll("td")
        if len(columns) == 0:
            continue

        itemObj = {}
        for item in columns:
            if item.find("a") is not None:
                item = item.find("a")
            if headers[count].contents[0] is None or headers[count].contents[0] == "":
                continue

            head = "name" if headers[count].contents[0] in blacklist else headers[count].contents[0]
            head = formatName(head)

            if head == "weight" or head == "cost":
                itemObj[head] = toNumber(item.contents[0])
            else:
                itemObj[head] = item.contents[0]

            if item.find("em") is not None:
                itemObj["description"] = item.find("em").contents[0]

            count = (count + 1) % len(headers)

        print("    " + itemObj["name"])
        if type(itemObj["name"]) is Tag:
            itemObj["name"] = item.contents[0].contents[0]

        if (itemObj["name"] == "Rope"):
            continue
        try:
            items[sectionName][formatName(itemObj["name"])] = itemObj
        except:
            print(itemObj)
            exit()

    return items


def toolsSection(soup, items):
    table = soup.find("table")

    headers = table.findAll("th")
    rows = table.findAll("tr")
    heads = []
    for i in range(3):
        heads.append(headers[i])

    stack = BeautifulSoup("", 'html.parser')

    sectionName = ""
    for row in rows:
        th = row.find("th")
        if th is not None:
            section = th.contents[0]
            if section in heads:
                continue

            if stack.find("tr") is not None:
                print("  " + sectionName)
                items = itemSection(stack, sectionName, items, heads)
                stack = BeautifulSoup("", 'html.parser')

            sectionName = section
            continue

        stack.append(row)

    print("  " + sectionName)
    items = itemSection(stack, sectionName, items, heads)
    return items


def itemGroup(soup, items, includeH2=False):
    h1s = soup.findAll("h1", id=True)
    tbodies = soup.findAll("table")
    blacklist = ["DND 5th Edition", "Site Navigation",
                 "Create a Page", "community wiki", "Other interesting sites", "Proficiency"]

    if (h1s is not None):
        count = 0
        if includeH2:
            for h2 in soup.findAll("h2"):
                if h2 is not None and h2.contents[0] not in blacklist:
                    section = h2.find("span").contents[0]
                    if section in blacklist:
                        continue

                    print("  " + formatName(section))
                    items = itemSection(
                        tbodies[count], formatName(section), items)
                    count += 1

        for h1 in h1s:
            if h1 is not None and h1.contents[0] not in blacklist:
                section = h1.find("span").contents[0]
                if section in blacklist:
                    continue

                print("  " + formatName(section))
                items = itemSection(
                    tbodies[count], formatName(section), items)
                count += 1
    else:
        print("  " + formatName(h1.find("span").contents[0]))
        items = itemSection(soup.find("tbody"), formatName(
            soup.find("h2").strip()), items)

    return items


def items():
    items = {}
    page = "http://dnd5e.wikidot.com/"
    soup = getPage(page)
    blacklist = ["/wondrous-items", "/currency",
                 "/siege-equipment", "/firearms"]

    processH2 = ["/armor"]

    for itemGroup_ in soup.find(id="toc76").find_next_sibling().findAll("a", href=True):
        link = itemGroup_['href']
        if link in blacklist:
            continue

        print(link)
        if link == "/tools":
            toolsSection(getPage(page + itemGroup_['href']), items)
        itemGroup(getPage(page + itemGroup_['href']), items, link in processH2)

    return items


def main():
    # spell_("http://dnd5e.wikidot.com" + "/spell:encode-thoughts")
    itemJson = items()
    saveFile("/../data/gameData/generated/items.json", itemJson)


if __name__ == "__main__":
    main()
