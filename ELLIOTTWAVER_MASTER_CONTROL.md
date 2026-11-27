ELLIOTTWAVER — MASTER CONTROL
Version: 1.0
Erstellt: 2026-11-20
Status: Steuerungsgrundlage; Phase A zur Freigabe vorbereitet, noch nicht ausgeführt
Gültigkeit: Verbindlicher Arbeitsauftrag für GitHub Copilot im ElliottWaver-Repository.
Hinweis: Historische Implementierungs- und Testergebnisse sind Berichte, keine aktuelle Repository-Verifikation.
0. Schnellstart für Copilot
Rolle: Senior Implementation Engineer. Lies diese Datei vollständig, prüfe die bestehenden Repository-Regeln (insbesondere .github/copilot-instructions.md) und befolge die strengere Sicherheitsregel bei Konflikten. Arbeite nur am ausdrücklich freigegebenen Paket.

Aktuell freigegeben: KEINES.
Nächstes Paket: PHASE-A — Read-only Repository- und Git-Baseline.
Startbedingung: Der Product Owner gibt PHASE-A ausdrücklich frei (z. B. „GO PHASE A“). Das Vorliegen dieser Datei ist keine Ausführungsfreigabe.

Nach jedem Paket: Prüfergebnisse in engineering/HANDOVER.md dokumentieren, Änderungen und offene Risiken offenlegen, dann STOPP. Keine Folgepakete oder Commits ohne gesonderte Freigabe.

Sofortige Stopps: Unklarer Repositoryzustand, drohender Verlust von Benutzeränderungen, Konflikt mit geschützten Dateien, grundlegender Architekturkonflikt, nicht reproduzierbare Qualitätsnachweise.
1. Projektauftrag und Produktziel
ElliottWaver ist eine Python-basierte Desktop-Anwendung für die strukturierte Elliott-Wave-Analyse von Marktdaten mit Forecast-Szenarien, Confidence-Bewertung und Fibonacci-Projektionen. Der nächste Produktmeilenstein ist eine kontrolliert freigabefähige Beta, nicht eine umfassende Neuentwicklung der Domain-Engines.
1.1 Rollen und Entscheidungskompetenzen
Rolle	Verantwortung	Entscheidungsspielraum
Product Owner (Benutzer)	Produktziele, Prioritäten, Freigaben, Praxistests, Releaseentscheidung	Genehmigt Pakete, grundlegende Richtungsänderungen und Commits
Chief Software Architect (ChatGPT)	Zielarchitektur, konkrete Lösungswege, Reihenfolge, Architekturreview, Abnahmeempfehlung	Gibt technische Leitplanken und Nachbesserungsaufträge vor; kann nur anhand vorgelegter Nachweise prüfen
Senior Implementation Engineer (Copilot)	Code, Tests, Refactoring, technische Dokumentation, reproduzierbare Nachweise	Darf lokale Details entscheiden; keine eigenmächtige Architektur- oder Scope-Änderung


Wichtig: Copilot darf keinen Bericht als „durch ChatGPT geprüft“ markieren, solange der Bericht nicht tatsächlich dem Chief Software Architect zur Prüfung vorgelegt wurde. Ebenso ist ein automatisch bestandener Test keine Product-Owner-Freigabe.
1.2 Entwicklungsprinzipien
- Domain-Driven Design, Clean Architecture, SOLID, klare Dependency Rule.
- Deterministische, möglichst unveränderliche Domain-Modelle.
- UI ausschließlich über die Application-Fassade (AnalysisApplication), keine direkte Engine-Orchestrierung aus tkinter.
- Technische Adapter in Infrastructure; Zusammensetzung im Bootstrap/Composition Root.
- ForecastEngine und ProjectionEngine nicht ohne nachgewiesenen Engine-Defekt ändern.
- Vorhandene Implementierungen wiederverwenden; keine zweite parallele Swing-, CSV- oder Validierungslogik schaffen.
- Keine erfundenen Dateipfade, Typen, Testzahlen oder Erfolgsmeldungen.
- Vor Eingriffen vorhandene Tests, öffentliche Verträge und Git-Änderungen berücksichtigen.
2. Zuletzt dokumentierter Projektstand — noch zu verifizieren
2.1 Berichteter Implementierungsstand
- Forecast-Domain und Forecast Engine V1 einschließlich Hardening: als umgesetzt berichtet.
- Fibonacci Projection Domain und Projection Engine einschließlich Hardening: als umgesetzt berichtet.
- Forecast-/Projection-Integration: als umgesetzt berichtet.
- MS-015 Desktop-MVP: AnalysisApplication, CSV-Provider, Runtime-Ports, Factory/Composition Root, tkinter/ttk-Desktop, Presenter, Modulstart und Dokumentation: als umgesetzt berichtet.
- Windows-Start wurde vom Product Owner mit python.exe -m pip install -e . und python.exe -m elliottwaver erfolgreich ausprobiert.
- Letzter gemeldeter Gesamtstand: 307 Tests bestanden, 91,43 % Coverage, Ruff PASS, MyPy PASS. Diese Zahlen sind historisch und dürfen nicht als Ergebnis eines aktuellen Laufs ausgegeben werden.
- Das zuletzt bekannte Defektregister enthält 16 offene Defekte (2 Blocker, 4 High, 6 Medium, 4 Low); Status durch Phase A aktualisieren.
2.2 Offene Kernrisiken
1. Produktiver Desktop-Pfad könnte noch den Noop-Swing-Port verwenden (DEF-002).
2. Desktop-Analyse könnte den Tk-Hauptthread blockieren (DEF-003).
3. Windows-CI und Wheel-Installations-Gate sind laut letzter Bestandsaufnahme nicht vollständig (DEF-011/012).
4. Zahlreiche bestehende, nicht committete Dateien im Workspace; der aktuelle Git-Stand ist nicht als sauber anzunehmen.
2.3 Unveränderlich geschützte Benutzerdateien
Nie ändern, löschen, zurücksetzen, stagen oder committen:
tests/unit/application/test_context_service.py
tests/unit/domain/context/test_elliott_context.py
Diese Schutzregel gilt auch für automatische Formatierung, Refactorings, git add ., git restore, git reset, git clean und sonstige Massenoperationen. Bei notwendigen Tests neue, ungeschützte Testdateien anlegen.
3. Zielarchitektur
Desktop View (tkinter/ttk)
   | Benutzerereignis / Darstellung
   v
