from NovaNotifier2 import *

player = Login()
config = Read_settings_file()
items = Read_id_file().items
Read_medians_file(items)
Network().items_network(items, player.cookies[0])
Medians_history(items, config.settings)
NovaNotifier(items)