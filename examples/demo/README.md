# Evaluation installation

**English** · [Español](README.es.md)

Deploy the demo to explore the product. Its three commented tfvars use `lzdemov1`, separate from the product example's `acmev1`, and `deploy_demo = true` to label the portals as evaluation. It deploys real Azure resources and incurs costs.

Use `./lz configure --demo --name my-demo-v1 --operator-ip '<IP>/32' --alert-email '<EMAIL>' --output-dir .local/demo`. Apply foundation and platform, followed by Dev/Prod and edge from the private executor. This demo's hub is shared by its own Dev/Prod, not another product installation. Never mix their states.

The `enable_*` switches work as in the product. Read the [manual](../../docs/FUNCIONAMIENTO.md) and [variables guide](../../docs/VARIABLES_Y_TFVARS.md) (Spanish). In-memory mode exists only for explicit local tests; the Azure demo uses Cosmos.
