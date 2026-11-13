"""Koostab infopanga andmed/turuulevaated.csv avalikest turuülevaadetest.

Talletatakse ainult arvulised näitajad koos allika, perioodi ja lingiga (mitte ülevaadete teksti).
Uue ülevaate lisamiseks lisa read allpool olevatesse tabelitesse ja käivita:
    python tools/ehita_turuulevaated.py
"""
from __future__ import annotations

import csv
from pathlib import Path

VÄLJAD = ["allikas", "väljaanne", "kuupäev", "periood", "tase", "piirkond", "ülem", "segment", "näitaja",
          "väärtus", "ühik", "url", "märkus"]

MARU_AASTA = ("Maa- ja Ruumiamet", "Eesti kinnisvaraturg 2025. aastal", "2026-02-15", "2025",
              "https://maaruum.ee/sites/default/files/documents/2026-02/Eesti%20kinnisvaraturg%202025.pdf")
MARU_INDEKS = ("Maa- ja Ruumiamet", "Kinnisvara hinnaindeksite kokkuvõte 2026 III", "2026-10-20", "2026-III",
               "https://maaruum.ee/sites/default/files/documents/2026-10/Kinnisvara%20hinnaindeksite%20KOKKUV%C3%95TE%202026%20III.pdf")

# --- Korteriomandid (eluruumid), vabaturu ostu-müügitehingud 2025 ---------------------------------
# piirkond | tase | ülem | arv | keskm. üldpind m² | keskm. €/m² | mediaan €/m² | tehingu mediaanhind €
KORTER_2025 = """
Eesti|riik||18809|56|2155|2192|104000
Harju maakond|maakond||10157|58|2893|2765|138500
Harju maakond v.a Tallinn|maakond||2569|70|2408|2564|160000
Hiiu maakond|maakond||47|60|863|902|50000
Ida-Viru maakond|maakond||1986|46|368|302|12350
Jõgeva maakond|maakond||256|55|451|435|23000
Järva maakond|maakond||353|57|630|649|32250
Lääne maakond|maakond||224|54|1403|1099|55000
Lääne-Viru maakond|maakond||667|52|729|560|28000
Põlva maakond|maakond||191|56|584|549|29950
Pärnu maakond|maakond||1028|54|1831|1781|84000
Rapla maakond|maakond||271|55|1050|987|47100
Saare maakond|maakond||181|58|1537|1447|78000
Tartu maakond|maakond||2523|60|2352|2328|125000
Valga maakond|maakond||259|51|520|403|17500
Viljandi maakond|maakond||408|54|972|880|40000
Võru maakond|maakond||258|51|817|818|36700
Tallinn|asula|Harju maakond|7588|54|3058|2830|134990
Keila linn|asula|Harju maakond|156|61|2676|2449|152000
Maardu linn|asula|Harju maakond|248|51|1760|1645|72500
Saue linn|asula|Harju maakond|88|62|2802|2952|173000
Paldiski linn|asula|Harju maakond|117|45|934|907|37500
Loo alevik|asula|Harju maakond|111|65|2824|2931|186900
Tabasalu alevik|asula|Harju maakond|49|86|2694|2566|233000
Kiili alev|asula|Harju maakond|83|71|3254|3297|233377
Peetri alevik|asula|Harju maakond|120|79|3115|3064|227950
Jüri alevik|asula|Harju maakond|53|69|2556|2446|153000
Saku alevik|asula|Harju maakond|59|65|2623|2383|153000
Laagri alevik|asula|Harju maakond|106|55|2650|2652|140000
Haabneeme alevik|asula|Harju maakond|90|82|2998|2887|212000
Viimsi alevik|asula|Harju maakond|69|70|3153|3278|190000
Kehra linn|asula|Harju maakond|46|55|1212|1132|54450
Kärdla linn|asula|Hiiu maakond|24|60|1157|1126|65750
Jõhvi linn|asula|Ida-Viru maakond|163|46|560|510|22000
Kohtla-Järve linn|asula|Ida-Viru maakond|604|46|205|145|6600
Narva linn|asula|Ida-Viru maakond|721|45|508|424|17500
Narva-Jõesuu linn|asula|Ida-Viru maakond|37|50|1137|949|48500
Sillamäe linn|asula|Ida-Viru maakond|237|44|286|259|10500
Jõgeva linn|asula|Jõgeva maakond|79|52|572|573|29500
Põltsamaa linn|asula|Jõgeva maakond|37|55|757|722|39500
Paide linn|asula|Järva maakond|153|55|873|842|41000
Türi linn|asula|Järva maakond|50|53|786|777|38820
Haapsalu linn|asula|Lääne maakond|130|49|1941|1349|66000
Rakvere linn|asula|Lääne-Viru maakond|189|53|1466|1292|65000
Tapa linn|asula|Lääne-Viru maakond|81|43|667|719|29000
Kunda linn|asula|Lääne-Viru maakond|68|46|284|277|11500
Põlva linn|asula|Põlva maakond|71|56|927|922|48000
Pärnu linn|asula|Pärnu maakond|699|53|2333|2134|105000
Sindi linn|asula|Pärnu maakond|21|50|1244|1161|52000
Sauga alevik|asula|Pärnu maakond|28|53|1840|1591|87500
Paikuse alev|asula|Pärnu maakond|17|60|1613|1633|75000
Rapla linn|asula|Rapla maakond|82|56|1534|1415|76500
Kohila alev|asula|Rapla maakond|35|51|1601|1597|73000
Kuressaare linn|asula|Saare maakond|146|58|1737|1647|85750
Tartu linn|asula|Tartu maakond|1586|54|2498|2369|115000
Elva linn|asula|Tartu maakond|33|60|1642|1576|82000
Raadi alev|asula|Tartu maakond|225|62|2894|2907|171170
Kõrveküla alevik|asula|Tartu maakond|88|98|2334|2332|239900
Ülenurme alevik|asula|Tartu maakond|46|73|2391|2399|181200
Otepää linn|asula|Valga maakond|23|60|1740|1343|86000
Valga linn|asula|Valga maakond|159|48|388|388|15000
Tõrva linn|asula|Valga maakond|25|55|724|748|36800
Viljandi linn|asula|Viljandi maakond|213|54|1474|1348|67000
Võru linn|asula|Võru maakond|166|49|1028|971|49250
Haabersti|linnaosa|Tallinn|1094|59|3048|3075|165538
Kesklinn|linnaosa|Tallinn|1227|58|3761|3612|194000
Kristiine|linnaosa|Tallinn|639|56|3412|3223|150000
Lasnamäe|linnaosa|Tallinn|1660|51|2491|2317|111000
Mustamäe|linnaosa|Tallinn|1293|49|2583|2436|115000
Nõmme|linnaosa|Tallinn|262|62|2809|2701|138000
Pirita|linnaosa|Tallinn|155|89|3457|2920|253000
Põhja-Tallinn|linnaosa|Tallinn|1258|47|3441|3068|129900
Astangu|asum|Haabersti|208|59|3193|3351|189700
Haabersti|asum|Haabersti|13|66|3109|3035|186000
Kakumäe|asum|Haabersti|13|118|3353|3384|369000
Mustjõe|asum|Haabersti|65|68|3939|4049|272000
Mäeküla|asum|Haabersti|23|70|3279|3234|217900
Pikaliiva|asum|Haabersti|184|61|3628|3654|205500
Tiskre|asum|Haabersti|77|68|3443|3700|214700
Vismeistri|asum|Haabersti|16|71|3482|3649|202000
Väike-Õismäe|asum|Haabersti|484|53|2506|2312|118000
Õismäe|asum|Haabersti|11|99|4867|4829|515000
Juhkentali|asum|Kesklinn|70|62|3892|3880|238500
Kadriorg|asum|Kesklinn|73|70|3872|4015|230000
Kassisaba|asum|Kesklinn|78|58|3903|3488|180000
Keldrimäe|asum|Kesklinn|107|51|3468|3284|145700
Kitseküla|asum|Kesklinn|188|55|3909|4010|198950
Kompassi|asum|Kesklinn|40|55|3281|2969|160000
Maakri|asum|Kesklinn|15|56|4083|4173|217000
Raua|asum|Kesklinn|67|64|3751|3611|222000
Sadama|asum|Kesklinn|93|60|3803|3573|195000
Sibulaküla|asum|Kesklinn|31|65|3712|3510|239000
Südalinn|asum|Kesklinn|13|69|5011|5129|290000
Tatari|asum|Kesklinn|37|72|3989|3472|251000
Torupilli|asum|Kesklinn|85|49|3615|3603|164000
Tõnismäe|asum|Kesklinn|28|74|4179|4046|239250
Uus Maailm|asum|Kesklinn|146|50|3292|3160|146000
Vanalinn|asum|Kesklinn|44|82|3984|3851|287500
Veerenni|asum|Kesklinn|108|57|4006|3845|195000
Järve|asum|Kristiine|57|46|3109|2941|131000
Lilleküla|asum|Kristiine|438|56|3311|3132|144950
Tondi|asum|Kristiine|144|58|3841|3936|209094
Katleri|asum|Lasnamäe|62|48|2244|2240|105500
Kurepõllu|asum|Lasnamäe|59|55|2996|2897|165000
Kuristiku|asum|Lasnamäe|115|51|2220|2232|110000
Laagna|asum|Lasnamäe|311|52|2206|2194|107000
Loopealse|asum|Lasnamäe|20|63|2788|2817|157500
Mustakivi|asum|Lasnamäe|210|51|2194|2142|107950
Pae|asum|Lasnamäe|187|49|2205|2185|104990
Paevälja|asum|Lasnamäe|102|58|4174|4208|218800
Priisle|asum|Lasnamäe|132|50|2439|2316|107000
Seli|asum|Lasnamäe|185|51|2371|2254|112000
Sikupilli|asum|Lasnamäe|237|45|2751|2694|110000
Sõjamäe|asum|Lasnamäe|5|40|1928|1834|73000
Uuslinn|asum|Lasnamäe|12|51|3692|3735|184150
Ülemiste|asum|Lasnamäe|19|46|2527|2293|105000
Kadaka|asum|Mustamäe|157|55|3487|3547|182490
Mustamäe|asum|Mustamäe|937|47|2452|2359|109900
Siili|asum|Mustamäe|58|51|2401|2316|115000
Sääse|asum|Mustamäe|140|51|2524|2439|119900
Hiiu|asum|Nõmme|20|54|2765|2728|159700
Kivimäe|asum|Nõmme|24|63|2862|2713|143450
Männiku|asum|Nõmme|70|52|2751|2682|117500
Nõmme|asum|Nõmme|31|68|3008|2930|139000
Pääsküla|asum|Nõmme|71|73|2804|2680|164900
Rahumäe|asum|Nõmme|20|42|2833|2800|102400
Raudalu|asum|Nõmme|9|62|2190|2100|101000
Vana-Mustamäe|asum|Nõmme|9|90|3160|2961|300000
Kose|asum|Pirita|28|71|2975|2901|203750
Lepiku|asum|Pirita|9|103|2898|2891|320000
Maarjamäe|asum|Pirita|8|74|2638|2753|191500
Merivälja|asum|Pirita|10|93|3019|3119|176500
Mähe|asum|Pirita|63|96|2847|2653|234000
Pirita|asum|Pirita|35|85|5411|5354|410000
Kalamaja|asum|Põhja-Tallinn|348|57|4795|4590|247750
Karjamaa|asum|Põhja-Tallinn|70|45|2635|2535|111000
Kelmiküla|asum|Põhja-Tallinn|14|58|3068|2879|142250
Kopli|asum|Põhja-Tallinn|158|47|3298|3167|125700
Pelgulinn|asum|Põhja-Tallinn|255|46|2949|2860|122900
Pelguranna|asum|Põhja-Tallinn|295|41|2627|2574|100000
Sitsi|asum|Põhja-Tallinn|116|38|3276|2888|119000
Annelinn|linnaosa|Tartu linn|448|53|1958|1795|90000
Ihaste|linnaosa|Tartu linn|31|104|2417|2666|235000
Jaamamõisa|linnaosa|Tartu linn|109|47|2516|2350|121900
Karlova|linnaosa|Tartu linn|198|49|2919|2902|136450
Kesklinn|linnaosa|Tartu linn|147|54|3394|3214|160000
Kvissentali|linnaosa|Tartu linn|13|52|2320|2365|106500
Raadi-Kruusamäe|linnaosa|Tartu linn|80|52|2019|1913|95500
Ropka|linnaosa|Tartu linn|44|51|2019|1913|98000
Ropka tööstuse|linnaosa|Tartu linn|30|53|1909|1889|94950
Ränilinn|linnaosa|Tartu linn|57|55|2723|2911|150000
Supilinn|linnaosa|Tartu linn|43|54|3007|3026|149900
Tammelinn|linnaosa|Tartu linn|48|80|2673|2670|195900
Tähtvere|linnaosa|Tartu linn|28|56|2559|2366|120000
Vaksali|linnaosa|Tartu linn|63|54|2714|2749|124000
Variku|linnaosa|Tartu linn|16|53|2835|2925|133500
Veeriku|linnaosa|Tartu linn|58|54|2360|2261|112000
Ülejõe|linnaosa|Tartu linn|168|51|2645|2452|118000
Kesklinn|linnaosa|Pärnu linn|456|52|2519|2323|115500
Rääma|linnaosa|Pärnu linn|147|57|2051|1839|108000
Vana-Pärnu|linnaosa|Pärnu linn|5|25|1808|2060|41000
Ülejõe|linnaosa|Pärnu linn|85|48|1909|1847|80000
"""

