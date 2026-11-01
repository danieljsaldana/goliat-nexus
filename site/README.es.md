# Web de Goliat - Nexus

[English](README.md) · **Español**

Web de producto basada en el lenguaje visual de `goliat-cloud-inventory`: DM Sans local, blanco y azul, presentación del producto, ES/EN y el mismo visor interactivo Archify. El contenido y los diagramas representan los módulos de Goliat - Nexus.

## Ejecutar

Desde la raíz de `prod`, con Python 3.10+ y Node.js 24+:

```bash
make site
make site-check
python3 -m http.server 8765 --bind 127.0.0.1 --directory dist
```

Abre `http://127.0.0.1:8765/`. También puedes usar `make site-serve` para generar y servir en un solo paso. La web final es estática; no necesita Node, una base de datos o credenciales de Azure para funcionar en el alojamiento.

## Contenido e interacciones

- Presentación de la solución con explorador interactivo: plataforma compartida, entrada web y eventos. Los recorridos se repiten automáticamente con una pausa de 2,5 segundos; se detienen fuera de pantalla, en pestañas ocultas o con movimiento reducido. Muestran relaciones conceptuales; no consultan Azure.
- Componentes y límites del producto, con comparación de capacidad Dev/Prod desplegable.
- Idiomas ES/EN con preferencia local opcional.
- Cuatro diagramas: arquitectura hub & spokes (inicial), red y seguridad, aplicación y eventos, y despliegue por capas. La arquitectura compacta sitúa el hub compartido entre Dev y Prod. El detalle de recursos se conserva en la tabla de inventario y en la documentación.
- Archify con zoom, selección de componentes, búsqueda, rutas y exportación.
- Entornos Dev/Prod con comandos actualizados, copia y enlaces a los tfvars comentados de GitHub.
- Documentación HTML y archivos de configuración legibles por separado, sin ZIP.
- Diseño responsive y respeto a la preferencia de movimiento reducido.

El visor y las etiquetas de los diagramas se muestran en español, como indica la web. La configuración del producto está en environments/: common.tfvars, dev.tfvars, prod.tfvars y ambos README. La demo de evaluación utiliza examples/demo/. Todo el código se versiona en Git; la web no genera ZIP. La [guía de variables](../docs/VARIABLES_Y_TFVARS.md) explica ambos usos. Los JSON de ejemplo proceden de `examples/`; el sitio no inventa configuraciones alternativas ni ejecuta Terraform en el navegador.

## Archivos

| Archivo | Propósito |
| --- | --- |
| `index.html` | Contenido y estructura |
| `styles.css` | Estilos, iconos y adaptación responsive |
| `app.js` | Idiomas, entornos, copia y cambio de diagrama |
| `diagram-viewer.js` | Carga independiente de diagramas, validación, límite de tiempo y reintento |
| `github.js` | Contador de estrellas mediante metadatos públicos de GitHub, sin credenciales |
| `content/architecture-explorer.js` | Textos y recorridos ES/EN del explorador de portada |
| `lab.js` | Simulación paso a paso, fallo de publicación, recuperación y repetición de eventos, sin contactar con Azure |
| `diagrams/overview.json` | Arquitectura compacta del hub compartido y de las aplicaciones de Dev/Prod |
| `diagrams/network.json` | Subredes, rutas, endpoints privados y seguridad |
| `diagrams/application.json` | Frontend, backend, Entra y procesamiento de eventos |
| `diagrams/deployment.json` | Dependencias de Foundation, Platform, Dev, Prod y Edge |
| `vendor/archify` | Runtime de Archify y licencias conservadas |
| `../scripts/build_site.py` | Generación de diagramas, documentos y `dist/` |
| `../scripts/check_site.py` | Comprobación de enlaces, anclas, perfiles y fuentes |

Los diagramas son de referencia y no consultan Azure. La web no almacena UUID, credenciales ni configuraciones del visitante. Los valores ficticios de ejemplo requieren sustitución antes de utilizar el CLI.

## Rutas de previsualización

`make site` prepara dos formas de servir la misma web: `dist/` como raíz, y `/site/index.html` al servir la raíz del repositorio. Los HTML de Archify y documentos se copian a `site/` como archivos generados e ignorados por Git. El artefacto publicado también incluye `/site/` para conservar enlaces de esa vista.

Los diagramas se resuelven respecto al módulo JavaScript, no mediante una ruta absoluta a una raíz concreta. El visor funciona independientemente de las peticiones de configuración y GitHub. Comprueba que el HTML contiene un diagrama, detecta respuestas 404 o páginas genéricas y ofrece un mensaje y reintento si falla la carga o vence su límite de tiempo. Muestra un estado de carga y evita reutilizar HTML antiguo de los diagramas. `make site-check` comprueba las tres entradas: `dist/`, `dist/site/` y `site/`.

Después de clonar o modificar el contenido hay que ejecutar `make site`. Abrir una copia fuente sin generar los artefactos no sustituye ese paso.

La identidad de alojamiento Sites está en `.openai/hosting.json`, en la raíz. El mismo `project_id` se conserva en las siguientes publicaciones. No se incluye ese archivo en la web ni en el checkout público de GitHub.

## Referencia y licencia

