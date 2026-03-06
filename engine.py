"""
Paper Wiper Engine
Detects and removes handwritten content from scanned exam papers.
Handles: fill-in-blank, MCQ bubbles, open answer boxes, circled answers.
"""

import cv2
import numpy as np
from pathlib import Path


# ── Tuning constants ────────────────────────────────────────────────────────
HANDWRITE_THRESHOLD  = 127   # binarisation threshold
MIN_STROKE_AREA      = 8     # ignore tiny noise specks
MAX_STROKE_AREA      = 18000 # ignore large printed elements (images, tables)
INPAINT_RADIUS       = 5     # inpaint fill radius (pixels)
DILATE_KERNEL        = 3     # grow detected regions slightly before wiping
PRINTED_UNIFORMITY   = 0.82  # connected-components with aspect uniformity above
                              # this are likely printed text — skip them


def load_image(path: str) -> np.ndarray:
    img = cv2.imread(path)
    if img is None:
        raise ValueError(f"Cannot load image: {path}")
    return img


def save_image(img: np.ndarray, path: str):
    cv2.imwrite(path, img)


# ── Step 1: binarise ────────────────────────────────────────────────────────
def binarise(img: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # Adaptive threshold handles uneven scan lighting
    binary = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        blockSize=21, C=10
    )
    return binary


# ── Step 2: separate printed vs handwritten ─────────────────────────────────
def is_handwritten_component(stats, labels, label_id, binary) -> bool:
    """
    Heuristic classifier for a single connected component.
    Printed text components tend to be:
      - very small (individual characters in a clean font)
      - highly regular in aspect ratio
      - uniform stroke width
    Handwritten components tend to be:
      - irregular shapes
      - larger bounding boxes relative to area
      - variable stroke width
    """
    x, y, w, h, area = (stats[label_id, cv2.CC_STAT_LEFT],
                         stats[label_id, cv2.CC_STAT_TOP],
                         stats[label_id, cv2.CC_STAT_WIDTH],
                         stats[label_id, cv2.CC_STAT_HEIGHT],
                         stats[label_id, cv2.CC_STAT_AREA])

    if area < MIN_STROKE_AREA:
        return False   # noise
    if area > MAX_STROKE_AREA:
        return False   # large printed element (diagram, table border)

    # Density: ratio of filled pixels to bounding box
    density = area / max(w * h, 1)

    # Aspect ratio
    aspect = w / max(h, 1)

    # Printed Chinese/English characters are usually:
    #   density > 0.25, aspect 0.5-2.0, small-ish area
    # Handwritten strokes are:
    #   lower density, more extreme aspects, or larger area

    # Rule 1: very elongated thin strokes = handwritten underline / slash
    if aspect > 6 or aspect < 0.1:
        if area > 30:
            return True

    # Rule 2: medium-large blobs with low density = handwritten characters
    if area > 150 and density < 0.30:
        return True

    # Rule 3: medium blobs in the mid-density range with large bounding box
    if area > 80 and w > 25 and h > 25:
        if density < 0.45:
            return True

    # Rule 4: very large area = definitely handwritten work area content
    if area > 2000:
        return True

    return False


def detect_handwriting_mask(img: np.ndarray) -> np.ndarray:
    """
    Returns a binary mask (255 = handwritten pixel) same size as img.
    """
    binary = binarise(img)

    # Connected components analysis
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
        binary, connectivity=8
    )

    mask = np.zeros(binary.shape, dtype=np.uint8)

    for label_id in range(1, num_labels):   # skip background (0)
        if is_handwritten_component(stats, labels, label_id, binary):
            mask[labels == label_id] = 255

    # Dilate slightly to catch edge pixels
    kernel = np.ones((DILATE_KERNEL, DILATE_KERNEL), np.uint8)
    mask = cv2.dilate(mask, kernel, iterations=2)

    return mask


# ── Step 3: wipe and restore ────────────────────────────────────────────────
def wipe_handwriting(img: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """
    Inpaint the masked regions with surrounding background content.
    This preserves printed lines underneath handwritten answers.
    """
    # Use Telea inpainting — best for restoring thin lines under writing
    result = cv2.inpaint(img, mask, INPAINT_RADIUS, cv2.INPAINT_TELEA)
    return result


def clean_page(img: np.ndarray,
               preview: bool = False
               ) -> tuple[np.ndarray, np.ndarray]:
    """
    Full pipeline for one page image.
    Returns (cleaned_image, preview_image_with_red_overlay).
    """
    mask = detect_handwriting_mask(img)
    cleaned = wipe_handwriting(img, mask)

    if preview:
        prev = img.copy()
        prev[mask == 255] = [80, 80, 255]   # red overlay on detected regions
    else:
        prev = None

    return cleaned, prev


# ── PDF support (requires PyMuPDF) ──────────────────────────────────────────
def pdf_to_images(pdf_path: str, dpi: int = 200) -> list[np.ndarray]:
    """Convert each PDF page to an OpenCV image."""
    import fitz   # PyMuPDF
    doc = fitz.open(pdf_path)
    images = []
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    for page in doc:
        pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
        arr = np.frombuffer(pix.samples, dtype=np.uint8)
        arr = arr.reshape(pix.height, pix.width, 3)
        images.append(cv2.cvtColor(arr, cv2.COLOR_RGB2BGR))
    doc.close()
    return images


def images_to_pdf(images: list[np.ndarray], output_path: str, dpi: int = 200):
    """Save a list of OpenCV images back to a PDF."""
    import fitz
    doc = fitz.open()
    for img in images:
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        h, w = rgb.shape[:2]
        pix = fitz.Pixmap(fitz.csRGB, w, h, rgb.tobytes(), False)
        page = doc.new_page(width=w * 72 / dpi, height=h * 72 / dpi)
        rect = fitz.Rect(0, 0, w * 72 / dpi, h * 72 / dpi)
        page.insert_image(rect, pixmap=pix)
    doc.save(output_path, garbage=4, deflate=True)
    doc.close()


def process_pdf(input_path: str,
                output_path: str,
                preview_path: str | None = None,
                dpi: int = 200,
                progress_callback=None) -> dict:
    """
    Full end-to-end: PDF in → cleaned PDF out.
    Optionally saves a preview PDF with red highlights.
    Returns stats dict.
    """
    pages = pdf_to_images(input_path, dpi=dpi)
    cleaned_pages = []
    preview_pages = []
    total_pixels = 0
    wiped_pixels = 0

    for i, page_img in enumerate(pages):
        if progress_callback:
            progress_callback(i + 1, len(pages))

        want_prev = preview_path is not None
        cleaned, prev = clean_page(page_img, preview=want_prev)
        cleaned_pages.append(cleaned)
        if prev is not None:
            preview_pages.append(prev)

        # stats
        mask = detect_handwriting_mask(page_img)
        total_pixels += mask.size
        wiped_pixels += int(np.sum(mask == 255))

    images_to_pdf(cleaned_pages, output_path, dpi=dpi)
    if preview_path and preview_pages:
        images_to_pdf(preview_pages, preview_path, dpi=dpi)

    return {
        "pages": len(pages),
        "wiped_percent": round(wiped_pixels / max(total_pixels, 1) * 100, 2),
    }