# --- Hoonestatud elamumaa (eramud koos krundiga), maakonnad: arv | keskm. krunt m² | keskm. € | mediaan € ---
ERAMU_2025 = """
Eesti|riik||3934|2844|178760|120000
Harju maakond|maakond||1387|1838|286831|266700
Harju maakond v.a Tallinn|maakond||1131|2021|257035|230000
Hiiu maakond|maakond||20|5878|118950|104500
Ida-Viru maakond|maakond||406|1547|36053|14250
Jõgeva maakond|maakond||117|6167|60580|45000
Järva maakond|maakond||108|4317|61066|42000
Lääne maakond|maakond||107|4764|128157|100000
Lääne-Viru maakond|maakond||188|3591|90527|63500
Põlva maakond|maakond||72|7257|67850|49000
Pärnu maakond|maakond||300|2757|157619|125500
Rapla maakond|maakond||232|2410|116099|79500
Saare maakond|maakond||91|6700|124609|105000
Tartu maakond|maakond||521|2435|235249|237000
Valga maakond|maakond||93|4070|67192|47000
Viljandi maakond|maakond||195|4298|95589|69000
Võru maakond|maakond||97|5352|62652|38990
Tallinn|omavalitsus|Harju maakond|256|1029|418469|361000
Haabersti|linnaosa|Tallinn|51|1293|520892|440000
Kesklinn|linnaosa|Tallinn|14|725|345666|331411
Kristiine|linnaosa|Tallinn|26|815|460900|300000
Nõmme|linnaosa|Tallinn|75|1110|390890|348000
Pirita|linnaosa|Tallinn|75|917|358458|340000
Põhja-Tallinn|linnaosa|Tallinn|10|689|576500|505000
Viimsi vald|omavalitsus|Harju maakond|126|1448|382131|366500
Rae vald|omavalitsus|Harju maakond|80|1810|406336|380000
Harku vald|omavalitsus|Harju maakond|182|1690|249931|193000
Saue vald|omavalitsus|Harju maakond|169|1898|243621|240000
Saku vald|omavalitsus|Harju maakond|110|1426|237535|212500
Kiili vald|omavalitsus|Harju maakond|59|2447|293590|342000
Jõelähtme vald|omavalitsus|Harju maakond|62|2159|263108|268500
Keila linn|omavalitsus|Harju maakond|21|863|254560|247000
Maardu linn|omavalitsus|Harju maakond|72|1009|195103|137000
Lääne-Harju vald|omavalitsus|Harju maakond|113|2525|173480|135000
Kose vald|omavalitsus|Harju maakond|49|3125|201870|205000
Anija vald|omavalitsus|Harju maakond|30|4033|119517|82000
Raasiku vald|omavalitsus|Harju maakond|25|2409|219420|258900
Kuusalu vald|omavalitsus|Harju maakond|29|6131|182359|123000
Tartu linn|omavalitsus|Tartu maakond|151|1064|245153|205000
Tartu vald|omavalitsus|Tartu maakond|52|3474|288832|314950
Kambja vald|omavalitsus|Tartu maakond|107|2116|271823|310000
Luunja vald|omavalitsus|Tartu maakond|46|2850|295531|300000
Nõo vald|omavalitsus|Tartu maakond|53|2068|202450|210000
Elva vald|omavalitsus|Tartu maakond|56|4106|132722|104500
Pärnu linn|omavalitsus|Pärnu maakond|141|1577|200476|200000
Tori vald|omavalitsus|Pärnu maakond|79|1988|152652|95000
Haapsalu linn|omavalitsus|Lääne maakond|60|3082|160266|146000
Rakvere linn|omavalitsus|Lääne-Viru maakond|38|987|138953|125000
Viljandi linn|omavalitsus|Viljandi maakond|56|875|150508|145000
Kohila vald|omavalitsus|Rapla maakond|123|1616|131612|85000
Rapla vald|omavalitsus|Rapla maakond|64|2497|108670|72000
Saaremaa vald|omavalitsus|Saare maakond|81|6418|123458|105000
Narva linn|omavalitsus|Ida-Viru maakond|122|803|20062|13500
Võru linn|omavalitsus|Võru maakond|26|1312|96611|81000
Paide linn|omavalitsus|Järva maakond|35|2524|71123|62500
"""

