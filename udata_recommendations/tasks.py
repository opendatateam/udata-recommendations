import logging
import json
import importlib.resources as pkg_resources

import mongoengine
import requests
import jsonschema
from flask import current_app

from udata.models import Dataset, Reuse

from udata.tasks import job
from udata.commands import success, error

log = logging.getLogger(__name__)


def recommendations_clean():
    nb_datasets = Dataset.objects.filter(**{
        'extras__recommendations__exists': True,
    }).update(**{
        'unset__extras__recommendations': True,
        'unset__extras__recommendations-reuses': True,
        'unset__extras__recommendations:sources': True,
    })
    success(f"Removed recommendations from {nb_datasets} dataset(s)")


def get_recommendations_data(url):
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()

    with pkg_resources.path('udata_recommendations', 'schema.json') as schema_path:
        with open(schema_path) as f:
            schema = json.load(f)
        jsonschema.validate(instance=data, schema=schema)

    return data


def get_dataset(id_or_slug):
    obj = Dataset.objects(slug=id_or_slug).first()
    return obj or Dataset.objects.get(id=id_or_slug)


def get_reuse(id_or_slug):
    obj = Reuse.objects(slug=id_or_slug).first()
    return obj or Reuse.objects.get(id=id_or_slug)


def process_source(source, recommendations_data):
    for dataset in recommendations_data:
        process_dataset(source, dataset)


def process_dataset(source, dataset):
    try:
        target_dataset = get_dataset(dataset['id'])
    except (Dataset.DoesNotExist, mongoengine.errors.ValidationError):
        error(f"Dataset {dataset['id']} not found")
        return

    log.info(f"Processing recommendations for dataset {dataset['id']}")
    valid_recos_datasets = []
    valid_recos_reuses = []
    for reco in dataset['recommendations']:
        # default type is `dataset` for retrocompat
        reco_type = reco.get('type', 'dataset')
        if reco_type == 'dataset':
            try:
                reco_dataset_obj = get_dataset(reco['id'])
                if reco_dataset_obj.id == target_dataset.id:
                    continue
                valid_recos_datasets.append({
                    'id': str(reco_dataset_obj.id),
                    'score': reco['score'],
                    'source': source,
                })
            except (Dataset.DoesNotExist, mongoengine.errors.ValidationError):
                error(f"Recommended dataset {reco['id']} not found")
                continue
        elif reco_type == 'reuse':
            try:
                reuse = get_reuse(reco['id'])
                valid_recos_reuses.append({
                    'id': str(reuse.id),
                    'score': reco['score'],
                    'source': source,
                })
            except (Reuse.DoesNotExist, mongoengine.errors.ValidationError):
                error(f"Recommended reuse {reco['id']} not found")
                continue
        else:
            error(f'Unknown recommendation type {reco_type}')
            continue

    if len(valid_recos_datasets) or len(valid_recos_reuses):
        new_sources = set(target_dataset.extras.get('recommendations:sources', []))
        new_sources.add(source)
        target_dataset.extras['recommendations:sources'] = list(new_sources)

    if len(valid_recos_datasets):
        success(f"Found {len(valid_recos_datasets)} new dataset recommendations for dataset {dataset['id']}")

        merged_recommendations = target_dataset.extras.get('recommendations', [])
        merged_recommendations.extend(valid_recos_datasets)
        new_recommendations = sorted(merged_recommendations, key=lambda k: k['score'], reverse=True)

        target_dataset.extras['recommendations'] = new_recommendations

    if len(valid_recos_reuses):
        success(f"Found {len(valid_recos_reuses)} new reuse recommendations for dataset {dataset['id']}")

        merged_recommendations = target_dataset.extras.get('recommendations-reuses', [])
        merged_recommendations.extend(valid_recos_reuses)
        new_recommendations = sorted(merged_recommendations, key=lambda k: k['score'], reverse=True)

        target_dataset.extras['recommendations-reuses'] = new_recommendations

    if len(valid_recos_datasets) or len(valid_recos_reuses):
        target_dataset.save()
    else:
        error(f"No recommendations found for dataset {dataset['id']}")


def recommendations_add(sources, should_clean):
    if should_clean:
        log.info('Cleaning up dataset recommendations')
        recommendations_clean()

    for source, url in sources.items():
        log.info(f'Fetching dataset recommendations from {url}, source {source}')
        process_source(source, get_recommendations_data(url))


@job("recommendations-clean")
def run_recommendations_clean(self):
    recommendations_clean()


@job("recommendations-add")
def run_recommendations_add(self, should_clean=True):
    should_clean = should_clean in [True, 'true', 'True']
    sources = current_app.config.get('RECOMMENDATIONS_SOURCES', {})

    recommendations_add(sources, should_clean)
