# One-Piece-TCG-Probability-Calculator
Deck Probability Analyzer
un calculateur One Piece Card Game

## 1. Onglet actuel — Probabilité de pioche
Tu gardes ton système actuel :
Axe X → nombre de cartes vues
Axe Y → probabilité
1x / 2x / 3x / 4x copies
Deck de 50 cartes
possibilité de prendre en compte les cartes de vie
C'est ton calculateur de base.
2. Nouvel onglet — Probabilité par tour
C'est effectivement plus intéressant pour un joueur que simplement « 5 cartes vues ».
Je mettrais :
Tour	Cartes vues cumulées	1x	2x	3x	4x
Tour 1	6	...	...	...	...
Tour 2	7	...	...	...	...
Tour 3	8	...	...	...	...
Tour 4	9	...	...	...	...
Tour 5	10	...	...	...	...
Mais il y a un point important : il faut définir exactement ce qu'on considère comme "cartes vues" à chaque tour.
Par exemple, si tu commences avec 5 cartes :
T1 = 5 cartes de départ + 1 pioche = 6
T2 = 7
T3 = 8
T4 = 9
T5 = 10
Et si certaines cartes permettent de piocher davantage, on pourra ensuite intégrer ces effets.
Le graphique serait alors beaucoup plus parlant :
X = Tour 1 → Tour 5
Y = Probabilité d'avoir au moins une copie
Cela permettrait immédiatement de répondre à une question du genre :
« J'ai 4 exemplaires de cette carte. Quelle est ma chance de l'avoir avant le tour 3 ? »
3. Onglet — Recherche dans les X premières cartes
Celui-ci est très intéressant pour les cartes qui disent quelque chose comme :
Regardez les 5 cartes du dessus de votre deck et...
Là, je ne ferais pas simplement un autre graphique de pioche.
Je créerais un calculateur du type :
Nombre de cartes capables de rechercher :
1 | 2 | 3 | 4
Nombre de cartes regardées :
3 | 5
Nombre de copies de la carte recherchée :
1 | 2 | 3 | 4
Puis :
Probabilité de trouver la carte recherchée
Par exemple :
4 copies dans le deck + 5 cartes regardées
→ calcul de la probabilité d'avoir au moins une des 4 copies parmi ces 5 cartes.
Et surtout, on pourrait ajouter le nombre de tentatives de recherche.
Exemple conceptuel :
Deck : 50
Carte recherchée : 4 copies
Cartes de recherche : 4 copies
Chaque chercheur regarde 5 cartes
Le programme pourrait alors répondre :
Chercheurs joués	Probabilité de trouver
1	XX %
2	XX %
3	XX %
4	XX %
Ça devient vraiment un outil d'analyse de deck plutôt qu'un simple calculateur de pioche.
4. Onglet — Piocher puis défausser
Celui-ci est également une très bonne idée, mais il faut le modéliser un peu différemment.
Tu pourrais avoir deux modes :
Mode A — Draw 1 → Discard 1
Exemple :
Piochez 1 carte, puis défaussez 1 carte.
Le programme devrait calculer l'impact sur la probabilité d'obtenir une carte.
Mode B — Draw 2 → Discard 2
Exemple :
Piochez 2 cartes, puis défaussez 2 cartes.
L'intérêt est de mesurer le filtrage du deck.
Et je pense qu'il serait intéressant d'afficher deux informations :
Probabilité d'avoir trouvé la carte
et
Nombre moyen de cartes vues
Parce que « draw 2, discard 2 » n'est pas réellement équivalent à une simple pioche de 2 : tu as vu deux cartes supplémentaires, mais tu dois ensuite en éliminer deux.
Mais je ferais une amélioration importante
Plutôt que de créer des onglets complètement indépendants, je construirais ton application autour d'un moteur commun.
Tu as déjà :
def proba_au_moins_une(N, K, n):
C'est très bien.
On pourrait ensuite ajouter des fonctions spécialisées :
Calculateur
│
├── Pioche simple
│
├── Probabilité par tour
│
├── Recherche Top 3 / Top 5
│
└── Pioche + défausse
Tout utiliserait le même moteur mathématique.
Et à terme, ton application pourrait devenir :
One Piece TCG Probability Calculator
Onglet 1 — Pioche
Quelle est ma chance de voir ma carte ?
Onglet 2 — Par tour
Quelle est ma chance d'avoir ma carte au T1/T2/T3/T4/T5 ?
Onglet 3 — Recherche
Quelle est ma chance de trouver ma carte avec mes searchers ?
Onglet 4 — Filtrage
Quelle est l'efficacité de Draw 1 → Discard 1 ou Draw 2 → Discard 2 ?
Onglet 5 — Analyse de deck (évolution future)
Quelle est la probabilité d'avoir une combinaison de cartes ?
Et ce dernier serait particulièrement intéressant pour One Piece, parce qu'on pourrait ensuite analyser des situations comme :
« Quelle est ma probabilité d'avoir un personnage + un Event + un DON!! avant le tour 3 ? »
Là, ton projet passerait vraiment d'un calculateur de pioche à un Deck Probability Analyzer.
Mon avis sur la priorité
Je développerais dans cet ordre :
① Probabilité par tour → très prioritaire
② Recherche Top 3 / Top 5 → très prioritaire
③ Draw/Discard → prioritaire
④ Combinaisons de cartes → évolution avancée
Et surtout, pour l'onglet par tour, je te conseille de ne pas mettre uniquement T1 à T5 en lignes : faire T1 à T10 avec possibilité de choisir le nombre de tours serait encore plus utile. On pourrait ensuite ajouter un bouton « Inclure les cartes de vie » comme dans ton onglet actuel.
Si tu veux, je peux ensuite modifier directement ton fichier Python actuel pour intégrer ces 3 nouveaux onglets en conservant ton interface et ton système actuel.
