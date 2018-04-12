# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import Blueprint

from udata import theme

from udata.core.dataset.models import Dataset
from udata.frontend import template_hook

blueprint = Blueprint('recommendations', __name__, template_folder='templates')


@template_hook
def dataset_recommendations(reco_ids):
    recommendations = Dataset.objects.filter(id__in=reco_ids)
    return theme.render('dataset-recommendations.html',
                        recommendations=recommendations)
