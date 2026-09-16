<?php
/**
 * Corps des dix articles « Curiosités » — corrections de faits, sources, clé dans l'intro,
 * slugs italiens. Appliqué le 2026-09-16 par le canal Novamira ; conservé ici comme TRACE
 * exacte de ce qui a été envoyé (jamais installé comme mu-plugin).
 *
 * D'OÙ ÇA VIENT. Franck, 16/09 : « il y a des choses dans les articles qu'il semble devoir
 * être modifié niveau SEO non ? » — puis « ok je te fais confiance ». Le dossier de relecture
 * est docs/CURIOSITES_RELECTURE_2026-09-16.md : chaque source y est LUE et citée.
 *
 * LA MÉTHODE, et pourquoi elle est ainsi : les articles ne sont jamais retapés. Chaque
 * changement est un couple (ancre exacte → texte neuf), et l'ancre doit apparaître UNE
 * fois dans le contenu en base, sinon l'article entier est laissé intact et nommé dans le
 * rapport. Les phrases neuves ont passé `utils.vocabulaire.trouver`, le contrôle du tiret
 * cadratin et celui de la contamination FR/IT avant d'entrer ici ; le contenu RÉSULTANT
 * est recontrôlé côté WordPress (clé exacte dans l'intro, liens externes, Wikipédia,
 * tiret, formes interdites) avant écriture. `wp_update_post` garde une révision : le
 * geste se défait depuis l'éditeur.
 *
 * $APPLIQUER = false rejoue le dry-run ; les ancres ne se retrouveront plus (le texte a
 * changé), et c'est voulu : ce fichier ne peut pas s'appliquer deux fois.
 */
