from asyncio import gather, run, sleep as async_sleep, set_event_loop_policy, \
    WindowsSelectorEventLoopPolicy, new_event_loop, create_task, run_coroutine_threadsafe
from datetime import datetime, timedelta, timezone
from statistics import median
from os import system
from sys import exit
from browsercookie3 import chrome
from tabulate import tabulate
from colorama import init, Fore
from win10toast_persist import ToastNotifier
from aiohttp import ClientSession, TCPConnector
from aioconsole import ainput
import discord
import aiofiles


class item:
    def __init__(self, ID, info_url, history_url, refine, prop, alert):
        self.ID = ID
        self.info_url = info_url
        self.history_url = history_url
        self.alert = alert
        self.refine = refine
        self.prop = prop
        self.med = -1
        self.long_med = -1


async def Login():
    print(Fore.LIGHTGREEN_EX + "Login in Progress...")
    cjs, cookies, usernames = [], [], []

    profile = 'Default'
    for i in range(10):
        try:
            cj = chrome(domain_name='novaragnarok.com', profile=profile)
            if cj:
                cjs.append(cj)
        except:
            pass
        profile = 'Profile ' + str(i)

    if not cjs:
        await Read_error(Fore.LIGHTRED_EX + "Chrome Cookies Not Found!")

    for each in cjs:
        cookies.append({"fluxSessionData": each._cookies['www.novaragnarok.com']['/']['fluxSessionData'].value})

    logins = await gather(*(Network_session(['https://novaragnarok.com'], cookie) for cookie in cookies))

    if discord_channel:
        print(Fore.LIGHTGREEN_EX + "Discord Connected!")
    else:
        print(Fore.LIGHTRED_EX + "Discord NOT Connected!")

    i = 0
    while i < len(cookies):
        try:
            username = logins[i][0].split("</strong>", 1)[0].rsplit(">", 1)[1]
            if '\\n' not in username and username not in usernames:
                print(username + Fore.LIGHTGREEN_EX + " Online!")
                usernames.append(username)
                i += 1
            else:
                del cookies[i]
        except:
            del cookies[i]
    if not i:
        await Read_error('No Account Found!')

    await async_sleep(2)
    return cookies


async def Read_info():
    # Read Settings
    remove, median_interval, median_filter = 1, 15, 0
    try:
        async with aiofiles.open('Files/Settings.txt', 'r') as f:
            async for line in f:
                if 'Median Cache Interval' in line:
                    median_interval = int(line.replace(' ', '').strip('\n').split('=')[1])
                if 'Median Filter' in line:
                    median_filter = int(line.replace(' ', '').replace('.', '').strip('\n').split('=')[1])
                if 'Median Cache Date' in line:
                    line = line.replace(' ', '').strip('\n').split('=')[1]
                    remove = await Date(line, median_interval, 1)
    except:
        await Read_error('Settings Error!')

    # Get file data and remove Medians_cache if old
    if not remove:
        today = datetime.utcnow() - timedelta(hours=7)
        today = today.replace(tzinfo=timezone.utc)
        async with aiofiles.open('Files/Medians_refresh.txt', 'w+') as f:
            await f.write(str(today.day) + '-' + str(today.month) + '-' + str(today.year))
        async with aiofiles.open('Files/Medians_cache.txt', 'w+'):
            pass

    # Read IDs
    items = []
    try:
        blacklist = set(open('Files/Blacklist.txt'))
    except:
        await Read_error('Blacklist Error!')

    try:
        async with aiofiles.open('Files/ID.txt', 'r') as f:
            async for line in f:
                if line.replace(' ', '') != '\n':
                    ID = line.strip('\n').split(';')[0].replace(' ', '')
                    if ID + '\n' not in blacklist:
                        items.append(item
                        (ID,
                         "https://www.novaragnarok.com/?module=vending&action=item&id=" + ID,
                         "https://www.novaragnarok.com/?module=vending&action=itemhistory&id=" + ID,
                         int(line.split(';')[1].replace(' ', '')),
                         [each.strip() for each in line.split(';')[2].split(',')],
                         int(line.split(';')[3].split('#')[0].replace('.', '').replace(',', '').replace(' ', '').replace('\n', '')),
                        ))
    except:
        await Read_error('ID Error!')

    # Read Medians_cache and write to a Dict
    medians_cache = {}
    try:
        async with aiofiles.open('Files/Medians_cache.txt', 'r') as f:
            async for line in f:
                if line.replace(' ', '') != '\n':
                    key, value = line.strip('\n').split(':')[0], line.strip('\n').split(':')[1].split(' ')
                    medians_cache[key] = list(value)
    except:
        await Read_error('Medians_cache Error!')

    # Find med in dict
    for each in items:
        key = str(each.ID) + ' ' + str(each.refine)
        if 'None' not in each.prop:
            each.med = 0
            each.long_med = 0
            each.history_url = 0
        else:
            if key in medians_cache:
                each.med, each.long_med = int(medians_cache[key][0]), int(medians_cache[key][1])
                each.history_url = 0  # Skip Network History Search

    # Delete from Network search if median is low
    i = 0
    while i < len(items):
        if items[i].med != -1 and 'None' in items[i].prop and items[i].med < median_filter and items[i].long_med < median_filter:
            del items[i]
        else:
             i += 1

    return items


