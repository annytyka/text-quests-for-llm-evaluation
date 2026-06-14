from config import DEEPSEEK_API_KEY_1, DEEPSEEK_API_KEY_2, MISTRAL_API_KEY_1, MISTRAL_API_KEY_2, MISTRAL_API_KEY_3, MISTRAL_API_KEY_4, MISTRAL_API_KEY_5, MISTRAL_API_KEY_6, MISTRAL_API_KEY_7, CLAUDE_API_KEY_1, CLAUDE_API_KEY_2
from mistralai import Mistral
from anthropic import Anthropic
from openai import OpenAI
from config import INTRO_CHAT, INTRO_CONCAT

MISTRAL_API_KEY = MISTRAL_API_KEY_6
DEEPSEEK_API_KEY = DEEPSEEK_API_KEY_2
CLAUDE_API_KEY = CLAUDE_API_KEY_1

TIMEOUT = 300
MAX_TOKENS = 10

class AnthropicAdapter:
    def __init__(
            self,
            model_name="claude-haiku-4-5",
            mode="concat",
            temperature=0.0,
            max_tokens=MAX_TOKENS
    ):
        self.mode = mode
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens

        self.client = Anthropic(api_key=CLAUDE_API_KEY, timeout=TIMEOUT)

        self.INTRO = INTRO_CHAT if self.mode == "chat" else INTRO_CONCAT


    def generate(self, user_prompt, system_prompt=None, temperature=None):
        if system_prompt is None:
            system_prompt = self.INTRO
            self.max_tokens = MAX_TOKENS
        else:
            self.max_tokens = 30000

        if temperature is None:
            temperature = self.temperature

        response = self.client.messages.create(
            model=self.model_name,
            temperature=temperature,
            max_tokens=self.max_tokens,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": user_prompt
                }
            ]
        )

        return response.content[0].text.strip()


class MistralAdapter:
    def __init__(
        self,
        mode="concat",
        model_name="mistral-large-latest",
        temperature=0.0,
        max_tokens=MAX_TOKENS
    ):
        self.mode = mode
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens

        self.client = Mistral(api_key=MISTRAL_API_KEY, timeout_ms=TIMEOUT * 1000)

        self.conversation_id = None

        self.INTRO = INTRO_CHAT if self.mode == "chat" else INTRO_CONCAT


    def generate(self, user_prompt, system_prompt=None, temperature=None):
        if self.mode == "chat":
            return self._ask_chat(user_prompt)
        else:
            return self._ask_concat(user_prompt, system_prompt, temperature)


    def _ask_chat(self, prompt):        
        if self.conversation_id is None:
            res = self.client.beta.conversations.start(
                model=self.model_name,
                instructions=self.INTRO,
                inputs=prompt,
                store=True,
                completion_args={
                    "temperature": self.temperature,
                    "max_tokens": self.max_tokens
                }
            )

            self.conversation_id = res.conversation_id

        else:
            res = self.client.beta.conversations.append(
                conversation_id=self.conversation_id,
                inputs=prompt,
                store=True,
                completion_args={
                    "temperature": self.temperature,
                    "max_tokens": self.max_tokens
                }
            )

        return res.outputs[0].content[0].strip()
    

    def _ask_concat(self, user_prompt, system_prompt=None, temperature=None):
        if system_prompt is None:
            system_prompt = self.INTRO
            self.max_tokens = MAX_TOKENS
        else:
            self.max_tokens = 30000

        if temperature is None:
            temperature = self.temperature

        res = self.client.chat.complete(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature,
            max_tokens=self.max_tokens
        )

        return res.choices[0].message.content.strip()
    
    

class DeepSeekAdapter:
    def __init__(
        self,
        model_name="deepseek-reasoner",
        mode="concat",
        temperature=0.0,
        max_tokens=30000
    ):
        self.mode = mode
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens

        self.client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com", timeout=TIMEOUT)

        self.INTRO = INTRO_CHAT if self.mode == "chat" else INTRO_CONCAT


    def generate(self, user_prompt, system_prompt=None, temperature=None):

        if system_prompt is None:
            system_prompt = self.INTRO

        if temperature is None:
            temperature = self.temperature

        res = self.client.chat.completions.create(
            model=self.model_name,
            temperature=temperature,
            max_tokens=self.max_tokens,
            stream=False,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ]
        )

        return res.choices[0].message.content.strip()
  