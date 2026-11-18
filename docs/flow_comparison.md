# Comparer DBR, kanban et CONWIP

## Lancer l'expérience

Ces commandes s'exécutent depuis la racine du dépôt après `pip install -e '.[dev]'`.

```bash
# Exporter le régime stable et le choc de mix avec les réglages du YAML
indeng compare-flow config/scenarios/flow_comparison.yaml --scenario both --variants --out out/replay

# Vérifier rapidement les huit combinaisons et leurs exports
indeng compare-flow config/scenarios/flow_comparison.yaml --campaign --core-only \
  --runs 2 --calibration-runs 1 --out out/quick

# Mesurer les huit combinaisons, les essais complémentaires et les variantes
indeng compare-flow config/scenarios/flow_comparison.yaml --campaign --workers 4 --out out/campaign
```

Tester un seul scénario avec `--scenario mix`, `--scenario mix_bleu` ou
`--scenario mix1_demande1_charge1`. `--seed` fixe la première graine.
La campagne réexporte les deux replays pédagogiques avec les réglages issus
de la calibration. Elle utilise la première graine d'évaluation, 1701 par
défaut. Écrire chaque campagne dans un dossier distinct permet de conserver
ses fichiers d'exécution et son protocole.

## Atelier et demande

Les temps sont en minutes. Chaque commande demande une pièce. Les quatre
postes A → B → C → D ont chacun une machine, avec des gammes communes aux
politiques. La demande nominale est de 5,4 pièces par heure. Au mix équilibré,
les charges nominales de B et C valent 90 % et 72 %.

À chaque arrivée le client reçoit une date promise. Le délai client est
nul dans le YAML de référence, ce qui mesure le service immédiat. Une pièce
disponible sert la plus ancienne commande ouverte de sa référence. Le besoin
de réapprovisionnement est calculé avec la cible, le backlog, le stock fini
et la production déjà engagée ou planifiée. Le besoin reçoit sa propre date
cible, par défaut 75 minutes après sa création. L'atelier démarre vide et
constitue ses stocks pendant l'échauffement.

| Facteur | Stable | Après le choc |
| --- | --- | --- |
| Mix | 20 rouges, 20 bleues, 20 vertes par fenêtre | 27 rouges, 12 bleues, 21 vertes avec B à 99 % de charge nominale |
| Demande | 60 arrivées régulièrement espacées par fenêtre | Quatre rafales de 15 arrivées au quart de l'intervalle habituel, aux mêmes volumes par fenêtre |
| Charge par OF | Durées nominales | Durées prévues à ±40 %, équilibrées par paire de rangs pour chaque référence et poste |

Une fenêtre contient 60 intervalles de demande nominale, soit 666,67 minutes.
Le choc suit quatre fenêtres d'échauffement. L'observation en dure huit.
Les arrivées se poursuivent pendant le suivi des échéances client et
réapprovisionnement. Les séquences de références sont permutées par graine
et par fenêtre. Les durées potentielles sont indexées par graine, référence,
poste, régime et rang. Les trois politiques reçoivent donc les mêmes
commandes et les mêmes suites de durées par poste, même si les files ou le
nombre d'opérations exécutées diffèrent. Pour le kanban, une durée prévue
est affectée à chaque OF local. Dans l'essai d'erreur de durée, la durée
réelle varie à compter du choc et le tirage est révélé au début de
l'opération. La moyenne nominale est conservée sur les paires complètes.

Les essais complémentaires comprennent le mix à dominante bleue qui déplace
la charge dominante de B vers C, le choc de mix à gammes identiques avec son
témoin stable, un renouvellement avec préavis, une erreur d'estimation des
durées, puis deux hausses de la demande. Une hausse de 5 % charge B à
94,5 %. Une hausse de 20 % le charge à 108 % et crée une surcharge
structurelle. Pour le renouvellement, la nouvelle référence reprend la
gamme de la verte. À la date de retrait, l'atelier termine de servir les
commandes vertes ouvertes. Le stock résiduel passe ensuite en quarantaine
et reste compté dans le stock total.

## Règles de pilotage

| Politique | Entrée du travail | Autorisations et exécution |
| --- | --- | --- |
| DBR | Au moment calculé par le calendrier à capacité finie du tambour | Créneau souhaité placé au plus tard avant la cible moins le tampon aval. Si la cible est infaisable, premier créneau libre après le temps amont prévu. Le lancement est borné par l'instant présent. |
| Kanban dédié | OF local dès qu'une carte de la référence et la pièce amont sont disponibles | La carte reste avec la pièce produite jusqu'au prélèvement. En fin de ligne, une demande client peut ouvrir un besoin même sans pièce disponible. La carte totale de chaque boucle et de chaque référence dépend du réglage du YAML. |
| CONWIP | Dès qu'un besoin net et une autorisation globale sont disponibles | Le plafond s'applique du lancement à l'entrée en stock fini, où l'OF rend son autorisation. |

Les travaux admissibles sont départagés par ancienneté du besoin puis par
identifiant. Pour le DBR, le poste tambour traite les OF prêts par ordre
de créneau. À l'amont, les OF dont le créneau est menacé passent devant
les autres. Le critère est le temps restant avant le créneau, moins la durée
amont prévue restante, inférieur ou égal au tiers du tampon amont.
Un tambour disponible peut prendre tôt un OF prêt si le premier créneau
attendu n'est pas prêt. Les opérations sont non préemptives. Les créneaux
et cibles restent les références de suivi et les écarts sont journalisés.

