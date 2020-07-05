from asyncio import gather, Semaphore, run, sleep as async_sleep, set_event_loop_policy, \
    WindowsSelectorEventLoopPolicy, new_event_loop, create_task, run_coroutine_threadsafe, get_event_loop, \
    wait_for
from datetime import datetime, timedelta, timezone
from statistics import median
from os import system
from sys import exit
from browser_cookie3 import chrome, firefox
from tabulate import tabulate
from win10toast_persist import ToastNotifier
from aiohttp import ClientSession
import aiofiles

"""
Tester Bot:
https://discord.com/api/oauth2/authorize?client_id=719077381754847232&permissions=8&scope=bot
"""
set_event_loop_policy(WindowsSelectorEventLoopPolicy())

class Login():
    
    def __init__(self):
        self.cookies, self.usernames = run(self.login())

    async def login(self):
        cjs, cookies, usernames = [], [], []
        profile = 'Default'
        
        for i in range(10):
            try:
                cj = chrome(domain_name='novaragnarok.com', profile=profile)
                if cj:
                    cjs.append(cj)
            except:
                pass
            profile = f'Profile {i}'

        if not cjs:
            return 

        for each in cjs:
            cookies.append({"fluxSessionData": each._cookies['www.novaragnarok.com']['/']['fluxSessionData'].value})

        login = await gather(*(Network().network_session(['https://novaragnarok.com'], cookie) for cookie in cookies))
        
        i = 0
        while i < len(login):
            try:
                username = login[i][0].split("</strong>", 1)[0].rsplit(">", 1)[1]
                if '\\n' not in username and username not in usernames:
                    usernames.append(username)
                    i += 1
                else:
                    del cookies[i]
            except Exception as e:
                print(e)
                del cookies[i]

        return cookies, usernames

class Read_settings_file():

    def __init__(self):
        self.median_filter = self.sell_price = 0 
        self.timer_interval = 180 
        self.settings = {}
        self.settings['SM'] = 15
        self.settings['LM'] = 60
        run(self.read_settings())

    async def read_settings(self):
       
        async with aiofiles.open('Files/Settings.txt', 'r') as f:
            async for line in f:
                if 'Median Filter' in line:
                    self.median_filter = int(line.split('=')[1].replace('.', '').strip(' ').strip())
                elif 'Refresh Time Interval' in line:
                    self.timer_interval = int(line.split('=')[1].strip(' ').strip())
                elif 'Minimum Sell Notification Price' in line:
                    self.sell_price = int(line.split('=')[1].replace('.', '').strip(' ').strip())
                elif 'Short Median Days' in line:
                    value = line.split('=')[1].strip(' ').strip()
                    self.settings['SM'] = int(value)
                elif 'Long Median Days' in line:
                    value = line.split('=')[1].strip(' ').strip()
                    self.settings['LM'] = int(value)
        
class Read_id_file():

    def __init__(self):
        self.items = run(self.read_id())

    class Item:
        def __init__(self, ID, url, history_url, refine, prop, alert):
            self.ID = ID
            self.url = url
            self.history_url = history_url
            self.alert = alert
            self.refine = refine
            self.prop = prop
            self.med = None
            self.long_med = None
            
    async def read_id(self):
        items = []
        blacklist = set(open('Files/Blacklist.txt'))
        async with aiofiles.open('Files/ID.txt', 'r') as f:
            async for line in f:
                if line.strip(' ') != '\n':
                    ID = line.split(';')[0].strip(' ')
                    if ID + '\n' not in blacklist:
                        items.append(self.Item(
                            ID,
                            "https://www.novaragnarok.com/?module=vending&action=item&id=" + ID,
                            "https://www.novaragnarok.com/?module=vending&action=itemhistory&id=" + ID,
                            int(line.split(';')[1].strip(' ')),
                            [each.strip() for each in line.split(';')[2].split(',')],
                            int(line.split(';')[3].split('#')[0].replace('.', '')
                                .strip(' ').strip()),
                        ))
        return items

class Read_medians_file():

    def __init__(self, items):
        self.medians_cache = {}
        run(self.set_cache(items))

    async def set_cache(self, items):
        medians_cache = {}
        async with aiofiles.open('Files/Medians_cache.txt', 'r') as f:
            async for line in f:
                if line.strip(' ') != '\n':
                    key, value = line.split(':')[0], line.split(':')[1].strip().split(' ')
                    medians_cache[key] = list(value)
            self.medians_cache = medians_cache

        for each in items:
            key = f'{each.ID} {each.refine}'
            if key in medians_cache and 'None' in each.prop:
                each.med, each.long_med = int(medians_cache[key][0]), int(medians_cache[key][1])
                
