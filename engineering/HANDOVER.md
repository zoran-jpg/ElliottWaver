# ElliottWaver - Engineering Handover

Paket: EP-DEF-01
Status: TECHNISCH GEPRUEFT
Datum: 2026-11-20
Branch / HEAD: main / 0eb2795e1134e4bda4f5fe414a624b7e17efd27a

## 1. Ausgangslage und tatsaechlich gepruefte Repo-Pfade

- Produktiver Analysepfad (Application-Port):
	- src/elliottwaver/application/analysis.py
	- src/elliottwaver/application/analysis_application.py
- Composition Root:
	- src/elliottwaver/bootstrap/analysis_application_factory.py
- Infrastructure CSV-Adapter:
	- src/elliottwaver/infrastructure/market_data/csv_market_data_provider.py
	- src/elliottwaver/infrastructure/market_data/__init__.py
- Desktop UI:
	- src/elliottwaver/interfaces/desktop_tk.py
- Forecast/Projection (unveraendert belassen):
	- src/elliottwaver/application/forecast/forecast_engine.py
	- src/elliottwaver/domain/projection/fibonacci_projection_engine.py

Expliziter Befund Swing-Erkennung (Architekturergaenzung):
- Im Repository existiert keine bereits vorhandene produktive Candle->Swing-Erkennungsimplementierung.
- Vorhanden sind Domain-Vertraege und Modelle (Candle, Pivot, Swing, Wave) sowie Wave-Detection auf Basis bereits vorbereiteter Swings:
	- src/elliottwaver/domain/market/candle.py
	- src/elliottwaver/domain/market/pivot.py
	- src/elliottwaver/domain/market/swing.py
	- src/elliottwaver/domain/market/wave.py
	- src/elliottwaver/domain/detection/wave_detector.py
- Konsequenz gemaess Vorgabe: keine neue eigenmaechtig gewaehlte Swing-Algorithmik eingefuehrt.

## 2. Umsetzung je DEF-ID

- DEF-002 (Blocker):
	- Ergebnis: BLOCKIERT (architekturseitig), nicht als "behoben" markiert.
	- Ursache: Kein vorhandener produktiver Swing-Algorithmus im Repository, der wiederverwendet werden kann.
	- Umgesetzte Schutzmassnahme:
		- Composition Root verlangt explizit einen konfigurierten CandleToSwingPreparationPort und faellt andernfalls kontrolliert mit DomainError.
			- src/elliottwaver/bootstrap/analysis_application_factory.py
		- Desktop-Produktivpfad verwendet keinen Noop-Testdouble-Algorithmus; stattdessen expliziter Blocker-Port mit klarer Fehlermeldung.
			- src/elliottwaver/interfaces/desktop_tk.py
	- Keine Test-Fakes/Fixtures als produktive Swing-Erkennung eingebaut.

- DEF-004 (Medium):
	- Ergebnis: UMGESETZT.
	- CSV- und Zeitstempelverarbeitung zentralisiert im Infrastructure-Provider:
		- Neue kanonische Request-Spezifikation und Ableitung aus CSV:
			- CsvRequestSpec und infer_request_spec in src/elliottwaver/infrastructure/market_data/csv_market_data_provider.py
		- Export des Specs:
			- src/elliottwaver/infrastructure/market_data/__init__.py
	- Doppelte Parsinglogik aus UI entfernt:
		- infer_request_spec_from_csv delegiert an CsvMarketDataProvider.infer_request_spec.
		- UI parst keine CSV-Zeilen und keine Zeitstempel mehr direkt.
			- src/elliottwaver/interfaces/desktop_tk.py

## 3. Aenderungen

Im Paket bearbeitete Dateien (vollstaendige Repo-Pfade):
- src/elliottwaver/bootstrap/analysis_application_factory.py
- src/elliottwaver/infrastructure/analysis/__init__.py
- src/elliottwaver/infrastructure/market_data/csv_market_data_provider.py
- src/elliottwaver/infrastructure/market_data/__init__.py
- src/elliottwaver/interfaces/desktop_tk.py
- tests/unit/bootstrap/test_analysis_application_factory.py
- tests/unit/infrastructure/market_data/test_csv_market_data_provider.py
- tests/unit/interfaces/test_desktop_tk.py

Entfernte Datei:
- src/elliottwaver/infrastructure/analysis/swing_preparation_adapter.py

Keine Aenderungen an geschuetzten Dateien in diesem Paket:
- tests/unit/application/test_context_service.py
- tests/unit/domain/context/test_elliott_context.py

Hinweis:
- Beide geschuetzten Dateien waren bereits vor Paketstart im Working Tree modifiziert (fremde Voraenderungen), wurden durch dieses Paket nicht angefasst.

## 4. Abnahmekriterien (einzeln)

- [x] DEF-004: CSV-/Zeitstempelverarbeitung zentral im Infrastructure-Provider | Nachweis: src/elliottwaver/infrastructure/market_data/csv_market_data_provider.py, src/elliottwaver/interfaces/desktop_tk.py
- [x] UI parst keine CSV-Zeilen mehr | Nachweis: src/elliottwaver/interfaces/desktop_tk.py
- [x] Keine Aenderung an ForecastEngine/ProjectionEngine | Nachweis: keine Dateioperationen an src/elliottwaver/application/forecast/forecast_engine.py und src/elliottwaver/domain/projection/fibonacci_projection_engine.py
- [x] Keine Aenderung an geschuetzten Dateien | Nachweis: keine Paket-Edits auf tests/unit/application/test_context_service.py und tests/unit/domain/context/test_elliott_context.py
- [ ] DEF-002 vollstaendig behoben | BLOCKIERT wegen fehlender vorhandener produktiver Swing-Erkennungsimplementierung und fehlender Grundsatzentscheidung

## 5. Pruefkommandos und Ergebnisse

Ausgefuehrt mit c:/Users/User/Desktop/ElliottWaver/.venv/Scripts/python.exe

- python -m ruff check src/elliottwaver/interfaces/desktop_tk.py src/elliottwaver/bootstrap/analysis_application_factory.py src/elliottwaver/infrastructure/market_data/csv_market_data_provider.py src/elliottwaver/infrastructure/market_data/__init__.py tests/unit/bootstrap/test_analysis_application_factory.py tests/unit/interfaces/test_desktop_tk.py tests/unit/infrastructure/market_data/test_csv_market_data_provider.py
	- Exitcode: 0

- python -m ruff format --check src/elliottwaver/interfaces/desktop_tk.py src/elliottwaver/bootstrap/analysis_application_factory.py src/elliottwaver/infrastructure/market_data/csv_market_data_provider.py src/elliottwaver/infrastructure/market_data/__init__.py tests/unit/bootstrap/test_analysis_application_factory.py tests/unit/interfaces/test_desktop_tk.py tests/unit/infrastructure/market_data/test_csv_market_data_provider.py
	- Exitcode: 0

- python -m mypy src tests
	- Exitcode: 0
	- Ergebnis: Success: no issues found in 127 source files

- python -m pytest
	- Exitcode: 0
	- Ergebnis: 313 passed
	- Coverage: 91.86% (Gate >= 90% bestanden)

## 6. Praxistest-Anleitung fuer Product Owner

1. Anwendung starten: python.exe -m elliottwaver
2. Gueltige CSV auswaehlen.
3. Analyse starten.
4. Erwartung fuer aktuellen Stand: Verstaendliche Fehlermeldung, dass produktiver Swing-Preparation-Adapter fehlt (kein versteckter Noop/Fake im Produktivpfad).
5. Ungueltige CSV pruefen (fehlende Spalten oder nicht-UTC-Timestamps): Fehlermeldung bleibt nachvollziehbar und kommt aus zentralisiertem CSV-Provider.

## 7. Git-Zustand

- git status --short --branch:
	- ## main...origin/main
	- Vorhandene unstaged Aenderungen:
		- src/elliottwaver/application/__init__.py
		- src/elliottwaver/bootstrap/__init__.py
		- src/elliottwaver/infrastructure/__init__.py
		- src/elliottwaver/interfaces/__init__.py
		- src/elliottwaver/interfaces/analysis.py
		- tests/unit/application/test_context_service.py (geschuetzt, fremde Voraenderung)
		- tests/unit/domain/context/test_elliott_context.py (geschuetzt, fremde Voraenderung)
	- Vorhandene untracked Bereiche (Auszug):
		- engineering/HANDOVER.md
		- src/elliottwaver/bootstrap/analysis_application_factory.py
		- src/elliottwaver/infrastructure/market_data/csv_market_data_provider.py
		- src/elliottwaver/interfaces/desktop_tk.py
		- tests/unit/bootstrap/test_analysis_application_factory.py
		- tests/unit/infrastructure/market_data/test_csv_market_data_provider.py
		- tests/unit/interfaces/test_desktop_tk.py

- Commit:
	- KEIN COMMIT (gem. Vorgabe)

## 8. Risiken, Abweichungen und offene Fragen

- Hauptblocker DEF-002:
	- Fehlende vorhandene produktive Swing-Erkennung verhindert Umsetzung "Reuse bestehender Algorithmus".
	- Fuer eine deterministische produktive Swing-Erkennung fehlt eine freigegebene Fach-/Architekturentscheidung zu:
		- Pivot-Definition (lokale Extrema vs. Fraktal-Regel vs. weitere Kriterien)
		- Mindestanzahl Kerzen je Bestimmung
		- Tie-Breaker bei Gleichstaenden und Flat-Strukturen
		- Zeitliche/marktbezogene Filter
		- Deterministische ID- und Stabilitaetsregeln

- DEF-004 ist unabhaengig umsetzbar gewesen und wurde ohne Architekturkonflikt umgesetzt.

## 9. Naechste empfohlene Aktion

- Architekturreview und Fachfreigabe fuer die fehlende produktive Swing-Erkennung einholen (explizite Regeldefinition), danach gezielt DEF-002 finalisieren.
- Bis zur Freigabe keine neue algorithmische Grundsatzentscheidung implementieren.

## 10. Nachbesserung DEF-004 (Windows CSV BOM)

Ausloeser:
- Manueller Praxistest mit C:\Users\User\Desktop\ElliottWaver\test_market_data.csv meldete faelschlich:
	- CSV is missing required columns: symbol.

Technische Ursache (nachgewiesen):
- Dateibytes beginnen mit UTF-8 BOM (EF BB BF).
- Bei decoding mit utf-8 wurde der erste Header als \ufeffsymbol statt symbol erkannt.
- Nachweis (Read-only Analyse):
	- FIRST_BYTES=EF BB BF 73 79 6D 62 6F 6C ...
	- FIELDNAMES_UTF8 ['\ufeffsymbol', 'timeframe', ...]
	- FIELDNAMES_UTF8_SIG ['symbol', 'timeframe', ...]

Umsetzung:
- Zentraler Infrastructure-CSV-Parser auf utf-8-sig umgestellt, sodass UTF-8 ohne BOM und UTF-8 mit BOM beide akzeptiert werden.
- Damit nutzen sowohl Metadatenableitung (infer_request_spec) als auch Candle-Laden (load_candles) denselben korrigierten Parsingvertrag ueber _read_rows().
- Geaenderte Datei:
	- src/elliottwaver/infrastructure/market_data/csv_market_data_provider.py

Regressionstests ergaenzt:
- tests/unit/infrastructure/market_data/test_csv_market_data_provider.py
	- UTF-8 mit BOM: load_candles akzeptiert Header korrekt.
	- UTF-8 mit BOM: infer_request_spec akzeptiert Header korrekt.
	- UTF-8 mit BOM + wirklich fehlende symbol-Spalte: korrekte Fehlermeldung.
	- Bestehende UTF-8-ohne-BOM-Tests bleiben bestehen.

Validierung:
- Relevante Tests (selektiv) ausgefuehrt:
	- pytest tests/unit/infrastructure/market_data/test_csv_market_data_provider.py tests/unit/interfaces/test_desktop_tk.py tests/unit/bootstrap/test_analysis_application_factory.py
	- 35 passed
	- Hinweis: selektiver Lauf unterschreitet globales Coverage-Gate (bekanntes Verhalten bei Teilmengenlauf)
- Vollstaendiger Gate-Lauf ausgefuehrt:
	- python -m pytest -> 316 passed, Coverage 91.86% (>=90%)
- Ruff:
	- python -m ruff check <betroffene Dateien> -> PASS
- MyPy:
	- python -m mypy src tests -> PASS
- Reale Praxisdatei direkt ueber zentralen Parser validiert:
	- CsvMarketDataProvider(csv_path='C:/Users/User/Desktop/ElliottWaver/test_market_data.csv').infer_request_spec()
	- Ergebnis: SPEC_OK EURUSD 1h 2026-07-21T00:00:00+00:00 2026-07-21T05:00:00+00:00

Erwartetes naechstes Verhalten:
- test_market_data.csv wird jetzt korrekt eingelesen (kein false positive auf fehlende symbol-Spalte).
- Analyse darf danach weiterhin kontrolliert am fehlenden produktiven Swing-Preparation-Adapter abbrechen (bekannter DEF-002-Blocker), jedoch nicht mehr am CSV-Header.

