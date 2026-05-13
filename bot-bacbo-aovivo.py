import csv
import datetime
import json
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import List, Optional

import requests
import telebot


@dataclass
class Strategy:
    pattern_reversed: List[str]
    bet: str


class WebScraper:

    def __init__(self):
        self.game = "BAC-BO AO VIVO"
        self.link = "https://lkwn.cc/cb615ffe"# config
        self.api_email = "XXXXXXXXXXXXXXXXXXXXXXX"  # config https://roletax.com/
        self.api_password = "XXXXXXXXXXXXXXXXXXXXXXX"  # config  https://roletax.com/
        self.token = "XXXXXXXXXXXXXXXXXXXXXXX"  # config  https://t.me/BotFather
        self.chat_id = "XXXXXXXXXXXXXXXXXXXXXXX"  # config  https://t.me/WhatChatIDBot

        self.protection = True # config 
        self.winibot = False # config  automatic bot
        self.gales = 2 # config 


        # IA (modelo probabilistico por contexto)
        self.ai_enabled = True # config 
        self.ai_max_context = 4 # config 
        self.ai_min_confidence = 0.60 # config 
        self.ai_min_samples = 40 # config 


        self.provider = "Evolution"  # config 
        self.game_api = "Bac-Bo-Ao-Vivo"  # config 

        self.base_url_api = "https://roletax.com" 
        self.url_api = f"{self.base_url_api}/v1/games/{self.provider}/{self.game_api}"
        self.url_login_api = f"{self.base_url_api}/auth/login"
        self.url_games_api = f"{self.base_url_api}/v1/games"
        self.api_access_token: Optional[str] = None
        self.results_newest_first: Optional[bool] = None
        self.telegram_timeout_seconds = 12
        self.poll_interval_seconds = 1
        self.win_results = 0
        self.branco_results = 0
        self.loss_results = 0
        self.max_hate = 0
        self.win_hate = 0
        self.count = 0
        self.analisar = True
        self.signal_in_progress = False
        self.signal_message_id: Optional[int] = None
        self.signal_thread_id: Optional[int] = None
        self.result_mgs: str = ""
        self.direction_color = "None"
        self.message_delete = False
        self.message_ids: Optional[int] = None
        self.bot = telebot.TeleBot(
            token=self.token,
            parse_mode="MARKDOWN",
            disable_web_page_preview=True,
        )
        self.session = requests.Session()
        self.date_now = str(datetime.datetime.now().strftime("%d/%m/%Y"))
        self.check_date = self.date_now

    def _send_message(self, text: str, **kwargs):
        try:
            return self.bot.send_message(
                chat_id=self.chat_id,
                text=text,
                timeout=self.telegram_timeout_seconds,
                **kwargs,
            )
        except Exception as error:
            print(f"Telegram send_message warning: {error}")
            return None

    def _send_sticker(self, sticker: str):
        try:
            return self.bot.send_sticker(
                self.chat_id,
                sticker=sticker,
                timeout=self.telegram_timeout_seconds,
            )
        except Exception as error:
            print(f"Telegram send_sticker warning: {error}")
            return None

    def _delete_message(self, message_id: int):
        try:
            self.bot.delete_message(
                chat_id=self.chat_id,
                message_id=message_id,
                timeout=self.telegram_timeout_seconds,
            )
            return True
        except Exception as error:
            print(f"Telegram delete warning: {error}")
            return False

    def load_strategies(self, csv_path: str) -> List[Strategy]:
        strategies: List[Strategy] = []

        try:
            with open(csv_path, newline="", encoding="utf-8") as file:
                reader = csv.reader(file)
                for row in reader:
                    if not row:
                        continue

                    raw = str(row[0]).strip()
                    if not raw or "=" not in raw:
                        continue

                    pattern_raw, bet_raw = raw.split("=", 1)
                    pattern_raw = pattern_raw.strip()
                    bet_raw = bet_raw.strip().upper()

                    if not pattern_raw or not bet_raw:
                        continue

                    pattern = [item.strip() for item in pattern_raw.split("-") if item.strip()]

                    # Suporta formato compacto como "BPP" alem de "B-P-P".
                    if len(pattern) == 1 and len(pattern[0]) > 1:
                        pattern = list(pattern[0])

                    pattern_reversed = [item.upper() for item in pattern[::-1]]
                    bet = bet_raw[0]

                    if bet not in ("B", "P"):
                        continue

                    strategies.append(Strategy(pattern_reversed=pattern_reversed, bet=bet))
        except FileNotFoundError:
            print(f"Arquivo de estrategia nao encontrado: {csv_path}")

        print(f"Estrategias carregadas: {len(strategies)}")
        return strategies

    def authenticate_api(self):
        payload = {
            "email": self.api_email,
            "password": self.api_password,
        }

        response = self.session.post(self.url_login_api, json=payload, timeout=10)
        response.raise_for_status()

        token_data = response.json()
        access_token = token_data.get("access_token")

        if not access_token:
            raise ValueError("A API nao retornou access_token no login.")

        self.api_access_token = access_token

    def _normalize_key(self, value: str) -> str:
        return "".join(ch.lower() for ch in str(value) if ch.isalnum())

    def _auth_headers(self) -> dict:
        if not self.api_access_token:
            self.authenticate_api()
        return {"Authorization": f"Bearer {self.api_access_token}"}

    def resolve_game_endpoint(self, headers: dict) -> bool:
        response = self.session.get(self.url_games_api, headers=headers, timeout=10)
        response.raise_for_status()

        games = response.json()
        if not isinstance(games, list):
            return False

        target_provider = self._normalize_key(self.provider)
        target_game = self._normalize_key(self.game_api)

        for item in games:
            provider = item.get("provider", "")
            game = item.get("game", "")

            if (
                self._normalize_key(provider) == target_provider
                and self._normalize_key(game) == target_game
            ):
                self.provider = provider
                self.game_api = game
                self.url_api = f"{self.base_url_api}/v1/games/{self.provider}/{self.game_api}"
                print(f"Endpoint resolvido automaticamente: {self.url_api}")
                return True

        available_for_provider = [
            item.get("game", "")
            for item in games
            if self._normalize_key(item.get("provider", "")) == target_provider
        ]

        print("Jogo nao encontrado exatamente. Disponiveis para o provider:", available_for_provider)
        return False

    def parse_results(self, data_json: dict) -> List[str]:
        results = data_json.get("results")
        if results is None:
            results = data_json.get("resultados")

        if isinstance(results, str):
            parsed = None

            try:
                parsed = json.loads(results)
            except json.JSONDecodeError:
                parsed = None

            if parsed is None:
                clean = results.strip().strip("[]")
                if clean:
                    parsed = [
                        item.strip().strip("\"'")
                        for item in clean.split(",")
                        if item.strip()
                    ]
                else:
                    parsed = []

            results = parsed

        if not isinstance(results, list):
            return []

        return [str(item).strip() for item in results if str(item).strip()]

    def fetch_results_from_api(self) -> List[str]:
        headers = self._auth_headers()
        response = self.session.get(self.url_api, headers=headers, timeout=10)

        if response.status_code == 401:
            self.api_access_token = None
            headers = self._auth_headers()
            response = self.session.get(self.url_api, headers=headers, timeout=10)

        if response.status_code == 404:
            resolved = self.resolve_game_endpoint(headers)
            if resolved:
                response = self.session.get(self.url_api, headers=headers, timeout=10)

        response.raise_for_status()
        game_payload = response.json()

        if "data_json" in game_payload and isinstance(game_payload["data_json"], dict):
            data_json = game_payload["data_json"]
        else:
            data_json = game_payload

        results = self.parse_results(data_json)

        if not results:
            print(f"Resposta inesperada da API: {str(game_payload)[:200]}")

        return results

    def normalize_results_order(self, results: List[str], previous_results: Optional[List[str]] = None) -> List[str]:
        normalized = list(results)

        if (
            self.results_newest_first is None
            and isinstance(previous_results, list)
            and len(previous_results) > 1
            and len(previous_results) == len(normalized)
        ):
            # Novo item entrando no inicio da lista.
            if previous_results[:-1] == normalized[1:]:
                self.results_newest_first = True
            # Novo item entrando no fim da lista.
            elif previous_results[1:] == normalized[:-1]:
                self.results_newest_first = False

            if self.results_newest_first is not None:
                print(f"Ordem detectada (newest_first): {self.results_newest_first}")

        if self.results_newest_first is False:
            normalized.reverse()

        return normalized

    def restart(self):
        if self.date_now != self.check_date:
            print("Reiniciando bot!")
            self.check_date = self.date_now

            self._send_sticker(
                "CAACAgEAAxkBAAEBbJJjXNcB92-_4vp2v0B3Plp9FONrDwACvgEAAsFWwUVjxQN4wmmSBCoE"
            )
            self.results()

            self.win_results = 0
            self.loss_results = 0
            self.branco_results = 0
            self.max_hate = 0
            self.win_hate = 0
            time.sleep(10)

            self._send_sticker(
                "CAACAgEAAxkBAAEBPQZi-ziImRgbjqbDkPduogMKzv0zFgACbAQAAl4ByUUIjW-sdJsr6CkE"
            )
            self.results()
            return True

        return False

    def alert_sinal(self):
        if self.signal_in_progress or self.count > 0 or not self.analisar:
            print("Alerta ignorado: operacao ativa.")
            return

        message = self._send_message(
            text="""
⚠️ ANALISANDO, FIQUE ATENTO!!!
""",
        )
        if message is not None:
            self.message_ids = message.message_id
            self.message_delete = True
        else:
            self.message_ids = None
            self.message_delete = False

    def alert_gale(self):
        kwargs = {}
        if self.signal_message_id is not None:
            kwargs["reply_to_message_id"] = self.signal_message_id
        if self.signal_thread_id is not None:
            kwargs["message_thread_id"] = self.signal_thread_id

        message = self._send_message(
            text=f"""⚠️ Vamos para o {self.count}ª GALE""",
            **kwargs,
        )
        if message is not None:
            self.message_ids = message.message_id
            self.message_delete = True
        else:
            self.message_ids = None
            self.message_delete = False

    def delete(self):
        if self.message_delete and self.message_ids is not None:
            self._delete_message(self.message_ids)
            self.message_delete = False
            self.message_ids = None

    def send_sinal(self):
        if self.signal_in_progress:
            print("Sinal ignorado: operacao em andamento.")
            return

        self.signal_in_progress = True
        self.analisar = False
        message = self._send_message(
            text=(
                f"""
🎲 <b>ENTRADA CONFIRMADA!</b>

🎰 Apostar no {self.direction_color}
🟠 Proteger no EMPATE
🔁 Fazer ate {self.gales} gales

📱 <a href=\"{self.link}\">{self.game}</a>

"""
            ),
            parse_mode="HTML",
        )
        self.signal_message_id = message.message_id if message is not None else None
        self.signal_thread_id = getattr(message, "message_thread_id", None) if message is not None else None

    def send_ai_sinal(self, confidence: float, samples: int):
        if self.signal_in_progress:
            print("Sinal IA ignorado: operacao em andamento.")
            return

        self.signal_in_progress = True
        self.analisar = False
        message = self._send_message(
            text=(
                f"""
🧠 <b>ENTRADA IA CONFIRMADA!</b>

🎰 Apostar no {self.direction_color}
🟠 Proteger no EMPATE
🔁 Fazer ate {self.gales} gales

📊 Confianca IA: {confidence * 100:.1f}% ({samples} amostras)
📱 <a href=\"{self.link}\">{self.game}</a>

"""
            ),
            parse_mode="HTML",
        )
        self.signal_message_id = message.message_id if message is not None else None
        self.signal_thread_id = getattr(message, "message_thread_id", None) if message is not None else None

    def _send_signal_result_message(self, text: str):
        kwargs = {}
        if self.signal_message_id is not None:
            kwargs["reply_to_message_id"] = self.signal_message_id
        else:
            print("[DEBUG] AVISO: signal_message_id é None! Mensagem NÃO será encadeada.")
        if self.signal_thread_id is not None:
            kwargs["message_thread_id"] = self.signal_thread_id
            print(f"[DEBUG] Usando thread: thread_id={self.signal_thread_id}")
        self._send_message(text=text, **kwargs)

    def _ai_predict_direction(self, final_colors: List[str]):
        # final_colors chega com resultado mais recente no indice 0.
        ordered = list(reversed(final_colors))
        if len(ordered) < 3:
            return None

        max_context = min(self.ai_max_context, len(ordered) - 1)
        for context_size in range(max_context, 0, -1):
            transitions = defaultdict(Counter)
            for index in range(len(ordered) - context_size):
                context = tuple(ordered[index : index + context_size])
                nxt = ordered[index + context_size]
                transitions[context][nxt] += 1

            current_context = tuple(ordered[-context_size:])
            counts = transitions.get(current_context)
            if not counts:
                continue

            sample_size = counts.get("P", 0) + counts.get("B", 0)
            if sample_size < self.ai_min_samples:
                continue

            p_count = counts.get("P", 0)
            b_count = counts.get("B", 0)

            if p_count == b_count:
                continue

            if p_count > b_count:
                bet = "P"
                confidence = p_count / sample_size
            else:
                bet = "B"
                confidence = b_count / sample_size

            if confidence < self.ai_min_confidence:
                continue

            return bet, confidence, sample_size, context_size

        return None

    def martingale(self, result: str):
        if result == "WIN":
            print("WIN")
            self.win_results += 1
            self.max_hate += 1
            self.result_mgs = """✅✅✅✅ WIN ✅✅✅✅"""
            self.signal_in_progress = False

        elif result == "LOSS":
            self.count += 1

            if self.count > self.gales:
                print("LOSS")
                self.loss_results += 1
                self.max_hate = 0
                self.result_mgs = """🚫🚫🚫🚫 LOSS 🚫🚫🚫🚫"""
                self.signal_in_progress = False
            else:
                print(f"Vamos para o {self.count}ª gale!")
                self.analisar = False
                self.signal_in_progress = True
                self.alert_gale()
                time.sleep(5)
                if self.winibot:
                    play_url = "http://127.0.0.1:8765/records/29/play"
                    try:
                        response = self.session.get(play_url, timeout=5)
                        response.raise_for_status()
                        print(f"Aposta executada: {play_url}")
                    except requests.RequestException as error:
                        print(f"Erro ao executar aposta automatica: {error}")
                return

        elif result == "EMPATE":
            print("EMPATE")
            self.branco_results += 1
            self.max_hate += 1
            self.result_mgs = """✅✅✅✅ EMPATE ✅✅✅✅"""
            self.signal_in_progress = False

        total = self.win_results + self.branco_results + self.loss_results
        if total != 0:
            accuracy = 100 / total * (self.win_results + self.branco_results)
        else:
            accuracy = 0

        self.win_hate = f"{accuracy:,.2f}%"
        self._send_signal_result_message(text=(
                f"""
{self.result_mgs}
                
► PLACAR = ✅{self.win_results} | 🟠{self.branco_results} | 🚫{self.loss_results}
► Consecutivas = {self.max_hate}
► Assertividade = {self.win_hate}

    """
            ),
        )

        self.signal_message_id = None
        self.signal_thread_id = None
        self.count = 0
        self.analisar = True
        self.restart()

    def check_results(self, result: str):
        if result == "E" and self.protection:
            self.martingale("EMPATE")
            return

        if result == "E" and not self.protection:
            self.martingale("LOSS")
            return

        if result == "E" and self.direction_color == "🟠":
            self.martingale("EMPATE")
            return

        if result != "E" and self.direction_color == "🟠":
            self.martingale("LOSS")
            return

        if result == "B" and self.direction_color == "🔴":
            self.martingale("WIN")
            return

        if result == "B" and self.direction_color == "🔵":
            self.martingale("LOSS")
            return

        if result == "P" and self.direction_color == "🔵":
            self.martingale("WIN")
            return

        if result == "P" and self.direction_color == "🔴":
            self.martingale("LOSS")
            return

    def convert_results_to_colors(self, results: List[str]) -> List[str]:
        mapping = {
            "banker": "B",
            "player": "P",
            "tie": "E",
            "empate": "E",
        }

        final_colors = []
        for item in results:
            key = str(item).strip().lower()
            final_colors.append(mapping.get(key, "E"))

        return final_colors

    def _pattern_matches(self, final_colors: List[str], final_raw: List[str], pattern: List[str]) -> bool:
        if len(final_colors) < len(pattern):
            return False

        for idx, token in enumerate(pattern):
            token_up = token.upper()
            if (
                token_up == "X"
                or token_up == str(final_colors[idx]).upper()
                or token_up == str(final_raw[idx]).upper()
            ):
                continue
            return False

        return True

    def estrategy(self, results: List[str]):
        final_raw = list(results)
        final_colors = self.convert_results_to_colors(results)

        # print(str(datetime.datetime.now().strftime("%H:%M")),final_raw)
        print(str(datetime.datetime.now().strftime("%H:%M")),final_colors[0:20])

        if not final_colors:
            return

        if self.count > 0:
            self.check_results(final_colors[0])
            return

        if self.signal_in_progress:
            self.check_results(final_colors[0])
            return

        if not self.analisar:
            self.check_results(final_colors[0])
            return

        alert_found = False

        for strategy in self.load_strategies("strategy.csv"):
            
            if self._pattern_matches(final_colors, final_raw, strategy.pattern_reversed):
                self.direction_color = "🔵" if strategy.bet == "P" else "🔴"
                print("Sinal encontrado", strategy.pattern_reversed, self.direction_color)

                self.send_sinal()
                time.sleep(5)

                if self.winibot:
                    play_url = None
                    if self.direction_color == "🔵":
                        play_url = "http://127.0.0.1:8765/records/25/play"
                    elif self.direction_color == "🔴":
                        play_url = "http://127.0.0.1:8765/records/27/play"

                    if play_url is not None:
                        try:
                            response = self.session.get(play_url, timeout=5)
                            response.raise_for_status()
                            print(f"Aposta executada: {play_url}")
                        except requests.RequestException as error:
                            print(f"Erro ao executar aposta automatica: {error}")
                return

            alert_pattern = strategy.pattern_reversed[1:]
            if alert_pattern and self._pattern_matches(final_colors, final_raw, alert_pattern):
                alert_found = True

        if self.ai_enabled:
            ai_prediction = self._ai_predict_direction(final_colors)
            if ai_prediction is not None:
                bet, confidence, samples, context_size = ai_prediction
                self.direction_color = "🔵" if bet == "P" else "🔴"
                print(
                    f"Sinal IA encontrado (contexto={context_size}, confianca={confidence:.2f}, amostras={samples})",
                    self.direction_color,
                )
                self.send_ai_sinal(confidence, samples)
                time.sleep(5)
                return

        if alert_found and self.analisar and not self.signal_in_progress and self.count == 0:
            print("ALERTA POSSIVEL SINAL")
            self.alert_sinal()
            return

    def start(self):
        previous_raw_results: List[str] = []

        while True:
            try:
                self.date_now = str(datetime.datetime.now().strftime("%d/%m/%Y"))
                time.sleep(self.poll_interval_seconds)

                raw_results = self.fetch_results_from_api()
                if not raw_results:
                    continue

                normalized_results = self.normalize_results_order(raw_results, previous_raw_results)

                if previous_raw_results != raw_results:
                    previous_raw_results = list(raw_results)
                    self.delete()
                    self.estrategy(normalized_results)

            except Exception as error:
                print("ERROR:", error)

if __name__ == "__main__":
    scraper = WebScraper()
    scraper.start()