class Network():
    
    def items_network(self, items, cookie, args=None):
        """
        Args True = Market Now
        Args False = Transaction History 
        Args None = Both 
        """

        #count = {'each': 1, 'total': len(items)}

        if args or args is None:
            info = []
            for each in items:
                info.append(each.url)
            htmls = run(self.network_session(info, cookie))

            i = 0
            for html in htmls:
                if html:
                    items[i].info_html = html
                    i += 1
                else:
                    del items[i]
            run(self.delete_unknown(items))

        if not args:
            info = []
            for each in items:
                if each.long_med is None:
                    info.append(each.history_url)
                else:
                    info.append(False)
            htmls = run(self.network_session(info, cookie))

            i = 0
            for html in htmls:
                if html:
                    items[i].history_html = html
                    i += 1
                else:
                    del items[i]

    async def network_session(self, search, cookie):
        sem = Semaphore(10)

        async with ClientSession(cookies=cookie) as session:
            htmls = await gather(*[self.network_sem(sem, self.network_get(each, session)) for each in search])

        return htmls

    async def network_sem(self, sem, network):
        async with sem:
            return await network

    async def network_get(self, url, session):
        if url:  # Skip history search if already has med
            while True:
                try:
                    async with session.get(url) as response:
                        if response.status == 200:
                            return str(await response.content.read())
                        await async_sleep(1)
                except:
                    await async_sleep(1)
        return True

    async def delete_unknown(self, items):
        blacklist = set(open('Files/Blacklist.txt'))
        async with aiofiles.open('Files/Blacklist.txt', 'a+') as f:
            i = 0
            while i < len(items):
                if items[i].info_html:
                    items[i].name = items[i].info_html.split('"item-name">')[1].split('<')[0]
                    if items[i].name != 'Unknown':
                        i += 1
                    else:
                        if items[i].ID not in blacklist:
                            await f.write(items[i].ID + '\n')
                            blacklist.add(items[i].ID)
                        del items[i]
        
class Medians_history():

    def __init__(self, items, settings):
        run(self.history(items, settings))

    async def history(self, items, settings):
        async with aiofiles.open('Files/Medians_cache.txt', 'a+') as f:
            for each in items:
                if not each.long_med:
                    each.med, each.long_med = self.median(each.history_html, each.refine, settings)
                    key = f'{each.ID} {each.refine}'
                    if each.long_med is None:
                        await f.write(f'{key}:0 0 \n')
                    else:
                        await f.write(f'{key}:{each.med} {each.long_med} \n')

    def median(self, history, refine, settings):
        med, long_med = [], []
        property_exist = '<th>Additional Properties</th>' in history
        find_price = history.split('</span>z')
        size = len(find_price) - 2
        
        i = 0
        # Refine column present
        if '>Refine</th>' in history:
            while i < size and date(find_price[i].rsplit(' - ', 1)[0].rsplit(">", 1)[1].split('/'), 
                                    settings['LM']):
                item_refine = int(find_price[i + 1].split('data-order="')[1].split('"')[0])
                if item_refine == refine:
                    if not property_exist or 'None' in find_price[i + 1].split('sorting_1')[0]:  
                        long_med.append(int(find_price[i].rsplit('>', 1)[-1].replace(',', '')))
                        if date(find_price[i].rsplit(' - ', 1)[0].rsplit(">", 1)[1].split('/'), settings['SM']):
                            med.append(int(find_price[i].rsplit('>', 1)[-1].replace(',', '')))
                i += 1

        # Refine column missing
        else:
            while i < size and date(find_price[i].rsplit(' - ', 1)[0].rsplit(">", 1)[1].split('/'),
                                    settings['LM']):
                if not property_exist or 'None' in find_price[i + 1].split('</tr>')[0]:  
                    long_med.append(int(find_price[i].rsplit('>', 1)[-1].replace(',', '')))
                    if date(find_price[i].rsplit(' - ', 1)[0].rsplit(">", 1)[1].split('/'), settings['SM']):
                        med.append(int(find_price[i].rsplit('>', 1)[-1].replace(',', '')))
                i += 1

        if med and long_med:
            return round(median(med)), round(median(long_med))
        elif med and not long_med:
            return round(median(med)), None
        elif not med and long_med:
            return None, round(median(long_med))
        elif not med and not long_med:
            return None, None

class Medians_date(): 
    """
    Everything here is Optional
    """

    async def delete_medians(self):
        async with aiofiles.open('Files/Medians_cache.txt', 'w+'):
            pass

    async def set_date(self):
        today = datetime.utcnow().replace(tzinfo=timezone.utc) - timedelta(hours=7)
        async with aiofiles.open('Files/Medians_refresh.txt', 'w+') as f:
            await f.write(f'{today.day}-{today.month}-{today.year}')
        
    def filter_medians(self, items, median_filter):
        i = 0
        while i < len(items):
            if items[i].med is not None \
                    and 'None' in items[i].prop \
                    and items[i].med < median_filter \
                    and items[i].long_med < median_filter:
                del items[i]
            else:
                i += 1