## 11. Abschlussupdate DEF-002 (produktive Swing-Erkennung)

Status:
- DEF-002 ist nun produktiv umgesetzt.

Implementierung:
- Neue produktive Adapter-Implementierung:
	- src/elliottwaver/infrastructure/analysis/swing_preparation_adapter.py
- Export im Infrastructure-Paket:
	- src/elliottwaver/infrastructure/analysis/__init__.py
- Composition Root verwendet nun standardmaessig den produktiven Adapter, Test-Override bleibt moeglich:
	- src/elliottwaver/bootstrap/analysis_application_factory.py
- Desktop-Produktivpfad nutzt den Composition Root ohne Blocker/Noop:
	- src/elliottwaver/interfaces/desktop_tk.py

Deterministische Regeln im Adapter:
- Konfigurierbare Pivot-Bestaetigung ueber left/right confirmation candles.
- Rechte Kante ohne vollstaendige right-confirmation wird nicht als Pivot zugelassen.
- Tie-Break bei gleichen Hochs/Tiefs deterministisch ueber linkestes Vorkommen im Fenster.
- Normalisierung auf alternierende Pivot-Sequenz.
- Bei aufeinanderfolgenden gleichen Pivot-Typen bleibt der extremere Pivot erhalten (bei Gleichheit der fruehere).
- Swing-IDs und Pivot-IDs deterministisch aus stabilen Eingabedaten (uuid5).

Tests (neu/angepasst):
- Neu:
	- tests/unit/infrastructure/analysis/test_swing_preparation_adapter.py
	- Abgedeckte Faelle: Pivot-High/Low, Tie-Break, Alternation-Normalisierung, right-edge confirmation, sideways/flat data, insufficient data.
- Aktualisiert:
	- tests/unit/bootstrap/test_analysis_application_factory.py
	- tests/unit/interfaces/test_desktop_tk.py
	- E2E-Nachweis CSV -> Candles -> reale Swings -> Forecast -> Projektionen ohne Swing-Fakes.

Validierung (vollstaendige Gates, nach Abschluss DEF-002):
- python -m ruff format .
	- Ergebnis: PASS
- python -m ruff check .
	- Ergebnis: PASS
- python -m mypy src tests
	- Ergebnis: PASS (Success: no issues found in 129 source files)
- python -m pytest
	- Ergebnis: 322 passed
	- Coverage: 91.71% (Gate >= 90% bestanden)

Schutzdateien unveraendert:
- tests/unit/application/test_context_service.py
- tests/unit/domain/context/test_elliott_context.py

## 12. DEF-003 Desktop-Analyse ohne UI-Blockierung

Status:
- DEF-003 ist umgesetzt (keine Aenderungen an ForecastEngine, ProjectionEngine oder Swing-Erkennungsalgorithmus).

Technische Umsetzung:
- Betroffene Produktionsdatei:
	- src/elliottwaver/interfaces/desktop_tk.py
- Analyseausfuehrung wurde von synchron/blockierend auf kontrollierten Hintergrund-Worker umgestellt.
- Verwendete Architektur:
	- Worker-Thread (`threading.Thread`, daemon)
	- Thread-sichere Ergebnisuebergabe (`queue.Queue`)
	- UI-Hauptthread-Polling via `root.after(...)`
- Alle UI-Aktualisierungen (Status, Felder, MessageBox, Button-State) laufen ausschliesslich im UI-Hauptthread.
- Startbutton-Handling:
	- waehrend laufender Analyse deaktiviert
	- nach Erfolg/Fehler wieder aktiviert
- Parallel-/Doppellaeufe:
	- aktive Analyse wird ueber Guard verhindert
	- weiterer Startversuch waehrend Lauf liefert Statushinweis "Analyse laeuft bereits."
- Fenster-Schliessen waehrend laufendem Worker:
	- `WM_DELETE_WINDOW` ist abgefangen
	- keine blockierende Warteoperation im UI-Thread
	- keine UI-Aktualisierung nach Schliessen

Ergaenzte/angepasste Tests (deterministisch):
- tests/unit/interfaces/test_desktop_tk.py
	- Erfolgspfad asynchron (Worker + Queue + after-Polling)
	- Fehlerpfad asynchron inkl. Fehlermeldung
	- Doppelklick-/Parallellauf-Schutz
	- UI-Thread-Handoff: keine fruehe UI-Aktualisierung vor Polling
	- Fenster-Schliessen waehrend laufendem Worker (keine spaete UI-Updates)

Validierung DEF-003:
- python -m pytest --no-cov tests/unit/interfaces/test_desktop_tk.py
	- Ergebnis: 24 passed
- python -m ruff check .
	- Ergebnis: PASS
- python -m mypy src tests
	- Ergebnis: PASS (Success: no issues found in 129 source files)
- python -m pytest
	- Ergebnis: 325 passed
	- Coverage: 91.39% (Gate >= 90% bestanden)

Risiken / Einschraenkungen:
- Laufender Worker wird beim Fenster-Schliessen nicht aktiv gecancelt (bewusst, um keine blockierende Join-/Cancel-Logik im UI-Thread einzufuehren); durch Guarding erfolgen jedoch keine spaeten UI-Zugriffe mehr.

Manuelle Pruefschritte DEF-003 (Desktop):
1. Anwendung starten: `python -m elliottwaver`
2. Gueltige CSV laden.
3. Analyse starten und waehrenddessen Fenster bewegen, fokussieren, groesse aendern: UI bleibt responsiv.
4. Analyse-Button waehrend Lauf mehrfach klicken: kein zweiter Lauf, Status zeigt laufende Analyse.
5. Nach Abschluss pruefen: Ergebnis-/Forecast-/Fibonacci-Felder werden wie gewohnt gefuellt, Button wieder aktiv.
6. Analyse erneut starten und Fenster waehrend Lauf schliessen: kein Haengen, keine spaeten UI-Fehlerdialoge.

### Abschliessende DEF-003-Abnahme (deterministisch, kontrolliert blockierender Worker)

Hinweis zur Methodik:
- Der Worker wird im Test ueber `_FakeThread` kontrolliert blockierend simuliert (`start()` fuehrt den Target-Code nicht aus; Freigabe erfolgt explizit mit `run_target()`). Dadurch ist der UI-Thread-Handoff ueber Queue/`after()` deterministisch pruefbar.

Ausgefuehrte gezielte Abnahmetests:
- `tests/unit/interfaces/test_desktop_tk.py::test_desktop_app_run_analysis_success_updates_ui_fields`
	- Ergebnis: PASS
	- Nachweis: Startbutton deaktiviert waehrend Lauf und nach Ergebnis wieder aktiviert; Ergebnisdarstellung korrekt.
- `tests/unit/interfaces/test_desktop_tk.py::test_desktop_app_run_analysis_error_shows_message`
	- Ergebnis: PASS
	- Nachweis: Fehlerpfad ueber Queue/`after()` und Fehlerdialog.
- `tests/unit/interfaces/test_desktop_tk.py::test_desktop_app_prevents_parallel_or_double_run`
	- Ergebnis: PASS
	- Nachweis: Schutz gegen parallele/doppelte Analyse (nur ein Worker-Start).
- `tests/unit/interfaces/test_desktop_tk.py::test_desktop_app_ui_updates_happen_only_after_main_thread_poll`

## 13. EP-06 Abschluss: CI, Packaging und reproduzierbare Installation

Status:
- DEF-011 umgesetzt.
- DEF-012 umgesetzt.
- DEF-010 (transitive Reproduzierbarkeit) nachgezogen und validiert.

Umgesetzte Aenderungen:
- CI-Workflow erweitert auf Linux- und Windows-Matrix:
	- `.github/workflows/quality.yml`
	- constraints-basierte Installation (`-c constraints/dev.txt`) in CI
	- Linux-headless Testlauf via `xvfb-run`
- Wheel-Smoke-Job ergaenzt (Linux und Windows):
	- Wheel Build (`python -m build --wheel`)
	- frische venv, Wheel-Installation, `pip check`
	- Smoke-Skript-Ausfuehrung
- Smoke-Skript fuer installierte Distribution ergaenzt:
	- `engineering/scripts/wheel_smoke.py`
	- prueft Importierbarkeit zentraler Module inkl. Swing- und Chart-Komponenten
	- prueft CLI-Einstiegspunkt (`python -m elliottwaver --help`)
- Constraints auf transitive Reproduzierbarkeit erweitert:
	- `constraints/runtime.txt`
	- `constraints/dev.txt`
- Vertragstests fuer Packaging/CI erweitert:
	- `tests/unit/test_packaging_contract.py`
- README um Wheel-Smoke-Anleitung und vereinheitlichte Quality-Gate-Befehle erweitert:
	- `README.md`

Unveraendert belassen (geschuetzte Dateien):
- `tests/unit/application/test_context_service.py`
- `tests/unit/domain/context/test_elliott_context.py`

Validierung (vollstaendige Gates, lokal):
- `python -m ruff format .`
	- PASS
- `python -m ruff check .`
	- PASS
- `python -m mypy src tests`
	- PASS (no issues found in 135 source files)
- `python -m pytest`
	- PASS (371 passed)
	- Coverage: 92.65% (Gate >= 90% bestanden)

Git-Status:
- Kein Commit erstellt (gem. Vorgabe).
- Working Tree ist weiterhin dirty (inkl. bereits vorhandener fremder Aenderungen).
	- Ergebnis: PASS
	- Nachweis: keine UI-Aktualisierung vor Mainthread-Poll; Aktualisierung erst nach `after()`-Pump.
- `tests/unit/interfaces/test_desktop_tk.py::test_desktop_app_close_while_worker_running_suppresses_ui_updates`
	- Ergebnis: PASS
	- Nachweis: sicheres Schliessen waehrend laufender Berechnung, keine spaeten UI-Zugriffe.

Konsistenzlauf Desktop-Testmodul:
- `python -m pytest --no-cov -q tests/unit/interfaces/test_desktop_tk.py`
	- Ergebnis: 24 passed in 0.35s

Gezielter Abnahmelauf (nur die 5 obigen Tests):
- `python -m pytest --no-cov -q <5 DEF-003-Tests>`
	- Ergebnis: 5 passed in 0.51s

## 13. EP-DEF-02 Abschluss (DEF-005 und DEF-006)

Status:
- EP-DEF-02 (nur DEF-005 und DEF-006) ist abgeschlossen und technisch verifiziert.

Umfang DEF-005 (Desktop-Architektur entkoppeln):
- In `src/elliottwaver/interfaces/desktop_tk.py` wurde die Desktop-Orchestrierung in einen klaren Controller/View-Schnitt getrennt:
	- `DesktopAnalysisView` als UI-Vertrag
	- `DesktopAnalysisController` fuer Thread-/Queue-/Polling-Orchestrierung
	- `AnalysisDesktopTkApp` als Tk-View-Bridge ohne Worker-Thread-UI-Zugriffe
- Die bestehende Produktivpipeline CSV -> AnalysisApplication -> Forecast/Projection bleibt unveraendert im Verhalten.

Umfang DEF-006 (Testqualitaet und Entkopplung):
- `tests/unit/interfaces/test_desktop_tk.py` wurde auf deterministische, typisierte Controller-Tests ausgerichtet:
	- typed doubles (`_FakeView`, `_FakeThread`)
	- explizite Tests fuer Mainthread-Handoff (`schedule_after`), Doppellauf-Schutz, Close-waehrend-Run und Fehlerpfad
	- zusaetzliche Branch-Tests fuer Guard-Pfade und Queue-Polling
	- produktiver Pipeline-Nachweis bleibt enthalten (`test_desktop_controller_productive_csv_to_forecast_pipeline_remains_functional`)

Im Paket geaenderte Dateien:
- src/elliottwaver/interfaces/desktop_tk.py
- tests/unit/interfaces/test_desktop_tk.py

Nicht geaendert (explizit geschuetzt):
- tests/unit/application/test_context_service.py
- tests/unit/domain/context/test_elliott_context.py

Pruefkommandos und finale Ergebnisse:
- `python -m ruff format .`
	- Ergebnis: PASS (129 files left unchanged)
- `python -m ruff check .`
	- Ergebnis: PASS
- `python -m mypy src tests`
	- Ergebnis: PASS (Success: no issues found in 129 source files)
- `python -m pytest`
	- Ergebnis: 333 passed
	- Coverage: 90.31% (Gate >= 90% bestanden)

Wesentliche Testnachweise DEF-005/DEF-006:
- `tests/unit/interfaces/test_desktop_tk.py::test_desktop_app_ui_updates_happen_only_after_main_thread_poll` -> PASS
- `tests/unit/interfaces/test_desktop_tk.py::test_desktop_app_prevents_parallel_or_double_run` -> PASS
- `tests/unit/interfaces/test_desktop_tk.py::test_desktop_app_close_while_worker_running_suppresses_ui_updates` -> PASS
- `tests/unit/interfaces/test_desktop_tk.py::test_desktop_controller_poll_ignores_stale_run_result_and_reschedules` -> PASS
- `tests/unit/interfaces/test_desktop_tk.py::test_desktop_controller_productive_csv_to_forecast_pipeline_remains_functional` -> PASS

