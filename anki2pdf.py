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
from reportlab.lib.utils import ImageReader
import re
import hashlib
import matplotlib.pyplot as plt
from matplotlib import rcParams
import matplotlib.font_manager as fm


# Register fonts
fm.fontManager.addfont('/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf')
fm.fontManager.addfont('/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf')
fm.fontManager.addfont('/usr/share/fonts/truetype/noto/NotoSans-Italic.ttf')
fm.fontManager.addfont('/usr/share/fonts/truetype/noto/NotoSans-BoldItalic.ttf')


MATH_CACHE_DIR = "math_cache"
if not os.path.exists(MATH_CACHE_DIR):
    os.makedirs(MATH_CACHE_DIR)

MATH_SCALE_FACTOR = None

try:
    pdfmetrics.registerFont(TTFont('NotoSans', '/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf'))
    pdfmetrics.registerFont(TTFont('NotoSans-Bold', '/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf'))
    
    pdfmetrics.registerFont(TTFont('NotoSymbols', '/usr/share/fonts/truetype/noto/NotoSansSymbols-Regular.ttf'))
    pdfmetrics.registerFont(TTFont('NotoSymbols2', '/usr/share/fonts/truetype/noto/NotoSansSymbols2-Regular.ttf'))

    LATEX_REPLACEMENTS = {} 

    # Configure MatplotLib to use NotoSans for Math
    rcParams['mathtext.fontset'] = 'custom'
    rcParams['mathtext.rm'] = 'Noto Sans'
    rcParams['mathtext.it'] = 'Noto Sans:italic'
    rcParams['mathtext.bf'] = 'Noto Sans:bold'

    FONT_NORMAL = 'NotoSans'
    FONT_BOLD = 'NotoSans-Bold'
    HAS_NOTO = True
except:
    print("Warning: Noto fonts not found. Falling back to Helvetica.")
    FONT_NORMAL = 'Helvetica'
    FONT_BOLD = 'Helvetica-Bold'
    HAS_NOTO = False
    rcParams['mathtext.fontset'] = 'stixsans'

def clean_latex_for_matplotlib(latex):
    # \le -> \leq
    latex = re.sub(r'\\le(?=[^a-zA-Z]|$)', r'\\leq', latex)
    # \ge -> \geq
    latex = re.sub(r'\\ge(?=[^a-zA-Z]|$)', r'\\geq', latex)
    return latex

def render_latex_local(latex, cache_dir=MATH_CACHE_DIR):
    latex = clean_latex_for_matplotlib(latex)
    latex_hash = hashlib.md5(latex.encode('utf-8')).hexdigest()
    image_path = os.path.join(cache_dir, f"{latex_hash}.png")
    
    if os.path.exists(image_path):
        return image_path
        
    try:
        fig = plt.figure(figsize=(0.01, 0.01))
        
        # Render text
        text = f"${latex}$"
        
        fig.text(0, 0, text, fontsize=40)
        
        # Save to buffer/file with bounding box tight
        bbox = fig.get_window_extent().transformed(fig.dpi_scale_trans.inverted())
        
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        canvas = FigureCanvasAgg(fig)
        
        fig.clf()
        fig.patch.set_alpha(0)
        
        # Use simple text rendering
        t = fig.text(0.5, 0.5, text, fontsize=40, ha='center', va='center')
        
        # Save
        # bbox_inches='tight' trims whitespace
        fig.savefig(image_path, dpi=300, bbox_inches='tight', transparent=True, pad_inches=0.02)
        plt.close(fig)
        
        return image_path
    
    except Exception as e:
        print(f"Error rendering math locally for '{latex}': {e}")
        plt.close(fig) if 'fig' in locals() else None
        return None

def get_math_scale():
    global MATH_SCALE_FACTOR
    if MATH_SCALE_FACTOR is not None:
        return MATH_SCALE_FACTOR
        
    try:
        image_path = render_latex_local("x")
        if image_path:
            img = ImageReader(image_path)
            _, h_ref = img.getSize()
            TARGET_X_HEIGHT = 18
            MATH_SCALE_FACTOR = TARGET_X_HEIGHT / h_ref
        else:
            MATH_SCALE_FACTOR = 1.0 # Fallback
    except Exception as e:
        print(f"Error calculating math scale: {e}")
        MATH_SCALE_FACTOR = 1.0
        
    print(f"Math scale factor: {MATH_SCALE_FACTOR}")
    return MATH_SCALE_FACTOR

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

                def process_mathjax(text):
                    # Regex for inline math \( ... \)
                    pattern_inline = r'\\\((.*?)\\\)'
                    # Regex for display math \[ ... \]
                    pattern_display = r'\\\[(.*?)\\\]'
                    
                    math_scale = get_math_scale()
                    
                    def replace_math(match):
                        latex = match.group(1).strip()
                        if not latex:
                            return ""
                        
                        image_path = render_latex_local(latex)
                        if not image_path:
                             return match.group(0) # Return original text on failure
                        
                        # Return image tag for ReportLab
                        # Adjust valign to align with text
                        try:
                            img = ImageReader(image_path)
                            iw, ih = img.getSize()
                            
                            target_width = iw * math_scale
                            target_height = ih * math_scale
                            
                            # Constrain to card size
                            max_img_width = CARD_WIDTH - 6*mm
                            max_img_height = CARD_HEIGHT - 6*mm
                            
                            downscale = min(1.0, max_img_width / target_width, max_img_height / target_height)
                            
                            target_width *= downscale
                            target_height *= downscale
                            
                            valign = -target_height/2 + 4 
                            
                            return f'<img src="{image_path}" valign="{valign}" width="{target_width}" height="{target_height}"/>'
                        except Exception as e:
                            print(f"Error reading image size: {e}")
                            return match.group(0)

                    # Process both patterns

                    # Process both patterns
                    text = re.sub(pattern_display, replace_math, text)
                    text = re.sub(pattern_inline, replace_math, text)
                    return text

                question = sanitize_html(question)
                answer = sanitize_html(answer)
                
                question = process_mathjax(question)
                answer = process_mathjax(answer)

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
    if HAS_NOTO:
        c.setFont('NotoSymbols', 10)
    else:
        c.setFont(FONT_NORMAL, 10)
    c.setFillColor(colors.grey)
    c.drawCentredString(x + width/2, y + 2*mm, "★")

def draw_page_number(c, page_bum, x, y):
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.grey)
    # Draw small page number at the bottom center of the page
    c.drawCentredString(PAGE_WIDTH / 2, 3 * mm, f"{page_bum}")

def create_pdf(cards, output_file):
    c = canvas.Canvas(output_file, pagesize=landscape(A4))
    
    page_num = 1
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
            
        draw_page_number(c, page_num, 0, 0)
        c.showPage()
        page_num += 1
        
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
            
            c.setStrokeColor(colors.lightgrey)
            c.rect(x, y, CARD_WIDTH, CARD_HEIGHT)
            
            draw_text_fitted(c, card['answer'], x, y, CARD_WIDTH, CARD_HEIGHT - 5*mm)
 
        draw_page_number(c, page_num, 0, 0)
        c.showPage()
        page_num += 1

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
