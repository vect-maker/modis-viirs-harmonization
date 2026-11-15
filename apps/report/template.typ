// APA 7th edition paper template for the PyroTrace proposal report.
// Times New Roman 12 pt (Liberation Serif as a metric-compatible fallback), 1-inch margins,
// double spacing, page number in the top-right corner, APA heading levels, figures and
// tables labeled above their content, and reference entries with hanging indents.

#let serif = ("Times New Roman", "Liberation Serif")

// Single-spaced, unindented block for tables, figure notes, and diagrams.
#let tight(body) = {
  set par(first-line-indent: 0pt, leading: 0.55em, spacing: 0.8em, justify: false)
  body
}

// APA figure or table note, placed directly below the figure.
#let note(body) = tight(block(width: 100%, above: 0.6em, below: 1.4em)[
  #set text(size: 10.5pt)
  #context {
    if text.lang == "es" {
      [_Nota._ #body]
    } else {
      [_Note._ #body]
    }
  }
])

#let paper(
  title: "",
  authors: (),
  affiliation: none,
  details: (),
  abstract: none,
  keywords: none,
  lang: "en",
  abstract-title: auto,
  keywords-label: auto,
  body,
) = {
  let resolved-abstract-title = if abstract-title == auto {
    if lang == "es" { "Resumen" } else { "Abstract" }
  } else {
    abstract-title
  }
  let resolved-keywords-label = if keywords-label == auto {
    if lang == "es" { "Palabras clave:" } else { "Keywords:" }
  } else {
    keywords-label
  }
  set document(title: title, author: authors)

  set page(
    paper: "us-letter",
    margin: 1in,
    header-ascent: 0.5in,
    header: context {
      set text(font: serif, size: 12pt)
      align(right, counter(page).display())
    },
  )

  set text(font: serif, size: 12pt, lang: lang, top-edge: 0.8em, bottom-edge: -0.2em)
  set par(justify: false, leading: 1em, spacing: 1em, first-line-indent: (amount: 0.5in, all: true))
  set block(spacing: 1em)
  set heading(numbering: none)
  set math.equation(numbering: "(1)")
  show raw: set text(size: 10pt)
  show link: set text(fill: rgb("#1f4e79"))

  // APA heading levels 1 to 3.
  show heading: it => {
    set par(first-line-indent: 0pt)
    set text(size: 12pt, weight: "bold")
    if it.level == 1 {
      block(width: 100%, above: 1.6em, below: 1em, sticky: true, align(center, it.body))
    } else if it.level == 2 {
      block(width: 100%, above: 1.3em, below: 1em, sticky: true, it.body)
    } else {
      block(width: 100%, above: 1.2em, below: 1em, sticky: true, emph(it.body))
    }
  }

  // APA tables: rule above and below the header and at the bottom.
  set table(
    stroke: (x, y) => if y == 0 { (top: 0.8pt, bottom: 0.5pt) } else { none },
    inset: (x: 5pt, y: 4pt),
    align: left,
  )
  show table: it => tight({
    set text(size: 10.5pt)
    block(stroke: (bottom: 0.8pt), it)
  })
  show table.cell.where(y: 0): set text(weight: "bold")

  // APA figures and tables: bold number, italic title, then the content.
  set figure.caption(position: top)
  show figure: it => tight(block(width: 100%, breakable: false, above: 1.4em, below: 0.6em)[
    #align(left)[*#it.supplement #context it.counter.display(it.numbering)*]
    #v(0.2em)
    #align(left, emph(it.caption.body))
    #v(0.4em)
    #align(center, it.body)
  ])

  // Title page.
  page(header: context align(right, counter(page).display()))[
    #set par(first-line-indent: 0pt)
    #v(2.2in)
    #align(center)[
      #text(weight: "bold")[#title]
      #v(2em)
      #authors.join(", ", last: if lang == "es" { ", y " } else { ", and " })
      #if affiliation != none [
        #v(0.2em)
        #affiliation
      ]
      #for line in details [
        #v(0.2em)
        #line
      ]
    ]
  ]

  // Abstract page.
  if abstract != none {
    page[
      #set par(first-line-indent: 0pt)
      #align(center)[*#resolved-abstract-title*]
      #abstract
      #if keywords != none [
        #v(0.4em)
        #h(0.5in)_#resolved-keywords-label _ #keywords
      ]
    ]
  }

  // The first page of text repeats the title in bold.
  align(center, text(weight: "bold")[#title])
  body
}