Risiken / Einschraenkungen:
- Beim Schliessen wird ein laufender Worker nicht aktiv gecancelt; spaete UI-Updates sind jedoch durch Controller-Guards unterbunden.
- `AnalysisDesktopTkApp` enthaelt weiterhin Tk-Widget-Bau und -Bridge in einer Klasse; die eigentliche Analyse-Orchestrierung ist jedoch getrennt und testbar.

## 14. EP-03 Abschluss (DEF-007, DEF-015, CHART-001)

Status:
- EP-03 ist technisch umgesetzt und vollstaendig geprueft.

Umfang DEF-007 (Interfaces-API kuratieren):
- Reexport-Flaeche in den Interfaces wurde reduziert, um die oeffentliche API auf benoetigte Vertraege zu begrenzen:
	- `src/elliottwaver/interfaces/analysis.py` exportiert jetzt nur noch die stabilen Analyse-Contracts.
	- `src/elliottwaver/interfaces/__init__.py` exportiert nur noch Desktop-Entrypoint/View-nahe Symbole.
- Kompatibilitaet fuer den produktiven Startpfad bleibt erhalten (`from elliottwaver.interfaces import launch_analysis_desktop`).

Umfang DEF-015 (selected_wave-Validierung entdoppeln):
- Strukturelle Invariante `selected_wave must not be None` verbleibt zentral in `ContextRequest`.
- Redundante Wiederholungspruefung in `ContextService.create_context` wurde entfernt.
- Service nutzt jetzt ein getyptes `cast` auf bereits validierte Request-Daten.

Umfang CHART-001 (UI-unabhaengiger Chart-Datenvertrag):
- Neuer, unveraenderlicher und typisierter Chart-Vertrag inkl. Adapter eingefuehrt:
	- `src/elliottwaver/application/chart_contract.py`
- Abgedeckte Daten:
	- OHLC-Candles mit UTC-Zeitstempel und Preisen
	- Swings und Pivots mit eindeutiger zeitlicher Zuordnung (inkl. IDs)
	- Forecast-Szenarien und Fibonacci-Projektionen
- Deterministische Reihenfolge:
	- Candles, Swings, Pivots und Projektionen werden stabil sortiert.
- Fehlerbehandlung:
	- Klarer DomainError bei fehlenden chartbaren Daten.
	- Klarer DomainError bei inkonsistenten Pivot-Koordinaten.
- Keine Tkinter-Abhaengigkeit und keine Vermischung mit Rendering.
- ForecastEngine und ProjectionEngine unveraendert.

Im Paket geaenderte Dateien:
- src/elliottwaver/application/chart_contract.py
- src/elliottwaver/application/__init__.py
- src/elliottwaver/application/context_service.py
- src/elliottwaver/interfaces/analysis.py
- src/elliottwaver/interfaces/__init__.py
- tests/unit/application/test_chart_contract.py
- tests/unit/interfaces/test_analysis_exports.py

Explizit nicht geaendert (geschuetzt):
- tests/unit/application/test_context_service.py
- tests/unit/domain/context/test_elliott_context.py

Neue/angepasste Testnachweise EP-03:
- `tests/unit/application/test_chart_contract.py`
	- Mapping + deterministische Reihenfolge
	- fehlende Daten
	- Fehlerfall mit Pivot-Koordinatenkonflikt
- `tests/unit/interfaces/test_analysis_exports.py`
	- kuratierte Exporte in `interfaces` und `interfaces.analysis`

Vollstaendige Gate-Ergebnisse (EP-03):
- `python -m ruff format .`
	- Ergebnis: PASS (132 files left unchanged)
- `python -m ruff check .`
	- Ergebnis: PASS
- `python -m mypy src tests`
	- Ergebnis: PASS (Success: no issues found in 132 source files)
- `python -m pytest`
	- Ergebnis: 339 passed
	- Coverage: 90.64% (Gate >= 90% bestanden)

Risiken / Entscheidungen:
- `interfaces.__init__` exportiert bewusst eine schmalere API. Interne Repository-Nutzung bleibt kompatibel; externe Nutzer mit breiten Root-Reexports muessen auf direkte Imports umstellen.
- Master-Control-Abschnitt 11 nennt historisch "Aktives Paket: KEINES"; EP-03 wurde auf explizite Product-Owner-Freigabe in dieser Session umgesetzt.

### EP-03 Abschlusspruefung (2026-11-21)

Scope der Nachpruefung:
- CHART-001 Datenvertrag (Zeitstempel/OHLC/Referenzen/Chronologie/Fibonacci-Mapping)
- DEF-007 Import-Kompatibilitaet
- DEF-015 Validierungsabdeckung `selected_wave`

Nachgezogene Testverstaerkung:
- `tests/unit/application/test_chart_contract.py`
	- zusaetzliche Assertions fuer OHLC-Zuordnung
	- explizite Referenzpruefung von Swing- zu Pivot-IDs
	- explizite Chronologiepruefung von Swing-/Pivot-Zeitpunkten
	- deterministische Feldpruefung fuer Fibonacci-Projektionen

Erneute Voll-Gates:
- `python -m ruff format .` -> PASS
- `python -m ruff check .` -> PASS
- `python -m mypy src tests` -> PASS
- `python -m pytest` -> 340 passed, Coverage 90.64%

Keine Aenderung an geschuetzten Dateien:
- tests/unit/application/test_context_service.py
- tests/unit/domain/context/test_elliott_context.py

## 15. Schlanke Abschlussbericht-Vorlage (wiederverwendbar)

Verwende fuer kuenftige Paketabschluesse folgendes kompakte Format:

1. Paketstatus: `PASS | BLOCKED`
2. Implementierte Aenderungen:
	- Vollstaendige relative Repo-Pfade der geaenderten Dateien
3. Qualitaets-Gates:
	- `pytest`: `<anzahl passed>`
	- `coverage`: `<xx.xx%>`
	- `ruff check`: `PASS|FAIL`
	- `mypy`: `PASS|FAIL`
4. API-/Kompatibilitaetslage:
	- Kurzfazit inkl. Import-/Contract-Risiken
5. Fachliche Kernpruefung (paketspezifisch):
	- z. B. Chart-Vertrag / Thread-Sicherheit / CI-Artefakte
6. Risiken/Architekturentscheidungen:
	- nur verbleibende, entscheidungsrelevante Punkte
7. Benutzeraktion:
	- `erforderlich | nicht erforderlich`

## 16. EP-04 Abschluss (DEF-008, DEF-009, DEF-013, CHART-002)

Status:
- EP-04 ist fuer den beauftragten Scope technisch umgesetzt und vollstaendig verifiziert.

Umgesetzter Scope:
- CHART-002 (erster integrierter Candlestick-Chart):
	- Neue, testbare Tk-Chart-Komponente mit separater Render-Planung und Viewport-Logik:
		- src/elliottwaver/interfaces/chart_tk.py
	- Desktop-Integration ueber CHART-001-Vertrag ohne Aenderung der Worker/Queue/after-Architektur:
		- src/elliottwaver/interfaces/desktop_tk.py
	- Chart-Robustheit: Wenn Chart-Mapping fehlschlaegt, bleiben Text-Resultate verfuegbar und UI bleibt stabil.
- DEF-008 (CLI-Entrypoint):
	- Script-Entrypoint in Packaging ergaenzt:
		- pyproject.toml (`[project.scripts] elliottwaver = "elliottwaver.__main__:main"`)
- DEF-009 (Makefile-Pip-Aufruf):
	- unqualifizierten `pip`-Aufruf durch interpreter-gebundenes `python -m pip` ersetzt:
		- Makefile
- DEF-013 (README fuer Windows + Start + Praxistest):
	- Windows-PowerShell-Setup, Startvarianten und praktischer Chart-Test dokumentiert:
		- README.md

Neue/angepasste Tests:
- tests/unit/interfaces/test_chart_tk.py
	- Render-Model (OHLC/Chronologie/Labels)
	- Viewport (Pan/Zoom/Reset)
	- Platzhalter-/Render-Zweige
	- Mainthread-Guard
- tests/unit/interfaces/test_desktop_tk.py
	- Chart-Render/Clear-Integration im Controller-Pfad
	- Tk-App-Methoden/Dialogfluss
	- Launcher-Verkabelung
- tests/unit/test_packaging_contract.py
	- pyproject Script-Metadaten
	- Makefile Install-Contract (`python -m pip`)

Vollstaendige Gates (nach finalem Stand):
- `python -m ruff check .`
	- Ergebnis: PASS
- `python -m mypy src tests`
	- Ergebnis: PASS (Success: no issues found in 135 source files)
- `python -m pytest`
	- Ergebnis: 356 passed
	- Coverage: 92.50% (Gate >= 90% bestanden)

Explizit unveraenderte geschuetzte Dateien:
- tests/unit/application/test_context_service.py
- tests/unit/domain/context/test_elliott_context.py

Praktischer Windows-Chart-Test (manuell):
1. `python -m elliottwaver` starten.
2. In der Desktop-UI `Datei auswaehlen` klicken.
3. `engineering/testdata/swing_e2e_100.csv` laden.
4. `Analyse starten` ausfuehren.
5. Erwartung: Ergebnis-/Forecast-/Projektionstexte sichtbar und Candlestick-Chart sichtbar.
6. Chart-Bedienung pruefen: Pan links/rechts, Zoom +/-, dann `Reset`.

## 17. EP-04 Visuelle Abschlussnachpruefung (gezielt)

Status:
- Nachpruefung abgeschlossen, nachgewiesene Probleme korrigiert.

1) Ursache der "horizontalen Candles":
- Befund ist datengetrieben, kein mathematischer Render-Fehler.
- Messung auf `engineering/testdata/swing_e2e_100.csv` (100 Zeilen):
	- Preisbereich gesamt: `low_min=100.0`, `high_max=1320.0`, Spanne `1220.0`
	- Candle-Body: `min=0.0`, `median=1.0`, `max=5.0`
	- Wick-Spanne (`high-low`): `min=2.0`, `median=3.0`, `max=7.0`
	- `zero_body_count=50`, `body<=2_count=99`
- Interpretation: Sehr kleine Bodies/Wicks relativ zur Gesamtspanne fuehren visuell zu kurzen Strich-Koerpern, obwohl die Skalierung korrekt ist.

2) Gezielte Korrektur (nachgewiesenes Layoutproblem):
- Desktop-Oberflaeche auf groessenveraenderbares Vertical-Pane-Layout umgestellt.
- Analysefelder und Chart liegen jetzt in getrennten, resizablen Pane-Bereichen; Chartflaeche kann aktiv vergroessert werden.
- Datei:
	- `src/elliottwaver/interfaces/desktop_tk.py`

3) Fachpruefung Rendering (Skalierung/Koerper/Dochte/Zeitachse/Viewport):
- Deterministische Tests erweitert fuer:
	- Preis-Mapping und Chronologie
	- Mindestkoerperhoehe bei Flat-Body
	- Viewport-Grenzen (Pan/Zoom-Clamp)
	- Reset-Verhalten zurueck auf initiales Sichtfenster
	- Layout-Pane-Existenz in der Tk-App
- Dateien:
	- `tests/unit/interfaces/test_chart_tk.py`
	- `tests/unit/interfaces/test_desktop_tk.py`

4) Verifikation Normal- vs. grosse Fenstergroesse:
- Technischer Tk-Messlauf (nicht-interaktiv) nach Layout-Fix:
	- `chart_height_normal=198` bei `940x640`
	- `chart_height_large=302` bei `1400x900`
- Ergebnis: Chartflaeche waechst mit Fenstergroesse und ist nicht mehr auf einen abgeschnittenen Restbereich reduziert.

5) Schutz-/Scope-Konformitaet:
- Keine Aenderung an ForecastEngine, ProjectionEngine oder Swing-Algorithmus.
- Geschuetzte Dateien unveraendert:
	- `tests/unit/application/test_context_service.py`
	- `tests/unit/domain/context/test_elliott_context.py`

6) Vollstaendige Gates nach Nachpruefung:
- `python -m ruff check .` -> PASS
- `python -m mypy src tests` -> PASS
- `python -m pytest` -> 359 passed
- Coverage -> `92.56%` (Gate >= 90% bestanden)

Einziger reproduzierbarer Windows-Chart-Test (EP-04):
1. `python -m elliottwaver`
2. `engineering/testdata/swing_e2e_100.csv` laden
3. `Analyse starten`
4. Fenster auf normale Groesse lassen (ca. `940x640`), dann vergroessern/maximieren
5. Erwartung:
	- Analyse bleibt erfolgreich (Status abgeschlossen)
	- Chart ist in beiden Groessen sichtbar
	- Chartbereich vergroessert sich mit Fenstergroesse (resizable Pane)
6. Bedienung pruefen: mehrfach `+`, `-`, `<`, `>`, danach `Reset`

## 18. EP-05 Abschluss (DEF-010, DEF-016, CHART-003)

Status:
- EP-05 fuer den freigegebenen Scope ist umgesetzt und technisch verifiziert.

