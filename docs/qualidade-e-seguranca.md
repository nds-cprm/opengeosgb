# Qualidade e segurança

## Lint (Python e Docker)

O workflow [`.github/workflows/lint.yml`](../.github/workflows/lint.yml) roda em pushes no `main` e em pull requests. Ele tem quatro jobs, e qualquer aviso faz o job falhar. Os avisos do flake8 e do shellcheck viram anotações nas linhas do PR.

| Job | O que verifica | Configuração |
|---|---|---|
| Python | `flake8 src` | `.flake8` |
| Dockerfile | `hadolint` no `Dockerfile` | `.hadolint.yaml` |
| Scripts | `shellcheck` nos scripts versionados, achados pela extensão `.sh` ou pelo shebang (fora o submódulo `docker/`) | `SHELLCHECK_SEVERITY` no workflow |
| Compose | `docker compose config` do compose base com o override, sobre o `.env.sample` | — |

O shellcheck só falha a partir de `warning`. Os `note`, quase todos SC2086 (variável sem aspas), ficam de fora: são dezenas nos scripts herdados do template, e pôr aspas pode mudar o comportamento. O `celery-cmd`, por exemplo, conta com variáveis vazias sumindo da linha de comando. Corrija-os aos poucos e depois suba a severidade para `info`.

As versões das ferramentas ficam fixas no `env` do workflow. Para rodar localmente:

```bash
flake8 src
docker run --rm -i -v "$PWD/.hadolint.yaml:/.config/hadolint.yaml:ro" \
  docker.io/hadolint/hadolint:v2.15.1 hadolint - < Dockerfile
docker run --rm -v "$PWD:/mnt:ro" -w /mnt docker.io/koalaman/shellcheck:v0.11.0 --severity=warning \
  opengeosgb-alias.sh opengeosgb-tests src/*.sh src/celery-cmd src/opengeosgb/br/*.sh
```

Para ignorar uma regra num ponto só, use `# hadolint ignore=DLxxxx` ou `# shellcheck disable=SCxxxx` logo acima da linha, com o motivo.

## Dependabot

O [`.github/dependabot.yml`](../.github/dependabot.yml) abre PRs semanais, às segundas, para dois ecossistemas. Cada PR passa pelo build, pelo smoke test, pelo Trivy e pelo lint.
- **GitHub Actions:** atualizações minor e patch num único PR, e as major em separado. O `trivy-action` é atualizado pelo SHA; antes do merge, confira os advisories e atualize junto o `SCAN_TRIVY_VERSION`.
- **pip (`src/`):** na prática, as versões forçadas do `requirements-overrides.txt`.

Estes ficam de fora e precisam ser atualizados à mão:
- a imagem base do `Dockerfile`, cujo `FROM` é montado por `ARG`;
- as tags git do `src/requirements.txt` (GeoNode e os apps da nds-cprm), porque o Dependabot não atualiza referências git de pip;
- as versões das imagens no `.env`.

O submódulo `docker/` também fica de fora: ele tem uma configuração própria.

## Verificação de vulnerabilidades

O job `scan` do workflow passa o [Trivy](https://trivy.dev/) na imagem amd64 em todos os eventos, inclusive nos pull requests, que não publicam a imagem. Ele relata as vulnerabilidades `HIGH` e `CRITICAL` que já têm correção, nos pacotes do sistema e nas bibliotecas Python do venv, e as publica em dois lugares:
- no resumo da execução do workflow, em tabela;
- na aba **Security > Code scanning** do repositório (SARIF, categoria `trivy-imagem`), que guarda o histórico e fecha os alertas quando a vulnerabilidade some. PRs vindos de forks não enviam o SARIF, porque não têm a permissão `security-events: write`.

As opções ficam no `env` do workflow:
- `SCAN_SEVERITY`: severidades relatadas (padrão `HIGH,CRITICAL`);
- `SCAN_EXIT_CODE`: com `0` (padrão), o scan só relata; com `1`, o job falha quando houver achados, e o `merge` não publica a imagem. Os PRs também passam a falhar;
- `SCAN_TRIVY_VERSION`: versão do Trivy, fixa.

Vulnerabilidades aceitas vão no [`.trivyignore`](../.trivyignore), uma por linha, com o motivo e uma data de expiração (`CVE-AAAA-NNNNN exp:AAAA-MM-DD`). Antes de aceitar uma vulnerabilidade de uma dependência fixada pelo GeoNode, veja se dá para forçar uma versão corrigida no `src/requirements-overrides.txt`, como foi feito com o Pillow.

**Versões fixadas por causa do incidente de 2026.** Em 19/03/2026, o projeto do Trivy teve credenciais roubadas: saiu uma release maliciosa (v0.69.4), e as tags do `aquasecurity/trivy-action` foram trocadas por código que roubava credenciais. Por isso, o workflow:
- referencia o `trivy-action` pelo SHA do commit, nunca pela tag;
- fixa a versão do Trivy, sem `latest`.

Ao atualizar, confira as releases e os advisories de [`aquasecurity/trivy`](https://github.com/aquasecurity/trivy/security/advisories) e de [`aquasecurity/trivy-action`](https://github.com/aquasecurity/trivy-action/security/advisories). Depois, troque o SHA (com a tag no comentário) e o `SCAN_TRIVY_VERSION`.

Para rodar o mesmo scan localmente, com a imagem do Trivy na mesma versão:

```bash
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v "$PWD/.trivyignore:/.trivyignore:ro" \
  docker.io/aquasec/trivy:0.76.2 image --scanners vuln --severity HIGH,CRITICAL --ignore-unfixed \
  --ignorefile /.trivyignore ghcr.io/nds-cprm/opengeosgb-geonode:local
```

No Podman, troque o socket pelo do Podman, por exemplo `$XDG_RUNTIME_DIR/podman/podman.sock`. Ou exporte a imagem com `podman save -o img.tar` e use `trivy image --input img.tar`.