async def Network(items, cookie, run):
    info, history, htmls = [], [], []
    count = {'each': 1, 'total': len(items)}

    # Search for Available Now Market Info
    for each in items:
        info.append(each.info_url)

    htmls = await Network_session(info, cookie, count)

    for i, html in enumerate(htmls):
        items[i].info_html = html

    i = 0
    while i < len(items):
        if not items[i].info_html:
            del items[i]
        else:
            i += 1

    # Seach for History Info
    if not run:
        await Delete_unknown(items)  # Delete and add Unknows to Blacklist

        for each in items:
            history.append(each.history_url)

        htmls = await Network_session(history, cookie, count)

        for i, html in enumerate(htmls):
            items[i].history_html = html

        i = 0
        while i < len(items):
            if not items[i].history_html:
                del items[i]
            else:
                i += 1


async def Network_session(search, cookie, count=None):
    async with ClientSession(cookies=cookie, connector=TCPConnector(limit=10)) as session:
        htmls = await gather(*[Network_get(each, session, count) for each in search])
    return htmls


async def Network_get(url, session, count=None):
    retry = 0
    if url:  # Skip history search if already has med
        while True and retry < 3:
            try:
                async with session.get(url, timeout=5) as response:
                    if response.status == 200:
                        if count:
                            print(('\x1b[2K' + Fore.LIGHTGREEN_EX + 'Searched: ' + str(count['each']) + '/' + str(count['total'])), end='\r')
                            count['each'] += 1
                        return str(await response.content.read())
                    retry += 1
                    await async_sleep(1)
            except:
                retry += 1
                await async_sleep(1)

        print(Fore.LIGHTRED_EX + "Internet or Server Offline")
        await ainput("\nPress any button to exit")
        exit(0)
    return 1


async def Delete_unknown(items):
    try:
        blacklist = set(open('Files/Blacklist.txt'))
        async with aiofiles.open('Files/Blacklist.txt', 'a+') as f:
            i = 0
            while i < len(items):
                if items[i].info_html:
                    items[i].name = items[i].info_html.split('"item-name">')[1].split('<')[0]
                    if items[i].name == 'Unknown':
                        if items[i].ID not in blacklist:
                            await f.write(items[i].ID + '\n')
                            blacklist.add(items[i].ID)
                        del items[i]
                    else:
                        i += 1
                else:
                    i += 1
    except:
        await Read_error('Blacklist Error!')