Desktop Controller / Background Runner
   | Aufruf über stabile Application-Schnittstelle
   v
AnalysisApplication (Application Facade)
   | Ports und Orchestrierung
   +--> CsvMarketDataProvider (Infrastructure: CSV/UTC/Validierung)
   +--> produktiver Swing-Preparation-Adapter (vorhandene Swing-Logik wiederverwenden)
   +--> Forecast Engine (Domain/Application nach bestehendem Vertrag)
   +--> Projection Engine (Domain/Application nach bestehendem Vertrag)
   |
   v
Analysis Result / Presenter / immutable View Model
   |
   v
Desktop View (nur Tk-Mainthread)
Die Darstellung ist ein logisches Zielbild. Vor der Implementierung die tatsächlich existierenden Typen und Ports prüfen; keine zusätzliche Klasse allein wegen des Diagramms erzeugen. Der tatsächliche Aufruf- und Rückgabevertrag der AnalysisApplication bleibt maßgeblich.
4. Verbindlicher Arbeitsprozess
4.1 Paket-Lebenszyklus
1. Freigabe: Product Owner gibt genau ein Paket frei.
2. Repository-Abgleich: Copilot nennt vorhandene Typen, vollständige relative Pfade, Abweichungen und relevante Tests.
3. Umsetzung: Copilot implementiert die unten vorgegebene Lösung. Lokale Detailentscheidungen sind zulässig, Architekturänderungen nicht.
4. Technische Prüfung: Pakettests, Integrationstests, Ruff, MyPy; passende manuelle/GUI-Tests. Kommandos und vollständige Ergebnisse festhalten.
5. Architektur- und Funktionsprüfung: Ergebnis mit Architekturregeln und jedem Abnahmekriterium abgleichen; dem Chief Software Architect zur Prüfung vorlegen.
6. Praxistest: Product Owner führt bei sichtbarem Verhalten einen kurzen, dokumentierten Test aus.
7. Freigabeentscheidung: Nur bei bestätigter Erfüllung „VERIFIZIERT“. Andernfalls „NACHBESSERUNG“; dasselbe Paket bleibt aktiv.
8. Commit: Nur nach gesonderter Freigabe, mit exakter Dateiliste; niemals pauschales Staging.
9. STOPP: Nächstes Paket erst nach ausdrücklicher Freigabe.
4.2 Statusmodell
BESTÄTIGT → IN ARBEIT → IMPLEMENTIERT → TECHNISCH GEPRÜFT → ARCHITEKTUR GEPRÜFT → PRAXIS GEPRÜFT (falls nötig) → VERIFIZIERT