def date(date, interval, args=None):
        
    if not args:
        today = datetime.utcnow().replace(tzinfo=timezone.utc) - timedelta(hours=7)
        date = f'{date[1]}-{date[0]}-20{date[2]}'
        date = datetime.strptime(date, "%d-%m-%Y")
        time = today - timedelta(days=date.day)

        if time.day < interval:
            return 1
        else:
            return 0
    else:
        date1 = date.split('-')[0].replace(' ', '').split('/')
        date2 = date.split('-')[1].replace(' ', '').split(':')
        date1[2] = '20' + date1[2]
        date = f'{date1[2]}-{date1[0]}-{date1[1]}-{date2[0]}-{date2[1]}'
        date = datetime.strptime(date, "%Y-%m-%d-%H-%M")
        date = date.replace(tzinfo=timezone.utc)

        if date >= interval:
            return 1  # sold
        else:
            return 0  # old

async def sold_notification(cookie, sell_price):
    start = datetime.utcnow().replace(second=0, microsecond=0, tzinfo=timezone.utc) - timedelta(hours=7)
    
    html = await Network().network_session(
                ['https://www.novaragnarok.com/?module=account&action=sellinghistory'], cookie)

    k = 0
    while True:
        i = j = back = found = 0
        while True:
            try:
                start = html.rsplit('Selling History', 1)[1].split('data-order', i + 1)[i + 1]
                date = start.split('</td>', 1)[0].rsplit('>', 1)[1]
                name = start.split('</a>', 1)[0].rsplit(' \\t', 1)[1].replace('\\t', '')
                prop = start.split('data-order', 1)[1].split('>', 1)[1].split('<', 1)[0]
                ea = start.split('data-order', 1)[1].split('<td>', 1)[1].split('</td>', 1)[0]
                # ea_price = start.split('</span>z', 1)[0].rsplit('>', 1)[1]
                price = start.split('</span>z', 2)[1].rsplit('>', 1)[1]
                if date(date, start, 1):  # Check if item time is newer than program start time
                    if not back:  # First count all new items since program start running
                        j += 1
                        i += 4  # Next item 4 'data-orders' ahead
                        continue
                if found:
                    k += 1
                    if int(price.replace(',', '')) >= sell_price * 0.97:
                        await windows_toast(name, prop, price, ea=ea)
                        
                    if j != k:
                        i += 4
                        continue
                    
                if j > k:
                    found, back, i = 1, 1, 0 # Return to list start to send notifications
                    continue

            except IndexError:  # Player could not have sell anything in game yet
                pass

            await async_sleep(30)

async def get_name(ID, cookie):
    name = None
    async with aiofiles.open('Files/Names.txt', 'r') as f:
        async for line in f:
            if line.split(':')[0].strip() == ID:
                name = line.split(':')[1].strip().rstrip(' ') 

    if not name:
        info = await Network().network_session(
            ["https://www.novaragnarok.com/?module=vending&action=item&id=" + ID], cookie)
        name = info.split('"item-name">')[1].split('<')[0].strip()
        if name != 'Unknown':
            async with aiofiles.open('Files/Names.txt', 'a+') as f:
                await f.write(f"{ID}:{name} \n")
    return name

async def windows_toast(name, prop, price, refine=None, place=None, ea=None):
    my_toast = ToastNotifier()
    if not ea: # Alert
         msg = f'{refine} {name}\n{", ".join(prop)}\n\nPrice: {price}\nLocation: {place}' # Price notification
    else:  # Sold
        msg = f'{ea}x {name}\n{", ".join(prop)}\n\nSold: {format(price, ",d")}z' # Sold notification
    
    my_toast.show_toast("NovaMarket", msg, threaded=True, icon_path='Files/icon.ico', duration=None)
    await async_sleep(0.1)

