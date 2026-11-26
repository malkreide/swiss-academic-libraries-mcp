# Messprobe: «Require branches to be up to date»

**Diese Datei ist eine Messprobe und gehört nicht auf `main`.** Der PR, der sie
bringt, wird geschlossen, nicht gemergt.

Der Branch setzt absichtlich auf `78eaf02` auf. Ihm fehlt gegenüber `main` der
Inhalts-Commit `d6da326` (#138), der nur `CLAUDE.md` und
`docs/branch-protection.md` ändert. Diese Datei ist neu, ein Konflikt ist damit
ausgeschlossen.

Gemessen wird im Browser, am Merge-Knopf des PR, nachdem die CI grün ist und
der PR nicht mehr als Draft steht:

- **Knopf gesperrt, bis «Update branch» geklickt wurde:** Die Option greift.
- **Knopf direkt drückbar:** Die Option greift nicht.

Hintergrund und bisherige Messungen: `docs/branch-protection.md`,
Abschnitt «Messprotokoll».
