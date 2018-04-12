# udata-recommendations

This plugin acts as a bridge between uData and a recommendation system.

In our case ([data.gouv.fr][]), it's a set of scripts living here https://github.com/etalab/datasets_reco.

## Compatibility

**udata-recommendations** requires Python 2.7+ and [uData][].

## Installation

Install [uData][].

Remain in the same virtual environment (for Python) and use the same version of npm (for JS).

Install **udata-recommendations**:

```shell
pip install udata-recommendations
```

Modify your local configuration file of **udata** (typically, `udata.cfg`) as following:

```python
PLUGINS = ['recommendations']
RECOMMENDATIONS_DATASETS_SOURCE_URL = 'http://path/to/recommendations.json'
```

Then run the command to fetch recommendations:

```shell
udata recommendations fill_for_datasets
```

## Expectations

This plugin expects the following format to provide datasets recommendations:

```json
{
    "id": "dataset-id",
    "recommendations": [
        {
            "id": "dataset-recommended-1"
        },
        {
            "id": "dataset-recommended-2"
        }
    ]
}
```

[uData]: https://github.com/opendatateam/udata
[data.gouv.fr]: https://data.gouv.fr
