# SKILL.state — Vendored Reference

Status: VENDORED EXTERNAL REFERENCE
Normative Scope: the authors' paper; not a TOAS specification

## Source And Attribution

- **Title:** SKILL.state: Scalable Long-Horizon Agent Skills
- **Authors:** Sanket Badhe, Priyanka Tiwari, Jonghyun Chung
- **Affiliations:** Google LLC and Purdue University, as presented upstream.
  The HTML groups the latter two authors and their affiliations; the local
  copy preserves that grouping rather than inferring individual assignments.
- **Pinned version:** arXiv:2608.26263v3, September 2, 2026
- **First submitted:** August 26, 2026
- **Retrieved:** September 26, 2026
- **Upstream:** [versioned abstract](https://arxiv.org/abs/2608.26263v3),
  [HTML](https://arxiv.org/html/2608.26263v3),
  [PDF](https://arxiv.org/pdf/2608.26263v3)
- **License:** [Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/),
  identified on the arXiv HTML. Copyright remains with the authors. This
  attribution and license apply to the converted paper and original figure;
  inclusion does not relicense them under the repository's own license.

## Local Contents

- [paper.md](paper.md): full paper, including references and appendices A–D.
- [Architecture figure](assets/skillstate-architecture.svg): original SVG from
  [the versioned HTML asset](https://arxiv.org/html/2608.26263v3/skillstate_tizk_fig.svg).
- [TOAS design note](../../notes/2026-09-26-state-transition-buffers.md): separate
  interpretation and open questions about state-transition-shaped buffers.

## Conversion Changes

Converted the article element from arXiv's HTML using Beautiful Soup and
`markdownify` 1.2.3, with explicit handling for the paper's LaTeXML structures:

- Removed site navigation and page chrome; retained all article sections.
- Converted MathML from its embedded source TeX, using inline dollar delimiters
  and numbered display equations.
- Converted all 11 data tables into Markdown tables. Spanning header cells use
  empty continuation cells; header groups retain their original order.
- Converted all 15 algorithm/prompt/example listings into fenced text, retaining
  source lines. Algorithm layout whitespace was normalized; mathematical
  notation in those blocks uses plain TeX for editor readability.
- Retained the original SVG locally and kept its caption.
- Preserved citation/reference targets with explicit HTML anchors and resolved
  external links against the versioned source URL.
- Normalized heading/list formatting, displayed author affiliations on separate
  lines, and added the local attribution banner and documentation links.

The scientific prose and reported values have not been rewritten. Source
wording and numbering quirks, including the appendix's `.1` and `.2` section
labels, remain. This is a reading copy of the HTML edition rather than a
facsimile of the PDF. Consult the pinned upstream PDF for publication layout.

Downloaded HTML SHA-256:

```text
1ec22f107b69b416518acdf3eb4ca3310ef3314123293fdd275554f8a6618d27
```

## Verification And Update Discipline

The intake compared 1,057 source text units (headings, paragraphs, bibliography
blocks, table cells, captions, and listing lines) against the Markdown after
normalizing formatting and math markup. All were retained. It also checked
11 data tables, 15 listings, seven display equations, and internal citation
targets. These checks establish conversion coverage, not independent validation
of the paper's experimental claims.

Future source updates should explicitly change the pinned version and repeat
the attribution and conversion review. Keep critique, proposed TOAS semantics,
and corrections to scientific claims in linked notes rather than editing them
into the vendored paper.
