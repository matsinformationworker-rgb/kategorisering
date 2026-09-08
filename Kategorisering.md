**Bakgrund**

Vi, [raizemore.com](http://raizemore.com) , är en produktjämförelsesajt liknande [prisjakt.nu](http://prisjakt.nu) och [pricerunner.se](http://pricerunner.se). Vår affärsmodell bygger på samarbete med affiliatenätverk och vi publicerar dagligen tusentals produkter från våra partners på våra produktsidor.  

Kunder som besöker vår webbsida har möjlighet att filtrera fram produkter genom ett **kategoriträd.** 

**Problemställning**  
Kategoriträdet som finns idag på [raizemore.com](http://raizemore.com) är dock inte tillfredsställande. Kategorierna som erbjuds innehåller onaturliga kategorier och produkterna som visas är i flera fall felaktigt kategoriserade. Jag tror att den befintliga lösningen använder en LLM för semantisk segmentering, men resultatet är inte stabilt. Vi skulle behöva något mycket mer stabilt.

Vi behöver en standardiserad kategorisering på max 4 nivåer som är intuitiv att använda.

**Utmaning**  
En utmaning är att produktsidorna bygger på “product feeds” från två olika affiliatenätverk, *Adtraction* och *Tradedoubler*, som använder olika typer av feeds. 

Exempel på feeds ligger i projektmappen

2xu\_\_adtraction\_\_2674\_\_2026-09-07T13-22-18-596Z.xml  
adlibris\_\_tradedoubler\_\_110179\_\_2026-09-01T09-17-38-486Z.json

Vi läser dagligen in ca 200 feeds (de flesta från Adtraction) och frågan är hur vi ska skapa ett kategoriträd på max 4 nivåer som mappar till produkterna i dessa filer?

**Vad jag har tänkt**  
Jag har tänkt på två olika principer att att angripa mappningen:

1. Antingen att börja med att skapa ett generiskt kategoriträd som är intuitivt och lätt för besökare att använda, och därefter försöka skapa en mappningsfunktion som mappar produkter in i dessa befintliga kategorier.  
2. Alternativt att försöka generera sådan struktur från butikernas feeds.

Viktigt är att samtliga produkter blir kategoriserade

Kanske har du ett annat förslag? Och dessutom kommer jag inte att klara av uppgiften för något av alternativen. Jag behöver din hjälp\!

Tror du att detta är möjligt?