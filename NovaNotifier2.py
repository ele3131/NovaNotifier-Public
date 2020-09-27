from os import system
from sys import platform
from asyncio import run, gather, sleep, create_task, BoundedSemaphore, TimeoutError
from datetime import datetime, timedelta, timezone
from statistics import median
from browsercookie3 import chrome, firefox
from aiohttp import ClientSession
import aiofiles
from colorama import init, Fore
from traceback import format_exc
from tabulate import tabulate
from aioconsole import ainput

if platform == "win32":
    from win10toast_persist import ToastNotifier


class NovaNotifier():

    def __init__(self):
        self.notify = {}
        self.settings = {}
        self.medians_cache = {}
        self.blacklist = {}
        self.network_count = {}
        self.usernames = []
        self.cookies = []
        self.items = []
        self.result = []
        self.enter_key = 0
        self.discord_user = ''

    async def start(self):
        try:
            print(Fore.LIGHTYELLOW_EX + "Initializing...")

            await self.read_discord()
            await self.read_settings()
            await self.read_id()
            await self.read_medians()

            print(Fore.LIGHTGREEN_EX + 'Discord in Progress...')

            if self.discord_user:
                import discord_bot
                self.discord_bot = discord_bot
                token = discord_bot.bot_token
                create_task(discord_bot.client.start(token))
                await discord_bot.finish.wait()

            if self.discord_user and discord_bot.confirm:
                print(f"Discord: {Fore.LIGHTGREEN_EX}{self.discord_user}")
            else:
                print(f"Discord: {Fore.LIGHTRED_EX}Offline")

            print(Fore.LIGHTGREEN_EX + 'Login in Progress...')

            self.sema = BoundedSemaphore(4)
            await self.login()

            print(Fore.LIGHTGREEN_EX + 'Requesting Items...')

            await self.network_items(self.items, self.cookies[0])
            await self.medians_history(self.items)
            self.format(self.items)

            await self.price_notification()
            self.make_table(self.items)

            for cookie, username in zip(self.cookies, self.usernames):
                create_task(self.sold_notification(cookie))

            await self.timer()
        except:
            system('cls')
            print(Fore.LIGHTRED_EX + format_exc())
            await ainput("\nPress any button to exit")
            exit(0)

    async def refresh(self):
        await self.network_items(self.items, self.cookies[0])
        self.format(self.items)
        self.make_table(self.items)

    async def timer(self):
        create_task(self.input())
        timer = self.settings['timer_refresh']
        while(timer):
            print(f"\x1b[2K{Fore.LIGHTYELLOW_EX}Refresh in {str(timer)} seconds", end='\r')
            timer -= 1
            await sleep(1)
            if timer <= 0 or self.enter_key:
                print('\x1b[2K' + Fore.LIGHTGREEN_EX + 'Refreshing...')
                timer = self.settings['timer_refresh']
                await self.refresh()
                self.enter_key = 0

    async def input(self):
        while True:
            await ainput()
            self.enter_key = 1

    async def login(self):
        cjs = []
        if self.settings['browser'] == 'firefox':
            try:
                cjs.append(firefox(domain_name='novaragnarok.com'))
            except BaseException:
                pass

        else:
            profile = 'Default'
            for i in range(10):
                try:
                    cjs.append(chrome(domain_name='novaragnarok.com', profile=profile))
                except:
                    pass
                profile = f'Profile {i}'

        if not cjs:
            raise IndexError('COOKIES NOT FOUND!')

        cookie = []
        for item in cjs:
            try:
                cookie.append({"fluxSessionData": item._cookies['www.novaragnarok.com']['/']['fluxSessionData'].value})
            except KeyError:
                pass

        login = (await gather(*[self.network_session('https://novaragnarok.com', each) for each in cookie]))

        for i, item in enumerate(login):
            try:
                username = item.split("</strong>", 1)[0].rsplit(">", 1)[1]
                if '\\n' not in username and username not in self.usernames:
                    self.usernames.append(username)
                    self.cookies.append(cookie[i])
            except:
                pass

        if self.usernames:
            print(f"Accounts: {Fore.LIGHTGREEN_EX}{str(*self.usernames)}")
        else:
            raise IndexError('COOKIES INVALID!')

    async def read_id(self):
        self.blacklist = set(open('Files/Blacklist.txt'))
        async with aiofiles.open('Files/ID.txt', 'r') as f:
            async for line in f:
                if line.strip():
                    ID = line.split(';')[0].strip(' ')
                    if ID + '\n' not in self.blacklist:
                        self.items.append({
                            'id': ID,
                            'market_url': "https://www.novaragnarok.com/?module=vending&action=item&id=" + ID,
                            'history_url': "https://www.novaragnarok.com/?module=vending&action=itemhistory&id=" + ID,
                            'refine': int(line.split(';')[1].strip()),
                            'property': [item.strip() for item in line.split(';')[2].split(',')],
                            'alert': int(line.split(';')[3].replace(' ', '').replace('.', '').replace(',', '').strip())
                        })

    async def read_settings(self):
        """ dict: SM, LM, median_filter, timer_interval, sell_filter, token and browser"""

        settings = {'SM': 15, 'LM': 60, 'median_filter': 0, 'timer_refresh': 180,
                    'sell_filter': 0, 'token': 0, 'browser': None}

        async with aiofiles.open('Files/Settings.txt', 'r') as f:
            async for line in f:
                if line.strip():
                    if 'median_filter' in line:
                        settings['median_filter'] = int(line.split('=')[1].replace('.', '').strip())
                    elif 'median_cache' in line:
                        settings['median_cache'] = int(line.split('=')[1].strip())
                    elif 'timer_refresh' in line:
                        settings['timer_refresh'] = int(line.split('=')[1].strip())
                    elif 'sell_filter' in line:
                        settings['sell_filter'] = int(line.split('=')[1].replace('.', '').strip())
                    elif 'SM' in line:
                        value = line.split('=')[1].strip()
                        settings['SM'] = int(value)
                    elif 'LM' in line:
                        value = line.split('=')[1].strip()
                        settings['LM'] = int(value)
                    elif 'browser' in line:
                        settings['browser'] = line.split('=')[1].strip()
        self.settings = settings

    async def read_discord(self):
        async with aiofiles.open('Files/Discord.txt', 'r') as f:
            async for line in f:
                if 'Discord_Username' in line:
                    self.discord_user = (line.replace(' ', '').strip().split('=')[1])

    async def read_medians(self):
        """Read and Set Items medians"""

        medians_cache = {}
        async with aiofiles.open('Files/Medians_cache.txt', 'r') as f:
            async for line in f:
                if line.strip():
                    key, value = line.split(':')[0], line.split(':')[1].strip().split(' ')
                    medians_cache[key] = list(value)

        for item in self.items:
            key = f"{item['id']} {item['refine']}"
            if key in medians_cache and 'None' in item['property']:
                item['short_med'], item['long_med'] = int(medians_cache[key][0]), int(medians_cache[key][1])

        # Get file date and delete medians if old
        with open('Files/Medians_refresh.txt', 'r') as f:
            date = (f.read()).strip()

        today = datetime.utcnow() - timedelta(hours=7)
        if not self.date(date, self.settings['median_cache'], today):
            async with aiofiles.open('Files/Medians_refresh.txt', 'w+') as f:
                await f.write(str(today.day) + '-' + str(today.month) + '-' + str(today.year))
            async with aiofiles.open('Files/Medians_cache.txt', 'w+'):
                pass

        # Delete item if medians are below median_filter
        i = 0
        while i < len(self.items):
            if 'long_med' in self.items[i].keys():
                if self.items[i]['long_med'] < self.settings['median_filter']:
                    if self.items[i]['short_med'] < self.settings['median_filter']:
                        del self.items[i]
                        continue
            i += 1

        self.medians_cache = medians_cache

    async def network_session(self, url, cookie):
        async with ClientSession(cookies=cookie) as session:
            html = await self.network_request(url, session)
        return html

    async def network_request(self, url, session):
        while True:
            try:
                async with self.sema, session.get(url, timeout=3) as response:
                    if response.status == 200:
                        return str(await response.content.read())
                    await sleep(1)
            except TimeoutError:
                await sleep(0.5)

    async def network_market_request(self, item, session):
        while True:
            try:
                async with self.sema, session.get(item['market_url'], timeout=4) as response:
                    if response.status == 200:
                        item['market_data'] = str(await response.content.read())
                        print(f"\x1b[2KSearched: {Fore.LIGHTGREEN_EX}{str(self.network_count['each'])}" +
                              f"/{str(self.network_count['total'])}", end='\r')
                        self.network_count['each'] += 1
                        break
                    await sleep(1)
            except TimeoutError:
                print(f"\x1b[2KSearched: {Fore.LIGHTRED_EX}{str(self.network_count['each'])}" +
                      f"/{str(self.network_count['total'])}", end='\r')
                await sleep(0.5)

    async def network_history_request(self, item, session):
        if 'long_med' not in item.keys():
            while True:
                try:
                    async with self.sema, session.get(item['history_url'], timeout=4) as response:
                        if response.status == 200:
                            item['history_data'] = str(await response.content.read())
                            print(f"\x1b[2KSearched: {Fore.LIGHTGREEN_EX}{str(self.network_count['each'])}" +
                                  f"/{str(self.network_count['total'])}", end='\r')
                            self.network_count['each'] += 1
                            break
                        await sleep(1)
                except TimeoutError:
                    print(f"\x1b[2KSearched: {Fore.LIGHTRED_EX}{str(self.network_count['each'])}" +
                          f"/{str(self.network_count['total'])}", end='\r')
                    await sleep(0.5)

    async def network_items(self, items, cookie):
        self.network_count = {'each': 1, 'total': len(items)}

        for item in items:
            if 'long_med' not in item.keys():
                self.network_count['total'] += 1

        async with ClientSession(cookies=cookie) as session:
            await gather(*[self.network_market_request(item, session) for item in items])

        await self.set_names(items)  # Remove Unknown Items before History Search

        async with ClientSession(cookies=cookie) as session:
            await gather(*[self.network_history_request(item, session) for item in items])

    async def set_names(self, items):
        async with aiofiles.open('Files/Blacklist.txt', 'a+') as f:
            async with aiofiles.open('Files/Medians_cache.txt', 'a+') as g:
                i = 0
                while i < len(items):
                    if items[i]['market_data']:
                        items[i]['name'] = items[i]['market_data'].split('"item-name">')[1].split('<')[0]
                        if items[i]['name'] != 'Unknown':
                            i += 1
                        elif items:
                            if items[i]['id'] + '\n' not in self.blacklist:
                                await f.write(items[i]['id'] + '\n')
                                self.blacklist.add(items[i]['id'])
                            key = f"{items[i]['id']} {items[i]['refine']}"
                            if key not in self.medians_cache.keys():
                                self.medians_cache[key] = "0 0"
                                await g.write(f"{key}: 0 0 \n")
                            del items[i]
                            self.network_count['total'] -= 1

    async def medians_history(self, items):
        async with aiofiles.open('Files/Medians_cache.txt', 'a+') as f:
            for item in items:
                if 'long_med' not in item.keys():
                    item['short_med'], item['long_med'] = await self.medians(item['history_data'], item['refine'])
                    key = f"{item['id']} {item['refine']}"
                    if key not in self.medians_cache.keys():
                        self.medians_cache[key] = f"{item['short_med']} {item['long_med']}"
                        await f.write(f"{key}: {item['short_med']} {item['long_med']} \n")

    async def medians(self, history, refine):
        med, long_med = [], []
        today = datetime.utcnow() - timedelta(hours=7)
        property_exist = '<th>Additional Properties</th>' in history
        find_price = history.split('</span>z')
        size = len(find_price) - 2

        i = 0
        # Refine column present
        if '>Refine</th>' in history:
            while i < size:
                item_refine = int(find_price[i + 1].split('data-order="')[1].split('"')[0])
                if item_refine == refine:
                    if property_exist or 'None' in find_price[i + 1].split('sorting_1')[0]:
                        date = find_price[i].rsplit(' - ', 1)[0].rsplit(">", 1)[1].split('/')
                        date_format = f"{date[1]}-{date[0]}-20{date[2]}"
                        if self.date(date_format, self.settings['LM'], today):
                            long_med.append(int(find_price[i].rsplit('>', 1)[-1].replace(',', '')))
                            if self.date(date_format, self.settings['SM'], today):
                                med.append(int(find_price[i].rsplit('>', 1)[-1].replace(',', '')))
                        else:
                            break
                i += 1

        # Refine column missing
        else:
            while i < size:
                if not property_exist or 'None' in find_price[i + 1].split('</tr>')[0]:
                    date = find_price[i].rsplit(' - ', 1)[0].rsplit(">", 1)[1].split('/')
                    date_format = f"{date[1]}-{date[0]}-20{date[2]}"
                    if self.date(date_format, self.settings['LM'], today):
                        long_med.append(int(find_price[i].rsplit('>', 1)[-1].replace(',', '')))
                        if self.date(date_format, self.settings['SM'], today):
                            med.append(int(find_price[i].rsplit('>', 1)[-1].replace(',', '')))
                    else:
                        break
                i += 1

        if med and long_med:
            return round(median(med)), round(median(long_med))
        elif med and not long_med:
            return round(median(med)), 0
        elif not med and long_med:
            return 0, round(median(long_med))
        elif not med and not long_med:
            return 0, 0

    async def sold_notification(self, cookie):
        start = datetime.utcnow().replace(second=0, microsecond=0, tzinfo=timezone.utc) - timedelta(hours=7)
        url = 'https://www.novaragnarok.com/?module=account&action=sellinghistory'

        k = 0
        item = {}
        while True:
            html = await self.network_session(url, cookie)
            i = j = back = found = 0
            while True:
                try:
                    search = html.rsplit('Selling History', 1)[1].split('data-order', i + 1)[i + 1]
                    time = search.split('</td>', 1)[0].rsplit('>', 1)[1]
                    item['name'] = search.split('</a>', 1)[0].rsplit('\\n', 1)[1].replace('\\t', '').replace('\\', '').strip()
                    item['prop'] = search.split('data-order', 1)[1].split('>', 1)[1].split('<', 1)[0]
                    item['ea'] = search.split('data-order', 1)[1].split('<td>', 1)[1].split('</td>', 1)[0]
                    item['price'] = search.split('</span>z', 2)[1].rsplit('>', 1)[1]
                    # ea_price = start.split('</span>z', 1)[0].rsplit('>', 1)[1]
                    if self.date(time, start, args=1):  # Check if item time is newer than program start time
                        if not back:  # First count all new items since program start running
                            j += 1
                            i += 4  # Next item 4 'data-orders' ahead
                            continue
                    if found:
                        k += 1
                        if int(item['price'].replace(',', '')) >= self.settings['sell_filter'] * 0.97:
                            await self.notification(item)

                        if j == k:
                            found = 0
                            break
                        else:
                            i += 4
                            continue

                    if j > k:
                        found, back, i = 1, 1, 0  # Return to list start to send notifications
                        continue

                except IndexError:  # Player could have sold nothing in game
                    pass

                await sleep(30)
                break

    async def price_notification(self):
        msg = []
        for item in self.items:
            if item['price'] is not None and item['alert'] > item['price']:
                if item['id'] not in self.notify or (item['id'] in self.notify and item['refine'] != self.notify[item['id']]):
                    msg.append(item)
                    self.notify[item['id']] = item['refine']

                # item['format_id'] = Fore.LIGHTGREEN_EX + item['id'] + Fore.LIGHTWHITE_EX  # ID green if notified
                item['format_name'] = Fore.LIGHTGREEN_EX + item['name']
                item['format_location'] = Fore.LIGHTGREEN_EX + item['location'] + Fore.LIGHTWHITE_EX  # Location green if notified
        if msg:
            create_task(self.notification(msg))

    async def notification(self, items):
        embed = self.discord_bot.discord.Embed(title='Good News!', description='', color=16580705)
        for item in items:
            if 'id' in item.keys():
                price = format(item['price'], ',d') + 'z'  # format_price has color
                url = 'https://www.novaragnarok.com/?module=vending&action=item&id=' + item['id']
                msg = (f"Item: {item['format_refine']} {item['name']}\nProperty: {item['format_property']}\n" +
                       f"Location: {item['location']}\nPrice: {price}\n{url}")
                embed.add_field(name='Item Alert:', value=msg)
            else:
                msg = f"Item: {item['ea']}x {item['name']}\nProp: {item['prop']}\nPrice: {item['price']}"
                embed.add_field(name='Sold Alert:', value=msg)

        if self.discord_user and self.discord_bot.confirm:
            await self.discord_bot.discord_user.send(embed=embed)

        if platform == "win32":
            toast = ToastNotifier()
            for item in items:
                if 'id' in item.keys():  # Market Alert
                    msg = (f"{item['format_refine']} {item['name']}\nProp: {item['format_property']}\n\n" +
                           f"{price} | {item['location']}")  # Price notification
                else:  # Sold Alert
                    msg = f"{item['ea']}x {item['name']}\nProp: {item['prop']}\n\nSold: {item['price']}"  # Sold notification

                toast.show_toast("NovaMarket", msg, threaded=True, icon_path='Files/icon.ico', duration=None)
                await sleep(1)

    def date(self, date, interval, today=None, args=None):
        if not args:
            date = datetime.strptime(date, "%d-%m-%Y")
            time = today - date

            if time.days <= interval:
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

    def format(self, items):
        for item in items:
            pos, format_refine, ea, cheap = self.price_search(item)

            if pos is not None:

                item['format_id'] = item['id']
                item['format_name'] = Fore.LIGHTCYAN_EX + item['name'] + Fore.LIGHTWHITE_EX
                item['format_refine'] = format_refine
                item['format_property'] = ', '.join(item['property'])
                item['format_price'] = format(item['price'], ',d') + 'z'
                item['ea'] = ea
                item['cheap'] = cheap
                item['format_short_med'] = format(item['short_med'], ',d') + 'z' if item['short_med'] else '-'
                item['format_long_med'] = format(item['long_med'], ',d') + 'z' if item['long_med'] else '-'
                item['short_med_perc'], item['long_med_perc'] = self.percentage(item)
                item['format_alert'] = format(item['alert'], ',d') + 'z' if item['alert'] != 0 else '-'
                item['format_location'] = item['location'] = self.place(item, pos)

                for key in item.keys():
                    if item[key] == '-':
                        item[key] = Fore.LIGHTBLACK_EX + item[key] + Fore.LIGHTWHITE_EX

            else:
                item['format_id'] = Fore.LIGHTBLACK_EX + item['id']
                item['format_name'] = item['name']
                item['format_refine'] = format_refine
                item['format_property'] = ', '.join(item['property'])
                item['format_price'] = '-'
                item['ea'] = '-'
                item['cheap'] = '-'
                item['format_short_med'] = format(item['short_med'], ',d') + 'z' if item['short_med'] else '-'
                item['format_long_med'] = format(item['long_med'], ',d') + 'z' if item['long_med'] else '-'
                item['short_med_perc'], item['long_med_perc'] = Fore.LIGHTBLACK_EX + '0%', Fore.LIGHTBLACK_EX + '0%'
                item['format_alert'] = format(item['alert'], ',d') + 'z' if item['alert'] != 0 else '-'
                item['format_location'] = item['location'] = '-' + Fore.LIGHTWHITE_EX

    def price_search(self, item):
        find_price_refine = item['market_data'].split('</span>z')
        prop_column = 'Additional Properties' in item['market_data']
        info = {'pos': None, 'cheap_total': 0, 'cheapest_total': 0, 'minor_price': 10000000000}
        minor_refine = item['refine']
        format_refine = f"+{item['refine']}"
        item['price'] = None

        # Check if Market Available
        try:
            refine_exist = item['market_data'].split('</span>z')[1].split('text-align:')[1].split(';')[0]
        except:
            return None, format_refine, '-', '-'

        i = total = 0
        if refine_exist == 'center':  # Refinable
            while i < len(find_price_refine) - 1:
                refine = int(find_price_refine[i + 1].split('data-order="')[1].split('"')[0])
                if refine >= item['refine']:
                    if self.property_check(prop_column, item['property'], find_price_refine[i + 1]):
                        self.lowest_price(find_price_refine[i], find_price_refine[i + 1], item['short_med'], i, info)
                        total += 1
                        minor_refine = refine
                i += 1

            if minor_refine != item['refine']:
                format_refine = f"+{item['refine']} -> +{minor_refine}"
            else:
                format_refine = '+' + str(minor_refine)

        elif refine_exist == 'right' and not item['refine']:  # Not Refinable
            while i < len(find_price_refine) - 1:
                if self.property_check(prop_column, item['property'], find_price_refine[i + 1]):
                    self.lowest_price(find_price_refine[i], find_price_refine[i + 1], item['short_med'], i, info)
                    total += 1
                i += 1

        item['price'] = info['minor_price'] if info['minor_price'] != 10000000000 else 0
        cheap = f'{info["cheapest_total"]}/{info["cheap_total"]}'

        return info['pos'], format_refine, str(total), cheap

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

    def property_check(self, prop_column, properties, find_price_refine):
        # No Property Column
        if not prop_column:
            if 'None' in properties or 'Any' in properties:
                return 1
            else:
                return 0

        # Property Column
        else:
            pos = {}  # Dict for duplicate properties
            for prop in properties:  # Check if every property is present
                if prop.lower() == 'any':
                    pass

                elif prop not in pos.keys():  # Not a duplicate property
                    i = find_price_refine.split('span class', 1)[0].find(prop)
                    if i != -1:
                        pos[prop] = i  # Save last property position
                    else:
                        return 0

                else:  # Duplicate property, search after last one
                    i = find_price_refine.split('span class', 1)[0][pos[prop] + 1: -1].find(prop)
                    if i != -1:
                        pos[prop] = i
                    else:
                        return 0
        return 1

    def percentage(self, item):
        if item['long_med']:
            if item['long_med'] >= item['price']:
                long_med_perc = f"{Fore.LIGHTGREEN_EX}-{str(round(abs(100 - (item['price'] / item['long_med']) * 100)))}%"
            else:
                long_med_perc = f"{Fore.LIGHTRED_EX}+{str(round(abs(100 - (item['price'] / item['long_med']) * 100)))}%"
        else:
            return Fore.LIGHTBLACK_EX + '0%', Fore.LIGHTBLACK_EX + '0%'

        if long_med_perc == Fore.LIGHTRED_EX + '+0%' or long_med_perc == Fore.LIGHTGREEN_EX + '-0%':
            long_med_perc = Fore.LIGHTBLACK_EX + '0%'

        if item['short_med']:
            if item['short_med'] >= item['price']:
                med_perc = f"{Fore.LIGHTGREEN_EX}-{str(round(abs(100 - (item['price'] / item['short_med']) * 100)))}%"
            else:
                med_perc = f"{Fore.LIGHTRED_EX}+{str(round(abs(100 - (item['price'] / item['short_med']) * 100)))}%"
        else:
            med_perc = Fore.LIGHTBLACK_EX + '0%'

        if med_perc == Fore.LIGHTRED_EX + '+0%' or med_perc == Fore.LIGHTGREEN_EX + '-0%':
            med_perc = Fore.LIGHTBLACK_EX + '0%'

        return med_perc, long_med_perc

    def place(self, item, pos):
        market_data = item['market_data']
        find_place = market_data.split("data-map=")
        places = find_place[pos + 1].replace(' ', '').split("</span>")[0].split(">")[1].split(',')
        return f'{places[0]}[{places[1]},{places[2]}]'.replace('\\n', '')

    def table_sort(self, val):
        return int(val[9].split('m', 1)[1].split('%', 1)[0]), int(val[10].split('m', 1)[1].split('%', 1)[0]), val[12]

    def make_table(self, items):
        t = ['ID', 'NAME', 'REFINE', 'PROP', 'EA', 'CHEAP', 'PRICE', 'SHORT MED', 'LONG MED', 'SM%', 'LM%', 'ALERT', 'LOCATION']
        if not self.result:
            for item in items:
                self.result.append([item['format_id'],
                                    item['format_name'],
                                    item['format_refine'],
                                    item['format_property'],
                                    item['ea'],
                                    item['cheap'],
                                    item['format_price'],
                                    item['format_short_med'],
                                    item['format_long_med'],
                                    item['short_med_perc'],
                                    item['long_med_perc'],
                                    item['format_alert'],
                                    item['format_location']])
        system('cls')
        self.result.sort(key=self.table_sort, reverse=True)
        print(tabulate(self.result, headers=t, tablefmt='grid'))
        print("(Refresh: Enter / Pause: Left Click / Resume: Right Click)")

        if self.discord_user and self.discord_bot.confirm:
            print(f"\nDiscord: {Fore.LIGHTGREEN_EX}{self.discord_user}")
        else:
            print(f"\nDiscord: {Fore.LIGHTRED_EX}Offline")

        print('\nTracking:', Fore.LIGHTGREEN_EX + str(*self.usernames), '\n')

init(autoreset=True)  # Colorama reset colors
run(NovaNotifier().start())