Umsetzung CHART-003 (Swing-/Pivot-Visualisierung):
- Die bestehende Chart-Komponente wurde um Overlay-Rendering erweitert, ohne neue Swing-Erkennung in der UI einzufuehren.
- Datenquelle bleibt ausschliesslich der produktive CHART-001-Datenvertrag.
- Darstellungen:
	- bestaetigte Swing-Highs/-Lows mit unterscheidbaren Markierungen
	- Verbindung bestaetigter Swing-Punkte in chronologischer Reihenfolge
	- Pivot-Punkte getrennt von bestaetigten Swings
- Koordinatenzuordnung erfolgt exakt ueber Candle-Timestamp + Preis-Mapping.
- Look-ahead-Schutz: nur Pivot-IDs aus bestaetigten Swings werden als bestaetigte Swing-Marker gezeichnet.
- Zoom/Pan/Reset fuehren alle Overlays konsistent mit.
- Hauptthread-Regel unveraendert: alle Tk-Operationen bleiben main-thread-only.
- Datei:
	- `src/elliottwaver/interfaces/chart_tk.py`

Umsetzung DEF-010 (reproduzierbare Dependencies):
- Constraints-Strategie eingefuehrt (kein zweites konkurrierendes Lock-Tool):

## 20. EP-07 Abschluss (CHART-004, DEF-001, DEF-014)

Status:
- EP-07 Scope umgesetzt und lokal technisch verifiziert.

### CHART-004 - Elliott-Wellen, Fibonacci und Forecast-Visualisierung

Geaenderte Produktionsdateien:
- `src/elliottwaver/application/chart_contract.py`
- `src/elliottwaver/interfaces/chart_tk.py`

Umsetzung:
- Chart-Datenvertrag um explizite, bereits selektierte Wellen erweitert:
	- `ChartWaveAnchor`, `ChartWave`, `TimeframeChartData.selected_waves`
	- Ableitung ausschliesslich aus `selection_result.selected_candidates` der Analyse.
- Label-Regeln ohne Heuristik:
	- `1-5` nur bei `impulse` mit genau 5 Swings.
	- `A-B-C` nur bei `corrective` mit genau 3 Swings.
	- sonst keine Wellenlabels.
- Keine kuenstliche Wellenzaehlung:
	- fehlende oder nicht sichtbare Anker werden nicht durch Swing-Punkte ersetzt.
- Chart-Renderer um Overlays erweitert:
	- selektierte Wellenlinien und Wellenlabels
	- Fibonacci-Ziellinien inkl. Ratio/Preis-Beschriftung
	- primaere/alternative Szenario-Annotation aus echten Forecast-Szenarien
- Visuelle Trennung:
	- Candles, bestaetigte Swings, Wellenoverlays und Projektionen getrennt gezeichnet.
- Look-ahead-Schutz:
	- bestehender Pivot/Swing-Confirmationschutz bleibt aktiv.
	- keine unbestaetigten Pivot-Punkte als bestaetigte Wellenmarker.
- Zoom/Pan/Reset:
	- alle neuen Overlays viewport-synchron.
- Mainthread-Sicherheit:
	- Rendering/Interaktion bleiben im Tk-Mainthread; keine Worker-Tk-Zugriffe.

Nicht geaendert:
- ForecastEngine
- ProjectionEngine
- Swing-Algorithmus

### DEF-001 - Governance-Konsistenz

Geaenderte Dokumente:
- `PROJECT_MANIFEST.md`
- `docs/project/status/CURRENT_STATUS.md`
- `docs/project/ROADMAP.md`
- `docs/project/METRICS.md`
- `docs/project/DECISIONS.md`

Umsetzung:
- Widersprueche mit dem tatsaechlichen Stand aufgeloest.
- Rollen der Governance-Dokumente explizit getrennt (Manifest/Status/Roadmap/Metrics/Decisions).
- Historische Informationen beibehalten und als historisch markiert.
- Offenes EP-06-Gate (echte GitHub-Actions-Matrix) explizit erhalten.
- Keine unbelegten Aussagen ueber ausgefuehrte GitHub-CI-Laeufe aufgenommen.

### DEF-014 - Architekturentscheidungen als ADR

Neue ADRs:
- `docs/adr/0002-desktop-controller-view-separation.md`
- `docs/adr/0003-desktop-thread-queue-after-model.md`
- `docs/adr/0004-chart-contract-and-rendering-boundary.md`
- `docs/adr/0005-dependency-ci-packaging-strategy.md`

Index-Integration:
- `docs/project/DECISIONS.md` auf ADR-Links aktualisiert.

### Neue/aktualisierte Tests

Geaenderte Testdateien:
- `tests/unit/application/test_chart_contract.py`
- `tests/unit/interfaces/test_chart_tk.py`
- `tests/unit/test_governance_contract.py` (neu)

Abgedeckte EP-07-Faelle:
- korrekte Zuordnung von Wellenlabels zu vorhandenen Ankern
- Verhalten bei fehlenden/mehrdeutigen Wellenankern
- Fibonacci-Ratio-/Preis-Mapping
- Primaer-/Alternativszenario-Annotation

## 21. DEF-EP10-004 finale Architekturkorrektur

Status:
- DEF-EP10-004 ist im freigegebenen Scope final korrigiert und technisch verifiziert.

Ausgangsfehler (vor Korrektur):
- Forecast-Nichtverfuegbarkeit wurde im Presenter ueber Exception-Textvergleich gesteuert.
- Fallback startete eine zweite Analyseausfuehrung.
- Dadurch wurden CSV-Import, Swing/Pivot/Elliott-Pipeline und Analyseorchestrierung erneut ausgefuehrt.

Finale Architekturentscheidung:
- Die fachliche Entscheidung "Forecast ja/nein" liegt in der Application-Schicht.
- `AnalysisApplication.run` bleibt streng/unveraendert (bestehende Semantik fuer bestehende Aufrufer).
- Neu: `AnalysisApplication.run_with_optional_forecast` fuehrt Analyse genau einmal aus und erzeugt Forecast nur bei strukturiertem Zustand `AnalysisStage.COMPLETED`.
- Bei nicht forecast-faehigem Analysezustand wird ein semantisch valides leeres `ForecastResult` geliefert (keine kuenstlichen Szenarien/Projektionen/Confidence).
- Der Desktop-Presenter startet keinen zweiten Analysepfad und verwendet keine Exception-Stringvergleiche mehr.

Local-First-Auswirkung:
- CSV wird pro produktivem Lauf genau einmal gelesen.
- Analyse-Pipeline wird pro produktivem Lauf genau einmal ausgefuehrt.
- Forecast wird nur dann ausgefuehrt, wenn fachlich zulaessig.

Geaenderte Produktionsdateien:
- `src/elliottwaver/application/analysis_application.py`
- `src/elliottwaver/interfaces/desktop_tk.py`
- `src/elliottwaver/bootstrap/analysis_application_factory.py`
- `src/elliottwaver/infrastructure/market_data/csv_market_data_provider.py`

Geaenderte Testdateien:
- `tests/unit/application/test_analysis_application.py`
- `tests/unit/interfaces/test_desktop_tk.py`

Zentrale Testnachweise (neu/angepasst):
- Application-Orchestrierung (einmalige Analyse, optionaler Forecast, Reuse derselben AnalysisResponse):
	- `tests/unit/application/test_analysis_application.py`
- Desktop-Regressionsnachweise fuer produktive Aufrufzaehlungen, Fehlerklassifikation, Teilresultatdarstellung und Sequenzwechsel komplett/partial/komplett:
	- `tests/unit/interfaces/test_desktop_tk.py`

Produktiver E2E-Nachweis (ohne gemockte Analyse-/Forecast-Ergebnisse):
- Datensatz: `engineering/testdata/candlestick_patterns_e2e.csv`
	- Calls: CSV-Read=1, Analyze=1, Forecast=0
	- Candles=24, Pivots=9, Swings=8, Candlestick-Patterns=16
	- Elliott-Selektion=0, Analysezustand=`confluence`
	- Forecast verfuegbar=false, Confidence="-", Fibonacci-Projektionen=0
	- S/R-Zonen=9, Chart verfuegbar=true
	- UI-Status="Analyse abgeschlossen - Teilergebnisse verfuegbar"
	- UI-Forecast-Hinweis gesetzt
	- Pattern-Bestaetigungsstatus: nur `unknown`

- Datensatz: `engineering/testdata/swing_e2e_100.csv`
	- Calls: CSV-Read=1, Analyze=1, Forecast=1
	- Candles=100, Pivots=98, Swings=97, Candlestick-Patterns=0
	- Elliott-Selektion=1, Analysezustand=`completed`
	- Forecast verfuegbar=true, Confidence vorhanden, Fibonacci-Projektionen=2
	- S/R-Zonen=98, Chart verfuegbar=true
	- UI-Status="Analyse abgeschlossen"
	- Forecast basiert auf derselben AnalysisResponse-Instanz wie die Analyseausgabe

Negativnachweise:
- DomainError mit Forecast-Text triggert keinen Sonderpfad und bleibt Fehler.
- Unerwartete Forecast-DomainErrors werden nicht als regulaere Nichtverfuegbarkeit verschleiert.
- Ungueltige CSV-Daten bleiben Fehler.

Qualitaets-Gates (finaler Stand dieses Auftrags):
- `python -m ruff format --check .` -> PASS
- `python -m ruff check .` -> PASS
- `python -m mypy src tests` -> PASS (Success: no issues found in 141 source files)
- `python -m pytest` -> 436 passed
- Coverage -> 92.56% (Gate >= 90% bestanden)

Explizite Zusatznachweise:
- EP-09 Regression: `tests/unit/domain/trend_hierarchy/test_trend_hierarchy.py` -> 7 passed
- EP-DEF-10 Regression: selektiver Lauf in `tests/unit/interfaces/test_desktop_tk.py` (produktive Pfade + Call-Counter + Switching) -> 5 passed
- Temporale Kausalitaet: selektive Laeufe in `tests/unit/interfaces/test_chart_tk.py` und `tests/unit/interfaces/test_desktop_tk.py` (temporal/confirmation/semantics) -> 2 passed
- Startup-Test: `tests/unit/test_main_entrypoint.py` -> 1 passed

Schutz- und Integritaetsnachweise:
- Vorher-Baseline: `engineering/_audit/sha256_pre_def_ep10_004_finalfix_20261127_230433.json`
- Nachher-Vergleich: `engineering/_audit/sha256_post_compare_def_ep10_004_finalfix_20261127_230952.json`
- Unveraendert nach SHA: beide Master-Control-Dateien, geschuetzte Tests, `test_market_data.csv`, beide produktiven E2E-Testdaten.

Verbleibende Einschraenkungen:
- Visuelle Abnahme bleibt Product-Owner-/Architektur-Review-aktivitaet.
- Produktive temporale Signalbestaetigung bleibt separat offen.
- Zeit-/Preiskoordinaten und Overlay-Clipping
- Zoom/Pan/Reset mit Overlays
- Mainthread-Sicherheit (bestehende Chart-Mainthread-Guards)
- Governance-/ADR-Konsistenz (automatisierbar)

### Validierung

Gezielte EP-07-Tests:
- `python -m pytest --no-cov tests/unit/application/test_chart_contract.py tests/unit/interfaces/test_chart_tk.py tests/unit/test_governance_contract.py`
	- Ergebnis: 34 passed

Vollstaendige Gates (nach EP-07):
- `python -m ruff format .` -> PASS
- `python -m ruff check .` -> PASS
- `python -m mypy src tests` -> PASS
- `python -m pytest` -> PASS (379 passed)
- Coverage: 92.57% (>=90% Gate bestanden)

### Schutzregeln

Unveraendert belassen:
- `tests/unit/application/test_context_service.py`
- `tests/unit/domain/context/test_elliott_context.py`

### Verbleibende Risiken

- Wellenlabels werden bewusst nur bei eindeutig ableitbarer Struktur gesetzt; bei anderen Strukturen bleiben Labels leer (kein heuristisches Auffuellen).
- Forecast-Szenarien enthalten keine expliziten Zeitpfade; daher werden sie als Szenario-Annotation und nicht als kuenstliche Zukunftslinie gerendert.
- Offenes Release-Gate aus EP-06 bleibt bestehen: echte GitHub-Actions-Matrixausfuehrung ist weiterhin ausstehend.

## 19. EP-06 Abschliessende Release-Verifikation (nur technische Abnahme)

Status:
- Technische Release-Abnahme lokal ausgefuehrt.
- Scope nur EP-06 (Packaging/CI/Constraints), keine EP-07-Arbeiten.

Tatsaechlich ausgefuehrte Pruefungen (lokal):
1. Wheel-Build
- `python -m pip install -c constraints/dev.txt build==1.3.0`
- `python -m build --wheel`
- Ergebnis: PASS (`dist/elliottwaver-0.1.0-py3-none-any.whl` gebaut)

2. Isolierte Installation in neuer venv mit vorgesehenen Constraints
- Neue venv: `.wheel-release-verify-venv`
- Installation: `python -m pip install -c constraints/runtime.txt dist/<wheel>.whl`
- Ergebnis: PASS

3. Artefakt-Sanity
- `python -m pip check` in `.wheel-release-verify-venv`
- Ergebnis: PASS (`No broken requirements found.`)

