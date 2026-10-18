# Rotinas de partição e baseline — evidência sintética

Extensão autorizada em 18/10/2026. Estas rotinas preparam a implementação da #2;
resultados científicos reais continuam dependentes da base elegível da #1.
Nenhuma rotina de partição verifica licença, curadoria, datas ou elegibilidade.

## Manifesto de partições

`scripts/channel_partitions.py` oferece `create_partitions`, `freeze_partitions`
e `load_partitions`. As entradas contêm somente `sample_id`, `channel_id`, `sector`,
`media_sha256` e, opcionalmente, `duplicate_group`. Visualizações e outros rótulos
são recusados nesse contrato, para que o resultado não influencie a divisão.

Um canal inteiro pertence a uma partição. Canais conectados por hash de mídia ou
grupo de duplicatas/republicações reconhecidas formam um componente indivisível,
inclusive em cadeias transitivas. A detecção automática de novas republicações
não faz parte desta rotina; ela usa somente os vínculos fornecidos.

O algoritmo versionado usa semente 42 e alvos de aproximadamente 60%/20%/20% dos
canais para treino/validação/teste. A ordem das linhas não altera a saída, e um
canal com muitas publicações não recebe peso adicional na contagem de canais.

Componentes são estratificados pelo conjunto de setores presentes. Estratos com
pelo menos três componentes são distribuídos por déficit de canais, reservando
uma unidade para cada partição. Nos estratos esparsos, há no máximo seis componentes;
suas combinações são enumeradas para minimizar ausência de setores e, depois,
desvio das proporções. Empates são resolvidos por hash da semente e dos grupos.

O manifesto relata contagens efetivas de publicações, canais, componentes e setores
por partição. Grupos grandes podem impedir as proporções exatas. Setores ausentes
e poucos componentes geram avisos explícitos. Menos de três componentes independentes
gera erro, sem repartir publicações do mesmo canal para fabricar suporte.

O arquivo congelado tem esquema, algoritmo, semente, procedência declarada
(`synthetic` ou `unvalidated`), hashes, atribuições e suporte. A recarga verifica
integridade e reproduz a atribuição pelos metadados, detectando alterações de
partição mesmo se o checksum tiver sido recalculado. Escrita atômica com permissão
0600 não substitui arquivos existentes; uma mudança requer novo manifesto.
Hashes identificam o conteúdo, sem constituir assinatura de um revisor.

`real_results_available` é sempre `false`. A procedência declarada não comprova
que um conjunto é elegível. Os registros locais existentes não foram importados,
reclassificados ou usados para treino nesta extensão.

## Verificações da partição

Vinte casos sintéticos passaram: divisão por canal e setor, proporções e contagens,
ordem de entrada, semente, canais prolíficos, duplicatas transitivas entre canais,
grupos mistos esparsos, pouco suporte, contratos, congelamento sem sobrescrita e
detecção de adulteração. Isso verifica o algoritmo, não uma partição científica
real nem generalização preditiva.
