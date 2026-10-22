# Candidato de observação isolada do loader CPU

Base `277804223eb6121dbeb541c0663af89ccf334eac`. Preparação para revisão,
sem execução do loader, biblioteca GGML, modelo, encoder ou grafo. Não houve
rede nesta unidade; as fontes foram obtidas uma vez pelo coordenador e lidas
como dados. Não há nova inferência, NIM, instalação, conta ou custo externo.

## Avanço comprovado pela fonte recebida

`ggml-backend.h` declara sob `extern "C"` o registro opaco e as APIs públicas:
`void ggml_backend_load_all_from_path(const char *)`, contagem/get de registro
e nome. A assinatura pública não precisa mais ser inferida de um símbolo.

`ggml-backend-reg.cpp` mostra que um caminho não nulo limita a lista de busca
àquele diretório; a busca padrão em executável/cwd/GGML_BACKEND_DIR ocorre
somente quando o argumento é nulo. Continua existindo a abertura adicional
via GGML_BACKEND_PATH, que deve estar ausente no ambiente da cápsula.

O loader carrega cada variante candidata para consultar seu score. O melhor
começa em zero e muda somente para `s > best_score`; empate não ganha uma
ordenação explícita e pode depender da enumeração. Se nenhum score positivo
existir, tenta o backend base dentro da mesma lista de busca. Não chamaremos
score diretamente: sua assinatura interna não é necessária à sonda pública.
Nenhum defeito de seleção histórico foi demonstrado por essa política.

O caminho de registro CPU não equivale a uma consulta sem efeitos:
`ggml_backend_cpu_reg` chama `ggml_cpu_init`; o device constrói uma descrição
lendo `/proc/cpuinfo`. A desmontagem de `ggml_cpu_init` nas variantes x64 e
alderlake contém chamadas a `ggml_init`/`ggml_free`, inicialização de tabelas
numéricas e estado de ambiente. Isso não demonstra inferência ou graph compute,
mas impede alegar que só CPUID seria executado ou que não existiria contexto
GGML. Uma eventual execução deve abranger explicitamente essa inicialização.

As fontes complementares fecham esse efeito: `ggml-cpu.c:3865` cria contexto
com `{0, NULL, false}` e o libera imediatamente; `ggml.c:1622` inicializa esse
contexto com `n_objects=0`, sem criar tensor/grafo. As tabelas são inicializadas
uma vez por DSO e KMP_BLOCKTIME pode ser definido no ambiente do filho.
`ggml-backend-dl.cpp` usa `dlopen(..., RTLD_NOW | RTLD_LOCAL)` no Linux e dlsym;
o deleter chama dlclose. Isso limita a inferência sobre a API, sem provar
equivalência de build entre a fonte e o bundle. O score permanece executado
internamente pelo loader original, sem uma chamada direta ou ABI inventada.

## Fronteira da observação proposta

A visão `/bundle` contém somente os 16 arquivos e aliases da
[allowlist](verification/vlm-cpu-loader-allowlist-v1.json): dois núcleos GGML
e 14 variantes CPU. Não contém RPC/GPU, libllama/libmtmd, CLI ou modelo. Os
seis DSOs de sistema também têm fontes de mount, destinos e hashes explícitos;
suas dependências NEEDED fecham nesse conjunto. Nenhum diretório de sistema,
projeto, usuário, cache ou modelos é montado inteiro.

A seleção observável é a da cápsula atual. Ela não identifica o backend de
um processo anterior, nem prova equivalência da ordem de enumeração com o
bundle completo. Uma DSO apenas mapeada durante o score não é prova de seleção.
Por isso o resultado deve vir da linha final de registro do loader, validada
contra os basenames conhecidos, juntamente com a confirmação de um único
registro CPU. Texto desconhecido é descartado, sem corpo bruto ou hash.

## C e comando propostos para revisão

A [sonda C](verification/vlm_cpu_loader_probe_v1.c) usa `ggml.h` oficial
verificado para o logger e quatro declarações públicas opacas do backend.
Seu argumento de busca é sempre `/bundle`, sem argumentos de CLI aceitos.
Ela não chama init_backend, get_features, criação de tensor ou graph compute.
O callback aceita somente uma linha INFO completa e literal de registro CPU
com basename conhecido; lê no máximo 256 caracteres, sem copiar texto rejeitado.
Logs e stdout diretos das bibliotecas são descartados. Somente o relatório
fixo usa o descritor de stdout preservado. Registro divergente, duplicata ou
linha não reconhecida de backend carregado falha sem seleção confirmada.

