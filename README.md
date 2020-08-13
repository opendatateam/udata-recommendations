# udata-recommendations

This plugin acts as a bridge between uData and a recommendation system.

In our case ([data.gouv.fr][]), it's a set of scripts living here https://github.com/etalab/piwik-covisits.

Recommendations are stored on datasets. Recommendations can come from various sources and are stored in a descending order, according to the provided score (from 1 to 100). The top recommendations are displayed at the bottom on the dataset page.

## Compatibility

**udata-recommendations** requires Python 3.7+ and [uData][].

## Installation

Install [uData][].

Remain in the same virtual environment (for Python).

Install **udata-recommendations**:

```shell
pip install udata-recommendations
```

Modify your local configuration file of **udata** (typically, `udata.cfg`) as following:

```python
PLUGINS = ['recommendations']
RECOMMENDATIONS_SOURCES = {
    'source-name': 'https://path/to/recommendations.json',
    'other-source': 'https://path/to/other/recommendations.json',
}
RECOMMENDATIONS_NB_RECOMMENDATIONS = 4
```

- `RECOMMENDATIONS_SOURCES`: A key-value dictionary of recommendation sources and URLs to fetch. _Default_: `{}`
- `RECOMMENDATIONS_NB_RECOMMENDATIONS`: The maximum number of recommendations to display on the dataset page. _Default_: `4`

## Usage

### Adding recommendations

You can fetch and store recommendations from your configuration by running the following command.

```shell
udata recommendations add
```

You can also specify a source and a URL to import one-off recommendations.

```shell
udata recommendations add --url https://example.com/recommendations.json --source my-source
```

**Cleaning recommendations before import**

If you want to clean recommendations before importing new ones, you can add the `--clean` flag to your commands.

```shell
udata recommendations add --clean
udata recommendations add --url https://example.com/recommendations.json --source my-source --clean
```

### Deleting recommendations

You can delete recommendations made by a specific source through a command.

```shell
udata recommendations clean my-source
```

This command will delete recommendations coming from the source `my-source`. If you want to clean multiple sources, you can run multiple times this command.

## Expectations

This plugin expects the following format to provide datasets recommendations:

```json
[
  {
    "id": "dataset-id",
    "recommendations": [
      {
        "id": "dataset-slug-1",
        "score": 100
      },
      {
        "id": "5ef1fe80f50446b8f41ba691",
        "score": 1
      }
    ]
  },
  {
    "id": "dataset-id2",
    "recommendations": [
      {
        "id": "5ef1fe80f50446b8f41ba691",
        "score": 50
      }
    ]
  }
]
```

Dataset IDs can be IDs or slugs. Scores should be between `1` and `100`, inclusive. You can validate your JSON using a [JSON Schema](udata_recommendations/schema.json).

[uData]: https://github.com/opendatateam/udata
[data.gouv.fr]: https://data.gouv.fr
