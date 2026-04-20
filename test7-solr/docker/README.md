# Solr container

Single-node Solr 9 with one core: `exocortex`.

## Up / down

```bash
# start (detached)
docker compose up -d

# stop (keeps index data)
docker compose down

# wipe index + start fresh (deletes the volume)
docker compose down -v && docker compose up -d
```

## Verify

```bash
# admin UI
open http://localhost:8983/solr/

# ping the core
curl -s 'http://localhost:8983/solr/exocortex/admin/ping?wt=json' | jq .

# current schema fields
curl -s 'http://localhost:8983/solr/exocortex/schema/fields' | jq '.fields[].name'
```

## Notes

- Bootstraps from Solr's built-in `_default` configset. The custom schema for this
  project is applied by `../ingest/setup_schema.py` via the Schema API (idempotent).
- Index data is in the `solr_data` named volume. `docker compose down` keeps it;
  `docker compose down -v` deletes it.
- First boot takes ~15-20s while the core is precreated.