async def History(items):
    medians_cache, settings = {}, {}

    # Bring files to memory
    try:
        async with aiofiles.open('Files/Medians_cache.txt', 'r') as f:
            async for line in f:
                if line.replace(' ', '') != '\n':
                    key, value = line.strip('\n').split(':')[0], line.strip('\n').split(':')[1]
                    medians_cache[key] = value
    except:
        await Read_error('Medians_cache Error!')

    try:
        async with aiofiles.open('Files/Settings.txt', 'r') as f:
            async for line in f:
                if 'Short Median Days' in line:
                    value = line.replace(' ', '').strip('\n').split('=')[1]
                    settings['SM'] = int(value)
                if 'Long Median Days' in line:
                    value = line.replace(' ', '').strip('\n').split('=')[1]
                    settings['LM'] = int(value)
    except:
        await Read_error('Settings Error!')

    # Calculate Medians
    try:
        async with aiofiles.open('Files/Medians_cache.txt', 'a+') as f:
            for each in items:
                if each.med == -1:  # If doesn't has median calculated
                    each.med, each.long_med = await Median(each.history_html, each.refine, settings)
                    key = str(each.ID) + ' ' + str(each.refine)
                    if key not in medians_cache:
                        await f.write(key + ':' + str(each.med) + ' ' + str(each.long_med) + '\n')
                        medians_cache[each.ID] = [each.med, each.long_med]
    except:
        await Read_error('Medians_cache Error!')


async def Median(history, refine, settings):
    med, long_med = [], []
    property_exist = history.find('<th>Additional Properties</th>')
    find_price = history.split('</span>z')
    size = len(find_price)-2
    smed_range, lmed_range = 15, 60

    try:
        smed_range = settings['SM']
        lmed_range = settings['LM']
    except:
        pass

    i = 0
    # Refine column missing
    if history.find('>Refine</th>') == -1:
        while i < size and await Date(find_price[i].rsplit(' - ', 1)[0].rsplit(">", 1)[1].split('/'), lmed_range):
            if property_exist == -1 or find_price[i+1].split('</tr>')[0].find('None') != -1:  # Med only Property None
                long_med.append(int(find_price[i].rsplit('>', 1)[-1].replace(',', '')))
                if await Date(find_price[i].rsplit(' - ', 1)[0].rsplit(">", 1)[1].split('/'), smed_range):
                    med.append(int(find_price[i].rsplit('>', 1)[-1].replace(',', '')))
            i += 1

    # Refine column present
    else:
        while i < size and await Date(find_price[i].rsplit(' - ', 1)[0].rsplit(">", 1)[1].split('/'), lmed_range):
            item_refine = int(find_price[i+1].split('data-order="')[1].split('"')[0])
            if item_refine == refine:
                if property_exist == -1 or find_price[i+1].split('sorting_1')[0].find('None') != -1:  # Med only Property None
                    long_med.append(int(find_price[i].rsplit('>', 1)[-1].replace(',', '')))
                    if await Date(find_price[i].rsplit(' - ', 1)[0].rsplit(">", 1)[1].split('/'), smed_range):
                        med.append(int(find_price[i].rsplit('>', 1)[-1].replace(',', '')))
            i += 1

    if med and long_med:
        return round(median(med)), round(median(long_med))
    elif med and not long_med:
        return round(median(med)), 0
    elif not med and long_med:
        return 0, round(median(long_med))
    elif not med and not long_med:
        return 0, 0


async def Date(date, interval, *args, check=None):
    today = datetime.utcnow() - timedelta(hours=7)
    today = today.replace(tzinfo=timezone.utc)

    if not args:
        date = date[1] + '-' + date[0] + '-' + '20' + date[2]
        date = datetime.strptime(date, "%d-%m-%Y")
        time = today - timedelta(days=date.day)
    elif 1 in args:
        date = datetime.strptime(date, "%d-%m-%Y")
        time = today - timedelta(days=date.day)
    elif 3 in args:
        date1 = date.replace(' ', '').split('-')[0].split('/')
        date2 = date.replace(' ', '').split('-')[1].split(':')
        date1[2] = '20' + date1[2]
        date = date1[2] + '-' + date1[0] + '-' + date1[1] + '-' + date2[0] + '-' + date2[1]
        date = datetime.strptime(date, "%Y-%m-%d-%H-%M")
        date = date.replace(tzinfo=timezone.utc)

        if date >= check:
            return 1  # sold
        else:
            return 0  # old

    if time.day < interval:
        return 1
    else:
        return 0


