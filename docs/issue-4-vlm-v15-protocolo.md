# Produto v15 — configuração nativa e projeção explícita

O aluno autorizou em 20/10/2026 implementar e avaliar a
[proposta pós-v14](issue-4-vlm-pos-v14-investigacao-e-proposta.md).
Uma versão R, fila própria e até **44 chamadas / zero aquisições / 1.200 s**.
Nenhuma auditoria nova, treino B/C ou promoção do M1 está incluída.

## Contrato congelado

Copiar exatamente prompt, schema e projeção do rascunho aprovado. Hashes:

- Prompt: `5896b5bf3c9e053c09da1179e11737e0d5b782b524cd179346a94bece1d23d36`.
- Schema: `1ee90e85d7204bbf21c86c7146852fb84fc433e26cc41a7949a90660cf54bfd3`.
- Projeção: `958f8d2f25e00d581f3d8bcc80278d78fabd10b6595124451b59c1c2f525adf0`.

Saída nativa: `item_configuration`, `state`, `presented_categories`, nessa ordem.
Dez configurações e 22 objetos: 19 positivos e três negativos/incerto.
Ausência/incidental/incerto exigem lista vazia. Sete configurações positivas
exigem exatamente uma categoria. Cabide, tecido puxado e detalhe enquadrado
admitem somente garment; as demais admitem as quatro categorias originais.
Preservar raw e configuração nativa; projetar para os 16 objetos semânticos
anteriores, com origem explícita
`derived_from_model_declared_item_configuration_not_independent_verification`.
A projeção não verifica pixels nem transforma respostas antigas em respostas v15.
Não reparar raw, categorias ou GT. Mesmos mapper, OR e janela de produto ≤3 s;
pessoa/texto em cache. Ambiguidade permanece unknown.

Qwen3-VL-2B Q4_K_M, projetor Q8_0 e b11716 instalados, CPU4, seed42, temperatura0,
saída64, limites visuais solicitados64/128 e um PNG RGB320×330 por chamada.
Nenhuma instalação, aquisição ou troca de ambiente/runtime/pesos.

## Gate nativo e verificação

Reutilizar ponte C++ v13 imutável e nove cabeçalhos oficiais em cache; compilar
somente a ponte contra as bibliotecas instaladas. Exigir conversão integral
`json_schema_to_grammar(..., false)`, sem warnings, com término completo,
zero divergências nos 13.640 objetos do domínio finito (22 aceitos), 22 variações de whitespace dos campos e 19 mutações brutas (13.681 sondas). Ordem de campos fixada pela
gramática; decoder semântico não exige ordem. Sem modelo ou forward pass nesse
gate. Conferir com o tokenizer instalado os 22 objetos compactos/com whitespace dos campos,
incluindo reserva de um token final em 64. Enums de arrays são literais nativos: whitespace interno ao array não é
aceito; whitespace arbitrário não é garantido. O primeiro preflight com arrays
indentados falhou em 19 sondas; preservá-lo e corrigir apenas a expectativa de
whitespace do verificador, sem alterar prompt, schema ou projeção.
Pin de fontes, bibliotecas, headers, schema, gramática e respostas. Testes usam
fixtures inventadas, sem runtime/internet/dados privados. Commit verificado antes
de gerar; fonte alterada após preflight invalida recibo.

## Execução limitada e revisão

1. Mesmos 12 controles, hashes e receita. Exigir 12/12 false. Falha perceptiva
   conclui o bloco e sela; falha operacional/JSON/identidade interrompe sem retry.
2. Se passar, quatro crops das oito folhas preservadas: 32 chamadas, sem download.
   Mesmos pixels/tempos; nem substituição de caso nem novos frames.
3. Após o bloco, pausar para revisão assistida de toda configuração/categoria
   positiva, inclusive tardia, vinculada a plano, resultado, crop, tempo,
   configuração, categoria, pista derivada, origem e hash da projeção. Revisar
   mesmo se o gate legado de valor+frames não passar. False/unknown reprova;
   ausência de recibo mantém pausa sem novas chamadas. Revisão não é cega nem
   certificação humana. Não forçar held/worn para recuperar dois casos de blusa
   com evidência inicial ambígua na inspeção congelada.
4. Selar depois da revisão e reportar separadamente 8/8 valor+frames do GT legado
   e suporte de configuração. Mesmo se ambos passarem, nenhuma continuação
   automática, aquisição, auditoria ou liberação de colunas.

Reservas duráveis antes do despacho; executor único com locks ancestrais;
180 s por chamada, RSS3,3 GiB, contabilização conservadora em interrupção.
Orçamento acumulado parte de 1.799 chamadas / 256 aquisições /
36.786,75786307302 s e termina no máximo em 1.843 / 256 / 37.986,75786307302 s.
Saldo antigo encerrado não é reaproveitado. Running/incerto não é retomável.

Comparar v14 nos oito vídeos, v13 nos quatro completos e demais caches nas
interseções reais. Controles com v14/v13/v11. Ganhos/perdas, denominadores,
unknown e evidência sem alterar pessoa/texto. Mudança conjunta de prompt e
representação não isola mecanismo causal. Oito positivos de moda não aprovam
o gate cego original nem a prontidão descritiva de 20 casos.

## Preservação

Guardas das coortes200/300, pins herdados e snapshot privado anterior à mudança.
Preservar oito folhas PNG, recortes/tempos, anotações, partições203/66/31, teste
reservado sem leitura semântica, M1/A200, A300, B-cache, serviço Python/MCP,
dependências, locks e ambientes. V14 e filas anteriores seladas e imutáveis.
README não rastreado fora do escopo, sem leitura, edição ou staging.
