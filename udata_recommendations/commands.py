# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

import click
import mongoengine
import requests

from flask import current_app

from udata.commands import cli, success, exit_with_error, error
from udata.core.dataset.models import Dataset

log = logging.getLogger(__name__)


@cli.group()
def recommendations():
    '''Recommendations related operations'''
    pass


def clean_datasets_recommendations():
    log.info('Cleaning up dataset recommendations...')
    datasets = Dataset.objects.filter(**{
        'extras__recommendations__exists': True,
    }).update(**{
        'unset__extras__recommendations': True,
    })
    success('Cleaned up %s dataset(s).' % datasets)


def get_datasets_data(url):
    try:
        r = requests.get(url)
    except requests.exceptions.ConnectionError:
        exit_with_error('ConnectionError when trying to reach source.')
    if not r.status_code == requests.codes.ok:
        exit_with_error('Bad response from source (%s).' % r.status_code)
    try:
        data = r.json()
    except ValueError:
        exit_with_error('Bad response from source, expecting valid JSON.')
    if not isinstance(data, list):
        exit_with_error('Bad response from source, expecting JSON list.')
    return data


def get_dataset(id_or_slug):
    obj = Dataset.objects(slug=id_or_slug).first()
    return obj or Dataset.objects.get(id=id_or_slug)


def process_dataset(idx, dataset):
    if 'id' not in dataset or 'recommendations' not in dataset:
        error(' '.join(('Bad response from source for item #%s,',
                        'expecting id and recommendations attributes.'))
              % idx)
        return 0
    try:
        dataset_obj = get_dataset(dataset['id'])
    except (Dataset.DoesNotExist, mongoengine.errors.ValidationError):
        error('Dataset %s not found' % dataset['id'])
        return 0
    log.info('Processing recommendations for dataset %s.' % dataset['id'])
    valid_recos = []
    for reco in dataset['recommendations']:
        try:
            reco_dataset_obj = get_dataset(reco['id'])
            valid_recos.append(str(reco_dataset_obj.id))
        except (Dataset.DoesNotExist, mongoengine.errors.ValidationError):
            error('Recommended dataset %s not found' % reco['id'])
            continue
    if len(valid_recos):
        success('Found %s recommendations for dataset %s.' % (
                 len(valid_recos), dataset['id']))
        dataset_obj.extras['recommendations'] = valid_recos
        dataset_obj.save()
    else:
        error('No recommendation found for dataset %s' % dataset['id'])
        return 0
    return 1


@recommendations.command()
@click.option('-s', '--source', default=None,
              help='The source URL to get recommendations from')
@click.option('-c', '--clean', is_flag=True, default=True,
              help='Cleanup existing recommendations')
def datasets(source, clean):
    if clean:
        clean_datasets_recommendations()
    nb_datasets = 0
    url = source or current_app.config.get(
        'RECOMMENDATIONS_DATASETS_SOURCE_URL')
    if not url:
        exit_with_error('Not source url set, aborting.')
    log.info('Fetching dataset recommendations from %s...', url)
    data = get_datasets_data(url)
    for idx, dataset in enumerate(data):
        nb_datasets += process_dataset(idx, dataset)
    success('Dataset recommendations filled for %s dataset(s).' % nb_datasets)
