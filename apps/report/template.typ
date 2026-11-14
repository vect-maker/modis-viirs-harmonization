// Report template for the FIRMS Harmonizer ETL hackathon report

#let project-report(
  title: "Project Report",
  subtitle: none,
  authors: (),
  date: datetime.today().display("[month repr:long] [day], [year]"),
  body,
) = {
  set document(title: title, author: authors)
  set text(size: 11pt, lang: "en")
  set par(justify: true)
  set heading(numbering: "1.1")

  // Title page
  set page(paper: "a4", margin: 2.2cm, numbering: none)
  align(center + horizon)[
    #text(24pt, weight: "bold")[#title]
    #if subtitle != none [
      #v(0.6em)
      #text(13pt, fill: luma(90))[#subtitle]
    ]
    #v(1.5em)
    #if authors.len() > 0 [
      #authors.join(", ")
      #v(0.5em)
    ]
    #date
  ]
  pagebreak()

  // Table of contents
  outline(title: [Contents], indent: auto, depth: 2)
  pagebreak()

  // Main content
  set page(
    numbering: "1",
    header: context {
      let p = counter(page).get().first()
      if p > 1 [
        #text(9pt, fill: luma(110))[#title #h(1fr) Page #p]
      ]
    },
  )
  counter(page).update(1)

  body
}