async def Sorting(items):
    for each in items:
        each.format_refine = each.refine
        pos = await Price_search(each)

        # Nothing found in market
        if pos == -1:
            each.format_id = Fore.LIGHTBLACK_EX + each.ID
            each.format_name = Fore.LIGHTBLACK_EX + each.name
            each.format_refine = Fore.LIGHTBLACK_EX + '+' + str(each.refine)
            each.format_prop = Fore.LIGHTBLACK_EX + ', '.join(each.prop)
            each.format_price = Fore.LIGHTBLACK_EX + '0z'
            each.format_med = Fore.LIGHTBLACK_EX + format(each.med, ',d') + 'z'
            each.format_long_med = Fore.LIGHTBLACK_EX + format(each.long_med, ',d') + 'z'
            each.med_porc = Fore.LIGHTBLACK_EX + '0%'
            each.long_med_porc = Fore.LIGHTBLACK_EX + '0%'
            each.format_alert = Fore.LIGHTBLACK_EX + format((each.alert), ',d') + 'z'
            each.format_place = Fore.RED + 'NOT AVAILABLE'
            each.ea = Fore.LIGHTBLACK_EX + '0'
            each.minor_ea = Fore.LIGHTBLACK_EX + '0'
            each.cheap = Fore.LIGHTBLACK_EX + '0/0'
            each.price = 0

        # Found something
        else:
            each.format_id = each.ID
            each.format_name = each.name
            each.format_prop = ', '.join(each.prop)
            each.format_price = format(each.price, ',d') + 'z'
            each.format_med = format(each.med, ',d') + 'z'
            each.format_long_med = format(each.long_med, ',d') + 'z'
            each.format_alert = format(each.alert, ',d') + 'z'
            await Place(each, pos)
            each.format_place = each.place
            await Porcentage(each)

            if each.format_long_med == '0z':
                each.format_long_med = Fore.LIGHTBLACK_EX + each.format_long_med
            if each.format_med == '0z':
                each.format_med = Fore.LIGHTBLACK_EX + each.format_med


async def Price_search(item):
    find_price_refine = item.info_html.split('</span>z')
    prop_column = item.info_html.find('Additional Properties')
    info = {'cheap_total': 0, 'cheapest_total': 0, 'minor_price': 10000000000, 'pos': -1}
    minor_refine = item.refine

    # Check if Market Available
    try:
        refine_exist = item.info_html.split('</span>z')[1].split('text-align:')[1].split(';')[0]
    except:
        return -1

    i = total = 0
    if refine_exist == 'center':  # Refinable
        while i < len(find_price_refine)-1:
            refine = int(find_price_refine[i+1].split('data-order="')[1].split('"')[0])
            if refine >= item.refine:
                if await Property_exists(prop_column, item, find_price_refine[i+1]):
                    await Lowest_price(find_price_refine[i], find_price_refine[i+1], item.med, i, info)
                    total += 1
            i += 1

        if minor_refine > item.refine:  # Explicit if displayed refine if is higher than user's refine inserted
            item.format_refine = Fore.LIGHTBLACK_EX + '+' + str(item.refine) + " -> " + Fore.LIGHTWHITE_EX + '+' + str(minor_refine)
        else:
            item.format_refine = '+' + str(minor_refine)

    elif refine_exist == 'right' and item.refine == 0:  # Not Refinable
        while i < len(find_price_refine)-1:
            if await Property_exists(prop_column, item, find_price_refine[i+1]):
                await Lowest_price(find_price_refine[i], find_price_refine[i+1], item.med, i, info)
                total += 1
            i += 1
        item.format_refine = '+0'

    item.price = info['minor_price']
    item.cheap = str(info['cheapest_total']) + '/' + str(info['cheap_total'])
    item.ea = str(total)
    return info['pos']


async def Lowest_price(find_price_refine, find_price_refine_next, med, i, info):
    price = int(find_price_refine.rsplit('>', 1)[-1].replace(',', ''))
    try:
        ea = int(find_price_refine_next.split('<td style')[0].split(' ea.')[0].rsplit(' ')[-1])
    except:
        ea = 1
    if price <= med:  # Cheap
        info['cheap_total'] += ea
        if price == info['minor_price']:
            info['cheapest_total'] += ea
        elif price < info['minor_price']:
            info['pos'] = i
            info['minor_price'] = price
            info['cheapest_total'] = ea
    else:  # Expensive
        if price < info['minor_price']:
            info['pos'] = i
            info['minor_price'] = price


