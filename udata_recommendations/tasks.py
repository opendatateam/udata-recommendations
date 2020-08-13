from flask import current_app

from udata.tasks import job

from .commands import process_sources, log as commands_log


log = commands_log


@job("add-recommendations")
def run_add_recommendations(self, should_clean=True):
    should_clean = should_clean in [True, 'true', 'True']
    sources = current_app.config.get('RECOMMENDATIONS_SOURCES', {})

    process_sources(sources, should_clean)