Bei Fehler: NACHBESSERUNG mit konkretem Befund und erneutem Test. BLOCKIERT ist zulässig, wenn ein nicht lokal lösbarer Konflikt vorliegt. Niemals Tests oder Reviews als bestanden ausgeben, die nicht durchgeführt wurden.
4.3 Paket-Quality-Gates
- Pro Paket: betroffene Unit- und Integrationstests, Ruff Check, Ruff Format Check, MyPy für relevante Projektbereiche (soweit Konfiguration es vorsieht), Funktionsnachweis der Paketabnahme.
- Am Milestone-Ende: vollständige Repository-Gates, Coverage, Build, Wheel-Installation, CI-Plattformmatrix und Release-Smoke.
- Bestehende Gates nicht lockern, Tests nicht pauschal überspringen, keine blanket noqa/`type: ignore`.
- Bei GUI-Paketen: Mainthread-Sicherheit und Windows-Praxistest gesondert dokumentieren.
4.4 Freigaben und Schreibaufwand
- GO PHASE A: nur read-only Baseline.
- GO EP-DEF-01 usw.: nur das bezeichnete Paket.
- PRÜFEN: Chief Software Architect soll die aktuelle Übergabe bewerten; Übergabeinhalt bereitstellen.
- NACHBESSERN: festgestellte Abweichungen im aktuellen Paket korrigieren.
- OK: Product-Owner-Abnahme des ausdrücklich geprüften Pakets; keine automatische Freigabe weiterer Pakete.
- WEITER: nächsten Auftrag vorbereiten; Umsetzung erst nach ausdrücklicher Paketfreigabe.
- STOP: keine weiteren Änderungen.
5. PHASE-A — Read-only Repository- und Git-Baseline
Priorität: Sofort. Status: WARTET AUF PRODUCT-OWNER-FREIGABE.
Zweck: Tatsächlichen Stand bestimmen, bevor irgendein Defekt repariert wird.
Verbindlicher Auftrag
1. Prüfe Arbeitsverzeichnis und Repository-Root mit git rev-parse --show-toplevel, Branch und HEAD.
2. Erfasse git status --short und git diff --name-status; unterscheide staged, unstaged, untracked, ignored soweit relevant.
3. Verifiziere, dass die beiden geschützten Testdateien unverändert bleiben.
4. Ermittle die tatsächlichen relativen Pfade und Signaturen von AnalysisApplication, CSV-Provider, Swing-Port/Implementierung, Factory/Composition Root, Desktop, __main__.py, pyproject.toml, Quality-Workflow und betroffenen Tests.
5. Prüfe anhand von Code und Tests die 16 Defekte und markiere jeden als BESTÄTIGT, BEREITS BEHOBEN, NICHT NACHWEISBAR oder BLOCKIERT — mit Beleg.
6. Erfasse vorhandene Quality-Gate-Konfigurationen und die letzten nachweisbaren Testergebnisse. Führe keine Tests aus, die Dateien erzeugen oder den Workspace verändern, sofern der Product Owner nicht gesondert zustimmt. Read-only Sichtprüfung ist ausreichend.
7. Prüfe bestehende .github/copilot-instructions.md und vorhandene Architekturentscheidungen auf Konflikte mit dieser Datei; nichts ändern.
8. Gib eine geordnete, auf den tatsächlichen Stand angepasste Empfehlung für EP-DEF-01 ab.
Strenge Grenzen
Keine Dateien schreiben oder ändern. Kein git add, Commit, Reset, Restore, Clean, Checkout, Rebase oder Autoformat. Keine Dependencies installieren. Keine neuen Branches. Auch engineering/HANDOVER.md in Phase A nicht ohne ausdrückliche Schreibfreigabe anlegen: Bericht direkt im Copilot-Chat ausgeben, damit die Baseline tatsächlich read-only bleibt. Ein späterer Auftrag darf den Bericht in HANDOVER übernehmen.
Abnahme Phase A
- Vollständige und glaubwürdige Git-Baseline.
- Exakte, überprüfte Repo-Pfade und Vertragsgrenzen.
- Für alle 16 Defekte eine nachvollziehbare Ersteinstufung.
- Geschützte Dateien unangetastet.
- Keine Workspace-Mutation.
- Bericht liegt zur Architekturprüfung vor; anschließend STOPP.
6. Defektprogramm — verbindliche Lösungen
Wichtig: Die unten genannten Dateinamen sind aus früheren Berichten bekannt; Copilot muss vor jeder Änderung die tatsächlichen Repo-Pfade ermitteln. Neue Dateien nur dort anlegen, wo sie zur vorhandenen Paketstruktur passen. Keine blind übernommenen, erfundenen Pfade.
EP-DEF-01 — Produktiver Analysefluss
Defekte: DEF-002 (Blocker), DEF-004 (Medium). Abhängigkeit: relevante Interface-Verträge aus DEF-007 vorab lesen, aber DEF-007 nicht ungefragt vollständig bearbeiten.
DEF-002 — Produktiven Swing-Preparation-Adapter anbinden
Problem: Der produktive Desktop-Pfad verwendet laut Bestandsaufnahme einen Noop-Swing-Port; der Analysefluss endet bei geeigneten CSV-Daten ohne echte Swing-Daten.

Festgelegte Lösung: Bestehenden Swing-Preparation-Port beibehalten; einen produktiven Adapter an die bereits vorhandene Swing-Erkennung anbinden; im Composition Root statt des Noop-Adapters injizieren. ForecastEngine und ProjectionEngine bleiben unverändert. Noop allenfalls als explizites Test Double behalten.

Implementierung:
1. Port, Swing-Domain-Logik und Factory anhand des Codes lokalisieren.
2. Den Adapter so implementieren, dass Marktdaten in die vertraglich erwarteten Swing-Objekte überführt werden; keine Swing-Logik duplizieren.
3. Factory/Bootstrap auf den produktiven Adapter umstellen; keine konkreten Infrastructure-Abhängigkeiten in der Tk-View.
4. Echte Fixture-Daten mit verwertbaren Swings sowie Grenzfälle ergänzen.
5. Testen, dass geeignete CSV-Daten Forecast und Projection erreichen und unzureichende Daten kontrolliert behandelt werden.
Erlaubt: Namen privater Helfer, Adapterstandort innerhalb Infrastructure, Test-Fakes, lokales Factory-Wiring.
Verboten: Domain-Engines umgehen/neu schreiben, Swing-Algorithmus in der UI, zweite parallele Erkennung.
Abnahme: Produktives Wiring ohne Noop; Integrationstest belegt vollständigen Analysepfad; kein Ergebnis wird bei unzureichenden Daten erfunden.
DEF-004 — CSV- und Timestamp-Parsing zentralisieren
Problem: CSV-/Zeitstempelverarbeitung in Desktop und CSV-Provider doppelt.

Festgelegte Lösung: CSV-Lesen, Spaltenprüfung, Zahlenkonvertierung, Zeitstempel- und UTC-Normalisierung liegen ausschließlich beim Infrastructure-Provider bzw. seinem privaten Parser. UI wählt Datei und präsentiert Ergebnisse/Fehler.

