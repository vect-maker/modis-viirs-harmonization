// Two-column academic/technical paper template for FIRMS Harmonizer ETL
// Targets Typst 0.15+

#let paper(
  title: "Paper Title",
  authors: (),
  affiliations: (:),
  date: datetime.today().display("[month repr:long] [year]"),
  abstract: none,
  keywords: none,
  body,
) = {
  set document(
    title: title,
    author: authors.map(a => if type(a) == dictionary { a.name } else { a }),
  )

  set page(
    paper: "us-letter",
    margin: (x: 0.72in, y: 0.85in),
    columns: 2,
    numbering: "1",
    footer: context {
      align(center, text(size: 9pt)[#counter(page).display()])
    },
  )

  set columns(gutter: 18pt)
  set text(font: ("New Computer Modern", "Liberation Serif"), size: 9.5pt, lang: "en")
  set par(justify: true, leading: 0.58em, spacing: 0.65em)
  set heading(numbering: "1.1")
  set math.equation(numbering: "(1)")

  show heading: set text(weight: "bold")
  show heading.where(level: 1): it => block(above: 1.2em, below: 0.6em, text(size: 12pt)[#it])
  show heading.where(level: 2): it => block(above: 1.0em, below: 0.5em, text(size: 10.5pt)[#it])
  show heading.where(level: 3): it => block(above: 0.8em, below: 0.4em, text(size: 9.5pt)[#it])

  show table.cell.where(y: 0): set text(weight: "bold")
  set table(
    stroke: (x, y) => if y == 0 {
      (top: 0.8pt + black, bottom: 0.5pt + black)
    } else if y == 1 {
      (top: 0.5pt + black)
    } else {
      none
    },
    inset: (x: 5pt, y: 4pt),
  )

  // Full-width title block spanning both columns
  place(
    top + center,
    scope: "parent",
    float: true,
    block(width: 92%, below: 1.4em)[
      #align(center)[
        #text(size: 16pt, weight: "bold")[#title]
        #v(0.8em)
        #if authors.len() > 0 [
          #text(size: 10pt)[
            #authors.map(a => {
              if type(a) == dictionary {
                [#a.name#super[#a.affil]]
              } else {
                a
              }
            }).join(h(1.4em))
          ]
          #v(0.4em)
        ]
        #if affiliations.len() > 0 [
          #text(size: 8.5pt)[
            #affiliations.pairs().map(((k, v)) => [#super[#k]#v]).join(h(1.2em))
          ]
          #v(0.4em)
        ]
        #text(size: 9.5pt)[#date]
      ]
    ],
  )

  // Abstract & Keywords (placed at top of first column, matching example layout)
  if abstract != none [
    #heading(outlined: false, numbering: none)[Abstract]
    #abstract
    #if keywords != none [
      #v(0.4em)
      *Keywords:* #keywords
    ]
    #v(0.6em)
  ]

  body
}

#let todo(msg) = text(fill: rgb("#b45309"), style: "italic")[#("[TODO: " + msg + "]")]
