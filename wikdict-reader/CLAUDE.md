# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

WikDict Reader is a Python library that annotates text with dictionary translations. It can handle conjugated forms, compound word splitting, and multi-word phrases. The primary use case is creating annotated EPUB files where words in the source language are linked to popup translations.

## Development Commands

### Testing
```bash
uv run pytest                 # Run all tests
uv run pytest tests/test_epub.py  # Run specific test file
```

### Code Quality
```bash
uv run ruff check            # Lint code
uv run ruff format           # Format code
```

### Installation/Setup
```bash
uv tool install "wikdict-reader @ git+https://github.com/karlb/wikdict-web#subdirectory=wikdict-reader"
```

### CLI Usage
```bash
translate_epub en-de input.epub [output.epub]  # Annotate EPUB with translations
```

## Architecture Overview

### Core Components

1. **CLI Module (`cli.py`)**: Entry point that handles argument parsing, database downloading, and orchestrates the translation process
2. **EPUB Processing (`epub.py`)**: Handles EPUB file manipulation, annotation insertion, and HTML processing  
3. **Translation Engine (`translate_segments.py`)**: Core text analysis that finds words/phrases and determines translation boundaries
4. **Lookup System (`lookup.py`)**: Database queries for translations with compound word splitting support
5. **HTML Utilities (`html.py`)**: HTML generation and formatting for popup content

### Translation Pipeline

1. **Text Segmentation**: `translate_segments.py` uses regex to identify words and attempts to find the longest translatable phrases
2. **Dictionary Lookup**: `lookup.py` queries SQLite databases with fuzzy matching and compound word splitting
3. **Annotation Insertion**: `epub.py` inserts HTML links and footnotes into EPUB content
4. **Database Management**: `cli.py` automatically downloads required dictionaries from wikdict.com

### Database Structure

- Main dictionaries: `{lang_pair}.sqlite3` (e.g., `en-de.sqlite3`)
- Compound databases: `{lang}-compound.sqlite3` for supported languages
- Stored in `~/.cache/wikdict/` or `$WIKDICT_DATA_DIR`

### Key Dependencies

- `lxml`: XML/HTML parsing and manipulation for EPUB processing
- `wikdict-query`: Database querying with fuzzy matching
- `wikdict-compound`: Compound word splitting for supported languages
- `more-itertools`: Advanced iteration utilities for text processing

### Testing Strategy

- Unit tests focus on translation segmentation (`test_translate_segments.py`)
- EPUB processing tests (`test_epub.py`)
- Uses pytest framework with simple test execution via `uv run pytest`