global $wpdb;
$APPLIQUER = false;
$FORMES = array('frontiere', 'frontiera', 'langues regionales', 'lingue regionali', 'francoprovencal', 'francoprovenzale', 'patois', 'espace alpin', 'spazio alpino', 'transfrontalier', 'transfrontaliero', 'transfrontaliere', 'royaume de sardaigne', 'regno di sardegna', 'venise des alpes', 'venezia delle alpi');
$ART = array(
  8227 => array('cle' => 'curiosités de Turin', 'slug' => null, 'rep' => array(
      array('De quoi regarder la ville autrement avant d\'aller voir ce qui s\'y joue cette semaine.', 'Six curiosités de Turin à regarder avant d\'aller voir ce qui s\'y joue cette semaine.')
  )),
  8228 => array('cle' => 'curiosità di Torino', 'slug' => 'curiosita-torino', 'rep' => array(
      array('Ecco di che parlare prima di scoprire cosa succede in città questa settimana.', 'Sei curiosità di Torino da guardare prima di scoprire cosa succede in città questa settimana.'),
      array('MuseoTorino, l\'enciclopedia storica della città', '<a href="https://www.museotorino.it/view/s/7a06d9800b904a03916c354fe051b39c">MuseoTorino</a>, l\'enciclopedia storica della città'),
      array('La Porta Palatina, all\'estremità nord', 'La <a href="https://www.museotorino.it/view/s/fb25e1a8d7a34826bde45128ef1580c7">Porta Palatina</a>, all\'estremità nord'),
      array('Torino la chiama la fetta di polenta', 'Torino la chiama la <a href="https://www.museotorino.it/view/s/abf01b826074462abb075c610f88c230">fetta di polenta</a>'),
      array('il simbolo di Torino, la Mole Antonelliana, oggi', 'il simbolo di Torino, la <a href="https://www.museotorino.it/view/s/3b1a0b1906c64a22b777cfab5df1d54d">Mole Antonelliana</a>, oggi'),
      array('Oggi ospita il museo nazionale del Risorgimento', 'Oggi ospita il <a href="https://www.museorisorgimentotorino.it/en/palazzo-carignano/">museo nazionale del Risorgimento</a>'),
      array('il Villaggio Leumann resta protetto', 'il <a href="https://cultura.gov.it/luogo/ecomuseo-villaggio-operaio-leumann">Villaggio Leumann</a> resta protetto'),
      array('Parlamento subalpin degli', 'Parlamento subalpino degli')
  )),
  8229 => array('cle' => 'curiosités de Chambéry', 'slug' => null, 'rep' => array(
      array('De quoi en parler avant d\'aller voir ce qui se passe en ville cette semaine.', 'Cinq curiosités de Chambéry à regarder avant d\'aller voir ce qui se passe en ville cette semaine.'),
      array('la fontaine des Éléphants célèbre depuis 1838', 'la <a href="https://pop.culture.gouv.fr/notice/merimee/PA00118233">fontaine des Éléphants</a> célèbre depuis 1838'),
      array('son surnom le plus répandu, <strong>les quatre sans-culs</strong>', 'son <a href="https://www.chamberymontagnes.com/en/discover-chambery-montagnes-a-true-elixir-of-savoie/the-must-sees-in-chambery-montagnes/the-elephant-fountain/">surnom le plus répandu</a>, <strong>les quatre sans-culs</strong>'),
      array('En 2014, un chantier de restauration retrouve pour de bon cette partie manquante, restée cachée près de deux siècles dans la structure interne de la fontaine, avant que les éléphants ne reprennent leur place au printemps suivant.', 'Sculptés de face seulement et soudés au monument central, ils n\'ont jamais eu d\'arrière-train : ce qui manque n\'a pas été perdu, il n\'a jamais existé.'),
      array('Selon l\'office de tourisme Chambéry Montagnes, c\'est le plus grand carillon', 'Selon l\'office de tourisme <a href="https://www.chamberymontagnes.com/fiche/grand-carillon/">Chambéry Montagnes</a>, c\'est le plus grand carillon'),
      array('<strong>un décor en trompe-l\'œil</strong> : environ six mille mètres carrés, le plus vaste ensemble de ce genre en Europe. Les murs et les voûtes, qui semblent sculptés dans un style gothique flamboyant, sont en réalité entièrement peints ; le peintre Casimir Vicario en réalise l\'essentiel entre 1834 et 1835, après un premier passage de Fabrizio Sevesi en 1810, et une dernière campagne du peintre Bernard Sciolli en 1885 achève le chœur et les chapelles du bas-côté droit. Trois mains, trois générations, et un seul décor qui donne le change depuis près de deux siècles, sur un édifice qui commence sa vie bien plus modestement, comme chapelle conventuelle des Franciscains vers 1420, consacrée en 1488 et achevée seulement en 1585.', '<strong>un décor en trompe-l\'œil</strong>, le plus vaste décor peint d\'Europe selon <a href="https://explore.chamberymontagnes.com/fr/activites/cathedrale-saint-francois-de-sales">Chambéry Montagnes</a>. Les murs et les voûtes, qui semblent sculptés dans un style gothique flamboyant, sont en réalité entièrement peints, par Casimir Vicario, en 1834. Un seul décor qui donne le change depuis près de deux siècles, sur un édifice qui commence sa vie bien plus modestement, comme église du couvent des Franciscains, commencée en 1418 et achevée en 1587, cathédrale seulement depuis 1779.'),
      array('dans le vallon des Charmettes, l\'écrivain', 'dans le vallon des <a href="https://www.chambery.fr/302-les-charmettes.htm">Charmettes</a>, l\'écrivain')
  )),
  8230 => array('cle' => 'curiosità di Chambéry', 'slug' => null, 'rep' => array(
      array('Ecco di che parlare prima di scoprire cosa succede in città questa settimana.', 'Cinque curiosità di Chambéry da guardare prima di scoprire cosa succede in città questa settimana.'),
      array('<a href="https://fr.wikipedia.org/wiki/Fontaine_des_%C3%89l%C3%A9phants">Fontaine des Éléphants</a>', '<a href="https://pop.culture.gouv.fr/notice/merimee/PA00118233">Fontaine des Éléphants</a>'),
      array('Sono sempre gli elefanti a valerle il soprannome più diffuso', 'Sono sempre gli elefanti a valerle il <a href="https://www.chamberymontagnes.com/en/discover-chambery-montagnes-a-true-elixir-of-savoie/the-must-sees-in-chambery-montagnes/the-elephant-fountain/">soprannome più diffuso</a>'),
      array('Nel 2014, durante un restauro, gli operai hanno davvero trovato quella parte mancante, rimasta nascosta per quasi due secoli nella struttura interna della fontana, prima che gli elefanti tornassero al loro posto la primavera successiva.', 'Scolpiti solo di fronte e saldati al monumento centrale, non hanno mai avuto un posteriore: ciò che manca non è andato perduto, non è mai esistito.'),
      array('<strong>un inganno dipinto</strong>: circa seimila metri quadrati di <a href="https://fr.wikipedia.org/wiki/Cath%C3%A9drale_Saint-Fran%C3%A7ois-de-Sales_de_Chamb%C3%A9ry">trompe-l\'œil</a>, il più vasto complesso del genere in Europa. Le pareti e le volte, che sembrano intagliate in stile gotico fiammeggiante, sono in realtà interamente dipinte: il pittore Casimir Vicario ne realizza la parte principale tra il 1834 e il 1835, dopo un primo intervento di Fabrizio Sevesi nel 1810, e un\'ultima campagna del pittore Bernard Sciolli nel 1885 completa il coro e le cappelle della navata destra. Tre mani, tre generazioni, un solo inganno che regge da quasi due secoli, su un edificio che comincia la sua vita in modo ben più modesto, come cappella conventuale dei Francescani verso il 1420, consacrata nel 1488 e completata solo nel 1585.', '<strong>un inganno dipinto</strong>, il più vasto decoro dipinto d\'Europa secondo <a href="https://www.chamberymontagnes.com/en/fiche/st-francis-de-sales-cathedral/">Chambéry Montagnes</a>. Le pareti e le volte, che sembrano intagliate in stile gotico fiammeggiante, sono in realtà interamente dipinte, da Casimir Vicario, nel 1834. Un solo inganno che regge da quasi due secoli, su un edificio che comincia la sua vita in modo ben più modesto, come chiesa del convento dei Francescani, iniziata nel 1418 e completata nel 1587, cattedrale solo dal 1779.')
  )),
  8231 => array('cle' => 'curiosités d\'Aoste', 'slug' => null, 'rep' => array(
      array('De quoi comprendre la ville avant d\'aller voir ce qui s\'y passe cette semaine.', 'Six curiosités d\'Aoste à comprendre avant d\'aller voir ce qui s\'y passe cette semaine.'),
      array('le piémontais se parle en zone frontalière', 'le piémontais se parle dans la basse vallée'),
      array('le titsch à Gressoney-Saint-Jean', 'le <a href="https://www.lovevda.it/it/banca-dati/10/tradizioni/gressoney-la-trinite/il-titsch-il-dialetto-tedesco-di-gressoney/447">titsch</a> à Gressoney-Saint-Jean'),
      array('l\'assemblée valdôtaine crée le Conseil des Commis', 'l\'assemblée valdôtaine crée le <a href="https://www.consiglio.vda.it/fr/storia/brevi-cenni-storici">Conseil des Commis</a>'),
      array('À Gressoney-Saint-Jean, Castel Savoia se dresse', 'À Gressoney-Saint-Jean, <a href="https://www.lovevda.it/it/banca-dati/8/castelli-e-torri/gressoney-saint-jean/castel-savoia/873">Castel Savoia</a> se dresse'),
      array('il meurt assassiné la même année, et la reine', 'il meurt assassiné à Monza l\'année suivante, en 1900, et la reine'),
      array('L\'Arc d\'Auguste, photographié', 'L\'<a href="https://www.regione.vda.it/cultura/patrimonio/siti_archeologici/augusta_praetoria/arco/approfondimenti_i.aspx">Arc d\'Auguste</a>, photographié'),
      array('porte un toit de tuiles d\'ardoise depuis 1716 seulement, ajouté trois siècles après sa construction pour arrêter', 'porte un toit d\'ardoise depuis 1716 seulement, posé dix-sept siècles après sa construction pour arrêter'),
      array('Le cryptoportique du forum, une galerie à deux niveaux courant sous l\'ancienne place publique, compte parmi les rares vestiges de ce type encore visitables en Europe, aux côtés d\'Arles, de Reims et de Bavay ; sa fonction exacte reste discutée, entrepôt, réserve rituelle ou simple soutènement de la place au-dessus.', 'Le <a href="https://www.comune.aosta.it/it/page/criptoportico-forense">cryptoportique du forum</a>, une galerie à deux nefs sur trois côtés courant sous l\'ancienne place publique, s\'atteint par un escalier à côté de la cathédrale ; sa fonction exacte reste discutée, la Commune y voit une charnière entre l\'espace sacré des temples et la place profane.'),
      array('Non loin, la Porta Praetoria, l\'ancienne entrée principale de la ville romaine, garde ses deux arches jumelles presque intactes, l\'une pour les piétons, l\'autre pour les chars.', 'Non loin, la <a href="https://www.lovevda.it/it/banca-dati/8/architettura-romana/aosta/porta-praetoria/730">Porta Praetoria</a>, l\'ancienne entrée principale de la ville romaine, garde ses trois ouvertures presque intactes, la centrale pour les chars, les deux latérales pour les piétons.')
  )),
  8232 => array('cle' => 'curiosità di Aosta', 'slug' => 'curiosita-aosta', 'rep' => array(
      array('Ecco di che parlare prima di scoprire cosa succede in città questa settimana.', 'Sei curiosità di Aosta da capire prima di scoprire cosa succede in città questa settimana.'),
      array('il piemontese si parla nelle zone di confine', 'il piemontese si parla nella bassa valle'),
      array('il titsch a Gressoney-Saint-Jean', 'il <a href="https://www.lovevda.it/it/banca-dati/10/tradizioni/gressoney-la-trinite/il-titsch-il-dialetto-tedesco-di-gressoney/447">titsch</a> a Gressoney-Saint-Jean'),
      array('l\'assemblea valdostana crea il Conseil des Commis', 'l\'assemblea valdostana crea il <a href="http://www.consiglio.regione.vda.it/storia/brevi-cenni-storici">Conseil des Commis</a>'),
      array('A Gressoney-Saint-Jean, Castel Savoia si erge', 'A Gressoney-Saint-Jean, <a href="https://www.lovevda.it/it/banca-dati/8/castelli-e-torri/gressoney-saint-jean/castel-savoia/873">Castel Savoia</a> si erge'),
      array('muore assassinato lo stesso anno, e la regina', 'muore assassinato a Monza l\'anno seguente, nel 1900, e la regina'),
      array('L\'Arco di Augusto, fotografato', 'L\'<a href="https://www.regione.vda.it/cultura/patrimonio/siti_archeologici/augusta_praetoria/arco/approfondimenti_i.aspx">Arco di Augusto</a>, fotografato'),
      array('porta un tetto di tegole d\'ardesia solo dal 1716, aggiunto tre secoli dopo la costruzione per fermare', 'porta un tetto d\'ardesia solo dal 1716, posato diciassette secoli dopo la costruzione per fermare'),
      array('Il criptoportico del foro, una galleria a due livelli che corre sotto l\'antica piazza pubblica, è tra le poche vestigia di questo tipo ancora visitabili in Europa, insieme ad Arles, Reims e Bavay; la sua funzione esatta resta discussa, magazzino, riserva rituale o semplice sostegno della piazza soprastante.', 'Il <a href="https://www.comune.aosta.it/it/page/criptoportico-forense">criptoportico del foro</a>, una galleria a due navate su tre lati che corre sotto l\'antica piazza pubblica, si raggiunge da una scala accanto alla cattedrale; la sua funzione esatta resta discussa, il Comune vi legge una cerniera tra lo spazio sacro dei templi e la piazza profana.'),
      array('Poco distante, la Porta Praetoria, l\'antico ingresso principale della città romana, conserva le sue due arcate gemelle quasi intatte, una per i pedoni, l\'altra per i carri.', 'Poco distante, la <a href="https://www.lovevda.it/it/banca-dati/8/architettura-romana/aosta/porta-praetoria/730">Porta Praetoria</a>, l\'antico ingresso principale della città romana, conserva le sue tre aperture quasi intatte, la centrale per i carri, le due laterali per i pedoni.')
  )),
  8233 => array('cle' => 'curiosités d\'Annecy', 'slug' => null, 'rep' => array(
      array('De quoi regarder la ville autrement avant d\'aller voir ce qui s\'y joue cette semaine.', 'Sept curiosités d\'Annecy à regarder avant d\'aller voir ce qui s\'y joue cette semaine.'),
      array('Rosalie Montmasson naît en 1823 à Saint-Jorioz, au bord du lac. Blanchisseuse, elle devient la seule femme parmi les Mille de Garibaldi, embarquée déguisée en homme pour l\'expédition qui unifie l\'Italie, débarquant à Marsala en mai 1860 et soignant les blessés sur le terrain jusqu\'à Naples. Elle épouse ensuite Francesco Crispi, futur président du Conseil italien, qui tentera plus tard, une fois au pouvoir, de faire annuler ce mariage pour épouser une autre femme, un scandale qui menace un temps sa carrière de chef du gouvernement. Rosalie meurt pauvre à Rome en 1904, presque oubliée malgré son rôle dans l\'unité italienne.', '<a href="https://www.treccani.it/enciclopedia/rosalie-montmasson_(Dizionario-Biografico)/">Rosalie Montmasson</a> naît en 1823 à Saint-Jorioz, au bord du lac. Repasseuse à Turin à partir de 1849, elle y rencontre l\'exilé sicilien Francesco Crispi, qu\'elle épouse à Malte en 1854, puis devient la seule femme parmi les Mille de Garibaldi, embarquée déguisée en homme pour l\'expédition qui unifie l\'Italie, débarquant à Marsala en mai 1860 et soignant les blessés à Vita, Salemi et Alcamo. Crispi, devenu ministre, épouse civilement une autre femme en 1878, plaide la nullité du mariage de Malte quand la presse l\'accuse de bigamie, et doit démissionner (<a href="https://www.treccani.it/enciclopedia/francesco-crispi_(Dizionario-Biografico)/">Treccani</a>). Rosalie meurt à Rome en 1904, avec une rente de la Maison royale pour toute reconnaissance.'),
      array('Dans un tout autre siècle, le palais de l\'Île, dont la silhouette fait tous les calendriers, sert de prison à Marguerite Frichelet-Avet, servante de Thônes qui soigne les blessés et sonne le tocsin contre les troupes révolutionnaires françaises venues mater le soulèvement paysan de 1793. Elle est fusillée sur ce qui est aujourd\'hui le Pâquier, <strong>une résistance restée sans monument</strong>, dans une ville qui n\'a jamais cherché à en garder la trace.', 'Dans un tout autre siècle, <a href="https://journals.openedition.org/rga/3229">Marguerite Frichelet-Avet</a>, servante lettrée de Thônes, ravitaille les paysans de la vallée soulevés en 1793 contre les troupes révolutionnaires françaises, est accusée d\'avoir sonné le tocsin, jugée à Annecy sans défenseur et fusillée le 18 mai sur le Champ-de-Mars, l\'actuel Pâquier, <strong>une résistance que les promeneurs du Pâquier ne soupçonnent pas</strong>.'),
      array('avant d\'être élu, en 1440, le dernier antipape de l\'histoire sous le nom de Félix V', 'avant d\'être élu, en 1439, le dernier antipape de l\'histoire sous le nom de <a href="https://www.treccani.it/enciclopedia/antipapa-felice-v_(Enciclopedia-dei-Papi)/">Félix V</a>'),
      array('François de Sales devient évêque de Genève', '<a href="https://www.diocese-annecy.fr/le-diocese/les-saint-e-s-et-les-grandes-figures/saint-francois-de-sales/biographie-saint-francois-de-sales">François de Sales</a> devient évêque de Genève'),
      array('Claude Gabriel de Launay naît en 1786 à Duingt', '<a href="https://www.treccani.it/enciclopedia/gabriele-de-launay_(Dizionario-Biografico)/">Claude Gabriel de Launay</a> naît en 1786 à Duingt'),
      array('président du Conseil du royaume de Savoie', 'président du Conseil des États de Savoie'),
      array('Germain Sommeiller, né à Saint-Jeoire', '<a href="https://www.treccani.it/enciclopedia/germain-sommeiller/">Germain Sommeiller</a>, né à Saint-Jeoire'),
      array('En 1896, Maxime-Antoine Ruphy fonde la chocolaterie des Marquisats', 'En 1896, Maxime-Antoine Ruphy fonde la <a href="https://musees.annecy.fr/Patrimoines/Decouvrez-nos-patrimoines/Annecy/L-ancienne-Chocolaterie-des-Marquisats">chocolaterie des Marquisats</a>'),
      array('Rebaptisée Chocolaterie d\'Annecy en 1907', 'Cédée en 1905 à son cousin Charles Ruphy et rebaptisée Chocolaterie d\'Annecy')
  )),
  8234 => array('cle' => 'curiosità di Annecy', 'slug' => null, 'rep' => array(
      array('Ecco di che parlare prima di scoprire cosa succede in città questa settimana.', 'Sette curiosità di Annecy da guardare prima di scoprire cosa succede in città questa settimana.'),
      array('Rosalie Montmasson nasce nel 1823 a Saint-Jorioz, sulla riva del lago. Lavandaia, diventa l\'unica donna tra i Mille di Garibaldi, imbarcata travestita da uomo per la spedizione che unifica l\'Italia, sbarcando a Marsala nel maggio 1860 e curando i feriti fino a Napoli. Sposa poi Francesco Crispi, futuro presidente del Consiglio italiano, che una volta al potere tenterà di far annullare quel matrimonio per sposarne un\'altra, uno scandalo che minaccia per un tempo la sua carriera di capo del governo. Rosalie muore povera a Roma nel 1904, quasi dimenticata nonostante il suo ruolo nell\'unità italiana.', '<a href="https://www.treccani.it/enciclopedia/rosalie-montmasson_(Dizionario-Biografico)/">Rosalie Montmasson</a> nasce nel 1823 a Saint-Jorioz, sulla riva del lago. Stiratrice a Torino dal 1849, vi incontra l\'esule siciliano Francesco Crispi, che sposa a Malta nel 1854, poi diventa l\'unica donna tra i Mille di Garibaldi, imbarcata travestita da uomo per la spedizione che unifica l\'Italia, sbarcando a Marsala nel maggio 1860 e curando i feriti a Vita, Salemi e Alcamo. Crispi, diventato ministro, sposa civilmente un\'altra donna nel 1878, sostiene la nullità del matrimonio di Malta quando la stampa lo accusa di bigamia, e deve dimettersi (<a href="https://www.treccani.it/enciclopedia/francesco-crispi_(Dizionario-Biografico)/">Treccani</a>). Rosalie muore a Roma nel 1904, con un vitalizio della Casa reale come unico riconoscimento.'),
      array('In un secolo del tutto diverso, il Palais de l\'Île, la cui sagoma riempie tutti i calendari, serve da prigione a Marguerite Frichelet-Avet, domestica di Thônes che cura i feriti e suona a martello contro le truppe rivoluzionarie francesi venute a reprimere la rivolta contadina del 1793. Viene fucilata su quello che oggi è il Pâquier, <strong>una resistenza rimasta senza monumento</strong>, in una città che non ha mai cercato di conservarne la traccia.', 'In un secolo del tutto diverso, <a href="https://journals.openedition.org/rga/3229">Marguerite Frichelet-Avet</a>, domestica istruita di Thônes, rifornisce i contadini della valle insorti nel 1793 contro le truppe rivoluzionarie francesi, è accusata di aver suonato a martello, giudicata ad Annecy senza difensore e fucilata il 18 maggio sul Champ-de-Mars, l\'attuale Pâquier, <strong>una resistenza che chi passeggia sul Pâquier non sospetta</strong>.'),
      array('eletto, nel 1440, l\'ultimo antipapa della storia con il nome di Felice V', 'eletto, nel 1439, l\'ultimo antipapa della storia con il nome di <a href="https://www.treccani.it/enciclopedia/antipapa-felice-v_(Enciclopedia-dei-Papi)/">Felice V</a>'),
      array('Francesco di Sales diventa vescovo di Ginevra', '<a href="https://www.diocese-annecy.fr/le-diocese/les-saint-e-s-et-les-grandes-figures/saint-francois-de-sales/biographie-saint-francois-de-sales">Francesco di Sales</a> diventa vescovo di Ginevra'),
      array('Claude Gabriel de Launay nasce nel 1786 a Duingt', '<a href="https://www.treccani.it/enciclopedia/gabriele-de-launay_(Dizionario-Biografico)/">Claude Gabriel de Launay</a> nasce nel 1786 a Duingt'),
      array('presidente del Consiglio del regno di Savoia', 'presidente del Consiglio degli Stati Sabaudi'),
      array('Germain Sommeiller, nato a Saint-Jeoire', '<a href="https://www.treccani.it/enciclopedia/germain-sommeiller/">Germain Sommeiller</a>, nato a Saint-Jeoire'),
      array('Nel 1896, Maxime-Antoine Ruphy fonda la cioccolateria dei Marquisats', 'Nel 1896, Maxime-Antoine Ruphy fonda la <a href="https://musees.annecy.fr/Patrimoines/Decouvrez-nos-patrimoines/Annecy/L-ancienne-Chocolaterie-des-Marquisats">cioccolateria dei Marquisats</a>'),
      array('Ribattezzata Chocolaterie d\'Annecy nel 1907', 'Ceduta nel 1905 al cugino Charles Ruphy e ribattezzata Chocolaterie d\'Annecy')
  )),
  8235 => array('cle' => 'curiosités de Nice', 'slug' => null, 'rep' => array(
      array('De quoi comprendre la ville avant d\'aller voir ce qui s\'y joue cette semaine.', 'Trois curiosités de Nice à comprendre avant d\'aller voir ce qui s\'y joue cette semaine.'),
      array('Nice célèbre depuis la fin du seizième siècle, par un premier monument puis un hommage encore rendu aujourd\'hui, sa figure légendaire de la résistance, Catherine Ségurane, la lavandière qui se serait battue au bastion Sincaire avec son battoir, symbole', 'Nice honore encore aujourd\'hui, chaque année, rue Sincaire, sa figure légendaire de la résistance, <a href="https://www.explorenicecotedazur.com/en/culture/stele-en-memoire-de-catherine-segurane/">Catherine Ségurane</a>, la lavandière qui aurait repoussé l\'ennemi avec son battoir le 15 août 1543, symbole'),
      array('La socca descend de la farinata génoise, une galette de pois chiches apportée par des marins ligures dès le treizième siècle et adaptée', 'La <a href="https://www.explorenicecotedazur.com/en/explore/art-of-living/gastronomy-and-local-produce/nicoise-recipes/la-socca/">socca</a> descend de la farinata génoise, une galette de pois chiches apportée par des marins ligures et adaptée'),
      array('La pissaladière descend de la pissa d\'Andrea, créée en 1490 en l\'honneur de l\'amiral génois Andrea Doria :', 'La <a href="https://www.explorenicecotedazur.com/en/explore/art-of-living/gastronomy-and-local-produce/nicoise-recipes/la-pissaladiere/">pissaladière</a> descend sans doute d\'une recette génoise de la fin du quinzième siècle, selon l\'office de tourisme, cousine de la piscialandrea que la Ligurie nomme d\'après l\'amiral génois Andrea Doria :'),
      array('En 1832, le roi Charles-Albert crée le Consiglio d\'Ornato', 'En 1832, le roi Charles-Albert crée le <a href="https://www.departement06.fr/documents/Import/decouvrir-les-am/rr158-ornato.pdf">Consiglio d\'Ornato</a>'),
      array('l\'architecte Pietro Bonvicini bâtit la porte de Turin, copiée sur une porte dessinée un siècle et demi plus tôt par Filippo Juvarra pour Turin elle-même, marquant le début', 'l\'architecte Pietro Bonvicini bâtit la <a href="https://jacquesguiaud.academia-nissarda.org/zoom-sur/album-aquarelle/item/nice-la-porte-de-turin">porte de Turin</a>, copiée sur l\'une des portes royales de la capitale, marquant le début')
  )),
  8236 => array('cle' => 'curiosità di Nizza', 'slug' => 'curiosita-nizza', 'rep' => array(
      array('Ecco di che parlare prima di scoprire cosa succede in città questa settimana.', 'Tre curiosità di Nizza da capire prima di scoprire cosa succede in città questa settimana.'),
      array('Nizza celebra dalla fine del Cinquecento, con un primo monumento e un omaggio ancora oggi rinnovato, la sua figura leggendaria della resistenza, Catherine Ségurane, la lavandaia che si sarebbe battuta al bastione Sincaire con la sua asse da bucato, simbolo', 'Nizza onora ancora oggi, ogni anno, in rue Sincaire, la sua figura leggendaria della resistenza, <a href="https://www.explorenicecotedazur.com/en/culture/stele-en-memoire-de-catherine-segurane/">Catherine Ségurane</a>, la lavandaia che avrebbe respinto il nemico con la sua asse da bucato il 15 agosto 1543, simbolo'),
      array('La socca discende dalla farinata genovese, una focaccia di ceci portata dai marinai liguri già nel Duecento e adattata', 'La <a href="https://www.explorenicecotedazur.com/en/explore/art-of-living/gastronomy-and-local-produce/nicoise-recipes/la-socca/">socca</a> discende dalla farinata genovese, una focaccia di ceci portata dai marinai liguri e adattata'),
      array('La pissaladière discende dalla pissa d\'Andrea, creata nel 1490 in onore dell\'ammiraglio genovese Andrea Doria:', 'La <a href="https://www.explorenicecotedazur.com/en/explore/art-of-living/gastronomy-and-local-produce/nicoise-recipes/la-pissaladiere/">pissaladière</a> discende probabilmente da una ricetta genovese della fine del Quattrocento, secondo l\'ufficio del turismo, cugina della piscialandrea che la Liguria chiama così dall\'ammiraglio genovese Andrea Doria:'),
      array('Nel 1832, il re Carlo Alberto crea il Consiglio d\'Ornato', 'Nel 1832, il re Carlo Alberto crea il <a href="https://www.departement06.fr/documents/Import/decouvrir-les-am/rr158-ornato.pdf">Consiglio d\'Ornato</a>'),
      array('l\'architetto Pietro Bonvicini costruisce la porta di Torino, copiata su una porta disegnata un secolo e mezzo prima da Filippo Juvarra per Torino stessa, a segnare l\'inizio', 'l\'architetto Pietro Bonvicini costruisce la <a href="https://jacquesguiaud.academia-nissarda.org/zoom-sur/album-aquarelle/item/nice-la-porte-de-turin">porta di Torino</a>, copiata su una delle porte regie della capitale, a segnare l\'inizio')
  ))
);

