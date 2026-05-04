import os
from pydantic import BaseModel, Field
from langchain_community.chat_models import ChatOllama
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from ...base_tool import BaseAgenticTool

class TextGeneratorArgs(BaseModel):
    system_prompt: str = Field(..., description="The system prompt defining the persona or rules")
    user_prompt: str = Field(..., description="The user prompt containing the request")
    model_name: str = Field("llama3", description="The model name to use")
    provider: int = Field(1, description="1 for local (Ollama), 2 for cloud (Groq)")

class TextGeneratorTool(BaseAgenticTool):
    name = "text_generator"
    description = "Generates text using a local LLM via Ollama. Useful for brainstorming, writing stories, or generating dialogue."
    args_schema = TextGeneratorArgs

    # Best Groq model for creative generation tasks
    GROQ_CREATIVE_MODEL = "llama-3.3-70b-versatile"
    # Fast Groq model for structured/parsing tasks
    GROQ_FAST_MODEL = "llama-3.1-8b-instant"

    def execute(self, system_prompt: str, user_prompt: str, model_name: str = "llama3", provider: int = 2) -> str:
        if provider == 1:
            # Local version via Ollama
            llm = ChatOllama(model=model_name, temperature=0.7)
        elif provider == 2:
            # Cloud version via Groq — use 70B for creative tasks, 8B if caller explicitly requests fast
            groq_model = model_name if model_name not in ("llama3", "llama-3.1-8b-instant") else self.GROQ_CREATIVE_MODEL
            llm = ChatGroq(model=groq_model, temperature=0.7)
        else:
            raise ValueError("Invalid provider choice. Use 1 for local, 2 for cloud.")
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        response = llm.invoke(messages)
        return response.content