class NovaNotifier():

    def __init__(self, items):
        notify = {}
        self.last_notification = ''
        self.format(items)
        self.make_table(items)
        self.notification(items, notify)

    def format(self, items):
        for each in items:
            pos = self.price_search(each)

            each.format_prop = ', '.join(each.prop) 
            each.format_alert = format(each.alert, ',d') + 'z'
            each.format_med = format(each.med, ',d') + 'z' if each.med else '-'
            each.format_long_med = format(each.long_med, ',d') + 'z' if each.long_med else '-'

            # Nothing found in market
            if pos == -1:
                each.price = each.format_price = each.med_porc = each.long_med_porc = \
                    each.place = each.ea = each.minor_ea = each.cheap = '-'

            # Found something
            else:
                each.format_price = format(each.price, ',d') + 'z'
                self.place(each, pos)
                self.percentage(each)

    def price_search(self, item):
        find_price_refine = item.info_html.split('</span>z')
        prop_column = 'Additional Properties' in item.info_html
        info = {'cheap_total': 0, 'cheapest_total': 0, 'minor_price': 10000000000, 'pos': -1}
        minor_refine = item.refine
        item.format_refine = f'+{item.refine}'
        # Check if Market Available
        try:
            refine_exist = item.info_html.split('</span>z')[1].split('text-align:')[1].split(';')[0]
        except:
            return -1

        i = total = 0
        if refine_exist == 'center':  # Refinable
            while i < len(find_price_refine) - 1:
                refine = int(find_price_refine[i + 1].split('data-order="')[1].split('"')[0])
                if refine >= item.refine:
                    if self.property_exists(prop_column, item, find_price_refine[i + 1]):
                        self.lowest_price(find_price_refine[i], find_price_refine[i + 1], item.med, i, info)
                        total += 1
                        minor_refine = refine
                i += 1

            if minor_refine > item.refine:  # Explicit if displayed refine if is higher than user's refine inserted
                item.format_refine = f'{item.refine} -> {minor_refine}'
            else:
                item.format_refine = '+' + str(minor_refine)

        elif refine_exist == 'right' and item.refine == 0:  # Not Refinable
            while i < len(find_price_refine) - 1:
                if self.property_exists(prop_column, item, find_price_refine[i + 1]):
                    self.lowest_price(find_price_refine[i], find_price_refine[i + 1], item.med, i, info)
                    total += 1
                i += 1
            
        item.price = info['minor_price']
        item.cheap = f'{info["cheapest_total"]}/{info["cheap_total"]}'
        item.ea = total
        return info['pos']

    def lowest_price(self, find_price_refine, find_price_refine_next, med, i, info):
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

    def property_exists(self, prop_column, item, find_price_refine):
        # No Property Column
        if not prop_column:
            if 'None' in item.prop or 'Any' in item.prop:
                return 1
            else:
                return 0

        # Property Column
        else:
            for each in item.prop: #Check if every property is present
                if each == 'Any' or each in find_price_refine.split('span class')[0]:
                    pass
                else:
                    return 0
            return 1

    def percentage(self, item):
        if item.long_med > 0:
            if item.long_med >= item.price:
                item.long_med_porc = '-' + str(round(abs(100 - (item.price / item.long_med) * 100))) + '%'
            else:
                item.long_med_porc = '+' + str(round(abs(100 - (item.price / item.long_med) * 100))) + '%'
        else:
            item.long_med_porc = None

        if item.med > 0:
            if item.med >= item.price:
                item.med_porc = '-' + str(round(abs(100 - (item.price / item.med) * 100))) + '%'
            else:
                item.med_porc = '+' + str(round(abs(100 - (item.price / item.med) * 100))) + '%'
        else:
            item.med_porc = None

    def place(self, item, pos):
        find_place = item.info_html.split("data-map=")
        places = find_place[pos + 1].replace(' ', '').split("</span>")[0].split(">")[1].split(',')
        item.place = f'{places[0]}[{places[1]},{places[2]}]'.replace('\\n', '')

    def make_table(self, items):
        table, t = [], ['ID', 'NAME', 'EA', 'CHEAP', 'REFINE', 'PROP', 'PRICE', 'SHORT MED', 'LONG MED', 'SM%', 'LM%',
                        'ALERT', 'LOCATION']

        for each in items:
            table.append([each.ID,
                          each.name,
                          each.ea,
                          each.cheap,
                          each.format_refine,
                          each.format_prop,
                          each.format_price,
                          each.format_med,
                          each.format_long_med,
                          each.med_porc,
                          each.long_med_porc,
                          each.format_alert,
                          each.place])

        #system('cls')
        print(tabulate(table, headers=t, tablefmt='fancy_grid'))

    def notification(self, items, notify):
        for each in items:
            if each.price != '-' and (each.alert >= each.price):
                if each.ID not in notify or (each.ID in notify and each.format_refine not in notify[each.ID]):
                    notification = datetime.utcnow().replace(tzinfo=timezone.utc) - timedelta(hours=7)
                    self.last_notification = notification.strftime('%d/%m/%Y %H:%M:%S')
                    run(windows_toast(each.name, each.prop, each.format_price, each.format_refine, each.place))
                    notify[each.ID] = [each.refine] # This needs to be outside NovaNotifier to not repeat notif.