Implementierung:
1. Doppelte Parserpfade ermitteln und eine zentrale Implementierung herstellen.
2. Bestehende CSV-Schemata und Fehlerverträge erhalten.
3. Fehlerfälle testen: fehlende/unlesbare/leere Datei, fehlende Spalten, ungültige Zahlen, ungültige/naive Zeitstempel nach geltender Projektregel, keine verwertbaren Daten.
4. Technische Fehler an einer klaren Grenze in stabile Application-/Presenter-Fehler übersetzen.
Abnahme: Ein produktiver Parser; UI interpretiert keine CSV-Zeilen; UTC-Regeln und Fehlerfälle sind getestet.

Paket-Praxistest: Reale geeignete CSV wählen → Analyse ausführen → Swings, Forecast, Confidence und Fibonacci-Projektionen plausibel sichtbar; ungültige CSV → verständliche Fehlermeldung. Keine Finanzprognose-Güte behaupten, nur technische Funktion nachweisen.
EP-DEF-02 — Desktop-Responsiveness und UI-Verantwortlichkeiten
Defekte: DEF-003 (High), DEF-005 (Medium). Voraussetzung: EP-DEF-01 verifiziert.
DEF-003 — Hintergrundanalyse ohne Tk-Blockade
Festgelegte Lösung: Ein Hintergrund-Worker führt den AnalysisApplication-Aufruf aus; Thread-sichere Queue/Ergebnisübergabe; alle Tk-Widgetupdates ausschließlich über den Mainthread und after(...). Während eines Laufs kein zweiter Start. Bei Fenster-Schließung keine nachträglichen Widgetzugriffe. Kein unnötiger Thread-Pool.

Implementierung: Kleinen AnalysisRunner/Controller einführen; Zustände bereit/läuft/erfolgreich/kein Ergebnis/Fehler abbilden; Worker-Exceptions kontrolliert übertragen; Closing-Flag und Polling-Abbruch; Tests mit blockierendem Fake, Fehlerpfad, Doppelstart und Fenster-Schließung.

Abnahme: UI bleibt während längerer Analyse bedienbar; kein Tk-Zugriff aus Worker; sichere Fehler- und Shutdown-Behandlung.
DEF-005 — View, Controller und Presenter trennen
Festgelegte Lösung: View = Widgets und Events; Controller = Ablauf, Worker, Status; Presenter = Transformation von Application-Ergebnissen in kleine View Models/Text. Keine neue generische UI-Framework-Schicht.

Implementierung: Bereits vorhandenen Presenter wiederverwenden/ergänzen; Parsing aus View entfernen; Orchestrierung in Controller; schmale typisierte Schnittstellen und Verhaltenstests.

Abnahme: Presenter kennt kein tkinter; View kennt keine CSV-Feldlogik; Controller kennt keine konkreten Forecast-/Projection-Engines.

Paket-Praxistest: Große CSV starten, Fenster bewegen, laufenden Zustand sehen, Mehrfachstart verhindern, Ergebnis/Fehler anzeigen, Fenster sicher schließen.
EP-DEF-03 — Packaging und CI Release Gate
Defekte: DEF-008 (High), DEF-011 (High), DEF-012 (Blocker). Voraussetzung: EP-DEF-02 verifiziert.
DEF-008 — Kanonischen Programmeinstieg deklarieren
Festgelegte Lösung: Eine kanonische main()-Funktion; __main__.py und [project.scripts] delegieren dorthin. python -m elliottwaver bleibt funktionsfähig. Paketimport darf keine GUI starten. Der neue Script-Name elliottwaver ist die gewünschte Distribution-Schnittstelle, soweit die tatsächliche Packaging-Konfiguration sie unterstützt.

Implementierung: Entrypoint lokalisieren, Doppel-Bootstrap vermeiden, Script-Metadaten ergänzen, Import- und Entrypoint-Tests sowie Windows-Doku aktualisieren.

Abnahme: Beide Startarten delegieren identisch; Import ist nebenwirkungsfrei; kein headless CI-Blockieren.
DEF-011 — Windows- und Linux-CI
Festgelegte Lösung: Bestehende Quality-Workflow-Gates auf ubuntu-latest und windows-latest ausweiten; dieselbe unterstützte Python-Version; interpretergebundenes python -m pip; headless-taugliche Tk-Tests ohne Gate-Abschwächung.

Abnahme: Matrix prüft Tests, Ruff Check, Ruff Format Check, MyPy auf beiden Betriebssystemen; CI-Ergebnisse belegbar.
DEF-012 — Artefakt-Build und Wheel-Install-Smoke
Festgelegte Lösung: python -m build, Wheel und sdist erzeugen, Wheel in frischer isolierter Umgebung installieren, Paketimport, Entry-Point-Vertrag und python -m pip check testen. GUI nicht interaktiv in CI starten.

Abnahme: Veröffentlichbares Artefakt baut und installiert reproduzierbar; Smoke läuft gegen installiertes Wheel, nicht nur Source Tree.

Paket-Praxistest: Windows-Installation in frischer virtueller Umgebung, Modulstart, optional Konsolenstart, Desktop-Fenster öffnet sich.
EP-DEF-04 — Architekturgrenzen und Testqualität
Defekte: DEF-006 (Medium), DEF-007 (Medium), DEF-015 (Low).
DEF-006 — UI-Tests typisieren
Festgelegte Lösung: Untypisierte Lambda-Fakes durch typisierte Fake-Klassen/-Funktionen ersetzen; öffentlich beobachtbares Verhalten testen; Protected-Member-Zugriffe vermeiden; keine pauschalen Suppressions.

