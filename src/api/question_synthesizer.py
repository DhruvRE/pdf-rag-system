"""
Advanced Educational Question Synthesizer.
Generates authentic mathematical (numericals, equations, algebra, geometry with SVG diagrams, sets, trigonometry)
and scientific questions with detailed step-by-step marking scheme solutions.
Strictly avoids any unwanted prefixes like '[school Analytical Question]'.
"""

import math
import random
from typing import Optional, List, Dict, Any


def generate_triangle_bpt_svg(ad: float, db: float, ae: float, ec: float) -> str:
    """Generates a clean vector SVG diagram of Triangle ABC with parallel segment DE."""
    return f'''<div class="my-3 flex flex-col items-center justify-center p-3 bg-slate-900 border border-slate-700/80 rounded-lg max-w-sm mx-auto">
  <span class="text-[11px] font-semibold text-indigo-300 mb-1">Figure: Triangle ABC with DE || BC</span>
  <svg width="240" height="170" viewBox="0 0 240 170" xmlns="http://www.w3.org/2000/svg" class="text-slate-200">
    <!-- Triangle ABC -->
    <polygon points="120,20 30,150 210,150" fill="none" stroke="#818cf8" stroke-width="2.5" />
    <!-- Line DE || BC -->
    <line x1="75" y1="85" x2="165" y2="85" stroke="#34d399" stroke-width="2" stroke-dasharray="3,3" />
    <!-- Vertices labels -->
    <text x="115" y="15" fill="#f8fafc" font-size="12" font-weight="bold">A</text>
    <text x="15" y="158" fill="#f8fafc" font-size="12" font-weight="bold">B</text>
    <text x="215" y="158" fill="#f8fafc" font-size="12" font-weight="bold">C</text>
    <text x="58" y="85" fill="#34d399" font-size="12" font-weight="bold">D</text>
    <text x="172" y="85" fill="#34d399" font-size="12" font-weight="bold">E</text>
    <!-- Dimension annotations -->
    <text x="75" y="55" fill="#94a3b8" font-size="10">{ad} cm</text>
    <text x="35" y="125" fill="#94a3b8" font-size="10">{db} cm</text>
    <text x="145" y="55" fill="#94a3b8" font-size="10">{ae} cm</text>
    <text x="180" y="125" fill="#f59e0b" font-weight="bold" font-size="10">EC = ?</text>
  </svg>
</div>'''


def generate_circle_tangent_svg(r: float, tangent_len: float, op_len: float) -> str:
    """Generates an SVG diagram for tangent from external point to circle."""
    return f'''<div class="my-3 flex flex-col items-center justify-center p-3 bg-slate-900 border border-slate-700/80 rounded-lg max-w-sm mx-auto">
  <span class="text-[11px] font-semibold text-indigo-300 mb-1">Figure: Tangent PT from Point P to Circle C(O, r)</span>
  <svg width="250" height="150" viewBox="0 0 250 150" xmlns="http://www.w3.org/2000/svg" class="text-slate-200">
    <!-- Circle with Center O -->
    <circle cx="75" cy="75" r="50" fill="none" stroke="#818cf8" stroke-width="2" />
    <circle cx="75" cy="75" r="3" fill="#818cf8" />
    <text x="65" y="70" fill="#f8fafc" font-size="11" font-weight="bold">O</text>
    <!-- Point P -->
    <circle cx="210" cy="75" r="3" fill="#34d399" />
    <text x="218" y="78" fill="#34d399" font-size="12" font-weight="bold">P</text>
    <!-- Point of contact T -->
    <circle cx="100" cy="32" r="3" fill="#f59e0b" />
    <text x="100" y="24" fill="#f59e0b" font-size="12" font-weight="bold">T</text>
    <!-- Radius OT -->
    <line x1="75" y1="75" x2="100" y2="32" stroke="#818cf8" stroke-width="1.8" />
    <text x="70" y="48" fill="#94a3b8" font-size="10">r={r}</text>
    <!-- Tangent PT -->
    <line x1="210" y1="75" x2="100" y2="32" stroke="#34d399" stroke-width="2" />
    <text x="155" y="45" fill="#34d399" font-size="10">{tangent_len} cm</text>
    <!-- Line OP -->
    <line x1="75" y1="75" x2="210" y2="75" stroke="#94a3b8" stroke-width="1.5" stroke-dasharray="4,4" />
    <text x="135" y="92" fill="#94a3b8" font-size="10">OP = ?</text>
    <!-- Right angle indicator at T -->
    <rect x="96" y="36" width="6" height="6" fill="none" stroke="#f59e0b" stroke-width="1" />
  </svg>
</div>'''