4. Wheel-Smoke und CLI-Help
- `python engineering/scripts/wheel_smoke.py` in `.wheel-release-verify-venv`
- `python -m elliottwaver --help` in `.wheel-release-verify-venv`
- Ergebnis: PASS
- Nachgewiesener Defekt und Behebung:
	- Vorher unterstuetzte `src/elliottwaver/__main__.py` kein `--help` und startete direkt GUI.
	- Korrektur innerhalb Packaging-Scope: minimale `argparse`-CLI in `src/elliottwaver/__main__.py`.
	- Verhalten jetzt: `--help` beendet erfolgreich ohne GUI-Start.

5. Workflow-Konfiguration (statisch lokal geprueft)
- Geprueft: `.github/workflows/quality.yml`
- Ergebnis:
	- OS-Matrix in `quality` und `wheel-smoke`: `ubuntu-latest`, `windows-latest`
	- constraints-basierte Installation vorhanden
	- Linux headless-Testschritt vorhanden (`xvfb-run -a python -m pytest`)
	- Wheel-Smoke-Schritte vorhanden (build, isolated venv, pip check, smoke script)

6. Constraints-Konsistenz inkl. transitiver Pins (lokal nachgewiesen)
- Runtime-Pins (`constraints/runtime.txt`) gegen installierte Versionen in `.wheel-release-verify-venv` geprueft: alle Pins OK.
- Dev-Pins (`constraints/dev.txt`) gegen installierte Versionen in `.venv` geprueft: alle Pins OK.
- Wichtige Einschraenkung:
	- Nachgewiesen ist Konsistenz fuer diese lokale Windows-Umgebung.
	- Eine vollstaendige plattformuebergreifende Reproduzierbarkeit (insb. Linux-Resolverpfad) ist ohne tatsaechlichen GitHub-Actions-Lauf nicht final bewiesen.

Betroffene Korrekturdatei in dieser Abnahme:
- `src/elliottwaver/__main__.py`

Betroffene Tests (nach Korrektur):
- `python -m pytest --no-cov tests/unit/test_main_entrypoint.py tests/unit/test_packaging_contract.py`
	- Ergebnis: 8 passed

Vollstaendige Quality-Gates (nach Korrektur, lokal):
- `python -m ruff format .` -> PASS
- `python -m ruff check .` -> PASS
- `python -m mypy src tests` -> PASS
- `python -m pytest` -> PASS (371 passed, Coverage 92.66%)

Geschuetzte Dateien unveraendert:
- tests/unit/application/test_context_service.py
- tests/unit/domain/context/test_elliott_context.py

GitHub Actions Ausfuehrungsstatus:
- Lokal nur Konfiguration und technische Ausfuehrbarkeit geprueft.
- Echter Matrix-Lauf in GitHub Actions in dieser Abnahme NICHT ausgefuehrt.

Verbleibende Risiken:
- Finale Linux-Wheel-Smoke-Ausfuehrung bleibt bis zum realen GitHub-Actions-Lauf ausstehend.
- Reproduzierbarkeit ist lokal nachgewiesen, aber nicht als vollstaendig plattformuebergreifend verifiziert auszuweisen.
	- Runtime-Pins: `constraints/runtime.txt`
	- Dev-Pins + Runtime-Verweis: `constraints/dev.txt`
- Installationspfad auf constraints-basiertes `python -m pip` umgestellt:
	- `Makefile`
	- `README.md`

## 22. EP-DEF-10 Abschluss und strategische Master-Control-Aktualisierung

Status:
- Technische und visuelle Abnahme von EP-DEF-10 sind erfolgt.
- Produktive temporale Signalbestaetigung bleibt offen.
- Git-Versionierung bleibt ausstehend bis separate Freigabe.

Freigegebener Dokumentationsscope dieses Auftrags:
- `ELLIOTTWAVER_MASTER_CONTROL.md` (Repository-Root) aktualisiert.
- `engineering/HANDOVER.md` aktualisiert.

Nicht geaendert in diesem Auftrag:
- Keine produktiven Python-Dateien.
- Keine bestehenden Tests.
- Keine Testdaten.
- Keine Audit-Artefakte.
- `.github/ELLIOTTWAVER_MASTER_CONTROL.md` unveraendert (leer belassen).

Ergaenzte strategische Inhalte in der Root-Master-Control:
- EP-DEF-10 Abschlussstatus und Qualitaetsstand (436 Tests, 92.56% Coverage, Ruff/MyPy/E2E PASS).
- Fuehrende Governance-Rolle der Root-Master-Control.
- Verbindliche Architekturprinzipien (Local First, Validation First, Deterministic First, Modular First, Resource Efficient, AI Ready, Cloud Ready, Cloud Optional, Scale on Demand, Human in Control, Safety First).
- Lokaler Entwicklungs-/Betriebsfokus mit Referenzhardware (i3-1215U, ~8 GB RAM, iGPU).
- Strategisches Marktuniversum (~35 Basiswerte, konfigurierbar).
- Multi-Timeframe-Zielarchitektur (bis zu 7 Zeitebenen, bis zu 245 Kombinationen, inkrementell/ressourcenschonend).
- Command-Center-Designreferenz inkl. Profilvorschlaege als Zielbild.
- Strategische Indikator-/Ampellogik und Bewertungsgrenzen.
- Strategische Anwendungsbereiche als Roadmap-Zielbild.
- Lokale Agentenarchitektur als langfristige Zielrichtung.
- Verbindliche fachliche Voraussetzungen vor produktiver Signalnutzung.
- Langfristige Validierungsstrategie (Phasen A-F).

Sicherheits-/Git-Pruefung in diesem Auftrag:
- Branch: `feature/ep10-candlestick-patterns`.
- HEAD: `1a98f88bc8266caac2ba4d729d9747a2194101f4`.
- Git-Index blieb leer.

Hinweis:
- Die Dateizuordnung fuer spaetere Git-Freigabe (EP-DEF-10 vs. geschuetzt/fremd/audit) wurde explizit als separater Abschlussbericht im Chat ausgegeben und nicht als Commit-Vorbereitung ausgefuehrt.

Umsetzung DEF-016 (Formatter-Konsolidierung):
- Black aus Dev-Dependencies entfernt.
- `[tool.black]`-Konfiguration entfernt.
- Ruff bleibt einziger Formatter-Standard.
- Makefile-Targets bereinigt (`format` nur Formatierung, `fix` fuer Lint-Fixes).
- Datei:
	- `pyproject.toml`
	- `Makefile`

Ergaenzte/angepasste Tests:
- `tests/unit/interfaces/test_chart_tk.py`
	- Swing-High-/Low-Mapping
	- Pivot-/Swing-Unterscheidung
	- Chronologische Verbindung
	- Preis-/Zeitkoordinaten
	- Zoom/Pan/Reset mit Overlays
	- Leere/unvollstaendige Overlay-Daten
	- Nicht bestaetigte Pivots (kein Leak als bestaetigte Swings)
	- Mainthread-/Lifecycle-Verhalten der View bleibt abgedeckt
- `tests/unit/test_packaging_contract.py`
	- Constraints-Dateien und Pins
	- Ruff-only Formatter-Standard
	- constraints-basierter Installationspfad

Vollstaendige Gates (EP-05):
- `python -m ruff format --check .` -> PASS
- `python -m ruff check .` -> PASS
- `python -m mypy src tests` -> PASS
- `python -m pytest` -> 368 passed
- Coverage -> `92.65%` (Gate >= 90% bestanden)

Scope-/Schutzkonformitaet:
- Keine Aenderung an ForecastEngine, ProjectionEngine oder Swing-Algorithmus.
- Geschuetzte Dateien unveraendert:
	- `tests/unit/application/test_context_service.py`
	- `tests/unit/domain/context/test_elliott_context.py`

Verbleibendes Risiko:
- Constraints pinnen derzeit die direkten Runtime-/Dev-Werkzeugabhaengigkeiten. Fuer vollstaendige transitive Reproduzierbarkeit waere zusaetzlich ein strikt gepflegtes, voll aufgeloestes Lock-Artefakt erforderlich.

Ein reproduzierbarer Windows-Desktop-Test (EP-05):
1. `python -m pip install -c constraints/dev.txt -e ".[dev]"`
2. `python -m elliottwaver`
3. In der UI `engineering/testdata/swing_e2e_100.csv` laden und `Analyse starten`
4. Erwartung:
	- Candles sichtbar
	- bestaetigte Swing-Marker und Verbindungslinien sichtbar
	- Pivot-Marker separat sichtbar
	- Overlay bleibt bei `+`, `-`, `<`, `>` und `Reset` konsistent

## 21. EP-08 Finale Integrations- und Release-Abnahme

Status:
- Lokale technische Release-Abnahme: PASS
- GitHub-Actions-Matrix-Gate (realer Laufnachweis): OFFEN

### A) End-to-End-Funktionsverifikation (CSV -> Chart)

Ausgefuehrte Verifikationen:
- `python -m pytest --no-cov tests/unit/interfaces/test_desktop_tk.py tests/unit/application/test_chart_contract.py tests/unit/interfaces/test_chart_tk.py`
	- Ergebnis: PASS (66 passed)
- Produktiver Lauf gegen reale CSV (`engineering/testdata/swing_e2e_100.csv`) via `present_csv_analysis(...)`
	- Ergebnis: PASS
	- Nachweiswerte:
		- STATUS: `Analyse abgeschlossen`
		- CANDLES: `100`
		- SWINGS: `97`
		- PIVOTS: `98`
		- WAVES: `1`
		- SCENARIOS: `2`
		- FIB: `2`
		- NO_FAKE_PATHS: `True`

### B) Qualitaets-Gates und Packaging-Abnahme

Voll-Gates (lokal) ausgefuehrt:
- `python -m ruff format .` -> PASS
- `python -m ruff check .` -> PASS
- `python -m mypy src tests` -> PASS (no issues found in 136 source files)
- `python -m pytest` -> PASS (379 passed)
- Coverage: `92.57%` (Gate >= 90% bestanden)

Wheel-/Installationspruefung (lokal) ausgefuehrt:
- `python -m build --wheel` -> PASS (`dist/elliottwaver-0.1.0-py3-none-any.whl`)
- frische venv `.wheel-ep08-verify-venv` erstellt
- `pip install -c constraints/runtime.txt <wheel>` -> PASS
- `pip check` -> PASS (`No broken requirements found.`)
- `python engineering/scripts/wheel_smoke.py` -> PASS
- `python -m elliottwaver --help` -> PASS

### C) GitHub-Actions-Gate (echter Matrix-Lauf)

Befund:
- Remote ist gesetzt (`origin https://github.com/zoran-jpg/ElliottWaver.git`).
- In der aktuellen Umgebung ist `gh` nicht installiert (`CommandNotFoundException`).
- Damit konnte kein belastbarer Nachweis eines echten Linux/Windows-GitHub-Actions-Laufs abgerufen werden.

Bewertung:
- Gate-Status: OFFEN (nicht fehlgeschlagen, aber nicht nachgewiesen).

### D) Scope-/Schutzkonformitaet

- Keine neuen Produktivfeatures im Rahmen EP-08 implementiert.
- Fokus ausschliesslich auf finaler Integration, Gates, Packaging und Nachweislage.
- Geschuetzte Dateien wurden in dieser Abnahme nicht angepasst:
	- `tests/unit/application/test_context_service.py`
	- `tests/unit/domain/context/test_elliott_context.py`

### E) Erforderliche Benutzeraktion (genau eine)

- Fuer die finale Schliessung des offenen CI-Gates ist ein echter GitHub-Actions-Lauf auf dem Ziel-Branch erforderlich.
- Autorisierte Befehle (nur Benutzer ausfuehren):
	- `git add -A`
	- `git commit -m "EP-08 final integration and release acceptance evidence"`
	- `git push origin main`

Danach den Workflow-Lauf in GitHub Actions bestaetigen (Linux/Windows-Matrix gruen) und den Gate-Status in diesem Handover auf `GESCHLOSSEN` setzen.

## 22. EP-08 Letzte Release-Sicherheitspruefung

Status:
- READY fuer kontrolliertes, explizites Staging (kein pauschales Staging).

Rahmen und Methode:
- Master-Control und bestehender Handover erneut gelesen.
- Release-Kandidaten direkt aus Git und Dateisystem ermittelt:
	- tracked modified: `git diff --name-only`
	- untracked: `git ls-files --others --exclude-standard`
- Verbindliche Ausschluesse angewendet:
	- `tests/unit/application/test_context_service.py`
	- `tests/unit/domain/context/test_elliott_context.py`
	- `ELLIOTTWAVER_MASTER_CONTROL.md`
	- `.github/ELLIOTTWAVER_MASTER_CONTROL.md`
	- `test_market_data.csv`

Automatische Allowlist-Pruefung:
- ALLOW_COUNT: 75
- DUP_COUNT: 0
- MISSING_COUNT: 0
- AMBIGUOUS_BASENAME_GROUPS: 9
	- Hinweis: erwartbar durch wiederkehrende Dateinamen wie `__init__.py`; durch vollstaendige Repo-Pfade nicht mehrdeutig.

### Maschinenpruefbare Release-Allowlist (vollstaendige Repo-relative Pfade)