# --- Hoonestamata elamumaa: arv | keskm. pind m² | keskm. €/m² | mediaan €/m² | tehingu mediaanhind € ---
ELAMUMAA_2025 = """
Eesti|riik||947|3637|50.5|28.4|60000
Harju maakond|maakond||374|2924|88.4|68.3|125000
Harju maakond v.a Tallinn|maakond||333|3126|63.8|58.8|120000
Hiiu maakond|maakond||22|9630|7.1|5.8|35400
Ida-Viru maakond|maakond||52|1947|12.5|8.9|16500
Jõgeva maakond|maakond||22|2575|12.1|7.1|12600
Järva maakond|maakond||16|3296|11.6|8.8|19250
Lääne maakond|maakond||44|7357|12.9|5.2|37850
Lääne-Viru maakond|maakond||37|3374|14.6|5.5|15000
Põlva maakond|maakond||10|6124|4.0|2.5|15250
Pärnu maakond|maakond||91|2885|29.0|23.1|43800
Rapla maakond|maakond||23|3613|26.8|28.3|47000
Saare maakond|maakond||56|8670|13.2|5.0|30000
Tartu maakond|maakond||150|2794|49.7|41.6|80200
Valga maakond|maakond||14|2557|17.6|7.8|15950
Viljandi maakond|maakond||22|3235|23.6|7.2|25550
Võru maakond|maakond||14|3734|14.7|10.3|30000
Tallinn|omavalitsus|Harju maakond|41|1286|288.3|221.0|254065
Haabersti|linnaosa|Tallinn|20|1347|228.7|217.9|267420
Pirita|linnaosa|Tallinn|9|1471|215.9|221.0|254065
Harku vald|omavalitsus|Harju maakond|50|2548|84.4|80.3|194500
Jõelähtme vald|omavalitsus|Harju maakond|22|2983|66.9|63.4|127000
Keila linn|omavalitsus|Harju maakond|11|2009|101.4|89.4|133590
Kiili vald|omavalitsus|Harju maakond|20|3913|60.3|66.4|138100
Lääne-Harju vald|omavalitsus|Harju maakond|63|4417|25.0|21.7|55000
Maardu linn|omavalitsus|Harju maakond|6|1203|93.8|97.6|106000
Raasiku vald|omavalitsus|Harju maakond|13|2719|38.8|36.6|101260
Rae vald|omavalitsus|Harju maakond|39|2255|82.8|72.4|110000
Saku vald|omavalitsus|Harju maakond|22|1887|91.4|106.5|112500
Saue vald|omavalitsus|Harju maakond|25|2155|62.9|72.8|124900
Viimsi vald|omavalitsus|Harju maakond|34|1969|96.9|91.2|156000
Tartu linn|omavalitsus|Tartu maakond|18|1977|87.8|88.7|132500
Tartu vald|omavalitsus|Tartu maakond|25|4701|56.4|57.5|108000
Kambja vald|omavalitsus|Tartu maakond|34|2524|59.4|56.0|91000
Luunja vald|omavalitsus|Tartu maakond|31|2392|45.4|46.5|90000
Pärnu linn|omavalitsus|Pärnu maakond|48|2233|39.3|29.6|49500
Tori vald|omavalitsus|Pärnu maakond|25|2583|21.5|21.9|30000
Saaremaa vald|omavalitsus|Saare maakond|56|7818|13.5|5.0|30000
Kohila vald|omavalitsus|Rapla maakond|14|2268|34.4|31.0|55250
"""

