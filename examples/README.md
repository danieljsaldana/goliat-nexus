# Examples

**English** · [Español](README.es.md)

Start with `../environments/`, which contains commented common/dev/prod HCL files. `demo/` defines a separate evaluation installation. `shared.json` and `shared.auto.tfvars.json` remain supported generated formats without comments. They contain fictional identifiers and no secrets.

`make tfvars` synchronizes the native JSON. `./lz render --config environments --examples` generates automatic inputs for the five layers without accessing Azure. Do not edit internal contracts inside `.lz/`.
