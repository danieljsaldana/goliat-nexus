# Goliat - Nexus 1.0.0 — valores de ejemplo, no secretos.
# Edita tus copias en .local/; usa configure para completar identidades reales.

# Entorno dev: componentes opcionales y servicios propios. Comparte el hub definido en common.tfvars.
dev = {
  # Acceso de usuarios/grupos Entra: Requester solo ve sus datos; Operator opera el entorno.
  access = {
    # Object IDs de operadores. Vacío usa operator_object_id de common, que debe ser usuario/grupo para esta asignación.
    operator_object_ids = []

    # Object IDs de usuarios/grupos con rol Requester y acceso al portal. Vacío: no hay solicitantes adicionales.
    requester_object_ids = []
  }

  # Excepciones HTTPS de este entorno; evita comodines amplios.
  additional_https_fqdns = []

  # Cosmos DB API MongoDB 7.0. Configura capacidad, región y política de backup.
  cosmosdb_config = {
    # Backup periódico: 60–1440 minutos. No equivale a restauración continua/PITR.
    backup_interval_minutes = 240

    # Horas de conservación: al menos dos intervalos y como máximo 720 horas.
    backup_retention_hours = 8

    # Redundancia del backup: Local, Zone o Geo. Revisar coste y necesidades de recuperación.
    backup_storage_redundancy = "Local"

    # Nombre lógico de la base MongoDB; se crean colecciones de solicitudes y actividades.
    database_name = "requests"

    # Solo una cuenta elegible por suscripción, y nunca en Serverless. Se desactiva por defecto.
    free_tier_enabled = false

    # true: pago por consumo, sin throughput reservado. No admite Free Tier.
    is_serverless = true

    # Región principal de Azure. Valida disponibilidad de Cosmos, Container Apps y Functions Flex.
    location = null

    # Máximo RU/s de autoscale, múltiplo de 1000; null para manual o Serverless.
    max_throughput = null

    # Versión de compatibilidad MongoDB validada por esta versión del producto.
    mongo_server_version = "7.0"

    # RU/s manuales (mínimo 400). null para Serverless o autoscale.
    throughput = null
  }

  # Etiqueta los portales como evaluación. No cambia a datos en memoria; las piezas se activan con enable_*.
  deploy_demo = false

  # API de lectura de actividades generadas por la Function.
  enable_api_activities = true

  # API de configuración y catálogo del portal, detrás del gateway privado.
  enable_api_platform = true

  # API de solicitudes: persiste en Cosmos y publica eventos.
  enable_api_tenant = true

  # Storage separado para adjuntos/contenido, con lifecycle solo en esos datos.
  enable_content_storage = true

  # Cuenta y base MongoDB de Cosmos con acceso privado; exige Key Vault.
  enable_cosmosdb = true

  # Gestionar los registros DNS públicos opcionales. El DNS privado de la plataforma sigue siendo necesario.
  enable_dns = true

  # Topic Event Grid publicador opcional; requiere API tenant y eventos. Sin clave local ni suscripciones automáticas.
  enable_event_grid = false

  # Function que consume la cola de solicitudes; requiere Storage, Cosmos y Key Vault.
  enable_event_processing = true

  # Vault privado por entorno. Necesario para Cosmos, Functions y tokens de despliegue web.
  enable_key_vault = true

  # Storage privado para paquetes, host de Functions y colas de eventos; autenticación Entra.
  enable_storage_account = true

  # Functions Flex Consumption: procesamiento asíncrono, reintentos y recuperación del outbox.
  functions = {
    # Límite máximo de escala de Functions Flex (40–1000), no instancias siempre encendidas.
    maximum_instances = 40

    # Memoria por instancia Flex: 512, 2048 o 4096 MiB.
    memory_mb = 2048

    # Versión Node.js del código de eventos suministrado (24).
    runtime_version = "24"
  }

  # Environment GitHub autorizado; usa subjects diferentes en Dev y Prod.
  github_environment = "dev"

  # Repositorio organización/nombre para OIDC; vacío desactiva el publicador opcional.
  github_repository = ""

  # Plan IP: los rangos no pueden solaparse; no reutilices subredes para servicios distintos.
  network = {
    # Subred delegada de Container Apps, al menos /23.
    apps_subnet_cidr = "10.10.0.0/23"

    # Private Endpoints del entorno: Key Vault, Cosmos, Storage y servicios de aplicación.
    data_subnet_cidr = "10.10.2.0/27"

    # Integración de Functions Flex, al menos /27. No puede compartirse con Container Apps.
    functions_subnet_cidr = "10.10.3.0/27"

    # VNet propia del entorno, emparejada únicamente con el hub.
    vnet_cidr = "10.10.0.0/16"
  }

  # DNS propio opcional. Por defecto zone_name vacío: nombres Azure, sin comprar dominio ni crear zona pública.
  public_dns = {
    # true crea la zona; false utiliza una existente cuando zone_name no está vacío.
    create_zone = false

    # Vacío usa nombres Azure. Para DNS propio indica una zona de tu propiedad; vinculación y certificado se configuran aparte.
    zone_name = ""
  }

  # Capacidad de las APIs y gateway del portal de ejemplo. Ajustar tras medir la carga.
  sample = {
    # Máximo de réplicas por API habilitada.
    api_max_replicas = 3

    # Mínimo de réplicas por API habilitada.
    api_min_replicas = 0

    # Puerto interno de cada API Node.js.
    api_port = 8000

    # vCPU por réplica Consumption; debe corresponder con memory.
    cpu = 0.25

    # Máximo de réplicas del gateway.
    frontend_max_replicas = 2

    # Mínimo de réplicas del gateway web privado.
    frontend_min_replicas = 0

    # Puerto interno del gateway Nginx.
    frontend_port = 8080

    # Concurrencia objetivo de la regla HTTP; no es una garantía de rendimiento.
    http_concurrency = 50

    # Memoria por réplica: 0.5Gi con 0.25 vCPU, por ejemplo.
    memory = "0.5Gi"

    # Versión lógica del código. El despliegue utiliza imágenes por digest inmutable.
    version = "1.0.0"
  }

  # Ajustes de las cuentas privadas del entorno; sin claves en estos tfvars.
  storage = {
    # Mover adjuntos inactivos a Cool. No se aplica a paquetes ni al estado del host Functions.
    content_cool_after_days = 30

    # Replicación Storage: LRS, ZRS o GRS.
    replication = "LRS"

    # Días de borrado reversible de blobs y contenedores.
    soft_delete_days = 14
  }

  # Static Web Apps. El contenido web es público; el gateway y los datos permanecen privados.
  web = {
    # Región principal de Azure. Valida disponibilidad de Cosmos, Container Apps y Functions Flex.
    location = "westeurope"

    # Free o Standard. Comprueba cuotas de webs por suscripción antes de habilitar todos los portales.
    sku = "Standard"
  }

  # Un Static Web App por entrada. Clave libre de 1–30 caracteres; añade entradas para más portales, o usa {} para ninguno.
  web_portals = {
    admin = {
      # Interfaz del ejemplo: tenant para solicitudes, admin para operaciones. No concede permisos Entra.
      view = "admin"
    }
    tenant = {
      # Interfaz del ejemplo: tenant para solicitudes, admin para operaciones. No concede permisos Entra.
      view = "tenant"
    }
  }

  # Redundancia zonal de Container Apps. No activa multirregión de Cosmos.
  zone_redundancy = false
}
