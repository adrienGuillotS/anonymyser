import time
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine

start = time.time()

configuration = {
    "nlp_engine_name": "spacy",
    "models": [
        {
            "lang_code": "fr",
            "model_name": "fr_core_news_lg",
        }
    ],
}

provider = NlpEngineProvider(nlp_configuration=configuration)
nlp_engine = provider.create_engine()

analyzer = AnalyzerEngine(
    nlp_engine=nlp_engine,
    supported_languages=["fr"]
)

text = """
Décision du 25 Février 2021 18° chambre 2ème section N° RG 18/02353
assistées de Henriette D, Greffier
DÉBATS
A l’audience du 12 Novembre 2020 tenue en audience publique devant Laurence P, juge rapporteur, qui, sans opposition des avocats, a tenu seule l’audience, et, après avoir entendu les conseils des parties, en a rendu compte au Tribunal, conformément aux dispositions de l’article 805 du Code de Procédure Civile.
Après clôture des débats, avis a été donné aux avocats que le jugement serait rendu par mise à disposition au greffe le 25 Février 2021.
JUGEMENT
Rendu publiquement par mise à disposition au greffe Contradictoire
En premier ressort
FAITS ET PROCEDURE
_________________
Par acte sous seing privé non daté, Mme D. (sic), aux droits de laquelle est venue Mme B (ci-après Mme B), a donné à bail en renouvellement à Mme V. G. (ci-après Mme G) divers locaux dépendant de l'immeuble sis ADRESSE à Paris, ainsi désignés : « Une boutique située à gauche sur rue, avec escalier intérieur menant à un entresol, une grande pièce sur rue, cuisine et W.C., avec cave n°7 », pour 9 ans à compter du 1er juillet 2007 pour se terminer à pareille date de l'année 2016, moyennant un loyer annuel de 6868,85 euros, hors taxes et hors charges, payable à terme échu, par quart aux quatre trimestres d'usage et pour la première fois le 1er octobre 2007, puis les 1er janvier, 1er avril et 1er juillet de chaque année.
Les locaux sont destinés à l'exercice de « l'activité de ACHAT, VENTE, EXPERTISE, REPARATION, ANTIQUITES, MOBILIER, TABLEAUX, OBJETS D'ART ET TOUS OBJETS SE RAPPORTANT A LA DECORATION ».
Par acte extrajudiciaire du 29 décembre 2015, Mme G. a signifié à Mme B. et au gestionnaire de celle-ci, la SOCIETE F. (ci après la société F.), une demande en renouvellement du bail à effet du 1er juillet 2016, en application de l'article L.145-10 du code de commerce.
Par acte extrajudiciaire du 25 mars 2016, Mme B. a refusé le renouvellement du bail sollicité en offrant une indemnité d'éviction, en application de l'article L.145-14 du code de commerce.
Par acte du 21 février 2018, Mme G. a fait assigner Mme B. et la société F. devant le tribunal de grande instance de Paris afin de voir dire que celles-ci lui sont redevables d'une indemnité d'éviction, de les voir condamner solidairement à lui payer une indemnité d'éviction et, avant dire droit, de voir désigner un expert judiciaire en vue de procéder à l'estimation des indemnités d'éviction et d'occupation découlant du refus de renouvellement.
Par ordonnance du 7 septembre 2018, le juge de la mise en état a désigné M. Xavier B. en qualité d'expert, qui a déposé son rapport le 25 octobre 2019, concluant à une indemnité d'éviction de 404 000 euros pour perte du fonds de commerce et à une indemnité d'occupation au 1er juillet 2016 de 18 270 euros par an, en ce compris un abattement de précarité de 10%.
"""

results = analyzer.analyze(
    text=text,
    language="fr"
)

print("Entités trouvées :")
print(results)

anonymizer = AnonymizerEngine()

anonymized = anonymizer.anonymize(
    text=text,
    analyzer_results=results
)
end = time.time()
print("\nTexte anonymisé :")
print(anonymized.text)
print(f"temps{end-start}")