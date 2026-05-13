# BOT BAC-BO AO VIVO

## Descrição
Este projeto é um bot automatizado para o jogo "BAC-BO AO VIVO". Ele utiliza estratégias definidas em um arquivo CSV para realizar apostas automáticas, além de integrar-se com APIs e enviar notificações via Telegram.

## Estrutura do Projeto
- **bot-bacbo-aovivo.py**: Script principal que contém toda a lógica do bot.
- **requeriments.txt**: Lista de dependências necessárias para executar o projeto.
- **strategy.csv**: Arquivo contendo as estratégias de apostas.

## Funcionalidades
- **Automação de Apostas**: Realiza apostas automáticas com base em estratégias predefinidas.
- **Integração com APIs**: Autenticação e obtenção de resultados via API.
- **Notificações no Telegram**: Envia mensagens e alertas para um chat do Telegram.
- **IA para Previsões**: Utiliza um modelo probabilístico para prever direções com base em contexto.

## Configuração
1. **Clonar o Repositório**:
   ```bash
   git clone <URL_DO_REPOSITORIO>
   ```

2. **Instalar Dependências**:
   Certifique-se de ter o Python instalado. Em seguida, execute:
   ```bash
   pip install -r requeriments.txt
   ```

3. **Configurar Variáveis**:
   Atualize as seguintes variáveis no arquivo `bot-bacbo-aovivo.py`:
   - `api_email`
   - `api_password`
   - `token`
   - `chat_id`

4. **Executar o Bot**:
   ```bash
   python bot-bacbo-aovivo.py
   ```

## Estratégias
As estratégias estão definidas no arquivo `strategy.csv` no seguinte formato:
```
<padrao>=<aposta>
```
Exemplo:
```
BPPPP=B
PBBBB=P
```
- **B**: Banco
- **P**: Jogador
- **E**: Empate

## Dependências
As dependências do projeto estão listadas no arquivo `requeriments.txt`. Algumas principais incluem:
- Flask
- requests
- pyTelegramBotAPI

## Contato
- **Telegram**: [Seu Telegram](https://t.me/mscodex)
- **API**: [RoleTax](https://roletax.com)


## Demo
- **DEMO**: [Bac bo](https://t.me/+3BXcLSr_7wRiOWUx)


## Contribuição
Contribuições são bem-vindas! Sinta-se à vontade para abrir issues e enviar pull requests.

## Licença
Este projeto está licenciado sob a licença MIT. Veja o arquivo LICENSE para mais detalhes.