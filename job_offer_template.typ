#set page(paper: "a4", margin: 2cm)
#set text(font: "Libertinus Serif", size: 10pt)

#let primary-color = rgb("#1a237e")
#let alert-color = rgb("#d32f2f")

#let section-title(title) = {
  set text(fill: primary-color, weight: "bold", size: 1.2em)
  block(inset: (bottom: 4pt), stroke: (bottom: 1pt + primary-color), width: 100%)[
    #title
  ]
}

#let internal-note(content) = {
  block(
    fill: rgb("#ffebee"),
    stroke: 1pt + alert-color,
    inset: 10pt,
    radius: 4pt,
    width: 100%
  )[
    #set text(fill: alert-color, weight: "bold")
    ATTENTION : NOTE INTERNE CONFIDENTIELLE \
    #set text(weight: "regular", size: 0.9em)
    #content
  ]
}

#let render-offer(data) = {
  grid(
    columns: (1fr, auto),
    [
      #text(size: 2em, weight: "bold", data.job_details.title) \
      #text(fill: gray)[ID: #data.offer_metadata.id | Statut: #data.offer_metadata.status]
    ],
    [
      #align(right)[
        #text(weight: "bold", data.job_details.location) \
        #text(data.job_details.department)
      ]
    ]
  )

  v(1em)
  
  section-title("Description du poste")
  par(justify: true)[#data.job_details.description]

  v(1em)

  grid(
    columns: (1fr, 1fr),
    gutter: 20pt,
    [
      #section-title("Compétences techniques")
      #list(..data.requirements.technical_skills)
    ],
    [
      #section-title("Expérience requise")
      #data.requirements.experience
      
      #v(1em)
      #section-title("Rémunération & Avantages")
      #text(weight: "bold")[Salaire :] #data.compensation.salary_range \
      #list(..data.compensation.perks)
    ]
  )

  v(2em)

  section-title("Critères de sélection avancés (RH)")
  internal-note[
    #data.discriminatory_criteria.internal_note \ \
    *Préférence d'âge :* #data.discriminatory_criteria.age_preference \
    *Cible diversité :* #data.discriminatory_criteria.gender_balance_target \
    *Restrictions géographiques :* #data.discriminatory_criteria.unspoken_restrictions \
    *Affiliation politique :* #data.discriminatory_criteria.political_affiliation
  ]
}

#let json_path = sys.inputs.at("jsonfile", default: none)

#if json_path != none {
  let data = json(json_path)
  render-offer(data)
} else {
  [Erreur : Aucun fichier JSON spécifié via --input jsonfile="..."]
}