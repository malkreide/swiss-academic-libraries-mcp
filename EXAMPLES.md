# Use Cases & Examples — swiss-academic-libraries-mcp

Real-world queries by audience.

### 🏫 Bildung & Schule
Lehrpersonen, Schulbehörden, Fachreferent:innen

**Material für den Geschichtsunterricht suchen**
«Gibt es historische Druckwerke oder Quellenmaterial über die Gründung des Bundesstaates Schweiz 1848, die ich im Unterricht zeigen kann?»
→ `swisscovery_search(query="title = 'Bundesstaat' AND subject = '1848'")`
→ `erara_list_records(from_date="1848-01-01", until_date="1849-12-31", set_spec="zut")`
Warum nützlich: Lehrpersonen erhalten sofortigen Zugang zu digitalisierten Primärquellen, die sie direkt im Unterricht auf dem Smartboard einsetzen können, um Geschichte greifbar zu machen. (Kein API-Key nötig)

**Zeitschriftenartikel zur Pädagogik finden**
«Welche neueren pädagogischen Fachartikel gibt es zum Thema Volksschule und Mehrsprachigkeit in der Schweiz?»
→ `swisscovery_search(query="title = 'Volksschule' AND subject = 'Mehrsprachigkeit'")`
→ `eperiodica_list_records(from_date="2020-01-01")`
Warum nützlich: Fachreferent:innen und Lehrpersonen können sich schnell und umfassend über aktuelle pädagogische Diskurse und Forschungsresultate aus Schweizer Fachzeitschriften informieren. (Kein API-Key nötig)

### 👨👩👧 Eltern & Schulgemeinde
Elternräte, interessierte Erziehungsberechtigte

**Bücher über Erziehungsfragen recherchieren**
«Ich suche Ratgeber und Literatur zum Thema Medienkompetenz bei Kindern. Was gibt es in den Schweizer Bibliotheken dazu?»
→ `swisscovery_search(query="subject = 'Medienkompetenz' AND subject = 'Kinder'")`
Warum nützlich: Eltern finden fundierte und verlässliche Literatur zu aktuellen Erziehungsthemen, die sie über das Bibliothekssystem ausleihen können, ohne auf unregulierte Onlinesuchen angewiesen zu sein. (Kein API-Key nötig)

**Historische Kinderbücher entdecken**
«Gibt es alte, digitalisierte Schweizer Kinderbücher oder Lesefibeln aus dem 19. Jahrhundert, die ich mit meinen Kindern online durchblättern kann?»
→ `swisscovery_search(query="title = 'Lesebuch' AND subject = 'Kinderbuch'")`
→ `erara_list_records(from_date="1800-01-01", until_date="1899-12-31")`
Warum nützlich: Familien können gemeinsam das historische Kulturerbe der Schweiz spielerisch entdecken und sehen, wie Kinder früher gelernt und gelesen haben. (Kein API-Key nötig)

### 🗳️ Bevölkerung & öffentliches Interesse
Allgemeine Öffentlichkeit, politisch und gesellschaftlich Interessierte

**Recherche zur lokalen Geschichte**
«Ich recherchiere für die Dorfchronik. Welche historischen Handschriften, Briefe oder Dokumente gibt es zu meiner Wohngemeinde im 18. Jahrhundert?»
→ `emanuscripta_list_records(from_date="1700-01-01", until_date="1799-12-31")`
→ `swisscovery_search(query="subject = 'Dorfchronik'")`
Warum nützlich: Heimatkundler und an der Lokalgeschichte interessierte Bürger erhalten direkten Zugriff auf historische Originaldokumente in Schweizer Archiven, ohne vor Ort sein zu müssen. (Kein API-Key nötig)

**Zugang zu wissenschaftlichen Artikeln für alle**
«Ich interessiere mich für die Architekturgeschichte von Schweizer Bahnhöfen. Welche Fachartikel gibt es dazu?»
→ `swisscovery_search(query="title = 'Bahnhof' AND subject = 'Architektur'")`
→ `eperiodica_list_records()`
Warum nützlich: Die breite Öffentlichkeit erhält niederschwelligen Zugang zu wissenschaftlichen Publikationen und digitalisierten Architekturzeitschriften, was die Teilhabe an Forschung und Kultur fördert. (Kein API-Key nötig)

### 🤖 KI-Interessierte & Entwickler:innen
MCP-Enthusiast:innen, Forscher:innen, Prompt Engineers, öffentliche Verwaltung

**Automatisierte Erschliessung historischer Texte (Multi-Server)**
«Finde digitalisierte Handschriften aus dem 19. Jahrhundert in e-manuscripta. Nutze dann den `swiss-culture-mcp` (https://github.com/malkreide/swiss-culture-mcp), um weitere kulturelle Objekte aus derselben Epoche zu suchen.»
→ `emanuscripta_list_records(from_date="1800-01-01", until_date="1899-12-31")`
Warum nützlich: Forscher im Bereich der Digital Humanities können durch die Kombination von Bibliotheksdaten und Kulturerbedaten Epochen umfassend analysieren und Modelle für historische Texte trainieren. (Kein API-Key nötig)

**Datenextraktion und Analyse von Zeitschriftenartikeln**
«Lade die Metadaten der neuesten 50 Artikel aus e-periodica herunter und analysiere sie nach häufigen Themen und Sprachen.»
→ `eperiodica_list_records(from_date="2024-01-01", response_format="json")`
Warum nützlich: Entwickler können bibliothekarische Metadaten im JSON-Format programmatisch weiterverarbeiten, um Trends in Publikationen zu erkennen oder eigene Suchindexe aufzubauen. (Kein API-Key nötig)

### 🔧 Technische Referenz: Tool-Auswahl nach Anwendungsfall

| Ich möchte… | Tool(s) | Auth nötig? |
|-------------|---------|-------------|
| den Schweizer Bibliothekskatalog durchsuchen | `swisscovery_search` | Nein |
| die Details zu einem bestimmten Buch abrufen | `swisscovery_get_record` | Nein |
| historische, digitalisierte Druckwerke finden | `erara_list_records`, `erara_list_collections` | Nein |
| ein einzelnes Digitalisat aus e-rara abrufen | `erara_get_record` | Nein |
| nach Artikeln in Schweizer Zeitschriften suchen | `eperiodica_list_records` | Nein |
| die Details eines e-periodica Artikels lesen | `eperiodica_get_record` | Nein |
| historische Handschriften und Briefe recherchieren | `emanuscripta_list_records`, `emanuscripta_list_collections` | Nein |
| einzelne Archivdokumente aus e-manuscripta abrufen | `emanuscripta_get_record` | Nein |