async def Property_exists(prop_column, item, find_price_refine):
    # No Property Column
    if prop_column == -1:
        if 'None' not in item.prop:
            return 0

    # Property Column
    else:
        d = {}
        for each in item.prop:
            if each not in d.keys():  # It is not a duplicate property
                i = find_price_refine.split('span class', 1)[0].find(each)
                if i != -1:
                    d[each] = i
                else:
                    return 0

            else:  # Duplicate property, search after last one
                i = find_price_refine.split('span class', 1)[0][d[each] + 1: -1].find(each)
                if i != -1:
                    pass
                else:
                    return 0
    return 1


async def Porcentage(item):
    if item.long_med > 0:
        if item.long_med >= item.price:
            item.long_med_porc = Fore.LIGHTGREEN_EX + '-' + str(abs(int(100-(item.price/item.long_med)*100))) + '%'
        else:
            item.long_med_porc = Fore.LIGHTRED_EX + '+' + str(abs(int(100-(item.price/item.long_med)*100))) + '%'
    else:
        item.long_med_porc = Fore.LIGHTBLACK_EX + '0%'

    if item.med > 0:
        if item.med >= item.price:
            item.med_porc = Fore.LIGHTGREEN_EX + '-' + str(abs(int(100-(item.price/item.med)*100))) + '%'
        else:
            item.med_porc = Fore.LIGHTRED_EX + '+' + str(abs(int(100-(item.price/item.med)*100))) + '%'
    else:
        item.med_porc = Fore.LIGHTBLACK_EX + '0%'


async def Place(item, pos):
    find_place = item.info_html.split("data-map=")
    places = find_place[pos+1].replace(' ', '').split("</span>")[0].split(">")[1].split(',')
    item.place = (places[0] + '[' + places[1] + ',' + places[2] + ']').replace('\\n', '')


async def Sold_notification(cookies, sell_price):
    now = datetime.utcnow() - timedelta(hours=7)
    now = now.replace(second=0, microsecond=0, tzinfo=timezone.utc)
    j, k, htmls = [0] * len(cookies), [0] * len(cookies), []

    while True:
        i = back = profile = found = 0
        htmls = []
        for i in range(len(cookies)):
            htmls.append(await Network_session(['https://www.novaragnarok.com/?module=account&action=sellinghistory'], cookies[i]))
        i = 0
        while profile < len(cookies):
            try:
                start = htmls[profile][0].rsplit('Selling History', 1)[1].split('data-order', i + 1)[i + 1]
                date = start.split('</td>', 1)[0].rsplit('>', 1)[1]
                name = start.split('</a>', 1)[0].rsplit('\\n', 1)[1].replace('\\t', '').replace('\\', '').lstrip(' ')
                prop = start.split('data-order', 1)[1].split('>', 1)[1].split('<', 1)[0]
                ea = start.split('data-order', 1)[1].split('<td>', 1)[1].split('</td>', 1)[0]
                # ea_price = start.split('</span>z', 1)[0].rsplit('>', 1)[1]
                price = start.split('</span>z', 2)[1].rsplit('>', 1)[1]
                if await Date(date, 0, 3, check=now):  # Check if item time is newer than program start time
                    if not back:  # First count all new items since program start running
                        j[profile] += 1
                        i += 4  # Next item 4 'data-orders' ahead
                        continue
                if found:
                    k[profile] += 1
                    if int(price.replace(',', '')) >= (sell_price * 0.97):
                        await Windows_toast(name, prop, price, ea=ea)
                        if discord_channel:
                            run_coroutine_threadsafe(Discord_toast(name, prop, price, ea=ea), discord_loop)
                    if j[profile] == k[profile]:
                        found = 0

                if j[profile] > k[profile]:
                    k[profile] += 1
                    if not found:
                        found, back, i = 1, 1, 0
                    else:
                        i += 4
                    continue
            except IndexError:  # Maybe player have not sell anything in game yet
                pass
            j[profile] = 0
            back = found = 0
            profile += 1
            await async_sleep(15)


