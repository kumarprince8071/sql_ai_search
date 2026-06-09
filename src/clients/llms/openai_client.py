from src.base.base_llm import BaseLLM
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage
from typing import Type, Any
from src.utils.config import Config


class OpenAIClient(BaseLLM):
    """Concrete implementation for OpenAI."""

    def __init__(self, model_name: str, temperature: float = 0.0):
        self.llm = ChatOpenAI(model=model_name, temperature=temperature,api_key=Config.OPENAI_API_KEY)

    async def generate_structured(self, system_prompt: str, user_prompt: str, schema_class: Type[Any],
                                  history: list = None) -> Any:
        """ this method generates the response based on the structured schema """

        structured_llm = self.llm.with_structured_output(schema_class, method="function_calling")
        messages = [SystemMessage(content=system_prompt)]
        if history:
            messages.append(MessagesPlaceholder(variable_name="history"))
        messages.append(("human", "{query}"))
        prompt = ChatPromptTemplate.from_messages(messages)
        chain = prompt | structured_llm
        return await chain.ainvoke({"query": user_prompt, "history": history or []})

    async def generate_text(self, system_prompt: str, user_prompt: str, history: list = None) -> str:
        """this method generates the response in human readable text in general context without the schema """

        messages = [SystemMessage(content=system_prompt)]
        if history:
            messages.append(MessagesPlaceholder(variable_name="history"))
        messages.append(("human", "{query}"))
        prompt = ChatPromptTemplate.from_messages(messages)
        chain = prompt | self.llm
        result = await chain.ainvoke({"query": user_prompt, "history": history or []})
        return result.content