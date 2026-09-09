# Contrato e dado

Uma tela pode estar implementada certa e aparecer errada porque o dado que a alimenta é mais pobre que o do Figma. Esse defeito é invisível em teste — o teste usa uma fixture rica — e só aparece quando alguém abre o app.

## Regra 1 — todo texto do Figma tem dono

Para cada texto, número e imagem do Figma, nomeie o campo da entity que o alimenta.

| Elemento no Figma | Campo | Existe hoje? |
|---|---|---|
| "Maria Helena Souza" | `Opportunity.patientName` | sim |
| "~4 km da sua residência" | `OpportunityDetail.distanceKm` | não — backend não entrega |

Elemento sem dono é uma pergunta para produto, não um texto fixo no widget. A entity é classe tipada com `fromJson`/`toJson`; a view nunca lê `Map` cru.

Antes de decidir como um órfão degrada, leia na spec da feature as **perguntas abertas e bloqueantes**: estatística sem fonte no backend, toggle sem campo, rótulo cuja origem ninguém confirmou costumam já estar escritos com endpoint proposto ou um "não modelar até produto responder". A decisão desta tabela cita essa linha; não a reinventa.

## Regra 2 — degradação é decisão, não acidente

Campo que o backend não entrega vira opcional na entity. O que a tela faz quando ele é nulo é uma decisão escrita: **a seção não renderiza**, ou **renderiza com um valor de fallback nomeado**. Nunca placeholder decorativo, nunca número inventado, nunca skeleton eterno.

Escreva a decisão por campo. Ela é o que explica, depois, por que a tela do app tem menos coisa que o Figma.

## Regra 3 — o fake que roda o app cobre o caso rico do Figma

Esta é a regra que fura o defeito.

Se o card do Figma mostra nome, endereço, data e resumo, o seed do fake mostra nome, endereço, data e resumo. Um seed magro somado à regra 2 produz uma tela vazia no app enquanto o teste mostra a tela cheia — e ninguém percebe, porque os dois artefatos nunca são comparados.

Checklist do seed:

- [ ] pelo menos um item exercita **todos** os campos opcionais que o Figma desenha
- [ ] pelo menos um item exercita a **degradação** (campos nulos), para ver como fica
- [ ] cada aba, filtro ou estado da tela tem item que cai nele — ramo sem item nunca é visto
- [ ] pelo menos um item com o **texto mais longo realista** (nome com 40 caracteres, endereço de duas linhas) para ver quebra e truncamento
- [ ] texto no idioma real do produto, nome e endereço plausíveis, datas relativas a hoje

## Regra 4 — fixture de teste e seed do fake contam a mesma história

Se divergirem, a divergência é intencional e escrita. O caso normal é o seed do fake ser o superconjunto: ele precisa cobrir o que o olho vai conferir na fase 7.

## Regra 5 — fake não prova contrato

Rodar com fakes confere **layout**. Confere-se **contrato** com o backend real, sem a flag de fakes. Uma resposta `200` com lista vazia não prova nome de campo nenhum.