Abnahme: Betroffene Tests sind MyPy-/Ruff-konform und prüfen Controller-, Presenter- und UI-Verhalten.
DEF-007 — Interfaces-API kuratieren
Festgelegte Lösung: Breite Reexports in interfaces/analysis.py und interfaces/__init__.py auf tatsächlich benötigte öffentliche Verträge begrenzen. Interne Nutzer auf direkte, architekturkonforme Imports migrieren. Vor Änderung tatsächliche externe Nutzer prüfen; bestehende öffentliche Kompatibilität nicht unbemerkt brechen.

Abnahme: Schmale dokumentierte Exporte, Contract-Tests, keine Importzyklen und keine unbeabsichtigten Breaking Changes.
DEF-015 — selected_wave-Validierung entdoppeln
Festgelegte Lösung: Strukturelle Request-Invarianten im Request-Objekt; Service validiert nur laufzeitabhängige fachliche Zustände. Nur tatsächlich identische Doppelprüfung entfernen; beabsichtigte Defense-in-Depth beibehalten und dokumentieren. Geschützte Tests nicht anfassen.

Abnahme: Unverändertes beobachtbares Fehlverhalten, eindeutige Verantwortlichkeit, neue ungeschützte Tests falls nötig.
EP-DEF-05 — Governance und Dokumentation
Defekte: DEF-001 (High), DEF-013 (Low), DEF-014 (Medium).
DEF-001 — Steuerungsdokumente konsistent halten
Festgelegte Lösung: PROJECT_MANIFEST.md = stabiler Produkt-/Architekturrahmen; CURRENT_STATUS.md = verifizierter Ist-Stand; ROADMAP.md = künftige Arbeit; METRICS.md = datierte reproduzierbare Messwerte; DECISIONS.md = Entscheidungsindex. Existenz/Pfade vorher prüfen, fehlende Dateien nicht ohne Bedarf neu anlegen.

Abnahme: Keine widersprüchlichen Statusaussagen, keine erfundenen Testwerte, historische Ergebnisse ausdrücklich gekennzeichnet.
DEF-013 — Windows- und Unix-Setup dokumentieren
Festgelegte Lösung: README mit Windows PowerShell (py -m venv .venv, Aktivierung, python.exe -m pip install -e ., python.exe -m elliottwaver) sowie Linux/macOS (python3 -m venv .venv, Aktivierung, python -m pip install -e ., python -m elliottwaver); Troubleshooting und Script-Entrypoint ergänzen.

Abnahme: Befehle passen zum tatsächlich verifizierten Projektsetup; keine lokalen absoluten Benutzerpfade.
DEF-014 — Relevante Architekturentscheidungen als ADR
Festgelegte Lösung: Nur signifikante Entscheidungen formal nachführen: Application-Fassade/UI-Grenze, tkinter/ttk, produktiver Swing-Adapter, Packaging-Entrypoints, plattformübergreifendes Release-Gate. Bereits vorhandene ADRs prüfen und nicht duplizieren; DECISIONS.md verlinkt die tatsächlich vorhandenen ADRs.

Abnahme: ADRs enthalten Kontext, Entscheidung, Alternativen, Folgen, Status; nachträgliche Formalisierung transparent.
EP-DEF-06 — Build-, Dependency- und Formatter-Hygiene
Defekte: DEF-009 (Low), DEF-010 (Medium), DEF-016 (Low).
DEF-009 — Pip an Interpreter binden
Festgelegte Lösung: In Makefile, CI und relevanter Dokumentation python -m pip statt barem pip; auf Windows nach Bedarf python.exe -m pip.

Abnahme: Installationskommandos nutzen den aktiven Interpreter; Makefile bleibt funktionsfähig.
DEF-010 — Reproduzierbare Dependencies
Festgelegte Lösung: Vorhandenes Lock-Tool zuerst identifizieren. Wenn bereits uv, Poetry, PDM oder ein anderes verbindliches Tool existiert, dieses beibehalten. Sonst Constraints-/pip-tools-Ansatz mit dokumentierter Generierung; pyproject.toml bleibt Quelle direkter Abhängigkeiten. Plattformmarker und optionale Extras korrekt berücksichtigen.

Abnahme: Lokale Entwicklung und CI nutzen reproduzierbare Versionen; kein zweites konkurrierendes Lock-System; Aktualisierung dokumentiert.
DEF-016 — Ruff als alleinigen Formatter
Festgelegte Lösung: Ruff Check und Ruff Format bleiben maßgeblich. Black nur entfernen, wenn kein nachgewiesener notwendiger Workflow es benötigt. Makefile, Pre-Commit, CI und Dev-Dependencies angleichen.

Abnahme: Eine konsistente Formatter-Toolchain, keine unbegründete Doppelabhängigkeit.
7. Gesamtfahrplan bis Beta
Phase	Inhalt	Gate / Ausgang
A	Read-only Git-/Repository-Baseline	Tatsächlicher Zustand belegt; Product Owner entscheidet über Start von EP-DEF-01
B	EP-DEF-01: produktiver Analysefluss	Echte CSV → Swing → Forecast → Projection nachgewiesen
C	EP-DEF-02: responsive Desktop-UI	Worker, sichere UI-Updates, Praxistest
D	EP-DEF-03 und EP-DEF-04: Release- und Architekturhärtung	CI/Wheel/Contracts geprüft; jedes Paket einzeln freigegeben
E	EP-DEF-05 und EP-DEF-06: Governance und Tooling	Dokumente und Dependencies konsistent; jedes Paket einzeln freigegeben
F	Milestone-Gesamtgate und Beta-Abnahme	Vollständige Quality Gates + Windows-Praxistest + Releaseentscheidung