# --- Haritav maa ja kasvava metsaga metsamaa, maakonnad: haritav mediaan €/ha | mets mediaan €/ha ---
MAATULUNDUS_2025 = """
Eesti|6530|6645
Harju maakond|5981|6926
Hiiu maakond|3594|7269
Ida-Viru maakond|5205|9352
Jõgeva maakond|6918|7819
Järva maakond|6634|6239
Lääne maakond|5614|5516
Lääne-Viru maakond|6904|6304
Põlva maakond|7803|5619
Pärnu maakond|5734|6066
Rapla maakond|6013|6001
Saare maakond|4246|6221
Tartu maakond|7676|7859
Valga maakond|7072|4279
Viljandi maakond|6996|8517
Võru maakond|6552|6297
"""

# --- Hinnaindeksid (2003 III = 1,0): aasta | kvartal | kinnisvara | korteriomand | hoonestamata maa ---
INDEKSID = """
2024|4|5.02|5.15625|5.29253
2025|1|5.50|5.49706|5.50638
2025|2|5.68|5.64280|5.10245
2025|3|5.29|5.67886|5.46895
2025|4|5.40|5.73695|5.21626
2026|1|5.67|5.76969|5.48628
2026|2|5.62|5.64373|5.57242
2026|3|5.89|5.97677|5.75012
"""

