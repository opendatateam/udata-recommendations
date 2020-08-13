from flask import current_app

from .commands import process_sources

from udata.tasks import job


@job("add-recommendations")
def run_add_recommendations(self, should_clean=True):
    should_clean = should_clean in [True, 'true', 'True']
    sources = current_app.config.get('RECOMMENDATIONS_SOURCES', {})

    process_sources(sources, should_clean)
