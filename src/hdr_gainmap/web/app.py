from pathlib import Path

from flask import Flask, render_template, request, send_file, jsonify
from werkzeug.utils import secure_filename
import uuid

from hdr_gainmap.main import run_sdr_hdr
from hdr_gainmap.preset import Preset

# Est-ceque c'est vraiment une bonne idée de mettre le dossier upload dans l'arborescence de l'app ?
# On pourrait le mettre dans le dossier courant
BASE_DIR = Path(__file__).parent
UPLOAD_FOLDER = BASE_DIR / "uploads"
UPLOAD_FOLDER.mkdir(exist_ok=True)

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        sdr_file = request.files.get("sdr")
        hdr_file = request.files.get("hdr")
        preset = request.form.get("preset", Preset.default)
        tag = request.form.get("tag") == "on"

        if not sdr_file or not hdr_file:
            return "Missing files", 400

        sdr_path = app.config["UPLOAD_FOLDER"] / secure_filename(sdr_file.filename)
        hdr_path = app.config["UPLOAD_FOLDER"] / secure_filename(hdr_file.filename)

        sdr_file.save(sdr_path)
        hdr_file.save(hdr_path)

        unique_id = uuid.uuid4().hex[:8]

        filename_path = Path(sdr_file.filename)
        output_filename = filename_path.with_stem(
            f"{filename_path.stem}_hdrgm_{unique_id}"
        )
        output_path = app.config["UPLOAD_FOLDER"] / output_filename

        preset_enum = Preset(preset)

        run_sdr_hdr(
            sdr_path=sdr_path,
            hdr_path=hdr_path,
            output_path=output_path,
            preset=preset_enum,
            tag=tag,
            keep_temp_files=False,
        )

        return jsonify({"image_url": f"/uploads/{output_filename}"})

    return render_template("index.html", presets=[p.name for p in Preset])


@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_file(app.config["UPLOAD_FOLDER"] / filename)


def run() -> None:
    app.run(debug=True)
