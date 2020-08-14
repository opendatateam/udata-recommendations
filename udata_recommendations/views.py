from flask import Blueprint, current_app

from udata import theme

from udata.core.dataset.models import Dataset
from udata.frontend import template_hook

blueprint = Blueprint('recommendations', __name__, template_folder='templates')


def has_recommendations(ctx):
    dataset = ctx['dataset']
    return dataset and dataset.extras.get('recommendations', [])


@template_hook('dataset.display.after-description', when=has_recommendations)
def dataset_recommendations(ctx):
    reco_ids = []
    recommendations = ctx['dataset'].extras['recommendations']

    # Get at most n unique recommendations
    # Recommendations are already sorted by score in desc order
    limit = current_app.config.get('RECOMMENDATIONS_NB_RECOMMENDATIONS')
    # Ordered sets don't exist but dicts are ordered since 3.7
    # https://stackoverflow.com/a/51145737
    reco_ids = list({r['id']: 0 for r in recommendations})[:limit]

    return theme.render(
        'dataset-recommendations.html',
        recommendations=Dataset.objects.filter(id__in=reco_ids)
    )
