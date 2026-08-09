"""Vocabolari italiani per il riconoscimento dei nomi di persona.

Tre insiemi, con ruoli diversi e complementari:

* ``FIRST_NAMES`` — nomi propri. Trovarne uno e' il segnale piu' forte:
  la parola successiva, se scritta con l'iniziale maiuscola, e' quasi
  sempre il cognome, anche se il cognome non compare in nessun elenco.
* ``SURNAMES`` — cognomi frequenti. Servono per i casi in cui il nome di
  battesimo manca ("il dott. Ferraris", "Rossi ha confermato").
* ``COMMON_CAPITALIZED`` — parole italiane che capita di trovare con
  l'iniziale maiuscola e che nomi non sono: mesi, saluti, titoli, enti,
  citta'. E' l'elenco che tiene a bada l'euristica del cognome.

Nessun elenco di nomi puo' essere completo, e questo non lo e'. Per
questo il riconoscimento non si affida solo agli elenchi: vedi
``mr_rao.privacy`` per le regole di contesto (intestazioni delle mail,
titoli professionali, parola accanto a un indirizzo di posta).
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Nomi propri
# ---------------------------------------------------------------------------

_FIRST_NAMES_M = """
abbondio abele abramo achille adalberto adamo adelchi adelmo adolfo adone
adriano agapito agostino alan alarico alberico alberto albino alcide aldo
aleandro alessandro alessio alfio alfonso alfredo alighiero alvaro amadeo
amato ambrogio amedeo americo amerigo amilcare amleto amos anacleto andrea
angelo aniello annibale ansaldo anselmo antenore antimo antonello antonino
antonio arcangelo archimede arduino aristide armando arnaldo arnolfo arrigo
arturo ascanio astorre attilio augusto aurelio aureliano ausonio azeglio
baldassarre baldo barnaba bartolo bartolomeo basilio bassano battista
benedetto beniamino benito benvenuto berardo bernardino bernardo berto
biagio bonaventura bonifacio boris brando bruno bruzio
caio calogero camillo candido carlo carmelo carmine casimiro cataldo
cecilio celeste celestino celso cesare cesarino chicco cipriano cirillo
ciriaco ciro claudio clemente cleto colombano cornelio corrado cosimo
cosma costantino costanzo cristian cristiano cristoforo curzio
damiano daniel daniele dante dario davide decio delfino demetrio denis
desiderio diego dino diomede dionigi dionisio divo domenico dominic donato
donatello doriano duccio dume duilio durante
edgardo edmondo edoardo efisio egidio egisto elia eliano eligio elio eliseo
elmo emanuele emidio emiliano emilio ennio enrico enzo eraldo erasmo ercole
erik ermanno ermenegildo ermes erminio ernesto eros ettore eugenio eusebio
evaristo evasio ezechiele ezio
fabiano fabio fabrizio fausto federico fedele felice ferdinando fermo
fernando ferruccio filiberto filippo fiorenzo firmino flavio floriano
fortunato francesco franco fulvio furio
gabriele gaetano galdino galeazzo gastone gaudenzio gennaro gerardo geremia
germano gerolamo gervasio giacinto giacobbe giacomo giampaolo giampiero
gianandrea gianbattista giancarlo gianfranco gianluca gianluigi gianmarco
gianmaria gianni gianpaolo gianpiero gianpietro giordano giorgio giosue
giovanni giovanbattista girolamo giuliano giulio giuseppe giustino giusto
goffredo graziano gregorio guelfo guerrino guglielmo guido gustavo
ignazio igor ilario ilario immacolato innocenzo iolando ippolito iris
isaia isidoro italo ivan ivano ivo
jacopo jari jonathan jury
lamberto lanfranco lauro lazzaro leandro leo leonardo leone leonello
leopoldo liberato liberto lino lino lionello livio lodovico lorenzo loris
luca luciano lucio ludovico luigi luigino
macario maddalena madio manfredi manlio manuel marcello marco mariano
marino mario martino marzio massimiliano massimo matteo mattia maurizio
mauro mederico melchiorre michelangelo michele milo mirco mirko modesto
moreno mose muzio
napoleone narciso natale natalino nazareno nazzareno neri nestore niccolo
nicola nicolo nino noe norberto nunzio
oddone odino olimpio olindo omar omero onofrio orazio oreste orfeo orlando
oronzo orsino oscar osvaldo ottaviano ottavio ottone ovidio
pacifico palmiro pancrazio panfilo paolino paolo pardo pasquale patrizio
pellegrino peppino piergiorgio pierluigi piermaria pierpaolo piero
piersilvio pietro pio pierfrancesco placido plinio policarpo pompeo
ponziano porfirio primo prospero protasio publio
quintino quirico quirino
raffaele raffaello raimondo ramiro raniero raoul raul reginaldo remigio
remo renato renzo riccardo rinaldo rino roberto rocco rodolfo rodrigo
rolando romano romeo romolo ronaldo rosario rosolino ruben rudi ruggero
ruggiero rutilio
sabatino sabino salvatore salvo samuele sandro sante santi santino saverio
sebastiano secondo serafino sergio settimio severino severo sigfrido
sigismondo silvano silverio silvestro silvio simone sirio sisto siro
sofronio spartaco stanislao stefano stelvio taddeo tancredi teobaldo
teodoro terenzio tiberio tiziano tobia tolomeo tommaso torquato toti
tullio turi
ubaldo uberto ugo ugolino ulderico ulisse umberto urbano
valentino valerio valeriano vanni vasco venanzio ventura vero vespasiano
vidal vieri vincenzo vinicio virgilio virginio vitale vito vittore
vittorio vladimiro
walter werner wilfredo william
zaccaria zeno zenone zaverio
"""

_FIRST_NAMES_F = """
ada adalgisa addolorata adelaide adele adelina adriana agata agnese agostina
aida alba alberta albina alda alessandra alessia alfonsina alice alida
alina allegra alma altea amalia amanda ambra amelia amina anastasia
andreina angela angelica angiolina anita anna annabella annalisa annamaria
annarita annunziata antonella antonia antonietta apollonia arianna
armanda armida assunta astrid aurelia aurora ausilia azzurra
barbara beatrice benedetta benilde berenice bernadette bertilla bianca
brigida bruna brunella
camilla candida carla carlotta carmela carmen carola carolina caterina
catia cecilia celeste celestina chiara cinzia clara clarissa claudia
clelia clementina cleofe cloe clotilde colomba concetta consuelo cornelia
corinna cosima costanza cristiana cristina
dafne dalia damiana daniela daria debora delfina delia delia denise desiree
diamante diana diletta dina dionisia doelia dolores domenica dominga
donatella donata dora dorotea
edda edvige egle elda elena eleonora elettra eliana elide elisa elisabetta
ella eloisa elsa elvira ema emanuela emilia emma enrica erica erika ermelinda
erminia ersilia esmeralda ester eufemia eugenia eulalia eva evelina
fabia fabiana fabiola fanny fausta federica fedora felicita fernanda fiamma
filippa filomena fiona fiorella fiorenza flaminia flavia flora floriana
franca francesca fulvia
gabriella gaetana gaia galatea gemma generosa genoveffa germana gessica
giada gianna gianfranca gigliola gilda gina ginevra gioconda gioia giordana
giorgia giorgina giovanna gisella giuditta giulia giuliana giulietta
giuseppa giuseppina giustina glenda gloria grazia graziella grazia greta
guendalina
ida ilaria ilenia ilva immacolata ines iolanda iole ione irene iride iris
irma isa isabella isadora iside isotta ivana ivonne
jessica jole jolanda
katia
lara laura lavinia lea leda letizia lia lidia liliana lina linda lisa livia
loredana lorella lorena lorenza loretta luana lucia luciana lucilla lucrezia
ludovica luigia luisa luisella luna
maddalena mafalda magda manuela mara marcella maresa margherita maria
mariangela marianna maricla mariella marilena marina marinella marisa
marta martina marzia matilde maura maurizia melania melissa mercedes
michela michelina milena mimma mira mirella miriam mirta modesta monica
morena
nadia natalia natalina nella nerina neve nicoletta nilde nina ninetta noemi
norma novella nuccia nunzia
olga olimpia olga oliva olivia ombretta ondina onorina orietta ornella
orsola ottavia
pace palma pamela paola paolina pasqualina patrizia perla petra pia pierina
pina piera placida polissena primavera priscilla
rachele raffaella rebecca regina renata riccarda rina rita roberta romana
romina rosa rosalba rosalia rosanna rosaria rosella rosetta rosina rossana
rossella rita ruggera
sabina sabrina samanta samantha sandra santa sara saveria scilla sebastiana
selene selvaggia serafina serena severina sibilla silvana silvia simona
simonetta sofia sonia speranza stefania stella susanna sveva
tamara tania tarcisia tea teodolinda teodora teresa tina tiziana tosca
tullia
ugolina
valentina valeria vanda vanessa vanna venera vera verdiana veronica vilma
vincenza viola violante violetta virginia vitalia vittoria viviana
wanda wilma
zaira zelinda zita zoe
"""

_FIRST_NAMES_EXTRA = """
alan alex andres anthony brian bruce carlos charles chris christian daniel
david dennis dylan edward eric frank george henry jack james jason john
jonathan joseph kevin louis luis mark martin matthew michael nicholas oliver
patrick paul peter philip richard robert ryan samuel scott sean simon
stephen steven thomas timothy tony victor vincent william
alexandra amanda amy angela ann anna barbara carol caroline catherine
charlotte christine claire diana donna elizabeth emily emma helen jane
janet jennifer jessica joan julia karen kate laura linda lisa louise
margaret maria marie mary michelle nancy nicole patricia rachel rebecca
rose ruth sandra sarah sharon sophie stephanie susan teresa victoria
"""

FIRST_NAMES: frozenset[str] = frozenset(
    _FIRST_NAMES_M.split() + _FIRST_NAMES_F.split() + _FIRST_NAMES_EXTRA.split()
)


# ---------------------------------------------------------------------------
# Cognomi
# ---------------------------------------------------------------------------

_SURNAMES = """
abate abbate abbruzzese acerbi acquaviva adamo agnelli agostinelli agostini
aiello ajello alberti albertini alessandri alessandrini alfano alfieri
aliberti alonzo altieri amadei amadori amato ambrosi ambrosini ambrosio
amendola amici amoroso amoruso ancona andreani andreoli andreotti andreozzi
angelini angeloni angelucci angiolini annunziata antinori antonelli antonini
apollonio aquino arcuri ardizzone arena argenti arienti arlotta armani
arnaldi arnone arrighi artioli ascoli asaro assenza astolfi atzeni audino
augello aurelio avallone avanzi averna azzarello azzolini
baccarini bacci bacchi badalamenti badini baglio bagnara bagnoli balboni
baldassarre baldi baldini baldo balestra balestrieri ballarin ballerini
balsamo balzano bandini banfi barbagallo barbaro barbato barbera barbero
barbieri barbini barbone barca bardi barile barletta barone barra barrera
barsotti bartoli bartolini bartolomei bartolucci basile bassani bassi
bassetti basso bastianelli battaglia battaglini battistelli battisti
bazzani beccaria bellagamba bellandi bellani bellavia bellelli belli
bellini bello bellomo bellucci belluzzi beltrame beltrami belotti benassi
benatti benedetti benedetto benelli beni benigni benini bentivoglio benvenuti
berardi berardo bergamaschi bergamini bernardi bernardini bernardo bernasconi
bernini beretta bertacchi bertani bertelli bertini berto bertoldi bertolini
bertolotti bertoni bertozzi bertucci besana bettini bevilacqua biagi biagini
biagioli bianchi bianchini bianco biasi biffi bigi bilotta binaghi bini
bisceglia bisogno bissi bizzarri boccaccio bocchi boccia boffa bogni boldrini
bollini bolognesi bombardieri bona bonaccorsi bonanni bonatti bonavita
bonaventura bonazzi bondi bonelli bonetti bonfanti bonfiglio bongiorno
boni bonifacio bonini bonomi bonomo bonora bordi bordoni borelli borghese
borghi borgia borgna bortolotti boscaino boschetti boschi bosco bosi bossi
botta bottari bottero bove bozzi bracci bragaglia brambilla branca brandi
brasca bravi bregoli brescia bressan bresciani brigida brigiotti brizzi
brocca brogi bruni brunelli brunetti bruno bruschi bucci bucciarelli
buffa bugli buonanno buonocore buono burgio busi bussolati busti buttiglione
buzzi
caccamo caccia caccialupi cadeddu cafiero cagnazzo caiazzo calabrese calabria
calamai calandra calcagno caldarelli caldarola calderone califano calvi
calvino camerini caminiti cammarata cammarota campagna campanella campani
campisi campo canale candela canella canepa cangiano canino cannata cannizzaro
canonico cantarella cantoni canzian capasso capece capelli capitani capobianco
capodanno caponi caporale cappelletti cappelli cappellini capuano capurso
caputo carbone carbonell carboni cardella cardillo cardone carella cariello
carini carlesi carletti carli carlini carminati carnevale carollo caroli
carone carosi carotenuto carpentieri carra carraro carrera carrieri carta
caruso casadei casagrande casale casalini casamassima casarini cascio caselli
casini caso cassano cassese cassetta castagna castagnoli castaldi castaldo
castellani castellano castelli castiglione castiglioni catalano catania
catanzaro catena cattaneo cattani caudullo cavaliere cavallaro cavalieri
cavallini cavallo cavazza cavazzoni cazzola ceccarelli cecchi cecchini
cecconi celentano celeste cella cellini cenci cerasoli cerino cerqua cerri
cerrone cerulli cervelli cesari cesarini chessa chiaramonte chiarelli
chiarini chiaro chiavelli chiesa chieti chinaglia chiodi chiodini chiriaco
chirico ciampi ciani ciaramella cicala ciccarelli ciccone cicero cicerone
cimino cinelli cinquini cioffi cipolla cipriani ciravolo cirelli citarella
citro ciuffo civitelli clemente coco codispoti cogliandro colangelo colella
coletta colicchio colombo colonna colucci columbro comini compagnone
condello conforti coniglio consiglio conte conti contini coppola corazza
corbelli cordova corleone cornacchia corona correale corridori corsi
corsini corso cortellessa cortese cortesi corvino cosentino cosenza cosma
cossu costa costantini costanzo cotugno cozzi cremona crescenzi crespi
cresta crippa crisafulli criscuolo crispino cristallo cristiano crivelli
croce crocetti crucitti cucchi cuccia cuccia cucciniello cuffaro cugini
cuoco cuomo cupido curcio curti cusenza cutrupi
dagostino dalessandro dalessio damato damiani damico dandrea dangelo
danieli dantona darienzo davanzo davoli decaro decarlo decesare defalco
defelice degiorgi degregorio delaurentiis delbono delfino delgiudice
dellabella dellaquila dellorto delmonte deloreto deluca delvecchio demaria
demarco demartino demasi demattia demeo demichele demurtas denaro denicola
deniro depalma depaoli depaolis derosa desantis desiderio desimone despina
detommaso devito diamanti diana diaz didonato dilorenzo dimartino dimarzio
dimatteo dimauro dinardo dinatale dinardo diodato dionisi dipalma dipietro
dirocco disalvo disanto disimone distefano ditommaso divita dolce domenico
dominici donadio donati donatiello dondi donzelli dorigo dorio dossena
dotti dragone drago duca duranti durante
eboli elia emanuele emiliani ermini errico esposito evangelisti
fabbri fabbrini fabbro fabiani fabrizi facchinetti facchini faedda faenza
fagiani faggiano fagnani falcinelli falco falcone falconi falzone famiglietti
fanara fanelli fantini fantoni fanucci faraone farina farinelli farolfi
fasano fasoli fassino fattori fausti fava favaro favero fazio fedele federici
federico fedi felici feliciano ferrandino ferrante ferrara ferrari ferrarini
ferraro ferrero ferretti ferri ferrini ferro fiaschi ficarra fidanza figini
filippi filippini filippone filomena fina finelli fini fino fiore fiorentini
fiorentino fioretti fiori fiorillo fiorini firrincieli fischetti fissore
fistarol fiumara flaminio flauto foa focaccia foglia fois folco fontana
fontanella foppa forcella forlani formica formisano fornara fornari forte
forti fortini fortunato foschi fossati fracasso franceschelli franceschi
franceschini francesconi franchi franchini franco frangipane frascati
frassinetti frattini frau frega freni fresta frigerio frigo frisone fumagalli
funari furlan furlani fusaro fusco fuschi
gabrielli gaeta gaetani gagliardi gagliano galante galanti galassi galati
galdi galeazzi galeotti galimberti gallelli galletti galli gallina gallo
galluzzo gamba gambardella gambino gandolfi gangemi garau garbarino gardini
gargano gargiulo garofalo garofano garuti gasparini gasparro gatta gatti
gatto gaudino gavazzi gazzola gelmini gemelli gennaro gentile gentili
geraci gerardi germano ghezzi ghiglione ghio ghirardi giachetti giacobbe
giacomelli giacomini giacomo giaconia giaimo giammarino gianfreda giannelli
giannetti gianni giannini giannone giansanti giardina giardino gibilisco
gigante giglio gilardi gioia giordani giordano giorgi giorgini giovannelli
giovannetti giovannini girardi girardi giuliani giuliano giunta giuriati
giusti giustiniani gnocchi gobbi goffredo gori gorini govoni gozzi gramigna
granata grande grandi granieri grassi grasso gravina graziani grazioli greco
gregori gregorio grieco grifoni grillo grimaldi grisanti grisenti gritti
grossi grosso grotta gualtieri guarino guarnieri guasconi guerra guerrieri
guerrini guglielmi guglielmo guida guidetti guidi guidotti gullo gusmeroli
iacobelli iacobucci iacovelli iacovone iadanza iannaccone iannelli iannone
iannuzzi iavarone ieva imbimbo imperato impellizzeri incardona indelicato
infantino ingrassia innocenti inzaghi iodice iorio iozzo ippolito irace
isgro iuliano izzo
labate laganà lagana lai laino lala lamanna lamberti lambertini lami
lanciotti landi landini lanfranchi langella lanza lanzafame lanzetta laporta
lapietra lapolla larosa larussa lattanzi lattanzio laudicina laurenti
laurenza lauria lauro lauta lavagna laviani lazzarini lazzaro lecce lena
lentini leo leonardi leone leoni leonetti leotta lepore leporini letizia
levi liberati libero licata licciardello liguori lima limongi lippi lisi
liuzzi livi lo bello lobianco lo cascio lodi lo giudice lombardi lombardo
longhi longo lonardo lo presti lorenzetti lorenzi lorusso losurdo lotti
lovato lo verde lucarelli lucchese lucchesi lucchetti luciani lucidi
luconi luongo lupi lupo lusso luzi
macchi macci macri maddalena madonia maestri maffei maffeis maganza maggi
maggiore magliocca magnani magnanini magno magri magrini maiello maiorano
maiorino malandrino malaspina malerba malfatti malinconico malocco malvezzi
mameli mancinelli mancini mancuso manenti manfredi manfredini manganelli
mangano mangia mangiapane mangione manias manna mannino manno manzi manzini
manzo mara marabini maragoni maranzano marasco marcantonio marcelli marchese
marchesi marchesini marchetti marchi marchini marconi marcucci marengo
marfella margiotta mari mariani marinaro marinelli marini marino mariotti
maritato marmo marone marotta marra marrazzo marrone marsala marsili martelli
martello martina martinelli martinez martini martino martorana marucci
maruzzella marzano marzocchi mascaro mascia masi masiello masini masone
massa massaro massimo mastrangelo mastroianni mastrogiacomo mastrolia
mattei mattera matteucci mattia mattioli mauri maurizi mauro mazza mazzanti
mazzarella mazzei mazzeo mazzetti mazzi mazzini mazzocchi mazzola mazzoli
mazzone mazzoni mazzotta mecca medici megna melchionna mele meli melillo
meloni melis menchini meneghini menegon menichetti mennella mensi menta
mercadante mercuri merenda merli merlini merlo messina meta miano miceli
micheli michelini micucci miele migliaccio migliore mignano milani milazzo
milena milone mina minelli miniaci minisci minniti minutoli miozzo miraglia
mirabella mirabelli miserendino misuraca mocci modugno moggi moio mola
molinari molteni mombelli monaco monardo mondini monetti mongelli monica
montagna montanari montanaro montefusco montella monti montorsi morabito
morando morandi morelli moretti morgante morgese mori moriconi morini
moro morra morrone mosca moscato moschella mosconi mottola mucci muccino
mulas munari mura murgia muroni murru musacchio muscarella musso mustacchio
mustica mutti muzio
nacci nadalin nannini nanni napoletano napoli napolitano nardelli nardi
nardini nardo natale natalizio navarra navarro nava nebuloni negri negro
nenci neri nervi nesi nesta nicastro niccolai nicolai nicoletti nicolosi
nicotra nigro ninni nisi nizzola nobile nobili nocera noce nocerino nofri
nolli nonis norcia notaro notarnicola novelli novello nucci nuccio nunziante
nuti nuzzo
occhipinti occhiuto oddo odorisio offredi ogliari olivares oliva oliveri
olivetti olivieri ombrosi onesti onofri onorato oppedisano orazi orefice
orlandi orlandini orlando ornaghi orsi orsini ortolani ortu osti ottaviani
ottaviano ottolini
pacchiarotti pace paci pacifici padovani padovano paganelli pagani pagano
paglia pagliaro pagliarulo paglione pagnotta paladini paladino palazzo
palazzolo palermo palladino pallante pallotta palma palmieri palmisano
palombi palombo palumbo panariello pancini pandolfi panebianco panetta
panichi paniz pantaleo pantano panzarella panzeri paoletti paoli paolini
paolucci papa papaleo papi papini pappalardo paradiso parente parenti
pariani parisi parmeggiani parodi parolini parri partipilo paruta pasca
pascale pasetti pasini pasqualini pasquini passalacqua passaro passeri
pastore pastorelli pastori patanè patalano patrizi pattarini pauletto
paulon pavan pavanello pavesi pavone pazienza pecoraro pedrazzi pedretti
pedrini pedrotti pelagatti pelizzari pellegrini pellegrino pellicano
pellizzari peluso pennacchio pennisi pepe peraldo perego perilli perillo
perini perna pernice perone perotti perri perrone perrotta persiani persico
peruzzi pescatore pesce pesenti pessina petrella petrelli petri petrillo
petrini petrone petronio petrucci petrucciani pezzali pezzella pezzotta
piacentini piana piano piazza piazzi piccinini piccirillo picciuto picco
piccolo piccoli picone pieri pierini pieroni pietrangeli pignata pignatelli
pignataro pilato pilato pillitteri pilloni pinardi pinelli pini pinna pino
pinto pintus piovan pipitone pira pirani pirola pironti pirrone pisani
pisano piscitelli pistone pittaluga pitzalis piva pizzarelli pizzella
pizzimenti pizzo pizzolato pizzuto placido plati podda poggi poggiali
poli polidori polito pollastri pollini pollini polito polizzi polverino
pompei pompili poncini ponti ponzi ponzio porcari porcelli porcu porretta
porta portelli porzio possenti postiglione potenza poti pozzi pozzo prandi
prati prato pratesi previti prezioso prete previtali priori prisco procopio
proietti prosperi provenzano puccetti pucci puccinelli puddu puglia pugliese
pugliesi puglisi puleo pulice pumo puntillo pupillo purificato putignano
quaglia quaranta quarta quartucci quattrocchi quattrone querini quinto
quintavalle quirino
racca radice raffaele raffaelli ragazzi ragazzo raggi ragni ragusa raimondi
raimondo rainone ramella ramunno randazzo ranieri ranucci rao rapisarda
rapisardi rasi raso raspa rastelli rattazzi ravaioli ravelli ravera ravera
re rebecchi recalcati recchia recupero redaelli reggiani regis reina renna
reno restivo restuccia riboli ricca ricci ricciardi ricciardelli ricciarelli
ricco ridolfi riccio rigamonti riggio righetti righi rigoni riina rinaldi
rinaldo ripa ripamonti risi riso riva rivaroli rivera rizzardi rizzi
rizzo rizzuto robba robbiano roberti robustelli rocca roccatagliata rocchi
rocco roda rodella rodolfi rodriguez roggero rolando rolfi rolla rollo
romagnoli romani romanelli romani romano romeo romito roncaglia roncalli
ronchi ronchetti rondinelli rongoni rosa rosati rosato roscini roselli
rosi rosini rosolen rossetti rossi rossini rossetto rosso rotella rotondo
rovelli rovere roversi rubino ruberto ruffini ruffino ruggeri ruggero
ruggiero ruocco ruotolo rusconi russo rustico rutigliano ruzzier
sabatini sabatino sabbadin sabbatini sacchetti sacchi sacco sada saggese
sala salamone salani salemi salerno saletti salomone salvadori salvago
salvati salvatore salvatori salvi salvini salvo sammarco sammartino sanchez
sandri sandrini sanfilippo sangiorgi sangiovanni sanna sannino santamaria
santangelo santarelli santarsiero santi santini santise santo santoni
santoro santucci sanzone saraceno saracino sarno sarti sartori sartorio
sassi sassano satta savarese savi savini savio savoia savona sbarbaro
sbrolli scaccia scaglia scaglione scala scalera scalzo scandurra scaramuzza
scaramuzzino scarano scarcella scardino scarfone scarlata scarpa scarpelli
scarpinato scavo scelsi schiavi schiavo schiavone schiavoni schiraldi
sciacca sciarra scibilia scipioni sciullo scognamiglio scola scopa scordo
scorza scotti scozzari scudieri scuderi sebastiani secci sechi seghezzi
segre selvaggio semeraro semperboni sena senatore serafini serafino sereni
sergi serpe serra serrano servidio sessa sestili sferrazza sferra sforza
sgarbi sgarbossa sgroi siciliano siena signorelli signorile signorini
sillano silva silvestri silvestrini silvestro simeone simeoni simonelli
simoni simonini sinatra sini siniscalchi sirna sironi sisti sivieri
soave sodano soldani soldati solimeno sollazzo solari soliani sonzogni
sordi sorrentino sorrenti sortino sottile spadaro spadoni spagnoletti
spagnolo spagnuolo spallone spampinato spano sparacino sparano speranza
sperandio spezia spina spinelli spinello spinosa spiriti spitaleri spoto
squillace squillante staiano stagnaro stanzani starace stassi stefanelli
stefani stefanini stella stellato stefanizzi sterpone stigliano stocchi
stoppa storti straface strano strazzullo strina strozzi stucchi sturniolo
suriano surace susini svanera
taddei tagliaferri tagliaferro tagliavia taglietti taibi talamo talarico
tallarico tamburello tamburini tamburrino tanzi taormina tarantino taranto
tarquini tassinari tassone tatarella tavani tavella tedeschi tedesco
tempesta tempestini tenaglia tenerelli tenore tentori teodori teresi terlizzi
termini terracciano terranova terrasi terzi tesone testa testi testoni
tiberi tibaldi ticozzi tinelli tinti tirelli tiraboschi tiso tizzano
tocco todaro toffanin toffoli togni tolomeo tomaselli tomasi tomasello
tomassini tommasi tommasini tondelli tondi tonelli toni tonini tononi
torchia torelli torlonia tornatore torre torres torrisi torti toscani
toscano tosetti tosi tosto tota totaro tozzi traina tramontana tramonti
trapani trasatti traversa traverso trentin trentini trevisan trevisani
tricarico trimarchi trincia trinca troia troiani troiano trombetta troncone
trotta trovato trombini truffelli trupia tucci tulli tumino turchetti
turchi turco turrini tuzzi
ubaldi uberti uccello udine ugolini ulivi umbrella ungaro urbani urso
usai ussia uva
vaccarella vaccari vaccaro vacchi vagnoni valente valentini valenza valeri
valeriani valle vallone valli valota valsecchi vanacore vandelli vannini
vanoli vanzetti varano varesi varotto vasile vassallo vecchi vecchietti
vecchio vecchione vela velardi vella veneziano venezia venditti veneziano
venturelli venturi venturini venturino verardi verdi verga vergani vergara
vernacchia veronese veronesi verrini versace vertecchi vescovi vespa
vestrucci vetrano vetrone vezzoli viale viani vicari vicedomini vicini
vidali vietri vigano vigna vigni vignali vignola vigo villa villani villano
vinci vinciguerra viola violante violi virgilio visconti visentin visintin
vitale vitali vitiello viti vitolo vitrano vittori vittorio viviani vivona
vizzini vocca voghera volante volpato volpe volpi volta voltolina vona
vozza vullo
zaccaria zaccagnini zaccardi zacchia zaffanella zaghi zagnoni zambelli
zambon zamboni zampa zampieri zamperini zamuner zanchetta zanchi zanella
zanetti zangara zangrando zanini zaninelli zanoletti zanoni zanotti zappa
zappala zappia zarabara zardi zaramella zavatta zavattaro zecca zecchin
zedda zelante zeni zennaro zerbini zeri zerilli zetti ziliani zilio zingale
zingaretti zinno zippo zito zizza zoccola zoia zola zollo zonta zoppi
zorzi zucca zucchelli zucchetti zucchi zuccotti zumbo zunino zurlo
"""

SURNAMES: frozenset[str] = frozenset(_SURNAMES.split())


# ---------------------------------------------------------------------------
# Parole italiane che iniziano con la maiuscola e non sono nomi di persona
# ---------------------------------------------------------------------------

_COMMON_CAPITALIZED = """
gentile gentilissimo gentilissima egregio egregia spettabile spett caro cara
carissimo carissima buongiorno buonasera buonanotte salve ciao arrivederci
cordiali cordialmente distinti distinte saluti saluto ringraziando ringrazio
grazie prego scusi scusa attenzione avviso nota note oggetto riscontro
riferimento allegato allegati allegata allegate seguito premesso premessa
considerato visto vista viste visti quanto tanto tutto tutti tutte tutta
questo questa questi queste quello quella quelli quelle
gennaio febbraio marzo aprile maggio giugno luglio agosto settembre ottobre
novembre dicembre lunedi martedi mercoledi giovedi venerdi sabato domenica
signor signora signori signore signorina dottor dottore dottoressa ingegner
ingegnere avvocato avvocatessa geometra architetto professore professoressa
ragioniere presidente direttore direttrice responsabile amministratore
amministratrice titolare legale rappresentante segretario segreteria
societa spa srl snc sas scarl azienda ditta impresa studio ufficio
dipartimento divisione settore reparto servizio servizi direzione sede
filiale agenzia comune provincia regione stato ministero ministro assessore
sindaco prefettura questura tribunale procura corte cassazione consiglio
commissione autorita ente enti istituto istituzione universita facolta
scuola liceo ospedale asl inps inail agenzia entrate camera commercio
banca intesa unicredit poste italiane
italia italiana italiano italiani italiane roma milano napoli torino
palermo genova bologna firenze bari catania venezia verona messina padova
trieste brescia parma taranto prato modena reggio reggio calabria perugia
livorno ravenna cagliari foggia rimini salerno ferrara sassari latina
giugliano monza siracusa pescara bergamo forli trento vicenza terni bolzano
novara piacenza ancona andria arezzo udine cesena lecce pesaro barletta
alessandria caserta asti catanzaro cosenza crotone potenza matera campobasso
aosta trapani agrigento ragusa enna caltanissetta nuoro oristano
lazio lombardia piemonte veneto toscana sicilia sardegna puglia campania
liguria marche umbria abruzzo molise basilicata calabria emilia romagna
friuli venezia giulia trentino alto adige valle aosta
europa europea unione comunita nazionale internazionale mondiale
gdpr privacy garante regolamento decreto legge codice normativa direttiva
articolo comma allegato titolo capo sezione paragrafo
area gestione patrimonio contabilita bilancio urbanistica anagrafe
ragioneria vigilanza
pratica pratiche fascicolo protocollo procedura procedimento istanza
domanda richiesta comunicazione lettera raccomandata pec mail email posta
telefono cellulare fax indirizzo sede legale operativa
oggi domani ieri mattina pomeriggio sera notte ore giorno giorni settimana
mese mesi anno anni data scadenza termine termini
totale importo imponibile netto lordo iva saldo acconto fattura fatture
ricevuta pagamento bonifico contratto accordo convenzione preventivo offerta
ordine consegna fornitura fornitore cliente clienti
progetto progetti attivita lavoro lavori intervento manutenzione impianto
impianti rete sistema sistemi software hardware server dati dato
sopralluogo verifica verifiche controllo collaudo
grande grandi nuovo nuova nuovi nuove primo prima secondo seconda terzo
terza ultimo ultima buon buona bene male molto poco altro altra altri altre
stesso stessa alcuni alcune ogni qualche nessuno nessuna
sono siamo siete essere stato stata stati state avere abbiamo avete
inoltre pertanto tuttavia quindi dunque infatti perche mentre quando dove
come cosa chi cui anche ancora sempre mai gia poi prima dopo durante
mediante tramite presso salvo tranne oltre entro
srl spa gruppo holding consorzio cooperativa associazione fondazione
onlus federazione sindacato ordine albo collegio
comitato consiglio giunta assemblea seduta verbale delibera deliberazione
determina determinazione ordinanza circolare disposizione provvedimento
piano piani programma programmi progetto piattaforma portale sportello
industriale commerciale amministrativo amministrativa tecnico tecnica
tecnici tecniche generale generali speciale specifico operativo esecutivo
preliminare definitivo straordinario ordinario interno esterno pubblico
pubblica privato privata centrale locale territoriale regionale provinciale
comunale statale civile penale tributario fiscale contabile finanziario
economico economica organizzativo informatico informatica digitale
fase fasi lotto lotti uno due tre quattro cinque sei sette otto nove dieci
parte parti punto punti elenco tabella figura scheda modulo modello
allegata documento documenti relazione rapporto report riepilogo sintesi
premesse conclusioni osservazioni valutazione valutazioni analisi esito
esiti risultato risultati obiettivo obiettivi ambito perimetro
sicurezza qualita ambiente salute formazione personale risorse umane
acquisti gare gara appalto appalti bando capitolato disciplinare
manutenzione assistenza supporto help desk logistica magazzino
datacenter cloud rete reti infrastruttura infrastrutture applicazione
applicativo applicativi database backup ripristino continuita
versione release aggiornamento patch collaudo esercizio produzione
nord sud est ovest centro settentrionale meridionale
gennaio dicembre corrente scorso prossimo venturo
capo capitolo comma lettera numero numeri codice codici identificativo
matricola serie targa protocollo pratica registro repertorio
banca dati carta carte libro libri conto conti cassa tesoreria
corte torre monte ponte villa valle campo campi porta porte forte
grande grandi piccolo piccola maggiore minore minimo medio media
il lo la le un uno una lui lei loro noi voi essi esse
contatta contattare contattami scrivi scrivere scrivimi chiama chiamare
invia inviare inviato inviata inviati inviate ricevuto ricevuta ricevi
rispondi rispondere risposta trasmetti trasmesso trasmessa allega allegare
conferma confermare confermato confermata segnala segnalare segnalazione
richiedi richiedere verifica verificare controlla controllare
apri aprire chiudi chiudere leggi leggere vedi vedere trova trovare
puoi potete devi dovete vuoi volete fai fate usa usare
firmato firmata firmatario firmatari redatto redatta approvato approvata
autorizzato autorizzata presentato presentata emesso emessa emissione
sottoscritto sottoscritta compilato compilata predisposto predisposta
aggiornato aggiornata revisionato revisionata validato validata
concordato concordata definito definita stabilito stabilita
di da in con su per tra fra del dello della dei degli delle al allo alla
ai agli alle dal dallo dalla dai dagli dalle nel nello nella nei negli
nelle sul sullo sulla sui sugli sulle col coi
"""

COMMON_CAPITALIZED: frozenset[str] = frozenset(_COMMON_CAPITALIZED.split())
