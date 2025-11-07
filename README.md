![Knowball_Banner](https://drive.google.com/uc?export=view&id=10Yb7sST16Aev2MYKxOp6ZmL3FhnRzTXf)

## Evolução do projeto em relação à Sprint 1

O projeto evoluiu significativamente da fase de concepção teórica, apresentada na Sprint 1, para a implementação de um protótipo funcional. Enquanto a primeira sprint focou em definir o problema, o público-alvo e a solução macro, **a Sprint 2 concentrou-se em materializar essas ideias em uma aplicação inicial.**

O escopo original foi mantido, mas o foco prático nos permitiu validar a viabilidade da integração entre a interface de usuário e o banco de dados, **transformando os conceitos planejados em funcionalidades tangíveis.**

## Ferramentas e tecnologias exploradas 

Para o desenvolvimento do protótipo, as seguintes ferramentas e tecnologias, planejadas na Sprint 1, foram exploradas, formando uma arquitetura integrada e escalável: 

  - **Oracle APEX (Application Express):** Oracle APEX é uma plataforma de desenvolvimento low-code nativa do Oracle para criar aplicações web e móveis modernas, seguras e escaláveis de forma rápida.

    - Utilizado para a criação rápida e eficiente da interface web do protótipo, permitindo a construção de formulários para       registro e consulta das denúncias. 

  - **Oracle Database integrado:** o Oracle APEX utiliza uma arquitetura encapsulada em banco de dados, baseada em metadados, que garante acesso aos dados com zero latência, além de oferecer escalabilidade e excelente desempenho.
    
    - O banco de dados Oracle é utilizada não apenas para persistência, mas também para processamento de toda lógica de negócio através de PL/SQL.   

  - **Oracle AI Services (OCI Language):** serviço de IA da **Oracle Cloud** para processamento de linguagem natural, especificamente a API de análise de sentimento.
  
    - Foram iniciados estudos e exploração da API de análise de sentimento para entender como integrá-la ao fluxo de dados. O      objetivo é utilizar este serviço para processar o texto das denúncias, conforme planejado na Sprint 1. 

  - **Bibliotecas python (`pandas`, `scikit-learn`):** a exploração inicial destas bibliotecas foi realizada para planejar o desenvolvimento do mecanismo de detecção de padrões, que analisará os dados em busca de denúncias recorrentes contra os mesmos indivíduos ou equipes:
    
    - `oci`: SDK oficial da **Oracle Cloud** para integração com serviços como **OCI Language**;
    
    - `pandas`: processamento e análise de dados de denúncias armazenadas;
    
    - `scikit-learn`: algoritmos de machine learning para identificação de padrões suspeitos (clustering de denúncias, detecção de anomalias).

## Funcionalidades do protótipo 

O protótipo atual, desenvolvido no **Oracle APEX**, já possui as seguintes funcionalidades implementadas e em execução: 

  - **Formulário de registro de denúncia:** uma interface web permite que o usuário insira as informações essenciais da denúncia, como a partida, o árbitro e um campo de texto para o relato detalhado.

![Imagem](https://drive.google.com/uc?export=view&id=1qByk9LlRtsXpyLpju8KjdTZs_iurRyM-)

  - **Geração de protocolo anônimo:** após o envio do formulário, o sistema registra a denúncia no banco de dados e gera automaticamente um número de protocolo único, que é exibido ao denunciante para acompanhamento futuro.

![Imagem](https://drive.google.com/uc?export=view&id=1qOW88e3f5n8LI3cP9T1AA1OgeJfo2NHM)

  - **Tela de consulta de protocolo:** uma funcionalidade básica de consulta foi implementada, permitindo ao usuário inserir seu número de protocolo para verificar o status atual da sua denúncia (ex: “Recebida”, “Em análise”).

![Imagem](https://drive.google.com/uc?export=view&id=1SZfxWnJF0RpVSC4ZnQffetbCVc77_dIv)

## Integrações que já puderam ser testadas ou implementadas

A principal integração implementada e testada com sucesso nesta sprint foi:

- **Integração entre Oracle APEX e Oracle Database (banco de dados integrado):** a conexão entre a interface do protótipo e o banco de dados embutido no APEX estão totalmente funcionais. Os formulários criados no APEX conseguem inserir (registrar denúncias) e consultar dados diretamente nas tabelas do banco de dados, garantindo a persistência das informações.

- Adicionalmente, **foi realizado um teste preliminar (prova de conceito) de consumo da API do serviço de análise de sentimento da OCI**, confirmando a viabilidade técnica de enviar um texto de denúncia e receber uma classificação de sentimento.

## Próximos passos até a versão final 

Para as próximas sprints, os passos planejados para a evolução do projeto são: 

  1. **Integração contínua da IA:** implementar de forma definitiva a chamada à **API de análise de sentimento** para que toda nova denúncia seja automaticamente classificada e marcada no banco de dados.
     
  2. **Desenvolvimento do módulo de análise de dados:** criar o back-end que analisará os dados armazenados para identificar padrões e tendências suspeitas, como múltiplas denúncias contra um mesmo árbitro ou time.
     
  3. **Criação de um dashboard administrativo:** desenvolver uma visão para os administradores do sistema, onde possam visualizar as denúncias, os resultados da análise de sentimento e os alertas gerados pela análise de dados.
     
  4. **Refinamento da interface (UI/UX):** melhorar a experiência do usuário no protótipo com base em feedbacks e testes de usabilidade.

## Fluxo técnico

O que acontece **AGORA** (Sprint 2):

```bash
   APEX     →      Database     →        APEX
(interface)    (salva/atualiza)    (mostra protocolo)
```

O que acontecerá **DEPOIS** (Sprints futuras):

```bash
   APEX     →      Database   →     OCI Language     →    Database    →         APEX
(interface)        (salva)      (analisa sentimento)     (atualiza)       (mostra protocolo)
```

```bash
 Database   →      Python (pandas + scikit-learn)     →    Database    →    Dashboard APEX
 (dados)             (detecta padrões suspeitos)           (alertas)      (visualização admin)
```

## Vídeo de demonstração

Segue abaixo o link do vídeo apresentando a evolução do projeto e demonstrando o funcionamento do protótipo: 

> 🎬 Clique na imagem abaixo para assistir no YouTube

[![Assista ao vídeo](https://img.youtube.com/vi/UewdXhF_TZ8/maxresdefault.jpg)](https://youtu.be/ctzDoaCnXF4?si=H6sil0fHTgRDbUEb)
