# Reporte de PyroTrace

La documentación técnica en español se compila con `just report::documentation`.
El documento describe los datos de Centroamérica y presenta citas, referencias y
formato de página conforme a APA, séptima edición.
Desde `apps/report` en PowerShell también se puede ejecutar:

```powershell
typst compile --font-path fonts documentation.typ output/PyroTrace_Armonizacion.pdf
```

El contenido editable está en `docs/harmonization.md`, desde la raíz del repositorio.

Prototipo experimental con fuentes primarias, ecuaciones y evidencia reproducible.
La explicación en español está en [../../docs/harmonization.md](../../docs/harmonization.md).

## Comprobar y compilar desde PowerShell

Desde la raíz del repositorio:

```powershell
python apps/report/validation/verify_prototype.py
cd apps/report
New-Item -ItemType Directory -Path output -Force | Out-Null
typst compile --font-path fonts main.typ output/report.pdf
Invoke-Item output/report.pdf
```

En Git Bash: `just report::validate`, `just report::build` y `just report::watch`.

## Actualizar la evidencia

Desde la raíz, después de revisar los resultados:

```powershell
python apps/report/validation/verify_prototype.py --refresh-report-data
```

El snapshot `validation/results.json` contiene los resultados, versión de DuckDB y
hashes SHA-256 de los SQL. Los archivos detallados están en `output/validation`.
Las comprobaciones ejecutan cuatro SQL sobre 810 registros sintéticos y comprueban
preservación de tuplas, límites horarios/espaciales, plataformas y FRP ausente.
También verifican el total del JSON mensual. No acreditan precisión científica.

Las referencias están en `references.bib`. Los valores de respaldo 2.20, 6.12, 4.50
y 1.14 son provisionales. El calendario actual muestra conteos brutos.
El PDF se genera en `output`, ignorado por Git. Liberation Serif se incluye con su licencia.