# --- Kinnisvarafirmade kuuülevaated (Tallinn, Tartu, Pärnu, Narva korterid) ---
# allikas | väljaanne | kuupäev | periood | piirkond | näitaja | väärtus | ühik | url | märkus
FIRMAD = """
Uus Maa|Augusti turuülevaade 2026|2026-10-13|2026-08|Tallinn|tehinguid|712|tk|https://uusmaa.ee/en/august-market-overview-market-was-quieter-but-remained-active/|aastaga 0%
Uus Maa|Augusti turuülevaade 2026|2026-10-13|2026-08|Tallinn|mediaan_eur_m2|2926|€/m²|https://uusmaa.ee/en/august-market-overview-market-was-quieter-but-remained-active/|aastaga +4%
Uus Maa|Augusti turuülevaade 2026|2026-10-13|2026-08|Tartu linn|tehinguid|149|tk|https://uusmaa.ee/en/august-market-overview-market-was-quieter-but-remained-active/|aastaga -15,3%
Uus Maa|Augusti turuülevaade 2026|2026-10-13|2026-08|Tartu linn|mediaan_eur_m2|2515|€/m²|https://uusmaa.ee/en/august-market-overview-market-was-quieter-but-remained-active/|aastaga +8,3%
Uus Maa|Augusti turuülevaade 2026|2026-10-13|2026-08|Pärnu linn|tehinguid|53|tk|https://uusmaa.ee/en/august-market-overview-market-was-quieter-but-remained-active/|aastaga -39%
Uus Maa|Augusti turuülevaade 2026|2026-10-13|2026-08|Pärnu linn|mediaan_eur_m2|2123|€/m²|https://uusmaa.ee/en/august-market-overview-market-was-quieter-but-remained-active/|aastaga -3,6%
Uus Maa|Augusti turuülevaade 2026|2026-10-13|2026-08|Narva linn|mediaan_eur_m2|330|€/m²|https://uusmaa.ee/en/august-market-overview-market-was-quieter-but-remained-active/|aastaga -20,5%; väike valim
Uus Maa|Augusti turuülevaade 2026|2026-10-13|2026-08|Eesti|tehinguid|2115|tk|https://uusmaa.ee/en/august-market-overview-market-was-quieter-but-remained-active/|kuuga -5,5%
Uus Maa|Juuli turuülevaade 2026|2026-10-13|2026-07|Tallinn|mediaan_eur_m2|2953|€/m²|https://uusmaa.ee/en/july-market-overview-apartment-market-gained-momentum/|aastaga +6,2%
Uus Maa|Juuli turuülevaade 2026|2026-10-13|2026-07|Tartu linn|mediaan_eur_m2|2543|€/m²|https://uusmaa.ee/en/july-market-overview-apartment-market-gained-momentum/|aastaga +5,9%
Uus Maa|Juuli turuülevaade 2026|2026-10-13|2026-07|Pärnu linn|mediaan_eur_m2|1900|€/m²|https://uusmaa.ee/en/july-market-overview-apartment-market-gained-momentum/|aastaga -9%
Uus Maa|Juuli turuülevaade 2026|2026-10-13|2026-07|Narva linn|mediaan_eur_m2|480|€/m²|https://uusmaa.ee/en/july-market-overview-apartment-market-gained-momentum/|aastaga +15,6%; väike valim
1Partner|Kuuülevaade oktoober 2026|2026-11-04|2026-10|Tallinn|keskmine_eur_m2|3251|€/m²|https://www.adaur.ee/1partner-kuuulevaade-korterite-keskmine-ruutmeetrihind-tegi-viimaste-aastate-rekordi-3251-eurot/|september 3175
1Partner|Kuuülevaade oktoober 2026|2026-11-04|2026-10|Tallinn|mediaan_eur_m2|2955|€/m²|https://www.adaur.ee/1partner-kuuulevaade-korterite-keskmine-ruutmeetrihind-tegi-viimaste-aastate-rekordi-3251-eurot/|september 2978
1Partner|Kuuülevaade oktoober 2026|2026-11-04|2026-10|Tallinn|tehinguid|801|tk|https://www.adaur.ee/1partner-kuuulevaade-korterite-keskmine-ruutmeetrihind-tegi-viimaste-aastate-rekordi-3251-eurot/|korteritehingud; kõik tehingud 990
1Partner|Kuuülevaade oktoober 2026|2026-11-04|2026-10|Tallinn|eramu_tehinguid|35|tk|https://www.adaur.ee/1partner-kuuulevaade-korterite-keskmine-ruutmeetrihind-tegi-viimaste-aastate-rekordi-3251-eurot/|hoonestatud elamumaa kinnistud
Pindi Kinnisvara|Pindi indeks|2026-11-01|2026-09|Eesti suuremad linnad|keskmine_eur_m2|2357|€/m²|https://www.pindi.ee/hindamine/|kaalutud keskmine (maakonnakeskused + Narva, Kohtla-Järve); kuuga -2%
"""