def generate_venn_diagram_svg(set_a_label: str, set_b_label: str, both_count: int, a_only: int, b_only: int) -> str:
    """Generates an SVG Venn diagram for sets."""
    return f'''<div class="my-3 flex flex-col items-center justify-center p-3 bg-slate-900 border border-slate-700/80 rounded-lg max-w-sm mx-auto">
  <span class="text-[11px] font-semibold text-indigo-300 mb-1">Figure: Venn Diagram of Sets A and B</span>
  <svg width="240" height="130" viewBox="0 0 240 130" xmlns="http://www.w3.org/2000/svg">
    <!-- Universal set box -->
    <rect x="10" y="10" width="220" height="110" fill="none" stroke="#475569" stroke-width="1.5" rx="6" />
    <text x="18" y="26" fill="#94a3b8" font-size="11" font-weight="bold">U</text>
    <!-- Circle A -->
    <circle cx="90" cy="65" r="40" fill="rgba(99, 102, 241, 0.15)" stroke="#6366f1" stroke-width="2" />
    <text x="75" y="32" fill="#818cf8" font-size="11" font-weight="bold">{set_a_label}</text>
    <text x="70" y="70" fill="#f8fafc" font-size="11">{a_only}</text>
    <!-- Circle B -->
    <circle cx="150" cy="65" r="40" fill="rgba(16, 185, 129, 0.15)" stroke="#10b981" stroke-width="2" />
    <text x="155" y="32" fill="#34d399" font-size="11" font-weight="bold">{set_b_label}</text>
    <text x="165" y="70" fill="#f8fafc" font-size="11">{b_only}</text>
    <!-- Intersection -->
    <text x="115" y="70" fill="#fbbf24" font-size="11" font-weight="bold">{both_count}</text>
  </svg>
</div>'''


