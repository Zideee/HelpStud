# Statistiques descriptives

Les statistiques descriptives résument un ensemble de données par quelques nombres. Les
indicateurs de position décrivent le centre de la distribution : la moyenne est la somme
des valeurs divisée par leur nombre, la médiane est la valeur qui partage les données en
deux moitiés, et le mode est la valeur la plus fréquente.

La moyenne est sensible aux valeurs extrêmes : un seul salaire très élevé suffit à la
faire monter, alors que la médiane bouge peu. C'est pourquoi on préfère souvent la
médiane pour décrire des revenus ou des prix immobiliers.

Les indicateurs de dispersion mesurent à quel point les valeurs s'écartent du centre.
La variance est la moyenne des carrés des écarts à la moyenne, et l'écart-type est sa
racine carrée, exprimée dans la même unité que les données. L'écart interquartile, entre
le premier et le troisième quartile, est moins sensible aux valeurs extrêmes.

# Probabilités

Une probabilité est un nombre entre 0 et 1 qui mesure la chance qu'un événement se
produise. La probabilité de l'événement contraire vaut un moins la probabilité de
l'événement. Pour deux événements incompatibles, la probabilité que l'un ou l'autre se
produise est la somme de leurs probabilités.

La probabilité conditionnelle est la probabilité d'un événement sachant qu'un autre
s'est produit. Deux événements sont indépendants si savoir que l'un s'est produit ne
change pas la probabilité de l'autre. La formule de Bayes permet d'inverser un
conditionnement : à partir de la probabilité d'un symptôme sachant une maladie, elle
donne la probabilité de la maladie sachant le symptôme.

# Lois de probabilité

Une variable aléatoire associe un nombre au résultat d'une expérience. Sa loi décrit les
valeurs possibles et leurs probabilités. La loi de Bernoulli modélise une expérience à
deux issues, succès ou échec. La loi binomiale compte le nombre de succès sur plusieurs
répétitions indépendantes de cette expérience.

La loi normale, en forme de cloche, est définie par sa moyenne et son écart-type. Environ
95 % des valeurs se trouvent à moins de deux écarts-types de la moyenne. Elle apparaît
partout grâce au théorème central limite : la moyenne d'un grand nombre de variables
indépendantes suit approximativement une loi normale, quelle que soit leur loi d'origine.

## Tests d'hypothèse

Un test d'hypothèse permet de décider, à partir d'un échantillon, si une affirmation sur
la population est plausible. On formule une hypothèse nulle, par exemple « la moyenne
vaut 12 », et une hypothèse alternative. On calcule ensuite une statistique de test et
sa p-valeur.

La p-valeur est la probabilité d'observer un résultat au moins aussi extrême si
l'hypothèse nulle est vraie. Si elle est inférieure au seuil choisi, souvent 5 %, on
rejette l'hypothèse nulle. Une p-valeur élevée ne prouve pas que l'hypothèse nulle est
vraie : elle indique seulement que les données ne permettent pas de la rejeter.