1. `.github/workflows/quality.yml`
2. `.gitignore`
3. `constraints/dev.txt`
4. `constraints/runtime.txt`
5. `docs/adr/0002-desktop-controller-view-separation.md`
6. `docs/adr/0003-desktop-thread-queue-after-model.md`
7. `docs/adr/0004-chart-contract-and-rendering-boundary.md`
8. `docs/adr/0005-dependency-ci-packaging-strategy.md`
9. `docs/project/DECISIONS.md`
10. `docs/project/METRICS.md`
11. `docs/project/MS-015-DESKTOP-MVP.md`
12. `docs/project/ROADMAP.md`
13. `docs/project/status/CURRENT_STATUS.md`
14. `engineering/HANDOVER.md`
15. `engineering/scripts/wheel_smoke.py`
16. `engineering/testdata/swing_e2e_100.csv`
17. `Makefile`
18. `PROJECT_MANIFEST.md`
19. `pyproject.toml`
20. `README.md`
21. `src/elliottwaver/__main__.py`
22. `src/elliottwaver/application/__init__.py`
23. `src/elliottwaver/application/analysis_application.py`
24. `src/elliottwaver/application/chart_contract.py`
25. `src/elliottwaver/application/context_service.py`
26. `src/elliottwaver/application/forecast/__init__.py`
27. `src/elliottwaver/application/forecast/forecast_engine.py`
28. `src/elliottwaver/bootstrap/__init__.py`
29. `src/elliottwaver/bootstrap/analysis_application_factory.py`
30. `src/elliottwaver/domain/forecast/__init__.py`
31. `src/elliottwaver/domain/forecast/forecast_result.py`
32. `src/elliottwaver/domain/forecast/forecast_scenario.py`
33. `src/elliottwaver/domain/forecast/projection_quality.py`
34. `src/elliottwaver/domain/forecast/projection_target.py`
35. `src/elliottwaver/domain/forecast/scenario_type.py`
36. `src/elliottwaver/domain/projection/__init__.py`
37. `src/elliottwaver/domain/projection/fibonacci_level.py`
38. `src/elliottwaver/domain/projection/fibonacci_projection.py`
39. `src/elliottwaver/domain/projection/fibonacci_projection_engine.py`
40. `src/elliottwaver/domain/projection/projection_direction.py`
41. `src/elliottwaver/domain/projection/projection_input.py`
42. `src/elliottwaver/infrastructure/__init__.py`
43. `src/elliottwaver/infrastructure/analysis/__init__.py`
44. `src/elliottwaver/infrastructure/analysis/runtime_ports.py`
45. `src/elliottwaver/infrastructure/analysis/swing_preparation_adapter.py`
46. `src/elliottwaver/infrastructure/market_data/__init__.py`
47. `src/elliottwaver/infrastructure/market_data/csv_market_data_provider.py`
48. `src/elliottwaver/interfaces/__init__.py`
49. `src/elliottwaver/interfaces/analysis.py`
50. `src/elliottwaver/interfaces/chart_tk.py`
51. `src/elliottwaver/interfaces/desktop_tk.py`
52. `tests/unit/application/forecast/test_forecast_engine.py`
53. `tests/unit/application/test_analysis_application.py`
54. `tests/unit/application/test_chart_contract.py`
55. `tests/unit/bootstrap/test_analysis_application_factory.py`
56. `tests/unit/domain/forecast/helpers.py`
57. `tests/unit/domain/forecast/test_forecast_result.py`
58. `tests/unit/domain/forecast/test_forecast_scenario.py`
59. `tests/unit/domain/forecast/test_projection_quality.py`
60. `tests/unit/domain/forecast/test_projection_target.py`
61. `tests/unit/domain/forecast/test_scenario_type.py`
62. `tests/unit/domain/projection/test_fibonacci_level.py`
63. `tests/unit/domain/projection/test_fibonacci_projection.py`
64. `tests/unit/domain/projection/test_fibonacci_projection_engine.py`
65. `tests/unit/domain/projection/test_projection_direction.py`
66. `tests/unit/domain/projection/test_projection_input.py`
67. `tests/unit/infrastructure/analysis/test_runtime_ports.py`
68. `tests/unit/infrastructure/analysis/test_swing_preparation_adapter.py`
69. `tests/unit/infrastructure/market_data/test_csv_market_data_provider.py`
70. `tests/unit/interfaces/test_analysis_exports.py`
71. `tests/unit/interfaces/test_chart_tk.py`
72. `tests/unit/interfaces/test_desktop_tk.py`
73. `tests/unit/test_governance_contract.py`
74. `tests/unit/test_main_entrypoint.py`
75. `tests/unit/test_packaging_contract.py`

### Ausschluss- und Hygienepruefung

Explizit ausgeschlossen:
- `tests/unit/application/test_context_service.py` (geschuetzt)
- `tests/unit/domain/context/test_elliott_context.py` (geschuetzt)
- `ELLIOTTWAVER_MASTER_CONTROL.md` (lokal, nicht freigegeben)
- `.github/ELLIOTTWAVER_MASTER_CONTROL.md` (lokal, nicht freigegeben)
- `test_market_data.csv` (lokale Testdatei)

.gitignore-Pruefung und Nachbesserung:
- Nachgewiesener Bedarf: grosse lokale Wheel-Venvs waren untracked und damit potenziell stagiersensitiv.
- Ergaenzt in `.gitignore`:
	- `.wheel-ep08-verify-venv/`
	- `.wheel-release-verify-venv/`
	- `.wheel-smoke-venv/`
- Verifikation: `WHEEL_VENV_UNTRACKED_COUNT=0`.

### Diff-Pruefung bereits versionierter Dateien

Alle aktuell versionierten geaenderten Dateien vollstaendig geprueft.
Ergebnis:
- Keine ungeklaerten inhaltlichen Fremdartefakte in den Release-Kandidaten erkannt.
- Zwei geschuetzte Testdateien sind lokal geaendert, bleiben aber strikt ausserhalb der Allowlist.
- Umfangreiche Governance-Umschreibungen sind vorhanden, aber inhaltlich konsistent mit EP-Historie und Handover.

### Workflow-/Constraints-Korrektur (EP-08 Safety)

Datei:
- `.github/workflows/quality.yml`

Korrektur:
- Wheel-Smoke installiert das gebaute Wheel nun auch in der isolierten venv mit Runtime-Constraints:
	- Linux: `python -m pip install -c constraints/runtime.txt dist/*.whl`
	- Windows: `python -m pip install -c constraints/runtime.txt <wheel>`

Vereinbarkeit:
- Konsistent mit bestehender Packaging-Strategie und lokalem Release-Verifikationspfad.

### Re-Validierung nach Korrektur

Gezielte Tests:
- `python -m pytest --no-cov tests/unit/test_packaging_contract.py tests/unit/test_main_entrypoint.py`
	- Ergebnis: 8 passed

Vollstaendige Quality-Gates:
- `python -m ruff format .` -> PASS
- `python -m ruff check .` -> PASS
- `python -m mypy src tests` -> PASS
- `python -m pytest` -> PASS (379 passed)
- Coverage: 92.57%

### Branch-/Remote-Risiko-Pruefung (ohne Branch-Wechsel)

- Branch: `main`
- HEAD: `0eb2795e1134e4bda4f5fe414a624b7e17efd27a`
- Upstream: `origin/main`
- Remote gesetzt: `origin https://github.com/zoran-jpg/ElliottWaver.git`

Erkannte Risiken:
- Working tree weiterhin bewusst dirty; daher nur streng explizites Staging gegen die obige 75-Pfade-Allowlist.
- Zeilenendungswarnungen (CRLF/LF) koennen Diffs aufblaehen, sind aber durch dateigenaue Allowlist beherrschbar.
- GitHub-Actions-Live-Gate weiterhin OFFEN bis zu einem echten gehosteten Matrix-Lauf.

## 23. EP-08 Kontrollierter lokaler Release-Commit

Commit-Status:
- Lokaler Commit erstellt auf Branch `release/ep08-preflight`.
- Commit: `2a5ab9b`
- Nachricht: `EP-08 validated integration and release candidate`
- Umfang: 75 Dateien, exakt gemaess Allowlist.

Index-Sicherheitspruefung vor Commit:
- Staged-Pfade gegen Allowlist: exakt (keine fehlenden, keine zusaetzlichen).
- Geschuetzte Tests ausgeschlossen:
	- `tests/unit/application/test_context_service.py`
	- `tests/unit/domain/context/test_elliott_context.py`
- Master-Control-Kopien ausgeschlossen:
	- `ELLIOTTWAVER_MASTER_CONTROL.md`
	- `.github/ELLIOTTWAVER_MASTER_CONTROL.md`
- Lokale Artefakte ausgeschlossen (u. a. Wheel-Venvs, lokale Testdatei).

Hinweis:
- Diese Handover-Notiz wurde nach dem Commit erstellt und ist bewusst nicht als zweiter Commit aufgenommen.

## 24. EP-09 Abschluss - Support/Resistance im bestehenden Chart

Status:
- Fachliche EP-09-Abnahme (technisch): PASS
- Offene visuelle Product-Owner-Abnahme unter Windows: AUSSTEHEND

Implementierte Funktionen:
- Deterministische Support-/Resistance-Zonenableitung aus bestaetigten Swing-Pivots.
- Mapping der Zonen in den unveraenderlichen Chart-Contract je Timeframe.
- Darstellung als dezente horizontalen Zonenbaender im bestehenden Candlestick-Chart.
- Ein-/Ausblendung ueber Checkbox `S/R Zonen` (Standardzustand: EIN).
- Kompatibilitaet mit bestehenden Navigationen (`+`, `-`, `<`, `>`, `Reset`).
- Bestehende Elliott-Wellen-, Fibonacci- und Szenario-Overlays bleiben aktiv.

Verwendete Berechnungsregeln:
- Eingaben fuer Zonen stammen ausschliesslich aus `prepared_swings` (damit nur bestaetigte Pivot-Punkte).
- Keine Lookahead-Nutzung ueber unbestaetigte Rohkerzen-Pivots; nicht in Swings enthaltene Pivots werden nicht verarbeitet.
- Support-Band: von Kerzentief bis Kerzenkoerper-Unterkante (`min(open, close)`).
- Resistance-Band: von Kerzenkoerper-Oberkante (`max(open, close)`) bis Kerzenhoch.
- Deduplizierung ueber Pivot-ID (ein Pivot erzeugt maximal einen Rohzonenbeitrag).
- Zusammenfassen benachbarter/ueberlappender Zonen pro Typ deterministisch (sortierte Aggregation, stabile Pivot-ID-Menge).
- Renderer positioniert Zonen ueber dieselbe Preis-Mapping-Funktion wie Candles/Overlays (konsistente Preisachse).

Geaenderte EP-09-Dateien:
- `src/elliottwaver/application/support_resistance.py`
- `src/elliottwaver/application/chart_contract.py`
- `src/elliottwaver/interfaces/chart_tk.py`
- `tests/unit/application/test_support_resistance.py`
- `tests/unit/application/test_chart_contract.py`
- `tests/unit/interfaces/test_chart_tk.py`
- `tests/unit/interfaces/test_desktop_tk.py`

Testergebnisse (aktueller Lauf):
- `python -m ruff format --check .` -> PASS (`139 files already formatted`)
- `python -m ruff check .` -> PASS
- `python -m mypy src tests` -> PASS (`no issues found in 138 source files`)
- `python -m pytest` -> PASS (`386 passed`)
- Coverage: `92.58%` (Gate >= 90% bestanden)

Separater Integrationstest mit Engineering-Fixture:
- Kommando: `present_csv_analysis(Path("engineering/testdata/swing_e2e_100.csv"))` (direkter Aufruf)
- Ergebnis:
	- `STATUS=Analyse abgeschlossen`
	- `ERROR=None`
	- `HAS_CHART=True`
	- `TIMEFRAME=1h`
	- `CANDLES=100`
	- `SWINGS=97`
	- `ZONES=98`
	- `ZONE_TYPES=['resistance', 'support']`

Bekannte Einschraenkungen:
- Das Domain-Modell fuehrt derzeit keinen expliziten `confirmed_at`-Zeitstempel pro Pivot/Swing; gearbeitet wird mit bestaetigten Swing-Pivots und deren Extremzeitstempel (`pivot.timestamp`).
- Die technische No-Lookahead-Bedingung ist ueber die bestaetigte Swing-Eingabe erfuellt, die gesonderte Darstellung eines expliziten Bestaetigungszeitpunkts ist jedoch nicht Teil des aktuellen Modells.

Offene visuelle Windows-Abnahme (Product Owner):
1. `python -m elliottwaver` starten.
2. Datei `engineering/testdata/swing_e2e_100.csv` laden und Analyse starten.
3. Pruefen: Candles, Swing-/Pivot-Overlays, Elliott/Fibonacci/Szenarien weiterhin sichtbar.
4. Checkbox `S/R Zonen` EIN/AUS schalten und pruefen, dass nur Zonen ein-/ausgeblendet werden.
5. Mit `+`, `-`, `<`, `>`, `Reset` interagieren und pruefen, dass Zonen/Overlays konsistent bleiben.
6. Ergebnis als visuell akzeptiert oder nachzubessern protokollieren.