Nach Beta: Produktfunktionen wie Visualisierung, weitere Datenquellen und Analyseerweiterungen nur nach neuer Priorisierung des Product Owners. Keine ungefragte Scope-Erweiterung während der Defektbehebung.
8. HANDOVER-Protokoll nach jedem freigegebenen Implementierungspaket
Zielpfad: engineering/HANDOVER.md (bei erster Schreibfreigabe erstellen).
Phase A: Bericht ausschließlich im Chat, weil Phase A read-only ist.

Jede Übergabe enthält exakt:
# ElliottWaver — Engineering Handover

Paket: <ID>
Status: <IN ARBEIT | IMPLEMENTIERT | TECHNISCH GEPRÜFT | BLOCKIERT>
Datum:
Branch / HEAD:

## 1. Ausgangslage und tatsächlich geprüfte Repo-Pfade
...

## 2. Umsetzung je DEF-ID
- DEF-XXX: Ursache, Lösung, geänderte Dateien, relevante Detailentscheidungen

## 3. Änderungen
- Vollständige relative Repo-Pfade; keine bloßen Basenames
- Keine Änderungen an geschützten Dateien: <belegt / Abweichung>

## 4. Abnahmekriterien (einzeln)
- [ ] Kriterium ... | Nachweis ...

## 5. Prüfkommandos und Ergebnisse
- Kommando, Exitcode, Anzahl Tests, Coverage nur wenn tatsächlich gemessen
- Ruff / MyPy / Format / Integration / Build je nach Paket
- Fehlgeschlagene Prüfungen vollständig nennen

## 6. Praxistest-Anleitung für Product Owner
- 3–6 konkrete Schritte, erwartete Ergebnisse, benötigte Beispieldaten

## 7. Git-Zustand
- git status --short
- staged / unstaged / untracked
- Commit nur wenn ausdrücklich freigegeben, sonst: KEIN COMMIT

## 8. Risiken, Abweichungen und offene Fragen
...

## 9. Nächste empfohlene Aktion
- Architekturreview anfordern; danach STOPP
Keine selbst erteilte Freigabe. Nur die technische Implementierung ist Copilots Aufgabe. Architekturprüfung und Product-Owner-Abnahme bleiben getrennte Schritte.
9. Git-, Scope- und Sicherheitspolitik
- Bestehende uncommittete Änderungen gehören dem Benutzer. Niemals ohne Auftrag zurücksetzen, überschreiben oder mit eigenen Änderungen vermischen.
- Vor Schreibpaketen git status --short, Branch/HEAD, Diff-Übersicht; nur klar zugeordnete Dateien ändern.
- Keine pauschalen git add ., git add -A, git reset --hard, git clean, git restore ..
- Vor vorgeschlagenem Commit: git diff --check, exakte Stage-Liste, git diff --cached --name-only, geschützte Dateien ausgeschlossen.
- Kein Commit ohne explizite Product-Owner-Freigabe. Architekturreview ersetzt keine Git-Freigabe.
- Keine automatischen großflächigen Formatierungen unbeteiligter Dateien.
- Bestehende .github/copilot-instructions.md nicht automatisch überschreiben; Regelkonflikte im Bericht nennen.
- Jede neue Datei mit tatsächlichem Pfad und Zweck begründen.
10. Vollständiges Milestone-/Beta-Quality-Gate
Die tatsächlichen Projektkommandos anhand von pyproject.toml, Makefile und CI verifizieren. Soweit passend:
python -m pytest
python -m ruff check .
python -m ruff format --check .
python -m mypy src
python -m build
python -m pip check
Zusätzlich:
1. Coverage-Grenze gemäß Projektkonfiguration prüfen (historisch >90 % berichtet).
2. Wheel in frischer virtueller Umgebung installieren und Paketimport prüfen.
3. Konsolen-/Modulstart ohne hängenden GUI-Prozess in CI verifizieren.
4. Linux- und Windows-CI nachweislich erfolgreich.
5. Windows-Desktop manuell mit geeigneter CSV durchlaufen.
6. Keine ungelösten Blocker; offene Risiken ausdrücklich vom Product Owner akzeptieren lassen.
7. Dokumentations- und Defektstatus nachführen.
8. Beta-Release ausschließlich nach Product-Owner-Freigabe.
11. Aktive Steuerung / Freigabeprotokoll
Feld	Aktueller Wert
Aktives Paket	KEINES
Nächster Kandidat	PHASE-A
Ausführungsfreigabe	AUSSTEHEND
Letztes Architekturreview	Nicht für diese Master-Datei durchgeführt
Letzte Paketabnahme	Keine neue Abnahme dokumentiert
Letzter Git-/Quality-Gate-Nachweis	Phase A ausstehend


Copilot-Anweisung nach einer expliziten Freigabe
Lies die Master-Control-Datei vollständig. Führe nur das ausdrücklich freigegebene Paket aus. Halte die Architektur, geschützte Dateien, Git-Sicherheit und Abnahmekriterien ein. Liefere den vollständigen Handover-Bericht und stoppe danach. Falls die Anweisungen dem realen Code widersprechen, melde die konkrete Abweichung; erfinde keine Lösung oder Dateipfade.

12. Strategische Fortschreibung — EP-DEF-10 Abschluss und Leitplanken