# --- Pindi Kinnisvara uusarenduste monitooring (Tallinn + Harjumaa, pakkumised arendusprojektides) ---
# piirkond | näitaja | väärtus | ühik | väljaanne | kuupäev | periood | url | märkus
UUSARENDUS = """
Tallinn ja Harjumaa|projekte|129|tk|Uusarenduste monitooring: tühjade uute korterite jääk tõuseb|2025-09-23|2025-09|https://www.pindi.ee/tuhjade-uute-korterite-jaak-touseb/|müügis olevad korteriarendused
Tallinn ja Harjumaa|pakkumisi|3238|tk|Uusarenduste monitooring: tühjade uute korterite jääk tõuseb|2025-09-23|2025-09|https://www.pindi.ee/tuhjade-uute-korterite-jaak-touseb/|uued korterid pakkumises
Tallinn ja Harjumaa|pakkumise_keskmine_eur_m2|4465|€/m²|Uusarenduste monitooring: tühjade uute korterite jääk tõuseb|2025-09-23|2025-09|https://www.pindi.ee/tuhjade-uute-korterite-jaak-touseb/|pakkumishind, mitte tehinguhind
Tallinn ja Harjumaa|valmis_muumata|1000|tk|Uusarenduste monitooring: tühjade uute korterite jääk tõuseb|2025-09-23|2025-09|https://www.pindi.ee/tuhjade-uute-korterite-jaak-touseb/|ületas taas 1000 ühiku piiri
Tallinn|valjamuugi_keskmine_eur_m2|4900|€/m²|Postimees: uusarenduste müümata korterite arv kasvab (Pindi)|2025-09-23|2025-09|https://majandus.postimees.ee/8322569/liiga-kallis-uusarenduste-muumata-korterite-arv-kasvab|ligikaudu ("läheneb 4900 eurole")
Harju maakond v.a Tallinn|pakkumise_keskmine_eur_m2|3500|€/m²|Postimees: uusarenduste müümata korterite arv kasvab (Pindi)|2025-09-23|2025-09|https://majandus.postimees.ee/8322569/liiga-kallis-uusarenduste-muumata-korterite-arv-kasvab|ligikaudu ("veidi üle 3500")
"""

