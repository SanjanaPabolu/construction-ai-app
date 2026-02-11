import os
import base64
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet

app = Flask(__name__)

# ---------------- CONFIG ----------------
UPLOAD_FOLDER = "uploads"
PDF_FOLDER = "pdfs"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PDF_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# ---------------- ROUTES ----------------

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/analyze", methods=["POST"])
@app.route("/analyze", methods=["POST"])
def analyze():
    # ---------- READ INPUTS ----------
    area = float(request.form.get("area"))
    floors = request.form.get("floors")
    building_type = request.form.get("buildingType")
    budget = request.form.get("budget")
    days = request.form.get("days")
    lat = request.form.get("latitude")
    lon = request.form.get("longitude")

    # Save image
    image = request.files.get("land_image")
    filename = secure_filename(image.filename)
    image_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    image.save(image_path)

    # ---------- PARSE NUMBER OF FLOORS ----------
    num_floors = 1
    if "+" in floors:
        try:
            num_floors = int(floors.split("+")[1]) + 1
        except:
            num_floors = 1

    # ---------- STEP 1: REALISTIC BASE TIMELINE (WEEKS) ----------
    base_weeks_map = {
        "Residential": 14,   # for G only
        "Duplex": 18,
        "Villa": 20,
        "Apartment": 28,
        "Commercial": 24,
        "Office": 22,
        "Other": 16
    }

    base_weeks = base_weeks_map.get(building_type, 16)

    # Enforce realistic minimum for G+1 Residential
    if building_type == "Residential" and num_floors >= 2:
        base_weeks = 16  # 4 months minimum

    # Add extra time for additional floors
    extra_floor_weeks = max(0, (num_floors - 1) * 2)

    # Add extra time for larger land area
    extra_area_weeks = int(area / 500)

    normal_weeks = base_weeks + extra_floor_weeks + extra_area_weeks

    # ---------- STEP 2: HANDLE USER-REQUESTED DAYS (FAST-TRACK) ----------
    if days and days.strip() != "":
        requested_days = int(days)
        requested_weeks = max(1, requested_days // 7)

        # Minimum constraint for G+1 Residential
        if building_type == "Residential" and num_floors >= 2 and requested_weeks < 16:
            timeline = "16 weeks (minimum feasible for G+1 residential)"
            effective_weeks = 16
        else:
            timeline = f"{requested_days} days"
            effective_weeks = requested_weeks
    else:
        timeline = f"{normal_weeks} weeks"
        effective_weeks = normal_weeks

    # ---------- STEP 3: COST PER SQ YARD (REALISTIC BY TYPE) ----------
    cost_per_sq_yard_map = {
        "Residential": 4200,
        "Commercial": 5500,
        "Duplex": 4800,
        "Apartment": 5200,
        "Villa": 6000,
        "Office": 5800,
        "Other": 4500
    }

    base_rate = cost_per_sq_yard_map.get(building_type, 4500)

    # ---------- STEP 4: BASE BUDGET ----------
    estimated_budget = int(area * base_rate)

    # If user gave budget, respect it
    if budget and budget.strip() != "":
        estimated_budget = int(budget)

    # ---------- STEP 5: TIME–COST–LABOUR TRADEOFF (PROJECT CRASHING) ----------
    speed_factor = normal_weeks / effective_weeks  # >1 means fast-track

    # Increase cost if schedule is compressed
    cost_multiplier = 1 + (0.15 * (speed_factor - 1))
    estimated_budget = int(estimated_budget * cost_multiplier)

    # ---------- STEP 6: WORKER ESTIMATION (REALISTIC) ----------
    normal_workers = int((area / 120) + (num_floors * 6))
    workers = int(normal_workers * speed_factor)

    # ---------- STEP 7: BUDGET BREAKDOWN (REALISTIC SHARES) ----------
    if speed_factor > 1:   # fast-track project
        materials_share = 0.42
        labor_share = 0.45
        machinery_share = 0.18
        approvals_share = 0.06
    else:  # normal schedule
        materials_share = 0.45
        labor_share = 0.30
        machinery_share = 0.12
        approvals_share = 0.05

    materials_cost = int(estimated_budget * materials_share)
    labor_cost = int(estimated_budget * labor_share)
    machinery_cost = int(estimated_budget * machinery_share)
    approvals_cost = int(estimated_budget * approvals_share)

    # ---------- STEP 8: WORKER BREAKDOWN ----------
    workers_breakdown = [
        f"{max(5, int(area/300))} Masons",
        f"{max(4, int(area/400))} Laborers",
        f"{max(2, int(num_floors))} Engineers",
        "3 Electricians",
        "3 Plumbers",
        f"{max(2, int(speed_factor * 2))} Supervisors"
    ]

    # ---------- STEP 9: DYNAMIC WEEK-BY-WEEK PLAN ----------
    weekly_plan = []

    total_weeks = effective_weeks

    weekly_plan.append("Week 1–2: Site clearing, leveling, and marking")

    if total_weeks <= 12:  # very fast project
        weekly_plan.append("Week 2–3: Foundation (fast-track, ready-mix concrete)")
        weekly_plan.append("Week 4–5: Ground floor structure + columns")
        weekly_plan.append("Week 6: First floor slab (if applicable)")
        weekly_plan.append("Week 7: Roofing")
        weekly_plan.append("Week 8–10: Electrical, plumbing, plastering (parallel teams)")
        weekly_plan.append("Week 11–12: Painting, finishing, inspection")

    elif 12 < total_weeks <= 20:
        weekly_plan.append("Week 2–3: Foundation work")
        weekly_plan.append("Week 4–6: Ground floor structure")
        if num_floors > 1:
            weekly_plan.append("Week 7–9: First floor structure")
        weekly_plan.append("Week 10–12: Roofing")
        weekly_plan.append("Week 13–16: Electrical, plumbing, plastering")
        weekly_plan.append("Week 17–20: Painting, finishing, inspection")

    else:  # long projects (large apartments/commercial)
        weekly_plan.append("Week 2–4: Foundation & piling (if required)")
        weekly_plan.append("Week 5–8: Ground floor structure")
        if num_floors > 1:
            weekly_plan.append("Week 9–14: Upper floor structures")
        weekly_plan.append("Week 15–18: Roofing")
        weekly_plan.append("Week 19–26: Electrical, plumbing, plastering")
        weekly_plan.append("Final weeks: Painting, landscaping, inspection")

    # ---------- FINAL RESPONSE ----------
    result = {
        "timeline": timeline,
        "estimatedBudget": f"₹ {estimated_budget:,}",
        "workers": f"{workers} workers",
        "costPerYard": f"₹ {base_rate:,}",
        "weeklyPlan": weekly_plan,
        "monthlyPlan": [
            "Month 1: Foundation & Ground Floor",
            "Month 2: Upper floors & Roofing" if num_floors > 1 else "Month 2: Roofing",
            "Month 3–4: Interiors & Finishing"
        ],
        "budgetBreakdown": {
            "materials": f"₹ {materials_cost:,}",
            "labor": f"₹ {labor_cost:,}",
            "machinery": f"₹ {machinery_cost:,}",
            "approvals": f"₹ {approvals_cost:,}"
        },
        "workersBreakdown": workers_breakdown,
        "materials": [
            "Cement", "Steel", "Bricks", "Sand",
            "Tiles", "Paint", "Wiring", "Pipes",
            "Ready-mix concrete (if fast-track)"
        ],
        "assumptions": [
            "Clear land",
            "Stable soil",
            "Approved building plan",
            "No extreme weather delays",
            "Standard construction quality"
        ],
        "meta": {
            "area": area,
            "floors": floors,
            "buildingType": building_type,
            "latitude": lat,
            "longitude": lon,
            "imagePath": image_path
        }
    }

    return jsonify(result)

@app.route("/download_pdf", methods=["POST"])
def download_pdf():
    data = request.json

    pdf_path = os.path.join(PDF_FOLDER, "construction_plan.pdf")
    doc = SimpleDocTemplate(pdf_path)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("AI Construction Plan Report", styles["Title"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("📍 Site Details", styles["Heading2"]))
    story.append(Paragraph(f"Land Area: {data['meta']['area']} sq yards", styles["BodyText"]))
    story.append(Paragraph(f"Floors: {data['meta']['floors']}", styles["BodyText"]))
    story.append(Paragraph(f"Building Type: {data['meta']['buildingType']}", styles["BodyText"]))
    story.append(Paragraph(f"Coordinates: {data['meta']['latitude']}, {data['meta']['longitude']}", styles["BodyText"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("⏳ Timeline", styles["Heading2"]))
    story.append(Paragraph(data["timeline"], styles["BodyText"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("💰 Estimated Budget", styles["Heading2"]))
    story.append(Paragraph(data["estimatedBudget"], styles["BodyText"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("👷 Workers Needed", styles["Heading2"]))
    story.append(Paragraph(data["workers"], styles["BodyText"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("📅 Week-by-Week Plan", styles["Heading2"]))
    for w in data["weeklyPlan"]:
        story.append(Paragraph(f"• {w}", styles["BodyText"]))

    doc.build(story)
    return send_file(pdf_path, as_attachment=True, download_name="construction_plan.pdf")

# ---------------- RUN APP ----------------
if __name__ == "__main__":
    app.run(debug=True)
