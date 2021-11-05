import datetime
import json
from dataclasses import dataclass
from typing import List

from flask import abort, render_template, request, Blueprint

from formie.models import db, Field, ChoiceField, Form, TextField

bp = Blueprint("forms", __name__, url_prefix="/forms")


def decode_fields(data: str) -> List[Field]:
    fields: List[Field] = []
    for elem in data:
        if "name" not in elem:
            raise ValueError("invalid format")
        if len(elem["name"]) > 256:
            raise ValueError("invalid value")

        if elem["type"] == "text":
            del elem["type"]
            if len(elem) != 2:
                raise ValueError("invalid format")
            if len(elem["default"]) > 1024:
                raise ValueError("invalid value")

            fields.append(TextField(**elem))
        elif elem["type"] == "choice":
            del elem["type"]

            fields.append(ChoiceField(**elem))
        else:
            raise ValueError("invalid format")
    return fields


def create_model(name: str, fields: List[Field]):
    cols = {"id": db.Column(db.Integer, primary_key=True)}
    for i, field in enumerate(fields):
        if isinstance(field, TextField):
            col = db.Column(db.Text, default=field.default)
        elif isinstance(field, ChoiceField):
            col = db.Column(db.Integer, default=field.default)
        cols[f"col{i}"] = col
    return type(name, (db.Model,), cols)


@bp.route("/new", methods=("GET", "POST"))
def new_form():
    if request.method == "POST":
        schema = request.json

        error = None
        try:
            fields = decode_fields(schema)
            form = Form(schema=json.dumps(schema), created_at=datetime.datetime.now())
            db.session.add(form)
            db.session.commit()
            create_model(str(form.id), fields).__table__.create(db.engine)
        except Exception as e:
            raise e
            abort(401)
        db.session.commit()

        return render_template("forms/creation_successful.html")
    return render_template("forms/new.html")


@bp.route("/<int:form_id>", methods=("GET", "POST"))
def form(form_id: int):
    form = Form.query.filter_by(id=form_id).first()
    if form is None:
        abort(404)

    # TODO: json getting deserialized twice here
    model = create_model(str(form.id), decode_fields(form.schema))

    if request.method == "POST":
        db.session.add(model(**request.form))
        db.session.commit()

    return render_template("forms/form.html", schema=json.loads(form.schema))


@bp.route("/<int:form_id>/view")
def view_form(form_id: int):
    form = Form.query.filter_by(id=form_id).first()
    if form is None:
        abort(404)

    # TODO: json getting deserialized twice here
    model = create_model(str(form.id), decode_fields(form.schema))

    return render_template(
        "forms/view.html", schema=json.loads(form.schema), results=model.query.all()
    )
