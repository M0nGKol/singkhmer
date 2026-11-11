# Data license

The **code** in this repository is MIT-licensed (see `LICENSE`).

The **annotations and data created in this project** (seed word list, drafted and
verified sentence pairs, the test set, survey results) are released under
[Creative Commons Attribution 4.0 (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/).

Third-party material keeps its own license and must be credited:

| Source | License | How it is used |
| --- | --- | --- |
| [Khmer Wikipedia](https://km.wikipedia.org) via [wikimedia/wikipedia](https://huggingface.co/datasets/wikimedia/wikipedia) | CC BY-SA 4.0 | Word frequencies and source sentences for synthetic pairs |
| [FineWeb-2](https://huggingface.co/datasets/HuggingFaceFW/fineweb-2) (`khm_Khmr`) | ODC-By 1.0, plus Common Crawl terms of use | Word frequencies and source sentences for synthetic pairs |

Because synthetic pairs are derived from Wikipedia and FineWeb-2 sentences, any released
file that contains those sentences is distributed under **CC BY-SA 4.0**, with FineWeb-2
(ODC-By 1.0) credited as a source. Keep synthetic files and
human-annotated files separate in releases so each carries the right license.

Before releasing any real user text (public comments, donated chats), read
[`docs/DATA_COLLECTION.md`](docs/DATA_COLLECTION.md#privacy-and-consent).