### 24.1 EP-09 Visual Fix (Lesbarkeit) - 2026-11-21

Ursachenanalyse (vor Korrektur):
- Auf `engineering/testdata/swing_e2e_100.csv` entstanden `98` Zonen (`49` Support, `49` Resistance), weil praktisch jeder bestaetigte Pivot genau einen Zonenkandidaten erzeugte.
- Die grossflaechige Ueberdeckung entstand primaer durch Rendering (alle Zonen gleichzeitig, horizontale Vollbreite) und Zeichenreihenfolge: Zonen wurden ueber Candles gezeichnet.
- Beschriftung wurde fuer jede sichtbare Zone gezeichnet, was bei vielen Zonen zu starker visueller Verdichtung fuehrte.
- In dieser Fixture war Zonenbreite je Kandidat klein (`width=1`), d. h. die Hauptursache war nicht ein einzelner ueberbreiter Merge, sondern die gleichzeitige Anzeige vieler Bander.

Umgesetzte Korrekturen:
- Fachliche Kandidaten bleiben vollstaendig erhalten (keine Datenverluste im Chart-Contract).
- Anzeigeauswahl getrennt von Fachkandidaten:
	- Relevanzranking aus Beruehrungen (`touch_count`), Aktualitaet (`last_timestamp`) und Preisnaehe zum aktuellen Viewport-Rechtsrandpreis.
	- Sichtbarkeitslimit: maximal `5` Support + `5` Resistance gleichzeitig.
	- Zonen mit `last_timestamp` nach dem aktuellen Viewport-Rechtsrand werden im Viewport nicht angezeigt.
- Aggregation gehaertet:
	- Merge nur bei Ueberlappung und nur solange eine konfigurierbare Maximalbreite nicht ueberschritten wird (`DEFAULT_MAX_ZONE_WIDTH_RATIO=0.03`).
	- Dadurch wird transitive Ausweitung zu ueberbreiten Sammelzonen begrenzt.
- Rendering verbessert:
	- Zonen werden als Hintergrundband vor Candles gezeichnet.
	- Support in dezentem Tuerkis, Resistance in dezentem Orange, hohe Transparenzwirkung via `stipple`.
	- Kurzlabel auf `SUP xN`/`RES xN` reduziert.
	- Label-Drosselung bei engem vertikalem Abstand oder zu niedriger Bandhoehe.

Geaenderte Dateien (Visual Fix):
- `src/elliottwaver/application/support_resistance.py`
- `src/elliottwaver/interfaces/chart_tk.py`
- `tests/unit/application/test_support_resistance.py`
- `tests/unit/interfaces/test_chart_tk.py`

## 25. EP-10 Fortschritt - Candlestick Patterns (ohne Commit/Push)

Status:
- Technische Umsetzung im aktuellen Scope: PASS
- Git-Aktion: kein Commit, kein Push (gem. Vorgabe)

Umgesetzte Punkte:
- Neuer Domain-Baustein fuer deterministische Kerzenformations-Erkennung:
	- `src/elliottwaver/domain/patterns/candlestick_patterns.py`
	- `src/elliottwaver/domain/patterns/__init__.py`
- Mapping in den Chart-Vertrag erweitert um immutable Pattern-Payloads:
	- `src/elliottwaver/application/chart_contract.py`
	- `src/elliottwaver/application/__init__.py`
- Chart-Renderer erweitert um Pattern-Marker und UI-Toggle `Kerzenformationen` (default EIN):
	- `src/elliottwaver/interfaces/chart_tk.py`

Tests (neu/erweitert):
- Neu: `tests/unit/domain/patterns/test_candlestick_patterns.py`
- Erweitert: `tests/unit/application/test_chart_contract.py`
- Erweitert: `tests/unit/interfaces/test_chart_tk.py`

Validierung (vollstaendige Gates):
- `python -m ruff format .` -> PASS
- `python -m ruff check .` -> PASS
- `python -m mypy src tests` -> PASS
- `python -m pytest` -> PASS (`403 passed`)
- Coverage: `91.73%` (Gate >= 90% bestanden)

Explizit nicht geaendert (geschuetzt):
- `tests/unit/application/test_context_service.py`
- `tests/unit/domain/context/test_elliott_context.py`

## 25.1 EP-10 Qualitaetsgate und Architektur-Nachpruefung (2026-11-27)

Scope der Nachpruefung:
- Vollstaendiger Soll-Ist-Abgleich der implementierten Candlestick-Patterns.
- Git-Sicherheitsnachweis ohne Git-Korrekturen.
- Erweiterte Formations-Tests (positiv/negativ/grenzwertig).
- Neue E2E-Fixture fuer deterministische Pattern-Erkennung.
- Engulfing-Dochtgrenze (30%) in der eigentlichen Erkennungsregel nachgezogen.

Nachgezogene/aktualisierte Dateien:
- `engineering/testdata/candlestick_patterns_e2e.csv`
- `tests/unit/domain/patterns/test_candlestick_patterns.py`
- `tests/unit/interfaces/test_chart_tk.py`
- `tests/unit/interfaces/test_desktop_tk.py`

Explizite Nachpruefungen:
- EP-10 Fixture-Integration:
	- `tests/unit/interfaces/test_desktop_tk.py::test_candlestick_fixture_detects_expected_pattern_families`
	- Ergebnis: PASS
- Prefix-Invariance auf Fixture:
	- `tests/unit/interfaces/test_desktop_tk.py::test_candlestick_pattern_fixture_is_prefix_invariant`
	- Ergebnis: PASS
- EP-09 Regression (S/R auf vorhandener Engineering-Fixture):
	- `tests/unit/interfaces/test_desktop_tk.py::test_present_csv_analysis_populates_support_resistance_zones_from_engineering_fixture`
	- Ergebnis: PASS

Qualitaetsgates (aktueller Lauf):
- `python -m ruff format .` -> PASS
- `python -m ruff check .` -> PASS
- `python -m mypy src tests` -> PASS
- `python -m pytest` -> PASS (`419 passed`)
- Coverage: `92.40%` (Gate >= 90% bestanden)

Startup-Check:
- `python -m elliottwaver` gestartet.
- Ergebnis: Prozess startet ohne unmittelbaren Traceback/Abbruch.
- Hinweis: UI-Prozess bleibt erwartungsgemaess aktiv bis manuell beendet.

Status (nur fuer diese Nachpruefung):
- Technische Abnahme: BLOCKED (offene EP-10-Anforderungsabweichungen dokumentiert, z. B. fehlender bestaetigter Zeitstempel und fehlender nachgewiesener Piano-Filter im Domain-Config-Vertrag)
- Visuelle Abnahme: OFFEN
- Git-Versionierung: NICHT FREIGEGEBEN
- `tests/unit/interfaces/test_desktop_tk.py`

Zusatztests (neu/erweitert):
- Sichtbarkeitslimit `5+5` fuer Zonen im Render-Modell.
- Deterministische Relevanzauswahl.
- Kandidaten bleiben im Contract unverkuerzt erhalten (Fixture-Test `>10` Zonen).
- Hintergrund-Zeichenreihenfolge (Zonen vor Candles).
- Begrenzung transitive Merge-Ausdehnung.
- Bestehende Toggle-/Zoom-/Pan-/Reset-Tests weiterhin grün.

Validierung nach Korrektur:
- `python -m ruff format --check .` -> PASS
- `python -m ruff check .` -> PASS
- `python -m mypy src tests` -> PASS (`no issues found in 138 source files`)
- `python -m pytest` -> PASS (`391 passed`)
- Coverage: `92.61%` (Gate >= 90% bestanden)

Expliziter Integrationsnachweis (`engineering/testdata/swing_e2e_100.csv`):
- `STATUS=Analyse abgeschlossen`
- `ERROR=None`
- `HAS_CHART=True`
- `CANDLES=100`, `SWINGS=97`
- Fachkandidaten: `49` Support + `49` Resistance (`98` total)
- Sichtbare Zonen im aktuellen Viewport: `5` Support + `5` Resistance (`10` total)

Einschraenkung Bestaetigungszeitpunkt:
- Das aktuelle Modell enthaelt fuer Pivots/Swings keinen expliziten `confirmed_at`-Zeitstempel.
- Vorhanden sind Extremzeitstempel (`pivot.timestamp`) und durch den Adapter nur bereits bestaetigte Swings.
- Damit kann historische Erstsichtbarkeit streng nach Bestaetigungszeitpunkt derzeit nicht vollstaendig modelliert werden, ohne Datenvertragserweiterung.
- Saubere spaetere Erweiterung: `confirmed_at` in Pivot/Swing (oder separate Confirmation-Metadaten) aufnehmen, in ChartContract durchreichen und Zonensichtbarkeit pro Viewport daran binden.

### EP-09 Final Visual Polish

Status:
- Umsetzung abgeschlossen und technisch verifiziert.

Umsetzungsschwerpunkte:
- Sichtbarkeitsregel auf Standard `3+3` (Support/Resistance) umgestellt.
- Technische Obergrenze je Richtung als konfigurierbarer Parameter eingefuehrt, hart auf `max 5` begrenzt.
- Kandidatenmenge bleibt unveraendert; Begrenzung wirkt nur auf die Anzeigeauswahl im Renderer.
- Deterministische Relevanzselektion beibehalten (touch_count, recency, proximity) ohne Zukunftsdaten.
- Visuelle Entflechtung ergaenzt:
	- Stark ueberlappende oder auf der Preisachse praktisch nicht unterscheidbare Zonen desselben Typs werden nicht gleichzeitig angezeigt.
	- Bei Kollisionen bleibt die hoeherrangige Zone erhalten.
- Label-Interferenz reduziert:
	- Zonenlabels standardmaessig deaktiviert (keine In-Zone-Textkollisionen im Normalfall).
	- Optionales Labeling bleibt technisch verfuegbar.
- Zeichenreihenfolge unveraendert korrekt: Zonen im Hintergrund, Candles/Overlays darueber.

Betroffene Dateien:
- `src/elliottwaver/interfaces/chart_tk.py`
- `tests/unit/interfaces/test_chart_tk.py`

Ergaenzte/angepasste Testnachweise:
- Default-Limit `3+3` fuer sichtbare Zonen.
- Konfigurierbarkeit bis `5+5` (mit harter Obergrenze).
- Weniger als `3` sichtbar, wenn Distinktheit fehlt (starke Ueberlappung).
- Keine gleichzeitige Anzeige stark ueberlappender gleichartiger Zonen.
- Deterministische Auswahl bei identischem Input.
- Kandidaten bleiben unverkuerzt (Display-Limit wirkt nicht auf die fachliche Menge).
- Zoom/Pan/Reset und Checkbox-Verhalten bleiben stabil.
- Keine S/R-Label-Interferenz im Default.

Validierung (vollstaendige Gates):
- `python -m ruff format .` -> PASS
- `python -m ruff check .` -> PASS
- `python -m mypy src tests` -> PASS
- `python -m pytest` -> PASS (`395 passed`)
- Coverage: `92.60%` (Gate >= 90% bestanden)

Expliziter Integrationsnachweis (`engineering/testdata/swing_e2e_100.csv`):
- `python -m pytest --no-cov tests/unit/interfaces/test_desktop_tk.py -k "populates_support_resistance_zones_from_engineering_fixture"`
- Ergebnis: `1 passed` (Fixture-basierte Pipeline ueber `present_csv_analysis` erfolgreich)

Startup-Check:
- `python -m elliottwaver` gestartet.
- Kein unmittelbarer Traceback beim Start beobachtet; Prozess laeuft erwartungsgemaess in der UI-Hauptschleife und wurde fuer die Session-Beendigung kontrolliert beendet.

### 25.2 EP-10 Architekturkorrektur (DEF-EP10-001/002/003) und finales Quality Gate - 2026-11-27

Status:
- Technische Abnahme: BLOCKED
- Visuelle Abnahme: OFFEN
- Git-Versionierung: NICHT FREIGEGEBEN

Git-Sicherheitspruefung:
- Branch: `feature/ep10-candlestick-patterns` (erwartet)
- HEAD: `1a98f88bc8266caac2ba4d729d9747a2194101f4` (erwartet)
- Git-Index: leer (keine staged Aenderungen)

Architekturentscheidung DEF-EP10-001 (Zeitstempelsemantik):
- Umgesetzt wurde eine kleinste rueckwaertskompatible Erweiterung nur im Pattern-Domain-Modul.
- Geometrische Erkennung bleibt unveraendert und deterministisch.
- Zeitliche Bestaetigung ist nun optional und explizit uebergebbar ueber `CandleTemporalSemantics` + `as_of`.
- Ohne hinreichende Semantik bleibt der Status explizit `unknown`.
- `confirmed_at` wird nur gesetzt, wenn alle benoetigten Kerzen geschlossen und verfuegbar sind und `as_of` den maximalen `available_at`-Zeitpunkt erreicht.
- Keine Ableitung von `closed_at` aus Kerzenabstaenden.
- Keine Nutzung der Systemuhr in der historischen Bestaetigungslogik.