$rapport = array(); $ecrits = 0;
foreach ($ART as $id => $a) {
    $p = get_post($id); if (!$p) { $rapport[$id] = 'ABSENT'; continue; }
    $c = $p->post_content; $ancres_ko = array();
    foreach ($a['rep'] as $r) { $n = substr_count($c, $r[0]); if ($n !== 1) { $ancres_ko[] = mb_substr($r[0], 0, 60) . " ×$n"; } }
    if ($ancres_ko) { $rapport[$id] = array('ANCRES_KO' => $ancres_ko); continue; }
    foreach ($a['rep'] as $r) { $c = str_replace($r[0], $r[1], $c); }
    // contrôles sur le contenu RÉSULTANT
    preg_match('/<p>(.*?)<\/p>/s', $c, $m); $intro = wp_strip_all_tags($m[1]);
    preg_match_all('/href="([^"]+)"/', $c, $h);
    $ext = 0; foreach ($h[1] as $u) { if (strpos($u, 'agendasabauda.eu') === false) $ext++; }
    $plat = remove_accents(mb_strtolower(wp_strip_all_tags($c)));
    $interdits = array(); foreach ($FORMES as $f) { if (strpos($plat, $f) !== false) $interdits[] = $f; }
    $rapport[$id] = array(
        'cle_exacte_dans_intro' => (mb_stripos($intro, $a['cle']) !== false),
        'liens_externes' => $ext,
        'wikipedia' => substr_count($c, 'wikipedia'),
        'tiret_cadratin' => substr_count($c, '—'),
        'vocab_interdit' => $interdits,
        'intro' => mb_substr($intro, -120),
        'slug' => $a['slug'] ? ($p->post_name . ' → ' . $a['slug']) : $p->post_name,
        'longueur' => mb_strlen($c),
    );
    if ($APPLIQUER) {
        $args = array('ID' => $id, 'post_content' => wp_slash($c));
        if ($a['slug']) { $args['post_name'] = $a['slug']; }
        $res = wp_update_post($args, true);
        $rapport[$id]['ecrit'] = is_wp_error($res) ? $res->get_error_message() : 'ok';
        if (!is_wp_error($res)) $ecrits++;
    }
}
return array('_mode' => $APPLIQUER ? 'ÉCRITURE' : 'dry-run', 'ecrits' => $ecrits, 'rapport' => $rapport);