O comando abaixo ainda **não foi executado**. Depende da revisão deste candidato
e da decisão aplicável do coordenador sobre a observação dinâmica local. Não
autoriza modelo, tensor, encoder, grafo, rede ou NIM. Parâmetros privados:
`SOURCE` é o checkout deste candidato; `RUNTIME_BUNDLE` é o bundle já fixado;
`GGML_TEXT` contém o `ggml.h` recebido; `OPERATOR_PARENT` é diretório 0700 do
operador. Nenhum localizador pessoal é publicado. O diretório filho fixo deve
estar ausente; sua existência recusa a execução, sem retry automático.

```sh
rtk proxy /usr/bin/env -i PATH=/usr/bin:/bin SOURCE="$SOURCE" \
  RUNTIME_BUNDLE="$RUNTIME_BUNDLE" GGML_TEXT="$GGML_TEXT" \
  OPERATOR_PARENT="$OPERATOR_PARENT" /usr/bin/timeout --kill-after=1 24 \
  /usr/bin/python3 -I - <<'PY'
import hashlib, json, os, pathlib, re, stat, subprocess

source, bundle, headers, parent = [pathlib.Path(os.environ[n]) for n in
    ('SOURCE', 'RUNTIME_BUNDLE', 'GGML_TEXT', 'OPERATOR_PARENT')]
for path in (source, bundle, headers, parent):
    assert path.is_absolute() and path.resolve() == path and path.is_dir()
assert parent.stat().st_uid == os.getuid()
assert stat.S_IMODE(parent.stat().st_mode) == 0o700
verification = source / 'docs/verification'
manifest_file = verification / 'vlm-cpu-loader-allowlist-v1.json'
assert manifest_file.stat().st_size <= 32768
manifest_raw = manifest_file.read_bytes()
assert hashlib.sha256(manifest_raw).hexdigest() == '9a291e97fb27c13c0aff32b50a744dcd71ac6a012acbc2d1c1de05d37a42e99b'
plan = json.loads(manifest_raw)
probe_source = verification / 'vlm_cpu_loader_probe_v1.c'
def check(path, expected):
    assert not path.is_symlink() and path.is_file()
    assert path.stat().st_size <= 4194304
    assert hashlib.sha256(path.read_bytes()).hexdigest() == expected
check(probe_source, plan['probe_source_sha256'])
check(headers / 'ggml.h', plan['source_sha256']['ggml.h'])
for name, digest in plan['bundle_sha256'].items():
    check(bundle / name, digest)
for item in plan['system_files']:
    check(pathlib.Path(item['source']), item['sha256'])
work = parent / 'vlm-cpu-loader-observation-v1'
work.mkdir(mode=0o700)
binary = work / 'observe'
clean = {'PATH': '/usr/bin:/bin'}
subprocess.run(['/usr/bin/cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
    '-I', str(headers), str(probe_source), '-L', str(bundle),
    '-Wl,-rpath,/bundle', '-Wl,-rpath-link,' + str(bundle),
    '-l:libggml.so.0.27.0', '-l:libggml-base.so.0.27.0',
    '-o', str(binary)], env=clean, check=True, capture_output=True, timeout=10)
check(binary, plan['compiled_probe_sha256'])
elf = subprocess.run(['/usr/bin/readelf', '-ld', str(binary)], env=clean,
    check=True, capture_output=True, text=True, timeout=2).stdout
assert '/lib64/ld-linux-x86-64.so.2' in elf
needed = set(re.findall(r'\(NEEDED\).*?\[(.*?)\]', elf))
assert needed == {'libggml.so.0', 'libggml-base.so.0', 'libc.so.6'}
assert re.search(r'\(RUNPATH\).*?\[/bundle\]', elf)
bwrap = ['/usr/bin/bwrap', '--unshare-all', '--die-with-parent', '--new-session',
    '--clearenv', '--tmpfs', '/', '--dir', '/bundle', '--dir', '/probe',
    '--dir', '/lib', '--dir', '/lib/x86_64-linux-gnu', '--dir', '/lib64',
    '--proc', '/proc']
for name in plan['bundle_sha256']:
    bwrap += ['--ro-bind', str(bundle / name), '/bundle/' + name]
for alias, name in plan['bundle_aliases'].items():
    bwrap += ['--ro-bind', str(bundle / name), '/bundle/' + alias]
for item in plan['system_files']:
    bwrap += ['--ro-bind', item['source'], item['target']]
interpreter = next(x['source'] for x in plan['system_files']
    if x['target'].endswith('/ld-linux-x86-64.so.2'))
bwrap += ['--ro-bind', interpreter, '/lib64/ld-linux-x86-64.so.2',
    '--ro-bind', str(binary), '/probe/observe',
    '--setenv', 'OMP_NUM_THREADS', '4', '--setenv', 'OPENBLAS_NUM_THREADS', '1',
    '--setenv', 'LC_ALL', 'C', '--chdir', '/',
    '--remount-ro', '/proc', '--remount-ro', '/', '--', '/probe/observe']
argv = ['/usr/bin/timeout', '--kill-after=1', '4', '/usr/bin/prlimit',
    '--cpu=2:2', '--as=268435456:268435456', '--core=0:0',
    '--fsize=4096:4096', '--nofile=64:64', '--'] + bwrap
report = work / 'report.json'
code = None
with report.open('xb') as target:
    try:
        code = subprocess.run(argv, env=clean, stdin=subprocess.DEVNULL,
            stdout=target, stderr=subprocess.DEVNULL, timeout=6).returncode
    except subprocess.TimeoutExpired:
        pass  # No claim of cleanup confirmation; no second attempt.
with report.open('rb') as stream:
    raw = stream.read(4097)
report.unlink()
result = {'observed': False, 'code': 'capsule_not_confirmed'}
try:
    value = json.loads(raw)
    if code == 0 and set(value) == {'observed', 'scope', 'variant'}:
        allowed = {n for n in plan['bundle_sha256'] if n.startswith('libggml-cpu-')}
        assert value['observed'] is True and value['scope'] == 'current_capsule_only'
        assert value['variant'] in allowed
        result = value
    elif code == 65 and value == {'observed': False, 'code': 'selection_not_confirmed'}:
        result = value
except (ValueError, TypeError, AssertionError):
    pass
print(json.dumps(result, sort_keys=True))
raise SystemExit(0 if result['observed'] else 70)
PY
```

