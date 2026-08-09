"""
Fixture PDF generator for question papers.
Generates realistic question paper PDFs with questions, options, sub-parts,
and embedded diagrams (circuits, ray diagrams, geometry, cell structures).
"""

import os
import io
import hashlib
from PIL import Image as PILImage, ImageDraw, ImageFont
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors


def create_diagram(diagram_type: str) -> io.BytesIO:
    """Creates a sample diagram image buffer based on diagram_type."""
    img = PILImage.new('RGB', (350, 180), color=(245, 247, 250))
    draw = ImageDraw.Draw(img)
    
    # Draw border
    draw.rectangle([2, 2, 347, 177], outline=(100, 100, 100), width=2)
    
    if diagram_type == "circuit":
        # Draw circuit diagram
        # Battery
        draw.line([(30, 90), (80, 90)], fill=(0, 0, 0), width=2)
        draw.line([(80, 70), (80, 110)], fill=(0, 0, 0), width=3)
        draw.line([(90, 80), (90, 100)], fill=(0, 0, 0), width=1)
        draw.line([(90, 90), (140, 90)], fill=(0, 0, 0), width=2)
        # Resistor R1
        draw.rectangle([140, 75, 200, 105], outline=(0, 0, 0), fill=(220, 220, 220), width=2)
        draw.text((155, 83), "R1 = 10 Ω", fill=(0, 0, 0))
        draw.line([(200, 90), (250, 90)], fill=(0, 0, 0), width=2)
        # Resistor R2
        draw.rectangle([250, 75, 310, 105], outline=(0, 0, 0), fill=(220, 220, 220), width=2)
        draw.text((265, 83), "R2 = 20 Ω", fill=(0, 0, 0))
        # Wire loop
        draw.line([(310, 90), (330, 90), (330, 150), (30, 150), (30, 90)], fill=(0, 0, 0), width=2)
        draw.text((140, 155), "Circuit Diagram for Q9", fill=(50, 50, 50))

    elif diagram_type == "optics":
        # Draw ray diagram for convex lens
        draw.line([(20, 90), (330, 90)], fill=(120, 120, 120), width=1) # Principal axis
        # Lens
        draw.ellipse([165, 30, 185, 150], outline=(0, 100, 200), fill=(200, 230, 255), width=2)
        # Object
        draw.line([(70, 90), (70, 40)], fill=(200, 0, 0), width=3) # Object arrow
        draw.polygon([(65, 45), (75, 45), (70, 35)], fill=(200, 0, 0))
        draw.text((60, 95), "Object (O)", fill=(0, 0, 0))
        # Rays
        draw.line([(70, 40), (175, 40), (280, 140)], fill=(255, 100, 0), width=2) # Ray 1
        draw.line([(70, 40), (175, 90), (280, 140)], fill=(0, 150, 0), width=2) # Ray 2
        # Image
        draw.line([(280, 90), (280, 140)], fill=(0, 0, 200), width=3) # Image arrow
        draw.text((270, 145), "Image (I)", fill=(0, 0, 0))
        draw.text((110, 160), "Optics Ray Diagram for Q10", fill=(50, 50, 50))

    elif diagram_type == "geometry":
        # Triangle with inscribed circle
        draw.polygon([(175, 25), (40, 155), (310, 155)], outline=(0, 0, 0), width=2)
        draw.text((170, 8), "A", fill=(0, 0, 0))
        draw.text((25, 155), "B", fill=(0, 0, 0))
        draw.text((315, 155), "C", fill=(0, 0, 0))
        # Inscribed circle
        draw.ellipse([110, 80, 240, 155], outline=(200, 0, 0), width=2)
        draw.text((170, 115), "O", fill=(200, 0, 0))
        draw.text((100, 160), "Geometric Construction for Q8", fill=(50, 50, 50))

    elif diagram_type == "cell":
        # Plant cell diagram
        draw.polygon([(40, 30), (310, 30), (330, 150), (20, 150)], outline=(30, 120, 30), fill=(230, 255, 230), width=3)
        # Nucleus
        draw.ellipse([140, 60, 200, 120], outline=(150, 0, 150), fill=(230, 200, 230), width=2)
        draw.text((150, 85), "Nucleus", fill=(100, 0, 100))
        # Cell wall label
        draw.line([(40, 50), (10, 50)], fill=(0, 0, 0), width=1)
        draw.text((2, 35), "Cell Wall", fill=(0, 0, 0))
        # Vacuole
        draw.rectangle([220, 50, 290, 130], outline=(0, 100, 200), fill=(220, 240, 255), width=2)
        draw.text((235, 85), "Vacuole", fill=(0, 50, 150))
        draw.text((110, 160), "Plant Cell Structure for Q7", fill=(50, 50, 50))

    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf


def generate_question_paper_pdf(
    output_path: str,
    cls: str,
    subject: str,
    year: str,
    paper_name: str,
    diagram_type: str = None
) -> dict:
    """
    Generates a realistic question paper PDF at output_path.
    Returns metadata dict about the paper.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Title'],
        fontSize=14,
        leading=18,
        alignment=1, # Center
        textColor=colors.HexColor('#1A237E')
    )
    header_style = ParagraphStyle(
        'DocHeader',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        alignment=1
    )
    sec_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=11,
        leading=15,
        textColor=colors.HexColor('#0D47A1'),
        spaceBefore=10,
        spaceAfter=6
    )
    q_style = ParagraphStyle(
        'QuestionText',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        spaceBefore=4,
        spaceAfter=2
    )
    opt_style = ParagraphStyle(
        'OptionText',
        parent=styles['Normal'],
        fontSize=9,
        leading=13,
        leftIndent=15,
        spaceBefore=2,
        spaceAfter=4
    )

    story = []

    # Title & Header
    story.append(Paragraph(f"<b>CENTRAL BOARD EXAMINATION - {year}</b>", title_style))
    story.append(Paragraph(f"<b>CLASS {cls} — {subject.upper()}</b>", title_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"<b>Time Allowed:</b> 3 Hours &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; <b>Maximum Marks:</b> 80", header_style))
    story.append(Spacer(1, 8))

    # General Instructions
    instructions = (
        "<b>General Instructions:</b><br/>"
        "1. This question paper contains 10 questions divided into Section A and Section B.<br/>"
        "2. Section A contains 5 Multiple Choice Questions carrying 1 mark each.<br/>"
        "3. Section B contains short & long answer questions carrying 3 to 5 marks each.<br/>"
        "4. All questions are compulsory. Read the diagrams carefully where provided."
    )
    story.append(Paragraph(instructions, q_style))
    story.append(Spacer(1, 10))

    # Section A
    story.append(Paragraph("<b>SECTION A (Multiple Choice Questions)</b>", sec_style))
    
    mcqs = [
        ("Q1. What is the SI unit of electric current?", "(a) Volt &nbsp;&nbsp;&nbsp; (b) Ampere &nbsp;&nbsp;&nbsp; (c) Ohm &nbsp;&nbsp;&nbsp; (d) Joule"),
        ("Q2. Which of the following is a balanced chemical equation?", "(a) H2 + O2 -> H2O &nbsp;&nbsp;&nbsp; (b) 2H2 + O2 -> 2H2O &nbsp;&nbsp;&nbsp; (c) H2 + 2O2 -> H2O"),
        ("Q3. The focal length of a spherical mirror is 20 cm. Its radius of curvature is:", "(a) 10 cm &nbsp;&nbsp;&nbsp; (b) 20 cm &nbsp;&nbsp;&nbsp; (c) 40 cm &nbsp;&nbsp;&nbsp; (d) 5 cm"),
        ("Q4. Which gas is evolved when dilute hydrochloric acid reacts with zinc granules?", "(a) Oxygen &nbsp;&nbsp;&nbsp; (b) Hydrogen &nbsp;&nbsp;&nbsp; (c) Carbon dioxide &nbsp;&nbsp;&nbsp; (d) Nitrogen"),
        ("Q5. The speed of light in vacuum is approximately:", "(a) 3 x 10^8 m/s &nbsp;&nbsp;&nbsp; (b) 3 x 10^5 m/s &nbsp;&nbsp;&nbsp; (c) 1.5 x 10^8 m/s &nbsp;&nbsp;&nbsp; (d) 3 x 10^6 m/s")
    ]

    for q_text, opt_text in mcqs:
        story.append(Paragraph(f"<b>{q_text}</b>", q_style))
        story.append(Paragraph(opt_text, opt_style))

    story.append(Spacer(1, 10))
    # Section B
    story.append(Paragraph("<b>SECTION B (Short & Long Answer Questions)</b>", sec_style))

    story.append(Paragraph("<b>Q6. State Ohm's Law and write its mathematical formula.</b>", q_style))
    story.append(Paragraph("(a) Define resistance of a conductor.", opt_style))
    story.append(Paragraph("(b) What factors affect the resistance of a wire?", opt_style))
    story.append(Spacer(1, 6))

    story.append(Paragraph("<b>Q7. Differentiate between autotrophic and heterotrophic nutrition with examples.</b>", q_style))
    story.append(Spacer(1, 6))

    if diagram_type:
        buf = create_diagram(diagram_type)
        img_elem = Image(buf, width=320, height=160)
        
        if diagram_type == "circuit":
            story.append(Paragraph("<b>Q8. Refer to the circuit diagram shown below to answer the following:</b>", q_style))
            story.append(Spacer(1, 4))
            story.append(img_elem)
            story.append(Spacer(1, 4))
            story.append(Paragraph("(a) Calculate the total effective resistance between the terminals.", opt_style))
            story.append(Paragraph("(b) If a battery of 12V is connected, find the total current flowing through the circuit.", opt_style))
            story.append(Spacer(1, 6))
            story.append(Paragraph("<b>Q9. Define magnetic field and draw magnetic field lines around a bar magnet.</b>", q_style))

        elif diagram_type == "optics":
            story.append(Paragraph("<b>Q8. Define refractive index of a medium.</b>", q_style))
            story.append(Spacer(1, 6))
            story.append(Paragraph("<b>Q9. Study the ray diagram given below for a convex lens:</b>", q_style))
            story.append(Spacer(1, 4))
            story.append(img_elem)
            story.append(Spacer(1, 4))
            story.append(Paragraph("(a) Identify the position and nature of the image formed.", opt_style))
            story.append(Paragraph("(b) Calculate the magnification if object distance u = -30 cm and focal length f = +15 cm.", opt_style))

        elif diagram_type == "geometry":
            story.append(Paragraph("<b>Q8. In the figure given below, a circle is inscribed in triangle ABC:</b>", q_style))
            story.append(Spacer(1, 4))
            story.append(img_elem)
            story.append(Spacer(1, 4))
            story.append(Paragraph("(a) Prove that the lengths of tangents drawn from an external point to a circle are equal.", opt_style))
            story.append(Paragraph("(b) If AB = 12 cm, BC = 8 cm, and AC = 10 cm, find the lengths of the tangent segments.", opt_style))
            story.append(Spacer(1, 6))
            story.append(Paragraph("<b>Q9. Find the quadratic polynomial whose zeroes are 3 and -4.</b>", q_style))

        elif diagram_type == "cell":
            story.append(Paragraph("<b>Q8. Observe the cell diagram below and answer the questions:</b>", q_style))
            story.append(Spacer(1, 4))
            story.append(img_elem)
            story.append(Spacer(1, 4))
            story.append(Paragraph("(a) Identify whether it is a plant cell or an animal cell. Give two reasons.", opt_style))
            story.append(Paragraph("(b) State the function of the cell wall and vacuole.", opt_style))
            story.append(Spacer(1, 6))
            story.append(Paragraph("<b>Q9. What are micro-organisms? Name two friendly micro-organisms.</b>", q_style))
    else:
        story.append(Paragraph("<b>Q8. State the law of conservation of energy with an example.</b>", q_style))
        story.append(Spacer(1, 6))
        story.append(Paragraph("<b>Q9. Describe an experiment to demonstrate chemical reactions.</b>", q_style))

    story.append(Spacer(1, 6))
    story.append(Paragraph("<b>Q10. Explain the process of photosynthesis with a balanced chemical equation.</b>", q_style))

    doc.build(story)
    
    return {
        "class": cls,
        "subject": subject,
        "year": year,
        "filename": os.path.basename(output_path),
        "output_path": output_path,
        "has_images": diagram_type is not None
    }
