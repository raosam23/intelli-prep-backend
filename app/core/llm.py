from langchain_openai import ChatOpenAI
from app.core.config import settings
from pydantic import SecretStr

llm = ChatOpenAI(
    model='gpt-4o-mini',
    temperature=0,
    api_key=SecretStr(settings.OPENAI_API_KEY)
)