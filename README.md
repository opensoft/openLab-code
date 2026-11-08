# openLab executable examples

Draft 0.1.0: synthetic requests and offline schema/file-integrity checks. No instrument operations, production transfer or scientific analysis is performed.

From the assembly root, using Python 3.10+:

```sh
python -m pip install -r code/requirements.txt
python code/tools/check_examples.py
python -m unittest discover -s code/tests -v
```

Set CONTRACTS_DIR or pass --contracts to the checker when using another checkout. Schemas are owned by openLab-spec; there is no private dependency and schema resolution is offline. Capability limits, authorization, expiration, idempotency and physical completion require a real host implementation.

Fixtures under examples/hplcms/raw/ are generated text data, not vendor files or measurements. The artifact manifest digest is SHA-256 of sorted file entries encoded as UTF-8 JSON with sorted keys and compact separators. The static checker reads whole files and is deliberately unsuitable for large concurrent production transfers.