# --- Ärikinnisvara: piirkond | segment | näitaja | väärtus | ühik | allikas | väljaanne | kuupäev | periood | url | märkus
ARI = """
Tallinn|büroo|vakants_kokku|8.7|%|Newsec|Baltic Office Market 2025 Q4|2026-01-31|2025-Q4|https://cdn.sanity.io/files/w1ytoec0/production/796b6fb95a2f6321a1e0f572014f7fa3163269f5.pdf?dl=|
Tallinn|büroo A|vakants|7.2|%|Newsec|Baltic Office Market 2025 Q4|2026-01-31|2025-Q4|https://cdn.sanity.io/files/w1ytoec0/production/796b6fb95a2f6321a1e0f572014f7fa3163269f5.pdf?dl=|
Tallinn|büroo B|vakants|9.6|%|Newsec|Baltic Office Market 2025 Q4|2026-01-31|2025-Q4|https://cdn.sanity.io/files/w1ytoec0/production/796b6fb95a2f6321a1e0f572014f7fa3163269f5.pdf?dl=|
Tallinn|büroo A|üür|17.3-24.0|€/m²/kuu|Newsec|Baltic Office Market 2025 Q4|2026-01-31|2025-Q4|https://cdn.sanity.io/files/w1ytoec0/production/796b6fb95a2f6321a1e0f572014f7fa3163269f5.pdf?dl=|
Tallinn|büroo B|üür|16.5-22.0|€/m²/kuu|Newsec|Baltic Office Market 2025 Q4|2026-01-31|2025-Q4|https://cdn.sanity.io/files/w1ytoec0/production/796b6fb95a2f6321a1e0f572014f7fa3163269f5.pdf?dl=|tabeli järjestus PDF-tekstist
Tallinn|büroo C|üür|11.8-15.8|€/m²/kuu|Newsec|Baltic Office Market 2025 Q4|2026-01-31|2025-Q4|https://cdn.sanity.io/files/w1ytoec0/production/796b6fb95a2f6321a1e0f572014f7fa3163269f5.pdf?dl=|tabeli järjestus PDF-tekstist
Tallinn|büroo A|tootlus|7.00-7.50|%|Newsec|Baltic Office Market 2025 Q4|2026-01-31|2025-Q4|https://cdn.sanity.io/files/w1ytoec0/production/796b6fb95a2f6321a1e0f572014f7fa3163269f5.pdf?dl=|
Tallinn|büroo B|tootlus|7.75-9.00|%|Newsec|Baltic Office Market 2025 Q4|2026-01-31|2025-Q4|https://cdn.sanity.io/files/w1ytoec0/production/796b6fb95a2f6321a1e0f572014f7fa3163269f5.pdf?dl=|
Tallinn|büroo|prime_tootlus|7|%|Colliers|Baltic H1 2026 (vahendatud)|2026-08-01|2026-Q2|https://internationalinvestment.biz/en/litva/8751-baltic-property-investment-accelerates-in-2026.html|teisene allikas
Tallinn|büroo A spekulatiivne|vakants|8.5-9|%|Colliers|Baltic H1 2026 (vahendatud)|2026-08-01|2026-Q2|https://internationalinvestment.biz/en/litva/8751-baltic-property-investment-accelerates-in-2026.html|teisene allikas
Tallinn|kaubanduskeskus|vakants|2.2|%|Colliers|Baltic H1 2026 (vahendatud)|2026-08-01|2026-Q2|https://neighborhood.lv/?p=45701|teisene allikas
Tallinn|kaubanduskeskus prime|üür|23-45|€/m²/kuu|Colliers|Baltic H1 2026 (vahendatud)|2026-08-01|2026-H1|https://neighborhood.lv/?p=45701|teisene allikas
Tallinn|tööstus/logistika|vakants|5.2|%|Colliers|Baltic H1 2026 (vahendatud)|2026-08-01|2026-Q2|https://internationalinvestment.biz/en/estonia/8851-local-investors-gain-ground-in-estonia.html|teisene allikas
Tallinn|büroo|prime_tootlus|6.5-7|%|Inreal / Uus Maa / Latio|Baltic real estate overview 2026 Winter/Spring|2026-04-01|2025-H2|https://www.inreal.lt/wp-content/uploads/2026/04/Baltic_real_estate_overview_2025_2026-Winter_Spring_ED.pdf|
Tallinn|kaubanduskeskus|prime_tootlus|7.5-8|%|Inreal / Uus Maa / Latio|Baltic real estate overview 2026 Winter/Spring|2026-04-01|2025-H2|https://www.inreal.lt/wp-content/uploads/2026/04/Baltic_real_estate_overview_2025_2026-Winter_Spring_ED.pdf|
Tallinn|toidukauplus|prime_tootlus|6.75-7.25|%|Inreal / Uus Maa / Latio|Baltic real estate overview 2026 Winter/Spring|2026-04-01|2025-H2|https://www.inreal.lt/wp-content/uploads/2026/04/Baltic_real_estate_overview_2025_2026-Winter_Spring_ED.pdf|
"""


