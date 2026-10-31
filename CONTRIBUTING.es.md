# Cómo contribuir a Goliat Nexus

[English](CONTRIBUTING.md) · **Español**

Puedes aportar informes de errores, mejoras, ejemplos, traducciones y correcciones de documentación. Las contribuciones utilizan la [licencia del repositorio](LICENSE); conserva la autoría y los avisos de terceros existentes. Consulta [el alcance de la licencia](LICENSING.md) antes de reutilizar el producto.

Utiliza los [formularios de issues](https://github.com/danieljsaldana/goliat-nexus/issues/new/choose) para errores, mejoras, documentación o consultas. Revisa antes las issues existentes y la [wiki](https://github.com/danieljsaldana/goliat-nexus/wiki). Para un cambio importante de arquitectura, explica primero el caso de uso en una issue. Puedes escribir issues y PRs en español o inglés.

Comunica vulnerabilidades mediante el [canal privado](https://github.com/danieljsaldana/goliat-nexus/security/advisories/new), siguiendo [SECURITY.md](SECURITY.md). No publiques credenciales, tfvars reales, estados, planes Terraform ni datos de clientes en issues, PRs, capturas o logs.

## Trabajar desde un fork

Crea un fork en GitHub, clónalo y abre una rama desde `main` actualizado:

```sh
git clone https://github.com/<TU-USUARIO>/goliat-nexus.git
cd goliat-nexus
git remote add upstream https://github.com/danieljsaldana/goliat-nexus.git
git switch -c fix/descripcion-breve
```

Antes de un cambio posterior, descarga las novedades de `upstream` y actualiza tu rama desde `upstream/main`. Abre la PR desde tu fork hacia `main` de este repositorio. No necesitas permisos de escritura, credenciales Azure ni acceso al agente privado para contribuir.

## Preparar herramientas y dependencias

Consulta las [versiones verificadas](docs/VERSIONES.md). CI utiliza Terraform 1.17.1, Python 3.15 y Node.js 24. Docker con motor Linux solo es necesario para la comprobación de imágenes.

```sh
npm ci --ignore-scripts
npm --prefix apps/api ci --ignore-scripts
npm --prefix apps/functions ci --ignore-scripts
npm --prefix apps/portal ci --ignore-scripts
python3 scripts/install_gitleaks.py
python3 scripts/install_actionlint.py
git config core.hooksPath .githooks
```

Instala ShellCheck para validar los scripts y workflows. El hook pre-push revisa las fuentes y el historial; CI repite estos controles.

## Validar las partes afectadas

```sh
make workflows-check
make fmt check test validate
make inventory docs wiki-check
make site site-check
python3 scripts/check_publication.py --history --strict-tracked --artifacts dist
make images-check
```

Ejecuta las comprobaciones relacionadas con tu cambio e indica en la PR cuáles no has podido ejecutar. CI realiza la validación completa antes de fusionar. Los tests Terraform usan proveedores simulados y configuración ficticia. Los tests de aplicación usan datos sintéticos; estos comandos no despliegan Azure. No utilices un entorno de producción para probar una contribución.

Respeta la separación entre módulos Terraform, stacks, CLI y aplicaciones. Añade pruebas de regresión cuando corrijas comportamientos y actualiza tfvars comentados, ejemplos y documentación cuando cambie la configuración. Mantén sincronizados los textos de usuario en inglés y español.

Para cambios web, ejecuta `make site-serve` y revisa tamaños de escritorio y móvil. Los diagramas se editan en `site/diagrams/` como JSON; su HTML se genera. Las páginas fuente de la wiki están en `docs/wiki/`. No subas HTML generado, builds, archivos comprimidos, `.local/`, `.lz/` ni valores de una instalación real. Consulta los [controles de publicación](docs/CI_CD.md).

## Revisión de pull requests

Explica el problema, el nuevo comportamiento y las pruebas realizadas. Enlaza la issue, añade capturas sin datos sensibles cuando ayuden y detalla los recursos, compatibilidad, costes o migraciones de datos que afecte un cambio de infraestructura. Una corrección pequeña de documentación no necesita una issue previa.

Las PRs se ejecutan en runners Ubuntu de GitHub con acceso de lectura a las fuentes y sin secretos Azure. Solo CodeQL recibe permiso para publicar los resultados de seguridad. Un mantenedor debe aprobar la ejecución de workflows de colaboradores externos; es normal que queden esperando. Las PRs no publican Pages, crean releases ni despliegan Azure. Los workflows no ejecutan código de colaboradores mediante `pull_request_target`.

`main` exige una PR, comprobaciones actualizadas, **CI passed**, los tres jobs de CodeQL, la revisión de dependencias y conversaciones de revisión resueltas. Los nuevos commits repiten los controles. La fusión automática está desactivada; un mantenedor decide cuándo fusionar. La configuración para un único mantenedor exige cero votos formales de aprobación, igual que Inventory, para permitirle fusionar sus propias PRs verificadas. Esto no concede permisos de fusión a colaboradores externos. Aumenta ese número cuando exista otro mantenedor independiente.

Respeta el [código de conducta](CODE_OF_CONDUCT.md). Los mantenedores clasifican cambios con `bug`, `enhancement`, `documentation` y `dependencies`; GitHub puede agrupar las notas de release con estas etiquetas. `good first issue` y `help wanted` señalan tareas abiertas a colaboración. Las nuevas issues reciben `needs triage`.

## Ajustes del mantenedor

Los ajustes de GitHub son independientes de los archivos y no se heredan al crear un fork. Mantén activados Issues y los forks, elimina automáticamente las ramas fusionadas, permite actualizar ramas de PR y conserva los controles de `main`. Actions debe tener lectura por defecto, no poder aprobar PRs y exigir aprobación para todos los colaboradores externos. Mantén activados los reportes privados de vulnerabilidades, la detección de secretos y la protección de push. Las correcciones de seguridad de Dependabot siguen pasando por PR, sin fusión automática.