def synthesize_math_question(
    index: int,
    topic: Optional[str],
    difficulty: str,
    target_q_type: str,
    class_level: str
) -> Dict[str, Any]:
    """Generates authentic, mathematically rigorous question with real numbers, formulas, and diagrams."""
    topic_lower = (topic or "").lower()
    
    # Selection of Math Category
    category = "general"
    if any(k in topic_lower for k in ["quad", "poly", "zero", "root", "algebra", "factor"]):
        category = "quadratic"
    elif any(k in topic_lower for k in ["ap", "arithmetic progression", "progression", "series"]):
        category = "ap"
    elif any(k in topic_lower for k in ["trig", "sin", "cos", "tan", "elevation", "height"]):
        category = "trigonometry"
    elif any(k in topic_lower for k in ["triangle", "similarity", "thales", "bpt"]):
        category = "triangles"
    elif any(k in topic_lower for k in ["circle", "tangent"]):
        category = "circles"
    elif any(k in topic_lower for k in ["coordinate", "distance", "section"]):
        category = "coordinate_geometry"
    elif any(k in topic_lower for k in ["set", "venn", "relation"]):
        category = "sets"
    elif any(k in topic_lower for k in ["volume", "surface", "sphere", "cylinder", "cone"]):
        category = "surface_volume"
    elif any(k in topic_lower for k in ["prob", "dice", "card", "stat", "mean", "median"]):
        category = "probability_stat"
    elif any(k in topic_lower for k in ["real number", "hcf", "lcm", "irrational"]):
        category = "real_numbers"
    else:
        # Rotate through standard curriculum topics based on index
        categories = ["quadratic", "ap", "trigonometry", "triangles", "circles", "coordinate_geometry", "surface_volume", "probability_stat", "sets", "real_numbers"]
        category = categories[(index - 1) % len(categories)]

    # Determine question type
    if target_q_type == "mcq":
        q_type = "multiple_choice"
    elif target_q_type in ("numerical", "short_answer"):
        q_type = "short_answer"
    elif target_q_type in ("long", "long_answer"):
        q_type = "long_answer"
    elif target_q_type in ("diagram", "case_based"):
        q_type = "case_based"
    else:
        # Balanced mix
        q_type = "multiple_choice" if index % 3 == 1 else ("short_answer" if index % 3 == 2 else "long_answer")

    # 1. Quadratic Equations & Polynomials
    if category == "quadratic":
        r1, r2 = random.choice([(2, 3), (1, 4), (-2, 5), (-3, -1), (2, -4), (3, 5)])
        b = -(r1 + r2)
        c = r1 * r2
        sign_b = f"- {abs(b)}" if b < 0 else f"+ {b}"
        sign_c = f"- {abs(c)}" if c < 0 else f"+ {c}"
        poly_str = f"x^2 {sign_b}x {sign_c}"

        if q_type == "multiple_choice":
            q_text = f"If $\\alpha$ and $\\beta$ are the zeroes of the quadratic polynomial $p(x) = {poly_str}$, find the numerical value of $\\frac{{1}}{{\\alpha}} + \\frac{{1}}{{\\beta}}$."
            val_num = -(b)
            val_den = c
            # Simplify
            g = math.gcd(abs(val_num), abs(val_den))
            n_s, d_s = val_num // g, val_den // g
            if d_s < 0:
                n_s, d_s = -n_s, -d_s
            ans_str = f"{n_s}" if d_s == 1 else f"\\frac{{{n_s}}}{{{d_s}}}"
            wrong_1 = f"-\\frac{{{n_s}}}{{{d_s}}}" if d_s != 1 else f"{-n_s}"
            wrong_2 = f"\\frac{{{d_s}}}{{{n_s}}}" if n_s != 0 else "0"
            wrong_3 = f"{c}"

            options = [
                {"label": "A", "text": f"${ans_str}$"},
                {"label": "B", "text": f"${wrong_1}$"},
                {"label": "C", "text": f"${wrong_2}$"},
                {"label": "D", "text": f"${wrong_3}$"}
            ]
            correct_answer = "Option (A)"
            solution = f"""**Step-by-Step Solution:**
1. Given polynomial $p(x) = {poly_str}$ with zeroes $\\alpha$ and $\\beta$.
2. By relations between zeroes and coefficients:
   - Sum of zeroes: $\\alpha + \\beta = -\\frac{{b}}{{a}} = -({b}) = {-b}$
   - Product of zeroes: $\\alpha \\beta = \\frac{{c}}{{a}} = {c}$
3. Evaluating the requested expression:
   $$\\frac{{1}}{{\\alpha}} + \\frac{{1}}{{\\beta}} = \\frac{{\\alpha + \\beta}}{{\\alpha \\beta}} = \\frac{{{-b}}}{{{c}}} = {ans_str}$$
4. Hence, the correct answer is **Option (A)**."""
        elif q_type == "short_answer":
            q_text = f"Find the roots of the quadratic equation ${poly_str} = 0$ using the quadratic formula."
            options = []
            correct_answer = f"x = {r1}, x = {r2}"
            disc = b**2 - 4 * c
            solution = f"""**Step-by-Step Solution:**
1. The given quadratic equation is ${poly_str} = 0$.
2. Comparing with standard form $ax^2 + bx + c = 0$:
   - $a = 1, b = {b}, c = {c}$
3. Calculate the discriminant $D$:
   $$D = b^2 - 4ac = ({b})^2 - 4(1)({c}) = {b**2} - ({4*c}) = {disc}$$
   Since $D > 0$, the equation has two distinct real roots.
4. Applying the quadratic formula:
   $$x = \\frac{{-b \\pm \\sqrt{{D}}}}{{2a}} = \\frac{{-({b}) \\pm \\sqrt{{{disc}}}}}{{2(1)}} = \\frac{{{-b} \\pm {abs(r1 - r2)}}}{{2}}$$
   - Taking positive sign: $x = \\frac{{{-b} + {abs(r1 - r2)}}}{{2}} = {max(r1, r2)}$
   - Taking negative sign: $x = \\frac{{{-b} - {abs(r1 - r2)}}}{{2}} = {min(r1, r2)}$
5. The roots of the equation are **$x = {r1}$** and **$x = {r2}$**."""
        else:
            q_text = f"Find the value of $k$ for which the quadratic equation $(k - 1)x^2 + 2(k - 1)x + 1 = 0$ has real and equal roots. Hence, find the roots of the equation."
            options = []
            correct_answer = "k = 2, Root: x = -1"
            solution = f"""**Step-by-Step Solution:**
1. Given equation: $(k - 1)x^2 + 2(k - 1)x + 1 = 0$.
2. For real and equal roots, the discriminant must be zero: $D = 0$.
   $$D = B^2 - 4AC = [2(k - 1)]^2 - 4(k - 1)(1) = 0$$
3. Expanding and factoring:
   $$4(k - 1)^2 - 4(k - 1) = 0 \\implies 4(k - 1)[(k - 1) - 1] = 0$$
   $$4(k - 1)(k - 2) = 0$$
   - Since $k - 1 \\neq 0$ (otherwise it ceases to be quadratic), $k \\neq 1$.
   - Therefore, **$k = 2$**.
4. Substituting $k = 2$ back into the quadratic equation:
   $$(2 - 1)x^2 + 2(2 - 1)x + 1 = 0 \\implies x^2 + 2x + 1 = 0 \\implies (x + 1)^2 = 0$$
5. Thus, the equal roots are **$x = -1, -1$**."""

    # 2. Arithmetic Progressions (AP)
    elif category == "ap":
        a = random.choice([3, 5, 7, 2, 9])
        d = random.choice([2, 3, 4, 5, 6])
        n_term = 12
        a_n = a + (n_term - 1) * d
        s_n = (n_term * (2 * a + (n_term - 1) * d)) // 2

        if q_type == "multiple_choice":
            q_text = f"The $12^{{\\text{{th}}}}$ term of the Arithmetic Progression $({a}, {a+d}, {a+2*d}, {a+3*d}, \\dots)$ is:"
            options = [
                {"label": "A", "text": f"${a_n}$"},
                {"label": "B", "text": f"${a_n - d}$"},
                {"label": "C", "text": f"${a_n + d}$"},
                {"label": "D", "text": f"${a_n + 2*d}$"}
            ]
            correct_answer = "Option (A)"
            solution = f"""**Step-by-Step Solution:**
1. Identify the parameters of the Arithmetic Progression:
   - First term $a = {a}$
   - Common difference $d = {a+d} - {a} = {d}$
2. The formula for the $n^{{\\text{{th}}}}$ term is:
   $$a_n = a + (n - 1)d$$
3. For $n = 12$:
   $$a_{{12}} = {a} + (12 - 1)({d}) = {a} + 11({d}) = {a} + {11*d} = {a_n}$$
4. Hence, the correct answer is **Option (A)**."""
        elif q_type == "short_answer":
            p_term = 4
            q_term = 9
            val_p = a + (p_term - 1) * d
            val_q = a + (q_term - 1) * d
            q_text = f"The $4^{{\\text{{th}}}}$ term of an AP is ${val_p}$ and its $9^{{\\text{{th}}}}$ term is ${val_q}$. Find the first term $a$, common difference $d$, and the $15^{{\\text{{th}}}}$ term."
            options = []
            a_15 = a + 14 * d
            correct_answer = f"a = {a}, d = {d}, a_15 = {a_15}"
            solution = f"""**Step-by-Step Solution:**
1. Formulate simultaneous equations:
   - $a_4 = a + 3d = {val_p}$  ...(Equation 1)
   - $a_9 = a + 8d = {val_q}$  ...(Equation 2)
2. Subtract Equation 1 from Equation 2:
   $$(a + 8d) - (a + 3d) = {val_q} - {val_p} \\implies 5d = {val_q - val_p} \\implies d = {d}$$
3. Substitute $d = {d}$ into Equation 1:
   $$a + 3({d}) = {val_p} \\implies a + {3*d} = {val_p} \\implies a = {a}$$
4. Calculate the $15^{{\\text{{th}}}}$ term:
   $$a_{{15}} = a + 14d = {a} + 14({d}) = {a} + {14*d} = {a_15}$$
5. Final Answer: **$a = {a}, d = {d}, a_{{15}} = {a_15}$**."""
        else:
            q_text = f"Find the sum of all two-digit natural numbers which leave a remainder of $1$ when divided by $3$."
            options = []
            correct_answer = "1650"
            solution = f"""**Step-by-Step Solution:**
1. The two-digit natural numbers start from 10 and end at 99.
2. Two-digit numbers leaving a remainder of 1 when divided by 3:
   - First number: $10$ (since $10 = 3 \\times 3 + 1$)
   - Next numbers: $13, 16, 19, \\dots$
   - Last two-digit number: $97$ (since $97 = 3 \\times 32 + 1$)
3. This sequence forms an AP with:
   - First term $a = 10$
   - Common difference $d = 3$
   - Last term $a_n = 97$
4. Find the number of terms $n$:
   $$a_n = a + (n - 1)d \\implies 97 = 10 + (n - 1)(3) \\implies 87 = 3(n - 1) \\implies n - 1 = 29 \\implies n = 30$$
5. Find the sum $S_{{30}}$:
   $$S_n = \\frac{{n}}{{2}}(a + l) = \\frac{{30}}{{2}}(10 + 97) = 15 \\times 107 = 1605$$
6. Correct Sum = **1605**."""

    # 3. Geometry & Triangles (with Figure)
    elif category == "triangles":
        ad = round(random.choice([2.4, 3.6, 1.8, 2.0]), 1)
        db = round(random.choice([3.6, 4.8, 5.4, 3.0]), 1)
        ae = round(random.choice([3.2, 4.0, 2.4, 3.0]), 1)
        ec = round((db * ae) / ad, 1)

        fig_svg = generate_triangle_bpt_svg(ad, db, ae, ec)
        q_text = f"In the given figure below, in $\\triangle ABC$, $DE \\parallel BC$. If $AD = {ad}\\text{{ cm}}$, $DB = {db}\\text{{ cm}}$, and $AE = {ae}\\text{{ cm}}$, find the length of $EC$.\n\n{fig_svg}"

        if q_type == "multiple_choice":
            options = [
                {"label": "A", "text": f"${ec}\\text{{ cm}}$"},
                {"label": "B", "text": f"${round(ec + 1.2, 1)}\\text{{ cm}}$"},
                {"label": "C", "text": f"${round(ec - 0.8, 1)}\\text{{ cm}}$"},
                {"label": "D", "text": f"${round(ec * 1.5, 1)}\\text{{ cm}}$"}
            ]
            correct_answer = "Option (A)"
        else:
            options = []
            correct_answer = f"EC = {ec} cm"

        solution = f"""**Step-by-Step Solution:**
1. State the relevant geometric theorem:
   - By the **Basic Proportionality Theorem (Thales' Theorem)**, if a line is drawn parallel to one side of a triangle intersecting the other two sides, it divides the sides in the same ratio.
2. Since $DE \\parallel BC$ in $\\triangle ABC$:
   $$\\frac{{AD}}{{DB}} = \\frac{{AE}}{{EC}}$$
3. Substitute the given values:
   $$\\frac{{{ad}}}{{{db}}} = \\frac{{{ae}}}{{EC}}$$
4. Cross-multiply to solve for $EC$:
   $$EC = \\frac{{{db} \\times {ae}}}{{{ad}}} = \\frac{{{round(db * ae, 2)}}}{{{ad}}} = {ec}\\text{{ cm}}$$
5. Therefore, the length of $EC$ is **${ec}\\text{{ cm}}$**."""

    # 4. Circles & Tangents (with Figure)
    elif category == "circles":
        r, tangent_len, op_len = random.choice([(5, 12, 13), (6, 8, 10), (7, 24, 25), (8, 15, 17)])
        fig_svg = generate_circle_tangent_svg(r, tangent_len, op_len)
        q_text = f"From an external point $P$, a tangent $PT$ of length ${tangent_len}\\text{{ cm}}$ is drawn to a circle with center $O$ and radius ${r}\\text{{ cm}}$. Calculate the distance of point $P$ from the center $O$.\n\n{fig_svg}"

        if q_type == "multiple_choice":
            options = [
                {"label": "A", "text": f"${op_len}\\text{{ cm}}$"},
                {"label": "B", "text": f"${op_len + 2}\\text{{ cm}}$"},
                {"label": "C", "text": f"${op_len - 3}\\text{{ cm}}$"},
                {"label": "D", "text": f"${round(math.sqrt(tangent_len**2 - r**2), 1)}\\text{{ cm}}$"}
            ]
            correct_answer = "Option (A)"
        else:
            options = []
            correct_answer = f"OP = {op_len} cm"

        solution = f"""**Step-by-Step Solution:**
1. Geometric Principle:
   - The tangent at any point of a circle is perpendicular to the radius through the point of contact.
   - Therefore, $\\angle OTP = 90^\\circ$, making $\\triangle OTP$ a right-angled triangle.
2. Applying Pythagoras' Theorem in right-angled $\\triangle OTP$:
   $$OP^2 = OT^2 + PT^2$$
3. Substituting the given parameters:
   $$OP^2 = ({r})^2 + ({tangent_len})^2 = {r**2} + {tangent_len**2} = {op_len**2}$$
4. Taking the square root:
   $$OP = \\sqrt{{{op_len**2}}} = {op_len}\\text{{ cm}}$$
5. Hence, the distance of point $P$ from the center is **${op_len}\\text{{ cm}}$**."""

    # 5. Trigonometry & Heights and Distances
    elif category == "trigonometry":
        if q_type == "multiple_choice":
            q_text = "Evaluate the numerical value of the trigonometric expression: $$\\frac{5\\cos^2 60^\\circ + 4\\sec^2 30^\\circ - \\tan^2 45^\\circ}{\\sin^2 30^\\circ + \\cos^2 30^\\circ}$$"
            options = [
                {"label": "A", "text": "$\\frac{67}{12}$"},
                {"label": "B", "text": "$\\frac{55}{12}$"},
                {"label": "C", "text": "$\\frac{13}{12}$"},
                {"label": "D", "text": "$5$"}
            ]
            correct_answer = "Option (A)"
            solution = f"""**Step-by-Step Solution:**
1. Substitute standard values of trigonometric ratios:
   - $\\cos 60^\\circ = \\frac{{1}}{{2}} \\implies \\cos^2 60^\\circ = \\frac{{1}}{{4}}$
   - $\\sec 30^\\circ = \\frac{{2}}{{\\sqrt{{3}}}} \\implies \\sec^2 30^\\circ = \\frac{{4}}{{3}}$
   - $\\tan 45^\\circ = 1 \\implies \\tan^2 45^\\circ = 1$
   - Identity: $\\sin^2 30^\\circ + \\cos^2 30^\\circ = 1$
2. Evaluate the numerator:
   $$\\text{{Numerator}} = 5\\left(\\frac{{1}}{{4}}\\right) + 4\\left(\\frac{{4}}{{3}}\\right) - 1 = \\frac{{5}}{{4}} + \\frac{{16}}{{3}} - 1$$
3. Take common denominator $12$:
   $$= \\frac{{15 + 64 - 12}}{{12}} = \\frac{{67}}{{12}}$$
4. Since denominator is $1$, final value is **$\\frac{{67}}{{12}}$** (Option A)."""
        else:
            dist = random.choice([30, 45, 60])
            h = round(dist * math.tan(math.radians(30)), 1)
            q_text = f"From a point on the horizontal ground, $30\\text{{ m}}$ away from the foot of a vertical tower, the angle of elevation of the top of the tower is measured to be $30^\\circ$. Find the height of the tower. (Take $\\sqrt{{3}} \\approx 1.732$)"
            options = []
            correct_answer = "17.32 m"
            solution = f"""**Step-by-Step Solution:**
1. Let $AB = h$ be the height of the vertical tower and $BC = 30\\text{{ m}}$ be the distance from the foot of the tower.
2. In right-angled $\\triangle ABC$:
   $$\\tan 30^\\circ = \\frac{{\\text{{Opposite}}}}{{\\text{{Adjacent}}}} = \\frac{{AB}}{{BC}}$$
3. Substitute known values:
   $$\\frac{{1}}{{\\sqrt{{3}}}} = \\frac{{h}}{{30}} \\implies h = \\frac{{30}}{{\\sqrt{{3}}}} = 10\\sqrt{{3}}\\text{{ m}}$$
4. Numerical evaluation:
   $$h = 10 \\times 1.732 = 17.32\\text{{ m}}$$
5. The height of the tower is **$17.32\\text{{ m}}$**."""

    # 6. Sets & Relations (with Venn Diagram)
    elif category == "sets":
        both = 12
        a_only = 18
        b_only = 15
        total_students = a_only + both + b_only + 5
        venn_svg = generate_venn_diagram_svg("Cricket", "Football", both, a_only, b_only)

        q_text = f"In a class of ${total_students}$ students, ${a_only + both}$ students play Cricket, ${b_only + both}$ play Football, and ${both}$ students play both games.\n\n{venn_svg}\nCalculate:\n1. How many students play Cricket only?\n2. How many students play Football only?\n3. How many students play neither sport?"
        options = []
        correct_answer = f"1) {a_only}, 2) {b_only}, 3) 5 students"
        solution = f"""**Step-by-Step Solution:**
1. Define the sets:
   - Let $C$ be the set of students playing Cricket: $|C| = {a_only + both}$
   - Let $F$ be the set of students playing Football: $|F| = {b_only + both}$
   - Students playing both sports: $|C \\cap F| = {both}$
   - Total students $|U| = {total_students}$
2. Calculate students playing Cricket only:
   $$|C - F| = |C| - |C \\cap F| = {a_only + both} - {both} = {a_only}$$
3. Calculate students playing Football only:
   $$|F - C| = |F| - |C \\cap F| = {b_only + both} - {both} = {b_only}$$
4. Calculate students playing at least one game:
   $$|C \\cup F| = |C| + |F| - |C \\cap F| = {a_only + both} + {b_only + both} - {both} = {a_only + b_only + both}$$
5. Calculate students playing neither sport:
   $$|U| - |C \\cup F| = {total_students} - {a_only + b_only + both} = 5$$
6. Answers: **(1) {a_only}**, **(2) {b_only}**, **(3) 5**."""

    # 7. Coordinate Geometry
    elif category == "coordinate_geometry":
        x1, y1 = 1, -3
        x2, y2 = 4, 6
        m, n = 2, 1
        px = (m * x2 + n * x1) / (m + n)
        py = (m * y2 + n * y1) / (m + n)
        q_text = f"Find the coordinates of the point $P(x, y)$ which divides the line segment joining the points $A({x1}, {y1})$ and $B({x2}, {y2})$ internally in the ratio ${m} : {n}$."
        options = []
        correct_answer = f"P({int(px)}, {int(py)})"
        solution = f"""**Step-by-Step Solution:**
1. Recall the Section Formula for internal division in ratio $m : n$:
   $$P(x, y) = \\left( \\frac{{m x_2 + n x_1}}{{m + n}}, \\frac{{m y_2 + n y_1}}{{m + n}} \\right)$$
2. Given values:
   - $(x_1, y_1) = ({x1}, {y1})$
   - $(x_2, y_2) = ({x2}, {y2})$
   - $m = {m}, n = {n}$
3. Calculate $x$-coordinate:
   $$x = \\frac{{{m}({x2}) + {n}({x1})}}{{{m} + {n}}} = \\frac{{{m*x2} + {n*x1}}}{{{m+n}}} = \\frac{{{m*x2 + n*x1}}}{{{m+n}}} = {int(px)}$$
4. Calculate $y$-coordinate:
   $$y = \\frac{{{m}({y2}) + {n}({y1})}}{{{m} + {n}}} = \\frac{{{m*y2} + {n*y1}}}{{{m+n}}} = \\frac{{{m*y2 + n*y1}}}{{{m+n}}} = {int(py)}$$
5. Hence, the coordinates of point $P$ are **$P({int(px)}, {int(py)})$**."""

    # 8. Surface Areas and Volumes
    elif category == "surface_volume":
        r_sph = 6
        r_cyl = 8
        vol_sph = (4/3) * math.pi * (r_sph**3)
        h_cyl = round((4 * (r_sph**3)) / (3 * (r_cyl**2)), 2)
        q_text = f"A solid metallic sphere of radius ${r_sph}\\text{{ cm}}$ is melted and recast into the shape of a solid cylinder of radius ${r_cyl}\\text{{ cm}}$. Find the height of the resulting cylinder."
        options = []
        correct_answer = f"{h_cyl} cm"
        solution = f"""**Step-by-Step Solution:**
1. Conservation of Volume Principle:
   $$\\text{{Volume of Cylinder}} = \\text{{Volume of Sphere}}$$
2. Formulae:
   - Volume of cylinder $= \\pi R^2 h$, where $R = {r_cyl}\\text{{ cm}}$
   - Volume of sphere $= \\frac{{4}}{{3}}\\pi r^3$, where $r = {r_sph}\\text{{ cm}}$
3. Equating the volumes:
   $$\\pi R^2 h = \\frac{{4}}{{3}}\\pi r^3 \\implies R^2 h = \\frac{{4}}{{3}}r^3$$
4. Substitute numerical values:
   $$({r_cyl})^2 \\times h = \\frac{{4}}{{3}} \\times ({r_sph})^3$$
   $$64 h = \\frac{{4}}{{3}} \\times 216 = 288 \\implies h = \\frac{{288}}{{64}} = {h_cyl}\\text{{ cm}}$$
5. The height of the cylinder is **${h_cyl}\\text{{ cm}}$**."""

    # 9. Real Numbers
    elif category == "real_numbers":
        num1, num2 = 306, 657
        hcf_val = 9
        lcm_val = (num1 * num2) // hcf_val
        q_text = f"Given that $\\text{{HCF}}({num1}, {num2}) = {hcf_val}$, find $\\text{{LCM}}({num1}, {num2})$ using the fundamental product relationship."
        options = []
        correct_answer = f"{lcm_val}"
        solution = f"""**Step-by-Step Solution:**
1. Fundamental theorem relation between two positive integers $a$ and $b$:
   $$\\text{{HCF}}(a, b) \\times \\text{{LCM}}(a, b) = a \\times b$$
2. Substitute the given values:
   $${hcf_val} \\times \\text{{LCM}}({num1}, {num2}) = {num1} \\times {num2}$$
3. Solve for LCM:
   $$\\text{{LCM}}({num1}, {num2}) = \\frac{{{num1} \\times {num2}}}{{{hcf_val}}} = \\frac{{{num1 * num2}}}{{{hcf_val}}} = {lcm_val}$$
4. Hence, the LCM is **${lcm_val}$**."""

    # 10. Probability & Statistics
    else:
        red, white, green = 5, 8, 4
        total_balls = red + white + green
        q_text = f"A box contains ${red}$ red balls, ${white}$ white balls, and ${green}$ green balls. One ball is drawn at random from the box. Find the probability that the ball drawn is:\n1. White\n2. Red or Green\n3. Not Red"
        options = []
        correct_answer = f"1) {white}/{total_balls}, 2) {red+green}/{total_balls}, 3) {white+green}/{total_balls}"
        solution = f"""**Step-by-Step Solution:**
1. Total number of elementary outcomes:
   $$n(S) = {red} + {white} + {green} = {total_balls}$$
2. (i) Probability of getting a white ball:
   $$P(\\text{{White}}) = \\frac{{n(\\text{{White}})}}{{n(S)}} = \\frac{{{white}}}{{{total_balls}}}$$
3. (ii) Probability of getting a red or green ball:
   $$n(\\text{{Red or Green}}) = {red} + {green} = {red + green}$$
   $$P(\\text{{Red or Green}}) = \\frac{{{red + green}}}{{{total_balls}}}$$
4. (iii) Probability of not getting a red ball:
   $$P(\\text{{Not Red}}) = 1 - P(\\text{{Red}}) = 1 - \\frac{{{red}}}{{{total_balls}}} = \\frac{{{white + green}}}{{{total_balls}}}$$
5. Final Answers: **$\\frac{{{white}}}{{{total_balls}}}$**, **$\\frac{{{red+green}}}{{{total_balls}}}$**, **$\\frac{{{white+green}}}{{{total_balls}}}$**."""

    return {
        "question_text": q_text,
        "question_type": q_type,
        "options": options,
        "correct_answer": correct_answer,
        "solution": solution
    }