def _read(tekst):
    return [r.split("|") for r in tekst.strip().splitlines()]


def ehita(tee: Path) -> int:
    read = []

    def lisa(src, tase, piirkond, ülem, segment, näitaja, väärtus, ühik, märkus=""):
        allikas, väljaanne, kuupäev, periood, url = src
        read.append(dict(allikas=allikas, väljaanne=väljaanne, kuupäev=kuupäev, periood=periood, tase=tase,
                         piirkond=piirkond, ülem=ülem, segment=segment, näitaja=näitaja, väärtus=väärtus,
                         ühik=ühik, url=url, märkus=märkus))

    for p, tase, ülem, arv, pind, kesk, med, tmed in _read(KORTER_2025):
        for n, v, u in (("tehinguid", arv, "tk"), ("keskmine_pind", pind, "m²"), ("keskmine_eur_m2", kesk, "€/m²"),
                        ("mediaan_eur_m2", med, "€/m²"), ("tehingu_mediaan", tmed, "€")):
            lisa(MARU_AASTA, tase, p, ülem, "korter", n, v, u)
    for p, tase, ülem, arv, krunt, kesk, med in _read(ERAMU_2025):
        for n, v, u in (("tehinguid", arv, "tk"), ("keskmine_krunt", krunt, "m²"), ("keskmine_hind", kesk, "€"),
                        ("tehingu_mediaan", med, "€")):
            lisa(MARU_AASTA, tase, p, ülem, "eramu", n, v, u, "hoonestatud elamumaa (sh garaažid)")
    for p, tase, ülem, arv, pind, kesk, med, tmed in _read(ELAMUMAA_2025):
        for n, v, u in (("tehinguid", arv, "tk"), ("keskmine_pind", pind, "m²"), ("keskmine_eur_m2", kesk, "€/m²"),
                        ("mediaan_eur_m2", med, "€/m²"), ("tehingu_mediaan", tmed, "€")):
            lisa(MARU_AASTA, tase, p, ülem, "elamumaa", n, v, u, "hoonestamata elamumaa")
    for p, har, mets in _read(MAATULUNDUS_2025):
        tase = "riik" if p == "Eesti" else "maakond"
        lisa(MARU_AASTA, tase, p, "", "haritav maa", "mediaan_eur_ha", har, "€/ha")
        lisa(MARU_AASTA, tase, p, "", "metsamaa", "mediaan_eur_ha", mets, "€/ha", "kasvava metsaga")
    for a, k, kv, ko, ma in _read(INDEKSID):
        src = MARU_INDEKS[:3] + (f"{a}-{'I' * int(k) if int(k) < 4 else 'IV'}", MARU_INDEKS[4])
        lisa(src, "riik", "Eesti", "", "kinnisvara", "hinnaindeks", kv, "2003 III = 1")
        lisa(src, "riik", "Eesti", "", "korter", "hinnaindeks", ko, "2003 III = 1")
        lisa(src, "riik", "Eesti", "", "hoonestamata maa", "hinnaindeks", ma, "2003 III = 1")
    for allikas, väljaanne, kuupäev, periood, p, n, v, u, url, m in _read(FIRMAD):
        tase = "riik" if p in ("Eesti", "Eesti suuremad linnad") else "asula"
        lisa((allikas, väljaanne, kuupäev, periood, url), tase, p, "", "korter", n, v, u, m)
    for p, n, v, u, väljaanne, kuupäev, periood, url, m in _read(UUSARENDUS):
        lisa(("Pindi Kinnisvara", väljaanne, kuupäev, periood, url), "piirkond", p, "", "uusarendus", n, v, u, m)
    for p, seg, n, v, u, allikas, väljaanne, kuupäev, periood, url, m in _read(ARI):
        lisa((allikas, väljaanne, kuupäev, periood, url), "asula", p, "", seg, n, v, u, m)

    tee.parent.mkdir(parents=True, exist_ok=True)
    with tee.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=VÄLJAD)
        w.writeheader()
        w.writerows(read)
    return len(read)


if __name__ == "__main__":
    juur = Path(__file__).resolve().parents[1]
    n = ehita(juur / "andmed" / "turuulevaated.csv")
    print(f"Kirjutatud {n} rida → andmed/turuulevaated.csv")
