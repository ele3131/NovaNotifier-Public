1-) Open ID.txt and type your items in this format: 

		ID;Refine;Properties;AlertPrice #Any comment you want 
Valid Examples:

1556;0;None;1000000  #Book of Gust of Wind
1556; 0; None; 1000000  #Book of Gust of Wind
1556 ; 0 ; None ; 1000000  #Book of Gust of Wind

2524;0;Wakwak Card;10.000.000  #Valkyrian Manteau[1] with Wakwak Card
2524; 0; Wakwak Card; 10.000.000  #Valkyrian Manteau[1] with Wakwak Card  
2524 ; 0 ; Wakwak Card ; 10.000.000  #Valkyrian Manteau[1] with Wakwak Card  

22000;0;Fighting Spirit 7,Runaway Magic;10.000.000 #Temporal Boots Of Strenght with 2 Properties
22000; 0; Fighting Spirit 7,Runaway Magic; 10.000.000 #Temporal Boots Of Strenght with 2 Properties
22000 ; 0 ; Fighting Spirit 7, Runaway Magic ; 10.000.000 #Temporal Boots Of Strenght with 2 Properties

// -- // -- //

Enabling Discord: Add your in Discord_Username (Ex: Michel#3659)

Discord Passcode = Received after running the program and sending 'start' to Nova Bot

Multiple Accounts: If you wish that Nova Notifier sends you "Sell Notifications" you can
		   use *Chrome* multiple sessions to track more than one account at the same time.
		   
// -- // -- //

Refine --> 0 if item doesn't accept refine. 
AlertPrice --> Below that price an Notification Toast will trigger (to never be notified = 0). 
Property --> Copy Properties from NovaRO Website. (None = Only None Property, Any = Any Property).
Medians --> Calculated based only on your Refine.
Short Median --> 15 Days by Default.
Long Median --> 45 Days by Default.
Notification --> Program creates an Task Bar icon for each notification.
Cheap Column --> "Amount of Lowest Price Items" / "Amount of Items Below Median".

Table is sorted by Short and Long Medians Percentages.

If your item refine is not on market, until it is, an above refine will be display.
	  
*For Elements, write just the element name (e.g: Water, Fire, Shadow...). 

// -- // -- //

Medians:

The program caches medians of searched items to reduce Network Requests, however after some time 
they will be outdated, edit 'median_cache' according to your preference.

// -- // -- //

Settings:

Some options are editable in Settings file:

'timer_refresh' = How many seconds to refresh.
'sell_filter' = Minimum sold item price to send notifications.
'SM' = Short Median Days (used to calculate items' medians)
'LM' = Long Median Days (used to calculate items' medians)
'median_cache' = Control after how many days medians will be erased.  
'median_filter' = Display only items that have medians above that number.
 
// -- // -- //

2-) Open Chrome or Firefox and Login NovaRO Website, Check 'Remember Me' (You can close the browser afterwards) 
		
3-) Run NovaPriceNotifier.exe and enjoy!

// -- // -- //

Support --> Discord: Michel#3659 