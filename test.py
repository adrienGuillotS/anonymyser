
import aspose.pdf as ap

# Charger le document PDF

document = ap.Document("t.pdf")

# Instancier un objet TextFragmentAbsorber
txtAbsorber = ap.text.TextFragmentAbsorber("Marcel")

# Texte de recherche
document.pages.accept(txtAbsorber)

# Obtenir une référence aux fragments de texte trouvés
textFragmentCollection = txtAbsorber.text_fragments

# Analyser tous les fragments de texte recherchés et remplacer le texte
for txtFragment in textFragmentCollection:
    txtFragment.text = "replaced-text"

# Enregistrer le PDF mis à jour
document.save("output.pdf")
