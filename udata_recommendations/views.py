from flask import Blueprint

from udata import theme

from udata.core.dataset.models import Dataset
from udata.frontend import template_hook

blueprint = Blueprint('recommendations', __name__, template_folder='templates')


def has_recommendations(ctx):
    dataset = ctx['dataset']
    return 'recommendations' in dataset.extras and len(dataset.extras['recommendations'])


@template_hook('dataset.display.after-description', when=has_recommendations)
def dataset_recommendations(ctx):
    reco_ids = ctx['dataset'].extras['recommendations']
    recommendations = Dataset.objects.filter(id__in=reco_ids)
    return theme.render('dataset-recommendations.html',
                        recommendations=recommendations)