def synthesize_science_question(
    index: int,
    subject: str,
    topic: Optional[str],
    difficulty: str,
    target_q_type: str,
    class_level: str
) -> Dict[str, Any]:
    """Generates authentic science numericals, chemical equations, and biological processes."""
    subj_lower = (subject or "").lower()
    
    if "physic" in subj_lower:
        # Physics numerical: Ohm's law or Lens formula
        v, r = random.choice([(12, 4), (220, 44), (9, 3), (24, 6)])
        i_curr = v / r
        q_text = f"A circuit carries an electric current connected to a ${v}\\text{{ V}}$ potential difference source across an unknown resistor of resistance $R$. If the measured current is $I = {i_curr}\\text{{ A}}$, calculate:\n1. The resistance $R$ of the resistor.\n2. The heat energy produced in the resistor in $2\\text{{ minutes}}$."
        h_heat = (i_curr**2) * r * 120
        options = []
        correct_answer = f"R = {r} Ω, Heat = {int(h_heat)} Joules"
        solution = f"""**Step-by-Step Solution:**
1. By Ohm's Law:
   $$V = I \\times R \\implies R = \\frac{{V}}{{I}} = \\frac{{{v}}}{{{i_curr}}} = {r}\\,\\Omega$$
2. Joule's Law of Heating:
   $$H = I^2 R t$$
   where time $t = 2\\text{{ minutes}} = 120\\text{{ seconds}}$.
   $$H = ({i_curr})^2 \\times {r} \\times 120 = {i_curr**2 * r} \\times 120 = {int(h_heat)}\\text{{ Joules}}$$
3. Answers: **$R = {r}\\,\\Omega$**, **$H = {int(h_heat)}\\text{{ J}}$**."""
    elif "chem" in subj_lower:
        # Chemistry balancing
        q_text = "Balance the following chemical equation and identify the type of chemical reaction:\n$$\\text{Fe} + \\text{H}_2\\text{O} \\to \\text{Fe}_3\\text{O}_4 + \\text{H}_2$$"
        options = []
        correct_answer = "3Fe + 4H2O -> Fe3O4 + 4H2 (Redox Reaction)"
        solution = """**Step-by-Step Solution:**
1. Unbalanced equation:
   $$\\text{Fe} + \\text{H}_2\\text{O} \\to \\text{Fe}_3\\text{O}_4 + \\text{H}_2$$
2. Balancing elements count:
   - Balance Fe atoms: Place 3 before Fe: $3\\text{Fe}$
   - Balance O atoms: Place 4 before $\\text{H}_2\\text{O}$ on LHS to match 4 in $\\text{Fe}_3\\text{O}_4$: $4\\text{H}_2\\text{O}$
   - Balance H atoms: RHS now has $4 \\times 2 = 8$ H atoms, so place 4 before $\\text{H}_2$: $4\\text{H}_2$
3. Balanced Chemical Equation:
   $$3\\text{Fe}_{(s)} + 4\\text{H}_2\\text{O}_{(g)} \\to \\text{Fe}_3\\text{O}_{4(s)} + 4\\text{H}_{2(g)}$$
4. Reaction Type: **Redox Reaction** (Iron is oxidized to $\\text{Fe}_3\\text{O}_4$, and water is reduced to $\\text{H}_2$)."""
    else:
        # General Science / Biology
        q_text = "Write the balanced chemical equation for the process of photosynthesis in green plants. Name the site of photosynthesis and state the three main events that occur during this process."
        options = []
        correct_answer = "6CO2 + 12H2O -> C6H12O6 + 6O2 + 6H2O"
        solution = """**Step-by-Step Solution:**
1. Balanced Chemical Equation for Photosynthesis:
   $$6\\text{CO}_2 + 12\\text{H}_2\\text{O} \\xrightarrow[\\text{Chlorophyll}]{\\text{Sunlight}} \\text{C}_6\\text{H}_{12}\\text{O}_6 + 6\\text{O}_2 + 6\\text{H}_2\\text{O}$$
2. Site of Photosynthesis: **Chloroplast** in green mesophyll cells of leaves.
3. Three Major Events:
   - Absorption of light energy by chlorophyll pigments.
   - Conversion of light energy to chemical energy and splitting of water molecules into hydrogen and oxygen (photolysis).
   - Reduction of carbon dioxide to carbohydrates (glucose)."""

    return {
        "question_text": q_text,
        "question_type": "short_answer",
        "options": options,
        "correct_answer": correct_answer,
        "solution": solution
    }


def synthesize_school_questions(
    school_name: str,
    class_level: str,
    subject: str,
    topic: Optional[str],
    difficulty: Optional[str],
    question_type: Optional[str],
    question_count: int,
    blueprint: dict,
    examples: list[dict]
) -> dict:
    """
    Main entry point for generating authentic questions matching the school pattern.
    Guarantees zero unwanted prefix tags ('[Navodaya Analytical Question]' removed).
    """
    questions = []
    subj_norm = (subject or "mathematics").lower()
    diff = difficulty or "medium"
    q_type_target = (question_type or "all").lower()

    for i in range(1, question_count + 1):
        if "math" in subj_norm:
            q_data = synthesize_math_question(
                index=i,
                topic=topic,
                difficulty=diff,
                target_q_type=q_type_target,
                class_level=class_level
            )
        else:
            q_data = synthesize_science_question(
                index=i,
                subject=subj_norm,
                topic=topic,
                difficulty=diff,
                target_q_type=q_type_target,
                class_level=class_level
            )
        questions.append(q_data)

    subject_title = subject.replace("_", " ").title() if subject and subject != "all" else "Mathematics"
    return {
        "title": f"{school_name} Examination Paper - Class {class_level} {subject_title}",
        "questions": questions
    }