O ambiente do filho não herda GGML_BACKEND_PATH nem seletores LD. A raiz é
nova, somente leitura; os mounts são arquivos individuais e proc namespaced.
Não há dispositivos GPU ou diretórios de projeto/usuário/modelos. bwrap deve
criar todas as namespaces ou falhar; não há opção de fallback ou compartilhamento
de rede. A disponibilidade de namespaces no kernel ainda não foi ensaiada.

Limites correspondentes ao argv: timeout 4 s + 1 s até SIGKILL; watchdog do
controlador em 6 s, com resultado não confirmado se acionado; RLIMIT_CPU 2 s,
RLIMIT_AS 256 MiB (espaço virtual, não RSS hard), RLIMIT_FSIZE 4096 bytes,
RLIMIT_NOFILE 64, core zero. Compilação tem prazo separado de 10 s e readelf 2 s.
O watchdog externo limita o controlador de preparação a 24 s + 1 s; admitindo
até 5 s residuais de uma observação já iniciada, o orçamento conservador total
é 30 s. Isso não transforma timeout/erro em prova de reaping ou cleanup.
O preflight recusa arquivo maior que 4 MiB antes de calcular seu hash; o
manifesto é limitado a 32 KiB e a leitura final do relatório a 4097 bytes.
R$0, uma observação no máximo e nenhum retry. Limpeza incerta impede aceitação;
a sonda não declara confirmação de cleanup só porque houve timeout.

Uma observação aceita identifica a variante nesta cápsula e permite comparar
essa escolha com uma hipótese concreta de seleção. Não mede threads efetivas
do encoder, não explica timeout anterior e não habilita inferência. Falha de
cápsula, recurso ou registro exige revisar o resultado, sem ensaio às cegas.

## Verificação realizada sem loader real

A C foi compilada/linkada com o header e os DSOs fixados, mas seu binário
**não foi executado**: 16.904 bytes,
SHA256 `bbe654d16c366412ca45a1bea008a1d33fb41b6ae3fccdfb5fc9608f0b6e343a`.
Readelf confirmou somente libggml, libggml-base e libc em NEEDED, RUNPATH
`/bundle` e o interpretador previsto. Nm confirmou somente as cinco imports
GGML da sonda (logger, load_all_from_path, count, get e name).

Os [stubs C inventados](verification/vlm_cpu_loader_probe_fake_test_v1.c)
passaram 12 casos: dois basenames válidos, basename desconhecido, RPC, log
desconhecido junto de válido, duplicata, nível errado, contagem/nome de registro
divergentes, mensagem NULL, mensagem longa e argumentos indevidos antes do
despacho. Há exatamente um despacho API em cada caso aplicável; entrada indevida
despacha zero. O binário fake não possui dependência GGML/llama/mtmd. A saída
direta inventada das bibliotecas é descartada; só a projeção fechada sobrevive.
Isso verifica o observador e suas recusas; não testa CPUID/score, loader real,
isolamento do kernel ou backend efetivamente escolhido. Nenhuma suíte antiga
foi repetida, biblioteca GGML carregada ou inferência executada.