async def Cheap_notification(items, notify):
    for each in items:
        if each.price and (each.alert >= each.price):
            try:
                if each.refine not in notify[each.ID]:
                    await Windows_toast(each.name, each.prop, each.price, each.refine, each.place)
                    notify[each.ID] = [each.refine]
                    if discord_channel:
                        run_coroutine_threadsafe(Discord_toast(each.name, each.refine, each.prop, each.price, each.place, each.info_url), discord_loop)
            except:
                await Windows_toast(each.name, each.prop, each.price, each.refine, each.place)
                notify[each.ID] = [each.refine]
                if discord_channel:
                    run_coroutine_threadsafe(Discord_toast(each.name, each.prop, each.price, each.refine, each.place, each.info_url), discord_loop)

            each.format_id = Fore.LIGHTGREEN_EX + each.ID  # ID green if notified
            each.format_place = Fore.LIGHTGREEN_EX + each.place  # Location green if notified


async def Windows_toast(name, prop, price, refine=None, place=None, ea=None):
    my_toast = ToastNotifier()
    if not ea:
        msg = ("+" + str(refine) + ' ' + name + '\nProp: ' + ', '.join(prop) + ' \n\n' + format(price, ',d')
               + 'z | ' + place)
    else:  # Sold
        msg = ea + 'x ' + name + '\nProp: ' + prop + '\n\nSold: ' + price + 'z'

    my_toast.show_toast("NovaMarket", msg, threaded=True, icon_path='Files/icon.ico', duration=None)
    await async_sleep(0.1)


async def Discord_toast(name, prop, price, refine=None, place=None, url=None, ea=None):
    if not ea:
        msg = "Price Reached!\nItem: " + "+" + str(refine) + ' ' + name + '\nProp: ' + ', '.join(prop) + \
              '\nLocation: ' + place + '\nPrice: ' + format(price, ',d') + 'z' + '\n' + url
    else:  # Sold
        msg = ea + 'x ' + name + '\nProp: ' + prop + '\nSold for: ' + price + 'z'

    await discord_user.send(msg)
    # await discord_channel.send(discord_user.name + '#' + discord_user.discriminator + '\n' + msg)


async def MakeTable(items):
    table, t = [], ['ID', 'NAME', 'EA', 'CHEAP', 'REF', 'PROP', 'PRICE', 'SHORT MED', 'LONG MED', 'SM%', 'LM%', 'ALERT', 'LOCATION']

    for each in items:
        table.append([Fore.LIGHTWHITE_EX + each.format_id,
                     Fore.LIGHTCYAN_EX + each.format_name,
                     Fore.LIGHTWHITE_EX + each.ea,
                     Fore.LIGHTWHITE_EX + each.cheap,
                     Fore.LIGHTWHITE_EX + each.format_refine,
                     Fore.WHITE + each.format_prop,
                     Fore.LIGHTMAGENTA_EX + each.format_price,
                     Fore.LIGHTYELLOW_EX + each.format_med,
                     Fore.LIGHTYELLOW_EX + each.format_long_med,
                     each.med_porc,
                     each.long_med_porc,
                     Fore.CYAN + each.format_alert,
                     Fore.LIGHTBLUE_EX + each.format_place + Fore.LIGHTWHITE_EX])

    table.sort(key=TableSort, reverse=True)
    system('cls')
    print(tabulate(table, headers=t, tablefmt='fancy_grid'))


def TableSort(val):
    return int(val[9].split('m')[1].split('%')[0]), val[12].split('m')[2].split('"\"')


async def Timer(t):
    while(t.timer):
        print('\x1b[2K' + Fore.LIGHTGREEN_EX + "Next Refresh(" + str(t.refresh+1) + "): " + 
                str(t.timer) + ' sec' + "\t\t(Force Refresh: Enter / Pause: Left Click / Resume: Right Click)", end='\r')
        t.timer -= 1
        await async_sleep(1)
        if t.timer <= 0:
            t.refresh += 1
            break

async def Input(t):
    while True:
        msg = await ainput()
        if t.timer and '' in msg:
            t.timer = 0
            
