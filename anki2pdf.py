import argparse
import sys
import os
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

try:
    pdfmetrics.registerFont(TTFont('NotoSans', '/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf'))
    pdfmetrics.registerFont(TTFont('NotoSans-Bold', '/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf'))
    
    pdfmetrics.registerFont(TTFont('NotoSymbols', '/usr/share/fonts/truetype/noto/NotoSansSymbols-Regular.ttf'))
    pdfmetrics.registerFont(TTFont('NotoSymbols2', '/usr/share/fonts/truetype/noto/NotoSansSymbols2-Regular.ttf'))
    
    FONT_NORMAL = 'NotoSans'
    FONT_BOLD = 'NotoSans-Bold'
    HAS_NOTO = True
except:
    print("Warning: Noto fonts not found. Falling back to Helvetica.")
    FONT_NORMAL = 'Helvetica'
    FONT_BOLD = 'Helvetica-Bold'
    HAS_NOTO = False

def apply_font_fallback(text):
    if not HAS_NOTO:
        return text
        
    out = []
    for char in text:
        codepoint = ord(char)
        if 0x1F000 <= codepoint <= 0x1FFFF:
             out.append(f'<font name="NotoSymbols2">{char}</font>')
        elif 0x2000 <= codepoint <= 0x2BFF:
             out.append(f'<font name="NotoSymbols">{char}</font>')
        else:
            out.append(char)
    return "".join(out)
PAGE_WIDTH, PAGE_HEIGHT = landscape(A4)
MARGIN = 5 * mm
GRID_ROWS = 3
GRID_COLS = 3
CARDS_PER_PAGE = GRID_ROWS * GRID_COLS
CARD_WIDTH = (PAGE_WIDTH - 2 * MARGIN) / GRID_COLS
CARD_HEIGHT = (PAGE_HEIGHT - 2 * MARGIN) / GRID_ROWS

def parse_anki_export(filepath):
    """
    Parses the Anki export file.
    Expected format: Tab-separated.
    """
    cards = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith('#'):
                continue
            parts = line.strip().split('\t')
            if len(parts) >= 5:
                deck_raw = parts[2]
                question = parts[3]
                answer = parts[4]
                
                deck_name = deck_raw.split('::')[-1]
                
                def sanitize_html(text):
                    # Basic replacements for block elements to line breaks/bullets
                    text = text.replace('<br>', '<br/>')
                    text = text.replace('<hr>', '<hr/>')
                    text = text.replace('<div>', '').replace('</div>', '<br/>')
                    text = text.replace('<ul>', '<br/>').replace('</ul>', '<br/>')
                    text = text.replace('<li>', '<br/>&bull; ').replace('</li>', '')
                    text = text.replace('<p>', '').replace('</p>', '<br/>')
                    
                    # Clean up multiple breaks
                    while '<br/><br/>' in text:
                        text = text.replace('<br/><br/>', '<br/>')
                    
                    # Remove leading breaks
                    if text.startswith('<br/>'):
                        text = text[5:]
                        
                    return text

                question = sanitize_html(question)
                answer = sanitize_html(answer)
                
                question = apply_font_fallback(question)
                answer = apply_font_fallback(answer)
                
                cards.append({
                    'deck': deck_name,
                    'question': question,
                    'answer': answer
                })
    return cards

def draw_text_fitted(c, text, x, y, width, height, max_font_size=16, min_font_size=6):
    style = ParagraphStyle(
        name='Normal',
        fontName=FONT_NORMAL,
        fontSize=max_font_size,
        leading=max_font_size * 1.2,
        alignment=TA_CENTER,
        textColor=colors.black,
        wordWrap=None
    )
    
    
    current_font_size = max_font_size
    while current_font_size >= min_font_size:
        style.fontSize = current_font_size
        style.leading = current_font_size * 1.2
        
        p = Paragraph(text, style)
        w, h = p.wrap(width - 4*mm, height - 4*mm)
        
        if w <= width and h <= height:
            y_offset = (height - h) / 2
            p.drawOn(c, x + 2*mm, y + height - y_offset - h)
            return
        
        current_font_size -= 1
    
    # If we fall through, draw with min size (might clip)
    style.fontSize = min_font_size
    style.leading = min_font_size * 1.2
    p = Paragraph(text, style)
    w, h = p.wrap(width - 4*mm, height - 4*mm)
    y_offset = (height - h) / 2
    p.drawOn(c, x + 2*mm, y + height - y_offset - h)

def draw_header(c, text, x, y, width):
    c.setFont(FONT_BOLD, 8)
    c.setFillColor(colors.grey)
    c.drawCentredString(x + width/2, y + CARD_HEIGHT - 4*mm, text)

def draw_front_indicator(c, x, y, width):
    c.setFont(FONT_NORMAL, 10)
    c.setFillColor(colors.grey)
    c.drawCentredString(x + width/2, y + 2*mm, "★")

def create_pdf(cards, output_file):
    c = canvas.Canvas(output_file, pagesize=landscape(A4))
    
    for i in range(0, len(cards), CARDS_PER_PAGE):
        chunk = cards[i : i + CARDS_PER_PAGE]
        
        # Front Side
        for idx, card in enumerate(chunk):
            row = idx // GRID_COLS
            col = idx % GRID_COLS
            
            x = MARGIN + col * CARD_WIDTH
            y = PAGE_HEIGHT - MARGIN - (row + 1) * CARD_HEIGHT
            
            c.setStrokeColor(colors.lightgrey)
            c.rect(x, y, CARD_WIDTH, CARD_HEIGHT)
            
            draw_header(c, card['deck'], x, y, CARD_WIDTH)
            
            draw_front_indicator(c, x, y, CARD_WIDTH)
            
            draw_text_fitted(c, card['question'], x, y, CARD_WIDTH, CARD_HEIGHT - 5*mm)
            
        c.showPage()
        
        # Back Side
        # Mirroring logic:
        # Row 0: 0,1,2 -> 2,1,0
        # Row 1: 3,4,5 -> 5,4,3
        # Row 2: 6,7,8 -> 8,7,6
        
        mirrored_chunk = [None] * CARDS_PER_PAGE
        for r in range(GRID_ROWS):
            row_start = r * GRID_COLS
            row_items = []
            for c_idx in range(GRID_COLS):
                if row_start + c_idx < len(chunk):
                    row_items.append(chunk[row_start + c_idx])
                else:
                    row_items.append(None)
            
            # Reverse the row items
            row_items.reverse()
            
            for c_idx, item in enumerate(row_items):
                mirrored_chunk[row_start + c_idx] = item

        for idx, card in enumerate(mirrored_chunk):
            if card is None:
                continue
                
            row = idx // GRID_COLS
            col = idx % GRID_COLS
            
            x = MARGIN + col * CARD_WIDTH
            y = PAGE_HEIGHT - MARGIN - (row + 1) * CARD_HEIGHT
            
            draw_text_fitted(c, card['answer'], x, y, CARD_WIDTH, CARD_HEIGHT - 5*mm)
 
        c.showPage()

    c.save()
    print(f"PDF created: {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert Anki export to Flashcard PDF")
    parser.add_argument("input", help="Path to Anki export text file")
    parser.add_argument("output", help="Path to output PDF file")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        print(f"Error: Input file not found: {args.input}")
        sys.exit(1)
        
    cards = parse_anki_export(args.input)
    print(f"Found {len(cards)} cards.")
    create_pdf(cards, args.output)