`dbr_fifo` conserve les dates de lancement et écarte l'urgence du créneau
pour séquencer les OF admissibles. `dbr_adaptive` choisit le tambour des
nouveaux OF à partir des commandes observées sur une fenêtre glissante.
Il estime la charge avec leurs gammes nominales, teste l'écart toutes les
166,67 minutes et change de poste à partir de 8 points de charge. Chaque
réservation déjà prise garde son poste et sa date.

`kanban_shared` partage les cartes d'une boucle entre les références. Les
cibles par référence restent des guides de reconstitution. La boucle
intermédiaire garde de la place pour les références actives sans pièce,
et une demande aval peut emprunter les cartes restantes. Avec trois cartes
pour trois références, cette garantie limite le partage. Lors d'un
renouvellement, le préavis et le traitement des commandes de l'ancienne
référence déterminent le moment où la nouvelle référence entre dans
cette garantie.

`conwip_weighted` consomme des minutes prévues au poste B au lieu de compter
les OF. Les plafonds de référence sont équivalents en minutes à la charge
nominale moyenne du même nombre d'OF. Si l'OF le plus ancien ne tient pas
dans le crédit restant, il attend une libération.

## Campagne et lecture des résultats

1. **Calibration stable.** Tester la grille YAML sur huit graines
   indépendantes de l'évaluation. Retenir la plus faible moyenne de stock
   total qui atteint 95 % de service. Si la cible est hors d'atteinte,
   retenir le meilleur service de la grille, puis le stock minimal à
   service égal. Les sorties signalent ce cas.
2. **Réglages gelés.** Rejouer chaque scénario sur 30 graines communes.
   Les trois politiques gardent les réglages calibrés en régime stable.
3. **Révision.** Sur des trajectoires pilotes séparées par scénario,
   choisir les paramètres de révision avec le même objectif de service.
   En évaluation, appliquer le changement à la fin de la deuxième fenêtre
   après le choc. La simulation conserve les pièces en cours et les
   commandes ouvertes. Les besoins excédentaires encore hors de l'atelier
   peuvent être annulés lors de la révision. Ce protocole mesure une
   adaptation informée par un pilote indépendant pour ce même régime.
   Les données de la répétition évaluée ne servent pas au choix du réglage.

| Sortie | Lecture |
| --- | --- |
| `calibration.csv` | Points testés, choix du réglage, cible atteinte et frontière service–stock |
| `service_stock.csv` | Meilleur service testé sous un budget de stock commun et plus petit stock testé à service comparable, sans interpolation |
| `runs/` et `runs.csv` | Un CSV par exécution d'évaluation et leur consolidation |
| `summary.csv` | Moyennes par scénario, phase et politique, plus proportion de replays ayant récupéré |
| `paired_differences.csv` | Écarts entre politiques, effet du choc par rapport au stable, effet de la révision et effet des variantes |
| `protocol.json` | Graines, paramètres gelés et horloge commune |
| `replay/{stable,mix}/` | Journaux détaillés, commandes, réapprovisionnements et chiffres pour le carton final |

Les intervalles à 95 % rééchantillonnent les différences appariées par
graine, avec 3 000 tirages bootstrap. La différence entre révision et
réglages gelés utilise les mêmes fenêtres post-révision. Les variantes
héritent des réglages gelés de leur politique de base. Pour juger le
kanban partagé, lire conjointement l'écart de service et l'écart de stock.

Le stock total moyenne dans le temps l'encours physique, le stock
intermédiaire, le stock fini et le stock obsolète. Un OF planifié hors
atelier ne représente pas encore une pièce. Le service évalue la cohorte
des commandes arrivées dans la fenêtre. Le retard p95 inclut la borne
basse des retards encore ouverts à la date de clôture du suivi. Le débit
mesure les livraisons effectuées dans la fenêtre, quelle que soit leur
date de commande.

L'aire du backlog cumule les pièces-minutes en attente. La dérive compare
les pics des première et dernière fenêtres de la période. La récupération
est le début de la première séquence de deux fenêtres consécutives où le
pic de backlog revient sous le maximum d'avant choc, hors première
fenêtre d'échauffement. Une durée de récupération vide indique qu'aucune
séquence n'a été observée. Les minutes de famine, de manque de carte,
d'attente de lancement et de manque de demande proviennent des états
successifs des postes. La charge en file devant B et C est exprimée en
heures de travail. Elle utilise les temps prévus pour DBR et CONWIP, et
la gamme nominale des pièces admissibles en kanban.

## Rejouer une trajectoire

Lire `events.csv` dans son ordre d'écriture à chaque temps `sim_time`.
Les lignes `state` donnent les pièces aux postes, les files, les stocks,
le backlog et la raison d'inactivité. Les événements `card_take`,
`card_return`, `conwip_return`, `slot_reserved` et `priority_change` précisent les
décisions. Le JSON `details` contient les identifiants et la capacité
concernés. En kanban, l'identifiant de pièce accompagne le prélèvement puis
le travail au poste suivant. Pour DBR et CONWIP, `piece_id` relie la pièce à
l'OF et à sa livraison. `orders.csv` conserve les trois dates côté client.
`replenishments.csv` conserve la cible, le créneau, le retour planifié et le
retour réel. Synchroniser les trois panneaux avec l'événement `shock` et
utiliser `end_card.csv` pour afficher séparément les chiffres de la
trajectoire et les moyennes des répétitions.