Statusfortschreibung (operativ bestaetigt):
- EP-DEF-10 ist im vereinbarten geometrischen Funktionsumfang technisch und visuell abgenommen.
- Bestaetigter Qualitaetsstand:
   - 436 Tests bestanden.
   - Coverage 92.56%.
   - Ruff PASS.
   - MyPy PASS.
   - Produktive Desktop-E2E-Tests PASS.
   - Ressourceneffizienz PASS.
   - Strukturierte Fehlerklassifikation PASS.
   - CSV-Cache PASS.
   - EP-09-Regression PASS.
   - Visuelle PO-Abnahme PASS.
- Produktive temporale Signalbestaetigung bleibt offen.
- Git-Versionierung bleibt bis separater Freigabe gesperrt.

Governance-Entscheidung:
- `ELLIOTTWAVER_MASTER_CONTROL.md` im Repository-Root ist das fuehrende operative Steuerungsdokument.
- `.github/ELLIOTTWAVER_MASTER_CONTROL.md` bleibt unveraendert und wird nicht als operative Quelle verwendet.
- Das abgeschlossene Paket wird als EP-DEF-10 gefuehrt.
- Historische Engineering-Paketbezeichnungen, Branch-Namen und Referenzen werden nicht rueckwirkend umbenannt.
- Das urspruengliche `EP-010-MULTI-TIMEFRAME-CONFLUENCE-ENGINE` bleibt eigenstaendig bestehen.

13. EP-DEF-10 Ergebnisprofil (normativ)

Dokumentierter fachlicher Umfang:
- Geometrische Candlestick-Erkennung mit zehn Varianten.
- Typisierte temporale Domain-Semantik.
- Unabhaengige Chart-Schalter.
- Unabhaengige Darstellung gueltiger Teilergebnisse.
- Einmalige CSV-Verarbeitung pro Lauf.
- Einmalige Analyseausfuehrung pro Lauf.
- Strukturierte optionale Forecast-Orchestrierung.
- Keine Exception-Textvergleiche fuer fachliche Ablaufsteuerung.
- Keine kuenstlichen Forecasts, Confidence-Werte oder Fibonacci-Projektionen.
- Definierte CSV-Cache-Lebensdauer auf Provider-Instanzebene.

Freigabestatus EP-DEF-10:
- Technisch: abgenommen.
- Visuell: abgenommen.
- Git-Versionierung: ausstehend.

14. Verbindliche strategische Architekturprinzipien

Fuer die weitere Entwicklung gelten:
- Local First.
- Validation First.
- Deterministic First.
- Modular First.
- Resource Efficient.
- AI Ready.
- Cloud Ready.
- Cloud Optional.
- Scale on Demand.
- Human in Control.
- Safety First.

Betriebs- und Entwicklungsrahmen:
- Das komplette Analysesystem wird zuerst lokal auf dem vorhandenen Windows-Rechner entwickelt, betrieben und nachweislich validiert.
- Referenzhardware:
   - Intel Core i3-1215U.
   - Rund 8 GB RAM.
   - Integrierte Intel-Grafik.
- Keine verpflichtende Cloud-Laufzeitabhaengigkeit fuer das lokale Kernsystem.
- GitHub und Copilot sind Entwicklungs- und QS-Werkzeuge, nicht Laufzeitvoraussetzungen.
- Externe Marktdatenbeschaffung ist mit lokaler Analyse vereinbar.
- Keine kostenpflichtigen APIs, externen Rechenserver oder Hardwarekaeufe ohne ausdrueckliche PO-Freigabe.
- Cloud-Rechenleistung und externe KI-Modelle sind optionale spaetere Erweiterungen.

15. Strategisches Marktuniversum (konfigurierbar)

Zielumfang:
- Rund 20 Kryptowaehrungen.
- 5 Rohstoffe.
- 10 Technologiekonzerne.
- Insgesamt rund 35 Basiswerte.

Rohstoffgruppen (vorbehaltlich finaler Instrumentauswahl):
- Gold.
- Silber.
- Oel.
- Erdgas.
- Uran (vorbehaltlich abschliessender PO-Bestaetigung).

Verbindliche Leitplanken:
- Keine hart einprogrammierte unveraenderliche Asset-Liste.
- Marktuniversum konfigurierbar halten.
- Unterschiedliche Handelszeiten, Datenfrequenzen und Instrumenteigenschaften beruecksichtigen.
- Konkrete Instrumente, Datenanbieter und Symbole werden separat festgelegt.

16. Multi-Timeframe Zielarchitektur (strategisch)

Zielhorizont bis zu sieben Zeitebenen:
- 1 Monat.
- 1 Woche.
- 1 Tag.
- 4 Stunden.
- 1 Stunde.
- 15 Minuten.
- 5 Minuten.

Strategischer Gesamtumfang:
- Bis zu 245 Markt-Zeitebenen-Kombinationen.

Leitplanken fuer Umsetzung:
- Keine Pflicht, alle Kombinationen gleichzeitig zu berechnen.
- Ressourcenschonende Priorisierung.
- Wiederverwendung vorhandener Ergebnisse.
- Inkrementelle Verarbeitung.

17. Command-Center Designreferenz (nicht als Ist-Implementierung)

