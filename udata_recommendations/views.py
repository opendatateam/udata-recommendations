# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import render_template, Blueprint

from udata.frontend import template_hook

blueprint = Blueprint('recommendations', __name__, template_folder='templates')


@template_hook
def dataset_recommendations(recommendations):
    return render_template('dataset-recommendations.html',
                           recommendations=recommendations)