Referencia visual: `goliat-cloud-inventory` en el commit `c456aa3d33169261e257506ff997dc42b49b4180`. Se reutilizan el símbolo Azure, el logotipo de GitHub, las fuentes locales y el runtime Archify 3.0.1 con sus avisos. Los iconos de interfaz usan Lucide 1.66.0 y conservan sus licencias ISC/MIT en `assets/Lucide-LICENSE.txt`. Consulta [NOTICE.md](NOTICE.md), `REFERENCE-LICENSE` y `vendor/archify/THIRD_PARTY_NOTICES.md`.

## Enlace a GitHub y estrellas

Los enlaces apuntan al repositorio definido en `content/project.json`. El contador muestra primero el dato verificado de `content/github-stars.json`, incluido un cero real. Su tooltip indica la fecha de comprobación. Después consulta `GET https://api.github.com/repos/{owner}/{repo}` sin token, cookies ni cabecera de autorización; los metadatos públicos válidos sustituyen ese dato.

Si el repositorio sigue privado, no existe, falla la red o se alcanza el límite de la API, se conserva el último valor verificado con su fecha original. Se rechazan capturas de metadatos inválidas o de otro repositorio. Si ninguna fuente está disponible, se mantiene el enlace sin inventar un contador. Actualiza el dato desde la raíz con `make github-stars`, usando tu sesión de GitHub CLI, y reconstruye la web con `make site`. Solo se guardan la URL del repositorio, el número y la fecha; no se publican credenciales.

El navegador conserva los metadatos de la API pública en `sessionStorage` durante 15 minutos (5 minutos tras un fallo). La petición tiene un límite de 4 segundos. El sitio y sus diagramas funcionan aunque GitHub no responda. Generar la web no modifica la visibilidad del repositorio ni sube código.

## Biblioteca de iconos local

`content/icons.json` selecciona 25 iconos de la versión fijada de `lucide-static`. Ejecuta `npm ci` y `npm run icons` para regenerar `assets/icons.svg` y su licencia. El sprite se versiona, por lo que generar la web normalmente no necesita un CDN de iconos ni instalar dependencias npm. Los controles estáticos y las tarjetas dinámicas del catálogo usan el mismo sprite. Azure y GitHub conservan sus marcas; las conexiones de los diagramas son geometría SVG independiente.

Comportamiento conforme a la [API de repositorios](https://docs.github.com/en/rest/repos/repos#get-a-repository) y sus [límites de acceso público](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api).

## Metadatos al compartir e imágenes de marca

`content/project.json` define el nombre público, autor, repositorio y URL de la web. La versión del producto se obtiene del archivo raíz `VERSION`. Ejecuta `python3 scripts/site_metadata.py` tras cambiar los metadatos. `make site` genera canonical, Open Graph, Twitter Card y SoftwareSourceCode legibles por crawlers sin JavaScript.

`assets/social-card.png` es la portada web de 1200 × 630; `assets/github-preview.png` es la imagen de 1280 × 640 para Social preview del repositorio. Se conservan sus fuentes SVG y los favicons. Regenera los PNG con `npm ci --ignore-scripts` y `npm run brand`; la portada del repositorio se configura por separado en GitHub.

La URL de publicación predeterminada está en el perfil público. Para otro hosting, usa `GOLIAT_SITE_URL=https://ejemplo.com/nexus/ make site`: cambia canonical e imágenes sin publicar ni modificar el enlace al código. Publica `dist/`, que incluye `.nojekyll` y rutas relativas compatibles con el subdirectorio del repositorio.


## Estrellas de GitHub

La web lee `stars.json` de la rama pública `github-stats`, que solo contiene ese dato. `.github/workflows/stars.yml` lo actualiza a diario a las 06:17 UTC y permite una ejecución manual. El job ejecuta el publicador de metadatos y sus tests: no compila aplicaciones ni Terraform, no despliega Pages y no necesita PAT ni credenciales Azure. Su `GITHUB_TOKEN` temporal puede escribir contenido; el script solo actualiza la rama de datos, sin forzar el historial. `main` conserva sus controles de PR.

El navegador guarda una caché de 15 minutos. Si el dato diario no está disponible o supera las 48 horas, puede consultar la API pública de GitHub y conservar la copia fechada incluida en la web. Cero es un valor válido; un fallo nunca se convierte en un cero inventado. El tooltip indica cuándo se comprobó el valor mostrado. GitHub puede retrasar o desactivar las ejecuciones programadas; puedes reintentarlo en **Actions → Refresh public GitHub stars → Run workflow**. Los forks deben cambiar la URL del repositorio de la web y activar su propio workflow. El navegador no recibe ningún token.

### Por qué conservar la rama github-stats

Almacena los datos públicos del contador, no el despliegue de la web. El workflow programado se ejecuta desde `main`, consulta el repositorio y actualiza únicamente `stars.json`; la web publicada lee directamente ese JSON. No hace falta una build diaria de Pages para actualizar las estrellas. Conserva la rama para este mecanismo: si la borras sin cambiar el workflow, la siguiente actualización la volverá a crear.

Otra opción sería consultar las estrellas durante una build diaria, incluirlas en los archivos generados y publicar Pages cada día. Permitiría quitar la rama de datos, pero exige adaptar el publicador y el frontend, y genera un despliegue completo de la web por cada actualización del contador. Nexus utiliza actualmente la actualización independiente de datos descrita arriba.