Der historische Prototyp bleibt Designreferenz fuer die strategische Zielrichtung:
- Dunkles Chartdesign.
- Vier gleichzeitige Charts im 2x2-Layout.
- Frei konfigurierbare Zeitebenen.
- Individuell maximierbare Charts.
- Elliott-Wellenzaehlung.
- Fibonacci-Retracements und Projektionen.
- EMA 20 und EMA 50.
- RSI und Stoch-RSI unter den Kurscharts.
- S/R-Zonen.
- Kerzenformationen.
- Ein-/ausschaltbare Overlays.
- Tabellarische Indikatorensicht mit Ampeln/Status.

Intraday-Referenzprofil:
- 4H MAKRO / 1H TAKT / 15M MIKRO / 5M TRIGGER.

Strategische Zusatzprofile (als Vorschlaege gekennzeichnet):
- Swing: 1W / 1D / 4H / 1H.
- Langfristig: 1 Monat / 1W / 1D / 4H.
- Individuell: frei konfigurierbar.

18. Indikatoren- und Ampeltabelle (strategisches Ziel)

Ziel:
- Tabellarische Bewertung pro Markt und Zeitebene.

Komponenten:
- Trend.
- Supertrend.
- EMA.
- RSI.
- Stoch-RSI.
- Elliott Wave.
- Fibonacci.
- Support/Resistance.
- Candlestick Patterns.
- Breakout/Retest.
- Multi-Timeframe-Konfluenz.
- Datenqualitaet.
- Zeitliche Bestaetigung.
- Risiko.

Verbindliche Bewertungsregeln:
- Explizite Trennung von Bullish/Bearish/Neutral, Bestaetigung, Ergebnisverfuegbarkeit, Datenqualitaet, Risiko und Gesamtstatus.
- Gruen bedeutet nicht automatisch Kauf.
- Fehlende Daten duerfen keine kuenstlich positiven Bewertungen erzeugen.
- Keine ungeprueften Handelswahrscheinlichkeiten.
- Bewertungsregeln muessen nachvollziehbar, deterministisch und testbar sein.

19. Strategische Anwendungsbereiche (Roadmap-Zielbild)

Langfristige Zielbereiche:
- Market Radar.
- Opportunity Ranking.
- Multi-Timeframe Command Center.
- Indikatoren-Cockpit.
- Forecast Center.
- Entry Cockpit.
- Risiko- und Portfolio-Management.
- Backtesting.
- Trading Journal.
- Agenten-Kontrollzentrum.

Klarstellung:
- Diese Bereiche sind Roadmap-Ziele, keine Aussage ueber bereits implementierte Funktionen.

20. Lokale Agentenarchitektur (strategisch)

Langfristige Zielrichtung:
- Lokaler Master-Agent als Orchestrator spezialisierter Fachagenten.

Zielverantwortungen:
- Marktdaten und Datenqualitaet.
- Elliott Wave.
- Fibonacci.
- Support/Resistance.
- Price Action.
- Candlestick Patterns.
- Breakout/Retest.
- Trend und Indikatoren.
- Multi-Timeframe-Konfluenz.
- Forecast-Szenarien.
- Risiko.
- Backtesting und Validierung.

Verbindliche Grenzen:
- Zunaechst deterministische, regelbasierte lokale Fachkomponenten.
- Keine Pflicht zu separaten KI-Modellen oder separaten Prozessen pro Agent.
- Optionale spaetere KI-Unterstuetzung nur fuer Interpretation/Zusammenfassung/Szenarioerklaerung.
- KI darf keine fachlichen Regeln umgehen oder Ergebnisse erfinden.
- Ressourcenlimits, Protokollierung, Berechtigungen und kontrollierte Abschaltung vorsehen.
- Keine automatischen Handelsorders.
- Product Owner behaelt die Entscheidungshoheit.

21. Fachliche Voraussetzungen vor produktiver Signalnutzung

Vor produktiver Signalverwendung, historischer Konfluenz und belastbarem Backtesting sind insbesondere verbindlich nachzuweisen:
- Produktive zeitliche Candle-Verfuegbarkeit.
- Explizite Kerzenabschlusszeiten.
- As-of-Semantik.
- Kausale Verfuegbarkeit der Kontextdaten.
- Kausale Pivot-/Swing-Bestaetigung.
- Kausale S/R-Zonen-Verfuegbarkeit.
- Prefix-Invarianz.
- Vermeidung von Look-ahead Bias.
- Ausschluss zeitlich unbekannter oder zukuenftiger Signale.
- Reproduzierbare Ergebnisse.

Verbot:
- Keine produktiven Entry-Signale aus ausschliesslich geometrisch erkannten, zeitlich unbestaetigten Formationen.

22. Langfristige Validierungsstrategie (strategische Reihenfolge)

Phase A:
- Technische lokale Systemgrundlage.

Phase B:
- Vollstaendige lokale Fachanalyse.

Phase C:
- Lokale Agenten-Orchestrierung.

Phase D:
- Historische und unabhaengige Validierung mit realen Marktdaten.

Phase E:
- Paper Trading und lokaler Dauerbetrieb.

Phase F:
- Optionale externe Rechenleistung und KI-Erweiterungen nach PO-Freigabe.

Validierung beinhaltet mindestens:
- Fachliche Korrektheit.
- Reproduzierbarkeit.
- Out-of-sample-Tests.
- Gebuehren, Spread und Slippage.
- Risikopruefung.
- CPU-/RAM-Messungen.
- Laufzeitmessungen.
- Stabilitaet.
- Wiederanlauf und Fehlerbehandlung.

Klarstellung:
- Softwarequalitaet ist kein Nachweis wirtschaftlicher Profitabilitaet.

Ende der Master-Control-Datei.