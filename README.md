# AnkiToFlashcard

A simple Python script to convert Anki flashcard exports into a print-ready PDF layout.

## Features

- **3x3 Grid Layout**: Fits 9 cards per A4 page.
- **Double-Sided Printing Support**: Automatically mirrors the back side of the cards for perfect alignment when printing on both sides.
- **Dynamic Text Scaling**: Automatically adjusts font size to fit your card content.
- **HTML Translation**: Supports basic HTML formatting (like `<br>`, `<div>`, `<ul>`, `<li>`).
- **Unicode Symbol Support**: Specifically designed to handle Noto Sans Symbols for math and special characters.

## Prerequisites

### Dependencies & Virtual Environment

It is highly recommended to use a virtual environment to avoid conflicts with system-wide packages and fix the "externally-managed-environment" error on modern Linux distributions.

1. **Create a virtual environment**:
   ```bash
   python3 -m venv .venv
   ```

2. **Install dependencies**:
   ```bash
   .venv/bin/pip install reportlab
   ```

### Fonts (Linux)

For full symbol support, the script looks for Noto Sans fonts. On Debian/Ubuntu, you can install them with:

```bash
sudo apt-get install fonts-noto-core fonts-noto-ui-extra fonts-noto-symbols
```

If these fonts are not found, the script will fall back to standard Helvetica.

## How to Export from Anki

To use this script, you must export your Anki deck in a specific format:

1. Open Anki and select the deck you want to export.
2. Go to **File > Export**.
3. Select **Notes in Plain Text** (.txt).
4. **IMPORTANT**: Ensure "Include HTML and media references" is **checked**.
5. Click **Export** and save the file.

## Usage

Run the script using the Python interpreter from your virtual environment:

```bash
./.venv/bin/python anki2pdf.py <input_file.txt> <output_file.pdf>
```

### Example

```bash
./.venv/bin/python anki2pdf.py my_anki_export.txt flashcards.pdf
```

## Layout Details

- **Page Size**: A4 (Landscape)
- **Grid**: 3 columns, 3 rows (9 cards per side)
- **Front Side**: Shows the question and a small star (★) indicator at the bottom.
- **Back Side**: Shows the answer, mirrored horizontally to match the front side's position when printed double-sided.

---

> [!TIP]
> When printing the generated PDF, ensure you select **"Actual Size"** or **100% Scale** in your printer settings to maintain correct card dimensions.
