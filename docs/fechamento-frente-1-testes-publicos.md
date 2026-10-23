# iSee — fixtures públicas sem executor privado

A revisão de integração encontrou uma dependência indevida dos testes: as duas
fixtures de diagnóstico executavam o módulo antes de substituir ROOT/FOLDER.
Esse import carregava `control_operator.py` de uma pasta privada absoluta. Os
dados/callbacks dos cenários eram inventados, mas os testes dependiam de código
privado e não eram portáveis para um clone público.

O helper `tests/positive_diagnostic_fake_owner.py` agora intercepta a criação
do loader **antes de executar o módulo público** e fornece um owner inteiramente
inventado, com supervisor, `owned_run` e `capsule` limitados a stubs. Qualquer
execução de filho não explicitamente simulada falha. Não há fallback ou skip
quando o arquivo privado está ausente, nem cópia desse código para o Git.

Uma guarda rejeita a leitura do OLD privado por `Path`/`io.open`, `builtins.open`,
`_io.open_code` ou `os.open`. As duas suítes verificam que o import foi interceptado
sem leitura e exercitam explicitamente a rejeição dessas cinco entradas. Os
estados globais de namespace/sys.path são restaurados ao sair da fixture.

Passaram **39 testes** nos dois arquivos direcionados. As contagens anteriores
se sobrepõem; não são somadas como cenários distintos. Ruff, formatação e
diffcheck passaram. Log e recibo persistentes:
`data/private/fechamento-20261023/frente-1/unit-6-portable-tests/`.
O checkout usado nos testes não possui `data/private/` ou ambiente copiado;
apenas o interpretador existente foi usado por referência explícita.

Nenhum operador, plano autorizado, cápsula ou contrato operacional mudou.
Os SHA-256 continuam:

- Operador v1: `4e5fd7e5a5cff86284de23f34f462c7c2e7e5c7c702f2f8c6b5845c01514bf06`.
- Operador v2: `50d936b77345715eb5fa8eb5e15d25e7b331de4c5227b0a90dff2bda1c31a7a0`.
- Plano v2, bytes: `db36da9563c868938841babbf007a1d16ce172e2f3e9d47f3ea986e2f374f2ba`.

Não houve novo preflight real, modelo, autorização ou versão operacional v3.
O [resultado real de falha do preflight](fechamento-frente-1-diagnostico-v2-resultados.md)
permanece inalterado. Reprodução a partir do clone independente:

```sh
rtk proxy env PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  /home/inteli/Documents/projetos/Galaxies-Inteli-Academy/.venv/bin/python -B \
  -m pytest -q -p no:cacheprovider tests/test_front1_positive_diagnostic.py \
  tests/test_front1_positive_diagnostic_v2.py
```