async def Read_error(msg):
    system('cls')
    print(Fore.LIGHTRED_EX + msg)
    await ainput("\nPress any button to exit")
    exit(0)

async def Main():
    notify = {}
    t = type('Async_variables', (), {})()
    run, t.inputs, t.refresh, t.timer = 0, 0, 0, 0
   
    #Read Files
    
    async with aiofiles.open('Files/Settings.txt', 'r') as f:
        async for line in f:
            if 'Refresh Time Interval' in line:
                timer_interval = int(line.replace(' ', '').strip('\n').split('=')[1])
                break
            else:
                timer_interval = 180
    async with aiofiles.open('Files/Settings.txt', 'r') as f:
        async for line in f:
            try:
                if 'Minimum Sell Notification Price' in line:
                    sell_price = int(line.replace(' ', '').replace('.', '').strip('\n').split('=')[1])
                    break
            except:
                sell_price = 0
                break
   
    cookies = await Login()
    items = await Read_info()

    #Loop
    while True:
        await Network(items, cookies[0], run)
        if not run: 
            await History(items)
            create_task(Input(t))
            create_task(Sold_notification(cookies, sell_price))
            run = 1
        await Sorting(items) 
        await Cheap_notification(items, notify)
        await MakeTable(items)
        t.timer = timer_interval
        await Timer(t)

init(autoreset=True)
#set_event_loop_policy(WindowsSelectorEventLoopPolicy())
discord_user = discord_channel = discord_bot = confirm = 0
discord_loop = new_event_loop()
client = discord.Client(loop=discord_loop)
my_toast = ToastNotifier()

"EDIT THESE LINES TO ENABLE YOUR OWN BOT:"

bot_id = 0
channel_id = 0
token = ''

"EDIT LINES END"

@client.event
async def on_ready():
    global discord_user, discord_channel, discord_bot
    async with aiofiles.open('Files/Settings.txt', 'r') as f:
        async for line in f:
            if 'Discord ID' in line:
                username = (line.replace(' ', '').strip('\n').split('=')[1])
                break
        
    try:
        discord_user = client.get_user(int(username))
        discord_bot = client.get_user(bot_id)
    except:
        await client.close()
        return
    
    discord_channel = client.get_channel(channel_id)

    try:
        msg = await discord_user.history(limit=1).flatten()
    except:
	    print(Fore.LIGHTRED_EX + "Send a DM to NovaNotifier Bot!")

    try:
        if msg[0].content != discord_user.name + '#' + discord_user.discriminator + '\nConfirm? (y/n)':
            await discord_user.send(discord_user.name + '#' + discord_user.discriminator + '\nConfirm? (y/n)')
        else:
            print(Fore.LIGHTRED_EX + "Reply Last Discord Message!")
            return
    except:
        await discord_user.send(discord_user.name + '#' + discord_user.discriminator + '\nConfirm? (y/n)')
        
@client.event
async def on_message(message):
    global discord_channel, confirm
    if message.author.id == discord_bot.id: 
        if message.content == discord_user.name + '#' + discord_user.discriminator + '\nConfirm? (y/n)' and not confirm:
            confirm = 1
    if message.author.id == discord_user.id:
        if confirm:
            if message.content == 'y':
                msg = await discord_user.history(limit=1).flatten()
                if msg[0].content != discord_user.name + '#' + discord_user.discriminator + '\nConfirm? (y/n)':
                    discord_channel = client.get_channel(716582786953117729) 
                    confirm = 0
                    await discord_user.send('Confirmed!')
                    create_task(Main())
            else:
                await discord_user.send('Not Confirmed!')
                await client.close()
    
    if message.content == '!clear':
        if message.author.id == discord_user.id:
            await discord_channel.purge(limit=None)
            async for msg in discord_user.history():
                if msg.author.id == discord_bot.id:
                    await msg.delete()
    if message.content == '!help':
        if message.author.id == discord_user.id:
            await discord_user.send('!clear = Delete bot messages')
             
print(Fore.LIGHTGREEN_EX + "Initializing...")
try:
    client.run(token)
except Exception as e:
    print(Fore.LIGHTRED_EX + "Discord Error!", e)
    
run(Main()) #No Discord 