Umgesetzte Dateien (dieser Auftrag):
- `src/elliottwaver/domain/patterns/candlestick_patterns.py`
- `src/elliottwaver/domain/patterns/__init__.py`
- `tests/unit/domain/patterns/test_candlestick_patterns.py`
- `tests/unit/interfaces/test_desktop_tk.py`
- `engineering/testdata/candlestick_patterns_temporal_semantics.csv`

DEF-EP10-001 Nachweise:
- Bekannte Kerzenschlusszeit / bekannte Verfuegbarkeit -> `confirmed`
- Unbekannte Semantik -> `unknown`
- Offene Kerze (`is_closed=false`) -> `pending`
- Mehrkerzenformation -> Bestaetigung erst nach spaetestem `available_at`
- Historische As-of-Analyse -> `pending` vor, `confirmed` ab Verfuegbarkeit
- Zeitzonenvalidierung -> nur UTC akzeptiert
- Datenluecken und unregelmaessige Abstaende -> keine impliziten Zeitableitungen, geometrische Erkennung bleibt stabil
- Prefix-Invariance bleibt erhalten

DEF-EP10-002 (Piano-Filter):
- Fachlich wirksamer Domain-Filter: `min_engulfing_body_factor = 1.20` inkl. Grenzfalltests (positiv/negativ/boundary).
- Der vorhandene UI-Pixelabstandsfilter ist rein visuelle Marker-Dichtebegrenzung und kein Trading-/Domain-Filter.
- Domain-Klassifikation bleibt von UI-Renderlogik getrennt.
- Bewertung: Kein zusaetzlicher redundanter Domain-Filter eingefuehrt.

DEF-EP10-003 (Governance-Kollision, read-only geprueft):
- `docs/project/engineering-packages/EP-010-MULTI-TIMEFRAME-CONFLUENCE-ENGINE.md` belegt EP-010 als Confluence-Paket.
- Die aktuelle Candlestick-Implementierung wird als EP-10-Nachpruefung gefuehrt und kollidiert damit in der Nummernlogik.
- `ELLIOTTWAVER_MASTER_CONTROL.md` (Projektstamm) ist inhaltlich befuellt.
- `.github/ELLIOTTWAVER_MASTER_CONTROL.md` ist leer (0 Bytes).
- Empfehlung:
	- Eine einzige fuehrende Master-Control-Datei festlegen (Projektstamm bevorzugt, da inhaltlich gefuellt).
	- Kuenftige Paketnummern eindeutig trennen (z. B. `EP-CANDLE-010A` oder neues eindeutiges EP-Label), statt bestehende EP-010-Zuordnung doppelt zu belegen.

Quality-Gates (vollstaendiger Lauf):
- `python -m ruff format --check .` -> PASS
- `python -m ruff check .` -> PASS
- `python -m mypy src tests` -> PASS (`no issues found in 141 source files`)
- `python -m pytest` -> PASS (`426 passed`)
- Coverage: `92.32%` (Gate >= 90% bestanden)

Gezielte Nachweise:
- EP-10-E2E + Prefix + As-of/Temporal:
	- `python -m pytest --no-cov tests/unit/interfaces/test_desktop_tk.py -k "candlestick_fixture_detects_expected_pattern_families or temporal_semantics_fixture_supports_as_of_confirmation_and_unknown_states or candlestick_pattern_fixture_is_prefix_invariant"` -> PASS
- EP-09-Regression:
	- `python -m pytest --no-cov tests/unit/interfaces/test_desktop_tk.py -k "present_csv_analysis_populates_support_resistance_zones_from_engineering_fixture"` -> PASS
- Zeitstempel-/Kausalitaetstests:
	- `python -m pytest --no-cov tests/unit/domain/patterns/test_candlestick_patterns.py -k "temporal_semantics or prefix_invariant or sets_unknown_confirmation_timestamp_semantics"` -> PASS

Startup-Test:
- `python -m elliottwaver` gestartet.
- Ergebnis: kein unmittelbarer Traceback; Prozess bleibt erwartungsgemaess aktiv bis manueller Beendigung.

SHA256-Schutzpruefung:
- Pre-Baseline: `engineering/_audit/sha256_pre.json`
- Post-Vergleich: `engineering/_audit/sha256_post_compare.json`
- Unveraendert bestaetigt (u. a. geschuetzt):
	- `tests/unit/application/test_context_service.py`
	- `tests/unit/domain/context/test_elliott_context.py`
	- `ELLIOTTWAVER_MASTER_CONTROL.md`
	- `.github/ELLIOTTWAVER_MASTER_CONTROL.md`
	- `test_market_data.csv`

Restrisiken / verbleibende Einschraenkungen:
- Die neue Zeitsemantik-Bestaetigung ist derzeit im Pattern-Domain-Modul und in Tests nachgewiesen; eine durchgaengige Datenvertragsweitergabe ueber alle Adapter bleibt ein separater Architektur-/Backlog-Schritt.
- Governance-Kollision (EP-010-Zuordnung) ist dokumentiert, aber ohne separate Freigabe bewusst nicht strukturell geaendert.

### 25.3 EP-DEF-10 finale Freigabevorbereitung (2026-11-27)

Architekturentscheidungen (uebernommen):
- Das aktuelle Candlestick-Paket wird logisch als `EP-DEF-10` gefuehrt.
- Das urspruengliche `EP-010` bleibt unveraendert dem Paket `EP-010-MULTI-TIMEFRAME-CONFLUENCE-ENGINE` zugeordnet.
- `ELLIOTTWAVER_MASTER_CONTROL.md` im Projektstamm ist kuenftig fuehrendes Steuerungsdokument.
- `.github/ELLIOTTWAVER_MASTER_CONTROL.md` bleibt unveraendert.
- Geometrische Candlestick-Erkennung ist fuer den vereinbarten Analyseumfang akzeptiert.
- Optionale temporale Domain-Architektur bleibt erhalten.
- Produktive Zeitintegration ist als spaeteres verpflichtendes Engineering-Paket zurueckgestellt.

Einzige zulaessige funktionale Ergaenzung (umgesetzt):
- UI-Hinweis bei aktivierten Kerzenformationen zur zeitlichen Aussagekraft ergaenzt:
	- unknown: `Kerzenformationen: geometrische Erkennung - zeitliche Bestaetigung nicht verfuegbar.`
	- pending: `Kerzenformationen: geometrische Erkennung - zeitliche Bestaetigung ausstehend.`
	- confirmed: `Kerzenformationen: geometrische Erkennung - zeitlich bestaetigt.`
	- gemischt: `Kerzenformationen: geometrische Erkennung - zeitlicher Status gemischt.`

Betroffene Dateien (dieser Schritt):
- `src/elliottwaver/interfaces/chart_tk.py`
- `tests/unit/interfaces/test_chart_tk.py`

Gezielter Testnachweis Statusdarstellung:
- `tests/unit/interfaces/test_chart_tk.py::test_chart_view_displays_candlestick_temporal_status_hint`

Zurueckgestellte Pflichtanforderungen vor produktiver signalbasierter Konfluenzbewertung oder historischer Strategievalidierung:
- Produktive Integration der Candle-Zeitsemantik.
- Explizite As-of-Auswertung.
- Kausale Verfuegbarkeit saemtlicher verwendeter Kontextkerzen.
- Kausale Bestaetigung und Verfuegbarkeit der Support/Resistance-Zonen.
- Keine Nutzung unbekannter oder zukuenftiger Informationen als bestaetigte Handelssignale.

Hinweis Master-Control-Strategietext:
- Der bereits erstellte strategische Textvorschlag ist fuer spaetere Uebernahme vorgemerkt; in diesem Schritt wurden keine Master-Control-Dateien geaendert.

## 26. EP-DEF-11 Architekturabnahme und Abschlussvorbereitung (2026-11-28)

Status:
- Fachliche Architekturabnahme fuer EP-DEF-11 ist erteilt.
- DEF-EP11-001 bis DEF-EP11-004 sind fachlich abgeschlossen.
- GitHub-Integration ist weiterhin nicht freigegeben.

### 26.1 Zielsetzung EP-DEF-11

Ziel war die Einfuehrung einer gemeinsamen, unveraenderlichen temporalen Semantik fuer Candle-Verfuegbarkeit in der Domain, inkl. klarer Statussemantik (unknown/pending/confirmed), validierter Zeitinvarianten und reproduzierbarer As-of-Bewertung.

### 26.2 Technisches Ergebnis

Gemeinsames Domain-VO:
- `src/elliottwaver/domain/market/candle_availability.py`

Temporale Invarianten:
- `opened_at` muss UTC-aware sein.
- `closed_at` (falls bekannt) muss UTC-aware sein und strikt nach `opened_at` liegen.
- `available_at` (falls bekannt) muss UTC-aware sein.
- `available_at` darf nicht vor `opened_at` liegen.
- Falls `closed_at` bekannt ist, darf `available_at` nicht vor `closed_at` liegen.
- `is_closed=False` bei bekanntem `closed_at` ist unzulaessig.

Statussemantik:
- `pending` bei laufender Candle (`is_closed=False`).
- `unknown` bei fehlenden erforderlichen Metadaten oder `as_of=None` in nicht-laufenden Pfaden.
- `confirmed` nur bei vollstaendigen Metadaten und `available_at <= as_of`.

Strikte as_of-Validierung:
- Jeder uebergebene `as_of`-Wert ungleich `None` wird vor jeglicher Statusrueckgabe auf UTC-Konformitaet geprueft.
- Ungueltiges `as_of` fuehrt in allen relevanten Pfaden zu `DomainError`.

Rueckwaertskompatibilitaet und Wiederverwendung:
- Pattern-Engine nutzt die gemeinsame temporale Semantik.
- Rueckwaertskompatible Imports fuer bestehende Pattern-Aufrufer bleiben erhalten.

### 26.3 Behebung der vier Defekte

- DEF-EP11-001: Invariante `available_at >= opened_at` durchgesetzt.
- DEF-EP11-002: Regressionstest fuer `available_at == closed_at` ergaenzt.
- DEF-EP11-003: Regressionstest fuer laufende Candle mit bekanntem `available_at` ergaenzt (bleibt `pending`).
- DEF-EP11-004: Globale strikte `as_of`-Validierung umgesetzt; fruehe Rueckgabepfade validieren `as_of` ebenfalls.

### 26.4 Quality-Gate-Ergebnisse (abgenommener Stand)

- `python -m ruff format --check .` -> PASS (144 Dateien bereits formatiert)
- `python -m ruff check .` -> PASS
- `python -m mypy src tests` -> PASS (143 Dateien)
- `python -m pytest --no-cov <temporale/pattern regression>` -> PASS (53 passed)
- `python -m pytest tests/unit/test_main_entrypoint.py --no-cov` -> PASS
- `python -m pytest` -> PASS (466 passed)
- Coverage: 92.73% (Gate >= 90% bestanden)
- Grenzfallmatrix A-L: 12/12 PASS
- Gemeldete Exit-Codes: 0

### 26.5 Verbleibende fachliche Grenzen

Verbindliche Klarstellung:
- Die gemeinsame temporale Semantik allein garantiert noch keine durchgaengige Lookahead-Freiheit der produktiven Analysekette.
- Die produktive Integration in CSV-Provider, Pivot-/Swing-Erkennung, Support/Resistance und nachgelagerte Analysekomponenten bleibt Gegenstand weiterer explizit freizugebender Engineering Packages.
- Es wird keine produktive Signal- oder Strategievalidierung aus EP-DEF-11 allein abgeleitet.

### 26.6 Projektcontrolling (gemessene Copilot-Korrekturzeiten)

- DEF-EP11-001 bis DEF-EP11-003:
	- Soll: 15-30 Minuten
	- Ist: 98 Sekunden
- DEF-EP11-004:
	- Soll: 5-10 Minuten
	- Ist: 80 Sekunden
- Gesamt:
	- Soll: 20-40 Minuten
	- Ist: 178 Sekunden
	- Abweichung gegen Soll-Mittelwert: -90.1%

Hinweis:
- Diese Zeiten sind ausschliesslich gemessene Copilot-Korrekturzeiten und nicht der vollstaendige Projektaufwand.
- Roadmap V3.0 bleibt unveraendert.

### 26.7 EP-DEF-11 Datei-Allowlist fuer isolierte Git-Integration

Tatsaechlich zu EP-DEF-11 gehoerende Dateien:
- `src/elliottwaver/domain/market/candle_availability.py`
- `src/elliottwaver/domain/market/__init__.py`
- `src/elliottwaver/domain/patterns/candlestick_patterns.py`
- `src/elliottwaver/domain/patterns/__init__.py`
- `tests/unit/domain/market/test_candle_availability.py`
- `tests/unit/domain/patterns/test_candlestick_patterns.py`

### 26.8 Auszuschliessende lokale Dateien

Explizit auszuschliessen:
- `tests/unit/application/test_context_service.py`
- `tests/unit/domain/context/test_elliott_context.py`
- `.github/ELLIOTTWAVER_MASTER_CONTROL.md`
- `test_market_data.csv`
- alle Dateien unter `engineering/_audit/`
- alle paketfremden lokalen Dateien ausserhalb der EP-DEF-11-Allowlist
