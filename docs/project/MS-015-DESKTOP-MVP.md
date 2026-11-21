# MS-015 Desktop MVP

## Funktionsumfang

- Desktop-Oberflaeche auf Basis von tkinter/ttk.
- CSV-Datei per Dateidialog auswaehlbar.
- Gewaehlter Dateipfad wird im UI angezeigt.
- Analyse ueber AnalysisApplication ausfuehrbar.
- Statusanzeige fuer Bereit, Laufend, Fehlgeschlagen, Abgeschlossen.
- Ergebnisdarstellung mit Stage, Symbol, Timeframes und Issues.
- Forecast-Darstellung inklusive Scenario- und Reasoning-Text.
- Confidence-Anzeige, sofern Forecast verfuegbar.
- Fibonacci-Projektionen in separatem Bereich.
- Verstaendliche Fehlermeldungen fuer typische Eingabe- und Pipelinefehler.

## CSV-Eingabeformat

Erforderliche Header-Spalten:

- symbol
- timeframe
- opened_at
- open
- high
- low
- close
- volume

Regeln:

- Die Datei muss mindestens eine Datenzeile enthalten.
- Alle Zeilen muessen dasselbe Symbol enthalten.
- Alle Zeilen muessen dasselbe Timeframe enthalten.
- opened_at muss UTC sein (z. B. 2026-07-21T00:00:00Z).

## Offizieller Startweg (Windows)

Installation im Projektverzeichnis:

```powershell
python.exe -m pip install -e .
```

Start im Projektverzeichnis:

```powershell
python.exe -m elliottwaver
```

Optionaler lokaler Entwicklerhinweis:

- Ein projektlokaler Interpreterpfad kann lokal verwendet werden, ist aber
	nicht der offizielle Produktstartweg.

## Bekannte Einschraenkungen

- In der Agent-Umgebung steht typischerweise kein GUI-Display zur Verfuegung.
- Der MVP nutzt aktuell einen Noop-Swing-Preparation-Port fuer den UI-Flow.
- Dadurch kann die Analyse fuer manche CSV-Eingaenge kein abgeschlossenes Forecast-Ergebnis liefern.

## Manuelle Smoke-Test-Schritte

1. UI starten (Befehl oben).
2. CSV mit gueltigem Header auswaehlen.
3. Pruefen, dass der Dateipfad im UI erscheint.
4. Analyse starten.
5. Pruefen, dass Status auf Laufend und danach auf Fehlgeschlagen oder Abgeschlossen wechselt.
6. Bei Fehler: Pruefen, dass eine verstaendliche Meldung angezeigt wird.
7. Bei Erfolg: Pruefen, dass Ergebnis-, Forecast-, Confidence- und Projektionstexte gefuellt sind.
8. Erneut Analyse starten (gleiche oder andere Datei), um Wiederholbarkeit zu bestaetigen.
