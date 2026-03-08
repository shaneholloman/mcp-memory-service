# Changelog Housekeeping Prompt

Use this prompt in a Claude Workspace (Project) or as a periodic maintenance task.
Run it after every 3-5 releases, or when CHANGELOG.md exceeds ~200 lines.

---

## Prompt

```
Du bist ein Release-Manager für das mcp-memory-service Repository.

Führe eine Changelog-Archivierung durch:

### 1. CHANGELOG.md aufräumen
- Lies CHANGELOG.md
- Behalte NUR die letzten 6-8 Versionen (alles ab der aktuellen Minor-Version minus 2)
- Der [Unreleased] Abschnitt bleibt immer
- Aktualisiere den Header-Kommentar mit dem neuen Versionsbereich

### 2. Ältere Einträge archivieren
- Verschiebe alle älteren Einträge nach docs/archive/CHANGELOG-HISTORIC.md
- Füge sie AM ANFANG des Archivs ein (neueste zuerst)
- Prüfe auf Duplikate — wenn eine Version bereits im Archiv existiert, nicht nochmal einfügen
- Erhalte die vollständige Formatierung (Markdown-Struktur, Links, Code-Blöcke)

### 3. README.md kürzen
- Finde den "Previous Releases" Abschnitt
- Behalte maximal 7 Einträge (einzeilige Zusammenfassungen)
- Stelle sicher, dass dieser Link am Ende steht:
  **Full version history**: [CHANGELOG.md](CHANGELOG.md) | [Older versions](docs/archive/CHANGELOG-HISTORIC.md) | [All Releases](https://github.com/doobidoo/mcp-memory-service/releases)

### 4. Validierung
- Kein Inhalt darf verloren gehen — jede Version existiert genau einmal
- Zähle die Versionen in CHANGELOG.md + Archiv und vergleiche mit vorher
- Prüfe, dass CHANGELOG.md unter 200 Zeilen ist
- Prüfe, dass README.md "Previous Releases" maximal 10 Zeilen hat

### 5. Commit
- Erstelle EINEN Commit mit Message:
  "chore: archive changelog entries older than vX.Y.Z"
- NICHT pushen — nur committen

### Dateien:
- CHANGELOG.md
- docs/archive/CHANGELOG-HISTORIC.md
- README.md

### Regeln:
- KEIN Inhalt löschen, nur verschieben
- Duplikate im Archiv entfernen
- Formatierung beibehalten
- Bei Unsicherheit: weniger archivieren, nicht mehr
```

---

## Trigger-Kriterien

Führe diesen Housekeeping-Job aus wenn:
- CHANGELOG.md > 200 Zeilen
- README.md "Previous Releases" > 10 Einträge
- Nach einem Major/Minor Release (z.B. v10.27.0, v11.0.0)
- Alle 4-6 Wochen als Routine

## Verwendung

### Als Claude Code Skill
```bash
# In Claude Code direkt ausführen:
cat docs/maintenance/changelog-housekeeping-prompt.md
# Dann den Prompt-Block kopieren und in die Conversation einfügen
```

### Als Claude Workspace Project Instruction
1. Erstelle ein neues Project in claude.ai
2. Füge den Prompt als Custom Instruction hinzu
3. Lade CHANGELOG.md, README.md, und CHANGELOG-HISTORIC.md als Kontext hoch
4. Starte eine Conversation mit: "Führe den Changelog Housekeeping Job aus"

### Als Claude Code Hook (automatisch)
Kann als post-release Hook konfiguriert werden — siehe .claude/directives/agents.md
